"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const syncPath = path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js");
const gatePath = path.join(__dirname, "..", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js");
const openPath = path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js");
const syncSource = fs.readFileSync(syncPath, "utf8");
const gateSource = fs.readFileSync(gatePath, "utf8");
const openSource = fs.readFileSync(openPath, "utf8");

const normalizeStart = syncSource.indexOf("const normalizeQuestionProgressRecord = (record = null) => {");
const normalizeEnd = syncSource.indexOf("const questionSavedSummary =", normalizeStart);
assert.ok(normalizeStart >= 0 && normalizeEnd > normalizeStart, "Space_Q progress normalizer not found");
const normalizeContext = { clean: (value) => String(value || "").trim() };
vm.createContext(normalizeContext);
vm.runInContext(`${syncSource.slice(normalizeStart, normalizeEnd)}\nglobalThis.normalize = normalizeQuestionProgressRecord;`, normalizeContext);
const partial = normalizeContext.normalize({
  identity: "ftg-lesson-000010896",
  activeRun: true,
  runId: "space-q-active-run",
  nodeIndex: 2,
  nodeCount: 8,
  state: { currentIndex: 2, questionIndex: 1, activeRun: true },
});
assert.strictEqual(partial.activeRun, true);
assert.strictEqual(partial.runId, "space-q-active-run");
assert.strictEqual(partial.state.runId, "space-q-active-run", "Continue must preserve the active run ID inside the resume state");
assert.strictEqual(partial.complete, false);
assert.strictEqual(partial.nodeIndex, 2);

const identityStart = syncSource.indexOf("const questionProgressIdentityFor =");
const identityEnd = syncSource.indexOf("const normalizeQuestionProgressRecord =", identityStart);
assert.ok(identityStart >= 0 && identityEnd > identityStart, "Space_Q identity resolver not found");
const identityContext = {
  clean: (value) => String(value || "").trim(),
  currentLessonSource: { lesson_id: "ftg-lesson-authoritative" },
  stableLessonIdFor: () => "ftg-lesson-embedded-stale",
  legacyQuestionProgressIdentityFor: () => "legacy",
};
vm.createContext(identityContext);
vm.runInContext(`${syncSource.slice(identityStart, identityEnd)}\nglobalThis.resolveIdentity = questionProgressIdentityFor;`, identityContext);
assert.strictEqual(identityContext.resolveIdentity({}, []), "ftg-lesson-authoritative", "Space_Q must use the opened entry's canonical lesson ID");

const gateGuard = gateSource.slice(
  gateSource.indexOf("const beginLessonEntryGateTransition ="),
  gateSource.indexOf("const finishLessonEntryGateTransition ="),
);
assert.doesNotMatch(gateGuard, /serverBrowser\.hidden/, "Space Task opens must not bypass Gate 1 when Lesson Vault is hidden");

const loadStart = openSource.indexOf("const loadServerLessonFile = async (entry) => {");
const fileFetch = openSource.indexOf("fetchServerText(`/server-data/file", loadStart);
const progressFetch = openSource.indexOf("progressPromise = fetchServerProgressForEntry", loadStart);
assert.ok(loadStart >= 0 && progressFetch > loadStart && fileFetch > progressFetch, "Space_Q progress must start before lesson file download/decode");

console.log("Space_Q Gate runtime regression checks passed.");
