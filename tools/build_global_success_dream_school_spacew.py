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
    ("My dream school is in the country.", "Ngôi trường mơ ước của tôi ở vùng quê.", "Trường mơ ước của tôi nằm ở nông thôn.", "Be + place: My dream school is in + place.", "in the country"),
    ("My dream school is very big and beautiful.", "Ngôi trường mơ ước của tôi rất lớn và đẹp.", "Trường mơ ước của tôi rất to và đẹp.", "Be + adjectives: is very big and beautiful.", "very big and beautiful"),
    ("It is an international school.", "Đó là một ngôi trường quốc tế.", "Nó là một trường quốc tế.", "Be + noun phrase: It is an + noun.", "an international school"),
    ("I want to study in a boarding school.", "Tôi muốn học ở một trường nội trú.", "Tôi muốn học trong một trường nội trú.", "Want to + base verb.", "want to study"),
    ("There is a big swimming pool in my dream school.", "Có một hồ bơi lớn trong ngôi trường mơ ước của tôi.", "Có một bể bơi lớn trong trường mơ ước của tôi.", "There is + singular noun.", "There is a big swimming pool"),
    ("My dream school has a video game room.", "Ngôi trường mơ ước của tôi có một phòng trò chơi điện tử.", "Trường mơ ước của tôi có một phòng game.", "Has + noun phrase.", "has a video game room"),
    ("There is a large greenhouse behind the classrooms.", "Có một nhà kính lớn phía sau các lớp học.", "Có một nhà kính rộng ở sau các phòng học.", "There is + noun + preposition phrase.", "behind the classrooms"),
    ("The students grow vegetables on the farm.", "Các học sinh trồng rau ở nông trại.", "Học sinh trồng rau trên nông trại.", "Present simple: plural subject + base verb.", "grow vegetables"),
    ("There are many trees around my dream school.", "Có nhiều cây xung quanh ngôi trường mơ ước của tôi.", "Có rất nhiều cây quanh trường mơ ước của tôi.", "There are + plural noun.", "There are many trees"),
    ("Every classroom has a smart TV and air conditioner.", "Mỗi lớp học có một TV thông minh và máy điều hòa.", "Mỗi phòng học có TV thông minh và điều hòa.", "Every + singular noun + has.", "Every classroom has"),
    ("The library is next to the science room.", "Thư viện ở cạnh phòng khoa học.", "Thư viện nằm bên cạnh phòng khoa học.", "Be + place phrase: is next to.", "next to the science room"),
    ("The playground is in front of the school building.", "Sân chơi ở phía trước tòa nhà trường học.", "Sân chơi nằm trước tòa nhà của trường.", "Be + place phrase: is in front of.", "in front of the school building"),
    ("There is a beautiful garden in my dream school.", "Có một khu vườn đẹp trong ngôi trường mơ ước của tôi.", "Có một khu vườn xinh đẹp trong trường mơ ước của tôi.", "There is + singular noun.", "There is a beautiful garden"),
    ("We learn English with teachers from many countries.", "Chúng tôi học tiếng Anh với giáo viên đến từ nhiều quốc gia.", "Chúng ta học tiếng Anh với giáo viên từ nhiều nước.", "Present simple: We + base verb.", "from many countries"),
    ("The students are friendly and helpful.", "Các học sinh thân thiện và hay giúp đỡ.", "Học sinh rất thân thiện và hữu ích.", "Be + adjectives: are friendly and helpful.", "friendly and helpful"),
    ("We have music and art lessons every week.", "Chúng tôi có các tiết âm nhạc và mỹ thuật mỗi tuần.", "Chúng ta có bài học âm nhạc và mỹ thuật hằng tuần.", "Present simple with frequency phrase.", "every week"),
    ("I go swimming after school every Friday.", "Tôi đi bơi sau giờ học vào mỗi thứ Sáu.", "Tôi đi bơi sau giờ học mỗi thứ Sáu.", "Go + V-ing; after school; every Friday.", "go swimming"),
    ("I love my dream school because it is modern and clean.", "Tôi yêu ngôi trường mơ ước của tôi vì nó hiện đại và sạch sẽ.", "Tôi thích trường mơ ước của mình vì nó hiện đại và sạch.", "Because clause gives a reason.", "because it is modern and clean"),
    ("My dream school has many clubs for students.", "Ngôi trường mơ ước của tôi có nhiều câu lạc bộ cho học sinh.", "Trường mơ ước của tôi có nhiều câu lạc bộ dành cho học sinh.", "Has + plural noun phrase.", "many clubs for students"),
    ("I hope I can study at my dream school one day.", "Tôi hy vọng một ngày nào đó tôi có thể học tại ngôi trường mơ ước của mình.", "Tôi hy vọng tôi có thể học ở trường mơ ước của mình một ngày nào đó.", "Hope + clause; can + base verb.", "I hope I can study"),
]


