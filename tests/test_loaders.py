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
    assert cases[0].id == "a"
    assert cases[0].expect.contains == ["world"]


def test_load_new_expectation_format(tmp_path: Path):
    file = tmp_path / "cases.yaml"
    file.write_text(
        """cases:
  - id: a
    prompt: hello
    expect:
      regex: ['h.*o']
      max_latency_ms: 1000
      judge:
        criteria: useful
        min_score: 0.8
""",
        encoding="utf-8",
    )
    case = load_cases(file)[0]
    assert case.expect.regex == ["h.*o"]
    assert case.expect.max_latency_ms == 1000
    assert case.expect.judge is not None
    assert case.expect.judge.min_score == 0.8


def test_duplicate_ids_rejected(tmp_path: Path):
    file = tmp_path / "cases.yaml"
    file.write_text("cases:\n- {id: a, prompt: one}\n- {id: a, prompt: two}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate case id"):
        load_cases(file)
