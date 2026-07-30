# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def resolve_tesseract_cmd() -> str:
    with TESSERACT_CMD_CACHE_LOCK:
        if TESSERACT_CMD_CACHE.get("checked"):
            cached_path = clean(TESSERACT_CMD_CACHE.get("path", ""))
            if cached_path and "pytesseract" in sys.modules:
                try:
                    pytesseract = sys.modules["pytesseract"]
                    pytesseract.pytesseract.tesseract_cmd = cached_path
                except Exception:
                    pass
            return cached_path
    probe_paths = []
    for env_name in ("QMLEARN_TESSERACT", "TESSERACT_CMD"):
        env_value = clean(os.environ.get(env_name, ""))
        if env_value:
            probe_paths.append(env_value)
    probe_paths.extend([
        shutil.which("tesseract") or "",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ])
    for candidate in probe_paths:
        path = clean(candidate)
        if path and Path(path).is_file():
            if "pytesseract" in sys.modules:
                try:
                    pytesseract = sys.modules["pytesseract"]
                    pytesseract.pytesseract.tesseract_cmd = path
                except Exception:
                    pass
            with TESSERACT_CMD_CACHE_LOCK:
                TESSERACT_CMD_CACHE.update({"checked": True, "path": path})
            return path
    try:
        import pytesseract
    except Exception:
        with TESSERACT_CMD_CACHE_LOCK:
            TESSERACT_CMD_CACHE.update({"checked": True, "path": ""})
        return ""
    current = clean(getattr(getattr(pytesseract, "pytesseract", pytesseract), "tesseract_cmd", ""))
    if current and Path(current).is_file():
        with TESSERACT_CMD_CACHE_LOCK:
            TESSERACT_CMD_CACHE.update({"checked": True, "path": current})
        return current
    for candidate in probe_paths:
        path = clean(candidate)
        if path and Path(path).is_file():
            try:
                pytesseract.pytesseract.tesseract_cmd = path
            except Exception:
                pass
            with TESSERACT_CMD_CACHE_LOCK:
                TESSERACT_CMD_CACHE.update({"checked": True, "path": path})
            return path
    with TESSERACT_CMD_CACHE_LOCK:
        TESSERACT_CMD_CACHE.update({"checked": True, "path": ""})
    return ""


def normalize_pdf_region_rect(rect_payload: object) -> dict:
    rect = rect_payload if isinstance(rect_payload, dict) else {}
    def _num(name: str, default: float = 0.0) -> float:
        try:
            return float(rect.get(name, default))
        except Exception:
            return default
    x = max(0.0, min(1.0, _num("x")))
    y = max(0.0, min(1.0, _num("y")))
    w = max(0.0, min(1.0, _num("w", _num("width"))))
    h = max(0.0, min(1.0, _num("h", _num("height"))))
    if x + w > 1.0:
        w = max(0.0, 1.0 - x)
    if y + h > 1.0:
        h = max(0.0, 1.0 - y)
    if w < 0.002 or h < 0.002:
        raise RuntimeError("Vung chon qua nho de Ghost Eye doc ro.")
    return {"x": x, "y": y, "w": w, "h": h}


def pdf_ocr_clean_candidate_text(value: object = "") -> str:
    text = clean(value)
    if not text:
        return ""
    lines = []
    for raw_line in re.split(r"[\r\n]+", text):
        line = clean(raw_line)
        if not line:
            continue
        letters = len(re.findall(r"[A-Za-zÀ-ỹ]", line, flags=re.UNICODE))
        symbols = len(re.findall(r"[^A-Za-zÀ-ỹ0-9\s.,!?;:'\"()/\\-]", line, flags=re.UNICODE))
        tokens = re.findall(r"[A-Za-zÀ-ỹ]{1,}(?:['’][A-Za-zÀ-ỹ]+)?", line, flags=re.UNICODE)
        validish = 0
        for token in tokens:
            key = clean(token).lower().replace("’", "'").strip("'")
            if key in COMMON_ENGLISH_CHAT_WORDS or len(key) >= 3:
                validish += 1
        if letters <= 0:
            continue
        if symbols > max(4, letters * 0.55) and validish < 2:
            continue
        if len(tokens) <= 1 and len(line) <= 2 and line.lower() not in {"i", "a"}:
            continue
        line = re.sub(r"^[^A-Za-zÀ-ỹ0-9]+", "", line, flags=re.UNICODE)
        line = re.sub(r"[^A-Za-zÀ-ỹ0-9.!?,'\")]+$", "", line, flags=re.UNICODE)
        if clean(line):
            lines.append(clean(line))
    return clean("\n".join(lines))


def pdf_ocr_raw_candidate_text(value: object = "") -> str:
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join([line for line in lines if line]).strip()


def pdf_ocr_candidate_score(value: object = "", qmdict: dict | None = None) -> float:
    text = pdf_ocr_clean_candidate_text(value)
    if not text:
        return -9999.0
    tokens = re.findall(r"[A-Za-zÀ-ỹ]{1,}(?:['’][A-Za-zÀ-ỹ]+)?", text, flags=re.UNICODE)
    if not tokens:
        return -9999.0
    valid = 0
    short_noise = 0
    for token in tokens:
        key = clean(token).lower().replace("’", "'").strip("'")
        if key in COMMON_ENGLISH_CHAT_WORDS:
            valid += 1
            continue
        if qmdict and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", key):
            try:
                if shared_world_chat_token_valid(key, qmdict):
                    valid += 1
                    continue
            except Exception:
                pass
        if len(key) <= 2 and key not in {"i", "a"}:
            short_noise += 1
    letters = len(re.findall(r"[A-Za-zÀ-ỹ]", text, flags=re.UNICODE))
    symbol_noise = len(re.findall(r"[^A-Za-zÀ-ỹ0-9\s.,!?;:'\"()/\\-]", text, flags=re.UNICODE))
    lines = max(1, len([line for line in text.splitlines() if clean(line)]))
    valid_ratio = valid / max(1, len(tokens))
    return (valid * 14.0) + (valid_ratio * 20.0) + (letters * 0.12) - (short_noise * 4.5) - (symbol_noise * 1.8) - max(0, lines - 5) * 1.5


