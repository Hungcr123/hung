from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import html as html_lib
import json
import re
import sys
import time
import os
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtCore import QPointF, QRectF, QSize, QThread, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QDesktopServices, QFont, QPainter, QPen, QPixmap, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QColorDialog,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from future_lesson_builder_gui import (
    CACHE_ROOT,
    CODE_PREFIX,
    SERVER_DATA_ROOT,
    clean_text,
    builder_server2_build_begin,
    builder_server2_build_end,
    edge_english_voice_specs,
    embedded_voice_label,
    encode_future_manifest,
    encode_future_payload,
    grammar_vietnamese_voice_specs,
    microsoft_voice_specs,
    people_voice_specs,
    sound_of_text_voice_specs,
    synthesize_embedded_audio,
    write_server_picture_asset,
    write_server_sound_asset,
)

APP_TITLE = "Future Question Builder"
QUESTION_EXTENSION = ".Space_Q"
SETTINGS_PATH = CACHE_ROOT / "space_q_builder_settings.json"
PREVIEW_DIR = CACHE_ROOT / "space_q_builder_preview"
FUTURE_HTML_PATH = Path(__file__).with_name("future.html")
QUESTION_AUDIO_MODES = [
    ("Off", "off"),
    ("Autoplay", "auto"),
    ("Click", "click"),
    ("Auto + Click", "both"),
]
QUESTION_INFO_MODES = [
    ("Typing card", "type"),
    ("Voice card", "audio"),
]
QUESTION_CARD_MODES = [
    ("Question card", "question"),
    ("Linking question card", "linking"),
]
DEFAULT_INFO_VOICE = "edge:vi-VN-NamMinhNeural"
DEFAULT_HIGHLIGHT_COLOR = "#46f0d7"
DEFAULT_PICTURE_REGION_COLOR = "#ff8a3d"


# Added 2026-07-17: let Space_Q audio generation use several bounded worker lanes.
def builder_audio_parallel_workers(task_count: int) -> int:
    raw = os.environ.get("FUTURE_BUILDER_AUDIO_PARALLEL", "")
    try:
        amount = int(float(raw)) if raw else 4
    except Exception:
        amount = 4
    return max(1, min(16, task_count, amount))
DEFAULT_INPUT_TEXT_COLOR = "#7eebff"
DEFAULT_QUESTION_EFFECT_FILES = {
    "true": "fx-true_a76ad961cb10db7ab6c8a928b2581711b5ae65b9.mp3",
    "false": "fx-false_1ee7795e2be3b283e45d8f6b3e1a0e166bb6d4cc.mp3",
}
DEFAULT_CRYSTAL_NAME = "Prism Crystal"
DEFAULT_CRYSTAL_USE = "Stores learning energy for future item upgrades."
HIGHLIGHT_STYLES = [
    ("Style 1 | Plasma brush", "style-1"),
    ("Style 2 | Ion underline", "style-2"),
    ("Style 3 | Neon capsule", "style-3"),
    ("Style 4 | Circuit frame", "style-4"),
    ("Style 5 | Aurora sweep", "style-5"),
    ("Style 6 | Digital blocks", "style-6"),
    ("Style 7 | Pulse halo", "style-7"),
    ("Style 8 | Laser slash", "style-8"),
    ("Style 9 | Quantum mist", "style-9"),
    ("Style 10 | Data rail", "style-10"),
]
HIGHLIGHT_RENDER_MODES = [
    ("Text glow only", "text"),
    ("Block highlight", "block"),
]
PICTURE_QUESTION_ANCHORS = [
    ("Highlighted root text", "highlight"),
    ("Picture ship/card", "picture"),
    ("Selected picture regions", "picture_regions"),
]
PICTURE_QUESTION_PLACEMENTS = [
    ("Auto", "auto"),
    ("Above connector rail", "above"),
    ("Below connector rail", "below"),
]
CONNECTOR_STYLES = [
    ("Connector 1 | Plasma beam", "connector-1"),
    ("Connector 2 | Sine wave", "connector-2"),
    ("Connector 3 | DNA helix", "connector-3"),
    ("Connector 4 | Circuit pulse", "connector-4"),
    ("Connector 5 | Aurora fiber", "connector-5"),
    ("Connector 6 | Data dash", "connector-6"),
    ("Connector 7 | Quantum braid", "connector-7"),
    ("Connector 8 | Laser rail", "connector-8"),
    ("Connector 9 | Orbital dots", "connector-9"),
    ("Connector 10 | Neural spark", "connector-10"),
]
SHIP_TYPES = [
    ("Random Fleet | Auto", "random"),
    ("Ship 1 | Aurora Scout", "ship-1"),
    ("Ship 2 | Orbital Saucer", "ship-2"),
    ("Ship 3 | Delta Spear", "ship-3"),
    ("Ship 4 | Quantum Cruiser", "ship-4"),
    ("Ship 5 | Citadel Cruiser", "ship-5"),
]


def safe_segment(value: object, fallback: str = "item", limit: int = 64) -> str:
    text = clean_text(value) or fallback
    text = re.sub(r'[^0-9A-Za-z._-]+', "-", text).strip(".-_") or fallback
    return text[:limit].strip(".-_") or fallback


def safe_unicode_filename_stem(value: object, fallback: str = "Future Question", limit: int = 120) -> str:
    text = clean_text(value) or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = fallback
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    if text.upper() in reserved:
        text = f"{text} Lesson"
    return text[:limit].strip(" .") or fallback


def clean_multiline_text(value: object) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip("\n")


def safe_color(value: object, fallback: str = DEFAULT_HIGHLIGHT_COLOR) -> str:
    text = clean_text(value)
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", text):
        return text.lower()
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", text):
        return "#" + "".join(ch * 2 for ch in text[1:]).lower()
    return fallback


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = clean_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(value)


def audio_mime_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return "audio/wav"
    if suffix in {".m4a", ".mp4"}:
        return "audio/mp4"
    if suffix == ".ogg":
        return "audio/ogg"
    return "audio/mpeg"


def default_question_effects_payload() -> dict:
    effects = {}
    sound_root = SERVER_DATA_ROOT / "Sound"
    for key, filename in DEFAULT_QUESTION_EFFECT_FILES.items():
        path = sound_root / filename
        if not path.is_file():
            path = next(iter(sorted(sound_root.glob(f"fx-{key}_*.mp3"))), path)
        if not path.is_file():
            continue
        effects[key] = {
            "mime": audio_mime_for_path(path),
            "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            "name": path.name,
        }
    return effects


def normalize_reward_config(source: object = None) -> dict:
    data = source if isinstance(source, dict) else {}
    crystal_source = data.get("crystal") if isinstance(data.get("crystal"), dict) else data
    name = clean_text(
        crystal_source.get("name")
        or crystal_source.get("title")
        or crystal_source.get("n")
        or DEFAULT_CRYSTAL_NAME
    )
    use = clean_multiline_text(
        crystal_source.get("use")
        or crystal_source.get("purpose")
        or crystal_source.get("description")
        or crystal_source.get("u")
        or DEFAULT_CRYSTAL_USE
    )
    return {
        "crystal": {
            "id": "crystal",
            "name": name or DEFAULT_CRYSTAL_NAME,
            "use": use or DEFAULT_CRYSTAL_USE,
        }
    }


def optional_safe_color(value: object) -> str:
    return safe_color(value, "")


def safe_highlight_render(value: object, fallback: str = "text") -> str:
    mode = clean_text(value).lower()
    if mode in {"block", "box", "old", "background"}:
        return "block"
    return fallback


HIGHLIGHT_CAMERA_FOCUS_KEYS = (
    "camera_focus",
    "cameraFocus",
    "focus",
    "f",
    "pan_to_highlight",
    "panToHighlight",
    "pan",
    "follow",
    "move_view",
    "moveView",
)


def highlight_camera_focus_enabled(value: object, default: bool = False) -> bool:
    if isinstance(value, dict):
        raw = None
        for key in HIGHLIGHT_CAMERA_FOCUS_KEYS:
            if key in value:
                raw = value.get(key)
                break
        if raw is None:
            return default
        value = raw
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = clean_text(value).lower()
    if text in {"1", "true", "yes", "y", "on", "checked", "tick", "pan", "focus"}:
        return True
    if text in {"0", "false", "no", "n", "off", "none", "unchecked"}:
        return False
    return default


def safe_picture_question_anchor(value: object, fallback: str = "highlight") -> str:
    key = clean_text(value).lower()
    valid = {item[1] for item in PICTURE_QUESTION_ANCHORS}
    return key if key in valid else fallback


def safe_picture_question_placement(value: object, fallback: str = "auto") -> str:
    key = clean_text(value).lower()
    valid = {item[1] for item in PICTURE_QUESTION_PLACEMENTS}
    return key if key in valid else fallback


def normalize_question_type(value: object) -> str:
    key = clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if key in {"input", "typed", "text", "tu_luan", "essay", "written"}:
        return "input"
    if key in {"select", "token_select", "word_select", "select_tokens", "select_words", "chon_tu", "chon_token"}:
        return "select"
    if key in {"guide", "guidance", "instruction", "instructions", "demo", "show", "presentation", "huong_dan"}:
        return "guide"
    return "choice"


def normalize_question_card_mode(value: object, fallback: str = "question") -> str:
    key = clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if key in {"linking", "link", "linked", "linked_question", "linking_question", "picture", "picture_question", "question_picture", "question_picture_card"}:
        return "linking"
    if key in {"question", "normal", "card", "question_card", "default"}:
        return "question"
    return fallback if fallback in {"question", "linking"} else "question"


def normalize_guidance_node_mode(value: object) -> str:
    key = clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if key in {"input", "typed", "text", "tu_luan", "essay", "written"}:
        return "input"
    if key in {"choice", "multiple_choice", "quiz", "question", "trac_nghiem"}:
        return "choice"
    return "info"


def clean_text_list(values: object) -> list[str]:
    if isinstance(values, str):
        raw_values = re.split(r"[\n\r]+", values)
    elif isinstance(values, list):
        raw_values = values
    else:
        raw_values = []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        value = clean_text(item.get("text") if isinstance(item, dict) else item)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def select_token_list(values: object, fallback: object = "") -> list[str]:
    if isinstance(values, str):
        raw_values = re.split(r"[\n\r]+", values)
    elif isinstance(values, list):
        raw_values = values
    else:
        raw_values = []
    tokens = [
        clean_text(item.get("text") if isinstance(item, dict) else item)
        for item in raw_values
        if clean_text(item.get("text") if isinstance(item, dict) else item)
    ]
    if not tokens:
        raw = clean_multiline_text(fallback)
        if raw:
            tokens = [clean_text(item) for item in re.split(r"[\n\r]+", raw) if clean_text(item)]
    if len(tokens) <= 1:
        raw_text = clean_text(tokens[0] if tokens else fallback)
        if raw_text:
            tokens = [part for part in re.split(r"\s+", raw_text) if part]
    return [clean_text(token) for token in tokens if clean_text(token)]


class AnswerLinesHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self.first_format = QTextCharFormat()
        self.first_format.setForeground(QColor("#ecfff9"))
        self.first_format.setBackground(QColor(36, 146, 92, 96))
        self.first_format.setFontWeight(QFont.Bold)
        self.even_format = QTextCharFormat()
        self.even_format.setForeground(QColor("#d9fff6"))
        self.even_format.setBackground(QColor(70, 240, 215, 28))
        self.odd_format = QTextCharFormat()
        self.odd_format.setForeground(QColor("#f8e9ff"))
        self.odd_format.setBackground(QColor(216, 108, 255, 24))

    def highlightBlock(self, text: str) -> None:
        if not text.strip():
            return
        block_number = self.currentBlock().blockNumber()
        fmt = self.first_format if block_number == 0 else (self.even_format if block_number % 2 == 0 else self.odd_format)
        self.setFormat(0, len(text), fmt)


def normalize_guidance_tree_node(source: object) -> dict:
    data = source if isinstance(source, dict) else {}
    title = clean_text(data.get("title") or data.get("label") or data.get("name") or data.get("t"))
    body = clean_multiline_text(data.get("body") or data.get("content") or data.get("text") or data.get("info") or data.get("b"))
    main = clean_multiline_text(data.get("main") or data.get("connector") or data.get("lead") or data.get("m"))
    answer_option = clean_text(data.get("answer_option") or data.get("answerOption") or data.get("option") or data.get("ao"))
    mode = normalize_guidance_node_mode(data.get("type") or data.get("mode") or data.get("kind") or data.get("quiz_type") or data.get("question_type"))
    question = clean_multiline_text(data.get("question") or data.get("prompt") or data.get("q"))
    answer = clean_text(data.get("answer") or data.get("correct") or data.get("a"))
    wrong = clean_text_list(data.get("wrong") if isinstance(data.get("wrong"), list) else data.get("wrongs") if isinstance(data.get("wrongs"), list) else data.get("options") if isinstance(data.get("options"), list) else data.get("w"))
    accepted = clean_text_list(data.get("answers") if isinstance(data.get("answers"), list) else data.get("accept") if isinstance(data.get("accept"), list) else data.get("accepts") if isinstance(data.get("accepts"), list) else data.get("alts"))
    if question and answer and mode == "info":
        mode = "choice"
    children = [
        child
        for child in (normalize_guidance_tree_node(item) for item in (data.get("children") if isinstance(data.get("children"), list) else data.get("items") if isinstance(data.get("items"), list) else []))
        if child
    ]
    has_question = bool(question and answer and mode in {"choice", "input"})
    if not title and (body or main or children or has_question):
        title = "Question branch" if has_question else "Info card"
    if not (title or body or main or children or has_question):
        return {}
    payload = {"title": title}
    if body:
        payload["body"] = body
    if main:
        payload["main"] = main
    if answer_option:
        payload["answer_option"] = answer_option
    if has_question:
        payload["type"] = mode
        payload["question"] = question
        payload["answer"] = answer
        if mode == "input":
            answers = clean_text_list([answer, *accepted, *wrong])
            if answers:
                payload["answers"] = answers
        else:
            clean_wrong = [value for value in wrong if value.casefold() != answer.casefold()]
            if clean_wrong:
                payload["wrong"] = clean_wrong
    if children:
        payload["children"] = children
    return payload


def normalize_guidance_tree_payload(source: object) -> dict:
    data = source if isinstance(source, dict) else {}
    raw_items = data.get("items") if isinstance(data.get("items"), list) else data.get("answers") if isinstance(data.get("answers"), list) else []
    items = []
    for entry in raw_items:
        raw = entry if isinstance(entry, dict) else {}
        text = clean_text(raw.get("text") or raw.get("answer") or raw.get("target") or raw.get("a"))
        main = clean_multiline_text(raw.get("main") or raw.get("connector") or raw.get("lead") or raw.get("m"))
        mode = normalize_guidance_node_mode(raw.get("type") or raw.get("mode") or raw.get("kind") or raw.get("quiz_type") or raw.get("question_type"))
        question = clean_multiline_text(raw.get("question") or raw.get("prompt") or raw.get("q"))
        answer = clean_text(raw.get("answer") or raw.get("correct") or raw.get("a"))
        wrong = clean_text_list(raw.get("wrong") if isinstance(raw.get("wrong"), list) else raw.get("wrongs") if isinstance(raw.get("wrongs"), list) else raw.get("options") if isinstance(raw.get("options"), list) else raw.get("w"))
        accepted = clean_text_list(raw.get("answers") if isinstance(raw.get("answers"), list) else raw.get("accept") if isinstance(raw.get("accept"), list) else raw.get("accepts") if isinstance(raw.get("accepts"), list) else raw.get("alts"))
        children = [
            child
            for child in (normalize_guidance_tree_node(item) for item in (raw.get("children") if isinstance(raw.get("children"), list) else raw.get("items") if isinstance(raw.get("items"), list) else []))
            if child
        ]
        has_question = bool(question and answer and mode in {"choice", "input"})
        if not (text or main or children or has_question):
            continue
        payload = {"text": text}
        if main:
            payload["main"] = main
        if has_question:
            payload["type"] = mode
            payload["question"] = question
            payload["answer"] = answer
            if mode == "input":
                answers = clean_text_list([answer, *accepted, *wrong])
                if answers:
                    payload["answers"] = answers
            else:
                clean_wrong = [value for value in wrong if value.casefold() != answer.casefold()]
                if clean_wrong:
                    payload["wrong"] = clean_wrong
        if children:
            payload["children"] = children
        items.append(payload)
    return {"items": items} if items else {}


