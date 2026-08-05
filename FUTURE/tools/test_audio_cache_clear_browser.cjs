"use strict";

const { chromium } = require("playwright");

const base = process.argv[2] || "http://127.0.0.1:8877";

const main = async () => {
  const browser = await chromium.launch({ headless: true, executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" });
  const page = await browser.newPage();
  await page.goto(`${base}/login`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => typeof window.__futureClearAudioCache === "function" && typeof window.__futureClearLessonAudioCache === "function");
  const result = await page.evaluate(async () => {
    const seed = (name, version, storeName) => new Promise((resolve, reject) => {
      const request = indexedDB.open(name, version);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(storeName)) {
          request.result.createObjectStore(storeName, { keyPath: "key" });
        }
      };
      request.onerror = () => reject(request.error || new Error(`open ${name} failed`));
      request.onsuccess = () => {
        const db = request.result;
        const tx = db.transaction(storeName, "readwrite");
        tx.objectStore(storeName).put({ key: "stale", blob: new Blob(["stale-audio"], { type: "audio/mpeg" }) });
        tx.oncomplete = () => { db.close(); resolve(true); };
        tx.onerror = () => reject(tx.error || new Error(`seed ${name} failed`));
      };
    });
    await seed("future_server2_audio_cache_v1", 1, "audio");
    await seed("future_space_w_audio_cache", 2, "audio");
    await caches.open("future-audio-test-cache");
    let activeReloadCalls = 0;
    window.__futureReloadCurrentSpaceVAudioCache = async () => {
      activeReloadCalls += 1;
      return { ok: true, active: true, startIndex: 7, ready: 4, failed: 0 };
    };
    const cleared = await window.__futureClearAudioCache({ epoch: 123456, source: "browser-contract" });
    const databases = typeof indexedDB.databases === "function" ? await indexedDB.databases() : [];
    const names = databases.map((row) => row.name).filter(Boolean);
    const cacheNames = await caches.keys();
    const refreshedUrl = window.__futureRevisionSafeAudioUrl("/server-data/qm-sound?word=book&voice=sot%3Aen-GB&v=current");
    return {
      cleared,
      names,
      cacheNames,
      refreshedUrl,
      activeReloadCalls,
      managerEpoch: window.__futureAudioCacheManager.epoch(),
      lastSeenEpoch: Number(localStorage.getItem("last_seen_audio_cache_epoch") || 0),
    };
  });
  await browser.close();
  console.log(JSON.stringify(result));
  if (!result.cleared || result.cleared.ok === false
    || result.names.includes("future_server2_audio_cache_v1")
    || result.names.includes("future_space_w_audio_cache")
    || result.activeReloadCalls !== 1
    || !result.cleared.active_reload || result.cleared.active_reload.startIndex !== 7
    || result.cacheNames.includes("future-audio-test-cache")
    || result.managerEpoch !== 123456
    || result.lastSeenEpoch !== 123456
    || /[?&]cache=/.test(result.refreshedUrl)) {
    process.exitCode = 1;
  }
};

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
