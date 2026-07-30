"""Verify every runtime Space_V writer embeds and reserves identity before publish."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app
import future_lesson_identity as identity


def main() -> None:
    pdf_source = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/08_pdf_vocab_scan.py").read_text(encoding="utf-8")
    mission_source = (ROOT / "FUTURE/server_parts/vocab_build_status/02_space_w_vocab_missions.py").read_text(encoding="utf-8")
    gui_source = (ROOT / "future_vocab_builder_gui.py").read_text(encoding="utf-8")
    builder_source = (ROOT / "future_lesson_builder_gui.py").read_text(encoding="utf-8")
    assert "write_generated_space_v_lesson(target_file, payload)" in pdf_source
    assert "write_generated_space_v_lesson(target, payload)" in mission_source
    assert pdf_source.index("write_generated_space_v_lesson(target_file, payload)") < pdf_source.index("prefetch_space_v_images_for_entries(new_entries)")
    assert mission_source.index("write_generated_space_v_lesson(target, payload)") < mission_source.index("prefetch_space_v_images_for_entries(new_entries)")
    assert gui_source.count("target.write_text(encode_future_manifest(") == 2
    assert builder_source.index("ensure_future_lesson_id(payload, output_path=output_path, space=space)") < builder_source.index("write_server_structure_asset(title, payload)")

    with tempfile.TemporaryDirectory(prefix="future-generated-space-v-") as temporary:
        root = Path(temporary) / "server data"
        root.mkdir(parents=True)
        registry = {"version": 1, "next_id": 1, "ids": {}}
        identity.SERVER_DATA_ROOT = root
        identity.SERVER_DATABASE_FILE = root / "server2.db"
        identity.LESSON_ID_REGISTRY_PATH = root / "_future_space_lesson_ids.json"
        identity.LESSON_ID_REGISTRY_CACHE = {"signature": None, "payload": None}
        identity.FILE_LESSON_ID_CACHE.clear()
        identity.lesson_id_registry_load = lambda: (registry, 1)
        identity.lesson_id_registry_write = lambda payload: 2

        target = root / "learner" / "Immediate Mission" / "Generated.Space_V"
        first = {"k": "ftv", "v": 1, "t": "Generated", "w": [{"w": "alpha"}]}
        first_id = app.write_generated_space_v_lesson(target, first)
        stored, _structure = app.load_future_lesson_document(target)
        assert identity.lesson_id_from_payload(stored) == first_id

        interrupted_target = root / "learner" / "Immediate Mission" / "Interrupted.Space_V"
        interrupted_payload = {"k": "ftv", "v": 1, "t": "Interrupted", "w": [{"w": "gamma"}]}
        reserved_before_crash = identity.reserve_lesson_id_in_database(interrupted_payload, interrupted_target, "Space_V")
        reserved_after_restart = identity.ensure_future_lesson_id(interrupted_payload, interrupted_target, "Space_V")
        assert reserved_after_restart == reserved_before_crash, "retry after reserve-before-publish must not allocate another ID"

        second = {"k": "ftv", "v": 1, "t": "Generated", "w": [{"w": "beta"}]}
        second_id = app.write_generated_space_v_lesson(target, second)
        assert second_id == first_id, "rebuilding the same generated lesson must retain its ID"
        stored, _structure = app.load_future_lesson_document(target)
        assert identity.lesson_id_from_payload(stored) == first_id

        connection = sqlite3.connect(identity.SERVER_DATABASE_FILE)
        try:
            assert connection.execute("SELECT COUNT(*) FROM lesson_files WHERE file_id=?", (first_id,)).fetchone()[0] == 1
            row = connection.execute(
                "SELECT file_id,status FROM lesson_file_replicas WHERE normalized_path=? COLLATE NOCASE",
                ("learner/Immediate Mission/Generated.Space_V",),
            ).fetchone()
            assert row == (first_id, "reserved")
        finally:
            connection.close()

    print("generated_space_v_identity=ok pdf_picture=true space_missions=true same_path_id_stable=true reserve_retry_idempotent=true sqlite_reserved=true")


if __name__ == "__main__":
    main()
