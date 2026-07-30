# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

STREAM_SCREEN_SECURITY_PARTS_ROOT = SERVER_PARTS_ROOT / "stream_screen_security"
STREAM_SCREEN_SECURITY_PART_FILES = (
    "01_stream_sessions.py",
    "02_screen_sessions.py",
    "03_security_health.py",
)


def _load_stream_screen_security_part(part_name: str) -> None:
    part_path = STREAM_SCREEN_SECURITY_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _stream_screen_security_part_name in STREAM_SCREEN_SECURITY_PART_FILES:
    _load_stream_screen_security_part(_stream_screen_security_part_name)
del _stream_screen_security_part_name
