import asyncio
import json
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.staticfiles import StaticFiles

from .harness_engine import HarnessEngine, TokenBudgetExceeded
from .router import ModelRouter, ModelUnavailableError

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:1.5b-instruct")
MAX_TOKEN_BUDGET = 8192
MAX_ITERATIONS = 2
RATE_LIMIT_REQUESTS = 3
RATE_LIMIT_WINDOW_SECONDS = 60


class RunRequest(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    domain: Literal["Legal LAB", "JobBench", "WorkBuddy"]
    prompt: str = Field(min_length=1, max_length=1200)
    maxIterations: int = Field(default=1, ge=1, le=MAX_ITERATIONS)
    tokenBudget: int = Field(default=4096, ge=1024, le=MAX_TOKEN_BUDGET)

    @field_validator("prompt")
    @classmethod
    def prompt_must_have_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be empty.")
        return value.strip()


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        now = time.monotonic()
        async with self.lock:
            history = self.requests[key]
            while history and now - history[0] > RATE_LIMIT_WINDOW_SECONDS:
                history.popleft()
            if len(history) >= RATE_LIMIT_REQUESTS:
                return False
            history.append(now)
            return True


limiter = SlidingWindowLimiter()
run_semaphore = asyncio.Semaphore(1)
HEARTBEAT_SECONDS = 10
router = ModelRouter(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await router.close()


app = FastAPI(title="Harness² Playground", docs_url=None, redoc_url=None, lifespan=lifespan)


def client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()[:64]
    if request.client:
        return request.client.host
    return "unknown"


def encode_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/healthz")
async def health() -> dict[str, Any]:
    try:
        await router.list_models()
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {
        "status": "ok",
        "projectId": os.getenv("PROJECT_ID", ""),
        "demoSlot": os.getenv("DEMO_SLOT", ""),
        "defaultModel": DEFAULT_MODEL,
    }


@app.get("/api/v1/models")
async def list_models() -> dict[str, Any]:
    try:
        models = await router.list_models()
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    for model in models:
        model["bundled"] = model["id"] == DEFAULT_MODEL
        model["licenseNote"] = "Open-weight model served locally by Ollama."
    return {"models": models, "defaultModel": DEFAULT_MODEL}


@app.post("/api/v1/stream")
async def stream_optimization(request: Request, body: RunRequest) -> StreamingResponse:
    if not await limiter.check(client_key(request)):
        raise HTTPException(
            status_code=429,
            detail=f"Limit is {RATE_LIMIT_REQUESTS} runs per minute. Please wait before trying again.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    try:
        models = await router.list_models()
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    available_models = {model["id"] for model in models}
    if body.model not in available_models:
        raise HTTPException(
            status_code=422,
            detail="Selected model is not available in this Ollama instance.",
        )
    if run_semaphore.locked():
        raise HTTPException(status_code=429, detail="Another optimization is already running.")

    async def events():
        # The semaphore is taken inside the generator so it is always released,
        # and the engine runs in a task so keepalives flow during slow model calls.
        await run_semaphore.acquire()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        done = object()

        async def produce() -> None:
            # A 2-iteration run measured ~3.7k tokens; keep headroom for judge retries.
            engine = HarnessEngine(router, max(body.tokenBudget, 3000 * body.maxIterations))
            try:
                async for item in engine.run(
                    model=body.model,
                    domain=body.domain,
                    prompt=body.prompt.strip(),
                    max_iterations=body.maxIterations,
                ):
                    await queue.put(encode_event(item["event"], item["data"]))
            except TokenBudgetExceeded as error:
                await queue.put(
                    encode_event("error", {"message": str(error), "code": "token_budget_exceeded"})
                )
            except ModelUnavailableError as error:
                await queue.put(
                    encode_event("error", {"message": str(error), "code": "model_unavailable"})
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                await queue.put(
                    encode_event(
                        "error",
                        {"message": f"Optimization failed: {error}", "code": "optimization_failed"},
                    )
                )
            finally:
                await queue.put(done)

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield ": keepalive\n\n"
                    continue
                if item is done:
                    break
                yield item
        finally:
            task.cancel()
            run_semaphore.release()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.is_dir():
    STATIC_DIR = BASE_DIR / "dist"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
