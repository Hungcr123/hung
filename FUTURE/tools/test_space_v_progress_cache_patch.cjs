const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const readPart = (name) => fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", name), "utf8");
const progressSource = readPart("13_translation_vocab_sync.js");
const vocabLoaderSource = readPart("12_question_translation_loader.js");
const vocabSyncSource = readPart("14_vocab_sync_tasks.js");
const taskSource = readPart("16_notices_vocabulary_missions.js");
const vaultRenderSource = readPart("20_pdf_page_progress.js");
const eventSource = readPart("21_progress_bootstrap_events.js");
const returnSource = readPart("17_vocab_to_pdf_bootstrap.js");

const guardStart = progressSource.indexOf("const shouldKeepExistingLessonProgressOverride =");
const guardEnd = progressSource.indexOf("const setLessonProgressOverride =", guardStart);
assert.ok(guardStart >= 0 && guardEnd > guardStart, "progress override guard not found");
const guardSource = progressSource.slice(guardStart, guardEnd);
const context = {
  clean: (value) => String(value || "").trim(),
  lessonProgressIsActivePartial: (progress) => Boolean(progress && progress.done < progress.total && (progress.done > 0 || progress.activeRun)),
  lessonProgressSnapshotTimestamp: (row) => Date.parse(row.updatedAt || row.savedAt || "") || 0,
};
vm.createContext(context);
vm.runInContext(`${guardSource}\nthis.guard = shouldKeepExistingLessonProgressOverride;`, context);

const current = { progress: { space: "Space_V", done: 9, total: 10, percent: 90, activeRun: true, runId: "old-run", updatedAt: "2026-07-19T12:00:00Z" } };
assert.equal(context.guard(current, { space: "Space_V", done: 2, total: 10, percent: 20, activeRun: true, runId: "new-run", updatedAt: "2026-07-19T13:00:00Z" }), false, "new run must replace the older higher progress");
assert.equal(context.guard(current, { space: "Space_V", done: 2, total: 10, percent: 20, activeRun: true, runId: "old-run", updatedAt: "2026-07-19T11:00:00Z" }), true, "stale same-run progress must not move backward");
assert.equal(context.guard({ progress: { ...current.progress, runId: "" } }, { space: "Space_V", done: 2, total: 10, percent: 20, activeRun: true, runId: "new-run", updatedAt: "2026-07-19T13:00:00Z" }), false, "newer identified run must replace a legacy override without run id");
assert.equal(context.guard(current, { space: "Space_V", done: 10, total: 10, percent: 100, completed: true, updatedAt: "2026-07-19T13:00:00Z" }), true, "completion history without a run id must not overwrite an active run");
assert.equal(context.guard(current, { space: "Space_V", done: 10, total: 10, percent: 100, completed: true, activeRun: true, runId: "old-run", updatedAt: "2026-07-19T13:00:00Z" }), true, "synthetic lifetime completion must not overwrite its still-active run");
assert.equal(context.guard(current, { space: "Space_V", done: 10, total: 10, percent: 100, completed: true, runId: "old-run", updatedAt: "2026-07-19T13:00:00Z" }), false, "real completion for the active run must be accepted");

const rememberStart = progressSource.indexOf("const rememberLessonVaultProgressSnapshot =");
const rememberEnd = progressSource.indexOf("const updateLessonVaultProgressSnapshotForPaths =", rememberStart);
const rememberSource = progressSource.slice(rememberStart, rememberEnd);
assert.match(rememberSource, /shouldKeepExistingLessonProgressOverride\(activeOverride, incomingProgress\)/);
assert.doesNotMatch(rememberSource, /lessonVaultProgressSnapshot\.set\(key, item\);\s*lessonProgressOverrides\.delete\(key\)/);

