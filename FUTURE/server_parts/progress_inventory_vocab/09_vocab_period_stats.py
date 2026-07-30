# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def local_period_starts_epoch() -> dict:
    now = time.time()
    local_now = time.localtime(now)
    day_start = time.mktime((local_now.tm_year, local_now.tm_mon, local_now.tm_mday, 0, 0, 0, local_now.tm_wday, local_now.tm_yday, local_now.tm_isdst))
    week_start = day_start - (local_now.tm_wday * 24 * 60 * 60)
    month_start = time.mktime((local_now.tm_year, local_now.tm_mon, 1, 0, 0, 0, 0, 1, local_now.tm_isdst))
    return {"day": day_start, "week": week_start, "month": month_start}


def vocabulary_item_first_epoch(item: dict) -> float:
    if not isinstance(item, dict):
        return 0.0
    return timestamp_to_epoch(item.get("first", "")) or timestamp_to_epoch(item.get("last", ""))


def vocabulary_registry_period_counts(words: dict) -> dict:
    starts = local_period_starts_epoch()
    counts = {"total": 0, "today": 0, "week": 0, "month": 0}
    for key, item in (words.items() if isinstance(words, dict) else []):
        if not key or not isinstance(item, dict):
            continue
        counts["total"] += 1
        learned_at = vocabulary_item_first_epoch(item)
        if learned_at >= starts["day"]:
            counts["today"] += 1
        if learned_at >= starts["week"]:
            counts["week"] += 1
        if learned_at >= starts["month"]:
            counts["month"] += 1
    return counts


def vocab_period_bucket(scope: str, epoch: float | None = None) -> str:
    scope = clean(scope).lower()
    value = time.time() if epoch is None else float(epoch or 0)
    local = time.localtime(value)
    if scope == "day":
        return time.strftime("%Y-%m-%d", local)
    if scope == "week":
        day_start = time.mktime((local.tm_year, local.tm_mon, local.tm_mday, 0, 0, 0, local.tm_wday, local.tm_yday, local.tm_isdst))
        week_start = day_start - (local.tm_wday * 24 * 60 * 60)
        return time.strftime("%Y-%m-%d", time.localtime(week_start))
    if scope == "month":
        return time.strftime("%Y-%m", local)
    return ""


def vocab_event_epoch(item: dict | None = None, default_epoch: float | None = None) -> float:
    source = item if isinstance(item, dict) else {}
    for key in ("last", "learned_at", "learnedAt", "updated_at", "updatedAt", "first"):
        raw = clean(source.get(key, ""))
        if not raw:
            continue
        epoch = timestamp_to_epoch(raw)
        if epoch > 0:
            return epoch
    return time.time() if default_epoch is None else float(default_epoch or time.time())


SPACE_LEADERBOARD_TYPES = ("space_v", "space_w", "space_q", "space_p", "space_s", "space_l")
SPACE_LEADERBOARD_NODE_TYPES = ("space_w", "space_q", "space_p", "space_s", "space_l")
SPACE_LEADERBOARD_ACTIVITY_FILE = SERVER_DATA_ROOT / "space_leaderboard_activity.json"
SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE: dict[str, object] = {"stamp": (), "state": {}}
SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK = threading.Lock()
SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT = threading.Event()
SPACE_LEADERBOARD_ACTIVE_COMPLETIONS_LOCK = threading.Lock()
SPACE_LEADERBOARD_ACTIVE_COMPLETIONS = 0
SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE: dict[str, object] = {
    "version": 0,
    "flushed": 0,
    "snapshot": None,
    "worker": None,
    "snapshot_requests": 0,
    "worker_starts": 0,
    "serialize_count": 0,
    "write_count": 0,
    "write_failures": 0,
    "last_bytes": 0,
    "write_ms_total": 0.0,
    "write_ms_max": 0.0,
}


def space_leaderboard_activity_file_stamp() -> tuple:
    _path, mtime_ns, size, _sha256 = server_database_document_signature(SPACE_LEADERBOARD_ACTIVITY_FILE)
    return (mtime_ns, size)


def clone_space_leaderboard_activity_state(state: dict) -> dict:
    try:
        import copy
        return copy.deepcopy(state if isinstance(state, dict) else {})
    except Exception:
        return dict(state or {})


