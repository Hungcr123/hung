# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

HTTP_SERVER_PARTS_ROOT = SERVER_PARTS_ROOT / "http_server"
HTTP_HANDLER_PART_FILES = (
    "02_handler_core.py",
    "03_handler_get_routes.py",
    "04_handler_post_routes.py",
    "05_handler_logging.py",
)
HTTP_SERVER_GLOBAL_PART_FILES = (
    "01_multipart_server.py",
    "06_main.py",
)
HTTP_SERVER_PART_FILES = (
    "01_multipart_server.py",
    "02_handler_core.py",
    "03_handler_get_routes.py",
    "04_handler_post_routes.py",
    "05_handler_logging.py",
    "06_main.py",
)


def _load_http_server_part(part_name: str) -> None:
    part_path = HTTP_SERVER_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


def _load_http_handler_part(part_name: str, class_namespace: dict) -> None:
    part_path = HTTP_SERVER_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals(), class_namespace)


for _http_server_global_part_name in ("01_multipart_server.py",):
    _load_http_server_part(_http_server_global_part_name)
del _http_server_global_part_name


class FutureWhisperHandler(BaseHTTPRequestHandler):
    server_version = "FutureWhisperServer/1.0"
    # Added 2026-07-26: allow benchmark/browser sessions to reuse sockets for length-delimited responses.
    protocol_version = "HTTP/1.1"

    for _http_handler_part_name in HTTP_HANDLER_PART_FILES:
        _load_http_handler_part(_http_handler_part_name, locals())
    del _http_handler_part_name


for _http_server_global_part_name in ("06_main.py",):
    _load_http_server_part(_http_server_global_part_name)
del _http_server_global_part_name
