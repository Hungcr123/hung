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


SPACE_Q_PATH = Path(
    r"C:\server data\common\Ngữ pháp\Ngữ pháp\Thì hiện tại đơn\Bài tập\Thì hiện tại đơn - 40 bài tập phân biệt thì.Space_Q"
)
QUESTION_VOICE = "kokoro_vi:mai_linh"
INFO_VOICE = "kokoro_vi:duc_duy"

WRONG_EXPLAIN = {
    "Does she likes tea?": "Sai. Sau trợ động từ Does, động từ chính phải giữ nguyên là like, không thêm s.",
    "Do she like tea?": "Sai. She là ngôi thứ ba số ít nên phải dùng Does, không dùng Do.",
    "He does not plays football.": "Sai. Sau does not, động từ chính phải là play, không phải plays.",
    "He do not play football.": "Sai. He là ngôi thứ ba số ít nên phải dùng does not.",
    "Where Tom does live?": "Sai. Trật tự câu hỏi Wh- phải là Where does Tom live?",
    "Where does Tom lives?": "Sai. Sau does, động từ chính live không thêm s.",
    "My parents works here.": "Sai. My parents là số nhiều nên dùng work, không dùng works.",
    "My parents does work here.": "Sai. My parents là số nhiều nên không dùng does trong câu khẳng định thường.",
    "What time do the shop open?": "Sai. The shop là số ít nên trợ động từ phải là does.",
    "What time does the shop opens?": "Sai. Sau does, động từ chính open giữ nguyên, không thêm s.",
}


def clean(value: object) -> str:
    return q.clean_text(value)


def prefix_for(parts: list[object]) -> str:
    return q.safe_segment("-".join(str(part) for part in parts), "spaceq-audio", 96)


def make_clip(text: str, voice: str, mode: str, prefix: str) -> dict:
    audio_bytes, mime = synthesize_embedded_audio(clean(text), voice, print)
    asset_id = hashlib.sha1(f"{prefix}:{voice}:{clean(text)}".encode("utf-8")).hexdigest()[:16]
    url = write_server_sound_asset(prefix_for([prefix, voice, asset_id]), audio_bytes, mime)
    return {
        "mode": mode,
        "text": clean(text),
        "voice": voice,
        "voice_label": embedded_voice_label(voice),
        "mime": mime,
        "url": url,
    }


def queue_job(jobs: list[tuple], target: dict, text: str, voice: str, mode: str, prefix: str) -> None:
    if target.get("url") and target.get("voice") == voice:
        return
    jobs.append((target, text, voice, mode, prefix))


