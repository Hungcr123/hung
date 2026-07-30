# AI/Language Runtime Parts

These files are loaded by `FUTURE/server_parts/04_ai_language_agents.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the load order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_chat_translation_voice.py`
   - Builder imports, chat translation helpers, chat voice catalog, and queued chat TTS.

2. `02_gemini_keys_models.py`
   - Gemini API key loading, model candidate discovery, cooldowns, error classification, and one-shot model requests.

3. `03_ai_agent_requests.py`
   - Loader for AI-agent sanitizer/context, translation/English/Vietnamese replies, QM City NPC replies, PDF explanations, notice assembly, Space_P follow-ups, and shared AI-agent state.

4. `04_ai_agent_history.py`
   - Per-user AI agent history paths, normalization, read/write/list/save/remove helpers.

5. `05_word_agent_core_history.py`
   - Word Agent keying, examples/detail normalization, phrase extras, and word-agent history cache.

6. `06_phonetic_ipa.py`
   - Phonetic/IPA cache, dictionary lookup, phonemizer fallback, warmup, and IPA maps.

7. `07_word_agent_gemini.py`
   - Word Agent history save and Gemini Vietnamese word/phrase explanation requests.

## Deeper Splits

- `ai_agent_requests/`: ordered source parts loaded by `03_ai_agent_requests.py`.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve Gemini key cooldown behavior and quota fallbacks; route handlers rely on those user-facing error messages.
- Preserve Word Agent and phonetic cache schemas because the frontend and QmDict/vocabulary flows read those structures.
