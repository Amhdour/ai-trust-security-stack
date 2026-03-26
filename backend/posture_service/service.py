from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.evidence_service.service import build_evidence_pack_summary
from backend.integration_adapter.repository import (
    load_eval_summaries,
    load_policy_bundle,
    load_reviewer_bundle,
    load_sample_events,
    load_service_inventory,
    repo_root,
)
from backend.launch_gate_service.service import build_launch_gate_summary


def _card(label: str, value: str, status: str, detail: str) -> dict[str, str]:
    return {"label": label, "value": value, "status": status, "detail": detail}


def _record(title: str, meta: str, detail: str, status: str = "neutral") -> dict[str, str]:
    return {"title": title, "meta": meta, "detail": detail, "status": status}


def _raw(path: str) -> str:
    return f"/raw/{path}"


def _status_from_launch(verdict: str) -> str:
    return {
        "go": "healthy",
        "conditional": "warning",
        "no-go": "critical",
    }.get(verdict, "neutral")


def _count_events(events: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(event.get("event_type", "")) for event in events)


def _latest(items: list[dict[str, Any]]) -> dict[str, Any]:
    return items[-1] if items else {}


def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def build_control_plane_dashboard(root: Path | None = None) -> dict[str, Any]:
    resolved_root = repo_root(root)
    services = load_service_inventory(resolved_root)
    events = load_sample_events(resolved_root)
    counts = _count_events(events)
    policy = load_policy_bundle(resolved_root)
    reviewer = load_reviewer_bundle(resolved_root)
    evidence_summary = build_evidence_pack_summary(resolved_root)
    launch_summary = build_launch_gate_summary(resolved_root)
    eval_summaries = load_eval_summaries(resolved_root)
    latest_eval = _latest(eval_summaries)

    request_events = [event for event in events if event.get("event_type") == "request.start"]
    policy_events = [event for event in events if event.get("event_type") == "policy.decision"]
    retrieval_events = [event for event in events if event.get("event_type") == "retrieval.decision"]
    deny_events = [event for event in events if event.get("event_type") == "deny.event"]
    tool_events = [event for event in events if event.get("event_type") == "tool.execution_attempt"]
    fallback_events = [event for event in events if event.get("event_type") == "fallback.event"]
    trace_ids = _unique([str(event.get("trace_id", "")) for event in events])
    audit_events = reviewer.get("sample_audit_events", {}).get("events", [])
    blocked_attacks = reviewer.get("blocked_attack_summary", {}).get("blocked_attacks", [])

    allowed_sources = policy.get("retrieval", {}).get("tenant_allowed_sources", {})
    allowed_integrations = policy.get("integrations", {}).get("allowed_integrations", [])
    mcp_servers = [value for value in allowed_integrations if str(value).startswith("mcp_server.")]
    registered_tools = _unique(
        list(policy.get("tools", {}).get("allowed_tools", []))
        + list(policy.get("tools", {}).get("forbidden_tools", []))
    )
    confirmation_required = list(policy.get("tools", {}).get("confirmation_required_tools", []))
    sandbox_required_tools = ["admin_shell"] if (resolved_root / "overlays/myStarterKit/artifacts/logs/sandbox/demo-admin_shell-evidence.json").exists() else []
    eval_passed = int(latest_eval.get("passed_count", 0))
    eval_total = int(latest_eval.get("total", 0))
    eval_failed = max(eval_total - eval_passed, 0)
    readiness_status = launch_summary["status"]

    retrieval_rows = []
    for tenant_id, sources in allowed_sources.items():
        for source in sources:
            retrieval_rows.append(
                {
                    "tenant": tenant_id,
                    "source": source,
                    "boundary": "tenant-scoped",
                    "trust": "trust metadata + provenance required",
                }
            )

    tool_rows = [
        {
            "control": "Registered tools",
            "value": str(len(registered_tools)),
            "notes": ", ".join(registered_tools) or "none",
        },
        {
            "control": "Approved tools",
            "value": str(len(policy.get("tools", {}).get("allowed_tools", []))),
            "notes": ", ".join(policy.get("tools", {}).get("allowed_tools", [])) or "none",
        },
        {
            "control": "Blocked tools",
            "value": str(len(policy.get("tools", {}).get("forbidden_tools", []))),
            "notes": ", ".join(policy.get("tools", {}).get("forbidden_tools", [])) or "none",
        },
        {
            "control": "Confirmation-required tools",
            "value": str(len(confirmation_required)),
            "notes": ", ".join(confirmation_required) or "none",
        },
        {
            "control": "Sandbox-required tools",
            "value": str(len(sandbox_required_tools)),
            "notes": ", ".join(sandbox_required_tools) or "none",
        },
        {
            "control": "MCP server inventory",
            "value": str(len(mcp_servers)),
            "notes": ", ".join(mcp_servers) or "none",
        },
    ]

    audit_rows = [
        {
            "event": str(event.get("event_type", "audit.event")),
            "trace_id": str(event.get("trace_id", "")),
            "request_id": str(event.get("request_id", "")),
            "summary": str(event.get("event_payload", {}).get("action", "captured")),
        }
        for event in audit_events[:5]
    ]

    launch_records = [
        _record(
            title=str(finding.get("control", "control")),
            meta=str(finding.get("status", "unknown")),
            detail=str(finding.get("summary", "")),
            status="healthy" if finding.get("status") == "pass" else "warning",
        )
        for finding in launch_summary.get("findings", [])
    ]

    sections = [
        {
            "id": "overview",
            "title": "Global Security Posture",
            "description": "Topline platform health across control, runtime, and evidence planes.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Top cards",
                    "items": [
                        _card(
                            "System status",
                            "Control tower live",
                            "healthy",
                            f"{len(services)} services inventoried across the local stack.",
                        ),
                        _card(
                            "Policy engine status",
                            "OPA connected" if "opa" in services else "OPA pending",
                            "healthy" if "opa" in services else "warning",
                            f"{len(allowed_integrations)} governed integrations in policy inventory.",
                        ),
                        _card(
                            "Identity status",
                            "Keycloak fronting sessions" if "keycloak" in services else "Identity adapter only",
                            "healthy" if "keycloak" in services else "warning",
                            "Dashboard-first flow starts with identity and session context.",
                        ),
                        _card(
                            "Retrieval backend status",
                            "Qdrant posture loaded" if "qdrant" in services else "Retrieval inventory only",
                            "healthy" if "qdrant" in services else "warning",
                            f"{sum(len(sources) for sources in allowed_sources.values())} source boundaries are modeled.",
                        ),
                        _card(
                            "Telemetry pipeline status",
                            "Langfuse + Grafana + Superset",
                            "healthy" if {"langfuse", "grafana", "superset"}.issubset(set(services)) else "warning",
                            f"{len(events)} sample telemetry events are available for dashboard aggregation.",
                        ),
                        _card(
                            "Launch-gate status",
                            readiness_status.upper(),
                            _status_from_launch(readiness_status),
                            f"Readiness score {launch_summary['readiness_score']} with {launch_summary['control_coverage']} controls fully passing.",
                        ),
                    ],
                }
            ],
        },
        {
            "id": "runtime",
            "title": "Live Runtime Activity",
            "description": "Request, policy, deny, and operator-confirmation activity summarized in one pane.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Live posture",
                    "items": [
                        _card("Active sessions", str(len(_unique([str(event.get("request_id", "")) for event in request_events]))), "healthy", "Distinct request sessions observed in the runtime sample."),
                        _card("Recent requests", str(len(request_events)), "neutral", "New requests entering the governed runtime."),
                        _card("Recent policy decisions", str(len(policy_events)), "neutral", "Policy checkpoints emitted by the runtime path."),
                        _card("Recent deny events", str(len(deny_events)), "warning" if deny_events else "healthy", "Explicit deny events raised by governance controls."),
                        _card("Tool execution attempts", str(len(tool_events)), "neutral", "Observed attempts to invoke tools from agent flows."),
                        _card("Fallback events", str(len(fallback_events)), "warning" if fallback_events else "healthy", "Fallback or degraded-runtime signals."),
                    ],
                },
                {
                    "type": "records",
                    "title": "Recent runtime events",
                    "items": [
                        *[
                            _record(
                                title=f"Request {event.get('request_id', '')}",
                                meta=f"{event.get('tenant_id', '')} | {event.get('timestamp', '')}",
                                detail=f"Path {event.get('payload', {}).get('path', '/runtime')}",
                                status="neutral",
                            )
                            for event in request_events
                        ],
                        *[
                            _record(
                                title=f"Deny {event.get('request_id', '')}",
                                meta=f"{event.get('tenant_id', '')} | {event.get('timestamp', '')}",
                                detail=str(event.get("payload", {}).get("reason", "denied")),
                                status="warning",
                            )
                            for event in deny_events
                        ],
                        *[
                            _record(
                                title=f"Confirmation required: {tool_name}",
                                meta="Tool governance",
                                detail="High-impact action stays behind explicit user confirmation.",
                                status="warning",
                            )
                            for tool_name in confirmation_required
                        ],
                    ],
                },
            ],
        },
        {
            "id": "retrieval",
            "title": "Retrieval Security View",
            "description": "Tenant boundaries, retrieval decisions, and provenance posture for RAG workflows.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Retrieval posture",
                    "items": [
                        _card("Indexed sources", str(len(retrieval_rows)), "healthy", "Sources currently modeled for tenant-scoped retrieval."),
                        _card("Tenant/source boundaries", str(len(allowed_sources)), "healthy", "Per-tenant source segmentation is declared in policy."),
                        _card("Retrieval decisions", str(len(retrieval_events)), "neutral", "Observed retrieval allow/deny decisions."),
                        _card("Blocked retrieval attempts", "0", "healthy", "No blocked retrieval attempts in the current telemetry sample."),
                        _card("Provenance coverage", "Required", "healthy", "Provenance and trust metadata checks are enforced in policy."),
                        _card("Connector exposure", "Scoped", "healthy", "Retrieval connectors are surfaced through allowed integration inventory only."),
                    ],
                },
                {
                    "type": "table",
                    "title": "Source boundaries",
                    "columns": [
                        {"key": "tenant", "label": "Tenant"},
                        {"key": "source", "label": "Indexed source"},
                        {"key": "boundary", "label": "Boundary"},
                        {"key": "trust", "label": "Trust requirements"},
                    ],
                    "rows": retrieval_rows,
                },
                {
                    "type": "records",
                    "title": "Recent retrieval decisions",
                    "items": [
                        _record(
                            title=f"{event.get('payload', {}).get('decision', 'allow').upper()} retrieval",
                            meta=f"{event.get('tenant_id', '')} | {event.get('timestamp', '')}",
                            detail=f"Backend {event.get('payload', {}).get('source', 'unknown')}",
                            status="healthy" if event.get("payload", {}).get("decision") == "allow" else "warning",
                        )
                        for event in retrieval_events
                    ],
                },
            ],
        },
        {
            "id": "tools-mcp",
            "title": "Tool and MCP Control View",
            "description": "Registered tools, approval gates, sandbox posture, and MCP inventory.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Control counts",
                    "items": [
                        _card("Registered tools", str(len(registered_tools)), "neutral", "Union of approved and blocked tool inventory."),
                        _card("Approved tools", str(len(policy.get("tools", {}).get("allowed_tools", []))), "healthy", "Tools allowed for governed execution."),
                        _card("Blocked tools", str(len(policy.get("tools", {}).get("forbidden_tools", []))), "warning", "Tools denied by policy bundle."),
                        _card("Confirmation-required", str(len(confirmation_required)), "warning", "High-impact tools requiring user approval."),
                        _card("Sandbox-required", str(len(sandbox_required_tools)), "warning" if sandbox_required_tools else "healthy", "Tools routed through isolated execution when needed."),
                        _card("MCP servers", str(len(mcp_servers)), "neutral", "Registered MCP runtime surfaces in policy inventory."),
                    ],
                },
                {
                    "type": "table",
                    "title": "Tool controls",
                    "columns": [
                        {"key": "control", "label": "Control"},
                        {"key": "value", "label": "Value"},
                        {"key": "notes", "label": "Notes"},
                    ],
                    "rows": tool_rows,
                },
                {
                    "type": "records",
                    "title": "Recent tool decisions",
                    "items": [
                        *[
                            _record(
                                title=f"Tool attempt: {event.get('payload', {}).get('tool_name', 'unknown')}",
                                meta=f"{event.get('request_id', '')} | {event.get('timestamp', '')}",
                                detail="Observed from runtime activity stream.",
                                status="neutral",
                            )
                            for event in tool_events
                        ],
                        *[
                            _record(
                                title=f"Blocked tool path: {event.get('payload', {}).get('reason', 'forbidden_tool')}",
                                meta=f"{event.get('request_id', '')} | deny.event",
                                detail="Governance denied the attempted action.",
                                status="warning",
                            )
                            for event in deny_events
                        ],
                    ],
                },
            ],
        },
        {
            "id": "evals",
            "title": "AI Traces and Evals",
            "description": "Trace coverage, red-team readiness, and eval quality posture across models and agents.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Trace and eval summary",
                    "items": [
                        _card("Recent traces", str(len(trace_ids)), "neutral", "Unique traces observed in the telemetry sample."),
                        _card("Prompt/response paths", f"{counts.get('request.start', 0)}/{counts.get('request.end', 0)}", "healthy", "Request starts versus completed responses."),
                        _card("Eval pass/fail counts", f"{eval_passed}/{eval_failed}", "healthy" if eval_failed == 0 else "warning", "Latest red-team summary snapshot."),
                        _card("Red-team scenario status", f"{reviewer.get('blocked_attack_summary', {}).get('blocked_count', 0)} blocked", "healthy", "Known hostile scenarios are being intercepted."),
                        _card("Safety metrics", f"{eval_passed}/{eval_total}", "healthy", "Latest suite reports security-redteam pass coverage."),
                        _card("Quality views", "Per runtime module", "neutral", "Split between control-plane summary and drill-down tooling."),
                    ],
                },
                {
                    "type": "records",
                    "title": "Recent traces and evals",
                    "items": [
                        *[
                            _record(
                                title=f"Trace {trace_id}",
                                meta="Langfuse-ready telemetry",
                                detail="Prompt/response path is available for downstream drill-down.",
                                status="neutral",
                            )
                            for trace_id in trace_ids
                        ],
                        *[
                            _record(
                                title=scenario.get("scenario", "Red-team scenario"),
                                meta=scenario.get("decision", "blocked"),
                                detail=scenario.get("control_triggered", ""),
                                status="healthy",
                            )
                            for scenario in blocked_attacks
                        ],
                    ],
                },
            ],
        },
        {
            "id": "audit-replay",
            "title": "Audit and Replay",
            "description": "Audit trails, trace IDs, replay-ready sessions, and exportable evidence links.",
            "blocks": [
                {
                    "type": "table",
                    "title": "Recent audit events",
                    "columns": [
                        {"key": "event", "label": "Audit event"},
                        {"key": "trace_id", "label": "Trace ID"},
                        {"key": "request_id", "label": "Request ID"},
                        {"key": "summary", "label": "Summary"},
                    ],
                    "rows": audit_rows,
                },
                {
                    "type": "records",
                    "title": "Replay and deny posture",
                    "items": [
                        _record(
                            title="Replay-ready sessions",
                            meta=str(len(_unique([str(event.get("request_id", "")) for event in audit_events]))),
                            detail="Audit sample includes request identifiers needed for replay correlation.",
                            status="healthy",
                        ),
                        *[
                            _record(
                                title=f"Deny reason: {event.get('payload', {}).get('reason', 'policy_denied')}",
                                meta=str(event.get("trace_id", "")),
                                detail="Visible to operators from the audit and runtime deny stream.",
                                status="warning",
                            )
                            for event in deny_events
                        ],
                    ],
                },
                {
                    "type": "links",
                    "title": "Evidence exports",
                    "items": [
                        {
                            "label": export["label"],
                            "href": export["href"],
                            "description": export["description"],
                            "status": "healthy",
                        }
                        for export in evidence_summary["exports"]
                    ],
                },
            ],
        },
        {
            "id": "launch-gate",
            "title": "Launch Gate and Readiness",
            "description": "Coverage, residual risk, failed tests, and release readiness in one place.",
            "blocks": [
                {
                    "type": "cards",
                    "title": "Readiness scorecard",
                    "items": [
                        _card("Control coverage", launch_summary["control_coverage"], "neutral", "Fully passing controls versus total control checks."),
                        _card("Missing controls", str(len(launch_summary["missing_controls"])), "warning" if launch_summary["missing_controls"] else "healthy", "Controls not fully satisfied in the current readiness report."),
                        _card("Failed tests", str(launch_summary["failed_tests"]), "healthy", "Known failed tests in the control-plane summary."),
                        _card("Residual risks", str(len(launch_summary["residual_risks"])), "warning" if launch_summary["residual_risks"] else "healthy", "Outstanding remediation or deployment caveats."),
                        _card("Readiness score", str(launch_summary["readiness_score"]), _status_from_launch(readiness_status), "Weighted readiness score derived from current findings."),
                        _card("Verdict", launch_summary["status"].upper(), _status_from_launch(readiness_status), "Go, conditional, or no-go summary for launch gate review."),
                    ],
                },
                {
                    "type": "records",
                    "title": "Findings and residual risks",
                    "items": [
                        *launch_records,
                        *[
                            _record(
                                title="Residual risk",
                                meta="remediation",
                                detail=str(risk),
                                status="warning",
                            )
                            for risk in launch_summary["residual_risks"]
                        ],
                    ],
                },
            ],
        },
        {
            "id": "entry-points",
            "title": "Entry Points",
            "description": "Operator launch points into runtime modules, governance surfaces, and evidence tools.",
            "blocks": [
                {
                    "type": "links",
                    "title": "Modules",
                    "items": [
                        {
                            "label": "Open Chat",
                            "href": "http://localhost:10000",
                            "description": "Launch governed chat flows through the runtime ingress path when Onyx is enabled behind Envoy.",
                            "status": "warning",
                        },
                        {
                            "label": "Open Agents",
                            "href": "http://localhost:10000",
                            "description": "Enter agent workflows through the same governed runtime path.",
                            "status": "warning",
                        },
                        {
                            "label": "Search Knowledge",
                            "href": "http://localhost:6333/dashboard",
                            "description": "Inspect retrieval backend posture and collections in Qdrant.",
                            "status": "healthy",
                        },
                        {
                            "label": "Review Policies",
                            "href": _raw("overlays/myStarterKit/policies/bundles/default/policy.json"),
                            "description": "Review the active runtime policy bundle and integration inventory.",
                            "status": "healthy",
                        },
                        {
                            "label": "Review Evals",
                            "href": "http://localhost:3002",
                            "description": "Open Langfuse for trace and eval drill-down.",
                            "status": "healthy",
                        },
                        {
                            "label": "Review Evidence Pack",
                            "href": _raw("overlays/myStarterKit/artifacts/evidence/reviewer/reviewer_evidence_bundle.json"),
                            "description": "Open the reviewer evidence bundle exported by myStarterKit.",
                            "status": "healthy",
                        },
                        {
                            "label": "Admin / Tenant Settings",
                            "href": "http://localhost:8080",
                            "description": "Identity and tenant administration entry point via Keycloak.",
                            "status": "healthy",
                        },
                    ],
                }
            ],
        },
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "Trust & Security Operations Dashboard for RAG and Autonomous Agents",
        "subtitle": "Dashboard main page -> identity/session -> governed AI runtime -> evidence/analytics",
        "runtime_module": "Onyx is presented as a governed runtime module behind this control plane.",
        "tabs": [
            {"id": "overview", "label": "Overview"},
            {"id": "runtime", "label": "Runtime"},
            {"id": "retrieval", "label": "Retrieval"},
            {"id": "tools-mcp", "label": "Tools & MCP"},
            {"id": "tools-mcp", "label": "Policies"},
            {"id": "evals", "label": "Evals"},
            {"id": "audit-replay", "label": "Audit & Replay"},
            {"id": "launch-gate", "label": "Launch Gate"},
            {"id": "audit-replay", "label": "Evidence Pack"},
            {"id": "entry-points", "label": "Chat / Agents"},
        ],
        "sections": sections,
        "sources": [
            {
                "label": "Policy bundle",
                "href": _raw("overlays/myStarterKit/policies/bundles/default/policy.json"),
                "description": "Policy, retrieval, tool, and integration inventory.",
            },
            {
                "label": "Telemetry sample",
                "href": _raw("telemetry/exports/sample_events.jsonl"),
                "description": "Normalized telemetry events feeding the dashboard summary.",
            },
            {
                "label": "Launch gate report",
                "href": _raw("overlays/myStarterKit/artifacts/logs/launch_gate/starter_launch_readiness_report.json"),
                "description": "Readiness findings consumed by the launch-gate section.",
            },
            {
                "label": "Reviewer evidence bundle",
                "href": _raw("overlays/myStarterKit/artifacts/evidence/reviewer/reviewer_evidence_bundle.json"),
                "description": "Audit and evidence-pack source material.",
            },
            {
                "label": "Grafana operational dashboard spec",
                "href": _raw("telemetry/dashboards/grafana/operational-dashboard-spec.json"),
                "description": "Operational drill-down contract surfaced behind the control plane.",
            },
        ],
    }
