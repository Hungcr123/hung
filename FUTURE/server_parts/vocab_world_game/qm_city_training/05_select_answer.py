def qm_city_training_select(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    requested_id = clean(source_payload.get("slime_id", ""))
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        _row, level_meta, stats, _changed = qm_city_training_ensure_user(state, username, tick_motion=False)
        arena = state["users"][username]["arena"]
        slime = qm_city_training_selected_slime(arena, requested_id)
        if not slime:
            raise RuntimeError("No slime is available. Reset the practice gate.")
        for item in (arena.get("slimes") if isinstance(arena.get("slimes"), list) else []):
            if isinstance(item, dict) and clean(item.get("id", "")) != clean(slime.get("id", "")):
                item.pop("focus_anchor_x", None)
                item.pop("focus_anchor_y", None)
        anchor_x = shared_world_clamp(source_payload.get("player_x", source_payload.get("playerX", slime.get("tx", slime.get("x", 0.5)))))
        anchor_y = shared_world_clamp(source_payload.get("player_y", source_payload.get("playerY", slime.get("ty", slime.get("y", 0.5)))))
        slime["focus_anchor_x"] = round(anchor_x, 4)
        slime["focus_anchor_y"] = round(anchor_y, 4)
        slime["tx"] = round(anchor_x, 4)
        slime["ty"] = round(anchor_y, 4)
        slime["next_move_at"] = time.time() + 1.0
        arena["selected_id"] = clean(slime.get("id", ""))
        question = slime.get("question") if isinstance(slime.get("question"), dict) else {}
        if not clean(question.get("prompt", "")) or not clean(question.get("answer", "")):
            question = qm_city_training_pick_question(username, arena, slime.get("preferred_kind", ""))
            slime["question"] = question
        arena["question"] = question
        arena["updated_at"] = utc_timestamp()
        write_qm_city_training_state(state)
        qm_city_training_clear_public_state_cache(username)
    return {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
            "event": {"type": "select", "slime_id": clean(slime.get("id", ""))},
        }
    }


