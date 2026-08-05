"""Local HTML editor for Space_Q, backed by the canonical builder worker.

Added 2026-08-01: expose the existing Space_Q serializer through a browser UI
without duplicating its normalization/audio/manifest logic.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import future_question_builder_gui as core

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "future_question_builder_web"
PREVIEWS: dict[str, str] = {}


def _materialize_data_url(value: str, folder: Path, stem: str) -> Path | None:
    if not value.startswith("data:") or "," not in value:
        return None
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0]
    suffix = mimetypes.guess_extension(mime) or ".bin"
    path = folder / f"{stem}{suffix}"
    path.write_bytes(base64.b64decode(encoded))
    return path


def _preview_document(space_q_text: str, payload: dict | None = None) -> str:
    source = ROOT / "future.html"
    if source.is_file():
        html = source.read_text(encoding="utf-8-sig", errors="replace")
        injection = (
            '<script id="ft-preview-code">window.__FTG_PREVIEW_CODE__='
            + json.dumps(space_q_text, ensure_ascii=False)
            + ';window.__FTG_PREVIEW_MODE__=true;</script>\n'
        )
        return html.replace("<script>", injection + "<script>", 1)
    preview_payload = json.dumps(payload or {}, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Space_Q structural preview</title><style>
    :root{{--bg:#071315;--card:#10272b;--line:#31666b;--mint:#52efd1;--ink:#effffb;--muted:#8ab5b3;--orange:#ffb36b}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 10% 0,#184144,transparent 34%),linear-gradient(145deg,#071315,#15162a);color:var(--ink);font:15px/1.45 'Trebuchet MS',sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}h1{{font:800 clamp(30px,5vw,58px)/1 Georgia,serif;margin:8px 0}}.note{{color:var(--muted);margin-bottom:22px}}.node{{border:1px solid var(--line);border-radius:20px;padding:18px;margin:16px 0;background:#091d20cc}}.root{{font:800 22px Georgia,serif;color:var(--mint);padding:16px;border-radius:14px;background:var(--card)}}.question{{margin:12px 0;padding:14px;border:1px solid #28585d;border-radius:14px;background:#0c2226}}.question b{{color:var(--orange)}}.chips{{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}}.chip{{padding:5px 8px;border:1px solid #397378;border-radius:999px;color:var(--muted);font-size:12px}}.answer{{color:#8df2b5}}img{{max-width:100%;max-height:420px;border-radius:14px;margin-top:12px}}</style></head><body><main><div style="letter-spacing:.2em;color:var(--mint);font-weight:900">SPACE_Q PREVIEW</div><h1 id="title"></h1><div class="note">Bản xem trước cấu trúc cục bộ. File build vẫn dùng serializer/audio/runtime Space_Q chính thức.</div><div id="nodes"></div></main><script>const p={preview_payload};const e=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));document.querySelector('#title').textContent=p.title||'Future Question';document.querySelector('#nodes').innerHTML=(p.nodes||[]).map((n,ni)=>{{const c=n.cards||{{}},qs=c.questions||[];return `<section class="node"><div class="root">${{e(c.root?.text||'Root')}}</div>${{c.picture?.url?`<img src="${{e(c.picture.url)}}" alt="${{e(c.picture.caption||'Picture')}}">`:''}}${{qs.map((q,qi)=>`<article class="question"><b>${{qi+1}}. ${{e(q.question)}}</b><div class="answer">Answer: ${{e(q.answer)}}</div><div>${{e((q.wrong||q.answers||q.tokens||[]).join(' · '))}}</div><div class="chips"><span class="chip">${{e(q.type)}}</span><span class="chip">${{e(q.card_mode||'question')}}</span><span class="chip">${{(q.root_highlights||[]).length}} highlights</span><span class="chip">${{(q.root_notice?.turns||[]).length}} notice turns</span><span class="chip">${{(q.guidance_tree?.items||[]).length}} guide roots</span></div></article>`).join('')}}</section>`}}).join('');</script></body></html>'''


def _run_build(document: dict, direct_payload: bool = False) -> dict:
    title = core.clean_text(document.get("title")) or "Future Question"
    order = "shuffle" if core.clean_text(document.get("order")).lower() == "shuffle" else "sequence"
    nodes = json.loads(json.dumps(document.get("nodes"))) if isinstance(document.get("nodes"), list) else []
    rewards = core.normalize_reward_config(document.get("rewards"))
    with tempfile.TemporaryDirectory(prefix="spaceq_web_") as tmp:
        # Browser file inputs produce data URLs; materialize them so the canonical
        # worker copies assets exactly like the former QFileDialog workflow.
        for node_index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            picture_url = str(node.get("picture_asset_url") or "")
            picture_path = _materialize_data_url(picture_url, Path(tmp), f"node-{node_index + 1}")
            if picture_path:
                node["picture_path"] = str(picture_path)
                node["picture_asset_url"] = ""
            for question_index, question in enumerate(node.get("questions") or []):
                if not isinstance(question, dict):
                    continue
                notice = question.get("root_notice") if isinstance(question.get("root_notice"), dict) else {}
                for turn_index, turn in enumerate(notice.get("turns") or []):
                    if not isinstance(turn, dict):
                        continue
                    avatar = turn.get("avatar") if isinstance(turn.get("avatar"), dict) else {}
                    avatar_path = _materialize_data_url(str(avatar.get("url") or ""), Path(tmp), f"notice-{node_index + 1}-{question_index + 1}-{turn_index + 1}")
                    if avatar_path:
                        turn["avatar_path"] = str(avatar_path)
                        turn.pop("avatar", None)
        output = Path(tmp) / (core.safe_unicode_filename_stem(title) + core.QUESTION_EXTENSION)
        worker = core.BuildQuestionWorker(nodes, title, order, output, direct_payload=direct_payload, reward_config=rewards)
        logs: list[str] = []
        errors: list[str] = []
        worker.log_message.connect(logs.append)
        worker.failed.connect(errors.append)
        worker.run()
        if errors or not output.is_file():
            raise RuntimeError("; ".join(errors) or "Không tạo được file Space_Q")
        raw = output.read_text(encoding="utf-8-sig")
        preview = _preview_document(raw, worker.last_payload)
        return {"filename": output.name, "space_q": base64.b64encode(raw.encode("utf-8")).decode(), "preview_html": base64.b64encode(preview.encode("utf-8")).decode(), "logs": logs, "payload": worker.last_payload}


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/bootstrap":
            _json_response(self, {"title": core.APP_TITLE, "voices": core.question_voice_specs(), "ship_types": core.SHIP_TYPES, "connector_styles": core.CONNECTOR_STYLES, "question_types": [["Multiple choice", "choice"], ["Typed answer", "input"], ["Select words/regions", "select"], ["Guidance / presentation", "guide"]], "question_audio_modes": core.QUESTION_AUDIO_MODES, "question_info_modes": core.QUESTION_INFO_MODES, "highlight_styles": core.HIGHLIGHT_STYLES, "highlight_render_modes": core.HIGHLIGHT_RENDER_MODES, "picture_question_anchors": core.PICTURE_QUESTION_ANCHORS, "picture_question_placements": core.PICTURE_QUESTION_PLACEMENTS})
            return
        if path == "/api/preview":
            preview_id = urlparse(self.path).query.removeprefix("id=")
            raw = PREVIEWS.get(preview_id, "").encode("utf-8")
            if not raw:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path.startswith("/preview-assets/"):
            file_path = ROOT / "FUTURE" / "web" / Path(path).name
            if not file_path.is_file():
                self.send_error(404)
                return
            raw = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        rel = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in file_path.parents or not file_path.is_file():
            self.send_error(404)
            return
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            if urlparse(self.path).path == "/api/load":
                content = data.get("content", "")
                with tempfile.NamedTemporaryFile("w", suffix=core.QUESTION_EXTENSION, encoding="utf-8", delete=False) as fh:
                    fh.write(content)
                    temp_name = fh.name
                try:
                    payload = core.decode_space_q_payload(Path(temp_name))
                    _json_response(self, {"payload": payload, "nodes": core.nodes_from_space_q_payload(payload)})
                finally:
                    Path(temp_name).unlink(missing_ok=True)
                return
            if urlparse(self.path).path == "/api/build":
                result = _run_build(data, bool(data.get("direct_payload")))
                if result.get("preview_html"):
                    preview_id = uuid.uuid4().hex
                    PREVIEWS[preview_id] = base64.b64decode(result["preview_html"]).decode("utf-8")
                    result["preview_url"] = f"/api/preview?id={preview_id}"
                    if len(PREVIEWS) > 8:
                        PREVIEWS.pop(next(iter(PREVIEWS)))
                _json_response(self, result)
                return
            self.send_error(404)
        except Exception as exc:
            _json_response(self, {"error": str(exc)}, 400)


def launch_web_builder(port: int = 0) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"{core.APP_TITLE} web: {url}")
    threading.Timer(0.15, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    launch_web_builder()
