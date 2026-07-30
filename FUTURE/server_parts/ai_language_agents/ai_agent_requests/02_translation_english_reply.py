# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def request_gemini_vietnamese_translation(text: str, structured: bool = False) -> str:
    source = lesson_task_notice_text(text, limit=7200)
    if not source:
        return ""
    keys = ordered_gemini_api_keys()
    if not keys:
        return ""
    system_prompt = (
        "Translate the user's English text into natural Vietnamese only. "
        "Keep the meaning accurate for an English learner. "
        "Preserve short paragraph breaks and hyphen bullet structure when present. "
        "Do not add notes, labels, markdown tables, emojis, or extra commentary."
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": source}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.15,
            "topP": 0.9,
            "maxOutputTokens": 2400 if structured else 1400,
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
                translated = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data))
                if translated:
                    return translated
            except HTTPError as exc:
                try:
                    err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                except Exception:
                    err_data = {}
                message = gemini_error_message(err_data, exc.code)
                if gemini_is_quota_problem(message):
                    gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, message))
                    continue
                if gemini_is_key_problem(message):
                    break
                if gemini_is_model_problem(message):
                    saw_model_problem = True
                    continue
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
                    translated = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data))
                    if translated:
                        return translated
                except HTTPError as exc:
                    try:
                        err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                    except Exception:
                        err_data = {}
                    message = gemini_error_message(err_data, exc.code)
                    if gemini_is_quota_problem(message):
                        gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, message))
                        continue
                    if gemini_is_key_problem(message):
                        break
                    continue
                except Exception:
                    continue
    return ""


