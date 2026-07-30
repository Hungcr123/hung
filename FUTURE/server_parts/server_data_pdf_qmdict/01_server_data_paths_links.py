# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def safe_server_data_path(relative_path: str = "", username: str = "", admin: bool = False) -> Path:
    username = normalize_username(username)
    ensure_server_data_folders(username)
    root = SERVER_DATA_ROOT.resolve()
    raw = clean_path_value(relative_path)
    if not raw:
        return root
    raw_parts = [part.strip() for part in raw.split("/") if part.strip()]
    if any(part in (".", "..") for part in raw_parts):
        raise RuntimeError("Duong dan server data khong hop le.")
    if not raw_parts:
        return root
    top_raw = raw_parts[0]
    if top_raw.lower() == "common":
        top = "common"
    elif top_raw.lower() == username.lower():
        top = username
    elif admin and re.match(r"^[A-Za-z0-9_.-]{1,64}$", top_raw) and (SERVER_DATA_ROOT / top_raw).is_dir():
        top = top_raw
    else:
        raise RuntimeError("Ban chi duoc mo thu muc common va thu muc user dang dang nhap.")
    allowed_root = (SERVER_DATA_ROOT / top).resolve()
    folder_link_matcher = globals().get("server_database_folder_link_match")
    folder_link_registry_ready = globals().get("server_database_folder_link_registry_ready")
    registry_ready = bool(folder_link_registry_ready()) if callable(folder_link_registry_ready) else False
    if registry_ready and callable(folder_link_matcher) and folder_link_matcher(raw):
        target = allowed_root.joinpath(*raw_parts[1:]).resolve()
        try:
            target.relative_to(allowed_root)
        except ValueError as exc:
            raise RuntimeError("Duong dan server data khong hop le.") from exc
        return target
    target = allowed_root
    for index, part in enumerate(raw_parts[1:]):
        # Added 2026-07-21: descendants of a linked root are virtual; do not enumerate its empty mirror skeleton.
        if not registry_ready and read_server_data_folder_link_payload(target):
            target = target.joinpath(*raw_parts[index + 1:])
            break
        direct = target / part
        if direct.exists():
            target = direct
            continue
        normalized_part = clean(part).lower()
        wanted_names = {normalized_part}
        matched = None
        try:
            for child in target.iterdir():
                child_name = clean(child.name)
                if child_name.lower() in wanted_names:
                    matched = child
                    break
        except OSError:
            matched = None
        target = matched if matched is not None else direct
    target = target.resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError as exc:
        raise RuntimeError("Duong dan server data khong hop le.") from exc
    return target


def server_data_relative(path: Path) -> str:
    root = SERVER_DATA_ROOT.resolve()
    try:
        relative = path.resolve().relative_to(root).as_posix()
        return "" if relative == "." else relative
    except Exception:
        return ""


def server_data_manifest_path(relative_path: str = "") -> Path:
    rel = clean_path_value(relative_path)
    if not rel:
        return SERVER_DATA_ROOT
    return SERVER_DATA_ROOT.joinpath(*rel.split("/"))


def read_server_data_link_payload(path: Path) -> dict:
    try:
        if not path.is_file():
            return {}
        if int(path.stat().st_size) > 64 * 1024:
            return {}
        text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not text.startswith("{"):
            return {}
        payload = json.loads(text)
        if not isinstance(payload, dict) or payload.get("kind") != SERVER_DATA_LINK_KIND:
            return {}
        target = clean_path_value(payload.get("target", ""))
        target_type = clean(payload.get("target_type", "")).lower()
        if not target or target_type not in {"file", "folder"}:
            return {}
        return {
            "kind": SERVER_DATA_LINK_KIND,
            "version": int(payload.get("version", 1) or 1),
            "target": target,
            "target_type": target_type,
            "created_by": normalize_username(payload.get("created_by", "")),
            "created_at": clean(payload.get("created_at", "")),
        }
    except Exception:
        return {}


