"use strict";

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const bootstrap = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "01_bootstrap_guard_ai_agent.js"), "utf8");
const scheduler = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "06_spacew_audio_scheduler.js"), "utf8");
const warmer = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "07_audio_speak_runtime.js"), "utf8");

if (!bootstrap.includes("window.__futureNativeAudioFetch = nativeFetch")) {
  throw new Error("Foreground audio cannot bypass the duplicate generic fetch cache.");
}
if (scheduler.includes("Promise.race([cacheTask, networkTask])")) {
  throw new Error("Foreground audio still starts network before the durable cache decision.");
}
if (!scheduler.includes("preloadAudioClip(asset, null, { priorityPlayback: true })")) {
  throw new Error("Audio playback is not using the priority path.");
}
const cacheRead = scheduler.indexOf("readSpaceWAudioRecord(persistentKey)");
const networkRead = scheduler.indexOf("rememberFetchedBlob(await fetchAudioBlob(priorityPlayback))");
if (cacheRead < 0 || networkRead < 0 || cacheRead >= networkRead) {
  throw new Error("Priority audio is not local-first before network fallback.");
}
if (!scheduler.includes("GENERIC_MEDIA_AUDIO_CACHE_PREFIX") || !scheduler.includes("content_hash: contentHash")) {
  throw new Error("Audio persistence is not keyed by stable asset identity plus content hash.");
}
const clipKeyStart = scheduler.indexOf("const audioClipCacheKey =");
const clipKeyEnd = scheduler.indexOf("const mediaBlobSha256 =", clipKeyStart);
const clipKeySource = scheduler.slice(clipKeyStart, clipKeyEnd);
if (!clipKeySource.includes("const assetId = audioMediaAssetId(asset)") || !clipKeySource.includes("GENERIC_MEDIA_AUDIO_CACHE_PREFIX")) {
  throw new Error("In-memory/pending audio cache is not keyed by the same shared media identity as IndexedDB.");
}
if (!clipKeySource.includes('parsed.pathname.toLowerCase() === "/server-data/qm-sound"')
  || !clipKeySource.includes('revision.toLowerCase() === "current"')) {
  throw new Error("Space audio RAM can still retain an unrevisioned qm-sound clip.");
}
if (!bootstrap.includes("stableAudioRequestKey") || !bootstrap.includes('path === "/server-data/qm-sound"')) {
  throw new Error("Generic browser audio cache does not recognize /server-data/qm-sound with stable shared keys.");
}
if (!bootstrap.includes('media-audio:v2:qm-sound') || !bootstrap.includes('JSON.stringify({ semanticParams, revision })')) {
  throw new Error("Generic audio cache key does not include the QMLearn content revision.");
}
if (!bootstrap.includes('url.searchParams.set("v", "current")')
  || !bootstrap.includes('revision.toLowerCase() === "current"')
  || !bootstrap.includes("window.__futureRevisionSafeAudioUrl = revisionSafeAudioUrl")
  || !bootstrap.includes("revisionedQmSoundUrlBySemanticKey.set(semanticKey, resolvedUrl)")
  || !bootstrap.includes('cache: persistentKey ? "force-cache" : "reload"')) {
  throw new Error("Legacy qm-sound URLs can still hydrate an unrevisioned IndexedDB or immutable HTTP entry.");
}
if (!scheduler.includes('parsed.pathname.toLowerCase() === "/server-data/qm-sound"')
  || !scheduler.includes('typeof window.__futureRevisionSafeAudioUrl === "function"')) {
  throw new Error("Shared Space audio can still persist a qm-sound record without an authoritative revision.");
}
if (!scheduler.includes("readSpaceWAudioRecord(legacyPersistentKey)")) {
  throw new Error("Legacy URL-keyed audio records are not migrated lazily.");
}
if (!scheduler.includes('["media-tts", "v1", voice') || !scheduler.includes("legacySpaceWAudioCacheKey")) {
  throw new Error("Generated lesson audio is not shared across users with lazy migration.");
}
if (!scheduler.includes("const assetId = audioMediaAssetId({ url: source })") || !scheduler.includes("legacySpaceWUrlAudioCacheKey")) {
  throw new Error("Embedded/URL audio is not shared across users by stable media identity.");
}
const sharedTtsKey = scheduler.slice(scheduler.indexOf("const spaceWAudioCacheKey ="), scheduler.indexOf("const legacySpaceWAudioCacheKey ="));
if (sharedTtsKey.includes("spaceWUserKey")) {
  throw new Error("Shared TTS media key is still scoped to a user.");
}
if (!warmer.includes('offlineStoragePressure === "critical"') || !warmer.includes('offlineStoragePressure === "high" ? 2 : 0')) {
  throw new Error("Deep audio warming is not reduced under storage pressure.");
}
if (!warmer.includes('await ensureOfflineStoragePersistence()') || !warmer.includes('pressure === "high" ? configuredRows.slice(0, 4)')) {
  throw new Error("Shared audio background work does not check current browser quota before prefetching.");
}

console.log("space_v_priority_audio=ok local_first=true cache_hit_network=0 identity=asset+sha256 shared_all_spaces=true qm_sound_idb=true legacy_migration=lazy pressure=bounded");
