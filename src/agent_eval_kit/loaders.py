from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    CitationSpec,
    CustomEvaluatorSpec,
    Expectation,
    JudgeSpec,
    TestCase,
    ToolCallSpec,
)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"Expected a string or list, got {type(value).__name__}.")
    return [str(item) for item in value]


def _parse_citations(raw: Any) -> CitationSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("'expect.citations' must be an object.")
    precision = raw.get("min_precision")
    coverage = raw.get("min_source_coverage")
    return CitationSpec(
        required=_as_list(raw.get("required")),
        min_count=int(raw.get("min_count", 0)),
        pattern=str(raw.get("pattern", r"\[[^\]]+\]")),
        validate_sources=bool(raw.get("validate_sources", False)),
        min_precision=float(precision) if precision is not None else None,
        min_source_coverage=float(coverage) if coverage is not None else None,
    )


def _parse_tool_calls(raw: Any) -> ToolCallSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("'expect.tool_calls' must be an object.")
    schemas = raw.get("args_schema") or {}
    if not isinstance(schemas, dict):
        raise ValueError("'expect.tool_calls.args_schema' must be an object.")
    max_count = raw.get("max_count")
    return ToolCallSpec(
        required=_as_list(raw.get("required")),
        forbidden=_as_list(raw.get("forbidden")),
        ordered=_as_list(raw.get("ordered")),
        max_count=int(max_count) if max_count is not None else None,
        args_schema={str(name): schema for name, schema in schemas.items()},
    )


def _parse_custom(raw: Any) -> list[CustomEvaluatorSpec]:
    if raw is None:
        return []

    if isinstance(raw, dict):
        return [
            CustomEvaluatorSpec(name=str(name), config=dict(config or {}))
            for name, config in raw.items()
        ]

    if not isinstance(raw, list):
        raise ValueError("'expect.custom' must be a list or object.")

    specs: list[CustomEvaluatorSpec] = []
    for item in raw:
        if isinstance(item, str):
            specs.append(CustomEvaluatorSpec(name=item))
        elif isinstance(item, dict) and item.get("name"):
            specs.append(
                CustomEvaluatorSpec(
                    name=str(item["name"]),
                    config=dict(item.get("config") or {}),
                )
            )
        else:
            raise ValueError("Each custom evaluator must be a name or an object with 'name'.")
    return specs


def _parse_expectation(item: dict[str, Any]) -> Expectation:
    raw = item.get("expect") or {}
    if raw and not isinstance(raw, dict):
        raise ValueError("'expect' must be an object.")

    contains = _as_list(raw.get("contains", item.get("expected_contains")))
    not_contains = _as_list(raw.get("not_contains", item.get("expected_not_contains")))
    regex = _as_list(raw.get("regex"))

    judge_spec = None
    judge = raw.get("judge")
    if judge is not None:
        if isinstance(judge, str):
            judge_spec = JudgeSpec(criteria=judge)
        elif isinstance(judge, dict) and judge.get("criteria"):
            judge_spec = JudgeSpec(
                criteria=str(judge["criteria"]),
                min_score=float(judge.get("min_score", 0.7)),
            )
        else:
            raise ValueError("'expect.judge' must be a criteria string or object.")

    schema = raw.get("json_schema")
    if schema is not None and not isinstance(schema, dict):
        raise ValueError("'expect.json_schema' must be a JSON Schema object.")

    max_latency_ms = raw.get("max_latency_ms")
    return Expectation(
        contains=contains,
        not_contains=not_contains,
        regex=regex,
        json_schema=schema,
        citations=_parse_citations(raw.get("citations")),
        tool_calls=_parse_tool_calls(raw.get("tool_calls")),
        custom=_parse_custom(raw.get("custom")),
        max_latency_ms=float(max_latency_ms) if max_latency_ms is not None else None,
        judge=judge_spec,
    )


def load_cases(path: str | Path) -> list[TestCase]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    items = raw.get("cases", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("Evaluation file must contain a list or a top-level 'cases' list.")

    cases: list[TestCase] = []
    seen: set[str] = set()
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict) or "prompt" not in item:
            raise ValueError(f"Case #{idx} must be an object with a 'prompt' field.")
        case_id = str(item.get("id", f"case-{idx}"))
        if case_id in seen:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen.add(case_id)

        tools = item.get("tools") or []
        if not isinstance(tools, list):
            raise ValueError(f"Case {case_id!r}: 'tools' must be a list.")

        cases.append(
            TestCase(
                id=case_id,
                prompt=str(item["prompt"]),
                system=str(item["system"]) if item.get("system") is not None else None,
                context=str(item["context"]) if item.get("context") is not None else None,
                tools=[dict(tool) for tool in tools],
                tool_choice=item.get("tool_choice"),
                expect=_parse_expectation(item),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return cases
