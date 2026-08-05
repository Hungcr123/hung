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
  isSpacePictureExtension: (value) => /\.(?:png|jpe?g|webp|space_picture)$/i.test(String(value || "")),
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

  calls.length = 0;
  context.serverLessonProgressPrefetchCache.clear();
  const endpointRows = [
    ["common/v.Space_V", ".Space_V", "/space-v/progress"],
    ["common/p.Space_P", ".Space_P", "/space-p/progress"],
    ["common/l.Space_L", ".Space_L", "/space-p/progress"],
    ["common/s.Space_S", ".Space_S", "/space-p/progress"],
    ["common/w.Space_W", ".Space_W", "/space-w/progress"],
  ];
  for (const [path, extension, endpoint] of endpointRows) {
    await context.fetchProgress({ path, extension });
    assert.ok(calls.at(-1).startsWith(endpoint), `${extension} used the wrong progress endpoint`);
  }

  calls.length = 0;
  context.serverLessonProgressPrefetchCache.clear();
  context.lessonVaultProgressSnapshotForPaths = () => ({ progress: { current: 2, total: 8, percent: 25 } });
  await context.fetchProgress({ path: "common/compact.Space_W", extension: ".Space_W" });
  assert.equal(calls.length, 1, "compact Vault summary must fall through to the full progress endpoint");
  calls.length = 0;
  context.serverLessonProgressPrefetchCache.clear();
  context.lessonVaultProgressSnapshotForPaths = () => ({ progress: { state: { currentIndex: 2 } } });
  await context.fetchProgress({ path: "common/full.Space_W", extension: ".Space_W" });
  assert.equal(calls.length, 0, "full checkpoint snapshot should avoid a duplicate progress request");
  console.log("lesson_progress_prefetch_identity=ok aliases=shared endpoints=V/P/L/S/W compact=network full=cache");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
