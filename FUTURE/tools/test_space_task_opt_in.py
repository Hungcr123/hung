"""Regression checks for explicit-folder-only Space Task behavior."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    empty_settings = {"preferred_folders": [], "updated_at": "", "updated_by": "", "updated_rev": ""}
    assert app._space_task_candidate_folder_rows("codexoptin", empty_settings) == []
    empty_payload = app._space_task_empty_opt_in_payload(empty_settings)
    assert empty_payload["opt_in_required"] is True
    assert empty_payload["tasks"] == []
    assert empty_payload["folders"] == []

    selected = {**empty_settings, "preferred_folders": ["common/Study/Empower A1"]}
    rows = app._space_task_candidate_folder_rows("codexoptin", selected)
    assert rows == [{"path": "common/Study/Empower A1", "source": "preferred", "direct_only": False}]
    print("space_task_opt_in=ok empty=no_scan selected=preferred_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
