from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import OpenAICompatibleClient
from .evaluator import JudgeFn, evaluate_case
from .models import CheckResult, EvalResult, TestCase

ProgressFn = Callable[[EvalResult], None]


def run_cases(
    cases: list[TestCase],
    client: OpenAICompatibleClient,
    model: str,
    workers: int = 4,
    judge_fn: JudgeFn | None = None,
    progress: ProgressFn | None = None,
) -> list[EvalResult]:
    workers = max(1, workers)

    def run_one(case: TestCase) -> EvalResult:
        try:
            chat = client.chat(
                model=model,
                prompt=case.prompt,
                system=case.system,
                context=case.context,
                tools=case.tools,
                tool_choice=case.tool_choice,
            )
            return evaluate_case(
                case,
                chat.content,
                chat.latency_ms,
                judge_fn=judge_fn,
                tool_calls=chat.tool_calls,
            )
        except Exception as exc:
            return EvalResult(
                id=case.id,
                passed=False,
                response="",
                latency_ms=0.0,
                checks={"request": CheckResult(False, str(exc))},
                error=str(exc),
                metadata=case.metadata,
            )

    by_id: dict[str, EvalResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_case = {pool.submit(run_one, case): case for case in cases}
        for future in as_completed(future_to_case):
            result = future.result()
            by_id[result.id] = result
            if progress:
                progress(result)

    return [by_id[case.id] for case in cases]
