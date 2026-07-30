# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def cloudflared_path() -> Path:
    candidates = [
        PROGRAME_ROOT / "tools" / "cloudflared" / "Future Tunnel.exe",
        PROGRAME_ROOT / "Future Tunnel.exe",
        PROGRAME_ROOT / "tools" / "cloudflared" / "cloudflared.exe",
        PROGRAME_ROOT / "cloudflared.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for item in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(item) / "cloudflared.exe"
        if candidate.is_file():
            return candidate
    return Path("")

def cloudflared_config_path() -> Path:
    return Path.home() / ".cloudflared" / "config.yml"

def cloudflared_tunnel_uuid(tunnel_name: str) -> str:
    name = normalize_cloudflare_tunnel_name(tunnel_name)
    if not name or os.name != "nt":
        return ""
    try:
        result = subprocess.run(
            [str(cloudflared_path()), "tunnel", "info", name],
            cwd=str(PROGRAME_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            **subprocess_hidden_kwargs(),
        )
    except Exception:
        return ""
    text = clean(result.stdout)
    match = (
        re.search(r"\bID:\s*([0-9a-fA-F-]{36})\b", text)
        or re.search(r"\bYour tunnel ([0-9a-fA-F-]{36})\b", text)
        or re.search(r"\b([0-9a-fA-F-]{36})\b", text)
    )
    return clean(match.group(1)) if match else ""

def write_cloudflared_named_config(tunnel_name: str, hostname: str) -> Path:
    tunnel_uuid = cloudflared_tunnel_uuid(tunnel_name)
    if not tunnel_uuid:
        raise RuntimeError(f"Khong xac dinh duoc tunnel ID cho '{clean(tunnel_name)}'.")
    credentials_path = Path.home() / ".cloudflared" / f"{tunnel_uuid}.json"
    if not credentials_path.is_file():
        raise RuntimeError(f"Khong tim thay cloudflared credentials: {credentials_path}")
    config_path = cloudflared_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                f"tunnel: {tunnel_uuid}",
                f"credentials-file: {credentials_path.as_posix()}",
                "ingress:",
                f"  - hostname: {normalize_cloudflare_public_hostname(hostname)}",
                "    service: http://127.0.0.1:8877",
                "  - service: http_status:404",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def cloudflared_config_path() -> Path:
    return Path.home() / ".cloudflared" / "config.yml"


def cloudflared_command_text_error(result: subprocess.CompletedProcess) -> str:
    text = clean(f"{result.stderr or ''} {result.stdout or ''}")
    if "Cannot determine default origin certificate path" in text or "cert.pem" in text:
        text = f"{text} | Hay chay: cloudflared tunnel login"
    return text or f"cloudflared exited with code {result.returncode}"


def run_cloudflared_setup_command(exe: Path, args: list[str], timeout: int = 45) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(exe), *args],
        cwd=str(PROGRAME_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        **subprocess_hidden_kwargs(),
    )


def cloudflared_windows_service_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "try { $s = Get-Service -Name cloudflared -ErrorAction Stop; if ($s.Status -eq 'Running') { '1' } } catch {}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            **subprocess_hidden_kwargs(),
        )
        return clean(result.stdout) == "1"
    except Exception:
        return False


def cloudflared_named_tunnel_process_running(tunnel_name: str, origin_url: str = "") -> bool:
    name = normalize_cloudflare_tunnel_name(tunnel_name)
    origin = clean(origin_url)
    if not name or os.name != "nt":
        return False
    script = (
        "$name=$env:FUTURE_TUNNEL_NAME; "
        "$origin=$env:FUTURE_TUNNEL_ORIGIN; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "$_.Name -in @('cloudflared.exe','Future Tunnel.exe') "
        "-and $_.CommandLine -like ('*tunnel*run*' + $name + '*') "
        "-and ([string]::IsNullOrWhiteSpace($origin) -or $_.CommandLine -like ('*' + $origin + '*') -or $_.CommandLine -like '*--config*') "
        "} | Select-Object -First 1 -ExpandProperty ProcessId"
    )
    env = os.environ.copy()
    env["FUTURE_TUNNEL_NAME"] = name
    env["FUTURE_TUNNEL_ORIGIN"] = origin
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=env,
            **subprocess_hidden_kwargs(),
        )
        return clean(result.stdout).isdigit()
    except Exception:
        return False

def cloudflared_quick_tunnel_process_running(origin_url: str = "") -> bool:
    origin = clean(origin_url)
    if not origin or os.name != "nt":
        return False
    script = (
        "$origin=$env:FUTURE_TUNNEL_ORIGIN; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "$_.Name -in @('cloudflared.exe','Future Tunnel.exe') "
        "-and $_.CommandLine -like '*tunnel*--url*' "
        "-and $_.CommandLine -like ('*' + $origin + '*') "
        "} | Select-Object -First 1 -ExpandProperty ProcessId"
    )
    env = os.environ.copy()
    env["FUTURE_TUNNEL_ORIGIN"] = origin
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=env,
            **subprocess_hidden_kwargs(),
        )
        return clean(result.stdout).isdigit()
    except Exception:
        return False


def start_future_cloudflared_task(tunnel_name: str, origin_url: str = "") -> bool:
    if os.name != "nt":
        return False
    name = normalize_cloudflare_tunnel_name(tunnel_name)
    script = (
        "$task='FutureCloudflaredTunnel'; "
        "try { "
        "  $t = Get-ScheduledTask -TaskName $task -ErrorAction Stop; "
        "  Start-ScheduledTask -TaskName $task -ErrorAction Stop; "
        "  Start-Sleep -Seconds 4; "
        "  '1' "
        "} catch { '0' }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            **subprocess_hidden_kwargs(),
        )
        if clean(result.stdout) != "1":
            return False
    except Exception:
        return False
    return cloudflared_named_tunnel_process_running(name, origin_url)


