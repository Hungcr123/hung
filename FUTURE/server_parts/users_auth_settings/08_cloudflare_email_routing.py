# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.

CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN = "qm-tech.io.vn"
CLOUDFLARE_EMAIL_ROUTING_API_BASE = "https://api.cloudflare.com/client/v4"
CLOUDFLARE_EMAIL_ROUTING_FILE = SERVER_DATA_ROOT / "_future_cloudflare_email_routing.json"
CLOUDFLARE_EMAIL_ROUTING_INBOX_FILE = SERVER_DATA_ROOT / "_future_cloudflare_email_routing_inbox.json"
CLOUDFLARE_EMAIL_ROUTING_LOCK = threading.RLock()
CLOUDFLARE_EMAIL_ROUTING_INBOX_LOCK = threading.RLock()
CLOUDFLARE_EMAIL_ROUTING_MAX_MESSAGES = 500


def cloudflare_email_routing_blank_config() -> dict:
    return {
        "version": 1,
        "domain": CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN,
        "account_id": "",
        "zone_id": "",
        "default_destination": "",
        "api_token": "",
        "inbound_secret": "",
        "aliases": [],
        "created_at": "",
        "updated_at": "",
    }


def cloudflare_email_routing_env(name: str) -> str:
    return clean(os.environ.get(name, "") or "").strip()


def cloudflare_email_routing_read_config() -> dict:
    base = cloudflare_email_routing_blank_config()
    with CLOUDFLARE_EMAIL_ROUTING_LOCK:
        data = server_database_read_document_json(CLOUDFLARE_EMAIL_ROUTING_FILE, {})
        if isinstance(data, dict):
            base.update({key: data.get(key, base.get(key)) for key in base})
    base["domain"] = normalize_email_routing_domain(base.get("domain", "")) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    base["aliases"] = normalize_email_routing_alias_rows(base.get("aliases", []), base["domain"])
    return base


def cloudflare_email_routing_effective_config() -> dict:
    config = cloudflare_email_routing_read_config()
    env_token = cloudflare_email_routing_env("FUTURE_CLOUDFLARE_API_TOKEN")
    env_account = cloudflare_email_routing_env("FUTURE_CLOUDFLARE_ACCOUNT_ID")
    env_zone = cloudflare_email_routing_env("FUTURE_CLOUDFLARE_ZONE_ID")
    env_domain = cloudflare_email_routing_env("FUTURE_EMAIL_ROUTING_DOMAIN")
    env_destination = cloudflare_email_routing_env("FUTURE_EMAIL_ROUTING_DEFAULT_DESTINATION")
    if env_account:
        config["account_id"] = env_account
    if env_zone:
        config["zone_id"] = env_zone
    if env_domain:
        config["domain"] = normalize_email_routing_domain(env_domain) or config["domain"]
    if env_destination:
        config["default_destination"] = normalize_email_routing_address(env_destination)
    if cloudflare_email_routing_env("FUTURE_EMAIL_ROUTING_INBOUND_SECRET"):
        config["inbound_secret"] = cloudflare_email_routing_env("FUTURE_EMAIL_ROUTING_INBOUND_SECRET")
    if env_token:
        config["api_token"] = env_token
        config["token_source"] = "env"
    elif clean(config.get("api_token", "")):
        config["token_source"] = "local"
    else:
        config["token_source"] = "missing"
    return config


def cloudflare_email_routing_write_config(config: dict) -> dict:
    current = cloudflare_email_routing_read_config()
    next_config = cloudflare_email_routing_blank_config()
    next_config.update(current)
    for key in ("domain", "account_id", "zone_id", "default_destination", "api_token", "inbound_secret", "aliases"):
        if key in config:
            next_config[key] = config.get(key)
    next_config["domain"] = normalize_email_routing_domain(next_config.get("domain", "")) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    next_config["account_id"] = clean(next_config.get("account_id", ""))[:120]
    next_config["zone_id"] = clean(next_config.get("zone_id", ""))[:120]
    next_config["default_destination"] = normalize_email_routing_address(next_config.get("default_destination", ""))
    next_config["api_token"] = clean(next_config.get("api_token", ""))
    next_config["inbound_secret"] = clean(next_config.get("inbound_secret", ""))
    next_config["aliases"] = normalize_email_routing_alias_rows(next_config.get("aliases", []), next_config["domain"])
    if not next_config.get("created_at"):
        next_config["created_at"] = utc_timestamp()
    next_config["updated_at"] = utc_timestamp()
    with CLOUDFLARE_EMAIL_ROUTING_LOCK:
        atomic_write_json(CLOUDFLARE_EMAIL_ROUTING_FILE, next_config, indent=2)
    return cloudflare_email_routing_read_config()


def cloudflare_email_routing_ensure_inbound_secret(config: dict | None = None) -> str:
    current = config or cloudflare_email_routing_read_config()
    secret = clean(current.get("inbound_secret", ""))
    if secret:
        return secret
    secret = secrets.token_urlsafe(32)
    cloudflare_email_routing_write_config({"inbound_secret": secret})
    return secret


def cloudflare_email_routing_verify_inbound_headers(headers) -> bool:
    try:
        expected = clean(cloudflare_email_routing_effective_config().get("inbound_secret", ""))
        if not expected:
            return False
        provided = clean(headers.get("X-Future-Email-Secret", ""))
        if not provided:
            auth = clean(headers.get("Authorization", ""))
            if auth.lower().startswith("bearer "):
                provided = clean(auth[7:])
        return bool(provided and hmac.compare_digest(provided, expected))
    except Exception:
        return False


def normalize_email_routing_domain(value: str) -> str:
    domain = clean(str(value or "")).strip().lower().rstrip(".")
    if domain.startswith("@"):
        domain = domain[1:]
    if not domain or len(domain) > 253 or "." not in domain:
        return ""
    if not re.match(r"^[a-z0-9.-]+$", domain):
        return ""
    labels = domain.split(".")
    for label in labels:
        if not label or len(label) > 63 or label.startswith("-") or label.endswith("-"):
            return ""
    return domain


