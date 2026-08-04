"""Thin Space PDF lesson packages shared by GUI, runtime and migration tools."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


SPACE_PDF_SCHEMA = "space_pdf"
SPACE_PDF_SCHEMA_VERSION = 2
SPACE_PDF_SUPPORTED_SCHEMA_VERSIONS = {1, 2}
SPACE_PDF_MANIFEST_MEMBER = "manifest.json"
SPACE_PDF_SOURCE_MEMBER = "source.pdf"
SPACE_PDF_MANIFEST_MAX_BYTES = 256 * 1024
SPACE_PDF_CHILD_JSON_MAX_BYTES = 32 * 1024 * 1024
SPACE_PDF_MAX_ENTRIES = 256
SPACE_PDF_MAX_TOTAL_UNCOMPRESSED_BYTES = 8 * 1024 * 1024 * 1024
SPACE_PDF_MAX_COMPRESSION_RATIO = 200


@dataclass(frozen=True)
class SpacePdfPackageResult:
    output_path: str
    lesson_id: str
    document_id: str
    source_sha256: str
    package_sha256: str
    package_bytes: int
    source_bytes: int
    validation_status: str
    manifest: dict
    asset_id: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stable_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_sha256(handle) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def _write_source_member(archive: zipfile.ZipFile, source: Path) -> tuple[str, int]:
    info = zipfile.ZipInfo(SPACE_PDF_SOURCE_MEMBER, date_time=datetime.now().timetuple()[:6])
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    digest = hashlib.sha256()
    total = 0
    with source.open("rb") as source_handle, archive.open(info, "w", force_zip64=True) as target_handle:
        for chunk in iter(lambda: source_handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
            target_handle.write(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _safe_member_name(value: str) -> bool:
    path = PurePosixPath(str(value or ""))
    return bool(value and not path.is_absolute() and ".." not in path.parts and "" not in path.parts)


# Added 2026-07-22: transitional relative readers remain rollback-compatible; new v2 writes use canonical assets.
def _safe_relative_source_path(value: str, suffixes: set[str]) -> str:
    raw = str(value or "").replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise RuntimeError("Space package source path is unsafe.")
    if Path(path.name).suffix.lower() not in suffixes:
        raise RuntimeError("Space package source type is invalid.")
    return path.as_posix()


def _validate_asset_id(value: object) -> str:
    asset_id = str(value or "")
    if not asset_id.startswith("ftg-asset-") or len(asset_id) != len("ftg-asset-") + 64:
        raise RuntimeError("Space package asset ID is invalid.")
    if any(char not in "0123456789abcdef" for char in asset_id[len("ftg-asset-"):].lower()):
        raise RuntimeError("Space package asset ID is invalid.")
    return asset_id.lower()


def _discover_server_data_root(package: Path, explicit_root: str | Path | None = None) -> Path:
    if explicit_root is not None:
        return Path(explicit_root).resolve()
    for parent in (package.parent, *package.parents):
        if (parent / "_assets").is_dir():
            return parent.resolve()
    default = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", r"C:\server data")).resolve()
    try:
        package.resolve().relative_to(default)
        return default
    except ValueError as exc:
        raise RuntimeError("Server Data root is required to resolve this canonical asset.") from exc


def _builder_server_data_root(output: Path, explicit_root: str | Path | None) -> Path:
    if explicit_root is not None:
        return Path(explicit_root).resolve()
    default = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", r"C:\server data")).resolve()
    try:
        output.resolve().relative_to(default)
        return default
    except ValueError:
        return output.parent.resolve()


# Added 2026-07-22: all PDF/Picture importers share one streaming, sharded, content-addressed asset store.
def import_canonical_space_asset(
    source_path: str | Path,
    server_data_root: str | Path,
    *,
    asset_kind: str,
    allowed_suffixes: set[str],
) -> dict:
    source = Path(source_path).resolve()
    root = Path(server_data_root).resolve()
    suffix = source.suffix.lower()
    if not source.is_file() or suffix not in allowed_suffixes:
        raise RuntimeError("Canonical asset source is invalid.")
    if asset_kind not in {"pdf", "picture"}:
        raise RuntimeError("Canonical asset kind is invalid.")
    incoming = root / "_assets" / ".incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    temporary = incoming / f".{uuid.uuid4().hex}.asset.tmp"
    digest = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as source_handle, temporary.open("wb") as target_handle:
            for chunk in iter(lambda: source_handle.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
                target_handle.write(chunk)
                total += len(chunk)
            target_handle.flush()
            os.fsync(target_handle.fileno())
        source_hash = digest.hexdigest()
        asset_id = f"ftg-asset-{source_hash}"
        locator = PurePosixPath("_assets", asset_kind, source_hash[:2], f"{asset_id}{suffix}").as_posix()
        destination = root / Path(*PurePosixPath(locator).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        created = False
        if destination.exists():
            if destination.stat().st_size != total or _file_sha256(destination) != source_hash:
                raise RuntimeError("Canonical asset path exists with corrupt bytes.")
        else:
            os.replace(temporary, destination)
            created = True
        return {
            "asset_id": asset_id,
            "asset_locator": locator,
            "asset_path": destination,
            "source_sha256": source_hash,
            "source_bytes": total,
            "created": created,
        }
    finally:
        temporary.unlink(missing_ok=True)


# Added 2026-07-22: readers accept embedded v1 packages while all new writes use thin relative assets.
def resolve_space_pdf_source_path(
    package_path: str | Path,
    manifest: dict | None = None,
    server_data_root: str | Path | None = None,
) -> Path | None:
    package = Path(package_path).resolve()
    current = manifest if isinstance(manifest, dict) else _validate_manifest(read_space_pdf_manifest_light(package))
    if current.get("source_storage") == "embedded":
        return None
    if current.get("source_storage") == "canonical":
        relative = _safe_relative_source_path(current.get("asset_locator", ""), {".pdf"})
        if not relative.startswith("_assets/pdf/"):
            raise RuntimeError("Space PDF canonical asset locator is invalid.")
        resolved = (_discover_server_data_root(package, server_data_root) / Path(*PurePosixPath(relative).parts)).resolve()
    else:
        relative = _safe_relative_source_path(current.get("source_path", ""), {".pdf"})
        resolved = (package.parent / Path(*PurePosixPath(relative).parts)).resolve()
        try:
            resolved.relative_to(package.parent.resolve())
        except ValueError as exc:
            raise RuntimeError("Space PDF source escapes its package folder.") from exc
    return resolved


def _build_lock_path(output: Path) -> Path:
    token = hashlib.sha256(str(output).lower().encode("utf-8")).hexdigest()[:12]
    return output.parent / f".spdf-{token}.build.lock"


def _build_temp_pattern(output: Path) -> str:
    return f".spdf-{hashlib.sha256(str(output).lower().encode('utf-8')).hexdigest()[:12]}-*.tmp"


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        return False


def _acquire_build_lock(output: Path) -> Path:
    lock_path = _build_lock_path(output)
    for _attempt in range(2):
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                row = json.loads(lock_path.read_text(encoding="utf-8"))
            except Exception:
                row = {}
            owner_pid = int(row.get("pid", 0) or 0)
            started_epoch = float(row.get("started_epoch", 0) or 0)
            if _pid_is_alive(owner_pid) and max(0.0, time.time() - started_epoch) < 6 * 3600:
                raise RuntimeError("Another builder is already writing this Space PDF output.")
            lock_path.unlink(missing_ok=True)
            continue
        else:
            try:
                payload = json.dumps({"pid": os.getpid(), "started_epoch": time.time()}, separators=(",", ":")).encode("utf-8")
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            for stale in output.parent.glob(_build_temp_pattern(output)):
                stale.unlink(missing_ok=True)
            return lock_path
    raise RuntimeError("Could not acquire the Space PDF build lock.")


def _validate_id(value: object, prefix: str) -> str:
    text = str(value or "").strip()
    if not text.startswith(prefix) or len(text) > 160:
        raise RuntimeError(f"Invalid package identity: {prefix}")
    return text


def _thumbnail_webp(pdf_path: Path) -> bytes:
    try:
        import fitz
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Thumbnail generation requires PyMuPDF and Pillow.") from exc
    document = fitz.open(str(pdf_path))
    try:
        if document.page_count <= 0:
            raise RuntimeError("The PDF has no pages.")
        pixmap = document.load_page(0).get_pixmap(matrix=fitz.Matrix(0.45, 0.45), alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=82, method=4)
        return output.getvalue()
    finally:
        document.close()


# Added 2026-07-22: watcher/open paths can read identity without hashing or extracting the source PDF.
def read_space_pdf_manifest_light(package_path: str | Path) -> dict:
    package = Path(package_path)
    with zipfile.ZipFile(package, "r") as archive:
        try:
            info = archive.getinfo(SPACE_PDF_MANIFEST_MEMBER)
        except KeyError as exc:
            raise RuntimeError("Space PDF package is missing manifest.json.") from exc
        if info.file_size <= 0 or info.file_size > SPACE_PDF_MANIFEST_MAX_BYTES:
            raise RuntimeError("Space PDF manifest size is invalid.")
        raw = archive.read(info)
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Space PDF manifest is invalid JSON.") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Space PDF manifest must be an object.")
    return manifest


def _validate_manifest(manifest: dict) -> dict:
    if str(manifest.get("schema") or "") != SPACE_PDF_SCHEMA:
        raise RuntimeError("Unsupported Space PDF schema.")
    version = int(manifest.get("schema_version", 0) or 0)
    if version not in SPACE_PDF_SUPPORTED_SCHEMA_VERSIONS:
        if version > SPACE_PDF_SCHEMA_VERSION:
            raise RuntimeError("Space PDF package schema is newer than this builder.")
        raise RuntimeError("Space PDF package schema version is invalid.")
    lesson_id = _validate_id(manifest.get("lesson_id"), "ftg-lesson-")
    document_id = _validate_id(manifest.get("document_id"), "ftg-document-")
    source_storage = str(manifest.get("source_storage") or ("embedded" if version == 1 else "")).lower()
    source_member = str(manifest.get("source_member") or "")
    source_path = str(manifest.get("source_path") or "")
    if source_storage == "embedded":
        if source_member != SPACE_PDF_SOURCE_MEMBER:
            raise RuntimeError("Space PDF source member is invalid.")
    elif source_storage == "relative":
        source_path = _safe_relative_source_path(source_path, {".pdf"})
        source_member = ""
    elif source_storage == "canonical":
        asset_id = _validate_asset_id(manifest.get("asset_id"))
        asset_locator = _safe_relative_source_path(manifest.get("asset_locator", ""), {".pdf"})
        if not asset_locator.startswith("_assets/pdf/") or Path(asset_locator).stem != asset_id:
            raise RuntimeError("Space PDF canonical asset mapping is invalid.")
        source_member = ""
        source_path = ""
    else:
        raise RuntimeError("Space PDF source storage is invalid.")
    source_hash = str(manifest.get("source_sha256") or "").lower()
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise RuntimeError("Space PDF source SHA-256 is invalid.")
    source_bytes = int(manifest.get("source_bytes", -1) or -1)
    if source_bytes <= 0:
        raise RuntimeError("Space PDF source size is invalid.")
    package_revision = int(manifest.get("package_revision", 0) or 0)
    if package_revision <= 0:
        raise RuntimeError("Space PDF package revision is invalid.")
    return {
        **manifest,
        "lesson_id": lesson_id,
        "document_id": document_id,
        "source_member": source_member,
        "source_path": source_path,
        "source_storage": source_storage,
        "asset_id": str(manifest.get("asset_id") or ""),
        "asset_locator": str(manifest.get("asset_locator") or ""),
        "source_sha256": source_hash,
        "source_bytes": source_bytes,
        "package_revision": package_revision,
    }


# Added 2026-07-22: runtime discovery validates portable identity without hashing embedded source bytes.
def validate_space_pdf_manifest_light(package_path: str | Path) -> dict:
    return _validate_manifest(read_space_pdf_manifest_light(package_path))


def _child_json_bytes(value: object, label: str) -> bytes:
    if value is None:
        return b""
    if not isinstance(value, (dict, list)):
        raise RuntimeError(f"{label} must be a JSON object or array.")
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > SPACE_PDF_CHILD_JSON_MAX_BYTES:
        raise RuntimeError(f"{label} is too large for a Space PDF package.")
    return raw


# Added 2026-07-22: full validation is used only at build/import/change boundaries, never on progress hot paths.
def validate_space_pdf_package(
    package_path: str | Path,
    verify_source: bool = True,
    server_data_root: str | Path | None = None,
) -> dict:
    package = Path(package_path)
    if not package.is_file():
        raise RuntimeError("Space PDF package does not exist.")
    with zipfile.ZipFile(package, "r") as archive:
        infos = archive.infolist()
        if not infos or len(infos) > SPACE_PDF_MAX_ENTRIES:
            raise RuntimeError("Space PDF package entry count is invalid.")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or any(not _safe_member_name(name) for name in names):
            raise RuntimeError("Space PDF package contains unsafe or duplicate members.")
        if any(info.flag_bits & 0x1 for info in infos):
            raise RuntimeError("Encrypted Space PDF members are not supported.")
        if any(stat.S_ISLNK((int(info.external_attr) >> 16) & 0xFFFF) for info in infos):
            raise RuntimeError("Space PDF package symlinks are not supported.")
        total_uncompressed = sum(max(0, int(info.file_size)) for info in infos)
        total_compressed = sum(max(1, int(info.compress_size)) for info in infos)
        if total_uncompressed > SPACE_PDF_MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise RuntimeError("Space PDF package is too large.")
        if total_uncompressed > total_compressed * SPACE_PDF_MAX_COMPRESSION_RATIO:
            raise RuntimeError("Space PDF package compression ratio is unsafe.")
        manifest = _validate_manifest(read_space_pdf_manifest_light(package))
        source_info = None
        if manifest["source_storage"] == "embedded":
            try:
                source_info = archive.getinfo(manifest["source_member"])
            except KeyError as exc:
                raise RuntimeError("Space PDF package is missing the source PDF.") from exc
            if source_info.file_size != manifest["source_bytes"]:
                raise RuntimeError("Space PDF source size does not match the manifest.")
        content_members = manifest.get("content_members") if isinstance(manifest.get("content_members"), dict) else {}
        for label, expected_member in (
            ("ai_notices", "lesson/ai_notices.json"),
            ("ai_questions", "lesson/ai_questions.json"),
            ("audio_markers", "lesson/audio_markers.json"),
        ):
            metadata = content_members.get(label)
            if metadata is None:
                continue
            if not isinstance(metadata, dict) or str(metadata.get("member") or "") != expected_member:
                raise RuntimeError(f"Space PDF {label} metadata is invalid.")
            try:
                member_info = archive.getinfo(expected_member)
            except KeyError as exc:
                raise RuntimeError(f"Space PDF package is missing {expected_member}.") from exc
            expected_bytes = int(metadata.get("bytes", -1) or -1)
            expected_hash = str(metadata.get("sha256") or "").lower()
            if expected_bytes <= 0 or expected_bytes > SPACE_PDF_CHILD_JSON_MAX_BYTES or member_info.file_size != expected_bytes:
                raise RuntimeError(f"Space PDF {label} size is invalid.")
            child_raw = archive.read(member_info)
            if hashlib.sha256(child_raw).hexdigest() != expected_hash:
                raise RuntimeError(f"Space PDF {label} fingerprint does not match the manifest.")
            try:
                child_value = json.loads(child_raw.decode("utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Space PDF {label} JSON is invalid.") from exc
            if not isinstance(child_value, (dict, list)):
                raise RuntimeError(f"Space PDF {label} must be a JSON object or array.")
        if verify_source:
            if source_info is not None:
                with archive.open(source_info, "r") as source_handle:
                    source_hash, source_bytes = _stream_sha256(source_handle)
            else:
                source_path = resolve_space_pdf_source_path(package, manifest, server_data_root)
                if source_path is None or not source_path.is_file():
                    raise RuntimeError("Space PDF relative source asset is missing.")
                with source_path.open("rb") as source_handle:
                    source_hash, source_bytes = _stream_sha256(source_handle)
            if source_bytes != manifest["source_bytes"] or source_hash != manifest["source_sha256"]:
                raise RuntimeError("Space PDF source fingerprint does not match the manifest.")
    return manifest


# Added 2026-07-22: one atomic finalizer is shared by the GUI and future legacy migration batches.
def build_space_pdf_package(
    source_pdf: str | Path,
    output_path: str | Path,
    *,
    title: str = "",
    owner_scope: str = "common",
    lesson_id: str = "",
    document_id: str = "",
    package_revision: int = 1,
    create_thumbnail: bool = False,
    ai_notices: object = None,
    ai_questions: object = None,
    audio_markers: object = None,
    overwrite: bool = False,
    delete_source_after_success: bool = False,
    server_data_root: str | Path | None = None,
) -> SpacePdfPackageResult:
    source = Path(source_pdf).resolve()
    output = Path(output_path).resolve()
    asset_root = _builder_server_data_root(output, server_data_root)
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise RuntimeError("Choose a valid PDF source file.")
    if output.suffix.lower() != ".space_pdf":
        raise RuntimeError("Output must use the .space_pdf extension.")
    if source == output:
        raise RuntimeError("Source and output paths must be different.")
    if output.exists() and not overwrite:
        raise RuntimeError("Output package already exists.")
    if output.exists():
        # Added 2026-07-24: rebuilding a package preserves its logical lesson/document identity.
        existing_manifest = validate_space_pdf_package(output, verify_source=False, server_data_root=asset_root)
        lesson_id = lesson_id or str(existing_manifest["lesson_id"])
        document_id = document_id or str(existing_manifest["document_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    build_lock = _acquire_build_lock(output)
    temporary: Path | None = None
    try:
        asset = import_canonical_space_asset(source, asset_root, asset_kind="pdf", allowed_suffixes={".pdf"})
        source_bytes = int(asset["source_bytes"])
        lesson_id = _validate_id(lesson_id or _stable_id("ftg-lesson-"), "ftg-lesson-")
        document_id = _validate_id(document_id or _stable_id("ftg-document-"), "ftg-document-")
        thumbnail = _thumbnail_webp(source) if create_thumbnail else b""
        child_json = {
            "ai_notices": ("lesson/ai_notices.json", _child_json_bytes(ai_notices, "AI notices")),
            "ai_questions": ("lesson/ai_questions.json", _child_json_bytes(ai_questions, "AI questions")),
            "audio_markers": ("lesson/audio_markers.json", _child_json_bytes(audio_markers, "Audio markers")),
        }
        # Added 2026-07-22: keep atomic temp names short so deep Unicode lesson folders stay below Windows path limits.
        temporary = output.parent / _build_temp_pattern(output).replace("*", uuid.uuid4().hex)
        source_hash = str(asset["source_sha256"])
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            manifest = {
                "schema": SPACE_PDF_SCHEMA,
                "schema_version": SPACE_PDF_SCHEMA_VERSION,
                "lesson_id": lesson_id,
                "document_id": document_id,
                "package_revision": max(1, int(package_revision or 1)),
                "title": str(title or source.stem).strip()[:240],
                "owner_scope": str(owner_scope or "common").strip()[:80],
                "source_filename": source.name,
                "source_storage": "canonical",
                "asset_id": asset["asset_id"],
                "asset_locator": asset["asset_locator"],
                "source_sha256": source_hash,
                "source_bytes": source_bytes,
                "created_at": _utc_now(),
                "builder": "future-space-pdf-package-v2-thin",
            }
            if thumbnail:
                manifest["thumbnail_member"] = "thumbnail.webp"
                manifest["thumbnail_sha256"] = hashlib.sha256(thumbnail).hexdigest()
                manifest["thumbnail_bytes"] = len(thumbnail)
            content_members = {}
            for label, (member, raw) in child_json.items():
                if raw:
                    content_members[label] = {"member": member, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                    archive.writestr(member, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            if content_members:
                manifest["content_members"] = content_members
            manifest_raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if len(manifest_raw) > SPACE_PDF_MANIFEST_MAX_BYTES:
                raise RuntimeError("Generated Space PDF manifest is too large.")
            archive.writestr(SPACE_PDF_MANIFEST_MEMBER, manifest_raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            if thumbnail:
                archive.writestr("thumbnail.webp", thumbnail, compress_type=zipfile.ZIP_STORED)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        final_manifest = validate_space_pdf_package(temporary, verify_source=True, server_data_root=asset_root)
        package_hash = _file_sha256(temporary)
        os.replace(temporary, output)
        if delete_source_after_success:
            source.unlink()
        return SpacePdfPackageResult(
            output_path=str(output),
            lesson_id=lesson_id,
            document_id=document_id,
            source_sha256=source_hash,
            package_sha256=package_hash,
            package_bytes=int(output.stat().st_size),
            source_bytes=source_bytes,
            validation_status="verified",
            manifest=final_manifest,
            asset_id=str(asset["asset_id"]),
        )
    except Exception:
        try:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    finally:
        build_lock.unlink(missing_ok=True)


def duplicate_space_pdf_as_new(
    source_package: str | Path,
    output_path: str | Path,
    *,
    title: str = "",
    overwrite: bool = False,
) -> SpacePdfPackageResult:
    source_package = Path(source_package)
    manifest = validate_space_pdf_package(source_package, verify_source=True)
    temporary_source: Path | None = None
    try:
        embedded_children = {}
        with zipfile.ZipFile(source_package, "r") as archive:
            if manifest["source_storage"] == "embedded":
                temporary_source = Path(output_path).parent / f".spdf-source-{uuid.uuid4().hex}.pdf"
                with temporary_source.open("wb") as handle, archive.open(manifest["source_member"], "r") as source_handle:
                    shutil.copyfileobj(source_handle, handle, length=4 * 1024 * 1024)
            else:
                temporary_source = resolve_space_pdf_source_path(source_package, manifest)
            content_members = manifest.get("content_members") if isinstance(manifest.get("content_members"), dict) else {}
            for label in ("ai_notices", "ai_questions", "audio_markers"):
                metadata = content_members.get(label)
                if isinstance(metadata, dict):
                    embedded_children[label] = json.loads(archive.read(str(metadata["member"])).decode("utf-8"))
        if temporary_source is None:
            raise RuntimeError("Space PDF source asset is unavailable for duplication.")
        return build_space_pdf_package(
            temporary_source,
            output_path,
            title=title or str(manifest.get("title") or ""),
            owner_scope=str(manifest.get("owner_scope") or "common"),
            lesson_id=_stable_id("ftg-lesson-"),
            document_id=str(manifest["document_id"]),
            ai_notices=embedded_children.get("ai_notices"),
            ai_questions=embedded_children.get("ai_questions"),
            audio_markers=embedded_children.get("audio_markers"),
            overwrite=overwrite,
            server_data_root=_discover_server_data_root(source_package),
        )
    finally:
        if temporary_source is not None and temporary_source.name.startswith(".spdf-source-"):
            temporary_source.unlink(missing_ok=True)


def compare_space_pdf_packages(left_path: str | Path, right_path: str | Path) -> str:
    left = validate_space_pdf_package(left_path, verify_source=True)
    right = validate_space_pdf_package(right_path, verify_source=True)
    if left["lesson_id"] != right["lesson_id"]:
        return "independent"
    if left["document_id"] == right["document_id"] and left["source_sha256"] == right["source_sha256"]:
        return "replica"
    return "collision"
