# Handoff: Harness² Playground → personal-website

Este demo se integra en `alulema/personal-website` como una imagen pública en GHCR, siguiendo el contrato de [`docs/DEMO_INTEGRATION.md`](docs/DEMO_INTEGRATION.md).

## Manifiesto para registrar

| Campo | Valor |
|---|---|
| `projectId` | `harness2-playground` |
| Nombre (ES) | `Playground Harness² de agentes IA` |
| Nombre (EN) | `Harness² AI Agent Playground` |
| Repo público | `https://github.com/alulema/harness-playground` |
| Imagen pública GHCR | `ghcr.io/alulema/harness-playground:latest` |
| Puerto del contenedor | `8080` |
| `shareable` | `true` |
| Secretos de provisión | Ninguno |
| Recursos extra / sidecars | Ninguno |

La imagen nueva integra Astro/React, FastAPI, Ollama y los pesos abiertos de `qwen2.5:1.5b-instruct`. Es autocontenida y no requiere una API externa. Los pesos ocupan unos 986 MB; la imagen construida localmente ocupa unos 1,2 GB (el tamaño publicado puede variar). Reserva memoria suficiente para inferencia local (se recomiendan al menos 4 GiB).

## Tareas de integración en personal-website

1. Registra `harness2-playground` con el nombre, imagen, puerto y valor `shareable` indicados arriba.
2. Añade la tarjeta al catálogo público de demos con nombres en español e inglés, descripción y `githubUrl` apuntando al repositorio.
3. Configura el gateway para enviar tráfico a `/` y mantener SSE en streaming; no agregues prefijos, autenticación ni TLS dentro del demo.
4. No declares secretos. La imagen contiene solo código público y pesos abiertos.
5. Verifica provisión, navegación, estilos y ejecución SSE desde el sitio, además del teardown de la sesión.

## Contrato implementado

- Sirve la interfaz desde `GET /` en `0.0.0.0:8080`.
- `GET /healthz` confirma que Ollama responde e informa `PROJECT_ID`, `DEMO_SLOT` y el modelo predeterminado.
- `GET /api/v1/models` enumera los modelos locales disponibles.
- `POST /api/v1/stream` recibe modelo, dominio, prompt, iteraciones y presupuesto de tokens; transmite eventos SSE de Propose → Probe → Compose.
- Un proceso supervisor inicia Ollama, espera a que responda, inicia FastAPI y detiene ambos procesos cuando termina el contenedor.
- El panel `DEMO_INFO` explica en español e inglés el runtime, el método y sus límites.

El modo Live ejecuta una demostración acotada con el mismo modelo local como generador y juez. Las puntuaciones son estimaciones subjetivas, no benchmarks. El proyecto ilustra el patrón Harness²; no contiene la implementación original de Google ni un optimizador validado. El modo Cached reproduce una traza de ejemplo y no llama al modelo.

## Estado

El código de ejecución en vivo y una imagen local autocontenida ya se verificaron con Qwen; el contenedor completó un ciclo SSE. Aún debe publicarse la imagen nueva en GHCR y actualizarse el registro del sitio. La imagen `latest` publicada anteriormente corresponde a la versión previa con trazas precalculadas; no la uses para afirmar que el demo live ya está desplegado.

## Referencias

- Contrato: [`docs/DEMO_INTEGRATION.md`](docs/DEMO_INTEGRATION.md)
- Desarrollo y ejecución: [`README.md`](README.md)
- Workflow de publicación: [`.github/workflows/publish-image.yml`](.github/workflows/publish-image.yml)
- Pull request anterior ya integrado a `main`: [alulema/harness-playground#1](https://github.com/alulema/harness-playground/pull/1)
