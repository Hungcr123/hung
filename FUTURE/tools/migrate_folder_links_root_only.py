"""Remove propagated folder-link documents/skeletons after root registry migration."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SERVER_DATA_ROOT = Path(r"C:\server data")
SERVER_DATABASE_FILE = SERVER_DATA_ROOT / "server2.db"
SERVER_DATA_MANIFEST_FILE = SERVER_DATA_ROOT / "_future_server_data_manifest.json"
MARKER_NAME = "._future_folder_link.json"


def clean_path(value: object = "") -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def relative_marker_path(path_value: str) -> str:
    target = Path(path_value)
    try:
        relative = target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
    except Exception:
        relative = clean_path(path_value)
    suffix = "/" + MARKER_NAME
    return relative[:-len(suffix)] if relative.lower().endswith(suffix.lower()) else relative


def atomic_write_json(path: Path, payload: dict) -> None:
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect(connection: sqlite3.Connection) -> dict:
    roots = {
        clean_path(row[0]).lower(): {"path": clean_path(row[0]), "target": clean_path(row[1])}
        for row in connection.execute("SELECT link_path,target_path FROM lesson_folder_links WHERE status='active'")
    }
    documents = []
    for row in connection.execute("SELECT path_key,path,content,encoding FROM documents WHERE lower(path) LIKE ?", (f"%{MARKER_NAME.lower()}",)):
        try:
            payload = json.loads(bytes(row[2] or b"").decode(str(row[3] or "utf-8"), errors="replace").lstrip("\ufeff"))
        except Exception:
            payload = {}
        documents.append({
            "path_key": str(row[0]),
            "path": str(row[1]),
            "relative": relative_marker_path(str(row[1])),
            "target": clean_path(payload.get("target", "")) if isinstance(payload, dict) else "",
        })
    descendants = []
    invalid = []
    for document in documents:
        relative = document["relative"]
        root = next(
            (item for key, item in roots.items() if relative.lower().startswith(key + "/")),
            None,
        )
        if not root:
            continue
        suffix = relative[len(root["path"]):].lstrip("/")
        expected = clean_path(f"{root['target']}/{suffix}" if suffix else root["target"])
        if document["target"].lower() != expected.lower():
            invalid.append({**document, "expected": expected})
        else:
            descendants.append({**document, "root": root["path"], "expected": expected})
    skeleton_dirs = []
    unsafe_files = []
    for root in roots.values():
        folder = SERVER_DATA_ROOT.joinpath(*root["path"].split("/"))
        if not folder.is_dir():
            continue
        for target in folder.rglob("*"):
            if target.is_file():
                unsafe_files.append(str(target))
            elif target.is_dir():
                skeleton_dirs.append(str(target))
    return {
        "roots": list(roots.values()),
        "document_count": len(documents),
        "propagated_documents": descendants,
        "invalid_documents": invalid,
        "skeleton_dirs": sorted(set(skeleton_dirs), key=lambda value: (-value.count(os.sep), value.lower())),
        "unsafe_files": unsafe_files,
    }


def patch_manifest(root_paths: list[str]) -> int:
    if not SERVER_DATA_MANIFEST_FILE.is_file():
        return 0
    manifest = json.loads(SERVER_DATA_MANIFEST_FILE.read_text(encoding="utf-8-sig", errors="replace"))
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    changed = 0
    for root in root_paths:
        for key in list(folders):
            if key.startswith(root + "/"):
                folders.pop(key, None)
                changed += 1
        if folders.get(root) != []:
            folders[root] = []
            changed += 1
    if changed:
        manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest["runtime_revision"] = f"folder-link-root-only-{time.time_ns()}"
        atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest)
    return changed


def migrate(backup_dir: Path) -> dict:
    if not backup_dir.is_dir() or not (backup_dir / "server2.db").is_file():
        raise RuntimeError("A verified backup containing server2.db is required.")
    connection = sqlite3.connect(SERVER_DATABASE_FILE, timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        before = inspect(connection)
        if before["invalid_documents"]:
            raise RuntimeError(f"Refusing mismatched propagated links: {before['invalid_documents'][:3]}")
        if before["unsafe_files"]:
            raise RuntimeError(f"Refusing non-empty linked skeletons: {before['unsafe_files'][:3]}")
        connection.execute("BEGIN IMMEDIATE")
        for row in before["propagated_documents"]:
            connection.execute("DELETE FROM documents WHERE path_key=?", (row["path_key"],))
            connection.execute("DELETE FROM lesson_folder_links WHERE link_path=? COLLATE NOCASE", (row["relative"],))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    removed_dirs = 0
    for raw in before["skeleton_dirs"]:
        target = Path(raw)
        try:
            target.resolve().relative_to(SERVER_DATA_ROOT.resolve())
            target.rmdir()
            removed_dirs += 1
        except OSError:
            continue
    manifest_changes = patch_manifest([row["path"] for row in before["roots"]])
    verify = sqlite3.connect(SERVER_DATABASE_FILE, timeout=30.0)
    verify.row_factory = sqlite3.Row
    try:
        after = inspect(verify)
        quick_check = str(verify.execute("PRAGMA quick_check").fetchone()[0])
    finally:
        verify.close()
    return {
        "backup": str(backup_dir),
        "roots": len(before["roots"]),
        "removed_documents": len(before["propagated_documents"]),
        "removed_dirs": removed_dirs,
        "manifest_changes": manifest_changes,
        "remaining_documents": after["document_count"],
        "remaining_propagated": len(after["propagated_documents"]),
        "remaining_unsafe_files": len(after["unsafe_files"]),
        "quick_check": quick_check,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    connection = sqlite3.connect(SERVER_DATABASE_FILE, timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        result = migrate(Path(args.backup_dir)) if args.apply else inspect(connection)
    finally:
        connection.close()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result.get("invalid_documents") or result.get("unsafe_files") else 0


if __name__ == "__main__":
    raise SystemExit(main())
