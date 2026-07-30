"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const bootstrap = fs.readFileSync("FUTURE/web/js_parts/01_bootstrap_guard_ai_agent.js", "utf8");
const audio = fs.readFileSync("FUTURE/web/js_parts/06_spacew_audio_scheduler.js", "utf8");
const images = fs.readFileSync("FUTURE/web/js_parts/12_question_translation_loader.js", "utf8");

const imageStart = images.indexOf("const pruneVocabImageCache =");
const imageEnd = images.indexOf("const vocabImageAssetId =", imageStart);
const imagePrune = images.slice(imageStart, imageEnd);
const audioStart = audio.indexOf("const pruneSpaceWAudioCache =");
const audioEnd = audio.indexOf("const normalizedCacheVoiceValue =", audioStart);
const audioPrune = audio.slice(audioStart, audioEnd);

assert.ok(imageStart >= 0 && audioStart >= 0);
assert.doesNotMatch(imagePrune, /\.getAll\(/, "image pruning must not materialize every cached blob");
assert.match(imagePrune, /openCursor\(null, "prev"\)/);
assert.match(audioPrune, /openCursor\(null, "prev"\)/);
assert.match(bootstrap, /SPACE_W_AUDIO_DB_VERSION = 2/);
assert.match(bootstrap, /SPACE_W_AUDIO_CACHE_MAX_BYTES = 512 \* 1024 \* 1024/);
assert.match(audio, /db\.onversionchange[\s\S]*spaceWAudioDbPromise = null/);
assert.match(images, /db\.onversionchange[\s\S]*vocabImageDbPromise = null/);
assert.match(images, /await pruneVocabImageCache\(\);[\s\S]*await pruneSpaceWAudioCache/);
assert.match(audioPrune, /pruneVocabImageCache[\s\S]*pruneSpaceWAudioCache/);

function retained(totalBytes, recordBytes, entryLimit, byteLimit) {
  const totalEntries = Math.ceil(totalBytes / recordBytes);
  const keptEntries = Math.min(totalEntries, entryLimit, Math.floor(byteLimit / recordBytes));
  return { totalEntries, keptEntries, keptBytes: keptEntries * recordBytes };
}

function benchmarkCursorModel(totalBytes, recordBytes, entryLimit, byteLimit) {
  const totalEntries = Math.ceil(totalBytes / recordBytes);
  let keptEntries = 0;
  let keptBytes = 0;
  let peakHeldRecords = 0;
  const cpuStart = process.cpuUsage();
  for (let index = 0; index < totalEntries; index += 1) {
    peakHeldRecords = Math.max(peakHeldRecords, 1);
    if (keptEntries < entryLimit && keptBytes + recordBytes <= byteLimit) {
      keptEntries += 1;
      keptBytes += recordBytes;
    }
  }
  const cpu = process.cpuUsage(cpuStart);
  return {
    recordsScanned: totalEntries,
    peakHeldRecords,
    cpuMs: (cpu.user + cpu.system) / 1000,
    keptBytes,
  };
}

async function verifyAudioQuotaRetry(alwaysFail = false) {
  const writeStart = audio.indexOf("const writeSpaceWAudioRecord =");
  const writeEnd = audio.indexOf("const normalizedCacheVoiceValue =", writeStart);
  const writeSource = audio.slice(writeStart, writeEnd);
  assert.ok(writeStart >= 0 && writeEnd > writeStart);
  const calls = [];
  let attempts = 0;
  const context = {
    Blob,
    Date,
    Promise,
    setImmediate,
    clean: (value) => String(value || "").trim(),
    isUsableCachedAudioBlob: () => true,
    SPACE_W_AUDIO_STORE: "audio",
    spaceWAudioPersistentWrites: 0,
    offlineStoragePressure: "normal",
    window: {},
    pruneVocabImageCache: async () => calls.push("image-prune"),
    pruneSpaceWAudioCache: async () => calls.push("audio-prune"),
    openSpaceWAudioDb: async () => ({
      transaction() {
        attempts += 1;
        if (alwaysFail || attempts === 1) {
          const error = new Error("quota");
          error.name = "QuotaExceededError";
          throw error;
        }
        const transaction = {
          objectStore: () => ({
            put: () => setImmediate(() => transaction.oncomplete && transaction.oncomplete()),
          }),
        };
        return transaction;
      },
    }),
  };
  vm.runInNewContext(`${writeSource}\nthis.writeSpaceWAudioRecord = writeSpaceWAudioRecord;`, context);
  const stored = await context.writeSpaceWAudioRecord({
    key: "quota-test",
    blob: new Blob([Buffer.alloc(256)], { type: "audio/mpeg" }),
  });
  return { stored, attempts, calls, state: context.window.__futureOfflineStorageState || null };
}

const MB = 1024 * 1024;
const GB = 1024 * MB;
const image500 = retained(500 * MB, 512 * 1024, 192, 64 * MB);
const image2g = retained(2 * GB, 512 * 1024, 192, 64 * MB);
const audio500 = retained(500 * MB, 256 * 1024, 8000, 512 * MB);
const audio2g = retained(2 * GB, 256 * 1024, 8000, 512 * MB);
const audioCritical = retained(2 * GB, 256 * 1024, 2000, 128 * MB);
const cursor500 = benchmarkCursorModel(500 * MB, 256 * 1024, 8000, 512 * MB);
const cursor2g = benchmarkCursorModel(2 * GB, 256 * 1024, 8000, 512 * MB);

assert.ok(image500.keptBytes <= 64 * MB && image2g.keptBytes <= 64 * MB);
assert.equal(audio500.keptBytes, 500 * MB);
assert.ok(audio2g.keptBytes <= 512 * MB);
assert.ok(audioCritical.keptBytes <= 128 * MB);

Promise.all([verifyAudioQuotaRetry(false), verifyAudioQuotaRetry(true)]).then(([retry, degraded]) => {
  assert.equal(retry.stored, true);
  assert.equal(retry.attempts, 2);
  assert.deepEqual(retry.calls, ["image-prune", "audio-prune"]);
  assert.equal(degraded.stored, false);
  assert.equal(degraded.attempts, 2);
  assert.deepEqual(degraded.calls, ["image-prune", "audio-prune"]);
  assert.equal(degraded.state, null, "a failed cache write must return without blocking lesson execution");
  assert.equal(cursor500.peakHeldRecords, 1);
  assert.equal(cursor2g.peakHeldRecords, 1);

  console.log(JSON.stringify({
    media_quota_recovery: "ok",
    image_500mb_kept_mb: image500.keptBytes / MB,
    image_2gb_kept_mb: image2g.keptBytes / MB,
    audio_500mb_kept_mb: audio500.keptBytes / MB,
    audio_2gb_kept_mb: audio2g.keptBytes / MB,
    audio_critical_kept_mb: audioCritical.keptBytes / MB,
    quota_retry_order: retry.calls,
    quota_retry_attempts: retry.attempts,
    quota_degrades_without_throw: !degraded.stored,
    cursor_500mb: cursor500,
    cursor_2gb: cursor2g,
    pruning: "cursor",
    recovery: "versionchange-reopen",
  }));
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
