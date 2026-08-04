from __future__ import annotations

import argparse
import atexit
import base64
import concurrent.futures
import copy
import ctypes
import difflib
import gzip
import hashlib
import hmac
import html
import importlib
import io
import ipaddress
import json
import math
import mimetypes
import os
import queue
import random
import re
import secrets
import signal
import shutil
import smtplib
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
import uuid
import webbrowser
import socket
import subprocess
import faulthandler
from datetime import datetime
from collections import Counter
from ctypes import wintypes
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen

from future_postgres_structure_asset_store import (
    close_structure_read_pool,
    initialize_structure_database,
    iter_structure_assets,
    ocr_cache_index,
    ocr_cache_page_text as structure_ocr_cache_page_text,
    ocr_cache_revision_ns,
    ocr_cache_text_snapshot,
    structure_asset_bytes,
    structure_asset_exists,
    structure_asset_gzip,
    structure_asset_json,
    structure_asset_logical_path,
    structure_asset_signature,
    write_structure_asset_json,
)
from future_space_pdf_package import resolve_space_pdf_source_path, validate_space_pdf_manifest_light, validate_space_pdf_package
from future_space_picture_package import resolve_space_picture_source_path, validate_space_picture_manifest_light, validate_space_picture_package


def _early_env_path(name: str, default: Path) -> Path:
    raw = str(os.environ.get(name, "") or "").strip().strip('"')
    if raw:
        return Path(raw).resolve()
    return Path(default).resolve()


def _early_env_bool(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "1" if default else "0") or "").strip().lower()
    return raw not in {"0", "false", "no", "off", "disabled"}


def _default_frontend_path() -> Path:
    candidates = [
        ROOT / "future.html",
        FUTURE_ROOT / "web" / "future_split.html",
        ROOT / "future_split.html",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return ROOT / "future.html"


FUTURE_ROOT = Path(__file__).resolve().parent
ROOT = FUTURE_ROOT.parent
PROGRAME_ROOT = ROOT.parent
# Added 2026-07-07: lets portable distributed workers use bundled model/cache roots.
QMLEARN_ROOT = Path(os.environ.get("FUTURE_QMLEARN_ROOT") or r"C:\QMLearn")
QMLEARN_DATA_ROOT = QMLEARN_ROOT / "Data"
SERVER_DATA_ROOT = _early_env_path("FUTURE_SERVER_DATA_ROOT", Path(r"C:\server data"))
SERVER_SOUND_DIR = SERVER_DATA_ROOT / "Sound"
SERVER_STRUCTURE_DIR = SERVER_DATA_ROOT / "Structure"
SERVER_PICTURE_DIR = SERVER_DATA_ROOT / "Picture"
NPC_TOP_DIR = SERVER_DATA_ROOT / "NPC_TOP"
SERVER_DATA_LINK_KIND = "future_server_data_link"
# Added 2026-07-24: staged canonical-ID rollout controls; blocking remains off until legacy mapping gates pass.
ID_CANONICAL_READ = _early_env_bool("FUTURE_ID_CANONICAL_READ", True)
ID_CANONICAL_WRITE = _early_env_bool("FUTURE_ID_CANONICAL_WRITE", True)
PATH_LEGACY_FALLBACK = _early_env_bool("FUTURE_PATH_LEGACY_FALLBACK", True)
PATH_WRITE_BLOCK = _early_env_bool("FUTURE_PATH_WRITE_BLOCK", False)
CANONICAL_ID_FALLBACK_COUNTERS = Counter()
CANONICAL_ID_FALLBACK_LOCK = threading.RLock()
SERVER_DATA_FOLDER_LINK_FILE = "._future_folder_link.json"
TASK_NOTICE_AVATAR_DIR = SERVER_PICTURE_DIR / "TaskNotice"
USER_AVATAR_DIR = SERVER_PICTURE_DIR / "UserAvatar"
USER_PROFILE_PHOTO_DIR = SERVER_PICTURE_DIR / "UserProfile"


# Added 2026-07-02: marks Server 2 related Python processes so they are easier to spot in Windows process tools.
def set_future_server2_process_status(role: str = "main") -> None:
    label = re.sub(r"\s+", " ", str(role or "main")).strip() or "main"
    os.environ["FUTURE_SERVER2_PROCESS_ROLE"] = label
    os.environ["FUTURE_SERVER2_PROCESS_STATUS"] = f"Future Server 2 - {label}"
    if os.name != "nt":
        return
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(f"Future Server 2 - {label}")
    except Exception:
        pass


QMDICT_SOURCE_FILE = PROGRAME_ROOT / "module_main" / "Data_Input" / "QmDict.py"
DEFAULT_SPACE_V_PICTURE_FOLDER = SERVER_PICTURE_DIR / "picture"
QMDICT_AUDIO_REFRESH_PROGRESS_FILE = SERVER_DATA_ROOT / "_future_qmdict_meaning_audio_refresh_progress.json"
QMDICT_AUDIO_REFRESH_REPORT_FILE = SERVER_DATA_ROOT / "_future_qmdict_meaning_audio_refresh_report.json"
QMDICT_WORD_AUDIO_REFRESH_PROGRESS_FILE = SERVER_DATA_ROOT / "_future_qmdict_word_audio_refresh_progress.json"
QMDICT_WORD_AUDIO_REFRESH_REPORT_FILE = SERVER_DATA_ROOT / "_future_qmdict_word_audio_refresh_report.json"
QMDICT_OCR_AUDIO_PRIORITY_FILE = SERVER_DATA_ROOT / "_future_qmdict_ocr_audio_priority.json"
QMLEARN_AUDIO_STEM_INDEX_FILE = SERVER_DATA_ROOT / "_future_qmlearn_audio_stem_index.json"
USER_ROOT = QMLEARN_ROOT / "users"
MAIN_SERVER_USER_ROOT = QMLEARN_ROOT / "server_users"
RUNTIME_ROOT = _early_env_path("FUTURE_RUNTIME_ROOT", PROGRAME_ROOT / "programe_cache" / "future_whisper_server")
SERVER_PID_FILE = RUNTIME_ROOT / "server.pid"
SERVER_PREVIOUS_PID_FILE = RUNTIME_ROOT / "server.previous.pid"
STT_WORKER_SCRIPT = _early_env_path("FUTURE_STT_WORKER_SCRIPT", ROOT / "future_stt_worker.py")
STT_WORKER_PID_FILE = RUNTIME_ROOT / "stt_worker.pid"
STT_WORKER_HOST = str(os.environ.get("FUTURE_STT_WORKER_HOST", "127.0.0.1") or "127.0.0.1").strip()
STT_WORKER_PORT = int(os.environ.get("FUTURE_STT_WORKER_PORT", "8766") or "8766")
STT_WORKER_URL = f"http://{STT_WORKER_HOST}:{STT_WORKER_PORT}"
VOICE_WORKER_SCRIPT = _early_env_path("FUTURE_VOICE_WORKER_SCRIPT", ROOT / "future_voice_worker.py")
VOICE_WORKER_PID_FILE = RUNTIME_ROOT / "voice_worker.pid"
VOICE_WORKER_HOST = str(os.environ.get("FUTURE_VOICE_WORKER_HOST", "127.0.0.1") or "127.0.0.1").strip()
VOICE_WORKER_PORT = int(os.environ.get("FUTURE_VOICE_WORKER_PORT", "8767") or "8767")
VOICE_WORKER_URL = f"http://{VOICE_WORKER_HOST}:{VOICE_WORKER_PORT}"
VOICE_WORKER_ENABLED = str(os.environ.get("FUTURE_VOICE_WORKER_ENABLED", "1") or "1").strip().lower() not in {"0", "false", "no", "off"}
PROCESS_WORKER_SCRIPT = _early_env_path("FUTURE_PROCESS_WORKER_SCRIPT", ROOT / "future_process_worker.py")
PROCESS_WORKER_PID_FILE = RUNTIME_ROOT / "process_worker.pid"
PROCESS_WORKER_HOST = str(os.environ.get("FUTURE_PROCESS_WORKER_HOST", "127.0.0.1") or "127.0.0.1").strip()
PROCESS_WORKER_PORT = int(os.environ.get("FUTURE_PROCESS_WORKER_PORT", "8880") or "8880")
PROCESS_WORKER_URL = f"http://{PROCESS_WORKER_HOST}:{PROCESS_WORKER_PORT}"
PROCESS_WORKER_ENABLED = str(os.environ.get("FUTURE_PROCESS_WORKER_ENABLED", "1") or "1").strip().lower() not in {"0", "false", "no", "off"}
SERVER_LOG_ROOT = SERVER_DATA_ROOT / "server_log"
LEARNING_LOG_FILE = SERVER_LOG_ROOT / "future_learning_log.txt"
LOGIN_LOG_FILE = SERVER_LOG_ROOT / "future_login_log.txt"
STT_DEBUG_LOG_FILE = SERVER_LOG_ROOT / "future_whisper_stt_debug.log"
STT_FAULT_LOG_FILE = SERVER_LOG_ROOT / "future_whisper_fault.log"
CODE_PREFIX = "FTG1."
IMAGE_FILE_SUFFIXES = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
# Updated 2026-07-22: portable PDF/Picture packages are first-class lesson artifacts; raw media is only an asset/legacy locator.
LESSON_FILE_SUFFIXES = {
    ".space_w", ".space_v", ".space_b", ".space_q", ".space_p", ".space_s", ".space_l",
    ".space_pdf", ".space_picture", ".pdf", ".txt", *IMAGE_FILE_SUFFIXES,
}
PENDING_USERS_FILE = USER_ROOT / "_web_pending_users.json"
ANNOUNCEMENTS_FILE = USER_ROOT / "_future_announcements.json"
AUTH_SESSIONS_FILE = USER_ROOT / "_future_auth_sessions.json"
AUTH_COOKIE_NAME = "future_lesson_auth_token"
MAX_JSON_BODY_BYTES = 512 * 1024
PASSWORD_RESET_FILE = USER_ROOT / "_future_password_resets.json"
CHAT_FILE = USER_ROOT / "_future_chat_messages.json"
CHAT_ATTACHMENT_DIR = USER_ROOT / "_future_chat_attachments"
ADMINS_FILE = USER_ROOT / "_future_admins.json"
BLOCKED_LOGIN_USERS_FILE = USER_ROOT / "_future_blocked_login_users.json"
SPEAK_SKIP_REQUESTS_FILE = USER_ROOT / "_future_space_w_speak_skip_requests.json"
SETTINGS_FILE = SERVER_DATA_ROOT / "_future_settings.json"
LESSON_TASKS_FILE = SERVER_DATA_ROOT / "_future_lesson_tasks.json"
LESSON_TASK_NOTICES_FILE = SERVER_DATA_ROOT / "_future_lesson_task_notices.json"
SERVER_DATA_MANIFEST_FILE = SERVER_DATA_ROOT / "_future_server_data_manifest.json"
SERVER_BOOT_SNAPSHOT_FILE = SERVER_DATA_ROOT / "_future_server2_boot_snapshot.json"
FRONTEND_RELOAD_FILE = SERVER_DATA_ROOT / "_future_frontend_reload.json"
PDF_PICTURE_METADATA_INDEX_FILE = SERVER_DATA_ROOT / "_future_pdf_picture_metadata_index.json"
VOCAB_LEADERBOARD_RANK_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_ranks.json"
VOCAB_LEADERBOARD_PERIOD_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_periods.json"
VOCAB_LEADERBOARD_PERIOD_WAL_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_periods.wal.jsonl"
SPACE_V_REGISTRY_SYNC_WAL_FILE = SERVER_DATA_ROOT / "_future_space_v_registry_sync.wal.jsonl"
VOCAB_LEADERBOARD_REWARD_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_reward_claims.json"
VOCAB_LEADERBOARD_VIEWERS_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_viewers.json"
VOCAB_LEADERBOARD_SOCIAL_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_social.json"
VOCAB_LEADERBOARD_CHAT_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_world_chat.json"
VOCAB_LEADERBOARD_NPC_TOP_FILE = SERVER_DATA_ROOT / "_future_vocab_leaderboard_npc_top.json"
SHARED_WORLD_FILE = SERVER_DATA_ROOT / "_future_shared_world.json"
SHARED_WORLD_KEYBOARD_FILE = SERVER_DATA_ROOT / "_future_shared_world_keyboard_passes.json"
SHARED_WORLD_BATTLE_FILE = SERVER_DATA_ROOT / "_future_shared_world_battles.json"
SHARED_WORLD_BATTLE_WORD_HISTORY_FILE = SERVER_DATA_ROOT / "_future_shared_world_battle_word_history.json"
QM_CITY_TRAINING_FILE = SERVER_DATA_ROOT / "_future_qm_city_training.json"
GEMINI_KEY_FILE = Path(os.environ.get("FUTURE_GEMINI_KEY_FILE") or (ROOT / "key.txt"))
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_TEXT_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
)
GEMINI_KEY_RE = re.compile(r"(?:AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-\.]{20,})")
GEMINI_KEY_LOCK = threading.RLock()
GEMINI_KEY_QUEUE_INDEX = 0
GEMINI_KEY_CACHE = {"mtime_ns": -1, "keys": []}
GEMINI_MODEL_CACHE: dict[str, tuple[float, list[str]]] = {}
GEMINI_MODEL_CACHE_SECONDS = 60 * 30


