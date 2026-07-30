"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const loader = fs.readFileSync("FUTURE/web/js_parts/12_question_translation_loader.js", "utf8");
const sync = fs.readFileSync("FUTURE/web/js_parts/14_vocab_sync_tasks.js", "utf8");
const bootstrap = fs.readFileSync("FUTURE/web/js_parts/17_vocab_to_pdf_bootstrap.js", "utf8");
const start = loader.indexOf("const completeVocabularyMission = async");
const end = loader.indexOf("const startNextVocabProbe =", start);
const completion = loader.slice(start, end);

assert.ok(start >= 0 && end > start, "Space_V completion block must exist");
assert.match(completion, /progressPayload = await sendVocabServerProgress\(completeRecord, "complete"\)/);
assert.match(completion, /acknowledgeVocabRegistrySyncQueued\(completeRecord, progressPayload\)/);
assert.match(completion, /if \(!registryQueued\) \{\s*scheduleVocabRegistrySync\(80\)/);
assert.doesNotMatch(completion, /prewarmCupLeaderboard[\s\S]*scheduleVocabRegistrySync\(80\)/);
assert.match(sync, /the online Space_V progress route durably queues registry sync/);
assert.match(sync, /syncResult\.queued \|\| syncResult\.running \|\| syncResult\.already_synced/);
assert.match(sync, /setVocabRegistrySyncDirty\(false\)/);
assert.match(sync, /coalesce duplicate completion records/);
assert.match(sync, /mergeVocabSyncWords\(previousRecord\.words, record\.words\)/);
assert.match(bootstrap, /const result = await reportLessonCompleted\("vocab_complete", \{ showGate: false \}\)/);
assert.match(bootstrap, /await window\.prewarmCupLeaderboard\(\{ scope: "day", type: "space_v", force: true \}\)/);
assert.doesNotMatch(bootstrap, /void reportLessonCompleted\("vocab_complete"/);

console.log("space_v_completion_registry_single_path=ok");
