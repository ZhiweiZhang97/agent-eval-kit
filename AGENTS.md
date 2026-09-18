# AGENTS.md

## Project goal
Keep Agent Eval Kit small, dependable, provider-agnostic, and easy to run locally or in CI.

## Development rules
- Python 3.10+.
- Add or update tests for every behavior change.
- Avoid provider-specific SDKs in core code; prefer OpenAI-compatible HTTP interfaces.
- Prefer deterministic evaluators over LLM judges when a deterministic contract is possible.
- Preserve backwards compatibility for documented YAML formats unless a major version explicitly changes them.
- Keep configuration explicit and public examples runnable with synthetic data.
- Do not commit API keys, private endpoints, customer data, or generated reports containing sensitive prompts.
- Run `ruff check .`, `pytest -q`, and `python -m build` before submitting changes.

## Architecture
- `loaders.py`: YAML parsing and compatibility handling.
- `models.py`: public evaluation data structures.
- `client.py`: OpenAI-compatible HTTP client and retry logic.
- `evaluator.py`: deterministic checks and judge integration contract.
- `judge.py`: optional LLM-as-a-Judge implementation.
- `runner.py`: concurrency and continue-on-error orchestration.
- `reporting.py`: JSON, Markdown, HTML, and JUnit outputs.
- `cli.py`: user-facing Typer commands.

## Good contribution areas
- Tool-call and agent-trajectory evaluators.
- RAG faithfulness / citation attribution.
- Semantic similarity and embedding adapters.
- Baseline comparison and regression thresholds.
- Pluggable custom evaluator API.
- Dataset adapters and richer reports.
