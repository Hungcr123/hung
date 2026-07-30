"""Inventory first-party frontend HTTP call sites and attribution metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JS_ROOT = ROOT / "FUTURE" / "web" / "js_parts"
CALL_RE = re.compile(r"\b(fetchAuthJson|fetchAuthForm|fetchWithTimeout|fetch)\s*\(")
ROUTE_RE = re.compile(r"^[`\"'](/[^`\"']*)")
SOURCE_RE = re.compile(r"(?:client_source=|clientSource\s*:|uiAction\s*:|X-Future-Source)")


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def main() -> None:
    rows: list[dict[str, object]] = []
    for path in sorted(JS_ROOT.glob("*.js")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for match in CALL_RE.finditer(text):
            tail = text[match.end() : match.end() + 900]
            route_match = ROUTE_RE.match(tail.lstrip())
            route = route_match.group(1).split("?", 1)[0] if route_match else ""
            external = bool(route_match and route_match.group(1).startswith("//"))
            if external:
                continue
            window = text[match.start() : match.end() + 900]
            rows.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "line": line_number(text, match.start()),
                    "wrapper": match.group(1),
                    "route": route or "<dynamic>",
                    "explicit_source": bool(SOURCE_RE.search(window)),
                }
            )

    first_party = [row for row in rows if str(row["route"]).startswith("/") or row["route"] == "<dynamic>"]
    explicit = sum(bool(row["explicit_source"]) for row in first_party)
    report = {
        "files_scanned": len(list(JS_ROOT.glob("*.js"))),
        "call_sites": len(first_party),
        "explicit_source": explicit,
        "route_fallback_only": len(first_party) - explicit,
        "dynamic_route": sum(row["route"] == "<dynamic>" for row in first_party),
        "rows": first_party,
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
