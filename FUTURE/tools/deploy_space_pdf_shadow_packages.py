"""Atomically deploy verified Space PDF packages without modifying legacy PDFs or SQLite."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import validate_space_pdf_package


def clean_path(value: object) -> str:
    return "/".join(part.strip() for part in str(value or "").replace("\\", "/").split("/") if part.strip())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    lessons = json.loads(args.mapping.read_text(encoding="utf-8"))["lessons"]
    pdf_rows = [(path, row) for path, row in sorted(lessons.items(), key=lambda item: item[0].lower()) if row.get("kind") == "pdf"]
    results = []
    for legacy_path, row in pdf_rows:
        source_pdf = args.target_root.joinpath(*clean_path(row.get("effective_path") or legacy_path).split("/"))
        source_package = args.package_root.joinpath(*clean_path(row["proposed_package_path"]).split("/"))
        target_package = args.target_root.joinpath(*clean_path(row["proposed_package_path"]).split("/"))
        if not source_pdf.is_file() or file_sha256(source_pdf) != row["source_sha256"]:
            raise RuntimeError(f"Legacy PDF changed after the frozen inventory: {legacy_path}")
        source_manifest = validate_space_pdf_package(source_package, verify_source=True)
        if source_manifest["lesson_id"] != row["lesson_id"] or source_manifest["document_id"] != row["document_id"] or source_manifest["source_sha256"] != row["source_sha256"]:
            raise RuntimeError(f"Staged package conflicts with the frozen mapping: {legacy_path}")
        status = "deployed"
        if target_package.is_file():
            target_manifest = validate_space_pdf_package(target_package, verify_source=True)
            if target_manifest["lesson_id"] != row["lesson_id"] or target_manifest["source_sha256"] != row["source_sha256"]:
                raise RuntimeError(f"Existing production package conflicts with the frozen mapping: {target_package}")
            status = "existing"
        else:
            target_package.parent.mkdir(parents=True, exist_ok=True)
            token = hashlib.sha256(str(target_package).lower().encode("utf-8")).hexdigest()[:12]
            for stale in target_package.parent.glob(f".spdf-deploy-{token}-*.tmp"):
                stale.unlink(missing_ok=True)
            temporary = target_package.parent / f".spdf-deploy-{token}-{uuid.uuid4().hex}.tmp"
            try:
                with source_package.open("rb") as source_handle, temporary.open("xb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle, length=4 * 1024 * 1024)
                    target_handle.flush()
                    os.fsync(target_handle.fileno())
                validate_space_pdf_package(temporary, verify_source=True)
                os.replace(temporary, target_package)
            finally:
                temporary.unlink(missing_ok=True)
        results.append({"legacy_path": legacy_path, "package_path": clean_path(row["proposed_package_path"]), "lesson_id": row["lesson_id"], "status": status})

    report = {
        "packages": len(results),
        "deployed": sum(row["status"] == "deployed" for row in results),
        "existing": sum(row["status"] == "existing" for row in results),
        "legacy_pdfs_preserved": sum(args.target_root.joinpath(*clean_path(row.get("effective_path") or path).split("/")).is_file() for path, row in pdf_rows),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("packages", "deployed", "existing", "legacy_pdfs_preserved")}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
