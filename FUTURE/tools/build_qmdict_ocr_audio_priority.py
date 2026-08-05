import json
import os
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAME_ROOT = ROOT.parent
SERVER_DATA_ROOT = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT") or r"C:\server data")
OUTPUT = SERVER_DATA_ROOT / "_future_qmdict_ocr_audio_priority.json"


# Added 2026-07-31: build the OCR-first English list once; audio refresh only reads the saved file.
def main() -> None:
    if str(PROGRAME_ROOT) not in sys.path:
        sys.path.insert(0, str(PROGRAME_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from module_main.QM_GATE import viewer_vocab_runtime as runtime
    from future_postgres_structure_asset_store import ocr_cache_text_snapshot

    revision_ns, texts = ocr_cache_text_snapshot()
    qmdict = runtime.get_qmdict()
    if not isinstance(qmdict, dict) or not qmdict:
        raise RuntimeError("QmDict is empty.")

    token_seen = set()
    tokens = []
    for text in texts:
        for token in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", str(text or "")):
            normalized = str(token or "").strip().lower().replace("`", "'").replace("´", "'")
            normalized = re.sub(r"\b([a-z]+)'s\b", r"\1", normalized)
            if normalized and normalized not in token_seen:
                token_seen.add(normalized)
                tokens.append(normalized)

    line_to_word = {}
    for raw_word, raw_line in qmdict.items():
        word = str(raw_word or "").strip()
        if word:
            line_to_word.setdefault(str(raw_line), word)

    started = time.time()
    words = []
    seen = set()
    for index, token in enumerate(tokens, 1):
        valid_lines = []
        runtime.is_valid_word(token, qmdict, valid_lines, number="1")
        for line in valid_lines:
            word = line_to_word.get(str(line), "")
            if word and word not in seen:
                seen.add(word)
                words.append(word)
        if index % 1000 == 0 or index == len(tokens):
            print(f"tokens={index}/{len(tokens)} words={len(words)}", flush=True)

    payload = {
        "version": 1,
        "source": "postgresql_ocr_cache",
        "ocr_revision_ns": int(revision_ns or 0),
        "pages": len(texts),
        "tokens": len(tokens),
        "words": words,
        "build_seconds": round(time.time() - started, 3),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_name(f"{OUTPUT.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, OUTPUT)
    print(f"saved={OUTPUT} words={len(words)}", flush=True)


if __name__ == "__main__":
    main()
