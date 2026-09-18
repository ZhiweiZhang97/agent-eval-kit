from pathlib import Path

from typer.testing import CliRunner

from agent_eval_kit.cli import app


def test_validate_command(tmp_path: Path):
    suite = tmp_path / "suite.yaml"
    suite.write_text("cases:\n  - id: hello\n    prompt: hi\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["validate", str(suite)])
    assert result.exit_code == 0
    assert "1 cases loaded" in result.stdout
