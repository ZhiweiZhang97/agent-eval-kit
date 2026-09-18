from pathlib import Path

import pytest

from agent_eval_kit.loaders import load_cases


def test_load_cases_backward_compatible(tmp_path: Path):
    file = tmp_path / "cases.yaml"
    file.write_text(
        "cases:\n  - id: a\n    prompt: hello\n    expected_contains: [world]\n",
        encoding="utf-8",
    )
    cases = load_cases(file)
    assert len(cases) == 1
    assert cases[0].expect.contains == ["world"]


def test_load_v04_agent_and_rag_fields(tmp_path: Path):
    file = tmp_path / "cases.yaml"
    file.write_text(
        """cases:
  - id: agent
    prompt: search
    tools:
      - type: function
        function:
          name: search
          parameters:
            type: object
    tool_choice: auto
    expect:
      citations:
        validate_sources: true
        min_precision: 1.0
      tool_calls:
        required: [search]
        max_count: 2
      custom:
        short-answer:
          max_chars: 100
""",
        encoding="utf-8",
    )
    case = load_cases(file)[0]
    assert case.tools[0]["function"]["name"] == "search"
    assert case.tool_choice == "auto"
    assert case.expect.citations is not None
    assert case.expect.citations.validate_sources is True
    assert case.expect.tool_calls is not None
    assert case.expect.tool_calls.required == ["search"]
    assert case.expect.custom[0].name == "short-answer"


def test_duplicate_ids_rejected(tmp_path: Path):
    file = tmp_path / "cases.yaml"
    file.write_text("cases:\n- {id: a, prompt: one}\n- {id: a, prompt: two}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate case id"):
        load_cases(file)
