#!/usr/bin/env python3
"""Prove a failed sound-index snapshot write recovers from the exact-entry WAL."""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import future_sound_asset_index as indexer


RUN_ROOT = ROOT / "programe_cache" / "sound_index_write_failure"


def main() -> int:
    if RUN_ROOT.exists():
        shutil.rmtree(RUN_ROOT)
    sound_root = RUN_ROOT / "Sound"
    sound_root.mkdir(parents=True)
    payload = b"sound-index-write-failure-recovery"
    digest = hashlib.sha1(payload).hexdigest()
    target = sound_root / "_v2" / "chat" / f"asset_{digest}.wav"
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)

    originals = {
        "SERVER_DATA_ROOT": indexer.SERVER_DATA_ROOT,
        "SERVER_SOUND_DIR": indexer.SERVER_SOUND_DIR,
        "SERVER_SOUND_V2_DIR": indexer.SERVER_SOUND_V2_DIR,
        "SOUND_ASSET_INDEX_FILE": indexer.SOUND_ASSET_INDEX_FILE,
        "SOUND_ASSET_INDEX_WAL_FILE": indexer.SOUND_ASSET_INDEX_WAL_FILE,
        "SOUND_ASSET_INDEX_RAM": indexer.SOUND_ASSET_INDEX_RAM,
        "SOUND_ASSET_INDEX_DIRTY": indexer.SOUND_ASSET_INDEX_DIRTY,
        "atomic_write_text": indexer.atomic_write_text,
        "schedule_sound_asset_index_flush": indexer.schedule_sound_asset_index_flush,
    }
    try:
        indexer.SERVER_DATA_ROOT = RUN_ROOT
        indexer.SERVER_SOUND_DIR = sound_root
        indexer.SERVER_SOUND_V2_DIR = sound_root / "_v2"
        indexer.SOUND_ASSET_INDEX_FILE = RUN_ROOT / "_future_sound_asset_index.json"
        indexer.SOUND_ASSET_INDEX_WAL_FILE = RUN_ROOT / "_future_sound_asset_index.wal.jsonl"
        indexer.SOUND_ASSET_INDEX_RAM = None
        indexer.SOUND_ASSET_INDEX_DIRTY = False
        indexer.schedule_sound_asset_index_flush = lambda _delay=2.0: None

        repair = indexer.ensure_sound_asset_index_entry(target.relative_to(RUN_ROOT).as_posix())
        if not repair.get("ok") or not repair.get("index_repaired"):
            raise AssertionError(repair)
        if not indexer.SOUND_ASSET_INDEX_WAL_FILE.is_file():
            raise AssertionError("exact-entry WAL was not durable before index snapshot")

        def fail_write(_path: Path, _text: str) -> None:
            raise OSError("injected index snapshot write failure")

        indexer.atomic_write_text = fail_write
        failed = False
        try:
            indexer.write_sound_asset_index_now("injected-failure")
        except OSError:
            failed = True
        if not failed or not indexer.SOUND_ASSET_INDEX_WAL_FILE.is_file():
            raise AssertionError("failed snapshot write discarded the recovery WAL")

        indexer.atomic_write_text = originals["atomic_write_text"]
        indexer.SOUND_ASSET_INDEX_RAM = None
        recovered = indexer.load_sound_asset_index(force=True, build_if_missing=False)
        if recovered.get("assets", {}).get(repair["key"]) != repair["path"]:
            raise AssertionError("restart WAL replay did not recover exact sound entry")
        flushed = indexer.write_sound_asset_index_now("recovered")
        if not flushed.get("ok") or indexer.SOUND_ASSET_INDEX_WAL_FILE.exists():
            raise AssertionError("recovered index did not checkpoint and clear WAL")
        print("sound_index_write_failure_recovery=ok file_preserved=1 wal_preserved=1 restart_replayed=1 exact_entry=1")
        return 0
    finally:
        for name, value in originals.items():
            setattr(indexer, name, value)
        if RUN_ROOT.exists():
            shutil.rmtree(RUN_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
