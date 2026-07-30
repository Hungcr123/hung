"""Probe whether localhost Codex login cookie authenticates /auth/me."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]


def scoped_env() -> dict[str, str]:
    env = dict(os.environ)
    domains = (
        "AI_HISTORY_DOCUMENTS", "ANNOUNCEMENTS", "APPEND_EVENTS", "AUTH", "CHAT", "INVENTORY",
        "LEADERBOARD_DOCUMENTS", "LEARNING_SUMMARY_DOCUMENTS", "LESSON_FOLDER_LINKS", "LESSON_IDENTITY",
        "LESSON_LAST_FILE", "LESSON_PROGRESS", "LESSON_TASK", "LESSON_TASK_NOTICES", "LESSON_TIME",
        "PDF_DRAWINGS", "QMDICT_DOCUMENTS", "QM_CITY_DOCUMENTS", "SPACE_PDF_AI_DOCUMENTS",
        "SPACE_W_SPEAK_SKIP", "USER_AUTH_DOCS", "USER_PREFERENCES", "VAULT_METADATA",
        "VIEWER_TOOL_DOCUMENTS", "VOCABULARY", "VOCAB_IMAGE_CACHE",
    )
    for domain in domains:
        env[f"FUTURE_DB_{domain}_BACKEND"] = "postgres"
    env["FUTURE_POSTGRES_ONLY"] = "1"
    env.pop("FUTURE_DB_BACKEND", None)
    env.pop("FUTURE_POSTGRES_BACKEND", None)
    return env


def main() -> int:
    env = scoped_env()
    stdout = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\auth_cookie_probe_18877.out.log")
    stderr = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\auth_cookie_probe_18877.err.log")
    old = requests.get("http://127.0.0.1:18877/health", timeout=2) if False else None
    if old is not None:
        pass
    proc = subprocess.Popen([sys.executable, "FUTURE_SERVER_2.py", "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"], cwd=str(ROOT), stdout=stdout.open("wb"), stderr=stderr.open("wb"), env=env)
    try:
        deadline = time.time() + 90
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited early: {proc.returncode}")
            try:
                health = requests.get("http://127.0.0.1:18877/health", timeout=4)
                if health.status_code == 200 and health.json().get("ok"):
                    break
            except Exception:
                pass
            time.sleep(1)
        s = requests.Session()
        login = s.get("http://127.0.0.1:18877/auth/codex-local-login?marker=1&username=hung&next=/status", allow_redirects=False, timeout=30)
        me = s.get("http://127.0.0.1:18877/auth/me", timeout=30)
        print({"login_status": login.status_code, "set_cookie": login.headers.get("Set-Cookie", ""), "cookies": s.cookies.get_dict(), "me_status": me.status_code, "me_text": me.text[:160]})
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
