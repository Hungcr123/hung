# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def stt_worker_request(path: str, payload: dict | None = None, timeout: float = 8.0, method: str = "POST") -> dict:
    url = f"{STT_WORKER_URL}{path if path.startswith('/') else '/' + path}"
    data = None
    headers = {"Accept": "application/json"}
    if method.upper() != "GET":
        data = json_bytes(payload or {})
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(url, data=data, headers=headers, method=method.upper())
    with urlopen(request, timeout=max(0.8, float(timeout or 8.0))) as response:
        raw = response.read()
    parsed = json.loads(raw.decode("utf-8-sig") if raw else "{}")
    if not isinstance(parsed, dict):
        raise RuntimeError("Invalid STT worker response.")
    if parsed.get("ok") is False:
        raise RuntimeError(clean(parsed.get("error", "")) or "STT worker error.")
    return parsed


def sync_stt_worker_state(payload: dict | None) -> None:
    if not isinstance(payload, dict):
        return
    SERVER_STATE.update(
        {
            "worker_url": STT_WORKER_URL,
            "worker_ready": bool(payload.get("ready")),
            "worker_loading": bool(payload.get("loading")),
            "worker_pid": int(payload.get("pid", 0) or 0),
            "ready": bool(payload.get("ready")) or bool(SERVER_STATE.get("ready")),
            "loading": bool(payload.get("loading")),
            "model_name": clean(payload.get("model_name", SERVER_STATE.get("model_name", ""))) or SERVER_STATE.get("model_name", "small"),
            "model_ref": clean(payload.get("model_ref", SERVER_STATE.get("model_ref", ""))),
            "language": clean(payload.get("language", SERVER_STATE.get("language", "en"))) or "en",
            "device": clean(payload.get("device", SERVER_STATE.get("device", "cpu"))) or "cpu",
            "compute_type": clean(payload.get("compute_type", SERVER_STATE.get("compute_type", "int8"))) or "int8",
            "last_error": clean(payload.get("last_error", SERVER_STATE.get("last_error", ""))),
            "worker_last_error": clean(payload.get("last_error", "")),
        }
    )


def stt_worker_health(timeout: float = 1.5) -> dict | None:
    try:
        payload = stt_worker_request("/health", method="GET", timeout=timeout)
        sync_stt_worker_state(payload)
        return payload
    except Exception as exc:
        SERVER_STATE.update({"worker_ready": False, "worker_loading": False, "worker_last_error": str(exc)})
        return None


def read_stt_worker_pid() -> int:
    try:
        if STT_WORKER_PID_FILE.is_file():
            return int(clean(STT_WORKER_PID_FILE.read_text(encoding="utf-8")) or "0")
    except Exception:
        pass
    return 0


def write_stt_worker_pid(pid: int) -> None:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_text(STT_WORKER_PID_FILE, str(int(pid or 0)), encoding="utf-8")
    except Exception:
        pass


def powershell_single_quote(value: object) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def _windowless_python_executable() -> str:
    exe = sys.executable or "python"
    if os.name == "nt":
        try:
            candidate = Path(exe).with_name("pythonw.exe")
            if candidate.is_file():
                return str(candidate)
        except Exception:
            pass
    return exe


def start_detached_stt_worker_process(cmd: list[str]) -> int:
    launch_cmd = list(cmd)
    if launch_cmd:
        launch_cmd[0] = _windowless_python_executable()
    worker_env = os.environ.copy()
    worker_env["FUTURE_SERVER2_PROCESS_ROLE"] = "stt-worker"
    worker_env["FUTURE_SERVER2_PROCESS_STATUS"] = "Future Server 2 - stt-worker"
    if os.name == "nt":
        hidden_kwargs = subprocess_hidden_kwargs()
        # Added 2026-07-08: detach Whisper/STT so dashboard server closes do not evict its warm RAM.
        hidden_kwargs["creationflags"] = (
            int(hidden_kwargs.get("creationflags", 0))
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        )
        try:
            process = subprocess.Popen(
                launch_cmd,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                env=worker_env,
                **hidden_kwargs,
            )
            return int(process.pid or 0)
        except Exception:
            return 0
    process = subprocess.Popen(
        launch_cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=worker_env,
        start_new_session=True,
    )
    return int(process.pid or 0)