def ensure_named_cloudflare_tunnel(exe: Path, tunnel_name: str, hostname: str) -> None:
    name = normalize_cloudflare_tunnel_name(tunnel_name)
    host = normalize_cloudflare_public_hostname(hostname)
    if not host:
        raise RuntimeError("Cloudflare domain khong hop le.")
    info = run_cloudflared_setup_command(exe, ["tunnel", "info", name], timeout=25)
    if info.returncode != 0:
        created = run_cloudflared_setup_command(exe, ["tunnel", "create", name], timeout=60)
        if created.returncode != 0:
            raise RuntimeError(f"Khong tao duoc Cloudflare Tunnel '{name}': {cloudflared_command_text_error(created)}")
    routed = run_cloudflared_setup_command(exe, ["tunnel", "route", "dns", "--overwrite-dns", name, host], timeout=60)
    if routed.returncode != 0:
        routed = run_cloudflared_setup_command(exe, ["tunnel", "route", "dns", "-f", name, host], timeout=60)
    if routed.returncode != 0:
        routed = run_cloudflared_setup_command(exe, ["tunnel", "route", "dns", name, host], timeout=60)
    if routed.returncode != 0:
        route_error = cloudflared_command_text_error(routed)
        if "record with that host already exists" not in route_error.lower():
            raise RuntimeError(f"Khong dang ky duoc domain '{host}' vao tunnel '{name}': {route_error}")


def tunnel_settings_changed(previous: dict, current: dict) -> bool:
    before_host = clean(previous.get("cloudflare_public_hostname", ""))
    after_host = clean(current.get("cloudflare_public_hostname", ""))
    before_name = clean(previous.get("cloudflare_tunnel_name", ""))
    after_name = clean(current.get("cloudflare_tunnel_name", ""))
    return before_host != after_host or before_name != after_name


def restart_tunnel_after_settings_change(previous: dict, current: dict) -> None:
    if not tunnel_settings_changed(previous, current):
        return
    origin = clean(TUNNEL_ORIGIN_URL)
    if not origin or SHUTDOWN_DONE or SERVER_STATE.get("shutdown_requested"):
        return
    if clean(SERVER_STATE.get("tunnel_status", "")) == "disabled":
        return

    def runner():
        stop_tunnel_process()
        start_cloudflare_tunnel(origin)

    threading.Thread(target=runner, daemon=True).start()


def _is_current_tunnel_process(process: subprocess.Popen, generation: int) -> bool:
    with TUNNEL_LOCK:
        return process is TUNNEL_PROCESS and int(generation or 0) == int(TUNNEL_GENERATION or 0) and not SHUTDOWN_DONE


def _read_tunnel_stream(pipe, stream_name: str, process: subprocess.Popen, generation: int) -> None:
    global TUNNEL_RESTART_ATTEMPTS
    public_pattern = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")
    try:
        for line in iter(pipe.readline, ""):
            text = clean(line)
            if not text:
                continue
            match = public_pattern.search(text)
            is_nonfatal_dns_warning = (
                "Failed to initialize DNS local resolver" in text
                or "Failed to refresh DNS local resolver" in text
            )
            is_transient_proxy_warning = "http2: stream closed" in text and bool(SERVER_STATE.get("public_app_url"))
            if match:
                public_url = match.group(0).rstrip("/")
                if _is_current_tunnel_process(process, generation):
                    with TUNNEL_LOCK:
                        TUNNEL_RESTART_ATTEMPTS = 0
                    SERVER_STATE.update(
                        {
                            "public_url": public_url,
                            "public_app_url": f"{public_url}/login",
                            "tunnel_status": "ready",
                            "tunnel_error": "",
                        }
                    )
                print(f"Future public app: {public_url}/login", flush=True)
            elif SERVER_STATE.get("tunnel_mode") == "named" and SERVER_STATE.get("public_url") and "registered" in text.lower():
                if _is_current_tunnel_process(process, generation):
                    with TUNNEL_LOCK:
                        TUNNEL_RESTART_ATTEMPTS = 0
                    public_url = clean(SERVER_STATE.get("public_url", "")).rstrip("/")
                    SERVER_STATE.update(
                        {
                            "public_url": public_url,
                            "public_app_url": f"{public_url}/login" if public_url else "",
                            "tunnel_status": "ready",
                            "tunnel_error": "",
                        }
                    )
            elif "ERR " in text or " error=" in text.lower():
                if _is_current_tunnel_process(process, generation):
                    if (
                        ((is_nonfatal_dns_warning or is_transient_proxy_warning) and SERVER_STATE.get("public_app_url"))
                        or clean(SERVER_STATE.get("tunnel_status", "")) == "ready"
                    ):
                        SERVER_STATE.update({"tunnel_error": ""})
                    else:
                        SERVER_STATE.update({"tunnel_error": text})
            display_stream = stream_name
            if text.startswith("INF "):
                display_stream = "info"
            elif (is_nonfatal_dns_warning or is_transient_proxy_warning) and SERVER_STATE.get("public_app_url"):
                display_stream = "warn"
            print(f"[cloudflared:{display_stream}] {text}", flush=True)
    except Exception as exc:
        if _is_current_tunnel_process(process, generation):
            SERVER_STATE.update({"tunnel_error": str(exc)})


