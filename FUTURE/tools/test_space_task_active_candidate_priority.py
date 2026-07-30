import ast
from pathlib import Path


SOURCE = Path("FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/03_payload.py")


def load_functions():
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {
        "_space_task_task_has_active_run",
        "_space_task_active_progress_keys",
        "_space_task_candidate_rank",
    }
    functions = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "clean": lambda value="": str(value or "").strip(),
        "clean_path_value": lambda value="": str(value or "").replace("\\", "/").strip("/ "),
        "natural_sort_key": lambda value="": str(value or "").lower(),
        "space_w_int": lambda value, default=0: int(value or default),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


def main():
    functions = load_functions()
    rank = functions["_space_task_candidate_rank"]
    active = {
        "path": "common/folder/active.Space_V",
        "space": "Space_V",
        "space_task_order": 7,
        "completed": True,
        "study": {"progress": {"done": 2, "total": 10, "activeRun": True}},
    }
    untouched = {
        "path": "common/folder/new.Space_V",
        "space": "Space_V",
        "space_task_order": 0,
        "completed": False,
        "study": {"progress": {"done": 0, "total": 10, "activeRun": False}},
    }
    assert rank(active) < rank(untouched), "active run must outrank a stale completed flag and a new untouched file"

    record = {"path": active["path"], "activeRun": True, "state": {}}
    progress_index = {
        ("Space_V", active["path"].lower()): record,
        ("Space_V", "id:ftg-lesson-active"): record,
    }
    keys = functions["_space_task_active_progress_keys"](progress_index)
    assert ("Space_V", active["path"].lower()) in keys
    assert all(not key.startswith("id:") for _space, key in keys)
    print("space_task_active_candidate_priority=ok")


if __name__ == "__main__":
    main()
