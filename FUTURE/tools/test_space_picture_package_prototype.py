"""Regression for atomic Space Picture build, embedded child data and Duplicate as New."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_picture_package import (
    build_space_picture_package,
    duplicate_space_picture_as_new,
    validate_space_picture_manifest_light,
    validate_space_picture_package,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ft-space-picture-") as raw:
        root = Path(raw)
        source = root / "source.png"
        Image.new("RGB", (32, 24), (20, 80, 140)).save(source)
        package = root / "lesson.space_picture"
        built = build_space_picture_package(
            source,
            package,
            title="Picture lesson",
            owner_scope="user:hung",
            ai_notices={"pages": {"1": [{"id": "notice-1"}]}},
            ai_questions={"pages": {"1": [{"id": "question-1"}]}},
            audio_markers={"pages": {"1": [{"id": "audio-1"}]}},
        )
        manifest = validate_space_picture_package(package, verify_source=True)
        assert validate_space_picture_manifest_light(package)["lesson_id"] == built.lesson_id
        with zipfile.ZipFile(package, "r") as archive:
            assert json.loads(archive.read("lesson/ai_notices.json"))["pages"]["1"][0]["id"] == "notice-1"
            assert json.loads(archive.read("lesson/ai_questions.json"))["pages"]["1"][0]["id"] == "question-1"
            assert json.loads(archive.read("lesson/audio_markers.json"))["pages"]["1"][0]["id"] == "audio-1"
        rebuilt = build_space_picture_package(
            source,
            package,
            title="Picture lesson rebuilt",
            ai_notices={"pages": {"1": [{"id": "notice-1"}]}},
            ai_questions={"pages": {"1": [{"id": "question-1"}]}},
            audio_markers={"pages": {"1": [{"id": "audio-1"}]}},
            overwrite=True,
        )
        assert rebuilt.lesson_id == built.lesson_id
        assert rebuilt.document_id == built.document_id
        duplicate = root / "duplicate.space_picture"
        copied = duplicate_space_picture_as_new(package, duplicate)
        copied_manifest = validate_space_picture_package(duplicate, verify_source=True)
        assert copied.lesson_id != built.lesson_id
        assert copied.document_id == built.document_id
        assert copied_manifest["source_sha256"] == manifest["source_sha256"]
        killed = root / "killed.space_picture"
        signal = root / "kill-ready.txt"
        child_code = """
import sys,time
from pathlib import Path
import future_space_picture_package as package
source,output,signal=map(Path,sys.argv[1:4])
original=package.validate_space_picture_package
def paused(path,verify_source=True,**kwargs):
    signal.write_text('ready',encoding='ascii')
    time.sleep(60)
    return original(path,verify_source=verify_source,**kwargs)
package.validate_space_picture_package=paused
package.build_space_picture_package(source,output)
"""
        child = subprocess.Popen([sys.executable, "-c", child_code, str(source), str(killed), str(signal)], cwd=ROOT)
        for _attempt in range(100):
            if signal.is_file():
                break
            if child.poll() is not None:
                raise AssertionError(f"Hard-kill child exited early: {child.returncode}")
            import time
            time.sleep(0.05)
        assert signal.is_file()
        child.kill()
        child.wait(timeout=10)
        assert not killed.exists()
        build_space_picture_package(source, killed)
        validate_space_picture_package(killed, verify_source=True)
        assert not list(root.glob("*.tmp")) and not list(root.glob("*.build.lock"))
    print("space_picture_package_prototype=ok build=true rebuild_preserves_id=true thin_asset=true children=true duplicate_new=true hard_kill=true cleanup=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