def _schedule_tunnel_restart(origin_url: str, reason: str = "") -> None:
    global TUNNEL_RESTART_TIMER, TUNNEL_RESTART_ATTEMPTS
    origin = clean(origin_url or TUNNEL_ORIGIN_URL)
    if not origin or SHUTDOWN_DONE or SERVER_STATE.get("shutdown_requested"):
        return
    with TUNNEL_LOCK:
        if TUNNEL_RESTART_TIMER and TUNNEL_RESTART_TIMER.is_alive():
            return
        TUNNEL_RESTART_ATTEMPTS += 1
        delay = min(TUNNEL_MAX_RESTART_DELAY_SECONDS, max(2, 2 ** min(TUNNEL_RESTART_ATTEMPTS, 5)))
        SERVER_STATE.update(
            {
                "tunnel_status": "restarting",
                "tunnel_error": f"{clean(reason) or 'cloudflared exited'} | retry in {delay}s",
                "public_url": "",
                "public_app_url": "",
            }
        )

        def runner():
            global TUNNEL_RESTART_TIMER
            with TUNNEL_LOCK:
                TUNNEL_RESTART_TIMER = None
            if SHUTDOWN_DONE or SERVER_STATE.get("shutdown_requested"):
                return
            start_cloudflare_tunnel(origin)

        TUNNEL_RESTART_TIMER = threading.Timer(delay, runner)
        TUNNEL_RESTART_TIMER.daemon = True
        TUNNEL_RESTART_TIMER.start()


def _watch_tunnel_process(process: subprocess.Popen, generation: int, origin_url: str) -> None:
    try:
        code = process.wait()
        if not _is_current_tunnel_process(process, generation):
            return
        with TUNNEL_LOCK:
            global TUNNEL_PROCESS
            if process is TUNNEL_PROCESS:
                TUNNEL_PROCESS = None
                close_tunnel_job_handle()
        if SERVER_STATE.get("tunnel_status") != "stopping" and not SERVER_STATE.get("shutdown_requested"):
            _schedule_tunnel_restart(origin_url, f"cloudflared exited with code {code}")
    except Exception as exc:
        if _is_current_tunnel_process(process, generation):
            with TUNNEL_LOCK:
                if process is TUNNEL_PROCESS:
                    TUNNEL_PROCESS = None
                    close_tunnel_job_handle()
            _schedule_tunnel_restart(origin_url, str(exc))


def subprocess_hidden_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


def read_pid_file(path: Path) -> int:
    try:
        raw = clean(path.read_text(encoding="utf-8-sig"))
        return int(raw) if raw.isdigit() else 0
    except Exception:
        return 0


def write_pid_file(path: Path, pid: int) -> None:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, str(int(pid or 0)), encoding="utf-8")
    except Exception as exc:
        SERVER_STATE["last_error"] = f"Cannot write pid file: {exc}"


def command_line_for_pid(pid: int) -> str:
    pid = int(pid or 0)
    if pid <= 0:
        return ""
    if os.name == "nt":
        script = (
            "$pidValue=$env:FUTURE_TARGET_PID; "
            "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=$pidValue\" -ErrorAction SilentlyContinue; "
            "if($p){$p.CommandLine}"
        )
        env = os.environ.copy()
        env["FUTURE_TARGET_PID"] = str(pid)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                env=env,
                **subprocess_hidden_kwargs(),
            )
            return clean(result.stdout)
        except Exception:
            return ""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def parent_pid_for_pid(pid: int) -> int:
    pid = int(pid or 0)
    if pid <= 0:
        return 0
    if os.name == "nt":
        script = (
            "$pidValue=$env:FUTURE_TARGET_PID; "
            "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=$pidValue\" -ErrorAction SilentlyContinue; "
            "if($p){$p.ParentProcessId}"
        )
        env = os.environ.copy()
        env["FUTURE_TARGET_PID"] = str(pid)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                env=env,
                **subprocess_hidden_kwargs(),
            )
            raw = clean(result.stdout)
            return int(raw) if raw.isdigit() else 0
        except Exception:
            return 0
    try:
        return int(os.getppid())
    except Exception:
        return 0


def current_server_protected_pids() -> set[int]:
    pids = {int(os.getpid())}
    cursor = int(os.getpid())
    for _ in range(8):
        parent = parent_pid_for_pid(cursor)
        if parent <= 0 or parent in pids:
            break
        pids.add(parent)
        cursor = parent
    return pids


def is_recorded_future_server_pid(pid: int) -> bool:
    pid = int(pid or 0)
    if pid <= 0 or pid in current_server_protected_pids():
        return False
    command_line = command_line_for_pid(pid)
    if not command_line:
        return False
    return future_server_command_line_matches(command_line)


def future_server_command_line_matches(command_line: str) -> bool:
    text = clean(command_line).lower().replace("\\", "/")
    if not text:
        return False
    if future_persistent_worker_command_line_matches(text):
        return False
    return bool(re.search(
        r'(?i)(?:^|\s)(?:"(?:[^"]*[\\/])?(?:pythonw?|py)(?:\d+(?:\.\d+)*)?\.exe"|(?:[^\s"]*[\\/])?(?:pythonw?|py)(?:\d+(?:\.\d+)*)?(?:\.exe)?)'
        r'(?:\s+-[^\s"]+)*'
        r'\s+(?:"[^"]*(?:future_server(?:_2)?|run_server_2)\.py"|[^\s"]*(?:future_server(?:_2)?|run_server_2)\.py)(?:\s|$)',
        text,
    ))


# Added 2026-07-08: keeps detached STT/voice/process workers out of dashboard close/old-server cleanup.
def future_persistent_worker_command_line_matches(command_line: str) -> bool:
    text = clean(command_line).lower().replace("\\", "/")
    if not text:
        return False
    return any(
        marker in text
        for marker in (
            "future_stt_worker.py",
            "future_stt_worker_2.py",
            "future_voice_worker.py",
            "future_voice_worker_2.py",
            "future_process_worker.py",
            "future_process_worker_2.py",
            "future_whisper_server.py",
        )
    )


