"""Regression gate: builder staging must not touch active PostgreSQL identity rows."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import future_lesson_identity as identity


def main() -> int:
    original = identity.reserve_lesson_id_in_database

    def forbidden(*_args, **_kwargs):
        raise AssertionError("staged builder attempted an active PostgreSQL identity write")

    identity.reserve_lesson_id_in_database = forbidden
    os.environ["FUTURE_LESSON_IDENTITY_STAGING"] = "1"
    try:
        payload = {"title": "staged"}
        lesson_id = identity.ensure_future_lesson_id(payload, ROOT / "staged.Space_W", "Space_W")
        if not lesson_id or payload.get("lesson_id") != lesson_id:
            raise AssertionError("staged lesson ID was not embedded")
    finally:
        identity.reserve_lesson_id_in_database = original
        os.environ.pop("FUTURE_LESSON_IDENTITY_STAGING", None)
    print("builder_identity_staging=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
