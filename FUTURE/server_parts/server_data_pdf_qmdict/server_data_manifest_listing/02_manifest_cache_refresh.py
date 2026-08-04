# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.


# Added 2026-07-30: old boot snapshots may predate root filtering. Sanitize
# them in RAM and on disk instead of exposing infrastructure folders again.
def sanitize_server_data_manifest_roots(manifest: dict) -> bool:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("folders"), dict):
        return False
    folders = manifest.get("folders")
    allowed = server_data_manifest_allowed_top_names()
    changed = False
    root_rows = folders.get("") if isinstance(folders.get(""), list) else []
    next_root_rows = [
        row for row in root_rows
        if isinstance(row, dict)
        and clean_path_value(row.get("path", "")).split("/", 1)[0].lower() in allowed
    ]
    if len(next_root_rows) != len(root_rows):
        folders[""] = next_root_rows
        changed = True
    for path in list(folders):
        clean_path = clean_path_value(path)
        if clean_path and clean_path.split("/", 1)[0].lower() not in allowed:
            folders.pop(path, None)
            changed = True
    revisions = manifest.get("runtime_root_revisions") if isinstance(manifest.get("runtime_root_revisions"), dict) else {}
    next_revisions = {root: revision for root, revision in revisions.items() if clean(root).lower() in allowed}
    if len(next_revisions) != len(revisions):
        manifest["runtime_root_revisions"] = next_revisions
        manifest["runtime_revision"] = hashlib.sha1(
            "|".join(f"{root}:{revision}" for root, revision in sorted(next_revisions.items())).encode("utf-8", "ignore")
        ).hexdigest()
        changed = True
    if changed:
        manifest["updated_at"] = utc_timestamp()
    return changed

def load_server_data_manifest_from_disk() -> dict:
    try:
        if not SERVER_DATA_MANIFEST_FILE.is_file():
            return {}
        payload = json.loads(SERVER_DATA_MANIFEST_FILE.read_text(encoding="utf-8-sig", errors="replace"))
        if isinstance(payload, dict) and isinstance(payload.get("folders"), dict):
            if sanitize_server_data_manifest_roots(payload):
                atomic_write_json(SERVER_DATA_MANIFEST_FILE, payload, indent=None)
            return payload
    except Exception:
        pass
    return {}


def schedule_server_data_manifest_metadata_backfill(manifest: dict, delay: float = 1.0) -> bool:
    with SERVER_DATA_MANIFEST_LOCK:
        if SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply"):
            return False
    if int((manifest or {}).get("structural_metadata_version", 0) or 0) >= SERVER_DATA_STRUCTURAL_METADATA_VERSION:
        return False

    def _run() -> None:
        try:
            started = time.perf_counter()
            refreshed = refresh_server_data_manifest_now("structural-metadata-backfill")
            file_rows = sum(
                1
                for rows in ((refreshed or {}).get("folders") or {}).values()
                for row in (rows or [])
                if isinstance(row, dict) and clean(row.get("type", "")) == "file"
            )
            print(
                f"Server data structural metadata ready: {file_rows} files in {int((time.perf_counter() - started) * 1000)}ms.",
                flush=True,
            )
            tree_warm = warm_server_data_tree_preload_cache(refreshed)
            print(
                f"Server data tree preload warm: {tree_warm.get('users', 0)} users, {tree_warm.get('cpu_ms', 0)}ms CPU, {tree_warm.get('gzip_bytes', 0)} gzip bytes.",
                flush=True,
            )
            overlay_warm = warm_server_data_user_overlay_cache(refreshed)
            print(
                f"Server data user overlay warm: {overlay_warm.get('users', 0)} users, {overlay_warm.get('cpu_ms', 0)}ms CPU, {overlay_warm.get('gzip_bytes', 0)} gzip bytes.",
                flush=True,
            )
        except Exception as exc:
            stt_debug_log("server_data_structural_metadata_backfill_failed", error=str(exc))

    timer = threading.Timer(max(0.1, float(delay or 1.0)), _run)
    timer.daemon = True
    timer.start()
    return True


def rebuild_server_data_manifest(force: bool = False, signature: str = "") -> dict:
    with SERVER_DATA_MANIFEST_LOCK:
        current = SERVER_DATA_MANIFEST_STATE.get("manifest")
        if not force and not SERVER_DATA_MANIFEST_STATE.get("dirty") and isinstance(current, dict):
            return current
        SERVER_DATA_MANIFEST_STATE["dirty"] = False
    try:
        manifest = build_server_data_manifest(signature=signature)
    except Exception as exc:
        stt_debug_log("server_data_manifest_build_failed", error=str(exc))
        with SERVER_DATA_MANIFEST_LOCK:
            SERVER_DATA_MANIFEST_STATE["dirty"] = True
            cached = SERVER_DATA_MANIFEST_STATE.get("manifest")
        return cached if isinstance(cached, dict) else {"version": 1, "root": str(SERVER_DATA_ROOT), "folders": {"": []}}
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
        SERVER_DATA_MANIFEST_STATE["dirty"] = False
        if signature:
            SERVER_DATA_MANIFEST_STATE["signature"] = clean(signature)
    schedule_future_boot_snapshot_write("manifest_rebuild", delay=1.0)
    ensure_server_data_lesson_identity_registry(manifest)
    return manifest


def get_server_data_manifest(force: bool = False) -> dict:
    with SERVER_DATA_MANIFEST_LOCK:
        cached = SERVER_DATA_MANIFEST_STATE.get("manifest")
        dirty = bool(SERVER_DATA_MANIFEST_STATE.get("dirty"))
    if force:
        signature = server_data_manifest_signature()
        return rebuild_server_data_manifest(force=True, signature=signature)
    if isinstance(cached, dict):
        if sanitize_server_data_manifest_roots(cached):
            try:
                atomic_write_json(SERVER_DATA_MANIFEST_FILE, cached, indent=None)
                schedule_future_boot_snapshot_write("manifest_root_sanitize", delay=0.5)
            except Exception as exc:
                stt_debug_log("server_data_manifest_root_sanitize_write_failed", error=str(exc))
        # Added 2026-07-28: once runtime revisions are already warm, return the
        # cached manifest directly instead of re-entering revision synthesis on
        # every browse/login request.
        if (
            int(cached.get("runtime_root_revision_version", 0) or 0) == 1
            and clean(cached.get("runtime_revision", ""))
            and isinstance(cached.get("runtime_root_revisions"), dict)
        ):
            return cached
        # Keep browsing responsive while the watcher/timer refreshes a dirty manifest.
        return ensure_server_data_manifest_runtime_revisions(cached)
    disk = load_server_data_manifest_from_disk()
    if disk:
        runtime_revisions_before = (
            int(disk.get("runtime_root_revision_version", 0) or 0),
            clean(disk.get("runtime_revision", "")),
            dict(disk.get("runtime_root_revisions") or {}) if isinstance(disk.get("runtime_root_revisions"), dict) else {},
        )
        ensure_server_data_manifest_runtime_revisions(disk)
        runtime_revisions_changed = runtime_revisions_before != (
            int(disk.get("runtime_root_revision_version", 0) or 0),
            clean(disk.get("runtime_revision", "")),
            dict(disk.get("runtime_root_revisions") or {}) if isinstance(disk.get("runtime_root_revisions"), dict) else {},
        )
        if runtime_revisions_changed:
            # Added 2026-07-22: persist one-time root revision cleanup during startup instead of carrying stale disk keys.
            disk["updated_at"] = utc_timestamp()
            try:
                atomic_write_json(SERVER_DATA_MANIFEST_FILE, disk, indent=None)
            except Exception as exc:
                stt_debug_log("server_data_manifest_runtime_revision_write_failed", error=str(exc))
        with SERVER_DATA_MANIFEST_LOCK:
            SERVER_DATA_MANIFEST_STATE["manifest"] = disk
        ensure_server_data_lesson_identity_registry(disk)
        return disk
    return rebuild_server_data_manifest(force=dirty)


# Added 2026-07-21: parent folders are scan scopes, while only the deepest touched paths are identity scopes.
def server_data_lesson_identity_delta_scopes(relative_paths: set[str] | list[str] | tuple[str, ...]) -> set[str]:
    candidates = sorted(
        {clean_path_value(path) for path in (relative_paths or []) if clean_path_value(path)},
        key=lambda path: (-path.count("/"), path.lower()),
    )
    selected: list[str] = []
    for path in candidates:
        lower_path = path.lower()
        if any(item.lower() == lower_path or item.lower().startswith(f"{lower_path}/") for item in selected):
            continue
        selected.append(path)
    return set(selected)


