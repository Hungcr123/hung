# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

AI_AGENT_HISTORY_LOCK = threading.RLock()
WORD_AGENT_HISTORY_LOCK = threading.RLock()
PHONETIC_IPA_LOCK = threading.RLock()
WORD_AGENT_HISTORY_CACHE = {
    "mtime_ns": -2,
    "payload": {"version": 1, "history": [], "updated_at": ""},
    "rows": [],
    "by_key": {},
    "latest_by_key": {},
}
PHONETIC_IPA_CACHE = {
    "mtime_ns": -2,
    "payload": {"version": 1, "items": {}, "updated_at": ""},
    "items": {},
}
PHONETIC_IPA_WARMING_KEYS: set[str] = set()
