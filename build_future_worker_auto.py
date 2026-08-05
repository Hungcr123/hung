from __future__ import annotations

import shutil
import subprocess
import sys
import os
import re
import hashlib
import json
from pathlib import Path
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


ROOT = Path(__file__).resolve().parent
PROGRAME_ROOT = ROOT.parent


def default_worker_auto_build_dir() -> Path:
    raw = str(os.environ.get("FUTURE_WORKER_AUTO_BUILD_DIR", "") or "").strip().strip('"')
    if raw:
        return Path(raw).resolve()
    if Path("D:/").exists():
        return Path("D:/FutureWorkerCache/future_worker_auto_build")
    return ROOT / "programe_cache" / "future_worker_auto_build"


BUILD_DIR = default_worker_auto_build_dir()
SPEC_FILE = BUILD_DIR / "spec" / "FutureWorkerAuto.spec"
EMBEDDED_FILE = BUILD_DIR / "future_worker_auto_embedded.py"
SOURCE_FILE = ROOT / "FUTURE" / "server2" / "future_worker_auto.py"
CODE_TOKEN_FILE = ROOT / "FUTURE" / "server2" / "distributed_worker_token.local.txt"
TOKEN_FILE = ROOT / "programe_cache" / "future_whisper_server_2" / "distributed_worker_token.txt"
STABLE_TOKEN_FILE = Path(r"C:\server data") / "_future_distributed_worker_token.txt"
LEGACY_TOKEN_FILE = PROGRAME_ROOT / "programe_cache" / "future_whisper_server" / "distributed_worker_token.txt"
DIST_DIR = ROOT / "dist_worker"
WORK_DIR = BUILD_DIR / "build"
STAGING_DIST_DIR = BUILD_DIR / "dist_candidate"
LOG_DIR = ROOT / "run"
LOG_FILE = LOG_DIR / "future_worker_auto_rebuild_latest.err.log"
EXE_FILE = DIST_DIR / "FutureWorkerAuto.exe"
CANDIDATE_EXE_FILE = STAGING_DIST_DIR / "FutureWorkerAuto.exe"
STALE_ONEDIR_DIR = DIST_DIR / "FutureWorkerAuto"
LOCK_FILE = BUILD_DIR / "future_worker_auto_build.lock"


def log(message: str = "") -> None:
    print(message, flush=True)


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing {label}: {path}")


def read_build_token() -> str:
    env_token = str(os.environ.get("WORKER_TOKEN", "") or "").strip()
    if env_token:
        return env_token
    for path in (CODE_TOKEN_FILE, TOKEN_FILE, STABLE_TOKEN_FILE, LEGACY_TOKEN_FILE):
        if path.is_file():
            token = path.read_text(encoding="utf-8", errors="replace").strip()
            if token:
                return token
    return ""


def read_build_server_url() -> str:
    return str(os.environ.get("FUTURE_SERVER_URL", "") or "").strip().rstrip("/")


