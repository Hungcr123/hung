const assert = require("node:assert/strict");
const fs = require("node:fs");

const read = (file) => fs.readFileSync(file, "utf8");
const root = "FUTURE/web/js_parts/";
const bootstrap = read(`${root}01_bootstrap_guard_ai_agent.js`);
const scheduler = read(`${root}06_spacew_audio_scheduler.js`);
const runtime = read(`${root}07_audio_speak_runtime.js`);
const ai = read(`${root}02_ai_agent_world_training.js`);
const vocab = read(`${root}12_question_translation_loader.js`);

for (const [name, source] of Object.entries({ scheduler, runtime, ai, vocab })) {
  for (const line of source.split(/\r?\n/).filter((row) => row.includes("/server-data/qm-sound?"))) {
    assert.match(line, /v=current/, `${name} direct QmSound URL must be current-revision safe: ${line.trim()}`);
  }
}
assert.match(bootstrap, /const versionToken = clean\(payload\.version \|\| payload\.etag/);
assert.match(bootstrap, /const controlToken = clean\(payload\.reload_token/);
assert.doesNotMatch(bootstrap, /const token = clean\(payload\.reload_token \|\| payload\.version/);
assert.match(runtime, /setPlaybackState\(false, serverExhausted/);
assert.match(vocab, /window\.__futureReloadCurrentSpaceVAudioCache = async/);
console.log("frontend_audio_pipeline_contract=ok direct_qm_sound_urls=all_current version_poll=asset_first");
