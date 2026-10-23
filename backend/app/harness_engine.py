import json
import math
from collections.abc import AsyncIterator
from typing import Any

from .router import ModelRouter

DOMAIN_PROBES = {
    "Legal LAB": "Review the same matter again. Identify missing facts, distinguish the document's wording from legal interpretation, and avoid inventing obligations.",
    "JobBench": "Review the same candidates again. Compare only job-related evidence, identify missing information, and do not infer protected or personal characteristics.",
    "WorkBuddy": "Revisit the same plan. Separate known facts from assumptions, surface the next decision, and order actions by dependency.",
}
def unwrap_schema_echo(value: Any) -> Any:
    """Some small models wrap their answer in the schema's own {"type", "properties"} envelope."""
    if isinstance(value, dict) and isinstance(value.get("properties"), dict) and "type" in value:
        return value["properties"]
    return value


BASE_AGENT_INSTRUCTION = "You are an AI assistant. Complete the task directly and concisely in no more than 70 words."

SYSTEM_SCHEMA = {
    "type": "object",
    "properties": {
        "component": {"type": "string", "enum": ["system_prompt", "memory", "tool_guidance"]},
        "instruction": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["component", "instruction", "reason"],
}

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "base_scores": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 100}, "minItems": 2, "maxItems": 2},
        "candidate_scores": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 100}, "minItems": 2, "maxItems": 2},
        "rationale": {"type": "string"},
    },
    "required": ["base_scores", "candidate_scores", "rationale"],
}


class TokenBudgetExceeded(RuntimeError):
    pass


