"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const sourcePath = path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js");
const source = fs.readFileSync(sourcePath, "utf8");
const start = source.indexOf("const updateQuestionProgressButtons = () => {");
const end = source.indexOf("const resetQuestionProgressCache = () => {", start);
assert.ok(start >= 0 && end > start, "Space_Q progress button function not found");

const prepareStart = source.indexOf("if (isQuestionPayload(payload)) {");
const pendingPosition = source.indexOf("pendingQuestionPayload = normalized;", prepareStart);
const updatePosition = source.indexOf("updateQuestionProgressButtons();", pendingPosition);
assert.ok(pendingPosition >= 0 && updatePosition > pendingPosition, "Space_Q must expose Gate actions immediately after preparing its payload");

const context = {
  pendingQuestionPayload: { nodes: [{}] },
  currentQuestionProgressCache: { savedProgress: null },
  loadStartButton: { hidden: true, disabled: true, textContent: "" },
  loadReviewButton: { hidden: true, disabled: true, textContent: "" },
  loadReviewTrainButton: { hidden: false, disabled: false },
  resolveSpaceRunNavigation: (saved) => ({ resumeAvailable: Boolean(saved && saved.resumeAvailable) }),
  navigationForLoadedRecord: () => ({ lifetimeComplete: context.lifetimeComplete }),
  lifetimeComplete: false,
  window: { __ftSyncLessonEntryGateActions: () => { context.syncCount += 1; } },
  syncCount: 0,
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nglobalThis.testUpdate = updateQuestionProgressButtons;`, context);

context.testUpdate();
assert.strictEqual(context.loadStartButton.hidden, false, "New Run must remain available while Space_Q server progress is unresolved");
assert.strictEqual(context.loadStartButton.disabled, false);
assert.strictEqual(context.loadStartButton.textContent, "Open New Run");
assert.strictEqual(context.loadReviewButton.hidden, true, "Continue must stay hidden without a resumable checkpoint");

context.currentQuestionProgressCache.savedProgress = { resumeAvailable: true };
context.testUpdate();
assert.strictEqual(context.loadStartButton.hidden, false);
assert.strictEqual(context.loadStartButton.textContent, "New Study");
assert.strictEqual(context.loadReviewButton.hidden, false, "Continue must appear for a resumable checkpoint");
assert.strictEqual(context.loadReviewButton.disabled, false);

context.currentQuestionProgressCache.savedProgress = null;
context.lifetimeComplete = true;
context.testUpdate();
assert.strictEqual(context.loadStartButton.hidden, false, "Completed history must still allow a new run");
assert.strictEqual(context.loadStartButton.textContent, "New Study");
assert.strictEqual(context.loadReviewButton.hidden, true);
assert.ok(context.syncCount >= 3, "Gate 1 actions were not synchronized after Space_Q progress changes");

console.log("Space_Q Gate action regression checks passed.");
