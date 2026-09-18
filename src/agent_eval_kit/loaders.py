from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import CitationSpec, Expectation, JudgeSpec, TestCase


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError(f"Expected a string or list, got {type(value).__name__}.")
    return [str(item) for item in value]


def _parse_expectation(item: dict[str, Any]) -> Expectation:
    raw = item.get("expect") or {}
    if raw and not isinstance(raw, dict):
        raise ValueError("'expect' must be an object.")

    contains = _as_list(raw.get("contains", item.get("expected_contains")))
    not_contains = _as_list(raw.get("not_contains", item.get("expected_not_contains")))
    regex = _as_list(raw.get("regex"))

    citation_spec = None
    citations = raw.get("citations")
    if citations is not None:
        if not isinstance(citations, dict):
            raise ValueError("'expect.citations' must be an object.")
        citation_spec = CitationSpec(
            required=_as_list(citations.get("required")),
            min_count=int(citations.get("min_count", 0)),
            pattern=str(citations.get("pattern", r"\[[^\]]+\]")),
        )

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
        citations=citation_spec,
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
        cases.append(
            TestCase(
                id=case_id,
                prompt=str(item["prompt"]),
                system=str(item["system"]) if item.get("system") is not None else None,
                context=str(item["context"]) if item.get("context") is not None else None,
                expect=_parse_expectation(item),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return cases
