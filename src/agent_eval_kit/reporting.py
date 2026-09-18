from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .models import EvalResult

REPORT_SCHEMA_VERSION = "1.1"


def summary(results: list[EvalResult]) -> dict[str, float | int]:
    total = len(results)
    passed = sum(r.passed for r in results)
    avg_latency = sum(r.latency_ms for r in results) / total if total else 0.0
    tool_call_count = sum(len(r.tool_calls) for r in results)
    judge_scores = [
        check.score
        for result in results
        for name, check in result.checks.items()
        if name == "judge" and check.score is not None
    ]
    avg_judge = sum(judge_scores) / len(judge_scores) if judge_scores else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round((passed / total * 100) if total else 0.0, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "tool_call_count": tool_call_count,
        "avg_judge_score": round(avg_judge, 4),
    }


def report_payload(results: list[EvalResult]) -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "toolkit_version": __version__,
        "summary": summary(results),
        "results": [asdict(r) for r in results],
    }


def write_json(path: str | Path, results: list[EvalResult]) -> None:
    Path(path).write_text(
        json.dumps(report_payload(results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_markdown(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    lines = [
        "# Agent Eval Report",
        "",
        f"- Toolkit: **v{__version__}**",
        f"- Total: **{s['total']}**",
        f"- Passed: **{s['passed']}**",
        f"- Failed: **{s['failed']}**",
        f"- Pass rate: **{s['pass_rate']}%**",
        f"- Average latency: **{s['avg_latency_ms']} ms**",
        f"- Tool calls: **{s['tool_call_count']}**",
        "",
        "| Case | Status | Latency (ms) | Tools | Failed checks |",
        "|---|---:|---:|---|---|",
    ]
    for result in results:
        failed = (
            ", ".join(name for name, check in result.checks.items() if not check.passed)
            or "-"
        )
        tools = ", ".join(call.name for call in result.tool_calls) or "-"
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"| {result.id} | {status} | {result.latency_ms:.1f} | {tools} | {failed} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    rows: list[str] = []
    for result in results:
        checks = "<br>".join(
            (
                f"{'✅' if check.passed else '❌'} "
                f"<code>{html.escape(name)}</code> — {html.escape(check.detail)}"
            )
            for name, check in result.checks.items()
        ) or "No checks"
        tools = "<br>".join(
            f"<code>{html.escape(call.name)}</code> {html.escape(str(call.arguments))}"
            for call in result.tool_calls
        ) or "-"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(result.id)}</code></td>"
            f"<td>{'PASS' if result.passed else 'FAIL'}</td>"
            f"<td>{result.latency_ms:.1f}</td>"
            f"<td>{tools}</td>"
            f"<td>{checks}</td>"
            "<td><details><summary>response</summary>"
            f"<pre>{html.escape(result.response)}</pre></details></td>"
            "</tr>"
        )

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Eval Report</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1280px;
margin:40px auto;padding:0 20px;color:#1f2937}}
table{{width:100%;border-collapse:collapse}}
th,td{{border:1px solid #d1d5db;padding:10px;text-align:left;vertical-align:top}}
th{{background:#f3f4f6}}
code,pre{{font-family:ui-monospace,SFMono-Regular,monospace}}
pre{{white-space:pre-wrap;max-width:520px}}
.summary{{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}}
.card{{border:1px solid #d1d5db;border-radius:8px;padding:12px 16px}}
</style></head><body>
<h1>Agent Eval Report</h1>
<p>Agent Eval Kit v{__version__}</p>
<div class="summary">
<div class="card">Pass rate <b>{s['pass_rate']}%</b></div>
<div class="card">Passed <b>{s['passed']}/{s['total']}</b></div>
<div class="card">Avg latency <b>{s['avg_latency_ms']} ms</b></div>
<div class="card">Tool calls <b>{s['tool_call_count']}</b></div>
</div>
<table>
<thead>
<tr>
<th>Case</th><th>Status</th><th>Latency</th><th>Tools</th><th>Checks</th><th>Output</th>
</tr>
</thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""
    Path(path).write_text(doc, encoding="utf-8")


def write_junit(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    suite = ET.Element(
        "testsuite",
        name="agent-eval-kit",
        tests=str(s["total"]),
        failures=str(s["failed"]),
    )
    for result in results:
        case = ET.SubElement(
            suite,
            "testcase",
            name=result.id,
            time=f"{result.latency_ms / 1000:.6f}",
        )
        if not result.passed:
            failed = [
                f"{name}: {check.detail}"
                for name, check in result.checks.items()
                if not check.passed
            ]
            message = "; ".join(failed) or result.error or "Evaluation failed"
            failure = ET.SubElement(case, "failure", message=message)
            failure.text = result.response
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
