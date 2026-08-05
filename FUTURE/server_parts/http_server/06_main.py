# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def future_browser_launch_config_path() -> Path:
    return ROOT / "programe_cache" / "future_browser_launch_config.json"


def read_future_browser_launch_config() -> dict:
    path = future_browser_launch_config_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        print(f"Could not read browser launch config {path}: {exc}", flush=True)
    return {}


def find_coccoc_browser_exe(config: dict | None = None) -> str:
    config = config or {}
    configured = clean(config.get("browser_path", ""))
    if configured and Path(configured).is_file():
        return configured
    candidates = []
    for env_name in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "CocCoc" / "Browser" / "Application" / "browser.exe")
    candidates.extend([
        Path.home() / "AppData" / "Local" / "CocCoc" / "Browser" / "Application" / "browser.exe",
        Path(r"C:\Program Files\CocCoc\Browser\Application\browser.exe"),
        Path(r"C:\Program Files (x86)\CocCoc\Browser\Application\browser.exe"),
    ])
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return ""


def open_future_start_page(url: str) -> None:
    config = read_future_browser_launch_config()
    browser_mode = clean(os.environ.get("FUTURE_BROWSER_MODE", "") or config.get("browser_mode", "")).lower()
    incognito_enabled = bool(config.get("coccoc_incognito_enabled", False)) and browser_mode != "coccoc"
    prefer_coccoc = browser_mode in ("coccoc", "coccoc-normal", "coc-coc", "coc_coc")
    if incognito_enabled or prefer_coccoc:
        browser_exe = find_coccoc_browser_exe(config)
        if browser_exe:
            try:
                args = [browser_exe]
                if incognito_enabled:
                    args.append("--incognito")
                args.append(url)
                subprocess.Popen(args, close_fds=True)
                mode_label = "incognito" if incognito_enabled else "normal"
                print(f"Opened Coc Coc {mode_label}: {url}", flush=True)
                return
            except Exception as exc:
                print(f"Could not open Coc Coc: {exc}", flush=True)
        else:
            print("Coc Coc browser.exe was not found. Falling back to the normal browser.", flush=True)
    webbrowser.open(url)

