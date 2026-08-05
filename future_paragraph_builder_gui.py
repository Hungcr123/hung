from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from future_lesson_builder_gui import (
    CACHE_ROOT,
    audio_duration_ms,
    build_audio_guided_timings,
    build_effect_sounds,
    build_timings,
    builder_server2_build_begin,
    builder_server2_build_end,
    clean_text,
    decode_future_lesson_document,
    edge_vietnamese_voice_specs,
    encode_future_manifest,
    encode_future_payload,
    estimate_duration_ms,
    embedded_voice_label,
    kokoro_vietnamese_voice_specs,
    people_voice_specs,
    phonemize_text,
    synthesize_embedded_audio,
    translate_to_vi,
    write_server_sound_asset,
)


APP_TITLE = "Future Paragraph Builder"
PARAGRAPH_EXTENSION = ".Space_P"
SPEAKING_EXTENSION = ".Space_S"
LISTENING_EXTENSION = ".Space_L"
AUTOSAVE_PATH = CACHE_ROOT / "paragraph_builder_autosave.json"
PREVIEW_DIR = CACHE_ROOT / "space_p_builder_preview"
FUTURE_HTML_PATH = Path(__file__).with_name("future.html")


# Added 2026-07-07: lets Space_P audio builds feed several Server 2 worker lanes at once.
def builder_audio_parallel_workers(task_count: int) -> int:
    raw = os.environ.get("FUTURE_BUILDER_AUDIO_PARALLEL", "")
    try:
        amount = int(float(raw)) if raw else 4
    except Exception:
        amount = 4
    return max(1, min(16, task_count, amount))


def clean_multiline(value: object) -> str:
    lines = [re.sub(r"\s+", " ", str(line or "")).strip() for line in str(value or "").splitlines()]
    return "\n".join(line for line in lines if line)


def paragraph_voice_options() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, key: str) -> None:
        key = clean_text(key)
        if not key:
            return
        lowered = key.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        options.append((clean_text(label) or embedded_voice_label(key), key))

    add("People | Male Adam", "kokoro:am_adam")
    add("People | Female Jessica", "kokoro:af_jessica")
    for label, key in people_voice_specs():
        add(label, key)
    if not options:
        add("Sound of Text | Female US", "sot:en-US")
        add("Sound of Text | Female UK", "sot:en-GB")
    return options


def paragraph_vietnamese_voice_options() -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, key: str) -> None:
        key = clean_text(key)
        if not key:
            return
        lowered = key.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        options.append((clean_text(label) or embedded_voice_label(key), key))

    add("Edge | Vietnamese VN | Nam Minh", "edge:vi-VN-NamMinhNeural")
    add("Edge | Vietnamese VN | Hoai My", "edge:vi-VN-HoaiMyNeural")
    for label, key in list(edge_vietnamese_voice_specs(force_refresh=False)) + list(kokoro_vietnamese_voice_specs()):
        add(label, key)
    return options


def split_parent_text(text: str, delimiter: str = ".") -> list[str]:
    marker = str(delimiter or ".")
    source = str(text or "")
    if not marker:
        marker = "."
    if marker not in source:
        return [source.strip()] if source.strip() else []
    parts = source.split(marker)
    keep_marker = marker in {".", "?", "!"}
    result: list[str] = []
    for index, part in enumerate(parts):
        cleaned = part.strip()
        if not cleaned:
            continue
        if keep_marker and index < len(parts) - 1 and not cleaned.endswith(marker):
            cleaned = f"{cleaned}{marker}"
        result.append(cleaned)
    return result


def fresh_translate_to_vi(text: str) -> str:
    source = clean_text(text)
    if not source:
        return ""

    def valid_translation(value: object) -> str:
        translated = clean_text(value)
        if not translated:
            return ""
        if translated.casefold() == source.casefold():
            return ""
        lowered = translated.casefold()
        if lowered.startswith("translate the following") or lowered.startswith("dịch đoạn"):
            return ""
        return translated

    remote_translated = valid_translation(translate_to_vi(source))
    if remote_translated:
        return remote_translated

    try:
        from module_main.Data_Input.Import import Translator

        result = Translator().translate(source, dest="vi", src="en")
        translated = valid_translation(getattr(result, "text", "") or "")
        if translated:
            return translated

        prompt = f"Dịch đoạn tiếng Anh sau sang tiếng Việt tự nhiên, chỉ trả lời bản dịch:\n{source}"
        result = Translator().translate(prompt, dest="vi", src="en")
        translated = valid_translation(getattr(result, "text", "") or "")
        if translated:
            translated = re.sub(r"^(bản dịch|dịch|tiếng việt)\s*[:：-]\s*", "", translated, flags=re.IGNORECASE).strip()
            return valid_translation(translated)
    except Exception:
        pass

    return ""


