const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const syncSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const layoutSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "05_screen_motion_layout.js"), "utf8");
const inputSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "08_speak_question_input.js"), "utf8");

const start = syncSource.indexOf("const paragraphProgressOverrideFromRecord =");
const end = syncSource.indexOf("const createLessonProgressNode =", start);
assert.ok(start >= 0 && end > start, "paragraph override not found");

const context = {
  clean: (value) => String(value || "").trim(),
  paragraphNodes: [],
};
vm.createContext(context);
vm.runInContext(`${syncSource.slice(start, end)}\nthis.toProgress = paragraphProgressOverrideFromRecord;`, context);

for (const [spaceMode, expectedSpace] of [["space_p", "Space_P"], ["space_l", "Space_L"], ["space_s", "Space_S"]]) {
  const progress = context.toProgress({
    runId: `run-${spaceMode}`,
    savedAt: "2026-07-20T00:00:00Z",
    activeRun: true,
    nodeIndex: 0,
    nodeCount: 1,
    state: {
      spaceMode,
      activeRun: true,
      runId: `run-${spaceMode}`,
      completedSegments: 0,
      totalSegments: 12,
      completedTokens: 0,
      totalTokens: 67,
      completedNodes: 0,
      totalNodes: 1,
    },
  });
  assert.deepEqual([progress.space, progress.done, progress.total, progress.percent, progress.text], [expectedSpace, 0, 12, 0, "0/12"]);
  assert.equal(progress.activeRun, true);
  assert.equal(progress.in_progress, true);
  assert.equal(progress.runId, `run-${spaceMode}`);
  assert.equal(progress.savedAt, "2026-07-20T00:00:00Z");

  const summarized = context.toProgress({
    space: expectedSpace,
    label: "Sentences",
    done: 2,
    total: 12,
    percent: 17,
    text: "2/12",
    activeRun: true,
    runId: `summary-${spaceMode}`,
    node_done: 0,
    node_total: 1,
  });
  assert.deepEqual(
    [summarized.space, summarized.done, summarized.total, summarized.text, summarized.runId],
    [expectedSpace, 2, 12, "2/12", `summary-${spaceMode}`],
    "server summary done/total must not collapse to the one root paragraph node",
  );
}

const cacheStart = syncSource.indexOf("const clearLessonProgressDisplayCaches =");
const cacheEnd = syncSource.indexOf("const refreshServerBrowserManifestSignatureIfNeeded =", cacheStart);
const cacheBlock = syncSource.slice(cacheStart, cacheEnd);
assert.doesNotMatch(cacheBlock, /clearLessonTaskPanelCache\s*\(/, "progress delta must not evict the Space Task cache");
assert.match(layoutSource, /let paragraphActiveRunId = "";/);
assert.match(inputSource, /paragraphActiveRunId = clean\(resumeState/);
assert.match(syncSource, /runId: paragraphActiveRunId/);
assert.match(syncSource, /"Space_P", "Space_L", "Space_S"/);

console.log("paragraph_back_progress=ok spaces=P,L,S active_zero=0/12 run_id=kept task_cache=kept");
