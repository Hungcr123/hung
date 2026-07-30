import ast
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "server_data_pdf_qmdict" / "server_data_manifest_listing" / "02_manifest_cache_refresh.py"


def load_start_function(namespace: dict):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    target = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "start_server_data_manifest_monitor"
    )
    module = ast.Module(body=[target], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace["start_server_data_manifest_monitor"]


def main():
    events = []
    manifest = {"signature": "startup-test", "structural_metadata_version": 0}
    lock = __import__("threading").RLock()
    state = {}
    namespace = {
        "SERVER_DATA_MANIFEST_LOCK": lock,
        "SERVER_DATA_MANIFEST_STATE": state,
        "SERVER_DATA_MANIFEST_FILE": SOURCE,
        "clean": lambda value: str(value or "").strip(),
        "ensure_server_data_manifest_runtime_revisions": lambda value: value,
        "load_server_data_manifest_from_disk": lambda: manifest,
        "start_server_data_manifest_watchdog": lambda: events.append("watchdog"),
        "schedule_server_data_manifest_metadata_backfill": lambda _manifest: events.append("backfill") or True,
        "warm_server_data_tree_preload_cache": lambda _manifest: events.append("tree-warm") or {
            "users": 100,
            "cpu_ms": 1,
            "gzip_bytes": 1,
        },
        "schedule_server_data_manifest_startup_verify": lambda: events.append("verify"),
        "start_server_data_manifest_interval_monitor": lambda: events.append("interval"),
        "refresh_server_data_manifest_now": lambda _reason: manifest,
        "get_server_data_manifest": lambda force=False: manifest,
    }
    load_start_function(namespace)()
    assert events == ["watchdog", "backfill", "tree-warm", "verify", "interval"], events
    print("server_data_tree_startup_warm=ok backfill_pending=true tree_warm_before_return=true")


if __name__ == "__main__":
    main()
