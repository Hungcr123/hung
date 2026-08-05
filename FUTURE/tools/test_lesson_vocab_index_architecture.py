"""Behavioral regressions for the shared lesson-id vocabulary index."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import time
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def qmdict_row(word: str) -> dict:
    return {"word": word, "meaning": f"meaning-{word}", "pron": f"/{word}/", "type": "noun"}


def main() -> int:
    expected_a = {"quasar", "nebula", "saffron", "tundra", "lantern", "velvet", "harbor", "compass", "beacon"}
    expected_b = {"orchid"}
    payload_a = {
        "k": "ftq",
        "lesson_id": "lesson-alpha",
        "rootText": "lantern",
        "nodes": [{
            "question": "quasar",
            "answer": "nebula",
            "wrong": ["saffron"],
            "options": ["tundra"],
            "explanation": "velvet quasar",
            "hint": "harbor",
            "guidance_tree": {"items": [{"main": "compass"}]},
            "root_notice": {"turns": [{"english": "beacon"}]},
            "id": "forbiddenidentifier",
            "url": "https://example.invalid/forbiddenasset.mp3",
            "hash": "forbiddenhash",
            "timestamp": "2030-01-01T00:00:00Z",
        }],
    }
    payload_b = {"k": "ftq", "lesson_id": "lesson-beta", "nodes": [{"question": "orchid"}]}
    summary_maps = {key: qmdict_row(key) for key in expected_a | expected_b}

    globals_map = app.lesson_file_vocab_meta_for_target.__globals__
    patched_names = (
        "VOCAB_FILE_META_INDEX_PATH",
        "qmdict_source_signature_key",
        "qmdict_registry_summary_maps",
        "qmdict_lookup_summary",
        "load_future_lesson_document",
        "server_data_relative",
        "schedule_vocab_file_meta_index_write",
        "lesson_file_vocab_meta_for_target",
        "safe_server_data_path",
        "server_data_effective_file_path",
        "is_admin_user",
        "normalize_username",
        "read_user_vocab_registry",
        "server_data_user_folder_path",
        "lesson_vocab_meta_for_id",
        "lesson_file_vocab_meta_cached_for_target",
        "lesson_vocab_meta_is_current",
        "schedule_lesson_vocab_meta_repair",
    )
    originals = {name: globals_map[name] for name in patched_names}
    original_state = copy.deepcopy(globals_map["VOCAB_FILE_META_INDEX_STATE"])
    original_ram = dict(globals_map["VOCAB_FILE_META_RAM_CACHE"])
    original_base_cache = dict(globals_map["QMDICT_VOCAB_BASE_CACHE"])
    load_counts: dict[str, int] = {}
    lookup_calls = {"count": 0}

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            lesson_a = temp_root / "alpha.Space_Q"
            lesson_b = temp_root / "beta.Space_Q"
            lesson_a.write_text("alpha-v1", encoding="utf-8")
            lesson_b.write_text("beta-v1", encoding="utf-8")
            payloads = {str(lesson_a): payload_a, str(lesson_b): payload_b}

            def load_document(path: Path):
                key = str(Path(path))
                load_counts[key] = load_counts.get(key, 0) + 1
                return copy.deepcopy(payloads[key]), None

            def lookup_summary(word: object = "", surface: str = "") -> dict:
                lookup_calls["count"] += 1
                return summary_maps.get(app.vocab_key(word), {})

            globals_map["VOCAB_FILE_META_INDEX_PATH"] = temp_root / "vocab_index.json"
            globals_map["qmdict_source_signature_key"] = lambda: (11, 22)
            globals_map["qmdict_registry_summary_maps"] = lambda: summary_maps
            globals_map["qmdict_lookup_summary"] = lookup_summary
            globals_map["load_future_lesson_document"] = load_document
            globals_map["server_data_relative"] = lambda path: Path(path).name
            globals_map["schedule_vocab_file_meta_index_write"] = lambda: None
            globals_map["VOCAB_FILE_META_RAM_CACHE"].clear()
            globals_map["VOCAB_FILE_META_INDEX_STATE"].update({
                "loaded": True,
                "rows": {},
                "lessons": {},
                "revision": 0,
                "first_dirty_at": 0.0,
                "timer": None,
            })

            meta_a = app.lesson_file_vocab_meta_for_target(lesson_a)
            meta_b = app.lesson_file_vocab_meta_for_target(lesson_b)
            assert set(meta_a["vocab_valid_word_keys"]) == expected_a
            assert set(meta_b["vocab_valid_word_keys"]) == expected_b
            assert meta_a["vocab_valid_word_keys"].count("quasar") == 1
            assert not ({"forbiddenidentifier", "forbiddenasset", "forbiddenhash", "example", "invalid"} & set(meta_a["vocab_word_keys"]))
            assert not (expected_a & set(meta_b["vocab_valid_word_keys"]))
            assert lookup_calls["count"] == 0
            assert load_counts[str(lesson_a)] == 1 and load_counts[str(lesson_b)] == 1

            second_a = app.lesson_file_vocab_meta_for_target(lesson_a)
            assert second_a["vocab_valid_word_keys"] == meta_a["vocab_valid_word_keys"]
            assert load_counts[str(lesson_a)] == 1

            revision = int(globals_map["VOCAB_FILE_META_INDEX_STATE"]["revision"] or 0)
            app.write_vocab_file_meta_index_snapshot(revision)
            persisted = json.loads(globals_map["VOCAB_FILE_META_INDEX_PATH"].read_text(encoding="utf-8"))
            assert persisted["version"] == app.VOCAB_FILE_META_INDEX_VERSION
            assert persisted["extractor_version"] == app.VOCAB_FILE_META_EXTRACTOR_VERSION
            assert set(persisted["lessons"]) == {"lesson-alpha", "lesson-beta"}

            globals_map["VOCAB_FILE_META_RAM_CACHE"].clear()
            globals_map["VOCAB_FILE_META_INDEX_STATE"].update({"loaded": False, "rows": {}, "lessons": {}})
            globals_map["qmdict_lookup_summary"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("restart must not validate"))
            restarted_a = app.lesson_vocab_meta_for_id("lesson-alpha")
            assert set(restarted_a["vocab_valid_word_keys"]) == expected_a
            assert load_counts[str(lesson_a)] == 1

            time.sleep(0.002)
            lesson_a.write_text("alpha-v2", encoding="utf-8")
            payloads[str(lesson_a)] = {**payload_a, "nodes": [*payload_a["nodes"], {"question": "orchid"}]}
            globals_map["qmdict_lookup_summary"] = lookup_summary
            changed_a = app.lesson_file_vocab_meta_for_target(lesson_a)
            assert "orchid" in changed_a["vocab_valid_word_keys"]
            assert load_counts[str(lesson_a)] == 2
            assert load_counts[str(lesson_b)] == 1
            app.lesson_file_vocab_meta_for_target(lesson_b)
            assert load_counts[str(lesson_b)] == 1

            globals_map["safe_server_data_path"] = lambda *_args, **_kwargs: lesson_a
            globals_map["server_data_effective_file_path"] = lambda *_args, **_kwargs: lesson_a
            globals_map["is_admin_user"] = lambda _username: False
            globals_map["normalize_username"] = lambda username: str(username).strip().lower()
            globals_map["read_user_vocab_registry"] = lambda username: {
                "words": {"quasar": {}} if username == "alice" else {"nebula": {}}
            }
            globals_map["server_data_user_folder_path"] = lambda username: temp_root / username
            globals_map["QMDICT_VOCAB_BASE_CACHE"].clear()
            alice_ctx = app.space_w_vocab_context("alpha.Space_Q", "alice", lesson_id="lesson-alpha")
            bob_ctx = app.space_w_vocab_context("alpha.Space_Q", "bob", lesson_id="lesson-alpha")
            alice_new = {app.vocab_key(entry.word) for entry in alice_ctx["new_entries"]}
            bob_new = {app.vocab_key(entry.word) for entry in bob_ctx["new_entries"]}
            assert "quasar" not in alice_new and "nebula" in alice_new
            assert "nebula" not in bob_new and "quasar" in bob_new
            assert load_counts[str(lesson_a)] == 2

            repair_started = threading.Event()
            repair_release = threading.Event()
            original_builder = originals["lesson_file_vocab_meta_for_target"]

            def slow_repair(_path: Path):
                repair_started.set()
                repair_release.wait(2)
                return {}

            globals_map["lesson_file_vocab_meta_for_target"] = slow_repair
            started = time.perf_counter()
            first_repair = app.schedule_lesson_vocab_meta_repair(lesson_a, "repair-alpha")
            assert repair_started.wait(1)
            second_repair = app.schedule_lesson_vocab_meta_repair(lesson_a, "repair-alpha")
            elapsed_ms = (time.perf_counter() - started) * 1000
            assert first_repair["scheduled"] and second_repair["single_flight"]
            assert elapsed_ms < 1000
            repair_release.set()
            globals_map["lesson_file_vocab_meta_for_target"] = original_builder

            globals_map["lesson_vocab_meta_for_id"] = lambda _lesson_id="": {}
            globals_map["lesson_file_vocab_meta_cached_for_target"] = lambda _target: {}
            globals_map["lesson_vocab_meta_is_current"] = lambda _record, _stat: False
            globals_map["schedule_lesson_vocab_meta_repair"] = lambda *_args, **_kwargs: {"scheduled": True, "single_flight": False}
            globals_map["read_user_vocab_registry"] = lambda _username: (_ for _ in ()).throw(AssertionError("pending index must not read registry"))
            started = time.perf_counter()
            pending = app.scan_space_w_vocabulary("alpha.Space_Q", "alice", include_words=False, lesson_id="lesson-alpha")
            pending_ms = (time.perf_counter() - started) * 1000
            assert pending["index_pending"] and pending["repair_scheduled"]
            assert pending_ms < 1000

        print(
            "lesson_vocab_index_architecture=ok "
            f"lesson_a={len(expected_a)} lesson_b={len(expected_b)} lookup_calls={lookup_calls['count']} "
            f"decode_a={load_counts.get(str(lesson_a), 0)} decode_b={load_counts.get(str(lesson_b), 0)} "
            f"pending_ms={pending_ms:.2f}"
        )
        return 0
    finally:
        timer = globals_map["VOCAB_FILE_META_INDEX_STATE"].get("timer")
        if hasattr(timer, "cancel"):
            timer.cancel()
        globals_map["VOCAB_FILE_META_INDEX_STATE"].clear()
        globals_map["VOCAB_FILE_META_INDEX_STATE"].update(original_state)
        globals_map["VOCAB_FILE_META_RAM_CACHE"].clear()
        globals_map["VOCAB_FILE_META_RAM_CACHE"].update(original_ram)
        globals_map["QMDICT_VOCAB_BASE_CACHE"].clear()
        globals_map["QMDICT_VOCAB_BASE_CACHE"].update(original_base_cache)
        globals_map.update(originals)


if __name__ == "__main__":
    raise SystemExit(main())