def ensure_stt_worker_process(model_name: str = "", language: str = "", preload: bool = False) -> dict:
    health = stt_worker_health(timeout=0.8)
    if health:
        if preload:
            try:
                stt_worker_request(
                    "/preload",
                    {"model_name": clean(model_name) or SERVER_STATE.get("model_name", "small"), "language": clean(language) or SERVER_STATE.get("language", "en")},
                    timeout=1.2,
                )
            except Exception as exc:
                SERVER_STATE.update({"worker_last_error": str(exc)})
        return health
    if not STT_WORKER_SCRIPT.is_file():
        raise RuntimeError(f"STT worker script not found: {STT_WORKER_SCRIPT}")
    cmd = [
        sys.executable or "python",
        "-B",
        str(STT_WORKER_SCRIPT),
        "--host",
        STT_WORKER_HOST,
        "--port",
        str(STT_WORKER_PORT),
        "--model",
        clean(model_name) or SERVER_STATE.get("model_name", "small"),
        "--language",
        clean(language) or SERVER_STATE.get("language", "en"),
    ]
    if preload:
        cmd.append("--preload")
    worker_pid = start_detached_stt_worker_process(cmd)
    write_stt_worker_pid(worker_pid)
    SERVER_STATE.update({"worker_pid": worker_pid, "worker_url": STT_WORKER_URL, "worker_loading": bool(preload)})
    for _attempt in range(20):
        time.sleep(0.15)
        health = stt_worker_health(timeout=0.6)
        if health:
            return health
    return {"ok": True, "started": True, "pid": worker_pid, "ready": False, "loading": bool(preload)}


def submit_worker_transcription(audio_path: str, model_name: str, language: str, expected: str = "", preferred_user: str = "") -> dict:
    started_at = time.time()
    try:
        remote_result = distributed_worker_try_stt(
            audio_path,
            model_name,
            language,
            expected,
            timeout_seconds=max(30.0, float(STT_JOB_TIMEOUT_SECONDS or 0) or 0.0) + 30.0,
            preferred_user=preferred_user,
        )
        if remote_result:
            remote_result.setdefault("job_id", uuid.uuid4().hex[:12])
            remote_result.setdefault("queue_position", 1)
            remote_result.setdefault("queue_wait_ms", 0)
            remote_result.setdefault("queue_process_ms", int(max(0.0, time.time() - started_at) * 1000))
            return remote_result
    except Exception as exc:
        stt_debug_log("distributed_stt_fallback", error=str(exc))
    ensure_stt_worker_process(model_name, language, preload=True)
    result = stt_worker_request(
        "/transcribe",
        {
            "audio_path": audio_path,
            "model_name": model_name,
            "language": language,
            "expected": expected,
        },
        timeout=max(30.0, float(STT_JOB_TIMEOUT_SECONDS or 0) or 0.0) + 30.0,
    )
    sync_stt_worker_state(result)
    result.setdefault("job_id", uuid.uuid4().hex[:12])
    result.setdefault("queue_position", 1)
    result.setdefault("queue_wait_ms", 0)
    result.setdefault("queue_process_ms", int(max(0.0, time.time() - started_at) * 1000))
    return result


def build_speech_reference_payload_worker(text: str) -> dict:
    ensure_stt_worker_process(SERVER_STATE.get("model_name", "small"), SERVER_STATE.get("language", "en"), preload=False)
    result = stt_worker_request("/reference", {"text": text}, timeout=45.0)
    sync_stt_worker_state(result)
    payload = result.get("speech_training")
    if not isinstance(payload, dict):
        raise RuntimeError("STT worker did not return speech reference data.")
    return payload


def similarity(a: str, b: str) -> float:
    aa = clean(a).lower()
    bb = clean(b).lower()
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 100.0
    return difflib.SequenceMatcher(None, aa, bb).ratio() * 100.0


# Added 2026-07-07: keeps STT grading strict enough that short or fuzzy words do not all pass.
def speech_token_match_ok(expected_word: str, spoken_word: str, score: float) -> bool:
    expected_norm = clean(expected_word).lower()
    spoken_norm = clean(spoken_word).lower()
    if not expected_norm or not spoken_norm:
        return False
    if expected_norm == spoken_norm:
        return True
    if len(expected_norm) <= 3:
        return False
    if len(expected_norm) <= 5:
        return float(score or 0.0) >= 92.0
    return float(score or 0.0) >= 88.0


