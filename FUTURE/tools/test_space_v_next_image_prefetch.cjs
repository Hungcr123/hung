const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "12_question_translation_loader.js"),
  "utf8",
);
const layoutSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "05_screen_motion_layout.js"),
  "utf8",
);

const nextStart = source.indexOf("const nextLikelyVocabImageItem =");
const nextEnd = source.indexOf("const prefetchVocabImageBytes =", nextStart);
assert.ok(nextStart >= 0 && nextEnd > nextStart, "next-image predictor missing");
const nextSource = source.slice(nextStart, nextEnd);
assert.match(nextSource, /vocabStudyIndexes\[vocabDrillIndex \+ 1\]/);
assert.match(nextSource, /vocabShuffleQueue\[0\]/);
assert.match(nextSource, /vocabQueue\.find\(\(candidate\) => vocabCanProbeIndex\(candidate\)\)/);

const scheduleStart = source.indexOf("const scheduleNextVocabImagePrefetch =");
const scheduleEnd = source.indexOf("const renderVocabPictureCard =", scheduleStart);
assert.ok(scheduleStart >= 0 && scheduleEnd > scheduleStart, "bounded next-image scheduler missing");
const scheduleSource = source.slice(scheduleStart, scheduleEnd);
assert.match(scheduleSource, /connection\.saveData/);
assert.match(scheduleSource, /2g\$\/i/);
assert.equal(
  (scheduleSource.match(/ensureVocabItemImageLazy\(/g) || []).length,
  1,
  "scheduler must request only one predicted item",
);
assert.match(scheduleSource, /\{ prefetchBytes: true \}/);

const renderStart = source.indexOf("const renderVocabPictureCard =");
const renderEnd = source.indexOf("const renderVocabSideCards =", renderStart);
const renderSource = source.slice(renderStart, renderEnd);
assert.match(renderSource, /vocabPictureImg\.onload =/);
assert.match(renderSource, /scheduleNextVocabImagePrefetch\(item\)/);

const ensureStart = source.indexOf("const ensureVocabItemImageLazy =");
const ensureEnd = source.indexOf("const scheduleNextVocabImagePrefetch =", ensureStart);
const ensureSource = source.slice(ensureStart, ensureEnd);
assert.ok(
  ensureSource.indexOf("readVocabImageRecord(assetId)") < ensureSource.indexOf("fetchServerJson(`/vocab/image"),
  "persistent image must be checked before Server 2",
);
assert.match(ensureSource, /fetchAndPersistVocabImage\(clean\(serverAsset\.asset_id\) \|\| assetId, image, serverAsset\)/);
assert.match(ensureSource, /result && result\.payload && typeof result\.payload === "object" \? result\.payload : result/);
assert.match(ensureSource, /vocabSideCardsVisible\(\) && current && vocabWordKey\(current\) === key/);
assert.match(ensureSource, /renderVocabPictureCard\(item\)/, "cached metadata must render immediately on Drill entry");

assert.match(layoutSource, /const VOCAB_IMAGE_DB_VERSION = 2/);
assert.match(layoutSource, /const VOCAB_IMAGE_MEDIA_KEY_VERSION = 1/);
assert.match(layoutSource, /const VOCAB_IMAGE_CACHE_MAX_ENTRIES = 192/);
assert.match(layoutSource, /VOCAB_IMAGE_CACHE_MAX_BYTES = 64 \* 1024 \* 1024/);
assert.match(source, /store\.createIndex\("accessAt", "accessAt"/);
assert.match(source, /store\.createIndex\("assetId", "assetId", \{ unique: true \}\)/);
assert.match(source, /crypto\.subtle\.digest\("SHA-256"/);
assert.match(source, /contentHash/);
assert.match(source, /mediaKeyVersion: VOCAB_IMAGE_MEDIA_KEY_VERSION/);
const imageKeyStart = source.indexOf("const vocabImageAssetId =");
const imageKeyEnd = source.indexOf("const vocabImageBlobSha256 =", imageKeyStart);
assert.ok(imageKeyStart >= 0 && imageKeyEnd > imageKeyStart, "shared image media key missing");
assert.doesNotMatch(source.slice(imageKeyStart, imageKeyEnd), /user|username|study_user/i, "image media key must be shared by all users on one client");
assert.match(source, /navigator\.storage\.persisted/);
assert.match(source, /navigator\.storage\.persist\(\)/);
assert.match(layoutSource, /OFFLINE_STORAGE_ESTIMATE_REFRESH_MS = 60 \* 1000/);
assert.match(source, /ensureOfflineStoragePersistence = \(forceRefresh = false\)/);
assert.match(source, /ensureOfflineStoragePersistence\(true\)\.then\(\(\) => pruneVocabImageCache\(\)\)/);
assert.match(source, /ratio >= 0\.85 \? "critical" : \(ratio >= 0\.7 \? "high" : "normal"\)/);
assert.match(source, /QuotaExceededError/);
assert.match(source, /limited: true/);
assert.match(renderSource, /if \(vocabSideCardsVisible\(\)\) \{\s*ensureVocabItemImageLazy\(item\)/, "Probe must not fetch optional images");
assert.match(scheduleSource, /offlineStoragePressure === "high"/);

console.log("space_v_next_image_prefetch=ok next=1 persistent=idb identity=asset+sha256 lru=192 quota=64MB probe_fetch=0");
