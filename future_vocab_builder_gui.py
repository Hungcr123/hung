from __future__ import annotations

import concurrent.futures
import math
import json
import re
import sys
import time
import threading
import traceback
import urllib.parse
from pathlib import Path

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRITE_HTML_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, WRITE_HTML_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scratch_vocab_builder_gui import (  # noqa: E402
    SOT_LOCAL_DATA_DIR,
    VocabularyEntry,
    clean_text,
    display_error_text,
    extract_entries_from_text_passage,
    load_four_column_entries_from_file,
    load_rows_from_file,
    resolve_vocab_entries,
    shared_local_audio_lang_for_voice,
    shared_local_audio_lang_candidates,
    shared_local_audio_voice_dir,
    normalize_sound_of_text_voice_key,
    synthesize_sound_of_text_cached,
)
from future_lesson_builder_gui import (  # noqa: E402
    SERVER_DATA_ROOT,
    build_effect_sounds,
    builder_audio_parallel_workers,
    builder_server2_build_begin,
    builder_server2_build_end,
    encode_future_manifest,
    synthesize_embedded_audio,
    write_server_sound_asset,
)


APP_TITLE = "Future Vocabulary Builder"
VOCAB_EXTENSION = ".Space_V"
VOCAB_STATIC_EXTENSION = ".Space_B"
DEFAULT_CHUNK_SIZE = 25
DEFAULT_OUTPUT_ROOT = SERVER_DATA_ROOT / "common"
DEFAULT_VOICES = [
    ("Sound of Text | Female UK", "sot:en-GB", "uk"),
    ("Sound of Text | Female US", "sot:en-US", "us"),
]
DEFAULT_MEANING_VOICE = ("Sound of Text | Vietnamese", "sot:vi-VN", "vi")
DICT_ALL = None
SOT_ONLINE_SEMAPHORE = threading.BoundedSemaphore(50)


def safe_stem(value: str) -> str:
    text = clean_text(value) or "Vocabulary"
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "Vocabulary"


def chunked(items: list[VocabularyEntry], size: int) -> list[list[VocabularyEntry]]:
    chunk_size = max(1, int(size or DEFAULT_CHUNK_SIZE))
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def vocab_key(value: str) -> str:
    return re.sub(r"\s+", " ", clean_text(value).lower()).strip()


