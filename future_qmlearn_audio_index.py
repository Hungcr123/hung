"""Persisted QmDict audio availability index.

The index is a derived cache: QmDict supplies the logical word key and workers
register the exact file they wrote.  Startup loads this small metadata file and
never scans the large QMLearn audio folders.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


QMLEARN_ROOT = Path(os.environ.get("FUTURE_QMLEARN_ROOT") or r"C:\QMLearn")
QMLEARN_DATA_ROOT = QMLEARN_ROOT / "Data"
SERVER_DATA_ROOT = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT") or r"C:\server data")
INDEX_FILE = SERVER_DATA_ROOT / "_future_qmlearn_audio_asset_index.json"
VERSION = 1
_LOCK = threading.RLock()
_STATE: dict | None = None
_DIRTY = False
_DIRTY_AT = 0.0
_LAST_UPDATE = 0.0
_WRITER_STARTED = False
_WAKE = threading.Condition(_LOCK)


def _clean(value: object = "") -> str:
    return str(value or "").strip()


def _key(word_key: object, voice: object) -> str:
    return f"{_clean(voice).lower()}|{_clean(word_key).lower()}"


def _empty() -> dict:
    return {"version": VERSION, "updated_at": "", "catalog": {"signature": "", "english": [], "vietnamese": []}, "assets": {}}


def _load_locked() -> dict:
    global _STATE
    if isinstance(_STATE, dict):
        return _STATE
    payload = _empty()
    try:
        raw = json.loads(INDEX_FILE.read_text(encoding="utf-8-sig", errors="replace"))
        if isinstance(raw, dict) and isinstance(raw.get("assets"), dict):
            payload.update({
                "version": int(raw.get("version", VERSION) or VERSION),
                "updated_at": _clean(raw.get("updated_at")),
                "catalog": raw.get("catalog") if isinstance(raw.get("catalog"), dict) else payload["catalog"],
                "assets": raw["assets"],
            })
    except Exception:
        pass
    _STATE = payload
    return payload


def load_qmlearn_audio_index() -> dict:
    with _LOCK:
        return _load_locked()


def lookup_qmlearn_audio_asset(word_key: object, voice: object) -> dict:
    with _LOCK:
        row = _load_locked()["assets"].get(_key(word_key, voice))
        return dict(row) if isinstance(row, dict) else {}


def qmlearn_audio_assets_snapshot() -> dict[str, dict]:
    with _LOCK:
        return {key: dict(row) for key, row in _load_locked()["assets"].items() if isinstance(row, dict)}


def sync_qmlearn_audio_qmdict_catalog(signature: object, english_words: object, vietnamese_meanings: object) -> dict:
    """Apply QmDict membership changes without inspecting audio directories."""
    english = {_clean(item).lower() for item in (english_words or []) if _clean(item)}
    vietnamese = {" ".join(_clean(item).lower().split()) for item in (vietnamese_meanings or []) if _clean(item)}
    with _WAKE:
        state = _load_locked()
        catalog = state.setdefault("catalog", {})
        old_signature = _clean(catalog.get("signature"))
        if old_signature == _clean(signature) and catalog.get("english") and catalog.get("vietnamese"):
            return {"changed": False, "removed": 0, "english": len(english), "vietnamese": len(vietnamese)}
        removed = 0
        for asset_key in list(state["assets"]):
            voice, word_key = asset_key.split("|", 1) if "|" in asset_key else ("", "")
            valid = word_key in (english if voice in {"sot:en-gb", "sot:en-us"} else vietnamese if voice == "sot:vi-vn" else set())
            if not valid and voice in {"sot:en-gb", "sot:en-us", "sot:vi-vn"}:
                state["assets"].pop(asset_key, None)
                removed += 1
        catalog.update({"signature": _clean(signature), "english": sorted(english), "vietnamese": sorted(vietnamese)})
        global _DIRTY, _DIRTY_AT, _LAST_UPDATE
        now = time.time()
        _DIRTY = True
        _DIRTY_AT = _DIRTY_AT or now
        _LAST_UPDATE = now
        _ensure_writer()
        _WAKE.notify()
        return {"changed": True, "removed": removed, "english": len(english), "vietnamese": len(vietnamese)}


def _writer() -> None:
    global _DIRTY, _DIRTY_AT, _LAST_UPDATE
    while True:
        with _WAKE:
            while not _DIRTY:
                _WAKE.wait()
            remaining = min(5.0 - (time.time() - _LAST_UPDATE), 120.0 - (time.time() - _DIRTY_AT))
            if remaining > 0:
                _WAKE.wait(timeout=max(0.1, remaining))
                continue
            snapshot = dict(_load_locked())
            snapshot["assets"] = dict(snapshot.get("assets") or {})
            snapshot["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _DIRTY = False
            _DIRTY_AT = 0.0
        try:
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp = INDEX_FILE.with_suffix(INDEX_FILE.suffix + ".tmp")
            temp.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            os.replace(temp, INDEX_FILE)
        except Exception:
            with _WAKE:
                _DIRTY = True
                _DIRTY_AT = _DIRTY_AT or time.time()


def _ensure_writer() -> None:
    global _WRITER_STARTED
    with _WAKE:
        if _WRITER_STARTED:
            return
        _WRITER_STARTED = True
        threading.Thread(target=_writer, daemon=True, name="qmlearn-audio-index-writer").start()


def register_qmlearn_audio_asset(word_key: object, word: object, voice: object, relative_path: object, revision: object = "") -> None:
    global _DIRTY, _DIRTY_AT, _LAST_UPDATE
    rel = _clean(relative_path).replace("/", "\\")
    if not rel or not _clean(word_key) or not _clean(voice):
        return
    try:
        candidate = (QMLEARN_DATA_ROOT / rel).resolve()
        candidate.relative_to(QMLEARN_DATA_ROOT.resolve())
    except Exception:
        return
    with _WAKE:
        state = _load_locked()
        state["assets"][_key(word_key, voice)] = {"word": _clean(word), "voice": _clean(voice), "path": rel, "revision": _clean(revision)}
        now = time.time()
        _DIRTY = True
        _DIRTY_AT = _DIRTY_AT or now
        _LAST_UPDATE = now
        _ensure_writer()
        _WAKE.notify()


def qmlearn_audio_index_stats() -> dict:
    with _LOCK:
        state = _load_locked()
        assets = state.get("assets") or {}
        catalog = state.get("catalog") if isinstance(state.get("catalog"), dict) else {}
        return {
            "version": VERSION,
            "assets": len(assets),
            "catalog_signature": _clean(catalog.get("signature")),
            "english": len(catalog.get("english") or []),
            "vietnamese": len(catalog.get("vietnamese") or []),
            "index_file": str(INDEX_FILE),
            "loaded": True,
        }
