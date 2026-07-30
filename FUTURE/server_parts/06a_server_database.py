# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# PostgreSQL is authoritative for all mutable server state; legacy SQLite paths are retired.

SERVER_DATABASE_INIT_LOCK = threading.Lock()
SERVER_DATABASE_READY = False
SERVER_DATABASE_READY_STATUS: dict[str, object] = {}
SERVER_DATABASE_DOCUMENT_LOCK = threading.Lock()
SERVER_DATABASE_DOCUMENT_STATE: dict[str, object] = {"pending": {}, "timer": None, "writing": False}
SERVER_DATABASE_DOCUMENT_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_DOCUMENT_CACHE: dict[str, dict[str, object]] = {}
SERVER_DATABASE_USER_PREFERENCES_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_USER_PREFERENCES_CACHE: dict[str, dict[str, object]] = {}
SERVER_DATABASE_USER_PROFILE_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_USER_PROFILE_CACHE: dict[str, dict[str, object]] = {}
SERVER_DATABASE_LESSON_STATE_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_LESSON_STATE_USERS: set[str] = set()
SERVER_DATABASE_LESSON_STATE_SIGNATURES: dict[str, tuple[int, int, int, int]] = {}
SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK = threading.RLock()
SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE: dict[str, str] = {}
SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_FOLDER_LINK_CACHE: dict[str, dict] = {}
# Added 2026-07-23: virtual Lesson Vault placement cache.  It is a rebuildable
# accelerator; SQLite rows remain authoritative for folders and entries.
SERVER_DATABASE_VAULT_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_VAULT_FOLDER_CACHE: dict[str, dict] = {}
SERVER_DATABASE_VAULT_ENTRY_CACHE: dict[str, dict] = {}
SERVER_DATABASE_VAULT_PATH_CACHE: dict[str, dict] = {}
SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER: dict[str, dict[str, dict]] = {}
SERVER_DATABASE_VAULT_ENTRY_CACHE_BY_USER: dict[str, dict[str, dict]] = {}
SERVER_DATABASE_VAULT_REVISION_CACHE: dict[str, int] = {}
SERVER_DATABASE_VAULT_LEGACY_SHELLS: set[str] = set()
SERVER_DATABASE_VAULT_ENABLED = truthy(os.environ.get("FUTURE_HYBRID_VAULT_ENABLED", "1"), True)
SERVER_DATABASE_LESSON_STATE_PRESENCE_CACHE_ENABLED = truthy(
    os.environ.get("FUTURE_LESSON_STATE_PRESENCE_CACHE", "1"),
    True,
)
SERVER_DATABASE_EXPORT_LOCK = threading.Lock()
SERVER_DATABASE_EXPORT_STATE: dict[str, object] = {"pending": {}, "timer": None, "writing": False}
SERVER_DATABASE_WRITE_BEHIND_SECONDS = 0.2
SERVER_DATABASE_WRITE_QUEUE: queue.Queue = queue.Queue()
SERVER_DATABASE_WRITER_LOCK = threading.Lock()
SERVER_DATABASE_WRITER_STARTED = False
SERVER_DATABASE_GROUP_COMMIT_SECONDS = 0.004
SERVER_DATABASE_GROUP_COMMIT_MAX_TASKS = 64
SERVER_DATABASE_WRITE_METRICS_LOCK = threading.Lock()
SERVER_DATABASE_WRITE_METRICS = {
    "batches": 0,
    "tasks": 0,
    "queue_wait_ms": 0.0,
    "begin_wait_ms": 0.0,
    "commit_ms": 0.0,
    "busy_errors": 0,
    "active_source": "",
    "active_started_at": 0.0,
    "last_source": "",
    "last_callback_ms": 0.0,
    "max_callback_ms": 0.0,
    "source_tasks": {},
    "source_callback_ms": {},
}
SERVER_DATABASE_CHANGE_GENERATIONS: dict[str, int] = {"period": 0, "period_resets": 0, "registry": 0, "progress": 0, "lesson_time": 0, "inventory": 0, "users": 0, "events": 0}
SERVER_DATABASE_USER_CHANGE_GENERATIONS: dict[str, dict[str, int]] = {"registry": {}, "period": {}, "progress": {}, "lesson_time": {}, "inventory": {}, "lesson_tasks": {}}
SERVER_DATABASE_REGISTRY_RAM_CACHE: dict[str, dict] = {}
SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE: dict[str, object] = {"loaded": False, "payload": {}}
SERVER_DATABASE_LESSON_TIME_RAM_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_LESSON_TIME_RAM_CACHE: dict[str, dict] = {}
LESSON_TIME_SERVER_BOOT_ID = secrets.token_hex(12)
LESSON_TIME_SERVER_BOOT_EPOCH = time.time()
LESSON_TIME_PROTOCOL = "server-time-v1"
LESSON_TIME_MAX_HEARTBEAT_SECONDS = 60
LESSON_TIME_ACTIVE_SESSION_LEASE_SECONDS = 90
LESSON_TIME_OFFLINE_CREDIT_MAX_SECONDS = 2 * 60 * 60
LESSON_TIME_OFFLINE_LEASE_SECONDS = 4 * 60 * 60
LESSON_TIME_OFFLINE_CLAIM_GRACE_SECONDS = 24 * 60 * 60
LESSON_TIME_RESTART_CLAIM_BOUNDARY_SECONDS = 15 * 60
LESSON_TIME_LEASE_SECRET = hashlib.sha256(f"{anti_robot_secret()}|lesson-time-lease-v1".encode("utf-8")).digest()
LESSON_TIME_HEARTBEAT_RAM_LOCK = threading.RLock()
LESSON_TIME_HEARTBEAT_RAM: dict[tuple[str, str], dict] = {}
LESSON_TIME_HEARTBEAT_RAM_MAX = 20_000
SERVER_DATABASE_INVENTORY_RAM_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_INVENTORY_RAM_CACHE: dict[str, dict] = {}
SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT = 64
SERVER_DATABASE_INVENTORY_EVENT_LOCKS = tuple(threading.RLock() for _index in range(SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT))
SERVER_DATABASE_INVENTORY_EVENT_RAM = tuple({} for _index in range(SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT))
SERVER_DATABASE_INVENTORY_EVENT_FLIGHTS = tuple({} for _index in range(SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT))
SERVER_DATABASE_INVENTORY_EVENT_RAM_MAX = 50_000
SERVER_DATABASE_PDF_DRAWING_RAM_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_PDF_DRAWING_RAM_CACHE: dict[tuple[str, str, int], dict] = {}
SERVER_DATABASE_TEST_AUTH_CACHE_LOCK = threading.RLock()
SERVER_DATABASE_TEST_AUTH_CACHE: dict[str, str] | None = None

SERVER_DATABASE_LOCAL_ONLY_DOCUMENT_NAMES = {
    "_future_admins.json",
    "_future_ai_agent_history.json",
    "_future_announcements.json",
    "_future_auth_sessions.json",
    "_future_chat_messages.json",
    "_future_cloudflare_email_routing.json",
    "_future_cloudflare_email_routing_inbox.json",
    "_future_frontend_reload.json",
    "_future_blocked_login_users.json",
    "_future_password_resets.json",
    "_future_settings.json",
    "_future_qm_city_training.json",
    "_future_shared_world.json",
    "_future_shared_world_battles.json",
    "_future_shared_world_battle_word_history.json",
    "_future_space_w_speak_skip_requests.json",
    "_future_space_pdf_ai_question_progress.json",
    "_future_space_pdf_ai_region_notices.json",
    "_future_space_pdf_ai_region_questions.json",
    "_future_space_pdf_audio_markers.json",
    "_future_space_pdf_drawings.json",
    "_future_space_lesson_ids.json",
    "_future_learned_vocabulary.json",
    "_future_vocab_leaderboard_periods.json",
    "_future_qmdict_confusable_meanings.json",
    "_future_qmdict_meaning_audio_refresh_history.json",
    "_future_qmdict_remove_proper_names_batch75.json",
    "_future_qmdict_restore_places_batch76.json",
    "_future_qmdict_short_word_cleanup.json",
    "_future_qmdict_short_word_review.json",
    "_future_qmdict_usage_examples_batch19.json",
    "_future_qmdict_usage_vi_batch10.json",
    "_future_qmdict_usage_vi_batch11.json",
    "_future_qmdict_usage_vi_batch12.json",
    "_future_qmdict_usage_vi_batch13.json",
    "_future_space_v_minimize_rebuild_report.json",
    "_future_space_v_minimize_rebuild_report_v2.json",
    "_future_space_v_minimize_retry_report.json",
    "_future_word_agent_history.json",
    "_user_identity.json",
    "_web_pending_users.json",
    "_future_inventory.json",
    "_future_learning_summary.json",
    "_future_lesson_task_notices.json",
    "_future_lesson_tasks.json",
    "_future_lesson_time.json",
    "_future_shared_world_keyboard_passes.json",
    "_future_vocab_leaderboard_npc_top.json",
    "_future_vocab_leaderboard_ranks.json",
    "_future_vocab_leaderboard_reward_claims.json",
    "_future_vocab_leaderboard_social.json",
    "_future_vocab_leaderboard_viewers.json",
    "_future_vocab_leaderboard_world_chat.json",
    "space_leaderboard_activity.json",
    "lesson_last_file.json",
    "._future_folder_link.json",
}


def server_database_normalize_timestamps(value: object):
    if isinstance(value, list):
        return [server_database_normalize_timestamps(item) for item in value]
    if not isinstance(value, dict):
        return value
    timestamp_names = {
        "at", "timestamp", "updated_at", "created_at", "saved_at", "last_at", "first_at", "learned_at", "completed_at",
        "updatedat", "createdat", "savedat", "lastat", "firstat", "learnedat", "completedat",
    }
    out = {}
    for key, item in value.items():
        if isinstance(item, (dict, list)):
            out[key] = server_database_normalize_timestamps(item)
        elif clean(key).lower() in timestamp_names and clean(item) and ":" in clean(item):
            out[key] = normalize_timestamp_text(item)
        else:
            out[key] = item
    return out



def backup_server_database(force: bool = False) -> dict:
    return {"ok": True, "skipped": "postgresql_authoritative"}



# Added 2026-07-20: refresh incompatible backups at boot and keep one bounded online-backup worker between shutdowns.
def server_database_backup_compatibility() -> dict:
    return {"compatible": True, "skipped": "postgresql_authoritative"}



def start_server_database_backup_worker() -> dict:
    return {"started": False, "reason": "postgresql_authoritative"}



def recover_server_database_if_corrupt() -> dict:
    return {"recovered": False, "reason": "postgresql_authoritative"}



# Added 2026-07-20: migrate the retired per-user lesson-time JSON document into indexed delta rows once.


# Added 2026-07-20: migrate inventory items and idempotency events out of JSON-shaped documents.


# Added 2026-07-20: migrate the all-user Lesson Tasks document into one compact row per user.


# Added 2026-07-20: migrate the monolithic chat document into durable message/read rows with permanent operation IDs.


# Added 2026-07-20: isolate mutable preferences from legacy user documents into one indexed row per user.


# Added 2026-07-20: hash and migrate durable login sessions into one row per active user.


# Added 2026-07-20: migrate the monolithic PDF drawing document into one atomic row per user/document/page.


def initialize_server_database() -> dict:
    global SERVER_DATABASE_READY, SERVER_DATABASE_READY_STATUS
    with SERVER_DATABASE_INIT_LOCK:
        validate_postgres_backend_configuration()
        SERVER_DATABASE_READY = True
        SERVER_DATABASE_READY_STATUS = {
            "ok": True,
            "backend": "postgresql",
            "postgres_only": True,
            "legacy_backend": "retired",
        }
        return dict(SERVER_DATABASE_READY_STATUS)



def server_database_status() -> dict:
    metrics_getter = globals().get("postgres_metrics_snapshot")
    return {
        "ok": True,
        "path": "postgresql:future_server2",
        "journal_mode": "postgresql",
        "synchronous": "postgresql",
        "postgres_only": True,
        "legacy_backend": {"enabled": False, "open": False},
        "postgres": metrics_getter() if callable(metrics_getter) else {},
    }



def _server_database_writer_loop() -> None:
    return



def start_server_database_writer() -> None:
    return




# Added 2026-07-20: expose cumulative local-only writer timing for comparable concurrency benchmarks.
def server_database_write_metrics_snapshot() -> dict:
    return {"batches": 0, "tasks": 0, "queue_depth": 0, "retired": True}



def flush_server_database_writer(force: bool = False) -> bool:
    return True





