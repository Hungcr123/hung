"""Verify QM City cannot fall back to SQLite or legacy JSON in PostgreSQL-only mode."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app
from FUTURE.postgres.repositories import leaderboard_documents, qm_city_documents


def main() -> int:
    assert "QM_CITY_DOCUMENTS" in app.POSTGRES_ONLY_REQUIRED_DOMAINS
    for name in qm_city_documents.QM_CITY_DOCUMENT_NAMES:
        assert app.server_database_document_local_only(Path(name)) is True

    original_env = {
        "FUTURE_POSTGRES_ONLY": os.environ.get("FUTURE_POSTGRES_ONLY"),
        "FUTURE_DB_QM_CITY_DOCUMENTS_BACKEND": os.environ.get("FUTURE_DB_QM_CITY_DOCUMENTS_BACKEND"),
        "FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND": os.environ.get("FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND"),
        "FUTURE_DB_VOCABULARY_BACKEND": os.environ.get("FUTURE_DB_VOCABULARY_BACKEND"),
    }
    original_qm_read = qm_city_documents.read_entry
    original_leaderboard_read = leaderboard_documents.read_entry
    original_store = app.server_database_store_document_now
    try:
        os.environ["FUTURE_POSTGRES_ONLY"] = "1"
        os.environ["FUTURE_DB_QM_CITY_DOCUMENTS_BACKEND"] = "postgres"
        os.environ["FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND"] = "postgres"
        os.environ["FUTURE_DB_VOCABULARY_BACKEND"] = "postgres"

        def failed_read(_path):
            raise RuntimeError("postgres unavailable")

        qm_city_documents.read_entry = failed_read
        leaderboard_documents.read_entry = failed_read
        for name in ("_future_shared_world.json", "_future_vocab_leaderboard_social.json"):
            try:
                app.server_database_document_entry(Path(name))
            except RuntimeError as exc:
                assert "postgres unavailable" in str(exc)
            else:
                raise AssertionError(f"PostgreSQL failure fell through for {name}")

        with tempfile.TemporaryDirectory(prefix="qm-city-pg-guard-") as temporary:
            target = Path(temporary) / "_future_qm_city_training.json"
            app.server_database_store_document_now = lambda *_args, **_kwargs: True
            app.atomic_write_json(target, {"version": 1})
            assert not target.exists(), "PostgreSQL-authoritative QM City state leaked to legacy JSON"

            derived = Path(temporary) / "vocab_file_meta_index_v1.json"
            app.atomic_write_json(derived, {"version": 1})
            assert derived.exists(), "PostgreSQL-only derived cache was not written locally"

            # The PostgreSQL document route must be reachable without initializing SQLite first.
            app.server_database_store_document_now = original_store
            original_initialize = app.initialize_server_database
            original_upsert = qm_city_documents.upsert_text
            app.initialize_server_database = lambda: (_ for _ in ()).throw(RuntimeError("SQLite init reached"))
            qm_city_documents.upsert_text = lambda *_args, **_kwargs: {"ok": True}
            try:
                assert app.server_database_store_document_now(target, '{"version":2}', authoritative=True)
            finally:
                app.initialize_server_database = original_initialize
                qm_city_documents.upsert_text = original_upsert

            wal_target = Path(temporary) / "periods.wal.jsonl"
            original_wal_path = app.VOCAB_LEADERBOARD_PERIOD_WAL_FILE
            app.VOCAB_LEADERBOARD_PERIOD_WAL_FILE = wal_target
            try:
                assert app.vocab_leaderboard_period_legacy_wal_enabled() is False
                assert app.append_vocab_leaderboard_period_wal("codexguard", {"day": {}}, app.utc_timestamp()) is False
                assert not wal_target.exists(), "PostgreSQL vocabulary runtime recreated the retired JSONL WAL"
            finally:
                app.VOCAB_LEADERBOARD_PERIOD_WAL_FILE = original_wal_path

        print("qm_city_postgres_runtime_guard=ok fail_closed=true legacy_json_write=false legacy_wal=false")
        return 0
    finally:
        qm_city_documents.read_entry = original_qm_read
        leaderboard_documents.read_entry = original_leaderboard_read
        app.server_database_store_document_now = original_store
        for name, value in original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    raise SystemExit(main())
