# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# Added 2026-07-09: keeps translate/QmDict/phonetic/spaCy workers hot across Server 2 restarts.

PROCESS_WORKER_SUPPORTED_QUEUES = {"translate", "qmdict", "phonetic", "spacy"}


def process_worker_request(path: str, payload: dict | None = None, timeout: float = 8.0, method: str = "POST") -> dict:
    url = f"{PROCESS_WORKER_URL}{path if path.startswith('/') else '/' + path}"
    data = None
    headers = {"Accept": "application/json"}
    if method.upper() != "GET":
        data = json_bytes(payload or {})
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(url, data=data, headers=headers, method=method.upper())
    with urlopen(request, timeout=max(0.8, float(timeout or 8.0))) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8-sig") if raw else "{}")
    if not isinstance(parsed, dict):
        raise RuntimeError("Invalid process worker response.")
    if parsed.get("ok") is False:
        raise RuntimeError(clean(parsed.get("error", "")) or "Process worker error.")
    return parsed


def sync_process_worker_state(payload: dict | None) -> None:
    if not isinstance(payload, dict):
        return
    SERVER_STATE.update(
        {
            "process_worker_url": PROCESS_WORKER_URL,
            "process_worker_ready": bool(payload.get("ready")),
            "process_worker_loading": bool(payload.get("loading")),
            "process_worker_pid": int(payload.get("pid", 0) or 0),
            "process_worker_last_error": clean(payload.get("last_error", "")),
            "process_worker_jobs": int(payload.get("jobs", 0) or 0),
            "process_worker_last_ms": int(payload.get("last_ms", 0) or 0),
        }
    )


def process_worker_health(timeout: float = 1.5) -> dict | None:
    if not PROCESS_WORKER_ENABLED:
        return None
    try:
        payload = process_worker_request("/health", method="GET", timeout=timeout)
        sync_process_worker_state(payload)
        return payload
    except Exception as exc:
        SERVER_STATE.update({"process_worker_ready": False, "process_worker_loading": False, "process_worker_last_error": str(exc)})
        return None


def write_process_worker_pid(pid: int) -> None:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_text(PROCESS_WORKER_PID_FILE, str(int(pid or 0)), encoding="utf-8")
    except Exception:
        pass


def start_detached_process_worker_process(cmd: list[str]) -> int:
    launch_cmd = list(cmd)
    if launch_cmd:
        launch_cmd[0] = _windowless_python_executable()
    worker_env = os.environ.copy()
    worker_env["FUTURE_SERVER2_PROCESS_ROLE"] = "process-worker"
    worker_env["FUTURE_SERVER2_PROCESS_STATUS"] = "Future Server 2 - process-worker"
    if os.name == "nt":
        hidden_kwargs = subprocess_hidden_kwargs()
        hidden_kwargs["creationflags"] = (
            int(hidden_kwargs.get("creationflags", 0))
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        )
        try:
            process = subprocess.Popen(
                launch_cmd,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                env=worker_env,
                **hidden_kwargs,
            )
            return int(process.pid or 0)
        except Exception:
            return 0
    process = subprocess.Popen(
        launch_cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=worker_env,
        start_new_session=True,
    )
    return int(process.pid or 0)


def ensure_process_worker_process(preload: bool = False) -> dict:
    if not PROCESS_WORKER_ENABLED:
        raise RuntimeError("Process worker is disabled.")
    health = process_worker_health(timeout=0.8)
    if health:
        if preload:
            try:
                process_worker_request("/warm", {"kinds": ["translate", "qmdict", "phonetic", "spacy"]}, timeout=1.2)
            except Exception as exc:
                SERVER_STATE.update({"process_worker_last_error": str(exc)})
        return health
    if not PROCESS_WORKER_SCRIPT.is_file():
        raise RuntimeError(f"Process worker script not found: {PROCESS_WORKER_SCRIPT}")
    cmd = [
        sys.executable or "python",
        "-B",
        str(PROCESS_WORKER_SCRIPT),
        "--host",
        PROCESS_WORKER_HOST,
        "--port",
        str(PROCESS_WORKER_PORT),
    ]
    if preload:
        cmd.append("--warm")
    worker_pid = start_detached_process_worker_process(cmd)
    write_process_worker_pid(worker_pid)
    SERVER_STATE.update({"process_worker_pid": worker_pid, "process_worker_url": PROCESS_WORKER_URL, "process_worker_loading": bool(preload)})
    for _attempt in range(20):
        time.sleep(0.15)
        health = process_worker_health(timeout=0.6)
        if health:
            return health
    return {"ok": True, "started": True, "pid": worker_pid, "ready": False, "loading": bool(preload)}


def process_worker_task_supported(queue_name: str, fn) -> bool:
    if not PROCESS_WORKER_ENABLED:
        return False
    if clean(queue_name).lower() not in PROCESS_WORKER_SUPPORTED_QUEUES:
        return False
    module_name = clean(getattr(fn, "__module__", ""))
    function_name = clean(getattr(fn, "__name__", ""))
    return bool(module_name == "FUTURE.server_parts.worker_jobs.heavy_language_jobs" and function_name)


def run_process_worker_task(queue_name: str, label: str, fn, args: tuple | list = (), kwargs: dict | None = None, timeout: float | None = None):
    ensure_process_worker_process(preload=False)
    payload = process_worker_request(
        "/run",
        {
            "queue": clean(queue_name),
            "label": clean(label),
            "module": clean(getattr(fn, "__module__", "")),
            "function": clean(getattr(fn, "__name__", "")),
            "args": list(args or []),
            "kwargs": kwargs if isinstance(kwargs, dict) else {},
        },
        timeout=max(5.0, float(timeout or 60.0)) + 5.0,
    )
    sync_process_worker_state(payload)
    return payload.get("result")


def warm_process_worker_task(queue_name: str, kind: str = "", timeout: float | None = None) -> dict:
    ensure_process_worker_process(preload=False)
    payload = process_worker_request(
        "/warm",
        {"kinds": [clean(kind) or clean(queue_name)]},
        timeout=max(5.0, float(timeout or 45.0)) + 5.0,
    )
    sync_process_worker_state(payload)
    return payload
