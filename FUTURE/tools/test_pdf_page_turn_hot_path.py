from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = (ROOT / "FUTURE/web/js_parts/20_pdf_page_progress.js").read_text(encoding="utf-8")
PDF = (ROOT / "FUTURE/web/js_parts/19_pdf_speak_chrome.js").read_text(encoding="utf-8")
GET = (ROOT / "FUTURE/server_parts/http_server/get_route_parts/05_progress_vocab_leaderboard.pyfrag").read_text(encoding="utf-8")


assert 'source: "pdf_page_turn"' in PAGE
assert 'uiAction: "pdf.page_turn"' in PAGE
assert "skipLastFilePost: true" in PAGE
assert "savePdfProgressLocalNow({ skipLastFilePost: true })" in PAGE
assert "recordPdfPageVisit(targetPage, { deferSave: true })" in PAGE
assert "options.deferSave !== true" in PDF
assert "window.clearTimeout(pdfProgressSaveTimer)" in PAGE
assert "pdfPageNavigationSerial += 1" in PAGE
assert "initialPdfLoadPending" in PAGE
assert 'source: "pdf_open_restore"' in PAGE
assert 'source: "picture_open_restore"' in PAGE
assert "pdfProgressLastSentSemanticSignature" in PDF
assert "pdfProgressNetworkSemanticSignature" in PDF
assert "options.skipLastFilePost !== true" in PDF

for route in ("/space-pdf/audio-markers", "/space-pdf/ai-region-notices", "/space-pdf/ai-region-questions"):
    block = GET.split(f'if path == "{route}":', 1)[1].split("        return", 1)[0]
    assert "chat_mark_online" not in block
    assert "mark_user_activity" not in block

print("pdf page-turn hot path: PASS")
