# Harness² AI Agent Playground

An interactive demonstration of agent-instruction optimization through **Propose → Probe → Compose**. Live mode uses a local open-weight model served by Ollama: it proposes a harness instruction, tests the current and candidate instructions on the user's task and a task variation, and adopts the candidate only when the same model's judge scores it higher. Cached mode replays an example without running inference.

This is an educational implementation inspired by the Harness² pattern, not Google's original implementation or a validated optimizer. The same model generates and judges results, so the scores are subjective estimates—not objective benchmark results.

## Run with Docker

The image contains the Astro/React UI, FastAPI service, Ollama runtime, and the `qwen2.5:1.5b-instruct` (default) and `gemma2:2b` model weights. It runs on CPU and requires no model API key or external inference service.

```sh
docker build -t harness2-playground .
docker run --rm -p 8080:8080 \
  -e PROJECT_ID=harness2-playground \
  -e DEMO_SLOT=demo01 \
  harness2-playground
```

Open `http://localhost:8080/`. The app listens on `0.0.0.0:8080`, serves the UI at `/`, exposes `/healthz`, and streams live optimization events from `POST /api/v1/stream`. `GET /api/v1/models` lists available local Ollama models. The container starts Ollama and the API together and waits for Ollama readiness before starting the API.

Allow several gigabytes of memory for local inference; 4 GiB or more is recommended. The bundled model is about 986 MB, and the locally built image is about 1.2 GB (registry size varies). A live run can take a few minutes on CPU; one iteration is selected by default, and a second iteration is available for a deeper, slower run. The app is designed for an internal ingress behind the demo gateway, which provides authentication and TLS; the app itself deliberately has neither.

## Container image

The GitHub Actions workflow builds and validates the image on pull requests to `main`. On pushes to `main`, it publishes `ghcr.io/alulema/harness-playground:latest`; on version tags (`v*`), it publishes the matching tag and commit SHA. The image targets `linux/amd64` and listens on port `8080`.

To run a published image:

```sh
docker pull ghcr.io/alulema/harness-playground:latest
docker run --rm -p 8080:8080 ghcr.io/alulema/harness-playground:latest
```

The GHCR package must be **Public** for the demo infrastructure to pull it without credentials. Only public application code and open model weights are included in the image.

## Develop locally

Prerequisites: Node.js 22+, npm, Python 3.13+, Ollama, and (for the full container) Docker.

Pull the default model and start Ollama:

```sh
ollama pull qwen2.5:1.5b-instruct
ollama pull gemma2:2b   # optional second model
ollama serve
```

In a second terminal, start the API:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

In a third terminal, start Astro:

```sh
npm install
npm run dev
```

Open the Astro URL shown in the terminal. Astro proxies `/api` requests to FastAPI on port `8080`. Set `OLLAMA_BASE_URL` if Ollama is listening elsewhere and `DEFAULT_MODEL` if you want a different default; the selected model must already be available in that Ollama instance.

## Runtime limits and evaluation

- Maximum of two optimization iterations and 8,192 tokens per run; the UI offers 2,048, 4,096, or 8,192-token budgets.
- One iteration is selected by default to keep live runs shorter; two iterations are available when a deeper run is preferred.
- One concurrent run and three runs per minute per client IP.
- The bundled default is Qwen2.5 1.5B Instruct; Gemma 2 2B is also bundled and selectable (the model list is read from Ollama, and `BUNDLED_MODELS` marks bundled entries). Live runs make multiple model calls; latency depends on available CPU and memory.
- Each probe includes the original task context plus a domain-specific variation. No external tools or data sources are called.
- The same model proposes instructions, generates responses, and judges current versus candidate outputs. A higher model-judge score is not proof of better real-world performance.
- Cached mode is a precomputed illustrative trace. If the live API is unavailable before an SSE event arrives, the UI replays the cached example and labels it accordingly.
- Outputs are not legal, hiring, or operational advice. Do not submit sensitive personal or confidential information.

## Checks

```sh
npm run check
npm run build
python -m unittest discover -s tests -v
```
