"""Focused canonical asset-store regression for thin PDF/Picture packages."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import build_space_pdf_package, resolve_space_pdf_source_path, validate_space_pdf_package


def _pdf(path: Path, text: str) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(str(path))
    document.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ft-canonical-assets-") as raw:
        root = Path(raw)
        server_data = root / "server_data"
        external_a = root / "outside-a"
        external_b = root / "outside-b"
        external_a.mkdir()
        external_b.mkdir()
        source_a = external_a / "book.pdf"
        source_b = external_b / "renamed-source.pdf"
        _pdf(source_a, "Canonical asset")
        shutil.copy2(source_a, source_b)
        package_a = server_data / "common" / "Book A.space_pdf"
        package_b = server_data / "common" / "Book B.space_pdf"
        first = build_space_pdf_package(source_a, package_a, server_data_root=server_data)
        second = build_space_pdf_package(source_b, package_b, server_data_root=server_data)
        assert first.asset_id == second.asset_id
        assets = [path for path in (server_data / "_assets" / "pdf").rglob("*.pdf") if path.is_file()]
        assert len(assets) == 1
        assert package_a.stat().st_size < source_a.stat().st_size
        source_a.unlink()
        source_b.rename(external_b / "source-renamed-after-import.pdf")
        manifest = validate_space_pdf_package(package_a, verify_source=True, server_data_root=server_data)
        canonical = resolve_space_pdf_source_path(package_a, manifest, server_data)
        assert canonical == assets[0].resolve()

        hidden = canonical.with_suffix(".missing-test")
        canonical.rename(hidden)
        try:
            validate_space_pdf_package(package_a, verify_source=True, server_data_root=server_data)
            raise AssertionError("Missing canonical asset was accepted")
        except RuntimeError as exc:
            assert "missing" in str(exc).lower()
        hidden.rename(canonical)

        original = canonical.read_bytes()
        canonical.write_bytes(original[:-1] + bytes([original[-1] ^ 0x01]))
        try:
            validate_space_pdf_package(package_a, verify_source=True, server_data_root=server_data)
            raise AssertionError("Corrupt canonical asset was accepted")
        except RuntimeError as exc:
            assert "fingerprint" in str(exc).lower()
        canonical.write_bytes(original)
        validate_space_pdf_package(package_b, verify_source=True, server_data_root=server_data)
        assert not list((server_data / "_assets" / ".incoming").glob("*.tmp"))
    print("space_canonical_asset_store=ok dedupe=true external_source_independent=true missing_detected=true corrupt_detected=true locator_relative=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
