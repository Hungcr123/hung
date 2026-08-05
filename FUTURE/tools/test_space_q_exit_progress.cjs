const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const syncSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const vaultSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const exitSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const progressSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");
const taskSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
const start = syncSource.indexOf("const questionProgressOverrideFromRecord =");
const end = syncSource.indexOf("// Added 2026-07-15: lets Space_W Back", start);
assert.ok(start >= 0 && end > start, "Space_Q progress override not found");

const context = { clean: (value) => String(value || "").trim(), questionNodes: [] };
vm.createContext(context);
vm.runInContext(`${syncSource.slice(start, end)}\nthis.toProgress = questionProgressOverrideFromRecord;`, context);

const progress = context.toProgress({
  activeRun: true,
  runId: "space-q-run-2",
  savedAt: "2026-07-20T00:00:00Z",
  nodeCount: 2,
  state: {
    activeRun: true,
    runId: "space-q-run-2",
    questionDone: 0,
    questionTotal: 20,
    completedNodes: 0,
    totalNodes: 2,
  },
});
assert.deepEqual([progress.done, progress.total, progress.percent, progress.text], [0, 20, 0, "0/20"]);
assert.equal(progress.activeRun, true);
assert.equal(progress.in_progress, true);
assert.equal(progress.runId, "space-q-run-2");
assert.equal(progress.savedAt, "2026-07-20T00:00:00Z");
assert.match(syncSource, /guidance: compactQuestionGuidanceForHash/);

const labelStart = syncSource.indexOf("const lessonCurrentRunProgressLabel =");
const labelEnd = syncSource.indexOf("const createServerChip =", labelStart);
const labelContext = { clean: (value) => String(value || "").trim(), lessonStudyCompletedRunCount: () => 0 };
vm.createContext(labelContext);
vm.runInContext(`${syncSource.slice(labelStart, labelEnd)}\nthis.progressLabel = lessonCurrentRunProgressLabel; this.nodeLabel = lessonCurrentRunNodeChipLabel; this.spaceQTotal = spaceQStructuralProgressTotal;`, labelContext);
assert.equal(labelContext.progressLabel({}, { space: "Space_Q", done: 2, total: 48, text: "2/48" }), "Question 2/48");
assert.equal(labelContext.nodeLabel({ space: "Space_Q", done: 2, total: 48, text: "2/48" }), "Question 2/48");
assert.equal(labelContext.spaceQTotal({ nodes: 8, questions: 48, direct_questions: 40, total_nodes: 0 }, {}), 48, "already-total question metadata must not become 56");
assert.equal(labelContext.spaceQTotal({ nodes: 8, questions: 40, direct_questions: 0, total_nodes: 0 }, {}), 48, "recursive question metadata must include root topics once");