# Added 2026-07-21: large branch scans produce SQLite writes only for lesson identities that actually changed.
def server_data_manifest_identity_snapshot(folders: dict, relative_paths: set[str] | list[str] | tuple[str, ...]) -> dict[str, tuple]:
    scopes = {clean_path_value(path).lower() for path in (relative_paths or []) if clean_path_value(path)}
    if not scopes or not isinstance(folders, dict):
        return {}
    snapshot: dict[str, tuple] = {}
    for rows in folders.values():
        for entry in rows if isinstance(rows, list) else []:
            if not isinstance(entry, dict) or clean(entry.get("type", "")).lower() != "file":
                continue
            path = clean_path_value(entry.get("path", ""))
            lower_path = path.lower()
            if not path or not any(lower_path == scope or lower_path.startswith(f"{scope}/") for scope in scopes):
                continue
            snapshot[path] = (
                clean(entry.get("lesson_id", ""))[:240],
                clean(entry.get("content_fingerprint", ""))[:320],
                int(entry.get("modified_ns", 0) or 0),
                int(entry.get("size", 0) or 0),
            )
    return snapshot


# Added 2026-07-21: persist only watcher-touched Space identity rows; old paths remain aliases for progress lookup.
def sync_server_data_lesson_identity_paths(manifest: dict, relative_paths: set[str] | list[str] | tuple[str, ...]) -> dict:
    normalized = server_data_lesson_identity_delta_scopes(relative_paths)
    if not normalized or not isinstance(manifest, dict):
        return {"registered": 0, "inactive": 0}
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    entries = []
    for rows in folders.values():
        for entry in rows if isinstance(rows, list) else []:
            if not isinstance(entry, dict) or clean(entry.get("type", "")).lower() != "file":
                continue
            path = clean_path_value(entry.get("path", ""))
            if path and any(path == target or path.startswith(f"{target}/") for target in normalized):
                if clean(entry.get("lesson_id", "")):
                    entries.append(dict(entry))
    register = globals().get("server_database_register_lesson_file_entries")
    result = register(entries, normalized) if callable(register) else {}
    return {
        "registered": max(0, int((result or {}).get("registered", 0) or 0)) if isinstance(result, dict) else 0,
        "collisions": max(0, int((result or {}).get("collisions", 0) or 0)) if isinstance(result, dict) else 0,
        "inactive": max(0, int((result or {}).get("inactive", 0) or 0)) if isinstance(result, dict) else 0,
    }


def ensure_server_data_lesson_identity_registry(manifest: dict) -> dict:
    count_reader = globals().get("server_database_lesson_file_count")
    register = globals().get("server_database_register_lesson_file_entries")
    if not callable(count_reader) or not callable(register) or int(count_reader() or 0) > 0:
        return {"registered": 0, "reason": "already_ready"}
    folders = manifest.get("folders") if isinstance(manifest, dict) and isinstance(manifest.get("folders"), dict) else {}
    entries = [
        dict(entry)
        for rows in folders.values()
        for entry in (rows if isinstance(rows, list) else [])
        if isinstance(entry, dict) and clean(entry.get("type", "")).lower() == "file" and clean(entry.get("lesson_id", ""))
    ]
    return register(entries) if entries else {"registered": 0, "reason": "manifest_missing_ids"}


