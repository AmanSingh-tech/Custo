# OP-06 execution plan

## Implemented foundation

- Strict `POST /triage` and compatibility `POST /v1/triage` routes.
- One-to-eight-turn request schema and exact four-field response schema.
- Bounded HTTP payloads, structured validation errors, request/version headers, and health checks.
- NFC normalization, control-character removal, safety flags, and injection-resistant serialization.
- Pluggable intent and action interfaces with a deterministic cold-start implementation.
- Deterministic state extraction for required support workflow slots.
- Versioned policy registry, compiler validation, permitted-action generation, and hard masking.
- Temperature-based confidence calibration and explicit human-routing reasons.
- Grouped dataset splitting, data auditing, TF-IDF training, corpus metrics, and smoke benchmark.
- Docker, Compose, Make targets, contract/unit/security tests, and task templates.
- Official ABCD importer: public data download, action-prefix extraction, generated label/policy
  registries, train/dev/test preservation, and source hashes.
- Trained-artifact-only production path, dev-only calibration, vectorized held-out scoring, paired
  clean/noisy/hostile case generation, and machine-enforced release gates.

## Next work with the official assets

1. Replace the ABCD-derived registry with the evaluator's exact closed labels if they differ.
2. Reconcile the generated candidate policy with the supplied ABCD guidelines and ontology.
3. Add state-slot features and workflow-aware hard negatives beyond historical action events.
4. Fit the human-routing threshold against an approved business cost matrix.
5. Add protected hidden cases, including the official confidence-error-ratio scorer.
6. Validate the exact Harbor schema against the evaluator-pinned release.
7. Run load/soak, security review, and release freeze.

## Release gates

- Intent accuracy at least 0.55 and macro-F1 at least 0.50.
- Action accuracy at least 0.55.
- Clean-to-noisy action gap no more than 0.10.
- Official confidence error ratio no more than 0.85.
- Invalid policy action rate below 1%.
- No hostile crashes/hangs or critical injection-driven actions.
- All valid HTTP responses conform to the four-field schema.
- All benchmark tasks pass the reference solution and fail negative controls.

## Deferred until the structured-output MVP is stable

- Stateful mock enterprise/ticket APIs.
- Learned multi-label state extraction.
- Transformer selection and ONNX/quantization.
- Production drift dashboards, canary rollout, and artifact signing.