const snapshotUpdateStart = syncSource.indexOf("const updateLessonVaultProgressSnapshotForPaths =");
const snapshotUpdateEnd = syncSource.indexOf("const lessonVaultProgressSnapshotForPaths =", snapshotUpdateStart);
const snapshotApplyStart = syncSource.indexOf("const applyLessonVaultProgressSnapshotToPayload =");
const snapshotApplyEnd = syncSource.indexOf("const pruneLessonProgressOverrides =", snapshotApplyStart);
const snapshotContext = {
  normalizeServerPathValue: (value) => String(value || "").trim(),
  normalizeTaskPath: (value) => String(value || "").trim().toLowerCase(),
  clean: (value) => String(value || "").trim(),
};
vm.createContext(snapshotContext);
vm.runInContext(`
  const lessonVaultProgressSnapshot = new Map();
  let lessonVaultProgressSnapshotGeneration = 7;
  const lessonProgressOverrideKey = (path = "") => normalizeTaskPath(normalizeServerPathValue(path || ""));
  let appliedEntries = 0;
  const applyLessonVaultProgressSnapshotToEntry = (entry = {}) => {
    appliedEntries += 1;
    return { ...entry, patched: true };
  };
  const rememberLessonVaultProgressSnapshot = () => 0;
  ${syncSource.slice(snapshotUpdateStart, snapshotUpdateEnd)}
  ${syncSource.slice(snapshotApplyStart, snapshotApplyEnd)}
  const taskPayload = {
    tasks: [{ lesson_id: "ftg-lesson-1" }],
    space_tasks: [{ lesson_id: "ftg-lesson-1" }],
    space_task: { tasks: [{ lesson_id: "ftg-lesson-1" }] },
  };
  Object.defineProperty(taskPayload, "__ftLessonVaultProgressSnapshotGeneration", { value: 7, configurable: true });
  updateLessonVaultProgressSnapshotForPaths(["space:space_q:id:ftg-lesson-1"], { space: "Space_Q", done: 2, total: 48, text: "2/48" });
  const patchedPayload = applyLessonVaultProgressSnapshotToPayload(taskPayload);
  this.snapshotGeneration = lessonVaultProgressSnapshotGeneration;
  this.snapshotProgress = lessonVaultProgressSnapshot.get("space:space_q:id:ftg-lesson-1").progress;
  this.appliedEntries = appliedEntries;
  this.patchedTask = patchedPayload.tasks[0];
  this.patchedSpaceTask = patchedPayload.space_task.tasks[0];
`, snapshotContext);
assert.equal(snapshotContext.snapshotGeneration, 8, "local Exit delta must invalidate generation-marked Space Task payloads");
assert.deepEqual([snapshotContext.snapshotProgress.done, snapshotContext.snapshotProgress.total], [2, 48]);
assert.equal(snapshotContext.appliedEntries, 3, "all Space Task row branches must be reapplied after the local generation advances");
assert.equal(snapshotContext.patchedTask.patched, true);
assert.equal(snapshotContext.patchedSpaceTask.patched, true, "canonical space_task.tasks must not retain stale progress");
assert.match(syncSource, /const rememberLessonVaultProgressEntries =/);

