# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def server_data_unique_child_path(folder: Path, desired_name: str) -> Path:
    safe_name = clean(str(desired_name or "")).replace("\\", " ").replace("/", " ").strip()
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "Linked lesson"
    candidate = folder / safe_name
    if not candidate.exists():
        return candidate
    suffix = "".join(Path(safe_name).suffixes)
    stem = safe_name[:-len(suffix)] if suffix else safe_name
    stem = stem.rstrip() or "Linked lesson"
    for index in range(2, 500):
        name = f"{stem} - link {index}{suffix}"
        candidate = folder / name
        if not candidate.exists():
            return candidate
    raise RuntimeError("Khong tao duoc ten link khong trung.")


def write_server_data_file_link(source_file: Path, destination_file: Path, actor_username: str = "") -> dict:
    source_target = server_data_effective_file_path(source_file, username=actor_username, admin=True)
    if not source_target.is_file() or not is_lesson_file(source_target):
        raise RuntimeError("Chi co the tao link cho tep bai hoc, PDF hoac anh.")
    payload = {
        "kind": SERVER_DATA_LINK_KIND,
        "version": 1,
        "target": server_data_relative(source_target),
        "target_type": "file",
        "created_by": normalize_username(actor_username),
        "created_at": utc_timestamp(),
    }
    destination_rel = server_data_relative(destination_file)
    destination_top = clean(destination_rel.split("/", 1)[0]).lower() if destination_rel else ""
    target_top = clean(payload["target"].split("/", 1)[0]).lower() if payload.get("target") else ""
    if destination_top == "common" and target_top != "common":
        raise RuntimeError("Cannot expose a private user file through common as a link.")
    if destination_top and destination_top != "common" and target_top not in {"common", destination_top}:
        raise RuntimeError("Cannot link another learner's private file into this folder.")
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination_file, payload, indent=None)
    return {
        "name": destination_file.name,
        "path": server_data_relative(destination_file),
        "target": payload["target"],
    }


def copy_server_data_folder_as_links(source_folder: Path, destination_parent: Path, actor_username: str = "") -> dict:
    if not source_folder.is_dir():
        raise RuntimeError("Nguon khong phai thu muc.")
    destination_root = server_data_unique_child_path(destination_parent, source_folder.name)
    source_folder_target = server_data_folder_link_target_path(source_folder, username=actor_username, admin=True) or source_folder
    source_folder_target = source_folder_target.resolve()
    destination_rel = server_data_relative(destination_root)
    destination_top = clean(destination_rel.split("/", 1)[0]).lower() if destination_rel else ""
    source_target_rel = server_data_relative(source_folder_target)
    target_top = clean(source_target_rel.split("/", 1)[0]).lower() if source_target_rel else ""
    if destination_top == "common" and target_top != "common":
        raise RuntimeError("Cannot expose a private user folder through common as a link.")
    if destination_top and destination_top != "common" and target_top not in {"common", destination_top}:
        raise RuntimeError("Cannot link another learner's private folder into this folder.")
    counts = server_data_folder_counts_cached(source_folder_target)
    write_server_data_folder_link_marker(destination_root, source_target_rel, actor_username, counts)
    return {
        "path": server_data_relative(destination_root),
        "name": destination_root.name,
        "folders": 1,
        "folder_count": int(counts.get("folder_count", 0) or 0),
        "files": int(counts.get("file_count", 0) or 0),
        "file_count": int(counts.get("file_count", 0) or 0),
        "space_v_file_count": int(counts.get("space_v_file_count", 0) or 0),
        "word_count": int(counts.get("word_count", 0) or 0),
        "fast_link": True,
        "target": source_target_rel,
    }


def server_data_immediate_mission_parts(relative_path: str = "") -> tuple[str, list[str]]:
    parts = [clean(part) for part in clean_path_value(relative_path).split("/") if clean(part)]
    if len(parts) < 2 or parts[1].lower() != VOCAB_MISSION_PENDING_DIR.lower():
        return "", []
    owner = normalize_username(parts[0])
    return owner, parts


def clear_server_data_immediate_mission_item(source: Path, source_raw: str, actor_username: str = "") -> dict:
    actor_username = normalize_username(actor_username)
    owner, parts = server_data_immediate_mission_parts(source_raw)
    if not owner:
        raise RuntimeError("Clear is only available inside Immediate Mission.")
    if owner.lower() == "common":
        raise RuntimeError("Immediate Mission cleanup is only available in learner folders.")
    if not is_admin_user(actor_username) and owner.lower() != actor_username.lower():
        raise RuntimeError("You can only clear your own Immediate Mission.")
    immediate_root = (SERVER_DATA_ROOT / owner / VOCAB_MISSION_PENDING_DIR).resolve()
    target = source.resolve()
    try:
        target.relative_to(immediate_root)
    except ValueError as exc:
        raise RuntimeError("Invalid Immediate Mission path.") from exc
    if not target.exists():
        return {
            "path": clean_path_value(source_raw),
            "type": "missing",
            "removed": 0,
        }
    removed = 0
    target_was_dir = target.is_dir()
    if target.is_file():
        target.unlink()
        removed = 1
    elif target_was_dir:
        for child in list(target.iterdir()):
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except FileNotFoundError:
                continue
    else:
        raise RuntimeError("Unsupported Immediate Mission item.")
    try:
        current = target if target.is_dir() else target.parent
        while current != immediate_root and current.exists() and current.is_dir() and not any(current.iterdir()):
            parent = current.parent
            current.rmdir()
            current = parent
    except Exception:
        pass
    return {
        "path": clean_path_value(source_raw),
        "type": "folder" if target_was_dir else "file",
        "removed": removed,
    }
