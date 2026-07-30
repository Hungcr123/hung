from __future__ import annotations

import os
import sys
from pathlib import Path

SERVER2_ROOT = Path(__file__).resolve().parent
FUTURE_ROOT = SERVER2_ROOT.parent
APP_ROOT = FUTURE_ROOT.parent

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

SPLIT_FRONTEND_PATH = FUTURE_ROOT / "web" / "future_split.html"
SPLIT_ASSET_ROOT = FUTURE_ROOT / "web"
SPLIT_RUNTIME_ROOT = APP_ROOT / "programe_cache" / "future_whisper_server_2"
SPLIT_STT_WORKER_SCRIPT = SERVER2_ROOT / "future_stt_worker_2.py"
SPLIT_VOICE_WORKER_SCRIPT = SERVER2_ROOT / "future_voice_worker_2.py"
SPLIT_PROCESS_WORKER_SCRIPT = SERVER2_ROOT / "future_process_worker_2.py"

os.environ.setdefault("FUTURE_FRONTEND_PATH", str(SPLIT_FRONTEND_PATH))
os.environ.setdefault("FUTURE_FRONTEND_ASSET_ROOT", str(SPLIT_ASSET_ROOT))
os.environ.setdefault("FUTURE_RUNTIME_ROOT", str(SPLIT_RUNTIME_ROOT))
os.environ.setdefault("FUTURE_STT_WORKER_SCRIPT", str(SPLIT_STT_WORKER_SCRIPT))
os.environ.setdefault("FUTURE_STT_WORKER_PORT", "8878")
os.environ.setdefault("FUTURE_VOICE_WORKER_SCRIPT", str(SPLIT_VOICE_WORKER_SCRIPT))
os.environ.setdefault("FUTURE_VOICE_WORKER_PORT", "8879")
os.environ.setdefault("FUTURE_PROCESS_WORKER_SCRIPT", str(SPLIT_PROCESS_WORKER_SCRIPT))
os.environ.setdefault("FUTURE_PROCESS_WORKER_PORT", "8880")
os.environ.setdefault("FUTURE_BROWSER_MODE", "coccoc")

from FUTURE.server_app import *  # re-export split server symbols for compatibility


def _with_default_arg(argv: list[str], name: str, value: str) -> list[str]:
    if any(arg == name or arg.startswith(f"{name}=") for arg in argv[1:]):
        return list(argv)
    return [*argv, name, value]


def main_server_2() -> int:
    argv = _with_default_arg(list(sys.argv), "--port", "8877")
    argv = _with_default_arg(argv, "--host", "0.0.0.0")
    sys.argv = argv
    return main()


if __name__ == "__main__":
    raise SystemExit(main_server_2())
