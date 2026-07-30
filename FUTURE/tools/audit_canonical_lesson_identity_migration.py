"""Read-only canonical lesson-ID migration inventory and mapping dry-run."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def norm_path(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or "").replace("\\", "/").strip("/")).casefold()


def clean_id(value: object) -> str:
    return str(value or "").strip()


def json_object(value: object) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except Exception:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


class DryRun:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.active = {
            norm_path(row["normalized_path"]): clean_id(row["file_id"])
            for row in self.connection.execute(
                "SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1"
            )
        }
        self.inactive = {
            norm_path(row["normalized_path"]): clean_id(row["file_id"])
            for row in self.connection.execute(
                "SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=0"
            )
        }
        self.links = [
            (norm_path(row["link_path"]), norm_path(row["target_path"]))
            for row in self.connection.execute(
                "SELECT link_path,target_path FROM lesson_folder_links WHERE status IN ('active','migrated')"
            )
        ]
        self.samples: dict[str, list[dict]] = collections.defaultdict(list)
        self.counts: collections.Counter[str] = collections.Counter()

    def sample(self, key: str, value: dict) -> None:
        if len(self.samples[key]) < 5:
            self.samples[key].append(value)

    def resolve(self, path: object) -> tuple[str, str]:
        raw = norm_path(path)
        if not raw:
            return "unresolved", ""
        if raw in self.active:
            return "high_alias", self.active[raw]
        if raw in self.inactive:
            return "collision", self.inactive[raw]
        parts = raw.split("/")
        for link_root, target_root in self.links:
            link_parts = link_root.split("/")
            if raw != link_root and not raw.startswith(link_root + "/"):
                continue
            mapped = "/".join([target_root, *parts[len(link_parts):]])
            if mapped in self.active:
                return "high_folder_link", self.active[mapped]
            if mapped in self.inactive:
                return "collision", self.inactive[mapped]
        return "unresolved", ""

    def classify_paths(self, paths: list[object]) -> tuple[str, set[str]]:
        results = [self.resolve(path) for path in paths if norm_path(path)]
        ids = {file_id for status, file_id in results if file_id}
        statuses = {status for status, _ in results}
        if len(ids) > 1:
            return "ambiguous", ids
        if len(ids) == 1:
            if "collision" in statuses:
                return "collision", ids
            return "high", ids
        if "collision" in statuses:
            return "collision", ids
        return "unresolved", ids

    def add(self, category: str, status: str, sample: dict) -> None:
        self.counts[f"{category}_{status}"] += 1
        self.sample(f"{category}_{status}", sample)

    def run(self) -> dict:
        progress_rows = list(self.connection.execute("SELECT rowid,* FROM lesson_progress"))
        stable_groups = collections.Counter(
            (row["username"], row["space"], row["file_id"])
            for row in progress_rows
            if clean_id(row["file_id"])
        )
        for row in progress_rows:
            if clean_id(row["file_id"]):
                continue
            record = json_object(row["record_json"])
            state = record.get("state") if isinstance(record.get("state"), dict) else {}
            status, ids = self.classify_paths([
                row["path"], record.get("path"), record.get("legacy_path"),
                state.get("path"), state.get("effective_path"), state.get("link_target"),
            ])
            self.add("progress", status, {
                "rowid": row["rowid"], "username": row["username"], "space": row["space"],
                "path": row["path"], "legacy_identity": row["identity"], "candidate_file_ids": sorted(ids),
            })

        for row in self.connection.execute("SELECT rowid,* FROM lesson_time WHERE file_id='' OR file_id IS NULL"):
            status, file_id = self.resolve(row["path"])
            self.add("lesson_time", status, {"rowid": row["rowid"], "path": row["path"], "candidate_file_id": file_id})

        for row in self.connection.execute(
            "SELECT rowid,username,lesson_key,file_id FROM lesson_time_credit_state WHERE file_id='' OR file_id IS NULL"
        ):
            ids = {
                clean_id(item[0])
                for item in self.connection.execute(
                    "SELECT file_id FROM lesson_time WHERE username=? AND lesson_key=? AND file_id<>''",
                    (row["username"], row["lesson_key"]),
                )
                if clean_id(item[0])
            }
            status = "high" if len(ids) == 1 else ("ambiguous" if len(ids) > 1 else "unresolved")
            self.add("lesson_time_credit", status, {"rowid": row["rowid"], "lesson_key": row["lesson_key"], "candidate_file_ids": sorted(ids)})

        for row in self.connection.execute("SELECT rowid,username,path,identity FROM pdf_drawings WHERE file_id='' OR file_id IS NULL"):
            status, file_id = self.resolve(row["path"])
            self.add("drawing", status, {"rowid": row["rowid"], "path": row["path"], "identity": row["identity"], "candidate_file_id": file_id})

        for row in self.connection.execute("SELECT id,event_json FROM append_events WHERE stream='learning'"):
            event = json_object(row["event_json"])
            status_text = str(event.get("status") or event.get("event") or "").casefold()
            completion_like = "lesson_complete" in status_text or status_text == "final"
            if not completion_like or clean_id(event.get("lesson_id") or event.get("file_id")):
                continue
            paths = [
                event.get("effective_path"), event.get("path"), event.get("display_path"),
                event.get("source_path"), event.get("linked_path"), event.get("link_path"),
            ]
            status, ids = self.classify_paths(paths)
            self.add("completion_event", status, {
                "event_id": row["id"], "paths": [path for path in paths if norm_path(path)],
                "candidate_file_ids": sorted(ids),
            })

        for row in self.connection.execute("SELECT username,record_json FROM lesson_task_state"):
            payload = json_object(row["record_json"])
            for bucket in ("tasks", "space_tasks"):
                items = payload.get(bucket) if isinstance(payload.get(bucket), list) else []
                for item in items:
                    if not isinstance(item, dict) or clean_id(item.get("lesson_id") or item.get("file_id")):
                        continue
                    path = item.get("effective_path") or item.get("path") or item.get("source_path")
                    status, file_id = self.resolve(path)
                    self.add("task", status, {"username": row["username"], "bucket": bucket, "task_id": item.get("id"), "path": path, "candidate_file_id": file_id})

        return {
            "read_only": True,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "alias_counts": {"active": len(self.active), "inactive": len(self.inactive), "folder_links": len(self.links)},
            "inventory": {
                "progress_rows": len(progress_rows),
                "progress_missing_file_id": sum(not clean_id(row["file_id"]) for row in progress_rows),
                "progress_stable_id_rows": sum(clean_id(row["file_id"]).casefold().startswith("ftg-lesson-") for row in progress_rows),
                "progress_duplicate_stable_groups": sum(value > 1 for value in stable_groups.values()),
                "lesson_time_rows": self.connection.execute("SELECT COUNT(*) FROM lesson_time").fetchone()[0],
                "lesson_time_missing_file_id": self.connection.execute("SELECT COUNT(*) FROM lesson_time WHERE file_id='' OR file_id IS NULL").fetchone()[0],
                "lesson_time_credit_rows": self.connection.execute("SELECT COUNT(*) FROM lesson_time_credit_state").fetchone()[0],
                "drawing_rows": self.connection.execute("SELECT COUNT(*) FROM pdf_drawings").fetchone()[0],
                "drawing_missing_file_id": self.connection.execute("SELECT COUNT(*) FROM pdf_drawings WHERE file_id='' OR file_id IS NULL").fetchone()[0],
                "vault_entries": self.connection.execute("SELECT COUNT(*) FROM vault_entries").fetchone()[0],
            },
            "mapping_counts": dict(self.counts),
            "samples": dict(self.samples),
            "migration_authorized": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=r"C:\server data\server2.db")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    connection = sqlite3.connect(f"file:{Path(args.db).as_posix()}?mode=ro", uri=True)
    try:
        report = DryRun(connection).run()
    finally:
        connection.close()
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    report["report_sha256"] = hashlib.sha256(encoded).hexdigest()
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
