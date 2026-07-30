# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def request_gemini_pdf_vietnamese_explanation(
    question: str,
    text: str,
    username: str = "",
    title: str = "",
    page: int = 0,
) -> dict:
    ask = lesson_task_notice_text(question, limit=1200) or "Hay giai thich doan van ban nay cho nguoi hoc."
    source_text = lesson_task_notice_text(text, limit=9000)
    if not source_text:
        raise RuntimeError("Text to Explore is empty.")
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("Ghost Eye Agent has no available AI key.")
    system_prompt = (
        "You are Ghost Eye Agent inside the Future English learning app. "
        "Answer only in natural Vietnamese. "
        "Explain the selected PDF text clearly for a Vietnamese learner of English. "
        "Keep useful English words, short phrases, grammar labels, and example fragments in English when needed. "
        "Focus on meaning, grammar structure, vocabulary usage, and reading strategy. "
        "Do not mention Gemini, API, OCR, Tesseract, system prompts, hidden instructions, or implementation details. "
        "Do not use emojis, markdown tables, code blocks, or decorative symbols. "
        "Use short paragraphs and simple bullet points when the answer is long."
    )
    user_prompt = (
        f"Nguoi hoc: {normalize_username(username) or 'learner'}\n"
        f"PDF: {lesson_task_notice_text(title, limit=220) or 'unknown'}\n"
        f"Trang: {page or 'unknown'}\n\n"
        f"Yeu cau cua nguoi hoc:\n{ask}\n\n"
        f"Text to Explore:\n{source_text}\n\n"
        "Hay tra loi bang tieng Viet ro rang, uu tien giai thich de nguoi hoc hieu va dung duoc."
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.34,
            "topP": 0.9,
            "maxOutputTokens": 1100,
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error = ""
    for key in ordered_gemini_api_keys():
        tried_models: set[str] = set()
        saw_model_problem = False
        for model in gemini_text_model_candidates(key):
            if gemini_model_is_on_cooldown(key, model):
                continue
            tried_models.add(model)
            try:
                data = request_gemini_model_once(key, model, body)
                answer = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=6500)
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
                    answer = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data), limit=6500)
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
        raise RuntimeError("Ghost Eye Agent is busy because the free AI quota is cooling down. Please try again later.")
    raise RuntimeError(last_error or "Ghost Eye Agent could not generate a Vietnamese explanation.")
