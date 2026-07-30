"""Focused completion invariants for portable V/W/Q/P/L/S progress."""

import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def assert_sqlite_complete(space: str, record: dict, expected: int) -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE lesson_progress_namespaces(
            username TEXT NOT NULL, space TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username, space)
        );
        CREATE TABLE lesson_progress(
            username TEXT NOT NULL, space TEXT NOT NULL, progress_key TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '', identity TEXT NOT NULL DEFAULT '', file_id TEXT NOT NULL DEFAULT '',
            node_index INTEGER NOT NULL DEFAULT 0, node_count INTEGER NOT NULL DEFAULT 0,
            learned_count INTEGER NOT NULL DEFAULT 0, complete INTEGER NOT NULL DEFAULT 0,
            server_revision INTEGER NOT NULL DEFAULT 0, updated_at_utc TEXT NOT NULL, record_json TEXT NOT NULL,
            PRIMARY KEY(username, space, progress_key)
        );
        CREATE UNIQUE INDEX lesson_progress_user_file_idx ON lesson_progress(username, file_id) WHERE file_id<>'';
        """
    )
    app._server_database_progress_upsert(connection, "codexcompletion", space, "probe", record)
    row = connection.execute("SELECT complete,record_json FROM lesson_progress").fetchone()
    assert row and row[0] == expected, (space, row)
    stored = json.loads(row[1])
    assert bool(stored.get("complete")) is bool(expected), (space, stored)


def assert_sqlite_rekeys_same_lesson_id(space: str) -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE lesson_progress_namespaces(
            username TEXT NOT NULL, space TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username, space)
        );
        CREATE TABLE lesson_progress(
            username TEXT NOT NULL, space TEXT NOT NULL, progress_key TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '', identity TEXT NOT NULL DEFAULT '', file_id TEXT NOT NULL DEFAULT '',
            node_index INTEGER NOT NULL DEFAULT 0, node_count INTEGER NOT NULL DEFAULT 0,
            learned_count INTEGER NOT NULL DEFAULT 0, complete INTEGER NOT NULL DEFAULT 0,
            server_revision INTEGER NOT NULL DEFAULT 0, updated_at_utc TEXT NOT NULL, record_json TEXT NOT NULL,
            PRIMARY KEY(username, space, progress_key)
        );
        CREATE UNIQUE INDEX lesson_progress_user_file_idx ON lesson_progress(username, file_id) WHERE file_id<>'';
        """
    )
    lesson_id = f"ftg-lesson-rekey-{space.lower()}"
    old = {"identity": lesson_id, "file_id": lesson_id, "path": f"old.{space}", "nodeCount": 4, "nodeIndex": 1, "_serverRevision": 1, "state": {"activeRun": True, "runId": "run-old"}}
    new = {"identity": lesson_id, "file_id": lesson_id, "path": f"new.{space}", "nodeCount": 4, "nodeIndex": 2, "_serverRevision": 2, "state": {"activeRun": True, "runId": "run-new"}}
    app._server_database_progress_upsert(connection, "codexcompletion", space, "old-key", old)
    app._server_database_progress_upsert(connection, "codexcompletion", space, "new-key", new)
    rows = connection.execute("SELECT progress_key,path,node_index FROM lesson_progress").fetchall()
    assert rows == [("new-key", f"new.{space}", 2)], rows
    connection.close()


