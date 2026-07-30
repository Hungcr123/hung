from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROOT_BUILDER = ROOT / "build_future_worker_auto.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the full standalone FutureWorkerAuto.exe")
    parser.add_argument("--server", default="", help="Optional default Server 2 API URL")
    parser.add_argument("--name", default="FutureWorkerAuto", help="EXE base name")
    args = parser.parse_args()
    if args.name != "FutureWorkerAuto":
        raise RuntimeError("Only the canonical FutureWorkerAuto build is supported.")
    env = os.environ.copy()
    if str(args.server or "").strip():
        env["FUTURE_SERVER_URL"] = str(args.server).strip().rstrip("/")
    return subprocess.run([sys.executable, str(ROOT_BUILDER)], cwd=str(ROOT), env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
