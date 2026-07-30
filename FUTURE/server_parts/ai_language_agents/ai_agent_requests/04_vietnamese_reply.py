# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def request_gemini_vietnamese_reply(
    message: str,
    english_answer: str = "",
    username: str = "",
    context: dict | None = None,
    mode: str = "spoken",
) -> str:
    prompt = lesson_task_notice_text(message, limit=3600)
    english = lesson_task_notice_text(english_answer, limit=3600)
    if not prompt and not english:
        return ""
    keys = ordered_gemini_api_keys()
    if not keys:
        return ""
    context = context if isinstance(context, dict) else {}
    lesson_hint, space_hint, answer_policy, runtime_hint = ai_agent_context_hints(context)
    answer_mode = normalize_ai_agent_answer_mode(mode)
    allow_current_vocab_word = ai_agent_allows_current_vocabulary_word(context)
    is_space_p = ai_agent_is_space_p_context(context)
    is_space_q = ai_agent_is_space_q_context(context)
    vietnamese_safety_prompt = (
        "Trong Space_V giai doan drill hoac shuffle, tu vung hien tai khong bi an. "
        "Duoc phep noi truc tiep tu do va dung chinh tu do de giai thich nghia, chinh ta, phat am, ngu phap, collocation va vi du. "
        "Khong tiet lo cac dap an an khong lien quan cua bai tap khac."
        if allow_current_vocab_word
        else (
            "Trong Space_P paragraph rewrite, full node text va full current segment text co the duoc dua vao nhu ngu canh noi bo de hieu ngu phap, nghia va trat tu tu. "
            "Duoc doc phan full text do de hieu, nhung khong duoc lam lo token tieng Anh dang khoa/chua mo. "
            "Cac tu tieng Anh da mo khoa trong revealed_text_only hoac revealed_words khong con bi an. "
            "Duoc phep noi truc tiep va giai thich cac tu da mo khoa do. "
            "Khong duoc tiet lo, doan, hay viet tiep cac token tieng Anh chua mo khoa; khong viet tron phan dich tieng Anh con lai. "
            "Voi tu chua mo khoa, chi goi y loai tu, huong nghia, dang chinh ta, vai tro ngu phap, trat tu tu, hoac chien luoc suy luan tu tieng Viet."
            if is_space_p
            else (
                "Trong Space_Q question practice, root_text_visible va current_question chi la ngu canh noi bo. "
                "Khong duoc dua ca cau lam goi y, khong liet ke tat ca tu/cum tu can chon, va khong lam lo token dang an, dang khoa, chua unlock, hoac dap an dung. "
                "Neu nguoi hoc hoi ve phan dang bi an/chua unlock, chi goi y nho ve vai tro ngu phap, huong nghia, loai tu, cach loai dap an gay nhieu, hoac mot buoc suy luan. "
                "Chi quote cum rat ngan da hien ro va khong phai dap an."
                if is_space_q
                else "Never reveal the exact answer, correct option, hidden target vocabulary word, or completed translation for the current exercise. Give hints and explanations instead."
            )
        )
    )
    if answer_mode == "detailed":
        system_prompt = (
            "You are Ghost AI, a Vietnamese learning support agent inside the Future English learning app. "
            "Answer in natural Vietnamese, not as a literal machine translation. "
            "Use the English answer as reference only, then explain in Vietnamese in a clear learner-friendly way. "
            "Keep English example sentences, English words, grammar labels, and short phrases in English when they are useful. "
            "Do not translate every English example into awkward Vietnamese. "
            "You may use short headings and hyphen bullet points. "
            "Do not use emojis, markdown tables, code blocks, or decorative symbols. "
            f"{vietnamese_safety_prompt}"
        )
        max_tokens = 900
        limit = 4200
    else:
        system_prompt = (
            "You are Ghost AI, a Vietnamese learning support agent inside the Future English learning app. "
            "Answer in natural Vietnamese as if you are talking to the learner. "
            "Do not make a literal machine translation of the English answer. "
            "Keep useful English examples, English words, and grammar labels in English. "
            "Do not use emojis, markdown, numbering, or decorative symbols. "
            f"{vietnamese_safety_prompt} Keep it concise."
        )
        max_tokens = 520
        limit = 2200
    user_prompt = (
        f"Nguoi hoc: {normalize_username(username) or 'learner'}\n"
        f"Khong gian dang hoc: {space_hint or 'unknown'}\n"
        f"Bai/file dang hoc: {lesson_hint or 'unknown'}\n\n"
        f"Ngu canh hien tai da bo dap an an:\n{runtime_hint or 'none'}\n\n"
        f"Chinh sach ho tro: {answer_policy or 'Chi goi y, khong tiet lo dap an chinh xac.'}\n\n"
        f"Cau hoi cua nguoi hoc:\n{prompt or 'Learner asked for support.'}\n\n"
        f"Cau tra loi tieng Anh ben trai de tham chieu, khong dich may tung chu:\n{english or 'none'}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.38,
            "topP": 0.9,
            "maxOutputTokens": max_tokens,
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for key in keys:
        tried_models: set[str] = set()
        saw_model_problem = False
        for model in gemini_text_model_candidates(key):
            if gemini_model_is_on_cooldown(key, model):
                continue
            tried_models.add(model)
            try:
                data = request_gemini_model_once(key, model, body)
                vietnamese = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=limit)
                if vietnamese:
                    return vietnamese
            except HTTPError as exc:
                try:
                    err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                except Exception:
                    err_data = {}
                message_text = gemini_error_message(err_data, exc.code)
                if gemini_is_quota_problem(message_text):
                    gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, message_text))
                    continue
                if gemini_is_key_problem(message_text):
                    break
                if gemini_is_model_problem(message_text):
                    saw_model_problem = True
                    continue
            except (URLError, TimeoutError, OSError):
                break
            except Exception:
                break
        if saw_model_problem:
            for model in list_gemini_generate_models(key):
                if model in tried_models:
                    continue
                try:
                    if gemini_model_is_on_cooldown(key, model):
                        continue
                    data = request_gemini_model_once(key, model, body)
                    vietnamese = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=limit)
                    if vietnamese:
                        return vietnamese
                except HTTPError as exc:
                    try:
                        err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                    except Exception:
                        err_data = {}
                    message_text = gemini_error_message(err_data, exc.code)
                    if gemini_is_quota_problem(message_text):
                        gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, message_text))
                        continue
                    if gemini_is_key_problem(message_text):
                        break
                    continue
                except (URLError, TimeoutError, OSError):
                    break
                except Exception:
                    continue
    return ""
