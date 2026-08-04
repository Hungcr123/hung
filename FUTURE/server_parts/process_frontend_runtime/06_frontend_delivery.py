# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

AUDIO_CACHE_EPOCH_FILE = SERVER_DATA_ROOT / "_future_audio_cache_epoch.json"
AUDIO_CACHE_EPOCH_LOCK = threading.RLock()
AUDIO_CACHE_EPOCH_VALUE = 0


# Added 2026-07-31: one durable monotonic epoch invalidates audio on every client, including offline clients.
def global_audio_cache_epoch(force_reload: bool = False) -> int:
    global AUDIO_CACHE_EPOCH_VALUE
    with AUDIO_CACHE_EPOCH_LOCK:
        if AUDIO_CACHE_EPOCH_VALUE > 0 and not force_reload:
            return AUDIO_CACHE_EPOCH_VALUE
        payload = {}
        document_row = None
        document_reader = globals().get("server_database_document_entry")
        try:
            document_row = document_reader(AUDIO_CACHE_EPOCH_FILE) if callable(document_reader) else None
            content = document_row.get("content") if isinstance(document_row, dict) else b""
            if isinstance(content, bytes):
                payload = json.loads(content.decode(clean(document_row.get("encoding")) or "utf-8-sig"))
        except Exception:
            payload = {}
        if not payload:
            try:
                if AUDIO_CACHE_EPOCH_FILE.is_file():
                    payload = json.loads(AUDIO_CACHE_EPOCH_FILE.read_text(encoding="utf-8-sig"))
            except Exception:
                payload = {}
        epoch = max(0, space_w_int(payload.get("global_audio_cache_epoch", 0), 0)) if isinstance(payload, dict) else 0
        if epoch <= 0:
            epoch = max(1, int(time.time() * 1000))
            atomic_write_json(AUDIO_CACHE_EPOCH_FILE, {
                "global_audio_cache_epoch": epoch,
                "updated_at": utc_timestamp(),
                "reason": "initialize",
            })
        elif not isinstance(document_row, dict):
            atomic_write_json(AUDIO_CACHE_EPOCH_FILE, {
                "global_audio_cache_epoch": epoch,
                "updated_at": clean(payload.get("updated_at", "")) or utc_timestamp(),
                "reason": clean(payload.get("reason", "")) or "postgres_migration",
            })
        AUDIO_CACHE_EPOCH_VALUE = epoch
        return epoch


# Added 2026-07-31: Dashboard Clear advances the durable epoch exactly once per command.
def bump_global_audio_cache_epoch(reason: object = "") -> int:
    global AUDIO_CACHE_EPOCH_VALUE
    with AUDIO_CACHE_EPOCH_LOCK:
        current = global_audio_cache_epoch()
        next_epoch = max(current + 1, int(time.time() * 1000))
        atomic_write_json(AUDIO_CACHE_EPOCH_FILE, {
            "global_audio_cache_epoch": next_epoch,
            "updated_at": utc_timestamp(),
            "reason": clean(reason) or "audio_cache_clear",
        })
        AUDIO_CACHE_EPOCH_VALUE = next_epoch
        for lock_name, cache_name in (
            ("QMLEARN_AUDIO_URL_CACHE_LOCK", "QMLEARN_AUDIO_URL_CACHE"),
            ("SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK", "SPACE_V_QMDICT_PAYLOAD_CACHE"),
            ("QMLEARN_HTTP_AUDIO_CACHE_LOCK", "QMLEARN_HTTP_AUDIO_CACHE"),
        ):
            lock = globals().get(lock_name)
            cache = globals().get(cache_name)
            if lock is not None and isinstance(cache, dict):
                try:
                    with lock:
                        cache.clear()
                except Exception:
                    pass
        return next_epoch