def plain_ascii_key(value: object) -> str:
    text = clean_text(value).lower()
    replacements = {
        "đ": "d",
        "á": "a",
        "à": "a",
        "ả": "a",
        "ã": "a",
        "ạ": "a",
        "ă": "a",
        "ắ": "a",
        "ằ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "ặ": "a",
        "â": "a",
        "ấ": "a",
        "ầ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ậ": "a",
        "é": "e",
        "è": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ẹ": "e",
        "ê": "e",
        "ế": "e",
        "ề": "e",
        "ể": "e",
        "ễ": "e",
        "ệ": "e",
        "í": "i",
        "ì": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ị": "i",
        "ó": "o",
        "ò": "o",
        "ỏ": "o",
        "õ": "o",
        "ọ": "o",
        "ô": "o",
        "ố": "o",
        "ồ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ộ": "o",
        "ơ": "o",
        "ớ": "o",
        "ờ": "o",
        "ở": "o",
        "ỡ": "o",
        "ợ": "o",
        "ú": "u",
        "ù": "u",
        "ủ": "u",
        "ũ": "u",
        "ụ": "u",
        "ư": "u",
        "ứ": "u",
        "ừ": "u",
        "ử": "u",
        "ữ": "u",
        "ự": "u",
        "ý": "y",
        "ỳ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "ỵ": "y",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_irregular_v2_qmv_source(path: Path) -> bool:
    return irregular_qmv_column_label(path) == "V2"


def irregular_qmv_column_label(path: Path) -> str:
    key = plain_ascii_key(path.name)
    if "dong tu bat quy tac" not in key:
        return ""
    if "cot 2" in key or "v2" in key:
        return "V2"
    if "cot 3" in key or "v3" in key:
        return "V3"
    return ""


def is_irregular_qmv_source(path: Path) -> bool:
    return bool(irregular_qmv_column_label(path))


def reverse_irregular_v2_entries(entries: list[VocabularyEntry]) -> list[VocabularyEntry]:
    reversed_entries: list[VocabularyEntry] = []
    for entry in entries:
        base = clean_text(entry.meaning)
        v2 = clean_text(entry.word)
        if not base or not v2:
            continue
        reversed_entries.append(
            VocabularyEntry(
                word=base,
                meaning=v2,
                pron=clean_text(entry.pron),
                word_type="V2",
                lookup_status=entry.lookup_status,
            )
        )
    return reversed_entries


def load_irregular_v2_entries_from_file(path: str) -> list[VocabularyEntry]:
    entries: list[VocabularyEntry] = []
    for row in load_rows_from_file(path):
        v2 = clean_text(row[0] if len(row) > 0 else "")
        base = clean_text(row[1] if len(row) > 1 else "")
        pron = clean_text(row[2] if len(row) > 2 else "")
        if not base or not v2:
            continue
        entries.append(
            VocabularyEntry(
                word=base,
                meaning=v2,
                pron=pron,
                word_type="V2",
                lookup_status="Irregular V2",
            )
        )
    return entries


def load_irregular_v2_spaceb_entries_from_file(path: str) -> list[VocabularyEntry]:
    return load_irregular_spaceb_entries_from_file(path, column_label="V2")


def load_irregular_spaceb_entries_from_file(path: str, column_label: str = "V2") -> list[VocabularyEntry]:
    entries: list[VocabularyEntry] = []
    label = clean_text(column_label).upper() or "V2"
    for row in load_rows_from_file(path):
        changed = clean_text(row[0] if len(row) > 0 else "")
        base = clean_text(row[1] if len(row) > 1 else "")
        pron = clean_text(row[2] if len(row) > 2 else "")
        if not base or not changed:
            continue
        entries.append(
            VocabularyEntry(
                word=changed,
                meaning=base,
                pron=pron,
                word_type=label,
                lookup_status=f"Space_B Irregular {label}",
            )
        )
    return entries


def is_sot_voice_key(voice_key: str) -> bool:
    return clean_text(voice_key).lower().startswith("sot:")


def is_vietnamese_sot_voice_key(voice_key: str) -> bool:
    voice = clean_text(voice_key).lower()
    return voice in {"sot:vi", "sot:vi-vn", "sot:vi_vn"}


def load_dict_all() -> dict:
    global DICT_ALL
    if DICT_ALL is not None:
        return DICT_ALL
    try:
        from dict_all import DICT  # type: ignore

        DICT_ALL = DICT if isinstance(DICT, dict) else {}
    except Exception:
        DICT_ALL = {}
    return DICT_ALL


def qml_data_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(SOT_LOCAL_DATA_DIR.resolve()).as_posix()
    except Exception:
        return ""


def qml_sound_url(path: Path) -> str:
    rel_path = qml_data_relative(path)
    if not rel_path:
        return ""
    return f"/server-data/qm-sound?path={urllib.parse.quote(rel_path, safe='')}"


def resolve_local_sound_path(text: str, voice_key: str) -> Path | None:
    local_text = clean_text(text)
    if not local_text:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import build_sound_storage_stem, resolve_sound_path
    except Exception:
        return None

    if is_vietnamese_sot_voice_key(voice_key):
        try:
            plain_stem = build_sound_storage_stem(local_text)
        except Exception:
            plain_stem = local_text
        if plain_stem:
            voice_dir = shared_local_audio_voice_dir(voice_key)
            candidates = [
                SOT_LOCAL_DATA_DIR / f"{plain_stem}.txt",
                SOT_LOCAL_DATA_DIR / f"{plain_stem}.mp3",
                SOT_LOCAL_DATA_DIR / f"{plain_stem}_vi-VN.mp3",
                voice_dir / f"{plain_stem}.txt",
                voice_dir / f"{plain_stem}.mp3",
                voice_dir / f"{plain_stem}_vi-VN.mp3",
            ]
            for candidate in candidates:
                if candidate.is_file():
                    return candidate
        return None

    langs = shared_local_audio_lang_candidates(voice_key)
    if is_sot_voice_key(voice_key):
        for lang in langs:
            try:
                raw_path = resolve_sound_path(local_text, lang, data_dir=str(SOT_LOCAL_DATA_DIR))
            except Exception:
                raw_path = ""
            if not raw_path:
                continue
            candidate = Path(raw_path)
            try:
                candidate.resolve().relative_to(SOT_LOCAL_DATA_DIR.resolve())
            except Exception:
                continue
            if candidate.is_file():
                return candidate

    voice_dir = shared_local_audio_voice_dir(voice_key)
    for lang in langs:
        try:
            raw_path = resolve_sound_path(local_text, lang, data_dir=str(voice_dir))
        except Exception:
            raw_path = ""
        if not raw_path:
            continue
        candidate = Path(raw_path)
        try:
            candidate.resolve().relative_to(SOT_LOCAL_DATA_DIR.resolve())
        except Exception:
            continue
        if candidate.is_file():
            return candidate
    return None


def local_sound_clip_from_path(path: Path) -> dict:
    url = qml_sound_url(path)
    return {"m": "audio/mpeg", "u": url, "src": "QMLearn/Data"} if url else {}


def force_save_local_sound_bytes(text: str, voice_key: str, audio_bytes: bytes, log) -> Path | None:
    local_text = clean_text(text)
    if not local_text or not audio_bytes:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import (
            build_sound_storage_stem,
            clear_internal_cache,
            save_sound_bytes,
        )
    except Exception as exc:
        log(f"Skip QMLearn/Data save {local_text}: {display_error_text(exc)}")
        return None

    if is_vietnamese_sot_voice_key(voice_key):
        try:
            plain_stem = build_sound_storage_stem(local_text)
            if plain_stem:
                target = SOT_LOCAL_DATA_DIR / f"{plain_stem}.mp3"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bytes(audio_bytes))
                clear_internal_cache()
                log(f"QMLearn/Data forced save: {local_text} ({voice_key})")
                return target
        except Exception as exc:
            log(f"Skip QMLearn/Data plain save {local_text}: {display_error_text(exc)}")

    lang = shared_local_audio_lang_for_voice(voice_key)
    voice_dir = shared_local_audio_voice_dir(voice_key)
    if not lang or not voice_dir:
        return None
    try:
        saved_path = clean_text(save_sound_bytes(local_text, lang, audio_bytes, data_dir=str(voice_dir), overwrite=True))
    except Exception as exc:
        log(f"Skip QMLearn/Data save {local_text}: {display_error_text(exc)}")
        return None
    if saved_path:
        candidate = Path(saved_path)
        try:
            candidate.resolve().relative_to(SOT_LOCAL_DATA_DIR.resolve())
        except Exception:
            return None
        if candidate.is_file():
            log(f"QMLearn/Data forced save: {local_text} ({voice_key})")
            return candidate
    return None


