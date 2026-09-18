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
class CaseDiff:
    id: str
    before_passed: bool
    after_passed: bool
    latency_delta_ms: float
    latency_delta_pct: float | None
    judge_delta: float | None
    before_tools: list[str] = field(default_factory=list)
    after_tools: list[str] = field(default_factory=list)


@dataclass
class BaselineComparison:
    passed: bool
    case_regressions: list[str] = field(default_factory=list)
    pass_rate_drop: float = 0.0
    latency_increase_pct: float = 0.0
    judge_score_drop: float = 0.0
    reasons: list[str] = field(default_factory=list)
    case_diffs: list[CaseDiff] = field(default_factory=list)


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
        passed = bool(item.get("passed"))
        results.append(
            EvalResult(
                id=str(item["id"]),
                passed=passed,
                response=str(item.get("response", "")),
                latency_ms=float(item.get("latency_ms", 0.0)),
                checks=checks,
                error=str(item["error"]) if item.get("error") is not None else None,
                metadata=dict(item.get("metadata") or {}),
                tool_calls=tool_calls,
                sample_count=int(item.get("sample_count", 1)),
                pass_count=int(item.get("pass_count", 1 if passed else 0)),
                latency_stddev_ms=float(item.get("latency_stddev_ms", 0.0)),
                judge_score_stddev=(
                    float(item["judge_score_stddev"])
                    if isinstance(item.get("judge_score_stddev"), int | float)
                    else None
                ),
            )
        )
    return results


def _judge_score_from_payload(item: dict[str, Any]) -> float | None:
    score = ((item.get("checks") or {}).get("judge") or {}).get("score")
    return float(score) if isinstance(score, int | float) else None


def _judge_score_from_result(item: EvalResult) -> float | None:
    check = item.checks.get("judge")
    return check.score if check is not None else None


def _avg_judge_from_payload(results: list[dict[str, Any]]) -> float | None:
    scores = [
        score
        for item in results
        if (score := _judge_score_from_payload(item)) is not None
    ]
    return sum(scores) / len(scores) if scores else None


def _avg_judge_from_results(results: list[EvalResult]) -> float | None:
    scores = [
        score
        for item in results
        if (score := _judge_score_from_result(item)) is not None
    ]
    return sum(scores) / len(scores) if scores else None


def _case_diff(previous: dict[str, Any], current: EvalResult) -> CaseDiff:
    before_latency = float(previous.get("latency_ms", 0.0))
    latency_delta = current.latency_ms - before_latency
    latency_pct = None
    if before_latency > 0:
        latency_pct = latency_delta / before_latency * 100

    before_judge = _judge_score_from_payload(previous)
    after_judge = _judge_score_from_result(current)
    judge_delta = None
    if before_judge is not None and after_judge is not None:
        judge_delta = after_judge - before_judge

    return CaseDiff(
        id=current.id,
        before_passed=bool(previous.get("passed")),
        after_passed=current.passed,
        latency_delta_ms=latency_delta,
        latency_delta_pct=latency_pct,
        judge_delta=judge_delta,
        before_tools=[
            str(call.get("name", ""))
            for call in previous.get("tool_calls") or []
        ],
        after_tools=[call.name for call in current.tool_calls],
    )


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

    case_diffs = [
        _case_diff(baseline_by_id[item.id], item)
        for item in current
        if item.id in baseline_by_id
    ]

    return BaselineComparison(
        passed=not reasons,
        case_regressions=case_regressions,
        pass_rate_drop=pass_rate_drop,
        latency_increase_pct=latency_increase_pct,
        judge_score_drop=judge_score_drop,
        reasons=reasons,
        case_diffs=case_diffs,
    )


def comparison_markdown(comparison: BaselineComparison) -> str:
    status = "PASS" if comparison.passed else "FAIL"
    lines = [
        "# Agent Eval Baseline Comparison",
        "",
        f"**Gate: {status}**",
        "",
        f"- Case regressions: **{len(comparison.case_regressions)}**",
        f"- Pass-rate drop: **{comparison.pass_rate_drop:.2f} pp**",
        f"- Latency increase: **{comparison.latency_increase_pct:.2f}%**",
        f"- Judge-score drop: **{comparison.judge_score_drop:.4f}**",
        "",
    ]
    if comparison.reasons:
        lines.extend(["## Gate failures", ""])
        lines.extend(f"- {reason}" for reason in comparison.reasons)
        lines.append("")

    lines.extend(
        [
            "## Case diff",
            "",
            "| Case | Before | After | Latency Δ | Judge Δ | Tool sequence |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for diff in comparison.case_diffs:
        latency = f"{diff.latency_delta_ms:+.1f} ms"
        if diff.latency_delta_pct is not None:
            latency += f" ({diff.latency_delta_pct:+.1f}%)"
        judge = "-" if diff.judge_delta is None else f"{diff.judge_delta:+.3f}"
        before_tools = " → ".join(diff.before_tools) or "-"
        after_tools = " → ".join(diff.after_tools) or "-"
        tool_change = (
            before_tools
            if before_tools == after_tools
            else f"{before_tools} → {after_tools}"
        )
        lines.append(
            f"| {diff.id} | {'PASS' if diff.before_passed else 'FAIL'} | "
            f"{'PASS' if diff.after_passed else 'FAIL'} | {latency} | "
            f"{judge} | {tool_change} |"
        )
    return "\n".join(lines) + "\n"
