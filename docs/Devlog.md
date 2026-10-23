# Harness² Playground — Devlog

## 2026-10-20 — Initial demo implementation

- Confirmed this repository is the demo source; the personal website consumes its published image rather than hosting the app source.
- Read `DEMO_INTEGRATION.md` and aligned the app to its portable-container contract: root route, fixed port `8080`, no app-level auth or TLS, stateless runtime, public scenario data only.
- Added an Astro/React interface for scenario selection, Propose → Probe → Compose progress, probe metrics, and base-versus-optimized output comparison.
- Added a FastAPI SSE endpoint that streams the bundled illustrative traces; cached browser replay remains available when the stream fails.
- Integrated the live site theme and optional details panel. Documented the architecture and the important limitation that the current traces are precomputed rather than real model evaluations.

## Live open-weight runtime

- Replaced the fixture-only API with a bounded Propose → Probe → Compose demonstration backed by Ollama and the open-weight Qwen2.5 1.5B Instruct model.
- Added model discovery, token and latency accounting, a per-run token budget, a single-run concurrency limit, and per-IP rate limiting.
- Kept cached examples as an explicitly labeled replay/fallback. Updated the About panel, README, and handoff to distinguish live model-judge estimates from objective benchmarks and from Google's original implementation.
- Added deterministic async engine tests and exercised a complete local SSE run against Ollama. The Docker image now bundles Ollama and the model; building and publishing that image is still pending.
