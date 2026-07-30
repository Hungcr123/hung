# Future Refactor Plan

## Goal

Move the large Future runtime out of the project root and into the `FUTURE/` folder while preserving the existing launch command and app behavior.

## Progress

- [x] Audit current `future.html` and server loading paths.
- [x] Create `FUTURE/` package and `FUTURE/web/` asset folder.
- [x] Move the server runtime to `FUTURE/server_app.py`.
- [x] Keep `FUTURE_SERVER.py` as a compatibility wrapper.
- [x] Extract inline CSS and JS from `future.html`.
- [x] Add static asset serving and cache/version support for the extracted assets.
- [x] Validate Python compile, frontend JavaScript parse, and local server smoke test.
- [x] Pass 2: split the server runtime into ordered `FUTURE/server_parts/` domain files.
- [x] Pass 2: keep `FUTURE/server_app.py` as constants plus ordered loader.
- [x] Pass 2: validate compile/import and local HTTP smoke after the split.
- [x] Pass 3: split `06_process_frontend_runtime.py` into ordered nested runtime parts.
- [x] Pass 3: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 4: split `07_server_data_pdf_qmdict.py` into ordered nested runtime parts.
- [x] Pass 4: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 5: split `08_progress_inventory_vocab.py` into ordered nested runtime parts.
- [x] Pass 5: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 6: split `09_vocab_world_game.py` into ordered nested runtime parts.
- [x] Pass 6: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 7: split `10_vocab_build_status.py` into ordered nested runtime parts.
- [x] Pass 7: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 8: split `11_http_server.py` into ordered nested HTTP runtime parts.
- [x] Pass 8: validate compile/import and local HTTP smoke after the nested split.
- [x] Pass 9: split `FUTURE/web/future.js` into ordered IIFE body parts with a rebuild manifest.
- [x] Pass 9: validate JS build/check, Python compile/import, and local HTTP smoke after the frontend split.
- [x] Pass 10: split `FUTURE/web/future.css` into ordered CSS rule-boundary parts with a rebuild manifest.
- [x] Pass 10: validate CSS build/check, JS build/check, Python compile/import, and local HTTP smoke after the stylesheet split.
- [x] Pass 11: split `vocab_build_status/03_status_page.py` into ordered dashboard source fragments with a rebuild manifest.
- [x] Pass 11: validate status page build/check, Python compile/import, frontend checks, and local HTTP smoke after the dashboard split.
- [x] Pass 12: split `http_server/04_handler_post_routes.py` into ordered POST route-family source fragments with a rebuild manifest.
- [x] Pass 12: validate POST route build/check, Python compile/import, frontend/status checks, and local GET/POST smoke after the split.
- [x] Pass 13: split `http_server/03_handler_get_routes.py` into ordered GET route-family source fragments with a rebuild manifest.
- [x] Pass 13: validate GET route build/check, Python compile/import, frontend/status/post checks, and local HTTP smoke after the split.
- [x] Pass 14: split `04_ai_language_agents.py` into ordered nested AI/language runtime parts.
- [x] Pass 14: validate compile/import, frontend/route build checks, and local HTTP smoke after the AI/language split.
- [x] Pass 15: split `02_users_auth_settings.py` into ordered nested users/auth/settings runtime parts.
- [x] Pass 15: validate compile/import, frontend/route build checks, and local HTTP smoke after the users/auth/settings split.
- [x] Pass 16: split `03_chat_paint_runtime.py` into ordered nested chat/paint runtime parts.
- [x] Pass 16: validate compile/import, frontend/route build checks, and local HTTP smoke after the chat/paint split.
- [x] Pass 17: split `05_stream_screen_security.py` into ordered nested stream/screen/security runtime parts.
- [x] Pass 17: validate compile/import, frontend/route build checks, and local HTTP smoke after the stream/screen/security split.
- [x] Pass 18: split `01_core_runtime.py` into ordered nested core runtime parts.
- [x] Pass 18: validate compile/import, frontend/route build checks, and local HTTP smoke after the core runtime split.
- [x] Pass 19: split `ai_language_agents/03_ai_agent_requests.py` into ordered deeper AI-agent request parts.
- [x] Pass 19: validate compile/import, frontend/route build checks, and local HTTP smoke after the AI-agent request split.
- [x] Pass 20: split `server_data_pdf_qmdict/04_server_data_manifest_listing.py` into ordered deeper server-data manifest/listing parts.
- [x] Pass 20: validate compile/import, frontend/route build checks, and local HTTP smoke after the server-data manifest/listing split.

## Current Layout