def read_server_data_folder_link_payload(folder: Path) -> dict:
    try:
        if not folder.is_dir():
            return {}
        database_reader = globals().get("server_database_folder_link_payload")
        if callable(database_reader):
            cached_payload = database_reader(folder)
            if isinstance(cached_payload, dict) and clean_path_value(cached_payload.get("target", "")):
                return cached_payload
        marker = folder / SERVER_DATA_FOLDER_LINK_FILE
        text = (server_database_read_document_text(marker, "") or "").strip()
        if not text.startswith("{"):
            return {}
        payload = json.loads(text)
        if not isinstance(payload, dict) or payload.get("kind") != SERVER_DATA_LINK_KIND:
            return {}
        target = clean_path_value(payload.get("target", ""))
        if not target:
            return {}
        return {
            "kind": SERVER_DATA_LINK_KIND,
            "version": int(payload.get("version", 1) or 1),
            "target": target,
            "target_type": "folder",
            "created_by": normalize_username(payload.get("created_by", "")),
            "created_at": clean(payload.get("created_at", "")),
        }
    except Exception:
        return {}


def server_data_link_target_path(path: Path, username: str = "", admin: bool = False) -> Path | None:
    payload = read_server_data_link_payload(path)
    if not payload:
        return None
    target_rel = clean_path_value(payload.get("target", ""))
    parts = [part for part in target_rel.split("/") if part]
    if not parts:
        return None
    target_top = clean(parts[0]).lower()
    username = normalize_username(username)
    if not admin and target_top != "common" and target_top != username.lower():
        raise RuntimeError("Lien ket nay tro den thu muc khong duoc phep.")
    return safe_server_data_path(target_rel, username or clean(parts[0]), admin=admin)


def server_data_folder_link_target_path(folder: Path, username: str = "", admin: bool = False) -> Path | None:
    payload = read_server_data_folder_link_payload(folder)
    if not payload:
        return None
    target_rel = clean_path_value(payload.get("target", ""))
    parts = [part for part in target_rel.split("/") if part]
    if not parts:
        return None
    target_top = clean(parts[0]).lower()
    username = normalize_username(username)
    if not admin and target_top != "common" and target_top != username.lower():
        raise RuntimeError("Lien ket thu muc nay tro den noi khong duoc phep.")
    return safe_server_data_path(target_rel, username or clean(parts[0]), admin=admin)


def write_server_data_folder_link_marker(folder: Path, target_rel: str, actor_username: str = "", counts: dict | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": SERVER_DATA_LINK_KIND,
        "version": 1,
        "target": clean_path_value(target_rel),
        "target_type": "folder",
        "created_by": normalize_username(actor_username),
        "created_at": utc_timestamp(),
    }
    if isinstance(counts, dict):
        for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
            try:
                payload[key] = max(0, int(counts.get(key, 0) or 0))
            except Exception:
                payload[key] = 0
        payload["counts_at"] = utc_timestamp()
    atomic_write_json(folder / SERVER_DATA_FOLDER_LINK_FILE, payload, indent=None)


def update_server_data_folder_link_counts(folder: Path, counts: dict | None = None) -> None:
    if not isinstance(counts, dict):
        return
    payload = read_server_data_folder_link_payload(folder)
    if not payload:
        return
    next_values = {}
    changed = False
    for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
        try:
            next_values[key] = max(0, int(counts.get(key, 0) or 0))
        except Exception:
            next_values[key] = 0
        try:
            current_value = max(0, int(payload.get(key, 0) or 0))
        except Exception:
            current_value = 0
        if key not in payload or current_value != next_values[key]:
            changed = True
    if not changed and clean(payload.get("counts_at", "")):
        return
    payload.update(next_values)
    payload["counts_at"] = utc_timestamp()
    atomic_write_json(Path(folder) / SERVER_DATA_FOLDER_LINK_FILE, payload, indent=None)


def resolve_server_data_file_link(path: Path, username: str = "", admin: bool = False) -> Path:
    current = path
    seen: set[str] = set()
    for _index in range(8):
        try:
            key = str(current.resolve()).lower()
        except Exception:
            key = str(current).lower()
        if key in seen:
            raise RuntimeError("Lien ket server data bi lap vong.")
        seen.add(key)
        target = server_data_link_target_path(current, username=username, admin=admin)
        if target is None:
            return current
        current = target
    raise RuntimeError("Lien ket server data qua sau.")


