"""Regression matrix for the self-contained Space PDF package prototype."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import future_space_pdf_package as package


def create_pdf(path: Path, text: str) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(str(path))
    document.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="future-space-pdf-") as folder:
        root = Path(folder)
        source = root / "source.pdf"
        create_pdf(source, "Space PDF prototype")
        built = root / "Lesson.space_pdf"
        result = package.build_space_pdf_package(
            source,
            built,
            title="Prototype",
            ai_notices=[{"notice_id": "notice-1", "text": "Read carefully"}],
            ai_questions=[{"question_id": "question-1", "prompt": "Why?"}],
            audio_markers=[{"audio_id": "audio-1", "page": 1, "audioPath": "Sound/example.mp3"}],
        )
        manifest = package.validate_space_pdf_package(built)
        assert manifest["lesson_id"] == result.lesson_id
        assert manifest["document_id"] == result.document_id
        rebuilt = package.build_space_pdf_package(
            source,
            built,
            title="Prototype rebuilt",
            ai_notices=[{"notice_id": "notice-1", "text": "Read carefully"}],
            ai_questions=[{"question_id": "question-1", "prompt": "Why?"}],
            audio_markers=[{"audio_id": "audio-1", "page": 1, "audioPath": "Sound/example.mp3"}],
            overwrite=True,
        )
        assert rebuilt.lesson_id == result.lesson_id
        assert rebuilt.document_id == result.document_id

        renamed = root / "Renamed.space_pdf"
        built.rename(renamed)
        assert package.validate_space_pdf_package(renamed)["lesson_id"] == result.lesson_id
        moved_dir = root / "moved"
        moved_dir.mkdir()
        moved = moved_dir / "Moved.space_pdf"
        renamed.rename(moved)
        shutil.copy2(source, moved_dir / source.name)
        copied = root / "Copied.space_pdf"
        shutil.copy2(moved, copied)
        assert package.compare_space_pdf_packages(moved, copied) == "replica"

        duplicate = root / "Independent.space_pdf"
        duplicate_result = package.duplicate_space_pdf_as_new(moved, duplicate)
        assert duplicate_result.lesson_id != result.lesson_id
        assert duplicate_result.document_id == result.document_id
        assert package.compare_space_pdf_packages(moved, duplicate) == "independent"
        duplicate_manifest = package.validate_space_pdf_package(duplicate)
        with zipfile.ZipFile(duplicate, "r") as archive:
            notices = json.loads(archive.read(duplicate_manifest["content_members"]["ai_notices"]["member"]))
            questions = json.loads(archive.read(duplicate_manifest["content_members"]["ai_questions"]["member"]))
            audio_markers = json.loads(archive.read(duplicate_manifest["content_members"]["audio_markers"]["member"]))
        assert notices[0]["notice_id"] == "notice-1"
        assert questions[0]["question_id"] == "question-1"
        assert audio_markers[0]["audio_id"] == "audio-1"

        changed_pdf = root / "changed.pdf"
        create_pdf(changed_pdf, "Different source")
        collision = root / "Collision.space_pdf"
        package.build_space_pdf_package(
            changed_pdf,
            collision,
            lesson_id=result.lesson_id,
            document_id="ftg-document-different",
        )
        assert package.compare_space_pdf_packages(moved, collision) == "collision"

        corrupt = root / "Corrupt.space_pdf"
        corrupt.write_bytes(moved.read_bytes()[: max(1, moved.stat().st_size // 2)])
        try:
            package.validate_space_pdf_package(corrupt)
            raise AssertionError("Incomplete package was accepted")
        except Exception:
            pass

        traversal = root / "Traversal.space_pdf"
        with zipfile.ZipFile(traversal, "w") as archive:
            archive.writestr("../manifest.json", "{}")
        try:
            package.validate_space_pdf_package(traversal)
            raise AssertionError("Traversal package was accepted")
        except Exception:
            pass

        newer = root / "Newer.space_pdf"
        newer_manifest = dict(manifest)
        newer_manifest["schema_version"] = 999
        with zipfile.ZipFile(newer, "w") as archive:
            archive.writestr("manifest.json", json.dumps(newer_manifest))
            archive.write(source, "source.pdf", compress_type=zipfile.ZIP_STORED)
        try:
            package.validate_space_pdf_package(newer)
            raise AssertionError("Newer schema package was accepted")
        except RuntimeError as exc:
            assert "newer" in str(exc).lower()

        failed_output = root / "Failed.space_pdf"
        with mock.patch.object(package, "validate_space_pdf_package", side_effect=RuntimeError("forced verify failure")):
            try:
                package.build_space_pdf_package(source, failed_output)
                raise AssertionError("Forced validation failure was ignored")
            except RuntimeError:
                pass
        assert not failed_output.exists()
        assert not list(root.glob(package._build_temp_pattern(failed_output)))

        killed_output = root / "Killed.space_pdf"
        signal_path = root / "kill-ready.txt"
        child_code = """
import sys,time
from pathlib import Path
import future_space_pdf_package as package
source,output,signal=map(Path,sys.argv[1:4])
original=package.validate_space_pdf_package
def paused(path,verify_source=True,**kwargs):
    signal.write_text('ready',encoding='utf-8')
    time.sleep(60)
    return original(path,verify_source=verify_source,**kwargs)
package.validate_space_pdf_package=paused
package.build_space_pdf_package(source,output)
"""
        child = subprocess.Popen([sys.executable, "-c", child_code, str(source), str(killed_output), str(signal_path)], cwd=ROOT)
        for _attempt in range(100):
            if signal_path.is_file():
                break
            child.poll()
            if child.returncode is not None:
                raise AssertionError(f"Hard-kill child exited early: {child.returncode}")
            import time
            time.sleep(0.05)
        assert signal_path.is_file()
        child.kill()
        child.wait(timeout=10)
        assert not killed_output.exists()
        assert list(root.glob(package._build_temp_pattern(killed_output)))
        package.build_space_pdf_package(source, killed_output)
        package.validate_space_pdf_package(killed_output)
        assert not list(root.glob(package._build_temp_pattern(killed_output)))
        assert not package._build_lock_path(killed_output).exists()

    print(
        "space_pdf_package_prototype=ok build=true rebuild_preserves_id=true verify=true rename=true move=true copy_replica=true "
        "duplicate_new=true thin_asset=true embedded_child_data=true collision=true corrupt=true traversal=true newer_schema=true "
        "atomic_cleanup=true hard_kill_recovery=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
