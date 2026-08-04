"""Atomic thin Space Picture packages using the shared lesson identity contract."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from future_space_pdf_package import (
    SPACE_PDF_CHILD_JSON_MAX_BYTES,
    SPACE_PDF_MANIFEST_MAX_BYTES,
    SPACE_PDF_MAX_COMPRESSION_RATIO,
    SPACE_PDF_MAX_ENTRIES,
    SPACE_PDF_MAX_TOTAL_UNCOMPRESSED_BYTES,
    SpacePdfPackageResult,
    _acquire_build_lock,
    _build_temp_pattern,
    _child_json_bytes,
    _file_sha256,
    _discover_server_data_root,
    _builder_server_data_root,
    _validate_asset_id,
    import_canonical_space_asset,
    _stable_id,
    _stream_sha256,
    _safe_relative_source_path,
    _utc_now,
    _validate_id,
)


SPACE_PICTURE_SCHEMA = "space_picture"
SPACE_PICTURE_SCHEMA_VERSION = 2
SPACE_PICTURE_SUPPORTED_SCHEMA_VERSIONS = {1, 2}
SPACE_PICTURE_MANIFEST_MEMBER = "manifest.json"
SPACE_PICTURE_SOURCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def _safe_member_name(value: str) -> bool:
    path = PurePosixPath(str(value or ""))
    return bool(value and not path.is_absolute() and ".." not in path.parts and "" not in path.parts)


def _source_member(source_suffix: str) -> str:
    suffix = str(source_suffix or "").lower()
    if suffix not in SPACE_PICTURE_SOURCE_SUFFIXES:
        raise RuntimeError("Choose a supported picture source file.")
    return f"source{suffix}"


def _mime_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


# Added 2026-07-22: Picture v2 resolves one adjacent authoritative image asset without package duplication.
def resolve_space_picture_source_path(
    package_path: str | Path,
    manifest: dict | None = None,
    server_data_root: str | Path | None = None,
) -> Path | None:
    package = Path(package_path).resolve()
    current = manifest if isinstance(manifest, dict) else _validate_manifest(read_space_picture_manifest_light(package))
    if current.get("source_storage") == "embedded":
        return None
    if current.get("source_storage") == "canonical":
        relative = _safe_relative_source_path(current.get("asset_locator", ""), SPACE_PICTURE_SOURCE_SUFFIXES)
        if not relative.startswith("_assets/picture/"):
            raise RuntimeError("Space Picture canonical asset locator is invalid.")
        resolved = (_discover_server_data_root(package, server_data_root) / Path(*PurePosixPath(relative).parts)).resolve()
    else:
        relative = _safe_relative_source_path(current.get("source_path", ""), SPACE_PICTURE_SOURCE_SUFFIXES)
        resolved = (package.parent / Path(*PurePosixPath(relative).parts)).resolve()
        try:
            resolved.relative_to(package.parent.resolve())
        except ValueError as exc:
            raise RuntimeError("Space Picture source escapes its package folder.") from exc
    return resolved


def _write_source_member(archive: zipfile.ZipFile, source: Path, member: str) -> tuple[str, int]:
    info = zipfile.ZipInfo(member)
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


def read_space_picture_manifest_light(package_path: str | Path) -> dict:
    with zipfile.ZipFile(Path(package_path), "r") as archive:
        try:
            info = archive.getinfo(SPACE_PICTURE_MANIFEST_MEMBER)
        except KeyError as exc:
            raise RuntimeError("Space Picture package is missing manifest.json.") from exc
        if info.file_size <= 0 or info.file_size > SPACE_PDF_MANIFEST_MAX_BYTES:
            raise RuntimeError("Space Picture manifest size is invalid.")
        raw = archive.read(info)
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Space Picture manifest is invalid JSON.") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Space Picture manifest must be an object.")
    return manifest


def _validate_manifest(manifest: dict) -> dict:
    if str(manifest.get("schema") or "") != SPACE_PICTURE_SCHEMA:
        raise RuntimeError("Unsupported Space Picture schema.")
    version = int(manifest.get("schema_version", 0) or 0)
    if version not in SPACE_PICTURE_SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeError("Space Picture package schema version is invalid.")
    lesson_id = _validate_id(manifest.get("lesson_id"), "ftg-lesson-")
    document_id = _validate_id(manifest.get("document_id"), "ftg-document-")
    source_storage = str(manifest.get("source_storage") or ("embedded" if version == 1 else "")).lower()
    source_member = str(manifest.get("source_member") or "")
    source_path = str(manifest.get("source_path") or "")
    if source_storage == "embedded":
        if not _safe_member_name(source_member) or Path(source_member).suffix.lower() not in SPACE_PICTURE_SOURCE_SUFFIXES:
            raise RuntimeError("Space Picture source member is invalid.")
    elif source_storage == "relative":
        source_path = _safe_relative_source_path(source_path, SPACE_PICTURE_SOURCE_SUFFIXES)
        source_member = ""
    elif source_storage == "canonical":
        asset_id = _validate_asset_id(manifest.get("asset_id"))
        asset_locator = _safe_relative_source_path(manifest.get("asset_locator", ""), SPACE_PICTURE_SOURCE_SUFFIXES)
        if not asset_locator.startswith("_assets/picture/") or Path(asset_locator).stem != asset_id:
            raise RuntimeError("Space Picture canonical asset mapping is invalid.")
        source_member = ""
        source_path = ""
    else:
        raise RuntimeError("Space Picture source storage is invalid.")
    source_hash = str(manifest.get("source_sha256") or "").lower()
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise RuntimeError("Space Picture source SHA-256 is invalid.")
    source_bytes = int(manifest.get("source_bytes", -1) or -1)
    if source_bytes <= 0:
        raise RuntimeError("Space Picture source size is invalid.")
    package_revision = int(manifest.get("package_revision", 0) or 0)
    if package_revision <= 0:
        raise RuntimeError("Space Picture package revision is invalid.")
    return {**manifest, "lesson_id": lesson_id, "document_id": document_id, "source_member": source_member,
            "source_path": source_path, "source_storage": source_storage,
            "asset_id": str(manifest.get("asset_id") or ""), "asset_locator": str(manifest.get("asset_locator") or ""),
            "source_sha256": source_hash, "source_bytes": source_bytes, "package_revision": package_revision}


def validate_space_picture_manifest_light(package_path: str | Path) -> dict:
    return _validate_manifest(read_space_picture_manifest_light(package_path))


def validate_space_picture_package(
    package_path: str | Path,
    verify_source: bool = True,
    server_data_root: str | Path | None = None,
) -> dict:
    package = Path(package_path)
    if not package.is_file():
        raise RuntimeError("Space Picture package does not exist.")
    with zipfile.ZipFile(package, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if not infos or len(infos) > SPACE_PDF_MAX_ENTRIES or len(names) != len(set(names)):
            raise RuntimeError("Space Picture package entry count is invalid.")
        if any(not _safe_member_name(name) for name in names):
            raise RuntimeError("Space Picture package contains an unsafe member.")
        if any(info.flag_bits & 0x1 for info in infos):
            raise RuntimeError("Encrypted Space Picture members are not supported.")
        if any(stat.S_ISLNK((int(info.external_attr) >> 16) & 0xFFFF) for info in infos):
            raise RuntimeError("Space Picture package symlinks are not supported.")
        total_uncompressed = sum(max(0, int(info.file_size)) for info in infos)
        total_compressed = sum(max(1, int(info.compress_size)) for info in infos)
        if total_uncompressed > SPACE_PDF_MAX_TOTAL_UNCOMPRESSED_BYTES or total_uncompressed > total_compressed * SPACE_PDF_MAX_COMPRESSION_RATIO:
            raise RuntimeError("Space Picture package size or compression ratio is unsafe.")
        manifest = _validate_manifest(read_space_picture_manifest_light(package))
        source_info = None
        if manifest["source_storage"] == "embedded":
            try:
                source_info = archive.getinfo(manifest["source_member"])
            except KeyError as exc:
                raise RuntimeError("Space Picture package is missing its source image.") from exc
            if source_info.file_size != manifest["source_bytes"]:
                raise RuntimeError("Space Picture source size does not match the manifest.")
        content_members = manifest.get("content_members") if isinstance(manifest.get("content_members"), dict) else {}
        for label, expected_member in (("ai_notices", "lesson/ai_notices.json"), ("ai_questions", "lesson/ai_questions.json"), ("audio_markers", "lesson/audio_markers.json")):
            metadata = content_members.get(label)
            if metadata is None:
                continue
            if not isinstance(metadata, dict) or str(metadata.get("member") or "") != expected_member:
                raise RuntimeError(f"Space Picture {label} metadata is invalid.")
            raw = archive.read(expected_member)
            if len(raw) != int(metadata.get("bytes", -1) or -1) or hashlib.sha256(raw).hexdigest() != str(metadata.get("sha256") or ""):
                raise RuntimeError(f"Space Picture {label} fingerprint is invalid.")
            if not isinstance(json.loads(raw.decode("utf-8")), (dict, list)):
                raise RuntimeError(f"Space Picture {label} must be JSON data.")
        if verify_source:
            if source_info is not None:
                with archive.open(source_info, "r") as source_handle:
                    source_hash, source_bytes = _stream_sha256(source_handle)
            else:
                source_path = resolve_space_picture_source_path(package, manifest, server_data_root)
                if source_path is None or not source_path.is_file():
                    raise RuntimeError("Space Picture relative source asset is missing.")
                with source_path.open("rb") as source_handle:
                    source_hash, source_bytes = _stream_sha256(source_handle)
            if source_hash != manifest["source_sha256"] or source_bytes != manifest["source_bytes"]:
                raise RuntimeError("Space Picture source fingerprint does not match the manifest.")
    return manifest


# Added 2026-07-22: Picture import uses the same atomic ID/child-data semantics as Space PDF.
def build_space_picture_package(source_picture: str | Path, output_path: str | Path, *, title: str = "",
                                owner_scope: str = "common", lesson_id: str = "", document_id: str = "",
                                package_revision: int = 1, ai_notices: object = None, ai_questions: object = None,
                                audio_markers: object = None, overwrite: bool = False,
                                delete_source_after_success: bool = False,
                                server_data_root: str | Path | None = None) -> SpacePdfPackageResult:
    source = Path(source_picture).resolve()
    output = Path(output_path).resolve()
    asset_root = _builder_server_data_root(output, server_data_root)
    if not source.is_file() or source.suffix.lower() not in SPACE_PICTURE_SOURCE_SUFFIXES:
        raise RuntimeError("Choose a supported picture source file.")
    if output.suffix.lower() != ".space_picture":
        raise RuntimeError("Output must use the .space_picture extension.")
    if output.exists() and not overwrite:
        raise RuntimeError("Output package already exists.")
    if output.exists():
        # Added 2026-07-24: rebuilding a package preserves its logical lesson/document identity.
        existing_manifest = validate_space_picture_package(output, verify_source=False, server_data_root=asset_root)
        lesson_id = lesson_id or str(existing_manifest["lesson_id"])
        document_id = document_id or str(existing_manifest["document_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = _acquire_build_lock(output)
    temporary = None
    try:
        asset = import_canonical_space_asset(
            source,
            asset_root,
            asset_kind="picture",
            allowed_suffixes=SPACE_PICTURE_SOURCE_SUFFIXES,
        )
        source_bytes = int(asset["source_bytes"])
        lesson_id = _validate_id(lesson_id or _stable_id("ftg-lesson-"), "ftg-lesson-")
        document_id = _validate_id(document_id or _stable_id("ftg-document-"), "ftg-document-")
        children = {
            "ai_notices": ("lesson/ai_notices.json", _child_json_bytes(ai_notices, "AI notices")),
            "ai_questions": ("lesson/ai_questions.json", _child_json_bytes(ai_questions, "AI questions")),
            "audio_markers": ("lesson/audio_markers.json", _child_json_bytes(audio_markers, "Audio markers")),
        }
        temporary = output.parent / _build_temp_pattern(output).replace("*", uuid.uuid4().hex)
        source_hash = str(asset["source_sha256"])
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            manifest = {
                "schema": SPACE_PICTURE_SCHEMA, "schema_version": SPACE_PICTURE_SCHEMA_VERSION,
                "lesson_id": lesson_id, "document_id": document_id, "package_revision": max(1, int(package_revision or 1)),
                "title": str(title or source.stem).strip()[:240], "owner_scope": str(owner_scope or "common").strip()[:80],
                "source_filename": source.name, "source_storage": "canonical", "asset_id": asset["asset_id"],
                "asset_locator": asset["asset_locator"],
                "source_mime_type": _mime_type(source.name),
                "source_sha256": source_hash, "source_bytes": source_bytes, "created_at": _utc_now(),
                "builder": "future-space-picture-package-v2-thin",
            }
            content_members = {}
            for label, (child_member, raw) in children.items():
                if raw:
                    content_members[label] = {"member": child_member, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                    archive.writestr(child_member, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            if content_members:
                manifest["content_members"] = content_members
            raw_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if len(raw_manifest) > SPACE_PDF_MANIFEST_MAX_BYTES:
                raise RuntimeError("Generated Space Picture manifest is too large.")
            archive.writestr(SPACE_PICTURE_MANIFEST_MEMBER, raw_manifest, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        final_manifest = validate_space_picture_package(temporary, verify_source=True, server_data_root=asset_root)
        package_hash = _file_sha256(temporary)
        os.replace(temporary, output)
        if delete_source_after_success:
            source.unlink()
        return SpacePdfPackageResult(str(output), lesson_id, document_id, source_hash, package_hash,
                                     int(output.stat().st_size), source_bytes, "verified", final_manifest,
                                     str(asset["asset_id"]))
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    finally:
        lock.unlink(missing_ok=True)


def duplicate_space_picture_as_new(source_package: str | Path, output_path: str | Path, *, title: str = "", overwrite: bool = False) -> SpacePdfPackageResult:
    package = Path(source_package)
    manifest = validate_space_picture_package(package, verify_source=True)
    temporary_source: Path | None = None
    try:
        children = {}
        with zipfile.ZipFile(package, "r") as archive:
            if manifest["source_storage"] == "embedded":
                temporary_source = Path(output_path).parent / f".spicture-source-{uuid.uuid4().hex}{Path(manifest['source_member']).suffix}"
                with temporary_source.open("wb") as handle, archive.open(manifest["source_member"], "r") as source_handle:
                    shutil.copyfileobj(source_handle, handle, length=4 * 1024 * 1024)
            else:
                temporary_source = resolve_space_picture_source_path(package, manifest)
            for label, metadata in (manifest.get("content_members") or {}).items():
                if isinstance(metadata, dict):
                    children[label] = json.loads(archive.read(str(metadata["member"])).decode("utf-8"))
        if temporary_source is None:
            raise RuntimeError("Space Picture source asset is unavailable for duplication.")
        return build_space_picture_package(temporary_source, output_path, title=title or str(manifest.get("title") or ""),
                                           owner_scope=str(manifest.get("owner_scope") or "common"),
                                           lesson_id=_stable_id("ftg-lesson-"), document_id=str(manifest["document_id"]),
                                           ai_notices=children.get("ai_notices"), ai_questions=children.get("ai_questions"),
                                           audio_markers=children.get("audio_markers"), overwrite=overwrite,
                                           server_data_root=_discover_server_data_root(package))
    finally:
        if temporary_source is not None and temporary_source.name.startswith(".spicture-source-"):
            temporary_source.unlink(missing_ok=True)
