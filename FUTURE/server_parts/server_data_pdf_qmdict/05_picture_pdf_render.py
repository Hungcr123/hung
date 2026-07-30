# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def safe_pdf_server_data_path(relative_path: str = "", username: str = "", admin: bool = False) -> Path:
    target = safe_server_data_path(relative_path, username, admin=admin)
    target = server_data_effective_file_path(target, username=username, admin=admin)
    if target.is_file() and target.suffix.lower() == ".pdf":
        return target
    package_resolver = globals().get("space_pdf_package_path_for_legacy")
    package = package_resolver(target) if callable(package_resolver) else None
    if package is not None and package.is_file() and package.suffix.lower() == ".space_pdf":
        try:
            manifest = validate_space_pdf_package(package, verify_source=True)
            source = resolve_space_pdf_source_path(package, manifest)
            if source is not None and source.is_file() and source.suffix.lower() == ".pdf":
                return source.resolve()
        except Exception as exc:
            raise RuntimeError(f"Khong mo duoc PDF source trong package Space_PDF: {exc}") from exc
    raise RuntimeError("Chi duoc mo file PDF trong C:\\server data.")


def is_picture_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_FILE_SUFFIXES


def picture_natural_sort_key(value: object = "") -> list[object]:
    return natural_sort_key(value)


def safe_picture_server_data_path(relative_path: str = "", username: str = "", admin: bool = False) -> Path:
    target = safe_server_data_path(relative_path, username, admin=admin)
    target = server_data_effective_file_path(target, username=username, admin=admin)
    if not is_picture_file(target):
        raise RuntimeError("Chi duoc mo file anh trong C:\\server data.")
    return target


def picture_sibling_files(target: Path) -> list[Path]:
    if not target.parent.is_dir():
        return [target]
    try:
        rows = [item for item in target.parent.iterdir() if is_picture_file(item)]
    except Exception:
        rows = [target]
    rows.sort(key=lambda item: picture_natural_sort_key(item.name))
    return rows or [target]


def picture_target_for_page(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1) -> tuple[Path, list[Path], int]:
    selected = safe_picture_server_data_path(relative_path, username, admin=admin)
    siblings = picture_sibling_files(selected)
    try:
        selected_index = next((index for index, item in enumerate(siblings) if item.resolve() == selected.resolve()), 0)
    except Exception:
        selected_index = 0
    try:
        page_number = int(page)
    except Exception:
        page_number = selected_index + 1
    if page_number <= 0:
        page_number = selected_index + 1
    index = max(0, min(len(siblings) - 1, page_number - 1))
    return siblings[index], siblings, index


def open_picture_image(path: Path):
    try:
        from PIL import Image, ImageOps
    except Exception as exc:
        raise RuntimeError("May chu chua co PIL/Pillow de mo anh.") from exc
    image = Image.open(path)
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass
    return image.convert("RGB")


