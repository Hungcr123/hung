"""Registry prototype tests run only against a copied production database."""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import build_space_pdf_package, duplicate_space_pdf_as_new
from future_space_picture_package import build_space_picture_package
from future_space_pdf_registry import (
    deactivate_space_pdf_replica,
    initialize_space_pdf_registry_schema,
    register_space_pdf_package,
    resolve_space_pdf_lesson,
    resolve_space_pdf_package_identity,
)


BASELINE_DB = Path(r"E:\FutureServer2LegacyBackup\20260722_0600_pdf_picture_asset_schema_phase1\server2.db")


def create_pdf(path: Path, text: str) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(str(path))
    document.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="space-pdf-registry-") as folder:
        root = Path(folder)
        database = root / "server2.db"
        shutil.copy2(BASELINE_DB, database)
        connection = sqlite3.connect(database, isolation_level=None)
        connection.row_factory = sqlite3.Row
        initialize_space_pdf_registry_schema(connection)
        initialize_space_pdf_registry_schema(connection)

        source = root / "source.pdf"
        changed = root / "changed.pdf"
        create_pdf(source, "Registry prototype")
        create_pdf(changed, "Diverged source")
        package = root / "lesson.space_pdf"
        built = build_space_pdf_package(source, package, title="Registry", owner_scope="common")
        first = register_space_pdf_package(
            connection, package, "common/Registry.space_pdf", operation_id="registry-first", actor_username="admin", actor_is_admin=True
        )
        assert first["status"] == "active"
        replay = register_space_pdf_package(
            connection, package, "common/Registry.space_pdf", operation_id="registry-first", actor_username="admin", actor_is_admin=True
        )
        assert replay["idempotent"] is True
        connection.execute("UPDATE space_pdf_lesson_meta SET schema_version=1,asset_id='',asset_locator='' WHERE file_id=?", (first["file_id"],))
        connection.execute("UPDATE space_pdf_documents SET asset_id='',asset_locator='' WHERE document_id=?", (first["document_id"],))
        upgraded = register_space_pdf_package(
            connection, package, "common/Registry v2.space_pdf", operation_id="registry-v2-upgrade", actor_username="admin", actor_is_admin=True
        )
        assert upgraded["status"] == "active"
        upgraded_meta = connection.execute(
            "SELECT schema_version,asset_id,asset_locator FROM space_pdf_lesson_meta WHERE file_id=?", (first["file_id"],)
        ).fetchone()
        assert int(upgraded_meta[0]) == 2 and str(upgraded_meta[1]).startswith("ftg-asset-") and str(upgraded_meta[2]).startswith("_assets/pdf/")
        try:
            register_space_pdf_package(
                connection, package, "common/Other.space_pdf", operation_id="registry-first", actor_username="admin", actor_is_admin=True
            )
            raise AssertionError("Operation ID conflict was accepted")
        except RuntimeError as exc:
            assert "operation id" in str(exc).lower()

        replica = root / "replica.space_pdf"
        shutil.copy2(package, replica)
        second = register_space_pdf_package(
            connection, replica, "common/Registry Copy.space_pdf", operation_id="registry-copy", actor_username="admin", actor_is_admin=True
        )
        assert second["file_id"] == first["file_id"] and second["status"] == "active"

        collision_package = root / "collision.space_pdf"
        build_space_pdf_package(
            changed,
            collision_package,
            title="Registry",
            owner_scope="common",
            lesson_id=built.lesson_id,
            document_id="ftg-document-collision",
        )
        collision = register_space_pdf_package(
            connection, collision_package, "common/Registry Collision.space_pdf", operation_id="registry-collision", actor_username="admin", actor_is_admin=True
        )
        assert collision["status"] == "collision"
        assert resolve_space_pdf_lesson(connection, "common/Registry Collision.space_pdf", "hung") == {}

        duplicate = root / "independent.space_pdf"
        duplicate_result = duplicate_space_pdf_as_new(package, duplicate)
        independent = register_space_pdf_package(
            connection, duplicate, "common/Independent.space_pdf", operation_id="registry-independent", actor_username="admin", actor_is_admin=True
        )
        assert independent["file_id"] == duplicate_result.lesson_id and independent["file_id"] != first["file_id"]

        private_source = root / "private.pdf"
        private_package = root / "private.space_pdf"
        create_pdf(private_source, "Private package")
        build_space_pdf_package(private_source, private_package, owner_scope="user:hung")
        private = register_space_pdf_package(
            connection, private_package, "hung/Private.space_pdf", operation_id="registry-private", actor_username="hung"
        )
        assert private["status"] == "active"
        assert resolve_space_pdf_lesson(connection, "hung/Private.space_pdf", "hung")["file_id"] == private["file_id"]
        try:
            resolve_space_pdf_lesson(connection, "hung/Private.space_pdf", "quynh")
            raise AssertionError("Cross-user private package resolution was allowed")
        except PermissionError:
            pass

        picture_source = root / "picture.png"
        picture_package = root / "picture.space_picture"
        from PIL import Image
        Image.new("RGB", (24, 18), (80, 40, 120)).save(picture_source)
        picture_built = build_space_picture_package(picture_source, picture_package, owner_scope="user:hung")
        picture = register_space_pdf_package(
            connection, picture_package, "hung/Picture.space_picture", operation_id="registry-picture", actor_username="hung"
        )
        assert picture["file_id"] == picture_built.lesson_id and picture["status"] == "active"
        assert connection.execute("SELECT space_id FROM lesson_files WHERE file_id=?", (picture["file_id"],)).fetchone()[0] == "Space_Picture"
        assert connection.execute("SELECT space_id FROM space_pdf_lesson_meta WHERE file_id=?", (picture["file_id"],)).fetchone()[0] == "Space_Picture"

        assert deactivate_space_pdf_replica(connection, "common/Registry Copy.space_pdf") is True
        assert resolve_space_pdf_lesson(connection, "common/Registry.space_pdf", "hung")["file_id"] == first["file_id"]
        assert resolve_space_pdf_lesson(connection, "common/Registry Copy.space_pdf", "hung") == {}
        connection.execute("DELETE FROM lesson_file_aliases WHERE file_id=?", (first["file_id"],))
        connection.execute("DELETE FROM lesson_file_replicas WHERE file_id=?", (first["file_id"],))
        connection.execute("DELETE FROM space_pdf_package_replicas WHERE file_id=? AND status='active'", (first["file_id"],))
        portable_copy = root / "never-registered-location.space_pdf"
        shutil.copy2(package, portable_copy)
        direct = resolve_space_pdf_package_identity(connection, portable_copy, "hung")
        assert direct["status"] == "active" and direct["file_id"] == first["file_id"]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        counts = {
            "documents": connection.execute("SELECT COUNT(*) FROM space_pdf_documents").fetchone()[0],
            "lessons": connection.execute("SELECT COUNT(*) FROM space_pdf_lesson_meta").fetchone()[0],
            "active_replicas": connection.execute("SELECT COUNT(*) FROM space_pdf_package_replicas WHERE status='active'").fetchone()[0],
            "collisions": connection.execute("SELECT COUNT(*) FROM space_pdf_package_replicas WHERE status='collision'").fetchone()[0],
        }
        connection.close()
        assert counts == {"documents": 4, "lessons": 4, "active_replicas": 3, "collisions": 1}, counts

    print(
        "space_pdf_registry_prototype=ok schema_twice=true register=true idempotent=true replica=true "
        "operation_conflict=true collision_quarantined=true duplicate_new=true cross_user_denied=true "
        "representation_upgrade=true picture=true delete_replica=true location_cache_optional=true quick_check=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
