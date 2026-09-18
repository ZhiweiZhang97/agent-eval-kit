from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .models import EvalResult
from .redaction import redact_text, redact_value

REPORT_SCHEMA_VERSION = "1.2"


def summary(results: list[EvalResult]) -> dict[str, float | int]:
    total = len(results)
    passed = sum(result.passed for result in results)
    avg_latency = (
        sum(result.latency_ms for result in results) / total if total else 0.0
    )
    tool_call_count = sum(len(result.tool_calls) for result in results)
    judge_scores = [
        check.score
        for result in results
        for name, check in result.checks.items()
        if name == "judge" and check.score is not None
    ]
    avg_judge = sum(judge_scores) / len(judge_scores) if judge_scores else 0.0
    total_samples = sum(result.sample_count for result in results)
    passed_samples = sum((result.pass_count or 0) for result in results)
    avg_latency_stddev = (
        sum(result.latency_stddev_ms for result in results) / total if total else 0.0
    )
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round((passed / total * 100) if total else 0.0, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "avg_latency_stddev_ms": round(avg_latency_stddev, 2),
        "tool_call_count": tool_call_count,
        "avg_judge_score": round(avg_judge, 4),
        "sample_count": total_samples,
        "sample_pass_rate": round(
            (passed_samples / total_samples * 100) if total_samples else 0.0,
            2,
        ),
    }


def report_payload(results: list[EvalResult]) -> dict[str, object]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "toolkit_version": __version__,
        "summary": summary(results),
        "results": [asdict(result) for result in results],
    }
    return redact_value(payload)


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
        f"- Cases: **{s['passed']}/{s['total']} passed**",
        f"- Case pass rate: **{s['pass_rate']}%**",
        f"- Samples: **{s['sample_count']}**",
        f"- Sample pass rate: **{s['sample_pass_rate']}%**",
        f"- Average latency: **{s['avg_latency_ms']} ms**",
        f"- Mean latency stddev: **{s['avg_latency_stddev_ms']} ms**",
        f"- Tool calls: **{s['tool_call_count']}**",
        "",
        "| Case | Status | Samples | Sample pass | Latency | Stddev | Tools | Failed checks |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for result in results:
        failed = (
            ", ".join(name for name, check in result.checks.items() if not check.passed)
            or "-"
        )
        tools = ", ".join(call.name for call in result.tool_calls) or "-"
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"| {redact_text(result.id)} | {status} | {result.sample_count} | "
            f"{result.sample_pass_rate * 100:.1f}% | {result.latency_ms:.1f} ms | "
            f"{result.latency_stddev_ms:.1f} ms | {redact_text(tools)} | "
            f"{redact_text(failed)} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    rows: list[str] = []
    for result in results:
        checks = "<br>".join(
            (
                f"{'✅' if check.passed else '❌'} "
                f"<code>{html.escape(redact_text(name))}</code> — "
                f"{html.escape(redact_text(check.detail))}"
            )
            for name, check in result.checks.items()
        ) or "No checks"
        tools = "<br>".join(
            (
                f"<code>{html.escape(redact_text(call.name))}</code> "
                f"{html.escape(redact_text(str(call.arguments)))}"
            )
            for call in result.tool_calls
        ) or "-"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(redact_text(result.id))}</code></td>"
            f"<td>{'PASS' if result.passed else 'FAIL'}</td>"
            f"<td>{result.pass_count}/{result.sample_count}</td>"
            f"<td>{result.latency_ms:.1f} ± {result.latency_stddev_ms:.1f}</td>"
            f"<td>{tools}</td>"
            f"<td>{checks}</td>"
            "<td><details><summary>response</summary>"
            f"<pre>{html.escape(redact_text(result.response))}</pre></details></td>"
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
<div class="card">Case pass <b>{s['pass_rate']}%</b></div>
<div class="card">Sample pass <b>{s['sample_pass_rate']}%</b></div>
<div class="card">Samples <b>{s['sample_count']}</b></div>
<div class="card">Avg latency <b>{s['avg_latency_ms']} ms</b></div>
</div>
<table>
<thead>
<tr>
<th>Case</th><th>Status</th><th>Samples</th><th>Latency</th>
<th>Tools</th><th>Checks</th><th>Output</th>
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
            name=redact_text(result.id),
            time=f"{result.latency_ms / 1000:.6f}",
        )
        if not result.passed:
            failed = [
                f"{name}: {check.detail}"
                for name, check in result.checks.items()
                if not check.passed
            ]
            message = redact_text(
                "; ".join(failed) or result.error or "Evaluation failed"
            )
            failure = ET.SubElement(case, "failure", message=message)
            failure.text = redact_text(result.response)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
