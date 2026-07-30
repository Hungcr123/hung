# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def server_data_path_top(relative_path: str = "") -> str:
    parts = [part for part in clean_path_value(relative_path).split("/") if part]
    return clean(parts[0]).lower() if parts else ""


def server_data_link_owner_payload(path: Path) -> dict:
    if path.is_dir():
        return read_server_data_folder_link_payload(path)
    return read_server_data_link_payload(path)


def server_data_link_created_by(path: Path) -> str:
    payload = server_data_link_owner_payload(path)
    return normalize_username(payload.get("created_by", "")) if payload else ""


def server_data_is_user_owned_link(path: Path, username: str = "") -> bool:
    username = normalize_username(username)
    return bool(username and server_data_link_created_by(path).lower() == username.lower())


def server_data_user_destination_allowed(destination: Path | None, username: str = "") -> bool:
    username = normalize_username(username)
    if not destination or not username:
        return False
    try:
        user_root = (SERVER_DATA_ROOT / username).resolve()
        dest = destination.resolve()
        dest.relative_to(user_root)
    except Exception:
        return False
    if dest == user_root:
        return True
    current = dest
    while current != user_root:
        if current.is_dir() and server_data_is_user_owned_link(current, username):
            return True
        parent = current.parent
        if parent == current:
            break
        current = parent
    return False


def validate_user_server_data_operation(
    action: str,
    source: Path,
    source_raw: str,
    destination: Path | None,
    destination_raw: str,
    actor_username: str,
) -> None:
    actor_username = normalize_username(actor_username)
    source_top = server_data_path_top(source_raw)
    destination_top = server_data_path_top(destination_raw)
    source_parts = [part for part in clean_path_value(source_raw).split("/") if part]
    if action == "clear_immediate":
        return
    if not actor_username:
        raise RuntimeError("Login required.")
    if destination is not None:
        if destination_top != actor_username.lower():
            raise RuntimeError("Learners can only place items inside their own QM-Home folder.")
        if not server_data_user_destination_allowed(destination, actor_username):
            raise RuntimeError("Learners can only place items in their own root folder or inside folders they added themselves.")
    if action == "copy_link":
        if source_top == "common":
            if len(source_parts) <= 1:
                raise RuntimeError("Choose a file or folder inside common, not the common root.")
            return
        if source_top == actor_username.lower() and server_data_is_user_owned_link(source, actor_username):
            return
        raise RuntimeError("Learners can only get common items or copy links they added themselves.")
    if action in {"move", "delete_link", "rename"}:
        if source_top != actor_username.lower() or not server_data_is_user_owned_link(source, actor_username):
            raise RuntimeError("Learners can only move or remove links they added themselves.")
        return
    raise RuntimeError("This QM-Home operation is not allowed.")


