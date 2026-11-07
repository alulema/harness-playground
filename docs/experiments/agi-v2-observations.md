# AGI futures v2: execution record

The [protocol](agi-v2-protocol.md) and its task and implementation hashes
were captured before this run. They were not independently timestamped or
registered, and the study authors could read the held-out tasks. The
[technical check](agi-v2-technical-check.json) is separate from the study.
The [pilot](agi-study.md) and its records remain unchanged.

The [development record](agi-v2-development-results.json) contains two
accepted Qwen instructions. Gemma produced a proposal but both attempts at
its first judge response were truncated invalid JSON, so its development
failed and it was excluded from the A/B phase. This is a technical failure,
not a recorded rejection. The accepted Qwen instructions both refer to
employment; they are applied unchanged to the other tasks, which may affect
transfer and should be considered when reviewing answers.

After the A/B run, the judge prompt and retry were improved to request a short
rationale and allow more output tokens. A second, separate
[technical check](agi-v2-judge-technical-check.json) completed for both
models; one success per model does not prove reliability on the study task.
The [engine patch used for v2](agi-v2-engine-used.patch), applied to the
recorded Git revision, reconstructs the recorded engine hash. Because the
current engine has since changed, the runner will refuse a new evaluation of
this development record under the hash check. The original captured results
remain valid records; any further study must be separately identified.

The [held-out record](agi-v2-heldout-results.json) contains 24 Qwen pairs
(8 tasks × 3 repetitions), with 48 completed streams. A completed stream
does not guarantee an untruncated answer. The
[blind packet](agi-v2-blind-review.json) and
[review instructions](agi-v2-reviewer-instructions.md) are ready for two
independent reviewers; the [mapping](agi-v2-review-key.json) must not be
given to them before they finish. **No human qualitative reviews have been
performed.** No improvement claim can be made from these blank forms.

## Arithmetic controls

Manual inspection using the protocol's rule (both counts and a consistent
calculation required) found:

| Task | Base correct | Candidate correct |
|---|---:|---:|
| Labs, answer 12 completed / 6 remaining | 2/3 | 1/3 |
| Reports, answer 18 completed / 7 remaining | 2/3 | 1/3 |
| Total | 4/6 | 2/6 |

For labs, candidate repetition 2 gives both correct counts and calculations
before its final sentence cuts off; repetition 3 cuts off before giving a
result. For reports, candidate repetitions 2 and 3 say 18 completed but 2
remaining. These are small, repeated observations, not a population estimate.
The observations concern the controls only and do not establish qualitative
performance on the AGI questions.
