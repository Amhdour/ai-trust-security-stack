# AI Trust & Security Stack (Umbrella Repository)

This repository is the **umbrella control-plane and integration overlay** for an AI Trust & Security stack built around upstream projects and `myStarterKit`.

## Design intent

- Treat `upstream/*` as third-party source of truth.
- Treat `overlays/myStarterKit` as the governance overlay baseline.
- Keep local platform logic additive in:
  - `overlays/`
  - `adapters/`
  - `policies/`
  - `telemetry/`
  - `launch-gate/`
  - `compose/`
  - `docs/`
  - `scripts/`

## Current structure snapshot

- `upstream/`: pinned submodules for Keycloak, Envoy, Onyx, OPA, Vault, Qdrant, optional gVisor, Langfuse, Grafana, and Superset.
- `overlays/myStarterKit/`: governance-overlay submodule.
- `overlays/governance-overlay/`: local, additive overlay contracts and integration wiring (this repo).
- `adapters/`: Python adapters for policy/runtime/retrieval/secrets/sandbox/observability bridges.
- `policies/`: OPA policy bundles and tests.
- `telemetry/`: event schema, sinks, exporters, and dashboard artifacts.
- `launch-gate/`: evidence-based readiness evaluator.
- `compose/`: local development stack definitions.
- `.devcontainer/`: Codespaces/devcontainer setup.

## Phase status

Execution plan tracking and phase notes are stored under `docs/phases/`.
