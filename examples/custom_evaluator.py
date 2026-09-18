from agent_eval_kit.models import CheckResult
from agent_eval_kit.plugins import evaluator


@evaluator("short-answer")
def short_answer(case, response, tool_calls, config):
    del case, tool_calls
    maximum = int(config.get("max_chars", 500))
    length = len(response)
    return CheckResult(
        length <= maximum,
        f"Response length is {length}; maximum is {maximum}.",
    )
