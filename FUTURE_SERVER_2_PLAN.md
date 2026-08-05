# Future Server 2 Split Plan

## Goal

Create a second Future server that uses the split frontend/runtime without changing the stable monolithic `FUTURE_SERVER.py` and `future.html`.

## Design

- [x] Keep the stable server 1 files untouched: `FUTURE_SERVER.py` and `future.html`.
- [x] Restore the split frontend as `future_split.html`.
- [x] Reuse the existing split package/assets in `FUTURE/` so `PROGRAME_ROOT` remains correct.
- [x] Add environment overrides in `FUTURE/server_app.py` for frontend path, asset root, and runtime root.
- [x] Add `FUTURE_SERVER_2.py` as the second entrypoint.
- [x] Add `future_stt_worker_2.py` so server 2 does not import the monolithic server through the worker.
- [x] Clear stale worker bridge errors after successful worker health checks.
- [x] Inline split CSS in hosted/protected HTML so `qm-tech.io.vn` does not depend on a separate CSS request.
- [x] Move canonical server 2 launcher into `FUTURE/server2/run_server_2.py`.
- [x] Move canonical server 2 worker into `FUTURE/server2/future_stt_worker_2.py`.
- [x] Move split frontend shell into `FUTURE/web/future_split.html`.
- [x] Add `FUTURE/RUN_SERVER_2.bat` so server 2 can be started from inside `FUTURE/`.
- [x] Default server 2 HTTP port: `8877`.
- [x] Default server 2 STT worker port: `8878`.
- [x] Validate split CSS/JS build manifests.
- [x] Validate Python compile/import.
- [x] Validate HTTP endpoints on server 2.
- [x] Validate browser rendering and console/network health.
- [x] Validate hosted HTTPS `https://qm-tech.io.vn/future.html`.
- [x] Validate Cốc Cốc with a clean browser profile.

## Run

```powershell
python FUTURE_SERVER_2.py --no-browser --no-tunnel --no-preload
```

Preferred from inside `FUTURE/`:

```powershell
.\RUN_SERVER_2.bat
```

Open:

```text
http://127.0.0.1:8877/login
```

## Notes

- Server 1 remains on `FUTURE_SERVER.py` and normally uses port `8765`.
- Server 2 uses `future_split.html` plus `/future-assets/future.css` and `/future-assets/future.js`.
- Server 2 runtime files are isolated under `programe_cache/future_whisper_server_2`.
- Hosted/domain HTML inlines CSS and protected JS so Cốc Cốc cannot render a white unstyled page from a missing stylesheet.
