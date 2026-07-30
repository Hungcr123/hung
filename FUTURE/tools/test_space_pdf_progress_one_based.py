"""Regression for one-based PDF/Picture progress from save through SQLite summary."""

from __future__ import annotations

import copy
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-pdf-one-based-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        app.SERVER_DATA_ROOT = root / "server-data"
        app.USER_ROOT = root / "users"
        app.SERVER_DATABASE_FILE = app.SERVER_DATA_ROOT / "server2.db"
        app.SERVER_DATABASE_BACKUP_FILE = app.SERVER_DATA_ROOT / "server2.db.backup"
        app.SERVER_DATABASE_READY = False
        app.SERVER_DATABASE_READY_STATUS = {}
        app.initialize_server_database()

        username = "codexpdfonebased"
        lesson_id = "ftg-lesson-pdf-one-based-regression"
        path = "common/PDF/one-based.space_pdf"
        key = app.space_pdf_progress_key(username, path, lesson_id)
        store = {
            "payload": app.default_space_progress_payload(),
            "write_revision": 0,
        }
        original_identity = app.space_pdf_progress_identity_for_source
        original_loader = app.load_space_progress_store
        original_bump = app.bump_login_preload_cache_generation
        original_patch = app.update_lesson_progress_index_cache_record
        try:
            app.space_pdf_progress_identity_for_source = lambda _username, _source: {
                "path": path,
                "legacy_key": "",
                "identity": lesson_id,
            }
            app.load_space_progress_store = lambda _space, _username: store
            app.bump_login_preload_cache_generation = lambda _username: None
            app.update_lesson_progress_index_cache_record = lambda *_args, **_kwargs: True

            payload = {
                "version": 2,
                "path": path,
                "identity": lesson_id,
                "lesson_id": lesson_id,
                "title": "One-based PDF",
                "page": 15,
                "pages": 256,
                "currentNode": 15,
                "nodeIndex": 15,
                "nodeIndexBase": 1,
                "nodeCount": 256,
                "savedAt": "2026-07-22T07:02:02Z",
                "state": {
                    "mode": "pdf",
                    "page": 15,
                    "pages": 256,
                    "currentNode": 15,
                    "nodeIndex": 15,
                    "nodeIndexBase": 1,
                    "savedAt": "2026-07-22T07:02:02Z",
                },
            }
            saved = app.save_space_pdf_progress(username, payload)
            assert saved["page"] == saved["currentNode"] == saved["nodeIndex"] == 15

            connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
            row = connection.execute(
                "SELECT node_index,node_count,server_revision,record_json FROM lesson_progress "
                "WHERE username=? AND space='Space_PDF' AND progress_key=?",
                (username, key),
            ).fetchone()
            assert row is not None
            record = json.loads(row[3])
            assert (row[0], row[1]) == (15, 256)
            assert record["page"] == record["currentNode"] == record["nodeIndex"] == 15
            assert "text" not in record
            summary = app.build_lesson_progress_summary(record, "Space_PDF", 256)
            assert (summary["done"], summary["total"], summary["text"]) == (15, 256, "15/256")

            revision = row[2]
            retry = copy.deepcopy(payload)
            retry["savedAt"] = "2026-07-22T07:03:02Z"
            retry["state"]["savedAt"] = retry["savedAt"]
            app.save_space_pdf_progress(username, retry)
            equal_epoch_lower = copy.deepcopy(payload)
            equal_epoch_lower.update({"page": 14, "currentNode": 14, "nodeIndex": 14, "savedAt": "2026-07-22T14:02:02+07:00"})
            equal_epoch_lower["state"].update({"page": 14, "currentNode": 14, "nodeIndex": 14, "savedAt": equal_epoch_lower["savedAt"]})
            app.save_space_pdf_progress(username, equal_epoch_lower)
            connection.close()

            connection = sqlite3.connect(app.SERVER_DATABASE_FILE)
            final_row = connection.execute(
                "SELECT node_index,node_count,server_revision,record_json FROM lesson_progress "
                "WHERE username=? AND space='Space_PDF' AND progress_key=?",
                (username, key),
            ).fetchone()
            final_record = json.loads(final_row[3])
            assert (final_row[0], final_row[1], final_row[2]) == (15, 256, revision)
            assert app.build_lesson_progress_summary(final_record, "Space_PDF", 256)["text"] == "15/256"
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            connection.close()
        finally:
            app.space_pdf_progress_identity_for_source = original_identity
            app.load_space_progress_store = original_loader
            app.bump_login_preload_cache_generation = original_bump
            app.update_lesson_progress_index_cache_record = original_patch
            app.SERVER_DATABASE_WRITE_QUEUE.put(None)
            app.SERVER_DATABASE_WRITE_QUEUE.join()

    print("space_pdf_progress_one_based=ok page=node=done=15 total=256 text=derived retry=noop equal-epoch=reject")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
