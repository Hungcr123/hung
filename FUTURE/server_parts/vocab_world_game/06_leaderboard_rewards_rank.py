# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def vocab_leaderboard_period_rows(period_state: dict, scope: str, bucket: str, limit: int = 3) -> list[dict]:
    safe_scope = clean(scope).lower()
    safe_bucket = clean(bucket)
    users = period_state.get("users") if isinstance(period_state.get("users"), dict) else {}
    rows = []
    for username, user_row in users.items():
        username = normalize_username(username)
        if not username or not isinstance(user_row, dict):
            continue
        if username.lower() == "testuser":
            continue
        scope_row = user_row.get(safe_scope) if isinstance(user_row.get(safe_scope), dict) else {}
        if clean(scope_row.get("bucket", "")) != safe_bucket:
            continue
        words = scope_row.get("words") if isinstance(scope_row.get("words"), dict) else {}
        score = len([key for key in words if clean(key)])
        if score <= 0:
            continue
        profile = read_user_profile(username)
        display_name = clean(profile.get("full_name", "")) or username
        gender = clean(profile.get("gender", "")).lower()
        if gender not in {"male", "female", "other"}:
            gender = "other"
        rows.append(
            {
                "username": username,
                "display_name": display_name,
                "gender": gender,
                "avatar": clean(profile.get("avatar", "")),
                "scope": safe_scope,
                "period_key": safe_bucket,
                "score": score,
            }
        )
    rows.sort(key=lambda item: (-int(item.get("score", 0) or 0), clean(item.get("display_name", "")).lower(), clean(item.get("username", "")).lower()))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    return rows[: max(1, min(10, int(limit or 3)))]


VOCAB_LEADERBOARD_RAM_CACHE: dict[tuple[str, int, str, bool], dict] = {}
VOCAB_LEADERBOARD_BUILD_INFLIGHT: dict[tuple[str, int, str, bool], dict] = {}
VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE: dict[tuple[str, int, str], dict] = {}
VOCAB_LEADERBOARD_RESPONSE_BUILD_INFLIGHT: dict[tuple[str, int, str], dict] = {}
VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK = threading.RLock()
VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION = 0
VOCAB_NODE_TOP_BATCH_LOCK = threading.RLock()
VOCAB_NODE_TOP_BATCH_EVENT = threading.Event()
VOCAB_NODE_TOP_BATCH_STATE: dict[str, object] = {
    "revision": 0,
    "boards": {},
    "worker": None,
    "worker_starts": 0,
    "build_count": 0,
    "build_failures": 0,
    "executor": None,
    "executor_workers": 0,
}
VOCAB_NODE_TOP_BATCH_QUIET_SECONDS = 1.0
VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS = 2.0
# Updated 2026-07-05: keep leaderboard payloads hot long enough for many learners opening Space_V together.
VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS = 60.0
VOCAB_LEADERBOARD_NPC_TOP_ACTIVITY_CACHE: dict[str, object] = {"at": 0.0, "payload": {}}
SPACE_LEADERBOARD_BACKFILL_CACHE: dict[str, dict] = {}
SPACE_LEADERBOARD_BACKFILL_TTL_SECONDS = 600.0
VOCAB_LEADERBOARD_REFRESH_PENDING: set[str] = set()
VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE: dict[str, object] = {"stamp": (), "state": None}
VOCAB_LEADERBOARD_DISK_STAMP_CACHE: dict[str, object] = {"source": {}, "stamp": {}}
VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_LOCK = threading.Lock()
VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE: dict[str, object] = {"version": 0, "flushed": 0, "snapshot": None, "worker": None}
VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT = threading.Event()
VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK = threading.Lock()
VOCAB_LEADERBOARD_RUNTIME_METRICS: dict[str, int] = {
    "response_seed_count": 0,
    "full_build_count": 0,
    "historical_backfill_count": 0,
    "rank_change_events": 0,
    "rank_snapshot_requests": 0,
    "rank_worker_starts": 0,
    "rank_serialize_count": 0,
    "rank_write_count": 0,
    "rank_write_failures": 0,
    "node_top_dirty_count": 0,
    "node_top_batch_build_count": 0,
    "node_top_batch_build_failures": 0,
    "node_top_refresh_requests": 0,
}


# Added 2026-07-29: bounded debounce keeps completion non-blocking while
# coalescing classroom Top mutations into one shared snapshot build.
def node_space_top_batch_status(board_type: str) -> dict:
    safe_type = normalize_space_leaderboard_type(board_type) or ""
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES:
        return {"pending": False, "revision": 0, "published_revision": 0}
    with VOCAB_NODE_TOP_BATCH_LOCK:
        boards = VOCAB_NODE_TOP_BATCH_STATE.get("boards") if isinstance(VOCAB_NODE_TOP_BATCH_STATE.get("boards"), dict) else {}
        row = boards.get(safe_type) if isinstance(boards.get(safe_type), dict) else {}
        revision = max(0, space_w_int(row.get("revision", 0), 0))
        published_revision = max(0, space_w_int(row.get("published_revision", 0), 0))
        retry_after_ms = 0
        if revision > published_revision:
            now = time.monotonic()
            first_dirty_at = float(row.get("first_dirty_at", 0.0) or now)
            last_dirty_at = float(row.get("last_dirty_at", 0.0) or first_dirty_at)
            build_at = min(
                first_dirty_at + VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS,
                last_dirty_at + VOCAB_NODE_TOP_BATCH_QUIET_SECONDS,
            )
            retry_after_ms = max(80, int(max(0.0, build_at - now) * 1000.0) + 80)
        return {
            "pending": revision > published_revision,
            "revision": revision,
            "published_revision": published_revision,
            "building_revision": max(0, space_w_int(row.get("building_revision", 0), 0)),
            "retry_after_ms": retry_after_ms,
        }


def _finish_node_space_top_batch_build(board_type: str, revision: int, built: bool) -> None:
    safe_type = normalize_space_leaderboard_type(board_type) or ""
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES:
        return
    now = time.monotonic()
    with VOCAB_NODE_TOP_BATCH_LOCK:
        boards = VOCAB_NODE_TOP_BATCH_STATE.setdefault("boards", {})
        row = boards.setdefault(safe_type, {})
        current_revision = max(0, space_w_int(row.get("revision", 0), 0))
        if built:
            row["published_revision"] = max(max(0, space_w_int(row.get("published_revision", 0), 0)), revision)
            VOCAB_NODE_TOP_BATCH_STATE["build_count"] = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("build_count", 0), 0)) + 1
            with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                VOCAB_LEADERBOARD_RUNTIME_METRICS["node_top_batch_build_count"] += 1
        else:
            row["first_dirty_at"] = float(row.get("first_dirty_at", 0.0) or 0.0) or now
            row["last_dirty_at"] = now
            VOCAB_NODE_TOP_BATCH_STATE["build_failures"] = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("build_failures", 0), 0)) + 1
            with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                VOCAB_LEADERBOARD_RUNTIME_METRICS["node_top_batch_build_failures"] += 1
        if max(0, space_w_int(row.get("building_revision", 0), 0)) == revision:
            row["building_revision"] = 0
        if current_revision > max(0, space_w_int(row.get("published_revision", 0), 0)):
            row["first_dirty_at"] = float(row.get("first_dirty_at", 0.0) or 0.0) or now
            row["last_dirty_at"] = float(row.get("last_dirty_at", 0.0) or 0.0) or now
        else:
            row["first_dirty_at"] = 0.0
            row["last_dirty_at"] = 0.0


def _node_space_top_batch_worker() -> None:
    while True:
        VOCAB_NODE_TOP_BATCH_EVENT.wait()
        while True:
            now = time.monotonic()
            due: list[tuple[str, int]] = []
            wait_seconds = None
            with VOCAB_NODE_TOP_BATCH_LOCK:
                boards = VOCAB_NODE_TOP_BATCH_STATE.get("boards") if isinstance(VOCAB_NODE_TOP_BATCH_STATE.get("boards"), dict) else {}
                for board_type, raw_row in boards.items():
                    row = raw_row if isinstance(raw_row, dict) else {}
                    revision = max(0, space_w_int(row.get("revision", 0), 0))
                    published_revision = max(0, space_w_int(row.get("published_revision", 0), 0))
                    if revision <= published_revision or max(0, space_w_int(row.get("building_revision", 0), 0)) > 0:
                        continue
                    first_dirty_at = float(row.get("first_dirty_at", 0.0) or now)
                    last_dirty_at = float(row.get("last_dirty_at", 0.0) or first_dirty_at)
                    build_at = min(
                        first_dirty_at + VOCAB_NODE_TOP_BATCH_MAX_WAIT_SECONDS,
                        last_dirty_at + VOCAB_NODE_TOP_BATCH_QUIET_SECONDS,
                    )
                    remaining = build_at - now
                    if remaining <= 0:
                        row["building_revision"] = revision
                        row["first_dirty_at"] = 0.0
                        row["last_dirty_at"] = 0.0
                        due.append((board_type, revision))
                    elif wait_seconds is None or remaining < wait_seconds:
                        wait_seconds = remaining
                VOCAB_NODE_TOP_BATCH_EVENT.clear()
            if due:
                def build_one(item: tuple[str, int]) -> None:
                    board_type, revision = item
                    built = False
                    try:
                        active_completion_count = globals().get("space_leaderboard_completion_active_count")
                        while callable(active_completion_count) and active_completion_count() > 0:
                            time.sleep(0.05)
                        result = seed_node_space_completion_response_cache(
                            "",
                            board_type,
                            load_space_leaderboard_activity_state(clone=False),
                            80,
                            shared=True,
                            batch_revision=revision,
                        )
                        built = bool(result.get("seeded"))
                    except Exception as exc:
                        try:
                            stt_debug_log("node_space_top_batch_build_failed", board_type=board_type, revision=revision, error=str(exc))
                        except Exception:
                            pass
                    _finish_node_space_top_batch_build(board_type, revision, built)
                worker_count = max(1, min(3, space_w_int(os.environ.get("FUTURE_NODE_TOP_WORKERS", "2"), 2)))
                with VOCAB_NODE_TOP_BATCH_LOCK:
                    executor = VOCAB_NODE_TOP_BATCH_STATE.get("executor")
                    executor_workers = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("executor_workers", 0), 0))
                    if executor is None or executor_workers != worker_count:
                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="node-space-top-build")
                        VOCAB_NODE_TOP_BATCH_STATE["executor"] = executor
                        VOCAB_NODE_TOP_BATCH_STATE["executor_workers"] = worker_count
                futures = [executor.submit(build_one, item) for item in due]
                for future in futures:
                    future.result()
                continue
            if wait_seconds is None:
                break
            VOCAB_NODE_TOP_BATCH_EVENT.wait(max(0.001, wait_seconds))


def mark_node_space_top_dirty(board_type: str) -> dict:
    safe_type = normalize_space_leaderboard_type(board_type) or ""
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES:
        return {"pending": False, "revision": 0, "published_revision": 0}
    now = time.monotonic()
    with VOCAB_NODE_TOP_BATCH_LOCK:
        boards = VOCAB_NODE_TOP_BATCH_STATE.setdefault("boards", {})
        row = boards.setdefault(safe_type, {})
        VOCAB_NODE_TOP_BATCH_STATE["revision"] = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("revision", 0), 0)) + 1
        revision = max(1, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("revision", 0), 1))
        if not float(row.get("first_dirty_at", 0.0) or 0.0):
            row["first_dirty_at"] = now
        row["last_dirty_at"] = now
        row["revision"] = revision
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        VOCAB_LEADERBOARD_RUNTIME_METRICS["node_top_dirty_count"] += 1
    return node_space_top_batch_status(safe_type)


def schedule_node_space_top_refresh(board_type: str) -> dict:
    # Added 2026-07-29: only a viewer asking for the dirty board wakes the
    # batch worker. Unopened Q/W/P/L/S boards keep their last snapshot at zero
    # sort/serialization cost.
    safe_type = normalize_space_leaderboard_type(board_type) or ""
    status = node_space_top_batch_status(safe_type)
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES or not status.get("pending"):
        return status
    with VOCAB_NODE_TOP_BATCH_LOCK:
        worker = VOCAB_NODE_TOP_BATCH_STATE.get("worker")
        if not isinstance(worker, threading.Thread) or not worker.is_alive():
            worker = threading.Thread(target=_node_space_top_batch_worker, daemon=True, name="node-space-top-batch")
            VOCAB_NODE_TOP_BATCH_STATE["worker"] = worker
            VOCAB_NODE_TOP_BATCH_STATE["worker_starts"] = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("worker_starts", 0), 0)) + 1
            worker.start()
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        VOCAB_LEADERBOARD_RUNTIME_METRICS["node_top_refresh_requests"] += 1
    VOCAB_NODE_TOP_BATCH_EVENT.set()
    return node_space_top_batch_status(safe_type)