def normalize_space_leaderboard_type(value: object = "") -> str:
    safe = clean(value).lower().replace("-", "_")
    if safe in {"v", "spacev", "space_b", "spaceb"}:
        return "space_v"
    if safe in {"w", "spacew"}:
        return "space_w"
    if safe in {"q", "spaceq"}:
        return "space_q"
    if safe in {"p", "spacep"}:
        return "space_p"
    if safe in {"s", "spaces"}:
        return "space_s"
    if safe in {"l", "spacel"}:
        return "space_l"
    return safe if safe in SPACE_LEADERBOARD_TYPES else ""


def space_leaderboard_type_for_path(relative_path: str = "", payload: dict | None = None, source: str = "") -> str:
    from_source = normalize_space_leaderboard_type(source)
    if from_source:
        return from_source
    suffix = Path(clean_path_value(relative_path)).suffix.lower()
    if suffix in {".space_v", ".space_b"}:
        return "space_v"
    if suffix == ".space_w":
        return "space_w"
    if suffix == ".space_q":
        return "space_q"
    if suffix == ".space_p":
        return "space_p"
    if suffix == ".space_s":
        return "space_s"
    if suffix == ".space_l":
        return "space_l"
    data = payload if isinstance(payload, dict) else {}
    if data.get("k") in {"ftv", "ftb"} or data.get("kind") == "future_vocabulary_payload":
        return "space_v"
    if data.get("k") == "ftq" or data.get("kind") == "future_question_payload":
        return "space_q"
    if data.get("k") == "ftp" or data.get("kind") == "future_paragraph_payload":
        mode = normalize_space_leaderboard_type(data.get("space_mode", ""))
        return mode if mode in {"space_p", "space_s", "space_l"} else "space_p"
    return "space_w" if data else ""


def recursive_space_q_question_count(value: object) -> int:
    if isinstance(value, list):
        return sum(recursive_space_q_question_count(item) for item in value)
    if not isinstance(value, dict):
        return 0
    total = 0
    cards = value.get("cards") if isinstance(value.get("cards"), dict) else {}
    for key in ("questions", "qs"):
        rows = cards.get(key) if isinstance(cards, dict) else None
        if isinstance(rows, list):
            total += len([item for item in rows if isinstance(item, dict) or clean(item)])
        rows = value.get(key)
        if isinstance(rows, list):
            total += len([item for item in rows if isinstance(item, dict) or clean(item)])
    for key in ("children", "nodes", "n", "items", "cards", "groups", "blocks"):
        child = value.get(key)
        if child is cards:
            continue
        if isinstance(child, (list, dict)):
            total += recursive_space_q_question_count(child)
    return total


def paragraph_payload_sentence_count(payload: dict | None) -> int:
    """Count child sentences across all paragraph nodes for space_p/space_s/space_l.
    Each node is one paragraph that holds many children (sentences), so counting
    sentences is fairer than counting nodes."""
    data = payload if isinstance(payload, dict) else {}
    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else data.get("n")
    if not isinstance(nodes, list):
        return 0
    total = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        children = node.get("children") if isinstance(node.get("children"), list) else node.get("c")
        if isinstance(children, list):
            total += len([child for child in children if isinstance(child, dict) or clean(child)])
        else:
            total += 1
    return total


def space_leaderboard_points_from_payload(space_type: str, payload: dict | None, fallback: int = 0) -> int:
    safe_type = normalize_space_leaderboard_type(space_type)
    data = payload if isinstance(payload, dict) else {}
    if safe_type == "space_q":
        return max(0, lesson_payload_question_total_count(data) or lesson_payload_question_count(data) or recursive_space_q_question_count(data) or fallback)
    if safe_type in {"space_p", "space_s", "space_l"}:
        return max(0, paragraph_payload_sentence_count(data) or lesson_payload_node_count(data) or fallback)
    if safe_type == "space_w":
        return max(0, lesson_payload_node_count(data) or fallback)
    return max(0, fallback)


def _clean_space_leaderboard_scope_row(existing: object, incoming: object) -> dict:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    bucket = clean(source.get("bucket", "")) or clean(current.get("bucket", ""))
    points = max(0, space_w_int(current.get("points", 0), 0), space_w_int(source.get("points", 0), 0))
    updated_at = timestamp_latest_text(current.get("updated_at", ""), source.get("updated_at", ""))
    return {"bucket": bucket, "points": points, "updated_at": updated_at} if bucket or points else {}


