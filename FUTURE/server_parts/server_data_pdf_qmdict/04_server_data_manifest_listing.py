# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

SERVER_DATA_MANIFEST_LISTING_PARTS_ROOT = SERVER_DATA_PDF_QMDICT_PARTS_ROOT / "server_data_manifest_listing"
SERVER_DATA_MANIFEST_LISTING_PART_FILES = (
    "01_manifest_build_scan.py",
    "02_manifest_cache_refresh.py",
    "03_manifest_query_cache.py",
    "04_lesson_completion.py",
    "05_list_server_data.py",
    "06_link_copy_mission_cleanup.py",
    "07_operations_read.py",
    "09_server_boot_snapshot.py",
)


def _load_server_data_manifest_listing_part(part_name: str) -> None:
    part_path = SERVER_DATA_MANIFEST_LISTING_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _server_data_manifest_listing_part_name in SERVER_DATA_MANIFEST_LISTING_PART_FILES:
    _load_server_data_manifest_listing_part(_server_data_manifest_listing_part_name)
del _server_data_manifest_listing_part_name
