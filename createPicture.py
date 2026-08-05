"""Local web GUI for collecting vocabulary pictures without recompression."""

from __future__ import annotations

import argparse
import base64
import gzip
import importlib
import json
import mimetypes
import os
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path(r"C:\server data\Picture\picture")
DEFAULT_COMMON = Path(r"C:\server data\common")
DEFAULT_QMDICT_ROOT = Path(r"C:\programe")
HTML_FILE = ROOT / "createPicture.html"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".jfif"}


def clean_word(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def word_key(value: object) -> str:
    # Match Server 2 vocab_key semantics so picture stems are neither merged nor skipped incorrectly.
    return re.sub(r"\s+", " ", clean_word(value).lower()).strip()


def filename_for_word(value: object) -> str:
    # Keep stems compatible with Server 2's vocab_key lookup while removing Windows-invalid characters.
    text = clean_word(value).casefold()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "untitled"


def existing_image_words(folder: Path) -> set[str]:
    if not folder.is_dir():
        return set()
    return {word_key(path.stem) for path in folder.iterdir() if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS}


def load_qmdict_words() -> list[str]:
    """Added 2026-07-30: load QmDict keys without changing server/runtime state."""
    try:
        import sys
        if str(DEFAULT_QMDICT_ROOT) not in sys.path:
            sys.path.insert(0, str(DEFAULT_QMDICT_ROOT))
        module = importlib.import_module("module_main.Data_Input.QmDict")
        values = getattr(module, "QMDICT", {})
    except Exception:
        return []
    if not isinstance(values, dict):
        return []
    result = []
    for raw in values:
        word = clean_word(raw)
        if word and re.search(r"[A-Za-z]", word):
            result.append(word)
    return result


def decode_space_v(path: Path) -> dict | None:
    try:
        encoded = path.read_text(encoding="utf-8-sig").strip()
        if not encoded.startswith("FTG1."):
            return None
        payload = encoded[5:]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(gzip.decompress(base64.urlsafe_b64decode(payload)).decode("utf-8-sig"))
    except Exception:
        return None


def load_space_v_words(common: Path) -> list[str]:
    words: list[str] = []
    if not common.is_dir():
        return words
    for path in common.rglob("*.Space_V"):
        payload = decode_space_v(path)
        rows = payload.get("w", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            continue
        for row in rows:
            value = row.get("w") if isinstance(row, dict) else row
            word = clean_word(value)
            if word and re.search(r"[A-Za-z]", word):
                words.append(word)
    return words


class PictureCatalog:
    def __init__(self, output: Path, common: Path = DEFAULT_COMMON):
        self.output = output
        self.common = common
        self.lock = threading.RLock()
        self.qmdict_words = load_qmdict_words()
        self.space_v_words = load_space_v_words(common)
        self.current = ""
        self.refresh()

    def refresh(self) -> None:
        with self.lock:
            existing = existing_image_words(self.output)
            seen: set[str] = set()
            ordered: list[tuple[str, str]] = []
            # Space_V words are the useful work queue; QmDict fills the remaining vocabulary afterward.
            for source, values in (("space_v_priority", self.space_v_words), ("qmdict", self.qmdict_words)):
                for value in values:
                    key = word_key(value)
                    if key in seen or key in existing:
                        continue
                    seen.add(key)
                    ordered.append((clean_word(value), source))
            self.candidates = ordered
            if self.current and word_key(self.current) not in {word_key(v) for v, _ in ordered}:
                self.current = ""
            if not self.current and ordered:
                self.current = ordered[0][0]

    def state(self) -> dict:
        with self.lock:
            current_index = next((i for i, (word, _) in enumerate(self.candidates) if word_key(word) == word_key(self.current)), -1)
            source = self.candidates[current_index][1] if current_index >= 0 else "manual"
            return {"word": self.current, "source": source, "index": current_index + 1, "total": len(self.candidates), "output": str(self.output), "exists": self.output.is_dir()}

    def set_word(self, value: object) -> dict:
        with self.lock:
            self.current = clean_word(value)
        return self.state()

    def save(self, word: str, content: bytes, filename: str = "") -> dict:
        with self.lock:
            word = clean_word(word)
            if not word:
                raise ValueError("Vui long nhap tu vung.")
            if not content:
                raise ValueError("Chua co anh trong khu vuc dan anh.")
            suffix = Path(filename).suffix.casefold() or mimetypes.guess_extension(filename.split(";", 1)[0]) or ".png"
            if suffix not in IMAGE_EXTENSIONS:
                suffix = ".png"
            self.output.mkdir(parents=True, exist_ok=True)
            target = self.output / f"{filename_for_word(word)}{suffix}"
            with target.open("xb") as handle:
                handle.write(content)
            self.current = ""
            self.refresh()
            return {"saved": target.name, **self.state()}

    def save_or_advance(self, word: str, content: bytes, filename: str = "") -> dict:
        """Added 2026-07-30: detect files downloaded outside the paste area before advancing."""
        with self.lock:
            word = clean_word(word)
            if not word:
                raise ValueError("Vui long nhap tu vung.")
            self.output.mkdir(parents=True, exist_ok=True)
            existing = existing_image_words(self.output)
            # Recheck the folder before honoring a stale pasted preview; external downloads win.
            if word_key(word) in existing:
                self.current = ""
                self.refresh()
                return {"detected_existing": True, **self.state()}
            if content:
                return self.save(word, content, filename)
            # No pasted image: advance for this pass, but keep the word eligible on a later refresh.
            self.refresh()
            current_key = word_key(word)
            next_word = ""
            for index, (candidate, _source) in enumerate(self.candidates):
                if word_key(candidate) == current_key:
                    if index + 1 < len(self.candidates):
                        next_word = self.candidates[index + 1][0]
                    break
            else:
                if self.candidates:
                    next_word = self.candidates[0][0]
            self.current = next_word
            return {"skipped": True, **self.state()}


class Handler(BaseHTTPRequestHandler):
    catalog: PictureCatalog

    def log_message(self, *_args):
        return

    def send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            self.catalog.refresh()
            self.send_json(self.catalog.state())
            return
        if parsed.path in {"/", "/index.html"}:
            raw = HTML_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            if parsed.path == "/api/save":
                word = urllib.parse.unquote(self.headers.get("X-Word", ""))
                result = self.catalog.save_or_advance(word, body, self.headers.get("X-Filename", ""))
                self.send_json(result)
                return
            if parsed.path == "/api/word":
                data = json.loads(body.decode("utf-8"))
                self.send_json(self.catalog.set_word(data.get("word", "")))
                return
            if parsed.path == "/api/output":
                data = json.loads(body.decode("utf-8"))
                value = clean_word(data.get("output", ""))
                if not value:
                    raise ValueError("Thu muc output khong duoc rong.")
                with self.catalog.lock:
                    self.catalog.output = Path(value)
                    self.catalog.refresh()
                self.send_json(self.catalog.state())
                return
            if parsed.path == "/api/refresh":
                self.catalog.refresh()
                self.send_json(self.catalog.state())
                return
            self.send_error(404)
        except FileExistsError as exc:
            self.send_json({"error": str(exc)}, 409)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="createPicture local web GUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--common", type=Path, default=DEFAULT_COMMON)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    catalog = PictureCatalog(args.output, args.common)
    Handler.catalog = catalog
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"createPicture: http://{args.host}:{args.port}")
    print(f"output: {catalog.output}")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(f"http://{args.host}:{args.port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
