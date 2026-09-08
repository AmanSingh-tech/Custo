from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ActionRule:
    action: str
    priority: int
    when_missing: tuple[str, ...] = ()
    when_present: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Workflow:
    intent: str
    rules: tuple[ActionRule, ...]
    fallback_action: str


@dataclass(frozen=True, slots=True)
class CompiledPolicy:
    version: str
    intents: frozenset[str]
    actions: frozenset[str]
    forbidden_actions: frozenset[str]
    workflows: dict[str, Workflow]


def _required_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise PolicyError(f"{name} must be a non-empty object")
    return value


def compile_policy_document(document: dict[str, Any]) -> CompiledPolicy:
    version = document.get("version")
    if not isinstance(version, str) or not version:
        raise PolicyError("version must be a non-empty string")
    intents = frozenset(str(value) for value in document.get("intents", []))
    actions = frozenset(str(value) for value in document.get("actions", []))
    forbidden = frozenset(str(value) for value in document.get("global_forbidden_actions", []))
    if not intents or not actions:
        raise PolicyError("intents and actions registries cannot be empty")
    workflows_raw = _required_mapping(document.get("workflows"), "workflows")
    workflows: dict[str, Workflow] = {}
    for intent, workflow_raw in workflows_raw.items():
        if intent not in intents:
            raise PolicyError(f"Workflow intent is not registered: {intent}")
        workflow = _required_mapping(workflow_raw, f"workflows.{intent}")
        fallback = workflow.get("fallback_action", "escalate_human")
        if fallback not in actions:
            raise PolicyError(f"Unregistered fallback action {fallback!r} for {intent}")
        rules: list[ActionRule] = []
        for index, raw_rule in enumerate(workflow.get("rules", [])):
            rule = _required_mapping(raw_rule, f"workflows.{intent}.rules[{index}]")
            action = rule.get("action")
            if action not in actions:
                raise PolicyError(f"Unregistered action {action!r} for {intent}")
            if action in forbidden:
                raise PolicyError(f"Globally forbidden action {action!r} is used by {intent}")
            rules.append(
                ActionRule(
                    action=action,
                    priority=int(rule.get("priority", 0)),
                    when_missing=tuple(str(value) for value in rule.get("when_missing", [])),
                    when_present=tuple(str(value) for value in rule.get("when_present", [])),
                )
            )
        if not rules:
            raise PolicyError(f"Workflow {intent} has no rules")
        workflows[intent] = Workflow(intent, tuple(rules), fallback)
    missing = intents - workflows.keys()
    if missing:
        raise PolicyError(f"Registered intents without workflows: {sorted(missing)}")
    return CompiledPolicy(version, intents, actions, forbidden, workflows)


def load_policy(path: Path) -> CompiledPolicy:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"Cannot load policy from {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise PolicyError("Policy root must be an object")
    return compile_policy_document(document)
