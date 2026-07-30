import ast
from pathlib import Path


SOURCE = Path("FUTURE/server_parts/server_data_pdf_qmdict/03_lesson_tasks_logs.py")


def load_completion_function():
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "lesson_task_completion_from_study"
    )
    namespace = {
        "clean": lambda value="": str(value or "").strip(),
        "merged_username_study_row": lambda rows, username: {},
        "space_w_int": lambda value, default=0: int(value or default),
        "timestamp_latest_text": lambda *values: next((str(value) for value in values if value), ""),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["lesson_task_completion_from_study"]


def main():
    completion = load_completion_function()
    boolean_active = completion(
        {"mine": 2, "progress": {"completed": True, "activeRun": True, "done": 2, "total": 10}},
        {},
        "quynh",
    )
    object_active = completion(
        {"mine": 1, "progress": {"completed": True, "activeRun": {"active": True}, "done": 3, "total": 10}},
        {},
        "quynh",
    )
    finished = completion(
        {"mine": 1, "progress": {"completed": True, "activeRun": False, "done": 10, "total": 10}},
        {},
        "quynh",
    )
    assert boolean_active["completed"] is False
    assert object_active["completed"] is False
    assert finished["completed"] is True
    print("space_task_active_run_completion=ok")


if __name__ == "__main__":
    main()
