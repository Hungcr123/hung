# Server Data, PDF, And QmDict Parts

These files are loaded by `FUTURE/server_parts/07_server_data_pdf_qmdict.py` into the shared Future server runtime namespace.

This is a nested transitional split. The files are grouped by behavior and loaded in order, but they still share globals with the rest of the server. Do not import them directly yet.

## Order

1. `01_server_data_paths_links.py`: server-data path guards, relative paths, file/folder link markers.
2. `02_lesson_study_progress.py`: lesson study repair, progress summaries, study time, learning summaries.
3. `03_lesson_tasks_logs.py`: manual lesson tasks, task notices, avatars/profile cards, login/learning logs.
4. `03_space_task_auto.py`: automatic Space Task queue, preferred folder settings, per-space lesson picking.
5. `04_server_data_manifest_listing.py`: loader for server-data manifest build/cache, list/file caches, lesson completion, link/copy cleanup, operations, and file reads.
6. `05_picture_pdf_render.py`: picture/PDF path guards, image/PDF render cache, PDF metadata warming.
7. `06_ocr_qmdict_core.py`: Tesseract resolution, OCR region extraction, QmDict runtime/reload/lookup/update.
8. `07_qmlearn_audio_spacev_repair.py`: QMLearn audio lookup, QmDict meaning audio refresh, Space_V QmDict repair.
9. `08_pdf_vocab_scan.py`: PDF/picture vocabulary stats, page scan, and PDF vocabulary mission generation.

## Deeper Splits

- `server_data_manifest_listing/`: ordered source parts loaded by `04_server_data_manifest_listing.py`.

## Next Step

`05_picture_pdf_render.py` is a good candidate for deeper extraction once its cache state and render path dependencies are isolated.
