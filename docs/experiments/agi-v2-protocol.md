# AGI futures v2: exploratory comparison

## Status and scope

This is a new study, `agi-futures-v2`, not a replacement or continuation of
the [pilot](agi-study.md). Its question is whether instructions selected by
this repository's simplified Propose → Probe → Compose cycle improve
answers to different AGI-related questions. This does not predict AGI or
reproduce the full Harness² framework. The proposer and judge use the same
model; a successful technical run is not evidence of improved answers.

The study is exploratory. The authors can read the tasks and the models may
have encountered related material during training. A hash recorded at the
start detects later changes but does not independently establish a prior
registration or conceal the tasks. If the protocol is independently
timestamped before development, record where and when separately.

## Design fixed before execution

- One [development task](agi-v2-development-task.json) about AGI and
  employment; only that task and the engine's development variation are sent
  to the proposer and judge. Two iterations per model, budget 8,192 tokens,
  Qwen2.5 1.5B Instruct and Gemma 2 2B. One development run per model. Keep
  all outputs, invalid attempts, retries, decisions and errors.
- Six [held-out qualitative questions](agi-v2-heldout-tasks.json) and two
  independent arithmetic controls, different from the pilot. For each model
  that completes development with at least one accepted instruction, generate
  three paired repetitions of each task, base versus base plus the frozen
  instructions. No candidate is invented for failed development or all
  rejections. Pair order and A/B presentation are randomized separately.
- Both arms use the same prompt, model digest, Ollama version, temperature
  0.2 and 160-token output limit. The baseline asks for at most 70 words;
  the model may ignore that request. Sampling seeds are not controlled. The
  router does not expose completion reason, so token-limit truncation may be
  unmarked. Inference is sequential; timing effects remain possible.
- The runner hashes the configuration, protocol, development and held-out
  task files, reviewer instructions, engine, runner and router before development, and checks them
  before evaluation. It records model digests and Ollama version. It refuses
  to overwrite records. A changed implementation requires a new study.
  Technical debugging before this study is not a study run.

## Blinded review

Recruit two independent human reviewers where feasible. Each gets a separate
copy of the same blind packet and the [reviewer instructions](agi-v2-reviewer-instructions.md),
not the raw results, model labels or key. Copies must be kept separate. The
packet is blind only with respect to labels; answer text may reveal origin.
Neither reviewer should see the other review before both are complete. A
review is not complete until an actual reviewer supplies scores, preferences
and notes; an unavailable second reviewer must be explicitly reported.

Score each qualitative response on each applicable criterion: **0** absent or
misleading, **1** partially addressed, **2** clearly addressed; use `null`
when not assessable and explain why. Record A/B/tie/cannot assess preference
and rationale. Failed or truncated responses remain visible; report them.

| Criterion | What to assess |
|---|---|
| calibration | Acknowledges uncertainty without asserting an arrival date or inevitable outcome. |
| assumptions | Identifies conditions underpinning conclusions. |
| scenarios | Considers relevant alternatives without implying equal likelihood. |
| reasoning | Connects reasons to conclusions and relevant objections. |
| evidence | Distinguishes verifiable current claims from hypotheses without fabricated citations. |
| usefulness | Answers the specific question clearly and concretely. |

Reviewers should flag claims requiring independent fact-checking, not pretend
they were verified. Generated rationales do not reveal internal reasoning.
Arithmetic controls are graded separately after qualitative review, against
the answers below. Neither the controls nor their keys should be included
when calculating qualitative scores. Control correctness requires both
counts and a consistent calculation, not merely one correct number.

## Analysis specified in advance

For each model, reviewer, qualitative task and repetition, compute candidate
minus base for each criterion with two non-null scores. Average the available
paired criterion differences within a response pair, then average the three
repetitions within each task; finally average the six task means with equal
weight. Report each criterion, task, repetition, preference and missing value
as well. Do not treat repetitions as independent tasks or pool the two models.

For a *descriptive improvement signal*, require two completed independent
reviews, all six tasks with all three paired repetitions available, both
reviewers' overall task-weighted mean differences at least **+0.25** points
on the 0–2 scale, and candidate preferences exceeding base preferences for
each reviewer. This threshold is a practical convention chosen in advance,
not a validated effect size or statistical significance test. An incomplete
comparison cannot meet the criterion. Report mixed or negative outcomes, all
technical failures, disagreements and all skipped models. This small sample
cannot justify general claims or eliminate chance and evaluator bias.

Score arithmetic separately by manual inspection for every response: labs
**12 completed, 6 remaining**; reports **18 completed, 7 remaining**.
Report all responses and correct counts by model and arm. Do not use a model
judge as the arithmetic verifier and do not infer a review from a blank form.

## Execution

Requires local Ollama and both models. Use new paths; do not overwrite or
rerun a failed development selectively. `evaluate` exits nonzero if a model
was skipped or an answer failed, preserving its records.

```sh
python -m scripts.agi_study develop --config docs/experiments/agi-v2-config.json \
  --output docs/experiments/agi-v2-development-results.json
python -m scripts.agi_study evaluate --config docs/experiments/agi-v2-config.json \
  --development docs/experiments/agi-v2-development-results.json \
  --repetitions 3 --raw docs/experiments/agi-v2-heldout-results.json \
  --blind docs/experiments/agi-v2-blind-review.json \
  --key docs/experiments/agi-v2-review-key.json
```

Give reviewers only the packet and the reviewer-instructions file, excluding
the arithmetic key and the raw records. Secure the key until both reviews are
complete.
