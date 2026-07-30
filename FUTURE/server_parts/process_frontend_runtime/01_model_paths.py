# Loaded by FUTURE.server_parts.06_process_frontend_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", clean(text).lower())


def model_candidates(model_name: str) -> list[str]:
    raw = clean(model_name).lower() or "small"
    if raw.endswith(".fast"):
        raw = raw[:-5].strip() or "small"
    ordered = list(MODEL_ALIASES.get(raw, [])) or [raw]
    if raw not in ordered:
        ordered.insert(0, raw)
    out = []
    seen = set()
    for item in ordered:
        key = clean(item).lower()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def folder_names_for_model(name: str) -> list[str]:
    names = [
        f"faster-whisper-{name}",
        f"faster_whisper_{name}",
    ]
    if name.endswith(".en"):
        base = name[:-3]
        names.extend([f"faster-whisper-{base}.en", f"faster_whisper_{base}_en"])
    return names


def resolve_model_path(model_name: str) -> str:
    checked = []
    raw = clean(model_name)
    if raw:
        direct = Path(raw)
        if direct.is_dir() and (direct / "model.bin").is_file():
            return str(direct)
    for root in MODEL_DIRS:
        for name in model_candidates(model_name):
            for folder_name in folder_names_for_model(name):
                candidate = Path(root) / folder_name
                checked.append(str(candidate))
                if candidate.is_dir() and (candidate / "model.bin").is_file():
                    return str(candidate)
    raise RuntimeError(
        "Offline faster-whisper model not found. Expected folder with model.bin, for example "
        f"C:\\QMLearn\\models\\faster-whisper-{clean(model_name) or 'small'}. Checked: "
        + " | ".join(checked[:32])
    )


def configure_paths() -> None:
    # Added 2026-07-13: PyInstaller onedir workers need native ML DLL folders registered before faster-whisper imports.
    native_roots = []
    try:
        if getattr(sys, "_MEIPASS", ""):
            native_roots.append(Path(getattr(sys, "_MEIPASS")).resolve())
    except Exception:
        pass
    try:
        native_roots.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass
    try:
        native_roots.append(Path.cwd().resolve())
    except Exception:
        pass
    native_items = []
    for root in native_roots:
        native_items.extend(
            [
                root,
                root / "_internal",
                root / "ctranslate2",
                root / "_internal" / "ctranslate2",
                root / "onnxruntime" / "capi",
                root / "_internal" / "onnxruntime" / "capi",
                root / "av",
                root / "_internal" / "av",
                root / "numpy.libs",
                root / "_internal" / "numpy.libs",
            ]
        )
    for item in (
        QMLEARN_ROOT / "ffmpeg" / "bin",
        QMLEARN_ROOT / "ffmpeg",
        QMLEARN_ROOT / "tools" / "ffmpeg" / "bin",
        QMLEARN_ROOT / "tools" / "ffmpeg",
        PROGRAME_ROOT,
        PROGRAME_ROOT / "module_main",
        *native_items,
    ):
        path = str(item)
        if item.exists() and path.lower() not in [x.lower() for x in os.environ.get("PATH", "").split(os.pathsep)]:
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
        if os.name == "nt" and item.exists() and hasattr(os, "add_dll_directory"):
            handles = globals().setdefault("FUTURE_NATIVE_DLL_HANDLES", [])
            seen = globals().setdefault("FUTURE_NATIVE_DLL_PATHS", set())
            key = path.lower()
            if key not in seen:
                try:
                    handles.append(os.add_dll_directory(path))
                    seen.add(key)
                except (FileNotFoundError, OSError):
                    pass
    if str(PROGRAME_ROOT) not in sys.path:
        sys.path.insert(0, str(PROGRAME_ROOT))


def local_ipv4_addresses() -> list[str]:
    addresses: list[str] = []
    seen = set()
    try:
        host_names = [socket.gethostname(), socket.getfqdn()]
        for host in host_names:
            try:
                for item in socket.gethostbyname_ex(host)[2]:
                    if item and not item.startswith("127.") and item not in seen:
                        seen.add(item)
                        addresses.append(item)
            except Exception:
                pass
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.connect(("8.8.8.8", 80))
                item = probe.getsockname()[0]
                if item and not item.startswith("127.") and item not in seen:
                    seen.add(item)
                    addresses.append(item)
            finally:
                probe.close()
        except Exception:
            pass
    except Exception:
        pass
    return addresses