# Added 2026-07-21: keep cheap delta freshness separate from the expensive full-tree integrity signature.
def ensure_server_data_manifest_runtime_revisions(manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        return manifest
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    roots = {
        clean_path_value(entry.get("path", "")).split("/", 1)[0].lower()
        for entry in (folders.get("") or [])
        if isinstance(entry, dict) and clean_path_value(entry.get("path", ""))
    }
    previous_root_revisions = (
        dict(manifest.get("runtime_root_revisions") or {})
        if isinstance(manifest.get("runtime_root_revisions"), dict)
        else {}
    )
    # Added 2026-07-22: deleted roots must not survive as cache identities after their folder rows are gone.
    root_revisions = {
        root: clean(previous_root_revisions.get(root, ""))
        for root in roots
        if clean(previous_root_revisions.get(root, ""))
    }
    for root in roots:
        if not clean(root_revisions.get(root, "")):
            root_revisions[root] = server_data_manifest_root_revision(folders, root)
    revisions_changed = (
        int(manifest.get("runtime_root_revision_version", 0) or 0) != 1
        or root_revisions != previous_root_revisions
    )
    manifest["runtime_root_revisions"] = root_revisions
    manifest["runtime_root_revision_version"] = 1
    if revisions_changed or not clean(manifest.get("runtime_revision", "")):
        previous_revision = clean(manifest.get("runtime_revision", "")) or clean(manifest.get("signature", ""))
        manifest["runtime_revision"] = hashlib.sha1(
            f"{previous_revision}|".encode("utf-8", "ignore")
            + "|".join(f"{root}:{revision}" for root, revision in sorted(root_revisions.items())).encode("utf-8", "ignore")
        ).hexdigest()
    return manifest


def server_data_manifest_runtime_revision(manifest: dict | None = None, roots: object = None) -> str:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    if not isinstance(source, dict):
        return ""
    global_revision = clean(source.get("runtime_revision", "")) or clean(source.get("signature", ""))
    scoped_roots = sorted({clean(root).lower() for root in (roots or []) if clean(root)})
    if not scoped_roots:
        return global_revision
    cache_key = (global_revision, tuple(scoped_roots))
    cache = globals().setdefault("SERVER_DATA_MANIFEST_RUNTIME_REVISION_CACHE", {})
    cached = cache.get(cache_key) if isinstance(cache, dict) else None
    if isinstance(cached, str):
        return cached
    root_revisions = source.get("runtime_root_revisions") if isinstance(source.get("runtime_root_revisions"), dict) else {}
    if (
        int(source.get("runtime_root_revision_version", 0) or 0) == 1
        and global_revision
        and isinstance(root_revisions, dict)
    ):
        parts = [
            f"{root}:{clean(root_revisions.get(root, '')) or 'absent'}"
            for root in scoped_roots
        ]
        revision = hashlib.sha1("|".join(parts).encode("utf-8", "ignore")).hexdigest()
        if isinstance(cache, dict):
            cache[cache_key] = revision
            if len(cache) > 4096:
                for old_key in list(cache.keys())[:1024]:
                    if old_key != cache_key:
                        cache.pop(old_key, None)
        return revision
    ensure_server_data_manifest_runtime_revisions(source)
    root_revisions = source.get("runtime_root_revisions") if isinstance(source.get("runtime_root_revisions"), dict) else {}
    parts = [
        f"{root}:{clean(root_revisions.get(root, '')) or server_data_manifest_root_revision(source.get('folders') or {}, root)}"
        for root in scoped_roots
    ]
    revision = hashlib.sha1("|".join(parts).encode("utf-8", "ignore")).hexdigest()
    if isinstance(cache, dict):
        cache[cache_key] = revision
        if len(cache) > 4096:
            for old_key in list(cache.keys())[:1024]:
                if old_key != cache_key:
                    cache.pop(old_key, None)
    return revision


def server_data_manifest_paths_fingerprint(folders: dict, relative_paths: object) -> str:
    paths = {
        clean_path_value(path)
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not isinstance(folders, dict) or not paths:
        return ""
    selected = []
    for raw_key, rows in folders.items():
        key = clean_path_value(raw_key)
        related = key == "" or any(
            key == path or key.startswith(f"{path}/") or path.startswith(f"{key}/")
            for path in paths
        )
        if related:
            selected.append((key, rows if isinstance(rows, list) else []))
    selected.sort(key=lambda item: (item[0].count("/"), item[0].lower()))
    data = json.dumps(selected, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha1(data).hexdigest()


# Added 2026-07-21: removing a top-level root must also remove its empty/stale descendant manifest rows.
def remove_server_data_manifest_subtree(folders: dict, relative_path: str) -> int:
    rel = clean_path_value(relative_path)
    if not rel or not isinstance(folders, dict):
        return 0
    removed = 0
    for key in list(folders.keys()):
        if key == rel or key.startswith(f"{rel}/"):
            folders.pop(key, None)
            removed += 1
    return removed


def update_server_data_manifest_runtime_revision(
    manifest: dict,
    before_fingerprint: str,
    after_fingerprint: str,
    relative_paths: object = None,
) -> str:
    current = server_data_manifest_runtime_revision(manifest)
    if before_fingerprint == after_fingerprint:
        manifest["runtime_revision"] = current
        return current
    seed = f"{current}|{after_fingerprint}|{time.time_ns()}"
    revision = hashlib.sha1(seed.encode("utf-8", "ignore")).hexdigest()
    manifest["runtime_revision"] = revision
    root_revisions = dict(manifest.get("runtime_root_revisions") or {}) if isinstance(manifest.get("runtime_root_revisions"), dict) else {}
    changed_roots = {
        clean_path_value(path).split("/", 1)[0].lower()
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    active_roots = {
        clean_path_value(entry.get("path", "")).split("/", 1)[0].lower()
        for entry in (folders.get("") or [])
        if isinstance(entry, dict) and clean_path_value(entry.get("path", ""))
    }
    for root in changed_roots:
        if root not in active_roots:
            root_revisions.pop(root, None)
            continue
        previous = clean(root_revisions.get(root, "")) or hashlib.sha1(
            f"{clean(manifest.get('signature', ''))}|{root}".encode("utf-8", "ignore")
        ).hexdigest()
        root_revisions[root] = hashlib.sha1(f"{previous}|{after_fingerprint}|{time.time_ns()}".encode("utf-8", "ignore")).hexdigest()
    manifest["runtime_root_revisions"] = root_revisions
    return revision


def update_server_data_manifest_top_root_entry(folders: dict, relative_path: str) -> bool:
    rel = clean_path_value(relative_path)
    if not isinstance(folders, dict) or not rel or "/" in rel:
        return False
    root_key = rel.lower()
    root_entries = [
        dict(entry)
        for entry in (folders.get("") or [])
        if isinstance(entry, dict) and clean_path_value(entry.get("path", "")).split("/", 1)[0].lower() != root_key
    ]
    target = server_data_manifest_path(rel)
    try:
        if target.is_dir() and root_key in server_data_manifest_allowed_top_names() and not server_data_manifest_should_skip(target):
            entry = server_data_manifest_entry(target)
            if isinstance(entry, dict):
                root_entries.append(entry)
    except Exception:
        pass
    root_entries.sort(key=lambda entry: (clean(entry.get("name", "")).lower() != "common", natural_sort_key(entry.get("name", ""))))
    folders[""] = root_entries
    return True


def mark_server_data_manifest_dirty(reason: str = "") -> None:
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["dirty"] = True
        SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)


def schedule_server_data_manifest_rebuild(delay: float = 0.8) -> None:
    mark_server_data_manifest_dirty("scheduled")
    with SERVER_DATA_MANIFEST_LOCK:
        timer = SERVER_DATA_MANIFEST_STATE.get("timer")
        if timer is not None and getattr(timer, "is_alive", lambda: False)():
            return

        def _run() -> None:
            try:
                signature = server_data_manifest_signature()
                rebuild_server_data_manifest(force=True, signature=signature)
                with SERVER_DATA_MANIFEST_LOCK:
                    SERVER_DATA_MANIFEST_STATE["signature"] = signature
                    published = bool(SERVER_DATA_MANIFEST_STATE.get("build_hold_publish_in_progress"))
                    if published:
                        SERVER_DATA_MANIFEST_STATE["build_hold_publish_in_progress"] = False
                        SERVER_DATA_MANIFEST_STATE["build_hold_requires_apply"] = False
                        SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = False
                        SERVER_DATA_MANIFEST_STATE["pending_paths"] = set()
                if published:
                    server_data_manifest_build_pending_persist(False)
            except Exception:
                mark_server_data_manifest_dirty("scheduled-rebuild-failed")

        new_timer = threading.Timer(max(0.1, float(delay or 0.8)), _run)
        new_timer.daemon = True
        SERVER_DATA_MANIFEST_STATE["timer"] = new_timer
        new_timer.start()


# Added 2026-07-16: verifies external/offline server-data changes after startup without blocking the server from becoming ready.
def schedule_server_data_manifest_startup_verify(delay: float = 20.0) -> None:
    def _run() -> None:
        try:
            delta = future_boot_snapshot_manifest_delta_paths()
            changed_paths = [clean_path_value(path) for path in (delta.get("changed_paths") or []) if clean_path_value(path) or path == ""]
            with SERVER_DATA_MANIFEST_LOCK:
                staged_restart = bool(SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply"))
                if staged_restart:
                    if delta.get("fallback") or "" in changed_paths:
                        SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = True
                    else:
                        pending = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
                        if not isinstance(pending, set):
                            pending = set()
                            SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending
                        pending.update(path for path in changed_paths if path)
            if staged_restart:
                server_data_manifest_build_pending_persist(True)
                return
            if delta.get("fallback") or "" in changed_paths:
                print(
                    f"Server data startup verify needs full refresh: {clean(delta.get('reason', 'fallback')) or 'fallback'}",
                    flush=True,
                )
                refresh_server_data_manifest_now("startup-delta-fallback")
            elif changed_paths:
                print(f"Server data startup verify changed branches: {len(changed_paths)}", flush=True)
                refresh_server_data_manifest_delta_paths_now(changed_paths, "startup-delta-branches")
            else:
                schedule_future_boot_snapshot_write("manifest_startup_verify", delay=1.0)
        except Exception as exc:
            stt_debug_log("server_data_manifest_startup_verify_failed", error=str(exc))

    timer = threading.Timer(max(1.0, float(delay or 20.0)), _run)
    timer.daemon = True
    timer.start()


SERVER_DATA_BUILD_HOLD_SECONDS = max(60.0, min(900.0, float(os.environ.get("FUTURE_SERVER_DATA_BUILD_HOLD_SECONDS", "300") or 300)))
SERVER_DATA_BUILD_PENDING_FILE = SERVER_DATA_ROOT / "_future_manifest_build_pending.json"


def server_data_manifest_build_pending_persist(dirty: bool = True) -> None:
    with SERVER_DATA_MANIFEST_LOCK:
        sessions = SERVER_DATA_MANIFEST_STATE.get("build_sessions") if isinstance(SERVER_DATA_MANIFEST_STATE.get("build_sessions"), dict) else {}
        pending_paths = sorted({
            clean_path_value(path)
            for path in (SERVER_DATA_MANIFEST_STATE.get("pending_paths") or set())
            if clean_path_value(path)
        })
        payload = {
            "version": 1,
            "dirty": bool(dirty),
            "updated_at": utc_timestamp(),
            "active_builders": [dict(row) for row in sessions.values() if isinstance(row, dict)],
            "pending_paths": pending_paths,
            "full_refresh_pending": bool(SERVER_DATA_MANIFEST_STATE.get("build_hold_full_refresh_pending")),
        }
    server_database_store_document_now(
        SERVER_DATA_BUILD_PENDING_FILE,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        authoritative=True,
    )
    try:
        SERVER_DATA_BUILD_PENDING_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError as exc:
        stt_debug_log("server_data_build_pending_marker_write_failed", error=str(exc))


def restore_server_data_manifest_build_pending() -> bool:
    payload = server_database_read_document_json(SERVER_DATA_BUILD_PENDING_FILE, {})
    if not isinstance(payload, dict) or not payload.get("dirty"):
        try:
            payload = json.loads(SERVER_DATA_BUILD_PENDING_FILE.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception:
            payload = {}
    if not isinstance(payload, dict) or not payload.get("dirty"):
        return False
    active_builders = [dict(row) for row in (payload.get("active_builders") or []) if isinstance(row, dict)]
    pending_paths = {
        clean_path_value(path)
        for path in (payload.get("pending_paths") or [])
        if clean_path_value(path)
    }
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["build_hold_active"] = False
        SERVER_DATA_MANIFEST_STATE["build_hold_requires_apply"] = bool(active_builders)
        SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = bool(payload.get("full_refresh_pending"))
        SERVER_DATA_MANIFEST_STATE["pending_paths"] = set(pending_paths)
        SERVER_DATA_MANIFEST_STATE["build_sessions"] = {
            f"recovered-{index}": row for index, row in enumerate(active_builders)
        }
    if active_builders:
        return True
    # Added 2026-08-04: a completed builder marker is recovered before startup tree warming.
    if payload.get("full_refresh_pending") or not pending_paths:
        with SERVER_DATA_MANIFEST_LOCK:
            previous_manifest = SERVER_DATA_MANIFEST_STATE.get("manifest")
            previous_folders = previous_manifest.get("folders") if isinstance(previous_manifest, dict) and isinstance(previous_manifest.get("folders"), dict) else {}
        identity_roots = set(server_data_manifest_allowed_top_names())
        before_identity = server_data_manifest_identity_snapshot(previous_folders, identity_roots)
        recovered_manifest = refresh_server_data_manifest_now("startup-builder-recovery")
        recovered_folders = recovered_manifest.get("folders") if isinstance(recovered_manifest.get("folders"), dict) else {}
        after_identity = server_data_manifest_identity_snapshot(recovered_folders, identity_roots)
        changed_identity_paths = {
            path for path in set(before_identity).union(after_identity)
            if before_identity.get(path) != after_identity.get(path)
        }
        if changed_identity_paths:
            sync_server_data_lesson_identity_paths(recovered_manifest, changed_identity_paths)
    else:
        refresh_server_data_manifest_delta_paths_now(pending_paths, "startup-builder-recovery")
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["pending_paths"] = set()
        SERVER_DATA_MANIFEST_STATE["build_hold_requires_apply"] = False
        SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = False
    server_data_manifest_build_pending_persist(False)
    return True


# Added 2026-07-30: hold manifest publication while a local builder is actively emitting files.
def server_data_manifest_build_hold_note_activity(reason: str = "builder") -> dict:
    now = time.monotonic()
    with SERVER_DATA_MANIFEST_LOCK:
        state = SERVER_DATA_MANIFEST_STATE
        first_activity = not bool(state.get("build_hold_requires_apply"))
        state["build_hold_active"] = True
        if not float(state.get("build_hold_started_at", 0.0) or 0.0):
            state["build_hold_started_at"] = now
        state["build_hold_last_activity_at"] = now
        state["build_hold_until"] = now + SERVER_DATA_BUILD_HOLD_SECONDS
        state["build_hold_requires_apply"] = True
        state["build_hold_requests"] = int(state.get("build_hold_requests", 0) or 0) + 1
        timer = state.get("build_hold_timer")
        if timer is not None:
            timer.cancel()

        def _expire() -> None:
            with SERVER_DATA_MANIFEST_LOCK:
                if not state.get("build_hold_active"):
                    return
                remaining = float(state.get("build_hold_until", 0.0) or 0.0) - time.monotonic()
                if remaining > 0.05:
                    retry = threading.Timer(remaining, _expire)
                    retry.daemon = True
                    state["build_hold_timer"] = retry
                    retry.start()
                    return
                state["build_hold_active"] = False
                state["build_hold_timer"] = None
                # Five quiet minutes only marks the staged build ready. It does
                # not publish incomplete builder output without admin approval.

        timer = threading.Timer(SERVER_DATA_BUILD_HOLD_SECONDS, _expire)
        timer.daemon = True
        state["build_hold_timer"] = timer
        timer.start()
        status = server_data_manifest_build_hold_status_locked(now)
    if first_activity:
        server_data_manifest_build_pending_persist(True)
    return status


def server_data_manifest_build_hold_status_locked(now: float | None = None) -> dict:
    now = time.monotonic() if now is None else float(now)
    state = SERVER_DATA_MANIFEST_STATE
    until = float(state.get("build_hold_until", 0.0) or 0.0)
    pending = state.get("pending_paths") if isinstance(state.get("pending_paths"), set) else set()
    sessions = state.get("build_sessions") if isinstance(state.get("build_sessions"), dict) else {}
    return {
        "active": bool(state.get("build_hold_active")) and until > now,
        "pending_paths": len(pending),
        "last_activity_age_ms": int(max(0.0, now - float(state.get("build_hold_last_activity_at", 0.0) or 0.0)) * 1000) if state.get("build_hold_last_activity_at") else 0,
        "apply_in_ms": int(max(0.0, until - now) * 1000) if until > now else 0,
        "running": bool(state.get("paths_running")),
        "apply_requested": bool(state.get("build_hold_apply_requested")),
        "requires_apply": bool(state.get("build_hold_requires_apply")),
        "builder_requests": int(state.get("build_hold_requests", 0) or 0),
        "active_builders": len(sessions),
        "builders": sorted({clean(row.get("space", "")) for row in sessions.values() if isinstance(row, dict) and clean(row.get("space", ""))}),
        "full_refresh_pending": bool(state.get("build_hold_full_refresh_pending")),
        "publish_in_progress": bool(state.get("build_hold_publish_in_progress")),
    }


def server_data_manifest_build_hold_status() -> dict:
    with SERVER_DATA_MANIFEST_LOCK:
        return server_data_manifest_build_hold_status_locked()


# Added 2026-08-04: builder output paths are accepted only as exact lesson files below Server Data.
def server_data_manifest_builder_output_path(path_value: object) -> tuple[Path | None, str]:
    raw = clean(path_value)
    if not raw:
        return None, ""
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = server_data_manifest_path(clean_path_value(raw))
    try:
        target = candidate.resolve()
        relative = target.relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
    except Exception as exc:
        raise RuntimeError("Builder output must stay inside Server Data.") from exc
    if target.suffix.lower() not in LESSON_FILE_SUFFIXES:
        return target, clean_path_value(relative)
    return target, clean_path_value(relative)


# Added 2026-08-04: publish one completed builder file directly into manifest, identity registry, and RAM.
def publish_server_data_manifest_builder_output(space: str, path_value: object) -> dict:
    target, relative = server_data_manifest_builder_output_path(path_value)
    if target is None or not relative or target.suffix.lower() not in LESSON_FILE_SUFFIXES:
        return {"published": False, "reason": "output_not_exact_lesson_file", "path": relative}
    if not target.is_file():
        raise RuntimeError("Completed builder output does not exist.")
    expected_suffix = {
        "SPACE_PDF": ".space_pdf",
        "SPACE_PICTURE": ".space_picture",
        "SPACE_Q": ".space_q",
        "SPACE_W": ".space_w",
        "SPACE_V": ".space_v",
        "SPACE_P": ".space_p",
        "SPACE_L": ".space_l",
        "SPACE_S": ".space_s",
    }.get(clean(space).upper())
    if expected_suffix and target.suffix.lower() != expected_suffix:
        raise RuntimeError(f"Builder output extension does not match {clean(space)}.")
    clear_lesson_metadata_cache()
    clear_server_data_list_cache_paths({relative, clean_path_value(relative.rsplit("/", 1)[0])})
    manifest = refresh_server_data_manifest_delta_paths_now({relative}, f"builder-finish:{clean(space).lower()}")
    identity_result = sync_server_data_lesson_identity_paths(manifest, {relative})
    parent = clean_path_value(relative.rsplit("/", 1)[0]) if "/" in relative else ""
    entry = next((
        dict(row)
        for row in ((manifest.get("folders") or {}).get(parent) or [])
        if isinstance(row, dict) and clean_path_value(row.get("path", "")).casefold() == relative.casefold()
    ), None)
    if not entry:
        raise RuntimeError("Builder output was not accepted into the lesson manifest.")
    if target.suffix.lower() in {".space_pdf", ".space_picture"} and not clean(entry.get("lesson_id", "")):
        raise RuntimeError("Published package is missing its lesson ID.")
    server_data_tree_compact_base(manifest)
    return {
        "published": True,
        "path": relative,
        "lesson_id": clean(entry.get("lesson_id", "")),
        "document_id": clean(entry.get("document_id", "")),
        "identity_registered": max(0, int(identity_result.get("registered", 0) or 0)),
        "runtime_revision": server_data_manifest_runtime_revision(manifest),
        "updated_at": clean(manifest.get("updated_at", "")),
    }


def server_data_manifest_builder_session_event(payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    action = clean(source.get("action", "")).lower() or "start"
    session_id = clean(source.get("session_id", ""))[:120]
    space = clean(source.get("space", "")).upper()[:16]
    output_path = clean(source.get("path", ""))
    _output_target, output_relative = server_data_manifest_builder_output_path(output_path) if output_path else (None, "")
    with SERVER_DATA_MANIFEST_LOCK:
        sessions = SERVER_DATA_MANIFEST_STATE.get("build_sessions")
        if not isinstance(sessions, dict):
            sessions = {}
            SERVER_DATA_MANIFEST_STATE["build_sessions"] = sessions
        if session_id:
            if action == "start":
                sessions[session_id] = {"space": space, "path": output_relative, "started_at": utc_timestamp()}
            else:
                row = dict(sessions.get(session_id) or {})
                row.update({"space": space or row.get("space", ""), "path": output_relative or row.get("path", ""), "status": action, "finished_at": utc_timestamp()})
                if action in {"finish", "failed"}:
                    sessions.pop(session_id, None)
                else:
                    sessions[session_id] = row
        status = server_data_manifest_build_hold_status_locked()
        status["active_builders"] = len(sessions)
        status["builders"] = sorted({clean(row.get("space", "")) for row in sessions.values() if isinstance(row, dict) and clean(row.get("space", ""))})
        if action in {"finish", "failed"} and not sessions:
            SERVER_DATA_MANIFEST_STATE["build_hold_active"] = False
    if output_path and action == "start":
        server_data_manifest_build_hold_note_activity(f"builder-session:{action}")
    publication = {"published": False, "reason": "not_finished", "path": output_relative}
    if action == "finish":
        publication = publish_server_data_manifest_builder_output(space, output_path)
        if publication.get("published"):
            parent = clean_path_value(output_relative.rsplit("/", 1)[0]) if "/" in output_relative else ""
            with SERVER_DATA_MANIFEST_LOCK:
                pending = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
                if not isinstance(pending, set):
                    pending = set()
                    SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending
                pending.difference_update({output_relative, parent})
                sessions = SERVER_DATA_MANIFEST_STATE.get("build_sessions") if isinstance(SERVER_DATA_MANIFEST_STATE.get("build_sessions"), dict) else {}
                clean_finish = not sessions and not pending and not SERVER_DATA_MANIFEST_STATE.get("build_hold_full_refresh_pending")
                if clean_finish:
                    SERVER_DATA_MANIFEST_STATE["build_hold_active"] = False
                    SERVER_DATA_MANIFEST_STATE["build_hold_requires_apply"] = False
                    SERVER_DATA_MANIFEST_STATE["build_hold_until"] = 0.0
    status = server_data_manifest_build_hold_status()
    marker_dirty = bool(status.get("requires_apply") or status.get("active_builders") or status.get("pending_paths") or status.get("full_refresh_pending"))
    server_data_manifest_build_pending_persist(marker_dirty)
    return {**status, **publication}


def apply_server_data_manifest_build_hold(reason: str = "admin-apply") -> dict:
    with SERVER_DATA_MANIFEST_LOCK:
        state = SERVER_DATA_MANIFEST_STATE
        sessions = state.get("build_sessions") if isinstance(state.get("build_sessions"), dict) else {}
        if sessions or state.get("build_hold_active"):
            raise RuntimeError("Builder is still active; finish the build before publishing staged lessons.")
        state["build_hold_active"] = False
        state["build_hold_until"] = 0.0
        state["build_hold_requires_apply"] = False
        state["build_hold_apply_requested"] = True
        state["build_hold_publish_in_progress"] = True
        timer = state.get("build_hold_timer")
        state["build_hold_timer"] = None
        pending = set(state.get("pending_paths") or set())
        full_refresh = bool(state.get("build_hold_full_refresh_pending"))
    if timer is not None:
        timer.cancel()
    if full_refresh:
        schedule_server_data_manifest_rebuild(0.05)
    elif pending:
        schedule_server_data_manifest_paths_refresh(pending, delay=0.05, reason=reason)
    with SERVER_DATA_MANIFEST_LOCK:
        state["build_hold_apply_requested"] = False
        return server_data_manifest_build_hold_status_locked()


def schedule_server_data_manifest_paths_refresh(relative_paths: list[str] | tuple[str, ...] | set[str], delay: float = 0.8, reason: str = "paths") -> None:
    # Added 2026-07-30: builder activity holds publication for five quiet minutes.
    quiet_seconds = 0.8
    max_wait_seconds = 2.0
    paths = {clean_path_value(item) for item in relative_paths if clean_path_value(item)}
    if not paths:
        return
    with SERVER_DATA_MANIFEST_LOCK:
        pending = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
        if not isinstance(pending, set):
            pending = set()
            SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending
        if not pending:
            SERVER_DATA_MANIFEST_STATE["paths_first_pending_at"] = time.monotonic()
        pending.update(paths)
        if SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply") or (
            SERVER_DATA_MANIFEST_STATE.get("build_hold_active")
            and float(SERVER_DATA_MANIFEST_STATE.get("build_hold_until", 0.0) or 0.0) > time.monotonic()
        ):
            return
        SERVER_DATA_MANIFEST_STATE["build_hold_active"] = False
        timer = SERVER_DATA_MANIFEST_STATE.get("paths_timer")
        if SERVER_DATA_MANIFEST_STATE.get("paths_running") or (
            timer is not None and getattr(timer, "is_alive", lambda: False)()
        ):
            return

        def _run() -> None:
            with SERVER_DATA_MANIFEST_LOCK:
                if SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply") or (
                    SERVER_DATA_MANIFEST_STATE.get("build_hold_active")
                    and float(SERVER_DATA_MANIFEST_STATE.get("build_hold_until", 0.0) or 0.0) > time.monotonic()
                ):
                    SERVER_DATA_MANIFEST_STATE["paths_timer"] = None
                    return
            with SERVER_DATA_MANIFEST_LOCK:
                queued = set(SERVER_DATA_MANIFEST_STATE.get("pending_paths") or set())
                SERVER_DATA_MANIFEST_STATE["pending_paths"] = set()
                SERVER_DATA_MANIFEST_STATE["paths_timer"] = None
                SERVER_DATA_MANIFEST_STATE["paths_first_pending_at"] = 0.0
                SERVER_DATA_MANIFEST_STATE["paths_running"] = True
            if not queued:
                with SERVER_DATA_MANIFEST_LOCK:
                    SERVER_DATA_MANIFEST_STATE["paths_running"] = False
                return
            retry_paths: set[str] = set()
            try:
                refresh_server_data_manifest_delta_paths_now(queued, reason)
            except Exception as exc:
                stt_debug_log("server_data_manifest_paths_refresh_failed", reason=reason, error=str(exc))
                retry_paths = queued
            finally:
                with SERVER_DATA_MANIFEST_LOCK:
                    pending_after = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
                    if not isinstance(pending_after, set):
                        pending_after = set()
                        SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending_after
                    pending_after.update(retry_paths)
                    followup = set(pending_after)
                    first_pending_at = float(SERVER_DATA_MANIFEST_STATE.get("paths_first_pending_at", 0.0) or 0.0)
                    SERVER_DATA_MANIFEST_STATE["paths_running"] = False
                    published = bool(SERVER_DATA_MANIFEST_STATE.get("build_hold_publish_in_progress")) and not retry_paths and not followup
                    if published:
                        SERVER_DATA_MANIFEST_STATE["build_hold_publish_in_progress"] = False
                        SERVER_DATA_MANIFEST_STATE["build_hold_requires_apply"] = False
                        SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = False
                if published:
                    server_data_manifest_build_pending_persist(False)
                if followup:
                    elapsed = max(0.0, time.monotonic() - first_pending_at) if first_pending_at else 0.0
                    schedule_server_data_manifest_paths_refresh(
                        followup,
                        delay=(1.5 if retry_paths else quiet_seconds)
                        if elapsed <= 0
                        else min(quiet_seconds, max(0.15, max_wait_seconds - elapsed)),
                        reason=f"{reason}-retry" if retry_paths else "paths-coalesced",
                    )

        timer = threading.Timer(max(0.15, float(delay or 0.8)), _run)
        timer.daemon = True
        SERVER_DATA_MANIFEST_STATE["paths_timer"] = timer
        timer.start()


def schedule_server_data_manifest_watch_rescan(relative_paths: set[str], delay: float = 2.0) -> None:
    paths = {clean_path_value(item) for item in relative_paths if clean_path_value(item)}
    if not paths:
        return
    with SERVER_DATA_MANIFEST_LOCK:
        pending = SERVER_DATA_MANIFEST_STATE.get("watch_rescan_paths")
        if not isinstance(pending, set):
            pending = set()
            SERVER_DATA_MANIFEST_STATE["watch_rescan_paths"] = pending
        pending.update(paths)
        timer = SERVER_DATA_MANIFEST_STATE.get("watch_rescan_timer")
        if timer is not None and getattr(timer, "is_alive", lambda: False)():
            return

        def _run() -> None:
            with SERVER_DATA_MANIFEST_LOCK:
                queued = set(SERVER_DATA_MANIFEST_STATE.get("watch_rescan_paths") or set())
                SERVER_DATA_MANIFEST_STATE["watch_rescan_paths"] = set()
                SERVER_DATA_MANIFEST_STATE["watch_rescan_timer"] = None
            schedule_server_data_manifest_paths_refresh(queued, delay=0.2, reason="native-watch-settled")

        timer = threading.Timer(max(0.5, float(delay or 2.0)), _run)
        timer.daemon = True
        SERVER_DATA_MANIFEST_STATE["watch_rescan_timer"] = timer
        timer.start()


def server_data_manifest_event_relevant(path_value: object) -> bool:
    try:
        path = Path(str(path_value or ""))
    except Exception:
        return False
    if not str(path):
        return False
    try:
        rel_parts = path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
    except Exception:
        return False
    if not rel_parts or rel_parts[0].startswith("_") or rel_parts[0] in server_data_manifest_skip_tops():
        return False
    if path.name == SERVER_DATA_MANIFEST_FILE.name or path.name.startswith(f".{SERVER_DATA_MANIFEST_FILE.name}"):
        return False
    suffix = path.suffix.lower()
    return (not suffix) or suffix in LESSON_FILE_SUFFIXES


def server_data_manifest_signature() -> str:
    digest = hashlib.sha1()
    count = 0
    try:
        top_folders = list(SERVER_DATA_ROOT.iterdir())
    except OSError:
        top_folders = []
    allowed_top_names = server_data_manifest_allowed_top_names()
    for top in sorted(top_folders, key=lambda item: item.name.lower()):
        try:
            if not top.is_dir() or top.name.lower() not in allowed_top_names:
                continue
        except OSError:
            continue
        for root, dirs, files in os.walk(top):
            root_path = Path(root)
            if server_data_manifest_should_skip(root_path):
                dirs[:] = []
                continue
            dirs[:] = [name for name in dirs if not server_data_manifest_should_skip(root_path / name)]
            for name in sorted(list(dirs) + [file_name for file_name in files if Path(file_name).suffix.lower() in LESSON_FILE_SUFFIXES]):
                path = root_path / name
                try:
                    stat = path.stat()
                    digest.update(server_data_relative(path).lower().encode("utf-8", "ignore"))
                    digest.update(str(int(stat.st_mtime_ns)).encode("ascii", "ignore"))
                    digest.update(str(int(stat.st_size)).encode("ascii", "ignore"))
                    count += 1
                except OSError:
                    continue
    digest.update(str(count).encode("ascii", "ignore"))
    return digest.hexdigest()


class ServerDataNativeWatcher:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name="server-data-native-watch")
        self.handle = None
        self.handle_lock = threading.Lock()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        with self.handle_lock:
            handle = self.handle
        if handle:
            try:
                ctypes.windll.kernel32.CancelIoEx(handle, None)
            except Exception:
                pass

    def join(self, timeout: float | None = None) -> None:
        self.thread.join(timeout=timeout)

    def _queue_event(self, name: str, action: int) -> None:
        rel = clean_path_value(name)
        if not rel:
            return
        with SERVER_DATA_MANIFEST_LOCK:
            if SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply"):
                suffix = Path(rel).suffix.lower()
                if suffix and suffix not in LESSON_FILE_SUFFIXES:
                    return
                parent = clean_path_value(rel.rsplit("/", 1)[0]) if "/" in rel else rel
                pending = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
                if not isinstance(pending, set):
                    pending = set()
                    SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending
                if parent:
                    pending.add(parent)
                return
        target = self.root / Path(rel)
        try:
            target_is_dir = target.is_dir()
        except OSError:
            target_is_dir = False
        with SERVER_DATA_MANIFEST_LOCK:
            manifest = SERVER_DATA_MANIFEST_STATE.get("manifest")
            known_folders = manifest.get("folders") if isinstance(manifest, dict) else None
            known_folder = isinstance(known_folders, dict) and rel in known_folders
        directory_event = target_is_dir or known_folder
        action_value = int(action or 0)
        # FILE_ACTION_MODIFIED for an ancestor directory is redundant; the recursive watcher also emits the child event.
        if action_value == 3 and directory_event:
            return
        if not directory_event and not server_data_manifest_event_relevant(target):
            return
        if "/" not in rel:
            reason = "native-watch-delete" if action_value in {2, 4} else "native-watch-root"
            schedule_server_data_manifest_paths_refresh({rel}, delay=0.65, reason=reason)
            return
        parent = clean_path_value(rel.rsplit("/", 1)[0])
        paths = {parent, rel}
        if directory_event or not Path(rel).suffix:
            schedule_server_data_manifest_watch_rescan(paths)
        reason = "native-watch-delete" if action_value in {2, 4} else "native-watch"
        schedule_server_data_manifest_paths_refresh(paths, delay=0.65, reason=reason)

    def _run(self) -> None:
        if os.name != "nt":
            return
        kernel32 = ctypes.windll.kernel32
        create_file = kernel32.CreateFileW
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(self.root),
            0x0001,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or int(handle) == int(invalid_handle):
            stt_debug_log("server_data_native_watch_start_failed", error=str(ctypes.get_last_error()))
            return
        with self.handle_lock:
            self.handle = handle
        buffer = ctypes.create_string_buffer(64 * 1024)
        bytes_returned = wintypes.DWORD()
        notify_filter = 0x00000001 | 0x00000002 | 0x00000004 | 0x00000008 | 0x00000010
        try:
            while not self.stop_event.is_set():
                ok = kernel32.ReadDirectoryChangesW(
                    handle,
                    ctypes.byref(buffer),
                    len(buffer),
                    True,
                    notify_filter,
                    ctypes.byref(bytes_returned),
                    None,
                    None,
                )
                if not ok:
                    if not self.stop_event.is_set():
                        stt_debug_log("server_data_native_watch_read_failed", error=str(ctypes.get_last_error()))
                    return
                size = int(bytes_returned.value or 0)
                offset = 0
                while offset + 12 <= size:
                    next_offset = int.from_bytes(buffer.raw[offset:offset + 4], "little")
                    action = int.from_bytes(buffer.raw[offset + 4:offset + 8], "little")
                    name_length = int.from_bytes(buffer.raw[offset + 8:offset + 12], "little")
                    name = buffer.raw[offset + 12:offset + 12 + name_length].decode("utf-16-le", errors="ignore")
                    self._queue_event(name, action)
                    if next_offset <= 0:
                        break
                    offset += next_offset
        finally:
            with self.handle_lock:
                self.handle = None
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass


def start_server_data_manifest_watchdog() -> bool:
    if os.name != "nt":
        return False
    with SERVER_DATA_MANIFEST_LOCK:
        observer = SERVER_DATA_MANIFEST_STATE.get("observer")
        if observer is not None:
            return True
        observer = ServerDataNativeWatcher(SERVER_DATA_ROOT)
        SERVER_DATA_MANIFEST_STATE["observer"] = observer
        SERVER_DATA_MANIFEST_STATE["watcher_started"] = True
    observer.start()
    return True


def refresh_server_data_manifest_now(reason: str = "manual") -> dict:
    signature = server_data_manifest_signature()
    clear_lesson_metadata_cache()
    clear_server_data_list_cache()
    manifest = rebuild_server_data_manifest(force=True, signature=signature)
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["signature"] = signature
        SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)
    schedule_future_boot_snapshot_write("manifest_refresh", delay=1.0)
    return manifest


def refresh_server_data_manifest_paths_now(relative_paths: list[str] | tuple[str, ...] | set[str], reason: str = "mutation") -> dict:
    normalized_paths = {
        clean_path_value(path)
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not normalized_paths:
        return get_server_data_manifest()
    manifest = None
    with SERVER_DATA_MANIFEST_LOCK:
        current = SERVER_DATA_MANIFEST_STATE.get("manifest")
        if isinstance(current, dict) and isinstance(current.get("folders"), dict):
            manifest = dict(current)
            manifest["folders"] = dict(current.get("folders") or {})
        else:
            disk = load_server_data_manifest_from_disk()
            if isinstance(disk, dict) and isinstance(disk.get("folders"), dict):
                manifest = disk
    if not isinstance(manifest, dict) or not isinstance(manifest.get("folders"), dict):
        return refresh_server_data_manifest_now(reason or "mutation")
    runtime_revisions_before = (
        int(manifest.get("runtime_root_revision_version", 0) or 0),
        clean(manifest.get("runtime_revision", "")),
        dict(manifest.get("runtime_root_revisions") or {}) if isinstance(manifest.get("runtime_root_revisions"), dict) else {},
    )
    ensure_server_data_manifest_runtime_revisions(manifest)
    runtime_revisions_changed = runtime_revisions_before != (
        int(manifest.get("runtime_root_revision_version", 0) or 0),
        clean(manifest.get("runtime_revision", "")),
        dict(manifest.get("runtime_root_revisions") or {}) if isinstance(manifest.get("runtime_root_revisions"), dict) else {},
    )
    folders = manifest.get("folders") or {}
    before_identity = server_data_manifest_identity_snapshot(folders, normalized_paths)
    before_fingerprint = server_data_manifest_paths_fingerprint(folders, normalized_paths)
    scan_targets: set[str] = set()
    for rel in normalized_paths:
        target = server_data_manifest_path(rel)
        remove_server_data_manifest_subtree(folders, rel)
        try:
            if update_server_data_manifest_top_root_entry(folders, rel):
                if target.exists() and target.is_dir():
                    scan_targets.add(rel)
                else:
                    remove_server_data_manifest_subtree(folders, rel)
                continue
            parent = target.parent
            parent_rel = server_data_relative(parent)
            if parent_rel:
                scan_targets.add(parent_rel)
        except Exception:
            pass
        try:
            if target.exists() and target.is_dir():
                scan_targets.add(rel)
        except Exception:
            pass
    for rel in sorted(scan_targets, key=lambda value: (value.count("/"), value)):
        try:
            folder = server_data_manifest_path(rel)
            if folder.is_dir() and not server_data_manifest_should_skip(folder):
                scan_server_data_manifest_folder(folder, folders)
        except Exception as exc:
            stt_debug_log("server_data_manifest_path_refresh_failed", path=rel, error=str(exc))
    enrich_server_data_manifest_counts_for_paths(folders, normalized_paths.union(scan_targets))
    after_identity = server_data_manifest_identity_snapshot(folders, normalized_paths)
    changed_identity_paths = {
        path for path in set(before_identity).union(after_identity)
        if before_identity.get(path) != after_identity.get(path)
    }
    after_fingerprint = server_data_manifest_paths_fingerprint(folders, normalized_paths)
    if before_fingerprint == after_fingerprint and not runtime_revisions_changed:
        with SERVER_DATA_MANIFEST_LOCK:
            SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
            SERVER_DATA_MANIFEST_STATE["dirty"] = False
            SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)
        return manifest
    manifest["updated_at"] = utc_timestamp()
    manifest["folders"] = folders
    if before_fingerprint != after_fingerprint:
        update_server_data_manifest_runtime_revision(
            manifest,
            before_fingerprint,
            after_fingerprint,
            normalized_paths,
        )
    if changed_identity_paths:
        sync_server_data_lesson_identity_paths(manifest, changed_identity_paths)
    try:
        SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest, indent=None)
    except Exception as exc:
        stt_debug_log("server_data_manifest_write_failed", error=str(exc))
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
        SERVER_DATA_MANIFEST_STATE["dirty"] = False
        SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)
    schedule_future_boot_snapshot_write("manifest_paths_refresh", delay=1.0)
    return manifest


