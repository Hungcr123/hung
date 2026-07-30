"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
const start = source.indexOf("      const createLessonStudyTimeSessionId =");
const end = source.indexOf("      const stopLessonStudyTimeHeartbeat =", start);
assert.ok(start >= 0 && end > start, "lesson time client block missing");
const block = source.slice(start, end);

class SharedStorage {
  constructor() { this.map = new Map(); }
  get length() { return this.map.size; }
  key(index) { return Array.from(this.map.keys())[index] ?? null; }
  getItem(key) { return this.map.has(String(key)) ? this.map.get(String(key)) : null; }
  setItem(key, value) { this.map.set(String(key), String(value)); }
  removeItem(key) { this.map.delete(String(key)); }
}

function createTab(storage, tabName, sent) {
  const context = {
    window: { crypto: { randomUUID: () => `${tabName}-0000-4000-8000-000000000001` } },
    currentLessonStudyPath: () => "common/test.Space_V",
    currentLessonStudyId: () => "ftg-lesson-test",
    currentLessonStudySpace: () => "Space_V",
    normalizeServerPathValue: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
    currentLessonSource: { title: "Test" },
    clean: (value) => String(value || "").trim(),
    authToken: "token",
    currentAuthUsername: "hung",
    authUser: { value: "hung" },
    localStorage: storage,
    getStoredAuthToken: () => "token",
    lessonStudyTimeBusy: false,
    lessonStudyTimeSessionId: "",
    lessonStudyTimeSequence: 0,
    loadGate: { classList: { contains: () => true } },
    fetchAuthJson: async (_path, options) => {
      const body = JSON.parse(options.body);
      sent.push({ tabName, body });
      return { payload: { time: { sessionId: body.session_id, offlineLease: `lease-${tabName}` } } };
    },
  };
  vm.createContext(context);
  vm.runInContext(`${block}\n;globalThis.api={sendLessonStudyTimeTick,releaseLessonStudyTimeTabLease,queueLessonStudyTimeOfflineClaim,readLessonStudyTimeOutbox,lessonStudyTimeLeaseKey};`, context);
  return context.api;
}

(async () => {
  const storage = new SharedStorage();
  const sent = [];
  const tabA = createTab(storage, "tab-a", sent);
  const tabB = createTab(storage, "tab-b", sent);
  assert.equal(
    tabA.lessonStudyTimeLeaseKey("common/test.Space_V", "ftg-lesson-test"),
    tabA.lessonStudyTimeLeaseKey("hung/linked/test.Space_V", "ftg-lesson-test"),
    "direct and folder-link paths must share one canonical lesson-time lease",
  );
  await Promise.all([tabA.sendLessonStudyTimeTick(0, { start: true }), tabB.sendLessonStudyTimeTick(0, { start: true })]);
  assert.equal(sent.length, 1, "only one tab may start the account heartbeat");
  const leader = sent[0].tabName === "tab-a" ? tabA : tabB;
  const follower = leader === tabA ? tabB : tabA;
  assert.equal(leader.releaseLessonStudyTimeTabLease(), true);
  await follower.sendLessonStudyTimeTick(0, { start: true });
  assert.equal(sent.length, 2, "follower must take over after the leader releases its lease");

  assert.equal(tabA.queueLessonStudyTimeOfflineClaim({ path: "common/a.Space_V", seconds: 30, session_id: "session-a", sequence: 1, offline_lease: "lease-a" }), true);
  assert.equal(tabB.queueLessonStudyTimeOfflineClaim({ path: "common/b.Space_V", seconds: 30, session_id: "session-b", sequence: 1, offline_lease: "lease-b" }), true);
  const rows = tabA.readLessonStudyTimeOutbox();
  assert.equal(rows.length, 2, "different tabs must not overwrite each other's time claims");
  assert.deepEqual(new Set(rows.map((row) => row.session_id)), new Set(["session-a", "session-b"]));
  console.log("lesson_time_multitab=ok leader_posts=1 failover=1 durable_rows=2");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
