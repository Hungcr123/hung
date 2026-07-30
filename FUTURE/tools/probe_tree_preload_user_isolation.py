"""Probe tree-preload user isolation and cache behavior.

Added 2026-07-26 for the PostgreSQL cache-delta checkpoint. It compares two
users against the same runtime and records whether common rows stay aligned
while private overlay rows differ.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import requests

BASE = "http://127.0.0.1:8877"
OUTPUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def server_process(port: int = 8877) -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError(f"Server 2 listener not found on port {port}")


def login(base: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError(f"Login returned no token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def get_tree(session: requests.Session, base: str, username: str, etag: str = "") -> dict[str, Any]:
    headers = {"Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    response = session.get(base + f"/server-data/tree-preload?username={username}", headers=headers, timeout=45)
    payload = response.json() if response.status_code != 304 else {}
    rows = payload.get("rows") or []
    common_rows = [row for row in rows if isinstance(row, dict) and str(row.get("path") or "").startswith("common/")]
    private_roots = sorted({str(row.get("path") or "").split("/", 1)[0] for row in rows if isinstance(row, dict) and str(row.get("path") or "").startswith(f"{username.lower()}/")})
    return {
        "status": response.status_code,
        "etag": str(response.headers.get("ETag") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "wire_bytes": int(response.headers.get("Content-Length") or 0),
        "decoded_bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest() if response.content else "",
        "common_manifest_signature": payload.get("common_manifest_signature", ""),
        "overlay_manifest_signature": payload.get("overlay_manifest_signature", ""),
        "manifest_signature": payload.get("manifest_signature", ""),
        "manifest_integrity_signature": payload.get("manifest_integrity_signature", ""),
        "manifest_updated_at": payload.get("manifest_updated_at", ""),
        "row_count": int(payload.get("row_count", 0) or 0),
        "common_row_count": len(common_rows),
        "private_roots": private_roots,
    }

def get_payload(session: requests.Session, base: str, route: str, username: str = "", etag: str = "") -> dict[str, Any]:
    headers = {"Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    response = session.get(base + route, headers=headers, timeout=45)
    payload = response.json() if response.status_code != 304 else {}
    rows = payload.get("rows") or []
    return {
        "route": route,
        "status": response.status_code,
        "etag": str(response.headers.get("ETag") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "wire_bytes": int(response.headers.get("Content-Length") or 0),
        "decoded_bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest() if response.content else "",
        "common_revision": payload.get("common_revision", ""),
        "common_manifest_signature": payload.get("common_manifest_signature", ""),
        "overlay_revision": payload.get("overlay_revision", ""),
        "overlay_manifest_signature": payload.get("overlay_manifest_signature", ""),
        "manifest_integrity_signature": payload.get("manifest_integrity_signature", ""),
        "row_count": int(payload.get("row_count", 0) or 0),
        "rows_with_common_root": sum(1 for row in rows if isinstance(row, dict) and str(row.get("path") or "").startswith("common/")),
        "rows_with_private_root": sum(1 for row in rows if username and isinstance(row, dict) and str(row.get("path") or "").startswith(f"{username.lower()}/")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--hung-password-env", default="FUTURE_HUNG_PASSWORD")
    parser.add_argument("--quynh-password-env", default="FUTURE_QUYNH_PASSWORD")
    args = parser.parse_args()

    hung_password = os.environ.get(args.hung_password_env, "")
    quynh_password = os.environ.get(args.quynh_password_env, "")
    if not hung_password or not quynh_password:
        raise RuntimeError("Set FUTURE_HUNG_PASSWORD and FUTURE_QUYNH_PASSWORD for this probe")

    process = server_process(8877)
    started_cpu = process.cpu_times().user + process.cpu_times().system
    hung_session = login(args.base, "hung", hung_password)
    quynh_session = login(args.base, "quynh", quynh_password)
    hung_common = get_payload(hung_session, args.base, "/server-data/common-tree", "hung")
    quynh_common = get_payload(quynh_session, args.base, "/server-data/common-tree", "quynh")
    hung_common_revalidate = get_payload(hung_session, args.base, "/server-data/common-tree", "hung", hung_common["etag"])
    quynh_common_revalidate = get_payload(quynh_session, args.base, "/server-data/common-tree", "quynh", quynh_common["etag"])
    hung_overlay = get_payload(hung_session, args.base, "/server-data/user-overlay", "hung")
    quynh_overlay = get_payload(quynh_session, args.base, "/server-data/user-overlay", "quynh")
    hung_overlay_revalidate = get_payload(hung_session, args.base, "/server-data/user-overlay", "hung", hung_overlay["etag"])
    quynh_overlay_revalidate = get_payload(quynh_session, args.base, "/server-data/user-overlay", "quynh", quynh_overlay["etag"])
    hung_tree = get_tree(hung_session, args.base, "hung")
    quynh_tree = get_tree(quynh_session, args.base, "quynh")
    hung_revalidate = get_tree(hung_session, args.base, "hung", hung_tree["etag"])
    quynh_revalidate = get_tree(quynh_session, args.base, "quynh", quynh_tree["etag"])
    cpu_ms = round(((process.cpu_times().user + process.cpu_times().system) - started_cpu) * 1000, 3)

    raw = {
        "timestamp_utc": utc_now(),
        "server_pid": process.pid,
        "cpu_ms": cpu_ms,
        "split_endpoints": {
            "hung_common": hung_common,
            "quynh_common": quynh_common,
            "hung_common_revalidate": hung_common_revalidate,
            "quynh_common_revalidate": quynh_common_revalidate,
            "hung_overlay": hung_overlay,
            "quynh_overlay": quynh_overlay,
            "hung_overlay_revalidate": hung_overlay_revalidate,
            "quynh_overlay_revalidate": quynh_overlay_revalidate,
        },
        "hung": {"cold": hung_tree, "revalidate": hung_revalidate},
        "quynh": {"cold": quynh_tree, "revalidate": quynh_revalidate},
        "same_common_etag": hung_common.get("etag") == quynh_common.get("etag"),
        "same_common_sha256": hung_common.get("sha256") == quynh_common.get("sha256"),
        "common_304_after_hung": hung_common_revalidate.get("status") == 304,
        "common_304_after_quynh": quynh_common_revalidate.get("status") == 304,
        "different_overlay_etag": hung_overlay.get("etag") != quynh_overlay.get("etag"),
        "overlay_304_after_hung": hung_overlay_revalidate.get("status") == 304,
        "overlay_304_after_quynh": quynh_overlay_revalidate.get("status") == 304,
        "common_has_no_private_rows": hung_common.get("rows_with_private_root") == 0 and quynh_common.get("rows_with_private_root") == 0,
        "overlay_has_no_common_rows": hung_overlay.get("rows_with_common_root") == 0 and quynh_overlay.get("rows_with_common_root") == 0,
        "same_common_signature": hung_tree.get("common_manifest_signature") == quynh_tree.get("common_manifest_signature"),
        "different_overlay_signature": hung_tree.get("overlay_manifest_signature") != quynh_tree.get("overlay_manifest_signature"),
        "same_integrity_signature": hung_tree.get("manifest_integrity_signature") == quynh_tree.get("manifest_integrity_signature"),
        "same_common_rows": hung_tree.get("common_row_count") == quynh_tree.get("common_row_count"),
        "different_private_roots": hung_tree.get("private_roots") != quynh_tree.get("private_roots"),
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "checkpoint_003_tree_preload_user_isolation_raw.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(path),
        "hung_304": int(hung_revalidate["status"] == 304),
        "quynh_304": int(quynh_revalidate["status"] == 304),
        "common_same_etag": raw["same_common_etag"],
        "common_same_sha256": raw["same_common_sha256"],
        "common_304": int(raw["common_304_after_hung"] and raw["common_304_after_quynh"]),
        "overlay_different_etag": raw["different_overlay_etag"],
        "overlay_304": int(raw["overlay_304_after_hung"] and raw["overlay_304_after_quynh"]),
        "common_has_no_private_rows": raw["common_has_no_private_rows"],
        "overlay_has_no_common_rows": raw["overlay_has_no_common_rows"],
        "same_common_signature": raw["same_common_signature"],
        "different_overlay_signature": raw["different_overlay_signature"],
        "same_common_rows": raw["same_common_rows"],
        "different_private_roots": raw["different_private_roots"],
        "cpu_ms": cpu_ms,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
