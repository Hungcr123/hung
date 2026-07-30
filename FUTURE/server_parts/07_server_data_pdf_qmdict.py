# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

SERVER_DATA_PDF_QMDICT_PARTS_ROOT = SERVER_PARTS_ROOT / "server_data_pdf_qmdict"
SERVER_DATA_PDF_QMDICT_PART_FILES = (
    "01_server_data_paths_links.py",
    "02_lesson_study_progress.py",
    "03_lesson_tasks_logs.py",
    "03_space_task_auto.py",
    "04_server_data_manifest_listing.py",
    "05_picture_pdf_render.py",
    "06_ocr_qmdict_core.py",
    "07_qmlearn_audio_spacev_repair.py",
    "08_pdf_vocab_scan.py",
)


def _load_server_data_pdf_qmdict_part(part_name: str) -> None:
    part_path = SERVER_DATA_PDF_QMDICT_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _server_data_pdf_qmdict_part_name in SERVER_DATA_PDF_QMDICT_PART_FILES:
    _load_server_data_pdf_qmdict_part(_server_data_pdf_qmdict_part_name)
del _server_data_pdf_qmdict_part_name