def _clean_space_leaderboard_user_row(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    completed = {}
    for raw_key, raw_row in (source.get("completed") if isinstance(source.get("completed"), dict) else {}).items():
        key = clean(raw_key)
        if not key or not isinstance(raw_row, dict):
            continue
        points = max(0, space_w_int(raw_row.get("points", 0), 0))
        if points <= 0:
            continue
        credited_buckets = raw_row.get("credited_buckets") if isinstance(raw_row.get("credited_buckets"), dict) else {}
        clean_credited_buckets = {
            scope: clean(credited_buckets.get(scope, ""))
            for scope in ("day", "week", "month")
            if clean(credited_buckets.get(scope, ""))
        }
        completed[key] = {
            "lesson_id": clean(raw_row.get("lesson_id") or raw_row.get("lessonId") or raw_row.get("file_id")),
            "path": clean_path_value(raw_row.get("path", "")),
            "points": points,
            "completed_at": clean(raw_row.get("completed_at", raw_row.get("completedAt", ""))),
            "last_completed_at": clean(raw_row.get("last_completed_at", raw_row.get("lastCompletedAt", ""))),
            "title": clean(raw_row.get("title", ""))[:180],
            "credited_buckets": clean_credited_buckets,
        }
    periods = {}
    for scope in ("day", "week", "month"):
        row = _clean_space_leaderboard_scope_row(source.get(scope), source.get(scope))
        if row:
            periods[scope] = row
    return {
        "total_points": max(0, space_w_int(source.get("total_points", source.get("totalPoints", 0)), 0)),
        "completed": completed,
        **periods,
        "updated_at": clean(source.get("updated_at", source.get("updatedAt", ""))),
    }


def space_leaderboard_entry_credited_buckets(entry: dict) -> dict:
    # Added 2026-07-06: let repeated study count once per active period without inflating all-time unique completion totals.
    source = entry if isinstance(entry, dict) else {}
    credited = source.get("credited_buckets") if isinstance(source.get("credited_buckets"), dict) else {}
    result = {
        scope: clean(credited.get(scope, ""))
        for scope in ("day", "week", "month")
        if clean(credited.get(scope, ""))
    }
    if result:
        return result
    event_epoch = timestamp_to_epoch(source.get("completed_at", "")) or timestamp_to_epoch(source.get("completedAt", ""))
    if event_epoch > 0:
        return {scope: vocab_period_bucket(scope, event_epoch) for scope in ("day", "week", "month")}
    return {}


def load_space_leaderboard_activity_state(clone: bool = True) -> dict:
    try:
        cached = SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE.get("state")
        with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
            pending_version = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("version", 0) or 0)
            flushed_version = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("flushed", 0) or 0)
        # Added 2026-07-29: a queued RAM snapshot is newer than the durable
        # derived file. Never reload that older file while a coalesced flush is pending.
        if pending_version > flushed_version and isinstance(cached, dict) and cached:
            return clone_space_leaderboard_activity_state(cached) if clone else cached
        stamp = space_leaderboard_activity_file_stamp()
        if stamp == SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE.get("stamp") and isinstance(cached, dict) and cached:
            return clone_space_leaderboard_activity_state(cached) if clone else cached
        payload = server_database_read_document_json(SPACE_LEADERBOARD_ACTIVITY_FILE, {})
        if isinstance(payload, dict):
            boards = {}
            raw_boards = payload.get("boards") if isinstance(payload.get("boards"), dict) else {}
            for raw_type, raw_board in raw_boards.items():
                board_type = normalize_space_leaderboard_type(raw_type)
                if not board_type or board_type == "space_v" or not isinstance(raw_board, dict):
                    continue
                users = raw_board.get("users") if isinstance(raw_board.get("users"), dict) else {}
                boards[board_type] = {
                    "users": {
                        normalize_username(username): _clean_space_leaderboard_user_row(row)
                        for username, row in users.items()
                        if normalize_username(username) and isinstance(row, dict)
                    },
                    "updated_at": clean(raw_board.get("updated_at", raw_board.get("updatedAt", ""))),
                }
            state = {"version": 1, "updated_at": clean(payload.get("updated_at", "")), "boards": boards}
            SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["stamp"] = stamp
            SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["state"] = clone_space_leaderboard_activity_state(state)
            return state
    except Exception:
        pass
    return {"version": 1, "updated_at": "", "boards": {}}


