from __future__ import annotations

import json
import sys
from pathlib import Path

APP_DIR = Path(r"C:\programe\write_html")
SETTINGS_PATH = Path(r"C:\programe\programe_cache\future_lesson_builder\builder_settings.json")
OUT_DIR = Path(r"C:\server data\common\Study\Global Success\High school\Grade 11\Space_W\Unit 01")

sys.path.insert(0, str(APP_DIR))

import future_lesson_builder_gui as builder  # noqa: E402


SENTENCES: list[tuple[str, str, str, str, str]] = [
    ("Nam had unhealthy habits in the past.", "Nam đã có những thói quen không lành mạnh trong quá khứ.", "Nam từng có thói quen không lành mạnh trong quá khứ.", "Past simple: Nam had + noun phrase.", "unhealthy habits in the past"),
    ("He often ate fast food.", "Anh ấy thường ăn đồ ăn nhanh.", "Anh ấy thường ăn thức ăn nhanh.", "Past simple with frequency adverb: often + ate.", "often ate fast food"),
    ("He often stayed up late.", "Anh ấy thường thức khuya.", "Anh ấy thường ở lại muộn.", "Past simple with frequency adverb: often + stayed.", "stayed up late"),
    ("Now he eats healthy food.", "Bây giờ anh ấy ăn thức ăn lành mạnh.", "Bây giờ anh ấy ăn đồ ăn tốt cho sức khỏe.", "Present simple: he + verb-s.", "eats healthy food"),
    ("He has given up bad habits.", "Anh ấy đã từ bỏ những thói quen xấu.", "Anh ấy đã bỏ các thói quen xấu.", "Present perfect: has + past participle.", "has given up bad habits"),
    ("He has changed his lifestyle.", "Anh ấy đã thay đổi lối sống của mình.", "Anh ấy đã thay đổi phong cách sống của mình.", "Present perfect: has changed + object.", "has changed his lifestyle"),
    ("He visited his grandfather.", "Anh ấy đã thăm ông của mình.", "Anh ấy đã đến thăm ông nội của mình.", "Past simple regular verb: visited.", "visited his grandfather"),
    ("His grandfather is ninety years old.", "Ông của anh ấy chín mươi tuổi.", "Ông của anh ấy là chín mươi tuổi.", "Be + age: is ninety years old.", "ninety years old"),
    ("His grandfather exercises every day.", "Ông của anh ấy tập thể dục mỗi ngày.", "Ông của anh ấy vận động mỗi ngày.", "Present simple: singular subject + verb-s.", "exercises every day"),
    ("His grandfather goes to bed early.", "Ông của anh ấy đi ngủ sớm.", "Ông của anh ấy lên giường sớm.", "Present simple: goes to bed + adverb.", "goes to bed early"),
    ("His grandfather eats a healthy diet.", "Ông của anh ấy ăn một chế độ ăn lành mạnh.", "Ông của anh ấy có một chế độ ăn uống lành mạnh.", "Present simple: eats + noun phrase.", "a healthy diet"),
    ("Exercise is good for our health.", "Tập thể dục tốt cho sức khỏe của chúng ta.", "Việc tập luyện tốt cho sức khỏe của chúng ta.", "Gerund/noun subject + is good for.", "good for our health"),
    ("Healthy food gives us energy.", "Thức ăn lành mạnh cung cấp năng lượng cho chúng ta.", "Đồ ăn tốt cho sức khỏe cho chúng ta năng lượng.", "Present simple: singular noun subject + verb-s.", "gives us energy"),
    ("Bad habits can harm our health.", "Những thói quen xấu có thể làm hại sức khỏe của chúng ta.", "Thói quen xấu có thể gây hại cho sức khỏe của chúng ta.", "Modal: can + base verb.", "can harm our health"),
    ("A healthy diet is important.", "Một chế độ ăn lành mạnh rất quan trọng.", "Một chế độ ăn uống lành mạnh là quan trọng.", "Be + adjective: is important.", "healthy diet is important"),
    ("We should exercise every day.", "Chúng ta nên tập thể dục mỗi ngày.", "Chúng ta nên vận động hằng ngày.", "Modal advice: should + base verb.", "should exercise every day"),
    ("We should eat more vegetables.", "Chúng ta nên ăn nhiều rau hơn.", "Chúng ta nên ăn thêm rau củ.", "Modal advice: should + base verb.", "should eat more vegetables"),
    ("We should not stay up late.", "Chúng ta không nên thức khuya.", "Chúng ta không nên ở lại muộn.", "Negative modal: should not + base verb.", "should not stay up late"),
    ("I have started working out.", "Tôi đã bắt đầu tập luyện.", "Tôi đã bắt đầu tập thể dục.", "Present perfect: have started + V-ing.", "started working out"),
    ("My parents encourage me to stay healthy.", "Bố mẹ tôi khuyến khích tôi giữ gìn sức khỏe.", "Cha mẹ tôi động viên tôi duy trì sự khỏe mạnh.", "Present simple: encourage + object + to-infinitive.", "encourage me to stay healthy"),
]


# Added 2026-07-07: creates consistent highlight metadata for Health Habits Space_W about cards.
def highlights(*terms: str) -> list[dict[str, object]]:
    colors = ["#ffff00", "#7dd3fc", "#86efac", "#f9a8d4", "#fbbf24"]
    return [{"t": term, "n": 1, "c": colors[index % len(colors)]} for index, term in enumerate(terms)]


