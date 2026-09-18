from agent_eval_kit.client import ChatResponse
from agent_eval_kit.models import Expectation, TestCase as EvalCase
from agent_eval_kit.runner import run_cases


class FakeClient:
    def chat(self, **kwargs):
        return ChatResponse(content="hello world", latency_ms=5.0, raw={})


def test_parallel_runner_preserves_case_order():
    cases = [
        EvalCase(id="a", prompt="a", expect=Expectation(contains=["hello"])),
        EvalCase(id="b", prompt="b", expect=Expectation(contains=["world"])),
    ]
    results = run_cases(cases, FakeClient(), model="fake", workers=2)  # type: ignore[arg-type]
    assert [r.id for r in results] == ["a", "b"]
    assert all(r.passed for r in results)
