# Experiment log

These entries were reconstructed on 2026-09-08 from recorded repository work and rerun checks.
They are labeled reconstructed rather than presented as contemporaneous laboratory notes. Commands
run from `/home/pendulum/custo`; outputs are bounded to the decision-relevant result.

## R-2026-09-08-01: Runtime and security checks

**Date:** 2026-09-08  
**Question:** Does the service keep demo behavior explicit and survive the covered hostile-input cases?

**Command:**

```text
PYTHONPATH=src python3 -m pytest
```

**Raw result:**

```text
35 passed in 0.20s
```

**Observation:** The full unit, contract, integration, and security suite passed. This supports the
explicit demo-mode boundary and the current hostile-input protections, but does not establish hidden
evaluator performance or production load behavior.

## R-2026-09-08-02: Policy-constrained held-out baseline

**Date:** 2026-09-08  
**Question:** Does policy masking preserve a valid action boundary without destroying baseline quality?

**Source:** Reconstructed from [BASELINE_REPORT.md](BASELINE_REPORT.md), whose source release hash is
`2bdf53ac359543dcdc38d55bc6513e78df120363f8f44870716e909f4606de15`.

**Recorded run:**

```text
make fetch-abcd
make prepare-abcd
make train DATA=data/processed/abcd/train.jsonl
make calibrate DATA=data/processed/abcd/dev.jsonl
make build-benchmark DATA=data/processed/abcd/test.jsonl
make evaluate-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd-derived.json DATA=benchmark/cases/abcd-development.jsonl
```

**Raw result:** Intent accuracy `0.7133`; intent macro-F1 `0.6871`; action accuracy `0.8158`;
clean-to-noisy action gap `0.0033`; invalid policy-action rate `0.0000`; paired action invariance
`0.9670`.

**Observation:** The policy boundary passed the recorded MVP gates and produced no invalid actions
on this development corpus. This remains development evidence, not hidden qualification evidence.

## R-2026-09-08-03: Confidence calibration is inconclusive

**Date:** 2026-09-08  
**Question:** Does the current calibrated confidence support the official confidence-error-ratio claim?

**Source:** Reconstructed from [BASELINE_REPORT.md](BASELINE_REPORT.md).

**Raw result:** Calibration ECE `0.3726`; Brier score `0.3066`. Classification metrics were stronger
than calibration metrics, with intent accuracy `0.7133` and action accuracy `0.8158`.

**Observation:** The result is inconclusive for the official confidence-error-ratio because that
scorer was not supplied. The available metrics are reported, but the official confidence gate is
not claimed as passed. This is the required failure/inconclusive experiment in the decision record.
