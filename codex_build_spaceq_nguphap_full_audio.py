from __future__ import annotations

import hashlib
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, r"C:\programe\write_html")

import future_question_builder_gui as q  # noqa: E402
from future_lesson_builder_gui import (  # noqa: E402
    embedded_voice_label,
    synthesize_embedded_audio,
    write_server_sound_asset,
)


ROOT = Path(r"C:\server data\common\Ngữ pháp\Ngữ pháp")
QUESTION_VOICE = "kokoro_vi:mai_linh"
INFO_VOICE = "kokoro_vi:duc_duy"


def clean(value: object) -> str:
    return q.clean_text(value)


def clip_key(text: str, voice: str) -> tuple[str, str]:
    return clean(text), clean(voice)


def make_clip(text: str, voice: str, prefix: str) -> dict:
    audio_bytes, mime = synthesize_embedded_audio(text, voice, print)
    digest = hashlib.sha1(f"{voice}:{text}".encode("utf-8")).hexdigest()[:16]
    url = write_server_sound_asset(q.safe_segment(f"spaceq-nguphap-{prefix}-{digest}", "spaceq-audio", 120), audio_bytes, mime)
    return {
        "text": text,
        "voice": voice,
        "voice_label": embedded_voice_label(voice),
        "mime": mime,
        "url": url,
    }


def valid_audio(source: object, text: str, voice: str) -> bool:
    return isinstance(source, dict) and bool(clean(source.get("url"))) and clean(source.get("text") or source.get("audio_text")) == text and clean(source.get("voice")) == voice


def main() -> None:
    paths = sorted(ROOT.rglob("*.Space_Q"))
    if not paths:
        raise SystemExit(f"No Space_Q files under {ROOT}")

    backups: list[Path] = []
    jobs: dict[tuple[str, str], tuple[str, str, str]] = {}
    targets: dict[tuple[str, str], list[dict]] = {}
    payloads: list[tuple[Path, dict]] = []
    for path in paths:
        payload = q.decode_space_q_payload(path)
        payloads.append((path, payload))
        file_stem = q.safe_segment(path.stem, "space-q", 48)
        for node_index, node in enumerate(payload.get("nodes") or [], 1):
            cards = node.get("cards") if isinstance(node.get("cards"), dict) else {}
            node_text = clean((cards.get("root") or {}).get("text") or node.get("root"))
            if node_text:
                audio = cards.get("audio") if isinstance(cards.get("audio"), dict) else {}
                if not valid_audio(audio, node_text, INFO_VOICE):
                    audio.update({"mode": "auto", "text": node_text, "voice": INFO_VOICE, "voice_label": embedded_voice_label(INFO_VOICE)})
                    cards["audio"] = audio
                    key = clip_key(node_text, INFO_VOICE)
                    targets.setdefault(key, []).append(audio)
                    jobs.setdefault(key, (node_text, INFO_VOICE, f"{file_stem}-node{node_index}"))
            questions = cards.get("questions") if isinstance(cards.get("questions"), list) else []
            for q_index, question in enumerate(questions, 1):
                question_text = clean(question.get("question"))
                if question_text:
                    audio = question.get("audio") if isinstance(question.get("audio"), dict) else {}
                    if not valid_audio(audio, question_text, QUESTION_VOICE):
                        audio.update({"mode": "click", "text": question_text, "voice": QUESTION_VOICE, "voice_label": embedded_voice_label(QUESTION_VOICE)})
                        question["audio"] = audio
                        key = clip_key(question_text, QUESTION_VOICE)
                        targets.setdefault(key, []).append(audio)
                        jobs.setdefault(key, (question_text, QUESTION_VOICE, f"{file_stem}-node{node_index}-q{q_index}"))
                answer_info = question.get("answer_info") if isinstance(question.get("answer_info"), dict) else {}
                items = answer_info.get("items") if isinstance(answer_info.get("items"), list) else []
                if not items and clean(question.get("answer")):
                    answer = clean(question.get("answer"))
                    items = [{"text": answer, "info_text": f"Đáp án đúng là {answer}. Hãy đối chiếu chủ ngữ, cấu trúc và dạng động từ trong câu.", "mode": "audio"}]
                    answer_info["items"] = items
                    question["answer_info"] = answer_info
                for info_index, item in enumerate(items, 1):
                    if not isinstance(item, dict):
                        continue
                    info_text = clean(item.get("info_text") or item.get("info") or item.get("explanation"))
                    if not info_text:
                        continue
                    item["mode"] = "audio"
                    item["voice"] = INFO_VOICE
                    item["voice_label"] = embedded_voice_label(INFO_VOICE)
                    audio = item.get("audio") if isinstance(item.get("audio"), dict) else {}
                    if not valid_audio(audio, info_text, INFO_VOICE):
                        audio.update({"mode": "click", "text": info_text, "voice": INFO_VOICE, "voice_label": embedded_voice_label(INFO_VOICE)})
                        item["audio"] = audio
                        key = clip_key(info_text, INFO_VOICE)
                        targets.setdefault(key, []).append(audio)
                        jobs.setdefault(key, (info_text, INFO_VOICE, f"{file_stem}-node{node_index}-q{q_index}-info{info_index}"))
            node["cards"] = cards

    print(f"FILES {len(paths)} UNIQUE_AUDIO_JOBS {len(jobs)}")
    if jobs:
        with ThreadPoolExecutor(max_workers=8) as pool:
            pending = {pool.submit(make_clip, text, voice, prefix): key for key, (text, voice, prefix) in jobs.items()}
            for done, future in enumerate(as_completed(pending), 1):
                key = pending[future]
                clip = future.result()
                for target in targets[key]:
                    target.update(clip)
                if done % 50 == 0 or done == len(pending):
                    print(f"AUDIO {done}/{len(pending)}")

    for path, payload in payloads:
        backup = path.with_suffix(path.suffix + f".audio_bak_{time.strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(path, backup)
        backups.append(backup)
        path.write_text(q.encode_future_payload(payload, path, "Space_Q"), encoding="utf-8")

    print(f"WROTE {len(payloads)} FILES; BACKUPS {len(backups)}")


if __name__ == "__main__":
    main()