def normalize_email_routing_address(value: str) -> str:
    address = clean(str(value or "")).strip().lower()
    if not address or len(address) > 90 or "@" not in address:
        return ""
    local, domain = address.rsplit("@", 1)
    if not local or len(local) > 64:
        return ""
    if not re.match(r"^[a-z0-9](?:[a-z0-9._%+\-]{0,62}[a-z0-9])?$", local):
        return ""
    if not normalize_email_routing_domain(domain):
        return ""
    return f"{local}@{normalize_email_routing_domain(domain)}"


def normalize_email_routing_alias_input(value: str, domain: str) -> str:
    target_domain = normalize_email_routing_domain(domain) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    raw = clean(str(value or "")).strip().lower()
    if not raw:
        raise RuntimeError("Nhap alias can tao, vi du admin hoac admin@domain.")
    if "@" in raw:
        local, raw_domain = raw.rsplit("@", 1)
        raw_domain = normalize_email_routing_domain(raw_domain)
        if raw_domain != target_domain:
            raise RuntimeError(f"Alias phai nam trong domain {target_domain}.")
    else:
        local = raw
    local = local.strip()
    if not local or len(local) > 64:
        raise RuntimeError("Alias khong hop le.")
    if not re.match(r"^[a-z0-9](?:[a-z0-9._%+\-]{0,62}[a-z0-9])?$", local):
        raise RuntimeError("Alias chi nen dung chu, so, dau cham, gach ngang, gach duoi, dau cong.")
    address = f"{local}@{target_domain}"
    if len(address) > 90:
        raise RuntimeError("Alias qua dai voi Cloudflare Email Routing.")
    return address


def normalize_email_routing_alias_rows(rows: object, domain: str) -> list[dict]:
    if not isinstance(rows, list):
        return []
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        address = normalize_email_routing_address(row.get("address", ""))
        if not address or address in seen:
            continue
        if domain and not address.endswith("@" + normalize_email_routing_domain(domain)):
            continue
        seen.add(address)
        out.append({
            "address": address,
            "destination": normalize_email_routing_address(row.get("destination", "")),
            "rule_id": clean(row.get("rule_id", ""))[:120],
            "name": clean(row.get("name", ""))[:256],
            "enabled": bool(row.get("enabled", True)),
            "created_at": clean(row.get("created_at", ""))[:80],
            "updated_at": clean(row.get("updated_at", ""))[:80],
        })
    out.sort(key=lambda item: item.get("address", ""))
    return out


def cloudflare_email_routing_text(value: object, limit: int = 12000) -> str:
    text = str(value or "").replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()[: max(0, int(limit or 0))]


def cloudflare_email_routing_decode_header(value: object) -> str:
    raw = clean(value)
    if not raw:
        return ""
    try:
        from email.header import decode_header, make_header
        return clean(str(make_header(decode_header(raw))))[:500]
    except Exception:
        return raw[:500]


def cloudflare_email_routing_extract_content(raw_text: object, limit: int = 12000) -> str:
    raw = cloudflare_email_routing_text(raw_text, max(limit * 2, limit))
    if not raw:
        return ""

    def tidy_message_text(value: str) -> str:
        text = str(value or "").replace("\u00a0", " ")
        code_match = re.search(r"(?is)(Enter this temporary verification code to continue:)\s*(\d{4,8})", text)
        if code_match:
            tail = ""
            tail_match = re.search(r"(?is)(If you were not trying to log in to OpenAI,.*?)(?:Best,\s*The OpenAI team|$)", text)
            if tail_match:
                tail = re.sub(r"\s+", " ", tail_match.group(1)).strip()
            parts = [code_match.group(1).strip(), code_match.group(2).strip()]
            if tail:
                parts.append(tail)
            return "\n\n".join(parts)[:limit]
        cleaned_lines = []
        for line in text.splitlines():
            clean_line = line.strip()
            if not clean_line:
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append("")
                continue
            lower = clean_line.lower()
            if (
                "{" in clean_line or "}" in clean_line
                or lower.startswith(("@font-face", "font-", "mso-", "-webkit-", "-ms-", "#", "."))
                or re.search(r"\b(width|height|padding|margin|font|line-height|border|color|background|display|src):", lower)
            ):
                continue
            cleaned_lines.append(clean_line)
        cleaned = "\n".join(cleaned_lines).strip()
        cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
        return cleaned[:limit]

    def html_to_text(value: str) -> str:
        html_text = str(value or "")
        html_text = re.sub(r"(?is)<(head|style|script|noscript|svg)[^>]*>.*?</\1>", " ", html_text)
        html_text = re.sub(r"(?is)<!--.*?-->", " ", html_text)
        html_text = re.sub(r"(?i)<br\s*/?>", "\n", html_text)
        html_text = re.sub(r"(?i)</(p|div|tr|table|h[1-6]|li)>", "\n", html_text)
        text = re.sub(r"<[^>]+>", " ", html_text)
        try:
            text = html.unescape(text)
        except Exception:
            pass
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return tidy_message_text(text.strip())

    try:
        message = BytesParser(policy=policy.default).parsebytes(raw.encode("utf-8", errors="replace"))
        plain_parts = []
        html_parts = []
        for part in message.walk() if message.is_multipart() else [message]:
            if part.get_content_disposition() == "attachment":
                continue
            content_type = clean(part.get_content_type()).lower()
            if content_type not in ("text/plain", "text/html"):
                continue
            try:
                content = str(part.get_content() or "")
            except Exception:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")
            content = cloudflare_email_routing_text(content, limit)
            if not content:
                continue
            if content_type == "text/plain":
                plain_parts.append(content)
            else:
                html_parts.append(html_to_text(content))
        selected = "\n\n".join(plain_parts or html_parts)
        selected = re.sub(r"[ \t]+", " ", selected).strip()
        if selected:
            return tidy_message_text(selected)[:limit]
    except Exception:
        pass
    lines = []
    in_body = False
    for line in raw.splitlines():
        if in_body:
            lines.append(line)
        elif not line.strip():
            in_body = True
    fallback = "\n".join(lines).strip() or raw
    if "Content-Type:" in fallback and re.search(r"(?m)^--[-_a-zA-Z0-9]+", fallback):
        return ""
    return tidy_message_text(fallback)[:limit]