class HarnessEngine:
    def __init__(self, router: ModelRouter, token_budget: int) -> None:
        self.router = router
        self.token_budget = token_budget
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.latency_ms = 0

    @property
    def tokens_used(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @staticmethod
    def estimate_tokens(messages: list[dict[str, str]]) -> int:
        return math.ceil(sum(len(message["content"]) for message in messages) / 3)

    def _check_budget(self, messages: list[dict[str, str]], max_tokens: int) -> int:
        estimated_prompt_tokens = self.estimate_tokens(messages)
        available = self.token_budget - self.tokens_used - estimated_prompt_tokens
        if available <= 0:
            raise TokenBudgetExceeded("Token budget reached before the next model call.")
        return min(max_tokens, available)

    async def generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 160,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        reserved_tokens = self._check_budget(messages, max_tokens)
        text = ""
        completion = None
        async for item in self.router.stream_chat(
            model,
            messages,
            max_tokens=reserved_tokens,
            json_mode=json_mode,
        ):
            token = item.get("token")
            if token:
                text += token
                yield {"type": "model_token", "token": token}
            if item.get("done"):
                completion = item

        if completion is None:
            raise RuntimeError("The model stream ended without usage information.")
        actual_prompt = completion["promptTokens"] or self.estimate_tokens(messages)
        actual_completion = completion["completionTokens"] or math.ceil(len(text) / 3)
        self.prompt_tokens += actual_prompt
        self.completion_tokens += actual_completion
        if self.tokens_used > self.token_budget:
            raise TokenBudgetExceeded("The model response exceeded the remaining token budget.")
        self.latency_ms += completion["latencyMs"]
        yield {
            "type": "model_metrics",
            "promptTokens": actual_prompt,
            "completionTokens": actual_completion,
            "latencyMs": completion["latencyMs"],
            "totalTokens": self.tokens_used,
        }
        yield {"type": "generated", "text": text}

    async def _complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 160,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        async for item in self.generate(model, messages, max_tokens=max_tokens, json_mode=json_mode):
            if item["type"] == "generated":
                self._last_generated = item["text"]
            else:
                yield item

    async def run(
        self,
        *,
        model: str,
        domain: str,
        prompt: str,
        max_iterations: int,
    ) -> AsyncIterator[dict[str, Any]]:
        tests = [prompt, f"{prompt}\n\nEvaluation variation: {DOMAIN_PROBES[domain]}"]
        baseline_outputs: list[str] = []
        best_outputs: list[str] = []
        instructions: list[str] = []
        current_score = 0.0
        accepted_iterations = 0
        self._last_generated = ""

        yield {
            "event": "run_started",
            "data": {
                "model": model,
                "domain": domain,
                "maxIterations": max_iterations,
                "tokenBudget": self.token_budget,
                "evaluation": "same-model-judge",
            },
        }

        for index, test_prompt in enumerate(tests):
            yield {
                "event": "baseline",
                "data": {"testCase": index + 1, "totalCases": len(tests), "status": "generating"},
            }
            messages = [
                {"role": "system", "content": BASE_AGENT_INSTRUCTION},
                {"role": "user", "content": test_prompt},
            ]
            async for item in self._complete(model, messages, max_tokens=96):
                yield {"event": item["type"], "data": item}
            baseline_outputs.append(self._last_generated)

        best_outputs = baseline_outputs.copy()
        initial_baseline = baseline_outputs[0]

        for iteration in range(1, max_iterations + 1):
            if iteration == 1:
                current_outputs = baseline_outputs.copy()
            else:
                current_outputs = []
                for test_prompt in tests:
                    current_messages = [
                        {"role": "system", "content": "\n".join([BASE_AGENT_INSTRUCTION, *instructions])},
                        {"role": "user", "content": test_prompt},
                    ]
                    async for item in self._complete(model, current_messages, max_tokens=96):
                        yield {"event": item["type"], "data": item}
                    current_outputs.append(self._last_generated)

            proposal_prompt = (
                "Improve an AI agent's written instructions for the task below. Propose exactly one concise, "
                "actionable instruction that could measurably improve the agent across task variations. Do not "
                "answer the task. Return exactly one JSON object matching this schema, with every key present: "
                f"{json.dumps(SYSTEM_SCHEMA)}\n\n"
                f"Domain: {domain}\nTask: {prompt}\n"
                f"Current harness instructions: {json.dumps(instructions, ensure_ascii=False)}"
            )
            yield {
                "event": "propose",
                "data": {"iteration": iteration, "component": "system_prompt", "status": "generating"},
            }
            for attempt in range(2):
                async for item in self._complete(
                    model,
                    [{"role": "user", "content": proposal_prompt}],
                    max_tokens=120,
                    json_mode=True,
                ):
                    yield {"event": item["type"], "data": item}
                try:
                    proposal = unwrap_schema_echo(json.loads(self._last_generated))
                    if not isinstance(proposal, dict):
                        raise ValueError("The proposal must be a JSON object.")
                    component = proposal.get("component")
                    raw_instruction = proposal.get("instruction")
                    raw_reason = proposal.get("reason")
                    if not isinstance(component, str) or component not in {"system_prompt", "memory", "tool_guidance"}:
                        raise ValueError("Unsupported harness component.")
                    if not isinstance(raw_instruction, str) or not isinstance(raw_reason, str):
                        raise ValueError("The proposal must include string instruction and reason fields.")
                    instruction = raw_instruction.strip()
                    reason = raw_reason.strip()
                    if not instruction or len(instruction) > 500:
                        raise ValueError("The proposed instruction must be between 1 and 500 characters.")
                    break
                except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError) as error:
                    if attempt == 0:
                        continue
                    yield {
                        "event": "error",
                        "data": {"message": f"The model produced an invalid harness proposal: {error}"},
                    }
                    return

            yield {
                "event": "propose",
                "data": {
                    "iteration": iteration,
                    "component": component,
                    "instruction": instruction,
                    "reason": reason,
                    "status": "ready",
                },
            }

            candidate_instructions = [*instructions, instruction]
            candidate_outputs: list[str] = []
            for index, test_prompt in enumerate(tests):
                yield {
                    "event": "probe",
                    "data": {"iteration": iteration, "testCase": index + 1, "totalCases": len(tests), "status": "generating"},
                }
                messages = [
                    {"role": "system", "content": "\n".join([BASE_AGENT_INSTRUCTION, *candidate_instructions])},
                    {"role": "user", "content": test_prompt},
                ]
                async for item in self._complete(model, messages, max_tokens=96):
                    yield {"event": item["type"], "data": item}
                candidate_outputs.append(self._last_generated)

            judge_prompt = (
                "You are evaluating two versions of an AI assistant on two test cases. Score each output from 0 "
                "to 100 for task completion, accuracy, relevance, and adherence to the task's domain requirements. "
                "Use the same rubric for both versions. Scores are comparative estimates, not objective facts. "
                "Return exactly one JSON object matching this schema, with every key present: "
                f"{json.dumps(JUDGE_SCHEMA)}\n"
                'Respond with values, not the schema itself. Example response: '
                '{"base_scores": [70, 65], "candidate_scores": [80, 72], "rationale": "Candidate is more specific."}\n\n'
                f"Domain: {domain}\n"
                f"Case 1 task: {tests[0]}\nCurrent output: {current_outputs[0]}\nCandidate output: {candidate_outputs[0]}\n\n"
                f"Case 2 task: {tests[1]}\nCurrent output: {current_outputs[1]}\nCandidate output: {candidate_outputs[1]}"
            )
            yield {
                "event": "probe",
                "data": {"iteration": iteration, "status": "judging", "evaluation": "same-model-judge"},
            }
            for attempt in range(2):
                async for item in self._complete(
                    model,
                    [{"role": "user", "content": judge_prompt}],
                    max_tokens=100,
                    json_mode=True,
                ):
                    yield {"event": item["type"], "data": item}
                try:
                    judgment = unwrap_schema_echo(json.loads(self._last_generated))
                    if not isinstance(judgment, dict):
                        raise ValueError("The judgment must be a JSON object.")
                    base_scores = judgment.get("base_scores")
                    candidate_scores = judgment.get("candidate_scores")
                    rationale = judgment.get("rationale") or "No rationale provided."
                    if (
                        not isinstance(base_scores, list)
                        or not isinstance(candidate_scores, list)
                        or len(base_scores) != 2
                        or len(candidate_scores) != 2
                        or any(type(score) is not int or not 0 <= score <= 100 for score in [*base_scores, *candidate_scores])
                        or not isinstance(rationale, str)
                    ):
                        raise ValueError("The judge must return two integer scores per version (0–100) and a rationale.")
                    base_score = sum(base_scores) / 2
                    candidate_score = sum(candidate_scores) / 2
                    rationale = rationale.strip()
                    break
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                    if attempt == 0:
                        continue
                    yield {"event": "error", "data": {"message": f"The model produced an invalid probe judgment: {error}"}}
                    return

            accepted = candidate_score > base_score
            current_score = candidate_score if accepted else base_score
            yield {
                "event": "probe",
                "data": {
                    "iteration": iteration,
                    "baseScores": base_scores,
                    "candidateScores": candidate_scores,
                    "baseScore": base_score,
                    "candidateScore": candidate_score,
                    "deltaScore": candidate_score - base_score,
                    "accepted": accepted,
                    "rationale": rationale,
                    "status": "complete",
                },
            }

            if accepted:
                instructions = candidate_instructions
                best_outputs = candidate_outputs
                accepted_iterations += 1
            yield {
                "event": "compose",
                "data": {
                    "iteration": iteration,
                    "component": component,
                    "instruction": instruction,
                    "accepted": accepted,
                    "harness": instructions,
                    "status": "complete",
                },
            }

        yield {
            "event": "completed",
            "data": {
                "model": model,
                "domain": domain,
                "baseOutput": initial_baseline,
                "optimizedOutput": best_outputs[0],
                "harness": instructions,
                "totalImprovement": current_score,
                "acceptedIterations": accepted_iterations,
                "metrics": {
                    "promptTokens": self.prompt_tokens,
                    "completionTokens": self.completion_tokens,
                    "totalTokens": self.tokens_used,
                    "latencyMs": self.latency_ms,
                    "iterations": max_iterations,
                },
                "evaluation": "same-model-judge",
            },
        }
