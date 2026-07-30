"""Regression for type-independent Space Task folder-group removal."""

from __future__ import annotations

import copy
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


SPACE_SUFFIX = {
    "Space_V": ".Space_V",
    "Space_W": ".Space_W",
    "Space_Q": ".Space_Q",
    "Space_L": ".Space_L",
    "Space_S": ".Space_S",
}


def task(space: str, path: str, index: int, folder: str = "") -> dict:
    row = {"id": f"task-{space.lower()}-{index}", "path": path, "space": space}
    if folder:
        row.update({"folder": folder, "space_task": True, "auto_task": True})
    return row


def main() -> int:
    originals = {
        "read": app.read_lesson_task_user_locked,
        "write": app.write_lesson_task_user_locked,
        "payload": app.space_task_payload_for_user,
        "validate": app.validate_username,
        "admin": app.is_admin_user,
    }
    record_box = {"value": {"tasks": [], "space_task": {}}}
    auto_box = {"tasks": []}
    writes = {"count": 0}

    def read_record(_username: str) -> dict:
        return copy.deepcopy(record_box["value"])

    def write_record(_username: str, record: dict) -> dict:
        writes["count"] += 1
        record_box["value"] = copy.deepcopy(record)
        return record

    app.read_lesson_task_user_locked = read_record
    app.write_lesson_task_user_locked = write_record
    app.space_task_payload_for_user = lambda *_args, **_kwargs: {"tasks": copy.deepcopy(auto_box["tasks"])}
    app.validate_username = lambda _username: (True, "")
    app.is_admin_user = lambda _username: False

    try:
        with tempfile.TemporaryDirectory(prefix="future-space-task-groups-") as temp:
            root = Path(temp)

            def create_file(relative: str) -> None:
                path = root / Path(relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")

            per_space = {}
            for space, suffix in SPACE_SUFFIX.items():
                group_a = f"common/{space}/Folder A"
                group_b = f"common/{space}/Folder B"
                rows = [task(space, f"{group_a}/a{index}{suffix}", index) for index in range(3)]
                rows.append(task(space, f"{group_b}/other{suffix}", 9))
                for row in rows:
                    create_file(row["path"])
                record_box["value"] = {"tasks": rows, "space_task": {}}
                auto_box["tasks"] = []
                writes["count"] = 0
                result = app.remove_space_task_group("codex_group", relative_path=rows[0]["path"], task_id=rows[0]["id"], actor_username="codex_group")
                remaining = record_box["value"]["tasks"]
                assert result["removed_count"] == 3 and len(remaining) == 1 and remaining[0]["path"].startswith(group_b)
                assert writes["count"] == 1
                assert all((root / Path(row["path"])).is_file() for row in rows)
                per_space[space] = result["removed_count"]

            group_a = "common/Mixed/Folder A"
            group_b = "common/Mixed/Folder B"
            mixed_a = [task(space, f"{group_a}/{space}{suffix}", index) for index, (space, suffix) in enumerate(SPACE_SUFFIX.items())]
            mixed_b = [task(space, f"{group_b}/{space}{suffix}", index + 20) for index, (space, suffix) in enumerate(SPACE_SUFFIX.items())]
            for row in [*mixed_a, *mixed_b]:
                create_file(row["path"])
            record_box["value"] = {"tasks": [*mixed_a, *mixed_b], "space_task": {}}
            writes["count"] = 0
            cross_result = app.remove_space_task_group("codex_group", relative_path=mixed_a[1]["path"], task_id=mixed_a[1]["id"], actor_username="codex_group")
            assert cross_result["removed_count"] == 5
            assert {row["path"] for row in record_box["value"]["tasks"]} == {row["path"] for row in mixed_b}
            assert writes["count"] == 1

            english = task("Space_V", "common/English/Unit 1/one.Space_V", 50)
            math = task("Space_V", "common/Math/Unit 1/two.Space_V", 51)
            record_box["value"] = {"tasks": [english, math], "space_task": {}}
            same_name_result = app.remove_space_task_group("codex_group", relative_path=english["path"], task_id=english["id"], actor_username="codex_group")
            assert same_name_result["removed_count"] == 1
            assert record_box["value"]["tasks"] == [math]

            standalone = task("Space_V", "common/root.Space_V", 60)
            other = task("Space_Q", "common/other.Space_Q", 61)
            record_box["value"] = {"tasks": [standalone, other], "space_task": {}}
            standalone_result = app.remove_space_task_group("codex_group", relative_path=standalone["path"], task_id=standalone["id"], actor_username="codex_group")
            assert standalone_result["removed_count"] == 1 and record_box["value"]["tasks"] == [other]
            assert not standalone_result["folder_backed"]

            auto_a = [task(space, f"{group_a}/auto-{space}{suffix}", index + 70, group_a) for index, (space, suffix) in enumerate(SPACE_SUFFIX.items())]
            auto_b = [task(space, f"{group_b}/auto-{space}{suffix}", index + 80, group_b) for index, (space, suffix) in enumerate(SPACE_SUFFIX.items())]
            for row in [*auto_a, *auto_b]:
                row.update(app.lesson_task_folder_group_metadata(row))
                create_file(row["path"])
            record_box["value"] = {
                "tasks": [],
                "space_task": {"preferred_folders": [group_a, group_b], "updated_rev": "rev-1", "assigned": {}},
            }
            auto_box["tasks"] = [*auto_a, *auto_b]
            writes["count"] = 0
            auto_result = app.remove_space_task_group(
                "codex_group",
                relative_path=auto_a[2]["path"],
                task_id=auto_a[2]["id"],
                folder_group_key=auto_a[2]["folder_group_key"],
                folder_path=group_a,
                actor_username="codex_group",
                base_revision="rev-1",
            )
            assert auto_result["removed_count"] == 5 and writes["count"] == 1
            assert record_box["value"]["space_task"]["preferred_folders"] == [group_b]
            assert {row["path"] for row in auto_result["space_tasks"]} == {row["path"] for row in auto_b}
            assert all((root / Path(row["path"])).is_file() for row in [*auto_a, *auto_b])

            bulk = [task("Space_V", f"common/Bulk/Folder {index // 3}/file-{index}.Space_V", index + 100) for index in range(300)]
            record_box["value"] = {"tasks": bulk, "space_task": {}}
            auto_box["tasks"] = []
            writes["count"] = 0
            cpu_started = time.process_time()
            bulk_result = app.remove_space_task_group("codex_group", relative_path=bulk[150]["path"], task_id=bulk[150]["id"], actor_username="codex_group")
            cpu_ms = (time.process_time() - cpu_started) * 1000.0
            assert bulk_result["removed_count"] == 3 and writes["count"] == 1 and cpu_ms < 250.0

            print(
                "space_task_folder_group_remove=ok "
                f"per_space={per_space} cross_type=5 auto=5 standalone=1 writes=1 cpu_ms={cpu_ms:.3f} files_preserved=true"
            )
    finally:
        app.read_lesson_task_user_locked = originals["read"]
        app.write_lesson_task_user_locked = originals["write"]
        app.space_task_payload_for_user = originals["payload"]
        app.validate_username = originals["validate"]
        app.is_admin_user = originals["admin"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