def synthesize_sound_of_text_reliable(text: str, voice_key: str, log) -> bytes:
    last_error: Exception | None = None
    try:
        audio_bytes, _mime = synthesize_embedded_audio(text, voice_key, log)
        if audio_bytes:
            force_save_local_sound_bytes(text, voice_key, audio_bytes, log)
            return bytes(audio_bytes)
    except Exception as exc:
        last_error = exc
        if callable(log):
            log(f"Server 2 audio fallback {clean_text(text)} ({voice_key}): {display_error_text(exc)}")
    for attempt in range(1, 3):
        try:
            with SOT_ONLINE_SEMAPHORE:
                if is_vietnamese_sot_voice_key(voice_key):
                    voice = normalize_sound_of_text_voice_key(voice_key)
                    log(f"Local miss C:\\QMLearn\\Data -> Sound of Text online: {clean_text(text)} ({voice})")
                    from module_main.Soundoftext_Api import Soundoftext_Api

                    api = Soundoftext_Api()
                    audio_bytes = api.load_mp3_bytes(text, voice=voice)
                    if not audio_bytes:
                        raise RuntimeError(f"Sound of Text khong tao duoc audio cho voice {voice}.")
                    force_save_local_sound_bytes(text, voice_key, audio_bytes, log)
                    log(f"Sound of Text: {voice}")
                    return audio_bytes
                return synthesize_sound_of_text_cached(text, voice_key, log_callback=log)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                log(f"Retry Sound of Text {attempt + 1}/2: {clean_text(text)} ({voice_key})")
                time.sleep(0.8)
    if last_error:
        raise last_error
    raise RuntimeError("Sound of Text failed.")


def compact_dict_detail(word: str) -> dict:
    dictionary = load_dict_all()
    key = vocab_key(word)
    raw = ""
    raw_key = ""
    for candidate in (key, key.replace(" ", "-"), key.replace("-", " ")):
        if candidate in dictionary:
            raw_key = candidate
            raw = str(dictionary.get(candidate) or "")
            break
    if not raw:
        return {}
    items = []
    char_budget = 760
    for line in raw.splitlines():
        text = clean_text(line)
        if not text or text.startswith("@"):
            continue
        entry = None
        if text.startswith("*"):
            entry = {"k": "pos", "t": clean_text(text.lstrip("*"))}
        elif text.startswith("-"):
            entry = {"k": "def", "t": clean_text(text.lstrip("-"))}
        elif text.startswith("="):
            sample = clean_text(text.lstrip("="))
            if "+" in sample:
                en, vi = sample.split("+", 1)
                entry = {"k": "ex", "e": clean_text(en), "v": clean_text(vi)}
            else:
                entry = {"k": "ex", "e": sample}
        elif text.startswith("!"):
            entry = {"k": "note", "t": clean_text(text.lstrip("!"))}
        else:
            entry = {"k": "line", "t": text}
        if not entry:
            continue
        preview = json.dumps(entry, ensure_ascii=False)
        if len(preview) > char_budget and items:
            break
        char_budget -= len(preview)
        items.append(entry)
        if len(items) >= 8:
            break
    return {"src": "dict_all", "key": raw_key, "items": items} if items else {}


def fetch_vocab_image(word: str, log) -> dict:
    target = clean_text(word)
    if not vocab_key(target):
        return {}
    # 2026-07-30: Space_V images are resolved only by Server 2 from its configured local picture folder.
    return {
        "u": f"/vocab/image-file?word={urllib.parse.quote(target, safe='')}",
        "s": "Local picture folder",
        "c": target,
    }


