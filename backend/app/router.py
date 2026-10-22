import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx


class ModelUnavailableError(RuntimeError):
    pass


class ModelRouter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=5, read=300, write=30, pool=5),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def list_models(self) -> list[dict[str, Any]]:
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ModelUnavailableError("Ollama is unavailable. Check the local model runtime.") from error

        models = response.json().get("models", [])
        return [
            {
                "id": item["name"],
                "name": item["name"],
                "size": item.get("size"),
                "family": item.get("details", {}).get("family"),
                "parameterSize": item.get("details", {}).get("parameter_size"),
            }
            for item in models
            if isinstance(item.get("name"), str)
        ]

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2,
            },
        }
        if json_mode:
            payload["format"] = "json"

        started = time.perf_counter()
        try:
            async with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ModelUnavailableError("Ollama returned an invalid streaming response.") from error

                    content = chunk.get("message", {}).get("content")
                    if content:
                        yield {"token": content}
                    if chunk.get("done"):
                        yield {
                            "done": True,
                            "promptTokens": int(chunk.get("prompt_eval_count", 0)),
                            "completionTokens": int(chunk.get("eval_count", 0)),
                            "latencyMs": round((time.perf_counter() - started) * 1000),
                        }
        except httpx.HTTPError as error:
            raise ModelUnavailableError(f"Could not complete a request with model {model}.") from error
