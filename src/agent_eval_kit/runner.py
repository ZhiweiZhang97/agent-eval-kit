from __future__ import annotations

import statistics
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import OpenAICompatibleClient
from .evaluator import JudgeFn, evaluate_case
from .models import CheckResult, EvalResult, TestCase

ProgressFn = Callable[[EvalResult], None]


def _judge_score(result: EvalResult) -> float | None:
    check = result.checks.get("judge")
    return check.score if check is not None else None


def _aggregate_check(
    name: str,
    samples: list[EvalResult],
    min_repeat_pass_rate: float,
) -> CheckResult:
    observed = [sample.checks[name] for sample in samples if name in sample.checks]
    if not observed:
        return CheckResult(False, f"Check {name!r} was not observed in any sample.")

    passed = sum(check.passed for check in observed)
    rate = passed / len(samples)
    scores = [check.score for check in observed if check.score is not None]
    score = statistics.mean(scores) if scores else rate
    example_failure = next(
        (check.detail for check in observed if not check.passed),
        "",
    )
    detail = (
        f"{passed}/{len(samples)} samples passed check {name!r} "
        f"({rate:.3f}); required {min_repeat_pass_rate:.3f}."
    )
    if example_failure:
        detail += f" Example failure: {example_failure}"
    return CheckResult(
        passed=rate >= min_repeat_pass_rate,
        detail=detail,
        score=score,
    )


def _aggregate_samples(
    case_id: str,
    samples: list[EvalResult],
    min_repeat_pass_rate: float,
) -> EvalResult:
    if len(samples) == 1:
        result = samples[0]
        result.sample_count = 1
        result.pass_count = 1 if result.passed else 0
        return result

    pass_count = sum(sample.passed for sample in samples)
    pass_rate = pass_count / len(samples)
    latencies = [sample.latency_ms for sample in samples]
    judge_scores = [
        score
        for sample in samples
        if (score := _judge_score(sample)) is not None
    ]
    representative = samples[-1]

    check_names = sorted(
        {
            name
            for sample in samples
            for name in sample.checks
        }
    )
    checks = {
        name: _aggregate_check(name, samples, min_repeat_pass_rate)
        for name in check_names
    }
    checks["repeat:pass_rate"] = CheckResult(
        passed=pass_rate >= min_repeat_pass_rate,
        detail=(
            f"{pass_count}/{len(samples)} complete samples passed "
            f"({pass_rate:.3f}); required {min_repeat_pass_rate:.3f}."
        ),
        score=pass_rate,
    )

    errors = [sample.error for sample in samples if sample.error]
    error = "; ".join(dict.fromkeys(errors)) if errors else None
    latency_stddev = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0
    judge_stddev = (
        statistics.pstdev(judge_scores) if len(judge_scores) > 1 else 0.0
    ) if judge_scores else None

    return EvalResult(
        id=case_id,
        passed=all(check.passed for check in checks.values()),
        response=representative.response,
        latency_ms=statistics.mean(latencies),
        checks=checks,
        error=error,
        metadata=representative.metadata,
        tool_calls=representative.tool_calls,
        sample_count=len(samples),
        pass_count=pass_count,
        latency_stddev_ms=latency_stddev,
        judge_score_stddev=judge_stddev,
    )


def run_cases(
    cases: list[TestCase],
    client: OpenAICompatibleClient,
    model: str,
    workers: int = 4,
    judge_fn: JudgeFn | None = None,
    progress: ProgressFn | None = None,
    repeats: int = 1,
    min_repeat_pass_rate: float = 1.0,
) -> list[EvalResult]:
    workers = max(1, workers)
    repeats = max(1, repeats)
    min_repeat_pass_rate = min(1.0, max(0.0, min_repeat_pass_rate))

    def run_once(case: TestCase) -> EvalResult:
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

    def run_case(case: TestCase) -> EvalResult:
        samples = [run_once(case) for _ in range(repeats)]
        return _aggregate_samples(case.id, samples, min_repeat_pass_rate)

    by_id: dict[str, EvalResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_case = {pool.submit(run_case, case): case for case in cases}
        for future in as_completed(future_to_case):
            result = future.result()
            by_id[result.id] = result
            if progress:
                progress(result)

    return [by_id[case.id] for case in cases]
