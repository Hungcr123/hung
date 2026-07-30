"""Verify Server 2 returns full payloads whenever the client retries without an ETag."""

from __future__ import annotations

import os

import requests


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active test only")
    base = "http://127.0.0.1:8877"
    login = requests.post(f"{base}/auth/login", json={"username": "hung", "password": password}, timeout=15)
    login.raise_for_status()
    token = login.json().get("token", "")
    headers = {"Authorization": f"Bearer {token}"}
    routes = [
        ("settings", "/settings", {}),
        ("announcements", "/announcements", {}),
        ("last_file", "/server-data/last-file", {}),
        ("lesson_tasks", "/lesson-tasks", {"user": "hung"}),
        ("vocab_registry", "/vocab/registry", {}),
        ("vocab_top", "/vocab/leaderboard", {"limit": "80", "scope": "month", "type": "space_v"}),
    ]
    checked = []
    for name, path, params in routes:
        full = requests.get(f"{base}{path}", params=params, headers=headers, timeout=20)
        full.raise_for_status()
        etag = full.headers.get("ETag", "")
        assert full.status_code == 200 and full.content and etag, (name, full.status_code, len(full.content), etag)

        not_modified = requests.get(
            f"{base}{path}",
            params=params,
            headers={**headers, "If-None-Match": etag},
            timeout=20,
        )
        assert not_modified.status_code == 304 and not not_modified.content, (name, not_modified.status_code)

        cache_loss_retry = requests.get(f"{base}{path}", params=params, headers=headers, timeout=20)
        cache_loss_retry.raise_for_status()
        assert cache_loss_retry.status_code == 200 and cache_loss_retry.content == full.content, name
        checked.append(name)

    print(f"etag_cache_loss_fallback=ok user=hung routes={','.join(checked)} full_retry=200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