def server_data_operation(payload: dict, actor_username: str = "") -> dict:
    actor_username = normalize_username(actor_username)
    source_raw = clean_path_value(payload.get("source", "") or payload.get("path", ""))
    destination_raw = clean_path_value(payload.get("destination", "") or payload.get("target", "") or payload.get("folder", ""))
    action = clean(payload.get("action", "")).lower().replace("-", "_")
    if action in {"copy", "copy_link", "link", "copylink", "get"}:
        action = "copy_link"
    if action in {"cut", "paste_move"}:
        action = "move"
    if action in {"delete", "delete_link", "remove_link", "unlink"}:
        action = "delete_link"
    if action in {"clear", "clear_immediate", "clear_immediate_mission", "cleanup_immediate"}:
        action = "clear_immediate"
    if action in {"mkdir", "new_folder"}:
        action = "create_folder"
    if action in {"move_up", "move_down"}:
        action = "reorder"
    if action not in {"copy_link", "move", "rename", "reorder", "create_folder", "delete_link", "clear_immediate"}:
        raise RuntimeError("Unknown server data operation.")
    actor_is_admin = is_admin_user(actor_username)
    if not actor_username:
        raise RuntimeError("Login required.")
    # Added 2026-07-23: browser Vault operations are metadata-only.  Keep the
    # old filesystem branch below only for the explicit legacy cleanup action;
    # this prevents rename/move/copy/remove from touching lesson bytes.
    vault_operation = globals().get("server_database_vault_operation")
    if action != "clear_immediate" and bool(globals().get("SERVER_DATABASE_VAULT_ENABLED", True)) and callable(vault_operation):
        virtual_result = vault_operation(payload, actor_username)
        if virtual_result:
            scoped_clear = globals().get("clear_server_data_list_cache_for_user")
            if callable(scoped_clear):
                scoped_clear(payload.get("target_user", "") or payload.get("user", "") or actor_username)
            else:
                clear_server_data_list_cache()
            return {"operation": action, "source": source_raw, "destination": destination_raw, "result": virtual_result, "virtual": True}
    if not source_raw:
        raise RuntimeError("Missing source path.")
    if action in {"copy_link", "move", "create_folder"} and not destination_raw:
        raise RuntimeError("Missing destination folder.")
    source = safe_server_data_path(source_raw, actor_username, admin=actor_is_admin)
    if not source.exists():
        raise RuntimeError("Source does not exist.")
    destination = None
    if action not in {"delete_link", "clear_immediate"}:
        destination = safe_server_data_path(destination_raw, actor_username, admin=actor_is_admin)
        if not destination.exists() or not destination.is_dir():
            raise RuntimeError("Destination must be a folder.")
    if not actor_is_admin:
        validate_user_server_data_operation(action, source, source_raw, destination, destination_raw, actor_username)
    source_rel_parts = [part for part in clean_path_value(source_raw).split("/") if part]
    if action == "move" and len(source_rel_parts) <= 1:
        raise RuntimeError("Cannot move QM-Home root folders.")
    with SERVER_DATA_LOCK:
        if action == "clear_immediate":
            result = clear_server_data_immediate_mission_item(source, source_raw, actor_username)
            operation = "clear_immediate"
        elif action == "delete_link":
            if source.is_dir():
                if not read_server_data_folder_link_payload(source):
                    raise RuntimeError("Only linked folders can be deleted with this action.")
                result = {"path": server_data_relative(source), "name": source.name, "type": "folder"}
                shutil.rmtree(source)
                delete_folder_link = globals().get("server_database_delete_folder_link")
                if callable(delete_folder_link):
                    delete_folder_link(result["path"])
            else:
                if not read_server_data_link_payload(source):
                    raise RuntimeError("Only linked files can be deleted with this action.")
                result = {"path": server_data_relative(source), "name": source.name, "type": "file"}
                source.unlink()
            operation = "delete_link"
        elif action == "copy_link":
            try:
                if source.is_dir() and destination.resolve().is_relative_to(source.resolve()):
                    raise RuntimeError("Cannot create a linked copy inside the same source folder.")
            except AttributeError:
                if source.is_dir() and str(destination.resolve()).lower().startswith(str(source.resolve()).lower()):
                    raise RuntimeError("Cannot create a linked copy inside the same source folder.")
            if source.is_dir():
                result = copy_server_data_folder_as_links(source, destination, actor_username)
            else:
                destination_file = server_data_unique_child_path(destination, source.name)
                result = write_server_data_file_link(source, destination_file, actor_username)
            operation = "copy_link"
        else:
            try:
                source_resolved = source.resolve()
                destination_resolved = destination.resolve()
                if source.is_dir() and destination_resolved.is_relative_to(source_resolved):
                    raise RuntimeError("Cannot move a folder into itself.")
            except AttributeError:
                if source.is_dir() and str(destination.resolve()).lower().startswith(str(source.resolve()).lower()):
                    raise RuntimeError("Cannot move a folder into itself.")
            target_path = server_data_unique_child_path(destination, source.name)
            shutil.move(str(source), str(target_path))
            result = {
                "path": server_data_relative(target_path),
                "name": target_path.name,
                "type": "folder" if target_path.is_dir() else "file",
            }
            operation = "move"
    clear_lesson_metadata_cache()
    clear_server_data_list_cache()
    if operation == "clear_immediate":
        refresh_server_data_manifest_paths_now(
            [
                source_raw,
                "/".join([part for part in clean_path_value(source_raw).split("/")[:-1] if part]),
            ],
            "server-data-clear-immediate",
        )
    else:
        result_path = result.get("path", "") if isinstance(result, dict) else ""
        source_parent_raw = "/".join([part for part in clean_path_value(source_raw).split("/")[:-1] if part])
        destination_parent_raw = "/".join([part for part in clean_path_value(destination_raw).split("/")[:-1] if part])
        if operation == "copy_link":
            changed_paths = [destination_raw, result_path, destination_parent_raw]
        elif operation == "delete_link":
            changed_paths = [source_raw, source_parent_raw]
        else:
            changed_paths = [source_raw, source_parent_raw, destination_raw, result_path, destination_parent_raw]
        refresh_server_data_manifest_paths_now(changed_paths, "server-data-op")
    return {"operation": operation, "source": source_raw, "destination": destination_raw, "result": result}


def read_server_data_file(relative_path: str = "", username: str = "", admin: bool = False) -> bytes:
    target = safe_server_data_path(relative_path, username, admin=admin)
    target = server_data_effective_file_path(target, username=username, admin=admin)
    if not target.is_file() or not is_lesson_file(target):
        raise RuntimeError("Chi duoc nap file Space_W/Space_V/Space_B/Space_Q/Space_P/PDF/TXT trong C:\\server data.")
    return cached_server_data_file_bytes(target)
