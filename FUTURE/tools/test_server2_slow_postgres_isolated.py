#!/usr/bin/env python3
"""Measure learner routes while an isolated PostgreSQL TCP proxy delays replies."""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import psutil

import test_lesson_complete_isolated_harness as isolated
import test_server2_expert_user_load_isolated as expert


ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = ROOT / "programe_cache" / "server2_slow_postgres_18878"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\server2_slow_postgres_20260802.json")
HTTP_PORT = 18878
POSTGRES_PORT = 55433
PROXY_PORT = 55434
VOICE_WORKER_PORT = 18779


def stop_voice_worker() -> None:
    for connection in psutil.net_connections(kind="tcp"):
        if not connection.laddr or connection.laddr.port != VOICE_WORKER_PORT or connection.status != psutil.CONN_LISTEN or not connection.pid:
            continue
        try:
            process = psutil.Process(connection.pid)
            if "future_voice_worker_2.py" in " ".join(process.cmdline()).lower():
                process.kill()
                process.wait(timeout=10)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass


class DelayedPostgresProxy:
    def __init__(self, delay_seconds: float = 0.025) -> None:
        self.delay_seconds = delay_seconds
        self.delay_enabled = threading.Event()
        self.stop_event = threading.Event()
        self.listener: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.connections: list[socket.socket] = []
        self.connection_lock = threading.Lock()

    def start(self) -> None:
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 10
        while self.listener is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if self.listener is None:
            raise RuntimeError("PostgreSQL delay proxy did not start")

    def stop(self) -> None:
        self.stop_event.set()
        if self.listener is not None:
            try:
                self.listener.close()
            except OSError:
                pass
        with self.connection_lock:
            for connection in self.connections:
                try:
                    connection.close()
                except OSError:
                    pass
        if self.thread is not None:
            self.thread.join(timeout=5)

    def _serve(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", PROXY_PORT))
        listener.listen(64)
        listener.settimeout(0.25)
        self.listener = listener
        while not self.stop_event.is_set():
            try:
                client, _address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            upstream = socket.create_connection(("127.0.0.1", POSTGRES_PORT), timeout=10)
            with self.connection_lock:
                self.connections.extend((client, upstream))
            threading.Thread(target=self._pump, args=(client, upstream, False), daemon=True).start()
            threading.Thread(target=self._pump, args=(upstream, client, True), daemon=True).start()

    def _pump(self, source: socket.socket, target: socket.socket, delayed: bool) -> None:
        try:
            while not self.stop_event.is_set():
                data = source.recv(65536)
                if not data:
                    break
                if delayed and self.delay_enabled.is_set():
                    time.sleep(self.delay_seconds)
                target.sendall(data)
        except OSError:
            pass
        finally:
            for connection in (source, target):
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    connection.close()
                except OSError:
                    pass


def configure() -> None:
    expert.RUN_ROOT = RUN_ROOT
    expert.configure()
    isolated.HTTP_PORT = HTTP_PORT
    isolated.BASE = f"http://127.0.0.1:{HTTP_PORT}"
    isolated.PG_PORT = POSTGRES_PORT
    isolated.PG_DSN = f"postgresql://future_server2_app@127.0.0.1:{POSTGRES_PORT}/{isolated.TEST_DATABASE}"


def main() -> int:
    configure()
    expert.remove_run_root()
    RUN_ROOT.mkdir(parents=True)
    server_process = None
    proxy = DelayedPostgresProxy()
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        fixtures = expert.prepare_server_data(expert.select_fixtures())
        usernames = expert.provision_users()
        proxy.start()
        proxy_dsn = f"postgresql://future_server2_app@127.0.0.1:{PROXY_PORT}/{isolated.TEST_DATABASE}"
        server_process = isolated.start_server(
            no_preload=True,
            extra_env={
                "FUTURE_PG_DSN": proxy_dsn,
                "FUTURE_DISTRIBUTED_WORKER_PORT": "18891",
                "FUTURE_VOICE_WORKER_PORT": str(VOICE_WORKER_PORT),
            },
        )
        health = isolated.wait_health(server_process)
        users = []
        for index, username in enumerate(usernames):
            token = isolated.login(username)
            session = expert.requests.Session()
            session.headers.update({"Authorization": f"Bearer {token}"})
            role = expert.ROLES[index % len(expert.ROLES)]
            users.append({"index": index, "username": username, "role": role, "fixture": fixtures[role], "session": session})
        server = psutil.Process(int(health["pid"]))
        baseline = expert.run_phase("postgres_baseline_10", users, 10, 8, server)
        proxy.delay_enabled.set()
        delayed = expert.run_phase("postgres_delayed_10", users, 10, 8, server)
        result = {
            "ok": baseline["errors"] == 0 and delayed["errors"] == 0,
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "resources": {"http": isolated.BASE, "postgres": POSTGRES_PORT, "proxy": PROXY_PORT, "production_mutated": False},
            "fault": {"server_reply_delay_ms_per_packet": proxy.delay_seconds * 1000},
            "baseline": baseline,
            "delayed": delayed,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    finally:
        proxy.stop()
        isolated.stop_server(server_process)
        stop_voice_worker()
        isolated.stop_postgres()
        expert.remove_run_root()


if __name__ == "__main__":
    raise SystemExit(main())
