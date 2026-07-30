"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const authSource = fs.readFileSync("FUTURE/web/js_parts/05_screen_motion_layout.js", "utf8");
const vocabSource = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
const noticesSource = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");

const completeAuthStart = authSource.indexOf("const completeAuth = async");
const completeAuthEnd = authSource.indexOf("const clearStoredAuthToken =", completeAuthStart);
const completeAuthSource = authSource.slice(completeAuthStart, completeAuthEnd);

assert.ok(completeAuthStart >= 0 && completeAuthEnd > completeAuthStart);
assert.doesNotMatch(
  completeAuthSource,
  /loadVocabLessonIndex\(/,
  "login must not fetch or parse the large vocabulary lesson index",
);
assert.match(completeAuthSource, /void openVaultAfterAuth\(\)/);
assert.doesNotMatch(
  completeAuthSource,
  /const openedPayload = await openServerBrowserAfterAuth[\s\S]*recordAuthPhase\("open-vault"\)/,
  "the first Lesson Vault paint must run outside the login promise",
);

const registryStatsStart = vocabSource.indexOf("const vocabRegistrySnapshotForStats =");
const registryStatsEnd = vocabSource.indexOf("const statsFromEntryVocabWordKeys =", registryStatsStart);
const registryStatsSource = vocabSource.slice(registryStatsStart, registryStatsEnd);
assert.ok(registryStatsStart >= 0 && registryStatsEnd > registryStatsStart);
assert.ok(
  registryStatsSource.indexOf("vocabRegistryLoaded") < registryStatsSource.indexOf("readVocabRegistryLocalCache"),
  "file clicks must use the in-memory vocabulary registry before parsing localStorage",
);

assert.match(vocabSource, /vocabLessonIndexMemoryCache/);
assert.match(vocabSource, /parse the large lesson index once per user/);
assert.match(vocabSource, /const fetchVocabFileKeyMap = async/);
assert.match(vocabSource, /\/vocab\/file-key-map/);
assert.match(vocabSource, /cacheEarnKeysFromLessonVaultEntries/);
const announceStart = noticesSource.indexOf("const announceSpaceVFileStats = async");
const announceEnd = noticesSource.indexOf("const questionInventoryUserKey =", announceStart);
const announceSource = noticesSource.slice(announceStart, announceEnd);
assert.ok(announceStart >= 0 && announceEnd > announceStart);
assert.match(announceSource, /fetchVocabFileKeyMap\(entry, learnerUser\)/);
assert.doesNotMatch(announceSource, /\/vocab\/file-stats|\/vocab\/lesson-index|\/space-v\/progress|\/server-data\/list/);

console.log("frontend_login_click_fast_path=ok");
