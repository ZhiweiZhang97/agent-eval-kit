# Changelog

## 0.5.0 - 2026-09-20

### Added

- Repeated per-case evaluation with configurable repeat count and minimum sample pass-rate gates.
- Latency standard deviation and judge-score standard deviation for repeated runs.
- Model / endpoint matrix command driven by YAML targets.
- PR-friendly Baseline Markdown diff with per-case status, latency, judge, and tool-sequence changes.
- Rate-limit-aware retry handling that honors `Retry-After`.
- Cross-thread minimum request interval for provider pacing.
- Automatic report redaction for common credential-like strings.
- Python 3.13 CI coverage.
- Dependabot configuration.
- Tag-triggered GitHub Release packaging workflow.

### Changed

- JSON report schema version is now `1.2`.
- Reports expose sample count, sample pass rate, and latency variability.
- The CLI table shows repeated-run stability when repeats are enabled.

### Compatibility

- Existing suites still default to one sample per case.
- v0.1 and v0.2 YAML compatibility remains.
- v0.4 tool-call, RAG, Baseline, and plugin syntax remains supported.

## 0.4.0 - 2026-09-18

- Added Baseline regression gates.
- Added agent tool definitions and tool-call assertions.
- Added RAG citation-source validation and source coverage.
- Added custom evaluator plugins.
- Added normalized tool calls to versioned reports.

## 0.2.0 - 2026-09-18

- Added the `expect:` evaluation DSL while keeping v0.1 suites compatible.
- Added regex, latency, JSON Schema, RAG citations, LLM-as-a-Judge, concurrency,
  retries, and HTML/JUnit reporting.

## 0.1.0 - 2026-09-18

Initial public-ready release.
