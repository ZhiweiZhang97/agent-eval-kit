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


def test_compare_command_writes_markdown(tmp_path: Path):
    report = {
        "schema_version": "1.2",
        "toolkit_version": "0.5.0",
        "summary": {"pass_rate": 100.0, "avg_latency_ms": 10.0},
        "results": [
            {
                "id": "a",
                "passed": True,
                "response": "ok",
                "latency_ms": 10.0,
                "checks": {},
                "tool_calls": [],
                "sample_count": 1,
                "pass_count": 1,
            }
        ],
    }
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    markdown = tmp_path / "comparison.md"
    payload = json.dumps(report)
    baseline.write_text(payload, encoding="utf-8")
    current.write_text(payload, encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "compare",
            str(baseline),
            str(current),
            "--markdown-out",
            str(markdown),
        ],
    )
    assert result.exit_code == 0
    assert "Baseline regression gate" in result.stdout
    assert markdown.exists()
    assert "Case diff" in markdown.read_text(encoding="utf-8")
