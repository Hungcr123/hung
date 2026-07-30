"""Regression that Server 2 warm-ready waits for the QmDict dependency map."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
MAIN = ROOT / "FUTURE" / "server_parts" / "http_server" / "06_main.py"
QMDICT = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "06_ocr_qmdict_core.py"


# Added 2026-07-21: first learners must not race an untracked nested QmDict warm thread.
def main() -> int:
    startup = MAIN.read_text(encoding="utf-8")
    qmdict = QMDICT.read_text(encoding="utf-8")
    background_start = startup.index("def _background_startup_tasks")
    background_end = startup.index("threading.Thread(target=_background_startup_tasks", background_start)
    background = startup[background_start:background_end]
    if "warm_qmdict_runtime(0.2)" not in background or "warm_qmdict_runtime_async(0.2)" in background:
        raise RuntimeError("Server warm-ready still races asynchronous QmDict warm")
    qmdict_section = background[background.index('SERVER_STATE["warm_status"] = "Warming QmDict cache..."'):]
    if "wait_for_request_quiet" in qmdict_section:
        raise RuntimeError("QmDict warm still waits for a second request-quiet window")
    if 'SERVER_STATE["qmdict_runtime_priority_wait_ms"] = 0' not in qmdict_section:
        raise RuntimeError("QmDict quiet-wait evidence is missing")
    if "def warm_qmdict_runtime(" not in qmdict or '"qmdict_runtime_ready": True' not in qmdict:
        raise RuntimeError("QmDict warm does not expose completion state")
    print("qmdict_startup_warm_gate=ok warm_ready_after_qmdict=true nested_thread=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
