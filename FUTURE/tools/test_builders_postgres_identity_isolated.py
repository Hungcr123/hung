#!/usr/bin/env python3
"""Fresh-snapshot PostgreSQL gate for shared Space builder identity/finalization."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
from pathlib import Path

import psycopg
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE.tools import test_lesson_complete_isolated_harness as isolated  # noqa: E402

isolated.RUN_ROOT = ROOT / "programe_cache" / "builders_postgres_identity_55432"
isolated.PG_ROOT = isolated.RUN_ROOT / "postgres"
isolated.PG_LOG = isolated.RUN_ROOT / "postgres.log"
isolated.TEST_DATABASE = "future_server2_builder_copy"
isolated.PG_DSN = f"postgresql://future_server2_app@127.0.0.1:{isolated.PG_PORT}/{isolated.TEST_DATABASE}"


SPACES = {
    "Space_V": {"k": "ftv", "kind": "future_vocab_payload", "words": [{"word": "alpha", "meaning": "a"}]},
    "Space_Q": {"k": "ftq", "kind": "future_question_payload", "nodes": [{"id": "q1", "root": "Question"}]},
    "Space_W": {"k": "ftw", "kind": "future_lesson_payload", "nodes": [{"id": "w1", "text": "Write one"}]},
    "Space_P": {"k": "ftp", "kind": "future_paragraph_payload", "nodes": [{"id": "p1", "children": [{"text": "One"}]}]},
    "Space_L": {"k": "ftp", "kind": "future_paragraph_payload", "space_mode": "space_l", "nodes": [{"id": "l1", "children": [{"text": "Listen"}]}]},
    "Space_S": {"k": "ftp", "kind": "future_paragraph_payload", "space_mode": "space_s", "nodes": [{"id": "s1", "children": [{"text": "Speak"}]}]},
    "Space_B": {"k": "ftv", "kind": "future_vocab_payload", "words": [{"word": "static", "meaning": "b"}]},
}


def configure_environment() -> Path:
    server_data = isolated.RUN_ROOT / "builder-server-data"
    server_data.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "FUTURE_PG_DSN": isolated.PG_DSN,
        "FUTURE_POSTGRES_ONLY": "1",
        "FUTURE_BUILDER_IDENTITY_BACKEND": "postgres",
        "FUTURE_SERVER_DATA_ROOT": str(server_data),
    })
    for domain in isolated.POSTGRES_DOMAINS:
        os.environ[f"FUTURE_DB_{domain}_BACKEND"] = "postgres"
    return server_data


def query_identity(path: str, lesson_id: str) -> dict:
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT canonical_fingerprint,status FROM future_server2.lesson_files WHERE file_id=%s",
            (lesson_id,),
        )
        lesson = cursor.fetchone()
        cursor.execute(
            "SELECT file_id,fingerprint,status FROM future_server2.lesson_file_replicas WHERE lower(normalized_path)=lower(%s)",
            (path,),
        )
        replica = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM future_server2.registry_documents WHERE key='lesson_ids'")
        registry = int(cursor.fetchone()[0] or 0)
    return {"lesson": lesson, "replica": replica, "registry": registry}


def main() -> int:
    if isolated.RUN_ROOT.exists():
        shutil.rmtree(isolated.RUN_ROOT)
    isolated.start_postgres()
    dump_path = None
    try:
        dump_path = isolated.sync_production_database_snapshot()
        server_data = configure_environment()
        identity = importlib.import_module("future_lesson_identity")
        builder = importlib.import_module("future_lesson_builder_gui")
        structure_store = importlib.import_module("future_postgres_structure_asset_store")
        assert identity.builder_identity_uses_postgres()
        callsites = {
            "Space_V": (ROOT / "future_vocab_builder_gui.py", 'encode_future_manifest(payload, batch_title, target, "Space_V")'),
            "Space_Q": (ROOT / "future_question_builder_gui.py", 'encode_future_manifest(payload, self.title, self.output_path, "Space_Q")'),
            "Space_W": (ROOT / "future_lesson_builder_gui.py", 'encode_future_manifest(payload, self.lesson_title, self.output_path, "Space_W")'),
            "Space_P/L/S": (ROOT / "future_paragraph_builder_gui.py", "encode_future_manifest(self.payload"),
        }
        for source_path, marker in callsites.values():
            assert marker in source_path.read_text(encoding="utf-8")

        results = {}
        for space, seed in SPACES.items():
            print(f"checking={space}", flush=True)
            suffix = space.replace("Space_", "")
            output = server_data / "common" / f"codex-builder-{suffix}.Space_{suffix}"
            relative = output.resolve().relative_to(server_data.resolve()).as_posix().lower()
            payload = {**seed, "title": f"Builder {space}", "version": 1}
            first = json.loads(builder.encode_future_manifest(payload, payload["title"], output, space))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(first, ensure_ascii=False), encoding="utf-8")
            lesson_id = first["lesson_id"]
            assert identity.lesson_payload_identity_fingerprint(payload) == identity.lesson_payload_identity_fingerprint({key: value for key, value in payload.items() if key not in {"lesson_id", "lessonId", "identity", "lesson", "meta"}})
            first_state = query_identity(relative, lesson_id)
            assert lesson_id.startswith("ftg-lesson-")
            assert first_state["lesson"] and first_state["lesson"][1] == "active"
            assert first_state["replica"] and first_state["replica"][0] == lesson_id and first_state["replica"][2] == "reserved"
            assert first_state["registry"] == 1
            stored_payload = structure_store.structure_asset_json(first["structure"])
            assert stored_payload["lesson_id"] == lesson_id
            assert stored_payload["kind"] == seed["kind"]

            edited_payload = {**seed, "title": f"Builder {space} edited", "version": 2, "edit_marker": space}
            edited = json.loads(builder.encode_future_manifest(edited_payload, edited_payload["title"], output, space))
            assert edited["lesson_id"] == lesson_id

            copy_path = output.with_name(output.stem + " Copy" + output.suffix)
            copied_payload = dict(edited_payload)
            copied = json.loads(builder.encode_future_manifest(copied_payload, copied_payload["title"], copy_path, space))
            assert copied["lesson_id"] == lesson_id

            divergent = dict(copied_payload)
            divergent["edit_marker"] = space + "-diverged"
            divergent_path = output.with_name(output.stem + " Diverged" + output.suffix)
            blocked = False
            try:
                builder.encode_future_manifest(divergent, divergent["title"], divergent_path, space)
            except RuntimeError as exc:
                blocked = "Duplicate as New Lesson" in str(exc)
            assert blocked
            results[space] = {"lesson_id": lesson_id, "stable_edit": True, "exact_copy": True, "divergent_copy_blocked": True}

        import fitz
        import FUTURE.server_app as app
        import future_space_pdf_package as pdf_package
        import future_space_picture_package as picture_package

        inputs = server_data / "builder-input"
        inputs.mkdir(parents=True, exist_ok=True)
        pdf_source = inputs / "builder.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "Builder PostgreSQL PDF")
        document.save(str(pdf_source))
        document.close()
        picture_source = inputs / "builder.png"
        Image.new("RGB", (40, 30), (24, 92, 140)).save(picture_source)
        package_cases = []
        for space, source, output, build in (
            ("Space_PDF", pdf_source, server_data / "common" / "codex-builder.space_pdf", pdf_package.build_space_pdf_package),
            ("Space_Picture", picture_source, server_data / "common" / "codex-builder.space_picture", picture_package.build_space_picture_package),
        ):
            built = build(source, output, title=f"Builder {space}", server_data_root=server_data)
            rebuilt = build(source, output, title=f"Builder {space} edited", overwrite=True, server_data_root=server_data)
            assert rebuilt.lesson_id == built.lesson_id
            stat = output.stat()
            relative = output.resolve().relative_to(server_data.resolve()).as_posix().lower()
            registered = app.server_database_register_lesson_file_entries([{
                "lesson_id": built.lesson_id,
                "path": relative,
                "content_fingerprint": built.source_sha256,
                "modified_ns": int(stat.st_mtime_ns),
                "size": int(stat.st_size),
                "space": space,
            }])
            assert registered.get("registered") == 1 and registered.get("collisions") == 0
            assert app.server_database_lesson_file_id_for_path(relative) == built.lesson_id
            package_cases.append((space, built.lesson_id))
        results.update({space: {"lesson_id": lesson_id, "stable_rebuild": True, "postgres_registered": True} for space, lesson_id in package_cases})

        assert not (server_data / "server2.db").exists()
        assert not (server_data / "structure_assets.db").exists()
        evidence = {
            "ok": True,
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": int(dump_path.stat().st_size if dump_path else 0),
            },
            "backend": "postgresql",
            "spaces": results,
            "builder_callsites": sorted(callsites),
            "runtime_structure_readback": True,
            "package_runtime_registration": True,
            "sqlite_created": False,
        }
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    finally:
        isolated.stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