def write_space_leaderboard_activity_state(state: dict) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "boards": {},
    }
    boards = state.get("boards") if isinstance(state.get("boards"), dict) else {}
    for raw_type, raw_board in boards.items():
        board_type = normalize_space_leaderboard_type(raw_type)
        if not board_type or board_type == "space_v" or not isinstance(raw_board, dict):
            continue
        users = raw_board.get("users") if isinstance(raw_board.get("users"), dict) else {}
        payload["boards"][board_type] = {
            "users": {
                normalize_username(username): _clean_space_leaderboard_user_row(row)
                for username, row in users.items()
                if normalize_username(username) and isinstance(row, dict)
            },
            "updated_at": clean(raw_board.get("updated_at", "")),
        }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    started = time.perf_counter()
    with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["serialize_count"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("serialize_count", 0) or 0) + 1
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["last_bytes"] = len(encoded.encode("utf-8"))
    atomic_write_text(SPACE_LEADERBOARD_ACTIVITY_FILE, encoded, encoding="utf-8")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["write_count"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("write_count", 0) or 0) + 1
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["write_ms_total"] = float(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("write_ms_total", 0.0) or 0.0) + elapsed_ms
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["write_ms_max"] = max(float(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("write_ms_max", 0.0) or 0.0), elapsed_ms)
    SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["stamp"] = space_leaderboard_activity_file_stamp()
    SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["state"] = clone_space_leaderboard_activity_state(payload)


def write_space_leaderboard_activity_state_async(state: dict) -> None:
    # Added 2026-07-29: one coalesced worker persists the derived Top snapshot; durable completion events remain the recovery source.
    if not isinstance(state, dict):
        return
    # Updated 2026-07-29: keep only the latest RAM source reference here.
    # Cloning the growing 100-user state on every completion consumed most of
    # the burst CPU; the single worker clones once after the quiet window.
    with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["snapshot_requests"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("snapshot_requests", 0) or 0) + 1
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["version"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("version", 0) or 0) + 1
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["snapshot"] = state
        worker = SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("worker")
        if not isinstance(worker, threading.Thread) or not worker.is_alive():
            worker = threading.Thread(target=_space_leaderboard_activity_flush_worker, daemon=True, name="space-leaderboard-activity-flush")
            SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["worker"] = worker
            SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["worker_starts"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("worker_starts", 0) or 0) + 1
            worker.start()
    SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["stamp"] = ()
    SPACE_LEADERBOARD_ACTIVITY_STATE_RAM_CACHE["state"] = state
    SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT.set()


# Added 2026-07-29: keep derived activity serialization off the completion hot path.
def space_leaderboard_completion_active(delta: int = 0) -> int:
    global SPACE_LEADERBOARD_ACTIVE_COMPLETIONS
    with SPACE_LEADERBOARD_ACTIVE_COMPLETIONS_LOCK:
        SPACE_LEADERBOARD_ACTIVE_COMPLETIONS = max(0, int(SPACE_LEADERBOARD_ACTIVE_COMPLETIONS) + int(delta or 0))
        return SPACE_LEADERBOARD_ACTIVE_COMPLETIONS


def space_leaderboard_completion_active_count() -> int:
    with SPACE_LEADERBOARD_ACTIVE_COMPLETIONS_LOCK:
        return max(0, int(SPACE_LEADERBOARD_ACTIVE_COMPLETIONS))


def _space_leaderboard_activity_flush_worker() -> None:
    while True:
        SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT.wait()
        # Updated 2026-07-29: wait for a quiet window so classroom bursts write
        # one derived snapshot after requests finish instead of serializing it
        # in the middle of completion latency measurements.
        while True:
            SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT.clear()
            time.sleep(2.0)
            if not SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT.is_set():
                break
        # A quiet activity queue is not enough: a new completion may have
        # started during the delay. Let its durable write finish first.
        while space_leaderboard_completion_active_count() > 0:
            time.sleep(0.1)
        with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
            version = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("version", 0) or 0)
            snapshot_source = SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("snapshot")
        with VOCAB_LEADERBOARD_PERIOD_LOCK:
            snapshot = clone_space_leaderboard_activity_state(snapshot_source) if isinstance(snapshot_source, dict) else None
        write_ok = True
        if isinstance(snapshot, dict):
            try:
                write_space_leaderboard_activity_state(snapshot)
            except Exception:
                # Added 2026-07-29: derived snapshots must retry after a busy
                # completion burst instead of killing the sole flush worker.
                write_ok = False
                with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
                    SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["write_failures"] = int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("write_failures", 0) or 0) + 1
        with SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_LOCK:
            if write_ok:
                SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE["flushed"] = version
            if not write_ok or int(SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_STATE.get("version", 0) or 0) != version:
                SPACE_LEADERBOARD_ACTIVITY_ASYNC_WRITE_EVENT.set()


