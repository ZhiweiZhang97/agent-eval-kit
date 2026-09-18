# Changelog

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
