"""Regression for cheap `/server-data/file` conditional preflight."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "FUTURE" / "server_parts" / "http_server" / "get_route_parts" / "03_auth_dashboard_server_data.pyfrag"


# Added 2026-07-20: prevent future refactors from rebuilding lesson payloads before a valid 304.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    route_start = source.index('if path == "/server-data/file":')
    route = source[route_start:source.index('self.send_json(500', route_start)]
    preflight = route.index('self.headers.get("If-None-Match"')
    hydration = route.index("cached_space_v_qmdict_file_bytes(target)")
    assert preflight < hydration, "Space_V conditional requests must be decided before hydration"
    assert '"server-data-space-v-qmdict",\n                    qmdict_mtime_ns,\n                    qmdict_size,' in route
    assert 'hydrate_meta.get("hydrated"' not in route
    assert route.count('"X-Future-Cache-Hit": "file-etag-preflight"') == 2
    assert route.count("etag=etag") >= 4
    print("server_data_file_etag_preflight=ok space_v=dependency_etag other=stat_etag")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