# Added 2026-07-16: refreshes startup-detected branches without recursively rescanning unchanged children/grandchildren.
def refresh_server_data_manifest_delta_paths_now(relative_paths: list[str] | tuple[str, ...] | set[str], reason: str = "startup-delta") -> dict:
    normalized_paths = {
        clean_path_value(path)
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not normalized_paths:
        return get_server_data_manifest()
    manifest = None
    with SERVER_DATA_MANIFEST_LOCK:
        current = SERVER_DATA_MANIFEST_STATE.get("manifest")
        if isinstance(current, dict) and isinstance(current.get("folders"), dict):
            manifest = dict(current)
            manifest["folders"] = dict(current.get("folders") or {})
        else:
            disk = load_server_data_manifest_from_disk()
            if isinstance(disk, dict) and isinstance(disk.get("folders"), dict):
                manifest = disk
    if not isinstance(manifest, dict) or not isinstance(manifest.get("folders"), dict):
        return refresh_server_data_manifest_now(reason or "startup-delta")
    ensure_server_data_manifest_runtime_revisions(manifest)
    folders = manifest.get("folders") or {}
    before_identity = server_data_manifest_identity_snapshot(folders, normalized_paths)
    before_fingerprint = server_data_manifest_paths_fingerprint(folders, normalized_paths)
    scan_targets: set[str] = set()
    for rel in normalized_paths:
        target = server_data_manifest_path(rel)
        try:
            if update_server_data_manifest_top_root_entry(folders, rel):
                if target.exists() and target.is_dir():
                    scan_targets.add(rel)
                continue
            if target.exists() and target.is_dir():
                scan_targets.add(rel)
            else:
                parent_rel = server_data_relative(target.parent)
                if parent_rel:
                    scan_targets.add(parent_rel)
                remove_server_data_manifest_subtree(folders, rel)
        except Exception:
            parent = clean_path_value(rel.rsplit("/", 1)[0]) if "/" in rel else ""
            if parent:
                scan_targets.add(parent)
    for rel in sorted(scan_targets, key=lambda value: (value.count("/"), value)):
        try:
            folder = server_data_manifest_path(rel)
            if folder.is_dir() and not server_data_manifest_should_skip(folder):
                scan_server_data_manifest_folder_delta(folder, folders, normalized_paths)
        except Exception as exc:
            stt_debug_log("server_data_manifest_delta_refresh_failed", path=rel, error=str(exc))
    enrich_server_data_manifest_counts_for_paths(folders, normalized_paths.union(scan_targets))
    after_identity = server_data_manifest_identity_snapshot(folders, normalized_paths)
    changed_identity_paths = {
        path for path in set(before_identity).union(after_identity)
        if before_identity.get(path) != after_identity.get(path)
    }
    after_fingerprint = server_data_manifest_paths_fingerprint(folders, normalized_paths)
    if before_fingerprint == after_fingerprint:
        with SERVER_DATA_MANIFEST_LOCK:
            SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
            SERVER_DATA_MANIFEST_STATE["dirty"] = False
            SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)
        return manifest
    manifest["updated_at"] = utc_timestamp()
    manifest["folders"] = folders
    update_server_data_manifest_runtime_revision(
        manifest,
        before_fingerprint,
        after_fingerprint,
        normalized_paths,
    )
    if changed_identity_paths:
        sync_server_data_lesson_identity_paths(manifest, changed_identity_paths)
    try:
        SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest, indent=None)
    except Exception as exc:
        stt_debug_log("server_data_manifest_write_failed", error=str(exc))
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
        SERVER_DATA_MANIFEST_STATE["dirty"] = False
        SERVER_DATA_MANIFEST_STATE["dirty_reason"] = clean(reason)
    schedule_future_boot_snapshot_write("manifest_delta_paths_refresh", delay=1.0)
    return manifest


