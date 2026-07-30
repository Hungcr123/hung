"""Measure portable Space PDF manifest reads without hashing embedded PDF bytes."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import read_space_pdf_manifest_light


DEFAULT_PACKAGE = Path(
    r"E:\FutureServer2LegacyBackup\20260722_0600_pdf_picture_asset_schema_phase1\prototype_samples\sample.space_pdf"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--reads", type=int, default=1000)
    args = parser.parse_args()
    package = args.package.resolve()
    reads = max(1, int(args.reads))
    if not package.is_file():
        raise SystemExit(f"Package not found: {package}")

    manifest = read_space_pdf_manifest_light(package)
    samples_ms: list[float] = []
    cpu_start = time.process_time_ns()
    wall_start = time.perf_counter_ns()
    for _index in range(reads):
        started = time.perf_counter_ns()
        current = read_space_pdf_manifest_light(package)
        samples_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        if current.get("lesson_id") != manifest.get("lesson_id"):
            raise RuntimeError("Manifest identity changed during benchmark.")
    wall_ms = (time.perf_counter_ns() - wall_start) / 1_000_000
    cpu_ms = (time.process_time_ns() - cpu_start) / 1_000_000
    ordered = sorted(samples_ms)
    result = {
        "package_bytes": package.stat().st_size,
        "reads": reads,
        "cpu_ms_per_read": round(cpu_ms / reads, 6),
        "wall_ms_per_read": round(wall_ms / reads, 6),
        "p50_ms": round(statistics.median(ordered), 6),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 6),
        "p99_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))], 6),
        "lesson_id": manifest.get("lesson_id"),
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
