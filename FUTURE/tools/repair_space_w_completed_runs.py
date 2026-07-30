"""Audit and repair inflated Space_W completedRuns from canonical completion events."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def clean(value: object) -> str:
    return str(value or "").strip()


def integer(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def completion_event_index(connection: sqlite3.Connection) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = defaultdict(lambda: {"runs": set(), "max_user_count": 0})
    for row in connection.execute(
        "SELECT username,event_key,event_json FROM append_events WHERE stream='learning' ORDER BY id"
    ):
        try:
            event = json.loads(row["event_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(event, dict) or clean(event.get("event")) != "lesson_complete":
            continue
        username = clean(row["username"] or event.get("user")).lower()
        lesson_id = clean(event.get("lesson_id") or event.get("file_id"))
        if not username or not lesson_id:
            continue
        run_id = clean(
            event.get("completion_run_id")
            or event.get("completionRunId")
            or event.get("event_key")
            or row["event_key"]
        )
        bucket = index[(username, lesson_id)]
        if run_id:
            bucket["runs"].add(run_id)
        bucket["max_user_count"] = max(bucket["max_user_count"], integer(event.get("user_count")))
    return index


def record_completed_runs(record: dict) -> int:
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else {}
    study = lesson_source.get("study") if isinstance(lesson_source.get("study"), dict) else {}
    progress = study.get("progress") if isinstance(study.get("progress"), dict) else {}
    return max(
        integer(record.get("completedRuns", record.get("completed_runs"))),
        integer(state.get("completedRuns", state.get("completed_runs"))),
        integer(study.get("mine")),
        integer(study.get("completedRuns", study.get("completed_runs"))),
        integer(progress.get("completedRuns", progress.get("completed_runs"))),
    )


def set_completed_runs(record: dict, count: int) -> dict:
    result = dict(record)
    result["completedRuns"] = count
    result["completed_runs"] = count
    state = dict(result.get("state")) if isinstance(result.get("state"), dict) else {}
    for key in ("completedRuns", "completed_runs"):
        if key in state:
            state[key] = count
    lesson_source = dict(state.get("lessonSource")) if isinstance(state.get("lessonSource"), dict) else {}
    study = dict(lesson_source.get("study")) if isinstance(lesson_source.get("study"), dict) else {}
    if study:
        study["mine"] = count
        for key in ("completedRuns", "completed_runs"):
            if key in study:
                study[key] = count
        progress = dict(study.get("progress")) if isinstance(study.get("progress"), dict) else {}
        for key in ("completedRuns", "completed_runs"):
            if key in progress:
                progress[key] = count
        if progress:
            study["progress"] = progress
        lesson_source["study"] = study
        state["lessonSource"] = lesson_source
    if state:
        result["state"] = state
    return result


def audit_space_w_files(root: Path) -> dict:
    report = {"files": 0, "invalid_json": 0, "missing_lesson_id": 0, "multiple_lesson_ids": 0}
    for path in root.rglob("*.Space_W"):
        report["files"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            report["invalid_json"] += 1
            continue
        ids: set[str] = set()

        def visit(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"lesson_id", "lessonId"} and clean(child):
                        ids.add(clean(child))
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(payload)
        if not ids:
            report["missing_lesson_id"] += 1
        elif len(ids) > 1:
            report["multiple_lesson_ids"] += 1
    return report


def run(db_path: Path, server_data: Path, apply: bool) -> dict:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    events = completion_event_index(connection)
    batch_id = f"space-w-runs-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    candidates = []
    for row in connection.execute(
        "SELECT rowid,* FROM lesson_progress WHERE space='Space_W' AND file_id<>'' ORDER BY username,file_id"
    ):
        try:
            record = json.loads(row["record_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        event_info = events.get((clean(row["username"]).lower(), clean(row["file_id"])))
        if not event_info:
            continue
        canonical_count = max(len(event_info["runs"]), integer(event_info["max_user_count"]))
        recorded_count = record_completed_runs(record)
        completion_run_id = clean(record.get("completionRunId") or record.get("completion_run_id"))
        if recorded_count <= canonical_count or not canonical_count:
            continue
        # High confidence requires the durable record to reference a canonical completion event.
        if completion_run_id and completion_run_id not in event_info["runs"]:
            continue
        candidates.append((row, record, recorded_count, canonical_count))

    if apply and candidates:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS canonical_migration_archive(
                migration_batch_id TEXT NOT NULL,
                source_primary_key TEXT NOT NULL,
                target_primary_key TEXT NOT NULL,
                full_original_payload TEXT NOT NULL,
                lesson_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                all_paths TEXT NOT NULL,
                revision INTEGER NOT NULL,
                server_timestamp TEXT NOT NULL,
                merge_reason TEXT NOT NULL,
                checksum TEXT NOT NULL,
                UNIQUE(migration_batch_id, source_primary_key)
            )"""
        )
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
        with connection:
            for row, record, old_count, new_count in candidates:
                original = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                primary = json.dumps(
                    {"username": row["username"], "space": row["space"], "progress_key": row["progress_key"]},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                connection.execute(
                    "INSERT INTO canonical_migration_archive VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        batch_id,
                        primary,
                        primary,
                        original,
                        row["file_id"],
                        row["file_id"],
                        json.dumps([row["path"]], ensure_ascii=False),
                        integer(row["server_revision"]),
                        now,
                        f"Space_W stage-2 run inflation {old_count}->{new_count}",
                        hashlib.sha256(original.encode("utf-8")).hexdigest(),
                    ),
                )
                repaired = json.dumps(set_completed_runs(record, new_count), ensure_ascii=False, separators=(",", ":"))
                connection.execute(
                    "UPDATE lesson_progress SET record_json=?,server_revision=server_revision+1 WHERE rowid=?",
                    (repaired, row["rowid"]),
                )
    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    connection.close()
    return {
        "database": str(db_path),
        "mode": "apply" if apply else "dry-run",
        "batch_id": batch_id,
        "space_w_files": audit_space_w_files(server_data),
        "event_identity_groups": len(events),
        "repair_candidates": len(candidates),
        "candidate_rows": [
            {
                "username": row["username"],
                "lesson_id": row["file_id"],
                "path": row["path"],
                "before": old_count,
                "after": new_count,
            }
            for row, _record, old_count, new_count in candidates
        ],
        "quick_check": quick_check,
        "foreign_key_errors": foreign_keys,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(r"C:\server data\server2.db"))
    parser.add_argument("--server-data", type=Path, default=Path(r"C:\server data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = run(args.db, args.server_data, args.apply)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