def start_server_data_manifest_interval_monitor() -> None:
    with SERVER_DATA_MANIFEST_LOCK:
        if SERVER_DATA_MANIFEST_STATE.get("monitor_thread"):
            return

    def _monitor() -> None:
        while not SERVER_STATE.get("shutdown_requested"):
            time.sleep(SERVER_DATA_MANIFEST_MONITOR_SECONDS)
            if SERVER_STATE.get("shutdown_requested"):
                return
            try:
                delta = future_boot_snapshot_manifest_delta_paths()
                changed_paths = [clean_path_value(path) for path in (delta.get("changed_paths") or []) if clean_path_value(path) or path == ""]
                with SERVER_DATA_MANIFEST_LOCK:
                    staged = bool(SERVER_DATA_MANIFEST_STATE.get("build_hold_requires_apply"))
                    if staged:
                        if delta.get("fallback") or "" in changed_paths:
                            SERVER_DATA_MANIFEST_STATE["build_hold_full_refresh_pending"] = True
                        else:
                            pending = SERVER_DATA_MANIFEST_STATE.get("pending_paths")
                            if not isinstance(pending, set):
                                pending = set()
                                SERVER_DATA_MANIFEST_STATE["pending_paths"] = pending
                            pending.update(path for path in changed_paths if path)
                if staged:
                    server_data_manifest_build_pending_persist(True)
                    continue
                if delta.get("fallback") or "" in changed_paths:
                    refresh_server_data_manifest_now("interval-delta-fallback")
                    print(
                        f"Server data manifest refreshed after hourly delta check: {SERVER_DATA_MANIFEST_FILE}",
                        flush=True,
                    )
                elif changed_paths:
                    refresh_server_data_manifest_delta_paths_now(changed_paths, "interval-delta-branches")
                    print(
                        f"Server data manifest refreshed branches after hourly delta check: {len(changed_paths)}",
                        flush=True,
                    )
                else:
                    schedule_future_boot_snapshot_write("manifest_interval_verify", delay=1.0)
            except Exception as exc:
                stt_debug_log("server_data_manifest_interval_failed", error=str(exc))

    thread = threading.Thread(target=_monitor, daemon=True, name="server-data-manifest-hourly")
    with SERVER_DATA_MANIFEST_LOCK:
        SERVER_DATA_MANIFEST_STATE["monitor_thread"] = thread
    thread.start()


