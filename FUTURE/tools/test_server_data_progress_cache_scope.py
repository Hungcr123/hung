import ast
import threading
import time
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "server_data_pdf_qmdict" / "server_data_manifest_listing" / "05_list_server_data.py"


def clean_path_value(value):
    return str(value or "").strip().replace("\\", "/").strip("/")


def normalize_username(value):
    return str(value or "").strip()


tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
wanted_names = {"clear_server_data_list_cache_paths", "patch_server_data_list_cache_study"}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted_names]
assert {node.name for node in nodes} == wanted_names

namespace = {
    "SERVER_DATA_LIST_CACHE": {},
    "SERVER_DATA_LIST_CACHE_LOCK": threading.RLock(),
    "clean_path_value": clean_path_value,
    "normalize_username": normalize_username,
}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)


def cache_key(user):
    return "|".join(["v2", "full", "deferred-tasks", "space-task-deferred", user, "user", "common", user, user, user])


def payload(done):
    return {
        "entries": [{
            "type": "file",
            "path": "common/File 02 - {7}.Space_V",
            "study": {"progress": {"done": done, "total": 10}},
        }]
    }


cache = namespace["SERVER_DATA_LIST_CACHE"]
cache[cache_key("hung")] = {"payload": payload(6)}
cache[cache_key("nam")] = {"payload": payload(10)}

patched = namespace["patch_server_data_list_cache_study"](
    ["common/File 02 - {7}.Space_V"],
    {"progress": {"done": 7, "total": 10}},
    username="hung",
)
assert patched == 1
assert cache[cache_key("hung")]["payload"]["entries"][0]["study"]["progress"]["done"] == 7
assert cache[cache_key("nam")]["payload"]["entries"][0]["study"]["progress"]["done"] == 10

namespace["clear_server_data_list_cache_paths"](["common/File 02 - {7}.Space_V"])
assert not cache

for index in range(100):
    user = f"u{index:03d}"
    cache[cache_key(user)] = {"payload": payload(index % 10)}
started = time.perf_counter()
patched = namespace["patch_server_data_list_cache_study"](
    ["common/File 02 - {7}.Space_V"],
    {"progress": {"done": 8, "total": 10}},
    username="u042",
)
elapsed_ms = (time.perf_counter() - started) * 1000
assert patched == 1
assert cache[cache_key("u042")]["payload"]["entries"][0]["study"]["progress"]["done"] == 8
assert cache[cache_key("u041")]["payload"]["entries"][0]["study"]["progress"]["done"] == 1
assert cache[cache_key("u043")]["payload"]["entries"][0]["study"]["progress"]["done"] == 3

print(f"server_data_progress_cache_scope=ok user_isolated=true path_index=6 users=100 patch_ms={elapsed_ms:.3f}")
