# Harness² Playground — Devlog

## 2026-10-20 — Initial demo implementation

- Confirmed this repository is the demo source; the personal website consumes its published image rather than hosting the app source.
- Read `DEMO_INTEGRATION.md` and aligned the app to its portable-container contract: root route, fixed port `8080`, no app-level auth or TLS, stateless runtime, public scenario data only.
- Added an Astro/React interface for scenario selection, Propose → Probe → Compose progress, probe metrics, and base-versus-optimized output comparison.
- Added a FastAPI SSE endpoint that streams the bundled illustrative traces; cached browser replay remains available when the stream fails.
- Integrated the live site theme and optional details panel. Documented the architecture and the important limitation that the current traces are precomputed rather than real model evaluations.

## 2026-10-21 to 2026-10-23 — Live runtime, open models, and deployment handoff

### Moving from replay to actual inference

The initial playground streamed precomputed examples. The goal then changed: make the demo perform a real, bounded Propose → Probe → Compose loop in this repository, with the personal website consuming the finished container image. An initial attempt started implementation in the website repository; it was stopped, its uncommitted demo files were cleaned up, and the work continued in this repository as requested. This kept the product boundary clear: the website hosts the demo, while this repository owns its UI, API, model runtime, and image.

- Replaced the fixture-only API with FastAPI and an Ollama-backed live engine. Added model discovery, SSE events, token and latency accounting, an iteration cap, a token budget, one-run-at-a-time concurrency, and per-IP rate limiting.
- Kept cached examples as a clearly labeled replay option. Documented that the live judge reuses the selected model, so scores are subjective comparative estimates rather than benchmarks; this demonstrates the Harness² pattern and is not Google's original optimizer.
- Chose a self-contained open-weight model runtime over hosted-model APIs to meet the autonomy requirement without API secrets or external inference calls. The initial target was a compact model that could fit the website's constrained container allocation; larger models such as Gemma 2 27B were not practical within that memory and latency budget.
- Bundled Qwen2.5 1.5B Instruct as the default open-weight model. The container runs without model API credentials or an external inference service.
- Added async engine tests and exercised a complete live SSE run locally. Built and ran the container, then verified its UI, health endpoint, model API, and stream.

### Slow runs and misleading “Stopped” status

Two iterations took several minutes on CPU. When a run paused at the second iteration's judge step, the UI's terminal status looked like a stop, but investigation showed that the model was still generating slowly; local reproductions completed. The exact error displayed in the original browser session was not captured, so its specific cause cannot be asserted retrospectively.

Testing also exposed genuine robustness issues around small models' structured output: a judge could return the JSON schema envelope instead of answer values, causing strict validation to reject the judgment. The final implementation:

- Adds an example answer to the judge prompt and unwraps schema-envelope JSON for both proposals and judgments.
- Retries malformed proposal/judge output once and accepts an empty rationale with a neutral fallback.
- Sends an SSE keepalive comment every 10 seconds during slow model calls, runs inference separately from the stream consumer, and releases the single-run semaphore on disconnect/cancellation.
- Reserves a minimum of 3,000 tokens per requested iteration so the selected budget does not starve a judge/retry near the end of a run.
- Shows elapsed time and the current phase in the activity panel to make long CPU inference less likely to look frozen.

Two-iteration local CPU tests completed with both models: approximately 4.5 minutes for Qwen2.5 1.5B and 7 minutes for Gemma 2 2B. These are measurements from the local test machine, not service-level guarantees; latency varies with CPU, memory, and load.

### Adding Gemma 2 2B

Gemma 2 2B was added as a selectable second model while retaining Qwen as the default. An initial live run revealed a Gemma-specific schema-envelope response that the original parser rejected; the shared unwrapping logic fixed it, after which Gemma completed two iterations locally.

Both model weights are baked into the image so model selection works without a network download or API key at runtime. The published image grew to approximately 2.8 GB. The hosting configuration was therefore raised to 2 vCPU and 4 GiB (the Container Apps Consumption ceiling used for this demo), with a startup probe allowing about five minutes for image/model startup. Gemma's measured multi-iteration latency is longer than Qwen's.

### Website integration and publication

- Published the live container for anonymous pull from `ghcr.io/alulema/harness-playground:latest`; the image manifest was verified after publication.
- Updated the `personal-website` demo registration, bilingual catalog description, resource sizing, startup probe, and Devlog. The changes were merged to the website's `main` branch via [personal-website#199](https://github.com/alulema/personal-website/pull/199); its Build and Deploy check passed. The separate [personal-website#198](https://github.com/alulema/personal-website/pull/198) fixed an unescaped apostrophe in the catalog description that broke Astro's build.
- Updated this repository's handoff with the two bundled models, measured local timings, image state, and remaining deployment checks in [harness-playground#4](https://github.com/alulema/harness-playground/pull/4).

The website's build/deploy workflow and local containers were verified. A full live session through the deployed website gateway—including startup time for the larger image, long-running SSE behavior, and session expiry during a two-iteration Gemma run—remains to be verified in that hosting environment.

## 2026-11-07 — Qualitative evaluation and clearer claims

- Captured three batches of synthetic local runs with Qwen and Gemma, including
  failed runs, generated text, judge decisions, token usage, and model metadata.
  The protocol, qualitative review, objective arithmetic check, and raw data
  are in [`experiments/workbuddy-synthetic.md`](experiments/workbuddy-synthetic.md).
- The arithmetic task exposed a gap between favorable judge scores and correct
  answers; no real rejected candidate occurred in these batches. These
  observations are exploratory and do not establish benchmark performance.
- Clarified the UI's system-prompt-only implementation, subjective judge
  scores, cached illustrative results, and effective token-budget floor. Added
  `finalJudgeScore` while retaining the legacy API field for compatibility.