def pdf_ocr_raw_text_from_word_data(data: object = None) -> str:
    source = data if isinstance(data, dict) else {}
    texts = source.get("text") if isinstance(source.get("text"), list) else []
    line_nums = source.get("line_num") if isinstance(source.get("line_num"), list) else []
    block_nums = source.get("block_num") if isinstance(source.get("block_num"), list) else []
    par_nums = source.get("par_num") if isinstance(source.get("par_num"), list) else []
    rows: list[tuple[tuple[int, int, int], str]] = []
    for index, raw_text in enumerate(texts):
        token = pdf_ocr_raw_candidate_text(raw_text)
        if not token:
            continue
        try:
            line_key = (
                int(block_nums[index]) if index < len(block_nums) else 0,
                int(par_nums[index]) if index < len(par_nums) else 0,
                int(line_nums[index]) if index < len(line_nums) else 0,
            )
        except Exception:
            line_key = (0, 0, 0)
        rows.append((line_key, token))
    if not rows:
        return ""
    lines: list[str] = []
    current_key = rows[0][0]
    current: list[str] = []
    for line_key, token in rows:
        if line_key != current_key and current:
            lines.append(" ".join(current))
            current = []
            current_key = line_key
        current.append(token)
    if current:
        lines.append(" ".join(current))
    return pdf_ocr_raw_candidate_text("\n".join(lines))


def pdf_ocr_text_from_word_data(data: object = None, qmdict: dict | None = None) -> str:
    source = data if isinstance(data, dict) else {}
    texts = source.get("text") if isinstance(source.get("text"), list) else []
    confs = source.get("conf") if isinstance(source.get("conf"), list) else []
    line_nums = source.get("line_num") if isinstance(source.get("line_num"), list) else []
    block_nums = source.get("block_num") if isinstance(source.get("block_num"), list) else []
    par_nums = source.get("par_num") if isinstance(source.get("par_num"), list) else []
    rows: list[tuple[tuple[int, int, int], str]] = []
    for index, raw_text in enumerate(texts):
        token = clean(raw_text)
        if not token:
            continue
        try:
            conf = float(confs[index])
        except Exception:
            conf = -1.0
        token = token.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
        letters = re.findall(r"[A-Za-zÀ-ỹ]", token, flags=re.UNICODE)
        if not letters:
            continue
        surface = re.sub(r"^[^A-Za-zÀ-ỹ0-9]+|[^A-Za-zÀ-ỹ0-9.,!?'\"]+$", "", token, flags=re.UNICODE)
        key = clean(surface).lower().strip(".,!?;:'\"()[]{}")
        key = key.replace("’", "'")
        if not key:
            continue
        common = key in COMMON_ENGLISH_CHAT_WORDS
        valid_word = common
        if not valid_word and qmdict and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", key):
            try:
                valid_word = shared_world_chat_token_valid(key, qmdict)
            except Exception:
                valid_word = False
        if conf < 55 and not (valid_word and conf >= 38):
            continue
        if len(key) <= 1 and key not in {"i", "a"}:
            continue
        if len(key) <= 2 and not valid_word and conf < 78:
            continue
        try:
            line_key = (
                int(block_nums[index]) if index < len(block_nums) else 0,
                int(par_nums[index]) if index < len(par_nums) else 0,
                int(line_nums[index]) if index < len(line_nums) else 0,
            )
        except Exception:
            line_key = (0, 0, 0)
        rows.append((line_key, surface))
    if not rows:
        return ""
    lines: list[str] = []
    current_key = rows[0][0]
    current: list[str] = []
    for line_key, token in rows:
        if line_key != current_key and current:
            lines.append(" ".join(current))
            current = []
            current_key = line_key
        current.append(token)
    if current:
        lines.append(" ".join(current))
    return pdf_ocr_clean_candidate_text("\n".join(lines))


def ocr_pil_image_text_direct(image, lang: str = "eng+vie") -> str:
    try:
        import pytesseract
        from PIL import ImageOps
    except Exception as exc:
        raise RuntimeError("Ghost Eye chua san sang tren may chu.") from exc
    if not resolve_tesseract_cmd():
        raise RuntimeError("Ghost Eye chua san sang tren may chu.")
    image = image.convert("RGB")
    width, height = image.size
    longest = max(width, height)
    if longest and longest < 1600:
        scale = 1600.0 / float(longest)
        image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))
    gray = ImageOps.autocontrast(ImageOps.grayscale(image))
    variants = []
    try:
        variants.append(("binary", gray.point(lambda pixel: 255 if pixel > 170 else 0)))
    except Exception:
        pass
    variants.append(("gray", gray))
    base_lang = clean(lang) or "eng+vie"
    lang_candidates = []
    if "eng" in base_lang.lower() and base_lang.lower() != "eng":
        lang_candidates.append("eng")
    lang_candidates.append(base_lang)
    lang_candidates = list(dict.fromkeys(lang_candidates))
    psm_values = [11, 6, 7]
    try:
        _runtime, qmdict = qmdict_runtime_and_dict()
    except Exception:
        qmdict = {}
    best_text = ""
    best_score = -9999.0
    for _variant_name, variant in variants:
        for ocr_lang in lang_candidates:
            for psm in psm_values:
                try:
                    word_data = pytesseract.image_to_data(
                        variant,
                        config=f"--oem 3 --psm {psm}",
                        lang=ocr_lang,
                        output_type=pytesseract.Output.DICT,
                    )
                except Exception:
                    word_data = None
                data_raw_text = pdf_ocr_raw_text_from_word_data(word_data)
                data_text = pdf_ocr_text_from_word_data(word_data, qmdict)
                data_score = pdf_ocr_candidate_score(data_text or data_raw_text, qmdict) + 8.0
                if data_score > best_score:
                    best_score = data_score
                    best_text = data_raw_text or data_text
                if (data_raw_text or data_text) and data_score >= 48.0:
                    return pdf_ocr_raw_candidate_text(data_raw_text or data_text)
                if (data_raw_text or data_text) and data_score >= 42.0 and len(re.findall(r"[A-Za-zÀ-ỹ]", data_text or data_raw_text, flags=re.UNICODE)) >= 12:
                    return pdf_ocr_raw_candidate_text(data_raw_text or data_text)
                try:
                    raw_text = pytesseract.image_to_string(
                        variant,
                        config=f"--oem 3 --psm {psm}",
                        lang=ocr_lang,
                    )
                except Exception:
                    continue
                raw_candidate = pdf_ocr_raw_candidate_text(raw_text)
                cleaned = pdf_ocr_clean_candidate_text(raw_text)
                score = pdf_ocr_candidate_score(cleaned, qmdict)
                if score > best_score:
                    best_score = score
                    best_text = raw_candidate or cleaned
                if cleaned and score >= 48.0:
                    return pdf_ocr_raw_candidate_text(raw_candidate or cleaned)
    return pdf_ocr_raw_candidate_text(best_text)


