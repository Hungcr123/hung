const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const syncSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const vaultSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const exitSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const progressSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");
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

const vaultStart = vaultSource.indexOf("function lessonVaultDisplayProgressForStudy");
const vaultEnd = vaultSource.indexOf("// Added 2026-06-30", vaultStart);
const vaultContext = {
  clean: (value) => String(value || "").trim(),
  lessonStudyCompletedRunCount: () => 0,
  lessonProgressIsActivePartial: (row) => Boolean(row && row.total > 0 && row.done < row.total && (row.activeRun || row.done > 0)),
  parseLessonProgressTimestamp: () => 0,
  lessonVaultCompletedProgressForStudy: () => null,
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
assert.match(vaultSource, /const entrySpaceQTotal =/);
assert.match(vaultSource, /node_total: entrySpaceQTotal/);

const exitStart = exitSource.indexOf("const returnToServerFileSelection =");
const savePosition = exitSource.indexOf("questionModeActive ? saveQuestionProgressNow()", exitStart);
const resetPosition = exitSource.indexOf("resetQuestionMode();", exitStart);
assert.ok(savePosition > exitStart && resetPosition > savePosition, "Exit must save Space_Q before clearing runtime state");
const signatureStart = progressSource.indexOf("const questionProgressSemanticSignature =");
const signatureEnd = progressSource.indexOf("const canSaveQuestionProgress =", signatureStart);
const signatureContext = { clean: (value) => String(value || "").trim() };
vm.createContext(signatureContext);
vm.runInContext(`${progressSource.slice(signatureStart, signatureEnd)}\nthis.signature = questionProgressSemanticSignature;`, signatureContext);
const semanticBase = { identity: "q", runId: "run", questionDone: 0, questionTotal: 48, totalNodes: 8, activeRun: true };
assert.equal(signatureContext.signature({ ...semanticBase, feedback: "loading", savedAt: "a" }), signatureContext.signature({ ...semanticBase, feedback: "ready", savedAt: "b" }));
assert.notEqual(signatureContext.signature(semanticBase), signatureContext.signature({ ...semanticBase, questionIndex: 1 }));
assert.match(progressSource, /semanticSignature === questionProgressLastSemanticSignature/);
console.log("space_q_exit_progress=ok active_zero=0/20 run_id=kept guidance_identity=recursive exit_save_before_reset=true");
