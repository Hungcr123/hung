# Future Server 2 Plan

## Current Architecture

- Canonical launcher: `FUTURE/server2/run_server_2.py`
- Start from Future folder: `FUTURE/RUN_SERVER_2.bat`
- Split frontend shell: `FUTURE/web/future_split.html`
- Split assets: `FUTURE/web/future.css` and `FUTURE/web/future.js`
- Server 2 worker: `FUTURE/server2/future_stt_worker_2.py`
- Compatibility wrapper: root `FUTURE_SERVER_2.py`

## Ports

- App: `8877`
- Worker: `8878`
- Public domain: `https://qm-tech.io.vn`

## Hosted Fixes

- Hosted/protected HTML now inlines split CSS.
- Hosted/protected HTML now inlines protected JS.
- Direct hosted JS request still returns `403` by design.
- Cốc Cốc white/unstyled rendering is avoided because the page no longer depends on an external stylesheet.

## Validation

- [x] `python -m compileall -q FUTURE_SERVER_2.py future_stt_worker_2.py FUTURE`
- [x] `node FUTURE/tools/build_future_js.cjs --check`
- [x] `node FUTURE/tools/build_future_css.cjs --check`
- [x] Local `http://127.0.0.1:8877/login`
- [x] Hosted `https://qm-tech.io.vn/future.html`
- [x] Cốc Cốc clean-profile browser test
- [x] Tunnel status: ready
- [x] Worker status: `future-stt-worker-2`, ready

## Pass 21 QM City Training Split

- [x] Split `FUTURE/server_parts/vocab_world_game/05_qm_city_training.py` into ordered parts.
- [x] Keep `05_qm_city_training.py` as a small loader.
- [x] Preserve shared-namespace loading and function names.
- [x] Validate compile/import/local HTTP after the split.

Planned parts:

- `01_state_stats.py`: training state, persistence, level/stat normalization, public stat payload.
- `02_question_pool.py`: sentence/word prompt pools, question kind normalization, generated question variants.
- `03_question_pick.py`: question selection and public question projection.
- `04_arena_lifecycle.py`: slime creation, arena rebalance/tick/new/user/public state, selection helpers.
- `05_select_answer.py`: select flow and answer/hit/reward flow.
- `06_upgrade_skill_reset.py`: stat upgrades, skill casting, and reset flow.

Validation results:

- `python -m compileall -q FUTURE_SERVER_2.py future_stt_worker_2.py FUTURE`: passed.
- Import check for `qm_city_training_state_for_user`, `qm_city_training_select`, `qm_city_training_answer`, `qm_city_training_upgrade`, `qm_city_training_cast_skill`, `qm_city_training_reset`, and `QM_CITY_TRAINING_PART_FILES`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_status_page.cjs --check`: passed.
- Temporary server 2 smoke on `http://127.0.0.1:8896`: `/frontend-version`, `/login`, `/health`, `/settings`, and `/announcements` passed; protected training routes returned clean `401` without login.
- Main server 2 restarted from `FUTURE/server2/run_server_2.py` on port `8877`.
- Hosted `https://qm-tech.io.vn/future.html`: passed; inline CSS is present and external hosted JS remains blocked by design.
- Coc Coc headless screenshot passed: `C:\Users\hungc\AppData\Local\Temp\future_server_2_coccoc_pass21.png`.
- Active main server 2 process: PID `13220`; active tunnel process: PID `20144`.

## Pass 22 Shared World Battle Split

- [x] Split `FUTURE/server_parts/vocab_world_game/04_shared_world_battle.py` into ordered parts.
- [x] Keep `04_shared_world_battle.py` as a small loader.
- [x] Preserve route-facing function names used by `/world/battle/*`.
- [x] Preserve QM City answer helper names loaded before QM City training.
- [x] Validate compile/import/build/local HTTP after the split.

Planned parts:

- `01_state_profile.py`: battle state cache, disk persistence, profile and invite public projection.
- `02_vocab_questions.py`: dictionary lookup, vocab pool, asked-word history, and battle question selection.
- `03_answer_rules.py`: answer matching plus Vietnamese token/score helpers shared with QM City training.
- `04_battle_engine.py`: battle ids, turns, answer reveal, crystal transfer, damage, finish, and HP checks.
- `05_public_state_npc.py`: public question/log/payload, timeout advance, NPC bot tick, prune, and state-for-user.
- `06_invite_respond.py`: invite creation, auto battle creation, accept/decline response flow.
- `07_answer_skill_forfeit.py`: answer application, skill application, skill route flow, and forfeit flow.

Guardrail: this remains a shared-namespace transitional split. Preserve delayed state flushing, atexit flush registration, NPC battle automation, crystal transfer side effects, and all public function names consumed by HTTP routes and QM City training.

Validation results:

- `python -m compileall -q FUTURE_SERVER_2.py future_stt_worker_2.py FUTURE`: passed.
- Import check for `load_shared_world_battle_state`, `write_shared_world_battle_state`, `shared_world_battle_state_for_user`, `shared_world_battle_invite`, `shared_world_battle_respond`, `shared_world_battle_answer`, `shared_world_battle_skill`, `shared_world_battle_forfeit`, `shared_world_battle_public_payload`, `shared_world_battle_pick_question`, `qm_city_training_vietnamese_answer_tokens`, `qm_city_training_vietnamese_answer_score`, and `qm_city_training_vietnamese_answer_matches`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_status_page.cjs --check`: passed.
- Temporary server 2 smoke on `http://127.0.0.1:8897`: `/frontend-version`, `/login`, `/health`, `/settings`, and `/announcements` passed; protected battle routes returned clean `401` without login.
- Main server 2 restarted from `FUTURE/server2/run_server_2.py` on port `8877`.
- Hosted `https://qm-tech.io.vn/future.html`: passed; inline CSS is present and external CSS link is absent.
- Active main server 2 process: PID `5828`; active tunnel process: PID `18248`.

## Pass 23 Shared World Core Split

- [x] Split `FUTURE/server_parts/vocab_world_game/03_shared_world_core.py` into ordered parts.
- [x] Keep `03_shared_world_core.py` as a small loader.
- [x] Preserve route-facing function names used by `/world/state`, `/world/move`, `/world/chat`, and `/world/action`.
- [x] Preserve shared constants/helpers consumed by battle and QM City training.
- [x] Validate compile/import/build/local HTTP after the split.

Planned parts:

- `01_state_city_npc.py`: shared-world state cache, disk persistence, clamp helpers, and city NPC profile/seed helpers.
- `02_profile_level_payload.py`: player profile, leaderboard meta, QM City level meta, level maps, and public player payload.
- `03_player_touch.py`: player row creation/update, movement target persistence, and stale-player pruning.
- `04_npc_bots.py`: NPC mode/settings/candidates, transition scheduling, NPC snapshots, active battle users, and NPC movement tick.
- `05_world_state_move.py`: active battle pairs, public world state payload, and movement route flow.
- `06_chat_validation.py`: English chat validation, display/target helpers, and NPC chat availability checks.
- `07_npc_chat_replies.py`: NPC chat reply worker and reply scheduling.
- `08_chat_action_constants.py`: chat route flow, world action route flow, and shared battle/QM City constants.
- `09_qm_city_skill_helpers.py`: QM City skill catalog/tree/stat helpers and training bonus-word helpers.

Guardrail: this remains a shared-namespace transitional split. Preserve state flush throttling, atexit flush registration, NPC online/battle filtering, chat validation rules, route-facing function names, and the battle/QM constants loaded after core but before battle/training loaders.

Validation results:

- `python -m compileall -q FUTURE_SERVER_2.py future_stt_worker_2.py FUTURE`: passed.
- Import check for `load_shared_world_state`, `write_shared_world_state`, `shared_world_state_for_user`, `shared_world_move`, `shared_world_chat`, `shared_world_action`, `shared_world_touch_player`, `shared_world_npc_bot_tick`, `shared_world_active_battle_pairs`, `validate_shared_world_chat_message`, `SHARED_WORLD_BATTLE_GAMES`, `QM_CITY_TRAINING_SLIME_COUNT`, `qm_city_training_skill_catalog`, `qm_city_training_public_skills`, `qm_city_training_bonus_words_for_user`, `shared_world_battle_state_for_user`, and `qm_city_training_state_for_user`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_status_page.cjs --check`: passed.
- Temporary server 2 smoke on `http://127.0.0.1:8901`: `/frontend-version`, `/login`, `/health`, and `/settings` passed; protected world/battle/training routes returned clean `401` without login.
- Main server 2 restarted from `FUTURE/server2/run_server_2.py` on port `8877`.
- Hosted `https://qm-tech.io.vn/future.html`: passed; inline CSS is present and external CSS link is absent.
- Active main server 2 process: PID `7164`; active tunnel process: PID `7404`.

## Pass 24 Space Task Build

- [x] Pause broad splitting/refactor work and build the new Task board feature on server 2.
- [x] Keep manual Task Node intact for admin/legacy workflows.
- [x] Add automatic Space Task payload for normal users.
- [x] Add admin switch button between Task Node and Space Task.
- [x] Add admin preferred folder settings for each learner.
- [x] Split the new backend feature into small parts instead of adding one large file.

Backend structure:

- `FUTURE/server_parts/server_data_pdf_qmdict/03_lesson_tasks_logs.py`: manual Task Node storage plus shared task normalization.
- `FUTURE/server_parts/server_data_pdf_qmdict/03_space_task_auto.py`: loader for Space Task feature parts.
- `FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/01_settings.py`: Space Task limits and preferred folder settings.
- `FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/02_folder_scan.py`: folder order, lesson file scan, source row creation.
- `FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/03_payload.py`: final Space Task payload builder.

Behavior:

- Normal users see Space Task instead of manual Task Node.
- Admin users can switch between manual Task Node and Space Task in the Task board.
- Admin can choose a Space Task priority folder directly from a folder row in Lesson Vault with `Choose folder task`.
- Space Task scans preferred folders first, then the learner folder.
- If admin has not chosen a priority folder, Space Task scans only the learner's own folder and descendants.
- `common` is used only when admin explicitly chooses `common` or a folder under `common` as a priority folder.
- Each Space gets the next unfinished file in order; `Space_V` gets two active vocabulary files.
- Completed files are skipped automatically, so the next unfinished file appears without keeping completed rows in the board.
- Admin can save preferred folders with POST `/lesson-tasks` action `space-folders`.

Validation results:

- `python -m compileall -q FUTURE`: passed.
- Import check for `space_task_payload_for_user`, `save_space_task_settings`, and `SPACE_TASK_AUTO_PART_FILES`: passed.
- Direct payload check for learner `anphm`: returned 7 active Space Task rows, including 2 `Space_V` vocabulary files.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Temporary server 2 smoke on `http://127.0.0.1:8904`: `/frontend-version` and `/login` passed; unauthenticated `/lesson-tasks` returned clean `401`.
- Main server 2 restarted on port `8877`; active app process: PID `7272`.
- Cloudflare named tunnel restarted; active tunnel process: PID `876`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed.
- Hosted `https://qm-tech.io.vn/future.html`: passed and contains `ft-task-mode-switch`, `ft-task-space-folders`, and `Space Task`.
- Follow-up fix: `/server-data/list` now includes `space_task` and `space_tasks`, so Task board renders auto tasks even when opened from Lesson Vault payload.
- Follow-up fix: user default queue no longer falls back to `common`; admin must choose a folder task when a learner should use a shared/common folder.
- Follow-up validation before compact-logo cleanup: `list_server_data('', 'hungc')` returned `0` Space Task rows because `hungc` has no own queued files; `list_server_data('', 'tin')` returned W/Q/P plus 2 `Space_V`; `list_server_data('', 'anphm')` still included Picture plus 2 `Space_V`.
- Follow-up frontend check before compact-logo cleanup: rebuilt `future.js`; local asset contained `Choose folder task` and the old `Vocabulary Task` label.

## Pass 25 Task Board Compact File Logos

- [x] Keep Space Task order explicit: 2 `Space_V` vocabulary files first, then `Space_W`, `Space_Q`, `Space_P`, and `Space_PDF`.
- [x] Stop automatic Picture task insertion; Picture remains manual-only.
- [x] Add shared frontend file-type logo helper for Task board and Lesson Vault.
- [x] Replace redundant Task board type text/chips with file-type logos.
- [x] Remove the visible `Vocabulary Task`, `Space_W Task`, `Picture Task`, and `Assigned` labels from the Task board.
- [x] Synchronize file-type logo colors/styles between Lesson Vault and Task board.

Current behavior:

- Normal users see compact Space Task cards with a colored file logo, file name, `Auto`, progress/time chips, and action buttons.
- The first two automatic rows are vocabulary files when unfinished `Space_V` files exist.
- Completed files stay skipped by backend payload generation; the next unfinished file appears automatically.
- Picture files are not auto-added by Space Task.
- Admin manual Task Node still keeps severity/remove controls; Space Task cards stay read-only except opening/selecting the lesson.

Validation results:

- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m compileall FUTURE/server_parts FUTURE/server_app.py FUTURE/server2`: passed.
- Direct payload check for learner `tin`: returned `Space_V`, `Space_V`, `Space_W`, `Space_Q`, `Space_P`.
- Direct payload check for learner `anphm`: returned only 2 `Space_V` rows, with no automatic Picture row.
- Source/bundle check: no `Vocabulary Task`, `Space_W Task`, `Picture Task`, or `Assigned` labels remain in Task board JS.
- Local HTTP smoke on `http://127.0.0.1:8877`: `/frontend-version`, `/future.html`, `/login`, and `/health` passed.
- Local asset check: `/future-assets/future.js` contains `ft-task-type-logo` and `ft-file-type-logo`, and does not contain `Assigned` or `Vocabulary Task`.
- Hosted smoke on `https://qm-tech.io.vn`: `/frontend-version` and `/future.html` passed after restarting the named tunnel.
- Active server 2 process: PID `6356`; active Cloudflare tunnel process: PID `20596`.

## Pass 26 File Logo Click Motion

- [x] Add a shared JS logo-motion helper for file-type logos.
- [x] Trigger the logo animation when selecting/clicking Task board cards and Lesson Vault file rows.
- [x] Trigger the same logo animation when clicking `Let's go`, because those buttons stop parent click propagation.
- [x] Keep hover/focus/periodic pulses from spamming the logo animation.
- [x] Add a 3.6 second logo animation with core brighten/scale, energy ring, and diagonal sweep.
- [x] Preserve the existing card/row click behavior and do not make the logo a separate interactive control.

Validation results:

- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future-assets/future.js` contains `triggerFutureFileLogoMotion`, `FUTURE_FILE_LOGO_MOTION_MS`, and `is-logo-burst`.
- Local `/future-assets/future.css` contains `futureFileLogoClickCore`, `futureFileLogoClickRing`, and `futureFileLogoClickSweep`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-872e21061a2028ee433dd6e8`.
- Hosted `https://qm-tech.io.vn/future.html`: passed.
- Hosted `/future-assets/future.css` contains the new logo click keyframes.
- Active server 2 process remains PID `6356`; active Cloudflare tunnel process remains PID `20596`.

## Pass 27 File Logo Electron Orbit Hover

- [x] Upgrade file-type logos from plain text to structured logo nodes with `label` plus 3 orbit layers.
- [x] Add hover/focus animation for Task board logos and Lesson Vault file-type marks.
- [x] Add 3 electron-style orbit rings with separate rotating paths and glowing electron dots.
- [x] Keep click animation, but upgrade it to run the same orbit system more strongly for 3.6 seconds.
- [x] Keep the logo non-interactive; hover/click behavior still belongs to the card/file row.
- [x] Preserve motion-off compatibility with explicit animation overrides for hover and click.

Validation results:

- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future-assets/future.js` contains `ft-file-logo-orbits`, `ft-file-logo-label`, and `triggerFutureFileLogoMotion`.
- Local `/future-assets/future.css` contains `futureFileLogoHoverCore`, `futureFileElectronOrbitA`, `futureFileElectronOrbitB`, and `futureFileElectronOrbitC`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-75e249f974972beabf76adf1`.
- Hosted `https://qm-tech.io.vn/future.html`: passed.
- Hosted `/future-assets/future.css` contains the hover/electron orbit keyframes.

## Pass 28 Admin Task Notice Popup Toggle

- [x] Add a `Task notice` toggle button to the admin Task board button group.
- [x] Add a `Hide` button inside the Task Notice popup header so the popup can be closed even when it covers the admin button group.
- [x] Change Task Notice admin UI from a third layout panel into a floating centered popup.
- [x] Stop using the old Notice tab/panel path; the Task board remains the normal Task board surface.
- [x] Default Task board mode is now `space`, so admin opens the same Space Task view that normal users see, with the existing switch still available for manual Task Node.
- [x] Keep Task Notice hidden until admin explicitly toggles it open.

Validation results:

- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future.html` contains `ft-task-notice-toggle` and `ft-task-notice-close`.
- Local `/future-assets/future.js` contains `setTaskNoticeAdminOpen`, `has-task-notice-popup`, and default `taskBoardMode = "space"`.
- Local `/future-assets/future.css` contains centered popup styling for `.ft-task-notice-admin`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9dcc009d973d031d71a8e55e`.
- Hosted `https://qm-tech.io.vn/future.html`: passed.
- Hosted `/future-assets/future.css` contains the centered Task Notice popup styling.
- Active server 2 process remains PID `6356`; active Cloudflare tunnel process remains PID `20596`.

## Pass 29 Space Task Admin Button Cleanup

- [x] Hide `Refresh stats` while admin is viewing `Space Task`.
- [x] Hide `Test <24h` while admin is viewing `Space Task`.
- [x] Hide `Test >24h` while admin is viewing `Space Task`.
- [x] Keep those legacy/debug buttons available only when admin switches back to manual `Task Node`.

Validation results:

- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future-assets/future.js` contains the new `displayUsesSpace` button-hiding conditions.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-8932c56d7a0f69d96ffab9e6`.
- Hosted `https://qm-tech.io.vn/future.html`: passed.

## Pass 30 Lesson Vault Folder Hover Motion

- [x] Add folder-only decorative DOM for Lesson Vault rows: document stack plus folder lid.
- [x] Add hover/focus animation that opens the folder lid and sends three document sheets upward/outward.
- [x] Keep the animation scoped to folder rows only; file-type logos keep their existing electron orbit/click motion.
- [x] Allow the folder icon overflow to remain visible so the document sheets are not clipped inside the 38px icon.
- [x] Preserve row click behavior; the new lid/doc elements are non-interactive and `aria-hidden`.
- [x] Tune the document keyframes so sheets stay invisible while low in the folder body, then appear only near the folder mouth.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future.html`: returned 200.
- Local `/future-assets/future.js` contains `ft-folder-doc-stack` and `ft-folder-lid`.
- Local bundle contains `futureFolderLidOpen`, `futureFolderDocFlyA`, `futureFolderDocFlyB`, and `futureFolderDocFlyC`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-340957fb52461d2fa14692e8`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Hosted `/future-assets/future.css`: GET returned 200 and contains the new folder hover keyframes.
- Hosted direct `/future-assets/future.js` remains protected by server design, so JS verification was done on the local asset and hosted HTML build.
- Follow-up tuning check: hosted CSS contains the new delayed document transforms and no longer contains the old early `14%` document fade-in.

## Pass 31 Task Board Cleanup And Scroll Edge Polish

- [x] Add a return fade-out point to the folder document keyframes so sheets become invisible while still above the folder mouth before resetting to the low hidden position.
- [x] Hide and disable `Test <24h` permanently in the admin Task board render path.
- [x] Hide and disable `Test >24h` permanently in the admin Task board render path.
- [x] Supersede Pass 29 legacy behavior: the two debug test buttons are no longer shown in Task Node either.
- [x] Add Lesson Vault-style top/bottom scroll edge mask, rail glow, and scroll padding to `.ft-task-list`.
- [x] Apply the same scroll polish to both normal Task board and Space Task, because both modes render through `.ft-task-list`.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `/future-assets/future.js` contains `taskEffectTestPendingButton.hidden = true` and `taskEffectTestOverdueButton.hidden = true`.
- Local `/future-assets/future.js` no longer contains the old `taskEffectTestPendingButton.hidden = !(payload.admin && !displayUsesSpace)` condition.
- Local and hosted `frontend-version`: passed with version `future-source-6ba3d10c2fa7b5473d3dca9c`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Hosted `/future-assets/future.css` contains the folder return fade transforms and the `.ft-task-list` edge mask/scroll padding.

## Pass 32 Folder Intake Motion Tuning

- [x] Slow down the document return phase so sheets visibly move back toward the folder mouth instead of disappearing too abruptly.
- [x] Keep the final low-position reset invisible so sheets do not leak below the folder body.
- [x] Delay the folder lid close point so the intake motion reads naturally.
- [x] Expand the folder body lower and wider inside the 38px icon to create more visual space for the document animation.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- Local and hosted `frontend-version`: passed with version `future-source-2037f8ed2bbeec92ee055b9e`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Hosted `/future-assets/future.css` contains the wider/taller folder body and the new document intake transforms.

## Pass 33 Folder Vertical Balance And Vault Top Clearance

- [x] Re-center the folder icon vertically inside the 38px file mark by moving the lid upward and body slightly upward.
- [x] Keep the folder body expanded enough for the document intake animation while reducing the previous low-heavy look.
- [x] Increase Lesson Vault list top padding so first-row folder animations have more space above them.
- [x] Soften the Lesson Vault top mask from 17px to 12px so flying documents are less likely to be clipped/faded at the top edge.
- [x] Apply matching mobile top/bottom padding for the Lesson Vault list.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- Local and hosted `frontend-version`: passed with version `future-source-87606217dbfd948cd5e44ddd`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Hosted `/future-assets/future.css` contains the new Lesson Vault padding/mask values and centered folder lid/body values.