def speech_training_token_analysis(expected_text: str, expected_words: list[str]) -> tuple[list[dict], dict]:
    expected = list(expected_words or [])
    analysis_rows: list[dict] = [{} for _ in expected]
    payload = {"primary_words": [], "secondary_words": [], "low_words": [], "analyzer": ""}
    if not expected:
        return analysis_rows, payload

    def _occurrence_key(norm: str, counters: dict[str, int]) -> tuple[str, int]:
        idx = int(counters.get(norm, 0) or 0)
        counters[norm] = idx + 1
        return norm, idx

    qmwrite_by_occ: dict[tuple[str, int], dict] = {}
    stress_by_occ: dict[tuple[str, int], dict] = {}
    try:
        configure_paths()
        from module_main.QMWrite.ScoringDef import analyze_sentence_data
        analyzed = analyze_sentence_data(expected_text, {}) or []
        counters: dict[str, int] = {}
        for item in list(analyzed or []):
            if not isinstance(item, dict):
                continue
            token_words = normalize_words(clean(item.get("text", "")))
            if len(token_words) != 1:
                continue
            qmwrite_by_occ[_occurrence_key(token_words[0], counters)] = {
                "surface": clean(item.get("text", "")),
                "lemma": clean(item.get("lemma", "")),
                "pos": clean(item.get("pos", "")),
                "dep": clean(item.get("dep", "")),
                "head": clean(item.get("head", "")),
                "head_pos": clean(item.get("head_pos", "")),
                "viet": clean(item.get("viet", "") or item.get("dict_meaning", "")),
                "verb_type": clean(item.get("verb_type", "")),
                "count_type": clean(item.get("count_type", "")),
            }
        payload["analyzer"] = "qmwrite-spacy"
    except Exception as exc:
        payload["analyzer_error"] = clean(exc)

    try:
        configure_paths()
        from module_main.SentenceMean.SentenceMean_stress_cache import analyze_sentence_stress_targets
        stress_info = dict(analyze_sentence_stress_targets(expected_text) or {})
        payload["primary_words"] = [clean(x) for x in list(stress_info.get("primary_words", []) or []) if clean(x)]
        payload["secondary_words"] = [clean(x) for x in list(stress_info.get("secondary_words", []) or []) if clean(x)]
        payload["low_words"] = [clean(x) for x in list(stress_info.get("low_words", []) or []) if clean(x)]
        counters = {}
        for item in list(stress_info.get("items", []) or []):
            if not isinstance(item, dict):
                continue
            norm = clean(item.get("norm", "")) or (normalize_words(clean(item.get("surface", ""))) or [""])[0]
            if not norm:
                continue
            stress_by_occ[_occurrence_key(norm, counters)] = {
                "stress_level": clean(item.get("importance", "")),
                "stress_score": round(float(item.get("stress_score", 0.0) or 0.0), 2),
                "stress_pos": clean(item.get("pos", "")),
                "stress_dep": clean(item.get("dep", "")),
                "is_function": bool(item.get("is_function", False)),
            }
    except Exception as exc:
        payload["stress_error"] = clean(exc)

    counters = {}
    for idx, word in enumerate(expected):
        key = _occurrence_key(clean(word).lower(), counters)
        merged = {}
        merged.update(qmwrite_by_occ.get(key, {}))
        merged.update(stress_by_occ.get(key, {}))
        if not clean(merged.get("stress_level", "")) and bool(merged.get("is_function", False)):
            merged["stress_level"] = "low"
        analysis_rows[idx] = merged
    return analysis_rows, payload


# Added 2026-07-01: sends spaCy/QMWrite speech metadata analysis to its own process queue.
def speech_training_token_analysis_queued(expected_text: str, expected_words: list[str]) -> tuple[list[dict], dict]:
    expected = list(expected_words or [])
    if not expected:
        return [], {"primary_words": [], "secondary_words": [], "low_words": [], "analyzer": ""}
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import speech_training_token_analysis_worker

    result = SPACY_WORK_QUEUE.run(
        f"speech-analysis:{len(expected)}",
        speech_training_token_analysis_worker,
        expected_text,
        expected,
        timeout=SPACY_WORK_QUEUE.timeout_seconds,
    )
    if isinstance(result, (tuple, list)) and len(result) == 2:
        rows, payload = result
        return list(rows or []), dict(payload or {})
    return speech_training_token_analysis(expected_text, expected)