- `FUTURE_SERVER.py`: compatibility entrypoint for old launchers.
- `FUTURE/server_app.py`: current server runtime.
- `FUTURE/web/future.css`: extracted stylesheet from `future.html`.
- `FUTURE/web/future.js`: extracted browser runtime from `future.html`.
- `FUTURE/tools/extract_future_html_assets.cjs`: one-time/mechanical extraction helper.
- `FUTURE/tools/split_server_app_parts.cjs`: mechanical server splitter used for Pass 2.
- `FUTURE/tools/split_vocab_build_status.cjs`: mechanical nested splitter used for Pass 7.
- `FUTURE/tools/split_http_server.cjs`: mechanical nested splitter used for Pass 8.
- `FUTURE/tools/split_future_js.cjs`: mechanical AST-based splitter used for Pass 9.
- `FUTURE/tools/build_future_js.cjs`: rebuild/check helper for `FUTURE/web/future.js` from ordered parts.
- `FUTURE/tools/split_future_css.cjs`: mechanical rule-boundary splitter used for Pass 10.
- `FUTURE/tools/build_future_css.cjs`: rebuild/check helper for `FUTURE/web/future.css` from ordered parts.
- `FUTURE/tools/split_status_page.cjs`: mechanical f-string fragment splitter used for Pass 11.
- `FUTURE/tools/build_status_page.cjs`: rebuild/check helper for `vocab_build_status/03_status_page.py` from ordered fragments.
- `FUTURE/tools/split_post_routes.cjs`: mechanical POST route-family splitter used for Pass 12.
- `FUTURE/tools/build_post_routes.cjs`: rebuild/check helper for `http_server/04_handler_post_routes.py` from ordered fragments.
- `FUTURE/tools/split_get_routes.cjs`: mechanical GET route-family splitter used for Pass 13.
- `FUTURE/tools/build_get_routes.cjs`: rebuild/check helper for `http_server/03_handler_get_routes.py` from ordered fragments.
- `FUTURE/tools/split_ai_language_agents.cjs`: mechanical nested splitter used for Pass 14.
- `FUTURE/tools/split_users_auth_settings.cjs`: mechanical nested splitter used for Pass 15.
- `FUTURE/tools/split_chat_paint_runtime.cjs`: mechanical nested splitter used for Pass 16.
- `FUTURE/tools/split_stream_screen_security.cjs`: mechanical nested splitter used for Pass 17.
- `FUTURE/tools/split_core_runtime.cjs`: mechanical nested splitter used for Pass 18.
- `FUTURE/tools/split_ai_agent_requests.cjs`: mechanical deeper splitter used for Pass 19.
- `FUTURE/tools/split_server_data_manifest_listing.cjs`: mechanical deeper splitter used for Pass 20.
- `FUTURE/web/js_parts/`: ordered body chunks for the single `future.js` IIFE.
- `FUTURE/web/js_parts/manifest.json`: build manifest with wrapper, order, statement ranges, line ranges, and checksums.
- `FUTURE/web/js_parts/README.md`: workflow and guardrails for editing/rebuilding the frontend JS parts.
- `FUTURE/web/css_parts/`: ordered stylesheet chunks for the single `future.css` entrypoint.
- `FUTURE/web/css_parts/manifest.json`: build manifest with rule-boundary ranges and checksums.
- `FUTURE/web/css_parts/README.md`: workflow and guardrails for editing/rebuilding the frontend CSS parts.
- `FUTURE/server_parts/`: ordered transitional server source parts.
- `FUTURE/server_parts/README.md`: map and rules for the transitional split.
- `FUTURE/server_parts/users_auth_settings/`: smaller ordered parts for users, admin listing, user deletion, profiles/preferences, auth, announcements, and server settings.
- `FUTURE/server_parts/users_auth_settings/README.md`: map and guardrails for users/auth/settings behavior.
- `FUTURE/server_parts/chat_paint_runtime/`: smaller ordered parts for chat state/activity, chat attachments/quota, chat messages/admin state, and paint board state.
- `FUTURE/server_parts/chat_paint_runtime/README.md`: map and guardrails for chat/paint behavior.
- `FUTURE/server_parts/stream_screen_security/`: smaller ordered parts for stream sessions, screen sessions/control, and security/health helpers.
- `FUTURE/server_parts/stream_screen_security/README.md`: map and guardrails for stream/screen/security behavior.
- `FUTURE/server_parts/core_runtime/`: smaller ordered parts for clean/CPU/work queues, anti-robot helpers, path/asset guards, and timestamp/debug logging.
- `FUTURE/server_parts/core_runtime/README.md`: map and guardrails for core runtime behavior.
- `FUTURE/server_parts/process_frontend_runtime/`: smaller ordered parts for model paths, tunnel/process lifecycle, STT, payload/assets, and frontend delivery.
- `FUTURE/server_parts/process_frontend_runtime/README.md`: map and rules for the nested split.
- `FUTURE/server_parts/server_data_pdf_qmdict/`: smaller ordered parts for server-data, lesson progress/tasks, PDF/picture rendering, OCR/QmDict, QMLearn audio, and PDF vocabulary scans.
- `FUTURE/server_parts/server_data_pdf_qmdict/README.md`: map and rules for the server-data/PDF/QmDict nested split.
- `FUTURE/server_parts/server_data_pdf_qmdict/server_data_manifest_listing/`: smaller ordered parts for server-data manifest build/cache, list/file caches, lesson completion, link/copy cleanup, operations, and file reads.
- `FUTURE/server_parts/server_data_pdf_qmdict/server_data_manifest_listing/README.md`: map and guardrails for the server-data manifest/listing deeper split.
- `FUTURE/server_parts/progress_inventory_vocab/`: smaller ordered parts for Space progress, inventory/assets, vocabulary registry, main vocabulary sync, and vocabulary period stats.
- `FUTURE/server_parts/progress_inventory_vocab/README.md`: map and guardrails for vocabulary registry behavior.
- `FUTURE/server_parts/ai_language_agents/`: smaller ordered parts for chat translation/voice, Gemini keys/models, AI agent requests/history, Word Agent, and phonetic IPA.
- `FUTURE/server_parts/ai_language_agents/README.md`: map and guardrails for the AI/language nested split.
- `FUTURE/server_parts/ai_language_agents/ai_agent_requests/`: smaller ordered parts for AI-agent sanitizers/context, Gemini request families, notice assembly, follow-ups, and shared state.
- `FUTURE/server_parts/ai_language_agents/ai_agent_requests/README.md`: map and guardrails for the AI-agent request deeper split.
- `FUTURE/server_parts/vocab_world_game/`: smaller ordered parts for vocabulary leaderboard, shared world, battle, QM City training, and vocabulary room games.
- `FUTURE/server_parts/vocab_world_game/README.md`: map and guardrails for world/game behavior.
- `FUTURE/server_parts/vocab_build_status/`: smaller ordered parts for lesson vocabulary helpers, Space_W/Space_P vocabulary missions, and the status dashboard.
- `FUTURE/server_parts/vocab_build_status/README.md`: map and guardrails for vocabulary build/status behavior.
- `FUTURE/server_parts/vocab_build_status/status_page_parts/`: ordered source fragments for the dashboard f-string runtime file.
- `FUTURE/server_parts/vocab_build_status/status_page_parts/README.md`: workflow and guardrails for editing/rebuilding dashboard fragments.
- `FUTURE/server_parts/http_server/`: smaller ordered parts for multipart/server setup, handler core helpers, GET routes, POST routes, logging, and startup.
- `FUTURE/server_parts/http_server/README.md`: map and guardrails for the transitional HTTP class-loader split.
- `FUTURE/server_parts/http_server/post_route_parts/`: ordered source fragments for `FutureWhisperHandler.do_POST`.
- `FUTURE/server_parts/http_server/post_route_parts/README.md`: route-family map and guardrails for editing/rebuilding POST fragments.
- `FUTURE/server_parts/http_server/get_route_parts/`: ordered source fragments for `FutureWhisperHandler.do_GET`.
- `FUTURE/server_parts/http_server/get_route_parts/README.md`: route-family map and guardrails for editing/rebuilding GET fragments.
- `future.html`: browser shell that loads extracted assets.

