"""Build voiced Doraemon Space_W lessons from the reviewed context manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock


WRITE_HTML_DIR = Path(__file__).resolve().parents[2]
CONTEXT_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spacew_context")
DEFAULT_OUTPUT_ROOT = Path(r"C:\server data\common\Study\Doraemon\Space W Doraemon")
SETTINGS_PATH = Path(r"C:\programe\programe_cache\future_lesson_builder\builder_settings.json")

sys.path.insert(0, str(WRITE_HTML_DIR))
import future_lesson_builder_gui as builder  # noqa: E402


MAIN_VOICE = "kokoro:am_adam"
GRAMMAR_VOICE = "edge:vi-VN-NamMinhNeural"
EMBEDDED_VOICES = [
    {"label": "Sound of Text | Female US", "key": "sot:en-US"},
    {"label": "Sound of Text | Female UK", "key": "sot:en-GB"},
]
TRAIN_VOICE = "kokoro:am_adam"
TRAIN_GRAMMAR_VOICE = "edge:vi-VN-NamMinhNeural"
TRAIN_EMBEDDED_VOICES = builder.default_train_mode_embedded_voices()
PRINT_LOCK = Lock()


def load_groups(manifest_path: Path) -> tuple[list[dict], dict[Path, list[dict]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    groups = manifest.get("groups") or []
    cache: dict[Path, list[dict]] = {}
    for group in groups:
        for ref in group.get("records") or []:
            path = Path(str(ref.get("context_file") or ""))
            if path not in cache:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                cache[path] = payload if isinstance(payload, list) else payload.get("records") or []
    return groups, cache


def entries_for_group(group: dict, context_cache: dict[Path, list[dict]]) -> list[dict]:
    entries = []
    for ref in group.get("records") or []:
        path = Path(str(ref.get("context_file") or ""))
        rows = context_cache[path]
        index = int(ref.get("record_index") or 0)
        record = dict(rows[index - 1])
        if record.get("status") != "selected":
            raise RuntimeError(f"Group references non-selected record: {path}:{index}")
        entry = {
            "en": str(record.get("en") or "").strip(),
            "meaning": str(record.get("meaning") or "").strip(),
            "machine_translation": str(record.get("machine_translation") or "").strip(),
            "hint": str(record.get("hint") or "").strip(),
            "about": record.get("about") if isinstance(record.get("about"), list) else [],
        }
        if not entry["en"] or not entry["meaning"]:
            raise RuntimeError(f"Group record lacks English/meaning: {path}:{index}")
        entries.append(entry)
    if len(entries) != 5:
        raise RuntimeError(f"Expected five entries, got {len(entries)} for {group.get('group_id')}")
    return entries


def validate_payload(payload: dict, title: str, *, require_identity: bool = True) -> None:
    nodes = payload.get("n") or []
    if len(nodes) != 5:
        raise RuntimeError(f"{title}: expected 5 nodes, got {len(nodes)}")
    lesson_ids = {str(payload.get(key) or "") for key in ("lesson_id", "lessonId", "identity", "lesson")}
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    lesson_ids.update(str(meta.get(key) or "") for key in ("lesson_id", "lessonId"))
    lesson_ids.discard("")
    if require_identity and (len(lesson_ids) != 1 or not next(iter(lesson_ids), "").startswith("ftg-lesson-")):
        raise RuntimeError(f"{title}: lesson identity is missing or inconsistent: {sorted(lesson_ids)}")
    for index, node in enumerate(nodes, 1):
        if not node.get("e") or not node.get("q"):
            raise RuntimeError(f"{title}: node {index} lacks English or Vietnamese prompt")
        if not node.get("vc") or node.get("vc") == "none":
            raise RuntimeError(f"{title}: node {index} has no main voice")
        if not (node.get("av") or []) or not (node.get("vq") or []) or not (node.get("gq") or []):
            raise RuntimeError(f"{title}: node {index} lacks voiced audio/grammar audio")
        if len(node.get("ab") or []) < 5:
            raise RuntimeError(f"{title}: node {index} lacks About cards")
        for card in node.get("ab") or []:
            answer = str(card.get("a") or "")
            for highlight in card.get("ah") or []:
                term = str(highlight.get("t") or "")
                if term and term not in answer:
                    raise RuntimeError(f"{title}: node {index} has invalid About highlight {term!r}")


def build_one(group: dict, context_cache: dict[Path, list[dict]], output_root: Path, resume: bool) -> dict:
    title = str(group["future_title"])
    source_folder = str(group["source_folder"])
    output_path = output_root / source_folder / f"{title}.Space_W"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if resume and output_path.is_file():
        try:
            payload = builder.decode_future_lesson_document(output_path.read_text(encoding="utf-8-sig"))
            validate_payload(payload, title)
            return {"title": title, "path": str(output_path), "status": "reused", "lesson_id": payload.get("lesson_id")}
        except Exception:
            pass

    entries = entries_for_group(group, context_cache)

    def log(message: str) -> None:
        text = str(message or "")
        if text.startswith(("Loi", "Error", "Traceback", "Khong")):
            with PRINT_LOCK:
                print(f"[{title}] {text}", flush=True)

    payload = builder.build_lesson(
        entries,
        title,
        MAIN_VOICE,
        EMBEDDED_VOICES,
        GRAMMAR_VOICE,
        log,
        practice_voice_key=TRAIN_VOICE,
        practice_embedded_voices=TRAIN_EMBEDDED_VOICES,
        practice_grammar_voice_key=TRAIN_GRAMMAR_VOICE,
    )
    payload["source_folder"] = source_folder
    payload["source_group_id"] = str(group.get("group_id") or "")
    validate_payload(payload, title, require_identity=False)
    manifest = builder.encode_future_manifest(payload, title, output_path=output_path, space="Space_W")
    output_path.write_text(manifest, encoding="utf-8")
    decoded = builder.decode_future_lesson_document(output_path.read_text(encoding="utf-8-sig"))
    validate_payload(decoded, title)
    return {
        "title": title,
        "path": str(output_path),
        "status": "built",
        "lesson_id": decoded.get("lesson_id"),
        "nodes": len(decoded.get("n") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=CONTEXT_ROOT / "build_ready_group_manifest.json")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=int(os.environ.get("DORAEMON_BUILD_WORKERS", "2")))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    groups, context_cache = load_groups(args.manifest)
    if args.limit > 0:
        groups = groups[: args.limit]
    args.output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    failures: list[dict] = []
    worker_count = max(1, min(4, int(args.workers or 1)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(build_one, group, context_cache, args.output_root, args.resume): group for group in groups}
        for index, future in enumerate(as_completed(futures), 1):
            group = futures[future]
            try:
                result = future.result()
                results.append(result)
                if index % 10 == 0 or index == len(futures):
                    with PRINT_LOCK:
                        print(f"progress={index}/{len(futures)} last={result['title']}", flush=True)
            except Exception as exc:
                failure = {"title": group.get("future_title"), "group_id": group.get("group_id"), "error": repr(exc)}
                failures.append(failure)
                with PRINT_LOCK:
                    print(json.dumps(failure, ensure_ascii=False), flush=True)
    report = {
        "manifest": str(args.manifest),
        "output_root": str(args.output_root),
        "requested_groups": len(groups),
        "built_or_reused": len(results),
        "failures": failures,
        "voice_contract": {
            "main": MAIN_VOICE,
            "embedded": EMBEDDED_VOICES,
            "grammar": GRAMMAR_VOICE,
            "train": TRAIN_VOICE,
            "train_grammar": TRAIN_GRAMMAR_VOICE,
        },
    }
    report_path = args.report or args.output_root / "_doraemon_build_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "built_or_reused": len(results), "failures": len(failures)}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
