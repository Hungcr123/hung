"""Compare two PostgreSQL login warmup benchmark result files.

Added 2026-07-26: emits the fixed metric table required by the login warmup
baseline workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pick(row: dict[str, Any], dotted: str) -> Any:
    current: Any = row
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def number(value: Any) -> float | None:
    try:
        if value is None or value == "NOT MEASURED":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value: Any) -> str:
    parsed = number(value)
    if parsed is None:
        return "NOT MEASURED"
    if parsed.is_integer():
        return str(int(parsed))
    return f"{parsed:.3f}".rstrip("0").rstrip(".")


def delta(before: Any, after: Any) -> tuple[str, str]:
    left = number(before)
    right = number(after)
    if left is None or right is None:
        return "NOT MEASURED", "NOT MEASURED"
    change = right - left
    percent = (change / left * 100.0) if left else 0.0
    return fmt(change), f"{percent:.2f}%"


METRICS = (
    ("CPU/login", "summary.cpu_ms_per_login_flow"),
    ("Total CPU/30s", "summary.total_server_cpu_ms"),
    ("Login P50", "summary.flow_metrics.login_done_ms.p50_ms"),
    ("Login P95", "summary.flow_metrics.login_done_ms.p95_ms"),
    ("Login P99", "summary.flow_metrics.login_done_ms.p99_ms"),
    ("Login -> Vault", "summary.flow_metrics.lesson_vault_usable_ms.p95_ms"),
    ("Login -> warm complete", "summary.flow_metrics.warm_cache_done_ms.p95_ms"),
    ("PostgreSQL queries", "summary.postgres_delta.sql_execute"),
    ("Pool wait", "summary.postgres_delta.pool_wait_ms_total"),
    ("Payload bytes", "summary.endpoint_metrics.login_preload.response_bytes"),
    ("Total requests", "summary.total_requests"),
    ("Top first open", "summary.flow_metrics.top_usable_ms.p95_ms"),
    ("Space_V first open", "summary.flow_metrics.space_v_metadata_usable_ms.p95_ms"),
    ("Cache hit rate", "summary.cache_hit_rate"),
    ("Errors", "summary.errors"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("checkpoint")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    baseline = load(args.baseline)
    checkpoint = load(args.checkpoint)
    lines = [
        "| Metric | Current baseline | After optimization | Delta | Delta % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, path in METRICS:
        before = pick(baseline, path)
        after = pick(checkpoint, path)
        diff, percent = delta(before, after)
        lines.append(f"| {label} | {fmt(before)} | {fmt(after)} | {diff} | {percent} |")
    output = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