def vocab_audio_clip(text: str, voice_key: str, log, *, online_fallback: bool = True) -> dict:
    local_path = resolve_local_sound_path(text, voice_key)
    if local_path is not None:
        log(f"QMLearn/Data link: {clean_text(text)} ({voice_key})")
        return local_sound_clip_from_path(local_path)
    if not online_fallback:
        return {}
    log(f"Sound of Text online request: {clean_text(text)} ({voice_key})")
    audio_bytes = synthesize_sound_of_text_reliable(text, voice_key, log)
    local_path = resolve_local_sound_path(text, voice_key)
    if local_path is not None:
        log(f"QMLearn/Data link saved: {clean_text(text)} ({voice_key})")
        return local_sound_clip_from_path(local_path)
    local_path = force_save_local_sound_bytes(text, voice_key, audio_bytes, log)
    if local_path is not None:
        return local_sound_clip_from_path(local_path)
    asset_path = write_server_sound_asset(f"vocab-{voice_key}-{text[:36]}", audio_bytes, "audio/mpeg")
    return {"m": "audio/mpeg", "u": asset_path, "src": "server-sound-fallback"}


def build_vocab_word_payload(
    item_index: int,
    total_entries: int,
    entry: VocabularyEntry,
    log,
    *,
    word_online_fallback: bool = True,
    include_meaning_audio: bool = True,
    meaning_online_fallback: bool = True,
    include_question_audio: bool = False,
    question_online_fallback: bool = False,
    include_images: bool = True,
    include_dict_detail: bool = True,
    minimal_qmdict: bool = True,
) -> dict | None:
    word = clean_text(entry.word)
    if not word:
        return None
    if minimal_qmdict:
        key = vocab_key(word)
        if not key:
            return None
        log(f"QmDict minimal row {item_index}/{total_entries}: {word}")
        return {"w": word}
    log(f"Audio {item_index}/{total_entries}: {word}")
    audio = {}
    for _label, voice_key, short_key in DEFAULT_VOICES:
        try:
            clip = vocab_audio_clip(word, voice_key, log, online_fallback=word_online_fallback)
            if clip:
                audio[voice_key] = clip
                audio[short_key] = clip
        except Exception as exc:
            log(f"Skip audio {word} {voice_key}: {display_error_text(exc)}")
    meaning = clean_text(entry.meaning)
    question_audio = {}
    if include_question_audio and meaning:
        for _label, voice_key, short_key in DEFAULT_VOICES:
            try:
                clip = vocab_audio_clip(meaning, voice_key, log, online_fallback=question_online_fallback)
                if clip:
                    question_audio[voice_key] = clip
                    question_audio[short_key] = clip
            except Exception as exc:
                log(f"Skip question audio {meaning} {voice_key}: {display_error_text(exc)}")
    if include_meaning_audio and meaning:
        _label, voice_key, short_key = DEFAULT_MEANING_VOICE
        try:
            clip = vocab_audio_clip(meaning, voice_key, log, online_fallback=meaning_online_fallback)
            if clip:
                audio[voice_key] = clip
                audio[short_key] = clip
        except Exception as exc:
            log(f"Skip audio meaning {word} {voice_key}: {display_error_text(exc)}")
    detail = compact_dict_detail(word) if include_dict_detail else {}
    image = fetch_vocab_image(word, log) if include_images else {}
    if detail:
        log(f"Dict detail: {word}")
    if image:
        log(f"Image signal: {word}")
    return {
        "w": word,
        "m": meaning,
        "p": clean_text(entry.pron),
        "ty": clean_text(entry.word_type),
        "au": audio,
        "qau": question_audio,
        "d": detail,
        "im": image,
    }


