

      const startTranslationLessonPayload = async (payload, selectedVoiceValue = "", options = {}) => {
        updateFutureAppRoute("space_w", { replace: futureAppRouteFromLocation() === "lesson_vault" });
        const guardedPath = clean(spaceWVocabBuildGuardPath).replace(/\\/g, "/");
        const activeSourcePath = clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/");
        if (guardedPath && activeSourcePath && guardedPath === activeSourcePath && !options.allowDuringVocabBuild) {
          loadGate.classList.add("is-hidden");
          if (vocabPreflightGate) {
            vocabPreflightGate.hidden = false;
          }
          setVocabPreflightBusy(true, "Vocabulary queue is still building on the server...");
          return false;
        }
        const cleanNodes = normalizeLessonPayloadNodes(payload);
        const nextEffects = normalizeEffectSounds(payload.effects || payload.sounds || payload.fx || {});
        const nextCacheIdentity = spaceWIdentityFor(payload, cleanNodes);
        if (!currentSpaceWCache.progressKey || currentSpaceWCache.identity !== nextCacheIdentity) {
          configureSpaceWCache(payload, cleanNodes);
        }
        loadVoices();
        if (!clean(selectedVoiceValue)) {
          applyCachedSpaceWVoice(true);
        }
        const selectedVoice = clean(selectedVoiceValue || voiceSelect.value);
        if (options.skipAudioPrepare) {
          warmSpaceWAudioCacheForActiveLesson(cleanNodes, selectedVoice, nextEffects, {
            label: "Space_W",
            startIndex: options.startIndex ?? currentNodeIndex,
            startDelayMs: 700,
          });
        } else {
          const prepared = await prepareSpaceWAudioCacheForStart(cleanNodes, selectedVoice, nextEffects, {
            label: "Space_W",
            startIndex: options.startIndex ?? currentNodeIndex,
            fastMode: options.fastMode || "new",
          });
          if (prepared && prepared.canceled) {
            return false;
          }
        }
        try {
          lessonEffects = nextEffects;
          lessonNodes = cleanNodes;
          resetSpaceWTrainMode();
          reviewModeActive = false;
          reviewQueue = [];
          reviewMasteredIndexes = new Set();
          reviewCurrentHadError = false;
          reviewSpeakCompleted = false;
          reviewFinished = false;
          spaceWActiveRunId = `space-w-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
          lessonCompletionSent = false;
          completionSyncBusy = false;
          currentVocabularyMission = null;
          questionModeActive = false;
          setQuestionInventoryHudVisible(false);
          pendingQuestionPayload = null;
          stopQuestionTyping();
          stopQuestionAudio();
          hideQuestionCards();
          if (qRootCard) {
            qRootCard.classList.add("is-hidden");
          }
          vocabModeActive = false;
          setVocabKeyboardLock(false);
          if (vocabCard) {
            vocabCard.classList.add("is-hidden");
          }
          renderVocabLearnedPanel();
          if (vocabLearnedConnector) {
            vocabLearnedConnector.classList.add("is-hidden");
          }
          hideVocabSideCards();
          vocabAudioCacheToken += 1;
          currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(payload);
          pendingVocabularyPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          loadGate.classList.add("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus("");
          setNode(lessonNodes[0], 0);
          applySelectedVoiceValue(selectedVoice);
          rememberCurrentSpaceWVoice();
          saveSpaceWProgressNow();
          warmSpaceWAudioCacheForActiveLesson(lessonNodes, voiceSelect.value, lessonEffects, {
            startIndex: currentNodeIndex,
            startDelayMs: 700,
          });
          closeVoicePicker();
        } catch (error) {
          loadGate.classList.remove("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus(error && error.message ? error.message : "Không mở được giao diện học.", true);
          throw error;
        }
      };

      const readPreloadedServerProgress = async (options = {}, expectedSpace = "") => {
        const promise = options && options.serverProgressPromise;
        if (!promise || typeof promise.then !== "function") {
          return null;
        }
        try {
          const result = await promise;
          if (result && result.failed) {
            return { ok: false, error: result.error };
          }
          const actualSpace = clean(result && result.space);
          const wantedSpace = clean(expectedSpace);
          const paragraphFamily = new Set(["Space_P", "Space_L", "Space_S"]);
          if (!result || (actualSpace !== wantedSpace && !(paragraphFamily.has(actualSpace) && paragraphFamily.has(wantedSpace)))) {
            return null;
          }
          return {
            ok: true,
            payload: result.payload && typeof result.payload === "object" ? result.payload : {},
            etag: clean(result.etag || ""),
          };
        } catch (error) {
          return { ok: false, error };
        }
      };

      const finishPreparedSpaceWLoadDecision = async (options = {}) => {
        const token = ++spaceWLoadDecisionToken;
        const identity = currentSpaceWCache.identity;
        setLoadStatus("Checking saved Space_W progress...");
        if (currentSpaceWCache.savedProgress) {
          const navigation = resolveSpaceRunNavigation(currentSpaceWCache.savedProgress, "Space_W");
          loadGate.classList.add("is-file-ready");
          loadVoices();
          applyCachedSpaceWVoice(true);
          updateVoiceSelectTone();
          updateSpaceWReviewButton();
          if (loadStartButton) {
            loadStartButton.hidden = false;
            loadStartButton.textContent = "New Study";
          }
          const savedWarmIndex = navigation.resumeAvailable ? spaceWSavedStartIndex(currentSpaceWCache.savedProgress) : 0;
          const canTrainReview = pendingSpaceWHasTrainModeNodes() && spaceWSavedProgressAllowsTrainReview(currentSpaceWCache.savedProgress, pendingLessonNodes);
          const actionText = navigation.resumeAvailable
            ? (canTrainReview ? "Select New Study, Continue Previous, or Review Train." : "Select New Study or Continue Previous.")
            : (canTrainReview ? "Completed. Select New Study or Review Train." : "Completed. Select New Study to begin another run.");
          setLoadStatus(`${spaceWSavedSummary(currentSpaceWCache.savedProgress)} ${actionText}`);
          warmSpaceWAudioCache(pendingLessonNodes, voiceSelect.value, {
            loadStatus: false,
            startIndex: savedWarmIndex,
            nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
            maxItems: 2,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
          });
          void readPreloadedServerProgress(options, "Space_W").then((preloaded) => {
            if (!preloaded || !preloaded.ok || token !== spaceWLoadDecisionToken || identity !== currentSpaceWCache.identity) {
              return;
            }
            const payload = preloaded.payload || {};
            applySpaceWVoicePayload(payload.preferences || {});
            applyAiAgentGhostEnVoicePayload(payload.preferences || {});
            mergeSpaceWServerProgressRecord(payload.progress || null);
            currentSpaceWCache.serverPayload = payload;
            currentSpaceWCache.serverEtag = clean(preloaded.etag || "");
            updateSpaceWReviewButton();
          }).catch(() => {});
          return;
        }
        const preloaded = await readPreloadedServerProgress(options, "Space_W");
        if (preloaded && preloaded.ok) {
          const payload = preloaded.payload || {};
          applySpaceWVoicePayload(payload.preferences || {});
          applyAiAgentGhostEnVoicePayload(payload.preferences || {});
          mergeSpaceWServerProgressRecord(payload.progress || null);
          currentSpaceWCache.serverPayload = payload;
          currentSpaceWCache.serverEtag = clean(preloaded.etag || "");
        } else {
          await refreshSpaceWServerProgress();
        }
        if (token !== spaceWLoadDecisionToken || identity !== currentSpaceWCache.identity || !pendingLessonNodes.length) {
          return;
        }
        loadGate.classList.add("is-file-ready");
        loadVoices();
        applyCachedSpaceWVoice(true);
        updateVoiceSelectTone();
        updateSpaceWReviewButton();
        const hasSaved = Boolean(currentSpaceWCache.savedProgress);
        if (loadStartButton) {
          loadStartButton.hidden = !hasSaved;
          loadStartButton.textContent = "New Study";
        }
        if (hasSaved) {
          const navigation = resolveSpaceRunNavigation(currentSpaceWCache.savedProgress, "Space_W");
          const savedWarmIndex = navigation.resumeAvailable ? spaceWSavedStartIndex(currentSpaceWCache.savedProgress) : 0;
          const canTrainReview = pendingSpaceWHasTrainModeNodes() && spaceWSavedProgressAllowsTrainReview(currentSpaceWCache.savedProgress, pendingLessonNodes);
          const actionText = navigation.resumeAvailable
            ? (canTrainReview ? "Select New Study, Continue Previous, or Review Train." : "Select New Study or Continue Previous.")
            : (canTrainReview ? "Completed. Select New Study or Review Train." : "Completed. Select New Study to begin another run.");
          setLoadStatus(`${spaceWSavedSummary(currentSpaceWCache.savedProgress)} ${actionText}`);
          warmSpaceWAudioCache(pendingLessonNodes, voiceSelect.value, {
            loadStatus: false,
            startIndex: savedWarmIndex,
            nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
            maxItems: 2,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
          });
          return;
        }
        const historyNavigation = navigationForLoadedRecord(null, "Space_W");
        if (historyNavigation.lifetimeComplete) {
          if (loadStartButton) {
            loadStartButton.hidden = false;
            loadStartButton.textContent = "New Study";
          }
          if (loadReviewButton) {
            loadReviewButton.hidden = true;
            loadReviewButton.disabled = true;
          }
          setLoadStatus("Completed. Select New Study to begin another run.");
          return;
        }
        setLoadStatus("No saved progress. Select Open New Run.");
        if (loadStartButton) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "Open New Run";
        }
        warmSpaceWAudioCache(pendingLessonNodes, voiceSelect.value, {
          loadStatus: false,
          startIndex: currentNodeIndex,
          nodeLimit: 1,
          maxItems: 1,
          startDelayMs: 900,
        });
        return;
      };

      const finishPreparedVocabLoadDecision = async (normalized = pendingVocabularyPayload, options = {}) => {
        const token = ++vocabLoadDecisionToken;
        const identity = currentVocabProgressCache.identity;
        setLoadStatus("Checking saved Space_V progress...");
        if (currentVocabProgressCache.savedProgress) {
          loadGate.classList.add("is-file-ready");
          updateVocabProgressButtons();
          const navigation = resolveSpaceRunNavigation(currentVocabProgressCache.savedProgress, "Space_V");
          setLoadStatus(`${vocabSavedSummary(currentVocabProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmVocabularyAudioCacheForLesson(normalized || pendingVocabularyPayload, {
            startIndex: navigation.resumeAvailable ? vocabSavedStartIndex(currentVocabProgressCache.savedProgress) : 0,
            label: "Space_V",
            includeAlternates: false,
            includeMeaning: true,
            startDelayMs: 650,
            delayMs: 45,
            status: false,
          });
          // 2026-08-04: keep Gate actions responsive while the click-time progress preload reconciles a newer device checkpoint.
          void readPreloadedServerProgress(options, "Space_V").then((preloaded) => {
            if (!preloaded || !preloaded.ok || token !== vocabLoadDecisionToken || identity !== currentVocabProgressCache.identity) return;
            const payload = preloaded.payload || {};
            mergeVocabServerProgressRecord(payload.progress || null);
            currentVocabProgressCache.serverPayload = payload;
            currentVocabProgressCache.serverEtag = clean(preloaded.etag || "");
            updateVocabProgressButtons();
          }).catch(() => {});
          return;
        }
        const preloaded = await readPreloadedServerProgress(options, "Space_V");
        if (preloaded && preloaded.ok) {
          const payload = preloaded.payload || {};
          mergeVocabServerProgressRecord(payload.progress || null);
          currentVocabProgressCache.serverPayload = payload;
          currentVocabProgressCache.serverEtag = clean(preloaded.etag || "");
          if (payload.vocabulary && Number(payload.vocabulary.total_words || 0)) {
            vocabRegistryTotal = Math.max(vocabRegistryTotal, Number(payload.vocabulary.total_words || 0) || 0);
            vocabRegistryLoaded = false;
          }
        } else {
          await refreshVocabServerProgress();
        }
        if (token !== vocabLoadDecisionToken || identity !== currentVocabProgressCache.identity || !pendingVocabularyPayload) {
          return;
        }
        loadGate.classList.add("is-file-ready");
        updateVocabProgressButtons();
        if (currentVocabProgressCache.savedProgress) {
          const navigation = resolveSpaceRunNavigation(currentVocabProgressCache.savedProgress, "Space_V");
          setLoadStatus(`${vocabSavedSummary(currentVocabProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmVocabularyAudioCacheForLesson(normalized || pendingVocabularyPayload, {
            startIndex: navigation.resumeAvailable ? vocabSavedStartIndex(currentVocabProgressCache.savedProgress) : 0,
            label: "Space_V",
            includeAlternates: false,
            includeMeaning: true,
            startDelayMs: 650,
            delayMs: 45,
            status: false,
          });
          return;
        }
        const historyNavigation = navigationForLoadedRecord(null, "Space_V");
        if (historyNavigation.lifetimeComplete) {
          if (loadStartButton) {
            loadStartButton.hidden = false;
            loadStartButton.textContent = "New Study";
          }
          if (loadReviewButton) {
            loadReviewButton.hidden = true;
            loadReviewButton.disabled = true;
          }
          setLoadStatus("Completed. Select New Study to begin another run.");
          return;
        }
        setLoadStatus("No saved Space_V progress. Select Open New Run.");
        if (loadStartButton) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "Open New Run";
        }
        return;
      };

      const finishPreparedQuestionLoadDecision = async (normalized = pendingQuestionPayload, options = {}) => {
        const token = ++questionLoadDecisionToken;
        const identity = currentQuestionProgressCache.identity;
        setLoadStatus("Checking saved Space_Q progress...");
        if (currentQuestionProgressCache.savedProgress) {
          const navigation = resolveSpaceRunNavigation(currentQuestionProgressCache.savedProgress, "Space_Q");
          loadGate.classList.add("is-file-ready");
          updateQuestionProgressButtons();
          const savedWarmState = normalizeQuestionResumeState(
            currentQuestionProgressCache.savedProgress && currentQuestionProgressCache.savedProgress.state,
            (normalized && normalized.nodes ? normalized.nodes.length : 0) || (pendingQuestionPayload && pendingQuestionPayload.nodes ? pendingQuestionPayload.nodes.length : 0),
          );
          setLoadStatus(`${questionSavedSummary(currentQuestionProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmQuestionAudioCacheForLesson(normalized || pendingQuestionPayload, {
            startIndex: navigation.resumeAvailable ? questionSavedStartIndex(currentQuestionProgressCache.savedProgress) : 0,
            startQuestionIndex: navigation.resumeAvailable && savedWarmState ? Math.max(0, Math.floor(Number(savedWarmState.questionIndex || 0) || 0)) : 0,
            questionOrder: navigation.resumeAvailable && savedWarmState && Array.isArray(savedWarmState.questionOrder) ? savedWarmState.questionOrder : [],
            nodeOrder: navigation.resumeAvailable && savedWarmState ? [savedWarmState.currentIndex, ...savedWarmState.queue] : [],
            label: "Space_Q",
            maxNodes: 1,
            maxTasks: 6,
            includeEffects: false,
            currentQuestionOnly: true,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
            status: false,
          });
          void readPreloadedServerProgress(options, "Space_Q").then((preloaded) => {
            if (!preloaded || !preloaded.ok || token !== questionLoadDecisionToken || identity !== currentQuestionProgressCache.identity) {
              return;
            }
            const payload = preloaded.payload || {};
            mergeQuestionServerProgressRecord(payload.progress || null);
            currentQuestionProgressCache.serverPayload = payload;
            currentQuestionProgressCache.serverEtag = clean(preloaded.etag || "");
            updateQuestionProgressButtons();
          }).catch(() => {});
          return;
        }
        const preloaded = await readPreloadedServerProgress(options, "Space_Q");
        if (preloaded && preloaded.ok) {
          const payload = preloaded.payload || {};
          mergeQuestionServerProgressRecord(payload.progress || null);
          currentQuestionProgressCache.serverPayload = payload;
          currentQuestionProgressCache.serverEtag = clean(preloaded.etag || "");
        } else {
          await refreshQuestionServerProgress();
        }
        if (token !== questionLoadDecisionToken || identity !== currentQuestionProgressCache.identity || !pendingQuestionPayload) {
          return;
        }
        loadGate.classList.add("is-file-ready");
        updateQuestionProgressButtons();
        if (currentQuestionProgressCache.savedProgress) {
          const navigation = resolveSpaceRunNavigation(currentQuestionProgressCache.savedProgress, "Space_Q");
          const savedWarmState = normalizeQuestionResumeState(
            currentQuestionProgressCache.savedProgress && currentQuestionProgressCache.savedProgress.state,
            (normalized && normalized.nodes ? normalized.nodes.length : 0) || (pendingQuestionPayload && pendingQuestionPayload.nodes ? pendingQuestionPayload.nodes.length : 0),
          );
          setLoadStatus(`${questionSavedSummary(currentQuestionProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmQuestionAudioCacheForLesson(normalized || pendingQuestionPayload, {
            startIndex: navigation.resumeAvailable ? questionSavedStartIndex(currentQuestionProgressCache.savedProgress) : 0,
            startQuestionIndex: navigation.resumeAvailable && savedWarmState ? Math.max(0, Math.floor(Number(savedWarmState.questionIndex || 0) || 0)) : 0,
            questionOrder: navigation.resumeAvailable && savedWarmState && Array.isArray(savedWarmState.questionOrder) ? savedWarmState.questionOrder : [],
            nodeOrder: navigation.resumeAvailable && savedWarmState ? [savedWarmState.currentIndex, ...savedWarmState.queue] : [],
            label: "Space_Q",
            maxNodes: 1,
            maxTasks: 6,
            includeEffects: false,
            currentQuestionOnly: true,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
            status: false,
          });
          return;
        }
        const historyNavigation = navigationForLoadedRecord(null, "Space_Q");
        if (historyNavigation.lifetimeComplete) {
          if (loadStartButton) {
            loadStartButton.hidden = false;
            loadStartButton.textContent = "New Study";
          }
          if (loadReviewButton) {
            loadReviewButton.hidden = true;
            loadReviewButton.disabled = true;
          }
          setLoadStatus("Completed. Select New Study to begin another run.");
          return;
        }
        setLoadStatus("No saved Space_Q progress. Select Open New Run.");
        if (loadStartButton) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "Open New Run";
        }
        return;
      };

      const finishPreparedParagraphLoadDecision = async (normalized = pendingParagraphPayload, options = {}) => {
        const token = ++paragraphLoadDecisionToken;
        const identity = currentParagraphProgressCache.identity;
        setLoadStatus("Checking saved Space_P progress...");
        if (currentParagraphProgressCache.savedProgress) {
          const paragraphSpace = isSpaceLPayload(normalized || pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(normalized || pendingParagraphPayload) ? "Space_S" : "Space_P");
          const navigation = resolveSpaceRunNavigation(currentParagraphProgressCache.savedProgress, paragraphSpace);
          loadGate.classList.add("is-file-ready");
          updateParagraphProgressButtons();
          setLoadStatus(`${paragraphSavedSummary(currentParagraphProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmParagraphAudioCacheForLesson(normalized || pendingParagraphPayload, {
            startIndex: navigation.resumeAvailable ? paragraphSavedStartIndex(currentParagraphProgressCache.savedProgress) : 0,
            startChildIndex: navigation.resumeAvailable ? paragraphSavedChildIndex(currentParagraphProgressCache.savedProgress) : 0,
            label: paragraphSpace,
            nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
            maxTasks: LESSON_AUDIO_BACKGROUND_TASK_LIMIT,
            includeEffects: false,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
            status: false,
          });
          void readPreloadedServerProgress(options, "Space_P").then((preloaded) => {
            if (!preloaded || !preloaded.ok || token !== paragraphLoadDecisionToken || identity !== currentParagraphProgressCache.identity) {
              return;
            }
            const payload = preloaded.payload || {};
            mergeParagraphServerProgressRecord(payload.progress || null);
            updateParagraphProgressButtons();
            if (currentParagraphProgressCache.savedProgress) {
              warmParagraphAudioCacheForLesson(normalized || pendingParagraphPayload, {
                startIndex: paragraphSavedStartIndex(currentParagraphProgressCache.savedProgress),
                startChildIndex: paragraphSavedChildIndex(currentParagraphProgressCache.savedProgress),
                label: "Space_P",
                nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
                maxTasks: LESSON_AUDIO_BACKGROUND_TASK_LIMIT,
                includeEffects: false,
                startDelayMs: 600,
                status: false,
              });
            }
          }).catch(() => {});
          return;
        }
        const preloaded = await readPreloadedServerProgress(options, "Space_P");
        if (preloaded && preloaded.ok) {
          const payload = preloaded.payload || {};
          mergeParagraphServerProgressRecord(payload.progress || null);
        } else {
          await refreshParagraphServerProgress();
        }
        if (token !== paragraphLoadDecisionToken || identity !== currentParagraphProgressCache.identity || !pendingParagraphPayload) {
          return;
        }
        loadGate.classList.add("is-file-ready");
        updateParagraphProgressButtons();
        if (currentParagraphProgressCache.savedProgress) {
          const paragraphSpace = isSpaceLPayload(normalized || pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(normalized || pendingParagraphPayload) ? "Space_S" : "Space_P");
          const navigation = resolveSpaceRunNavigation(currentParagraphProgressCache.savedProgress, paragraphSpace);
          setLoadStatus(`${paragraphSavedSummary(currentParagraphProgressCache.savedProgress)} ${navigation.resumeAvailable ? "Select New Study or Continue Previous." : "Completed. Select New Study to begin another run."}`);
          warmParagraphAudioCacheForLesson(normalized || pendingParagraphPayload, {
            startIndex: navigation.resumeAvailable ? paragraphSavedStartIndex(currentParagraphProgressCache.savedProgress) : 0,
            startChildIndex: navigation.resumeAvailable ? paragraphSavedChildIndex(currentParagraphProgressCache.savedProgress) : 0,
            label: paragraphSpace,
            nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
            maxTasks: LESSON_AUDIO_BACKGROUND_TASK_LIMIT,
            includeEffects: false,
            startDelayMs: LESSON_AUDIO_BACKGROUND_START_DELAY_MS,
            status: false,
          });
          return;
        }
        const paragraphHistorySpace = isSpaceLPayload(normalized || pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(normalized || pendingParagraphPayload) ? "Space_S" : "Space_P");
        const historyNavigation = navigationForLoadedRecord(null, paragraphHistorySpace);
        if (historyNavigation.lifetimeComplete) {
          if (loadStartButton) {
            loadStartButton.hidden = false;
            loadStartButton.textContent = "New Study";
          }
          if (loadReviewButton) {
            loadReviewButton.hidden = true;
            loadReviewButton.disabled = true;
          }
          setLoadStatus("Completed. Select New Study to begin another run.");
          return;
        }
        setLoadStatus("No saved Space progress. Select Open New Run.");
        if (loadStartButton) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "Open New Run";
        }
        warmParagraphAudioCacheForLesson(normalized || pendingParagraphPayload, {
          startIndex: 0,
          startChildIndex: 0,
          label: "Space_P",
          nodeLimit: 1,
          maxTasks: LESSON_AUDIO_BACKGROUND_TASK_LIMIT,
          includeEffects: false,
          startDelayMs: 900,
          status: false,
        });
        return;
      };

      const prepareLessonPayloadForGate = (payload, options = {}) => {
        hideActiveLessonSurfaceForLoad("Preparing selected lesson...");
        if (isVocabularyPayload(payload)) {
          setLoadVoiceLock(false);
          resetSpaceWCache();
          resetQuestionMode();
          resetParagraphMode();
          const normalized = normalizeCompactVocabPayload(payload);
          if (!normalized.words.length) {
            throw new Error("File vocabulary chua co tu hop le.");
          }
          pendingVocabularyPayload = normalized;
          configureVocabProgressCache(normalized, normalized.words);
          if (options.serverProgressPromise && typeof options.serverProgressPromise.then === "function") {
            const cacheIdentity = currentVocabProgressCache.identity;
            currentVocabProgressCache.serverProgressSettled = false;
            currentVocabProgressCache.serverProgressResult = null;
            currentVocabProgressCache.serverProgressPromise = Promise.resolve(options.serverProgressPromise).then((result) => {
              if (currentVocabProgressCache.identity === cacheIdentity) {
                currentVocabProgressCache.serverProgressSettled = true;
                currentVocabProgressCache.serverProgressResult = result;
              }
              return result;
            }, (error) => {
              const result = { space: "Space_V", payload: {}, failed: true, error };
              if (currentVocabProgressCache.identity === cacheIdentity) {
                currentVocabProgressCache.serverProgressSettled = true;
                currentVocabProgressCache.serverProgressResult = result;
              }
              return result;
            });
            options = { ...options, serverProgressPromise: currentVocabProgressCache.serverProgressPromise };
          }
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          lessonEffects = normalizeEffectSounds(normalized.effects || {});
          preloadLessonEffectSounds();
          currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(normalized);
          closeVoicePicker();
          if (!options.forceManualStart && shouldAutoStartLoadedFileInPopup() && (isVocabularyPayload(payload) || isQuestionPayload(payload))) {
            setLoadStatus("Da nap file vocabulary. Dang mo Vocabulary card...");
            return;
          }
          loadGate.classList.add("is-file-ready");
          updateVocabProgressButtons();
          if (reloadSessionRestorePending) {
            return;
          }
          void finishPreparedVocabLoadDecision(normalized, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_V.", true);
          });
          return;
        }
        if (isQuestionPayload(payload)) {
          setLoadVoiceLock(false);
          resetSpaceWCache();
          resetQuestionMode();
          resetParagraphMode();
          const normalized = normalizeQuestionPayload(payload);
          if (!normalized.nodes.length) {
            throw new Error("File Space_Q chưa có node Root hợp lệ.");
          }
          configureQuestionProgressCache(normalized, normalized.nodes);
          pendingQuestionPayload = normalized;
          updateQuestionProgressButtons();
          pendingVocabularyPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          lessonEffects = normalizeEffectSounds(normalized.effects || {});
          currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(normalized);
          closeVoicePicker();
          loadGate.classList.add("is-file-ready");
          if (reloadSessionRestorePending) {
            updateQuestionProgressButtons();
            return;
          }
          void finishPreparedQuestionLoadDecision(normalized, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_Q.", true);
          });
          return;
        }
        if (isParagraphPayload(payload)) {
          resetSpaceWCache();
          resetQuestionMode();
          resetParagraphMode();
          const normalized = normalizeParagraphPayload(payload);
          if (!normalized.nodes.length) {
            throw new Error("File Space_P has no valid paragraph node.");
          }
          configureParagraphProgressCache(normalized, normalized.nodes);
          pendingParagraphPayload = normalized;
          pendingVocabularyPayload = null;
          pendingQuestionPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          lessonEffects = normalizeEffectSounds(normalized.effects || {});
          currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(normalized);
          closeVoicePicker();
          setLoadVoiceLock(true, paragraphPayloadVoiceLabel(normalized));
          loadGate.classList.add("is-file-ready");
          if (reloadSessionRestorePending) {
            updateParagraphProgressButtons();
            return;
          }
          void finishPreparedParagraphLoadDecision(normalized, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_P.", true);
          });
          return;
        }
        resetQuestionMode();
        resetParagraphMode();
        setLoadVoiceLock(false);
        pendingVocabularyPayload = null;
        pendingQuestionPayload = null;
        pendingParagraphPayload = null;
        pendingLessonNodes = normalizeLessonPayloadNodes(payload);
        pendingLessonEffects = normalizeEffectSounds(payload.effects || payload.sounds || payload.fx || {});
        configureSpaceWCache(payload, pendingLessonNodes);
        currentSpaceWCache.vocabScanPromise = options.vocabScanPromise && typeof options.vocabScanPromise.then === "function"
          ? options.vocabScanPromise
          : null;
        // 2026-08-03: retain the parallel progress lookup so Continue never starts a duplicate blocking request.
        if (options.serverProgressPromise && typeof options.serverProgressPromise.then === "function") {
          const cacheIdentity = currentSpaceWCache.identity;
          currentSpaceWCache.serverProgressSettled = false;
          currentSpaceWCache.serverProgressResult = null;
          currentSpaceWCache.serverProgressPromise = Promise.resolve(options.serverProgressPromise).then((result) => {
            if (currentSpaceWCache.identity === cacheIdentity) {
              currentSpaceWCache.serverProgressSettled = true;
              currentSpaceWCache.serverProgressResult = result;
            }
            return result;
          }, (error) => {
            const result = { space: "Space_W", payload: {}, failed: true, error };
            if (currentSpaceWCache.identity === cacheIdentity) {
              currentSpaceWCache.serverProgressSettled = true;
              currentSpaceWCache.serverProgressResult = result;
            }
            return result;
          });
          options = { ...options, serverProgressPromise: currentSpaceWCache.serverProgressPromise };
        }
        const firstNode = pendingLessonNodes[0] || null;
        currentNode = firstNode;
        currentNodeIndex = 0;
        if (firstNode) {
          voiceHint = clean(firstNode.voice ?? firstNode.vc ?? voiceHint);
          currentAccent = voiceAccentFromText(voiceHint);
        }
        lessonEffects = pendingLessonEffects;
        loadGate.classList.add("is-file-ready");
        loadVoices();
        applyCachedSpaceWVoice(true);
        updateVoiceSelectTone();
        if (loadStartButton) {
          loadStartButton.hidden = true;
          loadStartButton.textContent = "New Study";
        }
        if (reloadSessionRestorePending) {
          updateSpaceWReviewButton();
          return;
        }
        setLoadStatus("Checking saved Space_W progress...");
        void finishPreparedSpaceWLoadDecision(options);
      };

      const startPreparedLesson = (options = {}) => {
        requestAutoFullscreenForSpaceOpen();
        if (pendingVocabularyPayload || pendingQuestionPayload || pendingParagraphPayload || pendingLessonNodes.length) {
          hideActiveLessonSurfaceForLoad("Opening selected lesson...");
        }
        if (pendingVocabularyPayload) {
          startLessonStudyTimeHeartbeat();
          void enterVocabularyPayloadNow(pendingVocabularyPayload, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_V.", true);
          });
          return;
        }
        if (pendingQuestionPayload) {
          startLessonStudyTimeHeartbeat();
          void enterQuestionPayloadNow(pendingQuestionPayload, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_Q.", true);
          });
          return;
        }
        if (pendingParagraphPayload) {
          startLessonStudyTimeHeartbeat();
          void enterLessonPayloadNow(pendingParagraphPayload, "", options);
          return;
        }
        if (!pendingLessonNodes.length) {
          setLoadStatus("Hãy chọn gói bài học trước.", true);
          return;
        }
        const selectedVoice = voiceSelect.value;
        enterLessonPayloadNow({ nodes: pendingLessonNodes, effects: pendingLessonEffects }, selectedVoice, options);
      };

      const startPreparedLessonNew = async (options = {}) => {
        if (pendingVocabularyPayload && currentVocabProgressCache.savedProgress) {
          await clearSavedVocabProgress(false);
        }
        if (pendingQuestionPayload && currentQuestionProgressCache.progressKey) {
          await clearSavedQuestionProgress(false);
          currentQuestionProgressCache.savedProgress = null;
          pendingQuestionResumeState = null;
        }
        if (pendingParagraphPayload && currentParagraphProgressCache.progressKey && currentParagraphProgressCache.savedProgress) {
          await clearSavedParagraphProgress(false);
        }
        if (pendingParagraphPayload) {
          paragraphNodeIndex = 0;
          paragraphChildIndex = 0;
        }
        if (pendingQuestionPayload && shouldRunSpaceWVocabPreflight(pendingQuestionPayload) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(pendingQuestionPayload, "", {
            ...options,
            forceNewRun: true,
            resumeState: null,
            startIndex: 0,
            reviewRun: false,
          });
          return;
        }
        if (pendingParagraphPayload && shouldRunSpaceWVocabPreflight(pendingParagraphPayload) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(pendingParagraphPayload, "", {
            ...options,
            forceNewRun: true,
            resumeState: null,
            startIndex: 0,
            reviewRun: false,
          });
          return;
        }
        if (pendingLessonNodes.length && currentSpaceWCache.progressKey && currentSpaceWCache.savedProgress) {
          await clearSavedSpaceWProgress(false);
          rememberCurrentSpaceWVoice();
        }
        if (pendingLessonNodes.length) {
          currentNodeIndex = 0;
          currentNode = pendingLessonNodes[0] || null;
          reviewModeActive = false;
          reviewQueue = [];
          reviewMasteredIndexes = new Set();
          reviewCurrentHadError = false;
          reviewSpeakCompleted = false;
          reviewFinished = false;
        }
        if (pendingLessonNodes.length && shouldRunSpaceWVocabPreflight({ nodes: pendingLessonNodes }) && !options.allowDuringVocabBuild) {
          const selectedVoice = clean(voiceSelect && voiceSelect.value);
          void runSpaceWVocabPreflight(
            { nodes: pendingLessonNodes, effects: pendingLessonEffects },
            selectedVoice,
            {
              ...options,
              forceNewRun: true,
              resumeState: null,
              startIndex: 0,
              reviewRun: false,
              vocabScanPromise: currentSpaceWCache.vocabScanPromise,
            },
          );
          return;
        }
        startPreparedLesson({
          ...options,
          forceNewRun: Boolean(pendingVocabularyPayload) || Boolean(pendingQuestionPayload) || Boolean(pendingParagraphPayload) || Boolean(pendingLessonNodes.length) || Boolean(options.forceNewRun),
          resumeState: null,
          startIndex: pendingQuestionPayload ? 0 : options.startIndex,
          reviewRun: false,
        });
      };

      const startSavedVocabProgress = async (options = {}) => {
        const traceStartedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
        const trace = { mode: "Space_V", startedAt: Date.now(), stages: [] };
        const mark = (stage, detail = {}) => {
          const now = typeof performance !== "undefined" ? performance.now() : Date.now();
          trace.stages.push({ stage, ms: Math.round((now - traceStartedAt) * 100) / 100, ...detail });
        };
        const publishTrace = (record = null) => {
          const state = record && record.state && typeof record.state === "object" ? record.state : {};
          trace.learnedCount = Array.isArray(state.learned) ? state.learned.length : Math.max(0, Number(record && record.learnedCount || 0) || 0);
          trace.unlearnedCount = Array.isArray(state.studyIndexes) ? state.studyIndexes.length : 0;
          window.__ftSpaceVContinueTrace = trace;
          console.info("[FTG][SpaceVContinue]", JSON.stringify(trace));
        };
        mark("continue-click");
        if (currentVocabProgressCache.serverPayload && clean(currentVocabProgressCache.serverEtag || "")) {
          mark("progress-cache-hit");
        } else if (currentVocabProgressCache.serverProgressSettled && currentVocabProgressCache.serverProgressResult) {
          const preloaded = await readPreloadedServerProgress({
            serverProgressPromise: Promise.resolve(currentVocabProgressCache.serverProgressResult),
          }, "Space_V");
          if (preloaded && preloaded.ok) {
            const payload = preloaded.payload || {};
            mergeVocabServerProgressRecord(payload.progress || null);
            currentVocabProgressCache.serverPayload = payload;
            currentVocabProgressCache.serverEtag = clean(preloaded.etag || "");
            mark("progress-preload-hit");
          } else {
            mark("progress-preload-failed");
          }
        } else if (currentVocabProgressCache.serverProgressPromise) {
          mark("progress-preload-pending");
        } else if (canUseVocabProgressServer()) {
          await refreshVocabServerProgress();
          mark("progress-direct-refresh");
        } else {
          mark("progress-local-only");
        }
        const record = normalizeVocabProgressRecord(currentVocabProgressCache.savedProgress || readSpaceWJson(currentVocabProgressCache.progressKey));
        const state = record && record.state && typeof record.state === "object" ? record.state : null;
        const navigation = resolveSpaceRunNavigation(record, "Space_V");
        if (!navigation.resumeAvailable) {
          updateVocabProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? "This Space_V run is completed. Select New Study to begin another run." : "No resumable Space_V run is available.", true);
          publishTrace(record);
          return false;
        }
        if (!state || !pendingVocabularyPayload) {
          updateVocabProgressButtons();
          setLoadStatus("No saved Space_V progress is available for this file.", true);
          publishTrace(record);
          return false;
        }
        startLessonStudyTimeHeartbeat();
        const result = await enterVocabularyPayloadNow(pendingVocabularyPayload, {
          ...options,
          resumeState: state,
          skipAudioPrepare: options.skipAudioPrepare,
          deferInitialProgressSave: Boolean(currentVocabProgressCache.serverProgressPromise && !currentVocabProgressCache.serverProgressSettled),
          startIndex: Math.max(0, Math.floor(Number(state.currentIndex || 0) || 0)),
        });
        mark("runtime-ready");
        publishTrace(record);
        return result;
      };

      const startSavedQuestionProgress = async (options = {}) => {
        const record = currentQuestionProgressCache.savedProgress || readSpaceWJson(currentQuestionProgressCache.progressKey);
        const saved = normalizeQuestionProgressRecord(record);
        const savedState = saved && saved.state && typeof saved.state === "object" ? saved.state : null;
        const navigation = resolveSpaceRunNavigation(saved, "Space_Q");
        if (!navigation.resumeAvailable) {
          updateQuestionProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? "This Space_Q run is completed. Select New Study to begin another run." : "No resumable Space_Q run is available.", true);
          return false;
        }
        if (!savedState || !pendingQuestionPayload) {
          updateQuestionProgressButtons();
          setLoadStatus("No saved Space_Q progress is available for this file.", true);
          return false;
        }
        const normalized = normalizeQuestionPayload(pendingQuestionPayload);
        const resumeState = normalizeQuestionResumeState(savedState, normalized.nodes.length);
        if (!resumeState) {
          setLoadStatus("Saved Space_Q progress could not be restored.", true);
          return false;
        }
        warmQuestionAudioCacheForLesson(normalized, {
          label: "Space_Q continue",
          startIndex: resumeState.currentIndex,
          startQuestionIndex: Math.max(0, Math.floor(Number(resumeState.questionIndex || 0) || 0)),
          questionOrder: Array.isArray(resumeState.questionOrder) ? resumeState.questionOrder : [],
          nodeOrder: [resumeState.currentIndex, ...resumeState.queue],
          maxNodes: 1,
          maxTasks: 6,
          includeEffects: false,
          currentQuestionOnly: true,
          startDelayMs: 90,
          delayMs: 70,
          workers: 1,
          status: false,
        });
        currentQuestionProgressCache.savedProgress = saved;
        startLessonStudyTimeHeartbeat();
        if (shouldRunSpaceWVocabPreflight(normalized) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(normalized, "", {
            ...options,
            resumeState,
            startIndex: resumeState.currentIndex,
          });
          return true;
        }
        return enterQuestionPayloadNow(normalized, {
          skipAudioPrepare: true,
          resumeState,
          startIndex: resumeState.currentIndex,
        });
      };

      const startSavedParagraphProgress = async (options = {}) => {
        if (canUseParagraphProgressServer()) {
          await refreshParagraphServerProgress();
        }
        const record = currentParagraphProgressCache.savedProgress || readSpaceWJson(currentParagraphProgressCache.progressKey);
        const saved = normalizeParagraphProgressRecord(record);
        const savedState = saved && saved.state && typeof saved.state === "object" ? saved.state : null;
        const paragraphSpace = isSpaceLPayload(pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(pendingParagraphPayload) ? "Space_S" : "Space_P");
        const navigation = resolveSpaceRunNavigation(saved, paragraphSpace);
        if (!navigation.resumeAvailable) {
          updateParagraphProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? `This ${paragraphSpace} run is completed. Select New Study to begin another run.` : `No resumable ${paragraphSpace} run is available.`, true);
          return false;
        }
        if (!savedState || !pendingParagraphPayload) {
          updateParagraphProgressButtons();
          setLoadStatus("No saved Space_P progress is available for this file.", true);
          return false;
        }
        const normalized = normalizeParagraphPayload(pendingParagraphPayload);
        const resumeState = normalizeParagraphResumeState(savedState, normalized);
        if (!resumeState) {
          setLoadStatus("Saved Space_P progress could not be restored.", true);
          return false;
        }
        currentParagraphProgressCache.savedProgress = saved;
        startLessonStudyTimeHeartbeat();
        if (shouldRunSpaceWVocabPreflight(normalized) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(normalized, "", {
            ...options,
            resumeState,
            startIndex: resumeState.currentIndex,
          });
          return true;
        }
        return enterParagraphPayloadNow(normalized, {
          ...options,
          resumeState,
          startIndex: resumeState.currentIndex,
        });
      };

      const startSavedSpaceWProgress = async (options = {}) => {
        const record = currentSpaceWCache.savedProgress || readSpaceWJson(currentSpaceWCache.progressKey);
        const savedState = record && record.state && typeof record.state === "object" ? record.state : null;
        const navigation = resolveSpaceRunNavigation(record, "Space_W");
        if (!navigation.resumeAvailable) {
          updateSpaceWReviewButton();
          setLoadStatus(navigation.lifetimeComplete ? "This Space_W run is completed. Select New Study to begin another run." : "No resumable Space_W run is available.", true);
          return false;
        }
        if (!savedState || !pendingLessonNodes.length) {
          updateSpaceWReviewButton();
          setLoadStatus("No saved Space_W progress is available for this file.", true);
          return;
        }
        rememberCurrentSpaceWVoice();
        const selected = selectedVoiceCacheRecord();
        const savedIndex = Math.max(0, Number(savedState.index ?? savedState.nodeIndex ?? 0) || 0);
        if (shouldRunSpaceWVocabPreflight({ nodes: pendingLessonNodes }) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(
            { nodes: pendingLessonNodes, effects: pendingLessonEffects },
            selected.value || savedState.selectedVoice || voiceSelect.value,
            {
              ...options,
              resumeSpaceWSaved: true,
              resumeState: savedState,
              startIndex: savedIndex,
              vocabScanPromise: currentSpaceWCache.vocabScanPromise,
            },
          );
          return true;
        }
        if (options.skipAudioPrepare) {
          warmSpaceWAudioCacheForActiveLesson(pendingLessonNodes, selected.value || savedState.selectedVoice || voiceSelect.value, pendingLessonEffects, {
            label: "Space_W review",
            startIndex: savedIndex,
            startDelayMs: 700,
          });
        } else {
          const prepared = await prepareSpaceWAudioCacheForStart(pendingLessonNodes, selected.value || savedState.selectedVoice || voiceSelect.value, pendingLessonEffects, {
            label: "Space_W review",
            startIndex: savedIndex,
            fastMode: "review",
          });
          if (prepared && prepared.canceled) {
            return false;
          }
        }
        const state = {
          ...savedState,
          nodes: pendingLessonNodes,
          effects: pendingLessonEffects,
          lessonSource: { ...(currentLessonSource || {}) },
          selectedVoice: selected.value || savedState.selectedVoice || voiceSelect.value,
          voiceHint: selected.label || savedState.voiceHint || selected.value || voiceHint,
          loadHidden: true,
          deferInitialProgressSave: Boolean(currentSpaceWCache.serverProgressPromise && !currentSpaceWCache.serverProgressSettled),
        };
        const ok = applyRuntimeState(state);
        if (!ok) {
          setLoadStatus("Saved progress could not be restored for this file.", true);
          return;
        }
        currentSpaceWCache.savedProgress = record;
        closeVoicePicker();
        setLoadStatus("");
        startLessonStudyTimeHeartbeat();
        if (!state.deferInitialProgressSave) {
          saveSpaceWProgressNow();
        }
        warmSpaceWAudioCacheForActiveLesson(lessonNodes, voiceSelect.value, lessonEffects, {
          startIndex: currentNodeIndex,
          startDelayMs: 900,
        });
      };

      const startSpaceWTrainReviewFromSaved = async (options = {}) => {
        const record = currentSpaceWCache.savedProgress || readSpaceWJson(currentSpaceWCache.progressKey);
        const savedState = record && record.state && typeof record.state === "object" ? record.state : {};
        if (!pendingLessonNodes.length) {
          updateSpaceWReviewButton();
          setLoadStatus("No Space_W lesson is ready for Train mode.", true);
          return false;
        }
        const cleanNodes = normalizeLessonPayloadNodes({ nodes: pendingLessonNodes });
        const trainNodes = collectSpaceWTrainModeNodesFrom(cleanNodes);
        if (!trainNodes.length) {
          updateSpaceWReviewButton();
          setLoadStatus("This Space_W file does not have Train mode nodes to review.", true);
          return false;
        }
        if (false && !spaceWSavedProgressAllowsTrainReview(record, cleanNodes)) {
          updateSpaceWReviewButton();
          setLoadStatus("Hoàn thành phần root của file này một lần trước khi dùng Review Train.", true);
          return false;
        }
        rememberCurrentSpaceWVoice();
        const selected = selectedVoiceCacheRecord();
        const selectedValue = selected.value || savedState.selectedVoice || voiceSelect.value;
        const nextEffects = normalizeEffectSounds(pendingLessonEffects || savedState.effects || {});
        const previewTrainNodes = trainNodes.map((node, index) => ({
          ...node,
          tr: true,
          trainMode: true,
          __spaceWTrain: true,
          trainBatch: 1,
          trainOrder: index + 1,
        }));
        const previewNodes = cleanNodes.concat(previewTrainNodes);
        if (options.skipAudioPrepare) {
          warmSpaceWAudioCacheForLesson(previewNodes, selectedValue, nextEffects, {
            label: "Space_W train review",
            startIndex: 0,
            includeAllNodes: true,
            includeAllEmbedded: true,
            includeGrammar: true,
            nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
            maxTasks: LESSON_AUDIO_BACKGROUND_TASK_LIMIT,
            startDelayMs: 900,
            delayMs: 180,
            status: false,
          });
        } else {
          const prepared = await prepareSpaceWAudioCacheForStart(previewNodes, selectedValue, nextEffects, {
            label: "Space_W train review",
            startIndex: 0,
            fastMode: "train_review",
          });
          if (prepared && prepared.canceled) {
            return false;
          }
        }
        try {
          stopActiveAudio();
          lessonEffects = nextEffects;
          lessonNodes = cleanNodes.map((node) => ({ ...node }));
          resetSpaceWTrainMode();
          spaceWNodeProgress = savedState.nodeProgress && typeof savedState.nodeProgress === "object"
            ? { ...savedState.nodeProgress }
            : {};
          reviewModeActive = false;
          reviewQueue = [];
          reviewMasteredIndexes = new Set();
          reviewCurrentHadError = false;
          reviewSpeakCompleted = false;
          reviewFinished = false;
          // Added 2026-07-24: Review/Train is stage 2 of the saved run.  Only
          // New Study may allocate a new run identity.
          spaceWActiveRunId = clean(
            record.runId || record.run_id || savedState.runId || savedState.run_id || spaceWActiveRunId,
          ) || `space-w-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
          lessonCompletionSent = Boolean(savedState.lessonCompletionSent);
          completionSyncBusy = false;
          currentVocabularyMission = null;
          questionModeActive = false;
          setQuestionInventoryHudVisible(false);
          pendingQuestionPayload = null;
          stopQuestionTyping();
          stopQuestionAudio();
          hideQuestionCards();
          if (qRootCard) {
            qRootCard.classList.add("is-hidden");
          }
          vocabModeActive = false;
          setVocabKeyboardLock(false);
          if (vocabCard) {
            vocabCard.classList.add("is-hidden");
          }
          renderVocabLearnedPanel();
          if (vocabLearnedConnector) {
            vocabLearnedConnector.classList.add("is-hidden");
          }
          hideVocabSideCards();
          vocabAudioCacheToken += 1;
          pendingVocabularyPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          loadGate.classList.add("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus("");
          currentSpaceWCache.savedProgress = record;
          applySelectedVoiceValue(selectedValue);
          rememberCurrentSpaceWVoice();
          spaceWTrainModeLocked = true;
          const added = expandSpaceWTrainModeNodes();
          if (!added && !spaceWTrainingNodeCount()) {
            throw new Error("This Space_W file does not have Train mode nodes to review.");
          }
          setNode(lessonNodes[0], 0);
          beginReviewMode();
          startLessonStudyTimeHeartbeat();
          saveSpaceWProgressNow();
          warmSpaceWAudioCacheForLesson(lessonNodes, voiceSelect.value, lessonEffects, {
            label: "Space_W train review",
            startIndex: currentNodeIndex,
            includeAllNodes: true,
            includeAllEmbedded: true,
            includeGrammar: true,
            delayMs: 220,
            status: false,
          });
          closeVoicePicker();
          return true;
        } catch (error) {
          loadGate.classList.remove("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus(error && error.message ? error.message : "Could not start Review Train.", true);
          return false;
        }
      };

      const enterLoadedLessonNow = () => {
        if (!hasPendingLoadedLesson()) {
          return;
        }
        requestAutoFullscreenForSpaceOpen();
        const mode = clean(lessonAudioPrepareMode || "start");
        cancelLessonAudioPrepare();
        hideActiveLessonSurfaceForLoad("Entering now. Audio cache will continue in the background.");
        if (pendingVocabularyPayload && resolveSpaceRunNavigation(currentVocabProgressCache.savedProgress, "Space_V").resumeAvailable) {
          void startSavedVocabProgress({ skipAudioPrepare: true }).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not restore saved Space_V progress.", true);
          });
          return;
        }
        if (pendingVocabularyPayload && currentVocabProgressCache.savedProgress) {
          updateVocabProgressButtons();
          return;
        }
        if (pendingVocabularyPayload && navigationForLoadedRecord(null, "Space_V").lifetimeComplete) {
          updateVocabProgressButtons();
          return;
        }
        const pendingParagraphSpace = isSpaceLPayload(pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(pendingParagraphPayload) ? "Space_S" : "Space_P");
        if (pendingParagraphPayload && resolveSpaceRunNavigation(currentParagraphProgressCache.savedProgress, pendingParagraphSpace).resumeAvailable) {
          void startSavedParagraphProgress({ skipAudioPrepare: true }).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not restore saved Space_P progress.", true);
          });
          return;
        }
        if (pendingParagraphPayload && currentParagraphProgressCache.savedProgress) {
          updateParagraphProgressButtons();
          return;
        }
        if (pendingParagraphPayload && navigationForLoadedRecord(null, pendingParagraphSpace).lifetimeComplete) {
          updateParagraphProgressButtons();
          return;
        }
        if (mode === "review") {
          if (resolveSpaceRunNavigation(currentSpaceWCache.savedProgress, "Space_W").resumeAvailable) {
            void startSavedSpaceWProgress({ skipAudioPrepare: true }).catch((error) => {
              setLoadStatus(error && error.message ? error.message : "Could not restore saved progress.", true);
            });
          } else {
            updateSpaceWReviewButton();
          }
          return;
        }
        if (mode === "train_review") {
          if (resolveSpaceRunNavigation(currentSpaceWCache.savedProgress, "Space_W").resumeAvailable) {
            void startSpaceWTrainReviewFromSaved({ skipAudioPrepare: true }).catch((error) => {
              setLoadStatus(error && error.message ? error.message : "Could not start Review Train.", true);
            });
          } else {
            updateSpaceWReviewButton();
          }
          return;
        }
        if (pendingQuestionPayload) {
          const navigation = resolveSpaceRunNavigation(currentQuestionProgressCache.savedProgress, "Space_Q");
          if (navigation.resumeAvailable) {
            void startSavedQuestionProgress({ skipAudioPrepare: true }).catch((error) => {
              setLoadStatus(error && error.message ? error.message : "Could not restore saved Space_Q progress.", true);
            });
          } else if (currentQuestionProgressCache.savedProgress || navigationForLoadedRecord(null, "Space_Q").lifetimeComplete) {
            updateQuestionProgressButtons();
          } else {
            void startPreparedLessonNew({ skipAudioPrepare: true, allowDuringVocabBuild: true, forceNewRun: true }).catch((error) => {
              setLoadStatus(error && error.message ? error.message : "Could not start a new study.", true);
            });
          }
          return;
        }
        if (pendingLessonNodes && pendingLessonNodes.length) {
          const navigation = resolveSpaceRunNavigation(currentSpaceWCache.savedProgress, "Space_W");
          if ((currentSpaceWCache.savedProgress && !navigation.resumeAvailable) || (!currentSpaceWCache.savedProgress && navigationForLoadedRecord(null, "Space_W").lifetimeComplete)) {
            updateSpaceWReviewButton();
            return;
          }
        }
        startPreparedLesson({ skipAudioPrepare: true });
      };

      const continuePreparedLessonFromSavedProgress = async (options = {}) => {
        const traceStartedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
        const trace = { mode: "Space_W", startedAt: Date.now(), stages: [] };
        const mark = (stage) => {
          const now = typeof performance !== "undefined" ? performance.now() : Date.now();
          trace.stages.push({ stage, ms: Math.round((now - traceStartedAt) * 100) / 100 });
        };
        const publishTrace = () => {
          try {
            window.__ftSpaceWContinueTrace = trace;
          } catch (_error) {
          }
        };
        const nextOptions = { skipAudioPrepare: true, ...options };
        if (pendingVocabularyPayload || pendingQuestionPayload || pendingParagraphPayload || pendingLessonNodes.length) {
          hideActiveLessonSurfaceForLoad("Checking saved progress...");
        }
        if (pendingVocabularyPayload) {
          await refreshVocabServerProgress();
          const navigation = navigationForLoadedRecord(currentVocabProgressCache.savedProgress, "Space_V");
          if (navigation.resumeAvailable) {
            return startSavedVocabProgress(nextOptions);
          }
          loadGate.classList.add("is-file-ready");
          updateVocabProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? "Completed. Select New Study to begin another run." : "No resumable Space_V run is available.");
          return false;
        }
        if (pendingQuestionPayload) {
          await refreshQuestionServerProgress();
          const navigation = navigationForLoadedRecord(currentQuestionProgressCache.savedProgress, "Space_Q");
          if (navigation.resumeAvailable) {
            return startSavedQuestionProgress(nextOptions);
          }
          loadGate.classList.add("is-file-ready");
          updateQuestionProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? "Completed. Select New Study to begin another run." : "No resumable Space_Q run is available.");
          return false;
        }
        if (pendingParagraphPayload) {
          await refreshParagraphServerProgress();
          const paragraphSpace = isSpaceLPayload(pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(pendingParagraphPayload) ? "Space_S" : "Space_P");
          const navigation = navigationForLoadedRecord(currentParagraphProgressCache.savedProgress, paragraphSpace);
          if (navigation.resumeAvailable) {
            return startSavedParagraphProgress(nextOptions);
          }
          loadGate.classList.add("is-file-ready");
          updateParagraphProgressButtons();
          setLoadStatus(navigation.lifetimeComplete ? "Completed. Select New Study to begin another run." : `No resumable ${paragraphSpace} run is available.`);
          return false;
        }
        if (pendingLessonNodes.length) {
          // 2026-08-03: Continue consumes the lookup already started beside file download.
          // If it is still pending, open the durable local checkpoint without issuing a duplicate wait.
          mark("continue-click");
          if (currentSpaceWCache.serverPayload && clean(currentSpaceWCache.serverEtag || "")) {
            mark("progress-cache-hit");
          } else if (currentSpaceWCache.serverProgressSettled && currentSpaceWCache.serverProgressResult) {
            const preloaded = await readPreloadedServerProgress({
              serverProgressPromise: Promise.resolve(currentSpaceWCache.serverProgressResult),
            }, "Space_W");
            if (preloaded && preloaded.ok) {
              const payload = preloaded.payload || {};
              applySpaceWVoicePayload(payload.preferences || {});
              applyAiAgentGhostEnVoicePayload(payload.preferences || {});
              mergeSpaceWServerProgressRecord(payload.progress || null);
              currentSpaceWCache.serverPayload = payload;
              currentSpaceWCache.serverEtag = clean(preloaded.etag || "");
              mark("progress-preload-hit");
            } else {
              mark("progress-preload-failed");
            }
          } else if (currentSpaceWCache.serverProgressPromise) {
            mark("progress-preload-pending");
          } else {
            mark("progress-local-only");
          }
          const navigation = navigationForLoadedRecord(currentSpaceWCache.savedProgress, "Space_W");
          if (navigation.resumeAvailable) {
            const result = await startSavedSpaceWProgress(nextOptions);
            mark("runtime-ready");
            publishTrace();
            return result;
          }
          loadGate.classList.add("is-file-ready");
          updateSpaceWReviewButton();
          if (loadStartButton) {
            loadStartButton.hidden = !navigation.lifetimeComplete;
            loadStartButton.textContent = "New Study";
          }
          setLoadStatus(navigation.lifetimeComplete ? "Completed. Select New Study to begin another run." : "No resumable Space_W run is available.");
          mark("no-resumable-run");
          publishTrace();
          return false;
        }
        return false;
      };

      const waitPreparedReloadPayload = async (mode = "", timeoutMs = 1800) => {
        const startedAt = Date.now();
        const expectedMode = clean(mode).toLowerCase();
        while (Date.now() - startedAt < timeoutMs) {
          if (
            (expectedMode === "space_v" && pendingVocabularyPayload) ||
            (expectedMode === "space_q" && pendingQuestionPayload) ||
            ((expectedMode === "space_p" || expectedMode === "space_s" || expectedMode === "space_l") && pendingParagraphPayload) ||
            (expectedMode === "space_w" && pendingLessonNodes.length) ||
            (!expectedMode && (pendingVocabularyPayload || pendingQuestionPayload || pendingParagraphPayload || pendingLessonNodes.length))
          ) {
            return true;
          }
          await delay(40);
        }
        return Boolean(pendingVocabularyPayload || pendingQuestionPayload || pendingParagraphPayload || pendingLessonNodes.length);
      };

      const restoreLessonAfterReloadSession = async (reloadState = {}) => {
        if (!authToken || !currentAuthUsername) {
          try {
            sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (_error) {
          }
          return false;
        }
        const source = reloadState && reloadState.source && typeof reloadState.source === "object" ? reloadState.source : {};
        const sourcePath = clean(reloadState.path || source.path || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        if (!sourcePath) {
          return false;
        }
        const locationRouteState = futureRouteStateFromLocation();
        const directRouteRestore = Boolean(
          reloadState.directRouteRestore ||
          reloadState.directRoute ||
          (locationRouteState.file && locationRouteState.route && locationRouteState.route.startsWith("space_"))
        );
        const restoreOptions = {
          skipAudioPrepare: true,
          allowDuringVocabBuild: directRouteRestore || Boolean(reloadState.allowDuringVocabBuild),
          directRouteRestore,
        };
        try {
          const restoreMode = normalizeFutureAppRoute(reloadState.mode || locationRouteState.process || locationRouteState.route || "");
          if (restoreMode === "space_picture" || /\.(png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i.test(sourcePath)) {
            await enterPictureServerFile({
              source: "server",
              path: sourcePath,
              name: clean(source.name || sourcePath.split("/").pop() || sourcePath),
              extension: (sourcePath.match(/\.[^.\/]+$/) || [""])[0],
            }, { replaceRoute: true, page: locationRouteState.page || 0, forcePage: true });
            try {
              sessionStorage.removeItem(RELOAD_SESSION_KEY);
            } catch (_error) {
            }
            return true;
          }
          if (restoreMode === "space_pdf" || sourcePath.toLowerCase().endsWith(".pdf")) {
            await enterPdfServerFile({
              source: "server",
              path: sourcePath,
              name: clean(source.name || sourcePath.split("/").pop() || sourcePath),
            }, { replaceRoute: true, page: locationRouteState.page || 0, forcePage: true });
            try {
              sessionStorage.removeItem(RELOAD_SESSION_KEY);
            } catch (_error) {
            }
            return true;
          }
          setLoadStatus("Reload session detected. Restoring current lesson...");
          const result = await fetchServerText(`/server-data/file?path=${encodeURIComponent(sourcePath)}`);
          const text = String(result.text || "").replace(/^\uFEFF/, "");
          if (!text.trim()) {
            throw new Error("Goi bai hoc tren server dang rong.");
          }
          const payload = await decodeFuturePayload(text);
          setCurrentLessonSource({
            ...source,
            source: "server",
            path: sourcePath,
            name: clean(source.name || sourcePath),
          }, payload);
          const routeKey = routeForLessonPayload(payload);
          updateFutureAppRoute(routeKey, {
            file: sourcePath,
            tree: reloadState.browserPath || futureRouteParentForPath(sourcePath),
            process: routeKey,
            replace: true,
          });
          rememberServerFile(sourcePath, { syncNow: true });
          closeServerBrowser();
          prepareLessonPayloadForGate(payload, restoreOptions);
          await waitPreparedReloadPayload(reloadState.mode || "", 2200);
          await continuePreparedLessonFromSavedProgress(restoreOptions);
          try {
            sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (_error) {
          }
          return true;
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not restore the reloaded lesson.", true);
          openServerBrowserAfterAuth();
          return false;
        }
      };

      const restoreBrowserAfterReloadSession = async (reloadState = {}) => {
          const routeState = reloadState && reloadState.routeState && typeof reloadState.routeState === "object"
            ? reloadState.routeState
            : futureRouteStateFromLocation();
          const routeAlreadyInLessonVault = normalizeFutureAppRoute(routeState.route || "") === "lesson_vault";
          const filePath = cleanFutureRoutePathValue(routeState.file || (routeAlreadyInLessonVault ? "" : reloadState.selectedFile) || "");
        const processKey = normalizeFutureAppRoute(routeState.process || reloadState.mode || "") || futureRouteSpaceForFilePath(filePath);
        const treePath = cleanFutureRoutePathValue(routeState.tree || reloadState.browserPath || (filePath ? futureRouteParentForPath(filePath) : ""));
        if (filePath && processKey && processKey.startsWith("space_") && routeState.route && routeState.route.startsWith("space_")) {
          return restoreLessonAfterReloadSession({
            ...reloadState,
            mode: processKey,
            path: filePath,
            directRouteRestore: true,
            allowDuringVocabBuild: true,
            source: {
              source: "server",
              path: filePath,
              name: filePath.split("/").pop() || filePath,
            },
            browserPath: treePath,
          });
        }
        try {
          setLoadStatus("Restoring lesson vault...");
          setServerBrowserPanel("vault");
          updateFutureAppRoute("lesson_vault", {
            tree: treePath,
            file: filePath,
            process: processKey,
            replace: true,
          });
          const restoredVaultPayload = await loadServerDataPath(treePath, false);
          if (filePath) {
            setSelectedTaskPath(filePath);
            const restore = typeof currentLessonVaultRestoreState === "function" ? currentLessonVaultRestoreState() : null;
            if (restore) {
              restore.lastFileReady = true;
              restore.targetFile = filePath;
              restore.targetTree = treePath;
              restore.targetPaths = [filePath];
              restore.candidates = [{ path: filePath, parentPath: treePath }];
              recordLessonVaultRestorePhase("refresh-target-ready", { source: "reload-session" });
              if (typeof scheduleLessonVaultLoginRestore === "function") {
                scheduleLessonVaultLoginRestore(restoredVaultPayload || { path: treePath, entries: serverCurrentEntries || [] }, "reload-session");
              }
            } else {
              scrollFocusedServerFileIntoView();
            }
          }
          try {
            sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (_error) {
          }
          return true;
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not restore lesson vault.", true);
          return false;
        }
      };

      const loadLessonPayload = (payload) => {
        hideActiveLessonSurfaceForLoad("Opening selected lesson...");
        enterLessonPayloadNow(payload);
      };

      const loadLessonFromCode = async (rawCode) => {
        setLoadStatus("Đang đọc file future...");
        const payload = await decodeFuturePayload(rawCode);
        setCurrentLessonSource({ source: "code", name: "inline.Space_W" }, payload);
        loadLessonPayload(payload);
      };

      const readLessonFileText = async (file) => {
        if (!file) {
          throw new Error("Chưa chọn file bài học.");
        }
        if (typeof file.text === "function") {
          try {
            const text = await file.text();
            if (String(text || "").trim()) {
              return text;
            }
          } catch (error) {
            // Fall through to FileReader for mobile file providers.
          }
        }
        return await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result || ""));
          reader.onerror = () => reject(reader.error || new Error("Không đọc được nội dung file."));
          reader.readAsText(file, "utf-8");
        });
      };

      let lessonFileReadInProgress = false;
      const handleLessonFileSelection = async () => {
        if (lessonFileReadInProgress) {
          return;
        }
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
          return;
        }
        requestAutoFullscreenForSpaceOpen();
        lessonFileReadInProgress = true;
        hideActiveLessonSurfaceForLoad(`Đã chọn ${file.name || "gói bài học"}, đang nạp...`);
        try {
          await delay(20);
          const text = await readLessonFileText(file);
          if (!String(text || "").trim()) {
            throw new Error("Gói bài học đang rỗng hoặc trình duyệt chưa đọc được nội dung.");
          }
          setLoadStatus("Đang giải nén và kiểm tra bài học...");
          await delay(20);
          const payload = await decodeFuturePayload(text.replace(/^\uFEFF/, ""));
          setCurrentLessonSource({ source: "local", name: file.name || "local.Space_W" }, payload);
          if (shouldAutoStartLoadedFileInPopup()) {
            setLoadStatus("Đã nạp file. Đang mở giao diện học...");
            await delay(20);
            loadLessonPayload(payload);
          } else {
            prepareLessonPayloadForGate(payload);
          }
        } catch (error) {
          console.error("FTG load Space_W failed", error);
          pendingVocabularyPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          resetSpaceWCache();
          loadGate.classList.remove("is-file-ready");
          setLoadStatus(error && error.message ? error.message : "Không đọc được file bài học.", true);
        } finally {
          try {
            fileInput.value = "";
          } catch (error) {
            // Some mobile browsers keep the selected file name until the next picker open.
          }
          lessonFileReadInProgress = false;
        }
      };

      let serverBrowserPath = "";
      let serverBrowserBusy = false;
      let serverBrowserFocusedFilePath = "";
      let serverDataClipboard = null;
      let serverContextMenuNode = null;
      let serverCurrentEntries = [];
      let serverBrowserPreferredTaskFolders = [];
      let serverBrowserPreferredTaskFolderOwner = "";
      let serverLessonProgressPrefetchTimer = 0;
      let serverBrowserFolderPrefetchTimer = 0;
      let serverBrowserFolderPrefetchBusy = false;
      let learningStatsMotionTimer = 0;
      const serverBrowserFolderPrefetchQueue = [];
      const serverBrowserFolderPrefetchSeen = new Set();
      const serverSpaceVFileStatsCache = new Map();
      const spaceTaskFolderOwnerMutations = new Map();
      const spaceTaskFolderMutationRefreshTimers = new Map();
      const LEARNING_STATS_MOTION_INTERVAL_MS = 10000;
      const LEARNING_STATS_MOTION_BURST_MS = 2000;
      const SERVER_WORKSPACE_MOTION_BURST_MS = 6200;
      const TASK_BOARD_PERIODIC_MOTION_LIMIT = 8;
      const SERVER_BROWSER_FOLDER_PREFETCH_LIMIT = 0;
      const SERVER_BROWSER_FOLDER_PREFETCH_QUEUE_LIMIT = 0;
      const SERVER_BROWSER_FOLDER_PREFETCH_DELAY_MS = 2000;
      const VOCAB_REGISTRY_LOCAL_CACHE_PREFIX = "future_vocab_registry_cache_v1";
      const VOCAB_REGISTRY_LOCAL_CACHE_SCHEMA_VERSION = 2;
      const SPACE_V_FILE_STATS_LOCAL_CACHE_PREFIX = "future_space_v_file_stats_cache_v1";
      const VOCAB_LESSON_INDEX_LOCAL_CACHE_PREFIX = "future_vocab_lesson_index_cache_v1";
      const VOCAB_FILE_KEY_MAP_LOCAL_CACHE_PREFIX = "future_vocab_file_key_map_cache_v1";
      let vocabLessonIndexMemoryCache = { user: "", payload: null };
      const vocabFileKeyMapMemoryCache = new Map();
      const vocabFileKeyMapPending = new Map();

      const normalizeServerPathValue = (pathValue = "") => {
        const raw = String(pathValue || "").replace(/\\/g, "/").replace(/[\r\n\t]+/g, " ").replace(/^\/+|\/+$/g, "").trim();
        if (!raw) {
          return "";
        }
        return raw.split("/").map((part) => part.trim()).filter(Boolean).join("/");
      };

      // Added 2026-07-03: keeps user vocabulary registry available immediately after login for client-side Lesson Vault estimates.
      const vocabRegistryLocalCacheKey = (username = "") => {
        const user = clean(username || currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
        return `${VOCAB_REGISTRY_LOCAL_CACHE_PREFIX}:${user}`;
      };

      const normalizeVocabRegistryCachePayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const normalizedWords = (Array.isArray(source.words) ? source.words : [])
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
        const periodSource = source.period_keys && typeof source.period_keys === "object"
          ? source.period_keys
          : (source.periodKeys && typeof source.periodKeys === "object" ? source.periodKeys : {});
        const periodKeys = {};
        ["day", "week", "month"].forEach((scope) => {
          periodKeys[scope] = (Array.isArray(periodSource[scope]) ? periodSource[scope] : [])
            .map((key) => normalize(key))
            .filter(Boolean);
        });
        return {
          version: VOCAB_REGISTRY_LOCAL_CACHE_SCHEMA_VERSION,
          username: clean(source.username || currentAuthUsername || ""),
          words: normalizedWords,
          period_keys: periodKeys,
          total_words: Number(source.total_words || normalizedWords.length) || normalizedWords.length,
          registry_generation: Math.max(0, Number(source.registry_generation || source.registryGeneration || 0) || 0),
          period_generation: Math.max(0, Number(source.period_generation || source.periodGeneration || 0) || 0),
          etag: clean(source.etag || ""),
          updatedAt: clean(source.updatedAt || source.savedAt || new Date().toISOString()),
          source: clean(source.source || "server"),
        };
      };

      const writeVocabRegistryLocalCache = (payload = {}, username = "") => {
        try {
          if (!window.localStorage) {
            return false;
          }
          const normalized = normalizeVocabRegistryCachePayload({
            ...payload,
            username: username || currentAuthUsername || "",
            updatedAt: new Date().toISOString(),
          });
          if (!normalized.words.length && !normalized.total_words) {
            return false;
          }
          localStorage.setItem(vocabRegistryLocalCacheKey(username), JSON.stringify(normalized));
          return true;
        } catch (error) {
          return false;
        }
      };

      // Added 2026-07-23: lifetime history with no current checkpoint must stop auto-start.
      const lessonHistoryRecordForNavigation = () => {
        const study = currentLessonSource && currentLessonSource.study && typeof currentLessonSource.study === "object"
          ? currentLessonSource.study
          : {};
        const completedRuns = Math.max(
          0,
          Math.floor(Number(study.mine || 0) || 0),
          Math.floor(Number(study.admin_mine || 0) || 0),
          Math.floor(Number(study.completedRuns || study.completed_runs || 0) || 0),
        );
        return completedRuns ? { completedRuns } : null;
      };

      const navigationForLoadedRecord = (record, spaceType) => (
        resolveSpaceRunNavigation(record || lessonHistoryRecordForNavigation(), spaceType)
      );

      const readVocabRegistryLocalCache = (username = "") => {
        try {
          if (!window.localStorage) {
            return null;
          }
          const raw = localStorage.getItem(vocabRegistryLocalCacheKey(username));
          if (!raw) {
            return null;
          }
          const parsed = JSON.parse(raw);
          if (!parsed || Number(parsed.version || 0) !== VOCAB_REGISTRY_LOCAL_CACHE_SCHEMA_VERSION) {
            localStorage.removeItem(vocabRegistryLocalCacheKey(username));
            return null;
          }
          const normalized = normalizeVocabRegistryCachePayload(parsed);
          return normalized.words.length || normalized.total_words ? normalized : null;
        } catch (error) {
          return null;
        }
      };

      const applyVocabRegistryLocalCache = (username = "") => {
        const cached = readVocabRegistryLocalCache(username);
        if (!cached) {
          return false;
        }
        vocabRegistryWords = cached.words.slice();
        vocabRegistryKeys = new Set(vocabRegistryWords.map((entry) => entry.key));
        vocabRegistryPeriodKeys = {
          day: new Set((cached.period_keys && cached.period_keys.day) || []),
          week: new Set((cached.period_keys && cached.period_keys.week) || []),
          month: new Set((cached.period_keys && cached.period_keys.month) || []),
        };
        vocabRegistryTotal = Number(cached.total_words || vocabRegistryWords.length) || vocabRegistryWords.length;
        vocabRegistryLoaded = true;
        vocabRegistryError = "";
        return true;
      };

      // Added 2026-07-28: authoritative completion responses update client Earn preview sets without a follow-up stats request.
      const applyVocabularyCompletionDeltaToLocalPreview = (payload = {}, username = "") => {
        const source = payload && typeof payload === "object" ? payload : {};
        const vocabulary = source.vocabulary && typeof source.vocabulary === "object"
          ? source.vocabulary
          : (source.completion && source.completion.vocabulary && typeof source.completion.vocabulary === "object" ? source.completion.vocabulary : source);
        const wordKeys = (Array.isArray(vocabulary.accepted_word_keys) ? vocabulary.accepted_word_keys
          : (Array.isArray(vocabulary.learned_word_keys) ? vocabulary.learned_word_keys
            : (Array.isArray(vocabulary.word_keys) ? vocabulary.word_keys : [])))
          .map((key) => normalize(key))
          .filter(Boolean);
        if (!wordKeys.length) {
          return false;
        }
        const targetUser = clean(username || source.username || vocabulary.username || currentAuthUsername || "");
        const cached = readVocabRegistryLocalCache(targetUser) || {
          username: targetUser,
          words: [],
          period_keys: { day: [], week: [], month: [] },
          total_words: 0,
        };
        const registryGeneration = Math.max(0, Number(vocabulary.registry_generation || vocabulary.registryGeneration || 0) || 0);
        const periodGeneration = Math.max(0, Number(vocabulary.period_generation || vocabulary.periodGeneration || 0) || 0);
        const cachedRegistryGeneration = Math.max(0, Number(cached.registry_generation || 0) || 0);
        const cachedPeriodGeneration = Math.max(0, Number(cached.period_generation || 0) || 0);
        if ((registryGeneration && cachedRegistryGeneration > registryGeneration) || (periodGeneration && cachedPeriodGeneration > periodGeneration)) {
          return false;
        }
        const byKey = new Map((cached.words || []).map((entry) => [normalize(entry.key || entry.word || ""), entry]).filter(([key]) => key));
        wordKeys.forEach((key) => {
          if (!byKey.has(key)) {
            byKey.set(key, { key, word: key, meaning: "", pron: "", type: "", count: 1, last: new Date().toISOString() });
          }
        });
        const periodKeys = cached.period_keys && typeof cached.period_keys === "object" ? cached.period_keys : {};
        ["day", "week", "month"].forEach((scope) => {
          const next = new Set((Array.isArray(periodKeys[scope]) ? periodKeys[scope] : []).map((key) => normalize(key)).filter(Boolean));
          wordKeys.forEach((key) => next.add(key));
          periodKeys[scope] = Array.from(next);
        });
        const nextPayload = normalizeVocabRegistryCachePayload({
          ...cached,
          username: targetUser,
          words: Array.from(byKey.values()),
          period_keys: periodKeys,
          total_words: Math.max(Number(vocabulary.total_words || 0) || 0, byKey.size),
          registry_generation: Math.max(registryGeneration, cachedRegistryGeneration),
          period_generation: Math.max(periodGeneration, cachedPeriodGeneration),
          updatedAt: new Date().toISOString(),
          source: "completion-delta",
        });
        writeVocabRegistryLocalCache(nextPayload, targetUser);
        if (!targetUser || clean(currentAuthUsername || "").toLowerCase() === targetUser.toLowerCase()) {
          applyVocabRegistryLocalCache(targetUser);
        }
        if (serverSpaceVFileStatsCache && typeof serverSpaceVFileStatsCache.clear === "function") {
          serverSpaceVFileStatsCache.clear();
        }
        return true;
      };

      const vocabLessonIndexLocalCacheKey = (username = "") => {
        const user = clean(username || currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
        return `${VOCAB_LESSON_INDEX_LOCAL_CACHE_PREFIX}:${user}`;
      };

      const normalizeVocabLessonIndexPayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const files = (Array.isArray(source.files) ? source.files : [])
          .map((file) => {
            const row = file && typeof file === "object" ? file : {};
            const path = normalizeServerPathValue(row.path || "");
            const wordKeys = (Array.isArray(row.word_keys) ? row.word_keys : (Array.isArray(row.wordKeys) ? row.wordKeys : []))
              .map((key) => normalize(key))
              .filter(Boolean);
            return {
              path,
              space: clean(row.space || "Lesson"),
              title: clean(row.title || path.split("/").pop() || ""),
              word_keys: Array.from(new Set(wordKeys)),
              total_words: Math.max(0, Math.floor(Number(row.total_words || row.totalWords || wordKeys.length) || wordKeys.length)),
            };
          })
          .filter((row) => row.path && row.word_keys.length);
        const learnedKeys = (Array.isArray(source.learned_keys) ? source.learned_keys : (Array.isArray(source.learnedKeys) ? source.learnedKeys : []))
          .map((key) => normalize(key))
          .filter(Boolean);
        const periodSource = source.period_keys && typeof source.period_keys === "object"
          ? source.period_keys
          : (source.periodKeys && typeof source.periodKeys === "object" ? source.periodKeys : {});
        const periodKeys = {};
        ["day", "week", "month"].forEach((scope) => {
          periodKeys[scope] = (Array.isArray(periodSource[scope]) ? periodSource[scope] : [])
            .map((key) => normalize(key))
            .filter(Boolean);
        });
        return {
          version: 1,
          user: clean(source.user || currentAuthUsername || ""),
          signature: clean(source.signature || ""),
          files,
          learned_keys: Array.from(new Set(learnedKeys)),
          period_keys: periodKeys,
          cachedAt: clean(source.cachedAt || new Date().toISOString()),
        };
      };

      const writeVocabLessonIndexLocalCache = (payload = {}, username = "") => {
        try {
          if (!window.localStorage) {
            return false;
          }
          const normalized = normalizeVocabLessonIndexPayload({
            ...payload,
            user: username || payload.user || currentAuthUsername || "",
            cachedAt: new Date().toISOString(),
          });
          if (!normalized.files.length) {
            return false;
          }
          localStorage.setItem(vocabLessonIndexLocalCacheKey(username || normalized.user), JSON.stringify(normalized));
          return true;
        } catch (error) {
          return false;
        }
      };

      const readVocabLessonIndexLocalCache = (username = "") => {
        const requestedUser = clean(username || currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
        if (
          vocabLessonIndexMemoryCache.payload
          && vocabLessonIndexMemoryCache.user === requestedUser
        ) {
          return vocabLessonIndexMemoryCache.payload;
        }
        try {
          if (!window.localStorage) {
            return null;
          }
          const raw = localStorage.getItem(vocabLessonIndexLocalCacheKey(username));
          if (!raw) {
            return null;
          }
          const normalized = normalizeVocabLessonIndexPayload(JSON.parse(raw));
          if (!normalized.files.length) {
            return null;
          }
          // Added 2026-07-28: parse the large lesson index once per user, not once per file click.
          vocabLessonIndexMemoryCache = { user: requestedUser, payload: normalized };
          return normalized;
        } catch (error) {
          return null;
        }
      };

      const statsFromVocabLessonIndex = (entry = {}, user = "") => {
        const index = readVocabLessonIndexLocalCache(user || currentAuthUsername || "");
        if (!index) {
          return null;
        }
        const filePath = normalizeServerPathValue(entry.path || entry.effective_path || entry.link_target || "");
        const file = index.files.find((row) => normalizeServerPathValue(row.path).toLowerCase() === filePath.toLowerCase());
        if (!file) {
          return null;
        }
        const learned = new Set(index.learned_keys || []);
        const uniqueKeys = Array.from(new Set(file.word_keys || []));
        const period = index.period_keys || {};
        const topEarnable = {};
        ["day", "week", "month"].forEach((scope) => {
          const used = new Set(Array.isArray(period[scope]) ? period[scope] : []);
          topEarnable[scope] = uniqueKeys.filter((key) => key && !used.has(key)).length;
        });
        return normalizeSpaceVFileStatsCachePayload({
          user: clean(user || index.user || currentAuthUsername || ""),
          path: file.path,
          space: file.space,
          title: file.title,
          total_words: uniqueKeys.length,
          new_words: uniqueKeys.filter((key) => key && !learned.has(key)).length,
          known_words: uniqueKeys.filter((key) => key && learned.has(key)).length,
          top_earnable: topEarnable,
          localEstimate: true,
          cachedAt: index.cachedAt,
        });
      };

      // Added 2026-07-09: computes Lesson Vault New/Earn counts from file word keys plus the user's local registry, without QmDict/client dictionary payloads.
      const vocabRegistrySnapshotForStats = (user = "") => {
        const requestedUser = clean(user || currentAuthUsername || "").toLowerCase();
        const currentUser = clean(currentAuthUsername || "").toLowerCase();
        if ((!requestedUser || requestedUser === currentUser) && vocabRegistryLoaded) {
          return {
            user: clean(currentAuthUsername || requestedUser || ""),
            keys: vocabRegistryKeys instanceof Set ? vocabRegistryKeys : new Set(),
            period: vocabRegistryPeriodKeys || {},
            cachedAt: "",
          };
        }
        const cached = readVocabRegistryLocalCache(requestedUser);
        if (cached) {
          return {
            user: clean(cached.username || requestedUser || ""),
            keys: new Set((cached.words || []).map((entry) => normalize(entry.key || entry.word || "")).filter(Boolean)),
            period: {
              day: new Set((cached.period_keys && cached.period_keys.day) || []),
              week: new Set((cached.period_keys && cached.period_keys.week) || []),
              month: new Set((cached.period_keys && cached.period_keys.month) || []),
            },
            cachedAt: cached.updatedAt || cached.cachedAt || "",
          };
        }
        if (requestedUser && currentUser && requestedUser !== currentUser) {
          return null;
        }
        if (!vocabRegistryLoaded && typeof applyVocabRegistryLocalCache === "function") {
          applyVocabRegistryLocalCache(currentUser);
        }
        if (!vocabRegistryLoaded) {
          return null;
        }
        return {
          user: clean(currentAuthUsername || requestedUser || ""),
          keys: vocabRegistryKeys instanceof Set ? vocabRegistryKeys : new Set(),
          period: vocabRegistryPeriodKeys || {},
          cachedAt: "",
        };
      };

      const statsFromEntryVocabWordKeys = (entry = {}, user = "") => {
        const rawKeys = Array.isArray(entry.vocab_word_keys)
          ? entry.vocab_word_keys
          : (Array.isArray(entry.vocabWordKeys) ? entry.vocabWordKeys : []);
        const uniqueKeys = Array.from(new Set(rawKeys.map((key) => normalize(key)).filter(Boolean)));
        if (!uniqueKeys.length) {
          return null;
        }
        const registry = vocabRegistrySnapshotForStats(user || currentAuthUsername || "");
        if (!registry || !(registry.keys instanceof Set)) {
          return null;
        }
        const period = registry.period || {};
        const topEarnable = {};
        ["day", "week", "month"].forEach((scope) => {
          const used = period[scope] instanceof Set ? period[scope] : new Set();
          topEarnable[scope] = uniqueKeys.filter((key) => key && !used.has(key)).length;
        });
        const filePath = normalizeServerPathValue(entry.path || entry.effective_path || entry.link_target || "");
        return normalizeSpaceVFileStatsCachePayload({
          user: clean(user || registry.user || currentAuthUsername || ""),
          path: filePath,
          space: clean(entry.vocab_space || entry.vocabSpace || entry.space || entry.extension || "Lesson"),
          title: clean(entry.title || entry.name || ""),
          total_words: Math.max(0, Math.floor(Number(entry.vocab_total_words || entry.vocabTotalWords || uniqueKeys.length) || uniqueKeys.length)),
          new_words: uniqueKeys.filter((key) => key && !registry.keys.has(key)).length,
          known_words: uniqueKeys.filter((key) => key && registry.keys.has(key)).length,
          top_earnable: topEarnable,
          localEstimate: true,
          cachedAt: registry.cachedAt || new Date().toISOString(),
        });
      };

      const vocabFileKeyMapStorageKey = (user = "") => `${VOCAB_FILE_KEY_MAP_LOCAL_CACHE_PREFIX}:${clean(user || currentAuthUsername || "guest").toLowerCase() || "guest"}`;

      const vocabFileKeyMapAliases = (entry = {}) => Array.from(new Set([
        entry.lesson_id, entry.lessonId, entry.path, entry.effective_path, entry.link_target,
        entry.linked_path, ...(Array.isArray(entry.aliases) ? entry.aliases : []),
      ].map((value) => normalizeServerPathValue(value || clean(value))).filter(Boolean).map((value) => value.toLowerCase())));

      const readVocabFileKeyMap = (user = "") => {
        const storageKey = vocabFileKeyMapStorageKey(user);
        if (vocabFileKeyMapMemoryCache.has(storageKey)) {
          return vocabFileKeyMapMemoryCache.get(storageKey);
        }
        let rows = [];
        try {
          const raw = window.localStorage && localStorage.getItem(storageKey);
          const parsed = raw ? JSON.parse(raw) : [];
          rows = Array.isArray(parsed) ? parsed : [];
        } catch (error) {
          rows = [];
        }
        vocabFileKeyMapMemoryCache.set(storageKey, rows);
        return rows;
      };

      const writeVocabFileKeyMap = (payload = {}, user = "") => {
        const keys = Array.from(new Set((Array.isArray(payload.vocab_word_keys) ? payload.vocab_word_keys : []).map(normalize).filter(Boolean)));
        if (!keys.length) return false;
        const row = { aliases: vocabFileKeyMapAliases(payload), path: normalizeServerPathValue(payload.resolved_path || payload.path || ""), lesson_id: clean(payload.lesson_id || ""), vocab_word_keys: keys, vocab_total_words: keys.length, vocab_space: clean(payload.vocab_space || "Lesson"), vocab_stats: payload.vocab_stats && typeof payload.vocab_stats === "object" ? payload.vocab_stats : null };
        const storageKey = vocabFileKeyMapStorageKey(user);
        const rows = readVocabFileKeyMap(user).filter((item) => !item || !row.aliases.some((alias) => Array.isArray(item.aliases) && item.aliases.includes(alias)));
        rows.push(row);
        const trimmed = rows.slice(-4000);
        vocabFileKeyMapMemoryCache.set(storageKey, trimmed);
        try { if (window.localStorage) localStorage.setItem(storageKey, JSON.stringify(trimmed)); } catch (error) { /* cache is optional */ }
        return true;
      };

      const entryWithCachedVocabWordKeys = (entry = {}, user = "") => {
        if (Array.isArray(entry.vocab_word_keys) && entry.vocab_word_keys.length) return entry;
        const aliases = vocabFileKeyMapAliases(entry);
        const row = readVocabFileKeyMap(user).find((item) => Array.isArray(item && item.aliases) && item.aliases.some((alias) => aliases.includes(alias)));
        return row ? { ...entry, vocab_word_keys: row.vocab_word_keys, vocab_total_words: row.vocab_total_words, vocab_space: row.vocab_space, vocab_stats: row.vocab_stats || null } : entry;
      };

      const cacheEarnKeysFromLessonVaultEntries = (entries = [], user = "") => {
        if (!Array.isArray(entries)) return 0;
        let count = 0;
        entries.forEach((entry) => {
          if (entry && Array.isArray(entry.vocab_word_keys) && entry.vocab_word_keys.length && writeVocabFileKeyMap(entry, user)) count += 1;
        });
        return count;
      };

      const fetchVocabFileKeyMap = async (entry = {}, user = "") => {
        const resolvedEntry = entryWithCachedVocabWordKeys(entry, user);
        const localStats = statsFromEntryVocabWordKeys(resolvedEntry, user);
        const cachedStatsAt = Date.parse(clean(resolvedEntry.vocab_stats && resolvedEntry.vocab_stats.cachedAt || "")) || 0;
        if (
          Array.isArray(resolvedEntry.vocab_word_keys)
          && resolvedEntry.vocab_word_keys.length
          && (localStats || (cachedStatsAt > 0 && Date.now() - cachedStatsAt < 15000))
        ) {
          return localStats ? { ...resolvedEntry, vocab_stats: localStats } : resolvedEntry;
        }
        const requestKey = `${clean(user || currentAuthUsername || "").toLowerCase()}:${vocabFileKeyMapAliases(entry).join("|")}`;
        if (vocabFileKeyMapPending.has(requestKey)) return vocabFileKeyMapPending.get(requestKey);
        const promise = (async () => {
          const result = await fetchAuthJson("/vocab/file-key-map", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...entry, user: clean(user || currentAuthUsername || ""), aliases: vocabFileKeyMapAliases(entry) }), timeoutMs: 8000 });
          const payload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
          writeVocabFileKeyMap(payload, user);
          return entryWithCachedVocabWordKeys({ ...entry, ...payload }, user);
        })();
        vocabFileKeyMapPending.set(requestKey, promise);
        try { return await promise; } finally { vocabFileKeyMapPending.delete(requestKey); }
      };

      const loadVocabLessonIndex = async (force = false) => {
        if (!authToken || !currentAuthUsername) {
          return null;
        }
        const cached = readVocabLessonIndexLocalCache(currentAuthUsername);
        if (cached && !force) {
          return cached;
        }
        try {
          const result = await fetchAuthJson("/vocab/lesson-index", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
            timeoutMs: 45000,
          });
          const payload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
          const normalized = normalizeVocabLessonIndexPayload(payload);
          if (normalized.files.length) {
            writeVocabLessonIndexLocalCache(normalized, currentAuthUsername || "");
            vocabLessonIndexMemoryCache = {
              user: clean(currentAuthUsername || "").toLowerCase(),
              payload: normalized,
            };
            return normalized;
          }
        } catch (error) {
          if (cached) {
            return cached;
          }
        }
        return cached;
      };
      if (typeof window !== "undefined") {
        window.__ftLoadVocabLessonIndex = loadVocabLessonIndex;
        window.__ftReadVocabLessonIndexLocalCache = readVocabLessonIndexLocalCache;
      }

      // Added 2026-07-03: persists per-file Space_V stats so Lesson Vault can show New/Earn chips before the server round trip.
      const spaceVFileStatsLocalCacheKey = (entry = {}, user = "") => {
        const viewer = clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
        const targetUser = clean(user || viewer).toLowerCase() || viewer;
        const filePath = normalizeServerPathValue(entry.path || entry.effective_path || entry.link_target || "");
        if (!filePath) {
          return "";
        }
        return `${SPACE_V_FILE_STATS_LOCAL_CACHE_PREFIX}:${viewer}:${targetUser}:${filePath.toLowerCase()}`;
      };

      const normalizeSpaceVFileStatsCachePayload = (stats = {}) => {
        const source = stats && typeof stats === "object" ? stats : {};
        const top = source.top_earnable && typeof source.top_earnable === "object"
          ? source.top_earnable
          : (source.topEarnable && typeof source.topEarnable === "object" ? source.topEarnable : {});
        return {
          ...source,
          total_words: Math.max(0, Math.floor(Number(source.total_words || 0) || 0)),
          new_words: Math.max(0, Math.floor(Number(source.new_words || 0) || 0)),
          known_words: Math.max(0, Math.floor(Number(source.known_words || 0) || 0)),
          top_earnable: {
            day: Math.max(0, Math.floor(Number(top.day || 0) || 0)),
            week: Math.max(0, Math.floor(Number(top.week || 0) || 0)),
            month: Math.max(0, Math.floor(Number(top.month || 0) || 0)),
          },
          cachedAt: clean(source.cachedAt || new Date().toISOString()),
          localEstimate: Boolean(source.localEstimate),
        };
      };

      const writeSpaceVFileStatsLocalCache = (entry = {}, user = "", stats = {}) => {
        const key = spaceVFileStatsLocalCacheKey(entry, user);
        if (!key || !stats || typeof stats !== "object") {
          return false;
        }
        const payload = normalizeSpaceVFileStatsCachePayload({
          ...stats,
          path: normalizeServerPathValue(entry.path || stats.path || ""),
          user: clean(user || stats.user || currentAuthUsername || ""),
          cachedAt: new Date().toISOString(),
        });
        try {
          serverSpaceVFileStatsCache.set(key, { at: Date.now(), payload });
          if (window.localStorage) {
            localStorage.setItem(key, JSON.stringify(payload));
          }
          return true;
        } catch (error) {
          return false;
        }
      };

      const readSpaceVFileStatsLocalCache = (entry = {}, user = "") => {
        entry = entryWithCachedVocabWordKeys(entry, user);
        const key = spaceVFileStatsLocalCacheKey(entry, user);
        if (!key) {
          return null;
        }
        const memory = serverSpaceVFileStatsCache.get(key);
        if (memory && memory.payload) {
          const hasEntryKeys = Array.isArray(entry.vocab_word_keys) || Array.isArray(entry.vocabWordKeys);
          if ((!hasEntryKeys || !memory.payload.localEstimate) && Date.now() - Number(memory.at || 0) < 15000) {
            return memory.payload;
          }
          if (!memory.payload.localEstimate) {
            serverSpaceVFileStatsCache.delete(key);
          }
        }
        if (typeof statsFromEntryVocabWordKeys === "function") {
          const fromEntry = statsFromEntryVocabWordKeys(entry, user);
          if (fromEntry) {
            serverSpaceVFileStatsCache.set(key, { at: Date.now(), payload: fromEntry });
            return fromEntry;
          }
        }
        if (typeof statsFromVocabLessonIndex === "function") {
          const fromIndex = statsFromVocabLessonIndex(entry, user);
          if (fromIndex) {
            serverSpaceVFileStatsCache.set(key, { at: Date.now(), payload: fromIndex });
            return fromIndex;
          }
        }
        try {
          if (!window.localStorage) {
            return null;
          }
          const raw = localStorage.getItem(key);
          if (!raw) {
            return null;
          }
          const payload = normalizeSpaceVFileStatsCachePayload(JSON.parse(raw));
          if (payload.localEstimate) {
            localStorage.removeItem(key);
            return null;
          }
          const cachedAt = Date.parse(clean(payload.cachedAt || "")) || 0;
          if (!cachedAt || Date.now() - cachedAt >= 15000) {
            localStorage.removeItem(key);
            return null;
          }
          serverSpaceVFileStatsCache.set(key, { at: Date.now(), payload });
          return payload;
        } catch (error) {
          return null;
        }
      };

      const serverBrowserListCache = new Map();
      const serverLessonProgressPrefetchCache = new Map();
      const serverBrowserPathWarmInflight = new Map();
      const SERVER_BROWSER_MANIFEST_REFRESH_KEY = "future_server_data_manifest_refreshed_at";
      const SERVER_BROWSER_MANIFEST_SIGNATURE_KEY = "future_server_data_manifest_signature";
      const SERVER_BROWSER_LIST_CACHE_TTL_MS = 60 * 60 * 1000;
      const SERVER_BROWSER_LIST_REFRESH_MIN_MS = 60 * 60 * 1000;
      const SERVER_BROWSER_MANIFEST_STATUS_MIN_MS = 60 * 60 * 1000;
      const SERVER_BROWSER_MANIFEST_POLL_MS = 60 * 60 * 1000;
      const SERVER_LESSON_PROGRESS_PREFETCH_TTL_MS = 30000;
      let serverBrowserManifestStatusCheckedAt = 0;
      let serverBrowserManifestStatusPromise = null;
      let currentLessonVaultCacheWarmTimer = 0;
      let currentLessonVaultCacheWarmLastAt = 0;

      const getServerBrowserManifestRefreshAt = () => {
        try {
          const value = Number(localStorage.getItem(SERVER_BROWSER_MANIFEST_REFRESH_KEY) || 0);
          return Number.isFinite(value) ? Math.max(0, value) : 0;
        } catch (error) {
          return 0;
        }
      };

      const getServerBrowserManifestSignature = () => {
        try {
          return clean(localStorage.getItem(SERVER_BROWSER_MANIFEST_SIGNATURE_KEY) || "");
        } catch (error) {
          return "";
        }
      };

      const rememberServerBrowserManifestSignature = (signature = "") => {
        const value = clean(signature || "");
        if (!value) {
          return;
        }
        try {
          localStorage.setItem(SERVER_BROWSER_MANIFEST_SIGNATURE_KEY, value);
        } catch (error) {
        }
      };

      const serverBrowserListCacheKey = (relativePath = "", taskOwner = "") => [
        clean(currentAuthUsername || ""),
        currentAuthIsAdmin ? "admin" : "user",
        normalizeServerPathValue(relativePath || ""),
        clean(taskOwner || ""),
      ].join("|");

      const getCachedServerBrowserListRow = (relativePath = "", taskOwner = "", options = {}) => {
        const key = serverBrowserListCacheKey(relativePath, taskOwner);
        const row = serverBrowserListCache.get(key);
        const refreshedAt = getServerBrowserManifestRefreshAt();
        const manifestSignature = getServerBrowserManifestSignature();
        const allowStale = Boolean(options && options.allowStale);
        if (
          !row
          || !row.payload
          || Boolean(row.payload.login_preview)
          || (!allowStale && Date.now() - Number(row.at || 0) > SERVER_BROWSER_LIST_CACHE_TTL_MS)
          || (!allowStale && Number(row.manifestRefreshAt || 0) < refreshedAt)
          || (!allowStale && manifestSignature && clean(row.manifestSignature || "") !== manifestSignature)
        ) {
          serverBrowserListCache.delete(key);
          serverBrowserFolderPrefetchSeen.delete(key);
          return null;
        }
        return row;
      };

      const rememberServerBrowserList = (relativePath = "", taskOwner = "", payload = null) => {
        if (!payload || typeof payload !== "object") {
          return;
        }
        if (payload.login_preview) {
          return;
        }
        cacheEarnKeysFromLessonVaultEntries(payload.entries, taskOwner || currentAuthUsername || "");
        serverBrowserListCache.set(serverBrowserListCacheKey(relativePath, taskOwner), {
          at: Date.now(),
          manifestRefreshAt: getServerBrowserManifestRefreshAt(),
          manifestSignature: clean(payload.manifest_signature || payload.manifestSignature || getServerBrowserManifestSignature()),
          payload,
        });
        rememberServerBrowserManifestSignature(payload.manifest_signature || payload.manifestSignature || "");
        if (serverBrowserListCache.size > 2000) {
          const ordered = Array.from(serverBrowserListCache.entries()).sort((a, b) => Number(a[1].at || 0) - Number(b[1].at || 0));
          ordered.slice(0, Math.max(1, ordered.length - 1800)).forEach(([key]) => serverBrowserListCache.delete(key));
        }
      };

      // Added 2026-07-21: an empty tree-snapshot row under a linked root is incomplete, not proof of an empty folder.
      const serverBrowserLinkedFolderSnapshotNeedsHydration = (relativePath = "", taskOwner = "", payload = null) => {
        if (!payload || typeof payload !== "object" || !payload.manifest_snapshot || (Array.isArray(payload.entries) && payload.entries.length)) {
          return false;
        }
        let candidate = normalizeServerPathValue(relativePath || "");
        const owner = clean(taskOwner || "");
        while (candidate) {
          const parent = serverParentPathForFile(candidate);
          const parentRow = getCachedServerBrowserListRow(parent, owner, { allowStale: true });
          const parentEntries = parentRow && parentRow.payload && Array.isArray(parentRow.payload.entries)
            ? parentRow.payload.entries
            : [];
          const candidateKey = normalizeTaskPath(candidate);
          if (parentEntries.some((entry) => (
            entry
            && entry.type === "folder"
            && normalizeTaskPath(normalizeServerPathValue(entry.path || "")) === candidateKey
            && Boolean(entry.linked || entry.link_target)
          ))) {
            return true;
          }
          if (!parent || parent === candidate) {
            break;
          }
          candidate = parent;
        }
        return false;
      };

      const patchLessonVaultCachedProgress = (paths = [], progress = null, options = {}) => {
        if (!progress || typeof progress !== "object" || typeof applyLessonVaultProgressSnapshotToEntry !== "function") {
          return 0;
        }
        const wanted = new Set((Array.isArray(paths) ? paths : [paths])
          .map((value) => normalizeTaskPath(normalizeServerPathValue(value || "")))
          .filter(Boolean));
        if (!wanted.size) {
          return 0;
        }
        let changed = 0;
        const patchEntries = (entries = []) => {
          if (!Array.isArray(entries)) {
            return;
          }
          entries.forEach((entry) => {
            if (!entry || typeof entry !== "object") {
              return;
            }
            const entrySpace = lessonVaultEntryProgressSpace(entry);
            const entryIds = [entry.lesson_id, entry.lessonId, entry.file_id, entry.fileId]
              .map((value) => clean(value).toLowerCase())
              .filter(Boolean);
            const entryPaths = [
              ...entryIds.map((value) => entrySpace ? `space:${entrySpace.toLowerCase()}:id:${value}` : ""),
              entry.path,
              entry.effective_path,
              entry.link_target,
              entry.linked_path,
              entry.sourcePath,
              entry.source_path,
              entry.original_path,
              typeof serverLearningPathForEntry === "function" ? serverLearningPathForEntry(entry) : "",
            ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
            if (!entryPaths.some((value) => wanted.has(value))) {
              return;
            }
            if (options.force) {
              const study = entry.study && typeof entry.study === "object" ? entry.study : {};
              const progressCompletedRuns = Math.max(
                0,
                Math.floor(Number(progress.completedRuns ?? progress.completed_runs ?? 0) || 0),
              );
              entry.study = {
                ...study,
                progress: { ...progress },
                progress_text: clean(progress.text || ""),
                progress_percent: Number(progress.percent || 0) || 0,
                updatedAt: clean(progress.updatedAt || progress.savedAt || new Date().toISOString()),
                ...(progressCompletedRuns > 0
                  ? {
                    mine: progressCompletedRuns,
                    completedRuns: progressCompletedRuns,
                    completed_runs: progressCompletedRuns,
                  }
                  : {}),
              };
              entry.progress = entry.study.progress;
            } else {
              Object.assign(entry, applyLessonVaultProgressSnapshotToEntry(entry));
            }
            changed += 1;
          });
        };
        patchEntries(serverCurrentEntries);
        serverBrowserListCache.forEach((row) => {
          if (row && row.payload) {
            patchEntries(row.payload.entries);
          }
        });
        if (changed && options && options.render && typeof renderServerDataList === "function") {
          const cachedRow = getCachedServerBrowserListRow(serverBrowserPath || "", serverTaskOwnerContext || currentAuthUsername || "", { allowStale: true });
          if (cachedRow && cachedRow.payload) {
            renderServerDataList(cachedRow.payload);
          }
        }
        return changed;
      };

      // Added 2026-07-05: updates only the just-returned lesson row from Server 2 RAM instead of reloading the whole folder.
      const refreshLessonVaultItemStudyFromServer = async (paths = [], taskOwner = "", options = {}) => {
        const pathList = (Array.isArray(paths) ? paths : [paths])
          .map((value) => normalizeServerPathValue(value || ""))
          .filter(Boolean);
        const primaryPath = pathList[0] || "";
        if (!primaryPath) {
          return null;
        }
        const query = new URLSearchParams();
        query.set("path", primaryPath);
        const owner = clean(taskOwner || "");
        if (owner) {
          query.set("task_owner", owner);
        }
        pathList.slice(1).forEach((alias) => query.append("alias", alias));
        const result = await fetchServerJson(`/server-data/item-study?${query.toString()}`);
        const study = result && result.study && typeof result.study === "object" ? result.study : null;
        if (!study) {
          return result || null;
        }
        const wantedPaths = new Set([
          ...pathList,
          result.path,
          result.effective_path,
        ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean));
        if (!wantedPaths.size) {
          return result || null;
        }
        const changedVisibleEntries = [];
        const patchEntries = (entries, collectVisible = false) => {
          let changed = false;
          if (!Array.isArray(entries)) {
            return false;
          }
          entries.forEach((entry) => {
            if (!entry || typeof entry !== "object" || entry.type !== "file") {
              return;
            }
            const entryPaths = [
              entry.path,
              entry.effective_path,
              entry.link_target,
              entry.linked_path,
              entry.sourcePath,
              entry.source_path,
              entry.original_path,
              serverLearningPathForEntry(entry),
            ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
            if (entryPaths.some((value) => wantedPaths.has(value))) {
              entry.study = { ...(entry.study && typeof entry.study === "object" ? entry.study : {}), ...study };
              changed = true;
              if (collectVisible) {
                changedVisibleEntries.push(entry);
              }
            }
          });
          return changed;
        };
        const changedCurrent = patchEntries(serverCurrentEntries, true);
        serverBrowserListCache.forEach((row) => {
          if (row && row.payload && Array.isArray(row.payload.entries)) {
            patchEntries(row.payload.entries);
          }
        });
        if (changedCurrent && options && options.render && typeof renderServerDataList === "function") {
          let patchedVisible = false;
          if (typeof syncLessonVaultChartFromChip === "function") {
            changedVisibleEntries.forEach((entry) => {
              const entryPaths = [
                entry.path,
                entry.effective_path,
                entry.link_target,
                entry.linked_path,
                entry.sourcePath,
                entry.source_path,
                entry.original_path,
                serverLearningPathForEntry(entry),
              ].map((value) => normalizeServerPathValue(value || "")).filter(Boolean);
              if (syncLessonVaultChartFromChip(entryPaths, entry, { retryMs: 160 })) {
                patchedVisible = true;
              }
            });
          }
          if (patchedVisible) {
            return result || null;
          }
          const cachedRow = getCachedServerBrowserListRow(serverBrowserPath || "", owner || serverTaskOwnerContext || "");
          if (cachedRow && cachedRow.payload) {
            renderServerDataList(cachedRow.payload);
          }
        }
        return result || null;
      };

      if (typeof window !== "undefined") {
        window.__ftRefreshLessonVaultItemStudyFromServer = refreshLessonVaultItemStudyFromServer;
      }

      const clearServerBrowserListCache = () => {
        serverBrowserListCache.clear();
        serverLessonProgressPrefetchCache.clear();
        serverBrowserPathWarmInflight.clear();
        serverSpaceVFileStatsCache.clear();
        serverCurrentEntries = [];
        serverBrowserFolderPrefetchQueue.length = 0;
        serverBrowserFolderPrefetchSeen.clear();
        serverBrowserFolderPrefetchBusy = false;
        if (serverLessonProgressPrefetchTimer) {
          window.clearTimeout(serverLessonProgressPrefetchTimer);
          serverLessonProgressPrefetchTimer = 0;
        }
        if (serverBrowserFolderPrefetchTimer) {
          window.clearTimeout(serverBrowserFolderPrefetchTimer);
          serverBrowserFolderPrefetchTimer = 0;
        }
      };

      // Added 2026-07-23: invalidate only the learner scope changed by an admin mutation.
      const clearServerBrowserListCacheForOwner = (owner = "") => {
        const target = clean(owner || "").toLowerCase();
        if (!target) {
          clearServerBrowserListCache();
          return;
        }
        for (const [key] of Array.from(serverBrowserListCache.entries())) {
          const parts = String(key || "").split("|");
          if (clean(parts[3] || "").toLowerCase() === target) {
            serverBrowserListCache.delete(key);
            serverBrowserFolderPrefetchSeen.delete(key);
          }
        }
        for (const [key] of Array.from(serverBrowserPathWarmInflight.entries())) {
          if (clean(String(key || "").split("|")[3] || "").toLowerCase() === target) {
            serverBrowserPathWarmInflight.delete(key);
          }
        }
        serverLessonProgressPrefetchCache.forEach((_, key) => {
          if (clean(String(key || "").split("|")[1] || "").toLowerCase() === target) {
            serverLessonProgressPrefetchCache.delete(key);
          }
        });
        if (authUsernameMatches(serverTaskOwnerContext, target)) {
          serverCurrentEntries = [];
        }
      };

      const clearServerLessonProgressPrefetchCache = (paths = [], space = "") => {
        const wantedPaths = new Set((Array.isArray(paths) ? paths : [paths])
          .map((path) => normalizeServerPathValue(path).toLowerCase())
          .filter(Boolean));
        const wantedSpace = clean(space || "").toLowerCase();
        if (!wantedPaths.size && !wantedSpace) {
          serverLessonProgressPrefetchCache.clear();
          return;
        }
        for (const key of Array.from(serverLessonProgressPrefetchCache.keys())) {
          const parts = String(key || "").split("|");
          const keySpace = clean(parts[2] || "").toLowerCase();
          const keyPath = normalizeServerPathValue(parts.slice(3).join("|")).toLowerCase();
          if ((!wantedSpace || keySpace === wantedSpace) && (!wantedPaths.size || wantedPaths.has(keyPath))) {
            serverLessonProgressPrefetchCache.delete(key);
          }
        }
      };

      const clearLessonProgressDisplayCaches = (paths = [], space = "") => {
        clearServerLessonProgressPrefetchCache(paths, space);
        // Progress saves already patch Lesson Vault and Space Task in RAM.
        // Clearing the task cache here forces a redundant server read on Back.
      };

      const refreshServerBrowserManifestSignatureIfNeeded = async (options = {}) => {
        const force = Boolean(options && options.force);
        if (!force && Date.now() - serverBrowserManifestStatusCheckedAt < SERVER_BROWSER_MANIFEST_STATUS_MIN_MS) {
          return getServerBrowserManifestSignature();
        }
        if (serverBrowserManifestStatusPromise) {
          return serverBrowserManifestStatusPromise;
        }
        serverBrowserManifestStatusPromise = (async () => {
          try {
            const result = await fetchServerJson(`/server-data/manifest-status?ts=${Date.now()}`);
            const payload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
            const nextSignature = clean(payload.signature || payload.manifest_signature || "");
            const previousSignature = getServerBrowserManifestSignature();
            serverBrowserManifestStatusCheckedAt = Date.now();
            if (nextSignature && previousSignature && nextSignature !== previousSignature) {
              clearServerBrowserListCache();
              try {
                localStorage.setItem(SERVER_BROWSER_MANIFEST_REFRESH_KEY, String(Date.now()));
              } catch (error) {
              }
            }
            if (nextSignature) {
              rememberServerBrowserManifestSignature(nextSignature);
            }
            return nextSignature || previousSignature;
          } catch (error) {
            serverBrowserManifestStatusCheckedAt = Date.now();
            return getServerBrowserManifestSignature();
          } finally {
            serverBrowserManifestStatusPromise = null;
          }
        })();
        return serverBrowserManifestStatusPromise;
      };

      const invalidateServerBrowserDataAfterMutation = () => {
        clearServerBrowserListCache();
        try {
          localStorage.setItem(SERVER_BROWSER_MANIFEST_REFRESH_KEY, String(Date.now()));
        } catch (error) {
        }
      };

      const scheduleServerBrowserFolderPrefetch = (delayMs = SERVER_BROWSER_FOLDER_PREFETCH_DELAY_MS) => {
        if (serverBrowserFolderPrefetchTimer || serverBrowserFolderPrefetchBusy || !serverBrowserFolderPrefetchQueue.length) {
          return;
        }
        serverBrowserFolderPrefetchTimer = window.setTimeout(async () => {
          serverBrowserFolderPrefetchTimer = 0;
          if (serverBrowserFolderPrefetchBusy || !serverBrowserFolderPrefetchQueue.length) {
            return;
          }
          const job = serverBrowserFolderPrefetchQueue.shift();
          if (!job || !job.path) {
            scheduleServerBrowserFolderPrefetch(0);
            return;
          }
          serverBrowserFolderPrefetchBusy = true;
          try {
            const row = getCachedServerBrowserListRow(job.path, job.taskOwner || "");
            if (!row) {
              const query = new URLSearchParams();
              query.set("path", job.path);
              query.set("defer_task_board", "1");
              if (clean(job.taskOwner || "")) {
                query.set("task_owner", clean(job.taskOwner || ""));
              }
              const result = await fetchServerJson(`/server-data/list?${query.toString()}`);
              rememberServerBrowserList(job.path, job.taskOwner || "", result.payload);
            }
          } catch (error) {
          } finally {
            serverBrowserFolderPrefetchBusy = false;
            if (serverBrowserFolderPrefetchQueue.length) {
              scheduleServerBrowserFolderPrefetch();
            }
          }
        }, Math.max(0, Number(delayMs || 0)));
      };

      const queueServerBrowserFolderPrefetch = (relativePath = "", taskOwner = "") => {
        const pathValue = normalizeServerPathValue(relativePath || "");
        if (!pathValue || document.visibilityState === "hidden") {
          return;
        }
        const owner = clean(taskOwner || "");
        const key = serverBrowserListCacheKey(pathValue, owner);
        if (serverBrowserFolderPrefetchSeen.has(key) || getCachedServerBrowserListRow(pathValue, owner)) {
          return;
        }
        serverBrowserFolderPrefetchSeen.add(key);
        serverBrowserFolderPrefetchQueue.push({ path: pathValue, taskOwner: owner });
        while (serverBrowserFolderPrefetchQueue.length > SERVER_BROWSER_FOLDER_PREFETCH_QUEUE_LIMIT) {
          serverBrowserFolderPrefetchQueue.shift();
        }
        scheduleServerBrowserFolderPrefetch();
      };

      const warmServerBrowserPathCache = async (relativePath = "", taskOwner = "", options = {}) => {
        const pathValue = normalizeServerPathValue(relativePath || "");
        if (document.visibilityState === "hidden") {
          return false;
        }
        const owner = clean(taskOwner || "");
        const force = Boolean(options && options.force);
        const cacheKey = serverBrowserListCacheKey(pathValue, owner);
        if (!force && getCachedServerBrowserListRow(pathValue, owner)) {
          return true;
        }
        if (serverBrowserPathWarmInflight.has(cacheKey)) {
          return serverBrowserPathWarmInflight.get(cacheKey);
        }
        const task = (async () => {
          try {
            const query = new URLSearchParams();
            query.set("path", pathValue);
            query.set("defer_task_board", "1");
            if (owner) {
              query.set("task_owner", owner);
            }
            const result = await fetchServerJson(`/server-data/list?${query.toString()}`);
            rememberServerBrowserList(pathValue, owner, result.payload);
            return true;
          } catch (_error) {
            return false;
          } finally {
            serverBrowserPathWarmInflight.delete(cacheKey);
          }
        })();
        serverBrowserPathWarmInflight.set(cacheKey, task);
        return task;
      };

      const currentLessonVaultFolderPath = () => {
        const sourcePath = normalizeServerPathValue(
          (currentLessonSource && currentLessonSource.path) ||
          (typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "")
        );
        if (sourcePath && /\.[A-Za-z0-9_]+$/.test(sourcePath.split("/").pop() || "")) {
          return serverParentPathForFile(sourcePath);
        }
        return sourcePath || normalizeServerPathValue(serverBrowserPath || getStoredServerPath() || "");
      };

      const scheduleCurrentLessonVaultCacheWarm = (delayMs = 1200, options = {}) => {
        const opts = options && typeof options === "object" ? options : {};
        if (!authToken) {
          return;
        }
        const folderPath = currentLessonVaultFolderPath();
        if (!folderPath && !opts.allowRoot) {
          return;
        }
        const now = Date.now();
        const minGap = Math.max(5000, Number(opts.minGapMs) || 45000);
        if (!opts.force && now - currentLessonVaultCacheWarmLastAt < minGap) {
          return;
        }
        if (currentLessonVaultCacheWarmTimer) {
          window.clearTimeout(currentLessonVaultCacheWarmTimer);
        }
        currentLessonVaultCacheWarmTimer = window.setTimeout(() => {
          currentLessonVaultCacheWarmTimer = 0;
          currentLessonVaultCacheWarmLastAt = Date.now();
          void warmServerBrowserPathCache(folderPath, clean(opts.taskOwner || ""), {
            force: Boolean(opts.force),
          });
        }, Math.max(0, Number(delayMs) || 0));
      };

      const prefetchServerBrowserChildFolders = (payload = {}, taskOwnerOverride = "") => {
        const entries = Array.isArray(payload && payload.entries) ? payload.entries : [];
        if (!entries.length || document.visibilityState === "hidden") {
          return;
        }
        const owner = clean(taskOwnerOverride || payload.task_owner || (!payload.admin ? payload.username : "") || "");
        entries
          .filter((entry) => entry && entry.type === "folder" && normalizeServerPathValue(entry.path || ""))
          .slice(0, SERVER_BROWSER_FOLDER_PREFETCH_LIMIT)
          .forEach((entry) => queueServerBrowserFolderPrefetch(entry.path, clean(entry.task_owner || owner)));
      };

      const getServerContextMenuNode = () => {
        if (serverContextMenuNode && document.body.contains(serverContextMenuNode)) {
          return serverContextMenuNode;
        }
        serverContextMenuNode = document.createElement("div");
        serverContextMenuNode.className = "ft-server-context-menu";
        serverContextMenuNode.hidden = true;
        serverContextMenuNode.setAttribute("role", "menu");
        document.body.appendChild(serverContextMenuNode);
        return serverContextMenuNode;
      };

      const hideServerContextMenu = () => {
        if (serverContextMenuNode) {
          serverContextMenuNode.hidden = true;
          serverContextMenuNode.textContent = "";
        }
      };

      const serverAdminPasteFallbackDestination = () => {
        if (!currentAuthIsAdmin) {
          return "";
        }
        const owner = normalizeServerPathValue(
          serverTaskOwnerContext
          || (currentTaskPayload && currentTaskPayload.task_owner)
          || "",
        );
        if (owner && serverPathTop(owner) !== "common") {
          return owner;
        }
        return "";
      };

      const serverEntryCanReceivePaste = (entry = null) => {
        if (!entry) {
          return Boolean(serverBrowserPath || serverAdminPasteFallbackDestination());
        }
        return clean(entry.type) === "folder" && clean(entry.path);
      };

      const serverContextDestinationPath = (entry = null) => {
        if (entry && serverEntryCanReceivePaste(entry)) {
          return normalizeServerPathValue(entry.path || "");
        }
        const currentPath = normalizeServerPathValue(serverBrowserPath || "");
        if (currentPath) {
          return currentPath;
        }
        return serverAdminPasteFallbackDestination();
      };

      const serverLearningPathForEntry = (entry = {}) => normalizeServerPathValue(entry && (entry.link_target || entry.effective_path || entry.path) || "");

      const serverLearningEntry = (entry = {}) => {
        const learningPath = serverLearningPathForEntry(entry);
        return learningPath && learningPath !== normalizeServerPathValue(entry.path || "")
          ? { ...entry, effective_path: learningPath, linked_path: normalizeServerPathValue(entry.path || "") }
          : entry;
      };

      const serverPathIsImmediateMission = (pathValue = "") => {
        const parts = normalizeServerPathValue(pathValue).split("/").filter(Boolean);
        return parts.length >= 2 && clean(parts[1]).toLowerCase() === "immediate mission";
      };

      const serverPathIsImmediateMissionRoot = (pathValue = "") => {
        const parts = normalizeServerPathValue(pathValue).split("/").filter(Boolean);
        return parts.length === 2 && clean(parts[1]).toLowerCase() === "immediate mission";
      };

      const serverPathTop = (pathValue = "") => {
        const parts = normalizeServerPathValue(pathValue).split("/").filter(Boolean);
        return clean(parts[0] || "").toLowerCase();
      };

      const serverPathIsOwnFolder = (pathValue = "") => {
        const username = clean(currentAuthUsername || "").toLowerCase();
        return Boolean(username && serverPathTop(pathValue) === username);
      };

      const serverEntryIsUserOwnedLink = (entry = null) => {
        if (!entry) {
          return false;
        }
        const creator = clean(entry.created_by || "").toLowerCase();
        const username = clean(currentAuthUsername || "").toLowerCase();
        const entryOwner = serverPathTop(entry.path || "");
        // Added 2026-07-24: compact/preloaded Vault rows may omit created_by,
        // but an SQLite placement ID under the signed-in user's root is still
        // unambiguously owned by that user. The server revalidates ownership.
        return Boolean(
          username
          && (
            creator === username
            || (
              entryOwner === username
              && Boolean(entry.vault_entry_id || entry.vault_folder_id)
            )
          )
        );
      };

      const serverEntryIsCommonItem = (entry = null) => Boolean(entry && entry.path && serverPathTop(entry.path) === "common");
      const serverEntryCanGetFromCommon = (entry = null) => {
        const parts = normalizeServerPathValue(entry && entry.path || "").split("/").filter(Boolean);
        return Boolean(parts.length >= 2 && parts[0].toLowerCase() === "common");
      };

      const serverUserCanPasteTo = (pathValue = "") => {
        const top = serverPathTop(pathValue);
        if (currentAuthIsAdmin) {
          return Boolean(top && top !== "common");
        }
        return serverPathIsOwnFolder(pathValue);
      };

      const serverDataOp = async (payload = {}, options = {}) => {
        const workingMessage = clean(options.workingMessage || "");
        if (workingMessage) {
          setLoadStatus(workingMessage);
          setTopOperationStatus(workingMessage, { working: true, progress: 0.18 });
        }
        try {
          const requestPayload = { ...(payload && typeof payload === "object" ? payload : {}) };
          const operationPath = normalizeServerPathValue(requestPayload.destination || requestPayload.target || requestPayload.source || requestPayload.path || "");
          const operationTop = serverPathTop(operationPath);
          const scopedTarget = clean(
            options.targetUser || requestPayload.target_user || requestPayload.user ||
            (currentAuthIsAdmin && operationTop && operationTop !== "common" ? operationTop : "") ||
            (!currentAuthIsAdmin ? currentAuthUsername : serverTaskOwnerContext) || "",
          );
          if (scopedTarget) {
            requestPayload.target_user = scopedTarget;
          }
          const result = await fetchServerJson("/server-data/op", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestPayload),
          });
          if (workingMessage) {
            setTopOperationStatus("Applying QM-Home changes...", { working: true, progress: 0.62 });
          }
          clearServerBrowserListCacheForOwner(scopedTarget);
          const refreshPath = normalizeServerPathValue(options.refreshPath || serverBrowserPath || "");
          if (workingMessage) {
            setTopOperationStatus("Refreshing Lesson Vault...", { working: true, progress: 0.82 });
          }
          const refreshOwner = Object.prototype.hasOwnProperty.call(options, "refreshOwner")
            ? clean(options.refreshOwner || "")
            : clean(options.targetUser || serverTaskOwnerContext || "");
          await loadServerDataPath(refreshPath, true, refreshOwner);
          const operationResult = result && result.payload && result.payload.result && typeof result.payload.result === "object"
            ? result.payload.result
            : {};
          if (typeof window !== "undefined" && typeof window.__ftVaultRealtimePublish === "function") {
            window.__ftVaultRealtimePublish({
              owner: clean(scopedTarget || currentAuthUsername || ""),
              revision: Number(operationResult.vault_revision || 0) || 0,
              result: operationResult,
            });
          }
          const doneMessage = clean(options.doneMessage || "") || "QM-Home updated.";
          setLoadStatus(doneMessage);
          if (workingMessage) {
            setTopOperationStatus(doneMessage, { working: false, progress: 1, autoHideMs: 2200 });
          }
          return result.payload;
        } catch (error) {
          if (workingMessage) {
            setTopOperationStatus(error && error.message ? error.message : "QM-Home operation failed.", {
              isError: true,
              working: false,
              progress: 1,
              autoHideMs: 4200,
            });
          }
          throw error;
        }
      };

      const runServerContextAction = async (action, entry = null) => {
        hideServerContextMenu();
        const userAllowedActions = new Set(["get-link", "copy-link", "cut", "paste", "new-vault-folder", "rename-placement", "move-placement-up", "move-placement-down", "delete-link", "clear-immediate"]);
        if (!currentAuthIsAdmin && !userAllowedActions.has(action)) {
          setLoadStatus("Only admins can manage QM-Home files.", true);
          return;
        }
        const entryPath = normalizeServerPathValue(entry && entry.path || "");
        try {
          if (action === "get-link") {
            if (!entryPath) return;
            if (!serverEntryCanGetFromCommon(entry)) {
              setLoadStatus("Get is only available for common lessons.", true);
              return;
            }
            const destination = normalizeServerPathValue(currentAuthUsername || "");
            if (!destination) {
              setLoadStatus("Your personal folder is not ready.", true);
              return;
            }
            await serverDataOp({
              action: "get",
              source: entryPath,
              destination,
            }, {
              refreshPath: destination,
              workingMessage: "Getting common item into your folder...",
              doneMessage: "Common item added to your Vault.",
            });
            serverBrowserPath = destination;
            rememberServerPath(destination);
            return;
          }
          if (action === "copy-link") {
            if (!entryPath) return;
            if (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(entry)) {
              setLoadStatus("You can only copy links you added yourself.", true);
              return;
            }
            serverDataClipboard = {
              mode: "copy_link",
              source: entryPath,
              name: entry && entry.name ? entry.name : entryPath.split("/").pop(),
            };
            setLoadStatus(`Vault placement ready: ${serverDataClipboard.name || "selected item"}. Right-click a folder to paste.`);
            return;
          }
          if (action === "cut") {
            if (!entryPath) return;
            if (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(entry)) {
              setLoadStatus("You can only cut links you added yourself.", true);
              return;
            }
            serverDataClipboard = {
              mode: "move",
              source: entryPath,
              name: entry && entry.name ? entry.name : entryPath.split("/").pop(),
            };
            setLoadStatus(`Move ready: ${serverDataClipboard.name || "selected item"}. Right-click a destination folder.`);
            return;
          }
          if (action === "paste") {
            if (!serverDataClipboard || !serverDataClipboard.source) {
              setLoadStatus("Nothing is ready to paste.", true);
              return;
            }
            const destination = serverContextDestinationPath(entry);
            if (!destination) {
              setLoadStatus("Choose a destination folder first.", true);
              return;
            }
            if (!serverUserCanPasteTo(destination)) {
              setLoadStatus("Learners can only paste into their own folder.", true);
              return;
            }
            setLoadStatus(serverDataClipboard.mode === "move" ? "Moving Vault placement..." : "Creating Vault placement...");
            await serverDataOp({
              action: serverDataClipboard.mode,
              source: serverDataClipboard.source,
              destination,
            }, {
              refreshPath: destination,
              workingMessage: serverDataClipboard.mode === "move" ? "Moving Vault placement..." : "Creating Vault placement...",
              doneMessage: serverDataClipboard.mode === "move" ? "Vault placement moved." : "Vault placement created.",
            });
            serverBrowserPath = destination;
            rememberServerPath(destination);
            if (serverDataClipboard.mode === "move") {
              serverDataClipboard = null;
            }
            return;
          }
          if (action === "delete-link") {
            if (!entryPath) return;
            if (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(entry)) {
              setLoadStatus("You can only remove links you added yourself.", true);
              return;
            }
            setLoadStatus("Removing item from Vault...");
            await serverDataOp({
              action: "delete_link",
              source: entryPath,
            }, {
              workingMessage: "Removing item from Vault...",
              doneMessage: "Item removed from Vault. Lesson data and progress were kept.",
            });
            return;
          }
          if (action === "admin-add-vault" || action === "admin-assign-task") {
            if (!currentAuthIsAdmin || !entryPath || serverPathTop(entryPath) !== "common") {
              setLoadStatus("Choose an item from Common Library first.", true);
              return;
            }
            const picker = typeof openAdminVaultTargetPicker === "function"
              ? await openAdminVaultTargetPicker({
                title: action === "admin-add-vault" ? "Add to Vault" : "Assign as Task",
                action: action === "admin-add-vault" ? "add" : "assign",
                body: action === "admin-add-vault"
                  ? "Choose My account or another user, then a virtual destination folder."
                  : "Choose Myself or another user who should receive this task.",
              })
              : "";
            const pickerUser = clean(picker && typeof picker === "object" ? picker.username : picker);
            const pickerDestination = clean(picker && typeof picker === "object" ? picker.destination : pickerUser);
            if (!pickerUser) return;
            if (action === "admin-add-vault") {
              await serverDataOp({
                action: "copy_link",
                source: entryPath,
                destination: pickerDestination || pickerUser,
                target_user: pickerUser,
              }, {
                targetUser: pickerUser,
                refreshPath: pickerDestination || pickerUser,
                refreshOwner: pickerUser,
                workingMessage: "Adding Common item to Vault...",
                doneMessage: `Added to @${pickerUser}'s Vault. No physical copy was created.`,
              });
            } else if (entry && entry.type === "folder" && typeof chooseSpaceTaskFolder === "function") {
              await chooseSpaceTaskFolder(pickerUser, entry, null, { skipConfirm: true });
            } else if (typeof addLessonTask === "function") {
              await addLessonTask(pickerUser, entry, null, { skipConfirm: true });
            }
            return;
          }
          if (action === "new-vault-folder") {
            const destination = serverContextDestinationPath(entry) || normalizeServerPathValue(serverBrowserPath || currentAuthUsername || "");
            if (!destination || !serverUserCanPasteTo(destination)) {
              setLoadStatus("Choose a folder in your personal Vault first.", true);
              return;
            }
            const name = clean(window.prompt("New Vault folder name:", "New folder") || "");
            if (!name) return;
            await serverDataOp({ action: "create_folder", destination, name }, {
              refreshPath: destination,
              workingMessage: "Creating virtual folder...",
              doneMessage: "Virtual folder saved. No physical folder was created.",
            });
            return;
          }
          if (action === "rename-placement") {
            if (!entryPath || !serverEntryIsUserOwnedLink(entry)) return;
            const currentName = clean(entry && entry.name || entryPath.split("/").pop() || "Lesson");
            const nextName = clean(window.prompt("Rename this Vault placement:", currentName) || "");
            if (!nextName || nextName === currentName) return;
            await serverDataOp({ action: "rename", source: entryPath, name: nextName }, {
              refreshPath: serverParentPathForFile(entryPath),
              workingMessage: "Renaming Vault placement...",
              doneMessage: "Vault placement renamed. Physical files were not changed.",
            });
            return;
          }
          if (action === "move-placement-up" || action === "move-placement-down") {
            if (!entryPath || !serverEntryIsUserOwnedLink(entry)) return;
            const direction = action === "move-placement-up" ? "up" : "down";
            await serverDataOp({ action: "reorder", source: entryPath, direction }, {
              refreshPath: serverParentPathForFile(entryPath),
              workingMessage: "Reordering Vault placement...",
              doneMessage: "Vault order saved in SQLite.",
            });
            return;
          }
          if (action === "clear-immediate") {
            const sourcePath = entryPath || normalizeServerPathValue(serverBrowserPath || "");
            if (!sourcePath) return;
            if (!serverPathIsImmediateMission(sourcePath)) {
              setLoadStatus("Clear is only available inside Immediate Mission.", true);
              return;
            }
            setLoadStatus("Clearing Immediate Mission item...");
            const refreshPath = entry && entry.type === "folder"
              ? serverParentPathForFile(sourcePath)
              : (entryPath ? serverParentPathForFile(sourcePath) : sourcePath);
            await serverDataOp({
              action: "clear_immediate",
              source: sourcePath,
            }, {
              refreshPath: refreshPath || serverBrowserPath,
              workingMessage: "Clearing Immediate Mission...",
              doneMessage: "Immediate Mission cleaned.",
            });
          }
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "QM-Home operation failed.", true);
        }
      };

      const addServerContextButton = (menu, label, action, entry = null, disabled = false) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.disabled = Boolean(disabled);
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void runServerContextAction(action, entry);
        });
        menu.appendChild(button);
      };

      const showServerContextMenu = (event, entry = null) => {
        const entryPath = normalizeServerPathValue(entry && entry.path || "");
        const contextPath = entryPath || normalizeServerPathValue(serverBrowserPath || "");
        const canClearImmediate = Boolean(contextPath && serverPathIsImmediateMission(contextPath));
        const canGetCommon = Boolean(!currentAuthIsAdmin && entryPath && serverEntryCanGetFromCommon(entry));
        const canManageOwnLink = Boolean(!currentAuthIsAdmin && entryPath && serverEntryIsUserOwnedLink(entry));
        const pasteDestination = serverContextDestinationPath(entry);
        const canPaste = Boolean(serverDataClipboard && serverDataClipboard.source && pasteDestination && serverUserCanPasteTo(pasteDestination));
        const canCreateVaultFolder = Boolean(pasteDestination && serverUserCanPasteTo(pasteDestination));
        if (!currentAuthIsAdmin && !canClearImmediate && !canGetCommon && !canManageOwnLink && !canPaste && !canCreateVaultFolder) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        const menu = getServerContextMenuNode();
        menu.textContent = "";
        if (entryPath && currentAuthIsAdmin && serverPathTop(entryPath) === "common") {
          addServerContextButton(menu, "Add to Vault...", "admin-add-vault", entry);
          addServerContextButton(menu, "Assign as Task...", "admin-assign-task", entry);
        } else if (entryPath && currentAuthIsAdmin) {
          addServerContextButton(menu, "Copy to Vault", "copy-link", entry);
          if (entry && (entry.virtual || entry.vault_entry_id || entry.vault_folder_id)) {
            addServerContextButton(menu, "Rename placement", "rename-placement", entry);
            addServerContextButton(menu, "Move placement up", "move-placement-up", entry);
            addServerContextButton(menu, "Move placement down", "move-placement-down", entry);
            addServerContextButton(menu, "Move placement", "cut", entry);
            addServerContextButton(menu, "Remove from Vault", "delete-link", entry);
          }
        } else if (entryPath && canGetCommon) {
          addServerContextButton(menu, "Get to my folder", "get-link", entry);
        } else if (entryPath && canManageOwnLink) {
          addServerContextButton(menu, "Copy placement", "copy-link", entry);
          addServerContextButton(menu, "Rename placement", "rename-placement", entry);
          addServerContextButton(menu, "Move placement up", "move-placement-up", entry);
          addServerContextButton(menu, "Move placement down", "move-placement-down", entry);
          addServerContextButton(menu, "Move placement", "cut", entry);
          addServerContextButton(menu, "Remove from Vault", "delete-link", entry);
        }
        if (canClearImmediate) {
          addServerContextButton(menu, entryPath ? "Clear this mission item" : "Clear this mission folder", "clear-immediate", entry);
        }
        if (canCreateVaultFolder) {
          addServerContextButton(menu, "New Vault folder", "new-vault-folder", entry);
        }
        if (currentAuthIsAdmin || serverDataClipboard) {
          addServerContextButton(menu, serverDataClipboard && serverDataClipboard.mode === "move" ? "Move here" : "Place in Vault here", "paste", entry, !canPaste);
        }
        if (!menu.children.length) {
          return;
        }
        menu.hidden = false;
        const width = menu.offsetWidth || 210;
        const height = menu.offsetHeight || 140;
        const x = Math.max(8, Math.min(window.innerWidth - width - 8, Number(event.clientX || 0)));
        const y = Math.max(8, Math.min(window.innerHeight - height - 8, Number(event.clientY || 0)));
        menu.style.left = `${x}px`;
        menu.style.top = `${y}px`;
      };

      const selectedServerEntry = () => {
        const selectedPath = normalizeServerPathValue(serverBrowserFocusedFilePath || "");
        if (!selectedPath || !Array.isArray(serverCurrentEntries)) {
          return null;
        }
        return serverCurrentEntries.find((entry) => normalizeTaskPath(entry && entry.path || "") === normalizeTaskPath(selectedPath)) || null;
      };

      const confirmServerLinkedDelete = (entry = {}) => new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "ft-server-delete-confirm";
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        const itemName = clean(entry.name || entry.path || "selected item");
        overlay.innerHTML = `
          <div class="ft-server-delete-dialog">
            <span class="ft-server-delete-grid" aria-hidden="true"></span>
            <span class="ft-server-delete-circuit" aria-hidden="true"></span>
            <div class="ft-server-delete-kicker">Vault placement</div>
            <div class="ft-server-delete-title">Remove from Vault?</div>
            <div class="ft-server-delete-name">This removes only this placement. Physical lesson files and learning progress stay untouched.<br><b></b></div>
            <div class="ft-server-delete-actions">
              <button type="button" data-choice="no">No</button>
              <button type="button" data-choice="yes">Yes</button>
            </div>
          </div>
        `;
        const nameNode = overlay.querySelector(".ft-server-delete-name b");
        if (nameNode) {
          nameNode.textContent = itemName;
        }
        let done = false;
        const cleanup = (value) => {
          if (done) return;
          done = true;
          document.removeEventListener("keydown", onKeyDown, true);
          overlay.remove();
          resolve(Boolean(value));
        };
        const onKeyDown = (event) => {
          const key = clean(event.key || "").toLowerCase();
          if (key === "escape") {
            event.preventDefault();
            event.stopPropagation();
            cleanup(false);
          }
          if (key === "enter") {
            event.preventDefault();
            event.stopPropagation();
            cleanup(true);
          }
        };
        overlay.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("button[data-choice]") : null;
          if (button) {
            event.preventDefault();
            cleanup(button.dataset.choice === "yes");
            return;
          }
          if (event.target === overlay) {
            cleanup(false);
          }
        });
        document.body.appendChild(overlay);
        document.addEventListener("keydown", onKeyDown, true);
        window.setTimeout(() => {
          const noButton = overlay.querySelector('button[data-choice="no"]');
          if (noButton && noButton.focus) noButton.focus();
        }, 30);
      });

      const handleServerBrowserClipboardShortcut = (event) => {
        if (!serverBrowser || serverBrowser.hidden) {
          return;
        }
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        const key = clean(event.key || "").toLowerCase();
        if (key === "delete" && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
          if (!serverBrowser.contains(event.target) && event.target !== document.body && event.target !== document.documentElement) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const activeEntry = selectedServerEntry();
          if (!activeEntry) {
            setLoadStatus("Select a linked file or folder before pressing Delete.", true);
            return;
          }
          if (!(activeEntry.linked || activeEntry.link_target) || (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(activeEntry))) {
            setLoadStatus("Delete key only removes linked files or linked folders. Original files are protected.", true);
            return;
          }
          void (async () => {
            const confirmed = await confirmServerLinkedDelete(activeEntry);
            if (!confirmed) {
              setLoadStatus("Delete cancelled.");
              return;
            }
            await runServerContextAction("delete-link", activeEntry);
          })();
          return;
        }
        if (!(event.ctrlKey || event.metaKey) || !["c", "x", "v"].includes(key)) {
          return;
        }
        if (!serverBrowser.contains(event.target) && event.target !== document.body && event.target !== document.documentElement) {
          return;
        }
        const activeEntry = selectedServerEntry();
        if (key === "c") {
          if (!activeEntry) {
            setLoadStatus("Select a file or folder before pressing Ctrl+C.", true);
            return;
          }
          if (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(activeEntry)) {
            setLoadStatus("You can only copy links you added yourself.", true);
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          void runServerContextAction("copy-link", activeEntry);
          return;
        }
        if (key === "x") {
          if (!activeEntry) {
            setLoadStatus("Select a file or folder before pressing Ctrl+X.", true);
            return;
          }
          if (!currentAuthIsAdmin && !serverEntryIsUserOwnedLink(activeEntry)) {
            setLoadStatus("You can only cut links you added yourself.", true);
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          void runServerContextAction("cut", activeEntry);
          return;
        }
        if (key === "v") {
          const destination = serverContextDestinationPath(null);
          if (!currentAuthIsAdmin && !serverUserCanPasteTo(destination)) {
            setLoadStatus("Learners can only paste into their own folder.", true);
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          void runServerContextAction("paste", null);
        }
      };

      document.addEventListener("pointerdown", (event) => {
        if (!serverContextMenuNode || serverContextMenuNode.hidden) {
          return;
        }
        if (event.target && serverContextMenuNode.contains(event.target)) {
          return;
        }
        hideServerContextMenu();
      }, true);
      document.addEventListener("keydown", handleServerBrowserClipboardShortcut, true);
      window.addEventListener("resize", hideServerContextMenu);
      if (serverListNode) {
        serverListNode.addEventListener("contextmenu", (event) => {
          if (event.target && event.target.closest && event.target.closest(".ft-server-item")) {
            return;
          }
          showServerContextMenu(event, null);
        });
      }

      const serverStorageKey = (baseKey) => {
        const username = clean(currentAuthUsername || (authUser && authUser.value));
        return username ? `${baseKey}:${username}` : baseKey;
      };
      const serverStorageKeyCandidates = (baseKey) => {
        const primary = serverStorageKey(baseKey);
        // 2026-07-31: authenticated navigation must never inherit another user's legacy unscoped last-file state.
        return primary === baseKey ? [primary] : [primary];
      };
      const readServerStorageValue = (baseKey) => {
        try {
          for (const key of serverStorageKeyCandidates(baseKey)) {
            const value = localStorage.getItem(key) || "";
            if (value) {
              return value;
            }
          }
        } catch (error) {
        }
        return "";
      };

      let serverLastFileState = { file: null, recentFiles: [], selectedFolder: null, updated_at: "" };
      let serverLastFileEtag = "";
      let serverLastFileHasServerPayload = false;
      let serverLastFolderState = { path: "", task_owner: "", selected_at: "", source: "" };
      let serverLastFileSyncTimer = 0;
      let serverLastFilePostPromise = null;
      let serverLastFilePostQueued = false;
      let serverLastFileLastSemanticSignature = "";
      let serverLastFileLastSemanticAt = 0;
      let serverLastFileRetryAfter = 0;
      let lessonVaultFolderDbPromise = null;
      const LESSON_VAULT_FOLDER_DB_NAME = "future-lesson-vault-folder-v1";
      const LESSON_VAULT_FOLDER_STORE = "folder_state";
      let serverLastFileFetchPromise = null;
      let serverLastFileFetchUsername = "";
      let serverLastFileFetchGeneration = 0;
      let lessonVaultRestoreGeneration = 0;
      let lessonVaultRestoreState = null;

      // 2026-07-31: one generation-scoped state machine coordinates login identity, last-file, tree render and scroll.
      const recordLessonVaultRestorePhase = (phase = "", extra = {}) => {
        const state = lessonVaultRestoreState;
        if (!state) return null;
        const row = {
          phase: clean(phase || "unknown"),
          at: Date.now(),
          generation: state.generation,
          username: state.username,
          targetFile: state.targetFile || "",
          targetTree: state.targetTree || "",
          restoreCalls: Number(state.restoreCalls || 0),
          ...extra,
        };
        state.timeline.push(row);
        if (state.timeline.length > 80) state.timeline.splice(0, state.timeline.length - 80);
        try {
          window.__futureLessonVaultRestoreTrace = state.timeline.slice();
          document.documentElement.dataset.futureLessonVaultRestoreTrace = JSON.stringify(row);
        } catch (error) {
        }
        return row;
      };

      const beginLessonVaultLoginRestore = (username = "", options = {}) => {
        const normalizedUser = clean(username || "");
        lessonVaultRestoreGeneration += 1;
        try {
          if (typeof lessonVaultRestoreWaitCleanup === "function") lessonVaultRestoreWaitCleanup();
        } catch (error) {
        }
        serverLastFileFetchPromise = null;
        serverLastFileFetchUsername = "";
        serverLastFileFetchGeneration = lessonVaultRestoreGeneration;
        serverLastFileEtag = "";
        serverLastFileHasServerPayload = false;
        serverLastFileState = { file: null, recentFiles: [], selectedFolder: null, updated_at: "" };
        serverLastFolderState = { path: "", task_owner: "", selected_at: "", source: "" };
        lessonVaultRestoreState = {
          generation: lessonVaultRestoreGeneration,
          username: normalizedUser,
          phase: "authenticated",
          startedAt: Number(options.startedAt || Date.now()) || Date.now(),
          targetFile: "",
          targetTree: "",
          targetOwner: normalizedUser,
          targetPaths: [],
          lastFileReady: false,
          treeReady: false,
          targetRendered: false,
          scrolled: false,
          cancelled: false,
          userInteracted: false,
          restoreCalls: 0,
          completedScrollTop: null,
          timeline: [],
        };
        if (typeof serverBrowserLoadSerial === "number") serverBrowserLoadSerial += 1;
        if (serverBrowserActiveAbort) {
          try { serverBrowserActiveAbort.abort(); } catch (error) {}
          serverBrowserActiveAbort = null;
        }
        recordLessonVaultRestorePhase("authenticated");
        return lessonVaultRestoreState;
      };

      const currentLessonVaultRestoreState = (generation = 0) => {
        const state = lessonVaultRestoreState;
        if (!state || state.cancelled) return null;
        if (generation && Number(generation) !== Number(state.generation)) return null;
        if (!authUsernameMatches(state.username, currentAuthUsername || "")) return null;
        return state;
      };

      const lessonVaultRestoreTargetRows = (state = serverLastFileState) => {
        const rows = [];
        const seen = new Set();
        const add = (value) => {
          const row = normalizeServerRecentRow(value);
          const key = normalizeTaskPath(row && row.path || "");
          if (!row || !key || seen.has(key) || !serverRecentRowIsResumeable(row)) return;
          seen.add(key);
          rows.push(row);
        };
        add(state && state.file);
        if (state && Array.isArray(state.recentFiles)) state.recentFiles.forEach(add);
        return rows;
      };

      const noteLessonVaultRestoreLastFile = (state = serverLastFileState, source = "last-file") => {
        const restore = currentLessonVaultRestoreState();
        if (!restore) return null;
        const rows = lessonVaultRestoreTargetRows(state);
        const target = rows[0] || null;
        restore.lastFileReady = true;
        restore.phase = "last-file-ready";
        restore.targetFile = normalizeServerPathValue(target && target.path || "");
        restore.targetTree = normalizeServerPathValue(target && (target.parentPath || serverParentPathForFile(target.path)) || "");
        restore.targetOwner = clean(target && target.task_owner || restore.username || "");
        restore.targetPaths = target ? Array.from(new Set([
          target.path,
          target.displayPath,
          target.sourcePath,
          target.effectivePath,
          target.linkTarget,
          target.linkedPath,
        ].map((value) => normalizeServerPathValue(value || "")).filter(Boolean))) : [];
        restore.candidates = rows;
        recordLessonVaultRestorePhase("last-file-ready", { source, candidateCount: rows.length });
        if (restore.pendingPayload && typeof scheduleLessonVaultLoginRestore === "function") {
          scheduleLessonVaultLoginRestore(restore.pendingPayload, "last-file-after-tree");
        }
        return restore;
      };

      const cancelLessonVaultLoginRestore = (reason = "cancelled", options = {}) => {
        const state = currentLessonVaultRestoreState(Number(options.generation || 0));
        if (!state || state.scrolled) return false;
        state.cancelled = true;
        state.userInteracted = Boolean(options.userInteracted);
        state.phase = "cancelled";
        recordLessonVaultRestorePhase("cancelled", { reason: clean(reason), userInteracted: state.userInteracted });
        return true;
      };

      window.__futureLessonVaultRestoreManager = {
        begin: beginLessonVaultLoginRestore,
        current: currentLessonVaultRestoreState,
        noteLastFile: noteLessonVaultRestoreLastFile,
        cancel: cancelLessonVaultLoginRestore,
        trace: () => lessonVaultRestoreState ? lessonVaultRestoreState.timeline.slice() : [],
      };

      const lessonLastFilePathFromEntry = (entry = {}) => {
        const source = entry && typeof entry === "object" ? entry : { path: entry };
        return normalizeServerPathValue(
          source.display_path
          || source.displayPath
          || source.sourcePath
          || source.source_path
          || source.linked_path
          || source.linkedPath
          || source.path
          || source.open_path
          || source.openPath
          || source.effective_path
          || source.effectivePath
          || source.link_target
          || source.linkTarget
          || ""
        );
      };

      const normalizeServerRecentRow = (item = null) => {
        const source = item && typeof item === "object" ? item : { path: item };
        const path = lessonLastFilePathFromEntry(source);
        const sourcePath = normalizeServerPathValue(source && (source.sourcePath || source.source_path || source.linked_path || source.linkedPath || source.path) || "");
        const effectivePath = normalizeServerPathValue(source && (source.effective_path || source.effectivePath || "") || "");
        const linkTarget = normalizeServerPathValue(source && (source.link_target || source.linkTarget || "") || "");
        const lessonId = clean(source && (source.lesson_id || source.lessonId || source.file_id || source.fileId || source.identity) || "");
        const taskOwner = clean(source && (source.task_owner || source.taskOwner) || serverTaskOwnerContext || currentAuthUsername || "");
        if (!path) {
          return null;
        }
        return {
          path,
          parentPath: normalizeServerPathValue(source.parentPath || source.parent || serverParentPathForFile(path)),
          title: clean(source.title || source.name || ""),
          space: clean(source.space || source.source || ""),
          page: Math.max(0, Math.floor(Number(source.page || source.currentPage || source.lastPage || 0) || 0)),
          pages: Math.max(0, Math.floor(Number(source.pages || source.totalPages || source.nodeCount || 0) || 0)),
          sourcePath,
          effectivePath,
          linkTarget,
          lesson_id: lessonId.toLowerCase().startsWith("ftg-lesson-") ? lessonId : "",
          file_id: lessonId.toLowerCase().startsWith("ftg-lesson-") ? lessonId : "",
          displayPath: normalizeServerPathValue(source && (source.display_path || source.displayPath || path) || path),
          task_owner: taskOwner,
          linkedPath: normalizeServerPathValue(source && (source.linked_path || source.linkedPath || "") || ""),
          accessedAt: clean(source.accessedAt || source.updatedAt || source.at || source.time || ""),
        };
      };

      const serverRecentRowIsResumeable = (row = null) => {
        const path = normalizeServerPathValue(row && row.path || "");
        return Boolean(path) && !serverPathIsImmediateMission(path);
      };

      const lessonVaultFolderBaseKey = (taskOwner = "") => `lesson-last-folder:${clean(taskOwner || "").toLowerCase() || "self"}`;
      const lessonVaultFolderStorageKey = (taskOwner = "") => serverStorageKey(lessonVaultFolderBaseKey(taskOwner));
      const lessonVaultFolderStorageKeyCandidates = (taskOwner = "") => serverStorageKeyCandidates(lessonVaultFolderBaseKey(taskOwner));

      const normalizeLessonVaultFolderState = (value = {}, fallbackOwner = "") => {
        const source = value && typeof value === "object" ? value : { path: value };
        const path = normalizeServerPathValue(source.path || source.folder || source.tree || source.parentPath || "");
        if (!path) {
          return null;
        }
        return {
          path,
          task_owner: clean(source.task_owner || source.taskOwner || fallbackOwner || ""),
          selected_at: clean(source.selected_at || source.selectedAt || source.updated_at || source.updatedAt || source.at || "") || new Date().toISOString(),
          source: clean(source.source || source.src || source.reason || ""),
        };
      };

      const openLessonVaultFolderDb = () => {
        if (!("indexedDB" in window)) {
          return Promise.resolve(null);
        }
        if (lessonVaultFolderDbPromise) {
          return lessonVaultFolderDbPromise;
        }
        lessonVaultFolderDbPromise = new Promise((resolve) => {
          try {
            const request = indexedDB.open(LESSON_VAULT_FOLDER_DB_NAME, 1);
            request.onupgradeneeded = () => {
              const db = request.result;
              if (!db.objectStoreNames.contains(LESSON_VAULT_FOLDER_STORE)) {
                db.createObjectStore(LESSON_VAULT_FOLDER_STORE, { keyPath: "key" });
              }
            };
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => resolve(null);
          } catch (error) {
            resolve(null);
          }
        });
        return lessonVaultFolderDbPromise;
      };

      const readLessonVaultFolderStateFromIndexedDb = async (taskOwner = "") => {
        const db = await openLessonVaultFolderDb();
        const keys = lessonVaultFolderStorageKeyCandidates(taskOwner);
        if (!db || !keys.length) {
          return null;
        }
        const readKey = (key) => new Promise((resolve) => {
          try {
            const request = db.transaction(LESSON_VAULT_FOLDER_STORE, "readonly").objectStore(LESSON_VAULT_FOLDER_STORE).get(key);
            request.onsuccess = () => resolve(normalizeLessonVaultFolderState(request.result || {}, taskOwner));
            request.onerror = () => resolve(null);
          } catch (error) {
            resolve(null);
          }
        });
        for (const key of keys) {
          const record = await readKey(key);
          if (record) {
            return record;
          }
        }
        return null;
      };

      const writeLessonVaultFolderStateToIndexedDb = async (taskOwner = "", state = {}) => {
        const db = await openLessonVaultFolderDb();
        const key = lessonVaultFolderStorageKey(taskOwner);
        const record = normalizeLessonVaultFolderState(state, taskOwner);
        if (!db || !key || !record) {
          return false;
        }
        return new Promise((resolve) => {
          try {
            const tx = db.transaction(LESSON_VAULT_FOLDER_STORE, "readwrite");
            tx.objectStore(LESSON_VAULT_FOLDER_STORE).put({ key, ...record });
            tx.oncomplete = () => resolve(true);
            tx.onerror = () => resolve(false);
            tx.onabort = () => resolve(false);
          } catch (error) {
            resolve(false);
          }
        });
      };

      const getStoredLessonVaultFolderState = (taskOwner = "") => {
        try {
          for (const key of lessonVaultFolderStorageKeyCandidates(taskOwner)) {
            const raw = localStorage.getItem(key) || "";
            if (!raw) {
              continue;
            }
            const parsed = JSON.parse(raw);
            const record = normalizeLessonVaultFolderState(parsed, taskOwner);
            if (record) {
              return record;
            }
          }
        } catch (error) {
        }
        return normalizeLessonVaultFolderState(serverLastFolderState || {}, taskOwner);
      };

      const readStoredLessonVaultFolderState = async (taskOwner = "") => {
        const indexedState = await readLessonVaultFolderStateFromIndexedDb(taskOwner);
        if (indexedState) {
          return indexedState;
        }
        return getStoredLessonVaultFolderState(taskOwner);
      };

      const rememberLessonVaultFolderState = (value = {}, options = {}) => {
        const taskOwner = clean(options.task_owner || options.taskOwner || value.task_owner || value.taskOwner || serverTaskOwnerContext || currentAuthUsername || "");
        const record = normalizeLessonVaultFolderState(value, taskOwner);
        if (!record) {
          return null;
        }
        serverLastFolderState = record;
        const key = lessonVaultFolderStorageKey(taskOwner);
        try {
          localStorage.setItem(key, JSON.stringify(record));
        } catch (error) {
        }
        if (authToken) {
          void writeLessonVaultFolderStateToIndexedDb(taskOwner, record);
        }
        return record;
      };

      const applyServerLastFileState = (payload = {}, options = {}) => {
        const source = payload && typeof payload === "object" ? (payload.state && typeof payload.state === "object" ? payload.state : payload) : {};
        const file = normalizeServerRecentRow(source.file || source);
        const rows = [];
        const seen = new Set();
        const add = (item) => {
          const row = normalizeServerRecentRow(item);
          const key = row && row.path ? row.path.toLowerCase() : "";
          if (!key || seen.has(key)) {
            return;
          }
          seen.add(key);
          rows.push(row);
        };
        if (file) add(file);
        if (Array.isArray(source.recentFiles)) {
          source.recentFiles.forEach(add);
        }
        if (options.preserveLocalRecent !== false) {
          readStoredServerRecentFiles().forEach(add);
        }
        serverLastFileState = {
          file: rows.find(serverRecentRowIsResumeable) || rows[0] || file || null,
          recentFiles: rows.slice(0, 20),
          selectedFolder: normalizeLessonVaultFolderState(source.selectedFolder || source.selected_folder || source.folder || serverLastFolderState || null, clean(source.task_owner || source.taskOwner || currentAuthUsername || "")),
          updated_at: clean(source.updated_at || source.updatedAt || ""),
        };
        if (serverLastFileState.selectedFolder) {
          serverLastFolderState = serverLastFileState.selectedFolder;
          try {
            localStorage.setItem(lessonVaultFolderStorageKey(serverLastFileState.selectedFolder.task_owner || ""), JSON.stringify(serverLastFileState.selectedFolder));
          } catch (error) {
          }
          void writeLessonVaultFolderStateToIndexedDb(serverLastFileState.selectedFolder.task_owner || "", serverLastFileState.selectedFolder);
        }
        if (serverLastFileState.file) {
          try {
            localStorage.setItem(serverStorageKey(SERVER_LAST_FILE_KEY), serverLastFileState.file.path);
            localStorage.setItem(serverStorageKey(SERVER_LAST_PATH_KEY), serverLastFileState.file.parentPath || serverParentPathForFile(serverLastFileState.file.path));
          } catch (error) {
          }
        }
        if (serverLastFileState.recentFiles.length) {
          writeStoredServerRecentFiles(serverLastFileState.recentFiles);
        }
        if (options.render !== false && typeof renderServerRecentFileShortcut === "function") {
          try {
            if (renderServerRecentFileShortcut() && serverNavNode) {
              serverNavNode.hidden = false;
            }
          } catch (error) {
          }
        }
        noteLessonVaultRestoreLastFile(serverLastFileState, clean(options.restoreSource || "last-file-state"));
        return serverLastFileState;
      };

      const syncServerLastFileFromServer = async (options = {}) => {
        const requestUsername = clean(currentAuthUsername || "");
        const requestGeneration = lessonVaultRestoreGeneration;
        const requestToken = clean(authToken || "");
        if (
          serverLastFileFetchPromise
          && authUsernameMatches(serverLastFileFetchUsername, requestUsername)
          && serverLastFileFetchGeneration === requestGeneration
        ) {
          return serverLastFileFetchPromise;
        }
        serverLastFileFetchUsername = requestUsername;
        serverLastFileFetchGeneration = requestGeneration;
        serverLastFileFetchPromise = (async () => {
          const recentFiles = readStoredServerRecentFiles();
          let serverState = null;
          let responseEtag = "";
          if (authToken) {
            try {
              const result = await fetchAuthJson("/server-data/last-file", {
                ifNoneMatch: serverLastFileHasServerPayload ? serverLastFileEtag : "",
                notModifiedPayload: serverLastFileHasServerPayload ? { ok: true, state: serverLastFileState } : null,
              });
              const payload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
              responseEtag = clean(result && result.etag || "");
              serverState = payload.state && typeof payload.state === "object" ? payload.state : null;
            } catch (error) {
              serverState = null;
            }
          }
          if (
            !authUsernameMatches(requestUsername, currentAuthUsername || "")
            || requestToken !== clean(authToken || "")
            || requestGeneration !== lessonVaultRestoreGeneration
          ) {
            recordLessonVaultRestorePhase("stale-last-file-ignored", { requestUsername });
            return serverLastFileState;
          }
          serverLastFileEtag = responseEtag;
          serverLastFileHasServerPayload = Boolean(serverState);
          const serverFile = serverState ? normalizeServerRecentRow(serverState.file || null) : null;
          const serverRecent = serverState && Array.isArray(serverState.recentFiles) ? serverState.recentFiles : [];
          const serverFolder = normalizeLessonVaultFolderState(serverState && (serverState.selectedFolder || serverState.selected_folder || serverState.folder) || {}, clean(serverState && (serverState.task_owner || serverState.taskOwner || currentAuthUsername || "")));
          const localFile = normalizeServerRecentRow(getStoredServerFile());
          const file = authToken
            ? (serverFile || serverRecent.find(serverRecentRowIsResumeable) || serverRecent[0] || localFile)
            : (serverFile || recentFiles[0] || localFile);
          const state = applyServerLastFileState(
            { file, recentFiles: [...serverRecent, ...recentFiles], selectedFolder: serverFolder },
            { ...options, restoreSource: "server-last-file" }
          );
          if (serverFolder) {
            serverLastFolderState = serverFolder;
          }
          return state;
        })();
        try {
          return await serverLastFileFetchPromise;
        } finally {
          if (
            authUsernameMatches(serverLastFileFetchUsername, requestUsername)
            && serverLastFileFetchGeneration === requestGeneration
          ) {
            serverLastFileFetchPromise = null;
          }
        }
      };

      const resolveLessonVaultRestoreTarget = async (options = {}) => {
        const routeTree = normalizeServerPathValue(options.routeTree || "");
        const routeFile = normalizeServerPathValue(options.routeFile || "");
        const routeTaskOwner = clean(options.routeTaskOwner || "");
        const routeTop = clean(routeTree.split("/").filter(Boolean)[0] || "");
        const inferredAdminOwner = currentAuthIsAdmin
          && routeTop
          && routeTop.toLowerCase() !== "common"
          && !authUsernameMatches(routeTop, currentAuthUsername)
          ? routeTop
          : "";
        const preferredOwner = clean(routeTaskOwner || inferredAdminOwner || serverTaskOwnerContext || currentAuthUsername || "");
        if (routeTree) {
          return {
            tree: routeTree,
            task_owner: preferredOwner,
            file: routeFile,
            paths: [routeFile].filter(Boolean),
            source: "route",
          };
        }
        const restore = currentLessonVaultRestoreState();
        const restoreFile = normalizeServerPathValue(restore && restore.targetFile || "");
        const restoreTree = normalizeServerPathValue(restore && restore.targetTree || (restoreFile ? serverParentPathForFile(restoreFile) : ""));
        if (restoreTree) {
          return {
            tree: restoreTree,
            task_owner: clean(restore && restore.targetOwner || preferredOwner || ""),
            file: restoreFile,
            paths: restore && Array.isArray(restore.targetPaths) ? restore.targetPaths.slice() : [restoreFile].filter(Boolean),
            source: "last_file",
          };
        }
        const localFolder = await readStoredLessonVaultFolderState(preferredOwner);
        if (localFolder && localFolder.path) {
          return {
            tree: localFolder.path,
            task_owner: clean(localFolder.task_owner || preferredOwner || ""),
            source: "local_folder",
          };
        }
        const serverFolder = normalizeLessonVaultFolderState(serverLastFileState && serverLastFileState.selectedFolder || serverLastFolderState || {}, preferredOwner);
        if (serverFolder && serverFolder.path) {
          return {
            tree: serverFolder.path,
            task_owner: clean(serverFolder.task_owner || preferredOwner || ""),
            source: "server_folder",
          };
        }
        const storedPath = normalizeServerPathValue(getStoredServerPath() || "");
        return {
          tree: storedPath || "",
          task_owner: lessonVaultTaskOwnerForPath(storedPath || "", preferredOwner),
          source: storedPath ? "stored_path" : "root",
        };
      };

      // Added 2026-07-21: ignore volatile access timestamps so repeated navigation cannot create a last-file request storm.
      const serverLastFileSemanticSignature = (state = {}) => {
        const source = state && typeof state === "object" ? state : {};
        const file = normalizeServerRecentRow(source.file || null);
        const selectedFolder = normalizeLessonVaultFolderState(source.selectedFolder || source.selected_folder || source.folder || {}, clean(serverTaskOwnerContext || currentAuthUsername || ""));
        const recentFiles = Array.isArray(source.recentFiles) ? source.recentFiles : [];
        try {
          return JSON.stringify({
            file: file ? {
              path: normalizeServerPathValue(file.path || ""),
              lessonId: clean(file.lesson_id || file.file_id || ""),
              sourcePath: normalizeServerPathValue(file.sourcePath || ""),
              effectivePath: normalizeServerPathValue(file.effectivePath || ""),
              linkTarget: normalizeServerPathValue(file.linkTarget || ""),
              taskOwner: clean(file.task_owner || file.taskOwner || "").toLowerCase(),
              parentPath: normalizeServerPathValue(file.parentPath || ""),
              page: Math.max(0, Number(file.page || 0) || 0),
              pages: Math.max(0, Number(file.pages || 0) || 0),
            } : null,
            recentPaths: recentFiles.map((row) => normalizeServerPathValue(row && row.path || "")).filter(Boolean).slice(0, 20),
            selectedFolder: selectedFolder ? {
              path: normalizeServerPathValue(selectedFolder.path || ""),
              taskOwner: clean(selectedFolder.task_owner || selectedFolder.taskOwner || "").toLowerCase(),
            } : null,
          });
        } catch (error) {
          return "";
        }
      };

      // Added 2026-07-08: persists Lesson Vault's selected display/link path to the server, not only localStorage.
      const postServerLastFileState = async () => {
        const recentFiles = readStoredServerRecentFiles();
        const file = recentFiles.find(serverRecentRowIsResumeable) || recentFiles[0] || normalizeServerRecentRow(serverLastFileState.file || getStoredServerFile());
        const selectedFolder = normalizeLessonVaultFolderState(serverLastFolderState || {}, clean(serverTaskOwnerContext || currentAuthUsername || ""));
        const state = applyServerLastFileState({ file, recentFiles, selectedFolder }, { render: true });
        const signature = serverLastFileSemanticSignature(state);
        const now = Date.now();
        if (signature && signature === serverLastFileLastSemanticSignature && now - serverLastFileLastSemanticAt < 30000) {
          return state;
        }
        if (serverLastFilePostPromise) {
          serverLastFilePostQueued = true;
          return serverLastFilePostPromise;
        }
        if (authToken && (state.file || selectedFolder)) {
          serverLastFilePostPromise = (async () => {
            const result = await fetchAuthJson("/server-data/last-file?client_source=server_last_file_sync", {
              method: "POST",
              body: JSON.stringify({ file: state.file, recentFiles: state.recentFiles, selectedFolder }),
            });
            const payload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
            serverLastFileEtag = "";
            serverLastFileHasServerPayload = false;
            if (payload.state) {
              return applyServerLastFileState(payload.state, { render: true });
            }
            return state;
          })();
          try {
            const saved = await serverLastFilePostPromise;
            serverLastFileLastSemanticSignature = signature;
            serverLastFileLastSemanticAt = Date.now();
            serverLastFileRetryAfter = 0;
            return saved;
          } catch (error) {
            serverLastFileRetryAfter = Date.now() + 5000;
          } finally {
            serverLastFilePostPromise = null;
            if (serverLastFilePostQueued) {
              serverLastFilePostQueued = false;
              queueServerLastFileSync(350);
            }
          }
        }
        return state;
      };

      const queueServerLastFileSync = (delayMs = 900) => {
        if (serverLastFileSyncTimer) {
          window.clearTimeout(serverLastFileSyncTimer);
        }
        const retryDelay = Math.max(0, serverLastFileRetryAfter - Date.now());
        serverLastFileSyncTimer = window.setTimeout(() => {
          serverLastFileSyncTimer = 0;
          void postServerLastFileState();
        }, Math.max(80, Number(delayMs) || 900, retryDelay));
      };

      const getStoredServerPath = () => {
        const serverFile = normalizeServerRecentRow(serverLastFileState && serverLastFileState.file || null);
        if (serverFile && serverFile.parentPath) {
          return serverFile.parentPath;
        }
        try {
          return normalizeServerPathValue(readServerStorageValue(SERVER_LAST_PATH_KEY) || "");
        } catch (error) {
          return "";
        }
      };

      const getStoredServerFile = () => {
        const serverFile = normalizeServerRecentRow(serverLastFileState && serverLastFileState.file || null);
        if (serverFile && serverFile.path) {
          return serverFile.path;
        }
        try {
          return normalizeServerPathValue(readServerStorageValue(SERVER_LAST_FILE_KEY) || "");
        } catch (error) {
          return "";
        }
      };

      const readStoredServerRecentFiles = () => {
        let rows = [];
        try {
          const merged = [];
          const seenStorage = new Set();
          for (const key of serverStorageKeyCandidates(SERVER_RECENT_FILES_KEY)) {
            const raw = localStorage.getItem(key) || "";
            if (!raw || seenStorage.has(key)) {
              continue;
            }
            seenStorage.add(key);
            const parsed = raw ? JSON.parse(raw) : [];
            if (Array.isArray(parsed)) {
              merged.push(...parsed);
            }
          }
          rows = merged;
        } catch (error) {
          rows = [];
        }
        const seen = new Set();
        const normalizedRows = [];
        const addRow = (item) => {
          const row = normalizeServerRecentRow(item);
          const path = row && row.path || "";
          const key = path.toLowerCase();
          if (!path || seen.has(key)) {
            return;
          }
          seen.add(key);
          normalizedRows.push(row);
        };
        if (serverLastFileState && Array.isArray(serverLastFileState.recentFiles)) {
          serverLastFileState.recentFiles.forEach(addRow);
        }
        rows.forEach(addRow);
        const lastFile = getStoredServerFile();
        const lastKey = lastFile.toLowerCase();
        if (lastFile && !seen.has(lastKey)) {
          const row = normalizeServerRecentRow(serverLastFileState && serverLastFileState.file || { path: lastFile, accessedAt: "" });
          if (row) normalizedRows.unshift(row);
        }
        return normalizedRows.slice(0, 20);
      };

      const writeStoredServerRecentFiles = (items = []) => {
        try {
          localStorage.setItem(serverStorageKey(SERVER_RECENT_FILES_KEY), JSON.stringify((Array.isArray(items) ? items : []).slice(0, 20)));
        } catch (error) {
        }
      };

      const serverParentPathForFile = (pathValue) => {
        const raw = normalizeServerPathValue(pathValue);
        const slash = raw.lastIndexOf("/");
        return slash > 0 ? raw.slice(0, slash) : "";
      };

      const rememberServerPath = (pathValue) => {
        try {
          localStorage.setItem(serverStorageKey(SERVER_LAST_PATH_KEY), normalizeServerPathValue(pathValue));
        } catch (error) {
        }
      };

      const rememberServerFile = (pathValue, options = {}) => {
        const source = pathValue && typeof pathValue === "object" ? pathValue : { path: pathValue };
        const fileRow = normalizeServerRecentRow({
          ...source,
          accessedAt: new Date().toISOString(),
        });
        const filePath = fileRow ? fileRow.path : "";
        if (!serverPathIsImmediateMission(filePath)) {
          try {
            localStorage.setItem(serverStorageKey(SERVER_LAST_FILE_KEY), filePath);
            localStorage.setItem(serverStorageKey(SERVER_LAST_PATH_KEY), fileRow ? fileRow.parentPath || serverParentPathForFile(filePath) : serverParentPathForFile(filePath));
          } catch (error) {
          }
        }
        if (filePath) {
          const key = filePath.toLowerCase();
          const nextRows = readStoredServerRecentFiles().filter((item) => normalizeServerPathValue(item.path || "").toLowerCase() !== key);
          nextRows.unshift(fileRow);
          writeStoredServerRecentFiles(nextRows);
          applyServerLastFileState({ file: nextRows[0], recentFiles: nextRows }, { render: true });
          if (options && options.syncNow) {
            queueServerLastFileSync(80);
          }
        }
        try {
          if (typeof renderServerRecentFileShortcut === "function" && renderServerRecentFileShortcut()) {
            if (serverNavNode) serverNavNode.hidden = false;
          }
        } catch (error) {
        }
      };

      const rememberLessonVaultFolder = (pathValue, taskOwner = "", source = "") => {
        const normalizedPath = normalizeServerPathValue(pathValue);
        const normalizedOwner = clean(taskOwner || serverTaskOwnerContext || currentAuthUsername || "");
        const existingFolder = [
          normalizeLessonVaultFolderState(serverLastFolderState || {}, normalizedOwner),
          getStoredLessonVaultFolderState(normalizedOwner),
        ].find((row) => row
          && normalizeServerPathValue(row.path || "") === normalizedPath
          && clean(row.task_owner || row.taskOwner || "").toLowerCase() === normalizedOwner.toLowerCase());
        if (existingFolder) {
          return existingFolder;
        }
        const record = rememberLessonVaultFolderState({
          path: normalizedPath,
          task_owner: normalizedOwner,
          selected_at: new Date().toISOString(),
          source: clean(source || ""),
        }, { task_owner: taskOwner });
        if (record) {
          serverLastFileState = {
            ...(serverLastFileState || {}),
            selectedFolder: record,
          };
          // 2026-07-21: folder focus is instant locally; persist only the final path after rapid Space Task navigation settles.
          queueServerLastFileSync(900);
        }
        return record;
      };

      const formatServerFileSize = (size) => {
        const bytes = Number(size || 0);
        if (!Number.isFinite(bytes) || bytes <= 0) {
          return "";
        }
        if (bytes < 1024) {
          return `${bytes} B`;
        }
        if (bytes < 1024 * 1024) {
          return `${Math.round(bytes / 1024)} KB`;
        }
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
      };

      const lessonTitleFromPayload = (payload = {}) => clean(payload.title || payload.t || "Future lesson");

      const futureDisplayNameWithoutId = (value = "") => {
        const raw = clean(value || "");
        if (!raw) {
          return "";
        }
        const normalized = raw.replace(/\\/g, "/").split("/").filter(Boolean).pop() || raw;
        const dotIndex = normalized.lastIndexOf(".");
        const hasExtension = dotIndex > 0 && dotIndex < normalized.length - 1;
        const stem = hasExtension ? normalized.slice(0, dotIndex) : normalized;
        const suffix = hasExtension ? normalized.slice(dotIndex) : "";
        const stripped = stem
          .replace(/\s*\[[a-z0-9_ -]*id[:_ -]*[0-9a-f]{8,}\]$/i, "")
          .replace(/[_-]+$/g, "")
          .trim();
        return (stripped || stem || normalized) + suffix;
      };

      const futureFriendlyDisplayName = (value = "", options = {}) => {
        const cleaned = futureDisplayNameWithoutId(value);
        if (!cleaned) {
          return "";
        }
        const keepExtension = Boolean(options.keepExtension);
        const dotIndex = cleaned.lastIndexOf(".");
        const base = !keepExtension && dotIndex > 0 ? cleaned.slice(0, dotIndex) : cleaned;
        return base.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim() || cleaned;
      };

      const lessonDisplayName = (entry = {}) => {
        const study = entry.study && typeof entry.study === "object" ? entry.study : {};
        const candidates = [
          entry.display_name,
          entry.displayName,
          study.display_name,
          study.displayName,
          entry.name,
          entry.path,
          study.title,
        ];
        for (const candidate of candidates) {
          const title = futureFriendlyDisplayName(clean(candidate || ""));
          if (!title) {
            continue;
          }
          const words = title.split(/\s+/).filter(Boolean);
          if (title.length <= 72 && words.length <= 10) {
            return title;
          }
        }
        return futureFriendlyDisplayName(clean(entry.display_name || entry.displayName || entry.name || entry.path || study.title || "Lesson")) || "Lesson";
      };

      const serverFolderDisplayName = (entry = {}) => {
        const explicit = clean(entry.display_name || entry.displayName || "");
        if (explicit) {
          return futureFriendlyDisplayName(explicit);
        }
        return futureFriendlyDisplayName(clean(entry.name || entry.path || "folder"), { keepExtension: true }) || "folder";
      };

      const shortStudyDate = (value) => {
        const raw = clean(value);
        if (!raw) {
          return "";
        }
        const date = new Date(raw);
        if (!Number.isFinite(date.getTime())) {
          return raw.slice(0, 16);
        }
        return date.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
      };

      const formatLessonTimes = (value) => {
        const count = Number(value || 0) || 0;
        return count === 1 ? "1 Time" : `${count} Times`;
      };

      // Added 2026-07-15: preserves completed-run history while a new active study run is in progress.
      const lessonStudyCompletedRunCount = (study = {}, options = {}) => {
        const source = study && typeof study === "object" ? study : {};
        const progress = source.progress && typeof source.progress === "object" ? source.progress : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const lessonStudy = lessonSource.study && typeof lessonSource.study === "object" ? lessonSource.study : {};
        const lessonProgress = lessonStudy.progress && typeof lessonStudy.progress === "object" ? lessonStudy.progress : {};
        const includeAdmin = Boolean(options && options.includeAdmin);
        const mine = Math.max(
          0,
          Math.floor(Number(source.mine || 0) || 0),
          Math.floor(Number(source.completedRuns ?? source.completed_runs ?? 0) || 0),
          Math.floor(Number(progress.completedRuns ?? progress.completed_runs ?? 0) || 0),
          Math.floor(Number(state.completedRuns ?? state.completed_runs ?? 0) || 0),
          Math.floor(Number(lessonStudy.mine || 0) || 0),
          Math.floor(Number(lessonStudy.completedRuns ?? lessonStudy.completed_runs ?? 0) || 0),
          Math.floor(Number(lessonProgress.completedRuns ?? lessonProgress.completed_runs ?? 0) || 0),
          includeAdmin ? Math.floor(Number(source.admin_mine || 0) || 0) : 0,
        );
        const total = Math.max(0, Math.floor(Number(source.total || 0) || 0));
        return total > 0 && mine > total ? total : mine;
      };

      // Added 2026-07-15: labels the current run separately from prior learned history.
      const lessonCurrentRunProgressLabel = (study = {}, progress = null) => {
        const source = study && typeof study === "object" ? study : {};
        const current = progress && typeof progress === "object"
          ? progress
          : (source.progress && typeof source.progress === "object" ? source.progress : {});
        // Added 2026-07-15: the Lesson Vault "Node" chip follows chart progress, not the resume pointer.
        const progressTotal = Math.max(0, Math.floor(Number(current.total ?? current.nodeCount ?? current.node_total ?? current.nodeTotal ?? 0) || 0));
        const progressDone = Math.max(0, Math.min(progressTotal || Infinity, Math.floor(Number(current.done ?? 0) || 0)));
        const text = clean(current.text || (progressTotal ? `${progressDone}/${progressTotal}` : ""));
        const priorRuns = typeof lessonStudyCompletedRunCount === "function" ? lessonStudyCompletedRunCount(source) : 0;
        const progressSpace = clean(current.space || source.space || "").toLowerCase();
        const workloadLabel = progressSpace === "space_q" ? "Question" : "Node";
        const nodeLabel = text ? `${workloadLabel} ${text}` : "";
        if (current.reviewing || current.reviewRun) {
          return nodeLabel || (text ? `Review ${text}` : "Review");
        }
        if (priorRuns > 0 || current.relearning || current.relearnRun || current.previously_completed || current.previouslyCompleted) {
          return nodeLabel || (text ? `Relearn ${text}` : "Relearn");
        }
        return nodeLabel || (text ? `${workloadLabel} ${text}` : workloadLabel);
      };

      // Added 2026-07-15: shows the active lesson node as its own Lesson Vault chip.
      const lessonCurrentRunNodeChipLabel = (progress = null) => {
        const current = progress && typeof progress === "object" ? progress : {};
        // Added 2026-07-15: keep the node chip aligned with the visible progress ring.
        const total = Math.max(0, Math.floor(Number(current.total ?? current.nodeCount ?? current.node_total ?? current.nodeTotal ?? 0) || 0));
        if (!total) {
          return "";
        }
        const text = clean(current.text || "");
        const workloadLabel = clean(current.space || "").toLowerCase() === "space_q" ? "Question" : "Node";
        if (text) {
          return `${workloadLabel} ${text}`;
        }
        const done = Math.max(0, Math.min(total, Math.floor(Number(current.done ?? 0) || 0)));
        return `${workloadLabel} ${done}/${total}`;
      };

      // Added 2026-08-03: normalize mixed legacy Space_Q metadata without adding root nodes twice.
      const spaceQStructuralProgressTotal = (study = {}, entry = {}) => {
        const sourceStudy = study && typeof study === "object" ? study : {};
        const sourceEntry = entry && typeof entry === "object" ? entry : {};
        const nodes = Math.max(0, Math.floor(Number(sourceStudy.nodes || sourceEntry.nodes || sourceEntry.node_count || 0) || 0));
        const directQuestions = Math.max(0, Math.floor(Number(sourceStudy.direct_questions || sourceStudy.directQuestions || sourceEntry.direct_questions || 0) || 0));
        const questions = Math.max(0, Math.floor(Number(sourceStudy.questions || sourceEntry.questions || 0) || 0));
        const explicitTotal = Math.max(0, Math.floor(Number(sourceStudy.total_nodes || sourceStudy.totalNodes || sourceEntry.total_nodes || 0) || 0));
        if (explicitTotal) {
          return explicitTotal;
        }
        return directQuestions ? Math.max(nodes + directQuestions, questions) : nodes + questions;
      };

      const createServerChip = (text, kind = "") => {
        const chip = document.createElement("span");
        const kindClasses = clean(kind).split(/\s+/).filter(Boolean).map((item) => `is-${item}`);
        chip.className = ["ft-server-chip", ...kindClasses].join(" ");
        chip.textContent = text;
        return chip;
      };

      const formatCompactNumber = (value) => {
        const number = Math.max(0, Math.floor(Number(value || 0) || 0));
        if (number >= 1000000) {
          return `${(number / 1000000).toFixed(number >= 10000000 ? 0 : 1)}M`;
        }
        if (number >= 1000) {
          return `${(number / 1000).toFixed(number >= 10000 ? 0 : 1)}K`;
        }
        return String(number);
      };

      const formatServerCountLabel = (value, singular, plural = "") => {
        const count = Math.max(0, Math.floor(Number(value || 0) || 0));
        const unit = count === 1 ? singular : (plural || `${singular}s`);
        return `${formatCompactNumber(count)} ${unit}`;
      };

      const learningSummaryDragNodes = new WeakSet();

      const installLearningSummaryDrag = (node) => {
        if (!node || learningSummaryDragNodes.has(node)) {
          return;
        }
        learningSummaryDragNodes.add(node);
        let dragging = false;
        let startX = 0;
        let startLeft = 0;
        let returnFrame = 0;
        const cancelReturnMotion = () => {
          if (returnFrame) {
            window.cancelAnimationFrame(returnFrame);
            returnFrame = 0;
          }
        };
        const stopDragging = () => {
          if (!dragging) {
            return;
          }
          dragging = false;
          node.classList.remove("is-dragging");
        };
        const returnToStart = () => {
          stopDragging();
          cancelReturnMotion();
          const start = Math.max(0, Number(node.scrollLeft || 0));
          if (start <= 0.5) {
            node.scrollLeft = 0;
            return;
          }
          const duration = Math.min(560, Math.max(260, start * 2.4));
          const startedAt = performance.now();
          const easeOut = (value) => 1 - Math.pow(1 - value, 3);
          const step = (now) => {
            const progress = Math.min(1, Math.max(0, (now - startedAt) / duration));
            node.scrollLeft = start * (1 - easeOut(progress));
            if (progress < 1) {
              returnFrame = window.requestAnimationFrame(step);
              return;
            }
            node.scrollLeft = 0;
            returnFrame = 0;
          };
          returnFrame = window.requestAnimationFrame(step);
        };
        node.addEventListener("pointerdown", (event) => {
          if (event.button && event.button !== 0) {
            return;
          }
          if (node.scrollWidth <= node.clientWidth + 2) {
            return;
          }
          cancelReturnMotion();
          dragging = true;
          startX = event.clientX;
          startLeft = node.scrollLeft;
          node.classList.add("is-dragging");
          if (typeof node.setPointerCapture === "function") {
            try {
              node.setPointerCapture(event.pointerId);
            } catch (error) {
              // Pointer capture is optional; drag-scroll still works without it.
            }
          }
        });
        node.addEventListener("pointermove", (event) => {
          if (!dragging) {
            return;
          }
          node.scrollLeft = startLeft - ((event.clientX - startX) * 1.18);
          event.preventDefault();
        });
        node.addEventListener("pointerup", (event) => {
          stopDragging();
          if (typeof node.releasePointerCapture === "function") {
            try {
              node.releasePointerCapture(event.pointerId);
            } catch (error) {
            }
          }
        });
        node.addEventListener("pointercancel", returnToStart);
        node.addEventListener("mouseleave", returnToStart);
        node.addEventListener("pointerleave", returnToStart);
      };

      const renderLearningSummary = (node, stats = {}) => {
        if (!node) {
          return;
        }
        const source = stats && typeof stats === "object" ? stats : {};
        const username = clean(source.username || "");
        if (!username) {
          node.hidden = true;
          node.textContent = "";
          delete node.dataset.learningSummarySignature;
          clearLearningStatsMotionCycle();
          return;
        }
        const rows = [
          { key: "vocab", label: "Vocabulary", value: source.vocabulary_words, detail: "words learned" },
          { key: "space-v", label: "Space V", value: source.space_v_files, detail: "vocab files" },
          { key: "space-w", label: "Space W", value: source.space_w_files, detail: "lesson files" },
          { key: "space-q", label: "Space Q", value: source.space_q_files, detail: "question files" },
          { key: "space-p", label: "Space P/S", value: source.space_p_files, detail: "paragraph/speaking files" },
        ];
        const summarySignature = hashSpaceWText(JSON.stringify({
          username,
          rows: rows.map((item) => ({
            key: item.key,
            value: Math.max(0, Math.floor(Number(item.value || 0) || 0)),
          })),
        }));
        if (node.childElementCount && node.dataset.learningSummarySignature === summarySignature) {
          node.hidden = false;
          if (!learningStatsMotionTimer && learningStatsMotionReady()) {
            scheduleLearningStatsMotionCycle();
          }
          return;
        }
        node.dataset.learningSummarySignature = summarySignature;
        node.textContent = "";
        rows.forEach((item) => {
          const card = document.createElement("div");
          card.className = `ft-learning-stat is-${item.key}`;
          const value = document.createElement("b");
          value.textContent = formatCompactNumber(item.value);
          value.title = String(Math.max(0, Math.floor(Number(item.value || 0) || 0)));
          const label = document.createElement("span");
          label.textContent = item.label;
          const detail = document.createElement("small");
          detail.textContent = item.detail;
          card.append(value, label, detail);
          node.appendChild(card);
        });
        node.hidden = false;
        installLearningSummaryDrag(node);
        node.scrollTo({ left: 0, behavior: "auto" });
        scheduleLearningStatsMotionCycle(1000);
      };

      const lessonVaultMotionOff = () => document.documentElement.classList.contains("ft-lesson-vault-motion-off")
        || document.documentElement.classList.contains("ft-ghost-ai-focus");

      const learningStatMotionCards = () => {
        if (!taskLearningSummaryNode || taskLearningSummaryNode.hidden) {
          return [];
        }
        return Array.from(taskLearningSummaryNode.querySelectorAll(".ft-learning-stat"));
      };

      const taskBoardPeriodicMotionCards = () => {
        if (!serverTaskListNode) {
          return [];
        }
        const listRect = serverTaskListNode.getBoundingClientRect();
        if (!listRect.width || !listRect.height) {
          return [];
        }
        return Array.from(serverTaskListNode.querySelectorAll(".ft-task-card:not(.is-complete)"))
          .filter((card) => {
            const rect = card.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && rect.bottom >= listRect.top - 80 && rect.top <= listRect.bottom + 80;
          })
          .slice(0, TASK_BOARD_PERIODIC_MOTION_LIMIT);
      };

      const learningStatsMotionReady = () => Boolean(
        lessonVaultMotionOff() &&
        serverBrowser &&
        !serverBrowser.hidden &&
        (learningStatMotionCards().length || taskBoardPeriodicMotionCards().length),
      );

      const clearLearningStatsMotionCycle = () => {
        if (learningStatsMotionTimer) {
          window.clearTimeout(learningStatsMotionTimer);
          learningStatsMotionTimer = 0;
        }
      };

      const pulseLearningStatsOnce = () => {
        if (!learningStatsMotionReady()) {
          clearLearningStatsMotionCycle();
          return false;
        }
        const cards = learningStatMotionCards();
        cards.forEach((card, index) => {
          window.clearTimeout(card._futureStatBurstTimer || 0);
          card.classList.remove("is-stat-burst");
          void card.offsetWidth;
          const delayMs = index * 80;
          window.setTimeout(() => {
            card.classList.add("is-stat-burst");
          }, delayMs);
          card._futureStatBurstTimer = window.setTimeout(() => {
            card.classList.remove("is-stat-burst");
            card._futureStatBurstTimer = 0;
          }, LEARNING_STATS_MOTION_BURST_MS + delayMs + 80);
        });
        taskBoardPeriodicMotionCards().forEach((card, index) => {
          window.setTimeout(() => {
            triggerServerWorkspaceMotionBurst(card, null, { source: "periodic" });
          }, index * 120);
        });
        return true;
      };

      const scheduleLearningStatsMotionCycle = (delayMs = LEARNING_STATS_MOTION_INTERVAL_MS) => {
        clearLearningStatsMotionCycle();
        if (!learningStatsMotionReady()) {
          return;
        }
        learningStatsMotionTimer = window.setTimeout(() => {
          learningStatsMotionTimer = 0;
          if (pulseLearningStatsOnce()) {
            scheduleLearningStatsMotionCycle(LEARNING_STATS_MOTION_INTERVAL_MS);
          }
        }, Math.max(1000, Number(delayMs) || LEARNING_STATS_MOTION_INTERVAL_MS));
      };

      const FUTURE_FILE_LOGO_MOTION_MS = 3600;

      const triggerFutureFileLogoMotion = (target, options = {}) => {
        const source = clean(options.source || "");
        if (source === "hover" || source === "focus" || source === "periodic") {
          return;
        }
        const root = target && target.closest
          ? (target.closest(".ft-server-item, .ft-task-card") || target)
          : target;
        if (!root || !root.querySelectorAll) {
          return;
        }
        const logos = Array.from(root.querySelectorAll(".ft-file-type-logo"));
        if (!logos.length && root.classList && root.classList.contains("ft-file-type-logo")) {
          logos.push(root);
        }
        logos.forEach((logo) => {
          window.clearTimeout(logo._futureFileLogoMotionTimer || 0);
          logo.classList.remove("is-logo-burst");
          void logo.offsetWidth;
          logo.classList.add("is-logo-burst");
          logo._futureFileLogoMotionTimer = window.setTimeout(() => {
            logo.classList.remove("is-logo-burst");
            logo._futureFileLogoMotionTimer = 0;
          }, FUTURE_FILE_LOGO_MOTION_MS + 120);
        });
      };

      const triggerServerWorkspaceMotionBurst = (target, relatedTarget = null, options = {}) => {
        if (!lessonVaultMotionOff()) {
          triggerFutureFileLogoMotion(target, options);
          return;
        }
        const card = target && target.closest
          ? target.closest(".ft-server-item, .ft-task-card")
          : null;
        if (!card || !serverBrowser || !serverBrowser.contains(card)) {
          return;
        }
        const source = clean(options.source || "");
        if (source === "hover" && card.classList.contains("ft-server-item")) {
          return;
        }
        if (relatedTarget && card.contains(relatedTarget)) {
          return;
        }
        triggerFutureFileLogoMotion(card, options);
        window.clearTimeout(card._futureMotionBurstTimer || 0);
        card.classList.remove("is-motion-burst");
        void card.offsetWidth;
        card.classList.add("is-motion-burst");
        card._futureMotionBurstTimer = window.setTimeout(() => {
          card.classList.remove("is-motion-burst");
          card._futureMotionBurstTimer = 0;
        }, SERVER_WORKSPACE_MOTION_BURST_MS + 60);
      };

      function startAnimationEngineBootSequence() {
        if (animationEngineBootTimer) {
          window.clearTimeout(animationEngineBootTimer);
          animationEngineBootTimer = 0;
        }
        document.documentElement.classList.add("ft-animation-engine-booting");
        if (mobileAnimationButton) {
          mobileAnimationButton.classList.add("is-booting");
        }
        animationEngineBootTimer = window.setTimeout(() => {
          document.documentElement.classList.remove("ft-animation-engine-booting");
          if (mobileAnimationButton) {
            mobileAnimationButton.classList.remove("is-booting");
          }
          animationEngineBootTimer = 0;
        }, 1750);
      }

      const formatStudyDuration = (seconds) => {
        const totalSeconds = Math.max(0, Math.floor(Number(seconds || 0) || 0));
        if (!totalSeconds) {
          return "";
        }
        const minutes = Math.floor(totalSeconds / 60);
        if (minutes < 1) {
          return `${totalSeconds}s`;
        }
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        if (hours > 0) {
          return rest ? `${hours}h ${rest}m` : `${hours}h`;
        }
        return `${minutes}m`;
      };

      const normalizedLessonProgress = (study = {}) => {
        const progress = study && study.progress && typeof study.progress === "object" ? study.progress : null;
        if (!progress) {
          return null;
        }
        const reviewing = Boolean(progress.reviewing || progress.reviewRun);
        const activeRun = Boolean(progress.activeRun || progress.active_run);
        const completed = Boolean(!activeRun && (progress.completed || progress.complete || progress.lessonComplete || progress.vocabComplete));
        const rawDone = reviewing ? (progress.review_done ?? progress.reviewDone ?? progress.done) : progress.done;
        const rawTotal = reviewing ? (progress.review_total ?? progress.reviewTotal ?? progress.total) : progress.total;
        const done = Math.max(0, Math.floor(Number(rawDone || 0) || 0));
        const total = Math.max(0, Math.floor(Number(rawTotal || 0) || 0));
        if (!total) {
          return null;
        }
        // Added 2026-07-15: review runs keep their current done/total even when the file has prior completions.
        const isCompleteDisplay = reviewing
          ? done >= total
          : (!activeRun && (completed || done >= total || Number(progress.percent || 0) >= 100));
        const canShowPartial = reviewing || (
          done < total &&
          (
            (done > 0 && progress.in_progress !== false) ||
            activeRun ||
            Boolean(progress.in_progress && (progress.previously_completed || progress.previouslyCompleted))
          )
        );
        if (!isCompleteDisplay && !canShowPartial) {
          return null;
        }
        const rawPercent = reviewing
          ? (progress.review_percent ?? progress.reviewPercent ?? progress.percent)
          : (activeRun ? null : progress.percent);
        const percent = reviewing
          ? Math.max(0, Math.min(99, Math.round(Number(rawPercent ?? ((done / total) * 100)) || 0)))
          : (isCompleteDisplay ? 100 : Math.max(activeRun && done === 0 ? 0 : 1, Math.min(99, Math.round(Number(rawPercent ?? ((done / total) * 100)) || 0))));
        const nodeDone = Math.max(0, Math.floor(Number(progress.node_done || progress.nodeDone || 0) || 0));
        const nodeTotal = Math.max(0, Math.floor(Number(progress.node_total || progress.nodeTotal || 0) || 0));
        const valueText = clean((reviewing ? (progress.review_text || progress.reviewText) : progress.text) || `${done}/${total}`);
        const relearning = Boolean(progress.relearning || progress.relearnRun || progress.previously_completed || progress.previouslyCompleted);
        const completedRuns = Math.max(
          0,
          Math.floor(Number(study.mine || 0) || 0),
          Math.floor(Number(study.completedRuns ?? study.completed_runs ?? 0) || 0),
          Math.floor(Number(study.completionCount ?? study.completion_count ?? 0) || 0),
          Math.floor(Number(progress.completedRuns ?? progress.completed_runs ?? 0) || 0),
          Math.floor(Number(progress.completionCount ?? progress.completion_count ?? 0) || 0),
        );
        const progressSpace = clean(progress.space || study.space || "");
        const isRepeatCompletion = typeof resolveLessonProgressRepeatState === "function"
          ? resolveLessonProgressRepeatState({ completedRuns, isCompleteDisplay, activeRun, relearning, reviewing, canShowPartial })
          : Boolean(completedRuns > 1 || (completedRuns > 0 && !isCompleteDisplay && (activeRun || relearning || reviewing || canShowPartial)));
        return {
          space: progressSpace,
          label: reviewing ? "Review" : (relearning ? clean(progress.relearnLabel || "Relearn") : clean(progress.label || "Progress")),
          done,
          total,
          percent,
          nodeDone,
          nodeTotal,
          valueText,
          completed: Boolean(isCompleteDisplay && !reviewing),
          reviewing,
          activeRun: Boolean(activeRun && !isCompleteDisplay),
          relearning,
          completedRuns,
          isRepeatCompletion,
          repeatRun: isRepeatCompletion,
          syncing: Boolean(progress.syncing || progress.pending_sync),
        };
      };

      const lessonProgressOverrideKey = (path = "") => normalizeTaskPath(normalizeServerPathValue(path || ""));
      const lessonVaultProgressSnapshot = new Map();
      let lessonVaultProgressSnapshotGeneration = 0;

      // Added 2026-07-29: prevents one signed-in user/run snapshot surviving logout or an account switch.
      const resetLessonVaultProgressRuntimeCache = () => {
        lessonVaultProgressSnapshot.clear();
        lessonProgressOverrides.clear();
        lessonVaultProgressSnapshotGeneration += 1;
      };
      if (typeof window !== "undefined") {
        window.__ftResetLessonVaultProgressRuntimeCache = resetLessonVaultProgressRuntimeCache;
      }

      const parseLessonProgressTimestamp = (value) => {
        if (typeof value === "number" && Number.isFinite(value)) {
          return value > 100000000000 ? value : value * 1000;
        }
        const text = clean(value || "");
        if (!text) {
          return 0;
        }
        const numeric = Number(text);
        if (Number.isFinite(numeric) && numeric > 0) {
          return numeric > 100000000000 ? numeric : numeric * 1000;
        }
        const parsed = Date.parse(text);
        return Number.isFinite(parsed) ? parsed : 0;
      };

      const lessonProgressSnapshotTimestamp = (row = {}) => {
        const source = row && typeof row === "object" ? row : {};
        const study = source.study && typeof source.study === "object" ? source.study : {};
        const progress = source.progress && typeof source.progress === "object"
          ? source.progress
          : (study.progress && typeof study.progress === "object" ? study.progress : {});
        return Math.max(
          parseLessonProgressTimestamp(source.updatedAt || source.updated_at || ""),
          parseLessonProgressTimestamp(source.savedAt || source.saved_at || ""),
          parseLessonProgressTimestamp(study.updatedAt || study.updated_at || ""),
          parseLessonProgressTimestamp(study.savedAt || study.saved_at || ""),
          parseLessonProgressTimestamp(progress.updatedAt || progress.updated_at || ""),
          parseLessonProgressTimestamp(progress.savedAt || progress.saved_at || ""),
        );
      };

      // Added 2026-07-31: equal timestamps use the durable server revision as their ordering tie-break.
      const lessonProgressSnapshotRevision = (row = {}) => {
        const source = row && typeof row === "object" ? row : {};
        const study = source.study && typeof source.study === "object" ? source.study : {};
        const progress = source.progress && typeof source.progress === "object"
          ? source.progress
          : (study.progress && typeof study.progress === "object" ? study.progress : {});
        return Math.max(
          0,
          Number(source.server_revision || source.serverRevision || source._serverRevision || 0) || 0,
          Number(study.server_revision || study.serverRevision || 0) || 0,
          Number(progress.server_revision || progress.serverRevision || 0) || 0,
        );
      };

      const compareLessonProgressSnapshotOrder = (left = {}, right = {}) => {
        const timestampDelta = lessonProgressSnapshotTimestamp(left) - lessonProgressSnapshotTimestamp(right);
        if (timestampDelta) {
          return timestampDelta;
        }
        return lessonProgressSnapshotRevision(left) - lessonProgressSnapshotRevision(right);
      };

      const normalizeLessonVaultProgressSnapshotItem = (item = {}, fallbackPath = "") => {
        const source = item && typeof item === "object" ? item : {};
        const pathValue = normalizeServerPathValue(source.path || fallbackPath || "");
        const study = source.study && typeof source.study === "object" ? { ...source.study } : {};
        const progress = source.progress && typeof source.progress === "object"
          ? { ...source.progress }
          : (study.progress && typeof study.progress === "object" ? { ...study.progress } : null);
        if (progress) {
          study.progress = progress;
          study.progress_text = clean(study.progress_text || progress.text || "");
          study.progress_percent = Number(study.progress_percent ?? progress.percent ?? 0) || 0;
        }
        return {
          ...source,
          path: pathValue,
          study,
          progress: progress || null,
          updatedAt: clean(source.updatedAt || source.updated_at || study.updatedAt || ""),
          savedAt: clean(source.savedAt || source.saved_at || study.savedAt || ""),
        };
      };

      // Added 2026-07-31: progress identities are namespaced by Space so legacy ID collisions cannot cross-apply.
      const lessonVaultProgressSnapshotSpace = (row = {}) => {
        const source = row && typeof row === "object" ? row : {};
        const study = source.study && typeof source.study === "object" ? source.study : {};
        const progress = source.progress && typeof source.progress === "object"
          ? source.progress
          : (study.progress && typeof study.progress === "object" ? study.progress : {});
        const raw = clean(progress.space || study.space || source.space || "").toLowerCase();
        const suffix = raw.replace(/^space[_-]?/, "");
        return suffix ? `Space_${suffix.toUpperCase()}` : "";
      };

      const lessonVaultEntryProgressSpace = (entry = {}) => {
        const routeSpace = typeof futureRouteSpaceForFilePath === "function"
          ? clean(futureRouteSpaceForFilePath(entry.path || entry.effective_path || entry.link_target || ""))
          : "";
        const raw = clean(routeSpace || entry.extension || "").toLowerCase().replace(/^\./, "");
        const suffix = raw.replace(/^space[_-]?/, "");
        return suffix ? `Space_${suffix.toUpperCase()}` : "";
      };

      // Added 2026-07-15: stores the login progress snapshot so Lesson Vault/Space Task can render progress without per-file GETs.
      const rememberLessonVaultProgressSnapshot = (snapshot = {}) => {
        const items = snapshot && typeof snapshot === "object" ? snapshot.items : null;
        if (!items || typeof items !== "object") {
          return 0;
        }
        let changed = 0;
        Object.entries(items).forEach(([rawKey, rawItem]) => {
          const item = normalizeLessonVaultProgressSnapshotItem(rawItem, rawKey);
          const itemSpace = lessonVaultProgressSnapshotSpace(item);
          const idValues = [item.lesson_id, item.lessonId, item.file_id, item.fileId]
            .map((value) => clean(value).toLowerCase())
            .filter(Boolean);
          const keys = [
            rawKey,
            item.path,
            ...idValues.map((value) => itemSpace ? `space:${itemSpace.toLowerCase()}:id:${value}` : ""),
            ...idValues.map((value) => itemSpace ? "" : `id:${value}`),
            item.effective_path,
            item.effectivePath,
            item.link_target,
            item.linkTarget,
            item.linked_path,
            item.linkedPath,
          ].map((value) => lessonProgressOverrideKey(value)).filter(Boolean);
          const newestExisting = keys.reduce((latest, key) => {
            const existing = lessonVaultProgressSnapshot.get(key);
            return existing && (!latest || compareLessonProgressSnapshotOrder(existing, latest) > 0) ? existing : latest;
          }, null);
          // Updated 2026-07-31: reject an older canonical item before it can create a stale alias key.
          if (newestExisting && compareLessonProgressSnapshotOrder(newestExisting, item) > 0) {
            return;
          }
          keys.forEach((key) => {
            const previous = lessonVaultProgressSnapshot.get(key);
            if (previous && compareLessonProgressSnapshotOrder(previous, item) > 0) {
              return;
            }
            if (previous && compareLessonProgressSnapshotOrder(previous, item) === 0 && JSON.stringify(previous) === JSON.stringify(item)) {
              return;
            }
            lessonVaultProgressSnapshot.set(key, item);
            const activeOverride = lessonProgressOverrides.get(key);
            const incomingProgress = item.progress || (item.study && item.study.progress) || null;
            // Login/tree snapshots may carry lifetime completion history. They must not
            // delete an identified New Study run that is already newer in local RAM.
            if (!activeOverride || (incomingProgress && !shouldKeepExistingLessonProgressOverride(activeOverride, incomingProgress))) {
              lessonProgressOverrides.delete(key);
            }
            changed += 1;
          });
        });
        if (changed > 0) {
          lessonVaultProgressSnapshotGeneration += 1;
          // 2026-08-03: the tree snapshot can arrive after the cached Task Board paint.
          // Reapply it immediately so both surfaces share the same canonical checkpoint.
          if (typeof window !== "undefined" && typeof window.__ftRefreshLessonTaskPanelFromProgressSnapshot === "function") {
            window.__ftRefreshLessonTaskPanelFromProgressSnapshot();
          }
        }
        return changed;
      };

      // Added 2026-08-03: a freshly listed Lesson Vault row is authoritative for the
      // same visible Space Task card, even when the task payload still carries an older summary.
      const rememberLessonVaultProgressEntries = (entries = []) => {
        const items = {};
        (Array.isArray(entries) ? entries : []).forEach((entry, index) => {
          if (!entry || typeof entry !== "object") {
            return;
          }
          const study = entry.study && typeof entry.study === "object" ? entry.study : {};
          const progress = study.progress && typeof study.progress === "object"
            ? study.progress
            : (entry.progress && typeof entry.progress === "object" ? entry.progress : null);
          if (!progress) {
            return;
          }
          const pathValue = normalizeServerPathValue(entry.path || entry.effective_path || entry.link_target || "");
          const lessonId = clean(entry.lesson_id || entry.lessonId || entry.file_id || entry.fileId || "").toLowerCase();
          const key = pathValue || (lessonId ? `entry:${lessonId}` : `entry:${index}`);
          items[key] = {
            ...entry,
            path: pathValue,
            lesson_id: lessonId || entry.lesson_id,
            study: { ...study, progress: { ...progress } },
            progress: { ...progress },
          };
        });
        return Object.keys(items).length ? rememberLessonVaultProgressSnapshot({ items }) : 0;
      };

      const updateLessonVaultProgressSnapshotForPaths = (paths = [], progress = null) => {
        if (!progress || typeof progress !== "object") {
          return;
        }
        let changed = false;
        const updatedAt = new Date().toISOString();
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = lessonProgressOverrideKey(path);
          if (!key) {
            return;
          }
          const previous = lessonVaultProgressSnapshot.get(key) || {};
          const previousStudy = previous.study && typeof previous.study === "object" ? previous.study : {};
          const nextProgress = { ...progress, syncing: true };
          const nextStudy = {
            ...previousStudy,
            progress: nextProgress,
            progress_text: clean(nextProgress.text || previousStudy.progress_text || ""),
            progress_percent: Number(nextProgress.percent ?? previousStudy.progress_percent ?? 0) || 0,
            updatedAt,
          };
          lessonVaultProgressSnapshot.set(key, {
            ...previous,
            path: normalizeServerPathValue(path || previous.path || ""),
            study: nextStudy,
            progress: nextProgress,
            updatedAt: nextStudy.updatedAt,
          });
          changed = true;
        });
        if (changed) {
          // Task payloads carry a generation marker; advance it so Exit reapplies this local delta immediately.
          lessonVaultProgressSnapshotGeneration += 1;
        }
      };

      const lessonVaultProgressSnapshotForPaths = (paths = [], expectedSpace = "") => {
        const normalizedExpectedSpace = clean(expectedSpace);
        for (const path of (Array.isArray(paths) ? paths : [paths])) {
          const key = lessonProgressOverrideKey(path);
          if (key && lessonVaultProgressSnapshot.has(key)) {
            const candidate = lessonVaultProgressSnapshot.get(key);
            if (!normalizedExpectedSpace || lessonVaultProgressSnapshotSpace(candidate) === normalizedExpectedSpace) {
              return candidate;
            }
          }
        }
        return null;
      };

      const applyLessonVaultProgressSnapshotToEntry = (entry = {}) => {
        if (!entry || typeof entry !== "object") {
          return entry;
        }
        const entrySpace = lessonVaultEntryProgressSpace(entry);
        const entryIds = [entry.lesson_id, entry.lessonId, entry.file_id, entry.fileId]
          .map((value) => clean(value).toLowerCase())
          .filter(Boolean);
        const paths = [
          ...entryIds.map((value) => entrySpace ? `space:${entrySpace.toLowerCase()}:id:${value}` : ""),
          entry.path,
          entry.effective_path,
          entry.effectivePath,
          entry.link_target,
          entry.linkTarget,
          entry.linked_path,
          entry.linkedPath,
          entry.sourcePath,
          entry.original_path,
        ];
        const snapshot = lessonVaultProgressSnapshotForPaths(paths, entrySpace);
        const activeOverride = typeof lessonProgressOverrideForPaths === "function"
          ? lessonProgressOverrideForPaths(paths)
          : null;
        if (!snapshot && !activeOverride) {
          return entry;
        }
        const baseStudy = entry.study && typeof entry.study === "object" ? entry.study : {};
        const snapshotStudy = snapshot && snapshot.study && typeof snapshot.study === "object" ? snapshot.study : {};
        const snapshotProgress = activeOverride || (snapshot && snapshot.progress && typeof snapshot.progress === "object"
          ? snapshot.progress
          : (snapshotStudy.progress && typeof snapshotStudy.progress === "object" ? snapshotStudy.progress : null));
        const baseProgress = baseStudy.progress && typeof baseStudy.progress === "object"
          ? baseStudy.progress
          : (entry.progress && typeof entry.progress === "object" ? entry.progress : null);
        const baseOrder = {
          server_revision: entry.server_revision || entry.serverRevision || baseStudy.server_revision || baseStudy.serverRevision || 0,
          updatedAt: entry.updatedAt || entry.updated_at || "",
          savedAt: entry.savedAt || entry.saved_at || "",
          study: baseStudy,
          progress: baseProgress,
        };
        const snapshotSpace = clean(snapshotProgress && snapshotProgress.space);
        const baseSpace = clean(baseProgress && baseProgress.space);
        const canonicalMediaCorrection = ["Space_PDF", "Space_Picture"].includes(snapshotSpace) && baseSpace !== snapshotSpace;
        // 2026-08-03: a task payload can contain structural Space_Q metadata
        // (for example total_nodes=48) while its progress summary is an older
        // placeholder such as 0/16. Prefer the identified Vault checkpoint in
        // that case; structural totals must never make a stale progress row win.
        const snapshotRunId = clean(snapshotProgress && (snapshotProgress.runId || snapshotProgress.run_id) || "");
        const baseRunId = clean(baseProgress && (baseProgress.runId || baseProgress.run_id) || "");
        const snapshotDone = Math.max(0, Number(snapshotProgress && snapshotProgress.done || 0) || 0);
        const baseDone = Math.max(0, Number(baseProgress && baseProgress.done || 0) || 0);
        const snapshotProgressTime = lessonProgressSnapshotTimestamp(snapshotProgress || {});
        const baseProgressTime = lessonProgressSnapshotTimestamp(baseProgress || {});
        const isActivePartialProgress = (progress = null) => {
          const row = progress && typeof progress === "object" ? progress : {};
          const total = Math.max(0, Number(row.total ?? row.nodeTotal ?? row.node_total ?? 0) || 0);
          const done = Math.max(0, Number(row.done ?? row.nodeDone ?? row.node_done ?? 0) || 0);
          const percent = Math.max(0, Math.min(100, Number(row.percent || 0) || 0));
          const activeRun = Boolean(row.activeRun || row.active_run);
          const completed = Boolean(row.completed || row.complete || row.lessonComplete || row.vocabComplete);
          return Boolean(!completed && total > 0 && done < total && percent < 100 && (activeRun || done > 0 || row.in_progress));
        };
        const snapshotBeatsBaseProgress = Boolean(
          snapshotProgress &&
          snapshotRunId &&
          isActivePartialProgress(snapshotProgress) &&
          (
            !baseProgress ||
            !isActivePartialProgress(baseProgress) ||
            !baseRunId ||
            (
              snapshotRunId === baseRunId &&
              snapshotDone >= baseDone &&
              (!baseProgressTime || snapshotProgressTime >= baseProgressTime)
            ) ||
            (
              snapshotRunId !== baseRunId &&
              snapshotProgressTime > baseProgressTime
            )
          )
        );
        const useSnapshotProgress = Boolean(
          snapshotProgress &&
          (
            activeOverride ||
            snapshotBeatsBaseProgress ||
            !baseProgress ||
            canonicalMediaCorrection ||
            (snapshot && lessonProgressSnapshotTimestamp(snapshot) && compareLessonProgressSnapshotOrder(snapshot, baseOrder) >= 0)
          )
        );
        const mergedStudy = {
          ...(useSnapshotProgress ? baseStudy : snapshotStudy),
          ...(useSnapshotProgress ? snapshotStudy : baseStudy),
        };
        if (useSnapshotProgress) {
          mergedStudy.progress = {
            ...(baseStudy.progress && typeof baseStudy.progress === "object" ? baseStudy.progress : {}),
            ...snapshotProgress,
          };
          mergedStudy.progress_text = clean(mergedStudy.progress.text || "");
          mergedStudy.progress_percent = Number(mergedStudy.progress.percent ?? 0) || 0;
        } else if (baseProgress) {
          mergedStudy.progress = { ...baseProgress };
          mergedStudy.progress_text = clean(mergedStudy.progress_text || mergedStudy.progress.text || "");
          mergedStudy.progress_percent = Number(mergedStudy.progress_percent ?? mergedStudy.progress.percent ?? 0) || 0;
        }
        return {
          ...entry,
          study: mergedStudy,
          progress: mergedStudy.progress || entry.progress,
        };
      };

      const applyLessonVaultProgressSnapshotToPayload = (payload = {}) => {
        const timelineStartedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
        if (typeof window !== "undefined") {
          const metrics = window.__ftLoginTimelineMetrics = window.__ftLoginTimelineMetrics || { counts: {}, totalMs: {}, maxMs: {} };
          if (typeof window.__ftRecordLoginTimelinePhase !== "function") {
            window.__ftRecordLoginTimelinePhase = (phase = "", ms = 0) => {
              const key = String(phase || "").trim();
              if (!key) return;
              const duration = Math.max(0, Number(ms) || 0);
              metrics.counts[key] = Number(metrics.counts[key] || 0) + 1;
              metrics.totalMs[key] = Number((Number(metrics.totalMs[key] || 0) + duration).toFixed(3));
              metrics.maxMs[key] = Math.max(Number(metrics.maxMs[key] || 0), duration);
            };
          }
        }
        const source = payload && typeof payload === "object" ? payload : {};
        if (source.progress_snapshot) {
          rememberLessonVaultProgressSnapshot(source.progress_snapshot);
        }
        if (source.__ftLessonVaultProgressSnapshotGeneration === lessonVaultProgressSnapshotGeneration) {
          return source;
        }
        const next = { ...source };
        if (Array.isArray(next.entries)) {
          next.entries = next.entries.map((entry) => applyLessonVaultProgressSnapshotToEntry(entry));
        }
        if (Array.isArray(next.tasks)) {
          next.tasks = next.tasks.map((task) => applyLessonVaultProgressSnapshotToEntry(task));
        }
        if (Array.isArray(next.space_tasks)) {
          next.space_tasks = next.space_tasks.map((task) => applyLessonVaultProgressSnapshotToEntry(task));
        }
        // Space Task's canonical nested rows are rendered from space_task.tasks;
        // keep that branch on the same lesson-id/path snapshot as the aliases above.
        if (next.space_task && typeof next.space_task === "object" && Array.isArray(next.space_task.tasks)) {
          next.space_task = {
            ...next.space_task,
            tasks: next.space_task.tasks.map((task) => applyLessonVaultProgressSnapshotToEntry(task)),
          };
        }
        if (typeof window !== "undefined" && typeof window.__ftRecordLoginTimelinePhase === "function") {
          const timelineEndedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
          window.__ftRecordLoginTimelinePhase("applyLessonVaultProgressSnapshotToPayload", timelineEndedAt - timelineStartedAt);
        }
        try {
          Object.defineProperty(next, "__ftLessonVaultProgressSnapshotGeneration", {
            value: lessonVaultProgressSnapshotGeneration,
            enumerable: false,
            configurable: true,
          });
        } catch (error) {
          try {
            next.__ftLessonVaultProgressSnapshotGeneration = lessonVaultProgressSnapshotGeneration;
          } catch (_error) {
          }
        }
        return next;
      };

      const pruneLessonProgressOverrides = () => {
        const now = Date.now();
        lessonProgressOverrides.forEach((value, key) => {
          if (!value || Number(value.expiresAt || 0) < now) {
            lessonProgressOverrides.delete(key);
          }
        });
      };

      // Prevent stale echoes and lifetime completion history from replacing an identified active run.
      const shouldKeepExistingLessonProgressOverride = (existing = null, incoming = null) => {
        const current = existing && existing.progress && typeof existing.progress === "object" ? existing.progress : null;
        const next = incoming && typeof incoming === "object" ? incoming : null;
        const currentSpace = clean(current && current.space).toLowerCase();
        const nextSpace = clean(next && next.space).toLowerCase();
        if (!current || !next || !["space_v", "space_w", "space_q", "space_p", "space_l", "space_s"].includes(currentSpace)) {
          return false;
        }
        // 2026-08-03: incomplete or differently-cased cache rows cannot clear
        // a newer identified active-run override.
        if (!nextSpace || nextSpace !== currentSpace) {
          return true;
        }
        const currentRunId = clean(current.runId || current.run_id || "");
        const nextRunId = clean(next.runId || next.run_id || "");
        const nextCompleted = Boolean(next.completed || next.complete || next.vocabComplete || next.lessonComplete);
        if (nextCompleted) {
          const nextStillActive = Boolean(next.activeRun || next.active_run);
          if (lessonProgressIsActivePartial(current) && currentRunId && nextRunId === currentRunId && nextStillActive) {
            // A completed summary that still claims the active run is lifetime-history fallback,
            // not a real completion of this run. Keep the local New Study chart.
            return true;
          }
          if (lessonProgressIsActivePartial(current) && currentRunId && !nextRunId) {
            return true;
          }
          return false;
        }
        if (next.reviewing || next.reviewRun) {
          return false;
        }
        const currentDone = Math.max(0, Math.floor(Number(current.done || 0) || 0));
        const nextDone = Math.max(0, Math.floor(Number(next.done || 0) || 0));
        const currentTotal = Math.max(0, Math.floor(Number(current.total || 0) || 0));
        const nextTotal = Math.max(0, Math.floor(Number(next.total || 0) || 0));
        const currentPercent = Math.max(0, Math.min(100, Number(current.percent || 0) || 0));
        const nextPercent = Math.max(0, Math.min(100, Number(next.percent || 0) || 0));
        const currentTimestamp = lessonProgressSnapshotTimestamp(current);
        const nextTimestamp = lessonProgressSnapshotTimestamp(next);
        if (nextRunId && currentRunId && nextRunId !== currentRunId) {
          return Boolean(currentTimestamp && nextTimestamp && currentTimestamp > nextTimestamp);
        }
        if (nextRunId && currentRunId && nextRunId === currentRunId && currentTotal && nextTotal && currentTotal === nextTotal && nextDone < currentDone) {
          return true;
        }
        if (nextRunId && currentRunId && nextRunId === currentRunId && nextTimestamp && currentTimestamp) {
          if (nextTimestamp > currentTimestamp) {
            return false;
          }
          if (nextTimestamp < currentTimestamp) {
            return true;
          }
        }
        if (nextRunId && !currentRunId && nextTimestamp && (!currentTimestamp || nextTimestamp >= currentTimestamp)) {
          return false;
        }
        const currentCompleted = Boolean(current.completed || current.complete || current.vocabComplete || current.lessonComplete || currentPercent >= 100);
        const nextActivePartial = lessonProgressIsActivePartial(next);
        if (currentCompleted && nextActivePartial) {
          return false;
        }
        if (currentTotal && nextTotal && currentTotal === nextTotal && nextDone < currentDone) {
          return true;
        }
        return Boolean(nextPercent < currentPercent && nextDone <= currentDone);
      };

      const setLessonProgressOverride = (paths = [], progress = null, ttlMs = 18000, options = {}) => {
        pruneLessonProgressOverrides();
        if (!progress || typeof progress !== "object") {
          return;
        }
        const expiresAt = Date.now() + Math.max(3000, Number(ttlMs) || 18000);
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = lessonProgressOverrideKey(path);
          if (key) {
            const existing = lessonProgressOverrides.get(key);
            if (!options.force && shouldKeepExistingLessonProgressOverride(existing, progress)) {
              return;
            }
            lessonProgressOverrides.set(key, { progress: { ...progress, syncing: true }, expiresAt });
          }
        });
        updateLessonVaultProgressSnapshotForPaths(paths, progress);
        patchLessonVaultCachedProgress(paths, progress, { render: true, force: Boolean(options.force) });
        if (typeof window !== "undefined" && typeof window.__ftPatchLessonTaskPanelProgress === "function") {
          window.__ftPatchLessonTaskPanelProgress(paths, progress);
        }
        console.info("[SPACE_V_PROGRESS_DEBUG] setLessonProgressOverride", {
          paths: (Array.isArray(paths) ? paths : [paths]).map((path) => normalizeServerPathValue(path)).filter(Boolean),
          progress,
          ttlMs,
        });
      };

      const clearLessonProgressOverride = (paths = []) => {
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = lessonProgressOverrideKey(path);
          if (key) {
            lessonProgressOverrides.delete(key);
          }
        });
      };

      const lessonProgressOverrideForPaths = (paths = []) => {
        pruneLessonProgressOverrides();
        for (const path of (Array.isArray(paths) ? paths : [paths])) {
          const key = lessonProgressOverrideKey(path);
          if (key && lessonProgressOverrides.has(key)) {
            return lessonProgressOverrides.get(key).progress;
          }
        }
        return null;
      };

      const applyLessonProgressOverride = (study = {}, paths = []) => {
        const override = lessonProgressOverrideForPaths(paths);
        if (!override) {
          return study || {};
        }
        return {
          ...(study && typeof study === "object" ? study : {}),
          progress: override,
        };
      };

      const lessonProgressResolvedOwner = (owner = "", paths = []) => {
        const fallback = clean(owner || "");
        if (typeof lessonVaultTaskOwnerForPath !== "function") {
          return fallback;
        }
        const path = (Array.isArray(paths) ? paths : [paths])
          .map((value) => normalizeServerPathValue(value || ""))
          .find((value) => value && !value.toLowerCase().startsWith("space:"));
        return clean(lessonVaultTaskOwnerForPath(path || "", fallback, null) || fallback);
      };

      const isAdminViewingOtherLearner = (owner = "", paths = []) => {
        const target = lessonProgressResolvedOwner(owner, paths);
        const viewer = clean(currentAuthUsername || "");
        return Boolean(currentAuthIsAdmin && target && viewer && target.toLowerCase() !== viewer.toLowerCase());
      };

      const splitLessonProgressForViewer = (study = {}, paths = [], owner = "") => {
        const source = study && typeof study === "object" ? study : {};
        const override = lessonProgressOverrideForPaths(paths);
        const baseAdminProgress = source && typeof source.admin_progress === "object" ? source.admin_progress : null;
        if (isAdminViewingOtherLearner(owner, paths)) {
          return {
            study: source,
            adminProgress: override || baseAdminProgress,
          };
        }
        // Updated 2026-08-03: an admin inside their own folder is the normal learner;
        // fold legacy admin fields into the single user surface instead of rendering two charts.
        const ownAdminView = Boolean(currentAuthIsAdmin && authUsernameMatches(lessonProgressResolvedOwner(owner, paths), currentAuthUsername));
        const sourceProgress = source.progress && typeof source.progress === "object" ? source.progress : null;
        const selfProgress = override || sourceProgress || (ownAdminView ? baseAdminProgress : null);
        const selfStudy = ownAdminView
          ? {
            ...source,
            admin_view: false,
            mine: Math.max(0, Number(source.mine || 0) || 0, Number(source.admin_mine || 0) || 0),
            completed_runs: Math.max(0, Number(source.completed_runs || source.completedRuns || 0) || 0, Number(source.admin_mine || 0) || 0),
            completedRuns: Math.max(0, Number(source.completedRuns || source.completed_runs || 0) || 0, Number(source.admin_mine || 0) || 0),
            mine_last: parseLessonProgressTimestamp(source.admin_mine_last || "") > parseLessonProgressTimestamp(source.mine_last || "")
              ? clean(source.admin_mine_last || "")
              : clean(source.mine_last || ""),
            ...(selfProgress ? {
              progress: selfProgress,
              progress_text: clean(selfProgress.text || source.progress_text || ""),
              progress_percent: Math.max(0, Math.min(100, Number(selfProgress.percent ?? source.progress_percent ?? 0) || 0)),
            } : {}),
          }
          : (override ? { ...source, progress: override } : source);
        return {
          study: selfStudy,
          adminProgress: null,
        };
      };

      const adminViewerCompletionCount = (study = {}) => {
        const source = study && typeof study === "object" ? study : {};
        return Math.max(
          0,
          Math.floor(Number(source.admin_progress_mine || source.admin_viewer_mine || 0) || 0),
        );
      };

      const adminProgressHasPriorCompletion = (study = {}, progress = null) => {
        const source = study && typeof study === "object" ? study : {};
        const progressSource = progress && typeof progress === "object" ? progress : {};
        if (lessonProgressIsActivePartial(progressSource)) {
          return false;
        }
        return Boolean(
          adminViewerCompletionCount(source) > 0 ||
          source.admin_progress_completed ||
          progressSource.previously_completed ||
          progressSource.previouslyCompleted
        );
      };

      const lessonProgressIsActivePartial = (progress = null) => {
        const source = progress && typeof progress === "object" ? progress : {};
        const total = Math.max(0, Math.floor(Number(source.total ?? source.nodeCount ?? source.node_total ?? source.nodeTotal ?? 0) || 0));
        const done = Math.max(0, Math.floor(Number(source.done ?? source.nodeIndex ?? source.node_done ?? source.nodeDone ?? 0) || 0));
        const percent = Math.max(0, Math.min(100, Number(source.percent || 0) || 0));
        const activeRun = Boolean(source.activeRun || source.active_run);
        const reviewing = Boolean(source.reviewing || source.reviewRun);
        const completed = !reviewing && !activeRun && Boolean(source.completed || source.complete || source.lessonComplete || source.vocabComplete);
        return Boolean(
          !completed &&
          total > 0 &&
          done < total &&
          percent < 100 &&
          (reviewing || (done > 0 && source.in_progress !== false) || activeRun)
        );
      };

      // Added 2026-07-06: counts Space_V progress from learnedCount when drill snapshots omit state.learned keys.
      const vocabProgressLearnedCountFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const learnedList = Array.isArray(state.learned) ? new Set(state.learned.map(clean).filter(Boolean)).size : 0;
        const learnedWords = Array.isArray(state.learnedWords)
          ? new Set(state.learnedWords.map((item) => {
            if (item && typeof item === "object") {
              return clean(item.key || item.word || item.text || item.lemma || "");
            }
            return clean(item);
          }).filter(Boolean)).size
          : 0;
        return Math.max(
          0,
          learnedList,
          learnedWords,
          Math.floor(Number(source.learnedCount ?? source.learned_count ?? 0) || 0),
          Math.floor(Number(state.learnedCount ?? state.learned_count ?? 0) || 0),
        );
      };

      const vocabProgressOverrideFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const total = Math.max(0, Math.floor(Number(source.nodeCount ?? state.nodeCount ?? vocabItems.length ?? 0) || 0));
        if (!total) {
          return null;
        }
        const learned = vocabProgressLearnedCountFromRecord(record);
        const nodeIndex = Math.max(0, Math.floor(Number(source.nodeIndex ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0));
        const hasLearnedProgress = (
          Array.isArray(state.learned)
          || Array.isArray(state.learnedWords)
          || Object.prototype.hasOwnProperty.call(source, "learnedCount")
          || Object.prototype.hasOwnProperty.call(source, "learned_count")
          || Object.prototype.hasOwnProperty.call(state, "learnedCount")
          || Object.prototype.hasOwnProperty.call(state, "learned_count")
        );
        const reviewing = Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun);
        const activeRun = Boolean(source.activeRun || source.active_run || state.activeRun || state.active_run);
        const complete = Boolean(source.complete || source.vocabComplete || source.lessonComplete || state.complete || state.vocabComplete || state.lessonComplete);
        const lessonStudy = state.lessonSource && state.lessonSource.study && typeof state.lessonSource.study === "object" ? state.lessonSource.study : {};
        const learnedBefore = Math.max(0, Math.floor(Number(lessonStudy.mine || lessonStudy.admin_mine || 0) || 0)) > 0;
        const relearning = Boolean(activeRun && !complete && learnedBefore);
        const runId = clean(source.runId || source.run_id || state.runId || state.run_id || "");
        const savedAt = clean(source.savedAt || source.saved_at || state.savedAt || state.saved_at || "");
        const updatedAt = clean(source.updatedAt || source.updated_at || state.updatedAt || state.updated_at || savedAt);
        const done = complete && !reviewing
          ? total
          : Math.max(0, Math.min(total, hasLearnedProgress ? learned : nodeIndex));
        const percent = complete && !reviewing
          ? 100
          : Math.max(0, Math.min(reviewing ? 99 : 100, Math.round((done / total) * 100)));
        const text = `${done}/${total}`;
        return reviewing
          ? {
            space: "Space_V",
            label: "Review",
            done,
            total,
            percent,
            text,
            completed: done >= total,
            reviewing: true,
            reviewRun: true,
            review_percent: percent,
            review_done: done,
            review_total: total,
            review_text: text,
            in_progress: done < total,
            syncing: true,
            runId,
            savedAt,
            updatedAt,
          }
          : {
            space: "Space_V",
            label: "Words",
            done,
            total,
            percent,
            text,
            completed: complete || done >= total,
            in_progress: done < total && (done > 0 || activeRun),
            activeRun,
            previously_completed: relearning || undefined,
            previouslyCompleted: relearning || undefined,
            relearning: relearning || undefined,
            relearnLabel: relearning ? "Relearn" : undefined,
            syncing: true,
            runId,
            savedAt,
            updatedAt,
          };
      };

      const questionProgressOverrideFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        // Exit can run after the cached checkpoint was written by an early manifest
        // (for example 16 nodes) while the live payload has the complete 48-item
        // workload. Prefer the live counters for the active lesson handoff.
        const liveStats = typeof questionModeActive !== "undefined" && questionModeActive
          && typeof questionNodes !== "undefined" && Array.isArray(questionNodes) && questionNodes.length
          && typeof questionProgressStats === "function"
          ? questionProgressStats()
          : null;
        const questionTotal = Math.max(0, Math.floor(Number(liveStats?.total ?? state.questionTotal ?? state.totalQuestions ?? 0) || 0));
        const nodeTotal = Math.max(0, Math.floor(Number(liveStats?.totalNodes ?? state.totalNodes ?? source.nodeCount ?? state.nodeCount ?? questionNodes.length ?? 0) || 0));
        const total = questionTotal || nodeTotal;
        if (!total) {
          return null;
        }
        const reviewing = Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun);
        const activeRun = Boolean(source.activeRun || source.active_run || state.activeRun || state.active_run);
        const runId = clean(source.runId || source.run_id || state.runId || state.run_id || "");
        const savedAt = clean(source.savedAt || state.savedAt || "");
        const updatedAt = clean(source.updatedAt || state.updatedAt || savedAt);
        const questionDone = Math.max(0, Math.floor(Number(liveStats?.done ?? state.questionDone ?? state.completedQuestions ?? 0) || 0));
        const nodeDone = Math.max(0, Math.floor(Number(liveStats?.completedNodes ?? state.completedNodes ?? 0) || 0));
        const done = Math.max(0, Math.min(total, questionTotal ? questionDone : nodeDone));
        const percent = Math.max(0, Math.min(reviewing ? 99 : 100, Math.round((done / total) * 100)));
        const text = `${done}/${total}`;
        const base = {
          space: "Space_Q",
          label: "Space_Q",
          done,
          total,
          percent,
          text,
          node_done: nodeDone,
          node_total: nodeTotal,
          nodes_text: nodeTotal ? `${nodeDone}/${nodeTotal}` : "",
          in_progress: done < total && (done > 0 || activeRun),
          activeRun,
          runId,
          savedAt,
          updatedAt,
          syncing: true,
          pending_sync: true,
        };
        return reviewing
          ? {
            ...base,
            completed: true,
            reviewing: true,
            reviewRun: true,
            review_done: done,
            review_total: total,
            review_percent: percent,
            review_text: text,
          }
          : base;
      };

      // Added 2026-07-15: lets Space_W Back update Lesson Vault DOM from the fresh local/server progress record.
      const spaceWProgressOverrideFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const nodeTotal = Math.max(0, Math.floor(Number(source.nodeCount ?? state.nodeCount ?? lessonNodes.length ?? pendingLessonNodes.length ?? 0) || 0));
        if (!nodeTotal) {
          return null;
        }
        const nodeIndex = Math.max(0, Math.floor(Number(source.nodeIndex ?? state.currentIndex ?? state.index ?? state.nodeIndex ?? 0) || 0));
        const reviewing = Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun || state.reviewModeActive);
        const reviewFinished = Boolean(source.reviewFinished || state.reviewFinished);
        const complete = Boolean(source.complete || source.lessonComplete || state.complete || state.lessonComplete);
        const activeRun = Boolean(!complete && (source.activeRun || source.active_run || state.activeRun || state.active_run));
        const reviewMastered = Array.isArray(state.reviewMastered)
          ? new Set(state.reviewMastered.map((value) => Math.max(0, Math.floor(Number(value) || 0))).filter((value) => value < nodeTotal)).size
          : 0;
        const derivedTotal = nodeTotal * 2;
        const derivedDone = reviewing || reviewFinished
          ? nodeTotal + reviewMastered
          : nodeIndex;
        const total = Math.max(derivedTotal, Math.floor(Number(source.progressTotal ?? source.progress_total ?? state.progressTotal ?? state.progress_total ?? 0) || 0));
        const done = complete || reviewFinished
          ? total
          : Math.max(0, Math.min(total, Math.floor(Number(source.progressDone ?? source.progress_done ?? state.progressDone ?? state.progress_done ?? derivedDone) || 0)));
        const percent = complete || reviewFinished
          ? 100
          : Math.max(0, Math.min(99, Math.round((done / total) * 100)));
        const runId = clean(source.runId || source.run_id || state.runId || state.run_id || "");
        const savedAt = clean(source.savedAt || source.saved_at || state.savedAt || state.saved_at || "");
        const updatedAt = clean(source.updatedAt || source.updated_at || state.updatedAt || state.updated_at || savedAt);
        const rootNodeTotal = Math.max(0, Math.floor(Number(source.rootNodeCount ?? state.rootNodeCount ?? nodeTotal) || 0));
        const normalSentenceCount = Math.max(0, Math.floor(Number(source.normalSentenceCount ?? state.normalSentenceCount ?? rootNodeTotal) || 0));
        const trainSentenceCount = Math.max(0, Math.floor(Number(source.trainSentenceCount ?? state.trainSentenceCount ?? 0) || 0));
        const sentenceCount = Math.max(normalSentenceCount + trainSentenceCount, Math.floor(Number(source.sentenceCount ?? state.sentenceCount ?? 0) || 0));
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const lessonStudy = lessonSource.study && typeof lessonSource.study === "object" ? lessonSource.study : {};
        const completedRuns = Math.max(
          0,
          Math.floor(Number(source.completedRuns ?? source.completed_runs ?? 0) || 0),
          Math.floor(Number(state.completedRuns ?? state.completed_runs ?? 0) || 0),
          Math.floor(Number(lessonStudy.mine || 0) || 0),
          Math.floor(Number(lessonStudy.completedRuns ?? lessonStudy.completed_runs ?? 0) || 0),
        );
        return {
          space: "Space_W",
          label: "Nodes",
          done,
          total,
          percent,
          text: `${done}/${total}`,
          node_done: Math.max(0, Math.min(nodeTotal, nodeIndex)),
          node_total: nodeTotal,
          nodes_text: `${Math.max(0, Math.min(nodeTotal, nodeIndex))}/${nodeTotal}`,
          completed: Boolean(complete || reviewFinished),
          in_progress: Boolean(done < total && (done > 0 || activeRun)),
          activeRun,
          reviewing,
          reviewRun: reviewing,
          review_done: reviewMastered,
          review_total: nodeTotal,
          runId,
          savedAt,
          updatedAt,
          root_node_total: rootNodeTotal,
          sentenceCount,
          normalSentenceCount,
          trainSentenceCount,
          completedRuns,
          completed_runs: completedRuns,
          previously_completed: completedRuns > 0,
          previouslyCompleted: completedRuns > 0,
          syncing: true,
          pending_sync: true,
        };
      };

      const paragraphProgressOverrideFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const spaceMode = clean(state.spaceMode || source.spaceMode || source.space).toLowerCase();
        const space = spaceMode === "space_l"
          ? "Space_L"
          : (spaceMode === "space_s" ? "Space_S" : "Space_P");
        const label = "Sentences";
        const tokenTotal = Math.max(0, Math.floor(Number(state.totalTokens ?? state.tokenTotal ?? 0) || 0));
        const tokenDone = Math.max(0, Math.floor(Number(state.completedTokens ?? state.tokenDone ?? 0) || 0));
        const segmentTotal = Math.max(0, Math.floor(Number(state.totalSegments ?? state.segmentTotal ?? 0) || 0));
        const segmentDone = Math.max(0, Math.floor(Number(state.completedSegments ?? state.segmentDone ?? 0) || 0));
        const summaryTotal = Math.max(0, Math.floor(Number(source.total ?? 0) || 0));
        const summaryDone = Math.max(0, Math.floor(Number(source.done ?? 0) || 0));
        const nodeTotal = Math.max(0, Math.floor(Number(state.totalNodes ?? source.nodeCount ?? source.node_total ?? source.nodeTotal ?? state.nodeCount ?? paragraphNodes.length ?? 0) || 0));
        const nodeDone = Math.max(0, Math.floor(Number(state.completedNodes ?? source.nodeIndex ?? source.node_done ?? source.nodeDone ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0));
        const total = segmentTotal || tokenTotal || summaryTotal || nodeTotal;
        if (!total) {
          return null;
        }
        const done = Math.max(0, Math.min(total, segmentTotal ? segmentDone : (tokenTotal ? tokenDone : (summaryTotal ? summaryDone : nodeDone))));
        const reviewing = Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun);
        const activeRun = Boolean(source.activeRun || source.active_run || state.activeRun || state.active_run);
        const complete = Boolean(!activeRun && (source.complete || source.lessonComplete || state.complete || state.lessonComplete || done >= total));
        const runId = clean(source.runId || source.run_id || state.runId || state.run_id || "");
        const savedAt = clean(source.savedAt || source.saved_at || state.savedAt || state.saved_at || "");
        const updatedAt = clean(source.updatedAt || source.updated_at || state.updatedAt || state.updated_at || savedAt);
        const percent = complete && !reviewing
          ? 100
          : Math.max(0, Math.min(reviewing ? 99 : 100, Math.round((done / total) * 100)));
        const text = `${done}/${total}`;
        const base = {
          space,
          label,
          done,
          total,
          percent,
          text,
          node_done: Math.max(0, Math.min(nodeDone, nodeTotal)),
          node_total: nodeTotal,
          nodes_text: nodeTotal ? `${Math.max(0, Math.min(nodeDone, nodeTotal))}/${nodeTotal}` : "",
          completed: complete,
          in_progress: done < total && (done > 0 || activeRun || reviewing),
          activeRun: Boolean(activeRun && !complete),
          runId,
          savedAt,
          updatedAt,
          syncing: true,
          pending_sync: true,
        };
        return reviewing
          ? {
            ...base,
            completed: done >= total,
            reviewing: true,
            reviewRun: true,
            review_done: done,
            review_total: total,
            review_percent: percent,
            review_text: text,
          }
          : base;
      };

      const createLessonProgressNode = (study = {}, extraClass = "", options = {}) => {
        const sourceStudy = options && options.progress && typeof options.progress === "object"
          ? { ...(study && typeof study === "object" ? study : {}), progress: options.progress }
          : study;
        let progress = normalizedLessonProgress(sourceStudy);
        if (!progress) {
          if (!(options && options.emptyProgress)) {
            return null;
          }
          const emptyTotal = Math.max(1, Math.floor(Number(options.emptyTotal || 1) || 1));
          progress = {
            label: clean(options.emptyLabel || "Progress"),
            done: 0,
            total: emptyTotal,
            percent: 0,
            nodeDone: 0,
            nodeTotal: 0,
            valueText: clean(options.emptyValueText || `0/${emptyTotal}`),
            completed: false,
            reviewing: false,
            syncing: false,
            empty: true,
          };
        }
        const wrap = document.createElement("span");
        wrap.className = `ft-lesson-progress ${extraClass}`.trim();
        if (options && options.variantClass) {
          wrap.classList.add(options.variantClass);
        }
        wrap.classList.toggle("is-progress-complete", Boolean(progress.completed && !progress.reviewing));
        wrap.classList.toggle("is-progress-repeat", Boolean(progress.isRepeatCompletion || progress.repeatRun));
        // Added 2026-07-24: first-run Space_W review is still the same run;
        // reserve the orange repeat styling for a later New Study run.
        const repeatReview = Boolean(progress.reviewing && (progress.space !== "Space_W" || progress.completedRuns > 0));
        wrap.classList.toggle("is-progress-review", Boolean(repeatReview || (progress.relearning && !progress.completed)));
        wrap.classList.toggle("is-progress-syncing", Boolean(progress.syncing));
        wrap.classList.toggle("is-progress-empty", Boolean(progress.empty));
        wrap.classList.add("is-progress-energized");
        wrap.dataset.progressPercent = String(progress.percent);
        wrap.dataset.completionRuns = String(Math.max(0, Math.floor(Number(progress.completedRuns || 0) || 0)));
        wrap.dataset.repeatCompletion = progress.isRepeatCompletion ? "1" : "0";
        if (options && options.ownerBadge) {
          wrap.dataset.progressOwner = clean(options.ownerBadge);
        }
        wrap.style.setProperty("--lesson-progress", `${progress.percent}%`);
        wrap.title = clean(options && options.title)
          || `${clean(options && options.ownerLabel) || "Current run"}: ${progress.label} ${progress.valueText} - ${progress.percent}%${progress.reviewing ? " review" : ""}`;
        const head = document.createElement("span");
        head.className = "ft-lesson-progress-head";
        const label = document.createElement("span");
        label.className = "ft-lesson-progress-label";
        label.textContent = clean(options && options.labelText) || (
          progress.empty
            ? progress.label
            : (progress.syncing
            ? `${progress.label} syncing`
            : (progress.reviewing
              ? `${progress.label} mode`
              : (progress.completed ? `${progress.label} complete` : `${progress.label} in progress`)))
        );
        const value = document.createElement("span");
        value.className = "ft-lesson-progress-value";
        value.textContent = progress.nodeTotal && progress.label === "Questions"
          ? `${progress.valueText} | N ${progress.nodeDone}/${progress.nodeTotal} | ${progress.percent}%`
          : (progress.reviewing ? `${progress.valueText} - ${progress.percent}% review` : `${progress.valueText} - ${progress.percent}%`);
        const track = document.createElement("span");
        track.className = "ft-lesson-progress-track";
        const fill = document.createElement("span");
        fill.className = "ft-lesson-progress-fill";
        fill.setAttribute("aria-hidden", "true");
        const trackValue = document.createElement("span");
        trackValue.className = "ft-lesson-progress-track-value";
        trackValue.textContent = `${progress.percent}%`;
        track.append(fill, trackValue);
        head.append(label, value);
        wrap.append(head, track);
        if (options && options.ownerBadge) {
          const owner = document.createElement("span");
          owner.className = "ft-vault-progress-owner";
          owner.textContent = clean(options.ownerBadge);
          owner.setAttribute("aria-hidden", "true");
          wrap.appendChild(owner);
        }
        return wrap;
      };

      const appendLessonTimeChip = (row, study = {}) => {
        const seconds = Number(study.time_seconds || (study.time && study.time.seconds) || 0) || 0;
        const label = formatStudyDuration(seconds);
        if (label) {
          row.appendChild(createServerChip(`Time ${label}`, "time"));
        }
      };

      const currentLessonStudyPath = () => clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
      const currentLessonStudyId = () => {
        const value = clean(currentLessonSource && (currentLessonSource.lesson_id || currentLessonSource.file_id));
        return value.toLowerCase().startsWith("ftg-lesson-") ? value : "";
      };

      // Added 2026-07-24: linked-folder writes keep canonical identity plus their display/effective locators.
      const linkedLessonProgressIdentity = (record = {}, fallbackIdentity = "") => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const identity = clean(
          source.lesson_id || source.lessonId || source.file_id || source.fileId || source.identity ||
          state.lesson_id || state.lessonId || lessonSource.lesson_id || lessonSource.file_id ||
          currentLessonStudyId() || fallbackIdentity,
        );
        return {
          lesson_id: identity.toLowerCase().startsWith("ftg-lesson-") ? identity : "",
          linked_path: normalizeServerPathValue(source.linked_path || state.linked_path || lessonSource.linked_path || currentLessonSource && currentLessonSource.linked_path || ""),
          effective_path: normalizeServerPathValue(source.effective_path || state.effective_path || lessonSource.effective_path || currentLessonSource && currentLessonSource.effective_path || ""),
          link_target: normalizeServerPathValue(source.link_target || state.link_target || lessonSource.link_target || currentLessonSource && currentLessonSource.link_target || ""),
        };
      };

      const currentLessonStudySpace = () => {
        const pathValue = currentLessonStudyPath().toLowerCase();
        if (vocabModeActive || pathValue.endsWith(".space_v") || pathValue.endsWith(".space_b")) {
          return "Space_V";
        }
        if (questionModeActive || pathValue.endsWith(".space_q")) {
          return "Space_Q";
        }
        if (pathValue.endsWith(".space_l") || (paragraphModeActive && typeof isSpaceLPayload === "function" && isSpaceLPayload())) {
          return "Space_L";
        }
        if (pathValue.endsWith(".space_s") || (paragraphModeActive && typeof isSpaceSPayload === "function" && isSpaceSPayload())) {
          return "Space_S";
        }
        if (paragraphModeActive || pathValue.endsWith(".space_p")) {
          return "Space_P";
        }
        return "Space_W";
      };

      // Added 2026-07-20: heartbeats carry identity only; Server 2 decides credited time from its own clock.
      const createLessonStudyTimeSessionId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `lesson-${window.crypto.randomUUID()}`;
        }
        return `lesson-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
      };

      const LESSON_TIME_OUTBOX_VERSION = 1;
      const LESSON_TIME_OUTBOX_ROW_VERSION = 2;
      const LESSON_TIME_TAB_LEASE_MS = 45000;
      const lessonStudyTimeTabId = window.crypto && typeof window.crypto.randomUUID === "function"
        ? window.crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      let lessonStudyTimeTabLeaseToken = "";
      const lessonStudyTimeOwner = () => clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
      const lessonStudyTimePathHash = (value = "") => {
        let hash = 2166136261;
        String(value || "").split("").forEach((character) => {
          hash ^= character.charCodeAt(0);
          hash = Math.imul(hash, 16777619);
        });
        return (hash >>> 0).toString(36);
      };
      const lessonStudyTimeOutboxKey = () => `future_lesson_time_outbox:v${LESSON_TIME_OUTBOX_VERSION}:${lessonStudyTimeOwner()}`;
      const lessonStudyTimeOutboxRowPrefix = () => `future_lesson_time_outbox_row:v${LESSON_TIME_OUTBOX_ROW_VERSION}:${encodeURIComponent(lessonStudyTimeOwner())}:`;
      const lessonStudyTimeTabLeaseKey = () => `future_lesson_time_tab_lease:v1:${encodeURIComponent(lessonStudyTimeOwner())}`;
      const lessonStudyTimeLeaseIdentity = (pathValue = "", lessonId = "") => {
        const canonicalId = clean(lessonId || currentLessonStudyId());
        if (canonicalId.toLowerCase().startsWith("ftg-lesson-")) {
          return `id:${canonicalId.toLowerCase()}`;
        }
        return `path:${normalizeServerPathValue(pathValue).toLowerCase()}`;
      };
      const lessonStudyTimeLeaseKey = (pathValue = "", lessonId = "") => `future_lesson_time_lease:v${LESSON_TIME_OUTBOX_VERSION}:${lessonStudyTimeOwner()}:${lessonStudyTimePathHash(lessonStudyTimeLeaseIdentity(pathValue, lessonId))}`;
      const legacyLessonStudyTimeLeaseKey = (pathValue = "") => `future_lesson_time_lease:v${LESSON_TIME_OUTBOX_VERSION}:${lessonStudyTimeOwner()}:${lessonStudyTimePathHash(pathValue)}`;
      const readLessonStudyTimeJson = (key, fallback) => {
        try {
          const parsed = JSON.parse(localStorage.getItem(key) || "null");
          return parsed && typeof parsed === "object" ? parsed : fallback;
        } catch (error) {
          return fallback;
        }
      };
      const writeLessonStudyTimeJson = (key, value) => {
        try {
          localStorage.setItem(key, JSON.stringify(value));
          return true;
        } catch (error) {
          return false;
        }
      };
      const lessonStudyTimeOutboxRowIdentity = (row = {}) => `${clean(row.session_id)}:${Number(row.sequence || 0)}`;
      const lessonStudyTimeRowTarget = (row = {}) => {
        const canonicalId = clean(row.lesson_id || row.file_id);
        return canonicalId.toLowerCase().startsWith("ftg-lesson-")
          ? `id:${canonicalId.toLowerCase()}`
          : `path:${normalizeServerPathValue(row.path || "").toLowerCase()}`;
      };
      const lessonStudyTimeOutboxRowKey = (row = {}) => `${lessonStudyTimeOutboxRowPrefix()}${encodeURIComponent(lessonStudyTimeOutboxRowIdentity(row))}`;
      const writeLessonStudyTimeOutboxRow = (row = {}) => {
        const identity = lessonStudyTimeOutboxRowIdentity(row);
        return Boolean(clean(row.session_id) && Number(row.sequence || 0) >= 0 && identity && writeLessonStudyTimeJson(lessonStudyTimeOutboxRowKey(row), row));
      };
      const readLessonStudyTimeOutbox = () => {
        const rows = new Map();
        const legacy = readLessonStudyTimeJson(lessonStudyTimeOutboxKey(), { rows: [] });
        const legacyRows = Array.isArray(legacy.rows) ? legacy.rows.filter((row) => row && typeof row === "object").slice(-240) : [];
        legacyRows.forEach((row) => rows.set(lessonStudyTimeOutboxRowIdentity(row), row));
        const prefix = lessonStudyTimeOutboxRowPrefix();
        for (let index = 0; index < localStorage.length; index += 1) {
          const key = clean(localStorage.key(index));
          if (!key.startsWith(prefix)) continue;
          const row = readLessonStudyTimeJson(key, null);
          if (row && typeof row === "object" && clean(row.session_id)) rows.set(lessonStudyTimeOutboxRowIdentity(row), row);
        }
        if (legacyRows.length) {
          legacyRows.forEach((row) => {
            if (!readLessonStudyTimeJson(lessonStudyTimeOutboxRowKey(row), null)) writeLessonStudyTimeOutboxRow(row);
          });
          try { localStorage.removeItem(lessonStudyTimeOutboxKey()); } catch (error) {}
        }
        return Array.from(rows.values()).slice(-240);
      };
      const removeLessonStudyTimeOutboxRow = (row = {}) => {
        try { localStorage.removeItem(lessonStudyTimeOutboxRowKey(row)); return true; } catch (error) { return false; }
      };

      // Added 2026-07-21: only one visible tab credits lesson time for an account; server checks remain authoritative.
      const ensureLessonStudyTimeTabLease = () => {
        const key = lessonStudyTimeTabLeaseKey();
        const now = Date.now();
        const current = readLessonStudyTimeJson(key, null);
        if (lessonStudyTimeTabLeaseToken && clean(current && current.token) === lessonStudyTimeTabLeaseToken) {
          return writeLessonStudyTimeJson(key, { token: lessonStudyTimeTabLeaseToken, tabId: lessonStudyTimeTabId, expiresAt: now + LESSON_TIME_TAB_LEASE_MS });
        }
        if (current && clean(current.token) && Number(current.expiresAt || 0) > now && clean(current.tabId) !== lessonStudyTimeTabId) {
          return false;
        }
        const token = `${lessonStudyTimeTabId}:${now.toString(36)}:${Math.random().toString(36).slice(2, 9)}`;
        if (!writeLessonStudyTimeJson(key, { token, tabId: lessonStudyTimeTabId, expiresAt: now + LESSON_TIME_TAB_LEASE_MS })) return false;
        const confirmed = readLessonStudyTimeJson(key, null);
        if (clean(confirmed && confirmed.token) !== token) return false;
        lessonStudyTimeTabLeaseToken = token;
        return true;
      };
      const releaseLessonStudyTimeTabLease = () => {
        if (!lessonStudyTimeTabLeaseToken) return false;
        const key = lessonStudyTimeTabLeaseKey();
        const current = readLessonStudyTimeJson(key, null);
        if (clean(current && current.token) !== lessonStudyTimeTabLeaseToken) {
          lessonStudyTimeTabLeaseToken = "";
          return false;
        }
        try { localStorage.removeItem(key); } catch (error) { return false; }
        lessonStudyTimeTabLeaseToken = "";
        return true;
      };
      // Added 2026-07-24: direct/link aliases share one lesson-time lease by canonical lesson ID.
      const readLessonStudyTimeLease = (pathValue = "", lessonId = "") => {
        const canonicalKey = lessonStudyTimeLeaseKey(pathValue, lessonId);
        const canonical = readLessonStudyTimeJson(canonicalKey, null);
        if (canonical) return canonical;
        const canonicalId = clean(lessonId || currentLessonStudyId());
        if (!canonicalId.toLowerCase().startsWith("ftg-lesson-")) return null;
        const legacyKey = legacyLessonStudyTimeLeaseKey(pathValue);
        const legacy = readLessonStudyTimeJson(legacyKey, null);
        if (!legacy) return null;
        const migrated = { ...legacy, lesson_id: canonicalId, migrated_from_path_key: true };
        if (writeLessonStudyTimeJson(canonicalKey, migrated)) {
          try { localStorage.removeItem(legacyKey); } catch (error) {}
        }
        return migrated;
      };
      const rememberLessonStudyTimeLease = (pathValue, result = {}, lessonId = "") => {
        const token = clean(result.offlineLease || lessonStudyTimeOfflineLease);
        if (!token || !lessonStudyTimeSessionId) return null;
        const canonicalId = clean(result.lesson_id || result.file_id || lessonId || currentLessonStudyId());
        lessonStudyTimeOfflineLease = token;
        const record = {
          path: clean(pathValue),
          lesson_id: canonicalId.toLowerCase().startsWith("ftg-lesson-") ? canonicalId : "",
          session_id: lessonStudyTimeSessionId,
          sequence: Math.max(0, Number(lessonStudyTimeSequence || 0) || 0),
          offline_lease: token,
          expires_epoch: Math.max(0, Number(result.offlineLeaseExpiresEpoch || 0) || 0),
          claim_deadline_epoch: Math.max(0, Number(result.offlineLeaseClaimDeadlineEpoch || 0) || 0),
        };
        writeLessonStudyTimeJson(lessonStudyTimeLeaseKey(pathValue, canonicalId), record);
        return record;
      };
      const queueLessonStudyTimeOfflineClaim = (payload = {}) => {
        if (!clean(payload.offline_lease) || !(Number(payload.seconds || 0) > 0)) return false;
        const identity = `${clean(payload.session_id)}:${Number(payload.sequence || 0)}`;
        if (readLessonStudyTimeOutbox().some((row) => lessonStudyTimeOutboxRowIdentity(row) === identity)) return true;
        return writeLessonStudyTimeOutboxRow({ ...payload, queued_at: new Date().toISOString() });
      };
      const applyLessonStudyTimeServerResult = (pathValue, payload = {}) => {
        const row = payload && payload.time && typeof payload.time === "object" ? payload.time : payload;
        const responseSessionId = clean(row.sessionId);
        if (responseSessionId && lessonStudyTimeSessionId && responseSessionId !== lessonStudyTimeSessionId) return row;
        if (clean(row.offlineLease)) lessonStudyTimeOfflineLease = clean(row.offlineLease);
        rememberLessonStudyTimeLease(pathValue, row, currentLessonStudyId());
        const timePaths = [pathValue, currentLessonSource && currentLessonSource.path, currentLessonSource && currentLessonSource.effective_path, currentLessonSource && currentLessonSource.link_target, currentLessonSource && currentLessonSource.linked_path].filter(Boolean);
        if (timePaths.length && typeof pinVisibleLessonVaultTimeChip === "function") {
          pinVisibleLessonVaultTimeChip(timePaths, row, { retryMs: 180 });
        }
        return row;
      };
      const drainLessonStudyTimeOfflineClaims = async () => {
        if (!authToken) return false;
        const rows = readLessonStudyTimeOutbox();
        if (!rows.length) return true;
        const first = rows[0];
        const firstTarget = lessonStudyTimeRowTarget(first);
        const group = rows.filter((row) => (
          lessonStudyTimeRowTarget(row) === firstTarget
          && clean(row.session_id) === clean(first.session_id)
          && clean(row.offline_lease) === clean(first.offline_lease)
        )).slice(0, 120);
        if (!group.length) return true;
        const maxSequence = Math.max(...group.map((row) => Math.max(0, Number(row.sequence || 0) || 0)));
        try {
          const result = await fetchAuthJson("/lesson/time", {
            method: "POST",
            body: JSON.stringify({
              path: clean(first.path),
              lesson_id: clean(first.lesson_id),
              title: clean(first.title),
              source: clean(first.source),
              seconds: 0,
              protocol: "server-time-v1",
              session_id: clean(first.session_id),
              sequence: maxSequence,
              offline_lease: clean(first.offline_lease),
              offline_claims: group.map((row) => ({ sequence: Number(row.sequence || 0), seconds: Number(row.seconds || 0) })),
            }),
          });
          const serverRow = result && result.payload && result.payload.time ? result.payload.time : {};
          if (clean(serverRow.heartbeatReason) === "session_conflict") return false;
          group.forEach(removeLessonStudyTimeOutboxRow);
          applyLessonStudyTimeServerResult(clean(first.path), result && result.payload ? result.payload : {});
          return true;
        } catch (error) {
          return false;
        }
      };

      const sendLessonStudyTimeTick = async (seconds = 30, options = {}) => {
        const pathValue = currentLessonStudyPath();
        if (!authToken && typeof getStoredAuthToken === "function") {
          authToken = getStoredAuthToken();
        }
        if (!authToken || !pathValue || lessonStudyTimeBusy || !loadGate.classList.contains("is-hidden")) {
          return null;
        }
        if (
          !(options && options.crossTabLockHeld)
          && typeof navigator !== "undefined"
          && navigator.locks
          && typeof navigator.locks.request === "function"
        ) {
          return navigator.locks.request(
            `future-lesson-time:${lessonStudyTimeOwner()}`,
            { ifAvailable: true },
            (lock) => lock ? sendLessonStudyTimeTick(seconds, { ...(options || {}), crossTabLockHeld: true }) : null,
          );
        }
        if (!ensureLessonStudyTimeTabLease()) {
          return null;
        }
        if (!lessonStudyTimeSessionId) {
          const savedLease = readLessonStudyTimeLease(pathValue, currentLessonStudyId());
          lessonStudyTimeSessionId = clean(savedLease && savedLease.session_id) || createLessonStudyTimeSessionId();
          lessonStudyTimeSequence = Math.max(0, Number(savedLease && savedLease.sequence || 0) || 0);
          lessonStudyTimeOfflineLease = clean(savedLease && savedLease.offline_lease);
        }
        const starting = Boolean(options && options.start);
        const savedLease = readLessonStudyTimeLease(pathValue, currentLessonStudyId());
        const savedSequence = clean(savedLease && savedLease.session_id) === lessonStudyTimeSessionId
          ? Math.max(0, Number(savedLease && savedLease.sequence || 0) || 0)
          : 0;
        const sequence = starting ? 0 : Math.max(lessonStudyTimeSequence, savedSequence) + 1;
        lessonStudyTimeSequence = Math.max(lessonStudyTimeSequence, sequence);
        rememberLessonStudyTimeLease(pathValue, {}, currentLessonStudyId());
        lessonStudyTimeBusy = true;
        try {
          await drainLessonStudyTimeOfflineClaims();
          const result = await fetchAuthJson("/lesson/time", {
            method: "POST",
            body: JSON.stringify({
              path: pathValue,
              lesson_id: currentLessonStudyId(),
              seconds,
              protocol: "server-time-v1",
              session_id: lessonStudyTimeSessionId,
              sequence,
              offline_lease: lessonStudyTimeOfflineLease,
              source: currentLessonStudySpace(),
              title: clean(currentLessonSource.title || currentLessonSource.name || "Future lesson"),
            }),
          });
          applyLessonStudyTimeServerResult(pathValue, result && result.payload ? result.payload : {});
          if (currentLessonStudySpace() === "Space_V" && typeof saveVocabProgressNow === "function") {
            try {
              saveVocabProgressNow();
            } catch (progressError) {
              console.warn("[SPACE_V_PROGRESS_DEBUG] heartbeat progress save failed", progressError);
            }
          }
          return result && result.payload ? result.payload : null;
        } catch (error) {
          queueLessonStudyTimeOfflineClaim({
            path: pathValue,
            lesson_id: currentLessonStudyId(),
            title: clean(currentLessonSource.title || currentLessonSource.name || "Future lesson"),
            source: currentLessonStudySpace(),
            seconds,
            session_id: lessonStudyTimeSessionId,
            sequence,
            offline_lease: lessonStudyTimeOfflineLease,
          });
          return null;
        } finally {
          lessonStudyTimeBusy = false;
        }
      };

      const stopLessonStudyTimeHeartbeat = () => {
        if (lessonStudyTimeTimer) {
          window.clearInterval(lessonStudyTimeTimer);
          lessonStudyTimeTimer = 0;
        }
        if (currentLessonVaultCacheWarmTimer) {
          window.clearTimeout(currentLessonVaultCacheWarmTimer);
          currentLessonVaultCacheWarmTimer = 0;
        }
        lessonStudyTimePath = "";
        lessonStudyTimeSessionId = "";
        lessonStudyTimeSequence = 0;
        lessonStudyTimeOfflineLease = "";
        releaseLessonStudyTimeTabLease();
      };

      window.addEventListener("pagehide", releaseLessonStudyTimeTabLease);
      window.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") releaseLessonStudyTimeTabLease();
      });

      const startLessonStudyTimeHeartbeat = () => {
        if (window.__ftLessonEntryGateActivationBlocked && typeof window.__ftRunAfterLessonEntryGateOpen === "function") {
          window.__ftRunAfterLessonEntryGateOpen(() => startLessonStudyTimeHeartbeat());
          return;
        }
        const pathValue = currentLessonStudyPath();
        if (!authToken || !pathValue) {
          return;
        }
        if (lessonStudyTimeTimer && lessonStudyTimePath === pathValue) {
          return;
        }
        stopLessonStudyTimeHeartbeat();
        lessonStudyTimePath = pathValue;
        const savedLease = readLessonStudyTimeLease(pathValue, currentLessonStudyId());
        lessonStudyTimeSessionId = clean(savedLease && savedLease.session_id) || createLessonStudyTimeSessionId();
        lessonStudyTimeSequence = Math.max(0, Number(savedLease && savedLease.sequence || 0) || 0);
        lessonStudyTimeOfflineLease = clean(savedLease && savedLease.offline_lease);
        scheduleCurrentLessonVaultCacheWarm(1600, { minGapMs: 60000 });
        void sendLessonStudyTimeTick(0, { start: !lessonStudyTimeOfflineLease });
        lessonStudyTimeTimer = window.setInterval(() => {
          if (document.visibilityState && document.visibilityState !== "visible") return;
          scheduleCurrentLessonVaultCacheWarm(1200, { minGapMs: 45000 });
          void sendLessonStudyTimeTick(30);
        }, 30000);
      };

      const hashSpaceWText = (value) => {
        const text = String(value || "");
        let hash = 2166136261;
        for (let index = 0; index < text.length; index += 1) {
          hash ^= text.charCodeAt(index);
          hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0).toString(36);
      };

      const spaceWUserKey = () => clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";

      const spaceWStorageKey = (prefix, identity) => `${prefix}:${spaceWUserKey()}:${identity}`;
      const spaceWGlobalVoiceStorageKey = () => `${SPACE_W_GLOBAL_VOICE_KEY}:${spaceWUserKey()}`;

      const compactSpaceWNodeForHash = (node = {}) => ({
        vi: clean(node.vi ?? node.q ?? ""),
        en: clean(node.en ?? node.e ?? ""),
        ipa: clean(node.ipa ?? node.i ?? ""),
        voice: clean(node.voice ?? node.vc ?? ""),
        xp: rawPracticeNodesFrom(node).map((item) => ({
          en: clean(item && (item.en ?? item.e ?? item.text ?? item.sentence)),
          vi: clean(item && (item.vi ?? item.q ?? item.mn ?? item.meaning)),
        })),
      });

      const stableLessonIdFor = (payload = {}) => {
        const meta = payload && typeof payload.meta === "object" ? payload.meta : {};
        const value = clean(payload.lesson_id || payload.lessonId || payload.identity || meta.lesson_id || meta.lessonId || "");
        return value.toLowerCase().startsWith("ftg-lesson-") ? value : "";
      };

      const legacySpaceWIdentityFor = (payload = {}, nodes = []) => {
        const source = currentLessonSource || {};
        const sourceId = clean(source.path).replace(/\\/g, "/") ||
          clean(source.name || source.title || lessonTitleFromPayload(payload) || "space-w");
        const sourceKind = clean(source.source || (source.path ? "server" : "local")) || "local";
        const compactNodes = (Array.isArray(nodes) ? nodes : []).map(compactSpaceWNodeForHash);
        const contentHash = hashSpaceWText(JSON.stringify({
          title: clean(source.title || lessonTitleFromPayload(payload)),
          count: compactNodes.length,
          nodes: compactNodes,
        }));
        const sourceHash = hashSpaceWText(`${sourceKind}:${sourceId}`);
        return `${sourceKind}-${sourceHash}-${contentHash}`;
      };

      const spaceWIdentityFor = (payload = {}, nodes = []) => stableLessonIdFor(payload) || legacySpaceWIdentityFor(payload, nodes);

      const readSpaceWJson = (key) => {
        if (!key) {
          return null;
        }
        try {
          const raw = localStorage.getItem(key);
          if (!raw) {
            return null;
          }
          const parsed = JSON.parse(raw);
          return parsed && typeof parsed === "object" ? parsed : null;
        } catch (error) {
          return null;
        }
      };

      const writeSpaceWJson = (key, value) => {
        if (!key) {
          return false;
        }
        try {
          localStorage.setItem(key, JSON.stringify(value));
          return true;
        } catch (error) {
          return false;
        }
      };

      const removeSpaceWJson = (key) => {
        if (!key) {
          return;
        }
        try {
          localStorage.removeItem(key);
        } catch (error) {
        }
      };

      const selectedVoiceCacheRecord = () => {
        const selected = voiceSelect && voiceSelect.options ? voiceSelect.options[voiceSelect.selectedIndex] : null;
        return {
          value: clean(voiceSelect && voiceSelect.value),
          label: clean(selected && selected.textContent),
          cachedAt: new Date().toISOString(),
        };
      };

      const normalizeSpaceWVoiceRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        return {
          value: clean(source.value || source.voice || source.id || ""),
          label: clean(source.label || source.name || source.text || ""),
          cachedAt: clean(source.cachedAt || source.updated_at || source.updatedAt || ""),
        };
      };

      const defaultSpaceWVoiceRecord = () => ({
        value: SPACE_W_DEFAULT_VOICE,
        label: "Female UK (en-GB)",
        cachedAt: "",
      });

      const readGlobalSpaceWVoiceRecord = () => {
        const saved = normalizeSpaceWVoiceRecord(readSpaceWJson(spaceWGlobalVoiceStorageKey()));
        return saved.value ? saved : null;
      };

      const writeGlobalSpaceWVoiceRecord = (record = null) => {
        const normalized = normalizeSpaceWVoiceRecord(record);
        if (!normalized.value) {
          return false;
        }
        normalized.cachedAt = normalized.cachedAt || new Date().toISOString();
        spaceWVoicePreference = {
          value: normalized.value,
          label: normalized.label,
          updatedAt: normalized.cachedAt,
        };
        return writeSpaceWJson(spaceWGlobalVoiceStorageKey(), normalized);
      };

      const applySpaceWVoicePayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const voice = normalizeSpaceWVoiceRecord(source.space_w_voice || source.spaceWVoice || source.voice || {});
        if (!voice.value) {
          return false;
        }
        writeGlobalSpaceWVoiceRecord(voice);
        if (currentSpaceWCache && currentSpaceWCache.identity) {
          currentSpaceWCache.voiceValue = voice.value;
          currentSpaceWCache.voiceLabel = voice.label;
          currentSpaceWCache.voiceApplied = false;
          applyCachedSpaceWVoice(true);
        }
        return true;
      };

      const syncSpaceWVoicePreferenceToServer = async (record = null) => {
        if (!authToken) {
          return;
        }
        const voice = normalizeSpaceWVoiceRecord(record || spaceWVoicePreference);
        if (!voice.value) {
          return;
        }
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              question_motion: questionMotionSettings,
              space_w_voice: {
                value: voice.value,
                label: voice.label,
                updated_at: voice.cachedAt || new Date().toISOString(),
              },
            }),
          });
        } catch (error) {
          // Local storage remains the offline fallback.
        }
      };

      const applyCachedSpaceWVoice = (force = false) => {
        if (!voiceSelect || !currentSpaceWCache.voiceValue) {
          return false;
        }
        if (currentSpaceWCache.voiceApplied && !force) {
          return false;
        }
        const options = Array.from(voiceSelect.options).filter((option) => !option.disabled);
        const targetValue = clean(currentSpaceWCache.voiceValue);
        const targetLabel = clean(currentSpaceWCache.voiceLabel);
        const match = options.find((option) => option.value === targetValue) ||
          (targetLabel && options.find((option) => clean(option.textContent) === targetLabel));
        if (!match) {
          return false;
        }
        voiceSelect.value = match.value;
        voiceHint = clean(match.textContent) || match.value || voiceHint;
        currentSpaceWCache.voiceApplied = true;
        updateVoiceSelectTone();
        refreshIpaForAccent(selectedVoiceAccent());
        return true;
      };

      const rememberCurrentSpaceWVoice = () => {
        if (!voiceSelect) {
          return;
        }
        const record = selectedVoiceCacheRecord();
        if (!record.value) {
          return;
        }
        currentSpaceWCache.voiceValue = record.value;
        currentSpaceWCache.voiceLabel = record.label;
        currentSpaceWCache.voiceApplied = true;
        currentSpaceWCache.voiceKey = spaceWGlobalVoiceStorageKey();
        writeGlobalSpaceWVoiceRecord(record);
        void syncSpaceWVoicePreferenceToServer(record);
      };

      const spaceWSavedSummary = (record = null) => {
        const savedAt = clean(record && (record.savedAt || record.updatedAt));
        if (!savedAt) {
          return "Saved progress found.";
        }
        const date = new Date(savedAt);
        if (!Number.isFinite(date.getTime())) {
          return "Saved progress found.";
        }
        return `Saved progress from ${date.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })}.`;
      };

      const spaceWSavedStartIndex = (record = null) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const recordIndex = record && Number.isFinite(Number(record.nodeIndex)) ? Number(record.nodeIndex) : 0;
        return Math.max(0, Math.floor(Number(state.index ?? state.nodeIndex ?? recordIndex) || 0));
      };

      const spaceWSavedProgressAllowsTrainReview = (record = null, rootNodes = pendingLessonNodes) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const rootCount = Math.max(0, Array.isArray(rootNodes) ? rootNodes.length : 0);
        if (!rootCount) {
          return false;
        }
        return true;
        if (state.lessonCompletionSent || state.reviewFinished) {
          return true;
        }
        const savedIndex = Math.max(0, Math.floor(Number(state.index ?? state.nodeIndex ?? record?.nodeIndex ?? 0) || 0));
        const savedRootCount = Math.max(
          1,
          Math.floor(Number(state.spaceWTrainModeRootCount) || 0) || rootCount,
        );
        return savedIndex >= Math.max(0, Math.min(rootCount, savedRootCount) - 1);
      };

      const pendingSpaceWHasTrainModeNodes = () => Boolean(
        Array.isArray(pendingLessonNodes) &&
        pendingLessonNodes.length &&
        collectSpaceWTrainModeNodesFrom(pendingLessonNodes).length
      );

      const updateSpaceWReviewButton = () => {
        const navigation = resolveSpaceRunNavigation(currentSpaceWCache && currentSpaceWCache.savedProgress, "Space_W");
        const hasSaved = Boolean(navigation.resumeAvailable);
        if (loadReviewButton) {
          loadReviewButton.hidden = !hasSaved;
          loadReviewButton.disabled = !hasSaved;
          loadReviewButton.textContent = "Continue Previous";
        }
        const canTrainReview = Boolean(
          pendingLessonNodes.length &&
          pendingSpaceWHasTrainModeNodes() &&
          spaceWSavedProgressAllowsTrainReview(currentSpaceWCache.savedProgress, pendingLessonNodes)
        );
        if (loadReviewTrainButton) {
          loadReviewTrainButton.hidden = !canTrainReview;
          loadReviewTrainButton.disabled = !canTrainReview;
          loadReviewTrainButton.textContent = "Review Train";
          loadReviewTrainButton.title = canTrainReview
            ? "Bỏ qua học root từ đầu và vào vòng ôn ngẫu nhiên root + train nodes."
            : "Hoàn thành phần root của file này một lần để mở Review Train.";
        }
        if (typeof window.__ftSyncLessonEntryGateActions === "function") window.__ftSyncLessonEntryGateActions();
      };

      const configureSpaceWCache = (payload = {}, nodes = []) => {
        const identity = spaceWIdentityFor(payload, nodes);
        const progressKey = spaceWStorageKey(SPACE_W_PROGRESS_PREFIX, identity);
        const legacyIdentity = legacySpaceWIdentityFor(payload, nodes);
        const voiceKey = spaceWGlobalVoiceStorageKey();
        const legacyVoiceKey = spaceWStorageKey(SPACE_W_VOICE_PREFIX, identity);
        let savedProgress = readSpaceWJson(progressKey);
        if (!savedProgress && legacyIdentity !== identity) {
          savedProgress = readSpaceWJson(spaceWStorageKey(SPACE_W_PROGRESS_PREFIX, legacyIdentity));
          if (savedProgress) writeSpaceWJson(progressKey, { ...savedProgress, identity });
        }
        const preferredVoice = normalizeSpaceWVoiceRecord(spaceWVoicePreference);
        const legacyVoice = normalizeSpaceWVoiceRecord(readSpaceWJson(legacyVoiceKey));
        const savedVoice = readGlobalSpaceWVoiceRecord() ||
          (preferredVoice.value ? preferredVoice : null) ||
          (legacyVoice.value ? legacyVoice : null) ||
          defaultSpaceWVoiceRecord();
        currentSpaceWCache = {
          identity,
          progressKey,
          voiceKey,
          voiceValue: clean(savedVoice && savedVoice.value),
          voiceLabel: clean(savedVoice && savedVoice.label),
          voiceApplied: false,
          savedProgress: savedProgress && savedProgress.state ? savedProgress : null,
          serverPayload: null,
          serverEtag: "",
          serverProgressPromise: null,
          serverProgressResult: null,
          serverProgressSettled: false,
          vocabScanPromise: null,
        };
        updateSpaceWReviewButton();
        return currentSpaceWCache;
      };

      // Added 2026-07-20: guidance-tree edits create a new Space_Q progress identity.
      const compactQuestionGuidanceForHash = (value = null) => {
        if (Array.isArray(value)) {
          return value.map(compactQuestionGuidanceForHash).filter(Boolean);
        }
        if (!value || typeof value !== "object") {
          return null;
        }
        return {
          text: preserveQuestionText(value.text || value.title || value.main || ""),
          question: preserveQuestionText(value.question || ""),
          answer: preserveQuestionText(value.answer || ""),
          children: compactQuestionGuidanceForHash(value.children || value.items || []),
        };
      };

      const compactQuestionNodeForHash = (node = {}) => ({
        id: clean(node.id || node.key || ""),
        root: preserveQuestionText(node.root || ""),
        audio: clean((questionCardData(node, "audio") || {}).url || ""),
        picture: clean((questionCardData(node, "picture") || {}).url || ""),
        questions: Array.isArray(questionCardData(node, "questions"))
          ? questionCardData(node, "questions").map((item) => ({
            q: preserveQuestionText(item && item.question),
            a: preserveQuestionText(item && item.answer),
            type: clean(item && item.type),
            guidance: compactQuestionGuidanceForHash(item && item.guidance_tree),
          }))
          : [],
      });

      const legacyQuestionProgressIdentityFor = (payload = {}, nodes = []) => {
        const compactNodes = (Array.isArray(nodes) ? nodes : []).map(compactQuestionNodeForHash);
        const contentHash = hashSpaceWText(JSON.stringify({
          title: clean(payload.title || payload.name || ""),
          order: clean(payload.order || ""),
          nodes: compactNodes,
        }));
        const sourceKind = clean(currentLessonSource.source || currentLessonSource.kind || "local");
        const sourceId = clean(currentLessonSource.path || currentLessonSource.name || currentLessonSource.title || payload.title || payload.name || "space-q");
        const sourceHash = hashSpaceWText(`${sourceKind}:${sourceId}`);
        return `${sourceHash}:${contentHash}`;
      };

      const questionProgressIdentityFor = (payload = {}, nodes = []) => {
        const sourceLessonId = clean(currentLessonSource && (currentLessonSource.lesson_id || currentLessonSource.file_id) || "");
        return (sourceLessonId.toLowerCase().startsWith("ftg-lesson-") ? sourceLessonId : "")
          || stableLessonIdFor(payload)
          || legacyQuestionProgressIdentityFor(payload, nodes);
      };

      const normalizeQuestionProgressRecord = (record = null) => {
        if (!record || typeof record !== "object") {
          return null;
        }
        const state = record.state && typeof record.state === "object" ? record.state : null;
        if (!state) {
          return null;
        }
        const reviewing = Boolean(record.reviewing || record.reviewRun || state.reviewing || state.reviewRun);
        const activeRun = Boolean(record.activeRun || record.active_run || state.activeRun || state.active_run);
        const runId = clean(record.runId || record.run_id || state.runId || state.run_id || "");
        const completedRuns = Math.max(0, Math.floor(Number(record.completedRuns ?? record.completed_runs ?? state.completedRuns ?? state.completed_runs ?? 0) || 0));
        return {
          version: 1,
          identity: clean(record.identity || state.identity || ""),
          savedAt: clean(record.savedAt || state.savedAt || state.updatedAt || ""),
          title: clean(record.title || state.title || "Space_Q"),
          nodeIndex: Math.max(0, Math.floor(Number(record.nodeIndex ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number(record.nodeCount ?? state.nodeCount ?? 0) || 0)),
          activeRun,
          runId,
          complete: Boolean(!activeRun && (record.complete || record.completed || record.lessonComplete || state.complete || state.lessonComplete)),
          completedRuns,
          completed_runs: completedRuns,
          reviewing,
          reviewRun: reviewing,
          state: {
            ...state,
            activeRun,
            active_run: activeRun,
            runId,
            run_id: runId,
            completedRuns,
            completed_runs: completedRuns,
            reviewing,
            reviewRun: reviewing,
          },
        };
      };

      const questionSavedSummary = (record = null) => {
        const savedAt = clean(record && (record.savedAt || record.updatedAt));
        if (!savedAt) {
          return "Saved Space_Q progress found.";
        }
        const date = new Date(savedAt);
        if (!Number.isFinite(date.getTime())) {
          return "Saved Space_Q progress found.";
        }
        return `Saved Space_Q progress from ${date.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })}.`;
      };

      const questionSavedStartIndex = (record = null) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const recordIndex = record && Number.isFinite(Number(record.nodeIndex)) ? Number(record.nodeIndex) : 0;
        return Math.max(0, Math.floor(Number(state.currentIndex ?? state.nodeIndex ?? recordIndex) || 0));
      };

      const configureQuestionProgressCache = (payload = {}, nodes = []) => {
        const identity = questionProgressIdentityFor(payload, nodes);
        const progressKey = spaceWStorageKey(SPACE_Q_PROGRESS_PREFIX, identity);
        const legacyIdentity = legacyQuestionProgressIdentityFor(payload, nodes);
        let savedProgress = normalizeQuestionProgressRecord(readSpaceWJson(progressKey));
        if (!savedProgress && legacyIdentity !== identity) {
          savedProgress = normalizeQuestionProgressRecord(readSpaceWJson(spaceWStorageKey(SPACE_Q_PROGRESS_PREFIX, legacyIdentity)));
          if (savedProgress) writeSpaceWJson(progressKey, { ...savedProgress, identity });
        }
        currentQuestionProgressCache = {
          identity,
          progressKey,
          savedProgress: savedProgress && savedProgress.state ? savedProgress : null,
          serverPayload: null,
          serverEtag: "",
        };
        updateQuestionProgressButtons();
        return currentQuestionProgressCache;
      };

      const updateQuestionProgressButtons = () => {
        const navigation = resolveSpaceRunNavigation(currentQuestionProgressCache && currentQuestionProgressCache.savedProgress, "Space_Q");
        const hasQuestionSaved = Boolean(pendingQuestionPayload && navigation.resumeAvailable);
        const hasQuestionHistory = Boolean(pendingQuestionPayload && !currentQuestionProgressCache?.savedProgress && navigationForLoadedRecord(null, "Space_Q").lifetimeComplete);
        if (loadStartButton && pendingQuestionPayload) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = hasQuestionHistory || currentQuestionProgressCache?.savedProgress ? "New Study" : "Open New Run";
        }
        if (loadReviewButton && pendingQuestionPayload) {
          loadReviewButton.hidden = !hasQuestionSaved;
          loadReviewButton.disabled = !hasQuestionSaved;
          loadReviewButton.textContent = "Continue Previous";
        }
        if (loadReviewTrainButton && pendingQuestionPayload) {
          loadReviewTrainButton.hidden = true;
          loadReviewTrainButton.disabled = true;
        }
        if (typeof window.__ftSyncLessonEntryGateActions === "function") window.__ftSyncLessonEntryGateActions();
      };

      const resetQuestionProgressCache = () => {
        if (questionProgressSaveTimer) {
          window.clearTimeout(questionProgressSaveTimer);
          questionProgressSaveTimer = 0;
        }
        if (questionServerProgressSaveTimer) {
          window.clearTimeout(questionServerProgressSaveTimer);
          questionServerProgressSaveTimer = 0;
        }
        pendingQuestionServerProgressRecord = null;
        questionProgressLastSemanticSignature = "";
        currentQuestionProgressCache = { identity: "", progressKey: "", savedProgress: null, serverPayload: null, serverEtag: "" };
        pendingQuestionResumeState = null;
        updateQuestionProgressButtons();
      };

      const currentQuestionServerPath = () => clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");

      // Added 2026-08-03: patch Lesson Vault and Space Task by canonical ID plus every visible/effective path.
      const currentQuestionProgressPaths = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const lessonId = clean(
          source.lesson_id || source.file_id || source.identity
          || state.lesson_id || state.file_id
          || lessonSource.lesson_id || lessonSource.file_id
          || currentLessonStudyId(),
        );
        return Array.from(new Set([
          lessonId.toLowerCase().startsWith("ftg-lesson-") ? `space:space_q:id:${lessonId.toLowerCase()}` : "",
          currentLessonStudyPath(),
          currentQuestionServerPath(),
          currentLessonSource && currentLessonSource.path,
          currentLessonSource && currentLessonSource.effective_path,
          currentLessonSource && currentLessonSource.link_target,
          currentLessonSource && currentLessonSource.linked_path,
          lessonSource.path,
          lessonSource.effective_path,
          lessonSource.link_target,
          lessonSource.linked_path,
        ].map((value) => normalizeServerPathValue(value || "")).filter(Boolean)));
      };

      const canUseQuestionProgressServer = () => Boolean(
        authToken &&
        currentQuestionProgressCache &&
        currentQuestionProgressCache.identity
      );

      const questionServerProgressPayload = (record = {}, action = "") => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const linkIdentity = linkedLessonProgressIdentity(record, currentQuestionProgressCache.identity);
        return {
          action: clean(action),
          path: currentQuestionServerPath(),
          identity: clean((record && record.identity) || currentQuestionProgressCache.identity),
          ...linkIdentity,
          title: clean((record && record.title) || state.title || currentLessonSource.title || currentLessonSource.name || "Space_Q"),
          nodeIndex: Math.max(0, Math.floor(Number((record && record.nodeIndex) ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number((record && record.nodeCount) ?? state.nodeCount ?? questionNodes.length ?? 0) || 0)),
          activeRun: Boolean((record && (record.activeRun || record.active_run)) || state.activeRun || state.active_run),
          runId: clean((record && (record.runId || record.run_id)) || state.runId || state.run_id || ""),
          expectedRunId: clean((record && (record.runId || record.run_id)) || state.runId || state.run_id || ""),
          baseRevision: Math.max(0, Math.floor(Number((record && (record._serverRevision || record.serverRevision || record.server_revision)) || 0) || 0)),
          syncOperationId: clean((record && (record.syncOperationId || record.sync_operation_id)) || state.syncOperationId || state.sync_operation_id || ""),
          reviewing: Boolean((record && (record.reviewing || record.reviewRun)) || state.reviewing || state.reviewRun),
          reviewRun: Boolean((record && (record.reviewing || record.reviewRun)) || state.reviewing || state.reviewRun),
          savedAt: clean((record && record.savedAt) || state.savedAt || new Date().toISOString()),
          state,
        };
      };

      const mergeQuestionServerProgressRecord = (record = null) => {
        const localRecord = currentQuestionProgressCache && currentQuestionProgressCache.savedProgress && typeof currentQuestionProgressCache.savedProgress === "object"
          ? currentQuestionProgressCache.savedProgress
          : null;
        const canonicalRecord = record && record.state && typeof record.state === "object"
          ? record
          : (record && localRecord && localRecord.state && typeof localRecord.state === "object" ? { ...localRecord, ...record, state: { ...localRecord.state } } : record);
        const normalized = normalizeQuestionProgressRecord(canonicalRecord);
        if (!normalized) {
          return null;
        }
        if (normalized.identity && currentQuestionProgressCache.identity && normalized.identity !== currentQuestionProgressCache.identity) {
          return currentQuestionProgressCache.savedProgress || null;
        }
        if (shouldKeepPendingLocalProgress(currentQuestionProgressCache.savedProgress, normalized)) {
          scheduleProgressOutboxDrain(150);
          return currentQuestionProgressCache.savedProgress;
        }
        normalized.pendingServerSync = false;
        currentQuestionProgressCache.savedProgress = normalized;
        if (currentQuestionProgressCache.progressKey) {
          writeSpaceWJson(currentQuestionProgressCache.progressKey, normalized);
        }
        updateQuestionProgressButtons();
        return normalized;
      };

      const refreshQuestionServerProgress = async () => {
        if (!canUseQuestionProgressServer()) {
          return currentQuestionProgressCache.savedProgress || null;
        }
        const query = new URLSearchParams();
        const pathValue = currentQuestionServerPath();
        if (pathValue) {
          query.set("path", pathValue);
        }
        query.set("identity", currentQuestionProgressCache.identity);
        try {
          const cachedRow = currentQuestionProgressCache.serverPayload && clean(currentQuestionProgressCache.serverEtag || "")
            ? { payload: currentQuestionProgressCache.serverPayload, etag: currentQuestionProgressCache.serverEtag }
            : null;
          const result = await fetchProgressJsonFast(`/space-q/progress?${query.toString()}`, cachedRow);
          const payload = result && result.payload ? result.payload : {};
          const merged = mergeQuestionServerProgressRecord(payload.progress || null);
          currentQuestionProgressCache.serverPayload = payload;
          currentQuestionProgressCache.serverEtag = clean(result && result.etag || "");
          return merged || currentQuestionProgressCache.savedProgress || null;
        } catch (error) {
          return currentQuestionProgressCache.savedProgress || null;
        }
      };

      const sendQuestionServerProgress = async (record = null, action = "") => {
        if (!canUseQuestionProgressServer()) {
          return null;
        }
        const body = questionServerProgressPayload(record || currentQuestionProgressCache.savedProgress || {}, action);
        const outboxRow = enqueueProgressOutboxRequest("space_q", "/space-q/progress?client_source=offline_outbox&response=compact-v1", body, currentQuestionProgressCache.progressKey);
        let result;
        try {
          result = await fetchAuthJson("/space-q/progress?client_source=space_q_progress_save&response=compact-v1", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
        const payload = result && result.payload ? result.payload : {};
        if (typeof payload.progress_save_ms === "number") {
          console.debug("[Space_Q progress] server save", payload.progress_save_ms, "ms");
        }
        if (typeof applyVocabularyCompletionDeltaToLocalPreview === "function") {
          applyVocabularyCompletionDeltaToLocalPreview(payload, currentAuthUsername);
        }
        if (payload.progress) {
          mergeQuestionServerProgressRecord(payload.progress);
        }
        currentQuestionProgressCache.serverPayload = null;
        currentQuestionProgressCache.serverEtag = "";
        return payload;
      };

      const clearQuestionServerProgress = async (record = null) => {
        if (!canUseQuestionProgressServer()) {
          return null;
        }
        return await sendQuestionServerProgress(record || { identity: currentQuestionProgressCache.identity, state: {} }, "clear");
      };

      const queueQuestionServerProgressSync = (record = null, delayMs = 900) => {
        if (!record || !canUseQuestionProgressServer()) {
          return;
        }
        pendingQuestionServerProgressRecord = record;
        if (questionServerProgressSaveTimer) {
          window.clearTimeout(questionServerProgressSaveTimer);
        }
        questionServerProgressSaveTimer = window.setTimeout(async () => {
          questionServerProgressSaveTimer = 0;
          if (questionServerProgressSyncBusy || !pendingQuestionServerProgressRecord) {
            if (pendingQuestionServerProgressRecord) {
              queueQuestionServerProgressSync(pendingQuestionServerProgressRecord, 900);
            }
            return;
          }
          const nextRecord = pendingQuestionServerProgressRecord;
          pendingQuestionServerProgressRecord = null;
          questionServerProgressSyncBusy = true;
          try {
            await sendQuestionServerProgress(nextRecord);
          } catch (error) {
            if (!(error && error.progressOutboxQueued)) {
              pendingQuestionServerProgressRecord = nextRecord;
            } else {
              scheduleProgressOutboxDrain(progressOutboxRetryMs);
            }
          } finally {
            questionServerProgressSyncBusy = false;
            if (pendingQuestionServerProgressRecord) {
              queueQuestionServerProgressSync(pendingQuestionServerProgressRecord, 1500);
            }
          }
        }, Math.max(100, Number(delayMs) || 900));
      };

      const clearSavedQuestionProgress = (syncServer = true) => {
        const clearedRecord = currentQuestionProgressCache && currentQuestionProgressCache.savedProgress;
        if (questionProgressSaveTimer) {
          window.clearTimeout(questionProgressSaveTimer);
          questionProgressSaveTimer = 0;
        }
        if (questionServerProgressSaveTimer) {
          window.clearTimeout(questionServerProgressSaveTimer);
          questionServerProgressSaveTimer = 0;
        }
        pendingQuestionServerProgressRecord = null;
        if (currentQuestionProgressCache && currentQuestionProgressCache.progressKey) {
          removeSpaceWJson(currentQuestionProgressCache.progressKey);
          currentQuestionProgressCache.savedProgress = null;
        }
        updateQuestionProgressButtons();
        if (syncServer) {
          return clearQuestionServerProgress(clearedRecord);
        }
        return Promise.resolve(null);
      };

      const normalizeQuestionResumeState = (state = {}, nodeCount = 0) => {
        if (!state || typeof state !== "object" || !nodeCount) {
          return null;
        }
        const maxIndex = Math.max(0, nodeCount - 1);
        const currentIndex = Math.max(0, Math.min(maxIndex, Math.floor(Number(state.currentIndex ?? state.nodeIndex ?? 0) || 0)));
        const queue = Array.isArray(state.queue)
          ? state.queue
            .map((item) => Math.floor(Number(item) || 0))
            .filter((item) => item >= 0 && item < nodeCount)
          : [];
        const questionOrder = Array.isArray(state.questionOrder)
          ? state.questionOrder
            .map((item) => Math.floor(Number(item)))
            .filter((item) => Number.isFinite(item) && item >= 0)
          : [];
        return {
          currentIndex,
          queue,
          nodePointer: Math.max(1, Math.min(nodeCount, Math.floor(Number(state.nodePointer || currentIndex + 1) || currentIndex + 1))),
          questionIndex: Math.max(0, Math.floor(Number(state.questionIndex || 0) || 0)),
          questionOrder,
          runId: clean(state.runId || state.run_id || ""),
          wrongAttempts: Math.max(0, Math.floor(Number(state.wrongAttempts || 0) || 0)),
          reviewing: Boolean(state.reviewing || state.reviewRun),
          reviewRun: Boolean(state.reviewing || state.reviewRun),
        };
      };

      const compactParagraphNodeForHash = (node = {}) => ({
        id: clean(node.id || node.key || ""),
        title: clean(node.title || node.name || ""),
        children: Array.isArray(node.children)
          ? node.children.map((child) => ({
            text: preserveQuestionText(child && child.text),
            meaning: preserveQuestionText(child && child.meaning),
          }))
          : [],
      });

      const legacyParagraphProgressIdentityFor = (payload = {}, nodes = []) => {
        const compactNodes = (Array.isArray(nodes) ? nodes : []).map(compactParagraphNodeForHash);
        const contentHash = hashSpaceWText(JSON.stringify({
          title: clean(payload.title || payload.name || ""),
          nodes: compactNodes,
        }));
        const sourceKind = clean(currentLessonSource.source || currentLessonSource.kind || "local");
        const sourceId = clean(currentLessonSource.path || currentLessonSource.name || currentLessonSource.title || payload.title || payload.name || "space-p");
        return `${hashSpaceWText(`${sourceKind}:${sourceId}`)}:${contentHash}`;
      };

      const paragraphProgressIdentityFor = (payload = {}, nodes = []) => stableLessonIdFor(payload) || legacyParagraphProgressIdentityFor(payload, nodes);

      const normalizeParagraphProgressRecord = (record = null) => {
        if (!record || typeof record !== "object") {
          return null;
        }
        const state = record.state && typeof record.state === "object" ? record.state : null;
        if (!state) {
          return null;
        }
        const reviewing = Boolean(record.reviewing || record.reviewRun || state.reviewing || state.reviewRun);
        const activeRun = Boolean(record.activeRun || record.active_run || state.activeRun || state.active_run);
        const completedRuns = Math.max(0, Math.floor(Number(record.completedRuns ?? record.completed_runs ?? state.completedRuns ?? state.completed_runs ?? 0) || 0));
        return {
          version: 1,
          identity: clean(record.identity || state.identity || ""),
          path: clean(record.path || state.path || (state.lessonSource && state.lessonSource.path) || ""),
          savedAt: clean(record.savedAt || state.savedAt || state.updatedAt || ""),
          title: clean(record.title || state.title || "Space_P"),
          nodeIndex: Math.max(0, Math.floor(Number(record.nodeIndex ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number(record.nodeCount ?? state.nodeCount ?? state.totalNodes ?? 0) || 0)),
          activeRun,
          reviewing,
          reviewRun: reviewing,
          complete: Boolean(!activeRun && (record.complete || record.lessonComplete || state.complete || state.lessonComplete)),
          lessonComplete: Boolean(!activeRun && (record.lessonComplete || record.complete || state.lessonComplete || state.complete)),
          completedRuns,
          completed_runs: completedRuns,
          runId: clean(record.runId || record.run_id || state.runId || state.run_id || ""),
          state: { ...state, reviewing, reviewRun: reviewing },
        };
      };

      const paragraphSavedSummary = (record = null) => {
        const savedAt = clean(record && (record.savedAt || record.updatedAt));
        if (!savedAt) {
          return "Saved paragraph progress found.";
        }
        const date = new Date(savedAt);
        if (!Number.isFinite(date.getTime())) {
          return "Saved paragraph progress found.";
        }
        return `Saved paragraph progress from ${date.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })}.`;
      };

      const paragraphSavedStartIndex = (record = null) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const recordIndex = record && Number.isFinite(Number(record.nodeIndex)) ? Number(record.nodeIndex) : 0;
        return Math.max(0, Math.floor(Number(state.currentIndex ?? state.nodeIndex ?? recordIndex) || 0));
      };

      const paragraphSavedChildIndex = (record = null) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        return Math.max(0, Math.floor(Number(state.childIndex || 0) || 0));
      };

      const updateParagraphProgressButtons = () => {
        const paragraphSpace = isSpaceLPayload(pendingParagraphPayload) ? "Space_L" : (isSpaceSPayload(pendingParagraphPayload) ? "Space_S" : "Space_P");
        const navigation = resolveSpaceRunNavigation(currentParagraphProgressCache && currentParagraphProgressCache.savedProgress, paragraphSpace);
        const hasSaved = Boolean(pendingParagraphPayload && navigation.resumeAvailable);
        const hasHistory = Boolean(pendingParagraphPayload && !currentParagraphProgressCache?.savedProgress && navigationForLoadedRecord(null, paragraphSpace).lifetimeComplete);
        if (loadStartButton && pendingParagraphPayload) {
          loadStartButton.hidden = !(currentParagraphProgressCache && currentParagraphProgressCache.savedProgress) && !hasHistory;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "New Study";
        }
        if (loadReviewButton && pendingParagraphPayload) {
          loadReviewButton.hidden = !hasSaved;
          loadReviewButton.disabled = !hasSaved;
          loadReviewButton.textContent = "Continue Previous";
        }
        if (loadReviewTrainButton && pendingParagraphPayload) {
          loadReviewTrainButton.hidden = true;
          loadReviewTrainButton.disabled = true;
        }
        if (typeof window.__ftSyncLessonEntryGateActions === "function") window.__ftSyncLessonEntryGateActions();
      };

      const configureParagraphProgressCache = (payload = {}, nodes = []) => {
        if (paragraphProgressSaveTimer) {
          window.clearTimeout(paragraphProgressSaveTimer);
          paragraphProgressSaveTimer = 0;
        }
        if (paragraphServerProgressSaveTimer) {
          window.clearTimeout(paragraphServerProgressSaveTimer);
          paragraphServerProgressSaveTimer = 0;
        }
        pendingParagraphServerProgressRecord = null;
        paragraphProgressLastSemanticSignature = "";
        const identity = paragraphProgressIdentityFor(payload, nodes);
        const progressPrefix = isSpaceLPayload(payload)
          ? `${SPACE_P_PROGRESS_PREFIX}_space_l`
          : (isSpaceSPayload(payload) ? `${SPACE_P_PROGRESS_PREFIX}_space_s` : SPACE_P_PROGRESS_PREFIX);
        const progressKey = spaceWStorageKey(progressPrefix, identity);
        const legacyIdentity = legacyParagraphProgressIdentityFor(payload, nodes);
        let savedProgress = normalizeParagraphProgressRecord(readSpaceWJson(progressKey));
        if (!savedProgress && legacyIdentity !== identity) {
          savedProgress = normalizeParagraphProgressRecord(readSpaceWJson(spaceWStorageKey(progressPrefix, legacyIdentity)));
          if (savedProgress) writeSpaceWJson(progressKey, { ...savedProgress, identity });
        }
        currentParagraphProgressCache = {
          identity,
          progressKey,
          savedProgress: savedProgress && savedProgress.state ? savedProgress : null,
          serverPayload: null,
          serverEtag: "",
        };
        updateParagraphProgressButtons();
        return currentParagraphProgressCache;
      };

      const resetParagraphProgressCache = () => {
        if (paragraphProgressSaveTimer) {
          window.clearTimeout(paragraphProgressSaveTimer);
          paragraphProgressSaveTimer = 0;
        }
        if (paragraphServerProgressSaveTimer) {
          window.clearTimeout(paragraphServerProgressSaveTimer);
          paragraphServerProgressSaveTimer = 0;
        }
        pendingParagraphServerProgressRecord = null;
        paragraphProgressLastSemanticSignature = "";
        currentParagraphProgressCache = { identity: "", progressKey: "", savedProgress: null, serverPayload: null, serverEtag: "" };
        updateParagraphProgressButtons();
      };

      const currentParagraphServerPath = () => clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");

      const paragraphServerPathFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : source;
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const sourceKind = clean(lessonSource.source || source.source || "").toLowerCase();
        const rawPath = clean(source.path || state.path || (sourceKind === "server" ? lessonSource.path : "") || "");
        return rawPath.replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
      };

      const currentParagraphProgressPaths = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        return [
          currentLessonStudyPath(),
          currentParagraphServerPath(),
          paragraphServerPathFromRecord(record),
          source.path,
          state.path,
          lessonSource.path,
          currentLessonSource && currentLessonSource.linked_path,
          currentLessonSource && currentLessonSource.effective_path,
          currentLessonSource && currentLessonSource.link_target,
          lessonSource.linked_path,
          lessonSource.effective_path,
          lessonSource.link_target,
        ].map((path) => normalizeServerPathValue(path)).filter(Boolean);
      };

      const canUseParagraphProgressServer = () => Boolean(
        authToken &&
        currentParagraphProgressCache &&
        currentParagraphProgressCache.identity
      );

      const paragraphServerProgressPayload = (record = {}, action = "") => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const pathValue = paragraphServerPathFromRecord(record) || currentParagraphServerPath();
        const linkIdentity = linkedLessonProgressIdentity(record, currentParagraphProgressCache.identity);
        return {
          action: clean(action),
          path: pathValue,
          identity: clean((record && record.identity) || currentParagraphProgressCache.identity),
          ...linkIdentity,
          space: isSpaceLPayload() ? "Space_L" : (isSpaceSPayload() ? "Space_S" : "Space_P"),
          title: clean((record && record.title) || state.title || currentLessonSource.title || currentLessonSource.name || (isSpaceLPayload() ? "Space_L" : (isSpaceSPayload() ? "Space_S" : "Space_P"))),
          nodeIndex: Math.max(0, Math.floor(Number((record && record.nodeIndex) ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number((record && record.nodeCount) ?? state.nodeCount ?? state.totalNodes ?? paragraphNodes.length ?? 0) || 0)),
          reviewing: Boolean((record && (record.reviewing || record.reviewRun)) || state.reviewing || state.reviewRun),
          reviewRun: Boolean((record && (record.reviewing || record.reviewRun)) || state.reviewing || state.reviewRun),
          savedAt: clean((record && record.savedAt) || state.savedAt || new Date().toISOString()),
          syncOperationId: clean((record && (record.syncOperationId || record.sync_operation_id)) || state.syncOperationId || state.sync_operation_id || ""),
          expectedRunId: clean((record && (record.runId || record.run_id)) || state.runId || state.run_id || ""),
          baseRevision: Math.max(0, Math.floor(Number((record && (record._serverRevision || record.serverRevision || record.server_revision)) || 0) || 0)),
          state,
        };
      };

      const mergeParagraphServerProgressRecord = (record = null) => {
        const localRecord = currentParagraphProgressCache && currentParagraphProgressCache.savedProgress && typeof currentParagraphProgressCache.savedProgress === "object"
          ? currentParagraphProgressCache.savedProgress
          : null;
        const canonicalRecord = record && record.state && typeof record.state === "object"
          ? record
          : (record && localRecord && localRecord.state && typeof localRecord.state === "object" ? { ...localRecord, ...record, state: { ...localRecord.state } } : record);
        const normalized = normalizeParagraphProgressRecord(canonicalRecord);
        if (!normalized) {
          return null;
        }
        if (normalized.identity && currentParagraphProgressCache.identity && normalized.identity !== currentParagraphProgressCache.identity) {
          return currentParagraphProgressCache.savedProgress || null;
        }
        if (shouldKeepPendingLocalProgress(currentParagraphProgressCache.savedProgress, normalized)) {
          scheduleProgressOutboxDrain(150);
          return currentParagraphProgressCache.savedProgress;
        }
        normalized.pendingServerSync = false;
        currentParagraphProgressCache.savedProgress = normalized;
        if (currentParagraphProgressCache.progressKey) {
          writeSpaceWJson(currentParagraphProgressCache.progressKey, normalized);
        }
        updateParagraphProgressButtons();
        return normalized;
      };

      const refreshParagraphServerProgress = async () => {
        if (!canUseParagraphProgressServer()) {
          return currentParagraphProgressCache.savedProgress || null;
        }
        const query = new URLSearchParams();
        const pathValue = currentParagraphServerPath();
        if (pathValue) {
          query.set("path", pathValue);
        }
        query.set("identity", currentParagraphProgressCache.identity);
        try {
          const cachedRow = currentParagraphProgressCache.serverPayload && clean(currentParagraphProgressCache.serverEtag || "")
            ? { payload: currentParagraphProgressCache.serverPayload, etag: currentParagraphProgressCache.serverEtag }
            : null;
          const result = await fetchProgressJsonFast(`/space-p/progress?${query.toString()}`, cachedRow);
          const payload = result && result.payload ? result.payload : {};
          const merged = mergeParagraphServerProgressRecord(payload.progress || null);
          currentParagraphProgressCache.serverPayload = payload;
          currentParagraphProgressCache.serverEtag = clean(result && result.etag || "");
          return merged || currentParagraphProgressCache.savedProgress || null;
        } catch (error) {
          return currentParagraphProgressCache.savedProgress || null;
        }
      };

      const sendParagraphServerProgress = async (record = null, action = "") => {
        if (!canUseParagraphProgressServer()) {
          return null;
        }
        const body = paragraphServerProgressPayload(record || currentParagraphProgressCache.savedProgress || {}, action);
        const outboxRow = enqueueProgressOutboxRequest("space_p", "/space-p/progress?client_source=offline_outbox&response=compact-v1", body, currentParagraphProgressCache.progressKey);
        let result;
        try {
          result = await fetchAuthJson("/space-p/progress?client_source=space_p_progress_save&response=compact-v1", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
        const payload = result && result.payload ? result.payload : {};
        if (typeof applyVocabularyCompletionDeltaToLocalPreview === "function") {
          applyVocabularyCompletionDeltaToLocalPreview(payload, currentAuthUsername);
        }
        let progressOverride = null;
        if (payload.progress) {
          mergeParagraphServerProgressRecord(payload.progress);
          progressOverride = paragraphProgressOverrideFromRecord(payload.progress);
          if (progressOverride) {
            setLessonProgressOverride(currentParagraphProgressPaths(payload.progress || body), progressOverride, 45000);
          }
        }
        clearLessonProgressDisplayCaches(currentParagraphProgressPaths(payload.progress || body), (progressOverride && progressOverride.space) || "Space_P");
        currentParagraphProgressCache.serverPayload = null;
        currentParagraphProgressCache.serverEtag = "";
        return payload;
      };

      const clearParagraphServerProgress = async (record = null) => {
        if (!canUseParagraphProgressServer()) {
          return null;
        }
        return await sendParagraphServerProgress(record || { identity: currentParagraphProgressCache.identity, state: {} }, "clear");
      };

      const queueParagraphServerProgressSync = (record = null, delayMs = 900) => {
        if (!record || !canUseParagraphProgressServer()) {
          return;
        }
        pendingParagraphServerProgressRecord = record;
        if (paragraphServerProgressSaveTimer) {
          window.clearTimeout(paragraphServerProgressSaveTimer);
        }
        paragraphServerProgressSaveTimer = window.setTimeout(async () => {
          paragraphServerProgressSaveTimer = 0;
          if (paragraphServerProgressSyncBusy || !pendingParagraphServerProgressRecord) {
            if (pendingParagraphServerProgressRecord) {
              queueParagraphServerProgressSync(pendingParagraphServerProgressRecord, 900);
            }
            return;
          }
          const nextRecord = pendingParagraphServerProgressRecord;
          pendingParagraphServerProgressRecord = null;
          paragraphServerProgressSyncBusy = true;
          try {
            await sendParagraphServerProgress(nextRecord);
          } catch (error) {
            if (!(error && error.progressOutboxQueued)) {
              pendingParagraphServerProgressRecord = nextRecord;
            } else {
              scheduleProgressOutboxDrain(progressOutboxRetryMs);
            }
          } finally {
            paragraphServerProgressSyncBusy = false;
            if (pendingParagraphServerProgressRecord) {
              queueParagraphServerProgressSync(pendingParagraphServerProgressRecord, 1500);
            }
          }
        }, Math.max(100, Number(delayMs) || 900));
      };

      const normalizeParagraphResumeState = (state = {}, payload = pendingParagraphPayload) => {
        if (!state || typeof state !== "object") {
          return null;
        }
        const normalized = normalizeParagraphPayload(payload || {});
        const totalNodes = normalized.nodes.length;
        if (!totalNodes) {
          return null;
        }
        const nodeIndex = Math.max(0, Math.min(totalNodes - 1, Math.floor(Number(state.currentIndex ?? state.nodeIndex ?? 0) || 0)));
        const children = Array.isArray(normalized.nodes[nodeIndex] && normalized.nodes[nodeIndex].children) ? normalized.nodes[nodeIndex].children : [];
        const childIndex = Math.max(0, Math.min(Math.max(0, children.length - 1), Math.floor(Number(state.childIndex || 0) || 0)));
        const revealed = Array.isArray(state.revealed) ? state.revealed : [];
        const spaceLUnlockedTokens = Array.isArray(state.spaceLUnlockedTokens)
          ? state.spaceLUnlockedTokens
          : (Array.isArray(state.space_l_unlocked_tokens) ? state.space_l_unlocked_tokens : []);
        return {
          currentIndex: nodeIndex,
          nodeIndex,
          childIndex,
          reviewing: Boolean(state.reviewing || state.reviewRun),
          reviewRun: Boolean(state.reviewing || state.reviewRun),
          inputValue: String(state.inputValue ?? state.input ?? state.typedText ?? state.partialInput ?? "").slice(0, 12000),
          revealed: children.map((child, index) => {
            const maxWords = paragraphWordParts(child && child.text ? child.text : "").map((part) => paragraphWordKey(part.word)).filter(Boolean).length;
            return Math.max(0, Math.min(maxWords, Math.floor(Number(revealed[index] || 0) || 0)));
          }),
          hints: Array.isArray(state.hints) ? state.hints.map(clean).filter(Boolean) : [],
          spaceLUnlockedTokens: spaceLUnlockedTokens.map(clean).filter(Boolean),
          wrongTokenCount: Math.max(0, Math.floor(Number(state.wrongTokenCount || 0) || 0)),
          runId: clean(state.runId || state.run_id || ""),
        };
      };

      const paragraphCurrentSegmentComplete = () => {
        if (isSpaceSpeechPayload()) {
          return spaceSLastReadScore >= SPACE_S_PASS_SCORE;
        }
        const expected = currentParagraphWords();
        return Boolean(expected.length && Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0) >= expected.length);
      };

      const paragraphCompletedSegmentsForSnapshot = () => Math.min(
        paragraphTotalSegments(),
        paragraphCompletedSegments() + (paragraphCurrentSegmentComplete() ? 1 : 0),
      );

      const paragraphProgressSnapshot = () => {
        const totalSegments = paragraphTotalSegments();
        const completedSegments = paragraphCompletedSegmentsForSnapshot();
        const totalTokens = paragraphTotalTokens();
        const completedTokens = paragraphCompletedTokensForSnapshot();
        const currentNodeChildren = currentParagraphNode() && Array.isArray(currentParagraphNode().children) ? currentParagraphNode().children : [];
        const currentNodeDone = currentNodeChildren.length && paragraphChildIndex >= currentNodeChildren.length - 1 && paragraphCurrentSegmentComplete();
        const completedNodes = Math.min(paragraphNodes.length, paragraphNodeIndex + (currentNodeDone ? 1 : 0));
        const paragraphComplete = Boolean(
          (totalTokens && completedTokens >= totalTokens) ||
          (!totalTokens && totalSegments && completedSegments >= totalSegments) ||
          (!totalTokens && !totalSegments && paragraphNodes.length && completedNodes >= paragraphNodes.length)
        );
        return {
          identity: currentParagraphProgressCache.identity,
          runId: paragraphActiveRunId,
          title: clean(currentLessonSource.title || currentLessonSource.name || (isSpaceLPayload() ? "Space_L" : (isSpaceSPayload() ? "Space_S" : "Space_P"))),
          spaceMode: isSpaceLPayload() ? "space_l" : (isSpaceSPayload() ? "space_s" : "space_p"),
          reviewing: Boolean(paragraphReviewRunActive),
          reviewRun: Boolean(paragraphReviewRunActive),
          activeRun: Boolean(!paragraphReviewRunActive && !paragraphComplete),
          complete: paragraphComplete,
          lessonComplete: paragraphComplete,
          lessonSource: { ...(currentLessonSource || {}) },
          currentIndex: Math.max(0, Math.floor(Number(paragraphNodeIndex || 0) || 0)),
          nodeIndex: Math.max(0, Math.floor(Number(paragraphNodeIndex || 0) || 0)),
          nodeCount: paragraphNodes.length,
          childIndex: Math.max(0, Math.floor(Number(paragraphChildIndex || 0) || 0)),
          inputValue: paragraphEls && paragraphEls.input ? String(paragraphEls.input.value || "").slice(0, 12000) : "",
          revealed: paragraphRevealed.slice(),
          hints: Array.from(paragraphHints),
          spaceLUnlockedTokens: isSpaceLPayload() && spaceLUnlockedTokenKeys instanceof Set ? Array.from(spaceLUnlockedTokenKeys) : [],
          wrongTokenCount: Math.max(0, Math.floor(Number(paragraphWrongTokenCount || 0) || 0)),
          completedSegments,
          totalSegments,
          completedTokens,
          totalTokens,
          completedNodes,
          totalNodes: paragraphNodes.length,
          savedAt: new Date().toISOString(),
        };
      };

      // Added 2026-07-21: identical P/L/S callbacks share one local checkpoint instead of creating autosave churn.
      const paragraphProgressSemanticSignature = (snapshot = {}) => {
        const comparable = { ...(snapshot && typeof snapshot === "object" ? snapshot : {}) };
        delete comparable.savedAt;
        delete comparable.syncOperationId;
        return JSON.stringify(comparable);
      };

      const createParagraphProgressOperationId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `space-p-${window.crypto.randomUUID()}`;
        }
        return `space-p-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      };

      const canSaveParagraphProgress = () => Boolean(
        currentParagraphProgressCache &&
        currentParagraphProgressCache.progressKey &&
        paragraphModeActive &&
        paragraphPayload &&
        paragraphNodes.length &&
        loadGate.classList.contains("is-hidden")
      );

      const saveParagraphProgressNow = () => {
        if (paragraphProgressSaveTimer) {
          window.clearTimeout(paragraphProgressSaveTimer);
          paragraphProgressSaveTimer = 0;
        }
        if (!canSaveParagraphProgress()) {
          return false;
        }
        const snapshot = paragraphProgressSnapshot();
        const semanticSignature = paragraphProgressSemanticSignature(snapshot);
        if (
          semanticSignature === paragraphProgressLastSemanticSignature
          && currentParagraphProgressCache.savedProgress
          && currentParagraphProgressCache.savedProgress.state
        ) {
          return currentParagraphProgressCache.savedProgress;
        }
        snapshot.syncOperationId = createParagraphProgressOperationId();
        const record = {
          version: 1,
          identity: currentParagraphProgressCache.identity,
          runId: snapshot.runId,
          syncOperationId: snapshot.syncOperationId,
          savedAt: snapshot.savedAt,
          title: snapshot.title,
          nodeIndex: snapshot.currentIndex,
          nodeCount: paragraphNodes.length,
          activeRun: Boolean(snapshot.activeRun),
          reviewing: Boolean(snapshot.reviewing || snapshot.reviewRun),
          reviewRun: Boolean(snapshot.reviewing || snapshot.reviewRun),
          complete: Boolean(snapshot.complete),
          lessonComplete: Boolean(snapshot.lessonComplete),
          pendingServerSync: true,
          state: snapshot,
        };
        const ok = writeSpaceWJson(currentParagraphProgressCache.progressKey, record);
        if (ok) {
          paragraphProgressLastSemanticSignature = semanticSignature;
          currentParagraphProgressCache.savedProgress = record;
          updateParagraphProgressButtons();
          const progressOverride = paragraphProgressOverrideFromRecord(record);
          if (progressOverride) {
            const progressPaths = currentParagraphProgressPaths(record);
            setLessonProgressOverride(progressPaths, progressOverride, 45000);
            if (typeof rememberLessonVaultProgressPin === "function") {
              rememberLessonVaultProgressPin(progressPaths, progressOverride, 120000);
            }
            if (typeof pinVisibleLessonVaultProgressRing === "function") {
              pinVisibleLessonVaultProgressRing(progressPaths, progressOverride, { retryMs: 120 });
            }
            clearLessonProgressDisplayCaches(progressPaths, progressOverride.space || "Space_P");
          }
        }
        queueParagraphServerProgressSync(record, 0);
        return ok ? record : null;
      };

      const queueParagraphProgressSave = (delayMs = 250) => {
        if (!canSaveParagraphProgress()) {
          return;
        }
        if (paragraphProgressSaveTimer) {
          window.clearTimeout(paragraphProgressSaveTimer);
        }
        paragraphProgressSaveTimer = window.setTimeout(saveParagraphProgressNow, Math.max(40, Number(delayMs) || 250));
      };

      const clearSavedParagraphProgress = (syncServer = true) => {
        const clearedRecord = currentParagraphProgressCache && currentParagraphProgressCache.savedProgress;
        if (paragraphProgressSaveTimer) {
          window.clearTimeout(paragraphProgressSaveTimer);
          paragraphProgressSaveTimer = 0;
        }
        if (paragraphServerProgressSaveTimer) {
          window.clearTimeout(paragraphServerProgressSaveTimer);
          paragraphServerProgressSaveTimer = 0;
        }
        pendingParagraphServerProgressRecord = null;
        paragraphProgressLastSemanticSignature = "";
        const progressPaths = currentParagraphProgressPaths(currentParagraphProgressCache.savedProgress || {});
        if (currentParagraphProgressCache.progressKey) {
          removeSpaceWJson(currentParagraphProgressCache.progressKey);
          currentParagraphProgressCache.savedProgress = null;
        }
        clearLessonProgressOverride(progressPaths);
        clearLessonProgressDisplayCaches(progressPaths, "");
        updateParagraphProgressButtons();
        if (syncServer) {
          return clearParagraphServerProgress(clearedRecord);
        }
        return Promise.resolve(null);
      };

      const legacyVocabProgressIdentityFor = (payload = {}, words = []) => {
        const compactWords = (Array.isArray(words) ? words : []).map((item) => ({
          word: clean(item && item.word),
          meaning: clean(item && item.meaning),
          type: clean(item && item.type),
        }));
        const contentHash = hashSpaceWText(JSON.stringify({
          title: clean(payload.title || payload.name || ""),
          words: compactWords,
        }));
        const sourceKind = clean(currentLessonSource.source || currentLessonSource.kind || "local");
        const sourceId = clean(currentLessonSource.path || currentLessonSource.name || currentLessonSource.title || payload.title || payload.name || "space-v");
        return `${hashSpaceWText(`${sourceKind}:${sourceId}`)}:${contentHash}`;
      };

      const vocabProgressIdentityFor = (payload = {}, words = []) => stableLessonIdFor(payload) || legacyVocabProgressIdentityFor(payload, words);

      const normalizeVocabProgressRecord = (record = null) => {
        if (!record || typeof record !== "object") {
          return null;
        }
        const state = record.state && typeof record.state === "object" ? record.state : null;
        if (!state) {
          return null;
        }
        const activeRun = Boolean(record.activeRun || record.active_run || state.activeRun || state.active_run);
        const runId = clean(record.runId || record.run_id || state.runId || state.run_id || "");
        const completedRuns = Math.max(0, Math.floor(Number(record.completedRuns ?? record.completed_runs ?? state.completedRuns ?? state.completed_runs ?? 0) || 0));
        const complete = Boolean(!activeRun && (record.complete || record.completed || record.vocabComplete || record.lessonComplete || state.complete || state.vocabComplete || state.lessonComplete));
        return {
          version: 1,
          identity: clean(record.identity || state.identity || ""),
          path: clean(record.path || state.path || (state.lessonSource && state.lessonSource.path) || ""),
          savedAt: clean(record.savedAt || state.savedAt || state.updatedAt || ""),
          title: clean(record.title || state.title || "Space_V"),
          nodeIndex: Math.max(0, Math.floor(Number(record.nodeIndex ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number(record.nodeCount ?? state.nodeCount ?? 0) || 0)),
          activeRun,
          learnedCount: vocabProgressLearnedCountFromRecord(record),
          activeRun,
          runId,
          complete,
          completedRuns,
          completed_runs: completedRuns,
          serverSyncedAt: clean(record.serverSyncedAt || state.serverSyncedAt || ""),
          serverSyncedUser: clean(record.serverSyncedUser || ""),
          serverSyncedLearned: Math.max(0, Math.floor(Number(record.serverSyncedLearned || 0) || 0)),
          state: { ...state, activeRun, runId, complete },
        };
      };

      const vocabSavedSummary = (record = null) => {
        const savedAt = clean(record && (record.savedAt || record.updatedAt));
        if (!savedAt) {
          return "Saved Space_V progress found.";
        }
        const date = new Date(savedAt);
        if (!Number.isFinite(date.getTime())) {
          return "Saved Space_V progress found.";
        }
        return `Saved Space_V progress from ${date.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })}.`;
      };

      const vocabSavedStartIndex = (record = null) => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const recordIndex = record && Number.isFinite(Number(record.nodeIndex)) ? Number(record.nodeIndex) : 0;
        return Math.max(0, Math.floor(Number(state.currentIndex ?? state.nodeIndex ?? recordIndex) || 0));
      };

      const updateVocabProgressButtons = () => {
        const navigation = resolveSpaceRunNavigation(currentVocabProgressCache && currentVocabProgressCache.savedProgress, "Space_V");
        const hasVocabSaved = Boolean(pendingVocabularyPayload && navigation.resumeAvailable);
        if (loadStartButton && pendingVocabularyPayload) {
          loadStartButton.hidden = false;
          loadStartButton.disabled = false;
          loadStartButton.textContent = "New Study";
        }
        if (loadReviewButton && pendingVocabularyPayload) {
          loadReviewButton.hidden = !hasVocabSaved;
          loadReviewButton.disabled = !hasVocabSaved;
          loadReviewButton.textContent = "Continue Previous";
        }
        if (loadReviewTrainButton && pendingVocabularyPayload) {
          loadReviewTrainButton.hidden = true;
          loadReviewTrainButton.disabled = true;
        }
        if (typeof window.__ftSyncLessonEntryGateActions === "function") window.__ftSyncLessonEntryGateActions();
      };

      const configureVocabProgressCache = (payload = {}, words = []) => {
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
        const identity = vocabProgressIdentityFor(payload, words);
        const progressKey = spaceWStorageKey(SPACE_V_PROGRESS_PREFIX, identity);
        const legacyIdentity = legacyVocabProgressIdentityFor(payload, words);
        let savedProgress = normalizeVocabProgressRecord(readSpaceWJson(progressKey));
        if (!savedProgress && legacyIdentity !== identity) {
          savedProgress = normalizeVocabProgressRecord(readSpaceWJson(spaceWStorageKey(SPACE_V_PROGRESS_PREFIX, legacyIdentity)));
          if (savedProgress) writeSpaceWJson(progressKey, { ...savedProgress, identity });
        }
        currentVocabProgressCache = {
          identity,
          progressKey,
          savedProgress: savedProgress && savedProgress.state ? savedProgress : null,
          serverPayload: null,
          serverEtag: "",
          serverProgressPromise: null,
          serverProgressResult: null,
          serverProgressSettled: false,
        };
        updateVocabProgressButtons();
        return currentVocabProgressCache;
      };

      const compactVocabWordForRegistry = (item = {}) => {
        const source = item && typeof item === "object" ? item : {};
        const word = clean(source.word || source.w || source.en || source.e || "");
        if (!word) {
          return null;
        }
        return {
          word,
          meaning: clean(source.meaning || source.m || source.vi || source.q || ""),
          pron: clean(source.pron || source.p || source.ipa || source.i || ""),
          type: clean(source.type || source.ty || source.pos || ""),
        };
      };

      const vocabLearnedWordRecordsFrom = (learnedKeys = [], items = [], savedWords = []) => {
        const wantedKeys = new Set(Array.from(learnedKeys || []).map(clean).filter(Boolean));
        if (!wantedKeys.size) {
          return [];
        }
        const out = new Map();
        const add = (item) => {
          const normalized = compactVocabWordForRegistry(item);
          const key = vocabWordKey(normalized);
          if (!normalized || !key || (wantedKeys.size && !wantedKeys.has(key))) {
            return;
          }
          out.set(key, normalized);
        };
        (Array.isArray(savedWords) ? savedWords : []).forEach(add);
        (Array.isArray(items) ? items : []).forEach(add);
        return Array.from(out.values());
      };

      const currentVocabLearnedWordRecords = () => vocabLearnedWordRecordsFrom(vocabLearnedKeys, vocabItems);

      const vocabProgressSnapshot = () => {
        const learnedKeys = Array.from(vocabLearnedKeys);
        const learnedCount = learnedKeys.length;
        const activeRun = Boolean(!vocabReviewRunActive && !lessonCompletionSent && !vocabCompletionFinalizing);
        return {
          identity: currentVocabProgressCache.identity,
          title: clean(currentLessonSource.title || currentLessonSource.name || "Space_V"),
          path: currentVocabServerPath(),
          effective_path: normalizeServerPathValue(currentLessonSource && (currentLessonSource.effective_path || currentLessonSource.link_target || "")),
          link_target: normalizeServerPathValue(currentLessonSource && (currentLessonSource.link_target || "")),
          lessonSource: { ...(currentLessonSource || {}) },
          nodeCount: vocabItems.length,
          learnedCount,
          phase: vocabPhase,
          runId: clean(vocabActiveRunId),
          activeRun,
          complete: false,
          vocabComplete: false,
          lessonComplete: false,
          lessonCompletionSent: false,
          reviewing: Boolean(vocabReviewRunActive),
          reviewRun: Boolean(vocabReviewRunActive),
          currentIndex: Math.max(-1, Math.floor(Number.isFinite(Number(vocabCurrentIndex)) ? Number(vocabCurrentIndex) : -1)),
          queue: Array.isArray(vocabQueue) ? vocabQueue.slice() : [],
          batch: Array.isArray(vocabBatch) ? vocabBatch.map((item) => vocabWordKey(item)).filter(Boolean) : [],
          learned: learnedKeys,
          learnedWords: currentVocabLearnedWordRecords(),
          studyIndexes: Array.isArray(vocabStudyIndexes) ? vocabStudyIndexes.slice() : [],
          blueReady: Array.from(vocabBlueCrystalReadyKeys),
          attempts: Array.from(vocabAttemptCounts.entries()),
          drillIndex: vocabDrillIndex,
          drillCorrectCount: vocabDrillCorrectCount,
          drillFailCount: vocabDrillFailCount,
          shuffleOriginal: vocabShuffleOriginal.slice(),
          shuffleRound: vocabShuffleRound,
          shuffleQueue: vocabShuffleQueue.slice(),
          shuffleCorrectCount: vocabShuffleCorrectCount,
          shuffleFailCount: vocabShuffleFailCount,
          savedAt: new Date().toISOString(),
        };
      };

      const currentVocabServerPath = () => clean(currentLessonSource && currentLessonSource.path).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");

      const currentVocabProgressPaths = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        return [
          currentLessonStudyPath(),
          currentVocabServerPath(),
          source.path,
          state.path,
          lessonSource.path,
          currentLessonSource && currentLessonSource.linked_path,
          currentLessonSource && currentLessonSource.effective_path,
          currentLessonSource && currentLessonSource.link_target,
          lessonSource.linked_path,
          lessonSource.effective_path,
          lessonSource.link_target,
        ].map((path) => normalizeServerPathValue(path)).filter(Boolean);
      };

      const vocabServerPathFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : source;
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const sourceKind = clean(lessonSource.source || source.source || "").toLowerCase();
        const rawPath = clean(source.path || state.path || (sourceKind === "server" ? lessonSource.path : "") || "");
        return rawPath.replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
      };

      const canUseVocabProgressServer = () => {
        return Boolean(authToken && currentVocabProgressCache && currentVocabProgressCache.identity);
      };

      const vocabServerProgressPayload = (record = {}, action = "") => {
        const state = record && record.state && typeof record.state === "object" ? record.state : {};
        const pathValue = vocabServerPathFromRecord(record) || currentVocabServerPath();
        const linkIdentity = linkedLessonProgressIdentity(record, currentVocabProgressCache.identity);
        return {
          action: clean(action),
          path: pathValue,
          identity: clean((record && record.identity) || currentVocabProgressCache.identity),
          ...linkIdentity,
          title: clean((record && record.title) || state.title || currentLessonSource.title || currentLessonSource.name || "Space_V"),
          nodeIndex: Math.max(0, Math.floor(Number((record && record.nodeIndex) ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number((record && record.nodeCount) ?? state.nodeCount ?? vocabItems.length ?? 0) || 0)),
          learnedCount: Math.max(0, Math.floor(Number((record && (record.learnedCount ?? record.learned_count)) ?? state.learnedCount ?? state.learned_count ?? (Array.isArray(state.learned) ? state.learned.length : 0)) || 0)),
          expectedRunId: clean((record && (record.runId || record.run_id)) || state.runId || state.run_id || ""),
          baseRevision: Math.max(0, Math.floor(Number((record && (record._serverRevision || record.serverRevision || record.server_revision)) || 0) || 0)),
          savedAt: clean((record && record.savedAt) || state.savedAt || new Date().toISOString()),
          asyncVocabularySync: Boolean(record && record.asyncVocabularySync),
          state,
          completion_trace_id: clean(window.__ftCompletionTraceId || ""),
        };
      };

      const mergeVocabServerProgressRecord = (record = null) => {
        const normalized = normalizeVocabProgressRecord(record);
        if (!normalized) {
          return null;
        }
        if (normalized.identity && currentVocabProgressCache.identity && normalized.identity !== currentVocabProgressCache.identity) {
          return currentVocabProgressCache.savedProgress || null;
        }
        if (shouldKeepPendingLocalProgress(currentVocabProgressCache.savedProgress, normalized)) {
          scheduleProgressOutboxDrain(150);
          return currentVocabProgressCache.savedProgress;
        }
        normalized.pendingServerSync = false;
        currentVocabProgressCache.savedProgress = normalized;
        if (currentVocabProgressCache.progressKey) {
          writeSpaceWJson(currentVocabProgressCache.progressKey, normalized);
        }
        updateVocabProgressButtons();
        return normalized;
      };

      const refreshVocabServerProgress = async () => {
        if (!canUseVocabProgressServer()) {
          return currentVocabProgressCache.savedProgress || null;
        }
        const query = new URLSearchParams();
        const pathValue = currentVocabServerPath();
        if (pathValue) {
          query.set("path", pathValue);
        }
        query.set("identity", currentVocabProgressCache.identity);
        query.set("client_source", "space_v_progress_refresh");
        try {
          const cachedRow = currentVocabProgressCache.serverPayload && clean(currentVocabProgressCache.serverEtag || "")
            ? { payload: currentVocabProgressCache.serverPayload, etag: currentVocabProgressCache.serverEtag }
            : null;
          const result = await fetchProgressJsonFast(`/space-v/progress?${query.toString()}`, cachedRow);
          const payload = result && result.payload ? result.payload : (result || {});
          const merged = mergeVocabServerProgressRecord(payload.progress || null);
          currentVocabProgressCache.serverPayload = payload;
          currentVocabProgressCache.serverEtag = clean(result && result.etag || "");
          return merged || currentVocabProgressCache.savedProgress || null;
        } catch (error) {
          return currentVocabProgressCache.savedProgress || null;
        }
      };

      const PROGRESS_OUTBOX_STORAGE_KEY = "future_progress_outbox:v1";
      const PROGRESS_OUTBOX_ROW_PREFIX = "future_progress_outbox_row:v2:";
      const PROGRESS_OUTBOX_DRAIN_LEASE_PREFIX = "future_progress_outbox_drain:v1:";
      const PROGRESS_OUTBOX_DRAIN_LEASE_MS = 45000;
      const progressOutboxTabId = window.crypto && typeof window.crypto.randomUUID === "function"
        ? window.crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      let progressOutboxDrainTimer = 0;
      let progressOutboxDrainBusy = false;
      let progressOutboxRetryMs = 4000;

      const progressRecordTimestampMs = (record = {}) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const raw = clean(source.localSavedAt || source.savedAt || source.saved_at || source.updatedAt || source.updated_at || state.savedAt || state.updatedAt || "");
        const parsed = raw ? Date.parse(raw) : NaN;
        return Number.isFinite(parsed) ? parsed : 0;
      };

      const shouldKeepPendingLocalProgress = (localRecord = null, remoteRecord = null) => Boolean(
        localRecord
        && localRecord.pendingServerSync === true
        && progressRecordTimestampMs(localRecord) > progressRecordTimestampMs(remoteRecord || {})
      );

      const progressOutboxOwner = () => clean(currentAuthUsername || (authUser && authUser.value) || "").toLowerCase();

      const progressOutboxRowKey = (row = {}) => `${PROGRESS_OUTBOX_ROW_PREFIX}${encodeURIComponent(clean(row && row.id))}:${encodeURIComponent(clean(row && row.revision) || "legacy")}`;

      const writeProgressOutboxRow = (row = {}) => {
        const id = clean(row && row.id);
        return Boolean(id && writeSpaceWJson(progressOutboxRowKey(row), row));
      };

      const readProgressOutbox = () => {
        const rows = new Map();
        const rowKeys = new Map();
        const staleKeys = new Set();
        const consider = (row, key = "") => {
          const id = clean(row && row.id);
          if (!id) return;
          const current = rows.get(id);
          const currentOrder = current ? [progressRecordTimestampMs(current), clean(current.revision)] : [-1, ""];
          const nextOrder = [progressRecordTimestampMs(row), clean(row.revision)];
          if (!current || nextOrder[0] > currentOrder[0] || (nextOrder[0] === currentOrder[0] && nextOrder[1] > currentOrder[1])) {
            const previousKey = rowKeys.get(id);
            if (previousKey) staleKeys.add(previousKey);
            rows.set(id, row);
            rowKeys.set(id, key);
          } else if (key) {
            staleKeys.add(key);
          }
        };
        const legacy = readSpaceWJson(PROGRESS_OUTBOX_STORAGE_KEY);
        const legacyRows = legacy && Array.isArray(legacy.rows) ? legacy.rows.filter((row) => row && typeof row === "object") : [];
        legacyRows.forEach((row) => consider(row));
        if (window.localStorage) {
          for (let index = 0; index < localStorage.length; index += 1) {
            const key = clean(localStorage.key(index));
            if (!key.startsWith(PROGRESS_OUTBOX_ROW_PREFIX)) continue;
            const row = readSpaceWJson(key);
            if (row && typeof row === "object") consider(row, key);
          }
        }
        if (legacyRows.length) {
          rows.forEach((row, id) => {
            if (!rowKeys.get(id)) writeProgressOutboxRow(row);
          });
          try { localStorage.removeItem(PROGRESS_OUTBOX_STORAGE_KEY); } catch (error) {}
        }
        staleKeys.forEach((key) => { try { localStorage.removeItem(key); } catch (error) {} });
        return Array.from(rows.values());
      };

      const removeProgressOutboxRow = (row = {}) => {
        const id = clean(row && row.id);
        if (!id) return false;
        const key = progressOutboxRowKey(row);
        const current = readSpaceWJson(key);
        if (current && clean(current.revision) !== clean(row.revision)) return false;
        try {
          localStorage.removeItem(key);
          return true;
        } catch (error) {
          return false;
        }
      };

      const progressOutboxDrainLeaseKey = (owner = "") => `${PROGRESS_OUTBOX_DRAIN_LEASE_PREFIX}${encodeURIComponent(clean(owner).toLowerCase())}`;

      // Added 2026-07-21: one tab drains a user's durable progress rows while other tabs keep enqueueing independently.
      const acquireProgressOutboxDrainLease = (owner = "") => {
        const key = progressOutboxDrainLeaseKey(owner);
        const now = Date.now();
        const existing = readSpaceWJson(key);
        if (existing && clean(existing.token) && Number(existing.expiresAt || 0) > now && clean(existing.tabId) !== progressOutboxTabId) {
          return "";
        }
        const token = `${progressOutboxTabId}:${now.toString(36)}:${Math.random().toString(36).slice(2, 9)}`;
        if (!writeSpaceWJson(key, { token, tabId: progressOutboxTabId, expiresAt: now + PROGRESS_OUTBOX_DRAIN_LEASE_MS })) return "";
        const confirmed = readSpaceWJson(key);
        return clean(confirmed && confirmed.token) === token ? token : "";
      };

      const renewProgressOutboxDrainLease = (owner = "", token = "") => {
        const key = progressOutboxDrainLeaseKey(owner);
        const current = readSpaceWJson(key);
        if (!token || clean(current && current.token) !== token) return false;
        return writeSpaceWJson(key, { token, tabId: progressOutboxTabId, expiresAt: Date.now() + PROGRESS_OUTBOX_DRAIN_LEASE_MS });
      };

      const releaseProgressOutboxDrainLease = (owner = "", token = "") => {
        const key = progressOutboxDrainLeaseKey(owner);
        const current = readSpaceWJson(key);
        if (!token || clean(current && current.token) !== token) return false;
        try { localStorage.removeItem(key); return true; } catch (error) { return false; }
      };

      const progressPathFromRecord = (record = {}) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        return normalizeServerPathValue(source.path || state.path || lessonSource.path || "");
      };

      const progressOutboxIdentity = (space = "", record = {}) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const lessonSource = state.lessonSource && typeof state.lessonSource === "object" ? state.lessonSource : {};
        const rawId = clean(
          source.lesson_id || source.lessonId || source.file_id || source.fileId || source.identity ||
          state.lesson_id || state.lessonId || state.file_id || state.fileId || state.identity ||
          lessonSource.lesson_id || lessonSource.file_id || lessonSource.identity || "",
        );
        const lessonId = rawId.toLowerCase().startsWith("ftg-lesson-") ? rawId : "";
        const normalizedSpace = clean(source.space_type || source.spaceType || state.space_type || state.spaceType || space).toLowerCase().replace(/-/g, "_");
        return {
          lesson_id: lessonId,
          file_id: lessonId,
          task_owner: clean(source.task_owner || source.taskOwner || state.task_owner || state.taskOwner || lessonSource.task_owner || currentAuthUsername || ""),
          space_type: normalizedSpace.startsWith("space_") ? normalizedSpace : clean(space).toLowerCase().replace(/-/g, "_"),
          operation_id: clean(source.operation_id || source.operationId || source.syncOperationId || source.sync_operation_id || state.operation_id || state.syncOperationId || state.sync_operation_id || ""),
          sequence: Math.max(0, Math.floor(Number(source.sequence ?? state.sequence ?? 0) || 0)),
          server_revision: Math.max(0, Math.floor(Number(source._serverRevision ?? source.serverRevision ?? source.server_revision ?? state.serverRevision ?? 0) || 0)),
          legacy_identity: lessonId ? "" : rawId,
        };
      };

      const progressOutboxHash = (value = "") => {
        let hash = 2166136261;
        String(value || "").split("").forEach((character) => {
          hash ^= character.charCodeAt(0);
          hash = Math.imul(hash, 16777619);
        });
        return (hash >>> 0).toString(36);
      };

      const progressPayloadFromLocalRecord = (space = "", record = {}, outboxRow = {}) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const path = progressPathFromRecord(source);
        const resolvedIdentity = progressOutboxIdentity(space, source);
        const lessonId = resolvedIdentity.lesson_id || clean(outboxRow.lesson_id || outboxRow.file_id);
        const operationId = resolvedIdentity.operation_id || clean(outboxRow.operation_id);
        const identityFields = {
          lesson_id: lessonId,
          file_id: lessonId,
          task_owner: resolvedIdentity.task_owner || clean(outboxRow.task_owner),
          space_type: resolvedIdentity.space_type || clean(outboxRow.space_type),
          operation_id: operationId,
          sequence: Math.max(resolvedIdentity.sequence, Number(outboxRow.sequence || 0) || 0),
          revision: Math.max(resolvedIdentity.server_revision, Number(outboxRow.server_revision || 0) || 0),
        };
        if (space === "space_pdf") {
          return { ...source, ...identityFields, path, action: clean(source.action || "offline-replay") };
        }
        if (space === "space_pdf_ai_question") {
          return {
            ...identityFields,
            path,
            mode: clean(source.mode || state.mode || "pdf") || "pdf",
            page: Math.max(1, Math.floor(Number(source.page || state.page || 1) || 1)),
            regionKey: clean(source.regionKey || source.region_key || ""),
            randomOrder: Boolean(source.randomOrder),
            order: Array.isArray(source.order) ? source.order : [],
            questionIndex: Math.max(0, Math.floor(Number(source.questionIndex || 0) || 0)),
            completed: source.completed && typeof source.completed === "object" ? source.completed : {},
            results: source.results && typeof source.results === "object" ? source.results : {},
            savedAt: clean(source.localSavedAt || source.savedAt || new Date().toISOString()),
            resetProgress: Boolean(source.resetProgress),
          };
        }
        const payload = {
          ...identityFields,
          action: "offline-replay",
          path,
          identity: lessonId || clean(source.identity || state.identity || resolvedIdentity.legacy_identity || ""),
          title: clean(source.title || state.title || ""),
          nodeIndex: Math.max(0, Math.floor(Number(source.nodeIndex ?? state.currentIndex ?? state.nodeIndex ?? 0) || 0)),
          nodeCount: Math.max(0, Math.floor(Number(source.nodeCount ?? state.nodeCount ?? state.totalNodes ?? 0) || 0)),
          savedAt: clean(source.savedAt || state.savedAt || ""),
          syncOperationId: clean(source.syncOperationId || source.sync_operation_id || state.syncOperationId || state.sync_operation_id || ""),
          reviewing: Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun),
          reviewRun: Boolean(source.reviewing || source.reviewRun || state.reviewing || state.reviewRun),
          state,
        };
        if (!payload.syncOperationId && operationId) payload.syncOperationId = operationId;
        if (space === "space_v") {
          payload.learnedCount = Math.max(0, Math.floor(Number(source.learnedCount ?? source.learned_count ?? state.learnedCount ?? state.learned_count ?? (Array.isArray(state.learned) ? state.learned.length : 0)) || 0));
        }
        return payload;
      };

      const markLocalProgressPending = (localKey = "", pending = true, syncedSavedAt = "") => {
        if (!localKey) {
          return null;
        }
        const record = readSpaceWJson(localKey);
        if (!record || typeof record !== "object") {
          return null;
        }
        record.pendingServerSync = Boolean(pending);
        if (!pending) {
          record.serverSyncedAt = new Date().toISOString();
          record.serverSyncedSavedAt = clean(syncedSavedAt || record.savedAt || (record.state && record.state.savedAt) || "");
        }
        writeSpaceWJson(localKey, record);
        return record;
      };

      const enqueueProgressOutboxRequest = (space = "", endpoint = "", payload = {}, localKey = "") => {
        const owner = progressOutboxOwner();
        const body = payload && typeof payload === "object" ? payload : {};
        const path = progressPathFromRecord(body) || normalizeServerPathValue(body.path || "");
        const identityFields = progressOutboxIdentity(space, body);
        const identity = identityFields.lesson_id || clean(body.identity || identityFields.legacy_identity || "");
        if (!owner || !space || !endpoint || (!path && !identityFields.lesson_id && !identity) || !localKey) {
          return null;
        }
        const localRecord = readSpaceWJson(localKey);
        if (localRecord) {
          markLocalProgressPending(localKey, true);
        }
        const stableLessonId = identityFields.lesson_id;
        const logicalTarget = stableLessonId || `${path.toLowerCase()}|${identity}`;
        const id = `${owner}|${space}|${logicalTarget}`;
        const revision = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        const savedAt = clean(body.savedAt || (body.state && body.state.savedAt) || "");
        const operationId = identityFields.operation_id || `progress-outbox:${progressOutboxHash(`${id}|${savedAt}|${localKey}`)}`;
        const row = {
          id,
          revision,
          owner,
          space,
          endpoint,
          localKey,
          path,
          identity,
          lesson_id: stableLessonId,
          file_id: stableLessonId,
          task_owner: identityFields.task_owner,
          space_type: identityFields.space_type,
          operation_id: operationId,
          sequence: identityFields.sequence,
          server_revision: identityFields.server_revision,
          savedAt,
          queuedAt: new Date().toISOString(),
          attempts: 0,
          fallbackPayload: localRecord ? null : {
            ...body,
            lesson_id: stableLessonId,
            file_id: stableLessonId,
            task_owner: identityFields.task_owner,
            space_type: identityFields.space_type,
            operation_id: operationId,
            sequence: identityFields.sequence,
            revision: identityFields.server_revision,
          },
        };
        if (!writeProgressOutboxRow(row)) {
          return null;
        }
        return row;
      };

      const acknowledgeProgressOutboxRequest = (row = {}, sentPayload = {}) => {
        if (!row || !row.id) {
          return;
        }
        const current = readProgressOutbox().find((item) => clean(item.id) === clean(row.id));
        if (!current || clean(current.revision) !== clean(row.revision)) {
          return;
        }
        const sentSavedAt = clean(sentPayload.savedAt || (sentPayload.state && sentPayload.state.savedAt) || row.savedAt || "");
        const local = readSpaceWJson(row.localKey);
        if (local && progressRecordTimestampMs(local) <= progressRecordTimestampMs(sentPayload)) {
          markLocalProgressPending(row.localKey, false, sentSavedAt);
          if (clean(row.space) === "space_pdf" && typeof pdfProgressLocalSharedKey === "function") {
            markLocalProgressPending(pdfProgressLocalSharedKey(row.path), false, sentSavedAt);
          }
        }
        removeProgressOutboxRow(row);
      };

      const scheduleProgressOutboxDrain = (delayMs = 1200) => {
        if (!progressOutboxOwner() || !authToken) {
          return;
        }
        if (progressOutboxDrainTimer) {
          window.clearTimeout(progressOutboxDrainTimer);
        }
        progressOutboxDrainTimer = window.setTimeout(() => {
          progressOutboxDrainTimer = 0;
          void drainProgressOutbox();
        }, Math.max(100, Number(delayMs) || 1200));
      };

      const drainProgressOutbox = async (crossTabLockHeld = false) => {
        const owner = progressOutboxOwner();
        if (!owner || !authToken || progressOutboxDrainBusy) {
          return false;
        }
        if (!crossTabLockHeld && typeof navigator !== "undefined" && navigator.locks && typeof navigator.locks.request === "function") {
          return navigator.locks.request(
            `future-progress-outbox-drain:${owner}`,
            { ifAvailable: true },
            (lock) => {
              if (!lock) {
                scheduleProgressOutboxDrain(1200);
                return false;
              }
              return drainProgressOutbox(true);
            },
          );
        }
        const drainLease = acquireProgressOutboxDrainLease(owner);
        if (!drainLease) {
          scheduleProgressOutboxDrain(1200);
          return false;
        }
        const rows = readProgressOutbox().filter((row) => clean(row.owner).toLowerCase() === owner);
        if (!rows.length) {
          progressOutboxRetryMs = 4000;
          releaseProgressOutboxDrainLease(owner, drainLease);
          return true;
        }
        progressOutboxDrainBusy = true;
        let failed = false;
        try {
          for (const row of rows.slice(0, 40)) {
            if (!renewProgressOutboxDrainLease(owner, drainLease)) {
              failed = true;
              break;
            }
            const local = readSpaceWJson(row.localKey);
            if (local && local.pendingServerSync !== true) {
              acknowledgeProgressOutboxRequest(row, local);
              continue;
            }
            const payload = local
              ? progressPayloadFromLocalRecord(clean(row.space), local, row)
              : (row.fallbackPayload && typeof row.fallbackPayload === "object" ? row.fallbackPayload : null);
            if (!payload || (!payload.path && !payload.identity && !payload.lesson_id) || (!payload.savedAt && clean(payload.action).toLowerCase() !== "clear")) {
              continue;
            }
            try {
              await fetchAuthJson(clean(row.endpoint), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                timeoutMs: 30000,
              });
              acknowledgeProgressOutboxRequest(row, payload);
            } catch (error) {
              failed = true;
              break;
            }
          }
        } finally {
          progressOutboxDrainBusy = false;
          releaseProgressOutboxDrainLease(owner, drainLease);
        }
        if (failed || readProgressOutbox().some((row) => clean(row.owner).toLowerCase() === owner)) {
          progressOutboxRetryMs = failed ? Math.min(30000, Math.max(4000, progressOutboxRetryMs * 1.7)) : 250;
          scheduleProgressOutboxDrain(progressOutboxRetryMs);
          return false;
        }
        progressOutboxRetryMs = 4000;
        return true;
      };

      const seedProgressOutboxFromLocalStorage = () => {
        const owner = progressOutboxOwner();
        if (!owner || !window.localStorage) {
          return 0;
        }
        const mappings = [
          [SPACE_W_PROGRESS_PREFIX, "space_w", "/space-w/progress?client_source=offline_outbox&response=compact-v1"],
          [SPACE_Q_PROGRESS_PREFIX, "space_q", "/space-q/progress?client_source=offline_outbox&response=compact-v1"],
          [`${SPACE_P_PROGRESS_PREFIX}_space_l`, "space_p", "/space-p/progress?client_source=offline_outbox&response=compact-v1"],
          [`${SPACE_P_PROGRESS_PREFIX}_space_s`, "space_p", "/space-p/progress?client_source=offline_outbox&response=compact-v1"],
          [SPACE_P_PROGRESS_PREFIX, "space_p", "/space-p/progress?client_source=offline_outbox&response=compact-v1"],
          [SPACE_V_PROGRESS_PREFIX, "space_v", "/space-v/progress?client_source=offline_outbox&response=compact-v1"],
          ["future_space_pdf_progress", "space_pdf", "/space-pdf/progress?client_source=offline_outbox"],
          ["future_pdf_ai_question_progress", "space_pdf_ai_question", "/space-pdf/ai-question-progress?client_source=offline_outbox"],
        ];
        let seeded = 0;
        for (let index = 0; index < localStorage.length; index += 1) {
          const key = clean(localStorage.key(index) || "");
          const mapping = mappings.find(([prefix]) => key.startsWith(`${prefix}:${owner}:`));
          if (!mapping) {
            continue;
          }
          const record = readSpaceWJson(key);
          if (!record || record.pendingServerSync !== true) {
            continue;
          }
          const payload = progressPayloadFromLocalRecord(mapping[1], record);
          if (enqueueProgressOutboxRequest(mapping[1], mapping[2], payload, key)) {
            seeded += 1;
          }
        }
        if (seeded || readProgressOutbox().some((row) => clean(row.owner).toLowerCase() === owner)) {
          scheduleProgressOutboxDrain(150);
        }
        return seeded;
      };

      window.addEventListener("online", () => {
        seedProgressOutboxFromLocalStorage();
        scheduleProgressOutboxDrain(150);
      });

      const sendVocabServerProgress = async (record = null, action = "") => {
        if (!canUseVocabProgressServer()) {
          return null;
        }
        const body = vocabServerProgressPayload(record || currentVocabProgressCache.savedProgress || {}, action);
        if (!body.path || !body.identity) {
          throw new Error(`Space_V progress missing ${!body.path ? "path" : "identity"}.`);
        }
        const sourceLabel = clean(action || "autosave").replace(/[^a-z0-9_-]+/gi, "_").toLowerCase() || "autosave";
        const outboxRow = enqueueProgressOutboxRequest("space_v", "/space-v/progress?client_source=offline_outbox&response=compact-v1", body, currentVocabProgressCache.progressKey);
        let result;
        try {
          result = await fetchAuthJson(`/space-v/progress?client_source=space_v_${encodeURIComponent(sourceLabel)}&response=compact-v1`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            timeoutMs: 30000,
          });
          if (outboxRow) acknowledgeProgressOutboxRequest(outboxRow, body);
        } catch (error) {
          if (outboxRow) {
            error.progressOutboxQueued = true;
            scheduleProgressOutboxDrain(progressOutboxRetryMs);
          }
          throw error;
        }
        const payload = result && result.payload ? result.payload : (result || {});
        if (typeof applyVocabularyCompletionDeltaToLocalPreview === "function") {
          applyVocabularyCompletionDeltaToLocalPreview(payload, currentAuthUsername);
        }
        if (payload.progress) {
          const canonicalProgress = clean(payload.response_schema) === "space-v-progress-compact-v1"
            ? {
              ...body,
              ...payload.progress,
              state: {
                ...(body.state && typeof body.state === "object" ? body.state : {}),
                ...(payload.progress.state && typeof payload.progress.state === "object" ? payload.progress.state : {}),
              },
            }
            : payload.progress;
          mergeVocabServerProgressRecord(canonicalProgress);
          currentVocabProgressCache.serverPayload = null;
          currentVocabProgressCache.serverEtag = "";
          const progressOverride = vocabProgressOverrideFromRecord(canonicalProgress);
          if (progressOverride) {
            const progressPaths = currentVocabProgressPaths(canonicalProgress || body);
            setLessonProgressOverride(progressPaths, progressOverride, 300000);
            rememberLessonVaultProgressPin(progressPaths, progressOverride, 300000);
            clearLessonProgressDisplayCaches(progressPaths, "Space_V");
          }
        }
        return payload;
      };

      const clearVocabServerProgress = async (record = null) => {
        if (!canUseVocabProgressServer()) {
          return null;
        }
        return await sendVocabServerProgress(record || { identity: currentVocabProgressCache.identity, state: {} }, "clear");
      };

      const vocabSyncStorageKey = (identity = "") => spaceWStorageKey(SPACE_V_VOCAB_SYNC_PREFIX, clean(identity || currentVocabProgressCache.identity || "space-v"));

