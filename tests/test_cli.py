import json
from pathlib import Path

from typer.testing import CliRunner

from agent_eval_kit.cli import app


def test_validate_command(tmp_path: Path):
    suite = tmp_path / "suite.yaml"
    suite.write_text("cases:\n  - id: hello\n    prompt: hi\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["validate", str(suite)])
    assert result.exit_code == 0
    assert "1 cases loaded" in result.stdout


def test_compare_command_passes_for_equal_reports(tmp_path: Path):
    report = {
        "schema_version": "1.1",
        "toolkit_version": "0.4.0",
        "summary": {"pass_rate": 100.0, "avg_latency_ms": 10.0},
        "results": [
            {
                "id": "a",
                "passed": True,
                "response": "ok",
                "latency_ms": 10.0,
                "checks": {},
                "tool_calls": [],
            }
        ],
    }
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    payload = json.dumps(report)
    baseline.write_text(payload, encoding="utf-8")
    current.write_text(payload, encoding="utf-8")

    result = CliRunner().invoke(app, ["compare", str(baseline), str(current)])
    assert result.exit_code == 0
    assert "Baseline regression gate" in result.stdout
