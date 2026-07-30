const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const readPart = (name) => fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", name), "utf8");

const source = readPart("12_question_translation_loader.js");
assert.match(source, /Repetition \$\{Math\.min\(vocabDrillCorrectCount, 10\)\} \/ 10/);
assert.doesNotMatch(source, /vocabDrillCorrectCount \+ 1/);
assert.match(source, /initialProgressRecord\.action = options\.forceNewRun \? "new_run" : "autosave"/);
assert.match(source, /initialProgressRecord\.state\.forceNewRun = true/);
const completeStart = source.indexOf("const completeVocabularyMission = async");
const completeEnd = source.indexOf("const startNextVocabProbe =", completeStart);
const completeHandler = source.slice(completeStart, completeEnd);
assert.match(completeHandler, /vocabLearnedKeys\.size < vocabItems\.length/);
assert.ok(
  completeHandler.indexOf("vocabLearnedKeys.size < vocabItems.length") < completeHandler.indexOf("vocabCompletionFinalizing = true"),
  "Completion guard must run before completion mutates state",
);
const resetStart = source.indexOf("const resetVocabInputForNewWord =");
const resetEnd = source.indexOf("const showVocabModePopup =", resetStart);
const resetHandler = source.slice(resetStart, resetEnd);
assert.doesNotMatch(resetHandler, /\[40, 120, 240\]/);
const resetTimerStart = resetHandler.indexOf("window.setTimeout(() =>");
const resetTimerBody = resetHandler.slice(resetTimerStart);
assert.doesNotMatch(resetTimerBody, /vocabAnswer\.value\s*=\s*""/);
assert.match(resetTimerBody, /vocabInputResetUntil = 0;/);

const start = source.indexOf("const checkVocabAnswer = async");
const end = source.indexOf("const enterVocabularyPayloadNow = async", start);
assert.ok(start >= 0 && end > start, "Space_V answer handler not found");
const handler = source.slice(start, end);

assert.match(handler, /const suppressRapidSubmit = vocabPhase !== "drill";/);
assert.match(handler, /if \(suppressRapidSubmit && now < vocabAnswerSubmitLockUntil\)/);
assert.match(handler, /vocabAnswerSubmitLockUntil = suppressRapidSubmit \? now \+ 220 : 0;/);

const submitLockStart = handler.indexOf("if (suppressRapidSubmit && now < vocabAnswerSubmitLockUntil)");
const submitLockEnd = handler.indexOf("if (vocabAnswer.disabled)", submitLockStart);
const submitLockBlock = handler.slice(submitLockStart, submitLockEnd);
assert.doesNotMatch(submitLockBlock, /clearFastVocabInput|vocabAnswer\.value\s*=\s*""/);
assert.doesNotMatch(handler, /if \(now < vocabInputResetUntil\)/);

const eventSource = readPart("21_progress_bootstrap_events.js");
const inputStart = eventSource.indexOf('vocabAnswer.addEventListener("input"');
const inputEnd = eventSource.indexOf('vocabAnswer.addEventListener("focus"', inputStart);
const inputHandler = eventSource.slice(inputStart, inputEnd);
assert.match(inputHandler, /vocabAnswer\.disabled \|\| vocabAnswer\.readOnly/);
assert.doesNotMatch(inputHandler, /Date\.now\(\) < vocabInputResetUntil|vocabAnswer\.value\s*=\s*""/);

const eventStart = source.indexOf("const postSpaceVClientEvent =");
const eventEnd = source.indexOf("const checkVocabProbeAnswer =", eventStart);
const eventHandler = source.slice(eventStart, eventEnd);
assert.doesNotMatch(eventHandler, /saveVocabProgressNow|queueVocabServerProgressSync/);
assert.match(eventHandler, /const postSpaceVClientEvent = \(\) => \{\};/);

const drillStart = source.indexOf("const checkVocabDrillAnswer = async");
const drillEnd = source.indexOf("const checkVocabShuffleAnswer = async", drillStart);
const drillHandler = source.slice(drillStart, drillEnd);
assert.doesNotMatch(drillHandler, /saveVocabProgressNow\(/);
assert.ok((drillHandler.match(/queueVocabProgressSave\(600\)/g) || []).length >= 2);
assert.match(drillHandler, /playVocabAnswerThen\(item, index, null, \{ lockDuringPlayback: false \}\)/);
assert.doesNotMatch(drillHandler, /showVocabItem\(item, index/);

const probeStart = source.indexOf("const checkVocabProbeAnswer = async");
const probeEnd = source.indexOf("const checkVocabDrillAnswer = async", probeStart);
const probeHandler = source.slice(probeStart, probeEnd);
assert.doesNotMatch(probeHandler, /saveVocabProgressNow\(/);
assert.match(probeHandler, /addVocabUnlearnedIndex\(vocabCurrentIndex, \{ deferSave: true \}\)/);

const shuffleStart = source.indexOf("const checkVocabShuffleAnswer = async");
const shuffleEnd = source.indexOf("const checkVocabAnswer = async", shuffleStart);
const shuffleHandler = source.slice(shuffleStart, shuffleEnd);
assert.doesNotMatch(shuffleHandler, /saveVocabProgressNow\(/);
assert.ok((shuffleHandler.match(/queueVocabProgressSave\(600\)/g) || []).length >= 2);

console.log("space_v_enter=ok probe_drill_shuffle_render_first=true event_posts=0 save=debounced same_card_rerender=false");
