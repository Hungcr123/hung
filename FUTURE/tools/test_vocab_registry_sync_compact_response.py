from pathlib import Path


SOURCE = Path("FUTURE/server_parts/http_server/post_route_parts/06_world_battle_game_lesson.pyfrag").read_text(encoding="utf-8")
START = SOURCE.index('    if path == "/vocab/registry/sync":')
END = SOURCE.index('    if path == "/vocab/sync-main-offline-push":', START)
ROUTE = SOURCE[START:END]

assert "user_vocabulary_registry_summary" not in ROUTE
assert "read_user_vocab_registry_summary(username)" in ROUTE
assert '"response_schema": "vocab-registry-sync-compact-v1"' in ROUTE
assert "sync_main=False" in ROUTE
assert "verify_registry=False" in ROUTE
assert '"words":' not in ROUTE

print("vocab_registry_sync_compact_response=ok")
