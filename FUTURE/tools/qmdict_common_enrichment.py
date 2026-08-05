"""Audit and apply reviewed 20-word QmDict enrichment batches for common Space_V."""

from __future__ import annotations

import argparse
import base64
import gzip
import importlib
import json
import os
import re
import sys
from pathlib import Path


DEFAULT_COMMON = Path(r"C:\server data\common")
DEFAULT_QMDICT = Path(r"C:\programe\module_main\Data_Input\QmDict.py")
PROGRAME_ROOT = Path(r"C:\programe")


def decode_space_v(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text.startswith("FTG1."):
        return {}
    encoded = text[5:] + "=" * ((4 - len(text[5:]) % 4) % 4)
    return json.loads(gzip.decompress(base64.urlsafe_b64decode(encoded)).decode("utf-8-sig"))


def common_words(common: Path) -> list[dict]:
    """Added 2026-07-30: preserve common lesson order while deduplicating vocabulary."""
    output = []
    seen = set()
    for path in sorted(common.rglob("*.Space_V"), key=lambda item: str(item).casefold()):
        try:
            payload = decode_space_v(path)
        except Exception:
            continue
        rows = payload.get("w", []) if isinstance(payload, dict) else []
        for row in rows if isinstance(rows, list) else []:
            word = str(row.get("w", "") if isinstance(row, dict) else row).strip()
            key = word.casefold()
            if not word or key in seen:
                continue
            seen.add(key)
            output.append({"word": word, "lesson": str(path)})
    return output


def load_runtime(qmdict_path: Path):
    if str(PROGRAME_ROOT) not in sys.path:
        sys.path.insert(0, str(PROGRAME_ROOT))
    module_name = "module_main.Data_Input.QmDict"
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)
    from module_main.QM_GATE import viewer_vocab_runtime

    return module.QMDICT, viewer_vocab_runtime


def resolve_entry(word: str, qmdict: dict, runtime) -> tuple[str, dict]:
    direct_key = word.strip().upper()
    if direct_key in qmdict:
        return direct_key, runtime.vocab_item_from_valid_line(qmdict[direct_key])
    valid_lines = []
    try:
        runtime.is_valid_word(word, qmdict, valid_lines, "1")
    except Exception:
        valid_lines = []
    if not valid_lines:
        return direct_key, {}
    selected = valid_lines[0]
    selected_key = next((key for key, value in qmdict.items() if value is selected), direct_key)
    return selected_key, runtime.vocab_item_from_valid_line(selected)


def missing_fields(entry: dict) -> list[str]:
    missing = []
    if len(str(entry.get("meaning", "")).strip()) < 12:
        missing.append("meaning")
    if not str(entry.get("type", "")).strip():
        missing.append("type")
    if len(str(entry.get("usage", "")).strip()) < 24:
        missing.append("usage")
    examples = entry.get("examples", [])
    valid_examples = [
        row for row in examples if isinstance(row, dict)
        and str(row.get("en", "")).strip() and str(row.get("vi", "")).strip()
    ] if isinstance(examples, list) else []
    if len(valid_examples) < 2:
        missing.append("examples")
    return missing


def audit(common: Path, qmdict_path: Path) -> list[dict]:
    qmdict, runtime = load_runtime(qmdict_path)
    output = []
    for source in common_words(common):
        key, entry = resolve_entry(source["word"], qmdict, runtime)
        missing = missing_fields(entry)
        if missing:
            output.append({**source, "key": key, "missing": missing, "entry": entry})
    return output


def normalized_examples(value: object) -> list[dict]:
    output = []
    for row in value if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        en = str(row.get("en", "")).strip()
        vi = str(row.get("vi", "")).strip()
        if en and vi:
            output.append({"en": en, "vi": vi})
    return output[:8]


