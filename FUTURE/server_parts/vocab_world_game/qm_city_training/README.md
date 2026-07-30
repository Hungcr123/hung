# QM City Training Parts

These files are loaded by `FUTURE/server_parts/vocab_world_game/05_qm_city_training.py` into the shared Future server runtime namespace.

This is a transitional split. Keep these files ordered and do not import them directly yet.

## Order

1. `01_state_stats.py`: Training state persistence, level/stat normalization, and public stat payload.
2. `02_question_pool.py`: Sentence/word prompt pools, question kind normalization, and generated question variants.
3. `03_question_pick.py`: Question selection and public question projection.
4. `04_arena_lifecycle.py`: Slime creation, arena rebalance/tick/new/user/public state, and selection helpers.
5. `05_select_answer.py`: Slime selection and answer/hit/reward flow.
6. `06_upgrade_skill_reset.py`: Stat upgrades, skill casting, and reset flow.

## Guardrails

- Preserve all public function names beginning with `qm_city_training_`.
- Preserve shared state locks and file writes through the existing helpers.
- Keep question kind order stable; the frontend depends on fixed slime/question slots.
- After edits, run compile/import and server 2 smoke tests.
