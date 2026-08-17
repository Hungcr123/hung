from pathlib import Path
import importlib.util

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "FUTURE" / "web"
JS = ROOT / "FUTURE" / "web" / "js_parts" / "03_world_motion_shared_state.js"
WORLD_JS = ROOT / "FUTURE" / "web" / "js_parts" / "02_ai_agent_world_training.js"
SCREEN_JS = ROOT / "FUTURE" / "web" / "js_parts" / "04_world_screen_paint.js"
LAYOUT_JS = ROOT / "FUTURE" / "web" / "js_parts" / "05_screen_motion_layout.js"
CSS = ROOT / "FUTURE" / "web" / "css_parts" / "03_chat_stream_screen.css"
CONTROLS_CSS = ROOT / "FUTURE" / "web" / "css_parts" / "02_auth_profile_controls.css"
HTML = ROOT / "FUTURE" / "web" / "future_split.html"
SKILL_HELPERS = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_core" / "09_qm_city_skill_helpers.py"
TRAINING_SKILL = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "qm_city_training" / "06_upgrade_skill_reset.py"
PLAYER_TOUCH = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_core" / "03_player_touch.py"
PLAYER_PAYLOAD = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_core" / "02_profile_level_payload.py"
BATTLE_PAYLOAD = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_battle" / "05_public_state_npc.py"
BATTLE_INVITE = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_battle" / "06_invite_respond.py"
BATTLE_ACTION = ROOT / "FUTURE" / "server_parts" / "vocab_world_game" / "shared_world_battle" / "07_answer_skill_forfeit.py"
BUILDER = ROOT / "FUTURE" / "tools" / "build_qm_city_character_scorpio.py"


# Added 2026-08-16: assert every normalized frame remains grounded inside its cell.
def grounded_frames(path: Path, cell_width: int, frame_count: int, expected_bottom: int) -> bool:
    with Image.open(path).convert("RGBA") as atlas:
        if atlas.width != cell_width * frame_count:
            return False
        for index in range(frame_count):
            frame = atlas.crop((index * cell_width, 0, (index + 1) * cell_width, atlas.height))
            bbox = frame.getchannel("A").point(lambda alpha: 255 if alpha >= 12 else 0).getbbox()
            if not bbox or bbox[3] != expected_bottom:
                return False
    return True


# Added 2026-08-16: verify Nộ keeps one ground origin while frames 3-5 retain intentional flight.
def ultimate_ground_anchor_contract() -> bool:
    spec = importlib.util.spec_from_file_location("scorpio_asset_builder", BUILDER)
    if not spec or not spec.loader:
        return False
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    destination = builder.ULTIMATE_DESTINATION_GROUND
    scale = builder.ULTIMATE_FIXED_SCALE
    anchors = builder.ULTIMATE_SOURCE_GROUND_ANCHORS
    if destination != (320, 483) or scale != 0.62 or len(anchors) != 6:
        return False
    if not (anchors[2][1] > 669 and anchors[3][1] > 548 and anchors[4][1] > 579):
        return False
    with Image.open(WEB / "character_scorpio_ultimate_atlas.png").convert("RGBA") as atlas:
        if atlas.size != (640 * 6, 640):
            return False
        anchors_stable = all(
            round(destination[0] - source_x * scale) + round(source_x * scale) == destination[0]
            and round(destination[1] - source_y * scale) + round(source_y * scale) == destination[1]
            for source_x, source_y in anchors
        )
        frame_five = atlas.crop((640 * 4, 0, 640 * 5, 640))
        frame_five_bbox = frame_five.getchannel("A").point(lambda alpha: 255 if alpha >= 12 else 0).getbbox()
        return anchors_stable and bool(frame_five_bbox and frame_five_bbox[1] > 0 and frame_five_bbox[3] < 640)


