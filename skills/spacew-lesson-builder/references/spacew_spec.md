# Space_W Lesson Spec

Use this JSON shape when generating a lesson from a script:

```json
{
  "title": "Gia đình 10 câu",
  "entries": [
    {
      "en": "How many people are there in your family?",
      "meaning": "Gia đình bạn có bao nhiêu người?",
      "google_translation": "Có bao nhiêu người trong gia đình bạn?",
      "hint": "Gợi ý: Câu này hỏi về số lượng thành viên trong gia đình.",
      "practice": [
        {
          "en": "I have a small family with three people.",
          "meaning": "Tôi có một gia đình nhỏ với ba người.",
          "hint": "Chú ý I have + noun phrase và with three people."
        }
      ],
      "about": [
        {
          "q": "câu trả lời của nó có thể là gì?",
          "a": "There are four people in my family. -> Gia đình tôi có bốn người.",
          "ah": [
            { "t": "There are four people", "n": 1, "c": "#ffff00" }
          ]
        },
        {
          "q": "Bản dịch để so sánh",
          "a": "Bản dịch tự nhiên dùng làm đề: Gia đình bạn có bao nhiêu người?\nBản dịch Google để so sánh: Có bao nhiêu người trong gia đình bạn?\nLưu ý: Đề chính được viết sát với câu người học cần gõ, giữ đúng ngôi, thì, ý chính và cách nói tự nhiên.",
          "highlight_terms": [
            "Bản dịch tự nhiên dùng làm đề",
            "Bản dịch Google để so sánh",
            "Đề chính được viết sát với câu người học cần gõ"
          ]
        },
        {
          "q": "5 câu hỏi nghĩa tương tự",
          "a": "How many family members do you have? -> Bạn có bao nhiêu thành viên trong gia đình?\nHow big is your family? -> Gia đình bạn đông không?",
          "ah": [
            { "t": "How many family members", "n": 1, "c": "#7dd3fc" },
            { "t": "How big", "n": 1, "c": "#86efac" }
          ]
        },
        {
          "q": "5 câu trả lời có thể dùng",
          "a": "There are four people in my family. -> Gia đình tôi có bốn người.\nI have a family of five. -> Gia đình tôi có năm người.",
          "ah": [
            { "t": "There are four people", "n": 1, "c": "#ffff00" },
            { "t": "I have a family of five", "n": 1, "c": "#7dd3fc" }
          ]
        },
        {
          "q": "Ngữ pháp liên quan",
          "a": "How many...? dùng để hỏi số lượng.\nCấu trúc: How many + danh từ số nhiều + are there...?",
          "highlight_terms": [
            "How many...?",
            "How many + danh từ số nhiều + are there...?"
          ]
        }
      ]
    }
  ]
}
```

Important notes:

- `ah` highlights the about answer `a`, not the main sentence.
- The `t` field must be an exact substring of `a`.
- `n` is the occurrence number when the same text appears more than once.
- For `5 câu hỏi nghĩa tương tự`, highlight one useful subphrase/grammar chunk inside each sample question line.
- For `5 câu trả lời có thể dùng`, highlight one useful subphrase/grammar chunk inside each sample answer line.
- For `câu trả lời của nó có thể là gì?`, `5 câu hỏi nghĩa tương tự`, and `5 câu trả lời có thể dùng`, each example line should use `English -> Vietnamese`.
- The translation after `->` should be natural Vietnamese and help the learner understand the example quickly.
- Keep highlights on meaningful English chunks before `->`; do not highlight the whole line or only the Vietnamese translation.
- Do not highlight an entire sample sentence unless it is truly just a short fixed expression and there is no better smaller phrase.
- Provide `meaning` manually. This is the actual prompt shown to the learner, so it must be natural, accurate, and close to the English sentence.
- Provide `google_translation` or `machine_translation` for the `Bản dịch để so sánh` card. Do not use the machine translation as the main prompt when it is unnatural.
- In the translation comparison card, highlight the labels and the note about the prompt being close to what the learner must type.
- Optional `practice` entries create Train mode extra sentences for that root node. Each practice entry needs English `en`, Vietnamese `meaning` when possible, and a useful `hint`.
- Train mode audio is separate from root-node audio: use only English `kokoro:am_adam` + `kokoro:af_jessica`, and Vietnamese `edge:vi-VN-NamMinhNeural`.
- Built practice sentences are stored as `node.xp` and must validate like full nodes: English audio `av`, Vietnamese prompt audio `vq`, grammar/spaCy audio `gq`, tokens, IPA, and scoring data.
- Runtime behavior: `xp` stays dormant until the learner clicks `Train mode`; only then should the app append Train nodes after all root nodes and begin gradual background audio caching for those Train nodes.
- For `Ngữ pháp liên quan`, prefer `highlight_terms` with exact short grammar segments; the build helper converts them to `ah`.
- Use concise grammar highlight segments. Do not highlight full grammar paragraphs.
- If a card explains grammar, highlight the exact grammar pattern, key vocabulary, answer form, and common mistake.
- A complete lesson should validate with at least these highlight counts per node: answer card `1`, translation comparison card `2`, similar-question card `5`, possible-answer card `5`, grammar card `5+`.
