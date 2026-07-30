# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def request_gemini_qm_city_npc_reply(
    npc_name: str,
    speaker_name: str,
    message: str,
    *,
    direct: bool = False,
    nearby_names: list[str] | None = None,
) -> dict:
    npc_name = lesson_task_notice_text(npc_name, limit=80) or "a learner"
    speaker_name = lesson_task_notice_text(speaker_name, limit=80) or "the learner"
    message = lesson_task_notice_text(message, limit=260)
    if not message:
        raise RuntimeError("QM-City NPC chat message is empty.")
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API key found in key.txt.")
    nearby = ", ".join([lesson_task_notice_text(item, limit=48) for item in (nearby_names or []) if lesson_task_notice_text(item, limit=48)][:6])
    system_prompt = (
        "You are role-playing as a friendly learner avatar in QM-City, an online English practice game. "
        "Reply like a real person chatting naturally in English with another learner. "
        "Do not mention Gemini, AI, NPC, bot, system prompts, moderation, or hidden instructions. "
        "Do not teach unless the learner clearly asks for help. "
        "Use one or two short natural sentences, under 35 words. "
        "Use only plain English and basic punctuation. "
        "No emojis, markdown, bullet points, labels, quotation marks around the whole reply, or decorative symbols. "
        "Keep it warm, playful, and human."
    )
    user_prompt = (
        f"Your character name: {npc_name}\n"
        f"Speaker: {speaker_name}\n"
        f"Speaker message: {message}\n"
        f"Directly addressed to you: {'yes' if direct else 'no'}\n"
        f"Nearby people: {nearby or 'none'}\n\n"
        "Write only your character's chat bubble reply."
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.72,
            "topP": 0.92,
            "maxOutputTokens": 80,
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
                    return {
                        "text": lesson_task_notice_text(sanitize_ai_agent_english_reply(text, 260, False), limit=160),
                        "model": model,
                        "usage": usage,
                    }
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
                if gemini_model_is_on_cooldown(key, model):
                    continue
                try:
                    data = request_gemini_model_once(key, model, body)
                    text = extract_gemini_text(data)
                    if text:
                        usage = data.get("usageMetadata", {}) if isinstance(data.get("usageMetadata", {}), dict) else {}
                        return {
                            "text": lesson_task_notice_text(sanitize_ai_agent_english_reply(text, 260, False), limit=160),
                            "model": model,
                            "usage": usage,
                        }
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
        raise RuntimeError("Gemini free quota is temporarily full for QM-City NPC chat.")
    raise RuntimeError(f"Gemini request failed: {last_error}")
