# OP-06 analysis

This analysis was reconstructed on 2026-09-08 from the published OP-06 baseline description, the
repository implementation, and the local runs in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md). It is not
presented as a contemporaneous experiment notebook.

## Lexical-baseline failure taxonomy

| Failure family | Why a lexical baseline fails | Intervention in this project | Evidence | What did not move |
| --- | --- | --- | --- | --- |
| Paraphrase and long-tail intents | Exact phrases miss wording variants and tail classes | TF-IDF word/character model and grouped training | ABCD-derived intent accuracy `0.7133` versus the published baseline `0.3748` | The exact hidden-split result is not available locally |
| Workflow-position ambiguity | Intent alone does not determine the next action | State slots, historical action turns, and policy candidate ranking | ABCD-derived action accuracy `0.8158`; invalid internal-policy action rate `0.0000` | This is not the official permitted-actions rate unless cases include that field |
| Noise and hostile text | Typos, controls, role-like text, and injections distort token evidence | Unicode normalization, structured serialization, flags, and human abstention | 35 tests pass; official-format blank/hostile checks return schema-valid responses | Per-noise-type accuracy has not yet been computed from the published files |
| Policy mismatch | Real agents sometimes deviate from written procedure | Keep policy masking explicit and document the gold/policy conflict | Published brief reports roughly 9% gold policy deviation; local policy rate is not comparable | No local reproduction of the official permitted-actions scorer |
| Flat confidence | A high score everywhere does not identify cases needing review | Temperature calibration, margins, and escalation | Historical ECE `0.3726`; top-70 ratio was not recorded in that run | No claim that the `0.85` bar is passed |

The interventions that changed the local result are therefore separable: the trained artifact moved
classification, state/policy masking moved action selection, and normalization protected runtime
behavior. The confidence intervention is inconclusive until the official top-70 report is run.

## Required next measurement

Run the published `train.jsonl.gz`, `dev.jsonl`, `dev_noisy.jsonl`, and `hostile.jsonl` through the
service, save one prediction per `id`, and run the published `grader.py`. Report clean and noisy
metrics by noise type, permitted-action violation rate against the gold's own rate, top-70 error
ratio, human-routing fraction, and evaluator-machine p95/cost. Those numbers must not be substituted
with the local smoke corpus.