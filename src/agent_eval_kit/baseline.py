from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import CheckResult, EvalResult, ToolCall


@dataclass
class BaselineThresholds:
    max_case_regressions: int = 0
    max_pass_rate_drop: float = 0.0
    max_latency_increase_pct: float | None = None
    max_judge_score_drop: float | None = None


@dataclass
class BaselineComparison:
    passed: bool
    case_regressions: list[str] = field(default_factory=list)
    pass_rate_drop: float = 0.0
    latency_increase_pct: float = 0.0
    judge_score_drop: float = 0.0
    reasons: list[str] = field(default_factory=list)


def load_report(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "summary" not in data or "results" not in data:
        raise ValueError("Baseline must be an Agent Eval Kit JSON report.")
    return data


def report_results(report: dict[str, Any]) -> list[EvalResult]:
    results: list[EvalResult] = []
    for item in report["results"]:
        checks = {
            str(name): CheckResult(
                passed=bool(value.get("passed")),
                detail=str(value.get("detail", "")),
                score=(
                    float(value["score"])
                    if isinstance(value.get("score"), int | float)
                    else None
                ),
            )
            for name, value in (item.get("checks") or {}).items()
        }
        tool_calls = [
            ToolCall(
                name=str(call.get("name", "")),
                arguments=call.get("arguments", {}),
                id=str(call["id"]) if call.get("id") is not None else None,
            )
            for call in item.get("tool_calls") or []
        ]
        results.append(
            EvalResult(
                id=str(item["id"]),
                passed=bool(item.get("passed")),
                response=str(item.get("response", "")),
                latency_ms=float(item.get("latency_ms", 0.0)),
                checks=checks,
                error=str(item["error"]) if item.get("error") is not None else None,
                metadata=dict(item.get("metadata") or {}),
                tool_calls=tool_calls,
            )
        )
    return results


def _avg_judge_from_payload(results: list[dict[str, Any]]) -> float | None:
    scores: list[float] = []
    for result in results:
        checks = result.get("checks") or {}
        judge = checks.get("judge") or {}
        score = judge.get("score")
        if isinstance(score, int | float):
            scores.append(float(score))
    return sum(scores) / len(scores) if scores else None


def _avg_judge_from_results(results: list[EvalResult]) -> float | None:
    scores = [
        check.score
        for result in results
        for name, check in result.checks.items()
        if name == "judge" and check.score is not None
    ]
    return sum(scores) / len(scores) if scores else None


def compare_results(
    baseline: dict[str, Any],
    current: list[EvalResult],
    thresholds: BaselineThresholds,
) -> BaselineComparison:
    baseline_results = baseline["results"]
    baseline_by_id = {str(item["id"]): item for item in baseline_results}
    current_by_id = {item.id: item for item in current}

    case_regressions = [
        case_id
        for case_id, previous in baseline_by_id.items()
        if previous.get("passed") is True
        and case_id in current_by_id
        and not current_by_id[case_id].passed
    ]

    baseline_pass_rate = float(baseline["summary"].get("pass_rate", 0.0))
    current_pass_rate = (
        sum(item.passed for item in current) / len(current) * 100 if current else 0.0
    )
    pass_rate_drop = max(0.0, baseline_pass_rate - current_pass_rate)

    baseline_latency = float(baseline["summary"].get("avg_latency_ms", 0.0))
    current_latency = (
        sum(item.latency_ms for item in current) / len(current) if current else 0.0
    )
    latency_increase_pct = 0.0
    if baseline_latency > 0:
        latency_increase_pct = max(
            0.0,
            (current_latency - baseline_latency) / baseline_latency * 100,
        )

    baseline_judge = _avg_judge_from_payload(baseline_results)
    current_judge = _avg_judge_from_results(current)
    judge_score_drop = 0.0
    if baseline_judge is not None and current_judge is not None:
        judge_score_drop = max(0.0, baseline_judge - current_judge)

    reasons: list[str] = []
    if len(case_regressions) > thresholds.max_case_regressions:
        reasons.append(
            f"{len(case_regressions)} case regressions exceed "
            f"limit {thresholds.max_case_regressions}."
        )
    if pass_rate_drop > thresholds.max_pass_rate_drop:
        reasons.append(
            f"Pass-rate drop {pass_rate_drop:.2f}pp exceeds "
            f"limit {thresholds.max_pass_rate_drop:.2f}pp."
        )
    if (
        thresholds.max_latency_increase_pct is not None
        and latency_increase_pct > thresholds.max_latency_increase_pct
    ):
        reasons.append(
            f"Latency increase {latency_increase_pct:.2f}% exceeds "
            f"limit {thresholds.max_latency_increase_pct:.2f}%."
        )
    if (
        thresholds.max_judge_score_drop is not None
        and judge_score_drop > thresholds.max_judge_score_drop
    ):
        reasons.append(
            f"Judge-score drop {judge_score_drop:.3f} exceeds "
            f"limit {thresholds.max_judge_score_drop:.3f}."
        )

    return BaselineComparison(
        passed=not reasons,
        case_regressions=case_regressions,
        pass_rate_drop=pass_rate_drop,
        latency_increase_pct=latency_increase_pct,
        judge_score_drop=judge_score_drop,
        reasons=reasons,
    )
