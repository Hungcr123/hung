# Loaded by FUTURE.server_parts.11_http_server into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def do_GET(self):
    self._future_handler_started_at = time.perf_counter()
    self._future_handler_is_first_request = not bool(getattr(self, "_future_handler_seen_request", False))
    self._future_handler_seen_request = True
    parsed = urlparse(self.path)
    path = parsed.path.rstrip("/") or "/"
    if not future_worker_listener_allows(self, path, "GET"):
        return
    self.record_security_poll_stat(path, "GET")
    if not self.enforce_security_block(path):
        return
    if not self.enforce_anti_robot_rate(path, "GET"):
        return
    if path == "/favicon.ico":
        self.send_response(204)
        self.safe_finish_response()
        return
    if path == "/anti-robot/challenge":
        if not self.enforce_anti_robot_challenge(path, "GET"):
            return
        self.send_json(200, {
            "ok": True,
            "token": make_anti_robot_token(self.anti_robot_client_key()),
            "ttl": ANTI_ROBOT_TOKEN_TTL_SECONDS,
        })
        return
    if path.startswith(FRONTEND_ASSET_ROUTE_PREFIX):
        try:
            target = frontend_asset_path_from_route(path)
            host_header = clean(self.headers.get("Host", ""))
            hosted = should_serve_obfuscated_frontend(self.client_address[0], host_header)
            if target.suffix.lower() == ".js" and hosted:
                self.send_json(403, {"ok": False, "error": "Hosted JavaScript is delivered through the protected HTML build."})
                return
            self.send_bytes(
                200,
                cached_public_file_bytes(target),
                frontend_asset_content_type(target),
                cache_control="no-store, no-cache, max-age=0, must-revalidate",
                etag=public_file_etag(target, f"future-asset-{target.suffix.lower().lstrip('.')}"),
                extra_headers={
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer",
                    "X-Robots-Tag": "noindex, nofollow, noarchive",
                },
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/frontend-version":
        try:
            stat = PUBLIC_FRONTEND_PATH.stat()
            signature = frontend_delivery_signature()
            reload_state = frontend_reload_state()
            source_etag = clean(signature.get("version", "")) or public_file_etag(PUBLIC_FRONTEND_PATH, "future-source")
            self.send_json(200, {
                "ok": True,
                "version": source_etag,
                "reload_token": reload_state.get("token", ""),
                "reload_updated_at": reload_state.get("updated_at", ""),
                "reload_reason": reload_state.get("reason", ""),
                "reload_command": reload_state.get("command", ""),
                "global_audio_cache_epoch": global_audio_cache_epoch(),
                "etag": source_etag,
                "mtime_ns": int(stat.st_mtime_ns),
                "size": int(stat.st_size),
                "files": signature.get("files", []),
                "updated_at": utc_timestamp(),
            })
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf-metadata/status":
        session = self.auth_session()
        if not self.is_local_admin_request() and not (session and is_admin_user(session.get("username", ""))):
            self.send_json(403, {"ok": False, "error": "Only admin can view PDF metadata index status."})
            return
        self.send_json(200, {"ok": True, **pdf_picture_metadata_status()})
        return
    if path in ("/", "/status"):
        if not self.is_local_admin_request():
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/login")
                self.safe_finish_response()
            else:
                self.send_json(403, {"ok": False, "error": "Dashboard chi mo tren may server. Hay dung /login de hoc."})
            return
        self.send_html(200, status_page())
        return
    if path == "/tunnel-dashboard":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Tunnel dashboard is only available on the server machine."})
            return
        try:
            dashboard_path = ROOT / "Tunnel Dashboard.html"
            self.send_bytes(
                200,
                dashboard_path.read_bytes(),
                "text/html; charset=utf-8",
                cache_control="private, no-store, no-cache, max-age=0, must-revalidate",
                etag=public_file_etag(dashboard_path, "future-tunnel-dashboard"),
                extra_headers={
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer",
                    "X-Robots-Tag": "noindex, nofollow, noarchive",
                },
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    app_routes = {"/login", "/lesson_vault", "/space_w", "/space_v", "/space_q", "/space_p", "/space_s", "/space_l", "/space_pdf", "/space_picture"}
    if path in ("/future", "/future.html") or path.startswith("/future.html/") or path in app_routes:
        try:
            host_header = clean(self.headers.get("Host", ""))
            hosted = should_serve_obfuscated_frontend(self.client_address[0], host_header)
            payload = future_hosted_html_bytes() if hosted else future_html_bytes()
            frontend_path = OBFUSCATED_FRONTEND_PATH if hosted and OBFUSCATED_FRONTEND_PATH.is_file() else PUBLIC_FRONTEND_PATH
            etag = public_file_etag(frontend_path, "future-hosted" if hosted else "future-local")
            self.send_bytes(
                200,
                payload,
                "text/html; charset=utf-8",
                cache_control="private, no-store, no-cache, max-age=0, must-revalidate",
                etag=etag,
                extra_headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "no-referrer",
                    "X-Robots-Tag": "noindex, nofollow, noarchive",
                    "X-Download-Options": "noopen",
                    "X-Permitted-Cross-Domain-Policies": "none",
                },
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/face-1.html":
        try:
            self.send_bytes(
                200,
                face1_html_bytes(),
                "text/html; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=public_file_etag(PUBLIC_FACE1_PATH, "face-1"),
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/face-2.html":
        try:
            self.send_bytes(
                200,
                face2_html_bytes(),
                "text/html; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=public_file_etag(PUBLIC_FACE2_PATH, "face-2"),
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/health":
        query = parse_qs(parsed.query)
        compact_dashboard = clean((query.get("view") or [""])[0]).lower() == "dashboard-v1"
        data, cache_hit = public_health_response_bytes(
            self.is_local_admin_request(),
            include_settings=not compact_dashboard,
        )
        self.send_bytes(
            200,
            data,
            "application/json; charset=utf-8",
            cache_control="no-store",
            extra_headers={"X-Future-Cache-Hit": "health-bytes" if cache_hit else "health-build"},
        )
        return
    if path == "/distributed-worker/download":
        if not (self.is_local_admin_request() or self.auth_session()):
            self.send_json(401, {"ok": False, "error": "Dang nhap de tai goi worker cho may nay."})
            return
        try:
            package_path = distributed_worker_client_zip_path()
            package_size = package_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(package_size))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Content-Disposition", 'attachment; filename="future_distributed_worker_full.zip"')
            self.send_header("X-Future-File-Bytes", str(package_size))
            if not self.safe_finish_response():
                return
            with package_path.open("rb") as file_in:
                while True:
                    chunk = file_in.read(1024 * 1024)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                        break
                    except OSError as write_exc:
                        if getattr(write_exc, "winerror", None) in {10053, 10054, 10058}:
                            break
                        raise
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/dashboard/space-v-picture-settings":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi dashboard tren may server moi duoc xem duong dan picture."})
            return
        try:
            self.send_json(200, {"ok": True, **space_v_local_picture_settings_payload()})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/settings":
        row = public_server_settings_response_cache_row()
        self.send_bytes(
            200,
            row.get("bytes", b""),
            "application/json; charset=utf-8",
            cache_control="public, max-age=0, must-revalidate",
            etag=clean(row.get("etag", "")),
            extra_headers={"X-Future-Cache-Hit": "settings-bytes" if row.get("cache_hit") else "settings-build"},
        )
        return
    if path == "/qmdict/reload-status":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Admin QmDict status is only available on the server machine."})
            return
        self.send_json(
            200,
            {
                "ok": True,
                "qmdict_reload": qmdict_reload_state_snapshot(),
                "qmdict_audio_refresh": qmdict_audio_refresh_job_snapshot(),
                "qmdict_word_audio_refresh": qmdict_word_audio_refresh_job_snapshot(),
                "space_v_repair": space_v_qmdict_repair_snapshot(),
            },
        )
        return
    if path == "/announcements":
        row = announcements_response_cache_row()
        self.send_bytes(
            200,
            row.get("bytes", b""),
            "application/json; charset=utf-8",
            cache_control="public, max-age=0, must-revalidate",
            etag=clean(row.get("etag", "")),
            extra_headers={"X-Future-Cache-Hit": "announcements-bytes" if row.get("cache_hit") else "announcements-build"},
        )
        return
    if path == "/chat/attachment":
        try:
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            download = clean((query.get("download") or ["0"])[0]).lower() in ("1", "true", "yes")
            display_name = chat_safe_filename((query.get("name") or [""])[0] or Path(rel_path).name)
            target = safe_chat_attachment_path(rel_path)
            content_type = chat_attachment_mime(target.name, mimetypes.guess_type(target.name)[0] or "")
            disposition_type = "attachment" if download else "inline"
            disposition = inline_content_disposition_filename(display_name, "attachment").replace("inline;", f"{disposition_type};", 1)
            self.send_bytes(
                200,
                target.read_bytes(),
                content_type,
                cache_control="private, max-age=86400",
                accept_ranges=True,
                content_disposition=disposition,
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/chat/poll":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        try:
            since = int(clean((query.get("since") or ["0"])[0]) or 0)
        except ValueError:
            since = 0
        is_open = clean((query.get("open") or ["0"])[0]).lower() in ("1", "true", "yes")
        username = session.get("username", "")
        chat_mark_online(username)
        touch_user_activity_seen(username)
        try:
            notice_after = int(clean((query.get("notice_after") or query.get("immediate_after") or ["0"])[0]) or 0)
        except ValueError:
            notice_after = 0
        chat_snapshot = chat_poll_snapshot(username, since, mark_read=is_open)
        self.send_json(200, {
            "ok": True,
            "username": username,
            **chat_snapshot,
            "server_time": chat_now(),
            **lesson_task_notice_immediate_payload(username, notice_after),
        })
        return
    if path == "/chat/admin/state":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem chat."})
            return
        query = parse_qs(parsed.query)
        message_user = clean((query.get("messages_for") or query.get("user") or [""])[0])
        include_all_messages = clean((query.get("messages") or ["0"])[0]).lower() in ("1", "true", "yes", "all")
        include_activity = clean((query.get("activity") or ["1"])[0]).lower() not in ("0", "false", "no")
        self.send_json(200, {"ok": True, **chat_admin_state(message_user=message_user, include_all_messages=include_all_messages, include_activity=include_activity)})
        return
    if path == "/screen/auth-admin/state":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can view online screen users."})
            return
        chat_mark_online(admin_session.get("username", ""))
        query = parse_qs(parsed.query)
        message_user = clean((query.get("messages_for") or query.get("user") or [""])[0])
        self.send_json(200, {"ok": True, **chat_admin_state(message_user=message_user, include_all_messages=False, include_activity=True)})
        return
    if path == "/chat/admin/voices":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem voice chat."})
            return
        query = parse_qs(parsed.query)
        force = clean((query.get("refresh") or ["0"])[0]).lower() in ("1", "true", "yes")
        self.send_json(200, {"ok": True, **chat_voice_option_payload(force_refresh=force)})
        return
    if path == "/chat/voices":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        chat_mark_online(session.get("username", ""))
        payload = chat_voice_option_payload(force_refresh=False)
        self.send_json(200, {"ok": True, "vi": payload.get("vi", []), "en": payload.get("en", []), "ready": payload.get("ready", False), "error": payload.get("error", "")})
        return
    if path == "/stream/state":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = session.get("username", "")
        chat_mark_online(username)
        self.send_json(200, {"ok": True, "session": stream_session_for_user(username), "admin_online": dashboard_is_online()})
        return
    if path == "/stream/poll":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        username = session.get("username", "")
        chat_mark_online(username)
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **stream_poll_chunks(username, session_id, after, "user")})
        return
    if path == "/stream/signal":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        username = session.get("username", "")
        chat_mark_online(username)
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **stream_poll_signal(username, "user", session_id, after)})
        return
    if path == "/stream/admin/poll":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **stream_poll_chunks(username, session_id, after, "admin")})
        return
    if path == "/stream/admin/signal":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi stream."})
            return
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **stream_poll_signal(username, "admin", session_id, after)})
        return
    if path == "/screen/state":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = session.get("username", "")
        chat_mark_online(username)
        self.send_json(200, {"ok": True, "session": screen_session_for_user(username), "admin_online": dashboard_is_online()})
        return
    if path == "/screen/signal":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        username = session.get("username", "")
        chat_mark_online(username)
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_signal(username, "user", session_id, after)})
        return
    if path == "/screen/control":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        username = session.get("username", "")
        chat_mark_online(username)
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_control(username, session_id, after)})
        return
    if path == "/screen/admin/frame":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem man hinh."})
            return
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_frame(username, session_id, after)})
        return
    if path == "/screen/auth-admin/frame":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can view screen frames."})
            return
        chat_mark_online(admin_session.get("username", ""))
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_frame(username, session_id, after)})
        return
    if path == "/screen/admin/audio":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi nghe screen."})
            return
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_audio_chunks(username, session_id, after, "admin")})
        return
    if path == "/screen/auth-admin/audio":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can listen to screen audio."})
            return
        chat_mark_online(admin_session.get("username", ""))
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_audio_chunks(username, session_id, after, "admin")})
        return
    if path == "/screen/audio":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = session.get("username", "")
        chat_mark_online(username)
        query = parse_qs(parsed.query)
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_audio_chunks(username, session_id, after, "user")})
        return
    if path == "/screen/admin/signal":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem man hinh."})
            return
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_signal(username, "admin", session_id, after)})
        return
    if path == "/screen/auth-admin/signal":
        admin_session = self.auth_admin_session()
        if not admin_session:
            self.send_json(403, {"ok": False, "error": "Only admins can view screen signals."})
            return
        chat_mark_online(admin_session.get("username", ""))
        query = parse_qs(parsed.query)
        username = clean((query.get("username") or [""])[0])
        session_id = clean((query.get("session") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, **screen_poll_signal(username, "admin", session_id, after)})
        return
    if path == "/paint/state":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = session.get("username", "")
        chat_mark_online(username)
        query = parse_qs(parsed.query)
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, "state": paint_public_state(username, include_data=True, after=after)})
        return
    if path == "/paint/admin/state":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server moi xem paint."})
            return
        query = parse_qs(parsed.query)
        username = normalize_username((query.get("username") or [""])[0])
        try:
            after = int(clean((query.get("after") or ["0"])[0]) or 0)
        except ValueError:
            after = 0
        self.send_json(200, {"ok": True, "state": paint_public_state(username, include_data=True, after=after)})
        return
    if path == "/auth/username":
        try:
            query = parse_qs(parsed.query)
            username = normalize_username((query.get("username") or query.get("user") or [""])[0])
            self.send_json(200, auth_username_lookup_payload(username))
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/common-tree":
        tree_request_started = time.perf_counter()
        common_phase_trace = {}
        tree_build_lock = None
        tree_cache_key = None
        tree_lock_acquired = False
        cache_lookup_ms = 0.0
        lock_wait_ms = 0.0
        build_ms = 0.0
        serialize_ms = 0.0
        compress_ms = 0.0
        send_ms = 0.0
        try:
            overlay_auth_started = time.perf_counter()
            session = self.auth_session()
            auth_ms = (time.perf_counter() - overlay_auth_started) * 1000
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            admin_view = bool(is_admin_user(username))
            manifest = get_server_data_manifest(force=False)
            structural_version = int(manifest.get("structural_metadata_version", 0) or 0) if isinstance(manifest, dict) else 0
            common_revision = server_data_manifest_runtime_revision(manifest, {"common"})
            tree_cache_revision = f"{common_revision}:sm{structural_version}"
            tree_cache_key = ("__shared_common_tree__", "common", tree_cache_revision)
            etag = f'"ft-tree-{hashlib.sha1("|".join(tree_cache_key).encode("utf-8")).hexdigest()}"'
            if clean(self.headers.get("If-None-Match", "")) == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
                self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
                self.safe_finish_response()
                return
            cache_lookup_started = time.perf_counter()
            with SERVER_DATA_LIST_CACHE_LOCK:
                tree_cache = globals().setdefault("SERVER_DATA_COMMON_TREE_PRELOAD_BYTES_CACHE", {})
                tree_locks = globals().setdefault("SERVER_DATA_COMMON_TREE_PRELOAD_BUILD_LOCKS", {})
                tree_build_lock = tree_locks.get(tree_cache_key)
                if tree_build_lock is None:
                    tree_build_lock = threading.Lock()
                    tree_locks[tree_cache_key] = tree_build_lock
                if len(tree_locks) > LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                    for old_key, old_lock in list(tree_locks.items()):
                        if old_key != tree_cache_key and not old_lock.locked():
                            tree_locks.pop(old_key, None)
                            if len(tree_locks) <= LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                                break
            cache_lookup_ms = (time.perf_counter() - cache_lookup_started) * 1000
            lock_started = time.perf_counter()
            tree_build_lock.acquire()
            tree_lock_acquired = True
            lock_wait_ms = (time.perf_counter() - lock_started) * 1000
            with SERVER_DATA_LIST_CACHE_LOCK:
                cached_tree = tree_cache.get(tree_cache_key) if isinstance(tree_cache, dict) else None
            tree_cache_hit = isinstance(cached_tree, dict)
            if not tree_cache_hit:
                build_started = time.perf_counter()
                tree_payload = build_server_data_common_tree_snapshot(manifest, trace=common_phase_trace)
                build_ms = (time.perf_counter() - build_started) * 1000
                serialize_started = time.perf_counter()
                identity_data = json_bytes(tree_payload)
                serialize_ms = (time.perf_counter() - serialize_started) * 1000
                compress_started = time.perf_counter()
                cached_tree = {
                    "identity": b"",
                    "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
                    "decoded_bytes": len(identity_data),
                }
                compress_ms = (time.perf_counter() - compress_started) * 1000
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_cache[tree_cache_key] = cached_tree
                    if len(tree_cache) > SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS:
                        for old_key in list(tree_cache.keys())[: max(1, len(tree_cache) - SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS)]:
                            tree_cache.pop(old_key, None)
            accepts_gzip = "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
            response_data = bytes(cached_tree.get("gzip") or b"") if accepts_gzip else bytes(cached_tree.get("identity") or b"")
            if not accepts_gzip and not response_data and cached_tree.get("gzip"):
                response_data = gzip.decompress(bytes(cached_tree.get("gzip") or b""))
            send_started = time.perf_counter()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_data)))
            self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
            self.send_header("ETag", etag)
            self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
            if accepts_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("X-Future-Cache-Hit", "common-tree" if tree_cache_hit else "miss")
            self.send_header("X-Future-Common-Revision", common_revision)
            self.send_header("X-Future-Common-Cache-Key", "server2-common-tree:user-scope")
            server_timing = ", ".join([
                f"common_auth;dur={auth_ms:.3f}",
                f"common_cache_lookup;dur={cache_lookup_ms:.3f}",
                f"common_lock;dur={lock_wait_ms:.3f}",
                f"common_manifest;dur={(common_phase_trace.get('manifest_ready', 0.0) - common_phase_trace.get('snapshot_start', 0.0)) * 1000:.3f}" if common_phase_trace.get("snapshot_start") else "common_manifest;dur=0.000",
                f"common_compact_base;dur={(common_phase_trace.get('compact_base_done', 0.0) - common_phase_trace.get('snapshot_start', 0.0)) * 1000:.3f}" if common_phase_trace.get("snapshot_start") else "common_compact_base;dur=0.000",
                f"common_rows_by_path;dur={(common_phase_trace.get('rows_by_path_done', 0.0) - common_phase_trace.get('manifest_ready', 0.0)) * 1000:.3f}" if common_phase_trace.get("rows_by_path_done") else "common_rows_by_path;dur=0.000",
                f"common_rows_by_root;dur={(common_phase_trace.get('rows_by_root_done', 0.0) - common_phase_trace.get('rows_by_path_done', 0.0)) * 1000:.3f}" if common_phase_trace.get("rows_by_root_done") else "common_rows_by_root;dur=0.000",
                f"common_payload_ready;dur={(common_phase_trace.get('payload_ready', 0.0) - common_phase_trace.get('rows_compacted', 0.0)) * 1000:.3f}" if common_phase_trace.get("payload_ready") else "common_payload_ready;dur=0.000",
                f"common_build;dur={build_ms:.3f}",
                f"common_serialize;dur={serialize_ms:.3f}",
                f"common_compress;dur={compress_ms:.3f}",
                f"common_send;dur={(time.perf_counter() - send_started) * 1000:.3f}",
                f"common_prepare;dur={(time.perf_counter() - tree_request_started) * 1000:.3f}",
            ])
            self.send_header("Server-Timing", server_timing)
            queue_wait_ms = self.request_queue_wait_ms()
            write_started = time.perf_counter()
            self.safe_finish_response(response_data)
            stt_debug_log(
                "common_tree_response_timing",
                cache_hit=tree_cache_hit,
                queue_wait_ms=round(queue_wait_ms, 3),
                handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
                write_ms=round((time.perf_counter() - write_started) * 1000, 3),
                bytes=len(response_data),
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        finally:
            if tree_lock_acquired and tree_build_lock is not None and tree_build_lock.locked():
                tree_build_lock.release()
            if tree_cache_key is not None:
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_locks = globals().setdefault("SERVER_DATA_COMMON_TREE_PRELOAD_BUILD_LOCKS", {})
                    if tree_locks.get(tree_cache_key) is tree_build_lock:
                        tree_locks.pop(tree_cache_key, None)
        return
    if path == "/server-data/user-overlay":
        tree_request_started = time.perf_counter()
        overlay_manifest_started = time.perf_counter()
        tree_build_lock = None
        tree_cache_key = None
        tree_lock_acquired = False
        auth_ms = 0.0
        try:
            overlay_auth_started = time.perf_counter()
            session = self.auth_session()
            auth_ms = (time.perf_counter() - overlay_auth_started) * 1000
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            admin_view = bool(is_admin_user(username))
            manifest = get_server_data_manifest(force=False)
            manifest_ms = (time.perf_counter() - overlay_manifest_started) * 1000
            structural_version = int(manifest.get("structural_metadata_version", 0) or 0) if isinstance(manifest, dict) else 0
            overlay_roots_started = time.perf_counter()
            if admin_view:
                registered_users = {
                    normalize_username(item).lower()
                    for item in list_dashboard_usernames()
                    if normalize_username(item)
                }
                overlay_roots = {"admin", username.lower(), *registered_users}
            else:
                overlay_roots = {username.lower()} if username else set()
            overlay_roots = {
                item for item in overlay_roots
                if item and item != "common" and item not in {clean(skip).lower() for skip in server_data_manifest_skip_tops()}
            }
            overlay_roots_ms = (time.perf_counter() - overlay_roots_started) * 1000
            overlay_revision_started = time.perf_counter()
            overlay_manifest_revision = server_data_manifest_user_overlay_revision(manifest, overlay_roots) if overlay_roots else ""
            overlay_manifest_revision_ms = (time.perf_counter() - overlay_revision_started) * 1000
            overlay_revision_started = time.perf_counter()
            vault_revision_reader = globals().get("server_database_vault_revision")
            vault_revision = int(vault_revision_reader(username) or 0) if callable(vault_revision_reader) and username else 0
            overlay_revision_ms = (time.perf_counter() - overlay_revision_started) * 1000
            overlay_revision = f"{overlay_manifest_revision}:v{vault_revision}"
            overlay_context = {
                "viewer": username,
                "overlay_roots": overlay_roots,
                "overlay_manifest_revision": overlay_manifest_revision,
                "vault_revision": vault_revision,
                "overlay_revision": overlay_revision,
                "structural_version": structural_version,
            }
            tree_cache_key = (username.lower(), "admin" if admin_view else "user", f"{overlay_revision}:sm{structural_version}")
            etag = f'"ft-overlay-{hashlib.sha1("|".join(tree_cache_key).encode("utf-8")).hexdigest()}"'
            if clean(self.headers.get("If-None-Match", "")) == etag:
                server_timing = ", ".join([
                    f"overlay_auth;dur={auth_ms:.3f}",
                    f"overlay_manifest;dur={manifest_ms:.3f}",
                    f"overlay_roots;dur={overlay_roots_ms:.3f}",
                    f"overlay_manifest_revision;dur={overlay_manifest_revision_ms:.3f}",
                    f"overlay_vault_revision;dur={overlay_revision_ms:.3f}",
                    f"overlay_prepare;dur={(time.perf_counter() - tree_request_started) * 1000:.3f}",
                ])
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, max-age=120, must-revalidate")
                self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
                self.send_header("Server-Timing", server_timing)
                self.safe_finish_response()
                return
            tree_cache = globals().get("SERVER_DATA_USER_OVERLAY_BYTES_CACHE", {})
            cached_tree = tree_cache.get(tree_cache_key) if isinstance(tree_cache, dict) else None
            tree_cache_hit = isinstance(cached_tree, dict)
            if tree_cache_hit:
                accepts_gzip = "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
                response_data = bytes(cached_tree.get("gzip") or b"") if accepts_gzip else bytes(cached_tree.get("identity") or b"")
                if not accepts_gzip and not response_data and cached_tree.get("gzip"):
                    response_data = gzip.decompress(bytes(cached_tree.get("gzip") or b""))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_data)))
                self.send_header("Cache-Control", "private, max-age=120, must-revalidate")
                self.send_header("ETag", etag)
                self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
                if accepts_gzip:
                    self.send_header("Content-Encoding", "gzip")
                self.send_header("X-Future-Cache-Hit", "user-overlay")
                self.send_header("X-Future-Overlay-Revision", overlay_revision)
                self.send_header("Server-Timing", ", ".join([
                    f"overlay_auth;dur={auth_ms:.3f}",
                    f"overlay_manifest;dur={manifest_ms:.3f}",
                    f"overlay_roots;dur={overlay_roots_ms:.3f}",
                    f"overlay_manifest_revision;dur={overlay_manifest_revision_ms:.3f}",
                    f"overlay_vault_revision;dur={overlay_revision_ms:.3f}",
                    f"overlay_build;dur=0.000",
                    f"overlay_serialize;dur=0.000",
                    f"overlay_compress;dur=0.000",
                    f"overlay_prepare;dur={(time.perf_counter() - tree_request_started) * 1000:.3f}",
                ]))
                queue_wait_ms = self.request_queue_wait_ms()
                write_started = time.perf_counter()
                self.safe_finish_response(response_data)
                stt_debug_log(
                    "user_overlay_response_timing",
                    cache_hit=tree_cache_hit,
                    queue_wait_ms=round(queue_wait_ms, 3),
                    handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3),
                    write_ms=round((time.perf_counter() - write_started) * 1000, 3),
                    bytes=len(response_data),
                )
                return
            lock_started = time.perf_counter()
            with SERVER_DATA_LIST_CACHE_LOCK:
                tree_cache = globals().setdefault("SERVER_DATA_USER_OVERLAY_BYTES_CACHE", {})
                tree_locks = globals().setdefault("SERVER_DATA_USER_OVERLAY_BUILD_LOCKS", {})
                tree_build_lock = tree_locks.get(tree_cache_key)
                if tree_build_lock is None:
                    tree_build_lock = threading.Lock()
                    tree_locks[tree_cache_key] = tree_build_lock
                if len(tree_locks) > LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                    for old_key, old_lock in list(tree_locks.items()):
                        if old_key != tree_cache_key and not old_lock.locked():
                            tree_locks.pop(old_key, None)
                            if len(tree_locks) <= LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                                break
            lock_timeout = max(1.0, float(globals().get("LOGIN_PRELOAD_BUILD_LOCK_TIMEOUT_SECONDS", 15.0) or 15.0))
            if not tree_build_lock.acquire(timeout=lock_timeout):
                self.send_json(503, {
                    "ok": False,
                    "error": "User overlay build is busy; retry shortly.",
                    "retry_after_ms": int(lock_timeout * 1000),
                })
                return
            tree_lock_acquired = True
            lock_wait_ms = (time.perf_counter() - lock_started) * 1000
            with SERVER_DATA_LIST_CACHE_LOCK:
                cached_tree = tree_cache.get(tree_cache_key) if isinstance(tree_cache, dict) else None
            tree_cache_hit = isinstance(cached_tree, dict)
            build_started = time.perf_counter()
            serialize_ms = 0.0
            compress_ms = 0.0
            if not tree_cache_hit:
                overlay_payload = build_server_data_user_tree_overlay(username, admin=admin_view, manifest=manifest, overlay_context=overlay_context)
                serialize_started = time.perf_counter()
                identity_data = json_bytes(overlay_payload)
                serialize_ms = (time.perf_counter() - serialize_started) * 1000
                compress_started = time.perf_counter()
                cached_tree = {
                    "identity": identity_data,
                    "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
                    "decoded_bytes": len(identity_data),
                }
                compress_ms = (time.perf_counter() - compress_started) * 1000
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_cache[tree_cache_key] = cached_tree
                    if len(tree_cache) > SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS:
                        for old_key in list(tree_cache.keys())[: max(1, len(tree_cache) - SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS)]:
                            tree_cache.pop(old_key, None)
            accepts_gzip = "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
            response_data = bytes(cached_tree.get("gzip") or b"") if accepts_gzip else bytes(cached_tree.get("identity") or b"")
            if not accepts_gzip and not response_data and cached_tree.get("gzip"):
                response_data = gzip.decompress(bytes(cached_tree.get("gzip") or b""))
            server_timing = ", ".join([
                f"overlay_auth;dur={auth_ms:.3f}",
                f"overlay_manifest;dur={manifest_ms:.3f}",
                f"overlay_roots;dur={overlay_roots_ms:.3f}",
                f"overlay_manifest_revision;dur={overlay_manifest_revision_ms:.3f}",
                f"overlay_vault_revision;dur={overlay_revision_ms:.3f}",
                f"overlay_lock;dur={lock_wait_ms:.3f}",
                f"overlay_build;dur={(time.perf_counter() - build_started) * 1000:.3f}",
                f"overlay_serialize;dur={serialize_ms:.3f}",
                f"overlay_compress;dur={compress_ms:.3f}",
                f"overlay_prepare;dur={(time.perf_counter() - tree_request_started) * 1000:.3f}",
            ])
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_data)))
            self.send_header("Cache-Control", "private, max-age=120, must-revalidate")
            self.send_header("ETag", etag)
            self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
            if accepts_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("X-Future-Cache-Hit", "user-overlay" if tree_cache_hit else "user-overlay-build")
            self.send_header("X-Future-Overlay-Revision", overlay_revision)
            self.send_header("Server-Timing", server_timing)
            response_started = time.perf_counter()
            headers_ms = (time.perf_counter() - response_started) * 1000
            write_started = time.perf_counter()
            self.safe_finish_response(response_data)
            write_ms = (time.perf_counter() - write_started) * 1000
            if headers_ms > 0 or write_ms > 0:
                stt_debug_log("user_overlay_response_timing", cache_hit=tree_cache_hit, headers_ms=round(headers_ms, 3), queue_wait_ms=round(self.request_queue_wait_ms(), 3), handler_elapsed_ms=round(self.request_handler_elapsed_ms(), 3), write_ms=round(write_ms, 3), bytes=len(response_data))
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        finally:
            if tree_lock_acquired and tree_build_lock is not None and tree_build_lock.locked():
                tree_build_lock.release()
            if tree_cache_key is not None:
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_locks = globals().setdefault("SERVER_DATA_USER_OVERLAY_BUILD_LOCKS", {})
                    if tree_locks.get(tree_cache_key) is tree_build_lock and tree_build_lock is not None and not tree_build_lock.locked():
                        tree_locks.pop(tree_cache_key, None)
        return
    if path == "/server-data/tree-preload":
        tree_request_started = time.perf_counter()
        tree_build_lock = None
        tree_cache_key = None
        tree_lock_acquired = False
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            admin_view = bool(is_admin_user(username))
            manifest = get_server_data_manifest(force=False)
            manifest_signature = server_data_tree_runtime_revision(username, admin_view, manifest)
            structural_version = int(manifest.get("structural_metadata_version", 0) or 0) if isinstance(manifest, dict) else 0
            tree_cache_revision = f"{manifest_signature}:sm{structural_version}"
            snapshot_username, tree_cache_identity = server_data_tree_snapshot_identity(username, admin_view, manifest)
            tree_cache_key = (tree_cache_identity, "admin" if admin_view else "user", tree_cache_revision)
            etag = f'"ft-tree-{hashlib.sha1("|".join(tree_cache_key).encode("utf-8")).hexdigest()}"'
            if clean(self.headers.get("If-None-Match", "")) == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
                self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
                self.safe_finish_response()
                return
            with SERVER_DATA_LIST_CACHE_LOCK:
                tree_cache = globals().setdefault("SERVER_DATA_TREE_PRELOAD_BYTES_CACHE", {})
                tree_locks = globals().setdefault("SERVER_DATA_TREE_PRELOAD_BUILD_LOCKS", {})
                tree_build_lock = tree_locks.get(tree_cache_key)
                if tree_build_lock is None:
                    tree_build_lock = threading.Lock()
                    tree_locks[tree_cache_key] = tree_build_lock
                if len(tree_locks) > LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                    for old_key, old_lock in list(tree_locks.items()):
                        if old_key != tree_cache_key and not old_lock.locked():
                            tree_locks.pop(old_key, None)
                            if len(tree_locks) <= LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS:
                                break
            tree_build_lock.acquire()
            tree_lock_acquired = True
            with SERVER_DATA_LIST_CACHE_LOCK:
                cached_tree = tree_cache.get(tree_cache_key) if isinstance(tree_cache, dict) else None
            tree_cache_hit = isinstance(cached_tree, dict)
            if not tree_cache_hit:
                tree_payload = build_server_data_tree_snapshot(snapshot_username, admin=admin_view)
                identity_data = json_bytes(tree_payload)
                cached_tree = {
                    "identity": b"",
                    "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
                }
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_cache[tree_cache_key] = cached_tree
                    if len(tree_cache) > SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS:
                        for old_key in list(tree_cache.keys())[: max(1, len(tree_cache) - SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS)]:
                            tree_cache.pop(old_key, None)
            accepts_gzip = "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
            response_data = bytes(cached_tree.get("gzip") or b"") if accepts_gzip else bytes(cached_tree.get("identity") or b"")
            if not accepts_gzip and not response_data and cached_tree.get("gzip"):
                response_data = gzip.decompress(bytes(cached_tree.get("gzip") or b""))
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_data)))
            self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
            self.send_header("ETag", etag)
            self.send_header("Vary", "Accept-Encoding, Cookie, Authorization")
            if accepts_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("X-Future-Cache-Hit", "tree-preload" if tree_cache_hit else "miss")
            self.send_header("Server-Timing", f"tree_prepare;dur={(time.perf_counter() - tree_request_started) * 1000:.3f}")
            self.safe_finish_response(response_data)
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        finally:
            if tree_lock_acquired and tree_build_lock is not None and tree_build_lock.locked():
                tree_build_lock.release()
            if tree_cache_key is not None:
                with SERVER_DATA_LIST_CACHE_LOCK:
                    tree_locks = globals().setdefault("SERVER_DATA_TREE_PRELOAD_BUILD_LOCKS", {})
                    if tree_locks.get(tree_cache_key) is tree_build_lock:
                        tree_locks.pop(tree_cache_key, None)
        return
    if path == "/server-data/login-preload":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap.", "reason": "auth_required"})
                return
            query = parse_qs(parsed.query)
            session_username = normalize_username(session.get("username", ""))
            username = normalize_username((query.get("username") or query.get("user") or [session_username])[0])
            valid, message = validate_username(username)
            if not valid:
                self.send_json(400, {"ok": False, "error": message, "reason": "invalid_username"})
                return
            if username != session_username:
                self.send_json(403, {"ok": False, "error": "Khong duoc nap du lieu cua user khac.", "reason": "cross_user"})
                return
            rel_path = clean_path_value((query.get("path") or [""])[0])
            response_mode = clean((query.get("response") or query.get("schema") or [""])[0])
            row = get_or_build_login_preload_response_cache_row(username, rel_path, response_mode)
            timing = row.get("timing") if isinstance(row, dict) else {}
            server_timing = ", ".join([
                f"login_preload_list;dur={float((timing or {}).get('list_server_data_ms', 0) or 0):.3f}",
                f"login_preload_progress;dur={float((timing or {}).get('progress_snapshot_ms', 0) or 0):.3f}",
                f"login_preload_progress_index;dur={float((timing or {}).get('progress_snapshot_index_ms', 0) or 0):.3f}",
                f"login_preload_progress_time;dur={float((timing or {}).get('progress_snapshot_time_ms', 0) or 0):.3f}",
                f"login_preload_progress_items;dur={float((timing or {}).get('progress_snapshot_items_ms', 0) or 0):.3f}",
                f"login_preload_progress_cache;dur={float((timing or {}).get('progress_snapshot_cache_ms', 0) or 0):.3f}",
                f"login_preload_last_file;dur={float((timing or {}).get('last_file_state_ms', 0) or 0):.3f}",
                f"login_preload_json;dur={float((timing or {}).get('json_bytes_ms', 0) or 0):.3f}",
                f"login_preload_total;dur={float((timing or {}).get('total_ms', 0) or 0):.3f}",
            ])
            self.send_bytes(
                200,
                row.get("bytes", b""),
                "application/json; charset=utf-8",
                cache_control="private, max-age=0, must-revalidate",
                etag=clean(row.get("etag", "")),
                extra_headers={
                    "X-Future-Cache-Hit": "login-preload-bytes" if row.get("cache_hit") else "login-preload-build",
                    "Server-Timing": server_timing,
                },
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/codex-local-login":
        try:
            if not self.is_local_admin_request():
                self.send_json(404, {"ok": False, "error": "Not found."})
                return
            query = parse_qs(parsed.query)
            marker = clean((query.get("marker") or query.get("codex") or [""])[0])
            if marker != "1":
                self.send_json(403, {"ok": False, "error": "Missing local Codex test marker."})
                return
            username = normalize_username((query.get("username") or query.get("user") or [""])[0])
            if not username:
                self.send_json(400, {"ok": False, "error": "Vui lòng nhập tên tài khoản.", "reason": "missing_username"})
                return
            if not server_database_user_exists(username):
                self.send_json(404, {"ok": False, "error": "Tài khoản không tồn tại.", "reason": "nouser"})
                return
            # Added 2026-07-06: local-only browser test login for Codex DOM checks without normal password entry.
            session = create_auth_session(username)
            next_path = clean((query.get("next") or ["/lesson_vault"])[0]) or "/lesson_vault"
            if not next_path.startswith("/") or next_path.startswith("//"):
                next_path = "/lesson_vault"
            self.send_response(302)
            self.send_header("Location", next_path)
            self.send_header(
                "Set-Cookie",
                f"{AUTH_COOKIE_NAME}={session.get('token', '')}; Max-Age=86400; Path=/; SameSite=Lax",
            )
            self.send_header("Cache-Control", "no-store, no-cache, max-age=0")
            self.safe_finish_response()
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/me":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = session.get("username", "")
        chat_mark_online(username)
        touch_user_activity_seen(username)
        self.send_json(200, auth_me_payload(username, include_rewards=True))
        return
    if path == "/auth/admin-users":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        username = normalize_username(session.get("username", ""))
        if not is_admin_user(username):
            self.send_json(403, {"ok": False, "error": "Only admins can view this list."})
            return
        chat_mark_online(username)
        picker_query = parse_qs(parsed.query)
        if clean((picker_query.get("picker") or [""])[0]).lower() in {"1", "true", "yes"}:
            picker = dashboard_admin_user_picker_payload(
                (picker_query.get("search") or picker_query.get("q") or [""])[0],
                int((picker_query.get("page") or ["1"])[0] or 1),
                int((picker_query.get("page_size") or ["10"])[0] or 10),
            )
            self.send_json(200, {"ok": True, **picker})
            return
        self.send_json(200, {"ok": True, **dashboard_admin_payload()})
        return
    if path == "/server-data/vault-folders":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        viewer = normalize_username(session.get("username", ""))
        query = parse_qs(parsed.query)
        target = normalize_username((query.get("user") or query.get("target_user") or [viewer])[0]) or viewer
        if target != viewer and not is_admin_user(viewer):
            self.send_json(403, {"ok": False, "error": "Only admins can view another user's Vault folders."})
            return
        rows = server_database_vault_folder_rows(target)
        self.send_json(200, {"ok": True, "username": target, "folders": rows, "vault_revision": server_database_vault_revision(target)})
        return
    if path == "/server-data/vault-revision":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        viewer = normalize_username(session.get("username", ""))
        query = parse_qs(parsed.query)
        target = normalize_username((query.get("user") or query.get("target_user") or [viewer])[0]) or viewer
        if target != viewer and not is_admin_user(viewer):
            self.send_json(403, {"ok": False, "error": "Only admins can view another user's Vault revision."})
            return
        self.send_json(200, {"ok": True, "username": target, "vault_revision": server_database_vault_revision(target)})
        return
    if path == "/profile/public":
        session = self.auth_session()
        if not session:
            self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
            return
        query = parse_qs(parsed.query)
        username = normalize_username((query.get("username") or query.get("user") or [session.get("username", "")])[0])
        if not username:
            self.send_json(400, {"ok": False, "error": "Missing user."})
            return
        self.send_json(200, {"ok": True, "profile": public_user_profile_card(username)})
        return
    if path == "/inventory":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            compact_response = clean((query.get("response") or [""])[0]).lower() == "compact-v1"
            self.send_json(200, {
                "ok": True,
                "response_schema": "inventory-compact-v1" if compact_response else "inventory-full-v1",
                **public_inventory(session.get("username", ""), compact=compact_response),
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/auth/pending":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Chi may server duoc duyet dang ky."})
            return
        self.send_json(200, {"ok": True, "pending": list_pending_registrations(), "password_resets": list_pending_password_resets()})
        return
    if path in ("/dashboard/login-log", "/dashboard/learning-log"):
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Dashboard logs are only available on the server machine."})
            return
        query = parse_qs(parsed.query)
        day = clean((query.get("date") or [""])[0])[:10]
        search = clean((query.get("search") or [""])[0])[:120]
        try:
            limit = int(clean((query.get("limit") or ["800"])[0]) or 800)
        except Exception:
            limit = 800
        log_path = LOGIN_LOG_FILE if path.endswith("login-log") else LEARNING_LOG_FILE
        rows = read_jsonl_log(log_path, limit=limit, date=day, search=search)
        if path.endswith("login-log"):
            rows = (rows + active_session_login_rows(day, search))
            rows.sort(key=lambda item: clean(item.get("at", "")), reverse=True)
            rows = rows[: max(1, min(5000, limit))]
        self.send_json(200, {"ok": True, "date": day, "search": search, "rows": rows, "retention_days": 31})
        return
    if path == "/dashboard/admins":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Admin settings are only available on the server machine."})
            return
        self.send_json(200, {"ok": True, **dashboard_admin_payload()})
        return
    if path == "/dashboard/email-routing":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Email Routing is only available on the server machine."})
            return
        self.send_html(200, cloudflare_email_routing_admin_page())
        return
    if path == "/dashboard/email-routing/state":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Email Routing is only available on the server machine."})
            return
        query = parse_qs(parsed.query)
        live = truthy((query.get("live") or ["false"])[0], False)
        self.send_json(200, {"ok": True, **cloudflare_email_routing_public_config(live=live)})
        return
    if path == "/dashboard/email-routing/worker.js":
        if not self.is_local_admin_request():
            self.send_json(403, {"ok": False, "error": "Email Routing worker script is only available on the server machine."})
            return
        query = parse_qs(parsed.query)
        endpoint = clean((query.get("endpoint") or [""])[0])
        data = cloudflare_email_routing_worker_script(endpoint).encode("utf-8")
        self.send_bytes(200, data, "text/javascript; charset=utf-8", cache_control="private, no-store, no-cache, max-age=0")
        return
    if path == "/server-data/manifest-status":
        try:
            session = self.auth_session()
            if not session and not self.is_local_admin_request():
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            manifest = get_server_data_manifest()
            folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
            self.send_json(200, {
                "ok": True,
                "updated_at": clean(manifest.get("updated_at", "")),
                "signature": server_data_tree_runtime_revision(
                    normalize_username(session.get("username", "")) if session else "",
                    bool((session and is_admin_user(session.get("username", ""))) or self.is_local_admin_request()),
                    manifest,
                ),
                "integrity_signature": clean(manifest.get("signature", "")),
                "folder_count": len(folders),
                "entry_count": sum(len(rows) for rows in folders.values() if isinstance(rows, list)),
                "build_hold": server_data_manifest_build_hold_status(),
            })
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/list":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            task_owner = clean((query.get("task_owner") or query.get("owner") or [""])[0])
            fresh = truthy((query.get("fresh") or query.get("force") or [""])[0], False)
            defer_task_board = truthy((query.get("defer_task_board") or query.get("deferTaskBoard") or [""])[0], False)
            include_space_task = truthy((query.get("include_space_task") or query.get("includeSpaceTask") or [""])[0], False)
            username = session.get("username", "")
            payload = dict(list_server_data(
                rel_path,
                username,
                admin=is_admin_user(username),
                task_owner_hint=task_owner,
                fresh=fresh,
                include_task_board=not defer_task_board,
                include_space_task=include_space_task,
            ))
            server_timing = clean(payload.pop("_server_timing", ""))
            response_bytes = payload.pop("_response_bytes", None)
            response_etag = clean(payload.pop("_response_etag", ""))
            response_cache_hit = bool(payload.pop("_response_cache_hit", False))
            if isinstance(response_bytes, bytes):
                self.send_bytes(
                    200,
                    response_bytes,
                    "application/json; charset=utf-8",
                    cache_control="private, max-age=0, must-revalidate",
                    etag=response_etag,
                    extra_headers={
                        "Server-Timing": server_timing,
                        "X-Future-Cache-Hit": "server-data-list-bytes" if response_cache_hit else "server-data-list-build",
                    },
                )
            else:
                self.send_json(200, payload, extra_headers={"Server-Timing": server_timing} if server_timing else None)
        except Exception as exc:
            stt_debug_log(
                "server_data_list_request_failed",
                user=normalize_username((locals().get("session") or {}).get("username", "")),
                path=clean_path_value(locals().get("rel_path", "")),
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/last-file":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            row = lesson_last_file_response_cache_row(username)
            self.send_bytes(
                200,
                row.get("bytes", b""),
                "application/json; charset=utf-8",
                cache_control="private, max-age=0, must-revalidate",
                etag=clean(row.get("etag", "")),
                extra_headers={"X-Future-Cache-Hit": "last-file-bytes" if row.get("cache_hit") else "last-file-build"},
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/item-study":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            if not rel_path:
                self.send_json(400, {"ok": False, "error": "Thieu path."})
                return
            username = normalize_username(session.get("username", ""))
            admin_view = is_admin_user(username)
            task_owner = normalize_username((query.get("task_owner") or query.get("owner") or [""])[0]) if admin_view else ""
            if task_owner and (not learner_user_exists(task_owner) or not (SERVER_DATA_ROOT / task_owner).is_dir()):
                task_owner = ""
            study_user = task_owner or lesson_task_owner_for_path(rel_path, username, admin=admin_view) or username
            aliases = [rel_path]
            for alias in query.get("alias") or query.get("aliases") or []:
                alias = clean_path_value(alias)
                if alias:
                    aliases.append(alias)
            target = safe_server_data_path(rel_path, username, admin=admin_view)
            effective_target = server_data_effective_file_path(target, username=username, admin=admin_view)
            study_path = clean_path_value(server_data_relative(effective_target)) or rel_path
            if study_path:
                aliases.append(study_path)
            progress_index = lesson_progress_record_index(study_user)
            time_index = lesson_time_state_index(study_user)
            study = summarize_lesson_study(
                effective_target,
                study_user,
                progress_index,
                time_index,
                include_admin=admin_view,
                progress_relative_path=study_path,
                path_is_effective=True,
                progress_relative_paths=aliases,
            )
            viewer_study = {}
            viewer_progress_user = username if admin_view and study_user and normalize_username(username) != normalize_username(study_user) else ""
            if viewer_progress_user:
                viewer_study = summarize_lesson_study(
                    effective_target,
                    viewer_progress_user,
                    lesson_progress_record_index(viewer_progress_user),
                    lesson_time_state_index(viewer_progress_user),
                    include_admin=True,
                    progress_relative_path=study_path,
                    path_is_effective=True,
                    progress_relative_paths=aliases,
                )
            self.send_json(200, {
                "ok": True,
                "username": username,
                "task_owner": study_user,
                "path": rel_path,
                "effective_path": study_path,
                "study": study,
                "viewer_study": viewer_study,
            })
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-tasks/status":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            query = parse_qs(parsed.query)
            target_user = normalize_username((query.get("user") or [""])[0])
            if target_user and target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can view another user's tasks."})
                return
            task_user = target_user or username
            status = space_task_payload_refresh_status(task_user, username, include_admin=is_admin_user(username))
            self.send_json(200, {"ok": True, "task_owner": task_user, **status})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-tasks":
        try:
            lesson_tasks_request_started = time.perf_counter()
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            query = parse_qs(parsed.query)
            target_user = normalize_username((query.get("user") or [""])[0])
            if target_user and target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can view another user's tasks."})
                return
            task_user = target_user or username
            viewer_is_admin = is_admin_user(username)
            row = get_or_build_lesson_tasks_response_cache_row(task_user, username, viewer_is_admin)
            request_ms = (time.perf_counter() - lesson_tasks_request_started) * 1000
            timing_parts = [f"lesson_tasks_total;dur={request_ms:.3f}"]
            if not row.get("cache_hit"):
                for timing_name, timing_value in (row.get("timing") or {}).items():
                    timing_parts.append(f"lesson_tasks_{clean(timing_name)};dur={float(timing_value or 0.0):.3f}")
            self.send_bytes(
                200,
                row.get("bytes", b""),
                "application/json; charset=utf-8",
                cache_control="private, max-age=0, must-revalidate",
                etag=clean(row.get("etag", "")),
                extra_headers={
                    "X-Future-Cache-Hit": "lesson-tasks-bytes" if row.get("cache_hit") else "lesson-tasks-build",
                    "Server-Timing": ", ".join(timing_parts),
                },
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/lesson-task-notices":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            query = parse_qs(parsed.query)
            target_user = normalize_username((query.get("user") or [""])[0])
            immediate_after_raw = (query.get("immediate_after") or query.get("instant_after") or [None])[0]
            if target_user and target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can view another user's task notices."})
                return
            notice_user = target_user or username
            immediate_payload = {}
            if immediate_after_raw is not None:
                try:
                    immediate_after = int(immediate_after_raw or 0)
                except Exception:
                    immediate_after = 0
                immediate_payload = lesson_task_notice_immediate_payload(notice_user, immediate_after)
            self.send_json(200, {
                "ok": True,
                "task_owner": notice_user,
                "task_notices": lesson_task_notices_for_user(notice_user, admin_view=bool(is_admin_user(username) and username != notice_user)),
                "admin": is_admin_user(username),
                **immediate_payload,
            })
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/file":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            username = session.get("username", "")
            admin_view = is_admin_user(username)
            target = safe_server_data_path(rel_path, username, admin=admin_view)
            target = server_data_effective_file_path(target, username=username, admin=admin_view)
            suffix = target.suffix.lower()
            if suffix not in {".space_w", ".space_v", ".space_b", ".space_q", ".space_p", ".space_s", ".space_l", ".pdf", ".txt"}:
                raise RuntimeError("Chi duoc nap file Space_W/Space_V/Space_B/Space_Q/Space_P/TXT trong C:\\server data.")
            if suffix == ".space_v":
                qmdict_sig = qmdict_source_signature()
                qmdict_mtime_ns = int(qmdict_sig.get("mtime_ns", 0) or 0)
                qmdict_size = int(qmdict_sig.get("size", -1) or -1)
                etag = render_variant_etag(
                    target,
                    "server-data-space-v-qmdict",
                    qmdict_mtime_ns,
                    qmdict_size,
                )
                request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
                if etag and (etag in request_etags or "*" in request_etags):
                    # Added 2026-07-20: avoid decoding/hydrating Space_V when the client already owns this exact dependency revision.
                    self.send_bytes(
                        200,
                        b"",
                        "text/plain; charset=utf-8",
                        cache_control="private, no-cache, max-age=0, must-revalidate",
                        etag=etag,
                        extra_headers={"X-Future-Cache-Hit": "file-etag-preflight"},
                    )
                    return
                payload_bytes, _hydrate_meta = cached_space_v_qmdict_file_bytes(target)
                self.send_bytes(
                    200,
                    payload_bytes,
                    "text/plain; charset=utf-8",
                    cache_control="private, no-cache, max-age=0, must-revalidate",
                    etag=etag,
                )
                return
            etag = public_file_etag(target, "server-data-file")
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag and (etag in request_etags or "*" in request_etags):
                self.send_bytes(
                    200,
                    b"",
                    "application/pdf" if suffix == ".pdf" else "text/plain; charset=utf-8",
                    cache_control="private, no-cache, max-age=0, must-revalidate",
                    accept_ranges=suffix == ".pdf",
                    etag=etag,
                    extra_headers={"X-Future-Cache-Hit": "file-etag-preflight"},
                )
                return
            self.send_bytes(
                200,
                cached_server_data_file_bytes(target),
                "application/pdf" if suffix == ".pdf" else "text/plain; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                accept_ranges=suffix == ".pdf",
                etag=etag,
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/character-asset":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            asset_name = Path(clean((query.get("name") or ["redgirl.gif"])[0])).name
            allowed_assets = {"redgirl.gif": "image/gif", "redgirl_fast.gif": "image/gif", "Amber.gif": "image/gif"}
            content_type = allowed_assets.get(asset_name)
            if not content_type:
                self.send_json(404, {"ok": False, "error": "Character asset not found."})
                return
            asset_root = (SERVER_DATA_ROOT / "Picture" / "Character").resolve()
            target = (asset_root / asset_name).resolve()
            try:
                target.relative_to(asset_root)
            except Exception:
                self.send_json(404, {"ok": False, "error": "Character asset not found."})
                return
            if not target.is_file():
                self.send_json(404, {"ok": False, "error": "Character asset not found."})
                return
            self.send_bytes(
                200,
                cached_server_data_file_bytes(target),
                content_type,
                cache_control="private, max-age=86400",
                etag=public_file_etag(target, "space-pdf-character-asset"),
            )
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/info":
        try:
            started = time.perf_counter()
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            warm_page = (query.get("warm_page") or query.get("page") or ["1"])[0]
            warm_scale = (query.get("warm_scale") or query.get("scale") or ["3.2"])[0]
            defer_render = truthy((query.get("defer_render") or query.get("deferRender") or ["0"])[0], False)
            quick_info = truthy((query.get("quick") or query.get("fast") or ["0"])[0], False)
            username = session.get("username", "")
            lesson_id = clean((query.get("lesson_id") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or [""])[0])
            asset_target = validated_lesson_asset_path(username, lesson_id, lesson_handle, "pdf") if lesson_id and lesson_handle else None
            handle_row = validate_lesson_handle(username, lesson_id, lesson_handle) if asset_target is not None else {}
            metadata_alias_target = None
            if handle_row:
                legacy_metadata_path = clean_path_value(handle_row.get("legacy_source_path", ""))
                if legacy_metadata_path:
                    metadata_alias_target = safe_pdf_server_data_path(legacy_metadata_path, username, admin=is_admin_user(username))
            info = pdf_document_quick_info(
                rel_path,
                username,
                admin=is_admin_user(username),
                trusted_target=asset_target,
                metadata_alias_target=metadata_alias_target,
            ) if quick_info else pdf_document_info(
                rel_path,
                username,
                admin=is_admin_user(username),
                trusted_target=asset_target,
                metadata_alias_target=metadata_alias_target,
            )
            if asset_target is not None:
                info = {**info, "name": clean(handle_row.get("display_name", "")) or Path(clean(handle_row.get("display_path", ""))).name,
                        "title": clean(handle_row.get("title", "")) or Path(clean(handle_row.get("display_path", ""))).stem,
                        "display_path": clean_path_value(handle_row.get("display_path", ""))}
            chat_mark_online(username)
            touch_user_activity_seen(username)
            mark_user_activity(username, {
                "status": "Opening PDF",
                "space": "Space_PDF",
                "path": rel_path,
            })
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            stt_debug_log("pdf_info_response", path=rel_path, username=username, ms=elapsed_ms, cache_items=pdf_picture_metadata_status().get("items", 0))
            self.send_json(200, {"ok": True, "pdf": info})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/file":
        try:
            started = time.perf_counter()
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            username = session.get("username", "")
            admin_run = is_admin_user(username)
            lesson_id = clean((query.get("lesson_id") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or [""])[0])
            target = validated_lesson_asset_path(username, lesson_id, lesson_handle, "pdf") if lesson_id and lesson_handle else safe_pdf_server_data_path(rel_path, username, admin=admin_run)
            handle_row = validate_lesson_handle(username, lesson_id, lesson_handle) if lesson_id and lesson_handle else {}
            pdf_etag = public_file_etag(target, "pdf-file")
            stat = target.stat()
            file_size = int(stat.st_size)
            content_disposition = inline_content_disposition_filename(clean(handle_row.get("display_name", "")) or target.name, "document.pdf")
            encoded_relative_path = quote(server_data_relative(target), safe="/")
            range_header = clean(self.headers.get("Range", ""))
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if not range_header and pdf_etag and (pdf_etag in request_etags or "*" in request_etags):
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                self.send_response(304)
                self.send_header("ETag", pdf_etag)
                self.send_header("Cache-Control", "private, max-age=86400")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("X-Future-File-Bytes", str(file_size))
                self.send_header("X-Future-File-Mtime", str(int(stat.st_mtime)))
                self.send_header("X-Future-File-Path", encoded_relative_path)
                self.send_header("Server-Timing", f"future-pdf-file;dur={elapsed_ms}")
                self.safe_finish_response()
                return

            status_code = 200
            start_byte = 0
            end_byte = max(file_size - 1, 0)
            content_length = file_size
            if range_header.startswith("bytes="):
                match = re.match(r"^bytes=(\d*)-(\d*)$", range_header)
                if not match or file_size <= 0:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "private, max-age=86400")
                    self.safe_finish_response()
                    return
                start_text, end_text = match.groups()
                if not start_text and not end_text:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "private, max-age=86400")
                    self.safe_finish_response()
                    return
                if start_text:
                    start_byte = int(start_text)
                    end_byte = int(end_text) if end_text else file_size - 1
                else:
                    suffix_length = int(end_text)
                    if suffix_length <= 0:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Cache-Control", "private, max-age=86400")
                        self.safe_finish_response()
                        return
                    start_byte = max(file_size - suffix_length, 0)
                    end_byte = file_size - 1
                if start_byte >= file_size or end_byte < start_byte:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "private, max-age=86400")
                    self.safe_finish_response()
                    return
                end_byte = min(end_byte, file_size - 1)
                content_length = end_byte - start_byte + 1
                status_code = 206

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(content_length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "private, max-age=86400")
            self.send_header("Content-Disposition", content_disposition)
            if pdf_etag:
                self.send_header("ETag", pdf_etag)
            if status_code == 206:
                self.send_header("Content-Range", f"bytes {start_byte}-{end_byte}/{file_size}")
            self.send_header("X-Future-File-Bytes", str(file_size))
            self.send_header("X-Future-File-Mtime", str(int(stat.st_mtime)))
            self.send_header("X-Future-File-Path", encoded_relative_path)
            self.send_header("Server-Timing", f"future-pdf-file;dur={elapsed_ms}")
            if not self.safe_finish_response():
                return
            sent = 0
            with target.open("rb") as file_in:
                if start_byte:
                    file_in.seek(start_byte)
                remaining = content_length
                while remaining > 0:
                    # Keep PDF Range responses observable as a smooth stream to XHR progress.
                    chunk = file_in.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                        break
                    except OSError as write_exc:
                        if getattr(write_exc, "winerror", None) in {10053, 10054, 10058}:
                            break
                        raise
                    sent += len(chunk)
                    remaining -= len(chunk)
                    self.wfile.flush()
            stt_debug_log("pdf_file_response", path=rel_path, username=username, bytes=sent, total=file_size, range=range_header, status=status_code, ms=elapsed_ms)
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/pdf/prewarm":
        self.send_json(410, {"ok": False, "error": "Server PDF page prewarm is disabled. Download the PDF file and render locally."})
        return
    if path == "/pdf/page":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            zoom = (query.get("scale") or query.get("zoom") or ["2.0"])[0]
            username = session.get("username", "")
            admin_run = is_admin_user(username)
            lesson_id = clean((query.get("lesson_id") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or [""])[0])
            asset_target = validated_lesson_asset_path(username, lesson_id, lesson_handle, "pdf") if lesson_id and lesson_handle else None
            handle_row = validate_lesson_handle(username, lesson_id, lesson_handle) if asset_target is not None else {}
            payload, meta = render_pdf_page_png(rel_path, username, admin=admin_run, page=page, zoom=zoom, trusted_target=asset_target)
            try:
                pdf_target = asset_target or safe_pdf_server_data_path(clean(meta.get("path", rel_path)), username, admin=admin_run)
                pdf_etag = render_variant_etag(pdf_target, "pdf-page", int(meta.get("page", page) or 1), "png")
            except Exception:
                pdf_etag = ""
            pdf_display_name = f"{Path(clean(handle_row.get('display_name', '')) or clean(meta.get('name', 'pdf'))).stem}-p{int(meta.get('page', page) or 1)}.png"
            self.send_bytes(
                200,
                payload,
                "image/png",
                cache_control="private, max-age=1800",
                content_disposition=inline_content_disposition_filename(pdf_display_name, "pdf-page.png"),
                etag=pdf_etag,
                extra_headers={
                    "X-Future-Cache-Hit": "1" if meta.get("cache_hit") else "0",
                    "X-Future-Disk-Cache-Hit": "1" if meta.get("disk_cache_hit") else "0",
                    "X-Future-Payload-Bytes": str(len(payload)),
                    "X-Future-Render-Ms": str(int(meta.get("render_ms", 0) or 0)),
                },
            )
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/picture/info":
        try:
            started = time.perf_counter()
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            username = session.get("username", "")
            lesson_id = clean((query.get("lesson_id") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or [""])[0])
            asset_target = validated_lesson_asset_path(username, lesson_id, lesson_handle, "picture") if lesson_id and lesson_handle else None
            info = picture_document_info(rel_path, username, admin=is_admin_user(username), trusted_target=asset_target)
            if asset_target is not None:
                handle_row = validate_lesson_handle(username, lesson_id, lesson_handle)
                info = {**info, "name": clean(handle_row.get("display_name", "")) or Path(clean(handle_row.get("display_path", ""))).name,
                        "title": clean(handle_row.get("title", "")) or Path(clean(handle_row.get("display_path", ""))).stem,
                        "display_path": clean_path_value(handle_row.get("display_path", ""))}
            chat_mark_online(username)
            touch_user_activity_seen(username)
            mark_user_activity(username, {
                "status": "Opening Picture",
                "space": "Space_Picture",
                "path": rel_path,
            })
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            stt_debug_log("picture_info_response", path=rel_path, username=username, ms=elapsed_ms, cache_items=pdf_picture_metadata_status().get("items", 0))
            self.send_json(200, {"ok": True, "picture": info})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/picture/image":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            username = session.get("username", "")
            admin_run = is_admin_user(username)
            lesson_id = clean((query.get("lesson_id") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or [""])[0])
            asset_target = validated_lesson_asset_path(username, lesson_id, lesson_handle, "picture") if lesson_id and lesson_handle else None
            handle_row = validate_lesson_handle(username, lesson_id, lesson_handle) if asset_target is not None else {}
            payload, meta = render_picture_image_png(rel_path, username, admin=admin_run, page=page, trusted_target=asset_target)
            out_ext = ".png" if clean(meta.get("mime", "")) == "image/png" else ".jpg"
            try:
                picture_target = asset_target or safe_picture_server_data_path(clean(meta.get("path", rel_path)), username, admin=admin_run)
                picture_etag = render_variant_etag(picture_target, "picture-page", int(meta.get("page", page) or 1), out_ext.lstrip("."))
            except Exception:
                picture_etag = ""
            picture_display_name = f"{Path(clean(handle_row.get('display_name', '')) or clean(meta.get('name', 'picture'))).stem}{out_ext}"
            self.send_bytes(
                200,
                payload,
                clean(meta.get("mime", "")) or "image/jpeg",
                cache_control="private, max-age=1800",
                content_disposition=inline_content_disposition_filename(picture_display_name, f"picture{out_ext}"),
                etag=picture_etag,
                extra_headers={
                    "X-Future-Cache-Hit": "1" if meta.get("cache_hit") else "0",
                    "X-Future-Disk-Cache-Hit": "1" if meta.get("disk_cache_hit") else "0",
                    "X-Future-Payload-Bytes": str(len(payload)),
                },
            )
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            username = normalize_username(session.get("username", ""))
            target_user = normalize_username((query.get("user") or query.get("target_user") or [""])[0]) or username
            if target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can view another user's Space_PDF progress."})
                return
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Opening Space_PDF" if target_user == username else f"Opening Space_PDF as @{target_user}",
                "space": "Space_PDF",
                "path": rel_path,
                "identity": identity,
            })
            progress = read_space_pdf_progress(target_user, rel_path, identity, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": target_user, "viewer": username, "admin_view": target_user != username, "progress": progress})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/drawing":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            username = normalize_username(session.get("username", ""))
            target_user = normalize_username((query.get("user") or query.get("target_user") or [""])[0]) or username
            if target_user != username and not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can view another user's PDF drawing."})
                return
            # Added 2026-07-20: per-page side-data reads must not emit chat/activity writes.
            drawing = read_space_pdf_drawing(target_user, rel_path, identity, page, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": target_user, "viewer": username, "admin_view": target_user != username, "drawing": drawing})
        except PermissionError as exc:
            self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/audio-markers":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            mode = clean((query.get("mode") or ["pdf"])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            username = normalize_username(session.get("username", ""))
            # Added 2026-07-24: page side-data reads are read-only hot-path lookups.
            markers = read_space_pdf_shared_audio_markers(username, rel_path, page, mode, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": username, **markers})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-region-notices":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            mode = clean((query.get("mode") or ["pdf"])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            username = normalize_username(session.get("username", ""))
            # Added 2026-07-24: page side-data reads are read-only hot-path lookups.
            notices = read_space_pdf_ai_region_notices(username, rel_path, page, mode, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": username, **notices})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-region-questions":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            mode = clean((query.get("mode") or ["pdf"])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            username = normalize_username(session.get("username", ""))
            # Added 2026-07-24: page side-data reads are read-only hot-path lookups.
            questions = read_space_pdf_ai_region_questions(username, rel_path, page, mode, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": username, **questions})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-notice-image":
        try:
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            raw = str(rel_path or "").replace("\\", "/").strip("/")
            if not raw or any(part in ("", ".", "..") for part in raw.split("/")):
                raise RuntimeError("Duong dan anh AI notice khong hop le.")
            image_root = (ROOT / "Ai_notice_image").resolve()
            target = (image_root / raw).resolve()
            target.relative_to(image_root)
            if not target.is_file() or target.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
                raise RuntimeError("Anh AI notice khong ton tai.")
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_bytes(
                200,
                cached_public_file_bytes(target),
                content_type,
                cache_control="public, max-age=3600",
                etag=public_file_etag(target, "ai-notice-image"),
                extra_headers={"X-Content-Type-Options": "nosniff"},
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-notice-image-list":
        try:
            image_root = (ROOT / "Ai_notice_image").resolve()
            if not image_root.exists():
                self.send_json(200, {"ok": True, "images": []})
                return
            images = []
            for item in sorted(image_root.iterdir(), key=lambda p: p.name.lower()):
                if item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
                    images.append({
                        "name": item.name,
                        "path": item.name,
                        "url": f"/space-pdf/ai-notice-image?path={quote(item.name)}",
                    })
            self.send_json(200, {"ok": True, "images": images})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-pdf/ai-question-progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            page = (query.get("page") or ["1"])[0]
            mode = clean((query.get("mode") or ["pdf"])[0])
            region_key = clean((query.get("regionKey") or query.get("region_key") or [""])[0])
            lesson_id = clean((query.get("lesson_id") or query.get("lessonId") or [""])[0])
            lesson_handle = clean((query.get("lesson_handle") or query.get("lessonHandle") or [""])[0])
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            progress = read_space_pdf_ai_question_progress(username, rel_path, page, mode, region_key, lesson_id, lesson_handle)
            self.send_json(200, {"ok": True, "username": username, **progress})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            username = session.get("username", "")
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Opening Space_W",
                "space": "Space_W",
                "path": rel_path,
                "identity": identity,
            })
            progress = read_space_w_progress(username, rel_path, identity)
            preferences = read_user_preferences(username)
            etag = space_w_progress_etag(progress, preferences, username, rel_path, identity)
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag in request_etags or "*" in request_etags:
                self.send_bytes(
                    200,
                    b"",
                    "application/json; charset=utf-8",
                    cache_control="private, no-cache, max-age=0, must-revalidate",
                    etag=etag,
                    extra_headers={"X-Future-Cache-Hit": "space-w-progress-etag"},
                )
                return
            self.send_bytes(
                200,
                json_bytes({
                    "ok": True,
                    "username": username,
                    "progress": progress,
                    "preferences": preferences,
                }),
                "application/json; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=etag,
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/speak-skip/state":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            payload = {
                "path": clean_path_value((query.get("path") or [""])[0]),
                "identity": clean((query.get("identity") or [""])[0]),
                "nodeIndex": clean((query.get("nodeIndex") or query.get("node_index") or ["0"])[0]),
                "sessionId": clean((query.get("sessionId") or query.get("session_id") or [""])[0]),
            }
            username = session.get("username", "")
            chat_mark_online(username)
            request = get_space_w_speak_skip(username, payload)
            self.send_json(200, {"ok": True, "username": username, "request": request})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-w/speak-skip/list":
        manager = self.speak_skip_admin_session()
        if not manager:
            self.send_json(403, {"ok": False, "error": "Chi admin moi duoc xem Speak skip requests."})
            return
        try:
            query = parse_qs(parsed.query)
            status = clean((query.get("status") or ["pending"])[0]) or "pending"
            username = clean((query.get("username") or [""])[0])
            requests = list_space_w_speak_skip_requests(status, username)
            self.send_json(200, {
                "ok": True,
                "requests": requests,
                "pending_count": len([item for item in requests if clean(item.get("status", "")).lower() == "pending"]),
                "admin": manager.get("username", ""),
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-q/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            username = session.get("username", "")
            chat_mark_online(username)
            mark_user_activity(username, {
                "status": "Opening Space_Q",
                "space": "Space_Q",
                "path": rel_path,
                "identity": identity,
            })
            progress = read_space_q_progress(username, rel_path, identity)
            etag = space_q_progress_etag(progress, username, rel_path, identity)
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag in request_etags or "*" in request_etags:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, no-cache, max-age=0, must-revalidate")
                self.send_header("X-Future-Cache-Hit", "space-q-progress-etag")
                self.safe_finish_response()
                return
            summary = build_lesson_progress_summary(progress, "Space_Q", 0) if isinstance(progress, dict) else {}
            self.send_bytes(
                200,
                json_bytes({"ok": True, "username": username, "progress": progress, "summary": summary}),
                "application/json; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=etag,
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-v/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            username = session.get("username", "")
            chat_mark_online(username)
            progress = read_space_v_progress(username, rel_path, identity)
            etag = space_v_progress_etag(progress, username, rel_path, identity)
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag in request_etags or "*" in request_etags:
                self.send_bytes(
                    200,
                    b"",
                    "application/json; charset=utf-8",
                    cache_control="private, no-cache, max-age=0, must-revalidate",
                    etag=etag,
                    extra_headers={"X-Future-Cache-Hit": "space-v-progress-etag"},
                )
                return
            response_payload = {
                "ok": True,
                "username": username,
                "progress": progress,
                "summary": space_v_progress_summary_from_record(progress) if isinstance(progress, dict) else {},
            }
            self.send_bytes(
                200,
                json_bytes(response_payload),
                "application/json; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=etag,
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/space-p/progress":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            identity = clean((query.get("identity") or [""])[0])
            username = session.get("username", "")
            chat_mark_online(username)
            progress = read_space_p_progress(username, rel_path, identity)
            progress_space = normalize_paragraph_progress_space((progress or {}).get("space") or ((progress or {}).get("state") or {}).get("spaceMode"))
            mark_user_activity(username, {
                "status": f"Opening {progress_space}",
                "space": progress_space,
                "path": rel_path,
                "identity": identity,
            })
            etag = space_p_progress_etag(progress, username, rel_path, identity)
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag in request_etags or "*" in request_etags:
                self.send_bytes(
                    200,
                    b"",
                    "application/json; charset=utf-8",
                    cache_control="private, no-cache, max-age=0, must-revalidate",
                    etag=etag,
                    extra_headers={"X-Future-Cache-Hit": "space-p-progress-etag"},
                )
                return
            self.send_bytes(
                200,
                json_bytes({"ok": True, "username": username, "progress": progress}),
                "application/json; charset=utf-8",
                cache_control="private, no-cache, max-age=0, must-revalidate",
                etag=etag,
            )
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/registry":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            username = normalize_username(session.get("username", ""))
            fresh = truthy((query.get("fresh") or query.get("sync") or query.get("force") or ["0"])[0], False)
            row = get_or_build_vocab_registry_response_cache_row(username, fresh)
            self.send_bytes(
                200,
                row.get("bytes", b""),
                "application/json; charset=utf-8",
                cache_control="private, max-age=0, must-revalidate",
                etag="" if fresh else clean(row.get("etag", "")),
                extra_headers={"X-Future-Cache-Hit": "vocab-registry-bytes" if row.get("cache_hit") else "vocab-registry-build"},
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/image-file":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            word = lesson_task_notice_text((query.get("word") or [""])[0], limit=180)
            image_id = lesson_task_notice_text((query.get("image_id") or query.get("image") or [""])[0], limit=260)
            record = space_v_local_picture_asset(word, image_id=image_id)
            target = Path(clean(record.get("path", ""))) if record else None
            if not target or not target.is_file() or target.suffix.lower() not in SPACE_V_LOCAL_PICTURE_SUFFIX_PRIORITY:
                self.send_json(404, {"ok": False, "error": "Khong co anh local cho tu nay."})
                return
            stat = target.stat()
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if not content_type.startswith("image/"):
                self.send_json(415, {"ok": False, "error": "File picture khong dung dinh dang anh."})
                return
            revision = f"{int(stat.st_mtime_ns):x}-{int(stat.st_size):x}"
            etag = f'"space-v-picture-{hashlib.sha1((vocab_key(word) + "|" + clean(record.get("image_id", "")) + "|" + revision).encode("utf-8")).hexdigest()}"'
            request_etags = [item.strip() for item in clean(self.headers.get("If-None-Match", "")).split(",") if item.strip()]
            if etag in request_etags or "*" in request_etags:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
                self.safe_finish_response()
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(int(stat.st_size)))
            self.send_header("Cache-Control", "private, max-age=300, must-revalidate")
            self.send_header("ETag", etag)
            self.send_header("Content-Disposition", inline_content_disposition_filename(target.name, "vocabulary-picture" + target.suffix.lower()))
            if not self.safe_finish_response():
                return
            with target.open("rb") as file_in:
                while True:
                    chunk = file_in.read(1024 * 1024)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                        break
                    except OSError as write_exc:
                        if getattr(write_exc, "winerror", None) in {10053, 10054, 10058}:
                            break
                        raise
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/image":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            word = lesson_task_notice_text((query.get("word") or [""])[0], limit=180)
            if not word:
                self.send_json(400, {"ok": False, "error": "Missing word."})
                return
            lookup = qmdict_space_v_image_lookup(word)
            images = lookup.get("images") if isinstance(lookup, dict) and isinstance(lookup.get("images"), list) else []
            username = normalize_username(session.get("username", ""))
            selection = server_database_load_vocab_image_selection(username, vocab_key(word))
            selected_image_id = clean(selection.get("image_id", ""))
            selected_index = next((index for index, item in enumerate(images) if clean(item.get("id", "")).casefold() == selected_image_id.casefold()), 0) if images else -1
            image = images[selected_index] if selected_index >= 0 else {}
            record = space_v_local_picture_asset(word, image_id=clean(image.get("id", "")))
            self.send_json(200, {
                "ok": True,
                "word": word,
                "image": image if isinstance(image, dict) else {},
                "images": images,
                "selected_image_id": clean(image.get("id", "")) if isinstance(image, dict) else "",
                "selected_index": selected_index,
                "selection_revision": max(0, int(selection.get("server_revision", 0) or 0)),
                "asset": {
                    "asset_id": f"local-picture:{vocab_key(word)}:{clean(record.get('revision', ''))}",
                    "metadata_revision": clean(record.get("revision", "")),
                } if record else {},
                "pending": bool((lookup or {}).get("pending")),
                "retry_after_ms": max(0, int((lookup or {}).get("retry_after_ms", 0) or 0)),
            })
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/ai-agent/history":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            limit = space_w_int((query.get("limit") or ["80"])[0], 80)
            username = normalize_username(session.get("username", ""))
            self.send_json(200, {"ok": True, "history": list_ai_agent_history(username, limit)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/word-agent/history":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            word = lesson_task_notice_text((query.get("word") or query.get("term") or [""])[0], limit=180)
            limit = space_w_int((query.get("limit") or ["80"])[0], 80)
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            self.send_json(200, {
                "ok": True,
                "word": word,
                "word_key": word_agent_key(word),
                "history": list_word_agent_history(word, limit),
            })
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/npc-top":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            if not is_admin_user(username):
                self.send_json(403, {"ok": False, "error": "Only admins can switch to NPC racers."})
                return
            self.send_json(200, {"ok": True, "npcs": npc_top_public_roster()})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            limit = space_w_int((query.get("limit") or ["10"])[0], 10)
            requested_double_check = truthy((query.get("double_check") or query.get("verify") or ["0"])[0], False)
            force_check = truthy((query.get("force_check") or ["0"])[0], False)
            double_check = requested_double_check and force_check
            scope = clean((query.get("scope") or ["total"])[0]).lower()
            board_type = normalize_space_leaderboard_type((query.get("type") or query.get("board_type") or ["space_v"])[0]) or "space_v"
            record_vocab_leaderboard_view(session.get("username", ""), scope)
            username = normalize_username(session.get("username", ""))
            row = vocab_leaderboard_response_cache_row(limit, username, board_type, double_check)
            self.send_bytes(
                200,
                row.get("bytes", b""),
                "application/json; charset=utf-8",
                cache_control="private, max-age=0, must-revalidate",
                etag=clean(row.get("etag", "")),
                extra_headers={
                    "X-Future-Cache-Hit": "vocab-top-bytes" if row.get("cache_hit") else "vocab-top-build",
                    "X-Future-Top-Pending": "1" if row.get("pending") else "0",
                    "X-Future-Top-Revision": str(max(0, space_w_int(row.get("revision", 0), 0))),
                    "X-Future-Top-Published-Revision": str(max(0, space_w_int(row.get("published_revision", 0), 0))),
                    "X-Future-Top-Retry-Ms": str(max(0, space_w_int(row.get("retry_after_ms", 0), 0))),
                },
            )
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/leaderboard/chat":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            limit = space_w_int((query.get("limit") or ["100"])[0], 100)
            after_id = space_w_int((query.get("after_id") or query.get("after") or ["0"])[0], 0)
            chat_mark_online(session.get("username", ""))
            if after_id > 0:
                self.send_json(200, vocab_leaderboard_chat_sync(after_id, limit))
            else:
                rows = vocab_leaderboard_chat_rows(limit)
                self.send_json(200, {"ok": True, "changed": True, "reset": True, "revision": max([space_w_int(row.get("id", 0), 0) for row in rows] or [0]), "messages": rows})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/sync-main-offline":
        try:
            query = parse_qs(parsed.query)
            session = self.auth_session()
            session_username = normalize_username(session.get("username", "")) if session else ""
            allowed = self.is_local_admin_request() or (session and is_admin_user(session_username))
            if not allowed:
                self.send_json(403, {"ok": False, "error": "Only the server machine or an admin can sync main offline vocabulary."})
                return
            force = clean((query.get("force") or ["1"])[0]).lower() not in {"0", "false", "no", "off"}
            reason = clean((query.get("reason") or ["main-login"])[0]) or "main-login"
            target_user = normalize_username((query.get("user") or query.get("username") or [""])[0])
            if target_user:
                result = sync_main_vocabulary_for_user(target_user, force=force)
                self.send_json(200, {"ok": True, "queued": False, "running": False, "user": target_user, "result": result})
                return
            result = start_main_vocab_sync_all(force=force, reason=reason)
            with MAIN_VOCAB_SYNC_LOCK:
                last_result = MAIN_VOCAB_SYNC_ALL_STATE.get("last_result", {})
            self.send_json(202, {"ok": True, **result, "last_result": last_result})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
        return
    if path == "/vocab/build-status":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            job_id = clean((query.get("id") or query.get("job_id") or [""])[0])
            result = get_vocab_build_job(job_id, session.get("username", ""))
            self.send_json(200, {"ok": True, **result})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/state":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, (query.get("actor") or query.get("as") or [""])[0])
            chat_mark_online(username)
            touch_user_activity_seen(username)
            payload = shared_world_state_for_user(actor, real_username=username)
            if actor != username:
                payload["world"]["real_user"] = username
                payload["world"]["acting_as"] = actor
            self.send_json(200, {"ok": True, **payload})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/battle/state":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            username = normalize_username(session.get("username", ""))
            actor = resolve_admin_npc_actor(username, (query.get("actor") or query.get("as") or [""])[0])
            chat_mark_online(username)
            touch_user_activity_seen(username)
            payload = shared_world_battle_state_for_user(actor)
            if actor != username:
                payload["real_user"] = username
                payload["acting_as"] = actor
            self.send_json(200, {"ok": True, **payload})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/training/state":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            chat_mark_online(username)
            touch_user_activity_seen(username)
            payload = qm_city_training_state_for_user(username)
            self.send_json(200, {"ok": True, **payload})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/world/keyboard-pass":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            username = normalize_username(session.get("username", ""))
            with SHARED_WORLD_KEYBOARD_LOCK:
                state = load_shared_world_keyboard_state()
                keyboard_pass = shared_world_keyboard_pass_for_user(username, state)
            self.send_json(200, {"ok": True, "username": username, "keyboard_pass": keyboard_pass, "is_admin": is_admin_user(username)})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/game/state":
        try:
            session = self.auth_session()
            if not session:
                self.send_json(401, {"ok": False, "error": "Chua dang nhap."})
                return
            query = parse_qs(parsed.query)
            room_id = clean((query.get("room") or [""])[0])
            state = game_room_state(session.get("username", ""), room_id)
            self.send_json(200, {"ok": True, **state} if "rooms" in state else {"ok": True, "room": state})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/asset":
        try:
            query = parse_qs(parsed.query)
            rel_path = clean_path_value((query.get("path") or [""])[0])
            structure_response = rel_path.lower().startswith("structure/")
            accepts_gzip = "gzip" in clean(self.headers.get("Accept-Encoding", "")).lower()
            if structure_response and accepts_gzip:
                payload, structure_meta = structure_asset_gzip(rel_path)
                content_type = "application/json; charset=utf-8"
                extra_headers = {"Content-Encoding": "gzip", "Vary": "Accept-Encoding"}
                etag = f'"structure-{structure_meta.get("sha256", "")}"'
            else:
                payload, content_type = read_server_asset(rel_path)
                extra_headers = None
                etag = ""
            self.send_bytes(
                200,
                payload,
                content_type,
                cache_control="public, max-age=31536000, immutable",
                accept_ranges=content_type.startswith("audio/"),
                etag=etag,
                extra_headers=extra_headers,
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    if path == "/server-data/qm-sound-meta":
        try:
            query = parse_qs(parsed.query)
            descriptor = qm_sound_protocol_descriptor(
                meaning=clean((query.get("meaning") or [""])[0]),
                word=clean((query.get("word") or query.get("text") or [""])[0]),
                voice=clean((query.get("voice") or [""])[0]),
                rel_path=clean_path_value((query.get("path") or [""])[0]),
            )
            self.send_json(200, {
                "ok": True,
                "audio_epoch": descriptor["audio_epoch"],
                "file_rev": descriptor["file_revision"],
                "url": descriptor["url"],
            }, extra_headers={"Cache-Control": "no-store, no-cache, max-age=0, must-revalidate"})
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)}, extra_headers={"Cache-Control": "no-store"})
        return
    if path == "/server-data/qm-sound":
        try:
            query = parse_qs(parsed.query)
            requested_epoch = max(0, space_w_int((query.get("audio_epoch") or [0])[0], 0))
            requested_file_revision = clean((query.get("file_rev") or [""])[0])
            legacy_revision = clean((query.get("v") or query.get("revision") or [""])[0])
            requested_revision = requested_file_revision or legacy_revision
            current_epoch = global_audio_cache_epoch()
            revision_identity = ""
            meaning = clean((query.get("meaning") or [""])[0])
            word = clean((query.get("word") or query.get("text") or [""])[0])
            voice = clean((query.get("voice") or [""])[0])
            rel_path = clean_path_value((query.get("path") or [""])[0])
            if meaning:
                revision_identity = f"meaning:{meaning.lower()}"
            elif word:
                revision_identity = f"word:{word.lower()}:{voice.lower()}"
            elif rel_path:
                revision_identity = f"path:{rel_path.lower()}"
            immutable_cache_key = (
                f"{revision_identity}|{requested_epoch}|{requested_file_revision}"
                if revision_identity and requested_epoch and requested_file_revision and requested_file_revision.lower() not in {"missing", "0"}
                else ""
            )
            descriptor = qm_sound_protocol_descriptor(word=word, voice=voice, meaning=meaning, rel_path=rel_path)
            payload, content_type, current_revision = read_qmlearn_data_sound_file_revisioned(descriptor["path"])
            revision_matches = bool(
                requested_epoch == current_epoch
                and requested_file_revision
                and requested_file_revision == current_revision
            )
            etag_source = f"{revision_identity}|{current_epoch}|{current_revision}"
            etag = f'"qm-sound-{hashlib.sha1(etag_source.encode("utf-8")).hexdigest()}"' if current_revision else ""
            if revision_matches and immutable_cache_key:
                cached_response = qmlearn_http_audio_cache_get_current(
                    immutable_cache_key,
                    requested_revision,
                    current_revision,
                )
                if cached_response:
                    self.send_bytes(
                        200,
                        cached_response["data"],
                        cached_response.get("content_type", "audio/mpeg"),
                        cache_control="public, max-age=31536000, immutable",
                        accept_ranges=True,
                        etag=clean(cached_response.get("etag", etag)),
                        extra_headers={
                            "X-Future-Audio-Cache-Epoch": str(current_epoch),
                            "X-Future-Audio-Revision": current_revision,
                            "X-Future-Audio-Cache-Source": "server-ram",
                        },
                    )
                    return
                qmlearn_http_audio_cache_put(immutable_cache_key, payload, content_type, current_revision, etag)
            self.send_bytes(
                200,
                payload,
                content_type,
                cache_control="public, max-age=31536000, immutable" if revision_matches else "no-store, no-cache, max-age=0, must-revalidate",
                accept_ranges=content_type.startswith("audio/"),
                etag=etag if revision_matches else "",
                extra_headers={
                    "X-Future-Audio-Cache-Epoch": str(current_epoch),
                    "X-Future-Audio-Revision": current_revision,
                    "X-Future-Audio-Cache-Source": "server-file",
                } if current_revision else None,
            )
        except Exception as exc:
            self.send_json(404, {"ok": False, "error": str(exc)})
        return
    self.send_json(404, {"ok": False, "error": "Not found"})