## Server Delivery Notes

- Local clients load `/future-assets/future.css` and `/future-assets/future.js` as separate files.
- Hosted/non-local clients receive JavaScript through the protected hosted HTML build; raw JS asset requests are blocked for those clients.
- `/frontend-version` now fingerprints `future.html`, `FUTURE/web/future.css`, and `FUTURE/web/future.js`.

## Validation

- `python -m py_compile FUTURE_SERVER.py FUTURE\server_app.py`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local smoke server: `http://127.0.0.1:8876/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Browser smoke passed: app rendered, CSS/JS tags loaded, console error count was 0.
- Hosted inline check passed: the hosted-prepared HTML no longer exposes the raw JS asset route.

## Pass 2 Server Split

`FUTURE/server_app.py` now keeps shared constants/state and loads these ordered parts:

- `01_core_runtime.py`: loader for clean helpers, CPU/work queues, anti-robot helpers, path/asset guards, timestamps, and debug logging.
- `02_users_auth_settings.py`: loader for users, admin listing, user deletion, profiles/preferences, auth sessions, announcements, and server settings.
- `03_chat_paint_runtime.py`: loader for chat state/activity, chat attachments/quota, chat messages/admin state, and paint board helpers.
- `04_ai_language_agents.py`: loader for translation, Gemini, AI agent, word/phonetic helper parts.
- `05_stream_screen_security.py`: loader for stream sessions, screen sessions/control, and security/health helpers.
- `06_process_frontend_runtime.py`: model/process/tunnel/STT worker and frontend delivery.
- `07_server_data_pdf_qmdict.py`: server-data listing, PDF/picture rendering, QmDict helpers.
- `08_progress_inventory_vocab.py`: Space progress, inventory, assets, vocabulary registry.
- `09_vocab_world_game.py`: vocabulary leaderboard, shared world, battle/game systems.
- `10_vocab_build_status.py`: loader for Space_W vocabulary build flow and status dashboard parts.
- `11_http_server.py`: loader for multipart parsing, HTTP server classes, route handlers, and `main()` parts.

This is intentionally transitional: parts are executed into the same runtime namespace so existing globals and cross-calls keep working. Convert one part at a time into a true importable module only after its dependencies are explicit.

## Pass 2 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE\server_app.py FUTURE\server_parts`: passed.
- Import check for `main`, `FutureWhisperHandler`, `future_html_bytes`, `frontend_delivery_signature`, `user_vocabulary_registry_summary`, `vocabulary_leaderboard`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local split smoke server: `http://127.0.0.1:8877/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.

## Pass 3 Process/Frontend Split

`FUTURE/server_parts/06_process_frontend_runtime.py` now loads these ordered nested parts:

- `01_model_paths.py`: word normalization, model folder resolution, PATH configuration, local IP discovery.
- `02_tunnel_process_dashboard.py`: Cloudflare tunnel setup, PID files, process cleanup, dashboard auto-shutdown.
- `03_local_stt_runtime.py`: local Faster-Whisper loading, queue, and preload helpers.
- `04_stt_worker_bridge.py`: detached STT worker bridge, speech scoring, token analysis.
- `05_payload_assets_storage.py`: JSON/HTML bytes, FTG payload encoding, lesson IO, asset path guards, atomic writes.
- `06_frontend_delivery.py`: frontend asset cache, gzip cache, `/future-assets`, hosted obfuscation, warm cache.

This is still a transitional split. The smaller files share the same runtime namespace, but the boundaries are now clear enough to convert `06_frontend_delivery.py` into a true importable module next.

## Pass 3 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `future_html_bytes`, `frontend_delivery_signature`, `user_vocabulary_registry_summary`, `vocabulary_leaderboard`, `submit_worker_transcription`, `cleanup_runtime`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local nested smoke server: `http://127.0.0.1:8878/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Smoke server process was stopped after validation.

## Pass 4 Server-Data/PDF/QmDict Split

`FUTURE/server_parts/07_server_data_pdf_qmdict.py` now loads these ordered nested parts:

- `01_server_data_paths_links.py`: server-data path guards, relative paths, file/folder link markers.
- `02_lesson_study_progress.py`: lesson study repair, progress summaries, study time, learning summaries.
- `03_lesson_tasks_logs.py`: lesson tasks, task notices, avatars/profile cards, login/learning logs.
- `04_server_data_manifest_listing.py`: loader for server-data manifest build/cache, list/file caches, lesson completion, link/copy cleanup, operations, and file reads.
- `05_picture_pdf_render.py`: picture/PDF path guards, image/PDF render cache, PDF metadata warming.
- `06_ocr_qmdict_core.py`: Tesseract resolution, OCR region extraction, QmDict runtime/reload/lookup/update.
- `07_qmlearn_audio_spacev_repair.py`: QMLearn audio lookup, QmDict meaning audio refresh, Space_V QmDict repair.
- `08_pdf_vocab_scan.py`: PDF/picture vocabulary stats, page scan, and PDF vocabulary mission generation.

