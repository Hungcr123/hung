# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

AI_LANGUAGE_AGENTS_PARTS_ROOT = SERVER_PARTS_ROOT / "ai_language_agents"
AI_LANGUAGE_AGENTS_PART_FILES = (
    "01_chat_translation_voice.py",
    "02_gemini_keys_models.py",
    "03_ai_agent_requests.py",
    "04_ai_agent_history.py",
    "05_word_agent_core_history.py",
    "06_phonetic_ipa.py",
    "07_word_agent_gemini.py",
)


def _load_ai_language_agents_part(part_name: str) -> None:
    part_path = AI_LANGUAGE_AGENTS_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _ai_language_agents_part_name in AI_LANGUAGE_AGENTS_PART_FILES:
    _load_ai_language_agents_part(_ai_language_agents_part_name)
del _ai_language_agents_part_name