# Added 2026-07-29: expose the committed learner delta so the client can keep
# the just-completed user visible while the official board snapshot batches.
def _space_leaderboard_viewer_delta(username: str, row: dict, point_count: int, pending: bool = True) -> dict:
    safe_row = row if isinstance(row, dict) else {}
    def scope_points(scope: str) -> int:
        value = safe_row.get(scope) if isinstance(safe_row.get(scope), dict) else {}
        return max(0, space_w_int(value.get("points", 0), 0))
    return {
        "username": normalize_username(username),
        "display_name": normalize_username(username),
        "total_words": max(0, space_w_int(safe_row.get("total_points", 0), 0)),
        "today_words": scope_points("day"),
        "week_words": scope_points("week"),
        "month_words": scope_points("month"),
        "points": max(0, space_w_int(point_count, 0)),
        "pending": bool(pending),
    }


def record_space_leaderboard_completion(username: str, relative_path: str, space_type: str, points: int, title: str = "", completed_at: str = "", lesson_id: str = "") -> dict:
    username = normalize_username(username)
    board_type = normalize_space_leaderboard_type(space_type)
    point_count = max(0, space_w_int(points, 0))
    rel_path = clean_path_value(relative_path)
    if not username or board_type not in SPACE_LEADERBOARD_NODE_TYPES or point_count <= 0 or not rel_path:
        return {"recorded": False, "reason": "invalid"}
    now_epoch = time.time()
    now_stamp = utc_timestamp()
    event_stamp = clean(completed_at) or now_stamp
    current_buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    canonical_id = clean(lesson_id)[:240]
    identity_key = f"id:{canonical_id.lower()}" if canonical_id.lower().startswith("ftg-lesson-") else f"path:{rel_path.lower()}"
    completion_key = hashlib.sha256(f"{username.lower()}|{board_type}|{identity_key}".encode("utf-8", errors="ignore")).hexdigest()[:32]
    legacy_key = hashlib.sha256(f"{username.lower()}|{board_type}|{rel_path.lower()}".encode("utf-8", errors="ignore")).hexdigest()[:32]
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_space_leaderboard_activity_state()
        boards = state.setdefault("boards", {})
        board = boards.setdefault(board_type, {"users": {}, "updated_at": ""})
        users = board.setdefault("users", {})
        row = users.get(username) if isinstance(users.get(username), dict) else {}
        row = _clean_space_leaderboard_user_row(row)
        completed = row.setdefault("completed", {})
        existing_entry = completed.get(completion_key) if isinstance(completed.get(completion_key), dict) else None
        if existing_entry is None and canonical_id and isinstance(completed.get(legacy_key), dict):
            existing_entry = completed.pop(legacy_key)
            completed[completion_key] = existing_entry
        if existing_entry:
            entry = existing_entry
            if canonical_id:
                entry["lesson_id"] = canonical_id
            credited_buckets = space_leaderboard_entry_credited_buckets(entry)
            entry["last_completed_at"] = event_stamp
            entry["path"] = clean_path_value(entry.get("path", "")) or rel_path
            entry["title"] = clean(entry.get("title", ""))[:180] or clean(title)[:180]
            total_added = False
        else:
            credited_buckets = {}
            entry = {
                "lesson_id": canonical_id,
                "path": rel_path,
                "points": point_count,
                "completed_at": event_stamp,
                "last_completed_at": event_stamp,
                "title": clean(title)[:180],
                "credited_buckets": credited_buckets,
            }
            row["total_points"] = max(0, space_w_int(row.get("total_points", 0), 0)) + point_count
            total_added = True
        credited_scopes = []
        for scope, bucket in current_buckets.items():
            if clean(credited_buckets.get(scope, "")) == bucket:
                continue
            scope_row = row.get(scope) if isinstance(row.get(scope), dict) else {}
            if clean(scope_row.get("bucket", "")) != bucket:
                scope_row = {"bucket": bucket, "points": 0, "updated_at": ""}
            scope_row["points"] = max(0, space_w_int(scope_row.get("points", 0), 0)) + point_count
            scope_row["updated_at"] = now_stamp
            row[scope] = scope_row
            credited_buckets[scope] = bucket
            credited_scopes.append(scope)
        if not credited_scopes and existing_entry:
            return {
                "recorded": False,
                "duplicate": True,
                "type": board_type,
                "points": 0,
                "viewer_delta": _space_leaderboard_viewer_delta(username, row, 0),
            }
        entry["credited_buckets"] = credited_buckets
        completed[completion_key] = entry
        row["updated_at"] = now_stamp
        users[username] = row
        board["users"] = users
        board["updated_at"] = now_stamp
        state["updated_at"] = now_stamp
        write_space_leaderboard_activity_state_async(state)
    cache_updated = False
    try:
        update_cache = globals().get("update_vocab_leaderboard_cache_for_user")
        if callable(update_cache):
            # Updated 2026-07-06: keep Space_W/Q/P/S/L top cache hot after a single learner completes.
            cache_update = update_cache(
                username,
                board_type=board_type,
                period_state=state,
                vocabulary_result={
                    "leaderboard_counts": {
                        "total": row.get("total_points", 0),
                        "day": (row.get("day") or {}).get("points", 0) if isinstance(row.get("day"), dict) else 0,
                        "week": (row.get("week") or {}).get("points", 0) if isinstance(row.get("week"), dict) else 0,
                        "month": (row.get("month") or {}).get("points", 0) if isinstance(row.get("month"), dict) else 0,
                    },
                    "leaderboard_updated_at": now_stamp,
                },
            )
            fast_seed = cache_update.get("fast_response_seed") if isinstance(cache_update.get("fast_response_seed"), dict) else {}
            if cache_update.get("updated") or fast_seed.get("seeded"):
                cache_updated = True
                return {
                    "recorded": True,
                    "type": board_type,
                    "points": point_count,
                    "credited_scopes": credited_scopes,
                    "total_added": total_added,
                    "cache_update": cache_update,
                    "viewer_delta": _space_leaderboard_viewer_delta(username, row, point_count),
                }
    except Exception:
        cache_updated = False
    if not cache_updated:
        try:
            invalidate_cache = globals().get("invalidate_vocab_leaderboard_ram_cache")
            if callable(invalidate_cache):
                # Updated 2026-07-06: foreground Top request rebuilds this board; avoid duplicate background CPU.
                invalidate_cache(board_type, schedule_refresh=False)
        except Exception:
            pass
    return {
        "recorded": True,
        "type": board_type,
        "points": point_count,
        "credited_scopes": credited_scopes,
        "total_added": total_added,
        "viewer_delta": _space_leaderboard_viewer_delta(username, row, point_count),
    }


