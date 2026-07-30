# Server-Data Manifest/Listing Parts

These files are loaded by `FUTURE/server_parts/server_data_pdf_qmdict/04_server_data_manifest_listing.py` into the shared Future server runtime namespace.

This is a deeper transitional split. Keep the load order stable until the manifest/listing helpers are converted into explicit importable modules.

## Load Order

1. `01_manifest_build_scan.py`
   - Manifest skip rules, folder/file counting, entry creation, folder scanning, count enrichment, and full manifest build.

2. `02_manifest_cache_refresh.py`
   - Manifest disk cache load, rebuild/get/dirty state, scheduled rebuild/path refresh, signature monitor, and startup monitor.

3. `03_manifest_query_cache.py`
   - Manifest entry queries, folder count helpers, list cache signatures, response cache, and file-byte cache.

4. `04_lesson_completion.py`
   - Server-data lesson completion recording, study block updates, vocabulary recording, mission archive, learning stats, and activity update.

5. `05_list_server_data.py`
   - Main `list_server_data` payload assembly and server-data list cache clearing.

6. `06_link_copy_mission_cleanup.py`
   - Unique child paths, file/folder link creation, immediate mission path parsing, and immediate mission cleanup.

7. `07_operations_read.py`
   - Link owner helpers, user operation validation, server-data operations, and file read cache access.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve safe path checks and user/admin ownership checks. Server-data operations can move/copy/delete lesson files.
- Preserve manifest dirty/cache invalidation behavior around mutations, completion logging, and folder-link updates.
- Keep `list_server_data` as one part until its payload branches have route-level tests; it mixes task/progress/study/manifest state.