def list_other_future_server_processes() -> list[dict]:
    current_pid = os.getpid()
    protected_pids = current_server_protected_pids()
    rows: list[dict] = []
    if os.name == "nt":
        script = (
            "$rows = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            "Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and ($_.CommandLine -match '(?i)(FUTURE_SERVER(?:_2)?\\.py|run_server_2\\.py)') } | "
            "Select-Object ProcessId,CommandLine; "
            "$rows | ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                **subprocess_hidden_kwargs(),
            )
            raw = clean(result.stdout)
            if raw:
                payload = json.loads(raw)
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    pid = int(item.get("ProcessId", 0) or 0)
                    command_line = clean(item.get("CommandLine", ""))
                    if pid > 0 and pid not in protected_pids and future_server_command_line_matches(command_line):
                        rows.append({"pid": pid, "command_line": command_line})
        except Exception as exc:
            stt_debug_log("future_server_process_scan_failed", error=str(exc))
    for path in (SERVER_PID_FILE, SERVER_PREVIOUS_PID_FILE):
        pid = read_pid_file(path)
        if pid and pid not in protected_pids and is_recorded_future_server_pid(pid) and not any(row.get("pid") == pid for row in rows):
            rows.append({"pid": pid, "command_line": command_line_for_pid(pid), "source": path.name})
    rows.sort(key=lambda row: int(row.get("pid", 0) or 0))
    return rows


def future_server_port_from_command_line(command_line: str = "") -> int:
    text = clean(command_line)
    if not text:
        return 0
    match = re.search(r"(?:^|\s)--port(?:=|\s+)(\d{2,5})(?:\s|$)", text)
    if not match:
        return 8765
    try:
        port = int(match.group(1))
    except Exception:
        return 0
    return port if 1 <= port <= 65535 else 0


