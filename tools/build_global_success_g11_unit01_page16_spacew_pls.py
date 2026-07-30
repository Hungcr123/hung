from __future__ import annotations

import json
import sys
import time
from pathlib import Path

APP_DIR = Path(r"C:\programe\write_html")
SETTINGS_PATH = Path(r"C:\programe\programe_cache\future_lesson_builder\builder_settings.json")
BASE_DIR = Path(r"C:\server data\common\Study\Global Success\High school\Grade 11")
OUT_W = BASE_DIR / "Space_W" / "Unit 01"
OUT_P = BASE_DIR / "Space_P" / "Unit 01"
OUT_S = BASE_DIR / "Space_S" / "Unit 01"
OUT_L = BASE_DIR / "Space_L" / "Unit 01"

sys.path.insert(0, str(APP_DIR))

import future_lesson_builder_gui as wbuilder  # noqa: E402
import future_paragraph_builder_gui as pbuilder  # noqa: E402


W_SENTENCES = [
    ("Thank you for your invitation.", "Cảm ơn bạn vì lời mời.", "Thank you for + noun.", "your invitation"),
    ("I am happy to accept your invitation.", "Tôi rất vui được nhận lời mời của bạn.", "Be happy to + base verb.", "accept your invitation"),
    ("I would love to join you.", "Tôi rất muốn tham gia cùng bạn.", "Would love to + base verb.", "would love to join"),
    ("I can come this Saturday.", "Tôi có thể đến vào thứ Bảy này.", "Can + base verb.", "this Saturday"),
    ("What time should I come?", "Tôi nên đến lúc mấy giờ?", "What time + should + subject + verb?", "What time should I"),
    ("What time shall we meet?", "Chúng ta sẽ gặp nhau lúc mấy giờ?", "What time + shall we + verb?", "shall we meet"),
    ("Shall we meet at seven?", "Chúng ta gặp nhau lúc bảy giờ nhé?", "Shall we + base verb?", "at seven"),
    ("I will arrive on time.", "Tôi sẽ đến đúng giờ.", "Will + base verb.", "on time"),
    ("Do I need to bring anything?", "Tôi có cần mang gì không?", "Do + subject + need to + verb?", "need to bring"),
    ("Should I buy some fruit?", "Tôi có nên mua một ít trái cây không?", "Should + subject + base verb?", "some fruit"),
    ("Can I bring some drinks?", "Tôi có thể mang một ít đồ uống không?", "Can + subject + base verb?", "some drinks"),
    ("I can help prepare the food.", "Tôi có thể giúp chuẩn bị đồ ăn.", "Can help + base verb.", "help prepare"),
    ("I look forward to seeing you.", "Tôi mong được gặp bạn.", "Look forward to + V-ing.", "seeing you"),
    ("Thank you for inviting me.", "Cảm ơn bạn đã mời tôi.", "Thank you for + V-ing.", "inviting me"),
    ("I can't wait to see everyone.", "Tôi rất nóng lòng được gặp mọi người.", "Can't wait to + base verb.", "see everyone"),
    ("Can I help you?", "Tôi có thể giúp bạn không?", "Can I + base verb?", "help you"),
    ("Can I help you with that?", "Tôi có thể giúp bạn việc đó không?", "Help somebody with something.", "with that"),
    ("Can I give you a hand?", "Tôi có thể giúp bạn một tay không?", "Give somebody a hand.", "give you a hand"),
    ("Let me help you.", "Để tôi giúp bạn.", "Let me + base verb.", "Let me help"),
    ("Let me help you with this machine.", "Để tôi giúp bạn với cái máy này.", "Let me + base verb + object.", "this machine"),
    ("Is there anything else I can do for you?", "Còn điều gì khác tôi có thể làm cho bạn không?", "Is there anything else + clause?", "anything else"),
    ("Please let me show you.", "Xin hãy để tôi chỉ cho bạn.", "Please let me + base verb.", "show you"),
    ("I can show you how.", "Tôi có thể chỉ cho bạn cách làm.", "Show somebody how.", "show you how"),
    ("Just press this button.", "Chỉ cần nhấn nút này.", "Imperative sentence.", "press this button"),
    ("Now it is working.", "Bây giờ nó đang hoạt động.", "Present continuous: is working.", "is working"),
    ("Thank you very much.", "Cảm ơn bạn rất nhiều.", "Polite thanks.", "very much"),
    ("Thanks for your help.", "Cảm ơn sự giúp đỡ của bạn.", "Thanks for + noun.", "your help"),
    ("That's very kind of you.", "Bạn thật tốt bụng.", "That's very kind of you.", "kind of you"),
    ("That's very nice of you.", "Bạn thật tốt.", "That's very nice of you.", "nice of you"),
    ("Thanks, but I think I'm fine.", "Cảm ơn, nhưng tôi nghĩ tôi ổn.", "Thanks, but + clause.", "I'm fine"),
    ("I can do it now.", "Bây giờ tôi có thể làm được.", "Can + base verb.", "do it now"),
    ("Everything is working well now.", "Bây giờ mọi thứ đang hoạt động tốt.", "Present continuous: is working.", "working well now"),
    ("I understand it now.", "Bây giờ tôi hiểu rồi.", "Present simple: understand.", "understand it"),
    ("I really appreciate your help.", "Tôi thật sự biết ơn sự giúp đỡ của bạn.", "Appreciate + noun.", "appreciate your help"),
    ("Thank you for helping me.", "Cảm ơn bạn đã giúp tôi.", "Thank you for + V-ing.", "helping me"),
    ("I want to change the speed.", "Tôi muốn thay đổi tốc độ.", "Want to + base verb.", "change the speed"),
    ("This treadmill is easy to use.", "Máy chạy bộ này dễ sử dụng.", "Be + adjective + to-infinitive.", "easy to use"),
    ("The trainer shows me how.", "Huấn luyện viên chỉ cho tôi cách làm.", "Show somebody how.", "shows me how"),
    ("I enjoy my workout every morning.", "Tôi thích buổi tập của mình mỗi sáng.", "Enjoy + noun.", "every morning"),
    ("Exercise keeps me healthy.", "Tập thể dục giúp tôi khỏe mạnh.", "Subject + keeps + object + adjective.", "keeps me healthy"),
    ("I work out three times a week.", "Tôi tập luyện ba lần một tuần.", "Work out + frequency phrase.", "three times a week"),
    ("I always warm up first.", "Tôi luôn khởi động trước.", "Frequency adverb before verb.", "warm up first"),
    ("Regular exercise gives me more energy.", "Tập thể dục đều đặn cho tôi nhiều năng lượng hơn.", "Subject + gives + object + noun.", "more energy"),
    ("I feel stronger after my workout.", "Tôi cảm thấy khỏe hơn sau buổi tập.", "Feel + comparative adjective.", "after my workout"),
    ("I enjoy exercising with my friends.", "Tôi thích tập thể dục cùng bạn bè.", "Enjoy + V-ing.", "exercising with my friends"),
    ("My family eats healthy food.", "Gia đình tôi ăn thức ăn lành mạnh.", "Present simple third-person singular.", "healthy food"),
    ("We buy fresh vegetables every week.", "Chúng tôi mua rau tươi mỗi tuần.", "Present simple + time phrase.", "fresh vegetables"),
    ("Fruit is good for our health.", "Trái cây tốt cho sức khỏe của chúng ta.", "Be good for + noun.", "good for our health"),
    ("Healthy meals give us energy.", "Những bữa ăn lành mạnh cho chúng ta năng lượng.", "Plural subject + base verb.", "give us energy"),
    ("A healthy diet helps us stay fit.", "Một chế độ ăn lành mạnh giúp chúng ta giữ dáng.", "Help + object + base verb.", "stay fit"),
    ("We should eat less fast food.", "Chúng ta nên ăn ít đồ ăn nhanh hơn.", "Should + base verb.", "less fast food"),
    ("Drinking enough water is important.", "Uống đủ nước là điều quan trọng.", "Gerund as subject.", "Drinking enough water"),
    ("Healthy habits improve our lives.", "Những thói quen lành mạnh cải thiện cuộc sống của chúng ta.", "Plural subject + base verb.", "improve our lives"),
    ("I want to live a healthy life.", "Tôi muốn sống một cuộc sống lành mạnh.", "Want to + base verb.", "healthy life"),
    ("My parents encourage healthy eating.", "Bố mẹ tôi khuyến khích việc ăn uống lành mạnh.", "Encourage + noun phrase.", "healthy eating"),
]