def qm_city_training_answer(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    answer = clean(source_payload.get("answer", ""))
    requested_id = clean(source_payload.get("slime_id", ""))
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        _row, level_meta, stats, _changed = qm_city_training_ensure_user(state, username, tick_motion=False)
        arena = state["users"][username]["arena"]
        slime = qm_city_training_selected_slime(arena, requested_id)
        if not slime:
            raise RuntimeError("Choose a slime before answering.")
        question = slime.get("question") if isinstance(slime.get("question"), dict) else {}
        if not clean(question.get("prompt", "")) or not clean(question.get("answer", "")):
            question = arena.get("question") if isinstance(arena.get("question"), dict) else {}
        if not clean(question.get("prompt", "")) or not clean(question.get("answer", "")):
            question = qm_city_training_pick_question(username, arena, slime.get("preferred_kind", ""))
        slime["question"] = question
        arena["question"] = question
        local_speech_question = bool(question.get("local_speech"))
        question_kind = qm_city_training_normalize_question_kind(question.get("training_kind", question.get("kind", "")))
        server_speech_answer = bool(source_payload.get("server_speech", source_payload.get("serverSpeech", False)))
        browser_speech_answer = bool(source_payload.get("browser_speech", source_payload.get("browserSpeech", False)))
        translate_threshold = 60 if server_speech_answer and question_kind in {"translate_vi", "translate_vi_speech"} else float(question.get("accept_percent", 70) or 70)
        if local_speech_question:
            correct = bool(source_payload.get("local_speech_passed"))
        elif question_kind in {"translate_vi", "translate_vi_speech"}:
            correct = qm_city_training_vietnamese_answer_matches(answer, question.get("answer", ""), translate_threshold / 100.0)
        else:
            correct = shared_world_battle_answer_matches(answer, question.get("answer", ""))
        critical_hit = False
        critical_reason = ""
        accuracy_percent = 0
        score_payload: dict = {}
        if local_speech_question:
            raw_percent = (
                source_payload.get("local_speech_percent", source_payload.get("localSpeechPercent",
                source_payload.get("local_speech_score", source_payload.get("localSpeechScore", 0))))
            )
            try:
                accuracy_percent = max(0, min(100, int(round(float(raw_percent or 0)))))
            except Exception:
                accuracy_percent = 0
            critical_hit = bool(correct and accuracy_percent >= 100)
            critical_reason = "perfect_speech" if critical_hit else ""
            score_payload = {
                "percent": accuracy_percent,
                "correct": space_w_int(source_payload.get("local_speech_correct", source_payload.get("localSpeechCorrect", 0)), 0),
                "total": space_w_int(source_payload.get("local_speech_total", source_payload.get("localSpeechTotal", 0)), 0),
            }
        elif question_kind in {"translate_vi", "translate_vi_speech"}:
            threshold = translate_threshold / 100.0
            score_payload = qm_city_training_vietnamese_answer_score(answer, question.get("answer", ""), threshold)
            correct = bool(score_payload.get("correct"))
            accuracy_percent = space_w_int(score_payload.get("percent", 0), 0)
            critical_hit = bool(correct and score_payload.get("exact"))
            critical_reason = ("perfect_spoken_translation" if server_speech_answer or question_kind == "translate_vi_speech" else "perfect_translation") if critical_hit else ""
        log = arena.setdefault("log", [])
        if not isinstance(log, list):
            log = []
        event = {
            "event_id": f"training_{time.time_ns()}",
            "type": "hit" if correct else "hurt",
            "correct": correct,
            "slime_id": clean(slime.get("id", "")),
            "slime_name": clean(slime.get("name", "Slime")),
            "slime_level": space_w_int(slime.get("level", 1), 1),
            "slime_x": slime.get("tx", slime.get("x", 0.5)),
            "slime_y": slime.get("ty", slime.get("y", 0.5)),
        }
        answer_text = clean(question.get("answer_text", "")) or clean(question.get("read_text", "")) or clean(question.get("answer", ""))
        question_prompt = clean(question.get("prompt", ""))
        if question_prompt:
            event["question_prompt"] = question_prompt
            event["questionPrompt"] = question_prompt
        if answer_text:
            event["answer"] = answer_text
            event["expected_answer"] = answer_text
            event["expectedAnswer"] = answer_text
        if answer:
            event["user_answer"] = answer
            event["userAnswer"] = answer
        if server_speech_answer:
            event["server_speech"] = True
            event["serverSpeech"] = True
            event["browser_speech"] = browser_speech_answer
            event["browserSpeech"] = browser_speech_answer
            event["speech_language"] = clean(source_payload.get("speech_language", source_payload.get("speechLanguage", "vi"))) or "vi"
            event["speechLanguage"] = event["speech_language"]
        if clean(question.get("kind", "")):
            event["question_kind"] = clean(question.get("kind", ""))
        if correct:
            skill = qm_city_training_choose_skill(level_meta.get("level", 1))
            base_damage = max(1, space_w_int(stats.get("strength", 1), 1))
            damage = base_damage
            damage_before_critical = damage
            if critical_hit:
                damage = max(1, damage * 2)
            slime_hp_before = space_w_int(slime.get("hp", 0), 0)
            slime["hp"] = max(0, space_w_int(slime.get("hp", 0), 0) - damage)
            mana_gain = 8
            arena["player_mana"] = min(space_w_int(stats.get("max_mana", 60), 60), space_w_int(arena.get("player_mana", 0), 0) + mana_gain)
            slime["mood"] = "hurt" if slime["hp"] > 0 else "defeated"
            question_exp = qm_city_training_question_exp(question)
            reward_count = question_exp
            defeated_now = slime_hp_before > 0 and slime["hp"] <= 0
            if defeated_now and not bool(slime.get("kill_rewarded")):
                slime["kill_rewarded"] = True
                reward_count += 1
                event["crystal_drops"] = qm_city_training_make_crystal_drops(event.get("event_id", ""))
                event["crystalDrops"] = event["crystal_drops"]
            if defeated_now:
                slime["respawn_at"] = time.time() + QM_CITY_TRAINING_SPEECH_RESPAWN_SECONDS
                event["respawn_seconds"] = QM_CITY_TRAINING_SPEECH_RESPAWN_SECONDS
            row_ref = state["users"].setdefault(username, {})
            current_training_words = qm_city_training_bonus_words_from_row(row_ref)
            row_ref["training_words"] = current_training_words + reward_count
            raw_stats = row_ref.get("stats") if isinstance(row_ref.get("stats"), dict) else {}
            raw_stats["training_words"] = row_ref["training_words"]
            level_meta = qm_city_training_level_meta(username, row_ref["training_words"])
            stats = qm_city_training_normalize_stats(raw_stats, level_meta)
            stats["training_words"] = row_ref["training_words"]
            row_ref["stats"] = stats
            max_hp = max(1, space_w_int(stats.get("max_hp", 100), 100))
            current_hp = max(0, min(max_hp, space_w_int(arena.get("player_hp", max_hp), max_hp)))
            heal_amount = 0
            if critical_hit:
                critical_heal_target = max(1, int(math.ceil(max_hp * 0.05)))
                healed_hp = min(max_hp, current_hp + critical_heal_target)
                heal_amount = max(0, healed_hp - current_hp)
                arena["player_hp"] = healed_hp
            else:
                arena["player_hp"] = current_hp
            attack_style = random.choice(("bolt", "arc", "sky", "slash", "nova"))
            event.update({
                "damage": damage,
                "base_damage": damage_before_critical,
                "baseDamage": damage_before_critical,
                "critical": critical_hit,
                "critical_multiplier": 2 if critical_hit else 1,
                "criticalMultiplier": 2 if critical_hit else 1,
                "critical_reason": critical_reason,
                "criticalReason": critical_reason,
                "accuracy_percent": accuracy_percent,
                "accuracyPercent": accuracy_percent,
                "score": score_payload,
                "answer": answer_text,
                "user_answer": answer,
                "userAnswer": answer,
                "expected_answer": answer_text,
                "expectedAnswer": answer_text,
                "attack_style": attack_style,
                "attackStyle": attack_style,
                "slime_hp": slime["hp"],
                "skill": {key: skill.get(key) for key in ("id", "name", "tone", "unlock_level")},
                "earned_words": reward_count,
                "exp": question_exp,
                "heal_amount": heal_amount,
                "healAmount": heal_amount,
                "mana_gain": mana_gain,
                "player_hp": arena["player_hp"],
                "playerHp": arena["player_hp"],
                "max_hp": max_hp,
                "maxHp": max_hp,
                "player_mana": arena["player_mana"],
                "slime_defeated": defeated_now,
            })
            critical_text = " Critical x2!" if critical_hit else ""
            heal_text = f" Critical recovery +{heal_amount} HP." if heal_amount else ""
            log.append({"at": utc_timestamp(), "type": "hit", "text": f"{clean(skill.get('name', 'Fire Skill'))}.{critical_text}{heal_text} Correct answer dealt {damage} damage and earned {reward_count} EXP."})
        else:
            damage = max(1, int(math.ceil(max(1, space_w_int(stats.get("max_hp", 100), 100)) / 10)))
            arena["player_hp"] = max(0, space_w_int(arena.get("player_hp", stats.get("max_hp", 100)), stats.get("max_hp", 100)) - damage)
            slime_mana_gain = 6
            slime["mana"] = min(space_w_int(slime.get("max_mana", 20), 20), space_w_int(slime.get("mana", 0), 0) + slime_mana_gain)
            slime["mood"] = "angry"
            event.update({"damage": damage, "answer": answer_text, "expected_answer": answer_text, "expectedAnswer": answer_text, "player_hp": arena["player_hp"], "slime_mana_gain": slime_mana_gain, "slime_mana": slime["mana"]})
            log.append({"at": utc_timestamp(), "type": "hurt", "text": f"Not yet. Slime countered for {damage} damage."})
            if arena["player_hp"] <= 0:
                event["player_defeated"] = True
                event["return_to_city"] = True
                log.append({"at": utc_timestamp(), "type": "restore", "text": "Your fire core fainted. Returning to QM-City center."})
                fresh_arena = qm_city_training_new_arena(username, level_meta, stats)
                fresh_arena["log"] = (log[-8:] + (fresh_arena.get("log") if isinstance(fresh_arena.get("log"), list) else []))[-24:]
                arena = fresh_arena
                state["users"][username]["arena"] = arena
        alive = qm_city_training_alive_slimes(arena)
        pending_speech_respawns = qm_city_training_pending_speech_respawns(arena)
        if not alive and not pending_speech_respawns:
            clear_log = {"at": utc_timestamp(), "type": "clear", "text": "All slimes are down. A fresh practice field is ready."}
            log.append(clear_log)
            arena = qm_city_training_new_arena(username, level_meta, stats)
            arena["log"] = (log[-8:] + (arena.get("log") if isinstance(arena.get("log"), list) else []))[-24:]
            state["users"][username]["arena"] = arena
            event["cleared"] = True
        else:
            if space_w_int(slime.get("hp", 0), 0) <= 0:
                slime.pop("focus_anchor_x", None)
                slime.pop("focus_anchor_y", None)
                arena["selected_id"] = ""
                arena["question"] = {}
            else:
                slime["question"] = qm_city_training_pick_question(username, arena, slime.get("preferred_kind", ""))
                arena["selected_id"] = clean(slime.get("id", ""))
            selected_slime = qm_city_training_selected_slime(arena)
            if selected_slime and isinstance(selected_slime.get("question"), dict):
                arena["question"] = selected_slime["question"]
            elif not selected_slime:
                arena["question"] = {}
            else:
                selected_kind = qm_city_training_normalize_question_kind(selected_slime.get("preferred_kind", "")) if selected_slime else ""
                arena["question"] = qm_city_training_pick_question(username, arena, selected_kind)
                if selected_slime:
                    selected_slime["question"] = arena["question"]
        arena["log"] = log[-24:]
        arena["updated_at"] = utc_timestamp()
        state["users"][username]["updated_at"] = utc_timestamp()
        write_qm_city_training_state(state)
        qm_city_training_clear_public_state_cache(username)
    return {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
            "event": event,
        }
    }
