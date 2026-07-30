# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

SPACE_TASK_AUTO_PARTS_ROOT = SERVER_DATA_PDF_QMDICT_PARTS_ROOT / "space_task_auto"
SPACE_TASK_AUTO_PART_FILES = (
    "01_settings.py",
    "02_folder_scan.py",
    "03_payload.py",
)


def _load_space_task_auto_part(part_name: str) -> None:
    part_path = SPACE_TASK_AUTO_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _space_task_auto_part_name in SPACE_TASK_AUTO_PART_FILES:
    _load_space_task_auto_part(_space_task_auto_part_name)
del _space_task_auto_part_name
