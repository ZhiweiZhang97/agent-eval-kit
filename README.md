# Agent Eval Kit

[![CI](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10--3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

A lightweight, provider-agnostic regression evaluation toolkit for **LLM agents, tool calls, and RAG applications**.

Agent Eval Kit turns prompts, tool contracts, retrieval evidence, and expected behaviors into version-controlled tests that run locally or in CI against OpenAI-compatible endpoints.

## What's new in v0.5

v0.5 focuses on reliability, comparison, and maintainability:

- **Repeated evaluation** with per-case sample pass rate, average latency, latency standard deviation, and judge-score variance.
- **Stability gates** with `--repeats` and `--min-repeat-pass-rate`.
- **Model / endpoint matrix** runs from a simple targets YAML file.
- **PR-friendly baseline diffs** showing pass/fail changes, per-case latency deltas, judge-score deltas, and tool-sequence changes.
- **Rate-limit-aware retries** that respect `Retry-After` and optional request pacing.
- **Default report redaction** for common credential and token shapes.
- CI now covers Python 3.10–3.13.
- Dependabot configuration and a tag-triggered GitHub Release workflow.

v0.4 capabilities remain: tool-call evaluation, RAG citation validation, baseline gates, custom evaluators, JSON Schema, LLM-as-a-Judge, concurrent execution, and JSON/Markdown/HTML/JUnit reports.

## Install

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick start

```bash
agent-eval validate examples/basic.yaml

export OPENAI_BASE_URL=https://api.example.com/v1
export OPENAI_MODEL=your-model
export OPENAI_API_KEY=your-key

agent-eval run examples/basic.yaml
```

Reports are written to `agent-eval-results/`:

```text
report.json
report.md
report.html
junit.xml
baseline-comparison.md   # when --baseline is used
```

## Repeated runs and stability

Single-shot evaluation can hide stochastic regressions. Run each case multiple times:

```bash
agent-eval run examples/basic.yaml \
  --repeats 5 \
  --min-repeat-pass-rate 0.8
```

A case passes the repeat gate only when its sample pass rate reaches the configured threshold. Reports include sample count, pass count, sample pass rate, mean latency, latency standard deviation, and judge-score standard deviation when a judge is used.

This keeps one stable case identity for Baseline comparison instead of generating synthetic case IDs for each sample.

## Model / endpoint matrix

Create a target file:

```yaml
targets:
  - name: primary
    base_url: https://api.example.com/v1
    model: model-a
    api_key_env: PRIMARY_API_KEY

  - name: candidate
    base_url: https://candidate.example.com/v1
    model: model-b
    api_key_env: CANDIDATE_API_KEY
    min_interval_ms: 250
```

Then run the same deterministic suite against every target:

```bash
agent-eval matrix examples/basic.yaml examples/matrix.yaml \
  --repeats 3 \
  --out-dir agent-eval-matrix
```

The matrix writes `matrix.json` and `matrix.md` with case pass rate, sample pass rate, and average latency for each target.

Matrix mode currently requires deterministic checks. Suites using LLM-as-a-Judge should use `agent-eval run`, where judge endpoint/model settings are explicit.

## Response evaluation

```yaml
cases:
  - id: structured-answer
    system: "Return JSON only."
    prompt: "Return status=ok and confidence=0.9."
    expect:
      json_schema:
        type: object
        required: [status, confidence]
        properties:
          status: {const: ok}
          confidence: {type: number, minimum: 0, maximum: 1}
```

Other deterministic response checks include `contains`, `not_contains`, `regex`, and `max_latency_ms`.

## Agent tool-call evaluation

```yaml
cases:
  - id: weather-agent
    prompt: "What is the weather in Hangzhou?"
    tools:
      - type: function
        function:
          name: get_weather
          description: Get current weather for a city.
          parameters:
            type: object
            required: [city]
            properties:
              city: {type: string}
    tool_choice: auto
    expect:
      tool_calls:
        required: [get_weather]
        forbidden: [delete_user_data]
        max_count: 2
        args_schema:
          get_weather:
            type: object
            required: [city]
            properties:
              city: {type: string}
```

For multi-step agents:

```yaml
expect:
  tool_calls:
    ordered: [search, summarize]
```

## RAG citation validation

```yaml
cases:
  - id: grounded-rag
    context: |
      [doc-1] RAG combines retrieval with generation.
      [doc-2] Regression tests detect unwanted behavior changes.
    prompt: "Explain both ideas."
    expect:
      citations:
        min_count: 2
        validate_sources: true
        min_precision: 1.0
        min_source_coverage: 1.0
```

For semantic faithfulness, combine deterministic citation checks with an LLM judge.

## Baseline regression gates and diffs

```bash
agent-eval run examples/basic.yaml \
  --baseline baselines/main.json \
  --max-case-regressions 0 \
  --max-pass-rate-drop 0 \
  --max-latency-increase-pct 20 \
  --max-judge-score-drop 0.05
```

Or compare reports without model calls:

```bash
agent-eval compare baselines/main.json agent-eval-results/report.json \
  --max-case-regressions 0 \
  --markdown-out agent-eval-results/pr-diff.md
```

The Markdown diff includes per-case status changes, latency deltas, judge deltas, and tool-sequence changes, so it can be posted directly into a pull request.

## Rate-limit-aware execution

Transient retryable failures use retry/backoff. When a server returns `Retry-After`, Agent Eval Kit respects it.

For providers with a known request-rate limit, pace starts explicitly:

```bash
agent-eval run suite.yaml --workers 8 --min-request-interval-ms 250
```

This pacing is shared across worker threads for one client.

## Custom evaluator plugins

```python
from agent_eval_kit.models import CheckResult
from agent_eval_kit.plugins import evaluator

@evaluator("short-answer")
def short_answer(case, response, tool_calls, config):
    maximum = int(config.get("max_chars", 500))
    return CheckResult(
        len(response) <= maximum,
        f"Response length is {len(response)}; maximum is {maximum}.",
    )
```

```bash
agent-eval run suite.yaml --plugin examples/custom_evaluator.py
```

Plugins execute local Python code. Only load plugins you trust.

## Report safety

Generated JSON, Markdown, HTML, and JUnit reports redact common credential-like strings by default, including provider-prefixed tokens, Bearer-style tokens, and common key/token assignment forms.

Redaction is defense-in-depth, not a substitute for keeping private prompts and production secrets out of public evaluation suites.

## CI and releases

The repository includes:

- `.github/workflows/ci.yml` — lint, tests, and package builds on Python 3.10–3.13.
- `.github/workflows/agent-eval-example.yml` — manual secret-backed evaluation.
- `.github/workflows/release.yml` — builds and publishes GitHub Release assets for `v*` tags.
- `.github/dependabot.yml` — monthly Python and GitHub Actions dependency updates.

## Design principles

1. **Version-control the contract.**
2. **Evaluate agent behavior, not only prose.**
3. **Measure stability, not only one lucky sample.**
4. **Prefer deterministic checks before model judges.**
5. **Make regressions reviewable in CI.**
6. **Stay provider-agnostic and locally inspectable.**
7. **Keep private data private.**

See [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and [docs/architecture.md](docs/architecture.md).

## License

Apache-2.0.
