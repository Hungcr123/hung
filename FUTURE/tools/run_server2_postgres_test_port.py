"""Launch Server 2 on a test port with scoped PostgreSQL-only flags.

Added 2026-07-27 for login timeline benchmarking. This avoids the
FUTURE_SERVER_2.py compatibility entrypoint because that entrypoint appends
--replace-old for manual production starts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POSTGRES_ONLY_DOMAINS = (
    "AI_HISTORY_DOCUMENTS",
    "ANNOUNCEMENTS",
    "APPEND_EVENTS",
    "AUTH",
    "CHAT",
    "INVENTORY",
    "LEADERBOARD_DOCUMENTS",
    "LEARNING_SUMMARY_DOCUMENTS",
    "LESSON_FOLDER_LINKS",
    "LESSON_IDENTITY",
    "LESSON_LAST_FILE",
    "LESSON_PROGRESS",
    "LESSON_TASK",
    "LESSON_TASK_NOTICES",
    "LESSON_TIME",
    "PDF_DRAWINGS",
    "QMDICT_DOCUMENTS",
    "QM_CITY_DOCUMENTS",
    "SPACE_PDF_AI_DOCUMENTS",
    "SPACE_W_SPEAK_SKIP",
    "USER_AUTH_DOCS",
    "USER_PREFERENCES",
    "VAULT_METADATA",
    "VIEWER_TOOL_DOCUMENTS",
    "VOCABULARY",
    "VOCAB_IMAGE_CACHE",
)


def configure_postgres_only() -> None:
    os.environ.setdefault("FUTURE_POSTGRES_ONLY", "1")
    os.environ.pop("FUTURE_DB_BACKEND", None)
    os.environ.pop("FUTURE_POSTGRES_BACKEND", None)
    os.environ.pop("FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK", None)
    os.environ.pop("FUTURE_TEST_PASSWORD", None)
    os.environ.setdefault("FUTURE_PG_DSN", "postgresql://future_server2_app@127.0.0.1:5432/future_server2")
    for domain in POSTGRES_ONLY_DOMAINS:
        os.environ.setdefault(f"FUTURE_DB_{domain}_BACKEND", "postgres")


def main() -> int:
    configure_postgres_only()
    sys.argv = [
        sys.argv[0],
        "--host",
        "127.0.0.1",
        "--port",
        "18877",
        "--no-browser",
        "--no-tunnel",
        "--no-preload",
    ]
    from FUTURE.server2.run_server_2 import main_server_2

    return int(main_server_2() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