def start_server_data_manifest_monitor() -> None:
    with SERVER_DATA_MANIFEST_LOCK:
        if SERVER_DATA_MANIFEST_STATE.get("watcher_started"):
            return
        SERVER_DATA_MANIFEST_STATE["watcher_started"] = True
    manifest = load_server_data_manifest_from_disk()
    if manifest:
        runtime_revisions_before = (
            int(manifest.get("runtime_root_revision_version", 0) or 0),
            clean(manifest.get("runtime_revision", "")),
            dict(manifest.get("runtime_root_revisions") or {}) if isinstance(manifest.get("runtime_root_revisions"), dict) else {},
        )
        ensure_server_data_manifest_runtime_revisions(manifest)
        if runtime_revisions_before != (
            int(manifest.get("runtime_root_revision_version", 0) or 0),
            clean(manifest.get("runtime_revision", "")),
            dict(manifest.get("runtime_root_revisions") or {}) if isinstance(manifest.get("runtime_root_revisions"), dict) else {},
        ):
            # Added 2026-07-22: startup monitor owns the first disk load, so persist stale-root pruning here too.
            manifest["updated_at"] = utc_timestamp()
            try:
                atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest, indent=None)
            except Exception as exc:
                stt_debug_log("server_data_manifest_runtime_revision_write_failed", error=str(exc))
        with SERVER_DATA_MANIFEST_LOCK:
            SERVER_DATA_MANIFEST_STATE["manifest"] = manifest
            SERVER_DATA_MANIFEST_STATE["dirty"] = False
            SERVER_DATA_MANIFEST_STATE["signature"] = clean(manifest.get("signature", ""))
        print(f"Server data manifest cache loaded: {SERVER_DATA_MANIFEST_FILE}", flush=True)
        if restore_server_data_manifest_build_pending():
            manifest = get_server_data_manifest(force=False)
        start_server_data_manifest_watchdog()
        backfill_scheduled = schedule_server_data_manifest_metadata_backfill(manifest)
        # Warm the currently valid manifest before HTTP starts accepting users.
        # A scheduled metadata backfill warms the replacement revision again.
        warmup_users = select_startup_warmup_usernames(purpose="startup")
        warmup_summary = startup_warmup_selection_summary(warmup_users)
        print(
            f"Warmup mode: {warmup_summary.get('mode', 'production')}; selected users: {len(warmup_users)}; "
            f"selected test users: {warmup_summary.get('selected_test_users', 0)}; "
            f"real users total: {warmup_summary.get('real_users_total', 0)}; "
            f"test users skipped: {warmup_summary.get('test_users_skipped', 0)}; include_test_users={int(bool(warmup_summary.get('include_test_users')))}.",
            flush=True,
        )
        tree_warm = warm_server_data_tree_preload_cache(manifest)
        print(
            f"Common Tree warm: revision {tree_warm.get('common_revision', '')}, build {tree_warm.get('common_builds', 0)}, "
            f"{tree_warm.get('common_cpu_ms', 0)}ms CPU, {tree_warm.get('common_gzip_bytes', 0)} gzip bytes. "
            f"Tree-preload per-user warm: {'enabled' if tree_warm.get('tree_preload_per_user') else 'disabled/not required'}, "
            f"{tree_warm.get('users', 0)} users, {tree_warm.get('gzip_bytes', 0)} gzip bytes"
            f"{' (metadata refresh scheduled)' if backfill_scheduled else ''}.",
            flush=True,
        )
        overlay_warm = warm_server_data_user_overlay_cache(manifest)
        print(
            f"Server data user overlay warm: {overlay_warm.get('users', 0)} users, {overlay_warm.get('cpu_ms', 0)}ms CPU, {overlay_warm.get('gzip_bytes', 0)} gzip bytes"
            f"{' (metadata refresh scheduled)' if backfill_scheduled else ''}.",
            flush=True,
        )
        login_warm = warm_login_preload_response_cache()
        print(
            f"Server data login preload warm: {login_warm.get('users', 0)} users, {login_warm.get('cpu_ms', 0)}ms CPU"
            f"{' (metadata refresh scheduled)' if backfill_scheduled else ''}.",
            flush=True,
        )
        login_list_warm = warm_login_server_data_list_cache()
        print(
            f"Server data login folder-list warm: {login_list_warm.get('users', 0)} users, {login_list_warm.get('cpu_ms', 0)}ms CPU, {login_list_warm.get('errors', 0)} errors"
            f"{' (metadata refresh scheduled)' if backfill_scheduled else ''}.",
            flush=True,
        )
        schedule_server_data_manifest_startup_verify()
        start_server_data_manifest_interval_monitor()
        return
    refresh_server_data_manifest_now("startup")
    warmup_users = select_startup_warmup_usernames(purpose="startup")
    warmup_summary = startup_warmup_selection_summary(warmup_users)
    print(
        f"Warmup mode: {warmup_summary.get('mode', 'production')}; selected users: {len(warmup_users)}; "
        f"selected test users: {warmup_summary.get('selected_test_users', 0)}; "
        f"real users total: {warmup_summary.get('real_users_total', 0)}; "
        f"test users skipped: {warmup_summary.get('test_users_skipped', 0)}; include_test_users={int(bool(warmup_summary.get('include_test_users')))}.",
        flush=True,
    )
    tree_warm = warm_server_data_tree_preload_cache(get_server_data_manifest(force=False))
    print(
        f"Common Tree warm: revision {tree_warm.get('common_revision', '')}, build {tree_warm.get('common_builds', 0)}, "
        f"{tree_warm.get('common_cpu_ms', 0)}ms CPU, {tree_warm.get('common_gzip_bytes', 0)} gzip bytes. "
        f"Tree-preload per-user warm: {'enabled' if tree_warm.get('tree_preload_per_user') else 'disabled/not required'}, "
        f"{tree_warm.get('users', 0)} users, {tree_warm.get('gzip_bytes', 0)} gzip bytes.",
        flush=True,
    )
    overlay_warm = warm_server_data_user_overlay_cache(get_server_data_manifest(force=False))
    print(
        f"Server data user overlay warm: {overlay_warm.get('users', 0)} users, {overlay_warm.get('cpu_ms', 0)}ms CPU, {overlay_warm.get('gzip_bytes', 0)} gzip bytes.",
        flush=True,
    )
    login_warm = warm_login_preload_response_cache()
    print(
        f"Server data login preload warm: {login_warm.get('users', 0)} users, {login_warm.get('cpu_ms', 0)}ms CPU.",
        flush=True,
    )
    login_list_warm = warm_login_server_data_list_cache()
    print(
        f"Server data login folder-list warm: {login_list_warm.get('users', 0)} users, {login_list_warm.get('cpu_ms', 0)}ms CPU, {login_list_warm.get('errors', 0)} errors.",
        flush=True,
    )
    print(f"Server data manifest built once: {SERVER_DATA_MANIFEST_FILE}", flush=True)
    start_server_data_manifest_watchdog()
    start_server_data_manifest_interval_monitor()