def highlights(*terms: str) -> list[dict[str, object]]:
    colors = ["#ffff00", "#7dd3fc", "#86efac", "#f9a8d4", "#fbbf24"]
    return [{"t": term, "n": 1, "c": colors[index % len(colors)]} for index, term in enumerate(terms)]


def make_about(en: str, meaning: str, machine: str, grammar: str, key: str) -> list[dict[str, object]]:
    subject = en.split(" ", 1)[0]
    answer_a = f"{en} -> {meaning}"
    compare_a = (
        f"Bản dịch tự nhiên dùng làm đề: {meaning}\n"
        f"Bản dịch máy để so sánh: {machine}\n"
        "Lưu ý: Đề chính giữ sát chủ ngữ, vị trí, từ vựng trường học và cấu trúc câu cần gõ."
    )
    similar_a = (
        "What is your dream school like? -> Trường mơ ước của bạn như thế nào?\n"
        "Where is your dream school? -> Trường mơ ước của bạn ở đâu?\n"
        f"Which phrase is important: {key}? -> Cụm nào quan trọng trong câu?\n"
        f"Who or what is the subject: {subject}? -> Chủ ngữ của câu là gì?\n"
        "Can you describe your school? -> Bạn có thể miêu tả trường của mình không?"
    )
    possible_a = (
        f"{en} -> {meaning}\n"
        f"The key phrase is {key}. -> Cụm quan trọng là {key}.\n"
        f"The subject is {subject}. -> Chủ ngữ là {subject}.\n"
        "This sentence describes a dream school. -> Câu này miêu tả một ngôi trường mơ ước.\n"
        "It is useful for Unit 1 project writing. -> Nó hữu ích cho bài viết dự án Unit 1."
    )
    grammar_a = (
        f"Ngữ pháp chính: {grammar}\n"
        f"Cụm cần nhớ: {key}.\n"
        f"Chủ ngữ trong câu: {subject}.\n"
        "Khi viết về dream school, giữ đúng danh từ trường học, vị trí và tính từ miêu tả.\n"
        "Lỗi thường gặp: quên mạo từ a/an, nhầm there is với there are, hoặc đặt sai giới từ chỉ vị trí."
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
            "ah": highlights("dream school", "Where is", key, "Who or what is the subject", "describe your school"),
        },
        {
            "q": "5 câu trả lời có thể dùng",
            "a": possible_a,
            "ah": highlights(en, key, f"The subject is {subject}", "dream school", "Unit 1 project writing"),
        },
        {
            "q": "Ngữ pháp liên quan",
            "a": grammar_a,
            "ah": highlights("Ngữ pháp chính", grammar, key, f"Chủ ngữ trong câu: {subject}", "Lỗi thường gặp"),
        },
    ]


def make_entry(item: tuple[str, str, str, str, str]) -> dict[str, object]:
    en, meaning, machine, grammar, key = item
    return {
        "en": en,
        "meaning": meaning,
        "google_translation": machine,
        "hint": f"Gợi ý: đây là câu về dream school; chú ý '{key}' và cấu trúc {grammar}",
        "about": make_about(en, meaning, machine, grammar, key),
        "practice": [],
    }


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
        title = f"Global Success Unit 01 Dream School Space W {part_index + 5:02d}"
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
