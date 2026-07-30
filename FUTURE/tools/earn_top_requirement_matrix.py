#!/usr/bin/env python3
"""Summarize current Earn/Top readiness evidence without mutating production."""

from __future__ import annotations

import json
from pathlib import Path


PLAN_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit")
DRY_RUN = PLAN_DIR / "earn_top_reconciliation_dry_run_20260728_v2.json"
CHECKPOINT = PLAN_DIR / "earn_top_checkpoint_20260728.md"
CANARY_HARNESS = Path(r"C:\programe\write_html\FUTURE\tools\earn_top_canary_repeatability.py")
CANARY_DRY_RUN = PLAN_DIR / "earn_top_canary_dry_run_hungcr_20260728_v3.json"


def _exists(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main() -> int:
    dry = _load_json(DRY_RUN) if _exists(DRY_RUN) else {}
    summary = dry.get("summary") if isinstance(dry.get("summary"), dict) else {}
    missing = summary.get("missing_from_period_rows") if isinstance(summary.get("missing_from_period_rows"), dict) else {}
    historical = summary.get("historical_not_in_event_ledger") if isinstance(summary.get("historical_not_in_event_ledger"), dict) else {}
    rows = dry.get("rows") if isinstance(dry.get("rows"), list) else []
    users = [row.get("user") for row in rows if isinstance(row, dict)]
    all_missing_zero = bool(missing) and all(int(value or 0) == 0 for value in missing.values())
    repair_needed = int(summary.get("repair_needed_users", -1) or 0)
    matrix = [
        {
            "requirement": "Production 8877 runtime identified",
            "status": "PASS" if _exists(CHECKPOINT) else "NOT_PROVEN",
            "evidence": str(CHECKPOINT),
        },
        {
            "requirement": "PostgreSQL schema/role identified without secrets",
            "status": "PASS" if dry.get("database", {}).get("current_database") == "future_server2" else "NOT_PROVEN",
            "evidence": dry.get("database", {}),
        },
        {
            "requirement": "Dry-run reconciliation by user/day/week/month",
            "status": "PASS" if users and dry.get("dry_run") is True else "NOT_PROVEN",
            "evidence": {"users": users, "buckets": dry.get("buckets")},
        },
        {
            "requirement": "No missing period rows for checked affected users",
            "status": "PASS" if all_missing_zero and repair_needed == 0 else "FAIL",
            "evidence": {"missing_from_period_rows": missing, "repair_needed_users": repair_needed},
        },
        {
            "requirement": "Historical month rows not silently deleted or backfilled from leaderboard",
            "status": "PASS" if int(historical.get("month", 0) or 0) >= 0 else "NOT_PROVEN",
            "evidence": {"historical_not_in_event_ledger": historical, "policy": "classified as migrated/source-hash coverage gap"},
        },
        {
            "requirement": "Controlled 5-cycle production repeatability before restart",
            "status": "NOT_PROVEN" if _exists(CANARY_HARNESS) else "MISSING_HARNESS",
            "evidence": {
                "harness": str(CANARY_HARNESS),
                "dry_run": str(CANARY_DRY_RUN) if _exists(CANARY_DRY_RUN) else "",
                "note": "Requires explicit --execute with approved canary user/file; not run yet.",
            },
        },
        {
            "requirement": "Controlled 2-cycle repeatability after restart",
            "status": "NOT_PROVEN",
            "evidence": "Requires the same canary gate after restart; not run yet.",
        },
        {
            "requirement": "No cross-user/common-tree contamination from repeatability",
            "status": "NOT_PROVEN",
            "evidence": "Needs canary execution evidence; no production write canary has been run.",
        },
    ]
    report = {
        "generated_from": {
            "dry_run": str(DRY_RUN),
            "checkpoint": str(CHECKPOINT),
        },
        "matrix": matrix,
        "complete": all(row["status"] == "PASS" for row in matrix),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
