#!/usr/bin/env python3
"""Develop harness instructions, then evaluate them on separate tasks."""

import argparse
import asyncio
import hashlib
import json
import random
import secrets
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.harness_engine import BASE_AGENT_INSTRUCTION, HarnessEngine
from backend.app.router import ModelRouter

ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT = ROOT / "docs/experiments/agi-development-task.json"
HELDOUT = ROOT / "docs/experiments/agi-heldout-tasks.json"
MODELS = ("qwen2.5:1.5b-instruct", "gemma2:2b")
CRITERIA = ("calibration", "assumptions", "scenarios", "reasoning", "evidence", "usefulness")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reserve(paths: list[Path]) -> None:
    if len(set(paths)) != len(paths):
        raise ValueError("Output paths must be distinct.")
    for path in paths:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)


async def metadata(router: ModelRouter) -> dict[str, Any]:
    tags = await router.client.get("/api/tags")
    tags.raise_for_status()
    version = await router.client.get("/api/version")
    version.raise_for_status()
    return {
        "ollama_version": version.json()["version"],
        "models": {model["name"]: model for model in tags.json()["models"]},
    }


def study_config(path: Path | None) -> tuple[dict[str, Any] | None, Path, Path]:
    if path is None:
        return None, DEVELOPMENT, HELDOUT
    config = json.loads(path.read_text(encoding="utf-8"))
    return config, ROOT / config["development_task"], ROOT / config["heldout_tasks"]


def study_hashes(config_path: Path, config: dict[str, Any]) -> dict[str, str]:
    paths = {
        "config": config_path,
        "protocol": ROOT / config["protocol"],
        "runner": Path(__file__),
        "router": ROOT / "backend/app/router.py",
    }
    if "reviewer_instructions" in config:
        paths["reviewer_instructions"] = ROOT / config["reviewer_instructions"]
    return {name: sha256(path) for name, path in paths.items()}


async def develop(
    router: ModelRouter, output: Path, models: list[str], config_path: Path | None = None
) -> dict[str, Any]:
    """Only the development task is sent to the proposer and judge."""
    config, development_path, heldout_path = study_config(config_path)
    if config is not None and models != config["models"]:
        raise ValueError("Models must match the study configuration.")
    task_bytes = development_path.read_bytes()
    task = json.loads(task_bytes)
    config_hashes = study_hashes(config_path, config) if config_path is not None and config is not None else None
    heldout_hash = sha256(heldout_path)
    info = await metadata(router)
    missing = [model for model in models if model not in info["models"]]
    if missing:
        raise ValueError(f"Models unavailable: {', '.join(missing)}")
    reserve([output])
    result: dict[str, Any] = {
        "phase": "development",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "engine_sha256": sha256(ROOT / "backend/app/harness_engine.py"),
        "development_task_sha256": hashlib.sha256(task_bytes).hexdigest(),
        "heldout_task_sha256": heldout_hash,
        "model_metadata": info,
        "task": task,
        "iterations": 2,
        "token_budget": 8192,
        "runs": [],
    }
    if config is not None:
        result["study_id"] = config["study_id"]
        result["study_hashes"] = config_hashes
    save(output, result)
    for model in models:
        run: dict[str, Any] = {"model": model, "events": [], "status": "incomplete"}
        result["runs"].append(run)
        engine = HarnessEngine(router, token_budget=8192)
        tokens: list[str] = []
        started = time.monotonic()
        try:
            async for event in engine.run(
                model=model, domain=task["domain"], prompt=task["prompt"], max_iterations=2
            ):
                if event["event"] == "model_token":
                    tokens.append(event["data"]["token"])
                    continue
                if event["event"] == "model_metrics":
                    run["events"].append({"event": "generated_text", "data": {"text": "".join(tokens)}})
                    tokens.clear()
                run["events"].append(event)
                if event["event"] in {"completed", "error"}:
                    run["status"] = event["event"]
                save(output, result)
        except Exception as error:
            run["events"].append({"event": "capture_error", "data": {"message": str(error)}})
            run["status"] = "error"
        finally:
            if tokens:
                run["events"].append({"event": "partial_generated_text", "data": {"text": "".join(tokens)}})
            run["wall_seconds"] = round(time.monotonic() - started, 2)
            save(output, result)
        print(f"{model}: development {run['status']}", flush=True)
    return result


async def answer(router: ModelRouter, model: str, prompt: str, instructions: list[str]) -> dict[str, Any]:
    text = ""
    completion = None
    started = time.monotonic()
    try:
        async for part in router.stream_chat(
            model,
            [
                {"role": "system", "content": "\n".join([BASE_AGENT_INSTRUCTION, *instructions])},
                {"role": "user", "content": prompt},
            ],
            max_tokens=160,
        ):
            text += part.get("token", "")
            if part.get("done"):
                completion = {key: part[key] for key in ("promptTokens", "completionTokens", "latencyMs")}
        if completion is None:
            raise RuntimeError("The model stream ended without usage information.")
        return {"status": "completed", "text": text, "usage": completion, "wall_seconds": round(time.monotonic() - started, 2)}
    except Exception as error:
        return {"status": "error", "text": text, "error": str(error), "wall_seconds": round(time.monotonic() - started, 2)}


