---
name: spacew-lesson-builder
description: Build or update Future Translation Gate Space_W lessons for C:\programe\write_html using future_lesson_builder_gui.py. Use when the user asks to create lessons like Tin 2, generate .Space_W files, rebuild lessons with embedded voice/audio, write accurate Vietnamese prompts, add Google/machine translation comparison cards, add about cards, add Train mode extra practice sentences, or highlight important explanation text in about cards.
---

# Space_W Lesson Builder

## Purpose

Create `.Space_W` lesson files that work with `C:\programe\write_html\future.html` and match the style of `Tin 2.Space_W`: English sentence nodes, Vietnamese meaning, hints, about cards, embedded voices, Vietnamese question audio, and grammar quiz audio.

## Fixed Paths

- App directory: `C:\programe\write_html`
- Builder module: `C:\programe\write_html\future_lesson_builder_gui.py`
- Current voice settings: `C:\programe\programe_cache\future_lesson_builder\builder_settings.json`
- Server data root: `C:\server data`
- Structure output: `C:\server data\Structure\*.json`
- Lesson output: usually `C:\programe\write_html\<title>.Space_W`

## Required Workflow

1. Read the user’s requested lesson topic and content requirements.
2. Build a lesson spec with entries shaped like:
   - `en`: English sentence.
   - `meaning`: Vietnamese prompt/meaning written manually, naturally, accurately, and close to what the learner must type.
   - `google_translation` or `machine_translation`: machine/Google-style Vietnamese translation for comparison in About.
   - `hint`: learner hint.
   - `about`: cards with `q`, `a`, and important `ah` highlights.
   - `practice`: optional Train mode extra sentences with `en`, `meaning`, and `hint`.
3. Use `future_lesson_builder_gui.py` functions to build the file. Do not hand-write the final structure JSON unless repairing a broken file.
4. Use voice settings from `builder_settings.json`. Do not use `"none"` for voice unless the user explicitly asks for no audio.
5. Generate the `.Space_W` manifest with `encode_future_manifest(payload, title)`.
6. Validate by loading the output with `decode_future_lesson_document`.

## Voice Rules

Use the same pattern as `Tin 2`:

```python
selected_voice = settings["selected_voice"]        # usually sot:en-US
grammar_voice = settings["grammar_voice"]          # usually edge:vi-VN-NamMinhNeural
embedded_voices = resolve_embedded_voice_specs(
    settings["embedded_voices"],
    settings["auto_groups"],
    log,
)
train_voice = "kokoro:am_adam"
train_grammar_voice = "edge:vi-VN-NamMinhNeural"
train_embedded_voices = default_train_mode_embedded_voices()  # Adam + Jessica only
payload = build_lesson(
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
```

Train mode extra-practice audio is configured separately from root nodes. Use only:

- Vietnamese prompt/grammar voice: `edge:vi-VN-NamMinhNeural` (Vietnamese VN | Nam Minh).
- English embedded voices: `kokoro:am_adam` (People | Male Adam) and `kokoro:af_jessica` (People | Female Jessica).

Expected validation for a voiced lesson:

- `len(payload["n"])` equals requested sentence count.
- Each node prompt `q`/entry `meaning` is manually written; do not let `translate_to_vi` or Google Translate become the main exercise prompt.
- Each prompt is close to the English answer: preserve person, tense/aspect, key objects, and important adverbs/prepositions.
- Each node has `vc` not equal to `none`.
- Each node has embedded audio: `len(node["av"]) > 0`.
- Each node has Vietnamese prompt audio: `len(node["vq"]) > 0`.
- Each node has grammar audio/questions: `len(node["gq"]) > 0`.
- If a node has Train mode extras under `node["xp"]`, every extra node must also have `av`, `vq`, `gq`, spaCy/scoring fields, English text, and Vietnamese prompt like a normal node.
- Each node has at least 5 about cards under `node["ab"]`.
- Highlight minimums per node: answer card `1`, translation comparison card `2`, similar-question card `5`, possible-answer card `5`, grammar card `5+`.
- Every highlight text `ah[*]["t"]` must be an exact substring of that card’s answer `a`.
- In sample cards, highlights must be useful subphrases, not the whole sample sentence.
- Every learner-facing example in About should include a Vietnamese translation using `English example -> Vietnamese translation`.

