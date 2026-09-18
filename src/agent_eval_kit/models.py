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


@dataclass
class Expectation:
    contains: list[str] = field(default_factory=list)
    not_contains: list[str] = field(default_factory=list)
    regex: list[str] = field(default_factory=list)
    json_schema: dict[str, Any] | None = None
    citations: CitationSpec | None = None
    max_latency_ms: float | None = None
    judge: JudgeSpec | None = None


@dataclass
class TestCase:
    id: str
    prompt: str
    system: str | None = None
    context: str | None = None
    expect: Expectation = field(default_factory=Expectation)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Backward-compatible aliases used by the v0.1 public API.
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
