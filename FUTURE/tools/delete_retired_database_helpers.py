"""One-shot deletion of unreachable legacy database helper families."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "FUTURE/server_parts/06a_server_database.py"

DELETE = {
    "server_database_ensure_user",
    "server_database_load_user_preferences_cache",
    "server_database_lesson_time_row",
    "server_database_inventory_item_row",
    "server_database_load_user_profile_cache",
    "server_database_load_lesson_state_presence_cache",
    "_server_database_progress_upsert",
    "server_database_migrate_progress_complete_current_run",
    "server_database_migrate_pdf_node_indexes_one_based",
    "server_database_restore_legacy_progress_orphans",
    "_server_database_vault_touch_revision",
    "_server_database_materialize_folder_reference",
    "_server_database_clone_vault_subtree",
    "server_database_migrate_vault_folder_links",
    "_server_database_vault_parent_folder",
    "_server_database_vault_unique_name",
    "_server_database_upsert_folder_link_row",
    "server_database_migrate_folder_link_documents",
    "server_database_load_folder_link_cache",
    "server_database_load_lesson_file_alias_cache",
    "_server_database_attach_legacy_progress_for_path",
    "_server_database_append_event_in_transaction",
    "_server_database_registry_payload",
}

REPLACE = {
    "restore_server_database_documents_to_legacy": '''def restore_server_database_documents_to_legacy() -> dict:
    raise RuntimeError("Legacy database document restore was removed after PostgreSQL cutover.")
''',
    "audit_server_database_document_coverage": '''def audit_server_database_document_coverage() -> dict:
    raise RuntimeError("Legacy database document audit was removed after PostgreSQL cutover.")
''',
    "migrate_server_database_from_legacy": '''def migrate_server_database_from_legacy() -> dict:
    raise RuntimeError("Legacy database migration was removed after PostgreSQL cutover.")
''',
}


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    spans = []
    found = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name in DELETE:
            found.add(node.name)
            spans.append((node.lineno - 1, int(node.end_lineno or node.lineno), ""))
        elif node.name in REPLACE:
            found.add(node.name)
            spans.append((node.lineno - 1, int(node.end_lineno or node.lineno), REPLACE[node.name].rstrip() + "\n\n"))
    expected = DELETE | set(REPLACE)
    missing = sorted(expected - found)
    if missing:
        raise RuntimeError(f"Missing functions: {missing}")
    for start, end, replacement in sorted(spans, reverse=True):
        lines[start:end] = [replacement]
    updated = "".join(lines)
    ast.parse(updated)
    TARGET.write_text(updated, encoding="utf-8", newline="")
    print(f"deleted_helpers={len(DELETE)} replaced_legacy_entrypoints={len(REPLACE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
