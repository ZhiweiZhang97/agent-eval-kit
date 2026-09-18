# Agent Eval Kit

[![CI](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

A lightweight, provider-agnostic regression evaluation toolkit for **LLM agents, tool calls, and RAG applications**.

Agent Eval Kit turns prompts, tool contracts, retrieval evidence, and expected behaviors into version-controlled tests that can run locally or in CI against OpenAI-compatible endpoints.

## What's new in v0.4

v0.4 expands the project from response-only evaluation into a practical agent/RAG regression framework:

- **Baseline regression gates** for case regressions, pass-rate drops, latency growth, and judge-score drops.
- **Agent tool-call evaluation** for required/forbidden tools, ordered trajectories, maximum calls, and argument JSON Schema.
- **Tool definitions in YAML**, passed through to OpenAI-compatible APIs with optional `tool_choice`.
- **Stronger RAG citation checks** for source validity, citation precision, and context-source coverage.
- **Pluggable custom evaluators** loaded from Python modules or local `.py` files.
- Versioned JSON reports that preserve normalized tool calls for CI and downstream analysis.

The v0.2 capabilities remain available: contains/not-contains, regex, JSON Schema, latency thresholds, LLM-as-a-Judge, concurrency, retries, HTML/Markdown/JUnit reports, and the legacy YAML syntax.

## Install

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick start

Validate a suite without making model calls:

```bash
agent-eval validate examples/basic.yaml
```

Run against any OpenAI-compatible endpoint:

```bash
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
```

A non-zero exit code is returned when a case fails or when an enabled baseline gate detects a regression.

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

A test can define tools exactly as an OpenAI-compatible API expects them:

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

For multi-step agents, require an ordered subsequence:

```yaml
expect:
  tool_calls:
    ordered: [search, summarize]
```

The order check allows unrelated calls between expected steps while preserving the required trajectory order.

## RAG citation validation

v0.4 can verify that generated citations actually refer to source identifiers present in the supplied context:

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

- `validate_sources: true` defaults the required precision to 1.0.
- `min_precision` is the fraction of cited identifiers that exist in context.
- `min_source_coverage` is the fraction of context source identifiers cited in the answer.
- `required` can still require specific citations explicitly.

For semantic faithfulness, combine these deterministic checks with an LLM judge.

## LLM-as-a-Judge

```yaml
expect:
  judge:
    criteria: "The answer must be correct, concise, and supported by the supplied context."
    min_score: 0.8
```

Configure a judge model:

```bash
export AGENT_EVAL_JUDGE_MODEL=your-judge-model
export AGENT_EVAL_JUDGE_BASE_URL=https://judge.example.com/v1
export AGENT_EVAL_JUDGE_API_KEY=your-judge-key
```

Deterministic checks should be preferred when a deterministic contract is possible.

## Baseline regression gates

Save a known-good `report.json`, then compare a later run against it:

```bash
agent-eval run examples/basic.yaml \
  --baseline baselines/main.json \
  --max-case-regressions 0 \
  --max-pass-rate-drop 0 \
  --max-latency-increase-pct 20 \
  --max-judge-score-drop 0.05
```

Or compare two existing reports without making model calls:

```bash
agent-eval compare baselines/main.json agent-eval-results/report.json \
  --max-case-regressions 0 \
  --max-pass-rate-drop 0 \
  --max-latency-increase-pct 20
```

The baseline gate detects:

- cases that previously passed but now fail,
- pass-rate drops in percentage points,
- average latency increases,
- average LLM-judge score drops.

## Custom evaluator plugins

Create a Python evaluator:

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

Reference it in YAML:

```yaml
expect:
  custom:
    short-answer:
      max_chars: 500
```

Load the plugin when running:

```bash
agent-eval run suite.yaml --plugin examples/custom_evaluator.py
```

Plugins execute local Python code. Only load plugins you trust.

## CI usage

The repository includes:

- `.github/workflows/ci.yml` — lint, tests, and package builds on Python 3.10–3.12.
- `.github/workflows/agent-eval-example.yml` — a manual API-backed evaluation workflow that stores reports as artifacts.

For a production repository, keep a reviewed baseline JSON file on the default branch and compare pull-request results against it.

## Design principles

1. **Version-control the contract.** Prompts, tools, and expected behavior should be reviewable diffs.
2. **Evaluate the agent, not only the prose.** Tool choice, arguments, order, and final answers all matter.
3. **Prefer deterministic checks.** Use schema, source, trajectory, and threshold checks before LLM judging.
4. **Provider agnostic by default.** Core execution targets OpenAI-compatible HTTP APIs.
5. **Make regressions actionable.** CI should show which behavior changed and why.
6. **Keep private data private.** Public suites and bug reports should use synthetic or licensed data.

## Project status

Agent Eval Kit is an early-stage open-source project. The public API is intentionally small, but minor versions may still refine configuration names and report fields before 1.0.

See [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [AGENTS.md](AGENTS.md).

## Security and privacy

Do not commit API keys, private endpoints, customer prompts, confidential documents, or evaluation reports containing sensitive information. Use environment variables and CI secret stores.

## License

Apache-2.0.
