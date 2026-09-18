# Roadmap

Agent Eval Kit aims to remain a small, inspectable regression framework rather than a hosted evaluation platform.

## v0.5 — Reproducibility and comparison

- Repeated runs and variance summaries for stochastic models.
- Model/provider comparison matrices.
- Per-case latency and judge-score regression diffs.
- Better PR-friendly Markdown summaries.
- Rate-limit aware scheduling.

## v0.6 — RAG and agent depth

- Claim-level citation attribution.
- Optional semantic similarity evaluators.
- Richer agent trajectory objects for multi-turn tool execution.
- Dataset adapters for JSONL and CSV.
- Optional trace import from common agent frameworks.

## Toward 1.0

- Stabilize the YAML evaluation contract.
- Stabilize the JSON report schema.
- Define plugin API compatibility guarantees.
- Publish migration guides for breaking changes.
- Add a documented security and privacy threat model.

## Non-goals

- Becoming a hosted evaluation SaaS.
- Requiring a specific model provider or SDK.
- Hiding evaluation logic behind opaque defaults.

Community feedback should shape priorities. Small, well-tested contributions that preserve provider independence are preferred.
