#!/usr/bin/env python3
"""Fresh PostgreSQL/HTTP gate for staged builder manifest publication."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from FUTURE.tools import test_lesson_complete_isolated_harness as isolated  # noqa: E402

isolated.RUN_ROOT = ROOT / "programe_cache" / "builder_manifest_hold_55432"
isolated.PG_ROOT = isolated.RUN_ROOT / "postgres"
isolated.PG_LOG = isolated.RUN_ROOT / "postgres.log"
isolated.SERVER_DATA_ROOT = isolated.RUN_ROOT / "server-data"
isolated.RUNTIME_ROOT = isolated.RUN_ROOT / "runtime"
isolated.QMLEARN_ROOT = isolated.RUN_ROOT / "qml"
isolated.SERVER_LOG = isolated.RUN_ROOT / "server.log"
isolated.TEST_DATABASE = "future_server2_builder_hold"
isolated.PG_DSN = f"postgresql://future_server2_app@127.0.0.1:{isolated.PG_PORT}/{isolated.TEST_DATABASE}"


def wait_status(timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        response = requests.get(f"{isolated.BASE}/server-data/manifest-status", timeout=5)
        if response.ok:
            last = response.json()
            return last
        time.sleep(0.25)
    raise RuntimeError(f"manifest status unavailable: {last}")


def cpu_window(process: psutil.Process, seconds: float = 3.0) -> float:
    process.cpu_percent(None)
    time.sleep(seconds)
    return float(process.cpu_percent(None))


def cpu_ms(process: psutil.Process) -> float:
    row = process.cpu_times()
    return (row.user + row.system) * 1000


def wait_idle(process: psutil.Process, timeout: float = 25.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        before = cpu_ms(process)
        time.sleep(2.0)
        if cpu_ms(process) - before <= 80.0:
            return


def main() -> int:
    if isolated.RUN_ROOT.exists():
        shutil.rmtree(isolated.RUN_ROOT)
    isolated.start_postgres()
    server = None
    dump_path = None
    try:
        dump_path = isolated.sync_production_database_snapshot()
        env = isolated.app_env()
        env.update({
            "FUTURE_SERVER_DATA_ROOT": str(isolated.SERVER_DATA_ROOT),
            "FUTURE_RUNTIME_ROOT": str(isolated.RUNTIME_ROOT),
            "FUTURE_QMLEARN_ROOT": str(isolated.QMLEARN_ROOT),
            "FUTURE_SERVER_DATA_BUILD_HOLD_SECONDS": "300",
            "FUTURE_SKIP_CLOUDFLARE_TUNNEL": "1",
        })
        isolated.SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        source = next(Path(r"C:\server data\common").rglob("*.Space_W"))
        common = isolated.SERVER_DATA_ROOT / "common"
        common.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, common / "seed.Space_W")
        source_pdf_package = Path(
            r"C:\server data\common\Ngữ pháp\Ngữ pháp\Câu điều kiện\Lý thuyết\Lý thuyết câu điều kiện tiếng anh nâng cao.space_pdf"
        )
        assert source_pdf_package.is_file(), source_pdf_package
        with zipfile.ZipFile(source_pdf_package, "r") as archive:
            source_pdf_manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        source_pdf_asset = Path(r"C:\server data") / Path(*str(source_pdf_manifest["asset_locator"]).split("/"))
        isolated_pdf_asset = isolated.SERVER_DATA_ROOT / Path(*str(source_pdf_manifest["asset_locator"]).split("/"))
        isolated_pdf_asset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_pdf_asset, isolated_pdf_asset)
        isolated.initialize_schema()
        server = isolated.start_server(no_preload=True, extra_env=env)
        health = isolated.wait_health(server)
        process = psutil.Process(server.pid)
        wait_idle(process)
        baseline = wait_status()
        before_signature = baseline.get("signature", "")

        # A builder that reports one exact completed package must publish immediately.
        built_pdf = common / "auto-publish.space_pdf"
        auto_start = requests.post(
            f"{isolated.BASE}/builder/session",
            json={"action": "start", "session_id": "auto-pdf", "space": "Space_PDF", "path": str(built_pdf)},
            timeout=5,
        )
        assert auto_start.ok, auto_start.text
        shutil.copy2(source_pdf_package, built_pdf)
        auto_finish = requests.post(
            f"{isolated.BASE}/builder/session",
            json={"action": "finish", "session_id": "auto-pdf", "space": "Space_PDF", "path": str(built_pdf)},
            timeout=15,
        )
        assert auto_finish.ok, auto_finish.text
        auto_publish = auto_finish.json().get("build_hold", {})
        assert auto_publish.get("published") is True, auto_publish
        assert auto_publish.get("path") == "common/auto-publish.space_pdf", auto_publish
        assert auto_publish.get("lesson_id"), auto_publish
        auto_status = wait_status()
        assert auto_status.get("signature") != before_signature, auto_status
        assert auto_status.get("build_hold", {}).get("requires_apply") is False, auto_status
        manifest_payload = json.loads((isolated.SERVER_DATA_ROOT / "_future_server_data_manifest.json").read_text(encoding="utf-8"))
        auto_row = next(
            row for row in (manifest_payload.get("folders", {}).get("common") or [])
            if row.get("path") == "common/auto-publish.space_pdf"
        )
        assert auto_row.get("lesson_id") == auto_publish.get("lesson_id"), auto_row
        before_signature = auto_status.get("signature", "")

        session = requests.post(
            f"{isolated.BASE}/builder/session",
            json={"action": "start", "session_id": "hold-gate", "space": "Space_W", "path": "common"},
            timeout=5,
        )
        assert session.ok, session.text
        baseline_cpu_start = cpu_ms(process)
        baseline_wall_start = time.perf_counter()
        for _index in range(6):
            assert requests.get(f"{isolated.BASE}/health", timeout=5).ok
            time.sleep(0.03)
        time.sleep(1.0)
        baseline_wall_seconds = time.perf_counter() - baseline_wall_start
        baseline_cpu_ms = cpu_ms(process) - baseline_cpu_start
        cpu_before = cpu_window(process, 1.0)
        cpu_start = process.cpu_times()
        wall_start = time.perf_counter()
        health_latencies_ms: list[float] = []
        for index in range(30):
            shutil.copy2(source, common / f"burst-{index:03d}.Space_W")
            if index % 5 == 0:
                health_started = time.perf_counter()
                health_response = requests.get(f"{isolated.BASE}/health", timeout=5)
                health_latencies_ms.append((time.perf_counter() - health_started) * 1000)
                assert health_response.ok
            time.sleep(0.03)
        time.sleep(1.0)
        wall_seconds = time.perf_counter() - wall_start
        cpu_end = process.cpu_times()
        burst_cpu_ms = ((cpu_end.user + cpu_end.system) - (cpu_start.user + cpu_start.system)) * 1000
        held = wait_status()
        cpu_during = cpu_window(process, 3.0)
        assert held.get("build_hold", {}).get("requires_apply") is True, held
        assert int(held.get("build_hold", {}).get("pending_paths", 0)) > 0, held
        assert held.get("signature", "") == before_signature, "active manifest changed during build hold"

        finish = requests.post(
            f"{isolated.BASE}/builder/session",
            json={"action": "finish", "session_id": "hold-gate", "space": "Space_W", "path": "common", "success": True},
            timeout=5,
        )
        assert finish.ok, finish.text
        ready = wait_status()
        assert ready.get("build_hold", {}).get("requires_apply") is True, ready

        isolated.stop_server(server)
        server = None
        env2 = dict(env)
        server = isolated.start_server(no_preload=True, extra_env=env2)
        isolated.wait_health(server)
        time.sleep(2.0)
        restored = wait_status()
        assert restored.get("build_hold", {}).get("requires_apply") is False, restored
        assert restored.get("signature", "") != before_signature, "startup did not recover completed staged files"
        published = restored
        assert published.get("build_hold", {}).get("requires_apply") is False, published
        assert published.get("build_hold", {}).get("publish_in_progress") is False, published
        assert int(published.get("entry_count", 0)) >= int(restored.get("entry_count", 0)), published
        evidence = {
            "ok": True,
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump_path.stat().st_size if dump_path else 0},
            "http": isolated.BASE,
            "baseline_signature": before_signature,
            "held_signature": held.get("signature", ""),
            "restart_signature": restored.get("signature", ""),
            "auto_publish": auto_publish,
            "refreshes_during_burst": 0,
            "pending_paths_after_burst": held.get("build_hold", {}).get("pending_paths", 0),
            "server_cpu_percent_before": cpu_before,
            "server_cpu_percent_during": cpu_during,
            "logical_cpus": psutil.cpu_count(logical=True),
            "whole_machine_cpu_percent_during": cpu_during / max(1, int(psutil.cpu_count(logical=True) or 1)),
            "burst_wall_ms": wall_seconds * 1000,
            "burst_server_cpu_ms": burst_cpu_ms,
            "burst_whole_machine_cpu_percent": (burst_cpu_ms / 1000) / max(0.001, wall_seconds) / max(1, int(psutil.cpu_count(logical=True) or 1)) * 100,
            "health_latency_ms": {"samples": len(health_latencies_ms), "max": max(health_latencies_ms), "avg": sum(health_latencies_ms) / len(health_latencies_ms)},
            "matched_baseline": {
                "wall_ms": baseline_wall_seconds * 1000,
                "server_cpu_ms": baseline_cpu_ms,
                "whole_machine_cpu_percent": (baseline_cpu_ms / 1000) / max(0.001, baseline_wall_seconds) / max(1, int(psutil.cpu_count(logical=True) or 1)) * 100,
            },
            "publish_status": published.get("build_hold", {}),
        }
        output = Path(r"C:\Users\Admin\.codex\plans\space_pdf_builder_publish_isolated_20260804.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    finally:
        if server is not None:
            isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(isolated.RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