PARAGRAPH_CHILDREN = [
    ("Last Saturday, my friend invited me to a small party after our workout at the gym.", "Thứ Bảy tuần trước, bạn tôi mời tôi đến một bữa tiệc nhỏ sau buổi tập ở phòng gym."),
    ("I was happy to accept the invitation because I wanted to see everyone.", "Tôi rất vui nhận lời mời vì tôi muốn gặp mọi người."),
    ("Before I went there, I asked what time we should meet and whether I needed to bring anything.", "Trước khi đến đó, tôi hỏi chúng tôi nên gặp lúc mấy giờ và tôi có cần mang gì không."),
    ("My friend told me to come at seven and said I could bring some fruit and drinks.", "Bạn tôi bảo tôi đến lúc bảy giờ và nói tôi có thể mang một ít trái cây và đồ uống."),
    ("At the gym, a new treadmill was difficult for me to use, so a trainer gave me a hand.", "Ở phòng gym, một máy chạy bộ mới hơi khó dùng với tôi, vì vậy một huấn luyện viên đã giúp tôi."),
    ("He showed me how to change the speed and told me to warm up first.", "Anh ấy chỉ cho tôi cách thay đổi tốc độ và bảo tôi khởi động trước."),
    ("I thanked him because his help was very kind and useful.", "Tôi cảm ơn anh ấy vì sự giúp đỡ đó rất tử tế và hữu ích."),
    ("Now I work out three times a week, eat healthy meals, and drink enough water.", "Bây giờ tôi tập luyện ba lần một tuần, ăn các bữa ăn lành mạnh và uống đủ nước."),
    ("Regular exercise gives me more energy and helps me feel stronger after every workout.", "Tập thể dục đều đặn cho tôi nhiều năng lượng hơn và giúp tôi cảm thấy khỏe hơn sau mỗi buổi tập."),
    ("My parents encourage healthy eating, so my family buys fresh vegetables and less fast food.", "Bố mẹ tôi khuyến khích ăn uống lành mạnh, nên gia đình tôi mua rau tươi và ít đồ ăn nhanh hơn."),
    ("I think healthy habits are important because they improve our lives and help us stay fit.", "Tôi nghĩ những thói quen lành mạnh rất quan trọng vì chúng cải thiện cuộc sống và giúp chúng ta giữ dáng."),
]