# Added 2026-07-20: final per-viewer JSON bytes stay reusable until a leaderboard-visible mutation occurs.
def invalidate_vocab_leaderboard_response_cache(board_type: str = "") -> None:
    global VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION
    safe_type = normalize_space_leaderboard_type(board_type) if clean(board_type) else ""
    with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
        VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION += 1
        if not safe_type:
            VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.clear()
            return
        for key in list(VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.keys()):
            if key and key[0] == safe_type:
                VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.pop(key, None)


def vocab_leaderboard_disk_stamp(board_type: str = "space_v") -> tuple:
    safe_type = normalize_space_leaderboard_type(board_type) or "space_v"
    files = [
        VOCAB_LEADERBOARD_REWARD_FILE,
    ]
    if safe_type == "space_v":
        files.append(VOCAB_LEADERBOARD_PERIOD_FILE)
    if safe_type == "space_v":
        files.append(VOCAB_LEADERBOARD_NPC_TOP_FILE)
    stamps = []
    for path in files:
        if server_database_document_local_only(path):
            _resolved, mtime_ns, size, _sha256 = server_database_document_signature(path)
            stamps.append((str(path), mtime_ns, size))
            continue
        try:
            stat = path.stat()
            stamps.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
        except Exception:
            stamps.append((str(path), 0, 0))
    source_stamp = list(stamps)
    if safe_type == "space_v":
        source_stamp.append((str(VOCAB_LEADERBOARD_RANK_FILE), *vocab_leaderboard_rank_file_stamp()))
    else:
        source_stamp.append((str(SPACE_LEADERBOARD_ACTIVITY_FILE), *space_leaderboard_activity_file_stamp()))
        source_stamp.append((str(VOCAB_LEADERBOARD_RANK_FILE), *vocab_leaderboard_rank_file_stamp()))
    source_stamp_tuple = tuple(source_stamp)
    source_cache = VOCAB_LEADERBOARD_DISK_STAMP_CACHE.get("source") if isinstance(VOCAB_LEADERBOARD_DISK_STAMP_CACHE.get("source"), dict) else {}
    stamp_cache = VOCAB_LEADERBOARD_DISK_STAMP_CACHE.get("stamp") if isinstance(VOCAB_LEADERBOARD_DISK_STAMP_CACHE.get("stamp"), dict) else {}
    if source_cache.get(safe_type) == source_stamp_tuple and isinstance(stamp_cache.get(safe_type), tuple):
        return stamp_cache.get(safe_type)
    try:
        if safe_type == "space_v":
            rank_state = load_vocab_leaderboard_rank_state(clone=False)
            rank_boards = rank_state.get("boards") if isinstance(rank_state.get("boards"), dict) else {}
            rank_stamp = []
            for scope in ("total", "day", "week", "month"):
                board = rank_boards.get(scope) if isinstance(rank_boards.get(scope), dict) else {}
                ranks = board.get("ranks") if isinstance(board.get("ranks"), dict) else {}
                moves = board.get("moves") if isinstance(board.get("moves"), dict) else {}
                rank_stamp.append((scope, clean(board.get("updated_at", "")), len(ranks), len(moves)))
            stamps.append(("rank:space_v", tuple(rank_stamp)))
        else:
            # Updated 2026-07-06: node-space cache stamps are board-specific so one top tab does not stale every other tab.
            activity_state = load_space_leaderboard_activity_state(clone=False)
            activity_boards = activity_state.get("boards") if isinstance(activity_state.get("boards"), dict) else {}
            activity_board = activity_boards.get(safe_type) if isinstance(activity_boards.get(safe_type), dict) else {}
            users = activity_board.get("users") if isinstance(activity_board.get("users"), dict) else {}
            completed_count = 0
            for row in users.values():
                completed = row.get("completed") if isinstance(row, dict) and isinstance(row.get("completed"), dict) else {}
                completed_count += len(completed)
            stamps.append((f"activity:{safe_type}", clean(activity_board.get("updated_at", "")), len(users), completed_count))
            rank_state = load_vocab_leaderboard_rank_state(clone=False)
            rank_boards = rank_state.get("boards") if isinstance(rank_state.get("boards"), dict) else {}
            rank_stamp = []
            for scope in ("total", "day", "week", "month"):
                rank_key = f"{safe_type}:{scope}"
                board = rank_boards.get(rank_key) if isinstance(rank_boards.get(rank_key), dict) else {}
                ranks = board.get("ranks") if isinstance(board.get("ranks"), dict) else {}
                moves = board.get("moves") if isinstance(board.get("moves"), dict) else {}
                rank_stamp.append((rank_key, clean(board.get("updated_at", "")), len(ranks), len(moves)))
            stamps.append((f"rank:{safe_type}", tuple(rank_stamp)))
    except Exception:
        _path, mtime_ns, size, _sha256 = server_database_document_signature(VOCAB_LEADERBOARD_RANK_FILE)
        stamps.append((str(VOCAB_LEADERBOARD_RANK_FILE), mtime_ns, size))
    final_stamp = tuple(stamps)
    # Updated 2026-07-06: cache board-specific stamps so Top hits do not parse rank/activity JSON repeatedly.
    source_cache[safe_type] = source_stamp_tuple
    stamp_cache[safe_type] = final_stamp
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["source"] = source_cache
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["stamp"] = stamp_cache
    return final_stamp


def invalidate_vocab_leaderboard_ram_cache(board_type: str = "", schedule_refresh: bool = True) -> None:
    safe_type = normalize_space_leaderboard_type(board_type) if clean(board_type) else ""
    with VOCAB_LEADERBOARD_LOCK:
        if not safe_type:
            VOCAB_LEADERBOARD_RAM_CACHE.clear()
        else:
            for key in list(VOCAB_LEADERBOARD_RAM_CACHE.keys()):
                if key and key[0] == safe_type:
                    VOCAB_LEADERBOARD_RAM_CACHE.pop(key, None)
    invalidate_vocab_leaderboard_response_cache(safe_type)
    if schedule_refresh:
        schedule_vocab_leaderboard_cache_refresh(safe_type, delay_seconds=0.25)


# Added 2026-07-05: primes the RAM leaderboard cache during startup so first Space_V opens do not compute it.
def warm_vocab_leaderboard_cache_async(
    delay_seconds: float = 1.0,
    limit: int = 80,
    board_types: tuple[str, ...] | list[str] | None = None,
) -> None:
    def runner() -> None:
        try:
            time.sleep(max(0.0, float(delay_seconds or 0)))
            targets = tuple(board_types or ("space_w", "space_q", "space_p", "space_s", "space_l", "space_v"))
            for board_type in targets:
                try:
                    vocabulary_leaderboard(limit, double_check=False, viewer="", board_type=board_type)
                except Exception as exc:
                    try:
                        stt_debug_log("vocab_leaderboard_warm_failed", board_type=board_type, error=str(exc))
                    except Exception:
                        pass
        except Exception:
            pass

    threading.Thread(target=runner, name="future-vocab-leaderboard-warm", daemon=True).start()


# Added 2026-07-06: skips delayed refresh work when a foreground leaderboard request already rebuilt cache.
def vocab_leaderboard_cache_is_fresh(board_type: str = "space_v", limit: int = 80) -> bool:
    safe_type = normalize_space_leaderboard_type(board_type) or "space_v"
    max_rows = max(1, min(500, space_w_int(limit, 80)))
    cache_key = (safe_type, max_rows, "", False)
    disk_stamp = vocab_leaderboard_disk_stamp(safe_type)
    with VOCAB_LEADERBOARD_LOCK:
        cached = VOCAB_LEADERBOARD_RAM_CACHE.get(cache_key)
        return bool(
            isinstance(cached, dict)
            and cached.get("disk_stamp") == disk_stamp
            and time.time() - float(cached.get("at", 0) or 0) <= VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS
        )


def schedule_vocab_leaderboard_cache_refresh(board_type: str = "", delay_seconds: float = 0.25, limit: int = 80) -> None:
    safe_type = normalize_space_leaderboard_type(board_type) if clean(board_type) else ""
    pending_key = safe_type or "__all__"
    with VOCAB_LEADERBOARD_LOCK:
        if pending_key in VOCAB_LEADERBOARD_REFRESH_PENDING:
            return
        VOCAB_LEADERBOARD_REFRESH_PENDING.add(pending_key)

    def runner() -> None:
        try:
            time.sleep(max(0.0, float(delay_seconds or 0)))
            targets = [safe_type] if safe_type else list(SPACE_LEADERBOARD_TYPES)
            for target in targets:
                try:
                    if vocab_leaderboard_cache_is_fresh(target, limit):
                        continue
                    vocabulary_leaderboard(limit, double_check=False, viewer="", board_type=target)
                except Exception as exc:
                    try:
                        stt_debug_log("vocab_leaderboard_refresh_failed", board_type=target, error=str(exc))
                    except Exception:
                        pass
        finally:
            with VOCAB_LEADERBOARD_LOCK:
                VOCAB_LEADERBOARD_REFRESH_PENDING.discard(pending_key)

    threading.Thread(target=runner, name=f"future-vocab-leaderboard-refresh-{pending_key}", daemon=True).start()


# Added 2026-07-05: keeps the heavy leaderboard cache shared while adding per-viewer social flags cheaply.
def vocab_leaderboard_payload_for_viewer(payload: dict, viewer: str = "") -> dict:
    source = payload if isinstance(payload, dict) else {}
    result = dict(source)
    source_boards = source.get("boards") if isinstance(source.get("boards"), dict) else {}
    result["boards"] = {
        scope: [dict(row) for row in rows if isinstance(row, dict)]
        for scope, rows in source_boards.items()
        if isinstance(rows, list)
    }
    result["users"] = result["boards"].get("total", [])
    viewer_key = normalize_username(viewer)
    if not viewer_key:
        return result
    boards = result.get("boards") if isinstance(result.get("boards"), dict) else {}
    result["boards"] = attach_vocab_leaderboard_social(boards, viewer_key, result.get("reaction_options") if isinstance(result.get("reaction_options"), list) else None)
    result["users"] = result["boards"].get("total", [])
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        social_state = load_vocab_leaderboard_social_state()
    result["my_statuses"] = vocab_leaderboard_my_statuses(viewer_key, social_state)
    return result


def clone_vocab_leaderboard_payload(payload: dict) -> dict:
    try:
        import copy
        return copy.deepcopy(payload if isinstance(payload, dict) else {})
    except Exception:
        return dict(payload or {})


# Added 2026-07-30: shared Top candidates must be authenticated learner names,
# never Server Data infrastructure folders or disposable test identities.
def vocab_leaderboard_reserved_usernames() -> set[str]:
    blocked = {"common", "sound", "structure", "picture", "server_log", "npc_top", "server", "server2"}
    reserved_reader = globals().get("reserved_user_data_names")
    if callable(reserved_reader):
        blocked.update(clean(item).lower() for item in reserved_reader())
    return blocked


def vocab_leaderboard_user_allowed(username: str, include_test_users: bool = False) -> bool:
    normalized = normalize_username(username)
    return bool(
        normalized
        and normalized not in vocab_leaderboard_reserved_usernames()
        and (include_test_users or not server_database_is_test_user(normalized))
    )


def vocab_leaderboard_real_usernames(board_type: str = "", limit: int = 0) -> list[str]:
    rows = {
        normalize_username(item)
        for item in list_registered_users()
        if vocab_leaderboard_user_allowed(item)
    }
    seed = f"{normalize_space_leaderboard_type(board_type) or 'space_v'}|{time.strftime('%Y-%m-%d')}"
    ordered = sorted(rows, key=lambda username: hashlib.sha256(f"{seed}|{username}".encode("utf-8", errors="ignore")).hexdigest())
    return ordered[: max(0, int(limit or 0))] if limit else ordered


