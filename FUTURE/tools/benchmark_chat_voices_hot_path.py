"""Benchmark cached chat voice catalog delivery for admin and 100 users."""

from __future__ import annotations

import concurrent.futures
import json
import os
import time

import requests

from benchmark_server2_100_users import BASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = server_process()

    def login(username: str) -> tuple[str, str]:
        response = requests.post(
            f"{BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        return username, str(response.json().get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        tokens = dict(pool.map(login, USERS))
    if len(tokens) != len(USERS) or any(not value for value in tokens.values()):
        raise RuntimeError("Could not prepare 100 distinct voice-catalog sessions")

    def phase(name: str, authenticated: bool) -> dict:
        wait_for_writer_quiescence()

        def request_one(index: int):
            username = USERS[index]
            headers = {"Authorization": f"Bearer {tokens[username]}"} if authenticated else {}
            route = "/chat/voices" if authenticated else "/chat/admin/voices"
            started = time.perf_counter()
            response = requests.get(
                f"{BASE}{route}?ts={time.time_ns()}-{index}",
                headers=headers,
                timeout=20,
            )
            decoded, wire, request_bytes = response_sizes(response)
            payload = response.json()
            return (
                (time.perf_counter() - started) * 1000,
                response.status_code,
                decoded,
                wire,
                request_bytes,
                len(payload.get("vi", [])),
                len(payload.get("en", [])),
                str(response.headers.get("X-Future-Cache-Hit") or ""),
            )

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                return list(pool.map(request_one, range(100)))

        rows, metrics = measured(process, run)
        result = {
            **metrics,
            "vi_voices": rows[0][5],
            "en_voices": rows[0][6],
            "cache_headers": {value: sum(1 for row in rows if row[7] == value) for value in sorted({row[7] for row in rows})},
        }
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    phase("CHAT_ADMIN_VOICES", authenticated=False)
    phase("CHAT_USER_VOICES", authenticated=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
