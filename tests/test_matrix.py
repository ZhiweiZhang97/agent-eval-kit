from pathlib import Path

import pytest

from agent_eval_kit.matrix import load_targets, matrix_payload
from agent_eval_kit.models import EvalResult


def test_load_matrix_targets(tmp_path: Path):
    config = tmp_path / "matrix.yaml"
    config.write_text(
        """targets:
  - name: a
    base_url: https://a.example/v1
    model: model-a
  - name: b
    base_url: https://b.example/v1
    model: model-b
    api_key_env: B_KEY
    min_interval_ms: 250
""",
        encoding="utf-8",
    )
    targets = load_targets(config)
    assert [target.name for target in targets] == ["a", "b"]
    assert targets[1].api_key_env == "B_KEY"
    assert targets[1].min_interval_ms == 250


def test_duplicate_matrix_targets_rejected(tmp_path: Path):
    config = tmp_path / "matrix.yaml"
    config.write_text(
        """targets:
  - {name: a, base_url: https://a.example/v1, model: one}
  - {name: a, base_url: https://b.example/v1, model: two}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_targets(config)


def test_matrix_payload_contains_summary():
    target_file = {
        "name": "a",
        "base_url": "https://a.example/v1",
        "model": "one",
    }
    from agent_eval_kit.matrix import MatrixTarget

    target = MatrixTarget(**target_file)
    result = EvalResult(
        id="case",
        passed=True,
        response="ok",
        latency_ms=10,
        checks={},
    )
    payload = matrix_payload({"a": [result]}, [target])
    assert payload["targets"][0]["summary"]["pass_rate"] == 100.0
