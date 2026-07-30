from __future__ import annotations

import ctypes
import ipaddress
import json
import multiprocessing
import msvcrt
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from FUTURE.server2.future_distributed_worker_client import CLIENT_VERSION, clean, main as worker_main


DEFAULT_SERVER_URL = ""
DEFAULT_WORKER_TOKEN = ""
DEFAULT_PORT = 8877
HTTP_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 FutureWorkerAuto/2026.07 Safari/537.36"
LAST_SERVER_URL = ""
SINGLE_INSTANCE_LOCK_HANDLE = None
SINGLE_INSTANCE_MUTEX_HANDLE = None
DEFAULT_MAX_INSTANCES_PER_MACHINE = 2


# Added 2026-07-22: validates the frozen worker before a build is allowed to replace the installed EXE.
def run_frozen_self_test() -> int:
    output_path = clean(os.environ.get("FUTURE_WORKER_SELF_TEST_OUTPUT", ""))
    payload = {
        "ok": False,
        "client_version": CLIENT_VERSION,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": str(Path(sys.executable).resolve()),
    }
    try:
        import future_ipv4_http  # noqa: F401
        import future_lesson_builder_gui  # noqa: F401
        from PyQt5 import QtCore  # noqa: F401

        payload.update({
            "ok": True,
            "ipv4_transport": True,
            "lesson_builder": True,
            "pyqt5": True,
        })
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        os.replace(temporary, target)
    return 0 if payload.get("ok") else 1


def config_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    target = Path(base) / "QM-Tech" / "FutureWorker"
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_saved_server() -> str:
    path = config_dir() / "auto_worker_config.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace") or "{}")
        return clean(payload.get("server_url", ""))
    except Exception:
        return ""


# Added 2026-07-09: lets installed auto workers recover token/server settings from worker_config.cmd.
def read_worker_cmd_config() -> dict:
    config: dict[str, str] = {}
    candidates = [
        Path.cwd() / "worker_config.cmd",
        Path(__file__).resolve().parent / "worker_config.cmd",
        config_dir() / "worker_config.cmd",
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / "worker_config.cmd")
    for path in candidates:
        try:
            if not path.is_file():
                continue
            for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line.lower().startswith("set "):
                    continue
                body = line[4:].strip()
                if "=" not in body:
                    continue
                key, value = body.split("=", 1)
                key = clean(key).upper()
                if key and key not in config:
                    config[key] = clean(value)
        except Exception:
            continue
    return config


def worker_auto_config_value(name: str, default: str = "") -> str:
    key = clean(name).upper()
    if not key:
        return clean(default)
    return clean(os.environ.get(key, "")) or clean(read_worker_cmd_config().get(key, "")) or clean(default)


# Added 2026-07-11: applies every worker_config.cmd variable before the embedded worker client starts.
def apply_worker_cmd_environment() -> None:
    for key, value in read_worker_cmd_config().items():
        if key and value and key not in os.environ:
            os.environ[key] = value


