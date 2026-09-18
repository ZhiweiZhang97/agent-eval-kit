from agent_eval_kit.client import ChatResponse
from agent_eval_kit.models import Expectation, ToolCall
from agent_eval_kit.models import TestCase as EvalCase
from agent_eval_kit.runner import run_cases


class FakeClient:
    def __init__(self):
        self.calls = 0

    def chat(self, **kwargs):
        assert "tools" in kwargs
        self.calls += 1
        return ChatResponse(
            content="hello world",
            latency_ms=float(self.calls * 10),
            raw={},
            tool_calls=[ToolCall(name="search", arguments={"query": "x"})],
        )


class FlakyClient:
    def __init__(self):
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        content = "good" if self.calls != 2 else "bad"
        return ChatResponse(
            content=content,
            latency_ms=10.0,
            raw={},
            tool_calls=[],
        )


def test_parallel_runner_preserves_case_order():
    cases = [
        EvalCase(id="a", prompt="a", expect=Expectation(contains=["hello"])),
        EvalCase(id="b", prompt="b", expect=Expectation(contains=["world"])),
    ]
    results = run_cases(cases, FakeClient(), model="fake", workers=2)  # type: ignore[arg-type]
    assert [result.id for result in results] == ["a", "b"]
    assert all(result.passed for result in results)
    assert results[0].tool_calls[0].name == "search"


def test_repeated_runs_report_stability_and_variance():
    case = EvalCase(
        id="stable",
        prompt="q",
        expect=Expectation(contains=["good"]),
    )
    result = run_cases(
        [case],
        FlakyClient(),  # type: ignore[arg-type]
        model="fake",
        repeats=3,
        min_repeat_pass_rate=0.66,
    )[0]
    assert result.sample_count == 3
    assert result.pass_count == 2
    assert round(result.sample_pass_rate, 3) == 0.667
    assert result.passed is True
    assert result.checks["repeat:pass_rate"].passed is True


def test_repeated_runs_can_fail_stability_gate():
    case = EvalCase(
        id="strict",
        prompt="q",
        expect=Expectation(contains=["good"]),
    )
    result = run_cases(
        [case],
        FlakyClient(),  # type: ignore[arg-type]
        model="fake",
        repeats=3,
        min_repeat_pass_rate=1.0,
    )[0]
    assert result.passed is False
    assert result.checks["repeat:pass_rate"].passed is False
