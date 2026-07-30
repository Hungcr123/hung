#!/usr/bin/env python3
"""Merge the newest QM City runtime state into PostgreSQL without stale overwrite."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app
from FUTURE.tools import migrate_qm_city_documents_to_postgres as source


TRAINING_NAME = "_future_qm_city_training.json"


def decode_payload(row: dict | None) -> dict:
    if not isinstance(row, dict):
        return {}
    try:
        payload = json.loads(bytes(row.get("content") or b"").decode(row.get("encoding") or "utf-8", errors="replace").lstrip("\ufeff"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def newest_text(left: object, right: object) -> str:
    left_text = app.clean(left)
    right_text = app.clean(right)
    return left_text if app.timestamp_to_epoch(left_text) > app.timestamp_to_epoch(right_text) else right_text


def merge_training_payload(sqlite_payload: dict, postgres_payload: dict) -> tuple[dict, dict]:
    sqlite_users = sqlite_payload.get("users") if isinstance(sqlite_payload.get("users"), dict) else {}
    postgres_users = postgres_payload.get("users") if isinstance(postgres_payload.get("users"), dict) else {}
    merged_users = {}
    choices = {"sqlite_newer": [], "postgres_newer_or_equal": [], "sqlite_only": [], "postgres_only": []}
    for username in sorted(set(sqlite_users) | set(postgres_users)):
        sqlite_row = sqlite_users.get(username) if isinstance(sqlite_users.get(username), dict) else None
        postgres_row = postgres_users.get(username) if isinstance(postgres_users.get(username), dict) else None
        if sqlite_row is None:
            merged_users[username] = dict(postgres_row or {})
            choices["postgres_only"].append(username)
            continue
        if postgres_row is None:
            merged_users[username] = dict(sqlite_row)
            choices["sqlite_only"].append(username)
            continue
        sqlite_epoch = app.timestamp_to_epoch(sqlite_row.get("updated_at") or sqlite_row.get("updatedAt"))
        postgres_epoch = app.timestamp_to_epoch(postgres_row.get("updated_at") or postgres_row.get("updatedAt"))
        if sqlite_epoch > postgres_epoch:
            merged_users[username] = dict(sqlite_row)
            choices["sqlite_newer"].append(username)
        else:
            merged_users[username] = dict(postgres_row)
            choices["postgres_newer_or_equal"].append(username)
    return {
        "version": 1,
        "updated_at": newest_text(sqlite_payload.get("updated_at"), postgres_payload.get("updated_at")) or app.utc_timestamp(),
        "users": merged_users,
    }, choices


def encoded_row(base_row: dict, payload: dict) -> dict:
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        **base_row,
        "content": content,
        "encoding": "utf-8",
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size": len(content),
        "file_mtime_ns": max(int(base_row.get("file_mtime_ns", 0) or 0), time.time_ns()),
        "updated_at_utc": app.utc_timestamp(),
    }


def build_plan() -> tuple[list[dict], dict]:
    sqlite_rows = {Path(row["path"]).name.lower(): row for row in source.sqlite_rows()}
    postgres_rows = {Path(row["path"]).name.lower(): row for row in source.pg_rows()}
    writes = []
    report = {"documents": {}, "training_choices": {}}
    for name in sorted(set(sqlite_rows) | set(postgres_rows)):
        sqlite_row = sqlite_rows.get(name)
        postgres_row = postgres_rows.get(name)
        if name == TRAINING_NAME:
            sqlite_payload = decode_payload(sqlite_row)
            postgres_payload = decode_payload(postgres_row)
            payload, choices = merge_training_payload(sqlite_payload, postgres_payload)
            report["training_choices"] = choices
            # Preserve the existing PostgreSQL bytes when only JSON formatting differs.
            if postgres_row is not None and payload == postgres_payload:
                desired = dict(postgres_row)
            else:
                base_row = dict(postgres_row or sqlite_row or {})
                desired = encoded_row(base_row, payload)
        elif postgres_row is not None:
            desired = dict(postgres_row)
        else:
            desired = dict(sqlite_row or {})
        changed = not postgres_row or bytes(desired.get("content") or b"") != bytes(postgres_row.get("content") or b"")
        report["documents"][name] = {
            "sqlite_present": sqlite_row is not None,
            "postgres_present": postgres_row is not None,
            "changed": changed,
            "desired_bytes": len(bytes(desired.get("content") or b"")),
        }
        if changed:
            writes.append(desired)
    report["write_count"] = len(writes)
    return writes, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", default="")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    writes, report = build_plan()
    report["applied"] = False
    if args.apply and writes:
        backup_path = Path(args.backup) if args.backup else Path(r"C:\Users\Admin\.codex\plans") / f"qm_city_postgres_before_merge_{time.strftime('%Y%m%d_%H%M%S')}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_rows = []
        for row in source.pg_rows():
            backup_rows.append(source.public_row(row) | {"content_base64": base64.b64encode(bytes(row.get("content") or b"")).decode("ascii")})
        backup_path.write_text(json.dumps({"rows": backup_rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        for row in writes:
            app.postgres_upsert_document_row(row)
        report["applied"] = True
        report["backup"] = str(backup_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
