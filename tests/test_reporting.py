import json
from pathlib import Path

from agent_eval_kit.models import CheckResult, EvalResult, ToolCall
from agent_eval_kit.reporting import write_html, write_json, write_junit, write_markdown


def test_all_report_formats_include_stability_and_tool_calls(tmp_path: Path):
    results = [
        EvalResult(
            id="a",
            passed=True,
            response="ok",
            latency_ms=10.0,
            checks={"contains:ok": CheckResult(True, "found")},
            tool_calls=[ToolCall("search", {"query": "x"})],
            sample_count=3,
            pass_count=3,
            latency_stddev_ms=1.5,
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

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["toolkit_version"] == "0.5.0"
    assert payload["schema_version"] == "1.2"
    assert payload["summary"]["tool_call_count"] == 1
    assert payload["summary"]["sample_count"] == 3
    assert payload["summary"]["sample_pass_rate"] == 100.0
    assert payload["results"][0]["latency_stddev_ms"] == 1.5
