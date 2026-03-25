# AI Trust & Security Stack Architecture Spec

## 1) Standing stack (logical order)

`Keycloak -> Envoy -> Onyx runtime (+ myStarterKit governance overlay) -> OPA -> Vault -> Qdrant -> optional gVisor -> Langfuse -> Grafana/Superset`

This order represents trust/security dependency and control delegation, not always a strict synchronous call chain.

## 2) Architecture intent

- Provide a secure runtime path for AI requests through identity, policy, and governance controls.
- Separate **control-plane decisions** from **runtime-plane execution**.
- Emit evidence continuously for post-request assurance and launch-gate decisions.

## 3) Trust boundaries

1. **External boundary** (client/user -> platform ingress)
   - Boundary crossing: untrusted external traffic into Envoy ingress.
   - Primary controls: session/token verification (Keycloak), ingress authn/authz routing (Envoy).

2. **Runtime boundary** (Envoy -> Onyx runtime)
   - Boundary crossing: authenticated requests enter application reasoning/runtime.
   - Primary controls: myStarterKit governance checks + policy hooks.

3. **Policy boundary** (Onyx/myStarterKit <-> OPA)
   - Boundary crossing: policy queries and decisions.
   - Primary controls: explicit allow/deny decisions, policy context validation, decision logging.

4. **Secret boundary** (Onyx/tooling <-> Vault)
   - Boundary crossing: access to protected credentials or keys.
   - Primary controls: least-privilege secret retrieval, short-lived access, auditable access paths.

5. **Data boundary** (Onyx/tooling <-> Qdrant)
   - Boundary crossing: retrieval of embeddings/documents for RAG workflows.
   - Primary controls: retrieval authorization, scoped indexes/collections, query/result observability.

6. **Sandbox boundary** (Onyx/tooling <-> gVisor, optional)
   - Boundary crossing: risky code/tool execution into isolated runtime.
   - Primary controls: syscall/process isolation and constrained execution profile.

7. **Evidence boundary** (all services -> Langfuse -> Grafana/Superset -> launch gate)
   - Boundary crossing: operational/security/evaluation telemetry into evidence systems.
   - Primary controls: trace completeness, immutable-ish audit trails, KPI/alert visibility.

## 4) Core control points

- **CP1 Identity/session establishment**: Keycloak issues/validates identity context.
- **CP2 Ingress enforcement**: Envoy performs ingress policy/auth checks and routing.
- **CP3 Runtime governance**: myStarterKit enforces trust/security controls before/through reasoning.
- **CP4 Policy decision**: myStarterKit and/or OPA authorize actions, tools, and data access.
- **CP5 Secret retrieval gate**: Vault access only when secrets are required.
- **CP6 Retrieval gate**: Qdrant access only when retrieval is required.
- **CP7 Risky execution sandboxing**: gVisor used when execution risk threshold is met.
- **CP8 Continuous evidence emission**: Langfuse telemetry throughout request lifecycle.
- **CP9 Post-request assurance**: Grafana/Superset views consumed by myStarterKit launch gate.

## 5) Data flow summary

- Request payload + identity context enters via Envoy.
- Onyx runtime receives request and context.
- Onyx/myStarterKit conditionally accesses:
  - Vault (secrets), only when needed.
  - Qdrant (retrieval), only when needed.
  - gVisor (sandbox), only for risky execution paths.
- Response and runtime metadata return through ingress path.
- Telemetry, policy decisions, and evaluations are emitted to Langfuse continuously.

## 6) Policy flow summary

- Policy context assembled from request, identity/session claims, action intent, and runtime state.
- myStarterKit applies local governance policies first (where configured).
- OPA provides centralized policy decisioning for allow/deny/constraints.
- Final decision governs whether Onyx can continue, call tools, read secrets, retrieve data, or execute in sandbox.
- Policy decision outcomes are logged as evidence signals.

## 7) Evidence flow summary

- During request: traces, policy decisions, retrieval/tool events, and security-relevant state emitted to Langfuse.
- Post request: Langfuse outputs feed dashboards/views in Grafana/Superset.
- Launch-gate consumes these evidence views/signals to allow, restrict, or block future launches.
