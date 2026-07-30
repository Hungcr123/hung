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
    ("I exercise every morning.", "Tôi tập thể dục mỗi sáng.", "Tôi tập thể dục mỗi buổi sáng.", "Present simple: I + base verb.", "every morning"),
    ("She is healthy and strong.", "Cô ấy khỏe mạnh và mạnh mẽ.", "Cô ấy khỏe mạnh và cường tráng.", "Be adjective: She is + adjective.", "healthy and strong"),
    ("We should eat more vegetables.", "Chúng ta nên ăn nhiều rau hơn.", "Chúng ta nên ăn thêm rau.", "Modal: should + base verb.", "should eat"),
    ("My father has just finished his work.", "Bố tôi vừa mới hoàn thành công việc của ông ấy.", "Cha tôi vừa hoàn thành công việc của mình.", "Present perfect: has just + past participle.", "has just finished"),
    ("They have lived here for five years.", "Họ đã sống ở đây được năm năm.", "Họ đã sống ở đây trong năm năm.", "Present perfect with for + time.", "for five years"),
    ("Students must wear uniforms at school.", "Học sinh phải mặc đồng phục ở trường.", "Học sinh phải mặc đồng phục tại trường.", "Modal: must + base verb.", "must wear"),
    ("You should get enough sleep.", "Bạn nên ngủ đủ giấc.", "Bạn nên có đủ giấc ngủ.", "Modal advice: should + base verb.", "should get"),
    ("My grandparents tell interesting stories.", "Ông bà tôi kể những câu chuyện thú vị.", "Ông bà của tôi kể các câu chuyện thú vị.", "Present simple plural subject.", "interesting stories"),
    ("Teenagers often use smartphones.", "Thanh thiếu niên thường dùng điện thoại thông minh.", "Thanh thiếu niên thường sử dụng điện thoại thông minh.", "Frequency adverb: often before main verb.", "often use"),
    ("We respect older people.", "Chúng ta tôn trọng người lớn tuổi.", "Chúng tôi tôn trọng người già hơn.", "Present simple: We + base verb.", "older people"),
    ("Future cities will be greener.", "Các thành phố trong tương lai sẽ xanh hơn.", "Thành phố tương lai sẽ xanh hơn.", "Future simple: will be + comparative adjective.", "will be greener"),
    ("Smart cities use modern technology.", "Các thành phố thông minh sử dụng công nghệ hiện đại.", "Thành phố thông minh dùng công nghệ hiện đại.", "Present simple plural subject.", "modern technology"),
    ("The weather is becoming warmer.", "Thời tiết đang trở nên ấm hơn.", "Thời tiết đang trở nên nóng hơn.", "Present continuous: is becoming + comparative.", "is becoming warmer"),
    ("Global warming is a serious problem.", "Sự nóng lên toàn cầu là một vấn đề nghiêm trọng.", "Nóng lên toàn cầu là một vấn đề nghiêm trọng.", "Be noun phrase: subject + is + complement.", "serious problem"),
    ("Many countries are members of ASEAN.", "Nhiều quốc gia là thành viên của ASEAN.", "Nhiều nước là thành viên ASEAN.", "Plural be: countries are members.", "members of ASEAN"),
    ("Vietnam is an active member of ASEAN.", "Việt Nam là một thành viên tích cực của ASEAN.", "Việt Nam là thành viên năng động của ASEAN.", "Singular be: Vietnam is + noun phrase.", "active member"),
    ("Recycling helps protect the environment.", "Tái chế giúp bảo vệ môi trường.", "Việc tái chế giúp bảo vệ môi trường.", "Gerund as subject: Recycling helps + base verb.", "helps protect"),
    ("Walking is good for your health.", "Đi bộ tốt cho sức khỏe của bạn.", "Việc đi bộ tốt cho sức khỏe của bạn.", "Gerund as subject: Walking is + adjective.", "good for your health"),
    ("We need clean air and clean water.", "Chúng ta cần không khí sạch và nước sạch.", "Chúng tôi cần không khí sạch và nước sạch.", "Present simple: need + noun phrases.", "clean air and clean water"),
    ("Everyone should live a healthy life.", "Mọi người nên sống một cuộc sống lành mạnh.", "Ai cũng nên sống một cuộc sống khỏe mạnh.", "Modal advice: should + base verb.", "healthy life"),
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
        "Lưu ý: Đề chính giữ sát ngôi, thì, cụm từ khóa và ý người học cần gõ."
    )
    similar_a = (
        f"What does this sentence mean? -> Câu này có nghĩa là gì?\n"
        f"Can you say: {en} -> Bạn có thể nói câu này không?\n"
        f"Which phrase is important: {key}? -> Cụm nào quan trọng trong câu?\n"
        f"Who is the subject: {subject}? -> Chủ ngữ của câu là gì?\n"
        "Is this sentence useful in daily English? -> Câu này có hữu ích trong tiếng Anh hằng ngày không?"
    )
    possible_a = (
        f"{en} -> {meaning}\n"
        f"I can write: {en} -> Tôi có thể viết câu này.\n"
        f"The key phrase is {key}. -> Cụm quan trọng là {key}.\n"
        f"The subject is {subject}. -> Chủ ngữ là {subject}.\n"
        "This is a useful sentence. -> Đây là một câu hữu ích."
    )
    grammar_a = (
        f"Ngữ pháp chính: {grammar}\n"
        f"Cụm cần nhớ: {key}.\n"
        f"Chủ ngữ trong câu: {subject}.\n"
        "Khi viết lại, giữ đúng thì, động từ chính và cụm thời gian hoặc cụm danh từ.\n"
        "Lỗi thường gặp: bỏ mất s/es, nhầm be với động từ thường, hoặc quên trợ động từ khuyết thiếu."
    )
    return [
        {"q": "câu trả lời của nó có thể là gì?", "a": answer_a, "ah": highlights(key)},
        {
            "q": "Bản dịch để so sánh",
            "a": compare_a,
            "ah": highlights("Bản dịch tự nhiên dùng làm đề", "Bản dịch máy để so sánh", "Đề chính giữ sát ngôi"),
        },
        {
            "q": "5 câu hỏi nghĩa tương tự",
            "a": similar_a,
            "ah": highlights("What does this sentence mean?", "Can you say", key, "Who is the subject", "daily English"),
        },
        {
            "q": "5 câu trả lời có thể dùng",
            "a": possible_a,
            "ah": highlights(en, "I can write", key, f"The subject is {subject}", "useful sentence"),
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
        "hint": f"Gợi ý: chú ý cấu trúc {grammar} và cụm '{key}'.",
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
        title = f"Global Success Grade 11 Unit 01 Space W {part_index + 1:02d}"
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
