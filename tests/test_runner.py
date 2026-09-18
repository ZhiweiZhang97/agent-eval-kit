from agent_eval_kit.client import ChatResponse
from agent_eval_kit.models import Expectation, ToolCall
from agent_eval_kit.models import TestCase as EvalCase
from agent_eval_kit.runner import run_cases


class FakeClient:
    def chat(self, **kwargs):
        assert "tools" in kwargs
        return ChatResponse(
            content="hello world",
            latency_ms=5.0,
            raw={},
            tool_calls=[ToolCall(name="search", arguments={"query": "x"})],
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
