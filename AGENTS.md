# AGENTS.md

## Project goal

Keep Agent Eval Kit small, dependable, provider-agnostic, and useful for response, RAG, and tool-calling regression tests.

## Development rules

- Python 3.10+.
- Add or update tests for every behavior change.
- Avoid provider-specific SDKs in core code; prefer OpenAI-compatible HTTP interfaces.
- Prefer deterministic evaluators over LLM judges when a deterministic contract is possible.
- Preserve documented YAML compatibility unless a major version explicitly changes it.
- Treat JSON report fields as an emerging public interface; version schema changes.
- Keep configuration explicit and public examples runnable with synthetic data.
- Do not commit API keys, private endpoints, customer data, or sensitive reports.
- Run `ruff check .`, `pytest -q`, and `python -m build` before submitting changes.

## Architecture

- `loaders.py`: YAML parsing and backwards compatibility.
- `models.py`: public evaluation and tool-call data structures.
- `client.py`: OpenAI-compatible HTTP client, tools, retry logic, tool normalization.
- `evaluator.py`: deterministic response, RAG, and tool-call assertions.
- `plugins.py`: custom evaluator registry and explicit plugin loading.
- `judge.py`: optional LLM-as-a-Judge implementation.
- `runner.py`: concurrent, continue-on-error orchestration.
- `baseline.py`: report loading and regression thresholds.
- `reporting.py`: versioned JSON plus Markdown, HTML, and JUnit outputs.
- `cli.py`: validation, execution, plugin loading, and baseline comparison.

## Good contribution areas

- Claim-level RAG faithfulness.
- Multi-turn agent trajectory imports.
- Semantic similarity evaluators with optional dependencies.
- Baseline and PR diff presentation.
- Rate-limit aware scheduling.
- Dataset adapters.
