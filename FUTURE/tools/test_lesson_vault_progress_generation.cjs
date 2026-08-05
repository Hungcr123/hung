const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const start = source.indexOf("const lessonProgressOverrideKey =");
const end = source.indexOf("const shouldKeepExistingLessonProgressOverride =", start);
assert.ok(start >= 0 && end > start, "Lesson Vault snapshot runtime block not found");
assert.doesNotMatch(source.slice(start, end), /fetch\(|fetchServer|\/progress/, "snapshot merge must remain frontend-local");

const context = {
  clean: (value) => String(value ?? "").trim(),
  normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  normalizeTaskPath: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "").toLowerCase(),
  futureRouteSpaceForFilePath: (value) => {
    const match = String(value ?? "").match(/\.(Space_[A-Za-z]+)$/i);
    return match ? match[1] : "";
  },
  lessonProgressOverrides: new Map(),
  shouldKeepExistingLessonProgressOverride: () => false,
  performance: { now: () => 0 },
  window: {},
  Date,
  JSON,
  Map,
  Object,
  Array,
  Number,
  String,
  Math,
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nglobalThis.__snapshotTest = {
  rememberLessonVaultProgressSnapshot,
  applyLessonVaultProgressSnapshotToPayload,
  generation: () => lessonVaultProgressSnapshotGeneration,
};`, context);

const runtime = context.__snapshotTest;
const sharedId = "legacy-collision-1";
const pdfPath = "common/PDF/Doraemon/Doremon Ep 01.pdf";
const vocabPath = "common/Vocab/File 02.Space_V";
const movedVocabPath = "common/Vocab Renamed/File 02.Space_V";

const snapshot10 = {
  items: {
    [pdfPath]: {
      path: pdfPath,
      lesson_id: sharedId,
      space: "Space_PDF",
      server_revision: 10,
      updatedAt: "2026-07-31T01:00:00Z",
      progress: { space: "Space_PDF", done: 10, total: 185, percent: 5, text: "10/185" },
      study: { space: "Space_PDF" },
    },
    [vocabPath]: {
      path: vocabPath,
      lesson_id: sharedId,
      space: "Space_V",
      server_revision: 10,
      updatedAt: "2026-07-31T01:00:00Z",
      progress: { space: "Space_V", done: 4, total: 10, percent: 40, text: "4/10" },
      study: { space: "Space_V" },
    },
  },
};

assert.ok(runtime.rememberLessonVaultProgressSnapshot(snapshot10) > 0);
const generation10 = runtime.generation();
const cachedPayload = {
  entries: [
    { type: "file", path: pdfPath, lesson_id: sharedId, extension: ".pdf", study: {} },
    { type: "file", path: movedVocabPath, effective_path: vocabPath, lesson_id: sharedId, extension: ".Space_V", study: {} },
  ],
};
const merged10 = runtime.applyLessonVaultProgressSnapshotToPayload(cachedPayload);
assert.equal(merged10.entries[0].study.progress.text, "10/185");
assert.equal(merged10.entries[1].study.progress.text, "4/10", "same lesson ID in another Space must not receive PDF progress");
assert.equal(merged10.__ftLessonVaultProgressSnapshotGeneration, generation10);

const repeated10 = runtime.applyLessonVaultProgressSnapshotToPayload(merged10);
assert.strictEqual(repeated10, merged10, "same generation render must be idempotent");
assert.equal(runtime.rememberLessonVaultProgressSnapshot(snapshot10), 0, "identical snapshot must not advance generation");
assert.equal(runtime.generation(), generation10);

const stale9 = {
  items: {
    [pdfPath]: {
      ...snapshot10.items[pdfPath],
      updatedAt: "2026-07-31T00:59:00Z",
      progress: { space: "Space_PDF", done: 1, total: 185, percent: 1, text: "1/185" },
    },
  },
};
assert.equal(runtime.rememberLessonVaultProgressSnapshot(stale9), 0, "older snapshot must be rejected");
assert.equal(runtime.applyLessonVaultProgressSnapshotToPayload(merged10).entries[0].study.progress.text, "10/185");

const staleAliasPath = "common/PDF/Doraemon Renamed/Doremon Ep 01.pdf";
const staleAlias9 = {
  items: {
    [staleAliasPath]: {
      ...stale9.items[pdfPath],
      path: staleAliasPath,
      lesson_id: sharedId,
    },
  },
};
assert.equal(runtime.rememberLessonVaultProgressSnapshot(staleAlias9), 0, "older canonical snapshot must not create a stale alias key");
assert.equal(
  runtime.applyLessonVaultProgressSnapshotToPayload({
    entries: [{ type: "file", path: staleAliasPath, lesson_id: sharedId, extension: ".pdf", study: {} }],
  }).entries[0].study.progress.text,
  "10/185",
  "renamed entry must continue using the newest canonical snapshot",
);

const snapshot11 = {
  items: {
    [pdfPath]: {
      ...snapshot10.items[pdfPath],
      server_revision: 11,
      updatedAt: "2026-07-31T01:01:00Z",
      progress: { space: "Space_PDF", done: 122, total: 185, percent: 66, text: "122/185 - 66%" },
    },
  },
};
assert.ok(runtime.rememberLessonVaultProgressSnapshot(snapshot11) > 0);
assert.ok(runtime.generation() > generation10);
const merged11 = runtime.applyLessonVaultProgressSnapshotToPayload(merged10);
assert.notStrictEqual(merged11, merged10, "new generation must reapply to a cached payload");
assert.equal(merged11.entries[0].study.progress.text, "122/185 - 66%");
assert.equal(merged11.entries[1].study.progress.text, "4/10");

const equalTimestampOlderRevision = {
  items: {
    [pdfPath]: {
      ...snapshot11.items[pdfPath],
      server_revision: 10,
      progress: { space: "Space_PDF", done: 50, total: 185, percent: 27, text: "50/185" },
    },
  },
};
assert.equal(runtime.rememberLessonVaultProgressSnapshot(equalTimestampOlderRevision), 0, "lower revision at equal timestamp must be rejected");
assert.equal(runtime.applyLessonVaultProgressSnapshotToPayload(merged11).entries[0].study.progress.text, "122/185 - 66%");

const newerPayload = {
  entries: [{
    type: "file",
    path: pdfPath,
    lesson_id: sharedId,
    extension: ".pdf",
    updatedAt: "2026-07-31T01:02:00Z",
    study: {
      progress: { space: "Space_PDF", done: 130, total: 185, percent: 70, text: "130/185 - 70%" },
      updatedAt: "2026-07-31T01:02:00Z",
    },
  }],
};
assert.equal(
  runtime.applyLessonVaultProgressSnapshotToPayload(newerPayload).entries[0].study.progress.text,
  "130/185 - 70%",
  "older RAM snapshot must not overwrite a newer tree payload",
);

const repeatCount = 50000;
const repeatStarted = process.hrtime.bigint();
for (let index = 0; index < repeatCount; index += 1) {
  runtime.applyLessonVaultProgressSnapshotToPayload(merged11);
}
const repeatMs = Number(process.hrtime.bigint() - repeatStarted) / 1e6;

console.log(
  `lesson_vault_progress_generation=ok reapply=true idempotent=true stale_rejected=true cross_space=true alias=true local_only=true `
  + `stale_alias_rejected=true same_generation_50k_ms=${repeatMs.toFixed(3)}`,
);
