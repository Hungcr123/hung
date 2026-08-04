# Loaded after the RAM distributed-worker broker into the shared Server 2 namespace.

DURABLE_TTS_QUEUE_CONDITION = threading.Condition(threading.RLock())
DURABLE_TTS_QUEUE_STOP = threading.Event()
DURABLE_TTS_QUEUE_THREADS: list[threading.Thread] = []
DURABLE_TTS_COORDINATOR_THREAD: threading.Thread | None = None
DURABLE_TTS_EXECUTION_QUEUE: list[dict] = []
DURABLE_TTS_EXECUTION_ACTIVE = 0
DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY = {1: 0, 2: 0, 3: 0}
DURABLE_TTS_QUEUE_STARTED = False
DURABLE_TTS_QUEUE_CLAIM_COUNT = 0
DURABLE_TTS_BACKGROUND_THROTTLE_EVENTS = 0
DURABLE_TTS_BACKGROUND_THROTTLE_LAST_REASON = ""
DURABLE_TTS_QUEUE_OWNER = f"server2-{os.getpid()}-{uuid.uuid4().hex[:8]}"
DURABLE_TTS_ARTIFACT_ROOT = SERVER_DATA_ROOT / "_future_runtime" / "tts_job_artifacts"
DURABLE_TTS_METRICS_CACHE = {"at": 0.0, "value": {}}


def durable_tts_queue_worker_count() -> int:
    try:
        value = int(os.environ.get("FUTURE_DURABLE_TTS_DISPATCHERS", "4") or 4)
    except Exception:
        value = 4
    return max(1, min(128, value))


def durable_tts_desired_dispatcher_count() -> int:
    try:
        live_capacity = int(distributed_worker_effective_job_limit("tts") or 0)
    except Exception:
        live_capacity = 0
    return max(durable_tts_queue_worker_count(), min(128, live_capacity))


# Added 2026-08-01: keep a bounded share of TTS lanes available for learner-facing jobs.
def durable_tts_interactive_reserve(worker_count: int | None = None) -> int:
    workers = max(1, int(worker_count or durable_tts_desired_dispatcher_count()))
    raw = clean(os.environ.get("FUTURE_DURABLE_TTS_INTERACTIVE_RESERVE", ""))
    try:
        reserve = int(float(raw)) if raw else (workers + 3) // 4
    except Exception:
        reserve = (workers + 3) // 4
    return max(0, min(16, workers - 1, reserve))


