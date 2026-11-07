# Synthetic WorkBuddy experiment

## Protocol (defined before running)

This is a qualitative demonstration, not a benchmark. Run the same synthetic,
non-sensitive task three times with Qwen2.5 1.5B Instruct and three times with
Gemma 2 2B. Use two sequential iterations, a budget of 8,192 tokens, temperature
0.2, and the same local Ollama instance. Preserve failures, decisions, generated
text, token counts, wall time, model digests, and the code revision in
`workbuddy-synthetic-runs.json`. No real people, legal documents, or private
data are involved.

The task says the prototype exists, accessibility and deployment have not
been tested, two engineers are available today, and the budget is unconfirmed.
It asks for three prioritized actions, known versus unknown facts, and a risk,
without inventing a budget or claiming tests are complete.

Evaluate the initial and final responses separately using this fixed rubric:

| Criterion | Pass | Fail |
|---|---|---|
| Three prioritized actions | Three identifiable, ordered actions | Otherwise |
| Known facts | States at least one fact from the task accurately | Otherwise |
| Unknowns | Explicitly identifies at least one untested area or the unknown budget | Otherwise |
| Risk | Identifies at least one plausible risk | Otherwise |
| Unsupported claims | Does not invent a budget or state that accessibility/deployment testing is complete | Otherwise |

These are observable content checks, not a measure of factual correctness,
usefulness in production, or statistically significant improvement. Record
the evidence and limitations for each assessment; a response with no unsupported
claim on these two specific points may still contain other unsupported claims.
The evaluator is separate from the model's automatic judge, but is not
automatically a blinded or independent human reviewer.

Run from the repository root with the documented local Python dependencies and
both models installed:

```sh
python -m scripts.capture_harness_experiment \
  --output docs/experiments/workbuddy-synthetic-runs.json
```

The capture script directly uses the engine and local Ollama, not the public
gateway; inference times are not deployment latency. Its `generated_text`
events retain model outputs in generation order. `propose`, `probe`, `compose`,
and `completed` events retain the decision context and final responses. The
task itself is part of the probe, so these results do not test generalization
to unseen tasks.

After the original six runs, a second six-run exploratory batch repeated the
same protocol without discarding failed runs. A further exploratory batch uses
a new synthetic capacity task (`--scenario capacity`): two engineers each have
three hours and 12 checks take 45 minutes each. The reference arithmetic is
8 checks completed and 4 remaining, assuming no overhead. Three two-iteration
runs per model were planned before running this batch. The different task
requires a separate evaluation; it is not part of the original comparison.

## Results

All data below comes from Ollama on the local host, not the deployed container.
Runs were captured on 2026-11-07. The two launch batches used the engine at
revision `a5bcabb32f1744a34fad8f65571c52627a4fb967`; the capacity batch additionally
used the additive `finalJudgeScore` result field. See each JSON file for the
exact model digests, timestamps, prompts, outputs, judge rationales, and token
counts. Times are wall-clock observations on this host and cannot be compared
directly with the earlier container CPU measurements.

The fixed-rubric assessments below were performed retrospectively by the
assistant using the output text, **not by a human, not blinded, and not by the
model acting as the run's judge**. They are separate content checks, but they
are not an independently validated evaluation. “Pass” for unsupported claims
only covers the two conditions in the rubric, not every possible hallucination.

### Original six runs

| Model | Completed | Failed | Reason for failure |
|---|---:|---:|---|
| Qwen2.5 1.5B | 1/3 | 2/3 | Invalid proposal JSON after retry |
| Gemma 2 2B | 1/3 | 2/3 | Invalid proposal JSON after retry in iteration 2 |

Both completed runs adopted both proposals. Two Gemma runs adopted their first
proposal and failed later; no final result was produced for those runs. All
errors and partial outputs remain in
[`workbuddy-synthetic-runs.json`](workbuddy-synthetic-runs.json).

| Completed run | Initial response | Retained response | Reason for rubric difference |
|---|---:|---:|---|
| Qwen #3 | 3/5 | 5/5 | The initial response has three actions and mentions the engineers, but does not state unknowns or a risk. The retained response includes both. |
| Gemma #2 | 4/5 | 3/5 | The initial response identifies three actions, known/unknown facts, but no risk. The retained response is cut off after the start of the second action and contains no risk. |

The Qwen result is an example of a **proposal accepted by the judge** with a
visible change in the requested structure. In Gemma #2, the second comparison's
judge preferred the candidate, 87.5 versus 82.5, yet the retained response was
incomplete under this rubric. The judge compares two task variants, while this
review checks only the retained response to the original task; these are not
the same evaluation and cannot be treated as directly equivalent scores.

### Additional launch-task observations

In the six-run exploratory repeat, three runs completed and three stopped on
invalid proposal JSON. The complete raw records are in
[`workbuddy-synthetic-exploratory.json`](workbuddy-synthetic-exploratory.json).

| Completed run | Initial response | Retained response | Observation |
|---|---:|---:|---|
| Qwen #2 | 5/5 | 4/5 | The retained answer lists two clear action areas and engineer availability, but its subsequent action list is cut off. It also calls the prototype “functional,” which the task did not establish; the narrow unsupported-claims rubric does not catch that. |
| Qwen #3 | 3/5 | 5/5 | The initial answer is truncated before its unknowns; the retained answer includes actions, knowns, unknowns, and a risk. |
| Gemma #3 | 5/5 | 4/5 | The retained answer is truncated before a third action, although it states a risk. |

### Independent arithmetic check

The separate capacity task has an objective reference: each engineer can do
`180 / 45 = 4` checks, so together they can do **8**, leaving **4**. All six
runs completed. None of the six retained responses correctly states both
numbers. The three Qwen retained answers state 4 completed and 8 remaining;
the Gemma retained answers contain inconsistent or incomplete calculations.
The [complete records](workbuddy-capacity-exploratory.json) preserve the
initial answers too; they also failed to state both correct values.

For example, Qwen capacity run #1 says “4 checks” and “8 checks remaining,”
yet the model's second judgment prefers the candidate, 87.5 versus 82.5. This
is a concrete, independently checkable **disagreement between the answer and
the judge's favorable assessment**, not a measurement of general model
accuracy. The judge compares the current and candidate outputs on two task
variants; the arithmetic check above inspects the final response for the
original task only.

Across all 18 runs, all **26 completed probe comparisons** accepted their
candidate; no real rejected candidate was observed. This small, nonrandom
sample cannot establish the judge's general acceptance rate. A rejected
candidate is covered in `test_rejected_proposal_keeps_base_and_reports_score_not_delta`,
but that is a deterministic mocked test, **not an observed model run**.
There is therefore no genuine rejected example available for a blog post from
these captures.

### Reproduction notes and limits

- The first two JSON files were recorded before the capture tool added Ollama
  version and engine-hash fields. Their recorded model digests and revision
  remain available; the version field must not be inferred retroactively.
- `generated_text` entries capture the actual model output, including malformed
  proposals, and are not polished examples. Engine error events are preserved.
- The displayed final score is the selected score from the **last comparison**,
  not the improvement from the original baseline. The engine can regenerate
  current responses in iteration 2, so that score may not correspond to the
  exact retained response displayed at the end.
- A real human review, blinded or separately conducted, and held-out tasks
  remain future work. Do not treat these examples as legal advice, a ranking
  of the models, benchmark results, or evidence that Harness² itself fails.