def ocr_pil_image_text(image, lang: str = "eng+vie") -> str:
    return GHOST_EYE_WORK_QUEUE.run(
        "ghost-eye-read",
        lambda: ocr_pil_image_text_direct(image, lang=lang),
        timeout=GHOST_EYE_WORK_QUEUE.timeout_seconds,
    )


def pdf_text_layer_is_useful(text: str = "", region: dict | None = None) -> bool:
    source = clean(text)
    if not source:
        return False
    data = region if isinstance(region, dict) else {}
    try:
        area = max(0.0, float(data.get("w", 0.0) or 0.0) * float(data.get("h", 0.0) or 0.0))
    except Exception:
        area = 0.0
    # Small selected regions may legitimately contain only one word. Full-page
    # scans often include a tiny watermark text layer over an image-only page.
    if area and area < 0.35:
        return True
    without_urls = re.sub(r"\b(?:https?://|www\.)\S+", " ", source, flags=re.I)
    words = re.findall(r"[A-Za-zÀ-ỹ]{2,}(?:[-'][A-Za-zÀ-ỹ]+)?", without_urls, flags=re.UNICODE)
    if len(words) >= 6:
        return True
    return len(clean(without_urls)) >= 80


def pdf_text_similarity_key(value: str = "") -> str:
    return re.sub(r"[^0-9a-zà-ỹ]+", "", clean(value).lower(), flags=re.UNICODE)


def pdf_merge_text_sources(text_layer: str = "", ghost_eye_text: str = "", text_layer_useful: bool = False) -> str:
    layer = clean(text_layer)
    ghost = clean(ghost_eye_text)
    if not layer:
        return ghost
    if not ghost:
        return layer
    layer_key = pdf_text_similarity_key(layer)
    ghost_key = pdf_text_similarity_key(ghost)
    if not layer_key:
        return ghost
    if not ghost_key:
        return layer
    if layer_key == ghost_key:
        return layer if text_layer_useful else ghost
    if layer_key in ghost_key:
        return ghost
    if ghost_key in layer_key:
        return layer
    similarity_score = difflib.SequenceMatcher(None, layer_key[:6000], ghost_key[:6000]).ratio()
    if similarity_score >= 0.88:
        # Same content through two engines. Prefer the digital source if it is
        # actually useful; otherwise keep the image result because OCR probably
        # contains the page body while the text layer only has a watermark.
        return layer if text_layer_useful and len(layer_key) >= len(ghost_key) * 0.72 else ghost
    first = layer if text_layer_useful else ghost
    second = ghost if text_layer_useful else layer
    return clean(f"{first}\n\n{second}")


