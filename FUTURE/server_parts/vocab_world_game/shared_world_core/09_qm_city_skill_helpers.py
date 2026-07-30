def qm_city_training_slime_anchors() -> list[tuple[float, float]]:
    return [
        (0.25, 0.24), (0.45, 0.18), (0.66, 0.23), (0.86, 0.20), (0.34, 0.45),
        (0.55, 0.42), (0.77, 0.46), (0.24, 0.73), (0.48, 0.72), (0.74, 0.73),
    ]


def qm_city_training_skill_catalog() -> list[dict]:
    return [
        {"id": "tiny-fireball", "name": "Tiny Fireball", "unlock_level": 1, "multiplier": 1.00, "bonus": 0, "tone": "fireball"},
        {"id": "spark-needle", "name": "Spark Needle", "unlock_level": 2, "multiplier": 1.04, "bonus": 1, "tone": "spark"},
        {"id": "flame-arc", "name": "Flame Arc", "unlock_level": 2, "multiplier": 1.08, "bonus": 2, "tone": "flame"},
        {"id": "solar-pebble", "name": "Solar Pebble", "unlock_level": 2, "multiplier": 1.12, "bonus": 2, "tone": "solar"},
        {"id": "comet-swipe", "name": "Comet Swipe", "unlock_level": 3, "multiplier": 1.16, "bonus": 3, "tone": "comet"},
        {"id": "ion-lash", "name": "Ion Lash", "unlock_level": 3, "multiplier": 1.20, "bonus": 3, "tone": "ion"},
        {"id": "phoenix-chip", "name": "Phoenix Chip", "unlock_level": 4, "multiplier": 1.24, "bonus": 4, "tone": "phoenix"},
        {"id": "plasma-hop", "name": "Plasma Hop", "unlock_level": 4, "multiplier": 1.28, "bonus": 4, "tone": "plasma"},
        {"id": "sun-core", "name": "Sun Core", "unlock_level": 5, "multiplier": 1.34, "bonus": 5, "tone": "sun"},
        {"id": "flare-ring", "name": "Flare Ring", "unlock_level": 5, "multiplier": 1.40, "bonus": 5, "tone": "flare"},
        {"id": "star-ignition", "name": "Star Ignition", "unlock_level": 6, "multiplier": 1.47, "bonus": 6, "tone": "star"},
        {"id": "neon-inferno", "name": "Neon Inferno", "unlock_level": 6, "multiplier": 1.54, "bonus": 6, "tone": "neon"},
        {"id": "meteor-zip", "name": "Meteor Zip", "unlock_level": 7, "multiplier": 1.62, "bonus": 7, "tone": "meteor"},
        {"id": "dragon-breath", "name": "Dragon Breath", "unlock_level": 7, "multiplier": 1.70, "bonus": 7, "tone": "dragon"},
        {"id": "nova-button", "name": "Nova Button", "unlock_level": 8, "multiplier": 1.78, "bonus": 8, "tone": "nova"},
        {"id": "aurora-flame", "name": "Aurora Flame", "unlock_level": 8, "multiplier": 1.86, "bonus": 8, "tone": "aurora"},
        {"id": "quantum-blaze", "name": "Quantum Blaze", "unlock_level": 9, "multiplier": 1.95, "bonus": 9, "tone": "quantum"},
        {"id": "helios-pulse", "name": "Helios Pulse", "unlock_level": 9, "multiplier": 2.04, "bonus": 9, "tone": "helios"},
        {"id": "cosmic-fireline", "name": "Cosmic Fireline", "unlock_level": 10, "multiplier": 2.14, "bonus": 10, "tone": "cosmic"},
        {"id": "singularity-flare", "name": "Singularity Flare", "unlock_level": 10, "multiplier": 2.25, "bonus": 12, "tone": "singularity"},
    ]


def qm_city_training_unlocked_skills(level: int) -> list[dict]:
    safe_level = max(1, space_w_int(level, 1))
    unlocked = [dict(skill) for skill in qm_city_training_skill_catalog() if space_w_int(skill.get("unlock_level", 1), 1) <= safe_level]
    return unlocked or [dict(qm_city_training_skill_catalog()[0])]


