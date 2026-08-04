# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def server_data_manifest_skip_tops() -> set[str]:
    # Updated 2026-07-06: keep internal caches, archives, and test folders out of server-data scans.
    return {
        "Sound",
        "Structure",
        "Picture",
        "NPC_TOP",
        "server_log",
        "Cache ORC",
        "_archive_non_users",
        "_future_qmid_backups",
        "_profile_refresh_backups",
        "_restore_backups",
        "server",
        "testuser",
        "codextestspacev",
    }


# Added 2026-07-30: Lesson Vault root is a logical namespace, not every
# directory stored beside Server Data. Keep only common and registered users.
def server_data_manifest_allowed_top_names() -> set[str]:
    allowed = {"common"}
    reader = globals().get("list_registered_users")
    if callable(reader):
        allowed.update(normalize_username(item) for item in reader() if normalize_username(item))
    blocked = {clean(item).lower() for item in server_data_manifest_skip_tops()}
    return {name for name in allowed if name and name not in blocked and not name.startswith("_")}


def server_data_folder_counts(folder: Path) -> dict:
    counts = {
        "folder_count": 0,
        "file_count": 0,
        "space_v_file_count": 0,
        "word_count": 0,
    }
    try:
        if not folder.is_dir():
            return counts
        for root, dirs, files in os.walk(folder):
            root_path = Path(root)
            if server_data_manifest_should_skip(root_path):
                dirs[:] = []
                continue
            dirs[:] = [name for name in dirs if not server_data_manifest_should_skip(root_path / name)]
            counts["folder_count"] += len(dirs)
            for filename in files:
                source_file = root_path / filename
                if server_data_manifest_should_skip(source_file):
                    continue
                try:
                    effective = server_data_effective_file_path(source_file, username="", admin=True)
                except Exception:
                    effective = source_file
                if not effective.is_file() or not is_lesson_file(effective):
                    continue
                counts["file_count"] += 1
                if effective.suffix.lower() in {".space_v", ".space_b"}:
                    counts["space_v_file_count"] += 1
                    try:
                        meta = cached_lesson_file_metadata(effective)
                        counts["word_count"] += max(0, space_w_int(meta.get("nodes", 0), 0))
                    except Exception:
                        pass
    except Exception:
        pass
    return counts


