from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import wave
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from PyQt5.QtCore import QThread, Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCursor, QTextCharFormat
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from future_lesson_identity import apply_lesson_id_to_payload, ensure_future_lesson_id, lesson_id_from_payload
from future_sound_asset_index import (
    sound_asset_extension_from_mime,
    write_server_sound_asset as indexed_write_server_sound_asset,
    write_server_sound_file_asset as indexed_write_server_sound_file_asset,
)
from future_postgres_structure_asset_store import (
    structure_asset_exists,
    structure_asset_json,
    write_structure_asset_bytes,
)

try:
    from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
except Exception:
    QMediaContent = None
    QMediaPlayer = None

try:
    import winsound
except Exception:
    winsound = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APP_TITLE = "Future Lesson Builder"
CODE_PREFIX = "FTG1."
LESSON_EXTENSION = ".Space_W"
SERVER_DATA_ROOT = Path(r"C:\server data")
SERVER_SOUND_DIR = SERVER_DATA_ROOT / "Sound"
SERVER_STRUCTURE_DIR = SERVER_DATA_ROOT / "Structure"
SERVER_PICTURE_DIR = SERVER_DATA_ROOT / "Picture"
CACHE_ROOT = Path(r"C:\programe\programe_cache\future_lesson_builder")
TTS_CACHE_DIR = CACHE_ROOT / "tts"
LOCAL_TTS_OUTPUT_DIR = CACHE_ROOT / "local_tts_outputs"
VOICE_SAMPLE_DIR = CACHE_ROOT / "voice_samples"
VOICE_SAMPLE_TEXT = "I would like a glass of water."
IPA_CACHE_PATH = CACHE_ROOT / "ipa_cache.json"
IPA_CACHE_LOCK = threading.RLock()
IPA_CACHE_RAM: dict[str, str] | None = None
IPA_CACHE_DIRTY_COUNT = 0
BUILDER_SETTINGS_PATH = CACHE_ROOT / "builder_settings.json"


# Added 2026-07-07: lets builder audio calls feed several Server 2 worker lanes while keeping memory bounded.
def builder_audio_parallel_workers(task_count: int) -> int:
    raw = os.environ.get("FUTURE_BUILDER_AUDIO_PARALLEL", "")
    try:
        amount = int(float(raw)) if raw else 4
    except Exception:
        amount = 4
    return max(1, min(16, task_count, amount))


WRITE_HTML_DIR = Path(__file__).resolve().parent
EFFECT_SOUND_FILES = {
    "open": WRITE_HTML_DIR / "open pop up.mp3",
    "true": WRITE_HTML_DIR / "true.mp3",
    "false": WRITE_HTML_DIR / "False.mp3",
}
COMMUNICATION_BASE_VOICES = [
    ("Sound of Text | Female UK", "sot:en-GB"),
    ("Sound of Text | Female US", "sot:en-US"),
    ("People | Male US", "male-us"),
]
TRAIN_MODE_PRIMARY_VOICE = "kokoro:am_adam"
TRAIN_MODE_VIETNAMESE_VOICE = "edge:vi-VN-NamMinhNeural"
TRAIN_MODE_ENGLISH_VOICES = [
    ("People | Male Adam", "kokoro:am_adam"),
    ("People | Female Jessica", "kokoro:af_jessica"),
]
VIBEVOICE_BUILDER_ENABLED = False
VIBEVOICE_DISABLED_MESSAGE = "VibeVoice is disabled in Future builders. Choose People, Sound of Text, Edge, or Microsoft voice."
_VIBEVOICE_RUNTIME = None
_KOKORO_RUNTIME = None
_KOKORO_VI_ONNX_RUNTIMES: dict[str, object] = {}
_KOKORO_VI_ONNX_RUNTIME_LOCK = threading.RLock()
_KOKORO_VI_ONNX_RUNTIME_LOAD_LOCKS: dict[str, threading.Lock] = {}
_TTS_SYNTH_LOCK = threading.RLock()
_TTS_SYNTH_LOCKS: dict[str, threading.Lock] = {}
BUILDER_SERVER2_DEFAULT_URL = "http://127.0.0.1:8877"
KOKORO_VI_MODEL_ROOT = Path(r"C:\QMLearn\models\kokoro_vietnamese")
KOKORO_VI_ONNX_PATH = KOKORO_VI_MODEL_ROOT / "kokoro_vi.onnx"
KOKORO_VI_CONFIG_PATH = KOKORO_VI_MODEL_ROOT / "config.json"
KOKORO_VI_DEFAULT_VOICEPACK = KOKORO_VI_MODEL_ROOT / "kokoro_vi_voicepack.pt"
KOKORO_VI_VOICEPACK_DIR = KOKORO_VI_MODEL_ROOT / "voicepacks"
KOKORO_VI_FALLBACK_VOICES = [
    ("Kokoro VI | Diem Trinh", "kokoro_vi:diem_trinh"),
    ("Kokoro VI | Hung Thinh", "kokoro_vi:hung_thinh"),
    ("Kokoro VI | Mai Linh", "kokoro_vi:mai_linh"),
    ("Kokoro VI | Mai Loan", "kokoro_vi:mai_loan"),
    ("Kokoro VI | Manh Dung", "kokoro_vi:manh_dung"),
    ("Kokoro VI | My Yen", "kokoro_vi:my_yen"),
    ("Kokoro VI | Ngoc Huyen", "kokoro_vi:ngoc_huyen"),
    ("Kokoro VI | Phat Tai", "kokoro_vi:phat_tai"),
    ("Kokoro VI | Thanh Dat", "kokoro_vi:thanh_dat"),
    ("Kokoro VI | Thuc Trinh", "kokoro_vi:thuc_trinh"),
    ("Kokoro VI | Tuan Ngoc", "kokoro_vi:tuan_ngoc"),
    ("Kokoro VI | Duc An", "kokoro_vi:duc_an"),
    ("Kokoro VI | Duc Duy", "kokoro_vi:duc_duy"),
    ("Kokoro VI | Storyvert", "kokoro_vi:storyvert"),
]


def _kokoro_voice_gender(voice_name: str) -> str:
    prefix = str(voice_name or "").strip().lower().split("_", 1)[0]
    if prefix.endswith("f"):
        return "female"
    if prefix.endswith("m"):
        return "male"
    return ""


def _kokoro_voice_label(voice_name: str) -> str:
    raw = str(voice_name or "").strip()
    if not raw:
        return "People | Kokoro"
    suffix = raw.split("_", 1)[1] if "_" in raw else raw
    pretty = re.sub(r"[_-]+", " ", suffix).strip().title() or raw
    gender = _kokoro_voice_gender(raw)
    if gender == "female":
        return f"People | Female {pretty}"
    if gender == "male":
        return f"People | Male {pretty}"
    return f"People | {pretty}"


def _kokoro_vietnamese_voice_label(voice_name: str) -> str:
    raw = str(voice_name or "").strip()
    if not raw:
        return "Kokoro VI | Vietnamese"
    pretty = re.sub(r"[_-]+", " ", raw).strip().title() or raw
    return f"Kokoro VI | {pretty}"


def _vibevoice_voice_label(voice_name: str) -> str:
    raw = str(voice_name or "").strip()
    pretty = re.sub(r"[_-]+", " ", raw).strip().title() or "Voice"
    return f"VibeVoice | {pretty}"


def _append_voice_option(options: list[tuple[str, str]], seen: set[str], label: str, key: str) -> None:
    clean_key = clean_text(key)
    if not clean_key:
        return
    lowered = clean_key.lower()
    if lowered in seen:
        return
    seen.add(lowered)
    options.append((clean_text(label) or embedded_voice_label(clean_key), clean_key))


def sound_of_text_voice_specs() -> list[tuple[str, str]]:
    return [
        (label, key)
        for label, key in COMMUNICATION_BASE_VOICES
        if str(label or "").lower().startswith("sound of text") or str(key or "").lower().startswith("sot:")
    ]


def edge_english_voice_specs(force_refresh: bool = False) -> list[tuple[str, str]]:
    try:
        from module_main.edge_tts_service import edge_voice_options

        return list(edge_voice_options(force_refresh=bool(force_refresh), languages=("en",)) or [])
    except Exception:
        try:
            from module_main.edge_tts_service import _DEFAULT_VOICES, edge_voice_option_label

            options: list[tuple[str, str]] = []
            for info in list(_DEFAULT_VOICES or []):
                locale = str(getattr(info, "locale", "") or "")
                if not locale.lower().startswith("en"):
                    continue
                short_name = str(getattr(info, "short_name", "") or "").strip()
                if short_name:
                    options.append((edge_voice_option_label(short_name), f"edge:{short_name}"))
            return options
        except Exception:
            return []


def edge_vietnamese_voice_specs(force_refresh: bool = False) -> list[tuple[str, str]]:
    try:
        from module_main.edge_tts_service import edge_voice_options

        options = list(edge_voice_options(force_refresh=bool(force_refresh), languages=("vi",)) or [])
        if options:
            return options
    except Exception:
        pass
    return [
        ("Edge | Vietnamese VN | Hoai My", "edge:vi-VN-HoaiMyNeural"),
        ("Edge | Vietnamese VN | Nam Minh", "edge:vi-VN-NamMinhNeural"),
    ]


# Added 2026-07-03: exposes local Kokoro Vietnamese voicepacks to PDF/notice voice pickers.
def kokoro_vietnamese_voice_specs() -> list[tuple[str, str]]:
    voice_rows: list[tuple[str, str]] = []
    voices_path = KOKORO_VI_MODEL_ROOT / "voices.json"
    if voices_path.is_file():
        try:
            data = json.loads(voices_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for name, info in data.items():
                    voice_name = clean_text(name)
                    if not voice_name:
                        continue
                    label = ""
                    if isinstance(info, dict):
                        label = clean_text(info.get("label", ""))
                    voice_rows.append((label or _kokoro_vietnamese_voice_label(voice_name), f"kokoro_vi:{voice_name}"))
        except Exception:
            voice_rows = []
    if not voice_rows:
        voice_rows = list(KOKORO_VI_FALLBACK_VOICES)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, key in voice_rows:
        clean_key = clean_text(key)
        lowered = clean_key.lower()
        if not clean_key or lowered in seen:
            continue
        seen.add(lowered)
        out.append((clean_text(label) or embedded_voice_label(clean_key), clean_key))
    return out


# Added 2026-07-10: prepares Kokoro VI model files on disk without loading the ONNX model into RAM.
def ensure_kokoro_vietnamese_model_files(download: bool = True, log=None) -> dict:
    KOKORO_VI_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    KOKORO_VI_VOICEPACK_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        ("kokoro_vi.onnx", KOKORO_VI_ONNX_PATH),
        ("config.json", KOKORO_VI_CONFIG_PATH),
        ("kokoro_vi_voicepack.pt", KOKORO_VI_DEFAULT_VOICEPACK),
    ]
    voices = {}
    try:
        from kokoro_vietnamese.core import DEFAULT_HF_REPO_ID, VOICES, _download_or_resolve  # type: ignore

        voices = dict(VOICES or {})
    except Exception:
        DEFAULT_HF_REPO_ID = "contextboxai/Kokoro-Vietnamese"
        _download_or_resolve = None
    for _voice_name, info in voices.items():
        filename = clean_text(info.get("filename", "")) if isinstance(info, dict) else ""
        if filename:
            required.append((filename, KOKORO_VI_MODEL_ROOT / filename))
    downloaded = []
    missing = []
    for remote_name, target in required:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.stat().st_size > 44:
                continue
            if not download or _download_or_resolve is None:
                missing.append(str(target))
                continue
            source = Path(_download_or_resolve(DEFAULT_HF_REPO_ID, remote_name, None))
            if source.is_file():
                target.write_bytes(source.read_bytes())
                downloaded.append(str(target))
            else:
                missing.append(str(target))
        except Exception as exc:
            missing.append(f"{target}: {exc}")
    voices_json = KOKORO_VI_MODEL_ROOT / "voices.json"
    if voices and not voices_json.is_file():
        try:
            voices_json.write_text(json.dumps(voices, ensure_ascii=False, indent=2), encoding="utf-8")
            downloaded.append(str(voices_json))
        except Exception as exc:
            missing.append(f"{voices_json}: {exc}")
    if callable(log):
        log(f"Kokoro VI files ready: downloaded={len(downloaded)} missing={len(missing)}")
    # Added 2026-07-11: expose per-file readiness so distributed workers do not misreport existing models as missing.
    return {
        "root": str(KOKORO_VI_MODEL_ROOT),
        "onnx": KOKORO_VI_ONNX_PATH.is_file() and KOKORO_VI_ONNX_PATH.stat().st_size > 44,
        "config": KOKORO_VI_CONFIG_PATH.is_file() and KOKORO_VI_CONFIG_PATH.stat().st_size > 44,
        "default_voicepack": KOKORO_VI_DEFAULT_VOICEPACK.is_file() and KOKORO_VI_DEFAULT_VOICEPACK.stat().st_size > 44,
        "voicepack_dir": str(KOKORO_VI_VOICEPACK_DIR),
        "downloaded": downloaded,
        "missing": missing,
        "ready": not missing,
    }

def grammar_vietnamese_voice_specs() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = [("Sound of Text | Vietnamese", "sot:vi-VN")]
    seen = {"sot:vi-vn"}
    for label, key in list(edge_vietnamese_voice_specs(force_refresh=False)) + list(kokoro_vietnamese_voice_specs()):
        lowered = clean_text(key).lower()
        if lowered and lowered not in seen:
            seen.add(lowered)
            options.append((label, key))
    return options


def train_mode_english_voice_specs() -> list[tuple[str, str]]:
    return list(TRAIN_MODE_ENGLISH_VOICES)


def train_mode_vietnamese_voice_specs() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = [("Edge | Vietnamese VN | Nam Minh", TRAIN_MODE_VIETNAMESE_VOICE)]
    seen = {TRAIN_MODE_VIETNAMESE_VOICE.lower()}
    for label, key in grammar_vietnamese_voice_specs():
        lowered = clean_text(key).lower()
        if lowered and lowered not in seen:
            seen.add(lowered)
            options.append((label, key))
    return options


def default_train_mode_embedded_voices() -> list[dict]:
    return [
        {"label": label, "key": normalize_audio_voice_key(key) or key}
        for label, key in train_mode_english_voice_specs()
    ]


def _is_english_sapi_voice(voice: object) -> bool:
    fields = [
        getattr(voice, "name", ""),
        getattr(voice, "id", ""),
        " ".join(str(item) for item in list(getattr(voice, "languages", []) or [])),
    ]
    haystack = " ".join(str(item or "") for item in fields).lower()
    return any(marker in haystack for marker in ("english", "en-us", "en_us", "en-gb", "en_gb", "\\en", "_en"))


def _microsoft_voice_label(name: str) -> str:
    pretty = clean_text(name)
    pretty = re.sub(r"^microsoft\s+", "", pretty, flags=re.IGNORECASE).strip()
    pretty = re.sub(r"\s*-\s*English\s*\([^)]*\)\s*$", "", pretty, flags=re.IGNORECASE).strip()
    pretty = re.sub(r"\s+Desktop$", "", pretty, flags=re.IGNORECASE).strip()
    return f"Microsoft | {pretty or 'Voice'}"


def _microsoft_online_label(edge_label: str, voice_key: str = "") -> str:
    label = clean_text(edge_label)
    if label.lower().startswith("edge |"):
        return "Microsoft |" + label.split("|", 1)[1]
    suffix = clean_text(voice_key.split(":", 1)[1] if ":" in voice_key else voice_key)
    pretty = re.sub(r"Neural$", "", suffix.split("-")[-1] if suffix else "Voice", flags=re.IGNORECASE)
    pretty = re.sub(r"([a-z])([A-Z])", r"\1 \2", pretty).strip()
    return f"Microsoft | {pretty or 'Voice'}"


def microsoft_online_voice_specs(force_refresh: bool = False) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    for label, key in edge_english_voice_specs(force_refresh=force_refresh):
        suffix = clean_text(key.split(":", 1)[1] if ":" in key else key)
        if suffix:
            options.append((_microsoft_online_label(label, key), f"microsoft:{suffix}"))
    return options


def microsoft_sapi_voice_specs() -> list[tuple[str, str]]:
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        voices = list(engine.getProperty("voices") or [])
        try:
            engine.stop()
        except Exception:
            pass
    except Exception:
        return []
    options: list[tuple[str, str]] = []
    seen: set[str] = set()
    for voice in voices:
        voice_id = clean_text(getattr(voice, "id", ""))
        if not voice_id or not _is_english_sapi_voice(voice):
            continue
        key = f"sapi:{voice_id}"
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        options.append((_microsoft_voice_label(getattr(voice, "name", "") or voice_id), key))
    return options


def microsoft_voice_specs(force_refresh: bool = False) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, key in microsoft_online_voice_specs(force_refresh=force_refresh) + microsoft_sapi_voice_specs():
        lowered = clean_text(key).lower()
        if not lowered or lowered in seen:
            continue
        seen.add(lowered)
        options.append((label, key))
    return options


def people_voice_specs() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = [("People | Male US", "male-us")]
    seen = {"male-us"}
    voice_names: list[str] = []
    try:
        from module_main.tts_kokoro_local import KokoroLocalTTS

        runtime = KokoroLocalTTS()
        runtime.prefer_subprocess = True
        voice_names = list(runtime.list_voices() or [])
    except Exception:
        voice_names = []
    if not voice_names:
        try:
            from module_main.tts_kokoro_local import KOKORO_FALLBACK_VOICES

            voice_names = list(KOKORO_FALLBACK_VOICES or [])
        except Exception:
            voice_names = []
    for voice_name in voice_names:
        key = f"kokoro:{voice_name}"
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        options.append((_kokoro_voice_label(voice_name), key))
    return options


def communication_voice_options() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, key in sound_of_text_voice_specs():
        _append_voice_option(options, seen, label, key)
    for label, key in people_voice_specs():
        _append_voice_option(options, seen, label, key)

    if VIBEVOICE_BUILDER_ENABLED:
        try:
            from vibevoice_realtime_gui import ENGINE_VIBEVOICE, VIBEVOICE_REPO, VOICE_DIR, resolve_default_model_path, scan_voice_options

            voice_names = list((scan_voice_options() or {}).keys())
            for voice_name in voice_names:
                key = f"vibevoice:{voice_name}"
                _append_voice_option(options, seen, _vibevoice_voice_label(voice_name), key)
            if not voice_names:
                missing = []
                if not os.path.isdir(VIBEVOICE_REPO):
                    missing.append("repo")
                if not os.path.isdir(VOICE_DIR):
                    missing.append("voice .pt")
                model_path = resolve_default_model_path(ENGINE_VIBEVOICE)
                if not os.path.isdir(model_path):
                    missing.append("model")
                reason = " + ".join(missing) if missing else "no voice .pt"
                _append_voice_option(options, seen, f"VibeVoice | missing {reason}", "__missing_vibevoice__")
        except Exception as exc:
            _append_voice_option(options, seen, f"VibeVoice | unavailable ({type(exc).__name__})", "__missing_vibevoice__")

    for label, key in edge_english_voice_specs(force_refresh=False):
        _append_voice_option(options, seen, label, key)
    for label, key in microsoft_voice_specs(force_refresh=False):
        _append_voice_option(options, seen, label, key)

    return options


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_kokoro_tts_text(value: object) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[\r\n\u2028\u2029]+", " ", text)
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", text)
    return clean_text(text)


def clean_log_text(value: object) -> str:
    lines = []
    for line in str(value or "").splitlines():
        text = clean_text(line)
        if text:
            lines.append(text)
    return "\n".join(lines)