def reset_space_leaderboard_today_credit_for_testing(board_types: list[str] | tuple[str, ...] | None = None) -> dict:
    # Added 2026-07-06: dashboard test reset lets admins replay the same Space lesson into Top Today.
    requested = [normalize_space_leaderboard_type(value) for value in (board_types or [])]
    requested = [value for value in requested if value in SPACE_LEADERBOARD_NODE_TYPES]
    if not requested:
        requested = list(SPACE_LEADERBOARD_NODE_TYPES)
    today_bucket = vocab_period_bucket("day", time.time())
    reset_at = utc_timestamp()
    removed_entries = 0
    touched_users = 0
    touched_boards = set()
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_space_leaderboard_activity_state()
        boards = state.setdefault("boards", {})
        for board_type in requested:
            board = boards.get(board_type) if isinstance(boards.get(board_type), dict) else {}
            users = board.get("users") if isinstance(board.get("users"), dict) else {}
            board_changed = False
            for username, row in users.items():
                if not isinstance(row, dict):
                    continue
                user_changed = False
                completed = row.get("completed") if isinstance(row.get("completed"), dict) else {}
                for entry in completed.values():
                    if not isinstance(entry, dict):
                        continue
                    credited_buckets = space_leaderboard_entry_credited_buckets(entry)
                    if clean(credited_buckets.get("day", "")) == today_bucket:
                        credited_buckets.pop("day", None)
                        entry["credited_buckets"] = credited_buckets
                        removed_entries += 1
                        user_changed = True
                if user_changed:
                    row.pop("day", None)
                    row["updated_at"] = reset_at
                    touched_users += 1
                    board_changed = True
            if board_changed:
                board["updated_at"] = reset_at
                touched_boards.add(board_type)
        if touched_boards:
            state["updated_at"] = reset_at
            write_space_leaderboard_activity_state(state)
    for board_type in touched_boards:
        try:
            invalidate_cache = globals().get("invalidate_vocab_leaderboard_ram_cache")
            if callable(invalidate_cache):
                invalidate_cache(board_type, schedule_refresh=False)
        except Exception:
            pass
    return {
        "reset_at": reset_at,
        "bucket": today_bucket,
        "board_types": sorted(touched_boards) if touched_boards else requested,
        "removed_entries": removed_entries,
        "touched_users": touched_users,
    }



