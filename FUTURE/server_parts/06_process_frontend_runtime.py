# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

PROCESS_FRONTEND_PARTS_ROOT = SERVER_PARTS_ROOT / "process_frontend_runtime"
PROCESS_FRONTEND_PART_FILES = (
    "01_model_paths.py",
    "02_tunnel_process_dashboard.py",
    "03_local_stt_runtime.py",
    "04_stt_worker_bridge.py",
    "04_voice_worker_bridge.py",
    "04_process_worker_bridge.py",
    "04_distributed_worker_pool.py",
    "04_durable_tts_queue.py",
    "05_payload_assets_storage.py",
    "06_frontend_delivery.py",
    "07_server_screen_clip_hotkey.py",
)


def _load_process_frontend_part(part_name: str) -> None:
    part_path = PROCESS_FRONTEND_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _process_frontend_part_name in PROCESS_FRONTEND_PART_FILES:
    _load_process_frontend_part(_process_frontend_part_name)
del _process_frontend_part_name
