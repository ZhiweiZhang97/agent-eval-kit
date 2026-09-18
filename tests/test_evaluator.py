from agent_eval_kit.evaluator import evaluate_case
from agent_eval_kit.models import CitationSpec, Expectation, JudgeSpec, TestCase as EvalCase


def test_contains_and_not_contains_pass():
    case = EvalCase(
        id="x",
        prompt="q",
        expect=Expectation(contains=["retrieval"], not_contains=["fabricated"]),
    )
    result = evaluate_case(case, "Retrieval improves grounding.", 12.0)
    assert result.passed is True


def test_json_schema_and_citation_pass():
    case = EvalCase(
        id="json",
        prompt="q",
        expect=Expectation(
            json_schema={"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}},
        ),
    )
    result = evaluate_case(case, '{"ok": true}', 3.0)
    assert result.passed is True
    assert result.checks["json_schema"].passed is True

    cited = EvalCase(
        id="cite",
        prompt="q",
        expect=Expectation(citations=CitationSpec(required=["[doc-1]"], min_count=1)),
    )
    result = evaluate_case(cited, "Grounded answer [doc-1]", 3.0)
    assert result.passed is True


def test_judge_score_controls_pass():
    case = EvalCase(
        id="judge",
        prompt="q",
        expect=Expectation(judge=JudgeSpec(criteria="be correct", min_score=0.8)),
    )
    result = evaluate_case(case, "answer", 1.0, judge_fn=lambda *_: (0.9, "good"))
    assert result.passed is True
    assert result.checks["judge"].score == 0.9
