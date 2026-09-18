from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from .models import EvalResult


def summary(results: list[EvalResult]) -> dict[str, float | int]:
    total = len(results)
    passed = sum(r.passed for r in results)
    avg_latency = sum(r.latency_ms for r in results) / total if total else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round((passed / total * 100) if total else 0.0, 2),
        "avg_latency_ms": round(avg_latency, 2),
    }


def write_json(path: str | Path, results: list[EvalResult]) -> None:
    payload = {"summary": summary(results), "results": [asdict(r) for r in results]}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    lines = [
        "# Agent Eval Report",
        "",
        f"- Total: **{s['total']}**",
        f"- Passed: **{s['passed']}**",
        f"- Failed: **{s['failed']}**",
        f"- Pass rate: **{s['pass_rate']}%**",
        f"- Average latency: **{s['avg_latency_ms']} ms**",
        "",
        "| Case | Status | Latency (ms) | Failed checks |",
        "|---|---:|---:|---|",
    ]
    for r in results:
        failed = ", ".join(name for name, check in r.checks.items() if not check.passed) or "-"
        lines.append(f"| {r.id} | {'PASS' if r.passed else 'FAIL'} | {r.latency_ms:.1f} | {failed} |")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(path: str | Path, results: list[EvalResult]) -> None:
    s = summary(results)
    rows: list[str] = []
    for r in results:
        checks = "<br>".join(
            f"{'✅' if c.passed else '❌'} <code>{html.escape(name)}</code> — {html.escape(c.detail)}"
            for name, c in r.checks.items()
        ) or "No checks"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(r.id)}</code></td>"
            f"<td>{'PASS' if r.passed else 'FAIL'}</td>"
            f"<td>{r.latency_ms:.1f}</td>"
            f"<td>{checks}</td>"
            f"<td><details><summary>response</summary><pre>{html.escape(r.response)}</pre></details></td>"
            "</tr>"
        )
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Eval Report</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px;color:#1f2937}}
table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #d1d5db;padding:10px;text-align:left;vertical-align:top}}th{{background:#f3f4f6}}
code,pre{{font-family:ui-monospace,SFMono-Regular,monospace}}pre{{white-space:pre-wrap;max-width:520px}}.summary{{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}}
.card{{border:1px solid #d1d5db;border-radius:8px;padding:12px 16px}}
</style></head><body>
<h1>Agent Eval Report</h1>
<div class="summary"><div class="card">Pass rate <b>{s['pass_rate']}%</b></div><div class="card">Passed <b>{s['passed']}/{s['total']}</b></div><div class="card">Avg latency <b>{s['avg_latency_ms']} ms</b></div></div>
<table><thead><tr><th>Case</th><th>Status</th><th>Latency</th><th>Checks</th><th>Output</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
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
    for r in results:
        case = ET.SubElement(suite, "testcase", name=r.id, time=f"{r.latency_ms / 1000:.6f}")
        if not r.passed:
            failed = [f"{name}: {check.detail}" for name, check in r.checks.items() if not check.passed]
            failure = ET.SubElement(case, "failure", message="; ".join(failed) or r.error or "Evaluation failed")
            failure.text = r.response
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