def server_data_effective_file_path(path: Path, username: str = "", admin: bool = False) -> Path:
    # Added 2026-07-29: direct physical manifest files do not need a vault
    # lookup or folder-link scan on every completion request.
    manifest_reader = globals().get("server_data_manifest_file_entry")
    if callable(manifest_reader) and path.is_file():
        relative = server_data_relative(path)
        manifest_entry = manifest_reader(relative)
        if isinstance(manifest_entry, dict):
            effective_path = clean_path_value(manifest_entry.get("effective_path") or manifest_entry.get("path", ""))
            if (
                effective_path.lower() == relative.lower()
                and not truthy(manifest_entry.get("linked"), False)
                and not truthy(manifest_entry.get("virtual"), False)
                and not clean(manifest_entry.get("vault_entry_id", ""))
            ):
                return path
    vault_entry_reader = globals().get("server_database_vault_entry_for_path")
    if bool(globals().get("SERVER_DATABASE_VAULT_ENABLED", True)) and callable(vault_entry_reader):
        relative = server_data_relative(path)
        virtual_entry = vault_entry_reader(relative)
        source_resolver = globals().get("server_database_vault_resolved_source_path")
        source_path = clean_path_value(source_resolver(virtual_entry)) if isinstance(virtual_entry, dict) and callable(source_resolver) else clean_path_value(virtual_entry.get("source_path", "")) if isinstance(virtual_entry, dict) else ""
        if source_path:
            source_top = clean(source_path.split("/", 1)[0]).lower()
            normalized_user = normalize_username(username)
            if not admin and source_top not in {"common", normalized_user.lower()}:
                raise RuntimeError("Vault entry points outside the allowed ownership scope.")
            return safe_server_data_path(source_path, normalized_user or source_top, admin=admin)
    path = server_data_resolve_folder_link_ancestor(path, username=username, admin=admin)
    target = resolve_server_data_file_link(path, username=username, admin=admin)
    if target.is_dir():
        raise RuntimeError("Lien ket hien tai tro den thu muc, khong phai tep.")
    return target


def server_data_resolve_folder_link_ancestor(path: Path, username: str = "", admin: bool = False) -> Path:
    database_matcher = globals().get("server_database_folder_link_match")
    if callable(database_matcher):
        match = database_matcher(path)
        if match:
            target = safe_server_data_path(match.get("target", ""), username=username, admin=admin)
            suffix = clean_path_value(match.get("suffix", ""))
            return target.joinpath(*suffix.split("/")) if suffix else target
    root = SERVER_DATA_ROOT.resolve()
    try:
        absolute = Path(path).resolve()
        relative_parts = absolute.relative_to(root).parts
    except Exception:
        return path
    current = root
    for index, part in enumerate(relative_parts):
        target = server_data_folder_link_target_path(current, username=username, admin=admin)
        if target is not None:
            return target.joinpath(*relative_parts[index:])
        current = current / part
    target = server_data_folder_link_target_path(current, username=username, admin=admin)
    return target if target is not None else path


def server_data_folder_link_ancestor_payload(path: Path) -> dict:
    database_matcher = globals().get("server_database_folder_link_match")
    if callable(database_matcher):
        match = database_matcher(path)
        if match:
            return match
    root = SERVER_DATA_ROOT.resolve()
    try:
        absolute = Path(path).resolve()
        relative_parts = absolute.relative_to(root).parts
    except Exception:
        return {}
    current = root
    for part in relative_parts:
        payload = read_server_data_folder_link_payload(current)
        if payload:
            return payload
        current = current / part
    return read_server_data_folder_link_payload(current)


def server_data_virtual_link_entry(source: Path, display_parent_rel: str = "", created_by: str = "") -> dict | None:
    entry = server_data_manifest_entry(source)
    if not entry:
        return None
    display_rel = clean_path_value(f"{clean_path_value(display_parent_rel)}/{source.name}" if display_parent_rel else source.name)
    target_rel = clean_path_value(entry.get("link_target") or entry.get("effective_path") or entry.get("path") or server_data_relative(source))
    entry["path"] = display_rel
    entry["linked"] = True
    entry["link_target"] = target_rel
    entry["effective_path"] = target_rel
    if created_by and not clean(entry.get("created_by", "")):
        entry["created_by"] = normalize_username(created_by)
    return entry


# Added 2026-07-21: linked-folder navigation projects clean manifest rows without rescanning the target directory.
def server_data_virtual_link_manifest_entry(source_entry: dict, display_parent_rel: str = "", created_by: str = "") -> dict | None:
    if not isinstance(source_entry, dict):
        return None
    entry = dict(source_entry)
    target_rel = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry.get("path", ""))
    name = clean(entry.get("name", "")) or (Path(target_rel).name if target_rel else "")
    if not target_rel or not name:
        return None
    display_rel = clean_path_value(f"{clean_path_value(display_parent_rel)}/{name}" if display_parent_rel else name)
    entry["name"] = name
    entry["path"] = display_rel
    entry["linked"] = True
    entry["link_target"] = target_rel
    entry["effective_path"] = target_rel
    entry["managed_mirror"] = True
    if created_by and not clean(entry.get("created_by", "")):
        entry["created_by"] = normalize_username(created_by)
    return entry