def main() -> int:
    global SERVER_HTTPD, DISTRIBUTED_WORKER_HTTPD
    set_future_server2_process_status("main")
    parser = argparse.ArgumentParser(description="Future local Faster-Whisper server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="en")
    parser.add_argument("--no-preload", action="store_true", help="Debug only: do not warm the Whisper model at startup.")
    parser.add_argument("--preload", action="store_true", help="Compatibility flag; preload is now enabled by default.")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-tunnel", action="store_true")
    parser.add_argument("--replace-old", action="store_true", help="Stop only the recorded previous future server before binding the port.")
    args = parser.parse_args()
    validate_postgres_backend_configuration()
    SERVER_STATE["model_name"] = clean(args.model) or "small"
    SERVER_STATE["language"] = clean(args.language) or "en"
    should_preload = not args.no_preload
    SERVER_STATE["lazy_model_load"] = not should_preload
    configure_paths()
    enable_stt_fault_logging()
    stt_debug_log("server_start", host=args.host, port=args.port, model=SERVER_STATE["model_name"], language=SERVER_STATE["language"], preload=should_preload, lazy_model_load=SERVER_STATE["lazy_model_load"])
    if args.replace_old:
        stopped_pid = stop_previous_server_from_pid_file()
        if stopped_pid:
            print(f"Stopped recorded old Future server PID {stopped_pid}.", flush=True)
    try:
        structure_info = initialize_structure_database()
        if not structure_info.get("migration_complete"):
            raise RuntimeError("PostgreSQL Structure asset migration is incomplete.")
        SERVER_STATE["structure_database"] = structure_info
        structure_backend = "PostgreSQL" if clean(structure_info.get("database", "")).lower().startswith("postgresql:") else "unknown"
        print(
            f"Structure database ready ({structure_backend}): assets {structure_info.get('assets', 0)}, "
            f"raw bytes {structure_info.get('raw_bytes', 0)}",
            flush=True,
        )
    except Exception as exc:
        print(f"Cannot prepare Structure database: {exc}", flush=True)
        return 1
    try:
        info = ensure_server_data_common_folder()
        SERVER_STATE["server_data_root"] = info.get("root", str(SERVER_DATA_ROOT))
        print(f"Server data ready: {SERVER_STATE['server_data_root']}\\common", flush=True)
        database_info = {
            "backend": "postgresql",
            "postgres_only": True,
            "documents_restored": 0,
            "counts": {},
        }
        # Added 2026-07-30: apply additive PostgreSQL tables/indexes before any durable queue access.
        database_info["postgres_schema"] = postgres_initialize_schema()
        # Added 2026-07-29: warm durable Vault placements before HTTP accepts learners.
        database_info["vault_placements"] = server_database_load_vault_cache(None)
        load_auth_sessions()
        database_info["completion_recovery"] = recover_pending_learning_completion_intents()
        hydrate_dashboard = globals().get("hydrate_dashboard_recent_log_state")
        if callable(hydrate_dashboard):
            database_info["dashboard_recent_logs"] = hydrate_dashboard(keep_days=3, limit=500)
        database_info["online_backup"] = {"started": False, "reason": "postgresql_authoritative"}
        SERVER_STATE["database"] = database_info
        print("Server database ready (PostgreSQL authority).", flush=True)
        npc_image_info = ensure_npc_top_browser_images()
        if npc_image_info.get("checked"):
            print(
                f"NPC_TOP images ready: checked {npc_image_info.get('checked', 0)}, browser copies {npc_image_info.get('converted', 0)}, failed {npc_image_info.get('failed', 0)}",
                flush=True,
            )
        start_future_boot_snapshot_cache()
        try:
            # Added 2026-07-16: loads the shared Sound asset JSON/WAL index at boot so Server 2 and builders reuse the same audio cache state.
            from future_sound_asset_index import warm_sound_asset_index
            sound_index_info = warm_sound_asset_index(build_if_missing=False)
            SERVER_STATE["sound_asset_index"] = sound_index_info
            print(
                f"Sound index ready: assets {sound_index_info.get('count', 0)}, signatures {sound_index_info.get('signatures', 0)}, {sound_index_info.get('ms', 0)}ms",
                flush=True,
            )
        except Exception as sound_exc:
            SERVER_STATE["sound_asset_index"] = {"ok": False, "error": str(sound_exc)}
            stt_debug_log("sound_asset_index_warm_failed", error=str(sound_exc))
        # Added 2026-07-30: recover durable TTS leases before accepting new audio requests.
        SERVER_STATE["durable_tts_queue"] = start_durable_tts_dispatcher()
        start_server_data_manifest_monitor()
        schedule_space_pdf_progress_startup_warm()
    except Exception as exc:
        SERVER_STATE["last_error"] = str(exc)
        print(f"Cannot prepare C:\\server data\\common: {exc}", flush=True)
    httpd = FutureThreadingHTTPServer((args.host, int(args.port)), FutureWhisperHandler)
    SERVER_HTTPD = httpd
    worker_httpd = None
    worker_host = ""
    worker_port = bounded_env_int("FUTURE_DISTRIBUTED_WORKER_PORT", 8890, 1024, 65535)
    configured_worker_host = clean(os.environ.get("FUTURE_DISTRIBUTED_WORKER_HOST", ""))
    lan_ips = []
    for ip_text in local_ipv4_addresses():
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if ip.version == 4 and ip.is_private and not ip.is_loopback:
            lan_ips.append(ip_text)
    worker_host = configured_worker_host or (lan_ips[0] if lan_ips else "127.0.0.1")
    try:
        worker_httpd = FutureWorkerHTTPServer((worker_host, worker_port), FutureWhisperHandler)
        DISTRIBUTED_WORKER_HTTPD = worker_httpd
        worker_url = f"http://{worker_host}:{worker_port}"
        SERVER_STATE.update({
            "distributed_worker_url": worker_url,
            "distributed_worker_listener": "lan-only",
            "distributed_worker_host": worker_host,
            "distributed_worker_port": worker_port,
            "distributed_worker_http_max_threads": worker_httpd.future_worker_max_threads,
        })
        threading.Thread(
            target=worker_httpd.serve_forever,
            daemon=True,
            name="future-worker-lan-http",
        ).start()
        print(f"Distributed worker LAN broker listening at {worker_url}", flush=True)
    except Exception as exc:
        DISTRIBUTED_WORKER_HTTPD = None
        SERVER_STATE.update({
            "distributed_worker_url": "",
            "distributed_worker_listener": "failed",
            "distributed_worker_listener_error": str(exc),
        })
        print(f"Distributed worker LAN broker failed: {exc}", flush=True)
    register_current_server_pid()
    browser_host = "127.0.0.1" if args.host in ("", "0.0.0.0", "::") else args.host
    server_url = f"http://{browser_host}:{args.port}"
    tunnel_origin_url = f"http://127.0.0.1:{args.port}"
    install_shutdown_cleanup(tunnel_origin_url)
    local_urls = [server_url]
    if args.host in ("", "0.0.0.0", "::"):
        local_urls.extend(f"http://{ip}:{args.port}" for ip in local_ipv4_addresses())
    SERVER_STATE["server_urls"] = list(dict.fromkeys(local_urls))
    print(f"Future Whisper server listening at {server_url}", flush=True)
    print(f"Future app served at {server_url}/login", flush=True)
    try:
        start_server_screen_clip_hotkey()
    except Exception as exc:
        print(f"[server-screen-clip] hotkey start skipped: {exc}", flush=True)
    if not args.no_browser:
        threading.Timer(0.15, lambda: open_future_start_page(f"{server_url}/status")).start()

    def _background_startup_tasks() -> None:
        SERVER_STATE.update({"warm_status": "Warm queue starting...", "warm_ready": False, "warm_started_at": time.time(), "warm_finished_at": 0})
        try:
            # Added 2026-07-29: once HTTP is ready, serve the first login or
            # completion burst before scanning derived startup indexes. This
            # keeps true-cold requests independent from background CPU work.
            SERVER_STATE["startup_request_priority_wait"] = httpd.wait_for_request_quiet(0.75, 10.0)
            SERVER_STATE["warm_status"] = "Checking server-data manifest..."
            if should_preload:
                SERVER_STATE["warm_status"] = "Warming STT worker..."
                print("Starting/reusing Future STT worker in background ...", flush=True)
                try:
                    ensure_stt_worker_process(SERVER_STATE["model_name"], SERVER_STATE["language"], preload=True)
                except Exception as exc:
                    SERVER_STATE["last_error"] = str(exc)
                    print(f"Future STT worker start skipped: {exc}", flush=True)
            else:
                SERVER_STATE["warm_status"] = "STT warm skipped by flag."
            SERVER_STATE["warm_status"] = "Warming Lesson Vault task progress index..."
            # Added 2026-07-10: keep Space Task folder assignment bursts from parsing the learning log on first user entry.
            try:
                learning_completion_log_index()
            except Exception as exc:
                stt_debug_log("lesson_vault_task_progress_warm_failed", error=str(exc))
            try:
                warm_lesson_tasks_response_cache_async(8, 0.2)
            except Exception as exc:
                stt_debug_log("lesson_tasks_response_cache_warm_start_failed", error=str(exc))
            recover_vocab_leaderboard_period_wal_async()
            replay_space_v_registry_sync_wal_async()
            SERVER_STATE["warm_status"] = "Warming QmDict cache..."
            # Added 2026-07-30: the initial startup request-priority gate above
            # is sufficient. A second quiet gate was reset by dashboard polls
            # and could delay this ~1.4s warm step for up to 60 seconds.
            SERVER_STATE["qmdict_runtime_priority_wait"] = {"skipped": True, "waited_ms": 0.0}
            SERVER_STATE["qmdict_runtime_priority_wait_ms"] = 0
            qmdict_warm_started = time.perf_counter()
            qmdict_warm_result = warm_qmdict_runtime(0.2)
            SERVER_STATE["qmdict_runtime_warm_wall_ms"] = int((time.perf_counter() - qmdict_warm_started) * 1000)
            SERVER_STATE["qmdict_runtime_warm_result"] = qmdict_warm_result
            SERVER_STATE["warm_status"] = "Preparing deterministic QMLearn audio paths..."
            warm_qmlearn_voice_audio_index_async(0.3)
            SERVER_STATE["warm_status"] = "Warming Space_V local picture index..."
            warm_space_v_local_picture_index_async(0.1)
            SERVER_STATE["warm_status"] = "Pinning process workers in RAM..."
            warm_future_process_workers_async(0.6)
            SERVER_STATE["warm_status"] = "Warming PDF and picture index..."
            if not use_pdf_picture_metadata_boot_snapshot():
                start_pdf_picture_metadata_warmer()
            SERVER_STATE["warm_status"] = "Warming MishiKa question cache..."
            warm_space_pdf_ai_region_question_cache_async(0.2)
            SERVER_STATE["warm_status"] = "Warming frontend cache..."
            warm_frontend_delivery_cache_async(0.2)
            try:
                warm_vocab_leaderboard_chat_cache(100)
            except Exception as exc:
                stt_debug_log("vocab_leaderboard_chat_warm_failed", error=str(exc))
            SERVER_STATE["warm_status"] = "Warming QM City training cache..."
            warm_qm_city_training_cache_async(1.2, limit=160)
            if not args.no_tunnel:
                SERVER_STATE["warm_status"] = "Starting Cloudflare Tunnel..."
                print("Starting Cloudflare Tunnel for internet access ...", flush=True)
                start_cloudflare_tunnel(tunnel_origin_url)
            else:
                SERVER_STATE["tunnel_status"] = "disabled"
                SERVER_STATE["warm_status"] = "Tunnel disabled. Finalizing warm..."
            SERVER_STATE.update({"warm_status": "Warm ready", "warm_ready": True, "warm_finished_at": time.time()})
        except Exception as exc:
            SERVER_STATE.update({"warm_status": f"Warm warning: {clean(exc)}", "warm_ready": False, "warm_finished_at": time.time()})

    threading.Thread(target=_background_startup_tasks, daemon=True, name="future-background-startup").start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_runtime()
        if worker_httpd is not None:
            try:
                worker_httpd.shutdown()
            except Exception:
                pass
            worker_httpd.server_close()
        DISTRIBUTED_WORKER_HTTPD = None
        httpd.server_close()
        SERVER_HTTPD = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
