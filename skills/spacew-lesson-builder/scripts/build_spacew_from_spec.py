from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_WRITE_HTML_DIR = Path(r"C:\programe\write_html")


def load_builder(write_html_dir: Path):
    sys.path.insert(0, str(write_html_dir))
    import future_lesson_builder_gui as lesson_builder  # type: ignore

    return lesson_builder


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def exact_phrase(text: str, phrase: str) -> str:
    source = str(text or "")
    target = clean_text(phrase)
    if not source or not target:
        return ""
    index = source.lower().find(target.lower())
    if index < 0:
        return ""
    return source[index:index + len(target)]


def occurrence_number(answer: str, term: str, absolute_index: int) -> int:
    if absolute_index < 0:
        return 1
    count = 0
    cursor = 0
    while True:
        found = answer.find(term, cursor)
        if found < 0 or found > absolute_index:
            break
        count += 1
        cursor = found + max(len(term), 1)
    return max(count, 1)


def normalize_highlights(card: dict) -> dict:
    answer = str(card.get("a") or card.get("answer") or "")
    highlights = card.get("ah") or card.get("highlights") or card.get("answer_highlights") or []
    terms = card.get("highlight_terms") or []
    colors = ["#ffff00", "#7dd3fc", "#86efac", "#f9a8d4", "#fbbf24"]
    if not isinstance(highlights, list):
        highlights = []
    else:
        highlights = list(highlights)
    seen = {clean_text(item.get("t")) for item in highlights if isinstance(item, dict)}
    if isinstance(terms, list):
        for term in terms:
            text = exact_phrase(answer, str(term or ""))
            if text and text not in seen:
                absolute_index = answer.find(text)
                highlights.append({
                    "t": text,
                    "n": occurrence_number(answer, text, absolute_index),
                    "c": colors[len(highlights) % len(colors)],
                })
                seen.add(text)
    out = dict(card)
    if highlights:
        out["ah"] = highlights
    return out


def translation_comparison_card(entry: dict) -> dict | None:
    natural = clean_text(entry.get("meaning") or entry.get("vi") or entry.get("mn") or entry.get("q"))
    google = clean_text(
        entry.get("google_translation")
        or entry.get("googleTranslation")
        or entry.get("machine_translation")
        or entry.get("machineTranslation")
    )
    if not natural or not google:
        return None
    return normalize_highlights({
        "q": "Bản dịch để so sánh",
        "a": (
            f"Bản dịch tự nhiên dùng làm đề: {natural}\n"
            f"Bản dịch Google để so sánh: {google}\n"
            "Lưu ý: Đề chính được viết sát với câu người học cần gõ, giữ đúng ngôi, thì, ý chính và cách nói tự nhiên."
        ),
        "highlight_terms": [
            "Bản dịch tự nhiên dùng làm đề",
            "Bản dịch Google để so sánh",
            "Đề chính được viết sát với câu người học cần gõ",
            "giữ đúng ngôi, thì, ý chính",
            "cách nói tự nhiên",
        ],
    })


def normalize_entries(entries: list[dict]) -> list[dict]:
    out = []
    for entry in entries:
        item = dict(entry)
        about = item.get("about") or []
        if isinstance(about, list):
            item["about"] = [normalize_highlights(card) if isinstance(card, dict) else card for card in about]
        practice = (
            item.get("practice")
            or item.get("extra_practice")
            or item.get("extraPractice")
            or item.get("supplemental")
            or item.get("xp")
            or []
        )
        if isinstance(practice, list):
            normalized_practice = []
            for practice_entry in practice:
                if not isinstance(practice_entry, dict):
                    normalized_practice.append(practice_entry)
                    continue
                practice_item = dict(practice_entry)
                practice_about = practice_item.get("about") or []
                if isinstance(practice_about, list):
                    practice_item["about"] = [
                        normalize_highlights(card) if isinstance(card, dict) else card
                        for card in practice_about
                    ]
                normalized_practice.append(practice_item)
            item["practice"] = normalized_practice
        comparison = translation_comparison_card(item)
        if comparison and isinstance(item.get("about"), list):
            if not any(
                isinstance(card, dict) and "bản dịch" in clean_text(card.get("q")).lower()
                for card in item["about"]
            ):
                item["about"].insert(1, comparison)
        out.append(item)
    return out


