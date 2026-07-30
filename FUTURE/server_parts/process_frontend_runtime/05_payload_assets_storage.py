# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def html_bytes(payload: str) -> bytes:
    return payload.encode("utf-8")


def encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(bytes(data or b"")).decode("ascii").rstrip("=")


def decode_base64url(value: str) -> bytes:
    raw = clean(value).replace("-", "+").replace("_", "/")
    raw += "=" * ((4 - (len(raw) % 4)) % 4)
    return base64.b64decode(raw.encode("ascii"), validate=False)


def decode_future_payload_code(raw_code: str) -> dict:
    raw_text = str(raw_code or "").strip()
    if raw_text.startswith("{"):
        payload = json.loads(raw_text)
        if isinstance(payload, dict) and payload.get("k") == "ftg_manifest":
            structure_reference = clean(payload.get("structure", ""))
            structure_payload = structure_asset_json(structure_reference)
            if isinstance(structure_payload, dict):
                return structure_payload
        if isinstance(payload, dict) and payload.get("k") == "ftg" and isinstance(payload.get("n"), list):
            return payload
        if isinstance(payload, dict) and payload.get("k") == "ftv" and isinstance(payload.get("w"), list):
            return payload
        if isinstance(payload, dict) and payload.get("k") == "ftq" and isinstance(payload.get("n"), list):
            return payload
        if isinstance(payload, dict) and payload.get("k") == "ftp" and isinstance(payload.get("nodes") or payload.get("n"), list):
            return payload
        if isinstance(payload, dict) and payload.get("kind") == "future_vocabulary_payload" and isinstance(payload.get("words"), list):
            return payload
        if isinstance(payload, dict) and payload.get("kind") == "future_translation_payload" and isinstance(payload.get("nodes"), list):
            return payload
        if isinstance(payload, dict) and payload.get("kind") == "future_question_payload" and isinstance(payload.get("nodes"), list):
            return payload
        if isinstance(payload, dict) and payload.get("kind") == "future_paragraph_payload" and isinstance(payload.get("nodes"), list):
            return payload
    code = re.sub(r"\s+", "", raw_text).strip()
    if not code.startswith(CODE_PREFIX):
        raise RuntimeError("File chua dung dinh dang FTG1.")
    compressed = decode_base64url(code[len(CODE_PREFIX):])
    payload = json.loads(gzip.decompress(compressed).decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("Payload FTG1 khong hop le.")
    if payload.get("k") == "ftg" and isinstance(payload.get("n"), list):
        return payload
    if payload.get("k") in {"ftv", "ftb"} and isinstance(payload.get("w"), list):
        return payload
    if payload.get("k") == "ftq" and isinstance(payload.get("n"), list):
        return payload
    if payload.get("k") == "ftp" and isinstance(payload.get("nodes") or payload.get("n"), list):
        return payload
    if payload.get("kind") == "future_translation_payload" and isinstance(payload.get("nodes"), list):
        return payload
    if payload.get("kind") == "future_vocabulary_payload" and isinstance(payload.get("words"), list):
        return payload
    if payload.get("kind") == "future_question_payload" and isinstance(payload.get("nodes"), list):
        return payload
    if payload.get("kind") == "future_paragraph_payload" and isinstance(payload.get("nodes"), list):
        return payload
    raise RuntimeError("File khong chua bai hoc Future hop le.")


def load_future_lesson_document(path: Path) -> tuple[dict, Path | None]:
    raw_text = path.read_text(encoding="utf-8-sig", errors="replace")
    structure_path = None
    if raw_text.strip().startswith("{"):
        payload = json.loads(raw_text)
        if isinstance(payload, dict) and payload.get("k") == "ftg_manifest":
            structure_reference = clean(payload.get("structure", ""))
            structure_path = safe_server_asset_path(structure_reference, "Structure")
            structure_payload = structure_asset_json(structure_reference)
            if isinstance(structure_payload, dict):
                return structure_payload, structure_path
    return decode_future_payload_code(raw_text), structure_path


def write_future_lesson_document(path: Path, payload: dict, structure_path: Path | None = None, refresh_manifest: bool = True) -> None:
    if structure_path is not None:
        # Added 2026-07-20: Structure manifests are SQLite-only; never recreate retired JSON files.
        write_structure_asset_json(structure_path, payload)
        try:
            clear_lesson_metadata_cache()
            if refresh_manifest:
                schedule_server_data_manifest_rebuild(0.8)
        except Exception:
            pass
        return
    atomic_write_text(path, encode_future_payload_code(payload), encoding="utf-8")
    try:
        clear_lesson_metadata_cache()
        if refresh_manifest:
            schedule_server_data_manifest_rebuild(0.8)
    except Exception:
        pass


def safe_server_asset_path(relative_path: str = "", required_top: str = "") -> Path:
    ensure_server_data_common_folder()
    raw = str(relative_path or "").replace("\\", "/").strip("/")
    raw_parts = [part.strip() for part in raw.split("/") if part.strip()]
    if len(raw_parts) < 2 or any(part in (".", "..") for part in raw_parts):
        raise RuntimeError("Duong dan asset khong hop le.")
    top = raw_parts[0]
    allowed = {"sound": "Sound", "structure": "Structure", "picture": "Picture", "npc_top": "NPC_TOP"}
    canonical = allowed.get(top.lower())
    if not canonical:
        raise RuntimeError("Chi duoc tai asset Sound, Structure, Picture hoac NPC_TOP.")
    if required_top and canonical.lower() != clean(required_top).lower():
        raise RuntimeError("Sai loai asset.")
    target = (SERVER_DATA_ROOT / canonical).joinpath(*raw_parts[1:]).resolve()
    allowed_root = (SERVER_DATA_ROOT / canonical).resolve()
    try:
        target.relative_to(allowed_root)
    except ValueError as exc:
        raise RuntimeError("Duong dan asset khong hop le.") from exc
    return target


def safe_qmlearn_data_sound_path(relative_path: str = "") -> Path:
    raw = str(relative_path or "").replace("\\", "/").strip("/")
    if not raw or any(part in (".", "..") for part in raw.split("/") if part):
        raise RuntimeError("Duong dan audio QMLearn khong hop le.")
    if re.match(r"^[A-Za-z]:", raw) or raw.startswith("//"):
        target = Path(raw).resolve()
    else:
        target = (QMLEARN_DATA_ROOT / raw).resolve()
    root = QMLEARN_DATA_ROOT.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Chi duoc tai audio trong C:\\QMLearn\\Data.") from exc
    if not target.is_file() and target.suffix.lower() == ".txt":
        mp3_target = target.with_suffix(".mp3")
        if mp3_target.is_file():
            target = mp3_target
    if not target.is_file() or target.suffix.lower() not in {".mp3", ".txt"}:
        raise RuntimeError("Audio QMLearn khong ton tai.")
    return target


def qmlearn_data_relative_path(path: Path | str | None) -> str:
    if path is None:
        return ""
    try:
        return Path(path).resolve().relative_to(QMLEARN_DATA_ROOT.resolve()).as_posix()
    except Exception:
        return ""


def encode_future_payload_code(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return CODE_PREFIX + encode_base64url(gzip.compress(raw, compresslevel=9))


def public_file_etag(path: Path, variant: str = "file") -> str:
    try:
        stat = path.stat()
        return f'W/"{clean(variant) or "file"}-{int(stat.st_mtime_ns):x}-{int(stat.st_size):x}"'
    except Exception:
        return ""


def render_variant_etag(path: Path, variant: str = "render", *parts: object) -> str:
    try:
        stat = path.stat()
        safe_parts = "-".join(safe_name_segment(str(part), "x", 80) for part in parts if str(part) != "")
        suffix = f"-{safe_parts}" if safe_parts else ""
        return f'W/"{clean(variant) or "render"}-{int(stat.st_mtime_ns):x}-{int(stat.st_size):x}{suffix}"'
    except Exception:
        return ""


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8", sync_database: bool = True) -> None:
    target = Path(path)
    database_sync_check = globals().get("server_database_document_requires_sync")
    database_store = globals().get("server_database_store_document_now")
    database_local_only = globals().get("server_database_document_local_only")
    postgres_authoritative = globals().get("server_database_document_postgres_authoritative")
    should_sync_database = callable(postgres_authoritative) and bool(postgres_authoritative(target))
    if sync_database and should_sync_database and callable(database_sync_check) and callable(database_store) and database_sync_check(target):
        stored = database_store(target, text, encoding, authoritative=True)
        if stored and (callable(database_local_only) and database_local_only(target)):
            return
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".tmp-{os.getpid()}-{threading.get_ident()}-{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(text, encoding=encoding)
        try:
            with tmp_path.open("a", encoding=encoding) as handle:
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            pass
        replace_error = None
        for attempt in range(6):
            try:
                os.replace(tmp_path, target)
                replace_error = None
                break
            except PermissionError as exc:
                replace_error = exc
                time.sleep(0.05 * (attempt + 1))
        if replace_error is not None:
            raise replace_error
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def atomic_write_json(path: Path, payload: object, indent: int | None = 2) -> None:
    kwargs = {"ensure_ascii": False}
    if indent is None:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = indent
    atomic_write_text(path, json.dumps(payload, **kwargs), encoding="utf-8")
