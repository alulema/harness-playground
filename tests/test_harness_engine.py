import json
import unittest
from collections.abc import AsyncIterator
from typing import Any

from backend.app.harness_engine import HarnessEngine, TokenBudgetExceeded


class FakeRouter:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        request = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "json_mode": json_mode,
        }
        self.requests.append(request)
        content = messages[-1]["content"]
        if "Improve an AI agent" in content:
            output = json.dumps({
                "component": "system_prompt",
                "instruction": "State what is known and what remains uncertain.",
                "reason": "Separates evidence from assumptions.",
            })
        elif "You are evaluating" in content:
            output = json.dumps({
                "base_scores": [60, 60],
                "candidate_scores": [80, 80],
                "rationale": "The candidate is clearer.",
            })
        else:
            output = "optimized answer" if "State what is known" in messages[0]["content"] else "base answer"

        yield {"token": output}
        yield {
            "done": True,
            "promptTokens": 10,
            "completionTokens": 5,
            "latencyMs": 20,
        }


class RejectingRouter(FakeRouter):
    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        if "You are evaluating" in messages[-1]["content"]:
            yield {"token": json.dumps({
                "base_scores": [60, 60],
                "candidate_scores": [50, 50],
                "rationale": "The candidate is less clear.",
            })}
            yield {"done": True, "promptTokens": 10, "completionTokens": 5, "latencyMs": 20}
            return
        async for item in super().stream_chat(
            model, messages, max_tokens=max_tokens, json_mode=json_mode
        ):
            yield item


class HarnessEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_probes_keep_the_user_task_context_and_compose_improved_rule(self) -> None:
        router = FakeRouter()
        engine = HarnessEngine(router, token_budget=8192)

        events = [item async for item in engine.run(
            model="qwen-test",
            domain="WorkBuddy",
            prompt="Plan a two-day research trip.",
            max_iterations=1,
        )]

        result = next(item["data"] for item in events if item["event"] == "completed")
        self.assertEqual(result["baseOutput"], "base answer")
        self.assertEqual(result["optimizedOutput"], "optimized answer")
        self.assertEqual(result["acceptedIterations"], 1)
        self.assertEqual(result["finalJudgeScore"], 80)
        self.assertEqual(result["totalImprovement"], result["finalJudgeScore"])
        self.assertEqual(len(result["harness"]), 1)
        self.assertTrue(any(
            "Plan a two-day research trip." in request["messages"][-1]["content"]
            and "Evaluation variation:" in request["messages"][-1]["content"]
            for request in router.requests
        ))
        self.assertTrue(any(
            item["event"] == "compose" and item["data"]["accepted"] is True
            for item in events
        ))

    async def test_rejected_proposal_keeps_base_and_reports_score_not_delta(self) -> None:
        engine = HarnessEngine(RejectingRouter(), token_budget=8192)
        events = [item async for item in engine.run(
            model="qwen-test",
            domain="WorkBuddy",
            prompt="Plan a two-day research trip.",
            max_iterations=1,
        )]
        result = next(item["data"] for item in events if item["event"] == "completed")
        probe = next(item["data"] for item in events if item["event"] == "probe" and item["data"]["status"] == "complete")
        self.assertFalse(probe["accepted"])
        self.assertEqual(probe["deltaScore"], -10)
        self.assertEqual(result["finalJudgeScore"], 60)
        self.assertEqual(result["optimizedOutput"], result["baseOutput"])
        self.assertEqual(result["harness"], [])

    async def test_token_budget_stops_before_making_an_unaffordable_call(self) -> None:
        router = FakeRouter()
        engine = HarnessEngine(router, token_budget=1)

        with self.assertRaises(TokenBudgetExceeded):
            _ = [item async for item in engine.run(
                model="qwen-test",
                domain="WorkBuddy",
                prompt="A task.",
                max_iterations=1,
            )]

        self.assertEqual(router.requests, [])


if __name__ == "__main__":
    unittest.main()
