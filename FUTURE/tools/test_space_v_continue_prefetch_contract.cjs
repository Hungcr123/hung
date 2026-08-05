"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
const runtimeSource = fs.readFileSync("FUTURE/web/js_parts/12_question_translation_loader.js", "utf8");

assert.match(source, /currentVocabProgressCache\.serverProgressPromise = Promise\.resolve\(options\.serverProgressPromise\)/);
assert.match(source, /progress-preload-hit/);
assert.match(source, /progress-preload-pending/);
assert.match(source, /deferInitialProgressSave: Boolean\(currentVocabProgressCache\.serverProgressPromise && !currentVocabProgressCache\.serverProgressSettled\)/);
assert.match(source, /\[FTG\]\[SpaceVContinue\]/);
assert.match(source, /unlearnedCount = Array\.isArray\(state\.studyIndexes\) \? state\.studyIndexes\.length : 0/);
assert.doesNotMatch(
  source.slice(source.indexOf("const startSavedVocabProgress ="), source.indexOf("const startSavedQuestionProgress =")),
  /if \(canUseVocabProgressServer\(\)\) \{\s*await refreshVocabServerProgress\(\);\s*\}/,
);
assert.match(runtimeSource, /options\.deferInitialProgressSave\s*\? null\s*: saveVocabProgressNow/);

console.log("space_v_continue_prefetch_contract=ok duplicate_refresh=false unlearned_state=preserved trace=true");
