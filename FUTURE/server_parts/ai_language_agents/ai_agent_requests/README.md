# AI Agent Request Parts

These files are loaded by `FUTURE/server_parts/ai_language_agents/03_ai_agent_requests.py` into the shared Future server runtime namespace.

This is a deeper transitional split. Keep the load order stable until the request helpers are converted into explicit importable modules.

## Load Order

1. `01_sanitize_context.py`
   - Vietnamese/English reply sanitizers, token estimate, runtime context scrubber, and Space_V/Space_P/Space_Q context checks.

2. `02_translation_english_reply.py`
   - Gemini Vietnamese translation request and main English AI-agent reply request.

3. `03_qm_city_npc_reply.py`
   - QM-City NPC Gemini chat-bubble reply request.

4. `04_vietnamese_reply.py`
   - Vietnamese AI-agent reply request using English answer/context as reference.

5. `05_pdf_explanation.py`
   - Ghost Eye PDF/Text-to-Explore Vietnamese explanation request.

6. `06_notice_followup.py`
   - AI-agent notice assembly, voice payload, metrics, and Space_P follow-up question generation.

7. `07_shared_agent_state.py`
   - Shared locks and caches used by AI-agent history, Word Agent history, and phonetic IPA parts loaded after this request loader.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve Gemini fallback/cooldown/quota behavior exactly; prompt helpers depend on consistent user-facing errors.
- Preserve hidden-answer safety prompts and context scrubber rules. Do not move blocked answer/solution filtering into route code.
- Keep `07_shared_agent_state.py` last inside this loader because later AI-language parts expect those locks/caches to exist.