def clamp_ratio(value: object, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = float(fallback)
    return max(0.0, min(1.0, number))


def normalize_picture_question_regions(source: object) -> list[dict]:
    values = source if isinstance(source, list) else []
    result: list[dict] = []
    for index, entry in enumerate(values, 1):
        if isinstance(entry, (list, tuple)) and len(entry) >= 4:
            raw = {"x": entry[0], "y": entry[1], "w": entry[2], "h": entry[3]}
        else:
            raw = entry if isinstance(entry, dict) else {}
        x = clamp_ratio(raw.get("x") or raw.get("left") or raw.get("l"), 0.0)
        y = clamp_ratio(raw.get("y") or raw.get("top") or raw.get("t"), 0.0)
        w = clamp_ratio(raw.get("w") or raw.get("width") or raw.get("rw"), 0.0)
        h = clamp_ratio(raw.get("h") or raw.get("height") or raw.get("rh"), 0.0)
        if w <= 0.002 or h <= 0.002:
            continue
        if x + w > 1.0:
            w = max(0.002, 1.0 - x)
        if y + h > 1.0:
            h = max(0.002, 1.0 - y)
        item = {
            "id": clean_text(raw.get("id") or raw.get("i")) or f"r{len(result) + 1}",
            "label": clean_text(raw.get("label") or raw.get("name") or raw.get("n")) or chr(64 + min(len(result) + 1, 26)),
            "shape": "rect",
            "x": round(x, 5),
            "y": round(y, 5),
            "w": round(w, 5),
            "h": round(h, 5),
        }
        color = optional_safe_color(raw.get("color") or raw.get("c") or raw.get("border_color") or raw.get("borderColor"))
        if color:
            item["color"] = color
        result.append(item)
    return result


def normalize_picture_question_payload(source: object, fallback_text: object = "") -> dict:
    data = source if isinstance(source, dict) else {}
    raw = data.get("picture_question") if isinstance(data.get("picture_question"), dict) else data.get("pictureQuestion")
    if not isinstance(raw, dict):
        raw = data.get("pq") if isinstance(data.get("pq"), dict) else {}
    anchor_source = raw if isinstance(raw, dict) else data
    regions = normalize_picture_question_regions(
        anchor_source.get("regions")
        or anchor_source.get("picture_regions")
        or anchor_source.get("rs")
        or data.get("picture_regions")
        or data.get("regions")
        or []
    )
    text = clean_multiline_text((raw.get("text") or raw.get("question") or raw.get("q")) if isinstance(raw, dict) else "")
    if not text:
        text = clean_multiline_text(data.get("picture_question_text") or data.get("question_bubble") or data.get("questionBubble"))
    has_picture_question_data = bool(raw) or bool(text) or bool(regions)
    if not has_picture_question_data:
        return {}
    fallback = clean_multiline_text(fallback_text)
    if fallback:
        text = fallback
    if not text:
        return {}
    raw_anchor = anchor_source.get("anchor") or anchor_source.get("a") or data.get("anchor")
    anchor = safe_picture_question_anchor(raw_anchor, "picture_regions" if regions else "highlight")
    payload = {
        "text": text,
        "anchor": anchor,
        "placement": safe_picture_question_placement(anchor_source.get("placement") or anchor_source.get("p") or data.get("placement"), "auto"),
    }
    region_color = optional_safe_color(
        anchor_source.get("region_color")
        or anchor_source.get("regionColor")
        or anchor_source.get("color")
        or anchor_source.get("c")
        or data.get("picture_region_color")
        or data.get("pictureRegionColor")
    )
    if region_color:
        payload["region_color"] = region_color
    if regions:
        payload["regions"] = regions
    return payload


def normalize_select_targets_payload(source: object) -> dict:
    data = source if isinstance(source, dict) else {}
    root_text = clean_multiline_text(
        data.get("root_text")
        or data.get("rootText")
        or data.get("text")
        or data.get("target_text")
        or data.get("targetText")
    )
    root_ranges_raw = (
        data.get("root_ranges")
        or data.get("rootRanges")
        or data.get("root_segments")
        or data.get("rootSegments")
        or []
    )
    if not isinstance(root_ranges_raw, list):
        root_ranges_raw = []
    root_ranges = []
    for entry in root_ranges_raw:
        raw = entry if isinstance(entry, dict) else {}
        try:
            start = int(raw.get("start") or raw.get("s") or 0)
            end = int(raw.get("end") or raw.get("e") or 0)
        except Exception:
            start, end = 0, 0
        text = clean_multiline_text(raw.get("text") or raw.get("t"))
        if end > start or text:
            root_ranges.append({
                "start": max(0, start),
                "end": max(0, end),
                "text": text,
            })
    regions = normalize_picture_question_regions(
        data.get("regions")
        or data.get("picture_regions")
        or data.get("pictureRegions")
        or []
    )
    payload: dict = {}
    if root_text:
        payload["root_text"] = root_text
    if root_ranges:
        payload["root_ranges"] = root_ranges
    if regions:
        payload["regions"] = regions
    color = optional_safe_color(data.get("region_color") or data.get("regionColor") or data.get("color"))
    if color:
        payload["region_color"] = color
    return payload


def select_targets_fallback_answer(select_targets: dict) -> str:
    payload = normalize_select_targets_payload(select_targets)
    labels: list[str] = []
    for index, region in enumerate(payload.get("regions") if isinstance(payload.get("regions"), list) else [], 1):
        if not isinstance(region, dict):
            continue
        label = clean_text(region.get("label") or region.get("id") or region.get("name"))
        labels.append(label or f"region {index}")
    if labels:
        return " ".join(labels)
    texts = [
        clean_text(item.get("text") if isinstance(item, dict) else "")
        for item in (payload.get("root_ranges") if isinstance(payload.get("root_ranges"), list) else [])
    ]
    texts = [text for text in texts if text]
    if texts:
        return " ".join(texts)
    if payload.get("root_text"):
        return clean_text(payload.get("root_text"))
    return ""


def normalize_info_mode(value: object, fallback: str = "audio") -> str:
    mode = clean_text(value).lower()
    valid = {key for _label, key in QUESTION_INFO_MODES}
    if mode in valid:
        return mode
    return fallback if fallback in valid else "audio"


def normalize_root_notice_turn(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    english = clean_multiline_text(data.get("english") or data.get("en") or data.get("text") or data.get("t"))
    vietnamese = clean_multiline_text(data.get("vietnamese") or data.get("vi") or data.get("translation") or data.get("v"))
    voice = clean_text(data.get("voice") or data.get("voice_key") or data.get("voiceKey") or data.get("vk"))
    speaker = clean_text(data.get("speaker") or data.get("speaker_name") or data.get("speakerName") or data.get("character") or data.get("character_name") or data.get("name"))
    avatar_path = clean_text(data.get("avatar_path") or data.get("avatarPath") or data.get("picture_path") or data.get("picturePath") or data.get("image_path") or data.get("imagePath"))
    avatar_url = clean_text(data.get("avatar_url") or data.get("avatarUrl") or data.get("picture_url") or data.get("pictureUrl") or data.get("image_url") or data.get("imageUrl"))
    payload = {}
    if english:
        payload["english"] = english
    if vietnamese:
        payload["vietnamese"] = vietnamese
    if voice:
        payload["voice"] = voice
    if speaker:
        payload["speaker"] = speaker
    if avatar_path:
        payload["avatar_path"] = avatar_path
    avatar = data.get("avatar") if isinstance(data.get("avatar"), dict) else {}
    if avatar_url:
        avatar = {**avatar, "url": avatar_url}
    if avatar:
        clean_avatar = {}
        for key in ("url", "name", "mime"):
            value = clean_text(avatar.get(key))
            if value:
                clean_avatar[key] = value
        if clean_avatar:
            payload["avatar"] = clean_avatar
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    if audio:
        payload["audio"] = audio
    return payload


def root_notice_turns(value: object) -> list[dict]:
    payload = normalize_root_notice_payload(value)
    turns = payload.get("turns") if isinstance(payload.get("turns"), list) else []
    if turns:
        return [dict(turn) for turn in turns if isinstance(turn, dict)]
    legacy = normalize_root_notice_turn(payload)
    return [legacy] if legacy else []


def normalize_root_notice_payload(value: object) -> dict:
    data = value if isinstance(value, dict) else {}
    raw_turns = None
    for key in ("turns", "items", "dialogue", "dialog", "speakers"):
        if isinstance(data.get(key), list):
            raw_turns = data.get(key)
            break
    if raw_turns is not None:
        turns = [normalize_root_notice_turn(item) for item in raw_turns]
        turns = [item for item in turns if item]
        return {"turns": turns} if turns else {}
    return normalize_root_notice_turn(data)


def root_notice_summary(value: object) -> str:
    turns = root_notice_turns(value)
    if not turns:
        return "No hologram notice dialogue."
    parts = []
    for index, turn in enumerate(turns, 1):
        speaker = clean_text(turn.get("speaker")) or clean_text(turn.get("voice")) or "Typing only"
        english = clean_multiline_text(turn.get("english"))
        parts.append(f"{index}. {speaker}: {english[:46] or 'empty text'}")
    return " | ".join(parts[:4]) + (" ..." if len(parts) > 4 else "")


def normalize_ship_type(value: object, fallback: str = "random") -> str:
    key = clean_text(value).lower()
    valid = {ship_key for _label, ship_key in SHIP_TYPES}
    return key if key in valid else fallback


def node_id_for(root: str = "") -> str:
    raw = f"{time.time_ns()}:{root}".encode("utf-8")
    return "qnode-" + hashlib.sha1(raw).hexdigest()[:12]


def load_settings() -> dict:
    try:
        if SETTINGS_PATH.is_file():
            payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                return payload
    except Exception:
        pass
    return {}


def save_settings(payload: dict) -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class PictureRegionCanvas(QWidget):
    changed = pyqtSignal()

    def __init__(self, image_path: Path, regions: list[dict] | None = None, region_color: object = DEFAULT_PICTURE_REGION_COLOR, parent=None) -> None:
        super().__init__(parent)
        self.image_path = Path(image_path)
        self.pixmap = QPixmap(str(self.image_path))
        self.regions = normalize_picture_question_regions(regions or [])
        self.region_color = safe_color(region_color, DEFAULT_PICTURE_REGION_COLOR)
        self.selected_index = len(self.regions) - 1 if self.regions else -1
        self.drag_start: QPointF | None = None
        self.drag_current: QPointF | None = None
        self.setMinimumSize(720, 420)
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:
        return QSize(900, 560)

    def image_rect(self) -> QRectF:
        rect = self.rect().adjusted(18, 18, -18, -18)
        if self.pixmap.isNull() or rect.width() <= 0 or rect.height() <= 0:
            return QRectF(rect)
        source = self.pixmap.size()
        scale = min(rect.width() / max(1, source.width()), rect.height() / max(1, source.height()))
        width = source.width() * scale
        height = source.height() * scale
        return QRectF(
            rect.left() + (rect.width() - width) / 2,
            rect.top() + (rect.height() - height) / 2,
            width,
            height,
        )

    def point_to_ratio(self, point) -> QPointF:
        rect = self.image_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return QPointF(0.0, 0.0)
        x = (point.x() - rect.left()) / rect.width()
        y = (point.y() - rect.top()) / rect.height()
        return QPointF(clamp_ratio(x), clamp_ratio(y))

    def region_to_rect(self, region: dict) -> QRectF:
        rect = self.image_rect()
        return QRectF(
            rect.left() + rect.width() * float(region.get("x") or 0),
            rect.top() + rect.height() * float(region.get("y") or 0),
            rect.width() * float(region.get("w") or 0),
            rect.height() * float(region.get("h") or 0),
        )

    def selected_regions(self) -> list[dict]:
        return normalize_picture_question_regions(self.regions)

    def active_region_color(self) -> str:
        if 0 <= self.selected_index < len(self.regions):
            return safe_color(self.regions[self.selected_index].get("color"), self.region_color)
        return safe_color(self.region_color, DEFAULT_PICTURE_REGION_COLOR)

    def set_region_color(self, color: object) -> None:
        self.region_color = safe_color(color, DEFAULT_PICTURE_REGION_COLOR)
        self.update()

    def set_active_region_color(self, color: object) -> None:
        safe = safe_color(color, DEFAULT_PICTURE_REGION_COLOR)
        if 0 <= self.selected_index < len(self.regions):
            self.regions[self.selected_index]["color"] = safe
            self.changed.emit()
        else:
            self.region_color = safe
        self.update()

    def delete_selected(self) -> None:
        if 0 <= self.selected_index < len(self.regions):
            self.regions.pop(self.selected_index)
            self.selected_index = min(self.selected_index, len(self.regions) - 1)
            self.changed.emit()
            self.update()

    def clear_regions(self) -> None:
        self.regions.clear()
        self.selected_index = -1
        self.changed.emit()
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self.pixmap.isNull():
            return
        pos = event.pos()
        for index in range(len(self.regions) - 1, -1, -1):
            if self.region_to_rect(self.regions[index]).contains(pos):
                self.selected_index = index
                self.drag_start = None
                self.drag_current = None
                self.changed.emit()
                self.update()
                return
        if self.image_rect().contains(pos):
            self.drag_start = self.point_to_ratio(pos)
            self.drag_current = self.drag_start
            self.selected_index = -1
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_start is None:
            return
        self.drag_current = self.point_to_ratio(event.pos())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self.drag_start is None:
            return
        end = self.point_to_ratio(event.pos())
        x1 = min(self.drag_start.x(), end.x())
        y1 = min(self.drag_start.y(), end.y())
        x2 = max(self.drag_start.x(), end.x())
        y2 = max(self.drag_start.y(), end.y())
        self.drag_start = None
        self.drag_current = None
        if x2 - x1 >= 0.01 and y2 - y1 >= 0.01:
            number = len(self.regions) + 1
            self.regions.append({
                "id": f"r{number}",
                "label": chr(64 + min(number, 26)),
                "shape": "rect",
                "x": round(x1, 5),
                "y": round(y1, 5),
                "w": round(x2 - x1, 5),
                "h": round(y2 - y1, 5),
                "color": safe_color(self.region_color, DEFAULT_PICTURE_REGION_COLOR),
            })
            self.selected_index = len(self.regions) - 1
            self.changed.emit()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#061112"))
        image_rect = self.image_rect()
        painter.setPen(QPen(QColor(70, 240, 215, 90), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
        painter.drawRoundedRect(image_rect, 10, 10)
        if not self.pixmap.isNull():
            painter.drawPixmap(image_rect.toRect(), self.pixmap)
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        base_color = QColor(safe_color(self.region_color, DEFAULT_PICTURE_REGION_COLOR))
        for index, region in enumerate(self.regions):
            rect = self.region_to_rect(region)
            active = index == self.selected_index
            pen_color = QColor(safe_color(region.get("color"), self.region_color))
            fill_color = QColor(pen_color)
            fill_color.setAlpha(66 if active else 42)
            painter.setPen(QPen(pen_color, 3 if active else 2))
            painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(rect, 6, 6)
            badge = QRectF(rect.left() + 6, rect.top() + 6, 30, 22)
            painter.setPen(Qt.NoPen)
            painter.setBrush(pen_color)
            painter.drawRoundedRect(badge, 5, 5)
            painter.setPen(QColor("#061112"))
            painter.drawText(badge, Qt.AlignCenter, clean_text(region.get("label")) or str(index + 1))
        if self.drag_start is not None and self.drag_current is not None:
            start = self.drag_start
            current = self.drag_current
            preview = {
                "x": min(start.x(), current.x()),
                "y": min(start.y(), current.y()),
                "w": abs(current.x() - start.x()),
                "h": abs(current.y() - start.y()),
            }
            rect = self.region_to_rect(preview)
            preview_color = QColor(base_color)
            preview_fill = QColor(base_color)
            preview_fill.setAlpha(36)
            painter.setPen(QPen(preview_color, 2, Qt.DashLine))
            painter.setBrush(QBrush(preview_fill))
            painter.drawRoundedRect(rect, 6, 6)


class PictureRegionDialog(QDialog):
    def __init__(
        self,
        image_path: Path,
        regions: list[dict] | None = None,
        region_color: object = DEFAULT_PICTURE_REGION_COLOR,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select picture regions")
        self.resize(1120, 720)
        self.region_color_value = safe_color(region_color, DEFAULT_PICTURE_REGION_COLOR)
        if parent is not None and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        title = QLabel("Drag on the embedded picture to create one or more target regions.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.canvas = PictureRegionCanvas(Path(image_path), regions or [], self.region_color_value, self)
        body.addWidget(self.canvas, 1)
        side = QVBoxLayout()
        body.addLayout(side)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(230)
        side.addWidget(QLabel("Regions"))
        side.addWidget(self.list_widget, 1)
        self.color_button = QPushButton()
        side.addWidget(QLabel("Selected bubble color"))
        side.addWidget(self.color_button)
        delete = QPushButton("Delete selected")
        clear = QPushButton("Clear all")
        side.addWidget(delete)
        side.addWidget(clear)
        side.addStretch(1)
        buttons = QHBoxLayout()
        ok = QPushButton("Use regions")
        cancel = QPushButton("Cancel")
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        def refresh_list() -> None:
            self.list_widget.clear()
            for index, region in enumerate(self.canvas.selected_regions()):
                label = clean_text(region.get("label")) or str(index + 1)
                color = safe_color(region.get("color"), self.region_color_value).upper()
                item = QListWidgetItem(
                    f"{label}: {color} | x={region['x']:.3f}, y={region['y']:.3f}, w={region['w']:.3f}, h={region['h']:.3f}"
                )
                self.list_widget.addItem(item)
            if 0 <= self.canvas.selected_index < self.list_widget.count():
                self.list_widget.setCurrentRow(self.canvas.selected_index)
            refresh_color_button()

        def select_from_list(row: int) -> None:
            if 0 <= row < len(self.canvas.regions):
                self.canvas.selected_index = row
                self.canvas.update()
                refresh_color_button()

        def refresh_color_button() -> None:
            color_value = safe_color(self.canvas.active_region_color(), DEFAULT_PICTURE_REGION_COLOR)
            red = int(color_value[1:3], 16)
            green = int(color_value[3:5], 16)
            blue = int(color_value[5:7], 16)
            luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
            text_color = "#061112" if luminance > 0.62 else "#ecfff9"
            label = "Bubble" if 0 <= self.canvas.selected_index < len(self.canvas.regions) else "New bubble"
            self.color_button.setText(f"{label} {color_value.upper()}")
            self.color_button.setToolTip("Select a region bubble, then choose its border color. Without a selection, this sets the default for new bubbles.")
            self.color_button.setStyleSheet(
                "QPushButton {"
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba({red},{green},{blue},0.96), stop:1 rgba(70,240,215,0.22));"
                f"color: {text_color};"
                f"border: 1px solid rgba({red},{green},{blue},0.92);"
                "border-radius: 10px;"
                "padding: 9px 12px;"
                "font-weight: 900;"
                "}"
            )

        def choose_region_color() -> None:
            color = QColorDialog.getColor(QColor(safe_color(self.canvas.active_region_color(), DEFAULT_PICTURE_REGION_COLOR)), self, "Choose selected bubble color")
            if not color.isValid():
                return
            selected_region = 0 <= self.canvas.selected_index < len(self.canvas.regions)
            if selected_region:
                self.canvas.set_active_region_color(color.name())
            else:
                self.region_color_value = color.name()
                self.canvas.set_region_color(self.region_color_value)
                refresh_list()
            refresh_color_button()

        self.canvas.changed.connect(refresh_list)
        self.list_widget.currentRowChanged.connect(select_from_list)
        self.color_button.clicked.connect(choose_region_color)
        delete.clicked.connect(self.canvas.delete_selected)
        clear.clicked.connect(self.canvas.clear_regions)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        refresh_list()
        refresh_color_button()

    def regions(self) -> list[dict]:
        return self.canvas.selected_regions()

    def region_color(self) -> str:
        return safe_color(self.region_color_value, DEFAULT_PICTURE_REGION_COLOR)


class GuidanceTreeDialog(QDialog):
    def __init__(self, answer_text: str, payload: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.answer_text = clean_text(answer_text)
        self.loading_item = False
        data = payload if isinstance(payload, dict) else {}
        self.setWindowTitle("Extra info/question tree")
        self.resize(1120, 740)
        if parent is not None and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        title = QLabel(f"Extra branch tree for: {self.answer_text or 'answer card'}")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        intro = QLabel("Click a parent card in the lesson to open its children. Question branches must be answered before their children unlock.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: rgba(236,255,249,.76); font-weight: 700;")
        layout.addWidget(intro)
        root_hint = QLabel(f"Root answer: {self.answer_text or 'selected answer'}")
        root_hint.setStyleSheet("color: rgba(108,240,164,.92); font-weight: 900;")
        layout.addWidget(root_hint)
        self.main_edit = QPlainTextEdit()
        self.main_edit.hide()

        body_layout = QHBoxLayout()
        layout.addLayout(body_layout, 1)
        left = QVBoxLayout()
        body_layout.addLayout(left, 1)
        left.addWidget(QLabel("Question / answer branch tree"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Answer branches"])
        self.tree.setMinimumWidth(420)
        left.addWidget(self.tree, 1)
        tree_buttons = QHBoxLayout()
        build_children = QPushButton("Build answer branches")
        remove = QPushButton("Remove answer")
        move_up = QPushButton("Up")
        move_down = QPushButton("Down")
        tree_buttons.addWidget(build_children)
        tree_buttons.addWidget(remove)
        tree_buttons.addWidget(move_up)
        tree_buttons.addWidget(move_down)
        left.addLayout(tree_buttons)

        right = QGridLayout()
        body_layout.addLayout(right, 1)
        right.addWidget(QLabel("Answer card"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("This card title is the answer text")
        right.addWidget(self.title_edit, 0, 1)
        right.addWidget(QLabel("Question type"), 1, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Choice question", "choice")
        self.mode_combo.addItem("Input question", "input")
        right.addWidget(self.mode_combo, 1, 1)
        right.addWidget(QLabel("Branch question"), 2, 0)
        self.question_edit = QPlainTextEdit()
        self.question_edit.setPlaceholderText("Question shown in the cut-corner connector card before this answer opens its child answers.")
        self.question_edit.setMinimumHeight(150)
        right.addWidget(self.question_edit, 2, 1)
        self.answer_label = QLabel("")
        self.answer_edit = QLineEdit()
        self.answer_label.hide()
        self.answer_edit.hide()
        right.addWidget(QLabel("Answers"), 3, 0)
        self.wrong_edit = QPlainTextEdit()
        self.wrong_edit.setPlaceholderText("One answer per line. Choice: first line is correct. Input: every line is accepted.")
        self.wrong_edit.setMinimumHeight(220)
        right.addWidget(self.wrong_edit, 3, 1)
        self.answers_highlighter = AnswerLinesHighlighter(self.wrong_edit.document())
        self.connector_edit = QPlainTextEdit()
        self.connector_edit.hide()
        self.body_edit = QPlainTextEdit()
        self.body_edit.hide()

        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        root_payload = dict(data)
        root_payload["title"] = self.answer_text or clean_text(data.get("text")) or "Root answer"
        root_payload["answer_option"] = self.answer_text or clean_text(data.get("text")) or root_payload["title"]
        self.root_item = self.item_from_node(root_payload) or QTreeWidgetItem([self.answer_text or "Root answer"])
        self.root_item.setData(0, Qt.UserRole, {
            **(self.root_item.data(0, Qt.UserRole) if isinstance(self.root_item.data(0, Qt.UserRole), dict) else {}),
            "answer_option": self.answer_text or clean_text(data.get("text")) or "Root answer",
        })
        self.tree.addTopLevelItem(self.root_item)
        self.tree.expandAll()
        self.tree.setCurrentItem(self.root_item)

        self.tree.currentItemChanged.connect(self.on_current_item_changed)
        self.mode_combo.currentIndexChanged.connect(self.update_mode_fields)
        self.load_item(self.tree.currentItem())
        build_children.clicked.connect(self.build_answer_children_for_current)
        remove.clicked.connect(self.remove_current)
        move_up.clicked.connect(lambda: self.move_current(-1))
        move_down.clicked.connect(lambda: self.move_current(1))
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)

    def item_from_node(self, node: object) -> QTreeWidgetItem | None:
        payload = normalize_guidance_tree_node(node)
        if not payload:
            return None
        answer_option = clean_text(payload.get("answer_option") or payload.get("answerOption"))
        item = QTreeWidgetItem([answer_option or clean_text(payload.get("title")) or "Answer"])
        item.setData(0, Qt.UserRole, {
            "main": clean_multiline_text(payload.get("main")),
            "body": clean_multiline_text(payload.get("body")),
            "mode": normalize_guidance_node_mode(payload.get("type") or payload.get("mode")),
            "question": clean_multiline_text(payload.get("question")),
            "answer": clean_text(payload.get("answer")),
            "wrong": clean_text_list(payload.get("wrong")),
            "answers": clean_text_list(payload.get("answers")),
            "answer_option": answer_option or clean_text(payload.get("title")),
        })
        item.setToolTip(0, clean_multiline_text(payload.get("body")) or clean_multiline_text(payload.get("main")))
        for child in payload.get("children") if isinstance(payload.get("children"), list) else []:
            child_item = self.item_from_node(child)
            if child_item is not None:
                item.addChild(child_item)
        return item

    def save_item(self, item: QTreeWidgetItem | None) -> None:
        if item is None or self.loading_item:
            return
        title = clean_text(self.title_edit.text()) or clean_text(self.answer_text) or "Answer"
        body = ""
        main = ""
        mode = normalize_guidance_node_mode(self.mode_combo.currentData())
        question = clean_multiline_text(self.question_edit.toPlainText())
        answer_lines = clean_text_list(self.wrong_edit.toPlainText())
        answer = answer_lines[0] if answer_lines else ""
        extra_values = answer_lines
        item.setText(0, title)
        item.setData(0, Qt.UserRole, {
            "main": main,
            "body": body,
            "mode": mode,
            "question": question,
            "answer": answer,
            "wrong": extra_values[1:] if mode == "choice" else [],
            "answers": extra_values if mode == "input" else [],
            "answer_option": title,
        })
        item.setToolTip(0, question or title)
        if mode in {"choice", "input"} and answer_lines:
            self.sync_answer_children(item, answer_lines)

    def load_item(self, item: QTreeWidgetItem | None) -> None:
        self.loading_item = True
        try:
            data = item.data(0, Qt.UserRole) if item is not None else {}
            data = data if isinstance(data, dict) else {}
            is_root = item is not None and item is getattr(self, "root_item", None)
            self.title_edit.setText(item.text(0) if item is not None else "")
            mode = normalize_guidance_node_mode(data.get("mode") or data.get("type"))
            index = self.mode_combo.findData(mode)
            self.mode_combo.setCurrentIndex(index if index >= 0 else 0)
            self.question_edit.setPlainText(clean_multiline_text(data.get("question")))
            answer = clean_text(data.get("answer"))
            values = clean_text_list(data.get("answers") if mode == "input" else [answer, *clean_text_list(data.get("wrong"))])
            if answer and not values:
                values = [answer]
            self.wrong_edit.setPlainText("\n".join(values))
            self.connector_edit.setPlainText(clean_multiline_text(data.get("main")))
            self.body_edit.setPlainText(clean_multiline_text(data.get("body")))
            enabled = item is not None
            self.title_edit.setEnabled(enabled and not is_root)
            self.mode_combo.setEnabled(enabled)
            self.question_edit.setEnabled(enabled)
            self.wrong_edit.setEnabled(enabled)
            self.connector_edit.setEnabled(enabled)
            self.body_edit.setEnabled(enabled)
            self.update_mode_fields()
        finally:
            self.loading_item = False

    def update_mode_fields(self) -> None:
        mode = normalize_guidance_node_mode(self.mode_combo.currentData())
        enabled = self.tree.currentItem() is not None
        quiz_enabled = enabled and mode in {"choice", "input"}
        self.question_edit.setEnabled(quiz_enabled)
        self.wrong_edit.setEnabled(quiz_enabled)
        self.wrong_edit.setPlaceholderText(
            "Every line is accepted as correct." if mode == "input" else "First line is correct. Other lines are wrong choices."
        )
        self.connector_edit.setPlaceholderText(
            "Optional connector note. For question nodes, the question itself is shown in the cut-corner connector card."
        )

    def build_answer_children_for_current(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        self.save_item(item)
        data = item.data(0, Qt.UserRole)
        data = data if isinstance(data, dict) else {}
        mode = normalize_guidance_node_mode(data.get("mode"))
        answers = clean_text_list(data.get("answers") if mode == "input" else [data.get("answer"), *clean_text_list(data.get("wrong"))])
        self.sync_answer_children(item, answers)
        self.tree.expandItem(item)

    def sync_answer_children(self, item: QTreeWidgetItem | None, answers: list[str]) -> None:
        if item is None:
            return
        existing_keys: set[str] = set()
        for index in range(item.childCount()):
            child = item.child(index)
            data = child.data(0, Qt.UserRole)
            data = data if isinstance(data, dict) else {}
            key = clean_text(data.get("answer_option") or child.text(0)).casefold()
            if key:
                existing_keys.add(key)
        for answer in answers:
            key = clean_text(answer).casefold()
            if not key or key in existing_keys:
                continue
            child = QTreeWidgetItem([answer])
            child.setData(0, Qt.UserRole, {
                "main": "",
                "body": "",
                "mode": "info",
                "question": "",
                "answer": "",
                "wrong": [],
                "answers": [],
                "answer_option": answer,
            })
            child.setToolTip(0, "Auto-created answer branch")
            item.addChild(child)
            existing_keys.add(key)
        item.setExpanded(True)

    def on_current_item_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None) -> None:
        self.save_item(previous)
        self.load_item(current)

    def make_new_item(self) -> QTreeWidgetItem:
        item = QTreeWidgetItem(["New info card"])
        item.setData(0, Qt.UserRole, {"main": "", "body": "", "mode": "info", "question": "", "answer": "", "wrong": [], "answers": []})
        return item

    def add_child(self) -> None:
        self.save_item(self.tree.currentItem())
        parent = self.tree.currentItem()
        item = self.make_new_item()
        if parent is None:
            self.tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
            parent.setExpanded(True)
        self.tree.setCurrentItem(item)

    def add_sibling(self) -> None:
        self.save_item(self.tree.currentItem())
        current = self.tree.currentItem()
        item = self.make_new_item()
        if current is None:
            self.tree.addTopLevelItem(item)
        else:
            parent = current.parent()
            if parent is None:
                self.tree.insertTopLevelItem(self.tree.indexOfTopLevelItem(current) + 1, item)
            else:
                parent.insertChild(parent.indexOfChild(current) + 1, item)
        self.tree.setCurrentItem(item)

    def remove_current(self) -> None:
        current = self.tree.currentItem()
        if current is None or current is getattr(self, "root_item", None):
            return
        parent = current.parent()
        if parent is None:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(current))
        else:
            parent.takeChild(parent.indexOfChild(current))
        self.load_item(self.tree.currentItem())

    def move_current(self, delta: int) -> None:
        current = self.tree.currentItem()
        if current is None or current is getattr(self, "root_item", None):
            return
        self.save_item(current)
        parent = current.parent()
        if parent is None:
            index = self.tree.indexOfTopLevelItem(current)
            next_index = max(0, min(self.tree.topLevelItemCount() - 1, index + delta))
            if next_index == index:
                return
            item = self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(next_index, item)
        else:
            index = parent.indexOfChild(current)
            next_index = max(0, min(parent.childCount() - 1, index + delta))
            if next_index == index:
                return
            item = parent.takeChild(index)
            parent.insertChild(next_index, item)
        self.tree.setCurrentItem(item)

    def node_from_item(self, item: QTreeWidgetItem) -> dict:
        data = item.data(0, Qt.UserRole)
        data = data if isinstance(data, dict) else {}
        children = [
            child
            for child in (self.node_from_item(item.child(index)) for index in range(item.childCount()))
            if child
        ]
        payload = {
            "title": clean_text(item.text(0)) or "Answer",
            "body": clean_multiline_text(data.get("body")),
            "main": clean_multiline_text(data.get("main")),
        }
        answer_option = clean_text(data.get("answer_option") or data.get("answerOption"))
        if answer_option:
            payload["answer_option"] = answer_option
        mode = normalize_guidance_node_mode(data.get("mode") or data.get("type"))
        question = clean_multiline_text(data.get("question"))
        answer = clean_text(data.get("answer"))
        if mode in {"choice", "input"} and question and answer:
            payload["type"] = mode
            payload["question"] = question
            payload["answer"] = answer
            if mode == "input":
                answers = clean_text_list([answer, *clean_text_list(data.get("answers"))])
                if answers:
                    payload["answers"] = answers
            else:
                wrong = [value for value in clean_text_list(data.get("wrong")) if value.casefold() != answer.casefold()]
                if wrong:
                    payload["wrong"] = wrong
        if children:
            payload["children"] = children
        return normalize_guidance_tree_node(payload)

    def payload(self) -> dict:
        self.save_item(self.tree.currentItem())
        return self.node_from_item(getattr(self, "root_item", None)) if getattr(self, "root_item", None) is not None else {}


class RootNoticeDialog(QDialog):
    def __init__(self, notice: dict, voices: list[tuple[str, str]], parent=None) -> None:
        super().__init__(parent)
        self.voices = list(voices or [])
        self.rows: list[dict] = []
        self.setWindowTitle("Hologram notice dialogue")
        self.setMinimumSize(980, 640)
        if parent is not None and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        title = QLabel("Build a multi-speaker hologram notice. Each turn can use its own voice, name, and avatar picture.")
        title.setObjectName("sectionTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.turn_layout = QVBoxLayout(self.content)
        self.turn_layout.setContentsMargins(6, 6, 6, 6)
        self.turn_layout.setSpacing(10)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)
        buttons = QHBoxLayout()
        add_turn = QPushButton("+ Add speaker turn")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(add_turn)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        for turn in root_notice_turns(notice):
            self.add_turn(turn)
        if not self.rows:
            self.add_turn({})
        add_turn.clicked.connect(lambda: self.add_turn({}))
        done.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)

    def make_voice_combo(self, selected: str = "") -> QComboBox:
        combo = QComboBox()
        combo.addItem("Typing only | no voice", "")
        for label, key in self.voices:
            combo.addItem(label, key)
        selected_key = clean_text(selected)
        if selected_key and combo.findData(selected_key) < 0:
            combo.addItem(embedded_voice_label(selected_key), selected_key)
        index = combo.findData(selected_key)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.setMinimumWidth(260)
        return combo

    def update_avatar_preview(self, row: dict) -> None:
        label = row.get("preview")
        path_edit = row.get("avatar")
        if not isinstance(label, QLabel) or not isinstance(path_edit, QLineEdit):
            return
        raw_path = clean_text(path_edit.text())
        pixmap = QPixmap(raw_path) if raw_path else QPixmap()
        if pixmap.isNull():
            label.setText("Avatar")
            label.setPixmap(QPixmap())
            return
        label.setText("")
        label.setPixmap(pixmap.scaled(66, 66, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def choose_avatar(self, row: dict) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose avatar picture",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*.*)",
        )
        if path and isinstance(row.get("avatar"), QLineEdit):
            row["avatar"].setText(path)
            self.update_avatar_preview(row)

    def collect_turns(self) -> list[dict]:
        turns = []
        for row in self.rows:
            voice_widget = row.get("voice")
            turn = {
                "speaker": clean_text(row["speaker"].text()) if isinstance(row.get("speaker"), QLineEdit) else "",
                "voice": clean_text(voice_widget.currentData()) if isinstance(voice_widget, QComboBox) else "",
                "english": clean_multiline_text(row["english"].toPlainText()) if isinstance(row.get("english"), QPlainTextEdit) else "",
                "vietnamese": clean_multiline_text(row["vietnamese"].toPlainText()) if isinstance(row.get("vietnamese"), QPlainTextEdit) else "",
                "avatar_path": clean_text(row["avatar"].text()) if isinstance(row.get("avatar"), QLineEdit) else "",
            }
            normalized = normalize_root_notice_turn(turn)
            if normalized:
                turns.append(normalized)
        return turns

    def rebuild_rows(self, turns: list[dict]) -> None:
        while self.rows:
            row = self.rows.pop()
            frame = row.get("frame")
            if isinstance(frame, QWidget):
                frame.setParent(None)
                frame.deleteLater()
        for turn in turns:
            self.add_turn(turn)
        if not self.rows:
            self.add_turn({})

    def move_row(self, row: dict, direction: int) -> None:
        turns = self.collect_turns()
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        target = index + int(direction)
        if target < 0 or target >= len(turns):
            return
        turns[index], turns[target] = turns[target], turns[index]
        self.rebuild_rows(turns)

    def remove_row(self, row: dict) -> None:
        if len(self.rows) <= 1:
            for key in ("speaker", "avatar"):
                widget = row.get(key)
                if isinstance(widget, QLineEdit):
                    widget.clear()
            for key in ("english", "vietnamese"):
                widget = row.get(key)
                if isinstance(widget, QPlainTextEdit):
                    widget.clear()
            voice = row.get("voice")
            if isinstance(voice, QComboBox):
                voice.setCurrentIndex(0)
            self.update_avatar_preview(row)
            return
        turns = self.collect_turns()
        try:
            index = self.rows.index(row)
        except ValueError:
            return
        if 0 <= index < len(turns):
            turns.pop(index)
        self.rebuild_rows(turns)

    def add_turn(self, turn: dict) -> None:
        turn = normalize_root_notice_turn(turn)
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        grid = QGridLayout(frame)
        grid.setColumnStretch(2, 1)
        index_label = QLabel(f"Turn {len(self.rows) + 1}")
        index_label.setObjectName("sectionTitle")
        preview = QLabel("Avatar")
        preview.setFixedSize(72, 72)
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet("border:1px solid rgba(70,240,215,.38); border-radius:6px; background:#061719; color:rgba(236,255,249,.58);")
        speaker = QLineEdit(clean_text(turn.get("speaker")))
        speaker.setPlaceholderText("Character name, e.g. Captain Mira")
        voice = self.make_voice_combo(clean_text(turn.get("voice")))
        avatar_value = clean_text(turn.get("avatar_path"))
        if not avatar_value and isinstance(turn.get("avatar"), dict):
            avatar_value = clean_text(turn["avatar"].get("url"))
        avatar = QLineEdit(avatar_value)
        avatar.setPlaceholderText("Avatar picture path")
        browse = QPushButton("Browse")
        english = QPlainTextEdit()
        english.setPlainText(clean_multiline_text(turn.get("english")))
        english.setPlaceholderText("English line spoken by this character")
        english.setFixedHeight(86)
        vietnamese = QPlainTextEdit()
        vietnamese.setPlainText(clean_multiline_text(turn.get("vietnamese")))
        vietnamese.setPlaceholderText("Vietnamese support line")
        vietnamese.setFixedHeight(58)
        up = QPushButton("Up")
        down = QPushButton("Down")
        remove = QPushButton("Remove")
        row = {
            "frame": frame,
            "preview": preview,
            "speaker": speaker,
            "voice": voice,
            "avatar": avatar,
            "english": english,
            "vietnamese": vietnamese,
        }
        grid.addWidget(preview, 0, 0, 3, 1)
        grid.addWidget(index_label, 0, 1)
        grid.addWidget(QLabel("Character"), 1, 1)
        grid.addWidget(speaker, 1, 2)
        grid.addWidget(QLabel("Voice"), 1, 3)
        grid.addWidget(voice, 1, 4)
        grid.addWidget(QLabel("Avatar"), 2, 1)
        grid.addWidget(avatar, 2, 2, 1, 2)
        grid.addWidget(browse, 2, 4)
        grid.addWidget(QLabel("English"), 3, 0)
        grid.addWidget(english, 3, 1, 1, 4)
        grid.addWidget(QLabel("Vietnamese"), 4, 0)
        grid.addWidget(vietnamese, 4, 1, 1, 4)
        controls = QHBoxLayout()
        controls.addWidget(up)
        controls.addWidget(down)
        controls.addWidget(remove)
        controls.addStretch(1)
        grid.addLayout(controls, 5, 1, 1, 4)
        browse.clicked.connect(lambda _checked=False, r=row: self.choose_avatar(r))
        avatar.textChanged.connect(lambda _text="", r=row: self.update_avatar_preview(r))
        up.clicked.connect(lambda _checked=False, r=row: self.move_row(r, -1))
        down.clicked.connect(lambda _checked=False, r=row: self.move_row(r, 1))
        remove.clicked.connect(lambda _checked=False, r=row: self.remove_row(r))
        self.rows.append(row)
        self.turn_layout.addWidget(frame)
        self.update_avatar_preview(row)

    def payload(self) -> dict:
        return normalize_root_notice_payload({"turns": self.collect_turns()})


def decode_base64url(value: str) -> bytes:
    raw = clean_text(value).replace("-", "+").replace("_", "/")
    raw += "=" * ((4 - len(raw) % 4) % 4)
    return base64.b64decode(raw.encode("ascii"))


def decode_space_q_payload(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        raise RuntimeError("File Space_Q rỗng.")
    if text.startswith("{"):
        payload = json.loads(text)
        if isinstance(payload, dict) and payload.get("k") == "ftg_manifest" and payload.get("structure"):
            structure = clean_text(payload.get("structure")).replace("\\", "/").lstrip("/")
            target = SERVER_DATA_ROOT / structure
            if not target.is_file():
                raise RuntimeError(f"Không tìm thấy structure: {target}")
            return json.loads(target.read_text(encoding="utf-8-sig", errors="replace"))
        if isinstance(payload, dict):
            return payload
        raise RuntimeError("JSON Space_Q không hợp lệ.")
    code = re.sub(r"\s+", "", text)
    if not code.startswith(CODE_PREFIX):
        raise RuntimeError("File không đúng định dạng Space_Q/FTG1.")
    raw = gzip.decompress(decode_base64url(code[len(CODE_PREFIX):]))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Payload Space_Q không hợp lệ.")
    return payload


def question_voice_specs() -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    seen: set[str] = set()

    def append(label: str, key: str) -> None:
        clean_key = clean_text(key)
        if not clean_key:
            return
        lowered = clean_key.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        specs.append((clean_text(label) or embedded_voice_label(clean_key), clean_key))

    for provider in (grammar_vietnamese_voice_specs, sound_of_text_voice_specs, edge_english_voice_specs, microsoft_voice_specs, people_voice_specs):
        try:
            for label, key in provider():
                append(label, key)
        except Exception:
            continue
    if not specs:
        append("Sound of Text | Female US", "sot:en-US")
    return specs


def split_question_line(line: str) -> list[str]:
    raw = str(line or "").strip()
    if not raw:
        return []
    if "\t" in raw:
        return [item.strip() for item in raw.split("\t")]
    if "|" in raw:
        return [item.strip() for item in raw.split("|")]
    try:
        return [item.strip() for item in next(csv.reader([raw]))]
    except Exception:
        return [item.strip() for item in raw.split(",")]


def normalize_loaded_questions(items: object) -> list[dict]:
    if not isinstance(items, list):
        return []
    result: list[dict] = []
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            continue
        wrong = raw_item.get("wrong") if isinstance(raw_item.get("wrong"), list) else raw_item.get("wrongs")
        if not isinstance(wrong, list):
            wrong = raw_item.get("w") if isinstance(raw_item.get("w"), list) else []
        answers = raw_item.get("answers") if isinstance(raw_item.get("answers"), list) else raw_item.get("accept")
        if not isinstance(answers, list):
            answers = raw_item.get("accepts") if isinstance(raw_item.get("accepts"), list) else []
        qtype = clean_text(raw_item.get("type") or raw_item.get("mode") or raw_item.get("t") or "choice").lower()
        qtype_key = normalize_question_type(qtype)
        question = clean_text(raw_item.get("question") or raw_item.get("q"))
        raw_answer_text = clean_multiline_text(raw_item.get("answer") or raw_item.get("a"))
        select_tokens = select_token_list(
            raw_item.get("tokens") or raw_item.get("select_tokens") or raw_item.get("selectTokens") or raw_item.get("tk"),
            raw_answer_text,
        ) if qtype_key == "select" else []
        answer = " ".join(select_tokens) if qtype_key == "select" and select_tokens else clean_text(raw_answer_text)
        select_targets = normalize_select_targets_payload(raw_item.get("select_targets") or raw_item.get("selectTargets") or raw_item.get("selection_targets") or raw_item.get("selectionTargets") or raw_item.get("stg"))
        if qtype_key == "select" and not answer and select_targets:
            answer = select_targets_fallback_answer(select_targets)
        if not question or not answer:
            continue
        raw_card_mode = raw_item.get("card_mode") or raw_item.get("cardMode") or raw_item.get("question_card_mode") or raw_item.get("questionCardMode") or raw_item.get("display_mode") or raw_item.get("displayMode") or raw_item.get("cm")
        question_audio = raw_item.get("audio") if isinstance(raw_item.get("audio"), dict) else (raw_item.get("question_audio") if isinstance(raw_item.get("question_audio"), dict) else raw_item.get("questionAudio"))
        question_audio = question_audio if isinstance(question_audio, dict) else {}
        answer_audio = raw_item.get("answer_audio") if isinstance(raw_item.get("answer_audio"), dict) else raw_item.get("answerAudio")
        answer_audio = answer_audio if isinstance(answer_audio, dict) else {}
        answer_info = raw_item.get("answer_info") if isinstance(raw_item.get("answer_info"), dict) else raw_item.get("answerInfo")
        answer_info = answer_info if isinstance(answer_info, dict) else {}
        root_highlights = raw_item.get("root_highlights") if isinstance(raw_item.get("root_highlights"), list) else raw_item.get("rootHighlights")
        if not isinstance(root_highlights, list):
            root_highlights = []
        root_notice = normalize_root_notice_payload(raw_item.get("root_notice") or raw_item.get("rootNotice") or raw_item.get("rn"))
        guidance_tree = normalize_guidance_tree_payload(raw_item.get("guidance_tree") or raw_item.get("guidanceTree") or raw_item.get("guide_tree") or raw_item.get("gt"))
        normalized_highlights = []
        for highlight in root_highlights:
            if not isinstance(highlight, dict):
                continue
            try:
                start = int(highlight.get("start") or highlight.get("s") or 0)
                end = int(highlight.get("end") or highlight.get("e") or 0)
            except Exception:
                start, end = 0, 0
            highlight_text = clean_multiline_text(highlight.get("text") or highlight.get("t"))
            picture_question = normalize_picture_question_payload(highlight, question)
            if end > start or highlight_text or picture_question:
                item_payload = {
                    "start": max(0, start),
                    "end": max(0, end),
                    "text": highlight_text,
                    "color": safe_color(highlight.get("color") or highlight.get("c")),
                    "style": clean_text(highlight.get("style") or highlight.get("st")) or "style-1",
                    "render": safe_highlight_render(highlight.get("render") or highlight.get("mode") or highlight.get("m")),
                    "info": clean_multiline_text(highlight.get("info") or highlight.get("note") or highlight.get("card") or highlight.get("i")),
                }
                if highlight_camera_focus_enabled(highlight):
                    item_payload["camera_focus"] = True
                if picture_question:
                    item_payload["picture_question"] = picture_question
                normalized_highlights.append(item_payload)
        inferred_card_mode = "linking" if any(isinstance(item, dict) and item.get("picture_question") for item in normalized_highlights) else "question"
        try:
            order_value = int(float(raw_item.get("order") or raw_item.get("o") or raw_item.get("sort") or raw_item.get("stt") or 0))
        except Exception:
            order_value = 0
        question_audio_mode = clean_text(question_audio.get("mode") or question_audio.get("playback") or ("click" if clean_text(question_audio.get("url") or question_audio.get("u")) else "off")).lower()
        answer_audio_mode = clean_text(answer_audio.get("mode") or answer_audio.get("playback") or ("click" if clean_text(answer_audio.get("url") or answer_audio.get("u")) else "off")).lower()
        result.append({
            "id": clean_text(raw_item.get("id") or raw_item.get("i")) or f"q-{index + 1}",
            "type": qtype_key,
            "card_mode": normalize_question_card_mode(raw_card_mode, inferred_card_mode),
            "order": max(0, order_value),
            "question": question,
            "answer": answer,
            "tokens": select_tokens,
            "answers": [clean_text(value.get("text") if isinstance(value, dict) else value) for value in answers if clean_text(value.get("text") if isinstance(value, dict) else value)],
            "wrong": [] if qtype_key == "select" else [clean_text(value.get("text") if isinstance(value, dict) else value) for value in wrong if clean_text(value.get("text") if isinstance(value, dict) else value)],
            "audio": question_audio,
            "audio_mode": question_audio_mode,
            "audio_voice": clean_text(question_audio.get("voice") or question_audio.get("v")),
            "answer_audio": answer_audio,
            "answer_audio_mode": answer_audio_mode,
            "answer_audio_voice": clean_text(answer_audio.get("voice") or answer_audio.get("v")),
            "answer_info": answer_info,
            "root_highlights": normalized_highlights,
            "root_notice": root_notice,
            "guidance_tree": guidance_tree,
        })
        if select_targets:
            result[-1]["select_targets"] = select_targets
    return result


def nodes_from_space_q_payload(payload: dict) -> list[dict]:
    nodes_raw = payload.get("nodes") if isinstance(payload.get("nodes"), list) else payload.get("n")
    if not isinstance(nodes_raw, list):
        return []
    result: list[dict] = []
    for index, raw_node in enumerate(nodes_raw):
        if not isinstance(raw_node, dict):
            continue
        cards = raw_node.get("cards") if isinstance(raw_node.get("cards"), dict) else raw_node.get("c")
        cards = cards if isinstance(cards, dict) else {}
        root_card = cards.get("root") if isinstance(cards.get("root"), dict) else cards.get("r")
        root_card = root_card if isinstance(root_card, dict) else {}
        picture = cards.get("picture") or cards.get("pic") or cards.get("p") or raw_node.get("picture") or raw_node.get("pic")
        picture = picture if isinstance(picture, dict) else {}
        audio = cards.get("audio") or cards.get("a") or raw_node.get("audio")
        audio = audio if isinstance(audio, dict) else {}
        questions = cards.get("questions") or cards.get("qs") or raw_node.get("questions") or raw_node.get("qs")
        root = clean_multiline_text(raw_node.get("root") or raw_node.get("r") or root_card.get("text") or root_card.get("t"))
        if not root:
            continue
        picture_url = clean_text(picture.get("url") or picture.get("u") or picture.get("path"))
        picture_name = clean_text(picture.get("name") or Path(picture_url).name)
        picture_region_color = safe_color(
            picture.get("region_color")
            or picture.get("regionColor")
            or picture.get("region")
            or picture.get("rc")
            or raw_node.get("picture_region_color")
            or raw_node.get("pictureRegionColor"),
            DEFAULT_PICTURE_REGION_COLOR,
        )
        audio_url = clean_text(audio.get("url") or audio.get("u") or audio.get("path"))
        audio_voice = clean_text(audio.get("voice") or audio.get("v")) or "sot:en-US"
        audio_text = clean_text(audio.get("text") or audio.get("t"))
        root_size_raw = root_card.get("font_size") or root_card.get("fontSize") or root_card.get("fs") or raw_node.get("root_font_size") or 20
        try:
            root_size = int(float(root_size_raw))
        except Exception:
            root_size = 56
        input_text_color = safe_color(
            root_card.get("input_text_color")
            or root_card.get("inputTextColor")
            or root_card.get("itc")
            or raw_node.get("input_text_color")
            or raw_node.get("inputTextColor")
            or raw_node.get("itc"),
            DEFAULT_INPUT_TEXT_COLOR,
        )
        input_text_prysm = bool_value(
            root_card.get("input_text_prysm")
            or root_card.get("inputTextPrysm")
            or root_card.get("input_prysm")
            or root_card.get("prysm")
            or raw_node.get("input_text_prysm")
            or raw_node.get("inputTextPrysm")
            or raw_node.get("input_prysm")
            or raw_node.get("prysm")
        )
        node = {
            "id": clean_text(raw_node.get("id") or raw_node.get("i")) or node_id_for(root),
            "root": root,
            "root_font_size": max(18, min(120, root_size)),
            "input_text_color": input_text_color,
            "input_text_prysm": input_text_prysm,
            "connector_style": clean_text(raw_node.get("connector_style") or raw_node.get("connectorStyle") or raw_node.get("cs") or root_card.get("connector_style") or root_card.get("connectorStyle") or root_card.get("cs")) or "connector-1",
            "ship_type": normalize_ship_type(raw_node.get("ship_type") or raw_node.get("shipType") or raw_node.get("st") or root_card.get("ship_type") or root_card.get("shipType") or root_card.get("st")),
            "picture_enabled": bool(picture_url),
            "picture_path": f"[embedded] {picture_url}" if picture_url else "",
            "picture_caption": clean_text(picture.get("caption") or picture.get("c") or picture_name),
            "picture_region_color": picture_region_color,
            "picture_asset_url": picture_url,
            "picture_asset_name": picture_name,
            "audio_enabled": bool(audio_url or audio_text),
            "audio_text": audio_text,
            "audio_voice": audio_voice,
            "audio_asset_url": audio_url,
            "audio_asset_mime": clean_text(audio.get("mime") or audio.get("m") or "audio/mpeg"),
            "audio_asset_id": clean_text(audio.get("id") or audio.get("i")),
            "audio_asset_text": audio_text,
            "audio_asset_voice": audio_voice,
            "audio_asset_voice_label": clean_text(audio.get("voice_label") or audio.get("label")),
            "questions_enabled": bool(questions),
            "questions": normalize_loaded_questions(questions),
        }
        result.append(node)
    return result


class QuestionDialog(QDialog):
    def __init__(
        self,
        questions: list[dict],
        settings: dict,
        voices: list[tuple[str, str]],
        parent=None,
        initial_row: int = -1,
        open_settings: bool = False,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.voices = list(voices or [])
        self.info_voices = self.build_info_voices()
        self.question_settings: dict[int, dict] = {}
        self.root_highlights: dict[int, list[dict]] = {}
        self.root_notices: dict[int, dict] = {}
        self.guidance_trees: dict[int, dict] = {}
        self.select_targets: dict[int, dict] = {}
        parent_root_text = ""
        if parent is not None and hasattr(parent, "root_text"):
            try:
                parent_root_text = str(parent.root_text.toPlainText() or "")
            except Exception:
                parent_root_text = ""
        self.root_preview_text = parent_root_text.replace("\r\n", "\n").replace("\r", "\n")
        self.picture_preview_path = ""
        self.picture_preview_asset_url = ""
        self.default_picture_region_color = DEFAULT_PICTURE_REGION_COLOR
        if parent is not None:
            try:
                node = parent.nodes[parent.current_row] if 0 <= parent.current_row < len(parent.nodes) else {}
            except Exception:
                node = {}
            self.picture_preview_path = clean_text(node.get("picture_path") if isinstance(node, dict) else "")
            self.picture_preview_asset_url = clean_text(node.get("picture_asset_url") if isinstance(node, dict) else "")
            if isinstance(node, dict):
                self.default_picture_region_color = safe_color(node.get("picture_region_color"), DEFAULT_PICTURE_REGION_COLOR)
        self.order_column = 0
        self.type_column = 1
        self.card_mode_column = 2
        self.question_column = 3
        self.answer_column = 4
        self.wrong_start_column = 5
        self.default_wrong_columns = 3
        if parent is not None and hasattr(parent, "styleSheet"):
            self.setStyleSheet(parent.styleSheet())
        self.setWindowTitle("Question card")
        self.resize(1260, 720)
        layout = QVBoxLayout(self)
        title = QLabel("Tạo câu hỏi cho card Question")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.table = QTableWidget(0, self.wrong_start_column + self.default_wrong_columns)
        self.refresh_question_headers()
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(58)
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        self.table.setColumnWidth(self.order_column, 82)
        self.table.setColumnWidth(self.type_column, 128)
        self.table.setColumnWidth(self.card_mode_column, 188)
        self.table.setColumnWidth(self.question_column, 420)
        self.table.setColumnWidth(self.answer_column, 250)
        for column in range(self.wrong_start_column, self.table.columnCount()):
            self.table.setColumnWidth(column, 210)
        self.table.setMinimumSize(980, 420)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_question_context_menu)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        add_choice = QPushButton("Add trắc nghiệm")
        add_input = QPushButton("Add tự luận")
        add_select = QPushButton("Add select")
        add_guidance = QPushButton("Add guidance")
        import_txt = QPushButton("Load TXT nhiều cột")
        question_setting = QPushButton("Question setting")
        highlight_setting = QPushButton("Root highlight")
        add_wrong = QPushButton("+ wrong column")
        remove = QPushButton("Xóa dòng")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(add_choice)
        buttons.addWidget(add_input)
        buttons.addWidget(add_select)
        buttons.addWidget(add_guidance)
        buttons.addWidget(import_txt)
        buttons.addWidget(question_setting)
        buttons.addWidget(highlight_setting)
        buttons.addWidget(add_wrong)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        add_choice.clicked.connect(lambda: self.add_question_row({"type": "choice"}))
        add_input.clicked.connect(lambda: self.add_question_row({"type": "input"}))
        add_select.clicked.connect(lambda: self.add_question_row({"type": "select"}))
        add_guidance.clicked.connect(lambda: self.add_question_row({"type": "guide"}))
        import_txt.clicked.connect(self.import_txt)
        question_setting.clicked.connect(self.edit_question_settings)
        highlight_setting.clicked.connect(self.edit_root_highlights)
        add_wrong.clicked.connect(self.add_wrong_column)
        remove.clicked.connect(self.remove_selected_rows)
        done.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        for item in questions or []:
            self.add_question_row(item)
        if not self.table.rowCount():
            self.add_question_row({"type": "choice"})
        if 0 <= initial_row < self.table.rowCount():
            self.table.setCurrentCell(initial_row, self.question_column)
            self.table.selectRow(initial_row)

    def refresh_question_headers(self) -> None:
        headers = ["Order", "Type", "Card mode", "Question", "Correct"]
        headers.extend(f"Wrong / Alt {index + 1}" for index in range(max(0, self.table.columnCount() - self.wrong_start_column)))
        self.table.setHorizontalHeaderLabels(headers)

    def ensure_wrong_columns(self, count: int) -> None:
        wanted = self.wrong_start_column + max(self.default_wrong_columns, int(count or 0))
        while self.table.columnCount() < wanted:
            column = self.table.columnCount()
            self.table.insertColumn(column)
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Interactive)
            self.table.setColumnWidth(column, 210)
        self.refresh_question_headers()

    def add_wrong_column(self) -> None:
        self.ensure_wrong_columns(self.table.columnCount() - self.wrong_start_column + 1)

    def build_info_voices(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        seen: set[str] = set()
        for provider in (grammar_vietnamese_voice_specs, lambda: self.voices):
            try:
                values = provider()
            except Exception:
                values = []
            for label, key in values:
                clean_key = clean_text(key)
                lowered = clean_key.lower()
                if clean_key and lowered not in seen:
                    seen.add(lowered)
                    options.append((clean_text(label) or embedded_voice_label(clean_key), clean_key))
        if not options:
            options.append(("Sound of Text | Vietnamese", "sot:vi-VN"))
        preferred = DEFAULT_INFO_VOICE.lower()
        options.sort(key=lambda item: 0 if clean_text(item[1]).lower() == preferred else 1)
        return options

    def default_info_voice(self) -> str:
        for _label, key in self.info_voices:
            if clean_text(key).lower() == DEFAULT_INFO_VOICE.lower():
                return clean_text(key)
        return self.info_voices[0][1] if self.info_voices else "sot:vi-VN"

    def make_voice_combo(self, selected: str = "") -> QComboBox:
        combo = QComboBox()
        for label, key in self.voices:
            combo.addItem(label, key)
        selected_key = clean_text(selected)
        if selected_key and combo.findData(selected_key) < 0:
            combo.addItem(embedded_voice_label(selected_key), selected_key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_optional_voice_combo(self, selected: str = "") -> QComboBox:
        combo = QComboBox()
        combo.addItem("Typing only | no voice", "")
        for label, key in self.voices:
            combo.addItem(label, key)
        selected_key = clean_text(selected)
        if selected_key and combo.findData(selected_key) < 0:
            combo.addItem(embedded_voice_label(selected_key), selected_key)
        index = combo.findData(selected_key)
        combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    def make_info_voice_combo(self, selected: str = "") -> QComboBox:
        combo = QComboBox()
        for label, key in self.info_voices:
            combo.addItem(label, key)
        selected_key = clean_text(selected)
        if selected_key and combo.findData(selected_key) < 0:
            combo.addItem(embedded_voice_label(selected_key), selected_key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_mode_combo(self, selected: str = "off") -> QComboBox:
        combo = QComboBox()
        selected_key = clean_text(selected).lower() or "off"
        if selected_key not in {key for _label, key in QUESTION_AUDIO_MODES}:
            selected_key = "off"
        for label, key in QUESTION_AUDIO_MODES:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_question_type_combo(self, selected: str = "choice") -> QComboBox:
        combo = QComboBox()
        selected_key = normalize_question_type(selected)
        combo.addItem("Choice", "choice")
        combo.addItem("Input", "input")
        combo.addItem("Select tokens", "select")
        combo.addItem("Guidance", "guide")
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_question_card_mode_combo(self, selected: str = "question") -> QComboBox:
        combo = QComboBox()
        selected_key = normalize_question_card_mode(selected)
        for label, key in QUESTION_CARD_MODES:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_info_mode_combo(self, selected: str = "audio") -> QComboBox:
        combo = QComboBox()
        selected_key = normalize_info_mode(selected, "audio")
        for label, key in QUESTION_INFO_MODES:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_highlight_style_combo(self, selected: str = "style-1") -> QComboBox:
        combo = QComboBox()
        combo.setMinimumWidth(440)
        selected_key = clean_text(selected) or "style-1"
        valid = {key for _label, key in HIGHLIGHT_STYLES}
        if selected_key not in valid:
            selected_key = "style-1"
        for label, key in HIGHLIGHT_STYLES:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_highlight_render_combo(self, selected: str = "text") -> QComboBox:
        combo = QComboBox()
        selected_key = safe_highlight_render(selected)
        for label, key in HIGHLIGHT_RENDER_MODES:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_picture_question_anchor_combo(self, selected: str = "highlight") -> QComboBox:
        combo = QComboBox()
        selected_key = safe_picture_question_anchor(selected)
        for label, key in PICTURE_QUESTION_ANCHORS:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_picture_question_placement_combo(self, selected: str = "auto") -> QComboBox:
        combo = QComboBox()
        selected_key = safe_picture_question_placement(selected)
        for label, key in PICTURE_QUESTION_PLACEMENTS:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def picture_source_path(self) -> Path | None:
        raw_path = clean_text(self.picture_preview_path)
        if raw_path.startswith("[embedded]"):
            raw_path = clean_text(raw_path.replace("[embedded]", "", 1))
        candidates: list[Path] = []
        if raw_path:
            candidates.append(Path(raw_path))
        asset_url = clean_text(self.picture_preview_asset_url) or raw_path
        if asset_url and not re.match(r"^[a-z]+://", asset_url, re.I):
            safe_asset = asset_url.replace("\\", "/").lstrip("/")
            candidates.append(SERVER_DATA_ROOT / safe_asset)
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate
            except Exception:
                continue
        return None

    def edit_picture_question_region_settings(
        self,
        regions: list[dict] | None = None,
        color: object | None = None,
    ) -> tuple[list[dict], str] | None:
        image_path = self.picture_source_path()
        if not image_path:
            QMessageBox.information(
                self,
                APP_TITLE,
                "No local picture file is available for this node. Choose or load the Picture card image first.",
            )
            return None
        dialog = PictureRegionDialog(
            image_path,
            normalize_picture_question_regions(regions or []),
            safe_color(color or self.default_picture_region_color, DEFAULT_PICTURE_REGION_COLOR),
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return None
        return dialog.regions(), dialog.region_color()

    def edit_picture_question_regions(self, regions: list[dict] | None = None) -> list[dict] | None:
        result = self.edit_picture_question_region_settings(regions)
        return result[0] if result else None

    def update_region_button(self, button: QPushButton, regions: list[dict] | None, color: object | None = None) -> None:
        count = len(normalize_picture_question_regions(regions or []))
        suffix = f" | {safe_color(color, self.default_picture_region_color).upper()}" if color else ""
        button.setText(f"Picture regions: {count}{suffix}")
        button.setToolTip("Open the embedded picture and select target regions.")

    def combo_value(self, row: int, column: int) -> str:
        widget = self.table.cellWidget(row, column)
        if isinstance(widget, QComboBox):
            return clean_text(widget.currentData())
        item = self.table.item(row, column)
        return clean_text(item.text() if item else "")

    def question_text_for_row(self, row: int) -> str:
        if row < 0 or row >= self.table.rowCount():
            return ""
        item = self.table.item(row, self.question_column)
        return clean_multiline_text(item.text() if item else "")

    def set_question_text_for_row(self, row: int, value: object) -> None:
        text = clean_multiline_text(value)
        if not text or row < 0 or row >= self.table.rowCount():
            return
        item = self.table.item(row, self.question_column)
        if item is None:
            self.table.setItem(row, self.question_column, QTableWidgetItem(text))
            return
        if clean_multiline_text(item.text()) != text:
            item.setText(text)

    def answer_key(self, value: str) -> str:
        return re.sub(r"\s+", " ", clean_text(value).lower()).strip()

    def current_root_selection_payload(self) -> dict:
        parent = self.parent()
        if parent is not None and hasattr(parent, "root_selection_payload"):
            try:
                payload = parent.root_selection_payload()
            except Exception:
                payload = {}
            if isinstance(payload, dict) and clean_multiline_text(payload.get("text")):
                return dict(payload)
        return {}

    def pick_root_highlight_payload(self, fallback_question_text: object = "") -> dict:
        source = self.root_preview_text or ""
        if not source:
            QMessageBox.information(self, APP_TITLE, "Root text đang trống.")
            return {}
        dialog = QDialog(self)
        dialog.setWindowTitle("Add selection from Root text")
        dialog.resize(900, 700)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Select a Root text range for this question.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        editor = QPlainTextEdit()
        editor.setPlainText(source)
        editor.setReadOnly(True)
        editor.setMinimumHeight(260)
        layout.addWidget(editor, 1)
        selected_color = {"value": "#ffff00"}
        options = QGridLayout()
        layout.addLayout(options)
        options.addWidget(QLabel("Highlight style"), 0, 0)
        style_combo = self.make_highlight_style_combo("style-2")
        options.addWidget(style_combo, 0, 1)
        options.addWidget(QLabel("Render mode"), 1, 0)
        render_combo = self.make_highlight_render_combo("block")
        options.addWidget(render_combo, 1, 1)
        pan_check = QCheckBox("Kéo màn hình sang highlight/region trước khi chạy hiệu ứng")
        pan_check.setToolTip("Chỉ bật cho highlight cần người học nhìn trực tiếp trước; mặc định tắt để tránh chóng mặt.")
        options.addWidget(QLabel("Camera focus"), 2, 0)
        options.addWidget(pan_check, 2, 1)
        options.addWidget(QLabel("Info card text"), 3, 0)
        info_edit = QPlainTextEdit()
        info_edit.setPlaceholderText("Optional info card text for this highlighted range.")
        info_edit.setMinimumHeight(86)
        options.addWidget(info_edit, 3, 1)
        options.addWidget(QLabel("Linking question card"), 4, 0)
        picture_question_edit = QPlainTextEdit()
        picture_question_edit.setPlaceholderText("Optional Linking question text. If no Root text is selected, it anchors to the question root or picture card.")
        picture_question_edit.setMinimumHeight(96)
        options.addWidget(picture_question_edit, 4, 1)
        options.addWidget(QLabel("Bubble anchor"), 5, 0)
        picture_anchor_combo = self.make_picture_question_anchor_combo("highlight")
        options.addWidget(picture_anchor_combo, 5, 1)
        options.addWidget(QLabel("Bubble placement"), 6, 0)
        picture_placement_combo = self.make_picture_question_placement_combo("auto")
        options.addWidget(picture_placement_combo, 6, 1)
        picture_regions: list[dict] = []
        picture_region_color = {"value": self.default_picture_region_color}
        region_row = QHBoxLayout()
        picture_region_button = QPushButton("Picture regions: 0")
        picture_region_hint = QLabel("Optional: connect this Linking question to selected picture areas.")
        region_row.addWidget(picture_region_button)
        region_row.addWidget(picture_region_hint, 1)
        options.addWidget(QLabel("Picture regions"), 7, 0)
        options.addLayout(region_row, 7, 1)
        buttons = QHBoxLayout()
        color_button = QPushButton("Color #ffff00")
        add_button = QPushButton("Add highlight")
        cancel = QPushButton("Cancel")
        buttons.addWidget(color_button)
        buttons.addStretch(1)
        buttons.addWidget(add_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        def update_color_button() -> None:
            color = safe_color(selected_color["value"])
            color_button.setText(f"Color {color}")
            color_button.setStyleSheet(f"background: {color}; color: #061112; font-weight: 900; border-radius: 10px; padding: 9px;")

        def choose_color() -> None:
            color = QColorDialog.getColor(QColor(safe_color(selected_color["value"])), dialog, "Choose highlight color")
            if color.isValid():
                selected_color["value"] = color.name()
                update_color_button()

        update_color_button()
        color_button.clicked.connect(choose_color)

        def choose_picture_regions() -> None:
            selected = self.edit_picture_question_region_settings(picture_regions, picture_region_color["value"])
            if selected is None:
                return
            selected_regions, selected_color = selected
            picture_regions[:] = selected_regions
            picture_region_color["value"] = selected_color
            if picture_regions:
                index = picture_anchor_combo.findData("picture_regions")
                if index >= 0:
                    picture_anchor_combo.setCurrentIndex(index)
            self.update_region_button(picture_region_button, picture_regions, picture_region_color["value"])

        picture_region_button.clicked.connect(choose_picture_regions)
        add_button.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return {}
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, APP_TITLE, "Hãy chọn một đoạn Root text trong khung trước.")
            return {}
        start = min(cursor.position(), cursor.anchor())
        end = max(cursor.position(), cursor.anchor())
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        payload = {
            "start": start,
            "end": end,
            "text": selected_text,
            "color": safe_color(selected_color["value"]),
            "style": clean_text(style_combo.currentData()) or "style-2",
            "render": safe_highlight_render(render_combo.currentData()),
            "info": clean_multiline_text(info_edit.toPlainText()),
        }
        if pan_check.isChecked():
            payload["camera_focus"] = True
        picture_question_text = clean_multiline_text(picture_question_edit.toPlainText())
        picture_question_text = picture_question_text or clean_multiline_text(fallback_question_text)
        if picture_question_text and (clean_multiline_text(picture_question_edit.toPlainText()) or picture_regions):
            payload["picture_question"] = {
                "text": picture_question_text,
                "anchor": "picture_regions" if picture_regions else safe_picture_question_anchor(picture_anchor_combo.currentData()),
                "placement": safe_picture_question_placement(picture_placement_combo.currentData()),
            }
            if picture_regions:
                payload["picture_question"]["regions"] = normalize_picture_question_regions(picture_regions)
                payload["picture_question"]["region_color"] = safe_color(picture_region_color["value"], self.default_picture_region_color)
        return payload

    def add_root_selection_to_row(self, row: int, open_editor: bool = True, force_picker: bool = False) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        row_question_text = self.question_text_for_row(row)
        payload = self.pick_root_highlight_payload(row_question_text) if force_picker else self.current_root_selection_payload()
        if not payload and not force_picker:
            payload = self.pick_root_highlight_payload(row_question_text)
            open_editor = False
        if not payload:
            return
        self.table.setCurrentCell(row, self.question_column)
        self.table.selectRow(row)
        highlights = self.root_highlights.setdefault(row, [])
        item_payload = {
            "start": max(0, int(payload.get("start") or 0)),
            "end": max(0, int(payload.get("end") or 0)),
            "text": clean_multiline_text(payload.get("text")),
            "color": safe_color(payload.get("color") or "#ffff00"),
            "style": clean_text(payload.get("style")) or "style-2",
            "render": safe_highlight_render(payload.get("render") or payload.get("mode") or "block"),
            "info": clean_multiline_text(payload.get("info")),
        }
        if highlight_camera_focus_enabled(payload):
            item_payload["camera_focus"] = True
        picture_question = normalize_picture_question_payload(payload, row_question_text)
        if picture_question:
            if clean_multiline_text(picture_question.get("text")) != row_question_text:
                self.set_question_text_for_row(row, picture_question.get("text"))
            item_payload["picture_question"] = picture_question
        highlights.append(item_payload)
        if open_editor:
            self.edit_root_highlights()

    def add_picture_question_to_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Add linking question card")
        dialog.resize(760, 430)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Create a Linking question card connected to the selected text, question root, or picture ship/card.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        question_edit = QPlainTextEdit()
        question_edit.setPlaceholderText("Linking Question uses the main Question text.")
        current_question_text = self.question_text_for_row(row)
        if current_question_text:
            question_edit.setPlainText(current_question_text)
        question_edit.setMinimumHeight(150)
        layout.addWidget(question_edit, 1)
        options = QGridLayout()
        layout.addLayout(options)
        options.addWidget(QLabel("Anchor"), 0, 0)
        anchor_combo = self.make_picture_question_anchor_combo("picture")
        options.addWidget(anchor_combo, 0, 1)
        placement_combo = self.make_picture_question_placement_combo("auto")
        options.addWidget(QLabel("Placement"), 1, 0)
        options.addWidget(placement_combo, 1, 1)
        pan_check = QCheckBox("Kéo màn hình sang vùng ảnh trước khi chạy animation")
        pan_check.setToolTip("Mặc định tắt. Chỉ bật nếu muốn người học nhìn vùng ảnh được chọn trước khi quay lại card hỏi.")
        options.addWidget(QLabel("Camera focus"), 2, 0)
        options.addWidget(pan_check, 2, 1)
        picture_regions: list[dict] = []
        picture_region_color = {"value": self.default_picture_region_color}
        picture_region_button = QPushButton("Picture regions: 0")
        options.addWidget(QLabel("Picture regions"), 3, 0)
        options.addWidget(picture_region_button, 3, 1)
        buttons = QHBoxLayout()
        add_button = QPushButton("Add Linking card")
        cancel = QPushButton("Cancel")
        buttons.addStretch(1)
        buttons.addWidget(add_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        def choose_picture_regions() -> None:
            selected = self.edit_picture_question_region_settings(picture_regions, picture_region_color["value"])
            if selected is None:
                return
            selected_regions, selected_color = selected
            picture_regions[:] = selected_regions
            picture_region_color["value"] = selected_color
            if picture_regions:
                index = anchor_combo.findData("picture_regions")
                if index >= 0:
                    anchor_combo.setCurrentIndex(index)
            self.update_region_button(picture_region_button, picture_regions, picture_region_color["value"])

        picture_region_button.clicked.connect(choose_picture_regions)
        add_button.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return
        question_text = clean_multiline_text(question_edit.toPlainText())
        if not question_text:
            QMessageBox.information(self, APP_TITLE, "Linking question text is empty.")
            return
        self.set_question_text_for_row(row, question_text)
        self.table.setCurrentCell(row, self.question_column)
        self.table.selectRow(row)
        highlights = self.root_highlights.setdefault(row, [])
        item_payload = {
            "start": 0,
            "end": 0,
            "text": "",
            "color": "#ffd166",
            "style": "style-2",
            "render": "block",
            "info": "",
            "picture_question": {
                "text": question_text,
                "anchor": "picture_regions" if picture_regions else safe_picture_question_anchor(anchor_combo.currentData(), "picture"),
                "placement": safe_picture_question_placement(placement_combo.currentData()),
            },
        }
        if pan_check.isChecked():
            item_payload["camera_focus"] = True
        highlights.append(item_payload)
        if picture_regions:
            highlights[-1]["picture_question"]["regions"] = normalize_picture_question_regions(picture_regions)
            highlights[-1]["picture_question"]["region_color"] = safe_color(picture_region_color["value"], self.default_picture_region_color)
        self.edit_root_highlights()

    def guidance_tree_entry_for_answer(self, row: int, answer_text: str) -> dict:
        tree = normalize_guidance_tree_payload(self.guidance_trees.get(row, {}))
        key = self.answer_key(answer_text)
        for entry in tree.get("items", []):
            if self.answer_key(clean_text(entry.get("text"))) == key:
                return dict(entry)
        return {"text": clean_text(answer_text), "main": "", "children": []}

    def set_guidance_tree_entry_for_answer(self, row: int, answer_text: str, payload: dict) -> None:
        answer_text = clean_text(answer_text)
        if not answer_text:
            return
        tree = normalize_guidance_tree_payload(self.guidance_trees.get(row, {}))
        key = self.answer_key(answer_text)
        items = [dict(entry) for entry in tree.get("items", []) if self.answer_key(clean_text(entry.get("text"))) != key]
        entry = {
            "text": answer_text,
            "main": clean_multiline_text(payload.get("main") if isinstance(payload, dict) else ""),
            "children": payload.get("children") if isinstance(payload, dict) and isinstance(payload.get("children"), list) else [],
        }
        if isinstance(payload, dict):
            mode = normalize_guidance_node_mode(payload.get("type") or payload.get("mode"))
            question = clean_multiline_text(payload.get("question"))
            answer = clean_text(payload.get("answer"))
            if mode in {"choice", "input"} and question and answer:
                entry["type"] = mode
                entry["question"] = question
                entry["answer"] = answer
                if mode == "input":
                    answers = clean_text_list(payload.get("answers"))
                    if answers:
                        entry["answers"] = answers
                else:
                    wrong = clean_text_list(payload.get("wrong"))
                    if wrong:
                        entry["wrong"] = wrong
        clean_entry = normalize_guidance_tree_payload({"items": [entry]}).get("items", [])
        if clean_entry:
            items.append(clean_entry[0])
        if items:
            self.guidance_trees[row] = {"items": items}
        else:
            self.guidance_trees.pop(row, None)

    def edit_guidance_tree_for_answer(self, row: int, answer_text: str) -> None:
        if row < 0 or row >= self.table.rowCount():
            return
        answer_text = clean_text(answer_text)
        if not answer_text:
            QMessageBox.information(self, APP_TITLE, "This answer card is empty.")
            return
        entry = self.guidance_tree_entry_for_answer(row, answer_text)
        dialog = GuidanceTreeDialog(answer_text, entry, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self.set_guidance_tree_entry_for_answer(row, answer_text, dialog.payload())

    def show_question_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        column = self.table.columnAt(pos.x())
        if row >= 0:
            self.table.setCurrentCell(row, column if column >= 0 else self.question_column)
            self.table.selectRow(row)
        menu = QMenu(self)
        answer_text = ""
        if row >= 0 and column >= self.answer_column:
            answer_text = clean_text(self.table.item(row, column).text() if self.table.item(row, column) else "")
        edit_guidance_tree = menu.addAction("Add / edit extra info/question tree")
        edit_guidance_tree.setEnabled(
            row >= 0
            and column >= self.answer_column
            and bool(answer_text)
        )
        edit_guidance_tree.triggered.connect(lambda _checked=False, target=row, text=answer_text: self.edit_guidance_tree_for_answer(target, text))
        menu.addSeparator()
        add_selection = menu.addAction("Add selection from Root text")
        add_selection.setEnabled(row >= 0)
        add_selection.triggered.connect(lambda _checked=False, target=row: self.add_root_selection_to_row(target, False, True))
        add_picture_question = menu.addAction("Add linking question card")
        add_picture_question.setEnabled(row >= 0)
        add_picture_question.triggered.connect(lambda _checked=False, target=row: self.add_picture_question_to_row(target))
        edit_select_targets = menu.addAction("Select question target setup")
        edit_select_targets.setEnabled(row >= 0 and normalize_question_type(self.combo_value(row, self.type_column)) == "select")
        edit_select_targets.triggered.connect(lambda _checked=False, target=row: self.edit_select_question_targets(target))
        edit_highlight = menu.addAction("Root highlight setting")
        edit_highlight.setEnabled(row >= 0)
        edit_highlight.triggered.connect(self.edit_root_highlights)
        question_setting = menu.addAction("Question setting")
        question_setting.setEnabled(row >= 0)
        question_setting.triggered.connect(self.edit_question_settings)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def answer_values_for_row(self, row: int) -> list[str]:
        answer = clean_text(self.table.item(row, self.answer_column).text() if self.table.item(row, self.answer_column) else "")
        values = [answer]
        for column in range(self.wrong_start_column, self.table.columnCount()):
            value = clean_text(self.table.item(row, column).text() if self.table.item(row, column) else "")
            if value:
                values.append(value)
        result = []
        seen = set()
        for value in values:
            key = self.answer_key(value)
            if key and key not in seen:
                seen.add(key)
                result.append(value)
        return result

    def select_tokens_from_root_ranges(self, ranges: list[dict]) -> list[str]:
        tokens: list[str] = []
        for item in ranges if isinstance(ranges, list) else []:
            if isinstance(item, dict):
                tokens.extend(select_token_list(item.get("text")))
        return tokens

    def initial_select_root_ranges(self, payload: dict) -> list[dict]:
        data = normalize_select_targets_payload(payload)
        ranges = data.get("root_ranges") if isinstance(data.get("root_ranges"), list) else []
        if ranges:
            return [dict(item) for item in ranges if isinstance(item, dict)]
        root_text = clean_multiline_text(data.get("root_text"))
        if root_text and self.root_preview_text:
            start = self.root_preview_text.find(root_text)
            if start >= 0:
                return [{"start": start, "end": start + len(root_text), "text": root_text}]
        return []

    def edit_select_root_text_targets(self, ranges: list[dict]) -> list[dict] | None:
        root_text = self.root_preview_text
        if not root_text:
            QMessageBox.information(self, APP_TITLE, "Root text is empty. Add Root text first.")
            return None
        current_ranges = [
            {
                "start": max(0, int(item.get("start") or 0)),
                "end": max(0, int(item.get("end") or 0)),
                "text": clean_multiline_text(item.get("text")),
            }
            for item in (ranges if isinstance(ranges, list) else [])
            if isinstance(item, dict)
        ]
        current_ranges = [item for item in current_ranges if item["end"] > item["start"] and item["text"]]

        dialog = QDialog(self)
        dialog.setWindowTitle("Collect text from Root highlight")
        dialog.resize(1040, 760)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Clone Root text: select words/phrases, then add them as clickable answer targets.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        hint = QLabel("Tip: drag over a word or phrase and press Add selection. Click an already highlighted target to remove it.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        class SelectRootTextEdit(QTextEdit):
            def mousePressEvent(editor_self, event):  # type: ignore[override]
                cursor = editor_self.cursorForPosition(event.pos())
                position = cursor.position()
                for index, item in enumerate(list(current_ranges)):
                    if int(item.get("start") or 0) <= position < int(item.get("end") or 0):
                        current_ranges.pop(index)
                        refresh_view()
                        event.accept()
                        return
                super().mousePressEvent(event)

        editor = SelectRootTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(root_text)
        editor.setMinimumHeight(420)
        editor.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(editor, 1)

        picked_list = QListWidget()
        picked_list.setMinimumHeight(120)
        layout.addWidget(picked_list)

        button_row = QHBoxLayout()
        add_selection = QPushButton("Add selection")
        clear_all = QPushButton("Clear text targets")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        button_row.addWidget(add_selection)
        button_row.addWidget(clear_all)
        button_row.addStretch(1)
        button_row.addWidget(done)
        button_row.addWidget(cancel)
        layout.addLayout(button_row)

        def clean_ranges() -> None:
            valid = []
            for item in current_ranges:
                try:
                    start = int(item.get("start") or 0)
                    end = int(item.get("end") or 0)
                except Exception:
                    continue
                start = max(0, min(len(root_text), start))
                end = max(0, min(len(root_text), end))
                if end <= start:
                    continue
                text = root_text[start:end]
                if clean_text(text):
                    valid.append({"start": start, "end": end, "text": text})
            valid.sort(key=lambda item: (item["start"], item["end"]))
            current_ranges[:] = valid

        def refresh_view() -> None:
            clean_ranges()
            selections = []
            for item in current_ranges:
                cursor = editor.textCursor()
                cursor.setPosition(int(item["start"]))
                cursor.setPosition(int(item["end"]), QTextCursor.KeepAnchor)
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                fmt = QTextCharFormat()
                fmt.setBackground(QBrush(QColor(70, 240, 215, 76)))
                fmt.setForeground(QBrush(QColor(236, 255, 249)))
                fmt.setFontWeight(QFont.Bold)
                selection.format = fmt
                selections.append(selection)
            editor.setExtraSelections(selections)
            picked_list.clear()
            for index, item in enumerate(current_ranges, 1):
                picked_list.addItem(f"{index}. {clean_text(item.get('text'))}")

        def add_current_selection() -> None:
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                QMessageBox.information(dialog, APP_TITLE, "Select words in the cloned Root text first.")
                return
            start = min(cursor.selectionStart(), cursor.selectionEnd())
            end = max(cursor.selectionStart(), cursor.selectionEnd())
            while start < end and root_text[start].isspace():
                start += 1
            while end > start and root_text[end - 1].isspace():
                end -= 1
            if end <= start:
                return
            current_ranges[:] = [
                item for item in current_ranges
                if int(item.get("end") or 0) <= start or int(item.get("start") or 0) >= end
            ]
            current_ranges.append({"start": start, "end": end, "text": root_text[start:end]})
            refresh_view()

        def remove_list_item(item: QListWidgetItem) -> None:
            row = picked_list.row(item)
            if 0 <= row < len(current_ranges):
                current_ranges.pop(row)
                refresh_view()

        add_selection.clicked.connect(add_current_selection)
        clear_all.clicked.connect(lambda: (current_ranges.clear(), refresh_view()))
        picked_list.itemClicked.connect(remove_list_item)
        done.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        refresh_view()
        if dialog.exec_() != QDialog.Accepted:
            return None
        clean_ranges()
        return [dict(item) for item in current_ranges]

    def edit_select_question_targets_legacy(self, row: int | None = None) -> None:
        row = self.table.currentRow() if row is None else row
        if row < 0 or row >= self.table.rowCount():
            return
        qtype = normalize_question_type(self.combo_value(row, self.type_column))
        if qtype != "select":
            QMessageBox.information(self, APP_TITLE, "Set this row type to Select tokens first.")
            return
        existing = normalize_select_targets_payload(self.select_targets.get(row, {}))
        answer_raw = clean_multiline_text(self.table.item(row, self.answer_column).text() if self.table.item(row, self.answer_column) else "")
        tokens = select_token_list(answer_raw)
        dialog = QDialog(self)
        dialog.setWindowTitle("Select question target setup")
        dialog.resize(980, 760)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Choose where learners click for this Select question: Root text words and/or picture regions.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        layout.addLayout(grid)
        root_target = QPlainTextEdit()
        root_target.setPlainText(clean_multiline_text(existing.get("root_text")))
        root_target.setPlaceholderText("Paste the Root text segment that contains selectable answer words.")
        root_target.setMinimumHeight(118)
        grid.addWidget(QLabel("Root selectable segment"), 0, 0)
        grid.addWidget(root_target, 0, 1)
        token_edit = QPlainTextEdit()
        token_edit.setPlainText("\n".join(tokens))
        token_edit.setPlaceholderText("One correct token per line. Example:\nswitched\nto")
        token_edit.setMinimumHeight(120)
        grid.addWidget(QLabel("Correct word tokens"), 1, 0)
        grid.addWidget(token_edit, 1, 1)
        word_picker = QListWidget()
        word_picker.setSelectionMode(QAbstractItemView.MultiSelection)
        word_picker.setMinimumHeight(132)
        grid.addWidget(QLabel("Click/select answer words"), 2, 0)
        grid.addWidget(word_picker, 2, 1)
        regions = normalize_picture_question_regions(existing.get("regions") or [])
        region_color = {"value": safe_color(existing.get("region_color"), self.default_picture_region_color)}
        region_button = QPushButton()
        self.update_region_button(region_button, regions, region_color["value"])
        grid.addWidget(QLabel("Correct picture regions"), 3, 0)
        grid.addWidget(region_button, 3, 1)
        helper_row = QHBoxLayout()
        use_selection = QPushButton("Use current Root selection")
        tokens_from_root = QPushButton("Tokens from Root segment")
        use_picked_words = QPushButton("Use selected words")
        refresh_picker = QPushButton("Refresh word picker")
        helper_row.addWidget(use_selection)
        helper_row.addWidget(tokens_from_root)
        helper_row.addWidget(use_picked_words)
        helper_row.addWidget(refresh_picker)
        helper_row.addStretch(1)
        layout.addLayout(helper_row)
        hint = QLabel("Runtime will highlight selected Root words / picture regions and connect them to the Selection card.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        clear = QPushButton("Clear setup")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        dialog.clear_setup = False

        def rebuild_word_picker() -> None:
            selected_counts: dict[str, int] = {}
            for value in select_token_list(token_edit.toPlainText()):
                key = clean_text(value).casefold()
                selected_counts[key] = selected_counts.get(key, 0) + 1
            word_picker.clear()
            used_counts: dict[str, int] = {}
            for value in select_token_list(root_target.toPlainText()):
                item = QListWidgetItem(value)
                word_picker.addItem(item)
                key = clean_text(value).casefold()
                used_counts[key] = used_counts.get(key, 0) + 1
                if used_counts[key] <= selected_counts.get(key, 0):
                    item.setSelected(True)

        def use_current_selection() -> None:
            parent = self.parent()
            payload = parent.root_selection_payload() if parent is not None and hasattr(parent, "root_selection_payload") else {}
            text = clean_multiline_text(payload.get("text") if isinstance(payload, dict) else "")
            if text:
                root_target.setPlainText(text)
                if not clean_multiline_text(token_edit.toPlainText()):
                    token_edit.setPlainText("\n".join(select_token_list(text)))
                rebuild_word_picker()
            else:
                QMessageBox.information(self, APP_TITLE, "Bôi đen đoạn Root text ở cửa sổ builder chính trước, rồi bấm lại nút này.")

        def fill_tokens_from_root() -> None:
            token_edit.setPlainText("\n".join(select_token_list(root_target.toPlainText())))
            rebuild_word_picker()

        def fill_tokens_from_picker() -> None:
            picked = [clean_text(item.text()) for item in word_picker.selectedItems() if clean_text(item.text())]
            if picked:
                token_edit.setPlainText("\n".join(picked))

        def choose_regions() -> None:
            selected = self.edit_picture_question_region_settings(regions, region_color["value"])
            if selected is None:
                return
            selected_regions, selected_color = selected
            regions[:] = normalize_picture_question_regions(selected_regions)
            region_color["value"] = safe_color(selected_color, self.default_picture_region_color)
            self.update_region_button(region_button, regions, region_color["value"])

        def clear_setup() -> None:
            dialog.clear_setup = True
            dialog.accept()

        use_selection.clicked.connect(use_current_selection)
        tokens_from_root.clicked.connect(fill_tokens_from_root)
        use_picked_words.clicked.connect(fill_tokens_from_picker)
        refresh_picker.clicked.connect(rebuild_word_picker)
        root_target.textChanged.connect(rebuild_word_picker)
        region_button.clicked.connect(choose_regions)
        clear.clicked.connect(clear_setup)
        done.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        rebuild_word_picker()
        if dialog.exec_() != QDialog.Accepted:
            return
        if getattr(dialog, "clear_setup", False):
            self.select_targets.pop(row, None)
            return
        next_tokens = select_token_list(token_edit.toPlainText())
        if next_tokens:
            self.table.setItem(row, self.answer_column, QTableWidgetItem("\n".join(next_tokens)))
        payload = {
            "root_text": clean_multiline_text(root_target.toPlainText()),
            "regions": normalize_picture_question_regions(regions),
            "region_color": safe_color(region_color["value"], self.default_picture_region_color),
        }
        payload = normalize_select_targets_payload(payload)
        if payload:
            self.select_targets[row] = payload
        else:
            self.select_targets.pop(row, None)

    def edit_select_question_targets(self, row: int | None = None) -> None:
        row = self.table.currentRow() if row is None else row
        if row < 0 or row >= self.table.rowCount():
            return
        qtype = normalize_question_type(self.combo_value(row, self.type_column))
        if qtype != "select":
            QMessageBox.information(self, APP_TITLE, "Set this row type to Select tokens first.")
            return
        existing = normalize_select_targets_payload(self.select_targets.get(row, {}))
        root_ranges = self.initial_select_root_ranges(existing)
        regions = normalize_picture_question_regions(existing.get("regions") or [])
        region_color = {"value": safe_color(existing.get("region_color"), self.default_picture_region_color)}

        dialog = QDialog(self)
        dialog.setWindowTitle("Select question target setup")
        dialog.resize(860, 520)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Choose where learners click for this Select question: Root text words and/or picture regions.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        layout.addLayout(grid)

        root_summary = QListWidget()
        root_summary.setMinimumHeight(150)
        collect_root = QPushButton("Collect text from Root highlight")
        root_box = QVBoxLayout()
        root_box.addWidget(collect_root)
        root_box.addWidget(root_summary)
        grid.addWidget(QLabel("Root text targets"), 0, 0)
        grid.addLayout(root_box, 0, 1)

        region_button = QPushButton()
        self.update_region_button(region_button, regions, region_color["value"])
        grid.addWidget(QLabel("Correct picture regions"), 1, 0)
        grid.addWidget(region_button, 1, 1)

        hint = QLabel("Runtime will highlight collected Root text targets / picture regions and connect them to the Selection card.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        clear = QPushButton("Clear setup")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        dialog.clear_setup = False

        def refresh_root_summary() -> None:
            root_summary.clear()
            for index, item in enumerate(root_ranges, 1):
                text = clean_text(item.get("text") if isinstance(item, dict) else "")
                if text:
                    root_summary.addItem(f"{index}. {text}")
            if not root_summary.count():
                root_summary.addItem("No Root text targets collected yet.")

        def collect_root_targets() -> None:
            selected = self.edit_select_root_text_targets(root_ranges)
            if selected is None:
                return
            root_ranges[:] = selected
            refresh_root_summary()

        def choose_regions() -> None:
            selected = self.edit_picture_question_region_settings(regions, region_color["value"])
            if selected is None:
                return
            selected_regions, selected_color = selected
            regions[:] = normalize_picture_question_regions(selected_regions)
            region_color["value"] = safe_color(selected_color, self.default_picture_region_color)
            self.update_region_button(region_button, regions, region_color["value"])

        def clear_setup() -> None:
            dialog.clear_setup = True
            dialog.accept()

        collect_root.clicked.connect(collect_root_targets)
        region_button.clicked.connect(choose_regions)
        clear.clicked.connect(clear_setup)
        done.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        refresh_root_summary()
        if dialog.exec_() != QDialog.Accepted:
            return
        if getattr(dialog, "clear_setup", False):
            self.select_targets.pop(row, None)
            self.table.setItem(row, self.answer_column, QTableWidgetItem(""))
            return

        next_tokens = self.select_tokens_from_root_ranges(root_ranges)
        self.table.setItem(row, self.answer_column, QTableWidgetItem("\n".join(next_tokens) if next_tokens else ""))
        payload = {
            "root_ranges": root_ranges,
            "regions": normalize_picture_question_regions(regions),
            "region_color": safe_color(region_color["value"], self.default_picture_region_color),
        }
        if len(root_ranges) == 1:
            payload["root_text"] = clean_multiline_text(root_ranges[0].get("text"))
        payload = normalize_select_targets_payload(payload)
        if payload:
            self.select_targets[row] = payload
        else:
            self.select_targets.pop(row, None)

    def add_question_row(self, item: dict) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        qtype = normalize_question_type(item.get("type") or item.get("mode") or "choice")
        raw_card_mode = item.get("card_mode") or item.get("cardMode") or item.get("question_card_mode") or item.get("questionCardMode") or item.get("display_mode") or item.get("displayMode") or item.get("cm")
        raw_highlights_for_mode = item.get("root_highlights") if isinstance(item.get("root_highlights"), list) else item.get("rootHighlights")
        fallback_card_mode = "linking" if any(
            isinstance(highlight, dict) and normalize_picture_question_payload(highlight, clean_text(item.get("question") or item.get("q")))
            for highlight in (raw_highlights_for_mode if isinstance(raw_highlights_for_mode, list) else [])
        ) else "question"
        card_mode = normalize_question_card_mode(raw_card_mode, fallback_card_mode)
        raw_answer_value = clean_multiline_text(item.get("answer") or item.get("a"))
        answer_value = clean_text(raw_answer_value)
        select_tokens = select_token_list(
            item.get("tokens") or item.get("select_tokens") or item.get("selectTokens") or item.get("tk"),
            raw_answer_value,
        ) if qtype == "select" else []
        if qtype == "select" and select_tokens:
            answer_value = "\n".join(select_tokens)
        answers = item.get("answers") if isinstance(item.get("answers"), list) else item.get("accept")
        if not isinstance(answers, list):
            answers = item.get("accepts") if isinstance(item.get("accepts"), list) else []
        accepted_values = [
            clean_text(value.get("text") if isinstance(value, dict) else value)
            for value in answers
            if clean_text(value.get("text") if isinstance(value, dict) else value)
        ]
        if qtype == "input" and not answer_value and accepted_values:
            answer_value = accepted_values[0]
        wrong = item.get("wrong") if isinstance(item.get("wrong"), list) else item.get("wrongs")
        if not isinstance(wrong, list):
            wrong = []
        wrong_values = [
            clean_text(value.get("text") if isinstance(value, dict) else value)
            for value in wrong
            if clean_text(value.get("text") if isinstance(value, dict) else value)
        ]
        if qtype == "input" and accepted_values:
            seen_answers = {self.answer_key(answer_value)}
            wrong_values = []
            for value in accepted_values:
                key = self.answer_key(value)
                if key and key not in seen_answers:
                    seen_answers.add(key)
                    wrong_values.append(value)
        if qtype == "select":
            wrong_values = []
        self.ensure_wrong_columns(len(wrong_values))
        order_value = clean_text(item.get("order") or item.get("o") or item.get("sort") or item.get("stt"))
        values = [
            order_value,
            qtype,
            card_mode,
            clean_text(item.get("question") or item.get("q")),
            answer_value,
        ]
        for column, value in enumerate(values):
            if column == self.type_column:
                self.table.setCellWidget(row, column, self.make_question_type_combo(qtype))
                continue
            if column == self.card_mode_column:
                self.table.setCellWidget(row, column, self.make_question_card_mode_combo(card_mode))
                continue
            table_item = QTableWidgetItem(value)
            if column in {self.order_column, self.type_column, self.card_mode_column}:
                table_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, table_item)
        for index, value in enumerate(wrong_values):
            self.table.setItem(row, self.wrong_start_column + index, QTableWidgetItem(value))
        audio = item.get("audio") if isinstance(item.get("audio"), dict) else {}
        answer_audio = item.get("answer_audio") if isinstance(item.get("answer_audio"), dict) else {}
        answer_info = item.get("answer_info") if isinstance(item.get("answer_info"), dict) else {}
        root_notice = normalize_root_notice_payload(item.get("root_notice") or item.get("rootNotice") or item.get("rn"))
        if root_notice:
            self.root_notices[row] = root_notice
        guidance_tree = normalize_guidance_tree_payload(item.get("guidance_tree") or item.get("guidanceTree") or item.get("guide_tree") or item.get("gt"))
        if guidance_tree:
            self.guidance_trees[row] = guidance_tree
        select_targets = normalize_select_targets_payload(item.get("select_targets") or item.get("selectTargets") or item.get("selection_targets") or item.get("selectionTargets") or item.get("stg"))
        if select_targets:
            self.select_targets[row] = select_targets
        highlights = item.get("root_highlights") if isinstance(item.get("root_highlights"), list) else item.get("rootHighlights")
        if isinstance(highlights, list):
            clean_highlights = []
            for highlight in highlights:
                if not isinstance(highlight, dict):
                    continue
                try:
                    start = int(highlight.get("start") or highlight.get("s") or 0)
                    end = int(highlight.get("end") or highlight.get("e") or 0)
                except Exception:
                    start, end = 0, 0
                highlight_text = clean_multiline_text(highlight.get("text") or highlight.get("t"))
                picture_question = normalize_picture_question_payload(highlight, clean_text(item.get("question") or item.get("q")))
                if end > start or highlight_text or picture_question:
                    item_payload = {
                        "start": max(0, start),
                        "end": max(0, end),
                        "text": highlight_text,
                        "color": safe_color(highlight.get("color") or highlight.get("c")),
                        "style": clean_text(highlight.get("style") or highlight.get("st")) or "style-1",
                        "render": safe_highlight_render(highlight.get("render") or highlight.get("mode") or highlight.get("m")),
                        "info": clean_multiline_text(highlight.get("info") or highlight.get("note") or highlight.get("card") or highlight.get("i")),
                    }
                    if highlight_camera_focus_enabled(highlight):
                        item_payload["camera_focus"] = True
                    if picture_question:
                        item_payload["picture_question"] = picture_question
                    clean_highlights.append(item_payload)
            if clean_highlights:
                self.root_highlights[row] = clean_highlights
        settings = {
            "question": {
                "mode": clean_text(item.get("audio_mode") or audio.get("mode") or "off").lower(),
                "voice": clean_text(item.get("audio_voice") or audio.get("voice") or audio.get("v")),
                "audio_text": clean_text(audio.get("audio_text") or audio.get("text") or audio.get("t")),
            },
            "answers": {},
        }
        answer_items = answer_audio.get("items") if isinstance(answer_audio.get("items"), list) else []
        for entry in answer_items:
            if not isinstance(entry, dict):
                continue
            text = clean_text(entry.get("text") or entry.get("t") or entry.get("answer") or entry.get("a"))
            key = self.answer_key(text)
            if key:
                settings["answers"].setdefault(key, {"text": text})
                settings["answers"][key].update({
                    "text": text,
                    "voice": clean_text(entry.get("voice") or entry.get("v") or answer_audio.get("voice")),
                    "mode": clean_text(entry.get("mode") or answer_audio.get("mode") or "off").lower(),
                    "audio_text": clean_text(entry.get("audio_text") or entry.get("text") or entry.get("t")),
                })
        info_items = answer_info.get("items") if isinstance(answer_info.get("items"), list) else []
        for entry in info_items:
            if not isinstance(entry, dict):
                continue
            text = clean_text(entry.get("text") or entry.get("t") or entry.get("answer") or entry.get("a"))
            key = self.answer_key(text)
            if key:
                settings["answers"].setdefault(key, {"text": text})
                settings["answers"][key].update({
                    "text": text,
                    "info_text": clean_text(entry.get("info_text") or entry.get("info") or entry.get("explain") or entry.get("explanation")),
                    "info_mode": normalize_info_mode(entry.get("mode") or entry.get("info_mode") or "audio", "audio"),
                    "info_voice": clean_text(entry.get("voice") or entry.get("v") or answer_info.get("voice")),
                })
        if settings["question"]["mode"] != "off" or settings["question"]["audio_text"] or settings["answers"]:
            self.question_settings[row] = settings

    def remove_selected_rows(self) -> None:
        rows = sorted({item.row() for item in self.table.selectedItems()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            removed = set(rows)
            next_settings = {}
            shift = 0
            for old_row in range(self.table.rowCount() + len(rows)):
                if old_row in removed:
                    shift += 1
                    continue
                if old_row in self.question_settings:
                    next_settings[old_row - shift] = self.question_settings[old_row]
            self.question_settings = next_settings
            next_highlights = {}
            shift = 0
            for old_row in range(self.table.rowCount() + len(rows)):
                if old_row in removed:
                    shift += 1
                    continue
                if old_row in self.root_highlights:
                    next_highlights[old_row - shift] = self.root_highlights[old_row]
            self.root_highlights = next_highlights
            next_notices = {}
            shift = 0
            for old_row in range(self.table.rowCount() + len(rows)):
                if old_row in removed:
                    shift += 1
                    continue
                if old_row in self.root_notices:
                    next_notices[old_row - shift] = self.root_notices[old_row]
            self.root_notices = next_notices
            next_guidance = {}
            shift = 0
            for old_row in range(self.table.rowCount() + len(rows)):
                if old_row in removed:
                    shift += 1
                    continue
                if old_row in self.guidance_trees:
                    next_guidance[old_row - shift] = self.guidance_trees[old_row]
            self.guidance_trees = next_guidance
            next_select_targets = {}
            shift = 0
            for old_row in range(self.table.rowCount() + len(rows)):
                if old_row in removed:
                    shift += 1
                    continue
                if old_row in self.select_targets:
                    next_select_targets[old_row - shift] = self.select_targets[old_row]
            self.select_targets = next_select_targets

    def import_txt(self) -> None:
        start = clean_text(self.settings.get("last_question_folder")) or str(Path.cwd())
        path, _filter = QFileDialog.getOpenFileName(self, "Chọn TXT câu hỏi", start, "Text files (*.txt *.csv);;All files (*.*)")
        if not path:
            return
        self.settings["last_question_folder"] = str(Path(path).parent)
        added = 0
        try:
            for raw_line in Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines():
                columns = split_question_line(raw_line)
                if len(columns) < 2:
                    continue
                self.add_question_row({
                    "type": "choice" if len(columns) > 2 else "input",
                    "question": columns[0],
                    "answer": columns[1],
                    "wrong": columns[2:],
                })
                added += 1
        except Exception as exc:
            QMessageBox.warning(self, APP_TITLE, f"Không load được TXT: {exc}")
            return
        QMessageBox.information(self, APP_TITLE, f"Đã thêm {added} câu hỏi.")

    def edit_question_settings(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_TITLE, "Hãy chọn một câu hỏi trước.")
            return
        answers = self.answer_values_for_row(row)
        if not answers:
            QMessageBox.information(self, APP_TITLE, "Câu hỏi chưa có đáp án.")
            return
        question_text = clean_text(self.table.item(row, self.question_column).text() if self.table.item(row, self.question_column) else "")
        qtype = normalize_question_type(self.combo_value(row, self.type_column))
        typed_question = qtype == "input"
        settings = self.question_settings.get(row) or {}
        question_setting = settings.get("question") if isinstance(settings.get("question"), dict) else {}
        answer_settings = settings.get("answers") if isinstance(settings.get("answers"), dict) else {}
        default_voice = self.voices[0][1] if self.voices else "sot:en-US"
        default_info_voice = self.default_info_voice()
        dialog = QDialog(self)
        dialog.setWindowTitle("Question setting")
        dialog.resize(1480, 820)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        label = QLabel("Question-level audio and explanation cards for the selected question.")
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        row_defs = [{"kind": "question", "label": "Question prompt", "value": question_text}]
        row_defs.extend({"kind": "answer", "label": answer, "value": answer} for answer in answers)
        if typed_question:
            row_defs.append({"kind": "typed_info", "label": "Typed answer correct", "value": "__typed_correct__"})
            row_defs.append({"kind": "typed_info", "label": "Typed answer wrong", "value": "__typed_wrong__"})
        table = QTableWidget(len(row_defs), 7)
        table.setHorizontalHeaderLabels(["Target", "Audio text override", "Audio voice", "Audio mode", "Info / explanation text", "Info mode", "Info voice"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for column in range(1, 7):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Interactive)
        table.setColumnWidth(1, 360)
        table.setColumnWidth(2, 210)
        table.setColumnWidth(3, 130)
        table.setColumnWidth(4, 430)
        table.setColumnWidth(5, 130)
        table.setColumnWidth(6, 210)
        table.setMinimumSize(1320, 560)
        table.setWordWrap(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(92)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        def set_label_cell(row_index: int, value: str) -> None:
            item = QTableWidgetItem(clean_text(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_index, 0, item)

        def make_text_editor(value: str, placeholder: str = "") -> QPlainTextEdit:
            editor = QPlainTextEdit()
            editor.setPlainText(clean_text(value))
            editor.setPlaceholderText(placeholder)
            editor.setMinimumSize(300, 74)
            editor.setMaximumHeight(130)
            return editor

        def editor_text(row_index: int, column: int) -> str:
            widget = table.cellWidget(row_index, column)
            if isinstance(widget, QPlainTextEdit):
                return clean_text(widget.toPlainText())
            item = table.item(row_index, column)
            return clean_text(item.text() if item else "")

        for index, definition in enumerate(row_defs):
            kind = definition["kind"]
            value = definition["value"]
            label_text = definition["label"]
            set_label_cell(index, label_text)
            if kind == "question":
                current = question_setting
                table.setCellWidget(index, 1, make_text_editor(clean_text(current.get("audio_text")) or question_text, "Question audio text"))
                table.setCellWidget(index, 2, self.make_voice_combo(clean_text(current.get("voice")) or default_voice))
                table.setCellWidget(index, 3, self.make_mode_combo(clean_text(current.get("mode")) or "off"))
                table.setCellWidget(index, 4, make_text_editor("", "Question prompt does not use explanation card"))
                table.cellWidget(index, 4).setEnabled(False)
                table.setCellWidget(index, 5, self.make_info_mode_combo("audio"))
                table.cellWidget(index, 5).setEnabled(False)
                table.setCellWidget(index, 6, self.make_info_voice_combo(default_info_voice))
                table.cellWidget(index, 6).setEnabled(False)
                continue
            current = answer_settings.get(self.answer_key(value), {}) if isinstance(answer_settings, dict) else {}
            if kind == "typed_info":
                table.setCellWidget(index, 1, make_text_editor("", "No answer audio for this feedback row"))
                table.cellWidget(index, 1).setEnabled(False)
                table.setCellWidget(index, 2, self.make_voice_combo(default_voice))
                table.cellWidget(index, 2).setEnabled(False)
                table.setCellWidget(index, 3, self.make_mode_combo("off"))
                table.cellWidget(index, 3).setEnabled(False)
                default_text = "Correct. The typed answer matches." if value == "__typed_correct__" else "Not yet. Review the signal and try again."
                table.setCellWidget(index, 4, make_text_editor(clean_text(current.get("info_text")) or default_text, "Feedback text"))
                table.setCellWidget(index, 5, self.make_info_mode_combo(clean_text(current.get("info_mode")) or "audio"))
                table.setCellWidget(index, 6, self.make_info_voice_combo(clean_text(current.get("info_voice")) or default_info_voice))
                continue
            table.setCellWidget(index, 1, make_text_editor(clean_text(current.get("audio_text")) or value, "Audio text override"))
            table.setCellWidget(index, 2, self.make_voice_combo(clean_text(current.get("voice")) or default_voice))
            table.setCellWidget(index, 3, self.make_mode_combo(clean_text(current.get("mode")) or "off"))
            table.setCellWidget(index, 4, make_text_editor(clean_text(current.get("info_text")), "Explanation card text"))
            table.setCellWidget(index, 5, self.make_info_mode_combo(clean_text(current.get("info_mode")) or "audio"))
            table.setCellWidget(index, 6, self.make_info_voice_combo(clean_text(current.get("info_voice")) or default_info_voice))
        layout.addWidget(table, 1)
        buttons = QHBoxLayout()
        clear = QPushButton("Clear setting")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        dialog.clear_all = False

        def clear_all() -> None:
            dialog.clear_all = True
            self.question_settings.pop(row, None)
            dialog.accept()

        clear.clicked.connect(clear_all)
        done.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return
        if getattr(dialog, "clear_all", False):
            return
        next_settings = {"question": {}, "answers": {}}
        q_voice_widget = table.cellWidget(0, 2)
        q_mode_widget = table.cellWidget(0, 3)
        q_audio_text = editor_text(0, 1)
        q_voice = clean_text(q_voice_widget.currentData() if isinstance(q_voice_widget, QComboBox) else default_voice) or default_voice
        q_mode = clean_text(q_mode_widget.currentData() if isinstance(q_mode_widget, QComboBox) else "off").lower() or "off"
        if q_mode != "off" or (q_audio_text and q_audio_text != question_text):
            next_settings["question"] = {"audio_text": q_audio_text, "voice": q_voice, "mode": q_mode}
        for index, definition in enumerate(row_defs[1:], 1):
            answer = definition["value"]
            kind = definition["kind"]
            voice_widget = table.cellWidget(index, 2)
            mode_widget = table.cellWidget(index, 3)
            info_mode_widget = table.cellWidget(index, 5)
            info_voice_widget = table.cellWidget(index, 6)
            audio_text = editor_text(index, 1) or answer
            voice = clean_text(voice_widget.currentData() if isinstance(voice_widget, QComboBox) else default_voice) or default_voice
            mode = clean_text(mode_widget.currentData() if isinstance(mode_widget, QComboBox) else "off").lower() or "off"
            info_text = editor_text(index, 4)
            info_mode = normalize_info_mode(info_mode_widget.currentData() if isinstance(info_mode_widget, QComboBox) else "audio", "audio")
            info_voice = clean_text(info_voice_widget.currentData() if isinstance(info_voice_widget, QComboBox) else default_info_voice) or default_info_voice
            if kind == "typed_info":
                if info_text:
                    next_settings["answers"][self.answer_key(answer)] = {"text": answer, "info_text": info_text, "info_mode": info_mode, "info_voice": info_voice}
                continue
            if mode != "off" or audio_text != answer or info_text:
                payload = {"text": answer, "audio_text": audio_text, "voice": voice, "mode": mode}
                if info_text:
                    payload.update({"info_text": info_text, "info_mode": info_mode, "info_voice": info_voice})
                next_settings["answers"][self.answer_key(answer)] = payload
        if next_settings["question"] or next_settings["answers"]:
            self.question_settings[row] = next_settings
        else:
            self.question_settings.pop(row, None)

    def edit_root_highlights(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_TITLE, "Hãy chọn một câu hỏi trước.")
            return
        highlights = [dict(item) for item in self.root_highlights.get(row, []) if isinstance(item, dict)]
        root_preview_text = self.root_preview_text or "Root card preview"
        row_question_text = self.question_text_for_row(row)
        synced_picture_question_text = {"value": row_question_text}
        dialog = QDialog(self)
        dialog.setWindowTitle("Root highlight setting")
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        dialog.setMinimumSize(1280, 720)
        dialog.resize(1680, 940)
        dialog.setWindowState(dialog.windowState() | Qt.WindowMaximized)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        label = QLabel("Các đoạn Root text sẽ được quét sáng khi câu hỏi này xuất hiện.")
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        route_note = QLabel(
            "Routing: choose Linking question card in the question row to ask through this linked card. It connects to highlighted Root text; if no highlight exists, it connects to the Question Root."
        )
        route_note.setWordWrap(True)
        route_note.setStyleSheet("color: rgba(236,255,249,.72); font-weight: 700;")
        layout.addWidget(route_note)
        notice_state = {"payload": normalize_root_notice_payload(self.root_notices.get(row, {}))}
        notice_layout = QGridLayout()
        layout.addLayout(notice_layout)
        notice_layout.addWidget(QLabel("Hologram notice dialogue"), 0, 0)
        notice_summary = QLabel(root_notice_summary(notice_state["payload"]))
        notice_summary.setWordWrap(True)
        notice_summary.setStyleSheet("color: rgba(236,255,249,.78); font-weight: 700;")
        edit_notice = QPushButton("Edit notice dialogue")
        clear_notice = QPushButton("Clear notice")
        notice_layout.addWidget(notice_summary, 0, 1)
        notice_layout.addWidget(edit_notice, 0, 2)
        notice_layout.addWidget(clear_notice, 0, 3)

        def refresh_notice_summary() -> None:
            notice_summary.setText(root_notice_summary(notice_state["payload"]))

        def open_notice_dialog() -> None:
            dialog_notice = RootNoticeDialog(notice_state["payload"], self.voices, self)
            if dialog_notice.exec_() == QDialog.Accepted:
                notice_state["payload"] = dialog_notice.payload()
                refresh_notice_summary()

        def clear_notice_dialog() -> None:
            notice_state["payload"] = {}
            refresh_notice_summary()

        edit_notice.clicked.connect(open_notice_dialog)
        clear_notice.clicked.connect(clear_notice_dialog)
        table = QTableWidget(len(highlights), 11)
        table.setHorizontalHeaderLabels(["Selected text", "Style", "Render", "Color", "Info card text", "Linking question", "Anchor", "Placement", "Picture regions", "Pan view", "Range"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        table.setColumnWidth(0, 380)
        table.setColumnWidth(1, 640)
        table.setColumnWidth(2, 190)
        table.setColumnWidth(4, 430)
        table.setColumnWidth(5, 520)
        table.setColumnWidth(9, 120)
        table.setColumnWidth(10, 130)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setDefaultSectionSize(84)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        preview_title = QLabel("Root card HTML preview")
        preview_title.setObjectName("sectionTitle")
        preview = QTextBrowser()
        preview.setOpenExternalLinks(False)
        preview.setMinimumHeight(210)
        preview.setStyleSheet("""
            QTextBrowser {
                background: #071719;
                border: 1px solid rgba(70, 240, 215, 0.32);
                border-radius: 14px;
                padding: 10px;
                color: #ecfff9;
            }
        """)

        def make_info_editor(value: str) -> QPlainTextEdit:
            editor = QPlainTextEdit()
            editor.setPlainText(clean_multiline_text(value))
            editor.setPlaceholderText("Info card text shown when learner points to this highlight")
            editor.setMinimumHeight(62)
            return editor

        def make_picture_question_editor(value: str) -> QPlainTextEdit:
            editor = QPlainTextEdit()
            editor.setPlainText(clean_multiline_text(value))
            editor.setPlaceholderText("Optional Linking question anchored to this highlight or to the picture ship/card.")
            editor.setMinimumHeight(72)
            return editor

        def remember_picture_question_text(editor: QPlainTextEdit) -> None:
            text = clean_multiline_text(editor.toPlainText())
            if text:
                synced_picture_question_text["value"] = text
                self.set_question_text_for_row(row, text)
            render_preview()

        def fill_table() -> None:
            table.setRowCount(len(highlights))
            for index, highlight in enumerate(highlights):
                text_item = QTableWidgetItem(clean_multiline_text(highlight.get("text"))[:420])
                color = safe_color(highlight.get("color"))
                color_item = QTableWidgetItem(color)
                range_item = QTableWidgetItem(f'{int(highlight.get("start") or 0)} - {int(highlight.get("end") or 0)}')
                color_item.setFlags(color_item.flags() & ~Qt.ItemIsEditable)
                range_item.setFlags(range_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(index, 0, text_item)
                style_combo = self.make_highlight_style_combo(clean_text(highlight.get("style")) or "style-1")
                render_combo = self.make_highlight_render_combo(clean_text(highlight.get("render") or highlight.get("mode")) or "text")
                picture_question = normalize_picture_question_payload(highlight, self.question_text_for_row(row))
                info_editor = make_info_editor(clean_multiline_text(highlight.get("info")))
                picture_question_editor = make_picture_question_editor(clean_multiline_text(picture_question.get("text")))
                anchor_combo = self.make_picture_question_anchor_combo(clean_text(picture_question.get("anchor")) or "highlight")
                placement_combo = self.make_picture_question_placement_combo(clean_text(picture_question.get("placement")) or "auto")
                style_combo.currentIndexChanged.connect(lambda _value=0: render_preview())
                render_combo.currentIndexChanged.connect(lambda _value=0: render_preview())
                info_editor.textChanged.connect(render_preview)
                picture_question_editor.textChanged.connect(lambda editor=picture_question_editor: remember_picture_question_text(editor))
                table.setCellWidget(index, 1, style_combo)
                table.setCellWidget(index, 2, render_combo)
                table.setItem(index, 3, color_item)
                table.setCellWidget(index, 4, info_editor)
                table.setCellWidget(index, 5, picture_question_editor)
                table.setCellWidget(index, 6, anchor_combo)
                table.setCellWidget(index, 7, placement_combo)
                region_button = QPushButton()
                self.update_region_button(
                    region_button,
                    picture_question.get("regions") if isinstance(picture_question, dict) else [],
                    picture_question.get("region_color") if isinstance(picture_question, dict) else None,
                )
                region_button.clicked.connect(lambda _checked=False, target=index: edit_regions_for_row(target))
                table.setCellWidget(index, 8, region_button)
                pan_widget = QCheckBox("Pan")
                pan_widget.setToolTip("Tick để kéo màn hình sang highlight/vùng ảnh trước, chạy hiệu ứng xong chờ 2 giây rồi quay lại card hỏi.")
                pan_widget.setChecked(highlight_camera_focus_enabled(highlight))
                pan_widget.stateChanged.connect(lambda _state=0: render_preview())
                table.setCellWidget(index, 9, pan_widget)
                table.setItem(index, 10, range_item)

        def sync_from_table() -> None:
            row_question_text = clean_multiline_text(synced_picture_question_text.get("value")) or self.question_text_for_row(row)
            if row_question_text:
                self.set_question_text_for_row(row, row_question_text)
            for index, highlight in enumerate(highlights):
                style_widget = table.cellWidget(index, 1)
                render_widget = table.cellWidget(index, 2)
                info_widget = table.cellWidget(index, 4)
                question_widget = table.cellWidget(index, 5)
                anchor_widget = table.cellWidget(index, 6)
                placement_widget = table.cellWidget(index, 7)
                pan_widget = table.cellWidget(index, 9)
                if isinstance(style_widget, QComboBox):
                    highlight["style"] = clean_text(style_widget.currentData()) or "style-1"
                if isinstance(render_widget, QComboBox):
                    highlight["render"] = safe_highlight_render(render_widget.currentData())
                if isinstance(info_widget, QPlainTextEdit):
                    highlight["info"] = clean_multiline_text(info_widget.toPlainText())
                if isinstance(pan_widget, QCheckBox) and pan_widget.isChecked():
                    highlight["camera_focus"] = True
                else:
                    for key in HIGHLIGHT_CAMERA_FOCUS_KEYS:
                        highlight.pop(key, None)
                question_text = clean_multiline_text(question_widget.toPlainText()) if isinstance(question_widget, QPlainTextEdit) else ""
                text_item = table.item(index, 0)
                selected_text = clean_multiline_text(text_item.text() if text_item else highlight.get("text"))
                if selected_text:
                    source_text = str(root_preview_text or "")
                    found = source_text.find(selected_text)
                    if found >= 0:
                        highlight["start"] = found
                        highlight["end"] = found + len(selected_text)
                    else:
                        highlight["start"] = 0
                        highlight["end"] = 0
                    highlight["text"] = selected_text
                else:
                    highlight["start"] = 0
                    highlight["end"] = 0
                    highlight["text"] = ""
                previous = normalize_picture_question_payload(highlight, row_question_text)
                regions = normalize_picture_question_regions(previous.get("regions") if isinstance(previous, dict) else [])
                region_color = optional_safe_color(previous.get("region_color") if isinstance(previous, dict) else "")
                selected_anchor = safe_picture_question_anchor(anchor_widget.currentData() if isinstance(anchor_widget, QComboBox) else "highlight", "highlight")
                if (question_text or regions) and row_question_text:
                    highlight["picture_question"] = {
                        "text": question_text or row_question_text,
                        "anchor": selected_anchor,
                        "placement": safe_picture_question_placement(placement_widget.currentData() if isinstance(placement_widget, QComboBox) else "auto"),
                    }
                    if regions:
                        highlight["picture_question"]["regions"] = regions
                        if region_color:
                            highlight["picture_question"]["region_color"] = region_color
                else:
                    highlight.pop("picture_question", None)

        def edit_regions_for_row(index: int) -> None:
            if index < 0 or index >= len(highlights):
                return
            sync_from_table()
            row_question_text = self.question_text_for_row(row)
            picture_question = normalize_picture_question_payload(highlights[index], row_question_text)
            if not picture_question:
                if not row_question_text:
                    QMessageBox.information(self, APP_TITLE, "Enter the main Question text before selecting picture regions.")
                    return
                anchor_widget = table.cellWidget(index, 6)
                placement_widget = table.cellWidget(index, 7)
                picture_question = {
                    "text": row_question_text,
                    "anchor": safe_picture_question_anchor(anchor_widget.currentData() if isinstance(anchor_widget, QComboBox) else "picture", "picture"),
                    "placement": safe_picture_question_placement(placement_widget.currentData() if isinstance(placement_widget, QComboBox) else "auto"),
                }
            selected = self.edit_picture_question_region_settings(
                picture_question.get("regions") if isinstance(picture_question, dict) else [],
                picture_question.get("region_color") if isinstance(picture_question, dict) else self.default_picture_region_color,
            )
            if selected is None:
                return
            selected_regions, selected_color = selected
            picture_question["regions"] = normalize_picture_question_regions(selected_regions)
            picture_question["region_color"] = safe_color(selected_color, self.default_picture_region_color)
            picture_question["anchor"] = safe_picture_question_anchor(picture_question.get("anchor"), "picture_regions" if picture_question["regions"] else "picture")
            highlights[index]["picture_question"] = picture_question
            anchor_widget = table.cellWidget(index, 6)
            if isinstance(anchor_widget, QComboBox):
                target = anchor_widget.findData(picture_question["anchor"])
                if target >= 0:
                    anchor_widget.setCurrentIndex(target)
            region_button = table.cellWidget(index, 8)
            if isinstance(region_button, QPushButton):
                self.update_region_button(region_button, picture_question.get("regions"), picture_question.get("region_color"))
            render_preview()

        def preview_ranges() -> list[dict]:
            source = str(root_preview_text or "")
            result: list[dict] = []
            for index, item in enumerate(highlights):
                if not isinstance(item, dict):
                    continue
                try:
                    start = max(0, int(item.get("start") or 0))
                    end = max(0, int(item.get("end") or 0))
                except Exception:
                    start, end = 0, 0
                selected = str(item.get("text") or "")
                if not (end > start) and selected:
                    found = source.find(selected)
                    if found >= 0:
                        start, end = found, found + len(selected)
                start = max(0, min(len(source), start))
                end = max(start, min(len(source), end))
                if end > start:
                    result.append({
                        "start": start,
                        "end": end,
                        "color": safe_color(item.get("color")),
                        "render": safe_highlight_render(item.get("render") or item.get("mode")),
                        "style": clean_text(item.get("style")) or "style-1",
                        "index": index,
                    })
            return sorted(result, key=lambda entry: (entry["start"], entry["end"]))

        def highlight_preview_style(color: str, render_mode: str, style_key: str) -> str:
            safe = safe_color(color)
            red = int(safe[1:3], 16)
            green = int(safe[3:5], 16)
            blue = int(safe[5:7], 16)
            if render_mode == "block":
                radius = "999px" if style_key in {"style-2", "style-3", "style-7"} else ("2px" if style_key in {"style-8", "style-10"} else "8px")
                if style_key == "style-2":
                    return (
                        f"color:{safe};"
                        f"background:linear-gradient(180deg,transparent 0 18%,rgba({red},{green},{blue},0.03) 38%,rgba({red},{green},{blue},0.07) 62%,rgba({red},{green},{blue},0.16) 82%,rgba({red},{green},{blue},0.04) 100%);"
                        f"border:0;"
                        f"border-radius:{radius};padding:1px 6px;"
                        f"box-shadow:0 8px 14px -7px rgba({red},{green},{blue},0.12),inset 0 -2px 0 rgba({red},{green},{blue},0.20);"
                        "font-weight:900;"
                    )
                return (
                    f"color:{safe};"
                    f"background:rgba({red},{green},{blue},0.22);"
                    f"border:1px solid rgba({red},{green},{blue},0.56);"
                    f"border-radius:{radius};padding:1px 6px;"
                    f"box-shadow:0 0 14px rgba({red},{green},{blue},0.38),inset 0 -2px 0 rgba({red},{green},{blue},0.45);"
                    "font-weight:900;"
                )
            return (
                f"color:{safe};"
                f"text-shadow:0 0 12px {safe},0 0 24px rgba({red},{green},{blue},0.75);"
                "font-weight:900;"
            )

        def render_preview_segments(line: str, line_start: int, ranges: list[dict]) -> str:
            overlaps = []
            for item in ranges:
                start = max(0, int(item["start"]) - line_start)
                end = min(len(line), int(item["end"]) - line_start)
                if end > start:
                    overlaps.append({**item, "start": start, "end": end})
            if not overlaps:
                return html_lib.escape(line, quote=True)
            html_parts: list[str] = []
            cursor = 0
            for item in sorted(overlaps, key=lambda entry: (entry["start"], entry["end"])):
                start = max(cursor, int(item["start"]))
                end = max(start, int(item["end"]))
                if start > cursor:
                    html_parts.append(html_lib.escape(line[cursor:start], quote=True))
                style = highlight_preview_style(item.get("color", DEFAULT_HIGHLIGHT_COLOR), item.get("render", "text"), item.get("style", "style-1"))
                html_parts.append(f'<span style="{style}">{html_lib.escape(line[start:end], quote=True)}</span>')
                cursor = end
            if cursor < len(line):
                html_parts.append(html_lib.escape(line[cursor:], quote=True))
            return "".join(html_parts)

        def render_preview() -> None:
            sync_from_table()
            source = str(root_preview_text or "")
            ranges = preview_ranges()
            has_block = any(item.get("render") == "block" for item in ranges)
            line_height = "1.42" if has_block else "1.18"
            offset = 0
            rows = []
            for line in source.split("\n"):
                line_html = render_preview_segments(line, offset, ranges)
                offset += len(line) + 1
                rows.append(f'<div style="min-height:1.18em;">{line_html or "&nbsp;"}</div>')
            preview.setHtml(f"""
                <html><body style="margin:0;background:#061112;color:#ecfff9;font-family:Segoe UI,Arial,sans-serif;">
                  <div style="border:1px solid rgba(70,240,215,.45);border-radius:18px;padding:20px 22px;
                              background:linear-gradient(145deg,rgba(5,24,28,.98),rgba(14,12,30,.96));
                              box-shadow:0 0 34px rgba(70,240,215,.18) inset;">
                    <div style="color:#46f0d7;font-size:11px;font-weight:900;letter-spacing:.16em;text-transform:uppercase;margin-bottom:10px;">
                      Question Root
                    </div>
                    <div style="font-size:30px;line-height:{line_height};font-weight:900;white-space:pre-wrap;">
                      {''.join(rows)}
                    </div>
                  </div>
                </body></html>
            """)

        fill_table()
        table.itemChanged.connect(lambda item: render_preview() if item and item.column() == 0 else None)
        layout.addWidget(table, 1)
        layout.addWidget(preview_title)
        layout.addWidget(preview, 0)
        render_preview()
        buttons = QHBoxLayout()
        pick = QPushButton("Choose color")
        delete = QPushButton("Delete selected")
        clear = QPushButton("Clear all")
        done = QPushButton("OK")
        cancel = QPushButton("Cancel")
        buttons.addWidget(pick)
        buttons.addWidget(delete)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(done)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        def selected_row() -> int:
            rows = sorted({item.row() for item in table.selectedItems()})
            return rows[0] if rows else -1

        def choose_color() -> None:
            sync_from_table()
            index = selected_row()
            if index < 0 or index >= len(highlights):
                return
            current = safe_color(highlights[index].get("color"))
            color = QColorDialog.getColor(QColor(current), dialog, "Choose highlight color")
            if color.isValid():
                highlights[index]["color"] = color.name()
                fill_table()
                table.selectRow(index)
                render_preview()

        def delete_selected() -> None:
            sync_from_table()
            index = selected_row()
            if index < 0 or index >= len(highlights):
                return
            highlights.pop(index)
            fill_table()
            if highlights:
                table.selectRow(min(index, len(highlights) - 1))
            render_preview()

        pick.clicked.connect(choose_color)
        delete.clicked.connect(delete_selected)
        clear.clicked.connect(lambda: (highlights.clear(), fill_table(), render_preview()))
        done.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return
        sync_from_table()
        notice_payload = normalize_root_notice_payload(notice_state["payload"])
        notice_turns = root_notice_turns(notice_payload)
        if notice_turns:
            fallback_question = self.question_text_for_row(row)
            fixed_turns = []
            for turn_index, turn in enumerate(notice_turns):
                next_turn = dict(turn)
                if not clean_multiline_text(next_turn.get("english")) and (
                    clean_multiline_text(next_turn.get("vietnamese"))
                    or clean_text(next_turn.get("voice"))
                    or clean_text(next_turn.get("speaker"))
                    or clean_text(next_turn.get("avatar_path"))
                    or isinstance(next_turn.get("avatar"), dict)
                ) and turn_index == 0:
                    next_turn["english"] = fallback_question
                if clean_multiline_text(next_turn.get("english")) or clean_multiline_text(next_turn.get("vietnamese")):
                    fixed_turns.append(next_turn)
            notice_payload = normalize_root_notice_payload({"turns": fixed_turns})
        if root_notice_turns(notice_payload):
            self.root_notices[row] = notice_payload
        else:
            self.root_notices.pop(row, None)
        if highlights:
            self.root_highlights[row] = highlights
        else:
            self.root_highlights.pop(row, None)

    def questions(self) -> list[dict]:
        result = []
        for row in range(self.table.rowCount()):
            order_text = clean_text(self.table.item(row, self.order_column).text() if self.table.item(row, self.order_column) else "")
            qtype = self.combo_value(row, self.type_column)
            card_mode = normalize_question_card_mode(self.combo_value(row, self.card_mode_column))
            question = clean_text(self.table.item(row, self.question_column).text() if self.table.item(row, self.question_column) else "")
            answer_raw = clean_multiline_text(self.table.item(row, self.answer_column).text() if self.table.item(row, self.answer_column) else "")
            qtype_key = normalize_question_type(qtype)
            select_tokens = select_token_list(answer_raw) if qtype_key == "select" else []
            answer = " ".join(select_tokens) if qtype_key == "select" and select_tokens else clean_text(answer_raw)
            select_targets = normalize_select_targets_payload(self.select_targets.get(row, {}))
            if qtype_key == "select" and not answer and select_targets:
                answer = select_targets_fallback_answer(select_targets)
            if not question or not answer:
                continue
            wrong = []
            seen_wrong = {self.answer_key(answer)}
            for column in range(self.wrong_start_column, self.table.columnCount()):
                value = clean_text(self.table.item(row, column).text() if self.table.item(row, column) else "")
                key = self.answer_key(value)
                if value and key and key not in seen_wrong:
                    seen_wrong.add(key)
                    wrong.append(value)
            try:
                order_value = int(float(order_text)) if order_text else 0
            except Exception:
                order_value = 0
            settings = self.question_settings.get(row) or {}
            question_setting = settings.get("question") if isinstance(settings.get("question"), dict) else {}
            answer_settings = settings.get("answers") if isinstance(settings.get("answers"), dict) else {}
            question_voice = clean_text(question_setting.get("voice")) or (self.voices[0][1] if self.voices else "sot:en-US")
            question_mode = clean_text(question_setting.get("mode") or "off").lower()
            question_audio_text = clean_text(question_setting.get("audio_text")) or question
            audio = {"mode": question_mode, "voice": question_voice, "audio_text": question_audio_text} if question_mode != "off" else {}
            answer_audio_items = []
            answer_info_items = []
            for value in [answer] + wrong:
                override = answer_settings.get(self.answer_key(value), {}) if isinstance(answer_settings, dict) else {}
                if override and (clean_text(override.get("mode")).lower() != "off" or clean_text(override.get("audio_text")) and clean_text(override.get("audio_text")) != value):
                    answer_audio_items.append({
                        "text": value,
                        "audio_text": clean_text(override.get("audio_text")) or value,
                        "voice": clean_text(override.get("voice")) or question_voice,
                        "mode": clean_text(override.get("mode") or "off").lower(),
                    })
                if override and clean_text(override.get("info_text")):
                    answer_info_items.append({
                        "text": value,
                        "info_text": clean_text(override.get("info_text")),
                        "mode": normalize_info_mode(override.get("info_mode") or "audio", "audio"),
                        "voice": clean_text(override.get("info_voice")) or self.default_info_voice(),
                    })
            accepted_answers = [answer] + wrong if qtype_key == "input" else [answer]
            clean_accepted_answers = []
            seen_answers = set()
            for value in accepted_answers:
                key = self.answer_key(value)
                if value and key and key not in seen_answers:
                    seen_answers.add(key)
                    clean_accepted_answers.append(value)
            if qtype_key == "input":
                for special_key in ("__typed_correct__", "__typed_wrong__"):
                    override = answer_settings.get(self.answer_key(special_key), {}) if isinstance(answer_settings, dict) else {}
                    if override and clean_text(override.get("info_text")):
                        answer_info_items.append({
                            "text": special_key,
                            "info_text": clean_text(override.get("info_text")),
                            "mode": normalize_info_mode(override.get("info_mode") or "audio", "audio"),
                            "voice": clean_text(override.get("info_voice")) or self.default_info_voice(),
                        })
            answer_audio = {"items": answer_audio_items} if answer_audio_items else {}
            answer_info = {"items": answer_info_items} if answer_info_items else {}
            question_payload = {
                "id": "q-" + hashlib.sha1(f"{row}:{question}:{answer}".encode("utf-8")).hexdigest()[:10],
                "type": qtype_key,
                "card_mode": card_mode,
                "order": max(0, order_value),
                "question": question,
                "answer": answer,
                "wrong": [] if qtype_key in {"input", "select"} else wrong,
                "audio": audio,
                "answer_audio": answer_audio,
                "answer_info": answer_info,
            }
            if qtype_key == "input" and clean_accepted_answers:
                question_payload["answers"] = clean_accepted_answers
            if qtype_key == "select":
                question_payload["tokens"] = select_tokens
            guidance_tree = normalize_guidance_tree_payload(self.guidance_trees.get(row, {}))
            if guidance_tree:
                question_payload["guidance_tree"] = guidance_tree
            if qtype_key == "select" and select_targets:
                question_payload["select_targets"] = select_targets
            highlights = self.root_highlights.get(row)
            if isinstance(highlights, list) and highlights:
                clean_highlights = []
                for highlight in highlights:
                    if not isinstance(highlight, dict):
                        continue
                    item_payload = dict(highlight)
                    if highlight_camera_focus_enabled(item_payload):
                        item_payload["camera_focus"] = True
                    else:
                        for key in HIGHLIGHT_CAMERA_FOCUS_KEYS:
                            item_payload.pop(key, None)
                    picture_question = normalize_picture_question_payload(item_payload, question)
                    if picture_question:
                        item_payload["picture_question"] = picture_question
                    else:
                        item_payload.pop("picture_question", None)
                    clean_highlights.append(item_payload)
                if clean_highlights:
                    question_payload["root_highlights"] = clean_highlights
            root_notice = normalize_root_notice_payload(self.root_notices.get(row, {}))
            if root_notice:
                question_payload["root_notice"] = root_notice
            result.append(question_payload)
        return result


class BuildQuestionWorker(QThread):
    log_message = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal(str, int)

    def __init__(
        self,
        nodes: list[dict],
        title: str,
        order: str,
        output_path: Path,
        direct_payload: bool = False,
        reward_config: dict | None = None,
    ) -> None:
        super().__init__()
        self.nodes = [dict(item) for item in nodes]
        self.title = clean_text(title) or "Future Question"
        self.order = "shuffle" if clean_text(order).lower() == "shuffle" else "sequence"
        self.output_path = Path(output_path)
        self.direct_payload = bool(direct_payload)
        self.reward_config = normalize_reward_config(reward_config)
        self.last_payload: dict = {}

    def log(self, message: str) -> None:
        text = clean_text(message)
        if text:
            self.log_message.emit(text)

    def audio_clip_payload(self, text: str, voice: str, mode: str, prefix: str, existing: dict | None = None) -> dict:
        audio_text = clean_text(text)
        voice_key = clean_text(voice) or "sot:en-US"
        mode_key = clean_text(mode).lower()
        if mode_key not in {"auto", "click", "both"} or not audio_text:
            return {}
        source = existing if isinstance(existing, dict) else {}
        can_reuse = (
            clean_text(source.get("url") or source.get("u") or source.get("path"))
            and audio_text == clean_text(source.get("audio_text") or source.get("text") or source.get("t") or audio_text)
            and voice_key == clean_text(source.get("voice") or source.get("v") or voice_key)
        )
        if can_reuse:
            return {
                "mode": mode_key,
                "text": audio_text,
                "voice": voice_key,
                "voice_label": clean_text(source.get("voice_label") or source.get("label")) or embedded_voice_label(voice_key),
                "mime": clean_text(source.get("mime") or source.get("m") or "audio/mpeg"),
                "url": clean_text(source.get("url") or source.get("u") or source.get("path")),
            }
        self.log(f"Create question audio: {embedded_voice_label(voice_key)} | {audio_text[:42]}")
        audio_bytes, mime = synthesize_embedded_audio(audio_text, voice_key, self.log)
        asset_id = hashlib.sha1(f"{prefix}:{voice_key}:{audio_text}".encode("utf-8")).hexdigest()[:16]
        url = write_server_sound_asset(f"{safe_segment(prefix)}-{safe_segment(voice_key)}-{asset_id}", audio_bytes, mime)
        return {
            "mode": mode_key,
            "text": audio_text,
            "voice": voice_key,
            "voice_label": embedded_voice_label(voice_key),
            "mime": mime,
            "url": url,
        }

    def root_notice_avatar_payload(self, turn: dict, prefix: str) -> dict:
        raw_avatar_path = clean_text(turn.get("avatar_path"))
        source = Path(raw_avatar_path)
        if source.is_file():
            self.log(f"Copy notice avatar: {source.name}")
            return {
                "url": write_server_picture_asset(f"{safe_segment(prefix)}-{safe_segment(source.stem)}", source.read_bytes(), source.suffix),
                "name": source.name,
            }
        if raw_avatar_path and (re.match(r"^[a-z]+://", raw_avatar_path, re.I) or raw_avatar_path.startswith("/") or raw_avatar_path.replace("\\", "/").startswith("assets/")):
            return {
                "url": raw_avatar_path,
                "name": Path(raw_avatar_path.replace("\\", "/")).name,
            }
        avatar = turn.get("avatar") if isinstance(turn.get("avatar"), dict) else {}
        avatar_url = clean_text(avatar.get("url") if isinstance(avatar, dict) else "")
        if avatar_url:
            return {
                "url": avatar_url,
                "name": clean_text(avatar.get("name")) if isinstance(avatar, dict) else "",
            }
        return {}

    def build_root_notice_payload(self, root_notice: dict, question_text: str, prefix: str) -> dict:
        turns = root_notice_turns(root_notice)
        if not turns:
            return {}
        built_turns = []
        for turn_index, turn in enumerate(turns, 1):
            notice_english = clean_multiline_text(turn.get("english")) or (question_text if turn_index == 1 else "")
            notice_vietnamese = clean_multiline_text(turn.get("vietnamese"))
            if not notice_english and not notice_vietnamese:
                continue
            voice = clean_text(turn.get("voice"))
            speaker = clean_text(turn.get("speaker"))
            turn_payload = {
                "english": notice_english,
                "vietnamese": notice_vietnamese,
            }
            if speaker:
                turn_payload["speaker"] = speaker
            avatar = self.root_notice_avatar_payload(turn, f"{prefix}-turn{turn_index}-avatar")
            if avatar:
                turn_payload["avatar"] = avatar
            if voice:
                turn_payload["voice"] = voice
                turn_payload["voice_label"] = embedded_voice_label(voice)
                existing_notice_audio = turn.get("audio") if isinstance(turn.get("audio"), dict) else {}
                notice_clip = self.audio_clip_payload(
                    notice_english,
                    voice,
                    "auto",
                    f"{prefix}-turn{turn_index}",
                    existing_notice_audio,
                )
                if notice_clip:
                    turn_payload["audio"] = notice_clip
            built_turns.append(turn_payload)
        return {"turns": built_turns} if built_turns else {}

    def run(self) -> None:
        build_session = builder_server2_build_begin("Space_Q", self.output_path)
        build_success = False
        try:
            payload_nodes = []
            file_stem = safe_segment(self.output_path.stem, "space-q", 48)
            for index, node in enumerate(self.nodes, 1):
                root = clean_multiline_text(node.get("root"))
                if not clean_text(root):
                    continue
                node_id = clean_text(node.get("id")) or node_id_for(root)
                root_font_size = int(node.get("root_font_size") or 0)
                connector_style = clean_text(node.get("connector_style")) or "connector-1"
                if connector_style not in {key for _label, key in CONNECTOR_STYLES}:
                    connector_style = "connector-1"
                ship_type = normalize_ship_type(node.get("ship_type"))
                root_card = {"text": root, "connector_style": connector_style, "ship_type": ship_type}
                if root_font_size > 0:
                    root_card["font_size"] = max(18, min(120, root_font_size))
                root_card["input_text_color"] = safe_color(node.get("input_text_color"), DEFAULT_INPUT_TEXT_COLOR)
                if bool_value(node.get("input_text_prysm")):
                    root_card["input_text_prysm"] = True
                cards = {"root": root_card}
                picture_region_color = safe_color(node.get("picture_region_color"), DEFAULT_PICTURE_REGION_COLOR)
                if node.get("picture_enabled") and (clean_text(node.get("picture_path")) or clean_text(node.get("picture_asset_url"))):
                    source = Path(clean_text(node.get("picture_path")))
                    if source.is_file():
                        self.log(f"Copy picture node {index}: {source.name}")
                        cards["picture"] = {
                            "url": write_server_picture_asset(f"spaceq-{file_stem}-{safe_segment(node_id)}-{source.stem}", source.read_bytes(), source.suffix),
                            "caption": clean_text(node.get("picture_caption")) or source.stem,
                            "name": source.name,
                            "region_color": picture_region_color,
                        }
                    elif clean_text(node.get("picture_asset_url")):
                        cards["picture"] = {
                            "url": clean_text(node.get("picture_asset_url")),
                            "caption": clean_text(node.get("picture_caption") or node.get("picture_asset_name")),
                            "name": clean_text(node.get("picture_asset_name")),
                            "region_color": picture_region_color,
                        }
                if node.get("audio_enabled") and clean_text(node.get("audio_text")):
                    voice = clean_text(node.get("audio_voice")) or "sot:en-US"
                    audio_text = clean_text(node.get("audio_text"))
                    can_reuse_audio = (
                        clean_text(node.get("audio_asset_url"))
                        and audio_text == clean_text(node.get("audio_asset_text"))
                        and voice == clean_text(node.get("audio_asset_voice"))
                    )
                    if can_reuse_audio:
                        self.log(f"Reuse audio node {index}: {embedded_voice_label(voice)}")
                        cards["audio"] = {
                            "id": clean_text(node.get("audio_asset_id")) or hashlib.sha1(f"{voice}:{audio_text}".encode("utf-8")).hexdigest()[:16],
                            "text": audio_text,
                            "voice": voice,
                            "voice_label": clean_text(node.get("audio_asset_voice_label")) or embedded_voice_label(voice),
                            "mime": clean_text(node.get("audio_asset_mime")) or "audio/mpeg",
                            "url": clean_text(node.get("audio_asset_url")),
                        }
                    else:
                        self.log(f"Tạo audio node {index}: {embedded_voice_label(voice)}")
                        audio_bytes, mime = synthesize_embedded_audio(audio_text, voice, self.log)
                        asset_id = hashlib.sha1(f"{file_stem}:{node_id}:{voice}:{audio_text}".encode("utf-8")).hexdigest()[:16]
                        asset_path = write_server_sound_asset(f"spaceq-{file_stem}-{safe_segment(node_id)}-{safe_segment(voice)}-{asset_id}", audio_bytes, mime)
                        cards["audio"] = {
                            "id": asset_id,
                            "text": audio_text,
                            "voice": voice,
                            "voice_label": embedded_voice_label(voice),
                            "mime": mime,
                            "url": asset_path,
                        }
                questions = node.get("questions") if isinstance(node.get("questions"), list) else []
                question_payloads = []
                for q_index, item in enumerate(questions, 1):
                    if not isinstance(item, dict) or not clean_text(item.get("question")):
                        continue
                    question_text = clean_text(item.get("question"))
                    qtype_key = normalize_question_type(item.get("type"))
                    raw_answer_text = clean_multiline_text(item.get("answer"))
                    select_tokens = select_token_list(
                        item.get("tokens") or item.get("select_tokens") or item.get("selectTokens") or item.get("tk"),
                        raw_answer_text,
                    ) if qtype_key == "select" else []
                    answer_text = " ".join(select_tokens) if qtype_key == "select" and select_tokens else clean_text(raw_answer_text)
                    select_targets = normalize_select_targets_payload(item.get("select_targets") or item.get("selectTargets") or item.get("selection_targets") or item.get("selectionTargets") or item.get("stg"))
                    if qtype_key == "select" and not answer_text and select_targets:
                        answer_text = select_targets_fallback_answer(select_targets)
                    if not answer_text:
                        continue
                    wrong_values = [clean_text(value.get("text") if isinstance(value, dict) else value) for value in (item.get("wrong") if isinstance(item.get("wrong"), list) else [])]
                    wrong_values = [value for value in wrong_values if value]
                    raw_answers = item.get("answers") if isinstance(item.get("answers"), list) else item.get("accept")
                    if not isinstance(raw_answers, list):
                        raw_answers = item.get("accepts") if isinstance(item.get("accepts"), list) else []
                    accepted_values = []
                    seen_accepted = set()
                    for value in [answer_text] + [
                        clean_text(entry.get("text") if isinstance(entry, dict) else entry)
                        for entry in raw_answers
                        if clean_text(entry.get("text") if isinstance(entry, dict) else entry)
                    ]:
                        key = re.sub(r"\s+", " ", clean_text(value).lower()).strip()
                        if value and key and key not in seen_accepted:
                            seen_accepted.add(key)
                            accepted_values.append(value)
                    if qtype_key == "input":
                        wrong_values = []
                    if qtype_key == "select":
                        wrong_values = []
                    try:
                        q_order = int(float(item.get("order") or 0))
                    except Exception:
                        q_order = 0
                    question_item = {
                        "id": clean_text(item.get("id")) or "q-" + hashlib.sha1(f"{node_id}:{q_index}:{question_text}:{answer_text}".encode("utf-8")).hexdigest()[:10],
                        "type": qtype_key,
                        "card_mode": normalize_question_card_mode(item.get("card_mode") or item.get("cardMode") or item.get("question_card_mode") or item.get("questionCardMode") or item.get("display_mode") or item.get("displayMode") or item.get("cm")),
                        "order": max(0, q_order),
                        "question": question_text,
                        "answer": answer_text,
                        "wrong": wrong_values,
                    }
                    question_item["type"] = qtype_key
                    if qtype_key == "input" and accepted_values:
                        question_item["answers"] = accepted_values
                    if qtype_key == "select":
                        question_item["tokens"] = select_tokens
                    if qtype_key == "select" and select_targets:
                        question_item["select_targets"] = select_targets
                    guidance_tree = normalize_guidance_tree_payload(item.get("guidance_tree") or item.get("guidanceTree") or item.get("guide_tree") or item.get("gt"))
                    if guidance_tree:
                        question_item["guidance_tree"] = guidance_tree
                    root_notice = normalize_root_notice_payload(item.get("root_notice") or item.get("rootNotice") or item.get("rn"))
                    if root_notice:
                        notice_payload = self.build_root_notice_payload(
                            root_notice,
                            question_text,
                            f"spaceq-{file_stem}-{safe_segment(node_id)}-q{q_index}-root-notice",
                        )
                        if notice_payload:
                            question_item["root_notice"] = notice_payload
                    root_highlights = item.get("root_highlights") if isinstance(item.get("root_highlights"), list) else []
                    if root_highlights:
                        clean_root_highlights = []
                        for highlight in root_highlights:
                            if not isinstance(highlight, dict):
                                continue
                            try:
                                start = int(highlight.get("start") or highlight.get("s") or 0)
                                end = int(highlight.get("end") or highlight.get("e") or 0)
                            except Exception:
                                start, end = 0, 0
                            text = clean_multiline_text(highlight.get("text") or highlight.get("t"))
                            picture_question = normalize_picture_question_payload(highlight, question_text)
                            if end > start or text or picture_question:
                                item_payload = {
                                    "start": max(0, start),
                                    "end": max(0, end),
                                    "text": text,
                                    "color": safe_color(highlight.get("color") or highlight.get("c")),
                                    "style": clean_text(highlight.get("style") or highlight.get("st")) or "style-1",
                                    "render": safe_highlight_render(highlight.get("render") or highlight.get("mode") or highlight.get("m")),
                                    "info": clean_multiline_text(highlight.get("info") or highlight.get("note") or highlight.get("card") or highlight.get("i")),
                                }
                                if highlight_camera_focus_enabled(highlight):
                                    item_payload["camera_focus"] = True
                                if picture_question:
                                    item_payload["picture_question"] = picture_question
                                clean_root_highlights.append(item_payload)
                        if clean_root_highlights:
                            question_item["root_highlights"] = clean_root_highlights
                    q_audio = item.get("audio") if isinstance(item.get("audio"), dict) else {}
                    q_mode = clean_text(q_audio.get("mode") or item.get("audio_mode") or "off").lower()
                    q_voice = clean_text(q_audio.get("voice") or item.get("audio_voice") or node.get("audio_voice")) or "sot:en-US"
                    q_audio_text = clean_text(q_audio.get("audio_text") or q_audio.get("text") or q_audio.get("t") or question_text)
                    built_question_audio = self.audio_clip_payload(q_audio_text, q_voice, q_mode, f"spaceq-{file_stem}-{safe_segment(node_id)}-q{q_index}", q_audio)
                    if built_question_audio:
                        question_item["audio"] = built_question_audio
                    answer_audio = item.get("answer_audio") if isinstance(item.get("answer_audio"), dict) else {}
                    answer_mode = clean_text(answer_audio.get("mode") or item.get("answer_audio_mode") or "off").lower()
                    answer_voice = clean_text(answer_audio.get("voice") or item.get("answer_audio_voice") or q_voice) or "sot:en-US"
                    existing_items = answer_audio.get("items") if isinstance(answer_audio.get("items"), list) else []
                    correct_existing = next((entry for entry in existing_items if isinstance(entry, dict) and clean_text(entry.get("text") or entry.get("t")) == answer_text), answer_audio)
                    correct_mode = clean_text(correct_existing.get("mode") or answer_mode).lower()
                    correct_voice = clean_text(correct_existing.get("voice") or correct_existing.get("v") or answer_voice) or answer_voice
                    correct_audio_text = clean_text(correct_existing.get("audio_text") or correct_existing.get("text") or correct_existing.get("t") or answer_text)
                    built_answer_audio = self.audio_clip_payload(correct_audio_text, correct_voice, correct_mode, f"spaceq-{file_stem}-{safe_segment(node_id)}-q{q_index}-answer", correct_existing)
                    answer_audio_payload = built_answer_audio or {"mode": answer_mode, "voice": answer_voice}
                    answer_items = []
                    if built_answer_audio:
                        answer_items.append({**built_answer_audio, "text": answer_text, "audio_text": correct_audio_text, "role": "correct"})
                    other_answer_values = accepted_values[1:] if qtype_key == "input" else wrong_values
                    other_answer_role = "accepted" if qtype_key == "input" else "wrong"
                    for wrong_index, wrong_text in enumerate(other_answer_values, 1):
                        existing = next((entry for entry in existing_items if isinstance(entry, dict) and clean_text(entry.get("text") or entry.get("t")) == wrong_text), {})
                        existing_mode = clean_text(existing.get("mode")).lower()
                        if existing and existing_mode == "off":
                            answer_items.append({"text": wrong_text, "mode": "off", "voice": clean_text(existing.get("voice")) or answer_voice, "role": other_answer_role})
                            continue
                        wrong_audio_text = clean_text(existing.get("audio_text") or existing.get("text") or existing.get("t") or wrong_text)
                        wrong_clip = self.audio_clip_payload(wrong_audio_text, clean_text(existing.get("voice")) or answer_voice, existing_mode or answer_mode, f"spaceq-{file_stem}-{safe_segment(node_id)}-q{q_index}-wrong{wrong_index}", existing)
                        if wrong_clip:
                            answer_items.append({**wrong_clip, "text": wrong_text, "audio_text": wrong_audio_text, "role": other_answer_role})
                    if built_answer_audio or answer_items:
                        answer_audio_payload["items"] = answer_items
                        question_item["answer_audio"] = answer_audio_payload
                    answer_info = item.get("answer_info") if isinstance(item.get("answer_info"), dict) else {}
                    info_items = answer_info.get("items") if isinstance(answer_info.get("items"), list) else []
                    built_info_items = []
                    for info_index, info in enumerate(info_items, 1):
                        if not isinstance(info, dict):
                            continue
                        target_text = clean_text(info.get("text") or info.get("t") or info.get("answer") or info.get("a"))
                        info_text = clean_text(info.get("info_text") or info.get("info") or info.get("explain") or info.get("explanation"))
                        info_mode = normalize_info_mode(info.get("mode") or info.get("info_mode") or "audio", "audio")
                        info_voice = clean_text(info.get("voice") or info.get("v")) or DEFAULT_INFO_VOICE
                        if not target_text or not info_text:
                            continue
                        info_payload = {
                            "text": target_text,
                            "info_text": info_text,
                            "mode": "audio" if info_mode == "audio" else "type",
                            "voice": info_voice,
                            "voice_label": embedded_voice_label(info_voice),
                        }
                        if info_mode == "audio":
                            clip = self.audio_clip_payload(info_text, info_voice, "click", f"spaceq-{file_stem}-{safe_segment(node_id)}-q{q_index}-info{info_index}", info)
                            if clip:
                                info_payload["audio"] = clip
                        built_info_items.append(info_payload)
                    if built_info_items:
                        question_item["answer_info"] = {"items": built_info_items}
                    question_payloads.append(question_item)
                if node.get("questions_enabled") and question_payloads:
                    cards["questions"] = question_payloads
                payload_nodes.append({
                    "id": node_id,
                    "root": root,
                    "connector_style": connector_style,
                    "ship_type": ship_type,
                    "cards": cards,
                })
            if not payload_nodes:
                raise RuntimeError("Chưa có node Root hợp lệ.")
            payload = {
                "k": "ftq",
                "kind": "future_question_payload",
                "version": 1,
                "title": self.title,
                "order": self.order,
                "nodes": payload_nodes,
                "study": {},
                "rewards": self.reward_config,
                "created": int(time.time()),
            }
            effects = default_question_effects_payload()
            if effects:
                payload["effects"] = effects
                self.log("Attach Space_Q true/false answer effect sounds.")
            else:
                self.log("Warning: true/false answer effect sounds were not found in C:\\server data\\Sound.")
            self.last_payload = payload
            if self.direct_payload:
                manifest = encode_future_payload(payload, self.output_path, "Space_Q")
            else:
                manifest = encode_future_manifest(payload, self.title, self.output_path, "Space_Q")
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(manifest, encoding="utf-8")
            self.finished_ok.emit(str(self.output_path), len(payload_nodes))
            build_success = True
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            builder_server2_build_end(build_session, "Space_Q", self.output_path, build_success)


class FutureQuestionBuilder(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.voices = question_voice_specs()
        self.nodes: list[dict] = []
        self.current_row = -1
        self.loading_node = False
        self.worker: BuildQuestionWorker | None = None
        self.worker_mode = ""
        self.picture_region_color_value = DEFAULT_PICTURE_REGION_COLOR
        self.input_text_color_value = DEFAULT_INPUT_TEXT_COLOR
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        left = QVBoxLayout()
        main.addLayout(left, 0)
        left.addWidget(QLabel("Nodes"))
        self.node_list = QListWidget()
        left.addWidget(self.node_list, 1)
        node_buttons = QHBoxLayout()
        self.add_node_button = QPushButton("Add node")
        self.remove_node_button = QPushButton("Remove")
        node_buttons.addWidget(self.add_node_button)
        node_buttons.addWidget(self.remove_node_button)
        left.addLayout(node_buttons)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_holder = QWidget()
        right_holder.setMinimumWidth(900)
        right_scroll.setWidget(right_holder)
        main.addWidget(right_scroll, 1)
        right = QVBoxLayout(right_holder)
        top = QGridLayout()
        right.addLayout(top)
        top.addWidget(QLabel("Title"), 0, 0)
        self.title_input = QLineEdit(clean_text(self.settings.get("title")) or "Future Question")
        top.addWidget(self.title_input, 0, 1)
        top.addWidget(QLabel("Node order"), 0, 2)
        self.order_combo = QComboBox()
        self.order_combo.addItem("Theo thứ tự", "sequence")
        self.order_combo.addItem("Xáo node", "shuffle")
        if clean_text(self.settings.get("order")) == "shuffle":
            self.order_combo.setCurrentIndex(1)
        top.addWidget(self.order_combo, 0, 3)
        rewards = normalize_reward_config(self.settings.get("rewards"))
        reward_tab = QTabWidget()
        reward_panel = QWidget()
        reward_layout = QGridLayout(reward_panel)
        crystal = rewards.get("crystal", {})
        reward_layout.addWidget(QLabel("Crystal name"), 0, 0)
        self.crystal_name_input = QLineEdit(clean_text(crystal.get("name")) or DEFAULT_CRYSTAL_NAME)
        self.crystal_name_input.setPlaceholderText("Prism Crystal")
        reward_layout.addWidget(self.crystal_name_input, 0, 1)
        reward_layout.addWidget(QLabel("Crystal use"), 1, 0)
        self.crystal_use_input = QPlainTextEdit(clean_multiline_text(crystal.get("use")) or DEFAULT_CRYSTAL_USE)
        self.crystal_use_input.setPlaceholderText("Stores learning energy for future item upgrades.")
        self.crystal_use_input.setMaximumHeight(78)
        reward_layout.addWidget(self.crystal_use_input, 1, 1)
        reward_tab.addTab(reward_panel, "Crystal reward")
        right.addWidget(reward_tab)
        right.addWidget(QLabel("Root card text"))
        self.root_text = QPlainTextEdit()
        self.root_text.setPlaceholderText("Nhập nội dung Root. Runtime sẽ đánh máy text này ở card chính.")
        self.root_text.setContextMenuPolicy(Qt.CustomContextMenu)
        right.addWidget(self.root_text, 1)
        root_options = QHBoxLayout()
        right.addLayout(root_options)
        root_options.addWidget(QLabel("Root text size"))
        self.root_font_size = QSpinBox()
        self.root_font_size.setRange(18, 120)
        self.root_font_size.setSingleStep(2)
        self.root_font_size.setValue(20)
        self.root_font_size.setSuffix(" px")
        root_options.addWidget(self.root_font_size)
        root_options.addWidget(QLabel("Input text"))
        self.input_text_color_button = QPushButton()
        self.input_text_color_button.setMinimumWidth(132)
        root_options.addWidget(self.input_text_color_button)
        self.input_text_prysm_check = QCheckBox("Prysm")
        self.input_text_prysm_check.setToolTip("Mix input text colors like prism crystal instead of one solid color.")
        root_options.addWidget(self.input_text_prysm_check)
        root_options.addWidget(QLabel("Region color"))
        self.picture_region_color_button = QPushButton()
        self.picture_region_color_button.setMinimumWidth(132)
        root_options.addWidget(self.picture_region_color_button)
        root_options.addWidget(QLabel("Ship type"))
        self.ship_type = QComboBox()
        for label, key in SHIP_TYPES:
            self.ship_type.addItem(label, key)
        root_options.addWidget(self.ship_type)
        root_options.addWidget(QLabel("Connector"))
        self.connector_style = QComboBox()
        for label, key in CONNECTOR_STYLES:
            self.connector_style.addItem(label, key)
        root_options.addWidget(self.connector_style)
        root_options.addStretch(1)
        card_line = QHBoxLayout()
        right.addLayout(card_line)
        self.card_table = QTableWidget(4, 2)
        self.card_table.setHorizontalHeaderLabels(["Card type", "Status"])
        self.card_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.card_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for row, name in enumerate(["Root", "Picture", "Audio", "Question"]):
            self.card_table.setItem(row, 0, QTableWidgetItem(name))
            self.card_table.setItem(row, 1, QTableWidgetItem(""))
        self.card_table.setMaximumHeight(150)
        card_line.addWidget(self.card_table, 1)
        card_buttons = QVBoxLayout()
        self.add_card_button = QPushButton("Add / Update selected card")
        self.remove_card_button = QPushButton("Remove selected card")
        self.edit_questions_button = QPushButton("Popup Question card")
        card_buttons.addWidget(self.add_card_button)
        card_buttons.addWidget(self.remove_card_button)
        card_buttons.addWidget(self.edit_questions_button)
        card_buttons.addStretch(1)
        card_line.addLayout(card_buttons)
        panels = QGridLayout()
        right.addLayout(panels)
        self.picture_check = QCheckBox("Picture card")
        self.picture_path = QLineEdit()
        self.picture_path.setReadOnly(True)
        self.picture_caption = QLineEdit()
        self.picture_caption.setPlaceholderText("Caption")
        self.choose_picture_button = QPushButton("Chọn ảnh")
        panels.addWidget(self.picture_check, 0, 0)
        panels.addWidget(self.picture_path, 0, 1)
        panels.addWidget(self.choose_picture_button, 0, 2)
        panels.addWidget(self.picture_caption, 1, 1, 1, 2)
        self.audio_check = QCheckBox("Audio card")
        self.audio_text = QPlainTextEdit()
        self.audio_text.setPlaceholderText("Text để tạo âm thanh cho card Audio")
        self.audio_text.setMaximumHeight(90)
        self.audio_voice = QComboBox()
        for label, key in self.voices:
            self.audio_voice.addItem(label, key)
        panels.addWidget(self.audio_check, 2, 0)
        panels.addWidget(self.audio_text, 2, 1)
        panels.addWidget(self.audio_voice, 2, 2)
        self.question_check = QCheckBox("Question card")
        self.question_summary = QLabel("0 questions")
        panels.addWidget(self.question_check, 3, 0)
        panels.addWidget(self.question_summary, 3, 1, 1, 2)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        right.addWidget(line)
        bottom = QHBoxLayout()
        right.addLayout(bottom)
        self.load_space_q_button = QPushButton("Load Space_Q")
        self.generate_button = QPushButton("Build Space_Q")
        self.preview_button = QPushButton("Run test HTML")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        bottom.addWidget(self.load_space_q_button)
        bottom.addWidget(self.generate_button)
        bottom.addWidget(self.preview_button)
        bottom.addWidget(self.progress, 1)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(130)
        right.addWidget(self.log_box)
        self.add_node_button.clicked.connect(self.add_node)
        self.remove_node_button.clicked.connect(self.remove_node)
        self.node_list.currentRowChanged.connect(self.change_node)
        self.choose_picture_button.clicked.connect(self.choose_picture)
        self.add_card_button.clicked.connect(self.add_or_update_selected_card)
        self.remove_card_button.clicked.connect(self.remove_selected_card)
        self.edit_questions_button.clicked.connect(self.edit_questions)
        self.root_text.customContextMenuRequested.connect(self.show_root_context_menu)
        self.load_space_q_button.clicked.connect(self.load_space_q)
        self.generate_button.clicked.connect(self.generate)
        self.preview_button.clicked.connect(self.run_preview)
        self.input_text_color_button.clicked.connect(self.choose_input_text_color)
        self.picture_region_color_button.clicked.connect(self.choose_picture_region_color)
        self.crystal_name_input.textChanged.connect(self.save_builder_state)
        self.crystal_use_input.textChanged.connect(self.save_builder_state)
        self.root_text.textChanged.connect(self.on_node_field_changed)
        self.root_font_size.valueChanged.connect(self.on_node_field_changed)
        self.input_text_prysm_check.toggled.connect(self.on_node_field_changed)
        self.ship_type.currentIndexChanged.connect(self.on_node_field_changed)
        self.connector_style.currentIndexChanged.connect(self.on_node_field_changed)
        self.picture_check.toggled.connect(self.on_node_field_changed)
        self.picture_caption.textChanged.connect(self.on_node_field_changed)
        self.audio_check.toggled.connect(self.on_node_field_changed)
        self.audio_text.textChanged.connect(self.on_node_field_changed)
        self.audio_voice.currentIndexChanged.connect(self.on_node_field_changed)
        self.question_check.toggled.connect(self.on_node_field_changed)
        self.apply_style()
        self.update_picture_region_color_button()
        if not self.restore_builder_state():
            self.add_node()

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QDialog { background: #061112; color: #ecfff9; }
            QWidget { background-color: #061112; color: #ecfff9; font-size: 15px; }
            QScrollArea, QAbstractScrollArea, QScrollArea > QWidget, QAbstractScrollArea > QWidget {
                background: #061112; border: none;
            }
            QLabel#sectionTitle {
                color: #46f0d7; font-size: 20px; font-weight: 900; letter-spacing: .08em;
                padding: 8px 2px;
            }
            QLineEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox, QSpinBox {
                background: #071719; border: 1px solid rgba(70, 240, 215, 0.32);
                border-radius: 10px; padding: 7px; color: #ecfff9;
                selection-background-color: rgba(70, 240, 215, 0.32);
                selection-color: #ffffff;
            }
            QPlainTextEdit { font-family: Consolas, "Segoe UI", sans-serif; font-size: 16px; }
            QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
                background: #081618; color: rgba(236, 255, 249, 0.48);
                border-color: rgba(70, 240, 215, 0.18);
            }
            QListWidget, QTableWidget {
                alternate-background-color: #0a2022;
                gridline-color: rgba(70, 240, 215, 0.16);
            }
            QTableWidget::item {
                background: rgba(8, 26, 28, 0.96);
                border-bottom: 1px solid rgba(70, 240, 215, 0.12);
                padding: 6px;
            }
            QTableWidget::item:selected, QListWidget::item:selected {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(70,240,215,.34), stop:1 rgba(216,108,255,.22));
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background: #061314;
                color: #ecfff9;
                border: 1px solid rgba(70, 240, 215, 0.44);
                selection-background-color: rgba(70, 240, 215, 0.32);
            }
            QMenu {
                background: #071719;
                color: #ecfff9;
                border: 1px solid rgba(70, 240, 215, 0.42);
                padding: 6px;
            }
            QMenu::item {
                background: transparent;
                padding: 8px 18px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background: rgba(70, 240, 215, 0.22);
                color: #ffffff;
            }
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #123f3d, stop:1 #341f4f);
                border: 1px solid rgba(70,240,215,.48); border-radius: 12px; padding: 11px 14px; font-weight: 850;
            }
            QPushButton:hover { border-color: rgba(126,255,235,.9); background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #185854, stop:1 #48296b); }
            QPushButton:disabled { color: rgba(236, 255, 249, 0.42); background: #0a1719; border-color: rgba(70,240,215,.16); }
            QCheckBox { spacing: 8px; font-weight: 700; }
            QHeaderView::section { background: #0b2224; color: #8fffee; border: 0; padding: 6px; }
            QTableCornerButton::section { background: #0b2224; border: 0; }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #061112;
                border: 1px solid rgba(70, 240, 215, 0.18);
                margin: 0;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #46f0d7, stop:1 #d86cff);
                border-radius: 7px;
                min-height: 28px;
                min-width: 28px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0; height: 0; border: 0; background: transparent;
            }
            QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
            QProgressBar {
                border: 1px solid rgba(70, 240, 215, 0.3); border-radius: 10px;
                background: #071719; text-align: center; color: #ecfff9;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #46f0d7, stop:1 #d86cff);
            }
        """)

    def log(self, message: str) -> None:
        text = clean_text(message)
        if text:
            self.log_box.appendPlainText(text)

    def ensure_voice_choice(self, voice_key: str, label: str = "") -> None:
        key = clean_text(voice_key)
        if not key or self.audio_voice.findData(key) >= 0:
            return
        display = clean_text(label) or embedded_voice_label(key)
        self.voices.append((display, key))
        self.audio_voice.addItem(display, key)

    def restore_builder_state(self) -> bool:
        draft_nodes = self.settings.get("draft_nodes")
        if not isinstance(draft_nodes, list) or not draft_nodes:
            return False
        self.loading_node = True
        try:
            self.nodes = [dict(node) for node in draft_nodes if isinstance(node, dict)]
            if not self.nodes:
                return False
            self.node_list.clear()
            for index, node in enumerate(self.nodes, 1):
                self.ensure_voice_choice(clean_text(node.get("audio_voice")), clean_text(node.get("audio_asset_voice_label")))
                root = clean_text(node.get("root")) or "Untitled root"
                self.node_list.addItem(QListWidgetItem(f"Node {index}: {root[:42]}"))
            current = max(0, min(len(self.nodes) - 1, int(self.settings.get("draft_current_row") or 0)))
            self.current_row = current
            self.node_list.setCurrentRow(current)
        except Exception:
            self.nodes = []
            self.node_list.clear()
            return False
        finally:
            self.loading_node = False
        self.load_current_node()
        self.log("Restored autosaved draft.")
        return True

    def save_builder_state(self) -> None:
        self.save_current_node()
        self.settings["title"] = clean_text(self.title_input.text())
        self.settings["order"] = clean_text(self.order_combo.currentData())
        self.settings["rewards"] = self.current_reward_config()
        self.settings["draft_nodes"] = self.nodes
        self.settings["draft_current_row"] = max(0, self.current_row)
        save_settings(self.settings)

    def current_reward_config(self) -> dict:
        return normalize_reward_config({
            "crystal": {
                "name": clean_text(self.crystal_name_input.text()) if hasattr(self, "crystal_name_input") else DEFAULT_CRYSTAL_NAME,
                "use": clean_multiline_text(self.crystal_use_input.toPlainText()) if hasattr(self, "crystal_use_input") else DEFAULT_CRYSTAL_USE,
            }
        })

    def add_node(self) -> None:
        self.save_current_node()
        node = {
            "id": node_id_for("Root"),
            "root": "",
            "root_font_size": 20,
            "input_text_color": DEFAULT_INPUT_TEXT_COLOR,
            "input_text_prysm": False,
            "picture_region_color": DEFAULT_PICTURE_REGION_COLOR,
            "connector_style": "connector-1",
            "ship_type": "random",
            "picture_enabled": False,
            "picture_path": "",
            "picture_caption": "",
            "picture_asset_url": "",
            "picture_asset_name": "",
            "audio_enabled": False,
            "audio_text": "",
            "audio_voice": self.voices[0][1] if self.voices else "sot:en-US",
            "audio_asset_url": "",
            "audio_asset_mime": "",
            "audio_asset_id": "",
            "audio_asset_text": "",
            "audio_asset_voice": "",
            "audio_asset_voice_label": "",
            "questions_enabled": False,
            "questions": [],
        }
        self.nodes.append(node)
        item = QListWidgetItem(f"Node {len(self.nodes)}")
        self.node_list.addItem(item)
        self.node_list.setCurrentRow(len(self.nodes) - 1)

    def remove_node(self) -> None:
        row = self.node_list.currentRow()
        if row < 0 or row >= len(self.nodes):
            return
        self.nodes.pop(row)
        self.node_list.takeItem(row)
        if not self.nodes:
            self.add_node()
        else:
            self.node_list.setCurrentRow(min(row, len(self.nodes) - 1))

    def change_node(self, row: int) -> None:
        if self.loading_node:
            return
        self.save_current_node()
        self.current_row = row
        self.load_current_node()

    def on_node_field_changed(self, *_args) -> None:
        if not self.loading_node:
            self.save_current_node()
            self.refresh_node_label()
            self.refresh_card_table()

    def update_input_text_color_button(self, color: object | None = None) -> None:
        if color is not None:
            self.input_text_color_value = safe_color(color, DEFAULT_INPUT_TEXT_COLOR)
        color_value = safe_color(self.input_text_color_value, DEFAULT_INPUT_TEXT_COLOR)
        self.input_text_color_value = color_value
        red = int(color_value[1:3], 16)
        green = int(color_value[3:5], 16)
        blue = int(color_value[5:7], 16)
        luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
        text_color = "#061112" if luminance > 0.62 else "#ecfff9"
        self.input_text_color_button.setText(f"Input {color_value.upper()}")
        self.input_text_color_button.setToolTip("Choose the typed answer text color for input questions in this node.")
        self.input_text_color_button.setStyleSheet(
            "QPushButton {"
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba({red},{green},{blue},0.96), stop:1 rgba(216,108,255,0.18));"
            f"color: {text_color};"
            f"border: 1px solid rgba({red},{green},{blue},0.86);"
            "border-radius: 10px;"
            "padding: 8px 12px;"
            "font-weight: 900;"
            "}"
        )

    def choose_input_text_color(self) -> None:
        color = QColorDialog.getColor(
            QColor(safe_color(self.input_text_color_value, DEFAULT_INPUT_TEXT_COLOR)),
            self,
            "Choose input text color",
        )
        if not color.isValid():
            return
        self.update_input_text_color_button(color.name())
        self.on_node_field_changed()

    def update_picture_region_color_button(self, color: object | None = None) -> None:
        if color is not None:
            self.picture_region_color_value = safe_color(color, DEFAULT_PICTURE_REGION_COLOR)
        color_value = safe_color(self.picture_region_color_value, DEFAULT_PICTURE_REGION_COLOR)
        self.picture_region_color_value = color_value
        red = int(color_value[1:3], 16)
        green = int(color_value[3:5], 16)
        blue = int(color_value[5:7], 16)
        luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
        text_color = "#061112" if luminance > 0.62 else "#ecfff9"
        self.picture_region_color_button.setText(f"Region {color_value.upper()}")
        self.picture_region_color_button.setToolTip("Choose the picture region bubble color for this node/image.")
        self.picture_region_color_button.setStyleSheet(
            "QPushButton {"
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba({red},{green},{blue},0.95), stop:1 rgba(70,240,215,0.26));"
            f"color: {text_color};"
            f"border: 1px solid rgba({red},{green},{blue},0.86);"
            "border-radius: 10px;"
            "padding: 8px 12px;"
            "font-weight: 900;"
            "}"
        )

    def choose_picture_region_color(self) -> None:
        color = QColorDialog.getColor(
            QColor(safe_color(self.picture_region_color_value, DEFAULT_PICTURE_REGION_COLOR)),
            self,
            "Choose picture region color",
        )
        if not color.isValid():
            return
        self.update_picture_region_color_button(color.name())
        self.on_node_field_changed()

    def save_current_node(self) -> None:
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        node = self.nodes[row]
        node["root"] = clean_multiline_text(self.root_text.toPlainText())
        node["root_font_size"] = int(self.root_font_size.value())
        node["input_text_color"] = safe_color(self.input_text_color_value, DEFAULT_INPUT_TEXT_COLOR)
        node["input_text_prysm"] = bool(self.input_text_prysm_check.isChecked())
        node["picture_region_color"] = safe_color(self.picture_region_color_value, DEFAULT_PICTURE_REGION_COLOR)
        node["connector_style"] = clean_text(self.connector_style.currentData()) or "connector-1"
        node["ship_type"] = normalize_ship_type(self.ship_type.currentData())
        node["picture_enabled"] = self.picture_check.isChecked()
        node["picture_path"] = self.picture_path.text().strip()
        node["picture_caption"] = self.picture_caption.text().strip()
        node["audio_enabled"] = self.audio_check.isChecked()
        node["audio_text"] = self.audio_text.toPlainText().strip()
        node["audio_voice"] = clean_text(self.audio_voice.currentData()) or "sot:en-US"
        node["questions_enabled"] = self.question_check.isChecked()

    def load_current_node(self) -> None:
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        node = self.nodes[row]
        self.loading_node = True
        try:
            self.root_text.setPlainText(clean_multiline_text(node.get("root")))
            self.root_font_size.setValue(max(18, min(120, int(node.get("root_font_size") or 20))))
            self.update_input_text_color_button(node.get("input_text_color") or DEFAULT_INPUT_TEXT_COLOR)
            self.input_text_prysm_check.setChecked(bool_value(node.get("input_text_prysm")))
            self.update_picture_region_color_button(node.get("picture_region_color") or DEFAULT_PICTURE_REGION_COLOR)
            connector = clean_text(node.get("connector_style")) or "connector-1"
            connector_index = self.connector_style.findData(connector)
            self.connector_style.setCurrentIndex(max(0, connector_index))
            ship = normalize_ship_type(node.get("ship_type"))
            ship_index = self.ship_type.findData(ship)
            self.ship_type.setCurrentIndex(max(0, ship_index))
            self.picture_check.setChecked(bool(node.get("picture_enabled")))
            self.picture_path.setText(clean_text(node.get("picture_path")))
            self.picture_caption.setText(clean_text(node.get("picture_caption")))
            self.audio_check.setChecked(bool(node.get("audio_enabled")))
            self.audio_text.setPlainText(clean_text(node.get("audio_text")))
            voice = clean_text(node.get("audio_voice"))
            self.ensure_voice_choice(voice, clean_text(node.get("audio_asset_voice_label")))
            voice_index = self.audio_voice.findData(voice)
            self.audio_voice.setCurrentIndex(max(0, voice_index))
            self.question_check.setChecked(bool(node.get("questions_enabled")))
        finally:
            self.loading_node = False
        self.refresh_node_label()
        self.refresh_card_table()

    def refresh_node_label(self) -> None:
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        root = clean_text(self.nodes[row].get("root")) or "Untitled root"
        item = self.node_list.item(row)
        if item:
            item.setText(f"Node {row + 1}: {root[:42]}")

    def refresh_card_table(self) -> None:
        row = self.current_row
        node = self.nodes[row] if 0 <= row < len(self.nodes) else {}
        root_size = int(node.get("root_font_size") or 20)
        region_color = safe_color(node.get("picture_region_color"), DEFAULT_PICTURE_REGION_COLOR).upper()
        ship_label = next((label.split("|", 1)[-1].strip() for label, key in SHIP_TYPES if key == normalize_ship_type(node.get("ship_type"))), "Auto")
        status = [
            f"Required | {root_size}px | {ship_label}" if clean_text(node.get("root")) else "Missing text",
            f"Enabled | region {region_color}" if node.get("picture_enabled") and (clean_text(node.get("picture_path")) or clean_text(node.get("picture_asset_url"))) else f"Off | region {region_color}",
            "Enabled" if node.get("audio_enabled") and clean_text(node.get("audio_text")) else "Off",
            f"{len(node.get('questions') or [])} questions" if node.get("questions_enabled") else "Off",
        ]
        for index, value in enumerate(status):
            self.card_table.setItem(index, 1, QTableWidgetItem(value))
        self.question_summary.setText(f"{len(node.get('questions') or [])} questions")

    def ensure_question_id(self, question: dict, index: int) -> str:
        question_id = clean_text(question.get("id") or question.get("i"))
        if not question_id:
            raw = f"{self.current_row}:{index}:{clean_text(question.get('question'))}:{clean_text(question.get('answer'))}".encode("utf-8")
            question_id = "q-" + hashlib.sha1(raw).hexdigest()[:10]
            question["id"] = question_id
        return question_id

    def make_picture_question_anchor_combo(self, selected: str = "highlight") -> QComboBox:
        combo = QComboBox()
        selected_key = safe_picture_question_anchor(selected)
        for label, key in PICTURE_QUESTION_ANCHORS:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def make_picture_question_placement_combo(self, selected: str = "auto") -> QComboBox:
        combo = QComboBox()
        selected_key = safe_picture_question_placement(selected)
        for label, key in PICTURE_QUESTION_PLACEMENTS:
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(selected_key)))
        return combo

    def picture_source_path(self) -> Path | None:
        row = self.current_row
        node = self.nodes[row] if 0 <= row < len(self.nodes) else {}
        raw_path = clean_text(node.get("picture_path"))
        if raw_path.startswith("[embedded]"):
            raw_path = clean_text(raw_path.replace("[embedded]", "", 1))
        candidates: list[Path] = []
        if raw_path:
            candidates.append(Path(raw_path))
        asset_url = clean_text(node.get("picture_asset_url")) or raw_path
        if asset_url and not re.match(r"^[a-z]+://", asset_url, re.I):
            candidates.append(SERVER_DATA_ROOT / asset_url.replace("\\", "/").lstrip("/"))
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate
            except Exception:
                continue
        return None

    def edit_picture_question_region_settings(
        self,
        regions: list[dict] | None = None,
        color: object | None = None,
    ) -> tuple[list[dict], str] | None:
        image_path = self.picture_source_path()
        if not image_path:
            QMessageBox.information(
                self,
                APP_TITLE,
                "No local picture file is available for this node. Choose or load the Picture card image first.",
            )
            return None
        row = self.current_row
        node = self.nodes[row] if 0 <= row < len(self.nodes) else {}
        default_color = safe_color(node.get("picture_region_color") if isinstance(node, dict) else "", DEFAULT_PICTURE_REGION_COLOR)
        dialog = PictureRegionDialog(
            image_path,
            normalize_picture_question_regions(regions or []),
            safe_color(color or default_color, DEFAULT_PICTURE_REGION_COLOR),
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return None
        return dialog.regions(), dialog.region_color()

    def edit_picture_question_regions(self, regions: list[dict] | None = None) -> list[dict] | None:
        result = self.edit_picture_question_region_settings(regions)
        return result[0] if result else None

    def update_region_button(self, button: QPushButton, regions: list[dict] | None, color: object | None = None) -> None:
        row = self.current_row
        node = self.nodes[row] if 0 <= row < len(self.nodes) else {}
        default_color = safe_color(node.get("picture_region_color") if isinstance(node, dict) else "", DEFAULT_PICTURE_REGION_COLOR)
        suffix = f" | {safe_color(color, default_color).upper()}" if color else ""
        button.setText(f"Picture regions: {len(normalize_picture_question_regions(regions or []))}{suffix}")
        button.setToolTip("Open the embedded picture and select target regions.")

    def show_root_context_menu(self, pos) -> None:
        menu = self.root_text.createStandardContextMenu(pos)
        menu.addSeparator()
        action = menu.addAction("Add selection to question...")
        cursor = self.root_text.textCursor()
        row = self.current_row
        has_node = 0 <= row < len(self.nodes)
        has_questions = 0 <= row < len(self.nodes) and bool(self.nodes[row].get("questions"))
        action.setEnabled(cursor.hasSelection() and has_questions)
        action.triggered.connect(self.add_root_selection_to_question)
        create_from_selection = menu.addAction("Create new question from selection...")
        create_from_selection.setEnabled(has_node and cursor.hasSelection())
        create_from_selection.triggered.connect(lambda _checked=False: self.create_question_from_root_context(True))
        create_blank = menu.addAction("Create new question...")
        create_blank.setEnabled(has_node)
        create_blank.triggered.connect(lambda _checked=False: self.create_question_from_root_context(False))
        menu.exec_(self.root_text.mapToGlobal(pos))

    def root_selection_payload(self) -> dict:
        cursor = self.root_text.textCursor()
        if not cursor.hasSelection():
            return {}
        start = min(cursor.position(), cursor.anchor())
        end = max(cursor.position(), cursor.anchor())
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        if not selected_text:
            return {}
        return {
            "start": start,
            "end": end,
            "text": selected_text,
            "color": "#ffff00",
            "style": "style-2",
            "render": "block",
            "info": "",
        }

    def create_question_from_root_context(self, use_selection: bool = True) -> None:
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        highlight = self.root_selection_payload() if use_selection else {}
        if use_selection and not highlight:
            return
        selected_text = clean_multiline_text(highlight.get("text")) if highlight else ""
        short_text = re.sub(r"\s+", " ", selected_text).strip()
        if len(short_text) > 80:
            short_text = short_text[:77].rstrip() + "..."
        question_text = f"Question for: {short_text}" if short_text else "New question"
        answer_text = selected_text or "Correct answer"
        new_question = {
            "type": "choice",
            "card_mode": "linking" if highlight else "question",
            "question": question_text,
            "answer": answer_text,
            "wrong": ["", "", ""],
        }
        if highlight:
            new_question["root_highlights"] = [highlight]
        self.question_check.setChecked(True)
        self.edit_questions(initial_question=new_question, open_settings=False)

    def add_root_selection_to_question(self) -> None:
        cursor = self.root_text.textCursor()
        if not cursor.hasSelection():
            return
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        self.save_current_node()
        node = self.nodes[row]
        questions = node.get("questions") if isinstance(node.get("questions"), list) else []
        if not questions:
            QMessageBox.information(self, APP_TITLE, "Node này chưa có câu hỏi để gắn highlight.")
            return
        start = min(cursor.position(), cursor.anchor())
        end = max(cursor.position(), cursor.anchor())
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        dialog = QDialog(self)
        dialog.setWindowTitle("Add selection to question")
        dialog.resize(820, 680)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("Chọn câu hỏi sẽ kích hoạt đoạn Root text đang bôi đen.")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        preview = QPlainTextEdit()
        preview.setPlainText(selected_text)
        preview.setReadOnly(True)
        preview.setMaximumHeight(100)
        layout.addWidget(preview)
        question_list = QListWidget()
        for index, question in enumerate(questions):
            question_id = self.ensure_question_id(question, index)
            item = QListWidgetItem(f"{index + 1}. {clean_text(question.get('question'))[:120]}")
            item.setData(Qt.UserRole, question_id)
            question_list.addItem(item)
        question_list.setCurrentRow(0)
        layout.addWidget(question_list, 1)
        selected_color = {"value": "#ffff00"}
        options = QGridLayout()
        layout.addLayout(options)
        options.addWidget(QLabel("Highlight style"), 0, 0)
        style_combo = QComboBox()
        for label, key in HIGHLIGHT_STYLES:
            style_combo.addItem(label, key)
        style_combo.setCurrentIndex(max(0, style_combo.findData("style-2")))
        options.addWidget(style_combo, 0, 1)
        options.addWidget(QLabel("Render mode"), 1, 0)
        render_combo = QComboBox()
        for label, key in HIGHLIGHT_RENDER_MODES:
            render_combo.addItem(label, key)
        render_combo.setCurrentIndex(max(0, render_combo.findData("block")))
        options.addWidget(render_combo, 1, 1)
        pan_check = QCheckBox("Kéo màn hình sang highlight/region trước khi chạy hiệu ứng")
        pan_check.setToolTip("Mặc định tắt. Tick nếu muốn người học nhìn đoạn được tô hoặc vùng ảnh trước, rồi quay lại card hỏi.")
        options.addWidget(QLabel("Camera focus"), 2, 0)
        options.addWidget(pan_check, 2, 1)
        options.addWidget(QLabel("Info card text"), 3, 0)
        info_edit = QPlainTextEdit()
        info_edit.setPlaceholderText("Text shown in the future info card when learner points to this highlight.")
        info_edit.setMinimumHeight(90)
        options.addWidget(info_edit, 3, 1)
        options.addWidget(QLabel("Linking question card"), 4, 0)
        picture_question_edit = QPlainTextEdit()
        picture_question_edit.setPlaceholderText("Optional Linking question anchored to this selection or the picture card.")
        picture_question_edit.setMinimumHeight(92)
        options.addWidget(picture_question_edit, 4, 1)
        options.addWidget(QLabel("Bubble anchor"), 5, 0)
        picture_anchor_combo = self.make_picture_question_anchor_combo("highlight")
        options.addWidget(picture_anchor_combo, 5, 1)
        options.addWidget(QLabel("Bubble placement"), 6, 0)
        picture_placement_combo = self.make_picture_question_placement_combo("auto")
        options.addWidget(picture_placement_combo, 6, 1)
        picture_regions: list[dict] = []
        picture_region_color = {"value": safe_color(node.get("picture_region_color"), DEFAULT_PICTURE_REGION_COLOR)}
        picture_region_button = QPushButton("Picture regions: 0")
        options.addWidget(QLabel("Picture regions"), 7, 0)
        options.addWidget(picture_region_button, 7, 1)
        buttons = QHBoxLayout()
        color_button = QPushButton("Choose color")
        add_button = QPushButton("Add highlight")
        cancel = QPushButton("Cancel")
        buttons.addWidget(color_button)
        buttons.addStretch(1)
        buttons.addWidget(add_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        def update_color_button() -> None:
            color = safe_color(selected_color["value"])
            color_button.setStyleSheet(f"background: {color}; color: #061112; font-weight: 900; border-radius: 10px; padding: 9px;")

        def choose_color() -> None:
            color = QColorDialog.getColor(QColor(safe_color(selected_color["value"])), dialog, "Choose highlight color")
            if color.isValid():
                selected_color["value"] = color.name()
                update_color_button()

        update_color_button()
        color_button.clicked.connect(choose_color)

        def choose_picture_regions() -> None:
            selected = self.edit_picture_question_region_settings(picture_regions, picture_region_color["value"])
            if selected is None:
                return
            selected_regions, selected_color = selected
            picture_regions[:] = selected_regions
            picture_region_color["value"] = selected_color
            if picture_regions:
                index = picture_anchor_combo.findData("picture_regions")
                if index >= 0:
                    picture_anchor_combo.setCurrentIndex(index)
            self.update_region_button(picture_region_button, picture_regions, picture_region_color["value"])

        picture_region_button.clicked.connect(choose_picture_regions)
        add_button.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        if dialog.exec_() != QDialog.Accepted:
            return
        item = question_list.currentItem()
        if not item:
            return
        target_id = clean_text(item.data(Qt.UserRole))
        for question in questions:
            if clean_text(question.get("id")) == target_id:
                question.setdefault("root_highlights", [])
                if not isinstance(question["root_highlights"], list):
                    question["root_highlights"] = []
                item_payload = {
                    "start": start,
                    "end": end,
                    "text": selected_text,
                    "color": safe_color(selected_color["value"]),
                    "style": clean_text(style_combo.currentData()) or "style-1",
                    "render": safe_highlight_render(render_combo.currentData()),
                    "info": clean_multiline_text(info_edit.toPlainText()),
                }
                if pan_check.isChecked():
                    item_payload["camera_focus"] = True
                base_question_text = clean_text(question.get("question"))
                typed_picture_question_text = clean_multiline_text(picture_question_edit.toPlainText())
                picture_question_text = typed_picture_question_text or base_question_text
                if typed_picture_question_text:
                    question["question"] = typed_picture_question_text
                if picture_question_text and (typed_picture_question_text or picture_regions):
                    item_payload["picture_question"] = {
                        "text": picture_question_text,
                        "anchor": "picture_regions" if picture_regions else safe_picture_question_anchor(picture_anchor_combo.currentData()),
                        "placement": safe_picture_question_placement(picture_placement_combo.currentData()),
                    }
                    if picture_regions:
                        item_payload["picture_question"]["regions"] = normalize_picture_question_regions(picture_regions)
                        item_payload["picture_question"]["region_color"] = safe_color(picture_region_color["value"], safe_color(node.get("picture_region_color"), DEFAULT_PICTURE_REGION_COLOR))
                question["root_highlights"].append(item_payload)
                break
        self.question_check.setChecked(True)
        self.save_current_node()
        self.save_builder_state()
        self.refresh_card_table()

    def add_or_update_selected_card(self) -> None:
        row = self.card_table.currentRow()
        if row == 1:
            self.picture_check.setChecked(True)
            self.choose_picture()
        elif row == 2:
            self.audio_check.setChecked(True)
        elif row == 3:
            self.question_check.setChecked(True)
            self.edit_questions()
        self.save_current_node()
        self.refresh_card_table()

    def remove_selected_card(self) -> None:
        row = self.card_table.currentRow()
        if row == 1:
            self.picture_check.setChecked(False)
        elif row == 2:
            self.audio_check.setChecked(False)
        elif row == 3:
            self.question_check.setChecked(False)
        self.save_current_node()
        self.refresh_card_table()

    def choose_picture(self) -> None:
        start = clean_text(self.settings.get("last_picture_folder")) or str(Path.cwd())
        path, _filter = QFileDialog.getOpenFileName(self, "Chọn ảnh cho Picture card", start, "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg *.bmp);;All files (*.*)")
        if not path:
            return
        self.settings["last_picture_folder"] = str(Path(path).parent)
        save_settings(self.settings)
        self.picture_path.setText(path)
        row = self.current_row
        if 0 <= row < len(self.nodes):
            self.nodes[row]["picture_asset_url"] = ""
            self.nodes[row]["picture_asset_name"] = ""
        if not self.picture_caption.text().strip():
            self.picture_caption.setText(Path(path).stem)
        self.picture_check.setChecked(True)
        self.save_current_node()
        self.refresh_card_table()

    def edit_questions(self, initial_question=None, open_settings: bool = False) -> None:
        row = self.current_row
        if row < 0 or row >= len(self.nodes):
            return
        self.save_current_node()
        questions = list(self.nodes[row].get("questions") or [])
        initial_row = -1
        if isinstance(initial_question, dict):
            questions.append(initial_question)
            initial_row = len(questions) - 1
        dialog = QuestionDialog(
            questions,
            self.settings,
            self.voices,
            self,
            initial_row=initial_row,
            open_settings=bool(open_settings and initial_row >= 0),
        )
        if dialog.exec_() == QDialog.Accepted:
            self.nodes[row]["questions"] = dialog.questions()
            self.nodes[row]["questions_enabled"] = bool(self.nodes[row]["questions"])
            self.question_check.setChecked(bool(self.nodes[row]["questions"]))
            self.save_builder_state()
            self.load_current_node()

    def load_space_q(self) -> None:
        self.save_current_node()
        start = clean_text(self.settings.get("last_space_q_folder") or self.settings.get("last_output_folder")) or str(Path.cwd())
        path, _filter = QFileDialog.getOpenFileName(self, "Load Space_Q", start, "Future Question (*.Space_Q);;JSON / FTG files (*.json *.txt *.Space_Q);;All files (*.*)")
        if not path:
            return
        try:
            payload = decode_space_q_payload(Path(path))
            nodes = nodes_from_space_q_payload(payload)
            if not nodes:
                raise RuntimeError("Không tìm thấy node Root hợp lệ trong Space_Q.")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Không load được Space_Q:\n{exc}")
            return
        self.settings["last_space_q_folder"] = str(Path(path).parent)
        self.settings["last_output_folder"] = str(Path(path).parent)
        title = clean_text(payload.get("title") or payload.get("t")) or Path(path).stem
        order = "shuffle" if clean_text(payload.get("order") or payload.get("o")).lower() == "shuffle" else "sequence"
        rewards = normalize_reward_config(payload.get("rewards") or payload.get("reward") or payload.get("rw"))
        self.title_input.setText(title)
        self.order_combo.setCurrentIndex(1 if order == "shuffle" else 0)
        self.crystal_name_input.setText(clean_text(rewards.get("crystal", {}).get("name")) or DEFAULT_CRYSTAL_NAME)
        self.crystal_use_input.setPlainText(clean_multiline_text(rewards.get("crystal", {}).get("use")) or DEFAULT_CRYSTAL_USE)
        self.loading_node = True
        try:
            self.nodes = nodes
            self.node_list.clear()
            for index, node in enumerate(self.nodes, 1):
                self.ensure_voice_choice(clean_text(node.get("audio_voice")), clean_text(node.get("audio_asset_voice_label")))
                root = clean_text(node.get("root")) or "Untitled root"
                self.node_list.addItem(QListWidgetItem(f"Node {index}: {root[:42]}"))
            self.current_row = 0
            self.node_list.setCurrentRow(0)
        finally:
            self.loading_node = False
        self.load_current_node()
        self.save_builder_state()
        self.log_box.clear()
        self.log(f"Loaded Space_Q: {path}")
        self.log(f"Nodes: {len(self.nodes)}")

    def valid_nodes(self) -> list[dict]:
        self.save_current_node()
        return [dict(node) for node in self.nodes if clean_text(node.get("root"))]

    def safe_output_name(self) -> str:
        title = clean_text(self.title_input.text()) or "Future Question"
        return f"{safe_unicode_filename_stem(title, 'Future Question')}{QUESTION_EXTENSION}"

    def set_build_busy(self, busy: bool) -> None:
        self.generate_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.load_space_q_button.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)

    def start_build_worker(self, nodes: list[dict], path: Path, mode: str, direct_payload: bool = False) -> None:
        self.worker_mode = mode
        self.save_builder_state()
        self.set_build_busy(True)
        self.log_box.clear()
        self.worker = BuildQuestionWorker(
            nodes,
            self.title_input.text(),
            clean_text(self.order_combo.currentData()),
            path,
            direct_payload=direct_payload,
            reward_config=self.current_reward_config(),
        )
        self.worker.log_message.connect(self.log)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.start()

    def generate(self) -> None:
        nodes = self.valid_nodes()
        if not nodes:
            QMessageBox.warning(self, APP_TITLE, "Hãy tạo ít nhất một node có Root text.")
            return
        output_start = clean_text(self.settings.get("last_output_folder")) or str(Path.cwd())
        output_path, _filter = QFileDialog.getSaveFileName(self, "Lưu Space_Q", str(Path(output_start) / self.safe_output_name()), "Future Question (*.Space_Q)")
        if not output_path:
            return
        path = Path(output_path)
        if not path.suffix:
            path = path.with_suffix(QUESTION_EXTENSION)
        self.settings["last_output_folder"] = str(path.parent)
        self.start_build_worker(nodes, path, "build", direct_payload=False)

    def run_preview(self) -> None:
        nodes = self.valid_nodes()
        if not nodes:
            QMessageBox.warning(self, APP_TITLE, "HÃ£y táº¡o Ã­t nháº¥t má»™t node cÃ³ Root text.")
            return
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        path = PREVIEW_DIR / f"{safe_segment(self.title_input.text(), 'Future_Question', 42)}-preview{QUESTION_EXTENSION}"
        self.start_build_worker(nodes, path, "preview", direct_payload=True)

    def open_preview_html(self, space_q_path: Path) -> None:
        if not FUTURE_HTML_PATH.is_file():
            raise RuntimeError(f"KhÃ´ng tÃ¬m tháº¥y future.html: {FUTURE_HTML_PATH}")
        raw_code = space_q_path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw_code:
            raise RuntimeError("File preview Space_Q Ä‘ang rá»—ng.")
        source_html = FUTURE_HTML_PATH.read_text(encoding="utf-8-sig", errors="replace")
        preview_script = (
            '<script id="ft-preview-code">'
            f"window.__FTG_PREVIEW_CODE__={json.dumps(raw_code, ensure_ascii=False)};"
            "window.__FTG_PREVIEW_MODE__=true;"
            "window.__FTG_PREVIEW_DEBUG__=true;"
            "</script>"
        )
        if "<script>" not in source_html:
            raise RuntimeError("future.html khÃ´ng cÃ³ script runtime Ä‘á»ƒ nhÃºng preview.")
        preview_html = source_html.replace("<script>", f"{preview_script}\n<script>", 1)
        preview_path = PREVIEW_DIR / "future_question_preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(preview_path))):
            raise RuntimeError(f"KhÃ´ng má»Ÿ Ä‘Æ°á»£c preview HTML: {preview_path}")
        self.log(f"Preview HTML: {preview_path}")

    def on_failed(self, message: str) -> None:
        self.set_build_busy(False)
        self.progress.setValue(0)
        self.worker_mode = ""
        QMessageBox.critical(self, APP_TITLE, message)

    def on_finished(self, path: str, count: int) -> None:
        mode = self.worker_mode
        self.set_build_busy(False)
        self.progress.setValue(1)
        self.log(f"Done: {path}")
        self.worker_mode = ""
        if mode == "preview":
            try:
                self.open_preview_html(Path(path))
                self.log(f"Run test Space_Q nodes: {count}")
            except Exception as exc:
                QMessageBox.critical(self, APP_TITLE, f"Build preview xong nhÆ°ng khÃ´ng má»Ÿ Ä‘Æ°á»£c HTML:\n{exc}")
            return
        QMessageBox.information(self, APP_TITLE, f"Đã build {count} node Space_Q.\n{path}")

    def closeEvent(self, event) -> None:
        self.save_builder_state()
        super().closeEvent(event)


if __name__ == "__main__":
    if "--pyqt5" not in sys.argv:
        from future_question_builder_web import launch_web_builder
        launch_web_builder()
    else:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = FutureQuestionBuilder()
        window.show()
        sys.exit(app.exec_())