## Translation Rules

Write the main `meaning` yourself. It is the Vietnamese exercise prompt, so it should sound natural but still cue the exact English sentence the learner needs to write.

Do not use a loose Vietnamese paraphrase if it hides important English details. Keep these close:

- subject/person: `you`, `your family`, `my mother`, `we`;
- tense/aspect/frequency: `usually`, `often`, `at the moment`, `on weekends`;
- question intent: quantity, frequency, job, location, choice, subject question;
- key phrases/prepositions: `for a living`, `on your own`, `with your family`, `eat meals together`.

Add a comparison translation in About:

- Title: `Bản dịch để so sánh`.
- Body:
  - `Bản dịch tự nhiên dùng làm đề: <manual meaning>`
  - `Bản dịch Google để so sánh: <google_translation>`
  - one short note that the main prompt is the natural, learner-facing prompt.
- If the translation was not actually obtained from Google, label it `Bản dịch máy để so sánh` instead of claiming Google.

## About Cards

For each sentence, include about cards similar to `Tin 2`:

- `câu trả lời của nó có thể là gì?`
- `Bản dịch để so sánh`
- `5 câu hỏi nghĩa tương tự`
- `5 câu trả lời có thể dùng`
- `Ngữ pháp liên quan`

Every important about card should include `ah` highlights. Highlight exact text that appears in the answer body.

Highlight format:

```python
{
    "q": "Ngữ pháp liên quan",
    "a": "How many...? dùng để hỏi số lượng.\nThere are + số lượng + people...",
    "ah": [
        {"t": "How many...?", "n": 1, "c": "#ffff00"},
        {"t": "There are + số lượng + people", "n": 1, "c": "#7dd3fc"}
    ]
}
```

Rules for highlights:

- Use `ah`, not a custom key.
- In `5 câu hỏi nghĩa tương tự`, highlight one important phrase or grammar chunk inside each sample question, usually 5 highlights.
- In `5 câu trả lời có thể dùng`, highlight one important phrase or grammar chunk inside each sample answer, usually 5 highlights.
- In `câu trả lời của nó có thể là gì?`, highlight the answer pattern or key chunk, not the whole answer if a smaller useful phrase exists.
- For every example in those three cards, write it as `English -> tiếng Việt`, for example `How many family members do you have? -> Bạn có bao nhiêu thành viên trong gia đình?`.
- Keep the highlight on the English phrase/grammar chunk, not on the Vietnamese translation or the whole `English -> Vietnamese` line.
- In `Ngữ pháp liên quan`, write a detailed, sentence-specific grammar analysis and highlight the exact structures learners must notice.
- Highlight grammar patterns, answer patterns, key vocabulary, and contrastive forms.
- Use exact substrings from `a`; otherwise the UI cannot find the segment.
- Use short segments, not entire paragraphs.
- Do not highlight a whole sample sentence just to satisfy the count; it does not help learners notice the pattern.
- Prefer explicit `highlight_terms`/`ah` for grammar cards instead of relying on generic auto-detection.
- Good colors: `#ffff00`, `#7dd3fc`, `#86efac`, `#f9a8d4`, `#fbbf24`.

For grammar cards, cover these points when relevant:

- question type and sentence function;
- core structure/formula;
- auxiliary choice (`do`, `does`, `is/are`, modal, etc.);
- subject-verb agreement;
- key phrase meaning;
- natural answer pattern;
- common mistake to avoid.

Do not leave grammar cards generic. Tie the explanation to the exact sentence.

## Train Mode Extra Practice