## Pass 4 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `safe_server_data_path`, `list_server_data`, `render_pdf_page_png`, `pdf_document_info`, `qmdict_lookup_summary`, `user_vocabulary_registry_summary`, `build_pdf_vocab_mission`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local server-data smoke server: `http://127.0.0.1:8879/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Smoke server process was stopped after validation.

## Cleanup

- Earlier smoke servers on ports `8876` and `8877` were stopped after Pass 4 cleanup.
- Existing non-smoke Future server/worker Python processes were left untouched.

## Pass 5 Progress/Inventory/Vocabulary Split

`FUTURE/server_parts/08_progress_inventory_vocab.py` now loads these ordered nested parts:

- `01_space_w_progress.py`: Space_W progress save/read/clear and speak-skip requests.
- `02_space_q_progress.py`: Space_Q progress save/read/clear.
- `03_space_v_progress.py`: Space_V progress save/read/clear and terminal completion repair.
- `04_space_p_pdf_progress.py`: Space_P and Space_PDF progress save/read/clear.
- `05_inventory_keyboard_assets.py`: inventory, shared-world keyboard pass, server assets, QMLearn sound reads.
- `06_vocab_registry_core.py`: vocabulary registry paths, QmDict reconciliation, Space_V file vocabulary stats.
- `07_main_vocab_sync.py`: sync between Future vocabulary registry and main/QMLearn vocabulary progress.
- `08_vocab_recording_summary.py`: record learned vocabulary items and build `user_vocabulary_registry_summary`.
- `09_vocab_period_stats.py`: vocabulary period buckets and event timestamps used by leaderboards.

Guardrail: `06_vocab_registry_core.py` and `08_vocab_recording_summary.py` support the server-backed Lexicon Memory panel and NEW/OLD card state. Preserve registry-backed learned-word state and do not reintroduce current-answer leakage.

## Pass 5 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `space_w_progress_path`, `save_space_v_progress`, `read_user_vocab_registry`, `user_vocabulary_registry_summary`, `read_user_vocab_registry_snapshot`, `vocabulary_registry_period_counts`, `vocab_period_bucket`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local progress/vocab smoke server: `http://127.0.0.1:8880/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Smoke server process was stopped after validation.

## Pass 6 Vocabulary World/Game Split

`FUTURE/server_parts/09_vocab_world_game.py` now loads these ordered nested parts:

- `01_leaderboard_period_npc.py`: leaderboard period state, NPC_TOP image/profile/session generation, NPC activity buffs.
- `02_leaderboard_social_chat.py`: leaderboard rewards/viewers/social reactions/statuses/world chat.
- `03_shared_world_core.py`: shared-world player state, NPC movement/chat, world actions.
- `04_shared_world_battle.py`: shared-world battle state, invites, turns, answers, skills, forfeit flow.
- `05_qm_city_training.py`: QM City training state, questions, slimes, skills, arena actions.
- `06_leaderboard_rewards_rank.py`: period settlement, reward claims, rank movement, `vocabulary_leaderboard`.
- `07_game_rooms.py`: vocabulary battle room creation, joining, word selection, ready/cancel flow.

## Pass 6 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `load_vocab_leaderboard_period_state`, `vocabulary_leaderboard`, `shared_world_state_for_user`, `shared_world_battle_state_for_user`, `qm_city_training_state_for_user`, `game_room_state`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local world/game smoke server: `http://127.0.0.1:8881/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Smoke server process was stopped after validation.

## Pass 7 Vocabulary Build/Status Split

`FUTURE/server_parts/10_vocab_build_status.py` now loads these ordered nested parts:

- `01_lesson_vocab_helpers.py`: lesson text extraction, QmDict entry resolution, entry summaries, completed progress summaries.
- `02_space_w_vocab_missions.py`: Space_W/Space_P vocabulary context, build jobs, scans, mission generation, completed mission archive.
- `03_status_page.py`: `status_page()` dashboard HTML/CSS/JS. This is still a large f-string and should be extracted in a later dashboard-template pass only after its route/state injections are mapped.

## Pass 7 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `lesson_english_text`, `resolve_vocab_entries_for_text`, `space_w_vocab_context`, `start_space_w_vocab_build_job`, `build_space_w_vocab_mission`, `archive_completed_mission_vocab_file`, `status_page`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local vocabulary build/status smoke server: `http://127.0.0.1:8882/login`.
- HTTP checks passed for `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/frontend-version`.
- Smoke server process was stopped after validation; stderr log was empty.

## Pass 8 HTTP Server Split

`FUTURE/server_parts/11_http_server.py` now loads these ordered nested parts:

- `01_multipart_server.py`: multipart form parser and `FutureThreadingHTTPServer`.
- `02_handler_core.py`: `FutureWhisperHandler` shared headers, response helpers, auth helpers, JSON body parsing, and `OPTIONS`.
- `03_handler_get_routes.py`: `FutureWhisperHandler.do_GET`.
- `04_handler_post_routes.py`: `FutureWhisperHandler.do_POST`.
- `05_handler_logging.py`: `FutureWhisperHandler.log_message`.
- `06_main.py`: CLI argument parsing, startup wiring, background warm tasks, and server loop.

Guardrail: handler method files are executed into the `FutureWhisperHandler` class namespace during the transitional load. Keep route order stable until GET/POST dispatch is extracted into explicit route-family functions.

## Pass 8 Validation

- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureThreadingHTTPServer`, `FutureWhisperHandler`, `parse_multipart_form`, and handler methods `end_headers`, `send_json`, `send_bytes`, `read_json_body`, `do_OPTIONS`, `do_GET`, `do_POST`, `log_message`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- Local HTTP split smoke server: `http://127.0.0.1:8883/login`.
- HTTP checks passed for `/frontend-version`, `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/health`.
- Smoke server process `14440` was stopped after validation; stderr log was empty.

