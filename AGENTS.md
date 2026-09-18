# AGENTS.md

## Project goal

Keep Agent Eval Kit small, dependable, provider-agnostic, and useful for response, RAG, tool-calling, and model-regression tests.

## Development rules

- Python 3.10+.
- Add or update tests for every behavior change.
- Avoid provider-specific SDKs in core code; prefer OpenAI-compatible HTTP interfaces.
- Prefer deterministic evaluators over LLM judges when a deterministic contract is possible.
- Preserve documented YAML compatibility unless a major version explicitly changes it.
- Treat JSON report fields as a public interface and version schema changes.
- Keep examples synthetic and safe to publish.
- Never commit credentials, private endpoints, customer data, or sensitive reports.
- Run `ruff check .`, `pytest -q`, and `python -m build` before submitting changes.

## Architecture

- `loaders.py`: YAML parsing and backwards compatibility.
- `models.py`: public evaluation, tool-call, and stability data structures.
- `client.py`: OpenAI-compatible HTTP client, pacing, retries, and tool normalization.
- `evaluator.py`: deterministic response, RAG, and tool-call assertions.
- `plugins.py`: custom evaluator registry and explicit plugin loading.
- `judge.py`: optional LLM-as-a-Judge implementation.
- `runner.py`: concurrent execution plus repeated-run aggregation.
- `baseline.py`: Baseline thresholds and per-case diffs.
- `matrix.py`: multi-model / multi-endpoint comparison configuration and reports.
- `redaction.py`: defense-in-depth report secret redaction.
- `reporting.py`: versioned JSON plus Markdown, HTML, and JUnit outputs.
- `cli.py`: validation, execution, compare, matrix, plugins, and Baseline gates.

## Good contribution areas

- Claim-level RAG faithfulness.
- Multi-turn agent trajectory imports.
- Semantic similarity evaluators with optional dependencies.
- Baseline and PR diff presentation.
- Dataset adapters.
- Usage/cost accounting.
