# Process And Frontend Runtime Parts

These files are loaded by `FUTURE/server_parts/06_process_frontend_runtime.py` into the shared Future server runtime namespace.

This is a nested transitional split. The files are smaller and easier to reason about, but they still share globals with the rest of the server. Do not import them directly yet.

## Order

1. `01_model_paths.py`: word normalization, model folder resolution, PATH configuration, local IP discovery.
2. `02_tunnel_process_dashboard.py`: Cloudflare tunnel setup, PID files, process cleanup, dashboard auto-shutdown.
3. `03_local_stt_runtime.py`: local in-process Faster-Whisper model loading, queue, and preload helpers.
4. `04_stt_worker_bridge.py`: detached STT worker bridge, speech scoring, token analysis.
5. `05_payload_assets_storage.py`: JSON/HTML bytes, FTG payload encoding, lesson document IO, server asset path guards, atomic writes.
6. `06_frontend_delivery.py`: frontend asset cache, gzip cache, `/future-assets` helpers, hosted obfuscation build, frontend warm cache.

## Next Step

`06_frontend_delivery.py` is the best first candidate for a true importable module because it has a visible API and mostly depends on paths, cache locks, and small helpers.
