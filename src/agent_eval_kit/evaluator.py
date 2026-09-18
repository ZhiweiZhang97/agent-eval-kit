from __future__ import annotations

import json
import re
from collections.abc import Callable

from jsonschema import SchemaError, ValidationError, validate

from .models import CheckResult, EvalResult, TestCase, ToolCall
from .plugins import run_custom_evaluator

JudgeFn = Callable[[TestCase, str], tuple[float, str]]


def _extract_json(response: str) -> object:
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _ordered_subsequence(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return True
    index = 0
    for name in actual:
        if name == expected[index]:
            index += 1
            if index == len(expected):
                return True
    return False


def _evaluate_citations(
    case: TestCase,
    response: str,
    checks: dict[str, CheckResult],
) -> None:
    citations = case.expect.citations
    if citations is None:
        return

    for required in citations.required:
        ok = required in response
        checks[f"citation:{required}"] = CheckResult(
            ok,
            f"Required citation {required!r} was not found.",
        )

    try:
        cited = re.findall(citations.pattern, response)
        context_sources = re.findall(citations.pattern, case.context or "")
    except re.error as exc:
        checks["citations:pattern"] = CheckResult(False, f"Invalid citation regex: {exc}")
        return

    checks["citations:min_count"] = CheckResult(
        len(cited) >= citations.min_count,
        f"Found {len(cited)} citation-like references; required {citations.min_count}.",
    )

    if citations.validate_sources or citations.min_precision is not None:
        context_set = set(context_sources)
        valid_count = sum(token in context_set for token in cited)
        precision = valid_count / len(cited) if cited else 0.0
        minimum = citations.min_precision if citations.min_precision is not None else 1.0
        checks["citations:precision"] = CheckResult(
            precision >= minimum,
            f"Citation precision {precision:.3f}; required at least {minimum:.3f}.",
            score=precision,
        )

    if citations.min_source_coverage is not None:
        context_set = set(context_sources)
        valid_cited = set(cited) & context_set
        coverage = len(valid_cited) / len(context_set) if context_set else 0.0
        checks["citations:source_coverage"] = CheckResult(
            coverage >= citations.min_source_coverage,
            (
                f"Context-source coverage {coverage:.3f}; required at least "
                f"{citations.min_source_coverage:.3f}."
            ),
            score=coverage,
        )


def _evaluate_tool_calls(
    case: TestCase,
    tool_calls: list[ToolCall],
    checks: dict[str, CheckResult],
) -> None:
    spec = case.expect.tool_calls
    if spec is None:
        return

    names = [call.name for call in tool_calls]
    for name in spec.required:
        checks[f"tool:required:{name}"] = CheckResult(
            name in names,
            f"Required tool {name!r} was not called.",
        )

    for name in spec.forbidden:
        checks[f"tool:forbidden:{name}"] = CheckResult(
            name not in names,
            f"Forbidden tool {name!r} was called.",
        )

    if spec.ordered:
        checks["tool:ordered"] = CheckResult(
            _ordered_subsequence(spec.ordered, names),
            f"Expected ordered tool subsequence {spec.ordered!r}; observed {names!r}.",
        )

    if spec.max_count is not None:
        checks["tool:max_count"] = CheckResult(
            len(tool_calls) <= spec.max_count,
            f"Observed {len(tool_calls)} tool calls; maximum is {spec.max_count}.",
        )

    for tool_name, schema in spec.args_schema.items():
        matching = [call for call in tool_calls if call.name == tool_name]
        if not matching:
            checks[f"tool:args_schema:{tool_name}"] = CheckResult(
                False,
                f"No call to {tool_name!r} was available for argument validation.",
            )
            continue

        errors: list[str] = []
        for index, call in enumerate(matching, start=1):
            try:
                validate(call.arguments, schema)
            except (ValidationError, SchemaError) as exc:
                errors.append(f"call #{index}: {exc.message}")
        checks[f"tool:args_schema:{tool_name}"] = CheckResult(
            not errors,
            "; ".join(errors) if errors else f"All {tool_name!r} arguments match the schema.",
        )


def evaluate_case(
    case: TestCase,
    response: str,
    latency_ms: float,
    judge_fn: JudgeFn | None = None,
    tool_calls: list[ToolCall] | None = None,
) -> EvalResult:
    calls = tool_calls or []
    checks: dict[str, CheckResult] = {}

    for token in case.expect.contains:
        ok = token.lower() in response.lower()
        checks[f"contains:{token}"] = CheckResult(
            ok,
            f"Expected response to contain {token!r}.",
        )

    for token in case.expect.not_contains:
        ok = token.lower() not in response.lower()
        checks[f"not_contains:{token}"] = CheckResult(
            ok,
            f"Expected response not to contain {token!r}.",
        )

    for pattern in case.expect.regex:
        try:
            ok = re.search(pattern, response, flags=re.MULTILINE) is not None
            detail = f"Expected regex to match: {pattern!r}."
        except re.error as exc:
            ok = False
            detail = f"Invalid regex {pattern!r}: {exc}"
        checks[f"regex:{pattern}"] = CheckResult(ok, detail)

    if case.expect.json_schema is not None:
        try:
            parsed = _extract_json(response)
            validate(parsed, case.expect.json_schema)
            checks["json_schema"] = CheckResult(
                True,
                "Response is valid JSON matching the schema.",
            )
        except (json.JSONDecodeError, ValidationError, SchemaError) as exc:
            checks["json_schema"] = CheckResult(
                False,
                f"JSON Schema validation failed: {exc}",
            )

    _evaluate_citations(case, response, checks)
    _evaluate_tool_calls(case, calls, checks)

    if case.expect.max_latency_ms is not None:
        ok = latency_ms <= case.expect.max_latency_ms
        checks["latency"] = CheckResult(
            ok,
            f"Latency {latency_ms:.1f} ms; limit {case.expect.max_latency_ms:.1f} ms.",
        )

    if case.expect.judge is not None:
        if judge_fn is None:
            checks["judge"] = CheckResult(
                False,
                "Judge is configured for the case but no judge model was provided.",
            )
        else:
            try:
                score, detail = judge_fn(case, response)
                ok = score >= case.expect.judge.min_score
                checks["judge"] = CheckResult(ok, detail, score=score)
            except Exception as exc:
                checks["judge"] = CheckResult(False, f"Judge failed: {exc}")

    for custom in case.expect.custom:
        checks[f"custom:{custom.name}"] = run_custom_evaluator(
            custom.name,
            case,
            response,
            calls,
            custom.config,
        )

    passed = all(check.passed for check in checks.values()) if checks else True
    return EvalResult(
        id=case.id,
        passed=passed,
        response=response,
        latency_ms=latency_ms,
        checks=checks,
        metadata=case.metadata,
        tool_calls=calls,
    )
