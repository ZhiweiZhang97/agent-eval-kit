# Roadmap

Agent Eval Kit aims to remain a small, inspectable regression framework rather than a hosted evaluation platform.

## v0.6 — Rich agent traces and RAG faithfulness

- Multi-turn trajectory objects rather than only single-response tool calls.
- Trace import adapters for common agent frameworks.
- Claim-level citation attribution.
- Optional semantic similarity evaluators.
- JSONL and CSV dataset adapters.

## v0.7 — CI and experiment ergonomics

- GitHub PR comment integration.
- Versioned baseline management helpers.
- Richer matrix diffs between candidate models.
- Historical trend aggregation from report files.
- Cost/token accounting when providers expose usage metadata.

## Toward 1.0

- Stabilize the YAML evaluation contract.
- Stabilize the JSON report schema.
- Define plugin API compatibility guarantees.
- Publish migration guides for breaking changes.
- Expand the documented security and privacy threat model.

## Non-goals

- Becoming a hosted evaluation SaaS.
- Requiring a specific model provider or SDK.
- Hiding evaluation logic behind opaque defaults.

Community feedback should shape priorities. Small, well-tested contributions that preserve provider independence are preferred.
