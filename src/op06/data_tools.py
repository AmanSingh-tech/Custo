from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class DatasetError(ValueError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                example = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(example, dict):
                raise DatasetError(f"{path}:{line_number}: example must be an object")
            examples.append(example)
    if not examples:
        raise DatasetError(f"{path}: no examples found")
    return examples


def canonical_conversation_id(example: dict[str, Any], index: int) -> str:
    value = example.get("conversation_id")
    if value is not None and str(value).strip():
        return str(value)
    turns = example.get("conversation") or example.get("turns")
    if turns is not None:
        digest = hashlib.sha256(
            json.dumps(turns, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        return f"derived-{digest}"
    return f"row-{index}"


def audit_examples(examples: list[dict[str, Any]]) -> dict[str, Any]:
    intent_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    conversation_counts: Counter[str] = Counter()
    turn_counts: Counter[int] = Counter()
    malformed = 0
    for index, example in enumerate(examples):
        intent = example.get("intent")
        action = example.get("action", example.get("next_action"))
        turns = example.get("conversation", example.get("turns"))
        if not isinstance(intent, str) or not isinstance(action, str) or not isinstance(turns, list):
            malformed += 1
            continue
        intent_counts[intent] += 1
        action_counts[action] += 1
        conversation_counts[canonical_conversation_id(example, index)] += 1
        turn_counts[len(turns)] += 1
    serialized = "\n".join(json.dumps(item, sort_keys=True, ensure_ascii=False) for item in examples)
    return {
        "rows": len(examples),
        "valid_rows": len(examples) - malformed,
        "malformed_rows": malformed,
        "conversations": len(conversation_counts),
        "prefix_rows": sum(max(0, count - 1) for count in conversation_counts.values()),
        "intents": dict(sorted(intent_counts.items())),
        "actions": dict(sorted(action_counts.items())),
        "turn_counts": {str(key): value for key, value in sorted(turn_counts.items())},
        "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


def _split_name(conversation_id: str, seed: int) -> str:
    digest = hashlib.sha256(f"{seed}:{conversation_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") / (2**64 - 1)
    if bucket < 0.8:
        return "train"
    if bucket < 0.9:
        return "calibration"
    return "test"


def split_examples(
    examples: list[dict[str, Any]], seed: int = 42
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {"train": [], "calibration": [], "test": []}
    for index, original in enumerate(examples):
        example = dict(original)
        conversation_id = canonical_conversation_id(example, index)
        example.setdefault("conversation_id", conversation_id)
        output[_split_name(conversation_id, seed)].append(example)
    return output


def write_splits(splits: dict[str, list[dict[str, Any]]], output_dir: Path, seed: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"seed": seed, "splits": {}}
    seen: set[str] = set()
    for name, examples in splits.items():
        path = output_dir / f"{name}.jsonl"
        lines = [json.dumps(example, ensure_ascii=False, sort_keys=True) for example in examples]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        ids = {str(example["conversation_id"]) for example in examples}
        overlap = seen & ids
        if overlap:
            raise DatasetError(f"conversation leakage detected: {sorted(overlap)[:3]}")
        seen.update(ids)
        manifest["splits"][name] = {
            "rows": len(examples),
            "conversations": len(ids),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def generate_noisy_text(text: str, seed: int) -> str:
    """Deterministic benign corruption helper for benchmark authoring."""
    rng = random.Random(seed)
    words = text.split()
    if not words:
        return text
    index = rng.randrange(len(words))
    word = words[index]
    if len(word) > 3:
        position = rng.randrange(1, len(word) - 1)
        word = word[:position] + word[position + 1] + word[position] + word[position + 2 :]
        words[index] = word
    return "  ".join(words)


def iter_jsonl_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(path.glob("*.jsonl"))
    else:
        raise DatasetError(f"Path does not exist: {path}")

