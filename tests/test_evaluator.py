from agent_eval_kit.evaluator import evaluate_case
from agent_eval_kit.models import (
    CitationSpec,
    Expectation,
    JudgeSpec,
    ToolCall,
    ToolCallSpec,
)
from agent_eval_kit.models import TestCase as EvalCase


def test_contains_and_not_contains_pass():
    case = EvalCase(
        id="x",
        prompt="q",
        expect=Expectation(contains=["retrieval"], not_contains=["fabricated"]),
    )
    result = evaluate_case(case, "Retrieval improves grounding.", 12.0)
    assert result.passed is True


def test_json_schema_and_citation_source_validation():
    structured = EvalCase(
        id="json",
        prompt="q",
        expect=Expectation(
            json_schema={
                "type": "object",
                "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}},
            },
        ),
    )
    result = evaluate_case(structured, '{"ok": true}', 3.0)
    assert result.passed is True

    cited = EvalCase(
        id="cite",
        prompt="q",
        context="[doc-1] Grounded source.",
        expect=Expectation(
            citations=CitationSpec(
                min_count=1,
                validate_sources=True,
                min_precision=1.0,
            )
        ),
    )
    result = evaluate_case(cited, "Grounded answer [doc-1]", 3.0)
    assert result.passed is True
    assert result.checks["citations:precision"].score == 1.0

    bad = evaluate_case(cited, "Unsupported answer [ghost]", 3.0)
    assert bad.passed is False
    assert bad.checks["citations:precision"].passed is False


def test_tool_call_sequence_and_arguments():
    case = EvalCase(
        id="agent",
        prompt="find it",
        expect=Expectation(
            tool_calls=ToolCallSpec(
                required=["search", "summarize"],
                forbidden=["delete"],
                ordered=["search", "summarize"],
                max_count=2,
                args_schema={
                    "search": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {"query": {"type": "string"}},
                    }
                },
            )
        ),
    )
    calls = [
        ToolCall("search", {"query": "eval"}),
        ToolCall("summarize", {"style": "short"}),
    ]
    result = evaluate_case(case, "", 10.0, tool_calls=calls)
    assert result.passed is True

    reversed_result = evaluate_case(case, "", 10.0, tool_calls=list(reversed(calls)))
    assert reversed_result.checks["tool:ordered"].passed is False


def test_source_coverage():
    case = EvalCase(
        id="coverage",
        prompt="q",
        context="[a] alpha\n[b] beta",
        expect=Expectation(
            citations=CitationSpec(
                min_count=1,
                validate_sources=True,
                min_source_coverage=1.0,
            )
        ),
    )
    result = evaluate_case(case, "Only alpha [a]", 1.0)
    assert result.passed is False
    assert result.checks["citations:source_coverage"].score == 0.5


def test_judge_score_controls_pass():
    case = EvalCase(
        id="judge",
        prompt="q",
        expect=Expectation(judge=JudgeSpec(criteria="be correct", min_score=0.8)),
    )
    result = evaluate_case(case, "answer", 1.0, judge_fn=lambda *_: (0.9, "good"))
    assert result.passed is True
    assert result.checks["judge"].score == 0.9