## Pass 9 Frontend JS Split

`FUTURE/web/future.js` remains the single browser-served JavaScript entrypoint, but its source is now split into ordered body chunks under `FUTURE/web/js_parts/`.

- Split method: AST-based, using Acorn, at statement boundaries inside the original single IIFE.
- Parts: 21 ordered files, each mapped in `FUTURE/web/js_parts/manifest.json`.
- Rebuild command: `node FUTURE\tools\build_future_js.cjs`.
- Check command: `node FUTURE\tools\build_future_js.cjs --check`.
- Source checksum after split: `9517d176d01915f3a44cdcc1cf585b7da0d67e87831f36e248e5f53439a47d8d`.

Guardrail: these files are not independent browser modules. Keep `future.html` loading `/future-assets/future.js`; do not load the parts as separate scripts until shared runtime state is converted intentionally.

## Pass 9 Validation

- `node FUTURE\tools\build_future_js.cjs --check`: passed; 21 parts rebuild `FUTURE/web/future.js` with SHA-256 `9517d176d01915f3a44cdcc1cf585b7da0d67e87831f36e248e5f53439a47d8d`.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `future_html_bytes`, `frontend_delivery_signature`, `frontend_asset_path_from_route`: passed.
- Local frontend JS split smoke server: `http://127.0.0.1:8884/login`.
- HTTP checks passed for `/frontend-version`, `/login`, `/future-assets/future.css`, `/future-assets/future.js`, `/future-assets/js_parts/01_bootstrap_guard_ai_agent.js`, and `/health`.
- Smoke server process `20416` was stopped after validation; stderr log was empty.

## Pass 10 Frontend CSS Split

`FUTURE/web/future.css` remains the single browser-served stylesheet entrypoint, but its source is now split into ordered chunks under `FUTURE/web/css_parts/`.

- Split method: brace-aware scanner at top-level CSS rule boundaries, preserving strings and comments.
- Parts: 12 ordered files, each mapped in `FUTURE/web/css_parts/manifest.json`.
- Rebuild command: `node FUTURE\tools\build_future_css.cjs`.
- Check command: `node FUTURE\tools\build_future_css.cjs --check`.
- Source checksum after split: `bb7406f4bf4beaa5c6d8c62d3fe47542e2d365baa5897ff19d60cb1714f9aa9e`.

Guardrail: keep `future.html` loading `/future-assets/future.css`; do not load the parts as separate stylesheets until cascade dependencies are mapped. The split preserves the current stylesheet byte-for-byte, including one top-level unmatched closing brace already present in the original CSS.

## Pass 10 Validation

- `node FUTURE\tools\build_future_css.cjs --check`: passed; 12 parts rebuild `FUTURE/web/future.css` with SHA-256 `bb7406f4bf4beaa5c6d8c62d3fe47542e2d365baa5897ff19d60cb1714f9aa9e`.
- `node FUTURE\tools\build_future_js.cjs --check`: passed; 21 parts rebuild `FUTURE/web/future.js` with SHA-256 `9517d176d01915f3a44cdcc1cf585b7da0d67e87831f36e248e5f53439a47d8d`.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `future_html_bytes`, `frontend_delivery_signature`, `frontend_asset_path_from_route`: passed.
- Local frontend CSS split smoke server: `http://127.0.0.1:8885/login`.
- HTTP checks passed for `/frontend-version`, `/login`, `/future-assets/future.css`, `/future-assets/future.js`, `/future-assets/css_parts/01_base_shell_layout.css`, `/future-assets/js_parts/01_bootstrap_guard_ai_agent.js`, and `/health`.
- Smoke server process `9228` was stopped after validation; stderr log was empty.

## Pass 11 Status Dashboard Fragment Split

`FUTURE/server_parts/vocab_build_status/03_status_page.py` remains the Python runtime file loaded by the server, but its source is now split into ordered fragments under `FUTURE/server_parts/vocab_build_status/status_page_parts/`.

- Split method: marker-based source fragments around dashboard `<style>`, body markup, and `<script>`.
- Parts: 8 ordered `.pyfrag` files, each mapped in `status_page_parts/manifest.json`.
- Rebuild command: `node FUTURE\tools\build_status_page.cjs`.
- Check command: `node FUTURE\tools\build_status_page.cjs --check`.
- Source checksum after split: `f1d1b3595101a91e05b8be41a47b71f7a88dc70b32982de670d7fb37735683cd`.

Guardrail: these fragments are not standalone Python modules. The dashboard is still one Python f-string, so preserve doubled braces inside embedded CSS/JavaScript until the dashboard is intentionally extracted into template/assets.

## Pass 11 Validation

- `node FUTURE\tools\build_status_page.cjs --check`: passed; 8 parts rebuild `FUTURE/server_parts/vocab_build_status/03_status_page.py` with SHA-256 `f1d1b3595101a91e05b8be41a47b71f7a88dc70b32982de670d7fb37735683cd`.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `status_page`, generated doctype, dashboard `<script>`, title text, and HTML byte size: passed.
- Local status dashboard smoke server: `http://127.0.0.1:8886/status`.
- HTTP checks passed for `/frontend-version`, `/status`, `/login`, `/future-assets/future.css`, `/future-assets/future.js`, and `/health`.
- Smoke server process `15460` was stopped after validation; stderr log was empty.

## Pass 12 POST Route Fragment Split

`FUTURE/server_parts/http_server/04_handler_post_routes.py` remains the handler method file loaded into `FutureWhisperHandler`, but its source is now split into ordered route-family fragments under `FUTURE/server_parts/http_server/post_route_parts/`.

- Split method: marker-based source fragments at major `if path ...` route family boundaries.
- Parts: 7 ordered `.pyfrag` files, each mapped in `post_route_parts/manifest.json`.
- Rebuild command: `node FUTURE\tools\build_post_routes.cjs`.
- Check command: `node FUTURE\tools\build_post_routes.cjs --check`.
- Source checksum after split: `eaf6d9cdd2065d01a41005206618cfa5ce9f16d7aea7f3cc834c652cf065348a`.

