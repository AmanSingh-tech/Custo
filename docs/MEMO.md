# Submission memo

## Residual risk

The largest residual risk is that the trained classifier and candidate policy may perform well on
the public ABCD-derived development corpus while misclassifying a hidden intent or recommending
an inappropriate next action under a changed procedure. Confidence is also not yet demonstrated
against the official confidence-error-ratio scorer: the available ECE is `0.3726`, and the recorded
baseline predates the top-70 ratio measurement.

## Who bears the cost

Customers bear the immediate cost of a wrong or delayed support recommendation. Support agents bear
the cost of unnecessary escalations and review queues. The service owner bears the operational and
reputational cost if a forbidden action crosses the policy boundary. The current design puts the
highest-cost uncertainty on the human-review path rather than executing account changes.

## Pause and handoff condition

Pause rollout or send the case to a person when confidence is below threshold, intent or action is
ambiguous, the policy has no valid candidate, the conversation contains hostile or corrupted input,
the state contains a contradiction, or the selected action explicitly requires human review. A
procedure change or a two-intent request that conflicts with the current policy is also a human route
until the policy version, precedence, and regression tests are updated.

## What the evidence supports

The repository supports a tested MVP claim: 35 tests pass, the development baseline has `0.0000`
invalid policy-action rate, and the recorded clean-to-noisy action gap is `0.0033`. It does not yet
support a claim of qualification on the hidden evaluator or production-ready confidence calibration.
The local reproduce/load rehearsal measured a `51.428 ms` p95 at concurrency 8 and zero external API
cost; those figures are not a promise about evaluator hardware or hosted-model pricing. The fraction
of official messages routed to a human must be reported after running the published clean/noisy data,
because the hidden distribution is not in this repository.

## Assistance disclosure

Coding-agent assistance was used for repository inspection, implementation support, and organizing
the evidence records. I independently reviewed the implementation, ran the cited test command, and
checked the baseline figures against the existing report. The submission does not rely on AI-text
detection or a claim that generated text proves authorship; the technical conversation should use
the raw runs and code paths as evidence.
