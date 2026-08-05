"use strict";

const fs = require("fs");
const { chromium } = require("playwright");

const [base, oldUrl, audioPath, newQuery] = process.argv.slice(2);
if (!base || !oldUrl || !audioPath || !newQuery) {
  throw new Error("usage: test_vocab_audio_browser_cache.cjs BASE OLD_URL AUDIO_PATH NEW_QUERY");
}

const sha256 = async (page, url) => page.evaluate(async (target) => {
  const response = await fetch(target);
  const bytes = new Uint8Array(await response.arrayBuffer());
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join("");
}, url);

const seedLegacyUnversionedRecord = async (page, url, blobUrl) => page.evaluate(async ({ target, sourceBlobUrl }) => {
  const parsed = new URL(target, window.location.href);
  const semanticParams = Array.from(parsed.searchParams.entries())
    .filter(([name]) => !["ts", "cache"].includes(String(name || "").trim().toLowerCase()))
    .sort((a, b) => `${a[0]}=${a[1]}`.localeCompare(`${b[0]}=${b[1]}`));
  const encoded = new TextEncoder().encode(JSON.stringify({ semanticParams, revision: "" }));
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  const hash = Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join("");
  const key = `media-audio:v2:qm-sound:${hash}`;
  const blob = await (await fetch(sourceBlobUrl)).blob();
  await new Promise((resolve, reject) => {
    const open = indexedDB.open("future_server2_audio_cache_v1", 1);
    open.onerror = () => reject(open.error || new Error("legacy IDB open failed"));
    open.onsuccess = () => {
      const tx = open.result.transaction("audio", "readwrite");
      tx.objectStore("audio").put({ key, url: target, blob, mime: blob.type || "audio/mpeg", createdAt: new Date().toISOString() });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error("legacy IDB write failed"));
    };
  });
  return key;
}, { target: url, sourceBlobUrl: blobUrl });

const main = async () => {
  const browser = await chromium.launch({ headless: true, executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" });
  const page = await browser.newPage();
  let qmRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/server-data/qm-sound")) qmRequests += 1;
  });
  await page.goto(`${base}/login`, { waitUntil: "domcontentloaded" });
  const oldBlob = await page.evaluate(async (url) => window.__futureResolveCachedAudioUrl(url), oldUrl);
  if (!String(oldBlob).startsWith("blob:")) throw new Error("old audio did not hydrate into a blob URL");
  const oldSha = await sha256(page, oldBlob);
  const unversionedUrl = `${base}${newQuery}`;
  const legacyUnversionedKey = await seedLegacyUnversionedRecord(page, unversionedUrl, oldBlob);

  // Replace the source after the old revision is safely persisted in IDB.
  const replacement = Buffer.from(fs.readFileSync(audioPath));
  replacement[replacement.length - 1] ^= 0x01;
  fs.writeFileSync(audioPath, replacement);
  const now = Date.now() / 1000;
  fs.utimesSync(audioPath, now + 2, now + 2);
  await page.waitForTimeout(80);
  const native = await page.evaluate(async (url) => {
    const response = await window.__futureNativeAudioFetch(url, { cache: "no-store" });
    const bytes = new Uint8Array(await response.arrayBuffer());
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return {
      sha: Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join(""),
      revision: response.headers.get("X-Future-Audio-Revision") || "",
    };
  }, `${base}${newQuery}`);
  const newVersionedUrl = `${base}${newQuery}${newQuery.includes("?") ? "&" : "?"}v=${encodeURIComponent(native.revision)}`;
  const newBlob = await page.evaluate(async (url) => window.__futureResolveCachedAudioUrl(url), newVersionedUrl);
  if (!String(newBlob).startsWith("blob:")) throw new Error("new audio did not hydrate into a blob URL");
  const newSha = await sha256(page, newBlob);
  const reopened = await browser.newPage();
  reopened.on("request", (request) => {
    if (request.url().includes("/server-data/qm-sound")) qmRequests += 1;
  });
  await reopened.goto(`${base}/login`, { waitUntil: "domcontentloaded" });
  const legacyResolution = await reopened.evaluate(async (url) => window.__futureResolveCachedAudioUrl(url), unversionedUrl);
  if (!String(legacyResolution).startsWith("blob:")) {
    throw new Error(`legacy unversioned cache was reused: ${legacyResolution}`);
  }
  const legacyRefreshSha = await sha256(reopened, legacyResolution);
  const mappedRevisionUrl = await reopened.evaluate((url) => window.__futureRevisionSafeAudioUrl(url), unversionedUrl);
  const requestsBeforeRepeat = qmRequests;
  const repeatResolution = await reopened.evaluate(async (url) => window.__futureResolveCachedAudioUrl(url), unversionedUrl);
  const repeatRefreshSha = await sha256(reopened, repeatResolution);
  const repeatNetworkRequests = qmRequests - requestsBeforeRepeat;
  const idbCount = await page.evaluate(async () => new Promise((resolve) => {
    const request = indexedDB.open("future_server2_audio_cache_v1", 1);
    request.onerror = () => resolve(0);
    request.onsuccess = () => {
      const db = request.result;
      const tx = db.transaction("audio", "readonly");
      const count = tx.objectStore("audio").count();
      count.onsuccess = () => resolve(count.result || 0);
      count.onerror = () => resolve(0);
    };
  }));
  await browser.close();
  const output = { old_sha256: oldSha, native_new_sha256: native.sha, cached_new_sha256: newSha, legacy_refresh_sha256: legacyRefreshSha, repeat_refresh_sha256: repeatRefreshSha, repeat_network_requests: repeatNetworkRequests, legacy_unversioned_key: legacyUnversionedKey, legacy_resolution: legacyResolution, mapped_revision_url: mappedRevisionUrl, new_revision: native.revision, qm_requests: qmRequests, idb_audio_records: idbCount };
  console.log(JSON.stringify(output));
  if (oldSha === newSha || native.sha !== newSha || legacyRefreshSha !== newSha || repeatRefreshSha !== newSha
    || repeatNetworkRequests !== 0 || !String(mappedRevisionUrl).includes(`v=${encodeURIComponent(native.revision)}`)
    || !native.revision || idbCount < 3 || qmRequests < 3) process.exitCode = 1;
};

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