# Added 2026-08-03: cap P3 work to a small residual share so already-claimed
# background TTS cannot occupy every CPU/worker lane when learners arrive.
def durable_tts_background_concurrency_limit(worker_count: int | None = None) -> int:
    workers = max(1, int(worker_count or durable_tts_desired_dispatcher_count()))
    reserve = durable_tts_interactive_reserve(workers)
    raw = clean(os.environ.get("FUTURE_DURABLE_TTS_BACKGROUND_MAX_ACTIVE", ""))
    try:
        configured = int(float(raw)) if raw else 0
    except Exception:
        configured = 0
    default_limit = max(1, workers // 4)
    limit = configured if configured > 0 else default_limit
    return max(0, min(16, workers - reserve, limit))


# Added 2026-08-02: keep P3 TTS from claiming new work while learners or high CPU are active.
def durable_tts_background_throttle_state() -> dict:
    httpd = globals().get("SERVER_HTTPD")
    active_requests = max(0, int(getattr(httpd, "_future_active_requests", 0) or 0))
    active_builder = max(0, int(getattr(httpd, "_future_active_builder_requests", 0) or 0))
    learner_requests = max(0, active_requests - active_builder)
    cpu_percent = 0.0
    guard_enabled = True
    threshold = 90
    cpu_reader = globals().get("current_system_cpu_percent")
    guard_reader = globals().get("cpu_guard_settings_snapshot")
    try:
        if callable(cpu_reader):
            cpu_percent = float(cpu_reader() or 0.0)
    except Exception:
        cpu_percent = 0.0
    try:
        guard = guard_reader() if callable(guard_reader) else {}
        guard_enabled = bool(guard.get("enabled", True))
        threshold = int(guard.get("threshold", 90) or 90)
    except Exception:
        pass
    cpu_high = guard_enabled and cpu_percent >= threshold
    reasons = []
    if learner_requests > 0:
        reasons.append("learner_requests")
    if cpu_high:
        reasons.append("cpu_high")
    return {
        "throttled": bool(reasons),
        "reason": "+".join(reasons),
        "cpu_high": cpu_high,
        "learner_requests": learner_requests,
        "active_requests": active_requests,
        "active_builder_requests": active_builder,
        "cpu_percent": round(cpu_percent, 1),
        "cpu_threshold": threshold,
    }


# Added 2026-07-31: grow durable dispatch lanes when more distributed TTS slots connect.
def durable_tts_ensure_dispatcher_capacity() -> int:
    global DURABLE_TTS_COORDINATOR_THREAD
    with DURABLE_TTS_QUEUE_CONDITION:
        if not DURABLE_TTS_QUEUE_STARTED:
            return len(DURABLE_TTS_QUEUE_THREADS)
        if not DURABLE_TTS_COORDINATOR_THREAD or not DURABLE_TTS_COORDINATOR_THREAD.is_alive():
            DURABLE_TTS_COORDINATOR_THREAD = threading.Thread(
                target=durable_tts_claim_coordinator_loop,
                name="durable-tts-coordinator",
                daemon=True,
            )
            DURABLE_TTS_COORDINATOR_THREAD.start()
        desired = durable_tts_desired_dispatcher_count()
        while len(DURABLE_TTS_QUEUE_THREADS) < desired:
            index = len(DURABLE_TTS_QUEUE_THREADS) + 1
            thread = threading.Thread(target=durable_tts_dispatch_loop, args=(index,), name=f"durable-tts-{index}", daemon=True)
            DURABLE_TTS_QUEUE_THREADS.append(thread)
            thread.start()
        DURABLE_TTS_QUEUE_CONDITION.notify_all()
        return len(DURABLE_TTS_QUEUE_THREADS)


def durable_tts_queue_lease_seconds() -> float:
    try:
        value = float(os.environ.get("FUTURE_DURABLE_TTS_LEASE_SECONDS", "180") or 180)
    except Exception:
        value = 180.0
    return max(30.0, min(900.0, value))


def durable_tts_canonical_params(params: dict | None = None) -> dict:
    source = params if isinstance(params, dict) else {}
    return {
        clean(key): source[key]
        for key in sorted(source)
        if clean(key) and not clean(key).startswith("_")
    }


def durable_tts_dedupe_key(text: str, voice: str, params: dict | None = None, output_key: str = "") -> str:
    payload = json.dumps(
        {
            "text": str(text or ""),
            "voice": clean(voice).lower(),
            "params": durable_tts_canonical_params(params),
            "output_key": clean(output_key),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def durable_tts_artifact_path(dedupe_key: str) -> Path:
    safe_key = clean(dedupe_key).lower()
    return DURABLE_TTS_ARTIFACT_ROOT / safe_key[:2] / f"{safe_key}.audio"


def durable_tts_json_value(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def durable_tts_row(cursor, row) -> dict:
    if not row:
        return {}
    columns = [clean(item.name if hasattr(item, "name") else item[0]) for item in cursor.description]
    result = dict(zip(columns, row))
    result["params_json"] = durable_tts_json_value(result.get("params_json"))
    result["result_json"] = durable_tts_json_value(result.get("result_json"))
    return result


def durable_tts_enqueue(
    text: str,
    voice: str,
    *,
    priority: int = 1,
    source: str = "runtime_voice",
    preferred_user: str = "",
    build_id: str = "",
    params: dict | None = None,
    output_key: str = "",
    max_attempts: int = 5,
) -> dict:
    source_text = str(text or "").strip()
    normalized_voice = clean(voice)
    if not source_text or not normalized_voice:
        raise RuntimeError("Missing TTS text or voice.")
    safe_priority = max(1, min(3, int(priority or 1)))
    safe_params = durable_tts_canonical_params(params)
    dedupe_key = durable_tts_dedupe_key(source_text, normalized_voice, safe_params, output_key)
    job_id = f"tts-{dedupe_key[:24]}"
    now = time.time()

    def _enqueue(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.tts_jobs (
                    job_id, dedupe_key, output_key, priority, source, status,
                    text_payload, voice, params_json, request_user, build_id,
                    max_attempts, created_epoch, updated_epoch
                ) VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                ON CONFLICT (dedupe_key) DO UPDATE SET
                    priority = LEAST(future_server2.tts_jobs.priority, EXCLUDED.priority),
                    source = CASE
                        WHEN EXCLUDED.priority < future_server2.tts_jobs.priority THEN EXCLUDED.source
                        ELSE future_server2.tts_jobs.source
                    END,
                    request_user = CASE WHEN EXCLUDED.request_user <> '' THEN EXCLUDED.request_user ELSE future_server2.tts_jobs.request_user END,
                    build_id = CASE WHEN EXCLUDED.build_id <> '' THEN EXCLUDED.build_id ELSE future_server2.tts_jobs.build_id END,
                    status = CASE
                        WHEN future_server2.tts_jobs.status IN ('failed', 'cancelled') THEN 'queued'
                        ELSE future_server2.tts_jobs.status
                    END,
                    attempt_count = CASE
                        WHEN future_server2.tts_jobs.status IN ('failed', 'cancelled') THEN 0
                        ELSE future_server2.tts_jobs.attempt_count
                    END,
                    next_retry_epoch = CASE
                        WHEN future_server2.tts_jobs.status IN ('failed', 'cancelled') THEN 0
                        ELSE future_server2.tts_jobs.next_retry_epoch
                    END,
                    last_error = CASE
                        WHEN future_server2.tts_jobs.status IN ('failed', 'cancelled') THEN ''
                        ELSE future_server2.tts_jobs.last_error
                    END,
                    updated_epoch = EXCLUDED.updated_epoch
                RETURNING *
                """,
                (
                    job_id, dedupe_key, clean(output_key), safe_priority, clean(source)[:80],
                    source_text, normalized_voice, json.dumps(safe_params, ensure_ascii=False, separators=(",", ":")),
                    clean(preferred_user).lower()[:120], clean(build_id)[:160],
                    max(1, min(20, int(max_attempts or 5))), now, now,
                ),
            )
            return durable_tts_row(cursor, cursor.fetchone())

    job = postgres_execute(_enqueue)
    with DURABLE_TTS_QUEUE_CONDITION:
        DURABLE_TTS_QUEUE_CONDITION.notify_all()
    durable_tts_ensure_dispatcher_capacity()
    return job


def durable_tts_recover_expired() -> int:
    now = time.time()

    def _recover(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET status = CASE WHEN attempt_count >= max_attempts THEN 'failed' ELSE 'retry_wait' END,
                    leased_by = '', lease_token = '', lease_expires_epoch = 0,
                    next_retry_epoch = CASE WHEN attempt_count >= max_attempts THEN 0 ELSE %s END,
                    updated_epoch = %s,
                    last_error = CASE WHEN last_error = '' THEN 'Lease expired before completion.' ELSE last_error END
                WHERE status IN ('leased', 'publishing') AND lease_expires_epoch > 0 AND lease_expires_epoch <= %s
                """,
                (now + 1.0, now, now),
            )
            return int(cursor.rowcount or 0)

    return int(postgres_execute(_recover) or 0)


def durable_tts_claim(owner: str, background_turn: bool = False) -> dict:
    now = time.time()
    lease_token = uuid.uuid4().hex
    lease_expires = now + durable_tts_queue_lease_seconds()
    priority_order = "CASE WHEN priority = 3 THEN 0 ELSE 1 END," if background_turn else ""

    def _claim(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH candidate AS (
                    SELECT job_id
                    FROM future_server2.tts_jobs
                    WHERE status IN ('queued', 'retry_wait')
                      AND next_retry_epoch <= %s
                    ORDER BY {priority_order} priority ASC, created_epoch ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE future_server2.tts_jobs AS jobs
                SET status = 'leased', leased_by = %s, lease_token = %s,
                    lease_expires_epoch = %s, heartbeat_epoch = %s,
                    attempt_count = attempt_count + 1,
                    started_epoch = CASE WHEN started_epoch <= 0 THEN %s ELSE started_epoch END,
                    updated_epoch = %s, last_error = ''
                FROM candidate
                WHERE jobs.job_id = candidate.job_id
                RETURNING jobs.*
                """,
                (now, clean(owner)[:120], lease_token, lease_expires, now, now, now),
            )
            return durable_tts_row(cursor, cursor.fetchone())

    return postgres_execute(_claim)


# Added 2026-07-31: one coordinator batches durable claims before executor threads run jobs.
def durable_tts_claim_batch(owner: str, limit: int, background_turn: bool = False) -> list[dict]:
    safe_limit = max(1, min(32, int(limit or 1)))
    now = time.time()
    lease_token_prefix = uuid.uuid4().hex
    lease_expires = now + durable_tts_queue_lease_seconds()
    priority_order = "CASE WHEN priority = 3 THEN 0 ELSE 1 END," if background_turn else ""

    def _claim(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH candidates AS (
                    SELECT job_id
                    FROM future_server2.tts_jobs
                    WHERE status IN ('queued', 'retry_wait')
                      AND next_retry_epoch <= %s
                    ORDER BY {priority_order} priority ASC, created_epoch ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT %s
                )
                UPDATE future_server2.tts_jobs AS jobs
                SET status = 'leased', leased_by = %s, lease_token = %s || jobs.job_id,
                    lease_expires_epoch = %s, heartbeat_epoch = %s,
                    attempt_count = jobs.attempt_count + 1,
                    started_epoch = CASE WHEN jobs.started_epoch <= 0 THEN %s ELSE jobs.started_epoch END,
                    updated_epoch = %s, last_error = ''
                FROM candidates
                WHERE jobs.job_id = candidates.job_id
                RETURNING jobs.*
                """,
                (now, safe_limit, clean(owner)[:120], lease_token_prefix, lease_expires, now, now, now),
            )
            return [durable_tts_row(cursor, row) for row in cursor.fetchall()]

    return list(postgres_execute(_claim) or [])


# Added 2026-08-01: claim interactive jobs first while capping builder leases in one transaction.
def durable_tts_claim_capacity_batch(owner: str, available: int, background_capacity: int) -> list[dict]:
    safe_available = max(1, min(32, int(available or 1)))
    safe_background = max(0, min(safe_available, int(background_capacity or 0)))
    now = time.time()
    lease_token_prefix = uuid.uuid4().hex
    lease_expires = now + durable_tts_queue_lease_seconds()

    def _claim(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH interactive AS (
                    SELECT job_id
                    FROM future_server2.tts_jobs
                    WHERE status IN ('queued', 'retry_wait')
                      AND next_retry_epoch <= %s
                      AND priority < 3
                    ORDER BY priority ASC, created_epoch ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT %s
                ),
                background AS (
                    SELECT job_id
                    FROM future_server2.tts_jobs
                    WHERE status IN ('queued', 'retry_wait')
                      AND next_retry_epoch <= %s
                      AND priority = 3
                    ORDER BY created_epoch ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT LEAST(%s, GREATEST(0, %s - (SELECT COUNT(*) FROM interactive)))
                ),
                candidates AS (
                    SELECT job_id FROM interactive
                    UNION ALL
                    SELECT job_id FROM background
                )
                UPDATE future_server2.tts_jobs AS jobs
                SET status = 'leased', leased_by = %s, lease_token = %s || jobs.job_id,
                    lease_expires_epoch = %s, heartbeat_epoch = %s,
                    attempt_count = jobs.attempt_count + 1,
                    started_epoch = CASE WHEN jobs.started_epoch <= 0 THEN %s ELSE jobs.started_epoch END,
                    updated_epoch = %s, last_error = ''
                FROM candidates
                WHERE jobs.job_id = candidates.job_id
                RETURNING jobs.*
                """,
                (
                    now,
                    safe_available,
                    now,
                    safe_background,
                    safe_available,
                    clean(owner)[:120],
                    lease_token_prefix,
                    lease_expires,
                    now,
                    now,
                    now,
                ),
            )
            rows = [durable_tts_row(cursor, row) for row in cursor.fetchall()]
            return sorted(rows, key=lambda row: (int(row.get("priority", 3) or 3), float(row.get("created_epoch", 0) or 0)))

    return list(postgres_execute(_claim) or [])


def durable_tts_heartbeat(job_id: str, owner: str, lease_token: str) -> bool:
    now = time.time()

    def _heartbeat(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET heartbeat_epoch = %s, lease_expires_epoch = %s, updated_epoch = %s
                WHERE job_id = %s AND leased_by = %s AND lease_token = %s
                  AND status IN ('leased', 'publishing')
                """,
                (now, now + durable_tts_queue_lease_seconds(), now, job_id, owner, lease_token),
            )
            return cursor.rowcount == 1

    return bool(postgres_execute(_heartbeat))


def durable_tts_mark_publishing(
    job: dict,
    artifact_path: Path | None = None,
    checksum: str = "",
    size: int = 0,
    result: dict | None = None,
) -> bool:
    now = time.time()

    def _mark(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET status = 'publishing', heartbeat_epoch = %s, updated_epoch = %s,
                    artifact_path = CASE WHEN %s <> '' THEN %s ELSE artifact_path END,
                    artifact_sha256 = CASE WHEN %s <> '' THEN %s ELSE artifact_sha256 END,
                    artifact_size = CASE WHEN %s > 0 THEN %s ELSE artifact_size END,
                    result_json = CASE WHEN %s <> '{}' THEN %s::jsonb ELSE result_json END
                WHERE job_id = %s AND leased_by = %s AND lease_token = %s
                  AND status = 'leased' AND lease_expires_epoch > %s
                """,
                (
                    now, now,
                    str(artifact_path or ""), str(artifact_path or ""),
                    clean(checksum), clean(checksum), int(size or 0), int(size or 0),
                    json.dumps(result or {}, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(result or {}, ensure_ascii=False, separators=(",", ":")),
                    job.get("job_id"), job.get("leased_by"), job.get("lease_token"), now,
                ),
            )
            return cursor.rowcount == 1

    return bool(postgres_execute(_mark))


def durable_tts_complete(job: dict, artifact_path: Path, checksum: str, size: int, result: dict) -> bool:
    now = time.time()

    def _complete(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET status = 'completed', completed_epoch = %s, updated_epoch = %s,
                    leased_by = '', lease_token = '', lease_expires_epoch = 0,
                    artifact_path = %s, artifact_sha256 = %s, artifact_size = %s,
                    result_json = %s::jsonb, last_error = ''
                WHERE job_id = %s AND leased_by = %s AND lease_token = %s
                  AND status = 'publishing'
                """,
                (
                    now, now, str(artifact_path), clean(checksum), int(size or 0),
                    json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    job.get("job_id"), job.get("leased_by"), job.get("lease_token"),
                ),
            )
            return cursor.rowcount == 1

    completed = bool(postgres_execute(_complete))
    if completed:
        with DURABLE_TTS_QUEUE_CONDITION:
            DURABLE_TTS_QUEUE_CONDITION.notify_all()
    return completed


def durable_tts_mark_callback_applied(job_id: str) -> None:
    now = time.time()

    def _mark(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET result_json = result_json || '{"callback_applied":true}'::jsonb,
                    updated_epoch = %s
                WHERE job_id = %s AND status = 'completed'
                """,
                (now, clean(job_id)),
            )

    postgres_execute(_mark)


def durable_tts_apply_completion_hook(job: dict) -> bool:
    result_meta = durable_tts_json_value(job.get("result_json"))
    if result_meta.get("callback_applied"):
        return True
    hook = globals().get("space_pdf_ai_question_tts_completed")
    if clean(job.get("source", "")) != "admin_ai_question" or not callable(hook):
        return False
    ready = durable_tts_result(job)
    if not ready:
        return False
    hook(job, ready)
    durable_tts_mark_callback_applied(clean(job.get("job_id", "")))
    return True


def durable_tts_reconcile_callbacks(limit: int = 12) -> int:
    def _load(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM future_server2.tts_jobs
                WHERE status = 'completed' AND source = 'admin_ai_question'
                  AND COALESCE((result_json ->> 'callback_applied')::boolean, false) = false
                ORDER BY completed_epoch ASC
                LIMIT %s
                """,
                (max(1, min(50, int(limit or 12))),),
            )
            return [durable_tts_row(cursor, row) for row in cursor.fetchall()]

    applied = 0
    for row in postgres_execute(_load):
        try:
            if durable_tts_apply_completion_hook(row):
                applied += 1
        except Exception as exc:
            stt_debug_log("durable_tts_callback_failed", job_id=clean(row.get("job_id", "")), error=str(exc))
    return applied


def durable_tts_fail(job: dict, error: str) -> bool:
    now = time.time()
    attempts = int(job.get("attempt_count", 1) or 1)
    max_attempts = int(job.get("max_attempts", 5) or 5)
    terminal = attempts >= max_attempts
    retry_delay = min(60.0, (2.0 ** min(6, max(0, attempts - 1))) + random.random())

    def _fail(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET status = %s, next_retry_epoch = %s, updated_epoch = %s,
                    leased_by = '', lease_token = '', lease_expires_epoch = 0,
                    last_error = %s
                WHERE job_id = %s AND leased_by = %s AND lease_token = %s
                  AND status IN ('leased', 'publishing')
                """,
                (
                    "failed" if terminal else "retry_wait", 0 if terminal else now + retry_delay, now,
                    clean(error)[:2000], job.get("job_id"), job.get("leased_by"), job.get("lease_token"),
                ),
            )
            return cursor.rowcount == 1

    failed = bool(postgres_execute(_fail))
    if failed:
        with DURABLE_TTS_QUEUE_CONDITION:
            DURABLE_TTS_QUEUE_CONDITION.notify_all()
    return failed


def durable_tts_artifact_valid(job: dict) -> bool:
    path_text = clean(job.get("artifact_path", ""))
    expected_size = int(job.get("artifact_size", 0) or 0)
    expected_sha = clean(job.get("artifact_sha256", "")).lower()
    if not path_text or expected_size <= 0 or not expected_sha:
        return False
    path = Path(path_text)
    try:
        if not path.is_file() or path.stat().st_size != expected_size:
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha
    except OSError:
        return False


def durable_tts_publish(job: dict, audio_bytes: bytes, result: dict) -> bool:
    if not audio_bytes:
        raise RuntimeError("TTS worker returned empty audio.")
    artifact_path = durable_tts_artifact_path(job.get("dedupe_key", ""))
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(audio_bytes).hexdigest()
    temp_path = artifact_path.with_name(f".{artifact_path.name}.{job.get('lease_token', '')}.tmp")
    with temp_path.open("wb") as handle:
        handle.write(audio_bytes)
        handle.flush()
        os.fsync(handle.fileno())
    if not durable_tts_mark_publishing(job, artifact_path, checksum, len(audio_bytes), result):
        try:
            temp_path.unlink()
        except OSError:
            pass
        return False
    os.replace(temp_path, artifact_path)
    return durable_tts_complete(job, artifact_path, checksum, len(audio_bytes), result)


def durable_tts_execute_job(job: dict) -> None:
    job_id = clean(job.get("job_id", ""))
    owner = clean(job.get("leased_by", ""))
    token = clean(job.get("lease_token", ""))
    heartbeat_stop = threading.Event()

    def _heartbeat_loop() -> None:
        interval = max(10.0, durable_tts_queue_lease_seconds() / 3.0)
        while not heartbeat_stop.wait(interval):
            try:
                if not durable_tts_heartbeat(job_id, owner, token):
                    return
            except Exception as exc:
                stt_debug_log("durable_tts_heartbeat_failed", job_id=job_id, error=str(exc))

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, name=f"tts-heartbeat-{job_id[-8:]}", daemon=True)
    heartbeat_thread.start()
    try:
        if durable_tts_artifact_valid(job):
            path = Path(clean(job.get("artifact_path", "")))
            result = durable_tts_json_value(job.get("result_json"))
            if durable_tts_mark_publishing(job):
                durable_tts_complete(job, path, clean(job.get("artifact_sha256", "")), int(job.get("artifact_size", 0) or 0), result)
            return
        params = durable_tts_json_value(job.get("params_json"))
        raw = distributed_worker_try_tts_raw(
            str(job.get("text_payload", "") or ""),
            clean(job.get("voice", "")),
            timeout_seconds=float(params.get("timeout_seconds", 0) or 0),
            preferred_user=clean(job.get("request_user", "")),
            priority=int(job.get("priority", 1) or 1),
        )
        if not raw:
            raise RuntimeError("No compatible TTS worker is currently available.")
        audio_bytes = raw.get("audio_bytes") or b""
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise RuntimeError("TTS worker returned no audio bytes.")
        result = {
            "mime": clean(raw.get("audio_mime", raw.get("mime", ""))) or "audio/mpeg",
            "voice": clean(raw.get("voice", "")) or clean(job.get("voice", "")),
            "worker_id": clean(raw.get("worker_id", "")),
        }
        for key in ("duration_ms", "durationMs", "timing_tokens", "timingTokens", "timings"):
            if key in raw:
                result[key] = raw[key]
        if not durable_tts_publish(job, bytes(audio_bytes), result):
            raise RuntimeError("TTS lease changed before artifact publication.")
        completed_job = durable_tts_job(job_id)
        try:
            durable_tts_apply_completion_hook(completed_job)
        except Exception as exc:
            stt_debug_log("durable_tts_callback_failed", job_id=job_id, error=str(exc))
    except Exception as exc:
        try:
            durable_tts_fail(job, str(exc))
        except Exception as fail_exc:
            stt_debug_log("durable_tts_fail_update_failed", job_id=job_id, error=str(fail_exc))
    finally:
        heartbeat_stop.set()


def durable_tts_dispatch_loop(index: int) -> None:
    global DURABLE_TTS_EXECUTION_ACTIVE
    while not DURABLE_TTS_QUEUE_STOP.is_set():
        with DURABLE_TTS_QUEUE_CONDITION:
            while not DURABLE_TTS_EXECUTION_QUEUE and not DURABLE_TTS_QUEUE_STOP.is_set():
                DURABLE_TTS_QUEUE_CONDITION.wait(timeout=5.0)
            if DURABLE_TTS_QUEUE_STOP.is_set():
                return
            job = DURABLE_TTS_EXECUTION_QUEUE.pop(0)
            priority = max(1, min(3, int(job.get("priority", 1) or 1)))
            DURABLE_TTS_EXECUTION_ACTIVE += 1
            DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY[priority] = DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY.get(priority, 0) + 1
        try:
            durable_tts_execute_job(job)
        except Exception as exc:
            stt_debug_log("durable_tts_dispatch_error", dispatcher=index, error=str(exc))
        finally:
            with DURABLE_TTS_QUEUE_CONDITION:
                DURABLE_TTS_EXECUTION_ACTIVE = max(0, DURABLE_TTS_EXECUTION_ACTIVE - 1)
                DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY[priority] = max(
                    0,
                    DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY.get(priority, 0) - 1,
                )
                DURABLE_TTS_QUEUE_CONDITION.notify()


def durable_tts_claim_coordinator_loop() -> None:
    global DURABLE_TTS_QUEUE_CLAIM_COUNT, DURABLE_TTS_BACKGROUND_THROTTLE_EVENTS, DURABLE_TTS_BACKGROUND_THROTTLE_LAST_REASON
    owner = f"{DURABLE_TTS_QUEUE_OWNER}-coordinator"
    last_recovery = 0.0
    last_callback_reconcile = 0.0
    while not DURABLE_TTS_QUEUE_STOP.is_set():
        try:
            now = time.time()
            if now - last_recovery >= 5.0:
                durable_tts_recover_expired()
                last_recovery = now
            if now - last_callback_reconcile >= 5.0:
                durable_tts_reconcile_callbacks()
                last_callback_reconcile = now
            with DURABLE_TTS_QUEUE_CONDITION:
                available = max(
                    0,
                    len(DURABLE_TTS_QUEUE_THREADS)
                    - DURABLE_TTS_EXECUTION_ACTIVE
                    - len(DURABLE_TTS_EXECUTION_QUEUE),
                )
                if available <= 0:
                    DURABLE_TTS_QUEUE_CONDITION.wait(timeout=1.0)
                    continue
                DURABLE_TTS_QUEUE_CLAIM_COUNT += 1
                worker_count = len(DURABLE_TTS_QUEUE_THREADS)
                reserve = durable_tts_interactive_reserve(worker_count)
                background_ceiling = min(
                    max(1, worker_count - reserve),
                    durable_tts_background_concurrency_limit(worker_count),
                )
                background_inflight = DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY.get(3, 0) + sum(
                    1 for row in DURABLE_TTS_EXECUTION_QUEUE if int(row.get("priority", 1) or 1) == 3
                )
                background_capacity = max(0, background_ceiling - background_inflight)
            throttle = durable_tts_background_throttle_state()
            if throttle.get("throttled"):
                DURABLE_TTS_BACKGROUND_THROTTLE_EVENTS += 1
                DURABLE_TTS_BACKGROUND_THROTTLE_LAST_REASON = clean(throttle.get("reason", ""))
                background_capacity = 0
            jobs = durable_tts_claim_capacity_batch(owner, min(available, 16), background_capacity)
            if not jobs:
                with DURABLE_TTS_QUEUE_CONDITION:
                    DURABLE_TTS_QUEUE_CONDITION.wait(timeout=5.0)
                continue
            with DURABLE_TTS_QUEUE_CONDITION:
                DURABLE_TTS_EXECUTION_QUEUE.extend(jobs)
                DURABLE_TTS_QUEUE_CONDITION.notify(len(jobs))
        except Exception as exc:
            stt_debug_log("durable_tts_coordinator_error", error=str(exc))
            DURABLE_TTS_QUEUE_STOP.wait(0.8)


def start_durable_tts_dispatcher() -> dict:
    global DURABLE_TTS_QUEUE_STARTED
    with DURABLE_TTS_QUEUE_CONDITION:
        if DURABLE_TTS_QUEUE_STARTED:
            return {"started": True, "workers": len(DURABLE_TTS_QUEUE_THREADS), "owner": DURABLE_TTS_QUEUE_OWNER}
        DURABLE_TTS_QUEUE_STOP.clear()
        recovered = durable_tts_recover_expired()
        DURABLE_TTS_QUEUE_STARTED = True
    workers = durable_tts_ensure_dispatcher_capacity()
    return {"started": True, "workers": workers, "owner": DURABLE_TTS_QUEUE_OWNER, "recovered": recovered}


def durable_tts_job(job_id: str) -> dict:
    def _load(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM future_server2.tts_jobs WHERE job_id = %s", (clean(job_id),))
            return durable_tts_row(cursor, cursor.fetchone())

    return postgres_execute(_load)


def durable_tts_requeue_missing_artifact(job: dict) -> dict:
    if clean(job.get("status", "")) != "completed" or durable_tts_artifact_valid(job):
        return job
    now = time.time()

    def _requeue(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE future_server2.tts_jobs
                SET status = 'queued', attempt_count = 0, next_retry_epoch = 0,
                    completed_epoch = 0, updated_epoch = %s, last_error = 'Completed artifact was missing or invalid.'
                WHERE job_id = %s AND status = 'completed'
                RETURNING *
                """,
                (now, clean(job.get("job_id", ""))),
            )
            return durable_tts_row(cursor, cursor.fetchone())

    return postgres_execute(_requeue) or job


def durable_tts_result(job: dict) -> dict | None:
    if clean(job.get("status", "")) != "completed" or not durable_tts_artifact_valid(job):
        return None
    path = Path(clean(job.get("artifact_path", "")))
    result = durable_tts_json_value(job.get("result_json"))
    result["audio_bytes"] = path.read_bytes()
    result["audio_mime"] = clean(result.get("mime", "")) or "audio/mpeg"
    result["durable_job_id"] = clean(job.get("job_id", ""))
    return result


def durable_tts_submit_raw(
    text: str,
    voice: str,
    *,
    priority: int = 1,
    source: str = "runtime_voice",
    timeout_seconds: float = 45.0,
    preferred_user: str = "",
    build_id: str = "",
    params: dict | None = None,
    output_key: str = "",
) -> dict | None:
    job = durable_tts_enqueue(
        text, voice, priority=priority, source=source, preferred_user=preferred_user,
        build_id=build_id, params=params, output_key=output_key,
    )
    job = durable_tts_requeue_missing_artifact(job)
    ready = durable_tts_result(job)
    if ready:
        return ready
    timeout = max(0.0, float(timeout_seconds or 0))
    if timeout <= 0:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        with DURABLE_TTS_QUEUE_CONDITION:
            DURABLE_TTS_QUEUE_CONDITION.wait(timeout=min(0.5, max(0.02, remaining)))
        job = durable_tts_job(job.get("job_id", ""))
        ready = durable_tts_result(job)
        if ready:
            return ready
        if clean(job.get("status", "")) in {"failed", "cancelled"}:
            return None
    return None


def durable_tts_queue_metrics() -> dict:
    now = time.time()
    with DURABLE_TTS_QUEUE_CONDITION:
        cached_at = float(DURABLE_TTS_METRICS_CACHE.get("at", 0) or 0)
        cached_value = DURABLE_TTS_METRICS_CACHE.get("value")
        if now - cached_at < 2.0 and isinstance(cached_value, dict) and cached_value:
            return dict(cached_value)

    def _metrics(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT priority, status, source, COUNT(*), MIN(created_epoch)
                FROM future_server2.tts_jobs
                WHERE status <> 'completed' OR completed_epoch >= %s
                GROUP BY priority, status, source
                ORDER BY priority, status, source
                """,
                (now - 86400.0,),
            )
            rows = cursor.fetchall()
        return [
            {"priority": int(row[0]), "status": clean(row[1]), "source": clean(row[2]), "count": int(row[3]), "oldest_epoch": float(row[4] or 0)}
            for row in rows
        ]

    rows = postgres_execute(_metrics)
    queued = [row for row in rows if row["status"] in {"queued", "retry_wait"}]
    oldest = min((row["oldest_epoch"] for row in queued if row["oldest_epoch"] > 0), default=0)
    with DURABLE_TTS_QUEUE_CONDITION:
        dispatchers = len(DURABLE_TTS_QUEUE_THREADS)
        active_by_priority = dict(DURABLE_TTS_EXECUTION_ACTIVE_BY_PRIORITY)
        memory_queue_by_priority = {
            priority: sum(1 for row in DURABLE_TTS_EXECUTION_QUEUE if int(row.get("priority", 1) or 1) == priority)
            for priority in (1, 2, 3)
        }
    result = {
        "owner": DURABLE_TTS_QUEUE_OWNER,
        "dispatchers": dispatchers,
        "interactive_reserve": durable_tts_interactive_reserve(dispatchers),
        "background_concurrency_limit": durable_tts_background_concurrency_limit(dispatchers),
        "active_by_priority": active_by_priority,
        "memory_queue_by_priority": memory_queue_by_priority,
        "rows": rows,
        "oldest_queue_age_seconds": max(0.0, now - oldest) if oldest else 0.0,
        "background_throttle_events": int(DURABLE_TTS_BACKGROUND_THROTTLE_EVENTS),
        "background_throttle_last_reason": clean(DURABLE_TTS_BACKGROUND_THROTTLE_LAST_REASON),
        "background_throttle": durable_tts_background_throttle_state(),
    }
    with DURABLE_TTS_QUEUE_CONDITION:
        DURABLE_TTS_METRICS_CACHE.update({"at": now, "value": result})
    return dict(result)