def ocr_pdf_region(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, rect: object = None, zoom: object = 2.4) -> dict:
    target = safe_pdf_server_data_path(relative_path, username, admin=admin)
    region = normalize_pdf_region_rect(rect)
    try:
        import fitz  # PyMuPDF
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("May chu chua co thu vien doc PDF.") from exc
    doc = open_pdf_document_cached(target, fitz)
    try:
        page_count = int(getattr(doc, "page_count", 0) or len(doc) or 0)
        if page_count <= 0:
            raise RuntimeError("PDF khong co trang nao.")
        index = pdf_page_index(page, page_count)
        page_obj = doc.load_page(index)
        page_rect = page_obj.rect
        clip = fitz.Rect(
            page_rect.x0 + (region["x"] * page_rect.width),
            page_rect.y0 + (region["y"] * page_rect.height),
            page_rect.x0 + ((region["x"] + region["w"]) * page_rect.width),
            page_rect.y0 + ((region["y"] + region["h"]) * page_rect.height),
        )
        text_layer = clean(page_obj.get_text("text", clip=clip) or "")
        text_layer_useful = pdf_text_layer_is_useful(text_layer, region)
        ocr_text = ""
        ocr_error = ""
        try:
            zoom_value = pdf_render_zoom(zoom)
            try:
                rendered_page_payload, rendered_page_meta = render_pdf_page_png(
                    server_data_relative(target),
                    username,
                    admin=admin,
                    page=index + 1,
                    zoom=zoom_value,
                )
                page_image = Image.open(io.BytesIO(rendered_page_payload)).convert("RGB")
                try:
                    page_width, page_height = page_image.size
                    left = int(max(0, min(page_width, region["x"] * page_width)))
                    top = int(max(0, min(page_height, region["y"] * page_height)))
                    right = int(max(left + 1, min(page_width, (region["x"] + region["w"]) * page_width)))
                    bottom = int(max(top + 1, min(page_height, (region["y"] + region["h"]) * page_height)))
                    crop = page_image.crop((left, top, right, bottom))
                    crop.load()
                    crop_source = clean(rendered_page_meta.get("encoder", "")) or "rendered-page"
                finally:
                    try:
                        page_image.close()
                    except Exception:
                        pass
            except Exception:
                page_image = render_single_embedded_pdf_page_image(doc, page_obj, zoom_value)
                if page_image is not None:
                    try:
                        page_width, page_height = page_image.size
                        left = int(max(0, min(page_width, region["x"] * page_width)))
                        top = int(max(0, min(page_height, region["y"] * page_height)))
                        right = int(max(left + 1, min(page_width, (region["x"] + region["w"]) * page_width)))
                        bottom = int(max(top + 1, min(page_height, (region["y"] + region["h"]) * page_height)))
                        crop = page_image.crop((left, top, right, bottom))
                        crop.load()
                        crop_source = "single-scan-fallback"
                    finally:
                        try:
                            page_image.close()
                        except Exception:
                            pass
                else:
                    try:
                        pix = page_obj.get_pixmap(matrix=fitz.Matrix(zoom_value, zoom_value), colorspace=fitz.csRGB, alpha=False, clip=clip)
                    except TypeError:
                        pix = page_obj.get_pixmap(matrix=fitz.Matrix(zoom_value, zoom_value), alpha=False, clip=clip)
                    crop = correct_pdf_negative_scan_image(pdf_pixmap_to_rgb_image(pix))
                    crop_source = "clip-fallback"
            ocr_text = ocr_pil_image_text(crop)
        except Exception as exc:
            raw_error = clean(str(exc))
            stt_debug_log(
                "pdf_ocr_engine_failed",
                path=server_data_relative(target),
                username=username,
                page=index + 1,
                rect=region,
                zoom=zoom,
                clip=f"{clip.x0:.1f},{clip.y0:.1f},{clip.x1:.1f},{clip.y1:.1f}",
                crop_source=locals().get("crop_source", ""),
                crop_pixels=f"{locals().get('left', '')},{locals().get('top', '')},{locals().get('right', '')},{locals().get('bottom', '')}",
                error=raw_error,
            )
            ocr_error = "Ghost Eye could not read this region. Try a clearer or larger selection." if re.search(r"tesseract|ocr", raw_error, re.I) else raw_error
        final_text = pdf_merge_text_sources(text_layer, ocr_text, text_layer_useful=text_layer_useful)
        if not final_text and ocr_error:
            raise RuntimeError(ocr_error)
        if not final_text:
            raise RuntimeError("Khong nhan dien duoc text trong vung da chon.")
        stt_debug_log(
            "pdf_ocr_done",
            path=server_data_relative(target),
            username=username,
            page=index + 1,
            rect=region,
            zoom=zoom,
            text_len=len(final_text),
            text_layer_len=len(text_layer),
            ghost_eye_len=len(ocr_text),
            crop=locals().get("crop_source", ""),
            crop_pixels=f"{locals().get('left', '')},{locals().get('top', '')},{locals().get('right', '')},{locals().get('bottom', '')}",
            engine="hybrid-source" if text_layer and ocr_text else ("ghost-eye" if ocr_text else "digital-source"),
        )
        return {
            "path": server_data_relative(target),
            "page": index + 1,
            "pages": page_count,
            "rect": region,
            "text": final_text,
            "text_layer": text_layer,
            "ghost_eye_text": ocr_text,
            "ghost_eye_error": ocr_error,
            "engine": "hybrid-source" if text_layer and ocr_text else ("ghost-eye" if ocr_text else "digital-source"),
            "ghost_eye_ready": bool(resolve_tesseract_cmd()),
        }
    finally:
        try:
            doc.close()
        except Exception:
            pass


def ocr_picture_region(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, rect: object = None) -> dict:
    target, siblings, index = picture_target_for_page(relative_path, username, admin=admin, page=page)
    region = normalize_pdf_region_rect(rect)
    image = open_picture_image(target)
    try:
        width, height = image.size
        left = int(max(0, min(width, region["x"] * width)))
        top = int(max(0, min(height, region["y"] * height)))
        right = int(max(left + 1, min(width, (region["x"] + region["w"]) * width)))
        bottom = int(max(top + 1, min(height, (region["y"] + region["h"]) * height)))
        crop = image.crop((left, top, right, bottom))
        try:
            text = ocr_pil_image_text(crop)
        finally:
            try:
                crop.close()
            except Exception:
                pass
        if not text:
            raise RuntimeError("Khong nhan dien duoc text trong vung da chon.")
        stt_debug_log(
            "picture_ocr_done",
            path=server_data_relative(target),
            username=username,
            page=index + 1,
            rect=region,
            crop=f"{left},{top},{right},{bottom}",
            text_len=len(text),
        )
        return {
            "path": server_data_relative(target),
            "page": index + 1,
            "pages": len(siblings),
            "rect": region,
            "text": text,
            "text_layer": "",
            "ghost_eye_text": text,
            "ghost_eye_error": "",
            "engine": "ghost-eye",
            "ghost_eye_ready": bool(resolve_tesseract_cmd()),
        }
    finally:
        try:
            image.close()
        except Exception:
            pass


def picture_scan_vocabulary(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1) -> dict:
    result = ocr_picture_region(
        relative_path,
        username,
        admin=admin,
        page=page,
        rect={"x": 0, "y": 0, "w": 1, "h": 1},
    )
    text = clean(result.get("text", ""))
    return {
        **result,
        "text": text,
        "vocabulary": qmdict_vocabulary_stats_queued(text, username),
    }


def sanitize_pdf_voice_text(text: str = "", limit: int = 1400) -> str:
    raw = lesson_task_notice_text(text, limit=max(1, int(limit or 1400)))
    kept = []
    last_space = False
    for char in raw:
        if char.isalnum() or char in {"?", "!", "."}:
            kept.append(char)
            last_space = False
        elif char.isspace():
            if not last_space:
                kept.append(" ")
                last_space = True
        else:
            if not last_space:
                kept.append(" ")
                last_space = True
    return re.sub(r"\s+", " ", "".join(kept)).strip()