def cached_public_file_bytes(path: Path) -> bytes:
    target = Path(path).resolve()
    stat = target.stat()
    cache_key = str(target).lower()
    with FRONTEND_BYTES_CACHE_LOCK:
        row = FRONTEND_BYTES_CACHE.get(cache_key) if isinstance(FRONTEND_BYTES_CACHE.get(cache_key), dict) else {}
        if row.get("mtime_ns") == int(stat.st_mtime_ns) and row.get("size") == int(stat.st_size) and isinstance(row.get("data"), bytes):
            return row["data"]
    data = target.read_bytes()
    with FRONTEND_BYTES_CACHE_LOCK:
        FRONTEND_BYTES_CACHE[cache_key] = {
            "mtime_ns": int(stat.st_mtime_ns),
            "size": int(stat.st_size),
            "data": data,
        }
        if len(FRONTEND_BYTES_CACHE) > 8:
            for key in list(FRONTEND_BYTES_CACHE.keys())[:-8]:
                FRONTEND_BYTES_CACHE.pop(key, None)
    return data


def gzip_cache_get(cache_key: str, data: bytes) -> bytes:
    global HTTP_GZIP_CACHE_BYTES
    key = clean(cache_key)
    if not key:
        return b""
    with HTTP_GZIP_CACHE_LOCK:
        row = HTTP_GZIP_CACHE.get(key) if isinstance(HTTP_GZIP_CACHE.get(key), dict) else {}
        if row.get("size") == len(data) and isinstance(row.get("data"), bytes):
            row["at"] = time.time()
            return row["data"]
    compressed = gzip.compress(bytes(data or b""), compresslevel=6)
    with HTTP_GZIP_CACHE_LOCK:
        previous = HTTP_GZIP_CACHE.get(key) if isinstance(HTTP_GZIP_CACHE.get(key), dict) else {}
        if isinstance(previous.get("data"), bytes):
            HTTP_GZIP_CACHE_BYTES -= len(previous["data"])
        HTTP_GZIP_CACHE[key] = {"size": len(data), "data": compressed, "at": time.time()}
        HTTP_GZIP_CACHE_BYTES += len(compressed)
        while HTTP_GZIP_CACHE_BYTES > HTTP_GZIP_CACHE_MAX_BYTES and HTTP_GZIP_CACHE:
            oldest_key = min(HTTP_GZIP_CACHE, key=lambda item: float(HTTP_GZIP_CACHE[item].get("at", 0) or 0))
            oldest = HTTP_GZIP_CACHE.pop(oldest_key, {})
            if isinstance(oldest.get("data"), bytes):
                HTTP_GZIP_CACHE_BYTES -= len(oldest["data"])
    return compressed