def request_future_server_soft_shutdown(port: int, pid: int = 0) -> dict:
    port = int(port or 0)
    if port <= 0:
        return {"ok": False, "reason": "missing_port"}
    session = f"kill-old-{os.getpid()}-{int(pid or 0)}-{secrets.token_hex(4)}"
    base_url = f"http://127.0.0.1:{port}"
    body = json.dumps({"session": session}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    try:
        urlopen(Request(f"{base_url}/dashboard/open", data=body, headers=headers, method="POST"), timeout=0.75).read()
        urlopen(Request(f"{base_url}/dashboard/shutdown", data=body, headers=headers, method="POST"), timeout=0.75).read()
        return {"ok": True, "port": port}
    except Exception as exc:
        return {"ok": False, "port": port, "error": str(exc)}


def kill_other_future_servers() -> dict:
    killed: list[dict] = []
    failed: list[dict] = []
    soft_shutdown: list[dict] = []
    flush_result = flush_future_runtime_caches()
    protected_pids = current_server_protected_pids()
    for row in list_other_future_server_processes():
        pid = int(row.get("pid", 0) or 0)
        if pid <= 0 or pid in protected_pids:
            continue
        command_line = clean(row.get("command_line", ""))
        port = future_server_port_from_command_line(command_line)
        soft_result = request_future_server_soft_shutdown(port, pid) if port else {"ok": False, "reason": "missing_port"}
        row["soft_shutdown"] = soft_result
        soft_shutdown.append({"pid": pid, **soft_result})
        if soft_result.get("ok"):
            time.sleep(1.25)
            if not command_line_for_pid(pid):
                killed.append({**row, "soft": True})
                continue
        try:
            terminate_process_only(pid)
            killed.append(row)
        except Exception as exc:
            failed.append({"pid": pid, "error": str(exc), "command_line": clean(row.get("command_line", ""))})
    killed_pids = {int(row.get("pid", 0) or 0) for row in killed}
    failed_pids = {int(row.get("pid", 0) or 0) for row in failed}
    stale_pid_files: list[dict] = []
    for path in (SERVER_PID_FILE, SERVER_PREVIOUS_PID_FILE):
        pid = read_pid_file(path)
        if not pid or pid in protected_pids:
            if pid and path == SERVER_PREVIOUS_PID_FILE:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
            continue
        if pid in killed_pids:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            continue
        if pid in failed_pids:
            continue
        command_line = command_line_for_pid(pid)
        if not command_line or not future_server_command_line_matches(command_line):
            try:
                path.unlink(missing_ok=True)
                stale_pid_files.append({"pid": pid, "source": path.name})
            except Exception as exc:
                failed.append({"pid": pid, "error": f"Cannot clear stale pid file {path.name}: {exc}", "command_line": command_line})
    try:
        write_pid_file(SERVER_PID_FILE, os.getpid())
    except Exception:
        pass
    return {
        "current_pid": os.getpid(),
        "protected_pids": sorted(protected_pids),
        "flushed_current": flush_result,
        "soft_shutdown": soft_shutdown,
        "killed": killed,
        "failed": failed,
        "stale_pid_files": stale_pid_files,
    }


# Added 2026-07-07: dashboard panic button closes Server 2 processes and tunnel for a clean relaunch.
def list_future_runtime_processes_for_clean_close() -> list[dict]:
    rows: list[dict] = []
    current_pid = int(os.getpid())
    if os.name == "nt":
        root_text = str(PROGRAME_ROOT).replace("\\", "\\\\")
        script = (
            "$root=$env:FUTURE_CLEAN_ROOT; "
            "$rows = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            "Where-Object { $_.CommandLine -and ("
            "($_.Name -match '^(python|pythonw|py)\\.exe$' -and $_.CommandLine -match '(?i)(FUTURE_SERVER(?:_2)?\\.py|run_server_2\\.py)') "
            "-or ($_.Name -in @('cloudflared.exe','Future Tunnel.exe') -and $_.CommandLine -match '(?i)\\btunnel\\b' -and ($_.CommandLine -match 'future-whisper' -or $_.CommandLine -match '127\\.0\\.0\\.1:(8877|8765)'))"
            ") } | Select-Object ProcessId,Name,CommandLine; "
            "$rows | ConvertTo-Json -Compress"
        )
        env = os.environ.copy()
        env["FUTURE_CLEAN_ROOT"] = root_text
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                env=env,
                **subprocess_hidden_kwargs(),
            )
            raw = clean(result.stdout)
            if raw:
                payload = json.loads(raw)
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    pid = int(item.get("ProcessId", 0) or 0)
                    if pid <= 0:
                        continue
                    rows.append({
                        "pid": pid,
                        "name": clean(item.get("Name", "")),
                        "command_line": clean(item.get("CommandLine", "")),
                        "current": pid == current_pid,
                    })
        except Exception as exc:
            stt_debug_log("future_runtime_clean_scan_failed", error=str(exc))
    for pid, label in (
        (read_pid_file(SERVER_PID_FILE), SERVER_PID_FILE.name),
        (read_pid_file(SERVER_PREVIOUS_PID_FILE), SERVER_PREVIOUS_PID_FILE.name),
    ):
        if pid and not any(int(row.get("pid", 0) or 0) == int(pid) for row in rows):
            command_line = command_line_for_pid(pid)
            if future_persistent_worker_command_line_matches(command_line):
                continue
            rows.append({"pid": int(pid), "name": label, "command_line": command_line, "source": label, "current": int(pid) == current_pid})
    rows = [row for row in rows if not future_persistent_worker_command_line_matches(clean(row.get("command_line", "")))]
    rows.sort(key=lambda row: (0 if bool(row.get("current")) else 1, int(row.get("pid", 0) or 0)))
    return rows


def clean_close_all_future_runtime(reason: str = "dashboard_clean_close_all") -> dict:
    flush_result = flush_future_runtime_caches()
    current_pid = int(os.getpid())
    rows = list_future_runtime_processes_for_clean_close()
    killed: list[dict] = []
    failed: list[dict] = []
    current_row = None
    for row in rows:
        pid = int(row.get("pid", 0) or 0)
        if pid <= 0:
            continue
        if pid == current_pid:
            current_row = row
            continue
        try:
            if future_runtime_clean_row_is_tunnel(row):
                terminate_process_tree(pid)
            else:
                terminate_process_only(pid)
            killed.append(row)
        except Exception as exc:
            failed.append({"pid": pid, "error": str(exc), "command_line": clean(row.get("command_line", ""))})
    for path in (SERVER_PID_FILE, SERVER_PREVIOUS_PID_FILE):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
    SERVER_STATE["shutdown_requested"] = True
    SERVER_STATE["shutdown_reason"] = clean(reason) or "dashboard_clean_close_all"
    stt_debug_log("future_runtime_clean_close_all", killed=[row.get("pid") for row in killed], failed=failed)
    return {
        "current_pid": current_pid,
        "current": current_row or {"pid": current_pid, "current": True},
        "flushed_current": flush_result,
        "killed": killed,
        "failed": failed,
        "will_exit_current": True,
    }


def schedule_clean_close_all_future_runtime(reason: str = "dashboard_clean_close_all", delay: float = 0.35) -> None:
    def runner() -> None:
        if delay > 0:
            time.sleep(delay)
        result = clean_close_all_future_runtime(reason)
        print(f"Future clean close all requested: {result}", flush=True)
        try:
            stop_server_data_manifest_watchdog()
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=runner, daemon=True, name="future-clean-close-all").start()


def stop_recorded_future_server(pid: int) -> bool:
    pid = int(pid or 0)
    if pid in current_server_protected_pids() or not is_recorded_future_server_pid(pid):
        return False
    # Updated 2026-07-09: stopping a stale Server 2 PID must not sweep detached STT/voice workers.
    terminate_process_only(pid)
    return True


def register_current_server_pid() -> None:
    current_pid = os.getpid()
    previous_pid = read_pid_file(SERVER_PID_FILE)
    if previous_pid and previous_pid != current_pid:
        write_pid_file(SERVER_PREVIOUS_PID_FILE, previous_pid)
        SERVER_STATE["previous_pid"] = previous_pid
    write_pid_file(SERVER_PID_FILE, current_pid)
    SERVER_STATE["pid"] = current_pid


def remove_current_server_pid_file() -> None:
    current_pid = os.getpid()
    try:
        if read_pid_file(SERVER_PID_FILE) == current_pid:
            SERVER_PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def stop_previous_server_from_pid_file() -> int:
    stopped = 0
    seen: set[int] = set()
    protected_pids = current_server_protected_pids()
    for path in (SERVER_PID_FILE, SERVER_PREVIOUS_PID_FILE):
        pid = read_pid_file(path)
        if not pid or pid in protected_pids or pid in seen:
            continue
        seen.add(pid)
        if stop_recorded_future_server(pid):
            stopped = pid
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
    return stopped


def create_kill_on_close_job():
    if os.name != "nt":
        return None
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = kernel32.SetInformationJobObject(
            wintypes.HANDLE(job),
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            kernel32.CloseHandle(wintypes.HANDLE(job))
            return None
        return job
    except Exception:
        return None


def attach_process_to_kill_job(process: subprocess.Popen) -> None:
    global TUNNEL_JOB_HANDLE
    if os.name != "nt" or not process:
        return
    job = create_kill_on_close_job()
    if not job:
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ok = kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(process._handle)))
        if not ok:
            kernel32.CloseHandle(wintypes.HANDLE(job))
            return
        TUNNEL_JOB_HANDLE = job
    except Exception:
        try:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(wintypes.HANDLE(job))
        except Exception:
            pass


def close_tunnel_job_handle() -> None:
    global TUNNEL_JOB_HANDLE
    job = TUNNEL_JOB_HANDLE
    TUNNEL_JOB_HANDLE = None
    if os.name != "nt" or not job:
        return
    try:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(wintypes.HANDLE(job))
    except Exception:
        pass


