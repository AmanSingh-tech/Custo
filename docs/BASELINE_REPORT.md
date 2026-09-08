# ABCD-derived baseline report

This report records the reproducible local baseline produced from the public ABCD v1.1 source
release. It is a development result, not a result from the supplied hidden qualification harness.

## Artifacts

- Source dataset SHA-256: `2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15`
- Prepared train/dev/test action examples: `29,186 / 3,684 / 3,608`
- Label registry: `56` intents and `31` actions including the safe escalation action
- Model: deterministic TF-IDF word/character features with `SGDClassifier(loss="log_loss")`
- Calibration: temperature `0.55`, fitted only on the dev split
- Policy: train-derived candidate-action registry, version `abcd-derived-2bdf53ac3595`

## Held-out evaluation

The test split was expanded into 10,824 paired development cases: one clean, one deterministic
noisy, and one hostile injection variant per test action point. The test data did not participate
in model fitting, calibration, or policy candidate-frequency ranking.

| Metric | Result | MVP gate |
|---|---:|---:|
| Intent accuracy | 0.7133 | ≥ 0.55 |
| Intent macro-F1 | 0.6871 | ≥ 0.50 |
| Action accuracy | 0.8158 | ≥ 0.55 |
| Action macro-F1 | 0.7856 | report |
| Clean action accuracy | 0.8190 | report |
| Clean → noisy action gap | 0.0033 | ≤ 0.10 |
| Invalid policy-action rate | 0.0000 | < 0.01 |
| Paired action invariance | 0.9670 | report |
| Calibration ECE | 0.3726 | report |
| Brier score | 0.3066 | report |

The configured release gates pass. The official confidence-error-ratio calculation and protected
qualification tasks were not supplied, so they remain intentionally outside this claim.

## Reproduce

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