def frontend_asset_path_from_route(route_path: str) -> Path:
    route = clean(route_path)
    if not route.startswith(FRONTEND_ASSET_ROUTE_PREFIX):
        raise RuntimeError("Invalid frontend asset route.")
    relative = unquote(route[len(FRONTEND_ASSET_ROUTE_PREFIX):]).replace("\\", "/")
    parts = [part for part in relative.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise RuntimeError("Invalid frontend asset path.")
    target = FRONTEND_ASSET_ROOT.joinpath(*parts).resolve()
    try:
        target.relative_to(FRONTEND_ASSET_ROOT)
    except Exception as exc:
        raise RuntimeError("Frontend asset path is outside FUTURE/web.") from exc
    if target.suffix.lower() not in FRONTEND_ASSET_CONTENT_TYPES:
        raise RuntimeError("Frontend asset type is not allowed.")
    if not target.is_file():
        raise RuntimeError("Frontend asset does not exist.")
    return target


def frontend_asset_content_type(path: Path) -> str:
    return FRONTEND_ASSET_CONTENT_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def frontend_known_asset_paths() -> list[Path]:
    return [
        FRONTEND_ASSET_ROOT / "future.css",
        FRONTEND_ASSET_ROOT / "future.js",
    ]


def frontend_file_fingerprint(path: Path, include_hash: bool = False) -> dict:
    target = Path(path).resolve()
    stat = target.stat()
    try:
        relative = target.relative_to(ROOT).as_posix()
    except Exception:
        relative = target.name
    row = {
        "path": relative,
        "mtime_ns": int(stat.st_mtime_ns),
        "size": int(stat.st_size),
    }
    if include_hash:
        row["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    return row


def frontend_delivery_signature(include_hash: bool = False) -> dict:
    rows = []
    for path in [PUBLIC_FRONTEND_PATH, *frontend_known_asset_paths()]:
        try:
            if Path(path).is_file():
                rows.append(frontend_file_fingerprint(path, include_hash=include_hash))
        except Exception:
            pass
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "version": f'W/"future-source-{digest[:24]}"',
        "digest": digest,
        "files": rows,
    }


def frontend_reload_state() -> dict:
    payload = {}
    try:
        if FRONTEND_RELOAD_FILE.is_file():
            payload = json.loads(FRONTEND_RELOAD_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        token = clean(payload.get("token", ""))
        if token:
            return {
                "token": token,
                "updated_at": clean(payload.get("updated_at", "")),
                "reason": clean(payload.get("reason", "")),
                "command": clean(payload.get("command", "")),
            }
    try:
        stat = PUBLIC_FRONTEND_PATH.stat()
        token = f"init-{int(stat.st_mtime_ns)}-{int(stat.st_size)}"
    except Exception:
        token = "init"
    return {"token": token, "updated_at": "", "reason": "", "command": ""}


def write_frontend_reload_state_file(payload: dict) -> None:
    # Added 2026-07-28: frontend reload tokens are runtime control state; in
    # PostgreSQL-only mode they must not route through the legacy SQLite document hook.
    FRONTEND_RELOAD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = FRONTEND_RELOAD_FILE.with_suffix(FRONTEND_RELOAD_FILE.suffix + ".tmp")
    data = json.dumps(payload if isinstance(payload, dict) else {}, ensure_ascii=False, indent=2)
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(data)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, FRONTEND_RELOAD_FILE)

def bump_frontend_reload_state(reason: object = "", command: object = "") -> dict:
    signature = frontend_delivery_signature()
    normalized_command = clean(command).lower()
    audio_cache_epoch = (
        bump_global_audio_cache_epoch(reason)
        if normalized_command == "clear-audio-cache"
        else global_audio_cache_epoch()
    )
    token = f"{int(time.time() * 1000)}-{clean(signature.get('digest', ''))[:12]}"
    payload = {
        "token": token,
        "updated_at": utc_timestamp(),
        "reason": clean(reason) or "manual_update",
        "command": normalized_command,
        "global_audio_cache_epoch": audio_cache_epoch,
        "frontend_version": clean(signature.get("version", "")),
    }
    write_frontend_reload_state_file(payload)
    with FRONTEND_BYTES_CACHE_LOCK:
        FRONTEND_BYTES_CACHE.clear()
    return payload


def future_html_bytes() -> bytes:
    path = PUBLIC_FRONTEND_PATH
    assert_public_file_allowed(path, allow_future_html=True)
    if not path.is_file():
        raise RuntimeError(f"Missing future.html at {path}")
    return cached_public_file_bytes(path)


def face1_html_bytes() -> bytes:
    path = PUBLIC_FACE1_PATH
    if not path.is_file():
        raise RuntimeError(f"Missing face 1.html at {path}")
    return cached_public_file_bytes(path)


def face2_html_bytes() -> bytes:
    path = PUBLIC_FACE2_PATH
    if not path.is_file():
        raise RuntimeError(f"Missing face 2.html at {path}")
    return cached_public_file_bytes(path)


def script_attrs_are_obfuscatable(attrs: str) -> bool:
    text = str(attrs or "")
    if re.search(r"\bsrc\s*=", text, flags=re.IGNORECASE):
        return False
    type_match = re.search(r"\btype\s*=\s*(['\"]?)([^'\"\s>]+)\1", text, flags=re.IGNORECASE)
    if not type_match:
        return True
    script_type = clean(type_match.group(2)).lower()
    return script_type in {"", "text/javascript", "application/javascript", "text/ecmascript", "application/ecmascript"}


def hosted_script_mangle_available() -> bool:
    return bool(shutil.which("node")) and (ROOT / "node_modules" / "terser").is_dir()


def mangle_hosted_javascript(source: str) -> tuple[str, bool]:
    raw = str(source or "")
    if not raw.strip() or not hosted_script_mangle_available():
        return raw, False
    node_script = r"""
const terser = require("terser");
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", async () => {
  try {
    const result = await terser.minify(input, {
      compress: false,
      mangle: { toplevel: true },
      format: { comments: false, beautify: false }
    });
    if (result.error) throw result.error;
    process.stdout.write(result.code || input);
  } catch (error) {
    console.error(error && error.stack ? error.stack : String(error));
    process.exit(2);
  }
});
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT),
            encoding="utf-8",
            errors="replace",
            timeout=HOSTED_SCRIPT_MANGLE_TIMEOUT_SECONDS,
            check=False,
            **subprocess_hidden_kwargs(),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout, True
        stt_debug_log("frontend_mangle_failed", returncode=result.returncode, stderr=clean(result.stderr)[-500:])
    except Exception as exc:
        stt_debug_log("frontend_mangle_exception", error=str(exc))
    return raw, False


def frontend_obfuscation_key_hash() -> str:
    settings = load_server_settings()
    configured = clean(settings.get("hosted_client_secret_hash", ""))
    if re.fullmatch(r"[0-9a-f]{64}", configured):
        return configured
    fallback = f"future-hosted-client|{ROOT}|{SERVER_DATA_ROOT}|{CODE_PREFIX}"
    return hashlib.sha256(fallback.encode("utf-8")).hexdigest()


def obfuscation_seed(key_hash: str, salt: str) -> int:
    value = f"{clean(key_hash)}|{clean(salt)}".encode("utf-8")
    seed = 2166136261
    for byte in value:
        seed ^= byte
        seed = (seed * 16777619) & 0xFFFFFFFF
    return seed or 0x9E3779B9


def xor_obfuscation_payload(payload: bytes, key_hash: str, salt: str) -> bytes:
    x = obfuscation_seed(key_hash, salt)
    out = bytearray(bytes(payload or b""))
    for index in range(len(out)):
        x ^= (x << 13) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        out[index] ^= x & 0xFF
    return bytes(out)


def obfuscate_script_block(attrs: str, source: str, key_hash: str) -> str:
    if not script_attrs_are_obfuscatable(attrs) or not str(source or "").strip():
        return f"<script{attrs}>{source}</script>"
    script_source, _mangled = mangle_hosted_javascript(str(source))
    salt = secrets.token_hex(12)
    encrypted = xor_obfuscation_payload(script_source.encode("utf-8"), key_hash, salt)
    encoded = base64.b64encode(encrypted).decode("ascii")
    chunks = [encoded[index:index + 24000] for index in range(0, len(encoded), 24000)]
    chunks_js = ",".join(json.dumps(chunk, separators=(",", ":")) for chunk in chunks)
    key_chunks = [key_hash[index:index + 8] for index in range(0, len(key_hash), 8)]
    key_js = ",".join(json.dumps(chunk, separators=(",", ":")) for chunk in key_chunks)
    salt_js = json.dumps(salt, separators=(",", ":"))
    return (
        f"<script{attrs}>"
        "(()=>{"
        f"const c=[{chunks_js}].join(\"\");"
        f"const k=[{key_js}].join(\"\");"
        f"const s={salt_js};"
        "let x=2166136261>>>0;"
        "const q=k+'|'+s;"
        "for(let i=0;i<q.length;i++){x^=q.charCodeAt(i)&255;x=Math.imul(x,16777619)>>>0}"
        "if(!x)x=0x9e3779b9;"
        "const b=atob(c);"
        "const a=new Uint8Array(b.length);"
        "for(let i=0;i<b.length;i++){"
        "x^=(x<<13);x>>>=0;x^=(x>>>17);x>>>=0;x^=(x<<5);x>>>=0;"
        "a[i]=b.charCodeAt(i)^(x&255)"
        "}"
        "(0,eval)(new TextDecoder(\"utf-8\").decode(a));"
        "})();"
        "</script>"
    )


def frontend_script_src(attrs: str) -> str:
    match = re.search(r"""\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", str(attrs or ""), flags=re.IGNORECASE)
    if not match:
        return ""
    return clean(next((item for item in match.groups() if item), ""))


def strip_frontend_script_src(attrs: str) -> str:
    text = str(attrs or "")
    text = re.sub(r"""\s*\bsrc\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", "", text, flags=re.IGNORECASE)
    return text


def frontend_link_href(attrs: str) -> str:
    match = re.search(r"""\bhref\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", str(attrs or ""), flags=re.IGNORECASE)
    if not match:
        return ""
    return clean(next((item for item in match.groups() if item), ""))


def frontend_link_is_stylesheet(attrs: str) -> bool:
    match = re.search(r"""\brel\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", str(attrs or ""), flags=re.IGNORECASE)
    if not match:
        return False
    rel = clean(next((item for item in match.groups() if item), "")).lower()
    return "stylesheet" in {part.strip() for part in rel.split()}


def inline_frontend_style_assets_for_hosted(html_text: str) -> str:
    def replace_link(match: re.Match) -> str:
        attrs = match.group(1) or ""
        if not frontend_link_is_stylesheet(attrs):
            return match.group(0)
        href = frontend_link_href(attrs)
        parsed_href = urlparse(href)
        route_path = parsed_href.path if parsed_href.scheme in ("", "http", "https") else ""
        if not route_path.startswith(FRONTEND_ASSET_ROUTE_PREFIX):
            return match.group(0)
        try:
            target = frontend_asset_path_from_route(route_path)
            if target.suffix.lower() != ".css":
                return match.group(0)
            css_text = target.read_text(encoding="utf-8-sig", errors="replace")
            return f"<style data-future-hosted-asset={json.dumps(route_path, ensure_ascii=False)}>\n{css_text}\n</style>"
        except Exception as exc:
            stt_debug_log("frontend_hosted_style_inline_failed", href=href, error=str(exc))
            return match.group(0)

    return re.sub(r"<link\b([^>]*)>", replace_link, str(html_text or ""), flags=re.IGNORECASE)


def inline_frontend_script_assets_for_hosted(html_text: str) -> str:
    def replace_script(match: re.Match) -> str:
        attrs = match.group(1) or ""
        source = match.group(2) or ""
        src = frontend_script_src(attrs)
        parsed_src = urlparse(src)
        route_path = parsed_src.path if parsed_src.scheme in ("", "http", "https") else ""
        if not route_path.startswith(FRONTEND_ASSET_ROUTE_PREFIX):
            return match.group(0)
        try:
            target = frontend_asset_path_from_route(route_path)
            if target.suffix.lower() != ".js":
                return match.group(0)
            return f"<script{strip_frontend_script_src(attrs)}>{target.read_text(encoding='utf-8-sig', errors='replace')}</script>"
        except Exception as exc:
            stt_debug_log("frontend_hosted_asset_inline_failed", src=src, error=str(exc))
            return f"<script{attrs}>{source}</script>"

    return re.sub(r"<script([^>]*)>([\s\S]*?)</script>", replace_script, str(html_text or ""), flags=re.IGNORECASE)


def build_obfuscated_frontend(html_text: str, key_hash: str) -> str:
    def replace_script(match: re.Match) -> str:
        return obfuscate_script_block(match.group(1) or "", match.group(2) or "", key_hash)

    prepared = inline_frontend_style_assets_for_hosted(str(html_text or ""))
    prepared = inline_frontend_script_assets_for_hosted(prepared)
    output = re.sub(r"<script([^>]*)>([\s\S]*?)</script>", replace_script, prepared, flags=re.IGNORECASE)
    return "<!-- Future hosted client build. Local source is kept on the server only. -->\n" + output


def future_hosted_html_bytes() -> bytes:
    path = PUBLIC_FRONTEND_PATH
    assert_public_file_allowed(path, allow_future_html=True)
    if not path.is_file():
        raise RuntimeError(f"Missing future.html at {path}")
    stat = path.stat()
    key_hash = frontend_obfuscation_key_hash()
    meta_base = {
        "version": OBFUSCATED_FRONTEND_VERSION,
        "source": str(path),
        "mtime_ns": int(stat.st_mtime_ns),
        "size": int(stat.st_size),
        "delivery": frontend_delivery_signature(include_hash=True),
        "key_hash": key_hash,
        "mangle": hosted_script_mangle_available(),
    }
    with FRONTEND_OBFUSCATION_LOCK:
        try:
            if OBFUSCATED_FRONTEND_PATH.is_file() and OBFUSCATED_FRONTEND_META_PATH.is_file():
                cached_meta = json.loads(OBFUSCATED_FRONTEND_META_PATH.read_text(encoding="utf-8-sig", errors="replace"))
                if isinstance(cached_meta, dict) and all(cached_meta.get(key) == value for key, value in meta_base.items()):
                    return cached_public_file_bytes(OBFUSCATED_FRONTEND_PATH)
        except Exception:
            pass
        source_text = path.read_text(encoding="utf-8-sig", errors="replace")
        meta = {
            **meta_base,
            "source_hash": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        }
        output = build_obfuscated_frontend(source_text, key_hash)
        data = output.encode("utf-8")
        try:
            RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
            tmp_html = OBFUSCATED_FRONTEND_PATH.with_name(f".{OBFUSCATED_FRONTEND_PATH.name}.{os.getpid()}.tmp")
            tmp_meta = OBFUSCATED_FRONTEND_META_PATH.with_name(f".{OBFUSCATED_FRONTEND_META_PATH.name}.{os.getpid()}.tmp")
            tmp_html.write_bytes(data)
            tmp_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_html.replace(OBFUSCATED_FRONTEND_PATH)
            tmp_meta.replace(OBFUSCATED_FRONTEND_META_PATH)
            with FRONTEND_BYTES_CACHE_LOCK:
                FRONTEND_BYTES_CACHE[str(OBFUSCATED_FRONTEND_PATH.resolve()).lower()] = {
                    "mtime_ns": int(OBFUSCATED_FRONTEND_PATH.stat().st_mtime_ns),
                    "size": int(OBFUSCATED_FRONTEND_PATH.stat().st_size),
                    "data": data,
                }
        except Exception as exc:
            stt_debug_log("frontend_obfuscation_cache_failed", error=str(exc))
        return data


def warm_frontend_delivery_cache_async(delay: float = 1.0) -> None:
    def _worker() -> None:
        try:
            if delay > 0:
                time.sleep(delay)
            local_payload = future_html_bytes()
            local_etag = public_file_etag(PUBLIC_FRONTEND_PATH, "future-local")
            if local_etag:
                gzip_cache_get(f"{local_etag}:gzip", local_payload)
            asset_bytes = 0
            for asset_path in frontend_known_asset_paths():
                try:
                    if not asset_path.is_file():
                        continue
                    payload = cached_public_file_bytes(asset_path)
                    asset_bytes += len(payload)
                    asset_etag = public_file_etag(asset_path, f"future-asset-{asset_path.suffix.lower().lstrip('.')}")
                    if asset_etag:
                        gzip_cache_get(f"{asset_etag}:gzip", payload)
                except Exception as exc:
                    stt_debug_log("frontend_asset_cache_warm_failed", path=str(asset_path), error=str(exc))
            hosted_payload = future_hosted_html_bytes()
            hosted_path = OBFUSCATED_FRONTEND_PATH if OBFUSCATED_FRONTEND_PATH.is_file() else PUBLIC_FRONTEND_PATH
            hosted_etag = public_file_etag(hosted_path, "future-hosted")
            if hosted_etag:
                gzip_cache_get(f"{hosted_etag}:gzip", hosted_payload)
            stt_debug_log("frontend_delivery_cache_warmed", local_bytes=len(local_payload), asset_bytes=asset_bytes, hosted_bytes=len(hosted_payload))
        except Exception as exc:
            stt_debug_log("frontend_delivery_cache_warm_failed", error=str(exc))

    threading.Thread(target=_worker, daemon=True, name="frontend-delivery-cache").start()
