

      const mergeVocabSyncWords = (existingWords = [], nextWords = []) => {
        const out = new Map();
        const add = (item) => {
          const normalized = compactVocabWordForRegistry(item);
          const key = vocabWordKey(normalized);
          if (!normalized || !key) {
            return;
          }
          const previous = out.get(key) || {};
          out.set(key, {
            word: normalized.word || previous.word || key,
            meaning: normalized.meaning || previous.meaning || "",
            pron: normalized.pron || previous.pron || "",
            type: normalized.type || previous.type || "",
          });
        };
        (Array.isArray(existingWords) ? existingWords : []).forEach(add);
        (Array.isArray(nextWords) ? nextWords : []).forEach(add);
        return Array.from(out.values());
      };

      const vocabSyncWordsSignature = (words = []) => mergeVocabSyncWords([], words)
        .map((item) => `${vocabWordKey(item)}\t${clean(item.meaning)}\t${clean(item.pron)}\t${clean(item.type)}`)
        .sort()
        .join("\n");

      const VOCAB_REGISTRY_SYNC_DIRTY_KEY = "future_vocab_registry_sync_dirty";

      const setVocabRegistrySyncDirty = (value = false) => {
        try {
          if (!window.localStorage) {
            return;
          }
          if (value) {
            localStorage.setItem(VOCAB_REGISTRY_SYNC_DIRTY_KEY, "1");
          } else {
            localStorage.removeItem(VOCAB_REGISTRY_SYNC_DIRTY_KEY);
          }
        } catch (error) {
          // ignore
        }
      };

      const hasVocabRegistrySyncDirty = () => {
        try {
          if (!window.localStorage) {
            return false;
          }
          return clean(localStorage.getItem(VOCAB_REGISTRY_SYNC_DIRTY_KEY) || "") === "1";
        } catch (error) {
          return false;
        }
      };

      // Added 2026-07-29: the online Space_V progress route durably queues registry sync; do not resend the same completion.
      const acknowledgeVocabRegistrySyncQueued = (record = null, progressPayload = null) => {
        const syncResult = progressPayload && typeof progressPayload.registry_sync === "object" ? progressPayload.registry_sync : null;
        if (!syncResult || !(syncResult.queued || syncResult.running || syncResult.already_synced)) {
          return false;
        }
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const syncedAt = clean(source.savedAt || state.savedAt || "");
        const syncedUser = clean(currentAuthUsername || "");
        const syncedLearned = Array.isArray(source.words) ? source.words.length : (Array.isArray(state.learnedWords) ? state.learnedWords.length : 0);
        const keys = [
          vocabSyncStorageKey(source.identity || state.identity || currentVocabProgressCache.identity),
          currentVocabProgressCache.progressKey,
        ].filter(Boolean);
        keys.forEach((key) => {
          const existing = readSpaceWJson(key);
          if (!existing || typeof existing !== "object") {
            return;
          }
          existing.serverSyncedAt = syncedAt;
          existing.serverSyncedUser = syncedUser;
          existing.serverSyncedLearned = syncedLearned;
          if (existing.state && typeof existing.state === "object") {
            existing.state.serverSyncedAt = syncedAt;
          }
          writeSpaceWJson(key, existing);
        });
        if (currentVocabProgressCache.savedProgress && typeof currentVocabProgressCache.savedProgress === "object") {
          currentVocabProgressCache.savedProgress.serverSyncedAt = syncedAt;
          currentVocabProgressCache.savedProgress.serverSyncedUser = syncedUser;
          currentVocabProgressCache.savedProgress.serverSyncedLearned = syncedLearned;
        }
        if (vocabRegistrySyncTimer) {
          window.clearTimeout(vocabRegistrySyncTimer);
          vocabRegistrySyncTimer = 0;
        }
        setVocabRegistrySyncDirty(false);
        return true;
      };

      const isVocabCompletionRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : source;
        return Boolean(
          source.complete ||
          source.vocabComplete ||
          source.lessonComplete ||
          source.lessonCompletionSent ||
          state.complete ||
          state.vocabComplete ||
          state.lessonComplete ||
          state.lessonCompletionSent
        );
      };

      const isVocabRegistryReadyRecord = (record = null) => {
        return isVocabCompletionRecord(record);
      };

      const writeVocabLearnedSyncRecord = (record = null, options = {}) => {
        const sourceRecord = record && typeof record === "object" ? record : null;
        const state = sourceRecord && sourceRecord.state && typeof sourceRecord.state === "object" ? sourceRecord.state : vocabProgressSnapshot();
        const registryReady = Boolean(options.force || isVocabCompletionRecord(sourceRecord || { state }));
        if (!registryReady) {
          return false;
        }
        const identity = clean((sourceRecord && sourceRecord.identity) || state.identity || currentVocabProgressCache.identity);
        if (!identity) {
          return false;
        }
        const learnedKeys = Array.isArray(state.learned) ? state.learned.map(clean).filter(Boolean) : Array.from(vocabLearnedKeys);
        const learnedWords = vocabLearnedWordRecordsFrom(
          learnedKeys,
          vocabItems,
          Array.isArray(state.learnedWords) ? state.learnedWords : (Array.isArray(state.learned_words) ? state.learned_words : []),
        );
        if (!learnedWords.length) {
          return false;
        }
        const key = vocabSyncStorageKey(identity);
        const existing = readSpaceWJson(key) || {};
        const mergedWords = mergeVocabSyncWords(existing.words, learnedWords);
        const existingSignature = vocabSyncWordsSignature(existing.words);
        const nextSignature = vocabSyncWordsSignature(mergedWords);
        const savedAt = clean((sourceRecord && sourceRecord.savedAt) || state.savedAt || new Date().toISOString());
        if (existingSignature && existingSignature === nextSignature) {
          if (!isVocabCompletionRecord(existing)) {
            const written = writeSpaceWJson(key, {
              ...existing,
              version: 1,
              identity: clean(existing.identity || identity),
              path: clean(existing.path || vocabServerPathFromRecord(sourceRecord || { state })).replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
              title: clean(existing.title || (sourceRecord && sourceRecord.title) || state.title || currentLessonSource.title || currentLessonSource.name || "Space_V"),
              complete: true,
              registryReady: true,
              vocabComplete: true,
              lessonComplete: true,
              words: mergedWords,
              savedAt,
              updatedAt: new Date().toISOString(),
            });
            if (written) {
              setVocabRegistrySyncDirty(true);
            }
            return written;
          }
          const existingRecord = normalizeVocabSyncRecordForSend({
            ...existing,
            identity: clean(existing.identity || identity),
            words: existing.words,
          });
          const needsSync = existingRecord ? !vocabSyncRecordIsFresh(existingRecord) : false;
          if (needsSync) {
            setVocabRegistrySyncDirty(true);
          }
          return needsSync;
        }
        const payload = {
          version: 1,
          identity,
          path: vocabServerPathFromRecord(sourceRecord || { state }),
          title: clean((sourceRecord && sourceRecord.title) || state.title || currentLessonSource.title || currentLessonSource.name || "Space_V"),
          complete: true,
          registryReady: true,
          vocabComplete: true,
          lessonComplete: true,
          words: mergedWords,
          savedAt,
          updatedAt: new Date().toISOString(),
        };
        const written = writeSpaceWJson(key, payload);
        if (written) {
          setVocabRegistrySyncDirty(true);
        }
        return written;
      };

      const vocabStorageOwnerFromKey = (key = "", prefix = "") => {
        const lead = `${prefix}:`;
        if (!String(key || "").startsWith(lead)) {
          return "";
        }
        const rest = String(key).slice(lead.length);
        const divider = rest.indexOf(":");
        return divider >= 0 ? clean(rest.slice(0, divider)).toLowerCase() : "";
      };

      const vocabSyncOwnerAliases = () => {
        const aliases = new Set(["guest"]);
        [spaceWUserKey(), currentAuthUsername, authUser && authUser.value].forEach((value) => {
          const key = clean(value).toLowerCase();
          if (key) {
            aliases.add(key);
          }
        });
        return aliases;
      };

      const normalizeVocabSyncRecordForSend = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const words = mergeVocabSyncWords([], source.words);
        const identity = clean(source.identity || "");
        if (!identity || !words.length) {
          return null;
        }
        return {
          version: 1,
          identity,
          path: clean(source.path || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
          title: clean(source.title || "Space_V"),
          complete: isVocabCompletionRecord(source),
          registryReady: isVocabCompletionRecord(source),
          vocabComplete: Boolean(source.vocabComplete || source.complete),
          lessonComplete: Boolean(source.lessonComplete || source.lessonCompletionSent || source.complete),
          words,
          savedAt: clean(source.savedAt || source.updatedAt || ""),
          serverSyncedAt: clean(source.serverSyncedAt || ""),
          serverSyncedUser: clean(source.serverSyncedUser || ""),
          serverSyncedLearned: Math.max(0, Math.floor(Number(source.serverSyncedLearned || 0) || 0)),
        };
      };

      const vocabSyncRecordIsFresh = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const savedAt = clean(source.savedAt || source.updatedAt || "");
        const syncedAt = clean(source.serverSyncedAt || "");
        const syncedUser = clean(source.serverSyncedUser || "").toLowerCase();
        const currentUser = clean(currentAuthUsername || "").toLowerCase();
        const learnedCount = Array.isArray(source.words) ? source.words.length : 0;
        const savedStamp = typeof parseLessonProgressTimestamp === "function" ? parseLessonProgressTimestamp(savedAt) : (Date.parse(savedAt) || 0);
        const syncedStamp = typeof parseLessonProgressTimestamp === "function" ? parseLessonProgressTimestamp(syncedAt) : (Date.parse(syncedAt) || 0);
        return Boolean(
          currentUser &&
          syncedUser === currentUser &&
          syncedAt &&
          (!savedAt || (syncedStamp && syncedStamp >= savedStamp)) &&
          Math.max(0, Number(source.serverSyncedLearned || 0) || 0) >= learnedCount
        );
      };

      const invalidateCupLeaderboardAfterVocabChange = (reloadIfOpen = true, boardType = currentCupType) => {
        const nextType = normalizeCupType(boardType || currentCupType);
        if (nextType) {
          currentCupType = nextType;
        }
        const cacheType = normalizeCupType(cupLeaderboardCache.type || currentCupType);
        const keepWarmRows = cacheType === currentCupType && cupLeaderboardCache && typeof cupLeaderboardCache === "object";
        cupLeaderboardCache = keepWarmRows
          ? { ...cupLeaderboardCache, at: 0, type: currentCupType }
          : { at: 0, type: currentCupType, boards: {}, users: [], viewers: [], myStatuses: {}, chat: [], reactionOptions: [] };
        if (reloadIfOpen && cupModal && cupModal.classList.contains("is-open")) {
          void loadCupLeaderboard(true);
        }
      };

      let vocabCupLeaderboardPrewarmTimer = 0;
      let vocabCupLeaderboardPrewarmLastAt = 0;

      const scheduleVocabCupLeaderboardPrewarm = (delayMs = 1200, options = {}) => {
        const opts = options && typeof options === "object" ? options : {};
        if (!vocabModeActive && !opts.force) {
          return;
        }
        const now = Date.now();
        const minGap = Math.max(3000, Number(opts.minGapMs) || 12000);
        if (!opts.force && now - vocabCupLeaderboardPrewarmLastAt < minGap) {
          return;
        }
        if (vocabCupLeaderboardPrewarmTimer) {
          window.clearTimeout(vocabCupLeaderboardPrewarmTimer);
        }
        vocabCupLeaderboardPrewarmTimer = window.setTimeout(() => {
          vocabCupLeaderboardPrewarmTimer = 0;
          vocabCupLeaderboardPrewarmLastAt = Date.now();
          const prewarm = window.prewarmCupLeaderboard;
          if (typeof prewarm !== "function") {
            return;
          }
          void prewarm({
            scope: clean(opts.scope || "day") || "day",
            type: "space_v",
            force: Boolean(opts.force),
          });
        }, Math.max(0, Number(delayMs) || 0));
      };

      const sendVocabRegistrySyncRecord = async (record = null) => {
        const payload = normalizeVocabSyncRecordForSend(record);
        if (!payload || !authToken) {
          return null;
        }
        const result = await fetchAuthJson("/vocab/registry/sync", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const response = result && result.payload ? result.payload : {};
        if (Array.isArray(response.words)) {
          vocabRegistryWords = response.words
            .map((entry) => ({
              key: normalize(entry.word || entry.key || ""),
              word: clean(entry.word || entry.key || ""),
              meaning: clean(entry.meaning || ""),
              pron: clean(entry.pron || ""),
              type: clean(entry.type || ""),
              count: Number(entry.count || 0) || 0,
              last: clean(entry.last || ""),
            }))
            .filter((entry) => entry.key && entry.word);
          vocabRegistryKeys = new Set(vocabRegistryWords.map((entry) => entry.key));
          const periodSource = response.period_keys && typeof response.period_keys === "object" ? response.period_keys : {};
          vocabRegistryPeriodKeys = {
            day: new Set((Array.isArray(periodSource.day) ? periodSource.day : []).map((key) => normalize(key)).filter(Boolean)),
            week: new Set((Array.isArray(periodSource.week) ? periodSource.week : []).map((key) => normalize(key)).filter(Boolean)),
            month: new Set((Array.isArray(periodSource.month) ? periodSource.month : []).map((key) => normalize(key)).filter(Boolean)),
          };
          vocabRegistryLoaded = true;
          vocabRegistryError = "";
          if (typeof writeVocabRegistryLocalCache === "function") {
            writeVocabRegistryLocalCache({
              ...response,
              words: vocabRegistryWords,
              total_words: Number(response.total_words || (response.vocabulary && response.vocabulary.total_words) || vocabRegistryWords.length) || vocabRegistryWords.length,
              source: "server-sync",
            }, currentAuthUsername || "");
          }
        }
        vocabRegistryTotal = Number(response.total_words || (response.vocabulary && response.vocabulary.total_words) || vocabRegistryTotal || 0) || vocabRegistryTotal;
        if (response.vocabulary || response.total_words) {
          invalidateCupLeaderboardAfterVocabChange(true);
        }
        renderVocabLearnedPanel();
        return response;
      };

      const collectVocabRegistrySyncJobs = () => {
        const jobs = [];
        const aliases = vocabSyncOwnerAliases();
        if (!window.localStorage) {
          return jobs;
        }
        for (let index = 0; index < localStorage.length; index += 1) {
          const key = localStorage.key(index);
          if (!key) {
            continue;
          }
          if (key.startsWith(`${SPACE_V_VOCAB_SYNC_PREFIX}:`)) {
            const owner = vocabStorageOwnerFromKey(key, SPACE_V_VOCAB_SYNC_PREFIX);
            if (owner && !aliases.has(owner)) {
              continue;
            }
            const rawRecord = readSpaceWJson(key);
            if (!isVocabCompletionRecord(rawRecord)) {
              removeSpaceWJson(key);
              continue;
            }
            const record = normalizeVocabSyncRecordForSend(rawRecord);
            if (record && !vocabSyncRecordIsFresh(record)) {
              jobs.push({ key, record, removeOnSuccess: true });
            }
            continue;
          }
          if (key.startsWith(`${SPACE_V_PROGRESS_PREFIX}:`)) {
            const owner = vocabStorageOwnerFromKey(key, SPACE_V_PROGRESS_PREFIX);
            if (owner && !aliases.has(owner)) {
              continue;
            }
            const progress = normalizeVocabProgressRecord(readSpaceWJson(key));
            const state = progress && progress.state && typeof progress.state === "object" ? progress.state : null;
            if (!progress || !state) {
              continue;
            }
            if (!isVocabCompletionRecord(progress)) {
              continue;
            }
            const learnedKeys = Array.isArray(state.learned) ? state.learned.map(clean).filter(Boolean) : [];
            const words = vocabLearnedWordRecordsFrom(
              learnedKeys,
              [],
              Array.isArray(state.learnedWords) ? state.learnedWords : (Array.isArray(state.learned_words) ? state.learned_words : []),
            );
            if (!words.length) {
              continue;
            }
            const record = {
              version: 1,
              identity: progress.identity,
              path: vocabServerPathFromRecord(progress),
              title: progress.title || state.title || "Space_V",
              complete: true,
              registryReady: true,
              vocabComplete: true,
              lessonComplete: true,
              words,
              savedAt: progress.savedAt || state.savedAt || "",
              serverSyncedAt: progress.serverSyncedAt,
              serverSyncedUser: progress.serverSyncedUser,
              serverSyncedLearned: progress.serverSyncedLearned,
            };
            if (!vocabSyncRecordIsFresh(record)) {
              jobs.push({ key, record, removeOnSuccess: false, progressRecord: progress });
            }
          }
        }
        // Added 2026-07-29: coalesce duplicate completion records before the sequential network loop.
        const grouped = new Map();
        jobs.forEach((job) => {
          const record = job && job.record && typeof job.record === "object" ? job.record : {};
          const groupKey = `${clean(record.identity || "").toLowerCase()}|${clean(record.path || "").toLowerCase()}`;
          if (!groupKey || groupKey === "|") {
            return;
          }
          const previous = grouped.get(groupKey);
          if (!previous) {
            grouped.set(groupKey, { ...job, members: [job], record: { ...record, words: mergeVocabSyncWords([], record.words) } });
            return;
          }
          const previousRecord = previous.record && typeof previous.record === "object" ? previous.record : {};
          const previousStamp = typeof parseLessonProgressTimestamp === "function" ? parseLessonProgressTimestamp(previousRecord.savedAt || "") : (Date.parse(previousRecord.savedAt || "") || 0);
          const nextStamp = typeof parseLessonProgressTimestamp === "function" ? parseLessonProgressTimestamp(record.savedAt || "") : (Date.parse(record.savedAt || "") || 0);
          const newest = nextStamp >= previousStamp ? record : previousRecord;
          previous.record = { ...newest, words: mergeVocabSyncWords(previousRecord.words, record.words) };
          previous.members.push(job);
        });
        return Array.from(grouped.values());
      };

      const syncVocabRegistryNow = async (force = false) => {
        if (!authToken || vocabRegistrySyncBusy) {
          return false;
        }
        if (vocabRegistrySyncTimer) {
          window.clearTimeout(vocabRegistrySyncTimer);
          vocabRegistrySyncTimer = 0;
        }
        if (vocabModeActive && vocabItems.length && currentVocabProgressCache.identity) {
          const state = vocabProgressSnapshot();
          writeVocabLearnedSyncRecord({
            version: 1,
            identity: currentVocabProgressCache.identity,
            savedAt: state.savedAt,
            title: state.title,
            nodeIndex: Math.max(0, state.currentIndex),
            nodeCount: vocabItems.length,
            state,
          });
        }
        const jobs = collectVocabRegistrySyncJobs();
        if (!jobs.length && !force) {
          return false;
        }
        vocabRegistrySyncBusy = true;
        let syncedAny = false;
        try {
          for (const job of jobs.slice(0, 120)) {
            const response = await sendVocabRegistrySyncRecord(job.record);
            if (!response) {
              continue;
            }
            if (response.ignored) {
              continue;
            }
            syncedAny = true;
            const syncedAt = new Date().toISOString();
            (Array.isArray(job.members) ? job.members : [job]).forEach((member) => {
              const existing = readSpaceWJson(member.key) || member.progressRecord || member.record || job.record;
              existing.serverSyncedAt = syncedAt;
              existing.serverSyncedUser = clean(currentAuthUsername || "");
              existing.serverSyncedLearned = Array.isArray(job.record.words) ? job.record.words.length : 0;
              if (existing.state && typeof existing.state === "object") {
                existing.state.serverSyncedAt = syncedAt;
              }
              if (member.removeOnSuccess) {
                removeSpaceWJson(member.key);
              } else {
                writeSpaceWJson(member.key, existing);
              }
            });
          }
        } catch (error) {
          if (authToken) {
            scheduleVocabRegistrySync(10000);
          }
          return syncedAny;
        } finally {
          vocabRegistrySyncBusy = false;
        }
        if (syncedAny) {
          setVocabRegistrySyncDirty(false);
          void loadVocabRegistry(true);
        } else if (!jobs.length) {
          setVocabRegistrySyncDirty(false);
        }
        return syncedAny;
      };

      const scheduleVocabRegistrySync = (delayMs = 1200) => {
        if (!authToken) {
          return;
        }
        if (vocabRegistrySyncTimer) {
          window.clearTimeout(vocabRegistrySyncTimer);
        }
        vocabRegistrySyncTimer = window.setTimeout(() => {
          vocabRegistrySyncTimer = 0;
          void syncVocabRegistryNow();
        }, Math.max(80, Number(delayMs) || 1200));
      };

      // Updated 2026-07-03: Space_V autosave writes to the server WAL immediately after learner progress snapshots.
      const SPACE_V_SERVER_AUTOSAVE_MS = 0;
      const SPACE_V_SERVER_AUTOSAVE_MAX_INFLIGHT = 3;

      // Added 2026-07-21: retries reuse one operation ID and identical callbacks do not create autosave churn.
      const vocabProgressSemanticSignature = (state = {}) => {
        const comparable = { ...(state && typeof state === "object" ? state : {}) };
        delete comparable.savedAt;
        delete comparable.syncOperationId;
        return JSON.stringify(comparable);
      };

      const createVocabProgressOperationId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `space-v-${window.crypto.randomUUID()}`;
        }
        return `space-v-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      };

      // Added 2026-07-03: sends Space_V autosaves with a small concurrent window so fast answers do not collapse into one blocked queue.
      const launchVocabServerProgressSync = async (record) => {
        if (!record || !canUseVocabProgressServer()) {
          return;
        }
        vocabServerProgressInFlight += 1;
        try {
          await sendVocabServerProgress(record, record.action || "autosave");
        } catch (error) {
          if (!(error && error.progressOutboxQueued)) {
            pendingVocabServerProgressRecord = record;
          } else {
            scheduleProgressOutboxDrain(progressOutboxRetryMs);
          }
          const now = Date.now();
          if (now - vocabServerProgressLastErrorAt > 5000) {
            vocabServerProgressLastErrorAt = now;
            console.warn("[SPACE_V_PROGRESS] save failed", error);
          }
        } finally {
          vocabServerProgressInFlight = Math.max(0, vocabServerProgressInFlight - 1);
          if (pendingVocabServerProgressRecord && vocabServerProgressInFlight < SPACE_V_SERVER_AUTOSAVE_MAX_INFLIGHT) {
            const nextRecord = pendingVocabServerProgressRecord;
            pendingVocabServerProgressRecord = null;
            window.setTimeout(() => void launchVocabServerProgressSync(nextRecord), 1500);
          }
        }
      };

      // Added 2026-07-03: drains the latest pending Space_V record whenever a concurrent autosave slot is available.
      const drainVocabServerProgressSync = () => {
        if (!pendingVocabServerProgressRecord || vocabServerProgressInFlight >= SPACE_V_SERVER_AUTOSAVE_MAX_INFLIGHT) {
          return;
        }
        const nextRecord = pendingVocabServerProgressRecord;
        pendingVocabServerProgressRecord = null;
        void launchVocabServerProgressSync(nextRecord);
      };

      const queueVocabServerProgressSync = (record = null, delayMs = SPACE_V_SERVER_AUTOSAVE_MS) => {
        if (!record || !canUseVocabProgressServer()) {
          return;
        }
        pendingVocabServerProgressRecord = record;
        if (vocabServerProgressSaveTimer) {
          window.clearTimeout(vocabServerProgressSaveTimer);
          vocabServerProgressSaveTimer = 0;
        }
        const normalizedDelay = Math.max(0, Number(delayMs) || 0);
        vocabServerProgressSaveTimer = window.setTimeout(() => {
          vocabServerProgressSaveTimer = 0;
          drainVocabServerProgressSync();
        }, normalizedDelay);
      };

      // Added 2026-07-21: completion must update durable local progress and both boards before leaderboard/server latency.
      const persistVocabCompletionLocally = (record = null) => {
        const source = record && typeof record === "object" ? record : null;
        const state = source && source.state && typeof source.state === "object" ? source.state : null;
        if (!source || !state || !isVocabCompletionRecord(source)) {
          return null;
        }
        currentVocabProgressCache.savedProgress = source;
        vocabProgressLastSemanticSignature = vocabProgressSemanticSignature(state);
        if (currentVocabProgressCache.progressKey) {
          writeSpaceWJson(currentVocabProgressCache.progressKey, source);
        }
        const progressOverride = vocabProgressOverrideFromRecord(source);
        if (progressOverride) {
          const progressPaths = typeof currentVocabProgressPaths === "function"
            ? currentVocabProgressPaths(source)
            : [currentLessonStudyPath(), currentLessonSource && currentLessonSource.path];
          setLessonProgressOverride(progressPaths, progressOverride, 300000, { force: true });
          rememberLessonVaultProgressPin(progressPaths, progressOverride, 300000);
          if (typeof pinVisibleLessonVaultProgressRing === "function") {
            pinVisibleLessonVaultProgressRing(progressPaths, progressOverride, { retryMs: 120 });
          }
          clearLessonProgressDisplayCaches(progressPaths, "Space_V");
        }
        updateVocabProgressButtons();
        return source;
      };

      const saveVocabProgressNow = (options = {}) => {
        if (vocabProgressSaveTimer) {
          window.clearTimeout(vocabProgressSaveTimer);
          vocabProgressSaveTimer = 0;
        }
          if (!vocabModeActive || !vocabItems.length) {
            return null;
          }
        const state = vocabProgressSnapshot();
        const semanticSignature = vocabProgressSemanticSignature(state);
        if (
          semanticSignature === vocabProgressLastSemanticSignature
          && currentVocabProgressCache.savedProgress
          && currentVocabProgressCache.savedProgress.state
        ) {
          return currentVocabProgressCache.savedProgress;
        }
        state.syncOperationId = createVocabProgressOperationId();
        const learnedCount = Math.max(0, Math.floor(Number(state.learnedCount || (Array.isArray(state.learned) ? state.learned.length : 0)) || 0));
        const record = {
          version: 2,
          action: "autosave",
          identity: currentVocabProgressCache.identity,
          savedAt: state.savedAt,
          title: state.title,
          path: currentVocabServerPath(),
          nodeIndex: Math.max(0, state.currentIndex),
          nodeCount: vocabItems.length,
          learnedCount,
          phase: state.phase,
          syncOperationId: state.syncOperationId,
          pendingServerSync: true,
          state,
        };
        currentVocabProgressCache.savedProgress = record;
        vocabProgressLastSemanticSignature = semanticSignature;
        if (currentVocabProgressCache.progressKey) {
          writeSpaceWJson(currentVocabProgressCache.progressKey, record);
        }
        try {
          const progressOverride = vocabProgressOverrideFromRecord(record);
          if (progressOverride) {
            const progressPaths = typeof currentVocabProgressPaths === "function"
              ? currentVocabProgressPaths(record)
              : [currentLessonStudyPath(), currentLessonSource && currentLessonSource.path];
            setLessonProgressOverride(progressPaths, progressOverride, 300000);
            rememberLessonVaultProgressPin(progressPaths, progressOverride, 300000);
            clearLessonProgressDisplayCaches(progressPaths, "Space_V");
          }
        } catch (error) {
        }
        if (!options || options.queueServerSync !== false) {
          queueVocabServerProgressSync(record, 0);
        }
        try {
          writeVocabLearnedSyncRecord(record);
        } catch (error) {
        }
        return record;
      };

      // Added 2026-07-03: immediately persists critical Space_V checkpoints such as Unlearned Words changes outside the autosave queue.
      const saveVocabProgressCheckpointNow = (action = "checkpoint") => {
        const record = saveVocabProgressNow({ queueServerSync: false });
        if (record) {
          record.action = clean(action || "checkpoint") || "checkpoint";
          queueVocabServerProgressSync(record, 0);
        }
        return record;
      };

      window.__ftFlushSpaceVProgressBeforeBack = async (options = {}) => {
        const record = saveVocabProgressNow({ queueServerSync: false }) || currentVocabProgressCache.savedProgress;
        if (!record) {
          return { ok: true, skipped: true, reason: "no_progress" };
        }
        try {
          record.action = "back";
          await sendVocabServerProgress(record, "back");
          const mergedRecord = currentVocabProgressCache.savedProgress;
          const progress = mergedRecord
            && clean(mergedRecord.identity) === clean(record.identity)
            && mergedRecord.state
            ? mergedRecord
            : record;
          return { ok: true, progress };
        } catch (error) {
          return { ok: true, progress: record, pending: true };
        }
      };

      // Added 2026-06-30: gives Lesson Vault Back an immediate local Space_V progress snapshot before the server POST finishes.
      window.__ftPeekSpaceVProgressBeforeBack = (options = {}) => {
        const record = saveVocabProgressNow({ queueServerSync: false }) || currentVocabProgressCache.savedProgress;
        if (!record) {
          return { ok: true, skipped: true, reason: "no_progress" };
        }
        const progressOverride = vocabProgressOverrideFromRecord(record);
        const progressPaths = typeof currentVocabProgressPaths === "function"
          ? currentVocabProgressPaths(record)
          : [currentLessonStudyPath(), currentLessonSource && currentLessonSource.path];
        return {
          ok: true,
          progress: record,
          progressOverride,
          progressPaths,
          path: vocabServerPathFromRecord(record) || currentVocabServerPath(),
        };
      };

      window.__ftKeepaliveSpaceVProgress = (action = "pagehide") => {
        const record = saveVocabProgressNow() || currentVocabProgressCache.savedProgress;
        if (!record || !authToken) {
          return false;
        }
        try {
          const body = vocabServerProgressPayload(record, action);
          const sourceLabel = clean(action || "keepalive").replace(/[^a-z0-9_-]+/gi, "_").toLowerCase() || "keepalive";
          fetch(`/space-v/progress?client_source=space_v_${encodeURIComponent(sourceLabel)}&response=compact-v1`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${authToken}`,
            },
            body: JSON.stringify(body),
            cache: "no-store",
            keepalive: true,
          }).catch(() => {});
          return true;
        } catch (error) {
          return false;
        }
      };

      const queueVocabProgressSave = (delayMs = 0) => {
        if (!currentVocabProgressCache.identity || !vocabModeActive) {
          return;
        }
        scheduleVocabCupLeaderboardPrewarm(1600);
        scheduleCurrentLessonVaultCacheWarm(1800, { minGapMs: 45000 });
        if (vocabProgressSaveTimer) {
          window.clearTimeout(vocabProgressSaveTimer);
          vocabProgressSaveTimer = 0;
        }
        const normalizedDelay = Math.max(0, Number(delayMs) || 0);
        if (normalizedDelay <= 250) {
          saveVocabProgressNow();
          return;
        }
        vocabProgressSaveTimer = window.setTimeout(saveVocabProgressNow, normalizedDelay);
      };

      const clearSavedVocabProgress = (syncServer = true) => {
        const clearedRecord = currentVocabProgressCache && currentVocabProgressCache.savedProgress;
        if (vocabProgressSaveTimer) {
          window.clearTimeout(vocabProgressSaveTimer);
          vocabProgressSaveTimer = 0;
        }
        if (vocabServerProgressSaveTimer) {
          window.clearTimeout(vocabServerProgressSaveTimer);
          vocabServerProgressSaveTimer = 0;
        }
        pendingVocabServerProgressRecord = null;
        vocabProgressLastSemanticSignature = "";
        const progressPaths = typeof currentVocabProgressPaths === "function"
          ? currentVocabProgressPaths(currentVocabProgressCache.savedProgress || {})
          : [currentLessonStudyPath(), currentLessonSource && currentLessonSource.path];
        if (currentVocabProgressCache.progressKey) {
          removeSpaceWJson(currentVocabProgressCache.progressKey);
        }
        currentVocabProgressCache.savedProgress = null;
        clearLessonProgressOverride(progressPaths);
        clearLessonProgressDisplayCaches(progressPaths, "Space_V");
        updateVocabProgressButtons();
        if (syncServer) {
          return clearVocabServerProgress(clearedRecord);
        }
        return Promise.resolve(null);
      };

      const resetSpaceWCache = () => {
        if (spaceWProgressSaveTimer) {
          window.clearTimeout(spaceWProgressSaveTimer);
          spaceWProgressSaveTimer = 0;
        }
        if (spaceWServerProgressSaveTimer) {
          window.clearTimeout(spaceWServerProgressSaveTimer);
          spaceWServerProgressSaveTimer = 0;
        }
        pendingSpaceWServerProgressRecord = null;
        currentSpaceWCache = { identity: "", progressKey: "", voiceKey: "", voiceValue: "", voiceLabel: "", voiceApplied: false, savedProgress: null };
        spaceWNodeProgress = {};
        spaceWAudioPreloadToken += 1;
        if (loadStartButton) {
          loadStartButton.hidden = true;
        }
        updateSpaceWReviewButton();
        updateLoadEnterNowButton();
      };

      const clearSavedSpaceWProgress = (syncServer = true) => {
        const clearedRecord = currentSpaceWCache && currentSpaceWCache.savedProgress;
        const hadSaved = Boolean(currentSpaceWCache && currentSpaceWCache.savedProgress);
        if (currentSpaceWCache && currentSpaceWCache.progressKey) {
          removeSpaceWJson(currentSpaceWCache.progressKey);
          currentSpaceWCache.savedProgress = null;
        }
        spaceWNodeProgress = {};
        updateSpaceWReviewButton();
        if (hadSaved && syncServer) {
          return clearSpaceWServerProgress(clearedRecord);
        }
        return Promise.resolve(null);
      };

      const currentSpaceWServerPath = () => clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");

      const canUseSpaceWProgressServer = () => Boolean(
        authToken &&
        currentAuthUsername &&
        currentSpaceWCache &&
        currentSpaceWCache.identity
      );

      const spaceWServerProgressPayload = (record = {}, action = "") => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const fallbackNodeCount = lessonNodes.length || pendingLessonNodes.length || 0;
        const linkIdentity = linkedLessonProgressIdentity(record, currentSpaceWCache.identity);
        return {
          action,
          path: currentSpaceWServerPath(),
          identity: clean((record && record.identity) || currentSpaceWCache.identity),
          ...linkIdentity,
          title: clean((record && record.title) || currentLessonSource.title || currentLessonSource.name || "Space_W"),
          nodeIndex: Number((record && record.nodeIndex) ?? state.index ?? currentNodeIndex) || 0,
          nodeCount: Number((record && record.nodeCount) ?? state.nodeCount ?? fallbackNodeCount) || 0,
          savedAt: clean((record && record.savedAt) || state.savedAt || new Date().toISOString()),
          syncOperationId: clean((record && (record.syncOperationId || record.sync_operation_id)) || state.syncOperationId || state.sync_operation_id),
          expectedRunId: clean((record && (record.runId || record.run_id)) || state.runId || state.run_id),
          baseRevision: Math.max(0, Math.floor(Number((record && (record._serverRevision || record.serverRevision || record.server_revision)) || 0) || 0)),
          state,
        };
      };

      const mergeSpaceWServerProgressRecord = (record = null) => {
        if (!record || typeof record !== "object") {
          return null;
        }
        const localRecord = currentSpaceWCache && currentSpaceWCache.savedProgress && typeof currentSpaceWCache.savedProgress === "object"
          ? currentSpaceWCache.savedProgress
          : null;
        const canonicalRecord = record.state && typeof record.state === "object"
          ? record
          : (localRecord && localRecord.state && typeof localRecord.state === "object" ? { ...localRecord, ...record, state: { ...localRecord.state } } : null);
        if (!canonicalRecord) {
          return null;
        }
        const recordIdentity = clean(canonicalRecord.identity);
        if (recordIdentity && currentSpaceWCache.identity && recordIdentity !== currentSpaceWCache.identity) {
          return null;
        }
        if (shouldKeepPendingLocalProgress(currentSpaceWCache.savedProgress, canonicalRecord)) {
          scheduleProgressOutboxDrain(150);
          return currentSpaceWCache.savedProgress;
        }
        const mergedRecord = { ...canonicalRecord, pendingServerSync: false };
        currentSpaceWCache.savedProgress = mergedRecord;
        if (currentSpaceWCache.progressKey) {
          writeSpaceWJson(currentSpaceWCache.progressKey, mergedRecord);
        }
        if (typeof spaceWProgressOverrideFromRecord === "function") {
          const progressOverride = spaceWProgressOverrideFromRecord(canonicalRecord);
          if (progressOverride) {
            const progressPaths = [
              typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "",
              typeof currentSpaceWServerPath === "function" ? currentSpaceWServerPath() : "",
              currentLessonSource && currentLessonSource.path,
              currentLessonSource && currentLessonSource.effective_path,
              currentLessonSource && currentLessonSource.link_target,
              currentLessonSource && currentLessonSource.linked_path,
            ].map((path) => normalizeServerPathValue(path || "")).filter(Boolean);
            setLessonProgressOverride(progressPaths, progressOverride, 120000);
            if (typeof rememberLessonVaultProgressPin === "function") {
              rememberLessonVaultProgressPin(progressPaths, progressOverride, 120000);
            }
            if (typeof pinVisibleLessonVaultProgressRing === "function") {
              pinVisibleLessonVaultProgressRing(progressPaths, progressOverride, { retryMs: 120 });
            }
            if (typeof clearLessonProgressDisplayCaches === "function") {
              clearLessonProgressDisplayCaches(progressPaths, "Space_W");
            }
          }
        }
        updateSpaceWReviewButton();
        return mergedRecord;
      };

      const refreshSpaceWServerProgress = async () => {
        if (!canUseSpaceWProgressServer()) {
          return currentSpaceWCache.savedProgress || null;
        }
        const query = new URLSearchParams();
        const pathValue = currentSpaceWServerPath();
        if (pathValue) {
          query.set("path", pathValue);
        }
        query.set("identity", currentSpaceWCache.identity);
        try {
          const cachedRow = currentSpaceWCache.serverPayload && clean(currentSpaceWCache.serverEtag || "")
            ? { payload: currentSpaceWCache.serverPayload, etag: currentSpaceWCache.serverEtag }
            : null;
          const result = await fetchProgressJsonFast(`/space-w/progress?${query.toString()}`, cachedRow);
          const payload = result.payload || {};
          applySpaceWVoicePayload(payload.preferences || {});
          applyAiAgentGhostEnVoicePayload(payload.preferences || {});
          const merged = mergeSpaceWServerProgressRecord(payload.progress || null);
          currentSpaceWCache.serverPayload = payload;
          currentSpaceWCache.serverEtag = clean(result.etag || "");
          return merged || currentSpaceWCache.savedProgress || null;
        } catch (error) {
          return currentSpaceWCache.savedProgress || null;
        }
      };

      const sendSpaceWServerProgress = async (record = null, action = "") => {
        if (!canUseSpaceWProgressServer()) {
          return null;
        }
        const body = spaceWServerProgressPayload(record || currentSpaceWCache.savedProgress || {}, action);
        const outboxRow = enqueueProgressOutboxRequest("space_w", "/space-w/progress?client_source=offline_outbox&response=compact-v1", body, currentSpaceWCache.progressKey);
        let result;
        try {
          result = await fetchAuthJson("/space-w/progress?client_source=space_w_progress_save&response=compact-v1", {
            method: "POST",
            body: JSON.stringify(body),
          });
          if (outboxRow) acknowledgeProgressOutboxRequest(outboxRow, body);
        } catch (error) {
          if (outboxRow) {
            error.progressOutboxQueued = true;
            scheduleProgressOutboxDrain(progressOutboxRetryMs);
          }
          throw error;
        }
        const payload = result.payload || {};
        if (typeof applyVocabularyCompletionDeltaToLocalPreview === "function") {
          applyVocabularyCompletionDeltaToLocalPreview(payload, currentAuthUsername);
        }
        if (payload.progress) {
          mergeSpaceWServerProgressRecord(payload.progress);
        }
        currentSpaceWCache.serverPayload = null;
        currentSpaceWCache.serverEtag = "";
        return payload;
      };

      const clearSpaceWServerProgress = async (record = null) => {
        if (!canUseSpaceWProgressServer()) {
          return null;
        }
        try {
          return await sendSpaceWServerProgress(record || { identity: currentSpaceWCache.identity, state: {} }, "clear");
        } catch (error) {
          return null;
        }
      };

      const queueSpaceWServerProgressSync = (record = null, delayMs = 900) => {
        if (!record || !canUseSpaceWProgressServer()) {
          return;
        }
        pendingSpaceWServerProgressRecord = record;
        if (spaceWServerProgressSaveTimer) {
          window.clearTimeout(spaceWServerProgressSaveTimer);
        }
        spaceWServerProgressSaveTimer = window.setTimeout(async () => {
          spaceWServerProgressSaveTimer = 0;
          if (spaceWServerProgressSyncBusy || !pendingSpaceWServerProgressRecord) {
            if (pendingSpaceWServerProgressRecord) {
              queueSpaceWServerProgressSync(pendingSpaceWServerProgressRecord, 900);
            }
            return;
          }
          const nextRecord = pendingSpaceWServerProgressRecord;
          pendingSpaceWServerProgressRecord = null;
          spaceWServerProgressSyncBusy = true;
          try {
            await sendSpaceWServerProgress(nextRecord);
          } catch (error) {
            if (!(error && error.progressOutboxQueued)) {
              pendingSpaceWServerProgressRecord = nextRecord;
            } else {
              scheduleProgressOutboxDrain(progressOutboxRetryMs);
            }
          } finally {
            spaceWServerProgressSyncBusy = false;
            if (pendingSpaceWServerProgressRecord) {
              queueSpaceWServerProgressSync(pendingSpaceWServerProgressRecord, 1500);
            }
          }
        }, Math.max(120, Number(delayMs) || 900));
      };

      const setCurrentLessonSource = (source = {}, payload = {}) => {
        const next = source && typeof source === "object" ? source : {};
        const payloadLessonId = typeof stableLessonIdFor === "function" ? stableLessonIdFor(payload) : "";
        const lessonId = clean(next.lesson_id || next.lessonId || next.file_id || next.fileId || payloadLessonId);
        currentLessonSource = {
          source: clean(next.source || next.type || ""),
          path: clean(next.path || ""),
          lesson_id: lessonId.toLowerCase().startsWith("ftg-lesson-") ? lessonId : "",
          file_id: lessonId.toLowerCase().startsWith("ftg-lesson-") ? lessonId : "",
          linked_path: clean(next.linked_path || next.alias_path || ""),
          effective_path: clean(next.effective_path || next.effectivePath || ""),
          link_target: clean(next.link_target || next.linkTarget || ""),
          task_owner: clean(next.task_owner || next.taskOwner || serverTaskOwnerContext || currentAuthUsername || ""),
          name: typeof futureFriendlyDisplayName === "function" ? futureFriendlyDisplayName(next.name || "") : clean(next.name || ""),
          title: typeof futureFriendlyDisplayName === "function" ? futureFriendlyDisplayName(next.title || lessonTitleFromPayload(payload)) : clean(next.title || lessonTitleFromPayload(payload)),
          study: next.study || payload.study || null,
        };
        lessonCompletionSent = false;
        completionSyncBusy = false;
      };

      const serverLessonMeta = (entry = {}) => {
        const sizeText = formatServerFileSize(entry.size);
        const study = entry.study && typeof entry.study === "object" ? entry.study : {};
        const userProgress = study.progress && typeof study.progress === "object" ? study.progress : null;
        const userProgressPartial = lessonProgressIsActivePartial(userProgress);
        const userProgressText = userProgressPartial
          ? (typeof lessonCurrentRunProgressLabel === "function"
            ? lessonCurrentRunProgressLabel(study, userProgress)
            : clean(userProgress.text || `${Math.max(0, Math.floor(Number(userProgress.done || 0) || 0))}/${Math.max(0, Math.floor(Number(userProgress.total || 0) || 0))}`))
          : "";
        const mine = typeof lessonStudyCompletedRunCount === "function"
          ? lessonStudyCompletedRunCount(study)
          : (Number(study.mine || study.completedRuns || study.completed_runs || 0) || 0);
        const total = Number(study.total || 0) || 0;
        const adminMine = currentAuthIsAdmin ? (Number(study.admin_mine || 0) || 0) : 0;
        const adminTotal = currentAuthIsAdmin ? (Number(study.admin_total || 0) || 0) : 0;
        const adminProgress = currentAuthIsAdmin && study.admin_progress && typeof study.admin_progress === "object" ? study.admin_progress : null;
        const adminPriorCompletion = currentAuthIsAdmin && adminProgressHasPriorCompletion(study, adminProgress);
        const adminViewerMine = currentAuthIsAdmin ? adminViewerCompletionCount(study) : 0;
        const adminProgressComplete = Boolean(adminProgress && !adminProgress.reviewing && (adminProgress.completed || adminProgress.complete || Number(adminProgress.percent || 0) >= 100));
        if (userProgressPartial) {
          return `${sizeText ? sizeText + " | " : ""}${userProgressText || `${Math.max(0, Math.floor(Number(userProgress.percent || 0) || 0))}%`}`;
        }
        if (mine > 0) {
          return `${sizeText ? sizeText + " | " : ""}${formatLessonTimes(mine)}`;
        }
        if (total > 0) {
          return `${sizeText ? sizeText + " | " : ""}Total ${formatLessonTimes(total)}`;
        }
        if (adminPriorCompletion || adminProgressComplete) {
          return `${sizeText ? sizeText + " | " : ""}Admin ${adminViewerMine ? formatLessonTimes(adminViewerMine) : "learned"}`;
        }
        if (adminProgress) {
          return `${sizeText ? sizeText + " | " : ""}Admin ${clean(adminProgress.text || "") || `${Math.max(0, Math.floor(Number(adminProgress.percent || 0) || 0))}%`}`;
        }
        if (adminMine > 0) {
          return `${sizeText ? sizeText + " | " : ""}Admin ${formatLessonTimes(adminMine)}`;
        }
        if (adminTotal > 0) {
          return `${sizeText ? sizeText + " | " : ""}Admin total ${formatLessonTimes(adminTotal)}`;
        }
        const ext = clean(entry.extension).toLowerCase();
        return sizeText || (ext === ".space_w" ? "Lesson pack" : ((ext === ".space_v" || ext === ".space_b") ? "Vocab pack" : (ext === ".space_q" ? "Question pack" : (ext === ".space_p" ? "Paragraph pack" : (isSpacePictureExtension(ext) ? "Picture" : "Legacy text")))));
      };

      const appendServerInfoChips = (row, entry = {}) => {
        const study = entry.study && typeof entry.study === "object" ? entry.study : {};
        if (entry.type === "folder") {
          const commonFolder = typeof serverEntryIsCommonItem === "function" && serverEntryIsCommonItem(entry);
          row.appendChild(createServerChip(commonFolder || entry.owner === "shared" ? "Common Library" : "Personal Vault", commonFolder || entry.owner === "shared" ? "shared" : "filetype"));
          const folderCount = Number(entry.folder_count || entry.folderCount || 0) || 0;
          const fileCount = Number(entry.file_count || entry.fileCount || 0) || 0;
          const wordCount = Number(entry.word_count || entry.wordCount || 0) || 0;
          const spaceVCount = Number(entry.space_v_file_count || entry.spaceVFileCount || 0) || 0;
          row.appendChild(createServerChip(folderCount ? formatServerCountLabel(folderCount, "folder") : "Folder", "folder-count"));
          if (fileCount) {
            row.appendChild(createServerChip(formatServerCountLabel(fileCount, "file"), "file-count"));
          }
          if (wordCount) {
            row.appendChild(createServerChip(formatServerCountLabel(wordCount, "word"), "word-count"));
          }
          if (spaceVCount && spaceVCount !== fileCount) {
            row.appendChild(createServerChip(`${formatCompactNumber(spaceVCount)} V Pack${spaceVCount === 1 ? "" : "s"}`, "pack-count"));
          }
          return;
        }
        const nodes = Number(study.nodes || entry.nodes || entry.node_count || 0) || 0;
        const mine = typeof lessonStudyCompletedRunCount === "function"
          ? lessonStudyCompletedRunCount(study)
          : (Number(study.mine || study.completedRuns || study.completed_runs || 0) || 0);
        const total = Number(study.total || 0) || 0;
        const adminMine = currentAuthIsAdmin ? (Number(study.admin_mine || 0) || 0) : 0;
        const adminTotal = currentAuthIsAdmin ? (Number(study.admin_total || 0) || 0) : 0;
        const adminProgress = currentAuthIsAdmin && study.admin_progress && typeof study.admin_progress === "object" ? study.admin_progress : null;
        const userProgress = study.progress && typeof study.progress === "object" ? study.progress : null;
        const userProgressPartial = lessonProgressIsActivePartial(userProgress);
        const adminPriorCompletion = currentAuthIsAdmin && adminProgressHasPriorCompletion(study, adminProgress);
        const adminViewerMine = currentAuthIsAdmin ? adminViewerCompletionCount(study) : 0;
        const adminProgressDone = adminProgress
          ? clean(adminProgress.text || "") || `${Math.max(0, Math.floor(Number(adminProgress.percent || 0) || 0))}%`
          : "";
        const adminProgressComplete = Boolean(
          adminProgress &&
          !adminProgress.reviewing &&
          (
            adminProgress.completed ||
            adminProgress.complete ||
            Number(adminProgress.percent || 0) >= 100
          )
        );
        const extension = clean(entry.extension).toLowerCase();
        row.appendChild(createServerChip(extension === ".space_w" ? "W Pack" : ((extension === ".space_v" || extension === ".space_b") ? (extension === ".space_b" ? "B Pack" : "V Pack") : (extension === ".space_q" ? "Q Pack" : (extension === ".space_p" ? "P Pack" : (extension === ".pdf" ? "PDF" : (isSpacePictureExtension(extension) ? "Picture" : "Legacy Text"))))), "filetype"));
          if (extension === ".space_q") {
            const directQuestions = Math.max(0, Math.floor(Number(study.direct_questions || study.directQuestions || entry.direct_questions || 0) || 0));
            const recursiveQuestions = Math.max(0, Math.floor(Number(study.questions || entry.questions || 0) || 0));
            const totalQuestions = Math.max(nodes + recursiveQuestions, Math.floor(Number(study.total_nodes || study.totalNodes || entry.total_nodes || 0) || 0));
            if (nodes) {
              row.appendChild(createServerChip(`${nodes} Topic${nodes === 1 ? "" : "s"}`, "filetype"));
            }
            if (directQuestions) {
              row.appendChild(createServerChip(`${directQuestions} Question${directQuestions === 1 ? "" : "s"}`, "filetype"));
            }
            if (totalQuestions) {
              row.appendChild(createServerChip(`${totalQuestions} Total`, "filetype"));
            }
          } else if (nodes) {
            row.appendChild(createServerChip(`${nodes} Node${nodes === 1 ? "" : "s"}`, "filetype"));
          }
          if ([".space_p", ".space_l", ".space_s"].includes(extension)) {
            const paragraphCount = Math.max(0, Math.floor(Number(study.paragraphs || entry.paragraphs || 0) || 0));
            if (paragraphCount) {
              row.appendChild(createServerChip(`${paragraphCount} Paragraph${paragraphCount === 1 ? "" : "s"}`, "filetype"));
            }
          }
          if (extension === ".space_w") {
            const sentenceCount = Math.max(0, Math.floor(Number(study.sentences || study.sentenceCount || entry.sentences || (userProgress && userProgress.sentenceCount) || 0) || 0));
            const normalSentenceCount = Math.max(0, Math.floor(Number(study.normal_sentences || study.normalSentenceCount || entry.normal_sentences || (userProgress && userProgress.normalSentenceCount) || 0) || 0));
            const trainSentenceCount = Math.max(0, Math.floor(Number(study.train_sentences || study.trainSentenceCount || entry.train_sentences || (userProgress && userProgress.trainSentenceCount) || 0) || 0));
            if (sentenceCount) {
              row.appendChild(createServerChip(`${sentenceCount} Sentence${sentenceCount === 1 ? "" : "s"}`, "filetype"));
            }
            if (normalSentenceCount) {
              row.appendChild(createServerChip(`${normalSentenceCount} Normal`, "filetype"));
            }
            if (trainSentenceCount) {
              row.appendChild(createServerChip(`${trainSentenceCount} Train`, "filetype"));
            }
          }
        const userRunChipLabel = userProgressPartial
          ? (typeof lessonCurrentRunProgressLabel === "function"
            ? lessonCurrentRunProgressLabel(study, userProgress)
            : clean(userProgress.text || `${Math.max(0, Math.floor(Number(userProgress.done || 0) || 0))}/${Math.max(0, Math.floor(Number(userProgress.total || 0) || 0))}`))
          : (currentAuthIsAdmin && study.admin_view
          ? (mine ? `User ${formatLessonTimes(mine)}` : "User New Run")
          : (mine ? formatLessonTimes(mine) : "New Run"));
        row.appendChild(createServerChip(userRunChipLabel, userProgressPartial ? "total" : (mine ? "learned" : "")));
        if (userProgressPartial && mine > 0) {
          row.appendChild(createServerChip(formatLessonTimes(mine), "learned"));
        }
        if (userProgressPartial && typeof lessonCurrentRunNodeChipLabel === "function") {
          const nodeChip = lessonCurrentRunNodeChipLabel(userProgress);
          if (nodeChip && nodeChip !== userRunChipLabel) {
            row.appendChild(createServerChip(nodeChip, "node"));
          }
        }
        if (total && total !== mine) {
          row.appendChild(createServerChip(`Total ${formatLessonTimes(total)}`, "total"));
        }
        if (!userProgressPartial && (adminPriorCompletion || adminProgressComplete)) {
          row.appendChild(createServerChip(adminViewerMine ? `Admin ${formatLessonTimes(adminViewerMine)}` : "Admin Learned", "admin learned"));
          if (adminProgress && !adminProgressComplete && adminProgressDone) {
            row.appendChild(createServerChip(`Admin run ${adminProgressDone}`, "admin"));
          }
        } else if (!userProgressPartial && adminProgress) {
          row.appendChild(createServerChip(`Admin ${adminProgressDone}`, "admin"));
        } else if (!userProgressPartial && adminMine) {
          row.appendChild(createServerChip(`Admin ${formatLessonTimes(adminMine)}`, "admin learned"));
        } else if (!userProgressPartial && adminTotal) {
          row.appendChild(createServerChip(`Admin total ${formatLessonTimes(adminTotal)}`, "admin"));
        } else if (!userProgressPartial && currentAuthIsAdmin && study.admin_view) {
          row.appendChild(createServerChip("Admin view", "admin"));
        }
        appendLessonTimeChip(row, study);
        if (!(Number(study.time_seconds || (study.time && study.time.seconds) || 0) > 0) && typeof lessonVaultTimePinForPaths === "function") {
          const pinnedTime = lessonVaultTimePinForPaths([
            entry.path,
            entry.effective_path,
            entry.link_target,
            entry.linked_path,
            entry.source_path,
            entry.original_path,
          ]);
          const pinnedSeconds = Number(pinnedTime && (pinnedTime.seconds || pinnedTime.time_seconds || 0)) || 0;
          if (pinnedSeconds > 0) {
            row.appendChild(createServerChip(`Time ${formatStudyDuration(pinnedSeconds)}`, "time"));
          }
        }
        const last = shortStudyDate(study.mine_last || study.last);
        if (last) {
          row.appendChild(createServerChip(`Recent ${last}`, "date"));
        }
      };

      let serverTaskOwnerContext = "";
      let currentTaskPayload = { task_owner: "", tasks: [], admin: false };
      let taskBoardMode = "space";
      let taskNoticeEditId = "";
      let taskNoticeAdminOpen = false;
      let taskNoticeVoiceRows = { vi: [], en: [] };
      let taskUserNoticeQueue = [];
      let taskUserNoticePlaying = false;
      let taskUserNoticeToken = 0;
      let taskNoticeFaceGazeTimer = 0;
      let taskNoticeFaceScene = null;
      let taskNoticeReturnTriggerId = 0;
      let pendingTaskNoticeReturnTrigger = null;
      let completedLessonReturnsSinceTaskNotice = 0;
      let taskNoticeImmediatePollTimer = 0;
      let taskNoticeImmediatePollInFlight = false;
      let taskNoticeImmediateLastId = 0;
      let taskNoticeImmediatePrimed = false;
      let taskNoticeImmediateLastPollAt = 0;
      const TASK_NOTICE_IMMEDIATE_ACTIVE_MS = 60000;
      const TASK_NOTICE_IMMEDIATE_HIDDEN_MS = 180000;
      let latestReplayableTaskNotice = null;
      const taskUserNoticeShownThisSession = new Set();
      const lessonTaskPanelCache = new Map();
      // Added 2026-07-22: coalesces duplicate login/task-board reads for the same authenticated owner.
      const lessonTaskPanelInflight = new Map();
      // Updated 2026-07-22: discard pre-PDF-first task payloads once so deleted/stale rows cannot survive in local cache.
      const LESSON_TASK_PANEL_CACHE_SCHEMA_VERSION = 3;
      const LESSON_TASK_PANEL_CACHE_TTL_MS = 30000;
      const LESSON_TASK_PANEL_REFRESH_MIN_MS = 10000;
      let serverBrowserActivePanel = "vault";
      let serverVaultVisibilityObserver = null;
      let serverVaultVisibilityFrame = 0;
      let serverVaultVisibilityCleanup = null;

      const lessonTaskPanelCacheKey = (owner = "") => [
        clean(currentAuthUsername || ""),
        currentAuthIsAdmin ? "admin" : "user",
        clean(owner || ""),
      ].join("|");
      // Added 2026-07-15: persists the login Space Task baseline so Back/reload can render without a server GET.
      const lessonTaskPanelLocalCacheKey = (owner = "") => serverStorageKey(`lesson-task-panel:${lessonTaskPanelCacheKey(owner)}`);

      const getLessonTaskPanelCacheRow = (owner = "") => {
        const key = lessonTaskPanelCacheKey(owner);
        const row = lessonTaskPanelCache.get(key);
        if (row && row.payload && Date.now() - Number(row.at || 0) <= LESSON_TASK_PANEL_CACHE_TTL_MS) {
          return row;
        }
        if (row) {
          lessonTaskPanelCache.delete(key);
        }
        try {
          const raw = window.localStorage ? localStorage.getItem(lessonTaskPanelLocalCacheKey(owner)) : "";
          const localRow = raw ? JSON.parse(raw) : null;
          if (
            localRow &&
            Number(localRow.schema_version || 0) === LESSON_TASK_PANEL_CACHE_SCHEMA_VERSION &&
            localRow.payload && typeof localRow.payload === "object"
          ) {
            const cached = {
              at: Number(localRow.at || 0) || Date.now(),
              payload: localRow.payload,
              etag: clean(localRow.etag || ""),
              schema_version: LESSON_TASK_PANEL_CACHE_SCHEMA_VERSION,
              local: true,
            };
            lessonTaskPanelCache.set(key, cached);
            return cached;
          }
          if (localRow && window.localStorage) {
            localStorage.removeItem(lessonTaskPanelLocalCacheKey(owner));
          }
        } catch (error) {}
        return null;
      };

      const rememberLessonTaskPanelCache = (owner = "", payload = null, etag = "") => {
        if (!payload || typeof payload !== "object") {
          return;
        }
        const spaceTask = payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        if (spaceTask.pending) {
          return;
        }
        lessonTaskPanelCache.set(lessonTaskPanelCacheKey(owner), {
          at: Date.now(),
          payload,
          etag: clean(etag || ""),
          schema_version: LESSON_TASK_PANEL_CACHE_SCHEMA_VERSION,
        });
        try {
          if (window.localStorage) {
            localStorage.setItem(lessonTaskPanelLocalCacheKey(owner), JSON.stringify({
              schema_version: LESSON_TASK_PANEL_CACHE_SCHEMA_VERSION,
              at: Date.now(),
              payload,
              etag: clean(etag || ""),
            }));
          }
        } catch (error) {}
      };

      const clearLessonTaskPanelCache = () => {
        lessonTaskPanelCache.clear();
      };

      // Added 2026-07-23: task mutations invalidate only the selected learner.
      const clearLessonTaskPanelCacheForOwner = (owner = "") => {
        const target = clean(owner || "");
        if (!target) {
          clearLessonTaskPanelCache();
          return;
        }
        lessonTaskPanelCache.delete(lessonTaskPanelCacheKey(target));
      };

      const setServerVaultItemViewportState = (item, visible) => {
        if (!item) {
          return;
        }
        const active = Boolean(visible);
        item.classList.toggle("is-vault-visible", active);
        item.classList.toggle("is-vault-inert", !active);
      };

      const serverVaultItemIsNearViewport = (item, margin = 180) => {
        if (!serverListNode || !item) {
          return true;
        }
        const rootRect = serverListNode.getBoundingClientRect();
        const itemRect = item.getBoundingClientRect();
        return itemRect.bottom >= rootRect.top - margin && itemRect.top <= rootRect.bottom + margin;
      };

      const disconnectServerVaultVisibilityObserver = () => {
        if (serverVaultVisibilityObserver) {
          try {
            serverVaultVisibilityObserver.disconnect();
          } catch (error) {
          }
          serverVaultVisibilityObserver = null;
        }
        if (serverVaultVisibilityCleanup) {
          try {
            serverVaultVisibilityCleanup();
          } catch (error) {
          }
          serverVaultVisibilityCleanup = null;
        }
      };

      const refreshServerVaultVisibility = () => {
        if (!serverListNode) {
          return;
        }
        if (serverVaultVisibilityFrame) {
          window.cancelAnimationFrame(serverVaultVisibilityFrame);
          serverVaultVisibilityFrame = 0;
        }
        disconnectServerVaultVisibilityObserver();
        const items = Array.from(serverListNode.querySelectorAll(".ft-server-item"));
        if (!items.length) {
          return;
        }
        const warmMargin = 180;
        items.forEach((item) => setServerVaultItemViewportState(item, serverVaultItemIsNearViewport(item, warmMargin)));
        if (typeof IntersectionObserver !== "function") {
          let fallbackFrame = 0;
          const updateFallbackVisibility = () => {
            fallbackFrame = 0;
            items.forEach((item) => setServerVaultItemViewportState(item, serverVaultItemIsNearViewport(item, warmMargin)));
          };
          const scheduleFallbackVisibility = () => {
            if (fallbackFrame) {
              return;
            }
            fallbackFrame = window.requestAnimationFrame(updateFallbackVisibility);
          };
          serverListNode.addEventListener("scroll", scheduleFallbackVisibility, { passive: true });
          window.addEventListener("resize", scheduleFallbackVisibility, { passive: true });
          serverVaultVisibilityCleanup = () => {
            if (fallbackFrame) {
              window.cancelAnimationFrame(fallbackFrame);
              fallbackFrame = 0;
            }
            serverListNode.removeEventListener("scroll", scheduleFallbackVisibility);
            window.removeEventListener("resize", scheduleFallbackVisibility);
          };
          updateFallbackVisibility();
          return;
        }
        serverVaultVisibilityObserver = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            setServerVaultItemViewportState(entry.target, Boolean(entry.isIntersecting || entry.intersectionRatio > 0));
          });
        }, {
          root: serverListNode,
          rootMargin: `${warmMargin}px 0px ${warmMargin}px 0px`,
          threshold: 0.01,
        });
        items.forEach((item) => serverVaultVisibilityObserver.observe(item));
      };

      const scheduleServerVaultVisibilityRefresh = () => {
        if (serverVaultVisibilityFrame) {
          window.cancelAnimationFrame(serverVaultVisibilityFrame);
        }
        serverVaultVisibilityFrame = window.requestAnimationFrame(() => {
          serverVaultVisibilityFrame = 0;
          refreshServerVaultVisibility();
        });
      };

      const serverBrowserPanelAvailable = (panel = "vault") => {
        const key = clean(panel || "vault").toLowerCase();
        if (key === "notice") {
          return false;
        }
        return key === "vault" || key === "task";
      };

      const setServerBrowserPanel = (panel = "vault") => {
        if (!serverBrowserLayout) {
          return;
        }
        let key = clean(panel || "vault").toLowerCase();
        if (!serverBrowserPanelAvailable(key)) {
          key = "vault";
        }
        serverBrowserActivePanel = key;
        serverBrowserLayout.dataset.activePanel = key;
        serverBrowserLayout.classList.toggle("is-panel-vault", key === "vault");
        serverBrowserLayout.classList.toggle("is-panel-task", key === "task");
        serverBrowserLayout.classList.toggle("is-panel-notice", key === "notice");
        serverBrowserTabButtons.forEach((button) => {
          const active = button.dataset.serverPanel === key;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        if (key === "task") {
          scheduleLearningStatsMotionCycle(1000);
          window.setTimeout(() => scheduleLearningStatsMotionCycle(1000), 180);
        } else {
          clearLearningStatsMotionCycle();
        }
      };

      const syncServerBrowserTabs = () => {
        if (!serverBrowserLayout) {
          return;
        }
        if (serverBrowserNoticeTab) {
          serverBrowserNoticeTab.hidden = true;
        }
        if (!serverBrowserPanelAvailable(serverBrowserActivePanel)) {
          serverBrowserActivePanel = "vault";
        }
        setServerBrowserPanel(serverBrowserActivePanel);
      };

      const taskNoticeVietnameseTranslation = (notice = {}) => preserveQuestionText(
        notice.translation_vi || notice.translationVi || notice.vietnamese || notice.vi || ""
      );

      const taskNoticeEnglishTranslation = (notice = {}) => preserveQuestionText(
        notice.translation_en || notice.translationEn || notice.english || notice.en || ""
      );

      const estimateNoticeTokenCount = (text = "") => {
        const value = clean(text);
        if (!value) return 0;
        const parts = value.match(/[A-Za-z0-9']+|[^\sA-Za-z0-9]/g);
        return Math.max(1, Math.ceil((parts ? parts.length : value.length / 4) * 1.18));
      };

      const formatAiRequestTime = (ms = 0) => {
        const value = Math.max(0, Number(ms) || 0);
        if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}s`;
        return `${Math.round(value)}ms`;
      };

      const setAiRingValue = (node, value = 0) => {
        if (!node) return;
        node.style.setProperty("--p", `${Math.max(0, Math.min(100, Number(value) || 0))}%`);
      };

      const updateTaskAiNoticeHud = (notice = {}, englishText = "", vietnameseText = "") => {
        if (!taskAiMetricMeters.length) return;
        const isAiNotice = Boolean(notice && notice._ai_agent);
        const metrics = notice && typeof notice.ai_agent_metrics === "object" ? notice.ai_agent_metrics : {};
        const inputTokens = Math.max(0, Number(metrics.input_tokens || metrics.inputTokens || 0) || 0) || estimateNoticeTokenCount(notice.user_prompt || notice.prompt || "");
        const outputTokens = Math.max(0, Number(metrics.output_tokens || metrics.outputTokens || 0) || 0) || estimateNoticeTokenCount(englishText || notice.text || "");
        const totalTokens = Math.max(inputTokens + outputTokens, Number(metrics.total_tokens || metrics.totalTokens || 0) || 0, 1);
        taskAiMetricMeters.forEach((meter) => {
          if (!meter) return;
          const meterSide = clean(meter.dataset.aiMeter || "").toLowerCase();
          const showMeter = Boolean(isAiNotice && meterSide !== "en");
          meter.hidden = !showMeter;
          meter.setAttribute("aria-hidden", showMeter ? "false" : "true");
          if (!showMeter) return;
          const inputNode = meter.querySelector("[data-ai-input-tokens]");
          const outputNode = meter.querySelector("[data-ai-output-tokens]");
          const timeNode = meter.querySelector("[data-ai-request-time]");
          if (inputNode) inputNode.textContent = String(inputTokens);
          if (outputNode) outputNode.textContent = String(outputTokens);
          if (timeNode) timeNode.textContent = formatAiRequestTime(metrics.request_ms || metrics.requestMs || 0);
          setAiRingValue(meter.querySelector(".ft-ai-notice-ring.is-input"), (inputTokens / totalTokens) * 100);
          setAiRingValue(meter.querySelector(".ft-ai-notice-ring.is-output"), (outputTokens / totalTokens) * 100);
        });
      };

      const setAiNoticeSaveStatus = (message = "", error = false) => {
        if (!aiNoticeSaveStatus) return;
        aiNoticeSaveStatus.textContent = message;
        aiNoticeSaveStatus.style.color = error ? "#ffc6c6" : "";
      };

      const aiAgentNoticeEnglish = (notice = aiAgentActiveNotice) => taskNoticeEnglishTranslation(notice || {})
        || preserveQuestionText(notice && notice.text || "");

      const aiAgentNoticeVietnamese = (notice = aiAgentActiveNotice) => taskNoticeVietnameseTranslation(notice || "")
        || preserveQuestionText(notice && notice.vietnamese || notice && notice.vi || "");

      const updateAiNoticeSaveButton = () => {
        if (!aiNoticeSaveButton) return;
        const hasTitle = Boolean(preserveQuestionText(aiNoticeSaveTitle && aiNoticeSaveTitle.value || ""));
        aiNoticeSaveButton.disabled = !hasTitle || !aiAgentActiveNotice;
      };

      const renderAiNoticeMemoryControls = (notice = {}) => {
        const isAi = Boolean(notice && notice._ai_agent);
        aiAgentActiveNotice = isAi ? notice : null;
        if (aiNoticeSave) {
          aiNoticeSave.hidden = !isAi;
        }
        if (aiNoticeHistoryButton) {
          aiNoticeHistoryButton.hidden = !isAi;
        }
        if (aiNoticeSaveTitle) {
          aiNoticeSaveTitle.value = "";
          aiNoticeSaveTitle.placeholder = isAi ? "Edit topic title to save this AI answer" : "";
        }
        setAiNoticeSaveStatus(isAi ? "Topic title is required before saving." : "");
        updateAiNoticeSaveButton();
        if (!isAi) {
          closeAiHistoryPanel();
        }
      };

      const closeAiHistoryPanel = () => {
        if (aiHistoryPanel) {
          aiHistoryPanel.classList.add("is-hidden");
          aiHistoryPanel.setAttribute("aria-hidden", "true");
        }
      };

      const selectAiHistoryEntry = (entry = {}) => {
        const id = clean(entry.id || "");
        if (aiHistoryDetailTitle) {
          aiHistoryDetailTitle.textContent = preserveQuestionText(entry.title || "Saved AI answer");
        }
        if (aiHistoryDetailEn) {
          aiHistoryDetailEn.textContent = preserveQuestionText(entry.english || entry.answer_en || "");
          aiHistoryDetailEn.scrollTop = 0;
        }
        if (aiHistoryDetailVi) {
          aiHistoryDetailVi.textContent = preserveQuestionText(entry.vietnamese || entry.answer_vi || "");
          aiHistoryDetailVi.scrollTop = 0;
        }
        if (aiHistoryList) {
          Array.from(aiHistoryList.querySelectorAll(".ft-ai-history-item")).forEach((button) => {
            button.classList.toggle("is-active", clean(button.dataset.historyId || "") === id);
          });
        }
      };

      const renderAiHistoryList = (entries = []) => {
        aiAgentHistoryCache = Array.isArray(entries) ? entries : [];
        if (!aiHistoryList) return;
        aiHistoryList.textContent = "";
        if (!aiAgentHistoryCache.length) {
          const empty = document.createElement("div");
          empty.className = "ft-ai-history-item";
          empty.textContent = "No saved AI answers yet.";
          aiHistoryList.appendChild(empty);
          selectAiHistoryEntry({ title: "Saved AI answers", english: "Save an AI answer with your own topic title first.", vietnamese: "Hãy nhập tiêu đề chủ đề rồi lưu câu trả lời AI trước." });
          return;
        }
        aiAgentHistoryCache.forEach((entry) => {
          const button = document.createElement("button");
          button.className = "ft-ai-history-item";
          button.type = "button";
          button.dataset.historyId = clean(entry.id || "");
          const title = preserveQuestionText(entry.title || "Untitled AI answer");
          const created = preserveQuestionText(entry.created_at || entry.createdAt || "");
          button.textContent = created ? `${title}  ·  ${created.slice(0, 10)}` : title;
          button.addEventListener("click", () => selectAiHistoryEntry(entry));
          aiHistoryList.appendChild(button);
        });
        selectAiHistoryEntry(aiAgentHistoryCache[0]);
      };

      const openAiHistoryPanel = async () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de xem AI history.");
          return;
        }
        if (aiHistoryPanel) {
          aiHistoryPanel.classList.remove("is-hidden");
          aiHistoryPanel.setAttribute("aria-hidden", "false");
        }
        renderAiHistoryList(aiAgentHistoryCache.length ? aiAgentHistoryCache : [{ title: "Loading AI history", english: "Loading saved answers...", vietnamese: "Đang tải lịch sử AI..." }]);
        try {
          const { payload } = await fetchAuthJson("/ai-agent/history?limit=80");
          renderAiHistoryList(Array.isArray(payload.history) ? payload.history : []);
        } catch (error) {
          renderAiHistoryList([{ title: "Could not load history", english: clean(error && error.message || "History unavailable."), vietnamese: "Không tải được lịch sử AI." }]);
        }
      };

      const saveAiNoticeHistory = async () => {
        const title = preserveQuestionText(aiNoticeSaveTitle && aiNoticeSaveTitle.value || "");
        if (!title) {
          setAiNoticeSaveStatus("Edit a topic title first. Untitled answers are not saved.", true);
          if (aiNoticeSaveTitle) aiNoticeSaveTitle.focus({ preventScroll: true });
          return;
        }
        const notice = aiAgentActiveNotice;
        if (!notice) {
          setAiNoticeSaveStatus("No active Ghost AI answer to save.", true);
          return;
        }
        const english = aiAgentNoticeEnglish(notice);
        const vietnamese = aiAgentNoticeVietnamese(notice);
        if (!english && !vietnamese) {
          setAiNoticeSaveStatus("This AI answer has no text to save.", true);
          return;
        }
        if (aiNoticeSaveButton) {
          aiNoticeSaveButton.disabled = true;
          aiNoticeSaveButton.textContent = "Saving";
        }
        setAiNoticeSaveStatus("Saving AI answer...");
        try {
          const context = aiAgentContextPayload();
          const runtime = context && context.runtime && typeof context.runtime === "object" ? context.runtime : {};
          const { payload } = await fetchAuthJson("/ai-agent/history", {
            method: "POST",
            body: JSON.stringify({
              action: "save",
              title,
              english,
              vietnamese,
              user_prompt: preserveQuestionText(notice.user_prompt || ""),
              space: context.space || "",
              file: context.file || context.lesson || "",
              word: preserveQuestionText(runtime.current_vocabulary_word || ""),
              context,
            }),
          });
          const entry = payload.entry || {};
          aiAgentHistoryCache = [entry, ...aiAgentHistoryCache.filter((item) => clean(item.id || "") !== clean(entry.id || ""))].filter((item) => item && clean(item.title || ""));
          setAiNoticeSaveStatus("Saved to AI history.");
          if (aiNoticeSaveTitle) aiNoticeSaveTitle.value = "";
          updateAiNoticeSaveButton();
        } catch (error) {
          setAiNoticeSaveStatus(error && error.message ? error.message : "Could not save AI history.", true);
        } finally {
          if (aiNoticeSaveButton) {
            aiNoticeSaveButton.textContent = "Save";
            updateAiNoticeSaveButton();
          }
        }
      };

      const taskNoticeSetState = (message = "Ready", error = false) => {
        if (!taskNoticeState) {
          return;
        }
        taskNoticeState.textContent = message;
        taskNoticeState.style.color = error ? "#ffc6c6" : "";
      };

      const normalizeTaskNoticeStyle = (value = "") => {
        const style = clean(value).toLowerCase().replace(/[\s_-]+/g, "");
        if (style === "face1" || style === "aiface1") {
          return "face1";
        }
        if (style === "face" || style === "face2" || style === "aiface" || style === "aiface2") {
          return "face";
        }
        return "hologram";
      };

      const taskNoticeStyleLabel = (value = "") => {
        const style = normalizeTaskNoticeStyle(value);
        if (style === "face1") {
          return "AI face 1";
        }
        if (style === "face") {
          return "AI face 2";
        }
        return "Hologram";
      };

      const taskNoticeDefaultEnglishVoice = { key: "kokoro:am_michael", label: "People | Male Michael" };
      const taskNoticeSecondEnglishVoice = { key: "kokoro:am_adam", label: "People | Male Adam" };
      const taskNoticeDefaultVietnameseVoice = { key: "edge:vi-VN-NamMinhNeural", label: "Edge | Vietnamese VN | Nam Minh" };
      const taskNoticeKokoroVietnameseVoices = [
        { key: "kokoro_vi:diem_trinh", label: "Kokoro VI | Diem Trinh" },
        { key: "kokoro_vi:hung_thinh", label: "Kokoro VI | Hung Thinh" },
        { key: "kokoro_vi:mai_linh", label: "Kokoro VI | Mai Linh" },
      ];

      const taskNoticeActiveLanguage = () => (taskNoticeLanguage && taskNoticeLanguage.value === "en") ? "en" : "vi";

      const prioritizeTaskNoticeEnglishVoices = (rows = []) => {
        const source = Array.isArray(rows) ? rows.slice() : [];
        const priorities = [taskNoticeDefaultEnglishVoice, taskNoticeSecondEnglishVoice];
        const out = [];
        priorities.forEach((voice) => {
          const index = source.findIndex((item) => item && item.key === voice.key);
          out.push(index >= 0 ? source.splice(index, 1)[0] : voice);
        });
        source.forEach((item) => {
          if (item && !out.some((voice) => voice.key === item.key)) {
            out.push(item);
          }
        });
        return out;
      };

      const taskNoticeSetActiveLanguage = (language = "vi", options = {}) => {
        const nextLanguage = language === "en" ? "en" : "vi";
        if (taskNoticeLanguage) {
          taskNoticeLanguage.value = nextLanguage;
        }
        if (taskNoticePaneEn) {
          taskNoticePaneEn.classList.toggle("is-active", nextLanguage === "en");
        }
        if (taskNoticePaneVi) {
          taskNoticePaneVi.classList.toggle("is-active", nextLanguage !== "en");
        }
        renderTaskNoticeVoiceSelect();
        if (options.focus) {
          const target = nextLanguage === "en" ? taskNoticeTextEn : taskNoticeTextVi;
          if (target) target.focus();
        }
      };

      const taskNoticeActiveTextNode = () => taskNoticeActiveLanguage() === "en" ? taskNoticeTextEn : taskNoticeTextVi;
      const taskNoticeActiveVoiceNode = () => taskNoticeActiveLanguage() === "en" ? taskNoticeVoiceEn : taskNoticeVoiceVi;

      const syncTaskNoticeLegacyFields = () => {
        const textNode = taskNoticeActiveTextNode();
        const voiceNode = taskNoticeActiveVoiceNode();
        if (taskNoticeText) {
          taskNoticeText.value = preserveQuestionText(textNode ? textNode.value : "");
        }
        if (taskNoticeVoice) {
          taskNoticeVoice.textContent = "";
          const option = document.createElement("option");
          option.value = voiceNode ? voiceNode.value || "" : "";
          option.textContent = voiceNode && voiceNode.options && voiceNode.selectedIndex >= 0
            ? voiceNode.options[voiceNode.selectedIndex].textContent || option.value
            : option.value;
          taskNoticeVoice.appendChild(option);
          taskNoticeVoice.value = option.value;
        }
      };

      const renderTaskNoticeVoiceSelect = () => {
        const viRows = taskNoticeVoiceRows.vi && taskNoticeVoiceRows.vi.length
          ? taskNoticeVoiceRows.vi
          : [taskNoticeDefaultVietnameseVoice, ...taskNoticeKokoroVietnameseVoices];
        renderLearnerVoiceSelect(taskNoticeVoiceEn, prioritizeTaskNoticeEnglishVoices(taskNoticeVoiceRows.en), taskNoticeDefaultEnglishVoice.key, taskNoticeDefaultEnglishVoice.label);
        renderLearnerVoiceSelect(taskNoticeVoiceVi, viRows, taskNoticeDefaultVietnameseVoice.key, taskNoticeDefaultVietnameseVoice.label);
        syncTaskNoticeLegacyFields();
      };

      const loadTaskNoticeVoiceOptions = async () => {
        if ((!taskNoticeVoiceEn && !taskNoticeVoiceVi) || !authToken) {
          return;
        }
        try {
          const result = await fetchSharedChatVoices();
          taskNoticeVoiceRows = {
            vi: Array.isArray(result.payload && result.payload.vi) ? result.payload.vi : [],
            en: Array.isArray(result.payload && result.payload.en) ? result.payload.en : [],
          };
        } catch (error) {
          taskNoticeVoiceRows = { vi: [], en: [] };
        }
        renderTaskNoticeVoiceSelect();
      };

      const translateTaskNoticeText = async (text = "", target = "en", source = "auto") => {
        const body = {
          action: "translate",
          text: preserveQuestionText(text),
          target: target === "vi" ? "vi" : "en",
          source: source === "vi" || source === "en" ? source : "auto",
        };
        const result = await fetchAuthJson("/lesson-task-notices", {
          method: "POST",
          body: JSON.stringify(body),
        });
        return preserveQuestionText(result.payload && (result.payload.translation || result.payload.text || ""));
      };

      const taskNoticeCompareKey = (value = "") => clean(value).toLowerCase().replace(/[\W_]+/g, "");
      const taskNoticeHasVietnameseMarks = (value = "") => /[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(String(value || ""));
      const taskNoticeAssertEnglishTranslation = (source = "", translated = "") => {
        const output = preserveQuestionText(translated);
        if (!output || taskNoticeHasVietnameseMarks(output) || taskNoticeCompareKey(output) === taskNoticeCompareKey(source)) {
          throw new Error("Translation did not return English. Please try again.");
        }
        return output;
      };

      const translateTaskNoticeToEnglish = async (options = {}) => {
        const previousLanguage = taskNoticeActiveLanguage();
        const source = preserveQuestionText(taskNoticeTextVi ? taskNoticeTextVi.value : "");
        if (!source) {
          taskNoticeSetState("Vietnamese message is empty.", true);
          return false;
        }
        if (taskNoticeTranslateEn) taskNoticeTranslateEn.disabled = true;
        taskNoticeSetState("Translating Vietnamese to English...");
        try {
          const translated = taskNoticeAssertEnglishTranslation(source, await translateTaskNoticeText(source, "en", "vi"));
          if (taskNoticeTextEn) taskNoticeTextEn.value = translated;
          if (taskNoticeTextVi) taskNoticeTextVi.value = source;
          if (options.activate !== false) taskNoticeSetActiveLanguage("en");
          else taskNoticeSetActiveLanguage(previousLanguage);
          taskNoticeSetState("English message updated.");
          scheduleTaskNoticeProfilePreferenceSync(0);
          return true;
        } catch (error) {
          taskNoticeSetState(error && error.message ? error.message : "Could not translate to English.", true);
          return false;
        } finally {
          if (taskNoticeTextVi) taskNoticeTextVi.value = source;
          if (taskNoticeTranslateEn) taskNoticeTranslateEn.disabled = false;
        }
      };

      const translateTaskNoticeToVietnamese = async (options = {}) => {
        const previousLanguage = taskNoticeActiveLanguage();
        const source = preserveQuestionText(taskNoticeTextEn ? taskNoticeTextEn.value : "");
        if (!source) {
          taskNoticeSetState("English message is empty.", true);
          return false;
        }
        if (taskNoticeTranslateVi) taskNoticeTranslateVi.disabled = true;
        taskNoticeSetState("Translating English to Vietnamese...");
        try {
          const translated = await translateTaskNoticeText(source, "vi", "en");
          if (taskNoticeTextVi) taskNoticeTextVi.value = translated;
          if (taskNoticeTextEn) taskNoticeTextEn.value = source;
          if (options.activate !== false) taskNoticeSetActiveLanguage("vi");
          else taskNoticeSetActiveLanguage(previousLanguage);
          taskNoticeSetState("Vietnamese message updated.");
          scheduleTaskNoticeProfilePreferenceSync(0);
          return true;
        } catch (error) {
          taskNoticeSetState(error && error.message ? error.message : "Could not translate to Vietnamese.", true);
          return false;
        } finally {
          if (taskNoticeTextEn) taskNoticeTextEn.value = source;
          if (taskNoticeTranslateVi) taskNoticeTranslateVi.disabled = false;
        }
      };

      const ensureTaskNoticeMirrorTranslation = async () => {
        const active = taskNoticeActiveLanguage();
        if (active === "en") {
          return translateTaskNoticeToVietnamese({ activate: false });
        }
        return translateTaskNoticeToEnglish({ activate: false });
      };

      const resetTaskNoticeEditor = () => {
        taskNoticeEditId = "";
        if (taskNoticeTextEn) taskNoticeTextEn.value = taskNoticeProfile.draft_text_en || "";
        if (taskNoticeTextVi) taskNoticeTextVi.value = taskNoticeProfile.draft_text_vi || taskNoticeProfile.draft_text || "";
        if (taskNoticeName) taskNoticeName.value = taskNoticeProfile.speaker_name || "";
        if (taskNoticeAvatar) taskNoticeAvatar.value = taskNoticeProfile.avatar || "";
        taskNoticeSetActiveLanguage(taskNoticeProfile.active_language || "vi");
        if (taskNoticeStyle) taskNoticeStyle.value = normalizeTaskNoticeStyle(taskNoticeProfile.notice_style || "hologram");
        if (taskNoticeOnce) taskNoticeOnce.checked = true;
        if (taskNoticeDay) taskNoticeDay.checked = false;
        if (taskNoticeAlways) taskNoticeAlways.checked = false;
        if (taskNoticeRepeatCount) taskNoticeRepeatCount.value = "0";
        if (taskNoticeBackGap) taskNoticeBackGap.value = "1";
        if (taskNoticeUntilComplete) taskNoticeUntilComplete.checked = false;
        if (taskNoticeAudio) taskNoticeAudio.checked = true;
        if (taskNoticeAck) taskNoticeAck.checked = false;
        if (taskNoticeAdd) taskNoticeAdd.textContent = "Add notice";
        renderTaskNoticeVoiceSelect();
        taskNoticeSetState("Ready");
      };

      const taskNoticeAvatarUrl = (value = "") => {
        const raw = clean(value);
        if (!raw) {
          return "";
        }
        if (/^(https?:|data:|blob:)/i.test(raw)) {
          return raw;
        }
        return serverAssetUrl(raw.replace(/^\/+/, ""));
      };

      const stopTaskNoticeFaceGaze = () => {
        if (taskNoticeFaceGazeTimer) {
          window.clearInterval(taskNoticeFaceGazeTimer);
          taskNoticeFaceGazeTimer = 0;
        }
        if (taskNoticeFaceScene && taskNoticeFaceScene.raf) {
          window.cancelAnimationFrame(taskNoticeFaceScene.raf);
        }
        taskNoticeFaceScene = null;
        if (taskUserNoticeFace) {
          const nativeFrame = taskUserNoticeFace.querySelector("iframe");
          if (nativeFrame && nativeFrame.contentWindow) {
            try {
              nativeFrame.contentWindow.postMessage({ type: "ft-face-destroy" }, "*");
            } catch (error) {
            }
          }
          taskUserNoticeFace.style.removeProperty("--face-rot-x");
          taskUserNoticeFace.style.removeProperty("--face-rot-y");
          taskUserNoticeFace.style.removeProperty("--face-shift-x");
          taskUserNoticeFace.style.removeProperty("--face-shift-y");
          taskUserNoticeFace.classList.remove("is-native-face");
        }
      };

      const startTaskNoticeFaceGaze = (token = taskUserNoticeToken) => {
        if (!taskUserNoticeFace || !taskUserNotice || !taskNoticeFaceScene) {
          return;
        }
        if (taskNoticeFaceGazeTimer) {
          window.clearInterval(taskNoticeFaceGazeTimer);
          taskNoticeFaceGazeTimer = 0;
        }
        const renderLoop = (stamp = 0) => {
          if (token !== taskUserNoticeToken || !taskUserNotice.classList.contains("is-face-style") || !taskUserNotice.classList.contains("is-live")) {
            stopTaskNoticeFaceGaze();
            return;
          }
          if (taskNoticeFaceScene && stamp - taskNoticeFaceScene.lastFrame > 32) {
            taskNoticeFaceScene.lastFrame = stamp;
            taskNoticeFaceScene.render(stamp / 1000, taskUserNotice.classList.contains("is-speaking"));
          }
          if (taskNoticeFaceScene) {
            taskNoticeFaceScene.raf = window.requestAnimationFrame(renderLoop);
          }
        };
        taskNoticeFaceScene.lastFrame = 0;
        taskNoticeFaceScene.raf = window.requestAnimationFrame(renderLoop);
      };

      const postTaskNoticeNativeFaceMessage = (payload = {}) => {
        if (!taskUserNoticeFace || !taskUserNoticeFace.classList.contains("is-native-face")) {
          return;
        }
        const frame = taskUserNoticeFace.querySelector("iframe");
        if (!frame || !frame.contentWindow) {
          return;
        }
        try {
          frame.contentWindow.postMessage(payload, "*");
        } catch (error) {
        }
      };