# Added 2026-08-16: protect the shared test/real Scorpio damage pipeline and asset set.
def main() -> int:
    js = JS.read_text(encoding="utf-8")
    world_js = WORLD_JS.read_text(encoding="utf-8")
    screen_js = SCREEN_JS.read_text(encoding="utf-8")
    layout_js = LAYOUT_JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    controls_css = CONTROLS_CSS.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    skill_helpers = SKILL_HELPERS.read_text(encoding="utf-8")
    training_skill = TRAINING_SKILL.read_text(encoding="utf-8")
    player_touch = PLAYER_TOUCH.read_text(encoding="utf-8")
    player_payload = PLAYER_PAYLOAD.read_text(encoding="utf-8")
    battle_payload = BATTLE_PAYLOAD.read_text(encoding="utf-8")
    battle_invite = BATTLE_INVITE.read_text(encoding="utf-8")
    battle_action = BATTLE_ACTION.read_text(encoding="utf-8")
    checks = {
        "selector": '<option value="scorpio">Cung Bọ Cạp</option>' in html,
        "local_refresh_restore": "future_qm_city_hung_character_v1" in world_js and "readSharedWorldAdminCharacterPreview()" in world_js and "window.localStorage.setItem(SHARED_WORLD_ADMIN_CHARACTER_STORAGE_KEY" in js,
        "city_character_renderer": 'node.classList.toggle("is-character-scorpio", scorpio);' in js and 'node.dataset.characterId = scorpio ? "character_scorpio"' in js,
        "battle_character_renderer": 'node.classList.toggle("is-character-scorpio", genderKey === "scorpio");' in js and 'genderKey === "scorpio"' in js,
        "battle_square_stand_ratio": ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-training-cast) .ft-world-character" in css and "width: 128px;" in css and "height: 128px;" in css,
        "battle_idle_direction_lock": all(marker in css for marker in (
            ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast).is-facing-down",
            ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast).is-facing-right",
            ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast).is-facing-left",
            ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast).is-facing-up",
        )),
        "ground_shadow_depth_order": "refreshSharedWorldBattleCharacterDepthOrder" in js and "refreshSharedWorldCharacterDepthOrder" in js and "dataset.worldDepthY" in js and "12 + index" in js,
        "shared_avatar_renderer": 'host.classList.toggle("has-scorpio-training-controls", genderKey === "scorpio");' in world_js,
        "shared_cast_function": "triggerSharedWorldScorpioBasicSkill(event, target, onImpact)" in js,
        "test_real_shared_damage_pipeline": "if (row.client_preview) {" in js and "triggerSharedWorldTrainingSkill(row, target, () => {" in js and "else triggerSharedWorldTrainingSkill(row, target, showHitFeedback);" in js,
        "pvp_shared_scorpio_cast": 'attackerGender === "scorpio"' in js and "triggerSharedWorldTrainingSkill(trainingEvent, targetNode, () => {" in js,
        "random_three_basics": "1 + Math.floor(Math.random() * 3)" in js,
        "release_frames": "const releaseFrames = { 1: 6, 2: 5, 3: 6 };" in js,
        "homing_frame_switch": 'arrow.classList.add("is-frame-two")' in js,
        "projectile_frame_one_hold": "const frameOneHoldMs = 260;" in js and "if (!frameTwo) {" in js and 'stage: "projectile-frame-2"' in js,
        "projectile_frame_one_clear_of_actor": "const frameOneSpawnDistance = 228;" in js and "spawnDistance: frameOneSpawnDistance" in js,
        "damage_after_burn": "finishSharedWorldTrainingImpactRender(onImpact);" in js,
        "scorpio_runtime_branch": 'classList.contains("is-character-scorpio")' in js,
        "city_scorpio_hud_visible": ".ft-world-card.has-scorpio-training-controls .ft-world-training-skill-dock" in controls_css and "display: grid;" in controls_css,
        "training_avatar_ignores_closed_battle": 'clean(battle.status) === "active" && battleOpen && worldBattleLeft' in world_js,
        "training_avatar_not_cleared_by_battle_poll": 'const wasBattleDock = worldTrainingSkillDock.classList.contains("is-pvp-training-dock")' in js and 'if (!wasBattleDock) return;' in js,
        "character_switch_ram_presence": "SHARED_WORLD_CHARACTER_KIND_CACHE[username] = next_character_kind" in player_touch and '"character_kind": character_kind' in player_payload and "payload.character_kind = normalizeSharedWorldCharacterKind" in layout_js and "sharedWorldObstacleEditorAllowed()" in layout_js,
        "character_switch_remote_battle": 'profile["character_kind"] = live_character_kind' in battle_payload and "profile.character_kind || profile.characterKind" in js,
        "battle_poll_stays_hot": "if (sharedWorldBattlePollingTimer) return;" in screen_js and "startSharedWorldBattlePolling();" in js,
        "finished_battle_does_not_hide_invite": 'const inviteBlockingBattle = activeBattle && clean(battle.status) === "active";' in js and "!inviteBlockingBattle" in js,
        "new_battle_handoff_accepts_new_id": "const lifecycleBattleId = responseBattleId && responseBattleId !== requestBattleId" in js and 'traceSharedWorldBattleLifecycle("new-battle-handoff"' in js,
        "battle_two_client_ready_gate": 'battle["phase"] = "waiting_ready"' in battle_invite and "shared_world_battle_all_players_ready" in battle_payload and 'client_ready = bool(source_payload.get("client_ready"' in battle_action and "ensureSharedWorldBattleClientReady" in js,
        "battle_damage_waits_for_both": battle_action.count("Waiting for both players to enter the Battle arena.") >= 3 and 'result["can_answer"] = shared_world_battle_all_players_ready(battle)' in battle_payload,
        "battle_actor_revives_active_node": 'clean(battle.status) === "active" && hp > 0' in js and 'node.classList.remove("is-battle-defeated")' in js,
        "admin_test_cleanup": '"is-scorpio-basic-cast"' in js and "const visualGapMs = scorpioBasic ? 3400" in js,
        "stand_grounded": grounded_frames(WEB / "character_scorpio_stand_atlas.png", 256, 3, 256),
        "run_down_grounded": grounded_frames(WEB / "character_scorpio_run_down_atlas.png", 256, 6, 256),
        "run_side_grounded": grounded_frames(WEB / "character_scorpio_run_side_atlas.png", 256, 5, 256),
        "run_up_grounded": grounded_frames(WEB / "character_scorpio_run_up_atlas.png", 256, 6, 256),
        "weapon_stand_grounded": grounded_frames(WEB / "character_scorpio_weapon_stand_atlas.png", 256, 3, 256),
        "weapon_run_down_grounded": grounded_frames(WEB / "character_scorpio_weapon_run_down_atlas.png", 256, 6, 256),
        "weapon_run_side_grounded": grounded_frames(WEB / "character_scorpio_weapon_run_side_atlas.png", 256, 6, 256),
        "weapon_run_up_grounded": grounded_frames(WEB / "character_scorpio_weapon_run_up_atlas.png", 256, 8, 256),
        "basic_one_grounded": grounded_frames(WEB / "character_scorpio_basic_1_atlas.png", 384, 8, 256),
        "basic_two_grounded": grounded_frames(WEB / "character_scorpio_basic_2_atlas.png", 384, 6, 256),
        "basic_three_grounded": grounded_frames(WEB / "character_scorpio_basic_3_atlas.png", 384, 7, 256),
        "burn_css": "ftWorldTrainingScorpioBurn 780ms steps(6, end) both" in css,
        "left_flip": "is-character-scorpio.is-moving:not(.is-training-cast).is-facing-left" in css and "scaleX(-1)" in css,
        "basic_source_faces_left": "is-scorpio-basic-cast.is-scorpio-cast-right .ft-world-character" in css and "transform: scaleX(-1) scale(var(--scorpio-basic-scale));" in css,
        "stand_direction_rows": all(marker in css for marker in (
            "not(.is-moving):not(.is-training-cast).is-facing-down",
            "not(.is-moving):not(.is-training-cast).is-facing-right",
            "not(.is-moving):not(.is-training-cast).is-facing-left",
            "not(.is-moving):not(.is-training-cast).is-facing-up",
        )),
        "run_direction_rows": all(marker in css for marker in (
            "character_scorpio_run_down_atlas.png",
            "character_scorpio_run_side_atlas.png",
            "character_scorpio_run_up_atlas.png",
        )),
        "training_battle_weapon_motion": all(marker in css for marker in (
            ".ft-world-card.is-training-map .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast)",
            ".ft-world-battle-card.is-live-battle .ft-world-player.is-character-scorpio:not(.is-moving):not(.is-training-cast)",
            "character_scorpio_weapon_stand_atlas.png",
            "character_scorpio_weapon_run_down_atlas.png",
            "character_scorpio_weapon_run_side_atlas.png",
            "character_scorpio_weapon_run_up_atlas.png",
            "ftWorldCharacterScorpioRunEight",
        )),
        "weapon_assets_cached": all(marker in js for marker in (
            "character_scorpio_weapon_stand_atlas.png",
            "character_scorpio_weapon_run_down_atlas.png",
            "character_scorpio_weapon_run_side_atlas.png",
            "character_scorpio_weapon_run_up_atlas.png",
        )),
        "city_keeps_non_weapon_motion": "--qm-scorpio-stand" in css and "character_scorpio_stand_atlas.png" in css and "character_scorpio_run_side_atlas.png" in css,
        "ultimate_ground_origin_anchored": ultimate_ground_anchor_contract(),
        "character_scale_150": "--scorpio-character-scale: 1.62;" in css and "--scorpio-basic-scale: 1.62;" in css,
        "ultimate_stage_expanded_canvas": "position: absolute;" in css and "width: 640px;" in css and "height: 640px;" in css and "bottom: -157px;" in css,
        "tall_character_name_offset": ".ft-world-player.is-character-scorpio .ft-world-name-row" in css and "top: -142px;" in css and ".ft-world-player.is-character-scorpio .ft-world-level" in css and "top: -106px;" in css and ".ft-world-player.is-me.is-character-scorpio .ft-world-training-player-hud" in css and "bottom: calc(100% + 88px);" in css and ".ft-world-battle-player.is-character-scorpio .ft-world-battle-player-head" in css and ".ft-world-battle-player.is-character-scorpio .ft-world-battle-stats" in css,
        "battle_hp_above_name": ".ft-world-battle-player.is-character-scorpio .ft-world-battle-player-head { transform: translateY(-88px); }" in css and ".ft-world-battle-player.is-character-scorpio .ft-world-battle-stats { top: -118px; }" in css,
        "cast_locks_actor_motion": "node.classList.contains(\"is-training-cast\")" in js and "void self.node.offsetWidth" not in js,
        "ultimate_frame_five": "const burnDelay = frameDuration * 4;" in js and 'stage: "frame-5-burn"' in js,
        "ultimate_random_per_enemy": "affected.forEach((row, index) =>" in js and "const variant = Math.random() < 0.5 ? 1 : 2;" in js,
        "ultimate_burn_slow_timing": "ftWorldTrainingScorpioUltimateBurn 1760ms steps(7, end) both" in css and "burn.remove(), 1820" in js and "scorpioUltimate ? 2600" in js,
        "ultimate_burn_scale_150": "scale(1.02);" in css and "scale(.63);" in css and "scale(1.14);" in css,
        "basic_burn_scale_150": "calc(var(--scorpio-burn-y, 0px) - 166px)) scale(1.08);" in css and "transform-origin: 50% 68%;" in css,
        "ultimate_burn_assets": all((WEB / f"character_scorpio_ultimate_burn_{index}_atlas.png").is_file() for index in (1, 2)),
        "ultimate_burn_one_new_folder": 'SOURCE / "burn nộ 1" / f"{index}.png"' in (ROOT / "FUTURE" / "tools" / "build_qm_city_character_scorpio.py").read_text(encoding="utf-8") and 'SOURCE / "burn nộ.png"' not in (ROOT / "FUTURE" / "tools" / "build_qm_city_character_scorpio.py").read_text(encoding="utf-8"),
        "ultimate_burn_two_new_folder": 'SOURCE / "burn nộ 2" / f"{index}.png"' in (ROOT / "FUTURE" / "tools" / "build_qm_city_character_scorpio.py").read_text(encoding="utf-8") and 'SOURCE / "burn nộ 2.png"' not in (ROOT / "FUTURE" / "tools" / "build_qm_city_character_scorpio.py").read_text(encoding="utf-8"),
        "ultimate_server_skill": '"id": "scorpio-ultimate"' in skill_helpers,
        "ultimate_server_full_field": "if not is_scorpio_ultimate and distance > 1:" in training_skill,
        "ultimate_viewport_scope": 'host.closest(".ft-world-stage")' in js and "visible_enemy_ids: visibleEnemyIds" in js and "visible_enemy_ids = {" in training_skill,
        "avatar": (WEB / "character_scorpio_avatar.png").is_file(),
        "ten_buttons": all((WEB / f"character_scorpio_basic_skill_{index}.png").is_file() for index in range(1, 11)),
        "ultimate_button_19": (WEB / "character_scorpio_ultimate_skill_button.png").is_file(),
        "responsive_controls": "@media (max-width: 760px)" in controls_css and ".has-scorpio-training-controls .ft-world-training-skill-dock" in controls_css and ".is-scorpio-ultimate" in controls_css,
    }
    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}={'ok' if passed else 'FAIL'}")
    if failed:
        print("failed=" + ",".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