async def evaluate(
    router: ModelRouter, development: Path, raw: Path, blind: Path, key: Path, repetitions: int,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Freeze the development output before loading any held-out task."""
    dev = json.loads(development.read_text(encoding="utf-8"))
    if dev.get("phase") != "development":
        raise ValueError("Expected a development-phase record.")
    config, development_path, heldout_path = study_config(config_path)
    if config is not None:
        if dev.get("study_id") != config["study_id"] or dev.get("study_hashes") != study_hashes(config_path, config):
            raise ValueError("Study configuration, protocol or implementation changed after development.")
        if repetitions != config["repetitions"]:
            raise ValueError("Repetitions must match the study configuration.")
    elif dev.get("study_id"):
        raise ValueError("The study configuration is required for this development record.")
    if dev["engine_sha256"] != sha256(ROOT / "backend/app/harness_engine.py"):
        raise ValueError("The engine changed after development; start a new study.")
    if dev["development_task_sha256"] != sha256(development_path):
        raise ValueError("The development task changed after development; start a new study.")
    heldout_bytes = heldout_path.read_bytes()
    if dev.get("heldout_task_sha256") != hashlib.sha256(heldout_bytes).hexdigest():
        raise ValueError("The held-out tasks were not frozen or changed after development; start a new study.")
    selected = []
    skipped = []
    for run in dev["runs"]:
        completed = next((e["data"] for e in run["events"] if e["event"] == "completed"), None)
        if run["status"] == "completed" and completed and completed["harness"]:
            selected.append((run["model"], completed["harness"]))
        else:
            skipped.append({"model": run["model"], "reason": "development failed or no instruction was accepted"})
    if not selected:
        raise ValueError("No completed development run produced accepted instructions; no A/B evaluation possible.")
    info = await metadata(router)
    if info["ollama_version"] != dev["model_metadata"]["ollama_version"]:
        raise ValueError("The Ollama version changed after development; start a new study.")
    for model, _ in selected:
        expected = dev["model_metadata"]["models"][model]["digest"]
        if info["models"].get(model, {}).get("digest") != expected:
            raise ValueError(f"Model {model} is missing or its digest changed after development.")
    tasks = json.loads(heldout_bytes)
    reserve([raw, blind, key])
    seed = secrets.randbits(64)
    randomizer = random.Random(seed)
    result: dict[str, Any] = {
        "phase": "heldout", "development_sha256": sha256(development),
        "heldout_task_sha256": dev["heldout_task_sha256"], "model_metadata": info,
        "repetitions": repetitions, "skipped": skipped, "pairs": [],
    }
    if config is not None:
        result["study_id"] = config["study_id"]
        result["study_hashes"] = dev["study_hashes"]
    reviews: dict[str, Any] = {"instructions": "Compare A and B without consulting the key. Score each criterion 0, 1, or 2; use null when not assessable. Do not review the arithmetic control as a prediction.", "pairs": []}
    mapping: dict[str, Any] = {"seed": seed, "pairs": []}
    save(raw, result)
    save(blind, reviews)
    save(key, mapping)
    for model, instructions in selected:
        for task in tasks:
            for repetition in range(1, repetitions + 1):
                order = ["base", "candidate"]
                randomizer.shuffle(order)
                responses: dict[str, Any] = {}
                for arm in order:
                    responses[arm] = await answer(router, model, task["prompt"], instructions if arm == "candidate" else [])
                pair_id = secrets.token_hex(8)
                side_order = ["base", "candidate"]
                randomizer.shuffle(side_order)
                pair = {
                    "id": pair_id, "model": model, "task_id": task["id"],
                    "repetition": repetition, "generation_order": order, "responses": responses,
                }
                result["pairs"].append(pair)
                mapping["pairs"].append({"id": pair_id, "model": model, "task_id": task["id"], "repetition": repetition, "A": side_order[0], "B": side_order[1]})
                review: dict[str, Any] = {"id": pair_id, "task": task["prompt"]}
                if "kind" in task:
                    review["kind"] = task["kind"]
                for label, arm in zip(("A", "B"), side_order):
                    response = responses[arm]
                    review[label] = {
                        "status": response["status"], "text": response["text"],
                        "scores": {criterion: None for criterion in CRITERIA},
                        "notes": "",
                    }
                review["preference"] = None
                review["preference_notes"] = ""
                reviews["pairs"].append(review)
                save(raw, result)
                save(key, mapping)
                save(blind, reviews)
                print(f"{model} {task['id']} repetition {repetition}: " + ", ".join(f"{arm}={responses[arm]['status']}" for arm in order), flush=True)
    randomizer.shuffle(reviews["pairs"])
    save(blind, reviews)
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    phases = parser.add_subparsers(dest="phase", required=True)
    dev = phases.add_parser("develop")
    dev.add_argument("--output", type=Path, required=True)
    dev.add_argument("--models", nargs="+", default=list(MODELS))
    dev.add_argument("--config", type=Path)
    heldout = phases.add_parser("evaluate")
    heldout.add_argument("--development", type=Path, required=True)
    heldout.add_argument("--raw", type=Path, required=True)
    heldout.add_argument("--blind", type=Path, required=True)
    heldout.add_argument("--key", type=Path, required=True)
    heldout.add_argument("--repetitions", type=int, default=2)
    heldout.add_argument("--config", type=Path)
    args = parser.parse_args()
    if args.phase == "evaluate" and args.repetitions < 1:
        parser.error("--repetitions must be positive")
    router = ModelRouter(args.ollama_url)
    try:
        if args.phase == "develop":
            result = await develop(router, args.output, args.models, args.config)
            if any(run["status"] != "completed" for run in result["runs"]):
                raise SystemExit("Some development runs failed; records were saved. Failed runs cannot be evaluated.")
        else:
            result = await evaluate(router, args.development, args.raw, args.blind, args.key, args.repetitions, args.config)
            if result["skipped"] or any(response["status"] != "completed" for pair in result["pairs"] for response in pair["responses"].values()):
                raise SystemExit("Some models or answers failed; records were saved for review.")
    finally:
        await router.close()


if __name__ == "__main__":
    asyncio.run(main())
