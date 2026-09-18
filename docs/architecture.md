# Architecture

Agent Eval Kit follows a deliberately small pipeline:

```text
YAML suite
   │
   ▼
 loader ──► typed cases
   │
   ▼
 runner ──► OpenAI-compatible endpoint
   │               │
   │               ▼
   └────────► model response
                   │
                   ▼
              evaluators
       ┌───────────┼───────────┐
       │           │           │
 deterministic   schema      judge
 checks          checks      (optional)
       └───────────┼───────────┘
                   ▼
               EvalResult
                   │
                   ▼
       JSON / Markdown / HTML / JUnit
```

## Modules

- `models.py` defines public evaluation data structures.
- `loaders.py` parses YAML and preserves compatibility with earlier suite syntax.
- `client.py` implements the minimal OpenAI-compatible HTTP contract and transient-error retry logic.
- `runner.py` manages concurrent execution while preserving input order and continue-on-error behavior.
- `evaluator.py` contains deterministic assertions and the judge integration contract.
- `judge.py` implements optional model-based scoring.
- `reporting.py` renders machine- and human-readable output.
- `cli.py` exposes validation and run commands.

## Design choices

### Provider independence

The core sends plain HTTP requests to an OpenAI-compatible endpoint instead of importing provider SDKs. This keeps the dependency surface small and allows the same suite to run against many gateways and self-hosted model servers.

### Deterministic checks first

LLM judging is useful for fuzzy quality criteria, but it adds cost and variance. Exact strings, regular expressions, JSON Schema, citations, and latency thresholds are evaluated deterministically whenever possible.

### Evaluation files are code

Suites are meant to be reviewed, versioned, and executed in CI. A behavior change should be visible as a diff rather than hidden in a hosted dashboard configuration.

### Safe failure behavior

A failed request becomes a failed case instead of stopping the entire suite. This is important when a large regression run encounters one malformed case or one transient provider error.
