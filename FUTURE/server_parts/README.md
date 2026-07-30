# Future Server Parts

These files are loaded by `FUTURE/server_app.py` in the order listed by `SERVER_PART_FILES`.

This is a transitional split: every part is executed into the shared Future server runtime namespace so existing global state and cross-calls keep working. Do not import these files directly yet.

## Order

1. `01_core_runtime.py`: shared helpers, path guards, timestamps, debug logging.
2. `02_users_auth_settings.py`: users, profiles, auth sessions, settings.
3. `03_chat_paint_runtime.py`: chat state, attachments, paint board helpers.
4. `04_ai_language_agents.py`: translation, Gemini, AI agent, word/phonetic helpers.
5. `05_stream_screen_security.py`: stream/screen sessions, origins, public health.
6. `06_process_frontend_runtime.py`: model/process/tunnel/STT worker and frontend delivery.
7. `07_server_data_pdf_qmdict.py`: server-data listing, PDF/picture rendering, QmDict helpers.
8. `08_progress_inventory_vocab.py`: Space progress, inventory, assets, vocabulary registry.
9. `09_vocab_world_game.py`: vocabulary leaderboard, shared world, battle/game systems.
10. `10_vocab_build_status.py`: Space_W vocabulary build flow and status dashboard HTML.
11. `11_http_server.py`: multipart parsing, HTTP server classes, route handlers, `main()`.

## Next Step

Convert one part at a time into a true module only after its inputs and outputs are explicit. Start with small low-dependency areas such as frontend delivery or PID/process helpers.
