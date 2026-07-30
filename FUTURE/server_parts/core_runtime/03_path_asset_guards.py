# Loaded by FUTURE.server_parts.01_core_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def clean_path_value(value) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = text.replace("\\", "/").strip().strip("/")
    if not text:
        return ""
    # Added 2026-07-22: normalize each segment once; this helper is hot in progress/tree payloads.
    parts = []
    for raw_part in text.split("/"):
        part = raw_part.strip()
        if part:
            parts.append(part)
    return "/".join(parts)


def normalize_cloudflare_public_hostname(value) -> str:
    raw = clean(value).strip().strip("\"'").strip()
    if not raw:
        return ""
    candidate = raw if re.match(r"^[a-z][a-z0-9+.-]*://", raw, flags=re.IGNORECASE) else f"//{raw}"
    try:
        parsed = urlparse(candidate)
        host = clean(parsed.hostname or "")
    except Exception:
        host = ""
    if not host:
        host = raw.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0].rsplit(":", 1)[0]
    host = clean(host).strip(".").lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return ""
    try:
        ipaddress.ip_address(host)
        return ""
    except Exception:
        pass
    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        return ""
    labels = host.split(".")
    if len(labels) < 2 or len(host) > 253:
        return ""
    label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
    if not all(label_pattern.fullmatch(label or "") for label in labels):
        return ""
    return host


def normalize_cloudflare_tunnel_name(value) -> str:
    raw = clean(value) or clean(DEFAULT_SETTINGS.get("cloudflare_tunnel_name", "future-whisper"))
    raw = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-.")
    return raw[:80] or "future-whisper"


def path_is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def public_path_block_reason(path: Path, allow_future_html: bool = False) -> str:
    target = path.resolve()
    if allow_future_html and target == PUBLIC_FRONTEND_PATH:
        return ""
    lowered_name = target.name.lower()
    lowered_parts = {part.lower() for part in target.parts}
    if lowered_name in PUBLIC_SOURCE_NAMES:
        return "File he thong khong duoc phep tai cong khai."
    if lowered_parts.intersection(PUBLIC_SOURCE_PARTS):
        return "Thu muc he thong khong duoc phep tai cong khai."
    if target.suffix.lower() in PUBLIC_SOURCE_SUFFIXES:
        return "Loai file nay bi chan de bao ve ma nguon/server."
    protected_roots = (ROOT, PROGRAME_ROOT, RUNTIME_ROOT, SERVER_LOG_ROOT)
    if any(path_is_inside(target, root) for root in protected_roots):
        return "Duong dan nay nam trong vung ma nguon/runtime cua server."
    return ""


def assert_public_file_allowed(path: Path, allow_future_html: bool = False) -> None:
    reason = public_path_block_reason(path, allow_future_html=allow_future_html)
    if reason:
        raise RuntimeError(reason)


def server_asset_category(target: Path) -> str:
    for category, root in (
        ("Sound", SERVER_SOUND_DIR),
        ("Structure", SERVER_STRUCTURE_DIR),
        ("Picture", SERVER_PICTURE_DIR),
        ("Picture", NPC_TOP_DIR),
    ):
        if path_is_inside(target, root):
            return category
    return ""


def assert_server_asset_allowed(target: Path) -> None:
    category = server_asset_category(target)
    if not category:
        raise RuntimeError("Asset khong nam trong thu muc Sound, Structure hoac Picture.")
    suffix = target.suffix.lower()
    if suffix not in SERVER_ASSET_SUFFIXES.get(category, set()):
        raise RuntimeError("Loai asset nay khong duoc phep tai cong khai.")
    reason = public_path_block_reason(target)
    if reason:
        raise RuntimeError(reason)


def assert_chat_attachment_allowed(filename: str, mime: str = "") -> None:
    suffix = Path(str(filename or "")).suffix.lower()
    normalized_mime = clean(mime).split(";")[0].lower()
    if suffix in CHAT_ATTACHMENT_BLOCKED_SUFFIXES or normalized_mime in CHAT_ATTACHMENT_BLOCKED_MIMES:
        raise RuntimeError("Loai tep nay bi chan de bao ve ma nguon/server.")