def highlights(*terms: str) -> list[dict[str, object]]:
    colors = ["#ffff00", "#7dd3fc", "#86efac", "#f9a8d4", "#fbbf24"]
    return [{"t": term, "n": 1, "c": colors[i % len(colors)]} for i, term in enumerate(terms)]


def about_for_w(en: str, meaning: str, grammar: str, key: str) -> list[dict[str, object]]:
    subject = en.split(" ", 1)[0]
    return [
        {"q": "câu trả lời của nó có thể là gì?", "a": f"{en} -> {meaning}", "ah": highlights(key)},
        {"q": "Bản dịch để so sánh", "a": f"Bản dịch tự nhiên dùng làm đề: {meaning}\nBản dịch máy để so sánh: {meaning}\nLưu ý: Đề chính giữ sát mẫu câu giao tiếp, lời mời, giúp đỡ và lối sống lành mạnh.", "ah": highlights("Bản dịch tự nhiên dùng làm đề", "Bản dịch máy để so sánh", "mẫu câu giao tiếp")},
        {"q": "5 câu hỏi nghĩa tương tự", "a": f"What does this sentence mean? -> Câu này có nghĩa là gì?\nCan you use the phrase {key}? -> Bạn có thể dùng cụm này không?\nWho is the subject: {subject}? -> Chủ ngữ của câu là gì?\nIs this sentence polite? -> Câu này có lịch sự không?\nCan you say it in real life? -> Bạn có thể nói câu này ngoài đời không?", "ah": highlights("What does this sentence mean?", key, f"Who is the subject: {subject}", "polite", "real life")},
        {"q": "5 câu trả lời có thể dùng", "a": f"{en} -> {meaning}\nThe key phrase is {key}. -> Cụm quan trọng là {key}.\nThe subject is {subject}. -> Chủ ngữ là {subject}.\nThis is useful in daily English. -> Câu này hữu ích trong tiếng Anh hằng ngày.\nIt matches Unit 1 page 16. -> Câu này phù hợp Unit 1 trang 16.", "ah": highlights(en, key, f"The subject is {subject}", "daily English", "Unit 1 page 16")},
        {"q": "Ngữ pháp liên quan", "a": f"Ngữ pháp chính: {grammar}\nCụm cần nhớ: {key}.\nChủ ngữ trong câu: {subject}.\nKhi viết lại, giữ đúng trợ động từ, cụm lịch sự và cụm chỉ sức khỏe.\nLỗi thường gặp: quên to sau want/love, nhầm should với can, hoặc bỏ mất giới từ.", "ah": highlights("Ngữ pháp chính", grammar, key, f"Chủ ngữ trong câu: {subject}", "Lỗi thường gặp")},
    ]


def make_w_entry(item: tuple[str, str, str, str]) -> dict[str, object]:
    en, meaning, grammar, key = item
    return {
        "en": en,
        "meaning": meaning,
        "hint": f"Gợi ý: chú ý '{key}' và mẫu {grammar}",
        "about": about_for_w(en, meaning, grammar, key),
        "practice": [],
    }


