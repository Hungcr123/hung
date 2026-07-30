const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const inputSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "08_speak_question_input.js"), "utf8");
const syncSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");

const tokenStart = inputSource.indexOf("function paragraphTokenCountForChild");
const tokenEnd = inputSource.indexOf("function paragraphCompletedSegments()", tokenStart);
assert.ok(tokenStart >= 0 && tokenEnd > tokenStart, "paragraph token snapshot functions not found");

const tokenContext = {
  paragraphNodes: [{ children: [{ text: "One two three" }, { text: "Four five" }] }],
  paragraphNodeIndex: 0,
  paragraphChildIndex: 0,
  paragraphRevealed: [3, 0],
  paragraphWordParts: (value) => String(value || "").split(/\s+/).filter(Boolean).map((word) => ({ word })),
  paragraphWordKey: (value) => String(value || "").toLowerCase(),
  isSpaceSpeechPayload: () => true,
  spaceSLastReadScore: 0,
  SPACE_S_PASS_SCORE: 80,
};
vm.createContext(tokenContext);
vm.runInContext(`${inputSource.slice(tokenStart, tokenEnd)}\nthis.completedTokens = paragraphCompletedTokensForSnapshot;`, tokenContext);
assert.equal(tokenContext.completedTokens(), 0, "visible Space_S words must not count before a passing read");
tokenContext.spaceSLastReadScore = 80;
assert.equal(tokenContext.completedTokens(), 3, "a passing Space_S read may count the current sentence");
tokenContext.paragraphChildIndex = 1;
tokenContext.spaceSLastReadScore = 0;
assert.equal(tokenContext.completedTokens(), 3, "only prior sentences count after advancing");

const completeStart = syncSource.indexOf("const paragraphCurrentSegmentComplete =");
const completeEnd = syncSource.indexOf("const paragraphCompletedSegmentsForSnapshot =", completeStart);
assert.ok(completeStart >= 0 && completeEnd > completeStart, "paragraph current-segment function not found");
const completeContext = {
  isSpaceSpeechPayload: () => true,
  spaceSLastReadScore: 0,
  SPACE_S_PASS_SCORE: 80,
  currentParagraphWords: () => ["one", "two", "three"],
  paragraphRevealed: [3],
  paragraphChildIndex: 0,
};
vm.createContext(completeContext);
vm.runInContext(`${syncSource.slice(completeStart, completeEnd)}\nthis.segmentComplete = paragraphCurrentSegmentComplete;`, completeContext);
assert.equal(completeContext.segmentComplete(), false, "Space_S starts at 0/N even though its guide sentence is visible");
completeContext.spaceSLastReadScore = 80;
assert.equal(completeContext.segmentComplete(), true, "Space_S counts the sentence after passing");
completeContext.isSpaceSpeechPayload = () => false;
completeContext.spaceSLastReadScore = 0;
assert.equal(completeContext.segmentComplete(), true, "Space_P still counts a fully revealed typed sentence");

console.log("space_s_initial_progress=ok visible_words=0 passed_read=1 prior_sentence=1 space_p_unchanged=true");