const keepOverrideStart = syncSource.indexOf("const shouldKeepExistingLessonProgressOverride =");
const keepOverrideEnd = syncSource.indexOf("const setLessonProgressOverride =", keepOverrideStart);
const keepOverrideContext = {
  clean: (value) => String(value || "").trim(),
  lessonProgressSnapshotTimestamp: (row) => Date.parse(row && (row.updatedAt || row.savedAt) || "") || 0,
  lessonProgressIsActivePartial: (row) => Boolean(row && row.total > 0 && row.done < row.total && (row.activeRun || row.done > 0)),
};
vm.createContext(keepOverrideContext);
vm.runInContext(`${syncSource.slice(keepOverrideStart, keepOverrideEnd)}\nthis.shouldKeep = shouldKeepExistingLessonProgressOverride;`, keepOverrideContext);
assert.equal(keepOverrideContext.shouldKeep({
  progress: { space: "Space_Q", done: 8, total: 48, text: "8/48", percent: 17, activeRun: true, runId: "run-1", updatedAt: "2026-08-03T04:16:00Z" },
}, {
  space: "Space_Q", done: 0, total: 16, text: "0/16", percent: 0, activeRun: true, runId: "older-run", updatedAt: "2026-08-03T04:15:59Z",
}), true, "stale Space_Q task snapshots must not delete the newer Exit override");
assert.equal(keepOverrideContext.shouldKeep({
  progress: { space: "Space_Q", done: 10, total: 48, text: "10/48", percent: 21, activeRun: true, runId: "run-1", updatedAt: "2026-08-03T04:16:00Z" },
}, {
  space: "Space_Q", done: 9, total: 48, text: "9/48", percent: 19, activeRun: true, runId: "run-1", updatedAt: "2026-08-03T04:16:01Z",
}), true, "same-run Space_Q progress must remain monotonic even when a stale echo has a later server timestamp");
const vaultIngestPosition = vaultSource.indexOf("rememberLessonVaultProgressEntries(payload.entries)");
const vaultApplyPosition = vaultSource.indexOf("applyLessonVaultProgressSnapshotToPayload(payload)", vaultIngestPosition);
assert.ok(vaultIngestPosition >= 0 && vaultApplyPosition > vaultIngestPosition, "Lesson Vault entries must seed shared progress before task/list rendering");
assert.match(vaultSource, /resolvedProgressEntries\.push\(/, "the exact visible Lesson Vault progress must feed the shared task snapshot");

const realSnapshotStart = syncSource.indexOf("const lessonProgressOverrideKey =");
const realSnapshotEnd = syncSource.indexOf("const pruneLessonProgressOverrides =", realSnapshotStart);
const realSnapshotContext = {
  clean: (value) => String(value || "").trim(),
  normalizeServerPathValue: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  normalizeTaskPath: (value) => String(value || "").trim().toLowerCase(),
  futureRouteSpaceForFilePath: () => "space_q",
};
vm.createContext(realSnapshotContext);
vm.runInContext(`
  const lessonProgressOverrides = new Map();
  ${syncSource.slice(realSnapshotStart, realSnapshotEnd)}
  const lesson = {
    lesson_id: "ftg-lesson-000010892",
    path: "common/grammar/probe.Space_Q",
    extension: ".space_q",
  };
  rememberLessonVaultProgressEntries([{
    ...lesson,
    study: { progress: { space: "Space_Q", done: 0, total: 16, text: "0/16", percent: 0, updatedAt: "2026-08-03T05:05:00Z" } },
  }]);
  rememberLessonVaultProgressEntries([{
    ...lesson,
    study: { progress: { space: "Space_Q", done: 12, total: 48, text: "12/48", percent: 25, activeRun: true, runId: "run-visible", updatedAt: "2026-08-03T05:06:15Z" } },
  }]);
  const result = applyLessonVaultProgressSnapshotToPayload({
    space_task: { tasks: [{ ...lesson, study: { progress: { space: "Space_Q", done: 0, total: 48, text: "0/48", percent: 0 } } }] },
  });
  this.visibleTaskProgress = result.space_task.tasks[0].study.progress;
`, realSnapshotContext);
assert.deepEqual(
  JSON.parse(JSON.stringify([realSnapshotContext.visibleTaskProgress.done, realSnapshotContext.visibleTaskProgress.total, realSnapshotContext.visibleTaskProgress.text])),
  [12, 48, "12/48"],
  "the canonical Space Task row must consume the exact progress resolved by the visible Lesson Vault card",
);

const activeOverrideApplyStart = syncSource.indexOf("const applyLessonVaultProgressSnapshotToEntry =");
const activeOverrideApplyEnd = syncSource.indexOf("const applyLessonVaultProgressSnapshotToPayload =", activeOverrideApplyStart);
const activeOverrideApplyContext = {
  clean: (value) => String(value || "").trim(),
  lessonVaultEntryProgressSpace: () => "Space_Q",
  lessonVaultProgressSnapshotForPaths: () => ({
    study: { progress: { space: "Space_Q", done: 0, total: 16, text: "0/16", percent: 0 } },
    progress: { space: "Space_Q", done: 0, total: 16, text: "0/16", percent: 0 },
  }),
  lessonProgressOverrideForPaths: () => ({
    space: "Space_Q", done: 21, total: 48, text: "21/48", percent: 44,
    activeRun: true, runId: "space-q-run-live", updatedAt: "2026-08-03T07:21:20Z",
  }),
  lessonProgressSnapshotTimestamp: () => 0,
  compareLessonProgressSnapshotOrder: () => 0,
};
vm.createContext(activeOverrideApplyContext);
vm.runInContext(`${syncSource.slice(activeOverrideApplyStart, activeOverrideApplyEnd)}\nthis.applyEntry = applyLessonVaultProgressSnapshotToEntry;`, activeOverrideApplyContext);
const protectedExitEntry = activeOverrideApplyContext.applyEntry({
  lesson_id: "ftg-lesson-000010892",
  path: "common/grammar/probe.Space_Q",
  extension: ".space_q",
  study: { progress: { space: "Space_Q", done: 0, total: 16, text: "0/16", percent: 0 } },
});
assert.deepEqual(
  JSON.parse(JSON.stringify([protectedExitEntry.study.progress.done, protectedExitEntry.study.progress.total, protectedExitEntry.study.progress.text])),
  [21, 48, "21/48"],
  "a delayed stale task/list render must consume the active Exit override instead of reverting to New Run",
);

const taskPatchStart = taskSource.indexOf("const patchLessonTaskPanelProgress =");
const taskPatchEnd = taskSource.indexOf("if (typeof window !== \"undefined\")", taskPatchStart);
const staleTask = {
  lesson_id: "ftg-lesson-1",
  path: "common/probe.Space_Q",
  study: { progress: { space: "Space_Q", done: 0, total: 48, text: "0/48", percent: 0 } },
};
const taskPatchContext = {
  clean: (value) => String(value || "").trim(),
  normalizeTaskPath: (value) => String(value || "").trim().toLowerCase(),
  taskLearningPath: (task) => task.effective_path || task.path || "",
  applyLessonVaultProgressSnapshotToPayload: (payload) => payload,
};
vm.createContext(taskPatchContext);
vm.runInContext(`
  let currentTaskPayload = {
    task_owner: "hung",
    tasks: [${JSON.stringify(staleTask)}],
    space_tasks: [${JSON.stringify(staleTask)}],
    space_task: { tasks: [${JSON.stringify(staleTask)}] },
  };
  const lessonTaskPanelCache = new Map([["hung", { payload: currentTaskPayload, at: 0 }]]);
  const rememberLessonTaskPanelCache = () => {};
  const serverTaskOwnerContext = "hung";
  const currentAuthUsername = "hung";
  const serverTaskListNode = { isConnected: true };
  let lessonTaskPanelLastSignature = "stale";
  let renderedPayload = null;
  const renderLessonTaskPanel = (payload) => { renderedPayload = payload; };
  ${taskSource.slice(taskPatchStart, taskPatchEnd)}
  this.patchResult = patchLessonTaskPanelProgress(
    ["space:space_q:id:ftg-lesson-1", "common/probe.Space_Q"],
    { space: "Space_Q", done: 2, total: 48, text: "2/48", percent: 4, activeRun: true, runId: "run-1" },
  );
  this.directTaskRows = [
    currentTaskPayload.tasks[0].study.progress,
    currentTaskPayload.space_tasks[0].study.progress,
    currentTaskPayload.space_task.tasks[0].study.progress,
    renderedPayload.tasks[0].study.progress,
  ];
`, taskPatchContext);
assert.equal(taskPatchContext.patchResult, true);
assert.deepEqual(JSON.parse(JSON.stringify(taskPatchContext.directTaskRows.map((row) => [row.done, row.total, row.text]))), [
  [2, 48, "2/48"],
  [2, 48, "2/48"],
  [2, 48, "2/48"],
  [2, 48, "2/48"],
]);
assert.match(taskSource, /if \(!fresh\) \{\s*return await existingRequest;/, "fresh task reads must not reuse a pre-checkpoint request");
assert.match(taskSource, /ifNoneMatch: !fresh && cachedPayload/, "fresh task reads must bypass stale 304 payload reuse");

const viewerSplitStart = syncSource.indexOf("const lessonProgressResolvedOwner =");
const viewerSplitEnd = syncSource.indexOf("const adminViewerCompletionCount =", viewerSplitStart);
assert.ok(viewerSplitStart >= 0 && viewerSplitEnd > viewerSplitStart, "admin/user progress split not found");
const viewerSplitContext = {
  clean: (value) => String(value || "").trim(),
  normalizeServerPathValue: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  lessonProgressOverrideForPaths: () => null,
  lessonVaultTaskOwnerForPath: (pathValue, explicitOwner) => {
    const top = String(pathValue || "").split("/").filter(Boolean)[0] || "";
    return top && top.toLowerCase() !== "common" ? top : explicitOwner;
  },
  authUsernameMatches: (left, right) => String(left || "").toLowerCase() === String(right || "").toLowerCase(),
  parseLessonProgressTimestamp: (value) => Date.parse(value || "") || 0,
  currentAuthIsAdmin: true,
  currentAuthUsername: "admin",
};
vm.createContext(viewerSplitContext);
vm.runInContext(`${syncSource.slice(viewerSplitStart, viewerSplitEnd)}\nthis.splitViewer = splitLessonProgressForViewer;`, viewerSplitContext);
const ownAdminSplit = viewerSplitContext.splitViewer({
  mine: 0,
  admin_mine: 1,
  admin_mine_last: "2026-08-03T00:00:00Z",
  admin_progress: { space: "Space_Q", done: 2, total: 48, text: "2/48", percent: 4, activeRun: true },
}, ["admin/Grammar/probe.Space_Q"], "other-stale-owner");
assert.equal(ownAdminSplit.adminProgress, null, "admin's own folder must not render a second admin chart");
assert.deepEqual([ownAdminSplit.study.progress.done, ownAdminSplit.study.progress.total, ownAdminSplit.study.mine], [2, 48, 1]);
const otherLearnerSplit = viewerSplitContext.splitViewer({
  progress: { space: "Space_Q", done: 3, total: 48, text: "3/48", percent: 6, activeRun: true },
  admin_progress: { space: "Space_Q", done: 7, total: 48, text: "7/48", percent: 15, activeRun: true },
}, ["learner/Grammar/probe.Space_Q"], "admin");
assert.deepEqual([otherLearnerSplit.study.progress.done, otherLearnerSplit.adminProgress.done], [3, 7], "other-user learner/admin charts must remain separate");

const vaultStart = vaultSource.indexOf("function lessonVaultDisplayProgressForStudy");
const vaultEnd = vaultSource.indexOf("// Added 2026-06-30", vaultStart);
const vaultContext = {
  clean: (value) => String(value || "").trim(),
  lessonStudyCompletedRunCount: () => 0,
  lessonProgressIsActivePartial: (row) => Boolean(row && row.total > 0 && row.done < row.total && (row.activeRun || row.done > 0)),
  parseLessonProgressTimestamp: () => 0,
  lessonVaultCompletedProgressForStudy: () => null,
  lessonVaultStructuralPageTotal: () => 0,
  spaceQStructuralProgressTotal: labelContext.spaceQTotal,
};
vm.createContext(vaultContext);
vm.runInContext(`${vaultSource.slice(vaultStart, vaultEnd)}\nthis.toVaultProgress = lessonVaultDisplayProgressForStudy;`, vaultContext);
const migrated = vaultContext.toVaultProgress(
  { nodes: 2, questions: 18, total_nodes: 20, progress: { space: "Space_Q", done: 0, total: 3, text: "0/3", activeRun: true, runId: "space-q-run-2" } },
  { extension: ".space_q", nodes: 2, questions: 18, total_nodes: 20 },
  null,
);
assert.deepEqual([migrated.done, migrated.total, migrated.text], [0, 20, "0/20"]);
const migratedLegacy = vaultContext.toVaultProgress(
  { nodes: 2, questions: 18, total_nodes: 20, progress: { space: "Space_Q", done: 0, total: 3, text: "0/3", activeRun: true } },
  { extension: ".space_q", nodes: 2, questions: 18, total_nodes: 20 },
  null,
);
assert.deepEqual([migratedLegacy.done, migratedLegacy.total, migratedLegacy.text], [0, 20, "0/20"]);
const correctedDoubleCount = vaultContext.toVaultProgress(
  { nodes: 8, questions: 48, direct_questions: 40, progress: { space: "Space_Q", done: 2, total: 56, text: "2/56", activeRun: true, runId: "space-q-run-2" } },
  { extension: ".space_q", nodes: 8, questions: 40, direct_questions: 40, total_nodes: 48 },
  null,
);
assert.deepEqual([correctedDoubleCount.done, correctedDoubleCount.total, correctedDoubleCount.text], [2, 48, "2/48"]);
assert.match(vaultSource, /const entrySpaceQTotal =/);
assert.match(vaultSource, /node_total: entrySpaceQTotal/);

const exitStart = exitSource.indexOf("const returnToServerFileSelection =");
const savePosition = exitSource.indexOf("const capturedQuestionProgressRecord =", exitStart);
const resetPosition = exitSource.indexOf("resetQuestionMode();", exitStart);
assert.ok(savePosition > exitStart && resetPosition > savePosition, "Exit must save Space_Q before clearing runtime state");
assert.match(exitSource.slice(exitStart, resetPosition), /currentQuestionProgressPaths\(questionProgressRecordForReturn\)/, "Exit must patch Space_Q by canonical lesson ID and path aliases");
assert.match(exitSource.slice(exitStart, resetPosition), /questionProgressOverrideForReturn, 120000, \{ force: true \}/, "Exit must pin the Space_Q DOM override instead of accepting stale cached progress");
assert.match(exitSource.slice(exitStart, resetPosition), /questionSavedRecordForReturn/, "Exit must fall back to the saved Space_Q checkpoint when the mode flag has already cleared");
assert.match(
  exitSource.slice(exitStart, resetPosition),
  /const spaceWProgressRecordForReturn = !capturedQuestionProgressRecord/,
  "a captured Space_Q Exit must not manufacture a stale Space_W checkpoint after the gate clears mode flags",
);
assert.match(
  exitSource.slice(exitStart, resetPosition),
  /const localProgressOverrideForReturn = questionSavedRecordForReturn && questionProgressOverrideForReturn/,
  "the captured Space_Q checkpoint must outrank neutral-runtime Space_W fallback state",
);
assert.match(exitSource.slice(exitStart), /loadLessonTasks\(returnTaskOwner, \{ fresh: true \}\)/, "Partial Space_Q Exit must refresh the canonical task board");
const exitTaskRefreshPosition = exitSource.indexOf("await loadLessonTasks(returnTaskOwner, { fresh: true })", exitStart);
const exitTaskReapplyPosition = exitSource.indexOf("setLessonProgressOverride(returnProgressPaths, localProgressOverrideForReturn", exitTaskRefreshPosition);
assert.ok(
  exitTaskRefreshPosition > exitStart && exitTaskReapplyPosition > exitTaskRefreshPosition,
  "the saved Space_Q checkpoint must be reapplied after a late fresh task response settles",
);
const compactPreloadStart = vaultSource.indexOf("} else if (preloadPayload.preload && preloadPayload.preload.progress_snapshot)");
const compactPreloadEnd = vaultSource.indexOf("loginVaultWarmupStats.progressApplyMs", compactPreloadStart);
assert.ok(compactPreloadStart >= 0 && compactPreloadEnd > compactPreloadStart, "compact-v2 progress hydration branch missing");
const compactPreloadSource = vaultSource.slice(compactPreloadStart, compactPreloadEnd);
assert.match(compactPreloadSource, /rememberLessonVaultProgressSnapshot\(progressSnapshot\)/, "compact-v2 must hydrate Lesson Vault and Space Task, not PDF only");
assert.match(compactPreloadSource, /rememberPdfProgressLoginSnapshot\(progressSnapshot\)/, "compact-v2 must preserve PDF progress hydration");
assert.match(progressSource, /currentQuestionProgressPaths\(record\)/, "Space_Q autosave must patch Lesson Vault and Space Task through the shared canonical path set");
const signatureStart = progressSource.indexOf("const questionProgressSemanticSignature =");
const signatureEnd = progressSource.indexOf("const canSaveQuestionProgress =", signatureStart);
const signatureContext = { clean: (value) => String(value || "").trim() };
vm.createContext(signatureContext);
vm.runInContext(`${progressSource.slice(signatureStart, signatureEnd)}\nthis.signature = questionProgressSemanticSignature;`, signatureContext);
const semanticBase = { identity: "q", runId: "run", questionDone: 0, questionTotal: 48, totalNodes: 8, activeRun: true };
assert.equal(signatureContext.signature({ ...semanticBase, feedback: "loading", savedAt: "a" }), signatureContext.signature({ ...semanticBase, feedback: "ready", savedAt: "b" }));
assert.notEqual(signatureContext.signature(semanticBase), signatureContext.signature({ ...semanticBase, questionIndex: 1 }));
assert.match(progressSource, /semanticSignature === questionProgressLastSemanticSignature/);
console.log("space_q_exit_progress=ok active_zero=0/20 task_direct_patch=2/48 task_generation=advanced label=Question exit_save_before_reset=true");
