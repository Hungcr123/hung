"""Validate and build content-only Doraemon Space_S manifests from reviewed specs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PACKETS = Path(r"C:\Users\Admin\.codex\plans\doraemon_spaces_context\source_packets.json")
SPEC_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spaces_context\specs")
OUTPUT_ROOT = Path(r"C:\server data\common\Study\Doraemon\Space S Doraemon")
REPORT_PATH = Path(r"C:\Users\Admin\.codex\plans\doraemon_spaces_context\build_report.json")

MAI_LINH = "kokoro_vi:mai_linh"
DUC_DUY = "kokoro_vi:duc_duy"
JESSICA = "kokoro:af_jessica"
MALE_VOICES = {"kokoro:am_adam", "kokoro:am_michael"}
MOJIBAKE = ("\ufffd", "Ã", "Â", "Æ", "Ð", "á»", "áº")
AUDIO_KEYS = {"audio", "meaning_audio", "vi_audio", "alt_audio", "word_audio"}
BANNED_FILLER = (
    "the group pauses to consider",
    "soon afterward the story reveals",
    "as the journey continues everyone learns",
    "the situation changes when they discover",
    "the friends compare the new evidence",
    "keeps the group moving forward",
)


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", text)


def normalized_sentence(text: str) -> str:
    return re.sub(r"[^a-z0-9']+", " ", clean(text).lower()).strip()


def contains_word(text: str, target: str) -> bool:
    target_key = normalized_sentence(target)
    return bool(target_key) and re.search(rf"(?<![a-z0-9']){re.escape(target_key)}(?![a-z0-9'])", normalized_sentence(text)) is not None


def five_grams(text: str) -> set[tuple[str, ...]]:
    tokens = normalized_sentence(text).split()
    return {tuple(tokens[index:index + 5]) for index in range(max(0, len(tokens) - 4))}


def jaccard(left: set, right: set) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def long_path(path: Path) -> str:
    raw = str(path.resolve())
    return f"\\\\?\\{raw}" if sys.platform == "win32" and not raw.startswith("\\\\?\\") else raw


def read_json(path: Path) -> object:
    with open(long_path(path), "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(long_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def strip_audio_fields(value: object) -> None:
    if isinstance(value, dict):
        for key in tuple(value):
            if key in AUDIO_KEYS:
                value.pop(key, None)
            else:
                strip_audio_fields(value[key])
    elif isinstance(value, list):
        for item in value:
            strip_audio_fields(item)


def source_packet_index() -> dict[str, dict]:
    payload = read_json(SOURCE_PACKETS)
    packets = payload.get("packets") if isinstance(payload, dict) else []
    return {clean(packet.get("packet_id")): packet for packet in packets if isinstance(packet, dict)}


# Added 2026-07-30: enforce the content, voice, provenance, and no-audio contract before any write.
def validate_spec(spec: dict, packet: dict) -> dict:
    errors: list[str] = []
    packet_id = clean(spec.get("packet_id"))
    nodes = spec.get("nodes") if isinstance(spec.get("nodes"), list) else []
    if len(nodes) != 1:
        errors.append(f"expected one node, got {len(nodes)}")
    node = nodes[0] if nodes and isinstance(nodes[0], dict) else {}
    children = node.get("children") if isinstance(node.get("children"), list) else []
    source_sentences = {
        normalized_sentence(page.get("corrected_english"))
        for page in packet.get("pages") or []
        if isinstance(page, dict) and clean(page.get("corrected_english"))
    }
    if not 6 <= len(children) <= 9:
        errors.append(f"expected 6-9 children, got {len(children)}")
    english_parts: list[str] = []
    for index, child in enumerate(children, 1):
        if not isinstance(child, dict):
            errors.append(f"child {index} is not an object")
            continue
        english = clean(child.get("text"))
        vietnamese = clean(child.get("meaning"))
        if not english or not vietnamese:
            errors.append(f"child {index} lacks English or Vietnamese")
        english_word_count = len(words(english))
        if english and not 7 <= english_word_count <= 27:
            errors.append(f"child {index} has unnatural length {english_word_count}")
        if english and (not english[0].isupper() or english[-1] not in ".?!"):
            errors.append(f"child {index} lacks polished English punctuation")
        if vietnamese and vietnamese[-1] not in ".?!":
            errors.append(f"child {index} lacks Vietnamese ending punctuation")
        if "doremon" in english.lower() or "doremon" in vietnamese.lower() or "đôrêmon" in vietnamese.lower():
            errors.append(f"child {index} must use the canonical name Doraemon")
        if any(marker in vietnamese for marker in MOJIBAKE):
            errors.append(f"child {index} contains Vietnamese mojibake")
        if AUDIO_KEYS & set(child):
            errors.append(f"child {index} contains audio fields")
        if normalized_sentence(english) in source_sentences:
            errors.append(f"child {index} copies a corrected OCR sentence verbatim")
        english_parts.append(english)
    paragraph = clean(" ".join(english_parts))
    paragraph_key = normalized_sentence(paragraph)
    word_count = len(words(paragraph))
    if not 90 <= word_count <= 115:
        errors.append(f"paragraph word count {word_count} is outside 90-115")
    if clean(node.get("text")) and normalized_sentence(node.get("text")) != normalized_sentence(paragraph):
        errors.append("node text does not match joined children")
    if any(mark in paragraph for mark in ('"', "“", "”")):
        errors.append("direct quoted dialogue is not allowed in the retelling")
    for phrase in BANNED_FILLER:
        if phrase in paragraph_key:
            errors.append(f"generic filler phrase is not allowed: {phrase}")
    for source_sentence in source_sentences:
        if len(source_sentence.split()) >= 5 and source_sentence in paragraph_key:
            errors.append("paragraph copies a corrected OCR sentence verbatim")
    vi_voice = clean(node.get("vi_voice"))
    en_voice = clean(node.get("voice"))
    if vi_voice == MAI_LINH and en_voice != JESSICA:
        errors.append("Mai Linh must pair with Jessica")
    elif vi_voice == DUC_DUY and en_voice not in MALE_VOICES:
        errors.append("Duc Duy must pair with Adam or Michael")
    elif vi_voice not in {MAI_LINH, DUC_DUY}:
        errors.append(f"unsupported Vietnamese voice {vi_voice!r}")
    packet_pages = [int(value) for value in packet.get("source_pages") or []]
    spec_pages = [int(value) for value in spec.get("source_pages") or []]
    if packet_pages != spec_pages:
        errors.append("source_pages differ from source packet")
    packet_vocab = {normalized_sentence(value): clean(value) for value in packet.get("vocabulary") or [] if clean(value)}
    targets = [clean(value) for value in spec.get("target_vocabulary") or [] if clean(value)]
    if not targets:
        errors.append("target_vocabulary is empty")
    for target in targets:
        if normalized_sentence(target) not in packet_vocab:
            errors.append(f"target vocabulary is not in Space_V: {target}")
        elif not contains_word(paragraph, target):
            errors.append(f"target vocabulary is not used: {target}")
    if errors:
        raise ValueError(f"{packet_id}: " + "; ".join(errors))
    return {"paragraph": paragraph, "word_count": word_count, "children": len(children)}


def output_path_for(spec: dict, packet: dict) -> Path:
    source_key = clean(packet.get("source_key"))
    match = re.search(r"File\s+(\d+)", Path(clean(packet.get("vocabulary_file"))).stem, re.IGNORECASE)
    number = match.group(1) if match else f"{abs(hash(clean(spec.get('packet_id')))) % 100000:05d}"
    return OUTPUT_ROOT / source_key / f"{source_key} - Story Retelling {number}.Space_S"


def load_specs(paths: list[Path]) -> list[dict]:
    specs: list[dict] = []
    for path in paths:
        payload = read_json(path)
        rows = payload.get("specs") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError(f"Spec file must contain a list or specs list: {path}")
        specs.extend(row for row in rows if isinstance(row, dict))
    return specs


def validate_cross_spec_duplicates(validated: list[tuple[dict, dict]]) -> None:
    sentence_owner: dict[str, str] = {}
    paragraphs: list[tuple[str, set[tuple[str, ...]]]] = []
    for spec, stats in validated:
        packet_id = clean(spec.get("packet_id"))
        node = spec["nodes"][0]
        for child in node["children"]:
            key = normalized_sentence(child.get("text"))
            if key in sentence_owner:
                raise ValueError(f"Duplicate sentence in {packet_id} and {sentence_owner[key]}: {child.get('text')}")
            sentence_owner[key] = packet_id
        grams = five_grams(stats["paragraph"])
        for other_id, other_grams in paragraphs:
            similarity = jaccard(grams, other_grams)
            if similarity > 0.45:
                raise ValueError(f"Paragraph overlap {similarity:.3f}: {packet_id} vs {other_id}")
        paragraphs.append((packet_id, grams))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("specs", nargs="*", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    spec_paths = args.specs or sorted(SPEC_ROOT.glob("batch_*.json"))
    specs = load_specs(spec_paths)
    if args.limit > 0:
        specs = specs[:args.limit]
    packets = source_packet_index()
    validated: list[tuple[dict, dict]] = []
    seen: set[str] = set()
    validation_errors: list[str] = []
    for spec in specs:
        packet_id = clean(spec.get("packet_id"))
        if packet_id in seen:
            validation_errors.append(f"Duplicate packet_id: {packet_id}")
            continue
        if packet_id not in packets:
            validation_errors.append(f"Unknown packet_id: {packet_id}")
            continue
        seen.add(packet_id)
        try:
            validated.append((spec, validate_spec(spec, packets[packet_id])))
        except ValueError as exc:
            validation_errors.append(str(exc))
    if validation_errors:
        print(json.dumps({"validation_errors": validation_errors[:100], "error_count": len(validation_errors)}, ensure_ascii=False, indent=2))
        raise ValueError(f"Spec validation failed for {len(validation_errors)} item(s)")
    validate_cross_spec_duplicates(validated)

    results: list[dict] = []
    failures: list[dict] = []
    if not args.validate_only:
        os.environ.setdefault("FUTURE_LESSON_IDENTITY_STAGING", "1")
        sys.path.insert(0, str(ROOT))
        import future_paragraph_builder_gui as builder

        for spec, stats in validated:
            packet = packets[clean(spec.get("packet_id"))]
            output_path = output_path_for(spec, packet)
            try:
                if args.resume and output_path.is_file():
                    decoded = builder.decode_future_lesson_document(output_path.read_text(encoding="utf-8-sig"))
                    provenance = decoded.get("source_provenance") if isinstance(decoded.get("source_provenance"), dict) else {}
                    if clean(decoded.get("space_mode")) == "space_s" and clean(provenance.get("packet_id")) == clean(spec.get("packet_id")):
                        results.append({"packet_id": clean(spec.get("packet_id")), "output": str(output_path), "status": "reused", **stats})
                        continue
                payload = builder.normalize_paragraph_payload({
                    "space_mode": "space_s",
                    "format": "Space_S",
                    "title": clean(spec.get("title")),
                    "hint_seconds": int(spec.get("hint_seconds") or 30),
                    "nodes": spec.get("nodes"),
                })
                payload["space_mode"] = "space_s"
                payload["format"] = "Space_S"
                payload["source_provenance"] = {
                    "packet_id": clean(spec.get("packet_id")),
                    "source_key": clean(packet.get("source_key")),
                    "source_pages": packet.get("source_pages") or [],
                    "vocabulary_file": clean(packet.get("vocabulary_file")),
                    "target_vocabulary": spec.get("target_vocabulary") or [],
                }
                builder.annotate_paragraph_pos_payload(payload, force=True)
                builder.annotate_paragraph_ipa_payload(payload, force=True, log=lambda _message: None)
                strip_audio_fields(payload)
                manifest = builder.encode_future_manifest(payload, payload["title"], output_path=output_path, space="Space_S")
                write_text(output_path, manifest)
                decoded = builder.decode_future_lesson_document(manifest)
                if clean(decoded.get("space_mode")) != "space_s" or clean(decoded.get("format")) != "Space_S":
                    raise RuntimeError(f"Decoded Space_S mode mismatch: {output_path}")
                decoded_text = json.dumps(decoded, ensure_ascii=False)
                if any(f'"{key}"' in decoded_text for key in AUDIO_KEYS):
                    raise RuntimeError(f"Audio field leaked into content-only output: {output_path}")
                results.append({"packet_id": clean(spec.get("packet_id")), "output": str(output_path), "status": "built", **stats})
            except Exception as exc:
                failures.append({"packet_id": clean(spec.get("packet_id")), "output": str(output_path), "error": repr(exc)})

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_text(REPORT_PATH, json.dumps({
        "spec_files": [str(path) for path in spec_paths],
        "validated": len(validated),
        "built": len(results),
        "failures": failures,
        "validate_only": bool(args.validate_only),
        "results": results,
    }, ensure_ascii=False, indent=2))
    print(json.dumps({"validated": len(validated), "built": len(results), "failures": len(failures), "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
