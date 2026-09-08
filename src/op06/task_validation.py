from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


REQUIRED_PATHS = (
    "instruction.md",
    "task.toml",
    "environment/seed.json",
    "solution/solution.py",
    "tests/test_outputs.py",
)


def validate_task(path: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (path / relative).is_file():
            errors.append(f"missing {relative}")
    task_file = path / "task.toml"
    if task_file.is_file():
        try:
            document = tomllib.loads(task_file.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"invalid task.toml: {exc}")
        else:
            task = document.get("task", {})
            if not isinstance(task, dict) or not str(task.get("name", "")).startswith("op06/"):
                errors.append("task.name must start with op06/")
            environment = document.get("environment", {})
            if not isinstance(environment, dict) or environment.get("network_mode") != "none":
                errors.append("environment.network_mode must be none")
    instruction = path / "instruction.md"
    if instruction.is_file() and "expected" in instruction.read_text(encoding="utf-8").casefold():
        errors.append("visible instruction may leak an expected result")
    return errors


def validate_tasks(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"tasks": 0, "valid": 0, "invalid": 1, "errors": {str(root): ["not a directory"]}}
    task_paths = sorted(path for path in root.iterdir() if path.is_dir())
    errors = {path.name: result for path in task_paths if (result := validate_task(path))}
    return {
        "tasks": len(task_paths),
        "valid": len(task_paths) - len(errors),
        "invalid": len(errors),
        "errors": errors,
    }