def build_speech_training_payload(expected_text: str, spoken_text: str, rows: list[dict]) -> dict:
    expected_words = [clean(row.get("expected", "")) for row in list(rows or []) if clean(row.get("expected", ""))]
    try:
        analysis_rows, analysis_payload = speech_training_token_analysis_queued(expected_text, expected_words)
    except Exception as exc:
        analysis_rows = [{} for _ in expected_words]
        analysis_payload = {
            "primary_words": [],
            "secondary_words": [],
            "low_words": [],
            "analyzer": "",
            "analyzer_error": clean(exc),
        }
    for idx, row in enumerate(list(rows or [])):
        extra = analysis_rows[idx] if idx < len(analysis_rows) and isinstance(analysis_rows[idx], dict) else {}
        for key, value in extra.items():
            if value not in ("", None, [], {}):
                row[key] = value
    weak_rows = [row for row in list(rows or []) if not bool(row.get("ok"))]
    primary = [clean(x) for x in list(analysis_payload.get("primary_words", []) or []) if clean(x)]
    secondary = [clean(x) for x in list(analysis_payload.get("secondary_words", []) or []) if clean(x)]
    low = [clean(x) for x in list(analysis_payload.get("low_words", []) or []) if clean(x)]
    correct = sum(1 for row in list(rows or []) if bool(row.get("ok")))
    total = len(rows or [])
    lines = [
        f"Độ khớp lời đọc: {correct}/{max(1, total)} từ. Từ màu đỏ là phần cần đọc lại rõ hơn.",
    ]
    def _word_label(items: list[str]) -> str:
        return "từ" if len(items) == 1 else "các từ"

    def _word_list(items: list[str], limit: int = 8) -> str:
        return ", ".join([clean(x) for x in list(items or []) if clean(x)][:limit])

    primary_ok = []
    primary_need = []
    secondary_ok = []
    secondary_need = []
    light_ok = []
    light_need = []
    for row in list(rows or []):
        expected = clean(row.get("expected", ""))
        if not expected:
            continue
        level = clean(row.get("stress_level", ""))
        ok = bool(row.get("ok"))
        if level == "primary":
            (primary_ok if ok else primary_need).append(expected)
        elif level == "secondary":
            (secondary_ok if ok else secondary_need).append(expected)
        elif level == "low":
            (light_ok if ok else light_need).append(expected)

    if primary:
        lines.append(f"Trọng âm chính nên rơi vào {_word_label(primary)} {_word_list(primary, 6)}.")
    if primary_ok:
        all_primary_ok = bool(primary) and not primary_need
        suffix = " Rất tốt." if all_primary_ok else ""
        lines.append(f"Bạn đã nhấn đúng {_word_label(primary_ok)} {_word_list(primary_ok)}.{suffix}")
    if primary_need:
        lines.append(f"Tuy nhiên, với {_word_label(primary_need)} {_word_list(primary_need)}, bạn nên tăng lực nhấn và làm rõ âm tiết mang trọng âm hơn.")

    if secondary:
        lines.append(f"Trọng âm phụ cần nhẹ hơn trọng âm chính nhưng vẫn có độ nổi ở {_word_label(secondary)} {_word_list(secondary, 6)}.")
    if secondary_ok:
        all_secondary_ok = bool(secondary) and not secondary_need
        suffix = " Rất ổn." if all_secondary_ok else ""
        lines.append(f"Bạn đã giữ được độ nhấn phụ ở {_word_label(secondary_ok)} {_word_list(secondary_ok)}.{suffix}")
    if secondary_need:
        lines.append(f"Còn {_word_label(secondary_need)} {_word_list(secondary_need)} nên được nâng vừa phải, không mạnh bằng trọng âm chính nhưng cũng không đọc lướt mất.")

    if low:
        lines.append(f"Nhóm cần đọc nhẹ và ngắn hơn gồm {_word_label(low)} {_word_list(low, 8)}.")
    if light_ok:
        all_light_ok = bool(low) and not light_need
        suffix = " Rất tốt." if all_light_ok else ""
        lines.append(f"Bạn đã xử lý gọn và nhẹ ở {_word_label(light_ok)} {_word_list(light_ok)}.{suffix}")
    if light_need:
        lines.append(f"Còn {_word_label(light_need)} {_word_list(light_need)} cần đọc ngắn hơn, lướt nhẹ hơn và tránh kéo dài.")
    if weak_rows:
        focus = []
        for row in weak_rows[:8]:
            expected = clean(row.get("expected", ""))
            heard = clean(row.get("spoken", ""))
            pos = clean(row.get("pos", ""))
            chunk = expected
            if heard:
                chunk += f" (máy nghe: {heard})"
            if pos:
                chunk += f" [{pos}]"
            focus.append(chunk)
        lines.append("Cần luyện lại: " + "; ".join(focus) + ".")
    else:
        lines.append("Các từ chính đã được nhận diện rõ. Giữ nhịp đọc đều và không nuốt âm cuối.")
    transcript_tokens = []
    matched_spoken = set()
    spoken_ok: dict[int, bool] = {}
    for row in list(rows or []):
        spoken_index = int(row.get("spoken_index", -1) if row.get("spoken_index", -1) is not None else -1)
        if spoken_index >= 0:
            matched_spoken.add(spoken_index)
            spoken_ok[spoken_index] = bool(row.get("ok"))
    spoken_words = normalize_words(spoken_text)
    expected_by_spoken = {}
    meta_by_spoken = {}
    for row in list(rows or []):
        spoken_index = int(row.get("spoken_index", -1) if row.get("spoken_index", -1) is not None else -1)
        if spoken_index >= 0:
            expected_by_spoken[spoken_index] = clean(row.get("expected", ""))
            meta_by_spoken[spoken_index] = {
                "stress_level": clean(row.get("stress_level", "")),
                "pos": clean(row.get("pos", "")),
                "dep": clean(row.get("dep", "")),
                "ipa": clean(row.get("ipa_uk", "") or row.get("ipa_us", "") or row.get("ipa", "")),
            }
    for idx, word in enumerate(spoken_words):
        meta = meta_by_spoken.get(idx, {})
        transcript_tokens.append(
            {
                "word": word,
                "ok": bool(spoken_ok.get(idx, False)),
                "extra": idx not in matched_spoken,
                "expected": expected_by_spoken.get(idx, "extra" if idx not in matched_spoken else ""),
                "label": expected_by_spoken.get(idx, "matched") if idx in matched_spoken else "extra",
                **meta,
            }
        )
    reference_tokens = []
    for row in list(rows or []):
        reference_tokens.append(
            {
                "expected": clean(row.get("expected", "")),
                "spoken": clean(row.get("spoken", "")),
                "ok": bool(row.get("ok")),
                "similarity": row.get("similarity", 0),
                "ipa": clean(row.get("ipa", "")),
                "ipa_us": clean(row.get("ipa_us", "")),
                "ipa_uk": clean(row.get("ipa_uk", "")),
                "pos": clean(row.get("pos", "")),
                "dep": clean(row.get("dep", "")),
                "lemma": clean(row.get("lemma", "")),
                "viet": clean(row.get("viet", "")),
                "stress_level": clean(row.get("stress_level", "")),
                "stress_score": row.get("stress_score", 0),
            }
        )
    ipa_text = " ".join(
        f"/{clean(row.get('ipa_uk', '') or row.get('ipa_us', '') or row.get('ipa', ''))}/"
        for row in list(rows or [])
        if clean(row.get("ipa_uk", "") or row.get("ipa_us", "") or row.get("ipa", ""))
    )
    return {
        "reference_text": clean(expected_text),
        "ipa_text": ipa_text,
        "lines_vi": lines,
        "reference_tokens": reference_tokens,
        "transcript_tokens": transcript_tokens,
        "primary_words": primary,
        "secondary_words": secondary,
        "low_words": low,
        "analyzer": clean(analysis_payload.get("analyzer", "")),
        "analyzer_error": clean(analysis_payload.get("analyzer_error", "")),
        "stress_error": clean(analysis_payload.get("stress_error", "")),
    }


