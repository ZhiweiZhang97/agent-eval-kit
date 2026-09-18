from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import EvalResult
from .reporting import summary


@dataclass
class MatrixTarget:
    name: str
    base_url: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    min_interval_ms: float = 0.0


def load_targets(path: str | Path) -> list[MatrixTarget]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    items = raw.get("targets") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("Matrix config must contain a non-empty 'targets' list.")

    targets: list[MatrixTarget] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Matrix target #{index} must be an object.")
        for required in ("name", "base_url", "model"):
            if not item.get(required):
                raise ValueError(f"Matrix target #{index} is missing {required!r}.")
        name = str(item["name"])
        if name in seen:
            raise ValueError(f"Duplicate matrix target name: {name}")
        seen.add(name)
        targets.append(
            MatrixTarget(
                name=name,
                base_url=str(item["base_url"]),
                model=str(item["model"]),
                api_key_env=str(item.get("api_key_env", "OPENAI_API_KEY")),
                min_interval_ms=float(item.get("min_interval_ms", 0.0)),
            )
        )
    return targets


def matrix_payload(
    results: dict[str, list[EvalResult]],
    targets: list[MatrixTarget],
) -> dict[str, Any]:
    by_name = {target.name: target for target in targets}
    return {
        "targets": [
            {
                **asdict(by_name[name]),
                "summary": summary(target_results),
            }
            for name, target_results in results.items()
        ]
    }


def write_matrix_json(
    path: str | Path,
    results: dict[str, list[EvalResult]],
    targets: list[MatrixTarget],
) -> None:
    Path(path).write_text(
        json.dumps(matrix_payload(results, targets), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_matrix_markdown(
    path: str | Path,
    results: dict[str, list[EvalResult]],
    targets: list[MatrixTarget],
) -> None:
    by_name = {target.name: target for target in targets}
    lines = [
        "# Agent Eval Model Matrix",
        "",
        "| Target | Model | Case pass | Sample pass | Avg latency |",
        "|---|---|---:|---:|---:|",
    ]
    for name, target_results in results.items():
        target = by_name[name]
        stats = summary(target_results)
        lines.append(
            f"| {name} | {target.model} | {stats['pass_rate']}% | "
            f"{stats['sample_pass_rate']}% | {stats['avg_latency_ms']} ms |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
