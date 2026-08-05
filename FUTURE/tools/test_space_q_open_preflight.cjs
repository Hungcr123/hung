const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"),
  "utf8",
);
const start = source.indexOf("const shouldRunSpaceWVocabPreflight =");
const end = source.indexOf("const runSpaceWVocabPreflight =", start);
assert.ok(start >= 0 && end > start, "vocabulary preflight predicate not found");

const context = {
  authToken: "test-token",
  currentAuthUsername: "hung",
  currentLessonSource: { path: "hung/Ngu phap/Present Simple Practice.Space_Q" },
  normalizeVocabPreflightPath: (value = "") => String(value).replace(/\\/g, "/"),
  isQuestionPayload: (payload) => payload && payload.kind === "question",
  isVocabularyPayload: (payload) => payload && payload.kind === "vocabulary",
  spaceWVocabSkipPaths: new Set(),
  spaceWVocabClearedPaths: new Set(),
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.shouldRun = shouldRunSpaceWVocabPreflight;`, context);

assert.equal(context.shouldRun({ kind: "question" }), true, "Space_Q vocabulary preflight must remain available");
context.currentLessonSource.path = "hung/Reading/Paragraph.Space_P";
assert.equal(context.shouldRun({ kind: "paragraph" }), true, "Space_P vocabulary preflight remains available");
assert.match(source, /timeoutMs:\s*spaceLabel === "Space_Q" \? 3000 : 10000/);
console.log("space_q_open_preflight=ok shared_scan=true timeout_ms=3000");
