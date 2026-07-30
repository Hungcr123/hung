# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

AI_AGENT_REQUESTS_PARTS_ROOT = AI_LANGUAGE_AGENTS_PARTS_ROOT / "ai_agent_requests"
AI_AGENT_REQUESTS_PART_FILES = (
    "01_sanitize_context.py",
    "02_translation_english_reply.py",
    "03_qm_city_npc_reply.py",
    "04_vietnamese_reply.py",
    "05_pdf_explanation.py",
    "06_notice_followup.py",
    "07_shared_agent_state.py",
)


def _load_ai_agent_requests_part(part_name: str) -> None:
    part_path = AI_AGENT_REQUESTS_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _ai_agent_requests_part_name in AI_AGENT_REQUESTS_PART_FILES:
    _load_ai_agent_requests_part(_ai_agent_requests_part_name)
del _ai_agent_requests_part_name
