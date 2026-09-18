# Roadmap

Agent Eval Kit is intentionally small. The roadmap focuses on capabilities that make regression evaluation more useful in real agent and RAG delivery workflows without turning the core into a hosted platform.

## v0.3 — Baselines and extensibility

- Compare a run against a versioned baseline report.
- Fail CI on configurable pass-rate, latency, or judge-score regressions.
- Add a small custom-evaluator plugin interface.
- Improve report diffs for pull requests.

## v0.4 — Agent and RAG depth

- Tool-call and agent-trajectory assertions.
- Stronger citation attribution and RAG faithfulness checks.
- Optional semantic similarity evaluators.
- Dataset adapters for common JSONL/CSV evaluation sets.

## v0.5 — Reproducibility and scale

- Repeated runs and variance summaries.
- Rate-limit aware scheduling.
- Model/provider comparison matrices.
- Better HTML trend and comparison views.

## Non-goals

- Becoming a hosted evaluation SaaS.
- Requiring a specific model provider or SDK.
- Hiding evaluation logic behind opaque defaults.

Community feedback should shape priorities. Small, well-tested contributions that preserve provider independence are preferred.
