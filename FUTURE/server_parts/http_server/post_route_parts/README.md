# POST Route Source Fragments

These files are ordered source fragments for `FUTURE/server_parts/http_server/04_handler_post_routes.py`.

`04_handler_post_routes.py` is still the handler method file loaded into `FutureWhisperHandler`. The fragments are concatenated to rebuild that file byte-for-byte.

## Route Families

1. `01_entry_dashboard_admin.pyfrag`
   - `do_POST` setup, anti-robot checks, dashboard/admin controls, metadata warm, learning stats, QmDict edits.

2. `02_pdf_ocr_scan.pyfrag`
   - PDF/picture OCR, page/image vocabulary scan, PDF vocabulary creation, translate/speak routes.

3. `03_pdf_ai_tasks_auth.pyfrag`
   - AI agent, word/phonetic agent, PDF explanation, lesson task notices, profile/avatar, server-data ops, auth.

4. `04_chat_stream_screen_paint.pyfrag`
   - Chat uploads/messages, stream/screen signaling, paint sync, announcements, settings.

5. `05_vocab_progress_leaderboard.pyfrag`
   - Vocabulary mission build, Space progress saves, file stats, leaderboard actions.

6. `06_world_battle_game_lesson.pyfrag`
   - Shared world, training, battle, registry sync, inventory, vocabulary game rooms, lesson timing/completion.

7. `07_transcribe_upload.pyfrag`
   - Fallback 404 and `/transcribe` multipart audio upload/worker submission.

## Workflow

1. Edit the relevant fragment in this folder.
2. Rebuild the handler method file:

   ```powershell
   node FUTURE\tools\build_post_routes.cjs
   ```

3. Verify the runtime file matches the fragments:

   ```powershell
   node FUTURE\tools\build_post_routes.cjs --check
   ```

4. Compile/import-check the server and run HTTP smoke tests before using the app.

## Guardrails

- These fragments are not standalone Python modules.
- Keep route order stable; many routes share auth/session side effects and fall through only by explicit `return`.
- The next real refactor should extract one route family at a time into helper methods after targeted POST smoke tests are written for that family.