def is_lesson_file(path: Path) -> bool:
    return path.suffix.lower() in LESSON_FILE_SUFFIXES


SPACE_PACKAGE_METADATA_LOCK = threading.RLock()
SPACE_PACKAGE_METADATA_CACHE: dict[tuple, dict] = {}
SPACE_LESSON_HANDLE_LOCK = threading.RLock()
SPACE_LESSON_HANDLES: dict[str, dict] = {}
SPACE_LESSON_HANDLE_TTL_SECONDS = 15 * 60
SPACE_LESSON_HANDLE_LIMIT = 4096


def space_pdf_package_path_for_legacy(path: Path) -> Path | None:
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix in {".space_pdf", ".space_picture"}:
        package = target
    elif suffix == ".pdf":
        package = target.with_suffix(".space_pdf")
    elif suffix in IMAGE_FILE_SUFFIXES:
        package = target.with_suffix(".space_picture")
    else:
        return None
    return package if package.is_file() else None


# Updated 2026-07-22: package discovery no longer depends on a legacy raw PDF/Picture beside the package.
def space_pdf_package_manifest_metadata(path: Path) -> dict:
    package = space_pdf_package_path_for_legacy(path)
    if package is None:
        return {}
    try:
        package_stat = package.stat()
        is_picture = package.suffix.lower() == ".space_picture"
        manifest = validate_space_picture_manifest_light(package) if is_picture else validate_space_pdf_manifest_light(package)
        source = resolve_space_picture_source_path(package, manifest) if is_picture else resolve_space_pdf_source_path(package, manifest)
        if source is None or not source.is_file():
            return {"package_status": "missing_asset"}
        source_stat = source.stat()
        cache_key = (
            str(package).lower(),
            int(package_stat.st_mtime_ns),
            int(package_stat.st_size),
            int(source_stat.st_mtime_ns),
            int(source_stat.st_size),
        )
        with SPACE_PACKAGE_METADATA_LOCK:
            cached = SPACE_PACKAGE_METADATA_CACHE.get(cache_key)
            if isinstance(cached, dict):
                return dict(cached)
        if int(manifest.get("source_bytes", 0) or 0) != int(source_stat.st_size):
            return {"package_status": "stale"}
        source_filename = clean(manifest.get("source_filename", ""))
        display_extension = Path(source_filename).suffix.lower()
        if is_picture:
            if display_extension not in IMAGE_FILE_SUFFIXES:
                display_extension = source.suffix.lower()
        else:
            display_extension = ".pdf"
        title = clean(manifest.get("title", "")) or package.stem
        display_name = source_filename or f"{title}{display_extension}"
        source_meta = cached_lesson_file_metadata(source)
        metadata = {
            "name": display_name,
            "raw_name": package.name,
            "extension": display_extension,
            "lesson_id": clean(manifest.get("lesson_id", ""))[:240],
            "document_id": clean(manifest.get("document_id", ""))[:240],
            "content_fingerprint": clean(manifest.get("source_sha256", ""))[:320],
            "package_path": server_data_relative(package),
            "source_path": server_data_relative(source),
            "asset_size": int(source_stat.st_size),
            "package_revision": max(1, space_w_int(manifest.get("package_revision", 1), 1)),
            "package_schema_version": max(1, space_w_int(manifest.get("schema_version", 1), 1)),
            "package_backed": True,
            "package_status": "active",
            **{
                key: max(0, space_w_int(source_meta.get(key, 0), 0))
                for key in SERVER_DATA_STRUCTURAL_METADATA_FIELDS
            },
        }
        with SPACE_PACKAGE_METADATA_LOCK:
            if len(SPACE_PACKAGE_METADATA_CACHE) >= 2048:
                SPACE_PACKAGE_METADATA_CACHE.clear()
            SPACE_PACKAGE_METADATA_CACHE[cache_key] = dict(metadata)
        return metadata
    except Exception as exc:
        stt_debug_log("space_pdf_package_manifest_invalid", path=str(package), error=str(exc))
        return {"package_status": "invalid"}


