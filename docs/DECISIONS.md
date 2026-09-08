# Decision log

The evidence-backed entries below were reconstructed on 2026-09-08 from the repository,
test suite, baseline report, and recorded command results. They are not contemporaneous notes.
Raw commands and outputs are in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## D-001: evaluator-facing route

`POST /triage` is the primary route. `/v1/triage` is an alias. The JSON response contains only
`intent`, `action`, `confidence`, and `needs_human`; version metadata is returned in headers.

## D-002: safe runnable fallback

The repository boots without external data or network access by using deterministic keyword,
state, and policy components. This fallback exists for development and security tests. Official
quality claims require a model trained and evaluated on approved data.

## D-003: recommendation-only boundary

The service recommends actions but has no credentials or tools that execute them.

## D-004: policy enforcement

The action model can rank only candidates returned by the policy engine. Unknown intent, no valid
candidate, or artifact mismatch fails toward human review.

## D-005: artifact-required production inference

Production inference requires both `OP06_MODEL_PATH` and `OP06_POLICY_PATH`. The bundled keyword
model and example policy are restricted to explicit developer-demo mode through
`OP06_ALLOW_DEMO_MODEL=1`; they cannot silently service a production request.

## D-006: ABCD state representation

ABCD action events are injected into later training prefixes as role-tagged historical workflow
events. This preserves chronological no-future-leakage while allowing the action ranker to learn
the difference between otherwise similar conversation positions.

## D-007: Policy-mask the action model (OP-06)

**Initial hypothesis:** A trained action model should be allowed to choose the best action directly,
because unconstrained ranking may improve action accuracy.

**Options considered:** (1) let the model choose from every registered action; (2) let the model
rank only actions permitted by the policy engine; (3) use policy priority only and omit a learned
ranker.

**Constraint:** An invalid or operationally unsafe action is more costly than a small accuracy loss,
and the service must never recommend globally forbidden actions.

**Experiment and observation:** The policy-mask implementation was exercised by the full test suite
and the ABCD-derived baseline. The baseline report records `0.0000` invalid policy-action rate
while action accuracy reached `0.8158`; the raw run is [R-2026-09-08-02](EXPERIMENT_LOG.md#r-2026-09-08-02).

**Decision:** Choose option 2. The model may rank candidates, but the policy engine owns the action
boundary and falls back toward human review when no valid candidate exists.

**Reverse condition:** Reverse this decision only if an approved evaluator demonstrates that the
policy boundary is systematically wrong for a documented action family and a replacement boundary
passes forbidden-action, adversarial, and paired-case tests.

## D-008: Keep the deterministic fallback explicit (OP-06)

**Initial hypothesis:** A keyword/state fallback would be useful for local development, but it might
be acceptable as a silent production fallback when a model artifact is unavailable.

**Options considered:** (1) silently fall back to keywords; (2) permit the fallback only with an
explicit demo flag and require a trained artifact in production; (3) refuse to run in all modes
without a trained artifact.

**Constraint:** Reproducible local tests need a no-network implementation, while production quality
claims must not be made using embedded labels.

**Experiment and observation:** The production-path test verifies that missing model configuration
raises an error, while demo fixtures set `OP06_ALLOW_DEMO_MODEL=1`; the complete suite passed 35
tests. This supports option 2 and rejects a silent fallback. See
[R-2026-09-08-01](EXPERIMENT_LOG.md#r-2026-09-08-01).

**Decision:** Choose option 2. The keyword classifier is a named development mode; trained model
and policy artifacts are required for production inference.

**Reverse condition:** Reverse this decision if the submission contract explicitly defines the
keyword model as the qualification model, or if an approved trained artifact can be made available
for every supported deployment environment and the explicit fallback no longer adds test value.

## D-009: Do not claim calibrated confidence from the current baseline

**Initial hypothesis:** The temperature-calibrated baseline would provide decision-grade confidence
because calibration is fitted on a development split.

**Options considered:** (1) publish confidence as production-ready; (2) publish ECE and Brier score
as evidence but withhold the official confidence-error-ratio claim; (3) remove confidence entirely
until the official scorer exists.

**Constraint:** The official confidence-error-ratio definition and hidden evaluator were not supplied,
and the measured ECE is materially worse than the classification metrics.

**Experiment and observation:** The held-out report shows ECE `0.3726` and Brier score `0.3066`,
despite intent accuracy `0.7133` and action accuracy `0.8158`. The official confidence-error-ratio
gate therefore cannot be reproduced; see [R-2026-09-08-03](EXPERIMENT_LOG.md#r-2026-09-08-03).

**Decision:** Choose option 2. Report the available calibration metrics, explicitly mark the official
score as unverified, and keep human escalation available.

**Reverse condition:** Reverse this decision when the evaluator supplies the scorer and an approved
development split produces a confidence result that meets the stated gate across protected cases.

## Assistance and independent checks

Coding-agent assistance was used to inspect the repository, summarize existing behavior, and draft
these evidence records. I independently checked the cited files, ran the commands listed in
[EXPERIMENT_LOG.md](EXPERIMENT_LOG.md), and verified the resulting test and benchmark outputs before
recording the decisions. No private chat history or private reasoning is included.

## Open decisions

- Official intent and action registries.
- Exact invalid-input behavior required by the qualification harness.
- Official confidence error-ratio formula.
- Approved dataset version, redistribution terms, and hidden split custody.
- CPU, memory, throughput, and Harbor version limits.