def pdf_vocab_word_key(value: object = "") -> str:
    text = clean(value).replace("’", "'").replace("`", "'").replace("´", "'").lower()
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def pdf_vocab_item_summary(item: object = None, surface: str = "") -> dict:
    source = item if isinstance(item, dict) else {}
    word = clean(source.get("word", ""))
    if not word:
        return {}
    examples = source.get("examples", [])
    if isinstance(examples, str):
        try:
            decoded_examples = json.loads(examples)
            examples = decoded_examples
        except Exception:
            examples = [examples] if clean(examples) else []
    return {
        "word": word,
        "surface": clean(surface),
        "meaning": clean(source.get("meaning", "")),
        "pron": clean(source.get("pron", "")),
        "type": clean(source.get("type", "")),
        "pron_us": clean(source.get("pron_us", "")),
        "pron_uk": clean(source.get("pron_uk", "")),
        "usage": clean(source.get("usage", "")),
        "examples": word_agent_clean_examples(examples),
    }


def qmdict_runtime_module():
    configure_paths()
    from module_main.QM_GATE import viewer_vocab_runtime as vocab_runtime  # noqa: PLC0415

    return vocab_runtime


def qmdict_source_signature() -> dict:
    try:
        stat = QMDICT_SOURCE_FILE.stat()
        return {"mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}
    except Exception as exc:
        return {"mtime_ns": 0, "size": -1, "error": str(exc)}


def qmdict_source_signature_key() -> tuple[int, int]:
    signature = qmdict_source_signature()
    return (
        int(signature.get("mtime_ns", 0) or 0),
        int(signature.get("size", -1) or -1),
    )


def qmdict_reload_state_snapshot() -> dict:
    with QMDICT_EDIT_LOCK:
        return {
            "mtime_ns": int(QMDICT_RELOAD_STATE.get("mtime_ns", 0) or 0),
            "size": int(QMDICT_RELOAD_STATE.get("size", -1) or -1),
            "checked_at": float(QMDICT_RELOAD_STATE.get("checked_at", 0.0) or 0.0),
            "loaded_at": clean(QMDICT_RELOAD_STATE.get("loaded_at", "")),
            "entries": int(QMDICT_RELOAD_STATE.get("entries", 0) or 0),
            "error": clean(QMDICT_RELOAD_STATE.get("error", "")),
        }


def clear_qmdict_runtime_caches(*, clear_qmdict: bool = False) -> None:
    try:
        runtime = qmdict_runtime_module()
        if clear_qmdict:
            try:
                setattr(runtime, "_QMDICT_CACHE", None)
            except Exception:
                pass
        for name in ("_WORD_ITEM_CACHE", "_PHRASE_VOCAB_ITEM_CACHE"):
            cache = getattr(runtime, name, None)
            if isinstance(cache, dict):
                cache.clear()
        try:
            setattr(runtime, "_QM_USAGE_NOTES_CACHE", None)
        except Exception:
            pass
        for name in ("_PHRASE_RECORDS_CACHE", "_PHRASE_INDEX_CACHE", "_PHRASE_EXACT_SCAN_CACHE"):
            cache = getattr(runtime, name, None)
            if isinstance(cache, dict):
                cache.clear()
                cache["qmdict_id"] = None
                if "records" in cache:
                    cache["records"] = None
                if "index" in cache:
                    cache["index"] = None
                if "buckets" in cache:
                    cache["buckets"] = None
        battle_cache = globals().get("SHARED_WORLD_BATTLE_DICT_CACHE")
        if isinstance(battle_cache, dict):
            battle_cache.clear()
        with QMDICT_SUMMARY_MAP_CACHE_LOCK:
            QMDICT_SUMMARY_MAP_CACHE.update({"signature": None, "maps": {}, "built_at": 0.0})
        with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
            QMDICT_LOOKUP_SUMMARY_CACHE.clear()
        with QMDICT_TEXT_TOKEN_DETAIL_CACHE_LOCK:
            QMDICT_TEXT_TOKEN_DETAIL_CACHE.clear()
        with QMDICT_TEXT_PHRASE_CACHE_LOCK:
            QMDICT_TEXT_PHRASE_CACHE.clear()
        with QMDICT_TEXT_ENTRY_CACHE_LOCK:
            QMDICT_TEXT_ENTRY_CACHE.clear()
        with QMDICT_VOCAB_BASE_CACHE_LOCK:
            QMDICT_VOCAB_BASE_CACHE.clear()
        with QMDICT_VOCAB_STATS_CACHE_LOCK:
            QMDICT_VOCAB_STATS_CACHE.clear()
        with QMDICT_VOCAB_INFLIGHT_LOCK:
            QMDICT_VOCAB_INFLIGHT.clear()
        with QMDICT_CHAT_TOKEN_CACHE_LOCK:
            QMDICT_CHAT_TOKEN_CACHE.clear()
    except Exception:
        pass


def reload_qmdict_runtime(*, force: bool = False, reason: str = "manual") -> dict:
    with QMDICT_EDIT_LOCK:
        signature = qmdict_source_signature()
        if not force and not signature.get("error"):
            if (
                int(QMDICT_RELOAD_STATE.get("mtime_ns", 0) or 0) == int(signature.get("mtime_ns", 0) or 0)
                and int(QMDICT_RELOAD_STATE.get("size", -1) or -1) == int(signature.get("size", -1) or -1)
            ):
                QMDICT_RELOAD_STATE["checked_at"] = time.time()
                return {"reloaded": False, "reason": "unchanged", **qmdict_reload_state_snapshot()}
        try:
            configure_paths()
            module_name = "module_main.Data_Input.QmDict"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            runtime = qmdict_runtime_module()
            clear_qmdict_runtime_caches(clear_qmdict=True)
            qmdict = runtime.get_qmdict()
            if not isinstance(qmdict, dict):
                qmdict = {}
            with SERVER_DATA_FILE_CACHE_LOCK:
                SERVER_DATA_FILE_CACHE.clear()
            QMDICT_RELOAD_STATE.update(
                {
                    "mtime_ns": int(signature.get("mtime_ns", 0) or 0),
                    "size": int(signature.get("size", -1) or -1),
                    "checked_at": time.time(),
                    "loaded_at": utc_timestamp(),
                    "entries": len(qmdict),
                    "error": "",
                }
            )
            stt_debug_log("qmdict_reload_done", reason=reason, entries=len(qmdict), mtime_ns=QMDICT_RELOAD_STATE["mtime_ns"])
            return {"reloaded": True, "reason": reason, **qmdict_reload_state_snapshot()}
        except Exception as exc:
            QMDICT_RELOAD_STATE.update({"checked_at": time.time(), "error": str(exc)})
            stt_debug_log("qmdict_reload_failed", reason=reason, error=str(exc))
            raise


def ensure_qmdict_runtime_fresh(*, force: bool = False) -> dict:
    with QMDICT_EDIT_LOCK:
        now = time.time()
        if not force and now - float(QMDICT_RELOAD_STATE.get("checked_at", 0.0) or 0.0) < 1.0:
            return {"reloaded": False, "reason": "recent-check", **qmdict_reload_state_snapshot()}
        signature = qmdict_source_signature()
        if force:
            return reload_qmdict_runtime(force=True, reason="forced")
        if signature.get("error"):
            QMDICT_RELOAD_STATE.update({"checked_at": now, "error": clean(signature.get("error", ""))})
            return {"reloaded": False, "reason": "signature-error", **qmdict_reload_state_snapshot()}
        if (
            int(QMDICT_RELOAD_STATE.get("mtime_ns", 0) or 0) != int(signature.get("mtime_ns", 0) or 0)
            or int(QMDICT_RELOAD_STATE.get("size", -1) or -1) != int(signature.get("size", -1) or -1)
        ):
            QMDICT_RELOAD_STATE["checked_at"] = now
            return {"reloaded": False, "reason": "manual-reload-required", **qmdict_reload_state_snapshot()}
        QMDICT_RELOAD_STATE["checked_at"] = now
        return {"reloaded": False, "reason": "unchanged", **qmdict_reload_state_snapshot()}


def qmdict_runtime_and_dict() -> tuple[object, dict]:
    ensure_qmdict_runtime_fresh()
    runtime = qmdict_runtime_module()
    try:
        qmdict = runtime.get_qmdict()
    except Exception:
        qmdict = {}
    return runtime, qmdict if isinstance(qmdict, dict) else {}


# Added 2026-07-21: the startup warm gate must not report ready before QmDict maps actually exist.
def warm_qmdict_runtime(delay: float = 0.0) -> dict:
    SERVER_STATE.update({"qmdict_runtime_ready": False, "qmdict_runtime_warm_started_at": time.time()})
    try:
        if delay > 0:
            time.sleep(delay)
        started = time.perf_counter()
        _runtime, qmdict = qmdict_runtime_and_dict()
        summary_maps = qmdict_registry_summary_maps()
        try:
            runtime = qmdict_runtime_module()
            runtime.extract_exact_vocab_words_from_text("look after take off make up get along")
        except Exception:
            pass
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        result = {
            "ready": True,
            "entries": len(qmdict) if isinstance(qmdict, dict) else 0,
            "summary_entries": len(summary_maps) if isinstance(summary_maps, dict) else 0,
            "ms": elapsed_ms,
        }
        SERVER_STATE.update({
            "qmdict_runtime_ready": True,
            "qmdict_runtime_warm_finished_at": time.time(),
            "qmdict_runtime_warm_ms": elapsed_ms,
            "qmdict_runtime_warm_error": "",
        })
        stt_debug_log("qmdict_runtime_warmed", **{key: value for key, value in result.items() if key != "ready"})
        return result
    except Exception as exc:
        SERVER_STATE.update({
            "qmdict_runtime_ready": False,
            "qmdict_runtime_warm_finished_at": time.time(),
            "qmdict_runtime_warm_error": str(exc),
        })
        stt_debug_log("qmdict_runtime_warm_failed", error=str(exc))
        return {"ready": False, "error": str(exc)}


def warm_qmdict_runtime_async(delay: float = 0.25) -> threading.Thread:
    thread = threading.Thread(target=warm_qmdict_runtime, args=(delay,), daemon=True, name="qmdict-runtime-warm")
    thread.start()
    return thread


def qmdict_actual_key(qmdict: dict, word: object = "") -> str:
    text = clean(word)
    if not text or not isinstance(qmdict, dict):
        return ""
    direct = text.strip().upper()
    if direct in qmdict:
        return direct
    try:
        runtime = qmdict_runtime_module()
        candidate = clean(runtime._qmdict_key_for_word(text))  # noqa: SLF001
        if candidate in qmdict:
            return candidate
    except Exception:
        pass
    lowered = direct.lower()
    for key in qmdict.keys():
        if clean(key).lower() == lowered:
            return clean(key)
    return ""


def qmdict_lookup_summary(word: object = "", surface: str = "") -> dict:
    text = clean(word)
    if not text:
        return {}
    signature_key = qmdict_source_signature_key()
    lookup_cache_key = (signature_key, pdf_vocab_word_key(text) or vocab_key(text))
    with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
        cached = QMDICT_LOOKUP_SUMMARY_CACHE.get(lookup_cache_key)
        if isinstance(cached, dict):
            out = dict(cached)
            if out:
                out["surface"] = clean(surface) or clean(out.get("surface", "")) or text
            return out
    try:
        runtime, qmdict = qmdict_runtime_and_dict()
    except Exception:
        return {}
    if not isinstance(qmdict, dict) or not qmdict:
        return {}
    candidates: list[dict] = []
    lookup_key = pdf_vocab_word_key(text)
    for value in (text, lookup_key):
        if not clean(value):
            continue
        try:
            direct = runtime.lookup_qmdict_by_lemma(clean(value), qmdict)
        except Exception:
            direct = None
        summary = pdf_vocab_item_summary(direct, surface=surface or text)
        if summary:
            candidates.append(summary)
    valid_lines = []
    try:
        runtime.is_valid_word(lookup_key or text, qmdict, valid_lines, number="1")
    except Exception:
        valid_lines = []
    for line in list(valid_lines or []):
        try:
            summary = pdf_vocab_item_summary(runtime.vocab_item_from_valid_line(line), surface=surface or text)
        except Exception:
            summary = {}
        if summary:
            candidates.append(summary)
    seen = set()
    unique: list[dict] = []
    for item in candidates:
        key = vocab_key(item.get("word", "")) or pdf_vocab_word_key(item.get("word", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    if not unique:
        with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
            QMDICT_LOOKUP_SUMMARY_CACHE[lookup_cache_key] = {}
            if len(QMDICT_LOOKUP_SUMMARY_CACHE) > QMDICT_LOOKUP_SUMMARY_CACHE_LIMIT:
                QMDICT_LOOKUP_SUMMARY_CACHE.clear()
        return {}
    exact = pdf_vocab_word_key(text)
    for item in unique:
        if pdf_vocab_word_key(item.get("word", "")) == exact:
            result = dict(item)
            break
    else:
        result = dict(unique[0])
    with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
        stored = dict(result)
        stored["surface"] = ""
        QMDICT_LOOKUP_SUMMARY_CACHE[lookup_cache_key] = stored
        if len(QMDICT_LOOKUP_SUMMARY_CACHE) > QMDICT_LOOKUP_SUMMARY_CACHE_LIMIT:
            QMDICT_LOOKUP_SUMMARY_CACHE.clear()
    result["surface"] = clean(surface) or clean(result.get("surface", "")) or text
    return result


# Added 2026-07-01: keeps single word/phrase QmDict lookups on the QmDict worker path.
def qmdict_lookup_summary_queued(word: object = "", surface: str = "") -> dict:
    text = clean(word)
    if not text:
        return {}
    if bool(globals().get("QMDICT_VOCAB_STATS_WORKER_ACTIVE", False)):
        return qmdict_lookup_summary(text, surface)
    signature_key = qmdict_source_signature_key()
    lookup_cache_key = (signature_key, pdf_vocab_word_key(text) or vocab_key(text))
    with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
        cached = QMDICT_LOOKUP_SUMMARY_CACHE.get(lookup_cache_key)
        if isinstance(cached, dict):
            out = dict(cached)
            if out:
                out["surface"] = clean(surface) or clean(out.get("surface", "")) or text
            return out
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import qmdict_lookup_summary_worker

    result = QMDICT_WORK_QUEUE.run(
        f"lookup:{text[:60]}",
        qmdict_lookup_summary_worker,
        text,
        surface,
        timeout=QMDICT_WORK_QUEUE.timeout_seconds,
    )
    if isinstance(result, dict) and result:
        with QMDICT_LOOKUP_SUMMARY_CACHE_LOCK:
            stored = dict(result)
            stored["surface"] = ""
            QMDICT_LOOKUP_SUMMARY_CACHE[lookup_cache_key] = stored
            if len(QMDICT_LOOKUP_SUMMARY_CACHE) > QMDICT_LOOKUP_SUMMARY_CACHE_LIMIT:
                QMDICT_LOOKUP_SUMMARY_CACHE.clear()
        result["surface"] = clean(surface) or clean(result.get("surface", "")) or text
        return result
    return {}


def update_qm_usage_phrase_meaning_type(
    phrase: object = "",
    meaning: object = None,
    word_type: object = None,
    usage: object = None,
    examples: object = None,
    admin: str = "",
) -> dict:
    target_phrase = clean(phrase)
    phrase_key = word_agent_key(target_phrase)
    if not target_phrase or not phrase_key:
        raise RuntimeError("Missing phrase.")
    configure_paths()
    module_name = "module_main.GrammarPharse.qm_usage_data"
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise RuntimeError("Phrase dictionary is not available.") from exc
    notes = getattr(module, "QM_USAGE_NOTES", {})
    if not isinstance(notes, dict) or not notes:
        raise RuntimeError("Phrase dictionary is empty.")
    actual_key = ""
    record = notes.get(phrase_key)
    if isinstance(record, dict):
        actual_key = phrase_key
    else:
        for candidate_key, candidate in notes.items():
            if word_agent_key(candidate_key) == phrase_key and isinstance(candidate, dict):
                actual_key = candidate_key
                record = candidate
                break
            if isinstance(candidate, dict) and word_agent_key(candidate.get("word", "")) == phrase_key:
                actual_key = candidate_key
                record = candidate
                break
    if not actual_key or not isinstance(record, dict):
        raise RuntimeError(f"Phrase entry not found: {target_phrase}")
    next_record = dict(record)
    next_record["word"] = lesson_task_notice_text(next_record.get("word") or target_phrase, limit=180) or target_phrase
    original_meaning = clean(next_record.get("meaning", ""))
    if meaning is not None:
        next_record["meaning"] = lesson_task_notice_text(meaning, limit=1600)
    if word_type is not None:
        type_field = "type" if "type" in next_record else "pos"
        next_record[type_field] = lesson_task_notice_text(word_type, limit=320)
    if usage is not None:
        next_record["usage"] = lesson_task_notice_text(usage, limit=1600)
    if examples is not None:
        next_record["examples"] = word_agent_clean_examples(examples)
    if not clean(next_record.get("meaning", "")):
        raise RuntimeError("Meaning cannot be empty.")
    if not clean(next_record.get("type", next_record.get("pos", ""))):
        raise RuntimeError("Type cannot be empty.")
    notes[actual_key] = next_record
    phrase_source_file = PROGRAME_ROOT / "module_main" / "GrammarPharse" / "qm_usage_data.py"
    pprint = __import__("pprint")
    source = "# Auto-generated from qm_usage.txt. Do not edit manually.\n"
    source += "QM_USAGE_NOTES = "
    source += pprint.pformat(notes, width=120, sort_dicts=False)
    source += "\n"
    atomic_write_text(phrase_source_file, source, encoding="utf-8")
    try:
        importlib.reload(module)
    except Exception:
        importlib.import_module(module_name)
    clear_qmdict_runtime_caches(clear_qmdict=False)
    if meaning is not None and clean(next_record.get("meaning", "")) != original_meaning:
        schedule_qmdict_meaning_audio_refresh(next_record.get("meaning", ""))
    extra = word_agent_phrase_extra(next_record.get("word") or target_phrase)
    entry = {
        "word": clean(extra.get("word") or next_record.get("word") or target_phrase),
        "surface": target_phrase,
        "meaning": clean(extra.get("meaning") or next_record.get("meaning", "")),
        "type": clean(extra.get("type") or next_record.get("type", next_record.get("pos", ""))),
        "usage": clean(extra.get("usage") or next_record.get("usage", "")),
        "examples": word_agent_clean_examples(extra.get("examples") or next_record.get("examples", [])),
        "kind": clean(extra.get("kind") or "phrase"),
    }
    stt_debug_log("phrase_admin_update", admin=admin, key=actual_key, word=entry["word"], meaning=entry["meaning"], word_type=entry["type"])
    return {"key": actual_key, "source": "phrase", "entry": entry}


def update_qmdict_meaning_type(
    word: object = "",
    meaning: object = None,
    word_type: object = None,
    usage: object = None,
    examples: object = None,
    source: object = "",
    admin: str = "",
) -> dict:
    target_word = clean(word)
    if not target_word:
        raise RuntimeError("Missing QmDict word.")
    prefer_phrase = clean(source).lower() in {"phrase", "phrases", "qm_usage", "usage"} or (" " in pdf_vocab_word_key(target_word))
    if prefer_phrase:
        try:
            return update_qm_usage_phrase_meaning_type(
                target_word,
                meaning=meaning,
                word_type=word_type,
                usage=usage,
                examples=examples,
                admin=admin,
            )
        except Exception:
            if clean(source).lower() in {"phrase", "phrases", "qm_usage", "usage"}:
                raise
    with QMDICT_EDIT_LOCK:
        ensure_qmdict_runtime_fresh(force=True)
        runtime, qmdict = qmdict_runtime_and_dict()
        if not isinstance(qmdict, dict) or not qmdict:
            raise RuntimeError("QmDict is not available.")
        key = qmdict_actual_key(qmdict, target_word)
        if not key:
            summary = qmdict_lookup_summary(target_word)
            key = qmdict_actual_key(qmdict, summary.get("word", ""))
        if not key or key not in qmdict:
            try:
                return update_qm_usage_phrase_meaning_type(
                    target_word,
                    meaning=meaning,
                    word_type=word_type,
                    usage=usage,
                    examples=examples,
                    admin=admin,
                )
            except Exception:
                pass
            raise RuntimeError(f"QmDict entry not found: {target_word}")
        existing = qmdict.get(key)
        if isinstance(existing, dict):
            row = [
                clean(existing.get("word", "")) or target_word,
                clean(existing.get("meaning", "")),
                clean(existing.get("pron", "")),
                clean(existing.get("type", "")),
                clean(existing.get("pron_us", "")),
                clean(existing.get("pron_uk", "")),
                clean(existing.get("usage", "")),
                word_agent_clean_examples(existing.get("examples", [])),
            ]
        elif isinstance(existing, (list, tuple)):
            row = list(existing)
        else:
            row = [target_word, "", "", "", "", "", "", []]
        while len(row) < 8:
            row.append("")
        for index in range(0, min(7, len(row))):
            row[index] = clean(row[index])
        row[7] = word_agent_clean_examples(row[7])
        row[0] = clean(row[0]) or target_word
        original_meaning = clean(row[1])
        if meaning is not None:
            row[1] = lesson_task_notice_text(meaning, limit=1600)
        if word_type is not None:
            row[3] = lesson_task_notice_text(word_type, limit=320)
        if usage is not None:
            row[6] = lesson_task_notice_text(usage, limit=1600)
        if examples is not None:
            row[7] = word_agent_clean_examples(examples)
        if not row[1]:
            raise RuntimeError("Meaning cannot be empty.")
        if not row[3]:
            raise RuntimeError("Type cannot be empty.")
        source = QMDICT_SOURCE_FILE.read_text(encoding="utf-8-sig", errors="replace")
        replacement = json.dumps(row, ensure_ascii=False)
        pattern = re.compile(r'(?m)^(\s*"' + re.escape(key) + r'"\s*:\s*)\[[^\n]*\]')
        next_source, count = pattern.subn(lambda match: f"{match.group(1)}{replacement}", source, count=1)
        if count != 1:
            raise RuntimeError(f"Cannot patch QmDict source for {key}.")
        atomic_write_text(QMDICT_SOURCE_FILE, next_source, encoding="utf-8")
        reload_qmdict_runtime(force=True, reason="admin-update")
        if meaning is not None and clean(row[1]) != original_meaning:
            schedule_qmdict_meaning_audio_refresh(row[1])
        runtime, _qmdict = qmdict_runtime_and_dict()
        stt_debug_log("qmdict_admin_update", admin=admin, key=key, word=row[0], meaning=row[1], word_type=row[3])
        return {"key": key, "entry": pdf_vocab_item_summary(runtime.vocab_item_from_valid_line(row), surface=target_word)}
