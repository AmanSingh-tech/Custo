from pathlib import Path

from op06.task_validation import validate_tasks


def test_bundled_tasks_are_complete() -> None:
    report = validate_tasks(Path("benchmark/tasks"))
    assert report == {"tasks": 3, "valid": 3, "invalid": 0, "errors": {}}

