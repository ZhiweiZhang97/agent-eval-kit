from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .client import OpenAICompatibleClient
from .judge import LLMJudge
from .loaders import load_cases
from .models import EvalResult
from .reporting import summary, write_html, write_json, write_junit, write_markdown
from .runner import run_cases

app = typer.Typer(help="Regression evaluation for LLM agents and RAG applications.")
console = Console()


@app.command()
def validate(file: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Validate an evaluation YAML file without calling a model."""
    cases = load_cases(file)
    console.print(f"[green]OK[/green] {len(cases)} cases loaded from {file}")


@app.command()
def run(
    file: Path = typer.Argument(..., exists=True, readable=True),
    base_url: str = typer.Option(..., envvar="OPENAI_BASE_URL"),
    model: str = typer.Option(..., envvar="OPENAI_MODEL"),
    api_key: str | None = typer.Option(None, envvar="OPENAI_API_KEY"),
    workers: int = typer.Option(4, min=1, max=64, help="Number of cases to execute concurrently."),
    retries: int = typer.Option(2, min=0, max=10, help="Retries for transient API errors."),
    timeout: float = typer.Option(60.0, min=1.0),
    judge_model: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_MODEL"),
    judge_base_url: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_BASE_URL"),
    judge_api_key: str | None = typer.Option(None, envvar="AGENT_EVAL_JUDGE_API_KEY"),
    out_dir: Path = typer.Option(Path("agent-eval-results")),
) -> None:
    """Run evaluation cases against an OpenAI-compatible endpoint."""
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
    table.add_column("Checks")
    for result in results:
        table.add_row(
            result.id,
            "PASS" if result.passed else "FAIL",
            f"{result.latency_ms:.1f} ms",
            str(len(result.checks)),
        )
    console.print(table)
    console.print(summary(results))
    console.print(f"Reports: {out_dir}")

    if any(not result.passed for result in results):
        raise typer.Exit(code=1)