## Pass 34 Folder Frame Escape And Vault Nav Compact

- [x] Increase the folder-only icon frame height to 48px so the document animation has a taller visual frame.
- [x] Move the folder body/lid/document stack down inside the taller frame so the folder remains balanced.
- [x] Let the document sheets fly slightly outside the folder icon frame during the peak motion for a more dynamic effect.
- [x] Redesign the Lesson Vault nav so `Back` and `Last file` split into left/right halves when a recent file exists.
- [x] Keep `Back` full width when no recent file shortcut is available.
- [x] Remove the long lower path/meta lines from `Back` and `Last file`; breadcrumb/path context remains in the top path bar and tooltips.
- [x] Remove unused CSS/JS references for the old `ft-server-back-meta` and `ft-server-recent-path` nodes.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-fa8bfa3cfbf7e97672f2b46e`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Hosted HTML contains `Last file` and no longer contains `ft-server-recent-path` or `ft-server-back-meta`.
- Hosted CSS contains `.ft-server-nav.has-recent-file`, the 48px folder frame, and the outside-frame document fly transform.
- Local `/future-assets/future.js` contains `has-recent-file` add/remove logic and no longer contains `serverRecentFilePathNode`.

## Pass 35 Space Task Folder Ownership And Summary Scroll

- [x] Allow normal users to choose and remove Space Task folders for their own account from Lesson Vault.
- [x] Keep admin folder management for target learners, while normal users are limited to their own top-level folder plus `common`.
- [x] Convert the Lesson Vault folder task button into a toggle: `Choose folder task` when unregistered and `Remove task folder` when registered.
- [x] Preserve folder registration order by appending newly chosen folders instead of prepending them.
- [x] Rebuild `/lesson-tasks` POST routes from the ordered fragment so `space-folders` accepts self-service user updates.
- [x] Update Space Task auto selection so two or more preferred folders are distributed by folder round-robin per Space type; this gives two `Space_V` slots one file per chosen folder first when possible.
- [x] Force admin and user Task board rendering to one shared Space Task view; the old Task Node switch remains hidden and disabled.
- [x] Hide the `Total tasks`, `Critical`, and `Completed` meter row in Space Task to give more vertical space to task files.
- [x] Add `Space P` to the learning summary cards.
- [x] Convert learning summary cards to a horizontal drag-scroll strip with smooth animated return to the `Vocabulary` card when the pointer leaves the summary area.
- [x] Restart Server 2 after backend edits so the Python route and Space Task selector changes are active.

Validation results:

- `node FUTURE/tools/build_post_routes.cjs`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `python -m py_compile FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/01_settings.py FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/03_payload.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-3d22c2e6d00484aaa505a720`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-3d22c2e6d00484aaa505a720`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Active Server 2 app process after restart: PID `19272`; active worker: PID `21108`; active Cloudflare tunnel: PID `18072`.

## Pass 36 Space Task Compact Card And Assignment Timer

- [x] Add lightweight backend assignment tracking for automatic Space Task files in `space_task.assigned`.
- [x] Preserve `space_task.assigned` when reading/writing lesson task records and when saving preferred folder settings.
- [x] Prune assignment timestamps to the currently active Space Task files so completed or removed-folder files do not keep stale assignment state.
- [x] Attach `assigned_at` to each active auto Space Task row and use it as `added_at` when the auto task has no manual timestamp.
- [x] Move `Let's go` out of the bottom controls row into a compact quick-action area directly under the progress stack.
- [x] Keep admin/user progress bars grouped in a single progress stack to avoid overlap when both learner and admin progress exist.
- [x] Add an `Assigned ...` chip beside the existing lesson time chip; the chip updates locally every minute without server calls.
- [x] Turn the assigned-time chip red with a distinct clock/ring style when the task age reaches 24 hours.
- [x] Add a 10-minute Task panel auto-refresh while the Task tab is open, matching the lightweight Lesson Vault polling cadence.
- [x] Restart Server 2 after backend edits so assignment timestamp tracking is active.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `python -m py_compile FUTURE/server_parts/server_data_pdf_qmdict/03_lesson_tasks_logs.py FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/01_settings.py FUTURE/server_parts/server_data_pdf_qmdict/space_task_auto/03_payload.py`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-9585920938ef264cb5726ea4`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9585920938ef264cb5726ea4`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.
- Unauthenticated local `/lesson-tasks`: returned clean `401`.
- Active Server 2 app process after restart: PID `20600`; active worker: PID `10948`; active Cloudflare tunnel: PID `4628`.

## Pass 37 Learning Summary Drag Reset Polish

- [x] Hide the visible scrollbar from the learning summary card strip while keeping horizontal drag.
- [x] Remove `scroll-snap` from the summary strip because it could hold the row between cards and leave `Vocabulary` partially clipped.
- [x] Replace native smooth-scroll reset with a custom requestAnimationFrame easing reset that always finishes at `scrollLeft = 0`.
- [x] Cancel any pending return animation as soon as the user starts dragging again.
- [x] Increase drag sensitivity slightly so the summary cards feel easier to pull by mouse.
- [x] Keep vertical page gestures working with `touch-action: pan-y`.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-b2f2b393d6e822bf66c0059d`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-b2f2b393d6e822bf66c0059d`.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 38 Login Vault Preload And Auth Connector Trim

- [x] Make `loadServerDataPath()` return the loaded/cached payload and support `throwOnError` for preload callers.
- [x] Extend `openServerBrowserAfterAuth()` with `revealAfterLoad`, `silent`, `fresh`, and `throwOnError` options so Lesson Vault can render while hidden.
- [x] Change `completeAuth()` to wait for the Lesson Vault request/render before hiding the login gate when auth should open Lesson Vault.
- [x] Keep the login submit disabled during the preload path to avoid double-submit flicker.
- [x] Hide the demo/real login Vault backdrop before preloading so the user does not see the old preview refresh into the real Vault.
- [x] Disable the heavy four-corner DNA connector login effect in JS, including SVG path generation, animation frames, corner flashes, and shockwave triggering.
- [x] Add CSS fallback to keep auth connector/fx layers hidden even if stale classes are present.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-eaf6546f645ae73fe2e2e75d`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-eaf6546f645ae73fe2e2e75d`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 39 Login DNA Connector Impact Trim

- [x] Re-enable the four-corner login DNA connector animation.
- [x] Add a separate `AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED` switch so connector motion and endpoint impact can be controlled independently.
- [x] Keep DNA path/rung animation active while disabling endpoint corner flash and final panel shockwave.
- [x] Avoid creating/positioning the auth impact FX layer when impact FX is disabled.
- [x] Remove the global CSS rule that hid `.ft-auth-connectors`, while keeping the fallback that hides only the flash/shockwave layer.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-e74f7c19250974eac1843c7d`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-e74f7c19250974eac1843c7d`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 40 Login Exit And Lesson Vault Double-Load Guard

- [x] Close the login card immediately after successful auth when the next screen is Lesson Vault, instead of keeping the card visible while the Vault request finishes.
- [x] Show the top operation loader during the hidden Lesson Vault preload so the transition has feedback without leaving the login card stuck on screen.
- [x] Keep `revealAfterLoad` so Lesson Vault itself is still revealed only after its folder payload is ready.
- [x] Remove the forced `fresh` request from login preload so an existing fresh folder cache can be reused.
- [x] Add a short recent-load guard for Lesson Vault folders to prevent immediate duplicate render/fetch of the same folder.
- [x] Add an auth-open busy flag so route navigation does not trigger a second Lesson Vault load while auth is already opening it.
- [x] Change the login backdrop flow to render the Lesson Vault demo backdrop first, and only fall back to the static preview if demo rendering fails, removing the static-preview-to-demo double flash on app entry.
- [x] No Server 2 restart required; this pass only changes frontend JS bundle and the running server serves the rebuilt static file.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-53b7f78d0e7d3d522ce4eae6`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-53b7f78d0e7d3d522ce4eae6`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 41 Space Task Hover Dispatch Popup

- [x] Remove the native browser title tooltip from Space Task cards so hovering no longer shows the raw file path/link popup.
- [x] Remove native title from the task card file-type logo while keeping its aria label.
- [x] Store task hover metadata on each Space Task card: title, path, space type, assignment source, assigned time, completion state, progress text, and progress percent.
- [x] Add a 3-second hover/focus delay before showing the custom Space Task dispatch popup.
- [x] Add a singleton floating popup over Lesson Vault, positioned on the left side and aligned near the hovered card.
- [x] Design the popup like the provided sketch: small thumbnail/status card, angular connector line, then a larger modern notification panel.
- [x] Animate the connector first with draw/blink, then animate the notification panel with scan/pop effects.
- [x] Generate dynamic content that says whether the file was automatically assigned by the system or assigned by admin.
- [x] Show assignment time, elapsed time, 24-hour target, current progress, and a stronger urgent message when the task is over 24 hours.
- [x] Use Vietnamese content when the learner has under 1000 vocabulary words; switch to English when the learner has 1000 or more.
- [x] Hide the popup on pointer leave, blur, card click, Let's go, severity change, or remove action.
- [x] Hide the popup on touch/mobile and when Lesson Vault motion is disabled.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-9f64af9333caff673bf94def`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9f64af9333caff673bf94def`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 42 Space Task Hover Popup Activation Fix

- [x] Fix the hover popup not showing when Lesson Vault motion was disabled; the Space Task dispatch popup now remains available even if general motion-off is active.
- [x] Remove the CSS rules that hid the popup for `ft-lesson-vault-motion-off` and coarse-pointer environments, because desktop/touch-hybrid browsers can match those rules unexpectedly.
- [x] Prevent the 3-second hover timer from resetting when the pointer moves across child elements inside the same task card.
- [x] Add delegated `pointerover`/`pointerout` handling on the whole server browser so dynamically rendered task cards reliably arm/cancel the popup.
- [x] Add `mouseenter`/`mouseleave` fallback listeners on each task card.
- [x] Update the popup connector so it animates from the actual hovered task file/card toward the floating notification on the left.
- [x] Keep the sketch-like small card with three compact content bars: file type, assignment source, and urgency/status.
- [x] Keep the large panel tied to the currently hovered Space Task file, with full assignment and 24-hour expectation text.
- [x] Add modern orbit/ring animation on the notification panel, similar to the top notification style.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-61ad1a339e8f903494a4c35e`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-61ad1a339e8f903494a4c35e`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 43 Space Task Hover Connector Re-anchor

