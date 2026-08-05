"""Focused contract for the durable shared audio epoch/revision protocol."""

from __future__ import annotations

import atexit
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    epoch_path = app.SERVER_DATA_ROOT / "_future_audio_cache_epoch.json"
    assert app.server_database_document_postgres_authoritative(epoch_path)
    entry = app.server_database_document_entry(epoch_path)
    assert entry and isinstance(entry.get("content"), bytes)
    payload = json.loads(entry["content"].decode(entry.get("encoding") or "utf-8"))
    epoch = int(payload.get("global_audio_cache_epoch", 0) or 0)
    assert epoch > 0 and app.global_audio_cache_epoch() == epoch

    descriptor = app.qm_sound_protocol_descriptor(word="Book", voice="sot:en-GB")
    query = parse_qs(urlparse(descriptor["url"]).query)
    assert int(query["audio_epoch"][0]) == epoch
    assert query["file_rev"][0] == descriptor["file_revision"]
    assert "v" not in query and "revision" not in query

    delivery = (ROOT / "FUTURE/server_parts/process_frontend_runtime/06_frontend_delivery.py").read_text(encoding="utf-8")
    frontend = (ROOT / "FUTURE/web/js_parts/01_bootstrap_guard_ai_agent.js").read_text(encoding="utf-8")
    assert "bump_global_audio_cache_epoch(reason)" in delivery
    assert 'normalized_command == "clear-audio-cache"' in delivery
    assert 'LAST_SEEN_AUDIO_CACHE_EPOCH_KEY = "last_seen_audio_cache_epoch"' in frontend
    assert "resolveQmSoundProtocolUrl" in frontend and "syncEpoch" in frontend

    try:
        atexit.unregister(app.flush_auth_sessions_to_disk)
    except Exception:
        pass
    print(f"audio_epoch_protocol=ok epoch={epoch} postgres=true exact_url=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
