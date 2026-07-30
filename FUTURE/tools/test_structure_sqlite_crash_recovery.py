"""Validate Structure/OCR durability after a forced Server 2 termination."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_structure_asset_store import ocr_cache_page_text, structure_asset_json


def main() -> int:
    probe = structure_asset_json("Structure/codex-crash-probe.json")
    if probe.get("w", [{}])[0].get("w") != "durable":
        raise AssertionError("Crash probe Structure row was not restored")
    if not ocr_cache_page_text("627_1- Empower 2nd B1 Student_s Book", "1.txt").strip():
        raise AssertionError("OCR SQLite row was not restored")
    main_db = sqlite3.connect(r"C:\server data\server2.db")
    structure_db = sqlite3.connect(r"C:\server data\structure_assets.db")
    try:
        main_status = (
            main_db.execute("PRAGMA quick_check").fetchone()[0],
            main_db.execute("PRAGMA journal_mode").fetchone()[0],
            main_db.execute("PRAGMA synchronous").fetchone()[0],
        )
        login_rows = main_db.execute(
            "SELECT COUNT(*) FROM append_events WHERE stream='login' AND username='hung'"
        ).fetchone()[0]
        structure_status = (
            structure_db.execute("PRAGMA quick_check").fetchone()[0],
            structure_db.execute("PRAGMA journal_mode").fetchone()[0],
            structure_db.execute("PRAGMA synchronous").fetchone()[0],
        )
        ocr_rows = structure_db.execute("SELECT COUNT(*) FROM ocr_pages").fetchone()[0]
        structure_db.execute("DELETE FROM assets WHERE path_key='codex-crash-probe.json'")
        structure_db.commit()
    finally:
        main_db.close()
        structure_db.close()
    print(
        f"main={main_status} login_rows={login_rows} structure={structure_status} "
        f"ocr_rows={ocr_rows} probe={probe.get('t')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
