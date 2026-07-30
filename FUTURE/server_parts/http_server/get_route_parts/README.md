# GET Route Source Fragments

These files are ordered source fragments for `FUTURE/server_parts/http_server/03_handler_get_routes.py`.

`03_handler_get_routes.py` is still the handler method file loaded into `FutureWhisperHandler`. The fragments are concatenated to rebuild that file byte-for-byte.

## Route Families

1. `01_entry_frontend_status.pyfrag`
   - `do_GET` setup, favicon, anti-robot challenge, frontend assets/version, dashboard/status, app shell, health/settings/announcements.

2. `02_chat_stream_screen_paint.pyfrag`
   - Chat attachments/poll/admin state/voices, stream state/poll/signals, screen state/signals/control, paint state.

3. `03_auth_dashboard_server_data.pyfrag`
   - Auth/session/profile/inventory, dashboard logs/admins, server-data manifest/list/file, lesson tasks/notices.

4. `04_pdf_picture_render.pyfrag`
   - PDF info/prewarm/page rendering and picture info/image rendering.

5. `05_progress_vocab_leaderboard.pyfrag`
   - Space progress reads, vocabulary registry/image/history, leaderboard/chat/sync/build-status.

6. `06_world_game_assets.pyfrag`
   - Shared world, battle/training/keyboard/game state, server-data assets, QMLearn sound, fallback 404.

## Workflow

1. Edit the relevant fragment in this folder.
2. Rebuild the handler method file:

   ```powershell
   node FUTURE\tools\build_get_routes.cjs
   ```

3. Verify the runtime file matches the fragments:

   ```powershell
   node FUTURE\tools\build_get_routes.cjs --check
   ```

4. Compile/import-check the server and run HTTP smoke tests before using the app.

## Guardrails

- These fragments are not standalone Python modules.
- Keep route order stable; several routes share local/admin/auth checks and return explicitly.
- Convert one route family at a time into helper methods only after targeted GET smoke tests exist for that family.
