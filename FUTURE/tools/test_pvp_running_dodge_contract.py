import ast
import pathlib
import time


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_battle" / "07_answer_skill_forfeit.py"
FRONTEND = ROOT / "FUTURE" / "web" / "js_parts" / "03_world_motion_shared_state.js"


def functions_from(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), "exec"), namespace)


class AlwaysDodgeSecrets:
    @staticmethod
    def randbelow(_limit):
        return 0


def main():
    namespace = {
        "time": time,
        "secrets": AlwaysDodgeSecrets,
        "clean": lambda value="": str(value or "").strip(),
        "normalize_username": lambda value="": str(value or "").strip().lower(),
        "utc_timestamp": lambda: "2026-08-17T00:00:00Z",
        "shared_world_battle_other": lambda battle, username: next(
            item for item in battle["players"] if item != username
        ),
        "shared_world_battle_apply_damage": lambda *_args: (_ for _ in ()).throw(
            AssertionError("dodged Nộ must not apply damage")
        ),
        "shared_world_battle_check_hp": lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("dodged Nộ must not finish/check HP")
        ),
    }
    functions_from(
        SOURCE,
        {
            "shared_world_battle_target_running",
            "shared_world_battle_roll_running_dodge",
            "shared_world_battle_dodge_log_row",
            "shared_world_battle_apply_skill_locked",
        },
        namespace,
    )
    battle = {
        "players": ["hung", "quynh"],
        "mp": {"hung": 100, "quynh": 0},
        "hp": {"hung": 100, "quynh": 100},
        "buffs": {},
        "movement": {
            "quynh": {
                "distance": 0.12,
                "running_until_epoch": time.time() + 2.0,
            }
        },
        "log": [],
    }
    basic = namespace["shared_world_battle_roll_running_dodge"](battle, "quynh", "basic_attack")
    assert basic and basic["chance"] == 0.5 and basic["side"] == "left"
    assert namespace["shared_world_battle_apply_skill_locked"](battle, "hung", "ultimate") is True
    assert battle["hp"]["quynh"] == 100
    assert battle["mp"]["hung"] == 0
    row = battle["log"][-1]
    assert row["type"] == "miss" and row["dodged"] is True and row["effect"] == "ultimate"
    assert row["dodge_chance"] == 0.2
    assert row["impact_offset_side"] in {"left", "right"}
    source = SOURCE.read_text(encoding="utf-8")
    frontend = FRONTEND.read_text(encoding="utf-8")
    assert "shared_world_battle_roll_running_dodge(battle, opponent, attack_effect)" in source
    assert "shared_world_battle_roll_running_dodge(battle, opponent, \"ultimate\")" in source
    assert "running_until_epoch" in source and "distance_px" in source
    assert "impact_offset_side" in frontend and "ft-world-battle-character-impact" in frontend
    assert "correct: true," in frontend and "preview_only: Boolean(missed)" in frontend
    assert "triggerSharedWorldBattleProjectile(attackerNode, targetNode, attackerGender, ultimateCast, delay, true, missMeta)" not in frontend
    assert "sharedWorldBattleMissPoint" in frontend and "showSharedWorldBattleMissLabelAtPoint" in frontend
    assert 'hitTarget && !(event.missed || event.dodged || event.dodge)' in frontend
    assert 'target && !(event.missed || event.dodged || event.dodge)' in frontend
    assert 'triggerSharedWorldTrainingEarthquake(trainingEvent)' in frontend
    assert 'triggerSharedWorldTrainingSkill(trainingEvent, targetNode, () => {' in frontend
    assert 'visualOwned: false' in frontend
    assert 'triggerSharedWorldBattleCast(self, opponent, "basic_attack", 10, false' not in frontend
    assert "queueSharedWorldBattleVisualTimeout(() => showSharedWorldBattleMissLabelAtPoint(missPoint)" not in frontend
    print("pvp_running_dodge_contract=ok basic=50 ultimate=20 hp_unchanged miss_offset=server")


if __name__ == "__main__":
    main()
