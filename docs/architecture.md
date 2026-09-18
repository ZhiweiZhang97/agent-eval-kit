# Architecture

Agent Eval Kit v0.5 evaluates model output, retrieval grounding, agent tool behavior, and stochastic stability.

```text
YAML suite ──────────────┐
                         │
tools / tool_choice ─────┤
                         ▼
                    loader / CLI
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        single target          target matrix
              │                     │
              └──────────┬──────────┘
                         ▼
                     runner
                 repeats × cases
                         │
                         ▼
              OpenAI-compatible API
             pacing + retry handling
                         │
                 content + tool_calls
                         │
                         ▼
                    evaluators
       response / RAG / tools / plugins / judge
                         │
                         ▼
               per-case aggregation
         pass rate + mean latency + variance
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
            reports            Baseline diff
     JSON / MD / HTML / JUnit   CI gate / PR MD
```

## Repeated-run model

Repeated samples are aggregated back into one stable case identity. This keeps Baseline comparisons meaningful while exposing sample pass rate and variability. The final representative response and tool sequence are the last sample, while pass count, latency statistics, and judge variance summarize all samples.

## Baseline comparison

Baseline reports remain ordinary JSON files. v0.5 adds per-case diffs for status, latency, judge score, and tool sequence in addition to aggregate gates.

## Model matrix

A matrix YAML file defines named targets, each with a base URL, model, credential environment variable, and optional request pacing. The same deterministic suite is executed against each target and summarized into `matrix.json` and `matrix.md`.

## Rate limiting

Retries continue to use exponential fallback, but explicit server `Retry-After` instructions take precedence. Optional minimum request intervals are coordinated across worker threads sharing one client.

## Report safety

Before persistence, common credential-like strings are redacted recursively from JSON reports and from human-readable report fields. This is defense-in-depth and does not make sensitive datasets appropriate for public repositories.

## Plugins

Plugins execute arbitrary local Python code and are never auto-discovered. They are loaded only through explicit user configuration.
