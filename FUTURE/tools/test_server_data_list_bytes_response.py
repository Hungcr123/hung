"""Regression for cached Lesson Vault folder responses being sent as JSON bytes."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


# Added 2026-07-30: cached response bytes must never be passed into send_json().
def main() -> int:
    payload = app.list_server_data(
        "common/PDF/Global Sucess",
        username="hung",
        fresh=True,
        lightweight=False,
        include_task_board=False,
        include_space_task=False,
    )
    assert isinstance(payload.get("_response_bytes"), bytes)
    assert payload.get("_response_etag")

    fragment = (
        ROOT
        / "FUTURE"
        / "server_parts"
        / "http_server"
        / "get_route_parts"
        / "03_auth_dashboard_server_data.pyfrag"
    ).read_text(encoding="utf-8")
    generated = (
        ROOT / "FUTURE" / "server_parts" / "http_server" / "03_handler_get_routes.py"
    ).read_text(encoding="utf-8")
    for source in (fragment, generated):
        route = source[source.index('if path == "/server-data/list"'):]
        route = route[:route.index('if path == "/server-data/last-file"')]
        assert 'payload.pop("_response_bytes", None)' in route
        assert "isinstance(response_bytes, bytes)" in route
        assert "self.send_bytes(" in route
        assert "server_data_list_request_failed" in route

    print("server_data_list_bytes_response=ok cached_bytes_use_send_bytes=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