def normalize_about_entries(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    entries: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            question = clean_log_text(item.get("q") or item.get("question") or item.get("title") or "")
            answer = clean_log_text(item.get("a") or item.get("answer") or item.get("explanation") or item.get("body") or "")
            highlights = normalize_about_highlights(item.get("ah") or item.get("answer_highlights") or item.get("answerHighlights") or item.get("hl") or item.get("highlights"))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            question = clean_log_text(item[0])
            answer = clean_log_text(item[1])
            highlights = []
        else:
            continue
        if question or answer:
            entry = {"q": question, "a": answer}
            if highlights:
                entry["ah"] = highlights
            entries.append(entry)
    return entries


def normalize_hex_color(value: object, fallback: str = "#ffff00") -> str:
    raw = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw.lower()
    if re.fullmatch(r"[0-9a-fA-F]{6}", raw):
        return f"#{raw.lower()}"
    if re.fullmatch(r"#[0-9a-fA-F]{3}", raw):
        return "#" + "".join(ch * 2 for ch in raw[1:].lower())
    return fallback


def normalize_about_highlights(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    highlights: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        color = normalize_hex_color(item.get("c") or item.get("color") or item.get("colour"))
        text = clean_log_text(item.get("t") or item.get("text") or item.get("segment") or "")
        start_raw = item.get("s", item.get("start"))
        end_raw = item.get("e", item.get("end"))
        try:
            start = int(start_raw)
            end = int(end_raw)
        except Exception:
            start = -1
            end = -1
        try:
            occurrence = max(1, int(item.get("n") or item.get("occurrence") or 1))
        except Exception:
            occurrence = 1
        if text:
            highlights.append({"t": text, "n": occurrence, "c": color})
        elif start >= 0 and end > start:
            highlights.append({"s": start, "e": end, "c": color})
    return highlights


def encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(bytes(data or b"")).decode("ascii").rstrip("=")


def decode_base64url(data: str) -> bytes:
    raw = clean_text(data)
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def encode_future_payload(payload: dict, output_path: str | Path = "", space: str = "") -> str:
    # Updated 2026-07-20: legacy builder call sites also emit SQLite-backed manifests.
    title = clean_text(payload.get("title") or payload.get("t")) or Path(str(output_path or "lesson")).stem
    return encode_future_manifest(payload, title, output_path, space)


def decode_future_lesson_document(text: str) -> dict:
    raw = str(text or "").lstrip("\ufeff").strip()
    if not raw:
        raise ValueError("File Space_W dang rong.")
    if raw.startswith(CODE_PREFIX):
        payload = json.loads(gzip.decompress(decode_base64url(raw[len(CODE_PREFIX):])).decode("utf-8"))
    else:
        payload = json.loads(raw)
    if isinstance(payload, dict) and clean_text(payload.get("k")).lower() == "ftg_manifest":
        structure = clean_text(payload.get("structure") or payload.get("sp") or payload.get("path"))
        if not structure:
            raise ValueError("Manifest Space_W thieu duong dan Structure.")
        if not structure_asset_exists(structure):
            raise FileNotFoundError(f"Khong tim thay Structure trong SQLite: {structure}")
        payload = structure_asset_json(structure)
    if not isinstance(payload, dict):
        raise ValueError("Du lieu Space_W khong hop le.")
    return payload


def ensure_server_asset_dirs() -> None:
    SERVER_SOUND_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_PICTURE_DIR.mkdir(parents=True, exist_ok=True)


def server_asset_name(prefix: str, payload: bytes, extension: str) -> str:
    digest = hashlib.sha1(bytes(payload or b"")).hexdigest()
    safe_prefix = re.sub(r"[^0-9A-Za-z._-]+", "-", clean_text(prefix)).strip("-") or "asset"
    safe_ext = re.sub(r"[^0-9A-Za-z]+", "", clean_text(extension).lstrip(".")) or "bin"
    return f"{safe_prefix}_{digest}.{safe_ext}"


def write_server_sound_asset(prefix: str, audio_bytes: bytes, mime: str) -> str:
    # Added 2026-07-16: share the Server 2 Sound JSON/WAL index so builders never glob the 140k-file flat Sound folder.
    return indexed_write_server_sound_asset(prefix, bytes(audio_bytes or b""), mime)


def write_server_sound_file_asset(prefix: str, payload: bytes, extension: str) -> str:
    # Added 2026-07-16: lets PDF media and builder tools write non-mp3 assets into the same sharded Sound cache.
    return indexed_write_server_sound_file_asset(prefix, bytes(payload or b""), extension or sound_asset_extension_from_mime(""))


def write_server_picture_asset(prefix: str, image_bytes: bytes, extension: str) -> str:
    ensure_server_asset_dirs()
    ext = clean_text(extension).lower().lstrip(".")
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}:
        ext = "png"
    name = server_asset_name(prefix, bytes(image_bytes or b""), ext)
    path = SERVER_PICTURE_DIR / name
    if not path.is_file():
        path.write_bytes(bytes(image_bytes or b""))
    return f"Picture/{name}"


def write_server_structure_asset(title: str, payload: dict) -> str:
    # Added 2026-07-20: every Space builder writes compressed Structure bytes directly to SQLite.
    ensure_server_asset_dirs()
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    name = server_asset_name(title or "lesson", raw, "json")
    logical_path = f"Structure/{name}"
    if not structure_asset_exists(logical_path):
        write_structure_asset_bytes(logical_path, raw)
    return f"Structure/{name}"


def encode_future_manifest(payload: dict, title: str, output_path: str | Path = "", space: str = "") -> str:
    ensure_future_lesson_id(payload, output_path=output_path, space=space)
    lesson_id = lesson_id_from_payload(payload)
    structure_path = write_server_structure_asset(title, payload)
    manifest = {
        "k": "ftg_manifest",
        "v": 2,
        "t": clean_text(title) or clean_text(payload.get("t")) or "Future lesson",
        "structure": structure_path,
        "created": int(time.time()),
    }
    apply_lesson_id_to_payload(manifest, lesson_id)
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def ensure_cache_dirs() -> None:
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_TTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def voice_cache_key(text: str, voice_key: str) -> str:
    raw = json.dumps(
        {"text": clean_text(text), "voice": clean_text(voice_key)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def normalize_sound_of_text_voice_key(voice_key: str) -> str:
    key = clean_text(voice_key).lower()
    if key in {"female-uk", "uk", "en-gb", "sot:en-gb", "soundoftext:en-gb"}:
        return "en-GB"
    if key in {"female-us", "male-us", "us", "en-us", "sot:en-us", "soundoftext:en-us"}:
        return "en-US"
    if key.startswith("sot:"):
        return clean_text(voice_key).split(":", 1)[1] or "en-US"
    return ""


def normalize_audio_voice_key(voice_key: str) -> str:
    key = clean_text(voice_key)
    lowered = key.lower()
    if lowered.startswith(("kokoro-vietnamese:", "kokoro_vietnamese:", "kokoro-vi:")):
        suffix = clean_text(key.split(":", 1)[1] if ":" in key else "")
        return f"kokoro_vi:{suffix}" if suffix else "kokoro_vi:diem_trinh"
    if lowered.startswith(("microsoft:", "msedge:")):
        suffix = clean_text(key.split(":", 1)[1] if ":" in key else "")
        if not suffix:
            return key
        try:
            from module_main.edge_tts_service import edge_voice_info

            info = edge_voice_info(suffix)
            if info is not None:
                suffix = info.short_name
        except Exception:
            pass
        return f"microsoft:{suffix}"
    if lowered == "male-us":
        return "edge:en-US-GuyNeural"
    sot = normalize_sound_of_text_voice_key(key)
    if sot and lowered in {"female-uk", "female-us", "sot:en-gb", "sot:en-us", "uk", "us", "en-gb", "en-us"}:
        return f"sot:{sot}"
    return key


def is_sound_of_text_voice(voice_key: str) -> bool:
    return bool(normalize_sound_of_text_voice_key(voice_key))


def embedded_voice_label(voice_key: str, fallback: str = "") -> str:
    raw_key = clean_text(voice_key)
    raw_lowered = raw_key.lower()
    fallback_label = clean_text(fallback)
    if raw_lowered == "male-us":
        return fallback_label or "People | Male US"
    key = normalize_audio_voice_key(voice_key)
    lowered = key.lower()
    if lowered.startswith("sot:"):
        voice = normalize_sound_of_text_voice_key(key)
        if voice == "en-GB":
            return "Sound of Text | Female UK"
        if voice == "en-US":
            return "Sound of Text | Female US"
        return f"Sound of Text | {voice}"
    if lowered.startswith("edge:"):
        if fallback_label and fallback_label.lower().startswith(("people |", "microsoft |")):
            return fallback_label
        try:
            from module_main.edge_tts_service import edge_voice_option_label

            return edge_voice_option_label(key.split(":", 1)[1])
        except Exception:
            return f"Edge | {key.split(':', 1)[1]}"
    if lowered.startswith("microsoft:"):
        if fallback_label:
            return fallback_label
        try:
            from module_main.edge_tts_service import edge_voice_option_label

            edge_label = edge_voice_option_label(key.split(":", 1)[1])
            return _microsoft_online_label(edge_label, key)
        except Exception:
            return f"Microsoft | {key.split(':', 1)[1]}"
    if lowered.startswith("sapi:"):
        return fallback_label or _microsoft_voice_label(key.split(":", 1)[1])
    if lowered.startswith("vibevoice:"):
        return "VibeVoice disabled"
    if lowered.startswith("kokoro_vi:"):
        return _kokoro_vietnamese_voice_label(key.split(":", 1)[1])
    if lowered.startswith("kokoro:"):
        return _kokoro_voice_label(key.split(":", 1)[1])
    return fallback_label or key or "Embedded voice"


def audio_mime_for_voice(voice_key: str) -> tuple[str, str]:
    lowered = normalize_audio_voice_key(voice_key).lower()
    if lowered.startswith(("kokoro:", "kokoro_vi:", "sapi:")):
        return "audio/wav", "wav"
    return "audio/mpeg", "mp3"


def mime_for_audio_path(path: Path) -> str:
    suffix = str(path.suffix or "").lower()
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".ogg":
        return "audio/ogg"
    if suffix == ".m4a":
        return "audio/mp4"
    return "audio/mpeg"


def build_effect_sounds(log=None) -> dict:
    effects = {}
    for key, path in EFFECT_SOUND_FILES.items():
        try:
            if path.is_file():
                data = path.read_bytes()
                asset_path = write_server_sound_asset(f"fx-{key}", data, "audio/mpeg")
                effects[key] = {"mime": "audio/mpeg", "url": asset_path, "u": asset_path}
        except Exception as exc:
            if callable(log):
                log(f"Bo qua am thanh {key}: {exc}")
    return effects


def voice_sample_cache_path(voice_key: str, mime: str = "") -> Path:
    key = normalize_audio_voice_key(voice_key) or clean_text(voice_key)
    extension = "wav" if "wav" in str(mime or "").lower() or key.lower().startswith(("kokoro:", "kokoro_vi:", "sapi:")) else "mp3"
    digest = hashlib.sha1(key.lower().encode("utf-8")).hexdigest()[:16]
    return VOICE_SAMPLE_DIR / f"{digest}.{extension}"


def write_voice_sample_cache(voice_key: str, label: str, audio_bytes: bytes, mime: str, text: str = "") -> Path:
    ensure_cache_dirs()
    path = voice_sample_cache_path(voice_key, mime)
    payload = bytes(audio_bytes or b"")
    tmp_path = path.with_name(f".{path.stem}.{os.getpid()}.{int(time.time() * 1000)}.tmp{path.suffix}")
    tmp_path.write_bytes(payload)
    written_path = path
    for attempt in range(8):
        try:
            os.replace(str(tmp_path), str(path))
            written_path = path
            break
        except PermissionError:
            if attempt >= 7:
                written_path = path.with_name(f"{path.stem}_{int(time.time() * 1000)}{path.suffix}")
                os.replace(str(tmp_path), str(written_path))
                break
            time.sleep(0.08)
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except Exception:
            pass
    meta_path = path.with_suffix(path.suffix + ".json")
    meta = {
        "label": clean_text(label) or embedded_voice_label(voice_key),
        "voice": normalize_audio_voice_key(voice_key) or clean_text(voice_key),
        "mime": clean_text(mime),
        "text": clean_text(text),
        "updated_at": int(time.time()),
        "file": written_path.name,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return written_path


def _mp3_duration_ms(audio_bytes: bytes) -> int:
    data = bytes(audio_bytes or b"")
    bitrates = {
        (3, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
        (2, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
        (0, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
    }
    sample_rates = {
        3: [44100, 48000, 32000, 0],
        2: [22050, 24000, 16000, 0],
        0: [11025, 12000, 8000, 0],
    }
    offset = 0
    total_seconds = 0.0
    frames = 0
    while offset + 4 <= len(data):
        if data[offset] != 0xFF or (data[offset + 1] & 0xE0) != 0xE0:
            offset += 1
            continue
        version = (data[offset + 1] >> 3) & 0x03
        layer = (data[offset + 1] >> 1) & 0x03
        bitrate_index = (data[offset + 2] >> 4) & 0x0F
        sample_rate_index = (data[offset + 2] >> 2) & 0x03
        padding = (data[offset + 2] >> 1) & 0x01
        if version == 1 or layer != 1 or bitrate_index in {0, 15} or sample_rate_index == 3:
            offset += 1
            continue
        bitrate = bitrates.get((version, 3), bitrates[(0, 3)])[bitrate_index] * 1000
        sample_rate = sample_rates.get(version, sample_rates[0])[sample_rate_index]
        if not bitrate or not sample_rate:
            offset += 1
            continue
        samples_per_frame = 1152 if version == 3 else 576
        frame_length = int((144000 * (bitrate // 1000) / sample_rate) + padding) if version == 3 else int((72000 * (bitrate // 1000) / sample_rate) + padding)
        if frame_length <= 4:
            offset += 1
            continue
        total_seconds += samples_per_frame / float(sample_rate)
        frames += 1
        offset += frame_length
    return int(round(total_seconds * 1000)) if frames else 0


def audio_duration_ms(audio_bytes: bytes, mime: str = "") -> int:
    payload = bytes(audio_bytes or b"")
    if not payload:
        return 0
    try:
        import soundfile as sf  # type: ignore

        info = sf.info(io.BytesIO(payload))
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        if duration > 0:
            return int(round(duration * 1000))
    except Exception:
        pass
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            if frames > 0 and sample_rate > 0:
                return int(round((frames / float(sample_rate)) * 1000))
    except Exception:
        pass
    if "mpeg" in str(mime or "").lower() or payload[:3] == b"ID3" or (len(payload) > 2 and payload[0] == 0xFF):
        return _mp3_duration_ms(payload)
    return 0


def audio_rms_rows(audio_bytes: bytes) -> list[dict]:
    try:
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore

        data, sample_rate = sf.read(io.BytesIO(bytes(audio_bytes or b"")), dtype="float32", always_2d=True)
        if data is None or len(data) == 0 or sample_rate <= 0:
            return []
        samples = data.mean(axis=1)
        window_size = max(128, int(round(sample_rate * 0.018)))
        hop_size = max(64, int(round(sample_rate * 0.012)))
        rows = []
        max_level = 0.0
        total = int(len(samples))
        for offset in range(0, total, hop_size):
            chunk = samples[offset : min(total, offset + window_size)]
            if len(chunk) == 0:
                continue
            level = float(np.sqrt(np.mean(np.square(chunk))))
            max_level = max(max_level, level)
            rows.append({"time": ((offset + (len(chunk) / 2.0)) / float(sample_rate)) * 1000.0, "level": level})
        if max_level > 0:
            for row in rows:
                row["level"] = float(row["level"]) / max_level
        return rows
    except Exception:
        return []


def build_audio_guided_timings(tokens: list[dict], duration_ms: int, audio_bytes: bytes) -> list[dict]:
    duration = max(int(duration_ms or 0), 0)
    base = build_timings(tokens, duration) if duration > 0 else []
    if duration <= 0 or len(base) < 2:
        return base
    rows = audio_rms_rows(audio_bytes)
    if len(rows) < 6:
        return base
    search_radius = max(80.0, min(220.0, float(duration) / max(6.0, len(base) * 2.4)))
    min_gap = max(45.0, min(180.0, float(duration) / max(10.0, len(base) * 2.8)))
    boundaries = []
    previous = 0.0
    for index, item in enumerate(base[:-1]):
        remaining = len(base) - index - 2
        latest = max(previous + min_gap, float(duration) - ((remaining + 1) * min_gap))
        predicted = max(previous + min_gap, min(latest, float(item.get("e", 0) or 0)))
        low = max(previous + min_gap, min(latest, predicted - search_radius))
        high = max(low, min(latest, predicted + search_radius))
        best_time = predicted
        best_score = math.inf
        for row in rows:
            t = float(row.get("time", 0.0) or 0.0)
            if t < low or t > high:
                continue
            distance = abs(t - predicted) / max(1.0, search_radius)
            score = (float(row.get("level", 0.0) or 0.0) * 1.8) + (distance * 0.45)
            if score < best_score:
                best_score = score
                best_time = t
        boundary = max(previous + min_gap, min(latest, best_time))
        boundaries.append(boundary)
        previous = boundary
    start = 0.0
    out = []
    for index, item in enumerate(base):
        end = boundaries[index] if index < len(boundaries) else float(duration)
        safe_end = max(start + 1.0, min(float(duration), end))
        out.append({"i": int(item.get("i", index) or index), "s": int(round(start)), "e": int(round(safe_end))})
        start = safe_end
    return out


def get_vibevoice_runtime():
    raise RuntimeError(VIBEVOICE_DISABLED_MESSAGE)


def reset_vibevoice_runtime() -> None:
    global _VIBEVOICE_RUNTIME
    if _VIBEVOICE_RUNTIME is not None:
        try:
            _VIBEVOICE_RUNTIME.close()
        except Exception:
            pass
    _VIBEVOICE_RUNTIME = None


def vibevoice_build_device() -> str:
    # The local GUI often runs on small GPUs; VibeVoice 0.5B OOMs on 2 GB VRAM.
    # CPU is slower, but it is the reliable path for packaging audio into Space_W.
    return "cpu"


def is_cuda_oom_error(exc: BaseException) -> bool:
    text = str(exc or "").lower()
    return "cuda out of memory" in text or ("out of memory" in text and "gpu" in text)


def get_kokoro_runtime():
    global _KOKORO_RUNTIME
    if _KOKORO_RUNTIME is None:
        from module_main.tts_kokoro_local import KokoroLocalTTS

        _KOKORO_RUNTIME = KokoroLocalTTS()
        _KOKORO_RUNTIME.prefer_subprocess = True
    return _KOKORO_RUNTIME


# Added 2026-07-07: lets desktop builders borrow Server 2 distributed workers without looping inside workers.
def builder_server2_bridge_enabled() -> bool:
    if clean_text(os.environ.get("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED", "")).lower() in {"1", "true", "yes", "on"}:
        return False
    if clean_text(os.environ.get("FUTURE_SERVER2_PROCESS_ROLE", "")):
        return False
    argv_text = " ".join(str(item or "") for item in sys.argv).lower()
    if "future_distributed_worker_client.py" in argv_text or "futureworkerauto" in argv_text:
        return False
    return clean_text(os.environ.get("FUTURE_BUILDER_USE_SERVER2", "1")).lower() not in {"0", "false", "no", "off"}


def builder_server2_url() -> str:
    raw = clean_text(os.environ.get("FUTURE_BUILDER_SERVER2_URL", "")) or BUILDER_SERVER2_DEFAULT_URL
    return raw.rstrip("/") or BUILDER_SERVER2_DEFAULT_URL


def builder_server2_json(path: str, payload: dict, timeout: float = 25.0) -> dict:
    if not builder_server2_bridge_enabled():
        return {}
    url = builder_server2_url() + "/" + str(path or "").lstrip("/")
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urlopen(request, timeout=max(1.0, float(timeout or 25.0))) as response:
            data = response.read(32 * 1024 * 1024)
        result = json.loads(data.decode("utf-8", errors="replace") or "{}")
        return result if isinstance(result, dict) and result.get("ok") else {}
    except (OSError, TimeoutError, URLError, json.JSONDecodeError):
        return {}


_BUILDER_STAGE_LOCK = threading.RLock()
_BUILDER_STAGE_SESSIONS: set[str] = set()
_BUILDER_STAGE_MARKER = SERVER_DATA_ROOT / "_future_manifest_build_pending.json"


def _builder_stage_marker_write() -> None:
    try:
        _BUILDER_STAGE_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _BUILDER_STAGE_MARKER.write_text(
            json.dumps(
                {
                    "version": 1,
                    "dirty": bool(_BUILDER_STAGE_SESSIONS),
                    "updated_epoch": time.time(),
                    "active_session_ids": sorted(_BUILDER_STAGE_SESSIONS),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


# Updated 2026-08-04: builders stage while writing, then Server 2 publishes an exact completed lesson file.
def builder_server2_build_begin(space: str, output_path: str | Path = "") -> str:
    session_id = uuid.uuid4().hex
    with _BUILDER_STAGE_LOCK:
        _BUILDER_STAGE_SESSIONS.add(session_id)
        os.environ["FUTURE_LESSON_IDENTITY_STAGING"] = "1"
        _builder_stage_marker_write()
    builder_server2_json(
        "/builder/session",
        {"action": "start", "session_id": session_id, "space": clean_text(space), "path": str(output_path or "")},
        timeout=3.0,
    )
    return session_id


def builder_server2_build_end(session_id: str, space: str, output_path: str | Path = "", success: bool = True) -> dict:
    result = {}
    try:
        result = builder_server2_json(
            "/builder/session",
            {
                "action": "finish" if success else "failed",
                "session_id": clean_text(session_id),
                "space": clean_text(space),
                "path": str(output_path or ""),
            },
            timeout=3.0,
        )
    finally:
        with _BUILDER_STAGE_LOCK:
            _BUILDER_STAGE_SESSIONS.discard(clean_text(session_id))
            _builder_stage_marker_write()
            if not _BUILDER_STAGE_SESSIONS:
                os.environ.pop("FUTURE_LESSON_IDENTITY_STAGING", None)
    return result


def builder_server2_translate_to_vi(text: str, force_refresh: bool = False) -> str:
    source = clean_text(text)
    if not source:
        return ""
    result = builder_server2_json(
        "/builder/translate",
        {"text": source, "dest": "vi", "src": "en", "limit": 9000, "force": bool(force_refresh)},
        timeout=45.0,
    )
    return clean_text(result.get("translation", ""))


def builder_server2_tts_audio(text: str, voice_key: str, log) -> tuple[bytes, str] | None:
    source = clean_text(text)
    key = normalize_audio_voice_key(voice_key)
    if not source or not key:
        return None
    builder_name = clean_text(Path(sys.argv[0]).stem).lower() or "builder"
    result = builder_server2_json(
        "/builder/tts",
        {
            "text": source,
            "voice": key,
            "source": f"builder:{builder_name}",
            "build_id": clean_text(os.environ.get("FUTURE_BUILDER_BUILD_ID", "")) or f"{builder_name}:{os.getpid()}",
        },
        timeout=90.0,
    )
    audio_b64 = clean_text(result.get("audio_base64", ""))
    if not audio_b64:
        return None
    try:
        audio_bytes = base64.b64decode(audio_b64.encode("ascii"), validate=True)
    except Exception:
        return None
    if not audio_bytes:
        return None
    mime = clean_text(result.get("mime", "")) or clean_text(result.get("audio_mime", "")) or audio_mime_for_voice(key)[0]
    if callable(log):
        worker_name = clean_text(result.get("worker", "")) or "Server 2 worker"
        log(f"Audio worker: {worker_name}")
    return bytes(audio_bytes), mime


def synthesize_sapi_audio_bytes(text: str, voice_key: str, log) -> bytes:
    import pyttsx3  # type: ignore

    clean_sentence = clean_text(text)
    if not clean_sentence:
        raise RuntimeError("Missing text for Microsoft voice.")
    key = normalize_audio_voice_key(voice_key)
    voice_id = clean_text(key.split(":", 1)[1] if ":" in key else key)
    output_path = LOCAL_TTS_OUTPUT_DIR / f"sapi_{voice_cache_key(clean_sentence, key)}.wav"
    if output_path.is_file():
        return output_path.read_bytes()
    engine = pyttsx3.init()
    try:
        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate", 145)
        engine.setProperty("volume", 1.0)
        engine.save_to_file(clean_sentence, str(output_path))
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass
    for _attempt in range(20):
        if output_path.is_file() and output_path.stat().st_size > 44:
            return output_path.read_bytes()
        time.sleep(0.05)
    raise RuntimeError("Microsoft voice did not create audio.")


# Added 2026-07-03: runs the local Kokoro Vietnamese ONNX CLI for kokoro_vi:* voices.
def synthesize_kokoro_vietnamese_audio_bytes(text: str, voice_key: str, output_path: Path, log) -> bytes:
    clean_sentence = clean_text(text)
    if not clean_sentence:
        raise RuntimeError("Missing text for Kokoro Vietnamese voice.")
    key = normalize_audio_voice_key(voice_key)
    voice_name = clean_text(key.split(":", 1)[1] if ":" in key else "") or "diem_trinh"
    voicepack = KOKORO_VI_VOICEPACK_DIR / f"{voice_name}.pt"
    if not voicepack.is_file():
        voicepack = KOKORO_VI_DEFAULT_VOICEPACK
    missing = [str(path) for path in (KOKORO_VI_ONNX_PATH, KOKORO_VI_CONFIG_PATH, voicepack) if not path.is_file()]
    if missing:
        raise RuntimeError("Kokoro Vietnamese model file missing: " + "; ".join(missing))
    if callable(log):
        log(f"Kokoro Vietnamese ONNX: {voice_name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def kokoro_vi_device_candidates() -> list[str]:
        requested = clean_text(os.environ.get("FUTURE_KOKORO_VI_DEVICE", "")).lower() or "cpu"
        if requested in {"cuda", "gpu"}:
            return ["cuda", "cpu"]
        if requested == "auto":
            try:
                import onnxruntime as ort  # type: ignore

                if "CUDAExecutionProvider" in list(ort.get_available_providers() or []):
                    return ["cuda", "cpu"]
            except Exception:
                pass
        return ["cpu"]

    def external_python_env() -> dict:
        env = dict(os.environ)
        bad_markers = ("\\_internal", "\\pyqt5\\qt5\\bin")
        kept = []
        for part in env.get("PATH", "").split(os.pathsep):
            lower = part.lower()
            if any(marker in lower for marker in bad_markers):
                continue
            kept.append(part)
        env["PATH"] = os.pathsep.join(kept)
        env.pop("QT_PLUGIN_PATH", None)
        env.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
        env.pop("QT_QPA_PLATFORM", None)
        return env

    def kokoro_vi_python_command() -> list[str]:
        candidates: list[list[str]] = []
        env_python = clean_text(os.environ.get("FUTURE_KOKORO_VI_PYTHON", ""))
        if env_python:
            candidates.append([env_python])
        if not getattr(sys, "frozen", False):
            candidates.append([sys.executable])
        candidates.extend([["python"], ["py", "-3"]])
        for candidate in candidates:
            try:
                probe = subprocess.run(
                    [*candidate, "-c", "import kokoro_vietnamese.onnx_cli, onnxruntime, soundfile; print('ok')"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=12,
                    check=False,
                    env=external_python_env(),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if probe.returncode == 0 and "ok" in str(probe.stdout or ""):
                    return candidate
            except Exception:
                continue
        return []

    def run_kokoro_cli_subprocess(run_voicepack: Path, suffix: str = "", device: str = "cpu") -> bytes:
        python_cmd = kokoro_vi_python_command()
        if not python_cmd:
            raise RuntimeError("Kokoro Vietnamese needs a real Python runtime with kokoro_vietnamese, onnxruntime, and soundfile.")
        timeout_raw = clean_text(os.environ.get("FUTURE_KOKORO_VI_TIMEOUT_SECONDS", "0"))
        try:
            process_timeout = float(timeout_raw)
        except Exception:
            process_timeout = 0.0
        process_timeout_value = None if process_timeout <= 0 else max(30.0, process_timeout)
        try:
            if output_path.is_file():
                output_path.unlink()
        except OSError:
            pass
        command = [
            *python_cmd,
            "-m",
            "kokoro_vietnamese.onnx_cli",
            "--text",
            clean_sentence,
            "--output",
            str(output_path),
            "--device",
            device,
            "--onnx",
            str(KOKORO_VI_ONNX_PATH),
            "--voicepack",
            str(run_voicepack),
            "--config",
            str(KOKORO_VI_CONFIG_PATH),
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(WRITE_HTML_DIR),
            timeout=process_timeout_value,
            check=False,
            env=external_python_env(),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stderr_text = completed.stderr.decode("utf-8", errors="ignore").strip() if isinstance(completed.stderr, (bytes, bytearray)) else str(completed.stderr or "").strip()
        stdout_text = completed.stdout.decode("utf-8", errors="ignore").strip() if isinstance(completed.stdout, (bytes, bytearray)) else str(completed.stdout or "").strip()
        if completed.returncode != 0:
            raise RuntimeError(stderr_text or stdout_text or f"Kokoro Vietnamese exited with {completed.returncode}.")
        if output_path.is_file() and output_path.stat().st_size > 44:
            return output_path.read_bytes()
        raise RuntimeError(
            "Kokoro Vietnamese did not create audio. "
            f"voice={voice_name}{suffix}; voicepack={run_voicepack}; python={' '.join(python_cmd)}; "
            f"exists={output_path.is_file()}; size={output_path.stat().st_size if output_path.is_file() else 0}; "
            f"stdout={stdout_text[:400]}; stderr={stderr_text[:400]}"
        )

    # Added 2026-07-10: PyInstaller workers cannot run sys.executable -m here because sys.executable is the worker EXE.
    def run_kokoro_onnx_in_process(run_voicepack: Path, suffix: str = "", device: str = "cpu") -> bytes:
        try:
            from kokoro_vietnamese.core import SAMPLE_RATE  # type: ignore
            from kokoro_vietnamese.onnx_cli import KokoroVietnameseONNX  # type: ignore
            import soundfile as sf  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Kokoro Vietnamese runtime import failed: {exc}") from exc
        runtime_key = "|".join(str(item) for item in (KOKORO_VI_ONNX_PATH, KOKORO_VI_CONFIG_PATH, run_voicepack, device))
        with _KOKORO_VI_ONNX_RUNTIME_LOCK:
            runtime = _KOKORO_VI_ONNX_RUNTIMES.get(runtime_key)
            load_lock = _KOKORO_VI_ONNX_RUNTIME_LOAD_LOCKS.get(runtime_key)
            if load_lock is None:
                load_lock = threading.Lock()
                _KOKORO_VI_ONNX_RUNTIME_LOAD_LOCKS[runtime_key] = load_lock
        if runtime is None:
            with load_lock:
                runtime = _KOKORO_VI_ONNX_RUNTIMES.get(runtime_key)
                if runtime is None:
                    runtime = KokoroVietnameseONNX(
                        voice=None,
                        onnx_path=KOKORO_VI_ONNX_PATH,
                        voicepack_path=run_voicepack,
                        config_path=KOKORO_VI_CONFIG_PATH,
                        device=device,
                    )
                    with _KOKORO_VI_ONNX_RUNTIME_LOCK:
                        _KOKORO_VI_ONNX_RUNTIMES[runtime_key] = runtime
        audio, phonemes = runtime.synthesize(clean_sentence)
        if len(audio) == 0:
            details = "; ".join(
                item for item in (
                    f"voice={voice_name}{suffix}",
                    f"voicepack={run_voicepack}",
                    f"phonemes={str(phonemes or '')[:400]}" if phonemes else "",
                )
                if item
            )
            raise RuntimeError("Kokoro Vietnamese did not create audio. " + details)
        sf.write(output_path, audio, SAMPLE_RATE)
        if not output_path.is_file() or output_path.stat().st_size <= 44:
            raise RuntimeError(
                "Kokoro Vietnamese did not create audio. "
                f"voice={voice_name}{suffix}; voicepack={run_voicepack}; "
                f"exists={output_path.is_file()}; size={output_path.stat().st_size if output_path.is_file() else 0}"
            )
        return output_path.read_bytes()

    prefer_in_process = clean_text(os.environ.get("FUTURE_KOKORO_VI_IN_PROCESS", "")).lower() in {"1", "true", "yes", "on", "warm"}
    device_errors = []
    try:
        last_exc = None
        for device in kokoro_vi_device_candidates():
            try:
                if prefer_in_process:
                    try:
                        audio_bytes = run_kokoro_onnx_in_process(voicepack, device=device)
                    except Exception as in_process_exc:
                        if callable(log):
                            log(f"Kokoro Vietnamese in-process fallback to subprocess for {voice_name} ({device}): {in_process_exc}")
                        audio_bytes = run_kokoro_cli_subprocess(voicepack, device=device)
                else:
                    try:
                        audio_bytes = run_kokoro_cli_subprocess(voicepack, device=device)
                    except Exception as subprocess_exc:
                        if callable(log):
                            log(f"Kokoro Vietnamese subprocess fallback to in-process for {voice_name} ({device}): {subprocess_exc}")
                        audio_bytes = run_kokoro_onnx_in_process(voicepack, device=device)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                device_errors.append(f"{device}: {exc}")
                if device != "cpu" and callable(log):
                    log(f"Kokoro Vietnamese {device} failed; fallback CPU: {exc}")
                continue
        if last_exc is not None:
            raise RuntimeError("; ".join(device_errors[-3:])) from last_exc
    except Exception as first_exc:
        if voicepack != KOKORO_VI_DEFAULT_VOICEPACK and KOKORO_VI_DEFAULT_VOICEPACK.is_file():
            if callable(log):
                log(f"Kokoro Vietnamese fallback voicepack for {voice_name}: {first_exc}")
            if prefer_in_process:
                try:
                    audio_bytes = run_kokoro_onnx_in_process(KOKORO_VI_DEFAULT_VOICEPACK, " fallback")
                except Exception as fallback_in_process_exc:
                    if callable(log):
                        log(f"Kokoro Vietnamese default voicepack subprocess fallback: {fallback_in_process_exc}")
                    audio_bytes = run_kokoro_cli_subprocess(KOKORO_VI_DEFAULT_VOICEPACK, " fallback")
            else:
                try:
                    audio_bytes = run_kokoro_cli_subprocess(KOKORO_VI_DEFAULT_VOICEPACK, " fallback")
                except Exception as fallback_subprocess_exc:
                    if callable(log):
                        log(f"Kokoro Vietnamese default voicepack in-process fallback: {fallback_subprocess_exc}")
                    audio_bytes = run_kokoro_onnx_in_process(KOKORO_VI_DEFAULT_VOICEPACK, " fallback")
        else:
            raise
    return audio_bytes


def synthesize_embedded_audio(text: str, voice_key: str, log) -> tuple[bytes, str]:
    ensure_cache_dirs()
    key = normalize_audio_voice_key(voice_key)
    mime, extension = audio_mime_for_voice(key)
    cache_path = TTS_CACHE_DIR / f"{voice_cache_key(text, key)}.{extension}"
    if cache_path.is_file():
        if callable(log):
            log(f"Audio cache: {embedded_voice_label(key)}")
        return cache_path.read_bytes(), mime
    cache_lock_key = str(cache_path)
    with _TTS_SYNTH_LOCK:
        cache_lock = _TTS_SYNTH_LOCKS.get(cache_lock_key)
        if cache_lock is None:
            cache_lock = threading.Lock()
            _TTS_SYNTH_LOCKS[cache_lock_key] = cache_lock
    with cache_lock:
        if cache_path.is_file():
            if callable(log):
                log(f"Audio cache: {embedded_voice_label(key)}")
            return cache_path.read_bytes(), mime

        if clean_text(os.environ.get("FUTURE_TTS_LOCAL_ONLY", "")).lower() not in {"1", "true", "yes", "on"}:
            remote_audio = builder_server2_tts_audio(text, key, log)
            if remote_audio:
                audio_bytes, remote_mime = remote_audio
                cache_path.write_bytes(bytes(audio_bytes or b""))
                return bytes(audio_bytes or b""), remote_mime or mime

        lowered = key.lower()
        if callable(log):
            log(f"Tao audio: {embedded_voice_label(key)}")
        if lowered.startswith("sot:"):
            from module_main.Soundoftext_Api import Soundoftext_Api

            voice = normalize_sound_of_text_voice_key(key) or "en-US"
            audio_bytes = Soundoftext_Api().load_mp3_bytes(text, voice=voice)
            if not audio_bytes:
                raise RuntimeError(f"Sound of Text khong tao duoc audio cho {voice}.")
        elif lowered.startswith("edge:"):
            from module_main.edge_tts_service import synthesize_edge_tts_bytes

            audio_bytes = synthesize_edge_tts_bytes(text, key, speed_percent=92)
        elif lowered.startswith("microsoft:"):
            from module_main.edge_tts_service import synthesize_edge_tts_bytes

            short_name = key.split(":", 1)[1]
            audio_bytes = synthesize_edge_tts_bytes(text, f"edge:{short_name}", speed_percent=92)
        elif lowered.startswith("sapi:"):
            audio_bytes = synthesize_sapi_audio_bytes(text, key, log)
        elif lowered.startswith("vibevoice:"):
            raise RuntimeError(VIBEVOICE_DISABLED_MESSAGE)
        elif lowered.startswith("kokoro_vi:"):
            voice_name = key.split(":", 1)[1]
            safe_voice = re.sub(r"[^0-9A-Za-z._-]+", "-", voice_name).strip("-") or "voice"
            output_path = LOCAL_TTS_OUTPUT_DIR / f"kokoro_vi_{safe_voice}_{voice_cache_key(text, key)}.wav"
            try:
                audio_bytes = synthesize_kokoro_vietnamese_audio_bytes(text, key, output_path, log)
            except Exception as exc:
                if callable(log):
                    log(f"Kokoro Vietnamese failed for {voice_name}: {exc}")
                raise RuntimeError(
                    f"Kokoro Vietnamese voice {voice_name} failed. "
                    "Install Python 3.11 with kokoro-vietnamese, onnxruntime, and soundfile on this worker, "
                    f"or choose Edge NamMinh/HoaiMy. Detail: {exc}"
                ) from exc
        elif lowered.startswith("kokoro:"):
            voice_name = key.split(":", 1)[1]
            safe_voice = re.sub(r"[^0-9A-Za-z._-]+", "-", voice_name).strip("-") or "voice"
            kokoro_text = clean_kokoro_tts_text(text)
            output_path = LOCAL_TTS_OUTPUT_DIR / f"kokoro_{safe_voice}_{voice_cache_key(kokoro_text, key)}.wav"
            if callable(log):
                log("Kokoro helper/subprocess")
            result_path, _voice_name = get_kokoro_runtime().synthesize_to_file(
                kokoro_text,
                voice_name,
                str(output_path),
                speed=1.0,
                allow_subprocess=True,
            )
            audio_bytes = Path(result_path).read_bytes()
        else:
            raise RuntimeError(f"Voice chua ho tro nhung audio: {voice_key}")

        cache_path.write_bytes(bytes(audio_bytes or b""))
        return bytes(audio_bytes or b""), mime


def translate_to_vi(text: str, force_refresh: bool = False) -> str:
    translated = builder_server2_translate_to_vi(text, force_refresh=force_refresh)
    if translated:
        return translated
    try:
        from module_main.Data_Input.Import import Translator

        result = Translator().translate(text, dest="vi", src="en")
        return clean_text(getattr(result, "text", "") or "")
    except Exception:
        return ""


def normalize_ipa_text(ipa_text: str, voice: str = "en-US") -> str:
    try:
        from module_main.Listenapp.listen_common import _normalize_ipa_text

        return clean_text(_normalize_ipa_text(str(ipa_text or ""), voice))
    except Exception:
        return clean_text(ipa_text)


def voice_region(voice: str) -> str:
    key = str(voice or "").strip().lower()
    if key.startswith("kokoro:bf_") or key.startswith("kokoro:bm_"):
        return "en-GB"
    if any(part in key for part in ("female-uk", "en-gb", "en_gb", "gb", "uk", "sonia", "ryan")):
        return "en-GB"
    return "en-US"


def ipa_cache_key(text: str, voice: str) -> str:
    region = voice_region(voice)
    cleaned = clean_text(text).lower()
    return hashlib.sha1(f"ipa-v1\0{region}\0{cleaned}".encode("utf-8", errors="ignore")).hexdigest()


def load_ipa_cache() -> dict[str, str]:
    global IPA_CACHE_RAM
    with IPA_CACHE_LOCK:
        if IPA_CACHE_RAM is not None:
            return IPA_CACHE_RAM
        try:
            payload = json.loads(IPA_CACHE_PATH.read_text(encoding="utf-8-sig", errors="replace"))
            source = payload if isinstance(payload, dict) else {}
            IPA_CACHE_RAM = {clean_text(key): clean_text(value) for key, value in source.items() if clean_text(key) and clean_text(value)}
        except Exception:
            IPA_CACHE_RAM = {}
        return IPA_CACHE_RAM


def save_ipa_cache_if_needed(force: bool = False) -> None:
    global IPA_CACHE_DIRTY_COUNT
    with IPA_CACHE_LOCK:
        if not IPA_CACHE_RAM or (not force and IPA_CACHE_DIRTY_COUNT < 40):
            return
        try:
            CACHE_ROOT.mkdir(parents=True, exist_ok=True)
            disk_payload = {}
            if IPA_CACHE_PATH.is_file():
                try:
                    loaded = json.loads(IPA_CACHE_PATH.read_text(encoding="utf-8-sig", errors="replace"))
                    if isinstance(loaded, dict):
                        disk_payload.update({clean_text(key): clean_text(value) for key, value in loaded.items() if clean_text(key) and clean_text(value)})
                except Exception:
                    pass
            disk_payload.update(IPA_CACHE_RAM)
            tmp_path = IPA_CACHE_PATH.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(disk_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(IPA_CACHE_PATH)
            IPA_CACHE_DIRTY_COUNT = 0
        except Exception:
            pass


def cache_ipa_value(cache_key: str, ipa: str) -> str:
    global IPA_CACHE_DIRTY_COUNT
    result = clean_text(ipa)
    if not result:
        return ""
    with IPA_CACHE_LOCK:
        load_ipa_cache()[cache_key] = result
        IPA_CACHE_DIRTY_COUNT += 1
    save_ipa_cache_if_needed()
    return result


def builder_server2_phonemize_text(text: str, voice: str) -> str:
    if os.environ.get("FUTURE_BUILDER_SERVER2_BRIDGE_DISABLED"):
        return ""
    try:
        payload = builder_server2_json("/builder/phonemize", {"text": text, "voice": voice}, timeout=30.0)
        return clean_text(payload.get("ipa"))
    except Exception:
        return ""


def phonemize_text(text: str, voice: str = "en-US") -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    cache_key = ipa_cache_key(cleaned, voice)
    cached = load_ipa_cache().get(cache_key, "")
    if cached:
        return cached
    remote_ipa = builder_server2_phonemize_text(cleaned, voice)
    if remote_ipa:
        return cache_ipa_value(cache_key, remote_ipa)
    region = voice_region(voice)
    language = "en-gb" if region == "en-GB" else "en-us"
    try:
        if not os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
            for candidate in (
                Path(r"C:\Program Files\eSpeak NG\libespeak-ng.dll"),
                Path(r"C:\Program Files (x86)\eSpeak NG\libespeak-ng.dll"),
            ):
                if candidate.is_file():
                    os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(candidate)
                    break
        from phonemizer import phonemize

        ipa = phonemize(
            cleaned,
            language=language,
            backend="espeak",
            strip=True,
            preserve_punctuation=True,
            with_stress=True,
        )
        return cache_ipa_value(cache_key, clean_text(str(ipa or "")))
    except Exception:
        try:
            from module_main.Listenapp.listen_common import PHONEMIZER_READY, phonemize

            if not PHONEMIZER_READY or phonemize is None:
                return ""
            ipa = phonemize(
                cleaned,
                language=language,
                backend="espeak",
                strip=True,
                preserve_punctuation=True,
                with_stress=True,
            )
            return cache_ipa_value(cache_key, normalize_ipa_text(str(ipa or ""), "en-GB" if language == "en-gb" else "en-US"))
        except Exception:
            return ""


def analyze_sentence(text: str) -> list[dict]:
    try:
        from module_main.QMWrite.ScoringDef import analyze_sentence_data

        data = analyze_sentence_data(text, {}) or []
        return [dict(item) for item in data if isinstance(item, dict)]
    except Exception:
        return []


def sentence_spans(text: str, analyzed: list[dict], voice: str) -> list[dict]:
    by_norm: dict[str, list[dict]] = {}
    for item in analyzed:
        key = re.sub(r"[^\w']+", "", str(item.get("text") or "").lower())
        if key:
            by_norm.setdefault(key, []).append(item)

    spans: list[dict] = []
    used: dict[str, int] = {}
    for match in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text):
        surface = match.group(0)
        norm = re.sub(r"[^\w']+", "", surface.lower())
        idx = used.get(norm, 0)
        used[norm] = idx + 1
        token_info = (by_norm.get(norm) or [{}])
        token_info = token_info[idx] if idx < len(token_info) else token_info[-1]
        dict_ipa = clean_text(token_info.get("dict_phonetic"))
        token_ipa_us = phonemize_text(surface, "en-US") or dict_ipa
        token_ipa_uk = phonemize_text(surface, "en-GB") or dict_ipa
        token_ipa = token_ipa_uk if voice_region(voice) == "en-GB" else token_ipa_us
        if not token_ipa:
            token_ipa = dict_ipa or phonemize_text(surface, voice)
        spans.append(
            {
                "t": surface,
                "s": int(match.start()),
                "e": int(match.end()),
                "i": token_ipa,
                "iu": token_ipa_us or token_ipa,
                "ik": token_ipa_uk or token_ipa,
                "l": clean_text(token_info.get("lemma")) or surface.lower(),
                "p": clean_text(token_info.get("pos")),
                "d": clean_text(token_info.get("dep")),
                "m": clean_text(token_info.get("viet") or token_info.get("dict_meaning")),
            }
        )
    return spans


def normalize_timing_token(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum() or ch == "'")


def token_timing_weight(token: dict) -> float:
    token_text = clean_text(token.get("t") or token.get("text"))
    normalized = normalize_timing_token(token_text)
    base_weight = max(0.45, float(len(normalized or token_text) or 1))
    if re.search(r"[.,!?;:]$", token_text):
        base_weight += 0.36

    ipa_text = clean_text(token.get("i") or token.get("ipa"))
    if ipa_text:
        ipa_compact = re.sub(r"\s+", "", ipa_text)
        ipa_vowel_count = len(re.findall(r"[iyɨʉɯuɪʏʊeøɘɵɤoəɛœɜɞʌɔæɐaɶɑɒɚɝ]", ipa_compact, flags=re.UNICODE))
        stress_count = ipa_text.count("ˈ") + ipa_text.count("ˌ")
        base_weight = max(
            base_weight,
            float(len(ipa_compact or "")) * 0.52,
            (float(ipa_vowel_count or 0) * 1.45) + (float(stress_count) * 0.2),
        )
    return float(max(0.45, base_weight))


def estimate_duration_ms(text: str, tokens: list[dict]) -> int:
    token_count = len(tokens) if tokens else len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))
    compact = re.sub(r"\s+", "", clean_text(text))
    char_count = max(1, len(compact))
    estimated = (float(max(1, token_count)) * 420.0) + (float(char_count) * 18.0) + 160.0
    return int(round(max(720.0, min(18000.0, estimated))))


def build_timings(tokens: list[dict], duration_ms: int) -> list[dict]:
    if not tokens:
        return []
    duration = max(int(duration_ms or 0), 720)
    lead_ms = min(90.0, float(duration) * 0.06)
    tail_ms = min(120.0, float(duration) * 0.08)
    if float(duration) <= (lead_ms + tail_ms + 90.0):
        lead_ms = 0.0
        tail_ms = 0.0
    usable_ms = max(80.0, float(duration) - lead_ms - tail_ms)
    weights = [token_timing_weight(item) for item in tokens]
    total_weight = max(0.01, sum(float(item or 0.0) for item in weights))
    cursor = float(lead_ms)
    cumulative = 0.0
    timings = []
    min_span = 45.0
    last_index = len(tokens) - 1
    for index, weight in enumerate(weights):
        start = float(cursor)
        if index >= last_index:
            end = max(float(duration) - tail_ms, start + 1.0)
        else:
            cumulative += float(weight or 0.0)
            predicted = lead_ms + (usable_ms * cumulative / total_weight)
            remaining = max(1, last_index - index)
            max_end = float(duration) - tail_ms - (float(remaining) * min_span)
            end = max(start + min_span, predicted)
            if max_end > start:
                end = min(end, max_end)
        end = min(float(duration), max(start + 1.0, end))
        timings.append({"i": index, "s": int(round(start)), "e": int(round(end))})
        cursor = float(end)
    return timings


def compact_analysis(analyzed: list[dict]) -> list[dict]:
    out = []
    for item in analyzed:
        out.append(
            {
                "t": clean_text(item.get("text")),
                "l": clean_text(item.get("lemma")),
                "p": clean_text(item.get("pos")),
                "d": clean_text(item.get("dep")),
                "h": clean_text(item.get("head")),
                "m": clean_text(item.get("viet") or item.get("dict_meaning")),
            }
        )
    return out


def build_scoring_words(text: str, tokens: list[dict], analyzed: list[dict]) -> list[dict]:
    analysis_by_norm: dict[str, list[dict]] = {}
    for item in analyzed:
        key = re.sub(r"[^0-9A-Za-z']+", "", clean_text(item.get("text")).lower())
        if key:
            analysis_by_norm.setdefault(key, []).append(item)
    used: dict[str, int] = {}
    words = []
    source_tokens = list(tokens or [])
    if source_tokens:
        for index, token in enumerate(source_tokens):
            surface = clean_text(token.get("t") or token.get("text"))
            if not surface:
                continue
            norm = re.sub(r"[^0-9A-Za-z']+", "", surface.lower())
            order = used.get(norm, 0)
            used[norm] = order + 1
            candidates = analysis_by_norm.get(norm) or []
            analysis = candidates[order] if order < len(candidates) else (candidates[-1] if candidates else {})
            words.append(
                {
                    "t": surface,
                    "n": re.sub(r"[^0-9a-z]+", "", norm.replace("’", "'").replace("'", "")),
                    "i": clean_text(token.get("i")),
                    "iu": clean_text(token.get("iu")),
                    "ik": clean_text(token.get("ik")),
                    "l": clean_text(token.get("l") or analysis.get("lemma")) or surface.lower(),
                    "p": clean_text(token.get("p") or analysis.get("pos")),
                    "d": clean_text(token.get("d") or analysis.get("dep")),
                    "h": clean_text(analysis.get("head")),
                    "m": clean_text(token.get("m") or analysis.get("viet") or analysis.get("dict_meaning")),
                    "s": int(token.get("s", index) or index),
                    "e": int(token.get("e", index + 1) or (index + 1)),
                }
            )
    if words:
        return words
    for index, match in enumerate(re.finditer(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", text)):
        surface = match.group(0)
        norm = re.sub(r"[^0-9A-Za-z']+", "", surface.lower().replace("’", "'"))
        words.append(
            {
                "t": surface,
                "n": re.sub(r"[^0-9a-z]+", "", norm.replace("'", "")),
                "i": "",
                "iu": "",
                "ik": "",
                "l": surface.lower(),
                "p": "",
                "d": "",
                "h": "",
                "m": "",
                "s": int(match.start()),
                "e": int(match.end()),
            }
        )
    return words


GRAMMAR_MAX_QUESTIONS = 10
GRAMMAR_POS_LABELS = {
    "ADJ": "Tính từ",
    "ADP": "Giới từ",
    "ADV": "Trạng từ",
    "AUX": "Trợ động từ",
    "CCONJ": "Liên từ đẳng lập",
    "DET": "Từ hạn định",
    "INTJ": "Thán từ",
    "NOUN": "Danh từ",
    "NUM": "Số từ",
    "PART": "Tiểu từ",
    "PRON": "Đại từ",
    "PROPN": "Danh từ riêng",
    "PUNCT": "Dấu câu",
    "SCONJ": "Liên từ phụ thuộc",
    "SYM": "Ký hiệu",
    "VERB": "Động từ",
    "X": "Từ chưa xác định",
}
GRAMMAR_DEP_LABELS = {
    "ROOT": "Trung tâm vị ngữ của câu",
    "acl": "Mệnh đề bổ nghĩa cho danh từ",
    "acomp": "Bổ ngữ tính từ",
    "advcl": "Mệnh đề trạng ngữ",
    "advmod": "Trạng ngữ",
    "agent": "Tác nhân trong câu bị động",
    "amod": "Bổ nghĩa bằng tính từ",
    "appos": "Đồng vị",
    "attr": "Bổ ngữ cho chủ ngữ",
    "aux": "Trợ động từ",
    "auxpass": "Trợ động từ bị động",
    "case": "Dấu hiệu quan hệ",
    "cc": "Liên từ nối",
    "ccomp": "Mệnh đề bổ ngữ",
    "compound": "Thành phần ghép danh từ",
    "conj": "Thành phần song song",
    "csubj": "Chủ ngữ dạng mệnh đề",
    "dep": "Quan hệ phụ thuộc khác",
    "det": "Từ hạn định cho danh từ",
    "dobj": "Tân ngữ trực tiếp",
    "expl": "Chủ ngữ giả",
    "intj": "Thán ngữ",
    "mark": "Dấu hiệu mệnh đề phụ",
    "neg": "Từ phủ định",
    "nmod": "Bổ nghĩa danh từ",
    "npadvmod": "Cụm danh từ làm trạng ngữ",
    "nsubj": "Chủ ngữ",
    "nsubjpass": "Chủ ngữ bị động",
    "nummod": "Bổ nghĩa số lượng",
    "obj": "Tân ngữ",
    "oprd": "Bổ ngữ cho tân ngữ",
    "parataxis": "Cấu trúc chen ngang",
    "pobj": "Tân ngữ của giới từ",
    "poss": "Sở hữu",
    "predet": "Từ hạn định đứng trước",
    "prep": "Cụm giới từ",
    "prt": "Tiểu từ trong cụm động từ",
    "punct": "Dấu câu",
    "quantmod": "Bổ nghĩa lượng từ",
    "relcl": "Mệnh đề quan hệ",
    "xcomp": "Bổ ngữ động từ mở",
}
GRAMMAR_FALLBACK_OPTIONS = {
    "pos": list(GRAMMAR_POS_LABELS.keys()),
    "dep": ["nsubj", "ROOT", "obj", "dobj", "pobj", "amod", "det", "prep", "aux", "advmod", "compound", "poss"],
    "head": [],
}
GRAMMAR_OK_TEMPLATES = [
    ("Đúng rồi, chính xác là", ""),
    ("Tốt lắm, đáp án đúng là", ""),
    ("Chính xác, câu trả lời là", ""),
    ("Rất tốt, lựa chọn đúng là", ""),
]
GRAMMAR_WRONG_TEMPLATES = [
    ("Sai rồi, đáp án đúng là", ""),
    ("Chưa đúng, chính xác là", ""),
    ("Gần đúng rồi, đáp án cần chọn là", ""),
    ("Cần xem lại, đáp án đúng là", ""),
]
GRAMMAR_QUESTION_TEMPLATES = {
    "pos": [
        "Loại từ của từ sau là gì? {word}",
        "Hãy xác định loại từ của từ sau. {word}",
        "Từ sau thuộc loại từ nào? {word}",
        "Trong câu này, từ sau là loại từ gì? {word}",
        "Chọn nhãn loại từ chính xác cho từ sau. {word}",
    ],
    "dep": [
        "Vai trò ngữ pháp của từ sau là gì? {word}",
        "Hãy xác định vai trò ngữ pháp của từ sau. {word}",
        "Từ sau giữ chức năng ngữ pháp nào trong câu? {word}",
        "Trong cấu trúc câu, từ sau đảm nhiệm vai trò nào? {word}",
        "Chọn vai trò phụ thuộc chính xác cho từ sau. {word}",
    ],
    "head": [
        "Từ sau phụ thuộc vào từ trung tâm nào? {word}",
        "Hãy chọn từ trung tâm mà từ sau phụ thuộc vào. {word}",
        "Trong câu này, từ sau đang nối về trung tâm nào? {word}",
        "Từ nào là head của từ sau? {word}",
        "Chọn từ điều khiển trực tiếp của từ sau. {word}",
    ],
}


def grammar_answer_key(value: object) -> str:
    return clean_text(value).lower()


def grammar_readable_label(value: object) -> str:
    text = clean_text(value)
    for separator in (" - ", " – ", " — ", ": "):
        if separator in text:
            text = text.split(separator)[-1]
    return clean_text(text)


def unique_grammar_values(values: list[object]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        key = grammar_answer_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def grammar_display_value(kind: str, value: object, word: dict | None = None) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    if kind == "pos":
        readable = grammar_readable_label(raw)
        if readable != raw:
            return readable
        return GRAMMAR_POS_LABELS.get(raw.upper(), raw)
    if kind == "dep":
        readable = grammar_readable_label(raw)
        if readable != raw:
            return readable
        return GRAMMAR_DEP_LABELS.get(raw, GRAMMAR_DEP_LABELS.get(raw.lower(), raw))
    if kind == "head":
        target = clean_text((word or {}).get("t") or (word or {}).get("text"))
        if target and grammar_answer_key(raw) == grammar_answer_key(target):
            return f"{raw} là từ trung tâm của chính nó"
    return raw


def grammar_audio_value(kind: str, value: object, word: dict | None = None) -> str:
    if kind == "head":
        return clean_text(value)
    display = grammar_display_value(kind, value, word)
    # POS/DEP audio should be Vietnamese only. If a future label is bilingual
    # like "DET - Từ hạn định", keep the Vietnamese side for TTS.
    for separator in (" - ", " – ", " — ", ": "):
        if separator in display:
            display = display.split(separator)[-1]
    return clean_text(display)


def grammar_option_key(kind: str, value: object, word: dict | None = None) -> str:
    if kind in ("pos", "dep"):
        return grammar_answer_key(grammar_audio_value(kind, value, word))
    return grammar_answer_key(value)


def unique_grammar_options(kind: str, values: list[object], word: dict | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        key = grammar_option_key(kind, text, word)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def grammar_type_answer_voice(kind: str, english_voice_key: str, grammar_voice_key: str) -> str:
    return grammar_voice_key


# Added 2026-07-07: keeps grammar quizzes from generating answer-specific voice files.
def grammar_default_question_audio_text(kind: str) -> str:
    if kind == "pos":
        return "Chọn loại từ đúng."
    if kind == "dep":
        return "Chọn vai trò ngữ pháp đúng."
    if kind == "head":
        return "Chọn từ trung tâm đúng."
    return "Chọn đáp án ngữ pháp đúng."


def grammar_question_template(kind: str, seed_index: int = 0) -> str:
    templates = GRAMMAR_QUESTION_TEMPLATES.get(kind) or ["Chọn đáp án đúng cho từ sau. {word}"]
    return templates[int(seed_index or 0) % len(templates)]


def grammar_question_parts(kind: str, word_text: str, english_voice_key: str, grammar_voice_key: str, template: str = "") -> list[tuple[str, str]]:
    return [(grammar_default_question_audio_text(kind), grammar_voice_key)]


def has_tts_speakable_text(text: str) -> bool:
    return bool(re.search(r"\w", clean_text(text), flags=re.UNICODE))


def grammar_audio_clip(text: str, voice_key: str, log, cache: dict[tuple[str, str], list]) -> list:
    sentence = clean_text(text)
    key = normalize_audio_voice_key(voice_key)
    if not sentence or not key:
        return []
    cache_key = (sentence, key.lower())
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    if not has_tts_speakable_text(sentence):
        cache[cache_key] = []
        return []
    audio_bytes, mime = synthesize_embedded_audio(sentence, key, log)
    if not audio_bytes:
        raise RuntimeError("empty audio")
    asset_path = write_server_sound_asset(f"grammar-{key}-{sentence[:32]}", audio_bytes, mime)
    clip = {"mime": mime, "url": asset_path, "u": asset_path}
    cache[cache_key] = clip
    return clip


def grammar_audio_sequence(parts: list[tuple[str, str]], log, cache: dict[tuple[str, str], list]) -> list[list]:
    sequence: list[list] = []
    for text, voice_key in parts:
        try:
            clip = grammar_audio_clip(text, voice_key, log, cache)
            if clip:
                sequence.append(clip)
        except Exception as exc:
            if callable(log):
                log(f"Bo qua audio ngu phap '{clean_text(text)}': {exc}")
    return sequence


def build_grammar_quiz_audio_assets(
    scoring_words: list[dict],
    english_voice_key: str,
    grammar_voice_key: str,
    log,
    audio_cache: dict[tuple[str, str], list] | None = None,
) -> list[dict]:
    words = list(scoring_words or [])
    if not words:
        return []
    grammar_voice = normalize_audio_voice_key(grammar_voice_key) or "sot:vi-VN"
    english_voice = normalize_audio_voice_key(english_voice_key) or "sot:en-US"
    clip_cache = audio_cache if audio_cache is not None else {}
    items: list[dict] = []
    all_head_values = [word.get("t") for word in words] + [word.get("h") for word in words]
    for word_index, word in enumerate(words):
        target_word = clean_text(word.get("t"))
        if not target_word:
            continue
        for kind, source_key in (("pos", "p"), ("dep", "d"), ("head", "h")):
            answer = clean_text(word.get(source_key))
            if not answer:
                continue
            if kind == "head":
                pool = unique_grammar_options(kind, all_head_values, word)
            else:
                pool = unique_grammar_options(kind, [item.get(source_key) for item in words] + GRAMMAR_FALLBACK_OPTIONS.get(kind, []), word)
            answer_key = grammar_option_key(kind, answer, word)
            distractors = [value for value in pool if grammar_option_key(kind, value, word) != answer_key][:12]
            option_values = unique_grammar_options(kind, [answer] + distractors, word)
            option_audio: dict[str, list[list]] = {}
            prompt_template = grammar_question_template(kind, word_index + len(items))
            items.append(
                {
                    "ty": kind,
                    "a": answer,
                    "wi": word_index,
                    "w": word,
                    "ev": english_voice,
                    "op": option_values,
                    "qp": prompt_template,
                    "qau": grammar_audio_sequence(grammar_question_parts(kind, target_word, english_voice, grammar_voice, prompt_template), log, clip_cache),
                    "oa": option_audio,
                    "fb": {
                        "ok": grammar_audio_sequence([("Đúng rồi.", grammar_voice)], log, clip_cache),
                        "wrong": grammar_audio_sequence([("Chưa đúng. Hãy chọn lại.", grammar_voice)], log, clip_cache),
                    },
                }
            )
    if callable(log) and items:
        log(f"Nhung audio hoi spaCy: {len(items)} cau ngu phap | toi da hoi {GRAMMAR_MAX_QUESTIONS} cau")
    return items


def build_embedded_audio_assets(text: str, tokens: list[dict], voices: list[dict], log) -> list[list]:
    voice_rows = []
    seen = set()
    for voice in list(voices or []):
        raw_key = clean_text(voice.get("key") if isinstance(voice, dict) else voice)
        key = normalize_audio_voice_key(raw_key)
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        label = embedded_voice_label(key, clean_text(voice.get("label") if isinstance(voice, dict) else ""))
        voice_rows.append((key, label))

    def build_one_audio_asset(key: str, label: str) -> list:
        audio_bytes, mime = synthesize_embedded_audio(text, key, log)
        if not audio_bytes:
            raise RuntimeError("empty audio")
        duration = audio_duration_ms(audio_bytes, mime)
        if duration <= 0:
            duration = estimate_duration_ms(text, tokens)
        timings = build_audio_guided_timings(tokens, duration, audio_bytes) or build_timings(tokens, duration)
        try:
            sample_path = write_voice_sample_cache(key, label, audio_bytes, mime, text)
            if callable(log):
                log(f"Cache sample voice: {label} -> {sample_path.name}")
        except Exception as sample_exc:
            if callable(log):
                log(f"Khong cache duoc sample {label}: {sample_exc}")
        asset_id = hashlib.sha1((key + "\0").encode("utf-8") + audio_bytes[:65536]).hexdigest()[:12]
        asset_path = write_server_sound_asset(f"voice-{key}-{text[:32]}", audio_bytes, mime)
        if callable(log):
            log(f"Luu audio server: {label} | {duration} ms | {asset_path}")
        return [
            asset_id,
            label,
            mime,
            "",
            timings,
            int(duration),
            key,
            asset_path,
        ]

    workers = builder_audio_parallel_workers(len(voice_rows))
    if workers > 1 and voice_rows:
        if callable(log):
            log(f"Parallel Space_W audio: {len(voice_rows)} clips | workers {workers}")
        assets_by_index: dict[int, list] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(build_one_audio_asset, key, label): (index, key, label)
                for index, (key, label) in enumerate(voice_rows)
            }
            for future in as_completed(future_map):
                index, _key, label = future_map[future]
                try:
                    assets_by_index[index] = future.result()
                except Exception as exc:
                    if callable(log):
                        log(f"Bo qua audio {label}: {exc}")
        return [assets_by_index[index] for index in range(len(voice_rows)) if index in assets_by_index]

    assets = []
    for key, label in voice_rows:
        try:
            assets.append(build_one_audio_asset(key, label))
        except Exception as exc:
            if callable(log):
                log(f"Bo qua audio {label}: {exc}")
    return assets


def parse_lesson_entry(line: str) -> dict[str, str]:
    raw = clean_text(line)
    if not raw:
        return {"en": "", "hint": "", "meaning": "", "about": [], "practice": []}
    if "|" not in raw:
        return {"en": raw, "hint": "", "meaning": "", "about": [], "practice": []}
    parts = [clean_text(part) for part in raw.split("|")]
    if len(parts) >= 3:
        return {"en": parts[0], "meaning": parts[1], "hint": " | ".join(parts[2:]), "about": [], "practice": []}
    sentence, hint = raw.split("|", 1)
    return {"en": clean_text(sentence), "hint": clean_text(hint), "meaning": "", "about": [], "practice": []}


def normalize_practice_entries(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    entries: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            entry = {
                "en": clean_text(item.get("en") or item.get("sentence") or item.get("text") or item.get("e") or ""),
                "hint": clean_text(item.get("hint") or item.get("guide") or item.get("note") or item.get("h") or ""),
                "meaning": clean_text(item.get("meaning") or item.get("vi") or item.get("mn") or item.get("q") or ""),
                "about": normalize_about_entries(item.get("about") or item.get("ab") or item.get("qa") or item.get("info")),
            }
        else:
            entry = parse_lesson_entry(str(item or ""))
        if entry.get("en"):
            entries.append(entry)
    return entries


def normalize_lesson_entry(entry) -> dict:
    if isinstance(entry, dict):
        return {
            "en": clean_text(entry.get("en") or entry.get("sentence") or entry.get("text") or ""),
            "hint": clean_text(entry.get("hint") or entry.get("guide") or entry.get("note") or ""),
            "meaning": clean_text(entry.get("meaning") or entry.get("vi") or entry.get("mn") or entry.get("q") or ""),
            "about": normalize_about_entries(entry.get("about") or entry.get("ab") or entry.get("qa") or entry.get("info")),
            "practice": normalize_practice_entries(
                entry.get("practice")
                or entry.get("extra_practice")
                or entry.get("extraPractice")
                or entry.get("supplemental")
                or entry.get("supplemental_sentences")
                or entry.get("xp")
                or entry.get("train")
                or entry.get("training")
            ),
        }
    return parse_lesson_entry(str(entry or ""))


def lesson_entry_sentence(entry) -> str:
    return normalize_lesson_entry(entry).get("en", "")


def build_node(
    sentence: str,
    voice_key: str,
    embedded_voices: list[dict],
    grammar_voice_key: str,
    log,
    grammar_audio_cache: dict[tuple[str, str], list] | None = None,
    hint: str = "",
    meaning: str = "",
    about: list[dict[str, str]] | None = None,
) -> dict:
    en = clean_text(sentence)
    if not en:
        raise ValueError("Cau rong.")
    log(f"Phan tich: {en}")
    vi = clean_text(meaning) or translate_to_vi(en)
    analyzed = analyze_sentence(en)
    tokens = sentence_spans(en, analyzed, voice_key)
    sentence_ipa_us = phonemize_text(en, "en-US")
    sentence_ipa_uk = phonemize_text(en, "en-GB")
    sentence_ipa = sentence_ipa_uk if voice_region(voice_key) == "en-GB" else sentence_ipa_us
    duration = estimate_duration_ms(en, tokens)
    timings = build_timings(tokens, duration)
    audio_assets = build_embedded_audio_assets(en, tokens, embedded_voices, log)
    scoring_words = build_scoring_words(en, tokens, analyzed)
    grammar_cache = grammar_audio_cache if grammar_audio_cache is not None else {}
    question_audio = grammar_audio_sequence([(vi or en, grammar_voice_key)], log, grammar_cache) if (vi or en) else []
    grammar_audio_assets = build_grammar_quiz_audio_assets(scoring_words, voice_key, grammar_voice_key, log, grammar_cache)
    node = {
        "q": vi or en,
        "vq": question_audio,
        "e": en,
        "i": sentence_ipa,
        "iu": sentence_ipa_us or sentence_ipa,
        "ik": sentence_ipa_uk or sentence_ipa,
        "a": [],
        "vc": voice_key,
        "tk": tokens,
        "tm": timings,
        "d": duration,
        "av": audio_assets,
        "an": compact_analysis(analyzed),
        "sc": scoring_words,
        "gq": grammar_audio_assets,
        "mn": vi,
    }
    node_hint = clean_text(hint)
    if node_hint:
        node["hint"] = node_hint
    about_items = normalize_about_entries(about or [])
    if about_items:
        node["ab"] = about_items
    return node


def build_lesson(
    sentences: list[object],
    title: str,
    voice_key: str,
    embedded_voices: list[dict],
    grammar_voice_key: str,
    log,
    practice_voice_key: str | None = None,
    practice_embedded_voices: list[dict] | None = None,
    practice_grammar_voice_key: str | None = None,
) -> dict:
    nodes = []
    grammar_audio_cache: dict[tuple[str, str], list] = {}
    practice_voice = normalize_audio_voice_key(practice_voice_key or voice_key) or normalize_audio_voice_key(voice_key) or "sot:en-US"
    practice_audio_voices = list(embedded_voices if practice_embedded_voices is None else practice_embedded_voices)
    practice_grammar_voice = (
        normalize_audio_voice_key(practice_grammar_voice_key or grammar_voice_key)
        or normalize_audio_voice_key(grammar_voice_key)
        or TRAIN_MODE_VIETNAMESE_VOICE
    )
    entries = [item for item in (normalize_lesson_entry(entry) for entry in sentences) if item.get("en")]
    for index, entry in enumerate(entries, start=1):
        log(f"Node {index}/{len(entries)}")
        node = build_node(
            entry["en"],
            voice_key,
            embedded_voices,
            grammar_voice_key,
            log,
            grammar_audio_cache,
            hint=entry.get("hint", ""),
            meaning=entry.get("meaning", ""),
            about=entry.get("about") if isinstance(entry.get("about"), list) else [],
        )
        practice_entries = normalize_practice_entries(entry.get("practice") if isinstance(entry.get("practice"), list) else [])
        practice_nodes = []
        for practice_index, practice_entry in enumerate(practice_entries, start=1):
            log(f"Practice {index}.{practice_index}/{len(practice_entries)}")
            practice_node = build_node(
                practice_entry["en"],
                practice_voice,
                practice_audio_voices,
                practice_grammar_voice,
                log,
                grammar_audio_cache,
                hint=practice_entry.get("hint", ""),
                meaning=practice_entry.get("meaning", ""),
                about=practice_entry.get("about") if isinstance(practice_entry.get("about"), list) else [],
            )
            practice_node["tr"] = True
            practice_node["src"] = index - 1
            practice_nodes.append(practice_node)
        if practice_nodes:
            node["xp"] = practice_nodes
        nodes.append(node)
    return {
        "k": "ftg",
        "v": 1,
        "t": clean_text(title),
        "created": int(time.time()),
        "fx": build_effect_sounds(log),
        "gv": normalize_audio_voice_key(grammar_voice_key) or "sot:vi-VN",
        "xv": {
            "vc": practice_voice,
            "gv": practice_grammar_voice,
            "av": practice_audio_voices,
        },
        "st": {"total": 0, "last": "", "users": {}, "history": []},
        "n": nodes,
    }


def resolve_embedded_voice_specs(manual_voices: list[dict], auto_groups: dict, log=None) -> list[dict]:
    voices: list[dict] = []
    seen: set[str] = set()

    def append_voice(label: str, raw_key: str) -> None:
        key = normalize_audio_voice_key(clean_text(raw_key))
        if not key or key.startswith("__missing_"):
            return
        lowered = key.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        voices.append({"label": clean_text(label) or embedded_voice_label(key), "key": key})

    for voice in list(manual_voices or []):
        if not isinstance(voice, dict):
            append_voice("", str(voice or ""))
            continue
        append_voice(clean_text(voice.get("label")), clean_text(voice.get("key")))

    groups = dict(auto_groups or {})
    if groups.get("sot"):
        before = len(voices)
        for label, key in sound_of_text_voice_specs():
            append_voice(label, key)
        if callable(log):
            log(f"Auto Sound of Text: +{len(voices) - before}")
    if groups.get("edge"):
        before = len(voices)
        for label, key in edge_english_voice_specs(force_refresh=False):
            append_voice(label, key)
        if callable(log):
            log(f"Auto Edge TTS English: +{len(voices) - before}")
    if groups.get("microsoft"):
        before = len(voices)
        for label, key in microsoft_voice_specs(force_refresh=False):
            append_voice(label, key)
        if callable(log):
            log(f"Auto Microsoft: +{len(voices) - before}")
    if groups.get("people"):
        before = len(voices)
        for label, key in people_voice_specs():
            append_voice(label, key)
        if callable(log):
            log(f"Auto People: +{len(voices) - before}")
    return voices


class GenerateWorker(QThread):
    log_message = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal(str, int)

    def __init__(
        self,
        sentences: list[object],
        title: str,
        voice: str,
        embedded_voices: list[dict],
        auto_groups: dict,
        grammar_voice: str,
        output_path: Path,
        train_voice: str = TRAIN_MODE_PRIMARY_VOICE,
        train_embedded_voices: list[dict] | None = None,
        train_grammar_voice: str = TRAIN_MODE_VIETNAMESE_VOICE,
    ) -> None:
        super().__init__()
        self.sentences = list(sentences)
        self.lesson_title = str(title or "")
        self.voice = str(voice or "female-us")
        self.embedded_voices = list(embedded_voices or [])
        self.auto_groups = dict(auto_groups or {})
        self.grammar_voice = str(grammar_voice or "sot:vi-VN")
        self.output_path = Path(output_path)
        self.train_voice = normalize_audio_voice_key(train_voice) or TRAIN_MODE_PRIMARY_VOICE
        self.train_embedded_voices = list(train_embedded_voices or default_train_mode_embedded_voices())
        self.train_grammar_voice = normalize_audio_voice_key(train_grammar_voice) or TRAIN_MODE_VIETNAMESE_VOICE
        self._pending_logs: list[str] = []
        self._last_log_emit = 0.0

    def _log(self, message: str) -> None:
        text = clean_text(message)
        if not text:
            return
        self._pending_logs.append(text)
        now = time.monotonic()
        if len(self._pending_logs) >= 18 or (now - self._last_log_emit) >= 0.16:
            self._flush_logs()

    def _flush_logs(self) -> None:
        if not self._pending_logs:
            return
        self.log_message.emit("\n".join(self._pending_logs))
        self._pending_logs = []
        self._last_log_emit = time.monotonic()

    def run(self) -> None:
        build_session = builder_server2_build_begin("Space_W", self.output_path)
        build_success = False
        try:
            self._log("Dang gom danh sach voice trong thread nen GUI khong bi dung...")
            embedded_voices = resolve_embedded_voice_specs(self.embedded_voices, self.auto_groups, self._log)
            if embedded_voices:
                labels = [item["label"] for item in embedded_voices]
                if len(labels) > 12:
                    self._log(f"Embedded voices ({len(labels)}): " + ", ".join(labels[:12]) + " ...")
                else:
                    self._log("Embedded voices: " + ", ".join(labels))
            else:
                self._log("Embedded voices: none")
            self._log(f"Voice hoi spaCy tieng Viet: {embedded_voice_label(self.grammar_voice)}")
            train_embedded_voices = resolve_embedded_voice_specs(self.train_embedded_voices, {}, self._log)
            if not train_embedded_voices:
                train_embedded_voices = default_train_mode_embedded_voices()
            self._log(
                "Train mode voices: "
                + ", ".join(item["label"] for item in train_embedded_voices)
                + f" | Vietnamese: {embedded_voice_label(self.train_grammar_voice)}"
            )
            payload = build_lesson(
                self.sentences,
                self.lesson_title,
                self.voice,
                embedded_voices,
                self.grammar_voice,
                self._log,
                practice_voice_key=self.train_voice,
                practice_embedded_voices=train_embedded_voices,
                practice_grammar_voice_key=self.train_grammar_voice,
            )
            manifest = encode_future_manifest(payload, self.lesson_title, self.output_path, "Space_W")
            self.output_path.write_text(manifest, encoding="utf-8")
            self._flush_logs()
            self.finished_ok.emit(str(self.output_path), len(payload.get("n", [])))
            build_success = True
        except Exception as exc:
            self._flush_logs()
            self.failed.emit(str(exc))
        finally:
            builder_server2_build_end(build_session, "Space_W", self.output_path, build_success)


class PreviewVoiceWorker(QThread):
    log_message = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal(str, str)

    def __init__(self, text: str, voice_key: str, label: str) -> None:
        super().__init__()
        self.text = clean_text(text) or VOICE_SAMPLE_TEXT
        self.voice_key = normalize_audio_voice_key(voice_key)
        self.label = clean_text(label) or embedded_voice_label(self.voice_key)

    def _log(self, message: str) -> None:
        self.log_message.emit(clean_text(message))

    def run(self) -> None:
        try:
            if not self.voice_key or self.voice_key.startswith("__missing_"):
                raise RuntimeError("Voice nay chua san sang de nghe thu.")
            audio_bytes, mime = synthesize_embedded_audio(self.text, self.voice_key, self._log)
            if not audio_bytes:
                raise RuntimeError("Voice khong tao duoc audio mau.")
            path = write_voice_sample_cache(self.voice_key, self.label, audio_bytes, mime, self.text)
            self.finished_ok.emit(str(path), self.label)
        except Exception as exc:
            self.failed.emit(str(exc))


class WarmCacheWorker(QThread):
    log_message = pyqtSignal(str)

    def __init__(self, warm_vibevoice: bool = False, warm_base: bool = True) -> None:
        super().__init__()
        self.warm_vibevoice = bool(warm_vibevoice)
        self.warm_base = bool(warm_base)

    def _log(self, message: str) -> None:
        self.log_message.emit(clean_text(message))

    def run(self) -> None:
        if self.warm_base:
            self._log("Warm spaCy / analysis cache...")
            try:
                analyze_sentence("This is a warm up sentence.")
                phonemize_text("This is a warm up sentence.", "en-US")
                phonemize_text("This is a warm up sentence.", "en-GB")
                self._log("spaCy / phonemize ready.")
            except Exception as exc:
                self._log(f"spaCy / phonemize warm skipped: {exc}")
            self._log("Warm Edge TTS catalog...")
            try:
                from module_main.edge_tts_service import list_edge_voices, synthesize_edge_tts_bytes

                list_edge_voices(force_refresh=False)
                synthesize_edge_tts_bytes("Hello.", "edge:en-US-AriaNeural", speed_percent=92)
                self._log("Edge TTS catalog ready.")
            except Exception as exc:
                self._log(f"Edge TTS warm skipped: {exc}")
        if not self.warm_vibevoice:
            self._log("VibeVoice warm skipped: disabled in Future builders.")
            return
        self._log("VibeVoice warm skipped: disabled in Future builders.")


class AboutEntriesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, entries: list[dict[str, str]] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About this sentence")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setSizeGripEnabled(True)
        self.resize(1180, 760)
        self.setMinimumSize(860, 560)
        self._entries = normalize_about_entries(entries or [])
        self._answer_highlights: list[dict[str, object]] = []
        self._loading = False
        self._build_ui()
        self._apply_style()
        self._reload_list()
        if self.entry_list.count():
            self.entry_list.setCurrentRow(0)
        QTimer.singleShot(0, self.showMaximized)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Expert Q&A nodes")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Add question and explanation cards that appear after the learner answers this Space_W node correctly.")
        subtitle.setObjectName("DialogSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.entry_list = QListWidget()
        self.entry_list.setMinimumWidth(230)
        self.entry_list.currentRowChanged.connect(self._load_current_entry)
        body.addWidget(self.entry_list, 1)

        editor = QVBoxLayout()
        editor.setSpacing(8)
        editor.addWidget(QLabel("Question"))
        self.question_edit = QPlainTextEdit()
        self.question_edit.setPlaceholderText("Example: Why is 'would like' used in this sentence?")
        self.question_edit.setMinimumHeight(120)
        editor.addWidget(self.question_edit)
        editor.addWidget(QLabel("Explanation"))
        self.answer_edit = QPlainTextEdit()
        self.answer_edit.setPlaceholderText("Explain the answer like an expert, in Vietnamese or English.")
        self.answer_edit.setMinimumHeight(360)
        editor.addWidget(self.answer_edit, 1)

        highlight_head = QHBoxLayout()
        highlight_label = QLabel("Colored explanation segments")
        self.color_selection_button = QPushButton("Color selected text")
        self.remove_color_button = QPushButton("Remove color")
        highlight_head.addWidget(highlight_label)
        highlight_head.addStretch(1)
        highlight_head.addWidget(self.color_selection_button)
        highlight_head.addWidget(self.remove_color_button)
        editor.addLayout(highlight_head)
        self.highlight_list = QListWidget()
        self.highlight_list.setMaximumHeight(96)
        editor.addWidget(self.highlight_list)

        tool_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.update_button = QPushButton("Update")
        self.delete_button = QPushButton("Delete")
        self.up_button = QPushButton("Up")
        self.down_button = QPushButton("Down")
        tool_row.addWidget(self.add_button)
        tool_row.addWidget(self.update_button)
        tool_row.addWidget(self.delete_button)
        tool_row.addStretch(1)
        tool_row.addWidget(self.up_button)
        tool_row.addWidget(self.down_button)
        editor.addLayout(tool_row)
        body.addLayout(editor, 2)
        layout.addLayout(body, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.setObjectName("PrimaryButton")
        action_row.addWidget(self.ok_button)
        action_row.addWidget(self.cancel_button)
        layout.addLayout(action_row)

        self.add_button.clicked.connect(self._add_entry)
        self.update_button.clicked.connect(self._update_entry)
        self.delete_button.clicked.connect(self._delete_entry)
        self.up_button.clicked.connect(lambda: self._move_entry(-1))
        self.down_button.clicked.connect(lambda: self._move_entry(1))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.color_selection_button.clicked.connect(self._color_selected_answer_text)
        self.remove_color_button.clicked.connect(self._remove_selected_highlight)
        self.answer_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.answer_edit.customContextMenuRequested.connect(self._show_answer_context_menu)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #061112;
                color: #effefa;
                font-family: "Segoe UI";
            }
            QLabel#DialogTitle {
                color: #46f0d7;
                font-size: 22px;
                font-weight: 900;
            }
            QLabel#DialogSubtitle {
                color: #9fc7c0;
                font-size: 12px;
                font-weight: 650;
            }
            QPlainTextEdit, QListWidget {
                color: #effefa;
                border: 1px solid rgba(70, 240, 215, 0.32);
                border-radius: 12px;
                background: rgba(4, 17, 20, 220);
                selection-background-color: rgba(70, 240, 215, 0.36);
            }
            QListWidget::item {
                min-height: 54px;
                padding: 8px;
                border-bottom: 1px solid rgba(70, 240, 215, 0.12);
            }
            QListWidget::item:selected {
                color: #ffffff;
                background: rgba(70, 240, 215, 0.22);
                border-left: 3px solid #46f0d7;
            }
            QPushButton {
                color: #effefa;
                border: 1px solid rgba(70, 240, 215, 0.34);
                border-radius: 10px;
                padding: 8px 12px;
                background: rgba(14, 41, 43, 225);
                font-weight: 850;
            }
            QPushButton:hover {
                border-color: rgba(108, 240, 164, 0.65);
                background: rgba(24, 71, 67, 235);
            }
            QPushButton#PrimaryButton {
                color: #051313;
                background: #46f0d7;
                border-color: #46f0d7;
            }
            """
        )

    def _entry_label(self, entry: dict[str, str], index: int) -> str:
        question = clean_text(entry.get("q")) or "(question empty)"
        answer = clean_text(entry.get("a"))
        highlight_count = len(normalize_about_highlights(entry.get("ah") or entry.get("answer_highlights") or entry.get("hl")))
        suffix = "explanation: set" if answer else "explanation: empty"
        if highlight_count:
            suffix += f" | colors: {highlight_count}"
        return f"{index + 1:02d}. {question}\n  {suffix}"

    def _reload_list(self) -> None:
        row = self.entry_list.currentRow()
        self.entry_list.clear()
        for index, entry in enumerate(self._entries):
            item = QListWidgetItem(self._entry_label(entry, index))
            item.setToolTip(f"Question: {entry.get('q', '')}\nExplanation: {entry.get('a', '')}")
            self.entry_list.addItem(item)
        if self.entry_list.count():
            self.entry_list.setCurrentRow(max(0, min(row, self.entry_list.count() - 1)))

    def _load_current_entry(self, row: int) -> None:
        self._loading = True
        try:
            entry = self._entries[row] if 0 <= row < len(self._entries) else {"q": "", "a": ""}
            self.question_edit.setPlainText(entry.get("q", ""))
            self.answer_edit.setPlainText(entry.get("a", ""))
            self._answer_highlights = normalize_about_highlights(entry.get("ah") or entry.get("answer_highlights") or entry.get("hl"))
            self._reload_highlight_list()
            self._apply_answer_highlight_preview()
        finally:
            self._loading = False

    def _editor_entry(self) -> dict[str, str]:
        highlights = normalize_about_highlights(self._answer_highlights)
        entry = {
            "q": clean_log_text(self.question_edit.toPlainText()),
            "a": clean_log_text(self.answer_edit.toPlainText()),
        }
        if highlights:
            entry["ah"] = highlights
        return entry

    def _commit_current_editor(self, refresh: bool = False) -> None:
        if self._loading:
            return
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        entry = self._editor_entry()
        if not entry["q"] and not entry["a"]:
            return
        self._entries[row] = entry
        if refresh:
            self._reload_list()
            self.entry_list.setCurrentRow(row)

    def _reload_highlight_list(self) -> None:
        self.highlight_list.clear()
        for index, item in enumerate(normalize_about_highlights(self._answer_highlights), start=1):
            label = clean_text(item.get("t") or f"{item.get('s', '')}:{item.get('e', '')}") or "(segment)"
            color = normalize_hex_color(item.get("c"))
            occurrence = int(item.get("n") or 1)
            row = QListWidgetItem(f"{index:02d}. {label}\n  {color} | occurrence {occurrence}")
            row.setToolTip(label)
            row.setForeground(QColor(color))
            self.highlight_list.addItem(row)

    def _apply_answer_highlight_preview(self) -> None:
        selections = []
        raw = self.answer_edit.toPlainText()
        for item in normalize_about_highlights(self._answer_highlights):
            text = clean_log_text(item.get("t") or "")
            if not text:
                continue
            occurrence = max(1, int(item.get("n") or 1))
            start = -1
            cursor_pos = 0
            for _idx in range(occurrence):
                start = raw.find(text, cursor_pos)
                if start < 0:
                    break
                cursor_pos = start + len(text)
            if start < 0:
                start = raw.find(text)
            if start < 0:
                continue
            end = start + len(text)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(self.answer_edit.document())
            selection.cursor.setPosition(start)
            selection.cursor.setPosition(end, QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            color = QColor(normalize_hex_color(item.get("c")))
            fmt.setForeground(color)
            fmt.setBackground(QColor(color.red(), color.green(), color.blue(), 42))
            fmt.setFontWeight(QFont.Bold)
            selection.format = fmt
            selections.append(selection)
        self.answer_edit.setExtraSelections(selections)

    def _show_answer_context_menu(self, pos) -> None:
        menu = self.answer_edit.createStandardContextMenu()
        menu.addSeparator()
        action = menu.addAction("Color selected explanation")
        action.triggered.connect(self._color_selected_answer_text)
        menu.exec_(self.answer_edit.mapToGlobal(pos))

    def _color_selected_answer_text(self) -> None:
        cursor = self.answer_edit.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, APP_TITLE, "Hay boi den mot doan trong Explanation truoc.")
            return
        selected = clean_log_text(cursor.selectedText().replace("\u2029", "\n"))
        if not selected:
            return
        color = QColorDialog.getColor(QColor("#ffff00"), self, "Choose highlight color")
        if not color.isValid():
            return
        raw = self.answer_edit.toPlainText()
        before = raw[: min(cursor.selectionStart(), cursor.selectionEnd())]
        before_clean = clean_log_text(before)
        occurrence = before_clean.count(selected) + 1
        self._answer_highlights.append({
            "t": selected,
            "n": max(1, occurrence),
            "c": color.name(),
        })
        self._reload_highlight_list()
        self._apply_answer_highlight_preview()
        self._commit_current_editor(refresh=True)

    def _remove_selected_highlight(self) -> None:
        row = self.highlight_list.currentRow()
        if 0 <= row < len(self._answer_highlights):
            self._answer_highlights.pop(row)
            self._reload_highlight_list()
            self._apply_answer_highlight_preview()

    def _add_entry(self) -> None:
        entry = self._editor_entry()
        if not entry["q"] and not entry["a"]:
            return
        self._entries.append(entry)
        self._reload_list()
        self.entry_list.setCurrentRow(len(self._entries) - 1)

    def _update_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            self._add_entry()
            return
        entry = self._editor_entry()
        if not entry["q"] and not entry["a"]:
            return
        self._entries[row] = entry
        self._reload_list()
        self.entry_list.setCurrentRow(row)

    def _delete_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        self._entries.pop(row)
        self._reload_list()
        if self.entry_list.count():
            self.entry_list.setCurrentRow(min(row, self.entry_list.count() - 1))
        else:
            self.question_edit.clear()
            self.answer_edit.clear()
            self._answer_highlights = []
            self._reload_highlight_list()
            self._apply_answer_highlight_preview()

    def _move_entry(self, direction: int) -> None:
        row = self.entry_list.currentRow()
        target = row + int(direction)
        if row < 0 or target < 0 or row >= len(self._entries) or target >= len(self._entries):
            return
        self._entries[row], self._entries[target] = self._entries[target], self._entries[row]
        self._reload_list()
        self.entry_list.setCurrentRow(target)

    def entries(self) -> list[dict[str, str]]:
        self._commit_current_editor(refresh=False)
        return normalize_about_entries(self._entries)

    def accept(self) -> None:
        self._commit_current_editor(refresh=False)
        super().accept()


class PracticeEntriesDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, entries: list[dict] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bổ sung câu cùng chủ đề")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setSizeGripEnabled(True)
        self.resize(1180, 760)
        self.setMinimumSize(860, 560)
        self._entries = normalize_practice_entries(entries or [])
        self._loading = False
        self._build_ui()
        self._apply_style()
        self._reload_list()
        if self.entry_list.count():
            self.entry_list.setCurrentRow(0)
        QTimer.singleShot(0, self.showMaximized)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Bổ sung câu cùng chủ đề")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Thêm nhiều câu luyện extra. Khi build, mỗi câu sẽ có dịch tiếng Việt, hint, audio, spaCy, IPA và chấm giọng như node gốc.")
        subtitle.setObjectName("DialogSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.entry_list = QListWidget()
        self.entry_list.setMinimumWidth(280)
        self.entry_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.entry_list.currentRowChanged.connect(self._load_current_entry)
        self.entry_list.customContextMenuRequested.connect(self._open_entry_context_menu)
        body.addWidget(self.entry_list, 1)

        editor = QVBoxLayout()
        editor.setSpacing(8)
        editor.addWidget(QLabel("English sentence"))
        self.sentence_edit = QPlainTextEdit()
        self.sentence_edit.setPlaceholderText("Example: I usually have dinner with my family on Sundays.")
        self.sentence_edit.setMinimumHeight(120)
        editor.addWidget(self.sentence_edit)

        editor.addWidget(QLabel("Vietnamese meaning"))
        self.meaning_edit = QPlainTextEdit()
        self.meaning_edit.setPlaceholderText("Có thể bỏ trống. Khi build, phần mềm sẽ tự dịch bằng translate_to_vi().")
        self.meaning_edit.setMinimumHeight(120)
        editor.addWidget(self.meaning_edit)

        editor.addWidget(QLabel("Hint"))
        self.hint_edit = QPlainTextEdit()
        self.hint_edit.setPlaceholderText("Gợi ý cho người học, ví dụ: Chú ý cụm usually + verb và on Sundays.")
        self.hint_edit.setMinimumHeight(160)
        editor.addWidget(self.hint_edit, 1)

        tool_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.update_button = QPushButton("Update")
        self.about_button = QPushButton("About...")
        self.delete_button = QPushButton("Delete")
        self.up_button = QPushButton("Up")
        self.down_button = QPushButton("Down")
        tool_row.addWidget(self.add_button)
        tool_row.addWidget(self.update_button)
        tool_row.addWidget(self.about_button)
        tool_row.addWidget(self.delete_button)
        tool_row.addStretch(1)
        tool_row.addWidget(self.up_button)
        tool_row.addWidget(self.down_button)
        editor.addLayout(tool_row)
        body.addLayout(editor, 2)
        layout.addLayout(body, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.setObjectName("PrimaryButton")
        action_row.addWidget(self.ok_button)
        action_row.addWidget(self.cancel_button)
        layout.addLayout(action_row)

        self.add_button.clicked.connect(self._add_entry)
        self.update_button.clicked.connect(self._update_entry)
        self.about_button.clicked.connect(self._edit_current_about)
        self.delete_button.clicked.connect(self._delete_entry)
        self.up_button.clicked.connect(lambda: self._move_entry(-1))
        self.down_button.clicked.connect(lambda: self._move_entry(1))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #061112;
                color: #effefa;
                font-family: "Segoe UI";
            }
            QLabel#DialogTitle {
                color: #46f0d7;
                font-size: 22px;
                font-weight: 900;
            }
            QLabel#DialogSubtitle {
                color: #9fc7c0;
                font-size: 12px;
                font-weight: 650;
            }
            QPlainTextEdit, QListWidget {
                color: #effefa;
                border: 1px solid rgba(70, 240, 215, 0.32);
                border-radius: 12px;
                background: rgba(4, 17, 20, 220);
                selection-background-color: rgba(70, 240, 215, 0.36);
            }
            QListWidget::item {
                min-height: 58px;
                padding: 8px;
                border-bottom: 1px solid rgba(70, 240, 215, 0.12);
            }
            QListWidget::item:selected {
                color: #ffffff;
                background: rgba(70, 240, 215, 0.22);
                border-left: 3px solid #46f0d7;
            }
            QPushButton {
                color: #effefa;
                border: 1px solid rgba(70, 240, 215, 0.34);
                border-radius: 10px;
                padding: 8px 12px;
                background: rgba(14, 41, 43, 225);
                font-weight: 850;
            }
            QPushButton:hover {
                border-color: rgba(108, 240, 164, 0.65);
                background: rgba(24, 71, 67, 235);
            }
            QPushButton#PrimaryButton {
                color: #051313;
                background: #46f0d7;
                border-color: #46f0d7;
            }
            """
        )

    def _entry_label(self, entry: dict, index: int) -> str:
        sentence = clean_text(entry.get("en")) or "(empty sentence)"
        meaning = clean_text(entry.get("meaning"))
        hint = clean_text(entry.get("hint"))
        about_count = len(normalize_about_entries(entry.get("about")))
        badges = ["meaning: set" if meaning else "meaning: auto translate"]
        if hint:
            badges.append("hint: set")
        if about_count:
            badges.append(f"about: {about_count}")
        return f"{index + 1:02d}. {sentence}\n  " + "  |  ".join(badges)

    def _reload_list(self) -> None:
        row = self.entry_list.currentRow()
        self.entry_list.clear()
        for index, entry in enumerate(self._entries):
            item = QListWidgetItem(self._entry_label(entry, index))
            item.setToolTip(
                f"English: {entry.get('en', '')}\n"
                f"Meaning: {entry.get('meaning', '') or '(auto translate when build)'}\n"
                f"Hint: {entry.get('hint', '') or '(none)'}\n"
                f"About cards: {len(normalize_about_entries(entry.get('about')))}"
            )
            self.entry_list.addItem(item)
        if self.entry_list.count():
            self.entry_list.setCurrentRow(max(0, min(row, self.entry_list.count() - 1)))

    def _load_current_entry(self, row: int) -> None:
        self._loading = True
        try:
            entry = self._entries[row] if 0 <= row < len(self._entries) else {"en": "", "meaning": "", "hint": ""}
            self.sentence_edit.setPlainText(entry.get("en", ""))
            self.meaning_edit.setPlainText(entry.get("meaning", ""))
            self.hint_edit.setPlainText(entry.get("hint", ""))
        finally:
            self._loading = False

    def _editor_entry(self, base: dict | None = None) -> dict:
        return {
            "en": clean_log_text(self.sentence_edit.toPlainText()),
            "meaning": clean_log_text(self.meaning_edit.toPlainText()),
            "hint": clean_log_text(self.hint_edit.toPlainText()),
            "about": normalize_about_entries((base or {}).get("about")),
        }

    def _commit_current_editor(self, refresh: bool = False) -> None:
        if self._loading:
            return
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        entry = self._editor_entry(self._entries[row])
        if not entry["en"]:
            return
        self._entries[row] = entry
        if refresh:
            self._reload_list()
            self.entry_list.setCurrentRow(row)

    def _add_entry(self) -> None:
        entry = self._editor_entry()
        if not entry["en"]:
            return
        self._entries.append(entry)
        self._reload_list()
        self.entry_list.setCurrentRow(len(self._entries) - 1)

    def _update_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            self._add_entry()
            return
        entry = self._editor_entry(self._entries[row])
        if not entry["en"]:
            return
        self._entries[row] = entry
        self._reload_list()
        self.entry_list.setCurrentRow(row)

    def _open_entry_context_menu(self, position) -> None:
        item = self.entry_list.itemAt(position)
        if item is None:
            return
        row = self.entry_list.row(item)
        if row < 0 or row >= len(self._entries):
            return
        self.entry_list.setCurrentRow(row)
        menu = QMenu(self)
        about_action = menu.addAction("Add / edit About cards")
        selected = menu.exec_(self.entry_list.mapToGlobal(position))
        if selected == about_action:
            self._edit_entry_about(row)

    def _edit_current_about(self) -> None:
        self._edit_entry_about(self.entry_list.currentRow())

    def _edit_entry_about(self, row: int) -> None:
        self._commit_current_editor(refresh=False)
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        dialog = AboutEntriesDialog(self, normalize_about_entries(entry.get("about")))
        if dialog.exec_() != QDialog.Accepted:
            return
        self._entries[row] = {
            **entry,
            "about": dialog.entries(),
        }
        self._reload_list()
        self.entry_list.setCurrentRow(row)

    def _delete_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        self._entries.pop(row)
        self._reload_list()
        if self.entry_list.count():
            self.entry_list.setCurrentRow(min(row, self.entry_list.count() - 1))
        else:
            self.sentence_edit.clear()
            self.meaning_edit.clear()
            self.hint_edit.clear()

    def _move_entry(self, direction: int) -> None:
        row = self.entry_list.currentRow()
        target = row + int(direction)
        if row < 0 or target < 0 or row >= len(self._entries) or target >= len(self._entries):
            return
        self._entries[row], self._entries[target] = self._entries[target], self._entries[row]
        self._reload_list()
        self.entry_list.setCurrentRow(target)

    def entries(self) -> list[dict]:
        self._commit_current_editor(refresh=False)
        return normalize_practice_entries(self._entries)

    def accept(self) -> None:
        self._commit_current_editor(refresh=False)
        super().accept()


class FutureLessonBuilder(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: GenerateWorker | None = None
        self.preview_worker: PreviewVoiceWorker | None = None
        self.warm_worker: WarmCacheWorker | None = None
        self._audio_player = QMediaPlayer(self) if QMediaPlayer is not None else None
        self._pending_log_lines: list[str] = []
        self._loading_settings = False
        self._pending_vibe_warm = False
        self._log_timer = QTimer(self)
        self._log_timer.setSingleShot(True)
        self._log_timer.setInterval(85)
        self._log_timer.timeout.connect(self._flush_log_buffer)
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 720)
        self.setMinimumSize(640, 460)
        self._build_ui()
        self._start_warm_cache()

    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root = QWidget()
        root.setObjectName("BuilderRoot")
        root.setMinimumWidth(720)
        scroll_area.setWidget(root)
        self.setCentralWidget(scroll_area)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(6)
        title = QLabel("Future Lesson Builder")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Generate FTG1 lesson files with translation, IPA, spaCy token analysis, and reading highlights.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        config_card = QFrame()
        config_card.setObjectName("Card")
        config_layout = QGridLayout(config_card)
        config_layout.setContentsMargins(18, 16, 18, 16)
        config_layout.setHorizontalSpacing(12)
        config_layout.setVerticalSpacing(10)

        self.title_input = QLineEdit("Future lesson")
        self.title_input.setPlaceholderText("Lesson title")
        self.voice_combo = QComboBox()
        for label, key in communication_voice_options():
            row = self.voice_combo.count()
            self.voice_combo.addItem(label, key)
            if str(key or "").startswith("__missing_"):
                item = self.voice_combo.model().item(row)
                if item is not None:
                    item.setEnabled(False)
        us_index = self.voice_combo.findData("sot:en-US")
        if us_index < 0:
            us_index = self.voice_combo.findData("female-us")
        if us_index >= 0:
            self.voice_combo.setCurrentIndex(us_index)
        self.grammar_voice_combo = QComboBox()
        for label, key in grammar_vietnamese_voice_specs():
            self.grammar_voice_combo.addItem(label, key)
        vi_index = self.grammar_voice_combo.findData(TRAIN_MODE_VIETNAMESE_VOICE)
        if vi_index < 0:
            vi_index = self.grammar_voice_combo.findData("sot:vi-VN")
        if vi_index >= 0:
            self.grammar_voice_combo.setCurrentIndex(vi_index)
        self.train_voice_combo = QComboBox()
        for label, key in train_mode_english_voice_specs():
            self.train_voice_combo.addItem(label, key)
        train_voice_index = self.train_voice_combo.findData(TRAIN_MODE_PRIMARY_VOICE)
        if train_voice_index >= 0:
            self.train_voice_combo.setCurrentIndex(train_voice_index)
        self.train_grammar_voice_combo = QComboBox()
        for label, key in train_mode_vietnamese_voice_specs():
            self.train_grammar_voice_combo.addItem(label, key)
        train_vi_index = self.train_grammar_voice_combo.findData(TRAIN_MODE_VIETNAMESE_VOICE)
        if train_vi_index >= 0:
            self.train_grammar_voice_combo.setCurrentIndex(train_vi_index)
        self.train_voice_summary = QLabel("Train mode embeds English audio with People | Male Adam and People | Female Jessica.")
        self.train_voice_summary.setWordWrap(True)
        self.add_voice_button = QPushButton("Add")
        self.remove_voice_button = QPushButton("Remove")
        self.preview_voice_button = QPushButton("Preview")
        self.embedded_voice_list = QListWidget()
        self.embedded_voice_list.setMinimumHeight(86)
        self.embedded_voice_list.setAlternatingRowColors(False)
        self.auto_sot_check = QCheckBox("All Sound of Text")
        self.auto_edge_check = QCheckBox("All Edge TTS English")
        self.auto_microsoft_check = QCheckBox("All Microsoft online")
        self.auto_people_check = QCheckBox("All People")
        self.warm_vibevoice_check = QCheckBox("Warm VibeVoice")
        self.auto_sot_check.setToolTip("Embed all Sound of Text English voices into the Space_W file.")
        self.auto_edge_check.setToolTip("Embed the full English Edge TTS catalog into the Space_W file.")
        self.auto_microsoft_check.setToolTip("Embed Microsoft online English voices into the Space_W file. Local SAPI English voices are included if Windows exposes them.")
        self.auto_people_check.setToolTip("Embed People/Kokoro voices. VibeVoice is not included here.")
        self.warm_vibevoice_check.setToolTip("VibeVoice is disabled in Future builders.")
        self.warm_vibevoice_check.setChecked(False)
        self.warm_vibevoice_check.setEnabled(False)
        self.warm_vibevoice_check.setVisible(False)

        config_layout.addWidget(QLabel("Lesson name"), 0, 0)
        config_layout.addWidget(self.title_input, 1, 0)
        config_layout.addWidget(QLabel("Voice source"), 0, 1)
        voice_row = QHBoxLayout()
        voice_row.setSpacing(8)
        voice_row.addWidget(self.voice_combo, 1)
        voice_row.addWidget(self.preview_voice_button)
        voice_row.addWidget(self.add_voice_button)
        voice_row.addWidget(self.remove_voice_button)
        config_layout.addLayout(voice_row, 1, 1)
        config_layout.addWidget(QLabel("Embedded voices in Space_W"), 2, 0, 1, 2)
        config_layout.addWidget(self.embedded_voice_list, 3, 0, 1, 2)
        auto_voice_row = QHBoxLayout()
        auto_voice_row.setSpacing(12)
        auto_voice_row.addWidget(self.auto_sot_check)
        auto_voice_row.addWidget(self.auto_edge_check)
        auto_voice_row.addWidget(self.auto_microsoft_check)
        auto_voice_row.addWidget(self.auto_people_check)
        auto_voice_row.addWidget(self.warm_vibevoice_check)
        auto_voice_row.addStretch(1)
        config_layout.addWidget(QLabel("Auto embed groups"), 4, 0, 1, 2)
        config_layout.addLayout(auto_voice_row, 5, 0, 1, 2)
        config_layout.addWidget(QLabel("SpaCy quiz Vietnamese voice"), 6, 0, 1, 2)
        config_layout.addWidget(self.grammar_voice_combo, 7, 0, 1, 2)
        config_layout.addWidget(QLabel("Train mode English primary voice"), 8, 0)
        config_layout.addWidget(self.train_voice_combo, 9, 0)
        config_layout.addWidget(QLabel("Train mode Vietnamese voice"), 8, 1)
        config_layout.addWidget(self.train_grammar_voice_combo, 9, 1)
        config_layout.addWidget(self.train_voice_summary, 10, 0, 1, 2)
        config_layout.setColumnStretch(0, 2)
        config_layout.setColumnStretch(1, 1)
        layout.addWidget(config_card)

        editor_card = QFrame()
        editor_card.setObjectName("Card")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(18, 16, 18, 16)
        editor_layout.setSpacing(10)
        editor_label = QLabel("Lesson nodes")
        editor_label.setObjectName("SectionLabel")
        node_tools = QHBoxLayout()
        node_tools.setSpacing(8)
        self.node_sentence_input = QLineEdit()
        self.node_sentence_input.setPlaceholderText("Type one English sentence, then Add line")
        self.add_node_button = QPushButton("Add line")
        self.about_node_button = QPushButton("About Q&A")
        self.load_txt_button = QPushButton("Load TXT list")
        self.load_space_w_button = QPushButton("Load Space_W")
        self.new_lesson_button = QPushButton("New")
        node_tools.addWidget(self.node_sentence_input, 1)
        node_tools.addWidget(self.add_node_button)
        node_tools.addWidget(self.about_node_button)
        node_tools.addWidget(self.load_txt_button)
        node_tools.addWidget(self.load_space_w_button)
        node_tools.addWidget(self.new_lesson_button)
        self.node_list = QListWidget()
        self.node_list.setMinimumHeight(220)
        self.node_list.setAlternatingRowColors(False)
        self.node_list.setContextMenuPolicy(Qt.CustomContextMenu)
        editor_layout.addWidget(editor_label)
        editor_layout.addLayout(node_tools)
        editor_layout.addWidget(self.node_list)
        layout.addWidget(editor_card, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.generate_button = QPushButton("Generate Space_W")
        self.generate_button.setObjectName("PrimaryButton")
        self.clear_button = QPushButton("Clear log")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        actions.addWidget(self.generate_button)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.progress)
        layout.addLayout(actions)

        log_card = QFrame()
        log_card.setObjectName("Card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 16, 18, 16)
        log_layout.setSpacing(10)
        log_label = QLabel("Build log")
        log_label.setObjectName("SectionLabel")
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(2500)
        self.log_text.setMinimumHeight(135)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_card)

        self._load_builder_settings()
        if self.node_list.count() == 0:
            self.add_node_entry(
                {"en": "I would like a glass of water.", "meaning": "", "hint": "Remember the polite pattern: would like + noun."},
                save=False,
            )
            self.add_node_entry(
                {"en": "She usually studies English after dinner.", "meaning": "", "hint": "Focus on the adverb of frequency before the main verb."},
                save=False,
            )
        self.generate_button.clicked.connect(self.generate)
        self.clear_button.clicked.connect(self.clear_log)
        self.add_node_button.clicked.connect(self.add_node_from_input)
        self.about_node_button.clicked.connect(lambda: self.edit_node_about(self.node_list.currentItem()))
        self.load_txt_button.clicked.connect(self.load_nodes_from_txt)
        self.load_space_w_button.clicked.connect(self.load_space_w_file)
        self.new_lesson_button.clicked.connect(self.new_lesson)
        self.node_sentence_input.returnPressed.connect(self.add_node_from_input)
        self.node_list.itemDoubleClicked.connect(lambda item: self.edit_node_sentence(item))
        self.node_list.customContextMenuRequested.connect(self.open_node_context_menu)
        self.preview_voice_button.clicked.connect(self.preview_selected_voice)
        self.add_voice_button.clicked.connect(self.add_embedded_voice)
        self.remove_voice_button.clicked.connect(self.remove_selected_embedded_voice)
        self.voice_combo.currentIndexChanged.connect(lambda *_args: self.save_builder_settings())
        self.grammar_voice_combo.currentIndexChanged.connect(lambda *_args: self.save_builder_settings())
        self.train_voice_combo.currentIndexChanged.connect(lambda *_args: self.save_builder_settings())
        self.train_grammar_voice_combo.currentIndexChanged.connect(lambda *_args: self.save_builder_settings())
        self.title_input.editingFinished.connect(self.save_builder_settings)
        self.embedded_voice_list.currentRowChanged.connect(lambda *_args: self.save_builder_settings())
        for checkbox in (self.auto_sot_check, self.auto_edge_check, self.auto_microsoft_check, self.auto_people_check):
            checkbox.toggled.connect(lambda _checked=False: self.save_builder_settings())
        self.warm_vibevoice_check.toggled.connect(self._on_warm_vibevoice_toggled)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(
            """
            QMainWindow {
                background: #061112;
            }
            QScrollArea {
                border: 0;
                background: #061112;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: rgba(3, 13, 14, 95);
                border: 0;
                margin: 2px;
                border-radius: 7px;
            }
            QScrollBar:vertical {
                width: 10px;
            }
            QScrollBar:horizontal {
                height: 10px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                min-height: 34px;
                min-width: 34px;
                border-radius: 5px;
                background: rgba(104, 136, 130, 0.34);
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: rgba(70, 240, 215, 0.42);
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0;
                height: 0;
            }
            QWidget {
                color: #effefa;
                font-family: "Segoe UI";
            }
            QWidget#BuilderRoot {
                background: #061112;
            }
            QFrame#Hero {
                border: 1px solid rgba(70, 240, 215, 0.34);
                border-radius: 18px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(13, 45, 42, 235),
                    stop:0.58 rgba(8, 24, 25, 230),
                    stop:1 rgba(31, 24, 18, 235));
            }
            QFrame#Card {
                border: 1px solid rgba(70, 240, 215, 0.24);
                border-radius: 16px;
                background: rgba(9, 28, 29, 190);
            }
            QLabel#HeroTitle {
                color: #effefa;
                font-size: 27px;
                font-weight: 900;
            }
            QLabel#HeroSubtitle {
                color: #aac8c1;
                font-size: 13px;
            }
            QLabel#SectionLabel {
                color: #46f0d7;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QListWidget {
                border: 1px solid rgba(70, 240, 215, 0.28);
                border-radius: 12px;
                background: rgba(3, 13, 14, 210);
                color: #effefa;
                selection-background-color: #46f0d7;
                selection-color: #061316;
                padding: 9px 11px;
            }
            QPlainTextEdit {
                line-height: 1.35;
            }
            QListWidget::item {
                min-height: 30px;
                padding: 5px 9px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                color: #061316;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6cf0a4, stop:1 #46f0d7);
            }
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus {
                border-color: rgba(108, 240, 164, 0.78);
            }
            QComboBox::drop-down {
                width: 30px;
                border: 0;
            }
            QComboBox QAbstractItemView {
                background: #071112;
                color: #effefa;
                selection-background-color: #46f0d7;
                selection-color: #061316;
                outline: 0;
            }
            QMenu {
                border: 1px solid rgba(70, 240, 215, 0.42);
                border-radius: 10px;
                background: #071112;
                color: #effefa;
                padding: 6px;
            }
            QMenu::item {
                min-width: 190px;
                padding: 8px 18px 8px 12px;
                border-radius: 7px;
                background: transparent;
            }
            QMenu::item:selected {
                color: #061316;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6cf0a4, stop:1 #46f0d7);
            }
            QMenu::separator {
                height: 1px;
                margin: 6px 8px;
                background: rgba(70, 240, 215, 0.28);
            }
            QPushButton {
                min-height: 40px;
                border-radius: 14px;
                padding: 0 18px;
                border: 1px solid rgba(108, 240, 164, 0.34);
                background: rgba(3, 13, 14, 210);
                color: #effefa;
                font-weight: 850;
            }
            QPushButton:hover {
                border-color: rgba(108, 240, 164, 0.7);
                background: rgba(12, 46, 43, 230);
            }
            QPushButton#PrimaryButton {
                border: 0;
                color: #062021;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6cf0a4, stop:1 #46f0d7);
            }
            QPushButton:disabled {
                opacity: 0.55;
                color: #6f8f88;
                background: rgba(18, 32, 32, 190);
            }
            QCheckBox {
                spacing: 7px;
                color: #d9fbf5;
                font-weight: 750;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid rgba(70, 240, 215, 0.42);
                background: rgba(3, 13, 14, 220);
            }
            QCheckBox::indicator:checked {
                border-color: rgba(108, 240, 164, 0.88);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6cf0a4, stop:1 #46f0d7);
            }
            QProgressBar {
                border: 1px solid rgba(70, 240, 215, 0.2);
                border-radius: 5px;
                background: rgba(3, 13, 14, 170);
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6cf0a4, stop:1 #d86cff);
            }
            """
        )

    def log(self, message: str) -> None:
        text = clean_log_text(message)
        if not text:
            return
        self._pending_log_lines.extend(text.splitlines())
        if len(self._pending_log_lines) >= 80:
            self._flush_log_buffer()
        elif not self._log_timer.isActive():
            self._log_timer.start()

    def _flush_log_buffer(self) -> None:
        if not self._pending_log_lines:
            return
        lines = self._pending_log_lines
        self._pending_log_lines = []
        self.log_text.appendPlainText("\n".join(lines))

    def clear_log(self) -> None:
        self._pending_log_lines = []
        self.log_text.clear()

    def node_entries(self) -> list[dict]:
        entries: list[dict] = []
        for index in range(self.node_list.count()):
            item = self.node_list.item(index)
            entry = item.data(Qt.UserRole)
            normalized = normalize_lesson_entry(entry if isinstance(entry, dict) else {})
            if normalized.get("en"):
                entries.append(normalized)
        return entries

    def _node_item_summary(self, entry: dict, row: int = 0) -> str:
        en = clean_text(entry.get("en"))
        meaning = clean_text(entry.get("meaning"))
        hint = clean_text(entry.get("hint"))
        about_count = len(normalize_about_entries(entry.get("about")))
        practice_count = len(normalize_practice_entries(entry.get("practice")))
        badges = []
        badges.append("meaning: set" if meaning else "meaning: auto translate")
        if hint:
            badges.append("hint: set")
        if about_count:
            badges.append(f"about: {about_count}")
        if practice_count:
            badges.append(f"train: {practice_count}")
        return f"{row + 1:02d}. {en}\n" + "  " + "  |  ".join(badges)

    def refresh_node_item(self, item: QListWidgetItem) -> None:
        entry = normalize_lesson_entry(item.data(Qt.UserRole) if item is not None else {})
        row = self.node_list.row(item) if item is not None else 0
        item.setText(self._node_item_summary(entry, row))
        tooltip = [
            f"Sentence: {entry.get('en', '')}",
            f"Meaning: {entry.get('meaning', '') or '(auto translate when build)'}",
            f"Hint: {entry.get('hint', '') or '(none)'}",
            f"About Q&A: {len(normalize_about_entries(entry.get('about')))} item(s)",
            f"Train mode extra: {len(normalize_practice_entries(entry.get('practice')))} sentence(s)",
        ]
        item.setToolTip("\n".join(tooltip))

    def refresh_node_numbers(self) -> None:
        for index in range(self.node_list.count()):
            self.refresh_node_item(self.node_list.item(index))

    def add_node_entry(self, entry: dict[str, str], save: bool = True) -> None:
        normalized = normalize_lesson_entry(entry)
        if not normalized.get("en"):
            return
        item = QListWidgetItem()
        item.setData(Qt.UserRole, normalized)
        self.node_list.addItem(item)
        self.refresh_node_item(item)
        if save:
            self.save_builder_settings()

    def add_node_from_input(self) -> None:
        text = clean_text(self.node_sentence_input.text())
        if not text:
            return
        self.add_node_entry(parse_lesson_entry(text))
        self.node_sentence_input.clear()

    def _update_node_entry(self, item: QListWidgetItem, **updates) -> None:
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        for key, value in updates.items():
            if key == "about":
                entry[key] = normalize_about_entries(value)
            elif key == "practice":
                entry[key] = normalize_practice_entries(value)
            else:
                entry[key] = clean_text(value)
        item.setData(Qt.UserRole, entry)
        self.refresh_node_item(item)
        self.save_builder_settings()

    def edit_node_sentence(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        text, ok = QInputDialog.getMultiLineText(self, APP_TITLE, "English sentence", entry.get("en", ""))
        if ok:
            self._update_node_entry(item, en=text)

    def edit_node_meaning(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        text, ok = QInputDialog.getMultiLineText(
            self,
            APP_TITLE,
            "Vietnamese meaning. Leave empty to auto translate when build.",
            entry.get("meaning", ""),
        )
        if ok:
            self._update_node_entry(item, meaning=text)

    def edit_node_hint(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        text, ok = QInputDialog.getMultiLineText(self, APP_TITLE, "Node hint", entry.get("hint", ""))
        if ok:
            self._update_node_entry(item, hint=text)

    def edit_node_about(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        dialog = AboutEntriesDialog(self, normalize_about_entries(entry.get("about")))
        if dialog.exec_() == QDialog.Accepted:
            self._update_node_entry(item, about=dialog.entries())

    def edit_node_practice(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        entry = normalize_lesson_entry(item.data(Qt.UserRole))
        dialog = PracticeEntriesDialog(self, normalize_practice_entries(entry.get("practice")))
        if dialog.exec_() == QDialog.Accepted:
            self._update_node_entry(item, practice=dialog.entries())

    def delete_node_item(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.node_list.currentItem()
        if item is None:
            return
        row = self.node_list.row(item)
        if row >= 0:
            self.node_list.takeItem(row)
            self.refresh_node_numbers()
            self.save_builder_settings()

    def new_lesson(self) -> None:
        if self.node_list.count():
            answer = QMessageBox.question(
                self,
                APP_TITLE,
                "Tao lesson moi va xoa danh sach node hien tai?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._stop_audio_playback()
        self.title_input.setText("Future lesson")
        self.node_sentence_input.clear()
        self.node_list.clear()
        self.clear_log()
        self.save_builder_settings()
        self.log("New lesson ready.")

    def open_node_context_menu(self, position) -> None:
        item = self.node_list.itemAt(position)
        if item is not None:
            self.node_list.setCurrentItem(item)
        menu = QMenu(self)
        if item is not None:
            edit_sentence_action = menu.addAction("Edit sentence")
            meaning_action = menu.addAction("Add / edit meaning")
            hint_action = menu.addAction("Add / edit hint")
            about_action = menu.addAction("Add / edit About Q&A")
            practice_action = menu.addAction("Bổ sung câu cùng chủ đề (Train mode)")
            delete_action = menu.addAction("Delete node")
            menu.addSeparator()
        load_txt_action = menu.addAction("Load list from TXT")
        add_from_input_action = menu.addAction("Add current input as node")
        action = menu.exec_(self.node_list.mapToGlobal(position))
        if item is not None and action == edit_sentence_action:
            self.edit_node_sentence(item)
        elif item is not None and action == meaning_action:
            self.edit_node_meaning(item)
        elif item is not None and action == hint_action:
            self.edit_node_hint(item)
        elif item is not None and action == about_action:
            self.edit_node_about(item)
        elif item is not None and action == practice_action:
            self.edit_node_practice(item)
        elif item is not None and action == delete_action:
            self.delete_node_item(item)
        elif action == load_txt_action:
            self.load_nodes_from_txt()
        elif action == add_from_input_action:
            self.add_node_from_input()

    def load_nodes_from_txt(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Nap danh sach cau tu TXT",
            str(Path.cwd()),
            "Text file (*.txt);;All files (*.*)",
        )
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raw = Path(path).read_text(encoding="utf-8", errors="replace")
        count = 0
        for line in raw.splitlines():
            entry = parse_lesson_entry(line)
            if entry.get("en"):
                self.add_node_entry(entry, save=False)
                count += 1
        self.refresh_node_numbers()
        self.save_builder_settings()
        self.log(f"Nap TXT: {count} node tu {path}")

    def _set_combo_by_voice_key(self, combo: QComboBox, key: str) -> None:
        normalized = normalize_audio_voice_key(clean_text(key))
        if not normalized:
            return
        index = combo.findData(normalized)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _add_embedded_voice_key(self, label: str, key: str) -> None:
        normalized = normalize_audio_voice_key(clean_text(key))
        if not normalized or normalized.startswith("__missing_"):
            return
        for index in range(self.embedded_voice_list.count()):
            item = self.embedded_voice_list.item(index)
            if clean_text(item.data(Qt.UserRole)).lower() == normalized.lower():
                return
        item = QListWidgetItem(clean_text(label) or embedded_voice_label(normalized))
        item.setData(Qt.UserRole, normalized)
        item.setToolTip(normalized)
        self.embedded_voice_list.addItem(item)

    def load_space_w_file(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Load Space_W de sua lai",
            str(Path.cwd()),
            "Space_W lesson (*.Space_W);;JSON/FTG file (*.json *.txt);;All files (*.*)",
        )
        if not path:
            return
        try:
            payload = decode_future_lesson_document(Path(path).read_text(encoding="utf-8-sig"))
            self.load_payload_into_editor(payload, path)
            self.log(f"Da load Space_W: {path}")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Khong load duoc Space_W:\n{exc}")

    def load_payload_into_editor(self, payload: dict, source_path: str = "") -> None:
        title = clean_text(payload.get("t") or payload.get("title") or Path(source_path).stem)
        if title:
            self.title_input.setText(title)
        grammar_voice = clean_text(payload.get("gv") or payload.get("grammar_voice"))
        self._set_combo_by_voice_key(self.grammar_voice_combo, grammar_voice)
        train_voice_config = payload.get("xv") if isinstance(payload.get("xv"), dict) else {}
        self._set_combo_by_voice_key(self.train_voice_combo, clean_text(train_voice_config.get("vc") or TRAIN_MODE_PRIMARY_VOICE))
        self._set_combo_by_voice_key(self.train_grammar_voice_combo, clean_text(train_voice_config.get("gv") or TRAIN_MODE_VIETNAMESE_VOICE))
        nodes = payload.get("n") if isinstance(payload.get("n"), list) else payload.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError("Space_W khong co danh sach node hop le.")
        self.node_list.clear()
        first_voice = ""
        seen_asset_keys: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            entry = {
                "en": clean_text(node.get("e") or node.get("en") or node.get("text")),
                "meaning": clean_text(node.get("mn") or node.get("q") or node.get("vi")),
                "hint": clean_text(node.get("hint") or node.get("h")),
                "about": normalize_about_entries(node.get("ab") or node.get("about") or node.get("qa") or node.get("info")),
                "practice": normalize_practice_entries(
                    node.get("xp")
                    or node.get("practice")
                    or node.get("extra_practice")
                    or node.get("extraPractice")
                    or node.get("supplemental")
                    or node.get("training")
                ),
            }
            if entry["en"]:
                self.add_node_entry(entry, save=False)
            if not first_voice:
                first_voice = clean_text(node.get("vc") or node.get("voice"))
            for asset in list(node.get("av") or []):
                if isinstance(asset, list) and len(asset) >= 7:
                    label = clean_text(asset[1])
                    key = normalize_audio_voice_key(clean_text(asset[6]))
                    lowered = key.lower()
                    if key and lowered not in seen_asset_keys:
                        seen_asset_keys.add(lowered)
                        self._add_embedded_voice_key(label, key)
        self._set_combo_by_voice_key(self.voice_combo, first_voice)
        self.refresh_node_numbers()
        self.save_builder_settings()

    def _builder_settings_payload(self) -> dict:
        selected_key, _label = self._selected_voice_key_label()
        grammar_voice_key = clean_text(self.grammar_voice_combo.currentData()) or clean_text(self.grammar_voice_combo.currentText())
        train_voice_key, _train_label = self._selected_train_voice_key_label()
        train_grammar_voice_key = clean_text(self.train_grammar_voice_combo.currentData()) or clean_text(self.train_grammar_voice_combo.currentText())
        current_item = self.embedded_voice_list.currentItem()
        current_embedded_key = clean_text(current_item.data(Qt.UserRole)) if current_item is not None else ""
        embedded_voices = []
        for index in range(self.embedded_voice_list.count()):
            item = self.embedded_voice_list.item(index)
            key = clean_text(item.data(Qt.UserRole))
            if not key:
                continue
            embedded_voices.append({"label": clean_text(item.text()), "key": key})
        return {
            "version": 1,
            "title": clean_text(self.title_input.text()),
            "selected_voice": selected_key,
            "grammar_voice": normalize_audio_voice_key(grammar_voice_key) or "sot:vi-VN",
            "train_voice": normalize_audio_voice_key(train_voice_key) or TRAIN_MODE_PRIMARY_VOICE,
            "train_grammar_voice": normalize_audio_voice_key(train_grammar_voice_key) or TRAIN_MODE_VIETNAMESE_VOICE,
            "train_embedded_voices": self.train_embedded_voice_specs(),
            "warm_vibevoice": False,
            "embedded_current_key": current_embedded_key,
            "embedded_voices": embedded_voices,
            "auto_groups": self.auto_voice_groups(),
            "nodes": self.node_entries(),
        }

    def save_builder_settings(self) -> None:
        if self._loading_settings:
            return
        try:
            ensure_cache_dirs()
            BUILDER_SETTINGS_PATH.write_text(
                json.dumps(self._builder_settings_payload(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            self.log(f"Khong luu duoc settings: {exc}")

    def _load_builder_settings(self) -> None:
        if not BUILDER_SETTINGS_PATH.is_file():
            return
        self._loading_settings = True
        try:
            data = json.loads(BUILDER_SETTINGS_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            title = clean_text(data.get("title"))
            if title:
                self.title_input.setText(title)
            selected_voice = normalize_audio_voice_key(clean_text(data.get("selected_voice")))
            if selected_voice:
                index = self.voice_combo.findData(selected_voice)
                if index >= 0:
                    self.voice_combo.setCurrentIndex(index)
            grammar_voice = normalize_audio_voice_key(clean_text(data.get("grammar_voice")))
            if grammar_voice:
                index = self.grammar_voice_combo.findData(grammar_voice)
                if index >= 0:
                    self.grammar_voice_combo.setCurrentIndex(index)
            train_voice = normalize_audio_voice_key(clean_text(data.get("train_voice"))) or TRAIN_MODE_PRIMARY_VOICE
            if train_voice:
                index = self.train_voice_combo.findData(train_voice)
                if index >= 0:
                    self.train_voice_combo.setCurrentIndex(index)
            train_grammar_voice = normalize_audio_voice_key(clean_text(data.get("train_grammar_voice"))) or TRAIN_MODE_VIETNAMESE_VOICE
            if train_grammar_voice:
                index = self.train_grammar_voice_combo.findData(train_grammar_voice)
                if index >= 0:
                    self.train_grammar_voice_combo.setCurrentIndex(index)
            self.warm_vibevoice_check.setChecked(False)
            groups = data.get("auto_groups")
            if isinstance(groups, dict):
                self.auto_sot_check.setChecked(bool(groups.get("sot")))
                self.auto_edge_check.setChecked(bool(groups.get("edge")))
                self.auto_microsoft_check.setChecked(bool(groups.get("microsoft")))
                self.auto_people_check.setChecked(bool(groups.get("people")))
            self.embedded_voice_list.clear()
            seen: set[str] = set()
            current_key = clean_text(data.get("embedded_current_key")).lower()
            current_row = -1
            for voice in list(data.get("embedded_voices") or []):
                if not isinstance(voice, dict):
                    continue
                key = normalize_audio_voice_key(clean_text(voice.get("key")))
                if not key or key.startswith("__missing_") or key.lower().startswith("vibevoice:"):
                    continue
                lowered = key.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                label = clean_text(voice.get("label")) or embedded_voice_label(key)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, key)
                item.setToolTip(key)
                self.embedded_voice_list.addItem(item)
                if current_key and lowered == current_key:
                    current_row = self.embedded_voice_list.count() - 1
            if current_row >= 0:
                self.embedded_voice_list.setCurrentRow(current_row)
            self.node_list.clear()
            for entry in list(data.get("nodes") or []):
                if isinstance(entry, dict):
                    self.add_node_entry(entry, save=False)
        except Exception as exc:
            self.log(f"Khong doc duoc settings cu: {exc}")
        finally:
            self._loading_settings = False

    def closeEvent(self, event) -> None:
        self.save_builder_settings()
        super().closeEvent(event)

    def _start_warm_cache(self, warm_vibevoice: bool | None = None, warm_base: bool = True) -> None:
        if self.warm_worker and self.warm_worker.isRunning():
            if warm_vibevoice:
                self._pending_vibe_warm = False
                self.log("VibeVoice warm skipped: disabled in Future builders.")
            return
        if warm_vibevoice:
            self.log("VibeVoice warm skipped: disabled in Future builders.")
        should_warm_vibevoice = False
        self.warm_worker = WarmCacheWorker(warm_vibevoice=should_warm_vibevoice, warm_base=bool(warm_base))
        self.warm_worker.log_message.connect(self.log)
        self.warm_worker.finished.connect(self._on_warm_cache_finished)
        self.warm_worker.start()

    def _on_warm_cache_finished(self) -> None:
        self._pending_vibe_warm = False

    def _on_warm_vibevoice_toggled(self, checked: bool) -> None:
        if checked:
            self.warm_vibevoice_check.blockSignals(True)
            self.warm_vibevoice_check.setChecked(False)
            self.warm_vibevoice_check.blockSignals(False)
            self.log("VibeVoice warm skipped: disabled in Future builders.")
        self.save_builder_settings()

    def _selected_voice_key_label(self) -> tuple[str, str]:
        key = clean_text(self.voice_combo.currentData()) or clean_text(self.voice_combo.currentText())
        label = clean_text(self.voice_combo.currentText())
        return normalize_audio_voice_key(key), label

    def _selected_train_voice_key_label(self) -> tuple[str, str]:
        key = clean_text(self.train_voice_combo.currentData()) or clean_text(self.train_voice_combo.currentText())
        label = clean_text(self.train_voice_combo.currentText())
        return normalize_audio_voice_key(key) or TRAIN_MODE_PRIMARY_VOICE, label

    def train_embedded_voice_specs(self) -> list[dict]:
        return default_train_mode_embedded_voices()

    def _preview_sentence(self) -> str:
        for entry in self.node_entries():
            text = lesson_entry_sentence(entry)
            if text:
                return text
        return VOICE_SAMPLE_TEXT

    def preview_selected_voice(self) -> None:
        if self.preview_worker and self.preview_worker.isRunning():
            QMessageBox.information(self, APP_TITLE, "Dang tao audio mau, vui long doi.")
            return
        key, label = self._selected_voice_key_label()
        if not key or key.startswith("__missing_"):
            QMessageBox.warning(self, APP_TITLE, "Voice nay dang thieu runtime hoac preset nen chua nghe thu duoc.")
            return
        self._stop_audio_playback()
        self.preview_voice_button.setEnabled(False)
        self.log(f"Preview voice: {label or embedded_voice_label(key)}")
        self.preview_worker = PreviewVoiceWorker(self._preview_sentence(), key, label)
        self.preview_worker.log_message.connect(self.log)
        self.preview_worker.failed.connect(self._on_preview_failed)
        self.preview_worker.finished_ok.connect(self._on_preview_ok)
        self.preview_worker.finished.connect(self._on_preview_finished)
        self.preview_worker.start()

    def _on_preview_ok(self, path: str, label: str) -> None:
        self.log(f"Da cache sample voice: {label} -> {Path(path).name}")
        self._flush_log_buffer()
        if not self._play_audio_file(path):
            QMessageBox.information(self, APP_TITLE, f"Da tao audio mau:\n{path}")

    def _on_preview_failed(self, message: str) -> None:
        self.log(f"Preview loi: {message}")
        self._flush_log_buffer()
        QMessageBox.warning(self, APP_TITLE, message)

    def _on_preview_finished(self) -> None:
        self.preview_voice_button.setEnabled(True)

    def _play_audio_file(self, path: str) -> bool:
        target = Path(path)
        if not target.is_file():
            return False
        if self._audio_player is not None and QMediaContent is not None:
            try:
                self._audio_player.stop()
                self._audio_player.setMedia(QMediaContent())
                self._audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(target.resolve()))))
                self._audio_player.play()
                return True
            except Exception as exc:
                self.log(f"QtMultimedia playback failed: {exc}")
        if target.suffix.lower() == ".wav" and winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
                winsound.PlaySound(str(target), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                return True
            except Exception as exc:
                self.log(f"winsound playback failed: {exc}")
        try:
            os.startfile(str(target))
            return True
        except Exception as exc:
            self.log(f"open audio failed: {exc}")
            return False

    def _stop_audio_playback(self) -> None:
        if self._audio_player is not None and QMediaContent is not None:
            try:
                self._audio_player.stop()
                self._audio_player.setMedia(QMediaContent())
            except Exception:
                pass
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        try:
            QApplication.processEvents()
        except Exception:
            pass

    def add_embedded_voice(self) -> None:
        key, selected_label = self._selected_voice_key_label()
        if key.startswith("__missing_"):
            QMessageBox.warning(self, APP_TITLE, "Voice nay dang thieu runtime hoac preset nen chua add duoc.")
            return
        if not key:
            return
        for index in range(self.embedded_voice_list.count()):
            item = self.embedded_voice_list.item(index)
            if clean_text(item.data(Qt.UserRole)).lower() == key.lower():
                self.embedded_voice_list.setCurrentRow(index)
                self.save_builder_settings()
                return
        label = selected_label or embedded_voice_label(key)
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, key)
        item.setToolTip(key)
        self.embedded_voice_list.addItem(item)
        self.log(f"Add embedded voice: {label}")
        self.save_builder_settings()

    def remove_selected_embedded_voice(self) -> None:
        row = self.embedded_voice_list.currentRow()
        if row < 0:
            return
        item = self.embedded_voice_list.takeItem(row)
        if item is not None:
            self.log(f"Remove embedded voice: {item.text()}")
        self.save_builder_settings()

    def embedded_voice_specs(self) -> list[dict]:
        voices = []
        seen = set()
        def append_voice(label: str, raw_key: str) -> None:
            key = normalize_audio_voice_key(clean_text(raw_key))
            if not key or key.startswith("__missing_"):
                return
            lowered = key.lower()
            if lowered in seen:
                return
            seen.add(lowered)
            voices.append({"label": clean_text(label) or embedded_voice_label(key), "key": key})

        for index in range(self.embedded_voice_list.count()):
            item = self.embedded_voice_list.item(index)
            append_voice(clean_text(item.text()), clean_text(item.data(Qt.UserRole)))
        return voices

    def auto_voice_groups(self) -> dict:
        return {
            "sot": bool(self.auto_sot_check.isChecked()),
            "edge": bool(self.auto_edge_check.isChecked()),
            "microsoft": bool(self.auto_microsoft_check.isChecked()),
            "people": bool(self.auto_people_check.isChecked()),
        }

    def _safe_output_name(self) -> str:
        raw = clean_text(self.title_input.text()) or "future_lesson"
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "-", raw).strip(" .-")
        return f"{safe or 'future_lesson'}{LESSON_EXTENSION}"

    def generate(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, APP_TITLE, "Dang generate, vui long doi.")
            return
        sentences = self.node_entries()
        if not sentences:
            QMessageBox.warning(self, APP_TITLE, "Hay nhap it nhat mot cau.")
            return
        output_path, _filter = QFileDialog.getSaveFileName(
            self,
            "Luu file future lesson",
            str(Path.cwd() / self._safe_output_name()),
            "Space_W lesson (*.Space_W);;Legacy text file (*.txt);;All files (*.*)",
        )
        if not output_path:
            return
        if not Path(output_path).suffix:
            output_path = str(Path(output_path).with_suffix(LESSON_EXTENSION))
        self._stop_audio_playback()
        self.generate_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.log("Bat dau generate...")
        voice_key = clean_text(self.voice_combo.currentData()) or clean_text(self.voice_combo.currentText())
        grammar_voice_key = clean_text(self.grammar_voice_combo.currentData()) or clean_text(self.grammar_voice_combo.currentText()) or "sot:vi-VN"
        train_voice_key, _train_voice_label = self._selected_train_voice_key_label()
        train_grammar_voice_key = clean_text(self.train_grammar_voice_combo.currentData()) or clean_text(self.train_grammar_voice_combo.currentText()) or TRAIN_MODE_VIETNAMESE_VOICE
        train_embedded_voices = self.train_embedded_voice_specs()
        embedded_voices = self.embedded_voice_specs()
        auto_groups = self.auto_voice_groups()
        self.log(f"Voice hint: {voice_key}")
        self.log(f"SpaCy Vietnamese voice: {embedded_voice_label(grammar_voice_key)}")
        self.log(
            "Train mode audio: "
            + ", ".join(item["label"] for item in train_embedded_voices)
            + f" | Vietnamese: {embedded_voice_label(train_grammar_voice_key)}"
        )
        if embedded_voices:
            labels = [item["label"] for item in embedded_voices]
            self.log("Manual embedded voices: " + ", ".join(labels))
        else:
            self.log("Manual embedded voices: none")
        enabled_groups = [name for name, enabled in auto_groups.items() if enabled]
        self.log("Auto groups: " + (", ".join(enabled_groups) if enabled_groups else "none"))
        self.worker = GenerateWorker(
            sentences,
            clean_text(self.title_input.text()),
            voice_key,
            embedded_voices,
            auto_groups,
            grammar_voice_key,
            Path(output_path),
            train_voice_key,
            train_embedded_voices,
            train_grammar_voice_key,
        )
        self.worker.log_message.connect(self.log)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_finished_ok(self, output_path: str, count: int) -> None:
        self.log(f"Da xuat: {output_path}")
        self.log(f"So node: {count}")
        self._flush_log_buffer()
        QMessageBox.information(self, APP_TITLE, f"Da tao file FTG1:\n{output_path}")

    def _on_failed(self, message: str) -> None:
        self.log(f"Loi: {message}")
        self._flush_log_buffer()
        QMessageBox.critical(self, APP_TITLE, message)

    def _on_worker_finished(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.generate_button.setEnabled(True)
        self._flush_log_buffer()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FutureLessonBuilder()
    window.show()
    sys.exit(app.exec_())