def backfill_space_leaderboard_from_learning_log(max_lines: int = 20000) -> dict:
    """Replay historical Space_W/Q/P/S/L completions from the learning log so the
    all-time totals include lessons finished before per-completion recording existed.
    Idempotent: reuses the same completion_key dedup as record_space_leaderboard_completion."""
    rows = server_database_read_events("learning", limit=max(1, int(max_lines or 20000)), keep_days=0)
    checked = 0
    recorded = 0
    skipped = 0
    changed = False
    payload_cache: dict[str, int] = {}
    now_epoch = time.time()
    current_buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    now_stamp = utc_timestamp()
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_space_leaderboard_activity_state()
        boards = state.setdefault("boards", {})
        for row in rows:
            if not isinstance(row, dict) or clean(row.get("event", "")) != "lesson_complete":
                continue
            path_text = clean_path_value(row.get("path", ""))
            if not path_text:
                continue
            board_type = space_leaderboard_type_for_path(path_text, None, clean(row.get("space_leaderboard_type", "")))
            if board_type not in SPACE_LEADERBOARD_NODE_TYPES:
                continue
            username = normalize_username(row.get("user", ""))
            if not username or username.lower() == "testuser":
                continue
            checked += 1
            canonical_id = clean(row.get("lesson_id") or row.get("file_id"))[:240]
            if not canonical_id:
                alias_reader = globals().get("server_database_lesson_file_id_for_path")
                canonical_id = clean(alias_reader(path_text))[:240] if callable(alias_reader) else ""
            identity_key = f"id:{canonical_id.lower()}" if canonical_id.lower().startswith("ftg-lesson-") else f"path:{path_text.lower()}"
            completion_key = hashlib.sha256(
                f"{username.lower()}|{board_type}|{identity_key}".encode("utf-8", errors="ignore")
            ).hexdigest()[:32]
            legacy_key = hashlib.sha256(
                f"{username.lower()}|{board_type}|{path_text.lower()}".encode("utf-8", errors="ignore")
            ).hexdigest()[:32]
            board = boards.setdefault(board_type, {"users": {}, "updated_at": ""})
            users = board.setdefault("users", {})
            user_row = _clean_space_leaderboard_user_row(users.get(username) if isinstance(users.get(username), dict) else {})
            completed = user_row.setdefault("completed", {})
            if completion_key in completed:
                continue
            if canonical_id and legacy_key in completed:
                completed[completion_key] = completed.pop(legacy_key)
                completed[completion_key]["lesson_id"] = canonical_id
                users[username] = user_row
                changed = True
                continue
            points = max(0, space_w_int(row.get("space_leaderboard_points", 0), 0))
            if points <= 0:
                cache_key = f"{board_type}|{path_text.lower()}"
                if cache_key not in payload_cache:
                    try:
                        target = safe_server_data_path(path_text, username, admin=is_admin_user(username))
                        if target.is_file():
                            file_payload, _structure_path = load_future_lesson_document(target)
                            fallback_nodes = max(0, space_w_int(row.get("nodes", 0), 0))
                            points = space_leaderboard_points_from_payload(board_type, file_payload, fallback_nodes)
                        else:
                            points = max(0, space_w_int(row.get("nodes", 0), 0))
                    except Exception:
                        points = max(0, space_w_int(row.get("nodes", 0), 0))
                    payload_cache[cache_key] = points
                else:
                    points = payload_cache[cache_key]
            if points <= 0:
                skipped += 1
                continue
            event_stamp = clean(row.get("at", "")) or clean(row.get("client_completed_at", "")) or now_stamp
            completed[completion_key] = {
                "lesson_id": canonical_id,
                "path": path_text,
                "points": points,
                "completed_at": event_stamp,
                "title": clean(row.get("title", ""))[:180],
            }
            user_row["total_points"] = max(0, space_w_int(user_row.get("total_points", 0), 0)) + points
            event_epoch = timestamp_to_epoch(event_stamp) or now_epoch
            for scope, bucket in current_buckets.items():
                if vocab_period_bucket(scope, event_epoch) != bucket:
                    continue
                scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
                if clean(scope_row.get("bucket", "")) != bucket:
                    scope_row = {"bucket": bucket, "points": 0, "updated_at": ""}
                scope_row["points"] = max(0, space_w_int(scope_row.get("points", 0), 0)) + points
                scope_row["updated_at"] = now_stamp
                user_row[scope] = scope_row
            user_row["updated_at"] = now_stamp
            users[username] = user_row
            board["users"] = users
            board["updated_at"] = now_stamp
            state["updated_at"] = now_stamp
            recorded += 1
            changed = True
        if changed:
            write_space_leaderboard_activity_state(state)
    return {"checked": checked, "recorded": recorded, "skipped": skipped}