def build_vocab_payload(
    entries: list[VocabularyEntry],
    *,
    title: str,
    batch_index: int,
    batch_total: int,
    log,
    max_workers: int | None = None,
    word_online_fallback: bool = True,
    include_meaning_audio: bool = True,
    meaning_online_fallback: bool = True,
    include_question_audio: bool = False,
    question_online_fallback: bool = False,
    include_images: bool = True,
    include_dict_detail: bool = True,
    minimal_qmdict: bool = True,
    dynamic_qmdict: bool = True,
    payload_kind: str = "ftv",
) -> dict:
    ordered_words: list[dict | None] = [None] * len(entries)
    worker_count = max(1, min(int(max_workers or builder_audio_parallel_workers(len(entries))), max(1, len(entries))))
    if worker_count <= 1 or len(entries) <= 1:
        for item_index, entry in enumerate(entries, start=1):
            ordered_words[item_index - 1] = build_vocab_word_payload(
                item_index,
                len(entries),
                entry,
                log,
                word_online_fallback=word_online_fallback,
                include_meaning_audio=include_meaning_audio,
                meaning_online_fallback=meaning_online_fallback,
                include_question_audio=include_question_audio,
                question_online_fallback=question_online_fallback,
                include_images=include_images,
                include_dict_detail=include_dict_detail,
                minimal_qmdict=minimal_qmdict,
            )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    build_vocab_word_payload,
                    item_index,
                    len(entries),
                    entry,
                    log,
                    word_online_fallback=word_online_fallback,
                    include_meaning_audio=include_meaning_audio,
                    meaning_online_fallback=meaning_online_fallback,
                    include_question_audio=include_question_audio,
                    question_online_fallback=question_online_fallback,
                    include_images=include_images,
                    include_dict_detail=include_dict_detail,
                    minimal_qmdict=minimal_qmdict,
                ): item_index - 1
                for item_index, entry in enumerate(entries, start=1)
            }
            for future in concurrent.futures.as_completed(futures):
                index = futures[future]
                try:
                    ordered_words[index] = future.result()
                except Exception as exc:
                    log(f"Skip word {index + 1}: {display_error_text(exc)}")
    words = [item for item in ordered_words if item]
    return {
        "k": clean_text(payload_kind) or "ftv",
        "v": 1,
        "t": clean_text(title),
        "created": int(time.time()),
        "batch": {
            "i": int(batch_index),
            "total": int(batch_total),
            "size": len(words),
        },
        "voices": [{"label": label, "key": key} for label, key, _short_key in DEFAULT_VOICES],
        "dyn": {"qmdict": bool(dynamic_qmdict), "minimal": bool(minimal_qmdict)},
        "fx": build_effect_sounds(log),
        "st": {"total": 0, "last": "", "users": {}, "history": []},
        "w": words,
    }


class VocabBuildWorker(QThread):
    progress_text = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, *, raw_text: str, title: str, output_dir: str, chunk_size: int, parent=None) -> None:
        super().__init__(parent)
        self.raw_text = str(raw_text or "")
        self.title = clean_text(title) or "Vocabulary"
        self.output_dir = str(output_dir or DEFAULT_OUTPUT_ROOT)
        self.chunk_size = max(1, int(chunk_size or DEFAULT_CHUNK_SIZE))

    def _log(self, message: str) -> None:
        self.progress_text.emit(clean_text(message))

    def run(self) -> None:
        build_session = builder_server2_build_begin("Space_V", self.output_dir)
        build_success = False
        try:
            self.progress_value.emit(0)
            if not clean_text(self.raw_text):
                raise ValueError("Chua co doan tieng Anh de tach tu vung.")

            self._log("Dang tach tu bang is_valid_word trong main...")
            entries = extract_entries_from_text_passage(self.raw_text)
            if entries:
                self._log(f"Da tach {len(entries)} muc. Dang tra QmDict...")
            resolved = resolve_vocab_entries(entries)
            resolved = [entry for entry in resolved if clean_text(entry.word)]
            if not resolved:
                raise ValueError("Khong tim thay tu vung hop le trong doan da nhap.")

            batches = chunked(resolved, self.chunk_size)
            output_root = Path(self.output_dir)
            output_root.mkdir(parents=True, exist_ok=True)
            stem = safe_stem(self.title)
            paths: list[str] = []
            total_batches = len(batches)

            for batch_number, batch_entries in enumerate(batches, start=1):
                batch_title = stem if total_batches == 1 else f"{stem} {batch_number:03d}"
                self._log(f"Build {batch_number}/{total_batches}: {batch_title}")

                def log_with_progress(message: str) -> None:
                    self._log(message)

                payload = build_vocab_payload(
                    batch_entries,
                    title=batch_title,
                    batch_index=batch_number,
                    batch_total=total_batches,
                    log=log_with_progress,
                )
                target = output_root / f"{batch_title}{VOCAB_EXTENSION}"
                target.write_text(encode_future_manifest(payload, batch_title, target, "Space_V") + "\n", encoding="utf-8")
                paths.append(str(target))
                self._log(f"Da tao: {target}")
                self.progress_value.emit(min(98, int(round((batch_number / total_batches) * 100))))

            self.progress_value.emit(100)
            self.completed.emit(
                {
                    "entry_count": str(len(resolved)),
                    "file_count": str(len(paths)),
                    "output_extension": VOCAB_EXTENSION,
                    "mode_label": "Space_V QmDict",
                    "paths": paths,
                    "output_dir": str(output_root),
                }
            )
            build_success = True
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            builder_server2_build_end(build_session, "Space_V", self.output_dir, build_success)


