const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..", "..");
const progressSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const transportSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");

// Added 2026-07-20: Continue Previous revalidates cross-device state with a payload-coupled ETag.
assert.match(progressSource, /serverPayload: null/);
assert.match(progressSource, /serverEtag: ""/);
assert.match(progressSource, /fetchProgressJsonFast\(`\/space-v\/progress\?\$\{query\.toString\(\)\}`, cachedRow\)/);
assert.match(progressSource, /currentVocabProgressCache\.serverPayload = payload/);
assert.match(progressSource, /currentVocabProgressCache\.serverEtag = clean/);
assert.doesNotMatch(progressSource, /VOCAB_SERVER_PROGRESS_FRESH_MS/);
assert.match(transportSource, /headers\["If-None-Match"\] = clean\(cachedRow\.etag\)/);
assert.match(transportSource, /response\.status === 304/);
assert.match(transportSource, /delete headers\["If-None-Match"\]/);
assert.match(transportSource, /\^\\\/space-\(\?:v\|w\|q\)\\\/progress/);
assert.match(transportSource, /for \(const base of candidates\)/);

console.log("space_v_progress_get_client=ok conditional_refresh=true cache_loss_retry=true stale_device_revalidate=true sequential_origin=true");
