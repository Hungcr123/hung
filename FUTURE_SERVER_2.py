from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _cli_port(argv: list[str]) -> int:
    for index, arg in enumerate(argv[1:], start=1):
        if arg.startswith("--port="):
            raw = arg.split("=", 1)[1].strip()
            if raw.isdigit():
                return int(raw)
        if arg == "--port" and index + 1 < len(argv):
            raw = argv[index + 1].strip()
            if raw.isdigit():
                return int(raw)
    return 8877


def _ensure_port_scoped_runtime_root() -> None:
    if os.environ.get("FUTURE_RUNTIME_ROOT"):
        return
    port = _cli_port(sys.argv)
    repo_root = Path(__file__).resolve().parent
    runtime_root = repo_root / "programe_cache" / f"future_whisper_server_{port}"
    os.environ["FUTURE_RUNTIME_ROOT"] = str(runtime_root)

_POSTGRES_DOMAINS = (
    "AI_HISTORY_DOCUMENTS",
    "ANNOUNCEMENTS",
    "APPEND_EVENTS",
    "AUTH",
    "CHAT",
    "INVENTORY",
    "LEADERBOARD_DOCUMENTS",
    "LEARNING_SUMMARY_DOCUMENTS",
    "LESSON_FOLDER_LINKS",
    "LESSON_IDENTITY",
    "LESSON_LAST_FILE",
    "LESSON_PROGRESS",
    "LESSON_TASK",
    "LESSON_TASK_NOTICES",
    "LESSON_TIME",
    "PDF_DRAWINGS",
    "QMDICT_DOCUMENTS",
    "QM_CITY_DOCUMENTS",
    "SPACE_PDF_AI_DOCUMENTS",
    "SPACE_W_SPEAK_SKIP",
    "USER_AUTH_DOCS",
    "USER_PREFERENCES",
    "VAULT_METADATA",
    "VIEWER_TOOL_DOCUMENTS",
    "VOCABULARY",
    "VOCAB_IMAGE_CACHE",
)


def _configure_manual_postgres_startup() -> None:
    # Added 2026-07-26: direct Explorer/manual starts use the same
    # PostgreSQL production defaults as the safe restart script.
    os.environ.pop("FUTURE_DB_BACKEND", None)
    os.environ.pop("FUTURE_POSTGRES_BACKEND", None)
    os.environ.pop("FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK", None)
    os.environ.pop("FUTURE_TEST_PASSWORD", None)
    os.environ.setdefault("FUTURE_PG_DSN", "postgresql://future_server2_app@127.0.0.1:5432/future_server2")
    for domain in _POSTGRES_DOMAINS:
        os.environ.setdefault(f"FUTURE_DB_{domain}_BACKEND", "postgres")


_configure_manual_postgres_startup()
_ensure_port_scoped_runtime_root()

def _ensure_postgres_service_running() -> None:
    # Added 2026-07-27: direct Server 2 starts are PostgreSQL-only, so make the
    # local PostgreSQL service available before runtime modules open the pool.
    if os.name != "nt":
        return
    if os.environ.get("FUTURE_SKIP_POSTGRES_SERVICE_START", "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    service_name = os.environ.get("FUTURE_POSTGRES_SERVICE_NAME", "postgresql-x64-17").strip() or "postgresql-x64-17"
    command = (
        f"$svc=Get-Service -Name '{service_name}' -ErrorAction Stop; "
        "if($svc.Status -ne 'Running'){Start-Service -Name $svc.Name}; "
        "$deadline=(Get-Date).AddSeconds(25); "
        "do{Start-Sleep -Milliseconds 250; $svc.Refresh()} "
        "until($svc.Status -eq 'Running' -or (Get-Date) -gt $deadline); "
        "if($svc.Status -ne 'Running'){throw 'PostgreSQL service did not reach Running.'}"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=35,
        )
    except Exception as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or "").strip()
        elif isinstance(exc, subprocess.TimeoutExpired):
            detail = "timeout while starting PostgreSQL service"
        raise RuntimeError(f"Cannot start required PostgreSQL service {service_name}: {detail or exc}") from exc

_ensure_postgres_service_running()

from FUTURE.server2.run_server_2 import *  # re-export split server symbols for compatibility


if __name__ == "__main__":
    if not any(arg == "--replace-old" or arg.startswith("--replace-old=") for arg in sys.argv[1:]):
        sys.argv.append("--replace-old")
    raise SystemExit(main_server_2())