def main() -> int:
    stamp = "2026-07-23T01:00:00Z"
    incomplete = {"nodeCount": 4, "nodeIndex": 1, "runId": "run-1", "updatedAt": stamp, "state": {"runId": "run-1"}}
    assert_sqlite_complete("Space_W", incomplete, 0)

    space_w_complete = {**incomplete, "state": {"runId": "run-1", "reviewFinished": True}}
    assert_sqlite_complete("Space_W", space_w_complete, 1)
    transition = app.space_progress_completion_transition(incomplete, space_w_complete, "Space_W")
    assert transition["transitioned"] is True
    assert app.space_progress_completion_transition(space_w_complete, space_w_complete, "Space_W")["transitioned"] is False

    new_study = {**incomplete, "runId": "run-2", "completedRuns": 1, "state": {"runId": "run-2", "activeRun": True}}
    summary = app.server_database_progress_completion_summary(new_study, "Space_W")
    assert summary["current_run_complete"] is False and summary["lifetime_complete"] is True
    assert_sqlite_complete("Space_W", new_study, 0)
    new_study_complete = {**new_study, "state": {"runId": "run-2", "reviewFinished": True}}
    assert app.space_progress_completion_transition(new_study, new_study_complete, "Space_W")["transitioned"] is True

    for space in ("Space_V", "Space_W", "Space_Q", "Space_P", "Space_L", "Space_S"):
        old_complete = {
            "nodeIndex": 4,
            "nodeCount": 4,
            "runId": f"{space}-old",
            "savedAt": "2026-07-23T01:00:00Z",
            "complete": True,
            "state": {"runId": f"{space}-old", "complete": True},
        }
        active_new = {
            "nodeIndex": 0,
            "nodeCount": 4,
            "runId": f"{space}-new",
            "savedAt": "2026-07-23T01:00:01Z",
            "activeRun": True,
            "state": {"runId": f"{space}-new", "activeRun": True},
        }
        merged = (
            app.merge_space_v_progress_record(old_complete, active_new, True)
            if space == "Space_V"
            else app.merge_space_progress_newest(old_complete, active_new, space)
        )
        merged_summary = app.server_database_progress_completion_summary(merged, space)
        assert merged_summary["current_run_complete"] is False, (space, merged)
        assert merged_summary["lifetime_complete"] is True, (space, merged)
        assert merged.get("completedRuns", 0) >= 1, (space, merged)

        stale_clear = {
            "savedAt": old_complete["savedAt"],
            "expectedRunId": old_complete["runId"],
            "baseRevision": 1,
        }
        protected_new = {**active_new, "_serverRevision": 2}
        assert app.space_progress_clear_is_stale(protected_new, stale_clear) is True, (space, protected_new, stale_clear)

    assert_sqlite_complete("Space_V", {
        "nodeCount": 2, "updatedAt": stamp, "state": {"learned": ["one", "two"]},
    }, 1)
    for space in ("Space_V", "Space_W", "Space_Q", "Space_P", "Space_L", "Space_S"):
        assert_sqlite_rekeys_same_lesson_id(space)
        canonical_id = f"ftg-lesson-ram-{space.lower()}"
        stale = {"lesson_id": canonical_id, "runId": "old-run"}
        picked, picked_key = app.space_progress_existing_canonical_state(
            {"unrelated-old-key": stale}, "canonical-key", "path-key", canonical_id
        )
        assert picked is stale and picked_key == "unrelated-old-key", (space, picked, picked_key)
    assert_sqlite_complete("Space_Q", {
        "nodeCount": 2, "updatedAt": stamp, "state": {"questionTotal": 6, "questionDone": 6},
    }, 1)
    for space in ("Space_P", "Space_L", "Space_S"):
        assert_sqlite_complete(space, {
            "nodeCount": 2, "updatedAt": stamp, "state": {"totalSegments": 8, "completedSegments": 8},
        }, 1)

    completion_source = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/server_data_manifest_listing/04_lesson_completion.py").read_text(encoding="utf-8")
    assert 'event_version = f"run:{requested_completion_run_id}"' in completion_source
    assert "requested_completion_run_id," in completion_source
    assert "lesson_completion_source_for_request(raw_path, username, requested_lesson_id)" in completion_source
    assert "resolve_lesson_identity_contract(" in completion_source
    client_source = (ROOT / "FUTURE/web/js_parts/17_vocab_to_pdf_bootstrap.js").read_text(encoding="utf-8")
    assert '/\\.space_w$/i.test(sourcePath)' in client_source
    assert "completion_run_id: completionRunId" in client_source
    coordinator_source = (ROOT / "FUTURE/web/js_parts/00_completion_coordinator.js").read_text(encoding="utf-8")
    assert 'recorded || duplicate || hasBoardPayload || context.completionAlreadyConfirmed || response.deduplicated' in coordinator_source
    assert 'ui.invalidateLeaderboard' in coordinator_source
    assert 'ui.openTopLeaderboard' in coordinator_source
    assert 'handleSpaceCompletion' in client_source
    assert 'effective_path: clean(source.effective_path || "")' in client_source
    assert 'link_target: clean(source.link_target || "")' in client_source
    assert 'if (lessonCompletionSent) {' in client_source
    assert 'completedSourcePath' in client_source
    navigation_source = (ROOT / "FUTURE/web/js_parts/13_translation_vocab_sync.js").read_text(encoding="utf-8")
    assert 'pendingVocabularyPayload && resolveSpaceRunNavigation(currentVocabProgressCache.savedProgress, "Space_V").resumeAvailable' in navigation_source
    assert 'pendingQuestionPayload) {' in navigation_source and 'startSavedQuestionProgress' in navigation_source
    assert 'await clearSavedQuestionProgress(false)' in navigation_source
    assert 'await clearSavedParagraphProgress(false)' in navigation_source
    assert 'clearSavedQuestionProgress();' not in (ROOT / "FUTURE/web/js_parts/12_question_translation_loader.js").read_text(encoding="utf-8")
    assert 'clearSavedParagraphProgress(true);' not in (ROOT / "FUTURE/web/js_parts/08_speak_question_input.js").read_text(encoding="utf-8")
    normalizer_source = (ROOT / "FUTURE/web/js_parts/06_spacew_audio_scheduler.js").read_text(encoding="utf-8")
    assert normalizer_source.count("lesson_id: clean(payload.lesson_id") >= 2
    assert "const lessonId = clean(payload.lesson_id" in normalizer_source
    restore_source = (ROOT / "FUTURE/web/js_parts/21_progress_bootstrap_events.js").read_text(encoding="utf-8")
    assert "restorePendingListenCard" in restore_source
    assert "nextPanelCanShow" in restore_source and "!speakStepCompleted" in restore_source
    server_source = (ROOT / "FUTURE/server_parts/progress_inventory_vocab/01_space_w_progress.py").read_text(encoding="utf-8")
    assert 'lesson_source["lesson_id"] = identity[:240]' in server_source
    vocab_server_source = (ROOT / "FUTURE/server_parts/progress_inventory_vocab/03_space_v_progress.py").read_text(encoding="utf-8")
    assert '"lesson_id": clean(identity_info.get("identity", ""))' in vocab_server_source
    print("portable_space_completion_consistency=ok spaces=V/W/Q/P/L/S lifetime_vs_active=true stable_run_id=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
