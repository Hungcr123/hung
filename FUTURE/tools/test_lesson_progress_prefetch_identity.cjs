"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const start = source.indexOf("      const serverLessonProgressSpaceForPath =");
const end = source.indexOf("      const scheduleServerLessonProgressPrefetch =", start);
assert.ok(start >= 0 && end > start, "lesson progress prefetch block missing");

const calls = [];
const context = {
  Date,
  URLSearchParams,
  currentAuthUsername: "hung",
  currentAuthIsAdmin: false,
  SERVER_LESSON_PROGRESS_PREFETCH_TTL_MS: 30000,
  serverLessonProgressPrefetchCache: new Map(),
  clean: (value) => String(value ?? "").trim(),
  normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  isSpacePictureExtension: () => false,
  fetchProgressJsonFast: async (url) => {
    calls.push(url);
    return { payload: { ok: true }, etag: "etag" };
  },
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\n;globalThis.fetchProgress=fetchServerProgressForEntry;`, context);

(async () => {
  const direct = { path: "common/test.Space_W", extension: ".Space_W", lesson_id: "ftg-lesson-42", identity_revision: 7 };
  const linked = { path: "hung/link/test.Space_W", extension: ".Space_W", lesson_id: "ftg-lesson-42", identity_revision: 7 };
  await Promise.all([context.fetchProgress(direct), context.fetchProgress(linked)]);
  assert.equal(calls.length, 1, "direct and link aliases must share one ID/revision cache entry");
  assert.match(calls[0], /identity=ftg-lesson-42/);
  assert.match(calls[0], /lesson_id=ftg-lesson-42/);

  await context.fetchProgress({ ...linked, identity_revision: 8 });
  assert.equal(calls.length, 2, "identity revision change must invalidate the business cache key");

  await context.fetchProgress({ path: "common/legacy-a.Space_W", extension: ".Space_W" });
  await context.fetchProgress({ path: "common/legacy-b.Space_W", extension: ".Space_W" });
  assert.equal(calls.length, 4, "legacy path fallback must remain distinct until migration");
  console.log("lesson_progress_prefetch_identity=ok direct_link=shared revision=invalidate legacy=path-fallback");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