class QmvFolderBuildWorker(QThread):
    progress_text = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    completed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, *, source_dir: str, output_dir: str, chunk_size: int, parent=None) -> None:
        super().__init__(parent)
        self.source_dir = str(source_dir or "")
        self.output_dir = str(output_dir or DEFAULT_OUTPUT_ROOT)
        self.chunk_size = max(1, int(chunk_size or DEFAULT_CHUNK_SIZE))

    def _log(self, message: str) -> None:
        self.progress_text.emit(clean_text(message))

    def _discover_qmv_files(self, source_root: Path) -> list[Path]:
        files = [
            path
            for path in source_root.rglob("*")
            if path.is_file() and path.suffix.lower() == ".qmv"
        ]
        files.sort(key=lambda path: str(path.relative_to(source_root)).lower())
        return files

    def _target_path_for_batch(
        self,
        *,
        clone_root: Path,
        source_root: Path,
        source_file: Path,
        batch_number: int,
        total_batches: int,
    ) -> Path:
        relative = source_file.relative_to(source_root)
        base_target = clone_root / relative.with_suffix(VOCAB_EXTENSION)
        if total_batches <= 1:
            return base_target
        return base_target.with_name(f"{base_target.stem} {batch_number:03d}{VOCAB_EXTENSION}")

    def run(self) -> None:
        build_session = builder_server2_build_begin("Space_V", self.output_dir)
        build_success = False
        try:
            self.progress_value.emit(0)
            source_root = Path(self.source_dir)
            if not source_root.is_dir():
                raise ValueError("Chua chon folder QMV hop le.")
            output_root = Path(self.output_dir)
            output_root.mkdir(parents=True, exist_ok=True)
            irregular_column_label = irregular_qmv_column_label(source_root)
            irregular_v2_mode = bool(irregular_column_label)
            clone_root = output_root / safe_stem(source_root.name)
            try:
                if clone_root.resolve() == source_root.resolve():
                    suffix_label = "Space_B" if irregular_v2_mode else "Space_V"
                    clone_root = output_root / f"{safe_stem(source_root.name)} {suffix_label}"
            except Exception:
                pass
            clone_root.mkdir(parents=True, exist_ok=True)

            qmv_files = self._discover_qmv_files(source_root)
            if not qmv_files:
                raise ValueError("Folder da chon khong co file .qmv.")

            self._log(f"Tim thay {len(qmv_files)} file QMV. Output clone: {clone_root}")
            if irregular_v2_mode:
                self._log(f"GUI da nhan dien bo dong tu bat quy tac {irregular_column_label}: se xuat .Space_B, hoi tu goc, dap an cot bien doi.")
            paths: list[str] = []
            converted_files = 0
            total_entries = 0
            total_units = max(1, len(qmv_files))

            for file_index, qmv_path in enumerate(qmv_files, start=1):
                rel = qmv_path.relative_to(source_root)
                self._log(f"Doc QMV {file_index}/{len(qmv_files)}: {rel}")
                if irregular_v2_mode:
                    entries = load_irregular_spaceb_entries_from_file(str(qmv_path), column_label=irregular_column_label)
                    self._log(f"Che do Space_B {irregular_column_label}: hien tu goc, bat nhap dong tu bat quy tac cot bien doi.")
                else:
                    entries = load_four_column_entries_from_file(str(qmv_path), mode="normal")
                    entries = resolve_vocab_entries(entries)
                entries = [entry for entry in entries if clean_text(entry.word)]
                if not entries:
                    self._log(f"Bo qua file rong/khong hop le: {rel}")
                    self.progress_value.emit(min(98, int(round((file_index / total_units) * 100))))
                    continue

                batches = chunked(entries, self.chunk_size)
                total_batches = len(batches)
                for batch_number, batch_entries in enumerate(batches, start=1):
                    batch_label = safe_stem(qmv_path.stem)
                    batch_title = batch_label if total_batches == 1 else f"{batch_label} {batch_number:03d}"
                    target = self._target_path_for_batch(
                        clone_root=clone_root,
                        source_root=source_root,
                        source_file=qmv_path,
                        batch_number=batch_number,
                        total_batches=total_batches,
                    )
                    if irregular_v2_mode:
                        target = target.with_suffix(VOCAB_STATIC_EXTENSION)
                    target.parent.mkdir(parents=True, exist_ok=True)

                    def log_with_progress(message: str) -> None:
                        self._log(message)

                    payload = build_vocab_payload(
                        batch_entries,
                        title=batch_title,
                        batch_index=batch_number,
                        batch_total=total_batches,
                        log=log_with_progress,
                        include_meaning_audio=not irregular_v2_mode,
                        include_question_audio=irregular_v2_mode,
                        question_online_fallback=irregular_v2_mode,
                        include_images=not irregular_v2_mode,
                        include_dict_detail=not irregular_v2_mode,
                        minimal_qmdict=not irregular_v2_mode,
                        dynamic_qmdict=not irregular_v2_mode,
                        payload_kind="ftb" if irregular_v2_mode else "ftv",
                    )
                    space_label = "Space_B" if irregular_v2_mode else "Space_V"
                    target.write_text(encode_future_manifest(payload, batch_title, target, space_label) + "\n", encoding="utf-8")
                    paths.append(str(target))
                    total_entries += len(batch_entries)
                    self._log(f"Da convert: {target}")

                converted_files += 1
                self.progress_value.emit(min(98, int(round((file_index / total_units) * 100))))

            self.progress_value.emit(100)
            self.completed.emit(
                {
                    "entry_count": str(total_entries),
                    "file_count": str(len(paths)),
                    "source_count": str(converted_files),
                    "output_extension": VOCAB_STATIC_EXTENSION if irregular_v2_mode else VOCAB_EXTENSION,
                    "mode_label": f"Space_B {irregular_column_label} static-answer" if irregular_v2_mode else "Space_V QmDict",
                    "paths": paths,
                    "output_dir": str(clone_root),
                }
            )
            build_success = True
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            builder_server2_build_end(build_session, "Space_V", self.output_dir, build_success)


class FutureVocabBuilderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: QThread | None = None
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Future Vocabulary Builder")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        hint = QLabel(
            "Nhap mot doan tieng Anh. Builder se dung is_valid_word/QmDict cua main, "
            "cat moi 25 tu thanh mot file .Space_V toi gian chi gom ten tu. "
            "Khi hoc, server se lay nghia/IPA/audio/anh moi nhat tu QmDict. "
            "Co the chon folder QMV de clone ca cay thu muc sang Space_V. "
            "Folder dong tu bat quy tac Cot 2 (V2) hoac Cot 3 (V3) se tu dong xuat .Space_B: hoi tu goc, dap an la cot bien doi, khong lay nghia QmDict."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.name_edit = QLineEdit("Tu vung")
        self.name_edit.setPlaceholderText("Vi du: Tu vung")
        grid.addWidget(QLabel("Ten file"), 0, 0)
        grid.addWidget(self.name_edit, 0, 1)

        self.output_edit = QLineEdit(str(DEFAULT_OUTPUT_ROOT))
        self.output_edit.setPlaceholderText(str(DEFAULT_OUTPUT_ROOT))
        browse_btn = QPushButton("Chon folder")
        browse_btn.clicked.connect(self._choose_output_dir)
        grid.addWidget(QLabel("Output"), 1, 0)
        grid.addWidget(self.output_edit, 1, 1)
        grid.addWidget(browse_btn, 1, 2)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1, 100)
        self.chunk_spin.setValue(DEFAULT_CHUNK_SIZE)
        grid.addWidget(QLabel("So tu moi file"), 2, 0)
        grid.addWidget(self.chunk_spin, 2, 1)

        self.qmv_folder_edit = QLineEdit("")
        self.qmv_folder_edit.setPlaceholderText("Chon folder co cac file .qmv de convert hang loat")
        qmv_browse_btn = QPushButton("Chon QMV folder")
        qmv_browse_btn.clicked.connect(self._choose_qmv_folder)
        self.qmv_mode_label = QLabel("Auto: Space_V QmDict")
        self.qmv_folder_edit.textChanged.connect(lambda _text: self._refresh_qmv_mode_label())
        grid.addWidget(QLabel("QMV folder"), 3, 0)
        grid.addWidget(self.qmv_folder_edit, 3, 1)
        grid.addWidget(qmv_browse_btn, 3, 2)
        grid.addWidget(QLabel("QMV mode"), 4, 0)
        grid.addWidget(self.qmv_mode_label, 4, 1, 1, 2)

        layout.addLayout(grid)

        self.source_edit = QPlainTextEdit()
        self.source_edit.setPlaceholderText("Paste English passage here...")
        self.source_edit.setMinimumHeight(260)
        layout.addWidget(self.source_edit)

        row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Minimal Space_V")
        self.generate_btn.clicked.connect(self._start_generate)
        row.addWidget(self.generate_btn)
        self.convert_qmv_btn = QPushButton("Convert QMV Folder (auto Space_B V2/V3)")
        self.convert_qmv_btn.clicked.connect(self._start_qmv_folder_convert)
        row.addWidget(self.convert_qmv_btn)
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        row.addWidget(self.status_label, 1)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(180)
        layout.addWidget(self.log_edit)

        scroll.setWidget(body)
        root_layout.addWidget(scroll)
        self.setCentralWidget(root)

        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #071112; color: #effefa; font-family: Segoe UI, Arial; }
            QLabel { color: #d8fff7; }
            QLineEdit, QPlainTextEdit, QSpinBox {
                background: rgba(7, 24, 29, 0.95);
                color: #effefa;
                border: 1px solid rgba(70, 240, 215, 0.42);
                border-radius: 10px;
                padding: 8px;
                selection-background-color: #46f0d7;
                selection-color: #061112;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #46f0d7, stop:1 #d86cff);
                color: #061112;
                border: 0;
                border-radius: 11px;
                padding: 10px 14px;
                font-weight: 800;
            }
            QPushButton:disabled { background: #263a3f; color: #95aaa8; }
            QProgressBar {
                border: 1px solid rgba(70, 240, 215, 0.35);
                border-radius: 8px;
                background: #08191d;
                color: #effefa;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: #46f0d7;
            }
            QScrollArea { border: 0; }
            """
        )

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chon folder output", self.output_edit.text().strip() or str(DEFAULT_OUTPUT_ROOT))
        if folder:
            self.output_edit.setText(folder)

    def _choose_qmv_folder(self) -> None:
        start = self.qmv_folder_edit.text().strip() or self.output_edit.text().strip() or str(DEFAULT_OUTPUT_ROOT)
        folder = QFileDialog.getExistingDirectory(self, "Chon folder QMV", start)
        if folder:
            self.qmv_folder_edit.setText(folder)
            self._refresh_qmv_mode_label()

    def _refresh_qmv_mode_label(self) -> bool:
        folder_text = self.qmv_folder_edit.text().strip()
        irregular_column_label = irregular_qmv_column_label(Path(folder_text)) if folder_text else ""
        irregular_v2_mode = bool(irregular_column_label)
        if irregular_v2_mode:
            self.qmv_mode_label.setText(f"Auto: Space_B {irregular_column_label} | hoi tu goc -> dap an cot bien doi")
        else:
            self.qmv_mode_label.setText("Auto: Space_V QmDict")
        return irregular_v2_mode

    def _append_log(self, message: str) -> None:
        self.log_edit.appendPlainText(clean_text(message))

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self.generate_btn.setDisabled(busy)
        self.convert_qmv_btn.setDisabled(busy)
        if status:
            self.status_label.setText(status)

    def _start_generate(self) -> None:
        if self.worker is not None:
            return
        raw_text = self.source_edit.toPlainText()
        if not clean_text(raw_text):
            QMessageBox.warning(self, APP_TITLE, "Hay nhap hoac paste doan tieng Anh truoc.")
            return
        self.log_edit.clear()
        self.progress.setValue(0)
        self._set_busy(True, "Dang tao Space_V toi gian tu QmDict...")
        self.worker = VocabBuildWorker(
            raw_text=raw_text,
            title=self.name_edit.text(),
            output_dir=self.output_edit.text(),
            chunk_size=self.chunk_spin.value(),
        )
        self.worker.progress_text.connect(self._append_log)
        self.worker.progress_value.connect(self.progress.setValue)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _start_qmv_folder_convert(self) -> None:
        if self.worker is not None:
            return
        source_dir = self.qmv_folder_edit.text().strip()
        if not source_dir:
            QMessageBox.warning(self, APP_TITLE, "Hay chon folder QMV truoc.")
            return
        irregular_v2_mode = self._refresh_qmv_mode_label()
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Chon folder output de tao clone Space_B V2/V3" if irregular_v2_mode else "Chon folder output de tao clone Space_V",
            self.output_edit.text().strip() or str(DEFAULT_OUTPUT_ROOT),
        )
        if not output_dir:
            return
        self.output_edit.setText(output_dir)
        self.log_edit.clear()
        self.progress.setValue(0)
        status = "Dang convert QMV folder sang Space_B V2/V3..." if irregular_v2_mode else "Dang convert QMV folder sang Space_V toi gian..."
        self._set_busy(True, status)
        self.worker = QmvFolderBuildWorker(
            source_dir=source_dir,
            output_dir=output_dir,
            chunk_size=self.chunk_spin.value(),
        )
        self.worker.progress_text.connect(self._append_log)
        self.worker.progress_value.connect(self.progress.setValue)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_completed(self, result: dict) -> None:
        self.worker = None
        source_count = clean_text(result.get("source_count", ""))
        source_text = f" | {source_count} QMV source" if source_count else ""
        output_extension = clean_text(result.get("output_extension", "")) or VOCAB_EXTENSION
        mode_label = clean_text(result.get("mode_label", "")) or "Space_V"
        self._set_busy(False, f"Done: {result.get('entry_count', '0')} tu | {result.get('file_count', '0')} file {output_extension}{source_text}.")
        paths = list(result.get("paths") or [])
        for path in paths:
            self._append_log(path)
        QMessageBox.information(
            self,
            APP_TITLE,
            f"Da tao file vocabulary {output_extension} ({mode_label}):\n"
            + "\n".join(paths[:8])
            + ("\n..." if len(paths) > 8 else "")
            + (f"\n\nOutput: {result.get('output_dir', '')}" if result.get("output_dir") else ""),
        )

    def _on_failed(self, error_text: str) -> None:
        self.worker = None
        self._set_busy(False, "Generate failed.")
        self._append_log(error_text)
        QMessageBox.critical(self, APP_TITLE, error_text)


def main() -> int:
    app = QApplication(sys.argv)
    window = FutureVocabBuilderWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