def paragraph_word_tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:[’'`-][^\W_]+)*", str(text or ""), flags=re.UNICODE)


def normalize_word_notes(raw_notes: object) -> list[dict]:
    notes = raw_notes if isinstance(raw_notes, list) else []
    normalized: list[dict] = []
    for index, item in enumerate(notes):
        source = item if isinstance(item, dict) else {}
        word = clean_text(source.get("word") or source.get("token") or source.get("w"))
        meaning_note = clean_multiline(
            source.get("meaning_note")
            or source.get("meaningNote")
            or source.get("meaning")
            or source.get("m")
        )
        grammar_note = clean_multiline(
            source.get("grammar_note")
            or source.get("grammarNote")
            or source.get("grammar")
            or source.get("g")
        )
        token_index = source.get("index", source.get("token_index", source.get("tokenIndex", index)))
        try:
            token_index = int(token_index)
        except Exception:
            token_index = index
        if word or meaning_note or grammar_note:
            normalized.append({
                "index": max(0, token_index),
                "word": word,
                "meaning_note": meaning_note,
                "grammar_note": grammar_note,
            })
    return normalized


def normalize_word_pos(raw_pos: object) -> list[dict]:
    items = raw_pos if isinstance(raw_pos, list) else []
    normalized: list[dict] = []
    for index, item in enumerate(items):
        source = item if isinstance(item, dict) else {}
        word = clean_text(source.get("word") or source.get("token") or source.get("t") or source.get("w"))
        pos = clean_text(source.get("pos") or source.get("p")).upper()
        tag = clean_text(source.get("tag") or source.get("tg"))
        lemma = clean_text(source.get("lemma") or source.get("l"))
        dep = clean_text(source.get("dep") or source.get("d"))
        head = clean_text(source.get("head") or source.get("h"))
        ipa = clean_text(source.get("ipa") or source.get("phonetic") or source.get("pronunciation"))
        ipa_us = clean_text(source.get("ipa_us") or source.get("ipaUS"))
        ipa_uk = clean_text(source.get("ipa_uk") or source.get("ipaUK"))
        token_index = source.get("index", source.get("token_index", source.get("tokenIndex", source.get("i", index))))
        try:
            token_index = int(token_index)
        except Exception:
            token_index = index
        if word or pos or tag or lemma or dep or head or ipa or ipa_us or ipa_uk:
            row = {
                "index": max(0, token_index),
                "word": word,
                "pos": pos,
                "tag": tag,
                "lemma": lemma,
                "dep": dep,
                "head": head,
            }
            if ipa:
                row["ipa"] = ipa
            if ipa_us:
                row["ipa_us"] = ipa_us
            if ipa_uk:
                row["ipa_uk"] = ipa_uk
            normalized.append(row)
    return normalized


def normalize_word_audio(raw_audio: object) -> list[dict]:
    items = raw_audio if isinstance(raw_audio, list) else []
    normalized: list[dict] = []
    for index, item in enumerate(items):
        source = item if isinstance(item, dict) else {}
        word = clean_text(source.get("word") or source.get("token") or source.get("t") or source.get("w"))
        token_index = source.get("index", source.get("token_index", source.get("tokenIndex", source.get("i", index))))
        try:
            token_index = int(token_index)
        except Exception:
            token_index = index
        url = clean_text(source.get("url") or source.get("u") or source.get("src"))
        mime = clean_text(source.get("mime") or source.get("m") or "audio/mpeg")
        voice = clean_text(source.get("voice") or source.get("v") or "sot:en-GB")
        origin = clean_text(source.get("source") or source.get("origin") or source.get("s"))
        if word or url:
            normalized.append({
                "index": max(0, token_index),
                "word": word,
                "url": url,
                "mime": mime or "audio/mpeg",
                "voice": voice or "sot:en-GB",
                "source": origin,
            })
    return normalized


_PARAGRAPH_SPACY_MODEL = None
_PARAGRAPH_SPACY_ATTEMPTED = False


# Added 2026-07-13: lock paragraph parsing to the local large spaCy model under C:\QMLearn.
def paragraph_spacy_model_candidates() -> list[str]:
    return [r"C:\QMLearn\en_core_web_lg"]


def paragraph_spacy_model():
    global _PARAGRAPH_SPACY_MODEL, _PARAGRAPH_SPACY_ATTEMPTED
    if _PARAGRAPH_SPACY_ATTEMPTED:
        return _PARAGRAPH_SPACY_MODEL
    _PARAGRAPH_SPACY_ATTEMPTED = True
    try:
        import spacy  # type: ignore

        for candidate in paragraph_spacy_model_candidates():
            try:
                _PARAGRAPH_SPACY_MODEL = spacy.load(candidate)
                break
            except Exception:
                continue
    except Exception:
        _PARAGRAPH_SPACY_MODEL = None
    return _PARAGRAPH_SPACY_MODEL


def paragraph_word_norm(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", clean_text(value).lower().replace("â€™", "'").replace("'", ""))


def fallback_word_pos(word: str, index: int = 0) -> dict:
    lowered = clean_text(word).lower()
    if not lowered:
        pos = ""
    elif lowered in {"a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "our", "their", "every"}:
        pos = "DET"
    elif lowered in {"i", "you", "me", "it", "we", "they", "he", "she"}:
        pos = "PRON"
    elif lowered in {"and", "but", "or"}:
        pos = "CCONJ"
    elif lowered in {"if", "when", "because", "whether", "that"}:
        pos = "SCONJ"
    elif lowered in {"in", "on", "for", "with", "from", "to", "into", "of", "at", "during", "before", "about", "until"}:
        pos = "ADP"
    elif lowered in {"am", "is", "are", "was", "were", "can", "could", "would", "will", "may"}:
        pos = "AUX"
    elif lowered.endswith("ly"):
        pos = "ADV"
    elif lowered.endswith("ing") or lowered.endswith("ed"):
        pos = "VERB"
    elif word[:1].isupper() and index > 0:
        pos = "PROPN"
    else:
        pos = "NOUN"
    return {"pos": pos, "tag": "", "lemma": lowered, "dep": "", "head": ""}


def paragraph_pos_for_text(text: str) -> list[dict]:
    words = paragraph_word_tokens(text)
    if not words:
        return []
    nlp = paragraph_spacy_model()
    spacy_tokens = []
    if nlp is not None:
        try:
            spacy_tokens = [token for token in nlp(clean_text(text)) if not token.is_space and not token.is_punct]
        except Exception:
            spacy_tokens = []
    cursor = 0
    items: list[dict] = []
    for index, word in enumerate(words):
        token = None
        target = paragraph_word_norm(word)
        while cursor < len(spacy_tokens):
            candidate = spacy_tokens[cursor]
            cursor += 1
            if paragraph_word_norm(candidate.text) == target:
                token = candidate
                break
        if token is not None:
            item = {
                "pos": clean_text(getattr(token, "pos_", "")),
                "tag": clean_text(getattr(token, "tag_", "")),
                "lemma": clean_text(getattr(token, "lemma_", "")),
                "dep": clean_text(getattr(token, "dep_", "")),
                "head": clean_text(getattr(getattr(token, "head", None), "text", "")),
            }
        else:
            item = fallback_word_pos(word, index)
        items.append({
            "index": index,
            "word": word,
            **item,
        })
    return normalize_word_pos(items)


def annotate_paragraph_pos_payload(payload: dict, force: bool = False) -> None:
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        children = node.get("children") if isinstance(node.get("children"), list) else []
        for child in children:
            if not isinstance(child, dict):
                continue
            tokens = paragraph_word_tokens(child.get("text") or "")
            existing = normalize_word_pos(child.get("word_pos") or child.get("wordPos") or child.get("wp"))
            if not force and len(existing) == len(tokens):
                child["word_pos"] = existing
                continue
            child["word_pos"] = paragraph_pos_for_text(child.get("text") or "")


def annotate_paragraph_ipa_payload(payload: dict, force: bool = False, log=None, progress=None, start: int = 33, span: int = 8) -> list[str]:
    warnings: list[str] = []
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    child_rows: list[tuple[int, int, dict, str]] = []
    token_words: dict[str, str] = {}
    for node_index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            continue
        node_text = clean_text(node.get("text"))
        if force or not (clean_text(node.get("ipa_us")) and clean_text(node.get("ipa_uk"))):
            if node_text:
                node["ipa_us"] = phonemize_text(node_text, "en-US")
                node["ipa_uk"] = phonemize_text(node_text, "en-GB")
                node["ipa"] = clean_text(node.get("ipa_uk") or node.get("ipa_us"))
        children = node.get("children") if isinstance(node.get("children"), list) else []
        for child_index, child in enumerate(children, start=1):
            if not isinstance(child, dict):
                continue
            text = clean_text(child.get("text"))
            if not text:
                continue
            child_rows.append((node_index, child_index, child, text))
            for token in paragraph_word_tokens(text):
                key = paragraph_word_audio_key(token)
                if key and key not in token_words:
                    token_words[key] = token

    token_ipa: dict[str, tuple[str, str]] = {}
    total = max(1, len(token_words) + len(child_rows))
    done = 0
    for key, word in token_words.items():
        try:
            token_ipa[key] = (phonemize_text(word, "en-US"), phonemize_text(word, "en-GB"))
        except Exception as exc:
            warnings.append(f"IPA word {word}: {exc}")
        done += 1
        if callable(progress):
            progress(start + int((done / total) * span), f"IPA words {done}/{len(token_words)}")

    for node_index, child_index, child, text in child_rows:
        try:
            if force or not (clean_text(child.get("ipa_us")) and clean_text(child.get("ipa_uk"))):
                if callable(log):
                    log(f"IPA node {node_index}.{child_index}")
                child["ipa_us"] = phonemize_text(text, "en-US")
                child["ipa_uk"] = phonemize_text(text, "en-GB")
                child["ipa"] = clean_text(child.get("ipa_uk") or child.get("ipa_us"))
            tokens = paragraph_word_tokens(text)
            rows_by_index = {int(row.get("index", index)): dict(row) for index, row in enumerate(normalize_word_pos(child.get("word_pos") or child.get("wordPos") or child.get("wp")))}
            for token_index, token in enumerate(tokens):
                row = rows_by_index.get(token_index) or {"index": token_index, "word": token}
                row["word"] = clean_text(row.get("word")) or token
                key = paragraph_word_audio_key(token)
                ipa_us, ipa_uk = token_ipa.get(key, ("", ""))
                if ipa_us:
                    row["ipa_us"] = ipa_us
                if ipa_uk:
                    row["ipa_uk"] = ipa_uk
                row["ipa"] = clean_text(row.get("ipa_uk") or row.get("ipa_us") or row.get("ipa"))
                rows_by_index[token_index] = row
            child["word_pos"] = normalize_word_pos([rows_by_index[index] for index in sorted(rows_by_index)])
        except Exception as exc:
            warnings.append(f"IPA node {node_index}.{child_index}: {exc}")
        done += 1
        if callable(progress):
            progress(start + int((done / total) * span), f"IPA segments {child_index}")
    return warnings


def paragraph_word_audio_key(word: str) -> str:
    text = unicodedata.normalize("NFKC", clean_text(word)).lower()
    text = text.replace("â€™", "'").replace("â€˜", "'").replace("`", "'")
    return re.sub(r"[^0-9a-z]+", "", text.replace("'", ""))


def _local_qmlearn_sot_audio_bytes(word: str) -> bytes | None:
    clean_word = clean_text(word)
    if not clean_word:
        return None
    try:
        from module_main.Data_Input.local_sound_loader import load_sound_bytes

        for candidate in dict.fromkeys([clean_word, clean_word.lower(), clean_word.title()]):
            audio_bytes = load_sound_bytes(
                candidate,
                "en-GB",
                data_dir=r"C:\QMLearn\Data",
                quiet=True,
                variant="sot-en-gb",
            )
            if audio_bytes:
                return bytes(audio_bytes)
    except Exception:
        return None
    return None


def _save_qmlearn_sot_audio_bytes(word: str, audio_bytes: bytes) -> None:
    if not audio_bytes:
        return
    try:
        from module_main.Data_Input.local_sound_loader import save_sound_bytes

        save_sound_bytes(
            clean_text(word),
            "en-GB",
            bytes(audio_bytes),
            data_dir=r"C:\QMLearn\Data",
            overwrite=False,
            variant="sot-en-gb",
        )
    except Exception:
        pass


def paragraph_word_audio_asset(word: str, log=None, force_build_id: str = "") -> dict | None:
    clean_word = clean_text(word)
    if not clean_word:
        return None
    audio_bytes = _local_qmlearn_sot_audio_bytes(clean_word)
    mime = "audio/mpeg"
    origin = "qml-data"
    if not audio_bytes:
        if callable(log):
            log(f"Word audio Sound of Text UK: {clean_word}")
        audio_bytes, mime = synthesize_embedded_audio(clean_word, "sot:en-GB", log)
        origin = "sound-of-text"
        _save_qmlearn_sot_audio_bytes(clean_word, audio_bytes)
    safe_word = re.sub(r"[^0-9A-Za-z._-]+", "-", clean_word).strip("-")[:48] or "word"
    prefix = f"spacep-word-en-gb-{safe_word}"
    if force_build_id:
        prefix = f"{prefix}-force-{force_build_id}"
    url = write_server_sound_asset(prefix, bytes(audio_bytes or b""), mime or "audio/mpeg")
    return {
        "url": url,
        "mime": mime or "audio/mpeg",
        "voice": "sot:en-GB",
        "source": origin,
    }


def add_word_audio_to_paragraph_payload(
    payload: dict,
    log=None,
    progress=None,
    start: int = 0,
    span: int = 35,
    force: bool = False,
    force_build_id: str = "",
) -> list[str]:
    warnings: list[str] = []
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    child_rows: list[tuple[dict, list[str]]] = []
    unique_words: dict[str, str] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        children = node.get("children") if isinstance(node.get("children"), list) else []
        for child in children:
            if not isinstance(child, dict):
                continue
            tokens = paragraph_word_tokens(child.get("text") or "")
            existing = normalize_word_audio(child.get("word_audio") or child.get("wordAudio") or child.get("wa"))
            if tokens and not force and len(existing) == len(tokens) and all(clean_text(item.get("url")) for item in existing):
                child["word_audio"] = existing
                continue
            child_rows.append((child, tokens))
            for token in tokens:
                key = paragraph_word_audio_key(token)
                if key and key not in unique_words:
                    unique_words[key] = token

    total = max(1, len(unique_words))
    assets: dict[str, dict] = {}
    for task_index, (key, word) in enumerate(unique_words.items(), start=1):
        try:
            asset = paragraph_word_audio_asset(word, log=log, force_build_id=force_build_id)
            if asset:
                assets[key] = asset
        except Exception as exc:
            warnings.append(f"Word audio {word}: {exc}")
        if callable(progress):
            progress(start + int((task_index / total) * span), f"Word audio {task_index}/{len(unique_words)}")

    for child, tokens in child_rows:
        rows: list[dict] = []
        for token_index, token in enumerate(tokens):
            key = paragraph_word_audio_key(token)
            asset = dict(assets.get(key) or {})
            if not asset:
                continue
            rows.append({
                "index": token_index,
                "word": token,
                **asset,
            })
        if rows:
            child["word_audio"] = normalize_word_audio(rows)
    return warnings


def new_parent_node(index: int) -> dict:
    return {
        "id": f"pnode-{index:03d}",
        "title": f"Paragraph Node {index}",
        "text": "",
        "voice": "kokoro:am_adam",
        "vi_voice": "edge:vi-VN-NamMinhNeural",
        "alt_voice": "kokoro:af_jessica",
        "children": [],
    }


def normalize_paragraph_child(child: object, index: int) -> dict:
    source = child if isinstance(child, dict) else {}
    explanations = source.get("explanations") if isinstance(source.get("explanations"), list) else source.get("e")
    if not isinstance(explanations, list):
        explanations = []
    word_notes = normalize_word_notes(
        source.get("word_notes")
        if isinstance(source.get("word_notes"), list)
        else source.get("wordNotes")
        if isinstance(source.get("wordNotes"), list)
        else source.get("wn")
    )
    word_pos = normalize_word_pos(
        source.get("word_pos")
        if isinstance(source.get("word_pos"), list)
        else source.get("wordPos")
        if isinstance(source.get("wordPos"), list)
        else source.get("wp")
    )
    word_audio = normalize_word_audio(
        source.get("word_audio")
        if isinstance(source.get("word_audio"), list)
        else source.get("wordAudio")
        if isinstance(source.get("wordAudio"), list)
        else source.get("wa")
    )
    return {
        "id": clean_text(source.get("id") or source.get("i") or f"child-{index:03d}"),
        "text": clean_multiline(source.get("text") or source.get("en") or source.get("t")),
        "meaning": clean_multiline(source.get("meaning") or source.get("vi") or source.get("m")),
        "audio": source.get("audio") if isinstance(source.get("audio"), dict) else None,
        "meaning_audio": source.get("meaning_audio") if isinstance(source.get("meaning_audio"), dict) else source.get("vi_audio") if isinstance(source.get("vi_audio"), dict) else None,
        "ipa": clean_text(source.get("ipa") or source.get("phonetic_ipa") or source.get("phoneticIpa") or source.get("phonetic")),
        "ipa_us": clean_text(source.get("ipa_us") or source.get("ipaUS")),
        "ipa_uk": clean_text(source.get("ipa_uk") or source.get("ipaUK")),
        "explanations": [
            {
                "title": clean_text((item if isinstance(item, dict) else {}).get("title") or (item if isinstance(item, dict) else {}).get("t") or f"Explanation {exp_index}"),
                "text": clean_multiline((item if isinstance(item, dict) else {}).get("text") or (item if isinstance(item, dict) else {}).get("body") or (item if isinstance(item, dict) else {}).get("b") or item),
            }
            for exp_index, item in enumerate(explanations, start=1)
            if isinstance(item, (dict, str))
        ],
        "word_notes": word_notes,
        "word_pos": word_pos,
        "word_audio": word_audio,
    }


def normalize_paragraph_payload(payload: dict) -> dict:
    source = payload if isinstance(payload, dict) else {}
    raw_nodes = source.get("nodes") if isinstance(source.get("nodes"), list) else source.get("n")
    if not isinstance(raw_nodes, list):
        raw_nodes = []
    nodes = []
    for index, raw_node in enumerate(raw_nodes, start=1):
        node = raw_node if isinstance(raw_node, dict) else {}
        raw_children = node.get("children") if isinstance(node.get("children"), list) else node.get("c")
        if not isinstance(raw_children, list):
            raw_children = []
        children = [
            child
            for child in (normalize_paragraph_child(item, child_index) for child_index, item in enumerate(raw_children, start=1))
            if child.get("text") or child.get("meaning")
        ]
        text = clean_multiline(node.get("text") or node.get("root") or node.get("r") or node.get("t")) or " ".join(clean_text(child.get("text")) for child in children)
        nodes.append({
            "id": clean_text(node.get("id") or node.get("i") or f"pnode-{index:03d}"),
            "title": clean_text(node.get("title") or node.get("name") or node.get("tt") or f"Paragraph Node {index}"),
            "text": text,
            "voice": clean_text(node.get("voice") or node.get("vc") or source.get("voice") or source.get("vc") or "kokoro:am_adam"),
            "vi_voice": clean_text(node.get("vi_voice") or node.get("viVoice") or node.get("vv") or source.get("vi_voice") or source.get("viVoice") or "edge:vi-VN-NamMinhNeural"),
            "alt_voice": clean_text(node.get("alt_voice") or node.get("altVoice") or node.get("av") or source.get("alt_voice") or source.get("altVoice") or "kokoro:af_jessica"),
            "ipa": clean_text(node.get("ipa") or node.get("phonetic_ipa") or node.get("phoneticIpa") or node.get("phonetic")),
            "ipa_us": clean_text(node.get("ipa_us") or node.get("ipaUS")),
            "ipa_uk": clean_text(node.get("ipa_uk") or node.get("ipaUK")),
            "children": children,
        })
    return {
        "k": "ftp",
        "kind": "future_paragraph_payload",
        "space_mode": clean_text(source.get("space_mode") or source.get("mode") or source.get("sm") or "space_p").lower() or "space_p",
        "format": clean_text(source.get("format") or source.get("fmt") or "Space_P"),
        "title": clean_text(source.get("title") or source.get("t") or "Space_P Paragraph Rewrite"),
        "hint_seconds": int(float(source.get("hint_seconds") or source.get("hintSeconds") or source.get("hint") or 30)),
        "effects": source.get("effects") if isinstance(source.get("effects"), dict) else source.get("fx") if isinstance(source.get("fx"), dict) else {},
        "nodes": nodes or [new_parent_node(1)],
    }


def add_audio_to_paragraph_payload(
    payload: dict,
    log=None,
    progress=None,
    start: int = 0,
    span: int = 90,
    force_build_id: str = "",
) -> list[str]:
    warnings: list[str] = []
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    tasks: list[tuple[int, int, dict, str, str, str, str]] = []

    def timing_tokens_for_child(child: dict, text: str) -> list[dict]:
        words = paragraph_word_tokens(text)
        if not words:
            return []
        rows = normalize_word_pos(child.get("word_pos") or child.get("wordPos") or child.get("wp"))
        rows_by_index = {
            max(0, int(row.get("index", index))): dict(row)
            for index, row in enumerate(rows)
            if isinstance(row, dict)
        }
        tokens: list[dict] = []
        for token_index, word in enumerate(words):
            row = rows_by_index.get(token_index) or {}
            token = {"t": clean_text(row.get("word")) or word}
            ipa = clean_text(row.get("ipa_uk") or row.get("ipa_us") or row.get("ipa"))
            if ipa:
                token["i"] = ipa
            tokens.append(token)
        return tokens

    for node_index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            continue
        voice_key = clean_text(node.get("voice")) or "kokoro:am_adam"
        alt_voice_key = clean_text(node.get("alt_voice") or node.get("altVoice") or node.get("av"))
        vi_voice_key = clean_text(node.get("vi_voice")) or "edge:vi-VN-NamMinhNeural"
        children = node.get("children") if isinstance(node.get("children"), list) else []
        for child_index, child in enumerate(children, start=1):
            if not isinstance(child, dict):
                continue
            audio_text = clean_text(child.get("text"))
            meaning_text = clean_text(child.get("meaning"))
            if meaning_text:
                tasks.append((node_index, child_index, child, "vi", meaning_text, vi_voice_key, "meaning_audio"))
            if audio_text:
                tasks.append((node_index, child_index, child, "en", audio_text, voice_key, "audio"))
                if alt_voice_key and alt_voice_key.lower() != voice_key.lower():
                    tasks.append((node_index, child_index, child, "en-alt", audio_text, alt_voice_key, "alt_audio"))
    total = max(1, len(tasks))
    workers = builder_audio_parallel_workers(len(tasks))

    def build_audio_asset(task: tuple) -> tuple[dict, str]:
        node_index, child_index, child, language, text, voice_key, key = task
        audio_bytes, mime = synthesize_embedded_audio(text, voice_key, log)
        prefix = f"spacep-{node_index:03d}-{child_index:03d}-{language}"
        if force_build_id:
            prefix = f"{prefix}-force-{force_build_id}"
        asset = {
            "url": write_server_sound_asset(prefix, audio_bytes, mime),
            "mime": mime,
            "voice": voice_key,
            "mode": "auto",
        }
        if language != "vi":
            tokens = timing_tokens_for_child(child, text)
            duration = audio_duration_ms(audio_bytes, mime)
            if duration <= 0:
                duration = estimate_duration_ms(text, tokens)
            timings = build_audio_guided_timings(tokens, duration, audio_bytes) or build_timings(tokens, duration)
            if duration > 0:
                asset["duration_ms"] = int(duration)
            if timings:
                asset["timings"] = timings
        return asset, key

    if workers > 1 and tasks:
        if callable(log):
            log(f"Parallel audio build: {len(tasks)} clips | workers {workers}")
        future_map = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for task in tasks:
                node_index, child_index, _child, language, _text, _voice_key, _key = task
                if callable(log):
                    log(f"{language.upper()} audio node {node_index}.{child_index}")
                future_map[executor.submit(build_audio_asset, task)] = task
            for task_index, future in enumerate(as_completed(future_map), start=1):
                node_index, child_index, child, language, _text, _voice_key, _key = future_map[future]
                try:
                    asset, key = future.result()
                    child[key] = asset
                except Exception as exc:
                    label = "Vietnamese" if language == "vi" else "English"
                    warnings.append(f"Node {node_index} child {child_index} {label}: {exc}")
                if callable(progress):
                    progress(start + int((task_index / total) * span), f"Audio {task_index}/{len(tasks)}")
        return warnings

    for task_index, (node_index, child_index, child, language, text, voice_key, key) in enumerate(tasks, start=1):
        try:
            if callable(log):
                log(f"{language.upper()} audio node {node_index}.{child_index}")
            asset, key = build_audio_asset((node_index, child_index, child, language, text, voice_key, key))
            child[key] = asset
        except Exception as exc:
            label = "Vietnamese" if language == "vi" else "English"
            warnings.append(f"Node {node_index} child {child_index} {label}: {exc}")
        if callable(progress):
            progress(start + int((task_index / total) * span), f"Audio {task_index}/{len(tasks)}")
    return warnings


class ParagraphBuildWorker(QThread):
    finished_ok = pyqtSignal(str, list)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, payload: dict, output_path: Path, generate_audio: bool, manifest: bool = True, force: bool = False) -> None:
        super().__init__()
        self.payload = json.loads(json.dumps(payload, ensure_ascii=False))
        self.output_path = Path(output_path)
        self.force = bool(force)
        self.generate_audio = bool(generate_audio) or self.force or clean_text(self.payload.get("space_mode")).lower() in {"space_s", "space_l"}
        self.manifest = bool(manifest)

    def run(self) -> None:
        build_space = clean_text(self.payload.get("format") or self.payload.get("space_mode") or "Space_P")
        build_session = builder_server2_build_begin(build_space, self.output_path)
        build_success = False
        try:
            warnings: list[str] = []
            force_build_id = ""
            if self.force:
                force_build_id = str(int(time.time() * 1000))
                self.payload["build_id"] = force_build_id
                self.payload["force_rebuild"] = True
                self.progress.emit(3, "Force rebuild enabled")
            self.progress.emit(4, "Annotating word part-of-speech")
            annotate_paragraph_pos_payload(self.payload, force=True)
            warnings.extend(add_word_audio_to_paragraph_payload(
                self.payload,
                lambda _message: None,
                lambda value, message: self.progress.emit(value, message),
                start=5,
                span=35,
                force=self.force,
                force_build_id=force_build_id,
            ))
            self.progress.emit(37, "Building IPA pronunciation")
            warnings.extend(annotate_paragraph_ipa_payload(
                self.payload,
                force=self.force,
                log=lambda _message: None,
                progress=lambda value, message: self.progress.emit(value, message),
                start=37,
                span=4,
            ))
            if self.generate_audio:
                warnings.extend(add_audio_to_paragraph_payload(
                    self.payload,
                    lambda _message: None,
                    lambda value, message: self.progress.emit(value, message),
                    start=42,
                    span=51,
                    force_build_id=force_build_id,
                ))
            else:
                self.progress.emit(62, "Preparing payload")
            if not isinstance(self.payload.get("effects"), dict) or not self.payload.get("effects"):
                self.progress.emit(92, "Embedding effect sounds")
                self.payload["effects"] = build_effect_sounds(lambda _message: None)
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.progress.emit(95, "Writing file")
            space_label = clean_text(self.payload.get("format") or self.payload.get("space_mode") or "Space_P")
            code = encode_future_manifest(self.payload, self.payload.get("title") or self.output_path.stem, self.output_path, space_label) if self.manifest else encode_future_payload(self.payload, self.output_path, space_label)
            self.output_path.write_text(code, encoding="utf-8")
            self.progress.emit(100, "Done")
            self.finished_ok.emit(str(self.output_path), warnings)
            build_success = True
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            builder_server2_build_end(build_session, build_space, self.output_path, build_success)


class ExplanationDialog(QDialog):
    def __init__(self, entries: list[dict] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Child Explanations")
        self.resize(720, 480)
        self.entries: list[dict] = [dict(item) for item in (entries or []) if isinstance(item, dict)]
        self.current_index = -1

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Add many explanation nodes for this child segment."))

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.load_entry)
        body.addWidget(self.list_widget, 1)

        editor = QVBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Explanation title")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Vietnamese explanation, grammar note, phrase note...")
        editor.addWidget(QLabel("Title"))
        editor.addWidget(self.title_edit)
        editor.addWidget(QLabel("Content"))
        editor.addWidget(self.text_edit, 1)
        body.addLayout(editor, 2)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        add_button = QPushButton("Add Explanation")
        add_button.clicked.connect(self.add_entry)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self.remove_entry)
        save_button = QPushButton("Save Current")
        save_button.clicked.connect(self.save_current)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        actions.addWidget(add_button)
        actions.addWidget(remove_button)
        actions.addStretch(1)
        actions.addWidget(save_button)
        actions.addWidget(ok_button)
        actions.addWidget(cancel_button)
        layout.addLayout(actions)

        self.refresh_list()
        if self.entries:
            self.list_widget.setCurrentRow(0)

    def refresh_list(self) -> None:
        current = self.current_index
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for index, item in enumerate(self.entries, start=1):
            title = clean_text(item.get("title")) or f"Explanation {index}"
            self.list_widget.addItem(QListWidgetItem(title))
        self.list_widget.blockSignals(False)
        if self.entries:
            self.list_widget.setCurrentRow(max(0, min(current, len(self.entries) - 1)))

    def save_current(self) -> None:
        if 0 <= self.current_index < len(self.entries):
            self.entries[self.current_index] = {
                "title": clean_text(self.title_edit.text()) or f"Explanation {self.current_index + 1}",
                "text": clean_multiline(self.text_edit.toPlainText()),
            }
            self.refresh_list()

    def load_entry(self, row: int) -> None:
        if 0 <= self.current_index < len(self.entries):
            self.entries[self.current_index] = {
                "title": clean_text(self.title_edit.text()) or f"Explanation {self.current_index + 1}",
                "text": clean_multiline(self.text_edit.toPlainText()),
            }
        self.current_index = row
        if 0 <= row < len(self.entries):
            item = self.entries[row]
            self.title_edit.setText(clean_text(item.get("title")))
            self.text_edit.setPlainText(clean_multiline(item.get("text")))
        else:
            self.title_edit.clear()
            self.text_edit.clear()

    def add_entry(self) -> None:
        self.save_current()
        self.entries.append({"title": f"Explanation {len(self.entries) + 1}", "text": ""})
        self.current_index = len(self.entries) - 1
        self.refresh_list()

    def remove_entry(self) -> None:
        if 0 <= self.current_index < len(self.entries):
            del self.entries[self.current_index]
            self.current_index = min(self.current_index, len(self.entries) - 1)
            self.refresh_list()
            self.load_entry(self.current_index)

    def get_entries(self) -> list[dict]:
        self.save_current()
        return [
            {"title": clean_text(item.get("title")), "text": clean_multiline(item.get("text"))}
            for item in self.entries
            if clean_text(item.get("title")) or clean_multiline(item.get("text"))
        ]