Guardrail: these fragments are not standalone Python modules. Keep route order stable until each route family is converted into explicit helper methods with targeted POST smoke tests.

## Pass 12 Validation

- `node FUTURE\tools\build_post_routes.cjs --check`: passed; 7 parts rebuild `FUTURE/server_parts/http_server/04_handler_post_routes.py` with SHA-256 `eaf6d9cdd2065d01a41005206618cfa5ce9f16d7aea7f3cc834c652cf065348a`.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler.do_POST`, `FutureWhisperHandler.do_GET`, and HTTP part order: passed.
- Local POST route smoke server: `http://127.0.0.1:8887/login`.
- GET checks passed for `/frontend-version`, `/login`, `/status`, and `/health`.
- POST checks passed for `/dashboard/ping` (`200`), `/dashboard/close` (`202`), and a missing POST route (`404`).
- Smoke server process `18776` was stopped after validation; stderr log was empty.

## Pass 13 GET Route Fragment Split

`FUTURE/server_parts/http_server/03_handler_get_routes.py` remains the handler method file loaded into `FutureWhisperHandler`, but its source is now split into ordered route-family fragments under `FUTURE/server_parts/http_server/get_route_parts/`.

- Split method: marker-based source fragments at major `if path ...` route family boundaries.
- Parts: 6 ordered `.pyfrag` files, each mapped in `get_route_parts/manifest.json`.
- Rebuild command: `node FUTURE\tools\build_get_routes.cjs`.
- Check command: `node FUTURE\tools\build_get_routes.cjs --check`.
- Source checksum after split: `a3d26b7fe7c68eba68dde6e177922a02d97eb398e99dc527da9de93303c12e2a`.

Guardrail: these fragments are not standalone Python modules. Keep route order stable until each route family is converted into explicit helper methods with targeted GET smoke tests.

## Pass 13 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed; 6 parts rebuild `FUTURE/server_parts/http_server/03_handler_get_routes.py` with SHA-256 `a3d26b7fe7c68eba68dde6e177922a02d97eb398e99dc527da9de93303c12e2a`.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler.do_GET`, `FutureWhisperHandler.do_POST`, `send_json`, and HTTP part order: passed.
- Local GET route smoke server: `http://127.0.0.1:8888/login`.
- GET checks passed for `/frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, and `/health`.
- Missing GET route returned `404`; POST `/dashboard/ping` still returned `200`.
- Smoke server process `19340` was stopped after validation; stderr log was empty.

## Pass 14 AI/Language Split

`FUTURE/server_parts/04_ai_language_agents.py` now loads these ordered nested parts:

- `01_chat_translation_voice.py`: builder imports, chat translation helpers, voice catalog, queued chat TTS.
- `02_gemini_keys_models.py`: Gemini key loading, model discovery, cooldowns, error classification, model requests.
- `03_ai_agent_requests.py`: loader for deeper AI-agent sanitizer/context, Gemini request family, notice/follow-up, and shared state parts.
- `04_ai_agent_history.py`: per-user AI agent history read/write/list/save/remove helpers.
- `05_word_agent_core_history.py`: Word Agent key/detail/example normalization and history cache.
- `06_phonetic_ipa.py`: phonetic/IPA cache, dictionary lookup, phonemizer fallback, warmup, maps.
- `07_word_agent_gemini.py`: Word Agent save and Gemini Vietnamese word/phrase explanation requests.

Guardrail: this remains a shared-namespace transitional split. Preserve Gemini cooldown/quota behavior and Word Agent/phonetic cache schemas.

## Pass 14 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `chat_translate_text`, `chat_voice_option_payload`, `load_gemini_api_keys`, `request_gemini_model_once`, `sanitize_ai_agent_vietnamese_reply`, `build_ai_agent_notice`, `list_ai_agent_history`, `word_agent_key`, `get_word_agent_history_cache`, `phonetic_ipa_key`, `phonetic_ipa_map_for_terms`, and `request_gemini_word_vietnamese_explanation`: passed.
- Local AI/language smoke server: `http://127.0.0.1:8889/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `10944` was stopped after validation; port `8889` had no listener afterward and stderr log was empty.

## Pass 15 Users/Auth/Settings Split

`FUTURE/server_parts/02_users_auth_settings.py` now loads these ordered nested parts:

- `01_users_admin_listing.py`: username validation, user file helpers, admin helpers, dashboard user listing, and user data flags.
- `02_user_delete_cleanup.py`: safe user-path deletion, runtime state cleanup, known-state pruning, and full user data deletion.
- `03_server_data_profile.py`: server-data user folders, profile read/normalize/save helpers, and `auth_me` payload/cache helpers.
- `04_user_preferences.py`: per-user UI/audio/profile-notice preferences and preference normalization/save helpers.
- `05_auth_registration.py`: login checks, auth session persistence, cookie token helpers, pending registration submit/approval/list helpers.
- `06_announcements.py`: announcement text normalization and announcement load/save helpers.
- `07_server_settings.py`: leaderboard reaction/reward settings, QM City settings, public settings, and load/save server settings.

Guardrail: this remains a shared-namespace transitional split. Preserve auth-session replacement/revocation behavior, safe deletion root checks, and `auth_me` cache invalidation around profile/preference/admin/user-delete changes.

