from pathlib import Path

from agent_eval_kit.models import CheckResult, EvalResult
from agent_eval_kit.reporting import write_html, write_json, write_junit, write_markdown


def test_all_report_formats(tmp_path: Path):
    results = [
        EvalResult(
            id="a",
            passed=True,
            response="ok",
            latency_ms=10.0,
            checks={"contains:ok": CheckResult(True, "found")},
        )
    ]
    paths = {
        "json": tmp_path / "report.json",
        "md": tmp_path / "report.md",
        "html": tmp_path / "report.html",
        "junit": tmp_path / "junit.xml",
    }
    write_json(paths["json"], results)
    write_markdown(paths["md"], results)
    write_html(paths["html"], results)
    write_junit(paths["junit"], results)
    for path in paths.values():
        assert path.exists()
        assert path.stat().st_size > 0
