from agent_eval_kit.baseline import (
    BaselineThresholds,
    compare_results,
    comparison_markdown,
)
from agent_eval_kit.models import CheckResult, EvalResult, ToolCall


def _result(
    case_id: str,
    passed: bool,
    latency: float,
    judge: float | None = None,
    tools: list[str] | None = None,
):
    checks = {}
    if judge is not None:
        checks["judge"] = CheckResult(passed=True, score=judge)
    return EvalResult(
        id=case_id,
        passed=passed,
        response="ok",
        latency_ms=latency,
        checks=checks,
        tool_calls=[ToolCall(name=name) for name in tools or []],
    )


def test_baseline_detects_case_and_pass_rate_regression():
    baseline = {
        "summary": {"pass_rate": 100.0, "avg_latency_ms": 100.0},
        "results": [
            {"id": "a", "passed": True, "checks": {}},
            {"id": "b", "passed": True, "checks": {}},
        ],
    }
    current = [_result("a", True, 100), _result("b", False, 100)]
    comparison = compare_results(baseline, current, BaselineThresholds())
    assert comparison.passed is False
    assert comparison.case_regressions == ["b"]
    assert comparison.pass_rate_drop == 50.0


def test_baseline_latency_judge_and_case_diff():
    baseline = {
        "summary": {"pass_rate": 100.0, "avg_latency_ms": 100.0},
        "results": [
            {
                "id": "a",
                "passed": True,
                "latency_ms": 100.0,
                "tool_calls": [{"name": "search"}],
                "checks": {"judge": {"passed": True, "score": 0.9}},
            }
        ],
    }
    current = [_result("a", True, 130, judge=0.7, tools=["search", "summarize"])]
    comparison = compare_results(
        baseline,
        current,
        BaselineThresholds(
            max_latency_increase_pct=20.0,
            max_judge_score_drop=0.1,
        ),
    )
    assert comparison.passed is False
    assert comparison.latency_increase_pct == 30.0
    assert round(comparison.judge_score_drop, 2) == 0.2
    assert comparison.case_diffs[0].latency_delta_ms == 30.0
    assert comparison.case_diffs[0].after_tools == ["search", "summarize"]

    markdown = comparison_markdown(comparison)
    assert "Case diff" in markdown
    assert "search" in markdown
    assert "summarize" in markdown
