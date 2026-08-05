from __future__ import annotations

import json
import os
import secrets
import shutil
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = 8766
APP_TOKEN = secrets.token_urlsafe(18)
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


HTML = r"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fast Permanent Delete Folders</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #f5f7fb;
      color: #162033;
      font: 14px "Segoe UI", Arial, sans-serif;
    }
    .app {
      max-width: 1180px;
      margin: 0 auto;
      padding: 18px;
    }
    .panel {
      background: #fff;
      border: 1px solid #d7deea;
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(15, 30, 60, 0.10);
      padding: 14px;
      margin-bottom: 14px;
    }
    h1 { margin: 0 0 6px; font-size: 22px; }
    h2 { margin: 0 0 10px; font-size: 16px; }
    .danger { color: #991b1b; font-weight: 700; }
    .muted { color: #64748b; line-height: 1.45; }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button, input, textarea {
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 9px 11px;
      font: inherit;
    }
    button { background: #fff; cursor: pointer; min-height: 38px; }
    button:hover { filter: brightness(0.97); }
    button.primary { background: #0f75bc; border-color: #0f75bc; color: #fff; font-weight: 700; }
    button.danger-button { background: #b91c1c; border-color: #b91c1c; color: #fff; font-weight: 800; }
    button.warning { background: #f59f00; border-color: #f59f00; color: #111827; font-weight: 700; }
    input { min-width: 220px; }
    textarea {
      width: 100%;
      min-height: 90px;
      resize: vertical;
      font-family: Consolas, monospace;
    }
    .folder-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 8px;
    }
    .folder-card {
      display: grid;
      gap: 8px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px;
      background: #f8fafc;
      min-width: 0;
    }
    .folder-card .path {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: Consolas, monospace;
    }
    .folder-card.invalid { border-color: #fca5a5; background: #fff1f2; }
    .folder-card.deleted { border-color: #86efac; background: #f0fdf4; opacity: 0.8; }
    progress { width: 100%; height: 20px; }
    .log {
      height: 230px;
      overflow: auto;
      background: #0b1020;
      color: #e5edf8;
      border-radius: 8px;
      padding: 12px;
      font-family: Consolas, monospace;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="panel">
      <h1>Fast Permanent Delete Folders</h1>
      <p class="muted"><span class="danger">Xóa vĩnh viễn, không qua Recycle Bin.</span> Chỉ chạy local tại 127.0.0.1. Kiểm tra kỹ danh sách trước khi nhập DELETE.</p>
    </div>

    <div class="panel">
      <h2>Chọn Folder</h2>
      <div class="row">
        <button id="chooseFolder" class="primary">Add Folder</button>
        <button id="validateButton">Validate</button>
        <button id="clearButton">Clear</button>
      </div>
      <p class="muted">Có thể bấm Add Folder nhiều lần. Hoặc paste mỗi dòng một path vào ô dưới rồi bấm Add Pasted Paths.</p>
      <textarea id="pasteBox" placeholder="D:\folder can xoa&#10;C:\temp\old-folder"></textarea>
      <div class="row" style="margin-top:8px">
        <button id="addPastedButton">Add Pasted Paths</button>
      </div>
    </div>

    <div class="panel">
      <div class="row">
        <h2 style="margin-right:auto">Danh Sách Xóa</h2>
        <span id="countStatus" class="muted"></span>
      </div>
      <div id="folderList" class="folder-grid"></div>
    </div>

    <div class="panel">
      <h2>Xác Nhận</h2>
      <div class="row">
        <input id="confirmInput" placeholder="Nhập DELETE">
        <button id="deleteButton" class="danger-button">PERMANENT DELETE</button>
        <button id="cancelButton" class="warning" disabled>Cancel</button>
      </div>
      <p id="status" class="muted">Chưa có job.</p>
      <progress id="progress" value="0" max="1"></progress>
    </div>

    <div class="panel">
      <h2>Log</h2>
      <div id="log" class="log"></div>
    </div>
  </div>

  <script>
    const TOKEN = "__TOKEN__";
    const STORAGE_KEY = "fastPermanentDeleteFoldersWeb.v1";
    const state = { paths: [], validations: {}, jobId: "" };
    const els = {
      chooseFolder: document.getElementById("chooseFolder"),
      validateButton: document.getElementById("validateButton"),
      clearButton: document.getElementById("clearButton"),
      pasteBox: document.getElementById("pasteBox"),
      addPastedButton: document.getElementById("addPastedButton"),
      folderList: document.getElementById("folderList"),
      countStatus: document.getElementById("countStatus"),
      confirmInput: document.getElementById("confirmInput"),
      deleteButton: document.getElementById("deleteButton"),
      cancelButton: document.getElementById("cancelButton"),
      status: document.getElementById("status"),
      progress: document.getElementById("progress"),
      log: document.getElementById("log"),
    };

    function saveState() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ paths: state.paths }));
    }

    function loadState() {
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        state.paths = Array.isArray(saved.paths) ? saved.paths : [];
      } catch {
        state.paths = [];
      }
    }

    async function api(path, payload = {}) {
      const response = await fetch(path + "?token=" + encodeURIComponent(TOKEN), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) throw new Error(data.error || "Request failed");
      return data;
    }

    function addPath(path) {
      const clean = String(path || "").trim();
      if (!clean) return;
      if (!state.paths.includes(clean)) state.paths.push(clean);
      saveState();
      render();
    }

    function removePath(path) {
      state.paths = state.paths.filter((item) => item !== path);
      delete state.validations[path];
      saveState();
      render();
    }

    function render() {
      els.folderList.innerHTML = "";
      els.countStatus.textContent = `${state.paths.length} folder`;
      if (!state.paths.length) {
        els.folderList.innerHTML = "<p class='muted'>Chưa chọn folder.</p>";
        return;
      }
      for (const path of state.paths) {
        const validation = state.validations[path];
        const card = document.createElement("div");
        card.className = "folder-card" + (validation && !validation.ok ? " invalid" : "");
        const pathLine = document.createElement("div");
        pathLine.className = "path";
        pathLine.title = path;
        pathLine.textContent = path;
        const meta = document.createElement("div");
        meta.className = "muted";
        meta.textContent = validation ? (validation.ok ? "Hợp lệ" : validation.error) : "Chưa validate";
        const row = document.createElement("div");
        row.className = "row";
        const remove = document.createElement("button");
        remove.textContent = "Remove";
        remove.addEventListener("click", () => removePath(path));
        row.appendChild(remove);
        card.append(pathLine, meta, row);
        els.folderList.appendChild(card);
      }
    }

    async function validatePaths() {
      const data = await api("/validate", { paths: state.paths });
      state.validations = data.results || {};
      render();
      return data;
    }

    async function pollJob() {
      if (!state.jobId) return;
      const data = await api("/job", { job_id: state.jobId });
      els.progress.max = Math.max(1, data.total || 1);
      els.progress.value = data.done || 0;
      els.status.textContent = `${data.status} | ${data.done || 0}/${data.total || 0} | deleted ${data.deleted || 0}, failed ${data.failed || 0}`;
      els.log.textContent = (data.log || []).join("\n");
      els.log.scrollTop = els.log.scrollHeight;
      if (data.status === "running" || data.status === "cancel_requested") {
        setTimeout(pollJob, 500);
      } else {
        els.deleteButton.disabled = false;
        els.cancelButton.disabled = true;
        state.paths = state.paths.filter((path) => !(data.deleted_paths || []).includes(path));
        saveState();
        render();
      }
    }

    els.chooseFolder.addEventListener("click", async () => {
      try {
        const data = await api("/choose-folder", {});
        if (data.path) addPath(data.path);
      } catch (err) {
        els.status.textContent = err.message;
      }
    });

    els.addPastedButton.addEventListener("click", () => {
      for (const line of els.pasteBox.value.split(/\r?\n/)) addPath(line);
      els.pasteBox.value = "";
    });

    els.validateButton.addEventListener("click", () => validatePaths().catch((err) => els.status.textContent = err.message));
    els.clearButton.addEventListener("click", () => {
      state.paths = [];
      state.validations = {};
      saveState();
      render();
    });

    els.deleteButton.addEventListener("click", async () => {
      if (els.confirmInput.value.trim() !== "DELETE") {
        els.status.textContent = "Bạn phải nhập DELETE để xác nhận.";
        return;
      }
      if (!state.paths.length) {
        els.status.textContent = "Chưa có folder để xóa.";
        return;
      }
      if (!confirm(`Xóa vĩnh viễn ${state.paths.length} folder, không qua Recycle Bin?`)) return;
      try {
        await validatePaths();
        const data = await api("/start-delete", { paths: state.paths, confirm: "DELETE" });
        state.jobId = data.job_id;
        els.deleteButton.disabled = true;
        els.cancelButton.disabled = false;
        els.confirmInput.value = "";
        pollJob();
      } catch (err) {
        els.status.textContent = err.message;
      }
    });

    els.cancelButton.addEventListener("click", async () => {
      if (!state.jobId) return;
      await api("/cancel", { job_id: state.jobId });
      els.status.textContent = "Đã yêu cầu dừng sau folder hiện tại.";
    });

    loadState();
    render();
  </script>
</body>
</html>
"""


# Added 2026-07-08: blocks dangerous permanent delete targets before any deletion starts.
def validate_delete_target(path: Path) -> tuple[bool, str]:
    try:
        resolved = path.resolve()
    except OSError as exc:
        return False, f"Không đọc được path: {exc}"
    if not resolved.exists():
        return False, "Folder không tồn tại."
    if not resolved.is_dir():
        return False, "Path này không phải folder."
    if resolved.parent == resolved:
        return False, "Không cho xóa root filesystem."
    if resolved == Path(resolved.anchor):
        return False, "Không cho xóa root ổ đĩa."
    system_names = {"windows", "program files", "program files (x86)", "programdata"}
    if resolved.name.lower() in system_names or (len(resolved.parts) <= 3 and any(part.lower() in system_names for part in resolved.parts)):
        return False, "Folder hệ thống quá nguy hiểm để xóa bằng tool này."
    return True, ""


# Added 2026-07-08: clears readonly attributes so shutil.rmtree can remove stubborn Windows files.
def on_remove_error(func, path, _exc_info) -> None:
    os.chmod(path, 0o700)
    func(path)


# Added 2026-07-08: deletes a folder tree permanently without using Recycle Bin.
def permanent_delete_folder(path: Path) -> None:
    shutil.rmtree(path, onerror=on_remove_error)


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


# Added 2026-07-08: runs deletion as a background job for progress polling.
def run_delete_job(job_id: str, paths: list[str]) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        job["total"] = len(paths)
    for index, raw_path in enumerate(paths, start=1):
        with JOBS_LOCK:
            if JOBS[job_id].get("cancel"):
                JOBS[job_id]["status"] = "cancel_requested"
                JOBS[job_id]["log"].append("Đã dừng trước folder tiếp theo.")
                break
            JOBS[job_id]["current"] = raw_path
        start = time.perf_counter()
        try:
            permanent_delete_folder(Path(raw_path))
            elapsed = time.perf_counter() - start
            with JOBS_LOCK:
                JOBS[job_id]["deleted"] += 1
                JOBS[job_id]["deleted_paths"].append(raw_path)
                JOBS[job_id]["log"].append(f"OK  | {elapsed:.2f}s | {raw_path}")
        except Exception as exc:
            with JOBS_LOCK:
                JOBS[job_id]["failed"] += 1
                JOBS[job_id]["log"].append(f"ERR | {raw_path} | {exc}")
        with JOBS_LOCK:
            JOBS[job_id]["done"] = index
    with JOBS_LOCK:
        if JOBS[job_id]["status"] == "running":
            JOBS[job_id]["status"] = "done"


class DeleteWebHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        return

    def authorized(self) -> bool:
        query = parse_qs(urlparse(self.path).query)
        return (query.get("token") or [""])[0] == APP_TOKEN

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/":
            self.send_error(404)
            return
        raw = HTML.replace("__TOKEN__", APP_TOKEN).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if not self.authorized():
            json_response(self, 403, {"ok": False, "error": "Unauthorized"})
            return
        path = urlparse(self.path).path
        try:
            payload = read_json(self)
            if path == "/choose-folder":
                self.handle_choose_folder()
            elif path == "/validate":
                self.handle_validate(payload)
            elif path == "/start-delete":
                self.handle_start_delete(payload)
            elif path == "/job":
                self.handle_job(payload)
            elif path == "/cancel":
                self.handle_cancel(payload)
            else:
                json_response(self, 404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            json_response(self, 500, {"ok": False, "error": str(exc)})

    def handle_choose_folder(self) -> None:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Chọn folder cần xóa vĩnh viễn")
        root.destroy()
        json_response(self, 200, {"ok": True, "path": folder or ""})

    def handle_validate(self, payload: dict) -> None:
        paths = [str(path).strip() for path in payload.get("paths") or [] if str(path).strip()]
        results = {}
        for raw_path in paths:
            ok, message = validate_delete_target(Path(raw_path))
            results[raw_path] = {"ok": ok, "error": message}
        json_response(self, 200, {"ok": True, "results": results})

    def handle_start_delete(self, payload: dict) -> None:
        if payload.get("confirm") != "DELETE":
            json_response(self, 400, {"ok": False, "error": "Missing DELETE confirmation"})
            return
        paths = [str(path).strip() for path in payload.get("paths") or [] if str(path).strip()]
        if not paths:
            json_response(self, 400, {"ok": False, "error": "No folders selected"})
            return
        for raw_path in paths:
            ok, message = validate_delete_target(Path(raw_path))
            if not ok:
                json_response(self, 400, {"ok": False, "error": f"{raw_path}: {message}"})
                return
        job_id = secrets.token_urlsafe(10)
        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "queued",
                "total": len(paths),
                "done": 0,
                "deleted": 0,
                "failed": 0,
                "current": "",
                "log": [],
                "cancel": False,
                "deleted_paths": [],
            }
        threading.Thread(target=run_delete_job, args=(job_id, paths), daemon=True).start()
        json_response(self, 200, {"ok": True, "job_id": job_id})

    def handle_job(self, payload: dict) -> None:
        job_id = str(payload.get("job_id") or "")
        with JOBS_LOCK:
            job = dict(JOBS.get(job_id) or {})
            if "log" in job:
                job["log"] = list(job["log"])[-300:]
            if "deleted_paths" in job:
                job["deleted_paths"] = list(job["deleted_paths"])
        if not job:
            json_response(self, 404, {"ok": False, "error": "Job not found"})
            return
        job["ok"] = True
        json_response(self, 200, job)

    def handle_cancel(self, payload: dict) -> None:
        job_id = str(payload.get("job_id") or "")
        with JOBS_LOCK:
            if job_id not in JOBS:
                json_response(self, 404, {"ok": False, "error": "Job not found"})
                return
            JOBS[job_id]["cancel"] = True
            JOBS[job_id]["status"] = "cancel_requested"
        json_response(self, 200, {"ok": True})


# Added 2026-07-08: starts the local-only web deletion utility.
def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), DeleteWebHandler)
    url = f"http://{HOST}:{PORT}/?token={APP_TOKEN}"
    print(f"Fast Permanent Delete Folders Web: {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
