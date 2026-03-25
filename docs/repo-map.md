# Repository Map

## Purpose
This document describes the umbrella repository layout for the AI Trust & Security stack.

## Top-level directories
- `.devcontainer/` — Codespaces and local dev environment definitions.
- `compose/` — Container composition and environment overlays.
- `docs/` — Architecture, boundaries, and operational documentation.
- `scripts/` — Validation/bootstrap helper scripts.
- `adapters/` — Integration adapters between upstream services.
- `policies/` — Policy artifacts (e.g., trust/security policy bundles).
- `telemetry/` — Observability configuration and dashboards.
- `launch-gate/` — Startup readiness and enforcement checks.
- `overlays/` — Local overlays/customizations layered over upstream components.
- `upstream/` — Third-party source mirrors/submodules.

## Notes
- `upstream/*` is treated as third-party and should remain unchanged unless strictly necessary.
- New implementation should be additive in umbrella-owned folders.
