"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { handleSpaceCompletion, resolveLessonProgressRepeatState, resolveSpaceRunNavigation } = require("../web/js_parts/00_completion_coordinator.js");

const spaces = ["Space_V", "Space_W", "Space_Q", "Space_P", "Space_L", "Space_S"];

for (const space of spaces) {
  const active = resolveSpaceRunNavigation({
    nodeIndex: 0,
    nodeCount: 4,
    completedRuns: 2,
    state: { runId: `${space}-new`, activeRun: true, currentIndex: 0 },
  }, space);
  assert.equal(active.resumeAvailable, true, `${space} new active run must resume`);
  assert.equal(active.navigationMode, "study", `${space} new active run must use study navigation`);
  assert.equal(active.lifetimeComplete, true, `${space} must retain lifetime completion history`);

  const partial = resolveSpaceRunNavigation({
    nodeIndex: 1,
    nodeCount: 4,
    state: { runId: `${space}-partial`, activeRun: true, currentIndex: 1 },
  }, space);
  assert.equal(partial.resumeAvailable, true, `${space} partial run must resume`);

  const completed = resolveSpaceRunNavigation({
    nodeIndex: 4,
    nodeCount: 4,
    completedRuns: 1,
    complete: true,
    state: { runId: `${space}-done`, activeRun: false, complete: true },
  }, space);
  assert.equal(completed.resumeAvailable, false, `${space} completed run must not resume`);
  assert.equal(completed.navigationMode, "completed", `${space} completed run must show New Study`);

  const newRunId = `${space}-new-${Date.now()}`;
  const newStudy = resolveSpaceRunNavigation({
    nodeIndex: 0,
    nodeCount: 4,
    completedRuns: 2,
    runId: newRunId,
    activeRun: true,
    state: { runId: newRunId, activeRun: true, currentIndex: 0 },
  }, space);
  assert.notEqual(newStudy.runId, `${space}-done`, `${space} New Study must not reuse completed run ID`);
  assert.equal(newStudy.resumeAvailable, true, `${space} New Study must restore navigation`);

  const reloaded = resolveSpaceRunNavigation({
    nodeIndex: 1,
    nodeCount: 4,
    completedRuns: 2,
    runId: newRunId,
    activeRun: true,
    state: { runId: newRunId, activeRun: true, currentIndex: 1 },
  }, space);
  assert.equal(reloaded.runId, newRunId, `${space} reload must retain the new run ID`);
  assert.equal(reloaded.resumeAvailable, true, `${space} reload must remain resumable`);

  const completedAgain = resolveSpaceRunNavigation({
    nodeIndex: 4,
    nodeCount: 4,
    completedRuns: 3,
    runId: newRunId,
    complete: true,
    state: { runId: newRunId, activeRun: false, complete: true },
  }, space);
  assert.equal(completedAgain.resumeAvailable, false, `${space} completed relearn run must stop resuming`);
}

const vocabCompleted = resolveSpaceRunNavigation({
  nodeCount: 2,
  state: { learned: ["one", "two"], runId: "v-done" },
}, "Space_V");
assert.equal(vocabCompleted.resumeAvailable, false);

const questionCompleted = resolveSpaceRunNavigation({
  state: { questionDone: 6, questionTotal: 6, runId: "q-done" },
}, "Space_Q");
assert.equal(questionCompleted.resumeAvailable, false);

for (const space of ["Space_P", "Space_L", "Space_S"]) {
  const completed = resolveSpaceRunNavigation({
    state: { completedSegments: 8, totalSegments: 8, runId: `${space}-done` },
  }, space);
  assert.equal(completed.resumeAvailable, false, `${space} completed segments must not resume`);
}

for (const [space, boardType] of [
  ["Space_W", "space_w"],
  ["Space_Q", "space_q"],
  ["Space_P", "space_p"],
  ["Space_L", "space_l"],
  ["Space_S", "space_s"],
]) {
  let opened = 0;
  const result = handleSpaceCompletion({
    completion_confirmed: true,
    space_leaderboard: { type: boardType, recorded: false, duplicate: true },
  }, { fallbackType: space }, {
    openTopLeaderboard: () => { opened += 1; },
  });
  assert.equal(result.shouldOpenTop, true, `${space} duplicate completion must still open Top`);
  assert.equal(opened, 1, `${space} Top must open exactly once`);
}

let boardPayloadOnlyOpened = 0;
const boardPayloadOnly = handleSpaceCompletion({
  database_event_committed: true,
  space_leaderboard: { type: "space_w", points: 2 },
}, { sourcePath: "common/test.Space_W", fallbackType: "space_v" }, {
  openTopLeaderboard: () => { boardPayloadOnlyOpened += 1; },
});
assert.equal(boardPayloadOnly.shouldOpenTop, true, "explicit Space_W board payload must open Top");
assert.equal(boardPayloadOnlyOpened, 1, "explicit Space_W board payload opens Top once");

let canonicalDuplicateOpened = 0;
const canonicalDuplicate = handleSpaceCompletion({
  completion_confirmed: true,
  leaderboard_type: "space_w",
  recorded: false,
  duplicate: true,
}, { fallbackType: "space_v" }, {
  openTopLeaderboard: () => { canonicalDuplicateOpened += 1; },
});
assert.equal(canonicalDuplicate.boardType, "space_w", "server leaderboard_type owns Top mapping");
assert.equal(canonicalDuplicate.shouldOpenTop, true, "confirmed canonical duplicate still opens Top");
assert.equal(canonicalDuplicateOpened, 1, "canonical duplicate opens Writing Top exactly once");

assert.equal(resolveLessonProgressRepeatState({ completedRuns: 1, isCompleteDisplay: true }), false, "first completion stays green");
assert.equal(resolveLessonProgressRepeatState({ completedRuns: 1, isCompleteDisplay: false, activeRun: true, canShowPartial: true }), true, "unfinished New Study is orange");
assert.equal(resolveLessonProgressRepeatState({ completedRuns: 2, isCompleteDisplay: true }), true, "second completion is orange");

const pdfSource = fs.readFileSync(path.join(__dirname, "../web/js_parts/20_pdf_page_progress.js"), "utf8");
assert.equal((pdfSource.match(/const displayPath = normalizeServerPathValue\(entry\.display_path/g) || []).length, 2, "PDF/Picture must retain display path for link focus");
assert.ok(pdfSource.includes("path: displayPath"), "PDF/Picture source and last-file rows must retain link display path");
assert.ok(pdfSource.includes('file: displayPath'), "PDF/Picture routes must retain link display path");
const progressCss = fs.readFileSync(path.join(__dirname, "../web/css_parts/06_question_guidance_motion.css"), "utf8");
assert.ok(progressCss.includes(".ft-vault-progress.is-progress-repeat.is-progress-complete .ft-lesson-progress-track"), "repeat completion must override the green chart");
assert.ok(progressCss.includes(".ft-vault-progress.is-progress-repeat.is-progress-complete .ft-lesson-progress-track-value"), "repeat completion center percent must use the same orange palette");

console.log("space_run_navigation=ok spaces=V/W/Q/P/L/S cases=A/B/C/D/E top_duplicate_once=true");