def keep_tunnel_process_on_server_exit() -> bool:
    raw = clean(os.environ.get("FUTURE_KEEP_TUNNEL_ON_RESTART", "1")).lower()
    return raw not in {"0", "false", "no", "off"}


# Added 2026-07-08: closes one Python server process without sweeping persistent worker children.
def terminate_process_only(pid: int) -> None:
    pid = int(pid or 0)
    if pid <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                **subprocess_hidden_kwargs(),
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def terminate_process_tree(pid: int) -> None:
    pid = int(pid or 0)
    if pid <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                **subprocess_hidden_kwargs(),
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


# Added 2026-07-08: clean-close uses tree termination only for tunnel processes, not Python workers.
def future_runtime_clean_row_is_tunnel(row: dict | None) -> bool:
    if not isinstance(row, dict):
        return False
    text = f"{clean(row.get('name', ''))} {clean(row.get('command_line', ''))}".lower()
    return "cloudflared" in text or "future tunnel.exe" in text


def cleanup_cloudflared_by_origin(origin_url: str, exclude_pid: int = 0) -> None:
    origin = clean(origin_url)
    if not origin or os.name != "nt":
        return
    script = (
        "$origin=$env:FUTURE_TUNNEL_ORIGIN; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('cloudflared.exe','Future Tunnel.exe') -and $_.CommandLine -like ('*' + $origin + '*') } | "
        "ForEach-Object { $_.ProcessId }"
    )
    env = os.environ.copy()
    env["FUTURE_TUNNEL_ORIGIN"] = origin
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            env=env,
            **subprocess_hidden_kwargs(),
        )
    except Exception:
        return
    for line in str(result.stdout or "").splitlines():
        raw = clean(line)
        if not raw.isdigit():
            continue
        pid = int(raw)
        if exclude_pid and pid == int(exclude_pid):
            continue
        terminate_process_tree(pid)


def stop_tunnel_process() -> None:
    global TUNNEL_PROCESS, TUNNEL_RESTART_TIMER
    with TUNNEL_LOCK:
        timer = TUNNEL_RESTART_TIMER
        TUNNEL_RESTART_TIMER = None
    if timer:
        try:
            timer.cancel()
        except Exception:
            pass
    process = TUNNEL_PROCESS
    TUNNEL_PROCESS = None
    if not process:
        return
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                terminate_process_tree(process.pid)
    except Exception:
        try:
            terminate_process_tree(process.pid)
        except Exception:
            pass
    close_tunnel_job_handle()


def stop_server_data_manifest_watchdog() -> None:
    with SERVER_DATA_MANIFEST_LOCK:
        observer = SERVER_DATA_MANIFEST_STATE.get("observer")
        paths_timer = SERVER_DATA_MANIFEST_STATE.get("paths_timer")
        watch_rescan_timer = SERVER_DATA_MANIFEST_STATE.get("watch_rescan_timer")
        SERVER_DATA_MANIFEST_STATE["observer"] = None
        SERVER_DATA_MANIFEST_STATE["watch_paths"] = []
        SERVER_DATA_MANIFEST_STATE["watcher_started"] = False
        SERVER_DATA_MANIFEST_STATE["paths_timer"] = None
        SERVER_DATA_MANIFEST_STATE["pending_paths"] = set()
        SERVER_DATA_MANIFEST_STATE["watch_rescan_timer"] = None
        SERVER_DATA_MANIFEST_STATE["watch_rescan_paths"] = set()
    if paths_timer and getattr(paths_timer, "is_alive", lambda: False)():
        try:
            paths_timer.cancel()
        except Exception:
            pass
    if watch_rescan_timer and getattr(watch_rescan_timer, "is_alive", lambda: False)():
        try:
            watch_rescan_timer.cancel()
        except Exception:
            pass
    if observer:
        try:
            observer.stop()
            observer.join(timeout=2)
        except Exception:
            pass


def cleanup_runtime() -> None:
    global SHUTDOWN_DONE
    with SHUTDOWN_LOCK:
        if SHUTDOWN_DONE:
            return
        SHUTDOWN_DONE = True
    stt_debug_log("server_cleanup", reason=SERVER_STATE.get("shutdown_reason", ""))
    SERVER_STATE["tunnel_status"] = "stopping"
    flush_future_runtime_caches()
    stop_server_data_manifest_watchdog()
    close_structure_read_pool()
    if keep_tunnel_process_on_server_exit():
        SERVER_STATE["tunnel_status"] = "kept_alive"
    else:
        stop_tunnel_process()
    remove_current_server_pid_file()


def flush_future_runtime_caches() -> dict:
    flushed: list[str] = []
    failed: list[dict] = []
    for name, args in (
        ("flush_space_progress_store", (True,)),
        ("flush_space_pdf_ai_runtime_stores", (True,)),
        ("flush_lesson_tasks_ram_cache", (True,)),
        ("flush_lesson_task_notices_ram_cache", (True,)),
        ("flush_lesson_last_file_all", ()),
        ("flush_chat_state_cache", (True,)),
        ("flush_shared_world_state_cache", (True,)),
        ("flush_shared_world_battle_state_cache", (True,)),
        ("flush_vocab_leaderboard_viewer_state", (True,)),
        ("flush_vocab_leaderboard_period_state", (True,)),
        ("compact_space_v_registry_sync_wal", (True,)),
        ("flush_server_database_legacy_exports", (True,)),
        ("flush_server_database_documents", (True,)),
        ("flush_server_database_writer", (True,)),
        ("backup_server_database", (True,)),
    ):
        func = globals().get(name)
        if not callable(func):
            continue
        try:
            func(*args)
            flushed.append(name)
        except Exception as exc:
            failed.append({"name": name, "error": str(exc)})
    try:
        # Added 2026-07-16: compacts Sound asset WAL into the shared JSON index during normal Server 2 flush/shutdown.
        from future_sound_asset_index import write_sound_asset_index_now
        write_sound_asset_index_now("runtime_flush")
        flushed.append("write_sound_asset_index_now")
    except Exception as exc:
        failed.append({"name": "write_sound_asset_index_now", "error": str(exc)})
    writer = globals().get("write_future_boot_snapshot")
    if callable(writer):
        try:
            writer("runtime_flush")
            flushed.append("write_future_boot_snapshot")
        except Exception as exc:
            failed.append({"name": "write_future_boot_snapshot", "error": str(exc)})
    return {"flushed": flushed, "failed": failed}


