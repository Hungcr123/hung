# Progress, Inventory, And Vocabulary Parts

These files are loaded by `FUTURE/server_parts/08_progress_inventory_vocab.py` into the shared Future server runtime namespace.

This is a nested transitional split. The files are grouped by behavior and loaded in order, but they still share globals with the rest of the server. Do not import them directly yet.

## Order

1. `01_space_w_progress.py`: Space_W progress save/read/clear and speak-skip requests.
2. `02_space_q_progress.py`: Space_Q progress save/read/clear.
3. `03_space_v_progress.py`: Space_V progress save/read/clear and terminal completion repair.
4. `04_space_p_pdf_progress.py`: Space_P and Space_PDF progress save/read/clear.
5. `05_inventory_keyboard_assets.py`: inventory, shared-world keyboard pass, server assets, QMLearn sound reads.
6. `06_vocab_registry_core.py`: vocabulary registry paths, QmDict reconciliation, Space_V file vocabulary stats.
7. `07_main_vocab_sync.py`: sync between Future vocabulary registry and main/QMLearn vocabulary progress.
8. `08_vocab_recording_summary.py`: record learned vocabulary items and build `user_vocabulary_registry_summary`.
9. `09_vocab_period_stats.py`: vocabulary period buckets and event timestamps used by leaderboards.

## Guardrails

`06_vocab_registry_core.py` and `08_vocab_recording_summary.py` support the server-backed Lexicon Memory panel and NEW/OLD card state. Preserve the current behavior: registry-backed, no current-answer leakage, and probe-only side memory UI is enforced by the frontend.
