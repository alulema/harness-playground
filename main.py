import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
RUNS: list[dict[str, Any]] = json.loads(
    (BASE_DIR / "src/data/harness2-cached-runs.json").read_text(encoding="utf-8")
)
PROJECT_ID = os.getenv("PROJECT_ID", "")
DEMO_SLOT = os.getenv("DEMO_SLOT", "")

app = FastAPI(title="Harness² Playground", docs_url=None, redoc_url=None)
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.is_dir():
    STATIC_DIR = BASE_DIR / "dist"


class RunRequest(BaseModel):
    scenarioId: str = Field(min_length=1, max_length=100)
    domain: Literal["Legal LAB", "JobBench", "WorkBuddy"]
    prompt: str = Field(min_length=1, max_length=1200)
    mode: Literal["live", "cached"] = "live"


def selected_run(request: RunRequest) -> dict[str, Any]:
    exact_match = next(
        (
            run
            for run in RUNS
            if run["id"] == request.scenarioId and run["domain"] == request.domain
        ),
        None,
    )
    if exact_match is not None:
        return exact_match
    return next(run for run in RUNS if run["domain"] == request.domain)


def encode_event(name: str, payload: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok", "projectId": PROJECT_ID, "demoSlot": DEMO_SLOT}


@app.post("/api/harness/stream")
async def harness_stream(request: RunRequest) -> StreamingResponse:
    run = selected_run(request)

    async def events():
        for step in run["steps"]:
            if request.mode == "live":
                await asyncio.sleep(0.55)
            yield encode_event(step["stage"], step)
        yield encode_event(
            "output",
            {
                "taskId": run["taskId"],
                "domain": run["domain"],
                "baseOutput": run["baseOutput"],
                "optimizedOutput": run["optimizedOutput"],
                "totalImprovement": run["totalImprovement"],
            },
        )
        yield encode_event(
            "completed",
            {
                "taskId": run["taskId"],
                "domain": run["domain"],
                "baseOutput": run["baseOutput"],
                "optimizedOutput": run["optimizedOutput"],
                "totalImprovement": run["totalImprovement"],
            },
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
