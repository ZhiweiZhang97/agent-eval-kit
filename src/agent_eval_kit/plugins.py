from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import CheckResult, TestCase, ToolCall

EvaluatorFn = Callable[
    [TestCase, str, list[ToolCall], dict[str, Any]],
    CheckResult | bool | tuple[bool, str],
]

_REGISTRY: dict[str, EvaluatorFn] = {}


def evaluator(name: str) -> Callable[[EvaluatorFn], EvaluatorFn]:
    key = name.strip()
    if not key:
        raise ValueError("Evaluator name cannot be empty.")

    def register(fn: EvaluatorFn) -> EvaluatorFn:
        if key in _REGISTRY:
            raise ValueError(f"Evaluator already registered: {key}")
        _REGISTRY[key] = fn
        return fn

    return register


def get_evaluator(name: str) -> EvaluatorFn | None:
    return _REGISTRY.get(name)


def clear_evaluators() -> None:
    _REGISTRY.clear()


def load_plugin(target: str) -> None:
    path = Path(target)
    if path.suffix == ".py" and path.exists():
        module_name = f"agent_eval_plugin_{abs(hash(path.resolve()))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load evaluator plugin: {target}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return
    importlib.import_module(target)


def run_custom_evaluator(
    name: str,
    case: TestCase,
    response: str,
    tool_calls: list[ToolCall],
    config: dict[str, Any],
) -> CheckResult:
    fn = get_evaluator(name)
    if fn is None:
        return CheckResult(False, f"Custom evaluator is not registered: {name}")
    try:
        value = fn(case, response, tool_calls, config)
    except Exception as exc:
        return CheckResult(False, f"Custom evaluator {name!r} failed: {exc}")

    if isinstance(value, CheckResult):
        return value
    if isinstance(value, tuple):
        passed, detail = value
        return CheckResult(bool(passed), str(detail))
    return CheckResult(bool(value), f"Custom evaluator {name!r} returned {bool(value)}.")
