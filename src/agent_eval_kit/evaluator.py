from __future__ import annotations

from collections.abc import Callable
import json
import re

from jsonschema import SchemaError, ValidationError, validate

from .models import CheckResult, EvalResult, TestCase

JudgeFn = Callable[[TestCase, str], tuple[float, str]]


def _extract_json(response: str) -> object:
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def evaluate_case(
    case: TestCase,
    response: str,
    latency_ms: float,
    judge_fn: JudgeFn | None = None,
) -> EvalResult:
    checks: dict[str, CheckResult] = {}

    for token in case.expect.contains:
        ok = token.lower() in response.lower()
        checks[f"contains:{token}"] = CheckResult(ok, f"Expected response to contain {token!r}.")

    for token in case.expect.not_contains:
        ok = token.lower() not in response.lower()
        checks[f"not_contains:{token}"] = CheckResult(
            ok, f"Expected response not to contain {token!r}."
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
            checks["json_schema"] = CheckResult(True, "Response is valid JSON matching the schema.")
        except (json.JSONDecodeError, ValidationError, SchemaError) as exc:
            checks["json_schema"] = CheckResult(False, f"JSON Schema validation failed: {exc}")

    citations = case.expect.citations
    if citations is not None:
        for required in citations.required:
            ok = required in response
            checks[f"citation:{required}"] = CheckResult(
                ok, f"Required citation {required!r} was not found."
            )
        try:
            count = len(re.findall(citations.pattern, response))
            ok = count >= citations.min_count
            checks["citations:min_count"] = CheckResult(
                ok,
                f"Found {count} citation-like references; required at least {citations.min_count}.",
            )
        except re.error as exc:
            checks["citations:min_count"] = CheckResult(False, f"Invalid citation regex: {exc}")

    if case.expect.max_latency_ms is not None:
        ok = latency_ms <= case.expect.max_latency_ms
        checks["latency"] = CheckResult(
            ok,
            f"Latency {latency_ms:.1f} ms; limit {case.expect.max_latency_ms:.1f} ms.",
        )

    if case.expect.judge is not None:
        if judge_fn is None:
            checks["judge"] = CheckResult(
                False, "Judge is configured for the case but no judge model was provided."
            )
        else:
            try:
                score, detail = judge_fn(case, response)
                ok = score >= case.expect.judge.min_score
                checks["judge"] = CheckResult(ok, detail, score=score)
            except Exception as exc:
                checks["judge"] = CheckResult(False, f"Judge failed: {exc}")

    passed = all(check.passed for check in checks.values()) if checks else True
    return EvalResult(
        id=case.id,
        passed=passed,
        response=response,
        latency_ms=latency_ms,
        checks=checks,
        metadata=case.metadata,
    )
