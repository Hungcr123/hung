# Core Runtime Parts

These files are loaded by `FUTURE/server_parts/01_core_runtime.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the load order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_clean_cpu_work_queue.py`
   - Text cleanup, bounded env integers, CPU sampling/guard state, `FutureWorkQueue`, queue singletons, and workload snapshots.

2. `02_sort_anti_robot.py`
   - Natural sort keys and anti-robot challenge secret, token, rate-limit, signature, and browser-like request helpers.

3. `03_path_asset_guards.py`
   - Path cleanup, Cloudflare hostname/tunnel normalization, public path blocking, server asset guards, and chat attachment file-type guard.

4. `04_time_debug_logging.py`
   - Local/UTC timestamp helpers, timestamp parsing, month window helper, STT debug log, and fault-handler logging setup.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve work-queue singleton creation order; downstream modules read `SERVER_WORK_QUEUES` and the queue globals.
- Preserve public path and asset guards because they protect source/runtime files from public download routes.
- Preserve anti-robot token timing and signature behavior because auth-sensitive routes depend on those challenge strings.
