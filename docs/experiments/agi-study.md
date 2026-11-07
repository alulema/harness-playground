# AGI futures: study protocol

## Question and limits

Does a harness instruction selected on one AGI-futures task improve responses to
other tasks under a prespecified review rubric? This is a small exploratory
study, not a way to predict humanity's future, establish AGI's arrival date, or
reproduce the full Harness² research framework. Qwen and Gemma may have been
trained on similar public topics; "held out" means not passed to this study's
proposer or selection process, not unseen during model pretraining.

## Prespecified design

1. Hash the [held-out task file](agi-heldout-tasks.json) before development
   begins and preserve that hash in the development record. Hashing does not
   send its contents to the model. Use the single [development task](agi-development-task.json), which asks
   for conditional scenarios about humanity's future with AGI. For each model,
   run the existing Propose → Probe → Compose engine once with two sequential
   iterations and an 8,192-token budget. Record every generation, judge decision,
   rejection, error, and completion. Do not retry failed studies or choose the
   best of multiple runs after seeing their results.
2. Freeze the completed instructions selected by the engine before loading the
   held-out prompts for evaluation. Failed development runs and
   completed runs with no accepted instruction are reported and skipped, not
   silently replaced with a fictional candidate. The engine is stateless across
   model runs; the held-out prompts are never supplied during development.
3. For each eligible model, run every held-out task twice with the base
   instruction and twice with the base plus that model's frozen instructions.
   Randomize generation order within each pair and A/B presentation separately.
   Generation uses the same model, prompt, 160-token cap and temperature 0.2
   in both arms. Sampling means repeated runs can vary; seeds are not controlled
   by the current Ollama router.
   The shared base instruction asks for no more than 70 words, which limits
   the detail available for nuanced answers.
4. Retain every response and error. The raw record identifies conditions; the
   blind packet contains only opaque pair IDs, tasks, answers and blank review
   fields. Give a reviewer **only the blind packet and this rubric**, not the
   raw record or mapping. Blinding is imperfect: text may reveal its origin.
   Keep the answer key separate until review is complete. A human review has
   not happened until an actual reviewer supplies scores.

The five open-ended tasks cover employment, science, access concentration,
evidence that would change a conclusion, and facts versus hypotheses. A sixth
task is an arithmetic control: 2 engineers × 180 minutes ÷ 45 minutes gives
**8 checks completed, 4 remaining**. Score this separately by direct inspection,
not using the speculative-futures rubric. The control is not a forecast and
does not validate performance on the five open-ended tasks.

## Human review rubric

For each response, give each applicable criterion **0** (absent or misleading),
**1** (partially addressed), or **2** (clearly addressed). Use `null` where not
applicable; document the evidence and any uncertainty in notes.

| Criterion | What to look for |
|---|---|
| Calibration | Acknowledges relevant uncertainty without claiming an AGI date or inevitable outcome. |
| Assumptions | Identifies conditions on which conclusions depend. |
| Scenarios | Considers relevant alternatives without assuming equal likelihood. |
| Reasoning | Connects stated reasons to conclusions and considers an objection when appropriate. |
| Evidence | Distinguishes verifiable current claims from hypotheses; does not invent citations. |
| Usefulness | Addresses the question clearly and concretely without overclaiming. |

Record a per-pair preference (`A`, `B`, `tie`, or `cannot assess`) and an
explanation; incomplete/error responses should remain visible. Reviewers
should flag unsupported factual statements, but this study does not supply or
retrieve a fixed evidence corpus. Do not grade current factual accuracy as
verified without checking independent sources. The model's explanations are
generated rationales, not proof of its internal reasoning.

After review, use the separate key to compare results by model and condition.
Report all cases, skipped models, errors, incomplete answers and disagreements;
do not report a post-selected example as representative. Two repetitions
and five qualitative tasks per model are insufficient for broad or statistical
claims. Do not describe a rejected candidate unless a recorded model decision
actually rejected it.

## Running

Requires the repository's Python dependencies, a local Ollama server, and both
bundled models. Execute from the repository root. Output paths must be new;
the script refuses to overwrite an existing record.

```sh
python -m scripts.agi_study develop --output docs/experiments/my-development.json
python -m scripts.agi_study evaluate \
  --development docs/experiments/my-development.json \
  --raw docs/experiments/my-heldout.json \
  --blind docs/experiments/my-blind-review.json \
  --key docs/experiments/my-review-key.json
```

The development phase sends only the development task to the models and hashes
the held-out file without supplying its content. Evaluation checks the
engine, development-task and held-out hashes, Ollama version, and selected
model digests against the frozen record before using held-out prompts. The
hash makes later changes detectable but is not independent proof of when the
protocol was registered. It records file hashes, timestamps,
model metadata, output text, token usage, durations and failures. The output
key includes the randomized mapping; **do not send it to the reviewer**.
The evaluation exits nonzero when any model was skipped or answer failed, while
preserving partial data. Outputs are saved during the run, but resuming a partial
study is not implemented. Start a separately labeled study instead of
overwriting one, and report both.

The router does not capture the model's completion reason, so responses at
the token limit may be truncated without an explicit truncation indicator.

## Initial local runs

The initial [pilot development record](agi-development-results.json) was
created before the script recorded a held-out task hash. Qwen completed with
two accepted instructions; Gemma failed with an unsupported proposal
component. That pilot cannot be evaluated under the revised hash check.

After adding the check, a separately recorded
[development run](agi-development-frozen.json) repeated both models using the
same tasks. Qwen again produced two accepted instructions; Gemma again failed
on an unsupported proposal component. This is an exploratory follow-on after
the pilot outcomes were known, not an independently preregistered replication.
Both attempts are retained rather than selecting a favorable one. The tasks
were not supplied to the model during development, but the team had already
authored them and there was no independent timestamped preregistration.

The [held-out record](agi-heldout-results.json) contains 12 Qwen pairs
(six tasks, two repetitions each); all 24 answers completed. Gemma was
skipped because its development run failed, so the evaluation command exited
nonzero as designed. The [blank review packet](agi-blind-review.json) and
[separate mapping](agi-review-key.json) are saved; no human review has yet
been performed. Do not send the mapping or raw record to the reviewer.

On the arithmetic control, neither base response nor either candidate
response gave the correct result of 8 completed and 4 remaining. Both
candidate answers said 3 completed and 9 remaining. The two base answers
also said 3 completed: one said 0 remaining, and the other did not state a
remainder and introduced an unsupported sequential-work constraint. These
are four observed answers, not a general performance estimate.
