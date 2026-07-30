const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const saveSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");
const vaultSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const chipSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "14_vocab_sync_tasks.js"), "utf8");
const overrideStart = source.indexOf("const spaceWProgressOverrideFromRecord =");
const overrideEnd = source.indexOf("const paragraphProgressOverrideFromRecord =", overrideStart);
assert.ok(overrideStart >= 0 && overrideEnd > overrideStart, "Space_W override not found");

const context = {
  clean: (value) => String(value || "").trim(),
  lessonNodes: [],
  pendingLessonNodes: [],
};
vm.createContext(context);
vm.runInContext(`${source.slice(overrideStart, overrideEnd)}\nthis.toProgress = spaceWProgressOverrideFromRecord;`, context);

const active = context.toProgress({
  nodeIndex: 0,
  nodeCount: 2,
  runId: "run-new",
  savedAt: "2026-07-19T10:00:00Z",
  state: { activeRun: true, runId: "run-new", nodeCount: 2, index: 0 },
});
assert.deepEqual([active.done, active.total, active.percent, active.text], [0, 4, 0, "0/4"]);
assert.equal(active.activeRun, true);

const review = context.toProgress({
  nodeIndex: 1,
  nodeCount: 2,
  runId: "run-new",
  state: { activeRun: true, reviewing: true, reviewModeActive: true, reviewMastered: [0], nodeCount: 2, index: 1 },
});
assert.deepEqual([review.done, review.total, review.percent], [3, 4, 75]);

const trained = context.toProgress({
  nodeIndex: 2,
  nodeCount: 5,
  runId: "run-new",
  state: { activeRun: true, nodeCount: 5, index: 2, spaceWTrainModeExpanded: true },
});
assert.deepEqual([trained.done, trained.total, trained.percent], [2, 10, 20]);

const complete = context.toProgress({
  nodeIndex: 4,
  nodeCount: 5,
  runId: "run-new",
  state: { reviewFinished: true, nodeCount: 5, index: 4 },
});
assert.deepEqual([complete.done, complete.total, complete.percent, complete.completed], [10, 10, 100, true]);

const guardStart = source.indexOf("const shouldKeepExistingLessonProgressOverride =");
const guardEnd = source.indexOf("const setLessonProgressOverride =", guardStart);
const guardContext = {
  clean: context.clean,
  lessonProgressIsActivePartial: (progress) => Boolean(progress && progress.done < progress.total && (progress.activeRun || progress.reviewing || progress.done > 0)),
  lessonProgressSnapshotTimestamp: (row) => Date.parse(row.updatedAt || row.savedAt || "") || 0,
};
vm.createContext(guardContext);
vm.runInContext(`${source.slice(guardStart, guardEnd)}\nthis.guard = shouldKeepExistingLessonProgressOverride;`, guardContext);

const current = { progress: { ...active, updatedAt: "2026-07-19T10:00:00Z" } };
assert.equal(guardContext.guard(current, { space: "Space_W", done: 2, total: 2, percent: 100, completed: true, updatedAt: "2026-07-19T10:01:00Z" }), true);
assert.equal(guardContext.guard(current, { ...active, done: 1, total: 8, percent: 13, updatedAt: "2026-07-19T10:01:00Z" }), false);
assert.equal(guardContext.guard(current, { ...active, done: 1, total: 4, percent: 25, updatedAt: "2026-07-19T09:59:00Z" }), true);

const saveStart = saveSource.indexOf("const saveSpaceWProgressNow =");
const saveEnd = saveSource.indexOf("const queueSpaceWProgressSave =", saveStart);
assert.match(saveSource.slice(saveStart, saveEnd), /return ok \? record : false;/, "Back must receive the saved record, not a boolean");
const displayStart = vaultSource.indexOf("function lessonVaultDisplayProgressForStudy");
const displayEnd = vaultSource.indexOf("function syncLessonVaultChartFromChip", displayStart);
const displaySource = vaultSource.slice(displayStart, displayEnd);
const completionStart = displaySource.indexOf("const completionTimestamp =");
const completionEnd = displaySource.indexOf("const pinnedSource =", completionStart);
const completionSource = displaySource.slice(completionStart, completionEnd);
assert.doesNotMatch(completionSource, /source\.(updatedAt|updated_at|savedAt|saved_at)/, "active-run timestamps are not completion timestamps");
assert.match(saveSource, /normalSentenceCount/);
assert.match(saveSource, /trainSentenceCount/);
const beginReviewStart = saveSource.indexOf("const beginReviewMode =");
const beginReviewEnd = saveSource.indexOf("const goNextNode =", beginReviewStart);
const beginReviewSource = saveSource.slice(beginReviewStart, beginReviewEnd);
assert.ok(beginReviewSource.indexOf("reviewModeActive = true") < beginReviewSource.indexOf("saveSpaceWProgressNow()"), "stage 2 must be marked before its checkpoint is saved");
const trainReviewStart = source.indexOf("const startSpaceWTrainReviewFromSaved =");
const trainReviewEnd = source.indexOf("const enterLoadedLessonNow =", trainReviewStart);
const trainReviewSource = source.slice(trainReviewStart, trainReviewEnd);
assert.match(trainReviewSource, /record\.runId \|\| record\.run_id \|\| savedState\.runId/);
assert.doesNotMatch(trainReviewSource, /spaceWActiveRunId = `space-w-\$\{Date\.now\(\)/, "Review must not allocate a new run ID");
assert.match(chipSource, /Sentence\$\{sentenceCount === 1 \? "" : "s"\}/);
assert.match(chipSource, /`\$\{normalSentenceCount\} Normal`/);
assert.match(chipSource, /`\$\{trainSentenceCount\} Train`/);

console.log("space_w_dynamic_progress=ok stage2_preserves_run stage_flag_saved_first new=0/4 review=3/4 completion=10/10");