def cloudflare_email_routing_content_needs_reparse(value: object) -> bool:
    text = str(value or "")
    if not text:
        return True
    lower = text.lower()
    return (
        "@font-face" in lower
        or "content-type:" in lower
        or "arc-seal:" in lower
        or "received:" in lower
        or "dkim-signature:" in lower
        or re.search(r"\b(font|padding|margin|mso-|line-height|border-collapse)\s*:", lower) is not None
    )


def cloudflare_email_routing_read_inbox() -> dict:
    base = {"version": 1, "messages": [], "updated_at": ""}
    with CLOUDFLARE_EMAIL_ROUTING_INBOX_LOCK:
        data = server_database_read_document_json(CLOUDFLARE_EMAIL_ROUTING_INBOX_FILE, {})
        if isinstance(data, dict):
            base.update({key: data.get(key, base.get(key)) for key in base})
    base["messages"] = normalize_email_routing_messages(base.get("messages", []))
    return base


def cloudflare_email_routing_write_inbox(messages: list[dict]) -> dict:
    payload = {
        "version": 1,
        "messages": normalize_email_routing_messages(messages)[:CLOUDFLARE_EMAIL_ROUTING_MAX_MESSAGES],
        "updated_at": utc_timestamp(),
    }
    with CLOUDFLARE_EMAIL_ROUTING_INBOX_LOCK:
        atomic_write_json(CLOUDFLARE_EMAIL_ROUTING_INBOX_FILE, payload, indent=2)
    return payload


def normalize_email_routing_messages(rows: object) -> list[dict]:
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        to_address = normalize_email_routing_address(row.get("to", ""))
        if not to_address:
            continue
        subject = cloudflare_email_routing_decode_header(row.get("subject", ""))
        text = cloudflare_email_routing_text(row.get("text", ""), 12000)
        content = cloudflare_email_routing_text(row.get("content", ""), 12000)
        if cloudflare_email_routing_content_needs_reparse(content):
            content = cloudflare_email_routing_extract_content(text, 12000)
        snippet = clean(content or row.get("snippet", "") or text)[:300]
        out.append({
            "id": clean(row.get("id", ""))[:120] or hashlib.sha256(json_bytes(row)).hexdigest()[:24],
            "received_at": clean(row.get("received_at", ""))[:80] or utc_timestamp(),
            "to": to_address,
            "from": normalize_email_routing_address(row.get("from", "")) or clean(row.get("from", ""))[:254],
            "subject": subject,
            "title": subject,
            "text": text,
            "content": content,
            "snippet": snippet,
            "source": clean(row.get("source", ""))[:80] or "webhook",
        })
    out.sort(key=lambda item: item.get("received_at", ""), reverse=True)
    return out[:CLOUDFLARE_EMAIL_ROUTING_MAX_MESSAGES]


def cloudflare_email_routing_store_message(payload: dict, headers=None) -> dict:
    config = cloudflare_email_routing_effective_config()
    domain = normalize_email_routing_domain(config.get("domain", "")) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    to_address = normalize_email_routing_alias_input(payload.get("to", "") or payload.get("recipient", ""), domain)
    from_address = normalize_email_routing_address(payload.get("from", "") or payload.get("sender", "")) or clean(payload.get("from", "") or payload.get("sender", ""))[:254]
    subject = cloudflare_email_routing_decode_header(payload.get("subject", ""))
    text = cloudflare_email_routing_text(payload.get("text", "") or payload.get("body", "") or payload.get("message", ""), 12000)
    content = cloudflare_email_routing_extract_content(text, 12000)
    message_id = clean(payload.get("id", "") or payload.get("message_id", ""))[:120]
    if not message_id:
        message_id = hashlib.sha256(json_bytes({
            "to": to_address,
            "from": from_address,
            "subject": subject,
            "text": text[:2000],
            "at": clean(payload.get("received_at", "")),
        })).hexdigest()[:24]
    message = {
        "id": message_id,
        "received_at": clean(payload.get("received_at", ""))[:80] or utc_timestamp(),
        "to": to_address,
        "from": from_address,
        "subject": subject,
        "title": subject,
        "text": text,
        "content": content,
        "snippet": clean(payload.get("snippet", "") or content or text)[:300],
        "source": clean(payload.get("source", ""))[:80] or "webhook",
    }
    inbox = cloudflare_email_routing_read_inbox()
    rows = [item for item in inbox.get("messages", []) if item.get("id") != message_id]
    rows.insert(0, message)
    saved = cloudflare_email_routing_write_inbox(rows)
    return {"message": message, "count": len(saved.get("messages", []))}


def cloudflare_email_routing_messages_for_dashboard(limit: int = 80) -> list[dict]:
    try:
        count = max(1, min(CLOUDFLARE_EMAIL_ROUTING_MAX_MESSAGES, int(limit or 80)))
    except Exception:
        count = 80
    return cloudflare_email_routing_read_inbox().get("messages", [])[:count]


