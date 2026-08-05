from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTES = (
    ROOT / "FUTURE/server_parts/http_server/03_handler_get_routes.py",
    ROOT / "FUTURE/server_parts/http_server/get_route_parts/06_world_game_assets.pyfrag",
)


def main() -> int:
    expected_etag = 'etag=etag if revision_matches else ""'
    expected_cache = '"public, max-age=31536000, immutable" if revision_matches else "no-store, no-cache, max-age=0, must-revalidate"'
    for route_path in ROUTES:
        source = route_path.read_text(encoding="utf-8")
        marker = 'if path == "/server-data/qm-sound":'
        route = source[source.index(marker):]
        assert expected_etag in route, route_path
        assert expected_cache in route, route_path
    print("qm-sound current/unversioned responses suppress ETag")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
