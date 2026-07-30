# Loaded by FUTURE.server_parts.03_chat_paint_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def chat_safe_filename(value: object, fallback: str = "attachment") -> str:
    raw = Path(str(value or "")).name.strip()
    raw = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" .")
    if not raw:
        raw = fallback
    stem = Path(raw).stem[:72].strip(" .") or fallback
    suffix = Path(raw).suffix[:16]
    return f"{stem}{suffix}"


def chat_attachment_url(path: str, download: bool = False, name: str = "") -> str:
    query = f"/chat/attachment?path={quote_path_component(path)}"
    if name:
        query += f"&name={quote_path_component(name)}"
    return f"{query}&download=1" if download else query


def quote_path_component(value: str) -> str:
    from urllib.parse import quote

    return quote(str(value or ""), safe="")


def safe_ascii_header_filename(value: object, fallback: str = "file", limit: int = 140) -> str:
    raw = Path(str(value or "")).name.strip() or fallback
    raw = raw.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", raw).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = text[: max(8, int(limit or 140))].strip(" .")
    return text or fallback


def inline_content_disposition_filename(display_name: object, fallback: str = "file") -> str:
    safe_display = chat_safe_filename(display_name, fallback)
    ascii_name = safe_ascii_header_filename(safe_display, fallback)
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote_path_component(safe_display)}"


def chat_attachment_mime(filename: str, content_type: str = "") -> str:
    mime = clean(content_type).split(";")[0].lower()
    if not mime or mime == "application/octet-stream":
        guessed = mimetypes.guess_type(filename)[0]
        if guessed:
            mime = guessed.lower()
    return mime or "application/octet-stream"


def save_chat_attachment(username: str, upload: dict, sender: str = "user") -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    data = bytes(upload.get("data") or b"")
    if not data:
        raise RuntimeError("Tep dinh kem dang trong.")
    max_bytes = 32 * 1024 * 1024
    if len(data) > max_bytes:
        raise RuntimeError("Tep dinh kem vuot qua 32 MB.")
    original = chat_safe_filename(upload.get("filename", "attachment"))
    mime = chat_attachment_mime(original, upload.get("content_type", ""))
    assert_chat_attachment_allowed(original, mime)
    suffix = Path(original).suffix.lower()[:12]
    stored_name = f"{int(time.time())}-{uuid.uuid4().hex}{suffix}"
    sender_folder = "admin" if clean(sender).lower() == "admin" else "user"
    target_dir = CHAT_ATTACHMENT_DIR / username / sender_folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = (target_dir / stored_name).resolve()
    root = CHAT_ATTACHMENT_DIR.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Duong dan dinh kem khong hop le.") from exc
    target.write_bytes(data)
    rel_path = target.relative_to(root).as_posix()
    if mime.startswith("image/"):
        kind = "image"
    elif mime.startswith("audio/"):
        kind = "audio"
    else:
        kind = "file"
    attachment = {
        "id": uuid.uuid4().hex,
        "name": original,
        "mime": mime,
        "size": len(data),
        "kind": kind,
        "path": rel_path,
    }
    attachment["url"] = chat_attachment_url(rel_path, name=original)
    attachment["download_url"] = chat_attachment_url(rel_path, download=True, name=original)
    return attachment