def pdf_picture_metadata_index_load() -> dict:
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        if PDF_PICTURE_METADATA_INDEX.get("loaded"):
            return PDF_PICTURE_METADATA_INDEX
        items = {}
        try:
            payload = json.loads(PDF_PICTURE_METADATA_INDEX_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            if isinstance(payload, dict) and isinstance(payload.get("items"), dict):
                items = {clean(key): value for key, value in payload.get("items", {}).items() if clean(key) and isinstance(value, dict)}
        except Exception:
            items = {}
        PDF_PICTURE_METADATA_INDEX.update({"loaded": True, "items": items})
        return PDF_PICTURE_METADATA_INDEX


def pdf_picture_metadata_index_save_locked() -> None:
    items = PDF_PICTURE_METADATA_INDEX.get("items")
    if not isinstance(items, dict):
        items = {}
    try:
        atomic_write_json(PDF_PICTURE_METADATA_INDEX_FILE, {
            "version": 1,
            "updated_at": utc_timestamp(),
            "items": items,
        }, indent=None)
        schedule_future_boot_snapshot_write("pdf_picture_metadata", delay=1.0)
    except Exception as exc:
        PDF_PICTURE_METADATA_WARM_STATE["error"] = str(exc)


def pdf_picture_metadata_signature(path: Path, *, include_parent: bool = False) -> dict:
    try:
        stat = path.stat()
        signature = {"mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}
    except OSError:
        signature = {"mtime_ns": 0, "size": -1}
    if include_parent:
        try:
            parent_stat = path.parent.stat()
            signature["parent_mtime_ns"] = int(parent_stat.st_mtime_ns)
        except OSError:
            signature["parent_mtime_ns"] = 0
    return signature


def pdf_picture_metadata_cache_key(kind: str, path: Path) -> str:
    return f"{clean(kind).lower()}:{server_data_relative(path).lower()}"


def get_cached_pdf_picture_metadata(kind: str, path: Path, *, include_parent: bool = False) -> dict | None:
    pdf_picture_metadata_index_load()
    key = pdf_picture_metadata_cache_key(kind, path)
    signature = pdf_picture_metadata_signature(path, include_parent=include_parent)
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        items = PDF_PICTURE_METADATA_INDEX.get("items") if isinstance(PDF_PICTURE_METADATA_INDEX.get("items"), dict) else {}
        row = items.get(key) if isinstance(items, dict) else None
        if not isinstance(row, dict) or row.get("signature") != signature or not isinstance(row.get("info"), dict):
            return None
        info = dict(row["info"])
    return info


def remember_pdf_picture_metadata(kind: str, path: Path, info: dict, *, include_parent: bool = False, persist: bool = True) -> None:
    if not isinstance(info, dict):
        return
    pdf_picture_metadata_index_load()
    key = pdf_picture_metadata_cache_key(kind, path)
    signature = pdf_picture_metadata_signature(path, include_parent=include_parent)
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        items = PDF_PICTURE_METADATA_INDEX.get("items")
        if not isinstance(items, dict):
            items = {}
            PDF_PICTURE_METADATA_INDEX["items"] = items
        items[key] = {
            "signature": signature,
            "info": dict(info),
            "at": time.time(),
        }
        if len(items) > 600:
            ordered = sorted(items.items(), key=lambda item: float(item[1].get("at", 0) or 0) if isinstance(item[1], dict) else 0)
            for old_key, _old_row in ordered[: max(1, len(items) - 520)]:
                items.pop(old_key, None)
        if persist:
            pdf_picture_metadata_index_save_locked()


def picture_document_info(relative_path: str = "", username: str = "", admin: bool = False, trusted_target: Path | None = None) -> dict:
    target = Path(trusted_target).resolve() if trusted_target is not None else safe_picture_server_data_path(relative_path, username, admin=admin)
    canonical_single = trusted_target is not None
    cached = get_cached_pdf_picture_metadata("picture", target, include_parent=not canonical_single)
    if cached is not None:
        cached["ghost_eye_ready"] = bool(resolve_tesseract_cmd())
        return cached
    if canonical_single:
        current, siblings, index = target, [target], 0
    else:
        current, siblings, index = picture_target_for_page(relative_path, username, admin=admin, page=0)
    try:
        from PIL import Image
        with Image.open(current) as image:
            width, height = image.size
    except Exception:
        width, height = 0, 0
    info = {
        "path": server_data_relative(target),
        "current_path": server_data_relative(current),
        "name": target.name,
        "title": target.stem,
        "pages": len(siblings),
        "page": index + 1,
        "size": int(target.stat().st_size),
        "first_page": {"width": width, "height": height},
        "has_text_layer": False,
        "text_layer": {"has_text_layer": False, "sampled_pages": 0, "sample_text_pages": 0, "sample_text_chars": 0},
        "ghost_eye_ready": bool(resolve_tesseract_cmd()),
        "images": [
            {
                "page": row_index + 1,
                "name": item.name,
                "path": server_data_relative(item),
                "size": int(item.stat().st_size),
            }
            for row_index, item in enumerate(siblings)
        ],
    }
    remember_pdf_picture_metadata("picture", target, info, include_parent=not canonical_single)
    return info


def render_picture_image_png(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, trusted_target: Path | None = None) -> tuple[bytes, dict]:
    if trusted_target is not None:
        target, siblings, index = Path(trusted_target).resolve(), [Path(trusted_target).resolve()], 0
    else:
        target, siblings, index = picture_target_for_page(relative_path, username, admin=admin, page=page)
    try:
        stat = target.stat()
        signature = f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"
    except OSError:
        signature = "0:0"
    suffix = target.suffix.lower()
    output_format = "PNG" if suffix == ".png" else "JPEG"
    mime = "image/png" if output_format == "PNG" else "image/jpeg"
    cache_key = f"picture|{str(target.resolve()).lower()}|{signature}|{output_format.lower()}"
    cached = get_cached_pdf_render(cache_key)
    if cached is not None:
        return cached
    image = open_picture_image(target)
    try:
        width, height = image.size
        out = io.BytesIO()
        if output_format == "PNG":
            image.save(out, format="PNG", optimize=True)
        else:
            image.save(out, format="JPEG", quality=90, optimize=True, progressive=True)
        data = out.getvalue()
    finally:
        try:
            image.close()
        except Exception:
            pass
    meta = {
        "page": index + 1,
        "pages": len(siblings),
        "path": server_data_relative(target),
        "name": target.name,
        "mime": mime,
        "width": int(width),
        "height": int(height),
        "cache_hit": False,
    }
    remember_pdf_render(cache_key, data, meta)
    return data, meta


def pdf_render_zoom(value: object = 2.0) -> float:
    try:
        zoom = float(value)
    except Exception:
        zoom = 2.0
    return max(0.5, min(6.5, zoom))


def pdf_page_index(value: object = 1, page_count: int = 0) -> int:
    try:
        page = int(value)
    except Exception:
        page = 1
    if page_count:
        page = max(1, min(int(page_count), page))
    else:
        page = max(1, page)
    return page - 1


def pdf_render_cache_key(path: Path, page_index: int, zoom: float) -> str:
    try:
        stat = path.stat()
        signature = f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"
    except OSError:
        signature = "0:0"
    return f"{str(path.resolve()).lower()}|{signature}|{int(page_index)}|{float(zoom):.2f}"


def pdf_pixmap_to_rgb_image(pix):
    from PIL import Image

    width = int(getattr(pix, "width", 0) or 0)
    height = int(getattr(pix, "height", 0) or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError("PDF page image is empty.")
    samples = getattr(pix, "samples", b"")
    channel_count = int(getattr(pix, "n", 0) or 0)
    has_alpha = bool(getattr(pix, "alpha", False))
    if channel_count == 1:
        return Image.frombytes("L", (width, height), samples).convert("RGB")
    if channel_count == 2:
        return Image.frombytes("LA", (width, height), samples).convert("RGB")
    if channel_count == 3:
        return Image.frombytes("RGB", (width, height), samples)
    if channel_count == 4 and has_alpha:
        return Image.frombytes("RGBA", (width, height), samples).convert("RGB")
    if channel_count == 4:
        return Image.frombytes("CMYK", (width, height), samples).convert("RGB")
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def should_invert_pdf_negative_scan(image) -> bool:
    try:
        from PIL import Image

        sample = image.convert("RGB")
        try:
            resample = getattr(Image.Resampling, "BILINEAR", Image.BILINEAR)
        except Exception:
            resample = 2
        sample.thumbnail((220, 220), resample)
        pixels = list(sample.getdata())
        total = len(pixels)
        if total <= 0:
            return False
        dark = 0
        light = 0
        very_dark = 0
        chroma_sum = 0
        for red, green, blue in pixels:
            luminance = (299 * red + 587 * green + 114 * blue) // 1000
            if luminance < 45:
                dark += 1
            if luminance > 210:
                light += 1
            if luminance < 18:
                very_dark += 1
            chroma_sum += max(red, green, blue) - min(red, green, blue)
        dark_ratio = dark / total
        light_ratio = light / total
        very_dark_ratio = very_dark / total
        chroma_avg = chroma_sum / total
        grayscale_scan = chroma_avg < 12
        return bool(
            grayscale_scan
            and very_dark_ratio >= 0.30
            and dark_ratio >= max(0.34, light_ratio - 0.08)
        )
    except Exception:
        return False


def correct_pdf_negative_scan_image(image):
    if not should_invert_pdf_negative_scan(image):
        return image
    try:
        from PIL import ImageOps
        return ImageOps.invert(image.convert("RGB"))
    except Exception:
        return image


def pdf_pil_resample_filter():
    try:
        from PIL import Image
        return getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
    except Exception:
        return 1


def encode_pdf_pil_png(image) -> bytes:
    out = io.BytesIO()
    image.save(out, format="PNG", compress_level=2, optimize=False)
    return out.getvalue()


def encode_pdf_pixmap_png(pix) -> bytes:
    try:
        image = correct_pdf_negative_scan_image(pdf_pixmap_to_rgb_image(pix))
        return encode_pdf_pil_png(image)
    except Exception:
        return pix.tobytes("png")


def render_single_embedded_pdf_page_image(document, page_obj, zoom: float):
    try:
        from PIL import Image

        images = page_obj.get_images(full=True)
        if len(images) != 1:
            return None
        xref = images[0][0]
        rects = page_obj.get_image_rects(xref)
        if not rects:
            return None
        image_info = document.extract_image(xref)
        image_bytes = image_info.get("image")
        if not image_bytes:
            return None
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        if image.width < 200 or image.height < 200:
            image.close()
            return None
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            image.close()
            image = Image.alpha_composite(background, rgba).convert("RGB")
            rgba.close()
            background.close()
        elif image.mode != "RGB":
            converted = image.convert("RGB")
            image.close()
            image = converted
        corrected_image = correct_pdf_negative_scan_image(image)
        if corrected_image is not image:
            try:
                image.close()
            except Exception:
                pass
            image = corrected_image
        page_rect = page_obj.rect
        canvas_width = max(1, int(round(float(page_rect.width) * zoom)))
        canvas_height = max(1, int(round(float(page_rect.height) * zoom)))
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
        target = rects[0]
        left = int(round(float(target.x0 - page_rect.x0) * zoom))
        top = int(round(float(target.y0 - page_rect.y0) * zoom))
        right = int(round(float(target.x1 - page_rect.x0) * zoom))
        bottom = int(round(float(target.y1 - page_rect.y0) * zoom))
        target_width = max(1, right - left)
        target_height = max(1, bottom - top)
        resized = image.resize((target_width, target_height), pdf_pil_resample_filter())
        image.close()
        canvas.paste(resized, (max(0, left), max(0, top)))
        resized.close()
        return canvas
    except Exception:
        return None


def pdf_render_disk_cache_paths(key: str) -> tuple[Path, Path]:
    digest = hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()
    shard = digest[:2]
    base = PDF_RENDER_DISK_CACHE_ROOT / shard / digest
    return base.with_suffix(".img"), base.with_suffix(".json")


def prune_pdf_render_disk_cache() -> None:
    if PDF_RENDER_DISK_CACHE_MAX_BYTES <= 0:
        return
    try:
        root = PDF_RENDER_DISK_CACHE_ROOT
        if not root.exists():
            return
        rows: list[tuple[float, int, Path, Path]] = []
        total = 0
        for payload_path in root.glob("*/*.img"):
            try:
                stat = payload_path.stat()
            except Exception:
                continue
            size = int(stat.st_size)
            total += size
            rows.append((float(stat.st_mtime), size, payload_path, payload_path.with_suffix(".json")))
        if total <= PDF_RENDER_DISK_CACHE_MAX_BYTES:
            return
        for _mtime, size, payload_path, meta_path in sorted(rows, key=lambda row: row[0]):
            if total <= PDF_RENDER_DISK_CACHE_MAX_BYTES:
                break
            try:
                payload_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                meta_path.unlink(missing_ok=True)
            except Exception:
                pass
            total -= size
    except Exception as exc:
        stt_debug_log("pdf_render_disk_cache_prune_failed", error=str(exc))


def get_disk_cached_pdf_render(key: str) -> tuple[bytes, dict] | None:
    if PDF_RENDER_DISK_CACHE_MAX_BYTES <= 0:
        return None
    payload_path, meta_path = pdf_render_disk_cache_paths(key)
    try:
        if not payload_path.exists() or not meta_path.exists():
            return None
        payload = payload_path.read_bytes()
        meta_raw = json.loads(meta_path.read_text(encoding="utf-8"))
        meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}
        meta["cache_hit"] = True
        meta["disk_cache_hit"] = True
        now = time.time()
        os.utime(payload_path, (now, now))
        os.utime(meta_path, (now, now))
        return payload, meta
    except Exception as exc:
        stt_debug_log("pdf_render_disk_cache_read_failed", key_hash=hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()[:12], error=str(exc))
        try:
            payload_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
        except Exception:
            pass
    return None


def remember_disk_pdf_render(key: str, payload: bytes, meta: dict) -> None:
    if PDF_RENDER_DISK_CACHE_MAX_BYTES <= 0 or not payload:
        return
    payload_path, meta_path = pdf_render_disk_cache_paths(key)
    try:
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_payload = payload_path.with_name(payload_path.name + f".{uuid.uuid4().hex}.tmp")
        tmp_meta = meta_path.with_name(meta_path.name + f".{uuid.uuid4().hex}.tmp")
        tmp_payload.write_bytes(bytes(payload))
        disk_meta = dict(meta or {})
        disk_meta.update({
            "cache_key_hash": hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest(),
            "payload_bytes": len(payload),
            "stored_at": time.time(),
        })
        tmp_meta.write_text(json.dumps(disk_meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp_payload, payload_path)
        os.replace(tmp_meta, meta_path)
        prune_pdf_render_disk_cache()
    except Exception as exc:
        stt_debug_log("pdf_render_disk_cache_write_failed", error=str(exc))


def get_cached_pdf_render(key: str) -> tuple[bytes, dict] | None:
    with PDF_RENDER_CACHE_LOCK:
        entry = PDF_RENDER_CACHE.get(key)
        if isinstance(entry, dict):
            entry["at"] = time.time()
            payload = entry.get("payload")
            meta = entry.get("meta")
            if isinstance(payload, (bytes, bytearray)) and isinstance(meta, dict):
                cached_meta = dict(meta)
                cached_meta["cache_hit"] = True
                cached_meta["ram_cache_hit"] = True
                return bytes(payload), cached_meta
    disk_cached = get_disk_cached_pdf_render(key)
    if disk_cached is not None:
        payload, meta = disk_cached
        remember_pdf_render(key, payload, meta, persist_disk=False)
        return payload, meta
    return None


def remember_pdf_render(key: str, payload: bytes, meta: dict, persist_disk: bool = True) -> None:
    data = bytes(payload or b"")
    with PDF_RENDER_CACHE_LOCK:
        PDF_RENDER_CACHE[key] = {
            "payload": data,
            "meta": dict(meta or {}),
            "size": len(data),
            "at": time.time(),
        }
        total = sum(int(item.get("size", 0) or 0) for item in PDF_RENDER_CACHE.values() if isinstance(item, dict))
        if len(PDF_RENDER_CACHE) > PDF_RENDER_CACHE_MAX_ENTRIES or total > PDF_RENDER_CACHE_MAX_BYTES:
            ordered = sorted(PDF_RENDER_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, old_entry in ordered:
                if len(PDF_RENDER_CACHE) <= PDF_RENDER_CACHE_MAX_ENTRIES and total <= PDF_RENDER_CACHE_MAX_BYTES:
                    break
                total -= int(old_entry.get("size", 0) or 0)
                PDF_RENDER_CACHE.pop(old_key, None)
    if persist_disk:
        remember_disk_pdf_render(key, data, meta)


def pdf_file_bytes_cache_key(target: Path) -> str:
    try:
        stat = target.stat()
        signature = f"{target.resolve()}|{int(stat.st_mtime_ns)}|{int(stat.st_size)}"
    except Exception:
        signature = str(target)
    return hashlib.sha256(signature.encode("utf-8", errors="ignore")).hexdigest()


def get_cached_pdf_file_bytes(target: Path) -> bytes | None:
    if PDF_FILE_BYTES_CACHE_MAX_BYTES <= 0:
        return None
    key = pdf_file_bytes_cache_key(target)
    with PDF_FILE_BYTES_CACHE_LOCK:
        entry = PDF_FILE_BYTES_CACHE.get(key)
        if not isinstance(entry, dict):
            return None
        payload = entry.get("payload")
        if not isinstance(payload, (bytes, bytearray)):
            PDF_FILE_BYTES_CACHE.pop(key, None)
            return None
        entry["at"] = time.time()
        return bytes(payload)


def remember_pdf_file_bytes(target: Path, payload: bytes) -> bytes:
    data = bytes(payload or b"")
    if not data or PDF_FILE_BYTES_CACHE_MAX_BYTES <= 0:
        return data
    if len(data) > PDF_FILE_BYTES_CACHE_MAX_FILE_BYTES or len(data) > PDF_FILE_BYTES_CACHE_MAX_BYTES:
        return data
    key = pdf_file_bytes_cache_key(target)
    with PDF_FILE_BYTES_CACHE_LOCK:
        PDF_FILE_BYTES_CACHE[key] = {"payload": data, "size": len(data), "at": time.time(), "path": str(target)}
        total = sum(int(item.get("size", 0) or 0) for item in PDF_FILE_BYTES_CACHE.values() if isinstance(item, dict))
        ordered = sorted(PDF_FILE_BYTES_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
        for old_key, old_entry in ordered:
            if len(PDF_FILE_BYTES_CACHE) <= PDF_FILE_BYTES_CACHE_MAX_ENTRIES and total <= PDF_FILE_BYTES_CACHE_MAX_BYTES:
                break
            total -= int(old_entry.get("size", 0) or 0)
            PDF_FILE_BYTES_CACHE.pop(old_key, None)
    return data


def open_pdf_document_cached(target: Path, fitz_module=None):
    if fitz_module is None:
        import fitz as fitz_module  # PyMuPDF
    payload = get_cached_pdf_file_bytes(target)
    if payload is not None:
        return fitz_module.open(stream=payload, filetype="pdf")
    try:
        size = int(target.stat().st_size)
    except Exception:
        size = 0
    if size > 0 and size <= PDF_FILE_BYTES_CACHE_MAX_FILE_BYTES and size <= PDF_FILE_BYTES_CACHE_MAX_BYTES:
        payload = remember_pdf_file_bytes(target, target.read_bytes())
        return fitz_module.open(stream=payload, filetype="pdf")
    return fitz_module.open(str(target))


def run_pdf_render_once(cache_key: str, label: str, render_fn) -> tuple[bytes, dict]:
    cached = get_cached_pdf_render(cache_key)
    if cached is not None:
        return cached
    owner = False
    with PDF_RENDER_CACHE_LOCK:
        cached = get_cached_pdf_render(cache_key)
        if cached is not None:
            return cached
        inflight = PDF_RENDER_INFLIGHT.get(cache_key)
        if not isinstance(inflight, dict):
            inflight = {"event": threading.Event(), "error": ""}
            PDF_RENDER_INFLIGHT[cache_key] = inflight
            owner = True
        event = inflight.get("event")
    if not owner:
        if isinstance(event, threading.Event):
            event.wait(timeout=PDF_RENDER_WORK_QUEUE.timeout_seconds + 5)
        cached = get_cached_pdf_render(cache_key)
        if cached is not None:
            return cached
        error_text = clean(inflight.get("error", "")) if isinstance(inflight, dict) else ""
        if error_text:
            raise RuntimeError(error_text)
        raise RuntimeError("PDF render is still busy. Please retry shortly.")
    try:
        render_started = time.perf_counter()
        data, meta = PDF_RENDER_WORK_QUEUE.run(
            label,
            render_fn,
            timeout=PDF_RENDER_WORK_QUEUE.timeout_seconds,
        )
        render_ms = int((time.perf_counter() - render_started) * 1000)
        if isinstance(meta, dict):
            meta.setdefault("render_ms", render_ms)
        remember_pdf_render(cache_key, data, meta, persist_disk=render_ms >= PDF_RENDER_DISK_CACHE_MIN_RENDER_MS)
        return data, meta
    except Exception as exc:
        with PDF_RENDER_CACHE_LOCK:
            row = PDF_RENDER_INFLIGHT.get(cache_key)
            if isinstance(row, dict):
                row["error"] = str(exc)
        raise
    finally:
        with PDF_RENDER_CACHE_LOCK:
            row = PDF_RENDER_INFLIGHT.pop(cache_key, None)
            event = row.get("event") if isinstance(row, dict) else None
            if isinstance(event, threading.Event):
                event.set()


def pdf_text_layer_summary(doc, sample_limit: int = 6) -> dict:
    try:
        page_count = int(getattr(doc, "page_count", 0) or len(doc) or 0)
    except Exception:
        page_count = 0
    sample_count = max(0, min(max(1, int(sample_limit or 6)), page_count))
    chars_by_page = []
    text_pages = 0
    total_chars = 0
    for index in range(sample_count):
        try:
            text = clean(doc.load_page(index).get_text("text") or "")
            chars = len(text)
        except Exception:
            chars = 0
        chars_by_page.append(chars)
        total_chars += chars
        if chars >= 20:
            text_pages += 1
    return {
        "sampled_pages": sample_count,
        "sample_chars": chars_by_page,
        "sample_text_pages": text_pages,
        "sample_text_chars": total_chars,
        "has_text_layer": bool(text_pages > 0),
    }


# Added 2026-07-05: returns file stats immediately so the browser can start ranged PDF chunks before heavy metadata parsing.
def pdf_document_quick_info(relative_path: str = "", username: str = "", admin: bool = False,
                            trusted_target: Path | None = None, metadata_alias_target: Path | None = None) -> dict:
    target = Path(trusted_target).resolve() if trusted_target is not None else safe_pdf_server_data_path(relative_path, username, admin=admin)
    stat = target.stat()
    cached = get_cached_pdf_picture_metadata("pdf", target) or {}
    # Updated 2026-07-22: canonical hash paths reuse the byte-identical legacy
    # metadata cache so quick opens never regress a known 185-page PDF to 1/1.
    if not cached and metadata_alias_target is not None:
        cached = get_cached_pdf_picture_metadata("pdf", Path(metadata_alias_target).resolve()) or {}
    if not cached:
        # Updated 2026-07-22: thin packages have no adjacent legacy PDF; reuse the revision-bound lesson metadata warmed from the canonical asset.
        lesson_meta = cached_lesson_file_metadata(target)
        lesson_pages = max(0, space_w_int(lesson_meta.get("nodes", 0), 0))
        if lesson_pages:
            cached = {
                "pages": lesson_pages,
                "title": clean(lesson_meta.get("title", "")),
            }
    first_page = cached.get("first_page") if isinstance(cached.get("first_page"), dict) else {}
    text_layer = cached.get("text_layer") if isinstance(cached.get("text_layer"), dict) else {}
    pages = max(1, space_w_int(cached.get("pages", 1), 1))
    return {
        "path": server_data_relative(target),
        "name": target.name,
        "title": clean(cached.get("title", "")) or target.stem,
        "pages": pages,
        "size": int(stat.st_size),
        "mtime": int(stat.st_mtime),
        "file_etag": public_file_etag(target, "pdf-file"),
        "first_page": first_page if first_page else {"width": 0, "height": 0},
        "text_layer": text_layer,
        "has_text_layer": bool(cached.get("has_text_layer", False)),
        "ghost_eye_ready": bool(resolve_tesseract_cmd()),
        "quick": True,
    }


def pdf_document_info(relative_path: str = "", username: str = "", admin: bool = False,
                      trusted_target: Path | None = None, metadata_alias_target: Path | None = None) -> dict:
    target = Path(trusted_target).resolve() if trusted_target is not None else safe_pdf_server_data_path(relative_path, username, admin=admin)
    cached = get_cached_pdf_picture_metadata("pdf", target)
    if cached is None and metadata_alias_target is not None:
        cached = get_cached_pdf_picture_metadata("pdf", Path(metadata_alias_target).resolve())
    if cached is not None:
        cached["ghost_eye_ready"] = bool(resolve_tesseract_cmd())
        try:
            stat = target.stat()
            cached["size"] = int(stat.st_size)
            cached["mtime"] = int(stat.st_mtime)
            cached["file_etag"] = public_file_etag(target, "pdf-file")
        except Exception:
            pass
        return cached
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise RuntimeError("May chu chua co PyMuPDF de mo PDF.") from exc
    doc = open_pdf_document_cached(target, fitz)
    try:
        page_count = int(getattr(doc, "page_count", 0) or len(doc) or 0)
        meta = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
        title = clean(meta.get("title", "")) or target.stem
        first_size = {"width": 0, "height": 0}
        if page_count:
            rect = doc.load_page(0).rect
            first_size = {"width": float(rect.width), "height": float(rect.height)}
        text_layer = pdf_text_layer_summary(doc)
        info = {
            "path": server_data_relative(target),
            "name": target.name,
            "title": title,
            "pages": page_count,
            "size": int(target.stat().st_size),
            "mtime": int(target.stat().st_mtime),
            "file_etag": public_file_etag(target, "pdf-file"),
            "first_page": first_size,
            "text_layer": text_layer,
            "has_text_layer": bool(text_layer.get("has_text_layer")),
            "ghost_eye_ready": bool(resolve_tesseract_cmd()),
        }
        remember_pdf_picture_metadata("pdf", target, info)
        return info
    finally:
        try:
            doc.close()
        except Exception:
            pass


def render_pdf_page_png(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, zoom: object = 2.0, trusted_target: Path | None = None) -> tuple[bytes, dict]:
    target = Path(trusted_target).resolve() if trusted_target is not None else safe_pdf_server_data_path(relative_path, username, admin=admin)
    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        raise RuntimeError("May chu chua co PyMuPDF de render PDF.") from exc
    cached_info = get_cached_pdf_picture_metadata("pdf", target) or {}
    page_count_hint = int(cached_info.get("pages", 0) or 0)
    try:
        requested_page = int(page)
    except Exception:
        requested_page = 1
    index = pdf_page_index(requested_page, page_count_hint) if page_count_hint > 0 else max(0, requested_page - 1)
    zoom_value = pdf_render_zoom(zoom)
    cache_key = pdf_render_cache_key(target, index, zoom_value)

    def render_uncached_page() -> tuple[bytes, dict]:
        worker_doc = open_pdf_document_cached(target, fitz)
        try:
            page_count = int(getattr(worker_doc, "page_count", 0) or len(worker_doc) or 0)
            if page_count <= 0:
                raise RuntimeError("PDF khong co trang nao.")
            safe_index = max(0, min(page_count - 1, index))
            page_obj = worker_doc.load_page(safe_index)
            page_image = render_single_embedded_pdf_page_image(worker_doc, page_obj, zoom_value)
            if page_image is not None:
                try:
                    data = encode_pdf_pil_png(page_image)
                    width, height = page_image.size
                    encoder = "png-single-scan-auto-tone"
                finally:
                    try:
                        page_image.close()
                    except Exception:
                        pass
            else:
                try:
                    pix = page_obj.get_pixmap(matrix=fitz.Matrix(zoom_value, zoom_value), colorspace=fitz.csRGB, alpha=False)
                except TypeError:
                    pix = page_obj.get_pixmap(matrix=fitz.Matrix(zoom_value, zoom_value), alpha=False)
                data = encode_pdf_pixmap_png(pix)
                width, height = int(pix.width), int(pix.height)
                encoder = "png-lossless-fast-auto-tone"
            meta = {
                "page": safe_index + 1,
                "pages": page_count,
                "zoom": zoom_value,
                "width": int(width),
                "height": int(height),
                "encoder": encoder,
                "cache_hit": False,
            }
            return data, meta
        finally:
            try:
                worker_doc.close()
            except Exception:
                pass

    return run_pdf_render_once(cache_key, f"pdf-page:{index + 1}", render_uncached_page)


def start_pdf_page_prewarm(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, zoom: object = 3.2, delay: float = 0.0) -> None:
    rel_path = clean_path_value(relative_path)
    if not rel_path:
        return
    try:
        zoom_value = pdf_render_zoom(zoom)
        page_value = int(float(page))
        if page_value < 1:
            return
    except Exception:
        page_value = 1
        zoom_value = 3.2

    def _worker() -> None:
        if delay > 0:
            time.sleep(max(0.0, min(2.5, float(delay))))
        try:
            started = time.perf_counter()
            data, meta = render_pdf_page_png(rel_path, username, admin=admin, page=page_value, zoom=zoom_value)
            stt_debug_log(
                "pdf_page_prewarm_done",
                path=rel_path,
                username=username,
                page=meta.get("page", page_value),
                zoom=meta.get("zoom", zoom_value),
                bytes=len(data),
                ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            stt_debug_log("pdf_page_prewarm_failed", path=rel_path, username=username, page=page_value, zoom=zoom_value, error=str(exc))

    threading.Thread(target=_worker, name=f"pdf-prewarm-{uuid.uuid4().hex[:8]}", daemon=True).start()


def start_pdf_page_prewarm_window(
    relative_path: str = "",
    username: str = "",
    admin: bool = False,
    center_page: object = 1,
    zoom: object = 3.2,
    include_current: bool = True,
    max_pages: object = 0,
) -> None:
    rel_path = clean_path_value(relative_path)
    if not rel_path:
        return
    try:
        center = int(float(center_page))
    except Exception:
        center = 1
    center = max(1, center)
    try:
        page_limit = max(0, int(float(max_pages or 0)))
    except Exception:
        page_limit = 0
    offsets = [
        (0, 0.0),
        (1, 0.25),
        (-1, 0.45),
        (2, 0.75),
        (-2, 1.05),
    ]
    seen: set[int] = set()
    for offset, delay in offsets:
        if offset == 0 and not include_current:
            continue
        page_value = center + offset
        if page_value < 1 or (page_limit and page_value > page_limit) or page_value in seen:
            continue
        seen.add(page_value)
        start_pdf_page_prewarm(rel_path, username, admin=admin, page=page_value, zoom=zoom, delay=delay)


def pdf_picture_metadata_warm_candidates(max_items: int = 240) -> list[tuple[str, str]]:
    pdf_rows: list[tuple[str, str]] = []
    picture_rows: list[tuple[str, str]] = []
    seen_picture_folders: set[str] = set()
    skip_tops = server_data_manifest_skip_tops()
    try:
        # Added 2026-07-16: use the RAM server-data manifest; rglob on the whole tree made startup warm CPU-heavy.
        manifest = get_server_data_manifest(force=False)
        folders = manifest.get("folders") if isinstance(manifest, dict) else {}
        if not isinstance(folders, dict):
            return []
        for folder_key in sorted(folders.keys(), key=lambda value: (str(value).count("/"), str(value).lower())):
            if len(pdf_rows) + len(picture_rows) >= max_items:
                break
            rows = folders.get(folder_key)
            if not isinstance(rows, list):
                continue
            for entry in rows:
                if len(pdf_rows) + len(picture_rows) >= max_items:
                    break
                if not isinstance(entry, dict) or clean(entry.get("type", "")) != "file":
                    continue
                rel = clean_path_value(entry.get("path", ""))
                if not rel:
                    continue
                top = rel.split("/", 1)[0]
                if top in skip_tops:
                    continue
                suffix = clean(entry.get("extension", "")).lower()
                if suffix == ".pdf":
                    pdf_rows.append(("pdf", rel))
                    continue
                if suffix in IMAGE_FILE_SUFFIXES:
                    parent_key = clean_path_value(rel.rsplit("/", 1)[0]).lower() if "/" in rel else ""
                    if parent_key and parent_key not in seen_picture_folders:
                        seen_picture_folders.add(parent_key)
                        picture_rows.append(("picture", rel))
    except Exception:
        return pdf_rows + picture_rows
    return (pdf_rows + picture_rows)[:max_items]


def warm_pdf_picture_metadata_index(max_items: int = 240) -> None:
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        if PDF_PICTURE_METADATA_WARM_STATE.get("running"):
            return
        PDF_PICTURE_METADATA_WARM_STATE.update({"started": True, "running": True, "done": 0, "failed": 0, "last": "", "error": ""})
    try:
        pdf_picture_metadata_index_load()
        rows = pdf_picture_metadata_warm_candidates(max_items=max_items)
        for kind, rel in rows:
            try:
                PDF_PICTURE_METADATA_WARM_STATE["last"] = rel
                warm_username = clean(rel.split("/", 1)[0]) or "common"
                if kind == "pdf":
                    target = safe_pdf_server_data_path(rel, warm_username, admin=False)
                    if get_cached_pdf_picture_metadata("pdf", target) is None:
                        pdf_document_info(rel, warm_username, admin=False)
                else:
                    target = safe_picture_server_data_path(rel, warm_username, admin=False)
                    if get_cached_pdf_picture_metadata("picture", target, include_parent=True) is None:
                        picture_document_info(rel, warm_username, admin=False)
                PDF_PICTURE_METADATA_WARM_STATE["done"] = int(PDF_PICTURE_METADATA_WARM_STATE.get("done", 0) or 0) + 1
                time.sleep(0.015)
            except Exception as exc:
                PDF_PICTURE_METADATA_WARM_STATE["failed"] = int(PDF_PICTURE_METADATA_WARM_STATE.get("failed", 0) or 0) + 1
                PDF_PICTURE_METADATA_WARM_STATE["error"] = str(exc)
        with PDF_PICTURE_METADATA_INDEX_LOCK:
            pdf_picture_metadata_index_save_locked()
        stt_debug_log(
            "pdf_picture_metadata_warm_done",
            done=PDF_PICTURE_METADATA_WARM_STATE.get("done", 0),
            failed=PDF_PICTURE_METADATA_WARM_STATE.get("failed", 0),
        )
        print(
            f"PDF/Picture metadata index ready: {PDF_PICTURE_METADATA_WARM_STATE.get('done', 0)} warmed, {PDF_PICTURE_METADATA_WARM_STATE.get('failed', 0)} failed.",
            flush=True,
        )
    except Exception as exc:
        PDF_PICTURE_METADATA_WARM_STATE["error"] = str(exc)
        stt_debug_log("pdf_picture_metadata_warm_failed", error=str(exc))
    finally:
        PDF_PICTURE_METADATA_WARM_STATE["running"] = False


def start_pdf_picture_metadata_warmer(max_items: int = 240, *, force: bool = False) -> None:
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        if PDF_PICTURE_METADATA_WARM_STATE.get("started") and not force:
            return
        if force:
            PDF_PICTURE_METADATA_WARM_STATE["started"] = False
    print(f"Starting PDF/Picture metadata index warm in background ({int(max_items or 0)} candidates) ...", flush=True)
    thread = threading.Thread(target=lambda: warm_pdf_picture_metadata_index(max_items=max_items), name="pdf-picture-metadata-warm", daemon=True)
    thread.start()


# Added 2026-07-16: trust a valid boot snapshot so startup does not reopen PDFs/images just to rebuild an already-valid metadata index.
def use_pdf_picture_metadata_boot_snapshot() -> bool:
    if not future_boot_snapshot_cache_usable("pdf_picture_metadata"):
        return False
    pdf_picture_metadata_index_load()
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        items = PDF_PICTURE_METADATA_INDEX.get("items") if isinstance(PDF_PICTURE_METADATA_INDEX.get("items"), dict) else {}
        item_count = len(items)
        if item_count <= 0:
            return False
        PDF_PICTURE_METADATA_WARM_STATE.update({
            "started": True,
            "running": False,
            "done": item_count,
            "failed": 0,
            "last": "boot_snapshot",
            "error": "",
            "source": "boot_snapshot",
        })
    print(f"PDF/Picture metadata index ready from boot snapshot: {item_count} cached.", flush=True)
    return True


def pdf_picture_metadata_status() -> dict:
    pdf_picture_metadata_index_load()
    with PDF_PICTURE_METADATA_INDEX_LOCK:
        items = PDF_PICTURE_METADATA_INDEX.get("items") if isinstance(PDF_PICTURE_METADATA_INDEX.get("items"), dict) else {}
        pdf_count = sum(1 for key in items if str(key).startswith("pdf:"))
        picture_count = sum(1 for key in items if str(key).startswith("picture:"))
        return {
            "index_file": str(PDF_PICTURE_METADATA_INDEX_FILE),
            "items": len(items),
            "pdf": pdf_count,
            "picture": picture_count,
            "warm": dict(PDF_PICTURE_METADATA_WARM_STATE),
            "loaded": bool(PDF_PICTURE_METADATA_INDEX.get("loaded")),
        }
