# Agent Eval Kit

[![CI](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhiweiZhang97/agent-eval-kit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

A lightweight, provider-agnostic regression evaluation toolkit for **LLM agents and RAG applications**.

Agent Eval Kit turns important prompts and expected behaviors into version-controlled tests that run locally or in CI against any OpenAI-compatible `/chat/completions` endpoint.

## Why this project?

LLM applications can regress even when application code barely changes. Prompts evolve, retrieval changes, providers update models, orchestration logic shifts, and structured output contracts break. Agent Eval Kit provides a small, inspectable baseline for catching those changes without requiring a hosted evaluation platform or a provider-specific SDK.

## v0.2 highlights

- YAML evaluation suites with a readable `expect:` DSL
- Backward compatibility with the v0.1 `expected_contains` format
- Deterministic checks: contains, not-contains, regex, latency thresholds
- JSON Schema validation for structured outputs
- Basic RAG citation/evidence checks
- Optional **LLM-as-a-Judge** scoring with a separate judge model
- Concurrent execution with retry/backoff for transient API failures
- JSON, Markdown, HTML, and JUnit reports
- GitHub Actions examples for CI and regression evaluation
- OpenAI-compatible APIs; no provider SDK lock-in

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

A non-zero exit code is returned when any case fails, making the command suitable for CI gates.

## Evaluation suite format

```yaml
cases:
  - id: grounded-answer
    system: "Answer only from context and cite the source id."
    context: |
      [doc-1] RAG combines retrieval with generation.
    prompt: "What is RAG?"
    expect:
      contains: ["retrieval", "generation"]
      not_contains: ["I browsed the web"]
      regex: ["(?i)rag|retrieval-augmented"]
      citations:
        required: ["[doc-1]"]
        min_count: 1
      max_latency_ms: 30000
```

### Structured-output validation

```yaml
expect:
  json_schema:
    type: object
    required: [status, confidence]
    properties:
      status: {const: ok}
      confidence: {type: number, minimum: 0, maximum: 1}
```

Markdown fenced JSON is accepted as well as raw JSON.

### LLM-as-a-Judge

Use judge checks only when deterministic checks are insufficient:

```yaml
expect:
  judge:
    criteria: "The answer should be concise, correct, and grounded in the supplied context."
    min_score: 0.8
```

Then configure a judge model:

```bash
export AGENT_EVAL_JUDGE_MODEL=your-judge-model
# Optional: use a different compatible endpoint for judging
export AGENT_EVAL_JUDGE_BASE_URL=https://judge.example.com/v1
export AGENT_EVAL_JUDGE_API_KEY=your-judge-key

agent-eval run examples/basic.yaml
```

The judge is prompted to return a score from `0` to `1` plus a short reason. Deterministic checks should still be preferred when possible.

## CI usage

The repository includes two workflows:

- `.github/workflows/ci.yml` — lint, tests, and package build on Python 3.10–3.12.
- `.github/workflows/agent-eval-example.yml` — a manual regression workflow that reads endpoint/model settings from GitHub Actions secrets and uploads evaluation reports as an artifact.

This keeps real API credentials out of the repository while providing a copyable starting point for PR or release gates.

## CLI options

```text
agent-eval validate SUITE.yaml

agent-eval run SUITE.yaml \
  --base-url ... \
  --model ... \
  --workers 4 \
  --retries 2 \
  --timeout 60 \
  --judge-model ... \
  --out-dir agent-eval-results
```

## Design principles

1. **Version-control the contract.** Important prompts and expected behaviors should live beside application code.
2. **Prefer deterministic checks.** Use schema, string, regex, citation, and latency checks before an LLM judge.
3. **Provider agnostic by default.** The core depends on an OpenAI-compatible HTTP contract rather than vendor SDKs.
4. **CI first.** Reports and exit codes are designed for automated regression gates.
5. **Keep private data private.** Public examples must use synthetic or properly licensed data.

## Roadmap

Good contribution areas include:

- semantic similarity evaluators
- richer RAG faithfulness and citation attribution checks
- tool-call / agent-trajectory evaluation
- dataset adapters
- baseline comparison and regression thresholds
- pluggable custom evaluators
- richer HTML dashboards

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Security and privacy

Do not commit API keys, private service URLs, customer prompts, confidential documents, or evaluation outputs containing sensitive data. Use GitHub Actions secrets and synthetic/public examples.

## License

Apache-2.0.