def rescore_space_leaderboard_completions() -> dict:
    """Recompute points for every recorded space_p/space_s/space_l/space_q/space_w completion
    from its current payload so older node-based scores switch to the fair sentence/question count.
    Rebuilds total_points and the current day/week/month period points from each completion."""
    rescored = 0
    checked = 0
    missing = 0
    payload_cache: dict[str, int | None] = {}
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_space_leaderboard_activity_state()
        boards = state.get("boards") if isinstance(state.get("boards"), dict) else {}
        changed = False
        for board_type, board in boards.items():
            safe_type = normalize_space_leaderboard_type(board_type)
            if safe_type not in SPACE_LEADERBOARD_NODE_TYPES or not isinstance(board, dict):
                continue
            users = board.get("users") if isinstance(board.get("users"), dict) else {}
            now_epoch = time.time()
            now_stamp = utc_timestamp()
            current_buckets = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
            for username, row in users.items():
                if not isinstance(row, dict):
                    continue
                completed = row.get("completed") if isinstance(row.get("completed"), dict) else {}
                new_total = 0
                scope_sums = {"day": 0, "week": 0, "month": 0}
                for key, entry in completed.items():
                    if not isinstance(entry, dict):
                        continue
                    checked += 1
                    rel_path = clean_path_value(entry.get("path", ""))
                    old_points = max(0, space_w_int(entry.get("points", 0), 0))
                    cache_key = f"{safe_type}|{rel_path.lower()}"
                    if cache_key not in payload_cache:
                        points = None
                        try:
                            target = safe_server_data_path(rel_path, normalize_username(username), admin=is_admin_user(username))
                            if target.is_file():
                                file_payload, _structure_path = load_future_lesson_document(target)
                                points = space_leaderboard_points_from_payload(safe_type, file_payload, old_points)
                        except Exception:
                            points = None
                        payload_cache[cache_key] = points
                    else:
                        points = payload_cache.get(cache_key)
                    effective = points if (points is not None and points > 0) else old_points
                    if points is None or points <= 0:
                        missing += 1
                    elif points != old_points:
                        entry["points"] = points
                        rescored += 1
                        changed = True
                    new_total += effective
                    credited_buckets = space_leaderboard_entry_credited_buckets(entry)
                    for scope in ("day", "week", "month"):
                        if clean(credited_buckets.get(scope, "")) == current_buckets[scope]:
                            scope_sums[scope] += effective
                if max(0, space_w_int(row.get("total_points", 0), 0)) != new_total:
                    row["total_points"] = new_total
                    changed = True
                for scope in ("day", "week", "month"):
                    scope_row = row.get(scope) if isinstance(row.get(scope), dict) else {}
                    desired = scope_sums[scope]
                    same_bucket = clean(scope_row.get("bucket", "")) == current_buckets[scope]
                    current_pts = max(0, space_w_int(scope_row.get("points", 0), 0))
                    if desired > 0:
                        if not same_bucket or current_pts != desired:
                            row[scope] = {"bucket": current_buckets[scope], "points": desired, "updated_at": now_stamp}
                            changed = True
                    elif same_bucket and current_pts != 0:
                        row[scope] = {"bucket": current_buckets[scope], "points": 0, "updated_at": now_stamp}
                        changed = True
        if changed:
            state["updated_at"] = utc_timestamp()
            write_space_leaderboard_activity_state(state)
    return {"checked": checked, "rescored": rescored, "missing": missing}



def space_leaderboard_period_counts_for_user(username: str, board_type: str, state: dict | None = None) -> dict:
    username = normalize_username(username)
    safe_type = normalize_space_leaderboard_type(board_type)
    source = state if isinstance(state, dict) else load_space_leaderboard_activity_state()
    board = (source.get("boards") if isinstance(source.get("boards"), dict) else {}).get(safe_type)
    users = board.get("users") if isinstance(board, dict) and isinstance(board.get("users"), dict) else {}
    row = users.get(username) if isinstance(users.get(username), dict) else {}
    counts = {"total": max(0, space_w_int(row.get("total_points", 0), 0))}
    now_epoch = time.time()
    for scope in ("day", "week", "month"):
        scope_row = row.get(scope) if isinstance(row.get(scope), dict) else {}
        counts[scope] = max(0, space_w_int(scope_row.get("points", 0), 0)) if clean(scope_row.get("bucket", "")) == vocab_period_bucket(scope, now_epoch) else 0
    return counts
