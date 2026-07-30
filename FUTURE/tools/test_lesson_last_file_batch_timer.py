import ast
import threading as real_threading
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "server_parts" / "server_data_pdf_qmdict" / "02_lesson_study_progress.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTION = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "schedule_lesson_last_file_flush")
SEMANTIC_FUNCTION = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "lesson_last_file_semantic_identity")


class FakeTimer:
    created = 0

    def __init__(self, _delay, _callback):
        type(self).created += 1
        self.daemon = False
        self._alive = False

    def start(self):
        self._alive = True

    def is_alive(self):
        return self._alive


class FakeThreading:
    Timer = FakeTimer


namespace = {
    "normalize_username": lambda value: str(value or "").strip(),
    "LESSON_LAST_FILE_LOCK": real_threading.RLock(),
    "LESSON_LAST_FILE_DIRTY_USERS": set(),
    "LESSON_LAST_FILE_FLUSH_TIMER": None,
    "LESSON_LAST_FILE_FLUSH_DELAY_SECONDS": 10.0,
    "flush_lesson_last_file_dirty": lambda: None,
    "threading": FakeThreading,
}
module = ast.Module(body=[FUNCTION], type_ignores=[])
exec(compile(ast.fix_missing_locations(module), str(SOURCE_PATH), "exec"), namespace)

semantic_namespace = {
    "clean": lambda value: str(value or "").strip(),
    "clean_path_value": lambda value: str(value or "").replace("\\", "/").strip("/"),
    "space_w_int": lambda value, default=0: int(value or default),
    "normalize_username": lambda value: str(value or "").strip(),
}
semantic_module = ast.Module(body=[SEMANTIC_FUNCTION], type_ignores=[])
exec(compile(ast.fix_missing_locations(semantic_module), str(SOURCE_PATH), "exec"), semantic_namespace)
semantic_identity = semantic_namespace["lesson_last_file_semantic_identity"]

for index in range(100):
    namespace["schedule_lesson_last_file_flush"](f"user{index}")

assert FakeTimer.created == 1, FakeTimer.created
assert len(namespace["LESSON_LAST_FILE_DIRTY_USERS"]) == 100
assert "schedule_lesson_last_file_flush(username)" in SOURCE
assert "persist_lesson_last_file_database(username, result)" not in (
    ast.get_source_segment(SOURCE, next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "remember_lesson_last_file")) or ""
)
assert "with lesson_last_file_user_lock(username):" in SOURCE
base = {
    "file": {"path": "common/A.Space_V", "parentPath": "common", "page": 2, "pages": 10, "accessedAt": "old"},
    "recentFiles": [{"path": "common/A.Space_V", "accessedAt": "old"}],
    "selectedFolder": {"path": "common", "task_owner": "hung", "selected_at": "old"},
}
new_timestamps = {
    "file": {**base["file"], "accessedAt": "new"},
    "recentFiles": [{"path": "common/A.Space_V", "accessedAt": "new"}],
    "selectedFolder": {**base["selectedFolder"], "selected_at": "new"},
}
new_page = {**new_timestamps, "file": {**new_timestamps["file"], "page": 3}}
assert semantic_identity(base) == semantic_identity(new_timestamps)
assert semantic_identity(base) != semantic_identity(new_page)
assert "time.time() - current_updated_epoch < 30.0" in SOURCE
remember_source = ast.get_source_segment(SOURCE, next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "remember_lesson_last_file")) or ""
assert remember_source.index("LESSON_LAST_FILE_REQUEST_CACHE.get") < remember_source.index("normalize_lesson_last_file_payload")
assert "LESSON_LAST_FILE_REQUEST_CACHE_MAX_USERS" in SOURCE
row_source = ast.get_source_segment(SOURCE, next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "normalize_lesson_last_file_row")) or ""
assert row_source.index('file_id.lower().startswith("ftg-lesson-")') < row_source.index("resolve_lesson_identity_contract(")
assert 'normalize_lesson_last_file_row(item, username, trusted_persisted=True)' in remember_source
print("lesson_last_file_batch_timer=ok users=100 timers=1 dirty_users=100 sqlite_durable=true semantic_30s_dedupe=true ram_preflight=true")
