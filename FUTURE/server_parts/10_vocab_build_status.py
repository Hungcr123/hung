# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

VOCAB_BUILD_STATUS_PARTS_ROOT = SERVER_PARTS_ROOT / "vocab_build_status"
VOCAB_BUILD_STATUS_PART_FILES = (
    "01_lesson_vocab_helpers.py",
    "02_space_w_vocab_missions.py",
    "03_status_page.py",
)


def _load_vocab_build_status_part(part_name: str) -> None:
    part_path = VOCAB_BUILD_STATUS_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _vocab_build_status_part_name in VOCAB_BUILD_STATUS_PART_FILES:
    _load_vocab_build_status_part(_vocab_build_status_part_name)
del _vocab_build_status_part_name
