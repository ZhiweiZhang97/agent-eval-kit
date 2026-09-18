from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .baseline import (
    BaselineComparison,
    BaselineThresholds,
    compare_results,
    comparison_markdown,
    load_report,
    report_results,
)
from .client import OpenAICompatibleClient
from .judge import LLMJudge
from .loaders import load_cases
from .matrix import load_targets, write_matrix_json, write_matrix_markdown
from .models import EvalResult
from .plugins import load_plugin
from .reporting import summary, write_html, write_json, write_junit, write_markdown
from .runner import run_cases

app = typer.Typer(
    help="Regression evaluation for LLM agents and RAG applications.",
    no_args_is_help=True,
)
console = Console()


def _thresholds(
    max_case_regressions: int,
    max_pass_rate_drop: float,
    max_latency_increase_pct: float | None,
    max_judge_score_drop: float | None,
) -> BaselineThresholds:
    return BaselineThresholds(
        max_case_regressions=max_case_regressions,
        max_pass_rate_drop=max_pass_rate_drop,
        max_latency_increase_pct=max_latency_increase_pct,
        max_judge_score_drop=max_judge_score_drop,
    )


def _show_comparison(comparison: BaselineComparison) -> None:
    status = "[green]PASS[/green]" if comparison.passed else "[red]FAIL[/red]"
    console.print(f"Baseline regression gate: {status}")
    console.print(
        {
            "case_regressions": comparison.case_regressions,
            "pass_rate_drop_pp": round(comparison.pass_rate_drop, 2),
            "latency_increase_pct": round(comparison.latency_increase_pct, 2),
            "judge_score_drop": round(comparison.judge_score_drop, 4),
        }
    )
    for reason in comparison.reasons:
        console.print(f"[red]- {reason}[/red]")


def _make_judge(
    judge_model: str | None,
    judge_base_url: str | None,
    judge_api_key: str | None,
    fallback_base_url: str,
    fallback_api_key: str | None,
    timeout: float,
    retries: int,
) -> LLMJudge | None:
    if not judge_model:
        return None
    judge_client = OpenAICompatibleClient(
        base_url=judge_base_url or fallback_base_url,
        api_key=judge_api_key or fallback_api_key,
        timeout=timeout,
        retries=retries,
    )
    return LLMJudge(judge_client, judge_model)


