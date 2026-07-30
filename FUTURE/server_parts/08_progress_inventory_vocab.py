# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

PROGRESS_INVENTORY_VOCAB_PARTS_ROOT = SERVER_PARTS_ROOT / "progress_inventory_vocab"
PROGRESS_INVENTORY_VOCAB_PART_FILES = (
    "01_space_w_progress.py",
    "02_space_q_progress.py",
    "03_space_v_progress.py",
    "04_space_p_pdf_progress.py",
    "05_inventory_keyboard_assets.py",
    "06_vocab_registry_core.py",
    "07_main_vocab_sync.py",
    "08_vocab_recording_summary.py",
    "09_vocab_period_stats.py",
)


def _load_progress_inventory_vocab_part(part_name: str) -> None:
    part_path = PROGRESS_INVENTORY_VOCAB_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _progress_inventory_vocab_part_name in PROGRESS_INVENTORY_VOCAB_PART_FILES:
    _load_progress_inventory_vocab_part(_progress_inventory_vocab_part_name)
del _progress_inventory_vocab_part_name
