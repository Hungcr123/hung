# Shared World Battle Parts

These files are loaded by `FUTURE/server_parts/vocab_world_game/04_shared_world_battle.py` into the shared Future server runtime namespace.

This is a nested transitional split. Keep the files ordered because later parts call helpers defined by earlier parts. Do not import these files directly yet.

## Order

1. `01_state_profile.py`: Battle state cache, disk persistence, profile and invite public projection.
2. `02_vocab_questions.py`: Dictionary lookup, vocab pool, asked-word history, and battle question selection.
3. `03_answer_rules.py`: Answer matching plus Vietnamese token and score helpers shared with QM City training.
4. `04_battle_engine.py`: Battle ids, turns, answer reveal, crystal transfer, damage, finish, and HP checks.
5. `05_public_state_npc.py`: Public question/log/payload, timeout advance, NPC bot tick, prune, and state-for-user.
6. `06_invite_respond.py`: Invite creation, auto battle creation, accept/decline response flow.
7. `07_answer_skill_forfeit.py`: Answer application, skill application, skill route flow, and forfeit flow.

## Guardrail

Preserve delayed state flushing, atexit flush registration, NPC battle automation, crystal transfer side effects, and all public function names consumed by HTTP routes and QM City training.