def early_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(os.environ.get(name, "") or default).strip())
    except Exception:
        value = int(default)
    return max(int(minimum), min(int(maximum), value))


def default_pdf_render_disk_cache_root() -> Path:
    env_root = str(os.environ.get("FUTURE_PDF_RENDER_DISK_CACHE_DIR", "") or "").strip().strip('"')
    if env_root:
        return Path(env_root)
    try:
        if Path("D:/").exists():
            return Path("D:/future_pdf_render_cache")
    except Exception:
        pass
    return RUNTIME_ROOT / "pdf_render_cache"


PDF_RENDER_CACHE_LOCK = threading.RLock()
PDF_RENDER_CACHE: dict[str, dict] = {}
PDF_RENDER_CACHE_MAX_BYTES = early_env_int("FUTURE_PDF_RENDER_RAM_CACHE_MAX_BYTES", 768 * 1024 * 1024, 64 * 1024 * 1024, 4 * 1024 * 1024 * 1024)
PDF_RENDER_CACHE_MAX_ENTRIES = early_env_int("FUTURE_PDF_RENDER_RAM_CACHE_MAX_ENTRIES", 160, 16, 1000)
PDF_RENDER_INFLIGHT: dict[str, dict] = {}
PDF_RENDER_DISK_CACHE_ROOT = default_pdf_render_disk_cache_root()
PDF_RENDER_DISK_CACHE_MAX_BYTES = early_env_int("FUTURE_PDF_RENDER_DISK_CACHE_MAX_BYTES", 8 * 1024 * 1024 * 1024, 0, 200 * 1024 * 1024 * 1024)
PDF_RENDER_DISK_CACHE_MIN_RENDER_MS = early_env_int("FUTURE_PDF_RENDER_DISK_CACHE_MIN_RENDER_MS", 180, 0, 60000)
PDF_FILE_BYTES_CACHE_LOCK = threading.RLock()
PDF_FILE_BYTES_CACHE: dict[str, dict] = {}
PDF_FILE_BYTES_CACHE_MAX_BYTES = early_env_int("FUTURE_PDF_FILE_BYTES_CACHE_MAX_BYTES", 768 * 1024 * 1024, 0, 4 * 1024 * 1024 * 1024)
PDF_FILE_BYTES_CACHE_MAX_FILE_BYTES = early_env_int("FUTURE_PDF_FILE_BYTES_CACHE_MAX_FILE_BYTES", 160 * 1024 * 1024, 0, 1024 * 1024 * 1024)
PDF_FILE_BYTES_CACHE_MAX_ENTRIES = early_env_int("FUTURE_PDF_FILE_BYTES_CACHE_MAX_ENTRIES", 12, 1, 64)
PDF_PICTURE_METADATA_INDEX_LOCK = threading.RLock()
PDF_PICTURE_METADATA_INDEX: dict[str, object] = {"loaded": False, "items": {}}
PDF_PICTURE_METADATA_WARM_STATE = {"started": False, "running": False, "done": 0, "failed": 0, "last": "", "error": ""}
TESSERACT_CMD_CACHE_LOCK = threading.RLock()
TESSERACT_CMD_CACHE = {"checked": False, "path": ""}
GEMINI_MODEL_COOLDOWN: dict[str, float] = {}
LESSON_TIME_FILE_NAME = "_future_lesson_time.json"
LEARNING_SUMMARY_FILE_NAME = "_future_learning_summary.json"
SPACE_W_PROGRESS_FILE_NAME = "_future_space_w_progress.json"
SPACE_Q_PROGRESS_FILE_NAME = "_future_space_q_progress.json"
SPACE_V_PROGRESS_FILE_NAME = "_future_space_v_progress.json"
SPACE_P_PROGRESS_FILE_NAME = "_future_space_p_progress.json"
SPACE_PDF_PROGRESS_FILE_NAME = "_future_space_pdf_progress.json"
AI_AGENT_HISTORY_FILE_NAME = "_future_ai_agent_history.json"
WORD_AGENT_HISTORY_FILE = SERVER_DATA_ROOT / "_future_word_agent_history.json"
PHONETIC_IPA_CACHE_FILE = SERVER_DATA_ROOT / "_future_phonetic_ipa_cache.json"
INVENTORY_FILE_NAME = "_future_inventory.json"
GAME_MAX_SEATS = 6
GAME_DEFAULT_SEATS = 2
GAME_MAX_WORDS = 50
GAME_ROOMS: dict[str, dict] = {}
GAME_LOCK = threading.RLock()
QMDICT_EDIT_LOCK = threading.RLock()
QMDICT_SUMMARY_MAP_CACHE_LOCK = threading.RLock()
QMDICT_SUMMARY_MAP_CACHE: dict[str, object] = {"signature": None, "maps": {}, "built_at": 0.0}
QMDICT_LOOKUP_SUMMARY_CACHE_LOCK = threading.RLock()
QMDICT_LOOKUP_SUMMARY_CACHE: dict[tuple[object, ...], dict] = {}
QMDICT_TEXT_TOKEN_DETAIL_CACHE_LOCK = threading.RLock()
QMDICT_TEXT_TOKEN_DETAIL_CACHE: dict[tuple[object, ...], dict] = {}
QMDICT_TEXT_PHRASE_CACHE_LOCK = threading.RLock()
QMDICT_TEXT_PHRASE_CACHE: dict[tuple[object, ...], list[dict]] = {}
QMDICT_TEXT_ENTRY_CACHE_LOCK = threading.RLock()
QMDICT_TEXT_ENTRY_CACHE: dict[tuple[object, ...], list[object]] = {}
QMDICT_VOCAB_BASE_CACHE_LOCK = threading.RLock()
QMDICT_VOCAB_BASE_CACHE: dict[tuple[object, ...], dict] = {}
QMDICT_VOCAB_STATS_CACHE_LOCK = threading.RLock()
QMDICT_VOCAB_STATS_CACHE: dict[tuple[object, ...], dict] = {}
QMDICT_VOCAB_INFLIGHT_LOCK = threading.RLock()
QMDICT_VOCAB_INFLIGHT: dict[tuple[object, ...], dict] = {}
QMDICT_CHAT_TOKEN_CACHE_LOCK = threading.RLock()
QMDICT_CHAT_TOKEN_CACHE: dict[tuple[object, ...], bool] = {}
QMDICT_LOOKUP_SUMMARY_CACHE_LIMIT = 24000
QMDICT_TEXT_TOKEN_DETAIL_CACHE_LIMIT = 800
QMDICT_TEXT_PHRASE_CACHE_LIMIT = 800
QMDICT_TEXT_ENTRY_CACHE_LIMIT = 800
QMDICT_VOCAB_BASE_CACHE_LIMIT = 500
QMDICT_VOCAB_STATS_CACHE_LIMIT = 500
QMDICT_CHAT_TOKEN_CACHE_LIMIT = 16000
SPACE_V_QMDICT_SYNC_LOCK = threading.RLock()
SPACE_V_QMDICT_REPAIR_LOCK = threading.RLock()
SPACE_V_DEFAULT_VOICES = (
    ("Sound of Text | Female UK", "sot:en-GB", "uk"),
    ("Sound of Text | Female US", "sot:en-US", "us"),
)
SPACE_V_AUDIO_REFRESH_DAILY_LIMIT = 20
SPACE_V_AUDIO_REFRESH_RATE_LOCK = threading.RLock()
SPACE_V_AUDIO_REFRESH_RATE: dict[str, dict] = {}
SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT_LOCK = threading.RLock()
SPACE_V_AUDIO_REFRESH_SINGLEFLIGHT: dict[tuple[str, str], dict] = {}
SPACE_V_AUDIO_REFRESH_MAX_CONCURRENT = 4
SPACE_V_AUDIO_REFRESH_SEMAPHORE = threading.BoundedSemaphore(SPACE_V_AUDIO_REFRESH_MAX_CONCURRENT)
QMLEARN_AUDIO_PATH_CACHE_LOCK = threading.RLock()
QMLEARN_AUDIO_PATH_CACHE: dict[tuple[str, str], Path | None] = {}
QMLEARN_AUDIO_DIR_INDEX_LOCK = threading.RLock()
QMLEARN_AUDIO_DIR_INDEX: dict[str, dict[str, Path]] = {}
QMLEARN_AUDIO_DIR_REVISION_INDEX: dict[str, dict[str, str]] = {}
QMLEARN_AUDIO_HELPERS_LOCK = threading.RLock()
QMLEARN_AUDIO_HELPERS: dict[str, object] = {"loaded": False, "file_name": None, "stem": None}
QMLEARN_AUDIO_URL_CACHE_LOCK = threading.RLock()
QMLEARN_AUDIO_URL_CACHE: dict[str, tuple[str, str]] = {}
QMLEARN_AUDIO_REVISION_CACHE_LOCK = threading.RLock()
QMLEARN_AUDIO_REVISION_CACHE: dict[str, tuple[int, int, str]] = {}
QMLEARN_HTTP_AUDIO_CACHE_LOCK = threading.RLock()
QMLEARN_HTTP_AUDIO_CACHE: dict[str, dict] = {}
QMLEARN_HTTP_AUDIO_CACHE_MAX_ITEMS = 512
QMLEARN_HTTP_AUDIO_CACHE_MAX_BYTES = 160 * 1024 * 1024
SPACE_V_QMDICT_REPAIR_JOB = {
    "running": False,
    "job_id": "",
    "started_at": "",
    "updated_at": "",
    "completed_at": "",
    "total": 0,
    "done": 0,
    "changed": 0,
    "audio_changed": 0,
    "removed": 0,
    "failed": 0,
    "last": "",
    "error": "",
}
QMDICT_RELOAD_STATE = {
    "mtime_ns": 0,
    "size": -1,
    "checked_at": 0.0,
    "loaded_at": "",
    "entries": 0,
    "error": "",
}
QMDICT_AUDIO_REFRESH_LOCK = threading.RLock()
QMDICT_AUDIO_REFRESH_INFLIGHT: set[str] = set()
# Added 2026-07-31: Vietnamese refresh shares the bounded resumable audio session limit.
QMDICT_AUDIO_REFRESH_MAX_WORKERS = 4
QMDICT_AUDIO_STEM_INDEX_LOCK = threading.RLock()
QMDICT_AUDIO_STEM_INDEX_CACHE = {"stems": set(), "loaded_at": 0.0}
QMDICT_AUDIO_REFRESH_JOB = {
    "running": False,
    "job_id": "",
    "mode": "",
    "phase": "",
    "message": "",
    "started_at": "",
    "updated_at": "",
    "completed_at": "",
    "scan_total": 0,
    "scan_done": 0,
    "workers": 0,
    "cleanup_total": 0,
    "cleanup_done": 0,
    "cleanup_deleted": 0,
    "total": 0,
    "done": 0,
    "cached": 0,
    "missing": 0,
    "downloaded": 0,
    "failed": 0,
    "last_key": "",
    "last_meaning": "",
    "error": "",
    "cancel_requested": False,
}
QMDICT_WORD_AUDIO_REFRESH_LOCK = threading.RLock()
# Added 2026-07-31: keep bulk Sound of Text refresh bounded until a small batch proves healthy.
QMDICT_WORD_AUDIO_REFRESH_MAX_WORKERS = 4
# Added 2026-07-31: persist bulk audio behind the worker feeder so file/index I/O
# cannot reduce the number of TTS jobs held by distributed workers.
QMDICT_WORD_AUDIO_WRITER_WORKERS = 8
QMDICT_WORD_AUDIO_RESULT_BUFFER = 128
# Added 2026-07-31: cache the PostgreSQL OCR-first word order by OCR and QmDict revision.
QMDICT_OCR_AUDIO_PRIORITY_LOCK = threading.RLock()
QMDICT_OCR_AUDIO_PRIORITY_CACHE = {"signature": None, "words": [], "pages": 0, "built_at": ""}
QMDICT_WORD_AUDIO_REFRESH_JOB = {
    "running": False,
    "job_id": "",
    "mode": "",
    "phase": "",
    "message": "",
    "started_at": "",
    "updated_at": "",
    "completed_at": "",
    "scan_total": 0,
    "scan_done": 0,
    "workers": 0,
    "total": 0,
    "done": 0,
    "refreshed": 0,
    "failed": 0,
    "priority_total": 0,
    "priority_done": 0,
    "last_key": "",
    "last_word": "",
    "last_voice": "",
    "error": "",
    "cancel_requested": False,
}
VOCAB_BUILD_JOBS: dict[str, dict] = {}
VOCAB_BUILD_LOCK = threading.RLock()
VOCAB_BUILD_TTL_SECONDS = 60 * 60 * 3
VOCAB_LEADERBOARD_REWARD_CHECK_CACHE: dict[str, dict] = {}
DEFAULT_LEADERBOARD_REACTIONS = [
    {"key": "love", "label": "Love", "mark": "💕⃝"},
    {"key": "burn", "label": "Fire heart", "mark": "❤️‍🔥"},
    {"key": "devil", "label": "Mischief", "mark": "😈"},
    {"key": "frost", "label": "Cool", "mark": "🥶"},
]
DEFAULT_QM_CITY_SKINS = [
    {"id": "slime", "name": "Slime", "price": 35, "image": "", "description": "A soft crystal slime form with elastic motion."},
    {"id": "cloud", "name": "Cloud", "price": 45, "image": "", "description": "A floating cloud spirit form with vapor trails."},
    {"id": "star-fox", "name": "Star Fox", "price": 60, "image": "", "description": "A quick cosmic fox form for bright movement."},
    {"id": "crystal-golem", "name": "Crystal Golem", "price": 80, "image": "", "description": "A heavy prism golem form with strong crystal armor."},
    {"id": "moon-cat", "name": "Moon Cat", "price": 55, "image": "", "description": "A quiet moon cat form with soft neon ears."},
    {"id": "ember-dragon", "name": "Ember Dragon", "price": 95, "image": "", "description": "A small dragon form with ember wings."},
    {"id": "aqua-sprite", "name": "Aqua Sprite", "price": 50, "image": "", "description": "A water sprite form with flowing blue light."},
    {"id": "thunder-cub", "name": "Thunder Cub", "price": 70, "image": "", "description": "A storm cub form with electric sparks."},
    {"id": "leaf-spirit", "name": "Leaf Spirit", "price": 42, "image": "", "description": "A forest spirit form with living leaf marks."},
    {"id": "neon-orb", "name": "Neon Orb", "price": 65, "image": "", "description": "A clean neon orb form with a hologram core."},
]
DEFAULT_QM_CITY_LEVELS = [
    {"level": 1, "total_exp": 0},
    {"level": 2, "total_exp": 25},
    {"level": 3, "total_exp": 75},
    {"level": 4, "total_exp": 150},
    {"level": 5, "total_exp": 300},
    {"level": 6, "total_exp": 500},
    {"level": 7, "total_exp": 800},
    {"level": 8, "total_exp": 1200},
    {"level": 9, "total_exp": 1700},
    {"level": 10, "total_exp": 2400},
]
DEFAULT_SETTINGS = {
    "word_hint_cycle_seconds": 30,
    "paragraph_hint_seconds": 30,
    "chat_attachment_limit_mb": 100,
    "ai_agent_notice_voice": "kokoro:am_michael",
    "space_w_ai_check_voice_enabled": True,
    "cpu_guard_enabled": True,
    "cpu_queue_threshold_percent": 90,
    "heavy_user_quota_per_minute": 5,
    "heavy_user_min_interval_seconds": 5,
    "distributed_worker_job_limits": {
        "translate": 4,
        "tts": 4,
        "stt": 4,
        "gemini": 4,
        "phonemize": 8,
    },
    "distributed_worker_machine_limit": 1,
    "qm_city_chat_min_english_percent": 50,
    "qm_city_chat_invalid_run_limit": 4,
    "qm_city_skins": DEFAULT_QM_CITY_SKINS,
    "qm_city_levels": DEFAULT_QM_CITY_LEVELS,
    "qm_city_npc": {
        "enabled": True,
        "mode": "top",
        "spawn_chance_percent": 55,
        "min_active": 1,
        "max_active": 5,
        "online_min_minutes": 20,
        "online_max_minutes": 40,
        "answer_correct_percent": 58,
        "steal_correct_percent": 34,
        "invite_chance_percent": 8,
        "invite_cooldown_min_seconds": 70,
        "invite_cooldown_max_seconds": 180,
    },
    "cloudflare_public_hostname": "",
    "cloudflare_tunnel_name": "future-whisper",
    "space_v_picture_folder": str(DEFAULT_SPACE_V_PICTURE_FOLDER),
    "webrtc_ice_servers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:global.stun.twilio.com:3478"]},
    ],
    "webrtc_force_relay": False,
    "question_hud_lines": [
        "MISSION NODE ONLINE",
        "ORBITAL MEMORY LINK",
        "QUESTION SIGNAL READY",
    ],
    "hosted_client_secret_hash": "",
    "leaderboard_reactions": DEFAULT_LEADERBOARD_REACTIONS,
    "leaderboard_rewards": {
        "total": {
            "title": "Hall Champion",
            "claim_window": "Honor reward preview for the all-time leaderboard.",
            "ranks": {
                "1": {"badge": True, "rare": 12, "easy": 36, "space_q": 12, "space_q_silver": 12, "space_p": 12, "space_p_silver": 12, "space_s": 12, "space_s_silver": 12, "space_w": 12, "space_w_silver": 12, "space_l": 12, "space_l_silver": 12, "space_v": 12},
                "2": {"badge": False, "rare": 8, "easy": 24, "space_q": 8, "space_q_silver": 8, "space_p": 8, "space_p_silver": 8, "space_s": 8, "space_s_silver": 8, "space_w": 8, "space_w_silver": 8, "space_l": 8, "space_l_silver": 8, "space_v": 8},
                "3": {"badge": False, "rare": 5, "easy": 16, "space_q": 5, "space_q_silver": 5, "space_p": 5, "space_p_silver": 5, "space_s": 5, "space_s_silver": 5, "space_w": 5, "space_w_silver": 5, "space_l": 5, "space_l_silver": 5, "space_v": 5},
            },
        },
        "day": {
            "title": "Daily Champion",
            "claim_window": "Claim during the next day only.",
            "ranks": {
                "1": {"badge": True, "rare": 5, "easy": 15, "space_q": 3, "space_q_silver": 3, "space_p": 3, "space_p_silver": 3, "space_s": 3, "space_s_silver": 3, "space_w": 3, "space_w_silver": 3, "space_l": 3, "space_l_silver": 3, "space_v": 3},
                "2": {"badge": False, "rare": 3, "easy": 10, "space_q": 2, "space_q_silver": 2, "space_p": 2, "space_p_silver": 2, "space_s": 2, "space_s_silver": 2, "space_w": 2, "space_w_silver": 2, "space_l": 2, "space_l_silver": 2, "space_v": 2},
                "3": {"badge": False, "rare": 2, "easy": 6, "space_q": 1, "space_q_silver": 1, "space_p": 1, "space_p_silver": 1, "space_s": 1, "space_s_silver": 1, "space_w": 1, "space_w_silver": 1, "space_l": 1, "space_l_silver": 1, "space_v": 1},
            },
        },
        "week": {
            "title": "Weekly Champion",
            "claim_window": "Claim during the next week only.",
            "ranks": {
                "1": {"badge": True, "rare": 18, "easy": 54, "space_q": 9, "space_q_silver": 9, "space_p": 9, "space_p_silver": 9, "space_s": 9, "space_s_silver": 9, "space_w": 9, "space_w_silver": 9, "space_l": 9, "space_l_silver": 9, "space_v": 9},
                "2": {"badge": False, "rare": 12, "easy": 36, "space_q": 6, "space_q_silver": 6, "space_p": 6, "space_p_silver": 6, "space_s": 6, "space_s_silver": 6, "space_w": 6, "space_w_silver": 6, "space_l": 6, "space_l_silver": 6, "space_v": 6},
                "3": {"badge": False, "rare": 8, "easy": 24, "space_q": 4, "space_q_silver": 4, "space_p": 4, "space_p_silver": 4, "space_s": 4, "space_s_silver": 4, "space_w": 4, "space_w_silver": 4, "space_l": 4, "space_l_silver": 4, "space_v": 4},
            },
        },
        "month": {
            "title": "Monthly Champion",
            "claim_window": "Claim during the next month only.",
            "ranks": {
                "1": {"badge": True, "rare": 60, "easy": 180, "space_q": 30, "space_q_silver": 30, "space_p": 30, "space_p_silver": 30, "space_s": 30, "space_s_silver": 30, "space_w": 30, "space_w_silver": 30, "space_l": 30, "space_l_silver": 30, "space_v": 30},
                "2": {"badge": False, "rare": 40, "easy": 120, "space_q": 20, "space_q_silver": 20, "space_p": 20, "space_p_silver": 20, "space_s": 20, "space_s_silver": 20, "space_w": 20, "space_w_silver": 20, "space_l": 20, "space_l_silver": 20, "space_v": 20},
                "3": {"badge": False, "rare": 25, "easy": 80, "space_q": 12, "space_q_silver": 12, "space_p": 12, "space_p_silver": 12, "space_s": 12, "space_s_silver": 12, "space_w": 12, "space_w_silver": 12, "space_l": 12, "space_l_silver": 12, "space_v": 12},
            },
        },
    },
}
PUBLIC_FRONTEND_PATH = _early_env_path("FUTURE_FRONTEND_PATH", _default_frontend_path())
PUBLIC_FACE1_PATH = (ROOT / "face 1.html").resolve()
PUBLIC_FACE2_PATH = (ROOT / "face 2.html").resolve()
FRONTEND_ASSET_ROOT = _early_env_path("FUTURE_FRONTEND_ASSET_ROOT", ROOT / "FUTURE" / "web")
FRONTEND_ASSET_ROUTE_PREFIX = "/future-assets/"
FRONTEND_ASSET_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
}
OBFUSCATED_FRONTEND_PATH = RUNTIME_ROOT / "future.hosted.obf.html"
OBFUSCATED_FRONTEND_META_PATH = RUNTIME_ROOT / "future.hosted.obf.json"
OBFUSCATED_FRONTEND_VERSION = 5
HOSTED_SCRIPT_MANGLE_TIMEOUT_SECONDS = 75
FRONTEND_BYTES_CACHE_LOCK = threading.RLock()
FRONTEND_BYTES_CACHE: dict[str, dict] = {}
HTTP_GZIP_CACHE_LOCK = threading.RLock()
HTTP_GZIP_CACHE: dict[str, dict] = {}
HTTP_GZIP_CACHE_MAX_BYTES = 96 * 1024 * 1024
HTTP_GZIP_CACHE_BYTES = 0
PUBLIC_SERVER_STATE_KEYS = {
    "model_name",
    "model_ref",
    "language",
    "device",
    "compute_type",
    "started_at",
    "ready",
    "loading",
    "preload_started_at",
    "preload_finished_at",
    "tunnel_status",
    "queue_pending",
    "queue_active",
    "queue_total",
    "queue_completed",
    "queue_failed",
    "queue_timeout",
    "queue_last_wait_ms",
    "queue_last_process_ms",
    "queue_last_completed_at",
    "learning_total",
    "dashboard_status",
    "dashboard_last_seen",
    "shutdown_requested",
    "lazy_model_load",
    "worker_ready",
    "worker_loading",
    "worker_pid",
    "warm_status",
    "warm_ready",
    "warm_started_at",
    "warm_finished_at",
}
LOCAL_SERVER_STATE_KEYS = {
    "last_error",
    "tunnel_error",
    "server_urls",
    "public_url",
    "public_app_url",
    "tunnel_mode",
    "tunnel_hostname",
    "tunnel_name",
    "server_data_root",
    "last_learning_event",
    "pid",
    "previous_pid",
    "dashboard_session",
    "dashboard_close_requested_at",
    "shutdown_reason",
    "worker_url",
    "worker_last_error",
    "distributed_worker_url",
    "distributed_worker_listener",
    "distributed_worker_host",
    "distributed_worker_port",
    "distributed_worker_http_max_threads",
    "distributed_worker_listener_error",
    "space_pdf_progress_warm",
    "last_space_pdf_progress_post",
}
PUBLIC_SOURCE_SUFFIXES = {
    ".py",
    ".pyw",
    ".pyc",
    ".pyd",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".html",
    ".htm",
    ".map",
    ".env",
    ".ini",
    ".cfg",
    ".toml",
    ".yaml",
    ".yml",
    ".pem",
    ".key",
    ".crt",
    ".pfx",
    ".sqlite",
    ".db",
    ".log",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".reg",
}
PUBLIC_SOURCE_NAMES = {
    ".env",
    "future_whisper_server.py",
    "_future_auth_sessions.json",
    "_future_settings.json",
    "_future_inventory.json",
    "_future_shared_world_battles.json",
    "_future_vocab_leaderboard_reward_claims.json",
    "_future_vocab_leaderboard_social.json",
    "_future_vocab_leaderboard_world_chat.json",
    "_future_lesson_time.json",
    "_future_learning_summary.json",
    "_future_space_w_progress.json",
    "_future_space_w_speak_skip_requests.json",
    "_future_space_q_progress.json",
    "_future_space_v_progress.json",
    "_future_space_pdf_progress.json",
    "_web_pending_users.json",
    "_future_announcements.json",
    "_future_chat_messages.json",
    "server.pid",
    "server.previous.pid",
}
PUBLIC_SOURCE_PARTS = {".git", ".hg", ".svn", ".codex", "__pycache__", "programe_cache", "server_log"}
SERVER_ASSET_SUFFIXES = {
    "Sound": {
        ".mp3", ".wav", ".m4a", ".ogg", ".webm", ".txt", ".aac", ".flac", ".opus", ".aiff", ".aif", ".amr", ".caf",
        ".mp4", ".m4v", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".mpeg", ".mpg", ".m2ts", ".mts", ".ts", ".ogv",
        ".3gp", ".3g2", ".vob", ".asf", ".rm", ".rmvb", ".divx", ".f4v",
    },
    "Structure": {".json"},
    "Picture": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".jfif"},
}
CHAT_ATTACHMENT_BLOCKED_SUFFIXES = PUBLIC_SOURCE_SUFFIXES | {".json", ".xml", ".svg", ".exe", ".dll", ".msi", ".com", ".scr", ".jar"}
CHAT_ATTACHMENT_BLOCKED_MIMES = {
    "application/javascript",
    "application/x-javascript",
    "text/javascript",
    "text/html",
    "text/css",
    "image/svg+xml",
    "application/x-msdownload",
}
PROFILE_PREFIX = "__QM_PROFILE__ | "
PREFERENCES_PREFIX = "__QM_PREFERENCES__ | "
MODEL_DIRS = [
    QMLEARN_ROOT / "models",
    QMLEARN_ROOT,
    QMLEARN_ROOT / "whisper_models",
    QMLEARN_ROOT / "VoiceToText",
    QMLEARN_ROOT / "VoiceToText" / "models",
    PROGRAME_ROOT / "module_main" / "VoiceToText" / "models",
    ROOT / "models",
    Path(tempfile.gettempdir()) / "whisper_models",
    Path.home() / ".cache" / "whisper",
]
MODEL_ALIASES = {
    "large": ["large-v3", "large-v2", "large-v1", "large", "medium", "small", "base"],
    "large-v3": ["large-v3", "large", "medium", "small", "base"],
    "large-v3-turbo": ["large-v3-turbo", "turbo", "medium", "small", "base"],
    "turbo": ["large-v3-turbo", "turbo", "medium", "small", "base"],
    "medium": ["medium", "small", "base", "tiny"],
    "medium.en": ["medium.en", "medium", "small.en", "small", "base", "tiny"],
    "small.en": ["small.en", "small", "base", "tiny"],
    "small": ["small", "base", "tiny"],
    "base": ["base", "tiny"],
}
SERVER_STATE = {
    "model_name": "small",
    "model_ref": "",
    "language": "en",
    "device": "cpu",
    "compute_type": "int8",
    "started_at": time.time(),
    "ready": False,
    "loading": False,
    "worker_ready": False,
    "worker_loading": False,
    "worker_pid": 0,
    "worker_url": "",
    "worker_last_error": "",
    "warm_status": "Preparing dashboard...",
    "warm_ready": False,
    "warm_started_at": 0,
    "warm_finished_at": 0,
    "preload_started_at": 0,
    "preload_finished_at": 0,
    "last_error": "",
    "server_urls": [],
    "public_url": "",
    "public_app_url": "",
    "tunnel_mode": "quick",
    "tunnel_hostname": "",
    "tunnel_name": "",
    "tunnel_status": "not_started",
    "tunnel_error": "",
    "queue_pending": 0,
    "queue_active": False,
    "queue_active_id": "",
    "queue_active_started_at": 0,
    "queue_total": 0,
    "queue_completed": 0,
    "queue_failed": 0,
    "queue_timeout": 0,
    "queue_last_wait_ms": 0,
    "queue_last_process_ms": 0,
    "queue_last_completed_at": 0,
    "server_data_root": str(SERVER_DATA_ROOT),
    "learning_total": 0,
    "last_learning_event": {},
    "pid": os.getpid(),
    "previous_pid": 0,
    "dashboard_status": "not_open",
    "dashboard_session": "",
    "dashboard_last_seen": 0,
    "dashboard_close_requested_at": 0,
    "dashboard_retire_session": "",
    "dashboard_retire_until": 0,
    "shutdown_requested": False,
    "shutdown_reason": "",
    "lazy_model_load": False,
}
MODEL_LOCK = threading.RLock()
MODEL_CACHE = {
    "model_ref": "",
    "device": "",
    "compute_type": "",
    "obj": None,
}
TUNNEL_PROCESS = None
TUNNEL_ORIGIN_URL = ""
TUNNEL_JOB_HANDLE = None
TUNNEL_LOCK = threading.RLock()
TUNNEL_GENERATION = 0
TUNNEL_RESTART_TIMER = None
TUNNEL_RESTART_ATTEMPTS = 0
TUNNEL_MAX_RESTART_DELAY_SECONDS = 30
SERVER_HTTPD = None
# Added 2026-07-31: keep long-poll worker traffic on a LAN-only listener so
# public web request threads are not held by hundreds of idle workers.
DISTRIBUTED_WORKER_HTTPD = None
ANTI_ROBOT_LOCK = threading.RLock()
ANTI_ROBOT_BUCKETS: dict[str, dict] = {}
SECURITY_ALERT_LOCK = threading.RLock()
SECURITY_RATE_ALERTS: dict[str, dict] = {}
SECURITY_POLL_STATS: dict[str, dict] = {}
SECURITY_BLOCKS: dict[str, dict] = {}
SECURITY_POLL_CPU_SAMPLE = {"at": time.time(), "cpu": time.process_time(), "percent": 0.0}
ANTI_ROBOT_SECRET_FILE = RUNTIME_ROOT / "anti_robot.secret"
ANTI_ROBOT_TOKEN_TTL_SECONDS = 20 * 60
ANTI_ROBOT_TOKEN_MIN_AGE_SECONDS = 0.35
ANTI_ROBOT_GET_LIMIT = 260
ANTI_ROBOT_POST_LIMIT = 80
ANTI_ROBOT_AUTH_LIMIT = 240
ANTI_ROBOT_HEAVY_LIMIT = 90
ANTI_ROBOT_AI_LIMIT = 45
ANTI_ROBOT_LOGIN_FAIL_LIMIT = 8
LOGIN_FAILURE_LOCKS: dict[str, dict] = {}
LOGIN_FAILURE_LOCK_SECONDS = 5 * 60
LOGIN_FAILURE_MAX_ATTEMPTS = 5
USER_HEAVY_QUOTA_LOCK = threading.RLock()
USER_HEAVY_QUOTA_BUCKETS: dict[str, dict] = {}
USER_HEAVY_QUOTA_SETTINGS_CACHE: dict[str, object] = {"at": 0.0, "per_minute": 5, "min_interval": 5}
ANTI_ROBOT_WORLD_GET_LIMIT = 1800
ANTI_ROBOT_WORLD_POST_LIMIT = 1200
ANTI_ROBOT_WORKER_ENDPOINT_LIMIT = 3600
STT_QUEUE = queue.Queue()
STT_QUEUE_LOCK = threading.RLock()
STT_WORKER_THREAD = None
# 0 means the HTTP caller waits until the Whisper worker finishes. The
# transcription engine already bounds the actual work; an extra queue timeout
# can incorrectly cut long Speak Training recordings.
STT_JOB_TIMEOUT_SECONDS = 0
AUTH_LOCK = threading.RLock()
AUTH_SESSIONS = {}
AUTH_REVOKED_SESSIONS = {}
AUTH_SESSIONS_SAVE_LOCK = threading.RLock()
AUTH_SESSIONS_SAVE_STATE = {"scheduled": False, "dirty": False}
# Throttle the disk writes that auth_session_state_for_token performs on every
# authenticated request. Persisting last_seen and re-ensuring the user folder
# on each poll serializes all users behind AUTH_LOCK + synchronous disk IO,
# which made the Lesson Vault feel slow with two or more learners online.
AUTH_SESSION_PERSIST_INTERVAL_SECONDS = 60.0
AUTH_SESSION_ASYNC_SAVE_DELAY_SECONDS = 5.0
AUTH_ENSURED_FOLDERS_LOCK = threading.RLock()
AUTH_ENSURED_FOLDERS = {}
AUTH_ENSURE_FOLDER_INTERVAL_SECONDS = 300.0
AUTH_ME_CACHE_LOCK = threading.RLock()
AUTH_ME_CACHE: dict[str, dict] = {}
AUTH_ME_CACHE_TTL_SECONDS = 12.0
ANNOUNCEMENT_LOCK = threading.RLock()
SETTINGS_LOCK = threading.RLock()
ADMIN_LOCK = threading.RLock()
ADMINS_RAM_CACHE = {"signature": None, "admins": set(), "checked_at": 0.0}
ADMINS_CACHE_RECHECK_SECONDS = 2.0
USER_PREFERENCES_RAM_CACHE: dict[str, dict] = {}
SERVER_DATA_LOCK = threading.RLock()
SERVER_DATA_MANIFEST_LOCK = threading.RLock()
SERVER_DATA_LIST_CACHE_LOCK = threading.RLock()
LOGIN_PRELOAD_CACHE_USER_GENERATIONS: dict[str, int] = {}
LOGIN_PRELOAD_FAST_CACHE: dict[tuple, dict] = {}
LOGIN_PRELOAD_FAST_CACHE_TTL_SECONDS = 2.0
LOGIN_PRELOAD_BUILD_LOCKS: dict[tuple, threading.Lock] = {}
LOGIN_PRELOAD_BUILD_LOCKS_MAX_ITEMS = 64
LOGIN_PRELOAD_BUILD_LOCK_TIMEOUT_SECONDS = 15.0
SERVER_DATA_TREE_PRELOAD_BYTES_CACHE: dict[tuple, dict] = {}
SERVER_DATA_TREE_PRELOAD_BUILD_LOCKS: dict[tuple, threading.Lock] = {}
SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS = 128
SERVER_DATA_FILE_CACHE_LOCK = threading.RLock()
SERVER_BOOT_SNAPSHOT_LOCK = threading.RLock()
SERVER_BOOT_SNAPSHOT_STATE: dict[str, object] = {"loaded": False, "snapshot": {}, "valid": False, "timer": None}
LESSON_TASK_LOCK = threading.RLock()
LESSON_TASK_NOTICE_LOCK = threading.RLock()
# RAM caches for the two global lesson-data files. Both files are shared
# across all users; reading them from disk on every vault request serializes
# all concurrent users behind LESSON_TASK_LOCK / LESSON_TASK_NOTICE_LOCK.
# Each cache entry is invalidated automatically when the file's mtime/size
# signature changes, so mutations are always visible on the next request.
LESSON_TASKS_RAM_CACHE: dict = {}
LESSON_TASKS_RAM_CACHE_LOCK = threading.RLock()
LESSON_TASK_NOTICES_RAM_CACHE: dict = {}
LESSON_TASK_NOTICES_RAM_CACHE_LOCK = threading.RLock()
LESSON_TASKS_WRITEBEHIND_FLUSH_SECONDS = 2.5
LESSON_TASKS_WRITEBEHIND_STARTED = False
# RAM cache for the per-folder Space Task file scan. The scan walks a
# learner's whole folder tree (rglob), which is the disk-heavy part of
# building the admin Space Task payload. Caching the scan by folder keeps
# admins from re-walking disk every time a list response cache misses
# (a learner's progress changes bust the list cache often while studying).
SPACE_TASK_FOLDER_SCAN_CACHE: dict = {}
SPACE_TASK_FOLDER_SCAN_CACHE_LOCK = threading.RLock()
SPACE_TASK_FOLDER_SCAN_TTL_SECONDS = 3600.0
# RAM cache for the fully-built Space Task payload, keyed per learner. Building
# this payload is the disk/CPU-heavy part of Lesson Vault folder loads because
# it normalizes many lesson files to decide the active queue. Serve cached
# payloads immediately and refresh them in the background so folder navigation
# stays fast for both the learner and admins viewing that learner.
SPACE_TASK_PAYLOAD_RAM_CACHE: dict = {}
SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK = threading.RLock()
SPACE_TASK_PAYLOAD_CACHE_TTL_SECONDS = 180.0
SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT: dict = {}
# A 100-user cold burst needs one settled payload per user; keep headroom for admin views.
_space_task_cache_max_text = str(os.environ.get("FUTURE_SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS", "256") or "256").strip()
SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS = max(128, min(2048, int(_space_task_cache_max_text) if _space_task_cache_max_text.isdigit() else 256))
_space_task_cache_evict_text = str(os.environ.get("FUTURE_SPACE_TASK_PAYLOAD_CACHE_EVICT_BATCH", "64") or "64").strip()
SPACE_TASK_PAYLOAD_CACHE_EVICT_BATCH = max(1, min(
    SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS // 2,
    int(_space_task_cache_evict_text) if _space_task_cache_evict_text.isdigit() else 64,
))
# One bounded shared pool prevents 100 simultaneous folder saves from building on 100 request threads.
_space_task_worker_text = str(os.environ.get("FUTURE_SPACE_TASK_PAYLOAD_WORKERS", "8") or "8").strip()
SPACE_TASK_PAYLOAD_REFRESH_WORKERS = max(1, min(16, int(_space_task_worker_text) if _space_task_worker_text.isdigit() else 8))
SPACE_TASK_PAYLOAD_REFRESH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=SPACE_TASK_PAYLOAD_REFRESH_WORKERS, thread_name_prefix="space-task-payload")
SPACE_TASK_PAYLOAD_REFRESH_TICKET = threading.BoundedSemaphore(132)
# Slow-path timing log threshold for list_server_data (milliseconds).
SERVER_DATA_LIST_SLOW_LOG_MS = 600
LESSON_TIME_LOCK = threading.RLock()
LEARNING_SUMMARY_LOCK = threading.RLock()
LESSON_METADATA_CACHE_LOCK = threading.RLock()
LESSON_PROGRESS_CACHE_LOCK = threading.RLock()
LEARNING_COMPLETION_LOG_CACHE_LOCK = threading.RLock()
SPACE_W_PROGRESS_LOCK = threading.RLock()
SPACE_Q_PROGRESS_LOCK = threading.RLock()
SPACE_V_PROGRESS_LOCK = threading.RLock()
SPACE_P_PROGRESS_LOCK = threading.RLock()
SPACE_PDF_PROGRESS_LOCK = threading.RLock()
# Write-behind store for per-user lesson progress. Saves update the RAM payload
# (authoritative for both reads and writes) and mark the user dirty; a flusher
# thread persists dirty users to disk on an interval, and completion/clear plus
# shutdown force an immediate flush. This keeps many concurrent learners from
# serializing behind a per-space lock and one disk read+write per tick.
SPACE_PROGRESS_STORE_LOCK = threading.RLock()
SPACE_PROGRESS_STORE: dict[str, dict] = {}
SPACE_PROGRESS_FLUSH_INTERVAL_SECONDS = 10.0
SPACE_PROGRESS_FLUSHER_STARTED = False
VOCAB_REGISTRY_LOCK = threading.RLock()
VOCAB_LEADERBOARD_LOCK = threading.RLock()
VOCAB_LEADERBOARD_PERIOD_LOCK = threading.RLock()
VOCAB_LEADERBOARD_REWARD_LOCK = threading.RLock()
VOCAB_LEADERBOARD_VIEWER_LOCK = threading.RLock()
VOCAB_LEADERBOARD_SOCIAL_LOCK = threading.RLock()
VOCAB_LEADERBOARD_CHAT_LOCK = threading.RLock()
VOCAB_LEADERBOARD_NPC_TOP_LOCK = threading.RLock()
SHARED_WORLD_LOCK = threading.RLock()
SHARED_WORLD_KEYBOARD_LOCK = threading.RLock()
SHARED_WORLD_BATTLE_LOCK = threading.RLock()
QM_CITY_TRAINING_LOCK = threading.RLock()
QM_CITY_TRAINING_PROMPT_CACHE_LOCK = threading.RLock()
SHARED_WORLD_LEVEL_CACHE_LOCK = threading.RLock()
SHARED_WORLD_LEVEL_CACHE: dict[str, dict] = {}
SHARED_WORLD_STATE_CACHE: dict[str, object] = {"mtime": -1.0, "state": None, "dirty": False, "last_flush": 0.0}
SHARED_WORLD_STATE_FLUSH_INTERVAL_SECONDS = 3.0
SHARED_WORLD_PROFILE_CACHE: dict[str, tuple[float, dict]] = {}
SHARED_WORLD_LEADERBOARD_META_CACHE: dict[str, object] = {"key": "", "at": 0.0, "payload": {}}
SHARED_WORLD_NPC_CHAT_REPLY_CHANCE_PERCENT = 30
SHARED_WORLD_NPC_CHAT_RADIUS = 0.32
SHARED_WORLD_NPC_CHAT_DELAY_MIN_SECONDS = 10
SHARED_WORLD_NPC_CHAT_DELAY_MAX_SECONDS = 15
SHARED_WORLD_NPC_CHAT_COOLDOWN_MIN_SECONDS = 120
SHARED_WORLD_NPC_CHAT_COOLDOWN_MAX_SECONDS = 240
SHARED_WORLD_CITY_NPC_COUNT = 10
SHARED_WORLD_CITY_NPC_PREFIX = "citynpc"
SHARED_WORLD_CITY_NPC_RETIRE_MIN_SECONDS = 35
SHARED_WORLD_CITY_NPC_RETIRE_MAX_SECONDS = 260
SHARED_WORLD_CITY_NPC_POINTS = [
    (0.18, 0.30),
    (0.34, 0.23),
    (0.52, 0.28),
    (0.72, 0.24),
    (0.84, 0.40),
    (0.68, 0.58),
    (0.48, 0.66),
    (0.26, 0.61),
    (0.16, 0.76),
    (0.80, 0.78),
]
MAIN_VOCAB_SYNC_LOCK = threading.RLock()
SPEAK_SKIP_LOCK = threading.RLock()
INVENTORY_LOCK = threading.RLock()
STT_DEBUG_LOCK = threading.RLock()
SHUTDOWN_LOCK = threading.RLock()
SHUTDOWN_DONE = False
DASHBOARD_LOCK = threading.RLock()
FRONTEND_OBFUSCATION_LOCK = threading.RLock()
CHAT_LOCK = threading.RLock()
CHAT_ONLINE = {}
CHAT_ONLINE_FIRST_SEEN = {}
LESSON_TASK_NOTICE_INSTANT = {}
USER_ACTIVITY_LOCK = threading.RLock()
USER_ACTIVITY = {}
CHAT_VOICE_LOCK = threading.RLock()
CHAT_VOICE_OPTIONS = {"vi": [], "en": [], "ready": False, "error": ""}
CHAT_TTS_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="future-chat-tts")
STREAM_LOCK = threading.RLock()
STREAM_SESSIONS = {}
STREAM_CHUNKS = {}
STREAM_CHUNK_LIMIT = 90
SCREEN_LOCK = threading.RLock()
SCREEN_SESSIONS = {}
SCREEN_FRAME_MAX_CHARS = 2200000
SCREEN_CONTROL_LIMIT = 400
PAINT_LOCK = threading.RLock()
PAINT_STATES = {}
PAINT_MAX_CHARS = 16 * 1024 * 1024
SERVER_DATA_MANIFEST_STATE = {
    "dirty": True,
    "manifest": None,
    "signature": "",
    "watcher_started": False,
    "observer": None,
    "timer": None,
    "paths_timer": None,
    "pending_paths": set(),
    "watch_rescan_timer": None,
    "watch_rescan_paths": set(),
    "monitor_thread": None,
    "build_hold_active": False,
    "build_hold_started_at": 0.0,
    "build_hold_last_activity_at": 0.0,
    "build_hold_until": 0.0,
    "build_hold_timer": None,
    "build_hold_requests": 0,
    "build_hold_apply_requested": False,
    "build_hold_requires_apply": False,
    "build_sessions": {},
    "build_hold_full_refresh_pending": False,
    "build_hold_publish_in_progress": False,
}
MAIN_VOCAB_SYNC_STATE: dict[str, dict] = {}
MAIN_VOCAB_SYNC_MIN_SECONDS = 10.0
MAIN_VOCAB_LOGIN_SYNC_MIN_SECONDS = 3600.0
MAIN_VOCAB_SYNC_ALL_STATE = {"running": False, "last": "", "last_result": {}}
LESSON_METADATA_CACHE: dict[str, dict] = {}
LESSON_PROGRESS_CACHE: dict[str, dict] = {}
LEARNING_COMPLETION_LOG_CACHE: dict[str, object] = {"signature": None, "index": {}}
SERVER_DATA_LIST_CACHE: dict[str, dict] = {}
SERVER_DATA_LIST_CACHE_TTL_SECONDS = 600.0
SERVER_DATA_MANIFEST_MONITOR_SECONDS = 3600.0
SERVER_DATA_FILE_CACHE: dict[str, dict] = {}
SERVER_DATA_FILE_CACHE_MAX_ITEMS = 48
SERVER_DATA_FILE_CACHE_MAX_BYTES = 192 * 1024 * 1024
SERVER_DATA_FILE_CACHE_MAX_FILE_BYTES = 64 * 1024 * 1024
DASHBOARD_WATCHER_STARTED = False
DASHBOARD_SHUTDOWN_GRACE_SECONDS = 45.0
DASHBOARD_RETIRE_OLD_SECONDS = 25.0
STT_FAULT_LOG_HANDLE = None
NPC_TOP_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".jfif", ".avif", ".heic", ".heif"}
NPC_TOP_BROWSER_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
NPC_TOP_MIN_SESSION_GAP_MINUTES = 30
NPC_TOP_DAILY_TOTAL_MIN = 25
NPC_TOP_DAILY_TOTAL_MAX = 75
NPC_TOP_SESSION_MIN_WORDS = 12
NPC_TOP_SESSION_MAX_WORDS = 25

SERVER_PARTS_ROOT = FUTURE_ROOT / "server_parts"
SERVER_PART_FILES = (
    "01_core_runtime.py",
    "02_users_auth_settings.py",
    "03_chat_paint_runtime.py",
    "04_ai_language_agents.py",
    "05_stream_screen_security.py",
    "06_process_frontend_runtime.py",
    "06a_postgres_adapter.py",
    "06a_server_database.py",
    "07_server_data_pdf_qmdict.py",
    "08_progress_inventory_vocab.py",
    "09_vocab_world_game.py",
    "10_vocab_build_status.py",
    "11_http_server.py",
)


def _load_server_part(part_name: str) -> None:
    part_path = SERVER_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _server_part_name in SERVER_PART_FILES:
    _load_server_part(_server_part_name)
del _server_part_name
