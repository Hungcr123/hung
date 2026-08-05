"""Validate staged Doraemon Space_W context without building lesson/audio files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_CONTEXT_ROOT = Path(r"C:\Users\Admin\.codex\plans\doraemon_spacew_context")
NON_ENGLISH_SCRIPT_RE = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\u0400-\u04ff\u0600-\u06ff]"
)


def page_number(file_name: object) -> int | None:
    match = re.search(r"\d+", str(file_name or ""))
    return int(match.group()) if match else None


def load_inventory(path: Path) -> dict[tuple[str, int], str]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    expected: dict[tuple[str, int], str] = {}
    for folder in payload.get("folders") or []:
        source_folder = str(folder.get("source_folder") or "").strip()
        for file_name in folder.get("files") or []:
            number = page_number(file_name)
            if source_folder and number is not None:
                expected[(source_folder, number)] = str(file_name)
    return expected


def iter_records(root: Path):
    for path in sorted(root.rglob("*.jsonl")):
        for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            text = raw.strip()
            if text:
                yield path, line_number, json.loads(text)
    for path in sorted(root.rglob("*.context.json")):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        records = payload if isinstance(payload, list) else payload.get("records") or payload.get("pages") or []
        for index, record in enumerate(records, 1):
            yield path, index, record


def validate_about(record: dict, location: str, errors: list[str]) -> None:
    about = record.get("about") or []
    if not isinstance(about, list) or len(about) < 5:
        errors.append(f"{location}: selected record has fewer than five About cards")
        return
    for card_index, card in enumerate(about, 1):
        if not isinstance(card, dict):
            errors.append(f"{location}: About card {card_index} is not an object")
            continue
        answer = str(card.get("a") or "")
        for highlight in card.get("ah") or []:
            term = str((highlight or {}).get("t") or "")
            if not term or term not in answer:
                errors.append(f"{location}: About card {card_index} has invalid highlight {term!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_CONTEXT_ROOT)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()
    inventory_path = args.inventory or args.root / "source_inventory.json"
    expected = load_inventory(inventory_path)
    seen: Counter[tuple[str, int]] = Counter()
    statuses: Counter[str] = Counter()
    selected_by_folder: dict[str, int] = defaultdict(int)
    errors: list[str] = []

    for path, row, record in iter_records(args.root / "workers"):
        location = f"{path}:{row}"
        folder = str(record.get("source_folder") or "").strip()
        page = record.get("source_page")
        try:
            page = int(page)
        except (TypeError, ValueError):
            errors.append(f"{location}: invalid source_page")
            continue
        key = (folder, page)
        seen[key] += 1
        status = str(record.get("status") or "").strip().lower()
        statuses[status] += 1
        if key not in expected:
            errors.append(f"{location}: page is not present in source inventory: {key}")
        if status == "selected":
            selected_by_folder[folder] += 1
            for field in ("ocr_raw", "en", "meaning", "machine_translation", "hint"):
                if not str(record.get(field) or "").strip():
                    errors.append(f"{location}: selected record missing {field}")
            qa = record.get("qa") or {}
            if NON_ENGLISH_SCRIPT_RE.search(str(record.get("en") or "")):
                errors.append(f"{location}: selected English sentence contains a non-English script")
            for field in ("english_reviewed", "vietnamese_reviewed", "diacritics_reviewed", "about_reviewed"):
                if qa.get(field) is not True:
                    errors.append(f"{location}: QA flag {field} is not true")
            validate_about(record, location, errors)
        elif status == "skipped":
            if not str(record.get("skip_reason") or record.get("reason") or "").strip():
                errors.append(f"{location}: skipped record missing skip_reason")
        else:
            errors.append(f"{location}: status must be selected or skipped")

    missing = sorted(set(expected) - set(seen))
    duplicates = sorted(
        key
        for key, count in seen.items()
        if count > 2 or (count == 2 and not any(
            bool(record.get("supplemental"))
            for _, _, record in iter_records(args.root / "workers")
            if (str(record.get("source_folder") or "").strip(), int(record.get("source_page") or -1)) == key
        ))
    )
    if missing:
        errors.append(f"missing_pages={len(missing)} first={missing[:5]}")
    if duplicates:
        errors.append(f"duplicate_pages={len(duplicates)} first={duplicates[:5]}")
    incomplete_groups = {folder: count % 5 for folder, count in selected_by_folder.items() if count % 5}
    report = {
        "expected_pages": len(expected),
        "recorded_pages": len(seen),
        "statuses": dict(statuses),
        "selected_by_folder": dict(sorted(selected_by_folder.items())),
        "future_five_node_files": sum(count // 5 for count in selected_by_folder.values()),
        "incomplete_group_remainders": incomplete_groups,
        "error_count": len(errors),
        "errors": errors[:100],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
