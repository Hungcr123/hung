# Loaded by FUTURE.server_app before 06a_server_database.py.
# PostgreSQL is the sole mutable-state backend for Server 2.

POSTGRES_ADAPTER_LOCK = threading.RLock()
POSTGRES_ADAPTER_POOL: dict[str, object] = {"dsn": "", "queue": None, "size": 0, "module": None}
POSTGRES_ADAPTER_METRICS_LOCK = threading.Lock()
POSTGRES_ADAPTER_METRICS: dict[str, float] = {
    "pool_wait_count": 0,
    "pool_wait_ms_total": 0.0,
    "pool_wait_ms_max": 0.0,
    "transactions": 0,
    "commits": 0,
    "rollbacks": 0,
    "sql_execute": 0,
    "sql_executemany": 0,
    "sql_round_trips": 0,
}
POSTGRES_TRACE_LOCAL = threading.local()
POSTGRES_REQUEST_TRANSACTION_LOCAL = threading.local()
POSTGRES_WORLD_CHAT_SCHEMA_READY = False
POSTGRES_USER_PREFERENCES_TABLE = "future_server2.user_preferences"
POSTGRES_LESSON_LAST_FILE_TABLE = "future_server2.lesson_last_file"
POSTGRES_LESSON_PROGRESS_TABLE = "future_server2.lesson_progress"
POSTGRES_PDF_DRAWINGS_TABLE = "future_server2.pdf_drawings"
POSTGRES_VOCABULARY_REGISTRY_TABLE = "future_server2.vocabulary_registry"
POSTGRES_VOCABULARY_EVENTS_TABLE = "future_server2.vocabulary_events"
POSTGRES_VOCABULARY_EARN_TABLES = {
    "day": "future_server2.daily_earn",
    "week": "future_server2.weekly_earn",
    "month": "future_server2.monthly_earn",
    "npc": "future_server2.npc_period_earn",
}
POSTGRES_APPEND_EVENTS_TABLE = "future_server2.append_events"
POSTGRES_DOCUMENTS_TABLE = "future_server2.documents"
POSTGRES_USERS_TABLE = "future_server2.users"
POSTGRES_USER_AUTH_CREDENTIALS_TABLE = "future_server2.user_auth_credentials"
POSTGRES_ADMIN_USERS_TABLE = "future_server2.admin_users"
POSTGRES_PENDING_REGISTRATIONS_TABLE = "future_server2.pending_registrations"
POSTGRES_PASSWORD_RESET_REQUESTS_TABLE = "future_server2.password_reset_requests"
POSTGRES_AUTH_SESSIONS_TABLE = "future_server2.auth_sessions"
POSTGRES_CHAT_MESSAGES_TABLE = "future_server2.chat_messages"
POSTGRES_CHAT_READ_STATE_TABLE = "future_server2.chat_read_state"
POSTGRES_WORLD_CHAT_MESSAGES_TABLE = "future_server2.world_chat_messages"
POSTGRES_LESSON_TASK_STATE_TABLE = "future_server2.lesson_task_state"
POSTGRES_LESSON_TIME_TABLE = "future_server2.lesson_time"
POSTGRES_LESSON_TIME_CREDIT_STATE_TABLE = "future_server2.lesson_time_credit_state"
POSTGRES_INVENTORY_ITEMS_TABLE = "future_server2.inventory_items"
POSTGRES_INVENTORY_EVENTS_TABLE = "future_server2.inventory_events"
POSTGRES_VOCAB_IMAGE_CACHE_TABLE = "future_server2.vocab_image_cache"
POSTGRES_VOCAB_IMAGE_SELECTION_TABLE = "future_server2.vocab_image_selection"
POSTGRES_LESSON_FILES_TABLE = "future_server2.lesson_files"
POSTGRES_LESSON_FILE_REPLICAS_TABLE = "future_server2.lesson_file_replicas"
POSTGRES_LESSON_FILE_ALIASES_TABLE = "future_server2.lesson_file_aliases"
POSTGRES_VAULT_FOLDERS_TABLE = "future_server2.vault_folders"
POSTGRES_VAULT_ENTRIES_TABLE = "future_server2.vault_entries"
POSTGRES_VAULT_REVISIONS_TABLE = "future_server2.vault_revisions"
POSTGRES_LESSON_FOLDER_LINKS_TABLE = "future_server2.lesson_folder_links"
POSTGRES_LESSON_PROGRESS_ORPHANS_TABLE = "future_server2.lesson_progress_orphans"
POSTGRES_DATABASE_META_TABLE = "future_server2.database_meta"
POSTGRES_SPACE_PDF_DOCUMENTS_TABLE = "future_server2.space_pdf_documents"
POSTGRES_SPACE_PDF_LESSON_META_TABLE = "future_server2.space_pdf_lesson_meta"
POSTGRES_SPACE_PDF_PACKAGE_REPLICAS_TABLE = "future_server2.space_pdf_package_replicas"
POSTGRES_CANONICAL_MIGRATION_ARCHIVE_TABLE = "future_server2.canonical_migration_archive"
POSTGRES_ANNOUNCEMENTS_TABLE = "future_server2.announcements"
POSTGRES_LESSON_TASK_NOTICES_TABLE = "future_server2.lesson_task_notices"
POSTGRES_LESSON_TASK_NOTICE_STATE_TABLE = "future_server2.lesson_task_notice_state"
POSTGRES_SPACE_W_SPEAK_SKIP_REQUESTS_TABLE = "future_server2.space_w_speak_skip_requests"
POSTGRES_TTS_JOBS_TABLE = "future_server2.tts_jobs"
POSTGRES_GLOBAL_BACKEND_FLAGS = ("FUTURE_DB_BACKEND", "FUTURE_POSTGRES_BACKEND")
POSTGRES_ONLY_REQUIRED_DOMAINS = (
    "APPEND_EVENTS", "AUTH", "INVENTORY", "LEADERBOARD_DOCUMENTS",
    "LEARNING_SUMMARY_DOCUMENTS", "LESSON_PROGRESS", "LESSON_TASK", "LESSON_TIME",
    "QM_CITY_DOCUMENTS", "QMDICT_DOCUMENTS", "USER_AUTH_DOCS", "USER_PREFERENCES", "VOCABULARY",
)


def postgres_backend_mode(domain: str = "") -> str:
    return "postgres"


def postgres_backend_enabled(domain: str = "") -> bool:
    return True


def postgres_configured_backend_flags() -> dict[str, str]:
    flags = {}
    for name, value in os.environ.items():
        key = clean(name).upper()
        if key in POSTGRES_GLOBAL_BACKEND_FLAGS or (key.startswith("FUTURE_DB_") and key.endswith("_BACKEND")):
            cleaned = clean(value).lower()
            if cleaned:
                flags[key] = cleaned
    return dict(sorted(flags.items()))

def validate_postgres_backend_configuration() -> dict[str, object]:
    flags = postgres_configured_backend_flags()
    non_postgres = {name: value for name, value in flags.items() if value != "postgres"}
    if non_postgres:
        raise RuntimeError(f"Server 2 accepts PostgreSQL backend flags only: {non_postgres}")
    return {"ok": True, "errors": [], "warnings": [], "flags": flags, "backend": "postgresql"}

def postgres_runtime_probe_snapshot() -> dict:
    config = validate_postgres_backend_configuration()
    result = {
        "dsn_set": bool(postgres_dsn()),
        "configuration": config,
        "database": "",
        "user": "",
        "ok": False,
    }
    if not postgres_dsn():
        return result

    def _probe(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            row = cursor.fetchone()
        return {"database": clean(row[0]), "user": clean(row[1])}

    values = postgres_execute(_probe)
    result.update(values)
    result["ok"] = bool(values.get("database") and values.get("user"))
    return result

def postgres_dsn() -> str:
    return clean(os.environ.get("FUTURE_PG_DSN", ""))


def postgres_import_driver():
    try:
        return importlib.import_module("psycopg")
    except Exception as exc:
        raise RuntimeError("PostgreSQL driver missing. Install psycopg and set FUTURE_PG_DSN.") from exc


def postgres_pool_size() -> int:
    try:
        value = int(os.environ.get("FUTURE_PG_POOL_SIZE", "16") or 16)
    except Exception:
        value = 16
    return max(1, min(64, value))


def postgres_get_connection():
    dsn = postgres_dsn()
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is not set.")
    with POSTGRES_ADAPTER_LOCK:
        pool = POSTGRES_ADAPTER_POOL.get("queue")
        if POSTGRES_ADAPTER_POOL.get("dsn") != dsn or pool is None:
            driver = postgres_import_driver()
            size = postgres_pool_size()
            pool = queue.Queue(maxsize=size)
            for _index in range(size):
                connection = driver.connect(dsn, autocommit=False)
                pool.put(connection)
            POSTGRES_ADAPTER_POOL.update({"dsn": dsn, "queue": pool, "size": size, "module": driver})
    wait_started = time.perf_counter()
    try:
        connection = pool.get(timeout=10)
        wait_ms = (time.perf_counter() - wait_started) * 1000
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["pool_wait_count"] += 1
            POSTGRES_ADAPTER_METRICS["pool_wait_ms_total"] += wait_ms
            POSTGRES_ADAPTER_METRICS["pool_wait_ms_max"] = max(POSTGRES_ADAPTER_METRICS["pool_wait_ms_max"], wait_ms)
        return connection
    except Exception as exc:
        raise RuntimeError("PostgreSQL pool exhausted.") from exc

def postgres_trace_begin(trace_id: str = "") -> dict:
    """Added 2026-07-29: isolate completion SQL evidence from unrelated server traffic."""
    safe_trace_id = clean(trace_id)[:160]
    current = getattr(POSTGRES_TRACE_LOCAL, "state", None)
    if isinstance(current, dict) and current.get("trace_id") == safe_trace_id:
        return current
    state = {
        "trace_id": safe_trace_id,
        "stage": "authentication_user_loading",
        "events": [],
        "transactions": 0,
        "commits": 0,
        "rollbacks": 0,
        "sql_round_trips": 0,
        "current_transaction_id": "",
        "current_connection_id": "",
        "current_repository": "",
        "runtime_stage_totals": {},
        "stage_started_wall_ns": time.perf_counter_ns(),
        "stage_started_thread_cpu_ns": time.thread_time_ns(),
        "stage_started_process_cpu_ns": time.process_time_ns(),
    }
    POSTGRES_TRACE_LOCAL.state = state
    return state


def postgres_trace_set_stage(stage: str = "") -> None:
    """Added 2026-07-29: label SQL with the active lesson-completion stage."""
    state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
    if isinstance(state, dict):
        now_wall = time.perf_counter_ns()
        now_thread = time.thread_time_ns()
        now_process = time.process_time_ns()
        previous = clean(state.get("stage")) or "unclassified"
        started_wall = int(state.get("stage_started_wall_ns", now_wall) or now_wall)
        started_thread = int(state.get("stage_started_thread_cpu_ns", now_thread) or now_thread)
        started_process = int(state.get("stage_started_process_cpu_ns", now_process) or now_process)
        runtime = state.setdefault("runtime_stage_totals", {})
        row = runtime.setdefault(previous, {"wall_ms": 0.0, "thread_cpu_ms": 0.0, "process_cpu_ms": 0.0})
        row["wall_ms"] += max(0.0, (now_wall - started_wall) / 1e6)
        row["thread_cpu_ms"] += max(0.0, (now_thread - started_thread) / 1e6)
        row["process_cpu_ms"] += max(0.0, (now_process - started_process) / 1e6)
        state["stage"] = clean(stage)[:120] or "unclassified"
        state["stage_started_wall_ns"] = now_wall
        state["stage_started_thread_cpu_ns"] = now_thread
        state["stage_started_process_cpu_ns"] = now_process


def postgres_trace_sql_identity(statement) -> tuple[str, str, str]:
    """Added 2026-07-29: fingerprint SQL without logging parameter values."""
    normalized = re.sub(r"\s+", " ", str(statement or "")).strip()
    operation = (normalized.split(" ", 1)[0] if normalized else "SQL").upper()[:24]
    fingerprint = hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:20]
    label = normalized[:180]
    return operation, fingerprint, label


def postgres_trace_record_event(event: dict) -> dict | None:
    state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
    if not isinstance(state, dict) or not state.get("trace_id"):
        return None
    row = {
        "trace_id": state.get("trace_id", ""),
        "stage": state.get("stage", "unclassified"),
        "repository": state.get("current_repository", ""),
        "transaction_id": state.get("current_transaction_id", ""),
        "connection_id": state.get("current_connection_id", ""),
        **event,
    }
    state.setdefault("events", []).append(row)
    logger = globals().get("stt_debug_log")
    # Updated 2026-07-29: response-local trace evidence must not synchronously
    # open and write the debug file for every SQL in a load test.
    disk_log = clean(os.environ.get("FUTURE_COMPLETION_TRACE_DISK_LOG", "")).lower() in {"1", "true", "yes", "on"}
    if disk_log and callable(logger):
        log_row = dict(row)
        log_row["trace_event"] = log_row.pop("event", "")
        logger("completion_trace_postgres", **log_row)
    return row


def postgres_trace_snapshot() -> dict:
    """Added 2026-07-29: return compact per-request SQL totals without clearing the trace."""
    state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
    if not isinstance(state, dict):
        return {}
    # Sample the final stage so runtime CPU covers the entire traced request.
    postgres_trace_set_stage(state.get("stage", "unclassified"))
    stage_totals: dict[str, dict[str, float]] = {}
    fingerprints: dict[str, dict[str, object]] = {}
    for event in state.get("events", []):
        stage = clean(event.get("stage")) or "unclassified"
        stage_row = stage_totals.setdefault(stage, {
            "sql_round_trips": 0, "wall_ms": 0.0, "rows_read": 0, "rows_written": 0,
            "transactions": 0, "commits": 0, "rollbacks": 0, "transaction_wall_ms": 0.0,
        })
        event_type = clean(event.get("event"))
        if event_type == "transaction_begin":
            stage_row["transactions"] += 1
            continue
        if event_type == "transaction_commit":
            stage_row["commits"] += 1
            stage_row["transaction_wall_ms"] += float(event.get("wall_ms", 0.0) or 0.0)
            continue
        if event_type == "transaction_rollback":
            stage_row["rollbacks"] += 1
            stage_row["transaction_wall_ms"] += float(event.get("wall_ms", 0.0) or 0.0)
            continue
        if event_type != "sql":
            continue
        stage_row["sql_round_trips"] += 1
        stage_row["wall_ms"] += float(event.get("wall_ms", 0.0) or 0.0)
        stage_row["rows_read"] += max(0, int(event.get("rows_read", 0) or 0))
        stage_row["rows_written"] += max(0, int(event.get("rows_written", 0) or 0))
        fingerprint = clean(event.get("sql_fingerprint"))
        fp_row = fingerprints.setdefault(fingerprint, {
            "sql_fingerprint": fingerprint,
            "sql_label": clean(event.get("sql_label")),
            "operation": clean(event.get("operation")),
            "calls": 0,
            "wall_ms": 0.0,
            "stages": set(),
        })
        fp_row["calls"] += 1
        fp_row["wall_ms"] += float(event.get("wall_ms", 0.0) or 0.0)
        fp_row["stages"].add(stage)
    top_fingerprints = []
    for row in fingerprints.values():
        top_fingerprints.append({
            **row,
            "wall_ms": round(float(row.get("wall_ms", 0.0) or 0.0), 3),
            "stages": sorted(row.pop("stages", set())),
        })
    top_fingerprints.sort(key=lambda row: (-int(row.get("calls", 0) or 0), -float(row.get("wall_ms", 0.0) or 0.0)))
    runtime_totals = state.get("runtime_stage_totals", {}) if isinstance(state.get("runtime_stage_totals"), dict) else {}
    for stage, runtime in runtime_totals.items():
        stage_totals.setdefault(stage, {
            "sql_round_trips": 0, "wall_ms": 0.0, "rows_read": 0, "rows_written": 0,
            "transactions": 0, "commits": 0, "rollbacks": 0, "transaction_wall_ms": 0.0,
        })
        stage_totals[stage].update({
            "runtime_wall_ms": round(float(runtime.get("wall_ms", 0.0) or 0.0), 3),
            "thread_cpu_ms": round(float(runtime.get("thread_cpu_ms", 0.0) or 0.0), 3),
            "process_cpu_ms": round(float(runtime.get("process_cpu_ms", 0.0) or 0.0), 3),
        })
    return {
        "trace_id": state.get("trace_id", ""),
        "transactions": int(state.get("transactions", 0) or 0),
        "commits": int(state.get("commits", 0) or 0),
        "rollbacks": int(state.get("rollbacks", 0) or 0),
        "sql_round_trips": int(state.get("sql_round_trips", 0) or 0),
        "stage_totals": {
            key: {
                "sql_round_trips": int(value["sql_round_trips"]),
                "wall_ms": round(float(value["wall_ms"]), 3),
                "rows_read": int(value.get("rows_read", 0) or 0),
                "rows_written": int(value.get("rows_written", 0) or 0),
                "transactions": int(value.get("transactions", 0) or 0),
                "commits": int(value.get("commits", 0) or 0),
                "rollbacks": int(value.get("rollbacks", 0) or 0),
                "transaction_wall_ms": round(float(value.get("transaction_wall_ms", 0.0) or 0.0), 3),
                **{name: value[name] for name in ("runtime_wall_ms", "thread_cpu_ms", "process_cpu_ms") if name in value},
            }
            for key, value in stage_totals.items()
        },
        "top_fingerprints": top_fingerprints[:30],
    }


def postgres_trace_finish() -> dict:
    """Added 2026-07-29: finalize and clear one request-local PostgreSQL trace."""
    result = postgres_trace_snapshot()
    POSTGRES_TRACE_LOCAL.state = None
    return result


class PostgresMetricsCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self._last_trace_event = None

    def execute(self, *args, **kwargs):
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["sql_execute"] += 1
            POSTGRES_ADAPTER_METRICS["sql_round_trips"] += 1
        started = time.perf_counter_ns()
        try:
            return self._cursor.execute(*args, **kwargs)
        finally:
            state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
            if isinstance(state, dict) and state.get("trace_id"):
                state["sql_round_trips"] = int(state.get("sql_round_trips", 0) or 0) + 1
                operation, fingerprint, label = postgres_trace_sql_identity(args[0] if args else "")
                trace_event = "sql"
                if operation == "SAVEPOINT":
                    trace_event = "savepoint_begin"
                elif operation == "RELEASE":
                    trace_event = "savepoint_release"
                elif operation == "ROLLBACK" and "SAVEPOINT" in label.upper():
                    trace_event = "savepoint_rollback"
                self._last_trace_event = postgres_trace_record_event({
                    "event": trace_event,
                    "operation": operation,
                    "sql_fingerprint": fingerprint,
                    "sql_label": label,
                    "round_trip_index": state["sql_round_trips"],
                    "wall_ms": round((time.perf_counter_ns() - started) / 1e6, 3),
                    "rows_read": 0,
                    "rows_written": 0 if operation == "SELECT" else max(0, int(getattr(self._cursor, "rowcount", 0) or 0)),
                })

    def executemany(self, *args, **kwargs):
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["sql_executemany"] += 1
            POSTGRES_ADAPTER_METRICS["sql_round_trips"] += 1
        started = time.perf_counter_ns()
        try:
            return self._cursor.executemany(*args, **kwargs)
        finally:
            state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
            if isinstance(state, dict) and state.get("trace_id"):
                state["sql_round_trips"] = int(state.get("sql_round_trips", 0) or 0) + 1
                operation, fingerprint, label = postgres_trace_sql_identity(args[0] if args else "")
                self._last_trace_event = postgres_trace_record_event({
                    "event": "sql",
                    "operation": f"{operation}_MANY",
                    "sql_fingerprint": fingerprint,
                    "sql_label": label,
                    "round_trip_index": state["sql_round_trips"],
                    "wall_ms": round((time.perf_counter_ns() - started) / 1e6, 3),
                    "rows_read": 0,
                    "rows_written": max(0, int(getattr(self._cursor, "rowcount", 0) or 0)),
                })

    def fetchone(self, *args, **kwargs):
        row = self._cursor.fetchone(*args, **kwargs)
        if isinstance(self._last_trace_event, dict) and self._last_trace_event.get("operation") == "SELECT":
            self._last_trace_event["rows_read"] = int(self._last_trace_event.get("rows_read", 0) or 0) + (1 if row is not None else 0)
            self._last_trace_event["rows_written"] = 0
            self._log_select_result()
        return row

    def fetchall(self, *args, **kwargs):
        rows = self._cursor.fetchall(*args, **kwargs)
        if isinstance(self._last_trace_event, dict) and self._last_trace_event.get("operation") == "SELECT":
            self._last_trace_event["rows_read"] = int(self._last_trace_event.get("rows_read", 0) or 0) + len(rows)
            self._last_trace_event["rows_written"] = 0
            self._log_select_result()
        return rows

    def _log_select_result(self) -> None:
        # Added 2026-07-29: emit fetched row counts after psycopg exposes them.
        event = self._last_trace_event
        logger = globals().get("stt_debug_log")
        if not isinstance(event, dict) or not callable(logger):
            return
        log_row = dict(event)
        log_row.pop("event", None)
        logger("completion_trace_postgres", trace_event="sql_result", **log_row)

    def __enter__(self):
        self._cursor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._cursor.__exit__(exc_type, exc, tb)

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class PostgresMetricsConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self, *args, **kwargs):
        return PostgresMetricsCursor(self._connection.cursor(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._connection, name)

def postgres_metrics_snapshot(reset: bool = False) -> dict:
    with POSTGRES_ADAPTER_LOCK:
        pool = POSTGRES_ADAPTER_POOL.get("queue")
        size = int(POSTGRES_ADAPTER_POOL.get("size", 0) or 0)
        idle = int(pool.qsize()) if pool is not None else 0
    with POSTGRES_ADAPTER_METRICS_LOCK:
        metrics = dict(POSTGRES_ADAPTER_METRICS)
        if reset:
            for key in POSTGRES_ADAPTER_METRICS:
                POSTGRES_ADAPTER_METRICS[key] = 0.0
    wait_count = int(metrics.get("pool_wait_count", 0) or 0)
    return {
        "pool_size": size,
        "pool_idle": idle,
        "pool_active": max(0, size - idle),
        "pool_wait_count": wait_count,
        "pool_wait_ms_total": round(float(metrics.get("pool_wait_ms_total", 0.0) or 0.0), 3),
        "pool_wait_ms_avg": round(float(metrics.get("pool_wait_ms_total", 0.0) or 0.0) / max(1, wait_count), 3),
        "pool_wait_ms_max": round(float(metrics.get("pool_wait_ms_max", 0.0) or 0.0), 3),
        "transactions": int(metrics.get("transactions", 0) or 0),
        "commits": int(metrics.get("commits", 0) or 0),
        "rollbacks": int(metrics.get("rollbacks", 0) or 0),
        "sql_execute": int(metrics.get("sql_execute", 0) or 0),
        "sql_executemany": int(metrics.get("sql_executemany", 0) or 0),
        "sql_round_trips": int(metrics.get("sql_round_trips", 0) or 0),
    }


def postgres_release_connection(connection, broken: bool = False) -> None:
    if connection is None:
        return
    with POSTGRES_ADAPTER_LOCK:
        pool = POSTGRES_ADAPTER_POOL.get("queue")
        dsn = POSTGRES_ADAPTER_POOL.get("dsn")
    if broken:
        try:
            connection.close()
        except Exception:
            pass
        if dsn and pool is not None:
            try:
                pool.put(postgres_import_driver().connect(dsn, autocommit=False), timeout=1)
            except Exception:
                pass
        return
    try:
        pool.put(connection, timeout=1)
    except Exception:
        try:
            connection.close()
        except Exception:
            pass


def postgres_close_pool() -> int:
    closed = 0
    with POSTGRES_ADAPTER_LOCK:
        pool = POSTGRES_ADAPTER_POOL.get("queue")
        POSTGRES_ADAPTER_POOL.update({"dsn": "", "queue": None, "size": 0, "module": None})
    if pool is None:
        return 0
    while True:
        try:
            connection = pool.get_nowait()
        except Exception:
            break
        try:
            connection.close()
            closed += 1
        except Exception:
            pass
    return closed


def postgres_execute(callback):
    request_state = getattr(POSTGRES_REQUEST_TRANSACTION_LOCAL, "state", None)
    if isinstance(request_state, dict) and request_state.get("active") and request_state.get("connection") is not None:
        trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        previous_repository = trace_state.get("current_repository", "") if isinstance(trace_state, dict) else ""
        if isinstance(trace_state, dict) and trace_state.get("trace_id"):
            trace_state["current_transaction_id"] = clean(request_state.get("transaction_id", ""))
            trace_state["current_connection_id"] = clean(request_state.get("connection_id", ""))
            trace_state["current_repository"] = clean(getattr(callback, "__qualname__", "") or getattr(callback, "__name__", ""))[:180]
        try:
            return callback(PostgresMetricsConnection(request_state["connection"]))
        except Exception:
            request_state["rollback_only"] = True
            raise
        finally:
            if isinstance(trace_state, dict):
                trace_state["current_repository"] = previous_repository

    connection = None
    broken = False
    try:
        connection = postgres_get_connection()
        state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        transaction_id = ""
        if isinstance(state, dict) and state.get("trace_id"):
            state["transactions"] = int(state.get("transactions", 0) or 0) + 1
            transaction_id = f"tx-{state['transactions']:03d}"
            state["current_transaction_id"] = transaction_id
            state["current_connection_id"] = f"pg-{id(connection):x}"
            state["current_repository"] = clean(getattr(callback, "__qualname__", "") or getattr(callback, "__name__", ""))[:180]
            postgres_trace_record_event({"event": "transaction_begin"})
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["transactions"] += 1
        result = callback(PostgresMetricsConnection(connection))
        commit_started = time.perf_counter_ns()
        connection.commit()
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["commits"] += 1
        if isinstance(state, dict) and state.get("trace_id"):
            state["commits"] = int(state.get("commits", 0) or 0) + 1
            postgres_trace_record_event({"event": "transaction_commit", "wall_ms": round((time.perf_counter_ns() - commit_started) / 1e6, 3)})
        return result
    except Exception:
        broken = True
        if connection is not None:
            try:
                rollback_started = time.perf_counter_ns()
                connection.rollback()
                with POSTGRES_ADAPTER_METRICS_LOCK:
                    POSTGRES_ADAPTER_METRICS["rollbacks"] += 1
                state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
                if isinstance(state, dict) and state.get("trace_id"):
                    state["rollbacks"] = int(state.get("rollbacks", 0) or 0) + 1
                    postgres_trace_record_event({"event": "transaction_rollback", "wall_ms": round((time.perf_counter_ns() - rollback_started) / 1e6, 3)})
            except Exception:
                pass
        raise
    finally:
        state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        if isinstance(state, dict):
            state["current_transaction_id"] = ""
            state["current_connection_id"] = ""
            state["current_repository"] = ""
        postgres_release_connection(connection, broken)


# Added 2026-07-29: mark the current completion request for one atomic core transaction.
def postgres_request_transaction_prepare() -> None:
    current = getattr(POSTGRES_REQUEST_TRANSACTION_LOCAL, "state", None)
    if isinstance(current, dict) and current.get("active"):
        return
    POSTGRES_REQUEST_TRANSACTION_LOCAL.state = {"prepared": True, "active": False}


# Added 2026-07-29: open one atomic PostgreSQL transaction for completion core writes.
def postgres_request_transaction_activate() -> bool:
    current = getattr(POSTGRES_REQUEST_TRANSACTION_LOCAL, "state", None)
    if not isinstance(current, dict) or not current.get("prepared"):
        return False
    if current.get("active"):
        return False
    connection = postgres_get_connection()
    trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
    transaction_id = ""
    connection_id = f"pg-{id(connection):x}"
    if isinstance(trace_state, dict) and trace_state.get("trace_id"):
        trace_state["transactions"] = int(trace_state.get("transactions", 0) or 0) + 1
        transaction_id = f"tx-{trace_state['transactions']:03d}"
        trace_state["current_transaction_id"] = transaction_id
        trace_state["current_connection_id"] = connection_id
        trace_state["current_repository"] = "lesson_completion_core"
        postgres_trace_record_event({"event": "transaction_begin"})
    with POSTGRES_ADAPTER_METRICS_LOCK:
        POSTGRES_ADAPTER_METRICS["transactions"] += 1
    POSTGRES_REQUEST_TRANSACTION_LOCAL.state = {
        "active": True,
        "connection": connection,
        "connection_id": connection_id,
        "transaction_id": transaction_id,
        "rollback_only": False,
    }
    return True


# Added 2026-07-29: commit and release the request-local completion transaction.
def postgres_request_transaction_commit() -> bool:
    request_state = getattr(POSTGRES_REQUEST_TRANSACTION_LOCAL, "state", None)
    if isinstance(request_state, dict) and request_state.get("prepared") and not request_state.get("active"):
        POSTGRES_REQUEST_TRANSACTION_LOCAL.state = None
        return False
    if not isinstance(request_state, dict) or not request_state.get("active"):
        return False
    connection = request_state.get("connection")
    broken = False
    try:
        if request_state.get("rollback_only"):
            raise RuntimeError("PostgreSQL completion transaction was marked for rollback.")
        started = time.perf_counter_ns()
        connection.commit()
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["commits"] += 1
        trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        if isinstance(trace_state, dict) and trace_state.get("trace_id"):
            trace_state["commits"] = int(trace_state.get("commits", 0) or 0) + 1
            trace_state["current_transaction_id"] = clean(request_state.get("transaction_id", ""))
            trace_state["current_connection_id"] = clean(request_state.get("connection_id", ""))
            trace_state["current_repository"] = "lesson_completion_core"
            postgres_trace_record_event({"event": "transaction_commit", "wall_ms": round((time.perf_counter_ns() - started) / 1e6, 3)})
        return True
    except Exception:
        broken = True
        try:
            rollback_started = time.perf_counter_ns()
            connection.rollback()
            with POSTGRES_ADAPTER_METRICS_LOCK:
                POSTGRES_ADAPTER_METRICS["rollbacks"] += 1
            trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
            if isinstance(trace_state, dict) and trace_state.get("trace_id"):
                trace_state["rollbacks"] = int(trace_state.get("rollbacks", 0) or 0) + 1
                trace_state["current_transaction_id"] = clean(request_state.get("transaction_id", ""))
                trace_state["current_connection_id"] = clean(request_state.get("connection_id", ""))
                trace_state["current_repository"] = "lesson_completion_core"
                postgres_trace_record_event({"event": "transaction_rollback", "wall_ms": round((time.perf_counter_ns() - rollback_started) / 1e6, 3)})
        except Exception:
            pass
        raise
    finally:
        POSTGRES_REQUEST_TRANSACTION_LOCAL.state = None
        postgres_release_connection(connection, broken)
        trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        if isinstance(trace_state, dict):
            trace_state["current_transaction_id"] = ""
            trace_state["current_connection_id"] = ""
            trace_state["current_repository"] = ""


# Added 2026-07-29: rollback the request-local completion transaction on failure.
def postgres_request_transaction_rollback() -> bool:
    request_state = getattr(POSTGRES_REQUEST_TRANSACTION_LOCAL, "state", None)
    if isinstance(request_state, dict) and request_state.get("prepared") and not request_state.get("active"):
        POSTGRES_REQUEST_TRANSACTION_LOCAL.state = None
        return False
    if not isinstance(request_state, dict) or not request_state.get("active"):
        return False
    connection = request_state.get("connection")
    broken = False
    try:
        started = time.perf_counter_ns()
        connection.rollback()
        with POSTGRES_ADAPTER_METRICS_LOCK:
            POSTGRES_ADAPTER_METRICS["rollbacks"] += 1
        trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        if isinstance(trace_state, dict) and trace_state.get("trace_id"):
            trace_state["rollbacks"] = int(trace_state.get("rollbacks", 0) or 0) + 1
            trace_state["current_transaction_id"] = clean(request_state.get("transaction_id", ""))
            trace_state["current_connection_id"] = clean(request_state.get("connection_id", ""))
            trace_state["current_repository"] = "lesson_completion_core"
            postgres_trace_record_event({"event": "transaction_rollback", "wall_ms": round((time.perf_counter_ns() - started) / 1e6, 3)})
        return True
    except Exception:
        broken = True
        raise
    finally:
        POSTGRES_REQUEST_TRANSACTION_LOCAL.state = None
        postgres_release_connection(connection, broken)
        trace_state = getattr(POSTGRES_TRACE_LOCAL, "state", None)
        if isinstance(trace_state, dict):
            trace_state["current_transaction_id"] = ""
            trace_state["current_connection_id"] = ""
            trace_state["current_repository"] = ""


def postgres_initialize_schema() -> dict:
    # Added 2026-07-25: first vertical-slice schema for user preferences.
    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS future_server2")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.user_preferences (
                    username TEXT PRIMARY KEY,
                    preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    server_revision BIGINT NOT NULL DEFAULT 1,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS user_preferences_updated_idx "
                "ON future_server2.user_preferences(updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_last_file (
                    username TEXT PRIMARY KEY,
                    current_lesson_id TEXT NOT NULL DEFAULT '',
                    current_path TEXT NOT NULL DEFAULT '',
                    selected_folder_path TEXT NOT NULL DEFAULT '',
                    state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_last_file_lesson_idx "
                "ON future_server2.lesson_last_file(current_lesson_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_last_file_updated_idx "
                "ON future_server2.lesson_last_file(updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.announcements (
                    announcement_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL DEFAULT 0,
                    text TEXT NOT NULL DEFAULT '',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    revision BIGINT NOT NULL DEFAULT 1,
                    created_at_utc TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS announcements_active_position_idx "
                "ON future_server2.announcements(active, position)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_task_notices (
                    username TEXT NOT NULL,
                    notice_id TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    notice_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at_utc TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, notice_id)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_task_notices_user_position_idx "
                "ON future_server2.lesson_task_notices(username, position)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_task_notices_updated_idx "
                "ON future_server2.lesson_task_notices(updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_task_notice_state (
                    username TEXT NOT NULL,
                    notice_id TEXT NOT NULL,
                    read_at_utc TEXT NOT NULL DEFAULT '',
                    seen_at_utc TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, notice_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.space_w_speak_skip_requests (
                    request_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress_key TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    identity TEXT NOT NULL DEFAULT '',
                    node_index INTEGER NOT NULL DEFAULT 0,
                    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at_utc TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    responded_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            # Added 2026-07-30: durable priority queue for interactive and builder TTS.
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.tts_jobs (
                    job_id TEXT PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    output_key TEXT NOT NULL DEFAULT '',
                    priority SMALLINT NOT NULL DEFAULT 3,
                    source TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'queued',
                    text_payload TEXT NOT NULL,
                    voice TEXT NOT NULL,
                    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    request_user TEXT NOT NULL DEFAULT '',
                    build_id TEXT NOT NULL DEFAULT '',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    leased_by TEXT NOT NULL DEFAULT '',
                    lease_token TEXT NOT NULL DEFAULT '',
                    lease_expires_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    heartbeat_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    next_retry_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    created_epoch DOUBLE PRECISION NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL,
                    started_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    completed_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    artifact_path TEXT NOT NULL DEFAULT '',
                    artifact_sha256 TEXT NOT NULL DEFAULT '',
                    artifact_size BIGINT NOT NULL DEFAULT 0,
                    result_json JSONB NOT NULL DEFAULT '{}'::jsonb
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS tts_jobs_claim_idx "
                "ON future_server2.tts_jobs(status, priority, next_retry_epoch, created_epoch)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS tts_jobs_lease_idx "
                "ON future_server2.tts_jobs(status, lease_expires_epoch)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS space_w_speak_skip_lookup_idx "
                "ON future_server2.space_w_speak_skip_requests(username, progress_key, session_id, node_index)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS space_w_speak_skip_status_updated_idx "
                "ON future_server2.space_w_speak_skip_requests(status, updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_progress_namespaces (
                    username TEXT NOT NULL,
                    space TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    PRIMARY KEY (username, space)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_progress (
                    username TEXT NOT NULL,
                    space TEXT NOT NULL,
                    progress_key TEXT NOT NULL,
                    path TEXT NOT NULL DEFAULT '',
                    identity TEXT NOT NULL DEFAULT '',
                    file_id TEXT NOT NULL,
                    node_index INTEGER NOT NULL DEFAULT 0,
                    node_count INTEGER NOT NULL DEFAULT 0,
                    learned_count INTEGER NOT NULL DEFAULT 0,
                    complete BOOLEAN NOT NULL DEFAULT FALSE,
                    server_revision BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    record_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, file_id),
                    UNIQUE (username, space, progress_key)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_progress_space_updated_idx "
                "ON future_server2.lesson_progress(username, space, updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.pdf_drawings (
                    username TEXT NOT NULL,
                    document_key TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    progress_key TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    identity TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    mode TEXT NOT NULL DEFAULT 'pdf',
                    drawing_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    content_hash TEXT NOT NULL DEFAULT '',
                    last_operation_id TEXT NOT NULL DEFAULT '',
                    server_revision BIGINT NOT NULL DEFAULT 1,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_by TEXT NOT NULL DEFAULT '',
                    deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    file_id TEXT NOT NULL DEFAULT '',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, document_key, page)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS pdf_drawings_path_idx "
                "ON future_server2.pdf_drawings(username, path, page)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS pdf_drawings_file_idx "
                "ON future_server2.pdf_drawings(username, file_id, page)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS pdf_drawings_updated_idx "
                "ON future_server2.pdf_drawings(username, updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vocabulary_registry (
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    word TEXT NOT NULL,
                    meaning TEXT NOT NULL DEFAULT '',
                    pron TEXT NOT NULL DEFAULT '',
                    word_type TEXT NOT NULL DEFAULT '',
                    learn_count INTEGER NOT NULL DEFAULT 0,
                    first_at_utc TEXT NOT NULL DEFAULT '',
                    last_at_utc TEXT NOT NULL DEFAULT '',
                    last_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    sources_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    qmdict_missing BOOLEAN NOT NULL DEFAULT FALSE,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, word_key)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS vocabulary_registry_last_idx "
                "ON future_server2.vocabulary_registry(username, last_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vocabulary_events (
                    id BIGINT PRIMARY KEY,
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    source_path TEXT NOT NULL DEFAULT '',
                    event_key TEXT NOT NULL,
                    learned_at_utc TEXT NOT NULL,
                    learned_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    local_day TEXT NOT NULL,
                    iso_week TEXT NOT NULL,
                    local_month TEXT NOT NULL,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    UNIQUE (username, word_key, event_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE SEQUENCE IF NOT EXISTS future_server2.vocabulary_events_runtime_id_seq
                    START WITH 930000000
                    MINVALUE 930000000
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS vocabulary_events_user_time_idx "
                "ON future_server2.vocabulary_events(username, learned_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.daily_earn (
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    day_key TEXT NOT NULL,
                    learned_at_utc TEXT NOT NULL,
                    learned_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    event_id BIGINT,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, word_key, day_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.weekly_earn (
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    week_key TEXT NOT NULL,
                    learned_at_utc TEXT NOT NULL,
                    learned_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    event_id BIGINT,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, word_key, week_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.monthly_earn (
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    month_key TEXT NOT NULL,
                    learned_at_utc TEXT NOT NULL,
                    learned_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    event_id BIGINT,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, word_key, month_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.npc_period_earn (
                    username TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    bucket_key TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    learned_at_utc TEXT NOT NULL,
                    learned_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (username, scope, bucket_key, word_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.append_events (
                    id BIGINT PRIMARY KEY,
                    stream TEXT NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    event_at_utc TEXT NOT NULL,
                    event_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    event_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    event_key TEXT NOT NULL DEFAULT '',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE SEQUENCE IF NOT EXISTS future_server2.append_events_runtime_id_seq
                    START WITH 940000000
                    MINVALUE 940000000
                """
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS append_events_stream_key_idx "
                "ON future_server2.append_events(stream,event_key) WHERE event_key<>''"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS append_events_stream_time_idx "
                "ON future_server2.append_events(stream,event_epoch DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS append_events_user_time_idx "
                "ON future_server2.append_events(username,event_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.documents (
                    path_key TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    content BYTEA NOT NULL,
                    encoding TEXT NOT NULL DEFAULT 'utf-8',
                    sha256 TEXT NOT NULL,
                    file_size BIGINT NOT NULL DEFAULT 0,
                    file_mtime_ns BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL DEFAULT '',
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS documents_updated_idx ON future_server2.documents(updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.users (
                    username TEXT PRIMARY KEY,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    is_test BOOLEAN NOT NULL DEFAULT FALSE,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.user_auth_credentials (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    source_path TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.admin_users (
                    username TEXT PRIMARY KEY,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.pending_registrations (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_at_utc TEXT NOT NULL DEFAULT '',
                    reviewed_at_utc TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS pending_registrations_status_idx ON future_server2.pending_registrations(status)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.password_reset_requests (
                    username TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    full_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    email_alias TEXT NOT NULL DEFAULT '',
                    client TEXT NOT NULL DEFAULT '',
                    requested_at_utc TEXT NOT NULL DEFAULT '',
                    reviewed_at_utc TEXT NOT NULL DEFAULT '',
                    expires_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    code_hash TEXT NOT NULL DEFAULT '',
                    has_code_hash BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS password_reset_requests_status_idx ON future_server2.password_reset_requests(status)"
            )
            cursor.execute(
                "ALTER TABLE future_server2.password_reset_requests ADD COLUMN IF NOT EXISTS code_hash TEXT NOT NULL DEFAULT ''"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL,
                    last_seen_epoch DOUBLE PRECISION NOT NULL,
                    last_persisted_epoch DOUBLE PRECISION NOT NULL,
                    expires_epoch DOUBLE PRECISION NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS auth_sessions_expiry_idx ON future_server2.auth_sessions(expires_epoch)")
            cursor.execute("CREATE INDEX IF NOT EXISTS auth_sessions_user_idx ON future_server2.auth_sessions(username)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS auth_sessions_username_unique_idx ON future_server2.auth_sessions(username)")
            cursor.execute("CREATE SEQUENCE IF NOT EXISTS future_server2.chat_messages_id_seq")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.chat_messages (
                    id BIGINT PRIMARY KEY DEFAULT nextval('future_server2.chat_messages_id_seq'),
                    username TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    operation_id TEXT NOT NULL DEFAULT '',
                    message_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "ALTER TABLE future_server2.chat_messages ALTER COLUMN id SET DEFAULT nextval('future_server2.chat_messages_id_seq')"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_operation_idx "
                "ON future_server2.chat_messages(username,sender,operation_id) WHERE operation_id<>''"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS chat_messages_user_id_idx ON future_server2.chat_messages(username,id)"
            )
            cursor.execute("CREATE SEQUENCE IF NOT EXISTS future_server2.world_chat_messages_id_seq")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.world_chat_messages (
                    id BIGINT PRIMARY KEY DEFAULT nextval('future_server2.world_chat_messages_id_seq'),
                    room_id TEXT NOT NULL DEFAULT 'world',
                    username TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    operation_id TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT '',
                    avatar TEXT NOT NULL DEFAULT '',
                    message_text TEXT NOT NULL DEFAULT '',
                    message_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "ALTER TABLE future_server2.world_chat_messages ALTER COLUMN id SET DEFAULT nextval('future_server2.world_chat_messages_id_seq')"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS world_chat_messages_room_id_idx ON future_server2.world_chat_messages(room_id,id DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS world_chat_messages_room_created_idx ON future_server2.world_chat_messages(room_id,created_epoch DESC)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS world_chat_messages_operation_idx "
                "ON future_server2.world_chat_messages(room_id,username,sender,operation_id) WHERE operation_id<>''"
            )
            cursor.execute(
                """
                SELECT setval(
                    'future_server2.chat_messages_id_seq',
                    GREATEST(
                        COALESCE((SELECT max(id) FROM future_server2.chat_messages), 0),
                        COALESCE((SELECT last_value FROM future_server2.chat_messages_id_seq), 1)
                    ),
                    true
                )
                """
            )
            cursor.execute(
                """
                SELECT setval(
                    'future_server2.world_chat_messages_id_seq',
                    GREATEST(
                        COALESCE((SELECT max(id) FROM future_server2.world_chat_messages), 0),
                        COALESCE((SELECT last_value FROM future_server2.world_chat_messages_id_seq), 1)
                    ),
                    true
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.chat_read_state (
                    username TEXT PRIMARY KEY,
                    admin_read BIGINT NOT NULL DEFAULT 0,
                    user_read BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_task_state (
                    username TEXT PRIMARY KEY,
                    record_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    server_revision BIGINT NOT NULL DEFAULT 1,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_task_state_updated_idx ON future_server2.lesson_task_state(updated_epoch DESC)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_time (
                    username TEXT NOT NULL,
                    lesson_key TEXT NOT NULL,
                    file_id TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    space TEXT NOT NULL DEFAULT '',
                    seconds BIGINT NOT NULL DEFAULT 0,
                    ticks BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(username, lesson_key)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_time_updated_idx ON future_server2.lesson_time(username, updated_epoch DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_time_file_idx ON future_server2.lesson_time(username, file_id) WHERE file_id<>''")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_time_credit_state (
                    username TEXT NOT NULL,
                    lesson_key TEXT NOT NULL,
                    file_id TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL,
                    last_sequence BIGINT NOT NULL DEFAULT 0,
                    last_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    boot_id TEXT NOT NULL DEFAULT '',
                    lease_issued_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    offline_credited_seconds BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(username, lesson_key)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.inventory_items (
                    username TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    use_text TEXT NOT NULL DEFAULT '',
                    quantity BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(username, item_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.inventory_events (
                    username TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    item_id TEXT NOT NULL DEFAULT '',
                    quantity BIGINT NOT NULL DEFAULT 0,
                    awarded_at_utc TEXT NOT NULL,
                    awarded_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(username, event_id)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS inventory_events_recent_idx ON future_server2.inventory_events(username, awarded_epoch DESC)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vocab_image_cache (
                    word_key TEXT PRIMARY KEY,
                    image_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    expires_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS vocab_image_cache_expiry_idx ON future_server2.vocab_image_cache(expires_epoch)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vocab_image_selection (
                    username TEXT NOT NULL,
                    word_key TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL DEFAULT '',
                    server_revision BIGINT NOT NULL DEFAULT 1,
                    selected_at_utc TEXT NOT NULL,
                    selected_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    PRIMARY KEY(username, word_key)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS vocab_image_selection_updated_idx ON future_server2.vocab_image_selection(username,selected_epoch DESC)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_files (
                    file_id TEXT PRIMARY KEY,
                    space_id TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL DEFAULT 'space',
                    canonical_fingerprint TEXT NOT NULL DEFAULT '',
                    identity_revision BIGINT NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    deleted_at_utc TEXT NOT NULL DEFAULT '',
                    deleted_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE SEQUENCE IF NOT EXISTS future_server2.lesson_file_replicas_runtime_id_seq")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_file_replicas (
                    replica_id BIGINT PRIMARY KEY DEFAULT nextval('future_server2.lesson_file_replicas_runtime_id_seq'),
                    file_id TEXT NOT NULL,
                    normalized_path TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL DEFAULT '',
                    file_mtime_ns BIGINT NOT NULL DEFAULT 0,
                    file_size BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    first_seen_at_utc TEXT NOT NULL,
                    first_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    last_seen_at_utc TEXT NOT NULL,
                    last_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "ALTER TABLE future_server2.lesson_file_replicas ALTER COLUMN replica_id SET DEFAULT nextval('future_server2.lesson_file_replicas_runtime_id_seq')"
            )
            cursor.execute(
                """
                SELECT setval(
                    'future_server2.lesson_file_replicas_runtime_id_seq',
                    GREATEST(
                        COALESCE((SELECT max(replica_id) FROM future_server2.lesson_file_replicas), 0),
                        COALESCE((SELECT last_value FROM future_server2.lesson_file_replicas_runtime_id_seq), 1)
                    ),
                    true
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_file_replicas_file_idx ON future_server2.lesson_file_replicas(file_id, status)")
            # Added 2026-07-30: watcher inactive-path updates compare normalized
            # paths case-insensitively and need indexed exact/prefix lookup.
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_file_replicas_path_lower_pattern_idx "
                "ON future_server2.lesson_file_replicas(lower(normalized_path) text_pattern_ops)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_file_aliases (
                    normalized_path TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manifest',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    first_seen_at_utc TEXT NOT NULL,
                    first_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    last_seen_at_utc TEXT NOT NULL,
                    last_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_file_aliases_file_idx ON future_server2.lesson_file_aliases(file_id, active)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS lesson_file_aliases_path_lower_pattern_idx "
                "ON future_server2.lesson_file_aliases(lower(normalized_path) text_pattern_ops)"
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vault_folders (
                    vault_folder_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    parent_folder_id TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL,
                    folder_type TEXT NOT NULL DEFAULT 'VIRTUAL',
                    source_path TEXT NOT NULL DEFAULT '',
                    sort_order BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS vault_folders_parent_idx ON future_server2.vault_folders(username,parent_folder_id,status,sort_order,display_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS vault_folders_source_idx ON future_server2.vault_folders(username,source_path,status)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vault_entries (
                    vault_entry_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    parent_folder_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL DEFAULT '',
                    entry_type TEXT NOT NULL,
                    physical_replica_id BIGINT,
                    source_entry_id TEXT,
                    source_path TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL,
                    sort_order BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS vault_entries_parent_idx ON future_server2.vault_entries(username,parent_folder_id,status,sort_order,display_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS vault_entries_lesson_idx ON future_server2.vault_entries(username,lesson_id,status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS vault_entries_replica_idx ON future_server2.vault_entries(physical_replica_id,status)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.vault_revisions (
                    username TEXT PRIMARY KEY,
                    revision BIGINT NOT NULL DEFAULT 1,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_folder_links (
                    link_path TEXT PRIMARY KEY,
                    target_path TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at_utc TEXT NOT NULL DEFAULT '',
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    revision BIGINT NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_folder_links_target_idx ON future_server2.lesson_folder_links(target_path,status)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.lesson_progress_orphans (
                    id BIGINT PRIMARY KEY,
                    username TEXT NOT NULL,
                    space TEXT NOT NULL,
                    progress_key TEXT NOT NULL,
                    path TEXT NOT NULL DEFAULT '',
                    identity TEXT NOT NULL DEFAULT '',
                    server_revision BIGINT NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    record_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    archived_at_utc TEXT NOT NULL,
                    archived_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    reason TEXT NOT NULL DEFAULT 'missing_file',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    UNIQUE(username,space,progress_key)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS lesson_progress_orphans_updated_idx ON future_server2.lesson_progress_orphans(username,space,updated_epoch DESC)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.database_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.space_pdf_documents (
                    document_id TEXT PRIMARY KEY,
                    source_sha256 TEXT NOT NULL,
                    source_bytes BIGINT NOT NULL,
                    mime_type TEXT NOT NULL DEFAULT 'application/pdf',
                    page_count BIGINT NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    asset_id TEXT NOT NULL DEFAULT '',
                    asset_locator TEXT NOT NULL DEFAULT '',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    row_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.space_pdf_lesson_meta (
                    file_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    schema_version BIGINT NOT NULL,
                    package_revision BIGINT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    owner_scope TEXT NOT NULL DEFAULT 'common',
                    source_filename TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL,
                    package_fingerprint TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    updated_at_utc TEXT NOT NULL,
                    updated_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    space_id TEXT NOT NULL DEFAULT 'Space_PDF',
                    asset_id TEXT NOT NULL DEFAULT '',
                    asset_locator TEXT NOT NULL DEFAULT '',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    row_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS space_pdf_lesson_meta_document_idx ON future_server2.space_pdf_lesson_meta(document_id,status)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.space_pdf_package_replicas (
                    normalized_path TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    package_sha256 TEXT NOT NULL,
                    semantic_fingerprint TEXT NOT NULL,
                    schema_version BIGINT NOT NULL,
                    package_revision BIGINT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    first_seen_at_utc TEXT NOT NULL,
                    first_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    last_seen_at_utc TEXT NOT NULL,
                    last_seen_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    space_id TEXT NOT NULL DEFAULT 'Space_PDF',
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    row_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS space_pdf_package_replicas_file_idx ON future_server2.space_pdf_package_replicas(file_id,status)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.canonical_migration_archive (
                    migration_batch_id TEXT NOT NULL,
                    source_primary_key TEXT NOT NULL,
                    target_primary_key TEXT NOT NULL,
                    full_original_payload JSONB NOT NULL,
                    lesson_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    all_paths JSONB NOT NULL,
                    revision BIGINT NOT NULL DEFAULT 0,
                    server_timestamp TEXT NOT NULL,
                    server_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    merge_reason TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(migration_batch_id, source_primary_key)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS canonical_migration_archive_lesson_idx ON future_server2.canonical_migration_archive(lesson_id,file_id)")
        return {"ok": True, "schema": "future_server2", "tables": ["user_preferences", "lesson_last_file", "lesson_progress", "pdf_drawings", "vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn", "append_events", "documents", "users", "auth_sessions", "chat_messages", "chat_read_state", "lesson_task_state", "lesson_time", "lesson_time_credit_state", "inventory_items", "inventory_events", "vocab_image_cache", "vocab_image_selection", "lesson_files", "lesson_file_replicas", "lesson_file_aliases", "vault_folders", "vault_entries", "vault_revisions", "lesson_folder_links", "lesson_progress_orphans", "database_meta", "space_pdf_documents", "space_pdf_lesson_meta", "space_pdf_package_replicas", "canonical_migration_archive"]}

    return postgres_execute(_run)


def postgres_load_user_preferences(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {}

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT preferences_json,server_revision,updated_at_utc,updated_epoch "
                "FROM future_server2.user_preferences WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            row = cursor.fetchone()
        if not row:
            return {}
        preferences = row[0] if isinstance(row[0], dict) else {}
        return {
            "preferences": dict(preferences),
            "server_revision": max(1, int(row[1] or 1)),
            "updated_at": clean(row[2]),
            "updated_epoch": max(0.0, float(row[3] or 0)),
        }

    return postgres_execute(_run)


def postgres_upsert_user_preferences_row(row: dict) -> dict:
    username = normalize_username(row.get("username", ""))
    if not username:
        raise RuntimeError("Missing username for PostgreSQL user_preferences upsert.")
    preferences = row.get("preferences") if isinstance(row.get("preferences"), dict) else {}
    revision = max(1, int(row.get("server_revision", 1) or 1))
    updated_at = clean(row.get("updated_at") or row.get("updated_at_utc"))
    updated_epoch = max(0.0, float(row.get("updated_epoch", 0) or 0))
    raw = json.dumps(preferences, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.user_preferences
                    (username,preferences_json,server_revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    preferences_json=excluded.preferences_json,
                    server_revision=excluded.server_revision,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (username, raw, revision, updated_at, updated_epoch, utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": username, "source_sha256": source_sha256}

    return postgres_execute(_run)


def postgres_save_user_preferences(username: str, patch: dict) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        raise RuntimeError("User khong ton tai.")
    source_patch = dict(patch) if isinstance(patch, dict) else {}
    expected_revision = None
    for key in ("_expected_server_revision", "expected_server_revision", "expectedServerRevision"):
        if key in source_patch:
            try:
                expected_revision = max(0, int(source_patch.pop(key) or 0))
            except Exception:
                expected_revision = 0
            break

    def _run(connection):
        with connection.cursor() as cursor:
            # Added 2026-07-30: serialize same-user preference patches so delayed tab responses cannot overwrite newer state.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"future-user-preferences:{normalized.lower()}",))
            cursor.execute(
                "SELECT preferences_json,server_revision,updated_at_utc,updated_epoch "
                "FROM future_server2.user_preferences WHERE lower(username)=lower(%s) FOR UPDATE",
                (normalized,),
            )
            row = cursor.fetchone()
            current = dict(row[0]) if row and isinstance(row[0], dict) else {}
            revision = max(0, int(row[1] or 0)) if row else 0
            current_updated_at = clean(row[2]) if row else ""
            current_updated_epoch = max(0.0, float(row[3] or 0)) if row else 0.0
            if expected_revision is not None and expected_revision != revision:
                incoming_vocab = source_patch.get("vocab_audio") if isinstance(source_patch.get("vocab_audio"), dict) else {}
                current_vocab = current.get("vocab_audio") if isinstance(current.get("vocab_audio"), dict) else {}
                try:
                    incoming_epoch = float(incoming_vocab.get("updated_epoch", 0) or 0)
                except Exception:
                    incoming_epoch = 0.0
                try:
                    current_vocab_epoch = float(current_vocab.get("updated_epoch", 0) or 0)
                except Exception:
                    current_vocab_epoch = 0.0
                # A newer same-device action may arrive after another tab's
                # write. Accept it only with a sane client clock; stale or
                # clock-skewed tabs keep the authoritative server revision.
                allow_newer_vocab_rebase = bool(
                    expected_revision < revision
                    and incoming_epoch > current_vocab_epoch
                    and abs(incoming_epoch - time.time()) <= 300.0
                )
                if not allow_newer_vocab_rebase:
                    current["updated_at"] = current_updated_at
                    return {
                        "preferences": current,
                        "server_revision": max(1, revision),
                        "updated_at": current_updated_at,
                        "updated_epoch": current_updated_epoch,
                        "changed": False,
                        "conflict": True,
                    }
            preferences = normalize_user_preferences(source_patch, current)
            if row and server_database_preference_identity(preferences) == server_database_preference_identity(current):
                current["updated_at"] = current_updated_at
                return {
                    "preferences": current,
                    "server_revision": max(1, revision),
                    "updated_at": current_updated_at,
                    "updated_epoch": current_updated_epoch,
                    "changed": False,
                }
            updated_at = utc_timestamp()
            updated_epoch = timestamp_to_epoch(updated_at)
            preferences["updated_at"] = updated_at
            next_revision = revision + 1 if revision else 1
            raw = json.dumps(preferences, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            source_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            cursor.execute(
                """
                INSERT INTO future_server2.user_preferences
                    (username,preferences_json,server_revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    preferences_json=excluded.preferences_json,
                    server_revision=excluded.server_revision,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (normalized, raw, next_revision, updated_at, updated_epoch, utc_timestamp(), source_sha256),
            )
            return {
                "preferences": preferences,
                "server_revision": next_revision,
                "updated_at": updated_at,
                "updated_epoch": updated_epoch,
                "changed": True,
            }

    return postgres_execute(_run)


def postgres_load_lesson_last_file(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {}

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT state_json FROM future_server2.lesson_last_file WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            row = cursor.fetchone()
        if not row:
            return {}
        return dict(row[0]) if isinstance(row[0], dict) else {}

    return postgres_execute(_run)


def postgres_upsert_lesson_last_file_row(username: str, payload: dict) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        raise RuntimeError("Missing username for PostgreSQL lesson_last_file upsert.")
    state = payload if isinstance(payload, dict) else {}
    file_row = state.get("file") if isinstance(state.get("file"), dict) else {}
    folder_row = state.get("selectedFolder") if isinstance(state.get("selectedFolder"), dict) else {}
    updated_at = clean(state.get("updated_at") or state.get("updatedAt")) or utc_timestamp()
    updated_epoch = timestamp_to_epoch(updated_at)
    current_lesson_id = clean(file_row.get("lesson_id") or file_row.get("file_id"))[:240]
    current_path = clean_path_value(file_row.get("path", ""))[:600]
    selected_folder_path = clean_path_value(folder_row.get("path", ""))[:600]
    raw = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_last_file
                    (username,current_lesson_id,current_path,selected_folder_path,state_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    current_lesson_id=excluded.current_lesson_id,
                    current_path=excluded.current_path,
                    selected_folder_path=excluded.selected_folder_path,
                    state_json=excluded.state_json,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (normalized, current_lesson_id, current_path, selected_folder_path, raw, updated_at, updated_epoch, utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": normalized, "source_sha256": source_sha256}

    return postgres_execute(_run)


def postgres_progress_row_from_record(space: str, username: str, key: str, record: dict) -> dict:
    normalized_space = normalize_space_progress_space(space)
    normalized_user = normalize_username(username)
    payload = dict(record) if isinstance(record, dict) else {}
    if normalized_space in {"Space_PDF", "Space_Picture"}:
        payload = server_database_normalize_pdf_progress_record(payload)
    payload, completion_summary = server_database_canonicalize_progress_completion(payload, normalized_space)
    payload = server_database_normalize_timestamps(payload)
    updated_at = normalize_timestamp_text(payload.get("updatedAt") or payload.get("savedAt"), fallback_now=True)
    file_id = clean(payload.get("lesson_id") or payload.get("file_id") or payload.get("identity"))[:240]
    if not file_id.lower().startswith("ftg-lesson-"):
        raise RuntimeError("PostgreSQL lesson_progress slice requires canonical ftg-lesson file_id.")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "username": normalized_user,
        "space": normalized_space,
        "progress_key": clean(key),
        "path": clean(payload.get("path", "")),
        "identity": clean(payload.get("identity", "")),
        "file_id": file_id,
        "node_index": max(0, space_w_int(payload.get("nodeIndex", 0), 0)),
        "node_count": max(0, space_w_int(payload.get("nodeCount", 0), 0)),
        "learned_count": max(0, space_w_int(completion_summary.get("learned_count", payload.get("learnedCount", 0)), 0)),
        "complete": bool(completion_summary.get("current_run_complete")),
        "server_revision": max(0, space_w_int(payload.get("_serverRevision", 0), 0)),
        "updated_at": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "record": payload,
        "record_json": raw,
        "source_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def postgres_upsert_lesson_progress_row(row: dict) -> dict:
    data = dict(row or {})
    username = normalize_username(data.get("username", ""))
    space = normalize_space_progress_space(data.get("space", ""))
    file_id = clean(data.get("file_id", ""))[:240]
    if not username or not space or not file_id.lower().startswith("ftg-lesson-"):
        raise RuntimeError("Missing canonical PostgreSQL lesson_progress identity.")
    progress_key = clean(data.get("progress_key", "")) or file_id
    updated_at = normalize_timestamp_text(data.get("updated_at") or data.get("updated_at_utc"), fallback_now=True)
    updated_epoch = timestamp_to_epoch(updated_at)
    record = data.get("record") if isinstance(data.get("record"), dict) else {}
    raw = data.get("record_json") if isinstance(data.get("record_json"), str) and data.get("record_json") else json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = data.get("source_sha256") or hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (username,space) DO UPDATE SET
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch
                """,
                (username, space, updated_at, updated_epoch),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress
                    (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                ON CONFLICT (username,file_id) DO UPDATE SET
                    space=excluded.space,
                    progress_key=excluded.progress_key,
                    path=excluded.path,
                    identity=excluded.identity,
                    node_index=excluded.node_index,
                    node_count=excluded.node_count,
                    learned_count=excluded.learned_count,
                    complete=excluded.complete,
                    server_revision=excluded.server_revision,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    record_json=excluded.record_json,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                WHERE excluded.server_revision>=future_server2.lesson_progress.server_revision
                """,
                (
                    username, space, progress_key, clean(data.get("path", "")), clean(data.get("identity", "")),
                    file_id, max(0, space_w_int(data.get("node_index", 0), 0)), max(0, space_w_int(data.get("node_count", 0), 0)),
                    max(0, space_w_int(data.get("learned_count", 0), 0)), bool(data.get("complete")),
                    max(0, space_w_int(data.get("server_revision", 0), 0)), updated_at, updated_epoch, raw, utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": username, "space": space, "file_id": file_id, "source_sha256": source_sha256}

    return postgres_execute(_run)


def postgres_apply_lesson_progress_entry(space: str, username: str, entry: dict) -> dict:
    normalized_user = normalize_username(username)
    normalized_space = normalize_space_progress_space(space)
    op = clean(entry.get("op", "upsert")).lower() if isinstance(entry, dict) else "upsert"
    key = clean(entry.get("key", "")) if isinstance(entry, dict) else ""
    file_id = clean(entry.get("file_id") or entry.get("lesson_id") or entry.get("identity"))[:240] if isinstance(entry, dict) else ""
    if op == "remove" and file_id.lower().startswith("ftg-lesson-"):
        def _remove(connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM future_server2.lesson_progress WHERE username=%s AND file_id=%s",
                    (normalized_user, file_id),
                )
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (username,space) DO UPDATE SET updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                    """,
                    (normalized_user, normalized_space, utc_timestamp(), time.time()),
                )
            return {"ok": True, "op": op, "key": key, "file_id": file_id}
        return postgres_execute(_remove)
    record = entry.get("record") if isinstance(entry, dict) and isinstance(entry.get("record"), dict) else None
    if key and record:
        row = postgres_progress_row_from_record(normalized_space, normalized_user, key, record)
        postgres_upsert_lesson_progress_row(row)
        return {"ok": True, "op": op, "key": key, "file_id": row["file_id"]}
    raise RuntimeError("PostgreSQL lesson_progress slice only supports canonical upsert/remove entries.")


def postgres_replace_lesson_progress_payload(space: str, username: str, payload: dict) -> dict:
    normalized_space = normalize_space_progress_space(space)
    normalized_user = normalize_username(username)
    source = normalize_space_progress_payload(payload)
    rows = []
    for key, record in source.get("states", {}).items():
        if clean(key) and isinstance(record, dict):
            rows.append(postgres_progress_row_from_record(normalized_space, normalized_user, clean(key), record))
    if any(not row["file_id"].lower().startswith("ftg-lesson-") for row in rows):
        raise RuntimeError("PostgreSQL lesson_progress replace supports canonical rows only.")

    def _replace(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM future_server2.lesson_progress WHERE username=%s AND space=%s",
                (normalized_user, normalized_space),
            )
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_progress
                        (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    """,
                    (
                        row["username"], row["space"], row["progress_key"], row["path"], row["identity"],
                        row["file_id"], row["node_index"], row["node_count"], row["learned_count"], row["complete"],
                        row["server_revision"], row["updated_at"], row["updated_epoch"], row["record_json"],
                        utc_timestamp(), row["source_sha256"],
                    ),
                )
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (username,space) DO UPDATE SET updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                """,
                (normalized_user, normalized_space, normalize_timestamp_text(source.get("updated_at"), fallback_now=True), timestamp_to_epoch(source.get("updated_at"))),
            )
        return True
    postgres_execute(_replace)
    return source


def postgres_load_lesson_progress_payload(space: str, username: str) -> dict | None:
    normalized_user = normalize_username(username)
    normalized_space = normalize_space_progress_space(space)

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_at_utc FROM future_server2.lesson_progress_namespaces WHERE username=%s AND space=%s",
                (normalized_user, normalized_space),
            )
            namespace = cursor.fetchone()
            cursor.execute(
                """
                SELECT progress_key,record_json,complete,node_index,node_count,learned_count,server_revision,file_id,identity,path
                FROM future_server2.lesson_progress WHERE username=%s AND space=%s
                """,
                (normalized_user, normalized_space),
            )
            states = {}
            for row in cursor.fetchall():
                record = dict(row[1]) if isinstance(row[1], dict) else {}
                record, _completion_summary = server_database_canonicalize_progress_completion(record, normalized_space)
                record["complete"] = bool(row[2])
                if "nodeIndex" not in record:
                    record["nodeIndex"] = max(0, space_w_int(row[3], 0))
                if "nodeCount" not in record:
                    record["nodeCount"] = max(0, space_w_int(row[4], 0))
                if "learnedCount" not in record:
                    record["learnedCount"] = max(0, space_w_int(row[5], 0))
                record["_serverRevision"] = max(
                    max(0, space_w_int(record.get("_serverRevision", record.get("serverRevision", 0)), 0)),
                    max(0, space_w_int(row[6], 0)),
                )
                if clean(row[7]) and not clean(record.get("file_id") or record.get("lesson_id")):
                    record["file_id"] = clean(row[7])
                    record["lesson_id"] = clean(row[7])
                if clean(row[8]) and not clean(record.get("identity")):
                    record["identity"] = clean(row[8])
                if clean(row[9]) and not clean(record.get("path")):
                    record["path"] = clean(row[9])
                states[clean(row[0])] = record
            # Added 2026-07-26: keep legacy path-only progress visible while
            # PostgreSQL canonical identity rollout finishes reattaching rows.
            cursor.execute(
                """
                SELECT progress_key,record_json,server_revision,updated_at_utc,identity,path
                FROM future_server2.lesson_progress_orphans
                WHERE username=%s AND space=%s
                ORDER BY updated_epoch ASC
                """,
                (normalized_user, normalized_space),
            )
            orphan_updated_at = ""
            for row in cursor.fetchall():
                key = clean(row[0])
                if not key or key in states:
                    continue
                record = dict(row[1]) if isinstance(row[1], dict) else {}
                record, _completion_summary = server_database_canonicalize_progress_completion(record, normalized_space)
                if clean(row[4]) and not clean(record.get("identity")):
                    record["identity"] = clean(row[4])
                if clean(row[5]) and not clean(record.get("path")):
                    record["path"] = clean(row[5])
                if "updatedAt" not in record:
                    record["updatedAt"] = clean(row[3])
                record["_serverRevision"] = max(
                    max(0, space_w_int(record.get("_serverRevision", record.get("serverRevision", 0)), 0)),
                    max(0, space_w_int(row[2], 0)),
                )
                states[key] = record
                orphan_updated_at = clean(row[3]) or orphan_updated_at
            if namespace is None and not states:
                return None
            updated_at = clean(namespace[0]) if namespace is not None else orphan_updated_at or utc_timestamp()
            return {"version": 1, "updated_at": updated_at, "states": states}

    return postgres_execute(_read)


def postgres_load_lesson_progress_payloads(username: str, spaces: object = None) -> dict[str, dict]:
    """Added 2026-07-28: batch login snapshot progress reads into one PG round-trip."""
    normalized_user = normalize_username(username)
    normalized_spaces = sorted({
        normalize_space_progress_space(space)
        for space in (spaces or [])
        if normalize_space_progress_space(space)
    })
    if not normalized_user or not normalized_spaces:
        return {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT space, updated_at_utc
                FROM future_server2.lesson_progress_namespaces
                WHERE username=%s AND space = ANY(%s)
                """,
                (normalized_user, normalized_spaces),
            )
            namespaces = {clean(row[0]): clean(row[1]) for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT space, progress_key, record_json, complete, node_index, node_count,
                       learned_count, server_revision, file_id, identity, path
                FROM future_server2.lesson_progress
                WHERE username=%s AND space = ANY(%s)
                """,
                (normalized_user, normalized_spaces),
            )
            states_by_space: dict[str, dict] = {space: {} for space in normalized_spaces}
            for row in cursor.fetchall():
                normalized_space = clean(row[0])
                states = states_by_space.setdefault(normalized_space, {})
                record = dict(row[2]) if isinstance(row[2], dict) else {}
                record, _completion_summary = server_database_canonicalize_progress_completion(record, normalized_space)
                record["complete"] = bool(row[3])
                if "nodeIndex" not in record:
                    record["nodeIndex"] = max(0, space_w_int(row[4], 0))
                if "nodeCount" not in record:
                    record["nodeCount"] = max(0, space_w_int(row[5], 0))
                if "learnedCount" not in record:
                    record["learnedCount"] = max(0, space_w_int(row[6], 0))
                record["_serverRevision"] = max(
                    max(0, space_w_int(record.get("_serverRevision", record.get("serverRevision", 0)), 0)),
                    max(0, space_w_int(row[7], 0)),
                )
                if clean(row[8]) and not clean(record.get("file_id") or record.get("lesson_id")):
                    record["file_id"] = clean(row[8])
                    record["lesson_id"] = clean(row[8])
                if clean(row[9]) and not clean(record.get("identity")):
                    record["identity"] = clean(row[9])
                if clean(row[10]) and not clean(record.get("path")):
                    record["path"] = clean(row[10])
                states[clean(row[1])] = record
            cursor.execute(
                """
                SELECT space, progress_key, record_json, server_revision, updated_at_utc, identity, path
                FROM future_server2.lesson_progress_orphans
                WHERE username=%s AND space = ANY(%s)
                ORDER BY space ASC, updated_epoch ASC
                """,
                (normalized_user, normalized_spaces),
            )
            orphan_updated_by_space: dict[str, str] = {}
            for row in cursor.fetchall():
                normalized_space = clean(row[0])
                key = clean(row[1])
                states = states_by_space.setdefault(normalized_space, {})
                if not key or key in states:
                    continue
                record = dict(row[2]) if isinstance(row[2], dict) else {}
                record, _completion_summary = server_database_canonicalize_progress_completion(record, normalized_space)
                if clean(row[5]) and not clean(record.get("identity")):
                    record["identity"] = clean(row[5])
                if clean(row[6]) and not clean(record.get("path")):
                    record["path"] = clean(row[6])
                if "updatedAt" not in record:
                    record["updatedAt"] = clean(row[4])
                record["_serverRevision"] = max(
                    max(0, space_w_int(record.get("_serverRevision", record.get("serverRevision", 0)), 0)),
                    max(0, space_w_int(row[3], 0)),
                )
                states[key] = record
                orphan_updated_by_space[normalized_space] = clean(row[4]) or orphan_updated_by_space.get(normalized_space, "")
            payloads: dict[str, dict] = {}
            for normalized_space in normalized_spaces:
                states = states_by_space.get(normalized_space, {})
                namespace = namespaces.get(normalized_space, "")
                if not namespace and not states:
                    continue
                payloads[normalized_space] = {
                    "version": 1,
                    "updated_at": namespace or orphan_updated_by_space.get(normalized_space, "") or utc_timestamp(),
                    "states": states,
                }
            return payloads
    return postgres_execute(_read)


def postgres_pdf_drawing_payload_from_row(row: object) -> dict:
    if not row:
        return {}
    drawing = row[7] if isinstance(row[7], dict) else {}
    return {
        "progress_key": clean(row[0]),
        "path": clean_path_value(row[1]),
        "identity": clean(row[2]),
        "title": clean(row[3]),
        "mode": clean(row[4]),
        "drawing": drawing,
        "content_hash": clean(row[5]),
        "last_operation_id": clean(row[6]),
        "deleted": bool(row[8]),
        "server_revision": max(1, space_w_int(row[9], 1)),
        "updated_at_utc": clean(row[10]),
        "updated_epoch": max(0.0, float(row[11] or 0.0)),
        "updated_by": normalize_username(row[12]),
        "file_id": clean(row[13]),
    }


def postgres_read_pdf_drawing_row(username: str, document_key: str, page: object) -> dict:
    normalized_user = normalize_username(username)
    key = clean(document_key)[:64]
    page_number = max(1, space_w_int(page, 1))
    if not normalized_user or not key:
        return {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT progress_key,path,identity,title,mode,content_hash,last_operation_id,drawing_json,
                       deleted,server_revision,updated_at_utc,updated_epoch,updated_by,file_id
                FROM future_server2.pdf_drawings WHERE username=%s AND document_key=%s AND page=%s
                """,
                (normalized_user, key, page_number),
            )
            return postgres_pdf_drawing_payload_from_row(cursor.fetchone())

    return postgres_execute(_read)


def postgres_read_pdf_drawing_row_by_path(username: str, path: str, page: object) -> dict:
    normalized_user = normalize_username(username)
    normalized_path = clean_path_value(path)
    page_number = max(1, space_w_int(page, 1))
    if not normalized_user or not normalized_path:
        return {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT document_key FROM future_server2.pdf_drawings
                WHERE username=%s AND lower(path)=lower(%s) AND page=%s
                    ORDER BY updated_epoch DESC, deleted DESC, server_revision DESC LIMIT 1
                """,
                (normalized_user, normalized_path, page_number),
            )
            row = cursor.fetchone()
            return clean(row[0]) if row else ""

    document_key = postgres_execute(_read)
    return postgres_read_pdf_drawing_row(normalized_user, document_key, page_number) if document_key else {}


def postgres_upsert_pdf_drawing_row(row: dict) -> dict:
    normalized_user = normalize_username(row.get("username", ""))
    document_key = clean(row.get("document_key", ""))[:64]
    page_number = max(1, space_w_int(row.get("page", 1), 1))
    if not normalized_user or not document_key:
        raise RuntimeError("Missing PostgreSQL pdf_drawing identity.")
    drawing = row.get("drawing") if isinstance(row.get("drawing"), dict) else {}
    raw = json.dumps(drawing, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    content_hash = clean(row.get("content_hash")) or hashlib.sha256(raw.encode("utf-8")).hexdigest()
    updated_at = normalize_timestamp_text(row.get("updated_at_utc") or row.get("updated_at"), fallback_now=True)
    updated_epoch = max(0.0, float(row.get("updated_epoch", 0.0) or timestamp_to_epoch(updated_at)))
    source_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.pdf_drawings
                    (username,document_key,page,progress_key,path,identity,title,mode,drawing_json,content_hash,last_operation_id,server_revision,updated_at_utc,updated_epoch,updated_by,deleted,file_id,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (username,document_key,page) DO UPDATE SET
                    progress_key=excluded.progress_key,
                    path=excluded.path,
                    identity=excluded.identity,
                    title=excluded.title,
                    mode=excluded.mode,
                    drawing_json=excluded.drawing_json,
                    content_hash=excluded.content_hash,
                    last_operation_id=excluded.last_operation_id,
                    deleted=excluded.deleted,
                    server_revision=GREATEST(future_server2.pdf_drawings.server_revision, excluded.server_revision),
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    updated_by=excluded.updated_by,
                    file_id=excluded.file_id,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                WHERE excluded.updated_epoch>=future_server2.pdf_drawings.updated_epoch
                """,
                (
                    normalized_user, document_key, page_number, clean(row.get("progress_key"))[:240],
                    clean_path_value(row.get("path", "")), clean(row.get("identity"))[:240], clean(row.get("title"))[:180],
                    "picture" if clean(row.get("mode")).lower() == "picture" else "pdf", raw, content_hash,
                    clean(row.get("last_operation_id"))[:160], max(1, space_w_int(row.get("server_revision", 1), 1)),
                    updated_at, updated_epoch, normalize_username(row.get("updated_by")) or normalized_user,
                    bool(row.get("deleted")), clean(row.get("file_id") or row.get("identity"))[:240],
                    utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": normalized_user, "document_key": document_key, "page": page_number, "source_sha256": source_sha256}

    return postgres_execute(_write)


def postgres_write_pdf_drawing_row(
    username: str,
    document_key: str,
    page: object,
    row: dict | None = None,
    remove: bool = False,
    clear_alias_document_keys: object = None,
    clear_path: str = "",
) -> dict:
    normalized_user = normalize_username(username)
    key = clean(document_key)[:64]
    page_number = max(1, space_w_int(page, 1))
    if not normalized_user or not key:
        raise RuntimeError("PDF drawing row identity is required.")

    def _write(connection):
        with connection.cursor() as cursor:
            if remove:
                cursor.execute(
                    "DELETE FROM future_server2.pdf_drawings WHERE username=%s AND document_key=%s AND page=%s",
                    (normalized_user, key, page_number),
                )
                return {"removed": bool(cursor.rowcount), "server_revision": 0}
            source = row if isinstance(row, dict) else {}
            drawing = source.get("drawing") if isinstance(source.get("drawing"), dict) else {}
            raw = json.dumps(drawing, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            content_hash = clean(source.get("content_hash")) or hashlib.sha256(raw.encode("utf-8")).hexdigest()
            updated_at = clean(source.get("updated_at_utc")) or utc_timestamp()
            updated_epoch = max(0.0, float(source.get("updated_epoch", 0.0) or timestamp_to_epoch(updated_at)))
            cursor.execute(
                """
                INSERT INTO future_server2.pdf_drawings
                    (username,document_key,page,progress_key,path,identity,title,mode,drawing_json,content_hash,last_operation_id,deleted,server_revision,updated_at_utc,updated_epoch,updated_by,file_id,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,1,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (username,document_key,page) DO UPDATE SET
                    progress_key=excluded.progress_key,
                    path=excluded.path,
                    identity=excluded.identity,
                    title=excluded.title,
                    mode=excluded.mode,
                    drawing_json=excluded.drawing_json,
                    content_hash=excluded.content_hash,
                    last_operation_id=excluded.last_operation_id,
                    deleted=excluded.deleted,
                    server_revision=future_server2.pdf_drawings.server_revision+1,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    updated_by=excluded.updated_by,
                    file_id=excluded.file_id,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    normalized_user, key, page_number, clean(source.get("progress_key"))[:240],
                    clean_path_value(source.get("path", "")), clean(source.get("identity"))[:240], clean(source.get("title"))[:180],
                    "picture" if clean(source.get("mode")).lower() == "picture" else "pdf", raw, content_hash,
                    clean(source.get("last_operation_id"))[:160], bool(source.get("deleted")), updated_at, updated_epoch,
                    normalize_username(source.get("updated_by")) or normalized_user, clean(source.get("file_id") or source.get("identity"))[:240],
                    utc_timestamp(), hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                ),
            )
            cursor.execute(
                "SELECT server_revision FROM future_server2.pdf_drawings WHERE username=%s AND document_key=%s AND page=%s",
                (normalized_user, key, page_number),
            )
            revision = cursor.fetchone()
            alias_keys = [clean(value)[:64] for value in (clear_alias_document_keys if isinstance(clear_alias_document_keys, (list, tuple, set)) else []) if clean(value)[:64] and clean(value)[:64] != key]
            normalized_path = clean_path_value(clear_path)
            alias_removed = 0
            if alias_keys or normalized_path:
                predicates = []
                params = [normalized_user, page_number, key]
                if alias_keys:
                    predicates.append("document_key = ANY(%s)")
                    params.append(alias_keys)
                if normalized_path:
                    predicates.append("lower(path)=lower(%s)")
                    params.append(normalized_path)
                cursor.execute(
                    "DELETE FROM future_server2.pdf_drawings WHERE username=%s AND page=%s AND document_key<>%s AND (" + " OR ".join(predicates) + ")",
                    tuple(params),
                )
                alias_removed = max(0, int(cursor.rowcount or 0))
            return {"removed": False, "server_revision": max(1, space_w_int(revision[0] if revision else 1, 1)), "alias_removed": alias_removed}

    return postgres_execute(_write)


def postgres_upsert_vocabulary_registry_row(row: dict) -> dict:
    username = normalize_username(row.get("username", ""))
    word_key = vocab_key(row.get("word_key") or row.get("word"))
    if not username or not word_key:
        raise RuntimeError("Missing PostgreSQL vocabulary registry identity.")
    sources = row.get("sources") if isinstance(row.get("sources"), list) else row.get("sources_json")
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except Exception:
            sources = []
    sources = [clean(value) for value in sources if clean(value)] if isinstance(sources, list) else []
    last_at = clean(row.get("last_at_utc") or row.get("last") or "")
    payload = {
        "username": username.lower(),
        "word_key": word_key,
        "word": clean(row.get("word")) or word_key,
        "meaning": clean(row.get("meaning")),
        "pron": clean(row.get("pron")),
        "word_type": clean(row.get("word_type") or row.get("type")),
        "learn_count": max(0, space_w_int(row.get("learn_count", row.get("count", 0)), 0)),
        "first_at_utc": clean(row.get("first_at_utc") or row.get("first")),
        "last_at_utc": last_at,
        "last_epoch": timestamp_to_epoch(last_at),
        "sources": sources,
        "qmdict_missing": bool(row.get("qmdict_missing")),
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vocabulary_registry
                    (username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,sources_json,qmdict_missing,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                ON CONFLICT (username,word_key) DO UPDATE SET
                    word=excluded.word,
                    meaning=excluded.meaning,
                    pron=excluded.pron,
                    word_type=excluded.word_type,
                    learn_count=excluded.learn_count,
                    first_at_utc=excluded.first_at_utc,
                    last_at_utc=excluded.last_at_utc,
                    last_epoch=excluded.last_epoch,
                    sources_json=excluded.sources_json,
                    qmdict_missing=excluded.qmdict_missing,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    username, word_key, payload["word"], payload["meaning"], payload["pron"],
                    payload["word_type"], payload["learn_count"], payload["first_at_utc"],
                    payload["last_at_utc"], payload["last_epoch"],
                    json.dumps(sources, ensure_ascii=False, separators=(",", ":")),
                    payload["qmdict_missing"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": username, "word_key": word_key, "source_sha256": source_sha256}

    return postgres_execute(_write)


def postgres_upsert_vocabulary_event_row(row: dict) -> dict:
    username = normalize_username(row.get("username", ""))
    word_key = vocab_key(row.get("word_key") or row.get("word"))
    event_key = clean(row.get("event_key"))[:80]
    if not username or not word_key or not event_key:
        raise RuntimeError("Missing PostgreSQL vocabulary event identity.")
    learned_at = clean(row.get("learned_at_utc")) or normalize_timestamp_text(row.get("learned_at_utc"), fallback_now=True)
    event_id = max(1, space_w_int(row.get("id", 0), 0))
    payload = {
        "id": event_id,
        "username": username.lower(),
        "word_key": word_key,
        "source_path": clean_path_value(row.get("source_path", "")),
        "event_key": event_key,
        "learned_at_utc": learned_at,
        "learned_epoch": timestamp_to_epoch(learned_at),
        "local_day": clean(row.get("local_day")),
        "iso_week": clean(row.get("iso_week")),
        "local_month": clean(row.get("local_month")),
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vocabulary_events
                    (id,username,word_key,source_path,event_key,learned_at_utc,learned_epoch,local_day,iso_week,local_month,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    username=excluded.username,
                    word_key=excluded.word_key,
                    source_path=excluded.source_path,
                    event_key=excluded.event_key,
                    learned_at_utc=excluded.learned_at_utc,
                    learned_epoch=excluded.learned_epoch,
                    local_day=excluded.local_day,
                    iso_week=excluded.iso_week,
                    local_month=excluded.local_month,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    event_id, username, word_key, payload["source_path"], event_key,
                    learned_at, payload["learned_epoch"], payload["local_day"], payload["iso_week"],
                    payload["local_month"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "id": event_id, "username": username, "word_key": word_key, "event_key": event_key, "source_sha256": source_sha256}

    return postgres_execute(_write)


def postgres_upsert_vocabulary_earn_row(scope: str, row: dict) -> dict:
    safe_scope = clean(scope).lower()
    username = normalize_username(row.get("username", ""))
    word_key = clean(row.get("word_key", ""))
    learned_at = clean(row.get("learned_at_utc")) or normalize_timestamp_text(row.get("learned_at_utc"), fallback_now=True)
    learned_epoch = timestamp_to_epoch(learned_at)
    if safe_scope in {"day", "week", "month"}:
        key_name = {"day": "day_key", "week": "week_key", "month": "month_key"}[safe_scope]
        bucket = clean(row.get(key_name, ""))
        if not username or not word_key or not bucket:
            raise RuntimeError("Missing PostgreSQL vocabulary earn identity.")
        payload = {
            "username": username.lower(),
            "word_key": word_key,
            key_name: bucket,
            "learned_at_utc": learned_at,
            "learned_epoch": learned_epoch,
            "event_id": row.get("event_id") if row.get("event_id") is not None else None,
        }
        source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
        table = POSTGRES_VOCABULARY_EARN_TABLES[safe_scope]

        def _write(connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {table}
                        (username,word_key,{key_name},learned_at_utc,learned_epoch,event_id,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (username,word_key,{key_name}) DO UPDATE SET
                        learned_at_utc=excluded.learned_at_utc,
                        learned_epoch=excluded.learned_epoch,
                        event_id=excluded.event_id,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (username, word_key, bucket, learned_at, learned_epoch, payload["event_id"], utc_timestamp(), source_sha256),
                )
            return {"ok": True, "scope": safe_scope, "username": username, "word_key": word_key, "bucket": bucket, "source_sha256": source_sha256}

        return postgres_execute(_write)
    if safe_scope == "npc":
        npc_scope = clean(row.get("scope", "")).lower()
        bucket = clean(row.get("bucket_key", ""))
        if not username or not npc_scope or not bucket or not word_key:
            raise RuntimeError("Missing PostgreSQL NPC earn identity.")
        payload = {
            "username": username.lower(),
            "scope": npc_scope,
            "bucket_key": bucket,
            "word_key": word_key,
            "learned_at_utc": learned_at,
            "learned_epoch": learned_epoch,
        }
        source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

        def _write_npc(connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO future_server2.npc_period_earn
                        (username,scope,bucket_key,word_key,learned_at_utc,learned_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (username,scope,bucket_key,word_key) DO UPDATE SET
                        learned_at_utc=excluded.learned_at_utc,
                        learned_epoch=excluded.learned_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (username, npc_scope, bucket, word_key, learned_at, learned_epoch, utc_timestamp(), source_sha256),
                )
            return {"ok": True, "scope": safe_scope, "username": username, "npc_scope": npc_scope, "bucket": bucket, "word_key": word_key, "source_sha256": source_sha256}

        return postgres_execute(_write_npc)
    raise RuntimeError("Unsupported vocabulary earn scope.")


def postgres_upsert_append_event_row(row: dict) -> dict:
    event_id = max(1, space_w_int(row.get("id", 0), 0))
    stream = clean(row.get("stream", ""))[:80]
    event_at = clean(row.get("event_at_utc")) or normalize_timestamp_text(row.get("event_at_utc"), fallback_now=True)
    event_json = row.get("event") if isinstance(row.get("event"), dict) else row.get("event_json")
    if isinstance(event_json, str):
        try:
            event_json = json.loads(event_json)
        except Exception:
            event_json = {}
    event_json = event_json if isinstance(event_json, dict) else {}
    if not event_id or not stream:
        raise RuntimeError("Missing PostgreSQL append_event identity.")
    raw = json.dumps(event_json, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    payload = {
        "id": event_id,
        "stream": stream,
        "username": normalize_username(row.get("username", "")),
        "event_at_utc": event_at,
        "event_epoch": timestamp_to_epoch(event_at),
        "event": event_json,
        "event_key": clean(row.get("event_key", ""))[:120],
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.append_events
                    (id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    stream=excluded.stream,
                    username=excluded.username,
                    event_at_utc=excluded.event_at_utc,
                    event_epoch=excluded.event_epoch,
                    event_json=excluded.event_json,
                    event_key=excluded.event_key,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (event_id, stream, payload["username"], event_at, payload["event_epoch"], raw, payload["event_key"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "id": event_id, "stream": stream, "event_key": payload["event_key"], "source_sha256": source_sha256}

    return postgres_execute(_write)


# Added 2026-07-25: runtime append-event backend for process-only PostgreSQL gates.
def postgres_append_event(stream: str, payload: dict) -> dict:
    source = server_database_normalize_timestamps(payload if isinstance(payload, dict) else {})
    event_at = normalize_timestamp_text(source.get("at"), fallback_now=True)
    username = normalize_username(source.get("user") or source.get("username") or "")
    event_key = clean(
        source.get("event_key")
        or source.get("completion_run_id")
        or source.get("completionRunId")
        or ""
    )
    if not event_key and clean(source.get("event", "")) == "lesson_complete":
        identity = "|".join([
            username.lower(),
            clean_path_value(source.get("path", "")).lower(),
            normalize_timestamp_text(source.get("client_completed_at") or source.get("at"), fallback_now=True),
        ])
        event_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    safe_stream = clean(stream)[:80]
    event_key = event_key[:160]
    encoded = json.dumps(source, ensure_ascii=False, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(
        json.dumps({
            "stream": safe_stream,
            "username": username,
            "event_key": event_key,
            "event_at_utc": event_at,
            "event": source,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            if event_key:
                cursor.execute(
                    """
                    INSERT INTO future_server2.append_events
                        (id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256)
                    VALUES (nextval('future_server2.append_events_runtime_id_seq'),%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                    ON CONFLICT (stream,event_key) WHERE event_key<>'' DO UPDATE SET
                        username=excluded.username,
                        event_at_utc=excluded.event_at_utc,
                        event_epoch=excluded.event_epoch,
                        event_json=excluded.event_json,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    RETURNING id
                    """,
                    (safe_stream, username, event_at, timestamp_to_epoch(event_at), encoded, event_key, utc_timestamp(), source_sha256),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO future_server2.append_events
                        (id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256)
                    VALUES (nextval('future_server2.append_events_runtime_id_seq'),%s,%s,%s,%s,%s::jsonb,'',%s,%s)
                    RETURNING id
                    """,
                    (safe_stream, username, event_at, timestamp_to_epoch(event_at), encoded, utc_timestamp(), source_sha256),
                )
            row = cursor.fetchone()
        return {"ok": True, "id": int(row[0] or 0), "event_key": event_key}

    return postgres_execute(_write)


def postgres_read_events(stream: str, limit: int = 800, keep_days: int = 0) -> list[dict]:
    safe_stream = clean(stream)[:80]
    safe_limit = max(1, min(50000, int(limit or 800)))

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_json FROM future_server2.append_events
                WHERE stream=%s ORDER BY id DESC LIMIT %s
                """,
                (safe_stream, safe_limit),
            )
            return [dict(row[0]) if isinstance(row[0], dict) else {} for row in cursor.fetchall()]

    rows = postgres_execute(_read)
    cutoff = time.time() - max(0, int(keep_days or 0)) * 86400 if keep_days else 0.0
    events = []
    for payload in rows:
        if not isinstance(payload, dict):
            continue
        epoch = timestamp_to_epoch(payload.get("at", "")) or 0.0
        if cutoff and epoch and epoch < cutoff:
            continue
        events.append(payload)
    events.sort(key=lambda item: timestamp_order_key(item.get("at", "")), reverse=True)
    return events[:safe_limit]


def postgres_pending_learning_completion_intents() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_key,event_json FROM future_server2.append_events
                WHERE stream='learning_intent'
                ORDER BY id
                """
            )
            return [
                {"event_key": clean(row[0]), "event_json": dict(row[1]) if isinstance(row[1], dict) else {}}
                for row in cursor.fetchall()
            ]

    return postgres_execute(_read)

def postgres_learning_completion_complete(event_key: str) -> bool:
    key = clean(event_key)[:160]
    if not key:
        return False

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT event_json FROM future_server2.append_events WHERE stream='learning' AND event_key=%s",
                (key,),
            )
            row = cursor.fetchone()
        return dict(row[0]) if row and isinstance(row[0], dict) else None

    payload = postgres_execute(_read)
    return isinstance(payload, dict) and clean(payload.get("status", "")).lower() not in {"", "core", "core_committed", "pending"}


# Added 2026-07-29: combine completion idempotency read and durable intent insert.
def postgres_begin_learning_completion(payload: dict) -> dict:
    source = server_database_normalize_timestamps(payload if isinstance(payload, dict) else {})
    event_key = clean(source.get("event_key", ""))[:160]
    if not event_key:
        raise RuntimeError("Lesson completion event key is required.")
    username = normalize_username(source.get("user") or source.get("username") or "")
    event_at = normalize_timestamp_text(source.get("at"), fallback_now=True)
    intent = {**source, "event": "lesson_complete_intent", "status": "pending", "recovery_replay_version": 1}
    encoded = json.dumps(intent, ensure_ascii=False, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(
        json.dumps({"stream": "learning_intent", "username": username, "event_key": event_key, "event": intent}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT event_json FROM future_server2.append_events WHERE stream='learning' AND event_key=%s",
                (event_key,),
            )
            completed = cursor.fetchone()
            if completed is not None:
                completed_payload = completed[0] if isinstance(completed[0], dict) else {}
                status = clean(completed_payload.get("status", "")).lower() if isinstance(completed_payload, dict) else ""
                if status not in {"", "core", "core_committed", "pending"}:
                    return {"ok": True, "complete": True, "event_key": event_key}
            cursor.execute(
                """
                INSERT INTO future_server2.append_events
                    (id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256)
                VALUES (nextval('future_server2.append_events_runtime_id_seq'),%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                ON CONFLICT (stream,event_key) WHERE event_key<>'' DO UPDATE SET
                    username=excluded.username,
                    event_at_utc=excluded.event_at_utc,
                    event_epoch=excluded.event_epoch,
                    event_json=excluded.event_json,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                RETURNING id
                """,
                ("learning_intent", username, event_at, timestamp_to_epoch(event_at), encoded, event_key, utc_timestamp(), source_sha256),
            )
            cursor.fetchone()
        return {"ok": True, "complete": False, "event_key": event_key}

    return postgres_execute(_write)


def postgres_upsert_document_row(row: dict) -> dict:
    path_key = clean(row.get("path_key", "")).lower()
    path = clean(row.get("path", ""))
    content = row.get("content", b"")
    if isinstance(content, str):
        content = content.encode(clean(row.get("encoding")) or "utf-8", errors="replace")
    content = bytes(content or b"")
    if not path_key or not path:
        raise RuntimeError("Missing PostgreSQL document identity.")
    sha256 = clean(row.get("sha256")) or hashlib.sha256(content).hexdigest()
    updated_at = clean(row.get("updated_at_utc")) or utc_timestamp()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.documents
                    (path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc,updated_epoch,migrated_at_utc)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (path_key) DO UPDATE SET
                    path=excluded.path,
                    content=excluded.content,
                    encoding=excluded.encoding,
                    sha256=excluded.sha256,
                    file_size=excluded.file_size,
                    file_mtime_ns=excluded.file_mtime_ns,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc
                """,
                (
                    path_key, path, content, clean(row.get("encoding")) or "utf-8", sha256,
                    max(0, space_w_int(row.get("file_size", len(content)), len(content))),
                    max(0, space_w_int(row.get("file_mtime_ns", 0), 0)),
                    updated_at, timestamp_to_epoch(updated_at), utc_timestamp(),
                ),
            )
        return {"ok": True, "path_key": path_key, "sha256": sha256}

    return postgres_execute(_write)

# Added 2026-07-25: copy auth users into PostgreSQL for the migration slice without changing live auth routing.
def postgres_upsert_user_row(row: dict) -> dict:
    username = normalize_username(row.get("username", ""))
    if not username:
        raise RuntimeError("Missing PostgreSQL user identity.")
    profile = row.get("profile")
    if profile is None:
        profile = row.get("profile_json")
    if isinstance(profile, str):
        try:
            profile = json.loads(profile or "{}")
        except Exception:
            profile = {}
    profile = profile if isinstance(profile, dict) else {}
    updated_at = clean(row.get("updated_at_utc")) or normalize_timestamp_text(row.get("updated_at_utc"), fallback_now=True)
    payload = {
        "username": username.lower(),
        "is_admin": bool(row.get("is_admin")),
        "profile": profile,
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "is_test": bool(row.get("is_test")),
    }
    raw_profile = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.users
                    (username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    is_admin=excluded.is_admin,
                    profile_json=excluded.profile_json,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    is_test=excluded.is_test,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (username, payload["is_admin"], raw_profile, updated_at, payload["updated_epoch"], payload["is_test"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": username, "source_sha256": source_sha256}

    return postgres_execute(_write)

# Added 2026-07-26: PostgreSQL-only startup needs user discovery without opening a legacy local database.
def postgres_list_registered_users() -> list[str]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username FROM future_server2.users WHERE COALESCE(is_test,false)=false ORDER BY lower(username)"
            )
            rows = cursor.fetchall()
        return [normalize_username(row[0]) for row in rows if normalize_username(row[0])]

    return postgres_execute(_read)


# Added 2026-07-29: account deletion must remove every PostgreSQL user-owned row, not only legacy SQLite state.
def postgres_delete_user_data(username: str, path_fragments: list[str] | tuple[str, ...] = ()) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"deleted": 0, "tables": {}}
    safe_fragments = [clean(value).lower() for value in path_fragments if clean(value)]
    driver = postgres_driver()

    def _write(connection):
        deleted_by_table: dict[str, int] = {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT columns.table_name
                FROM information_schema.columns columns
                JOIN information_schema.tables tables
                  ON tables.table_schema=columns.table_schema AND tables.table_name=columns.table_name
                WHERE columns.table_schema='future_server2'
                  AND columns.column_name='username'
                  AND tables.table_type='BASE TABLE'
                ORDER BY CASE WHEN columns.table_name='users' THEN 1 ELSE 0 END, columns.table_name
                """
            )
            table_names = [clean(row[0]) for row in cursor.fetchall() if clean(row[0])]
            for table_name in table_names:
                cursor.execute(
                    driver.sql.SQL("DELETE FROM {}.{} WHERE lower(username)=lower(%s)").format(
                        driver.sql.Identifier("future_server2"),
                        driver.sql.Identifier(table_name),
                    ),
                    (normalized,),
                )
                removed = max(0, int(cursor.rowcount or 0))
                if removed:
                    deleted_by_table[table_name] = removed
            if safe_fragments:
                cursor.execute(
                    """
                    DELETE FROM future_server2.documents document
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(%s::text[]) AS fragment(value)
                        WHERE lower(document.path_key)=fragment.value
                           OR lower(document.path_key) LIKE fragment.value || E'\\\\%%'
                           OR lower(document.path)=fragment.value
                           OR lower(document.path) LIKE fragment.value || E'\\\\%%'
                    )
                    """,
                    (safe_fragments,),
                )
                removed = max(0, int(cursor.rowcount or 0))
                if removed:
                    deleted_by_table["documents"] = deleted_by_table.get("documents", 0) + removed
        return {"deleted": sum(deleted_by_table.values()), "tables": deleted_by_table}

    return postgres_execute(_write)

# Added 2026-07-28: startup warmup selection needs account metadata so
# production can skip benchmark/test users without deleting them.
def postgres_list_user_warmup_records() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, COALESCE(is_test,false) AS is_test, COALESCE(is_admin,false) AS is_admin "
                "FROM future_server2.users ORDER BY lower(username)"
            )
            rows = cursor.fetchall()
        result = []
        for row in rows:
            username = normalize_username(row[0])
            if username:
                result.append({"username": username, "is_test": bool(row[1]), "is_admin": bool(row[2])})
        return result

    return postgres_execute(_read)

def postgres_user_exists(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM future_server2.users WHERE lower(username)=lower(%s) LIMIT 1",
                (normalized,),
            )
            return cursor.fetchone() is not None

    return bool(postgres_execute(_read))

# Added 2026-07-25: scoped auth/admin/pending/reset helpers keep legacy user docs out of generic PostgreSQL documents.
def postgres_load_user_auth_credential(username: str) -> str:
    normalized = normalize_username(username)
    if not normalized:
        return ""

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM future_server2.user_auth_credentials WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            row = cursor.fetchone()
        return clean(row[0]) if row else ""

    return postgres_execute(_read)

def postgres_load_user_profile(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT profile_json FROM future_server2.users WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            row = cursor.fetchone()
        return dict(row[0]) if row and isinstance(row[0], dict) else {}

    return postgres_execute(_read)

def postgres_upsert_user_auth_credential(username: str, password_hash_value: str, source_path: str = "") -> dict:
    normalized = normalize_username(username)
    password_hash_value = clean(password_hash_value)
    if not normalized or not password_hash_value:
        raise RuntimeError("Missing PostgreSQL user auth credential.")
    updated_at = utc_timestamp()
    payload = {
        "username": normalized,
        "password_hash": password_hash_value,
        "source_path": clean(source_path),
        "updated_at_utc": updated_at,
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.user_auth_credentials
                    (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    source_path=excluded.source_path,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (normalized, password_hash_value, clean(source_path), updated_at, timestamp_to_epoch(updated_at), utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": normalized, "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_admin_users() -> set[str]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT username FROM future_server2.admin_users WHERE enabled=true")
            return {normalize_username(row[0]) for row in cursor.fetchall() if normalize_username(row[0])}

    return postgres_execute(_read)

def postgres_replace_admin_users(admins: set[str]) -> dict:
    rows = sorted({normalize_username(item) for item in admins if normalize_username(item)}, key=str.lower)
    updated_at = utc_timestamp()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.admin_users")
            deleted = int(cursor.rowcount or 0)
            for username in rows:
                source_sha256 = hashlib.sha256(f"{username}|{updated_at}".encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.admin_users
                        (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,true,%s,%s,%s,%s)
                    """,
                    (username, updated_at, timestamp_to_epoch(updated_at), utc_timestamp(), source_sha256),
                )
        return {"ok": True, "deleted": deleted, "rows": len(rows)}

    return postgres_execute(_write)

def postgres_load_pending_registrations() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,password_hash,profile_json,status,requested_at_utc,reviewed_at_utc "
                "FROM future_server2.pending_registrations"
            )
            rows = cursor.fetchall()
        payload = {}
        for row in rows:
            username = normalize_username(row[0])
            if not username:
                continue
            payload[username] = {
                "username": username,
                "password_hash": clean(row[1]),
                "profile": dict(row[2]) if isinstance(row[2], dict) else {},
                "status": clean(row[3]) or "pending",
                "requested_at": clean(row[4]),
                "reviewed_at": clean(row[5]),
            }
        return payload

    return postgres_execute(_read)

def postgres_replace_pending_registrations(payload: dict) -> dict:
    source = payload if isinstance(payload, dict) else {}
    rows = []
    for key, item in sorted(source.items(), key=lambda pair: normalize_username(pair[0])):
        if not isinstance(item, dict):
            continue
        username = normalize_username(item.get("username", key))
        if not username:
            continue
        profile = item.get("profile") if isinstance(item.get("profile"), dict) else {}
        updated_at = clean(item.get("reviewed_at") or item.get("requested_at")) or utc_timestamp()
        rows.append((username, clean(item.get("password_hash", "")), profile, clean(item.get("status", "pending")) or "pending", clean(item.get("requested_at", "")), clean(item.get("reviewed_at", "")), updated_at))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.pending_registrations")
            deleted = int(cursor.rowcount or 0)
            for username, password_hash_value, profile, status, requested_at, reviewed_at, updated_at in rows:
                source_sha256 = hashlib.sha256(json.dumps({"username": username, "profile": profile, "status": status, "requested_at": requested_at, "reviewed_at": reviewed_at}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.pending_registrations
                        (username,password_hash,profile_json,status,requested_at_utc,reviewed_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (username, password_hash_value, json.dumps(profile, ensure_ascii=False, separators=(",", ":")), status, requested_at, reviewed_at, updated_at, timestamp_to_epoch(updated_at), utc_timestamp(), source_sha256),
                )
        return {"ok": True, "deleted": deleted, "rows": len(rows)}

    return postgres_execute(_write)

def postgres_load_password_reset_requests() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,status,full_name,email,email_alias,client,requested_at_utc,reviewed_at_utc,expires_epoch,attempts,has_code_hash,code_hash "
                "FROM future_server2.password_reset_requests"
            )
            rows = cursor.fetchall()
        payload = {}
        for row in rows:
            username = normalize_username(row[0])
            if not username:
                continue
            payload[username] = {
                "username": username,
                "status": clean(row[1]) or "pending",
                "full_name": clean(row[2]),
                "email": clean(row[3]),
                "email_alias": clean(row[4]),
                "client": clean(row[5]),
                "requested_at": clean(row[6]),
                "reviewed_at": clean(row[7]),
                "expires_at": float(row[8] or 0),
                "attempts": int(row[9] or 0),
                **({"code_hash": clean(row[11])} if bool(row[10]) and clean(row[11]) else {}),
            }
        return payload

    return postgres_execute(_read)

def postgres_replace_password_reset_requests(payload: dict) -> dict:
    source = payload if isinstance(payload, dict) else {}
    rows = []
    for key, item in sorted(source.items(), key=lambda pair: normalize_username(pair[0])):
        if not isinstance(item, dict):
            continue
        username = normalize_username(item.get("username", key))
        if not username:
            continue
        updated_at = clean(item.get("reviewed_at") or item.get("requested_at")) or utc_timestamp()
        code_hash = clean(item.get("code_hash", ""))
        rows.append((username, clean(item.get("status", "pending")) or "pending", clean(item.get("full_name", "")), clean(item.get("email", "")), clean(item.get("email_alias", "")), clean(item.get("client", "")), clean(item.get("requested_at", "")), clean(item.get("reviewed_at", "")), float(item.get("expires_at", 0) or 0), int(item.get("attempts", 0) or 0), code_hash, bool(code_hash), updated_at))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.password_reset_requests")
            deleted = int(cursor.rowcount or 0)
            for username, status, full_name, email, email_alias, client, requested_at, reviewed_at, expires_epoch, attempts, code_hash, has_code_hash, updated_at in rows:
                source_sha256 = hashlib.sha256(json.dumps({"username": username, "status": status, "requested_at": requested_at, "reviewed_at": reviewed_at, "has_code_hash": has_code_hash}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.password_reset_requests
                        (username,status,full_name,email,email_alias,client,requested_at_utc,reviewed_at_utc,expires_epoch,attempts,code_hash,has_code_hash,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (username, status, full_name, email, email_alias, client, requested_at, reviewed_at, expires_epoch, attempts, code_hash, has_code_hash, updated_at, timestamp_to_epoch(updated_at), utc_timestamp(), source_sha256),
                )
        return {"ok": True, "deleted": deleted, "rows": len(rows)}

    return postgres_execute(_write)

# Added 2026-07-25: copy durable auth-session hashes into PostgreSQL without exposing raw tokens.
def postgres_upsert_auth_session_row(row: dict) -> dict:
    token_hash = clean(row.get("token_hash", ""))
    username = normalize_username(row.get("username", ""))
    if not token_hash or not username:
        raise RuntimeError("Missing PostgreSQL auth_session identity.")
    updated_at = clean(row.get("updated_at_utc")) or normalize_timestamp_text(row.get("updated_at_utc"), fallback_now=True)
    payload = {
        "token_hash": token_hash,
        "username": username.lower(),
        "created_epoch": float(row.get("created_epoch") or 0),
        "last_seen_epoch": float(row.get("last_seen_epoch") or 0),
        "last_persisted_epoch": float(row.get("last_persisted_epoch") or 0),
        "expires_epoch": float(row.get("expires_epoch") or 0),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.auth_sessions
                    (token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (token_hash) DO UPDATE SET
                    username=excluded.username,
                    created_epoch=excluded.created_epoch,
                    last_seen_epoch=excluded.last_seen_epoch,
                    last_persisted_epoch=excluded.last_persisted_epoch,
                    expires_epoch=excluded.expires_epoch,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    token_hash, username, payload["created_epoch"], payload["last_seen_epoch"],
                    payload["last_persisted_epoch"], payload["expires_epoch"], updated_at,
                    payload["updated_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "token_hash": token_hash, "username": username, "source_sha256": source_sha256}

    return postgres_execute(_write)

# Added 2026-07-25: process-gated auth session runtime helpers keep raw tokens out of PostgreSQL.
def postgres_load_auth_sessions() -> dict[str, dict]:
    now = time.time()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch "
                "FROM future_server2.auth_sessions WHERE expires_epoch>%s",
                (now,),
            )
            rows = cursor.fetchall()
        return {
            clean(row[0]): {
                "username": normalize_username(row[1]),
                "created_at": float(row[2] or now),
                "last_seen": float(row[3] or now),
                "last_seen_persisted": float(row[4] or row[3] or now),
                "expires_at": float(row[5] or now + 86400),
            }
            for row in rows
            if clean(row[0]) and normalize_username(row[1])
        }

    return postgres_execute(_read)

def postgres_replace_auth_sessions_batch(rows: list[dict] | tuple[dict, ...]) -> int:
    normalized_rows = []
    for item in rows or ():
        username = normalize_username((item or {}).get("username", ""))
        key = clean((item or {}).get("token_hash", ""))
        issued = float((item or {}).get("issued_at", 0) or time.time())
        if not username or len(key) != 64:
            raise RuntimeError("Auth session is invalid.")
        normalized_rows.append((key, username, issued, issued, issued, issued + 86400, local_timestamp(issued), issued))
    if not normalized_rows:
        return 0

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO future_server2.auth_sessions
                    (token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'runtime')
                ON CONFLICT(username) DO UPDATE SET
                    token_hash=excluded.token_hash,
                    created_epoch=excluded.created_epoch,
                    last_seen_epoch=excluded.last_seen_epoch,
                    last_persisted_epoch=excluded.last_persisted_epoch,
                    expires_epoch=excluded.expires_epoch,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                [(a, b, c, d, e, f, g, h, utc_timestamp()) for a, b, c, d, e, f, g, h in normalized_rows],
            )
        return len(normalized_rows)

    return int(postgres_execute(_write) or 0)

def postgres_touch_auth_sessions(rows: dict[str, dict]) -> int:
    source = {clean(key): dict(item) for key, item in (rows or {}).items() if clean(key) and isinstance(item, dict)}
    if not source:
        return 0

    def _write(connection):
        changed = 0
        with connection.cursor() as cursor:
            for key, item in source.items():
                last_seen = max(0.0, float(item.get("last_seen", 0) or 0))
                if last_seen <= 0:
                    continue
                cursor.execute(
                    """
                    UPDATE future_server2.auth_sessions
                    SET last_seen_epoch=GREATEST(last_seen_epoch,%s),
                        last_persisted_epoch=GREATEST(last_persisted_epoch,%s),
                        expires_epoch=GREATEST(expires_epoch,%s),
                        updated_at_utc=%s,
                        updated_epoch=%s,
                        migrated_at_utc=%s
                    WHERE token_hash=%s
                    """,
                    (last_seen, last_seen, last_seen + 86400, local_timestamp(last_seen), last_seen, utc_timestamp(), key),
                )
                changed += max(0, int(cursor.rowcount or 0))
        return changed

    return int(postgres_execute(_write) or 0)

def postgres_delete_auth_sessions(username: str = "", token_hashes: list[str] | tuple[str, ...] | None = None) -> int:
    normalized = normalize_username(username)
    keys = tuple(clean(value) for value in (token_hashes or ()) if clean(value))
    if not normalized and not keys:
        return 0

    def _write(connection):
        with connection.cursor() as cursor:
            before = 0
            if normalized:
                cursor.execute("DELETE FROM future_server2.auth_sessions WHERE username=%s", (normalized,))
                before += max(0, int(cursor.rowcount or 0))
            for key in keys:
                cursor.execute("DELETE FROM future_server2.auth_sessions WHERE token_hash=%s", (key,))
                before += max(0, int(cursor.rowcount or 0))
        return before

    return int(postgres_execute(_write) or 0)

# Added 2026-07-25: migrate chat messages while preserving IDs and operation-id idempotency.
def postgres_upsert_chat_message_row(row: dict) -> dict:
    message_id = max(1, space_w_int(row.get("id", 0), 0))
    username = normalize_username(row.get("username", ""))
    sender = "admin" if clean(row.get("sender", "")).lower() == "admin" else "user"
    operation = clean(row.get("operation_id", ""))[:160]
    message = row.get("message")
    if message is None:
        message = row.get("message_json")
    if isinstance(message, str):
        try:
            message = json.loads(message or "{}")
        except Exception:
            message = {}
    message = message if isinstance(message, dict) else {}
    created_at = clean(row.get("created_at_utc")) or normalize_timestamp_text(message.get("at"), fallback_now=True)
    created_epoch = max(0.0, float(row.get("created_epoch") or 0), timestamp_to_epoch(created_at))
    if not message_id or not username:
        raise RuntimeError("Missing PostgreSQL chat message identity.")
    payload = {
        "id": message_id,
        "username": username.lower(),
        "sender": sender,
        "operation_id": operation,
        "message": message,
        "created_at_utc": created_at,
        "created_epoch": created_epoch,
    }
    raw = json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.chat_messages
                    (id,username,sender,operation_id,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                    username=excluded.username,
                    sender=excluded.sender,
                    operation_id=excluded.operation_id,
                    message_json=excluded.message_json,
                    created_at_utc=excluded.created_at_utc,
                    created_epoch=excluded.created_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (message_id, username, sender, operation, raw, created_at, created_epoch, utc_timestamp(), source_sha256),
            )
        return {"ok": True, "id": message_id, "username": username, "operation_id": operation, "source_sha256": source_sha256}

    return postgres_execute(_write)

# Added 2026-07-25: migrate chat read watermarks as monotonic per-user state.
def postgres_upsert_chat_read_state_row(row: dict) -> dict:
    username = normalize_username(row.get("username", ""))
    if not username:
        raise RuntimeError("Missing PostgreSQL chat read-state identity.")
    updated_at = clean(row.get("updated_at_utc")) or normalize_timestamp_text(row.get("updated_at_utc"), fallback_now=True)
    payload = {
        "username": username.lower(),
        "admin_read": max(0, space_w_int(row.get("admin_read", 0), 0)),
        "user_read": max(0, space_w_int(row.get("user_read", 0), 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.chat_read_state
                    (username,admin_read,user_read,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (username) DO UPDATE SET
                    admin_read=GREATEST(future_server2.chat_read_state.admin_read, excluded.admin_read),
                    user_read=GREATEST(future_server2.chat_read_state.user_read, excluded.user_read),
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (username, payload["admin_read"], payload["user_read"], updated_at, payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": username, "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_chat_state() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,message_json FROM future_server2.chat_messages ORDER BY id DESC LIMIT 800")
            rows = cursor.fetchall()
            messages = []
            for row in reversed(rows):
                item = dict(row[1]) if isinstance(row[1], dict) else {}
                if item:
                    item["id"] = int(row[0] or 0)
                    messages.append(item)
            cursor.execute("SELECT username,admin_read,user_read FROM future_server2.chat_read_state")
            read_rows = cursor.fetchall()
        return {
            "messages": messages,
            "admin_read": {normalize_username(row[0]): max(0, int(row[1] or 0)) for row in read_rows},
            "user_read": {normalize_username(row[0]): max(0, int(row[2] or 0)) for row in read_rows},
        }

    return postgres_execute(_read)

# Added 2026-07-25: runtime PostgreSQL chat insert for feature-flagged validation.
def postgres_add_chat_message(item: dict, operation_id: str = "") -> dict:
    source = dict(item) if isinstance(item, dict) else {}
    username = normalize_username(source.get("username", ""))
    sender = "admin" if clean(source.get("sender", "")).lower() == "admin" else "user"
    operation = clean(operation_id or source.get("operation_id", ""))[:160]
    if operation and not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", operation):
        raise RuntimeError("Chat operation ID is invalid.")
    if not username:
        raise RuntimeError("Chat message requires a username.")
    created_at = normalize_timestamp_text(source.get("at"), fallback_now=True)
    created_epoch = max(0.0, float(source.get("ts", 0) or 0), timestamp_to_epoch(created_at))

    def _write(connection):
        with connection.cursor() as cursor:
            source.pop("id", None)
            source["username"] = username
            source["sender"] = sender
            source["at"] = created_at
            source["ts"] = created_epoch
            if operation:
                source["operation_id"] = operation
            raw = json.dumps(source, ensure_ascii=False, separators=(",", ":"), default=str)
            if operation:
                cursor.execute(
                    """
                    INSERT INTO future_server2.chat_messages(username,sender,operation_id,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                    ON CONFLICT (username,sender,operation_id) WHERE operation_id<>''
                    DO NOTHING
                    RETURNING id
                    """,
                    (
                        username, sender, operation, raw, created_at, created_epoch, utc_timestamp(),
                        hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    cursor.execute(
                        "SELECT id,message_json FROM future_server2.chat_messages WHERE username=%s AND sender=%s AND operation_id=%s",
                        (username, sender, operation),
                    )
                    existing = cursor.fetchone()
                    if existing is not None:
                        message = dict(existing[1]) if isinstance(existing[1], dict) else {}
                        message["id"] = int(existing[0] or 0)
                        return {"message": message, "duplicate": True}
                    raise RuntimeError("Chat operation retry could not find existing message.")
                message_id = int(inserted[0] or 0)
            else:
                cursor.execute(
                    """
                    INSERT INTO future_server2.chat_messages(username,sender,operation_id,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        username, sender, operation, raw, created_at, created_epoch, utc_timestamp(),
                        hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                )
                message_id = int(cursor.fetchone()[0] or 0)
            source["id"] = message_id
            if message_id % 64 == 0:
                cursor.execute(
                    "DELETE FROM future_server2.chat_messages WHERE id IN "
                    "(SELECT id FROM future_server2.chat_messages ORDER BY id DESC LIMIT ALL OFFSET 800)"
                )
            return {"message": source, "duplicate": False}

    return postgres_execute(_write)

def postgres_update_chat_read(username: str, field: str, message_id: int) -> bool:
    normalized = normalize_username(username)
    column = "admin_read" if clean(field).lower() == "admin_read" else "user_read"
    value = max(0, int(message_id or 0))
    if not normalized or value <= 0:
        return False

    def _write(connection):
        now = utc_timestamp()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO future_server2.chat_read_state(username,{column},updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username) DO UPDATE SET
                    {column}=GREATEST(future_server2.chat_read_state.{column}, excluded.{column}),
                    updated_at_utc=CASE WHEN excluded.{column} > future_server2.chat_read_state.{column} THEN excluded.updated_at_utc ELSE future_server2.chat_read_state.updated_at_utc END,
                    updated_epoch=GREATEST(future_server2.chat_read_state.updated_epoch, excluded.updated_epoch),
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                RETURNING {column}
                """,
                (normalized, value, now, timestamp_to_epoch(now), utc_timestamp(), hashlib.sha256(f"{normalized}:{column}:{value}".encode("utf-8")).hexdigest()),
            )
            row = cursor.fetchone()
        return bool(row and int(row[0] or 0) >= value)

    return bool(postgres_execute(_write))

def postgres_replace_chat_state(payload: dict) -> bool:
    state = payload if isinstance(payload, dict) else {}
    messages = [dict(item) for item in state.get("messages", []) if isinstance(item, dict)][-800:]
    admin_read = state.get("admin_read", {}) if isinstance(state.get("admin_read"), dict) else {}
    user_read = state.get("user_read", {}) if isinstance(state.get("user_read"), dict) else {}

    def _write(connection):
        with connection.cursor() as cursor:
            for item in messages:
                message_id = max(0, int(item.get("id", 0) or 0))
                username = normalize_username(item.get("username", ""))
                if message_id <= 0 or not username:
                    continue
                sender = "admin" if clean(item.get("sender", "")).lower() == "admin" else "user"
                operation = clean(item.get("operation_id", ""))[:160]
                created_at = normalize_timestamp_text(item.get("at"), fallback_now=True)
                created_epoch = max(0.0, float(item.get("ts", 0) or 0), timestamp_to_epoch(created_at))
                raw_message = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                source_sha256 = hashlib.sha256(raw_message.encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.chat_messages
                        (id,username,sender,operation_id,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                    ON CONFLICT(id) DO UPDATE SET
                        username=excluded.username,
                        sender=excluded.sender,
                        operation_id=excluded.operation_id,
                        message_json=excluded.message_json,
                        created_at_utc=excluded.created_at_utc,
                        created_epoch=excluded.created_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (message_id, username, sender, operation, raw_message, created_at, created_epoch, utc_timestamp(), source_sha256),
                )
            now = utc_timestamp()
            usernames = {normalize_username(value) for value in (*admin_read.keys(), *user_read.keys()) if normalize_username(value)}
            for username in usernames:
                payload_row = {
                    "username": username,
                    "admin_read": max(0, int(admin_read.get(username, 0) or 0)),
                    "user_read": max(0, int(user_read.get(username, 0) or 0)),
                    "updated_at_utc": now,
                }
                raw = json.dumps(payload_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                cursor.execute(
                    """
                    INSERT INTO future_server2.chat_read_state(username,admin_read,user_read,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(username) DO UPDATE SET
                        admin_read=GREATEST(future_server2.chat_read_state.admin_read, excluded.admin_read),
                        user_read=GREATEST(future_server2.chat_read_state.user_read, excluded.user_read),
                        updated_at_utc=excluded.updated_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (username, payload_row["admin_read"], payload_row["user_read"], now, timestamp_to_epoch(now), utc_timestamp(), hashlib.sha256(raw.encode("utf-8")).hexdigest()),
                )
        return True

    return bool(postgres_execute(_write))

def postgres_delete_chat_user(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.chat_messages WHERE username=%s", (normalized,))
            message_count = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.chat_read_state WHERE username=%s", (normalized,))
            read_count = int(cursor.rowcount or 0)
        return bool(message_count or read_count)

    return bool(postgres_execute(_write))

def postgres_ensure_world_chat_schema() -> None:
    global POSTGRES_WORLD_CHAT_SCHEMA_READY
    if POSTGRES_WORLD_CHAT_SCHEMA_READY:
        return

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS future_server2")
            cursor.execute("CREATE SEQUENCE IF NOT EXISTS future_server2.world_chat_messages_id_seq")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS future_server2.world_chat_messages (
                    id BIGINT PRIMARY KEY DEFAULT nextval('future_server2.world_chat_messages_id_seq'),
                    room_id TEXT NOT NULL DEFAULT 'world',
                    username TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    operation_id TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT '',
                    avatar TEXT NOT NULL DEFAULT '',
                    message_text TEXT NOT NULL DEFAULT '',
                    message_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at_utc TEXT NOT NULL,
                    created_epoch DOUBLE PRECISION NOT NULL DEFAULT 0,
                    migrated_at_utc TEXT NOT NULL DEFAULT '',
                    source_sha256 TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                "ALTER TABLE future_server2.world_chat_messages ALTER COLUMN id SET DEFAULT nextval('future_server2.world_chat_messages_id_seq')"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS world_chat_messages_room_id_idx ON future_server2.world_chat_messages(room_id,id DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS world_chat_messages_room_created_idx ON future_server2.world_chat_messages(room_id,created_epoch DESC)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS world_chat_messages_operation_idx "
                "ON future_server2.world_chat_messages(room_id,username,sender,operation_id) WHERE operation_id<>''"
            )
            cursor.execute(
                """
                SELECT setval(
                    'future_server2.world_chat_messages_id_seq',
                    GREATEST(
                        COALESCE((SELECT max(id) FROM future_server2.world_chat_messages), 0),
                        COALESCE((SELECT last_value FROM future_server2.world_chat_messages_id_seq), 1)
                    ),
                    true
                )
                """
            )
        return True

    postgres_execute(_run)
    POSTGRES_WORLD_CHAT_SCHEMA_READY = True

def postgres_load_world_chat_state(room_id: str = "world") -> dict:
    postgres_ensure_world_chat_schema()
    safe_room = clean(room_id) or "world"

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,room_id,username,sender,operation_id,display_name,avatar,message_text,message_json,created_at_utc,created_epoch "
                "FROM future_server2.world_chat_messages WHERE room_id=%s ORDER BY id DESC LIMIT 100",
                (safe_room,),
            )
            rows = cursor.fetchall()
        messages = []
        for row in reversed(rows):
            item = dict(row[8]) if isinstance(row[8], dict) else {}
            if not item:
                item = {
                    "room_id": clean(row[1]) or safe_room,
                    "username": normalize_username(row[2]),
                    "sender": "admin" if clean(row[3]).lower() == "admin" else "user",
                    "operation_id": clean(row[4]),
                    "display_name": clean(row[5]),
                    "avatar": clean(row[6]),
                    "message": clean(row[7]),
                    "created_at": clean(row[9]),
                    "ts": float(row[10] or 0),
                }
            item["id"] = int(row[0] or 0)
            item["room_id"] = clean(row[1]) or safe_room
            item["username"] = normalize_username(row[2])
            item["sender"] = "admin" if clean(row[3]).lower() == "admin" else "user"
            item["operation_id"] = clean(row[4])
            item["display_name"] = clean(row[5]) or item.get("display_name", "")
            item["avatar"] = clean(row[6]) or item.get("avatar", "")
            item["message"] = clean(row[7]) or item.get("message", "")
            item["created_at"] = clean(row[9]) or item.get("created_at", "")
            item["ts"] = max(0.0, float(row[10] or 0))
            messages.append(item)
        revision = int(rows[0][0] or 0) if rows else 0
        return {"room_id": safe_room, "revision": revision, "messages": messages}

    return postgres_execute(_read)

def postgres_add_world_chat_message(item: dict, operation_id: str = "", room_id: str = "world") -> dict:
    postgres_ensure_world_chat_schema()
    source = dict(item) if isinstance(item, dict) else {}
    safe_room = clean(room_id) or "world"
    username = normalize_username(source.get("username", ""))
    sender = "admin" if clean(source.get("sender", "")).lower() == "admin" else "user"
    operation = clean(operation_id or source.get("operation_id", ""))[:160]
    if operation and not re.fullmatch(r"[A-Za-z0-9._:-]{8,160}", operation):
        raise RuntimeError("World chat operation ID is invalid.")
    if not username:
        raise RuntimeError("World chat message requires a username.")
    created_at = normalize_timestamp_text(source.get("at") or source.get("created_at"), fallback_now=True)
    created_epoch = max(0.0, float(source.get("ts", 0) or 0), timestamp_to_epoch(created_at))
    display_name = clean(source.get("display_name", ""))
    avatar = clean(source.get("avatar", ""))
    message_text = clean(source.get("message", ""))

    def _write(connection):
        with connection.cursor() as cursor:
            if operation.startswith("legacy-"):
                cursor.execute(
                    "SELECT id,message_json FROM future_server2.world_chat_messages "
                    "WHERE room_id=%s AND username=%s AND sender=%s AND display_name=%s AND avatar=%s "
                    "AND message_text=%s AND created_at_utc=%s ORDER BY id LIMIT 1",
                    (safe_room, username, sender, display_name, avatar, message_text, created_at),
                )
                existing_legacy = cursor.fetchone()
                if existing_legacy is not None:
                    message = dict(existing_legacy[1]) if isinstance(existing_legacy[1], dict) else {}
                    message["id"] = int(existing_legacy[0] or 0)
                    return {"message": message, "duplicate": True}
            source.pop("id", None)
            source["room_id"] = safe_room
            source["username"] = username
            source["sender"] = sender
            source["operation_id"] = operation
            source["display_name"] = display_name
            source["avatar"] = avatar
            source["message"] = message_text
            source["at"] = created_at
            source["ts"] = created_epoch
            raw = json.dumps(source, ensure_ascii=False, separators=(",", ":"), default=str)
            if operation:
                cursor.execute(
                    """
                    INSERT INTO future_server2.world_chat_messages
                        (room_id,username,sender,operation_id,display_name,avatar,message_text,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                    ON CONFLICT (room_id,username,sender,operation_id) WHERE operation_id<>''
                    DO NOTHING
                    RETURNING id
                    """,
                    (
                        safe_room, username, sender, operation, display_name, avatar, message_text, raw,
                        created_at, created_epoch, utc_timestamp(), hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    cursor.execute(
                        "SELECT id,message_json FROM future_server2.world_chat_messages WHERE room_id=%s AND username=%s AND sender=%s AND operation_id=%s",
                        (safe_room, username, sender, operation),
                    )
                    existing = cursor.fetchone()
                    if existing is not None:
                        message = dict(existing[1]) if isinstance(existing[1], dict) else {}
                        message["id"] = int(existing[0] or 0)
                        return {"message": message, "duplicate": True}
                    raise RuntimeError("World chat operation retry could not find existing message.")
                message_id = int(inserted[0] or 0)
            else:
                cursor.execute(
                    """
                    INSERT INTO future_server2.world_chat_messages
                        (room_id,username,sender,operation_id,display_name,avatar,message_text,message_json,created_at_utc,created_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        safe_room, username, sender, operation, display_name, avatar, message_text, raw,
                        created_at, created_epoch, utc_timestamp(), hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                )
                message_id = int(cursor.fetchone()[0] or 0)
            source["id"] = message_id
            source["room_id"] = safe_room
            cursor.execute(
                "DELETE FROM future_server2.world_chat_messages WHERE id IN "
                "(SELECT id FROM future_server2.world_chat_messages WHERE room_id=%s ORDER BY id DESC LIMIT ALL OFFSET 100)",
                (safe_room,),
            )
            return {"message": source, "duplicate": False}

    return postgres_execute(_write)

def postgres_delete_world_chat_user(username: str, room_id: str = "world") -> bool:
    postgres_ensure_world_chat_schema()
    normalized = normalize_username(username)
    safe_room = clean(room_id) or "world"
    if not normalized:
        return False

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM future_server2.world_chat_messages WHERE room_id=%s AND username=%s",
                (safe_room, normalized),
            )
            return int(cursor.rowcount or 0) > 0

    return bool(postgres_execute(_write))

def postgres_lesson_task_payload(row: dict) -> tuple[dict, str, str]:
    record = row.get("record")
    if record is None:
        record = row.get("record_json")
    if isinstance(record, str):
        try:
            record = json.loads(record or "{}")
        except Exception:
            record = {}
    record = record if isinstance(record, dict) else {}
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at")) or normalize_timestamp_text(row.get("updated_at_utc"), fallback_now=True)
    payload = {
        "username": normalize_username(row.get("username", "")).lower(),
        "record": record,
        "server_revision": max(1, space_w_int(row.get("server_revision") or row.get("revision"), 1)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    return payload, encoded, source_sha256

# Added 2026-07-25: migrate and validate Space Task state rows without changing the default PostgreSQL path.
def postgres_upsert_lesson_task_state_row(row: dict) -> dict:
    payload, encoded, source_sha256 = postgres_lesson_task_payload(row)
    username = normalize_username(payload.get("username", ""))
    if not username:
        raise RuntimeError("Missing PostgreSQL lesson_task_state identity.")

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_task_state
                    (username,record_json,server_revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT(username) DO UPDATE SET
                    record_json=excluded.record_json,
                    server_revision=excluded.server_revision,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (username, encoded, payload["server_revision"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": username, "revision": payload["server_revision"], "updated_at": payload["updated_at_utc"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_lesson_task_record(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"record": {}, "revision": 0, "updated_at": ""}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT record_json,server_revision,updated_at_utc FROM future_server2.lesson_task_state WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            row = cursor.fetchone()
        if row is None:
            return {"record": {}, "revision": 0, "updated_at": ""}
        record = dict(row[0]) if isinstance(row[0], dict) else {}
        return {"record": record, "revision": max(0, space_w_int(row[1], 0)), "updated_at": clean(row[2])}

    return postgres_execute(_read)

def postgres_load_all_lesson_task_records() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT username,record_json,updated_at_utc FROM future_server2.lesson_task_state ORDER BY lower(username)")
            rows = cursor.fetchall()
        by_user = {}
        updated_at = ""
        for row in rows:
            username = normalize_username(row[0])
            record = dict(row[1]) if isinstance(row[1], dict) else {}
            if username and isinstance(record, dict):
                by_user[username] = record
            updated_at = timestamp_latest_text(updated_at, clean(row[2]))
        return {"version": 1, "updated_at": updated_at, "by_user": by_user}

    return postgres_execute(_read)

def postgres_write_lesson_task_record(username: str, record: dict | None = None) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        raise RuntimeError("Missing Lesson Task user.")
    source = server_database_normalize_timestamps(record if isinstance(record, dict) else {})
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT record_json,server_revision,updated_at_utc FROM future_server2.lesson_task_state WHERE lower(username)=lower(%s)",
                (normalized,),
            )
            current = cursor.fetchone()
            if current is not None:
                current_record = current[0] if isinstance(current[0], dict) else {}
                current_encoded = json.dumps(current_record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                if current_encoded == encoded:
                    return {
                        "record": source,
                        "revision": max(0, space_w_int(current[1], 0)),
                        "updated_at": clean(current[2]),
                        "changed": False,
                    }
            revision = max(0, space_w_int(current[1], 0)) + 1 if current is not None else 1
            updated_at = utc_timestamp()
            payload = {
                "username": normalized.lower(),
                "record": source,
                "server_revision": revision,
                "updated_at_utc": updated_at,
                "updated_epoch": timestamp_to_epoch(updated_at),
            }
            source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_task_state(username,record_json,server_revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT(username) DO UPDATE SET
                    record_json=excluded.record_json,
                    server_revision=excluded.server_revision,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (normalized, encoded, revision, updated_at, payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"record": source, "revision": revision, "updated_at": updated_at, "changed": True}

    return postgres_execute(_write)

def postgres_delete_lesson_task_record(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_task_state WHERE lower(username)=lower(%s)", (normalized,))
            return bool(cursor.rowcount or 0)

    return bool(postgres_execute(_write))

# Added 2026-07-27: PostgreSQL-only Lesson Task builds need a cheap learning
# state presence probe without touching a disabled local database connection.
def postgres_user_has_lesson_state(username: str) -> bool:
    normalized = normalize_username(username)
    if not normalized:
        return False

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    EXISTS(SELECT 1 FROM future_server2.lesson_progress WHERE lower(username)=lower(%s) LIMIT 1)
                    OR EXISTS(SELECT 1 FROM future_server2.lesson_time WHERE lower(username)=lower(%s) LIMIT 1)
                    OR EXISTS(SELECT 1 FROM future_server2.vocabulary_registry WHERE lower(username)=lower(%s) LIMIT 1)
                    OR EXISTS(SELECT 1 FROM future_server2.append_events WHERE lower(username)=lower(%s) LIMIT 1)
                """,
                (normalized, normalized, normalized, normalized),
            )
            row = cursor.fetchone()
        return bool(row and row[0])

    return bool(postgres_execute(_read))

def postgres_lesson_file_count() -> int:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.lesson_files")
            row = cursor.fetchone()
        return max(0, int((row[0] if row else 0) or 0))

    return int(postgres_execute(_read) or 0)

def postgres_lesson_time_row_from_source(row: dict) -> dict:
    updated_at = clean(row.get("updated_at_utc") or row.get("updatedAt", ""))
    return {
        "username": normalize_username(row.get("username", "")),
        "lesson_key": clean(row.get("lesson_key", "")),
        "file_id": clean(row.get("file_id", ""))[:240],
        "path": clean_path_value(row.get("path", "")),
        "title": clean(row.get("title", ""))[:180],
        "space": clean(row.get("space", ""))[:40],
        "seconds": max(0, space_w_int(row.get("seconds", 0), 0)),
        "ticks": max(0, space_w_int(row.get("ticks", 0), 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": max(0.0, float(row.get("updated_epoch", 0) or 0), timestamp_to_epoch(updated_at)),
    }

# Added 2026-07-25: copy lesson time totals into PostgreSQL without enabling write cutover.
def postgres_upsert_lesson_time_row(row: dict) -> dict:
    payload = postgres_lesson_time_row_from_source(row)
    if not payload["username"] or not payload["lesson_key"]:
        raise RuntimeError("Missing PostgreSQL lesson_time identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_time
                    (username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username,lesson_key) DO UPDATE SET
                    file_id=excluded.file_id,
                    path=excluded.path,
                    title=excluded.title,
                    space=excluded.space,
                    seconds=excluded.seconds,
                    ticks=excluded.ticks,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["username"], payload["lesson_key"], payload["file_id"], payload["path"], payload["title"],
                    payload["space"], payload["seconds"], payload["ticks"], payload["updated_at_utc"],
                    payload["updated_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": payload["username"], "lesson_key": payload["lesson_key"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_lesson_time_credit_row_from_source(row: dict) -> dict:
    updated_at = clean(row.get("updated_at_utc") or row.get("updatedAt", ""))
    return {
        "username": normalize_username(row.get("username", "")),
        "lesson_key": clean(row.get("lesson_key", "")),
        "file_id": clean(row.get("file_id", ""))[:240],
        "session_id": clean(row.get("session_id", ""))[:96],
        "last_sequence": max(0, space_w_int(row.get("last_sequence", 0), 0)),
        "last_seen_epoch": max(0.0, float(row.get("last_seen_epoch", 0) or 0)),
        "boot_id": clean(row.get("boot_id", ""))[:120],
        "lease_issued_epoch": max(0.0, float(row.get("lease_issued_epoch", 0) or 0)),
        "offline_credited_seconds": max(0, space_w_int(row.get("offline_credited_seconds", 0), 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_upsert_lesson_time_credit_state_row(row: dict) -> dict:
    payload = postgres_lesson_time_credit_row_from_source(row)
    if not payload["username"] or not payload["lesson_key"]:
        raise RuntimeError("Missing PostgreSQL lesson_time_credit_state identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_time_credit_state
                    (username,lesson_key,file_id,session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,offline_credited_seconds,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username,lesson_key) DO UPDATE SET
                    file_id=excluded.file_id,
                    session_id=excluded.session_id,
                    last_sequence=excluded.last_sequence,
                    last_seen_epoch=excluded.last_seen_epoch,
                    boot_id=excluded.boot_id,
                    lease_issued_epoch=excluded.lease_issued_epoch,
                    offline_credited_seconds=excluded.offline_credited_seconds,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["username"], payload["lesson_key"], payload["file_id"], payload["session_id"],
                    payload["last_sequence"], payload["last_seen_epoch"], payload["boot_id"], payload["lease_issued_epoch"],
                    payload["offline_credited_seconds"], payload["updated_at_utc"], payload["updated_epoch"],
                    utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": payload["username"], "lesson_key": payload["lesson_key"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_lesson_time_payload(username: str) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"version": 1, "updated_at": "", "states": {}}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc FROM future_server2.lesson_time WHERE lower(username)=lower(%s) ORDER BY updated_epoch",
                (normalized,),
            )
            rows = cursor.fetchall()
        states = {}
        updated_at = ""
        for row in rows:
            lesson_key = clean(row[0])
            if not lesson_key:
                continue
            seconds = max(0, space_w_int(row[5], 0))
            states[lesson_key] = {
                "file_id": clean(row[1])[:240],
                "lesson_id": clean(row[1])[:240],
                "path": clean_path_value(row[2]),
                "title": clean(row[3])[:180],
                "space": clean(row[4])[:40],
                "seconds": seconds,
                "ticks": max(0, space_w_int(row[6], 0)),
                "minutes": round(seconds / 60, 2),
                "updatedAt": clean(row[7]),
            }
            updated_at = clean(row[7])
        return {"version": 1, "updated_at": updated_at, "states": states}

    return postgres_execute(_read)

def postgres_inventory_item_row_from_source(row: dict) -> dict:
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "username": normalize_username(row.get("username", "")),
        "item_id": clean(row.get("item_id") or row.get("id", ""))[:80],
        "name": clean(row.get("name", ""))[:160],
        "use_text": clean(row.get("use_text") or row.get("use", ""))[:320],
        "quantity": max(0, space_w_int(row.get("quantity", 0), 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_inventory_event_row_from_source(row: dict) -> dict:
    awarded_at = clean(row.get("awarded_at_utc") or row.get("awarded_at", ""))
    return {
        "username": normalize_username(row.get("username", "")),
        "event_id": clean(row.get("event_id", ""))[:240],
        "item_id": clean(row.get("item_id", ""))[:80],
        "quantity": max(0, space_w_int(row.get("quantity", 0), 0)),
        "awarded_at_utc": awarded_at,
        "awarded_epoch": timestamp_to_epoch(awarded_at),
    }

# Added 2026-07-25: copy inventory item totals into PostgreSQL without enabling award cutover.
def postgres_upsert_inventory_item_row(row: dict) -> dict:
    payload = postgres_inventory_item_row_from_source(row)
    if not payload["username"] or not payload["item_id"]:
        raise RuntimeError("Missing PostgreSQL inventory item identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.inventory_items
                    (username,item_id,name,use_text,quantity,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username,item_id) DO UPDATE SET
                    name=excluded.name,
                    use_text=excluded.use_text,
                    quantity=excluded.quantity,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["username"], payload["item_id"], payload["name"], payload["use_text"],
                    payload["quantity"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": payload["username"], "item_id": payload["item_id"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_upsert_inventory_event_row(row: dict) -> dict:
    payload = postgres_inventory_event_row_from_source(row)
    if not payload["username"] or not payload["event_id"]:
        raise RuntimeError("Missing PostgreSQL inventory event identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.inventory_events
                    (username,event_id,item_id,quantity,awarded_at_utc,awarded_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username,event_id) DO UPDATE SET
                    item_id=excluded.item_id,
                    quantity=excluded.quantity,
                    awarded_at_utc=excluded.awarded_at_utc,
                    awarded_epoch=excluded.awarded_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["username"], payload["event_id"], payload["item_id"], payload["quantity"],
                    payload["awarded_at_utc"], payload["awarded_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "username": payload["username"], "event_id": payload["event_id"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_inventory_payload(username: str, event_limit: int = 5000) -> dict:
    normalized = normalize_username(username)
    if not normalized:
        return {"version": 1, "updated_at": "", "items": {}, "events": []}
    try:
        safe_event_limit = max(0, min(5000, int(event_limit)))
    except (TypeError, ValueError):
        safe_event_limit = 5000

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT item_id,name,use_text,quantity,updated_at_utc FROM future_server2.inventory_items WHERE lower(username)=lower(%s) ORDER BY item_id",
                (normalized,),
            )
            item_rows = cursor.fetchall()
            if safe_event_limit:
                cursor.execute(
                    "SELECT event_id,awarded_at_utc FROM future_server2.inventory_events WHERE lower(username)=lower(%s) ORDER BY awarded_epoch DESC LIMIT %s",
                    (normalized, safe_event_limit),
                )
                event_rows = cursor.fetchall()
            else:
                event_rows = []
        items = {
            clean(row[0]): {
                "id": clean(row[0]),
                "name": clean(row[1])[:160],
                "use": clean(row[2])[:320],
                "quantity": max(0, space_w_int(row[3], 0)),
                "updated_at": clean(row[4]),
            }
            for row in item_rows
            if clean(row[0])
        }
        events = [clean(row[0]) for row in reversed(event_rows) if clean(row[0])]
        updated_candidates = [clean(row[4]) for row in item_rows] + [clean(row[1]) for row in event_rows]
        updated_at = timestamp_latest_text(*updated_candidates) if updated_candidates else ""
        return {"version": 1, "updated_at": updated_at, "items": items, "events": events}

    return postgres_execute(_read)

def postgres_vocab_image_cache_row_from_source(row: dict) -> dict:
    image = row.get("image")
    if image is None:
        image = row.get("image_json")
    if isinstance(image, str):
        try:
            image = json.loads(image or "{}")
        except Exception:
            image = {}
    image = image if isinstance(image, dict) else {}
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "word_key": clean(row.get("word_key", "")).lower(),
        "image": image,
        "expires_epoch": max(0.0, float(row.get("expires_epoch", 0) or 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_upsert_vocab_image_cache_row(row: dict) -> dict:
    payload = postgres_vocab_image_cache_row_from_source(row)
    if not payload["word_key"]:
        raise RuntimeError("Missing PostgreSQL vocab_image_cache identity.")
    raw = json.dumps(payload["image"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vocab_image_cache
                    (word_key,image_json,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT(word_key) DO UPDATE SET
                    image_json=excluded.image_json,
                    expires_epoch=excluded.expires_epoch,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (payload["word_key"], raw, payload["expires_epoch"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "word_key": payload["word_key"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_load_vocab_image_cache(word_key: str) -> dict | None:
    key = clean(word_key).lower()
    if not key:
        return None

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT image_json,expires_epoch FROM future_server2.vocab_image_cache WHERE word_key=%s AND expires_epoch>%s",
                (key, time.time()),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        image = dict(row[0]) if isinstance(row[0], dict) else {}
        return {"image": image, "expires_epoch": float(row[1] or 0)}

    return postgres_execute(_read)

def postgres_load_vocab_image_cache_rows(limit: int = 2048) -> list[dict]:
    safe_limit = max(1, min(10000, int(limit or 2048)))

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT word_key,image_json,expires_epoch FROM future_server2.vocab_image_cache WHERE expires_epoch>%s ORDER BY expires_epoch DESC LIMIT %s",
                (time.time(), safe_limit),
            )
            rows = cursor.fetchall()
        return [
            {"word_key": clean(row[0]).lower(), "image": dict(row[1]) if isinstance(row[1], dict) else {}, "expires_epoch": float(row[2] or 0)}
            for row in rows
            if clean(row[0])
        ]

    return postgres_execute(_read)

def postgres_store_vocab_image_cache_batch(rows: list[dict] | tuple[dict, ...]) -> int:
    normalized = [postgres_vocab_image_cache_row_from_source(row if isinstance(row, dict) else {}) for row in rows or ()]
    normalized = [row for row in normalized if row["word_key"] and isinstance(row["image"], dict) and row["expires_epoch"] > 0]
    if not normalized:
        return 0

    def _write(connection):
        count = 0
        with connection.cursor() as cursor:
            for row in normalized:
                raw = json.dumps(row["image"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                if not row["updated_at_utc"]:
                    row = {**row, "updated_at_utc": local_timestamp(), "updated_epoch": time.time()}
                source_sha256 = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.vocab_image_cache(word_key,image_json,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                    ON CONFLICT(word_key) DO UPDATE SET image_json=excluded.image_json,
                        expires_epoch=excluded.expires_epoch,
                        updated_at_utc=excluded.updated_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (row["word_key"], raw, row["expires_epoch"], row["updated_at_utc"], row["updated_epoch"], utc_timestamp(), source_sha256),
                )
                count += 1
        return count

    return int(postgres_execute(_write) or 0)


# Added 2026-08-04: read one user's selected primary image with an indexed two-column lookup.
def postgres_load_vocab_image_selection(username: str, word_key: str) -> dict:
    normalized_user = normalize_username(username)
    key = clean(word_key).lower()[:180]
    if not normalized_user or not key:
        return {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT image_id,operation_id,server_revision,selected_at_utc,selected_epoch "
                "FROM future_server2.vocab_image_selection WHERE lower(username)=lower(%s) AND word_key=%s",
                (normalized_user, key),
            )
            row = cursor.fetchone()
        return {
            "image_id": clean(row[0]),
            "operation_id": clean(row[1]),
            "server_revision": max(1, int(row[2] or 1)),
            "selected_at": clean(row[3]),
            "selected_epoch": max(0.0, float(row[4] or 0)),
        } if row else {}

    return postgres_execute(_read)


# Added 2026-08-04: persist one primary-image choice atomically and reject out-of-order device writes by numeric epoch.
def postgres_save_vocab_image_selection(username: str, word_key: str, image_id: str, operation_id: str = "", selected_epoch: object = 0) -> dict:
    normalized_user = normalize_username(username)
    key = clean(word_key).lower()[:180]
    selected_image = clean(image_id)[:260]
    operation = clean(operation_id)[:160]
    if not normalized_user or not key or not selected_image:
        raise RuntimeError("Invalid vocabulary image selection.")
    try:
        incoming_epoch = float(selected_epoch or 0)
    except (TypeError, ValueError):
        incoming_epoch = 0.0
    now_epoch = time.time()
    if incoming_epoch <= 0 or abs(incoming_epoch - now_epoch) > 300.0:
        incoming_epoch = now_epoch

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"future-vocab-image:{normalized_user.lower()}:{key}",))
            cursor.execute(
                "SELECT image_id,operation_id,server_revision,selected_at_utc,selected_epoch "
                "FROM future_server2.vocab_image_selection WHERE lower(username)=lower(%s) AND word_key=%s FOR UPDATE",
                (normalized_user, key),
            )
            row = cursor.fetchone()
            if row and operation and clean(row[1]) == operation:
                return {"image_id": clean(row[0]), "operation_id": clean(row[1]), "server_revision": max(1, int(row[2] or 1)), "selected_at": clean(row[3]), "selected_epoch": max(0.0, float(row[4] or 0)), "changed": False}
            current_epoch = max(0.0, float(row[4] or 0)) if row else 0.0
            if row and incoming_epoch < current_epoch:
                return {"image_id": clean(row[0]), "operation_id": clean(row[1]), "server_revision": max(1, int(row[2] or 1)), "selected_at": clean(row[3]), "selected_epoch": current_epoch, "changed": False, "stale": True}
            revision = max(1, int(row[2] or 1) + 1) if row else 1
            selected_at = utc_timestamp()
            cursor.execute(
                """
                INSERT INTO future_server2.vocab_image_selection
                    (username,word_key,image_id,operation_id,server_revision,selected_at_utc,selected_epoch)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username,word_key) DO UPDATE SET
                    image_id=excluded.image_id,
                    operation_id=excluded.operation_id,
                    server_revision=excluded.server_revision,
                    selected_at_utc=excluded.selected_at_utc,
                    selected_epoch=excluded.selected_epoch
                """,
                (normalized_user, key, selected_image, operation, revision, selected_at, incoming_epoch),
            )
        return {"image_id": selected_image, "operation_id": operation, "server_revision": revision, "selected_at": selected_at, "selected_epoch": incoming_epoch, "changed": True}

    return postgres_execute(_write)

def postgres_lesson_file_alias_row_from_source(row: dict) -> dict:
    first_seen = clean(row.get("first_seen_at_utc") or row.get("first_seen", ""))
    last_seen = clean(row.get("last_seen_at_utc") or row.get("last_seen", ""))
    return {
        "normalized_path": clean_path_value(row.get("normalized_path", "")).lower(),
        "file_id": clean(row.get("file_id", ""))[:240],
        "source": clean(row.get("source", ""))[:80] or "manifest",
        "active": bool(row.get("active")),
        "first_seen_at_utc": first_seen,
        "first_seen_epoch": timestamp_to_epoch(first_seen),
        "last_seen_at_utc": last_seen,
        "last_seen_epoch": timestamp_to_epoch(last_seen),
    }

# Added 2026-07-25: copy path-to-lesson identity aliases into PostgreSQL for canonical-ID migration.
def postgres_upsert_lesson_file_alias_row(row: dict) -> dict:
    payload = postgres_lesson_file_alias_row_from_source(row)
    if not payload["normalized_path"] or not payload["file_id"]:
        raise RuntimeError("Missing PostgreSQL lesson_file_alias identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_file_aliases
                    (normalized_path,file_id,source,active,first_seen_at_utc,first_seen_epoch,last_seen_at_utc,last_seen_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(normalized_path) DO UPDATE SET
                    file_id=excluded.file_id,
                    source=excluded.source,
                    active=excluded.active,
                    first_seen_at_utc=excluded.first_seen_at_utc,
                    first_seen_epoch=excluded.first_seen_epoch,
                    last_seen_at_utc=excluded.last_seen_at_utc,
                    last_seen_epoch=excluded.last_seen_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["normalized_path"], payload["file_id"], payload["source"], payload["active"],
                    payload["first_seen_at_utc"], payload["first_seen_epoch"], payload["last_seen_at_utc"],
                    payload["last_seen_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "normalized_path": payload["normalized_path"], "file_id": payload["file_id"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_lesson_file_row_from_source(row: dict) -> dict:
    created_at = clean(row.get("created_at_utc") or row.get("created_at", ""))
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    deleted_at = clean(row.get("deleted_at_utc") or row.get("deleted_at", ""))
    return {
        "file_id": clean(row.get("file_id", ""))[:240],
        "space_id": clean(row.get("space_id", ""))[:240],
        "kind": clean(row.get("kind", ""))[:40] or "space",
        "canonical_fingerprint": clean(row.get("canonical_fingerprint", "")),
        "identity_revision": max(1, space_w_int(row.get("identity_revision", 1), 1)),
        "status": clean(row.get("status", ""))[:40] or "active",
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "deleted_at_utc": deleted_at,
        "deleted_epoch": timestamp_to_epoch(deleted_at),
    }

def postgres_lesson_file_replica_row_from_source(row: dict) -> dict:
    first_seen = clean(row.get("first_seen_at_utc") or row.get("first_seen", ""))
    last_seen = clean(row.get("last_seen_at_utc") or row.get("last_seen", ""))
    return {
        "replica_id": max(1, space_w_int(row.get("replica_id", 0), 0)),
        "file_id": clean(row.get("file_id", ""))[:240],
        "normalized_path": clean_path_value(row.get("normalized_path", "")).lower(),
        "fingerprint": clean(row.get("fingerprint", "")),
        "file_mtime_ns": max(0, space_w_int(row.get("file_mtime_ns", 0), 0)),
        "file_size": max(0, space_w_int(row.get("file_size", 0), 0)),
        "status": clean(row.get("status", ""))[:40] or "active",
        "first_seen_at_utc": first_seen,
        "first_seen_epoch": timestamp_to_epoch(first_seen),
        "last_seen_at_utc": last_seen,
        "last_seen_epoch": timestamp_to_epoch(last_seen),
    }

def postgres_upsert_lesson_file_row(row: dict) -> dict:
    payload = postgres_lesson_file_row_from_source(row)
    if not payload["file_id"]:
        raise RuntimeError("Missing PostgreSQL lesson_file identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_files
                    (file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,deleted_at_utc,deleted_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(file_id) DO UPDATE SET
                    space_id=excluded.space_id,
                    kind=excluded.kind,
                    canonical_fingerprint=excluded.canonical_fingerprint,
                    identity_revision=excluded.identity_revision,
                    status=excluded.status,
                    created_at_utc=excluded.created_at_utc,
                    created_epoch=excluded.created_epoch,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    deleted_at_utc=excluded.deleted_at_utc,
                    deleted_epoch=excluded.deleted_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["file_id"], payload["space_id"], payload["kind"], payload["canonical_fingerprint"],
                    payload["identity_revision"], payload["status"], payload["created_at_utc"], payload["created_epoch"],
                    payload["updated_at_utc"], payload["updated_epoch"], payload["deleted_at_utc"], payload["deleted_epoch"],
                    utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "file_id": payload["file_id"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_upsert_lesson_file_replica_row(row: dict) -> dict:
    payload = postgres_lesson_file_replica_row_from_source(row)
    if not payload["replica_id"] or not payload["file_id"] or not payload["normalized_path"]:
        raise RuntimeError("Missing PostgreSQL lesson_file_replica identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_file_replicas
                    (replica_id,file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,first_seen_epoch,last_seen_at_utc,last_seen_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(replica_id) DO UPDATE SET
                    file_id=excluded.file_id,
                    normalized_path=excluded.normalized_path,
                    fingerprint=excluded.fingerprint,
                    file_mtime_ns=excluded.file_mtime_ns,
                    file_size=excluded.file_size,
                    status=excluded.status,
                    first_seen_at_utc=excluded.first_seen_at_utc,
                    first_seen_epoch=excluded.first_seen_epoch,
                    last_seen_at_utc=excluded.last_seen_at_utc,
                    last_seen_epoch=excluded.last_seen_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["replica_id"], payload["file_id"], payload["normalized_path"], payload["fingerprint"],
                    payload["file_mtime_ns"], payload["file_size"], payload["status"], payload["first_seen_at_utc"],
                    payload["first_seen_epoch"], payload["last_seen_at_utc"], payload["last_seen_epoch"],
                    utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "replica_id": payload["replica_id"], "file_id": payload["file_id"], "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_vault_folder_row_from_source(row: dict) -> dict:
    created_at = clean(row.get("created_at_utc") or row.get("created_at", ""))
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "vault_folder_id": clean(row.get("vault_folder_id", ""))[:240],
        "username": normalize_username(row.get("username", "")),
        "parent_folder_id": clean(row.get("parent_folder_id", ""))[:240],
        "display_name": clean(row.get("display_name", ""))[:240],
        "folder_type": clean(row.get("folder_type", ""))[:40] or "VIRTUAL",
        "source_path": clean_path_value(row.get("source_path", "")),
        "sort_order": space_w_int(row.get("sort_order", 0), 0),
        "status": clean(row.get("status", ""))[:40] or "active",
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_vault_entry_row_from_source(row: dict) -> dict:
    created_at = clean(row.get("created_at_utc") or row.get("created_at", ""))
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    physical = row.get("physical_replica_id")
    return {
        "vault_entry_id": clean(row.get("vault_entry_id", ""))[:240],
        "username": normalize_username(row.get("username", "")),
        "parent_folder_id": clean(row.get("parent_folder_id", ""))[:240],
        "lesson_id": clean(row.get("lesson_id", ""))[:240],
        "entry_type": clean(row.get("entry_type", ""))[:40],
        "physical_replica_id": None if physical is None else max(0, space_w_int(physical, 0)),
        "source_entry_id": clean(row.get("source_entry_id", ""))[:240],
        "source_path": clean_path_value(row.get("source_path", "")),
        "display_name": clean(row.get("display_name", ""))[:240],
        "sort_order": space_w_int(row.get("sort_order", 0), 0),
        "status": clean(row.get("status", ""))[:40] or "active",
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_vault_revision_row_from_source(row: dict) -> dict:
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "username": normalize_username(row.get("username", "")),
        "revision": max(1, space_w_int(row.get("revision", 1), 1)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_upsert_vault_folder_row(row: dict) -> dict:
    payload = postgres_vault_folder_row_from_source(row)
    if not payload["vault_folder_id"] or not payload["username"]:
        raise RuntimeError("Missing PostgreSQL vault_folder identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vault_folders
                    (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(vault_folder_id) DO UPDATE SET
                    username=excluded.username,parent_folder_id=excluded.parent_folder_id,display_name=excluded.display_name,
                    folder_type=excluded.folder_type,source_path=excluded.source_path,sort_order=excluded.sort_order,status=excluded.status,
                    created_at_utc=excluded.created_at_utc,created_epoch=excluded.created_epoch,updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                """,
                (payload["vault_folder_id"], payload["username"], payload["parent_folder_id"], payload["display_name"], payload["folder_type"], payload["source_path"], payload["sort_order"], payload["status"], payload["created_at_utc"], payload["created_epoch"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "vault_folder_id": payload["vault_folder_id"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_upsert_vault_entry_row(row: dict) -> dict:
    payload = postgres_vault_entry_row_from_source(row)
    if not payload["vault_entry_id"] or not payload["username"]:
        raise RuntimeError("Missing PostgreSQL vault_entry identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vault_entries
                    (vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(vault_entry_id) DO UPDATE SET
                    username=excluded.username,parent_folder_id=excluded.parent_folder_id,lesson_id=excluded.lesson_id,entry_type=excluded.entry_type,
                    physical_replica_id=excluded.physical_replica_id,source_entry_id=excluded.source_entry_id,source_path=excluded.source_path,
                    display_name=excluded.display_name,sort_order=excluded.sort_order,status=excluded.status,created_at_utc=excluded.created_at_utc,
                    created_epoch=excluded.created_epoch,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                """,
                (payload["vault_entry_id"], payload["username"], payload["parent_folder_id"], payload["lesson_id"], payload["entry_type"], payload["physical_replica_id"], payload["source_entry_id"], payload["source_path"], payload["display_name"], payload["sort_order"], payload["status"], payload["created_at_utc"], payload["created_epoch"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "vault_entry_id": payload["vault_entry_id"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_upsert_vault_revision_row(row: dict) -> dict:
    payload = postgres_vault_revision_row_from_source(row)
    if not payload["username"]:
        raise RuntimeError("Missing PostgreSQL vault_revision identity.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.vault_revisions(username,revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(username) DO UPDATE SET
                    revision=excluded.revision,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                """,
                (payload["username"], payload["revision"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "username": payload["username"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_lesson_folder_link_row_from_source(row: dict) -> dict:
    payload = row.get("payload")
    if payload is None:
        payload = row.get("payload_json")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload or "{}")
        except Exception:
            payload = {}
    payload = payload if isinstance(payload, dict) else {}
    created_at = clean(row.get("created_at_utc") or row.get("created_at", ""))
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "link_path": clean_path_value(row.get("link_path", "")),
        "target_path": clean_path_value(row.get("target_path", "")),
        "created_by": normalize_username(row.get("created_by", "")),
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "payload": payload,
        "revision": max(1, space_w_int(row.get("revision", 1), 1)),
        "status": clean(row.get("status", ""))[:40] or "active",
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_upsert_lesson_folder_link_row(row: dict) -> dict:
    payload = postgres_lesson_folder_link_row_from_source(row)
    if not payload["link_path"] or not payload["target_path"]:
        raise RuntimeError("Missing PostgreSQL lesson_folder_link identity.")
    raw_payload = json.dumps(payload["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_folder_links
                    (link_path,target_path,created_by,created_at_utc,created_epoch,payload_json,revision,status,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(link_path) DO UPDATE SET
                    target_path=excluded.target_path,
                    created_by=excluded.created_by,
                    created_at_utc=excluded.created_at_utc,
                    created_epoch=excluded.created_epoch,
                    payload_json=excluded.payload_json,
                    revision=excluded.revision,
                    status=excluded.status,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["link_path"], payload["target_path"], payload["created_by"], payload["created_at_utc"],
                    payload["created_epoch"], raw_payload, payload["revision"], payload["status"], payload["updated_at_utc"],
                    payload["updated_epoch"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "link_path": payload["link_path"], "target_path": payload["target_path"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_lesson_progress_orphan_row_from_source(row: dict) -> dict:
    record = row.get("record")
    if record is None:
        record = row.get("record_json")
    if isinstance(record, str):
        try:
            record = json.loads(record or "{}")
        except Exception:
            record = {}
    record = record if isinstance(record, dict) else {}
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    archived_at = clean(row.get("archived_at_utc") or row.get("archived_at", ""))
    return {
        "id": max(1, space_w_int(row.get("id", 0), 0)),
        "username": normalize_username(row.get("username", "")),
        "space": clean(row.get("space", ""))[:40],
        "progress_key": clean(row.get("progress_key", "")),
        "path": clean_path_value(row.get("path", "")),
        "identity": clean(row.get("identity", ""))[:240],
        "server_revision": max(0, space_w_int(row.get("server_revision", 0), 0)),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "record": record,
        "archived_at_utc": archived_at,
        "archived_epoch": timestamp_to_epoch(archived_at),
        "reason": clean(row.get("reason", ""))[:80] or "missing_file",
    }

def postgres_upsert_lesson_progress_orphan_row(row: dict) -> dict:
    payload = postgres_lesson_progress_orphan_row_from_source(row)
    if not payload["id"] or not payload["username"] or not payload["space"] or not payload["progress_key"]:
        raise RuntimeError("Missing PostgreSQL lesson_progress_orphan identity.")
    raw_record = json.dumps(payload["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress_orphans
                    (id,username,space,progress_key,path,identity,server_revision,updated_at_utc,updated_epoch,record_json,archived_at_utc,archived_epoch,reason,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT(id) DO UPDATE SET
                    username=excluded.username,space=excluded.space,progress_key=excluded.progress_key,path=excluded.path,
                    identity=excluded.identity,server_revision=excluded.server_revision,updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,record_json=excluded.record_json,archived_at_utc=excluded.archived_at_utc,
                    archived_epoch=excluded.archived_epoch,reason=excluded.reason,migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["id"], payload["username"], payload["space"], payload["progress_key"], payload["path"],
                    payload["identity"], payload["server_revision"], payload["updated_at_utc"], payload["updated_epoch"],
                    raw_record, payload["archived_at_utc"], payload["archived_epoch"], payload["reason"], utc_timestamp(), source_sha256,
                ),
            )
        return {"ok": True, "id": payload["id"], "username": payload["username"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_database_meta_row_from_source(row: dict) -> dict:
    updated_at = clean(row.get("updated_at_utc") or row.get("updated_at", ""))
    return {
        "key": clean(row.get("key", ""))[:240],
        "value": clean(row.get("value", "")),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
    }

def postgres_upsert_database_meta_row(row: dict) -> dict:
    payload = postgres_database_meta_row_from_source(row)
    if not payload["key"]:
        raise RuntimeError("Missing PostgreSQL database_meta key.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.database_meta(key,value,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (payload["key"], payload["value"], payload["updated_at_utc"], payload["updated_epoch"], utc_timestamp(), source_sha256),
            )
        return {"ok": True, "key": payload["key"], "source_sha256": source_sha256}
    return postgres_execute(_write)

def postgres_load_database_meta_value(key: str) -> str:
    safe_key = clean(key)[:240]
    if not safe_key:
        return ""

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM future_server2.database_meta WHERE key=%s",
                (safe_key,),
            )
            row = cursor.fetchone()
        return clean(row[0]) if row else ""

    return postgres_execute(_read)

def postgres_store_database_meta_value(key: str, value: str, updated_at_utc: str = "") -> dict:
    payload = {
        "key": clean(key)[:240],
        "value": clean(value),
        "updated_at_utc": clean(updated_at_utc) or utc_timestamp(),
    }
    if not payload["key"]:
        raise RuntimeError("Missing PostgreSQL database_meta key.")
    source_sha256 = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.database_meta(key,value,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (payload["key"], payload["value"], payload["updated_at_utc"], timestamp_to_epoch(payload["updated_at_utc"]), utc_timestamp(), source_sha256),
            )
        return {"ok": True, **payload, "source_sha256": source_sha256}

    return postgres_execute(_write)

def postgres_canonical_migration_archive_row_from_source(row: dict) -> dict:
    import sys
    from FUTURE.server_parts import postgres_domain_canonical_migration_archive as domain
    return domain.row_from_source(row, sys.modules[__name__])

def postgres_upsert_canonical_migration_archive_row(row: dict) -> dict:
    import sys
    from FUTURE.server_parts import postgres_domain_canonical_migration_archive as domain
    return domain.upsert_row(row, sys.modules[__name__])

def postgres_space_pdf_document_row_from_source(row: dict) -> dict:
    created_at = clean(row.get("created_at_utc", ""))
    updated_at = clean(row.get("updated_at_utc", ""))
    return {
        "document_id": clean(row.get("document_id", ""))[:240],
        "source_sha256": clean(row.get("source_sha256", "")),
        "source_bytes": max(0, space_w_int(row.get("source_bytes", 0), 0)),
        "mime_type": clean(row.get("mime_type", ""))[:120] or "application/pdf",
        "page_count": max(0, space_w_int(row.get("page_count", 0), 0)),
        "status": clean(row.get("status", ""))[:40] or "active",
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "asset_id": clean(row.get("asset_id", ""))[:240],
        "asset_locator": clean(row.get("asset_locator", "")),
    }

def postgres_space_pdf_lesson_meta_row_from_source(row: dict) -> dict:
    created_at = clean(row.get("created_at_utc", ""))
    updated_at = clean(row.get("updated_at_utc", ""))
    return {
        "file_id": clean(row.get("file_id", ""))[:240],
        "document_id": clean(row.get("document_id", ""))[:240],
        "schema_version": max(0, space_w_int(row.get("schema_version", 0), 0)),
        "package_revision": max(0, space_w_int(row.get("package_revision", 0), 0)),
        "title": clean(row.get("title", ""))[:300],
        "owner_scope": clean(row.get("owner_scope", ""))[:120] or "common",
        "source_filename": clean(row.get("source_filename", ""))[:260],
        "source_sha256": clean(row.get("source_sha256", "")),
        "package_fingerprint": clean(row.get("package_fingerprint", "")),
        "status": clean(row.get("status", ""))[:40] or "active",
        "created_at_utc": created_at,
        "created_epoch": timestamp_to_epoch(created_at),
        "updated_at_utc": updated_at,
        "updated_epoch": timestamp_to_epoch(updated_at),
        "space_id": clean(row.get("space_id", ""))[:40] or "Space_PDF",
        "asset_id": clean(row.get("asset_id", ""))[:240],
        "asset_locator": clean(row.get("asset_locator", "")),
    }

def postgres_space_pdf_package_replica_row_from_source(row: dict) -> dict:
    first_seen = clean(row.get("first_seen_at_utc", ""))
    last_seen = clean(row.get("last_seen_at_utc", ""))
    return {
        "normalized_path": clean_path_value(row.get("normalized_path", "")).lower(),
        "file_id": clean(row.get("file_id", ""))[:240],
        "document_id": clean(row.get("document_id", ""))[:240],
        "package_sha256": clean(row.get("package_sha256", "")),
        "semantic_fingerprint": clean(row.get("semantic_fingerprint", "")),
        "schema_version": max(0, space_w_int(row.get("schema_version", 0), 0)),
        "package_revision": max(0, space_w_int(row.get("package_revision", 0), 0)),
        "status": clean(row.get("status", ""))[:40] or "active",
        "first_seen_at_utc": first_seen,
        "first_seen_epoch": timestamp_to_epoch(first_seen),
        "last_seen_at_utc": last_seen,
        "last_seen_epoch": timestamp_to_epoch(last_seen),
        "space_id": clean(row.get("space_id", ""))[:40] or "Space_PDF",
    }

def postgres_upsert_space_pdf_document_row(row: dict) -> dict:
    payload = postgres_space_pdf_document_row_from_source(row)
    if not payload["document_id"]:
        raise RuntimeError("Missing PostgreSQL space_pdf_document identity.")
    row_sha = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.space_pdf_documents(document_id,source_sha256,source_bytes,mime_type,page_count,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,asset_id,asset_locator,migrated_at_utc,row_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(document_id) DO UPDATE SET source_sha256=excluded.source_sha256,source_bytes=excluded.source_bytes,mime_type=excluded.mime_type,page_count=excluded.page_count,status=excluded.status,created_at_utc=excluded.created_at_utc,created_epoch=excluded.created_epoch,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch,asset_id=excluded.asset_id,asset_locator=excluded.asset_locator,migrated_at_utc=excluded.migrated_at_utc,row_sha256=excluded.row_sha256
                """,
                (payload["document_id"], payload["source_sha256"], payload["source_bytes"], payload["mime_type"], payload["page_count"], payload["status"], payload["created_at_utc"], payload["created_epoch"], payload["updated_at_utc"], payload["updated_epoch"], payload["asset_id"], payload["asset_locator"], utc_timestamp(), row_sha),
            )
        return {"ok": True, "document_id": payload["document_id"], "source_sha256": row_sha}
    return postgres_execute(_write)

def postgres_upsert_space_pdf_lesson_meta_row(row: dict) -> dict:
    payload = postgres_space_pdf_lesson_meta_row_from_source(row)
    if not payload["file_id"] or not payload["document_id"]:
        raise RuntimeError("Missing PostgreSQL space_pdf_lesson_meta identity.")
    row_sha = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.space_pdf_lesson_meta(file_id,document_id,schema_version,package_revision,title,owner_scope,source_filename,source_sha256,package_fingerprint,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,space_id,asset_id,asset_locator,migrated_at_utc,row_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(file_id) DO UPDATE SET document_id=excluded.document_id,schema_version=excluded.schema_version,package_revision=excluded.package_revision,title=excluded.title,owner_scope=excluded.owner_scope,source_filename=excluded.source_filename,source_sha256=excluded.source_sha256,package_fingerprint=excluded.package_fingerprint,status=excluded.status,created_at_utc=excluded.created_at_utc,created_epoch=excluded.created_epoch,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch,space_id=excluded.space_id,asset_id=excluded.asset_id,asset_locator=excluded.asset_locator,migrated_at_utc=excluded.migrated_at_utc,row_sha256=excluded.row_sha256
                """,
                (payload["file_id"], payload["document_id"], payload["schema_version"], payload["package_revision"], payload["title"], payload["owner_scope"], payload["source_filename"], payload["source_sha256"], payload["package_fingerprint"], payload["status"], payload["created_at_utc"], payload["created_epoch"], payload["updated_at_utc"], payload["updated_epoch"], payload["space_id"], payload["asset_id"], payload["asset_locator"], utc_timestamp(), row_sha),
            )
        return {"ok": True, "file_id": payload["file_id"], "source_sha256": row_sha}
    return postgres_execute(_write)

def postgres_upsert_space_pdf_package_replica_row(row: dict) -> dict:
    payload = postgres_space_pdf_package_replica_row_from_source(row)
    if not payload["normalized_path"] or not payload["file_id"]:
        raise RuntimeError("Missing PostgreSQL space_pdf_package_replica identity.")
    row_sha = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.space_pdf_package_replicas(normalized_path,file_id,document_id,package_sha256,semantic_fingerprint,schema_version,package_revision,status,first_seen_at_utc,first_seen_epoch,last_seen_at_utc,last_seen_epoch,space_id,migrated_at_utc,row_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,document_id=excluded.document_id,package_sha256=excluded.package_sha256,semantic_fingerprint=excluded.semantic_fingerprint,schema_version=excluded.schema_version,package_revision=excluded.package_revision,status=excluded.status,first_seen_at_utc=excluded.first_seen_at_utc,first_seen_epoch=excluded.first_seen_epoch,last_seen_at_utc=excluded.last_seen_at_utc,last_seen_epoch=excluded.last_seen_epoch,space_id=excluded.space_id,migrated_at_utc=excluded.migrated_at_utc,row_sha256=excluded.row_sha256
                """,
                (payload["normalized_path"], payload["file_id"], payload["document_id"], payload["package_sha256"], payload["semantic_fingerprint"], payload["schema_version"], payload["package_revision"], payload["status"], payload["first_seen_at_utc"], payload["first_seen_epoch"], payload["last_seen_at_utc"], payload["last_seen_epoch"], payload["space_id"], utc_timestamp(), row_sha),
            )
        return {"ok": True, "normalized_path": payload["normalized_path"], "source_sha256": row_sha}
    return postgres_execute(_write)
