const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const readPart = (name) => fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", name), "utf8");
const exitSource = readPart("17_vocab_to_pdf_bootstrap.js");
const syncSource = readPart("13_translation_vocab_sync.js");
const spaceWSyncSource = readPart("14_vocab_sync_tasks.js");
const eventSource = readPart("21_progress_bootstrap_events.js");

const returnStart = exitSource.indexOf("const returnToServerFileSelection =");
const returnEnd = exitSource.indexOf("const setServerBrowserLoading =", returnStart);
assert.ok(returnStart >= 0 && returnEnd > returnStart, "shared Space Exit flow not found");
const returnFlow = exitSource.slice(returnStart, returnEnd);

const resetW = returnFlow.indexOf("resetSpaceWCache();");
const resetQ = returnFlow.indexOf("resetQuestionMode();");
const resetParagraph = returnFlow.indexOf("resetParagraphMode();");
assert.ok(returnFlow.indexOf("saveSpaceWProgressNow()") < resetW, "Space_W Exit must save locally before cache reset");
assert.ok(returnFlow.indexOf("questionModeActive ? saveQuestionProgressNow()") < resetQ, "Space_Q Exit must save locally before runtime reset");
assert.ok(returnFlow.indexOf("paragraphModeActive ? saveParagraphProgressNow()") < resetParagraph, "Space_P/L/S Exit must save locally before runtime reset");
assert.match(returnFlow, /vocabProgressOverrideForReturn \|\| spaceWProgressOverrideForReturn \|\| questionProgressOverrideForReturn \|\| paragraphProgressOverrideForReturn/);
assert.match(returnFlow, /progress: localProgressOverrideForReturn/);
assert.match(returnFlow, /pinVisibleLessonVaultProgressRing\(returnProgressPaths, localProgressOverrideForReturn/);

const vaultStart = eventSource.indexOf("if (vaultButton) {");
const vaultEnd = eventSource.indexOf("if (cupButton) {", vaultStart);
const vaultFlow = eventSource.slice(vaultStart, vaultEnd);
assert.doesNotMatch(vaultFlow, /await .*Progress/);
assert.match(vaultFlow, /returnToServerFileSelection\(\{ vocabProgressRecord \}\)/);

const qMergeStart = syncSource.indexOf("const mergeQuestionServerProgressRecord =");
const qMergeEnd = syncSource.indexOf("const refreshQuestionServerProgress =", qMergeStart);
const paragraphMergeStart = syncSource.indexOf("const mergeParagraphServerProgressRecord =");
const paragraphMergeEnd = syncSource.indexOf("const refreshParagraphServerProgress =", paragraphMergeStart);
const wMergeStart = spaceWSyncSource.indexOf("const mergeSpaceWServerProgressRecord =");
const wMergeEnd = spaceWSyncSource.indexOf("const refreshSpaceWServerProgress =", wMergeStart);
assert.match(syncSource.slice(qMergeStart, qMergeEnd), /\.\.\.localRecord, \.\.\.record, state: \{ \.\.\.localRecord\.state \}/);
assert.match(syncSource.slice(paragraphMergeStart, paragraphMergeEnd), /\.\.\.localRecord, \.\.\.record, state: \{ \.\.\.localRecord\.state \}/);
assert.match(spaceWSyncSource.slice(wMergeStart, wMergeEnd), /\.\.\.localRecord, \.\.\.record, state: \{ \.\.\.localRecord\.state \}/);
assert.match(syncSource, /"Space_P", "Space_L", "Space_S"/);

const runCompactMerge = (source, functionName, context, compactRecord) => {
  vm.createContext(context);
  vm.runInContext(`${source}\nthis.mergeCompact = ${functionName};`, context);
  return context.mergeCompact(compactRecord);
};

const wContext = {
  clean: (value) => String(value || "").trim(),
  currentSpaceWCache: {
    identity: "w-one-node",
    progressKey: "w-key",
    savedProgress: { identity: "w-one-node", pendingServerSync: true, state: { nodeCount: 1, progressDone: 2, progressTotal: 2 } },
  },
  shouldKeepPendingLocalProgress: () => false,
  scheduleProgressOutboxDrain: () => {},
  writeSpaceWJson: () => true,
  spaceWProgressOverrideFromRecord: () => null,
  updateSpaceWReviewButton: () => {},
};
const mergedW = runCompactMerge(spaceWSyncSource.slice(wMergeStart, wMergeEnd), "mergeSpaceWServerProgressRecord", wContext, {
  identity: "w-one-node", complete: true, pendingServerSync: false,
});
assert.equal(mergedW.state.nodeCount, 1);
assert.equal(mergedW.state.progressTotal, 2);

const qContext = {
  currentQuestionProgressCache: {
    identity: "q-one-node",
    progressKey: "q-key",
    savedProgress: { identity: "q-one-node", pendingServerSync: true, state: { nodeCount: 1, questionDone: 1, questionTotal: 1 } },
  },
  normalizeQuestionProgressRecord: (record) => record,
  shouldKeepPendingLocalProgress: () => false,
  scheduleProgressOutboxDrain: () => {},
  writeSpaceWJson: () => true,
  updateQuestionProgressButtons: () => {},
};
const mergedQ = runCompactMerge(syncSource.slice(qMergeStart, qMergeEnd), "mergeQuestionServerProgressRecord", qContext, {
  identity: "q-one-node", complete: true, pendingServerSync: false,
});
assert.equal(mergedQ.state.nodeCount, 1);
assert.equal(mergedQ.state.questionTotal, 1);

for (const spaceMode of ["space_p", "space_l", "space_s"]) {
  const pContext = {
    currentParagraphProgressCache: {
      identity: `${spaceMode}-one-node`,
      progressKey: `${spaceMode}-key`,
      savedProgress: { identity: `${spaceMode}-one-node`, pendingServerSync: true, state: { spaceMode, totalNodes: 1, totalSegments: 1 } },
    },
    normalizeParagraphProgressRecord: (record) => record,
    shouldKeepPendingLocalProgress: () => false,
    scheduleProgressOutboxDrain: () => {},
    writeSpaceWJson: () => true,
    updateParagraphProgressButtons: () => {},
  };
  const merged = runCompactMerge(syncSource.slice(paragraphMergeStart, paragraphMergeEnd), "mergeParagraphServerProgressRecord", pContext, {
    identity: `${spaceMode}-one-node`, complete: true, pendingServerSync: false,
  });
  assert.equal(merged.state.spaceMode, spaceMode);
  assert.equal(merged.state.totalNodes, 1);
  assert.equal(merged.state.totalSegments, 1);
}

console.log("space_exit_progress_all=ok W,Q,P,L,S=local-first one_node_compact=merged exit=no-await");