Use `practice` on a lesson entry to add same-topic extra sentences. These are not normal lesson nodes at first. The builder writes them under the built node’s `xp` field after running the same `build_node()` pipeline as root nodes.

Practice entry shape:

```json
{
  "en": "I usually have dinner with my family on Sundays.",
  "meaning": "Tôi thường ăn tối cùng gia đình vào Chủ nhật.",
  "hint": "Chú ý usually + verb và with my family.",
  "about": [
    {
      "q": "Câu này cần chú ý gì?",
      "a": "I usually have dinner... -> Tôi thường ăn tối... Highlight usually để nhớ tần suất.",
      "ah": [{"t": "usually", "n": 1, "c": "#ffff00"}]
    }
  ]
}
```

Rules:

- Write `practice[*].en` in English.
- Write `practice[*].meaning` manually when possible. If blank, the builder may call `translate_to_vi()` automatically.
- Add a short `practice[*].hint` that helps the learner type the extra sentence.
- Add `practice[*].about` when creating rich Train mode practice. These About cards follow the same rules as root-node About cards: accurate Vietnamese translations for examples, useful phrase-level highlights, and grammar-specific explanations.
- Keep Train mode About mobile-safe: normally use one compact `Ngữ pháp chính` card per train sentence, avoid long lists, avoid full-sentence highlights, and keep highlights to short exact grammar chunks such as `How many`, `Do + subject + base verb`, `usually/often`, `There are`, or the key preposition phrase. Validate that every `ah[*].t` is an exact substring of the card body so mobile rendering does not break.
- In `future_lesson_builder_gui.py`, train/practice sentences can be edited from the "Bổ sung câu cùng chủ đề" dialog. Right-click a train sentence, or use its About button, to open the maximized About-card editor for that train node.
- Keep practice sentences close to the same topic as the root node.
- Expect the built `.Space_W` node to contain `xp`; each `xp` item should behave like a full node with audio, IPA, spaCy analysis, grammar questions, and speaking/scoring data.
- Build practice nodes with the separate Train mode voices: English `kokoro:am_adam` + `kokoro:af_jessica`, Vietnamese `edge:vi-VN-NamMinhNeural`.
- In the learner app, About has a `Train mode` button when `xp` exists. When the learner clicks it, the app appends all extra practice nodes to the end of the lesson, keeps the learner on the root-node path first, then moves into Train nodes after the roots are complete. Train audio should start caching gradually only after this click.
- After a learner has saved/completed the root path for a Space_W file once, the load gate can show `Review Train`. This skips root-first study, expands Train nodes, and starts the same shuffled review flow over root + Train nodes.
- The hidden tools group includes a Lesson Vault button that returns to the folder/file selection screen.

## Recommended Script

Use or adapt `scripts/build_spacew_from_spec.py` when building from a JSON spec. It imports the real builder module, loads the current voice settings, builds the lesson, writes the `.Space_W` manifest, and validates audio counts.

Spec details are in `references/spacew_spec.md`.

## Validation Commands

After building:

```powershell
$env:PYTHONIOENCODING='utf-8'
python - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, r"C:\programe\write_html")
import future_lesson_builder_gui as f
p = Path(r"C:\programe\write_html\<title>.Space_W")
payload = f.decode_future_lesson_document(p.read_text(encoding="utf-8-sig"))
print(payload.get("t"), len(payload.get("n", [])), payload.get("gv"))
for i, n in enumerate(payload.get("n", []), 1):
    print(i, n.get("vc"), len(n.get("av") or []), len(n.get("vq") or []), len(n.get("gq") or []), n.get("e"))
PY
```

If PowerShell heredoc syntax is awkward, use `@' ... '@ | python -`.

Also check the build log for real failures:

```powershell
rg -n "Traceback|Loi|failed|khong tao duoc" build_*.log
```

`Bo qua audio` lines are unacceptable when the user requested a voiced lesson, unless the skipped item is intentionally unsupported and the final validation still has complete `av`, `vq`, and `gq`.