def build_speech_reference_payload(reference_text: str) -> dict:
    expected = normalize_words(reference_text)
    rows = [
        {
            "expected": word,
            "spoken": "",
            "spoken_index": -1,
            "ok": False,
            "similarity": 0,
            "start_ms": 0,
            "end_ms": 0,
        }
        for word in expected
    ]
    try:
        ipa_map = phonetic_ipa_map_for_terms_queued(expected, generate_missing=True, schedule_missing=False)
    except Exception:
        ipa_map = {}
    for row in rows:
        ipa_row = ipa_map.get(phonetic_ipa_key(row.get("expected", "")), {})
        if isinstance(ipa_row, dict) and ipa_row:
            row["ipa"] = clean(ipa_row.get("ipa", ""))
            row["ipa_us"] = clean(ipa_row.get("ipa_us", ""))
            row["ipa_uk"] = clean(ipa_row.get("ipa_uk", ""))
    return build_speech_training_payload(reference_text, "", rows)


def score_spoken(expected_text: str, spoken_text: str, timeline_words: list[dict]) -> dict:
    expected = normalize_words(expected_text)
    spoken = normalize_words(spoken_text)
    timeline = list(timeline_words or [])
    rows = []
    used = set()
    exact = difflib.SequenceMatcher(None, expected, spoken)
    for tag, i1, i2, j1, j2 in exact.get_opcodes():
        if tag == "equal":
            for gi, sj in zip(range(i1, i2), range(j1, j2)):
                used.add(sj)
    for gi, word in enumerate(expected):
        best = None
        for sj, spoken_word in enumerate(spoken):
            if sj in used and spoken_word != word:
                continue
            score = similarity(word, spoken_word)
            position_penalty = max(0.0, abs(gi - sj) * 9.0)
            value = score - position_penalty
            if best is None or value > best[0]:
                best = (value, score, sj, spoken_word)
        ok = bool(best and speech_token_match_ok(word, best[3], best[1]))
        spoken_index = int(best[2]) if best else -1
        if ok and spoken_index >= 0:
            used.add(spoken_index)
        timing = timeline[spoken_index] if 0 <= spoken_index < len(timeline) and isinstance(timeline[spoken_index], dict) else {}
        rows.append(
            {
                "expected": word,
                "spoken": best[3] if best else "",
                "spoken_index": spoken_index,
                "ok": ok,
                "similarity": round(float(best[1] if best else 0.0), 2),
                "start_ms": timing.get("start_ms", 0),
                "end_ms": timing.get("end_ms", 0),
            }
        )
    try:
        ipa_map = phonetic_ipa_map_for_terms_queued(expected, generate_missing=True, schedule_missing=False)
    except Exception:
        ipa_map = {}
    for row in rows:
        ipa_row = ipa_map.get(phonetic_ipa_key(row.get("expected", "")), {})
        if isinstance(ipa_row, dict) and ipa_row:
            row["ipa"] = clean(ipa_row.get("ipa", ""))
            row["ipa_us"] = clean(ipa_row.get("ipa_us", ""))
            row["ipa_uk"] = clean(ipa_row.get("ipa_uk", ""))
            row["stress"] = "'" in row["ipa"] or "'" in row["ipa_us"] or "'" in row["ipa_uk"] or "ˈ" in row["ipa"] or "ˈ" in row["ipa_us"] or "ˈ" in row["ipa_uk"]
    correct = sum(1 for row in rows if row.get("ok"))
    score = round((correct / max(1, len(expected))) * 100.0, 2)
    extra = max(0, len(spoken) - len([row for row in rows if row.get("spoken")]))
    missing = [row.get("expected", "") for row in rows if not row.get("ok")]
    if score >= 92:
        feedback = "Excellent shadowing. Rhythm and word coverage are strong."
    elif score >= 78:
        feedback = "Good speaking. Repeat the highlighted weak words once more."
    elif score >= 55:
        feedback = "Readable, but several words need clearer pronunciation."
    else:
        feedback = "Try again slowly, one phrase at a time."
    speech_training = build_speech_training_payload(expected_text, spoken_text, rows)
    return {
        "score": score,
        "correct": correct,
        "total": len(expected),
        "extra_words": extra,
        "missing_words": missing[:8],
        "details": rows,
        "feedback": feedback,
        "speech_training": speech_training,
    }
