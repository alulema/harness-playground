# Harness² AI Agent Playground

An interactive, self-contained demo of recursive agent optimization. Explore how system prompts, memory, and tool guidance can evolve through the **Propose → Probe → Compose** loop.

The frontend is built with Astro, React, Tailwind CSS, and Recharts. A small FastAPI service serves the static app and streams scenario traces over Server-Sent Events. The included traces are illustrative and precomputed: live mode streams them progressively; cached mode replays them in the browser. Neither mode calls an LLM or runs the original Harness² optimizer.

## Run with Docker

```sh
docker build -t harness2-playground .
docker run --rm -p 8080:8080 \
  -e PROJECT_ID=harness2-playground \
  -e DEMO_SLOT=demo01 \
  harness2-playground
```

Open `http://localhost:8080/`. The service listens on `0.0.0.0:8080`, serves the UI at `/`, and exposes `/healthz`. It is designed to run behind a reverse proxy or gateway that provides authentication and TLS; the app itself deliberately has neither.

## Container image

The GitHub Actions workflow builds and validates the image on pull requests to `main`. On pushes to `main`, it publishes `ghcr.io/alulema/harness-playground:latest`; on version tags (`v*`), it publishes the matching tag and commit SHA. The image targets `linux/amd64` and listens on port `8080`.

To run a published image:

```sh
docker pull ghcr.io/alulema/harness-playground:latest
docker run --rm -p 8080:8080 ghcr.io/alulema/harness-playground:latest
```

The first package publication may require setting the GHCR package visibility to **Public** in GitHub Packages before an unauthenticated deployment can pull it.

## Develop locally

Prerequisites: Node.js 22+, npm, Python 3.13+, and Docker.

```sh
npm install
npm run dev
```

Install the Python requirements and start FastAPI in one terminal:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

Then run `npm run dev` in a second terminal and open the Astro URL. The dev server proxies `/api` requests to FastAPI on port 8080. The default frontend API endpoint is `/api/harness/stream`. To build the frontend against a different endpoint, set `PUBLIC_HARNESS_STREAM_URL` before `npm run build`. If the live endpoint cannot connect or closes before its completion event, the browser falls back to the bundled scenario trace.

## Scenarios and limitations

`src/data/harness2-cached-runs.json` contains public evaluation examples for Legal LAB, JobBench, and WorkBuddy. Add a scenario there with the same shape as the existing entries to extend the demo. Prompts are accepted for interaction, but custom prompts select an example trace by domain and do not trigger inference. Outputs and scores are illustrative, not legal, hiring, or operational advice.

```sh
npm run check
npm run build
```
