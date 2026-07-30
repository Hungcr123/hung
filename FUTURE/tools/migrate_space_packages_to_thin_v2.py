"""Stage embedded Space PDF/Picture packages as thin canonical-asset v2 packages."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import import_canonical_space_asset, validate_space_pdf_package
from future_space_picture_package import SPACE_PICTURE_SOURCE_SUFFIXES, validate_space_picture_package


SERVER_DATA_ROOT = Path(r"C:\server data")


def _source_for(package: Path) -> Path:
    if package.suffix.lower() == ".space_pdf":
        source = package.with_suffix(".pdf")
        if source.is_file():
            return source
    else:
        for suffix in sorted(SPACE_PICTURE_SOURCE_SUFFIXES):
            source = package.with_suffix(suffix)
            if source.is_file():
                return source
    raise RuntimeError(f"Legacy source asset is missing: {package}")


def _validator(package: Path):
    return validate_space_picture_package if package.suffix.lower() == ".space_picture" else validate_space_pdf_package


def _write_thin_package(source_package: Path, target_package: Path, asset: dict, staging_root: Path) -> bool:
    validator = _validator(source_package)
    before = validator(source_package, verify_source=True)
    if target_package.is_file():
        after = _validator(target_package)(target_package, verify_source=True, server_data_root=staging_root)
        for field in ("lesson_id", "document_id", "source_sha256", "source_bytes", "package_revision"):
            if after.get(field) != before.get(field):
                raise RuntimeError(f"Existing staged package differs at {field}: {target_package}")
        if after.get("asset_id") != asset["asset_id"] or after.get("asset_locator") != asset["asset_locator"]:
            raise RuntimeError(f"Existing staged package has a different canonical asset: {target_package}")
        return False

    target_package.parent.mkdir(parents=True, exist_ok=True)
    # Added 2026-07-22: short atomic names keep deep Unicode lesson folders under Windows path limits.
    temporary = target_package.parent / f".sp-{uuid.uuid4().hex}.tmp"
    try:
        with zipfile.ZipFile(source_package, "r") as old, zipfile.ZipFile(temporary, "w", allowZip64=True) as new:
            source_member = str(before.get("source_member") or "")
            for info in old.infolist():
                if info.filename in {"manifest.json", source_member}:
                    continue
                raw = old.read(info)
                replacement = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                replacement.compress_type = info.compress_type
                replacement.external_attr = info.external_attr
                replacement.comment = info.comment
                new.writestr(replacement, raw)
            manifest = dict(before)
            manifest.pop("source_member", None)
            manifest.pop("source_path", None)
            manifest["schema_version"] = 2
            manifest["source_storage"] = "canonical"
            manifest["asset_id"] = asset["asset_id"]
            manifest["asset_locator"] = asset["asset_locator"]
            manifest["builder"] = f"future-{str(manifest.get('schema') or 'space').replace('_', '-')}-package-v2-canonical-staging"
            manifest["representation_migrated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            raw_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            new.writestr("manifest.json", raw_manifest, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        after = _validator(target_package)(temporary, verify_source=True, server_data_root=staging_root)
        for field in ("lesson_id", "document_id", "source_sha256", "source_bytes", "package_revision"):
            if after.get(field) != before.get(field):
                raise RuntimeError(f"Staging conversion changed {field}: {source_package}")
        os.replace(temporary, target_package)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=SERVER_DATA_ROOT)
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    packages = sorted(
        [*source_root.rglob("*.space_pdf"), *source_root.rglob("*.space_picture")],
        key=lambda path: str(path).lower(),
    )
    discovered = []
    for package in packages:
        source = _source_for(package)
        manifest = _validator(package)(package, verify_source=True)
        discovered.append((package, source, manifest))
    baseline = {
        "packages": len(discovered),
        "pdf_packages": sum(package.suffix.lower() == ".space_pdf" for package, _, _ in discovered),
        "picture_packages": sum(package.suffix.lower() == ".space_picture" for package, _, _ in discovered),
        "source_bytes": sum(int(source.stat().st_size) for _, source, _ in discovered),
        "embedded_package_bytes": sum(int(package.stat().st_size) for package, _, _ in discovered),
    }
    if not args.apply:
        print(json.dumps(baseline, ensure_ascii=False, sort_keys=True))
        return 0
    if args.staging_root is None:
        raise RuntimeError("--staging-root is required with --apply")
    staging_root = args.staging_root.resolve()
    if staging_root == source_root or source_root in staging_root.parents:
        raise RuntimeError("Staging root must be outside live Server Data.")
    staging_root.mkdir(parents=True, exist_ok=True)

    asset_created = 0
    package_created = 0
    rows = []
    for package, source, manifest in discovered:
        kind = "pdf" if package.suffix.lower() == ".space_pdf" else "picture"
        suffixes = {".pdf"} if kind == "pdf" else SPACE_PICTURE_SOURCE_SUFFIXES
        asset = import_canonical_space_asset(source, staging_root, asset_kind=kind, allowed_suffixes=suffixes)
        asset_created += int(bool(asset["created"]))
        target = staging_root / "lessons" / package.relative_to(source_root)
        created = _write_thin_package(package, target, asset, staging_root)
        package_created += int(created)
        rows.append({
            "package": str(package.relative_to(source_root)),
            "lesson_id": manifest["lesson_id"],
            "asset_id": asset["asset_id"],
            "asset_locator": asset["asset_locator"],
            "asset_created": bool(asset["created"]),
            "package_created": created,
        })
    asset_files = [path for path in (staging_root / "_assets").rglob("*") if path.is_file() and ".incoming" not in path.parts]
    thin_packages = [*staging_root.rglob("*.space_pdf"), *staging_root.rglob("*.space_picture")]
    result = {
        **baseline,
        "asset_created": asset_created,
        "package_created": package_created,
        "canonical_asset_count": len(asset_files),
        "canonical_asset_bytes": sum(path.stat().st_size for path in asset_files),
        "thin_package_count": len(thin_packages),
        "thin_package_bytes": sum(path.stat().st_size for path in thin_packages),
        "deduplicated_assets": len(discovered) - len(asset_files),
        "rows": rows,
    }
    (staging_root / "thin_asset_staging_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