def save_server(url: str) -> None:
    if not clean(url):
        return
    path = config_dir() / "auto_worker_config.json"
    try:
        path.write_text(json.dumps({"server_url": clean(url), "saved_at": int(time.time())}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# Added 2026-07-07: removes stale/old worker instances before this dashboard owns the mutex.
def terminate_duplicate_worker_processes() -> None:
    # Added 2026-07-10: avoid PowerShell process probes that can flash/reloop on classroom PCs.
    return None


# Added 2026-07-07: keeps one Auto worker app per Windows user; lanes inside the worker provide concurrency.
def future_worker_allow_multiple_instances() -> bool:
    value = clean(os.environ.get("FUTURE_WORKER_ALLOW_MULTIPLE", "")).lower()
    return value in {"1", "true", "yes", "on", "multi"}


# Added 2026-07-07: keeps double-clicked Auto workers from multiplying beyond the server/dashboard cap.
def future_worker_max_instances_per_machine() -> int:
    raw = clean(os.environ.get("FUTURE_WORKER_MAX_INSTANCES", ""))
    try:
        amount = int(float(raw)) if raw else DEFAULT_MAX_INSTANCES_PER_MACHINE
    except Exception:
        amount = DEFAULT_MAX_INSTANCES_PER_MACHINE
    return max(1, min(32, amount))


def count_running_future_worker_auto_instances() -> int:
    # Added 2026-07-10: mutex/file lock is the source of truth; do not spawn PowerShell to count.
    return 1


def local_instance_limit_allows_start() -> bool:
    if not future_worker_allow_multiple_instances():
        return count_running_future_worker_auto_instances() <= 1
    return count_running_future_worker_auto_instances() <= future_worker_max_instances_per_machine()


def acquire_single_instance_lock() -> bool:
    global SINGLE_INSTANCE_LOCK_HANDLE, SINGLE_INSTANCE_MUTEX_HANDLE
    if future_worker_allow_multiple_instances():
        return True
    try:
        mutex_name = "Local\\QMTechFutureWorkerAutoSingleInstance"
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if handle:
            SINGLE_INSTANCE_MUTEX_HANDLE = handle
            if ctypes.windll.kernel32.GetLastError() == 183:
                return False
    except Exception:
        pass
    try:
        lock_path = config_dir() / "FutureWorkerAuto.lock"
        handle = open(lock_path, "a+b")
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return False
        SINGLE_INSTANCE_LOCK_HANDLE = handle
        return True
    except Exception:
        return True


# Added 2026-07-07: lets the local worker dashboard send notes/log snippets to Server 2.
def post_worker_log_to_server(message: str) -> dict:
    server_url = normalize_server_url(worker_auto_config_value("SERVER_URL", DEFAULT_SERVER_URL) or read_saved_server() or LAST_SERVER_URL)
    token = worker_auto_config_value("WORKER_TOKEN", DEFAULT_WORKER_TOKEN)
    if not server_url:
        raise RuntimeError("No Server 2 URL is known yet.")
    if not token:
        raise RuntimeError("Missing worker token.")
    payload = {
        "token": token,
        "worker_id": clean(os.environ.get("FUTURE_WORKER_ID", "")) or socket.gethostname(),
        "name": socket.gethostname(),
        "owner_user": clean(os.environ.get("FUTURE_WORKER_OWNER", "")) or clean(os.environ.get("USERNAME", "")) or socket.gethostname(),
        "message": str(message or "").strip(),
    }
    if not payload["message"]:
        raise RuntimeError("No log text to send.")
    request = Request(
        server_url + "/distributed-worker/log",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": HTTP_USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        raw = response.read(65536)
    result = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    if not isinstance(result, dict) or result.get("ok") is False:
        raise RuntimeError(clean(result.get("error", "")) or "Server rejected worker log.")
    return result


def normalize_server_url(url: str) -> str:
    raw = clean(url).rstrip("/")
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except Exception:
        return raw
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    return raw


def url_healthy(url: str, timeout: float = 0.45) -> bool:
    target = normalize_server_url(url)
    if not target:
        return False
    try:
        request = Request(target + "/health", headers={"User-Agent": HTTP_USER_AGENT, "Accept": "application/json,text/plain,*/*"})
        with urlopen(request, timeout=timeout) as response:
            data = response.read(65536)
        text = data.decode("utf-8", errors="replace")
        if "future-whisper" in text and '"ok"' in text:
            return True
        try:
            payload = json.loads(text or "{}")
            return bool(payload.get("ok")) and clean(payload.get("service", "")) == "future-whisper"
        except Exception:
            return False
    except Exception:
        return False


def local_ipv4_addresses() -> list[str]:
    seen = set()
    out = []
    for host in (socket.gethostname(), socket.getfqdn(), "localhost"):
        try:
            infos = socket.gethostbyname_ex(host)[2]
        except Exception:
            infos = []
        for item in infos:
            try:
                ip = ipaddress.ip_address(item)
            except ValueError:
                continue
            if ip.version == 4 and not ip.is_loopback and item not in seen:
                seen.add(item)
                out.append(item)
    return out


# Added 2026-07-07: lets the standalone worker find Server 2 on the same Wi-Fi without user setup.
def discover_server_url(log=None) -> str:
    global LAST_SERVER_URL
    candidates = [
        clean(os.environ.get("FUTURE_SERVER_URL", "")),
        clean(DEFAULT_SERVER_URL),
        read_saved_server(),
        f"http://127.0.0.1:{DEFAULT_PORT}",
    ]
    lan_candidates = []
    local_ips = local_ipv4_addresses()
    if log:
        log("Local IPv4: " + (", ".join(local_ips) if local_ips else "none"))
    for ip_text in local_ipv4_addresses():
        try:
            network = ipaddress.ip_network(ip_text + "/24", strict=False)
        except ValueError:
            continue
        if log:
            log(f"Scanning LAN adapter range {network} on port {DEFAULT_PORT}...")
        for ip in network.hosts():
            lan_candidates.append(f"http://{ip}:{DEFAULT_PORT}")
    seen = set()
    for url in candidates:
        key = normalize_server_url(url)
        if not key or key in seen:
            continue
        seen.add(key)
        if log:
            log(f"Checking {key}/health")
        if url_healthy(key):
            save_server(key)
            if log:
                log(f"Found Future Server 2: {key}")
            LAST_SERVER_URL = key
            return key
    scan_targets = []
    for url in lan_candidates:
        key = normalize_server_url(url)
        if key and key not in seen:
            seen.add(key)
            scan_targets.append(key)
    if scan_targets:
        with ThreadPoolExecutor(max_workers=64) as pool:
            future_map = {pool.submit(url_healthy, url): url for url in scan_targets}
            for future in as_completed(future_map):
                url = future_map[future]
                try:
                    ok = bool(future.result())
                except Exception:
                    ok = False
                if ok:
                    save_server(url)
                    if log:
                        log(f"Found Future Server 2: {url}")
                    LAST_SERVER_URL = url
                    return url
    if log:
        log("No Future Server 2 found on localhost or current Wi-Fi range.")
    return ""


class QueueWriter:
    def __init__(self, write_func):
        self.write_func = write_func

    def write(self, value):
        text = str(value or "")
        if text.strip():
            self.write_func(text.rstrip())

    def flush(self):
        return None


def run_worker_forever(log=print) -> int:
    apply_worker_cmd_environment()
    token = worker_auto_config_value("WORKER_TOKEN", DEFAULT_WORKER_TOKEN)
    if not token:
        log("Missing worker token in this build.")
        return 3
    owner = worker_auto_config_value("FUTURE_WORKER_OWNER") or clean(os.environ.get("USERNAME", "")) or socket.gethostname()
    while True:
        server_url = discover_server_url(log)
        if not server_url:
            log("Retrying discovery in 5 seconds. Check server is running, same Wi-Fi/Ethernet LAN, and firewall allows port 8877.")
            time.sleep(5)
            continue
        globals()["LAST_SERVER_URL"] = server_url
        log(f"Connecting worker as '{owner}' to {server_url}")
        sys.argv = [
            sys.argv[0],
            "--server",
            server_url,
            "--token",
            token,
            "--owner-user",
            owner,
            "--capabilities",
            worker_auto_config_value("FUTURE_WORKER_CAPABILITIES", "translate,tts,stt,gemini"),
            "--max-jobs",
            worker_auto_config_value("FUTURE_WORKER_MAX_JOBS", "translate=16,tts=16,stt=16,gemini=16"),
            "--poll-seconds",
            worker_auto_config_value("FUTURE_WORKER_POLL_SECONDS", "1"),
        ]
        try:
            return worker_main()
        except KeyboardInterrupt:
            log("Worker stopped.")
            return 0
        except Exception as exc:
            log(f"Worker crashed: {exc}")
            log(traceback.format_exc())
            log("Restarting worker in 5 seconds...")
            time.sleep(5)


# Added 2026-07-07: PyQt5 local dashboard so classroom machines show connection errors instead of closing silently.
def run_dashboard() -> int:
    try:
        from PyQt5.QtCore import QTimer
        from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
        from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
    except Exception:
        return run_worker_forever(print)

    events: queue.Queue[str] = queue.Queue()

    def log(message: object = "") -> None:
        text = str(message or "").rstrip()
        if text:
            events.put(f"[{time.strftime('%H:%M:%S')}] {text}")

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = QWidget()
    window.setWindowTitle("QM-Tech Future Worker")
    window.resize(860, 540)
    window.setMinimumSize(680, 420)
    window.setStyleSheet(
        """
        QWidget { background: #101418; color: #eef7f2; font-family: Segoe UI; }
        QLabel#title { font-size: 20px; font-weight: 800; color: #ff9f35; }
        QLabel#status { color: #ffbf5a; font-weight: 700; padding: 6px 0; }
        QTextEdit { background: #070a0d; border: 1px solid #2b3b45; border-radius: 8px; padding: 8px; color: #d8fff1; }
        QPushButton { background: #1b2a31; border: 1px solid #3d5b65; border-radius: 7px; padding: 8px 12px; font-weight: 700; }
        QPushButton:hover { border-color: #ff9f35; color: #ffcf73; }
        """
    )
    layout = QVBoxLayout(window)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    title = QLabel("QM-Tech Future Worker")
    title.setObjectName("title")
    layout.addWidget(title)
    status = QLabel("Starting...")
    status.setObjectName("status")
    status.setWordWrap(True)
    layout.addWidget(status)
    log_box = QTextEdit()
    log_box.setReadOnly(True)
    log_box.setFont(QFont("Consolas", 10))
    layout.addWidget(log_box, 1)
    send_row = QHBoxLayout()
    send_input = QLineEdit()
    send_input.setPlaceholderText("Type a note for Server 2, or leave blank to send recent log...")
    send_log = QPushButton("Send log to server")
    send_row.addWidget(send_input, 1)
    send_row.addWidget(send_log)
    layout.addLayout(send_row)
    actions = QHBoxLayout()
    open_folder = QPushButton("Open log/config folder")
    clear_log = QPushButton("Clear log")
    warm_kokoro_vi = QPushButton("Warm Kokoro VI RAM")
    actions.addStretch(1)
    actions.addWidget(warm_kokoro_vi)
    actions.addWidget(clear_log)
    actions.addWidget(open_folder)
    layout.addLayout(actions)

    # Added 2026-07-14: color log lines by job/source while keeping the stable D worker dashboard base.
    def log_line_color(line: str) -> str:
        text = str(line or "")
        upper = text.upper()
        lower = text.lower()
        if "FAILED" in upper or "ERROR" in upper or "CRASH" in upper or "TRACEBACK" in upper:
            return "#ff6b86"
        if upper.startswith("TTS |") or " TTS |" in upper or "LOCAL KOKORO" in upper or "EDGE/MICROSOFT" in upper or "SOUNDOFTEXT" in upper:
            return "#70d6ff"
        if upper.startswith("STT |") or "FASTER-WHISPER" in upper:
            return "#c792ea"
        if upper.startswith("TRANSLATE |") or "GOOGLETRANS" in upper:
            return "#ffd166"
        if upper.startswith("GEMINI |"):
            return "#8df5a6"
        if upper.startswith("PHONEMIZE |"):
            return "#f7a8ff"
        if upper.startswith("WARM |") or " warm " in lower:
            return "#9be7c1"
        if "FOUND FUTURE SERVER 2" in upper or "CONNECTING WORKER" in upper:
            return "#7bd88f"
        if "SCANNING" in upper or "CHECKING" in upper:
            return "#9fb7c8"
        return "#d8fff1"

    def append_log(line: str) -> None:
        text = str(line or "")
        cursor = log_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(log_line_color(text)))
        cursor.insertText(text + "\n", fmt)
        log_box.setTextCursor(cursor)
        scrollbar = log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        if "Found Future Server 2" in text or "Connecting worker" in text or "job " in text or " | " in text:
            status.setText(text)
            status.setStyleSheet("color: #6cf0a4; font-weight: 800; padding: 6px 0;")
        elif "No Future Server 2" in text or "Retrying discovery" in text or "failed" in text.lower() or "crashed" in text.lower():
            status.setText(text)
            status.setStyleSheet("color: #ff7a90; font-weight: 800; padding: 6px 0;")

    def send_log_to_server() -> None:
        text = send_input.text().strip()
        if not text:
            text = log_box.toPlainText()[-12000:]
        send_log.setEnabled(False)
        try:
            result = post_worker_log_to_server(text)
            send_input.clear()
            log(f"Sent worker log to Server 2 ({int(result.get('stored', 0) or 0)} chars).")
        except Exception as exc:
            log(f"Send worker log failed: {exc}")
        finally:
            send_log.setEnabled(True)

    def warm_kokoro_vi_models() -> None:
        warm_kokoro_vi.setEnabled(False)
        def runner() -> None:
            try:
                apply_worker_cmd_environment()
                os.environ["FUTURE_WARM_ALL_KOKORO_VI"] = "1"
                os.environ["FUTURE_KOKORO_VI_IN_PROCESS"] = "1"
                os.environ["FUTURE_TTS_LOCAL_ONLY"] = "1"
                os.environ.setdefault("FUTURE_KOKORO_VI_DEVICE", "cpu")
                from FUTURE.server2.future_distributed_worker_client import mark_worker_feature, warm_worker_runtime

                log("Warming all Kokoro Vietnamese voices into RAM/cache...")
                result = warm_worker_runtime("tts", force=True)
                mark_worker_feature("tts_kokoro_vi_warm", True)
                try:
                    import future_lesson_builder_gui as builder  # type: ignore
                    runtime_count = len(getattr(builder, "_KOKORO_VI_ONNX_RUNTIMES", {}) or {})
                except Exception:
                    runtime_count = 0
                vi_payload = result.get("vi", {}) if isinstance(result, dict) else {}
                warmed_rows = vi_payload.get("warmed", []) if isinstance(vi_payload, dict) else []
                failed_rows = vi_payload.get("failed", []) if isinstance(vi_payload, dict) else []
                message = f"Kokoro Vietnamese warm ready: warmed {len(warmed_rows)} voice(s), RAM runtimes {runtime_count}, failed {len(failed_rows)}."
                log(message)
                try:
                    post_worker_log_to_server(message)
                except Exception as exc:
                    log(f"Warm status send failed: {exc}")
            except Exception as exc:
                log(f"Kokoro Vietnamese warm failed: {exc}")
                log(traceback.format_exc())
                try:
                    post_worker_log_to_server("Kokoro Vietnamese warm failed.",)
                except Exception:
                    pass
            finally:
                QTimer.singleShot(0, lambda: warm_kokoro_vi.setEnabled(True))

        threading.Thread(target=runner, name="future-worker-warm-kokoro-vi", daemon=True).start()

    def pump() -> None:
        while True:
            try:
                append_log(events.get_nowait())
            except queue.Empty:
                break

    def worker_thread() -> None:
        sys.stdout = QueueWriter(log)
        sys.stderr = QueueWriter(log)
        run_worker_forever(log)

    open_folder.clicked.connect(lambda: os.startfile(str(config_dir())))
    clear_log.clicked.connect(log_box.clear)
    warm_kokoro_vi.clicked.connect(warm_kokoro_vi_models)
    send_log.clicked.connect(send_log_to_server)
    send_input.returnPressed.connect(send_log_to_server)
    threading.Thread(target=worker_thread, name="future-worker-dashboard", daemon=True).start()
    log("PyQt5 dashboard started. Looking for Future Server 2...")
    timer = QTimer(window)
    timer.timeout.connect(pump)
    timer.start(150)
    window.show()
    return int(app.exec_())


def main() -> int:
    multiprocessing.freeze_support()
    if "--self-test" in sys.argv:
        return run_frozen_self_test()
    # Added 2026-07-10: stop duplicate/startup launches before they can open more windows.
    if not acquire_single_instance_lock():
        return 0
    if not local_instance_limit_allows_start():
        return 0
    # Added 2026-07-07: newest launch owns the visible dashboard and cleans stale background workers.
    terminate_duplicate_worker_processes()
    if "--no-dashboard" in sys.argv:
        sys.argv = [item for item in sys.argv if item != "--no-dashboard"]
        return run_worker_forever(print)
    return run_dashboard()


if __name__ == "__main__":
    raise SystemExit(main())
