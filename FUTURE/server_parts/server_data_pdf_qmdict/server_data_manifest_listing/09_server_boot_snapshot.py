# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.


def future_boot_snapshot_file_row(path: Path) -> dict:
    if server_database_document_local_only(path):
        _resolved, mtime_ns, size, sha256 = server_database_document_signature(path)
        return {"exists": bool(sha256), "mtime_ns": mtime_ns, "size": size if sha256 else -1}
    try:
        stat = Path(path).stat()
        return {"exists": True, "mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}
    except OSError:
        return {"exists": False, "mtime_ns": 0, "size": -1}


def future_boot_snapshot_file_matches(snapshot: dict, name: str, path: Path) -> bool:
    if not isinstance(snapshot, dict):
        return False
    files = snapshot.get("files")
    if not isinstance(files, dict):
        return False
    row = files.get(name)
    if not isinstance(row, dict):
        return False
    current = future_boot_snapshot_file_row(path)
    return (
        bool(row.get("exists")) == bool(current.get("exists"))
        and int(row.get("mtime_ns", 0) or 0) == int(current.get("mtime_ns", 0) or 0)
        and int(row.get("size", -1) or -1) == int(current.get("size", -1) or -1)
    )


def future_boot_snapshot_extra_files() -> dict[str, Path]:
    rows = {
        "manifest": SERVER_DATA_MANIFEST_FILE,
        "pdf_picture_metadata": PDF_PICTURE_METADATA_INDEX_FILE,
        "qmlearn_audio_stem_index": QMLEARN_AUDIO_STEM_INDEX_FILE,
        "lesson_tasks": LESSON_TASKS_FILE,
        "lesson_task_notices": LESSON_TASK_NOTICES_FILE,
    }
    for name, key in (
        ("space_pdf_ai_region_notices", "SPACE_PDF_AI_REGION_NOTICES_FILE"),
        ("space_pdf_ai_region_questions", "SPACE_PDF_AI_REGION_QUESTIONS_FILE"),
        ("space_pdf_ai_question_progress", "SPACE_PDF_AI_QUESTION_PROGRESS_FILE"),
        ("space_pdf_audio_markers", "SPACE_PDF_SHARED_AUDIO_MARKERS_FILE"),
    ):
        value = globals().get(key)
        if value is not None:
            try:
                rows[name] = Path(value)
            except Exception:
                pass
    return rows


def future_boot_snapshot_previous_manifest_baseline() -> dict:
    with SERVER_BOOT_SNAPSHOT_LOCK:
        snapshot = SERVER_BOOT_SNAPSHOT_STATE.get("snapshot")
    baseline = snapshot.get("manifest_baseline") if isinstance(snapshot, dict) else None
    return baseline if isinstance(baseline, dict) else {}


def future_boot_snapshot_top_folders() -> list[str]:
    rows: list[str] = []
    try:
        skip_tops = server_data_manifest_skip_tops()
        for item in SERVER_DATA_ROOT.iterdir():
            try:
                if item.is_dir() and item.name not in skip_tops:
                    rows.append(clean(item.name).lower())
            except OSError:
                continue
    except OSError:
        return []
    return sorted({item for item in rows if item})


# Added 2026-07-16: stores known folder/file stat signatures so next startup can detect changed branches without a full disk walk.
def future_boot_snapshot_manifest_baseline(manifest: dict) -> dict:
    folders = manifest.get("folders") if isinstance(manifest, dict) else {}
    if not isinstance(folders, dict):
        return {}
    folder_rows: dict[str, dict] = {}
    file_rows: dict[str, dict] = {}
    for rel in folders.keys():
        rel_key = clean_path_value(rel)
        if not rel_key:
            continue
        folder_rows[rel_key] = future_boot_snapshot_file_row(server_data_manifest_path(rel_key))
    for rows in folders.values():
        if not isinstance(rows, list):
            continue
        for entry in rows:
            if not isinstance(entry, dict) or clean(entry.get("type", "")) != "file":
                continue
            rel = clean_path_value(entry.get("path", ""))
            if rel:
                file_rows[rel] = future_boot_snapshot_file_row(server_data_manifest_path(rel))
    return {
        "version": 1,
        "created_at": utc_timestamp(),
        "folders": folder_rows,
        "files": file_rows,
        "top_folders": future_boot_snapshot_top_folders(),
        "folder_count": len(folder_rows),
        "file_count": len(file_rows),
    }


def future_boot_snapshot_should_rebuild_manifest_baseline(reason: str = "", manifest: dict | None = None) -> bool:
    reason_key = clean(reason).lower()
    if reason_key.startswith("manifest") or reason_key in {"atexit", "shutdown", "runtime_flush", "smoke"}:
        return True
    baseline = future_boot_snapshot_previous_manifest_baseline()
    if not isinstance(baseline.get("folders"), dict) or not isinstance(baseline.get("files"), dict):
        return True
    if isinstance(manifest, dict) and isinstance(manifest.get("folders"), dict):
        folder_count = len(manifest.get("folders") or {})
        try:
            if int(baseline.get("folder_count", -1) or -1) != folder_count:
                return True
        except Exception:
            return True
    return False


def future_boot_snapshot_manifest_delta_paths(limit: int = 800) -> dict:
    baseline = future_boot_snapshot_previous_manifest_baseline()
    folder_rows = baseline.get("folders") if isinstance(baseline, dict) else None
    file_rows = baseline.get("files") if isinstance(baseline, dict) else None
    if not isinstance(folder_rows, dict) or not isinstance(file_rows, dict):
        return {"ok": False, "fallback": True, "reason": "missing_baseline", "changed_paths": []}
    previous_top_folders = baseline.get("top_folders")
    if isinstance(previous_top_folders, list):
        current_top_folders = future_boot_snapshot_top_folders()
        if sorted(clean(item).lower() for item in previous_top_folders) != current_top_folders:
            return {"ok": False, "fallback": True, "reason": "top_folders_changed", "changed_paths": [""]}
    changed: set[str] = set()
    checked_folders = 0
    checked_files = 0
    for rel, row in folder_rows.items():
        rel_key = clean_path_value(rel)
        if not rel_key and rel != "":
            continue
        checked_folders += 1
        current = future_boot_snapshot_file_row(server_data_manifest_path(rel_key))
        if not isinstance(row, dict) or current != row:
            changed.add(rel_key)
            if len(changed) > limit:
                return {"ok": False, "fallback": True, "reason": "too_many_changed_folders", "changed_paths": sorted(changed)}
    for rel, row in file_rows.items():
        rel_key = clean_path_value(rel)
        if not rel_key:
            continue
        checked_files += 1
        current = future_boot_snapshot_file_row(server_data_manifest_path(rel_key))
        if not isinstance(row, dict) or current != row:
            parent = clean_path_value(rel_key.rsplit("/", 1)[0]) if "/" in rel_key else ""
            changed.add(parent)
            if len(changed) > limit:
                return {"ok": False, "fallback": True, "reason": "too_many_changed_files", "changed_paths": sorted(changed)}
    return {
        "ok": True,
        "fallback": False,
        "reason": "",
        "changed_paths": sorted(changed, key=lambda value: (value.count("/"), value.lower())),
        "checked_folders": checked_folders,
        "checked_files": checked_files,
    }


# Added 2026-07-16: records cache-file signatures at shutdown/flush so startup can trust hot disk snapshots before background refresh.
def future_boot_snapshot_current_payload(reason: str = "runtime") -> dict:
    manifest = {}
    with SERVER_DATA_MANIFEST_LOCK:
        current_manifest = SERVER_DATA_MANIFEST_STATE.get("manifest")
        if isinstance(current_manifest, dict):
            manifest = current_manifest
        manifest_signature = clean(SERVER_DATA_MANIFEST_STATE.get("signature", "")) or clean(manifest.get("signature", ""))
        manifest_dirty = bool(SERVER_DATA_MANIFEST_STATE.get("dirty"))
    if not isinstance(manifest.get("folders"), dict):
        disk_manifest = load_server_data_manifest_from_disk()
        if isinstance(disk_manifest, dict) and isinstance(disk_manifest.get("folders"), dict):
            manifest = disk_manifest
            manifest_signature = manifest_signature or clean(disk_manifest.get("signature", ""))
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    manifest_folder_count = len(folders) if isinstance(folders, dict) else 0
    manifest_entry_count = 0
    if isinstance(folders, dict):
        for rows in folders.values():
            if isinstance(rows, list):
                manifest_entry_count += len(rows)
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        pdf_items = PDF_PICTURE_METADATA_INDEX.get("items")
        pdf_loaded = bool(PDF_PICTURE_METADATA_INDEX.get("loaded"))
        pdf_item_count = len(pdf_items) if isinstance(pdf_items, dict) else 0
    if not pdf_item_count:
        try:
            pdf_payload = json.loads(PDF_PICTURE_METADATA_INDEX_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            pdf_disk_items = pdf_payload.get("items") if isinstance(pdf_payload, dict) else None
            if isinstance(pdf_disk_items, dict):
                pdf_item_count = len(pdf_disk_items)
        except Exception:
            pass
    with QMDICT_AUDIO_STEM_INDEX_LOCK:
        audio_stems = QMDICT_AUDIO_STEM_INDEX_CACHE.get("stems")
        audio_loaded = isinstance(audio_stems, set) and bool(audio_stems)
        audio_count = len(audio_stems) if isinstance(audio_stems, set) else 0
    if not audio_count:
        try:
            audio_payload = json.loads(QMLEARN_AUDIO_STEM_INDEX_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            audio_count = int(audio_payload.get("count", 0) or 0) if isinstance(audio_payload, dict) else 0
            if not audio_count and isinstance(audio_payload.get("stems"), list):
                audio_count = len(audio_payload.get("stems") or [])
        except Exception:
            pass
    with SPACE_PROGRESS_STORE_LOCK:
        progress_rows = list(SPACE_PROGRESS_STORE.values())
        dirty_progress = sum(1 for row in progress_rows if isinstance(row, dict) and bool(row.get("dirty")))
        pending_wal = sum(len(row.get("pending_wal_entries") or []) for row in progress_rows if isinstance(row, dict))
    files = {name: future_boot_snapshot_file_row(path) for name, path in future_boot_snapshot_extra_files().items()}
    if future_boot_snapshot_should_rebuild_manifest_baseline(reason, manifest):
        manifest_baseline = future_boot_snapshot_manifest_baseline(manifest)
    else:
        manifest_baseline = future_boot_snapshot_previous_manifest_baseline()
    return {
        "version": 1,
        "created_at": utc_timestamp(),
        "reason": clean(reason) or "runtime",
        "root": str(SERVER_DATA_ROOT),
        "files": files,
        "manifest": {
            "signature": manifest_signature,
            "dirty": manifest_dirty,
            "folders": manifest_folder_count,
            "entries": manifest_entry_count,
        },
        "manifest_baseline": manifest_baseline,
        "pdf_picture_metadata": {"loaded": pdf_loaded, "items": pdf_item_count},
        "qmlearn_audio_stem_index": {"loaded": audio_loaded, "stems": audio_count},
        "space_progress_store": {"rows": len(progress_rows), "dirty": dirty_progress, "pending_wal_entries": pending_wal},
    }


def load_future_boot_snapshot() -> dict:
    try:
        payload = json.loads(SERVER_BOOT_SNAPSHOT_FILE.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        payload = {}
    valid = (
        isinstance(payload, dict)
        and future_boot_snapshot_file_matches(payload, "manifest", SERVER_DATA_MANIFEST_FILE)
        and future_boot_snapshot_file_matches(payload, "pdf_picture_metadata", PDF_PICTURE_METADATA_INDEX_FILE)
        and future_boot_snapshot_file_matches(payload, "qmlearn_audio_stem_index", QMLEARN_AUDIO_STEM_INDEX_FILE)
    )
    with SERVER_BOOT_SNAPSHOT_LOCK:
        SERVER_BOOT_SNAPSHOT_STATE.update({"loaded": True, "snapshot": payload if isinstance(payload, dict) else {}, "valid": bool(valid)})
    return payload if isinstance(payload, dict) else {}


def future_boot_snapshot_cache_usable(name: str = "") -> bool:
    cache_name = clean(name)
    with SERVER_BOOT_SNAPSHOT_LOCK:
        snapshot = SERVER_BOOT_SNAPSHOT_STATE.get("snapshot")
        valid = bool(SERVER_BOOT_SNAPSHOT_STATE.get("valid"))
    if not valid or not isinstance(snapshot, dict) or not cache_name:
        return False
    files = snapshot.get("files")
    if not isinstance(files, dict) or cache_name not in files:
        return False
    target = future_boot_snapshot_extra_files().get(cache_name)
    return bool(target is not None and future_boot_snapshot_file_matches(snapshot, cache_name, target))


def future_boot_snapshot_count(section: str = "", field: str = "") -> int:
    with SERVER_BOOT_SNAPSHOT_LOCK:
        snapshot = SERVER_BOOT_SNAPSHOT_STATE.get("snapshot")
    row = snapshot.get(clean(section)) if isinstance(snapshot, dict) else None
    if not isinstance(row, dict):
        return 0
    try:
        return int(row.get(clean(field), 0) or 0)
    except Exception:
        return 0


def write_future_boot_snapshot(reason: str = "runtime") -> dict:
    payload = future_boot_snapshot_current_payload(reason)
    try:
        atomic_write_json(SERVER_BOOT_SNAPSHOT_FILE, payload, indent=None)
    except Exception as exc:
        stt_debug_log("future_boot_snapshot_write_failed", error=str(exc), reason=reason)
        return {"ok": False, "error": str(exc)}
    with SERVER_BOOT_SNAPSHOT_LOCK:
        SERVER_BOOT_SNAPSHOT_STATE.update({"loaded": True, "snapshot": payload, "valid": True})
    return {"ok": True, "path": str(SERVER_BOOT_SNAPSHOT_FILE)}


def schedule_future_boot_snapshot_write(reason: str = "runtime", delay: float = 0.5) -> None:
    with SERVER_BOOT_SNAPSHOT_LOCK:
        timer = SERVER_BOOT_SNAPSHOT_STATE.get("timer")
        if timer is not None and getattr(timer, "is_alive", lambda: False)():
            return
        def _run() -> None:
            try:
                write_future_boot_snapshot(reason)
            except Exception:
                pass
        next_timer = threading.Timer(max(0.1, float(delay or 0.5)), _run)
        next_timer.daemon = True
        SERVER_BOOT_SNAPSHOT_STATE["timer"] = next_timer
        next_timer.start()


def start_future_boot_snapshot_cache() -> None:
    snapshot = load_future_boot_snapshot()
    valid = bool(SERVER_BOOT_SNAPSHOT_STATE.get("valid"))
    SERVER_STATE["boot_snapshot"] = {
        "loaded": bool(snapshot),
        "valid": valid,
        "path": str(SERVER_BOOT_SNAPSHOT_FILE),
        "manifest_folders": future_boot_snapshot_count("manifest", "folders"),
        "pdf_picture_items": future_boot_snapshot_count("pdf_picture_metadata", "items"),
        "audio_stems": future_boot_snapshot_count("qmlearn_audio_stem_index", "stems"),
    }
    if snapshot:
        marker = "valid" if valid else "stale"
        print(f"Future boot snapshot {marker}: {SERVER_BOOT_SNAPSHOT_FILE}", flush=True)
    else:
        print(f"Future boot snapshot missing: {SERVER_BOOT_SNAPSHOT_FILE}", flush=True)


atexit.register(lambda: write_future_boot_snapshot("atexit"))