## Pass 15 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `normalize_username`, `validate_username`, `dashboard_admin_payload`, `safe_delete_user_path`, `delete_user_data`, `server_data_user_folder_path`, `read_user_profile`, `auth_me_payload`, `normalize_user_preferences`, `save_user_preferences`, `check_user_login`, `create_auth_session`, `auth_session_state_for_token`, `submit_pending_registration`, `list_pending_registrations`, `load_announcements`, `save_announcements`, `normalize_server_settings`, `public_server_settings`, `load_server_settings`, and `save_server_settings`: passed.
- Local users/auth/settings smoke server: `http://127.0.0.1:8890/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `8048` was stopped after validation; port `8890` had no listener afterward and stderr log was empty.

## Pass 16 Chat/Paint Split

`FUTURE/server_parts/03_chat_paint_runtime.py` now loads these ordered nested parts:

- `01_chat_state_activity.py`: chat JSON state, online markers, user activity tracking, and recent-online detection.
- `02_chat_attachments_quota.py`: attachment naming, URLs, MIME detection, upload save, safe path resolution, deletion, cleanup, and quota enforcement.
- `03_chat_messages_admin.py`: message creation, read markers, user/admin message views, unread counts, recent lesson activity, and admin chat dashboard state.
- `04_paint_board.py`: paint board data validation, cursor normalization, public state, canvas updates, and cursor updates.

Guardrail: this remains a shared-namespace transitional split. Preserve attachment root checks/quota cleanup, message read-marker semantics, and paint revision behavior.

## Pass 16 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `load_chat_state_locked`, `save_chat_state_locked`, `chat_mark_online`, `mark_user_activity`, `chat_safe_filename`, `save_chat_attachment`, `safe_chat_attachment_path`, `clear_chat_for_user`, `enforce_chat_attachment_quota_locked`, `chat_add_message`, `chat_messages_for`, `chat_admin_state`, `normalize_paint_data`, `paint_public_state`, `paint_update_state`, and `paint_update_cursor`: passed.
- Local chat/paint smoke server: `http://127.0.0.1:8891/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `13372` was stopped after validation; port `8891` had no listener afterward and stderr log was empty.

## Pass 17 Stream/Screen/Security Split

`FUTURE/server_parts/05_stream_screen_security.py` now loads these ordered nested parts:

- `01_stream_sessions.py`: dashboard online state, audio stream sessions, WebRTC stream signaling, stream chunks, and stream cleanup.
- `02_screen_sessions.py`: screen preview sessions, WebRTC screen signaling, frame polling, remote-control command normalization, and control polling.
- `03_security_health.py`: local/private host checks, origin normalization, hosted frontend obfuscation decision, CORS allow-listing, and public health payload.

Guardrail: this remains a shared-namespace transitional split. Preserve stream/screen session state names, WebRTC candidate version/id behavior, and local/private host plus CORS decisions.

## Pass 17 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `dashboard_is_online`, `stream_public_session`, `stream_webrtc_state`, `stream_cleanup_locked`, `stream_request`, `stream_submit_signal`, `stream_poll_chunks`, `screen_public_session`, `screen_webrtc_state`, `screen_cleanup_locked`, `screen_request`, `screen_submit_signal`, `normalize_screen_control_command`, `screen_poll_control`, `is_local_client`, `is_private_or_local_host`, `allowed_cors_origin`, `should_serve_obfuscated_frontend`, and `public_health_payload`: passed.
- Local stream/screen/security smoke server: `http://127.0.0.1:8892/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `8740` was stopped after validation; port `8892` had no listener afterward and stderr log was empty.

## Pass 18 Core Runtime Split

`FUTURE/server_parts/01_core_runtime.py` now loads these ordered nested parts:

- `01_clean_cpu_work_queue.py`: text cleanup, bounded env integers, CPU sampling/guard state, `FutureWorkQueue`, queue singletons, and workload snapshots.
- `02_sort_anti_robot.py`: natural sort keys and anti-robot challenge secret, token, rate-limit, signature, and browser-like request helpers.
- `03_path_asset_guards.py`: path cleanup, Cloudflare hostname/tunnel normalization, public path blocking, server asset guards, and chat attachment file-type guard.
- `04_time_debug_logging.py`: local/UTC timestamp helpers, timestamp parsing, month window helper, STT debug log, and fault-handler logging setup.

Guardrail: this remains a shared-namespace transitional split. Preserve work-queue singleton creation order, public path/asset guards, and anti-robot token timing/signature behavior.

## Pass 18 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `clean`, `bounded_env_int`, `apply_cpu_guard_settings`, `cpu_guard_settings_snapshot`, `current_system_cpu_percent`, `FutureWorkQueue`, `server_workload_snapshot`, `natural_sort_key`, `anti_robot_secret`, `make_anti_robot_token`, `verify_anti_robot_token`, `anti_robot_browser_like`, `clean_path_value`, `normalize_cloudflare_public_hostname`, `path_is_inside`, `assert_public_file_allowed`, `assert_server_asset_allowed`, `assert_chat_attachment_allowed`, `local_timestamp`, `utc_timestamp`, `timestamp_to_epoch`, `stt_debug_log`, and `enable_stt_fault_logging`: passed.
- Work queue singleton check for `ghost_eye`, `pdf_render`, `translate`, and `voice`: passed.
- Local core runtime smoke server: `http://127.0.0.1:8893/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `32` was stopped after validation; port `8893` had no listener afterward and stderr log was empty.

## Pass 19 AI-Agent Request Split

`FUTURE/server_parts/ai_language_agents/03_ai_agent_requests.py` now loads these ordered deeper parts:

- `01_sanitize_context.py`: Vietnamese/English reply sanitizers, token estimate, runtime context scrubber, and Space_V/Space_P/Space_Q context checks.
- `02_translation_english_reply.py`: Gemini Vietnamese translation request and main English AI-agent reply request.
- `03_qm_city_npc_reply.py`: QM-City NPC Gemini chat-bubble reply request.
- `04_vietnamese_reply.py`: Vietnamese AI-agent reply request using English answer/context as reference.
- `05_pdf_explanation.py`: Ghost Eye PDF/Text-to-Explore Vietnamese explanation request.
- `06_notice_followup.py`: AI-agent notice assembly, voice payload, metrics, and Space_P follow-up question generation.
- `07_shared_agent_state.py`: shared locks and caches used by AI-agent history, Word Agent history, and phonetic IPA parts loaded after this request loader.

