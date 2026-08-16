"""Guard PvP Basic damage timing and background-tab recovery."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOTION = (ROOT / "FUTURE" / "web" / "js_parts" / "03_world_motion_shared_state.js").read_text(encoding="utf-8")
EVENTS = (ROOT / "FUTURE" / "web" / "js_parts" / "21_progress_bootstrap_events.js").read_text(encoding="utf-8")


def main() -> int:
    checks = {
        "single_explosion_owner": "showSharedWorldMaleBasicEnemyExplosion(impactPoint, attackerNode, () => {" in MOTION
        and "showSharedWorldMaleBasicEnemyExplosion(impactPoint, attackerNode);" not in MOTION,
        "damage_commits_from_server_impact_callback": 'triggerSharedWorldBattleHit(target, damage, false, attacker);' in MOTION
        and 'triggerSharedWorldBattleCast(attacker, target, effect, damage, false, () => {' in MOTION,
        "optimistic_basic_no_fake_hp": 'triggerSharedWorldBattleCast(self, opponent, "basic_attack", 10, false' not in MOTION
        and "visualOwned: false" in MOTION,
        "server_snapshot_waits_for_impact": 'reason: "basic-impact-pending"' in MOTION
        and "sharedWorldBattleDeferredCombatPayload = payload;" in MOTION,
        "confirmed_log_does_not_replay_basic": "optimisticRecord.visualOwned && !ultimateHit" in MOTION,
        "background_payload_is_deferred": 'reason: "background-hidden"' in MOTION,
        "visible_resync_clears_visual_backlog": "clearSharedWorldBattleVisualState();" in MOTION
        and 'releaseSharedWorldBattleCombatRender("visibility-resume", true)' in MOTION
        and "void refreshSharedWorldBattle();" in MOTION,
        "background_animation_callbacks_are_cancelled": "sharedWorldPvpAnimationLifecycleValid" in MOTION
        and 'document.visibilityState === "visible"' in MOTION
        and "shot.remove();" in MOTION
        and "spear.remove();" in MOTION,
        "visibility_handler_is_bound": 'document.addEventListener("visibilitychange", handleSharedWorldBattleVisibilityChange);' in EVENTS,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit(f"PvP Basic impact/visibility contract failed: {', '.join(failed)}")
    print("pvp_basic_impact_visibility_contract=ok explosion=single damage=impact-frame visibility=resync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