# Added 2026-07-29: give the automatic post-completion Top a correct compact
# board while the full startup cache is still warming. This avoids making the
# first learner rebuild chat/social/profile decoration on the request thread.
def seed_node_space_completion_response_cache(
    username: str,
    board_type: str,
    activity_state: dict,
    limit: int = 80,
    shared: bool = False,
    expected_generation: int | None = None,
    batch_revision: int = 0,
) -> dict:
    safe_type = normalize_space_leaderboard_type(board_type) or ""
    viewer_key = normalize_username(username)
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES or (not viewer_key and not shared) or not isinstance(activity_state, dict):
        return {"seeded": False}
    max_rows = max(1, min(500, space_w_int(limit, 100)))
    boards_state = activity_state.get("boards") if isinstance(activity_state.get("boards"), dict) else {}
    board_state = boards_state.get(safe_type) if isinstance(boards_state.get(safe_type), dict) else {}
    users_state = board_state.get("users") if isinstance(board_state.get("users"), dict) else {}
    candidate_usernames = list(users_state)
    real_user_candidates = vocab_leaderboard_real_usernames(safe_type)
    real_usernames = set(real_user_candidates)
    candidate_usernames.extend(real_user_candidates[:max_rows * 2])
    include_test_users = str(os.environ.get("FUTURE_ISOLATED_LOAD_TEST", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    base_rows = []
    seen_usernames = set()
    for raw_username in candidate_usernames:
        row_username = normalize_username(raw_username)
        if row_username in seen_usernames or not row_username:
            continue
        seen_usernames.add(row_username)
        if not vocab_leaderboard_user_allowed(row_username, include_test_users) and row_username != viewer_key:
            continue
        counts = space_leaderboard_period_counts_for_user(row_username, safe_type, activity_state)
        # Added 2026-07-30: the post-completion seed must carry the same
        # profile decoration as the full board, otherwise node-space cards
        # lose avatars/names until the slower refresh replaces the snapshot.
        profile = read_user_profile(row_username)
        display_name = clean(profile.get("full_name", "")) or row_username
        gender = clean(profile.get("gender", "")).lower()
        if gender not in {"male", "female", "other"}:
            gender = "other"
        base_rows.append({
            "username": row_username,
            "display_name": display_name,
            "gender": gender,
            "avatar": clean(profile.get("avatar", "")),
            "total_words": max(0, space_w_int(counts.get("total", 0), 0)),
            "today_words": max(0, space_w_int(counts.get("day", 0), 0)),
            "week_words": max(0, space_w_int(counts.get("week", 0), 0)),
            "month_words": max(0, space_w_int(counts.get("month", 0), 0)),
            "board_type": safe_type,
            "score_unit": "points",
            "updated_at": clean(board_state.get("updated_at", "")),
            "npc": False,
        })
    score_fields = {"total": "total_words", "day": "today_words", "week": "week_words", "month": "month_words"}
    public_boards = {}
    now_stamp = utc_timestamp()
    for scope, score_field in score_fields.items():
        rows = [{**row, "scope": scope, "score": int(row.get(score_field, 0) or 0)} for row in base_rows if int(row.get(score_field, 0) or 0) > 0]
        rows.sort(key=lambda item: (-int(item.get("score", 0) or 0), clean(item.get("display_name", "")).lower(), clean(item.get("username", "")).lower()))
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
            if normalize_username(row.get("username", "")) == viewer_key:
                row["rank_move"] = {"direction": "new", "delta": 0, "previous_rank": 0, "current_rank": rank, "changed_at": now_stamp}
        if len(rows) < max_rows:
            used = {normalize_username(item.get("username", "")) for item in rows}
            seed = f"{scope}|{vocab_period_bucket(scope) or time.strftime('%Y-%m-%d')}"
            fillers = [
                row for row in base_rows
                if normalize_username(row.get("username", "")) and normalize_username(row.get("username", "")) not in used
            ]
            fillers.sort(key=lambda item: hashlib.sha256(
                f"{seed}|{normalize_username(item.get('username', ''))}".encode("utf-8", errors="ignore")
            ).hexdigest())
            for filler in fillers[: max(0, max_rows - len(rows))]:
                rows.append({
                    **filler,
                    "scope": scope,
                    "score": 0,
                    "rank": len(rows) + 1,
                    "placeholder": True,
                    "rank_move": {"direction": "preview", "delta": 0, "previous_rank": 0, "current_rank": len(rows) + 1},
                })
        public_boards[scope] = rows[:max_rows]
    reaction_options = normalize_leaderboard_reaction_options(DEFAULT_SETTINGS.get("leaderboard_reactions"))
    payload = {
        "ok": True,
        "updated_at": now_stamp,
        "limit": max_rows,
        "scope": "total",
        "board_type": safe_type,
        "board_types": list(SPACE_LEADERBOARD_TYPES),
        "score_unit": "points",
        "double_checked": False,
        "period_reconcile": {},
        "space_backfill": {"cached": True, "fast_completion_seed": True, "activity_state": {"ready": True, "users": len(base_rows)}},
        "npc_top": {},
        "boards": public_boards,
        "users": public_boards.get("total", []),
        # World chat/viewers are global across all Space boards. Keep them in
        # the compact seed so switching Q/W/P/L/S does not create a blank chat.
        "viewers": vocab_leaderboard_viewer_rows(80),
        "world_chat": vocab_leaderboard_chat_rows(100),
        "rewards": normalize_leaderboard_rewards(DEFAULT_SETTINGS.get("leaderboard_rewards")),
        "my_statuses": {},
        "reaction_options": reaction_options,
        "reaction_keys": [item["key"] for item in reaction_options],
    }
    data = json_bytes(payload)
    cache_key = (safe_type, max_rows, "" if shared else viewer_key.lower())
    with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
        if expected_generation is not None and expected_generation != VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION:
            return {"seeded": False, "stale_generation": True}
        VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE[cache_key] = {
            "payload": payload,
            "bytes": data,
            "etag": f'"vocab-top-{hashlib.sha1(data).hexdigest()}"',
            "cache_hit": False,
            "at": time.time(),
            "expires_at": time.time() + 15.0,
            "fast_completion_seed": True,
            "revision": max(0, space_w_int(batch_revision, 0)),
        }
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        VOCAB_LEADERBOARD_RUNTIME_METRICS["response_seed_count"] += 1
    return {"seeded": True, "users": len(base_rows), "response_bytes": len(data)}


# Added 2026-07-05: refreshes one learner inside hot leaderboard payloads without rebuilding every user.
def update_vocab_leaderboard_cache_for_user(
    username: str,
    board_type: str = "space_v",
    vocabulary_result: dict | None = None,
    period_state: dict | None = None,
) -> dict:
    safe_type = normalize_space_leaderboard_type(board_type) or "space_v"
    username = normalize_username(username)
    if not username or username.lower() == "testuser":
        return {"updated": False, "reason": "unsupported", "user": username, "board_type": safe_type}
    # Updated 2026-07-29: completion only invalidates derived Top bytes. The
    # first GET rebuilds one shared compact payload under singleflight after
    # the durable activity delta is committed and the per-user lock is free.
    if safe_type in SPACE_LEADERBOARD_NODE_TYPES:
        with VOCAB_LEADERBOARD_LOCK:
            for cache_key in list(VOCAB_LEADERBOARD_RAM_CACHE.keys()):
                if cache_key and cache_key[0] == safe_type:
                    VOCAB_LEADERBOARD_RAM_CACHE.pop(cache_key, None)
        # Test-only comparator for proving the cost of invalidating unrelated boards.
        if os.environ.get("FUTURE_TEST_NODE_TOP_GLOBAL_DIRTY") == "1":
            batch_status = {}
            for node_type in SPACE_LEADERBOARD_NODE_TYPES:
                status = mark_node_space_top_dirty(node_type)
                if node_type == safe_type:
                    batch_status = status
        else:
            batch_status = mark_node_space_top_dirty(safe_type)
        return {
            "updated": True,
            "cache_entries": 0,
            "invalidated": True,
            "user": username,
            "board_type": safe_type,
            "fast_response_seed": {"seeded": False, "deferred": True, **batch_status},
        }
    # Added 2026-07-29: reuse the already-rendered Top row before querying the profile store.
    cached_user_row = None
    with VOCAB_LEADERBOARD_LOCK:
        for cached in VOCAB_LEADERBOARD_RAM_CACHE.values():
            payload = cached.get("payload") if isinstance(cached, dict) else None
            boards = payload.get("boards") if isinstance(payload, dict) and isinstance(payload.get("boards"), dict) else {}
            for rows in boards.values():
                if not isinstance(rows, list):
                    continue
                match = next((row for row in rows if isinstance(row, dict) and normalize_username(row.get("username", "")) == username), None)
                if match:
                    cached_user_row = dict(match)
                    break
            if cached_user_row:
                break
    profile = {
        "full_name": cached_user_row.get("display_name", "") if cached_user_row else "",
        "gender": cached_user_row.get("gender", "") if cached_user_row else "",
        "avatar": cached_user_row.get("avatar", "") if cached_user_row else "",
    }
    if not cached_user_row:
        profile = read_user_profile(username)
    display_name = clean(profile.get("full_name", "")) or username
    gender = clean(profile.get("gender", "")).lower()
    if gender not in {"male", "female", "other"}:
        gender = "other"
    if safe_type == "space_v":
        total_words = -1
        if isinstance(vocabulary_result, dict):
            total_words = max(
                total_words,
                space_w_int(vocabulary_result.get("total_words", -1), -1),
                space_w_int(vocabulary_result.get("verified_total_words", -1), -1),
            )
        registry_updated_at = ""
        if total_words < 0:
            registry = read_user_vocab_registry_snapshot(username)
            words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
            total_words = len([key for key, item in words.items() if key and isinstance(item, dict)])
            registry_updated_at = clean(registry.get("updated_at", ""))
        if not registry_updated_at:
            registry_updated_at = utc_timestamp()
        counts = vocab_leaderboard_period_counts_for_user(username, period_state)
        score_unit = "words"
    elif safe_type in SPACE_LEADERBOARD_NODE_TYPES:
        # Updated 2026-07-06: node-space completions patch hot top rows instead of forcing a full board rebuild.
        space_activity_state = period_state if isinstance(period_state, dict) else load_space_leaderboard_activity_state()
        supplied_counts = vocabulary_result.get("leaderboard_counts") if isinstance(vocabulary_result, dict) else None
        counts = supplied_counts if isinstance(supplied_counts, dict) else space_leaderboard_period_counts_for_user(username, safe_type, space_activity_state)
        total_words = max(0, space_w_int(counts.get("total", 0), 0))
        registry_updated_at = clean((vocabulary_result or {}).get("leaderboard_updated_at", "")) or clean(
            (((space_activity_state.get("boards") if isinstance(space_activity_state.get("boards"), dict) else {}).get(safe_type) or {}).get("updated_at", ""))
        ) or utc_timestamp()
        score_unit = "points"
    else:
        return {"updated": False, "reason": "unsupported", "user": username, "board_type": safe_type}
    base_row = {
        "username": username,
        "display_name": display_name,
        "gender": gender,
        "avatar": clean(profile.get("avatar", "")),
        "total_words": max(0, int(total_words or 0)),
        "today_words": max(0, space_w_int(counts.get("day", 0), 0)),
        "week_words": max(0, space_w_int(counts.get("week", 0), 0)),
        "month_words": max(0, space_w_int(counts.get("month", 0), 0)),
        "board_type": safe_type,
        "score_unit": score_unit,
        "updated_at": registry_updated_at,
        "npc": False,
    }
    score_fields = {"total": "total_words", "day": "today_words", "week": "week_words", "month": "month_words"}
    touched = 0
    with VOCAB_LEADERBOARD_LOCK:
        for cache_key, cached in list(VOCAB_LEADERBOARD_RAM_CACHE.items()):
            if not cache_key or cache_key[0] != safe_type or not isinstance(cached, dict):
                continue
            payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else {}
            boards = payload.get("boards") if isinstance(payload.get("boards"), dict) else {}
            if not boards:
                continue
            max_rows = max(1, min(500, space_w_int(payload.get("limit", cache_key[1] if len(cache_key) > 1 else 80), 80)))
            for scope, score_field in score_fields.items():
                previous_rows = boards.get(scope) if isinstance(boards.get(scope), list) else []
                previous_by_user = {
                    normalize_username(row.get("username", "")): dict(row)
                    for row in previous_rows
                    if isinstance(row, dict) and normalize_username(row.get("username", ""))
                }
                previous_rank = max(0, space_w_int((previous_by_user.get(username) or {}).get("rank", 0), 0))
                rows = [
                    dict(row)
                    for row in previous_rows
                    if isinstance(row, dict) and normalize_username(row.get("username", "")) != username and not bool(row.get("placeholder"))
                ]
                score = max(0, space_w_int(base_row.get(score_field, 0), 0))
                if score > 0:
                    rows.append({**base_row, "scope": scope, "score": score})
                rows.sort(key=lambda item: (-int(item.get("score", 0) or 0), clean(item.get("display_name", "")).lower(), clean(item.get("username", "")).lower()))
                rows = rows[:max_rows]
                for index, row in enumerate(rows, 1):
                    current_user = normalize_username(row.get("username", ""))
                    old_rank = previous_rank if current_user == username else max(0, space_w_int((previous_by_user.get(current_user) or {}).get("rank", 0), 0))
                    row["rank"] = index
                    if old_rank and old_rank != index:
                        delta = old_rank - index
                        row["rank_move"] = {
                            "direction": "up" if delta > 0 else "down",
                            "delta": abs(delta),
                            "previous_rank": old_rank,
                            "current_rank": index,
                            "changed_at": utc_timestamp(),
                        }
                    elif current_user == username and not old_rank:
                        row["rank_move"] = {
                            "direction": "new",
                            "delta": 0,
                            "previous_rank": 0,
                            "current_rank": index,
                            "changed_at": utc_timestamp(),
                        }
                    elif isinstance((previous_by_user.get(current_user) or {}).get("rank_move"), dict):
                        row["rank_move"] = (previous_by_user.get(current_user) or {}).get("rank_move")
                if len(rows) < max_rows:
                    used = {normalize_username(item.get("username", "")) for item in rows}
                    placeholders = [
                        dict(row)
                        for row in previous_rows
                        if isinstance(row, dict)
                        and bool(row.get("placeholder"))
                        and normalize_username(row.get("username", "")) not in used
                        and normalize_username(row.get("username", "")) != username
                    ]
                    for filler in placeholders[: max(0, max_rows - len(rows))]:
                        filler["rank"] = len(rows) + 1
                        filler["scope"] = scope
                        rows.append(filler)
                boards[scope] = rows
            payload["boards"] = boards
            payload["users"] = boards.get("total", [])
            payload["updated_at"] = utc_timestamp()
            cached["payload"] = payload
            cached["at"] = time.time()
            touched += 1
    # Added 2026-07-28: a fresh completion must never keep serving stale Top JSON
    # just because the serialized bytes cache outlived the RAM payload entry.
    invalidate_vocab_leaderboard_response_cache(safe_type)
    fast_response_seed = {}
    if touched <= 0 and safe_type in SPACE_LEADERBOARD_NODE_TYPES:
        fast_response_seed = seed_node_space_completion_response_cache(username, safe_type, space_activity_state)
    if touched <= 0 and safe_type == "space_v":
        schedule_vocab_leaderboard_cache_refresh(safe_type, delay_seconds=0.6)
    return {"updated": touched > 0, "cache_entries": touched, "user": username, "board_type": safe_type, "fast_response_seed": fast_response_seed}


def settle_closed_vocab_leaderboard_periods(period_state: dict | None = None, now_epoch: float | None = None) -> dict:
    now_value = time.time() if now_epoch is None else float(now_epoch or time.time())
    state = period_state if isinstance(period_state, dict) else load_vocab_leaderboard_period_state()
    users = state.setdefault("users", {})
    current_buckets = {scope: vocab_period_bucket(scope, now_value) for scope in ("day", "week", "month")}
    stale_buckets: dict[str, set[str]] = {"day": set(), "week": set(), "month": set()}
    for user_row in users.values():
        if not isinstance(user_row, dict):
            continue
        for scope in ("day", "week", "month"):
            scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
            bucket = clean(scope_row.get("bucket", ""))
            if bucket and bucket != current_buckets[scope]:
                stale_buckets[scope].add(bucket)
    stale_buckets = {scope: buckets for scope, buckets in stale_buckets.items() if buckets}
    if not stale_buckets:
        return {"settled": 0, "periods": [], "period_state_changed": False}

    periods = []
    reward_changed = False
    with VOCAB_LEADERBOARD_REWARD_LOCK:
        reward_state = load_vocab_leaderboard_reward_state()
        closed = reward_state.setdefault("closed", {})
        for scope, buckets in stale_buckets.items():
            scope_closed = closed.setdefault(scope, {})
            for bucket in sorted(buckets):
                period_key = clean(bucket)
                if not period_key:
                    continue
                if not isinstance(scope_closed.get(period_key), dict):
                    rows = vocab_leaderboard_period_rows(state, scope, period_key, limit=3)
                    if rows:
                        scope_closed[period_key] = {
                            "scope": scope,
                            "period_key": period_key,
                            "closed_at": utc_timestamp(),
                            "rows": rows,
                            "claimed": {},
                        }
                        reward_changed = True
                        periods.append({"scope": scope, "period_key": period_key, "winners": len(rows)})
                else:
                    periods.append({"scope": scope, "period_key": period_key, "winners": len(scope_closed[period_key].get("rows", []) if isinstance(scope_closed[period_key].get("rows"), list) else [])})
        if reward_changed:
            write_vocab_leaderboard_reward_state(reward_state)

    removed_rows = 0
    for user_row in users.values():
        if not isinstance(user_row, dict):
            continue
        for scope, buckets in stale_buckets.items():
            scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
            if clean(scope_row.get("bucket", "")) in buckets:
                user_row.pop(scope, None)
                removed_rows += 1
    state["updated_at"] = utc_timestamp()
    return {"settled": len(periods), "periods": periods, "period_state_changed": bool(removed_rows)}


LEADERBOARD_REWARD_ITEM_DEFS = {
    "rare": {
        "id": "leaderboard_crystal_rare",
        "name": "Golden Axe",
        "use": "Awarded from leaderboard ranks for strong first-time vocabulary progress.",
    },
    "easy": {
        "id": "leaderboard_crystal_easy",
        "name": "Silver Axe",
        "use": "Awarded from leaderboard ranks for steady vocabulary review progress.",
    },
    "space_q": {
        "id": "space_q_spellbook_gold",
        "name": "Golden Magic Book",
        "use": "Awarded from Space_Q leaderboard ranks.",
    },
    "space_q_silver": {
        "id": "space_q_spellbook_silver",
        "name": "Silver Magic Book",
        "use": "Awarded from Space_Q leaderboard ranks for review progress.",
    },
    "space_p": {
        "id": "space_p_bow_gold",
        "name": "Golden Magic Bow",
        "use": "Awarded from Space_P leaderboard ranks.",
    },
    "space_p_silver": {
        "id": "space_p_bow_silver",
        "name": "Silver Magic Bow",
        "use": "Awarded from Space_P leaderboard ranks for review progress.",
    },
    "space_s": {
        "id": "space_s_sax_gold",
        "name": "Golden Devil Wings",
        "use": "Awarded from Space_S leaderboard ranks.",
    },
    "space_s_silver": {
        "id": "space_s_sax_silver",
        "name": "Silver Devil Wings",
        "use": "Awarded from Space_S leaderboard ranks for review progress.",
    },
    "space_w": {
        "id": "space_w_cup_gold",
        "name": "Golden Mastery Cup",
        "use": "Awarded from Space_W leaderboard ranks.",
    },
    "space_w_silver": {
        "id": "space_w_cup_iron",
        "name": "Silver Practice Cup",
        "use": "Awarded from Space_W leaderboard ranks for review progress.",
    },
    "space_l": {
        "id": "space_l_sword_gold",
        "name": "Golden Great Sword",
        "use": "Awarded from Space_L leaderboard ranks.",
    },
    "space_l_silver": {
        "id": "space_l_sword_silver",
        "name": "Silver Great Sword",
        "use": "Awarded from Space_L leaderboard ranks for review progress.",
    },
    "space_v": {
        "id": "leaderboard_space_v_crystal",
        "name": "Golden Axe",
        "use": "A leaderboard reward crystal for vocabulary missions.",
    },
}


def leaderboard_badge_item(scope: str, title: str) -> dict:
    safe_scope = clean(scope).lower() or "leaderboard"
    safe_title = clean(title) or f"{safe_scope.title()} Champion"
    return {
        "id": f"leaderboard_badge_{safe_scope}",
        "name": f"{safe_title} Badge",
        "use": f"Proof of a rank #1 finish in the {safe_title} leaderboard period.",
    }


def leaderboard_reward_entries(scope: str, rank: int, rewards: dict) -> list[dict]:
    safe_scope = clean(scope).lower()
    scope_reward = rewards.get(safe_scope) if isinstance(rewards.get(safe_scope), dict) else {}
    ranks = scope_reward.get("ranks") if isinstance(scope_reward.get("ranks"), dict) else {}
    rank_reward = ranks.get(str(rank)) if isinstance(ranks.get(str(rank)), dict) else {}
    entries = []
    if bool(rank_reward.get("badge")) and rank == 1:
        entries.append({"kind": "badge", "quantity": 1, "item": leaderboard_badge_item(safe_scope, clean(scope_reward.get("title", "")))})
    for kind, item in LEADERBOARD_REWARD_ITEM_DEFS.items():
        quantity = max(0, min(9999, space_w_int(rank_reward.get(kind, 0), 0)))
        if quantity > 0:
            entries.append({"kind": kind, "quantity": quantity, "item": item})
    return entries


def claim_pending_vocab_leaderboard_rewards(username: str, force_settle: bool = True) -> dict:
    username = normalize_username(username)
    if not username:
        return {"claims": [], "items": []}
    settled = {"settled": 0, "periods": []}
    if force_settle:
        with VOCAB_LEADERBOARD_PERIOD_LOCK:
            period_state = load_vocab_leaderboard_period_state()
            settled = settle_closed_vocab_leaderboard_periods(period_state)
            if settled.get("settled") or settled.get("period_state_changed"):
                write_vocab_leaderboard_period_state(period_state)

    rewards = None
    claims = []
    awarded_items = []
    pending_awards = []
    pending_item_records = []
    with VOCAB_LEADERBOARD_REWARD_LOCK:
        reward_state = load_vocab_leaderboard_reward_state(clone=False)
        closed = reward_state.setdefault("closed", {})
        changed = False
        for scope in ("day", "week", "month"):
            scope_closed = closed.get(scope) if isinstance(closed.get(scope), dict) else {}
            for period_key in sorted(scope_closed.keys()):
                period = scope_closed.get(period_key) if isinstance(scope_closed.get(period_key), dict) else {}
                rows = period.get("rows") if isinstance(period.get("rows"), list) else []
                winner = None
                for row in rows:
                    if isinstance(row, dict) and normalize_username(row.get("username", "")) == username:
                        winner = row
                        break
                if not winner:
                    continue
                rank = max(0, space_w_int(winner.get("rank", 0), 0))
                if rank not in (1, 2, 3):
                    continue
                claimed = period.setdefault("claimed", {})
                if clean(claimed.get(username, "")):
                    continue
                if rewards is None:
                    rewards = normalize_leaderboard_rewards(load_server_settings().get("leaderboard_rewards", DEFAULT_SETTINGS["leaderboard_rewards"]))
                entries = leaderboard_reward_entries(scope, rank, rewards)
                period_claim = {
                    "scope": scope,
                    "period_key": clean(period.get("period_key", period_key)),
                    "rank": rank,
                    "score": max(0, space_w_int(winner.get("score", 0), 0)),
                    "items": [],
                }
                for entry in entries:
                    item = entry.get("item") if isinstance(entry.get("item"), dict) else {}
                    quantity = max(1, min(9999, space_w_int(entry.get("quantity", 1), 1)))
                    event_id = f"leaderboard:{scope}:{period_key}:rank{rank}:{username}:{clean_inventory_item_id(item.get('id', entry.get('kind', 'reward')))}"
                    item_record = {
                        "kind": clean(entry.get("kind", "")),
                        "id": clean(item.get("id", "")),
                        "name": clean(item.get("name", "")),
                        "quantity": quantity,
                        "awarded": False,
                    }
                    period_claim["items"].append(item_record)
                    awarded_items.append(item_record)
                    pending_item_records.append(item_record)
                    pending_awards.append({"item": item, "quantity": quantity, "event_id": event_id})
                claimed[username] = utc_timestamp()
                changed = True
                claims.append(period_claim)
        inventory_payload = {}
        if pending_awards:
            # Added 2026-07-06: claim all leaderboard reward inventory entries in one RAM-backed batch.
            batch_result = award_inventory_items(username, pending_awards)
            inventory_payload = batch_result.get("inventory", {}) if isinstance(batch_result.get("inventory"), dict) else {}
            batch_awards = batch_result.get("awards") if isinstance(batch_result.get("awards"), list) else []
            for item_record, result in zip(pending_item_records, batch_awards):
                result_item = result.get("item") if isinstance(result.get("item"), dict) else {}
                item_record["id"] = clean(result_item.get("id", item_record.get("id", "")))
                item_record["name"] = clean(result_item.get("name", item_record.get("name", "")))
                item_record["awarded"] = bool(result.get("awarded", False))
        if changed:
            reward_state.setdefault("claims", {}).setdefault(username, [])
            existing = reward_state["claims"].get(username) if isinstance(reward_state["claims"].get(username), list) else []
            reward_state["claims"][username] = (existing + claims)[-1000:]
            write_vocab_leaderboard_reward_state(reward_state)

    return {
        "claims": claims,
        "items": awarded_items,
        "inventory": inventory_payload,
        "settled": settled,
        "claimed_at": utc_timestamp() if claims else "",
    }


# Added 2026-07-07: skips reward-claim scans for users absent from closed top periods.
def vocab_leaderboard_reward_candidate_users() -> set[str]:
    signature = vocab_leaderboard_reward_file_signature()
    cached = VOCAB_LEADERBOARD_REWARD_CANDIDATE_CACHE
    if cached.get("signature") == signature:
        return set(cached.get("users") or set())
    reward_state = load_vocab_leaderboard_reward_state(clone=False)
    closed = reward_state.get("closed") if isinstance(reward_state.get("closed"), dict) else {}
    users: set[str] = set()
    for scope in ("day", "week", "month"):
        scope_closed = closed.get(scope) if isinstance(closed.get(scope), dict) else {}
        for period in scope_closed.values():
            if not isinstance(period, dict):
                continue
            claimed = period.get("claimed") if isinstance(period.get("claimed"), dict) else {}
            rows = period.get("rows") if isinstance(period.get("rows"), list) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                username = normalize_username(row.get("username", ""))
                if not username or clean(claimed.get(username, "")):
                    continue
                rank = max(0, space_w_int(row.get("rank", 0), 0))
                if rank in (1, 2, 3):
                    users.add(username)
    cached["signature"] = signature
    cached["users"] = set(users)
    return users


def maybe_claim_pending_vocab_leaderboard_rewards(username: str, force: bool = False) -> dict:
    username = normalize_username(username)
    if not username:
        return {"claims": [], "items": []}
    now = time.time()
    marker = "|".join(vocab_period_bucket(scope, now) for scope in ("day", "week", "month"))
    cached = VOCAB_LEADERBOARD_REWARD_CHECK_CACHE.get(username) if isinstance(VOCAB_LEADERBOARD_REWARD_CHECK_CACHE.get(username), dict) else {}
    if not force and clean(cached.get("marker", "")) == marker and now - float(cached.get("at", 0) or 0) < 300:
        return {"claims": [], "items": [], "skipped": "recent"}
    if not force:
        with VOCAB_LEADERBOARD_REWARD_LOCK:
            candidates = vocab_leaderboard_reward_candidate_users()
        if username not in candidates:
            VOCAB_LEADERBOARD_REWARD_CHECK_CACHE[username] = {"marker": marker, "at": now}
            return {"claims": [], "items": [], "skipped": "no_pending"}
    result = claim_pending_vocab_leaderboard_rewards(username, force_settle=True)
    VOCAB_LEADERBOARD_REWARD_CHECK_CACHE[username] = {"marker": marker, "at": now}
    return result


LOGIN_REWARD_CLAIM_QUEUE_LOCK = threading.RLock()
LOGIN_REWARD_CLAIM_QUEUE_STATE = {"running": False, "users": set()}


# Added 2026-07-08: coalesces login reward checks so 100 simultaneous logins do not spawn 100 threads.
def schedule_login_reward_claim(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"scheduled": False, "reason": "missing_user"}

    def worker() -> None:
        while True:
            with LOGIN_REWARD_CLAIM_QUEUE_LOCK:
                pending_users = LOGIN_REWARD_CLAIM_QUEUE_STATE.get("users")
                users = sorted(pending_users) if isinstance(pending_users, set) else []
                LOGIN_REWARD_CLAIM_QUEUE_STATE["users"] = set()
            if not users:
                with LOGIN_REWARD_CLAIM_QUEUE_LOCK:
                    pending_users = LOGIN_REWARD_CLAIM_QUEUE_STATE.get("users")
                    if isinstance(pending_users, set) and pending_users:
                        continue
                    LOGIN_REWARD_CLAIM_QUEUE_STATE["running"] = False
                return
            for pending_user in users:
                try:
                    maybe_claim_pending_vocab_leaderboard_rewards(pending_user, force=False)
                except Exception as exc:
                    stt_debug_log("login_reward_claim_failed", user=pending_user, error=str(exc))

    with LOGIN_REWARD_CLAIM_QUEUE_LOCK:
        pending_users = LOGIN_REWARD_CLAIM_QUEUE_STATE.get("users")
        if not isinstance(pending_users, set):
            pending_users = set()
            LOGIN_REWARD_CLAIM_QUEUE_STATE["users"] = pending_users
        pending_users.add(username)
        if bool(LOGIN_REWARD_CLAIM_QUEUE_STATE.get("running")):
            return {"scheduled": True, "running": True, "user": username}
        LOGIN_REWARD_CLAIM_QUEUE_STATE["running"] = True
    threading.Thread(target=worker, daemon=True, name="login-reward-claim").start()
    return {"scheduled": True, "running": False, "user": username}


def record_vocab_leaderboard_period_activity(username: str, learned_items: list[dict], default_epoch: float | None = None) -> dict:
    username = normalize_username(username)
    if not username or not learned_items:
        return {"recorded": 0}
    now_epoch = time.time()
    event_default_epoch = now_epoch if default_epoch is None else float(default_epoch or now_epoch)
    current_buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    current_starts = local_period_starts_epoch()
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_vocab_leaderboard_period_state()
        settled = settle_closed_vocab_leaderboard_periods(state, now_epoch)
        resets = state.get("resets") if isinstance(state.get("resets"), dict) else {}
        effective_starts = {
            scope: max(float(current_starts.get(scope, 0) or 0), timestamp_to_epoch(resets.get(scope, "")) or 0)
            for scope in ("day", "week", "month")
        }
        users = state.setdefault("users", {})
        recorded = {"day": 0, "week": 0, "month": 0}
        wal_scopes: dict[str, dict] = {}
        changed = bool(settled.get("period_state_changed"))
        now_stamp = utc_timestamp()
        for scope in ("day", "week", "month"):
            additions: dict[str, str] = {}
            for item in learned_items:
                normalized = normalize_vocabulary_registry_item(item)
                key = vocab_key(normalized.get("word", ""))
                if not key:
                    continue
                event_epoch = vocab_event_epoch(item, event_default_epoch)
                if event_epoch < effective_starts[scope] or vocab_period_bucket(scope, event_epoch) != current_buckets[scope]:
                    continue
                additions[key] = now_stamp
            if not additions:
                continue
            user_row = vocab_leaderboard_period_user_row(users, username, create=True)
            scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
            if clean(scope_row.get("bucket", "")) != current_buckets[scope]:
                scope_row = {"bucket": current_buckets[scope], "words": {}, "updated_at": ""}
                changed = True
            words = scope_row.setdefault("words", {})
            for key, stamp in additions.items():
                if key not in words:
                    recorded[scope] += 1
                    changed = True
                    wal_scope = wal_scopes.setdefault(scope, {"bucket": current_buckets[scope], "words": {}, "updated_at": now_stamp})
                    wal_scope["words"][key] = stamp
                words.setdefault(key, stamp)
            scope_row["updated_at"] = now_stamp
            user_row[scope] = scope_row
        if changed:
            state["updated_at"] = now_stamp
            npc_period_writer = globals().get("server_database_record_npc_period_activity")
            npc_period_result = {}
            if callable(npc_period_writer) and callable(globals().get("npc_top_profile_for_user")) and npc_top_profile_for_user(username):
                npc_period_result = npc_period_writer(username, wal_scopes)
            if settled.get("period_state_changed"):
                write_vocab_leaderboard_period_state(state)
                clear_vocab_leaderboard_period_wal()
            else:
                append_vocab_leaderboard_period_wal(username, wal_scopes, now_stamp)
                write_vocab_leaderboard_period_state_async(state)
            update_vocab_leaderboard_cache_for_user(username, "space_v", period_state=state)
            if int(npc_period_result.get("recorded", 0) or 0) > 0:
                invalidate_vocab_leaderboard_ram_cache("space_v")
    return {"recorded": sum(recorded.values()), **recorded, "settled": settled}


def reconcile_vocab_leaderboard_periods_from_learning_log(max_lines: int = 12000) -> dict:
    """Repair day/week/month vocabulary tops from completed Space_V lesson logs."""
    now_epoch = time.time()
    starts = local_period_starts_epoch()
    current_buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    base_state = load_vocab_leaderboard_period_state()
    resets = base_state.get("resets") if isinstance(base_state.get("resets"), dict) else {}
    effective_starts = {
        scope: max(float(starts.get(scope, 0) or 0), timestamp_to_epoch(resets.get(scope, "")) or 0)
        for scope in ("day", "week", "month")
    }
    earliest = min(effective_starts.values())
    rows = server_database_read_events("learning", limit=max(1, int(max_lines or 12000)), keep_days=0)
    checked = 0
    replayed = 0
    skipped = 0
    aggregate: dict[str, dict[str, set[str]]] = {}
    file_cache: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, dict) or clean(row.get("event", "")) != "lesson_complete":
            continue
        path_text = clean(row.get("path", ""))
        if not path_text.lower().endswith(".space_v"):
            continue
        username = normalize_username(row.get("user", ""))
        if not username:
            continue
        event_epoch = timestamp_to_epoch(row.get("at", "")) or timestamp_to_epoch(row.get("client_completed_at", ""))
        if event_epoch < earliest:
            continue
        target_scopes = [
            scope
            for scope in ("day", "week", "month")
            if event_epoch >= effective_starts[scope] and vocab_period_bucket(scope, event_epoch) == current_buckets[scope]
        ]
        if not target_scopes:
            continue
        checked += 1
        try:
            target = safe_server_data_path(path_text, username, admin=is_admin_user(username))
            if not target.is_file():
                skipped += 1
                continue
            cache_key = str(target)
            word_keys = file_cache.get(cache_key)
            if word_keys is None:
                file_payload, _structure_path = load_future_lesson_document(target)
                learned = vocabulary_words_from_payload(file_payload)
                word_keys = {
                    vocab_key(normalize_vocabulary_registry_item(item).get("word", ""))
                    for item in learned
                    if isinstance(item, dict)
                }
                word_keys = {key for key in word_keys if key}
                file_cache[cache_key] = word_keys
            if not word_keys:
                skipped += 1
                continue
            user_scopes = aggregate.setdefault(username, {})
            for scope in target_scopes:
                user_scopes.setdefault(scope, set()).update(word_keys)
            replayed += 1
        except Exception:
            skipped += 1
            continue
    added = 0
    changed = False
    settled = {"settled": 0, "period_state_changed": False}
    now_stamp = utc_timestamp()
    if aggregate:
        with VOCAB_LEADERBOARD_PERIOD_LOCK:
            state = load_vocab_leaderboard_period_state()
            settled = settle_closed_vocab_leaderboard_periods(state, now_epoch)
            changed = bool(settled.get("period_state_changed"))
            users = state.setdefault("users", {})
            for username, scopes in aggregate.items():
                user_row = vocab_leaderboard_period_user_row(users, username, create=True)
                for scope, word_keys in scopes.items():
                    if scope not in current_buckets or not word_keys:
                        continue
                    scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
                    if clean(scope_row.get("bucket", "")) != current_buckets[scope]:
                        scope_row = {"bucket": current_buckets[scope], "words": {}, "updated_at": ""}
                        changed = True
                    words = scope_row.setdefault("words", {})
                    for key in sorted(word_keys):
                        if key not in words:
                            added += 1
                            changed = True
                        words.setdefault(key, now_stamp)
                    scope_row["updated_at"] = now_stamp
                    user_row[scope] = scope_row
            if changed:
                state["updated_at"] = now_stamp
                write_vocab_leaderboard_period_state(state)
    return {"checked": checked, "replayed": replayed, "skipped": skipped, "added": added, "users": len(aggregate), "settled": settled}


def vocab_leaderboard_period_user_row(users: dict, username: str, create: bool = False) -> dict:
    """Return a period row even when older data used a different username casing."""
    username = normalize_username(username)
    if not isinstance(users, dict) or not username:
        return {}
    exact = users.get(username)
    if isinstance(exact, dict):
        return exact
    folded = username.casefold()
    for raw_key, raw_row in users.items():
        if clean(raw_key).casefold() == folded and isinstance(raw_row, dict):
            return raw_row
    if not create:
        return {}
    row: dict = {}
    users[username] = row
    return row


def vocab_leaderboard_period_counts_for_user(username: str, state: dict | None = None) -> dict:
    username = normalize_username(username)
    source = state if isinstance(state, dict) else load_vocab_leaderboard_period_state(clone=False)
    users = source.get("users") if isinstance(source.get("users"), dict) else {}
    row = vocab_leaderboard_period_user_row(users, username, create=False)
    counts = {}
    now_epoch = time.time()
    for scope in ("day", "week", "month"):
        scope_row = row.get(scope) if isinstance(row.get(scope), dict) else {}
        if clean(scope_row.get("bucket", "")) != vocab_period_bucket(scope, now_epoch):
            counts[scope] = 0
            continue
        words = scope_row.get("words") if isinstance(scope_row.get("words"), dict) else {}
        counts[scope] = len([key for key in words if clean(key)])
    return counts


def vocab_leaderboard_period_word_keys_for_user(username: str, state: dict | None = None) -> dict[str, set[str]]:
    username = normalize_username(username)
    source = state if isinstance(state, dict) else load_vocab_leaderboard_period_state(clone=False)
    users = source.get("users") if isinstance(source.get("users"), dict) else {}
    row = vocab_leaderboard_period_user_row(users, username, create=False)
    result: dict[str, set[str]] = {}
    now_epoch = time.time()
    for scope in ("day", "week", "month"):
        scope_row = row.get(scope) if isinstance(row.get(scope), dict) else {}
        if clean(scope_row.get("bucket", "")) != vocab_period_bucket(scope, now_epoch):
            result[scope] = set()
            continue
        words = scope_row.get("words") if isinstance(scope_row.get("words"), dict) else {}
        result[scope] = {clean(key).lower() for key in words if clean(key)}
    return result


def reset_vocab_leaderboard_periods(scopes: list[str] | tuple[str, ...] | None = None) -> dict:
    allowed = {"day", "week", "month"}
    requested = [clean(scope).lower() for scope in (scopes or []) if clean(scope).lower() in allowed]
    if not requested:
        requested = ["day", "week", "month"]
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_vocab_leaderboard_period_state()
        users = state.setdefault("users", {})
        for user_row in users.values():
            if not isinstance(user_row, dict):
                continue
            for scope in requested:
                user_row.pop(scope, None)
        resets = state.setdefault("resets", {})
        now = utc_timestamp()
        for scope in requested:
            resets[scope] = now
        state["updated_at"] = now
        write_vocab_leaderboard_period_state(state)
        database_reset = globals().get("server_database_reset_periods")
        if callable(database_reset):
            database_reset(requested)
    with VOCAB_LEADERBOARD_LOCK:
        rank_state = load_vocab_leaderboard_rank_state()
        boards = rank_state.setdefault("boards", {})
        for scope in requested:
            boards.pop(scope, None)
        try:
            write_vocab_leaderboard_rank_state(rank_state)
        except Exception:
            pass
    clear_vocab_leaderboard_social_scopes(requested)
    invalidate_vocab_leaderboard_ram_cache()
    return {"scopes": requested, "reset_at": utc_timestamp()}


def _clean_vocab_leaderboard_rank_rows(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    rows = {}
    for raw_username, raw_rank in source.items():
        username = normalize_username(raw_username)
        rank = max(0, space_w_int(raw_rank, 0))
        if username and rank > 0 and (username not in rows or rank < rows[username]):
            rows[username] = rank
    return rows

def _clean_vocab_leaderboard_move_rows(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    rows = {}
    for raw_username, raw_move in source.items():
        username = normalize_username(raw_username)
        if not username or not isinstance(raw_move, dict):
            continue
        candidate = {
            "direction": clean(raw_move.get("direction", "")),
            "delta": max(0, space_w_int(raw_move.get("delta", 0), 0)),
            "previous_rank": max(0, space_w_int(raw_move.get("previous_rank", raw_move.get("previousRank", 0)), 0)),
            "current_rank": max(0, space_w_int(raw_move.get("current_rank", raw_move.get("currentRank", 0)), 0)),
            "changed_at": clean(raw_move.get("changed_at", raw_move.get("changedAt", ""))),
        }
        current = rows.get(username)
        if not isinstance(current, dict) or timestamp_order_key(candidate["changed_at"]) >= timestamp_order_key(current.get("changed_at", "")):
            rows[username] = candidate
    return rows

def _clean_vocab_leaderboard_rank_boards(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    boards = {}
    for raw_scope, raw_board in source.items():
        scope = clean(raw_scope).lower()
        if not scope or not isinstance(raw_board, dict):
            continue
        boards[scope] = {
            "ranks": _clean_vocab_leaderboard_rank_rows(raw_board.get("ranks")),
            "moves": _clean_vocab_leaderboard_move_rows(raw_board.get("moves")),
            "updated_at": clean(raw_board.get("updated_at", raw_board.get("updatedAt", ""))),
        }
    return boards


# Added 2026-07-06: clones cached rank state without reparsing the rank JSON on every Top hit.
def clone_vocab_leaderboard_rank_state(state: dict | None = None) -> dict:
    try:
        import copy
        return copy.deepcopy(state if isinstance(state, dict) else {"version": 1, "updated_at": "", "boards": {}})
    except Exception:
        return {"version": 1, "updated_at": "", "boards": {}}


# Added 2026-07-06: cheap file stamp for the rank-state RAM cache.
def vocab_leaderboard_rank_file_stamp() -> tuple:
    _path, mtime_ns, size, _sha256 = server_database_document_signature(VOCAB_LEADERBOARD_RANK_FILE)
    return (mtime_ns, size)


def load_vocab_leaderboard_rank_state(clone: bool = True) -> dict:
    stamp = vocab_leaderboard_rank_file_stamp()
    cached_state = VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE.get("state")
    if VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE.get("stamp") == stamp and isinstance(cached_state, dict):
        return clone_vocab_leaderboard_rank_state(cached_state) if clone else cached_state
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_RANK_FILE, {})
    if isinstance(payload, dict):
        boards = _clean_vocab_leaderboard_rank_boards(payload.get("boards"))
        state = {"version": 1, "updated_at": clean(payload.get("updated_at", "")), "boards": boards}
        VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["stamp"] = stamp
        VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["state"] = clone_vocab_leaderboard_rank_state(state)
        return state
    return {"version": 1, "updated_at": "", "boards": {}}


def write_vocab_leaderboard_rank_state(state: dict) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "boards": _clean_vocab_leaderboard_rank_boards(state.get("boards")),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_serialize_count"] += 1
    if str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"} or postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
        try:
            from FUTURE.postgres.repositories import leaderboard_documents as pg_leaderboard_documents
            if pg_leaderboard_documents.is_leaderboard_document(VOCAB_LEADERBOARD_RANK_FILE):
                pg_leaderboard_documents.upsert_text(
                    VOCAB_LEADERBOARD_RANK_FILE,
                    encoded,
                    "utf-8",
                    utc_timestamp(),
                    0,
                )
            else:
                atomic_write_text(VOCAB_LEADERBOARD_RANK_FILE, encoded, encoding="utf-8")
        except Exception as exc:
            stt_debug_log("postgres_vocab_leaderboard_rank_write_failed", path=str(VOCAB_LEADERBOARD_RANK_FILE), error=str(exc))
            raise
    else:
        atomic_write_text(VOCAB_LEADERBOARD_RANK_FILE, encoded, encoding="utf-8")
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_write_count"] += 1
    VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["stamp"] = vocab_leaderboard_rank_file_stamp()
    VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["state"] = clone_vocab_leaderboard_rank_state(payload)
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["source"] = {}
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["stamp"] = {}


def write_vocab_leaderboard_rank_state_async(state: dict) -> None:
    # Updated 2026-07-29: one coalesced worker persists only the newest rank
    # snapshot; repeated Top movement must not spawn one serializer per request.
    if not isinstance(state, dict):
        return
    snapshot = clone_vocab_leaderboard_rank_state(state)
    with VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_LOCK:
        with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
            VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_snapshot_requests"] += 1
        VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE["version"] = int(VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("version", 0) or 0) + 1
        VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE["snapshot"] = snapshot
        worker = VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("worker")
        if not isinstance(worker, threading.Thread) or not worker.is_alive():
            worker = threading.Thread(target=_vocab_leaderboard_rank_flush_worker, daemon=True, name="vocab-leaderboard-rank-flush")
            VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE["worker"] = worker
            with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_worker_starts"] += 1
            worker.start()
    VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["stamp"] = vocab_leaderboard_rank_file_stamp()
    VOCAB_LEADERBOARD_RANK_STATE_RAM_CACHE["state"] = snapshot
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["source"] = {}
    VOCAB_LEADERBOARD_DISK_STAMP_CACHE["stamp"] = {}
    VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT.set()


def _vocab_leaderboard_rank_flush_worker() -> None:
    while True:
        VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT.wait()
        # Updated 2026-07-29: wait for the same quiet window as the activity
        # snapshot so derived rank persistence never competes with completion.
        while True:
            VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT.clear()
            time.sleep(2.0)
            if not VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT.is_set():
                break
        with VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_LOCK:
            version = int(VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("version", 0) or 0)
            snapshot = VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("snapshot")
        write_ok = True
        if isinstance(snapshot, dict):
            try:
                write_vocab_leaderboard_rank_state(snapshot)
            except Exception:
                # Added 2026-07-29: keep the one worker alive and retry the
                # newest derived snapshot after transient pool pressure.
                write_ok = False
                with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                    VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_write_failures"] += 1
        with VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_LOCK:
            if write_ok:
                VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE["flushed"] = version
            if not write_ok or int(VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("version", 0) or 0) != version:
                VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_EVENT.set()


def apply_vocab_leaderboard_rank_moves(boards: dict[str, list[dict]]) -> dict[str, list[dict]]:
    with VOCAB_LEADERBOARD_LOCK:
        state = load_vocab_leaderboard_rank_state(clone=False)
        state_boards = state.setdefault("boards", {})
        now = utc_timestamp()
        changed = False
        rank_change_events = 0
        for scope, rows in boards.items():
            board_state = state_boards.setdefault(scope, {})
            previous_ranks = board_state.get("ranks") if isinstance(board_state.get("ranks"), dict) else {}
            previous_moves = board_state.get("moves") if isinstance(board_state.get("moves"), dict) else {}
            next_ranks = {}
            next_moves = dict(previous_moves)
            for row in rows:
                username = normalize_username(row.get("username", ""))
                if not username:
                    continue
                current_rank = max(1, space_w_int(row.get("rank", 0), 0))
                next_ranks[username] = current_rank
                previous_rank = max(0, space_w_int(previous_ranks.get(username, 0), 0))
                move = previous_moves.get(username) if isinstance(previous_moves.get(username), dict) else {}
                if previous_rank and previous_rank != current_rank:
                    delta = previous_rank - current_rank
                    move = {
                        "direction": "up" if delta > 0 else "down",
                        "delta": abs(delta),
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "changed_at": now,
                    }
                    next_moves[username] = move
                    changed = True
                    rank_change_events += 1
                elif not previous_rank:
                    move = {
                        "direction": "new",
                        "delta": 0,
                        "previous_rank": 0,
                        "current_rank": current_rank,
                        "changed_at": now,
                    }
                    next_moves[username] = move
                    changed = True
                    rank_change_events += 1
                row["rank_move"] = move
            if previous_ranks != next_ranks:
                changed = True
            board_state["ranks"] = next_ranks
            board_state["moves"] = next_moves
            board_state["updated_at"] = now
        # Updated 2026-07-29: node-space scores are already durable in activity
        # state and rank movement is derived UI state. Keep those moves in RAM;
        # rewriting the combined rank document after every node Top change cost
        # roughly 2.7 seconds of process CPU in the isolated classroom gate.
        persist_changed = any(clean(scope).lower().startswith("space_v:") for scope in boards)
        if rank_change_events:
            with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                VOCAB_LEADERBOARD_RUNTIME_METRICS["rank_change_events"] += rank_change_events
        if changed and persist_changed:
            try:
                write_vocab_leaderboard_rank_state_async(state)
            except Exception:
                pass
    return boards


def vocabulary_leaderboard(limit: int = 10, double_check: bool = False, viewer: str = "", board_type: str = "space_v") -> dict:
    max_rows = max(1, min(500, space_w_int(limit, 10)))
    selected_board_type = normalize_space_leaderboard_type(board_type) or "space_v"
    viewer_key = normalize_username(viewer)
    cache_key = (selected_board_type, max_rows, "", bool(double_check))
    disk_stamp = vocab_leaderboard_disk_stamp(selected_board_type)
    if not double_check:
        with VOCAB_LEADERBOARD_LOCK:
            cached = VOCAB_LEADERBOARD_RAM_CACHE.get(cache_key)
            if (
                isinstance(cached, dict)
                and cached.get("disk_stamp") == disk_stamp
                and time.time() - float(cached.get("at", 0) or 0) <= VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS
            ):
                payload = vocab_leaderboard_payload_for_viewer(cached.get("payload") if isinstance(cached.get("payload"), dict) else {}, viewer_key)
                payload["cache"] = {"hit": True, "ttl_seconds": VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS, "disk_checked": True}
                return payload
    # Added 2026-07-10: coalesce cold leaderboard builds so a classroom opening
    # Top together does not make every request scan profiles and rank/social state.
    leaderboard_build_event = None
    leaderboard_should_signal = False
    if not double_check:
        now = time.time()
        with VOCAB_LEADERBOARD_LOCK:
            cached = VOCAB_LEADERBOARD_RAM_CACHE.get(cache_key)
            if (
                isinstance(cached, dict)
                and cached.get("disk_stamp") == disk_stamp
                and now - float(cached.get("at", 0) or 0) <= VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS
            ):
                payload = vocab_leaderboard_payload_for_viewer(cached.get("payload") if isinstance(cached.get("payload"), dict) else {}, viewer_key)
                payload["cache"] = {"hit": True, "ttl_seconds": VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS, "disk_checked": True}
                return payload
            inflight = VOCAB_LEADERBOARD_BUILD_INFLIGHT.get(cache_key)
            if isinstance(inflight, dict) and hasattr(inflight.get("event"), "wait") and now - float(inflight.get("at", 0.0) or 0.0) < 30.0:
                leaderboard_build_event = inflight.get("event")
            else:
                leaderboard_build_event = threading.Event()
                VOCAB_LEADERBOARD_BUILD_INFLIGHT[cache_key] = {"event": leaderboard_build_event, "at": now}
                leaderboard_should_signal = True
        if not leaderboard_should_signal and leaderboard_build_event is not None:
            leaderboard_build_event.wait(12.0)
            with VOCAB_LEADERBOARD_LOCK:
                cached = VOCAB_LEADERBOARD_RAM_CACHE.get(cache_key)
                if (
                    isinstance(cached, dict)
                    and cached.get("disk_stamp") == disk_stamp
                    and time.time() - float(cached.get("at", 0) or 0) <= VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS
                ):
                    payload = vocab_leaderboard_payload_for_viewer(cached.get("payload") if isinstance(cached.get("payload"), dict) else {}, viewer_key)
                    payload["cache"] = {"hit": True, "ttl_seconds": VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS, "disk_checked": True, "coalesced": True}
                    return payload
    try:
        with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
            VOCAB_LEADERBOARD_RUNTIME_METRICS["full_build_count"] += 1
        with VOCAB_LEADERBOARD_PERIOD_LOCK:
            period_roll_state = load_vocab_leaderboard_period_state()
            rolled = settle_closed_vocab_leaderboard_periods(period_roll_state)
            if rolled.get("settled") or rolled.get("period_state_changed"):
                write_vocab_leaderboard_period_state(period_roll_state)
    except Exception:
        pass
    period_reconcile = {}
    if double_check:
        try:
            period_reconcile = reconcile_vocab_leaderboard_periods_from_learning_log()
        except Exception as exc:
            period_reconcile = {"error": str(exc)}
    space_backfill = {}
    if selected_board_type != "space_v":
        backfill_cache_key = "__node_spaces__"
        backfill_cache = SPACE_LEADERBOARD_BACKFILL_CACHE.get(backfill_cache_key) if isinstance(SPACE_LEADERBOARD_BACKFILL_CACHE.get(backfill_cache_key), dict) else {}
        activity_state_for_backfill = load_space_leaderboard_activity_state(clone=False)
        activity_boards_for_backfill = activity_state_for_backfill.get("boards") if isinstance(activity_state_for_backfill.get("boards"), dict) else {}
        selected_activity_board = activity_boards_for_backfill.get(selected_board_type) if isinstance(activity_boards_for_backfill.get(selected_board_type), dict) else {}
        selected_activity_users = selected_activity_board.get("users") if isinstance(selected_activity_board.get("users"), dict) else {}
        should_backfill = bool(
            double_check
            or (
                not selected_activity_users
                and time.time() - float(backfill_cache.get("at", 0) or 0) > SPACE_LEADERBOARD_BACKFILL_TTL_SECONDS
            )
        )
        if should_backfill:
            with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
                VOCAB_LEADERBOARD_RUNTIME_METRICS["historical_backfill_count"] += 1
            try:
                space_backfill = backfill_space_leaderboard_from_learning_log()
            except Exception as exc:
                space_backfill = {"error": str(exc)}
            if double_check:
                try:
                    space_backfill["rescore"] = rescore_space_leaderboard_completions()
                except Exception as exc:
                    space_backfill["rescore_error"] = str(exc)
            else:
                space_backfill["rescore"] = {"deferred": True}
            SPACE_LEADERBOARD_BACKFILL_CACHE[backfill_cache_key] = {"at": time.time(), "payload": clone_vocab_leaderboard_payload(space_backfill)}
        else:
            space_backfill = clone_vocab_leaderboard_payload(backfill_cache.get("payload") if isinstance(backfill_cache.get("payload"), dict) else {})
            space_backfill["cached"] = True
            if selected_activity_users:
                space_backfill["activity_state"] = {"ready": True, "users": len(selected_activity_users)}
    npc_top_activity = {}
    if selected_board_type == "space_v":
        cached_npc_activity = VOCAB_LEADERBOARD_NPC_TOP_ACTIVITY_CACHE.get("payload")
        if time.time() - float(VOCAB_LEADERBOARD_NPC_TOP_ACTIVITY_CACHE.get("at", 0) or 0) <= 20.0 and isinstance(cached_npc_activity, dict):
            npc_top_activity = clone_vocab_leaderboard_payload(cached_npc_activity)
            npc_top_activity["cached"] = True
        else:
            try:
                npc_top_activity = apply_vocab_leaderboard_npc_top_activity()
                VOCAB_LEADERBOARD_NPC_TOP_ACTIVITY_CACHE["at"] = time.time()
                VOCAB_LEADERBOARD_NPC_TOP_ACTIVITY_CACHE["payload"] = clone_vocab_leaderboard_payload(npc_top_activity)
            except Exception as exc:
                npc_top_activity = {"error": str(exc)}
    npc_top_entries = npc_top_manifest()
    npc_top_state = load_vocab_leaderboard_npc_top_state()
    period_state = load_vocab_leaderboard_period_state(clone=False)
    space_activity_state = load_space_leaderboard_activity_state(clone=False)
    if selected_board_type == "space_v":
        candidates: set[str] = set(vocab_leaderboard_real_usernames(selected_board_type))
        candidates.update(npc_top_entries.keys())
    else:
        # Added 2026-07-10: node-space Top only needs users with activity on
        # that board plus the viewer; scanning every registered zero-score user
        # made 100-user classes rebuild cold boards with needless profile reads.
        candidates = set()
        if viewer_key:
            candidates.add(viewer_key)
        # Updated 2026-07-06: node-space boards already have their active users in RAM state; avoid scanning server-data root.
        space_boards = space_activity_state.get("boards") if isinstance(space_activity_state.get("boards"), dict) else {}
        selected_space_board = space_boards.get(selected_board_type) if isinstance(space_boards.get(selected_board_type), dict) else {}
        selected_space_users = selected_space_board.get("users") if isinstance(selected_space_board.get("users"), dict) else {}
        candidates.update(normalize_username(username) for username in selected_space_users.keys() if normalize_username(username))
        candidates.update(vocab_leaderboard_real_usernames(selected_board_type, max_rows * 2))
    include_test_users = str(os.environ.get("FUTURE_ISOLATED_LOAD_TEST", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    candidates = {
        username for username in candidates
        if username and (
            username in npc_top_entries
            or vocab_leaderboard_user_allowed(username, include_test_users)
        )
    }
    # Updated 2026-07-30: do not infer learners from Server Data folder names.
    # Registered users, active node users, and explicit NPCs are authoritative.
    all_rows = []
    zero_space_v_placeholders = 0
    for username in sorted(candidates, key=str.lower):
        if normalize_username(username).lower() == "testuser":
            continue
        npc_profile = npc_top_profile_for_user(username)
        if selected_board_type == "space_v" and npc_profile:
            profile = npc_profile
            display_name = clean(profile.get("full_name", "")) or username
            total_words = npc_top_total_words(username, npc_top_state)
            registry_updated_at = clean(((npc_top_state.get("npcs") if isinstance(npc_top_state.get("npcs"), dict) else {}).get(username) or {}).get("updated_at", ""))
            activity_counts = vocab_leaderboard_period_counts_for_user(username, period_state)
        else:
            if selected_board_type == "space_v" and double_check:
                try:
                    reconcile_user_vocabulary_total(username, sync_main=False)
                except Exception:
                    pass
            if selected_board_type == "space_v":
                registry_summary_reader = globals().get("read_user_vocab_registry_summary")
                registry_summary = registry_summary_reader(username) if callable(registry_summary_reader) else {}
                if isinstance(registry_summary, dict):
                    total_words = max(0, space_w_int(registry_summary.get("total_words", 0), 0))
                    registry_updated_at = clean(registry_summary.get("updated_at", ""))
                else:
                    registry = read_user_vocab_registry_snapshot(username)
                    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
                    total_words = len([key for key, item in words.items() if key and isinstance(item, dict)])
                    registry_updated_at = clean(registry.get("updated_at", ""))
                activity_counts = vocab_leaderboard_period_counts_for_user(username, period_state)
                if (
                    total_words <= 0
                    and max(
                        0,
                        int(activity_counts.get("day", 0) or 0),
                        int(activity_counts.get("week", 0) or 0),
                        int(activity_counts.get("month", 0) or 0),
                    ) <= 0
                    and normalize_username(username) != viewer_key
                ):
                    zero_space_v_placeholders += 1
                    if zero_space_v_placeholders > max_rows * 2:
                        continue
            else:
                space_counts = space_leaderboard_period_counts_for_user(username, selected_board_type, space_activity_state)
                total_words = space_counts.get("total", 0)
                activity_counts = space_counts
                registry_updated_at = clean(
                    (((space_activity_state.get("boards") if isinstance(space_activity_state.get("boards"), dict) else {}).get(selected_board_type) or {}).get("updated_at", ""))
                )
            profile = read_user_profile(username)
            display_name = clean(profile.get("full_name", "")) or username
        gender = clean(profile.get("gender", "")).lower()
        if gender not in {"male", "female", "other"}:
            gender = "other"
        all_rows.append(
            {
                "username": username,
                "display_name": display_name,
                "gender": gender,
                "avatar": clean(profile.get("avatar", "")),
                "total_words": total_words,
                "today_words": activity_counts.get("day", 0),
                "week_words": activity_counts.get("week", 0),
                "month_words": activity_counts.get("month", 0),
                "board_type": selected_board_type,
                "score_unit": "words" if selected_board_type == "space_v" else "points",
                "updated_at": registry_updated_at,
                "npc": bool(selected_board_type == "space_v" and npc_profile),
            }
        )
    boards: dict[str, list[dict]] = {}
    score_fields = {"total": "total_words", "day": "today_words", "week": "week_words", "month": "month_words"}
    for scope, score_field in score_fields.items():
        board_rows = []
        for row in all_rows:
            score = max(0, space_w_int(row.get(score_field, 0), 0))
            if score <= 0:
                continue
            board_rows.append({**row, "scope": scope, "score": score})
        board_rows.sort(key=lambda item: (-int(item.get("score", 0) or 0), clean(item.get("display_name", "")).lower(), clean(item.get("username", "")).lower()))
        for index, row in enumerate(board_rows, 1):
            row["rank"] = index
        boards[scope] = board_rows
    rank_boards = apply_vocab_leaderboard_rank_moves({f"{selected_board_type}:{scope}": rows for scope, rows in boards.items()})
    boards = {scope: rank_boards.get(f"{selected_board_type}:{scope}", rows) for scope, rows in boards.items()}
    for scope in score_fields:
        board_rows = boards.setdefault(scope, [])
        if len(board_rows) >= max_rows:
            continue
        used = {normalize_username(item.get("username", "")) for item in board_rows}
        seed = f"{scope}|{vocab_period_bucket(scope) or time.strftime('%Y-%m-%d')}"
        fillers = [
            row for row in all_rows
            if normalize_username(row.get("username", "")) and normalize_username(row.get("username", "")) not in used
        ]
        fillers.sort(key=lambda item: hashlib.sha256(f"{seed}|{normalize_username(item.get('username', ''))}".encode("utf-8", errors="ignore")).hexdigest())
        for filler in fillers[: max(0, max_rows - len(board_rows))]:
            board_rows.append(
                {
                    **filler,
                    "scope": scope,
                    "board_type": selected_board_type,
                    "score_unit": "words" if selected_board_type == "space_v" else "points",
                    "score": 0,
                    "rank": len(board_rows) + 1,
                    "placeholder": True,
                    "rank_move": {"direction": "preview", "delta": 0, "previous_rank": 0, "current_rank": len(board_rows) + 1},
                }
            )
    public_boards = {scope: board_rows[:max_rows] for scope, board_rows in boards.items()}
    settings_payload = load_server_settings()
    reaction_options = normalize_leaderboard_reaction_options(settings_payload.get("leaderboard_reactions"))
    public_boards = attach_vocab_leaderboard_social(public_boards, "", reaction_options)
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        social_state = load_vocab_leaderboard_social_state()
    payload = {
        "updated_at": utc_timestamp(),
        "limit": max_rows,
        "scope": "total",
        "board_type": selected_board_type,
        "board_types": list(SPACE_LEADERBOARD_TYPES),
        "score_unit": "words" if selected_board_type == "space_v" else "points",
        "double_checked": bool(double_check),
        "period_reconcile": period_reconcile,
        "space_backfill": space_backfill,
        "npc_top": npc_top_activity,
        "boards": public_boards,
        "users": public_boards.get("total", []),
        "viewers": vocab_leaderboard_viewer_rows(80),
        "world_chat": vocab_leaderboard_chat_rows(100),
        "rewards": normalize_leaderboard_rewards(settings_payload.get("leaderboard_rewards", DEFAULT_SETTINGS["leaderboard_rewards"])),
        "my_statuses": vocab_leaderboard_my_statuses("", social_state),
        "reaction_options": reaction_options,
        "reaction_keys": [item["key"] for item in reaction_options],
    }
    if not double_check:
        disk_stamp_after = vocab_leaderboard_disk_stamp(selected_board_type)
        with VOCAB_LEADERBOARD_LOCK:
            VOCAB_LEADERBOARD_RAM_CACHE[cache_key] = {
                "at": time.time(),
                "disk_stamp": disk_stamp_after,
                "payload": clone_vocab_leaderboard_payload(payload),
            }
            if len(VOCAB_LEADERBOARD_RAM_CACHE) > 48:
                oldest = sorted(
                    VOCAB_LEADERBOARD_RAM_CACHE.items(),
                    key=lambda item: float((item[1] or {}).get("at", 0) or 0),
                )[:16]
                for old_key, _row in oldest:
                    VOCAB_LEADERBOARD_RAM_CACHE.pop(old_key, None)
        payload["cache"] = {
            "hit": False,
            "ttl_seconds": VOCAB_LEADERBOARD_RAM_CACHE_TTL_SECONDS,
            "disk_checked": True,
            "disk_changed_while_loading": disk_stamp_after != disk_stamp,
        }
    if leaderboard_should_signal and leaderboard_build_event is not None:
        with VOCAB_LEADERBOARD_LOCK:
            inflight = VOCAB_LEADERBOARD_BUILD_INFLIGHT.get(cache_key)
            if isinstance(inflight, dict) and inflight.get("event") is leaderboard_build_event:
                VOCAB_LEADERBOARD_BUILD_INFLIGHT.pop(cache_key, None)
        leaderboard_build_event.set()
    return vocab_leaderboard_payload_for_viewer(payload, viewer_key)


def leaderboard_runtime_metrics_snapshot() -> dict:
    with VOCAB_LEADERBOARD_RUNTIME_METRICS_LOCK:
        leaderboard = dict(VOCAB_LEADERBOARD_RUNTIME_METRICS)
    with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
        activity = {
            key: value
            for key, value in SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.items()
            if key not in {"snapshot", "worker"}
        }
        worker = SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("worker")
        activity["worker_alive"] = bool(isinstance(worker, threading.Thread) and worker.is_alive())
    with VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_LOCK:
        rank_worker = VOCAB_LEADERBOARD_RANK_ASYNC_WRITE_STATE.get("worker")
    with VOCAB_NODE_TOP_BATCH_LOCK:
        node_batch = {
            key: VOCAB_NODE_TOP_BATCH_STATE.get(key, 0)
            for key in ("revision", "worker_starts", "build_count", "build_failures", "executor_workers")
        }
        node_batch["boards"] = {
            board_type: dict(row) for board_type, row in (VOCAB_NODE_TOP_BATCH_STATE.get("boards") or {}).items()
            if isinstance(row, dict)
        }
        node_worker = VOCAB_NODE_TOP_BATCH_STATE.get("worker")
        node_batch["worker_alive"] = bool(isinstance(node_worker, threading.Thread) and node_worker.is_alive())
        node_batch["executor_workers"] = max(0, space_w_int(VOCAB_NODE_TOP_BATCH_STATE.get("executor_workers", 0), 0))
    return {
        "leaderboard": leaderboard,
        "activity_snapshot": activity,
        "node_top_batch": node_batch,
        "rank_worker_alive": bool(isinstance(rank_worker, threading.Thread) and rank_worker.is_alive()),
        "thread_count": len(threading.enumerate()),
        "rank_worker_threads": sum(1 for thread in threading.enumerate() if thread.name == "vocab-leaderboard-rank-flush"),
        "activity_worker_threads": sum(1 for thread in threading.enumerate() if thread.name == "space-leaderboard-activity-flush"),
        "node_top_batch_threads": sum(1 for thread in threading.enumerate() if thread.name == "node-space-top-batch"),
    }


# Added 2026-07-20: coalesce final JSON serialization and let unchanged Top reads return HTTP 304.
def vocab_leaderboard_response_cache_row(
    limit: int = 80,
    viewer: str = "",
    board_type: str = "space_v",
    double_check: bool = False,
) -> dict:
    safe_type = normalize_space_leaderboard_type(board_type) or "space_v"
    max_rows = max(1, min(500, space_w_int(limit, 80)))
    viewer_key = normalize_username(viewer)
    if double_check:
        payload = {"ok": True, **vocabulary_leaderboard(max_rows, True, viewer_key, safe_type)}
        data = json_bytes(payload)
        return {
            "payload": payload,
            "bytes": data,
            "etag": f'"vocab-top-{hashlib.sha1(data).hexdigest()}"',
            "cache_hit": False,
            "double_checked": True,
        }

    shared_node_cache = safe_type in SPACE_LEADERBOARD_NODE_TYPES
    cache_key = (safe_type, max_rows, "" if shared_node_cache else viewer_key.lower())
    batch_status = node_space_top_batch_status(safe_type) if shared_node_cache else {"pending": False, "revision": 0, "published_revision": 0}
    build_event = None
    should_build = False
    with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
        row = VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.get(cache_key)
        # Added 2026-07-29: node-space snapshots are revision-invalidated.
        # Keep an expired snapshot available while its board-local batch is
        # pending instead of rebuilding synchronously inside a learner burst.
        if (
            not shared_node_cache
            and isinstance(row, dict)
            and row.get("expires_at")
            and time.time() >= float(row.get("expires_at", 0) or 0)
        ):
            VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.pop(cache_key, None)
            row = None
        if isinstance(row, dict) and isinstance(row.get("bytes"), bytes):
            row_revision = max(0, space_w_int(row.get("revision", 0), 0))
            if batch_status.get("pending") and row_revision < max(0, space_w_int(batch_status.get("revision", 0), 0)):
                batch_status = schedule_node_space_top_refresh(safe_type)
            return {
                **row,
                "cache_hit": True,
                "pending": bool(batch_status.get("pending") and row_revision < max(0, space_w_int(batch_status.get("revision", 0), 0))),
                "revision": max(row_revision, max(0, space_w_int(batch_status.get("revision", 0), 0))),
                "published_revision": row_revision,
                "retry_after_ms": max(0, space_w_int(batch_status.get("retry_after_ms", 0), 0)),
            }
        inflight = VOCAB_LEADERBOARD_RESPONSE_BUILD_INFLIGHT.get(cache_key)
        if isinstance(inflight, dict) and hasattr(inflight.get("event"), "wait"):
            build_event = inflight.get("event")
        else:
            build_event = threading.Event()
            VOCAB_LEADERBOARD_RESPONSE_BUILD_INFLIGHT[cache_key] = {"event": build_event, "at": time.time()}
            should_build = True
        generation = VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION

    if not should_build and build_event is not None:
        build_event.wait(12.0)
        with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
            row = VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.get(cache_key)
            if isinstance(row, dict) and isinstance(row.get("bytes"), bytes):
                return {**row, "cache_hit": True, "coalesced": True}

    try:
        if shared_node_cache:
            build_revision = max(0, space_w_int(batch_status.get("revision", 0), 0))
            seed_result = seed_node_space_completion_response_cache(
                "",
                safe_type,
                load_space_leaderboard_activity_state(clone=False),
                max_rows,
                shared=True,
                expected_generation=generation,
                batch_revision=build_revision,
            )
            with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
                row = VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.get(cache_key)
            if not seed_result.get("seeded") or not isinstance(row, dict) or not isinstance(row.get("bytes"), bytes):
                payload = {"ok": True, **vocabulary_leaderboard(max_rows, False, viewer_key, safe_type)}
                data = json_bytes(payload)
                row = {
                    "payload": payload,
                    "bytes": data,
                    "etag": f'"vocab-top-{hashlib.sha1(data).hexdigest()}"',
                    "cache_hit": False,
                    "at": time.time(),
                    "revision": build_revision,
                }
            if isinstance(row, dict) and isinstance(row.get("bytes"), bytes):
                _finish_node_space_top_batch_build(safe_type, build_revision, True)
        else:
            payload = {"ok": True, **vocabulary_leaderboard(max_rows, False, viewer_key, safe_type)}
            data = json_bytes(payload)
            row = {
                "payload": payload,
                "bytes": data,
                "etag": f'"vocab-top-{hashlib.sha1(data).hexdigest()}"',
                "cache_hit": False,
                "at": time.time(),
            }
        with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
            if generation == VOCAB_LEADERBOARD_RESPONSE_CACHE_GENERATION:
                VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE[cache_key] = row
                if len(VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE) > 256:
                    oldest = sorted(
                        VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.items(),
                        key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0),
                    )[:64]
                    for old_key, _old_row in oldest:
                        VOCAB_LEADERBOARD_RESPONSE_BYTES_CACHE.pop(old_key, None)
        latest_status = node_space_top_batch_status(safe_type) if shared_node_cache else batch_status
        row_revision = max(0, space_w_int((row or {}).get("revision", 0), 0))
        return {
            **(row or {}),
            "pending": bool(latest_status.get("pending") and row_revision < max(0, space_w_int(latest_status.get("revision", 0), 0))),
            "revision": max(row_revision, max(0, space_w_int(latest_status.get("revision", 0), 0))),
            "published_revision": row_revision,
            "retry_after_ms": max(0, space_w_int(latest_status.get("retry_after_ms", 0), 0)),
        }
    finally:
        if should_build and build_event is not None:
            with VOCAB_LEADERBOARD_RESPONSE_CACHE_LOCK:
                inflight = VOCAB_LEADERBOARD_RESPONSE_BUILD_INFLIGHT.get(cache_key)
                if isinstance(inflight, dict) and inflight.get("event") is build_event:
                    VOCAB_LEADERBOARD_RESPONSE_BUILD_INFLIGHT.pop(cache_key, None)
            build_event.set()
