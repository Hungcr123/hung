# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

CHAT_PAINT_RUNTIME_PARTS_ROOT = SERVER_PARTS_ROOT / "chat_paint_runtime"
CHAT_PAINT_RUNTIME_PART_FILES = (
    "01_chat_state_activity.py",
    "02_chat_attachments_quota.py",
    "03_chat_messages_admin.py",
    "04_paint_board.py",
)


def _load_chat_paint_runtime_part(part_name: str) -> None:
    part_path = CHAT_PAINT_RUNTIME_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _chat_paint_runtime_part_name in CHAT_PAINT_RUNTIME_PART_FILES:
    _load_chat_paint_runtime_part(_chat_paint_runtime_part_name)
del _chat_paint_runtime_part_name
