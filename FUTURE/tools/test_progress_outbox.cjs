const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const sourcePath = path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js");
const source = fs.readFileSync(sourcePath, "utf8");
const vocabConfigStart = source.indexOf("const configureVocabProgressCache =");
const vocabConfigEnd = source.indexOf("const compactVocabWordForRegistry =", vocabConfigStart);
const vocabConfig = source.slice(vocabConfigStart, vocabConfigEnd);
assert.match(vocabConfig, /spaceWStorageKey\(SPACE_V_PROGRESS_PREFIX, identity\)/);
assert.match(vocabConfig, /normalizeVocabProgressRecord\(readSpaceWJson\(progressKey\)\)/);
assert.doesNotMatch(vocabConfig, /progressKey:\s*""/);
const vocabSaveSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "14_vocab_sync_tasks.js"), "utf8");
const vocabSaveStart = vocabSaveSource.indexOf("const saveVocabProgressNow =");
const vocabSaveEnd = vocabSaveSource.indexOf("const saveVocabProgressCheckpointNow =", vocabSaveStart);
const vocabSave = vocabSaveSource.slice(vocabSaveStart, vocabSaveEnd);
assert.match(vocabSave, /writeSpaceWJson\(currentVocabProgressCache\.progressKey, record\)/);
const start = source.indexOf('const PROGRESS_OUTBOX_STORAGE_KEY = "future_progress_outbox:v1";');
const endMarker = 'window.addEventListener("online", () => {';
const eventStart = source.indexOf(endMarker, start);
const eventEnd = source.indexOf("      });", eventStart) + "      });".length;
assert.ok(start >= 0 && eventStart > start && eventEnd > eventStart, "outbox source block not found");
const outboxSource = source.slice(start, eventEnd);

class MemoryStorage {
  constructor(seed = {}) {
    this.map = new Map(Object.entries(seed));
  }
  get length() { return this.map.size; }
  key(index) { return Array.from(this.map.keys())[index] ?? null; }
  getItem(key) { return this.map.has(String(key)) ? this.map.get(String(key)) : null; }
  setItem(key, value) { this.map.set(String(key), String(value)); }
  removeItem(key) { this.map.delete(String(key)); }
  snapshot() { return Object.fromEntries(this.map); }
}

function createRuntime(storage, fetchImpl) {
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
    readSpaceWJson: (key) => {
      try { return JSON.parse(storage.getItem(key) || "null"); } catch { return null; }
    },
    writeSpaceWJson: (key, value) => {
      try { storage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
    },
    fetchAuthJson: fetchImpl,
    pdfProgressLocalSharedKey: (filePath) => `future_space_pdf_progress:local:${filePath}`,
    window: {
      localStorage: storage,
      addEventListener: () => {},
      setTimeout: () => 1,
      clearTimeout: () => {},
    },
  };
  vm.createContext(context);
  vm.runInContext(`${outboxSource}\n;globalThis.__outbox = {readProgressOutbox, enqueueProgressOutboxRequest, acknowledgeProgressOutboxRequest, drainProgressOutbox, seedProgressOutboxFromLocalStorage, shouldKeepPendingLocalProgress, progressRecordTimestampMs};`, context);
  return context.__outbox;
}

const progressKey = "future_space_w_progress:hung:lesson-1";
const baseRecord = {
  identity: "lesson-1",
  savedAt: "2026-07-19T10:00:00Z",
  pendingServerSync: true,
  state: { savedAt: "2026-07-19T10:00:00Z", lessonSource: { source: "server", path: "common/probe.Space_W" } },
};

