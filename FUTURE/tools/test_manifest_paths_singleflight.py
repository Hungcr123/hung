"""Regression gate for coalesced Server Data manifest path refreshes."""

from __future__ import annotations

import threading
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import FUTURE.server_app as app


def main() -> int:
    state = app.SERVER_DATA_MANIFEST_STATE
    with app.SERVER_DATA_MANIFEST_LOCK:
        state["pending_paths"] = set()
        state["paths_timer"] = None
        state["paths_running"] = False
        state["build_hold_active"] = False
        state["build_hold_requires_apply"] = False
        state["build_hold_publish_in_progress"] = False
        state["build_hold_full_refresh_pending"] = False
        state["build_sessions"] = {}

    entered = threading.Event()
    release = threading.Event()
    calls: list[set[str]] = []
    active = 0
    max_active = 0
    original = app.refresh_server_data_manifest_delta_paths_now

    def fake_refresh(paths, reason=""):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        calls.append(set(paths))
        entered.set()
        if len(calls) == 1:
            if not release.wait(3):
                raise AssertionError("first refresh did not release")
        active -= 1
        return {}

    app.refresh_server_data_manifest_delta_paths_now = fake_refresh
    try:
        app.server_data_manifest_build_hold_note_activity("test-builder")
        app.schedule_server_data_manifest_paths_refresh({"common/staged"}, delay=0.01, reason="test-hold")
        time.sleep(0.08)
        if calls:
            raise AssertionError(f"build hold refreshed before apply: {calls!r}")
        with app.SERVER_DATA_MANIFEST_LOCK:
            if "common/staged" not in state.get("pending_paths", set()):
                raise AssertionError("held path was not retained")
            state["build_hold_active"] = False
            state["build_hold_requires_apply"] = False
            state["pending_paths"] = set()
        app.schedule_server_data_manifest_paths_refresh({"common/a"}, delay=0.01, reason="test")
        if not entered.wait(2):
            raise AssertionError("first refresh did not start")
        app.schedule_server_data_manifest_paths_refresh({"common/b"}, delay=0.01, reason="test")
        app.schedule_server_data_manifest_paths_refresh({"common/c"}, delay=0.01, reason="test")
        release.set()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and len(calls) < 2:
            time.sleep(0.02)
        if max_active != 1 or len(calls) != 2 or calls[1] != {"common/b", "common/c"}:
            raise AssertionError(f"singleflight failed: calls={calls!r}, max_active={max_active}")
    finally:
        app.refresh_server_data_manifest_delta_paths_now = original
        with app.SERVER_DATA_MANIFEST_LOCK:
            timer = state.get("paths_timer")
            state["pending_paths"] = set()
            state["paths_timer"] = None
            state["paths_running"] = False
            state["build_hold_active"] = False
            state["build_hold_requires_apply"] = False
            state["build_hold_publish_in_progress"] = False
            state["build_hold_full_refresh_pending"] = False
            state["build_sessions"] = {}
        if timer is not None:
            timer.cancel()
    print("manifest_paths_singleflight=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
