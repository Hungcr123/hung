"""Verify package/state equality after copied Space PDF shadow migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import validate_space_pdf_package
from FUTURE.tools.migrate_space_pdf_shadow_copy import SIDE_DOCUMENTS, clean_path, decode_document, portable_child_for_path, progress_winner


def table_hash(connection: sqlite3.Connection, table: str) -> str:
    rows = [tuple(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--migrated", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    lessons = json.loads(args.mapping.read_text(encoding="utf-8"))["lessons"]
    ordered_pdf_rows = [(path, row) for path, row in sorted(lessons.items(), key=lambda item: item[0].lower()) if row.get("kind") == "pdf"]
    if args.limit > 0:
        ordered_pdf_rows = ordered_pdf_rows[: args.limit]
    pdf_rows = dict(ordered_pdf_rows)
    path_to_id = {clean_path(path).lower(): str(row["lesson_id"]) for path, row in pdf_rows.items()}
    baseline = sqlite3.connect(f"file:{args.baseline}?mode=ro", uri=True)
    migrated = sqlite3.connect(f"file:{args.migrated}?mode=ro", uri=True)
    baseline.row_factory = sqlite3.Row
    migrated.row_factory = sqlite3.Row

    stores = {label: decode_document(baseline, filename) for label, filename in SIDE_DOCUMENTS.items()}
    package_child_counts = {label: 0 for label in SIDE_DOCUMENTS}
    package_errors = []
    for legacy_path, row in pdf_rows.items():
        package = args.package_root.joinpath(*clean_path(row["proposed_package_path"]).split("/"))
        try:
            manifest = validate_space_pdf_package(package, verify_source=True)
            if manifest["lesson_id"] != row["lesson_id"] or manifest["document_id"] != row["document_id"] or manifest["source_sha256"] != row["source_sha256"]:
                raise RuntimeError("identity/fingerprint mismatch")
            content_members = manifest.get("content_members") if isinstance(manifest.get("content_members"), dict) else {}
            with zipfile.ZipFile(package, "r") as archive:
                for label in SIDE_DOCUMENTS:
                    expected = portable_child_for_path(stores[label], legacy_path)
                    metadata = content_members.get(label)
                    if expected is None and metadata is not None:
                        raise RuntimeError(f"unexpected {label}")
                    if expected is not None:
                        if not isinstance(metadata, dict):
                            raise RuntimeError(f"missing {label}")
                        actual = json.loads(archive.read(str(metadata["member"])).decode("utf-8"))
                        if actual != expected:
                            raise RuntimeError(f"{label} payload mismatch")
                        package_child_counts[label] += 1
        except Exception as exc:
            package_errors.append({"path": legacy_path, "error": str(exc)})

    baseline_progress = [row for row in baseline.execute("SELECT * FROM lesson_progress WHERE space='Space_PDF'") if clean_path(row["path"]).lower() in path_to_id]
    source_rows = migrated.execute("SELECT * FROM space_pdf_progress_migration_sources").fetchall()
    source_index = {(str(row["username"]).lower(), str(row["file_id"]), str(row["source_progress_key"])): row for row in source_rows}
    progress_source_mismatch = []
    groups: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in baseline_progress:
        file_id = path_to_id[clean_path(row["path"]).lower()]
        key = (str(row["username"]).lower(), file_id, str(row["progress_key"]))
        shadow = source_index.get(key)
        if shadow is None or shadow["record_json"] != row["record_json"] or int(shadow["server_revision"]) != int(row["server_revision"]):
            progress_source_mismatch.append(key)
        groups.setdefault((key[0], file_id), []).append(row)
    canonical_mismatch = []
    for (username, file_id), rows in groups.items():
        winner = progress_winner(rows)
        shadow = migrated.execute(
            "SELECT * FROM space_pdf_progress_shadow WHERE username=? AND file_id=?",
            (username, file_id),
        ).fetchone()
        if shadow is None or shadow["source_progress_key"] != winner["progress_key"] or shadow["record_json"] != winner["record_json"]:
            canonical_mismatch.append((username, file_id))

    baseline_drawings = [row for row in baseline.execute("SELECT * FROM pdf_drawings") if clean_path(row["path"]).lower() in path_to_id]
    drawing_mismatch = []
    for row in baseline_drawings:
        file_id = path_to_id[clean_path(row["path"]).lower()]
        shadow = migrated.execute(
            "SELECT * FROM space_pdf_drawing_shadow WHERE username=? AND file_id=? AND page=?",
            (row["username"], file_id, row["page"]),
        ).fetchone()
        if shadow is None or shadow["drawing_json"] != row["drawing_json"] or int(shadow["server_revision"]) != int(row["server_revision"]) or int(shadow["deleted"]) != int(row["deleted"]):
            drawing_mismatch.append((row["username"], file_id, row["page"]))

    def strip_added_ids(value: object) -> object:
        if isinstance(value, list):
            return [strip_added_ids(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: strip_added_ids(item) for key, item in value.items()}
        path_key = clean_path(result.get("effective_path") or result.get("path")).lower()
        if path_key in path_to_id:
            if result.get("lesson_id") == path_to_id[path_key]:
                result.pop("lesson_id", None)
            if result.get("file_id") == path_to_id[path_key]:
                result.pop("file_id", None)
        return result

    task_mismatch = []
    for row in baseline.execute("SELECT username,record_json FROM lesson_task_state"):
        migrated_row = migrated.execute("SELECT record_json FROM lesson_task_state WHERE username=?", (row["username"],)).fetchone()
        if migrated_row is None or strip_added_ids(json.loads(migrated_row[0])) != strip_added_ids(json.loads(row["record_json"])):
            task_mismatch.append(row["username"])

    untouched_tables = ["users", "inventory_items", "inventory_events", "append_events", "vocabulary_events", "auth_sessions"]
    untouched_mismatch = [table for table in untouched_tables if table_hash(baseline, table) != table_hash(migrated, table)]
    leftovers = [str(path) for path in args.package_root.rglob("*") if path.is_file() and (path.name.endswith(".tmp") or path.name.endswith(".build.lock"))]
    report = {
        "packages_expected": len(pdf_rows),
        "packages_invalid": package_errors,
        "embedded_child_packages": package_child_counts,
        "progress_sources_expected": len(baseline_progress),
        "progress_sources_actual": len(source_rows),
        "progress_source_mismatch": progress_source_mismatch,
        "canonical_expected": len(groups),
        "canonical_actual": migrated.execute("SELECT COUNT(*) FROM space_pdf_progress_shadow").fetchone()[0],
        "canonical_mismatch": canonical_mismatch,
        "drawings_expected": len(baseline_drawings),
        "drawings_actual": migrated.execute("SELECT COUNT(*) FROM space_pdf_drawing_shadow").fetchone()[0],
        "drawing_mismatch": drawing_mismatch,
        "task_mismatch": task_mismatch,
        "untouched_table_mismatch": untouched_mismatch,
        "leftover_build_files": leftovers,
        "foreign_key_errors": len(migrated.execute("PRAGMA foreign_key_check").fetchall()),
        "quick_check": migrated.execute("PRAGMA quick_check").fetchone()[0],
    }
    report["ok"] = not any((package_errors, progress_source_mismatch, canonical_mismatch, drawing_mismatch, task_mismatch, untouched_mismatch, leftovers, report["foreign_key_errors"])) and report["quick_check"] == "ok" and report["progress_sources_expected"] == report["progress_sources_actual"] and report["canonical_expected"] == report["canonical_actual"] and report["drawings_expected"] == report["drawings_actual"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    baseline.close()
    migrated.close()
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
