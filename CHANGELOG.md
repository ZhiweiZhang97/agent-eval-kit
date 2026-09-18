# Changelog

## 0.4.0 - 2026-09-18

### Added

- Baseline regression comparison with CI thresholds for:
  - previously passing cases that regress,
  - pass-rate drop,
  - average latency increase,
  - average LLM-judge score drop.
- `agent-eval compare` for comparing two existing JSON reports.
- OpenAI-compatible tool definitions and `tool_choice` in YAML cases.
- Normalized tool-call capture in evaluation reports.
- Agent tool-call assertions:
  - required and forbidden tools,
  - ordered tool trajectories,
  - maximum tool-call count,
  - per-tool argument JSON Schema.
- RAG citation-source validation, citation precision, and context-source coverage.
- Custom evaluator registry with `@evaluator(...)`.
- Plugin loading from importable modules or local Python files.
- Report schema metadata and tool-call reporting.

### Compatibility

- v0.1 `expected_contains` / `expected_not_contains` suites remain supported.
- v0.2 `expect:` suites remain supported.
- Existing response-only evaluations do not need tool configuration.

## 0.2.0 - 2026-09-18

- Added the `expect:` evaluation DSL while keeping v0.1 suites compatible.
- Added regex and latency checks.
- Added JSON Schema validation for structured model output.
- Added RAG citation/evidence checks.
- Added optional LLM-as-a-Judge scoring.
- Added concurrent execution and retry/backoff for transient API errors.
- Added HTML and JUnit reports alongside JSON and Markdown.
- Expanded CI to Python 3.10–3.12 and package-build validation.
- Added a GitHub Actions example for secret-backed regression evaluation.
- Expanded examples and automated tests.

## 0.1.0 - 2026-09-18

Initial public-ready release:

- YAML evaluation cases
- OpenAI-compatible chat client
- deterministic contains / not-contains checks
- JSON and Markdown reports
- CI workflow and tests
