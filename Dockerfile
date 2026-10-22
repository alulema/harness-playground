FROM ollama/ollama:0.6.8 AS model
ENV OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/models
RUN set -eu; \
    mkdir -p /models; \
    ollama serve >/tmp/ollama.log 2>&1 & \
    server_pid=$!; \
    trap 'kill "$server_pid" 2>/dev/null || true' EXIT; \
    ready=0; \
    attempt=0; \
    while [ "$attempt" -lt 60 ]; do \
      if ollama list >/dev/null 2>&1; then ready=1; break; fi; \
      attempt=$((attempt + 1)); \
      sleep 2; \
    done; \
    if [ "$ready" -ne 1 ]; then cat /tmp/ollama.log; exit 1; fi; \
    ollama pull qwen2.5:1.5b-instruct

FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY astro.config.mjs tsconfig.json ./
COPY src ./src
RUN npm run build

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DEFAULT_MODEL=qwen2.5:1.5b-instruct \
    OLLAMA_BASE_URL=http://127.0.0.1:11434 \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/opt/ollama/models \
    OLLAMA_KEEP_ALIVE=5m \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    LD_LIBRARY_PATH=/usr/lib/ollama
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && mkdir -p /usr/lib/ollama /opt/ollama/models \
    && chown -R app:app /opt/ollama
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=model /bin/ollama /usr/local/bin/ollama
COPY --from=model /usr/lib/ollama/*.so* /usr/lib/ollama/
COPY --chown=app:app --from=model /models /opt/ollama/models
COPY main.py .
COPY backend ./backend
COPY --from=frontend --chown=app:app /build/dist ./static
USER app
EXPOSE 8080
CMD ["python", "-m", "backend.container"]
