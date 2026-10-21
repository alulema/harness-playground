# Harness² Playground — Devlog

## 2026-10-20 — Initial demo implementation

- Confirmed this repository is the demo source; the personal website consumes its published image rather than hosting the app source.
- Read `DEMO_INTEGRATION.md` and aligned the app to its portable-container contract: root route, fixed port `8080`, no app-level auth or TLS, stateless runtime, public scenario data only.
- Added an Astro/React interface for scenario selection, Propose → Probe → Compose progress, probe metrics, and base-versus-optimized output comparison.
- Added a FastAPI SSE endpoint that streams the bundled illustrative traces; cached browser replay remains available when the stream fails.
- Integrated the live site theme and optional details panel. Documented the architecture and the important limitation that the current traces are precomputed rather than real model evaluations.
