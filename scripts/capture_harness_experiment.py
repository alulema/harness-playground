#!/usr/bin/env python3
"""Capture bounded, synthetic Harness² runs for qualitative analysis."""

import argparse
import asyncio
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from backend.app.harness_engine import HarnessEngine
from backend.app.router import ModelRouter

PROMPT = (
    "A small team must prepare a public demo for Friday. The prototype exists, "
    "but accessibility and deployment have not been tested. There are two "
    "engineers available today and no confirmed budget. Suggest three prioritized "
    "next actions, state what is known versus unknown, and identify one risk. "
    "Do not invent a budget or claim testing is complete."
)
CAPACITY_PROMPT = (
    "A synthetic demo launch has 12 independent checks. Each check takes 45 "
    "minutes. Two engineers each have exactly 3 hours available today. Calculate "
    "how many checks they can complete and how many remain, assuming no parallel "
    "overhead. Give three prioritized actions and identify one risk. Do not invent "
    "additional engineers or time."
)
MODELS = ("qwen2.5:1.5b-instruct", "gemma2:2b")


async def capture(router: ModelRouter, model: str, repetitions: int, prompt: str, save: Callable[[dict], None]) -> None:
    for repetition in range(1, repetitions + 1):
        started = datetime.now(timezone.utc).isoformat()
        start_time = time.perf_counter()
        events = []
        token_parts = []
        engine = HarnessEngine(router, token_budget=8192)
        try:
            async for event in engine.run(
                model=model, domain="WorkBuddy", prompt=prompt, max_iterations=2
            ):
                if event["event"] == "model_token":
                    token_parts.append(event["data"]["token"])
                    continue
                if event["event"] == "model_metrics":
                    events.append({"event": "generated_text", "data": {"text": "".join(token_parts)}})
                    token_parts.clear()
                events.append(event)
        except Exception as error:
            events.append({"event": "capture_error", "data": {"message": str(error)}})
        if token_parts:
            events.append({"event": "partial_generated_text", "data": {"text": "".join(token_parts)}})
        record = {
            "model": model,
            "repetition": repetition,
            "started_at_utc": started,
            "wall_seconds": round(time.perf_counter() - start_time, 2),
            "events": events,
        }
        save(record)
        status = next((e["event"] for e in reversed(events) if e["event"] in {"completed", "error", "capture_error"}), "incomplete")
        print(f"{model} run {repetition}: {status} ({record['wall_seconds']}s)", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--scenario", choices=("launch", "capacity"), default="launch")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    router = ModelRouter(args.ollama_url)
    try:
        tags_response = await router.client.get("/api/tags")
        tags_response.raise_for_status()
        version_response = await router.client.get("/api/version")
        version_response.raise_for_status()
        models = {item["name"]: item for item in tags_response.json()["models"]}
        missing = [model for model in MODELS if model not in models]
        if missing:
            raise RuntimeError(f"Models not available in Ollama: {', '.join(missing)}")
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        prompt = PROMPT if args.scenario == "launch" else CAPACITY_PROMPT
        results = {
            "description": "Synthetic qualitative experiment; not a benchmark.",
            "revision": revision,
            "engine_sha256": hashlib.sha256(Path("backend/app/harness_engine.py").read_bytes()).hexdigest(),
            "ollama_version": version_response.json()["version"],
            "prompt": prompt,
            "domain": "WorkBuddy",
            "iterations": 2,
            "token_budget": 8192,
            "temperature": 0.2,
            "models": {model: models[model] for model in MODELS},
            "runs": [],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)

        def save(record: dict) -> None:
            results["runs"].append(record)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")

        for model in MODELS:
            await capture(router, model, args.repetitions, prompt, save)
    finally:
        await router.close()
    if any(not any(event["event"] == "completed" for event in run["events"]) for run in results["runs"]):
        raise SystemExit("One or more runs did not complete; partial results were saved.")


if __name__ == "__main__":
    asyncio.run(main())