- [x] Remove the small thumbnail/status card from the Space Task hover popup; the hover UI now only shows the main notification panel.
- [x] Position the notification panel to the left of the hovered Space Task file/card instead of pinning it to a fixed left viewport slot.
- [x] Detach the connector SVG from the transformed popup element and mount it directly on `body`, fixing incorrect coordinate calculations.
- [x] Re-anchor the connector so it starts from the popup panel and connects to the hovered file logo.
- [x] Use the visible card rectangle inside the scroll container as fallback, with logo coordinates preferred for the connector endpoint.
- [x] Keep the notification text tied to the actual Space Task file currently being hovered.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-bd8bb7a44d4d1b1ed5746d44`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-bd8bb7a44d4d1b1ed5746d44`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 44 Space Task Hover Connector Sketch Match

- [x] Rebuild the Space Task hover connector geometry so the line starts from the real hovered task file/logo, runs through a short horizontal stem, turns through an angled segment, then enters the notification panel edge like the user's sketch.
- [x] Keep the notification panel beside the hovered task card, preferring the left side and falling back to the right only when there is no room.
- [x] Anchor the connector to the nearest logo/card edge so it no longer appears detached from the hovered file.
- [x] Split the connector styling into glow, core, moving trace, and endpoint nodes so the line is visually clear above Lesson Vault.
- [x] Add the missing trace and endpoint pulse keyframes so the modern connector animation actually runs.
- [x] Keep the popup content tied to the actual Space Task card being hovered; no fake thumbnail/status mini-card is rendered.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS bundles and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-9a7e4a55a30a384ea8efab72`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9a7e4a55a30a384ea8efab72`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 45 Space Task Hover Connector Shape Correction

- [x] Change the Space Task hover connector from a 4-segment line into the original sketch-like shape: one short horizontal arm from the hovered file/logo, then one diagonal segment into the popup.
- [x] Remove the extra final horizontal segment that made the connector look unlike the first design.
- [x] Force the popup endpoint lower than the file/logo anchor so the diagonal segment is visible instead of collapsing into a flat line.
- [x] Keep the existing glow, core, moving trace, and endpoint pulse styling from Pass 44.
- [x] No Server 2 restart required; this pass only changes frontend JS and the running server serves the rebuilt static file.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-b3a844b9bab5cf989fdec6b1`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-b3a844b9bab5cf989fdec6b1`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 46 Space Task Hover Connector Up-left Rail

- [x] Change the Space Task hover connector direction to start at the hovered file/logo, travel diagonally up-left, then continue as a horizontal rail.
- [x] Move the notification popup upward so the popup sits above the horizontal connector rail instead of beside or below the diagonal.
- [x] Keep the connector anchored to the real hovered task card/logo and preserve the glow, trace, and endpoint pulse visuals.
- [x] Keep the left-side popup preference; right-side fallback remains only for tight viewport cases.
- [x] No Server 2 restart required; this pass only changes frontend JS and the running server serves the rebuilt static file.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-d5f75bdad1c17d447a3f7d6b`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-d5f75bdad1c17d447a3f7d6b`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 47 Space Task Hover Connector Rail Timing

- [x] Make the hover connector calmer: it draws in, blinks twice, then returns to a static state instead of continuing infinite connector motion.
- [x] Keep the popup notification animation active above the connector rail so the visual emphasis moves from the line to the notification.
- [x] Set the horizontal connector rail to about two-thirds of the popup width.
- [x] Place the rail about 10px below the popup panel when there is enough vertical space.
- [x] Keep the diagonal segment anchored from the real hovered task file/logo into the rail.
- [x] Reduce connector glow/core thickness so the line feels more like the first callout design and less visually heavy.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-0fe47043d0faecd8768d3629`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-0fe47043d0faecd8768d3629`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: first 30s request timed out, retry with 60s timeout returned 200.

## Pass 48 Space Task Hover Rail Spacing and Popup Border

- [x] Increase the gap between the popup panel and the connector rail from a fixed 10px to a viewport-based gap of about 5% of screen height.
- [x] Clamp the rail gap between 24px and 72px so the callout remains usable on both small and tall screens.
- [x] Remove the two endpoint dots from the connector for a cleaner callout line.
- [x] Brighten the popup border and add a stronger but still controlled cyan/white glow so the notification stands out above Lesson Vault.
- [x] Keep the existing connector timing: draw in, blink twice, then stay static while the popup animation carries the emphasis.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-7612f153d3a5eb4be90c95ee`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-7612f153d3a5eb4be90c95ee`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 49 Space Task Hover Connector Icon Rail

- [x] Reduce the Space Task hover popup delay from 3 seconds to 1 second.
- [x] Add a vertical connector rail next to the hovered task icon, offset by about 1% of viewport width.
- [x] Match the vertical rail height to the icon height, clamped to stay clean across task card layouts.
- [x] Route the connector from the vertical icon rail into the diagonal segment and then into the horizontal popup rail.
- [x] Add a parallelogram terminal cap at the far end of the connector rail for a more Future-style finish.
- [x] Keep the connector animation calm: draw in, blink twice, then stay static.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-266cee46a592563742c02eb3`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-266cee46a592563742c02eb3`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 50 Space Task Hover Segmented Parallelogram Connector

- [x] Add a dedicated SVG segment group for the Space Task hover connector.
- [x] Generate multiple small parallelogram plates along the diagonal connector segment.
- [x] Generate multiple small parallelogram plates along the horizontal rail segment.
- [x] Keep the existing vertical icon rail and terminal parallelogram cap from Pass 49.
- [x] Style diagonal and horizontal plates with separate cyan/gold accents so the connector feels more Future-like without becoming too noisy.
- [x] Animate plates in with a short stagger, then blink twice and settle into a static state with the rest of the connector.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-5d734cfc707b90389bd834fc`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-5d734cfc707b90389bd834fc`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 51 Space Task Hover Large Connector Plates

- [x] Replace the many small diagonal parallelogram plates with one large primary parallelogram on the diagonal connector segment.
- [x] Shape the diagonal plate along the up-left/down-right connector axis so its acute corners read in the diagonal direction.
- [x] Make horizontal rail plates larger and fewer, closer in visual weight to the terminal parallelogram cap.
- [x] Extend the horizontal rail to 95% of the popup width.
- [x] Slightly reduce rail inset so the longer rail sits cleaner under the popup.
- [x] Strengthen the primary diagonal plate border/glow while keeping the connector blink limited to two cycles.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-a51c722ac4d4eb00ef2b29c8`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-a51c722ac4d4eb00ef2b29c8`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 52 Space Task Hover Rail Plate Balance

- [x] Remove the diagonal parallelogram plate from the Space Task hover connector.
- [x] Keep the diagonal connector as a clean line from the icon rail into the horizontal rail.
- [x] Reduce the horizontal rail length from 95% to 80% of the popup width.
- [x] Make the horizontal parallelogram plates shorter but thicker so they read as stronger Future-style blocks.
- [x] Keep the terminal parallelogram cap and the calm draw/blink-twice connector timing.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-9507c535707b5165bb6fe314`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9507c535707b5165bb6fe314`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 53 Space Task Hover Even Rail Modules

- [x] Replace the proportional rail plate distribution with a centered module layout.
- [x] Use consistent module count, module width, and fixed gaps so the horizontal parallelograms read evenly.
- [x] Keep the rail at 80% of the popup width from Pass 52.
- [x] Add a slim highlight plate inside each rail module for a cleaner Future-style connector.
- [x] Keep the diagonal connector clean with no diagonal parallelogram plate.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-69f3f9b8bed566e7ac3c4358`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-69f3f9b8bed566e7ac3c4358`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 54 Task Notice Hologram Compact Language Mode

- [x] Update Task Notice Hologram runtime so the main card text follows the active notice language.
- [x] If the notice is Vietnamese/voice Vietnamese, the Hologram main card shows Vietnamese text.
- [x] If the notice is English/send audio English, the Hologram main card shows English text.
- [x] Hide the separate Vietnamese mirror/translation card for Hologram style so the lower-corner Vietnamese card no longer appears.
- [x] Keep Face styles able to use the existing bilingual/mirror layout.
- [x] Add Hologram-specific compact classes and CSS so the popup height is reduced closer to the Space_Q notification profile.
- [x] Hide the extra subtext line in compact Hologram mode to avoid unnecessary height.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-91f5cecd697f1a3e75d7872a`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-91f5cecd697f1a3e75d7872a`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 55 Folder Task SVG Button and Notice Ack Layer

- [x] Replace the Lesson Vault folder task text action with a single SVG-based Future-style button.
- [x] Keep one button state machine for normal, linked, linking, and removing states via `setFolderTaskChooseButtonState()`.
- [x] After linking or removing a Space Task folder, replay a compact Hologram Task Notice confirmation popup.
- [x] Keep the folder notice bilingual: Vietnamese when the learner profile should use Vietnamese, otherwise English.
- [x] Move the Task Notice acknowledge listener earlier so `I understand` clicks made during the popup boot animation are not lost.
- [x] Raise the acknowledge button above notice overlays and force pointer events on the live button.
- [x] Compact Hologram avatar layout so avatars are smaller, centered vertically, and stay behind header/text details.
- [x] Avoid newer CSS color APIs on the folder SVG button so older Chromium/Coc Coc builds have a safer render path.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-9d5cc7c7b349f6864fc7e228`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-9d5cc7c7b349f6864fc7e228`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: first 70s request timed out, retry with 120s timeout returned 200.
- In-app Browser tool was not exposed in this turn and Playwright was not installed, so visual browser automation was skipped after HTTP/build validation.

## Pass 56 Correct Folder Task Replay Button

- [x] Correct the Pass 55 interpretation: the Lesson Vault folder choose/remove button is not the requested replay button.
- [x] Restore the Lesson Vault folder task action to compact text states: `Choose folder task`, `Remove task folder`, `Linking`, and `Removing`.
- [x] Remove the incorrect SVG Folder Task button styles from the Lesson Vault folder action path.
- [x] Restore Hologram avatar layout by removing the compact avatar override added in Pass 55.
- [x] Keep the `I understand` click listener improvement because it fixes the earlier ack timing bug without changing layout.
- [x] Rewire the Space Task header `Folder task` button to replay the latest Task Notice sent by admin instead of opening the Space Task folder prompt.
- [x] Remember the latest realtime/immediate Task Notice for replay, with saved `task_notices` as fallback.
- [x] Replay the latest notice through `showTaskUserNotice()` in preview mode so it reopens visually without marking the notice read again.
- [x] Add a small replay-specific style to the Space Task `Folder task` header button while keeping it in the existing button group.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-0d552bd0bcffc30437fe7475`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-0d552bd0bcffc30437fe7475`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 57 Hologram Avatar Offset and Ack Click Fix

- [x] Lower the compact Hologram Task Notice avatar so it no longer sits over the title/header text.
- [x] Shift compact Hologram text content to the right when an avatar is present, leaving a cleaner gap beside the avatar.
- [x] Keep the Hologram avatar visible and full-sized enough to match the existing style, instead of shrinking it aggressively.
- [x] Keep header/text layers above the avatar layer so the top details remain readable.
- [x] Strengthen the `I understand` acknowledgement path by accepting both `pointerup` and `click`.
- [x] Remove both acknowledgement listeners as soon as one fires, avoiding stale click handlers across notices.
- [x] Preserve the Space Task `Folder task` replay behavior from Pass 56.
- [x] No Server 2 restart required; this pass only changes frontend JS/CSS and the running server serves the rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed.
- `node FUTURE/tools/build_future_css.cjs`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-7c4cf3f25f16d14c17fdf56c`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-7c4cf3f25f16d14c17fdf56c`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200.

