"""Benchmark Space_V image lookup for repeated and distributed vocabulary words."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import time

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


WORDS = (
    "eyebrow", "apple", "bridge", "camera", "doctor", "engine", "forest", "guitar", "harbor", "island",
    "jacket", "kitchen", "library", "mountain", "notebook", "orange", "pencil", "queen", "river", "school",
    "teacher", "umbrella", "village", "window", "yellow", "zebra", "airport", "bicycle", "coffee", "diamond",
    "elephant", "flower", "garden", "hospital", "internet", "journey", "keyboard", "language", "market", "nature",
    "ocean", "picture", "question", "restaurant", "station", "telephone", "university", "vehicle", "water", "xylophone",
    "yogurt", "animal", "basket", "castle", "dinner", "energy", "family", "glasses", "holiday", "idea",
    "juice", "king", "lesson", "mirror", "number", "office", "people", "quiet", "radio", "street",
    "ticket", "uniform", "voice", "weather", "young", "answer", "bread", "chair", "desk", "earth",
    "friend", "green", "house", "important", "job", "letter", "music", "night", "paper", "road",
    "sun", "train", "useful", "video", "world", "year", "book", "computer", "door", "English",
)


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = server_process()

    def login(username: str) -> tuple[str, str]:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return username, str(response.json().get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        tokens = dict(pool.map(login, USERS))

    def phase(name: str, word_for_index) -> dict:
        wait_for_writer_quiescence()

        def request_one(index: int):
            username = USERS[index]
            word = word_for_index(index)
            started = time.perf_counter()
            response = requests.get(
                f"{BASE}/vocab/image?word={requests.utils.quote(word)}&ts={time.time_ns()}-{index}",
                headers={"Authorization": f"Bearer {tokens[username]}"},
                timeout=30,
            )
            decoded, wire, request_bytes = response_sizes(response)
            payload = response.json()
            image = payload.get("image") if isinstance(payload.get("image"), dict) else {}
            return (
                (time.perf_counter() - started) * 1000,
                response.status_code,
                decoded,
                wire,
                request_bytes,
                bool(image.get("u") or image.get("url")),
                bool(payload.get("pending")),
                str(response.headers.get("X-Future-Cache-Hit") or ""),
            )

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                return list(pool.map(request_one, range(100)))

        rows, metrics = measured(process, run)
        result = {
            **metrics,
            "images_found": sum(1 for row in rows if row[5]),
            "pending": sum(1 for row in rows if row[6]),
            "cache_headers": {value: sum(1 for row in rows if row[7] == value) for value in sorted({row[7] for row in rows})},
        }
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    if os.environ.get("VOCAB_IMAGE_BENCH_WARM_ONLY") == "1":
        phase("VOCAB_IMAGE_DISTRIBUTED_WARM", lambda index: WORDS[index])
        return 0
    phase("VOCAB_IMAGE_SAME", lambda _index: "Eyebrow")
    phase("VOCAB_IMAGE_DISTRIBUTED", lambda index: WORDS[index])
    writer_before = requests.get(f"{BASE}/health?view=dashboard-v1", timeout=10).json().get("postgres_writer", {})
    cpu_before = sum(process.cpu_times()[:2])
    io_before = process.io_counters()
    started = time.perf_counter()
    cached_rows = 0
    while time.perf_counter() - started < 90:
        connection = sqlite3.connect(DATABASE)
        try:
            cached_rows = int(connection.execute(
                f"SELECT COUNT(*) FROM vocab_image_cache WHERE word_key IN ({','.join('?' for _ in WORDS)}) AND expires_epoch>?",
                tuple(word.lower() for word in WORDS) + (time.time(),),
            ).fetchone()[0])
        finally:
            connection.close()
        if cached_rows >= len(WORDS):
            break
        time.sleep(0.5)
    time.sleep(1.2)
    wait_for_writer_quiescence()
    writer_after = requests.get(f"{BASE}/health?view=dashboard-v1", timeout=10).json().get("postgres_writer", {})
    io_after = process.io_counters()
    print("VOCAB_IMAGE_BACKGROUND", json.dumps({
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "server_cpu_ms": round(max(0.0, sum(process.cpu_times()[:2]) - cpu_before) * 1000, 3),
        "cached_rows": cached_rows,
        "postgres_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "process_io": {
            "read_ops": max(0, int(io_after.read_count - io_before.read_count)),
            "write_ops": max(0, int(io_after.write_count - io_before.write_count)),
            "read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
            "write_bytes": max(0, int(io_after.write_bytes - io_before.write_bytes)),
        },
    }, ensure_ascii=True), flush=True)
    phase("VOCAB_IMAGE_DISTRIBUTED_WARM", lambda index: WORDS[index])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