def server_database_upsert_user(username: str, profile: dict | None = None) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    postgres_upsert_user_row({
        "username": normalized,
        "is_admin": is_admin_user(normalized),
        "is_test": False,
        "profile": profile if isinstance(profile, dict) else {},
        "updated_at_utc": utc_timestamp(),
    })
    if isinstance(profile, dict) and profile:
        normalized_profile = server_database_normalize_timestamps(profile)
        identity = hashlib.sha256(json.dumps(normalized_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
        with SERVER_DATABASE_USER_PROFILE_CACHE_LOCK:
            SERVER_DATABASE_USER_PROFILE_CACHE[normalized.lower()] = {
                "profile": copy.deepcopy(normalized_profile),
                "updated_at": utc_timestamp(),
                "identity": identity,
            }
    return True


def server_database_generation(name: str = "") -> int:
    return int(SERVER_DATABASE_CHANGE_GENERATIONS.get(clean(name).lower(), 0) or 0)


def server_database_user_generation(name: str = "", username: str = "") -> int:
    bucket = SERVER_DATABASE_USER_CHANGE_GENERATIONS.get(clean(name).lower())
    return int((bucket or {}).get(normalize_username(username).lower(), 0) or 0) if isinstance(bucket, dict) else 0


def server_database_bump_user_generation(name: str = "", username: str = "") -> int:
    key = clean(name).lower()
    user_key = normalize_username(username).lower()
    if not user_key:
        return 0
    bucket = SERVER_DATABASE_USER_CHANGE_GENERATIONS.setdefault(key, {})
    bucket[user_key] = int(bucket.get(user_key, 0) or 0) + 1
    return bucket[user_key]


# Added 2026-07-20: load the bounded authoritative chat rows once for the shared runtime cache.
def server_database_load_auth_sessions() -> dict[str, dict]:
    return postgres_load_auth_sessions()


def server_database_replace_auth_sessions_batch(rows: list[dict] | tuple[dict, ...]) -> int:
    normalized_rows = []
    for item in rows or ():
        username = normalize_username((item or {}).get("username", ""))
        key = clean((item or {}).get("token_hash", ""))
        issued = float((item or {}).get("issued_at", 0) or time.time())
        if not username or len(key) != 64:
            raise RuntimeError("Auth session is invalid.")
        normalized_rows.append((key, username, issued, issued, issued, issued + 86400, local_timestamp(issued)))
    if not normalized_rows:
        return 0
    return postgres_replace_auth_sessions_batch([
        {"token_hash": key, "username": username, "issued_at": issued}
        for key, username, issued, *_rest in normalized_rows
    ])


def server_database_replace_auth_session(username: str, token_hash: str, now: float) -> bool:
    return server_database_replace_auth_sessions_batch([{
        "username": username,
        "token_hash": token_hash,
        "issued_at": now,
    }]) == 1


def server_database_touch_auth_sessions(rows: dict[str, dict]) -> int:
    source = {clean(key): dict(item) for key, item in (rows or {}).items() if clean(key) and isinstance(item, dict)}
    if not source:
        return 0
    return postgres_touch_auth_sessions(source)


def server_database_delete_auth_sessions(username: str = "", token_hashes: list[str] | tuple[str, ...] | None = None) -> int:
    normalized = normalize_username(username)
    keys = tuple(clean(value) for value in (token_hashes or ()) if clean(value))
    if not normalized and not keys:
        return 0
    return postgres_delete_auth_sessions(normalized, keys)


# Added 2026-07-20: load one derived vocabulary image row without scanning or decoding a shared cache document.
def server_database_load_vocab_image_cache(word_key: str) -> dict | None:
    key = clean(word_key).lower()
    if not key:
        return None
    return postgres_load_vocab_image_cache(key)


# Added 2026-07-20: hydrate the bounded derived image RAM cache with one indexed SQLite read after restart.
def server_database_load_vocab_image_cache_rows(limit: int = 2048) -> list[dict]:
    return postgres_load_vocab_image_cache_rows(limit)


# Added 2026-07-20: persist a coalesced batch of positive or negative derived vocabulary image results.
def server_database_store_vocab_image_cache_batch(rows: list[dict] | tuple[dict, ...]) -> int:
    return postgres_store_vocab_image_cache_batch(rows)


def server_database_load_user_preferences(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {}
    return postgres_load_user_preferences(normalized)




def server_database_preference_identity(preferences: dict | None = None) -> str:
    def _semantic(value):
        if isinstance(value, dict):
            return {
                key: _semantic(item)
                for key, item in value.items()
                if clean(key).lower() not in {"updated_at", "updatedat", "server_revision", "serverrevision", "_serverrevision"}
            }
        if isinstance(value, list):
            return [_semantic(item) for item in value]
        return value

    return json.dumps(_semantic(preferences if isinstance(preferences, dict) else {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


# Added 2026-07-20: merge a compact preference patch atomically and avoid writes for exact retries.
def server_database_save_user_preferences(username: str, patch: dict) -> dict:
    normalized = normalize_username(username)
    source_patch = dict(patch) if isinstance(patch, dict) else {}
    if not normalized:
        raise RuntimeError("User khong ton tai.")
    return postgres_save_user_preferences(normalized, source_patch)


def server_database_load_chat_state() -> dict:
    return postgres_load_chat_state()


# Added 2026-07-20: commit one idempotent chat message before the HTTP acknowledgement.
def server_database_add_chat_message(item: dict, operation_id: str = "") -> dict:
    source = dict(item) if isinstance(item, dict) else {}
    username = normalize_username(source.get("username", ""))
    sender = "admin" if clean(source.get("sender", "")).lower() == "admin" else "user"
    operation = clean(operation_id or source.get("operation_id", ""))[:160]
    if operation and not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", operation):
        raise RuntimeError("Chat operation ID is invalid.")
    if not username:
        raise RuntimeError("Chat message requires a username.")
    return postgres_add_chat_message(source, operation)


def server_database_update_chat_read(username: str, field: str, message_id: int) -> bool:
    normalized = normalize_username(username)
    column = "admin_read" if clean(field).lower() == "admin_read" else "user_read"
    value = max(0, int(message_id or 0))
    if not normalized or value <= 0:
        return False
    return postgres_update_chat_read(normalized, column, value)


def server_database_replace_chat_state(payload: dict) -> bool:
    return postgres_replace_chat_state(payload)


def server_database_delete_chat_user(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    return postgres_delete_chat_user(normalized)


# Added 2026-07-20: Lesson Tasks read/write one authenticated user's row instead of an all-user document.
def server_database_load_lesson_task_record(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"record": {}, "revision": 0, "updated_at": ""}
    return postgres_load_lesson_task_record(normalized)


def server_database_load_all_lesson_task_records() -> dict:
    return postgres_load_all_lesson_task_records()


def server_database_write_lesson_task_record(username: str, record: dict | None = None) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        raise RuntimeError("Missing Lesson Task user.")
    result = postgres_write_lesson_task_record(normalized, record)
    if result.get("changed"):
        server_database_bump_user_generation("lesson_tasks", normalized)
    return result


def server_database_delete_lesson_task_record(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    removed = postgres_delete_lesson_task_record(normalized)
    if removed:
        server_database_bump_user_generation("lesson_tasks", normalized)
    return removed


# Added 2026-07-20: lesson study time uses indexed additive rows instead of rewriting a per-user JSON document.


def server_database_load_lesson_time_payload(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"version": 1, "updated_at": "", "states": {}}
    return postgres_load_lesson_time_payload(normalized)


# Added 2026-07-20: signed leases bound bounded offline study claims to a server-issued session.
def server_database_lesson_time_offline_lease(
    username: str,
    lesson_key: str,
    session_id: str,
    issued_epoch: float,
) -> dict:
    issued = max(0, int(float(issued_epoch or 0)))
    payload = {
        "v": 1,
        "u": normalize_username(username).lower(),
        "k": clean(lesson_key),
        "s": clean(session_id),
        "i": issued,
        "x": issued + LESSON_TIME_OFFLINE_LEASE_SECONDS,
        "d": issued + LESSON_TIME_OFFLINE_LEASE_SECONDS + LESSON_TIME_OFFLINE_CLAIM_GRACE_SECONDS,
        "m": LESSON_TIME_OFFLINE_CREDIT_MAX_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(
        LESSON_TIME_LEASE_SECRET,
        f"lesson-time-lease-v1.{encoded}".encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "token": f"{encoded}.{signature}",
        "issuedEpoch": issued,
        "expiresEpoch": payload["x"],
        "claimDeadlineEpoch": payload["d"],
        "maxOfflineSeconds": payload["m"],
    }


def server_database_verify_lesson_time_offline_lease(
    token: object,
    username: str,
    lesson_key: str,
    session_id: str,
    now_epoch: float,
) -> dict:
    raw = clean(token)
    if not raw or "." not in raw:
        raise RuntimeError("Lesson offline lease is missing.")
    encoded, signature = raw.rsplit(".", 1)
    expected = hmac.new(
        LESSON_TIME_LEASE_SECRET,
        f"lesson-time-lease-v1.{encoded}".encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise RuntimeError("Lesson offline lease signature is invalid.")
    try:
        padded = encoded + ("=" * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Lesson offline lease payload is invalid.") from exc
    if not isinstance(payload, dict) or int(payload.get("v", 0) or 0) != 1:
        raise RuntimeError("Lesson offline lease version is invalid.")
    if (
        clean(payload.get("u", "")).lower() != normalize_username(username).lower()
        or clean(payload.get("k", "")) != clean(lesson_key)
        or clean(payload.get("s", "")) != clean(session_id)
    ):
        raise RuntimeError("Lesson offline lease identity does not match.")
    issued = max(0, int(payload.get("i", 0) or 0))
    deadline = max(0, int(payload.get("d", 0) or 0))
    if issued <= 0 or deadline <= 0 or float(now_epoch or 0) > deadline:
        raise RuntimeError("Lesson offline lease has expired.")
    return {
        **payload,
        "m": max(0, min(LESSON_TIME_OFFLINE_CREDIT_MAX_SECONDS, int(payload.get("m", 0) or 0))),
    }


def server_database_add_lesson_time(
    username: str,
    lesson_key: str,
    legacy_key: str,
    path: str,
    title: str,
    space: str,
    seconds: int | float,
    session_id: str = "",
    sequence: int | None = None,
    protocol: str = "",
    offline_claims: list[dict] | tuple[dict, ...] | None = None,
    offline_lease: str = "",
    authenticated_user: bool = False,
) -> dict:
    normalized = normalize_username(username)
    key = clean(lesson_key)
    if not normalized or not key:
        raise RuntimeError("Lesson time requires user and lesson key.")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(float(seconds)):
        raise RuntimeError("Lesson heartbeat seconds must be a finite number.")
    requested_seconds = int(seconds)
    if float(seconds) != float(requested_seconds) or requested_seconds < 0 or requested_seconds > LESSON_TIME_MAX_HEARTBEAT_SECONDS:
        raise RuntimeError("Lesson heartbeat seconds are outside the accepted range.")
    safe_protocol = clean(protocol).lower()
    safe_session_id = clean(session_id)[:96]
    normalized_offline_claims: list[dict] = []
    lease_info: dict = {}
    if safe_protocol == LESSON_TIME_PROTOCOL:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,96}", safe_session_id):
            raise RuntimeError("Lesson heartbeat session is invalid.")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0 or sequence > 2_147_483_647:
            raise RuntimeError("Lesson heartbeat sequence is invalid.")
        if offline_claims is not None:
            if not isinstance(offline_claims, (list, tuple)) or not offline_claims or len(offline_claims) > 120:
                raise RuntimeError("Lesson offline heartbeat batch is invalid.")
            for claim in offline_claims:
                source = claim if isinstance(claim, dict) else {}
                claim_sequence = source.get("sequence")
                claim_seconds = source.get("seconds")
                if (
                    isinstance(claim_sequence, bool)
                    or not isinstance(claim_sequence, int)
                    or claim_sequence < 0
                    or claim_sequence > 2_147_483_647
                    or isinstance(claim_seconds, bool)
                    or not isinstance(claim_seconds, (int, float))
                    or not math.isfinite(float(claim_seconds))
                    or float(claim_seconds) != float(int(claim_seconds))
                    or int(claim_seconds) <= 0
                    or int(claim_seconds) > LESSON_TIME_MAX_HEARTBEAT_SECONDS
                ):
                    raise RuntimeError("Lesson offline heartbeat row is invalid.")
                normalized_offline_claims.append({"sequence": claim_sequence, "seconds": int(claim_seconds)})
            normalized_offline_claims.sort(key=lambda row: row["sequence"])
            if int(sequence) != normalized_offline_claims[-1]["sequence"]:
                raise RuntimeError("Lesson offline heartbeat sequence does not match its batch.")
    else:
        if requested_seconds <= 0:
            raise RuntimeError("Legacy lesson heartbeat seconds must be positive.")
        safe_session_id = "legacy"
        sequence = None
    now_epoch = time.time()
    updated_at = local_timestamp(now_epoch)
    updated_epoch = max(0.0, now_epoch)
    if normalized_offline_claims:
        lease_info = server_database_verify_lesson_time_offline_lease(
            offline_lease,
            normalized,
            key,
            safe_session_id,
            updated_epoch,
        )
        ram_key = (normalized.lower(), key)
        with LESSON_TIME_HEARTBEAT_RAM_LOCK:
            cached_heartbeat = LESSON_TIME_HEARTBEAT_RAM.get(ram_key)
            if (
                isinstance(cached_heartbeat, dict)
                and clean(cached_heartbeat.get("session_id", "")) == safe_session_id
                and int(cached_heartbeat.get("lease_issued_epoch", 0) or 0) == int(lease_info.get("i", 0) or 0)
                and int(sequence) <= max(0, int(cached_heartbeat.get("last_sequence", 0) or 0))
            ):
                return {
                    "acceptedSeconds": 0,
                    "heartbeatAccepted": False,
                    "heartbeatReason": "replay",
                    "sessionId": safe_session_id,
                    "sequence": int(sequence),
                }
    elif safe_protocol == LESSON_TIME_PROTOCOL:
        ram_key = (normalized.lower(), key)
        with LESSON_TIME_HEARTBEAT_RAM_LOCK:
            cached_heartbeat = LESSON_TIME_HEARTBEAT_RAM.get(ram_key)
            if isinstance(cached_heartbeat, dict) and clean(cached_heartbeat.get("session_id", "")) == safe_session_id:
                cached_sequence = max(0, int(cached_heartbeat.get("last_sequence", 0) or 0))
                elapsed_monotonic = max(0.0, time.monotonic() - float(cached_heartbeat.get("last_monotonic", 0.0) or 0.0))
                if int(sequence) <= cached_sequence or elapsed_monotonic < 0.75:
                    reason = "replay" if int(sequence) <= cached_sequence else "too_fast"
                    cached_heartbeat["last_sequence"] = max(cached_sequence, int(sequence))
                    return {
                        "acceptedSeconds": 0,
                        "heartbeatAccepted": False,
                        "heartbeatReason": reason,
                        "sessionId": safe_session_id,
                        "sequence": int(sequence),
                    }


    from FUTURE.postgres.repositories import lesson_time as pg_lesson_time

    result = pg_lesson_time.add_lesson_time_heartbeat({
        "username": normalized,
        "lesson_key": key,
        "legacy_key": legacy_key,
        "path": path,
        "title": title,
        "space": space,
        "requested_seconds": requested_seconds,
        "session_id": safe_session_id,
        "sequence": sequence,
        "protocol": safe_protocol,
        "offline_claims": normalized_offline_claims,
        "offline_lease": offline_lease,
        "lease_info": lease_info,
        "updated_at": updated_at,
        "updated_epoch": updated_epoch,
        "server_boot_id": LESSON_TIME_SERVER_BOOT_ID,
        "server_boot_epoch": LESSON_TIME_SERVER_BOOT_EPOCH,
    })
    if safe_protocol == LESSON_TIME_PROTOCOL:
        ram_key = (normalized.lower(), key)
        reason = clean(result.get("heartbeatReason", ""))
        if reason != "session_conflict":
            with LESSON_TIME_HEARTBEAT_RAM_LOCK:
                if len(LESSON_TIME_HEARTBEAT_RAM) >= LESSON_TIME_HEARTBEAT_RAM_MAX and ram_key not in LESSON_TIME_HEARTBEAT_RAM:
                    for stale_key in tuple(LESSON_TIME_HEARTBEAT_RAM)[:2000]:
                        LESSON_TIME_HEARTBEAT_RAM.pop(stale_key, None)
                previous_heartbeat = LESSON_TIME_HEARTBEAT_RAM.get(ram_key)
                lease_issued_epoch = int(lease_info.get("i", 0) or 0)
                if lease_issued_epoch <= 0 and isinstance(previous_heartbeat, dict):
                    lease_issued_epoch = int(previous_heartbeat.get("lease_issued_epoch", 0) or 0)
                LESSON_TIME_HEARTBEAT_RAM[ram_key] = {
                    "session_id": safe_session_id,
                    "last_sequence": max(0, int(sequence or 0)),
                    "last_monotonic": time.monotonic(),
                    "lease_issued_epoch": lease_issued_epoch,
                }
    accepted_seconds = max(0, space_w_int(result.get("acceptedSeconds", 0), 0))
    if accepted_seconds <= 0:
        return result
    SERVER_DATABASE_CHANGE_GENERATIONS["lesson_time"] += 1
    generation = server_database_bump_user_generation("lesson_time", normalized)
    cache_key = normalized.lower()
    with SERVER_DATABASE_LESSON_TIME_RAM_CACHE_LOCK:
        cached = SERVER_DATABASE_LESSON_TIME_RAM_CACHE.get(cache_key)
        payload = cached.get("payload") if isinstance(cached, dict) and isinstance(cached.get("payload"), dict) else None
        if isinstance(payload, dict):
            states = payload.setdefault("states", {})
            old_key = clean(legacy_key)
            if old_key and old_key != key:
                states.pop(old_key, None)
            current = states.get(key) if isinstance(states.get(key), dict) else {}
            if max(0, space_w_int(result.get("ticks", 0), 0)) >= max(0, space_w_int(current.get("ticks", 0), 0)):
                states[key] = dict(result)
                payload["updated_at"] = clean(result.get("updatedAt", ""))
            SERVER_DATABASE_LESSON_TIME_RAM_CACHE[cache_key] = {"generation": generation, "payload": payload}
        else:
            SERVER_DATABASE_LESSON_TIME_RAM_CACHE.pop(cache_key, None)
    return result


def server_database_replace_lesson_time_payload(username: str, payload: dict) -> bool:
    normalized = normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    states = source.get("states") if isinstance(source.get("states"), dict) else {}

    from FUTURE.postgres.repositories import lesson_time as pg_lesson_time
    result = pg_lesson_time.replace_lesson_time_payload(normalized, source)
    if result:
        SERVER_DATABASE_CHANGE_GENERATIONS["lesson_time"] += 1
        server_database_bump_user_generation("lesson_time", normalized)
        with SERVER_DATABASE_LESSON_TIME_RAM_CACHE_LOCK:
            SERVER_DATABASE_LESSON_TIME_RAM_CACHE.pop(normalized.lower(), None)
    return bool(result)


# Added 2026-07-20: inventory awards are atomic item deltas with event-id idempotency, not document rewrites.


def server_database_load_inventory_payload(username: str, event_limit: int = 5000) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"version": 1, "updated_at": "", "items": {}, "events": []}
    try:
        safe_event_limit = max(0, min(5000, int(event_limit)))
    except (TypeError, ValueError):
        safe_event_limit = 5000
    return postgres_load_inventory_payload(normalized, safe_event_limit)


# Added 2026-07-21: exact inventory retries reuse the committed row without entering SQLite again.
def server_database_inventory_cached_retry(normalized: str, award: dict) -> dict | None:
    item = award.get("item") if isinstance(award.get("item"), dict) else {}
    item_id = clean(item.get("id", ""))[:80]
    event_id = clean(award.get("event_id", ""))[:240]
    quantity = max(1, min(9999, space_w_int(award.get("quantity", 1), 1)))
    if not item_id or not event_id:
        return None
    flight_key = (normalized.lower(), event_id)
    shard_index = hash(flight_key) % SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT
    cached = SERVER_DATABASE_INVENTORY_EVENT_RAM[shard_index].get(flight_key)
    if not isinstance(cached, dict) or clean(cached.get("item_id", "")) != item_id or int(cached.get("quantity", 0) or 0) != quantity:
        return None
    public_item = cached.get("item") if isinstance(cached.get("item"), dict) else dict(item)
    return {
        "results": [{"awarded": False, "event_id": event_id, "item": dict(public_item), "quantity": quantity}],
        "items": {item_id: dict(public_item)},
        "events": [],
        "updated_at": clean(cached.get("updated_at", "")),
    }


# Added 2026-07-21: bound retry memory and wake concurrent followers only after commit or rollback.
def server_database_inventory_finish_flight(
    flight_key: tuple[str, str] | None,
    award: dict | None = None,
    committed: dict | None = None,
) -> None:
    if not flight_key:
        return
    shard_index = hash(flight_key) % SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT
    shard_cache = SERVER_DATABASE_INVENTORY_EVENT_RAM[shard_index]
    shard_flights = SERVER_DATABASE_INVENTORY_EVENT_FLIGHTS[shard_index]
    with SERVER_DATABASE_INVENTORY_EVENT_LOCKS[shard_index]:
        if isinstance(award, dict) and isinstance(committed, dict):
            event_cache = committed.get("_event_cache") if isinstance(committed.get("_event_cache"), dict) else {}
            cached_event = event_cache.get(flight_key[1]) if isinstance(event_cache.get(flight_key[1]), dict) else {}
            item = cached_event.get("item") if isinstance(cached_event.get("item"), dict) else {}
            if clean(cached_event.get("item_id", "")) and int(cached_event.get("quantity", 0) or 0) > 0:
                shard_cache[flight_key] = {
                    "item_id": clean(cached_event.get("item_id", ""))[:80],
                    "quantity": max(1, min(9999, space_w_int(cached_event.get("quantity", 1), 1))),
                    "item": dict(item),
                    "updated_at": clean(committed.get("updated_at", "")),
                }
            shard_limit = max(100, SERVER_DATABASE_INVENTORY_EVENT_RAM_MAX // SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT)
            if len(shard_cache) > shard_limit:
                for stale_key in tuple(shard_cache)[:100]:
                    shard_cache.pop(stale_key, None)
        flight = shard_flights.pop(flight_key, None)
        if isinstance(flight, threading.Event):
            flight.set()


def server_database_award_inventory_items(
    username: str,
    awards: list[dict] | tuple[dict, ...],
    authenticated_user: bool = False,
) -> dict:
    normalized = normalize_username(username)
    normalized_awards = [row for row in awards if isinstance(row, dict)]
    now = utc_timestamp()
    flight_key: tuple[str, str] | None = None
    flight_leader = False
    if len(normalized_awards) == 1:
        single_award = normalized_awards[0]
        event_id = clean(single_award.get("event_id", ""))[:240]
        item = single_award.get("item") if isinstance(single_award.get("item"), dict) else {}
        if normalized and event_id and clean(item.get("id", "")):
            flight_key = (normalized.lower(), event_id)
            shard_index = hash(flight_key) % SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT
            while True:
                with SERVER_DATABASE_INVENTORY_EVENT_LOCKS[shard_index]:
                    cached_retry = server_database_inventory_cached_retry(normalized, single_award)
                    if isinstance(cached_retry, dict):
                        return cached_retry
                    shard_flights = SERVER_DATABASE_INVENTORY_EVENT_FLIGHTS[shard_index]
                    flight = shard_flights.get(flight_key)
                    if not isinstance(flight, threading.Event):
                        flight = threading.Event()
                        shard_flights[flight_key] = flight
                        flight_leader = True
                        break
                if not flight.wait(15.0):
                    break


    try:
        from FUTURE.postgres.repositories import inventory as pg_inventory

        committed = pg_inventory.award_inventory_items(normalized, normalized_awards, now)
    except Exception:
        if flight_leader:
            server_database_inventory_finish_flight(flight_key)
        raise
    if flight_leader:
        server_database_inventory_finish_flight(flight_key, normalized_awards[0], committed)
    if committed.get("events"):
        SERVER_DATABASE_CHANGE_GENERATIONS["inventory"] += 1
        server_database_bump_user_generation("inventory", normalized)
        with SERVER_DATABASE_INVENTORY_RAM_CACHE_LOCK:
            for cache_key in tuple(SERVER_DATABASE_INVENTORY_RAM_CACHE):
                if cache_key.startswith(f"{normalized.lower()}:"):
                    SERVER_DATABASE_INVENTORY_RAM_CACHE.pop(cache_key, None)
    return committed


def server_database_replace_inventory_payload(username: str, payload: dict) -> bool:
    normalized = normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    items = source.get("items") if isinstance(source.get("items"), dict) else {}
    events = source.get("events") if isinstance(source.get("events"), list) else []
    updated_at = normalize_timestamp_text(source.get("updated_at"), fallback_now=True)

    from FUTURE.postgres.repositories import inventory as pg_inventory
    result = pg_inventory.replace_inventory_payload(normalized, source)
    if result:
        SERVER_DATABASE_CHANGE_GENERATIONS["inventory"] += 1
        server_database_bump_user_generation("inventory", normalized)
        for shard_index in range(SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT):
            with SERVER_DATABASE_INVENTORY_EVENT_LOCKS[shard_index]:
                shard_cache = SERVER_DATABASE_INVENTORY_EVENT_RAM[shard_index]
                for event_key in tuple(shard_cache):
                    if event_key[0] == normalized.lower():
                        shard_cache.pop(event_key, None)
        with SERVER_DATABASE_INVENTORY_RAM_CACHE_LOCK:
            for cache_key in tuple(SERVER_DATABASE_INVENTORY_RAM_CACHE):
                if cache_key.startswith(f"{normalized.lower()}:"):
                    SERVER_DATABASE_INVENTORY_RAM_CACHE.pop(cache_key, None)
    return bool(result)


# Added 2026-07-20: PDF drawings use bounded row-level RAM/SQLite access instead of cloning a multi-megabyte document.
def server_database_pdf_drawing_cache_key(username: str, document_key: str, page: object) -> tuple[str, str, int]:
    return normalize_username(username).lower(), clean(document_key)[:64], max(1, space_w_int(page, 1))


def server_database_read_pdf_drawing_row(username: str, document_key: str, page: object) -> dict:
    cache_key = server_database_pdf_drawing_cache_key(username, document_key, page)
    if not cache_key[0] or not cache_key[1]:
        return {}
    return postgres_read_pdf_drawing_row(username, document_key, page)


# Added 2026-07-22: legacy PDF/Picture drawings can be found by the indexed path during lesson_id migration.
def server_database_read_pdf_drawing_row_by_path(username: str, path: str, page: object) -> dict:
    normalized_user = normalize_username(username)
    normalized_path = clean_path_value(path)
    page_number = max(1, space_w_int(page, 1))
    if not normalized_user or not normalized_path:
        return {}
    return postgres_read_pdf_drawing_row_by_path(normalized_user, normalized_path, page_number)


def server_database_write_pdf_drawing_row(username: str, document_key: str, page: object, row: dict | None = None, remove: bool = False) -> dict:
    normalized_user = normalize_username(username)
    cache_key = server_database_pdf_drawing_cache_key(normalized_user, document_key, page)
    source = row if isinstance(row, dict) else {}
    if not normalized_user or not cache_key[1]:
        raise RuntimeError("PDF drawing row identity is required.")
    result = postgres_write_pdf_drawing_row(normalized_user, cache_key[1], cache_key[2], source, remove=remove)
    with SERVER_DATABASE_PDF_DRAWING_RAM_CACHE_LOCK:
        SERVER_DATABASE_PDF_DRAWING_RAM_CACHE.pop(cache_key, None)
        if not remove:
            SERVER_DATABASE_PDF_DRAWING_RAM_CACHE[cache_key] = {
                "row": copy.deepcopy({**source, "server_revision": int(result.get("server_revision", 1) or 1)})
            }
    return result




def server_database_load_user_profile(username: str) -> dict | None:
    normalized = normalize_username(username)
    with SERVER_DATABASE_USER_PROFILE_CACHE_LOCK:
        row = SERVER_DATABASE_USER_PROFILE_CACHE.get(normalized.lower())
        if not isinstance(row, dict):
            return None
        profile = row.get("profile")
        return copy.deepcopy(profile) if isinstance(profile, dict) and profile else None


def server_database_user_profile_signature(username: str) -> tuple[str, str]:
    normalized = normalize_username(username)
    with SERVER_DATABASE_USER_PROFILE_CACHE_LOCK:
        row = SERVER_DATABASE_USER_PROFILE_CACHE.get(normalized.lower())
        if not isinstance(row, dict):
            return "", ""
        return clean(row.get("updated_at")), clean(row.get("identity"))


def server_database_user_exists(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    postgres_exists = globals().get("postgres_user_exists")
    if callable(postgres_exists):
        return bool(postgres_exists(normalized))
    return False


# Added 2026-07-21: preload one compact user-presence set so cold Task Board reads never open SQLite per user.


def server_database_lesson_state_signature(username: str) -> tuple[int, int, int, int]:
    normalized = normalize_username(username)
    return (
        server_database_user_generation("progress", normalized),
        server_database_user_generation("lesson_time", normalized),
        server_database_user_generation("registry", normalized),
        server_database_user_generation("events", normalized),
    )


# Updated 2026-07-21: generation changes recheck only the affected user after the startup presence preload.
def server_database_user_has_lesson_state(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    cache_key = normalized.lower()
    signature = server_database_lesson_state_signature(normalized)
    if SERVER_DATABASE_LESSON_STATE_PRESENCE_CACHE_ENABLED:
        with SERVER_DATABASE_LESSON_STATE_CACHE_LOCK:
            cached_signature = SERVER_DATABASE_LESSON_STATE_SIGNATURES.get(cache_key)
            if cached_signature == signature:
                return cache_key in SERVER_DATABASE_LESSON_STATE_USERS
    has_state = bool(postgres_user_has_lesson_state(normalized))
    if SERVER_DATABASE_LESSON_STATE_PRESENCE_CACHE_ENABLED:
        with SERVER_DATABASE_LESSON_STATE_CACHE_LOCK:
            if has_state:
                SERVER_DATABASE_LESSON_STATE_USERS.add(cache_key)
            else:
                SERVER_DATABASE_LESSON_STATE_USERS.discard(cache_key)
            SERVER_DATABASE_LESSON_STATE_SIGNATURES[cache_key] = signature
    return has_state


# Added 2026-07-20: reusable load-test identities live only in SQLite and stay out of production user statistics.
def server_database_load_test_credentials(refresh: bool = False) -> dict[str, str]:
    global SERVER_DATABASE_TEST_AUTH_CACHE
    with SERVER_DATABASE_TEST_AUTH_CACHE_LOCK:
        if not refresh and isinstance(SERVER_DATABASE_TEST_AUTH_CACHE, dict):
            return dict(SERVER_DATABASE_TEST_AUTH_CACHE)

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.username,c.password_hash FROM future_server2.users u "
                "JOIN future_server2.user_auth_credentials c ON lower(c.username)=lower(u.username) "
                "WHERE COALESCE(u.is_test,false)=true"
            )
            rows = cursor.fetchall()
        return {normalize_username(row[0]): clean(row[1]) for row in rows if normalize_username(row[0])}

    payload = postgres_execute(_read)
    with SERVER_DATABASE_TEST_AUTH_CACHE_LOCK:
        SERVER_DATABASE_TEST_AUTH_CACHE = dict(payload)
    return payload



def server_database_test_user_password_hash(username: str) -> str:
    return clean(server_database_load_test_credentials().get(normalize_username(username), ""))


def server_database_is_test_user(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False
    # Added 2026-07-30: PostgreSQL-only production has no SQLite test-credential
    # table, so stale codex/load-test rows must still be excluded from shared
    # leaderboard documents and rebuilt caches.
    if normalized.startswith(("codex", "testuser", "tester", "loadtest")):
        return True
    return normalized in server_database_load_test_credentials()


def server_database_delete_user(username: str) -> dict:
    normalized = normalize_username(username)
    user_path_fragments = [
        str((USER_ROOT / normalized).resolve()).lower(),
        str((SERVER_DATA_ROOT / normalized).resolve()).lower(),
        str(user_file_path(normalized).resolve()).lower(),
    ]
    postgres_result = postgres_delete_user_data(normalized, user_path_fragments)
    for key in SERVER_DATABASE_CHANGE_GENERATIONS:
        SERVER_DATABASE_CHANGE_GENERATIONS[key] += 1
    with SERVER_DATABASE_USER_PROFILE_CACHE_LOCK:
        SERVER_DATABASE_USER_PROFILE_CACHE.pop(normalized.lower(), None)
    with SERVER_DATABASE_PDF_DRAWING_RAM_CACHE_LOCK:
        for cache_key in tuple(SERVER_DATABASE_PDF_DRAWING_RAM_CACHE):
            if cache_key[0] == normalized.lower():
                SERVER_DATABASE_PDF_DRAWING_RAM_CACHE.pop(cache_key, None)
    return {
        "deleted": max(0, int(postgres_result.get("deleted", 0) or 0)),
        "postgres": postgres_result,
    }



def server_database_document_key(path: Path | str) -> tuple[str, str]:
    # Added 2026-07-20: document keys are lexical absolute paths; filesystem realpath resolution cost dominated cached reads.
    resolved = os.path.normpath(os.path.abspath(os.fspath(path)))
    return os.path.normcase(resolved), resolved


def server_database_document_local_only(path: Path | str) -> bool:
    target = Path(path)
    name = target.name.lower()
    if name in SERVER_DATABASE_LOCAL_ONLY_DOCUMENT_NAMES:
        return True
    if name.endswith(("_viewer_state.json", "_side_viewer_bridge.json", "_main_pdf_tool_state.json", "_image_viewer_state.json")):
        return True
    try:
        username = normalize_username(target.stem)
        valid_username, _message = validate_username(username)
        target_parent_key, _target_parent = server_database_document_key(target.parent)
        user_root_key, _user_root = server_database_document_key(USER_ROOT)
        return target_parent_key == user_root_key and target.suffix.lower() == ".txt" and valid_username and not name.startswith("__") and not name.endswith("_vocab_progress.txt")
    except Exception:
        return False


def server_database_document_postgres_authoritative(path: Path | str) -> bool:
    """Return whether a document path has an explicit PostgreSQL document owner."""
    routes = (
        ("QM_CITY_DOCUMENTS", "FUTURE.postgres.repositories.qm_city_documents", "is_qm_city_document"),
        ("LEADERBOARD_DOCUMENTS", "FUTURE.postgres.repositories.leaderboard_documents", "is_leaderboard_document"),
        ("QMDICT_DOCUMENTS", "FUTURE.postgres.repositories.qmdict_documents", "is_qmdict_document"),
        ("SPACE_PDF_AI_DOCUMENTS", "FUTURE.postgres.repositories.space_pdf_ai_documents", "is_space_pdf_ai_document"),
        ("VIEWER_TOOL_DOCUMENTS", "FUTURE.postgres.repositories.viewer_tool_documents", "is_viewer_tool_document"),
    )
    for domain, module_name, predicate_name in routes:
        if postgres_backend_mode(domain) != "postgres":
            continue
        try:
            module = __import__(module_name, fromlist=[predicate_name])
            if bool(getattr(module, predicate_name)(path)):
                return True
        except Exception:
            continue
    return False


def server_database_load_document_cache(connection=None) -> int:
    with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
        SERVER_DATABASE_DOCUMENT_CACHE.clear()
    return 0



def server_database_document_entry(path: Path | str) -> dict[str, object] | None:
    postgres_only = str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    if postgres_backend_mode("SYSTEM_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import system_documents as pg_system_documents
            if pg_system_documents.is_system_document(path):
                entry = pg_system_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_system_document_read_failed", path=str(path), error=str(exc))
    if postgres_backend_mode("QM_CITY_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import qm_city_documents as pg_qm_city_documents
            if pg_qm_city_documents.is_qm_city_document(path):
                entry = pg_qm_city_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_qm_city_document_read_failed", path=str(path), error=str(exc))
            # Added 2026-07-30: QM City PostgreSQL authority must never fall back to stale SQLite/cache state.
            raise
    if postgres_backend_mode("QMDICT_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import qmdict_documents as pg_qmdict_documents
            if pg_qmdict_documents.is_qmdict_document(path):
                entry = pg_qmdict_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_qmdict_document_read_failed", path=str(path), error=str(exc))
    if postgres_backend_mode("SPACE_PDF_AI_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import space_pdf_ai_documents as pg_space_pdf_ai_documents
            if pg_space_pdf_ai_documents.is_space_pdf_ai_document(path):
                entry = pg_space_pdf_ai_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_space_pdf_ai_document_read_failed", path=str(path), error=str(exc))
    if postgres_backend_mode("VIEWER_TOOL_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import viewer_tool_documents as pg_viewer_tool_documents
            if pg_viewer_tool_documents.is_viewer_tool_document(path):
                entry = pg_viewer_tool_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_viewer_tool_document_read_failed", path=str(path), error=str(exc))
    if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import leaderboard_documents as pg_leaderboard_documents
            if pg_leaderboard_documents.is_leaderboard_document(path):
                entry = pg_leaderboard_documents.read_entry(path)
                return dict(entry) if isinstance(entry, dict) else None
        except Exception as exc:
            stt_debug_log("postgres_leaderboard_document_read_failed", path=str(path), error=str(exc))
            # Added 2026-07-30: QM City leaderboard/social state is PostgreSQL-authoritative in production.
            raise
    if not postgres_only:
        initialize_server_database()
    path_key, _resolved = server_database_document_key(path)
    with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
        entry = SERVER_DATABASE_DOCUMENT_CACHE.get(path_key)
        return dict(entry) if isinstance(entry, dict) else None


def server_database_document_exists(path: Path | str) -> bool:
    return server_database_document_entry(path) is not None


def server_database_document_signature(path: Path | str) -> tuple[str, int, int, str]:
    entry = server_database_document_entry(path)
    if not isinstance(entry, dict):
        return (str(Path(path)), 0, 0, "")
    return (
        clean(entry.get("path")) or str(Path(path)),
        int(entry.get("file_mtime_ns", 0) or 0),
        int(entry.get("file_size", 0) or 0),
        clean(entry.get("sha256")),
    )


def server_database_read_document_text(path: Path | str, default: str | None = None) -> str | None:
    entry = server_database_document_entry(path)
    if not isinstance(entry, dict):
        return default
    encoding = clean(entry.get("encoding")) or "utf-8"
    return bytes(entry.get("content") or b"").decode(encoding, errors="replace")


def server_database_read_document_json(path: Path | str, default: object = None):
    text = server_database_read_document_text(path, None)
    if text is None:
        return copy.deepcopy(default)
    try:
        return json.loads(text.lstrip("\ufeff"))
    except Exception:
        return copy.deepcopy(default)


def server_database_document_requires_sync(path: Path | str) -> bool:
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix not in {".json", ".jsonl", ".txt"}:
        return False
    try:
        resolved = target.resolve()
        if SERVER_LOG_ROOT in resolved.parents:
            return False
    except Exception:
        pass
    name = target.name.lower()
    derived_markers = (
        ".wal.", "manifest", "boot_snapshot", "metadata_index", "audio_stem_index", "sound_asset_index",
        "refresh_progress", "refresh_report", "cache", "_future_space_w_progress",
        "_future_space_q_progress", "_future_space_v_progress", "_future_space_p_progress",
        "_future_space_pdf_progress", "_future_learned_vocabulary", "_future_vocab_leaderboard_periods",
        "_vocab_progress.txt", "distributed_worker_token", "future.hosted.obf", "key.txt",
    )
    return not any(marker in name for marker in derived_markers)


def server_database_store_document_now(path: Path | str, text: str, encoding: str = "utf-8", authoritative: bool = False) -> bool:
    target = Path(path)
    if target.suffix.lower() not in {".json", ".jsonl", ".txt"}:
        return False
    path_key, resolved = server_database_document_key(target)
    data = str(text).encode(encoding, errors="replace")
    try:
        mtime_ns = max(int(target.stat().st_mtime_ns), time.time_ns() if authoritative else 0)
    except Exception:
        mtime_ns = time.time_ns() if authoritative else 0
    # Added 2026-07-20: unchanged SQLite documents need neither SHA-256 nor a durable rewrite.
    with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
        cached = SERVER_DATABASE_DOCUMENT_CACHE.get(path_key)
        if (
            isinstance(cached, dict)
            and cached.get("content") == data
            and clean(cached.get("encoding", "utf-8")) == clean(encoding)
        ):
            return True
    updated_at_utc = utc_timestamp()
    digest = hashlib.sha256(data).hexdigest()
    if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import leaderboard_documents as pg_leaderboard_documents
            if pg_leaderboard_documents.is_leaderboard_document(target):
                pg_leaderboard_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_leaderboard_document_write_failed", path=str(target), error=str(exc))
            raise
    if postgres_backend_mode("SYSTEM_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import system_documents as pg_system_documents
            if pg_system_documents.is_system_document(target):
                pg_system_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_system_document_write_failed", path=str(target), error=str(exc))
            raise
    if postgres_backend_mode("QM_CITY_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import qm_city_documents as pg_qm_city_documents
            if pg_qm_city_documents.is_qm_city_document(target):
                pg_qm_city_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_qm_city_document_write_failed", path=str(target), error=str(exc))
            raise
    if postgres_backend_mode("QMDICT_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import qmdict_documents as pg_qmdict_documents
            if pg_qmdict_documents.is_qmdict_document(target):
                pg_qmdict_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_qmdict_document_write_failed", path=str(target), error=str(exc))
            raise
    if postgres_backend_mode("SPACE_PDF_AI_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import space_pdf_ai_documents as pg_space_pdf_ai_documents
            if pg_space_pdf_ai_documents.is_space_pdf_ai_document(target):
                pg_space_pdf_ai_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_space_pdf_ai_document_write_failed", path=str(target), error=str(exc))
            raise
    if postgres_backend_mode("VIEWER_TOOL_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import viewer_tool_documents as pg_viewer_tool_documents
            if pg_viewer_tool_documents.is_viewer_tool_document(target):
                pg_viewer_tool_documents.upsert_text(target, text, encoding, updated_at_utc, mtime_ns)
                with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
                    SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
                        "path": resolved,
                        "content": data,
                        "encoding": encoding,
                        "sha256": digest,
                        "file_size": len(data),
                        "file_mtime_ns": mtime_ns,
                        "updated_at_utc": updated_at_utc,
                    }
                return True
        except Exception as exc:
            stt_debug_log("postgres_viewer_tool_document_write_failed", path=str(target), error=str(exc))
            raise
    raise RuntimeError("No PostgreSQL document owner exists for this path.")


def _flush_server_database_document_worker() -> None:
    with SERVER_DATABASE_DOCUMENT_LOCK:
        SERVER_DATABASE_DOCUMENT_STATE["pending"] = {}
        SERVER_DATABASE_DOCUMENT_STATE["timer"] = None
        SERVER_DATABASE_DOCUMENT_STATE["writing"] = False



def server_database_schedule_document_mirror(path: Path | str, text: str, encoding: str = "utf-8") -> None:
    return



def flush_server_database_documents(force: bool = False) -> bool:
    _flush_server_database_document_worker()
    return True



def _flush_server_database_export_worker() -> None:
    while True:
        with SERVER_DATABASE_EXPORT_LOCK:
            pending = SERVER_DATABASE_EXPORT_STATE.get("pending")
            rows = dict(pending) if isinstance(pending, dict) else {}
            SERVER_DATABASE_EXPORT_STATE["pending"] = {}
            SERVER_DATABASE_EXPORT_STATE["timer"] = None
            SERVER_DATABASE_EXPORT_STATE["writing"] = True
        if not rows:
            with SERVER_DATABASE_EXPORT_LOCK:
                SERVER_DATABASE_EXPORT_STATE["writing"] = False
            return
        for path_text, row in rows.items():
            try:
                atomic_write_json(Path(path_text), row.get("payload"), indent=row.get("indent", 2))
            except Exception as exc:
                stt_debug_log("server_database_legacy_export_failed", path=path_text, error=str(exc))
        with SERVER_DATABASE_EXPORT_LOCK:
            pending = SERVER_DATABASE_EXPORT_STATE.get("pending")
            if not isinstance(pending, dict) or not pending:
                SERVER_DATABASE_EXPORT_STATE["writing"] = False
                return


def server_database_schedule_json_export(path: Path | str, payload: object, indent: int | None = 2) -> None:
    with SERVER_DATABASE_EXPORT_LOCK:
        pending = SERVER_DATABASE_EXPORT_STATE.get("pending")
        if not isinstance(pending, dict):
            pending = {}
            SERVER_DATABASE_EXPORT_STATE["pending"] = pending
        pending[str(Path(path).resolve())] = {"payload": copy.deepcopy(payload), "indent": indent}
        timer = SERVER_DATABASE_EXPORT_STATE.get("timer")
        if bool(SERVER_DATABASE_EXPORT_STATE.get("writing")) or (timer and timer.is_alive()):
            return
        timer = threading.Timer(0.5, _flush_server_database_export_worker)
        timer.daemon = True
        SERVER_DATABASE_EXPORT_STATE["timer"] = timer
        timer.start()


def flush_server_database_legacy_exports(force: bool = False) -> bool:
    with SERVER_DATABASE_EXPORT_LOCK:
        timer = SERVER_DATABASE_EXPORT_STATE.get("timer")
        if timer and timer.is_alive():
            timer.cancel()
        SERVER_DATABASE_EXPORT_STATE["timer"] = None
    _flush_server_database_export_worker()
    return True


def server_database_normalize_pdf_progress_record(record: dict | None = None) -> dict:
    source = dict(record) if isinstance(record, dict) else {}
    state = dict(source.get("state")) if isinstance(source.get("state"), dict) else {}
    raw_page = source.get("page", state.get("page"))
    if raw_page is None or clean(raw_page) == "":
        raw_node = source.get("currentNode", state.get("currentNode", source.get("nodeIndex", state.get("nodeIndex", 0))))
        one_based = space_w_int(source.get("nodeIndexBase", state.get("nodeIndexBase", 0)), 0) == 1 or space_w_int(source.get("version", 0), 0) >= 2
        page = max(1, space_w_int(raw_node, 0) if one_based else space_w_int(raw_node, 0) + 1)
    else:
        page = max(1, space_w_int(raw_page, 1))
    pages = max(0, space_w_int(source.get("pages", state.get("pages", source.get("nodeCount", state.get("nodeCount", 0)))), 0))
    source.update({
        "version": max(2, space_w_int(source.get("version", 0), 0)),
        "page": page,
        "pages": pages,
        "currentNode": page,
        "nodeIndex": page,
        "nodeIndexBase": 1,
        "nodeCount": pages,
    })
    state.update({"page": page, "pages": pages, "currentNode": page, "nodeIndex": page, "nodeIndexBase": 1})
    source["state"] = state
    return source


# Added 2026-07-23: one completion rule feeds SQLite columns, progress readers, migration, and leaderboard recovery.
def server_database_progress_completion_summary(record: dict | None = None, space: str = "") -> dict:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    normalized_space = clean(space) or clean(source.get("space") or state.get("space")) or "Space_W"
    marker_keys = (
        "complete",
        "completed",
        "lessonComplete",
        "lessonCompletionSent",
        "vocabComplete",
        "registryReady",
    )
    current_run_complete = any(
        truthy(source.get(key), False) or truthy(state.get(key), False)
        for key in marker_keys
    )
    if normalized_space == "Space_W" and (
        truthy(source.get("reviewFinished"), False)
        or truthy(state.get("reviewFinished"), False)
    ):
        current_run_complete = True

    # Added 2026-07-24: a newer identified run owns current progress even when
    # the payload still carries lifetime/review completion markers from an older run.
    if truthy(source.get("activeRun") or source.get("active_run"), False) or truthy(
        state.get("activeRun") or state.get("active_run"), False
    ):
        current_run_complete = False

    node_count = max(
        0,
        space_w_int(source.get("nodeCount", 0), 0),
        space_w_int(state.get("nodeCount", 0), 0),
    )
    learned_count = max(
        0,
        space_w_int(source.get("learnedCount", source.get("learned_count", 0)), 0),
        space_w_int(state.get("learnedCount", state.get("learned_count", 0)), 0),
    )
    if normalized_space == "Space_V":
        learned_rows = state.get("learned") if isinstance(state.get("learned"), list) else []
        learned_count = max(learned_count, len({clean(item).lower() for item in learned_rows if clean(item)}))
        if node_count and learned_count >= node_count:
            current_run_complete = True
    elif normalized_space == "Space_Q":
        question_total = max(
            0,
            space_w_int(state.get("questionTotal", state.get("totalQuestions", 0)), 0),
        )
        question_done = max(
            0,
            space_w_int(
                state.get("questionDone", state.get("completedQuestions", state.get("questionsDone", 0))),
                0,
            ),
        )
        if question_total and question_done >= question_total:
            current_run_complete = True
    elif normalized_space in {"Space_P", "Space_S", "Space_L"}:
        segment_total = max(
            0,
            space_w_int(
                state.get(
                    "totalSegments",
                    state.get("segmentTotal", state.get("totalTokens", state.get("tokenTotal", 0))),
                ),
                0,
            ),
        )
        segment_done = max(
            0,
            space_w_int(
                state.get(
                    "completedSegments",
                    state.get("segmentDone", state.get("completedTokens", state.get("tokenDone", 0))),
                ),
                0,
            ),
        )
        if segment_total and segment_done >= segment_total:
            current_run_complete = True

    # Added 2026-07-24: Space_W's root pass is only stage 1.  It must not be
    # treated as a completed run until the explicit review-finished/completion
    # transition arrives; otherwise entering Review inflates lifetime runs.
    node_progress = state.get("nodeProgress") if isinstance(state.get("nodeProgress"), dict) else {}
    if normalized_space != "Space_W" and node_count and len(node_progress) >= node_count:
        completed_nodes = 0
        for item in node_progress.values():
            if not isinstance(item, dict):
                continue
            if any(
                truthy(item.get(key), False)
                for key in ("nextPanelCanShow", "speakStepCompleted", "grammarStepCompleted", "reviewSpeakCompleted")
            ):
                completed_nodes += 1
        if completed_nodes >= node_count:
            current_run_complete = True

    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else {}
    lesson_study = lesson_source.get("study") if isinstance(lesson_source.get("study"), dict) else {}
    lesson_progress = lesson_study.get("progress") if isinstance(lesson_study.get("progress"), dict) else {}
    completed_runs = max(
        0,
        space_w_int(source.get("mine", 0), 0),
        space_w_int(source.get("completedRuns", source.get("completed_runs", 0)), 0),
        space_w_int(state.get("completedRuns", state.get("completed_runs", 0)), 0),
        space_w_int(lesson_study.get("mine", 0), 0),
        space_w_int(lesson_study.get("completedRuns", lesson_study.get("completed_runs", 0)), 0),
        space_w_int(lesson_progress.get("completedRuns", lesson_progress.get("completed_runs", 0)), 0),
    )
    if current_run_complete:
        completed_runs = max(completed_runs, 1)
    return {
        "space": normalized_space,
        "current_run_complete": bool(current_run_complete),
        "lifetime_complete": bool(completed_runs > 0),
        "completed_runs": completed_runs,
        "learned_count": learned_count,
        "node_count": node_count,
    }


def server_database_canonicalize_progress_completion(record: dict | None = None, space: str = "") -> tuple[dict, dict]:
    source = dict(record) if isinstance(record, dict) else {}
    summary = server_database_progress_completion_summary(source, space)
    current_run_complete = bool(summary.get("current_run_complete"))
    state = dict(source.get("state")) if isinstance(source.get("state"), dict) else {}
    active_run = truthy(source.get("activeRun") or source.get("active_run"), False) or truthy(
        state.get("activeRun") or state.get("active_run"), False
    )
    if active_run:
        for key in ("complete", "completed", "lessonComplete", "lessonCompletionSent", "vocabComplete", "registryReady"):
            if key in source or key == "complete":
                source[key] = False
            if key in state:
                state[key] = False
        for key in ("reviewFinished", "reviewComplete"):
            if key in source:
                source[key] = False
            if key in state:
                state[key] = False
    source["complete"] = current_run_complete
    if state or isinstance(source.get("state"), dict):
        state["complete"] = current_run_complete
        source["state"] = state
    completed_runs = max(0, space_w_int(summary.get("completed_runs", 0), 0))
    if completed_runs > 0:
        source["completedRuns"] = completed_runs
        source["completed_runs"] = completed_runs
        source["learned"] = True
        if summary.get("current_run_complete") and not clean(source.get("completedAt") or source.get("completed_at")):
            completed_at = clean(source.get("updatedAt") or source.get("savedAt"))
            if completed_at:
                source["completedAt"] = completed_at
    return source, summary




# Added 2026-07-24: separates current-run completion from lifetime history in every existing SQLite progress row.


# Added 2026-07-22: PDF/Picture business node numbers are one-based and equal the visible page.


# Added 2026-07-21: migration archives remain durable rollback evidence, while legacy path rows stay readable until reattached.


# Added 2026-07-23: hybrid Lesson Vault placement layer.  Physical lesson files
# remain watcher-owned; browser copy/move/rename/remove only changes these rows.
def _server_database_vault_id(prefix: str, seed: str = "") -> str:
    value = clean_path_value(seed).lower()
    if value:
        return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:28]}"
    return f"{prefix}-{uuid.uuid4().hex[:28]}"




# Added 2026-07-24: choose the populated active subtree when stale duplicate
# virtual placements share one visible path; never let SQLite row order decide
# which learner tree is returned.
def _server_database_vault_build_path_cache(folders: list[dict], entries: list[dict]) -> tuple[dict, dict]:
    by_id = {clean(row.get("vault_folder_id")): row for row in folders if clean(row.get("vault_folder_id"))}
    children: dict[str, list[str]] = {}
    entry_counts: dict[str, int] = {}
    for row in folders:
        folder_id = clean(row.get("vault_folder_id"))
        parent_id = clean(row.get("parent_folder_id"))
        if folder_id:
            children.setdefault(parent_id, []).append(folder_id)
    for row in entries:
        parent_id = clean(row.get("parent_folder_id"))
        entry_counts[parent_id] = entry_counts.get(parent_id, 0) + 1
    score_cache: dict[str, int] = {}

    def subtree_score(folder_id: str) -> int:
        if folder_id in score_cache:
            return score_cache[folder_id]
        score = entry_counts.get(folder_id, 0)
        for child_id in children.get(folder_id, []):
            score += 1 + subtree_score(child_id)
        score_cache[folder_id] = score
        return score

    for folder_id in by_id:
        subtree_score(folder_id)

    path_cache: dict[str, dict] = {}

    def put_path(key: str, item: dict, score: int = 0) -> None:
        normalized = clean_path_value(key).lower()
        if not normalized:
            return
        existing = path_cache.get(normalized)
        if existing is None:
            path_cache[normalized] = item
            item.setdefault("_vault_path_score", score)
            return
        existing_score = int(existing.get("_vault_path_score", 0) or 0)
        if score > existing_score:
            item.setdefault("_vault_path_score", score)
            path_cache[normalized] = item

    unresolved = list(folders)
    for _ in range(len(folders) + 1):
        progressed = False
        for row in list(unresolved):
            folder_id = clean(row.get("vault_folder_id"))
            parent_id = clean(row.get("parent_folder_id"))
            if not parent_id:
                path = clean_path_value(row.get("username", ""))
            else:
                parent = path_cache.get(parent_id)
                if not parent:
                    continue
                path = clean_path_value(f"{parent['path']}/{row.get('display_name', '')}")
            item = dict(row)
            item["path"] = path
            item["_vault_path_score"] = score_cache.get(folder_id, 0)
            # Folder IDs remain addressable even when their display paths collide.
            path_cache[folder_id] = item
            put_path(path, item, score_cache.get(folder_id, 0))
            unresolved.remove(row)
            progressed = True
        if not unresolved or not progressed:
            break
    for row in unresolved:
        folder_id = clean(row.get("vault_folder_id"))
        item = dict(row)
        item["path"] = clean_path_value(f"{row.get('username', '')}/{row.get('display_name', '')}")
        item["_vault_path_score"] = score_cache.get(folder_id, 0)
        path_cache[folder_id] = item
        put_path(item["path"], item, score_cache.get(folder_id, 0))

    entry_cache: dict[str, dict] = {}
    for row in entries:
        parent = path_cache.get(clean(row.get("parent_folder_id")))
        if not parent:
            continue
        item = dict(row)
        item["path"] = clean_path_value(f"{parent['path']}/{row.get('display_name', '')}")
        entry_id = clean(row.get("vault_entry_id"))
        entry_cache[entry_id] = item
        put_path(item["path"], item, 1)
    return path_cache, entry_cache

def _server_database_vault_index_by_user(rows: dict[str, dict]) -> dict[str, dict[str, dict]]:
    indexed: dict[str, dict[str, dict]] = {}
    for key, item in (rows or {}).items():
        if not isinstance(item, dict):
            continue
        user = normalize_username(item.get("username", "")).lower()
        if not user:
            continue
        indexed.setdefault(user, {})[key] = item
    return indexed


def server_database_load_vault_cache(connection=None) -> int:
    from FUTURE.postgres.repositories import vault as pg_vault
    payload = pg_vault.load_cache_rows()
    folders = list(payload.get("folders", []))
    entries = list(payload.get("entries", []))
    revisions = dict(payload.get("revisions", {}))
    folder_ids = {clean(row.get("vault_folder_id")) for row in folders}
    legacy_shells = set()
    for link_path in payload.get("link_paths", []):
        path = clean_path_value(link_path)
        user = normalize_username(path.split("/", 1)[0])
        if path and _server_database_vault_id("vault-folder", f"{user}|{path}") in folder_ids:
            legacy_shells.add(path.lower())
    path_cache, entry_cache = _server_database_vault_build_path_cache(folders, entries)
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        SERVER_DATABASE_VAULT_FOLDER_CACHE.clear()
        SERVER_DATABASE_VAULT_FOLDER_CACHE.update({key: value for key, value in path_cache.items() if value.get("vault_folder_id")})
        SERVER_DATABASE_VAULT_ENTRY_CACHE.clear()
        SERVER_DATABASE_VAULT_ENTRY_CACHE.update(entry_cache)
        SERVER_DATABASE_VAULT_PATH_CACHE.clear()
        SERVER_DATABASE_VAULT_PATH_CACHE.update(path_cache)
        SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER.clear()
        SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER.update(_server_database_vault_index_by_user(SERVER_DATABASE_VAULT_FOLDER_CACHE))
        SERVER_DATABASE_VAULT_ENTRY_CACHE_BY_USER.clear()
        SERVER_DATABASE_VAULT_ENTRY_CACHE_BY_USER.update(_server_database_vault_index_by_user(SERVER_DATABASE_VAULT_ENTRY_CACHE))
        SERVER_DATABASE_VAULT_REVISION_CACHE.clear()
        SERVER_DATABASE_VAULT_REVISION_CACHE.update(revisions)
        SERVER_DATABASE_VAULT_LEGACY_SHELLS.clear()
        SERVER_DATABASE_VAULT_LEGACY_SHELLS.update(legacy_shells)
    return len(folders) + len(entries)


def server_database_reload_vault_user_cache(username: str = "") -> int:
    """Refresh one user's virtual tree after a metadata transaction."""
    user = normalize_username(username)
    if not user:
        return 0
    from FUTURE.postgres.repositories import vault as pg_vault
    payload = pg_vault.load_cache_rows(user)
    folders = list(payload.get("folders", []))
    entries = list(payload.get("entries", []))
    revisions = dict(payload.get("revisions", {}))
    path_cache, entry_cache = _server_database_vault_build_path_cache(folders, entries)
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        for cache in (SERVER_DATABASE_VAULT_FOLDER_CACHE, SERVER_DATABASE_VAULT_PATH_CACHE):
            for key in [key for key, item in cache.items() if normalize_username(item.get("username", "")).lower() == user.lower()]:
                cache.pop(key, None)
        for key in [key for key, item in SERVER_DATABASE_VAULT_ENTRY_CACHE.items() if normalize_username(item.get("username", "")).lower() == user.lower()]:
            SERVER_DATABASE_VAULT_ENTRY_CACHE.pop(key, None)
        SERVER_DATABASE_VAULT_FOLDER_CACHE.update({key: value for key, value in path_cache.items() if value.get("vault_folder_id")})
        SERVER_DATABASE_VAULT_ENTRY_CACHE.update(entry_cache)
        SERVER_DATABASE_VAULT_PATH_CACHE.update(path_cache)
        SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER[user.lower()] = _server_database_vault_index_by_user({key: value for key, value in path_cache.items() if value.get("vault_folder_id")}).get(user.lower(), {})
        SERVER_DATABASE_VAULT_ENTRY_CACHE_BY_USER[user.lower()] = _server_database_vault_index_by_user(entry_cache).get(user.lower(), {})
        SERVER_DATABASE_VAULT_REVISION_CACHE[user.lower()] = max(0, int(revisions.get(user.lower(), 0) or 0))
    return len(folders) + len(entries)


def server_database_vault_match(path_value: str = "") -> dict:
    path = clean_path_value(path_value).lower()
    if not path:
        return {}
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        exact = SERVER_DATABASE_VAULT_PATH_CACHE.get(path)
        if exact and exact.get("vault_folder_id"):
            result = dict(exact)
            result["suffix"] = ""
            return result
        matches = []
        for key, item in SERVER_DATABASE_VAULT_FOLDER_CACHE.items():
            if "/" not in key and key.startswith("vault-"):
                continue
            if clean(item.get("folder_type", "")).upper() not in {"COMMON_REFERENCE", "PHYSICAL_REFERENCE"}:
                continue
            if path.startswith(key + "/"):
                matches.append((key, item))
        if not matches:
            return {}
        root, item = max(matches, key=lambda pair: len(pair[0]))
        result = dict(item)
        result["suffix"] = path[len(root):].lstrip("/")
        result["vault_path"] = root
        return result


def server_database_vault_entry_for_path(path_value: str = "") -> dict:
    path = clean_path_value(path_value).lower()
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        item = SERVER_DATABASE_VAULT_PATH_CACHE.get(path)
        if item and item.get("vault_entry_id"):
            return dict(item)
    return {}


def server_database_vault_resolved_source_path(entry_or_path: dict | str = "") -> str:
    entry = dict(entry_or_path) if isinstance(entry_or_path, dict) else server_database_vault_entry_for_path(entry_or_path)
    lesson_id = clean(entry.get("lesson_id", ""))
    replica_id = entry.get("physical_replica_id")
    if replica_id:
        from FUTURE.postgres.repositories import vault as pg_vault
        resolved = pg_vault.resolved_source_path(replica_id, lesson_id)
        if resolved:
            return resolved
    current = server_database_lesson_current_path(lesson_id) if lesson_id else ""
    return clean_path_value(current or entry.get("source_path", ""))


def server_database_vault_children(folder_id: str = "", username: str = "") -> list[dict]:
    parent = clean(folder_id)
    user = normalize_username(username)
    if not parent:
        parent = _server_database_vault_root_id(user)
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        folders = []
        for item in SERVER_DATABASE_VAULT_FOLDER_CACHE.values():
            if clean(item.get("parent_folder_id")) == parent and (not user or normalize_username(item.get("username")) == user):
                if not any(clean(existing.get("vault_folder_id")) == clean(item.get("vault_folder_id")) for existing in folders):
                    folders.append(dict(item))
        entries = [dict(item) for item in SERVER_DATABASE_VAULT_ENTRY_CACHE.values()
                   if clean(item.get("parent_folder_id")) == parent and (not user or normalize_username(item.get("username")) == user)]
    folders.sort(key=lambda item: (int(item.get("sort_order", 0) or 0), natural_sort_key(item.get("display_name", ""))))
    entries.sort(key=lambda item: (int(item.get("sort_order", 0) or 0), natural_sort_key(item.get("display_name", ""))))
    return folders + entries


# Added 2026-07-23: return only the target user's virtual folder metadata for destination pickers.
def server_database_vault_folder_rows(username: str = "") -> list[dict]:
    user = normalize_username(username)
    if not user:
        return []
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        values = list(SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER.get(user.lower(), {}).values())
    unique = {}
    for row in values:
        folder_id = clean(row.get("vault_folder_id", ""))
        if folder_id:
            unique[folder_id] = dict(row)
    rows = sorted(
        unique.values(),
        key=lambda row: (
            clean(row.get("parent_folder_id", "")).lower(),
            0 if int(row.get("sort_order", 0) or 0) > 0 else 1,
            int(row.get("sort_order", 0) or 0),
            clean(row.get("display_name", "")).lower(),
        ),
    )
    return [
        {
            "vault_folder_id": clean(row.get("vault_folder_id", "")),
            "parent_folder_id": clean(row.get("parent_folder_id", "")),
            "display_name": clean(row.get("display_name", "")),
            "folder_type": clean(row.get("folder_type", "")),
            "sort_order": int(row.get("sort_order", 0) or 0),
        }
        for row in rows
    ]


def server_database_vault_is_legacy_shell(path_value: str = "") -> bool:
    path = clean_path_value(path_value).lower()
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        return bool(path and path in SERVER_DATABASE_VAULT_LEGACY_SHELLS)


def server_database_vault_revision(username: str = "") -> int:
    user = normalize_username(username)
    if not user:
        return 0
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        return max(0, int(SERVER_DATABASE_VAULT_REVISION_CACHE.get(user.lower(), 0) or 0))


def _server_database_vault_patch_created_folder(row: dict, destination: str, revision: int) -> bool:
    """Added 2026-07-29: patch one committed PostgreSQL folder without reloading a user's Vault."""
    user = normalize_username(row.get("username", ""))
    folder_id = clean(row.get("vault_folder_id", ""))
    destination_path = clean_path_value(destination)
    if not user or not folder_id or not destination_path:
        return False
    item = dict(row)
    item["path"] = clean_path_value(f"{destination_path}/{row.get('display_name', '')}")
    item["_vault_path_score"] = 0
    user_key = user.lower()
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        parent = SERVER_DATABASE_VAULT_PATH_CACHE.get(destination_path.lower())
        if destination_path.lower() == user_key and not parent:
            root_id = _server_database_vault_root_id(user)
            parent = {
                "vault_folder_id": root_id,
                "username": user,
                "parent_folder_id": "",
                "display_name": user,
                "folder_type": "ROOT",
                "source_path": user,
                "sort_order": 0,
                "status": "active",
                "path": user,
                "_vault_path_score": 1,
            }
            SERVER_DATABASE_VAULT_FOLDER_CACHE[root_id] = parent
            SERVER_DATABASE_VAULT_FOLDER_CACHE[user_key] = parent
            SERVER_DATABASE_VAULT_PATH_CACHE[root_id] = parent
            SERVER_DATABASE_VAULT_PATH_CACHE[user_key] = parent
            SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER.setdefault(user_key, {})[root_id] = parent
            SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER[user_key][user_key] = parent
        if not parent or clean(parent.get("vault_folder_id", "")) != clean(row.get("parent_folder_id", "")):
            return False
        path_key = item["path"].lower()
        SERVER_DATABASE_VAULT_FOLDER_CACHE[folder_id] = item
        SERVER_DATABASE_VAULT_FOLDER_CACHE[path_key] = item
        SERVER_DATABASE_VAULT_PATH_CACHE[folder_id] = item
        SERVER_DATABASE_VAULT_PATH_CACHE[path_key] = item
        SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER.setdefault(user_key, {})[folder_id] = item
        SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER[user_key][path_key] = item
        SERVER_DATABASE_VAULT_REVISION_CACHE[user_key] = max(
            max(0, int(SERVER_DATABASE_VAULT_REVISION_CACHE.get(user_key, 0) or 0)),
            max(1, int(revision or 1)),
        )
    return True


def _server_database_vault_root_id(username: str) -> str:
    return _server_database_vault_id("vault-root", normalize_username(username))








def server_database_vault_reload_cache() -> int:
    return server_database_load_vault_cache(None)






def server_database_vault_operation(payload: dict, actor_username: str = "") -> dict:
    """Apply a browser Vault operation as one SQLite transaction only."""
    if not SERVER_DATABASE_VAULT_ENABLED:
        return {}
    viewer = normalize_username(actor_username)
    user = normalize_username(payload.get("target_user", "") or payload.get("user", "") or viewer)
    action = clean(payload.get("action", "")).lower().replace("-", "_")
    if action in {"copy", "link", "copylink", "get"}:
        action = "copy_link"
    if action in {"cut", "paste_move"}:
        action = "move"
    if action in {"delete", "unlink", "remove_link"}:
        action = "delete_link"
    if action == "rename":
        action = "rename"
    if action in {"mkdir", "new_folder", "create_folder"}:
        action = "create_folder"
    reorder_direction = ""
    if action in {"move_up", "move_down", "reorder"}:
        reorder_direction = clean(payload.get("direction", "") or action.removeprefix("move_")).lower()
        action = "reorder"
    if action not in {"copy_link", "move", "delete_link", "rename", "create_folder", "reorder"}:
        return {}
    source_raw = clean_path_value(payload.get("source", "") or payload.get("path", ""))
    destination_raw = clean_path_value(payload.get("destination", "") or payload.get("target", "") or payload.get("folder", ""))
    if not viewer or not user or (action != "create_folder" and not source_raw) or (action in {"copy_link", "move", "create_folder"} and not destination_raw):
        raise RuntimeError("Missing Vault operation fields.")
    viewer_is_admin = is_admin_user(viewer)
    if user.lower() != viewer.lower() and not viewer_is_admin:
        raise RuntimeError("Only admins can manage another user's Vault.")
    if not server_database_user_exists(user):
        raise RuntimeError("Target user does not exist.")
    source_top = server_data_path_top(source_raw)
    destination_top = server_data_path_top(destination_raw)
    if destination_top and destination_top not in {"common", user.lower()}:
        raise RuntimeError("Vault destination must belong to the selected target user.")
    if source_top and source_top not in {"common", user.lower()} and action != "copy_link":
        raise RuntimeError("Vault source does not belong to the selected target user.")
    if source_raw and server_data_path_top(source_raw) == "common" and action != "copy_link":
        raise RuntimeError("COMMON_LIBRARY_READ_ONLY")
    if destination_raw and server_data_path_top(destination_raw) == "common":
        raise RuntimeError("COMMON_LIBRARY_READ_ONLY")
    old_entry = server_database_vault_entry_for_path(source_raw)
    old_folder = server_database_vault_match(source_raw)
    if old_folder and old_folder.get("suffix"):
        old_folder = {}
    now = utc_timestamp()
    result = {}
    from FUTURE.postgres.repositories import vault as pg_vault
    folder_id = _server_database_vault_id("vault-folder")
    row = pg_vault.create_virtual_folder(
        user,
        destination_raw,
        clean(payload.get("display_name", "") or payload.get("name", "")) or "New folder",
        folder_id,
        now,
    )
    if not _server_database_vault_patch_created_folder(row, destination_raw, int(row.get("revision", 1) or 1)):
        server_database_reload_vault_user_cache(user)
    return {
        "path": clean_path_value(f"{destination_raw}/{row.get('display_name', '')}"),
        "name": clean(row.get("display_name", "")),
        "type": "folder",
        "vault_folder_id": folder_id,
        "vault_revision": max(1, int(row.get("revision", 1) or 1)),
        "virtual": True,
    }


# Added 2026-07-21: folder-link roots are canonical SQLite rows; propagated child markers remain rollback-only.


# Added 2026-07-21: folder-link roots are canonical SQLite rows; propagated child markers remain rollback-only.
def _server_database_folder_link_relative(path_value: Path | str = "") -> str:
    raw = os.path.normpath(os.path.abspath(os.fspath(path_value)))
    try:
        relative = Path(raw).resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
    except Exception:
        relative = clean_path_value(path_value)
    marker_suffix = "/" + clean(globals().get("SERVER_DATA_FOLDER_LINK_FILE", "._future_folder_link.json"))
    if relative.lower().endswith(marker_suffix.lower()):
        relative = relative[:-len(marker_suffix)]
    return clean_path_value(relative)








def server_database_folder_link_payload(path_value: Path | str = "") -> dict:
    relative = _server_database_folder_link_relative(path_value).lower()
    if not relative:
        return {}
    with SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK:
        payload = SERVER_DATABASE_FOLDER_LINK_CACHE.get(relative)
        return dict(payload) if isinstance(payload, dict) else {}


def server_database_folder_link_match(path_value: Path | str = "") -> dict:
    relative = _server_database_folder_link_relative(path_value)
    if not relative:
        return {}
    vault_matcher = globals().get("server_database_vault_match")
    if SERVER_DATABASE_VAULT_ENABLED and callable(vault_matcher):
        virtual = vault_matcher(relative)
        if virtual and virtual.get("vault_folder_id") and clean(virtual.get("folder_type", "")).upper() in {"COMMON_REFERENCE", "PHYSICAL_REFERENCE"}:
            result = dict(virtual)
            result.setdefault("target", clean_path_value(virtual.get("source_path", "")))
            result.setdefault("target_type", "folder")
            result.setdefault("created_by", normalize_username(virtual.get("username", "")))
            result["link_path"] = clean_path_value(virtual.get("path", relative)).lower()
            result["requested_path"] = relative
            return result
    lowered = relative.lower()
    with SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK:
        matches = [
            (root, payload)
            for root, payload in SERVER_DATABASE_FOLDER_LINK_CACHE.items()
            if lowered == root or lowered.startswith(root + "/")
        ]
    if not matches:
        return {}
    root, payload = max(matches, key=lambda item: len(item[0]))
    result = dict(payload)
    result["link_path"] = root
    result["requested_path"] = relative
    result["suffix"] = relative[len(root):].lstrip("/")
    return result


def server_database_folder_link_registry_ready() -> bool:
    with SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK:
        legacy_ready = bool(SERVER_DATABASE_FOLDER_LINK_CACHE)
    with SERVER_DATABASE_VAULT_CACHE_LOCK:
        return bool(legacy_ready or (SERVER_DATABASE_VAULT_ENABLED and SERVER_DATABASE_VAULT_FOLDER_CACHE))


def server_database_delete_folder_link(path_value: Path | str = "") -> bool:
    relative = _server_database_folder_link_relative(path_value)
    if not relative:
        return False
    marker_name = clean(globals().get("SERVER_DATA_FOLDER_LINK_FILE", "._future_folder_link.json"))
    marker_path = SERVER_DATA_ROOT.joinpath(*relative.split("/")) / marker_name
    path_key, _resolved = server_database_document_key(marker_path)
    from FUTURE.postgres.repositories import vault as pg_vault
    result = bool(pg_vault.delete_folder_link(relative))
    if result:
        with SERVER_DATABASE_FOLDER_LINK_CACHE_LOCK:
            SERVER_DATABASE_FOLDER_LINK_CACHE.pop(relative.lower(), None)
        with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
            SERVER_DATABASE_DOCUMENT_CACHE.pop(path_key, None)
    return result



# Added 2026-07-21: SQLite active/quarantine state is preloaded before tree warming or learner requests.


def server_database_lesson_identity_registry_ready() -> bool:
    with SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK:
        return bool(SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE)


def _server_database_progress_record_order(record: dict | None = None) -> tuple[float, int, str]:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    stamp = source.get("updatedAt") or source.get("savedAt") or state.get("updatedAt") or state.get("savedAt") or ""
    revision = max(0, space_w_int(source.get("_serverRevision", source.get("serverRevision", 0)), 0))
    run_id = clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id"))
    return max(0.0, timestamp_to_epoch(stamp)), revision, run_id


def _server_database_merge_identity_progress_records(left: dict | None, right: dict | None) -> dict:
    old = left if isinstance(left, dict) else {}
    new = right if isinstance(right, dict) else {}
    winner = dict(new if _server_database_progress_record_order(new) >= _server_database_progress_record_order(old) else old)
    old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
    new_state = new.get("state") if isinstance(new.get("state"), dict) else {}
    winner_state = dict(winner.get("state")) if isinstance(winner.get("state"), dict) else {}
    completed_runs = max(
        max(0, space_w_int(old.get("completedRuns", old.get("completed_runs", old_state.get("completedRuns", 0))), 0)),
        max(0, space_w_int(new.get("completedRuns", new.get("completed_runs", new_state.get("completedRuns", 0))), 0)),
    )
    if completed_runs:
        winner["completedRuns"] = completed_runs
        winner["completed_runs"] = completed_runs
        winner_state["completedRuns"] = completed_runs
    if truthy(old.get("learned") or old_state.get("learned") or new.get("learned") or new_state.get("learned"), False):
        winner["learned"] = True
        winner_state["learned"] = True
    if winner_state:
        winner["state"] = winner_state
    return winner


# Added 2026-07-21: an exact returning path atomically upgrades restored legacy progress to its portable file ID.


# Added 2026-07-21: native-watcher deltas atomically retire touched locations and register their current Space IDs.
def server_database_register_lesson_file_entries(
    entries: list[dict] | tuple[dict, ...],
    inactive_paths: list[str] | tuple[str, ...] | set[str] = (),
) -> dict:
    rows = [dict(entry) for entry in (entries or []) if isinstance(entry, dict) and clean(entry.get("lesson_id", ""))]
    normalized_inactive = sorted({clean_path_value(path) for path in (inactive_paths or []) if clean_path_value(path)})
    if not rows and not normalized_inactive:
        return {"ok": True, "registered": 0, "collisions": 0, "inactive": 0}
    from FUTURE.postgres.repositories import lesson_identity as pg_lesson_identity
    result = pg_lesson_identity.register_lesson_file_entries(rows, normalized_inactive)
    reattached_users = [normalize_username(value) for value in result.get("reattached_users", []) if normalize_username(value)]
    if reattached_users:
        SERVER_DATABASE_CHANGE_GENERATIONS["progress"] += 1
        for affected_user in reattached_users:
            server_database_bump_user_generation("progress", affected_user)
    with SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK:
        for cache_key in list(SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE):
            if any(
                cache_key == path.lower() or cache_key.startswith(f"{path.lower()}/")
                for path in normalized_inactive
            ):
                SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(cache_key, None)
        for raw_path, file_id in result.get("active_aliases", []):
            path = clean_path_value(raw_path).lower()
            if path and file_id:
                SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE[path] = file_id
        for raw_path in result.get("quarantined_aliases", []):
            path = clean_path_value(raw_path).lower()
            if path:
                SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(path, None)
    result.pop("active_aliases", None)
    result.pop("quarantined_aliases", None)
    result.pop("reattached_users", None)
    for rebound_user in result.pop("rebound_vault_users", []) or []:
        server_database_reload_vault_user_cache(rebound_user)
    return result


def server_database_lesson_file_count() -> int:
    try:
        return max(0, int(postgres_lesson_file_count() or 0))
    except Exception:
        return 0


def server_database_lesson_file_id_for_path(path_value: str = "") -> str:
    path = clean_path_value(path_value)
    if not path:
        return ""
    from FUTURE.postgres.repositories import lesson_identity as pg_lesson_identity
    cache_key = path.lower()
    with SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK:
        if cache_key in SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE:
            return SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE[cache_key]
    file_id = pg_lesson_identity.postgres_file_id_for_path(path)
    with SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK:
        SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE[cache_key] = file_id
    return file_id


def server_database_lesson_current_path(file_id_value: str = "") -> str:
    file_id = clean(file_id_value)[:240]
    if not file_id:
        return ""
    from FUTURE.postgres.repositories import lesson_identity as pg_lesson_identity
    return pg_lesson_identity.postgres_current_path(file_id)


def server_database_mark_lesson_file_paths_inactive(paths: list[str] | tuple[str, ...] | set[str]) -> int:
    normalized = sorted({clean_path_value(path) for path in (paths or []) if clean_path_value(path)})
    if not normalized:
        return 0
    from FUTURE.postgres.repositories import lesson_identity as pg_lesson_identity
    changed = pg_lesson_identity.mark_lesson_file_paths_inactive(normalized)
    if changed:
        with SERVER_DATABASE_LESSON_FILE_ALIAS_LOCK:
            for cache_key in list(SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE):
                if any(cache_key == path.lower() or cache_key.startswith(f"{path.lower()}/") for path in normalized):
                    SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(cache_key, None)
    return int(changed or 0)




def server_database_begin_learning_completion(payload: dict) -> dict:
    source = payload if isinstance(payload, dict) else {}
    event_key = clean(source.get("event_key", ""))[:160]
    if not event_key:
        raise RuntimeError("Lesson completion event key is required.")
    return postgres_begin_learning_completion(source)


def server_database_learning_completion_complete(event_key: str) -> bool:
    return postgres_learning_completion_complete(event_key)


# Added 2026-07-22: commit the final completion event and its derived per-user summary in one FULL transaction.
def server_database_finalize_learning_completion(payload: dict, summary_path: Path | str, summary_payload: dict) -> dict:
    source = {**(payload if isinstance(payload, dict) else {}), "status": "final"}
    source.pop("intent_with_progress", None)
    source.pop("learning_summary_payload", None)
    target = Path(summary_path)
    path_key, resolved = server_database_document_key(target)
    data = json.dumps(summary_payload if isinstance(summary_payload, dict) else {}, ensure_ascii=False, indent=2).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    updated_at_utc = utc_timestamp()
    mtime_ns = time.time_ns()
    event_result = postgres_append_event("learning", source)
    from FUTURE.postgres.repositories import learning_summary_documents as pg_learning_summary_documents
    document_result = pg_learning_summary_documents.upsert_json(target, summary_payload if isinstance(summary_payload, dict) else {})
    with SERVER_DATABASE_DOCUMENT_CACHE_LOCK:
        SERVER_DATABASE_DOCUMENT_CACHE[path_key] = {
            "path": resolved,
            "content": data,
            "encoding": "utf-8",
            "sha256": digest,
            "file_size": len(data),
            "file_mtime_ns": mtime_ns,
            "updated_at_utc": updated_at_utc,
        }
    return {"ok": True, "event_key": clean(event_result.get("event_key", "")), "document": document_result}



def server_database_apply_progress_entry(space: str, username: str, entry: dict) -> dict:
    result = postgres_apply_lesson_progress_entry(space, username, entry)
    SERVER_DATABASE_CHANGE_GENERATIONS["progress"] += 1
    server_database_bump_user_generation("progress", username)
    return result


def server_database_write_lesson_progress(username: str, space: str, key: str, record: dict) -> dict:
    # Added 2026-07-26: compatibility wrapper for Space_V registry/recovery paths
    # after lesson progress moved behind the PostgreSQL-aware adapter.
    normalized_key = clean(key)
    payload = record if isinstance(record, dict) else {}
    return server_database_apply_progress_entry(
        space,
        username,
        {
            "op": "upsert",
            "key": normalized_key,
            "record": payload,
            "file_id": clean(payload.get("file_id") or payload.get("lesson_id") or payload.get("identity")),
            "lesson_id": clean(payload.get("lesson_id") or payload.get("file_id") or payload.get("identity")),
            "identity": clean(payload.get("identity") or payload.get("lesson_id") or payload.get("file_id")),
        },
    )


def server_database_replace_progress_payload(space: str, username: str, payload: dict) -> dict:
    result = postgres_replace_lesson_progress_payload(space, username, payload)
    SERVER_DATABASE_CHANGE_GENERATIONS["progress"] += 1
    server_database_bump_user_generation("progress", username)
    return result


def server_database_load_progress_payload(space: str, username: str) -> dict | None:
    return postgres_load_lesson_progress_payload(space, username)


def server_database_load_progress_payloads(username: str, spaces: object = None) -> dict[str, dict]:
    """Added 2026-07-28: batch read progress namespaces for login snapshots."""
    normalized_user = normalize_username(username)
    normalized_spaces = [
        normalize_space_progress_space(space)
        for space in (spaces or [])
        if normalize_space_progress_space(space)
    ]
    if not normalized_user or not normalized_spaces:
        return {}
    return postgres_load_lesson_progress_payloads(normalized_user, normalized_spaces)




def server_database_load_vocab_registry(username: str) -> dict | None:
    normalized_user = normalize_username(username)
    generation = server_database_user_generation("registry", normalized_user)
    cached = SERVER_DATABASE_REGISTRY_RAM_CACHE.get(normalized_user.lower())
    if isinstance(cached, dict) and int(cached.get("generation", -1)) == generation and isinstance(cached.get("payload"), dict):
        return copy.deepcopy(cached["payload"])
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    payload = pg_vocabulary.load_registry(normalized_user)
    if isinstance(payload, dict):
        SERVER_DATABASE_REGISTRY_RAM_CACHE[normalized_user.lower()] = {"generation": generation, "payload": copy.deepcopy(payload)}
    return payload


def server_database_vocab_registry_summary(username: str) -> dict:
    # Added 2026-07-20: avoids loading legacy JSON or cloning all words for leaderboard summaries.
    normalized_user = normalize_username(username)
    if not normalized_user:
        return {"total_words": 0, "updated_at": ""}
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    return pg_vocabulary.registry_summary(normalized_user)


def server_database_vocab_file_key_stats(username: str, word_keys: list[str], buckets: dict, resets: dict | None = None) -> dict:
    """Added 2026-07-29: return compact per-file New/Earn counts from authoritative tables."""
    normalized_user = normalize_username(username)
    keys = sorted({vocab_key(value) for value in (word_keys or []) if vocab_key(value)})
    total = len(keys)
    if not normalized_user or not keys:
        return {"total_words": total, "known_words": 0, "new_words": total, "top_earnable": {scope: total for scope in ("day", "week", "month")}}
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    return pg_vocabulary.file_key_stats(normalized_user, keys, buckets, resets)


def server_database_replace_vocab_registry(username: str, registry: dict) -> dict:
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    result = pg_vocabulary.replace_registry(username, registry)
    SERVER_DATABASE_CHANGE_GENERATIONS["registry"] += 1
    server_database_bump_user_generation("registry", username)
    SERVER_DATABASE_REGISTRY_RAM_CACHE.pop(normalize_username(username).lower(), None)
    return result


def server_database_record_vocabulary_transaction(
    username: str,
    learned: list[dict],
    source_path: str,
    increment_count: bool,
    now_stamp: str,
    buckets: dict,
    run_marker: str = "",
    record_period_activity: bool = True,
    progress_record: dict | None = None,
    completion_event: dict | None = None,
) -> dict:
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    result = pg_vocabulary.record_transaction(
        username,
        learned,
        source_path,
        increment_count,
        now_stamp,
        buckets,
        run_marker=run_marker,
        record_period_activity=record_period_activity,
    )
    if isinstance(progress_record, dict) and clean(progress_record.get("key", "")):
        server_database_write_lesson_progress(username, "Space_V", clean(progress_record.get("key", "")), progress_record)
    SERVER_DATABASE_CHANGE_GENERATIONS["registry"] += 1
    server_database_bump_user_generation("registry", username)
    if any(int(value or 0) > 0 for value in result.get("recorded", {}).values()):
        SERVER_DATABASE_CHANGE_GENERATIONS["period"] += 1
        server_database_bump_user_generation("period", username)
    if isinstance(completion_event, dict):
        event_key = server_database_append_event("learning", completion_event).get("event_key", "")
        if clean(event_key):
            result["event_key"] = clean(event_key)
    return result


def server_database_period_scopes(username: str, buckets: dict, resets: dict | None = None) -> dict:
    normalized_user = normalize_username(username)
    # Updated 2026-07-29: PostgreSQL-only recovery must not depend on a local SQLite file existing.
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    return pg_vocabulary.period_scopes(normalized_user, buckets, resets)


# Added 2026-07-20: synthetic racers persist period scores without becoming login users.
def server_database_record_npc_period_activity(username: str, scopes: dict) -> dict:
    normalized_user = normalize_username(username)
    if not normalized_user or not isinstance(scopes, dict):
        return {"recorded": 0}
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    result = pg_vocabulary.record_npc_period_activity(normalized_user, scopes)
    if int(result.get("recorded", 0) or 0) > 0:
        SERVER_DATABASE_CHANGE_GENERATIONS["period"] += 1
        server_database_bump_user_generation("period", username)
    return result


def server_database_reset_periods(scopes: list[str] | tuple[str, ...]) -> dict:
    requested = [clean(scope).lower() for scope in scopes if clean(scope).lower() in {"day", "week", "month"}]
    from FUTURE.postgres.repositories import vocabulary as pg_vocabulary
    result = pg_vocabulary.reset_periods(requested)
    SERVER_DATABASE_CHANGE_GENERATIONS["period"] += 1
    return result


def server_database_load_period_resets() -> dict:
    database_key = "postgresql:vocab_period_resets"
    if bool(SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("loaded")) and SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("database_key") == database_key:
        cached = SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("payload")
        return dict(cached) if isinstance(cached, dict) else {}
    loader = globals().get("postgres_load_database_meta_value")
    raw = loader("vocab_period_resets") if callable(loader) else ""
    try:
        payload = json.loads(raw) if raw else {}
    except Exception:
        payload = {}
    normalized = {
        scope: normalize_timestamp_text(payload.get(scope, ""))
        for scope in ("day", "week", "month")
        if clean(payload.get(scope, ""))
    }
    SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.update({"loaded": True, "database_key": database_key, "payload": normalized})
    return dict(normalized)



def server_database_store_period_resets(resets: dict | None = None) -> dict:
    source = resets if isinstance(resets, dict) else {}
    payload = {
        scope: normalize_timestamp_text(source.get(scope, ""))
        for scope in ("day", "week", "month")
        if clean(source.get(scope, ""))
    }
    database_key = "postgresql:vocab_period_resets"
    if bool(SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("loaded")) and SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("database_key") == database_key and SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.get("payload") == payload:
        return dict(payload)
    writer = globals().get("postgres_store_database_meta_value")
    if not callable(writer):
        raise RuntimeError("PostgreSQL period reset writer is unavailable.")
    writer("vocab_period_resets", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    SERVER_DATABASE_PERIOD_RESETS_RAM_CACHE.update({"loaded": True, "database_key": database_key, "payload": dict(payload)})
    SERVER_DATABASE_CHANGE_GENERATIONS["period"] += 1
    SERVER_DATABASE_CHANGE_GENERATIONS["period_resets"] += 1
    return payload



def server_database_append_event(stream: str, payload: dict) -> dict:
    result = postgres_append_event(stream, payload)
    SERVER_DATABASE_CHANGE_GENERATIONS["events"] += 1
    source = payload if isinstance(payload, dict) else {}
    username = normalize_username(source.get("user") or source.get("username") or "")
    if username:
        server_database_bump_user_generation("events", username)
        if clean(stream).lower() == "learning":
            server_database_bump_user_generation("learning_events", username)
    return result


def server_database_read_events(stream: str, limit: int = 800, keep_days: int = 0) -> list[dict]:
    return postgres_read_events(stream, limit=limit, keep_days=keep_days)


def recover_pending_learning_completion_intents() -> dict:
    return {"checked": 0, "recovered": 0, "pending": 0}


def server_database_overlay_period_state(state: dict) -> dict:
    try:
        if not callable(globals().get("postgres_list_registered_users")) or not callable(globals().get("postgres_execute")):
            return state
        now_epoch = time.time()
        buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
        resets = state.get("resets") if isinstance(state.get("resets"), dict) else {}
        users = state.setdefault("users", {})
        usernames = set(globals().get("postgres_list_registered_users")() or [])

        def _npc_users(connection):
            with connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT username FROM future_server2.npc_period_earn")
                return [clean(row[0]) for row in cursor.fetchall() if clean(row[0])]

        usernames.update(globals().get("postgres_execute")(_npc_users) or [])
        for username in usernames:
            scopes = server_database_period_scopes(username, buckets, resets)
            if any(isinstance(row.get("words"), dict) and row.get("words") for row in scopes.values()):
                users[username] = {**(users.get(username) if isinstance(users.get(username), dict) else {}), **scopes}
    except Exception:
        return state
    return state



def server_database_known_document_paths() -> list[Path]:
    paths: dict[str, Path] = {}
    for name, value in list(globals().items()):
        if not (name.endswith("_FILE") or name.endswith("_PATH")) or not isinstance(value, Path):
            continue
        if value.suffix.lower() in {".json", ".jsonl", ".txt"}:
            paths[str(value.resolve()).lower()] = value
    for root in (USER_ROOT, SERVER_DATA_ROOT):
        try:
            for path in root.glob("*.json"):
                paths[str(path.resolve()).lower()] = path
            for path in root.glob("*.txt"):
                paths[str(path.resolve()).lower()] = path
        except Exception:
            pass
    try:
        for folder in USER_ROOT.iterdir():
            if not folder.is_dir():
                continue
            for pattern in ("_future*.json", "lesson_last_file.json"):
                for path in folder.glob(pattern):
                    paths[str(path.resolve()).lower()] = path
    except Exception:
        pass
    try:
        for folder in SERVER_DATA_ROOT.iterdir():
            if not folder.is_dir() or folder.name.lower() in {"common", "sound", "image", "server_log"}:
                continue
            for path in folder.glob("_future*.json"):
                paths[str(path.resolve()).lower()] = path
    except Exception:
        pass
    return sorted(paths.values(), key=lambda path: str(path).lower())


def server_database_stable_file_bytes(path: Path) -> tuple[bytes, int] | None:
    for _attempt in range(3):
        try:
            before = path.stat()
            data = path.read_bytes()
            after = path.stat()
        except Exception:
            return None
        if int(before.st_mtime_ns) == int(after.st_mtime_ns) and int(before.st_size) == int(after.st_size) == len(data):
            return data, int(after.st_mtime_ns)
    return None


def restore_server_database_documents_to_legacy() -> dict:
    raise RuntimeError("Legacy database document restore was removed after PostgreSQL cutover.")



def audit_server_database_document_coverage() -> dict:
    raise RuntimeError("Legacy database document audit was removed after PostgreSQL cutover.")



def migrate_server_database_from_legacy() -> dict:
    raise RuntimeError("Legacy database migration was removed after PostgreSQL cutover.")
