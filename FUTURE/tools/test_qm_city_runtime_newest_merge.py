"""Verify QM City migration orders UTC, offset and legacy timestamps numerically."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.migrate_qm_city_runtime_newest_to_postgres import merge_training_payload


def main() -> int:
    sqlite_payload = {
        "updated_at": "2026-07-30T10:00:00+07:00",
        "users": {
            "sqlite_newer": {"updated_at": "2026-07-30T10:00:00+07:00", "value": "sqlite"},
            "equal": {"updated_at": "2026-07-30 10:00:00", "value": "sqlite"},
            "sqlite_only": {"updated_at": "2026-07-30T01:00:00Z", "value": "sqlite"},
        },
    }
    postgres_payload = {
        "updated_at": "2026-07-30T04:00:00Z",
        "users": {
            "sqlite_newer": {"updated_at": "2026-07-30T02:00:00Z", "value": "postgres"},
            "equal": {"updated_at": "2026-07-30T03:00:00Z", "value": "postgres"},
            "postgres_only": {"updated_at": "2026-07-30T04:00:00Z", "value": "postgres"},
        },
    }
    merged, choices = merge_training_payload(sqlite_payload, postgres_payload)
    assert merged["users"]["sqlite_newer"]["value"] == "sqlite"
    assert merged["users"]["equal"]["value"] == "postgres"
    assert merged["users"]["sqlite_only"]["value"] == "sqlite"
    assert merged["users"]["postgres_only"]["value"] == "postgres"
    assert choices["sqlite_newer"] == ["sqlite_newer"]
    print("qm_city_runtime_newest_merge=ok numeric_order=true equal_prefers_postgres=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
