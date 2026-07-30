"""Reconcile portable Space lifetime completion without changing active-run progress."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


DB_PATH = Path(r"C:\server data\server2.db")
BOARD_PATH = Path(r"C:\server data\space_leaderboard_activity.json")
PORTABLE_SPACES = {"Space_V", "Space_W", "Space_Q", "Space_P", "Space_L", "Space_S"}
BOARD_SPACES = {
    "Space_W": "space_w",
    "Space_Q": "space_q",
    "Space_P": "space_p",
    "Space_L": "space_l",
    "Space_S": "space_s",
}
MARKER_KEY = "portable_space_completion_consistency_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def clean(value: object = "") -> str:
    return " ".join(str(value or "").strip().split())


def clean_path(value: object = "") -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def server_is_listening() -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(0.15)
    try:
        return probe.connect_ex(("127.0.0.1", 8877)) == 0
    finally:
        probe.close()


def json_record(raw: object) -> dict:
    try:
        value = json.loads(str(raw or "{}"))
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}


def completed_at_from_record(record: dict) -> str:
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    return clean(
        record.get("completedAt")
        or record.get("completed_at")
        or state.get("completedAt")
        or state.get("completed_at")
    )


def leaderboard_points(space: str, record: dict, fallback: int) -> int:
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    if space == "Space_Q":
        return max(0, app.space_w_int(state.get("questionTotal", state.get("totalQuestions", fallback)), 0))
    if space in {"Space_P", "Space_L", "Space_S"}:
        return max(0, app.space_w_int(
            state.get("totalSegments", state.get("segmentTotal", state.get("totalTokens", state.get("tokenTotal", fallback)))),
            0,
        ))
    return max(0, app.space_w_int(record.get("nodeCount", state.get("nodeCount", fallback)), 0))


def completion_key(username: str, board_type: str, identity: str) -> str:
    return hashlib.sha256(f"{username.lower()}|{board_type}|{identity}".encode("utf-8", errors="ignore")).hexdigest()[:32]


def make_backup(connection: sqlite3.Connection, root: Path) -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = root / f"{stamp}_portable_space_completion_reconcile"
    target.mkdir(parents=True, exist_ok=False)
    backup_db = target / "server2_before.db"
    backup_connection = sqlite3.connect(str(backup_db))
    try:
        connection.backup(backup_connection)
    finally:
        backup_connection.close()
    if BOARD_PATH.is_file():
        shutil.copy2(BOARD_PATH, target / BOARD_PATH.name)
    files = []
    for item in sorted(target.iterdir(), key=lambda path: path.name.lower()):
        if not item.is_file():
            continue
        digest = hashlib.sha256(item.read_bytes()).hexdigest().upper()
        files.append({"name": item.name, "size": item.stat().st_size, "sha256": digest})
    manifest = {"created_at_utc": utc_now(), "source_database": str(DB_PATH), "files": files}
    manifest_path = target / "sha256_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "path": str(target),
        "manifest": str(manifest_path),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper(),
    }


def load_aliases(connection: sqlite3.Connection) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for file_id, path in connection.execute(
        "SELECT file_id,normalized_path FROM lesson_file_aliases WHERE active=1"
    ):
        canonical_id = clean(file_id)
        normalized_path = clean_path(path).lower()
        if canonical_id and normalized_path:
            aliases.setdefault(canonical_id, set()).add(normalized_path)
    return aliases


def reconcile(apply: bool, backup_root: Path, leaderboard_recent_hours: float) -> dict:
    if apply and server_is_listening():
        raise RuntimeError("Server 2 must be stopped before --apply so RAM cannot overwrite reconciled SQLite/documents.")
    connection = sqlite3.connect(str(DB_PATH), timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA foreign_keys=ON")
    before_status = {
        "journal_mode": clean(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
        "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
        "quick_check": clean(connection.execute("PRAGMA quick_check").fetchone()[0]).lower(),
        "foreign_keys": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
    }
    aliases = load_aliases(connection)
    rows = list(connection.execute(
        "SELECT username,space,progress_key,path,file_id,node_count,learned_count,complete,server_revision,updated_at_utc,record_json "
        "FROM lesson_progress WHERE space IN ('Space_V','Space_W','Space_Q','Space_P','Space_L','Space_S') "
        "ORDER BY username,space,progress_key"
    ))
    actions = []
    unsafe_complete = []
    users = set()
    for row in rows:
        record = json_record(row["record_json"])
        normalized, summary = app.server_database_canonicalize_progress_completion(record, row["space"])
        expected_complete = 1 if summary.get("lifetime_complete") else 0
        expected_learned = max(0, app.space_w_int(summary.get("learned_count", row["learned_count"]), 0))
        if int(row["complete"] or 0) == 1 and not expected_complete:
            unsafe_complete.append({
                "username": row["username"], "space": row["space"], "progress_key": row["progress_key"],
            })
            continue
        normalized_json = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), default=str)
        record_changed = normalized_json != json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str)
        column_changed = int(row["complete"] or 0) != expected_complete or int(row["learned_count"] or 0) != expected_learned
        if not record_changed and not column_changed:
            continue
        action = {
            "username": clean(row["username"]), "space": clean(row["space"]), "progress_key": clean(row["progress_key"]),
            "path": clean_path(row["path"]), "file_id": clean(row["file_id"]),
            "complete_before": int(row["complete"] or 0), "complete_after": expected_complete,
            "learned_before": int(row["learned_count"] or 0), "learned_after": expected_learned,
            "server_revision_before": int(row["server_revision"] or 0),
            "record": normalized, "summary": summary, "completed_at": completed_at_from_record(normalized),
            "points": leaderboard_points(row["space"], normalized, int(row["node_count"] or 0)),
        }
        actions.append(action)
        users.add(action["username"])

    board_state = app.load_space_leaderboard_activity_state()
    board_state = app.clone_space_leaderboard_activity_state(board_state)
    board_actions = []
    board_skipped_missing = []
    now_epoch = datetime.now(timezone.utc).timestamp()
    current_buckets = {scope: app.vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    board_candidates = {}
    for row in rows:
        record = json_record(row["record_json"])
        normalized, summary = app.server_database_canonicalize_progress_completion(record, row["space"])
        lesson_id = clean(row["file_id"] or normalized.get("lesson_id") or normalized.get("file_id"))
        completed_at = completed_at_from_record(normalized)
        if not summary.get("lifetime_complete") or not lesson_id.lower().startswith("ftg-lesson-") or not completed_at:
            continue
        candidate = {
            "username": clean(row["username"]), "space": clean(row["space"]), "progress_key": clean(row["progress_key"]),
            "path": clean_path(row["path"]), "file_id": lesson_id, "record": normalized,
            "completed_at": completed_at, "points": leaderboard_points(row["space"], normalized, int(row["node_count"] or 0)),
        }
        candidate_key = f"{candidate['username'].lower()}|{candidate['space']}|{lesson_id.lower()}"
        previous = board_candidates.get(candidate_key)
        if previous is None or app.timestamp_to_epoch(candidate["completed_at"]) >= app.timestamp_to_epoch(previous["completed_at"]):
            board_candidates[candidate_key] = candidate
    for action in board_candidates.values():
        board_type = BOARD_SPACES.get(action["space"], "")
        lesson_id = action["file_id"]
        completed_at = action["completed_at"]
        points = action["points"]
        if not board_type or not lesson_id.lower().startswith("ftg-lesson-") or not completed_at or points <= 0:
            continue
        event_epoch = app.timestamp_to_epoch(completed_at)
        if not event_epoch:
            continue
        path = action["path"]
        valid_paths = set(aliases.get(lesson_id, set()))
        if path:
            valid_paths.add(path.lower())
        boards = board_state.setdefault("boards", {})
        board = boards.setdefault(board_type, {"users": {}, "updated_at": ""})
        board_users = board.setdefault("users", {})
        user_row = app._clean_space_leaderboard_user_row(board_users.get(action["username"], {}))
        completed = user_row.setdefault("completed", {})
        canonical_key = completion_key(action["username"], board_type, f"id:{lesson_id.lower()}")
        matching_keys = []
        for key, entry in completed.items():
            if not isinstance(entry, dict):
                continue
            entry_id = clean(entry.get("lesson_id"))
            entry_path = clean_path(entry.get("path")).lower()
            if entry_id.lower() == lesson_id.lower() or (entry_path and entry_path in valid_paths):
                matching_keys.append(key)
        if matching_keys:
            source_key = canonical_key if canonical_key in matching_keys else matching_keys[0]
            entry = completed[source_key]
            changed = source_key != canonical_key or clean(entry.get("lesson_id")) != lesson_id
            if source_key != canonical_key:
                completed.pop(source_key, None)
                completed[canonical_key] = entry
            entry["lesson_id"] = lesson_id
            if changed:
                board_actions.append({**{key: action[key] for key in ("username", "space", "progress_key", "file_id", "path")}, "action": "canonicalize_existing"})
            board_users[action["username"]] = user_row
            continue
        age_seconds = now_epoch - float(event_epoch)
        if age_seconds < -300 or age_seconds > max(0.0, leaderboard_recent_hours) * 3600.0:
            board_skipped_missing.append({
                **{key: action[key] for key in ("username", "space", "progress_key", "file_id", "path")},
                "completed_at": completed_at, "reason": "outside_conservative_recent_window",
            })
            continue
        event_buckets = {scope: app.vocab_period_bucket(scope, event_epoch) for scope in ("day", "week", "month")}
        credited = dict(event_buckets)
        completed[canonical_key] = {
            "lesson_id": lesson_id, "path": path, "points": points,
            "completed_at": completed_at, "last_completed_at": completed_at,
            "title": clean(action["record"].get("title"))[:180], "credited_buckets": credited,
        }
        user_row["total_points"] = max(0, app.space_w_int(user_row.get("total_points", 0), 0)) + points
        for scope, bucket in event_buckets.items():
            if bucket != current_buckets[scope]:
                continue
            scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
            if clean(scope_row.get("bucket")) != bucket:
                scope_row = {"bucket": bucket, "points": 0, "updated_at": ""}
            scope_row["points"] = max(0, app.space_w_int(scope_row.get("points", 0), 0)) + points
            scope_row["updated_at"] = utc_now()
            user_row[scope] = scope_row
        user_row["updated_at"] = utc_now()
        board_users[action["username"]] = user_row
        board["updated_at"] = utc_now()
        board_actions.append({**{key: action[key] for key in ("username", "space", "progress_key", "file_id", "path")}, "action": "add_missing", "points": points, "completed_at": completed_at})

    backup = {}
    if apply:
        backup = make_backup(connection, backup_root)
        connection.execute("BEGIN IMMEDIATE")
        for action in actions:
            record = dict(action["record"])
            next_revision = action["server_revision_before"] + 1
            record["_serverRevision"] = next_revision
            record["_completionNormalizationVersion"] = 1
            connection.execute(
                "UPDATE lesson_progress SET learned_count=?,complete=?,server_revision=?,record_json=? "
                "WHERE username=? AND space=? AND progress_key=? AND server_revision=?",
                (
                    action["learned_after"], action["complete_after"], next_revision,
                    json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str),
                    action["username"], action["space"], action["progress_key"], action["server_revision_before"],
                ),
            )
        connection.execute(
            "INSERT INTO database_meta(key,value,updated_at_utc) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at_utc=excluded.updated_at_utc",
            (MARKER_KEY, json.dumps({"version": 1, "rows": len(actions), "users": len(users)}, separators=(",", ":")), utc_now()),
        )
        connection.commit()
        if board_actions:
            app.write_space_leaderboard_activity_state(board_state)
            app.flush_server_database_writer(force=True)

    after_status = {
        "quick_check": clean(connection.execute("PRAGMA quick_check").fetchone()[0]).lower(),
        "foreign_keys": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
    }
    connection.close()
    return {
        "ok": not unsafe_complete and before_status["quick_check"] == "ok" and after_status["quick_check"] == "ok",
        "mode": "apply" if apply else "dry-run", "scanned": len(rows), "actionable": len(actions),
        "users": len(users), "by_space": {space: sum(1 for row in actions if row["space"] == space) for space in sorted(PORTABLE_SPACES)},
        "unsafe_complete": unsafe_complete, "leaderboard_actions": board_actions,
        "leaderboard_skipped_missing": board_skipped_missing,
        "before_status": before_status, "after_status": after_status, "backup": backup,
        "actions": [{key: row[key] for key in ("username", "space", "progress_key", "file_id", "path", "complete_before", "complete_after", "learned_before", "learned_after", "completed_at", "points")} for row in actions],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-root", default=r"E:\FutureServer2LegacyBackup")
    parser.add_argument("--leaderboard-recent-hours", type=float, default=12.0)
    parser.add_argument("--report", default="")
    args = parser.parse_args()
    report = reconcile(args.apply, Path(args.backup_root), args.leaderboard_recent_hours)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("ok", "mode", "scanned", "actionable", "users", "by_space", "unsafe_complete", "before_status", "after_status", "backup")}, ensure_ascii=False, indent=2))
    print(
        f"leaderboard_actions={len(report['leaderboard_actions'])} "
        f"leaderboard_skipped_missing={len(report['leaderboard_skipped_missing'])} report={args.report or '-'}"
    )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
