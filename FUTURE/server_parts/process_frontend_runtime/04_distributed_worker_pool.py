# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

import zipfile

DISTRIBUTED_WORKER_TOKEN_FILE = RUNTIME_ROOT / "distributed_worker_token.txt"
DISTRIBUTED_WORKER_CODE_TOKEN_FILE = ROOT / "FUTURE" / "server2" / "distributed_worker_token.local.txt"
DISTRIBUTED_WORKER_STABLE_TOKEN_FILE = SERVER_DATA_ROOT / "_future_distributed_worker_token.txt"
DISTRIBUTED_WORKER_CLIENT_SCRIPT = ROOT / "FUTURE" / "server2" / "future_distributed_worker_client.py"


# Added 2026-07-09: keeps huge worker EXE/ZIP build caches off the crowded C: drive when D: exists.
def default_distributed_worker_cache_root() -> Path:
    raw = clean(os.environ.get("FUTURE_DISTRIBUTED_WORKER_CACHE_ROOT", ""))
    if raw:
        return Path(raw).resolve()
    if Path("D:/").exists():
        return Path("D:/FutureWorkerCache/distributed_worker")
    return RUNTIME_ROOT / "distributed_worker"


DISTRIBUTED_WORKER_CACHE_ROOT = default_distributed_worker_cache_root()
DISTRIBUTED_WORKER_PACKAGE_CACHE_DIR = DISTRIBUTED_WORKER_CACHE_ROOT / "packages"
DISTRIBUTED_WORKER_EXE_CACHE_DIR = DISTRIBUTED_WORKER_CACHE_ROOT / "exe"
DISTRIBUTED_WORKER_EXE_PATH = DISTRIBUTED_WORKER_EXE_CACHE_DIR / "FutureWorker.exe"
DISTRIBUTED_WORKER_EXE_META_PATH = DISTRIBUTED_WORKER_EXE_CACHE_DIR / "FutureWorker.embed.json"
DISTRIBUTED_WORKER_EXE_BUILD_LOCK = threading.Lock()
DISTRIBUTED_WORKER_STALE_SECONDS = 45
DISTRIBUTED_WORKER_MAX_RESULT_BYTES = 512 * 1024 * 1024
DISTRIBUTED_WORKER_LOCK = threading.RLock()
DISTRIBUTED_WORKER_CONDITION = threading.Condition(DISTRIBUTED_WORKER_LOCK)
DISTRIBUTED_WORKERS: dict[str, dict] = {}
DISTRIBUTED_WORKER_JOBS: dict[str, dict] = {}
DISTRIBUTED_WORKER_QUEUE: list[str] = []
DISTRIBUTED_WORKER_LOGS: list[dict] = []
DISTRIBUTED_WORKER_STATS = {
    "created": 0,
    "completed": 0,
    "failed": 0,
    "timeout": 0,
    "fallback": 0,
    "retried": 0,
}
DISTRIBUTED_WORKER_JOB_KINDS = ("translate", "tts", "stt", "gemini", "phonemize")
DISTRIBUTED_WORKER_ASSIGN_GRACE_SECONDS = 4.0
DISTRIBUTED_WORKER_MAX_ATTEMPTS_PER_WORKER = 5
DISTRIBUTED_WORKER_MAX_TOTAL_ATTEMPTS = 40
DISTRIBUTED_WORKER_ROUND_ROBIN_CURSOR: dict[str, int] = {}


