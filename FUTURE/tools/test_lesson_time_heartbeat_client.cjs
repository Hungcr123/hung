"use strict";

const fs = require("fs");
const vm = require("vm");

(async () => {
  const source = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
  const start = source.indexOf("      const createLessonStudyTimeSessionId =");
  const end = source.indexOf("      const stopLessonStudyTimeHeartbeat =", start);
  if (start < 0 || end < 0) throw new Error("Lesson heartbeat helpers not found");
  const sent = [];
  const storage = new Map();
  let requestCount = 0;
  const context = {
    window: { crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000001" } },
    currentLessonStudyPath: () => "common/test.Space_V",
    currentLessonStudyId: () => "ftg-lesson-test",
    currentLessonStudySpace: () => "Space_V",
    normalizeServerPathValue: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
    currentLessonSource: { title: "Test" },
    clean: (value) => String(value || "").trim(),
    authToken: "token",
    currentAuthUsername: "codex_time",
    authUser: { value: "codex_time" },
    localStorage: {
      get length() { return storage.size; },
      key: (index) => Array.from(storage.keys())[index] ?? null,
      getItem: (key) => storage.has(key) ? storage.get(key) : null,
      setItem: (key, value) => storage.set(key, String(value)),
      removeItem: (key) => storage.delete(key),
    },
    getStoredAuthToken: () => "token",
    lessonStudyTimeBusy: false,
    lessonStudyTimeSessionId: "",
    lessonStudyTimeSequence: 0,
    loadGate: { classList: { contains: () => true } },
    fetchAuthJson: async (_path, options) => {
      const body = JSON.parse(options.body);
      sent.push(body);
      requestCount += 1;
      if (requestCount === 1) {
        return { payload: { time: { sessionId: body.session_id, offlineLease: "signed-test-lease" } } };
      }
      if (requestCount === 2) throw new Error("simulated network outage");
      return { payload: { time: { sessionId: body.session_id, heartbeatReason: body.offline_claims ? "offline_credited" : "credited" } } };
    },
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nthis.sendTick = sendLessonStudyTimeTick;`, context);
  await context.sendTick(0, { start: true });
  await context.sendTick(30);
  const queuedPayload = [...storage.entries()].find(([key]) => key.startsWith("future_lesson_time_outbox_row:v2:"));
  if (!queuedPayload || JSON.parse(queuedPayload[1]).sequence !== 1) {
    throw new Error("Failed heartbeat was not retained in the durable client outbox");
  }
  await context.sendTick(30);
  if (sent.length !== 4) throw new Error(`Expected start, failed tick, offline batch, and live tick; got ${sent.length}`);
  if (sent[0].protocol !== "server-time-v1" || sent[0].sequence !== 0 || sent[0].seconds !== 0) {
    throw new Error("Start heartbeat is not compact server-time-v1 sequence zero");
  }
  if (sent.some((row) => row.lesson_id !== "ftg-lesson-test")) {
    throw new Error("Canonical lesson ID was not retained across live/offline heartbeats");
  }
  if (sent[1].session_id !== sent[0].session_id || sent[1].sequence !== 1 || sent[1].seconds !== 30) {
    throw new Error("Follow-up heartbeat did not reuse session and increment sequence");
  }
  if (!Array.isArray(sent[2].offline_claims) || sent[2].offline_claims[0].sequence !== 1 || sent[2].offline_lease !== "signed-test-lease") {
    throw new Error("Reconnect did not drain the signed offline heartbeat batch");
  }
  if (sent[3].sequence !== 2 || sent[3].session_id !== sent[0].session_id) {
    throw new Error("Live heartbeat did not continue after the offline batch");
  }
  if (JSON.parse(queuedPayload[1]).sequence !== 1) {
    throw new Error("Captured outbox evidence unexpectedly changed");
  }
  const finalOutbox = [...storage.entries()].filter(([key]) => key.startsWith("future_lesson_time_outbox_row:v2:"));
  if (finalOutbox.length !== 0) {
    throw new Error("Acknowledged offline heartbeat remained in the outbox");
  }
  if (Object.prototype.hasOwnProperty.call(sent[1], "client_time")) {
    throw new Error("Client wall-clock time must not be sent as trusted credit data");
  }
  console.log("lesson_time_heartbeat_client=ok protocol=server-time-v1 sequence=0,1,2 offline_outbox=drained client_clock=absent");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
