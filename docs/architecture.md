# Architecture

Agent Eval Kit v0.4 evaluates three surfaces together: model output, retrieval grounding, and agent tool behavior.

```text
YAML suite
   │
   ├── prompt / context
   ├── tools / tool_choice
   └── expectations
          │
          ▼
       loader
          │
          ▼
        runner ─────────► OpenAI-compatible endpoint
          │                         │
          │                         ▼
          │               content + tool_calls
          │                         │
          └─────────────────────────┘
                    │
                    ▼
                evaluators
       ┌────────────┼─────────────┐
       │            │             │
 response/RAG    tool calls     plugins
 assertions      trajectory     custom checks
       └────────────┼─────────────┘
                    ▼
                EvalResult
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      reports            baseline gate
 JSON/MD/HTML/JUnit      previous report
```

## Core modules

### `models.py`

Defines the public data model for cases, expectations, tool calls, checks, and results.

### `loaders.py`

Parses YAML, keeps the v0.1 and v0.2 formats compatible, and translates agent/RAG configuration into typed structures.

### `client.py`

Implements a small OpenAI-compatible `/chat/completions` client. It forwards tool definitions and `tool_choice`, retries transient failures, and normalizes modern `tool_calls` plus legacy `function_call` responses.

### `evaluator.py`

Runs deterministic checks for text, regex, JSON Schema, latency, citations, citation-source validity, source coverage, tool selection, tool order, and tool arguments. It also delegates optional LLM judging and custom evaluators.

### `plugins.py`

Provides an explicit local plugin mechanism. Plugins register evaluators with `@evaluator(name)` and are loaded only when the user passes `--plugin`.

### `baseline.py`

Compares a current run with a previous versioned JSON report. The gate can fail CI for case regressions, pass-rate drops, latency growth, or judge-score drops.

### `reporting.py`

Produces versioned JSON reports plus Markdown, HTML, and JUnit output. Normalized tool calls are included in JSON and human-readable reports.

## Design choices

### Evaluate behavior, not implementation

Agent Eval Kit does not require a particular agent framework. The contract is the OpenAI-compatible request/response shape plus explicit expectations.

### Deterministic checks first

String, schema, citation, tool trajectory, and threshold checks are cheap and repeatable. LLM judging is reserved for criteria that cannot be represented deterministically.

### Baselines are ordinary files

A baseline is a reviewed `report.json`. It can live in Git, be downloaded from CI, or be produced by another workflow. No hosted state is required.

### Plugins are explicit

Plugins execute Python code and therefore are never auto-discovered from arbitrary files. Users opt in with `--plugin`, which keeps the default execution path inspectable.

### Safe failure behavior

One failed API request or evaluator becomes a failed case rather than aborting the entire suite.
