"""Verify lossless PDF drawing migration from the backed-up document into row storage."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path


MAIN = Path(r"C:\server data\server2.db")
BEFORE = Path(r"E:\FutureServer2LegacyBackup\2026-07-20_133800_pdf_drawing_rows\server2_before.db")
DRAWING_PATH_KEY = os.path.normcase(os.path.abspath(r"C:\server data\_future_space_pdf_drawings.json"))


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def legacy_rows(connection: sqlite3.Connection) -> dict[tuple[str, str, int], str]:
    row = connection.execute("SELECT content,encoding FROM documents WHERE path_key=?", (DRAWING_PATH_KEY,)).fetchone()
    if row is None:
        return {}
    payload = json.loads(bytes(row[0]).decode(str(row[1] or "utf-8")))
    return {
        (str(username), str(document_key), int(page)): canonical(drawing)
        for username, documents in (payload.get("users") or {}).items()
        if isinstance(documents, dict)
        for document_key, document in documents.items()
        if isinstance(document, dict)
        for page, drawing in (document.get("pages") or {}).items()
        if isinstance(drawing, dict)
    }


def sqlite_rows(connection: sqlite3.Connection) -> dict[tuple[str, str, int], str]:
    return {
        (str(username), str(document_key), int(page)): canonical(json.loads(drawing_json))
        for username, document_key, page, drawing_json in connection.execute(
            "SELECT username,document_key,page,drawing_json FROM pdf_drawings"
        )
    }


def main() -> int:
    before = sqlite3.connect(BEFORE)
    current = sqlite3.connect(MAIN)
    try:
        expected = legacy_rows(before)
        actual = sqlite_rows(current)
        migrated_actual = {key: value for key, value in actual.items() if not key[0].lower().startswith("codexload")}
        assert expected, "Backup drawing document is empty"
        assert migrated_actual == expected, {
            "expected": len(expected),
            "actual": len(migrated_actual),
            "missing": sorted(set(expected) - set(migrated_actual))[:5],
            "extra": sorted(set(migrated_actual) - set(expected))[:5],
            "different": [key for key in expected.keys() & migrated_actual.keys() if expected[key] != migrated_actual[key]][:5],
        }
        assert current.execute("SELECT 1 FROM documents WHERE path_key=?", (DRAWING_PATH_KEY,)).fetchone() is None
        assert current.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert current.execute("SELECT value FROM database_meta WHERE key='schema_version'").fetchone()[0] == "7"
        print(f"pdf_drawing_sqlite=ok rows={len(migrated_actual)} legacy_document=retired schema=7")
    finally:
        current.close()
        before.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