def cloudflare_email_routing_received_addresses_for_dashboard() -> list[dict]:
    rows = cloudflare_email_routing_read_inbox().get("messages", [])
    by_address: dict[str, dict] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        address = normalize_email_routing_address(item.get("to", item.get("recipient", "")))
        if not address:
            continue
        latest = clean(item.get("received_at", ""))
        entry = by_address.get(address) or {
            "address": address,
            "count": 0,
            "latest": "",
            "last_received_at": "",
            "title": "",
        }
        entry["count"] = int(entry.get("count", 0) or 0) + 1
        if not clean(entry.get("latest", "")) or latest > clean(entry.get("latest", "")):
            entry["latest"] = latest
            entry["last_received_at"] = latest
            entry["title"] = clean(item.get("title", item.get("subject", "")))[:220]
        by_address[address] = entry
    out = list(by_address.values())
    out.sort(key=lambda row: (clean(row.get("latest", "")), clean(row.get("address", ""))), reverse=True)
    return out


def cloudflare_email_routing_nslookup(record_type: str, domain: str, server: str = "1.1.1.1") -> str:
    kind = clean(record_type or "").upper()
    target = normalize_email_routing_domain(domain)
    resolver = clean(server or "1.1.1.1") or "1.1.1.1"
    if kind not in {"MX", "TXT"} or not target:
        return ""
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        result = subprocess.run(
            ["nslookup", f"-type={kind}", target, resolver],
            capture_output=True,
            text=True,
            timeout=6,
            creationflags=flags,
        )
        text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return text[:5000]
    except Exception:
        return ""


def cloudflare_email_routing_mx_records(domain: str) -> list[dict]:
    text = cloudflare_email_routing_nslookup("MX", domain)
    records = []
    seen = set()
    for match in re.finditer(r"MX preference\s*=\s*(\d+),\s*mail exchanger\s*=\s*([^\s]+)", text, re.I):
        host = clean(match.group(2)).lower().rstrip(".")
        if not host or host in seen:
            continue
        seen.add(host)
        records.append({"preference": int(match.group(1)), "host": host})
    records.sort(key=lambda row: (int(row.get("preference", 0)), row.get("host", "")))
    return records


def cloudflare_email_routing_txt_records(domain: str) -> list[str]:
    text = cloudflare_email_routing_nslookup("TXT", domain)
    rows = []
    seen = set()
    for match in re.finditer(r'"([^"]+)"', text):
        value = clean(match.group(1))
        if value and value not in seen:
            seen.add(value)
            rows.append(value)
    return rows[:20]


def cloudflare_email_routing_public_endpoint(domain: str) -> str:
    try:
        settings = load_server_settings()
    except Exception:
        settings = {}
    host = normalize_cloudflare_public_hostname(settings.get("cloudflare_public_hostname", "")) if isinstance(settings, dict) else ""
    if not host:
        host = normalize_email_routing_domain(domain)
    return f"https://{host}/email-routing/inbound" if host else ""


def cloudflare_email_routing_probe_endpoint(endpoint: str) -> dict:
    url = clean(endpoint)
    if not url.startswith("https://"):
        return {"ok": False, "status": 0, "error": "Public HTTPS endpoint is missing."}
    try:
        request = Request(url, method="OPTIONS")
        with urlopen(request, timeout=6) as response:
            return {"ok": 200 <= int(response.status) < 400, "status": int(response.status), "error": ""}
    except Exception as exc:
        return {"ok": False, "status": 0, "error": clean(str(exc))[:220]}


def cloudflare_email_routing_readiness(config: dict | None = None, messages: list[dict] | None = None) -> dict:
    effective = config or cloudflare_email_routing_effective_config()
    domain = normalize_email_routing_domain(effective.get("domain", "")) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    inbox_rows = messages if isinstance(messages, list) else cloudflare_email_routing_messages_for_dashboard()
    mx_records = cloudflare_email_routing_mx_records(domain)
    txt_records = cloudflare_email_routing_txt_records(domain)
    endpoint = cloudflare_email_routing_public_endpoint(domain)
    endpoint_probe = cloudflare_email_routing_probe_endpoint(endpoint)
    has_secret = bool(clean(effective.get("inbound_secret", "")))
    mx_ready = any("mx.cloudflare.net" in clean(row.get("host", "")).lower() for row in mx_records)
    spf_ready = any("include:_spf.mx.cloudflare.net" in row.lower() for row in txt_records)
    worker_seen = any(clean(row.get("source", "")) == "cloudflare-email-worker" for row in inbox_rows if isinstance(row, dict))
    server_ready = bool(mx_ready and has_secret and endpoint_probe.get("ok"))
    return {
        "domain": domain,
        "ready": server_ready,
        "mx_ready": mx_ready,
        "spf_ready": spf_ready,
        "webhook_secret_ready": has_secret,
        "public_endpoint": endpoint,
        "public_endpoint_ready": bool(endpoint_probe.get("ok")),
        "public_endpoint_status": endpoint_probe.get("status", 0),
        "public_endpoint_error": clean(endpoint_probe.get("error", ""))[:220],
        "api_token_ready": bool(clean(effective.get("api_token", ""))),
        "api_token_optional": True,
        "message_count": len(inbox_rows),
        "cloudflare_worker_seen": bool(worker_seen),
        "mx_records": mx_records,
        "txt_records": txt_records,
        "checked_at": utc_timestamp(),
    }


def cloudflare_email_routing_public_config(live: bool = False) -> dict:
    config = cloudflare_email_routing_effective_config()
    token = clean(config.get("api_token", ""))
    inbound_secret = cloudflare_email_routing_ensure_inbound_secret(config)
    messages = cloudflare_email_routing_messages_for_dashboard()
    received_addresses = cloudflare_email_routing_received_addresses_for_dashboard()
    payload = {
        "domain": clean(config.get("domain", "")),
        "account_id": clean(config.get("account_id", "")),
        "zone_id": clean(config.get("zone_id", "")),
        "default_destination": normalize_email_routing_address(config.get("default_destination", "")),
        "token_saved": bool(token),
        "token_source": clean(config.get("token_source", "missing")),
        "token_hint": ("..." + token[-4:]) if token and len(token) >= 4 else "",
        "inbound_secret": inbound_secret,
        "inbound_secret_hint": ("..." + inbound_secret[-6:]) if inbound_secret and len(inbound_secret) >= 6 else "",
        "inbound_endpoint": "/email-routing/inbound",
        "aliases": normalize_email_routing_alias_rows(config.get("aliases", []), config.get("domain", "")),
        "messages": messages,
        "received_addresses": received_addresses,
        "readiness": cloudflare_email_routing_readiness(config, messages),
        "storage_file": str(CLOUDFLARE_EMAIL_ROUTING_FILE),
        "docs": {
            "rules": "https://developers.cloudflare.com/api/resources/email_routing/subresources/rules/methods/create/",
            "addresses": "https://developers.cloudflare.com/email-routing/setup/email-routing-addresses/",
        },
    }
    if live:
        try:
            payload["live"] = cloudflare_email_routing_live_state(config)
        except Exception as exc:
            payload["live_error"] = str(exc)
    return payload