def server_data_folder_counts_cached(folder: Path) -> dict:
    try:
        stat = folder.stat()
        signature = (str(folder.resolve()).lower(), int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (str(folder).lower(), 0, -1)
    cache = getattr(server_data_folder_counts_cached, "_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(server_data_folder_counts_cached, "_cache", cache)
    row = cache.get(signature)
    if isinstance(row, dict) and time.time() - float(row.get("at", 0) or 0) < 60:
        return dict(row.get("counts", {}))
    counts = server_data_folder_counts(folder)
    cache.clear() if len(cache) > 300 else None
    cache[signature] = {"at": time.time(), "counts": dict(counts)}
    return counts


def server_data_manifest_name_fields(path: Path) -> dict:
    try:
        return {"name": path.name, "raw_name": path.name}
    except Exception:
        return {"name": path.name, "raw_name": path.name}


# Added 2026-08-01: build one lesson's shared vocabulary index alongside its manifest metadata.
def server_data_manifest_vocab_metadata(path: Path) -> dict:
    try:
        if path.suffix.lower() not in VOCAB_STATS_SUPPORTED_EXTENSIONS:
            return {}
        meta = lesson_file_vocab_meta_for_target(path)
        if not isinstance(meta, dict) or not clean(meta.get("lesson_id", "")):
            return {}
        return {
            "vocab_indexed": True,
            "vocab_total_words": max(0, int(meta.get("vocab_total_words", 0) or 0)),
            "vocab_valid_words": len(meta.get("vocab_valid_word_keys") or []),
            "vocab_source_revision": clean(meta.get("vocab_source_revision", "")),
            "vocab_qmdict_revision": clean(meta.get("vocab_validated_signature", "")),
            "vocab_extractor_version": clean(meta.get("vocab_extractor_version", "")),
        }
    except Exception as exc:
        stt_debug_log("server_data_manifest_vocab_metadata_failed", path=str(path), error=str(exc))
        return {"vocab_indexed": False}


SERVER_DATA_STRUCTURAL_METADATA_VERSION = 7
SERVER_DATA_STRUCTURAL_METADATA_FIELDS = (
    "nodes", "questions", "direct_questions", "total_nodes", "paragraphs", "sentences", "normal_sentences", "train_sentences",
)


def server_data_manifest_cached_structural_metadata(display_path: Path, effective_path: Path, stat) -> dict:
    try:
        rel = server_data_relative(display_path)
        parent_rel = clean_path_value(rel.rsplit("/", 1)[0]) if "/" in rel else ""
        with SERVER_DATA_MANIFEST_LOCK:
            manifest = SERVER_DATA_MANIFEST_STATE.get("manifest")
        folders = manifest.get("folders") if isinstance(manifest, dict) and isinstance(manifest.get("folders"), dict) else {}
        old = next((row for row in (folders.get(parent_rel) or []) if isinstance(row, dict) and clean_path_value(row.get("path", "")).lower() == rel.lower()), None)
        old_version = int(old.get("metadata_version", 0) or 0) if isinstance(old, dict) else 0
        if not isinstance(old, dict) or old_version != SERVER_DATA_STRUCTURAL_METADATA_VERSION:
            return {}
        if effective_path.suffix.lower() in {".space_p", ".space_l", ".space_s"} and "paragraphs" not in old:
            return {}
        old_mtime_ns = int(old.get("modified_ns", 0) or 0)
        if old_mtime_ns:
            if old_mtime_ns != int(stat.st_mtime_ns):
                return {}
        elif int(old.get("modified", 0) or 0) != int(stat.st_mtime):
            return {}
        if int(old.get("size", -1) or 0) != int(stat.st_size):
            return {}
        dependency_path = clean(old.get("metadata_dependency_path", ""))
        expected_dependency = (
            clean(old.get("metadata_dependency_key", "")),
            int(old.get("metadata_dependency_mtime_ns", 0) or 0),
            int(old.get("metadata_dependency_size", -1) if old.get("metadata_dependency_size") is not None else -1),
        )
        if dependency_path and lesson_dependency_signature(dependency_path) != expected_dependency:
            return {}
        return {
            key: max(0, space_w_int(old.get(key, 0), 0))
            for key in SERVER_DATA_STRUCTURAL_METADATA_FIELDS
        } | {
            "lesson_id": clean(old.get("lesson_id", ""))[:240],
            "content_fingerprint": clean(old.get("content_fingerprint", ""))[:320],
            "metadata_version": SERVER_DATA_STRUCTURAL_METADATA_VERSION,
            "metadata_dependency_path": dependency_path,
            "metadata_dependency_key": expected_dependency[0],
            "metadata_dependency_mtime_ns": expected_dependency[1],
            "metadata_dependency_size": expected_dependency[2],
        }
    except Exception:
        return {}


def server_data_manifest_structural_metadata(display_path: Path, effective_path: Path, stat) -> dict:
    cached = server_data_manifest_cached_structural_metadata(display_path, effective_path, stat)
    if cached:
        return cached
    try:
        meta = cached_lesson_file_metadata(effective_path)
        dependency_path = clean(meta.get("metadata_dependency_path", ""))
        dependency = lesson_dependency_signature(dependency_path)
        return {
            key: max(0, space_w_int(meta.get(key, 0), 0))
            for key in SERVER_DATA_STRUCTURAL_METADATA_FIELDS
        } | {
            "lesson_id": clean(meta.get("lesson_id", ""))[:240],
            "content_fingerprint": clean(meta.get("content_fingerprint", ""))[:320],
            "metadata_version": SERVER_DATA_STRUCTURAL_METADATA_VERSION,
            "metadata_dependency_path": dependency_path,
            "metadata_dependency_key": dependency[0],
            "metadata_dependency_mtime_ns": dependency[1],
            "metadata_dependency_size": dependency[2],
        }
    except Exception:
        return {}


def server_data_manifest_entry(path: Path) -> dict | None:
    try:
        # Updated 2026-07-22: a portable package is the visible lesson artifact; its legacy raw sibling is asset-only.
        if (path.suffix.lower() == ".pdf" or path.suffix.lower() in IMAGE_FILE_SUFFIXES) and space_pdf_package_path_for_legacy(path):
            return None
        folder_link_payload = read_server_data_folder_link_payload(path)
        if folder_link_payload:
            target_folder = server_data_folder_link_target_path(path, username="", admin=True)
            if target_folder is None or not target_folder.is_dir():
                stat = path.stat()
                return {
                    **server_data_manifest_name_fields(path),
                    "path": server_data_relative(path),
                    "type": "folder",
                    "size": 0,
                    "modified": int(stat.st_mtime),
                    "extension": "",
                    "linked": True,
                    "link_target": clean_path_value(folder_link_payload.get("target", "")),
                    "created_by": normalize_username(folder_link_payload.get("created_by", "")),
                    "created_at": clean(folder_link_payload.get("created_at", "")),
                    "link_unavailable": True,
                }
            stat = target_folder.stat()
            entry = {
                **server_data_manifest_name_fields(path),
                "path": server_data_relative(path),
                "type": "folder",
                "size": 0,
                "modified": int(stat.st_mtime),
                "extension": "",
                "linked": True,
                "link_target": clean_path_value(folder_link_payload.get("target", "")),
                "created_by": normalize_username(folder_link_payload.get("created_by", "")),
                "created_at": clean(folder_link_payload.get("created_at", "")),
            }
            if any(key in folder_link_payload for key in ("folder_count", "file_count", "space_v_file_count", "word_count")):
                for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
                    try:
                        entry[key] = max(0, int(folder_link_payload.get(key, 0) or 0))
                    except Exception:
                        entry[key] = 0
                entry["counts_at"] = clean(folder_link_payload.get("counts_at", ""))
            return entry
        link_payload = read_server_data_link_payload(path)
        if link_payload:
            target = server_data_link_target_path(path, username="", admin=True)
            if target is None or not target.exists():
                stat = path.stat()
                target_type = clean(link_payload.get("target_type", "file")).lower()
                return {
                    **server_data_manifest_name_fields(path),
                    "path": server_data_relative(path),
                    "type": "folder" if target_type == "folder" else "file",
                    "size": 0,
                    "modified": int(stat.st_mtime),
                    "extension": "" if target_type == "folder" else Path(clean_path_value(link_payload.get("target", ""))).suffix,
                    "linked": True,
                    "link_target": clean_path_value(link_payload.get("target", "")),
                    "created_by": normalize_username(link_payload.get("created_by", "")),
                    "created_at": clean(link_payload.get("created_at", "")),
                    "link_unavailable": True,
                }
            target_is_dir = target.is_dir()
            if not target_is_dir and not is_lesson_file(target):
                return None
            stat = target.stat()
            fields = server_data_manifest_name_fields(path)
            entry = {
                **fields,
                "path": server_data_relative(path),
                "type": "folder" if target_is_dir else "file",
                "size": 0 if target_is_dir else int(stat.st_size),
                "modified": int(stat.st_mtime),
                "extension": "" if target_is_dir else target.suffix,
                "linked": True,
                "link_target": clean_path_value(link_payload.get("target", "")),
                "created_by": normalize_username(link_payload.get("created_by", "")),
                "created_at": clean(link_payload.get("created_at", "")),
            }
            if not target_is_dir:
                entry["modified_ns"] = int(stat.st_mtime_ns)
                entry.update(server_data_manifest_structural_metadata(path, target, stat))
                entry.update(space_pdf_package_manifest_metadata(target))
                entry.update(server_data_manifest_vocab_metadata(target))
            return entry
        is_dir = path.is_dir()
        if not is_dir and not is_lesson_file(path):
            return None
        stat = path.stat()
        entry = {
            **server_data_manifest_name_fields(path),
            "path": server_data_relative(path),
            "type": "folder" if is_dir else "file",
            "size": 0 if is_dir else int(stat.st_size),
            "modified": int(stat.st_mtime),
            "extension": "" if is_dir else path.suffix,
        }
        if not is_dir:
            entry["modified_ns"] = int(stat.st_mtime_ns)
            entry.update(server_data_manifest_structural_metadata(path, path, stat))
            entry.update(space_pdf_package_manifest_metadata(path))
            entry.update(server_data_manifest_vocab_metadata(path))
        return entry
    except Exception:
        return None


def server_data_manifest_should_skip(path: Path) -> bool:
    try:
        if (path.suffix.lower() == ".pdf" or path.suffix.lower() in IMAGE_FILE_SUFFIXES) and space_pdf_package_path_for_legacy(path):
            return True
        if path.name == SERVER_DATA_MANIFEST_FILE.name or path.name.startswith(f".{SERVER_DATA_MANIFEST_FILE.name}"):
            return True
        if path.name.startswith("._future_") and path.suffix.lower() == ".json":
            return True
        rel_parts = path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
        return bool(rel_parts and (rel_parts[0].startswith("_") or rel_parts[0] in server_data_manifest_skip_tops()))
    except Exception:
        return False


def scan_server_data_manifest_folder(folder: Path, folders: dict[str, list[dict]]) -> None:
    rel = server_data_relative(folder)
    old_rows = folders.get(rel) if isinstance(folders.get(rel), list) else []
    entries: list[dict] = []
    folder_link_payload = read_server_data_folder_link_payload(folder)
    if folder_link_payload:
        target_folder = server_data_folder_link_target_path(folder, username="", admin=True)
        if target_folder is None or not target_folder.is_dir():
            if old_rows:
                folders[rel] = old_rows
                stt_debug_log("server_data_manifest_link_target_unavailable", path=rel, preserved_rows=len(old_rows))
                return
            stt_debug_log("server_data_manifest_link_target_unavailable", path=rel, preserved_rows=0)
            # Keep the on-disk link markers and their folder skeleton; scanning must never delete user data.
            try:
                children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), natural_sort_key(item.name)))
            except OSError:
                folders.setdefault(rel, [])
                return
            for child in children:
                try:
                    if not child.is_dir() or server_data_manifest_should_skip(child):
                        continue
                except Exception:
                    continue
                entry = server_data_manifest_entry(child)
                if entry:
                    entries.append(entry)
                scan_server_data_manifest_folder(child, folders)
            folders[rel] = entries
            return
        # Updated 2026-07-21: a linked root is a virtual manifest mirror; never create or scan propagated skeleton markers.
        folders[rel] = []
        return
    try:
        children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), natural_sort_key(item.name)))
    except OSError:
        folders[rel] = entries
        return
    for child in children:
        if server_data_manifest_should_skip(child):
            continue
        try:
            is_dir = child.is_dir()
        except Exception:
            continue
        if is_dir:
            entry = server_data_manifest_entry(child)
            if entry:
                entries.append(entry)
            scan_server_data_manifest_folder(child, folders)
            continue
        if child.is_file() and is_lesson_file(child):
            entry = server_data_manifest_entry(child)
            if entry:
                entries.append(entry)
    folders[rel] = entries


