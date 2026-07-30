"""Focused approval compensation probe for pending registration failures."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = Path(r"E:\FutureServer2PostgresMigrationBackups\20260726_snapshot_baseline_20260726_032052")
USERNAME_PG = "codexapprovalpg"
USERNAME_FILE = "codexapprovalfile"
PASSWORD = "CodexApproval42"


@contextlib.contextmanager
def patched(module, **replacements):
    original = {}
    for name, value in replacements.items():
        original[name] = getattr(module, name)
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(module, name, value)


def clone_roots() -> tuple[Path, Path]:
    work_root = Path(tempfile.mkdtemp(prefix="codex_auth_approval_focus_"))
    server_data = work_root / "server data"
    qmlearn = work_root / "QMLearn"
    shutil.copytree(SNAPSHOT_ROOT / "server data", server_data)
    shutil.copytree(SNAPSHOT_ROOT / "QMLearn", qmlearn)
    return server_data, qmlearn


def load_app(server_data: Path, qmlearn: Path):
    os.environ["FUTURE_SERVER_DATA_ROOT"] = str(server_data)
    os.environ["FUTURE_QMLEARN_ROOT"] = str(qmlearn)
    sys.path.insert(0, str(ROOT))
    import FUTURE.server_app as app  # noqa: WPS433

    return app


def state(app, username: str) -> dict:
    user_file = app.user_file_path(username)
    user_folder = app.user_folder_path(username)
    return {
        "user_file": user_file.is_file(),
        "user_folder": user_folder.is_dir(),
        "pending_file": app.load_pending_users().get(username, {}).get("status", ""),
        "profile": app.read_user_profile(username),
    }


def main() -> int:
    server_data, qmlearn = clone_roots()
    app = load_app(server_data, qmlearn)
    try:
        app.submit_pending_registration({
            "username": USERNAME_PG,
            "password": PASSWORD,
            "full_name": "Codex Approval",
            "gender": "other",
            "birth_date": "2000-01-01",
        })
        before = state(app, USERNAME_PG)

        def fail_pg(*_args, **_kwargs):
            raise RuntimeError("forced_pg_failure")

        pg_failed = False
        try:
            with patched(app, postgres_upsert_user_auth_credential=fail_pg):
                app.approve_pending_registration(USERNAME_PG, "accept")
        except RuntimeError as exc:
            pg_failed = "forced_pg_failure" in str(exc)
        after_pg = state(app, USERNAME_PG)

        app.submit_pending_registration({
            "username": USERNAME_FILE,
            "password": PASSWORD,
            "full_name": "Codex Approval",
            "gender": "other",
            "birth_date": "2000-01-01",
        })

        def fail_final_save(_payload):
            raise RuntimeError("forced_file_failure")

        file_failed = False
        try:
            with patched(app, save_pending_users=fail_final_save):
                app.approve_pending_registration(USERNAME_FILE, "accept")
        except RuntimeError as exc:
            file_failed = "forced_file_failure" in str(exc)
        after_file = state(app, USERNAME_FILE)

        cleanup = {
            "pending_pg": app.load_pending_users().get(USERNAME_PG),
            "pending_file": app.load_pending_users().get(USERNAME_FILE),
            "user_file_pg": app.user_file_path(USERNAME_PG).exists(),
            "user_folder_pg": app.user_folder_path(USERNAME_PG).exists(),
            "user_file_file": app.user_file_path(USERNAME_FILE).exists(),
            "user_folder_file": app.user_folder_path(USERNAME_FILE).exists(),
        }
        result = {
            "ok": bool(pg_failed and file_failed and after_pg["pending_file"] == "pending" and after_file["pending_file"] == "pending"),
            "before": before,
            "after_pg": after_pg,
            "after_file": after_file,
            "cleanup": cleanup,
            "pg_failed": pg_failed,
            "file_failed": file_failed,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    finally:
        shutil.rmtree(server_data.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