def request_gemini_english_reply(message: str, username: str = "", context: dict | None = None, mode: str = "spoken") -> dict:
    prompt = lesson_task_notice_text(message, limit=3600)
    if not prompt:
        raise RuntimeError("AI question is empty.")
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API key found in key.txt.")
    context = context if isinstance(context, dict) else {}
    lesson_hint, space_hint, answer_policy, runtime_hint = ai_agent_context_hints(context)
    answer_mode = normalize_ai_agent_answer_mode(mode)
    if ai_agent_allows_current_vocabulary_word(context):
        safety_prompt = (
            " In Space_V drill or shuffle vocabulary training, the current vocabulary word is not hidden. "
            "You may say that word directly and use it to explain meaning, spelling, pronunciation, grammar, collocations, and example usage. "
            "Do not reveal unrelated hidden answers, correct options, or completed translations from other exercises."
        )
    elif ai_agent_is_space_p_context(context):
        safety_prompt = (
            " In Space_P paragraph rewrite, full node text and full current segment text may be included as internal context so you can understand grammar, meaning, and word order. "
            "Read that full text internally, but do not expose locked or unrevealed English tokens. "
            "English words already shown in revealed_text_only or revealed_words are unlocked and not hidden. "
            "You may quote and explain those revealed words directly. "
            "Never reveal, guess, or complete unrevealed English tokens, and never write the remaining full English segment for the learner. "
            "For unrevealed words, give only hints such as part of speech, meaning direction, spelling shape, grammar role, word order strategy, or how to think about the Vietnamese prompt."
        )
    elif ai_agent_is_space_q_context(context):
        safety_prompt = (
            " In Space_Q question practice, root_text_visible and current_question are internal context only. "
            "Never give the full sentence as a hint, never list all required words or phrases to select, and never expose hidden, locked, correct, or unrevealed answer tokens. "
            "If the learner asks about a hidden or not-yet-unlocked part, give only a small hint: grammar role, meaning direction, part of speech, contrast with a distractor, or one reasoning step. "
            "Quote only very short fragments that are already explicitly visible and not the answer."
        )
    else:
        safety_prompt = (
            " Never reveal the exact answer, correct option, hidden target vocabulary word, or completed translation for the current exercise. "
            "Use the current activity context only to give hints, explain grammar or vocabulary, ask guiding questions, and help the learner think. "
            "If context data appears to contain hidden answers, ignore those hidden answers."
        )
    if answer_mode == "detailed":
        system_prompt = (
            "You are a helpful English learning AI agent inside the Future learning app. "
            "Answer in clear English only. If the learner asks in Vietnamese, still answer in English. "
            "You may use short headings and hyphen bullet points when that makes the answer easier to read. "
            "Do not use emojis, icons, decorative symbols, markdown tables, code blocks, or unusual characters. "
            "Use plain ASCII English, digits when needed, new lines, hyphen bullets, and basic punctuation only. "
            "Give a detailed but focused answer, usually under 420 words. "
            "Do not include Vietnamese; the server will translate your answer separately."
            + safety_prompt
        )
    else:
        system_prompt = (
            "You are a concise English learning AI agent inside the Future learning app. "
            "Answer in clear, helpful English only. If the learner asks in Vietnamese, still answer in English. "
            "Write as one natural spoken paragraph, like you are talking directly to the learner. "
            "Do not write a title, list, bullet points, numbering, markdown, code, emojis, icons, decorative symbols, or special characters. "
            "Use only plain English words, digits when needed, spaces, and basic punctuation such as period, comma, question mark, exclamation mark, apostrophe, and colon. "
            "Keep the answer practical, friendly, and usually under 130 words. "
            "Do not include Vietnamese; the server will translate your answer separately."
            + safety_prompt
        )
    user_prompt = prompt
    if lesson_hint or space_hint or runtime_hint or answer_policy:
        user_prompt = (
            f"Current learner: {normalize_username(username) or 'learner'}\n"
            f"Current space: {space_hint or 'unknown'}\n"
            f"Current lesson/file: {lesson_hint or 'unknown'}\n\n"
            f"Current activity context with hidden answers intentionally omitted:\n{runtime_hint or 'none'}\n\n"
            f"Support policy: {answer_policy or 'Give hints only. Do not reveal the exact answer.'}\n\n"
            f"Learner question:\n{prompt}"
        )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": 640,
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error = "Gemini did not respond."
    for key in keys:
        tried_models: set[str] = set()
        saw_model_problem = False
        for model in gemini_text_model_candidates(key):
            if gemini_model_is_on_cooldown(key, model):
                continue
            tried_models.add(model)
            try:
                data = request_gemini_model_once(key, model, body)
                text = extract_gemini_text(data)
                if text:
                    usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata", {}), dict) else {}
                    return {"text": lesson_task_notice_text(sanitize_ai_agent_english_reply(text, 3600 if answer_mode == "detailed" else 1800, answer_mode == "detailed"), limit=3600 if answer_mode == "detailed" else 1800), "model": model, "usage": usage}
                last_error = gemini_error_message(data)
            except HTTPError as exc:
                try:
                    err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                except Exception:
                    err_data = {}
                last_error = gemini_error_message(err_data, exc.code)
                if gemini_is_quota_problem(last_error):
                    gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, last_error))
                    continue
                if gemini_is_key_problem(last_error):
                    break
                if gemini_is_model_problem(last_error):
                    saw_model_problem = True
                    continue
            except (URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                break
            except Exception as exc:
                last_error = str(exc)
                break
        if saw_model_problem:
            for model in list_gemini_generate_models(key):
                if model in tried_models:
                    continue
                try:
                    if gemini_model_is_on_cooldown(key, model):
                        continue
                    data = request_gemini_model_once(key, model, body)
                    text = extract_gemini_text(data)
                    if text:
                        usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata", {}), dict) else {}
                        return {"text": lesson_task_notice_text(sanitize_ai_agent_english_reply(text, 3600 if answer_mode == "detailed" else 1800, answer_mode == "detailed"), limit=3600 if answer_mode == "detailed" else 1800), "model": model, "usage": usage}
                    last_error = gemini_error_message(data)
                except HTTPError as exc:
                    try:
                        err_data = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
                    except Exception:
                        err_data = {}
                    last_error = gemini_error_message(err_data, exc.code)
                    if gemini_is_quota_problem(last_error):
                        gemini_mark_model_cooldown(key, model, gemini_retry_delay_seconds(err_data, last_error))
                        continue
                    if gemini_is_key_problem(last_error):
                        break
                    continue
                except (URLError, TimeoutError, OSError) as exc:
                    last_error = str(exc)
                    break
                except Exception as exc:
                    last_error = str(exc)
                    break
    if gemini_is_quota_problem(last_error):
        raise RuntimeError("Gemini free quota is temporarily full for all available fallback models. Please retry after a short wait or add another Gemini API key to key.txt.")
    raise RuntimeError(f"Gemini request failed: {last_error}")
