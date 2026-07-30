import concurrent.futures
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import FUTURE.server_app as app


ROOT = Path(r"C:\server data")
DEFAULT_SAMPLE = ROOT / r"common\Study\B1 plus Cambridge student Vocabulary Output - [147 Files] - {3551 words}\Welcome - [4 Files] - {97 words}\File 001 - {1-4}.Space_V"


def sample_space_v_path() -> Path:
    if DEFAULT_SAMPLE.is_file():
        return DEFAULT_SAMPLE
    for path in (ROOT / "common").rglob("*.Space_V"):
        if path.is_file():
            return path
    raise RuntimeError("Khong tim thay file Space_V mau trong C:\\server data\\common.")


def percentile_summary(values: list[int]) -> dict:
    if not values:
        return {}

    def pick(percent: float) -> int:
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * percent))))
        return values[index]

    return {
        "min": values[0],
        "p50": pick(0.50),
        "p90": pick(0.90),
        "p99": pick(0.99),
        "max": values[-1],
    }


def open_space_v_once(target: Path) -> dict:
    started = time.perf_counter()
    payload, meta = app.cached_space_v_qmdict_file_bytes(target)
    return {
        "ms": int((time.perf_counter() - started) * 1000),
        "bytes": len(payload),
        "hydrated": int(meta.get("hydrated", 0) or 0),
    }


def hydrated_words(target: Path, limit: int = 12) -> list[str]:
    app.cached_space_v_qmdict_file_bytes(target)
    payload, _structure_path = app.load_future_lesson_document(target)
    hydrated, _meta = app.hydrate_space_v_payload_with_qmdict(payload)
    rows = hydrated.get("w") if isinstance(hydrated.get("w"), list) else hydrated.get("words")
    words = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict):
            word = app.clean(row.get("w") or row.get("word") or "")
            if word:
                words.append(word)
        if len(words) >= limit:
            break
    return words


def audio_once(word: str, voice: str = "sot:en-GB") -> dict:
    started = time.perf_counter()
    payload, _content_type = app.read_qmlearn_data_sound_by_voice_text(word, voice)
    return {"ms": int((time.perf_counter() - started) * 1000), "bytes": len(payload)}


def run_group(label: str, fn, items: list, workers: int = 32) -> dict:
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    rows = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fn, item) for item in items]
        for future in concurrent.futures.as_completed(futures):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append(str(exc))
    wall_ms = int((time.perf_counter() - started_wall) * 1000)
    cpu_ms = int((time.process_time() - started_cpu) * 1000)
    times = sorted(int(row.get("ms", 0) or 0) for row in rows)
    return {
        "label": label,
        "count": len(items),
        "workers": workers,
        "ok": len(rows),
        "errors": errors[:5],
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "per_request_ms": percentile_summary(times),
        "bytes": rows[0].get("bytes", 0) if rows else 0,
        "hydrated": rows[0].get("hydrated", 0) if rows else 0,
    }


def main() -> None:
    target = sample_space_v_path()
    app.reload_qmdict_runtime(force=False, reason="spacev-open-probe")
    cold = open_space_v_once(target)
    warm = open_space_v_once(target)
    with app.SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
        app.SPACE_V_QMDICT_PAYLOAD_CACHE.clear()
        app.SPACE_V_QMDICT_PREFETCH_KEYS.clear()
    cold_open100 = run_group("cold_open_space_v_payload_100", lambda _idx: open_space_v_once(target), list(range(100)))
    open100 = run_group("open_space_v_payload_100", lambda _idx: open_space_v_once(target), list(range(100)))
    with app.SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
        app.SPACE_V_QMDICT_PAYLOAD_CACHE.clear()
        app.SPACE_V_QMDICT_PREFETCH_KEYS.clear()
    map_started = time.perf_counter()
    map_size = len(app.qmdict_registry_summary_maps())
    map_warm_ms = int((time.perf_counter() - map_started) * 1000)
    map_open = open_space_v_once(target)
    words = hydrated_words(target, limit=25)
    with app.QMLEARN_DATA_SOUND_BYTES_CACHE_LOCK:
        app.QMLEARN_DATA_SOUND_BYTES_CACHE.clear()
    audio_cold = [audio_once(word) for word in words]
    with app.QMLEARN_DATA_SOUND_BYTES_CACHE_LOCK:
        app.QMLEARN_DATA_SOUND_BYTES_CACHE.clear()
    audio_cold100 = run_group("cold_audio_word_100", audio_once, [words[index % len(words)] for index in range(100)] if words else [])
    audio_items = [words[index % len(words)] for index in range(100)] if words else []
    audio100 = run_group("audio_word_100", audio_once, audio_items)
    audio2500_items = [words[index % len(words)] for index in range(2500)] if words else []
    audio2500 = run_group("audio_word_2500", audio_once, audio2500_items, workers=64)
    print(json.dumps({
        "sample": str(target),
        "cold_open": cold,
        "warm_open": warm,
        "cold_open100": cold_open100,
        "open100": open100,
        "qmdict_map_warm": {"ms": map_warm_ms, "entries": map_size},
        "map_open": map_open,
        "audio_words": words,
        "audio_cold_ms": percentile_summary(sorted(row["ms"] for row in audio_cold)),
        "audio_cold100": audio_cold100,
        "audio100": audio100,
        "audio2500": audio2500,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
