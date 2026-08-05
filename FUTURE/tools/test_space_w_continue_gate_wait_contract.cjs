const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const policyStart = source.indexOf("const lessonEntryChoiceNeedsVocabPreflight =");
const policyEnd = source.indexOf("const activateLessonEntryGateChoice =", policyStart);
assert.ok(policyStart >= 0 && policyEnd > policyStart, "entry choice preflight policy not found");

const context = {
  shouldRunSpaceWVocabPreflight: () => true,
  loadReviewButton: { id: "continue" },
  loadReviewTrainButton: { id: "train" },
  loadStartButton: { id: "new" },
  pendingLessonNodes: [{}],
  pendingQuestionPayload: null,
  pendingParagraphPayload: null,
};
vm.createContext(context);
vm.runInContext(`${source.slice(policyStart, policyEnd)}\nthis.policy = lessonEntryChoiceNeedsVocabPreflight;`, context);

assert.equal(context.policy(context.loadReviewButton, { nodes: [{}] }), true, "Space_W Continue must preserve vocabulary preflight");
assert.equal(context.policy(context.loadReviewTrainButton, { nodes: [{}] }), false, "Review Train must not wait for an unstarted vocab preflight");
assert.equal(context.policy(context.loadStartButton, { nodes: [{}] }), true, "New Study still owns the vocabulary preflight route");
assert.match(source, /for \(let attempt = 0; attempt < 240 && !state\.vocabPreflightResolved; attempt \+= 1\) await delay\(50\)/);
assert.match(source, /\[FTG\]\[EntryChoice\]/);
assert.match(source, /preflight-policy/);
assert.match(source, /runtime-ready/);

const loadSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const missionSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
const serverOpenSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
assert.match(serverOpenSource, /source: "lesson-click-prefetch"/);
assert.match(serverOpenSource, /vocabScanPromise = fetchServerJson\("\/vocab\/scan-space-w\?response=compact-v1"/);
assert.match(loadSource, /resumeSpaceWSaved: true/);
assert.match(loadSource, /vocabScanPromise: currentSpaceWCache\.vocabScanPromise/);
assert.match(missionSource, /source: prefetchedScan \? "continue-prefetch" : "choice-request"/);
assert.match(missionSource, /continueWaitMs/);
assert.match(missionSource, /startSavedSpaceWProgress\(\{ \.\.\.\(resumeOptions \|\| \{\}\), allowDuringVocabBuild: true \}\)/);

console.log("space_w_continue_gate_wait_contract=ok click_prefetch=true continue_preflight=true resume_saved=true duplicate_scan=false trace=true");
