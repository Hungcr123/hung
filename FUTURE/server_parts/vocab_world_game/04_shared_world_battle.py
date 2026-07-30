# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This loader keeps shared-world battle split into ordered domain parts.

SHARED_WORLD_BATTLE_PARTS_ROOT = VOCAB_WORLD_GAME_PARTS_ROOT / "shared_world_battle"
SHARED_WORLD_BATTLE_PART_FILES = (
    "01_state_profile.py",
    "02_vocab_questions.py",
    "03_answer_rules.py",
    "04_battle_engine.py",
    "05_public_state_npc.py",
    "06_invite_respond.py",
    "07_answer_skill_forfeit.py",
)


def _load_shared_world_battle_part(part_name: str) -> None:
    part_path = SHARED_WORLD_BATTLE_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _shared_world_battle_part_name in SHARED_WORLD_BATTLE_PART_FILES:
    _load_shared_world_battle_part(_shared_world_battle_part_name)
del _shared_world_battle_part_name
