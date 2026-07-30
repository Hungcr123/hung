"""Measure linked-folder navigation without mutating live lesson data."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def logical_folder_links(manifest: dict) -> list[dict]:
    entries = [
        dict(entry)
        for rows in (manifest.get("folders") or {}).values()
        for entry in (rows if isinstance(rows, list) else [])
        if isinstance(entry, dict)
        and entry.get("type") == "folder"
        and app.clean_path_value(entry.get("link_target", ""))
    ]
    linked_paths = {app.clean_path_value(entry.get("path", "")).lower() for entry in entries}
    roots = []
    for entry in entries:
        path = app.clean_path_value(entry.get("path", ""))
        parts = path.split("/")
        if any("/".join(parts[:index]).lower() in linked_paths for index in range(1, len(parts))):
            continue
        roots.append(entry)
    return roots


def navigation_cases(manifest: dict, limit: int) -> list[tuple[str, str]]:
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    cases: list[tuple[str, str]] = []
    for link in logical_folder_links(manifest):
        display_root = app.clean_path_value(link.get("path", ""))
        target_root = app.clean_path_value(link.get("link_target", ""))
        username = app.normalize_username(display_root.split("/", 1)[0])
        target_keys = sorted(
            key for key in folders
            if key == target_root or key.startswith(target_root + "/")
        )
        for target_path in target_keys:
            suffix = target_path[len(target_root):].lstrip("/")
            display_path = app.clean_path_value(f"{display_root}/{suffix}" if suffix else display_root)
            cases.append((username, display_path))
    if not cases:
        raise RuntimeError("No logical folder-link navigation cases found.")
    expanded = []
    while len(expanded) < limit:
        expanded.extend(cases)
    return expanded[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--label", default="folder-link")
    parser.add_argument("--output", default="")
    parser.add_argument("--manifest-state", choices=("current", "clean", "dirty"), default="current")
    args = parser.parse_args()

    manifest = app.get_server_data_manifest(force=False)
    if args.manifest_state != "current":
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = args.manifest_state == "dirty"
    cases = navigation_cases(manifest, max(1, int(args.requests or 100)))
    if getattr(app, "SERVER_DATABASE_WRITER_STARTED", False):
        app.SERVER_DATABASE_WRITE_QUEUE.join()
    writer_before = app.server_database_write_metrics_snapshot()
    process = psutil.Process(os.getpid())
    io_before = process.io_counters()
    wal = Path(str(app.SERVER_DATABASE_FILE) + "-wal")
    wal_before = wal.stat().st_size if wal.is_file() else 0
    latencies = []
    entries = 0
    errors = []
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    for username, path in cases:
        started = time.perf_counter()
        try:
            payload = app.list_server_data(
                path,
                username=username,
                admin=False,
                fresh=True,
                lightweight=True,
                include_task_board=False,
                include_space_task=False,
            )
            entries += len(payload.get("entries", [])) if isinstance(payload, dict) else 0
        except Exception as exc:
            errors.append({"user": username, "path": path, "error": str(exc)})
        latencies.append((time.perf_counter() - started) * 1000.0)
    wall = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    io_after = process.io_counters()
    wal_after = wal.stat().st_size if wal.is_file() else 0
    if getattr(app, "SERVER_DATABASE_WRITER_STARTED", False):
        app.SERVER_DATABASE_WRITE_QUEUE.join()
    writer_after = app.server_database_write_metrics_snapshot()
    result = {
        "label": args.label,
        "requests": len(cases),
        "logical_links": len(logical_folder_links(manifest)),
        "manifest_dirty": bool(app.SERVER_DATA_MANIFEST_STATE.get("dirty")),
        "unique_paths": len(set(cases)),
        "errors": len(errors),
        "error_sample": errors[:5],
        "entries": entries,
        "cpu_ms_per_request": round(cpu * 1000.0 / len(cases), 3),
        "wall_ms_per_request": round(wall * 1000.0 / len(cases), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "requests_per_second": round(len(cases) / wall, 3) if wall else 0.0,
        "read_ops": max(0, int(io_after.read_count - io_before.read_count)),
        "read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
        "write_ops": max(0, int(io_after.write_count - io_before.write_count)),
        "write_bytes": max(0, int(io_after.write_bytes - io_before.write_bytes)),
        "wal_growth": max(0, wal_after - wal_before),
        "sqlite_writer_tasks": max(0, int(writer_after.get("tasks", 0) or 0) - int(writer_before.get("tasks", 0) or 0)),
        "sqlite_writer_batches": max(0, int(writer_after.get("batches", 0) or 0) - int(writer_before.get("batches", 0) or 0)),
        "sqlite_busy_errors": max(0, int(writer_after.get("busy_errors", 0) or 0) - int(writer_before.get("busy_errors", 0) or 0)),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
