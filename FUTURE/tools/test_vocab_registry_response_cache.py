"""Regression checks for per-user vocabulary registry bytes and ETag caching."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "hung"
    row = app.build_vocab_registry_response_cache_row(username, False)
    payload = json.loads(row["bytes"].decode("utf-8"))
    assert payload["total_words"] == len(payload.get("words", []))
    assert row["etag"].startswith('"vocab-registry-')
    assert app.vocab_registry_response_cache_row(username)["cache_hit"] is True

    app.server_database_bump_user_generation("registry", "codex-other-user")
    assert app.vocab_registry_response_cache_row(username)["cache_hit"] is True
    app.server_database_bump_user_generation("registry", username)
    assert app.vocab_registry_response_cache_row(username) is None

    # PostgreSQL loads must reuse the generation-scoped RAM payload too.
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    load_globals = app.server_database_load_vocab_registry.__globals__
    original_backend = load_globals["postgres_backend_mode"]
    original_generation = load_globals["server_database_user_generation"]
    original_loader = pg_vocabulary.load_registry
    probe_user = "codex-registry-ram-probe"
    calls = {"count": 0}
    try:
        load_globals["postgres_backend_mode"] = lambda _domain: "postgres"
        load_globals["server_database_user_generation"] = lambda _domain, _user: 7
        pg_vocabulary.load_registry = lambda _user: calls.update(count=calls["count"] + 1) or {"version": 1, "words": {"one": {"word": "one"}}}
        load_globals["SERVER_DATABASE_REGISTRY_RAM_CACHE"].pop(probe_user, None)
        assert app.server_database_load_vocab_registry(probe_user)["words"]["one"]["word"] == "one"
        assert app.server_database_load_vocab_registry(probe_user)["words"]["one"]["word"] == "one"
        assert calls["count"] == 1
    finally:
        load_globals["postgres_backend_mode"] = original_backend
        load_globals["server_database_user_generation"] = original_generation
        pg_vocabulary.load_registry = original_loader
        load_globals["SERVER_DATABASE_REGISTRY_RAM_CACHE"].pop(probe_user, None)
    print("vocab_registry_response_cache=ok bytes=true etag=true per_user_invalidation=true postgres_ram=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
