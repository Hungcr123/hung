"""Validate staged Doraemon Space_P content before any lesson/audio build."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spacep_context")
INVENTORY_NAME = "source_inventory.json"
NON_ENGLISH_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\u0400-\u04ff\u0600-\u06ff]")
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
MOJIBAKE_RE = re.compile(r"(?:Ã.|Â.|â€|ï¿½|�)")
VOICE_PAIRS = {
    "kokoro_vi:mai_linh": {"kokoro:af_jessica"},
    "kokoro_vi:duc_duy": {"kokoro:am_adam", "kokoro:am_michael"},
}


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_word(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).casefold())


# 2026-07-30: Anchor QA thresholds to each authoritative Space_V inventory entry.
def load_inventory(root: Path) -> dict[int, dict[str, object]]:
    payload = json.loads((root / INVENTORY_NAME).read_text(encoding="utf-8-sig"))
    items = payload.get("items") if isinstance(payload, dict) else []
    result: dict[int, dict[str, object]] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            result[int(item.get("file_number"))] = item
        except (TypeError, ValueError):
            continue
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    inventory = load_inventory(args.root)
    specs = sorted((args.root / "workers").rglob("*.spec.json"))
    numbers: Counter[int] = Counter()
    folders: Counter[str] = Counter()
    errors: list[str] = []
    total_words = 0
    total_children = 0
    sentence_locations: dict[str, list[str]] = {}

    for path in specs:
        try:
            spec = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
        file_number = source.get("file_number")
        try:
            file_number = int(file_number)
        except (TypeError, ValueError):
            errors.append(f"{path}: invalid source.file_number")
            continue
        numbers[file_number] += 1
        expected_name = f"file_{file_number:03d}.spec.json"
        if path.name.casefold() != expected_name.casefold():
            errors.append(f"{path}: filename does not match source.file_number {file_number}")
        inventory_item = inventory.get(file_number)
        if not inventory_item:
            errors.append(f"{path}: source.file_number absent from inventory")
            inventory_item = {}
        if clean(source.get("space_v_file")) != clean(inventory_item.get("space_v_file")):
            errors.append(f"{path}: source.space_v_file does not match inventory")
        if clean(source.get("source_folder")) != clean(inventory_item.get("source_folder")):
            errors.append(f"{path}: source.source_folder does not match inventory")
        source_pages = source.get("source_pages") if isinstance(source.get("source_pages"), list) else []
        inventory_pages = inventory_item.get("source_pages") if isinstance(inventory_item.get("source_pages"), list) else []
        if source_pages != inventory_pages:
            errors.append(f"{path}: source.source_pages does not match inventory")
        folders[clean(source.get("source_folder"))] += 1
        nodes = spec.get("nodes") if isinstance(spec.get("nodes"), list) else []
        if len(nodes) != 1:
            errors.append(f"{path}: expected one paragraph node, got {len(nodes)}")
            continue
        node = nodes[0] if isinstance(nodes[0], dict) else {}
        children = node.get("children") if isinstance(node.get("children"), list) else []
        total_children += len(children)
        if not (5 <= len(children) <= 10):
            errors.append(f"{path}: expected 5-10 child sentences, got {len(children)}")
        english = " ".join(clean(child.get("text")) for child in children if isinstance(child, dict))
        word_count = len(WORD_RE.findall(english))
        total_words += word_count
        if not (90 <= word_count <= 115):
            errors.append(f"{path}: paragraph word count {word_count}, expected 90-115")
        if NON_ENGLISH_SCRIPT_RE.search(english):
            errors.append(f"{path}: English paragraph contains a non-English script")
        if clean(node.get("text")) and clean(node.get("text")) != english:
            errors.append(f"{path}: node.text does not equal joined child text")
        child_ids = set()
        for index, child in enumerate(children, 1):
            if not isinstance(child, dict):
                errors.append(f"{path}: child {index} is not an object")
                continue
            child_id = clean(child.get("id"))
            if not child_id or child_id in child_ids:
                errors.append(f"{path}: missing/duplicate child id {child_id!r}")
            child_ids.add(child_id)
            if not clean(child.get("text")) or not clean(child.get("meaning")):
                errors.append(f"{path}: child {index} lacks English/Vietnamese")
            child_text = clean(child.get("text"))
            if len(WORD_RE.findall(child_text)) >= 6:
                sentence_locations.setdefault(child_text.casefold(), []).append(str(path))
            if MOJIBAKE_RE.search(clean(child.get("meaning"))):
                errors.append(f"{path}: child {index} contains Vietnamese mojibake")
            explanations = child.get("explanations") if isinstance(child.get("explanations"), list) else []
            titles = {clean(item.get("title")).casefold() for item in explanations if isinstance(item, dict)}
            required = {"ý nghĩa", "cấu trúc", "từ vựng"}
            if len(explanations) < 3 or not required.issubset(titles):
                errors.append(f"{path}: child {index} lacks required explanations")
            if any(not clean(item.get("text")) for item in explanations if isinstance(item, dict)):
                errors.append(f"{path}: child {index} has empty explanation")
            if any(key in child for key in ("audio", "meaning_audio", "vi_audio", "alt_audio")):
                errors.append(f"{path}: child {index} contains audio before approval")
        vi_voice = clean(spec.get("vi_voice"))
        voice = clean(spec.get("voice"))
        if vi_voice not in VOICE_PAIRS or voice not in VOICE_PAIRS.get(vi_voice, set()):
            errors.append(f"{path}: invalid voice pairing {vi_voice!r} -> {voice!r}")
        if clean(spec.get("alt_voice")) != voice:
            errors.append(f"{path}: alt_voice must equal voice during content staging")
        used_vocab = source.get("target_vocabulary") if isinstance(source.get("target_vocabulary"), list) else []
        inventory_vocab = inventory_item.get("vocabulary") if isinstance(inventory_item.get("vocabulary"), list) else []
        inventory_vocab_normalized = {normalize_word(word) for word in inventory_vocab}
        paragraph_words = {normalize_word(word) for word in WORD_RE.findall(english)}
        missing_vocab = [word for word in used_vocab if normalize_word(word) not in paragraph_words]
        unknown_vocab = [word for word in used_vocab if normalize_word(word) not in inventory_vocab_normalized]
        required_vocab_count = min(5, len({normalize_word(word) for word in inventory_vocab if normalize_word(word)}))
        if len({normalize_word(word) for word in used_vocab if normalize_word(word)}) < required_vocab_count:
            errors.append(f"{path}: fewer than {required_vocab_count} target vocabulary items")
        if missing_vocab:
            errors.append(f"{path}: target vocabulary absent from paragraph: {missing_vocab[:5]}")
        if unknown_vocab:
            errors.append(f"{path}: target vocabulary absent from source inventory: {unknown_vocab[:5]}")
        qa = spec.get("qa") if isinstance(spec.get("qa"), dict) else {}
        for field in ("english_reviewed", "vietnamese_reviewed", "diacritics_reviewed", "flow_reviewed", "vocabulary_reviewed"):
            if qa.get(field) is not True:
                errors.append(f"{path}: QA flag {field} is not true")

    missing = sorted(set(range(1, 256)) - set(numbers))
    duplicates = sorted(number for number, count in numbers.items() if count != 1)
    if missing:
        errors.append(f"missing_file_numbers={missing[:20]} count={len(missing)}")
    if duplicates:
        errors.append(f"duplicate_file_numbers={duplicates[:20]} count={len(duplicates)}")
    repeated_sentences = {
        sentence: locations
        for sentence, locations in sentence_locations.items()
        if len(locations) > 1
    }
    for sentence, locations in sorted(repeated_sentences.items(), key=lambda item: (-len(item[1]), item[0])):
        errors.append(f"repeated sentence in {len(locations)} specs: {sentence!r}")
    build_report_path = args.root / "doraemon_spacep_build_report.json"
    build_report: dict[str, object] = {}
    if build_report_path.is_file():
        try:
            loaded_report = json.loads(build_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded_report, dict):
                build_report = loaded_report
        except Exception as exc:
            errors.append(f"{build_report_path}: invalid build report: {exc}")
    report = {
        "spec_count": len(specs),
        "covered_file_numbers": len(numbers),
        "source_folders": len([key for key in folders if key]),
        "total_paragraph_words": total_words,
        "total_children": total_children,
        "repeated_sentences": len(repeated_sentences),
        "space_p_built": build_report.get("built") == 255 and build_report.get("unique_lesson_ids") == 255,
        "audio_generated": build_report.get("audio_generated") is True,
        "error_count": len(errors),
        "errors": errors[:200],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