## Pass 58 Notice Beacon Offset and Frontend Update Session Restore

- [x] Shift the two blinking Hologram notice beacon dots left so they no longer overlap the notice kicker/title text.
- [x] Add a frontend-update reload snapshot before `/frontend-version` forces a refresh, preserving token, username, route, selected file, and browser path when a logged-in user receives a newer HTML build.
- [x] When the stale page is still on `/login` but a valid token exists, redirect the update refresh to Lesson Vault so restore avoids the login-clearing path.
- [x] When the stale page is on `/login` without a token, defer the frontend refresh instead of wiping the login form; after successful auth, the pending version refresh runs with a saved reload session.
- [x] Adjust `restoreAuthSession()` so a valid reload snapshot is honored before the explicit login route clears stored auth.
- [x] Rebuild `future.js` and `future.css`; no Server 2 restart required because the running server serves the rebuilt files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `49c4be67fd25d5003469d3e91d8d5c120a23e8691637f6f178b59b158c3db7d7`.
- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `fafc3e7203a3b10281147201fe0b38769466ba042ddd96706b172a5e27b9b40e`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-ed0a4ae432ca70be20889cda`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-ed0a4ae432ca70be20889cda`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200 on retry with a longer timeout.
- Local `http://127.0.0.1:8000` was not running in this turn; Server 2 validation used the documented `8877` port.

## Pass 59 Disable Startup Frontend Auto-Reload

- [x] Remove the forced `location.replace()` / `location.reload()` path from the startup `/frontend-version` check.
- [x] Keep `/frontend-version` as a lightweight version recorder only: it updates `future_frontend_cache_version` and clears old server-data manifest markers when the version changes.
- [x] Remove the post-login pending frontend reload path so a successful login is not interrupted by a version refresh.
- [x] Clear stale frontend reload/pending session flags when recording the version, preventing old Pass 58 state from firing later.
- [x] Preserve the normal auth restore/session logic; only the frontend update auto-refresh behavior was disabled.
- [x] Rebuild `future.js` and `future.css`; no Server 2 restart required because the running server serves the rebuilt files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `5aa01edaf51474a5328ec28139083fc1ce638220a22935339d3b4e0537b91211`.
- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `fafc3e7203a3b10281147201fe0b38769466ba042ddd96706b172a5e27b9b40e`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- `rg` check found no remaining `applyFrontendCacheVersionReload`, `applyPendingFrontendCacheReloadAfterAuth`, `writeFrontendCacheReloadSession`, or `frontendCacheVersionParam` references.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-b45042941dbb626ef6445bdc`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-b45042941dbb626ef6445bdc`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: first request timed out, retry with 60s timeout returned 200.

## Pass 60 Login Username Warmup and Lesson Vault Preload

- [x] Identify the slow login path: Lesson Vault opens only after auth, then `/server-data/list` may do a cold manifest/list/progress/task pass before the user sees the cached username/Vault state.
- [x] Add lightweight public `GET /auth/username?username=...` to validate username format, report registered users, and report pending registration state before password entry.
- [x] Add `GET /server-data/login-preload?username=...&path=...` to warm the server-side Lesson Vault list cache for an existing user before password entry.
- [x] Strip tasks, Space Task, and Task Notices from the pre-auth preload response so notices/task node stay hidden until the password is accepted.
- [x] Start username check and Vault preload when the user presses Enter in the username field, blurs/changes username, or focuses the password field.
- [x] If the username is invalid/missing, show the error early and focus/select the username field for correction.
- [x] On successful login, wait briefly for an already-running warmup, then open Lesson Vault; if warmup is not finished, login continues normally instead of blocking.
- [x] Rebuild GET routes and frontend bundles, then restart Server 2 so the new Python endpoints are active.

Validation results:

- `node FUTURE/tools/build_get_routes.cjs`: passed, `03_handler_get_routes.py` sha256 `391fda0403130071de9889ba78eba5e75dc5da1e96a41a4bf6758746abb0d831`.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `6f4807afd493747592b8c4f14014e4ecce28c9f486d5d9b7adcf5be72b272dda`.
- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `fafc3e7203a3b10281147201fe0b38769466ba042ddd96706b172a5e27b9b40e`.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/http_server/03_handler_get_routes.py`: passed.
- Server 2 restarted; new listener is active on `127.0.0.1:8877`.
- Local `http://127.0.0.1:8877/auth/username?username=hung`: returned 200 with `exists: true`.
- Local invalid username check returned 200 with `valid: false` and a correction message.
- Local `http://127.0.0.1:8877/server-data/login-preload?username=hung`: returned 200; first warmup took about 3014 ms.
- Hosted `https://qm-tech.io.vn/auth/username?username=hung`: returned 200 with `exists: true`.
- Hosted `https://qm-tech.io.vn/server-data/login-preload?username=hung`: returned 200; warmed response took about 9 ms after local cache was hot.
- Local and hosted `/frontend-version`: returned version `future-source-2cc8c1739de0947a8da5de47`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200 with 60s timeout.

## Pass 61 Open Lesson Vault Immediately After Login

- [x] Remove the post-login transition/loading screen that showed `Dang tai Lesson Vault...`.
- [x] Stop hiding the Lesson Vault browser while `openServerBrowserAfterAuth()` is loading data.
- [x] Change the auth success path to open Lesson Vault immediately with `revealAfterLoad: false`.
- [x] Keep username warmup running in the background, but do not wait for it before showing Lesson Vault.
- [x] Keep loading feedback inside Lesson Vault itself if data is still being fetched.
- [x] No Server 2 restart required; this pass changes frontend JS only and the running server serves rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `5e05f6b6f591ca1cf73056ee0dec061df9776d2973bd6099d1e2dc44f08ab942`.
- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `fafc3e7203a3b10281147201fe0b38769466ba042ddd96706b172a5e27b9b40e`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `future.js` parse check: passed.
- `rg` check found no remaining `Dang tai Lesson Vault`, `revealAfterLoad: true`, or `clearLoginVaultRealBackdrop({ hideBrowser` in the auth success path.
- Local `http://127.0.0.1:8877/frontend-version`: passed with version `future-source-949186057db472153af5d2b2`.
- Hosted `https://qm-tech.io.vn/frontend-version`: passed with version `future-source-949186057db472153af5d2b2`.
- Local `http://127.0.0.1:8877/future.html`: GET returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: GET returned 200 with 60s timeout.
- Hosted `https://qm-tech.io.vn/auth/username?username=hung`: returned 200, confirming the Pass 60 warmup endpoint still works.

## Pass 62 Cross-Network Screen Share Transport

- [x] Diagnose why screen share only worked reliably on the same network: the frontend only used default STUN servers, while cross-network NAT/CGNAT often needs TURN relay.
- [x] Add WebRTC ICE settings to Server 2 defaults and public settings: `webrtc_ice_servers`, `webrtc_force_relay`, `webrtc_has_turn`, and nested `webrtc`.
- [x] Support both new env config (`FUTURE_TURN_URLS`, `FUTURE_TURN_USERNAME`, `FUTURE_TURN_CREDENTIAL`, `FUTURE_WEBRTC_FORCE_RELAY`) and the existing settings aliases (`turn_urls`, `turn_username`, `turn_credential`, `webrtc_relay_only`).
- [x] Update frontend WebRTC creation to refresh `/settings` before starting learner/admin peers and apply dynamic ICE config instead of hardcoded-only STUN.
- [x] Re-enable server-relayed screen JPEG fallback: authenticated users can post `/screen/frame`; local/admin-auth viewers can poll `/screen/admin/frame` or `/screen/auth-admin/frame`.
- [x] Restore learner frame sending and admin frame polling so server relay works when direct WebRTC is blocked by different networks.
- [x] Keep direct WebRTC as the preferred path, but lower frame relay pressure when WebRTC is connected.
- [x] Document TURN env setup in `FUTURE/server2/README.md`.
- [x] Restart Server 2 cleanly after removing duplicate stale `run_server_2.py` processes.

Validation results:

- `node FUTURE/tools/build_get_routes.cjs`: passed, `03_handler_get_routes.py` sha256 `19447eb31009eaa6688e3f43f6d906f024c807e6d7d0e5879d0baa8f0ccbccd6`.
- `node FUTURE/tools/build_post_routes.cjs`: passed, `04_handler_post_routes.py` sha256 `bc62d02ad8f1fcfc7f2c3270abd0654823f2307c7a09bb1ded8cf8c357521e84`.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `7af03f2239a927453debf37d7aae1af02840502c7ac1642b2e4f81153ab3ee03`.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/users_auth_settings/07_server_settings.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Local `http://127.0.0.1:8877/settings`: returned `webrtc_has_turn: true`, `webrtc.force_relay: true`, and current OpenRelay TURN URLs from `_future_settings.json`.
- Hosted `https://qm-tech.io.vn/settings`: returned the same WebRTC/TURN settings after tunnel reconnect.
- Local `http://127.0.0.1:8877/screen/admin/frame?username=test&session=test&after=0`: returned 200 with `{"ok":true,"session":{},"frame":null}`, confirming fallback frame polling is no longer disabled.
- Unauthenticated local `POST /screen/frame`: returned 401, confirming frame upload remains auth-gated.
- Local `http://127.0.0.1:8877/frontend-version`: returned version `future-source-472247844edc612d83bd1ec8`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned version `future-source-472247844edc612d83bd1ec8`.
- Local `http://127.0.0.1:8877/future.html`: returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.
- Server 2 is running as one parent/child pair for `FUTURE/server2/run_server_2.py`; listener PID is `22128` on `127.0.0.1:8877`.

## Pass 63 Screen Control Cursor and Faster Relay Frames

- [x] Diagnose why admin mouse was not visible on the user side after screen relay started working: cursor-only commands were sent over WebRTC datachannel only and were filtered out of HTTP fallback.
- [x] Allow `cursor` commands to travel through `/screen/auth-admin/control` when the datachannel is not open, so the user can see the admin cursor over server-relayed screen sessions.
- [x] Add `adminScreenPointerActive` state and send real `pointermove` commands while the admin is dragging, instead of sending only passive cursor movement.
- [x] Add pointer capture/release and pointer cancel handling on the admin screen view to avoid stuck drag states.
- [x] Speed up user-side control polling from 1000 ms to 90 ms during active screen sessions.
- [x] Speed up server-relayed frames by changing capture width from 1440 to 1280, JPEG quality from 0.82 to 0.72, and fallback frame interval from 900 ms to 280 ms.
- [x] Speed up admin frame polling while WebRTC video is not live from 650 ms to 260 ms.
- [x] Keep lower frame pressure when WebRTC is connected by polling fallback frames at 1800 ms and user capture fallback at 1800 ms.
- [x] Rebuild `future.js`; no Server 2 restart required because this pass changes frontend JS only and the running server serves rebuilt static files.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `860d8d5950ff07827d6a39226b7027df767c4fa09cf6eec2275370b0692aa21a`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `rg` check confirmed `adminScreenPointerActive`, `LEARNER_SCREEN_CONTROL_POLL_MS`, and `const httpCommands = commands` are present in both `js_parts` and built `future.js`.
- Local `http://127.0.0.1:8877/frontend-version`: returned version `future-source-ea23aaed5b7280d7f0a51f38`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned version `future-source-ea23aaed5b7280d7f0a51f38`.
- Local `http://127.0.0.1:8877/future.html`: returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.