# Added 2026-07-16: refreshes one manifest folder without walking unchanged descendants during startup delta checks.
def scan_server_data_manifest_folder_delta(folder: Path, folders: dict[str, list[dict]], changed_paths: set[str] | None = None) -> None:
    rel = server_data_relative(folder)
    changed = {clean_path_value(path).lower() for path in (changed_paths or set())}
    old_rows = folders.get(rel) if isinstance(folders.get(rel), list) else []
    old_child_paths = {
        clean_path_value(row.get("effective_path") or row.get("link_target") or row.get("path", ""))
        for row in old_rows
        if isinstance(row, dict) and clean(row.get("type", "")) == "folder"
    }
    entries: list[dict] = []
    current_child_paths: set[str] = set()
    folder_link_payload = read_server_data_folder_link_payload(folder)
    if folder_link_payload:
        target_folder = server_data_folder_link_target_path(folder, username="", admin=True)
        if target_folder is None or not target_folder.is_dir():
            folders[rel] = old_rows
            stt_debug_log("server_data_manifest_link_target_unavailable", path=rel, preserved_rows=len(old_rows))
            return
        # Updated 2026-07-21: delta refresh also treats linked descendants as virtual manifest rows.
        folders[rel] = []
        return
    try:
        children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), natural_sort_key(item.name)))
    except OSError:
        folders[rel] = entries
        return
    for child in children:
        if server_data_manifest_should_skip(child):
            continue
        try:
            is_dir = child.is_dir()
        except Exception:
            continue
        if is_dir:
            entry = server_data_manifest_entry(child)
            if entry:
                entries.append(entry)
            child_rel = server_data_relative(child)
            if child_rel:
                current_child_paths.add(child_rel)
                child_key = child_rel.lower()
                child_changed = child_key in changed or any(path.startswith(f"{child_key}/") for path in changed)
                child_new = child_rel not in folders
                if child_new:
                    scan_server_data_manifest_folder(child, folders)
                elif child_changed:
                    scan_server_data_manifest_folder_delta(child, folders, changed)
            continue
        if child.is_file() and is_lesson_file(child):
            entry = server_data_manifest_entry(child)
            if entry:
                entries.append(entry)
    for removed_child in old_child_paths - current_child_paths:
        for key in list(folders.keys()):
            if key == removed_child or key.startswith(f"{removed_child}/"):
                folders.pop(key, None)
    folders[rel] = entries


