"""Archive and remove Space_W completion events created before stage 2 finished."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

from repair_space_w_completed_runs import clean, integer, record_completed_runs, set_completed_runs


def run(db_path: Path, apply: bool) -> dict:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    events: dict[tuple[str, str], list[tuple[sqlite3.Row, dict]]] = {}
    for row in connection.execute(
        "SELECT id,stream,username,event_at_utc,event_key,event_json FROM append_events WHERE stream='learning'"
    ):
        try:
            event = json.loads(row["event_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(event, dict) or clean(event.get("event")) != "lesson_complete":
            continue
        lesson_id = clean(event.get("lesson_id") or event.get("file_id"))
        key = (clean(row["username"] or event.get("user")).lower(), lesson_id)
        if key[0] and key[1]:
            events.setdefault(key, []).append((row, event))

    candidates = []
    for progress_row in connection.execute(
        "SELECT rowid,* FROM lesson_progress WHERE space='Space_W' AND file_id<>''"
    ):
        try:
            record = json.loads(progress_row["record_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        active = bool(
            record.get("activeRun")
            or record.get("active_run")
            or state.get("activeRun")
            or state.get("active_run")
        )
        complete = bool(
            record.get("complete")
            or record.get("lessonComplete")
            or record.get("reviewFinished")
            or state.get("complete")
            or state.get("lessonComplete")
            or state.get("reviewFinished")
        )
        run_id = clean(record.get("runId") or record.get("run_id") or state.get("runId") or state.get("run_id"))
        if not active or complete or not run_id:
            continue
        lesson_events = events.get((clean(progress_row["username"]).lower(), clean(progress_row["file_id"])), [])
        false_events = [
            (row, event)
            for row, event in lesson_events
            if clean(event.get("completion_run_id") or event.get("completionRunId")) == run_id
        ]
        if not false_events:
            continue
        false_ids = {integer(row["id"]) for row, _event in false_events}
        remaining = [(row, event) for row, event in lesson_events if integer(row["id"]) not in false_ids]
        remaining_runs = {
            clean(event.get("completion_run_id") or event.get("completionRunId") or row["event_key"])
            for row, event in remaining
            if clean(event.get("completion_run_id") or event.get("completionRunId") or row["event_key"])
        }
        prior_count = max(
            len(remaining_runs),
            max((integer(event.get("user_count")) for _row, event in remaining), default=0),
            max((integer(event.get("user_count")) - 1 for _row, event in false_events), default=0),
        )
        candidates.append((progress_row, record, false_events, record_completed_runs(record), prior_count))

    batch_id = f"space-w-stage1-events-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
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
            for progress_row, record, false_events, old_count, new_count in candidates:
                original_progress = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                progress_key = f"lesson_progress:{progress_row['rowid']}"
                connection.execute(
                    "INSERT INTO canonical_migration_archive VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        batch_id,
                        progress_key,
                        progress_key,
                        original_progress,
                        progress_row["file_id"],
                        progress_row["file_id"],
                        json.dumps([progress_row["path"]], ensure_ascii=False),
                        integer(progress_row["server_revision"]),
                        now,
                        f"Space_W active stage-2 run had false completion event; runs {old_count}->{new_count}",
                        hashlib.sha256(original_progress.encode("utf-8")).hexdigest(),
                    ),
                )
                repaired = json.dumps(set_completed_runs(record, new_count), ensure_ascii=False, separators=(",", ":"))
                connection.execute(
                    "UPDATE lesson_progress SET record_json=?,server_revision=server_revision+1 WHERE rowid=?",
                    (repaired, progress_row["rowid"]),
                )
                for event_row, event in false_events:
                    original_event = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    event_key = f"append_events:{event_row['id']}"
                    connection.execute(
                        "INSERT INTO canonical_migration_archive VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            batch_id,
                            event_key,
                            progress_key,
                            original_event,
                            progress_row["file_id"],
                            progress_row["file_id"],
                            json.dumps([progress_row["path"]], ensure_ascii=False),
                            integer(progress_row["server_revision"]),
                            now,
                            "Space_W stage-1 completion event matched an active incomplete run",
                            hashlib.sha256(original_event.encode("utf-8")).hexdigest(),
                        ),
                    )
                    connection.execute("DELETE FROM append_events WHERE id=?", (event_row["id"],))

    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    connection.close()
    return {
        "database": str(db_path),
        "mode": "apply" if apply else "dry-run",
        "batch_id": batch_id,
        "repair_candidates": len(candidates),
        "false_event_count": sum(len(item[2]) for item in candidates),
        "rows": [
            {
                "username": row["username"],
                "lesson_id": row["file_id"],
                "path": row["path"],
                "run_id": clean(record.get("runId") or (record.get("state") or {}).get("runId")),
                "event_ids": [event_row["id"] for event_row, _event in false_events],
                "completed_runs_before": old_count,
                "completed_runs_after": new_count,
            }
            for row, record, false_events, old_count, new_count in candidates
        ],
        "quick_check": quick_check,
        "foreign_key_errors": foreign_keys,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(r"C:\server data\server2.db"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = run(args.db, args.apply)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