## Pass 64 Admin Screen Transport Modes and Realtime Path Logging

- [x] Add an admin screen `Mode` button with three transport preferences:
  - `Auto`: WebRTC first, server relay fallback.
  - `Realtime`: prefer WebRTC direct/TURN video and avoid relay-only policy.
  - `Relay`: pause WebRTC and use server frame relay only.
- [x] Add an admin `Check path` button to snapshot the current screen transport path.
- [x] Add a compact admin-side transport log panel showing mode, active transport, control channel, peer state, ICE state, and frame id.
- [x] Add server-side transport logging endpoint `POST /screen/auth-admin/transport-log`.
- [x] Write transport logs to `C:\server data\_future_screen_transport_log.jsonl` so later debugging can read which branch actually ran.
- [x] Change legacy `webrtc_relay_only` handling so it no longer forces all WebRTC traffic through TURN by default; current `/settings` now keeps TURN available but reports `webrtc_force_relay: false`.
- [x] Keep `FUTURE_WEBRTC_FORCE_RELAY=1` as the explicit override for true relay-only WebRTC when needed.
- [x] Further reduce fallback latency by switching relay frame encoding to WebP, reducing frame width to 1120, quality to 0.64, frame interval to 160 ms, admin frame poll to 160 ms, and control poll to 60 ms.
- [x] Rebuild POST routes, frontend JS, and frontend CSS, then restart Server 2 because backend routes/settings changed.

Validation results:

- `node FUTURE/tools/build_post_routes.cjs`: passed, `04_handler_post_routes.py` sha256 `7a490d2feb02a5e14a3b27a2ae41196c543a966e977a39b2afa5db2de5133bc8`.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `251f299ab317b89d291aa5811d367451c92f17b34b1983261f170289d5a3d989`.
- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `dd252bad777ae0cc04042001f198cf3d62cad3916b1c1706878bf7f496c1f6f6`.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/users_auth_settings/07_server_settings.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Server 2 restarted; listener PID is `22096` on `127.0.0.1:8877`.
- Local `http://127.0.0.1:8877/settings`: returned `webrtc_force_relay:false`, `webrtc_has_turn:true`, and OpenRelay TURN URLs still available as fallback.
- Local `POST /screen/auth-admin/transport-log`: returned 200 on local admin test and wrote `C:\server data\_future_screen_transport_log.jsonl`.
- Local `http://127.0.0.1:8877/frontend-version`: returned version `future-source-8125c8ecb445c93e3391cbc4`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned version `future-source-8125c8ecb445c93e3391cbc4`.
- Local `http://127.0.0.1:8877/future.html`: returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.

## Pass 65 Screen Share 720p Quality Profile

- [x] Switch the screen-share quality target to a stable 720p profile instead of the reverted low-latency profile.
- [x] Set WebRTC capture constraints to `1280x720`, `30fps`, with `resizeMode: "crop-and-scale"`.
- [x] Set WebRTC sender encoding to maintain resolution, target `6.5 Mbps`, `30fps`, and calculate `scaleResolutionDownBy` from the captured source so larger screens downscale toward 720p.
- [x] Raise server relay fallback to 720p bounds: max width `1280`, max height `720`, WebP quality `0.78`.
- [x] Scale fallback frames by both width and height so non-16:9 screens do not exceed the 720p envelope.
- [x] Rebuild `future.js`; no Server 2 restart required because this pass changes frontend JS only.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `c2613d883802467175e6d5d62bda6516f6ab53c4a22aa145f4f4f6c0eefaa0da`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `rg` check confirmed `LEARNER_SCREEN_WEBRTC_WIDTH`, `LEARNER_SCREEN_PREVIEW_MAX_HEIGHT`, `crop-and-scale`, `LEARNER_SCREEN_WEBRTC_BITRATE`, and calculated `scaleResolutionDownBy` are present in `js_parts` and built `future.js`.
- Local `http://127.0.0.1:8877/frontend-version`: returned version `future-source-dde2946d9efd7302c51523fb`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned version `future-source-dde2946d9efd7302c51523fb`.
- Local `http://127.0.0.1:8877/future.html`: returned 200.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.

## Pass 66 Screen Transport Log Diagnostic

- [x] Read `C:\server data\_future_screen_transport_log.jsonl` to identify the active screen-share branch.
- [x] Confirm current `/settings` reports `webrtc_force_relay:false`, `webrtc_has_turn:true`, and OpenRelay TURN URLs are available, so the server is not forcing relay-only mode.
- [x] Latest manual checks show mode `relay`, transport `server-relay-frame`, control `http-control`; this is the HTTP image relay branch, not direct WebRTC realtime.
- [x] Earlier Auto/Realtime attempts created WebRTC tracks, but ICE then reached `failed/disconnected`, so the app fell back to server relay.
- [x] Approximate relay speed from logged `frame_id` deltas is around `0.55-1.16 fps`, with the latest relay session around `0.83 fps`; current logs are branch/status logs, not full WebRTC FPS/bitrate telemetry.

Follow-up improvement options:

- Add a dedicated screen telemetry pass using `RTCPeerConnection.getStats()` plus relay encode/upload timing so the admin log can show real FPS, bitrate, upload latency, frame size, and dropped/late frames.
- For true realtime across different networks, prioritize a reliable private TURN server or VPN-style path; OpenRelay is present but current ICE logs show it is not producing a stable connection.
- For the HTTP relay fallback, keep 720p resolution but consider a lighter relay encoder/profile because 720p WebP quality `0.78` over JSON/base64 can limit frame rate heavily on weaker machines or slow uplinks.

## Pass 67 Screen Fallback 10fps Binary Relay Profile

- [x] Keep the fallback frame envelope at 720p (`1280x720`) but change the target fallback cadence to `10fps` (`100ms`).
- [x] Lower fallback WebP quality from `0.78` to `0.68` to reduce frame payload while keeping the 720p profile.
- [x] Add client-side binary frame upload for fallback frames using `canvas.toBlob()` and `POST /screen/frame-binary`.
- [x] Keep the old JSON/DataURL `/screen/frame` route as automatic fallback if binary upload is unavailable.
- [x] Change the sender frame loop to compensate for encode/upload time instead of always waiting a full interval after upload finishes.
- [x] Change the admin fallback frame poll interval to follow `LEARNER_SCREEN_PREVIEW_INTERVAL_MS`, so the viewer can poll at the same 10fps target instead of being capped by the previous `160ms` poll.
- [x] Add lightweight relay telemetry in admin transport snapshots: `relay_fps`, frame chars, width, and height.
- [x] Add screen frame timing data to `collectFtCpuDebug()` for local debugging: mode, last elapsed ms, encode ms, upload ms, bytes, target fps, and binary enabled state.
- [x] Add backend helper `screen_store_frame_bytes()` to convert accepted image bytes to the existing DataURL session frame format, keeping the admin viewer contract unchanged.
- [x] Restart Server 2 cleanly after discovering two Server 2 process groups were running; the old process was still holding port `8877` and did not recognize the new route.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `27c1b84acee4b6db2cdcddc1d6396b51d1adf4b7814b8007275f529d1a9dbdaf`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs`: passed, `04_handler_post_routes.py` sha256 `a21ff824ee7b0125dc0943286da0b9e08ba3bfde9807df500f46b6531c84bb91`.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Server 2 restarted cleanly; the active listener is on `127.0.0.1:8877`.
- Local `POST /screen/frame-binary` without auth returns `401 missing_token`, confirming the new route is live and protected.
- Local `http://127.0.0.1:8877/frontend-version`: returned version `future-source-a40acf8a5a0225ea8c8cae11`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned version `future-source-a40acf8a5a0225ea8c8cae11`.
- Hosted `https://qm-tech.io.vn/future.html`: one validation request timed out, but hosted `/frontend-version` already confirms the tunnel is serving the new frontend version.

## Pass 68 Paint and Screen Realtime Rate-Limit Exemption

- [x] Diagnose `Too many requests` while drawing: paint cursor/sync can exceed the shared `ANTI_ROBOT_POST_LIMIT = 80` requests per minute during active drawing.
- [x] Add `anti_robot_realtime_path()` in the HTTP handler core.
- [x] Exempt realtime paint routes from the generic request bucket:
  - `/paint/state`
  - `/paint/admin/state`
  - `/paint/sync`
  - `/paint/cursor`
  - `/paint/admin/sync`
  - `/paint/admin/cursor`
- [x] Exempt high-frequency screen-control/frame routes too, so the 10fps fallback profile is not stopped by the generic bucket:
  - `/screen/frame`
  - `/screen/frame-binary`
  - `/screen/control`
  - `/screen/auth-admin/frame`
  - `/screen/auth-admin/control`
  - `/screen/admin/frame`
  - `/screen/admin/control`
- [x] Keep anti-robot browser challenge and route-level auth/admin checks in place; this removes only the generic per-minute bucket for realtime paths.
- [x] Restart Server 2 cleanly so the core handler change is active.

Validation results:

- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/http_server/02_handler_core.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `15936`.
- Burst test: 120 local GET requests to `/paint/state?after=0` returned `401` and no `429`, confirming the rate bucket no longer blocks the paint state path.
- Burst test: 120 local POST requests to `/paint/cursor` returned `401` and no `429`, confirming the rate bucket no longer blocks paint cursor traffic.
- Local `http://127.0.0.1:8877/frontend-version`: still returns `future-source-a40acf8a5a0225ea8c8cae11`; no frontend rebuild was required.

## Pass 69 Screen Fallback Audio Relay