def server_data_manifest_file_counts(entry: dict | None) -> dict:
    counts = {
        "folder_count": 0,
        "file_count": 0,
        "space_v_file_count": 0,
        "word_count": 0,
    }
    if not isinstance(entry, dict) or clean(entry.get("type", "")) != "file":
        return counts
    extension = clean(entry.get("extension", "")).lower()
    if extension not in LESSON_FILE_SUFFIXES:
        return counts
    counts["file_count"] = 1
    if extension in {".space_v", ".space_b"}:
        counts["space_v_file_count"] = 1
        try:
            target_rel = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry.get("path", ""))
            if target_rel:
                meta = cached_lesson_file_metadata(server_data_manifest_path(target_rel))
                counts["word_count"] = max(0, int(meta.get("nodes", 0) or 0))
        except Exception:
            counts["word_count"] = 0
    return counts


def enrich_server_data_manifest_counts(folders: dict[str, list[dict]]) -> None:
    if not isinstance(folders, dict):
        return
    memo: dict[str, dict] = {}

    def add_counts(base: dict, extra: dict) -> None:
        for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
            try:
                base[key] = int(base.get(key, 0) or 0) + max(0, int(extra.get(key, 0) or 0))
            except Exception:
                base[key] = int(base.get(key, 0) or 0)

    def counts_for_rel(relative_path: str = "", stack: set[str] | None = None) -> dict:
        rel = clean_path_value(relative_path)
        if rel in memo:
            return dict(memo[rel])
        active = set(stack or set())
        if rel.lower() in active:
            return {"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0}
        active.add(rel.lower())
        rows = folders.get(rel)
        total = {"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0}
        if not isinstance(rows, list):
            memo[rel] = dict(total)
            return dict(total)
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_type = clean(row.get("type", ""))
            if row_type == "folder":
                child_rel = clean_path_value(row.get("effective_path") or row.get("link_target") or row.get("path", ""))
                child_counts = counts_for_rel(child_rel, active) if child_rel in folders else None
                if child_counts is None:
                    try:
                        child_counts = server_data_folder_counts_cached(server_data_manifest_path(child_rel))
                    except Exception:
                        child_counts = {"file_count": 0, "space_v_file_count": 0, "word_count": 0}
                    child_counts = {
                        "folder_count": int(child_counts.get("folder_count", 0) or 0),
                        "file_count": int(child_counts.get("file_count", 0) or 0),
                        "space_v_file_count": int(child_counts.get("space_v_file_count", 0) or 0),
                        "word_count": int(child_counts.get("word_count", 0) or 0),
                    }
                for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
                    try:
                        row[key] = max(0, int(child_counts.get(key, 0) or 0))
                    except Exception:
                        row[key] = 0
                if row.get("linked") or row.get("link_target"):
                    row["counts_from_manifest_build"] = True
                    try:
                        update_server_data_folder_link_counts(server_data_manifest_path(clean_path_value(row.get("path", ""))), row)
                    except Exception:
                        pass
                total["folder_count"] += 1
                add_counts(total, child_counts)
                continue
            file_counts = server_data_manifest_file_counts(row)
            add_counts(total, file_counts)
        memo[rel] = dict(total)
        return dict(total)

    for rel in list(folders.keys()):
        counts_for_rel(rel)


# Added 2026-07-05: updates manifest counts only near folders touched by a small mutation.
def enrich_server_data_manifest_counts_for_paths(folders: dict[str, list[dict]], relative_paths: set[str] | list[str] | tuple[str, ...]) -> None:
    if not isinstance(folders, dict):
        return
    targets = {
        clean_path_value(path)
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not targets:
        return
    memo: dict[str, dict] = {}

    def add_counts(base: dict, extra: dict) -> None:
        for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
            try:
                base[key] = int(base.get(key, 0) or 0) + max(0, int(extra.get(key, 0) or 0))
            except Exception:
                base[key] = int(base.get(key, 0) or 0)

    def counts_for_rel(relative_path: str = "", stack: set[str] | None = None) -> dict:
        rel = clean_path_value(relative_path)
        if rel in memo:
            return dict(memo[rel])
        active = set(stack or set())
        if rel.lower() in active:
            return {"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0}
        active.add(rel.lower())
        rows = folders.get(rel)
        total = {"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0}
        if not isinstance(rows, list):
            memo[rel] = dict(total)
            return dict(total)
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_type = clean(row.get("type", ""))
            if row_type == "folder":
                child_rel = clean_path_value(row.get("effective_path") or row.get("link_target") or row.get("path", ""))
                child_counts = counts_for_rel(child_rel, active) if child_rel in folders else None
                if child_counts is None:
                    child_counts = {"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0}
                for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
                    try:
                        row[key] = max(0, int(child_counts.get(key, 0) or 0))
                    except Exception:
                        row[key] = 0
                total["folder_count"] += 1
                add_counts(total, child_counts)
                continue
            file_counts = server_data_manifest_file_counts(row)
            add_counts(total, file_counts)
        memo[rel] = dict(total)
        return dict(total)

    parents: set[str] = set()
    for target in targets:
        current = target
        while current:
            if current in folders:
                parents.add(current)
            current = "/".join(current.split("/")[:-1])
    for rel in sorted(parents, key=lambda value: value.count("/"), reverse=True):
        counts_for_rel(rel)
    for rel in list(parents):
        parent_rel = "/".join(rel.split("/")[:-1])
        rows = folders.get(parent_rel)
        if not isinstance(rows, list):
            continue
        rel_counts = counts_for_rel(rel)
        for row in rows:
            if not isinstance(row, dict) or clean(row.get("type", "")) != "folder":
                continue
            child_rel = clean_path_value(row.get("effective_path") or row.get("link_target") or row.get("path", ""))
            if child_rel != rel:
                continue
            for key in ("folder_count", "file_count", "space_v_file_count", "word_count"):
                try:
                    row[key] = max(0, int(rel_counts.get(key, 0) or 0))
                except Exception:
                    row[key] = 0


def server_data_manifest_root_revision(folders: dict, root: str) -> str:
    root_key = clean(root).lower()
    if not root_key or not isinstance(folders, dict):
        return ""
    root_entries = [
        entry
        for entry in (folders.get("") or [])
        if isinstance(entry, dict) and clean_path_value(entry.get("path", "")).split("/", 1)[0].lower() == root_key
    ]
    branch_rows = [
        (clean_path_value(path), rows if isinstance(rows, list) else [])
        for path, rows in folders.items()
        if clean_path_value(path).lower() == root_key or clean_path_value(path).lower().startswith(f"{root_key}/")
    ]
    branch_rows.sort(key=lambda item: (item[0].count("/"), item[0].lower()))
    data = json.dumps([root_entries, branch_rows], ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha1(data).hexdigest()


def build_server_data_manifest(signature: str = "") -> dict:
    ensure_server_data_common_folder()
    folders: dict[str, list[dict]] = {"": []}
    root_entries: list[dict] = []
    try:
        top_folders = sorted(SERVER_DATA_ROOT.iterdir(), key=lambda item: natural_sort_key(item.name))
    except OSError:
        top_folders = []
    allowed_top_names = server_data_manifest_allowed_top_names()
    for item in top_folders:
        try:
            if not item.is_dir() or item.name.lower() not in allowed_top_names:
                continue
        except Exception:
            continue
        entry = server_data_manifest_entry(item)
        if not entry:
            continue
        root_entries.append(entry)
        scan_server_data_manifest_folder(item, folders)
    folders[""] = root_entries
    enrich_server_data_manifest_counts(folders)
    root_entries.sort(key=lambda entry: (clean(entry.get("name", "")).lower() != "common", natural_sort_key(entry.get("name", ""))))
    folders[""] = root_entries
    runtime_root_revisions = {
        clean_path_value(entry.get("path", "")).split("/", 1)[0].lower(): server_data_manifest_root_revision(
            folders,
            clean_path_value(entry.get("path", "")).split("/", 1)[0],
        )
        for entry in root_entries
        if clean_path_value(entry.get("path", ""))
    }
    runtime_revision = hashlib.sha1(
        "|".join(f"{root}:{revision}" for root, revision in sorted(runtime_root_revisions.items())).encode("utf-8", "ignore")
    ).hexdigest()
    manifest = {
        "version": 1,
        "structural_metadata_version": SERVER_DATA_STRUCTURAL_METADATA_VERSION,
        "root": str(SERVER_DATA_ROOT),
        "updated_at": utc_timestamp(),
        "signature": clean(signature),
        "runtime_revision": runtime_revision,
        "runtime_root_revisions": runtime_root_revisions,
        "runtime_root_revision_version": 1,
        "folders": folders,
    }
    try:
        SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest, indent=None)
    except Exception as exc:
        stt_debug_log("server_data_manifest_write_failed", error=str(exc))
    return manifest
