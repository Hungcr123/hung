"""Compatibility exports for the PostgreSQL-backed Structure asset store.

The old module name remains importable for builders and maintenance scripts, but
there is no local database implementation or backend selection here.
"""

from future_postgres_structure_asset_store import (
    close_structure_read_pool,
    initialize_structure_database,
    iter_structure_assets,
    lesson_id_registry_load,
    lesson_id_registry_write,
    ocr_cache_index,
    ocr_cache_page_text,
    run_postgres_transaction,
    structure_asset_bytes,
    structure_asset_exists,
    structure_asset_gzip,
    structure_asset_json,
    structure_asset_logical_path,
    structure_asset_signature,
    write_structure_asset_bytes,
    write_structure_asset_json,
)

__all__ = [
    "close_structure_read_pool",
    "initialize_structure_database",
    "iter_structure_assets",
    "lesson_id_registry_load",
    "lesson_id_registry_write",
    "ocr_cache_index",
    "ocr_cache_page_text",
    "run_postgres_transaction",
    "structure_asset_bytes",
    "structure_asset_exists",
    "structure_asset_gzip",
    "structure_asset_json",
    "structure_asset_logical_path",
    "structure_asset_signature",
    "write_structure_asset_bytes",
    "write_structure_asset_json",
]
