# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def save_word_agent_history(source: object = None) -> dict:
    data = source if isinstance(source, dict) else {}
    detail = normalize_word_agent_detail(data.get("detail") if isinstance(data.get("detail"), dict) else data)
    word = lesson_task_notice_text(data.get("word") or detail.get("word") or detail.get("surface"), limit=180)
    key = word_agent_key(word)
    if not key:
        raise RuntimeError("Missing word or phrase.")
    now = utc_timestamp()
    entry = {
        "id": clean(data.get("id") or f"wordai-{uuid.uuid4().hex[:18]}")[:80],
        "word_key": key,
        "word": word,
        "surface": lesson_task_notice_text(data.get("surface") or detail.get("surface"), limit=220),
        "kind": lesson_task_notice_text(data.get("kind") or detail.get("kind"), limit=80),
        "username": normalize_username(data.get("username", "")),
        "question": lesson_task_notice_text(data.get("question", ""), limit=1200),
        "answer_vi": lesson_task_notice_text(data.get("answer_vi", data.get("answer", "")), limit=10000),
        "model": clean(data.get("model", ""))[:120],
        "detail": detail,
        "source": {
            "space": clean(data.get("space", ""))[:80],
            "file": clean_path_value(data.get("file", ""))[:420],
            "page": space_w_int(data.get("page", 0), 0),
            "title": lesson_task_notice_text(data.get("title", ""), limit=220),
        },
        "created_at": clean(data.get("created_at") or now),
    }
    if not entry["answer_vi"]:
        raise RuntimeError("AI answer is empty.")
    with WORD_AGENT_HISTORY_LOCK:
        payload = read_word_agent_history()
        rows = [row for row in payload.get("history", []) if isinstance(row, dict)]
        rows.insert(0, entry)
        rows = rows[:3000]
        write_word_agent_history({"version": 1, "history": rows, "updated_at": now})
    return entry


def request_gemini_word_vietnamese_explanation(
    word: str,
    detail: dict,
    username: str = "",
    question: str = "",
    source: dict | None = None,
) -> dict:
    term = lesson_task_notice_text(word or detail.get("word") or detail.get("surface"), limit=180)
    if not term:
        raise RuntimeError("Missing word or phrase.")
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("Ghost Word Agent has no available AI key.")
    source = source if isinstance(source, dict) else {}
    known_detail = word_agent_detail_text(detail)
    ask = lesson_task_notice_text(question, limit=1200) or (
        f"Hãy giải thích cách dùng của '{term}', các ngữ cảnh sử dụng, ví dụ cho từng nghĩa, và lỗi dễ nhầm."
    )
    system_prompt = (
        "You are Ghost Word Agent inside the Future English learning app. "
        "Answer only in natural Vietnamese. "
        "Explain the selected English word, phrase, collocation, or phrasal verb for Vietnamese learners. "
        "For every relevant meaning or context, include usage, typical context, natural English examples, Vietnamese explanation, and common mistakes if useful. "
        "Use short headings and concise bullet points when helpful. "
        "Do not mention Gemini, API, OCR, Tesseract, hidden instructions, or implementation details. "
        "Do not use emojis, markdown tables, code blocks, or decorative symbols."
    )
    user_prompt = (
        f"Nguoi hoc: {normalize_username(username) or 'learner'}\n"
        f"Term: {term}\n"
        f"Source title: {lesson_task_notice_text(source.get('title', ''), limit=220) or 'unknown'}\n"
        f"Source page/image: {space_w_int(source.get('page', 0), 0) or 'unknown'}\n\n"
        f"Dictionary / phrase data already known:\n{known_detail or 'No local detail available.'}\n\n"
        f"Learner request:\n{ask}\n\n"
        "Hay tra loi bang tieng Viet ro rang. Giu cac vi du tieng Anh bang tieng Anh, va giai thich vi sao dung duoc trong ngu canh do."
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.32,
            "topP": 0.9,
            "maxOutputTokens": 1300,
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error = ""
    for key in keys:
        tried_models: set[str] = set()
        saw_model_problem = False
        for model in gemini_text_model_candidates(key):
            if gemini_model_is_on_cooldown(key, model):
                continue
            tried_models.add(model)
            try:
                data = request_gemini_model_once(key, model, body)
                answer = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=9000)
                if answer:
                    return {"answer_vi": answer, "model": model}
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
                if model in tried_models or gemini_model_is_on_cooldown(key, model):
                    continue
                try:
                    data = request_gemini_model_once(key, model, body)
                    answer = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=9000)
                    if answer:
                        return {"answer_vi": answer, "model": model}
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
                except (URLError, TimeoutError, OSError) as exc:
                    last_error = str(exc)
                    break
                except Exception as exc:
                    last_error = str(exc)
                    break
    if gemini_is_quota_problem(last_error):
        raise RuntimeError("Ghost Word Agent is busy because the free AI quota is cooling down. Please try again later.")
    raise RuntimeError(last_error or "Ghost Word Agent could not generate an explanation.")