def distributed_worker_clean_capabilities(value) -> list[str]:
    if isinstance(value, str):
        raw_items = re.split(r"[\s,;|]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = []
    allowed = set(DISTRIBUTED_WORKER_JOB_KINDS)
    result = []
    for item in raw_items:
        key = clean(item).lower()
        if key in allowed and key not in result:
            result.append(key)
    return result or ["translate"]


# Added 2026-07-07: keeps worker lane capacity bounded and dashboard-controlled.
def distributed_worker_job_limits() -> dict:
    try:
        settings = load_server_settings()
        limits = normalize_distributed_worker_job_limits(settings.get("distributed_worker_job_limits", {}))
    except Exception:
        limits = dict(DEFAULT_SETTINGS.get("distributed_worker_job_limits", {}))
    return normalize_distributed_worker_job_limits(limits)


# Added 2026-07-07: caps Auto worker apps per machine; internal lanes provide concurrency.
def distributed_worker_machine_limit() -> int:
    try:
        settings = load_server_settings()
        amount = normalize_distributed_worker_machine_limit(settings.get("distributed_worker_machine_limit", 1))
    except Exception:
        amount = int(DEFAULT_SETTINGS.get("distributed_worker_machine_limit", 1) or 1)
    return max(1, min(32, int(amount or 1)))


# Added 2026-07-13: lets total job capacity grow with online worker lanes instead of a fixed global cap.
def distributed_worker_effective_job_limit_locked(kind: str, payload: dict | None = None) -> int:
    key = clean(kind).lower()
    configured = distributed_worker_job_limits()
    base_limit = int(configured.get(key, 0) or 0)
    now = time.time()
    worker_capacity = 0
    for worker in DISTRIBUTED_WORKERS.values():
        if worker.get("status") != "online":
            continue
        if key not in (worker.get("capabilities") or []):
            continue
        if now - float(worker.get("last_seen", 0) or 0) > DISTRIBUTED_WORKER_STALE_SECONDS:
            continue
        if not distributed_worker_supports_job_payload(worker, key, payload):
            continue
        max_jobs = distributed_worker_clean_max_jobs(worker.get("max_jobs_by_kind", {}), worker.get("capabilities") or [])
        worker_capacity += int(max_jobs.get(key, 0) or 0)
    return max(0, min(128, max(base_limit, worker_capacity)))


# Added 2026-07-07: normalizes per-worker max jobs so one worker can run one lane of each kind.
def distributed_worker_clean_max_jobs(value, capabilities: list[str] | None = None) -> dict:
    caps = set(capabilities or DISTRIBUTED_WORKER_JOB_KINDS)
    source = value if isinstance(value, dict) else {}
    result: dict[str, int] = {}
    for kind in DISTRIBUTED_WORKER_JOB_KINDS:
        if kind not in caps:
            result[kind] = 0
            continue
        try:
            amount = int(float(source.get(kind, 1)))
        except Exception:
            amount = 1
        result[kind] = max(0, min(16, amount))
    return result


# Added 2026-07-11: lets Server 2 route Kokoro VI only to workers that proved local support.
def distributed_worker_clean_features(value) -> dict:
    source = value if isinstance(value, dict) else {}
    truthy_values = {"1", "true", "yes", "on", "ok", "ready", "supported"}
    return {
        "tts_kokoro_vi": clean(source.get("tts_kokoro_vi", source.get("ttsKokoroVi", ""))).lower() in truthy_values,
        "tts_kokoro_vi_cuda": clean(source.get("tts_kokoro_vi_cuda", source.get("ttsKokoroViCuda", ""))).lower() in truthy_values,
        "tts_kokoro_vi_warm": clean(source.get("tts_kokoro_vi_warm", source.get("ttsKokoroViWarm", ""))).lower() in truthy_values,
        "phonemize_warm": clean(source.get("phonemize_warm", source.get("phonemizeWarm", ""))).lower() in truthy_values,
        "spacy_warm": clean(source.get("spacy_warm", source.get("spacyWarm", ""))).lower() in truthy_values,
        "kokoro_vi_error": clean(source.get("kokoro_vi_error", source.get("kokoroViError", "")))[:500],
        "kokoro_vi_python": clean(source.get("kokoro_vi_python", source.get("kokoroViPython", "")))[:260],
    }


def distributed_worker_supports_job_payload(worker: dict | None, kind: str, payload: dict | None = None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    key = clean(kind).lower()
    if key != "tts":
        return True
    voice = clean(payload.get("voice", payload.get("voice_key", payload.get("voiceKey", "")))).lower()
    if voice.startswith("kokoro_vi:"):
        if truthy(payload.get("_allow_unsupported_worker_once", False), False):
            return True
        features = distributed_worker_clean_features((worker or {}).get("features", {}))
        return bool(features.get("tts_kokoro_vi"))
    return True


# Added 2026-07-07: tracks active jobs by worker lane instead of one global busy flag.
def distributed_worker_active_jobs(worker: dict | None) -> dict:
    worker = worker if isinstance(worker, dict) else {}
    raw = worker.get("active_jobs", {})
    result: dict[str, list[str]] = {kind: [] for kind in DISTRIBUTED_WORKER_JOB_KINDS}
    if isinstance(raw, dict):
        for kind in DISTRIBUTED_WORKER_JOB_KINDS:
            value = raw.get(kind, [])
            values = value if isinstance(value, list) else ([value] if value else [])
            result[kind] = [clean(item) for item in values if clean(item)]
    elif worker.get("current_job"):
        job_id = clean(worker.get("current_job", ""))
        job = DISTRIBUTED_WORKER_JOBS.get(job_id, {})
        kind = clean(job.get("kind", "")).lower()
        if kind in result:
            result[kind] = [job_id]
    return result


def distributed_worker_apply_active_jobs(worker: dict, active_jobs: dict) -> None:
    normalized = distributed_worker_active_jobs({"active_jobs": active_jobs})
    flat = [job_id for ids in normalized.values() for job_id in ids]
    worker["active_jobs"] = normalized
    worker["busy_kinds"] = [kind for kind, ids in normalized.items() if ids]
    worker["busy"] = bool(flat)
    worker["current_job"] = ",".join(flat[:4])


def distributed_worker_active_count(kind: str = "") -> int:
    key = clean(kind).lower()
    total = 0
    for worker in DISTRIBUTED_WORKERS.values():
        active = distributed_worker_active_jobs(worker)
        if key:
            total += len(active.get(key, []))
        else:
            total += sum(len(ids) for ids in active.values())
    return total


# Added 2026-07-07: score workers for fair job reservation before the poll race starts.
def distributed_worker_score(worker: dict, kind: str, preferred_user: str = "") -> tuple:
    active = distributed_worker_active_jobs(worker)
    max_jobs = distributed_worker_clean_max_jobs(worker.get("max_jobs_by_kind", {}), worker.get("capabilities") or [])
    kind_capacity = max(1, int(max_jobs.get(clean(kind).lower(), 1) or 1))
    total_capacity = max(1, sum(max(0, int(max_jobs.get(job_kind, 0) or 0)) for job_kind in DISTRIBUTED_WORKER_JOB_KINDS))
    kind_load = len(active.get(clean(kind).lower(), []))
    total_load = sum(len(ids) for ids in active.values())
    owner = clean(worker.get("owner_user", "")).lower()
    preferred = clean(preferred_user).lower()
    return (
        0 if preferred and owner == preferred else 1,
        kind_load / kind_capacity,
        total_load / total_capacity,
        kind_load,
        total_load,
        int(worker.get("assigned", 0) or 0),
        int(worker.get(f"assigned_{kind}", 0) or 0),
        float(worker.get("last_assigned_at", 0) or 0),
        int(worker.get("completed", 0) or 0),
        clean(worker.get("worker_id", "")),
    )


# Added 2026-07-07: deals jobs like cards across workers that still have a free lane.
def distributed_worker_load_key(worker: dict, kind: str) -> tuple:
    key = clean(kind).lower()
    active = distributed_worker_active_jobs(worker)
    max_jobs = distributed_worker_clean_max_jobs(worker.get("max_jobs_by_kind", {}), worker.get("capabilities") or [])
    kind_capacity = max(1, int(max_jobs.get(key, 1) or 1))
    total_capacity = max(1, sum(max(0, int(max_jobs.get(job_kind, 0) or 0)) for job_kind in DISTRIBUTED_WORKER_JOB_KINDS))
    kind_load = len(active.get(key, []))
    total_load = sum(len(ids) for ids in active.values())
    return (
        kind_load / kind_capacity,
        total_load / total_capacity,
        kind_load,
        total_load,
    )


def distributed_worker_pick_round_robin(available: list[dict], kind: str, preferred_user: str = "") -> dict | None:
    key = clean(kind).lower()
    preferred = clean(preferred_user).lower()
    candidates = list(available or [])
    if preferred:
        preferred_rows = [worker for worker in candidates if clean(worker.get("owner_user", "")).lower() == preferred]
        if preferred_rows:
            candidates = preferred_rows
    if not candidates:
        return None
    best_load = min(distributed_worker_load_key(worker, key) for worker in candidates)
    lowest_load = [worker for worker in candidates if distributed_worker_load_key(worker, key) == best_load]
    lowest_load.sort(key=lambda worker: clean(worker.get("worker_id", "")))
    cursor = int(DISTRIBUTED_WORKER_ROUND_ROBIN_CURSOR.get(key, 0) or 0)
    selected = lowest_load[cursor % len(lowest_load)]
    DISTRIBUTED_WORKER_ROUND_ROBIN_CURSOR[key] = cursor + 1
    return selected


# Added 2026-07-09: keeps the distributed-worker token stable even if runtime cache is cleaned.
def read_distributed_worker_token_file(path: Path) -> str:
    try:
        if path.is_file():
            token = clean(path.read_text(encoding="utf-8", errors="replace"))
            if len(token) >= 24:
                return token
    except Exception:
        return ""
    return ""


# Added 2026-07-07: creates a shared token for public pull-workers without exposing anonymous job endpoints.
def ensure_distributed_worker_token() -> str:
    try:
        SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        token = read_distributed_worker_token_file(DISTRIBUTED_WORKER_CODE_TOKEN_FILE)
        if not token:
            token = read_distributed_worker_token_file(DISTRIBUTED_WORKER_STABLE_TOKEN_FILE)
        if not token:
            token = read_distributed_worker_token_file(DISTRIBUTED_WORKER_TOKEN_FILE)
            if token:
                try:
                    atomic_write_text(DISTRIBUTED_WORKER_STABLE_TOKEN_FILE, token, encoding="utf-8")
                except Exception:
                    pass
        if token:
            try:
                if read_distributed_worker_token_file(DISTRIBUTED_WORKER_CODE_TOKEN_FILE) != token:
                    atomic_write_text(DISTRIBUTED_WORKER_CODE_TOKEN_FILE, token, encoding="utf-8")
            except Exception:
                pass
            try:
                if read_distributed_worker_token_file(DISTRIBUTED_WORKER_STABLE_TOKEN_FILE) != token:
                    atomic_write_text(DISTRIBUTED_WORKER_STABLE_TOKEN_FILE, token, encoding="utf-8")
            except Exception:
                pass
            try:
                if read_distributed_worker_token_file(DISTRIBUTED_WORKER_TOKEN_FILE) != token:
                    atomic_write_text(DISTRIBUTED_WORKER_TOKEN_FILE, token, encoding="utf-8")
            except Exception:
                pass
            return token
        token = secrets.token_urlsafe(32)
        atomic_write_text(DISTRIBUTED_WORKER_CODE_TOKEN_FILE, token, encoding="utf-8")
        atomic_write_text(DISTRIBUTED_WORKER_STABLE_TOKEN_FILE, token, encoding="utf-8")
        atomic_write_text(DISTRIBUTED_WORKER_TOKEN_FILE, token, encoding="utf-8")
        return token
    except Exception:
        return clean(os.environ.get("FUTURE_DISTRIBUTED_WORKER_TOKEN", "")) or "future-worker-local-token"


def distributed_worker_public_token_hint() -> str:
    token = ensure_distributed_worker_token()
    if len(token) <= 12:
        return token
    return f"{token[:6]}...{token[-6:]}"


def distributed_worker_auth_token(headers=None, payload: dict | None = None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    token = clean(payload.get("token", ""))
    if not token and headers is not None:
        auth = clean(headers.get("Authorization", ""))
        if auth.lower().startswith("bearer "):
            token = clean(auth[7:])
        if not token:
            token = clean(headers.get("X-Future-Worker-Token", ""))
    return token


def distributed_worker_authorized(headers=None, payload: dict | None = None) -> bool:
    return hmac.compare_digest(distributed_worker_auth_token(headers, payload), ensure_distributed_worker_token())


def distributed_worker_prune_locked(now: float | None = None) -> None:
    now = float(now or time.time())
    for worker in DISTRIBUTED_WORKERS.values():
        last_seen = float(worker.get("last_seen", 0) or 0)
        if last_seen and now - last_seen > DISTRIBUTED_WORKER_STALE_SECONDS:
            if worker.get("status") != "offline":
                worker_id = clean(worker.get("worker_id", ""))
                active = distributed_worker_active_jobs(worker)
                for job_ids in active.values():
                    for job_id in list(job_ids):
                        distributed_worker_requeue_job_locked(job_id, worker_id, "Worker went offline.", now)
                worker["status"] = "offline"
                distributed_worker_apply_active_jobs(worker, {})
                worker["updated_at"] = now


# Added 2026-07-07: retries failed/offline distributed jobs on another worker before falling back.
def distributed_worker_requeue_job_locked(job_id: str, worker_id: str = "", error: str = "", now: float | None = None) -> bool:
    job = DISTRIBUTED_WORKER_JOBS.get(clean(job_id))
    if not job or job.get("status") not in {"queued", "claimed"}:
        return False
    now = float(now or time.time())
    attempts = int(job.get("attempts", 1) or 1)
    attempts_by_worker = job.get("attempts_by_worker") if isinstance(job.get("attempts_by_worker"), dict) else {}
    failed_workers = [clean(item) for item in (job.get("failed_workers") or []) if clean(item)]
    clean_worker = clean(worker_id or job.get("worker_id", ""))
    if clean_worker:
        attempts_by_worker[clean_worker] = int(attempts_by_worker.get(clean_worker, 0) or 0) + 1
    if clean_worker and attempts_by_worker.get(clean_worker, 0) >= DISTRIBUTED_WORKER_MAX_ATTEMPTS_PER_WORKER and clean_worker not in failed_workers:
        failed_workers.append(clean_worker)
    if attempts >= DISTRIBUTED_WORKER_MAX_TOTAL_ATTEMPTS:
        job.update({
            "status": "failed",
            "error": clean(error)[:1200] or "Worker failed.",
            "attempts_by_worker": attempts_by_worker,
            "failed_workers": failed_workers,
            "finished_at": now,
        })
        DISTRIBUTED_WORKER_STATS["failed"] += 1
        event = job.get("event")
        if event:
            event.set()
        return False
    job.update({
        "status": "queued",
        "worker_id": "",
        "claimed_at": 0,
        "target_worker_id": "",
        "target_exclusive_until": 0,
        "exclusive_until": 0,
        "attempts": attempts + 1,
        "attempts_by_worker": attempts_by_worker,
        "failed_workers": failed_workers,
        "last_error": clean(error)[:1200],
        "retried_at": now,
    })
    if job_id not in DISTRIBUTED_WORKER_QUEUE:
        DISTRIBUTED_WORKER_QUEUE.insert(0, job_id)
    DISTRIBUTED_WORKER_STATS["retried"] += 1
    return True


def distributed_worker_retry_turn_allowed_locked(job: dict, worker_id: str, job_kind: str) -> bool:
    attempts_by_worker = job.get("attempts_by_worker") if isinstance(job.get("attempts_by_worker"), dict) else {}
    failed_workers = {clean(item) for item in (job.get("failed_workers") or []) if clean(item)}
    current_attempts = int(attempts_by_worker.get(worker_id, 0) or 0)
    if worker_id in failed_workers or current_attempts >= DISTRIBUTED_WORKER_MAX_ATTEMPTS_PER_WORKER:
        return False
    now = time.time()
    candidates = []
    for row in DISTRIBUTED_WORKERS.values():
        candidate_id = clean(row.get("worker_id", ""))
        if not candidate_id or candidate_id in failed_workers:
            continue
        if row.get("status") != "online":
            continue
        if job_kind not in (row.get("capabilities") or []):
            continue
        if not distributed_worker_supports_job_payload(row, job_kind, job.get("payload") if isinstance(job.get("payload"), dict) else {}):
            continue
        if now - float(row.get("last_seen", 0) or 0) > DISTRIBUTED_WORKER_STALE_SECONDS:
            continue
        active = distributed_worker_active_jobs(row)
        max_jobs = distributed_worker_clean_max_jobs(row.get("max_jobs_by_kind", {}), row.get("capabilities") or [])
        if len(active.get(job_kind, [])) >= int(max_jobs.get(job_kind, 1) or 0):
            continue
        candidates.append(int(attempts_by_worker.get(candidate_id, 0) or 0))
    if not candidates:
        return True
    return current_attempts <= min(candidates)


def distributed_worker_available_locked(kind: str, preferred_user: str = "", payload: dict | None = None) -> list[dict]:
    now = time.time()
    distributed_worker_prune_locked(now)
    key = clean(kind).lower()
    effective_limit = distributed_worker_effective_job_limit_locked(key, payload)
    if effective_limit <= 0 or distributed_worker_active_count(key) >= effective_limit:
        return []
    preferred = clean(preferred_user).lower()
    rows = []
    for worker in DISTRIBUTED_WORKERS.values():
        if worker.get("status") != "online":
            continue
        if key not in (worker.get("capabilities") or []):
            continue
        if not distributed_worker_supports_job_payload(worker, key, payload):
            continue
        if now - float(worker.get("last_seen", 0) or 0) > DISTRIBUTED_WORKER_STALE_SECONDS:
            continue
        active = distributed_worker_active_jobs(worker)
        max_jobs = distributed_worker_clean_max_jobs(worker.get("max_jobs_by_kind", {}), worker.get("capabilities") or [])
        if len(active.get(key, [])) >= int(max_jobs.get(key, 1) or 0):
            continue
        rows.append(worker)
    rows.sort(key=lambda worker: distributed_worker_score(worker, key, preferred))
    return rows


def distributed_worker_register(payload: dict, client_ip: str = "", user_agent: str = "") -> dict:
    if not distributed_worker_authorized(None, payload):
        raise PermissionError("Worker token is invalid.")
    now = time.time()
    worker_id = clean(payload.get("worker_id", "")) or uuid.uuid4().hex[:16]
    name = clean(payload.get("name", "")) or f"worker-{worker_id[:6]}"
    owner_user = clean(payload.get("owner_user", payload.get("owner", payload.get("username", "")))).lower()
    caps = distributed_worker_clean_capabilities(payload.get("capabilities", []))
    max_jobs = distributed_worker_clean_max_jobs(payload.get("max_jobs_by_kind", payload.get("maxJobsByKind", {})), caps)
    features = distributed_worker_clean_features(payload.get("features", {}))
    machine_id = clean(payload.get("machine_id", payload.get("machineId", "")))[:120]
    machine_name = clean(payload.get("machine_name", payload.get("machineName", "")))[:120] or name
    machine_key = machine_id or machine_name or name
    with DISTRIBUTED_WORKER_CONDITION:
        limit = distributed_worker_machine_limit()
        existing_worker = DISTRIBUTED_WORKERS.get(worker_id)
        if not existing_worker:
            online_same_machine = 0
            for row in DISTRIBUTED_WORKERS.values():
                if row.get("status") != "online":
                    continue
                row_machine = clean(row.get("machine_key", "")) or clean(row.get("machine_id", "")) or clean(row.get("machine_name", "")) or clean(row.get("name", ""))
                if row_machine and machine_key and row_machine == machine_key:
                    online_same_machine += 1
            if online_same_machine >= limit:
                return {
                    "worker_id": worker_id,
                    "rejected": True,
                    "error": f"Machine worker limit reached ({limit}).",
                    "machine_limit": limit,
                    "job_limits": distributed_worker_job_limits(),
                    "token_hint": distributed_worker_public_token_hint(),
                    "capabilities": caps,
                }
        worker = DISTRIBUTED_WORKERS.get(worker_id) or {
            "worker_id": worker_id,
            "created_at": now,
            "completed": 0,
            "failed": 0,
        }
        worker.update({
            "name": name[:80],
            "capabilities": caps,
            "features": features,
            "owner_user": owner_user[:80],
            "machine_id": machine_id,
            "machine_name": machine_name[:120],
            "machine_key": machine_key[:160],
            "status": "online",
            "max_jobs_by_kind": max_jobs,
            "last_seen": now,
            "updated_at": now,
            "client_ip": clean(client_ip)[:80],
            "user_agent": clean(user_agent)[:180],
            "version": clean(payload.get("version", ""))[:40],
            "message": clean(payload.get("message", ""))[:220],
        })
        distributed_worker_apply_active_jobs(worker, distributed_worker_active_jobs(worker))
        DISTRIBUTED_WORKERS[worker_id] = worker
        DISTRIBUTED_WORKER_CONDITION.notify_all()
    return {
        "worker_id": worker_id,
        "token_hint": distributed_worker_public_token_hint(),
        "capabilities": caps,
        "job_limits": distributed_worker_job_limits(),
        "machine_limit": distributed_worker_machine_limit(),
    }


def distributed_worker_poll(payload: dict, client_ip: str = "", user_agent: str = "", wait_seconds: float = 20.0) -> dict:
    if not distributed_worker_authorized(None, payload):
        raise PermissionError("Worker token is invalid.")
    worker_id = clean(payload.get("worker_id", ""))
    if not worker_id:
        return {"job": None, "error": "missing worker_id"}
    caps = distributed_worker_clean_capabilities(payload.get("capabilities", []))
    lane = clean(payload.get("lane", payload.get("kind", payload.get("job_kind", "")))).lower()
    if lane and lane not in caps:
        return {"job": None, "error": "unsupported lane"}
    if not lane:
        lane = ""
    max_jobs = distributed_worker_clean_max_jobs(payload.get("max_jobs_by_kind", payload.get("maxJobsByKind", {})), caps)
    features = distributed_worker_clean_features(payload.get("features", {}))
    claim_limit_raw = payload.get("claim_limit", payload.get("claimLimit", 1))
    try:
        claim_limit = int(float(claim_limit_raw or 1))
    except Exception:
        claim_limit = 1
    claim_limit = max(1, min(32, claim_limit))
    deadline = time.time() + max(0.0, min(30.0, float(wait_seconds or 0)))
    with DISTRIBUTED_WORKER_CONDITION:
        worker = DISTRIBUTED_WORKERS.get(worker_id)
        if not worker:
            worker = distributed_worker_register({**payload, "token": ensure_distributed_worker_token()}, client_ip, user_agent)
            worker = DISTRIBUTED_WORKERS.get(worker_id, {})
        worker.update({
            "capabilities": caps,
            "features": features,
            "max_jobs_by_kind": max_jobs,
            "owner_user": clean(payload.get("owner_user", payload.get("owner", payload.get("username", worker.get("owner_user", ""))))).lower()[:80],
            "machine_id": clean(payload.get("machine_id", payload.get("machineId", worker.get("machine_id", ""))))[:120],
            "machine_name": clean(payload.get("machine_name", payload.get("machineName", worker.get("machine_name", worker.get("name", "")))))[:120],
            "machine_key": (clean(payload.get("machine_id", payload.get("machineId", worker.get("machine_id", "")))) or clean(payload.get("machine_name", payload.get("machineName", worker.get("machine_name", worker.get("name", ""))))) or clean(worker.get("name", "")))[:160],
            "status": "online",
            "last_seen": time.time(),
            "updated_at": time.time(),
            "client_ip": clean(client_ip)[:80],
            "user_agent": clean(user_agent)[:180],
        })
        distributed_worker_apply_active_jobs(worker, distributed_worker_active_jobs(worker))
        while True:
            distributed_worker_prune_locked()
            claimed_jobs = []
            active = distributed_worker_active_jobs(worker)
            for job_id in list(DISTRIBUTED_WORKER_QUEUE):
                if len(claimed_jobs) >= claim_limit:
                    break
                job = DISTRIBUTED_WORKER_JOBS.get(job_id)
                if not job or job.get("status") != "queued":
                    try:
                        DISTRIBUTED_WORKER_QUEUE.remove(job_id)
                    except ValueError:
                        pass
                    continue
                job_kind = clean(job.get("kind", "")).lower()
                if job_kind not in caps:
                    continue
                if lane and job_kind != lane:
                    continue
                if not distributed_worker_supports_job_payload(worker, job_kind, job.get("payload") if isinstance(job.get("payload"), dict) else {}):
                    continue
                target_worker_id = clean(job.get("target_worker_id", ""))
                target_until = float(job.get("target_exclusive_until", 0) or 0)
                if target_worker_id and target_worker_id != worker_id and time.time() < target_until:
                    continue
                failed_workers = [clean(item) for item in (job.get("failed_workers") or []) if clean(item)]
                if worker_id in failed_workers:
                    continue
                if not distributed_worker_retry_turn_allowed_locked(job, worker_id, job_kind):
                    continue
                if len(active.get(job_kind, [])) >= int(max_jobs.get(job_kind, 1) or 0):
                    continue
                preferred = clean(job.get("preferred_user", "")).lower()
                exclusive_until = float(job.get("exclusive_until", 0) or 0)
                if preferred and clean(worker.get("owner_user", "")).lower() != preferred and time.time() < exclusive_until:
                    continue
                DISTRIBUTED_WORKER_QUEUE.remove(job_id)
                now = time.time()
                job.update({"status": "claimed", "worker_id": worker_id, "claimed_at": now})
                active.setdefault(job_kind, []).append(job_id)
                distributed_worker_apply_active_jobs(worker, active)
                worker.update({"last_seen": now, "updated_at": now})
                claimed_jobs.append({
                    "job_id": job_id,
                    "kind": job.get("kind"),
                    "payload": job.get("payload") or {},
                    "timeout_seconds": job.get("timeout_seconds", 60),
                })
            if claimed_jobs:
                return {
                    "job": claimed_jobs[0],
                    "jobs": claimed_jobs,
                }
            remaining = deadline - time.time()
            if remaining <= 0:
                return {"job": None}
            DISTRIBUTED_WORKER_CONDITION.wait(timeout=min(remaining, 5.0))


def distributed_worker_submit_result(payload: dict, client_ip: str = "") -> dict:
    if not distributed_worker_authorized(None, payload):
        raise PermissionError("Worker token is invalid.")
    worker_id = clean(payload.get("worker_id", ""))
    job_id = clean(payload.get("job_id", ""))
    if not worker_id or not job_id:
        raise ValueError("Missing worker_id or job_id.")
    ok = truthy(payload.get("ok", False), False)
    now = time.time()
    with DISTRIBUTED_WORKER_CONDITION:
        worker = DISTRIBUTED_WORKERS.get(worker_id)
        job = DISTRIBUTED_WORKER_JOBS.get(job_id)
        if not job:
            return {"accepted": False, "error": "job_not_found"}
        if clean(job.get("worker_id", "")) != worker_id:
            return {"accepted": False, "error": "job_worker_mismatch"}
        if worker:
            active = distributed_worker_active_jobs(worker)
            for kind, ids in list(active.items()):
                active[kind] = [item for item in ids if item != job_id]
            distributed_worker_apply_active_jobs(worker, active)
            worker.update({"last_seen": now, "updated_at": now, "client_ip": clean(client_ip)[:80]})
        if ok:
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            job.update({"status": "done", "result": result, "finished_at": now})
            DISTRIBUTED_WORKER_STATS["completed"] += 1
            if worker:
                worker["completed"] = int(worker.get("completed", 0) or 0) + 1
        else:
            error = clean(payload.get("error", ""))[:1200] or "Worker failed."
            job_payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
            retried = False if truthy(job_payload.get("_no_retry", False), False) else distributed_worker_requeue_job_locked(job_id, worker_id, error, now)
            if retried:
                if worker:
                    worker["failed"] = int(worker.get("failed", 0) or 0) + 1
                    worker["last_error"] = error
                DISTRIBUTED_WORKER_CONDITION.notify_all()
                return {"accepted": True, "retried": True}
            job.update({"status": "failed", "error": error, "finished_at": now})
            if worker:
                worker["failed"] = int(worker.get("failed", 0) or 0) + 1
                worker["last_error"] = error
        event = job.get("event")
        if event:
            event.set()
        DISTRIBUTED_WORKER_CONDITION.notify_all()
    return {"accepted": True}


# Added 2026-07-07: stores remote worker dashboard notes/logs for server-side troubleshooting.
def distributed_worker_submit_log(payload: dict, client_ip: str = "") -> dict:
    if not distributed_worker_authorized(None, payload):
        raise PermissionError("Worker token is invalid.")
    now = time.time()
    worker_id = clean(payload.get("worker_id", ""))[:80] or "unknown"
    text = str(payload.get("message", payload.get("log", "")) or "").replace("\x00", "").strip()
    if not text:
        raise ValueError("Missing worker log message.")
    text = text[-12000:]
    with DISTRIBUTED_WORKER_CONDITION:
        worker = DISTRIBUTED_WORKERS.get(worker_id)
        row = {
            "at": now,
            "time": local_timestamp(now),
            "worker_id": worker_id,
            "name": clean(payload.get("name", worker.get("name", "") if worker else ""))[:80],
            "owner_user": clean(payload.get("owner_user", payload.get("owner", worker.get("owner_user", "") if worker else ""))).lower()[:80],
            "client_ip": clean(client_ip)[:80],
            "kind": clean(payload.get("kind", ""))[:40],
            "job_id": clean(payload.get("job_id", ""))[:80],
            "version": clean(payload.get("version", worker.get("version", "") if worker else ""))[:40],
            "error": str(payload.get("error", "") or "")[-12000:],
            "message": text,
        }
        DISTRIBUTED_WORKER_LOGS.append(row)
        del DISTRIBUTED_WORKER_LOGS[:-300]
        if worker:
            worker["last_worker_log"] = text[:500]
            worker["last_worker_log_at"] = now
            worker["last_seen"] = now
            worker["updated_at"] = now
        DISTRIBUTED_WORKER_CONDITION.notify_all()
    return {"accepted": True, "stored": len(text)}


# Added 2026-07-11: shows server-side worker routing failures in the same dashboard log panel.
def distributed_worker_add_server_log(message: str, *, kind: str = "", error: str = "", worker_id: str = "server-router") -> None:
    text = str(message or "").replace("\x00", "").strip()
    if not text:
        return
    now = time.time()
    with DISTRIBUTED_WORKER_CONDITION:
        row = {
            "at": now,
            "time": local_timestamp(now),
            "worker_id": clean(worker_id)[:80] or "server-router",
            "name": "Server router",
            "owner_user": "server",
            "client_ip": "",
            "kind": clean(kind)[:40],
            "job_id": "",
            "version": "",
            "error": str(error or "")[-12000:],
            "message": text[-12000:],
        }
        DISTRIBUTED_WORKER_LOGS.append(row)
        del DISTRIBUTED_WORKER_LOGS[:-300]
        DISTRIBUTED_WORKER_CONDITION.notify_all()


# Added 2026-07-07: prefer LAN HTTP for distributed workers so large audio payloads avoid tunnel SSL churn.
def distributed_worker_server_url(prefer_lan: bool = True) -> str:
    local_urls = [clean(item).rstrip("/") for item in (SERVER_STATE.get("server_urls", []) or []) if clean(item)]
    if prefer_lan:
        for item in local_urls:
            lowered = item.lower()
            if lowered.startswith("http://") and "127.0.0.1" not in lowered and "localhost" not in lowered:
                return item
    for item in local_urls:
        if item:
            return item
    public_url = clean(SERVER_STATE.get("public_url", "")).rstrip("/")
    if public_url:
        return public_url
    public_app_url = clean(SERVER_STATE.get("public_app_url", "")).rstrip("/")
    if public_app_url:
        return public_app_url[:-6].rstrip("/") if public_app_url.lower().endswith("/login") else public_app_url
    return "http://127.0.0.1:8877"


# Added 2026-07-07: gives authorized workers a Gemini key only at job time so keys are not copied to other PCs.
def distributed_worker_gemini_key(payload: dict) -> dict:
    if not distributed_worker_authorized(None, payload):
        raise PermissionError("Worker token is invalid.")
    keys = ordered_gemini_api_keys()
    if not keys:
        raise RuntimeError("No Gemini API key is configured on Server 2.")
    return {"api_key": keys[0]}


def distributed_worker_submit_job(kind: str, payload: dict, timeout_seconds: float = 20.0, preferred_user: str = "") -> dict | None:
    key = clean(kind).lower()
    if key not in DISTRIBUTED_WORKER_JOB_KINDS:
        return None
    submit_payload = payload if isinstance(payload, dict) else {}
    # Added 2026-07-11: long Kokoro VI audio jobs can run for minutes; explicit no-timeout jobs must not be cut off.
    requested_timeout = float(timeout_seconds or 0.0)
    no_timeout = requested_timeout <= 0 or truthy(submit_payload.get("_no_timeout", False), False)
    timeout_seconds = None if no_timeout else max(1.0, min(180.0, requested_timeout or 20.0))
    wait_budget = 180.0 if timeout_seconds is None else timeout_seconds
    event = threading.Event()
    job_id = f"{key}-{uuid.uuid4().hex[:12]}"
    now = time.time()
    preferred = clean(preferred_user).lower()
    with DISTRIBUTED_WORKER_CONDITION:
        available = distributed_worker_available_locked(key, preferred, submit_payload)
        if not available:
            DISTRIBUTED_WORKER_STATS["fallback"] += 1
            return None
        submit_voice = clean(submit_payload.get("voice", submit_payload.get("voice_key", submit_payload.get("voiceKey", "")))).lower()
        if key == "tts" and submit_voice.startswith("kokoro_vi:"):
            cuda_available = [
                worker for worker in available
                if distributed_worker_clean_features(worker.get("features", {})).get("tts_kokoro_vi_cuda")
            ]
            if cuda_available:
                available = cuda_available
            warm_available = [
                worker for worker in available
                if distributed_worker_clean_features(worker.get("features", {})).get("tts_kokoro_vi_warm")
            ]
            if warm_available:
                available = warm_available
        target_worker = distributed_worker_pick_round_robin(available, key, preferred) or available[0]
        target_worker_id = clean(target_worker.get("worker_id", ""))
        target_grace = min(DISTRIBUTED_WORKER_ASSIGN_GRACE_SECONDS, max(0.75, wait_budget * 0.15))
        has_preferred_worker = bool(preferred and any(clean(worker.get("owner_user", "")).lower() == preferred for worker in available))
        DISTRIBUTED_WORKER_STATS["created"] += 1
        DISTRIBUTED_WORKER_JOBS[job_id] = {
            "job_id": job_id,
            "kind": key,
            "payload": submit_payload,
            "status": "queued",
            "created_at": now,
            "timeout_seconds": 0 if timeout_seconds is None else timeout_seconds,
            "preferred_user": preferred,
            "exclusive_until": now + min(2.0, max(0.0, wait_budget * 0.25)) if has_preferred_worker else 0,
            "target_worker_id": target_worker_id,
            "target_exclusive_until": now + target_grace if target_worker_id else 0,
            "attempts": 1,
            "attempts_by_worker": {},
            "failed_workers": [],
            "event": event,
        }
        if target_worker_id:
            target_worker["assigned"] = int(target_worker.get("assigned", 0) or 0) + 1
            target_worker[f"assigned_{key}"] = int(target_worker.get(f"assigned_{key}", 0) or 0) + 1
            target_worker["last_assigned_at"] = now
            target_worker["updated_at"] = now
        DISTRIBUTED_WORKER_QUEUE.append(job_id)
        DISTRIBUTED_WORKER_CONDITION.notify_all()
    if not event.wait(timeout_seconds):
        with DISTRIBUTED_WORKER_CONDITION:
            job = DISTRIBUTED_WORKER_JOBS.get(job_id)
            if job and job.get("status") in {"queued", "claimed"}:
                job.update({"status": "timeout", "error": "Worker timed out.", "finished_at": time.time()})
                DISTRIBUTED_WORKER_STATS["timeout"] += 1
                assigned = clean(job.get("worker_id", ""))
                worker = DISTRIBUTED_WORKERS.get(assigned)
                if worker:
                    active = distributed_worker_active_jobs(worker)
                    for kind, ids in list(active.items()):
                        active[kind] = [item for item in ids if item != job_id]
                    distributed_worker_apply_active_jobs(worker, active)
                    worker.update({"last_error": "Worker timed out.", "updated_at": time.time()})
                try:
                    DISTRIBUTED_WORKER_QUEUE.remove(job_id)
                except ValueError:
                    pass
                DISTRIBUTED_WORKER_CONDITION.notify_all()
        return None
    with DISTRIBUTED_WORKER_LOCK:
        job = DISTRIBUTED_WORKER_JOBS.get(job_id) or {}
        if job.get("status") == "done":
            return job.get("result") if isinstance(job.get("result"), dict) else {}
        return None


def distributed_worker_dashboard_payload(local_client: bool = False) -> dict:
    now = time.time()
    with DISTRIBUTED_WORKER_LOCK:
        distributed_worker_prune_locked(now)
        configured_job_limits = distributed_worker_job_limits()
        job_limits = {
            kind: distributed_worker_effective_job_limit_locked(kind)
            for kind in DISTRIBUTED_WORKER_JOB_KINDS
        }
        workers = []
        for worker in sorted(DISTRIBUTED_WORKERS.values(), key=lambda item: (item.get("status") != "online", item.get("name", ""))):
            if worker.get("status") != "online":
                continue
            active_jobs = distributed_worker_active_jobs(worker)
            busy_kinds = [kind for kind, ids in active_jobs.items() if ids]
            workers.append({
                "worker_id": worker.get("worker_id", ""),
                "name": worker.get("name", ""),
                "capabilities": list(worker.get("capabilities") or []),
                "features": distributed_worker_clean_features(worker.get("features", {})),
                "max_jobs_by_kind": distributed_worker_clean_max_jobs(worker.get("max_jobs_by_kind", {}), worker.get("capabilities") or []),
                "active_jobs": active_jobs,
                "busy_kinds": busy_kinds,
                "owner_user": worker.get("owner_user", ""),
                "machine_name": worker.get("machine_name", ""),
                "status": worker.get("status", "offline"),
                "busy": bool(busy_kinds),
                "current_job": worker.get("current_job", ""),
                "last_seen_seconds": int(max(0.0, now - float(worker.get("last_seen", 0) or 0))),
                "completed": int(worker.get("completed", 0) or 0),
                "failed": int(worker.get("failed", 0) or 0),
                "last_error": worker.get("last_error", ""),
                "client_ip": worker.get("client_ip", "") if local_client else "",
                "version": worker.get("version", ""),
            })
        queued = sum(1 for job in DISTRIBUTED_WORKER_JOBS.values() if job.get("status") == "queued")
        claimed = sum(1 for job in DISTRIBUTED_WORKER_JOBS.values() if job.get("status") == "claimed")
        active = sum(1 for worker in workers if worker.get("status") == "online")
        stats = dict(DISTRIBUTED_WORKER_STATS)
        active_by_kind = {kind: distributed_worker_active_count(kind) for kind in DISTRIBUTED_WORKER_JOB_KINDS}
        logs = [dict(row) for row in DISTRIBUTED_WORKER_LOGS[-80:]]
    server_url = distributed_worker_server_url(prefer_lan=True)
    command = f'python future_distributed_worker_client.py --server "{server_url}" --token "{ensure_distributed_worker_token()}" --owner-user USERNAME --capabilities translate,tts,stt,gemini,phonemize --max-jobs translate=16,tts=16,stt=16,gemini=16,phonemize=16'
    return {
        "enabled": True,
        "workers": workers,
        "online": active,
        "queued": queued,
        "claimed": claimed,
        "job_limits": job_limits,
        "configured_job_limits": configured_job_limits,
        "machine_limit": distributed_worker_machine_limit(),
        "active_by_kind": active_by_kind,
        "logs": logs,
        "stats": stats,
        "token_hint": distributed_worker_public_token_hint(),
        "download_url": "/distributed-worker/download",
        "command": command if local_client else "",
        "server_url": server_url if local_client else "",
    }


# Added 2026-07-07: builds a portable worker kit that can install itself into user startup.
def distributed_worker_portable_package_files(server_url: str, token: str) -> dict[str, str | bytes]:
    client_data = DISTRIBUTED_WORKER_CLIENT_SCRIPT.read_bytes()
    config = (
        "@echo off\r\n"
        "set SERVER_URL=" + server_url + "\r\n"
        "set WORKER_TOKEN=" + token + "\r\n"
        "set FUTURE_WORKER_OWNER=\r\n"
        "set FUTURE_WORKER_ID=\r\n"
        "set FUTURE_WORKER_CAPABILITIES=translate,tts,stt,gemini,phonemize\r\n"
        "set FUTURE_WORKER_MAX_JOBS=translate=16,tts=16,stt=16,gemini=16,phonemize=16\r\n"
        "set FUTURE_WORKER_ALLOW_MULTIPLE=0\r\n"
        "set FUTURE_WORKER_POLL_SECONDS=1\r\n"
        "set FUTURE_APP_ROOT=\r\n"
        "set FUTURE_QMLEARN_ROOT=\r\n"
    )
    start_bat = (
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "cd /d \"%~dp0\"\r\n"
        "if exist worker_config.cmd call worker_config.cmd\r\n"
        "if \"%SERVER_URL%\"==\"\" set SERVER_URL=" + server_url + "\r\n"
        "if \"%WORKER_TOKEN%\"==\"\" set WORKER_TOKEN=" + token + "\r\n"
        "if \"%FUTURE_WORKER_OWNER%\"==\"\" set /p FUTURE_WORKER_OWNER=Future username for this worker: \r\n"
        "if \"%FUTURE_WORKER_ID%\"==\"\" set FUTURE_WORKER_ID=%COMPUTERNAME%-%RANDOM%%RANDOM%\r\n"
        "if \"%FUTURE_WORKER_INSTANCE_ID%\"==\"\" set FUTURE_WORKER_INSTANCE_ID=%RANDOM%%RANDOM%\r\n"
        "if \"%FUTURE_WORKER_CAPABILITIES%\"==\"\" set FUTURE_WORKER_CAPABILITIES=translate,tts,stt,gemini,phonemize\r\n"
        "if \"%FUTURE_WORKER_MAX_JOBS%\"==\"\" set FUTURE_WORKER_MAX_JOBS=translate=16,tts=16,stt=16,gemini=16,phonemize=16\r\n"
        "if \"%FUTURE_WORKER_ALLOW_MULTIPLE%\"==\"\" set FUTURE_WORKER_ALLOW_MULTIPLE=0\r\n"
        "if \"%FUTURE_WORKER_POLL_SECONDS%\"==\"\" set FUTURE_WORKER_POLL_SECONDS=1\r\n"
        "if \"%FUTURE_APP_ROOT%\"==\"\" set FUTURE_APP_ROOT=%~dp0\r\n"
        "if \"%FUTURE_QMLEARN_ROOT%\"==\"\" set FUTURE_QMLEARN_ROOT=%~dp0\r\n"
        "set FUTURE_WORKER_RUNTIME_ID=%FUTURE_WORKER_ID%-%FUTURE_WORKER_INSTANCE_ID%\r\n"
        "(\r\n"
        "  echo @echo off\r\n"
        "  echo set SERVER_URL=%SERVER_URL%\r\n"
        "  echo set WORKER_TOKEN=%WORKER_TOKEN%\r\n"
        "  echo set FUTURE_WORKER_OWNER=%FUTURE_WORKER_OWNER%\r\n"
        "  echo set FUTURE_WORKER_ID=%FUTURE_WORKER_ID%\r\n"
        "  echo set FUTURE_WORKER_CAPABILITIES=%FUTURE_WORKER_CAPABILITIES%\r\n"
        "  echo set FUTURE_WORKER_MAX_JOBS=%FUTURE_WORKER_MAX_JOBS%\r\n"
        "  echo set FUTURE_WORKER_ALLOW_MULTIPLE=%FUTURE_WORKER_ALLOW_MULTIPLE%\r\n"
        "  echo set FUTURE_WORKER_POLL_SECONDS=%FUTURE_WORKER_POLL_SECONDS%\r\n"
        "  echo set FUTURE_APP_ROOT=%FUTURE_APP_ROOT%\r\n"
        "  echo set FUTURE_QMLEARN_ROOT=%FUTURE_QMLEARN_ROOT%\r\n"
        ") > worker_config.cmd\r\n"
        "echo Future Worker connecting as %FUTURE_WORKER_OWNER% to %SERVER_URL% [%FUTURE_WORKER_RUNTIME_ID%]\r\n"
        "if exist FutureWorker.exe (\r\n"
        "  FutureWorker.exe --server \"%SERVER_URL%\" --token \"%WORKER_TOKEN%\" --owner-user \"%FUTURE_WORKER_OWNER%\" --worker-id \"%FUTURE_WORKER_RUNTIME_ID%\" --capabilities \"%FUTURE_WORKER_CAPABILITIES%\" --max-jobs \"%FUTURE_WORKER_MAX_JOBS%\" --poll-seconds \"%FUTURE_WORKER_POLL_SECONDS%\" --app-root \"%FUTURE_APP_ROOT%\"\r\n"
        ") else (\r\n"
        "  python future_distributed_worker_client.py --server \"%SERVER_URL%\" --token \"%WORKER_TOKEN%\" --owner-user \"%FUTURE_WORKER_OWNER%\" --worker-id \"%FUTURE_WORKER_RUNTIME_ID%\" --capabilities \"%FUTURE_WORKER_CAPABILITIES%\" --max-jobs \"%FUTURE_WORKER_MAX_JOBS%\" --poll-seconds \"%FUTURE_WORKER_POLL_SECONDS%\" --app-root \"%FUTURE_APP_ROOT%\"\r\n"
        ")\r\n"
        "pause\r\n"
    )
    start_hidden_vbs = (
        "Set shell = CreateObject(\"WScript.Shell\")\r\n"
        "Set fso = CreateObject(\"Scripting.FileSystemObject\")\r\n"
        "folder = fso.GetParentFolderName(WScript.ScriptFullName)\r\n"
        "shell.CurrentDirectory = folder\r\n"
        "shell.Run \"\"\"\" & folder & \"\\start_worker.bat\" & \"\"\"\", 0, False\r\n"
    )
    install_bat = (
        "@echo off\r\n"
        "setlocal EnableExtensions\r\n"
        "set TARGET=%LOCALAPPDATA%\\QM-Tech\\FutureWorker\r\n"
        "del \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\QM-Tech Future Worker.lnk\" >nul 2>nul\r\n"
        "mkdir \"%TARGET%\" >nul 2>nul\r\n"
        "robocopy \"%~dp0\" \"%TARGET%\" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul\r\n"
        "if errorlevel 8 echo Worker files copy had warnings. Check the extracted folder.\r\n"
        "if not exist \"%TARGET%\\worker_config.cmd\" copy /Y \"%~dp0worker_config.cmd\" \"%TARGET%\\\" >nul\r\n"
        "call \"%TARGET%\\worker_config.cmd\"\r\n"
        "if \"%FUTURE_WORKER_OWNER%\"==\"\" set /p FUTURE_WORKER_OWNER=Future username for this worker: \r\n"
        "if \"%FUTURE_WORKER_ID%\"==\"\" set FUTURE_WORKER_ID=%COMPUTERNAME%-%RANDOM%%RANDOM%\r\n"
        "(\r\n"
        "  echo @echo off\r\n"
        "  echo set SERVER_URL=" + server_url + "\r\n"
        "  echo set WORKER_TOKEN=" + token + "\r\n"
        "  echo set FUTURE_WORKER_OWNER=%FUTURE_WORKER_OWNER%\r\n"
        "  echo set FUTURE_WORKER_ID=%FUTURE_WORKER_ID%\r\n"
        "  echo set FUTURE_WORKER_CAPABILITIES=translate,tts,stt,gemini,phonemize\r\n"
        "  echo set FUTURE_WORKER_MAX_JOBS=translate=16,tts=16,stt=16,gemini=16,phonemize=16\r\n"
        "  echo set FUTURE_WORKER_ALLOW_MULTIPLE=0\r\n"
        "  echo set FUTURE_WORKER_POLL_SECONDS=1\r\n"
        "  echo set FUTURE_APP_ROOT=%TARGET%\r\n"
        "  echo set FUTURE_QMLEARN_ROOT=%TARGET%\r\n"
        ") > \"%TARGET%\\worker_config.cmd\"\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup') + '\\QM-Tech Future Worker.lnk'); $s.TargetPath='%TARGET%\\start_worker_hidden.vbs'; $s.WorkingDirectory='%TARGET%'; $s.IconLocation='%SystemRoot%\\System32\\shell32.dll,13'; $s.Save()\"\r\n"
        "echo Installed Future Worker to %TARGET%\r\n"
        "echo It will auto-connect when Windows starts.\r\n"
        "set /p START_NOW=Start worker now? (Y/N): \r\n"
        "if /I \"%START_NOW%\"==\"Y\" wscript \"%TARGET%\\start_worker_hidden.vbs\"\r\n"
        "pause\r\n"
    )
    uninstall_bat = (
        "@echo off\r\n"
        "setlocal\r\n"
        "del \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\QM-Tech Future Worker.lnk\" >nul 2>nul\r\n"
        "echo Future Worker startup entry removed. You can delete this folder manually if you no longer need it:\r\n"
        "echo %LOCALAPPDATA%\\QM-Tech\\FutureWorker\r\n"
        "pause\r\n"
    )
    readme = (
        "Future Distributed Worker Portable\n\n"
        "Quick install:\n"
        "1. Extract this ZIP.\n"
        "2. Run install_worker.bat once.\n"
        "3. Enter the Future username that owns this PC.\n"
        "4. Windows will auto-start this worker on login and connect it to Server 2.\n\n"
        "Important:\n"
        "- FutureWorker.exe is bundled when the server can build it with PyInstaller.\n"
        "- The models folder is bundled outside the EXE so model updates do not require rebuilding the EXE.\n"
        "- Source .py files are not included in the full package.\n"
        "- The full model bundle is large, often several GB.\n\n"
        "Files:\n"
        "- install_worker.bat: installs into %LOCALAPPDATA%\\QM-Tech\\FutureWorker and creates Startup shortcut.\n"
        "- FutureWorker.exe: worker launcher/client.\n"
        "- start_worker.bat: runs visibly for debugging, using EXE first.\n"
        "- start_worker_hidden.vbs: runs silently at Windows startup.\n"
        "- worker_config.cmd: server URL, token, username, worker id, capabilities.\n"
        "- uninstall_worker.bat: removes the Startup shortcut.\n"
    )
    return {
        "future_distributed_worker_client.py": client_data,
        "worker_config.cmd": config,
        "start_worker.bat": start_bat,
        "start_worker_hidden.vbs": start_hidden_vbs,
        "install_worker.bat": install_bat,
        "uninstall_worker.bat": uninstall_bat,
        "README.txt": readme,
    }


def distributed_worker_exe_embed_digest(server_url: str = "", token: str = "") -> str:
    raw = f"{clean(server_url)}|{clean(token)}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


# Added 2026-07-09: writes a temporary client entrypoint with internal server URL/token embedded in the EXE.
def distributed_worker_embedded_client_script(target: Path, server_url: str, token: str) -> Path:
    source = DISTRIBUTED_WORKER_CLIENT_SCRIPT.read_text(encoding="utf-8", errors="replace")
    source = re.sub(r'^DEFAULT_SERVER_URL\s*=\s*".*"$', f"DEFAULT_SERVER_URL = {clean(server_url)!r}", source, count=1, flags=re.MULTILINE)
    source = re.sub(r'^DEFAULT_WORKER_TOKEN\s*=\s*".*"$', f"DEFAULT_WORKER_TOKEN = {clean(token)!r}", source, count=1, flags=re.MULTILINE)
    if "DEFAULT_SERVER_URL =" not in source or "DEFAULT_WORKER_TOKEN =" not in source:
        raise RuntimeError("Worker client defaults were not found for embedding.")
    target.write_text(source, encoding="utf-8")
    return target


def distributed_worker_exe_is_fresh(embed_digest: str = "") -> bool:
    try:
        if not DISTRIBUTED_WORKER_EXE_PATH.is_file():
            return False
        if embed_digest:
            try:
                meta = json.loads(DISTRIBUTED_WORKER_EXE_META_PATH.read_text(encoding="utf-8", errors="replace") or "{}")
            except Exception:
                meta = {}
            if clean(meta.get("embed_digest", "")) != clean(embed_digest):
                return False
        exe_mtime = DISTRIBUTED_WORKER_EXE_PATH.stat().st_mtime
        watched = [
            ROOT / "FUTURE" / "server2",
            ROOT / "FUTURE" / "server_parts",
            PROGRAME_ROOT / "module_main",
        ]
        newest = DISTRIBUTED_WORKER_CLIENT_SCRIPT.stat().st_mtime
        for item in watched:
            _count, _size, mtime = distributed_worker_folder_signature(item)
            newest = max(newest, float(mtime or 0))
        for item in (ROOT / "FUTURE" / "__init__.py", ROOT / "FUTURE" / "server_app.py", ROOT / "future_lesson_builder_gui.py"):
            if item.is_file():
                newest = max(newest, item.stat().st_mtime)
        return exe_mtime >= newest
    except OSError:
        return False


def ensure_distributed_worker_exe(server_url: str = "", token: str = "") -> Path | None:
    server_url = clean(server_url) or distributed_worker_server_url(prefer_lan=True)
    token = clean(token) or ensure_distributed_worker_token()
    embed_digest = distributed_worker_exe_embed_digest(server_url, token)
    if distributed_worker_exe_is_fresh(embed_digest):
        return DISTRIBUTED_WORKER_EXE_PATH
    with DISTRIBUTED_WORKER_EXE_BUILD_LOCK:
        if distributed_worker_exe_is_fresh(embed_digest):
            return DISTRIBUTED_WORKER_EXE_PATH
        DISTRIBUTED_WORKER_EXE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        work_dir = DISTRIBUTED_WORKER_EXE_CACHE_DIR / "build"
        spec_dir = DISTRIBUTED_WORKER_EXE_CACHE_DIR / "spec"
        dist_dir = DISTRIBUTED_WORKER_EXE_CACHE_DIR / "dist"
        for target in (work_dir, spec_dir, dist_dir):
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            target.mkdir(parents=True, exist_ok=True)
        embedded_script = distributed_worker_embedded_client_script(work_dir / "future_distributed_worker_client_embedded.py", server_url, token)
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--name",
            "FutureWorker",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(work_dir),
            "--specpath",
            str(spec_dir),
            "--paths",
            str(ROOT),
            "--paths",
            str(PROGRAME_ROOT),
            "--hidden-import",
            "future_lesson_builder_gui",
            "--collect-submodules",
            "FUTURE.server_parts",
            "--collect-submodules",
            "FUTURE.server2",
            "--collect-submodules",
            "module_main",
            "--collect-data",
            "language_tags",
            "--collect-data",
            "langcodes",
            "--add-data",
            f"{ROOT / 'FUTURE' / 'server_parts'};FUTURE/server_parts",
            str(embedded_script),
        ]
        result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(("PyInstaller worker build failed: " + (result.stderr or result.stdout or "")).strip()[:4000])
        built = dist_dir / "FutureWorker.exe"
        if not built.is_file():
            raise RuntimeError("PyInstaller did not create FutureWorker.exe.")
        shutil.copy2(built, DISTRIBUTED_WORKER_EXE_PATH)
        try:
            atomic_write_text(
                DISTRIBUTED_WORKER_EXE_META_PATH,
                json.dumps(
                    {
                        "embed_digest": embed_digest,
                        "server_url": server_url,
                        "token_hint": distributed_worker_public_token_hint(),
                        "built_at": int(time.time()),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        return DISTRIBUTED_WORKER_EXE_PATH


def distributed_worker_folder_signature(root: Path) -> tuple[int, int, int]:
    if not root.exists():
        return (0, 0, 0)
    count = 0
    total_size = 0
    newest_mtime = 0
    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            stat = path.stat()
            count += 1
            total_size += int(stat.st_size)
            newest_mtime = max(newest_mtime, int(stat.st_mtime))
        except OSError:
            continue
    return (count, total_size, newest_mtime)


def distributed_worker_package_cache_path(server_url: str) -> Path:
    models_root = (QMLEARN_ROOT / "models").resolve()
    model_count, model_size, model_mtime = distributed_worker_folder_signature(models_root)
    app_roots = [
        ROOT / "FUTURE" / "server2",
        ROOT / "FUTURE" / "server_parts",
        PROGRAME_ROOT / "module_main",
    ]
    app_count = app_size = app_mtime = 0
    for item in app_roots:
        count, size, mtime = distributed_worker_folder_signature(item)
        app_count += count
        app_size += size
        app_mtime = max(app_mtime, mtime)
    for item in (ROOT / "FUTURE" / "__init__.py", ROOT / "FUTURE" / "server_app.py", ROOT / "future_lesson_builder_gui.py"):
        try:
            stat = item.stat()
            app_count += 1
            app_size += int(stat.st_size)
            app_mtime = max(app_mtime, int(stat.st_mtime))
        except OSError:
            continue
    token = ensure_distributed_worker_token()
    token_digest = hashlib.sha1(token.encode("utf-8", errors="ignore")).hexdigest()[:16]
    key = f"{server_url}|{token_digest}|m{model_count}-{model_size}-{model_mtime}|a{app_count}-{app_size}-{app_mtime}"
    digest = hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:16]
    DISTRIBUTED_WORKER_PACKAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return DISTRIBUTED_WORKER_PACKAGE_CACHE_DIR / f"future_distributed_worker_full_{digest}.zip"


def distributed_worker_zip_add_tree(archive: zipfile.ZipFile, source_root: Path, archive_root: str, *, compression: int) -> None:
    if not source_root.exists():
        return
    for path in source_root.rglob("*"):
        try:
            if not path.is_file():
                continue
            parts = {part.lower() for part in path.parts}
            name = path.name.lower()
            if "__pycache__" in parts or name.endswith((".pyc", ".pyo")):
                continue
            rel = path.relative_to(source_root).as_posix()
            archive.write(path, f"{archive_root.rstrip('/')}/{rel}", compress_type=compression)
        except OSError:
            continue


def distributed_worker_client_zip_path() -> Path:
    server_url = distributed_worker_server_url(prefer_lan=True)
    token = ensure_distributed_worker_token()
    worker_exe = ensure_distributed_worker_exe(server_url, token)
    if not worker_exe or not worker_exe.is_file():
        raise RuntimeError("FutureWorker.exe is not ready.")
    target = distributed_worker_package_cache_path(server_url)
    if target.is_file() and target.stat().st_size > 1024:
        return target
    temp = target.with_suffix(".tmp")
    if temp.exists():
        try:
            temp.unlink()
        except OSError:
            pass
    files = distributed_worker_portable_package_files(server_url, token)
    with zipfile.ZipFile(temp, "w", allowZip64=True) as archive:
        for name, data in files.items():
            if name == "future_distributed_worker_client.py":
                continue
            archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
        archive.write(worker_exe, "FutureWorker.exe", compress_type=zipfile.ZIP_STORED)
        distributed_worker_zip_add_tree(archive, (QMLEARN_ROOT / "models").resolve(), "models", compression=zipfile.ZIP_STORED)
    temp.replace(target)
    return target


def distributed_worker_client_zip_bytes() -> bytes:
    return distributed_worker_client_zip_path().read_bytes()


def distributed_worker_try_translate(text: str, dest: str = "en", src: str = "auto", limit: int = 2200, timeout_seconds: float = 8.0, preferred_user: str = "", force_refresh: bool = False) -> str:
    result = distributed_worker_submit_job(
        "translate",
        {"text": str(text or ""), "dest": clean(dest) or "en", "src": clean(src) or "auto", "limit": max(1, int(limit or 2200)), "force": bool(force_refresh)},
        timeout_seconds=timeout_seconds,
        preferred_user=preferred_user,
    )
    translated = lesson_task_notice_text((result or {}).get("text", ""), limit=max(1, int(limit or 2200))) if result else ""
    if translated and translation_result_is_usable(str(text or ""), translated, dest):
        return translated
    return ""


def distributed_worker_try_phonemize(text: str, voice: str = "en-US", timeout_seconds: float = 20.0, preferred_user: str = "") -> str:
    result = distributed_worker_submit_job(
        "phonemize",
        {"text": str(text or ""), "voice": clean(voice) or "en-US"},
        timeout_seconds=timeout_seconds,
        preferred_user=preferred_user,
    )
    return clean((result or {}).get("ipa", "")) if result else ""


def distributed_worker_try_tts_raw(text: str, voice_key: str, timeout_seconds: float = 45.0, preferred_user: str = "") -> dict | None:
    voice = clean(voice_key)
    payload = {"text": str(text or ""), "voice": voice}
    if voice.lower().startswith("kokoro_vi:"):
        payload["_no_timeout"] = True
        with DISTRIBUTED_WORKER_CONDITION:
            online_tts_workers = [
                worker for worker in DISTRIBUTED_WORKERS.values()
                if worker.get("status") == "online" and "tts" in (worker.get("capabilities") or [])
            ]
            kvi_ready_workers = [
                worker for worker in online_tts_workers
                if distributed_worker_clean_features(worker.get("features", {})).get("tts_kokoro_vi")
            ]
        if online_tts_workers and not kvi_ready_workers:
            names = ", ".join(clean(worker.get("name", worker.get("worker_id", ""))) for worker in online_tts_workers[:6])
            payload["_allow_unsupported_worker_once"] = True
            payload["_no_retry"] = True
            distributed_worker_add_server_log(
                f"Kokoro Vietnamese voice {voice} diagnostic assigned once. Online TTS worker(s) exist but Kokoro Vietnamese is missing: {names}.",
                kind="tts",
                error="Worker has tts capability but lacks Python 3.11 + kokoro-vietnamese/onnxruntime/soundfile/model files.",
            )
        elif not online_tts_workers:
            distributed_worker_add_server_log(
                f"Kokoro Vietnamese voice {voice} not assigned. No online TTS worker.",
                kind="tts",
                error="No online worker with tts capability.",
            )
    result = distributed_worker_submit_job(
        "tts",
        payload,
        timeout_seconds=0 if payload.get("_no_timeout") else timeout_seconds,
        preferred_user=preferred_user,
    )
    if not result:
        return None
    audio_b64 = clean(result.get("audio_base64", ""))
    if not audio_b64:
        return None
    try:
        audio_bytes = base64.b64decode(audio_b64.encode("ascii"), validate=True)
    except Exception:
        return None
    if not audio_bytes:
        return None
    return {**result, "audio_bytes": audio_bytes}


def distributed_worker_try_stt(audio_path: str, model_name: str, language: str, expected: str = "", timeout_seconds: float = 90.0, preferred_user: str = "") -> dict | None:
    try:
        data = Path(audio_path).read_bytes()
    except Exception:
        return None
    if not data or len(data) > DISTRIBUTED_WORKER_MAX_RESULT_BYTES:
        return None
    result = distributed_worker_submit_job(
        "stt",
        {
            "audio_base64": base64.b64encode(data).decode("ascii"),
            "audio_name": Path(audio_path).name,
            "model_name": clean(model_name) or "small",
            "language": clean(language) or "en",
            "expected": str(expected or ""),
        },
        timeout_seconds=timeout_seconds,
        preferred_user=preferred_user,
    )
    if not result or not clean(result.get("text", "")):
        return None
    result.setdefault("remote_worker", True)
    return result


# Added 2026-07-07: lets Gemini requests use a remote worker while the server keeps the API key.
def distributed_worker_try_gemini_model_once(model: str, body: bytes, timeout_seconds: float = 70.0, preferred_user: str = "") -> dict | None:
    try:
        body_json = bytes(body or b"").decode("utf-8", errors="strict")
    except Exception:
        return None
    result = distributed_worker_submit_job(
        "gemini",
        {
            "model": clean(model) or "gemini-1.5-flash",
            "body_json": body_json,
            "timeout_seconds": max(5.0, min(30.0, float(timeout_seconds or 20.0))),
        },
        timeout_seconds=timeout_seconds,
        preferred_user=preferred_user,
    )
    response = result.get("response") if isinstance(result, dict) else None
    return response if isinstance(response, dict) else None


def distributed_worker_gemini_available() -> bool:
    with DISTRIBUTED_WORKER_LOCK:
        return bool(distributed_worker_available_locked("gemini", "", {}))
