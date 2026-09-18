from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeSpec:
    criteria: str
    min_score: float = 0.7


@dataclass
class CitationSpec:
    required: list[str] = field(default_factory=list)
    min_count: int = 0
    pattern: str = r"\[[^\]]+\]"
    validate_sources: bool = False
    min_precision: float | None = None
    min_source_coverage: float | None = None


@dataclass
class ToolCall:
    name: str
    arguments: Any = field(default_factory=dict)
    id: str | None = None


@dataclass
class ToolCallSpec:
    required: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    ordered: list[str] = field(default_factory=list)
    max_count: int | None = None
    args_schema: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class CustomEvaluatorSpec:
    name: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Expectation:
    contains: list[str] = field(default_factory=list)
    not_contains: list[str] = field(default_factory=list)
    regex: list[str] = field(default_factory=list)
    json_schema: dict[str, Any] | None = None
    citations: CitationSpec | None = None
    tool_calls: ToolCallSpec | None = None
    custom: list[CustomEvaluatorSpec] = field(default_factory=list)
    max_latency_ms: float | None = None
    judge: JudgeSpec | None = None


@dataclass
class TestCase:
    id: str
    prompt: str
    system: str | None = None
    context: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: Any = None
    expect: Expectation = field(default_factory=Expectation)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expected_contains(self) -> list[str]:
        return self.expect.contains

    @property
    def expected_not_contains(self) -> list[str]:
        return self.expect.not_contains


@dataclass
class CheckResult:
    passed: bool
    detail: str = ""
    score: float | None = None


@dataclass
class EvalResult:
    id: str
    passed: bool
    response: str
    latency_ms: float
    checks: dict[str, CheckResult]
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
