"""Focused regression for collision-safe Space lesson ID migration."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import future_lesson_identity as identity_runtime
from future_lesson_identity import generate_future_lesson_id, lesson_id_from_payload
from FUTURE.tools import assign_space_lesson_ids as assigner
from FUTURE.tools.assign_space_lesson_ids import encode_payload, load_payload_from_text, read_text
from FUTURE.tools import migrate_space_lesson_id_collisions as migration


def write_space(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encode_payload(payload) + "\n", encoding="utf-8")


def read_id(path: Path) -> str:
    payload, _mode, _structure = load_payload_from_text(read_text(path))
    return lesson_id_from_payload(payload)


def main() -> int:
    first = generate_future_lesson_id()
    second = generate_future_lesson_id({first})
    assert first != second
    assert first.startswith("ftg-lesson-") and second.startswith("ftg-lesson-")

    with tempfile.TemporaryDirectory(prefix="future-space-id-") as temporary:
        base = Path(temporary)
        root = base / "server data"
        common = root / "common"
        old_id = "ftg-lesson-000000111"
        write_space(common / "A.Space_V", {"lesson_id": old_id, "words": [{"word": "alpha"}]})
        write_space(common / "A replica.Space_V", {"lesson_id": old_id, "words": [{"word": "alpha"}]})
        write_space(common / "B.Space_V", {"lesson_id": old_id, "words": [{"word": "beta"}]})
        write_space(common / "Independent 1.Space_V", {"lesson_id": "independent-one", "words": [{"word": "same"}]})
        write_space(common / "Independent 2.Space_V", {"lesson_id": "independent-two", "words": [{"word": "same"}]})
        write_space(common / "Missing.Space_V", {"words": [{"word": "missing"}]})

        backup = base / "backup"
        for source in common.glob("*.Space_V"):
            destination = backup / "wrappers" / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())

        scan = migration.scan_space_identities(root)
        summary = migration.dry_run_summary(scan)
        assert summary["divergent_collision_groups"] == 1
        assert summary["planned_reassigned_files"] == 1
        assert summary["missing_ids"] == 1
        assert summary["planned_total_writes"] == 2

        registry = {"version": 1, "next_id": 1, "ids": {}}
        written = []
        original_load = migration.registry_load
        original_write = migration.registry_write
        migration.registry_load = lambda: registry
        migration.registry_write = lambda payload: written.append(json.loads(json.dumps(payload)))
        try:
            ledger = base / "ledger.json"
            result = migration.apply_ledger(root, backup, ledger, scan)
            assert result["changed"] == 2
            assert written

            a_id = read_id(common / "A.Space_V")
            replica_id = read_id(common / "A replica.Space_V")
            b_id = read_id(common / "B.Space_V")
            missing_id = read_id(common / "Missing.Space_V")
            assert a_id == old_id and replica_id == old_id
            assert b_id not in {"", old_id}
            assert missing_id not in {"", old_id, b_id}
            assert read_id(common / "Independent 1.Space_V") == "independent-one"
            assert read_id(common / "Independent 2.Space_V") == "independent-two"

            second_scan = migration.scan_space_identities(root)
            second_result = migration.apply_ledger(root, backup, ledger, second_scan)
            assert second_result["changed"] == 0
            assert read_id(common / "B.Space_V") == b_id
            assert read_id(common / "Missing.Space_V") == missing_id
        finally:
            migration.registry_load = original_load
            migration.registry_write = original_write

    with tempfile.TemporaryDirectory(prefix="future-space-assign-") as temporary:
        root = Path(temporary) / "server data"
        write_space(root / "common" / "Same 1.Space_V", {"words": [{"word": "same"}]})
        write_space(root / "common" / "Same 2.Space_V", {"words": [{"word": "same"}]})
        registry = {"version": 1, "next_id": 1, "ids": {}}
        original_load = assigner.registry_load
        original_write = assigner.registry_write
        assigner.registry_load = lambda: registry
        assigner.registry_write = lambda _payload: None
        try:
            result = assigner.assign_ids(root, dry_run=False)
        finally:
            assigner.registry_load = original_load
            assigner.registry_write = original_write
        assert result["missing_assigned"] == 2
        assert read_id(root / "common" / "Same 1.Space_V") != read_id(root / "common" / "Same 2.Space_V")

    with tempfile.TemporaryDirectory(prefix="future-space-builder-db-") as temporary:
        base = Path(temporary)
        database = base / "server2.db"
        registry = {"version": 1, "next_id": 1, "ids": {}}
        original_database = identity_runtime.SERVER_DATABASE_FILE
        original_read = identity_runtime._read_registry_unlocked
        original_write = identity_runtime._write_registry_unlocked
        identity_runtime.SERVER_DATABASE_FILE = database
        identity_runtime._read_registry_unlocked = lambda: registry
        identity_runtime._write_registry_unlocked = lambda _payload: None
        try:
            first_payload = {"title": "Builder", "words": [{"word": "alpha"}]}
            first_id = identity_runtime.ensure_future_lesson_id(first_payload, base / "A.Space_V", "Space_V")
            replica_payload = {"lesson_id": first_id, "title": "Builder", "words": [{"word": "alpha"}]}
            replica_id = identity_runtime.ensure_future_lesson_id(replica_payload, base / "moved" / "A.Space_V", "Space_V")
            collision_payload = {"lesson_id": first_id, "title": "Other", "words": [{"word": "beta"}]}
            collision_id = identity_runtime.ensure_future_lesson_id(collision_payload, base / "B.Space_V", "Space_V")
            assert replica_id == first_id
            assert collision_id != first_id
            connection = sqlite3.connect(database)
            try:
                assert connection.execute("SELECT COUNT(*) FROM lesson_files").fetchone()[0] == 2
                assert connection.execute("SELECT COUNT(*) FROM lesson_file_replicas").fetchone()[0] == 3
            finally:
                connection.close()
        finally:
            identity_runtime.SERVER_DATABASE_FILE = original_database
            identity_runtime._read_registry_unlocked = original_read
            identity_runtime._write_registry_unlocked = original_write

    print("space_lesson_id_migration=ok random_ids=true builder_db_reserve=true move_copy=true builder_collision_fork=true idempotent=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
