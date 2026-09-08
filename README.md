# OP-06 TriageBench

OP-06 is a policy-constrained customer-support triage service plus a reproducible
evaluation harness. The API accepts up to eight role-tagged conversation turns and returns
an intent, a policy-permitted next action, calibrated confidence, and a human-routing flag.

This repository has two deliberate modes. The developer console and smoke suite run with an
explicit demo model. Production mode requires a trained model artifact and generated/approved
policy artifact; it does not silently fall back to embedded keyword labels. When an approved
dataset is available, `training/train_baseline.py` produces a TF-IDF model bundle that plugs into
the same runtime through `OP06_MODEL_PATH`.

## Quick start

The local environment needs Python 3.11 or newer.

```bash
make test
make benchmark-smoke
make serve
```

Then call the service:

```bash
curl -s http://127.0.0.1:8000/triage \
  -H 'content-type: application/json' \
  -d '{"conversation":[{"role":"customer","text":"My card is not working."}]}'
```

For manual testing, open [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/). The built-in
developer console sends requests to the same `/triage` route used by integrations and benchmark tasks.

Example response:

```json
{
  "intent": "card_not_working",
  "action": "ask_when_issue_started",
  "confidence": 0.609,
  "needs_human": false
}
```

Health and version endpoints are available at `/health/live`, `/health/ready`, and `/version`.
`/v1/triage` is provided as a compatibility alias.

## Architecture

```text
validated request
  -> Unicode-safe normalization and trusted serialization
  -> intent classifier
  -> deterministic conversation-state extractor
  -> versioned policy engine
  -> policy-masked action ranker
  -> confidence calibrator
  -> escalation rules
  -> four-field API response
```

The runtime cannot execute a refund or mutate a customer account. It only recommends the
next action. Conversation text is treated as untrusted data, never as policy or instructions.

## Use a trained baseline

Training data uses one JSON object per line:

```json
{"conversation_id":"c-1","conversation":[{"role":"customer","text":"My card was declined"}],"intent":"card_not_working","action":"ask_when_issue_started"}
```

Create leakage-safe conversation-grouped splits and train:

```bash
make data-audit DATA=data/examples.jsonl
make build-splits DATA=data/examples.jsonl
make train DATA=data/splits/train.jsonl
make serve-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd-derived.json
```

The policy registry remains a hard output boundary even when a trained artifact is used.
Update `src/op06/resources/policy.json` after the official label registries and guidelines are
confirmed.

## Prepare the official ABCD source data

The importer reads ABCD's real `take_action` targets, derives leakage-safe conversation prefixes,
and writes a policy candidate registry from the train split. Downloaded data is ignored by Git.

```bash
make fetch-abcd
make prepare-abcd
make train DATA=data/processed/abcd/train.jsonl
make calibrate DATA=data/processed/abcd/dev.jsonl
make build-benchmark DATA=data/processed/abcd/test.jsonl
make evaluate-trained \
  MODEL=models/baseline.joblib \
  POLICY=policies/compiled/abcd-derived.json \
  DATA=benchmark/cases/abcd-development.jsonl
```

The generated policy is a data-derived action candidate boundary. Review it against ABCD's
guidelines before treating it as a production policy.

## Benchmark

Local benchmark cases are JSONL records containing the API conversation and expected fields.

```bash
make benchmark-smoke
PYTHONPATH=src python -m op06.cli benchmark benchmark/cases --output reports/run.json
```

The report contains intent/action accuracy, macro-F1, ECE, Brier score, failures, and artifact
versions. The `benchmark/tasks` directories provide the ITSMBench/Harbor-style separation
between visible instructions, environment description, solution, and verifier expectations.

Smoke task packs are strict: every expected result must match. Corpus evaluation is statistical:
`make evaluate-trained` evaluates release gates across the held-out corpus and prints only a bounded
sample of failures, while preserving total failure counts in the report.

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `OP06_CONFIDENCE_THRESHOLD` | `0.58` | Human-review threshold |
| `OP06_MAX_REQUEST_BYTES` | `65536` | Maximum HTTP request size |
| `OP06_POLICY_PATH` | bundled policy | Alternate compiled policy |
| `OP06_MODEL_PATH` | unset | Optional trained joblib bundle |

## What remains dataset-dependent

The official OP-06 dataset, complete label registries, evaluator fixtures, and exact confidence
error-ratio definition were not present in the supplied material. Consequently, the included
labels and smoke data are executable examples—not a claim that qualification thresholds have
already been met. Before submission, replace/extend the bundled registry, train on the approved
data, and run the hidden evaluator.

See `docs/BUILD_PLAN.md` for milestones and `docs/DATA_FORMAT.md` for the canonical data format.

## Submission evidence

The judgment evidence is recorded in [docs/DECISIONS.md](docs/DECISIONS.md), with reconstructed
raw runs in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) and residual-risk ownership and pause
conditions in [docs/MEMO.md](docs/MEMO.md). These documents distinguish development evidence from
claims that require the hidden evaluator or official confidence scorer.
