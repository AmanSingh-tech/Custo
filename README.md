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

## Project map

| Location | Purpose |
|---|---|
| `src/op06/api/` | FastAPI contract, request limits, health checks, and browser test console. |
| `src/op06/pipeline.py` | Normalization, classification, state, policy, confidence, and escalation. |
| `src/op06/policy/` | Versioned policy compilation and action-candidate restrictions. |
| `src/op06/abcd.py` and `training/` | Public-data import, grouped training, and temperature calibration. |
| `src/op06/benchmark.py` and `benchmark/` | Smoke cases, paired robustness cases, metrics, gates, and task validation. |
| `tests/` | Unit, API-contract, integration, and hostile-input regression tests. |
| `docs/` | Build plan, data format, decisions, raw runs, analysis, and rollout memo. |

## Request contract and safe behavior

The service accepts the repository-native shape (`conversation` with `role` and `text`) and the
published OP-06-compatible shape (`id` plus `context` with `speaker` and `text`). Published-format
responses echo the supplied `id`. Both forms accept one to eight turns; malformed requests return
`422`, oversized HTTP bodies return `413`, and a blank published-format message returns a safe
`unknown` / `none` human-routing response.

A policy conflict, no valid candidate, low confidence, hostile-input flag, or state contradiction
routes the case to a person. The API is recommendation-only: it has no account credentials, payment
access, or side-effecting tools, and an action model can rank only policy-permitted candidates.

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

## Qualification status: do not substitute local metrics

The repository contains local smoke tasks and an ABCD-derived development benchmark. They are useful
for regression testing, but they are **not qualification metrics**. The required published evaluator
assets are absent from this repository:

```text
train.jsonl.gz
dev.jsonl
dev_noisy.jsonl
hostile.jsonl
grader.py
```

When those files are provided, keep them outside source control (for example under
`data/official/`), train only on `train.jsonl.gz`, start the trained service, and run the supplied
`grader.py` according to its own documented invocation. Preserve the unedited input files, exact
command, service/model/policy versions, grader output, and evaluator-machine load result in
`docs/EXPERIMENT_LOG.md`. Only then report clean and noisy performance, permitted-action violations,
hostile/human-routing behavior, the official top-70 confidence-error ratio, p95 latency, and cost.

Until that run exists, the correct claim is: **local development evidence passes; official
qualification is pending the published files and grader.**

## Review evidence map

| Dimension | Evidence in this repository | Remaining uncertainty |
|---|---|---|
| Service contract | API-contract tests and `/healthz` | Exact grader edge cases are unavailable. |
| Data provenance | ABCD importer and hashes in the experiment log | Official train/dev files are not present. |
| Model quality | Reproducible ABCD-derived baseline report | Qualification performance is unknown. |
| Policy correctness | Candidate mask and invalid-action metric | Official procedure and scorer are pending. |
| Robustness | Paired smoke/noisy/hostile cases and security tests | Published noise families have not been run. |
| Confidence and escalation | Calibration, thresholds, and human-route rules | Official top-70 ratio is unverified. |
| Operations and accountability | Container, CI, load script, decision log, and memo | Evaluator-machine latency/cost are unknown. |

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `OP06_CONFIDENCE_THRESHOLD` | `0.58` | Human-review threshold |
| `OP06_MAX_REQUEST_BYTES` | `65536` | Maximum HTTP request size |
| `OP06_POLICY_PATH` | bundled policy | Alternate compiled policy |
| `OP06_MODEL_PATH` | unset | Optional trained joblib bundle |

## What remains dataset-dependent

The published OP-06 service contract, hostile pack, and confidence-error-ratio definition are now
available from the hiring repository, but those evaluator files are not included here. Consequently,
the included labels and smoke data are executable examples, not a qualification claim. Before
submission, run the published data and grader, report noisy-slice and human-routing results, and
measure p95 latency and cost on the evaluator machine.

See `docs/BUILD_PLAN.md` for milestones and `docs/DATA_FORMAT.md` for the canonical data format.
See [docs/ANALYSIS.md](docs/ANALYSIS.md) for the failure taxonomy and known evidence gaps.

## Submission evidence

The judgment evidence is recorded in [docs/DECISIONS.md](docs/DECISIONS.md), with reconstructed
raw runs in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) and residual-risk ownership and pause
conditions in [docs/MEMO.md](docs/MEMO.md). These documents distinguish development evidence from
claims that require the hidden evaluator or official confidence scorer.
