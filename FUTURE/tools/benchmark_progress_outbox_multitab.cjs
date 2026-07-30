"use strict";

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const start = source.indexOf('const PROGRESS_OUTBOX_STORAGE_KEY = "future_progress_outbox:v1";');
const eventStart = source.indexOf('window.addEventListener("online", () => {', start);
const eventEnd = source.indexOf("      });", eventStart) + "      });".length;
if (start < 0 || eventStart < 0 || eventEnd <= eventStart) throw new Error("Progress outbox source not found");
const block = source.slice(start, eventEnd);

class SharedStorage {
  constructor() {
    this.map = new Map();
    this.beforeSet = null;
  }
  get length() { return this.map.size; }
  key(index) { return Array.from(this.map.keys())[index] ?? null; }
  getItem(key) { return this.map.has(String(key)) ? this.map.get(String(key)) : null; }
  setItem(key, value) {
    if (this.beforeSet) {
      this.beforeSet(String(key), String(value));
    }
    this.map.set(String(key), String(value));
  }
  removeItem(key) { this.map.delete(String(key)); }
}

function runtime(storage, fetchAuthJson) {
  const context = {
    console,
    Date,
    Math,
    JSON,
    localStorage: storage,
    currentAuthUsername: "hung",
    authToken: "token",
    authUser: { value: "hung" },
    SPACE_W_PROGRESS_PREFIX: "future_space_w_progress",
    SPACE_Q_PROGRESS_PREFIX: "future_space_q_progress",
    SPACE_P_PROGRESS_PREFIX: "future_space_p_progress",
    SPACE_V_PROGRESS_PREFIX: "future_space_v_progress",
    clean: (value) => String(value ?? "").trim(),
    normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
    readSpaceWJson: (key) => { try { return JSON.parse(storage.getItem(key) || "null"); } catch { return null; } },
    writeSpaceWJson: (key, value) => { storage.setItem(key, JSON.stringify(value)); return true; },
    fetchAuthJson,
    pdfProgressLocalSharedKey: (filePath) => `future_space_pdf_progress:local:${filePath}`,
    window: { localStorage: storage, addEventListener: () => {}, setTimeout: () => 1, clearTimeout: () => {} },
  };
  vm.createContext(context);
  vm.runInContext(`${block}\n;globalThis.api={readProgressOutbox,enqueueProgressOutboxRequest,drainProgressOutbox};`, context);
  return context.api;
}

const record = (identity, pathValue) => ({
  identity,
  path: pathValue,
  savedAt: "2026-07-21T00:00:00Z",
  pendingServerSync: true,
  state: { savedAt: "2026-07-21T00:00:00Z", path: pathValue },
});

(async () => {
  const storage = new SharedStorage();
  const keyA = "future_space_v_progress:hung:a";
  const keyB = "future_space_v_progress:hung:b";
  storage.setItem(keyA, JSON.stringify(record("a", "common/a.Space_V")));
  storage.setItem(keyB, JSON.stringify(record("b", "common/b.Space_V")));
  const tabA = runtime(storage, async () => ({ payload: { ok: true } }));
  const tabB = runtime(storage, async () => ({ payload: { ok: true } }));
  storage.beforeSet = (key) => {
    if (key === "future_progress_outbox:v1" || key.startsWith("future_progress_outbox_row:v2:")) {
      storage.beforeSet = null;
      tabB.enqueueProgressOutboxRequest("space_v", "/space-v/progress", record("b", "common/b.Space_V"), keyB);
    }
  };
  tabA.enqueueProgressOutboxRequest("space_v", "/space-v/progress", record("a", "common/a.Space_V"), keyA);
  const rowsAfterRace = tabA.readProgressOutbox();

  const sameStorage = new SharedStorage();
  const sameKey = "future_space_v_progress:hung:same";
  const older = record("same", "common/same.Space_V");
  const newer = { ...older, savedAt: "2026-07-21T00:05:00Z", state: { ...older.state, savedAt: "2026-07-21T00:05:00Z" } };
  sameStorage.setItem(sameKey, JSON.stringify(older));
  const sameA = runtime(sameStorage, async () => ({ payload: { ok: true } }));
  const sameB = runtime(sameStorage, async () => ({ payload: { ok: true } }));
  sameStorage.beforeSet = (key) => {
    if (key.startsWith("future_progress_outbox_row:v2:")) {
      sameStorage.beforeSet = null;
      sameStorage.setItem(sameKey, JSON.stringify(newer));
      sameB.enqueueProgressOutboxRequest("space_v", "/space-v/progress", newer, sameKey);
    }
  };
  sameA.enqueueProgressOutboxRequest("space_v", "/space-v/progress", older, sameKey);
  const sameRows = sameA.readProgressOutbox();

  let posts = 0;
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const drainStorage = new SharedStorage();
  const drainKey = "future_space_v_progress:hung:drain";
  drainStorage.setItem(drainKey, JSON.stringify(record("drain", "common/drain.Space_V")));
  const drainA = runtime(drainStorage, async () => { posts += 1; await gate; return { payload: { ok: true } }; });
  const drainB = runtime(drainStorage, async () => { posts += 1; await gate; return { payload: { ok: true } }; });
  drainA.enqueueProgressOutboxRequest("space_v", "/space-v/progress", record("drain", "common/drain.Space_V"), drainKey);
  const first = drainA.drainProgressOutbox();
  const second = drainB.drainProgressOutbox();
  await new Promise((resolve) => setImmediate(resolve));
  release();
  await Promise.all([first, second]);

  console.log(JSON.stringify({
    enqueue_race_rows: rowsAfterRace.length,
    enqueue_race_ids: rowsAfterRace.map((row) => row.id),
    duplicate_drain_posts: posts,
    same_id_rows: sameRows.length,
    same_id_saved_at: sameRows[0] && sameRows[0].savedAt,
    expected_safe_rows: 2,
    expected_safe_posts: 1,
  }));
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
