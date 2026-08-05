"""Fresh-snapshot isolated gate for Space_V image-gallery persistence."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE.tools import test_lesson_complete_isolated_harness as h


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    stamp = str(int(time.time()))
    h.RUN_ROOT = h.ROOT / "programe_cache" / f"space_v_image_gallery_isolated_{stamp}_18877"
    h.PG_ROOT = h.RUN_ROOT / "postgres"
    h.SERVER_DATA_ROOT = h.RUN_ROOT / "server-data"
    h.RUNTIME_ROOT = h.RUN_ROOT / "runtime"
    h.QMLEARN_ROOT = h.RUN_ROOT / "qml"
    h.SERVER_LOG = h.RUN_ROOT / "server.log"
    h.PG_LOG = h.RUN_ROOT / "postgres.log"
    output_path = Path(r"C:\Users\Admin\.codex\plans\space_v_image_gallery_isolated_20260804.json")
    pg_process = None
    server = None
    try:
        h.RUN_ROOT.mkdir(parents=True, exist_ok=True)
        h.copy_lesson()
        picture_root = h.RUN_ROOT / "pictures"
        picture_root.mkdir(parents=True, exist_ok=True)
        for name in ("codexgallery.jpg", "codexgallery1.png", "codexgallery2.webp"):
            (picture_root / name).write_bytes(("fixture-" + name).encode("ascii"))

        pg_process = h.start_postgres()
        dump_path = h.sync_production_database_snapshot()
        h.initialize_schema()
        h.provision_postgres()
        server = h.start_server(no_preload=True)
        health = h.wait_health(server)

        setting_response = requests.post(
            f"{h.BASE}/dashboard/space-v-picture-settings",
            json={"folder": str(picture_root)},
            timeout=30,
        )
        setting_response.raise_for_status()
        token = h.login()
        headers = auth_headers(token)

        initial_response = requests.get(f"{h.BASE}/vocab/image", headers=headers, params={"word": "codexgallery"}, timeout=30)
        initial_response.raise_for_status()
        initial = initial_response.json()
        images = initial.get("images") or []
        assert [row.get("id") for row in images] == ["codexgallery.jpg", "codexgallery1.png", "codexgallery2.webp"]

        selected_epoch = time.time()
        save_response = requests.post(
            f"{h.BASE}/vocab/image-primary",
            headers=headers,
            json={
                "word": "codexgallery",
                "image_id": "codexgallery2.webp",
                "operation_id": "isolated-gallery-newer",
                "selected_epoch": selected_epoch,
            },
            timeout=30,
        )
        save_response.raise_for_status()
        saved = save_response.json()

        stale_response = requests.post(
            f"{h.BASE}/vocab/image-primary",
            headers=headers,
            json={
                "word": "codexgallery",
                "image_id": "codexgallery.jpg",
                "operation_id": "isolated-gallery-older",
                "selected_epoch": selected_epoch - 1,
            },
            timeout=30,
        )
        stale_response.raise_for_status()
        stale = stale_response.json()
        after_stale = requests.get(f"{h.BASE}/vocab/image", headers=headers, params={"word": "codexgallery"}, timeout=30).json()

        invalid_asset = requests.get(
            f"{h.BASE}/vocab/image-file",
            headers=headers,
            params={"word": "codexgallery", "image_id": "missing.png"},
            timeout=30,
        )

        h.stop_server(server)
        server = h.start_server(no_preload=True)
        restart_health = h.wait_health(server)
        restart_token = h.login()
        after_restart = requests.get(
            f"{h.BASE}/vocab/image",
            headers=auth_headers(restart_token),
            params={"word": "codexgallery"},
            timeout=30,
        ).json()

        output = {
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump_path.stat().st_size},
            "resources": {"run_root": str(h.RUN_ROOT), "http": h.HTTP_PORT, "postgres": h.PG_PORT},
            "health": {"initial": health, "restart": restart_health},
            "gallery": {
                "ids": [row.get("id") for row in images],
                "initial_index": initial.get("selected_index"),
                "saved": saved,
                "stale": stale,
                "after_stale_index": after_stale.get("selected_index"),
                "after_restart_index": after_restart.get("selected_index"),
                "after_restart_id": after_restart.get("selected_image_id"),
                "invalid_asset_status": invalid_asset.status_code,
            },
        }
        output["gates"] = {
            "warm_ready_initial": bool(health.get("warm_ready")),
            "warm_ready_restart": bool(restart_health.get("warm_ready")),
            "three_variants": output["gallery"]["ids"] == ["codexgallery.jpg", "codexgallery1.png", "codexgallery2.webp"],
            "selection_saved": saved.get("image_id") == "codexgallery2.webp" and bool(saved.get("changed")),
            "stale_rejected": stale.get("image_id") == "codexgallery2.webp" and bool(stale.get("stale")),
            "restart_persisted": after_restart.get("selected_image_id") == "codexgallery2.webp" and after_restart.get("selected_index") == 2,
            "invalid_id_rejected": invalid_asset.status_code == 404,
        }
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if not all(output["gates"].values()):
            raise RuntimeError(f"Space_V image gallery isolated gates failed: {output['gates']}")
        return 0
    except Exception:
        failure = {
            "postgres_log": h.PG_LOG.read_text(encoding="utf-8", errors="replace")[-12000:] if h.PG_LOG.is_file() else "",
            "server_log": h.SERVER_LOG.read_text(encoding="utf-8", errors="replace")[-12000:] if h.SERVER_LOG.is_file() else "",
        }
        Path(r"C:\Users\Admin\.codex\plans\space_v_image_gallery_isolated_failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise
    finally:
        h.stop_server(server)
        h.stop_postgres()
        shutil.rmtree(h.RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