# Added 2026-07-07: builds the five learner-facing about cards for each Health Habits sentence.
def make_about(en: str, meaning: str, machine: str, grammar: str, key: str) -> list[dict[str, object]]:
    subject = en.split(" ", 1)[0]
    answer_a = f"{en} -> {meaning}"
    compare_a = (
        f"Bản dịch tự nhiên dùng làm đề: {meaning}\n"
        f"Bản dịch máy để so sánh: {machine}\n"
        "Lưu ý: Đề chính giữ sát chủ ngữ, thì, thói quen sức khỏe và cụm từ khóa người học cần gõ."
    )
    similar_a = (
        "What healthy habit does this sentence mention? -> Câu này nhắc đến thói quen lành mạnh nào?\n"
        "How can we talk about health habits? -> Chúng ta có thể nói về thói quen sức khỏe như thế nào?\n"
        f"Which phrase is important: {key}? -> Cụm nào quan trọng trong câu?\n"
        f"Who or what is the subject: {subject}? -> Chủ ngữ của câu là ai hoặc là gì?\n"
        "Is this habit good or bad for health? -> Thói quen này tốt hay xấu cho sức khỏe?"
    )
    possible_a = (
        f"{en} -> {meaning}\n"
        f"The key phrase is {key}. -> Cụm quan trọng là {key}.\n"
        f"The subject is {subject}. -> Chủ ngữ là {subject}.\n"
        "This sentence is about health habits. -> Câu này nói về thói quen sức khỏe.\n"
        "It is useful for Unit 1 health writing. -> Nó hữu ích cho bài viết Unit 1 về sức khỏe."
    )
    grammar_a = (
        f"Ngữ pháp chính: {grammar}\n"
        f"Cụm cần nhớ: {key}.\n"
        f"Chủ ngữ trong câu: {subject}.\n"
        "Khi viết về health habits, giữ đúng thì quá khứ, hiện tại đơn, hiện tại hoàn thành hoặc should theo từng câu.\n"
        "Lỗi thường gặp: quên s/es với he/she/it, dùng sai phân từ quá khứ, hoặc bỏ mất not trong lời khuyên phủ định."
    )
    return [
        {"q": "câu trả lời của nó có thể là gì?", "a": answer_a, "ah": highlights(key)},
        {
            "q": "Bản dịch để so sánh",
            "a": compare_a,
            "ah": highlights("Bản dịch tự nhiên dùng làm đề", "Bản dịch máy để so sánh", "Đề chính giữ sát chủ ngữ"),
        },
        {
            "q": "5 câu hỏi nghĩa tương tự",
            "a": similar_a,
            "ah": highlights("healthy habit", "health habits", key, "Who or what is the subject", "good or bad for health"),
        },
        {
            "q": "5 câu trả lời có thể dùng",
            "a": possible_a,
            "ah": highlights(en, key, f"The subject is {subject}", "health habits", "Unit 1 health writing"),
        },
        {
            "q": "Ngữ pháp liên quan",
            "a": grammar_a,
            "ah": highlights("Ngữ pháp chính", grammar, key, f"Chủ ngữ trong câu: {subject}", "Lỗi thường gặp"),
        },
    ]


# Added 2026-07-07: converts each Health Habits tuple into the builder entry schema.
def make_entry(item: tuple[str, str, str, str, str]) -> dict[str, object]:
    en, meaning, machine, grammar, key = item
    return {
        "en": en,
        "meaning": meaning,
        "machine_translation": machine,
        "hint": f"Gợi ý: đây là câu về health habits; chú ý '{key}' và cấu trúc {grammar}",
        "about": make_about(en, meaning, machine, grammar, key),
        "practice": [],
    }


# Added 2026-07-07: builds four five-node Space_W files with current embedded voice settings and validation output.
def main() -> None:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    selected_voice = settings["selected_voice"]
    grammar_voice = settings["grammar_voice"]
    embedded_voices = builder.resolve_embedded_voice_specs(
        settings.get("embedded_voices", []),
        settings.get("auto_groups", {}),
        print,
    )
    train_embedded_voices = builder.default_train_mode_embedded_voices()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built = []
    for part_index in range(4):
        chunk = SENTENCES[part_index * 5 : (part_index + 1) * 5]
        title = f"Global Success Grade 11 Unit 01 Health Habits Space W {part_index + 1:02d}"
        entries = [make_entry(item) for item in chunk]
        payload = builder.build_lesson(
            entries,
            title,
            selected_voice,
            embedded_voices,
            grammar_voice,
            print,
            practice_voice_key=settings.get("train_voice") or "kokoro:am_adam",
            practice_embedded_voices=train_embedded_voices,
            practice_grammar_voice_key=settings.get("train_grammar_voice") or "edge:vi-VN-NamMinhNeural",
        )
        output_path = OUT_DIR / f"{title}.Space_W"
        output_path.write_text(builder.encode_future_manifest(payload, title, output_path, "Space_W"), encoding="utf-8")
        decoded = builder.decode_future_lesson_document(output_path.read_text(encoding="utf-8-sig"))
        nodes = decoded.get("n") or []
        built.append(
            {
                "file": str(output_path),
                "nodes": len(nodes),
                "audio": [
                    {
                        "e": node.get("e"),
                        "vc": node.get("vc"),
                        "av": len(node.get("av") or []),
                        "vq": len(node.get("vq") or []),
                        "gq": len(node.get("gq") or []),
                        "ab": len(node.get("ab") or []),
                    }
                    for node in nodes
                ],
            }
        )

    print(json.dumps({"built": built}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