- [x] Diagnose missing audio in screen fallback: the previous screen share requested `audio:false`, sent only image frames during HTTP fallback, and the admin WebRTC offer requested video only.
- [x] Change `getDisplayMedia()` screen capture options to request audio, with system/window audio hints for Chromium-based browsers.
- [x] Add captured audio tracks to the screen WebRTC peer so direct WebRTC can carry screen audio when the peer path works.
- [x] Add an admin audio transceiver and `offerToReceiveAudio:true` so admin can receive direct screen audio tracks.
- [x] Add screen-session audio chunk storage on the backend with `screen_add_audio_chunk()` and `screen_poll_audio_chunks()`.
- [x] Add user route `POST /screen/audio-chunk`.
- [x] Add admin routes `GET /screen/admin/audio` and `GET /screen/auth-admin/audio`.
- [x] Add the screen audio routes to the realtime rate-limit exemption list.
- [x] Add learner-side MediaRecorder fallback relay from the captured display audio track, using short chunks every `360ms`.
- [x] Add admin-side audio relay polling and queue playback for fallback mode.
- [x] Add direct WebRTC audio playback handling in the admin screen `track` handler.
- [x] Add audio state to admin transport snapshots and UI log lines: `webrtc-audio`, `relay-audio`, or `pending`.
- [x] Keep screen frame/video behavior unchanged while adding audio as a parallel path.

Important runtime note:

- Browser audio is only available if the browser grants an audio track from `getDisplayMedia()`. In Chromium/Coc Coc/Edge this usually means the user must choose a tab/window/screen source that supports audio and enable the share-audio checkbox in the browser picker.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `6ab6e8c669837edbb00f55145ace19c2bdf81d5ceeac66056c4f7a6f3419e0c1`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs`: passed, `04_handler_post_routes.py` sha256 `531c944deb050a3b8cd594b9ae6df994c6336b56c7f60fb4113d732096475492`.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `node FUTURE/tools/build_get_routes.cjs`: passed, `03_handler_get_routes.py` sha256 `945e4f23af8d644ef9c4e9b3a720d31894dfe04fd6f642e5966e2bb44cb89cc1`.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/02_handler_core.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `21868`.
- Local `POST /screen/audio-chunk` without auth returned `401 missing_token`, confirming the new user audio route is live and protected.
- Local `GET /screen/auth-admin/audio` returned `{"ok":true,"session":{},"chunks":[]}` from local admin context, confirming the admin audio poll route is live.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-20521db0f40af7ce5b2c79a1`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-20521db0f40af7ce5b2c79a1`.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.

## Pass 70 Disable Generic Request Rate Limit

- [x] Diagnose the mic `Too many requests` issue after enabling audio: mic relay uses `/stream/chunk`, which can burst beyond the old generic request buckets.
- [x] Disable the generic per-minute request bucket in `enforce_anti_robot_rate()`.
- [x] Keep route-level authentication and the anti-robot browser/challenge checks active; this pass removes only the `429 Too many requests` bucket.
- [x] Restart Server 2 so the core handler change is active.

Validation results:

- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/http_server/02_handler_core.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `16016`.
- Burst test: 140 local POST requests to `/stream/chunk` returned `401` and no `429`, confirming mic relay is no longer blocked by request rate.
- Burst test: 320 local GET requests to `/frontend-version` returned `200` and no `429`, confirming the generic GET bucket is disabled too.
- Local `http://127.0.0.1:8877/frontend-version`: still returns `future-source-20521db0f40af7ce5b2c79a1`; no frontend rebuild was required.

## Pass 71 Smooth Mic Relay Playback

- [x] Diagnose admin mic relay stutter: the old relay repeatedly stopped/started `MediaRecorder` every ~360 ms and admin played each chunk with a new `Audio()` element, causing buffer gaps and restart latency.
- [x] Change learner mic relay to keep one `MediaRecorder` running continuously and emit chunks with `recorder.start(240)`.
- [x] Change screen-audio fallback relay to the same continuous `MediaRecorder` timeslice pattern.
- [x] Add admin dashboard `MediaSource` playback for user mic relay chunks, appending WebM/Opus buffers in sequence instead of restarting audio per chunk.
- [x] Keep the old per-chunk `Audio()` playback as fallback if `MediaSource` or the chunk MIME is unsupported.
- [x] Add bounded pending-buffer queues so relay audio does not drift far behind when the network stalls.
- [x] Apply the same `MediaSource` buffer pattern to screen-audio relay playback in `future.js`.
- [x] Rebuild `future.js` and the dashboard status page, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `a502b6cd83667c07d5b0e28f527a1d16feab6bfcbd249b4f4a86a5878961c31b`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_status_page.cjs`: passed, `03_status_page.py` sha256 `56b7e8d58b3a452353929b50c18ec96b209304d1c9f2bee7bbf5df9b2916cb6b`.
- `node FUTURE/tools/build_status_page.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/vocab_build_status/03_status_page.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `21984`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-55f4ecb8b243e5f8c02304b1`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-55f4ecb8b243e5f8c02304b1`.
- Hosted `https://qm-tech.io.vn/future.html`: returned 200.
- Local `http://127.0.0.1:8877/status`: returned 200 and contains both `MediaSource` and `adminStreamRelayMediaSource`, confirming the dashboard script update is live.

## Run

From `C:\programe\write_html\FUTURE`:

```powershell
.\RUN_SERVER_2.bat
```

Or:

```powershell
python .\server2\run_server_2.py
```

## Pass 72 Admin Mic During Screen Session

- [x] Diagnose the cross-network mic gap: the old screen audio path only carried user/share audio to admin; admin mic had no server-relay path for the user to hear when WebRTC direct/TURN was unavailable.
- [x] Add directional screen audio chunks with `sender=user/admin`, so each side receives only the opposite side's audio and never hears its own relay chunks.
- [x] Add protected user polling route `GET /screen/audio` for user-side admin mic playback.
- [x] Add protected admin route `POST /screen/auth-admin/audio-chunk` so admin mic can be sent through Server 2 during the same screen session.
- [x] Add a `Mic On/Off` button inside the admin screen panel.
- [x] Add admin mic capture with browser echo cancellation/noise suppression/auto gain, continuous `MediaRecorder` chunks, and relay posting through Server 2.
- [x] Add user-side playback for admin mic using the same `MediaSource` buffer style used for smoother relay audio, with per-chunk `Audio()` fallback.
- [x] Add direct WebRTC admin mic tracks when available, while keeping server relay active for different-network fallback.
- [x] Add admin screen transport logging field `admin_mic` with `off`, `enabled`, or `relay-sending`.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `6cd5884ddd36f44ca38f8d6e0373ca334a3d1c88bb9e44d346295a61dfadc469`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `node FUTURE/tools/build_get_routes.cjs`: passed, `03_handler_get_routes.py` sha256 `165f52077854e87ddf7b8a85e1b085e730904a5cb88a2fdb07944c9969a15372`.
- `node FUTURE/tools/build_get_routes.cjs --check`: passed.
- `node FUTURE/tools/build_post_routes.cjs`: passed, `04_handler_post_routes.py` sha256 `4c3ecd0fa155d48cd8580255f0ec099152efd34c15363ba08a29f12405d5a578`.
- `node FUTURE/tools/build_post_routes.cjs --check`: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/02_handler_core.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- `future.js` parse check: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `6848`.
- Local `GET /screen/audio?session=test` without login returned `401 missing_token`, confirming the user-side admin-audio route is live and protected.
- Local `POST /screen/auth-admin/audio-chunk` reached the route and returned `400` for the fake session, confirming the admin mic route is live.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-d16502b2340371432e84f1c1`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-d16502b2340371432e84f1c1`.

## Pass 73 User Mic During Screen Session

- [x] Diagnose the user-to-admin audio gap: the previous screen relay only recorded audio tracks returned by `getDisplayMedia()`, which is usually tab/system audio, not the user's microphone.
- [x] Add learner-side microphone capture with browser echo cancellation, noise suppression, and auto gain.
- [x] Mix user microphone audio with optional display/tab audio into one `MediaRecorder` stream when both are available, avoiding two independent recorder streams fighting the admin playback buffer.
- [x] Keep fallback behavior: if mic permission is denied, screen sharing continues and only display/tab audio is relayed if available.
- [x] Add learner mic tracks to the WebRTC screen peer when direct WebRTC is available, while keeping the server relay active for different-network fallback.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `22f93ff22cd191b7904e9fca23effabff412a0fa9bf0eb0745a0c047386c7f6a`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `21420`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-ef809548738bec56eaf6b59e`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-ef809548738bec56eaf6b59e`.
- Local `GET /screen/audio?session=test` without login still returned `401 missing_token`, confirming protected screen audio routes remain active.

## Pass 74 Non-Blocking Screen Mic Upgrade

- [x] Diagnose regression after Pass 73: requesting learner microphone inside the main screen-audio relay could block the screen startup/polling flow behind a browser permission prompt, which also made admin-to-user mic appear broken on different networks.
- [x] Change learner screen audio relay to start immediately without requesting mic, preserving the existing admin-to-user audio polling path.
- [x] Add a delayed background mic upgrade: after the screen session is active, request learner mic, then restart only the learner-to-admin audio recorder with mic/display mix if permission is granted.
- [x] Keep screen sharing and admin mic playback alive even when the user denies or delays mic permission.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `7d7cca8dcbc6ae891f42ef1b084b48bcaf4bb24a29a280c8e1c5041c839c305d`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `6272`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-ed5608bc706f5df5a48c5e4e`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-ed5608bc706f5df5a48c5e4e`.
- Local `GET /screen/audio?session=test` without login still returned `401 missing_token`.

## Pass 75 Stable Screen Mic Relay Segments

- [x] Diagnose the "both sides hear only the beginning, then silence" symptom: continuous `MediaRecorder` timeslice chunks plus `MediaSource` playback can stall after the first appended WebM/Opus segment in some browsers/network combinations.
- [x] Change learner-to-admin screen audio relay to record short self-contained segments by starting a recorder, stopping it after about one second, then automatically restarting while the screen session is active.
- [x] Change admin-to-user mic relay to the same short self-contained segment loop.
- [x] Disable `MediaSource` playback for screen mic relay and use the existing queued `Audio()` fallback, which is more reliable for independent short audio segments across different networks.
- [x] Keep WebRTC direct audio untouched; this pass improves the server relay fallback path.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `dbb3e56e6521289e128e17a515e0791ee19737e4935118556781448c63952b75`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/stream_screen_security/02_screen_sessions.py FUTURE/server_parts/http_server/03_handler_get_routes.py FUTURE/server_parts/http_server/04_handler_post_routes.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `15332`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-6c69ca0ea8ced9f2011d1f87`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-6c69ca0ea8ced9f2011d1f87`.
- Local `GET /screen/audio?session=test` without login still returned `401 missing_token`.

## Pass 76 Paint Image Commit Fix

- [x] Diagnose Paint image paste/upload disappearing: inserted pictures were stored as a temporary selection with `canvas` but `imageData: null`.
- [x] Fix `commitLearnerPaintSelection()` so it accepts either `imageData` selections or `canvas` image selections; previously it deleted canvas-only pictures when changing tools.
- [x] Add Paint `Enter` behavior: when a picture/selection is active, pressing Enter commits it to the canvas, renders, and syncs.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `dcff7c4d547ae5dd29dbe2297bf48a84d9bf218de59515679eeb8a674883d744`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `20044`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-49a9b7fa21c6c2e01d36ced0`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-49a9b7fa21c6c2e01d36ced0`.

## Pass 77 Paint HD Canvas Quality