Guardrail: this remains a shared-namespace transitional split. Preserve Gemini fallback/cooldown/quota behavior, hidden-answer safety prompts/context scrubber rules, and keep shared state loaded last before later AI-language parts.

## Pass 19 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `sanitize_ai_agent_vietnamese_reply`, `normalize_ai_agent_answer_mode`, `sanitize_ai_agent_english_reply`, `estimate_ai_agent_token_count`, `ai_agent_scrub_runtime_context`, `ai_agent_context_hints`, `request_gemini_vietnamese_translation`, `request_gemini_english_reply`, `request_gemini_qm_city_npc_reply`, `request_gemini_vietnamese_reply`, `request_gemini_pdf_vietnamese_explanation`, `build_ai_agent_notice`, and `build_ai_agent_space_p_followup`: passed.
- Shared state check for `AI_AGENT_HISTORY_LOCK`, `WORD_AGENT_HISTORY_CACHE`, and `PHONETIC_IPA_CACHE`: passed.
- Local AI-agent request smoke server: `http://127.0.0.1:8894/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `13864` was stopped after validation; port `8894` had no listener afterward and stderr log was empty.

## Pass 20 Server-Data Manifest/Listing Split

`FUTURE/server_parts/server_data_pdf_qmdict/04_server_data_manifest_listing.py` now loads these ordered deeper parts:

- `01_manifest_build_scan.py`: manifest skip rules, folder/file counting, entry creation, folder scanning, count enrichment, and full manifest build.
- `02_manifest_cache_refresh.py`: manifest disk cache load, rebuild/get/dirty state, scheduled rebuild/path refresh, signature monitor, and startup monitor.
- `03_manifest_query_cache.py`: manifest entry queries, folder count helpers, list cache signatures, response cache, and file-byte cache.
- `04_lesson_completion.py`: server-data lesson completion recording, study block updates, vocabulary recording, mission archive, learning stats, and activity update.
- `05_list_server_data.py`: main `list_server_data` payload assembly and server-data list cache clearing.
- `06_link_copy_mission_cleanup.py`: unique child paths, file/folder link creation, immediate mission path parsing, and immediate mission cleanup.
- `07_operations_read.py`: link owner helpers, user operation validation, server-data operations, and file read cache access.

Guardrail: this remains a shared-namespace transitional split. Preserve safe path checks, user/admin ownership checks, manifest dirty/cache invalidation behavior, and keep `list_server_data` as one part until route-level tests exist.

## Pass 20 Validation

- `node FUTURE\tools\build_get_routes.cjs --check`: passed.
- `node FUTURE\tools\build_post_routes.cjs --check`: passed.
- `node FUTURE\tools\build_status_page.cjs --check`: passed.
- `node FUTURE\tools\build_future_css.cjs --check`: passed.
- `node FUTURE\tools\build_future_js.cjs --check`: passed.
- `new Function(FUTURE/web/future.js)`: passed.
- `python -m compileall -q FUTURE_SERVER.py FUTURE`: passed.
- Import check for `main`, `FutureWhisperHandler`, `server_data_manifest_skip_tops`, `server_data_folder_counts`, `server_data_manifest_entry`, `scan_server_data_manifest_folder`, `build_server_data_manifest`, `load_server_data_manifest_from_disk`, `rebuild_server_data_manifest`, `get_server_data_manifest`, `refresh_server_data_manifest_now`, `refresh_server_data_manifest_paths_now`, `start_server_data_manifest_monitor`, `server_data_manifest_root_entry`, `server_data_manifest_folder_entries`, `server_data_manifest_folder_counts`, `server_data_list_cache_signature`, `get_cached_server_data_list`, `cached_server_data_file_bytes`, `record_lesson_completion`, `list_server_data`, `clear_server_data_list_cache`, `server_data_unique_child_path`, `write_server_data_file_link`, `copy_server_data_folder_as_links`, `clear_server_data_immediate_mission_item`, `validate_user_server_data_operation`, `server_data_operation`, and `read_server_data_file`: passed.
- Local server-data manifest/listing smoke server: `http://127.0.0.1:8895/login`.
- HTTP checks passed for `GET /frontend-version`, `/login`, `/status`, `/settings`, `/announcements`, `/future-assets/future.css`, `/future-assets/future.js`, `/health`, and `POST /dashboard/ping`.
- Smoke server PID `13304` was stopped after validation; port `8895` had no listener afterward and stderr log was empty.

## Next Server Split Targets

- Convert `process_frontend_runtime/06_frontend_delivery.py` into a true importable module first; it has the cleanest public API and smallest dependency surface.
- Then convert process/PID helpers and dashboard watcher from `process_frontend_runtime/02_tunnel_process_dashboard.py`.
- Then isolate cache state for `server_data_pdf_qmdict/04_server_data_manifest_listing.py` and `server_data_pdf_qmdict/05_picture_pdf_render.py`.
- Then split large world/game subparts only after route usage is documented, especially `vocab_world_game/03_shared_world_core.py`, `04_shared_world_battle.py`, and `05_qm_city_training.py`.
- Then convert one `http_server/post_route_parts/` family at a time into helper methods with targeted POST tests.
- Then convert one `http_server/get_route_parts/` family at a time into helper methods with targeted GET tests.
- Then refine `vocab_build_status/status_page_parts/` into real dashboard template/assets after documenting injected values and browser-side handlers.

## Next Frontend Split Targets

- Refine `FUTURE/web/js_parts/` from mechanical chunks into semantic groups after testing the app flows each group owns.
- Later choose true browser modules only after shared runtime state is moved behind explicit namespaces.
- Refine `FUTURE/web/css_parts/` from mechanical chunks into semantic UI-domain files after visual smoke tests cover each area.
