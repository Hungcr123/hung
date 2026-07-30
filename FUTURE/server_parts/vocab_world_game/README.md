# Vocabulary World And Game Parts

These files are loaded by `FUTURE/server_parts/09_vocab_world_game.py` into the shared Future server runtime namespace.

This is a nested transitional split. The files are grouped by behavior and loaded in order, but they still share globals with the rest of the server. Do not import them directly yet.

## Order

1. `01_leaderboard_period_npc.py`: leaderboard period state, NPC_TOP image/profile/session generation, NPC activity buffs.
2. `02_leaderboard_social_chat.py`: leaderboard rewards/viewers/social reactions/statuses/world chat.
3. `03_shared_world_core.py`: loader for `shared_world_core/` player state, NPC movement/chat, world actions, battle/QM constants.
4. `04_shared_world_battle.py`: loader for `shared_world_battle/` battle state, invites, turns, answers, skills, forfeit flow.
5. `05_qm_city_training.py`: loader for `qm_city_training/` training state, questions, slimes, skills, arena actions.
6. `06_leaderboard_rewards_rank.py`: period settlement, reward claims, rank movement, `vocabulary_leaderboard`.
7. `07_game_rooms.py`: vocabulary battle room creation, joining, word selection, ready/cancel flow.

## Next Step

The shared world core, battle, and QM City training flows are now split behind small loaders. Next candidates in this folder are `06_leaderboard_rewards_rank.py`, `01_leaderboard_period_npc.py`, and `02_leaderboard_social_chat.py`, but only split them after adding targeted leaderboard/reward smoke checks.
