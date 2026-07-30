"""Regression for one-scan chat poll snapshots and no-op read-marker persistence."""

from __future__ import annotations

import ast
import threading
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "chat_paint_runtime" / "03_chat_messages_admin.py"


def main() -> int:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {"chat_message_read_state", "chat_messages_with_read_state", "chat_poll_snapshot"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    state = {
        "messages": [
            {"id": 1, "username": "codex_chat", "sender": "user", "text": "one"},
            {"id": 2, "username": "codex_chat", "sender": "admin", "text": "two"},
            {"id": 3, "username": "codex_chat", "sender": "admin", "text": "three"},
            {"id": 4, "username": "other", "sender": "admin", "text": "other"},
        ],
        "admin_read": {"codex_chat": 1},
        "user_read": {},
    }
    saves = []
    updates = []
    namespace = {
        "CHAT_LOCK": threading.RLock(),
        "normalize_username": lambda value: str(value or "").strip().lower(),
        "clean": lambda value: str(value or "").strip(),
        "load_chat_state_locked": lambda: state,
        "save_chat_state_locked": lambda value: saves.append(value),
        "server_database_update_chat_read": lambda username, field, value: updates.append((username, field, value)) or True,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
    poll = namespace["chat_poll_snapshot"]

    closed = poll("codex_chat", 1, False)
    assert [row["id"] for row in closed["messages"]] == [2, 3]
    assert closed["unread"] == 2 and closed["read"] == {"admin_read": 1, "user_read": 0}
    assert not saves and not updates

    opened = poll("codex_chat", 1, True)
    assert opened["unread"] == 0 and opened["read"]["user_read"] == 3
    assert len(updates) == 1 and not saves
    repeated = poll("codex_chat", 3, True)
    assert repeated["messages"] == [] and repeated["unread"] == 0
    assert len(updates) == 1 and not saves

    threads = [threading.Thread(target=lambda: poll("codex_chat", 3, True)) for _ in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(updates) == 1 and not saves
    print("chat_poll_snapshot=ok state_loads=one logical_save=one repeat_and_concurrency=noop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