class WordAnalysisDialog(QDialog):
    def __init__(self, children: list[dict] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Word Analysis Notes")
        self.resize(1180, 640)
        self.children: list[dict] = [json.loads(json.dumps(child, ensure_ascii=False)) for child in (children or []) if isinstance(child, dict)]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Edit notes for each word in the current large node. These notes are saved inside the Space_P payload."))

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "#",
            "Child segment",
            "Word",
            "Meaning analysis in this sentence",
            "Grammar / structure / relation",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        close_button = QPushButton("Cancel")
        close_button.clicked.connect(self.reject)
        ok_button = QPushButton("Save Notes")
        ok_button.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(close_button)
        actions.addWidget(ok_button)
        layout.addLayout(actions)

        self.populate()

    @staticmethod
    def _note_key(word: str, index: int) -> str:
        return f"{index}:{clean_text(word).lower()}"

    @staticmethod
    def _word_key(word: str) -> str:
        return clean_text(word).lower()

    def _existing_note(self, child: dict, word: str, index: int, used: set[int]) -> dict:
        notes = normalize_word_notes(child.get("word_notes") or child.get("wordNotes") or child.get("wn"))
        keyed = {
            self._note_key(note.get("word", ""), int(note.get("index", note_index) or 0)): (note_index, note)
            for note_index, note in enumerate(notes)
        }
        direct = keyed.get(self._note_key(word, index))
        if direct and direct[0] not in used:
            used.add(direct[0])
            return dict(direct[1])
        lowered = self._word_key(word)
        for note_index, note in enumerate(notes):
            if note_index in used:
                continue
            if self._word_key(note.get("word", "")) == lowered:
                used.add(note_index)
                return dict(note)
        return {}

    def populate(self) -> None:
        self.table.setRowCount(0)
        for child_index, child in enumerate(self.children):
            text = clean_multiline(child.get("text"))
            tokens = paragraph_word_tokens(text)
            used_notes: set[int] = set()
            segment_label = f"{child_index + 1}. {text[:90]}{'...' if len(text) > 90 else ''}"
            for token_index, word in enumerate(tokens):
                note = self._existing_note(child, word, token_index, used_notes)
                row = self.table.rowCount()
                self.table.insertRow(row)
                number_item = QTableWidgetItem(str(row + 1))
                number_item.setFlags(number_item.flags() & ~Qt.ItemIsEditable)
                segment_item = QTableWidgetItem(segment_label)
                segment_item.setFlags(segment_item.flags() & ~Qt.ItemIsEditable)
                word_item = QTableWidgetItem(word)
                word_item.setFlags(word_item.flags() & ~Qt.ItemIsEditable)
                word_item.setData(Qt.UserRole, child_index)
                word_item.setData(Qt.UserRole + 1, token_index)
                meaning_item = QTableWidgetItem(clean_multiline(note.get("meaning_note") or note.get("meaning")))
                grammar_item = QTableWidgetItem(clean_multiline(note.get("grammar_note") or note.get("grammar")))
                self.table.setItem(row, 0, number_item)
                self.table.setItem(row, 1, segment_item)
                self.table.setItem(row, 2, word_item)
                self.table.setItem(row, 3, meaning_item)
                self.table.setItem(row, 4, grammar_item)
        self.table.resizeRowsToContents()

    def get_children(self) -> list[dict]:
        children = [json.loads(json.dumps(child, ensure_ascii=False)) for child in self.children]
        notes_by_child: dict[int, list[dict]] = {index: [] for index in range(len(children))}
        for row in range(self.table.rowCount()):
            word_item = self.table.item(row, 2)
            if word_item is None:
                continue
            child_index = int(word_item.data(Qt.UserRole) or 0)
            token_index = int(word_item.data(Qt.UserRole + 1) or 0)
            word = clean_text(word_item.text())
            meaning_note = clean_multiline(self.table.item(row, 3).text() if self.table.item(row, 3) else "")
            grammar_note = clean_multiline(self.table.item(row, 4).text() if self.table.item(row, 4) else "")
            if not (word or meaning_note or grammar_note):
                continue
            if meaning_note or grammar_note:
                notes_by_child.setdefault(child_index, []).append({
                    "index": token_index,
                    "word": word,
                    "meaning_note": meaning_note,
                    "grammar_note": grammar_note,
                })
        for child_index, child in enumerate(children):
            child["word_notes"] = notes_by_child.get(child_index, [])
        return children


class ParagraphBuilderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.voice_options = paragraph_voice_options()
        self.vi_voice_options = paragraph_vietnamese_voice_options()
        self.nodes: list[dict] = [new_parent_node(1)]
        self.current_index = 0
        self.loading = False
        self.audio_warnings: list[str] = []
        self.build_worker: ParagraphBuildWorker | None = None
        self.worker_mode = ""
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.write_autosave)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        left = QVBoxLayout()
        left.addWidget(QLabel("Large Nodes"))
        self.node_list = QListWidget()
        self.node_list.currentRowChanged.connect(self.change_node)
        left.addWidget(self.node_list, 1)
        node_actions = QHBoxLayout()
        add_node = QPushButton("Add Node")
        add_node.clicked.connect(self.add_node)
        remove_node = QPushButton("Remove")
        remove_node.clicked.connect(self.remove_node)
        node_actions.addWidget(add_node)
        node_actions.addWidget(remove_node)
        left.addLayout(node_actions)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        meta = QGridLayout()
        self.title_edit = QLineEdit("Space_P Paragraph Rewrite")
        self.output_edit = QLineEdit(str(Path.cwd() / "Space_P_Paragraph.Space_P"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("Space_P | paragraph rewrite", "space_p")
        self.format_combo.addItem("Space_S | speaking unlock", "space_s")
        self.format_combo.addItem("Space_L | hidden listening", "space_l")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_output)
        self.hint_seconds = QSpinBox()
        self.hint_seconds.setRange(3, 300)
        self.hint_seconds.setValue(30)
        self.voice_combo = QComboBox()
        self.vi_voice_combo = QComboBox()
        self.alt_voice_combo = QComboBox()
        self.generate_audio_check = QCheckBox("Generate child audio")
        self.generate_audio_check.setChecked(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Idle")
        for label, key in self.voice_options:
            self.voice_combo.addItem(label, key)
            self.alt_voice_combo.addItem(label, key)
        for label, key in self.vi_voice_options:
            self.vi_voice_combo.addItem(label, key)
        self.set_combo_value(self.voice_combo, "kokoro:am_adam")
        self.set_combo_value(self.vi_voice_combo, "edge:vi-VN-NamMinhNeural")
        self.set_combo_value(self.alt_voice_combo, "kokoro:af_jessica")
        meta.addWidget(QLabel("Lesson title"), 0, 0)
        meta.addWidget(self.title_edit, 0, 1, 1, 3)
        meta.addWidget(QLabel("Output"), 1, 0)
        meta.addWidget(self.output_edit, 1, 1, 1, 2)
        meta.addWidget(browse_button, 1, 3)
        meta.addWidget(QLabel("Format"), 2, 0)
        meta.addWidget(self.format_combo, 2, 1)
        meta.addWidget(QLabel("Hint seconds"), 3, 0)
        meta.addWidget(self.hint_seconds, 3, 1)
        meta.addWidget(QLabel("Primary voice"), 3, 2)
        meta.addWidget(self.voice_combo, 3, 3)
        meta.addWidget(QLabel("Vietnamese voice"), 4, 2)
        meta.addWidget(self.vi_voice_combo, 4, 3)
        meta.addWidget(QLabel("Second voice"), 5, 2)
        meta.addWidget(self.alt_voice_combo, 5, 3)
        meta.addWidget(self.generate_audio_check, 6, 3)
        meta.addWidget(self.progress_bar, 7, 0, 1, 4)
        right.addLayout(meta)

        self.node_title_edit = QLineEdit()
        self.node_title_edit.setPlaceholderText("Large node title")
        right.addWidget(self.node_title_edit)

        parent_row = QHBoxLayout()
        self.parent_text = QPlainTextEdit()
        self.parent_text.setPlaceholderText("Paste the large paragraph here. Use . to split into child segments.")
        self.split_delimiter_edit = QLineEdit(".")
        self.split_delimiter_edit.setPlaceholderText("Split mark")
        self.split_delimiter_edit.setMaximumWidth(120)
        self.auto_translate_check = QCheckBox("Auto VI")
        self.auto_translate_check.setChecked(True)
        split_button = QPushButton("Split")
        split_button.setMinimumWidth(110)
        split_button.clicked.connect(self.split_current_parent)
        parent_row.addWidget(self.parent_text, 1)
        parent_row.addWidget(self.split_delimiter_edit)
        parent_row.addWidget(self.auto_translate_check)
        parent_row.addWidget(split_button)
        right.addLayout(parent_row, 2)

        analysis_row = QHBoxLayout()
        self.word_analysis_button = QPushButton("Word Analysis Notes...")
        self.word_analysis_button.setToolTip("Open a word-by-word table for meaning and grammar analysis notes in this large node.")
        self.word_analysis_button.clicked.connect(self.open_word_analysis_notes)
        analysis_row.addStretch(1)
        analysis_row.addWidget(self.word_analysis_button)
        right.addLayout(analysis_row)

        self.child_table = QTableWidget(0, 4)
        self.child_table.setHorizontalHeaderLabels(["English child text", "Vietnamese meaning", "Explanations", ""])
        self.child_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.child_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.child_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.child_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.child_table.verticalHeader().setVisible(False)
        right.addWidget(self.child_table, 3)

        child_actions = QHBoxLayout()
        add_child = QPushButton("Add Child")
        add_child.clicked.connect(lambda: self.add_child_row({"text": "", "meaning": "", "explanations": []}))
        remove_child = QPushButton("Remove Selected Child")
        remove_child.clicked.connect(self.remove_selected_child)
        self.open_button = QPushButton("Open Space_P")
        self.open_button.clicked.connect(self.open_space_p_file)
        self.preview_button = QPushButton("Run Test HTML")
        self.preview_button.clicked.connect(self.run_preview_html)
        self.build_button = QPushButton("Build Space_P")
        self.build_button.clicked.connect(self.build_file)
        self.force_build_button = QPushButton("Force Build")
        self.force_build_button.setToolTip("Rebuild Space_P with fresh Structure and audio URLs, overwriting the selected manifest.")
        self.force_build_button.clicked.connect(self.force_build_file)
        child_actions.addWidget(self.open_button)
        child_actions.addWidget(self.preview_button)
        child_actions.addWidget(add_child)
        child_actions.addWidget(remove_child)
        child_actions.addStretch(1)
        child_actions.addWidget(self.build_button)
        child_actions.addWidget(self.force_build_button)
        right.addLayout(child_actions)
        layout.addLayout(right, 4)

        self.connect_autosave_signals()
        self.sync_format_controls()
        if not self.load_autosave():
            self.refresh_node_list()
            self.load_node(0)

    def connect_autosave_signals(self) -> None:
        self.title_edit.textChanged.connect(self.schedule_autosave)
        self.output_edit.textChanged.connect(self.schedule_autosave)
        self.format_combo.currentIndexChanged.connect(self.sync_format_controls)
        self.format_combo.currentIndexChanged.connect(self.schedule_autosave)
        self.hint_seconds.valueChanged.connect(self.schedule_autosave)
        self.voice_combo.currentIndexChanged.connect(self.schedule_autosave)
        self.vi_voice_combo.currentIndexChanged.connect(self.schedule_autosave)
        self.alt_voice_combo.currentIndexChanged.connect(self.schedule_autosave)
        self.generate_audio_check.toggled.connect(self.schedule_autosave)
        self.node_title_edit.textChanged.connect(self.schedule_autosave)
        self.parent_text.textChanged.connect(self.schedule_autosave)
        self.split_delimiter_edit.textChanged.connect(self.schedule_autosave)
        self.auto_translate_check.toggled.connect(self.schedule_autosave)
        self.child_table.itemChanged.connect(self.schedule_autosave)

    def schedule_autosave(self, *_args) -> None:
        if self.loading:
            return
        self.autosave_timer.start(600)

    def project_state(self) -> dict:
        self.save_current_node()
        return {
            "title": clean_text(self.title_edit.text()) or "Space_P Paragraph Rewrite",
            "output": clean_text(self.output_edit.text()),
            "format": clean_text(self.format_combo.currentData() or "space_p"),
            "hint_seconds": int(self.hint_seconds.value()),
            "split_delimiter": self.split_delimiter_edit.text() or ".",
            "auto_translate": bool(self.auto_translate_check.isChecked()),
            "generate_audio": bool(self.generate_audio_check.isChecked()),
            "current_index": int(self.current_index),
            "nodes": self.nodes,
            "saved_at": int(time.time()),
        }

    def write_autosave(self) -> None:
        if self.loading:
            return
        try:
            AUTOSAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            AUTOSAVE_PATH.write_text(json.dumps(self.project_state(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def apply_project_state(self, data: dict, output_path: str = "") -> None:
        source = data if isinstance(data, dict) else {}
        nodes = source.get("nodes") if isinstance(source.get("nodes"), list) else []
        self.loading = True
        try:
            self.title_edit.setText(clean_text(source.get("title") or source.get("t") or "Space_P Paragraph Rewrite"))
            self.set_combo_value(self.format_combo, clean_text(source.get("format") or source.get("space_mode") or "space_p"))
            if output_path or source.get("output"):
                self.output_edit.setText(clean_text(output_path or source.get("output")))
            self.hint_seconds.setValue(max(3, min(300, int(float(source.get("hint_seconds") or source.get("hintSeconds") or 30)))))
            self.split_delimiter_edit.setText(clean_text(source.get("split_delimiter") or source.get("splitDelimiter") or ".") or ".")
            self.auto_translate_check.setChecked(bool(source.get("auto_translate", True)))
            self.generate_audio_check.setChecked(bool(source.get("generate_audio", True)))
            self.nodes = [dict(node) for node in nodes if isinstance(node, dict)] or [new_parent_node(1)]
            self.current_index = max(0, min(int(source.get("current_index") or 0), len(self.nodes) - 1))
        finally:
            self.loading = False
        self.refresh_node_list()
        self.load_node(self.current_index)
        self.schedule_autosave()

    def load_autosave(self) -> bool:
        if not AUTOSAVE_PATH.is_file():
            return False
        try:
            data = json.loads(AUTOSAVE_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                self.apply_project_state(data)
                return True
        except Exception:
            pass
        return False

    def open_space_p_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Space_P/Space_S/Space_L", self.output_edit.text(), "Space_P/Space_S/Space_L (*.Space_P *.Space_S *.Space_L);;All files (*.*)")
        if not path:
            return
        try:
            payload = decode_future_lesson_document(Path(path).read_text(encoding="utf-8-sig", errors="replace"))
            if not isinstance(payload, dict) or (payload.get("k") != "ftp" and payload.get("kind") != "future_paragraph_payload"):
                raise RuntimeError("This file is not a Space_P/Space_S/Space_L paragraph payload.")
            normalized = normalize_paragraph_payload(payload)
            source_mode = clean_text(payload.get("space_mode") or payload.get("format")).lower()
            suffix = Path(path).suffix.lower()
            if suffix == LISTENING_EXTENSION.lower() or source_mode in {"space_l", "space_l hidden listening"}:
                normalized["format"] = "space_l"
                normalized["space_mode"] = "space_l"
            elif suffix == SPEAKING_EXTENSION.lower() or source_mode in {"space_s", "space_s speaking unlock"}:
                normalized["format"] = "space_s"
                normalized["space_mode"] = "space_s"
            else:
                normalized["format"] = "space_p"
                normalized["space_mode"] = "space_p"
            normalized["output"] = str(Path(path))
            normalized["split_delimiter"] = self.split_delimiter_edit.text() or "."
            normalized["auto_translate"] = self.auto_translate_check.isChecked()
            normalized["generate_audio"] = self.generate_audio_check.isChecked()
            normalized["current_index"] = 0
            self.apply_project_state(normalized, str(Path(path)))
            QMessageBox.information(self, APP_TITLE, f"Loaded:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    @staticmethod
    def set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if clean_text(combo.itemData(index)).lower() == clean_text(value).lower():
                combo.setCurrentIndex(index)
                return

    def selected_space_format(self) -> str:
        value = clean_text(self.format_combo.currentData() if hasattr(self, "format_combo") else "")
        return value if value in {"space_s", "space_l"} else "space_p"

    def selected_output_extension(self) -> str:
        space_format = self.selected_space_format()
        if space_format == "space_s":
            return SPEAKING_EXTENSION
        if space_format == "space_l":
            return LISTENING_EXTENSION
        return PARAGRAPH_EXTENSION

    def sync_format_controls(self, *_args) -> None:
        if not hasattr(self, "format_combo"):
            return
        space_format = self.selected_space_format()
        if hasattr(self, "generate_audio_check") and space_format in {"space_s", "space_l"} and not self.generate_audio_check.isChecked():
            self.generate_audio_check.setChecked(True)
        if space_format == "space_s":
            self.build_button.setText("Build Space_S")
        elif space_format == "space_l":
            self.build_button.setText("Build Space_L")
        else:
            self.build_button.setText("Build Space_P")
        self.open_button.setText("Open Space_P/S/L")
        self.force_build_button.setToolTip("Rebuild selected Space_P/Space_S/Space_L with fresh Structure and audio URLs.")

    def refresh_node_list(self) -> None:
        self.node_list.blockSignals(True)
        self.node_list.clear()
        for index, node in enumerate(self.nodes, start=1):
            title = clean_text(node.get("title")) or f"Paragraph Node {index}"
            self.node_list.addItem(f"{index}. {title}")
        self.node_list.blockSignals(False)
        self.node_list.setCurrentRow(max(0, min(self.current_index, len(self.nodes) - 1)))

    def save_current_node(self) -> None:
        if self.loading or not (0 <= self.current_index < len(self.nodes)):
            return
        node = self.nodes[self.current_index]
        node["title"] = clean_text(self.node_title_edit.text()) or f"Paragraph Node {self.current_index + 1}"
        node["text"] = clean_multiline(self.parent_text.toPlainText())
        node["voice"] = clean_text(self.voice_combo.currentData()) or "kokoro:am_adam"
        node["vi_voice"] = clean_text(self.vi_voice_combo.currentData()) or "edge:vi-VN-NamMinhNeural"
        node["alt_voice"] = clean_text(self.alt_voice_combo.currentData()) or "kokoro:af_jessica"
        node["children"] = self.collect_children()

    def load_node(self, index: int) -> None:
        if not (0 <= index < len(self.nodes)):
            return
        self.loading = True
        node = self.nodes[index]
        self.node_title_edit.setText(clean_text(node.get("title")) or f"Paragraph Node {index + 1}")
        self.parent_text.setPlainText(clean_multiline(node.get("text")))
        self.set_combo_value(self.voice_combo, clean_text(node.get("voice")) or "kokoro:am_adam")
        self.set_combo_value(self.vi_voice_combo, clean_text(node.get("vi_voice")) or "edge:vi-VN-NamMinhNeural")
        self.set_combo_value(self.alt_voice_combo, clean_text(node.get("alt_voice")) or "kokoro:af_jessica")
        self.child_table.setRowCount(0)
        for child in node.get("children") if isinstance(node.get("children"), list) else []:
            self.add_child_row(child if isinstance(child, dict) else {})
        self.loading = False

    def change_node(self, row: int) -> None:
        if row == self.current_index or row < 0:
            return
        self.save_current_node()
        self.current_index = row
        self.load_node(row)
        self.schedule_autosave()

    def add_node(self) -> None:
        self.save_current_node()
        self.nodes.append(new_parent_node(len(self.nodes) + 1))
        self.current_index = len(self.nodes) - 1
        self.refresh_node_list()
        self.load_node(self.current_index)
        self.schedule_autosave()

    def remove_node(self) -> None:
        if len(self.nodes) <= 1:
            QMessageBox.information(self, APP_TITLE, "At least one large node is required.")
            return
        del self.nodes[self.current_index]
        self.current_index = max(0, min(self.current_index, len(self.nodes) - 1))
        self.refresh_node_list()
        self.load_node(self.current_index)
        self.schedule_autosave()

    def add_child_row(self, child: dict) -> None:
        row = self.child_table.rowCount()
        self.child_table.insertRow(row)
        text_item = QTableWidgetItem(clean_multiline(child.get("text")))
        text_item.setData(Qt.UserRole, clean_text(child.get("id")))
        if isinstance(child.get("audio"), dict):
            text_item.setData(Qt.UserRole + 1, dict(child.get("audio")))
        if isinstance(child.get("meaning_audio"), dict):
            text_item.setData(Qt.UserRole + 2, dict(child.get("meaning_audio")))
        text_item.setData(Qt.UserRole + 3, normalize_word_notes(child.get("word_notes") or child.get("wordNotes") or child.get("wn")))
        text_item.setData(Qt.UserRole + 4, normalize_word_pos(child.get("word_pos") or child.get("wordPos") or child.get("wp")))
        text_item.setData(Qt.UserRole + 5, normalize_word_audio(child.get("word_audio") or child.get("wordAudio") or child.get("wa")))
        meaning_item = QTableWidgetItem(clean_multiline(child.get("meaning")))
        self.child_table.setItem(row, 0, text_item)
        self.child_table.setItem(row, 1, meaning_item)
        explanation_count = len(child.get("explanations") if isinstance(child.get("explanations"), list) else [])
        summary = QTableWidgetItem(f"{explanation_count} node{'' if explanation_count == 1 else 's'}")
        summary.setFlags(summary.flags() & ~Qt.ItemIsEditable)
        summary.setData(Qt.UserRole, [dict(item) for item in child.get("explanations", []) if isinstance(item, dict)])
        self.child_table.setItem(row, 2, summary)
        button = QPushButton("Edit...")
        button.clicked.connect(self.edit_explanations_from_button)
        self.child_table.setCellWidget(row, 3, button)
        self.schedule_autosave()

    def collect_children(self) -> list[dict]:
        children: list[dict] = []
        for row in range(self.child_table.rowCount()):
            text = clean_multiline(self.child_table.item(row, 0).text() if self.child_table.item(row, 0) else "")
            meaning = clean_multiline(self.child_table.item(row, 1).text() if self.child_table.item(row, 1) else "")
            summary = self.child_table.item(row, 2)
            explanations = summary.data(Qt.UserRole) if summary else []
            child_id = clean_text(self.child_table.item(row, 0).data(Qt.UserRole) if self.child_table.item(row, 0) else "") or f"child-{row + 1:03d}"
            audio = self.child_table.item(row, 0).data(Qt.UserRole + 1) if self.child_table.item(row, 0) else None
            meaning_audio = self.child_table.item(row, 0).data(Qt.UserRole + 2) if self.child_table.item(row, 0) else None
            word_notes = self.child_table.item(row, 0).data(Qt.UserRole + 3) if self.child_table.item(row, 0) else []
            word_pos = self.child_table.item(row, 0).data(Qt.UserRole + 4) if self.child_table.item(row, 0) else []
            word_audio = self.child_table.item(row, 0).data(Qt.UserRole + 5) if self.child_table.item(row, 0) else []
            if text or meaning or explanations:
                child_payload = {
                    "id": child_id,
                    "text": text,
                    "meaning": meaning,
                    "explanations": [dict(item) for item in explanations if isinstance(item, dict)],
                }
                normalized_notes = normalize_word_notes(word_notes)
                if normalized_notes:
                    child_payload["word_notes"] = normalized_notes
                normalized_pos = normalize_word_pos(word_pos)
                if normalized_pos:
                    child_payload["word_pos"] = normalized_pos
                normalized_audio = normalize_word_audio(word_audio)
                if normalized_audio:
                    child_payload["word_audio"] = normalized_audio
                if isinstance(audio, dict):
                    child_payload["audio"] = dict(audio)
                if isinstance(meaning_audio, dict):
                    child_payload["meaning_audio"] = dict(meaning_audio)
                children.append(child_payload)
        return children

    def split_current_parent(self) -> None:
        text = self.parent_text.toPlainText()
        delimiter = self.split_delimiter_edit.text() or "."
        parts = split_parent_text(text, delimiter)
        if not parts:
            QMessageBox.warning(self, APP_TITLE, "No child segment found. Check the split marker.")
            return
        if self.child_table.rowCount():
            answer = QMessageBox.question(self, APP_TITLE, "Replace current child rows with split text?")
            if answer != QMessageBox.Yes:
                return
        self.child_table.setRowCount(0)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        untranslated: list[str] = []
        try:
            for part in parts:
                meaning = fresh_translate_to_vi(part) if self.auto_translate_check.isChecked() else ""
                if self.auto_translate_check.isChecked() and not meaning:
                    untranslated.append(part)
                self.add_child_row({"text": part, "meaning": meaning, "explanations": []})
                QApplication.processEvents()
        finally:
            QApplication.restoreOverrideCursor()
        self.schedule_autosave()
        if untranslated:
            QMessageBox.warning(
                self,
                APP_TITLE,
                "Some child segments could not be freshly translated. Their Vietnamese cells were left blank instead of falling back to the English text.",
            )

    def open_word_analysis_notes(self) -> None:
        if not (0 <= self.current_index < len(self.nodes)):
            return
        self.save_current_node()
        children = self.nodes[self.current_index].get("children")
        if not isinstance(children, list) or not children:
            QMessageBox.information(self, APP_TITLE, "Split or add child segments before editing word analysis notes.")
            return
        dialog = WordAnalysisDialog(children, self)
        if dialog.exec_() == QDialog.Accepted:
            self.nodes[self.current_index]["children"] = dialog.get_children()
            self.load_node(self.current_index)
            self.schedule_autosave()

    def edit_explanations(self, row: int) -> None:
        if not (0 <= row < self.child_table.rowCount()):
            return
        summary = self.child_table.item(row, 2)
        entries = summary.data(Qt.UserRole) if summary else []
        dialog = ExplanationDialog(entries if isinstance(entries, list) else [], self)
        if dialog.exec_() == QDialog.Accepted:
            updated = dialog.get_entries()
            if summary is None:
                summary = QTableWidgetItem()
                summary.setFlags(summary.flags() & ~Qt.ItemIsEditable)
                self.child_table.setItem(row, 2, summary)
            summary.setText(f"{len(updated)} node{'' if len(updated) == 1 else 's'}")
            summary.setData(Qt.UserRole, updated)
            self.schedule_autosave()

    def edit_explanations_from_button(self) -> None:
        sender = self.sender()
        for row in range(self.child_table.rowCount()):
            if self.child_table.cellWidget(row, 3) is sender:
                self.edit_explanations(row)
                return

    def remove_selected_child(self) -> None:
        rows = sorted({index.row() for index in self.child_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.child_table.removeRow(row)
        if rows:
            self.schedule_autosave()

    def browse_output(self) -> None:
        extension = self.selected_output_extension()
        path, _ = QFileDialog.getSaveFileName(self, "Save Space_P/Space_S/Space_L", self.output_edit.text(), "Space_P/Space_S/Space_L (*.Space_P *.Space_S *.Space_L)")
        if path:
            output = Path(path)
            if output.suffix.lower() not in {PARAGRAPH_EXTENSION.lower(), SPEAKING_EXTENSION.lower(), LISTENING_EXTENSION.lower()}:
                output = output.with_suffix(extension)
            self.output_edit.setText(str(output))

    def build_payload(self) -> dict:
        self.save_current_node()
        self.audio_warnings = []
        space_format = self.selected_space_format()
        nodes = []
        for index, source in enumerate(self.nodes, start=1):
            children = [
                child for child in (source.get("children") if isinstance(source.get("children"), list) else [])
                if clean_text(child.get("text")) and clean_text(child.get("meaning"))
            ]
            if not children:
                continue
            is_speech_mode = space_format in {"space_s", "space_l"}
            voice_key = "kokoro:am_adam" if is_speech_mode else (clean_text(source.get("voice")) or "kokoro:am_adam")
            vi_voice_key = clean_text(source.get("vi_voice")) or "edge:vi-VN-NamMinhNeural"
            text = clean_multiline(source.get("text")) or " ".join(clean_text(child.get("text")) for child in children)
            nodes.append({
                "id": clean_text(source.get("id")) or f"pnode-{index:03d}",
                "title": clean_text(source.get("title")) or f"Paragraph Node {index}",
                "text": text,
                "voice": voice_key,
                "vi_voice": vi_voice_key,
                "alt_voice": "sot:en-GB" if is_speech_mode else (clean_text(source.get("alt_voice")) or "kokoro:af_jessica"),
                "children": children,
            })
        if not nodes:
            raise RuntimeError("Please create at least one child segment with English text and Vietnamese meaning.")
        return {
            "k": "ftp",
            "kind": "future_paragraph_payload",
            "space_mode": space_format,
            "format": "Space_L" if space_format == "space_l" else ("Space_S" if space_format == "space_s" else "Space_P"),
            "version": 1,
            "title": clean_text(self.title_edit.text()) or ("Space_L Hidden Listening" if space_format == "space_l" else ("Space_S Speaking Unlock" if space_format == "space_s" else "Space_P Paragraph Rewrite")),
            "hint_seconds": int(self.hint_seconds.value()),
            "effects": {},
            "nodes": nodes,
            "created": int(time.time()),
        }

    def build_file(self) -> None:
        self.build_file_with_options(force=False)

    def force_build_file(self) -> None:
        self.build_file_with_options(force=True)

    def build_file_with_options(self, force: bool = False) -> None:
        try:
            payload = self.build_payload()
            extension = self.selected_output_extension()
            output = Path(clean_text(self.output_edit.text()) or ("Space_S_Speaking.Space_S" if extension == SPEAKING_EXTENSION else ("Space_L_Listening.Space_L" if extension == LISTENING_EXTENSION else "Space_P_Paragraph.Space_P")))
            if output.suffix.lower() not in {PARAGRAPH_EXTENSION.lower(), SPEAKING_EXTENSION.lower(), LISTENING_EXTENSION.lower()}:
                output = output.with_suffix(extension)
            self.output_edit.setText(str(output))
            self.start_build_worker(payload, output, "force" if force else "build", manifest=True, force=force)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))

    def set_build_busy(self, busy: bool) -> None:
        for button in (self.open_button, self.preview_button, self.build_button, self.force_build_button, self.word_analysis_button):
            button.setEnabled(not busy)
        self.generate_audio_check.setEnabled(not busy)
        if busy:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Starting...")
        else:
            if self.progress_bar.value() >= 100:
                self.progress_bar.setFormat("Done")
            else:
                self.progress_bar.setFormat("Idle")
        self.setWindowTitle(f"{APP_TITLE} - building in background" if busy else APP_TITLE)

    def start_build_worker(self, payload: dict, output: Path, mode: str, manifest: bool, force: bool = False) -> None:
        if self.build_worker and self.build_worker.isRunning():
            QMessageBox.information(self, APP_TITLE, "A build is already running in the background.")
            return
        self.worker_mode = mode
        self.set_build_busy(True)
        self.build_worker = ParagraphBuildWorker(payload, output, self.generate_audio_check.isChecked(), manifest=manifest, force=force)
        self.build_worker.progress.connect(self.on_build_progress)
        self.build_worker.finished_ok.connect(self.on_build_finished)
        self.build_worker.failed.connect(self.on_build_failed)
        self.build_worker.finished.connect(lambda: self.set_build_busy(False))
        self.build_worker.start()

    def on_build_progress(self, value: int, message: str) -> None:
        progress_value = max(0, min(100, int(value)))
        self.progress_bar.setValue(progress_value)
        self.progress_bar.setFormat(f"{progress_value}% - {clean_text(message) or 'Building'}")

    def on_build_failed(self, message: str) -> None:
        self.worker_mode = ""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Failed")
        QMessageBox.critical(self, APP_TITLE, message)

    def on_build_finished(self, path: str, warnings: list) -> None:
        mode = self.worker_mode
        self.worker_mode = ""
        warning_text = ""
        if warnings:
            warning_text = "\n\nAudio warnings:\n" + "\n".join(str(item) for item in warnings[:6])
            if len(warnings) > 6:
                warning_text += f"\n...and {len(warnings) - 6} more."
        if mode == "preview":
            try:
                self.open_preview_html(Path(path))
            except Exception as exc:
                QMessageBox.critical(self, APP_TITLE, f"Preview build completed but HTML could not open:\n{exc}{warning_text}")
            return
        if mode == "force":
            QMessageBox.information(self, APP_TITLE, f"Force rebuilt with fresh Structure/audio URLs:\n{path}{warning_text}")
            return
        QMessageBox.information(self, APP_TITLE, f"Built:\n{path}{warning_text}")

    def open_preview_html(self, space_p_path: Path) -> None:
        if not FUTURE_HTML_PATH.is_file():
            raise RuntimeError(f"Cannot find future.html: {FUTURE_HTML_PATH}")
        raw_code = space_p_path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw_code:
            raise RuntimeError("Preview Space_P file is empty.")
        source_html = FUTURE_HTML_PATH.read_text(encoding="utf-8-sig", errors="replace")
        preview_script = (
            '<script id="ft-preview-code">'
            f"window.__FTG_PREVIEW_CODE__={json.dumps(raw_code, ensure_ascii=False)};"
            "window.__FTG_PREVIEW_MODE__=true;"
            "window.__FTG_PREVIEW_DEBUG__=true;"
            "</script>"
        )
        if "<script>" not in source_html:
            raise RuntimeError("future.html does not have the runtime script marker for preview injection.")
        preview_html = source_html.replace("<script>", f"{preview_script}\n<script>", 1)
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        preview_path = PREVIEW_DIR / "future_paragraph_preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(preview_path))):
            raise RuntimeError(f"Cannot open preview HTML: {preview_path}")

    def run_preview_html(self) -> None:
        try:
            PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
            payload = self.build_payload()
            safe_title = re.sub(r"[^0-9A-Za-z._-]+", "-", clean_text(payload.get("title"))).strip("-") or "Space_P"
            preview_path = PREVIEW_DIR / f"{safe_title}-preview{PARAGRAPH_EXTENSION}"
            self.start_build_worker(payload, preview_path, "preview", manifest=False)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Cannot run preview HTML:\n{exc}")


def main() -> int:
    app = QApplication(sys.argv)
    window = ParagraphBuilderWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