def build_space_w(settings: dict) -> list[dict]:
    selected_voice = settings["selected_voice"]
    grammar_voice = settings["grammar_voice"]
    embedded_voices = wbuilder.resolve_embedded_voice_specs(settings.get("embedded_voices", []), settings.get("auto_groups", {}), print)
    train_embedded_voices = wbuilder.default_train_mode_embedded_voices()
    OUT_W.mkdir(parents=True, exist_ok=True)
    built = []
    for part_index in range(0, len(W_SENTENCES), 5):
        chunk = W_SENTENCES[part_index : part_index + 5]
        number = part_index // 5 + 1
        title = f"Global Success Grade 11 Unit 01 Page 16 Space W {number:02d}"
        payload = wbuilder.build_lesson(
            [make_w_entry(item) for item in chunk],
            title,
            selected_voice,
            embedded_voices,
            grammar_voice,
            print,
            practice_voice_key=settings.get("train_voice") or "kokoro:am_adam",
            practice_embedded_voices=train_embedded_voices,
            practice_grammar_voice_key=settings.get("train_grammar_voice") or "edge:vi-VN-NamMinhNeural",
        )
        output = OUT_W / f"{title}.Space_W"
        output.write_text(wbuilder.encode_future_manifest(payload, title, output, "Space_W"), encoding="utf-8")
        decoded = wbuilder.decode_future_lesson_document(output.read_text(encoding="utf-8-sig"))
        nodes = decoded.get("n") or []
        built.append({"file": str(output), "nodes": len(nodes), "audio": [(len(n.get("av") or []), len(n.get("vq") or []), len(n.get("gq") or []), len(n.get("ab") or [])) for n in nodes]})
    return built


def child_guides(en: str, vi: str) -> list[dict[str, str]]:
    return [
        {"title": "Ý nghĩa", "text": vi},
        {"title": "Cấu trúc", "text": "Chú ý mẫu câu lớp 11 về lời mời, đề nghị giúp đỡ, tập luyện và lối sống lành mạnh."},
        {"title": "Từ vựng", "text": "Ghi nhớ các cụm: invitation, give me a hand, treadmill, warm up, work out, healthy habits."},
    ]


def paragraph_payload(title: str, mode: str) -> dict:
    children = [
        {
            "id": f"child-{i:03d}",
            "text": en,
            "meaning": vi,
            "explanations": child_guides(en, vi),
        }
        for i, (en, vi) in enumerate(PARAGRAPH_CHILDREN, start=1)
    ]
    return {
        "k": "ftp",
        "kind": "future_paragraph_payload",
        "space_mode": mode,
        "format": "Space_L" if mode == "space_l" else ("Space_S" if mode == "space_s" else "Space_P"),
        "version": 1,
        "title": title,
        "hint_seconds": 30,
        "effects": {},
        "nodes": [
            {
                "id": "pnode-001",
                "title": "Healthy Lifestyle Paragraph",
                "text": " ".join(en for en, _vi in PARAGRAPH_CHILDREN),
                "voice": "kokoro:am_adam",
                "vi_voice": "edge:vi-VN-NamMinhNeural",
                "alt_voice": "sot:en-GB" if mode in {"space_s", "space_l"} else "kokoro:af_jessica",
                "children": children,
            }
        ],
        "created": int(time.time()),
    }


def build_paragraph_file(title: str, mode: str, output: Path) -> dict:
    payload = paragraph_payload(title, mode)
    warnings: list[str] = []
    warnings.extend(pbuilder.add_word_audio_to_paragraph_payload(payload, log=print))
    warnings.extend(pbuilder.annotate_paragraph_ipa_payload(payload, force=True, log=print))
    warnings.extend(pbuilder.add_audio_to_paragraph_payload(payload, log=print))
    if not payload.get("effects"):
        payload["effects"] = pbuilder.build_effect_sounds(lambda _message: None)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(pbuilder.encode_future_manifest(payload, title, output, payload.get("format") or "Space_P"), encoding="utf-8")
    decoded = pbuilder.decode_future_lesson_document(output.read_text(encoding="utf-8-sig", errors="replace"))
    nodes = decoded.get("nodes") or []
    segments = sum(len(node.get("children") or []) for node in nodes if isinstance(node, dict))
    audio_segments = 0
    for node in nodes:
        for child in node.get("children") or []:
            if child.get("audio") and child.get("meaning_audio"):
                audio_segments += 1
    return {"file": str(output), "nodes": len(nodes), "segments": segments, "audio_segments": audio_segments, "warnings": warnings}


def build_space_pls() -> list[dict]:
    title_base = "Global Success Grade 11 Unit 01 Page 16 Healthy Lifestyle Paragraph"
    return [
        build_paragraph_file(title_base + " Space P", "space_p", OUT_P / f"{title_base} Space P.Space_P"),
        build_paragraph_file(title_base + " Space S", "space_s", OUT_S / f"{title_base} Space S.Space_S"),
        build_paragraph_file(title_base + " Space L", "space_l", OUT_L / f"{title_base} Space L.Space_L"),
    ]


def main() -> None:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    result = {
        "space_w": build_space_w(settings),
        "paragraph": build_space_pls(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
