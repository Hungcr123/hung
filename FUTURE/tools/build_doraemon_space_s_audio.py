"""Add resumable sentence audio and word timelines to Doraemon Space_S lessons."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = Path(r"C:\server data\common\Study\Doraemon\Space S Doraemon")
REPORT_PATH = Path(r"C:\Users\Admin\.codex\plans\doraemon_space_s_audio_report.json")
AUDIO_KEYS = ("audio", "meaning_audio")


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f"{path.name}.audio-{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


# Added 2026-07-30: reject incomplete clips so resume never skips missing word timelines.
def audio_asset_complete(builder, child: dict, key: str, require_timings: bool) -> bool:
    asset = child.get(key)
    if not isinstance(asset, dict) or not clean(asset.get("url")):
        return False
    if not require_timings:
        return True
    tokens = builder.paragraph_word_tokens(child.get("text") or "")
    timings = asset.get("timings") if isinstance(asset.get("timings"), list) else []
    if not tokens or len(timings) != len(tokens):
        return False
    previous_end = 0
    for index, row in enumerate(timings):
        if not isinstance(row, dict):
            return False
        start = int(row.get("s", -1) or 0)
        end = int(row.get("e", -1) or 0)
        if int(row.get("i", index) or index) != index or start < previous_end or end <= start:
            return False
        previous_end = end
    return int(asset.get("duration_ms", 0) or 0) >= previous_end > 0


# Added 2026-07-30: validate every child before publishing an audio-bearing manifest.
def payload_audio_status(builder, payload: dict) -> tuple[bool, int, int]:
    total = 0
    complete = 0
    for node in payload.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        for child in node.get("children") or []:
            if not isinstance(child, dict):
                continue
            for key in AUDIO_KEYS:
                total += 1
                if audio_asset_complete(builder, child, key, require_timings=(key == "audio")):
                    complete += 1
    return bool(total) and complete == total, complete, total


def save_report(payload: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(REPORT_PATH, json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("FUTURE_LESSON_IDENTITY_STAGING", "1")
    os.environ.setdefault("FUTURE_BUILDER_AUDIO_PARALLEL", "4")
    sys.path.insert(0, str(ROOT))
    import future_paragraph_builder_gui as builder

    files = sorted(OUTPUT_ROOT.rglob("*.Space_S"), key=lambda path: str(path).lower())
    start_index = max(0, int(args.start_index))
    files = files[start_index:]
    if args.limit > 0:
        files = files[: args.limit]

    started = time.time()
    session_id = builder.builder_server2_build_begin("Space_S", OUTPUT_ROOT)
    results: list[dict] = []
    failures: list[dict] = []
    for offset, path in enumerate(files, start=1):
        absolute_index = start_index + offset
        try:
            payload = builder.decode_future_lesson_document(path.read_text(encoding="utf-8-sig"))
            ready, complete, total = payload_audio_status(builder, payload)
            if args.resume and ready and not args.force:
                results.append({"index": absolute_index, "path": str(path), "status": "reused", "clips": total})
                print(json.dumps(results[-1], ensure_ascii=False), flush=True)
                continue

            builder.annotate_paragraph_pos_payload(payload, force=False)
            builder.annotate_paragraph_ipa_payload(payload, force=False, log=lambda _message: None)
            for node in payload.get("nodes") or []:
                if isinstance(node, dict):
                    # Space_S uses one selected English voice per paragraph; avoid duplicate alt clips.
                    node["alt_voice"] = clean(node.get("voice"))
            if args.force:
                for node in payload.get("nodes") or []:
                    for child in node.get("children") or []:
                        if isinstance(child, dict):
                            for key in ("audio", "meaning_audio", "alt_audio"):
                                child.pop(key, None)
            warnings = builder.add_audio_to_paragraph_payload(
                payload,
                log=lambda message: print(f"[{absolute_index}/{start_index + len(files)}] {message}", flush=True),
                force_build_id=str(int(started)) if args.force else "",
            )
            ready, complete, total = payload_audio_status(builder, payload)
            if warnings or not ready:
                raise RuntimeError(f"audio incomplete {complete}/{total}; warnings={warnings[:4]}")
            manifest = builder.encode_future_manifest(payload, clean(payload.get("title")), output_path=path, space="Space_S")
            atomic_write_text(path, manifest)
            decoded = builder.decode_future_lesson_document(manifest)
            verified, verified_complete, verified_total = payload_audio_status(builder, decoded)
            if not verified:
                raise RuntimeError(f"decoded audio incomplete {verified_complete}/{verified_total}")
            results.append({"index": absolute_index, "path": str(path), "status": "built", "clips": verified_total})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        except Exception as exc:
            failure = {"index": absolute_index, "path": str(path), "error": repr(exc)}
            failures.append(failure)
            print(json.dumps(failure, ensure_ascii=False), flush=True)
        save_report({
            "started_at": started,
            "updated_at": time.time(),
            "requested": len(files),
            "completed": len(results),
            "failures": failures,
            "results": results,
        })

    builder.builder_server2_build_end(session_id, "Space_S", OUTPUT_ROOT, success=not failures)
    print(json.dumps({"requested": len(files), "completed": len(results), "failures": len(failures), "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