def patch_embedded_defaults(path: Path, server_url: str, token: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r'^DEFAULT_SERVER_URL\s*=\s*".*"$', f"DEFAULT_SERVER_URL = {server_url!r}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r'^DEFAULT_WORKER_TOKEN\s*=\s*".*"$', f"DEFAULT_WORKER_TOKEN = {token!r}", text, count=1, flags=re.MULTILINE)
    path.write_text(text, encoding="utf-8")


def module_main_data_args() -> list[str]:
    module_root = PROGRAME_ROOT / "module_main"
    if not module_root.exists():
        return []
    allowed_suffixes = {".json", ".txt", ".tsv", ".qmai", ".qme", ".svg"}
    args: list[str] = []
    for path in module_root.rglob("*"):
        try:
            if not path.is_file():
                continue
            parts = {part.lower() for part in path.parts}
            if "__pycache__" in parts or "logs" in parts:
                continue
            if path.suffix.lower() not in allowed_suffixes:
                continue
            rel_parent = path.parent.relative_to(module_root)
            args.extend(["--add-data", f"{path};{Path('module_main') / rel_parent}"])
        except OSError:
            continue
    return args


def future_server_parts_data_args() -> list[str]:
    source_root = ROOT / "FUTURE" / "server_parts"
    if not source_root.exists():
        return []
    return ["--add-data", f"{source_root};FUTURE/server_parts"]


def acquire_build_lock():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK_FILE.open("a+", encoding="utf-8")
    try:
        if sys.platform == "win32":
            try:
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                log("FutureWorkerAuto build is already running. Stop it first or wait for it to finish.")
                lock_handle.close()
                return None
        else:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                log("FutureWorkerAuto build is already running. Stop it first or wait for it to finish.")
                lock_handle.close()
                return None
        lock_handle.seek(0)
        lock_handle.truncate()
        lock_handle.write(str(__import__("os").getpid()))
        lock_handle.flush()
        return lock_handle
    except Exception:
        lock_handle.close()
        raise


def release_build_lock(lock_handle) -> None:
    if not lock_handle:
        return
    try:
        if sys.platform == "win32":
            try:
                lock_handle.seek(0)
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    finally:
        lock_handle.close()


# Added 2026-07-14: prevents accidental onedir worker output from being mistaken for the real onefile build.
def remove_stale_onedir_output() -> None:
    if not STALE_ONEDIR_DIR.exists():
        return
    resolved = STALE_ONEDIR_DIR.resolve()
    if resolved.parent != DIST_DIR.resolve() or resolved.name != "FutureWorkerAuto":
        raise RuntimeError(f"Refuse to remove unexpected worker output path: {resolved}")
    shutil.rmtree(resolved, ignore_errors=True)


# Added 2026-07-22: reject a onefile archive if any embedded entry cannot be decompressed.
def validate_onefile_archive(path: Path) -> dict:
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(path))
    extracted_bytes = 0
    for name in archive.toc:
        data = archive.extract(name)
        extracted_bytes += len(data or b"")
    return {
        "entries": len(archive.toc),
        "extracted_bytes": extracted_bytes,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


# Added 2026-07-22: imports critical runtime modules without connecting or taking the live worker lock.
def validate_frozen_runtime(path: Path) -> dict:
    result_path = BUILD_DIR / "future_worker_auto_self_test.json"
    result_path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["FUTURE_WORKER_SELF_TEST_OUTPUT"] = str(result_path)
    completed = subprocess.run(
        [str(path), "--self-test"],
        cwd=str(ROOT),
        env=env,
        timeout=120,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not result_path.is_file():
        raise RuntimeError(f"Frozen worker self-test failed with exit code {completed.returncode}.")
    payload = json.loads(result_path.read_text(encoding="utf-8", errors="replace") or "{}")
    if not payload.get("ok") or payload.get("client_version") != "2026-07-22":
        raise RuntimeError(f"Frozen worker self-test returned an invalid result: {payload}")
    return payload


def publish_validated_candidate(candidate: Path) -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DIST_DIR / ".FutureWorkerAuto.exe.new"
    temporary.unlink(missing_ok=True)
    shutil.copy2(candidate, temporary)
    os.replace(temporary, EXE_FILE)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    build_lock = acquire_build_lock()
    if build_lock is None:
        return 2

    try:
        require_file(SOURCE_FILE, "source file")

        log("Copy latest FutureWorkerAuto source...")
        shutil.copy2(SOURCE_FILE, EMBEDDED_FILE)
        token = read_build_token()
        if not token:
            log("")
            log("Missing worker token. Start Server 2 once so it creates:")
            log(str(TOKEN_FILE))
            log("Or set WORKER_TOKEN before running this build.")
            return 1
        server_url = read_build_server_url()
        patch_embedded_defaults(EMBEDDED_FILE, server_url, token)
        log("Embedded worker token: yes")
        log("Embedded server URL: " + (server_url or "auto-discover LAN"))
        remove_stale_onedir_output()
        if STAGING_DIST_DIR.exists():
            shutil.rmtree(STAGING_DIST_DIR)
        STAGING_DIST_DIR.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "FutureWorkerAuto",
            "--distpath",
            str(STAGING_DIST_DIR),
            "--workpath",
            str(WORK_DIR),
            "--specpath",
            str(BUILD_DIR / "spec"),
            "--paths",
            str(ROOT),
            "--paths",
            str(PROGRAME_ROOT),
            "--hidden-import",
            "FUTURE.server2.future_distributed_worker_client",
            "--hidden-import",
            "future_lesson_builder_gui",
            "--hidden-import",
            "googletrans",
            "--collect-submodules",
            "FUTURE.server_parts",
            "--collect-submodules",
            "FUTURE.server2",
            "--collect-submodules",
            "module_main",
            "--collect-submodules",
            "googletrans",
            "--collect-data",
            "language_tags",
            "--collect-data",
            "langcodes",
            "--collect-data",
            "kokoro_onnx",
            "--collect-data",
            "espeakng_loader",
            *future_server_parts_data_args(),
            *module_main_data_args(),
            str(EMBEDDED_FILE),
        ]

        log("Building FutureWorkerAuto.exe...")
        log(f"Log is also saved to: {LOG_FILE}")
        log("")

        with LOG_FILE.open("w", encoding="utf-8", errors="replace") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                log_handle.write(line)
                log_handle.flush()
            return_code = process.wait()

        if return_code != 0:
            log("")
            log(f"Build failed with exit code {return_code}. Check: {LOG_FILE}")
            return return_code

        if not CANDIDATE_EXE_FILE.is_file():
            log("")
            log(f"Build finished but candidate exe was not found: {CANDIDATE_EXE_FILE}")
            return 1

        log("Validating every embedded archive entry...")
        archive_result = validate_onefile_archive(CANDIDATE_EXE_FILE)
        log(f"Archive valid: {archive_result['entries']} entries, SHA-256 {archive_result['sha256']}")
        log("Running frozen runtime self-test...")
        runtime_result = validate_frozen_runtime(CANDIDATE_EXE_FILE)
        log(f"Runtime valid: client {runtime_result['client_version']}, IPv4 transport ready")
        publish_validated_candidate(CANDIDATE_EXE_FILE)

        log("")
        log("Build complete:")
        log(str(EXE_FILE))
        return 0
    finally:
        release_build_lock(build_lock)


if __name__ == "__main__":
    raise SystemExit(main())
