from agent_eval_kit.models import CheckResult, TestCase as EvalCase
from agent_eval_kit.plugins import (
    clear_evaluators,
    evaluator,
    run_custom_evaluator,
)


def test_custom_evaluator_registry():
    clear_evaluators()

    @evaluator("short-answer")
    def short_answer(case, response, tool_calls, config):
        del case, tool_calls
        maximum = int(config["max_chars"])
        return CheckResult(len(response) <= maximum, "length check")

    result = run_custom_evaluator(
        "short-answer",
        EvalCase(id="x", prompt="q"),
        "short",
        [],
        {"max_chars": 10},
    )
    assert result.passed is True
