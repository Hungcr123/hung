

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

      let lessonEntryGateSequenceToken = 0;
      let lessonEntryGateSequenceState = null;
      let lessonEntryGateClockTimer = 0;
      let lessonEntryGateSealTimer = 0;
      let lessonEntryGateAutoContinueTimer = 0;
      let lessonEntryGateDeferredServerBrowserClose = false;
      let lessonEntryGateFastStartRequested = false;
      let lessonEntryPdfProgressFrame = 0;
      let lessonEntryPdfProgressPayload = null;
      const LESSON_ENTRY_PRIMARY_SEAL_MS = 1050;

      // Added 2026-08-02: keeps the primary-gate lesson choices hidden outside the manual Space entry decision.
      const hideLessonEntryGateActions = () => {
        [lessonEntryGateOpenButton, lessonEntryGateContinueButton, lessonEntryGateTrainButton, lessonEntryGateExitButton].forEach((button) => {
          if (button) button.hidden = true;
        });
      };

      // Added 2026-08-02: cancels the PDF gate's one-second default Continue choice.
      const clearLessonEntryGateAutoContinue = () => {
        if (lessonEntryGateAutoContinueTimer) {
          window.clearTimeout(lessonEntryGateAutoContinueTimer);
          lessonEntryGateAutoContinueTimer = 0;
        }
      };

      // Added 2026-08-03: stops circuit-board animation while the heavy primary doors are physically moving.
      const setLessonEntryPrimaryGateMoving = (moving = false) => {
        if (lessonEntryGateFrame) lessonEntryGateFrame.classList.toggle("is-primary-moving", Boolean(moving));
      };

      // Added 2026-08-02: freezes Lesson Vault motion/timers while the gate owns the frame budget.
      const freezeLessonVaultForEntryGate = () => {
        document.documentElement.classList.add("ft-lesson-entry-motion-freeze");
        if (typeof clearLearningStatsMotionCycle === "function") clearLearningStatsMotionCycle();
        if (!serverBrowser) return;
        serverBrowser.querySelectorAll("*").forEach((node) => {
          ["_futureStatBurstTimer", "_futureFileLogoMotionTimer", "_futureMotionBurstTimer"].forEach((key) => {
            if (node[key]) window.clearTimeout(node[key]);
            node[key] = 0;
          });
          node.classList.remove("is-stat-burst", "is-logo-burst", "is-motion-burst", "is-task-focus-burst");
        });
      };

      // Added 2026-08-02: restores Lesson Vault motion only after the gate has fully left the viewport.
      const unfreezeLessonVaultAfterEntryGate = () => {
        document.documentElement.classList.remove("ft-lesson-entry-motion-freeze");
        if (typeof scheduleLearningStatsMotionCycle === "function") scheduleLearningStatsMotionCycle(900);
      };

      const updateLessonEntryGateClock = () => {
        if (!lessonEntryGateClock) {
          return;
        }
        const now = new Date();
        lessonEntryGateClock.textContent = [now.getHours(), now.getMinutes(), now.getSeconds()]
          .map((value) => String(value).padStart(2, "0"))
          .join(":");
      };

      const formatLessonEntryStreamBytes = (bytes = 0) => {
        const value = Math.max(0, Number(bytes || 0) || 0);
        if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(value >= 10 * 1024 * 1024 ? 1 : 2)} MB`;
        if (value >= 1024) return `${Math.round(value / 1024)} KB`;
        return `${Math.round(value)} B`;
      };

      // Updated 2026-08-03: network bytes paint synchronously; local milestones stay frame-coalesced.
      const renderLessonEntryPdfProgress = () => {
        lessonEntryPdfProgressFrame = 0;
        const progress = lessonEntryPdfProgressPayload;
        const state = lessonEntryGateSequenceState;
        if (!progress || !state || !state.pdfProgressEnabled || !lessonEntryPdfStream) return;
        const loaded = Math.max(0, Number(progress.loaded || 0) || 0);
        const total = Math.max(0, Number(progress.total || 0) || 0);
        const done = Boolean(progress.done);
        const explicitOverall = Number(progress.overallPercent);
        const percent = Number.isFinite(explicitOverall)
          ? Math.max(0, Math.min(100, Math.round(explicitOverall)))
          : (total > 0
            ? Math.max(0, Math.min(100, Math.round((loaded / total) * 100)))
            : (done ? 100 : Math.max(0, Math.min(99, Math.round(Number(progress.percent || 0) || 0)))));
        const chunkIndex = Math.max(0, Math.floor(Number(progress.chunkIndex || 0) || 0));
        const chunkCount = Math.max(0, Math.floor(Number(progress.chunkCount || 0) || 0));
        lessonEntryPdfStream.hidden = false;
        lessonEntryPdfStream.style.setProperty("--ft-entry-pdf-progress", `${percent}%`);
        if (lessonEntryPdfStreamGraph) {
          lessonEntryPdfStreamGraph.style.setProperty("--ft-entry-pdf-progress", `${percent}%`);
        }
        if (lessonEntryPdfStreamProgressRing) {
          const circumference = 2 * Math.PI * 110;
          lessonEntryPdfStreamProgressRing.style.strokeDasharray = `${circumference} ${circumference}`;
          lessonEntryPdfStreamProgressRing.style.strokeDashoffset = String(circumference - ((percent / 100) * circumference));
        }
        lessonEntryPdfStream.classList.toggle("is-ready", done);
        if (lessonEntryPdfStreamPhase) lessonEntryPdfStreamPhase.textContent = clean(progress.phase || (done ? "PDF CACHE READY" : "PDF CHUNK STREAM"));
        if (lessonEntryPdfStreamPercent) lessonEntryPdfStreamPercent.textContent = `${percent}%`;
        if (lessonEntryPdfStreamFill) lessonEntryPdfStreamFill.style.width = `${percent}%`;
        if (lessonEntryPdfStreamChunk) {
          const chunkPercent = Number.isFinite(Number(progress.chunkPercent)) ? ` · ${Math.round(Math.max(0, Math.min(100, Number(progress.chunkPercent))))}%` : "";
          lessonEntryPdfStreamChunk.textContent = chunkCount
            ? `${progress.cached ? "CACHE" : "CHUNK"} ${Math.min(chunkCount, Math.max(1, chunkIndex))}/${chunkCount}${chunkPercent}`
            : clean(progress.chunkLabel || "READING METADATA");
        }
        if (lessonEntryPdfStreamBytes) {
          lessonEntryPdfStreamBytes.textContent = total > 0
            ? `${formatLessonEntryStreamBytes(loaded)} / ${formatLessonEntryStreamBytes(total)}`
            : `${formatLessonEntryStreamBytes(loaded)} / --`;
        }
      };

      const updateLessonEntryPdfProgress = (progress = {}) => {
        const state = lessonEntryGateSequenceState;
        const next = progress && typeof progress === "object" ? { ...progress } : {};
        const sourceSurface = clean(next.surface).toLowerCase() === "pdf file";
        if (!state) return false;
        // A real foreground PDF stream is authoritative even if the media-choice
        // state was lost during the Vault -> PDF handoff. Recover only while gate 1 is visible.
        if (!state.pdfProgressEnabled) {
          if (!sourceSurface || !lessonEntryGate || lessonEntryGate.hidden) return false;
          state.pdfProgressEnabled = true;
          state.pdfProgressMode = "network";
          state.pdfOverallProgress = 0;
          state.pdfSourceComplete = false;
          state.pdfProgressPhaseLocked = false;
          if (lessonEntryGateFrame) lessonEntryGateFrame.classList.add("is-pdf-stream-active");
        }
        if (state.pdfProgressPhaseLocked && next.surface) return false;
        if (!Number.isFinite(Number(next.overallPercent)) && next.surface) {
          const loaded = Math.max(0, Number(next.loaded || 0) || 0);
          const total = Math.max(0, Number(next.total || 0) || 0);
          const isSourceFile = clean(next.surface).toLowerCase() === "pdf file";
          const rawPercent = total > 0
            ? Math.max(0, Math.min(100, (loaded / total) * 100))
            : Math.max(0, Number(next.percent || 0) || 0);
          // Network mode reports the complete source transfer; local mode is reset separately after it.
          if (isSourceFile) {
            if (state.pdfProgressMode === "local") return false;
            next.overallPercent = rawPercent;
            if (next.done) {
              next.overallPercent = 100;
              state.pdfSourceComplete = true;
            }
          } else {
            if (!state.pdfSourceComplete || state.pdfProgressMode !== "local") return false;
            next.overallPercent = rawPercent;
          }
          next.phase = isSourceFile ? (rawPercent >= 100 ? "PDF SOURCE CACHED" : "PDF CHUNK STREAM") : "PDF PAGE CACHE";
        }
        if (Number.isFinite(Number(next.overallPercent))) {
          next.overallPercent = Math.max(Number(state.pdfOverallProgress || 0), Math.min(100, Number(next.overallPercent)));
          state.pdfOverallProgress = next.overallPercent;
        }
        if (Array.isArray(window.__ftLessonEntryPdfOverallProbe) && Number.isFinite(Number(next.overallPercent))) {
          const value = Math.round(Number(next.overallPercent));
          if (window.__ftLessonEntryPdfOverallProbe.at(-1) !== value) window.__ftLessonEntryPdfOverallProbe.push(value);
        }
        lessonEntryPdfProgressPayload = { ...(lessonEntryPdfProgressPayload || {}), ...next };
        if (sourceSurface) {
          if (lessonEntryPdfProgressFrame) {
            window.cancelAnimationFrame(lessonEntryPdfProgressFrame);
            lessonEntryPdfProgressFrame = 0;
          }
          renderLessonEntryPdfProgress();
          return true;
        }
        if (!lessonEntryPdfProgressFrame) lessonEntryPdfProgressFrame = window.requestAnimationFrame(renderLessonEntryPdfProgress);
        return true;
      };

      // Added 2026-08-02: starts a separate monotonic 0-100 local-render pass after network reaches 100%.
      const beginLessonEntryPdfLocalProgress = () => {
        const state = lessonEntryGateSequenceState;
        if (!state || !state.pdfProgressEnabled || !state.pdfSourceComplete) return false;
        state.pdfProgressMode = "local";
        state.pdfOverallProgress = 0;
        state.pdfProgressPhaseLocked = false;
        lessonEntryPdfProgressPayload = null;
        return updateLessonEntryPdfProgress({
          overallPercent: 0,
          phase: "LOCAL PDF RENDER",
          chunkLabel: "LOCAL PIPELINE",
          loaded: 0,
          total: 0,
          done: false,
        });
      };
      window.__ftBeginLessonEntryPdfLocalProgress = beginLessonEntryPdfLocalProgress;

      const resetLessonEntryPdfProgress = () => {
        lessonEntryPdfProgressPayload = null;
        if (lessonEntryPdfProgressFrame) window.cancelAnimationFrame(lessonEntryPdfProgressFrame);
        lessonEntryPdfProgressFrame = 0;
        if (lessonEntryPdfStream) {
          lessonEntryPdfStream.hidden = true;
          lessonEntryPdfStream.classList.remove("is-ready");
          lessonEntryPdfStream.style.setProperty("--ft-entry-pdf-progress", "0%");
        }
        if (lessonEntryPdfStreamGraph) {
          lessonEntryPdfStreamGraph.style.setProperty("--ft-entry-pdf-progress", "0%");
        }
        if (lessonEntryPdfStreamProgressRing) {
          const circumference = 2 * Math.PI * 110;
          lessonEntryPdfStreamProgressRing.style.strokeDasharray = `${circumference} ${circumference}`;
          lessonEntryPdfStreamProgressRing.style.strokeDashoffset = String(circumference);
        }
        if (lessonEntryGateFrame) lessonEntryGateFrame.classList.remove("is-pdf-stream-active");
      };
      window.__ftUpdateLessonEntryPdfProgress = updateLessonEntryPdfProgress;
      window.__ftLessonEntryPdfProgressActive = () => Boolean(
        lessonEntryGateSequenceState && lessonEntryGateSequenceState.pdfProgressEnabled
      );

      // Added 2026-08-02: seals Lesson Vault behind a full-screen two-stage gate while the selected lesson becomes ready.
      const beginLessonEntryGateTransition = (entry = {}, options = {}) => {
        if (!lessonEntryGate || !lessonEntryGateFrame) {
          return 0;
        }
        const token = ++lessonEntryGateSequenceToken;
        if (lessonEntryGateClockTimer) {
          window.clearInterval(lessonEntryGateClockTimer);
          lessonEntryGateClockTimer = 0;
        }
        if (lessonEntryGateSealTimer) {
          window.clearTimeout(lessonEntryGateSealTimer);
          lessonEntryGateSealTimer = 0;
        }
        lessonEntryGateDeferredServerBrowserClose = false;
        lessonEntryGateFastStartRequested = false;
        resetLessonEntryPdfProgress();
        hideLessonEntryGateActions();
        freezeLessonVaultForEntryGate();
        lessonEntryGate.hidden = false;
        lessonEntryGate.setAttribute("aria-hidden", "false");
        lessonEntryGate.classList.remove("is-fading", "is-error");
        lessonEntryGateFrame.classList.remove("is-primary-sealed", "is-primary-open", "is-secondary-ready", "is-secondary-open", "is-primary-moving");
        setLessonEntryPrimaryGateMoving(true);
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "SEALING LESSON VAULT";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = clean(entry.name || entry.title || "Preparing lesson channel");
        if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "LOCKED";
        if (lessonEntryGate2Led) {
          lessonEntryGate2Led.style.background = "#ef4444";
          lessonEntryGate2Led.style.boxShadow = "0 0 10px #ef4444";
        }
        if (lessonEntryPrimaryLed) {
          lessonEntryPrimaryLed.style.background = "#ef4444";
          lessonEntryPrimaryLed.style.boxShadow = "0 0 10px #ef4444";
        }
        updateLessonEntryGateClock();
        lessonEntryGateClockTimer = window.setInterval(updateLessonEntryGateClock, 1000);
        lessonEntryGateSequenceState = { token, startedAt: Date.now(), primarySealComplete: false };
        clearLessonEntryGateAutoContinue();
        window.__ftLessonEntryGateActivationToken = token;
        window.__ftLessonEntryGateActivationBlocked = true;
        lessonEntryGateSealTimer = window.setTimeout(() => {
          lessonEntryGateSealTimer = 0;
          const activeState = lessonEntryGateSequenceState;
          if (!activeState || activeState.token !== token) return;
          activeState.primarySealComplete = true;
          setLessonEntryPrimaryGateMoving(false);
          if (lessonEntryGateDeferredServerBrowserClose) {
            lessonEntryGateDeferredServerBrowserClose = false;
            closeServerBrowser();
          }
        }, LESSON_ENTRY_PRIMARY_SEAL_MS);
        void lessonEntryGateFrame.offsetWidth;
        window.requestAnimationFrame(() => {
          window.requestAnimationFrame(() => {
            if (lessonEntryGateSequenceState && lessonEntryGateSequenceState.token === token) {
              lessonEntryGateFrame.classList.add("is-primary-sealed");
            }
          });
        });
        return token;
      };

      // Added 2026-08-02: completes the secondary opening after any vocabulary decision has resolved.
      const openLessonEntrySecondaryGate = async (token = 0) => {
        if (!token || !lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGateFrame.classList.add("is-secondary-open");
        await delay(950);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGate.classList.add("is-fading");
        await delay(360);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGate.hidden = true;
        lessonEntryGate.setAttribute("aria-hidden", "true");
        lessonEntryGate.classList.remove("is-fading");
        lessonEntryGateFrame.classList.remove("is-primary-sealed", "is-primary-open", "is-secondary-ready", "is-secondary-open", "is-primary-moving", "is-vocab-alert");
        if (lessonEntryVocabAlert) lessonEntryVocabAlert.hidden = true;
        unfreezeLessonVaultAfterEntryGate();
        lessonEntryGateSequenceState = null;
        resetLessonEntryPdfProgress();
        lessonEntryGateDeferredServerBrowserClose = false;
        if (lessonEntryGateClockTimer) {
          window.clearInterval(lessonEntryGateClockTimer);
          lessonEntryGateClockTimer = 0;
        }
        window.__ftLessonEntryGateActivationBlocked = false;
        window.dispatchEvent(new CustomEvent("ft:lesson-entry-gate-open", { detail: { token, opened: true } }));
        return true;
      };

      window.__ftRunAfterLessonEntryGateOpen = (callback) => {
        if (typeof callback !== "function") return false;
        if (!window.__ftLessonEntryGateActivationBlocked) {
          callback();
          return true;
        }
        const token = Number(window.__ftLessonEntryGateActivationToken || 0);
        window.addEventListener("ft:lesson-entry-gate-open", (event) => {
          const detail = event && event.detail && typeof event.detail === "object" ? event.detail : {};
          if (detail.opened && Number(detail.token || 0) === token) callback();
        }, { once: true });
        return false;
      };

      // Added 2026-08-02: records whether preflight can release gate 2 or must show the vocabulary route card.
      const settleLessonEntryGateVocabPreflight = (hasAlert = false) => {
        const state = lessonEntryGateSequenceState;
        if (!state || !state.awaitingVocabPreflight) return false;
        state.vocabPreflightResolved = true;
        state.vocabAlertPending = Boolean(hasAlert);
        return true;
      };

      const finishLessonEntryGateTransition = async (token = 0, label = "") => {
        const state = lessonEntryGateSequenceState;
        if (!token || !state || state.token !== token || !lessonEntryGate || !lessonEntryGateFrame) {
          return false;
        }
        const markChoiceTrace = typeof state.choiceTraceMark === "function" ? state.choiceTraceMark : () => {};
        markChoiceTrace("gate-transition-start");
        const sealMs = LESSON_ENTRY_PRIMARY_SEAL_MS;
        const elapsed = Date.now() - Number(state.startedAt || 0);
        if (elapsed < sealMs) await delay(sealMs - elapsed);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGateSequenceState.awaitingDecision = false;
        hideLessonEntryGateActions();
        const mediaGate = Boolean(state.mediaChoice);
        if (mediaGate && state.pdfProgressEnabled) {
          state.pdfProgressPhaseLocked = true;
          updateLessonEntryPdfProgress({ overallPercent: 100, phase: "LOCAL VIEWER READY", done: true });
          await delay(140);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        }
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "PRIMARY GATE SECURED";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = clean(label || "Synchronizing lesson channel");
        if (lessonEntryPrimaryLed) {
          lessonEntryPrimaryLed.style.background = "#22c55e";
          lessonEntryPrimaryLed.style.boxShadow = "0 0 10px #22c55e";
        }
        lessonEntryGateFrame.classList.add("is-secondary-ready");
        setLessonEntryPrimaryGateMoving(true);
        lessonEntryGateFrame.classList.add("is-primary-open");
        await delay(1000);
        markChoiceTrace("primary-open");
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        setLessonEntryPrimaryGateMoving(false);
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "SYNCHRONIZING INNER GATE";
        if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "SYNC...";
        await delay(mediaGate ? 0 : 800);
        markChoiceTrace("inner-sync-complete");
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "LESSON CHANNEL ACTIVE";
        if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "ACTIVE";
        if (lessonEntryGate2Led) {
          lessonEntryGate2Led.style.background = "#22c55e";
          lessonEntryGate2Led.style.boxShadow = "0 0 10px #22c55e";
        }
        await delay(mediaGate ? 0 : 400);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        if (state.awaitingVocabPreflight) {
          markChoiceTrace("preflight-wait-start");
          for (let attempt = 0; attempt < 240 && !state.vocabPreflightResolved; attempt += 1) await delay(50);
          markChoiceTrace("preflight-wait-end", { resolved: Boolean(state.vocabPreflightResolved) });
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
          if (state.vocabAlertPending) {
            if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "VOCABULARY ROUTE AVAILABLE";
            if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "ACTION REQUIRED";
            if (state.choiceTrace) console.info("[FTG][EntryChoice]", state.choiceTrace);
            return true;
          }
        }
        markChoiceTrace("secondary-release");
        if (state.choiceTrace) console.info("[FTG][EntryChoice]", state.choiceTrace);
        return openLessonEntrySecondaryGate(token);
      };

      // Added 2026-08-02: mirrors the prepared Space actions onto gate 1 after background loading finishes.
      const syncLessonEntryGateActions = () => {
        const state = lessonEntryGateSequenceState;
        if (lessonEntryGateExitButton) {
          lessonEntryGateExitButton.hidden = false;
          lessonEntryGateExitButton.disabled = false;
        }
        if (state && state.mediaChoice) {
          const resumePage = Math.max(0, Math.floor(Number(state.mediaChoice.resumePage || 0) || 0));
          const isPdfChoice = state.mediaChoice.kind === "pdf";
          if (lessonEntryGateOpenButton) {
            lessonEntryGateOpenButton.hidden = false;
            lessonEntryGateOpenButton.disabled = false;
            lessonEntryGateOpenButton.title = isPdfChoice ? "Continue // Open saved page" : "New // Open page 1";
            lessonEntryGateOpenButton.setAttribute("aria-label", lessonEntryGateOpenButton.title);
          }
          if (lessonEntryGateContinueButton) {
            lessonEntryGateContinueButton.hidden = isPdfChoice || !resumePage;
            lessonEntryGateContinueButton.disabled = isPdfChoice || !resumePage;
            lessonEntryGateContinueButton.title = resumePage ? `Continue // Open saved page ${resumePage}` : "No saved page";
            lessonEntryGateContinueButton.setAttribute("aria-label", lessonEntryGateContinueButton.title);
          }
          if (lessonEntryGateTrainButton) {
            lessonEntryGateTrainButton.hidden = true;
            lessonEntryGateTrainButton.disabled = true;
          }
          return resumePage ? 2 : 1;
        }
        const mappings = [
          [lessonEntryGateOpenButton, loadStartButton, "Open New Run"],
          [lessonEntryGateContinueButton, loadReviewButton, "Continue Previous"],
          [lessonEntryGateTrainButton, loadReviewTrainButton, "REVIEW TRAIN"],
        ];
        let visible = 0;
        mappings.forEach(([gateButton, sourceButton, label]) => {
          if (!gateButton) return;
          const available = Boolean(sourceButton && !sourceButton.hidden && !sourceButton.disabled);
          gateButton.hidden = !available;
          gateButton.disabled = !available;
          gateButton.setAttribute("aria-label", label);
          gateButton.title = label;
          if (gateButton === lessonEntryGateTrainButton) gateButton.textContent = label;
          if (available) visible += 1;
        });
        return visible;
      };
      window.__ftSyncLessonEntryGateActions = () => {
        const state = lessonEntryGateSequenceState;
        return state && state.awaitingDecision ? syncLessonEntryGateActions() : 0;
      };

      // Added 2026-08-02: pauses a prepared Space behind sealed gate 1 until the learner chooses Open or Continue.
      const armLessonEntryGateDecision = async (token = 0, label = "") => {
        const state = lessonEntryGateSequenceState;
        if (!token || !state || state.token !== token) return false;
        const elapsed = Date.now() - Number(state.startedAt || 0);
        if (elapsed < LESSON_ENTRY_PRIMARY_SEAL_MS) await delay(LESSON_ENTRY_PRIMARY_SEAL_MS - elapsed);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        state.awaitingDecision = true;
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "LESSON READY // SELECT ACCESS";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = clean(label || "Prepared lesson");
        if (lessonEntryPrimaryLed) {
          lessonEntryPrimaryLed.style.background = "#22c55e";
          lessonEntryPrimaryLed.style.boxShadow = "0 0 10px #22c55e";
        }
        for (let attempt = 0; attempt < 160; attempt += 1) {
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token || !state.awaitingDecision) return false;
          if (syncLessonEntryGateActions()) return true;
          await delay(50);
        }
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "LESSON PREPARATION DELAYED";
        return false;
      };

      // Added 2026-08-02: starts the selected prepared run before releasing the two gate layers.
      const lessonEntryChoiceNeedsVocabPreflight = (sourceButton = null, payload = null) => {
        if (!payload || !shouldRunSpaceWVocabPreflight(payload)) return false;
        if (sourceButton === loadReviewTrainButton) return false;
        return true;
      };

      const activateLessonEntryGateChoice = async (sourceButton = null) => {
        const state = lessonEntryGateSequenceState;
        if (!state || !state.awaitingDecision || !sourceButton || sourceButton.hidden || sourceButton.disabled) return false;
        const traceStartedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
        const trace = {
          action: sourceButton === loadReviewButton ? "continue" : (sourceButton === loadReviewTrainButton ? "review-train" : "new-study"),
          startedAt: Date.now(),
          stages: [],
        };
        const mark = (stage, detail = {}) => {
          const now = typeof performance !== "undefined" ? performance.now() : Date.now();
          trace.stages.push({ stage, ms: Math.round((now - traceStartedAt) * 100) / 100, ...detail });
          window.__ftLessonEntryChoiceTrace = trace;
        };
        state.choiceTrace = trace;
        state.choiceTraceMark = mark;
        mark("choice-click");
        state.awaitingDecision = false;
        hideLessonEntryGateActions();
        const preflightPayload = pendingQuestionPayload || pendingParagraphPayload || (pendingLessonNodes.length ? { nodes: pendingLessonNodes, effects: pendingLessonEffects } : null);
        state.awaitingVocabPreflight = lessonEntryChoiceNeedsVocabPreflight(sourceButton, preflightPayload);
        state.vocabPreflightResolved = !state.awaitingVocabPreflight;
        state.vocabAlertPending = false;
        mark("preflight-policy", { awaiting: state.awaitingVocabPreflight });
        lessonEntryGateFastStartRequested = sourceButton === loadStartButton;
        sourceButton.click();
        mark("source-dispatched");
        for (let attempt = 0; attempt < 30; attempt += 1) {
          if (!loadGate || loadGate.classList.contains("is-hidden")) break;
          await delay(50);
        }
        mark("runtime-ready", { loadHidden: Boolean(!loadGate || loadGate.classList.contains("is-hidden")) });
        lessonEntryGateFastStartRequested = false;
        return finishLessonEntryGateTransition(state.token, currentLessonSource.title || currentLessonSource.name || "Lesson ready");
      };

      const activateLessonEntryMediaChoice = async (mode = "new") => {
        const state = lessonEntryGateSequenceState;
        const choice = state && state.mediaChoice;
        if (!state || !state.awaitingDecision || !choice || typeof choice.open !== "function") return false;
        clearLessonEntryGateAutoContinue();
        state.awaitingDecision = false;
        hideLessonEntryGateActions();
        state.pdfProgressEnabled = choice.kind === "pdf";
        if (state.pdfProgressEnabled) {
          state.pdfOverallProgress = 0;
          state.pdfSourceComplete = false;
          state.pdfProgressMode = "network";
          state.pdfProgressPhaseLocked = false;
          lessonEntryGateFrame.classList.add("is-pdf-stream-active");
          updateLessonEntryPdfProgress({ phase: "PDF METADATA", chunkLabel: "NEGOTIATING SOURCE", loaded: 0, total: 0, percent: 0 });
        }
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = mode === "continue" ? "RESTORING SAVED PAGE" : "OPENING PAGE 1";
        try {
          await choice.open(mode);
          return finishLessonEntryGateTransition(state.token, choice.label || "Document ready");
        } catch (error) {
          return cancelLessonEntryGateTransition(state.token, error && error.message ? error.message : "Could not open document");
        }
      };

      const armLessonEntryMediaGateDecision = async (token = 0, options = {}) => {
        const state = lessonEntryGateSequenceState;
        if (!token || !state || state.token !== token || typeof options.open !== "function") return false;
        clearLessonEntryGateAutoContinue();
        state.mediaChoice = {
          resumePage: Math.max(0, Math.floor(Number(options.resumePage || 0) || 0)),
          label: clean(options.label || "Document ready"),
          kind: clean(options.kind || "").toLowerCase(),
          open: options.open,
        };
        const armed = await armLessonEntryGateDecision(token, options.label || "Document ready");
        if (armed && state.mediaChoice.kind === "pdf") {
          lessonEntryGateAutoContinueTimer = window.setTimeout(() => {
            lessonEntryGateAutoContinueTimer = 0;
            const active = lessonEntryGateSequenceState;
            if (active && active.token === token && active.awaitingDecision && active.mediaChoice && active.mediaChoice.kind === "pdf") {
              void activateLessonEntryMediaChoice("continue");
            }
          }, 1000);
        }
        return armed;
      };

      // 2026-08-03: cancel a pending entry by reopening only gate 1 over the restored Vault.
      const exitPendingLessonEntryGate = async () => {
        const state = lessonEntryGateSequenceState;
        if (!state || !state.awaitingDecision || !lessonEntryGate || !lessonEntryGateFrame) return false;
        clearLessonEntryGateAutoContinue();
        const token = state.token;
        state.awaitingDecision = false;
        hideLessonEntryGateActions();
        if (typeof cancelLessonAudioPrepare === "function") cancelLessonAudioPrepare();
        if (typeof stopActiveAudio === "function") stopActiveAudio();
        pendingVocabularyPayload = null;
        pendingQuestionPayload = null;
        pendingParagraphPayload = null;
        pendingLessonNodes = [];
        pendingLessonEffects = {};
        if (loadGate) {
          loadGate.classList.add("is-hidden");
          loadGate.classList.remove("is-file-ready");
        }
        if (clean(params.get("ft_gate_probe"))) {
          if (serverBrowser) serverBrowser.hidden = false;
          if (typeof syncServerWorkspaceOpenState === "function") syncServerWorkspaceOpenState();
        } else if (typeof openServerBrowser === "function") {
          openServerBrowser();
        }
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "RETURNING TO LESSON VAULT";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = "ENTRY CANCELLED";
        lessonEntryGateFrame.classList.remove("is-secondary-ready", "is-secondary-open", "is-vocab-alert");
        setLessonEntryPrimaryGateMoving(true);
        lessonEntryGateFrame.classList.add("is-primary-open");
        window.__ftLessonEntryGateExitChoiceResult = { primaryOpened: true, secondaryOpened: false };
        await delay(1000);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        setLessonEntryPrimaryGateMoving(false);
        lessonEntryGate.classList.add("is-fading");
        await delay(360);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGate.hidden = true;
        lessonEntryGate.setAttribute("aria-hidden", "true");
        lessonEntryGate.classList.remove("is-fading");
        lessonEntryGateFrame.classList.remove("is-primary-sealed", "is-primary-open", "is-secondary-ready", "is-secondary-open", "is-primary-moving", "is-vocab-alert");
        unfreezeLessonVaultAfterEntryGate();
        lessonEntryGateSequenceState = null;
        resetLessonEntryPdfProgress();
        lessonEntryGateDeferredServerBrowserClose = false;
        window.__ftLessonEntryGateActivationBlocked = false;
        window.dispatchEvent(new CustomEvent("ft:lesson-entry-gate-open", { detail: { token, opened: false } }));
        if (lessonEntryGateClockTimer) window.clearInterval(lessonEntryGateClockTimer);
        lessonEntryGateClockTimer = 0;
        return true;
      };

      // Added 2026-08-02: opens gate 2 only after the selected vocabulary route has begun rendering.
      const releaseLessonEntryGateAfterVocabChoice = async () => {
        const state = lessonEntryGateSequenceState;
        if (!state || !state.vocabAlertPending) return false;
        state.vocabAlertPending = false;
        if (lessonEntryVocabAlert) lessonEntryVocabAlert.hidden = true;
        lessonEntryGateFrame.classList.remove("is-vocab-alert");
        for (let attempt = 0; attempt < 160; attempt += 1) {
          if (vocabModeActive || questionModeActive || paragraphModeActive || (loadGate && loadGate.classList.contains("is-hidden"))) break;
          await delay(50);
        }
        return openLessonEntrySecondaryGate(state.token);
      };

      if (lessonEntryGateOpenButton) lessonEntryGateOpenButton.addEventListener("click", () => void (
        lessonEntryGateSequenceState && lessonEntryGateSequenceState.mediaChoice
          ? activateLessonEntryMediaChoice(lessonEntryGateSequenceState.mediaChoice.kind === "pdf" ? "continue" : "new")
          : activateLessonEntryGateChoice(loadStartButton)
      ));
      if (lessonEntryGateContinueButton) lessonEntryGateContinueButton.addEventListener("click", () => void (
        lessonEntryGateSequenceState && lessonEntryGateSequenceState.mediaChoice
          ? activateLessonEntryMediaChoice("continue")
          : activateLessonEntryGateChoice(loadReviewButton)
      ));
      if (lessonEntryGateTrainButton) lessonEntryGateTrainButton.addEventListener("click", () => void activateLessonEntryGateChoice(loadReviewTrainButton));
      if (lessonEntryGateExitButton) lessonEntryGateExitButton.addEventListener("click", () => void exitPendingLessonEntryGate());

      const cancelLessonEntryGateTransition = async (token = 0, message = "") => {
        if (!token || !lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token || !lessonEntryGate) {
          return false;
        }
        clearLessonEntryGateAutoContinue();
        lessonEntryGate.classList.add("is-error");
        hideLessonEntryGateActions();
        freezeLessonVaultForEntryGate();
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "LESSON CHANNEL INTERRUPTED";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = clean(message || "Returning to Lesson Vault");
        if (lessonEntryGateFrame) lessonEntryGateFrame.classList.add("is-primary-open", "is-secondary-open");
        await delay(320);
        if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return false;
        lessonEntryGate.classList.add("is-fading");
        await delay(360);
        lessonEntryGate.hidden = true;
        lessonEntryGate.setAttribute("aria-hidden", "true");
        lessonEntryGate.classList.remove("is-fading", "is-error");
        lessonEntryGateSequenceState = null;
        window.__ftLessonEntryGateActivationBlocked = false;
        window.dispatchEvent(new CustomEvent("ft:lesson-entry-gate-open", { detail: { token, opened: false } }));
        lessonEntryGateDeferredServerBrowserClose = false;
        lessonEntryGateFastStartRequested = false;
        unfreezeLessonVaultAfterEntryGate();
        if (lessonEntryGateSealTimer) {
          window.clearTimeout(lessonEntryGateSealTimer);
          lessonEntryGateSealTimer = 0;
        }
        if (lessonEntryGateClockTimer) {
          window.clearInterval(lessonEntryGateClockTimer);
          lessonEntryGateClockTimer = 0;
        }
        return true;
      };

      // Added 2026-08-02: reverses the two-stage gate before handing an active Space back to Lesson Vault.
      const beginLessonExitGateTransition = (onPrimarySealed = null, label = "") => {
        if (!lessonEntryGate || !lessonEntryGateFrame || lessonEntryGateSequenceState) return false;
        const token = ++lessonEntryGateSequenceToken;
        if (lessonEntryGateClockTimer) window.clearInterval(lessonEntryGateClockTimer);
        if (lessonEntryGateSealTimer) window.clearTimeout(lessonEntryGateSealTimer);
        lessonEntryGateClockTimer = 0;
        lessonEntryGateSealTimer = 0;
        lessonEntryGateDeferredServerBrowserClose = false;
        lessonEntryGateFastStartRequested = false;
        hideLessonEntryGateActions();
        freezeLessonVaultForEntryGate();
        lessonEntryGate.hidden = false;
        lessonEntryGate.setAttribute("aria-hidden", "false");
        lessonEntryGate.classList.remove("is-fading", "is-error");
        lessonEntryGateFrame.classList.remove("is-primary-sealed", "is-primary-open", "is-secondary-ready", "is-secondary-open", "is-primary-moving");
        lessonEntryGateFrame.classList.add("is-secondary-ready", "is-secondary-open");
        if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "CLOSING LESSON CHANNEL";
        if (lessonEntryGateTitle) lessonEntryGateTitle.textContent = clean(label || "Returning to Lesson Vault");
        if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "LOCKING...";
        if (lessonEntryGate2Led) {
          lessonEntryGate2Led.style.background = "#ef4444";
          lessonEntryGate2Led.style.boxShadow = "0 0 10px #ef4444";
        }
        if (lessonEntryPrimaryLed) {
          lessonEntryPrimaryLed.style.background = "#ef4444";
          lessonEntryPrimaryLed.style.boxShadow = "0 0 10px #ef4444";
        }
        updateLessonEntryGateClock();
        lessonEntryGateClockTimer = window.setInterval(updateLessonEntryGateClock, 1000);
        lessonEntryGateSequenceState = { token, startedAt: Date.now(), mode: "exit", primarySealComplete: false };
        void lessonEntryGateFrame.offsetWidth;
        window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
          if (lessonEntryGateSequenceState && lessonEntryGateSequenceState.token === token) {
            lessonEntryGateFrame.classList.remove("is-secondary-open");
          }
        }));
        void (async () => {
          await delay(950);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return;
          if (lessonEntryGate2Status) lessonEntryGate2Status.textContent = "SEALED";
          setLessonEntryPrimaryGateMoving(true);
          lessonEntryGateFrame.classList.add("is-primary-sealed");
          await delay(LESSON_ENTRY_PRIMARY_SEAL_MS);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return;
          setLessonEntryPrimaryGateMoving(false);
          lessonEntryGateSequenceState.primarySealComplete = true;
          if (typeof onPrimarySealed === "function") onPrimarySealed();
          await delay(120);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return;
          lessonEntryGateFrame.classList.remove("is-secondary-ready", "is-secondary-open");
          setLessonEntryPrimaryGateMoving(true);
          lessonEntryGateFrame.classList.add("is-primary-open");
          if (lessonEntryGateKicker) lessonEntryGateKicker.textContent = "LESSON VAULT RESTORED";
          await delay(1000);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return;
          setLessonEntryPrimaryGateMoving(false);
          lessonEntryGate.classList.add("is-fading");
          await delay(360);
          if (!lessonEntryGateSequenceState || lessonEntryGateSequenceState.token !== token) return;
          lessonEntryGate.hidden = true;
          lessonEntryGate.setAttribute("aria-hidden", "true");
          lessonEntryGate.classList.remove("is-fading");
          lessonEntryGateFrame.classList.remove("is-primary-sealed", "is-primary-open", "is-secondary-ready", "is-secondary-open", "is-primary-moving");
          unfreezeLessonVaultAfterEntryGate();
          lessonEntryGateSequenceState = null;
          if (lessonEntryGateClockTimer) window.clearInterval(lessonEntryGateClockTimer);
          lessonEntryGateClockTimer = 0;
        })();
        return true;
      };

      const lessonEntryGateProbeMode = clean(params.get("ft_gate_probe"));
      if (lessonEntryGateProbeMode === "1" || lessonEntryGateProbeMode === "visual") {
        window.__ftLessonEntryGateProbe = {
          begin: (label = "DOM gate probe") => beginLessonEntryGateTransition({ name: label }, { force: true }),
          finish: (token, label = "DOM lesson ready") => finishLessonEntryGateTransition(token, label),
          cancel: (token, message = "DOM probe cancelled") => cancelLessonEntryGateTransition(token, message),
          deferVaultClose: () => {
            if (!serverBrowser) return false;
            serverBrowser.hidden = false;
            closeServerBrowser();
            return !serverBrowser.hidden;
          },
          armDecision: (token) => {
            if (loadStartButton) {
              loadStartButton.hidden = false;
              loadStartButton.disabled = false;
            }
            if (loadReviewButton) {
              loadReviewButton.hidden = false;
              loadReviewButton.disabled = false;
            }
            return armLessonEntryGateDecision(token, "Space_Q prepared");
          },
          armDecisionDelayedContinue: (token) => {
            if (loadStartButton) {
              loadStartButton.hidden = false;
              loadStartButton.disabled = false;
            }
            if (loadReviewButton) {
              loadReviewButton.hidden = true;
              loadReviewButton.disabled = true;
            }
            const armed = armLessonEntryGateDecision(token, "Space_W delayed progress");
            window.setTimeout(() => {
              if (loadReviewButton) {
                loadReviewButton.hidden = false;
                loadReviewButton.disabled = false;
              }
              if (typeof window.__ftSyncLessonEntryGateActions === "function") window.__ftSyncLessonEntryGateActions();
            }, 250);
            return armed;
          },
          paragraphPreloadSpaces: async () => {
            const payload = { progress: { state: { currentIndex: 0, childIndex: 1 } } };
            const rows = await Promise.all(["Space_P", "Space_L", "Space_S"].map((space) => (
              readPreloadedServerProgress({ serverProgressPromise: Promise.resolve({ space, payload }) }, "Space_P")
            )));
            return rows.map((row) => Boolean(row && row.ok));
          },
          paragraphChildResume: () => ["Space_P", "Space_L", "Space_S"].map((space) => (
            resolveSpaceRunNavigation({ state: { childIndex: 1 } }, space).resumeAvailable
          )),
          snapshotCheckpointContract: () => ({
            compact: lessonProgressSnapshotHasFullCheckpoint({ progress: { current: 3, total: 8, percent: 37.5 } }),
            full: lessonProgressSnapshotHasFullCheckpoint({ progress: { state: { currentIndex: 3 } } }),
          }),
          spaceQResumeContract: () => {
            const normalized = normalizeQuestionProgressRecord({
              identity: "ftg-lesson-probe",
              activeRun: true,
              runId: "space-q-probe-run",
              nodeIndex: 2,
              nodeCount: 8,
              state: { currentIndex: 2, questionIndex: 1, activeRun: true },
            });
            const navigation = resolveSpaceRunNavigation(normalized, "Space_Q");
            const resume = normalizeQuestionResumeState(normalized && normalized.state, 8);
            return {
              activeRun: Boolean(normalized && normalized.activeRun),
              resumeAvailable: Boolean(navigation && navigation.resumeAvailable),
              currentIndex: Number(resume && resume.currentIndex),
              questionIndex: Number(resume && resume.questionIndex),
              runId: clean(resume && resume.runId),
            };
          },
          spaceQProgressPathsContract: () => {
            const previousSource = currentLessonSource;
            currentLessonSource = {
              source: "server",
              path: "common/probe.Space_Q",
              effective_path: "common/effective-probe.Space_Q",
              lesson_id: "ftg-lesson-probe",
              file_id: "ftg-lesson-probe",
            };
            try {
              return currentQuestionProgressPaths({
                identity: "ftg-lesson-probe",
                state: { lessonSource: { ...currentLessonSource } },
              });
            } finally {
              currentLessonSource = previousSource;
            }
          },
          spaceQTaskProgressContract: () => {
            if (!serverTaskListNode || typeof renderLessonTaskPanel !== "function" || typeof patchLessonTaskPanelProgress !== "function") {
              return { available: false };
            }
            const previousPayload = currentTaskPayload;
            const probeTask = {
              id: "space-q-task-progress-probe",
              lesson_id: "ftg-lesson-probe",
              file_id: "ftg-lesson-probe",
              path: "common/probe.Space_Q",
              extension: ".space_q",
              title: "Space_Q task progress probe",
              available: true,
              study: {
                total_nodes: 48,
                progress_text: "0/48",
                progress_percent: 0,
                progress: { space: "Space_Q", done: 0, total: 48, text: "0/48", percent: 0, activeRun: true, runId: "probe-run" },
              },
            };
            try {
              renderLessonTaskPanel({ task_owner: clean(currentAuthUsername || "probe"), tasks: [probeTask], space_tasks: [], admin: false });
              patchLessonTaskPanelProgress(
                ["space:space_q:id:ftg-lesson-probe", "common/probe.Space_Q"],
                { space: "Space_Q", done: 2, total: 48, text: "2/48", percent: 4, activeRun: true, runId: "probe-run" },
              );
              const card = serverTaskListNode.querySelector('[data-task-id="space-q-task-progress-probe"]');
              return {
                available: true,
                progressText: clean(card && card.dataset.progressText || ""),
                progressPercent: clean(card && card.dataset.progressPercent || ""),
                visibleText: clean(card && card.querySelector(".ft-task-progress") && card.querySelector(".ft-task-progress").textContent || ""),
              };
            } finally {
              if (previousPayload && typeof previousPayload === "object") {
                renderLessonTaskPanel(previousPayload);
              } else {
                currentTaskPayload = previousPayload;
                serverTaskListNode.textContent = "";
              }
            }
          },
          armMediaDecision: (token, resumePage = 7, sourceDownloadOptions = null) => {
            window.__ftLessonEntryMediaProbe = { choice: "", page: 0, activated: false };
            window.__ftLessonEntryPdfProgressProbe = [];
            window.__ftLessonEntryPdfOverallProbe = [];
            window.__ftRunAfterLessonEntryGateOpen(() => {
              window.__ftLessonEntryMediaProbe.activated = true;
            });
            return armLessonEntryMediaGateDecision(token, {
              resumePage,
              label: "PDF media choice",
              kind: "pdf",
              open: async (mode) => {
                window.__ftLessonEntryMediaProbe.choice = mode;
                window.__ftLessonEntryMediaProbe.page = mode === "continue" ? resumePage : 1;
                if (sourceDownloadOptions && typeof sourceDownloadOptions === "object") {
                  const bytes = Math.max(1, Math.floor(Number(sourceDownloadOptions.bytes || 0) || (5 * 1024 * 1024)));
                  const key = clean(sourceDownloadOptions.key || `pdf-gate-probe-${bytes}`);
                  const previous = { mode: pdfState.mode, path: pdfState.path, size: pdfState.size, page: pdfState.page };
                  try {
                    pdfState.mode = "pdf";
                    pdfState.path = "probe.pdf";
                    pdfState.size = bytes;
                    pdfState.page = 1;
                    const query = new URLSearchParams({ path: "probe.pdf" });
                    const result = await downloadPdfSourceFileByChunks(key, query, { path: "probe.pdf", size: bytes }, {
                      trackProgress: true,
                      isCurrent: () => true,
                    });
                    window.__ftLessonEntryMediaProbe.bytes = Number(result && result.bytes || 0) || 0;
                    beginLessonEntryPdfLocalProgress();
                    setPdfPageLoadProgress({ overallPercent: 100, phase: "LOCAL PAGE READY", done: true });
                    return;
                  } finally {
                    pdfState.mode = previous.mode;
                    pdfState.path = previous.path;
                    pdfState.size = previous.size;
                    pdfState.page = previous.page;
                  }
                }
                setPdfPageLoadProgress({ loaded: 1000, total: 1000, done: true, surface: "PDF page", phase: "PDF PAGE CACHE" });
                for (const progress of [
                  { loaded: 370, total: 1000, chunkIndex: 2, chunkCount: 6, chunkPercent: 37 },
                  { loaded: 820, total: 1000, chunkIndex: 5, chunkCount: 6, chunkPercent: 82 },
                  { loaded: 1000, total: 1000, chunkIndex: 6, chunkCount: 6, chunkPercent: 100, done: true },
                ]) {
                  setPdfPageLoadProgress({ ...progress, surface: "PDF file", phase: progress.done ? "PDF CACHE READY" : "PDF CHUNK STREAM" });
                  await delay(150);
                  const streamRect = lessonEntryPdfStream ? lessonEntryPdfStream.getBoundingClientRect() : null;
                  window.__ftLessonEntryPdfProgressProbe.push({
                    percent: clean(lessonEntryPdfStreamPercent && lessonEntryPdfStreamPercent.textContent),
                    chunk: clean(lessonEntryPdfStreamChunk && lessonEntryPdfStreamChunk.textContent),
                    graphProgress: clean(lessonEntryPdfStreamGraph && lessonEntryPdfStreamGraph.style.getPropertyValue("--ft-entry-pdf-progress")),
                    ringOffset: clean(lessonEntryPdfStreamProgressRing && lessonEntryPdfStreamProgressRing.style.strokeDashoffset),
                    hidden: Boolean(lessonEntryPdfStream && lessonEntryPdfStream.hidden),
                    withinViewport: Boolean(streamRect && streamRect.left >= 0 && streamRect.right <= window.innerWidth && streamRect.top >= 0 && streamRect.bottom <= window.innerHeight),
                  });
                }
                beginLessonEntryPdfLocalProgress();
                await delay(80);
                setPdfPageLoadProgress({ overallPercent: 100, phase: "LOCAL PAGE READY", done: true });
                await delay(80);
              },
            });
          },
          previewPdfProgress: (percent = 64) => {
            const state = lessonEntryGateSequenceState;
            if (!state) return false;
            state.pdfProgressEnabled = true;
            lessonEntryGateFrame.classList.add("is-pdf-stream-active");
            const safePercent = Math.max(0, Math.min(100, Math.round(Number(percent || 0) || 0)));
            return updateLessonEntryPdfProgress({
              phase: "PDF CHUNK STREAM",
              overallPercent: safePercent,
              loaded: safePercent * 1024 * 1024,
              total: 100 * 1024 * 1024,
              chunkIndex: Math.max(1, Math.ceil(safePercent / 10)),
              chunkCount: 10,
              done: safePercent >= 100,
            });
          },
          recoverPdfProgressState: (percent = 37) => {
            const state = lessonEntryGateSequenceState;
            if (!state || !lessonEntryGate || lessonEntryGate.hidden) return false;
            state.pdfProgressEnabled = false;
            state.pdfProgressMode = "";
            state.pdfOverallProgress = 0;
            const safePercent = Math.max(1, Math.min(99, Math.round(Number(percent || 0) || 0)));
            return updateLessonEntryPdfProgress({
              surface: "PDF file",
              phase: "PDF CHUNK STREAM",
              loaded: safePercent * 1024,
              total: 100 * 1024,
              chunkIndex: 1,
              chunkCount: 15,
              chunkPercent: safePercent,
              done: false,
            });
          },
          xhrProgress: async (path = "/ft-gate-xhr-progress-probe") => {
            const events = [];
            const result = await fetchAuthBlob(path, {
              sameOriginOnly: true,
              progressTransport: "xhr",
              onProgress: (progress) => events.push(Math.max(0, Number(progress && progress.loaded || 0) || 0)),
            });
            return { bytes: Number(result && result.blob && result.blob.size || 0) || 0, events };
          },
          pdfCacheTimeout: async () => {
            const startedAt = window.performance.now();
            const result = await withPdfCacheTimeout(new Promise(() => {}), 1000, "timeout");
            return { result, elapsedMs: Math.round(window.performance.now() - startedAt) };
          },
          pdfSourceDownload: async (options = {}) => {
            const bytes = Math.max(1, Math.floor(Number(options.bytes || 0) || (5 * 1024 * 1024)));
            const key = clean(options.key || `pdf-probe-${bytes}`);
            const previous = {
              mode: pdfState.mode,
              path: pdfState.path,
              size: pdfState.size,
              page: pdfState.page,
            };
            try {
              pdfState.mode = "pdf";
              pdfState.path = "probe.pdf";
              pdfState.size = bytes;
              pdfState.page = 1;
              const query = new URLSearchParams({ path: "probe.pdf" });
              const result = await downloadPdfSourceFileByChunks(key, query, { path: "probe.pdf", size: bytes }, {
                trackProgress: options.trackProgress !== false,
                isCurrent: () => true,
              });
              return {
                bytes: Number(result && result.bytes || 0) || 0,
                chunks: Number(result && result.chunks || 0) || 0,
                trace: Array.isArray(window.__ftPdfSourceNetworkTrace) ? window.__ftPdfSourceNetworkTrace.slice() : [],
              };
            } finally {
              pdfState.mode = previous.mode;
              pdfState.path = previous.path;
              pdfState.size = previous.size;
              pdfState.page = previous.page;
            }
          },
          pdfSourceWarmDownload: async (options = {}) => {
            const bytes = Math.max(1, Math.floor(Number(options.bytes || 0) || (5 * 1024 * 1024)));
            const key = clean(options.key || `pdf-warm-probe-${bytes}`);
            const previous = {
              mode: pdfState.mode,
              path: pdfState.path,
              size: pdfState.size,
              page: pdfState.page,
              lessonId: pdfState.lessonId,
            };
            try {
              pdfState.mode = "pdf";
              pdfState.path = "common/PDF/Probe/real.space_pdf";
              pdfState.size = bytes;
              pdfState.page = 1;
              pdfState.lessonId = "ftg-probe-stable-lesson";
              const result = await warmPdfSourceFileCache({
                path: "_assets/pdf/probe/real.pdf",
                size: bytes,
                lesson_id: pdfState.lessonId,
              }, { trackProgress: true });
              return {
                bytes: Number(result && result.bytes || 0) || 0,
                trace: Array.isArray(window.__ftPdfSourceNetworkTrace) ? window.__ftPdfSourceNetworkTrace.slice() : [],
              };
            } finally {
              pdfState.mode = previous.mode;
              pdfState.path = previous.path;
              pdfState.size = previous.size;
              pdfState.page = previous.page;
              pdfState.lessonId = previous.lessonId;
            }
          },
          vocabAlert: (token) => {
            const state = lessonEntryGateSequenceState;
            if (!state || state.token !== token) return false;
            state.awaitingVocabPreflight = true;
            state.vocabPreflightResolved = false;
            state.vocabAlertPending = false;
            lessonEntryGateFrame.classList.add("is-secondary-ready", "is-primary-open");
            return showLessonEntryVocabAlert({ new_count: 48, pending_count: 2, files_needed: 2 }, "preflight");
          },
          exit: (label = "Space exit DOM gate") => beginLessonExitGateTransition(() => {
            window.__ftLessonExitGateProbeResult = {
              primarySealed: lessonEntryGateFrame.classList.contains("is-primary-sealed"),
              secondaryClosed: !lessonEntryGateFrame.classList.contains("is-secondary-open"),
            };
          }, label),
        };
        if (clean(params.get("ft_xhr_probe")) === "1") {
          const output = document.createElement("output");
          output.id = "ft-entry-xhr-progress-probe-output";
          output.hidden = true;
          document.body.appendChild(output);
          window.setTimeout(async () => {
            try {
              output.textContent = JSON.stringify(await window.__ftLessonEntryGateProbe.xhrProgress());
            } catch (error) {
              output.textContent = JSON.stringify({ error: error && error.message ? error.message : String(error) });
            }
          }, 0);
        }
        if (lessonEntryGateProbeMode === "visual") {
          window.setTimeout(() => {
            const token = window.__ftLessonEntryGateProbe.begin("Lesson Vault // Space_Q");
            const pdfPreview = Math.max(0, Math.min(100, Number(params.get("ft_pdf_preview") || 0) || 0));
            if (pdfPreview > 0) {
              window.setTimeout(() => window.__ftLessonEntryGateProbe.previewPdfProgress(pdfPreview), 1150);
              return;
            }
            window.setTimeout(() => {
              void window.__ftLessonEntryGateProbe.finish(token, "Question channel ready");
            }, 1300);
          }, 250);
        }
      }

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
        // 2026-08-03: capture the route/progress identity before the exit gate can
        // clear Space runtime state. The post-animation callback must not infer it again.
        const capturedReturnLessonPath = normalizeServerPathValue(options.returnLessonPath || currentLessonStudyPath());
        const capturedReturnLessonTree = normalizeServerPathValue(
          options.returnLessonTree
          || (capturedReturnLessonPath ? serverParentPathForFile(capturedReturnLessonPath) : (serverBrowserPath || getStoredServerPath() || ""))
        );
        const capturedReturnTaskOwner = clean(options.returnTaskOwner || serverTaskOwnerContext || currentAuthUsername || "");
        const capturedQuestionProgressRecord = options.questionProgressRecord && typeof options.questionProgressRecord === "object"
          ? options.questionProgressRecord
          : (questionModeActive && typeof saveQuestionProgressNow === "function" ? saveQuestionProgressNow() : null);
        if (!options.skipLessonExitGate) {
          if (typeof stopPdfAiAssistRuntimeAudio === "function") {
            stopPdfAiAssistRuntimeAudio();
          }
          const exitLabel = clean(currentLessonSource.title || currentLessonSource.name || "Returning to Lesson Vault");
          const started = beginLessonExitGateTransition(() => {
            returnToServerFileSelection({
              ...options,
              skipLessonExitGate: true,
              returnLessonPath: capturedReturnLessonPath,
              returnLessonTree: capturedReturnLessonTree,
              returnTaskOwner: capturedReturnTaskOwner,
              questionProgressRecord: capturedQuestionProgressRecord,
            });
          }, exitLabel);
          if (started) return;
        }
        const completedBeforeReturn = Boolean(lessonCompletionSent);
        const returnLessonPath = capturedReturnLessonPath;
        const returnLessonTree = capturedReturnLessonTree;
        const returnTaskOwner = capturedReturnTaskOwner;
        const vocabProgressRecordForReturn = options.vocabProgressRecord && typeof options.vocabProgressRecord === "object"
          ? options.vocabProgressRecord
          : (vocabModeActive && currentVocabProgressCache.savedProgress && typeof currentVocabProgressCache.savedProgress === "object"
            ? currentVocabProgressCache.savedProgress
            : null);
        const spaceWProgressRecordForReturn = !capturedQuestionProgressRecord
          && !vocabModeActive && !questionModeActive && !paragraphModeActive && typeof saveSpaceWProgressNow === "function"
          ? saveSpaceWProgressNow()
          : null;
        const questionProgressRecordForReturn = capturedQuestionProgressRecord;
        const paragraphProgressRecordForReturn = paragraphModeActive ? saveParagraphProgressNow() : null;
        const returnProgressPaths = [
          ...(questionProgressRecordForReturn && typeof currentQuestionProgressPaths === "function" ? currentQuestionProgressPaths(questionProgressRecordForReturn) : []),
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
        // The group Exit can run after the mode flag is cleared by the gate;
        // retain the last durable client checkpoint as the local handoff source.
        const questionSavedRecordForReturn = questionProgressRecordForReturn
          || (currentQuestionProgressCache && currentQuestionProgressCache.savedProgress && typeof currentQuestionProgressCache.savedProgress === "object"
            ? currentQuestionProgressCache.savedProgress
            : null);
        const questionProgressOverrideForReturn = questionProgressOverrideFromRecord(questionSavedRecordForReturn);
        if (returnLessonPath && questionProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, questionProgressOverrideForReturn, 120000, { force: true });
          rememberLessonVaultProgressPin(returnProgressPaths, questionProgressOverrideForReturn, 120000);
          clearServerLessonProgressPrefetchCache(returnProgressPaths, "Space_Q");
        }
        const paragraphProgressOverrideForReturn = paragraphProgressOverrideFromRecord(paragraphProgressRecordForReturn);
        if (returnLessonPath && paragraphProgressOverrideForReturn) {
          setLessonProgressOverride(returnProgressPaths, paragraphProgressOverrideForReturn, 120000);
          rememberLessonVaultProgressPin(returnProgressPaths, paragraphProgressOverrideForReturn, 120000);
        }
        // The exit gate can clear mode flags before this callback runs. Preserve
        // the captured Space_Q checkpoint instead of manufacturing a stale
        // Space_W fallback from the now-neutral runtime state.
        const localProgressOverrideForReturn = questionSavedRecordForReturn && questionProgressOverrideForReturn
          ? questionProgressOverrideForReturn
          : (paragraphProgressRecordForReturn && paragraphProgressOverrideForReturn
            ? paragraphProgressOverrideForReturn
            : (vocabProgressRecordForReturn && vocabProgressOverrideForReturn
              ? vocabProgressOverrideForReturn
              : spaceWProgressOverrideForReturn));
        const vocabProgressSyncForReturn = Promise.resolve(null);
        const questionProgressSyncForReturn = questionSavedRecordForReturn && canUseQuestionProgressServer()
          ? sendQuestionServerProgress(questionSavedRecordForReturn).catch(() => null)
          : Promise.resolve(null);
        pendingTaskNoticeReturnTrigger = {
          id: ++taskNoticeReturnTriggerId,
          completedReturn: completedBeforeReturn,
        };
        const refreshTree = returnLessonTree || serverBrowserPath || getStoredServerPath() || "";
        // Added 2026-07-31: route first so optional Space cleanup cannot strand Exit inside the lesson.
        if (refreshTree) {
          updateFutureAppRoute("lesson_vault", {
            tree: refreshTree,
            task_owner: returnTaskOwner,
            replace: true,
          });
          setServerBrowserPanel("vault");
        }
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
        vocabAudioCacheToken += 1;
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
        if (refreshTree) {
          const forceFreshProgress = Boolean(options.forceFreshProgress);
          const hasReturnFolderCache = typeof getCachedServerBrowserListRow === "function"
            && !forceFreshProgress
            && Boolean(getCachedServerBrowserListRow(refreshTree, returnTaskOwner, { allowStale: true }));
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
          if (refreshTree && (vocabProgressRecordForReturn || spaceWProgressRecordForReturn || questionSavedRecordForReturn || paragraphProgressRecordForReturn)) {
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
          // Added 2026-08-03: a partial Space_Q Exit must re-read the canonical task board too;
          // local path pins cover the fast paint, while this closes alias/cache mismatches.
          if (returnTaskOwner && (completedBeforeReturn || questionSavedRecordForReturn)) {
            await loadLessonTasks(returnTaskOwner, { fresh: true }).catch(() => {});
            // Updated 2026-08-03: the fresh task response can finish after the
            // Exit fast-paint and replace it with an older automatic-task row.
            // Reapply the exact saved checkpoint after that response settles.
            if (localProgressOverrideForReturn) {
              setLessonProgressOverride(returnProgressPaths, localProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS, { force: true });
              rememberLessonVaultProgressPin(returnProgressPaths, localProgressOverrideForReturn, SPACE_V_LOCAL_PROGRESS_PROTECT_MS);
            }
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
        if (lessonEntryGateSequenceState && !lessonEntryGateSequenceState.primarySealComplete) {
          lessonEntryGateDeferredServerBrowserClose = true;
          return;
        }
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
      // Added 2026-08-02: fence delayed AI audio so page/lesson navigation cannot restart it after cleanup.
      var pdfAiQuestionAudioToken = 0;
      var pdfAiQuestionFeedbackAudio = null;
      var pdfAiNoticeFireballState = null;
      var pdfAiNoticeFireballTypeTimer = 0;
      var pdfAiNoticeFireballMoveTimer = 0;
      var pdfAiNoticeFireballJumpTimer = 0;
      var pdfAiNoticeFireballHideTimer = 0;
      var pdfAiNoticeFireballHoverTimer = 0;
      var pdfAiNoticeFireballDrag = null;
      var pdfAiNoticeVoiceAudio = null;
      var pdfAiNoticeAudioToken = 0;
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
      // Updated 2026-08-03: Q2 is the default, so old Q1 page PNGs must not be reused.
      // Updated 2026-08-03: restore Q1 PDF.js rendering for every PDF page.
      const PDF_PAGE_RENDER_VERSION = "pdfjs-local-q1-20260803";
      const PDF_PAGE_PERSISTENT_CACHE = "future-space-pdf-pages-v1";
      const PDF_FILE_PERSISTENT_CACHE = "future-space-pdf-files-v1";
      // Added 2026-08-03: keep enough bytes per Range request to avoid turning
      // a large source PDF into dozens of sequential auth/handle round trips.
      // The server still flushes small blocks so XHR progress remains smooth.
      const PDF_FILE_CHUNK_BYTES = 2 * 1024 * 1024;
      // Updated 2026-08-03: multi-chunk PDFs stay chunked on every reopen instead
      // of being collapsed into one full-file Cache API blob that jumps to 100%.
      const PDF_FILE_FULL_CACHE_MAX_BYTES = PDF_FILE_CHUNK_BYTES;
      const PDF_FILE_CACHE_READ_TIMEOUT_MS = 6000;
      // Added 2026-08-03: cache persistence must never hold the foreground PDF network pass.
      const PDF_FILE_CACHE_WRITE_TIMEOUT_MS = 4000;
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
