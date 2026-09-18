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
    load_report,
    report_results,
)
from .client import OpenAICompatibleClient
from .judge import LLMJudge
from .loaders import load_cases
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
    if not comparison.passed:
        raise typer.Exit(code=1)


@app.command()
def run(
    file: Path = typer.Argument(..., exists=True, readable=True),
    base_url: str = typer.Option(..., envvar="OPENAI_BASE_URL"),
    model: str = typer.Option(..., envvar="OPENAI_MODEL"),
    api_key: str | None = typer.Option(None, envvar="OPENAI_API_KEY"),
    workers: int = typer.Option(4, min=1, max=64),
    retries: int = typer.Option(2, min=0, max=10),
    timeout: float = typer.Option(60.0, min=1.0),
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
    )

    judge_fn = None
    if any(case.expect.judge for case in cases):
        if judge_model:
            judge_client = OpenAICompatibleClient(
                base_url=judge_base_url or base_url,
                api_key=judge_api_key or api_key,
                timeout=timeout,
                retries=retries,
            )
            judge_fn = LLMJudge(judge_client, judge_model)
        else:
            console.print(
                "[yellow]Warning:[/yellow] judge checks exist but --judge-model was not set."
            )

    def progress(result: EvalResult) -> None:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"{status} {result.id}")

    results = run_cases(
        cases=cases,
        client=client,
        model=model,
        workers=workers,
        judge_fn=judge_fn,
        progress=progress,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "report.json", results)
    write_markdown(out_dir / "report.md", results)
    write_html(out_dir / "report.html", results)
    write_junit(out_dir / "junit.xml", results)

    table = Table(title="Agent Eval Kit")
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Tools")
    table.add_column("Checks")
    for result in results:
        table.add_row(
            result.id,
            "PASS" if result.passed else "FAIL",
            f"{result.latency_ms:.1f} ms",
            ", ".join(call.name for call in result.tool_calls) or "-",
            str(len(result.checks)),
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
        baseline_passed = comparison.passed

    if any(not result.passed for result in results) or not baseline_passed:
        raise typer.Exit(code=1)
