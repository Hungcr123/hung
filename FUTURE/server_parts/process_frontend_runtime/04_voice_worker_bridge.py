# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Added 2026-07-07: keeps Kokoro/SOT/Edge voice work in a persistent worker across Server 2 restarts.


def voice_worker_request(path: str, payload: dict | None = None, timeout: float = 8.0, method: str = "POST") -> dict:
    url = f"{VOICE_WORKER_URL}{path if path.startswith('/') else '/' + path}"
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
        raise RuntimeError("Invalid voice worker response.")
    if parsed.get("ok") is False:
        raise RuntimeError(clean(parsed.get("error", "")) or "Voice worker error.")
    return parsed


def sync_voice_worker_state(payload: dict | None) -> None:
    if not isinstance(payload, dict):
        return
    SERVER_STATE.update(
        {
            "voice_worker_url": VOICE_WORKER_URL,
            "voice_worker_ready": bool(payload.get("ready")),
            "voice_worker_loading": bool(payload.get("loading")),
            "voice_worker_pid": int(payload.get("pid", 0) or 0),
            "voice_worker_last_error": clean(payload.get("last_error", "")),
            "voice_worker_last_voice": clean(payload.get("last_voice", "")),
            "voice_worker_last_ms": int(payload.get("last_ms", 0) or 0),
        }
    )


def voice_worker_health(timeout: float = 1.5) -> dict | None:
    if not VOICE_WORKER_ENABLED:
        return None
    try:
        payload = voice_worker_request("/health", method="GET", timeout=timeout)
        sync_voice_worker_state(payload)
        return payload
    except Exception as exc:
        SERVER_STATE.update({"voice_worker_ready": False, "voice_worker_loading": False, "voice_worker_last_error": str(exc)})
        return None


def write_voice_worker_pid(pid: int) -> None:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_text(VOICE_WORKER_PID_FILE, str(int(pid or 0)), encoding="utf-8")
    except Exception:
        pass


def start_detached_voice_worker_process(cmd: list[str]) -> int:
    launch_cmd = list(cmd)
    if launch_cmd:
        launch_cmd[0] = _windowless_python_executable()
    worker_env = os.environ.copy()
    worker_env["FUTURE_SERVER2_PROCESS_ROLE"] = "voice-worker"
    worker_env["FUTURE_SERVER2_PROCESS_STATUS"] = "Future Server 2 - voice-worker"
    if os.name == "nt":
        hidden_kwargs = subprocess_hidden_kwargs()
        # Added 2026-07-08: keep voice worker detached and RAM-warm across dashboard server closes.
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


def ensure_voice_worker_process(preload: bool = False, warm_model: bool = False) -> dict:
    if not VOICE_WORKER_ENABLED:
        raise RuntimeError("Voice worker is disabled.")
    health = voice_worker_health(timeout=0.8)
    if health:
        if preload or warm_model:
            try:
                voice_worker_request("/warm", {"model": bool(warm_model)}, timeout=1.2)
            except Exception as exc:
                SERVER_STATE.update({"voice_worker_last_error": str(exc)})
        return health
    if not VOICE_WORKER_SCRIPT.is_file():
        raise RuntimeError(f"Voice worker script not found: {VOICE_WORKER_SCRIPT}")
    cmd = [
        sys.executable or "python",
        "-B",
        str(VOICE_WORKER_SCRIPT),
        "--host",
        VOICE_WORKER_HOST,
        "--port",
        str(VOICE_WORKER_PORT),
    ]
    if preload:
        cmd.append("--warm")
    if warm_model:
        cmd.append("--warm-model")
    worker_pid = start_detached_voice_worker_process(cmd)
    write_voice_worker_pid(worker_pid)
    SERVER_STATE.update({"voice_worker_pid": worker_pid, "voice_worker_url": VOICE_WORKER_URL, "voice_worker_loading": bool(preload or warm_model)})
    for _attempt in range(20):
        time.sleep(0.15)
        health = voice_worker_health(timeout=0.6)
        if health:
            return health
    return {"ok": True, "started": True, "pid": worker_pid, "ready": False, "loading": bool(preload or warm_model)}


def synthesize_message_audio_via_voice_worker(text: str, voice_key: str, timeout: float | None = None) -> dict:
    ensure_voice_worker_process(preload=False)
    started_at = time.time()
    payload = voice_worker_request(
        "/synthesize",
        {"text": text, "voice": voice_key},
        timeout=max(30.0, float(timeout or VOICE_WORK_QUEUE.timeout_seconds or 0) or 0.0) + 30.0,
    )
    sync_voice_worker_state(payload)
    payload.setdefault("queue_position", 1)
    payload.setdefault("queue_wait_ms", 0)
    payload.setdefault("queue_process_ms", int(max(0.0, time.time() - started_at) * 1000))
    return payload
