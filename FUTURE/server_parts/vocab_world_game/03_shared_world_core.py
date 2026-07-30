# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This loader keeps shared-world core split into ordered domain parts.

SHARED_WORLD_CORE_PARTS_ROOT = VOCAB_WORLD_GAME_PARTS_ROOT / "shared_world_core"
SHARED_WORLD_CORE_PART_FILES = (
    "01_state_city_npc.py",
    "02_profile_level_payload.py",
    "03_player_touch.py",
    "04_npc_bots.py",
    "05_world_state_move.py",
    "06_chat_validation.py",
    "07_npc_chat_replies.py",
    "08_chat_action_constants.py",
    "09_qm_city_skill_helpers.py",
)


def _load_shared_world_core_part(part_name: str) -> None:
    part_path = SHARED_WORLD_CORE_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _shared_world_core_part_name in SHARED_WORLD_CORE_PART_FILES:
    _load_shared_world_core_part(_shared_world_core_part_name)
del _shared_world_core_part_name
