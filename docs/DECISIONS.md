# Decision log

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

## Open decisions

- Official intent and action registries.
- Exact invalid-input behavior required by the qualification harness.
- Official confidence error-ratio formula.
- Approved dataset version, redistribution terms, and hidden split custody.
- CPU, memory, throughput, and Harbor version limits.