def qm_city_training_public_skills(level: int, stats: dict | None = None) -> list[dict]:
    _safe_level = max(1, space_w_int(level, 1))
    data = stats if isinstance(stats, dict) else {}
    skill_levels = qm_city_training_normalize_skill_levels(data.get("skill_levels", {}))
    max_mana = max(1, space_w_int(data.get("max_mana", qm_city_training_max_mana_for_level(_safe_level)), qm_city_training_max_mana_for_level(_safe_level)))
    rows = []
    for skill in qm_city_training_skill_tree():
        skill_id = clean(skill.get("id", "")).lower()
        current_level = max(0, space_w_int(skill_levels.get(skill_id, skill.get("base_level", 0)), 0))
        max_level = max(current_level, space_w_int(skill.get("max_level", current_level), current_level))
        base_percent = space_w_int(skill.get("base_percent", 100), 100)
        per_level = space_w_int(skill.get("per_level_percent", 10), 10)
        damage_percent = base_percent + max(0, current_level - max(0, space_w_int(skill.get("base_level", 0), 0))) * per_level
        row = {key: skill.get(key) for key in ("id", "name", "tone", "description")}
        row.update({
            "level": current_level,
            "current_level": current_level,
            "currentLevel": current_level,
            "max_level": max_level,
            "maxLevel": max_level,
            "damage_percent": damage_percent,
            "damagePercent": damage_percent,
            "mana_cost": max(1, int(math.ceil(max_mana * float(skill.get("mana_cost_ratio", 1 / 3) or (1 / 3))))),
            "manaCost": max(1, int(math.ceil(max_mana * float(skill.get("mana_cost_ratio", 1 / 3) or (1 / 3))))),
            "radius_px": max(1, space_w_int(skill.get("radius_px", 400), 400)),
            "radiusPx": max(1, space_w_int(skill.get("radius_px", 400), 400)),
            "unlocked": current_level > 0,
            "can_upgrade": current_level < max_level,
            "canUpgrade": current_level < max_level,
        })
        rows.append(row)
    return rows


def qm_city_training_choose_skill(level: int) -> dict:
    unlocked = qm_city_training_unlocked_skills(level)
    recent = unlocked[-6:] if len(unlocked) > 6 else unlocked
    return dict(secrets.choice(recent))


def qm_city_training_skill_tree() -> list[dict]:
    return [
        {
            "id": "earthquake",
            "name": "Earthquake",
            "max_level": 10,
            "base_level": 1,
            "base_percent": 100,
            "per_level_percent": 10,
            "mana_cost_ratio": 1 / 3,
            "radius_px": 400,
            "tone": "earth",
            "description": "Jump, stomp the ground, crack the field, and damage all slimes inside 400px.",
        },
    ]


def qm_city_training_strength_for_level(level: int) -> int:
    safe_level = max(1, space_w_int(level, 1))
    return max(6, 6 + safe_level * 2)


def qm_city_training_max_hp_for_level(level: int) -> int:
    safe_level = max(1, space_w_int(level, 1))
    return 100 + (safe_level - 1) * 12


def qm_city_training_max_mana_for_level(level: int) -> int:
    safe_level = max(1, space_w_int(level, 1))
    return 60 + (safe_level - 1) * 6


def qm_city_training_normalize_skill_levels(source: object) -> dict:
    raw = source if isinstance(source, dict) else {}
    levels: dict[str, int] = {}
    for skill in qm_city_training_skill_tree():
        skill_id = clean(skill.get("id", "")).lower()
        if not skill_id:
            continue
        base_level = max(0, space_w_int(skill.get("base_level", 0), 0))
        max_level = max(base_level, space_w_int(skill.get("max_level", base_level), base_level))
        levels[skill_id] = max(base_level, min(max_level, space_w_int(raw.get(skill_id, base_level), base_level)))
    return levels


def qm_city_training_skill_spent_points(skill_levels: dict) -> int:
    spent = 0
    for skill in qm_city_training_skill_tree():
        skill_id = clean(skill.get("id", "")).lower()
        base_level = max(0, space_w_int(skill.get("base_level", 0), 0))
        spent += max(0, space_w_int((skill_levels or {}).get(skill_id, base_level), base_level) - base_level)
    return spent


def qm_city_training_bonus_words_from_row(row: object) -> int:
    data = row if isinstance(row, dict) else {}
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    return max(0, space_w_int(data.get("training_words", stats.get("training_words", 0)), 0))


def qm_city_training_bonus_words_for_user(username: str) -> int:
    username = normalize_username(username)
    if not username:
        return 0
    try:
        state = load_qm_city_training_state()
        users = state.get("users") if isinstance(state.get("users"), dict) else {}
        return qm_city_training_bonus_words_from_row(users.get(username))
    except Exception:
        return 0
