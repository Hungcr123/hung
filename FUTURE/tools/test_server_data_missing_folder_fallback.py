"""Regression for stale Lesson Vault folder restoration."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


# Added 2026-07-21: deleted remembered folders fall back without exposing another user's root.
def main() -> int:
    missing_private = "hung/codex-missing-parent/codex-missing-child"
    private_payload = app.list_server_data(
        missing_private,
        username="hung",
        fresh=True,
        lightweight=True,
        include_task_board=False,
        include_space_task=False,
    )
    assert private_payload["path"].lower() == "hung"
    assert private_payload["fallback_from"].lower() == missing_private.lower()
    assert private_payload.get("entries")

    missing_common = "common/codex-missing-parent/codex-missing-child"
    common_payload = app.list_server_data(
        missing_common,
        username="hung",
        fresh=True,
        lightweight=True,
        include_task_board=False,
        include_space_task=False,
    )
    assert common_payload["path"].lower() == "common"
    assert common_payload["fallback_from"].lower() == missing_common.lower()
    assert common_payload.get("entries")

    print("server_data_missing_folder_fallback=ok private=hung shared=common no_500=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