(async () => {
  let storage = new MemoryStorage({ [progressKey]: JSON.stringify(baseRecord) });
  let fail = true;
  const sent = [];
  let runtime = createRuntime(storage, async (_endpoint, options) => {
    if (fail) throw new Error("server offline");
    sent.push(JSON.parse(options.body));
    return { payload: { ok: true } };
  });
  assert.equal(runtime.progressRecordTimestampMs({ savedAt: "2026-07-20T02:50:00Z" }), runtime.progressRecordTimestampMs({ savedAt: "2026-07-20T09:50:00+07:00" }));
  assert.equal(runtime.progressRecordTimestampMs({ savedAt: "2026-07-20 09:50:00" }), 1784515800000);
  assert.equal(runtime.progressRecordTimestampMs({}), 0);

  runtime.enqueueProgressOutboxRequest("space_w", "/space-w/progress", baseRecord, progressKey);
  assert.equal(runtime.readProgressOutbox().length, 1);
  assert.equal((await runtime.drainProgressOutbox()), false);
  assert.equal(runtime.readProgressOutbox().length, 1, "offline drain must retain the row");

  storage = new MemoryStorage(storage.snapshot());
  runtime = createRuntime(storage, async (_endpoint, options) => {
    sent.push(JSON.parse(options.body));
    return { payload: { ok: true } };
  });
  runtime.seedProgressOutboxFromLocalStorage();
  assert.equal(runtime.readProgressOutbox().length, 1, "reload must rediscover pending local progress");
  assert.equal((await runtime.drainProgressOutbox()), true);
  assert.equal(runtime.readProgressOutbox().length, 0);

  const synced = JSON.parse(storage.getItem(progressKey));
  assert.equal(synced.pendingServerSync, false);
  assert.equal(sent.at(-1).path, "common/probe.Space_W");

  const newer = { ...baseRecord, savedAt: "2026-07-19T10:05:00Z", state: { ...baseRecord.state, savedAt: "2026-07-19T10:05:00Z" } };
  storage.setItem(progressKey, JSON.stringify(baseRecord));
  runtime = createRuntime(storage, async () => ({ payload: { ok: true } }));
  const oldRow = runtime.enqueueProgressOutboxRequest("space_w", "/space-w/progress", baseRecord, progressKey);
  storage.setItem(progressKey, JSON.stringify(newer));
  runtime.enqueueProgressOutboxRequest("space_w", "/space-w/progress", newer, progressKey);
  runtime.acknowledgeProgressOutboxRequest(oldRow, baseRecord);
  assert.equal(runtime.readProgressOutbox().length, 1, "an old response must not acknowledge a newer checkpoint");
  assert.equal(runtime.shouldKeepPendingLocalProgress(newer, baseRecord), true);

  const clearStorage = new MemoryStorage();
  const clearSent = [];
  runtime = createRuntime(clearStorage, async (_endpoint, options) => {
    clearSent.push(JSON.parse(options.body));
    return { payload: { ok: true } };
  });
  runtime.enqueueProgressOutboxRequest("space_w", "/space-w/progress", {
    action: "clear",
    path: "common/probe.Space_W",
    identity: "lesson-1",
    state: {},
  }, progressKey);
  await runtime.drainProgressOutbox();
  assert.equal(clearSent[0].action, "clear", "offline reset must survive without a local progress record");
  assert.equal(runtime.readProgressOutbox().length, 0);

  const canonicalStorage = new MemoryStorage();
  const canonicalSent = [];
  runtime = createRuntime(canonicalStorage, async (_endpoint, options) => {
    canonicalSent.push(JSON.parse(options.body));
    return { payload: { ok: true } };
  });
  const canonicalKey = "future_space_w_progress:hung:ftg-lesson-42";
  const canonicalRecord = {
    lesson_id: "ftg-lesson-42",
    file_id: "ftg-lesson-42",
    task_owner: "hung",
    space_type: "Space_W",
    operation_id: "op-space-w-42",
    _serverRevision: 7,
    path: "hung/linked/test.Space_W",
    savedAt: "2026-07-19T11:00:00Z",
    pendingServerSync: true,
    state: { savedAt: "2026-07-19T11:00:00Z" },
  };
  canonicalStorage.setItem(canonicalKey, JSON.stringify(canonicalRecord));
  runtime.enqueueProgressOutboxRequest("space_w", "/space-w/progress", canonicalRecord, canonicalKey);
  await runtime.drainProgressOutbox();
  assert.equal(canonicalSent[0].lesson_id, "ftg-lesson-42");
  assert.equal(canonicalSent[0].file_id, "ftg-lesson-42");
  assert.equal(canonicalSent[0].task_owner, "hung");
  assert.equal(canonicalSent[0].operation_id, "op-space-w-42");
  assert.equal(canonicalSent[0].revision, 7);

  const allRecords = {
    "future_space_w_progress:hung:w": { ...baseRecord, identity: "w" },
    "future_space_q_progress:hung:q": { ...baseRecord, identity: "q" },
    "future_space_v_progress:hung:v": { ...baseRecord, identity: "v", path: "common/v.Space_V" },
    "future_space_p_progress:hung:p": { ...baseRecord, identity: "p" },
    "future_space_p_progress_space_l:hung:l": { ...baseRecord, identity: "l" },
    "future_space_p_progress_space_s:hung:s": { ...baseRecord, identity: "s" },
    "future_space_pdf_progress:hung:pdf": { ...baseRecord, identity: "pdf", path: "common/a.pdf", page: 3, pages: 9 },
    "future_pdf_ai_question_progress:hung:ai": {
      path: "common/a.pdf",
      mode: "pdf",
      page: 3,
      regionKey: "region-1",
      localSavedAt: "2026-07-19T10:00:00Z",
      pendingServerSync: true,
      order: ["q1"],
      completed: {},
      results: {},
    },
  };
  const allStorage = new MemoryStorage(Object.fromEntries(Object.entries(allRecords).map(([key, value]) => [key, JSON.stringify(value)])));
  const endpoints = [];
  runtime = createRuntime(allStorage, async (endpoint) => {
    endpoints.push(endpoint);
    return { payload: { ok: true } };
  });
  assert.equal(runtime.seedProgressOutboxFromLocalStorage(), 8);
  await runtime.drainProgressOutbox();
  assert.equal(runtime.readProgressOutbox().length, 0);
  assert.equal(new Set(endpoints).size, 6, "all Space families should use their expected shared endpoints");

  console.log("progress_outbox_smoke=ok cases=offline,reload,newer-wins,clear,all-spaces");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
