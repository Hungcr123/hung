# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

CORE_RUNTIME_PARTS_ROOT = SERVER_PARTS_ROOT / "core_runtime"
CORE_RUNTIME_PART_FILES = (
    "01_clean_cpu_work_queue.py",
    "02_sort_anti_robot.py",
    "03_path_asset_guards.py",
    "04_time_debug_logging.py",
)


def _load_core_runtime_part(part_name: str) -> None:
    part_path = CORE_RUNTIME_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _core_runtime_part_name in CORE_RUNTIME_PART_FILES:
    _load_core_runtime_part(_core_runtime_part_name)
del _core_runtime_part_name
