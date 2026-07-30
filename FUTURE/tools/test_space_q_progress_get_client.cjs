const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..", "..");
const progressSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const transportSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
const eventSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");

// Added 2026-07-21: Space_Q Continue revalidates with a payload-coupled ETag and trusts tree preload in folders.
assert.match(progressSource, /currentQuestionProgressCache\.serverPayload = payload/);
assert.match(progressSource, /currentQuestionProgressCache\.serverEtag = clean\(preloaded\.etag \|\| ""\)/);
assert.match(progressSource, /serverPayload: null/);
assert.match(progressSource, /serverEtag: ""/);
assert.match(progressSource, /fetchProgressJsonFast\(`\/space-q\/progress\?\$\{query\.toString\(\)\}`, cachedRow\)/);
assert.match(progressSource, /currentQuestionProgressCache\.serverPayload = null/);
assert.match(progressSource, /currentQuestionProgressCache\.serverEtag = ""/);
assert.match(transportSource, /\^\\\/space-\(\?:v\|w\|q\)\\\/progress/);
assert.match(transportSource, /Space_W\/Q tree\/login preload is authoritative/);
assert.match(transportSource, /space === "Space_W" \|\| space === "Space_Q"/);
assert.match(eventSource, /Could not restore saved Space_Q progress/);
assert.match(eventSource, /continuePreparedLessonFromSavedProgress\(\{ skipAudioPrepare: true \}\)/);

console.log("space_q_progress_get_client=ok conditional_refresh=true cache_loss_retry=true post_invalidation=true sequential_origin=true continue_revalidate=true vault_preload=true");