def cloudflare_email_routing_require_config(config: dict, need_account: bool = False, need_zone: bool = False) -> dict:
    token = clean(config.get("api_token", ""))
    if not token:
        raise RuntimeError("Thieu Cloudflare API token.")
    if need_account and not clean(config.get("account_id", "")):
        raise RuntimeError("Thieu Cloudflare account_id.")
    if need_zone and not clean(config.get("zone_id", "")):
        raise RuntimeError("Thieu Cloudflare zone_id.")
    return config


def cloudflare_email_routing_api_request(method: str, api_path: str, payload: dict | None = None, config: dict | None = None, timeout: float = 25.0) -> dict:
    effective = cloudflare_email_routing_require_config(config or cloudflare_email_routing_effective_config())
    method = clean(method or "GET").upper()
    api_path = "/" + clean(api_path).lstrip("/")
    data = json_bytes(payload or {}) if payload is not None else None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {clean(effective.get('api_token', ''))}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(CLOUDFLARE_EMAIL_ROUTING_API_BASE + api_path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=max(2.0, float(timeout or 25.0))) as response:
            raw = response.read()
    except HTTPError as exc:
        raw = exc.read()
        message = cloudflare_email_routing_api_error_text(raw)
        raise RuntimeError(f"Cloudflare API {exc.code}: {message}") from exc
    except URLError as exc:
        raise RuntimeError(f"Khong ket noi duoc Cloudflare API: {exc}") from exc
    try:
        result = json.loads(raw.decode("utf-8-sig", errors="replace")) if raw else {}
    except Exception as exc:
        raise RuntimeError("Cloudflare API tra ve JSON khong hop le.") from exc
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(cloudflare_email_routing_api_payload_error(result))
    return result if isinstance(result, dict) else {"success": False, "result": result}


def cloudflare_email_routing_api_error_text(raw: bytes) -> str:
    try:
        payload = json.loads((raw or b"").decode("utf-8-sig", errors="replace"))
        if isinstance(payload, dict):
            return cloudflare_email_routing_api_payload_error(payload)
    except Exception:
        pass
    text = clean((raw or b"").decode("utf-8", errors="replace"))[:500]
    return text or "Cloudflare API request failed."


