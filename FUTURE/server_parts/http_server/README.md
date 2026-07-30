# HTTP Server Runtime Parts

These files are loaded by `FUTURE/server_parts/11_http_server.py` into the shared Future server runtime namespace.

This is a transitional nested split. The handler method files are executed into the `FutureWhisperHandler` class namespace, not imported as standalone modules.

## Load Order

1. `01_multipart_server.py`
   - Multipart form parsing for audio uploads.
   - `FutureThreadingHTTPServer`.

2. `02_handler_core.py`
   - Shared response helpers, CORS/security headers, auth helpers, JSON/body parsing, and `OPTIONS`.
   - `end_headers()` uses an explicit `BaseHTTPRequestHandler.end_headers(self)` call because this method is compiled outside the original class body during the transitional load.

3. `03_handler_get_routes.py`
   - All current `GET` route handling.

4. `04_handler_post_routes.py`
   - All current `POST` route handling, including dashboard control, auth, lesson/progress, vocabulary, world/game, and transcription routes.

5. `05_handler_logging.py`
   - HTTP request logging.

6. `06_main.py`
   - CLI argument parsing, startup wiring, background warm tasks, and `serve_forever()`.

## Guardrails

- Keep `03_handler_get_routes.py` and `04_handler_post_routes.py` route order stable until route dispatch is extracted into explicit handler functions.
- Do not move method files out of this folder without changing the class-loader contract in `11_http_server.py`.
- Next safe improvement is to split `04_handler_post_routes.py` by route families using helper methods or standalone route functions with explicit dependencies.
