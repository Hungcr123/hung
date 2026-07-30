# Loaded by FUTURE.server_parts.ai_language_agents.03_ai_agent_requests into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def sanitize_ai_agent_vietnamese_reply(text: str, limit: int = 9000) -> str:
    cleaned = html.unescape(str(text or ""))
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = re.sub(r"[*_`~#\[\]{}<>|\\/]+", " ", cleaned)
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    lines = []
    for line in cleaned.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned[:limit].strip()


def normalize_ai_agent_answer_mode(value: object) -> str:
    mode = clean(value).lower().replace("-", "_").replace(" ", "_")
    if mode in {"detail", "detailed", "long", "deep", "full", "bullet", "bullets"}:
        return "detailed"
    return "spoken"


def sanitize_ai_agent_english_reply(text: str, limit: int = 1800, structured: bool = False) -> str:
    cleaned = html.unescape(str(text or ""))
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or ch == "\t" or 32 <= ord(ch) <= 126)
    if structured:
        cleaned = re.sub(r"[*_`~#\[\]{}<>|\\/]+", " ", cleaned)
        cleaned = re.sub(r"[^\w\s.,!?';:\"()%-]", " ", cleaned)
        lines = []
        for line in cleaned.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                lines.append(line)
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    else:
        cleaned = re.sub(r"^[\s>*#`~_\-\u2022]+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"[*_`~#\[\]{}<>|\\/]+", " ", cleaned)
        cleaned = re.sub(r"[^\w\s.,!?';:\"()%-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit].strip()


def estimate_ai_agent_token_count(text: str) -> int:
    raw = clean(text)
    if not raw:
        return 0
    words = re.findall(r"[A-Za-z0-9']+|[^\sA-Za-z0-9]", raw)
    if words:
        return max(1, int(math.ceil(len(words) * 1.18)))
    return max(1, int(math.ceil(len(raw) / 4)))


def ai_agent_scrub_runtime_context(value: object, depth: int = 0) -> object:
    if depth > 4:
        return ""
    blocked_parts = ("answer", "correct", "solution", "expected", "target", "choice", "option")
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = clean(raw_key)
            if not key:
                continue
            key_l = key.lower()
            if any(part in key_l for part in blocked_parts):
                continue
            result[key[:80]] = ai_agent_scrub_runtime_context(raw_value, depth + 1)
        return result
    if isinstance(value, list):
        return [ai_agent_scrub_runtime_context(item, depth + 1) for item in value[:18]]
    if isinstance(value, str):
        return lesson_task_notice_text(value, limit=1200)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return lesson_task_notice_text(str(value), limit=600)


def ai_agent_context_hints(context: dict | None = None) -> tuple[str, str, str, str]:
    source = context if isinstance(context, dict) else {}
    lesson_hint = lesson_task_notice_text(source.get("lesson", source.get("file", "")), limit=420)
    space_hint = lesson_task_notice_text(source.get("space", source.get("process", "")), limit=80)
    answer_policy = lesson_task_notice_text(source.get("answer_policy", ""), limit=520)
    runtime_context = source.get("runtime") if isinstance(source.get("runtime"), dict) else {}
    runtime_hint = ""
    if runtime_context:
        try:
            runtime_hint = lesson_task_notice_text(
                json.dumps(ai_agent_scrub_runtime_context(runtime_context), ensure_ascii=False, indent=2),
                limit=2600,
            )
        except Exception:
            runtime_hint = ""
    return lesson_hint, space_hint, answer_policy, runtime_hint


def ai_agent_allows_current_vocabulary_word(context: dict | None = None) -> bool:
    source = context if isinstance(context, dict) else {}
    runtime = source.get("runtime") if isinstance(source.get("runtime"), dict) else {}
    space = clean(source.get("space", source.get("process", ""))).lower()
    activity = clean(runtime.get("activity", "")).lower()
    phase = clean(runtime.get("phase", "")).lower()
    allowed = bool(runtime.get("allow_current_vocabulary_word"))
    return bool(
        allowed
        and (space == "space_v" or "space_v" in activity or "vocabulary" in activity)
        and phase in {"drill", "shuffle"}
    )


def ai_agent_is_space_p_context(context: dict | None = None) -> bool:
    source = context if isinstance(context, dict) else {}
    runtime = source.get("runtime") if isinstance(source.get("runtime"), dict) else {}
    space = clean(source.get("space", source.get("process", ""))).lower()
    activity = clean(runtime.get("activity", "")).lower()
    return bool(space == "space_p" or "space_p" in activity or "paragraph rewrite" in activity)


def ai_agent_is_space_q_context(context: dict | None = None) -> bool:
    source = context if isinstance(context, dict) else {}
    runtime = source.get("runtime") if isinstance(source.get("runtime"), dict) else {}
    space = clean(source.get("space", source.get("process", ""))).lower()
    activity = clean(runtime.get("activity", "")).lower()
    return bool(space == "space_q" or "space_q" in activity or "question practice" in activity)
