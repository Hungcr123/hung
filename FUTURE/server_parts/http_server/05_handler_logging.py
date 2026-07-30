# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

# Keep attribution deterministic and cheap: route labels avoid stack inspection,
# request-body parsing, and filesystem lookups on every access-log line.
ACCESS_LOG_ROUTE_SOURCES = {
    ("POST", "/auth/login"): "auth.login",
    "/auth/me": "auth.session",
    "/auth/username": "auth.username_lookup",
    "/frontend-version": "frontend.version_poll",
    "/settings": "settings.read",
    "/announcements": "announcements.read",
    "/server-data/tree-preload": "lesson_vault.tree_preload",
    "/server-data/login-preload": "lesson_vault.login_preload",
    "/server-data/list": "lesson_vault.folder_list",
    "/server-data/file": "lesson_vault.file_read",
    "/server-data/item-study": "lesson_vault.item_study",
    ("GET", "/server-data/last-file"): "navigation.last_file_read",
    ("POST", "/server-data/last-file"): "navigation.last_file_save",
    ("GET", "/lesson-tasks"): "space_task.load",
    ("POST", "/lesson-tasks"): "space_task.mutate",
    "/lesson-tasks/status": "space_task.status",
    ("GET", "/space-v/progress"): "space_v.progress_read",
    ("POST", "/space-v/progress"): "space_v.progress_save",
    ("GET", "/space-w/progress"): "space_w.progress_read",
    ("POST", "/space-w/progress"): "space_w.progress_save",
    ("GET", "/space-q/progress"): "space_q.progress_read",
    ("POST", "/space-q/progress"): "space_q.progress_save",
    ("GET", "/space-p/progress"): "space_p.progress_read",
    ("POST", "/space-p/progress"): "space_p.progress_save",
    ("GET", "/space-l/progress"): "space_l.progress_read",
    ("POST", "/space-l/progress"): "space_l.progress_save",
    ("GET", "/space-s/progress"): "space_s.progress_read",
    ("POST", "/space-s/progress"): "space_s.progress_save",
    ("GET", "/space-pdf/progress"): "space_pdf.progress_read",
    ("POST", "/space-pdf/progress"): "space_pdf.progress_save",
    ("GET", "/space-picture/progress"): "space_picture.progress_read",
    ("POST", "/space-picture/progress"): "space_picture.progress_save",
    "/inventory": "inventory.read",
    "/vocab/registry": "vocab.registry",
    "/vocab/leaderboard": "vocab.leaderboard",
}
ACCESS_LOG_SOURCE_PREFIXES = (
    "auth_", "client_", "frontend_", "lesson_", "navigation_", "offline_",
    "pdf_", "picture_", "server_", "space_", "ui_", "vocab_",
)


def access_log_client_source(self, value: str) -> str:
    candidate = clean(value).lower()
    if not candidate or len(candidate) > 64 or not re.fullmatch(r"[a-z][a-z0-9_]*", candidate):
        return ""
    if candidate.startswith(self.ACCESS_LOG_SOURCE_PREFIXES):
        return candidate
    return ""


def access_log_route_source(self, method: str, parsed_path: str) -> str:
    safe_method = clean(method or "request").upper() or "REQUEST"
    route = self.ACCESS_LOG_ROUTE_SOURCES.get((safe_method, parsed_path))
    if not route:
        route = self.ACCESS_LOG_ROUTE_SOURCES.get(parsed_path)
    if route:
        return route
    safe_method = safe_method.lower()
    safe_path = re.sub(r"[^a-zA-Z0-9/_-]+", "_", clean(parsed_path or "/"))
    return f"http.{safe_method}.{safe_path.strip('/').replace('/', '.') or 'root'}"


