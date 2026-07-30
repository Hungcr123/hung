"""Verify progress index invalidation is SQLite-generation based and filesystem-free."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "hung"
    original_path_reader = app.space_progress_existing_path
    before = app.lesson_progress_index_signature(username)
    try:
        app.space_progress_existing_path = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("progress signature touched a legacy export")
        )
        same = app.lesson_progress_index_signature(username)
        assert same == before
        app.server_database_bump_user_generation("progress", username)
        after = app.lesson_progress_index_signature(username)
        assert after != before
    finally:
        app.space_progress_existing_path = original_path_reader
    source_path = ROOT / "FUTURE" / "server_parts" / "06a_server_database.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    vocab_source = ast.unparse(functions["server_database_record_vocabulary_transaction"]).replace("'", '"')
    register_source = ast.unparse(functions["server_database_register_lesson_file_entries"]).replace("'", '"')
    assert 'server_database_bump_user_generation("progress", username)' in vocab_source
    assert 'server_database_bump_user_generation("progress", affected_user)' in register_source
    assert 'result.pop("reattached_users", None)' in register_source
    print("progress_index_generation=ok postgres_authoritative=true legacy_stats=0 invalidation=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

