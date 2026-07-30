"""Read-only inventory and stable proposed identity map for legacy PDF/Picture lessons."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path


SERVER_DATA_ROOT = Path(r"C:\server data")
MANIFEST = SERVER_DATA_ROOT / "_future_server_data_manifest.json"
DATABASE = SERVER_DATA_ROOT / "server2.db"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
SIDE_DOCUMENT_NAMES = {
    "_future_space_pdf_ai_question_progress.json",
    "_future_space_pdf_ai_region_notices.json",
    "_future_space_pdf_ai_region_questions.json",
    "_future_space_pdf_audio_markers.json",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows_checksum(rows: list[dict]) -> str:
    raw = json.dumps(rows, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stable_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def load_existing_mapping(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "lessons": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    lessons = payload.get("lessons") if isinstance(payload, dict) and isinstance(payload.get("lessons"), dict) else {}
    return {"version": 1, "lessons": lessons}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--mapping", required=True)
    args = parser.parse_args()
    output_path = Path(args.output)
    mapping_path = Path(args.mapping)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries: list[dict] = []
    for folder_rows in (manifest.get("folders") or {}).values():
        for entry in folder_rows if isinstance(folder_rows, list) else []:
            if not isinstance(entry, dict) or str(entry.get("type") or "").lower() != "file":
                continue
            legacy_path = str(entry.get("path") or "").replace("\\", "/").strip("/")
            suffix = Path(legacy_path).suffix.lower()
            if suffix != ".pdf" and suffix not in IMAGE_SUFFIXES:
                continue
            effective_path = str(entry.get("link_target") or legacy_path).replace("\\", "/").strip("/")
            physical = SERVER_DATA_ROOT.joinpath(*effective_path.split("/"))
            entries.append({
                "legacy_path": legacy_path,
                "effective_path": effective_path,
                "kind": "pdf" if suffix == ".pdf" else "picture",
                "owner_scope": "common" if legacy_path.lower().startswith("common/") else legacy_path.split("/", 1)[0].lower(),
                "is_link": effective_path.lower() != legacy_path.lower(),
                "source_size": int(physical.stat().st_size if physical.is_file() else (entry.get("size", 0) or 0)),
                "source_mtime_ns": int(entry.get("modified_ns", 0) or 0),
                "source_exists": physical.is_file(),
                "source_sha256": file_sha256(physical) if physical.is_file() else "",
                "old_manifest_lesson_id": str(entry.get("lesson_id") or ""),
            })

    existing_mapping = load_existing_mapping(mapping_path)
    old_lessons = existing_mapping["lessons"]
    document_by_hash: dict[str, str] = {}
    lesson_by_effective: dict[str, str] = {}
    for row in old_lessons.values():
        if not isinstance(row, dict):
            continue
        if row.get("source_sha256") and row.get("document_id"):
            document_by_hash[str(row["source_sha256"])] = str(row["document_id"])
        if row.get("effective_path") and row.get("lesson_id"):
            lesson_by_effective[str(row["effective_path"]).lower()] = str(row["lesson_id"])

    next_lessons: dict[str, dict] = {}
    for entry in sorted(entries, key=lambda row: row["legacy_path"].lower()):
        previous = old_lessons.get(entry["legacy_path"]) if isinstance(old_lessons.get(entry["legacy_path"]), dict) else {}
        source_hash = entry["source_sha256"]
        document_id = str(previous.get("document_id") or document_by_hash.get(source_hash) or stable_id("ftg-document-"))
        if source_hash:
            document_by_hash[source_hash] = document_id
        effective_key = entry["effective_path"].lower()
        lesson_id = str(previous.get("lesson_id") or lesson_by_effective.get(effective_key) or stable_id("ftg-lesson-"))
        lesson_by_effective[effective_key] = lesson_id
        legacy = Path(entry["legacy_path"])
        output_rel = str(legacy.with_suffix(".space_pdf" if entry["kind"] == "pdf" else ".space_picture")).replace("\\", "/")
        next_lessons[entry["legacy_path"]] = {
            **entry,
            "lesson_id": lesson_id,
            "document_id": document_id,
            "proposed_package_path": output_rel,
            "stage": "discovered",
        }

    mapping_payload = {"version": 1, "lessons": next_lessons}
    mapping_path.write_text(json.dumps(mapping_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    progress_rows = [dict(row) for row in connection.execute(
        "SELECT username,path,identity,file_id,progress_key,server_revision,updated_at_utc,record_json "
        "FROM lesson_progress WHERE space='Space_PDF' ORDER BY username,path,progress_key"
    )]
    drawing_rows = [dict(row) for row in connection.execute(
        "SELECT username,path,identity,document_key,page,server_revision,updated_at_utc,content_hash,deleted "
        "FROM pdf_drawings ORDER BY username,path,document_key,page"
    )]
    time_rows = [dict(row) for row in connection.execute(
        "SELECT username,path,file_id,lesson_key,seconds,ticks,updated_at_utc FROM lesson_time "
        "WHERE lower(space) IN ('space_pdf','space_picture') ORDER BY username,path,lesson_key"
    )]
    side_documents = []
    for row in connection.execute("SELECT path,sha256,file_size FROM documents ORDER BY path"):
        if Path(str(row["path"])).name.lower() in SIDE_DOCUMENT_NAMES:
            side_documents.append(dict(row))
    task_rows = [dict(row) for row in connection.execute(
        "SELECT username,server_revision,updated_at_utc,record_json FROM lesson_task_state ORDER BY username"
    )]
    alias_paths = {str(row[0]).lower() for row in connection.execute("SELECT normalized_path FROM lesson_file_aliases")}
    connection.close()

    manifest_paths = {row["legacy_path"].lower() for row in entries}
    effective_paths = {row["effective_path"].lower() for row in entries}
    state_paths = {str(row.get("path") or "").replace("\\", "/").strip("/").lower() for row in progress_rows + drawing_rows + time_rows}
    orphan_state_paths = sorted(path for path in state_paths if path and path not in manifest_paths and path not in effective_paths)

    hashes = collections.defaultdict(list)
    for row in entries:
        if row["source_sha256"]:
            hashes[row["source_sha256"]].append(row["legacy_path"])
    duplicate_candidates = [
        {"source_sha256": source_hash, "paths": sorted(paths), "count": len(paths)}
        for source_hash, paths in hashes.items() if len(paths) > 1
    ]
    path_hash = {row["legacy_path"].lower(): row["source_sha256"] for row in entries}
    identities = collections.defaultdict(set)
    for row in progress_rows + drawing_rows:
        identity = str(row.get("identity") or "")
        source_hash = path_hash.get(str(row.get("path") or "").replace("\\", "/").strip("/").lower(), "")
        if identity and source_hash:
            identities[identity].add(source_hash)
    identity_collisions = [
        {"identity": identity, "source_hashes": sorted(source_hashes)}
        for identity, source_hashes in identities.items() if len(source_hashes) > 1
    ]
    duplicate_progress_groups = [
        {"username": username, "path": path, "rows": count}
        for (username, path), count in collections.Counter(
            (str(row.get("username") or ""), str(row.get("path") or "")) for row in progress_rows
        ).items() if count > 1
    ]
    task_path_references = sum(
        1 for row in task_rows for path in manifest_paths if path and path in str(row.get("record_json") or "").replace("\\", "/").lower()
    )

    route_files = [
        Path(r"C:\programe\write_html\FUTURE\server_parts\http_server\get_route_parts\04_pdf_picture_render.pyfrag"),
        Path(r"C:\programe\write_html\FUTURE\server_parts\http_server\get_route_parts\05_progress_vocab_leaderboard.pyfrag"),
        Path(r"C:\programe\write_html\FUTURE\server_parts\http_server\post_route_parts\02_pdf_ocr_scan.pyfrag"),
        Path(r"C:\programe\write_html\FUTURE\server_parts\http_server\post_route_parts\03_pdf_ai_tasks_auth.pyfrag"),
        Path(r"C:\programe\write_html\FUTURE\server_parts\http_server\post_route_parts\05_vocab_progress_leaderboard.pyfrag"),
    ]
    route_names = set()
    for path in route_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            marker = 'if path == "'
            if marker not in line:
                continue
            endpoint = line.split(marker, 1)[1].split('"', 1)[0]
            if endpoint.startswith(("/space-pdf/", "/pdf/", "/picture/")):
                route_names.add(endpoint)

    inventory = {
        "version": 1,
        "manifest": {
            "assets": len(entries),
            "pdf": sum(row["kind"] == "pdf" for row in entries),
            "picture": sum(row["kind"] == "picture" for row in entries),
            "bytes": sum(row["source_size"] for row in entries),
            "missing_files": sorted(row["legacy_path"] for row in entries if not row["source_exists"]),
            "links": sum(row["is_link"] for row in entries),
            "embedded_lesson_ids": sum(bool(row["old_manifest_lesson_id"]) for row in entries),
            "legacy_aliases_already_in_sqlite": sum(row["legacy_path"].lower() in alias_paths for row in entries),
        },
        "state": {
            "progress_rows": len(progress_rows),
            "progress_users": len({row["username"] for row in progress_rows}),
            "drawing_rows": len(drawing_rows),
            "drawing_users": len({row["username"] for row in drawing_rows}),
            "time_rows": len(time_rows),
            "side_documents": side_documents,
            "task_path_references": task_path_references,
            "orphan_state_paths": orphan_state_paths,
            "duplicate_progress_groups": duplicate_progress_groups,
        },
        "identity": {
            "proposed_lessons": len({row["lesson_id"] for row in next_lessons.values()}),
            "proposed_documents": len({row["document_id"] for row in next_lessons.values()}),
            "duplicate_content_groups": duplicate_candidates,
            "legacy_identity_collisions": identity_collisions,
        },
        "routes": {"path_or_context_endpoints": len(route_names), "endpoints": sorted(route_names)},
        "checksums": {
            "progress": rows_checksum(progress_rows),
            "drawings": rows_checksum(drawing_rows),
            "time": rows_checksum(time_rows),
            "side_documents": rows_checksum(side_documents),
            "mapping": rows_checksum(list(next_lessons.values())),
        },
        "estimated": {
            "self_contained_package_source_bytes": sum(row["source_size"] for row in entries),
            "temporary_disk_for_legacy_plus_packages": sum(row["source_size"] for row in entries) * 2,
        },
    }
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output_path),
        "mapping": str(mapping_path),
        "assets": inventory["manifest"]["assets"],
        "progress_rows": len(progress_rows),
        "drawing_rows": len(drawing_rows),
        "duplicates": len(duplicate_candidates),
        "collisions": len(identity_collisions),
        "orphans": len(orphan_state_paths),
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