def request_server_shutdown(reason: str = "dashboard_closed", delay: float = 0.0) -> None:
    with SHUTDOWN_LOCK:
        if SERVER_STATE.get("shutdown_requested"):
            return
        SERVER_STATE["shutdown_requested"] = True
        SERVER_STATE["shutdown_reason"] = clean(reason) or "dashboard_closed"

    def runner():
        if delay > 0:
            time.sleep(delay)
        print(f"Future server shutdown requested: {SERVER_STATE.get('shutdown_reason')}", flush=True)
        stt_debug_log("server_shutdown_requested", reason=SERVER_STATE.get("shutdown_reason", ""))
        flush_future_runtime_caches()
        httpd = SERVER_HTTPD
        if httpd is not None:
            try:
                httpd.shutdown()
                return
            except Exception as exc:
                print(f"HTTP shutdown failed: {exc}", flush=True)
        cleanup_runtime()

    threading.Thread(target=runner, daemon=True).start()


def start_dashboard_watcher() -> None:
    global DASHBOARD_WATCHER_STARTED
    with DASHBOARD_LOCK:
        if DASHBOARD_WATCHER_STARTED:
            return
        DASHBOARD_WATCHER_STARTED = True

    def watcher():
        while not SHUTDOWN_DONE:
            time.sleep(0.5)
            should_shutdown = False
            with DASHBOARD_LOCK:
                close_requested_at = float(SERVER_STATE.get("dashboard_close_requested_at", 0) or 0)
                if close_requested_at and time.time() - close_requested_at >= DASHBOARD_SHUTDOWN_GRACE_SECONDS:
                    SERVER_STATE["dashboard_status"] = "closed"
                    should_shutdown = True
            if should_shutdown:
                request_server_shutdown("dashboard_closed")
                return

    threading.Thread(target=watcher, daemon=True).start()


def mark_dashboard_open(session_id: str) -> None:
    session_id = clean(session_id) or secrets.token_hex(8)
    with DASHBOARD_LOCK:
        now = time.time()
        retire_session = clean(SERVER_STATE.get("dashboard_retire_session", ""))
        retire_until = float(SERVER_STATE.get("dashboard_retire_until", 0) or 0)
        if retire_session and retire_until > now and session_id != retire_session:
            SERVER_STATE.update(
                {
                    "dashboard_status": "open",
                    "dashboard_session": retire_session,
                    "dashboard_close_requested_at": 0,
                }
            )
            return
        if retire_session and (retire_until <= now or session_id == retire_session):
            SERVER_STATE.update({"dashboard_retire_session": "", "dashboard_retire_until": 0})
        SERVER_STATE.update(
            {
                "dashboard_status": "open",
                "dashboard_session": session_id,
                "dashboard_last_seen": now,
                "dashboard_close_requested_at": 0,
            }
        )
    start_dashboard_watcher()


def mark_dashboard_ping(session_id: str) -> None:
    session_id = clean(session_id)
    with DASHBOARD_LOCK:
        now = time.time()
        retire_session = clean(SERVER_STATE.get("dashboard_retire_session", ""))
        retire_until = float(SERVER_STATE.get("dashboard_retire_until", 0) or 0)
        if retire_session and retire_until > now and session_id != retire_session:
            return
        if retire_session and (retire_until <= now or session_id == retire_session):
            SERVER_STATE.update({"dashboard_retire_session": "", "dashboard_retire_until": 0})
        current = clean(SERVER_STATE.get("dashboard_session", ""))
        if not current or current == session_id:
            SERVER_STATE.update(
                {
                    "dashboard_status": "open",
                    "dashboard_session": session_id or current,
                    "dashboard_last_seen": now,
                    "dashboard_close_requested_at": 0,
                }
            )


def keep_dashboard_session(session_id: str) -> None:
    session_id = clean(session_id)
    if not session_id:
        return
    now = time.time()
    with DASHBOARD_LOCK:
        SERVER_STATE.update(
            {
                "dashboard_status": "open",
                "dashboard_session": session_id,
                "dashboard_last_seen": now,
                "dashboard_close_requested_at": 0,
                "dashboard_retire_session": session_id,
                "dashboard_retire_until": now + DASHBOARD_RETIRE_OLD_SECONDS,
            }
        )
    start_dashboard_watcher()


def dashboard_control_response(session_id: str) -> dict:
    session_id = clean(session_id)
    with DASHBOARD_LOCK:
        now = time.time()
        current = clean(SERVER_STATE.get("dashboard_session", ""))
        status = clean(SERVER_STATE.get("dashboard_status", "not_open")) or "not_open"
        retire_session = clean(SERVER_STATE.get("dashboard_retire_session", ""))
        retire_until = float(SERVER_STATE.get("dashboard_retire_until", 0) or 0)
        if retire_session and retire_until > now:
            current = retire_session
        elif retire_session and retire_until <= now:
            SERVER_STATE.update({"dashboard_retire_session": "", "dashboard_retire_until": 0})
    should_close = bool(session_id and current and session_id != current)
    return {
        "dashboard_status": status,
        "dashboard_session": current,
        "dashboard_id": session_id,
        "close_dashboard": should_close,
        "close_reason": "superseded_dashboard" if should_close else "",
    }


