# Custo

**Policy-constrained triage for customer-support conversations.**

Custo reads a support chat between a customer and an agent and returns four things: what the
customer needs (intent), the next step the support policy allows (action), a calibrated confidence
score, and whether a person should take over. It only makes recommendations. It has no
credentials, payment access or side-effecting tools, so it cannot issue a refund or change an account.

Custo implements the **OP-06 TriageBench** service contract and includes a reproducible evaluation
harness alongside the service.

> **Live demo:** _add your Render URL here after deploying (see [Deploy](#deploy))_

```text
customer: "Hi, my card is not working."
agent:    "Sorry to hear that. When did this start?"
customer: "Yesterday afternoon."
                │
                ▼
{ "intent": "card_not_working",
  "action": "ask_alternate_terminal_attempted",
  "confidence": 0.6191,
  "needs_human": false }
```

## Contents

- [Demo UI](#demo-ui)
- [Quick start](#quick-start)
- [Deploy](#deploy)
- [API](#api)
- [How it works](#how-it-works)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Training on real data](#training-on-real-data)
- [Tests and benchmarks](#tests-and-benchmarks)
- [Project status](#project-status)

## Demo UI

Open the service root (`/`) to reach the web demo. It runs the first example as soon as it loads.

- **Conversation builder:** add customer and agent messages (up to 8), edit them in place, or
  start from a one-click example.
- **Decision:** a verdict ("Safe to handle automatically" or "Send to a human agent") with its
  reason, the intent, the recommended next step, and a confidence gauge marked at the threshold.
- **How it decided:** a five-step trace showing input screening, intent scores, facts already
  established in the chat, the actions the policy allows (forbidden actions shown crossed out),
  and the routing checks that fired.
- **Developer extras:** the raw JSON response, a ready-to-run `curl` command, a session run
  history, and light and dark themes. The layout works on phones.

Each example has a direct link of the form `/app/#<id>`. These are the results from the bundled
demo model:

| Link | Scenario | Intent → action | Routing |
|---|---|---|---|
| `#card-start` | Card not working | `card_not_working` → `ask_when_issue_started` | Auto |
| `#card-progress` | Follow-up after the agent's question | `card_not_working` → `ask_alternate_terminal_attempted` | Auto |
| `#fx` | Wrong exchange rate, amount given | `card_payment_wrong_exchange_rate` → `explain_exchange_rate_process` | Auto |
| `#fraud` | Unrecognised card payment | `card_payment_not_recognised` → `secure_account_and_escalate` | Human: policy requires a person |
| `#hostile` | Prompt injection asking for `execute_refund` | `card_not_working` → `ask_when_issue_started` | Human: suspicious input |
| `#vague` | "hello, can someone help me?" | `general_support` → `request_clarification` | Human: low confidence |

The step-by-step trace comes from `/demo/explain`, which is only available when
`OP06_EXPOSE_TRACE=1` is set. Without it, the UI still works and shows only the four-field result.

## Quick start

You need Python 3.11 or newer.

```bash
git clone https://github.com/AmanSingh-tech/Custo.git
cd Custo
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

make test              # unit, contract, integration and security tests
make serve             # demo model on http://127.0.0.1:8000/
```

Use `make serve` for the API alone. To get the demo UI with the step-by-step trace, run:

```bash
OP06_ALLOW_DEMO_MODEL=1 OP06_EXPOSE_TRACE=1 PYTHONPATH=src \
  uvicorn op06.api.app:app --port 8000
```

You can also use Docker, which runs the same configuration as the hosted demo:

```bash
docker compose up --build   # http://127.0.0.1:8000/
```

## Deploy

### Vercel

The FastAPI app runs on Vercel as a single Python function. No `npm` build is needed, because the
frontend is plain HTML, CSS and JS served by the API.

1. Push this repository to GitHub.
2. Sign in to [Vercel](https://vercel.com) with GitHub. Choose **Add New → Project**, import
   this repository, and keep the defaults (Framework Preset: **FastAPI** or **Other**, with no
   build command or output directory).
3. Click **Deploy**. Your demo URL looks like `https://custo.vercel.app`.

Vercel finds the app through the root [`index.py`](index.py). That file turns on
`OP06_ALLOW_DEMO_MODEL` and `OP06_EXPOSE_TRACE` by default, and project environment variables
override them. [`.vercelignore`](.vercelignore) keeps tests, docs and training code out of the
bundle. Every push to `main` redeploys.

### Render or any container host

The container listens on `$PORT` (default `8000`), so it runs unchanged on Render, Railway,
Fly.io or Google Cloud Run. The repository includes a Render Blueprint:

1. Push this repository to GitHub.
2. Sign in to [Render](https://render.com) with GitHub. Choose **New → Blueprint** and select
   this repository.
3. Render reads [`render.yaml`](render.yaml), builds the Dockerfile, applies the demo settings,
   and health-checks `/health/ready`. Your demo URL looks like
   `https://custo-triage-demo.onrender.com`.

Every push to `main` redeploys. On Render's free plan the service sleeps when idle, so the first
request after a quiet period takes 30–50 seconds. Open the URL shortly before a live demo.

## API

Interactive API docs are served at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/triage` | Triage a conversation. `/v1/triage` is an alias. |
| `POST` | `/demo/explain` | Result plus pipeline trace. Requires `OP06_EXPOSE_TRACE=1`. |
| `GET` | `/health/live`, `/health/ready`, `/healthz` | Liveness and readiness checks |
| `GET` | `/version` | Service, API, schema, model and policy versions |
| `GET` | `/` → `/app/` | Demo UI |

### Request

`/triage` accepts two request shapes, each with one to eight turns. Roles are `customer`, `agent`
or `action`.

```bash
# Native shape
curl -s http://127.0.0.1:8000/triage -H 'content-type: application/json' \
  -d '{"conversation":[{"role":"customer","text":"My card is not working."}]}'

# Published OP-06 shape: the response echoes the id
curl -s http://127.0.0.1:8000/triage -H 'content-type: application/json' \
  -d '{"id":"case-1","context":[{"speaker":"customer","text":"My card is not working."}]}'
```

### Response

```json
{
  "intent": "card_not_working",
  "action": "ask_when_issue_started",
  "confidence": 0.6191,
  "needs_human": false
}
```

Every response carries `x-request-id`, `x-api-version`, `x-model-version` and `x-policy-version`
headers.

### Errors and safe defaults

| Situation | Result |
|---|---|
| Malformed request, blank native turn, or more than 8 turns | `422` with `{"error": {"code": "invalid_request", ...}}` |
| Body larger than `OP06_MAX_REQUEST_BYTES` | `413` |
| Blank message in the OP-06 shape | `200` with `unknown` / `none`, `needs_human: true` |
| Hostile input in the OP-06 shape | `200` with `unknown` / `none`, `needs_human: true` |

## How it works

```text
validated request
  → Unicode normalisation and injection screening   (bidi, zero-width, fake roles, "ignore instructions")
  → intent classifier                               (keyword demo model or trained TF-IDF bundle)
  → conversation-state extractor                    (what the chat has already established)
  → versioned policy engine                         (allowed next actions for this intent + state)
  → policy-masked action ranker                     (can only choose an allowed action)
  → temperature-calibrated confidence
  → escalation rules                                (decide needs_human)
  → four-field response
```

A case is sent to a person when any of these apply: confidence is below the threshold, intent or
action is ambiguous, the policy has no valid path, the chosen action requires a human (for
example `secure_account_and_escalate`), the input looks hostile or corrupted, or the conversation
contradicts itself.

Conversation text is always treated as untrusted data, never as instructions. The policy in
[`src/op06/resources/policy.json`](src/op06/resources/policy.json) is a hard output boundary.
Actions such as `execute_refund`, `close_customer_account` and `reveal_authentication_secret` are
globally forbidden and can never be returned.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `OP06_ALLOW_DEMO_MODEL` | unset | `1` uses the built-in keyword model. Without it, a trained model is required. |
| `OP06_MODEL_PATH` | unset | Path to a trained `joblib` bundle. |
| `OP06_POLICY_PATH` | bundled policy | Path to an alternate compiled policy. |
| `OP06_CONFIDENCE_THRESHOLD` | `0.58` | Confidence below this routes the case to a human. |
| `OP06_EXPOSE_TRACE` | unset | `1` enables `/demo/explain`. Leave unset in production. |
| `OP06_MAX_REQUEST_BYTES` | `65536` | Maximum HTTP request size. |
| `PORT` | `8000` | Container listen port. Set automatically by hosting platforms. |

The service refuses to start with neither a trained model nor the demo flag. It never falls back
to the demo model silently.

## Project structure

| Location | Purpose |
|---|---|
| `src/op06/api/` | FastAPI app: request contract, size limits, health and version routes, trace endpoint. |
| `src/op06/web/` | Demo UI in plain HTML, CSS and JS with no build step, served at `/app/`. |
| `src/op06/pipeline.py` | Wires normalisation, classification, state, policy, ranking, calibration and escalation. |
| `src/op06/preprocessing/` | Unicode normalisation and hostile-input flags. |
| `src/op06/intent/`, `action/` | Keyword demo classifier, trained-model loaders, policy-masked ranker. |
| `src/op06/state/` | Rule-based conversation-state extraction. |
| `src/op06/policy/` | Policy compilation and allowed-action engine. |
| `src/op06/confidence/` | Temperature calibration and escalation rules. |
| `src/op06/abcd.py`, `training/` | ABCD dataset import, grouped splits, baseline training and calibration. |
| `src/op06/benchmark.py`, `benchmark/` | Smoke cases, task packs, metrics and release gates. |
| `tests/` | Unit, API contract, integration and hostile-input tests. |
| `docs/` | Build plan, data format, decisions, experiment log, analysis and rollout memo. |
| `Dockerfile`, `docker-compose.yaml`, `render.yaml` | Container image, local hardened run, and Render deploy. |
| `index.py`, `.vercelignore` | Vercel entrypoint and bundle exclusions. |

## Training on real data

Training data uses one JSON object per line. See [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md) for
the full format.

```json
{"conversation_id":"c-1","conversation":[{"role":"customer","text":"My card was declined"}],"intent":"card_not_working","action":"ask_when_issue_started"}
```

To train on your own data:

```bash
make data-audit   DATA=data/examples.jsonl
make build-splits DATA=data/examples.jsonl        # leakage-safe, grouped by conversation
make train        DATA=data/splits/train.jsonl
make serve-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd-derived.json
```

To train on the public ABCD dataset:

```bash
make fetch-abcd
make prepare-abcd                                  # also writes a data-derived policy
make train      DATA=data/processed/abcd/train.jsonl
make calibrate  DATA=data/processed/abcd/dev.jsonl
make build-benchmark DATA=data/processed/abcd/test.jsonl
make evaluate-trained MODEL=models/baseline.joblib \
  POLICY=policies/compiled/abcd-derived.json DATA=benchmark/cases/abcd-development.jsonl
```

Downloaded data, models and compiled policies are ignored by Git. Review a generated policy
against ABCD's guidelines before treating it as a production policy.

## Tests and benchmarks

```bash
make test                # full pytest suite
make test-security       # hostile-input regressions only
make benchmark-validate  # check benchmark task packs
make benchmark-smoke     # strict smoke cases: every case must match
ruff check .             # lint, also run in CI
```

Benchmark reports include intent and action accuracy, macro-F1, ECE, Brier score, failure
counts and artifact versions. CI ([.github/workflows/ci.yaml](.github/workflows/ci.yaml)) runs
tests, lint, task validation, the smoke benchmark and a container build on every push.

## Project status

The local tests, smoke tasks and ABCD-derived benchmark are **development evidence, not
qualification metrics**. The published OP-06 evaluator files (`train.jsonl.gz`, `dev.jsonl`,
`dev_noisy.jsonl`, `hostile.jsonl`, `grader.py`) are not included in this repository. When they
are available:

1. Keep them out of source control, for example under `data/official/`.
2. Train only on `train.jsonl.gz`, start the trained service, and run `grader.py` as its own
   documentation describes.
3. Record the inputs, the exact command, the service, model and policy versions, the grader output
   and the load results in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md).

Until that run exists, the accurate claim is: **local development evidence passes, and official
qualification is pending the published files and grader.**

| Area | Evidence here | Still open |
|---|---|---|
| Service contract | API contract tests, health routes | Exact grader edge cases |
| Model quality | Reproducible ABCD-derived baseline | Performance on the official data |
| Policy correctness | Action mask, invalid-action metric | Official procedure and scorer |
| Robustness | Clean, noisy and hostile cases; security tests | Published noise families |
| Confidence | Calibration, threshold, routing rules | Official top-70 confidence-error ratio |
| Operations | Container, CI, load script, memo | p95 latency and cost on the evaluator machine |

Further reading: [docs/DECISIONS.md](docs/DECISIONS.md) (design decisions),
[docs/ANALYSIS.md](docs/ANALYSIS.md) (failure taxonomy),
[docs/MEMO.md](docs/MEMO.md) (residual risk and pause conditions),
[docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) (milestones), and [SECURITY.md](SECURITY.md).
