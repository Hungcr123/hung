# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

VOCAB_WORLD_GAME_PARTS_ROOT = SERVER_PARTS_ROOT / "vocab_world_game"
VOCAB_WORLD_GAME_PART_FILES = (
    "01_leaderboard_period_npc.py",
    "02_leaderboard_social_chat.py",
    "03_shared_world_core.py",
    "04_shared_world_battle.py",
    "05_qm_city_training.py",
    "06_leaderboard_rewards_rank.py",
    "07_game_rooms.py",
)


def _load_vocab_world_game_part(part_name: str) -> None:
    part_path = VOCAB_WORLD_GAME_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _vocab_world_game_part_name in VOCAB_WORLD_GAME_PART_FILES:
    _load_vocab_world_game_part(_vocab_world_game_part_name)
del _vocab_world_game_part_name