def mark_dashboard_close(session_id: str) -> bool:
    session_id = clean(session_id)
    with DASHBOARD_LOCK:
        current = clean(SERVER_STATE.get("dashboard_session", ""))
        if not current or not session_id or current != session_id:
            return False
        SERVER_STATE.update(
            {
                "dashboard_status": "closing",
                "dashboard_close_requested_at": time.time(),
            }
        )
    start_dashboard_watcher()
    return True


def install_shutdown_cleanup(origin_url: str) -> None:
    def handle_shutdown(_signum=None, _frame=None):
        cleanup_runtime()
        raise SystemExit(0)

    atexit.register(cleanup_runtime)
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        try:
            signal.signal(signum, handle_shutdown)
        except Exception:
            pass


def start_cloudflare_tunnel(origin_url: str):
    global TUNNEL_PROCESS, TUNNEL_ORIGIN_URL, TUNNEL_GENERATION
    exe = cloudflared_path()
    settings = load_server_settings()
    public_hostname = clean(settings.get("cloudflare_public_hostname", ""))
    tunnel_name = normalize_cloudflare_tunnel_name(settings.get("cloudflare_tunnel_name", "future-whisper"))
    tunnel_mode = "named" if public_hostname else "quick"
    public_url = f"https://{public_hostname}" if public_hostname else ""
    if not exe or not exe.is_file():
        SERVER_STATE.update(
            {
                "tunnel_status": "missing",
                "tunnel_error": "cloudflared.exe is not installed. No public internet link is available to copy.",
            }
        )
        SERVER_STATE.update({"tunnel_mode": tunnel_mode, "tunnel_hostname": public_hostname, "tunnel_name": tunnel_name if public_hostname else ""})
        return None
    with TUNNEL_LOCK:
        if TUNNEL_PROCESS and TUNNEL_PROCESS.poll() is None:
            return TUNNEL_PROCESS
        TUNNEL_ORIGIN_URL = clean(origin_url)
        TUNNEL_GENERATION += 1
        generation = TUNNEL_GENERATION
        status = "restarting" if TUNNEL_RESTART_ATTEMPTS else "starting"
        SERVER_STATE.update(
            {
                "tunnel_status": status,
                "tunnel_error": "",
                "public_url": public_url,
                "public_app_url": f"{public_url}/login" if public_url else "",
                "tunnel_mode": tunnel_mode,
                "tunnel_hostname": public_hostname,
                "tunnel_name": tunnel_name if public_hostname else "",
            }
        )
    if not public_hostname and keep_tunnel_process_on_server_exit() and cloudflared_quick_tunnel_process_running(origin_url):
        SERVER_STATE.update(
            {
                "tunnel_status": "running",
                "tunnel_error": "",
                "public_url": clean(SERVER_STATE.get("public_url", "")),
                "public_app_url": clean(SERVER_STATE.get("public_app_url", "")),
                "tunnel_mode": tunnel_mode,
                "tunnel_hostname": public_hostname,
                "tunnel_name": "",
            }
        )
        return None
    if public_hostname and cloudflared_named_tunnel_process_running(tunnel_name, origin_url):
        SERVER_STATE.update(
            {
                "tunnel_status": "running",
                "tunnel_error": "",
                "public_url": public_url,
                "public_app_url": f"{public_url}/login",
                "tunnel_mode": tunnel_mode,
                "tunnel_hostname": public_hostname,
                "tunnel_name": tunnel_name,
            }
        )
        return None
    if public_hostname:
        try:
            write_cloudflared_named_config(tunnel_name, public_hostname)
            ensure_named_cloudflare_tunnel(exe, tunnel_name, public_hostname)
        except Exception as exc:
            SERVER_STATE.update(
                {
                    "tunnel_status": "setup_error",
                    "tunnel_error": str(exc),
                    "public_url": public_url,
                    "public_app_url": f"{public_url}/login",
                    "tunnel_mode": tunnel_mode,
                    "tunnel_hostname": public_hostname,
                    "tunnel_name": tunnel_name,
                }
            )
            return None
    try:
        env = os.environ.copy()
        env["FUTURE_SERVER2_PROCESS_ROLE"] = "tunnel"
        env["FUTURE_SERVER2_PROCESS_STATUS"] = "Future Server 2 - tunnel"
        command = (
            [str(exe), "tunnel", "--config", str(cloudflared_config_path()), "run", tunnel_name]
            if public_hostname
            else [str(exe), "tunnel", "--url", origin_url, "--protocol", "http2", "--loglevel", "info"]
        )
        process = subprocess.Popen(
            command,
            cwd=str(PROGRAME_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            **subprocess_hidden_kwargs(),
        )
    except Exception as exc:
        if public_hostname:
            SERVER_STATE.update(
                {
                    "tunnel_status": "setup_error",
                    "tunnel_error": str(exc),
                    "public_url": "",
                    "public_app_url": "",
                }
            )
        else:
            _schedule_tunnel_restart(origin_url, f"cannot start cloudflared: {exc}")
        return None
    with TUNNEL_LOCK:
        TUNNEL_PROCESS = process
    if not keep_tunnel_process_on_server_exit():
        attach_process_to_kill_job(process)
    threading.Thread(target=_read_tunnel_stream, args=(process.stdout, "out", process, generation), daemon=True).start()
    threading.Thread(target=_read_tunnel_stream, args=(process.stderr, "err", process, generation), daemon=True).start()
    threading.Thread(target=_watch_tunnel_process, args=(process, generation, origin_url), daemon=True).start()
    return process