const setStart = progressSource.indexOf("const setLessonProgressOverride =");
const setEnd = progressSource.indexOf("const clearLessonProgressOverride =", setStart);
const setSource = progressSource.slice(setStart, setEnd);
assert.match(setSource, /patchLessonVaultCachedProgress\(paths, progress, \{ render: true, force: Boolean\(options\.force\) \}\)/);
assert.match(setSource, /!options\.force && shouldKeepExistingLessonProgressOverride/);
assert.match(progressSource, /if \(options\.force\)[\s\S]*progress_text: clean\(progress\.text/);
assert.match(setSource, /__ftPatchLessonTaskPanelProgress\(paths, progress\)/);

const vocabStart = progressSource.indexOf("const vocabProgressOverrideFromRecord =");
const vocabEnd = progressSource.indexOf("const questionProgressOverrideFromRecord =", vocabStart);
const vocabSource = progressSource.slice(vocabStart, vocabEnd);
assert.match(vocabSource, /runId/);
assert.match(vocabSource, /savedAt/);
assert.match(vocabSource, /updatedAt/);
assert.match(vocabSource, /const hasLearnedProgress =/);
assert.match(vocabSource, /hasLearnedProgress \? learned : nodeIndex/);

const hydrationStart = taskSource.indexOf("const canonicalProgressSummaryFromHydration =");
const hydrationEnd = taskSource.indexOf("const hydrateLessonTaskProgress =", hydrationStart);
assert.ok(hydrationStart >= 0 && hydrationEnd > hydrationStart, "canonical hydration selector not found");
const hydrationSource = taskSource.slice(hydrationStart, hydrationEnd);
const hydrationContext = {
  clean: (value) => String(value || "").trim(),
  vocabProgressOverrideFromRecord: () => ({ done: 10, total: 10, completed: true }),
  questionProgressOverrideFromRecord: () => null,
  paragraphProgressOverrideFromRecord: () => null,
  spaceWProgressOverrideFromRecord: () => null,
};
vm.createContext(hydrationContext);
vm.runInContext(`${hydrationSource}\nthis.progressOverrideFromHydration = progressOverrideFromHydration;`, hydrationContext);
const canonicalActiveRun = hydrationContext.progressOverrideFromHydration("Space_V", {
  progress: { complete: true, nodeCount: 10, learnedCount: 10 },
  summary: {
    space: "Space_V",
    done: 0,
    total: 10,
    percent: 0,
    completed: false,
    activeRun: true,
    in_progress: true,
    previously_completed: true,
    completedRuns: 12,
    runId: "space-v-current-run",
    savedAt: "2026-07-24T01:00:00Z",
  },
});
assert.equal(canonicalActiveRun.done, 0, "canonical current run must outrank stale raw completion");
assert.equal(canonicalActiveRun.total, 10);
assert.equal(canonicalActiveRun.completed, false);
assert.equal(canonicalActiveRun.activeRun, true);
assert.equal(canonicalActiveRun.previously_completed, true);
assert.equal(canonicalActiveRun.completedRuns, 12);
assert.equal(canonicalActiveRun.runId, "space-v-current-run");
assert.equal(canonicalActiveRun.text, "0/10");

const normalizeVocabStart = progressSource.indexOf("const normalizeVocabProgressRecord =");
const normalizeVocabEnd = progressSource.indexOf("const vocabSavedSummary =", normalizeVocabStart);
assert.ok(normalizeVocabStart >= 0 && normalizeVocabEnd > normalizeVocabStart, "vocabulary progress normalizer not found");
const normalizeVocabSource = progressSource.slice(normalizeVocabStart, normalizeVocabEnd);
const normalizeVocabContext = {
  clean: (value) => String(value || "").trim(),
  vocabProgressLearnedCountFromRecord: () => 0,
};
vm.createContext(normalizeVocabContext);
vm.runInContext(`${normalizeVocabSource}\nthis.normalize = normalizeVocabProgressRecord;`, normalizeVocabContext);
const normalizedActiveRun = normalizeVocabContext.normalize({
  nodeCount: 10,
  learnedCount: 3,
  complete: true,
  completedRuns: 12,
  runId: "space-v-current-run",
  activeRun: true,
  state: { currentIndex: 3, complete: true, activeRun: true, runId: "space-v-current-run" },
});
assert.equal(normalizedActiveRun.activeRun, true);
assert.equal(normalizedActiveRun.complete, false, "active run must not inherit stale completion flag");
assert.equal(normalizedActiveRun.completedRuns, 12, "lifetime completion count must survive normalization");
assert.equal(normalizedActiveRun.runId, "space-v-current-run");

const displayProgressStart = progressSource.indexOf("const normalizedLessonProgress =");
const displayProgressEnd = progressSource.indexOf("const lessonProgressOverrideKey =", displayProgressStart);
assert.ok(displayProgressStart >= 0 && displayProgressEnd > displayProgressStart, "normalized display progress helper not found");
const displayProgressSource = progressSource.slice(displayProgressStart, displayProgressEnd);
const displayProgressContext = {
  clean: (value) => String(value || "").trim(),
  resolveLessonProgressRepeatState: (source) => Boolean(source.completedRuns > 0 && source.activeRun && !source.isCompleteDisplay),
};
vm.createContext(displayProgressContext);
vm.runInContext(`${displayProgressSource}\nthis.display = normalizedLessonProgress;`, displayProgressContext);
const activeDisplay = displayProgressContext.display({
  progress: { done: 0, total: 10, percent: 100, complete: true, activeRun: true, in_progress: true, completedRuns: 12 },
});
assert.equal(activeDisplay.percent, 0, "active run must derive chart percent from current done/total");
assert.equal(activeDisplay.completed, false, "active run must not render as completed");
assert.equal(activeDisplay.isRepeatCompletion, true, "active run after lifetime completion must be repeat/orange");

const learnedWordsStart = progressSource.indexOf("const vocabLearnedWordRecordsFrom =");
const learnedWordsEnd = progressSource.indexOf("const currentVocabLearnedWordRecords =", learnedWordsStart);
const learnedWordsSource = progressSource.slice(learnedWordsStart, learnedWordsEnd);
assert.match(learnedWordsSource, /if \(!wantedKeys\.size\) \{\s*return \[\];/);

const snapshotStart = progressSource.indexOf("const vocabProgressSnapshot =");
const snapshotEnd = progressSource.indexOf("const currentVocabServerPath =", snapshotStart);
const snapshotSource = progressSource.slice(snapshotStart, snapshotEnd);
assert.match(snapshotSource, /complete: false/);
assert.match(snapshotSource, /lessonComplete: false/);

const sendStart = progressSource.indexOf("const sendVocabServerProgress =");
const sendEnd = progressSource.indexOf("const clearVocabServerProgress =", sendStart);
assert.ok(sendStart >= 0 && sendEnd > sendStart, "Space_V server save helper not found");
const sendSource = progressSource.slice(sendStart, sendEnd);
assert.match(sendSource, /response=compact-v1/);
assert.match(sendSource, /space-v-progress-compact-v1/);
assert.match(sendSource, /\.\.\.body/);
assert.match(sendSource, /\.\.\.payload\.progress/);
assert.match(sendSource, /\.\.\.\(body\.state/);
assert.match(sendSource, /\.\.\.\(payload\.progress\.state/);

const completionStart = vocabLoaderSource.indexOf("const completeVocabularyMission =");
const completionEnd = vocabLoaderSource.indexOf("const startNextVocabProbe =", completionStart);
assert.ok(completionStart >= 0 && completionEnd > completionStart, "Space_V completion flow not found");
const completionSource = vocabLoaderSource.slice(completionStart, completionEnd);
assert.match(completionSource, /completeState\.syncOperationId = createVocabProgressOperationId\(\)/);
assert.match(completionSource, /pendingServerSync: true/);
assert.ok(
  completionSource.indexOf("persistVocabCompletionLocally(completeRecord)") < completionSource.indexOf("await sendVocabServerProgress(completeRecord"),
  "local completion must patch both boards before waiting for Server 2",
);

const localCompletionStart = vocabSyncSource.indexOf("const persistVocabCompletionLocally =");
const localCompletionEnd = vocabSyncSource.indexOf("const saveVocabProgressNow =", localCompletionStart);
assert.ok(localCompletionStart >= 0 && localCompletionEnd > localCompletionStart, "local Space_V completion helper not found");
const localCompletionSource = vocabSyncSource.slice(localCompletionStart, localCompletionEnd);
assert.match(localCompletionSource, /writeSpaceWJson\(currentVocabProgressCache\.progressKey, source\)/);
assert.match(localCompletionSource, /setLessonProgressOverride\(progressPaths, progressOverride, 300000, \{ force: true \}\)/);
assert.match(localCompletionSource, /rememberLessonVaultProgressPin/);
assert.match(localCompletionSource, /clearLessonProgressDisplayCaches\(progressPaths, "Space_V"\)/);
const completionEffects = {};
const localCompletionContext = {
  isVocabCompletionRecord: () => true,
  currentVocabProgressCache: { progressKey: "progress-key", savedProgress: null },
  vocabProgressSemanticSignature: () => "complete-signature",
  vocabProgressLastSemanticSignature: "",
  writeSpaceWJson: (key, value) => { completionEffects.write = { key, value }; },
  vocabProgressOverrideFromRecord: () => ({ space: "Space_V", done: 1, total: 1, percent: 100, completed: true }),
  currentVocabProgressPaths: () => ["common/demo.Space_V"],
  setLessonProgressOverride: (paths, progress, ttl, options) => { completionEffects.override = { paths, progress, ttl, options }; },
  rememberLessonVaultProgressPin: () => { completionEffects.pinned = true; },
  pinVisibleLessonVaultProgressRing: () => { completionEffects.ring = true; },
  clearLessonProgressDisplayCaches: () => { completionEffects.cleared = true; },
  updateVocabProgressButtons: () => { completionEffects.buttons = true; },
  currentLessonStudyPath: () => "",
  currentLessonSource: {},
};
vm.createContext(localCompletionContext);
vm.runInContext(`${localCompletionSource}\nthis.persistCompletion = persistVocabCompletionLocally;`, localCompletionContext);
const localCompleteRecord = { complete: true, pendingServerSync: true, state: { complete: true } };
assert.equal(localCompletionContext.persistCompletion(localCompleteRecord), localCompleteRecord);
assert.equal(localCompletionContext.currentVocabProgressCache.savedProgress, localCompleteRecord);
assert.equal(completionEffects.write.key, "progress-key");
assert.equal(completionEffects.override.options.force, true);
assert.equal(completionEffects.override.progress.percent, 100);
assert.equal(completionEffects.pinned, true);
assert.equal(completionEffects.cleared, true);

const flushStart = vocabSyncSource.indexOf("window.__ftFlushSpaceVProgressBeforeBack =");
const flushEnd = vocabSyncSource.indexOf("window.__ftPeekSpaceVProgressBeforeBack =", flushStart);
const flushSource = vocabSyncSource.slice(flushStart, flushEnd);
assert.doesNotMatch(flushSource, /payload && payload\.progress/);
assert.match(flushSource, /clean\(mergedRecord\.identity\) === clean\(record\.identity\)/);
assert.match(flushSource, /return \{ ok: true, progress \}/);

const returnStart = returnSource.indexOf("const returnToServerFileSelection =");
const returnEnd = returnSource.indexOf("const syncMobileViewportHeight =", returnStart);
const returnFlowSource = returnSource.slice(returnStart, returnEnd);
assert.match(returnFlowSource, /vocabModeActive && currentVocabProgressCache\.savedProgress/);

const startNewStart = progressSource.indexOf("const startPreparedLessonNew =");
const startNewEnd = progressSource.indexOf("const loadServerDataFile =", startNewStart);
const startNewSource = progressSource.slice(startNewStart, startNewEnd);
assert.match(startNewSource, /forceNewRun: Boolean\(pendingVocabularyPayload\)/);

const taskPatchStart = taskSource.indexOf("const patchLessonTaskPanelProgress =");
const taskPatchEnd = taskSource.indexOf("const loadLessonTasks =", taskPatchStart);
assert.ok(taskPatchStart >= 0 && taskPatchEnd > taskPatchStart, "Space Task progress patch not found");
const taskPatchSource = taskSource.slice(taskPatchStart, taskPatchEnd);
assert.match(taskPatchSource, /currentTaskPayload = applyLessonVaultProgressSnapshotToPayload/);
assert.match(taskPatchSource, /lessonTaskPanelCache\.forEach/);
assert.match(taskPatchSource, /rememberLessonTaskPanelCache/);
assert.match(taskPatchSource, /renderLessonTaskPanel\(currentTaskPayload\)/);
assert.match(taskPatchSource, /window\.__ftPatchLessonTaskPanelProgress/);
assert.doesNotMatch(taskSource, /serverTaskPanel/, "undefined task panel reference would trigger autosave retry loops");

const chartStart = vaultRenderSource.indexOf("function syncLessonVaultChartFromChip");
const chartEnd = vaultRenderSource.indexOf("function syncSpaceVLessonVaultChartFromChip", chartStart);
const chartSource = vaultRenderSource.slice(chartStart, chartEnd);
assert.match(chartSource, /lessonVaultProgressPinForPaths\(pinPaths\)/);
assert.match(chartSource, /activePinnedProgress \|\| fallbackProgress/);

const displayStart = vaultRenderSource.indexOf("function lessonVaultDisplayProgressForStudy");
const displayEnd = vaultRenderSource.indexOf("function syncLessonVaultChartFromChip", displayStart);
assert.ok(displayStart >= 0 && displayEnd > displayStart, "Lesson Vault display-progress helper not found");
const displaySource = vaultRenderSource.slice(displayStart, displayEnd);
assert.match(displaySource, /const activeRunId = clean\(rawProgress\.runId \|\| rawProgress\.run_id \|\| ""\)/);
assert.match(displaySource, /const staleAfterCompletion = !activeRunId/);
const displayContext = {
  clean: (value) => String(value || "").trim(),
  lessonStudyCompletedRunCount: () => 1,
  parseLessonProgressTimestamp: (value) => Date.parse(value || "") || 0,
  lessonProgressIsActivePartial: (progress) => Boolean(progress && progress.total > 0 && progress.done < progress.total && progress.percent < 100 && progress.activeRun),
  lessonVaultCompletedProgressForStudy: () => ({ done: 10, total: 10, percent: 100, completed: true }),
  lessonVaultStructuralPageTotal: () => 0,
};
vm.createContext(displayContext);
vm.runInContext(`${displaySource}\nthis.displayProgress = lessonVaultDisplayProgressForStudy;`, displayContext);
const identifiedZeroRun = displayContext.displayProgress({
  mine: 1,
  mine_last: "2026-07-19T11:00:00Z",
  progress: { done: 0, total: 10, percent: 0, activeRun: true, runId: "run-new", savedAt: "2026-07-19T10:00:00Z" },
}, { extension: ".Space_V" });
assert.equal(identifiedZeroRun.done, 0, "identified New Study 0/N must beat later lifetime completion metadata");
assert.equal(identifiedZeroRun.previously_completed, true, "lifetime completion remains a separate chip");

const exitStart = eventSource.indexOf("if (vaultButton) {");
const exitEnd = eventSource.indexOf("if (cupButton) {", exitStart);
const exitSource = eventSource.slice(exitStart, exitEnd);
assert.doesNotMatch(exitSource, /refreshLessonVaultItemStudyFromServer/);
assert.doesNotMatch(exitSource, /forceFreshProgress/);
assert.match(exitSource, /returnToServerFileSelection\(\{ vocabProgressRecord, questionProgressRecord \}\)/);
assert.doesNotMatch(exitSource, /await window\.__ftFlushSpaceVProgressBeforeBack/);
assert.match(exitSource, /void window\.__ftFlushSpaceVProgressBeforeBack/);

console.log("space_v_progress_cache_patch=ok new_run=accept stale_same_run=reject vault_cache=patched task_cache=patched dom=rerender");