def main() -> None:
    payload = q.decode_space_q_payload(SPACE_Q_PATH)
    backup = SPACE_Q_PATH.with_suffix(SPACE_Q_PATH.suffix + f".audio_bak_{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(SPACE_Q_PATH, backup)

    jobs: list[tuple] = []
    file_stem = q.safe_segment(SPACE_Q_PATH.stem, "space-q", 48)

    for node_index, node in enumerate(payload.get("nodes", [])[2:], start=3):
        cards = node.get("cards") if isinstance(node.get("cards"), dict) else {}
        root_text = clean(node.get("root") or (cards.get("root") or {}).get("text"))
        node_audio_text = f"Phần {node_index - 2}. {root_text} Mỗi câu đều có phản hồi giải thích sau khi em trả lời."
        node_audio = cards.get("audio") if isinstance(cards.get("audio"), dict) else {}
        node_audio.update({
            "id": clean(node_audio.get("id")) or f"node-{node_index}-audio",
            "mode": "auto",
            "text": node_audio_text,
            "voice": INFO_VOICE,
            "voice_label": embedded_voice_label(INFO_VOICE),
        })
        queue_job(jobs, node_audio, node_audio_text, INFO_VOICE, "auto", f"{file_stem}-node{node_index}-intro")
        cards["audio"] = node_audio

        for question_index, question in enumerate(cards.get("questions") or [], start=1):
            question_text = clean(question.get("question"))
            q_audio_text = f"Câu {question_index}: {question_text}"
            q_audio = question.get("audio") if isinstance(question.get("audio"), dict) else {}
            q_audio.update({
                "mode": "auto",
                "text": q_audio_text,
                "voice": QUESTION_VOICE,
                "voice_label": embedded_voice_label(QUESTION_VOICE),
            })
            queue_job(jobs, q_audio, q_audio_text, QUESTION_VOICE, "auto", f"{file_stem}-node{node_index}-q{question_index}")
            question["audio"] = q_audio

            answer_info = question.get("answer_info") if isinstance(question.get("answer_info"), dict) else {}
            info_items = answer_info.get("items") if isinstance(answer_info.get("items"), list) else []
            answer = clean(question.get("answer"))
            if not info_items and answer:
                info_items = [{
                    "text": answer,
                    "info_text": f"Đáp án đúng: {answer}. Hãy kiểm tra chủ ngữ, trợ động từ do/does, và dạng nguyên mẫu của động từ chính.",
                }]
            for item in info_items:
                if not isinstance(item, dict):
                    continue
                item["mode"] = "audio"
                item["voice"] = INFO_VOICE
                item["voice_label"] = embedded_voice_label(INFO_VOICE)
                info_text = clean(item.get("info_text") or item.get("info"))
                item_audio = item.get("audio") if isinstance(item.get("audio"), dict) else {}
                item_audio.update({
                    "mode": "click",
                    "text": info_text,
                    "voice": INFO_VOICE,
                    "voice_label": embedded_voice_label(INFO_VOICE),
                })
                queue_job(
                    jobs,
                    item_audio,
                    info_text,
                    INFO_VOICE,
                    "click",
                    f"{file_stem}-node{node_index}-q{question_index}-info-{q.safe_segment(item.get('text'), 'answer', 24)}",
                )
                item["audio"] = item_audio

            existing_texts = {clean(item.get("text")) for item in info_items if isinstance(item, dict)}
            if question.get("type") == "choice":
                for wrong in question.get("wrong") or []:
                    wrong = clean(wrong)
                    if not wrong or wrong in existing_texts:
                        continue
                    info_text = WRONG_EXPLAIN.get(wrong) or (
                        f"Sai. Lựa chọn {wrong} chưa đúng với quy tắc hiện tại đơn trong câu này. Hãy nhìn lại chủ ngữ và trợ động từ."
                    )
                    item_audio = {
                        "mode": "click",
                        "text": info_text,
                        "voice": INFO_VOICE,
                        "voice_label": embedded_voice_label(INFO_VOICE),
                    }
                    item = {
                        "text": wrong,
                        "info_text": info_text,
                        "mode": "audio",
                        "voice": INFO_VOICE,
                        "voice_label": embedded_voice_label(INFO_VOICE),
                        "audio": item_audio,
                    }
                    queue_job(
                        jobs,
                        item_audio,
                        info_text,
                        INFO_VOICE,
                        "click",
                        f"{file_stem}-node{node_index}-q{question_index}-wrong-{q.safe_segment(wrong, 'wrong', 24)}",
                    )
                    info_items.append(item)
            question["answer_info"] = {"items": info_items}
        node["cards"] = cards

    print("BACKUP", backup)
    print("AUDIO_JOBS", len(jobs))
    if jobs:
        workers = max(1, min(8, len(jobs)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(make_clip, text, voice, mode, prefix): target
                for target, text, voice, mode, prefix in jobs
            }
            for done, future in enumerate(as_completed(future_map), start=1):
                target = future_map[future]
                target.update(future.result())
                if done % 20 == 0 or done == len(jobs):
                    print("DONE", done, "/", len(jobs))

    payload["created"] = int(time.time())
    SPACE_Q_PATH.write_text(q.encode_future_payload(payload, SPACE_Q_PATH, "Space_Q"), encoding="utf-8")
    print("WROTE", SPACE_Q_PATH)

    verify = q.decode_space_q_payload(SPACE_Q_PATH)
    counts = {"node_audio": 0, "q_audio": 0, "info_audio": 0, "info_type": 0, "missing_info": 0}
    for node in verify.get("nodes", []):
        cards = node.get("cards") or {}
        if (cards.get("audio") or {}).get("url"):
            counts["node_audio"] += 1
        for question in cards.get("questions") or []:
            if (question.get("audio") or {}).get("url"):
                counts["q_audio"] += 1
            items = (question.get("answer_info") or {}).get("items") or []
            if not items:
                counts["missing_info"] += 1
            for item in items:
                if (item.get("audio") or {}).get("url"):
                    counts["info_audio"] += 1
                elif item.get("mode") != "audio":
                    counts["info_type"] += 1
    print("COUNTS", counts)


if __name__ == "__main__":
    main()