def _space_package_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _space_lesson_handle_issue(username: str, descriptor: dict) -> tuple[str, float]:
    now = time.time()
    expires = now + SPACE_LESSON_HANDLE_TTL_SECONDS
    token = secrets.token_urlsafe(32)
    row = {**descriptor, "username": normalize_username(username), "expires_epoch": expires}
    with SPACE_LESSON_HANDLE_LOCK:
        for key, current in list(SPACE_LESSON_HANDLES.items()):
            if float(current.get("expires_epoch", 0) or 0) <= now:
                SPACE_LESSON_HANDLES.pop(key, None)
        if len(SPACE_LESSON_HANDLES) >= SPACE_LESSON_HANDLE_LIMIT:
            oldest = min(SPACE_LESSON_HANDLES, key=lambda key: float(SPACE_LESSON_HANDLES[key].get("expires_epoch", 0) or 0))
            SPACE_LESSON_HANDLES.pop(oldest, None)
        SPACE_LESSON_HANDLES[token] = row
    return token, expires


# Added 2026-07-22: one validated open turns a path into the generic lesson identity used by later state routes.
def open_lesson_descriptor(username: str, relative_path: str, admin: bool = False, requested_lesson_id: str = "", task_owner: str = "") -> dict:
    viewer = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        raise RuntimeError("Lesson path is required.")
    path_owner = normalize_username(raw_path.split("/", 1)[0])
    if not admin and path_owner.lower() not in {"common", viewer.lower()}:
        raise PermissionError("Lesson path belongs to another user scope.")
    display = safe_server_data_path(raw_path, viewer, admin=admin)
    effective = server_data_effective_file_path(display, username=viewer, admin=admin)
    effective_suffix = effective.suffix.lower()
    package_suffixes = {".space_pdf", ".space_picture"}
    if not effective.is_file() or (
        effective_suffix not in package_suffixes
        and effective_suffix != ".pdf"
        and effective_suffix not in IMAGE_FILE_SUFFIXES
    ):
        raise RuntimeError("This lesson type does not have a portable package adapter yet.")
    package = space_pdf_package_path_for_legacy(effective)
    if package is None:
        raise RuntimeError("Portable Space PDF/Picture package is not ready for this lesson.")
    is_picture = package.suffix.lower() == ".space_picture"
    manifest = validate_space_picture_package(package, verify_source=True) if is_picture else validate_space_pdf_package(package, verify_source=True)
    resolved_source = resolve_space_picture_source_path(package, manifest) if is_picture else resolve_space_pdf_source_path(package, manifest)
    if resolved_source is None or not resolved_source.is_file():
        raise RuntimeError("Canonical PDF/Picture asset is missing.")
    source_stat = resolved_source.stat()
    package_stat = package.stat()
    cache_key = (
        "validated-open",
        str(package).lower(),
        int(package_stat.st_mtime_ns),
        int(package_stat.st_size),
        int(source_stat.st_mtime_ns),
        int(source_stat.st_size),
    )
    with SPACE_PACKAGE_METADATA_LOCK:
        descriptor = SPACE_PACKAGE_METADATA_CACHE.get(cache_key)
    if not isinstance(descriptor, dict):
        if resolved_source is not None and manifest.get("source_storage") == "canonical":
            canonical_source = resolved_source
            source_matches = canonical_source.is_file() and int(manifest["source_bytes"]) == int(canonical_source.stat().st_size)
        elif resolved_source is not None:
            canonical_source = resolved_source
            source_matches = resolved_source == effective.resolve() and int(manifest["source_bytes"]) == int(source_stat.st_size)
        else:
            # Embedded v1 compatibility must still prove that the visible legacy asset is byte-identical.
            canonical_source = effective.resolve()
            source_matches = int(manifest["source_bytes"]) == int(source_stat.st_size) and _space_package_file_sha256(effective) == manifest["source_sha256"]
        if not source_matches:
            raise RuntimeError("Legacy PDF/Picture and portable package source do not match.")
        owner_scope = clean(manifest.get("owner_scope", "common")).lower()
        if not admin and owner_scope != "common" and owner_scope != f"user:{viewer.lower()}":
            raise PermissionError("Portable lesson belongs to another user scope.")
        canonical_stat = canonical_source.stat()
        descriptor = {
            "lesson_id": clean(manifest["lesson_id"]),
            "file_id": clean(manifest["lesson_id"]),
            "canonical_file_id": clean(manifest["lesson_id"]),
            "document_id": clean(manifest["document_id"]),
            "space_type": "Space_Picture" if package.suffix.lower() == ".space_picture" else "Space_PDF",
            "title": clean(manifest.get("title", "")) or package.stem,
            "display_name": clean(manifest.get("source_filename", "")) or display.name,
            "artifact_revision": max(1, space_w_int(manifest.get("package_revision", 1), 1)),
            "artifact_path": server_data_relative(package),
            "source_path": server_data_relative(canonical_source),
            "legacy_source_path": "" if effective_suffix in package_suffixes else server_data_relative(effective),
            "source_sha256": clean(manifest["source_sha256"]),
            "source_bytes": int(manifest["source_bytes"]),
            "source_mtime_ns": int(canonical_stat.st_mtime_ns),
            "asset_id": clean(manifest.get("asset_id", "")),
            "asset_locator": clean(manifest.get("asset_locator", "")),
            "owner_scope": owner_scope or "common",
        }
        with SPACE_PACKAGE_METADATA_LOCK:
            if len(SPACE_PACKAGE_METADATA_CACHE) >= 2048:
                SPACE_PACKAGE_METADATA_CACHE.clear()
            SPACE_PACKAGE_METADATA_CACHE[cache_key] = dict(descriptor)
    effective_path = clean_path_value(server_data_relative(effective))
    display_path = clean_path_value(server_data_relative(display)) or raw_path
    identity_resolver = globals().get("resolve_lesson_identity_contract")
    identity = identity_resolver(
        display_path,
        viewer,
        admin=admin,
        requested_lesson_id=clean(requested_lesson_id) or descriptor.get("lesson_id", ""),
        task_owner=task_owner,
        strict=True,
        require_file=True,
    ) if callable(identity_resolver) else {}
    request_descriptor = {
        **descriptor,
        "display_path": clean_path_value(identity.get("display_path", "")) or display_path,
        "requested_path": clean_path_value(identity.get("requested_path", "")) or display_path,
        "link_path": clean_path_value(identity.get("link_path", "")) or (display_path if display_path.lower() != effective_path.lower() else ""),
        "effective_path": clean_path_value(identity.get("effective_path", "")) or effective_path,
        "task_owner": normalize_username(identity.get("task_owner") or task_owner or viewer),
    }
    handle, expires = _space_lesson_handle_issue(viewer, request_descriptor)
    return {**request_descriptor, "lesson_handle": handle, "handle_expires_epoch": expires}