def validate_batch(batch: dict) -> list[str]:
    entries = batch.get("entries", []) if isinstance(batch, dict) else []
    errors = []
    if len(entries) != 20:
        errors.append(f"batch_size={len(entries)} (expected 20)")
    keys = set()
    for index, row in enumerate(entries):
        key = str(row.get("key", "")).strip().upper() if isinstance(row, dict) else ""
        if not key:
            errors.append(f"entry[{index}].key missing")
            continue
        if key in keys:
            errors.append(f"duplicate key: {key}")
        keys.add(key)
        for field in ("word", "meaning", "type", "usage"):
            if not str(row.get(field, "")).strip():
                errors.append(f"{key}.{field} missing")
        meaning = str(row.get("meaning", "")).strip()
        senses = [part.strip() for part in meaning.split(",") if part.strip()]
        if not 2 <= len(senses) <= 5:
            errors.append(f"{key}.meaning_senses={len(senses)}")
        if len({sense.casefold() for sense in senses}) != len(senses):
            errors.append(f"{key}.meaning_duplicate_sense")
        if re.search(r"[^A-Za-zÀ-ỹĐđ\s,]", meaning):
            errors.append(f"{key}.meaning_special_character")
        usage = str(row.get("usage", "")).strip().casefold()
        vietnamese_markers = (" là ", " dùng ", " nghĩa ", " không ", " thường ", " phân biệt ", " khi ", " còn ", " với ", " trong ", " được ", " đã ")
        if sum(marker in f" {usage} " for marker in vietnamese_markers) < 1 or not re.search(r"[À-ỹĐđ]", usage):
            errors.append(f"{key}.usage_not_vietnamese_explanation")
        examples = normalized_examples(row.get("examples", []))
        if len(examples) < 2:
            errors.append(f"{key}.examples={len(examples)}")
        example_keys = {(row["en"].casefold(), row["vi"].casefold()) for row in examples}
        if len(example_keys) != len(examples):
            errors.append(f"{key}.duplicate_examples")
    return errors


def apply_batch(batch: dict, qmdict_path: Path) -> dict:
    errors = validate_batch(batch)
    if errors:
        raise RuntimeError("; ".join(errors))
    qmdict, _runtime = load_runtime(qmdict_path)
    text = qmdict_path.read_text(encoding="utf-8-sig")
    changed = []
    originals = {}
    for update in batch["entries"]:
        key = str(update["key"]).strip().upper()
        old = list(qmdict.get(key, [])) if isinstance(qmdict.get(key), (list, tuple)) else []
        originals[key] = json.loads(json.dumps(old, ensure_ascii=False))
        while len(old) < 8:
            old.append([] if len(old) == 7 else "")
        for index, field in ((0, "word"), (1, "meaning"), (3, "type"), (6, "usage")):
            value = str(update.get(field, "")).strip()
            if value:
                old[index] = value
        old[7] = normalized_examples(update.get("examples", []))
        serialized = json.dumps(old, ensure_ascii=False, separators=(", ", ": "))
        key_text = json.dumps(key, ensure_ascii=False)
        replacement = f"    {key_text}: {serialized},"
        pattern = re.compile(rf"^\s{{4}}{re.escape(key_text)}\s*:\s*.*,$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(replacement, text, count=1)
        else:
            closing = text.rfind("}")
            if closing < 0:
                raise RuntimeError("QmDict closing brace not found")
            text = text[:closing] + replacement + "\n" + text[closing:]
        changed.append(key)
    temp = qmdict_path.with_suffix(qmdict_path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, qmdict_path)
    return {"changed": changed, "originals": originals}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--common", type=Path, default=DEFAULT_COMMON)
    parser.add_argument("--qmdict", type=Path, default=DEFAULT_QMDICT)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.audit:
        rows = audit(args.common, args.qmdict)
        print(json.dumps({"incomplete": len(rows), "rows": rows[:max(0, args.limit)]}, ensure_ascii=False, indent=2))
        return
    if not args.batch:
        parser.error("--batch is required unless --audit is used")
    batch = json.loads(args.batch.read_text(encoding="utf-8-sig"))
    errors = validate_batch(batch)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    result = {"valid": True, "entries": len(batch["entries"])}
    if args.apply:
        result.update(apply_batch(batch, args.qmdict))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
