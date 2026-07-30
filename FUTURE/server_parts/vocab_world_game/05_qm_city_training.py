# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This loader keeps QM City training split into ordered domain parts.

QM_CITY_TRAINING_PARTS_ROOT = VOCAB_WORLD_GAME_PARTS_ROOT / "qm_city_training"
QM_CITY_TRAINING_PART_FILES = (
    "01_state_stats.py",
    "02_question_pool.py",
    "03_question_pick.py",
    "04_arena_lifecycle.py",
    "05_select_answer.py",
    "06_upgrade_skill_reset.py",
)


def _load_qm_city_training_part(part_name: str) -> None:
    part_path = QM_CITY_TRAINING_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _qm_city_training_part_name in QM_CITY_TRAINING_PART_FILES:
    _load_qm_city_training_part(_qm_city_training_part_name)
del _qm_city_training_part_name