# Added 2026-07-01: annotates access logs with the authenticated user behind each poll.
def request_log_identity(self) -> str:
    username = ""
    target = ""
    source = ""
    route = ""
    lesson_id = ""
    file_hint = ""
    try:
        token = clean(self.headers.get("Authorization", ""))
        if not token:
            token = clean(self.headers.get("X-Future-Auth", ""))
        if not token:
            token = request_cookie_value(self.headers.get("Cookie", ""), AUTH_COOKIE_NAME)
        if token:
            session = self.auth_session()
            if session:
                username = clean(session.get("username", ""))
    except Exception:
        username = ""
    if not username:
        try:
            if self.is_local_admin_request():
                username = "server"
        except Exception:
            username = ""
    try:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        target = clean(
            (query.get("user") or query.get("username") or query.get("message_user") or [""])[0]
        )
        source = self.access_log_client_source(
            (query.get("client_source") or query.get("source") or [""])[0]
            or self.headers.get("X-Future-Source", "")
        )
        lesson_id = clean((query.get("lesson_id") or query.get("identity") or query.get("file_id") or [""])[0])
        raw_file_hint = clean((query.get("path") or query.get("file") or query.get("lesson") or [""])[0])
        if raw_file_hint:
            file_hint = re.sub(r"\s+", " ", raw_file_hint.rsplit("/", 1)[-1]).strip()[:120]
        route = self.access_log_route_source(getattr(self, "command", ""), parsed.path)
        ui_action = re.sub(r"[^a-z0-9_.-]", "", clean((query.get("ui_action") or [""])[0]).lower())[:40]
        trigger = re.sub(r"[^a-z0-9_.-]", "", clean((query.get("trigger") or [""])[0]).lower())[:32]
        retry = clean((query.get("retry") or [""])[0])
        from_page = clean((query.get("from_page") or [""])[0])
        to_page = clean((query.get("to_page") or [""])[0])
    except Exception:
        target = ""
        source = ""
        route = ""
        ui_action = ""
        trigger = ""
        retry = ""
        from_page = ""
        to_page = ""
    label = f"user={username or '-'}"
    if target and target != username:
        label += f" target={target}"
    label += f" src={source or route or 'http.unknown'}"
    if source and route and source != route:
        label += f" route={route}"
    if ui_action:
        label += f" action={ui_action}"
    if trigger:
        label += f" trigger={trigger}"
    if retry in {"0", "1"}:
        label += f" retry={retry}"
    if from_page.isdigit() and to_page.isdigit():
        label += f" page={from_page}->{to_page}"
    if lesson_id:
        label += f" lesson={lesson_id[:120]}"
    if file_hint:
        label += f" file={file_hint}"
    return label


# Added 2026-07-15: enables real ANSI colors in the Windows Server 2 console instead of printing raw escape codes.
ACCESS_LOG_WINDOWS_VT_READY = False

def enable_windows_virtual_terminal_for_access_logs(self) -> bool:
    handler_cls = type(self)
    if getattr(handler_cls, "ACCESS_LOG_WINDOWS_VT_READY", False):
        return True
    setattr(handler_cls, "ACCESS_LOG_WINDOWS_VT_READY", True)
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        enable_virtual_terminal = 0x0004
        for handle_id in (-11, -12):
            handle = kernel32.GetStdHandle(handle_id)
            if not handle:
                continue
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | enable_virtual_terminal)
        return True
    except Exception:
        return False

# Added 2026-07-01: colors access logs by authenticated username for easier multi-user scanning.
def access_log_color_enabled(self) -> bool:
    flag = clean(os.environ.get("FUTURE_ACCESS_LOG_COLOR", "1")).lower()
    return flag not in {"0", "false", "no", "off"} and clean(os.environ.get("NO_COLOR", "")) == ""


def access_log_username_from_identity(self, identity: str = "") -> str:
    match = re.search(r"\buser=([^\s]+)", str(identity or ""))
    return clean(match.group(1) if match else "")


def access_log_color_for_username(self, username: str = "") -> str:
    user = clean(username)
    if not user or user == "-":
        return "\033[2;37m"
    if user.lower() == "server":
        return "\033[3;97m"
    palette = [
        "\033[92m", "\033[32m", "\033[96m", "\033[94m",
        "\033[93m", "\033[95m", "\033[91m",
        "\033[38;5;82m", "\033[38;5;118m", "\033[38;5;45m",
        "\033[38;5;219m", "\033[38;5;208m", "\033[38;5;141m",
    ]
    digest = hashlib.blake2s(user.lower().encode("utf-8"), digest_size=2).digest()
    index = int.from_bytes(digest, "big") % len(palette)
    return palette[index]


def color_access_log_line(self, identity: str, line: str) -> str:
    if not self.access_log_color_enabled():
        return line
    self.enable_windows_virtual_terminal_for_access_logs()
    username = self.access_log_username_from_identity(identity)
    color = self.access_log_color_for_username(username)
    return f"{color}{line}\033[0m"


def should_log_access_request(self) -> bool:
    try:
        parsed_path = urlparse(self.path).path.rstrip('/') or '/'
        if parsed_path.startswith('/distributed-worker/') and not truthy(SERVER_STATE.get('dashboard_worker_access_logs_visible', True), True):
            return False
    except Exception:
        return True
    return True

def log_message(self, fmt, *args):
    if not self.should_log_access_request():
        return
    try:
        identity = self.request_log_identity()
    except Exception:
        identity = "user=?"
    line = f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {identity} {fmt % args}"
    try:
        print(self.color_access_log_line(identity, line), flush=True)
    except UnicodeEncodeError:
        safe_line = self.color_access_log_line(identity, line).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        try:
            sys.stdout.buffer.write((safe_line + "\n").encode("utf-8", errors="replace"))
            sys.stdout.flush()
        except Exception:
            pass