def clean_chat_attachment(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    path = clean(value.get("path", ""))
    name = chat_safe_filename(value.get("name", "attachment"))
    if not path:
        return {}
    mime = chat_attachment_mime(name, value.get("mime", ""))
    raw_kind = clean(value.get("kind", "")).lower()
    if raw_kind == "image" or mime.startswith("image/"):
        kind = "image"
    elif raw_kind == "audio" or mime.startswith("audio/"):
        kind = "audio"
    else:
        kind = "file"
    size = int(value.get("size", 0) or 0)
    item = {
        "id": clean(value.get("id", "")) or uuid.uuid4().hex,
        "name": name,
        "mime": mime,
        "size": max(0, size),
        "kind": kind,
        "path": path,
        "url": chat_attachment_url(path, name=name),
        "download_url": chat_attachment_url(path, download=True, name=name),
    }
    return item


def chat_extra_attachments(extra: dict | None) -> list[dict]:
    if not isinstance(extra, dict):
        return []
    source = extra.get("attachments")
    if source is None and isinstance(extra.get("attachment"), dict):
        source = [extra.get("attachment")]
    rows = source if isinstance(source, list) else []
    result = []
    for item in rows[:8]:
        clean_item = clean_chat_attachment(item)
        if clean_item:
            result.append(clean_item)
    return result


def resolve_chat_attachment_path(relative_path: str = "") -> Path:
    raw = str(relative_path or "").replace("\\", "/").strip("/")
    raw_parts = [part.strip() for part in raw.split("/") if part.strip()]
    if not raw_parts or any(part in (".", "..") for part in raw_parts):
        raise RuntimeError("Duong dan dinh kem khong hop le.")
    root = CHAT_ATTACHMENT_DIR.resolve()
    target = CHAT_ATTACHMENT_DIR.joinpath(*raw_parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Duong dan dinh kem khong hop le.") from exc
    return target


def safe_chat_attachment_path(relative_path: str = "") -> Path:
    target = resolve_chat_attachment_path(relative_path)
    if not target.is_file():
        raise RuntimeError("Dinh kem khong ton tai.")
    assert_chat_attachment_allowed(target.name, chat_attachment_mime(target.name))
    return target


def chat_attachment_sort_value(item: dict, fallback_index: int = 0) -> tuple[float, int, int]:
    message_id = int(item.get("id", 0) or 0)
    try:
        ts = float(item.get("ts", 0) or 0)
    except Exception:
        ts = 0.0
    return (ts, message_id, fallback_index)


def chat_attachment_quota_bytes() -> int:
    settings = load_server_settings()
    return int(settings.get("chat_attachment_limit_bytes", DEFAULT_SETTINGS["chat_attachment_limit_mb"] * 1024 * 1024) or 0)


def chat_attachment_scan_files(username: str) -> dict[str, dict]:
    username = normalize_username(username)
    root = CHAT_ATTACHMENT_DIR.resolve()
    user_dir = (CHAT_ATTACHMENT_DIR / username).resolve()
    try:
        user_dir.relative_to(root)
    except ValueError:
        return {}
    if not user_dir.is_dir():
        return {}
    rows: dict[str, dict] = {}
    for target in user_dir.rglob("*"):
        if not target.is_file():
            continue
        try:
            rel_path = target.resolve().relative_to(root).as_posix()
            stat = target.stat()
        except Exception:
            continue
        mime = chat_attachment_mime(target.name)
        rows[rel_path] = {
            "path": rel_path,
            "target": target,
            "size": max(0, int(stat.st_size or 0)),
            "kind": "image" if mime.startswith("image/") else "file",
            "sort": (float(stat.st_mtime or 0), 0, 0),
        }
    return rows


def remove_empty_chat_attachment_dirs(target: Path) -> None:
    root = CHAT_ATTACHMENT_DIR.resolve()
    try:
        parent = target.resolve().parent
    except Exception:
        return
    while True:
        try:
            parent.relative_to(root)
        except ValueError:
            return
        if parent == root:
            return
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def delete_chat_attachment_file(relative_path: str) -> bool:
    try:
        target = resolve_chat_attachment_path(relative_path)
    except Exception:
        return False
    try:
        if target.is_file():
            target.unlink()
            remove_empty_chat_attachment_dirs(target)
            return True
    except Exception:
        return False
    return False


def delete_chat_audio_file(relative_path: str) -> bool:
    raw = str(relative_path or "").replace("\\", "/").strip("/")
    if not raw.lower().startswith("sound/"):
        return False
    target = (SERVER_DATA_ROOT / raw).resolve()
    sound_root = SERVER_SOUND_DIR.resolve()
    try:
        target.relative_to(sound_root)
    except ValueError:
        return False
    if not target.name.startswith("chat-"):
        return False
    try:
        if target.is_file():
            target.unlink()
            return True
    except Exception:
        return False
    return False


def delete_chat_attachment_tree(username: str) -> None:
    username = normalize_username(username)
    if not username:
        return
    root = CHAT_ATTACHMENT_DIR.resolve()
    target = (CHAT_ATTACHMENT_DIR / username).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def clear_chat_for_user(username: str) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    attachment_paths: set[str] = set()
    audio_paths: set[str] = set()
    removed = 0
    with CHAT_LOCK:
        state = load_chat_state_locked()
        messages = state.get("messages", []) if isinstance(state.get("messages", []), list) else []
        keep_messages = []
        for item in messages:
            if not isinstance(item, dict) or normalize_username(item.get("username", "")) != username:
                keep_messages.append(item)
                continue
            removed += 1
            for attachment in item.get("attachments", []) if isinstance(item.get("attachments", []), list) else []:
                clean_attachment = clean_chat_attachment(attachment)
                if clean_attachment.get("path"):
                    attachment_paths.add(clean_attachment["path"])
            for key in ("audio_path",):
                value = clean(item.get(key, ""))
                if value:
                    audio_paths.add(value)
            audio = item.get("audio")
            if isinstance(audio, dict):
                value = clean(audio.get("path", ""))
                if value:
                    audio_paths.add(value)
        state["messages"] = keep_messages
        for read_key in ("admin_read", "user_read"):
            if isinstance(state.get(read_key), dict):
                state[read_key].pop(username, None)
        server_database_delete_chat_user(username)
        CHAT_STATE_CACHE.update({"state": state, "dirty": False})
    for path in attachment_paths:
        delete_chat_attachment_file(path)
    delete_chat_attachment_tree(username)
    deleted_audio = 0
    for path in audio_paths:
        if delete_chat_audio_file(path):
            deleted_audio += 1
    return {
        "username": username,
        "removed_messages": removed,
        "removed_attachments": len(attachment_paths),
        "removed_audio": deleted_audio,
    }


def enforce_chat_attachment_quota_locked(username: str, state: dict) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    limit_bytes = chat_attachment_quota_bytes()
    if limit_bytes <= 0:
        return False
    messages = state.get("messages", []) if isinstance(state.get("messages", []), list) else []
    files = chat_attachment_scan_files(username)
    referenced: list[dict] = []
    referenced_paths: set[str] = set()
    for message_index, item in enumerate(messages):
        if not isinstance(item, dict) or normalize_username(item.get("username", "")) != username:
            continue
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list):
            continue
        for attachment_index, attachment in enumerate(attachments):
            clean_attachment = clean_chat_attachment(attachment)
            path = clean_attachment.get("path", "")
            if not path:
                continue
            referenced_paths.add(path)
            file_row = files.get(path, {})
            size = int(file_row.get("size", clean_attachment.get("size", 0)) or 0)
            kind = clean_attachment.get("kind", "file")
            referenced.append({
                "key": f"{int(item.get('id', 0) or 0)}:{attachment_index}:{path}",
                "path": path,
                "kind": "image" if kind == "image" else "file",
                "size": size,
                "sort": chat_attachment_sort_value(item, attachment_index + message_index),
            })
    total_bytes = sum(int(row.get("size", 0) or 0) for row in files.values())
    if total_bytes <= limit_bytes:
        return False

    protected: set[str] = set()
    for kind in ("image", "file"):
        rows = sorted([row for row in referenced if row.get("kind") == kind], key=lambda row: row.get("sort", (0, 0, 0)))
        protected.update(str(row.get("key", "")) for row in rows[-20:])

    orphan_rows = [
        {
            "key": f"orphan:{path}",
            "path": path,
            "kind": row.get("kind", "file"),
            "size": int(row.get("size", 0) or 0),
            "sort": row.get("sort", (0, 0, 0)),
            "orphan": True,
        }
        for path, row in files.items()
        if path not in referenced_paths
    ]
    candidates = sorted(
        [row for row in referenced if str(row.get("key", "")) not in protected] + orphan_rows,
        key=lambda row: row.get("sort", (0, 0, 0)),
    )

    deleted_paths: set[str] = set()
    removed_reference_keys: set[str] = set()
    remaining_bytes = total_bytes

    def mark_delete(row: dict) -> None:
        nonlocal remaining_bytes
        path = clean(row.get("path", ""))
        if not path or path in deleted_paths:
            return
        deleted_paths.add(path)
        remaining_bytes -= int(files.get(path, {}).get("size", row.get("size", 0)) or 0)
        if not row.get("orphan"):
            removed_reference_keys.add(str(row.get("key", "")))

    for row in candidates:
        mark_delete(row)
    if remaining_bytes > limit_bytes:
        for row in sorted(referenced, key=lambda item: item.get("sort", (0, 0, 0))):
            if remaining_bytes <= limit_bytes:
                break
            mark_delete(row)

    if not deleted_paths:
        return False

    for path in sorted(deleted_paths):
        delete_chat_attachment_file(path)

    changed = False
    for item in messages:
        if not isinstance(item, dict) or normalize_username(item.get("username", "")) != username:
            continue
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list):
            continue
        next_attachments = []
        for attachment_index, attachment in enumerate(attachments):
            clean_attachment = clean_chat_attachment(attachment)
            path = clean_attachment.get("path", "")
            key = f"{int(item.get('id', 0) or 0)}:{attachment_index}:{path}"
            if path in deleted_paths or key in removed_reference_keys:
                changed = True
                continue
            next_attachments.append(attachment)
        if len(next_attachments) != len(attachments):
            if next_attachments:
                item["attachments"] = next_attachments
            else:
                item.pop("attachments", None)
                if not clean(item.get("text", "")):
                    item["text"] = "Attachment removed by storage limit."
            changed = True
    return changed


def enforce_all_chat_attachment_quotas() -> None:
    with CHAT_LOCK:
        state = load_chat_state_locked()
        usernames = {
            normalize_username(item.get("username", ""))
            for item in state.get("messages", [])
            if isinstance(item, dict)
        }
        if CHAT_ATTACHMENT_DIR.is_dir():
            for child in CHAT_ATTACHMENT_DIR.iterdir():
                if child.is_dir():
                    username = normalize_username(child.name)
                    if username:
                        usernames.add(username)
        changed = False
        for username in sorted(item for item in usernames if item):
            changed = enforce_chat_attachment_quota_locked(username, state) or changed
        if changed:
            save_chat_state_locked(state)