def load_voice_settings(lesson_builder, settings_path: Path, log):
    data = {}
    if settings_path.is_file():
        data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    selected_voice = lesson_builder.clean_text(data.get("selected_voice")) or "sot:en-US"
    grammar_voice = lesson_builder.clean_text(data.get("grammar_voice")) or "edge:vi-VN-NamMinhNeural"
    train_voice = lesson_builder.clean_text(data.get("train_voice")) or lesson_builder.TRAIN_MODE_PRIMARY_VOICE
    train_grammar_voice = lesson_builder.clean_text(data.get("train_grammar_voice")) or lesson_builder.TRAIN_MODE_VIETNAMESE_VOICE
    embedded_voices = data.get("embedded_voices") if isinstance(data.get("embedded_voices"), list) else []
    train_embedded_voices = (
        data.get("train_embedded_voices")
        if isinstance(data.get("train_embedded_voices"), list)
        else lesson_builder.default_train_mode_embedded_voices()
    )
    auto_groups = data.get("auto_groups") if isinstance(data.get("auto_groups"), dict) else {
        "sot": True,
        "edge": False,
        "microsoft": False,
        "people": False,
    }
    selected_voice = lesson_builder.normalize_audio_voice_key(selected_voice) or "sot:en-US"
    grammar_voice = lesson_builder.normalize_audio_voice_key(grammar_voice) or "edge:vi-VN-NamMinhNeural"
    train_voice = lesson_builder.normalize_audio_voice_key(train_voice) or lesson_builder.TRAIN_MODE_PRIMARY_VOICE
    train_grammar_voice = lesson_builder.normalize_audio_voice_key(train_grammar_voice) or lesson_builder.TRAIN_MODE_VIETNAMESE_VOICE
    embedded = lesson_builder.resolve_embedded_voice_specs(embedded_voices, auto_groups, log)
    train_embedded = lesson_builder.resolve_embedded_voice_specs(train_embedded_voices, {}, log)
    if not train_embedded:
        train_embedded = lesson_builder.default_train_mode_embedded_voices()
    return selected_voice, embedded, grammar_voice, train_voice, train_embedded, train_grammar_voice


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--write-html-dir", type=Path, default=DEFAULT_WRITE_HTML_DIR)
    parser.add_argument("--settings", type=Path)
    args = parser.parse_args()

    lesson_builder = load_builder(args.write_html_dir)
    settings_path = args.settings or lesson_builder.BUILDER_SETTINGS_PATH

    def log(message: str) -> None:
        text = str(message or "")
        if text.startswith(("Node ", "Phan tich:", "Tao audio:", "Audio cache:", "Nhung audio")):
            print(text)

    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    title = lesson_builder.clean_text(spec.get("title")) or "Future lesson"
    entries = normalize_entries(spec.get("entries") or spec.get("nodes") or [])
    if not entries:
        raise SystemExit("Spec has no entries.")

    selected_voice, embedded_voices, grammar_voice, train_voice, train_embedded_voices, train_grammar_voice = load_voice_settings(lesson_builder, settings_path, log)
    payload = lesson_builder.build_lesson(
        entries,
        title,
        selected_voice,
        embedded_voices,
        grammar_voice,
        log,
        practice_voice_key=train_voice,
        practice_embedded_voices=train_embedded_voices,
        practice_grammar_voice_key=train_grammar_voice,
    )
    manifest = lesson_builder.encode_future_manifest(payload, title)
    out_path = args.out or (args.write_html_dir / f"{title}.Space_W")
    out_path.write_text(manifest, encoding="utf-8")

    decoded = lesson_builder.decode_future_lesson_document(out_path.read_text(encoding="utf-8-sig"))
    nodes = decoded.get("n", [])
    bad = [
        (i, len(node.get("av") or []), len(node.get("vq") or []), len(node.get("gq") or []))
        for i, node in enumerate(nodes, 1)
        if not node.get("vc") or not (node.get("av") or []) or not (node.get("vq") or []) or not (node.get("gq") or [])
    ]
    bad_practice = []
    for i, node in enumerate(nodes, 1):
        practice_nodes = node.get("xp") or []
        if not isinstance(practice_nodes, list):
            bad_practice.append((i, "xp_not_list", type(practice_nodes).__name__))
            continue
        for j, practice_node in enumerate(practice_nodes, 1):
            if not isinstance(practice_node, dict):
                bad_practice.append((i, j, "not_object"))
                continue
            if not practice_node.get("e") or not practice_node.get("q"):
                bad_practice.append((i, j, "missing_prompt_or_sentence"))
            if not (practice_node.get("av") or []) or not (practice_node.get("vq") or []) or not (practice_node.get("gq") or []):
                bad_practice.append((
                    i,
                    j,
                    "bad_audio",
                    len(practice_node.get("av") or []),
                    len(practice_node.get("vq") or []),
                    len(practice_node.get("gq") or []),
                ))
            if not (practice_node.get("tk") or []) or not (practice_node.get("sc") or []):
                bad_practice.append((i, j, "missing_analysis_or_scoring"))
    bad_about = []
    for i, node in enumerate(nodes, 1):
        about = node.get("ab") or []
        if len(about) < 5:
            bad_about.append((i, "about_cards", len(about)))
        required = [
            ("câu trả lời", 1),
            ("bản dịch", 2),
            ("5 câu hỏi", 5),
            ("5 câu trả lời", 5),
            ("ngữ pháp", 5),
        ]
        for title_part, minimum in required:
            matching = [
                card for card in about
                if isinstance(card, dict) and title_part in clean_text(card.get("q")).lower()
            ]
            if not matching:
                bad_about.append((i, f"missing_{title_part}", 0))
                continue
            count = len(matching[0].get("ah") or [])
            if count < minimum:
                bad_about.append((i, f"{title_part}_highlights", count))
        for card_no, card in enumerate(about, 1):
            answer = str((card or {}).get("a") or "")
            title = clean_text((card or {}).get("q")).lower()
            for highlight in (card or {}).get("ah") or []:
                text = clean_text((highlight or {}).get("t"))
                if text and text not in answer:
                    bad_about.append((i, f"card_{card_no}_missing_highlight_text", text))
            if "câu trả lời" in title or "5 câu hỏi" in title or "5 câu trả lời" in title:
                highlights = [
                    clean_text((highlight or {}).get("t"))
                    for highlight in (card or {}).get("ah") or []
                    if clean_text((highlight or {}).get("t"))
                ]
                for line in answer.splitlines():
                    sample = clean_text(line)
                    if not sample:
                        continue
                    if " -> " not in sample:
                        bad_about.append((i, f"card_{card_no}_missing_example_translation", sample))
                    else:
                        left, right = sample.split(" -> ", 1)
                        if not clean_text(left) or not clean_text(right):
                            bad_about.append((i, f"card_{card_no}_bad_example_translation", sample))
                    if sample in highlights:
                        bad_about.append((i, f"card_{card_no}_full_line_highlight", sample))
                    if not any(text in sample and text != sample for text in highlights):
                        bad_about.append((i, f"card_{card_no}_line_without_phrase_highlight", sample))
    print(json.dumps({
        "output": str(out_path),
        "title": decoded.get("t"),
        "nodes": len(nodes),
        "voice": nodes[0].get("vc") if nodes else "",
        "grammar_voice": decoded.get("gv"),
        "train_voice": (decoded.get("xv") or {}).get("vc") if isinstance(decoded.get("xv"), dict) else "",
        "train_grammar_voice": (decoded.get("xv") or {}).get("gv") if isinstance(decoded.get("xv"), dict) else "",
        "bad_audio_nodes": bad,
        "bad_practice_nodes": bad_practice,
        "bad_about_nodes": bad_about,
    }, ensure_ascii=False, indent=2))
    return 1 if bad or bad_practice or bad_about else 0


if __name__ == "__main__":
    raise SystemExit(main())
