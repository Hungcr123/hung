

      const resumeSpaceWAfterVocabulary = async () => {
        const pending = pendingSpaceWAfterVocabulary;
        const mission = currentVocabularyMission && typeof currentVocabularyMission === "object" ? { ...currentVocabularyMission } : {};
        hideVocabPreflightGate();
        spaceWVocabBuildGuardPath = "";
        if (pending && pending.payload) {
          const source = pending.source || {};
          const sourcePath = clean(source.path).replace(/\\/g, "/");
          if (sourcePath) {
            spaceWVocabClearedPaths.add(sourcePath);
          }
          setCurrentLessonSource(source, pending.payload);
          const payload = pending.payload;
          const selectedVoiceValue = pending.selectedVoiceValue || "";
          const resumeOptions = pending.resumeOptions && typeof pending.resumeOptions === "object" ? pending.resumeOptions : {};
          pendingSpaceWAfterVocabulary = null;
          currentVocabularyMission = null;
          if (isQuestionPayload(payload)) {
            await enterQuestionPayloadNow(payload, { ...resumeOptions, allowDuringVocabBuild: true });
          } else if (isParagraphPayload(payload)) {
            await enterParagraphPayloadNow(payload, { ...resumeOptions, allowDuringVocabBuild: true });
          } else {
            await startTranslationLessonPayload(payload, selectedVoiceValue, { ...resumeOptions, allowDuringVocabBuild: true });
          }
          return;
        }
        const sourcePath = clean(mission.source_path || "").replace(/\\/g, "/");
        if (!sourcePath) {
          showCompletionGate();
          return;
        }
        try {
          const missionSpace = vocabPreflightSpaceLabel(mission.source_space || mission.space || sourcePath);
          setLoadStatus(`Opening the ${missionSpace} mission...`);
          const result = await fetchServerText(`/server-data/file?path=${encodeURIComponent(sourcePath)}`);
          const payload = await decodeFuturePayload(String(result.text || "").replace(/^\uFEFF/, ""));
          spaceWVocabClearedPaths.add(sourcePath);
          const payloadSpace = vocabPreflightPayloadSpace(payload, sourcePath);
          setCurrentLessonSource({
            source: "server",
            path: sourcePath,
            name: sourcePath.split("/").pop() || payloadSpace,
            title: clean(mission.source_title || ""),
          }, payload);
          currentVocabularyMission = null;
          if (isQuestionPayload(payload)) {
            await enterQuestionPayloadNow(payload, { allowDuringVocabBuild: true });
          } else if (isParagraphPayload(payload)) {
            await enterParagraphPayloadNow(payload, { allowDuringVocabBuild: true });
          } else {
            await startTranslationLessonPayload(payload, voiceSelect.value, { allowDuringVocabBuild: true });
          }
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not open lesson after vocabulary.", true);
          showCompletionGate();
        }
      };

      const updateVocabularyBuildProgress = (job = {}) => {
        const progress = Math.max(0, Math.min(100, Number(job.progress || 0) || 0));
        const message = clean(job.message || "Building Space_V queue on the server...");
        const suffix = progress ? ` ${Math.round(progress)}%` : "";
        setVocabPreflightBusy(true, `${message}${suffix}`);
        if (vocabPreflightRemaining) {
          vocabPreflightRemaining.textContent = progress ? `${Math.round(progress)}% complete` : "Server build running";
        }
        if (vocabPreflightFiles) {
          const files = Array.isArray(job.files) ? job.files : [];
          if (files.length) {
            vocabPreflightFiles.textContent = files.length === 1 ? "1 pack ready" : `${files.length} packs ready`;
          }
        }
      };

      const waitVocabularyBuildJob = async (jobId, sourcePath, token) => {
        let lastJob = null;
        while (token === vocabPreflightBuildToken) {
          const result = await fetchServerJson(`/vocab/build-status?id=${encodeURIComponent(jobId)}`);
          const job = result.payload || {};
          lastJob = job;
          updateVocabularyBuildProgress(job);
          const status = clean(job.status).toLowerCase();
          if (status === "done") {
            return job;
          }
          if (status === "error" || status === "failed") {
            throw new Error(clean(job.error || job.message) || "Vocabulary build failed.");
          }
          await delay(900);
        }
        throw new Error("Vocabulary build was cancelled.");
      };

      const startVocabularyMissionFromPreflight = async () => {
        if (vocabPreflightBusy) {
          return;
        }
        const state = vocabPreflightState || {};
        const directFiles = Array.isArray(state.files) ? state.files : (Array.isArray(state.pending_files) ? state.pending_files : []);
        if (directFiles.length) {
          try {
            await loadVocabularyMissionFile(directFiles[0]);
          } catch (error) {
            setVocabPreflightBusy(false);
            setVocabPreflightStatus(error && error.message ? error.message : "Could not open the vocabulary pack.", true);
          }
          return;
        }
        const pending = pendingSpaceWAfterVocabulary || {};
        const sourcePath = clean((pending.source && pending.source.path) || state.source_path).replace(/\\/g, "/");
        const spaceLabel = vocabPreflightSpaceLabel(pending.space || state.space || sourcePath);
        if (!sourcePath) {
          setVocabPreflightStatus(`${spaceLabel} source is missing.`, true);
          return;
        }
        try {
          const token = ++vocabPreflightBuildToken;
          spaceWVocabBuildGuardPath = sourcePath;
          setVocabPreflightBusy(true, "Starting server vocabulary build...");
          const result = await fetchServerJson("/vocab/build-mission", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: sourcePath, async: true }),
          });
          const initialJob = result.payload || {};
          updateVocabularyBuildProgress(initialJob);
          const jobId = clean(initialJob.job_id || initialJob.id);
          const finalPayload = jobId && clean(initialJob.status).toLowerCase() !== "done"
            ? await waitVocabularyBuildJob(jobId, sourcePath, token)
            : initialJob;
          if (token !== vocabPreflightBuildToken || sourcePath !== spaceWVocabBuildGuardPath) {
            return;
          }
          const files = Array.isArray(finalPayload && finalPayload.files)
            ? finalPayload.files
            : (Array.isArray(finalPayload && finalPayload.result && finalPayload.result.files) ? finalPayload.result.files : []);
          if (!files.length) {
            spaceWVocabClearedPaths.add(sourcePath);
            spaceWVocabBuildGuardPath = "";
            hideVocabPreflightGate();
            await resumeSpaceWAfterVocabulary();
            return;
          }
          vocabPreflightState = { ...(finalPayload.result || finalPayload || {}), files };
          spaceWVocabBuildGuardPath = "";
          await loadVocabularyMissionFile(files[0]);
        } catch (error) {
          spaceWVocabBuildGuardPath = "";
          setVocabPreflightBusy(false);
          setVocabPreflightStatus(error && error.message ? error.message : "Could not build the vocabulary queue.", true);
        }
      };

      const handleVocabularyMissionCompletion = async () => {
        const mission = currentVocabularyMission && typeof currentVocabularyMission === "object" ? { ...currentVocabularyMission } : null;
        const missionKind = clean(mission && mission.kind).toLowerCase();
        const hasSpaceWQueue = Boolean(pendingSpaceWAfterVocabulary || (mission && /space_[wqpsl]_vocab_prerequisite/.test(missionKind)));
        if (!hasSpaceWQueue) {
          const result = await reportLessonCompleted("vocab_complete", { showGate: false });
          if (result && typeof window.prewarmCupLeaderboard === "function") {
            await window.prewarmCupLeaderboard({ scope: "day", type: "space_v", force: true });
          }
          hideVocabModePopup();
          await openCupLeaderboardAfterVocabularyComplete();
          showCompletionGate();
          return;
        }
        const result = await reportLessonCompleted("vocab_complete", { showGate: false });
        if (!result) {
          showCompletionGate();
          return;
        }
        if (typeof window.prewarmCupLeaderboard === "function") {
          await window.prewarmCupLeaderboard({ scope: "day", type: "space_v", force: true });
        }
        hideVocabModePopup();
        await openCupLeaderboardAfterVocabularyComplete();
        const vocabulary = result && result.vocabulary && typeof result.vocabulary === "object" ? result.vocabulary : {};
        const remaining = Array.isArray(vocabulary.remaining_files) ? vocabulary.remaining_files : [];
        if (remaining.length) {
          showVocabPreflightGate({
            pending_count: remaining.length,
            pending_files: remaining,
            files: remaining,
            new_count: Number(vocabulary.learned_words || 0) || 0,
          }, "queue");
          return;
        }
        const targetSpace = vocabPreflightSpaceLabel(
          (pendingSpaceWAfterVocabulary && pendingSpaceWAfterVocabulary.space) ||
          (mission && (mission.source_space || mission.space)) ||
          missionKind
        );
        setVocabFeedback(`Vocabulary queue complete. Opening ${targetSpace} mission.`, "ok");
        showVocabModePopup(
          "Vocabulary route complete",
          `All queued Space_V packs are synced. Opening the ${targetSpace} mission now.`,
          "probe",
          1600,
        ).then(() => {
          void resumeSpaceWAfterVocabulary();
        });
      };

      const reportLessonCompleted = async (reason = "complete", options = {}) => {
        const isolatedProbe = ["127.0.0.1", "localhost"].includes(window.location.hostname) && window.location.port === "18877";
        if (isolatedProbe && options && options.forceNewCompletion) {
          lessonCompletionSent = false;
        }
        const traceSeed = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        window.__ftCompletionTraceId = `${clean(currentAuthUsername || "user")}-space-v-${traceSeed}`.slice(0, 160);
        window.__ftCompletionTraceUntil = Date.now() + 15000;
        // Added 2026-07-29: final completion owns the last progress write; cancel a queued autosave before it races the final POST.
        if (typeof vocabProgressSaveTimer !== "undefined" && vocabProgressSaveTimer) {
          window.clearTimeout(vocabProgressSaveTimer);
          vocabProgressSaveTimer = 0;
        }
        if (typeof vocabServerProgressSaveTimer !== "undefined" && vocabServerProgressSaveTimer) {
          window.clearTimeout(vocabServerProgressSaveTimer);
          vocabServerProgressSaveTimer = 0;
        }
        saveSpaceWProgressNow();
        const showGate = !options || options.showGate !== false;
        if (lessonCompletionSent) {
          if (showGate) {
            showCompletionGate();
            const completedSourcePath = clean(currentLessonSource && currentLessonSource.path).split(/[?#]/, 1)[0].toLowerCase();
            handleSpaceCompletion({}, {
              sourcePath: completedSourcePath,
              fallbackType: currentCupType,
              completionAlreadyConfirmed: true,
            }, {
              openTopLeaderboard: (type, response) => openCupLeaderboard({
                scope: "day",
                type,
                pendingUser: response && response.space_leaderboard && response.space_leaderboard.viewer_delta,
              }),
            });
          }
          return null;
        }
        lessonCompletionSent = true;
        completionSyncBusy = true;
        if (showGate) {
          showCompletionGate();
        }
        const source = currentLessonSource || {};
        const sourcePath = clean(source.path).split(/[?#]/, 1)[0];
        const completionRunId = clean(options && options.completionRunIdOverride)
          || (/\.space_w$/i.test(sourcePath) ? clean(spaceWActiveRunId) : "");
        const payload = {
          path: clean(source.path),
          lesson_id: clean(source.lesson_id || source.lessonId || source.file_id || source.fileId || ""),
          linked_path: clean(source.linked_path || ""),
          effective_path: clean(source.effective_path || ""),
          link_target: clean(source.link_target || ""),
          task_owner: clean(source.task_owner || source.taskOwner || serverTaskOwnerContext || currentAuthUsername || ""),
          name: clean(source.name),
          title: clean(source.title || (currentNode && currentNode.title) || "Future lesson"),
          nodes: lessonNodes.length,
          completed_at: new Date().toISOString(),
          ...(completionRunId ? { completion_run_id: completionRunId } : {}),
          source: clean(source.source) || (source.path ? "server" : "local"),
          reason,
          completion_trace_id: clean(window.__ftCompletionTraceId || ""),
        };
        try {
          if (typeof sendLessonStudyTimeTick === "function") {
            await sendLessonStudyTimeTick(30);
          }
          const result = await fetchServerJson("/lesson/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const study = result.payload && result.payload.study ? result.payload.study : {};
          currentLessonSource.study = study;
          clearServerBrowserListCache();
          clearLessonTaskPanelCache();
          const completedTaskOwner = clean(serverTaskOwnerContext || currentAuthUsername || "");
          if (completedTaskOwner && typeof loadLessonTasks === "function") {
            void loadLessonTasks(completedTaskOwner, { fresh: true }).catch(() => {});
          }
          const mine = Number(study.mine || 0) || 0;
          const total = Number(study.total || 0) || 0;
          const completionProgress = study.progress && typeof study.progress === "object"
            ? {
              ...study.progress,
              completed: true,
              complete: true,
              completedRuns: mine,
              completed_runs: mine,
              previously_completed: true,
              previouslyCompleted: true,
            }
            : {
              space: currentCupType === "space_w" ? "Space_W" : "",
              done: currentCupType === "space_w" ? Math.max(0, lessonNodes.length * 2) : Math.max(0, lessonNodes.length),
              total: currentCupType === "space_w" ? Math.max(0, lessonNodes.length * 2) : Math.max(0, lessonNodes.length),
              percent: 100,
              text: currentCupType === "space_w" ? `${Math.max(0, lessonNodes.length * 2)}/${Math.max(0, lessonNodes.length * 2)}` : `${Math.max(0, lessonNodes.length)}/${Math.max(0, lessonNodes.length)}`,
              completed: true,
              complete: true,
              completedRuns: mine,
              completed_runs: mine,
              previously_completed: true,
              previouslyCompleted: true,
            };
          const completionPaths = [source.path, source.linked_path, source.effective_path, source.link_target].filter(Boolean);
          if (completionPaths.length && typeof setLessonProgressOverride === "function") {
            setLessonProgressOverride(completionPaths, completionProgress, 120000, { force: true });
          }
          const suffix = mine ? ` Ban da hoc file nay ${mine} lan.` : (total ? ` Tong luot hoc file: ${total}.` : "");
          setTtsStatus(`Da bao server va luu log hoc tap.${suffix}`, false);
          completionSyncBusy = false;
          stopLessonStudyTimeHeartbeat();
          if (showGate) {
            updateCompletionGate(study);
          }
          handleSpaceCompletion(result.payload || {}, {
            sourcePath,
            fallbackType: currentCupType,
            allowOpen: showGate,
          }, {
            invalidateLeaderboard: (type) => invalidateCupLeaderboardAfterVocabChange(cupModal && cupModal.classList.contains("is-open"), type),
            openTopLeaderboard: (type, response) => openCupLeaderboard({
              scope: "day",
              type,
              pendingUser: response && response.space_leaderboard && response.space_leaderboard.viewer_delta,
            }),
          });
          // 2026-07-29: A normal Space_V completion already persists its compact
          // delta server-side; refresh the registry only when the response
          // actually carries vocabulary mutations that need rendering.
          if (result.payload && result.payload.vocabulary) {
            invalidateCupLeaderboardAfterVocabChange(true, "space_v");
            void loadVocabRegistry(true);
          }
          return result.payload || {};
        } catch (error) {
          lessonCompletionSent = false;
          completionSyncBusy = false;
          setTtsStatus(`Hoc xong nhung chua gui duoc server: ${error && error.message ? error.message : error}`, true);
          if (showGate && completeMessage) {
            completeMessage.textContent = `Đã hoàn thành bài học, nhưng server chưa xác nhận: ${error && error.message ? error.message : error}`;
          }
          if (showGate) {
            showCompletionGate();
          }
          if (showGate && completeMessage) {
            completeMessage.textContent = `Completed, but the server has not confirmed it yet: ${error && error.message ? error.message : error}`;
          }
          return null;
        }
      };

      // Added 2026-07-29: isolated 18877 probe measures the real completion-to-Top DOM path without manual lesson drills.
      const installIsolatedCompletionDomProbe = () => {
        const params = new URLSearchParams(window.location.search || "");
        const enabled = ["127.0.0.1", "localhost"].includes(window.location.hostname)
          && window.location.port === "18877"
          && params.get("ft_completion_probe") === "1";
        if (!enabled || document.getElementById("ft-node-completion-dom-probe")) return;
        const button = document.createElement("button");
        button.id = "ft-node-completion-dom-probe";
        button.type = "button";
        button.textContent = "Run isolated completion DOM probe";
        button.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:10px 14px;border:2px solid #111;background:#ffd84d;color:#111;font:700 13px sans-serif;";
        const output = document.createElement("output");
        output.id = "ft-node-completion-dom-probe-result";
        output.hidden = true;
        window.__ftNodeCompletionDomProbeReady = () => Boolean(currentAuthUsername && clean(currentLessonSource && currentLessonSource.path));
        window.__ftNodeCompletionDomProbeExit = () => {
          if (typeof returnToServerFileSelection === "function") {
            returnToServerFileSelection({});
            return true;
          }
          return false;
        };
        button.addEventListener("click", async () => {
          if (button.disabled) return;
          button.disabled = true;
          const started = performance.now();
          const originalFetch = window.fetch;
          const topRequests = [];
          window.fetch = async (...args) => {
            const requestUrl = clean(typeof args[0] === "string" ? args[0] : (args[0] && args[0].url));
            const response = await originalFetch(...args);
            if (/\/vocab\/leaderboard(?:\?|$)/i.test(requestUrl) && !/\/chat(?:\?|$)/i.test(requestUrl)) {
              topRequests.push({
                url: requestUrl,
                response_ms: Number((performance.now() - started).toFixed(3)),
                response_bytes: Math.max(0, Number(response.headers.get("content-length") || 0)),
                status: response.status,
              });
            }
            return response;
          };
          try {
            const sourcePath = clean(currentLessonSource && currentLessonSource.path);
            if (!currentAuthUsername || !sourcePath) throw new Error("Open an authenticated lesson first.");
            const payload = await reportLessonCompleted("isolated_dom_probe", {
              forceNewCompletion: true,
              completionRunIdOverride: `dom-probe-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
            });
            const completionResponseMs = performance.now() - started;
            if (!payload) throw new Error("Completion did not return a payload.");
            const deadline = performance.now() + 10000;
            let modalText = "";
            let topDataVisible = false;
            while (performance.now() < deadline) {
              modalText = cupModal && cupModal.classList.contains("is-open") ? clean(cupModal.textContent || "") : "";
              topDataVisible = Boolean(modalText && !/Scanning top|Loading/i.test(modalText) && /points|ranked by/i.test(modalText));
              if (topDataVisible) break;
              await new Promise((resolve) => window.setTimeout(resolve, 20));
            }
            const modalOpen = Boolean(cupModal && cupModal.classList.contains("is-open"));
            modalText = modalOpen ? clean(cupModal.textContent || "") : modalText;
            const result = {
              ok: modalOpen && topDataVisible,
              username: clean(currentAuthUsername),
              source_path: sourcePath,
              board_type: clean(payload.leaderboard_type || (payload.space_leaderboard || {}).type || currentCupType),
              completion_response_ms: Number(completionResponseMs.toFixed(3)),
              completion_to_top_api_ms: topRequests.length ? topRequests[0].response_ms : 0,
              completion_to_top_dom_ms: Number((performance.now() - started).toFixed(3)),
              top_response_bytes: topRequests.reduce((total, row) => total + row.response_bytes, 0),
              top_requests: topRequests,
              modal_open: modalOpen,
              top_data_visible: topDataVisible,
              user_visible: modalText.toLowerCase().includes(clean(currentAuthUsername).toLowerCase()),
              modal_text: modalText.slice(0, 1200),
            };
            window.__ftNodeCompletionDomProbeResult = result;
            output.value = JSON.stringify(result);
            output.textContent = output.value;
            output.dataset.ready = "1";
            button.textContent = modalOpen ? "DOM probe complete" : "DOM probe timed out";
          } catch (error) {
            window.__ftNodeCompletionDomProbeResult = { ok: false, error: clean(error && error.message ? error.message : error) };
            output.value = JSON.stringify(window.__ftNodeCompletionDomProbeResult);
            output.textContent = output.value;
            output.dataset.ready = "1";
            button.textContent = "DOM probe failed";
          } finally {
            window.fetch = originalFetch;
            button.disabled = false;
          }
        });
        document.body.append(button, output);
      };
      window.setTimeout(installIsolatedCompletionDomProbe, 0);

      const enterLessonPayloadNow = (payload, selectedVoiceValue = "", options = {}) => {
        hideActiveLessonSurfaceForLoad("Opening selected lesson...");
        installIsolatedCompletionDomProbe();
        updateFutureAppRoute(routeForLessonPayload(payload));
        startLessonStudyTimeHeartbeat();
        if (isVocabularyPayload(payload)) {
          resetSpaceWCache();
          void enterVocabularyPayloadNow(payload, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_V.", true);
          });
          return;
        }
        if (isQuestionPayload(payload)) {
          resetSpaceWCache();
          void enterQuestionPayloadNow(payload, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_Q.", true);
          });
          return;
        }
        if (isParagraphPayload(payload)) {
          resetSpaceWCache();
          if (shouldRunSpaceWVocabPreflight(payload) && !options.allowDuringVocabBuild) {
            void runSpaceWVocabPreflight(payload, "", options);
            return;
          }
          void enterParagraphPayloadNow(payload, options).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not open Space_P.", true);
          });
          return;
        }
        if (shouldRunSpaceWVocabPreflight(payload) && !options.allowDuringVocabBuild) {
          void runSpaceWVocabPreflight(payload, selectedVoiceValue, options);
          return;
        }
        void startTranslationLessonPayload(payload, selectedVoiceValue, options).catch((error) => {
          setLoadStatus(error && error.message ? error.message : "Could not open Space_W.", true);
        });
      };

      const updateCompletionGate = (study = null) => {
        const currentStudy = study && typeof study === "object"
          ? study
          : (currentLessonSource && currentLessonSource.study && typeof currentLessonSource.study === "object" ? currentLessonSource.study : {});
        if (completeLessonNode) {
          completeLessonNode.textContent = clean(currentLessonSource.title || currentLessonSource.name || "Future lesson");
        }
        if (completeNodesNode) {
          completeNodesNode.textContent = String(lessonNodes.length || 0);
        }
        if (completeRunsNode) {
          const mine = Number(currentStudy.mine || 0) || 0;
          completeRunsNode.textContent = mine ? `${mine} lần` : (lessonCompletionSent ? "Synced" : "Syncing");
        }
        if (completeRunsNode && completionSyncBusy) {
          completeRunsNode.textContent = "Syncing";
        }
        if (completeMessage) {
          const total = Number(currentStudy.total || 0) || 0;
          completeMessage.textContent = total
            ? `AI đã ghi nhận tiến độ. Tổng lượt hoàn thành của file này: ${total}.`
            : "AI đã ghi nhận bạn hoàn thành bài học. Trạng thái đang được đồng bộ với server.";
        }
        renderCompletionCrystalSummary();
      };

      const showCompletionGate = () => {
        if (!completeGate) {
          return;
        }
        dismissSoftKeyboard();
        updateCompletionGate();
        completeGate.hidden = false;
        completeGate.setAttribute("tabindex", "-1");
        renderCompletionCrystalSummary();
        if (authToken) {
          void loadQuestionInventory().then(() => {
            if (completeGate && !completeGate.hidden) {
              renderCompletionCrystalSummary();
            }
          }).catch(() => {});
        }
        window.setTimeout(() => {
          try {
            completeGate.focus({ preventScroll: true });
          } catch (error) {
          }
        }, 30);
      };

      const hideCompletionGate = () => {
        if (completeGate) {
          completeGate.hidden = true;
        }
      };

      const hideActiveLessonSurfaceForLoad = (message = "") => {
        stopLessonStudyTimeHeartbeat();
        spaceWLoadDecisionToken += 1;
        vocabLoadDecisionToken += 1;
        questionLoadDecisionToken += 1;
        paragraphLoadDecisionToken += 1;
        hideCompletionGate();
        vocabAnswerAudioToken += 1;
        stopActiveAudio();
        stopVocabMeaningAudio();
        stopQuestionTyping();
        stopQuestionAudio();
        resetParagraphMode({ keepPending: true });
        resetPdfMode();
        hideVocabModePopup();
        clearVocabHintTimers();
        setVocabKeyboardLock(false);
        hideVocabPreflightGate();
        hideSpeakPanel();
        hideHintPanel();
        hideAboutPanel({ resetUnlock: true });
        hideScorePanel(true);
        hideGrammarQuiz(false, true);
        clearAllConnectors();
        hideQuestionCards();
        hideVocabSideCards();
        spaceWSpeakSkipSessionApproved = false;
        spaceWSpeakSkipSessionId = createSpaceWSpeakSkipSessionId();
        if (cardNode) {
          cardNode.classList.add("is-hidden");
        }
        if (vocabCard) {
          vocabCard.classList.add("is-hidden");
        }
        if (qRootCard) {
          qRootCard.classList.add("is-hidden");
        }
        setSpaceWModeClass(false);
        currentNode = null;
        questionCurrentNode = null;
        if (vocabUnlearnedPanel) {
          vocabUnlearnedPanel.classList.add("is-hidden");
        }
        if (vocabLearnedPanel) {
          vocabLearnedPanel.classList.add("is-hidden");
        }
        if (vocabWeakConnector) {
          vocabWeakConnector.classList.add("is-hidden");
        }
        if (vocabLearnedConnector) {
          vocabLearnedConnector.classList.add("is-hidden");
        }
        if (loadGate) {
          loadGate.classList.remove("is-hidden");
          loadGate.classList.remove("is-file-ready");
        }
        if (message) {
          setLoadStatus(message);
        }
        updateLoadEnterNowButton();
      };

      const restartCurrentLessonFromBeginning = () => {
        hideCompletionGate();
        vocabModeTransitioning = false;
        hideVocabModePopup();
        clearVocabHintTimers();
        if (vocabModeActive && vocabItems.length) {
          vocabQueue = shuffleIndexes(vocabItems.length);
          vocabBatch = [];
          vocabRoundQueue = [];
          vocabCurrentIndex = -1;
          vocabCurrentHadError = false;
          vocabLearnedKeys = new Set();
          vocabAttemptCounts = new Map();
          vocabStudyIndexes = [];
          vocabStudyKeys = new Set();
          vocabPhase = "probe";
          vocabDrillIndex = 0;
          vocabDrillCorrectCount = 0;
          vocabDrillFailCount = 0;
          vocabShuffleOriginal = [];
          vocabShuffleRound = 0;
          vocabShuffleQueue = [];
          vocabShuffleCorrectCount = 0;
          vocabShuffleFailCount = 0;
          lessonCompletionSent = false;
          completionSyncBusy = false;
          if (cardNode) {
            cardNode.classList.add("is-hidden");
          }
          if (vocabCard) {
            vocabCard.classList.remove("is-hidden");
          }
          renderVocabUnlearnedList();
          startNextVocabProbe();
          return;
        }
        if (questionModeActive && questionPayload && questionNodes.length) {
          questionQueue = questionPayload.order === "shuffle" ? shuffleIndexes(questionNodes.length) : questionNodes.map((_node, index) => index);
          questionNodePointer = 0;
          questionCurrentNode = null;
          questionCurrentQuestions = [];
          questionCurrentQuestionOrder = [];
          questionQuestionIndex = 0;
          questionWrongAttempts = 0;
          resetQuestionAttemptRewardState();
          lessonCompletionSent = false;
          completionSyncBusy = false;
          if (cardNode) {
            cardNode.classList.add("is-hidden");
          }
          if (vocabCard) {
            vocabCard.classList.add("is-hidden");
          }
          if (qRootCard) {
            qRootCard.classList.remove("is-hidden");
          }
          hideQuestionCards();
          clearQuestionAdvanceTimer();
          stopQuestionTyping();
          stopQuestionAudio();
          showNextQuestionNode();
          return;
        }
        if (!lessonNodes.length) {
          return;
        }
        reviewModeActive = false;
        reviewQueue = [];
        reviewMasteredIndexes = new Set();
        reviewCurrentHadError = false;
        reviewSpeakCompleted = false;
        reviewFinished = false;
        lessonCompletionSent = false;
        completionSyncBusy = false;
        setNode(lessonNodes[0], 0);
      };

      const lessonVaultProgressPins = new Map();
      const lessonVaultTimePins = new Map();
      const SPACE_V_LOCAL_PROGRESS_PROTECT_MS = 300000;

      // Added 2026-06-30: remembers the just-saved progress ring across Lesson Vault list rerenders.
      const rememberLessonVaultProgressPin = (paths = [], progress = null, ttlMs = 120000) => {
        if (!progress || typeof progress !== "object") {
          return;
        }
        const expiresAt = Date.now() + Math.max(5000, Number(ttlMs || 0) || 120000);
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = normalizeTaskPath(normalizeServerPathValue(path || ""));
          if (key) {
            const existing = lessonVaultProgressPins.get(key);
            if (typeof shouldKeepExistingLessonProgressOverride === "function" && shouldKeepExistingLessonProgressOverride(existing, progress)) {
              return;
            }
            lessonVaultProgressPins.set(key, { progress: { ...progress }, expiresAt });
          }
        });
      };

      const lessonVaultProgressPinForPaths = (paths = []) => {
        const now = Date.now();
        for (const [key, row] of Array.from(lessonVaultProgressPins.entries())) {
          if (!row || Number(row.expiresAt || 0) < now) {
            lessonVaultProgressPins.delete(key);
          }
        }
        for (const path of (Array.isArray(paths) ? paths : [paths])) {
          const key = normalizeTaskPath(normalizeServerPathValue(path || ""));
          const row = key ? lessonVaultProgressPins.get(key) : null;
          if (row && row.progress) {
            return row.progress;
          }
        }
        return null;
      };

      // Added 2026-07-03: lets Back render from the fresh server payload instead of a protected local Space_V pin.
      const clearLessonVaultProgressPin = (paths = []) => {
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = normalizeTaskPath(normalizeServerPathValue(path || ""));
          if (key) {
            lessonVaultProgressPins.delete(key);
          }
        });
      };

      // Added 2026-07-26: keeps freshly credited lesson time visible until server payload refresh catches up.
      const rememberLessonVaultTimePin = (paths = [], time = null, ttlMs = 120000) => {
        if (!time || typeof time !== "object") {
          return;
        }
        const expiresAt = Date.now() + Math.max(5000, Number(ttlMs || 0) || 120000);
        (Array.isArray(paths) ? paths : [paths]).forEach((path) => {
          const key = normalizeTaskPath(normalizeServerPathValue(path || ""));
          if (key) {
            lessonVaultTimePins.set(key, { time: { ...time }, expiresAt });
          }
        });
      };

      const lessonVaultTimePinForPaths = (paths = []) => {
        const now = Date.now();
        for (const [key, row] of Array.from(lessonVaultTimePins.entries())) {
          if (!row || Number(row.expiresAt || 0) < now) {
            lessonVaultTimePins.delete(key);
          }
        }
        for (const path of (Array.isArray(paths) ? paths : [paths])) {
          const key = normalizeTaskPath(normalizeServerPathValue(path || ""));
          const row = key ? lessonVaultTimePins.get(key) : null;
          if (row && row.time) {
            return row.time;
          }
        }
        return null;
      };

      // Added 2026-06-30: pins the just-saved progress ring after Lesson Vault refreshes replace the visible row.
      const pinVisibleLessonVaultProgressRing = (paths = [], progress = null, options = {}) => {
        if (!serverListNode || !progress || typeof progress !== "object") {
          return false;
        }
        rememberLessonVaultProgressPin(paths, progress);
        const wantedPaths = new Set((Array.isArray(paths) ? paths : [paths])
          .map((path) => normalizeTaskPath(normalizeServerPathValue(path || "")))
          .filter(Boolean));
        if (!wantedPaths.size) {
          return false;
        }
        let updated = false;
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file")).forEach((item) => {
          const itemPaths = [
            item.dataset.path || "",
            item.dataset.effectivePath || "",
            item.dataset.linkTarget || "",
            item.dataset.linkedPath || "",
            item.dataset.sourcePath || "",
            item.dataset.originalPath || "",
          ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
          if (!itemPaths.some((pathValue) => wantedPaths.has(pathValue))) {
            return;
          }
          const iconColumn = item.querySelector(".ft-server-icon-column");
          if (!iconColumn) {
            return;
          }
          Array.from(iconColumn.children).forEach((child) => {
            if (child && child.classList && child.classList.contains("ft-vault-progress") && !child.classList.contains("ft-vault-progress-admin")) {
              child.remove();
            }
          });
          const progressNode = createLessonProgressNode({}, "ft-vault-progress", { progress });
          if (!progressNode) {
            return;
          }
          iconColumn.appendChild(progressNode);
          item.classList.add("has-progress");
          updated = true;
        });
        const retryMs = Math.max(0, Number(options.retryMs || 0) || 0);
        if (!updated && retryMs) {
          window.setTimeout(() => {
            pinVisibleLessonVaultProgressRing(paths, progress);
          }, retryMs);
        }
        return updated;
      };

      // Added 2026-07-26: refreshes the visible Time chip after a /lesson/time acknowledgement.
      const pinVisibleLessonVaultTimeChip = (paths = [], time = null, options = {}) => {
        if (!serverListNode || !time || typeof time !== "object") {
          return false;
        }
        rememberLessonVaultTimePin(paths, time, Number(options.ttlMs || 0) || 120000);
        const wantedPaths = new Set((Array.isArray(paths) ? paths : [paths])
          .map((path) => normalizeTaskPath(normalizeServerPathValue(path || "")))
          .filter(Boolean));
        if (!wantedPaths.size) {
          return false;
        }
        let updated = false;
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file")).forEach((item) => {
          const itemPaths = [
            item.dataset.path || "",
            item.dataset.effectivePath || "",
            item.dataset.linkTarget || "",
            item.dataset.linkedPath || "",
            item.dataset.sourcePath || "",
            item.dataset.originalPath || "",
          ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
          if (!itemPaths.some((pathValue) => wantedPaths.has(pathValue))) {
            return;
          }
          const chipRow = item.querySelector(".ft-server-chip-row");
          if (!chipRow) {
            return;
          }
          Array.from(chipRow.querySelectorAll(".ft-server-chip.is-time")).forEach((chip) => chip.remove());
          const seconds = Number(time.seconds || time.time_seconds || 0) || 0;
          const label = formatStudyDuration(seconds);
          if (label) {
            chipRow.appendChild(createServerChip(`Time ${label}`, "time"));
            updated = true;
          }
        });
        const retryMs = Math.max(0, Number(options.retryMs || 0) || 0);
        if (!updated && retryMs) {
          window.setTimeout(() => {
            pinVisibleLessonVaultTimeChip(paths, time, { ...options, retryMs: 0 });
          }, retryMs);
        }
        return updated;
      };

      // Exit leaves an active Space; callers must flush the latest progress before this clears runtime state.
      const returnToServerFileSelection = (options = {}) => {
        const completedBeforeReturn = Boolean(lessonCompletionSent);
        const returnLessonPath = currentLessonStudyPath();
        const returnLessonTree = normalizeServerPathValue(returnLessonPath ? serverParentPathForFile(returnLessonPath) : (serverBrowserPath || getStoredServerPath() || ""));
        const returnTaskOwner = clean(serverTaskOwnerContext || currentAuthUsername || "");
        const vocabProgressRecordForReturn = options.vocabProgressRecord && typeof options.vocabProgressRecord === "object"
          ? options.vocabProgressRecord
          : (vocabModeActive && currentVocabProgressCache.savedProgress && typeof currentVocabProgressCache.savedProgress === "object"
            ? currentVocabProgressCache.savedProgress
            : null);
        const spaceWProgressRecordForReturn = !vocabModeActive && !questionModeActive && !paragraphModeActive && typeof saveSpaceWProgressNow === "function"
          ? saveSpaceWProgressNow()
          : null;
        const questionProgressRecordForReturn = questionModeActive ? saveQuestionProgressNow() : null;
        const paragraphProgressRecordForReturn = paragraphModeActive ? saveParagraphProgressNow() : null;
        const returnProgressPaths = [
          returnLessonPath,
          vocabServerPathFromRecord(vocabProgressRecordForReturn),
          typeof currentSpaceWServerPath === "function" ? currentSpaceWServerPath() : "",
          ...(paragraphProgressRecordForReturn && typeof currentParagraphProgressPaths === "function" ? currentParagraphProgressPaths(paragraphProgressRecordForReturn) : []),
          currentLessonSource && currentLessonSource.linked_path,
          currentLessonSource && currentLessonSource.path,
          currentLessonSource && currentLessonSource.effective_path,
          currentLessonSource && currentLessonSource.link_target,
        ];
        let vocabProgressOverrideForReturn = vocabProgressOverrideFromRecord(vocabProgressRecordForReturn);
        if (completedBeforeReturn && vocabProgressOverrideForReturn && vocabProgressOverrideForReturn.space === "Space_V") {
          const total = Math.max(0, Math.floor(Number(vocabProgressOverrideForReturn.total || vocabProgressOverrideForReturn.done || 0) || 0));
          if (total) {
            vocabProgressOverrideForReturn = {
              ...vocabProgressOverrideForReturn,
              done: total,
              total,
              percent: 100,
              text: `${total}/${total}`,
              completed: true,
              complete: true,
              in_progress: false,
              syncing: true,
            };
          }
        }
        if (returnLessonPath && vocabProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, vocabProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS, { force: true });
          rememberLessonVaultProgressPin(returnProgressPaths, vocabProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
          clearServerLessonProgressPrefetchCache(returnProgressPaths, "Space_V");
        }
        const spaceWProgressOverrideForReturn = spaceWProgressOverrideFromRecord(spaceWProgressRecordForReturn);
        if (returnLessonPath && spaceWProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, spaceWProgressOverrideForReturn, 120000);
          rememberLessonVaultProgressPin(returnProgressPaths, spaceWProgressOverrideForReturn, 120000);
        }
        const questionProgressOverrideForReturn = questionProgressOverrideFromRecord(questionProgressRecordForReturn);
        if (returnLessonPath && questionProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, questionProgressOverrideForReturn, 24000);
        }
        const paragraphProgressOverrideForReturn = paragraphProgressOverrideFromRecord(paragraphProgressRecordForReturn);
        if (returnLessonPath && paragraphProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, paragraphProgressOverrideForReturn, 120000);
          rememberLessonVaultProgressPin(returnProgressPaths, paragraphProgressOverrideForReturn, 120000);
        }
        const localProgressOverrideForReturn = vocabProgressOverrideForReturn || spaceWProgressOverrideForReturn || questionProgressOverrideForReturn || paragraphProgressOverrideForReturn;
        const vocabProgressSyncForReturn = Promise.resolve(null);
        const questionProgressSyncForReturn = questionProgressRecordForReturn && canUseQuestionProgressServer()
          ? sendQuestionServerProgress(questionProgressRecordForReturn).catch(() => null)
          : Promise.resolve(null);
        pendingTaskNoticeReturnTrigger = {
          id: ++taskNoticeReturnTriggerId,
          completedReturn: completedBeforeReturn,
        };
        if (paragraphModeActive) {
          resetParagraphMode();
        }
        hideCompletionGate();
        stopLessonStudyTimeHeartbeat();
        vocabAnswerAudioToken += 1;
        stopActiveAudio();
        stopVocabMeaningAudio();
        vocabModeTransitioning = false;
        hideVocabModePopup();
        clearVocabHintTimers();
        resetPdfMode();
        hideSpeakPanel();
        hideHintPanel();
        hideAboutPanel({ resetUnlock: true });
        hideScorePanel(true);
        hideGrammarQuiz(false, true);
        clearAllConnectors();
        mobileUnlockedPanels.clear();
        mobileActivePanelKey = "";
        syncMobilePanelTabs();
        reviewModeActive = false;
        reviewFinished = false;
        reviewQueue = [];
        reviewMasteredIndexes = new Set();
        pendingLessonNodes = [];
        pendingLessonEffects = {};
        pendingVocabularyPayload = null;
        resetQuestionMode();
        pendingSpaceWAfterVocabulary = null;
        currentVocabularyMission = null;
        vocabPreflightState = null;
        resetVocabPreflightSessionMemory();
        hideVocabPreflightGate();
        lessonNodes = [];
        vocabModeActive = false;
        setVocabKeyboardLock(false);
        vocabItems = [];
        clearVocabAudioCache();
        vocabQueue = [];
        vocabBatch = [];
        vocabRoundQueue = [];
        vocabLearnedKeys = new Set();
        vocabAttemptCounts = new Map();
        vocabStudyIndexes = [];
        vocabStudyKeys = new Set();
        vocabPhase = "probe";
        vocabShuffleOriginal = [];
        vocabShuffleQueue = [];
        currentNode = null;
        lessonCompletionSent = false;
        completionSyncBusy = false;
        vocabCompletionFinalizing = false;
        vocabReviewRunActive = false;
        currentLessonSource = { source: "", path: "", name: "", title: "", study: null };
        resetSpaceWCache();
        if (vocabCard) {
          vocabCard.classList.add("is-hidden");
        }
        renderVocabUnlearnedList();
        hideVocabSideCards();
        if (cardNode) {
          cardNode.classList.add("is-hidden");
        }
        loadGate.classList.remove("is-hidden", "is-file-ready");
        setLoadStatus("Chọn bài học khác trong lesson vault.");
        if (returnLessonTree) {
          rememberServerPath(returnLessonTree);
        }
        if (returnLessonPath) {
          // Keep the exact completed lesson focused while the parent tree is rehydrated.
          serverBrowserFocusedFilePath = normalizeServerPathValue(returnLessonPath);
          rememberServerFile(returnLessonPath);
        }
            const refreshTree = returnLessonTree || serverBrowserPath || getStoredServerPath() || "";
            if (refreshTree) {
              const forceFreshProgress = Boolean(options.forceFreshProgress || completedBeforeReturn);
              const hasReturnFolderCache = typeof getCachedServerBrowserListRow === "function"
                && !forceFreshProgress
                && Boolean(getCachedServerBrowserListRow(refreshTree, returnTaskOwner, { allowStale: true }));
            updateFutureAppRoute("lesson_vault", {
              tree: refreshTree,
              task_owner: returnTaskOwner,
              replace: true,
            });
            setServerBrowserPanel("vault");
            // Back performs one route/load. A cached origin folder stays entirely local; a direct-open cache miss fetches it once.
              void loadServerDataPath(refreshTree, false, returnTaskOwner, {
                silent: true,
                fresh: forceFreshProgress,
              hydrateTaskBoardNow: false,
            skipTaskBoardHydrate: true,
              skipRouteLeaveFlush: true,
              skipBackgroundVerify: true,
              skipChildPrefetch: true,
              localCacheOnly: hasReturnFolderCache,
                source: forceFreshProgress ? "space_v_exit_progress_refresh" : (hasReturnFolderCache ? "space_v_group_back_cache" : "space_v_group_back_cache_miss"),
            })
            .then((payload) => {
              if (localProgressOverrideForReturn) {
                setLessonProgressOverride(returnProgressPaths, localProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS, { force: true });
                rememberLessonVaultProgressPin(returnProgressPaths, localProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
              }
              if (typeof selectServerLessonVaultEntryFromPayload === "function") {
                selectServerLessonVaultEntryFromPayload(payload || { entries: serverCurrentEntries || [] }, returnProgressPaths, {
                  progress: localProgressOverrideForReturn,
                    retryMs: 160,
                    skipProgressPrefetch: true,
                    skipFileStats: true,
                    rememberFile: false,
                    updateRoute: false,
                });
              }
              pinVisibleLessonVaultProgressRing(returnProgressPaths, localProgressOverrideForReturn, { retryMs: 160 });
            })
            .catch(() => {});
        }
        void Promise.allSettled([vocabProgressSyncForReturn, questionProgressSyncForReturn]).then(async () => {
          if (refreshTree && (vocabProgressRecordForReturn || spaceWProgressRecordForReturn || questionProgressRecordForReturn || paragraphProgressRecordForReturn)) {
            // Updated 2026-07-15: return-to-vault keeps local progress pins and does not issue item-study GETs.
            if (typeof selectServerLessonVaultEntryFromPayload === "function") {
              selectServerLessonVaultEntryFromPayload({ entries: serverCurrentEntries || [] }, returnProgressPaths, {
                progress: localProgressOverrideForReturn,
                  retryMs: 180,
                  skipProgressPrefetch: true,
                  skipFileStats: true,
                  rememberFile: false,
                  updateRoute: false,
              });
            }
            pinVisibleLessonVaultProgressRing(returnProgressPaths, localProgressOverrideForReturn, { retryMs: 180 });
          }
          if (!localProgressOverrideForReturn) {
            clearLessonProgressOverride(returnProgressPaths);
          }
          if (returnTaskOwner && completedBeforeReturn) {
            await loadLessonTasks(returnTaskOwner, { localCacheOnly: true }).catch(() => {});
            if (typeof selectServerLessonVaultEntryFromPayload === "function") {
              selectServerLessonVaultEntryFromPayload({ entries: serverCurrentEntries || [] }, returnProgressPaths, {
                progress: localProgressOverrideForReturn,
                  retryMs: 220,
                  skipProgressPrefetch: true,
                  skipFileStats: true,
                  rememberFile: false,
                  updateRoute: false,
              });
            }
            pinVisibleLessonVaultProgressRing(returnProgressPaths, localProgressOverrideForReturn, { retryMs: 220 });
          }
        });
      };

      const setServerBrowserLoading = (message) => {
        if (!serverListNode) {
          return;
        }
        serverListNode.textContent = "";
        const empty = document.createElement("div");
        empty.className = "ft-server-empty";
        empty.textContent = message;
        serverListNode.appendChild(empty);
      };

      const serverDisplayPathLabel = (relativePath = "") => {
        const pathValue = normalizeServerPathValue(relativePath || "");
        const cleanParts = pathValue.split("/").filter(Boolean).map((part) => (
          typeof futureFriendlyDisplayName === "function"
            ? futureFriendlyDisplayName(part, { keepExtension: true })
            : clean(part)
        ));
        return `QM-Home${cleanParts.length ? " > " + cleanParts.join(" > ") : ""}`;
      };

      const setServerBrowserPathLabel = (relativePath = "") => {
        if (!serverPathNode) {
          return;
        }
        const pathValue = normalizeServerPathValue(relativePath || "");
        const rawParts = pathValue.split("/").filter(Boolean);
        const parts = ["QM-Home", ...rawParts.map((part) => (
          typeof futureFriendlyDisplayName === "function"
            ? futureFriendlyDisplayName(part, { keepExtension: true })
            : clean(part)
        ))];
        const fullLabel = serverDisplayPathLabel(pathValue);
        serverPathNode.dataset.path = pathValue;
        const createPathBlock = (part, index, visualIndex, options = {}) => {
          const targetPath = index === 0 ? "" : rawParts.slice(0, index).join("/");
          const block = document.createElement("button");
          block.type = "button";
          block.className = [
            "ft-server-path-block",
            index === 0 ? "is-root" : "",
            options.ellipsis ? "is-ellipsis" : "",
          ].filter(Boolean).join(" ");
          block.dataset.path = options.ellipsis ? "" : targetPath;
          block.style.setProperty("--path-i", String(visualIndex));
          block.textContent = part;
          block.title = options.ellipsis
            ? `Show full route: ${fullLabel}`
            : (index === 0 ? "Open QM-Home" : `Open ${part}`);
          block.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (options.ellipsis) {
              renderPathBlocks(false, true);
              setLoadStatus("Full Lesson Vault route expanded.");
              return;
            }
            // Route immediately. loadServerDataPath supersedes any in-flight
            // load (serial + AbortController), so fast repeated breadcrumb
            // clicks no longer stack delays or time out. The is-routing flag is
            // purely visual and always clears when the load settles, so a block
            // can never get stuck as a dead button.
            block.classList.add("is-routing");
            setLoadStatus(`Routing to ${serverDisplayPathLabel(targetPath)}...`);
            const targetOwner = typeof lessonVaultTaskOwnerForPath === "function"
              ? lessonVaultTaskOwnerForPath(targetPath, targetPath ? serverTaskOwnerContext : "")
              : (targetPath ? serverTaskOwnerContext : clean(currentAuthUsername || ""));
            const hasLocalBreadcrumbPayload = typeof getCachedServerBrowserListRow === "function"
              && Boolean(getCachedServerBrowserListRow(targetPath, targetOwner, { allowStale: true }));
            const taskFocusRouteActive = Number(window.__ftLessonVaultLocalRouteUntil || 0) > Date.now();
            if (hasLocalBreadcrumbPayload) {
              window.__ftLessonVaultLocalRouteUntil = Math.max(Number(window.__ftLessonVaultLocalRouteUntil || 0), Date.now() + 2500);
            } else if (!taskFocusRouteActive) {
              window.__ftLessonVaultLocalRouteUntil = 0;
            }
            if (typeof rememberLessonVaultFolder === "function") {
              rememberLessonVaultFolder(targetPath, targetOwner, "breadcrumb");
            }
            Promise.resolve(
              loadServerDataPath(targetPath, false, targetOwner, {
                // Added 2026-07-15: breadcrumb clicks use local cache only when that branch is actually cached; otherwise fetch once and cache it.
                skipBackgroundVerify: true,
                skipChildPrefetch: true,
                skipTaskBoardHydrate: true,
                skipRouteLeaveFlush: true,
                localCacheOnly: hasLocalBreadcrumbPayload,
                source: hasLocalBreadcrumbPayload ? "lesson_vault_breadcrumb_click" : "lesson_vault_breadcrumb_cache_miss",
              })
            ).catch(() => {}).finally(() => {
              block.classList.remove("is-routing");
            });
          });
          serverPathNode.appendChild(block);
        };
        const renderPathBlocks = (collapsed = false, expanded = false) => {
          serverPathNode.textContent = "";
          serverPathNode.classList.toggle("is-collapsed", Boolean(collapsed && !expanded));
          if (collapsed && !expanded && parts.length > 4) {
            createPathBlock(parts[0], 0, 0);
            createPathBlock("...", 1, 1, { ellipsis: true });
            const tailStart = Math.max(1, parts.length - 2);
            parts.slice(tailStart).forEach((part, offset) => {
              const realIndex = tailStart + offset;
              createPathBlock(part, realIndex, offset + 2);
            });
            return;
          }
          parts.forEach((part, index) => createPathBlock(part, index, index));
        };
        const collapseByCount = parts.length > 6;
        renderPathBlocks(collapseByCount);
        if (!collapseByCount && parts.length > 3) {
          window.requestAnimationFrame(() => {
            if (!serverPathNode || serverPathNode.dataset.path !== pathValue || serverPathNode.classList.contains("is-collapsed")) {
              return;
            }
            const styles = window.getComputedStyle(serverPathNode);
            const lineHeight = Number.parseFloat(styles.lineHeight) || 16;
            const padding = (Number.parseFloat(styles.paddingTop) || 0) + (Number.parseFloat(styles.paddingBottom) || 0);
            if (serverPathNode.scrollHeight > (lineHeight * 3) + padding + 4) {
              renderPathBlocks(true);
            }
          });
        }
        serverPathNode.setAttribute("aria-label", fullLabel);
      };

      // Added 2026-07-09, updated 2026-07-11: keeps admin/user Space Task owner tied to the visible Lesson Vault route.
      function lessonVaultTaskOwnerForPath(pathValue = "", explicitOwner = "", payload = null) {
        const explicit = clean(explicitOwner || "");
        const normalizedPath = normalizeTaskPath(normalizeServerPathValue(pathValue || ""));
        const adminUser = clean(currentAuthUsername || (payload && payload.username) || "");
        if (currentAuthIsAdmin && adminUser) {
          const topFolder = clean((normalizedPath.split("/").filter(Boolean)[0] || ""));
          const contextOwner = clean(serverTaskOwnerContext || "");
          if (!normalizedPath) {
            return adminUser;
          }
          if (topFolder && authUsernameMatches(topFolder, adminUser)) {
            return adminUser;
          }
          if (normalizedPath === "common" || topFolder.toLowerCase() === "common") {
            const commonOwner = clean(explicit || contextOwner || "");
            if (commonOwner && !authUsernameMatches(commonOwner, adminUser)) {
              return commonOwner;
            }
            return adminUser;
          }
          if (topFolder && contextOwner && authUsernameMatches(topFolder, contextOwner)) {
            return contextOwner;
          }
          // Added 2026-07-23: compact tree rows created for the admin can carry
          // the viewer as owner; the selected top-level user folder is authoritative.
          if (
            topFolder
            && !authUsernameMatches(topFolder, adminUser)
            && (
              (explicit && authUsernameMatches(explicit, adminUser))
              || (contextOwner && authUsernameMatches(contextOwner, adminUser))
            )
          ) {
            return topFolder;
          }
          if (explicit) {
            return explicit;
          }
        } else {
          if (explicit) {
            return explicit;
          }
          // Non-admin tree-preload rows are keyed by the signed-in owner, including QM-Home.
          // Returning an empty owner here made every root breadcrumb click miss that hot cache.
          return clean((payload && payload.username) || currentAuthUsername || "");
        }
        if (payload && !payload.admin) {
          return clean(payload.username || currentAuthUsername || "");
        }
        return "";
      }

      // Home navigates only within Lesson Vault (parent folder/QM-Home); it is not the Space Exit action.
      const setServerBrowserBackControl = (relativePath = "", parentPath = "", taskOwner = "") => {
        const currentPath = normalizeServerPathValue(relativePath || "");
        if (!serverNavNode || !serverBackButton) {
          return;
        }
        const hasRecentFile = renderServerRecentFileShortcut();
        if (!currentPath) {
          serverBackButton.hidden = true;
          serverBackButton.onclick = null;
          serverNavNode.hidden = !hasRecentFile;
          return;
        }
        const targetParent = normalizeServerPathValue(parentPath || serverParentPathForFile(currentPath));
        const owner = targetParent && typeof lessonVaultTaskOwnerForPath === "function"
          ? lessonVaultTaskOwnerForPath(targetParent, taskOwner || "")
          : (targetParent ? clean(taskOwner || "") : "");
        const resolveBackLessonVaultTarget = async () => {
          const fallbackTree = targetParent || "";
          const fallbackOwner = owner || serverTaskOwnerContext || currentAuthUsername || "";
          if (fallbackTree) {
            return {
              tree: fallbackTree,
              task_owner: clean(fallbackOwner || ""),
            };
          }
          if (typeof readStoredLessonVaultFolderState === "function") {
            const storedFolder = await readStoredLessonVaultFolderState(fallbackOwner);
            const storedFolderParent = storedFolder && storedFolder.path
              ? normalizeServerPathValue(serverParentPathForFile(storedFolder.path))
              : "";
            if (storedFolderParent) {
              return {
                tree: storedFolderParent,
                task_owner: clean(storedFolder.task_owner || fallbackOwner || ""),
              };
            }
          } else if (typeof getStoredLessonVaultFolderState === "function") {
            const storedFolder = getStoredLessonVaultFolderState(fallbackOwner);
            const storedFolderParent = storedFolder && storedFolder.path
              ? normalizeServerPathValue(serverParentPathForFile(storedFolder.path))
              : "";
            if (storedFolderParent) {
              return {
                tree: storedFolderParent,
                task_owner: clean(storedFolder.task_owner || fallbackOwner || ""),
              };
            }
          }
          return {
            tree: fallbackTree,
            task_owner: clean(fallbackOwner || ""),
          };
        };
        const initialBackTarget = typeof getStoredLessonVaultFolderState === "function"
          ? getStoredLessonVaultFolderState(serverTaskOwnerContext || currentAuthUsername || "")
          : null;
        const restoredTargetTree = targetParent || (
          initialBackTarget && initialBackTarget.path
            ? normalizeServerPathValue(serverParentPathForFile(initialBackTarget.path))
            : ""
        ) || "";
        const restoredTargetOwner = clean((initialBackTarget && initialBackTarget.task_owner) || owner || serverTaskOwnerContext || currentAuthUsername || "");
        serverNavNode.hidden = false;
        serverBackButton.hidden = false;
        const parentLabel = restoredTargetTree
          ? `Home: ${serverDisplayPathLabel(restoredTargetTree)}`
          : "Home: QM-Home";
        serverBackButton.title = parentLabel;
        serverBackButton.setAttribute("aria-label", `Home to ${restoredTargetTree ? serverDisplayPathLabel(restoredTargetTree) : "QM-Home"}`);
        serverBackButton.onclick = async () => {
          serverBackButton.disabled = true;
          let canNavigateBack = true;
          let backProgressPaths = [currentPath];
          let backProgressOverride = null;
          try {
            const spaceWRecordForBack = typeof saveSpaceWProgressNow === "function" ? saveSpaceWProgressNow() : null;
            if (spaceWRecordForBack && typeof spaceWProgressOverrideFromRecord === "function") {
              backProgressOverride = spaceWProgressOverrideFromRecord(spaceWRecordForBack);
              backProgressPaths = [
                currentPath,
                typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "",
                typeof currentSpaceWServerPath === "function" ? currentSpaceWServerPath() : "",
                currentLessonSource && currentLessonSource.path,
                currentLessonSource && currentLessonSource.effective_path,
                currentLessonSource && currentLessonSource.link_target,
                currentLessonSource && currentLessonSource.linked_path,
              ].filter(Boolean);
            }
            const questionRecordForBack = !backProgressOverride && typeof saveQuestionProgressNow === "function" ? saveQuestionProgressNow() : null;
            if (questionRecordForBack && typeof questionProgressOverrideFromRecord === "function") {
              backProgressOverride = questionProgressOverrideFromRecord(questionRecordForBack);
              backProgressPaths = [
                currentPath,
                typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "",
                typeof currentQuestionServerPath === "function" ? currentQuestionServerPath() : "",
                currentLessonSource && currentLessonSource.path,
                currentLessonSource && currentLessonSource.effective_path,
                currentLessonSource && currentLessonSource.link_target,
                currentLessonSource && currentLessonSource.linked_path,
              ].filter(Boolean);
            }
            const paragraphRecordForBack = !backProgressOverride && typeof saveParagraphProgressNow === "function" ? saveParagraphProgressNow() : null;
            if (paragraphRecordForBack && typeof paragraphProgressOverrideFromRecord === "function") {
              backProgressOverride = paragraphProgressOverrideFromRecord(paragraphRecordForBack);
              backProgressPaths = [
                currentPath,
                ...(typeof currentParagraphProgressPaths === "function" ? currentParagraphProgressPaths(paragraphRecordForBack) : []),
                typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "",
                currentLessonSource && currentLessonSource.path,
                currentLessonSource && currentLessonSource.effective_path,
                currentLessonSource && currentLessonSource.link_target,
                currentLessonSource && currentLessonSource.linked_path,
              ].filter(Boolean);
            }
            if (typeof window.__ftPeekSpaceVProgressBeforeBack === "function") {
              const peekResult = window.__ftPeekSpaceVProgressBeforeBack({ ttlMs: SPACE_V_LOCAL_PROGRESS_PROTECT_MS, setOverride: false });
              if (peekResult && peekResult.progress) {
                backProgressOverride = peekResult.progressOverride || vocabProgressOverrideFromRecord(peekResult.progress);
                backProgressPaths = [currentPath, ...(Array.isArray(peekResult.progressPaths) && peekResult.progressPaths.length
                  ? peekResult.progressPaths
                  : (typeof currentVocabProgressPaths === "function"
                    ? currentVocabProgressPaths(peekResult.progress)
                    : [
                      currentLessonStudyPath(),
                      currentLessonSource && currentLessonSource.path,
                      currentLessonSource && currentLessonSource.effective_path,
                      currentLessonSource && currentLessonSource.link_target,
                      peekResult.path,
                    ]))].filter(Boolean);
              }
            }
            if (typeof window.__ftFlushSpaceVProgressBeforeBack === "function") {
              const flushResult = await window.__ftFlushSpaceVProgressBeforeBack({ notice: true, setOverride: false });
              if (flushResult && flushResult.ok === false) {
                canNavigateBack = false;
              } else if (flushResult && flushResult.progress) {
                backProgressOverride = vocabProgressOverrideFromRecord(flushResult.progress);
                backProgressPaths = [currentPath, ...(typeof currentVocabProgressPaths === "function"
                  ? currentVocabProgressPaths(flushResult.progress)
                  : [
                    currentLessonStudyPath(),
                    currentLessonSource && currentLessonSource.path,
                    currentLessonSource && currentLessonSource.effective_path,
                    currentLessonSource && currentLessonSource.link_target,
                    flushResult.path,
                  ])].filter(Boolean);
              }
            }
          } catch (error) {
            canNavigateBack = false;
            if (typeof setTopOperationStatus === "function") {
              setTopOperationStatus(`Space_V progress save failed: ${error && error.message ? error.message : "unknown error"}`, {
                isError: true,
                autoHideMs: 7000,
              });
            }
          } finally {
            serverBackButton.disabled = false;
          }
          if (!canNavigateBack) {
            return;
          }
          if (typeof window.__ftClearSpaceWOverlaysForRouteLeave === "function") {
            window.__ftClearSpaceWOverlaysForRouteLeave();
          }
          if (!backProgressOverride && backProgressPaths.length && typeof clearLessonProgressOverride === "function") {
            clearLessonProgressOverride(backProgressPaths);
          }
          if (!backProgressOverride) {
            clearLessonVaultProgressPin(backProgressPaths);
          } else {
            setLessonProgressOverride(backProgressPaths, backProgressOverride, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
            rememberLessonVaultProgressPin(backProgressPaths, backProgressOverride, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
          }
          const backTarget = await resolveBackLessonVaultTarget();
          const backTargetTree = backTarget.tree || "";
          const backTargetOwner = clean(backTarget.task_owner || "");
          // Added 2026-07-15: Back should trust the already-updated RAM/browser snapshot.
          // Pulling task hydration, child prefetch, or item-study refresh here makes
          // Server 2 recalculate progress/task indexes for a state it just saved.
          const hasLocalBackPayload = typeof getCachedServerBrowserListRow === "function"
            && Boolean(getCachedServerBrowserListRow(backTargetTree, backTargetOwner, { allowStale: true }));
          loadServerDataPath(backTargetTree, false, backTargetOwner, {
            hydrateTaskBoardNow: false,
            skipTaskBoardHydrate: true,
            skipRouteLeaveFlush: true,
            skipBackgroundVerify: true,
            skipChildPrefetch: true,
            localCacheOnly: hasLocalBackPayload,
            source: hasLocalBackPayload ? "lesson_vault_back_cache" : "lesson_vault_back_cache_miss",
          }).then((payload) => {
            if (typeof selectServerLessonVaultEntryFromPayload === "function") {
              selectServerLessonVaultEntryFromPayload(payload || {}, backProgressPaths, {
                motion: true,
                progress: backProgressOverride,
                retryMs: 180,
                updateRoute: false,
                skipProgressPrefetch: true,
                skipFileStats: true,
              });
            }
            if (typeof rememberLessonVaultFolder === "function" && backTargetTree) {
              rememberLessonVaultFolder(backTargetTree, backTargetOwner, "back_restore");
            }
            if (backProgressOverride) {
              rememberLessonVaultProgressPin(backProgressPaths, backProgressOverride, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
              setLessonProgressOverride(backProgressPaths, backProgressOverride, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
              pinVisibleLessonVaultProgressRing(backProgressPaths, backProgressOverride, { retryMs: 180 });
            }
            // Updated 2026-07-15: Back stays local-only; missing overrides should not trigger item-study GETs.
          }).catch(() => {});
        };
      };

      const showServerBrowserPathError = (relativePath = "", message = "", taskOwnerOverride = "") => {
        serverBrowserPath = normalizeServerPathValue(relativePath || "");
        setServerBrowserPathLabel(serverBrowserPath);
        setServerBrowserLoading(message || "Could not read this QM-Home layer.");
        const parentPath = serverParentPathForFile(serverBrowserPath);
        const owner = clean(taskOwnerOverride || "");
        setServerBrowserBackControl(serverBrowserPath, parentPath, parentPath ? owner : "");
      };

      const closeServerBrowser = () => {
        if (typeof window.__ftClearSpaceWOverlaysForRouteLeave === "function") {
          window.__ftClearSpaceWOverlaysForRouteLeave();
        }
        if (serverBrowser) {
          serverBrowser.hidden = true;
          syncServerWorkspaceOpenState();
        }
        clearLearningStatsMotionCycle();
        try {
          stopServerBrowserAutoRefresh();
        } catch (error) {
        }
        try {
          stopServerBrowserManifestPoll();
        } catch (error) {
        }
      };

      var pdfModeActive = false;
      var pdfEls = null;
      var pdfSelectionTechBurstTimer = 0;
      var pdfSelectionTechBurstOffTimer = 0;
      var pdfUnionPulseTimer = 0;
      var pdfUnionPulseOffTimer = 0;
      var pdfOcrActiveBatch = 0;
      var pdfOcrAppendSequence = 0;
      var pdfOcrAppendBaseFound = "";
      var pdfOcrAppendBaseExplore = "";
      var pdfOcrAppendSlots = [];
      var pdfExploreAnalyzeSerial = 0;
      const PDF_OCR_ENGINE_KEY = "future_pdf_ocr_engine";
      const PDF_SCAN_PAGE_SOURCE_KEY = "future_pdf_scan_page_source";
      const PDF_BROWSER_OCR_SCRIPT_URL = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
      var pdfScanPageSource = "sync";
      var pdfState = {
        mode: "pdf",
        path: "",
        name: "",
        title: "",
        page: 1,
        pages: 0,
        scale: 2,
        viewZoom: 1,
        baseDisplayWidth: 0,
        pagePointWidth: 0,
        pagePointHeight: 0,
        hasTextLayer: false,
        tesseractReady: false,
        objectUrl: "",
        selection: null,
        selections: [],
        ocrText: "",
        ocrRawText: "",
        ocrFilteredText: "",
        ocrViewMode: "raw",
        translation: "",
        translationCache: {},
        ghostConsoleFloating: false,
        ghostConsolePosition: null,
        translationPosition: null,
        vocabStats: null,
        vocabMission: null,
        vocabDetailMap: {},
        scanBusy: false,
        ghostConsoleVisible: true,
        unlearnedWords: {},
        pictureImages: [],
        agentHistory: [],
        wordAgentHistory: [],
        ocrTab: "found",
        wordDetailPinned: false,
        pinnedWordKey: "",
        wordDetailEntries: [],
        wordDetailSurface: "",
        wordDetailPage: "basic",
        wordAgentLatestByKey: {},
        phoneticIpaByKey: {},
        agentBackMode: "pdf",
        pinnedPages: [],
        audioMarkers: [],
        aiRegionNotices: [],
        aiRegionQuestions: [],
        aiNoticeActiveId: "",
        aiQuestionActiveId: "",
        aiNoticeRegionsVisible: false,
        aiAssistRegionsVisible: true,
        sourceFileUrl: "",
        sourceFileBlob: null,
        sourceFileCacheKey: "",
        sourceFileBytes: 0,
        sourceFileCached: false,
        pdfDocument: null,
        pdfDocumentKey: "",
        fileEtag: "",
        fileMtime: "",
        size: 0,
        localImageActive: false,
        localImageSlotIndex: 0,
        localImageDataUrl: "",
        localImageWidth: 0,
        localImageHeight: 0,
      };
      var pdfAiRegionNoticeLoadToken = 0;
      var pdfAiRegionQuestionLoadToken = 0;
      var pdfAiQuestionAudio = null;
      var pdfAiNoticeFireballState = null;
      var pdfAiNoticeFireballTypeTimer = 0;
      var pdfAiNoticeFireballMoveTimer = 0;
      var pdfAiNoticeFireballJumpTimer = 0;
      var pdfAiNoticeFireballHideTimer = 0;
      var pdfAiNoticeFireballHoverTimer = 0;
      var pdfAiNoticeFireballDrag = null;
      var pdfAiNoticeVoiceAudio = null;
      var pdfAiNoticeVoicePlayedKeys = new Set();
      var pdfAiNoticeFireballSeenKeys = new Set();
      const SPACE_PICTURE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff"]);
      const isSpacePictureExtension = (value = "") => SPACE_PICTURE_EXTENSIONS.has(clean(value).toLowerCase());
      var pdfSelectDrag = null;
      var pdfFloatingPanelDrag = null;
      var pdfPointSelectStart = null;
      var pdfRightClickPointHandledAt = 0;
      var pdfShiftSelectionActive = false;
      var pdfPanDrag = null;
      var pdfNavigatorPointerId = 0;
      var pdfNavigatorFrame = 0;
      var pdfNavigatorLastTick = 0;
      var pdfNavigatorVector = { x: 0, y: 0, power: 0 };
      var pdfNavigatorVelocity = { x: 0, y: 0 };
      var pdfCompactToolbarEnabled = true;
      var pdfRenderQualityLevel = 1;
      var pdfPenActive = false;
      var pdfAudioInsertActive = false;
      var pdfAudioMarkers = [];
      var pdfAudioMarkerLoadToken = 0;
      var pdfAudioMarkerDrag = null;
      var pdfAudioMarkerEditingId = "";
      var pdfAudioMarkerMoveId = "";
      var pdfAudioMarkerVoicePayload = null;
      var pdfAudioMarkerVoicePromise = null;
      var pdfAudioMarkerVoiceRows = [];
      var pdfAudioPopoverMode = "audio";
      var pdfAudioPopoverSnapshot = "";
      var pdfAudioPopoverSaving = false;
      var pdfAudioPopoverDrag = null;
      var pdfAudioMicCtrlCandidate = false;
      var pdfAudioMarkerFileInput = null;
      var pdfAudioMarkerPlayer = null;
      var pdfAudioMarkerPlayingId = "";
      var pdfAudioMarkerEndedId = "";
      var pdfAudioMarkerPlayingPage = 0;
      var pdfAudioMarkerPins = {};
      var pdfAudioMarkerVideoPopup = null;
      var pdfAudioMarkerVideoConnector = null;
      var pdfAudioMarkerTranscodeRetry = {};
      var pdfAudioMarkerAutoResetTimer = 0;
      var pdfAudioMarkerProgressRaf = 0;
      var pdfAudioMarkerCache = {};
      // Added 2026-07-15: coalesces Space_PDF/Picture page side-data loads while users flip pages quickly.
      var pdfSideDataLoadTimer = 0;
      var pdfSideDataLoadSerial = 0;
      var pdfAiRegionNoticeCache = {};
      var pdfAiRegionQuestionCache = {};
      var pdfAudioMarkerLoadInflight = {};
      var pdfAiRegionNoticeLoadInflight = {};
      var pdfAiRegionQuestionLoadInflight = {};
      var pdfDrawingLoadInflight = {};
      var pdfPenColor = "#ffd166";
      var pdfPenWidth = 5;
      var pdfPenPointer = null;
      var pdfDrawingVectorVersion = 2;
      var pdfPenLastDustAt = 0;
      var pdfPenClearing = false;
      var pdfEraserActive = false;
      var pdfEraserPointer = null;
      var pdfEraserSize = 34;
      var pdfEraserCursor = null;
      var pdfTextActive = false;
      var pdfTextColor = "#ffffff";
      var pdfTextFont = "Inter";
      var pdfTextSize = 28;
      var pdfTextBold = false;
      var pdfTextItalic = false;
      var pdfTextDraft = null;
      var pdfTextSelectionColorPopover = null;
      var pdfTextSelectionRange = null;
      var pdfPinnedRegions = [];
      var pdfPinnedRegionActiveId = "";
      var pdfPinnedPageReturnPage = 0;
      var pdfLocalImageSlots = [];
      var pdfLocalImageOriginalState = null;
      var pdfLocalImageRuntimeUrl = "";
      var pdfLocalImageSuppressOpenUntil = 0;
      var pdfOcrEngine = "server";
      var pdfBrowserOcrScriptPromise = null;
      var pdfOcrEnginePopover = null;
      var pdfScanSourcePopover = null;
      var pdfPinnedRegionVisible = false;
      var pdfPinnedRegionDrag = null;
      const PDF_PAGE_RENDER_VERSION = "pdfjs-local-quality";
      const PDF_PAGE_PERSISTENT_CACHE = "future-space-pdf-pages-v1";
      const PDF_FILE_PERSISTENT_CACHE = "future-space-pdf-files-v1";
      const PDF_FILE_CHUNK_BYTES = 2 * 1024 * 1024;
      const PDF_FILE_FULL_CACHE_MAX_BYTES = 64 * 1024 * 1024;
      const PDF_FILE_CACHE_READ_TIMEOUT_MS = 6000;
      const PDF_LOCAL_IMAGE_CACHE = "future-space-pdf-local-images-v1";
      const PDFJS_MODULE_URL = "/future-assets/vendor/pdfjs/pdf.min.mjs";
      const PDFJS_WORKER_URL = "/future-assets/vendor/pdfjs/pdf.worker.min.mjs";
      var pdfPageCache = new Map();
      var pdfRenderRequestToken = 0;
      // Added 2026-07-22: rapid page clicks update one latest-wins navigation runner.
      var pdfPendingPage = 0;
      var pdfPageNavigationPromise = null;
      var pdfPageNavigationSerial = 0;
      var pdfDrawingLoadToken = 0;
      var pdfDrawingSavePromise = Promise.resolve();
      var pdfDrawingLayerMemoryCache = new Map();
      var pdfPrefetchSerial = 0;
      var pdfPrefetchControllers = new Set();
      var pdfBackgroundPageCacheTimer = 0;
      var pdfBackgroundPageCacheBusy = false;
      var pdfBackgroundPageCacheCursor = 1;
      var pdfBackgroundPageCacheScope = "";
      var pdfPreviewController = null;
      var pdfPreviewObjectUrl = "";
      var pdfSourceFileWarmPromises = new Map();
      var pdfJsModulePromise = null;
      var pdfJsDocumentPromise = null;
      var pdfAudioPlayer = null;
      var pdfProgressSaveTimer = 0;
      var pdfProgressLifecycleFlushAt = 0;
      var pdfProgressLifecycleFlushSignature = "";
      // Added 2026-07-24: suppresses repeated identical PDF progress POSTs after page render settles.
      var pdfProgressLastSentSemanticSignature = "";
      // Added 2026-07-15: avoids reposting last-file while the learner only clicks/selects on the same PDF page.
      var pdfLastFileSyncSignature = "";
      // Added 2026-07-15: fetches server PDF/Picture state once per session, then lets local cache drive the UI.
      var pdfProgressServerBootstrapKeys = new Set();
      var pdfDrawingServerBootstrapKeys = new Set();
      var pdfAgentThinkingTimer = 0;
      var pdfAgentThinkingStartedAt = 0;
      var pdfPhoneticIpaPending = new Set();
      var pdfSpeakTrainingNudgeTimer = 0;
      var pdfSpeakTraining = {
        recorder: null,
        stream: null,
        chunks: [],
        blob: null,
        url: "",
        audio: null,
        audioContext: null,
        analyser: null,
        source: null,
        frame: 0,
        rows: [],
        busy: false,
        mode: "idle",
        cancelStop: false,
        referenceText: "",
        referenceIpa: "",
        referenceTokens: [],
        transcriptTokens: [],
        voiceLoaded: false,
        referenceAudio: null,
        referenceAudioPath: "",
        referenceAudioText: "",
        referenceAudioVoice: "",
        referenceAudioLabel: "",
        referenceAudioWarmKey: "",
        referenceAudioWarming: false,
        referenceAudioPreload: null,
        referenceFrame: 0,
        referenceTimeline: [],
        referenceHighlightIndex: -1,
        transcriptTimeline: [],
        transcriptFrame: 0,
        transcriptHighlightIndex: -1,
        aiCheckVoice: true,
        aiCheckVoiceFallbackActive: false,
        serverAllowsWhisper: true,
        serverManaged: false,
        serverSettingCheckBusy: false,
        recognition: null,
        recognitionActive: false,
        recognitionManualStop: false,
        recognitionTranscript: "",
        recognitionChunkText: "",
        recognitionLastError: "",
        browserLocalRecording: false,
        browserLocalAutoReplay: false,
      };
      const PDF_PROGRESS_PREFIX = "future_space_pdf_progress";
      const PDF_UNLEARNED_PREFIX = "future_space_pdf_unlearned";
      const PDF_COMPACT_TOOLBAR_KEY = "future_pdf_compact_toolbar";
      const PDF_DRAWING_TOOL_KEY = "future_pdf_drawing_tool";
      const PDF_SPEAK_AI_CHECK_KEY = "future_pdf_speak_ai_check_voice";