def validate_lesson_handle(username: str, lesson_id: str, lesson_handle: str) -> dict:
    token = clean(lesson_handle)
    viewer = normalize_username(username)
    with SPACE_LESSON_HANDLE_LOCK:
        row = dict(SPACE_LESSON_HANDLES.get(token) or {})
        if row and float(row.get("expires_epoch", 0) or 0) <= time.time():
            SPACE_LESSON_HANDLES.pop(token, None)
            row = {}
    if not row or normalize_username(row.get("username", "")).lower() != viewer.lower() or clean(row.get("lesson_id", "")) != clean(lesson_id):
        raise PermissionError("Lesson handle is missing, stale or belongs to another session.")
    return row


# Added 2026-07-22: media routes use the validated handle to reach canonical assets without trusting client paths.
def validated_lesson_asset_path(username: str, lesson_id: str, lesson_handle: str, asset_kind: str) -> Path:
    row = validate_lesson_handle(username, lesson_id, lesson_handle)
    kind = clean(asset_kind).lower()
    if kind not in {"pdf", "picture"}:
        raise RuntimeError("Lesson asset kind is invalid.")
    source_path = clean_path_value(row.get("source_path", ""))
    target = (SERVER_DATA_ROOT / Path(*source_path.split("/"))).resolve()
    allowed_root = (SERVER_DATA_ROOT / "_assets" / kind).resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError as exc:
        raise PermissionError("Lesson handle does not reference a canonical asset.") from exc
    expected_suffixes = {".pdf"} if kind == "pdf" else IMAGE_FILE_SUFFIXES
    if not target.is_file() or target.suffix.lower() not in expected_suffixes:
        raise RuntimeError("Canonical lesson asset is missing.")
    stat = target.stat()
    if int(row.get("source_bytes", 0) or 0) != int(stat.st_size) or int(row.get("source_mtime_ns", 0) or 0) != int(stat.st_mtime_ns):
        raise RuntimeError("Canonical lesson asset changed; reopen the lesson to validate its new revision.")
    return target
