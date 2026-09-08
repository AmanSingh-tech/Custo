.PHONY: bootstrap serve serve-trained test test-unit test-security benchmark-validate benchmark-smoke benchmark-full data-audit build-splits fetch-abcd prepare-abcd build-benchmark train calibrate evaluate evaluate-trained docker-build

PYTHON ?= python3
PYTHONPATH := src

bootstrap:
	uv sync --extra dev

serve:
	OP06_ALLOW_DEMO_MODEL=1 PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn op06.api.app:app --host 0.0.0.0 --port 8000

serve-trained:
	@test -n "$(MODEL)" || (echo "Usage: make serve-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd.json" && exit 2)
	@test -n "$(POLICY)" || (echo "Usage: make serve-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd.json" && exit 2)
	OP06_MODEL_PATH=$(MODEL) OP06_POLICY_PATH=$(POLICY) PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn op06.api.app:app --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest

test-unit:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests/unit tests/contract

test-security:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests/security

benchmark-validate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli validate benchmark/tasks

benchmark-smoke:
	OP06_ALLOW_DEMO_MODEL=1 PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli benchmark benchmark/cases/smoke.jsonl --strict-cases

benchmark-full:
	OP06_ALLOW_DEMO_MODEL=1 PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli benchmark benchmark/cases --strict-cases

data-audit:
	@test -n "$(DATA)" || (echo "Usage: make data-audit DATA=path/to/examples.jsonl" && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli audit $(DATA)

build-splits:
	@test -n "$(DATA)" || (echo "Usage: make build-splits DATA=path/to/examples.jsonl" && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli split $(DATA) data/splits

fetch-abcd:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli fetch-abcd data/raw/abcd

prepare-abcd:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli prepare-abcd data/raw/abcd/dataset.json.gz data/processed/abcd --policy policies/compiled/abcd-derived.json

build-benchmark:
	@test -n "$(DATA)" || (echo "Usage: make build-benchmark DATA=data/processed/abcd/test.jsonl" && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli build-benchmark $(DATA) benchmark/cases/abcd-development.jsonl

train:
	@test -n "$(DATA)" || (echo "Usage: make train DATA=path/to/train.jsonl" && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) training/train_baseline.py --input $(DATA) --output models/baseline.joblib

calibrate:
	@test -n "$(DATA)" || (echo "Usage: make calibrate DATA=data/processed/abcd/dev.jsonl MODEL=models/baseline.joblib" && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) training/fit_calibrator.py --model $(or $(MODEL),models/baseline.joblib) --input $(DATA)

evaluate: benchmark-validate benchmark-smoke

evaluate-trained:
	@test -n "$(MODEL)" || (echo "Usage: make evaluate-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd-derived.json DATA=data/processed/abcd/test.jsonl" && exit 2)
	@test -n "$(POLICY)" || (echo "Usage: make evaluate-trained MODEL=models/baseline.joblib POLICY=policies/compiled/abcd-derived.json DATA=data/processed/abcd/test.jsonl" && exit 2)
	@test -n "$(DATA)" || (echo "Usage: make evaluate-trained MODEL=... POLICY=... DATA=..." && exit 2)
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m op06.cli benchmark $(DATA) --model $(MODEL) --policy $(POLICY) --enforce-gates

docker-build:
	docker build -t op06-triagebench:local .