def cloudflare_email_routing_api_payload_error(payload: dict) -> str:
    parts = []
    for key in ("errors", "messages"):
        rows = payload.get(key, [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    message = clean(row.get("message", ""))
                    code = clean(row.get("code", ""))
                    if message:
                        parts.append((f"{code}: " if code else "") + message)
    return "; ".join(parts) or "Cloudflare API request failed."


def cloudflare_email_routing_live_state(config: dict | None = None) -> dict:
    effective = cloudflare_email_routing_effective_config()
    if config:
        effective.update(config)
    cloudflare_email_routing_require_config(effective, need_account=True, need_zone=True)
    account_id = quote(clean(effective.get("account_id", "")), safe="")
    zone_id = quote(clean(effective.get("zone_id", "")), safe="")
    addresses = cloudflare_email_routing_api_request("GET", f"/accounts/{account_id}/email/routing/addresses?per_page=100", config=effective)
    rules = cloudflare_email_routing_api_request("GET", f"/zones/{zone_id}/email/routing/rules?per_page=100", config=effective)
    return {
        "addresses": cloudflare_email_routing_simplify_addresses(addresses.get("result", [])),
        "rules": cloudflare_email_routing_simplify_rules(rules.get("result", []), effective.get("domain", "")),
        "checked_at": utc_timestamp(),
    }


def cloudflare_email_routing_simplify_addresses(rows: object) -> list[dict]:
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({
            "id": clean(row.get("id", "")),
            "email": normalize_email_routing_address(row.get("email", "")),
            "verified": clean(row.get("verified", "")),
            "created": clean(row.get("created", "")),
            "modified": clean(row.get("modified", "")),
        })
    out.sort(key=lambda item: item.get("email", ""))
    return out


def cloudflare_email_routing_simplify_rules(rows: object, domain: str = "") -> list[dict]:
    if not isinstance(rows, list):
        return []
    normalized_domain = normalize_email_routing_domain(domain)
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        address = ""
        for matcher in row.get("matchers", []) if isinstance(row.get("matchers", []), list) else []:
            if isinstance(matcher, dict) and clean(matcher.get("field", "")) == "to":
                address = normalize_email_routing_address(matcher.get("value", ""))
                break
        if normalized_domain and address and not address.endswith("@" + normalized_domain):
            continue
        destinations = []
        for action in row.get("actions", []) if isinstance(row.get("actions", []), list) else []:
            if isinstance(action, dict) and clean(action.get("type", "")) == "forward":
                values = action.get("value", [])
                if isinstance(values, list):
                    destinations.extend([normalize_email_routing_address(item) for item in values])
        destinations = [item for item in destinations if item]
        out.append({
            "id": clean(row.get("id", "")),
            "address": address,
            "destinations": destinations,
            "enabled": bool(row.get("enabled", False)),
            "name": clean(row.get("name", "")),
            "priority": row.get("priority", 0),
        })
    out.sort(key=lambda item: item.get("address", ""))
    return out


def cloudflare_email_routing_save_settings(payload: dict) -> dict:
    existing = cloudflare_email_routing_read_config()
    domain = normalize_email_routing_domain(payload.get("domain", "")) or existing.get("domain", "") or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    destination = normalize_email_routing_address(payload.get("default_destination", "")) if "default_destination" in payload else existing.get("default_destination", "")
    if payload.get("default_destination") and not destination:
        raise RuntimeError("Gmail dich khong hop le.")
    token = clean(payload.get("api_token", ""))
    if not token and not truthy(payload.get("clear_token", False), False):
        token = existing.get("api_token", "")
    if truthy(payload.get("clear_token", False), False):
        token = ""
    inbound_secret = clean(payload.get("inbound_secret", ""))
    if truthy(payload.get("regenerate_inbound_secret", False), False):
        inbound_secret = secrets.token_urlsafe(32)
    if not inbound_secret:
        inbound_secret = existing.get("inbound_secret", "")
    saved = cloudflare_email_routing_write_config({
        "domain": domain,
        "account_id": clean(payload.get("account_id", existing.get("account_id", "")))[:120],
        "zone_id": clean(payload.get("zone_id", existing.get("zone_id", "")))[:120],
        "default_destination": destination,
        "api_token": token,
        "inbound_secret": inbound_secret,
    })
    return cloudflare_email_routing_public_config(live=False)


def cloudflare_email_routing_create_destination(payload: dict) -> dict:
    config = cloudflare_email_routing_effective_config()
    cloudflare_email_routing_require_config(config, need_account=True)
    destination = normalize_email_routing_address(payload.get("destination", "") or config.get("default_destination", ""))
    if not destination:
        raise RuntimeError("Nhap Gmail dich de Cloudflare gui email xac minh.")
    account_id = quote(clean(config.get("account_id", "")), safe="")
    result = cloudflare_email_routing_api_request(
        "POST",
        f"/accounts/{account_id}/email/routing/addresses",
        {"email": destination},
        config=config,
    )
    return {"destination": destination, "cloudflare": result, **cloudflare_email_routing_public_config(live=True)}


def cloudflare_email_routing_create_alias(payload: dict) -> dict:
    config = cloudflare_email_routing_effective_config()
    cloudflare_email_routing_require_config(config, need_zone=True)
    domain = normalize_email_routing_domain(payload.get("domain", "") or config.get("domain", "")) or CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN
    address = normalize_email_routing_alias_input(payload.get("address", "") or payload.get("local_part", ""), domain)
    destination = normalize_email_routing_address(payload.get("destination", "") or config.get("default_destination", ""))
    if not destination:
        raise RuntimeError("Nhap Gmail dich da verify tren Cloudflare.")
    zone_id = quote(clean(config.get("zone_id", "")), safe="")
    name = clean(payload.get("name", ""))[:256] or f"Future mail {address}"
    rule_payload = {
        "name": name,
        "enabled": truthy(payload.get("enabled", True), True),
        "matchers": [{"type": "literal", "field": "to", "value": address}],
        "actions": [{"type": "forward", "value": [destination]}],
    }
    result = cloudflare_email_routing_api_request(
        "POST",
        f"/zones/{zone_id}/email/routing/rules",
        rule_payload,
        config=config,
    )
    rule = result.get("result", {}) if isinstance(result.get("result", {}), dict) else {}
    cloudflare_email_routing_record_alias(address, destination, rule)
    return {"address": address, "destination": destination, "cloudflare": result, **cloudflare_email_routing_public_config(live=True)}


def cloudflare_email_routing_record_alias(address: str, destination: str, rule: dict) -> None:
    config = cloudflare_email_routing_read_config()
    aliases = [row for row in normalize_email_routing_alias_rows(config.get("aliases", []), config.get("domain", "")) if row.get("address") != address]
    aliases.append({
        "address": normalize_email_routing_address(address),
        "destination": normalize_email_routing_address(destination),
        "rule_id": clean(rule.get("id", ""))[:120] if isinstance(rule, dict) else "",
        "name": clean(rule.get("name", ""))[:256] if isinstance(rule, dict) else "",
        "enabled": bool(rule.get("enabled", True)) if isinstance(rule, dict) else True,
        "created_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
    })
    cloudflare_email_routing_write_config({"aliases": aliases})


def cloudflare_email_routing_delete_alias(payload: dict) -> dict:
    config = cloudflare_email_routing_effective_config()
    cloudflare_email_routing_require_config(config, need_zone=True)
    rule_id = clean(payload.get("rule_id", "") or payload.get("id", ""))
    address = normalize_email_routing_address(payload.get("address", ""))
    if not rule_id:
        for row in normalize_email_routing_alias_rows(config.get("aliases", []), config.get("domain", "")):
            if address and row.get("address") == address:
                rule_id = clean(row.get("rule_id", ""))
                break
    if not rule_id:
        raise RuntimeError("Thieu Cloudflare rule_id de xoa alias.")
    zone_id = quote(clean(config.get("zone_id", "")), safe="")
    result = cloudflare_email_routing_api_request("DELETE", f"/zones/{zone_id}/email/routing/rules/{quote(rule_id, safe='')}", config=config)
    current = cloudflare_email_routing_read_config()
    aliases = []
    for row in normalize_email_routing_alias_rows(current.get("aliases", []), current.get("domain", "")):
        if row.get("rule_id") == rule_id or (address and row.get("address") == address):
            continue
        aliases.append(row)
    cloudflare_email_routing_write_config({"aliases": aliases})
    return {"deleted": rule_id, "cloudflare": result, **cloudflare_email_routing_public_config(live=True)}


def cloudflare_email_routing_worker_script(endpoint: str = "") -> str:
    config = cloudflare_email_routing_effective_config()
    secret = cloudflare_email_routing_ensure_inbound_secret(config)
    default_destination = normalize_email_routing_address(config.get("default_destination", ""))
    endpoint_value = clean(endpoint)
    if not endpoint_value:
        endpoint_value = "https://YOUR-FUTURE-SERVER/email-routing/inbound"
    if not endpoint_value.endswith("/email-routing/inbound"):
        endpoint_value = endpoint_value.rstrip("/") + "/email-routing/inbound"
    return f"""export default {{
  async email(message, env, ctx) {{
    const endpoint = env.FUTURE_INBOUND_URL || {json.dumps(endpoint_value)};
    const secret = env.FUTURE_EMAIL_SECRET || {json.dumps(secret)};
    const forwardTo = env.DEFAULT_FORWARD_TO || {json.dumps(default_destination)};
    const subject = message.headers.get("subject") || "";
    const messageId = message.headers.get("message-id") || crypto.randomUUID();
    let raw = "";
    try {{
      raw = await new Response(message.raw).text();
    }} catch (error) {{
      raw = String(error && error.message ? error.message : error);
    }}
    ctx.waitUntil(fetch(endpoint, {{
      method: "POST",
      headers: {{
        "Content-Type": "application/json; charset=utf-8",
        "X-Future-Email-Secret": secret,
      }},
      body: JSON.stringify({{
        id: messageId,
        to: message.to,
        from: message.from,
        subject,
        text: raw.slice(0, 12000),
        snippet: raw.slice(0, 300),
        source: "cloudflare-email-worker",
      }}),
    }}));
    if (forwardTo && message.canBeForwarded) {{
      await message.forward(forwardTo);
    }}
  }},
}};
"""


def cloudflare_email_routing_admin_page() -> str:
    state = cloudflare_email_routing_public_config(live=False)
    state_json = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    return """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Future Email Routing</title>
  <style>
    :root { color-scheme: light; --ink:#17202a; --muted:#5c6975; --line:#d9e2ea; --bg:#f6f8fb; --panel:#ffffff; --accent:#147a7e; --danger:#b42318; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Arial, sans-serif; background:var(--bg); color:var(--ink); }
    header { padding:22px 24px 14px; border-bottom:1px solid var(--line); background:#fff; }
    h1 { margin:0; font-size:24px; line-height:1.2; }
    main { width:min(1180px, calc(100% - 32px)); margin:18px auto 40px; display:grid; gap:14px; }
    section { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }
    h2 { margin:0 0 12px; font-size:17px; }
    form { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; align-items:end; }
    label { display:grid; gap:5px; font-size:13px; color:var(--muted); }
    input { width:100%; padding:10px 11px; border:1px solid #c8d3dd; border-radius:6px; font-size:14px; color:var(--ink); background:#fff; }
    button { min-height:38px; border:0; border-radius:6px; padding:0 14px; color:white; background:var(--accent); font-weight:700; cursor:pointer; }
    button.secondary { background:#344054; }
    button.danger { background:var(--danger); }
    button:disabled { opacity:.55; cursor:wait; }
    .full { grid-column:1 / -1; }
    .bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:space-between; }
    .note { color:var(--muted); font-size:13px; line-height:1.45; }
    .status { min-height:24px; color:var(--muted); font-size:13px; }
    .status.error { color:var(--danger); }
    .grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { padding:9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
    th { color:var(--muted); font-size:12px; text-transform:uppercase; }
    code { background:#eef4f7; padding:2px 5px; border-radius:5px; }
    .message-list { display:grid; gap:10px; }
    .message { border:1px solid var(--line); border-radius:8px; padding:12px; background:#fbfdff; }
    .message-title { margin:0 0 6px; font-size:15px; line-height:1.35; }
    .message-meta { color:var(--muted); font-size:12px; line-height:1.45; }
    .message-content { margin:9px 0 0; white-space:pre-wrap; line-height:1.45; max-height:190px; overflow:auto; }
    @media (max-width: 820px) { form, .grid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <div>
        <h1>Future Email Routing</h1>
        <div class="note">Cloudflare forward aliases for <code id="domainLabel"></code></div>
      </div>
      <button class="secondary" id="refreshLive" type="button">Refresh live</button>
    </div>
  </header>
  <main>
    <section>
      <h2>Cloudflare config</h2>
      <form id="configForm">
        <label>Domain <input name="domain" autocomplete="off"></label>
        <label>Default Gmail destination <input name="default_destination" autocomplete="off" placeholder="name@gmail.com"></label>
        <label>Account ID <input name="account_id" autocomplete="off"></label>
        <label>Zone ID <input name="zone_id" autocomplete="off"></label>
        <label class="full">API token <input name="api_token" autocomplete="off" placeholder="leave blank to keep saved token"></label>
        <label><span><input type="checkbox" name="clear_token" value="1" style="width:auto"> Clear saved token</span></label>
        <div><button type="submit">Save config</button></div>
      </form>
      <p class="note" id="tokenStatus"></p>
    </section>

    <div class="grid">
      <section>
        <h2>Destination Gmail</h2>
        <form id="destinationForm">
          <label class="full">Gmail to verify <input name="destination" autocomplete="off" placeholder="name@gmail.com"></label>
          <div class="full"><button type="submit">Send verify email</button></div>
        </form>
        <p class="note">Cloudflare will email this inbox. Click verify there before creating aliases.</p>
      </section>

      <section>
        <h2>Create alias</h2>
        <form id="aliasForm">
          <label>Alias <input name="address" autocomplete="off" placeholder="admin"></label>
          <label>Forward to Gmail <input name="destination" autocomplete="off" placeholder="default Gmail if empty"></label>
          <label class="full">Rule name <input name="name" autocomplete="off" placeholder="optional"></label>
          <div class="full"><button type="submit">Create alias</button></div>
        </form>
      </section>
    </div>

    <section>
      <div class="bar"><h2>Aliases</h2><span class="status" id="status"></span></div>
      <div id="aliasTable"></div>
    </section>

    <section>
      <h2>Destination addresses</h2>
      <div id="destinationTable"></div>
    </section>

    <section>
      <h2>Received messages</h2>
      <div id="messageTable"></div>
    </section>
  </main>
  <script id="initialState" type="application/json">__STATE_JSON__</script>
  <script>
    let state = JSON.parse(document.getElementById("initialState").textContent || "{}");
    const statusEl = document.getElementById("status");
    const domainLabel = document.getElementById("domainLabel");
    const tokenStatus = document.getElementById("tokenStatus");
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[ch]));
    const setStatus = (message, error = false) => {
      statusEl.textContent = message || "";
      statusEl.classList.toggle("error", !!error);
    };
    const formPayload = (form) => Object.fromEntries(new FormData(form).entries());
    const api = async (url, options = {}) => {
      const response = await fetch(url, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) throw new Error(payload.error || response.statusText);
      return payload;
    };
    const fillConfig = () => {
      const form = document.getElementById("configForm");
      form.domain.value = state.domain || "";
      form.account_id.value = state.account_id || "";
      form.zone_id.value = state.zone_id || "";
      form.default_destination.value = state.default_destination || "";
      form.api_token.value = "";
      form.clear_token.checked = false;
      domainLabel.textContent = state.domain || "";
      tokenStatus.textContent = state.token_saved ? `Token: ${state.token_source || "local"} ${state.token_hint || ""}` : "Token: missing";
    };
    const rowsHtml = (rows, columns, empty) => {
      if (!rows || !rows.length) return `<p class="note">${empty}</p>`;
      return `<table><thead><tr>${columns.map((col) => `<th>${col[0]}</th>`).join("")}</tr></thead><tbody>` +
        rows.map((row) => `<tr>${columns.map((col) => `<td>${col[1](row)}</td>`).join("")}</tr>`).join("") +
        `</tbody></table>`;
    };
    const render = () => {
      fillConfig();
      const liveRules = state.live && Array.isArray(state.live.rules) ? state.live.rules : [];
      const localAliases = Array.isArray(state.aliases) ? state.aliases : [];
      const rows = liveRules.length ? liveRules : localAliases.map((row) => ({
        id: row.rule_id,
        address: row.address,
        destinations: row.destination ? [row.destination] : [],
        enabled: row.enabled,
        name: row.name,
      }));
      document.getElementById("aliasTable").innerHTML = rowsHtml(rows, [
        ["Address", (row) => `<code>${esc(row.address || "")}</code>`],
        ["Forward", (row) => (row.destinations || []).map(esc).join("<br>") || ""],
        ["Status", (row) => row.enabled ? "enabled" : "disabled"],
        ["Rule", (row) => `<span class="note">${esc(row.id || row.name || "")}</span>`],
        ["", (row) => row.id ? `<button class="danger" data-delete="${esc(row.id)}" data-address="${esc(row.address || "")}" type="button">Delete</button>` : ""],
      ], "No aliases yet.");
      const addresses = state.live && Array.isArray(state.live.addresses) ? state.live.addresses : [];
      document.getElementById("destinationTable").innerHTML = rowsHtml(addresses, [
        ["Email", (row) => `<code>${esc(row.email || "")}</code>`],
        ["Verified", (row) => row.verified ? esc(row.verified) : "pending"],
        ["ID", (row) => `<span class="note">${esc(row.id || "")}</span>`],
      ], "Use Refresh live after saving Cloudflare config.");
      const messages = Array.isArray(state.messages) ? state.messages : [];
      document.getElementById("messageTable").innerHTML = messages.length ? `<div class="message-list">` + messages.map((row) => `
        <article class="message">
          <h3 class="message-title">${esc(row.title || row.subject || "(No subject)")}</h3>
          <div class="message-meta">
            From <code>${esc(row.from || "")}</code> to <code>${esc(row.to || "")}</code><br>
            ${esc(row.received_at || "")} | ${esc(row.source || "")}
          </div>
          <div class="message-content">${esc(row.content || row.snippet || row.text || "")}</div>
        </article>
      `).join("") + `</div>` : `<p class="note">No received messages yet.</p>`;
      document.querySelectorAll("[data-delete]").forEach((button) => {
        button.addEventListener("click", async () => {
          if (!confirm(`Delete ${button.dataset.address || "this alias"}?`)) return;
          await runButton(button, async () => {
            state = await api("/dashboard/email-routing/delete-rule", {
              method: "POST",
              body: JSON.stringify({ rule_id: button.dataset.delete, address: button.dataset.address || "" }),
            });
            render();
          });
        });
      });
    };
    const runButton = async (button, work) => {
      button.disabled = true;
      try {
        setStatus("Working...");
        await work();
        setStatus("Done.");
      } catch (error) {
        setStatus(error.message || String(error), true);
      } finally {
        button.disabled = false;
      }
    };
    document.getElementById("configForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runButton(event.submitter, async () => {
        const payload = formPayload(event.currentTarget);
        payload.clear_token = event.currentTarget.clear_token.checked;
        state = await api("/dashboard/email-routing/config", { method: "POST", body: JSON.stringify(payload) });
        render();
      });
    });
    document.getElementById("destinationForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runButton(event.submitter, async () => {
        state = await api("/dashboard/email-routing/destination", { method: "POST", body: JSON.stringify(formPayload(event.currentTarget)) });
        render();
      });
    });
    document.getElementById("aliasForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await runButton(event.submitter, async () => {
        state = await api("/dashboard/email-routing/alias", { method: "POST", body: JSON.stringify(formPayload(event.currentTarget)) });
        render();
      });
    });
    document.getElementById("refreshLive").addEventListener("click", async (event) => {
      await runButton(event.currentTarget, async () => {
        state = await api("/dashboard/email-routing/state?live=1");
        render();
      });
    });
    render();
  </script>
</body>
</html>""".replace("__STATE_JSON__", state_json)
