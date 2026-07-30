# Vocabulary Build/Status Runtime Parts

These files are loaded by `FUTURE/server_parts/10_vocab_build_status.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the file order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_lesson_vocab_helpers.py`
   - Extracts lesson English text from Space_W/Space_P payloads.
   - Resolves QmDict vocabulary entries and converts entries into UI summaries.
   - Builds completed-progress summaries used by vocabulary missions.

2. `02_space_w_vocab_missions.py`
   - Builds Space_W/Space_P vocabulary context.
   - Tracks vocabulary-build jobs and snapshots.
   - Scans lessons, writes mission files, and archives completed mission vocab files.

3. `03_status_page.py`
   - Serves the Future server status dashboard HTML/CSS/JS through `status_page()`.
   - This file is still intentionally large because the dashboard markup and browser script are tightly embedded in one f-string.

## Guardrails

- Preserve the runtime namespace contract while this folder is transitional.
- Keep vocabulary mission behavior registry-backed; do not mark already learned words as new mission words.
- Do not split `03_status_page.py` into static template/assets until the status routes, injected server values, and browser-side handlers are mapped in a separate pass.
