# Security Policy

## Reporting a vulnerability

Please do not disclose security vulnerabilities in a public issue. Use GitHub private vulnerability reporting when available.

Include a concise description, affected version, reproduction steps, and potential impact. Do not include real credentials, private prompts, customer data, or confidential service URLs.

## Threat model notes

Agent Eval Kit processes model prompts, outputs, tool arguments, and evaluation metadata. These may contain confidential information.

- Store provider credentials in environment variables or CI secret stores.
- Treat generated reports and CI artifacts as potentially sensitive.
- v0.5 applies defense-in-depth redaction for common credential-like strings, but redaction is not guaranteed to recognize every secret format.
- Custom evaluator plugins execute arbitrary Python code. Load only trusted plugins.
- Matrix configuration should name credential environment variables rather than embedding credential values.
- Public examples and bug reports should use synthetic or properly licensed data.

## Dependency and CI hygiene

The repository uses automated dependency update proposals and CI across supported Python versions. Review dependency changes before merging them.
