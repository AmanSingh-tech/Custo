from __future__ import annotations

import argparse
import json
from pathlib import Path

from op06.benchmark import render_report, run_benchmark
from op06.abcd import download_abcd, prepare_abcd, write_benchmark_cases, write_prepared_abcd
from op06.config import Settings
from op06.data_tools import audit_examples, load_jsonl, split_examples, write_splits
from op06.evaluation.gates import evaluate_release_gates
from op06.pipeline import TriagePipeline
from op06.task_validation import validate_tasks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="op06", description="OP-06 TriageBench tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="run local JSONL benchmark cases")
    benchmark.add_argument("path", type=Path)
    benchmark.add_argument("--output", type=Path)
    benchmark.add_argument("--model", type=Path)
    benchmark.add_argument("--policy", type=Path)
    benchmark.add_argument("--enforce-gates", action="store_true")
    benchmark.add_argument(
        "--strict-cases",
        action="store_true",
        help="fail when any individual expected output does not match",
    )

    validate = subparsers.add_parser("validate", help="validate benchmark task packages")
    validate.add_argument("path", type=Path)

    audit = subparsers.add_parser("audit", help="audit canonical JSONL examples")
    audit.add_argument("path", type=Path)

    split = subparsers.add_parser("split", help="make conversation-grouped splits")
    split.add_argument("path", type=Path)
    split.add_argument("output", type=Path)
    split.add_argument("--seed", type=int, default=42)

    fetch_abcd = subparsers.add_parser("fetch-abcd", help="download public ABCD source assets")
    fetch_abcd.add_argument("output", type=Path)

    prepare_abcd_parser = subparsers.add_parser(
        "prepare-abcd", help="convert ABCD into canonical examples"
    )
    prepare_abcd_parser.add_argument("dataset", type=Path)
    prepare_abcd_parser.add_argument("output", type=Path)
    prepare_abcd_parser.add_argument("--policy", type=Path, required=True)

    build_benchmark = subparsers.add_parser(
        "build-benchmark", help="create paired clean/noisy/hostile development cases"
    )
    build_benchmark.add_argument("input", type=Path)
    build_benchmark.add_argument("output", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "benchmark":
        runtime = None
        if args.model or args.policy:
            settings = Settings(
                model_path=args.model,
                policy_path=args.policy or Settings().policy_path,
                allow_demo_model=False,
            )
            runtime = TriagePipeline.build(settings)
        report = run_benchmark(args.path, runtime)
        if args.enforce_gates:
            report["release_gates"] = evaluate_release_gates(report["summary"])
        rendered = render_report(report)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        failed = (args.strict_cases and report["summary"]["failed"]) or (
            args.enforce_gates and not report["release_gates"]["passed"]
        )
        raise SystemExit(1 if failed else 0)
    if args.command == "audit":
        print(json.dumps(audit_examples(load_jsonl(args.path)), indent=2, sort_keys=True))
        return
    if args.command == "validate":
        report = validate_tasks(args.path)
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1 if report["invalid"] else 0)
    if args.command == "split":
        examples = load_jsonl(args.path)
        manifest = write_splits(split_examples(examples, args.seed), args.output, args.seed)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return
    if args.command == "fetch-abcd":
        print(json.dumps(download_abcd(args.output), indent=2, sort_keys=True))
        return
    if args.command == "prepare-abcd":
        prepared = prepare_abcd(args.dataset)
        write_prepared_abcd(prepared, args.output, args.policy)
        print(json.dumps(prepared.manifest, indent=2, sort_keys=True))
        return
    if args.command == "build-benchmark":
        print(json.dumps(write_benchmark_cases(args.input, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
