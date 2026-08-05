"""Build and verify the reviewed Doraemon Space_P specs without sentence audio."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spacep_context_final")
DEFAULT_OUTPUT = Path(r"C:\server data\common\Study\Doraemon\Space P Doraemon")
DEFAULT_BUILDER = Path(
    r"C:\Users\Admin\.codex\skills\spacep-paragraph-builder\scripts\build_spacep_from_spec.py"
)


def safe_name(value: object) -> str:
    text = re.sub(r"[<>:\"/\\|?*]+", "_", str(value or ""))
    return re.sub(r"\s+", " ", text).strip(" .")


def output_name(spec: dict[str, object]) -> str:
    source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
    number = int(source.get("file_number"))
    folder = safe_name(source.get("source_folder"))
    pages = source.get("source_pages") if isinstance(source.get("source_pages"), list) else []
    page_label = ",".join(str(page) for page in pages)
    return f"File {number:03d} - {folder} - {{{page_label}}}.Space_P"


def load_skill_builder(path: Path):
    module_spec = importlib.util.spec_from_file_location("spacep_skill_builder", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Cannot load Space_P builder: {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


# 2026-07-30: Build each reviewed spec independently so failures can resume safely.
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--builder", type=Path, default=DEFAULT_BUILDER)
    args = parser.parse_args()

    specs: list[tuple[int, Path, dict[str, object]]] = []
    for path in (args.root / "workers").rglob("*.spec.json"):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        specs.append((int(source.get("file_number")), path, payload))
    specs.sort(key=lambda item: item[0])
    if [number for number, _, _ in specs] != list(range(1, 256)):
        raise SystemExit("Expected exactly one reviewed spec for every file number 1-255.")

    args.output.mkdir(parents=True, exist_ok=True)
    skill_builder = load_skill_builder(args.builder)
    builder = skill_builder.load_builder(Path(r"C:\programe\write_html"))
    rows: list[dict[str, object]] = []
    lesson_ids: set[str] = set()
    for index, (number, spec_path, spec) in enumerate(specs, 1):
        output = args.output / output_name(spec)
        payload = skill_builder.build_payload(spec)
        if hasattr(builder, "annotate_paragraph_pos_payload"):
            builder.annotate_paragraph_pos_payload(payload, force=True)
        if hasattr(builder, "add_word_audio_to_paragraph_payload"):
            builder.add_word_audio_to_paragraph_payload(payload, log=lambda _message: None)
        if not payload.get("effects"):
            payload["effects"] = builder.build_effect_sounds(lambda _message: None)
        output.write_text(
            builder.encode_future_manifest(payload, payload.get("title") or output.stem, output, "Space_P"),
            encoding="utf-8",
        )
        decoded = builder.decode_future_lesson_document(output.read_text(encoding="utf-8-sig", errors="replace"))
        stats = skill_builder.summarize(decoded)
        lesson_id = decoded.get("lesson_id") or decoded.get("lessonId") or decoded.get("lid") or ""
        if not lesson_id or lesson_id in lesson_ids:
            raise SystemExit(f"Missing or duplicate lesson_id for file {number:03d}: {lesson_id!r}")
        lesson_ids.add(lesson_id)
        if stats["audio_segments"] != 0:
            raise SystemExit(f"Unexpected sentence audio in file {number:03d}")
        expected_children = len(spec["nodes"][0]["children"])
        if stats["nodes"] != 1 or stats["segments"] != expected_children:
            raise SystemExit(f"Decoded structure mismatch for file {number:03d}")
        rows.append(
            {
                "file_number": number,
                "spec": str(spec_path),
                "output": str(output),
                "lesson_id": lesson_id,
                "segments": expected_children,
                "voice": spec.get("voice"),
                "vi_voice": spec.get("vi_voice"),
                "audio_segments": 0,
            }
        )
        if index % 10 == 0 or index == len(specs):
            print(f"progress={index}/{len(specs)} last={output.name}", flush=True)

    report = {
        "spec_root": str(args.root),
        "output_root": str(args.output),
        "built": len(rows),
        "unique_lesson_ids": len(lesson_ids),
        "audio_generated": False,
        "rows": rows,
    }
    report_path = args.root / "doraemon_spacep_build_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
