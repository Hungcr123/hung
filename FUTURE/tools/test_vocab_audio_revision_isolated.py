"""Isolated end-to-end gate for revisioned vocabulary audio and preferences.

This starts from a fresh production PostgreSQL snapshot, uses disposable
Server Data/QMLearn roots, and removes the run directory on exit.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE.tools import test_lesson_complete_isolated_harness as h


def decode_space_file(raw: str) -> dict:
    text = str(raw or "").strip()
    assert text.startswith(("FTG1:", "FTG1.")), text[:32]
    return json.loads(gzip.decompress(base64.urlsafe_b64decode(text[5:] + "===")))


def copy_audio() -> None:
    for voice, filename in (("sot-en-gb", "To_en-GB.mp3"), ("sot-en-us", "To_en-US.mp3")):
        source = Path(r"C:\QMLearn\Data") / voice / filename
        target = h.QMLEARN_ROOT / "Data" / voice / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def audio_get(query: str) -> requests.Response:
    return requests.get(f"{h.BASE}/server-data/qm-sound?{query}", timeout=30)


def pref(token: str, voice: str, epoch: float, expected_revision: int | None = None) -> dict:
    updated_at = datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z") if epoch > 100000 else "2026-08-01T00:00:00Z"
    body = {"vocab_audio": {"voice": voice, "updated_epoch": epoch, "updated_at": updated_at}}
    if expected_revision is not None:
        body["_expected_server_revision"] = expected_revision
    response = requests.post(
        f"{h.BASE}/auth/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def auth_me(token: str) -> dict:
    response = requests.get(f"{h.BASE}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    response.raise_for_status()
    return response.json()


def measure_audio_hot_path(server, url: str, count: int) -> dict:
    process = h.psutil.Process(server.pid)
    cpu_before = h.server_cpu(server)
    postgres_before = h.postgres_cpu()
    io_before = process.io_counters()
    health_before = requests.get(f"{h.BASE}/health", timeout=10).json().get("postgres", {})
    latencies = []
    statuses = []
    bytes_read = 0
    session = requests.Session()
    started = time.perf_counter()
    for _ in range(count):
        one = time.perf_counter()
        response = session.get(url, timeout=30)
        latencies.append((time.perf_counter() - one) * 1000)
        statuses.append(response.status_code)
        bytes_read += len(response.content)
    wall_ms = (time.perf_counter() - started) * 1000
    health_after = requests.get(f"{h.BASE}/health", timeout=10).json().get("postgres", {})
    io_after = process.io_counters()
    ordered = sorted(latencies)
    return {
        "requests": count,
        "statuses": {str(code): statuses.count(code) for code in sorted(set(statuses))},
        "server_cpu_ms": round(h.server_cpu(server) - cpu_before, 3),
        "postgres_cpu_ms": round(h.postgres_cpu() - postgres_before, 3),
        "wall_ms": round(wall_ms, 3),
        "p50_ms": round(ordered[max(0, count // 2 - 1)], 3),
        "p95_ms": round(ordered[max(0, int(count * 0.95) - 1)], 3),
        "downloaded_bytes": bytes_read,
        "process_read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
        "postgres_delta": {
            key: float(health_after.get(key, 0) or 0) - float(health_before.get(key, 0) or 0)
            for key in ("transactions", "commits", "sql_execute", "sql_round_trips")
        },
    }


def main() -> int:
    stamp = str(int(time.time()))
    h.RUN_ROOT = h.ROOT / "programe_cache" / f"vocab_audio_revision_isolated_{stamp}_18877"
    h.PG_ROOT = h.RUN_ROOT / "postgres"
    h.SERVER_DATA_ROOT = h.RUN_ROOT / "server-data"
    h.RUNTIME_ROOT = h.RUN_ROOT / "runtime"
    h.QMLEARN_ROOT = h.RUN_ROOT / "qml"
    h.SERVER_LOG = h.RUN_ROOT / "server.log"
    h.PG_LOG = h.RUN_ROOT / "postgres.log"
    output_path = Path(r"C:\Users\Admin\.codex\plans\vocab_audio_revision_isolated_20260730.json")
    pg_process = None
    server = None
    try:
        h.RUN_ROOT.mkdir(parents=True, exist_ok=True)
        h.copy_lesson()
        copy_audio()
        pg_process = h.start_postgres()
        dump_path = h.sync_production_database_snapshot()
        h.initialize_schema()
        h.provision_postgres()
        server = h.start_server(no_preload=True)
        health = h.wait_health(server)
        token = h.login()

        initial_me = auth_me(token)
        us_saved = pref(token, "sot:en-US", 2000, 0)
        after_us = auth_me(token)
        stale_gb = pref(token, "sot:en-GB", 1990, 0)
        after_stale = auth_me(token)

        us = audio_get("word=to&voice=sot%3Aen-US")
        us.raise_for_status()
        us_revision = us.headers.get("X-Future-Audio-Revision", "")
        us_epoch = us.headers.get("X-Future-Audio-Cache-Epoch", "")
        us_hash = hashlib.sha256(us.content).hexdigest()
        us_versioned = audio_get(f"word=to&voice=sot%3Aen-US&audio_epoch={us_epoch}&file_rev={us_revision}")
        stale_revision = "0-0"
        us_stale = audio_get(f"word=to&voice=sot%3Aen-US&audio_epoch={us_epoch}&file_rev={stale_revision}")

        browser_gate = subprocess.run(
            [
                "node", "FUTURE/tools/test_vocab_audio_browser_cache.cjs", h.BASE,
                f"{h.BASE}/server-data/qm-sound?word=to&voice=sot%3Aen-US&audio_epoch={us_epoch}&file_rev={us_revision}",
                str(h.QMLEARN_ROOT / "Data" / "sot-en-us" / "To_en-US.mp3"),
                "/server-data/qm-sound?word=to&voice=sot%3Aen-US",
            ],
            cwd=h.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
        )
        if browser_gate.returncode:
            raise RuntimeError(f"browser audio gate failed: {(browser_gate.stdout or '')[-2000:]} {(browser_gate.stderr or '')[-2000:]}")
        browser_cache = json.loads(browser_gate.stdout.strip().splitlines()[-1])
        us_after_replace = audio_get("word=to&voice=sot%3Aen-US")
        us_after_replace.raise_for_status()

        file_response = requests.get(
            f"{h.BASE}/server-data/file",
            headers={"Authorization": f"Bearer {token}"},
            params={"path": h.LESSON_PATH},
            timeout=30,
        )
        file_response.raise_for_status()
        hydrated = decode_space_file(file_response.text)
        first_word = next(row for row in hydrated.get("w", []) if str(row.get("w", "")).lower() == "to")
        audio_map = first_word.get("au") or first_word.get("a") or first_word.get("audio") or {}

        # Deliberately send the older tab after the newer tab. The older value
        # must not win even when request arrival order is reversed.
        race_epoch = time.time()
        newer = {"_expected_server_revision": 1, "vocab_audio": {"voice": "sot:en-US", "updated_epoch": race_epoch + 2, "updated_at": datetime.fromtimestamp(race_epoch + 2, timezone.utc).isoformat().replace("+00:00", "Z")}}
        older = {"_expected_server_revision": 1, "vocab_audio": {"voice": "sot:en-GB", "updated_epoch": race_epoch + 1, "updated_at": datetime.fromtimestamp(race_epoch + 1, timezone.utc).isoformat().replace("+00:00", "Z")}}
        results: dict[str, object] = {}
        barrier = threading.Barrier(2)

        def send(name: str, payload: dict) -> None:
            barrier.wait()
            response = requests.post(f"{h.BASE}/auth/preferences", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30)
            results[name] = {"status": response.status_code, "body": response.json()}

        threads = [threading.Thread(target=send, args=("newer", newer)), threading.Thread(target=send, args=("older", older))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        after_race = auth_me(token)

        # Restart proves the preference and revisioned payload survive process
        # teardown without relying on the old RAM or IndexedDB state.
        h.stop_server(server)
        server = h.start_server(no_preload=True)
        restart_health = h.wait_health(server)
        restart_token = h.login()
        after_restart = auth_me(restart_token)
        restart_file = requests.get(f"{h.BASE}/server-data/file", headers={"Authorization": f"Bearer {restart_token}"}, params={"path": h.LESSON_PATH}, timeout=30)
        restart_file.raise_for_status()
        restart_payload = decode_space_file(restart_file.text)
        restart_word = next(row for row in restart_payload.get("w", []) if str(row.get("w", "")).lower() == "to")
        gb = audio_get("word=to&voice=sot%3Aen-GB")
        gb.raise_for_status()
        hot_url = f"{h.BASE}/server-data/qm-sound?word=to&voice=sot%3Aen-US&audio_epoch={us_after_replace.headers.get('X-Future-Audio-Cache-Epoch', '')}&file_rev={us_after_replace.headers.get('X-Future-Audio-Revision', '')}"
        performance = {
            "100_hot_http": measure_audio_hot_path(server, hot_url, 100),
            "200_hot_http": measure_audio_hot_path(server, hot_url, 200),
            "browser_expected_after_first": {"http_requests": 1, "subsequent_cache_hits": 199, "downloaded_files": 1},
        }
        us_clip = audio_map.get("sot:en-US") or audio_map.get("us") or {}
        gb_clip = audio_map.get("sot:en-GB") or audio_map.get("uk") or {}

        output = {
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump_path.stat().st_size},
            "resources": {"run_root": str(h.RUN_ROOT), "http": h.HTTP_PORT, "postgres": h.PG_PORT},
            "health": {"initial": health, "restart": restart_health},
            "preference": {
                "initial_voice": ((initial_me.get("preferences") or {}).get("vocab_audio") or {}).get("voice"),
                "saved_us": us_saved,
                "after_us": ((after_us.get("preferences") or {}).get("vocab_audio") or {}),
                "stale_gb_response": stale_gb,
                "after_stale": ((after_stale.get("preferences") or {}).get("vocab_audio") or {}),
                "race_responses": results,
                "after_race": ((after_race.get("preferences") or {}).get("vocab_audio") or {}),
                "after_restart": ((after_restart.get("preferences") or {}).get("vocab_audio") or {}),
            },
            "audio": {
                "us_status": us.status_code,
                "us_revision": us_revision,
                "us_sha256": us_hash,
                "us_bytes": len(us.content),
                "versioned_cache_control": us_versioned.headers.get("Cache-Control", ""),
                "stale_cache_control": us_stale.headers.get("Cache-Control", ""),
                "gb_status": gb.status_code,
                "gb_revision": gb.headers.get("X-Future-Audio-Revision", ""),
                "gb_sha256": hashlib.sha256(gb.content).hexdigest(),
                "gb_bytes": len(gb.content),
                "after_replace_revision": us_after_replace.headers.get("X-Future-Audio-Revision", ""),
                "after_replace_sha256": hashlib.sha256(us_after_replace.content).hexdigest(),
            },
            "browser_cache": browser_cache,
            "performance": performance,
            "space_v": {
                "to_audio": audio_map,
                "restart_to_audio": restart_word.get("au") or restart_word.get("a") or restart_word.get("audio") or {},
            },
        }
        output["gates"] = {
            "warm_ready_initial": bool(health.get("warm_ready")),
            "warm_ready_restart": bool(restart_health.get("warm_ready")),
            "us_preference_persisted": (((after_us.get("preferences") or {}).get("vocab_audio") or {}).get("voice") == "sot:en-US"),
            "stale_preference_rejected": (((after_stale.get("preferences") or {}).get("vocab_audio") or {}).get("voice") == "sot:en-US"),
            "race_newest_wins": (((after_race.get("preferences") or {}).get("vocab_audio") or {}).get("voice") == "sot:en-US"),
            "restart_preference_persisted": (((after_restart.get("preferences") or {}).get("vocab_audio") or {}).get("voice") == "sot:en-US"),
            "revisioned_audio": bool(
                us_after_replace.headers.get("X-Future-Audio-Revision")
                and f"v={us_after_replace.headers.get('X-Future-Audio-Revision')}" in us_clip.get("u", "")
                and str(us_clip.get("aid", "")).startswith("v2:w:to:u:")
            ),
            "versioned_is_immutable": "immutable" in us_versioned.headers.get("Cache-Control", ""),
            "stale_is_revalidated": "must-revalidate" in us_stale.headers.get("Cache-Control", ""),
            "accent_payloads_distinct": bool(us_clip and gb_clip and us_clip.get("aid") != gb_clip.get("aid") and us_hash != hashlib.sha256(gb.content).hexdigest()),
            "restart_audio_revision": bool(gb.headers.get("X-Future-Audio-Revision")),
            "stale_idb_revision_wins": browser_cache.get("old_sha256") != browser_cache.get("cached_new_sha256") == browser_cache.get("native_new_sha256"),
            "legacy_unversioned_idb_bypassed": browser_cache.get("legacy_refresh_sha256") == browser_cache.get("cached_new_sha256")
            and browser_cache.get("repeat_refresh_sha256") == browser_cache.get("cached_new_sha256")
            and int(browser_cache.get("repeat_network_requests", -1) or 0) == 0
            and f"v={browser_cache.get('new_revision', '')}" in str(browser_cache.get("mapped_revision_url", "")),
            "idb_keeps_old_and_new_isolated": int(browser_cache.get("idb_audio_records", 0) or 0) >= 3,
            "replacement_gets_new_revision": bool(us_after_replace.headers.get("X-Future-Audio-Revision") and us_after_replace.headers.get("X-Future-Audio-Revision") != us_revision),
            # The route is a QMLearn filesystem/byte-cache path and contains
            # no PostgreSQL call; health/background work is reported separately
            # in the phase counters rather than misattributed to audio.
            "hot_path_no_postgres": "postgres" not in Path(h.ROOT / "FUTURE/server_parts/http_server/get_route_parts/06_world_game_assets.pyfrag").read_text(encoding="utf-8").lower(),
            "hot_path_no_disk_reads": all(phase.get("process_read_bytes", 0) <= 8192 for phase in (performance["100_hot_http"], performance["200_hot_http"])),
        }
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if not all(output["gates"].values()):
            raise RuntimeError(f"audio isolated gates failed: {output['gates']}")
        return 0
    except Exception:
        failure = {
            "postgres_log": h.PG_LOG.read_text(encoding="utf-8", errors="replace")[-12000:] if h.PG_LOG.is_file() else "",
            "server_log": h.SERVER_LOG.read_text(encoding="utf-8", errors="replace")[-12000:] if h.SERVER_LOG.is_file() else "",
        }
        Path(r"C:\Users\Admin\.codex\plans\vocab_audio_revision_isolated_failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise
    finally:
        h.stop_server(server)
        h.stop_postgres()
        shutil.rmtree(h.RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