- [x] Diagnose low Paint canvas quality: the internal Paint board was `1200x720`, so large Paint windows and high-DPI displays upscaled the drawing buffer.
- [x] Raise Paint board resolution to HD `1920x1080`.
- [x] Scale pen, eraser, and text drawing sizes to preserve the old visual feel on the larger HD board.
- [x] Increase Paint server payload limit from 8MB to 16MB so HD PNG sync has more room.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `e43d0acdfa76c139af16af952bc5510c76e77a9bf8afdeb6078c02a5a7564e10`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py FUTURE/server_parts/chat_paint_runtime/04_paint_board.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `19568`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-750cc2625241f0cce2aa29fe`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-750cc2625241f0cce2aa29fe`.

## Pass 78 Paint True Board Zoom And Original Paste Size

- [x] Diagnose Paint zoom issue: canvas CSS size changed, but the render path used stage dimensions as the drawing coordinate system, so the stage/caro feeling changed more clearly than the drawn board content.
- [x] Add board-based canvas CSS sizing: `100%` now fits the HD board into the stage, and zoom in/out scales the board canvas itself.
- [x] Render grid, strokes, pasted images, selections, and draft rectangles in the same board coordinate transform so zoom affects all Paint content together.
- [x] Change pasted/uploaded images to start at their original natural pixel size instead of being automatically scaled down to 70% of the board.
- [x] Note for next pass: browser cookies cannot store unlimited image quality; original-image local caching should use IndexedDB/local browser storage, while server sync should remain lightweight.
- [x] Rebuild `future.js` and restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `0d8c0cd060143c965b51c1d0e74ec3a71bc02f8f030ae4a01e7110e086ac8a2d`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `14784`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-40c7dc7594d988a43c86e427`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-40c7dc7594d988a43c86e427`.

## Pass 79 Paint Browser Zoom Resilience

- [x] Diagnose browser zoom layout issue: Paint toolbar used absolute positioning with fixed `38px` height, so browser zoom made controls overflow or cover the canvas.
- [x] Allow Paint toolbar to wrap and scroll vertically within a bounded dynamic viewport height.
- [x] Add Paint stage top padding/scroll-padding so the canvas is not hidden under a wrapped toolbar.
- [x] Update canvas fit calculation to use the stage content box after padding, so board sizing remains stable under browser zoom.
- [x] Keep Paint's internal zoom behavior from Pass 78 unchanged.
- [x] Rebuild `future.css` and `future.js`, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `523458ed77ea06e7248bb3f4425124dc7df971aa768a27eeb376abf35cf7d4b0`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `ca0663b692187656ae666537c7d6697da1213bd0f26ced305202ae39685334e4`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `5600`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-7e5b13f831b0e2d3ea0366f5`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-7e5b13f831b0e2d3ea0366f5`.

## Pass 80 Paint 100 Percent Fill And Center

- [x] Diagnose 100% Paint zoom issue after board-fit zoom: a strict 16:9 board fit left the dark outer stage grid visible when the Paint stage aspect ratio did not match the board.
- [x] Change Paint 100% sizing to fill the available stage content box, so the white Paint canvas covers the Paint area.
- [x] Keep internal Paint zoom scaling all board content together by multiplying the filled content box by `learnerPaintZoom`.
- [x] Center the canvas inside the stage so zoomed-out/zoomed-in states do not feel left/top biased.
- [x] Rebuild `future.css` and `future.js`, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `977bf4be0e64a6ff21d9d7bf027516f661fa8ca0e54b1d6542ef206486c996bb`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `a38f14bf4c910784d5eed224a3ae7476aa2afdd2443d441ff6f4066c936ca2d5`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `19696`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-58dffb02803a13615a676d73`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-58dffb02803a13615a676d73` after one transient post-restart 502 retry.

## Pass 81 Paint Remove Dark Stage Gaps

- [x] Diagnose remaining dark checkerboard exposure at Paint 100% on different displays: stage fallback background was still dark, so toolbar padding/subpixel/DPI gaps appeared as black caro outside the white canvas.
- [x] Add a small canvas overscan using `ceil + 2px` so 100% fill covers subpixel browser zoom gaps.
- [x] Change Paint stage fallback background from dark caro to a light canvas-matching grid, so any unavoidable exposed area blends with the white Paint board instead of looking like an outer black panel.
- [x] Rebuild `future.css` and `future.js`, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `2f9e2e661fceaac21e06677da8bc6a7ee68f8cd8c8d90bdedd7d74c5553c890b`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `2b9202d35a952563c5730ce693686559c0b4691323d85c9ddb667d400057f591`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `13496`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-83c0b92514e9ca80cb0d648c`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-83c0b92514e9ca80cb0d648c`.

## Pass 82 Paint Full Stage Canvas At 100 Percent

- [x] Diagnose remaining checkerboard exposure on different monitor sizes: Paint stage still reserved a top padding area for the floating toolbar, while the canvas size calculation subtracted that padding from the fill area.
- [x] Remove Paint stage padding/scroll-padding so the canvas can cover the whole stage at `100%` Paint zoom.
- [x] Update Paint canvas CSS-size calculation to use the full stage rectangle instead of subtracting padding.
- [x] Keep the toolbar as a floating overlay above the canvas using existing absolute positioning and `z-index`.
- [x] Rebuild `future.css` and `future.js`, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `6428b2a7fba096c5f14f57f39264524c4a0865d445cbdb174be67a62a771bde9`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `9843a298ab70af6ab4d008ae1564199d2f84d0ee72d3dcb24f5a6236e112da78`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `5600`.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-6b9f2ef2540851e6ba7fd4d2`.
- Browser CSS check on local app: `.ft-paint-stage` computed `paddingTop: 0px`, `scrollPaddingTop: 0px`, and light canvas-matching background.
- Hosted `https://qm-tech.io.vn/frontend-version`: timed out during post-restart retry; local server is healthy.

## Pass 83 Paint Interaction Restore

- [x] React to regression report: after the full-stage canvas change, Paint could no longer draw or insert pictures reliably.
- [x] Restore the previous Paint stage padding/scroll-padding model so the toolbar overlay does not interfere with the active drawing region.
- [x] Restore canvas sizing to subtract the toolbar padding from the drawable area, matching the interaction model that worked before.
- [x] Keep the light canvas-matching stage background from Pass 81 so exposed stage areas are no longer black checkerboard.
- [x] Rebuild `future.css` and `future.js`, then restart Server 2.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `f4cba362053fb3283d4a0ccbd6b5562c2cd373200f5b76f4f98853abc9185fef`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `2b9202d35a952563c5730ce693686559c0b4691323d85c9ddb667d400057f591`.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `python -m py_compile FUTURE/server_app.py`: passed.
- Server 2 restarted; active listener is `127.0.0.1:8877` PID `2912`.
- Browser CSS check on local app: `.ft-paint-stage` exists with `paddingTop: 128px`, `scrollPaddingTop: 128px`, and light `rgb(247, 255, 249)` background.
- Local `http://127.0.0.1:8877/frontend-version`: returned `future-source-75d3602b12bda53c020a3bdc`.
- Hosted `https://qm-tech.io.vn/frontend-version`: returned `future-source-75d3602b12bda53c020a3bdc` after one transient 502 retry.

## Pass 84 QM City Browser VI EN Speech Token Strike

- [x] React to QM City training report: Browser VI+EN slimes that ask in English and expect spoken Vietnamese did not feel like the Vietnamese-cue speak-English slime flow because the character overhead token bubble was missing/cleared too early.
- [x] Add frontend Vietnamese speech token scoring for Browser VI+EN using accent-insensitive token normalization and coverage/precision rules aligned with the Server 2 answer scorer.
- [x] Route Browser VI+EN live transcript into the same character overhead speech bubble used by speech combat, with Vietnamese scoring and masked target tokens.
- [x] Move the visible speech combat feedback out of the center popup and into a `worldCard` overlay anchored to the fire character's `.ft-world-fireball` position.
- [x] Add animated token-flight blocks above the fire character as Browser VI+EN inserts tokens into the input; matching Vietnamese answer tokens glow green and non-matching tokens glow red.
- [x] Add an immediate animated `MIC` beacon above the fire character when Browser VI+EN recording starts, so `translate_vi` 70% questions show a visible recording state before any token arrives.
- [x] Add frontend debug logs under the `QM-City Browser VI+EN` console prefix and the `window.__qmCitySpeechTokenDebug` buffer to trace draft input, expected answer detection, fireball anchor detection, layer creation, mic beacon, and token block spawn.
- [x] Fix the actual `translate_vi` expected-text gap: public QM City questions hide `answer` / `answer_text`, so Browser VI+EN token scoring now reads `meaning` / `translation` / `vietnamese` for translate-to-Vietnamese questions.
- [x] Remove the visible mic beacon after anchor verification; token-flight remains as the live combat feedback.
- [x] Unlock target tokens progressively while recording: correctly spoken target tokens show, missing target tokens stay hidden as placeholders; stopping recording reveals the full target answer.
- [x] Keep the overhead token bubble alive while recording; only stopping the Browser mic/Ctrl flow submits the answer and lets the server decide hit or slime counter.
- [x] Guard Strike/Enter while Browser mic is recording so battle resolution cannot happen before stop.
- [x] Hide the redundant `Speech strike` submit button in the popup for Browser VI+EN speech questions so stop mic is the only speech scoring action.
- [x] Hide the popup submit/Strike button for all QM City training slime questions; Enter remains the compact submit path for typed answers, and mic stop remains the speech scoring path.
- [x] Keep the final overhead token bubble visible briefly after stop/auto-submit so the learner can see the token result during the hit/counter animation.
- [x] Preserve backend event flow: Server 2 still decides `hit`/`hurt`, damage, EXP, and score payload for `translate_vi` / `translate_vi_speech`.

Validation results:

- `node FUTURE/tools/build_future_css.cjs`: passed, `future.css` sha256 `6766d8c7f9c8f22a7ecf3fb53bbd4991690ccaf878f9d52ca3d51cdc890f90de`.
- `node FUTURE/tools/build_future_js.cjs`: passed, `future.js` sha256 `728007bf6dc503ff374afa9aa068452580a5f6179028ecd40ff3b4f208cb237b`.
- `node FUTURE/tools/build_future_css.cjs --check`: passed.
- `node FUTURE/tools/build_future_js.cjs --check`: passed.
- `future.js` parse check: passed.
- `py -3 -m py_compile FUTURE/server_parts/vocab_world_game/shared_world_battle/03_answer_rules.py FUTURE/server_parts/vocab_world_game/qm_city_training/05_select_answer.py`: passed.
- `py -3 -m compileall -q FUTURE_SERVER_2.py future_stt_worker_2.py FUTURE`: passed.
- Local `http://127.0.0.1:8877/health`: returned HTTP 200.
- In-app Browser check on `http://127.0.0.1:8877/login?codexBust=...`: loaded `future-assets/future.js` with no console errors; microphone permission was not exercised during automated verification.
