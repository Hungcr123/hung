"""Prepare reviewed OCR/vocabulary provenance packets for Doraemon Space_S drafting."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VOCAB_ROOT_PARENT = Path(r"C:\server data\common\Study\Doraemon")
CONTEXT_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spacew_context\workers")
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spaces_context\source_packets.json")


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def read_text(path: Path) -> str:
    raw_path = str(path.resolve())
    if sys.platform == "win32" and not raw_path.startswith("\\\\?\\"):
        raw_path = "\\\\?\\" + raw_path
    with open(raw_path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def page_numbers(name: str) -> list[int]:
    match = re.search(r"\{([^}]*)\}", name)
    if not match:
        return []
    values: list[int] = []
    for token in match.group(1).split(","):
        token = token.strip()
        if token.isdigit():
            values.append(int(token))
    return sorted(set(values))


def source_key(folder_name: str) -> str:
    match = re.search(r"(Ep\s*\d+|v\d{2})", folder_name, re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot identify source key: {folder_name}")
    token = match.group(1)
    return f"Doraemon_Long_Stories_{token.lower()}" if token.lower().startswith("v") else f"Doremon Ep {int(token[2:]):02d}"


def decode_vocab(path: Path) -> dict:
    sys.path.insert(0, str(ROOT))
    import future_paragraph_builder_gui as paragraph_builder

    return paragraph_builder.decode_future_lesson_document(read_text(path))


def normalized_source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


# Added 2026-07-30: merge every reviewed worker context into one source/page lookup.
def load_context_index() -> tuple[dict[str, dict[int, dict]], dict[str, Path]]:
    index: dict[str, dict[int, dict]] = {}
    paths: dict[str, Path] = {}
    for path in sorted(CONTEXT_ROOT.rglob("*.context.json")):
        payload = json.loads(read_text(path))
        rows = payload if isinstance(payload, list) else payload.get("records") or []
        for row in rows:
            key = normalized_source_key(clean(row.get("source_folder")))
            page = int(row.get("source_page") or 0)
            if key and page > 0:
                index.setdefault(key, {})[page] = row
                paths[key] = path
    return index, paths


def find_vocab_root() -> Path:
    candidates = [p for p in VOCAB_ROOT_PARENT.iterdir() if p.is_dir() and len(list(p.rglob("*.Space_V"))) == 255]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one 255-file vocabulary root, found {len(candidates)}")
    return candidates[0]


def main() -> int:
    vocab_root = find_vocab_root()
    context_cache, context_paths = load_context_index()
    packets: list[dict] = []
    vocab_files = sorted(vocab_root.rglob("*.Space_V"), key=lambda p: str(p).lower())
    if len(vocab_files) != 255:
        raise RuntimeError(f"Expected 255 Space_V files, found {len(vocab_files)}")

    for vocab_path in vocab_files:
        folder_name = vocab_path.parent.name
        key = source_key(folder_name)
        lookup_key = normalized_source_key(key)
        if lookup_key not in context_cache:
            raise FileNotFoundError(f"Reviewed OCR context missing for {key}")
        pages = page_numbers(vocab_path.name)
        decoded = decode_vocab(vocab_path)
        words = [clean(row.get("w")) for row in decoded.get("w") or [] if isinstance(row, dict)]
        words = list(dict.fromkeys(word for word in words if word))
        page_rows = []
        for page in pages:
            row = context_cache[lookup_key].get(page, {})
            page_rows.append({
                "page": page,
                "status": clean(row.get("status")),
                "corrected_english": clean(row.get("en")),
                "ocr_raw": clean(row.get("ocr_raw")),
                "skip_reason": clean(row.get("skip_reason")),
            })
        packets.append({
            "packet_id": f"{key}__{vocab_path.stem}",
            "source_key": key,
            "source_folder": folder_name,
            "source_pages": pages,
            "vocabulary_file": str(vocab_path),
            "vocabulary": words,
            "ocr_context_file": str(context_paths[lookup_key]),
            "pages": page_rows,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "version": 1,
        "source_inventory": str(Path(r"C:\Users\Admin\.codex\plans\doraemon_spacew_context\source_inventory.json")),
        "vocab_root": str(vocab_root),
        "packet_count": len(packets),
        "packets": packets,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "packets": len(packets), "vocab_files": len(vocab_files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
