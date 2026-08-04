# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def build_ai_agent_notice(username: str, message: str, context: dict | None = None, mode: str = "spoken") -> dict:
    started_at = time.perf_counter()
    answer_mode = normalize_ai_agent_answer_mode(mode)
    gemini = request_gemini_english_reply(message, username=username, context=context, mode=answer_mode)
    english = lesson_task_notice_text(
        sanitize_ai_agent_english_reply(gemini.get("text", ""), 3600 if answer_mode == "detailed" else 1800, answer_mode == "detailed"),
        limit=3600 if answer_mode == "detailed" else 1800,
    )
    if not english:
        raise RuntimeError("Gemini returned an empty answer.")
    vietnamese = request_gemini_vietnamese_reply(message, english, username=username, context=context, mode=answer_mode)
    if not vietnamese:
        vietnamese = request_gemini_vietnamese_translation(english, structured=answer_mode == "detailed")
    if not vietnamese:
        vietnamese = task_notice_translate_to_vietnamese(english)
    settings = load_server_settings()
    voice = clean(settings.get("ai_agent_notice_voice", DEFAULT_SETTINGS["ai_agent_notice_voice"])) or DEFAULT_SETTINGS["ai_agent_notice_voice"]
    voice_lowered = voice.lower()
    voice_is_vietnamese = voice_lowered.startswith(("kokoro_vi:", "sot:vi")) or "vi-vn" in voice_lowered
    if answer_mode == "spoken":
        audio_text = vietnamese if voice_is_vietnamese else english
    else:
        audio_text = "Ghost AI đã tạo câu trả lời chi tiết. Hãy đọc hai khung trên màn hình." if voice_is_vietnamese else "Here is a detailed answer from Ghost AI. Please read the two panels on the screen."
    audio_payload: dict = {}
    audio_error = ""
    try:
        audio_payload = chat_synthesize_message_audio_queued(audio_text, voice, source="ai_notice_followup")
    except Exception as exc:
        audio_error = str(exc)
    now = utc_timestamp()
    usage = gemini.get("usage", {}) if isinstance(gemini.get("usage", {}), dict) else {}
    prompt_tokens = int(usage.get("promptTokenCount") or usage.get("prompt_token_count") or estimate_ai_agent_token_count(message))
    output_tokens = int(usage.get("candidatesTokenCount") or usage.get("candidates_token_count") or estimate_ai_agent_token_count(english))
    total_tokens = int(usage.get("totalTokenCount") or usage.get("total_token_count") or (prompt_tokens + output_tokens))
    request_ms = max(1, int((time.perf_counter() - started_at) * 1000))
    try:
        audio_duration_ms = int(float(audio_payload.get("duration_ms", audio_payload.get("durationMs", 0)) or 0))
    except Exception:
        audio_duration_ms = 0
    ai_agent_metrics = {
        "input_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "request_ms": request_ms,
        "audio_ms": audio_duration_ms,
    }
    notice = {
        "id": f"ai-agent-{uuid.uuid4().hex[:16]}",
        "user": normalize_username(username),
        "text": english,
        "language": "en",
        "translation_en": english,
        "translation_vi": vietnamese,
        "mode": "once",
        "notice_style": "face1",
        "audio_enabled": bool(audio_payload),
        "require_ack": True,
        "voice": voice,
        "voice_label": audio_payload.get("voice_label") or "People | Male Michael",
        "speaker_name": "Ghost AI",
        "ai_agent_mode": answer_mode,
        "audio_text": audio_text,
        "ai_agent_metrics": ai_agent_metrics,
        "created_by": "ai-agent",
        "created_at": now,
        "updated_at": now,
        "active": True,
    }
    if audio_payload:
        notice.update(audio_payload)
    normalized = normalize_lesson_task_notice(notice, username) or notice
    normalized["_immediate"] = True
    normalized["_ai_agent"] = True
    normalized["_instant_id"] = int(time.time() * 1000)
    normalized["ai_agent_mode"] = answer_mode
    normalized["translation_vi"] = vietnamese
    normalized["translation_en"] = english
    normalized["audio_text"] = audio_text
    normalized["gemini_model"] = clean(gemini.get("model", ""))
    normalized["ai_agent_metrics"] = ai_agent_metrics
    if audio_error:
        normalized["audio_error"] = audio_error[:260]
    return normalized


def build_ai_agent_space_p_followup(username: str, context: dict | None = None) -> dict:
    source = context if isinstance(context, dict) else {}
    lesson_hint, _space_hint, answer_policy, runtime_hint = ai_agent_context_hints(source)
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API key found in key.txt.")
    system_prompt = (
        "You are Ghost AI, a careful Vietnamese English tutor in the Future Space_P paragraph rewrite exercise. "
        "The learner has just completed one English segment, but at least one word was revealed by an auto hint. "
        "Create exactly one short Vietnamese follow-up question that invites the learner to ask for a deeper explanation. "
        "Focus on the likely reason for the hint: grammar, word order, word choice, collocation, tense, article, preposition, or sentence structure. "
        "Do not answer the question. Do not make a list. Do not use markdown, emojis, numbering, decorative symbols, or labels. "
        "Write naturally, usually starting like: Trong câu vừa rồi, bạn có muốn biết vì sao... "
        "The completed segment may be referenced briefly, but do not expose future locked content from later segments."
    )
    user_prompt = (
        f"Nguoi hoc: {normalize_username(username) or 'learner'}\n"
        f"Bai/file dang hoc: {lesson_hint or 'Space_P'}\n\n"
        f"Ngu canh Space_P vua hoan thanh:\n{runtime_hint or 'none'}\n\n"
        f"Chinh sach: {answer_policy or 'Tao mot cau hoi goi mo ngan bang tieng Viet.'}\n\n"
        "Hay tao mot cau hoi goi mo duy nhat bang tieng Viet de nguoi hoc bam Ghost AI va tra loi neu muon duoc giai thich."
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.42,
            "topP": 0.9,
            "maxOutputTokens": 160,
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
                text = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data))
                text = lesson_task_notice_text(text, limit=420)
                if text:
                    return {"question_vi": text, "model": model}
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
                    text = sanitize_ai_agent_vietnamese_reply(extract_gemini_text(data))
                    text = lesson_task_notice_text(text, limit=420)
                    if text:
                        return {"question_vi": text, "model": model}
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
                except Exception as exc:
                    last_error = str(exc)
                    continue
    fallback_question = "Trong câu vừa rồi, bạn có muốn biết vì sao cấu trúc hoặc trật tự từ đó được dùng như vậy không?"
    if gemini_is_quota_problem(last_error):
        return {"question_vi": fallback_question, "model": "fallback"}
    return {"question_vi": fallback_question, "model": "fallback", "error": last_error[:240]}
