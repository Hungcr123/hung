# Shared World Core Parts

These files are loaded by `FUTURE/server_parts/vocab_world_game/03_shared_world_core.py` into the shared Future server runtime namespace.

This is a nested transitional split. Keep the files ordered because later parts call helpers and constants defined by earlier parts. Do not import these files directly yet.

## Order

1. `01_state_city_npc.py`: Shared-world state cache, disk persistence, clamp helpers, and city NPC profile/seed helpers.
2. `02_profile_level_payload.py`: Player profile, leaderboard meta, QM City level meta, level maps, and public player payload.
3. `03_player_touch.py`: Player row creation/update, movement target persistence, and stale-player pruning.
4. `04_npc_bots.py`: NPC mode/settings/candidates, transition scheduling, snapshots, active battle users, and NPC movement tick.
5. `05_world_state_move.py`: Active battle pairs, public world state payload, and movement route flow.
6. `06_chat_validation.py`: English chat validation, display/target helpers, and NPC chat availability checks.
7. `07_npc_chat_replies.py`: NPC chat reply worker and reply scheduling.
8. `08_chat_action_constants.py`: Chat route flow, world action route flow, and shared battle/QM City constants.
9. `09_qm_city_skill_helpers.py`: QM City skill catalog/tree/stat helpers and training bonus-word helpers.

## Guardrail

Preserve state flush throttling, atexit flush registration, NPC online/battle filtering, chat validation rules, route-facing function names, and the battle/QM constants loaded after core but before battle/training loaders.