@app.command()
def validate(file: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Validate an evaluation YAML file without calling a model."""
    cases = load_cases(file)
    console.print(f"[green]OK[/green] {len(cases)} cases loaded from {file}")


@app.command()
def compare(
    baseline: Path = typer.Argument(..., exists=True, readable=True),
    current: Path = typer.Argument(..., exists=True, readable=True),
    max_case_regressions: int = typer.Option(0, min=0),
    max_pass_rate_drop: float = typer.Option(0.0, min=0.0),
    max_latency_increase_pct: float | None = typer.Option(None, min=0.0),
    max_judge_score_drop: float | None = typer.Option(None, min=0.0),
    markdown_out: Path | None = typer.Option(None, help="Write a PR-friendly diff."),
) -> None:
    """Compare two JSON reports and fail when regression thresholds are exceeded."""
    previous = load_report(baseline)
    current_report = load_report(current)
    comparison = compare_results(
        previous,
        report_results(current_report),
        _thresholds(
            max_case_regressions,
            max_pass_rate_drop,
            max_latency_increase_pct,
            max_judge_score_drop,
        ),
    )
    _show_comparison(comparison)
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(comparison_markdown(comparison), encoding="utf-8")
    if not comparison.passed:
        raise typer.Exit(code=1)


@app.command()
def matrix(
    file: Path = typer.Argument(..., exists=True, readable=True),
    config: Path = typer.Argument(..., exists=True, readable=True),
    workers: int = typer.Option(4, min=1, max=64),
    repeats: int = typer.Option(1, min=1, max=100),
    min_repeat_pass_rate: float = typer.Option(1.0, min=0.0, max=1.0),
    retries: int = typer.Option(2, min=0, max=10),
    timeout: float = typer.Option(60.0, min=1.0),
    out_dir: Path = typer.Option(Path("agent-eval-matrix")),
) -> None:
    """Run one suite against multiple model/endpoint targets."""
    cases = load_cases(file)
    targets = load_targets(config)
    if any(case.expect.judge for case in cases):
        raise typer.BadParameter(
            "Matrix mode currently requires deterministic checks; "
            "remove judge expectations or use 'agent-eval run'."
        )

    all_results: dict[str, list[EvalResult]] = {}
    for target in targets:
        api_key = os.getenv(target.api_key_env)
        console.print(f"[bold]Running target:[/bold] {target.name} ({target.model})")
        client = OpenAICompatibleClient(
            base_url=target.base_url,
            api_key=api_key,
            timeout=timeout,
            retries=retries,
            min_interval_ms=target.min_interval_ms,
        )
        all_results[target.name] = run_cases(
            cases=cases,
            client=client,
            model=target.model,
            workers=workers,
            repeats=repeats,
            min_repeat_pass_rate=min_repeat_pass_rate,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_matrix_json(out_dir / "matrix.json", all_results, targets)
    write_matrix_markdown(out_dir / "matrix.md", all_results, targets)

    table = Table(title="Agent Eval Model Matrix")
    table.add_column("Target")
    table.add_column("Model")
    table.add_column("Case pass")
    table.add_column("Sample pass")
    table.add_column("Avg latency")
    by_name = {target.name: target for target in targets}
    for name, results in all_results.items():
        stats = summary(results)
        table.add_row(
            name,
            by_name[name].model,
            f"{stats['pass_rate']}%",
            f"{stats['sample_pass_rate']}%",
            f"{stats['avg_latency_ms']} ms",
        )
    console.print(table)
    if any(not result.passed for results in all_results.values() for result in results):
        raise typer.Exit(code=1)


@app.command()
def run(
    file: Path = typer.Argument(..., exists=True, readable=True),
    base_url: str = typer.Option(..., envvar="OPENAI_BASE_URL"),
    model: str = typer.Option(..., envvar="OPENAI_MODEL"),
    api_key: str | None = typer.Option(None, envvar="OPENAI_API_KEY"),
    workers: int = typer.Option(4, min=1, max=64),
    repeats: int = typer.Option(1, min=1, max=100),
    min_repeat_pass_rate: float = typer.Option(1.0, min=0.0, max=1.0),
    retries: int = typer.Option(2, min=0, max=10),
    timeout: float = typer.Option(60.0, min=1.0),
    min_request_interval_ms: float = typer.Option(0.0, min=0.0),
    judge_model: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_MODEL"),
    judge_base_url: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_BASE_URL"),
    judge_api_key: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_API_KEY"),
    plugin: list[str] = typer.Option([], "--plugin", help="Module name or .py evaluator plugin."),
    baseline: Path | None = typer.Option(None, help="Previous report.json used as a CI gate."),
    max_case_regressions: int = typer.Option(0, min=0),
    max_pass_rate_drop: float = typer.Option(0.0, min=0.0),
    max_latency_increase_pct: float | None = typer.Option(None, min=0.0),
    max_judge_score_drop: float | None = typer.Option(None, min=0.0),
    out_dir: Path = typer.Option(Path("agent-eval-results")),
) -> None:
    """Run evaluation cases against an OpenAI-compatible endpoint."""
    for target in plugin:
        load_plugin(target)

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    cases = load_cases(file)
    client = OpenAICompatibleClient(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        retries=retries,
        min_interval_ms=min_request_interval_ms,
    )

    judge_fn = _make_judge(
        judge_model,
        judge_base_url,
        judge_api_key,
        base_url,
        api_key,
        timeout,
        retries,
    )
    if any(case.expect.judge for case in cases) and judge_fn is None:
        console.print(
            "[yellow]Warning:[/yellow] judge checks exist but --judge-model was not set."
        )

    def progress(result: EvalResult) -> None:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        sample_info = (
            f" [{result.pass_count}/{result.sample_count}]"
            if result.sample_count > 1
            else ""
        )
        console.print(f"{status} {result.id}{sample_info}")

    results = run_cases(
        cases=cases,
        client=client,
        model=model,
        workers=workers,
        judge_fn=judge_fn,
        progress=progress,
        repeats=repeats,
        min_repeat_pass_rate=min_repeat_pass_rate,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "report.json", results)
    write_markdown(out_dir / "report.md", results)
    write_html(out_dir / "report.html", results)
    write_junit(out_dir / "junit.xml", results)

    table = Table(title="Agent Eval Kit")
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Samples")
    table.add_column("Latency")
    table.add_column("Tools")
    for result in results:
        table.add_row(
            result.id,
            "PASS" if result.passed else "FAIL",
            f"{result.pass_count}/{result.sample_count}",
            f"{result.latency_ms:.1f} ± {result.latency_stddev_ms:.1f} ms",
            ", ".join(call.name for call in result.tool_calls) or "-",
        )
    console.print(table)
    console.print(summary(results))
    console.print(f"Reports: {out_dir}")

    baseline_passed = True
    if baseline is not None:
        comparison = compare_results(
            load_report(baseline),
            results,
            _thresholds(
                max_case_regressions,
                max_pass_rate_drop,
                max_latency_increase_pct,
                max_judge_score_drop,
            ),
        )
        _show_comparison(comparison)
        (out_dir / "baseline-comparison.md").write_text(
            comparison_markdown(comparison),
            encoding="utf-8",
        )
        baseline_passed = comparison.passed

    if any(not result.passed for result in results) or not baseline_passed:
        raise typer.Exit(code=1)
