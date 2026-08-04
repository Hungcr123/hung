

      const renderSpeakResult = (payload = {}) => {
        const score = Number(payload.score || 0) || 0;
        const details = Array.isArray(payload.details) ? payload.details : [];
        if (speakScore) {
          speakScore.textContent = `${Math.round(score)}%`;
        }
        if (speakTranscript) {
          const transcriptText = clean(payload.text || payload.transcript || "");
          speakTranscript.textContent = transcriptText ? `Transcript: ${transcriptText}` : "Speech analysis did not detect clear English yet.";
        }
        if (speakMessage) {
          speakMessage.textContent = clean(payload.feedback) || `Đúng ${Number(payload.correct || 0)}/${Number(payload.total || details.length || 0)} từ.`;
        }
        if (speakWordsNode) {
          speakWordsNode.textContent = "";
          const rows = details.length ? details : scoreInputWords(clean(payload.text || "")).details.map((item) => ({
            expected: item.text,
            spoken: item.typed,
            ok: item.ok,
            similarity: item.ok ? 100 : 0,
          }));
          rows.forEach((row, rowIndex) => {
            const chip = document.createElement("span");
            chip.className = "ft-speak-word";
            chip.classList.toggle("is-ok", Boolean(row.ok));
            chip.classList.toggle("is-miss", !row.ok);
            const expectedText = clean(row.expected || row.text || "");
            const spokenText = clean(row.spoken || "");
            const speakIndex = Number.isFinite(Number(row.index)) ? Number(row.index) : rowIndex;
            chip.textContent = row.ok ? expectedText : `${expectedText}${spokenText ? ` -> ${spokenText}` : ""}`;
            chip.title = `${Math.round(Number(row.similarity || 0))}%`;
            chip.dataset.speakIndex = String(speakIndex);
            if (row.ok) {
              prepareSpaceWScoringAudioToken(chip, expectedText, speakIndex);
            }
            speakWordsNode.appendChild(chip);
          });
        }
        setSpeakStatus(score >= 78 ? "Giọng đọc ổn. Có thể nghe lại rồi đọc thêm lần nữa." : "Hãy đọc chậm hơn và nhấn rõ các từ đang đỏ.", score >= 78 ? "ok" : "error");
        scheduleDesktopPanelLayout();
      };

      const applySpeakScoringOutcome = (payload = {}, sourceLabel = "", options = {}) => {
        renderSpeakResult(payload);
        const scoreValue = Number(payload.score || 0) || 0;
        if (scoreValue > 80) {
          speakStarCount = Math.min(5, speakStarCount + 1);
          renderSpeakStars();
        }
        const speakPassed = scoreValue >= SPEAK_UNLOCK_SCORE;
        const speakUnlockedByAdmin = Boolean(spaceWSpeakSkipSessionApproved);
        const speakTone = speakUnlockedByAdmin || scoreValue >= 78 || speakPassed ? "ok" : "error";
        const scoreText = Math.round(scoreValue);
        const sourceSuffix = sourceLabel ? ` ${sourceLabel}` : "";
        const statusMessage = speakUnlockedByAdmin && !speakPassed
          ? `Speak score is ${scoreText}%, but admin already approved Speak skip for this file session. Next remains unlocked.`
          : speakPassed
            ? `Speak reached ${scoreText}%. Next is unlocked; grammar checkpoint is optional review.`
            : scoreValue >= 78
              ? "Good voice. Replay and read again if you want a cleaner result."
              : `Speak is ${scoreText}%. Record again or report an error for admin approval.`;
        setSpeakStatus(`${statusMessage}${sourceSuffix}`, speakTone);
        const shouldOfferGrammar = speakPassed && !isReviewPhase() && nextPanelCanShow && !grammarStepCompleted;
        const grammarWasWaitingForStart = Boolean(grammarState.active && grammarState.awaitingStart && !grammarStepCompleted);
        const grammarMessage = `Speak reached ${scoreText}%. Next is ready; grammar checkpoint is optional review.`;
        if (!isReviewPhase()) {
          if (speakUnlockedByAdmin || speakPassed) {
            speakStepCompleted = true;
          } else if (!grammarStepCompleted && !grammarState.active) {
            speakStepCompleted = false;
          }
          updateNextButton(true);
        }
        if (isReviewPhase() && nextPanelCanShow && completedListenCount >= requiredListenCount()) {
          reviewSpeakCompleted = speakUnlockedByAdmin || speakPassed;
          updateNextButton();
        }
        playEffectSound(speakPassed ? "true" : "false");
        queueSpaceWProgressSave(100);
        void (async () => {
          if (options.replay !== false) {
            await delay(260);
            await playSpeakReplay(true);
          }
          if (shouldOfferGrammar && !isReviewPhase() && nextPanelCanShow && !grammarStepCompleted) {
            const activateGrammar = !isMobilePanelFlow();
            if (!grammarState.active) {
              beginGrammarQuiz(grammarMessage, { activate: activateGrammar });
            } else {
              keepGrammarCheckpointAvailable(grammarMessage, { activate: activateGrammar });
            }
            if (!activateGrammar) {
              revealMobilePanel("speak");
              setActivePanel(speakPanel);
              updateSpeakConnector(true);
            }
          } else if (grammarWasWaitingForStart) {
            const activateGrammar = !isMobilePanelFlow();
            keepGrammarCheckpointAvailable(grammarState.startMessage || grammarMessage, { activate: activateGrammar });
            if (!activateGrammar) {
              revealMobilePanel("speak");
              setActivePanel(speakPanel);
              updateSpeakConnector(true);
            }
          } else if (!isReviewPhase() && !speakPassed && speakUnlockedByAdmin) {
            speakStepCompleted = true;
            updateNextButton(true);
            setSpeakReportButtonState("accepted");
            setSpeakStatus(`Speak score is ${scoreText}%. Admin skip still keeps Next unlocked for this file session.`, "ok");
          } else if (!isReviewPhase() && !speakPassed && !grammarStepCompleted && !grammarState.active) {
            setSpeakStatus(`Speak is ${scoreText}%. Next is still locked; record again or report an error for admin approval.`, "error");
          }
        })();
      };

      const fetchWhisperJson = async (path, options = {}) => {
        const errors = [];
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        for (const base of candidates) {
          try {
            const headers = await antiRobotHeaders(base, options.headers || {});
            const response = await fetch(`${base}${path}`, {
              ...options,
              headers,
              mode: "cors",
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.ok === false) {
              const error = new Error(clean(payload.error) || `Speech service lỗi ${response.status}`);
              error.isWhisperServerError = true;
              throw error;
            }
            return { base, payload, response };
          } catch (error) {
            if (error && error.isWhisperServerError) {
              throw error;
            }
            errors.push(`${base}: ${error && error.message ? error.message : error}`);
          }
        }
        const error = new Error(`Không nối được speech service. Đã thử: ${errors.join(" | ")}`);
        error.isWhisperServerError = true;
        throw error;
      };

      const unlockSpeakAfterSpeechServiceError = (error) => {
        const detail = clean(error && error.message ? error.message : error);
        speakStepCompleted = true;
        if (isReviewPhase()) {
          reviewSpeakCompleted = true;
        }
        if (speakScore) {
          speakScore.textContent = "SKIP";
        }
        if (speakMessage) {
          speakMessage.textContent = "Speech analysis service failed, so Speak was skipped for this node.";
        }
        if (speakTranscript) {
          speakTranscript.textContent = "Transcript unavailable because the speech service did not respond.";
        }
        if (speakWordsNode) {
          speakWordsNode.textContent = "";
        }
        showSpeakPanel(true);
        setSpeakStatus(`Speech service error. Speak skipped and Next is unlocked.${detail ? ` Detail: ${detail}` : ""}`, "ok");
        updateNextButton(true);
        queueSpaceWProgressSave(100);
        playEffectSound("true");
      };

      const commitSpeakRecognitionChunk = () => {
        const completedChunk = clean(speakRecognitionChunkText);
        if (completedChunk) {
          speakRecognitionTranscript = clean(`${speakRecognitionTranscript} ${completedChunk}`);
          speakRecognitionChunkText = "";
        }
      };

      const currentBrowserSpeakTranscript = () => clean(`${speakRecognitionTranscript} ${speakRecognitionChunkText}`);

      const renderBrowserSpeakLive = () => {
        const payload = browserSpeakPayload(currentBrowserSpeakTranscript());
        const elapsedMs = speakBrowserRecordingStartedAt ? performance.now() - speakBrowserRecordingStartedAt : 0;
        rememberBrowserSpeakTokenTimeline(payload, elapsedMs);
        renderSpeakResult(payload);
        setSpeakStatus(`Browser mic is listening. Detected ${Number(payload.correct || 0)}/${Number(payload.total || 0)} tokens. Press Stop mic when done.`, "");
      };

      const stopSpeakBrowserLocalRecording = (options = {}) => {
        const autoReplay = Boolean(options && options.autoReplay);
        const recorder = speakRecorder;
        if (!recorder) {
          cleanupSpeakStream();
          updateSpeakReplayButton();
          return false;
        }
        const finishLocalRecording = () => {
          const mime = recorder.mimeType || "audio/webm";
          const blob = speakChunks.length ? new Blob(speakChunks, { type: mime }) : null;
          if (speakRecorder === recorder) {
            speakRecorder = null;
          }
          speakChunks = [];
          cleanupSpeakStream();
          if (blob && blob.size) {
            setSpeakRecordedBlob(blob);
            if (autoReplay) {
              clearSpeakAutoReplayTimer();
              speakAutoReplayTimer = window.setTimeout(() => {
                speakAutoReplayTimer = 0;
                if (speakRecordedBlob === blob && !speakBusy && !speakRecognitionActive) {
                  void playSpeakReplay(true);
                }
              }, 220);
            }
          } else {
            updateSpeakReplayButton();
          }
        };
        if (recorder.state === "inactive") {
          finishLocalRecording();
          return true;
        }
        recorder.onstop = finishLocalRecording;
        try {
          recorder.stop();
        } catch (error) {
          finishLocalRecording();
        }
        return true;
      };

      const finishBrowserSpeakRecognition = () => {
        const transcript = currentBrowserSpeakTranscript();
        speakRecognitionTranscript = transcript;
        speakRecognitionChunkText = "";
        if (speakRecordButton) {
          speakRecordButton.classList.remove("is-recording");
          speakRecordButton.textContent = "Record";
        }
        if (speakModeToggleButton) {
          speakModeToggleButton.disabled = false;
        }
        stopSpeakWave("idle");
        stopSpeakBrowserLocalRecording({ autoReplay: true });
        updateSpeakReplayButton();
        if (!transcript && speakRecognitionLastError) {
          setSpeakStatus(`Browser voice check stopped: ${speakRecognitionLastError}`, "error");
          return;
        }
        const payload = browserSpeakPayload(transcript);
        const elapsedMs = speakBrowserRecordingStartedAt ? performance.now() - speakBrowserRecordingStartedAt : 0;
        rememberBrowserSpeakTokenTimeline(payload, elapsedMs);
        applySpeakScoringOutcome(payload, "Browser voice check.", { replay: false });
      };

      const stopSpeakBrowserRecognition = (finalize = true) => {
        const recognition = speakRecognition;
        speakRecognitionActive = false;
        speakRecognitionManualStop = true;
        if (!recognition) {
          if (finalize) {
            finishBrowserSpeakRecognition();
          }
          return;
        }
        recognition.onend = () => {
          if (finalize) {
            commitSpeakRecognitionChunk();
          } else {
            speakRecognitionChunkText = "";
          }
          if (speakRecognition === recognition) {
            speakRecognition = null;
          }
          if (finalize) {
            finishBrowserSpeakRecognition();
          }
        };
        try {
          recognition.stop();
        } catch (error) {
          try {
            recognition.abort();
          } catch (abortError) {
          }
          if (speakRecognition === recognition) {
            speakRecognition = null;
          }
          if (finalize) {
            finishBrowserSpeakRecognition();
          }
        }
      };

      const stopLessonAudioBeforeSpeakRecording = () => {
        if (typeof stopActiveAudio === "function") {
          stopActiveAudio();
        }
        if (typeof stopGrammarAudio === "function") {
          stopGrammarAudio();
        }
        if (typeof stopSpeakReplay === "function") {
          stopSpeakReplay();
        }
        if (typeof setPlaybackState === "function") {
          setPlaybackState(false);
        }
      };

      const startSpeakBrowserRecognition = async () => {
        if (completedListenCount < requiredListenCount()) {
          showSpeakPanel(true);
          setSpeakStatus(`Listen to the full English sentence ${requiredListenCount()} time(s) before Speak.`, "error");
          setTtsStatus(listenStatusText(), true);
          return;
        }
        const RecognitionCtor = browserSpeechRecognitionCtor();
        if (!RecognitionCtor) {
          setSpeakStatus("This browser does not support live speech recognition. Turn AI check voice ON to use server analysis.", "error");
          return;
        }
        showSpeakPanel(true);
        stopLessonAudioBeforeSpeakRecording();
        cancelSpeakRecording();
        clearSpeakRecording();
        resetSpeakScoringDisplay();
        speakBrowserRecordingStartedAt = performance.now();
        speakBrowserTokenTimeline = [];
        clearSpeakReplayTokenHighlight();
        let localRecordingReady = false;
        if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function" && window.MediaRecorder) {
          try {
            speakStream = await navigator.mediaDevices.getUserMedia({
              audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
              },
            });
            const mimeType = selectedRecorderMime();
            speakChunks = [];
            speakRecorder = new MediaRecorder(speakStream, mimeType ? { mimeType } : undefined);
            speakRecorder.ondataavailable = (event) => {
              if (event.data && event.data.size) {
                speakChunks.push(event.data);
              }
            };
            speakRecorder.onerror = () => {
              setSpeakStatus("Browser voice check is still listening, but local replay recording had an error.", "error");
            };
            speakRecorder.start(250);
            localRecordingReady = true;
          } catch (error) {
            speakRecorder = null;
            speakChunks = [];
            cleanupSpeakStream();
          }
        }
        speakRecognitionTranscript = "";
        speakRecognitionChunkText = "";
        speakRecognitionLastError = "";
        const recognition = new RecognitionCtor();
        speakRecognition = recognition;
        speakRecognitionActive = true;
        speakRecognitionManualStop = false;
        recognition.lang = "en-US";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.onresult = (event) => {
          const parts = [];
          const results = event && event.results ? event.results : [];
          for (let index = 0; index < results.length; index += 1) {
            const result = results[index];
            const text = clean(result && result[0] && result[0].transcript);
            if (text) {
              parts.push(text);
            }
          }
          speakRecognitionChunkText = clean(parts.join(" "));
          renderBrowserSpeakLive();
        };
        recognition.onerror = (event) => {
          const code = clean(event && event.error);
          if (code && code !== "no-speech") {
            speakRecognitionLastError = code;
          }
          if (code === "not-allowed" || code === "service-not-allowed") {
            speakRecognitionActive = false;
            speakRecognitionManualStop = true;
          }
        };
        recognition.onend = () => {
          if (speakRecognition !== recognition) {
            return;
          }
          commitSpeakRecognitionChunk();
          if (speakRecognitionActive && !speakRecognitionManualStop) {
            window.setTimeout(() => {
              if (speakRecognition === recognition && speakRecognitionActive && !speakRecognitionManualStop) {
                try {
                  recognition.start();
                } catch (error) {
                  speakRecognitionActive = false;
                  speakRecognitionManualStop = true;
                  speakRecognitionLastError = clean(error && error.message ? error.message : error) || speakRecognitionLastError;
                  finishBrowserSpeakRecognition();
                }
              }
            }, 120);
            return;
          }
          speakRecognition = null;
          finishBrowserSpeakRecognition();
        };
        try {
          recognition.start();
          if (localRecordingReady && speakStream) {
            await startSpeakStreamWave(speakStream);
          } else {
            startSpeakWave("recording", null);
          }
          if (speakRecordButton) {
            speakRecordButton.classList.add("is-recording");
            speakRecordButton.textContent = "Stop mic";
          }
          if (speakModeToggleButton) {
            speakModeToggleButton.disabled = true;
          }
          updateSpeakReplayButton();
          setSpeakStatus("Browser mic is listening. Read freely; any correct token will light up.", "");
          playEffectSound("open");
        } catch (error) {
          speakRecognition = null;
          speakRecognitionActive = false;
          speakRecognitionManualStop = false;
          if (speakRecorder && speakRecorder.state !== "inactive") {
            try {
              speakRecorder.onstop = null;
              speakRecorder.stop();
            } catch (stopError) {
            }
          }
          speakRecorder = null;
          speakChunks = [];
          speakBrowserRecordingStartedAt = 0;
          speakBrowserTokenTimeline = [];
          clearSpeakReplayTokenHighlight();
          cleanupSpeakStream();
          stopSpeakWave("idle");
          setSpeakStatus(`Could not start browser voice check: ${error && error.message ? error.message : error}`, "error");
        }
      };

      const submitSpeakRecording = async (blob) => {
        if (!blob || !blob.size) {
          setSpeakStatus("Chưa có âm thanh để chấm.", "error");
          return;
        }
        setSpeakBusy(true);
        setActivePanel(speakPanel);
        startSpeakProcessingWave();
        setSpeakStatus("Đang gửi audio tới speech analysis...", "");
        try {
          const form = new FormData();
          const mime = clean(blob.type) || "audio/webm";
          form.append("audio", blob, `future-speaking.${speakAudioExtension(mime)}`);
          form.append("expected", clean(englishNode.textContent));
          form.append("language", "en");
          form.append("model", WHISPER_MODEL);
          form.append("source", "space_w");
          const result = await fetchWhisperJson("/transcribe", {
            method: "POST",
            body: form,
          });
          const payload = result.payload || {};
          rememberServerSpeakTokenTimeline(payload);
          renderSpeakResult(payload);
          const speakScore = Number(payload.score || 0) || 0;
          if (speakScore > 80) {
            speakStarCount = Math.min(5, speakStarCount + 1);
            renderSpeakStars();
          }
          const speakPassed = speakScore >= SPEAK_UNLOCK_SCORE;
          const speakUnlockedByAdmin = Boolean(spaceWSpeakSkipSessionApproved);
          const speakTone = speakUnlockedByAdmin || speakScore >= 78 || speakPassed ? "ok" : "error";
          const speakScoreText = Math.round(speakScore);
          const speakMessage = speakUnlockedByAdmin && !speakPassed
            ? `Speak score is ${speakScoreText}%, but admin already approved Speak skip for this file session. Next remains unlocked.`
            : speakPassed
            ? `Speak đạt ${speakScoreText}%. Next đã mở; grammar checkpoint là phần ôn thêm.`
            : speakScore >= 78
              ? "Giọng đọc ổn. Có thể nghe lại rồi đọc thêm lần nữa."
              : `Speak hiện tại ${speakScoreText}%. Bạn có thể ghi âm lại để luyện phát âm rõ hơn.`;
          setSpeakStatus(`${speakMessage} Server: ${result.base}`, speakTone);
          const shouldOfferGrammar = speakPassed && !isReviewPhase() && nextPanelCanShow && !grammarStepCompleted;
          const grammarWasWaitingForStart = Boolean(grammarState.active && grammarState.awaitingStart && !grammarStepCompleted);
          const grammarMessage = `Speak đạt ${speakScoreText}%. Next đã sẵn sàng; có thể mở grammar checkpoint để ôn thêm.`;
          if (!isReviewPhase()) {
            if (speakUnlockedByAdmin || speakPassed) {
              speakStepCompleted = true;
            } else if (!grammarStepCompleted && !grammarState.active) {
              speakStepCompleted = false;
            }
            updateNextButton(true);
          }
          if (isReviewPhase() && nextPanelCanShow && completedListenCount >= requiredListenCount()) {
            reviewSpeakCompleted = speakUnlockedByAdmin || speakPassed;
            updateNextButton();
          }
          playEffectSound(speakPassed ? "true" : "false");
          queueSpaceWProgressSave(100);
          void (async () => {
            await delay(260);
            await playSpeakReplay(true);
            if (shouldOfferGrammar && !isReviewPhase() && nextPanelCanShow && !grammarStepCompleted) {
              const activateGrammar = !isMobilePanelFlow();
              if (!grammarState.active) {
                beginGrammarQuiz(grammarMessage, { activate: activateGrammar });
              } else {
                keepGrammarCheckpointAvailable(grammarMessage, { activate: activateGrammar });
              }
              if (!activateGrammar) {
                revealMobilePanel("speak");
                setActivePanel(speakPanel);
                updateSpeakConnector(true);
              }
            } else if (grammarWasWaitingForStart) {
              const activateGrammar = !isMobilePanelFlow();
              keepGrammarCheckpointAvailable(grammarState.startMessage || grammarMessage, { activate: activateGrammar });
              if (!activateGrammar) {
                revealMobilePanel("speak");
                setActivePanel(speakPanel);
                updateSpeakConnector(true);
              }
            } else if (!isReviewPhase() && !speakPassed && speakUnlockedByAdmin) {
              speakStepCompleted = true;
              updateNextButton(true);
              setSpeakReportButtonState("accepted");
              setSpeakStatus(`Speak score is ${speakScoreText}%. Admin skip still keeps Next unlocked for this file session.`, "ok");
            } else if (!isReviewPhase() && !speakPassed && !grammarStepCompleted && !grammarState.active) {
              setSpeakStatus(`Speak hiện tại ${speakScoreText}%. Next vẫn khóa; hãy ghi âm lại hoặc báo lỗi để admin duyệt bỏ qua.`, "error");
            }
          })();
        } catch (error) {
          if (error && error.isWhisperServerError) {
            if (browserSpeechRecognitionCtor()) {
              speakAiCheckVoiceFallbackActive = true;
              setSpeakAiCheckVoice(false, false);
              setSpeakStatus(`Whisper connection failed. Falling back to browser live voice check: ${error && error.message ? error.message : error}`, "error");
              window.setTimeout(() => {
                if (!speakBusy && !speakRecognitionActive && !speakRecognition) {
                  void startSpeakBrowserRecognition();
                }
              }, 0);
            } else {
              unlockSpeakAfterSpeechServiceError(error);
            }
          } else {
            setSpeakStatus(`Không chấm được giọng: ${error && error.message ? error.message : error}. Hãy kiểm tra speech service trên server.`, "error");
          }
        } finally {
          setSpeakBusy(false);
          if (speakRecordButton) {
            speakRecordButton.textContent = "Record";
          }
          if (speakWaveMode === "processing") {
            stopSpeakWave(speakRecordedBlob ? "ready" : "idle");
          }
        }
      };

      const stopSpeakRecording = () => {
        if (!speakRecorder || speakRecorder.state === "inactive") {
          return;
        }
        setSpeakStatus("Đang xử lý bản ghi...", "");
        void primeSpeakReplayAutoplay();
        try {
          speakRecorder.stop();
        } catch (error) {
          setSpeakStatus("Không dừng được ghi âm.", "error");
        }
      };

      const startSpeakRecording = async () => {
        if (completedListenCount < requiredListenCount()) {
          showSpeakPanel(true);
          setSpeakStatus(`Hãy nghe trọn câu tiếng Anh ${requiredListenCount()} lần trước khi Speak.`, "error");
          setTtsStatus(listenStatusText(), true);
          return;
        }
        showSpeakPanel(true);
        if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function" || !window.MediaRecorder) {
          setSpeakStatus("Trình duyệt chưa hỗ trợ ghi âm bằng MediaRecorder.", "error");
          return;
        }
        stopLessonAudioBeforeSpeakRecording();
        cancelSpeakRecording();
        clearSpeakRecording();
        resetSpeakScoringDisplay();
        void primeSpeakReplayAutoplay();
        try {
          speakStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
          const mimeType = selectedRecorderMime();
          speakChunks = [];
          speakRecorder = new MediaRecorder(speakStream, mimeType ? { mimeType } : undefined);
          speakRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size) {
              speakChunks.push(event.data);
            }
          };
          speakRecorder.onerror = () => {
            setSpeakStatus("Ghi âm bị lỗi, hãy thử lại.", "error");
          };
          speakRecorder.onstop = () => {
            const blob = new Blob(speakChunks, { type: speakRecorder.mimeType || mimeType || "audio/webm" });
            speakRecorder = null;
            speakChunks = [];
            cleanupSpeakStream();
            setSpeakRecordedBlob(blob);
            startSpeakProcessingWave();
            if (speakRecordButton) {
              speakRecordButton.classList.remove("is-recording");
              speakRecordButton.textContent = "Record";
            }
            updateSpeakReplayButton();
            void submitSpeakRecording(blob);
          };
          speakRecorder.start(250);
          await startSpeakStreamWave(speakStream);
          if (speakRecordButton) {
            speakRecordButton.classList.add("is-recording");
            speakRecordButton.textContent = "Stop & score";
          }
          if (speakModeToggleButton) {
            speakModeToggleButton.disabled = true;
          }
          updateSpeakReplayButton();
          setSpeakStatus("Đang ghi âm... đọc trọn câu tiếng Anh rồi bấm Stop.", "");
          playEffectSound("open");
        } catch (error) {
          cleanupSpeakStream();
          if (speakModeToggleButton) {
            speakModeToggleButton.disabled = false;
          }
          setSpeakStatus(`Không mở được micro: ${error && error.message ? error.message : error}`, "error");
        }
      };

      let speakRecordStartCheckBusy = false;
      const toggleSpeakRecording = async () => {
        if (speakBusy) {
          return;
        }
        if (!speakAiCheckVoice) {
          if (speakRecognitionActive || speakRecognition) {
            stopSpeakBrowserRecognition(true);
            return;
          }
          if (speakRecordStartCheckBusy) {
            return;
          }
          speakRecordStartCheckBusy = true;
          try {
            // Record must not wait on /settings; browser scoring is the safe OFF-mode default.
            await startSpeakBrowserRecognition();
          } finally {
            speakRecordStartCheckBusy = false;
          }
          return;
        }
        if (speakRecorder && speakRecorder.state === "recording") {
          stopSpeakRecording();
          return;
        }
        if (speakRecordStartCheckBusy) {
          return;
        }
        speakRecordStartCheckBusy = true;
        try {
          // The mode is already synchronized from server settings; never gate Record on a live settings request.
          if (!speakAiCheckVoice || speakAiCheckVoiceServerManaged) {
            await startSpeakBrowserRecognition();
            return;
          }
          await startSpeakRecording();
        } finally {
          speakRecordStartCheckBusy = false;
        }
      };

      const grammarPosLabels = {
        ADJ: "Tính từ",
        ADP: "Giới từ",
        ADV: "Trạng từ",
        AUX: "Trợ động từ",
        CCONJ: "Liên từ đẳng lập",
        DET: "Từ hạn định",
        INTJ: "Thán từ",
        NOUN: "Danh từ",
        NUM: "Số từ",
        PART: "Tiểu từ",
        PRON: "Đại từ",
        PROPN: "Danh từ riêng",
        PUNCT: "Dấu câu",
        SCONJ: "Liên từ phụ thuộc",
        SYM: "Ký hiệu",
        VERB: "Động từ",
        X: "Từ chưa xác định",
      };
      const grammarDepLabels = {
        ROOT: "Trung tâm vị ngữ của câu",
        acl: "Mệnh đề bổ nghĩa cho danh từ",
        acomp: "Bổ ngữ tính từ",
        advcl: "Mệnh đề trạng ngữ",
        advmod: "Trạng ngữ",
        agent: "Tác nhân trong câu bị động",
        amod: "Bổ nghĩa bằng tính từ",
        appos: "Đồng vị",
        attr: "Bổ ngữ cho chủ ngữ",
        aux: "Trợ động từ",
        auxpass: "Trợ động từ bị động",
        case: "Dấu hiệu quan hệ",
        cc: "Liên từ nối",
        ccomp: "Mệnh đề bổ ngữ",
        compound: "Thành phần ghép danh từ",
        conj: "Thành phần song song",
        csubj: "Chủ ngữ dạng mệnh đề",
        dep: "Quan hệ phụ thuộc khác",
        det: "Từ hạn định cho danh từ",
        dobj: "Tân ngữ trực tiếp",
        expl: "Chủ ngữ giả",
        intj: "Thán ngữ",
        mark: "Dấu hiệu mệnh đề phụ",
        neg: "Từ phủ định",
        nmod: "Bổ nghĩa danh từ",
        npadvmod: "Cụm danh từ làm trạng ngữ",
        nsubj: "Chủ ngữ",
        nsubjpass: "Chủ ngữ bị động",
        nummod: "Bổ nghĩa số lượng",
        obj: "Tân ngữ",
        oprd: "Bổ ngữ cho tân ngữ",
        parataxis: "Cấu trúc chen ngang",
        pobj: "Tân ngữ của giới từ",
        poss: "Sở hữu",
        predet: "Từ hạn định đứng trước",
        prep: "Cụm giới từ",
        prt: "Tiểu từ trong cụm động từ",
        punct: "Dấu câu",
        quantmod: "Bổ nghĩa lượng từ",
        relcl: "Mệnh đề quan hệ",
        xcomp: "Bổ ngữ động từ mở",
      };
      const grammarQuestionPrompts = {
        pos: "Loại từ của từ sau là gì? {word}",
        dep: "Vai trò ngữ pháp của từ sau là gì? {word}",
        head: "Từ sau phụ thuộc vào từ trung tâm nào? {word}",
      };
      const grammarFallbackOptions = {
        pos: Object.keys(grammarPosLabels),
        dep: ["nsubj", "ROOT", "obj", "dobj", "pobj", "amod", "det", "prep", "aux", "advmod", "compound", "poss"],
        head: [],
      };

      const grammarReadableLabel = (value) => {
        let text = clean(value);
        [" - ", " – ", " — ", ": "].some((separator) => {
          if (!text.includes(separator)) {
            return false;
          }
          text = clean(text.split(separator).pop());
          return true;
        });
        return text;
      };

      const grammarDisplayValue = (type, value, item = null) => {
        const raw = clean(value);
        if (!raw) {
          return "";
        }
        if (type === "pos") {
          const readable = grammarReadableLabel(raw);
          if (readable !== raw) return readable;
          return grammarPosLabels[raw.toUpperCase()] || raw;
        }
        if (type === "dep") {
          const readable = grammarReadableLabel(raw);
          if (readable !== raw) return readable;
          return grammarDepLabels[raw] || grammarDepLabels[raw.toLowerCase()] || raw;
        }
        if (type === "head") {
          const word = clean(item && item.word && item.word.text);
          return word && grammarAnswerKey(raw) === grammarAnswerKey(word)
            ? `${raw} (từ trung tâm của chính nó)`
            : raw;
        }
        return raw;
      };

      const grammarTypeText = (type) => {
        if (type === "pos") return "loại từ";
        if (type === "dep") return "vai trò ngữ pháp";
        if (type === "head") return "từ trung tâm";
        return "phân tích";
      };

      const renderGrammarPromptText = (item) => {
        grammarPrompt.textContent = "";
        const template = clean(item.prompt) || grammarQuestionPrompts[item.type] || "Chọn đáp án đúng cho từ sau. {word}";
        const targetWord = clean(item.word && item.word.text) || "từ này";
        const safeTemplate = template.includes("{word}") ? template : `${template} {word}`;
        const parts = safeTemplate.split("{word}");
        grammarPrompt.appendChild(document.createTextNode(parts[0] || ""));
        const wordSpan = document.createElement("span");
        wordSpan.className = "ft-grammar-question-word";
        wordSpan.textContent = targetWord;
        grammarPrompt.appendChild(wordSpan);
        grammarPrompt.appendChild(document.createTextNode(parts.slice(1).join(targetWord)));
      };

      const renderGrammarTargetText = (item) => {
        if (!grammarTarget) {
          return;
        }
        grammarTarget.hidden = true;
        grammarTarget.setAttribute("aria-hidden", "true");
        grammarTarget.textContent = "";
      };

      const grammarAnswerKey = (value) => clean(value).toLowerCase();

      const grammarOptionKey = (type, value, item = null) => {
        if (type === "pos" || type === "dep") {
          return grammarAnswerKey(grammarDisplayValue(type, value, item));
        }
        return grammarAnswerKey(value);
      };

      const uniqueGrammarValues = (values) => {
        const seen = new Set();
        return values.map(clean).filter(Boolean).filter((value) => {
          const key = grammarAnswerKey(value);
          if (!key || seen.has(key)) {
            return false;
          }
          seen.add(key);
          return true;
        });
      };

      const uniqueGrammarOptions = (type, values, item = null) => {
        const seen = new Set();
        return (Array.isArray(values) ? values : []).map(clean).filter(Boolean).filter((value) => {
          const key = grammarOptionKey(type, value, item);
          if (!key || seen.has(key)) {
            return false;
          }
          seen.add(key);
          return true;
        });
      };

      const grammarHash = (value) => {
        const raw = String(value || "");
        let hash = 2166136261;
        for (let index = 0; index < raw.length; index += 1) {
          hash ^= raw.charCodeAt(index);
          hash = Math.imul(hash, 16777619) >>> 0;
        }
        return hash;
      };

      const grammarShuffle = (values, seed) => values.slice().sort((a, b) => grammarHash(`${seed}:${a}`) - grammarHash(`${seed}:${b}`));
      const grammarShuffleBy = (values, seed, keyFn) => values.slice().sort((a, b) => {
        const aKey = typeof keyFn === "function" ? keyFn(a) : String(a);
        const bKey = typeof keyFn === "function" ? keyFn(b) : String(b);
        return grammarHash(`${seed}:${aKey}`) - grammarHash(`${seed}:${bKey}`);
      });

      const normalizeGrammarWord = (raw, fallback = null) => {
        const source = raw && typeof raw === "object" ? raw : {};
        const fallbackWord = fallback && typeof fallback === "object" ? fallback : {};
        return {
          text: clean(source.text ?? source.t ?? fallbackWord.text ?? ""),
          norm: normalizeWord(source.norm ?? source.n ?? source.text ?? source.t ?? fallbackWord.norm ?? fallbackWord.text ?? ""),
          ipa: clean(source.ipa ?? source.i ?? fallbackWord.ipa ?? ""),
          lemma: clean(source.lemma ?? source.l ?? fallbackWord.lemma ?? ""),
          pos: clean(source.pos ?? source.p ?? fallbackWord.pos ?? ""),
          dep: clean(source.dep ?? source.d ?? fallbackWord.dep ?? ""),
          head: clean(source.head ?? source.h ?? fallbackWord.head ?? ""),
          meaning: clean(source.meaning ?? source.m ?? source.viet ?? fallbackWord.meaning ?? ""),
        };
      };

      const normalizeGrammarBankItem = (raw, fallbackWords = []) => {
        if (!raw || typeof raw !== "object") {
          return null;
        }
        const wordIndex = Math.max(0, Number(raw.wordIndex ?? raw.wi ?? raw.index ?? 0) || 0);
        const word = normalizeGrammarWord(raw.word ?? raw.w, fallbackWords[wordIndex]);
        const type = clean(raw.type ?? raw.ty ?? raw.kind);
        const answer = clean(raw.answer ?? raw.a ?? word[type]);
        if (!type || !answer || !word.text) {
          return null;
        }
        return {
          type,
          answer,
          word,
          wordIndex,
          englishVoice: clean(raw.englishVoice ?? raw.ev ?? raw.voice ?? raw.vc),
          prompt: clean(raw.prompt ?? raw.qp ?? raw.promptText ?? raw.pt),
          options: Array.isArray(raw.options ?? raw.op) ? (raw.options ?? raw.op).map(clean).filter(Boolean) : [],
          questionAudio: raw.questionAudio ?? raw.question_audio ?? raw.qau ?? raw.qa,
          optionAudio: raw.optionAudio ?? raw.option_audio ?? raw.oa ?? {},
          feedbackAudio: raw.feedbackAudio ?? raw.feedback_audio ?? raw.fb ?? {},
        };
      };

      const getNodeGrammarBank = () => {
        const raw = currentNode && (currentNode.grammar_questions ?? currentNode.gq ?? currentNode.grammarQuiz);
        if (!Array.isArray(raw) || !raw.length) {
          return [];
        }
        const words = getNodeScoringWords(currentNode);
        return raw.map((item) => normalizeGrammarBankItem(item, words)).filter(Boolean);
      };

      const buildGrammarQuizItems = () => {
        const bankItems = getNodeGrammarBank();
        if (bankItems.length) {
          const seed = `${Date.now()}:${Math.random()}:${currentNodeIndex}:bank`;
          return grammarShuffleBy(bankItems, seed, (item) => `${item.wordIndex}:${item.type}:${item.answer}`).slice(0, Math.min(10, bankItems.length));
        }
        const words = getNodeScoringWords(currentNode);
        const candidates = [];
        words.forEach((word, wordIndex) => {
          if (word.pos) candidates.push({ type: "pos", answer: word.pos, word, wordIndex });
          if (word.dep) candidates.push({ type: "dep", answer: word.dep, word, wordIndex });
          if (word.head) candidates.push({ type: "head", answer: word.head, word, wordIndex });
        });
        if (!candidates.length) {
          return [];
        }
        const seed = `${Date.now()}:${Math.random()}:${currentNodeIndex}`;
        return grammarShuffleBy(candidates, seed, (entry) => `${entry.wordIndex}:${entry.type}:${entry.answer}`)
          .slice(0, Math.min(10, candidates.length))
          .filter((item) => clean(item.answer));
      };

      const buildGrammarOptions = (item) => {
        const words = getNodeScoringWords(currentNode);
        const answer = clean(item && item.answer);
        let pool = [];
        if (Array.isArray(item.options) && item.options.length) {
          pool = item.options.concat([answer]);
        } else if (item.type === "head") {
          pool = words.map((word) => word.text).concat(words.map((word) => word.head));
        } else {
          pool = words.map((word) => word[item.type]).concat(grammarFallbackOptions[item.type] || []);
        }
        const answerKey = grammarOptionKey(item.type, answer, item);
        const distractors = uniqueGrammarOptions(item.type, pool, item)
          .filter((value) => grammarOptionKey(item.type, value, item) !== answerKey)
          .slice(0, 12);
        const seed = `${grammarState.shuffleSeed}:${grammarState.revision}:${item.wordIndex}-${item.type}`;
        const selected = grammarShuffle(distractors, seed).slice(0, 3);
        return grammarShuffle(uniqueGrammarOptions(item.type, [answer].concat(selected), item), `final-${seed}`);
      };

      const grammarOptionAudioFor = (item, value) => {
        const source = item && item.optionAudio && typeof item.optionAudio === "object" ? item.optionAudio : {};
        const exact = source[value];
        const wanted = grammarOptionKey(item && item.type, value, item);
        const match = Object.keys(source).find((key) => grammarOptionKey(item && item.type, key, item) === wanted);
        const fallback = exact || (match ? source[match] : null);
        if (item && item.type === "head") {
          return { kind: "speak", text: clean(value), fallback };
        }
        return fallback;
      };

      const grammarQuestionAudioSequence = (item, options = [], includeOptionAudio = true) => {
        const sequence = normalizeAudioSequence(item && item.questionAudio);
        if (item && item.word && clean(item.word.text) && sequence.length >= 3) {
          sequence.splice(1, 1, { kind: "speak", text: clean(item.word.text), fallback: [sequence[1]] });
        }
        if (includeOptionAudio) {
          options.forEach((option) => {
            sequence.push(...normalizeAudioSequence(grammarOptionAudioFor(item, option)));
          });
        }
        return sequence;
      };

      const grammarFeedbackAudioSequence = (item, ok) => {
        const source = item && item.feedbackAudio && typeof item.feedbackAudio === "object" ? item.feedbackAudio : {};
        const sequence = normalizeAudioSequence(ok ? (source.ok ?? source.true ?? source.correct) : (source.wrong ?? source.false ?? source.fall));
        if (item && item.type === "head" && clean(item.answer) && sequence.length >= 2) {
          sequence.splice(1, 1, { kind: "speak", text: clean(item.answer), fallback: [sequence[1]] });
        }
        return sequence;
      };

      const nodeQuestionAudioSequence = (node = currentNode) => normalizeAudioSequence(node && (node.question_audio ?? node.questionAudio ?? node.vq));

      const playNodeQuestionAudio = (node = currentNode) => {
        const sequence = nodeQuestionAudioSequence(node);
        if (!sequence.length) {
          return;
        }
        void playGrammarAudioSequence(sequence);
      };

      const setGrammarOptionsLocked = (locked) => {
        grammarState.lock = Boolean(locked);
        if (!grammarOptionsNode) {
          return;
        }
        Array.from(grammarOptionsNode.querySelectorAll(".ft-grammar-option")).forEach((node) => {
          node.disabled = Boolean(locked);
        });
      };

      const updateGrammarSilentButton = () => {
        if (!grammarSilentButton) {
          return;
        }
        grammarSilentButton.classList.toggle("is-active", grammarKeepSilent);
        grammarSilentButton.setAttribute("aria-pressed", grammarKeepSilent ? "true" : "false");
        grammarSilentButton.textContent = grammarKeepSilent ? "Silent on" : "Keep silent";
      };

      const updateGrammarSkipButton = () => {
        if (!grammarSkipButton) {
          return;
        }
        const enabled = Boolean(grammarState.active && grammarState.awaitingCorrectAdvance);
        grammarSkipButton.disabled = !enabled;
        grammarSkipButton.classList.toggle("is-active", enabled);
      };

      const setGrammarStartVisible = (visible) => {
        if (grammarStartGate) {
          grammarStartGate.classList.toggle("is-hidden", !visible);
        }
        if (grammarStartButton) {
          grammarStartButton.disabled = !visible;
        }
      };

      const updateGrammarConnector = (makeActive = true, options = {}) => {
        if (!grammarPanel || !grammarPanel.classList.contains("is-live")) {
          return;
        }
        const shouldPan = options && Object.prototype.hasOwnProperty.call(options, "pan")
          ? Boolean(options.pan)
          : Boolean(makeActive);
        const activeConnector = connectorForPanel(grammarPanel);
        activeConnector.classList.remove("is-live", "is-complete", "is-dim");
        if (makeActive) {
          setActivePanel(grammarPanel);
        }
        positionConnectorTo(grammarPanel);
        void activeConnector.offsetWidth;
        activeConnector.classList.add("is-live");
        if (makeActive) {
          setActivePanel(grammarPanel);
        }
        if (shouldPan) {
          autoPanToPanel(grammarPanel);
        }
        window.setTimeout(() => {
          activeConnector.classList.add("is-complete");
          if (makeActive) {
            setActivePanel(grammarPanel);
          }
        }, Math.max(120, CONNECTOR_DRAW_MS - 90));
      };

      const showGrammarStartPanel = (message = "", options = {}) => {
        if (!grammarPanel) {
          return;
        }
        const activate = !(options && options.activate === false);
        grammarPanel.classList.remove("is-correct", "is-wrong", "is-locked");
        grammarPanel.classList.add("is-live");
        if (activate) {
          revealMobilePanel("grammar");
        } else {
          setMobilePanelUnlocked("grammar", true);
          syncMobilePanelTabs();
        }
        grammarState.awaitingStart = true;
        grammarState.started = false;
        grammarState.lock = true;
        setGrammarStartVisible(true);
        updateGrammarSkipButton();
        if (grammarProgress) {
          grammarProgress.textContent = `${grammarState.items.length || 0} Q`;
        }
        if (grammarPrompt) {
          grammarPrompt.textContent = "Grammar checkpoint is ready.";
        }
        if (grammarTarget) {
          grammarTarget.hidden = true;
          grammarTarget.setAttribute("aria-hidden", "true");
          grammarTarget.textContent = "";
        }
        if (grammarOptionsNode) {
          grammarOptionsNode.textContent = "";
        }
        if (grammarFeedback) {
          const displayMessage = clean(message);
          grammarFeedback.textContent = /^[\x00-\x7F]*$/.test(displayMessage) && displayMessage
            ? displayMessage
            : "Speak is complete. Press Start to launch grammar checkpoint.";
          grammarFeedback.classList.remove("is-error");
          grammarFeedback.classList.add("is-ok");
        }
        updateGrammarConnector(activate, { pan: activate });
      };

      const grammarQuestionIsRendered = () => Boolean(
        grammarOptionsNode && grammarOptionsNode.querySelector(".ft-grammar-option")
      );

      const keepGrammarCheckpointAvailable = (message = "", options = {}) => {
        if (!grammarPanel || isReviewPhase() || grammarStepCompleted) {
          return false;
        }
        if (!grammarState.active) {
          return false;
        }
        const shouldWaitForStart = Boolean(
          grammarState.awaitingStart ||
          (grammarState.started === false && grammarState.index === 0 && !grammarQuestionIsRendered())
        );
        if (shouldWaitForStart) {
          grammarState.awaitingStart = true;
          grammarState.started = false;
          showGrammarStartPanel(message || grammarState.startMessage || "", options);
          return true;
        }
        if (!grammarQuestionIsRendered() && grammarState.index < grammarState.items.length) {
          renderGrammarQuestion({ silent: true });
          return true;
        }
        if (!grammarPanel.classList.contains("is-live")) {
          grammarPanel.classList.add("is-live");
          if (options && options.activate === false) {
            setMobilePanelUnlocked("grammar", true);
            syncMobilePanelTabs();
          } else {
            revealMobilePanel("grammar");
          }
          updateGrammarConnector(!(options && options.activate === false), { pan: !(options && options.activate === false) });
        }
        return true;
      };

      const startGrammarQuizFromGate = () => {
        if (!grammarState.active || !grammarState.awaitingStart) {
          return;
        }
        grammarState.awaitingStart = false;
        grammarState.started = true;
        grammarState.lock = false;
        setGrammarStartVisible(false);
        renderGrammarQuestion();
      };

      const toggleGrammarSilent = () => {
        grammarKeepSilent = !grammarKeepSilent;
        updateGrammarSilentButton();
      };

      const skipGrammarQuestion = () => {
        if (!grammarState.active || !grammarState.awaitingCorrectAdvance) {
          return;
        }
        stopGrammarAudio();
        const expectedIndex = Number(grammarState.awaitingIndex ?? grammarState.index) || 0;
        grammarState.awaitingCorrectAdvance = false;
        grammarState.skipFeedback = true;
        grammarState.index = Math.max(grammarState.index, expectedIndex + 1);
        if (grammarFeedback) {
          grammarFeedback.textContent = "Đã bỏ qua phần đọc phản hồi.";
          grammarFeedback.classList.remove("is-ok", "is-error");
        }
        updateGrammarSkipButton();
        renderGrammarQuestion();
      };

      const setGrammarFocus = (item) => {
        const result = scoreInputWords(answerInput.value);
        const typed = result.typedWords[item.wordIndex];
        grammarFocusRange = typed ? { start: typed.start, end: typed.end } : null;
        renderAnswerHighlight(result);
      };

      const markGrammarEffect = (className) => {
        if (!grammarPanel) {
          return;
        }
        if (grammarEffectTimer) {
          window.clearTimeout(grammarEffectTimer);
          grammarEffectTimer = 0;
        }
        grammarPanel.classList.remove("is-correct", "is-wrong");
        void grammarPanel.offsetWidth;
        grammarPanel.classList.add(className);
        grammarEffectTimer = window.setTimeout(() => {
          grammarPanel.classList.remove(className);
          grammarEffectTimer = 0;
        }, 820);
      };

      const lockGrammarPanel = () => {
        if (!grammarPanel || !grammarPanel.classList.contains("is-live") || isMobilePanelFlow()) {
          return;
        }
        stopGrammarAudio();
        setGrammarOptionsLocked(true);
        grammarState = {
          ...grammarState,
          active: false,
          lock: true,
          awaitingCorrectAdvance: false,
          awaitingIndex: -1,
          skipFeedback: false,
          awaitingStart: false,
          started: true,
        };
        setGrammarStartVisible(false);
        updateGrammarSkipButton();
        grammarFocusRange = null;
        grammarPanel.classList.remove("is-correct", "is-wrong");
        grammarPanel.classList.add("is-locked");
        if (grammarFeedback && !clean(grammarFeedback.textContent)) {
          grammarFeedback.textContent = "Checkpoint đã hoàn tất.";
          grammarFeedback.classList.add("is-ok");
          grammarFeedback.classList.remove("is-error");
        }
        renderAnswerHighlight(scoreInputWords(answerInput.value));
        const node = connectorForPanel(grammarPanel);
        if (node.classList.contains("is-live")) {
          node.classList.remove("is-active");
          node.classList.add("is-dim");
        }
      };

      const hideGrammarQuiz = (resetHighlight = true, force = false) => {
        stopGrammarAudio();
        grammarState = {
          active: false,
          items: [],
          index: 0,
          lock: false,
          pendingMessage: "Chính xác.",
          revision: 0,
          shuffleSeed: "",
          awaitingStart: false,
          started: false,
        };
        setGrammarStartVisible(false);
        updateGrammarSkipButton();
        grammarFocusRange = null;
        if (grammarEffectTimer) {
          window.clearTimeout(grammarEffectTimer);
          grammarEffectTimer = 0;
        }
        if (grammarPanel) {
          if (!force && !isMobilePanelFlow() && grammarPanel.classList.contains("is-locked")) {
            if (resetHighlight) {
              renderAnswerHighlight(scoreInputWords(answerInput.value));
            }
            return;
          }
          grammarPanel.classList.remove("is-live", "is-correct", "is-wrong", "is-locked", "is-mobile-hidden");
        }
        setMobilePanelUnlocked("grammar", false);
        syncMobilePanelTabs();
        if (connectorTargetPanel === grammarPanel) {
          connectorTargetPanel = null;
        }
        hidePanelConnector(grammarPanel);
        setActivePanel(connectorTargetPanel);
        if (grammarOptionsNode) {
          grammarOptionsNode.textContent = "";
        }
        if (grammarFeedback) {
          grammarFeedback.textContent = "";
          grammarFeedback.classList.remove("is-ok", "is-error");
        }
        if (resetHighlight) {
          renderAnswerHighlight(scoreInputWords(answerInput.value));
        }
      };

      const completeGrammarQuiz = () => {
        const message = grammarState.pendingMessage || "Đúng câu và hoàn tất phần phân tích ngữ pháp.";
        if (isMobilePanelFlow()) {
          stopGrammarAudio();
          grammarState = { ...grammarState, active: false, lock: true, awaitingStart: false, started: true };
          setGrammarStartVisible(false);
          updateGrammarSkipButton();
          if (grammarPanel) {
            grammarPanel.classList.add("is-live", "is-locked");
          }
          revealMobilePanel("grammar");
        } else {
          lockGrammarPanel();
        }
        grammarStepCompleted = true;
        renderGrammarStars();
        feedbackNode.textContent = message;
        feedbackNode.classList.remove("is-error");
        feedbackNode.classList.add("is-ok");
        updateNextButton(true);
        setTtsStatus(listenStatusText() || "Grammar checkpoint da xong. Next van san sang.");
        queueSpaceWProgressSave(100);
      };

      const renderGrammarQuestion = (optionsForRender = {}) => {
        if (!grammarState.active || !grammarPanel || !grammarOptionsNode) {
          return;
        }
        if (grammarState.awaitingStart) {
          showGrammarStartPanel(grammarState.startMessage || "");
          return;
        }
        grammarState.started = true;
        setGrammarStartVisible(false);
        if (grammarState.index >= grammarState.items.length) {
          completeGrammarQuiz();
          return;
        }
        const renderSilent = Boolean(optionsForRender && optionsForRender.silent);
        const item = grammarState.items[grammarState.index];
        const options = buildGrammarOptions(item);
        grammarState.lock = false;
        grammarState.awaitingCorrectAdvance = false;
        grammarState.awaitingIndex = -1;
        grammarState.skipFeedback = false;
        updateGrammarSkipButton();
        grammarPanel.classList.remove("is-correct", "is-wrong", "is-locked");
        grammarPanel.classList.add("is-live");
        revealMobilePanel("grammar");
        let shouldPlayOpenSound = false;
        if (!grammarState.openSoundPlayed) {
          grammarState.openSoundPlayed = true;
          shouldPlayOpenSound = true;
        }
        grammarProgress.textContent = `${grammarState.index + 1}/${grammarState.items.length}`;
        renderGrammarPromptText(item);
        renderGrammarTargetText(item);
        grammarFeedback.textContent = "";
        grammarFeedback.classList.remove("is-ok", "is-error");
        grammarOptionsNode.textContent = "";
        options.forEach((option) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "ft-grammar-option";
          button.dataset.value = option;
          button.textContent = grammarDisplayValue(item.type, option, item);
          button.disabled = false;
          grammarOptionsNode.appendChild(button);
        });
        setGrammarFocus(item);
        updateGrammarConnector(true);
        const expectedIndex = grammarState.index;
        const questionSequence = renderSilent ? [] : grammarQuestionAudioSequence(item, options, !grammarKeepSilent);
        if (!questionSequence.length) {
          if (shouldPlayOpenSound) {
            playEffectSound("open");
          }
          return;
        }
        void (async () => {
          if (shouldPlayOpenSound) {
            await playEffectSoundAsync("open");
          }
          await playGrammarAudioSequence(questionSequence);
          if (grammarState.active && grammarState.index === expectedIndex) {
            updateGrammarSkipButton();
          }
        })();
      };

      const handleGrammarOption = async (value, button) => {
        if (!grammarState.active || grammarState.lock) {
          return;
        }
        stopGrammarAudio();
        const item = grammarState.items[grammarState.index];
        const expectedIndex = grammarState.index;
        const ok = grammarAnswerKey(value) === grammarAnswerKey(item.answer);
        const firstAttempt = !grammarFirstAttempted.has(expectedIndex);
        if (firstAttempt) {
          grammarFirstAttempted.add(expectedIndex);
          if (ok) {
            grammarFirstTryCorrect.add(expectedIndex);
          }
          renderGrammarStars();
        }
        setGrammarOptionsLocked(true);
        Array.from(grammarOptionsNode.querySelectorAll(".ft-grammar-option")).forEach((node) => {
          node.classList.remove("is-wrong");
          if (ok && grammarAnswerKey(node.dataset.value) === grammarAnswerKey(item.answer)) {
            node.classList.add("is-correct");
          }
        });
        if (button) {
          button.classList.add(ok ? "is-correct" : "is-wrong");
        }
        grammarState.awaitingCorrectAdvance = Boolean(ok);
        grammarState.awaitingIndex = expectedIndex;
        grammarState.skipFeedback = false;
        updateGrammarSkipButton();
        markGrammarEffect(ok ? "is-correct" : "is-wrong");
        await playEffectSoundAsync(ok ? "true" : "false");
        if (!grammarState.active || grammarState.index !== expectedIndex) {
          return;
        }
        if (!ok) {
          grammarState.awaitingCorrectAdvance = false;
          grammarState.skipFeedback = false;
          updateGrammarSkipButton();
          grammarFeedback.textContent = "Chưa đúng. Chọn lại nhé.";
          grammarFeedback.classList.remove("is-ok");
          grammarFeedback.classList.add("is-error");
          setGrammarOptionsLocked(false);
          return;
        }
        if (!grammarKeepSilent && !grammarState.skipFeedback) {
          await playGrammarAudioSequence(grammarFeedbackAudioSequence(item, ok));
        }
        if (!grammarState.active || grammarState.index !== expectedIndex) {
          return;
        }
        grammarState.awaitingCorrectAdvance = false;
        grammarState.skipFeedback = false;
        updateGrammarSkipButton();
        grammarFeedback.textContent = ok
          ? "Đúng rồi. Chuyển sang câu phân tích tiếp theo."
          : `Chưa đúng. Đáp án đúng: ${grammarDisplayValue(item.type, item.answer, item)}.`;
        grammarFeedback.classList.toggle("is-ok", ok);
        grammarFeedback.classList.toggle("is-error", !ok);
        grammarState.index += 1;
        renderGrammarQuestion();
      };

      const beginGrammarQuiz = (message = "Chinh xac.", options = {}) => {
        const items = buildGrammarQuizItems();
        if (!items.length) {
          grammarState = { ...grammarState, pendingMessage: message || "Grammar checkpoint da xong." };
          grammarFirstAttempted = new Set();
          grammarFirstTryCorrect = new Set();
          if (options && options.activate === false) {
            grammarStepCompleted = true;
            renderGrammarStars();
            updateNextButton(true);
            queueSpaceWProgressSave(100);
            return false;
          }
          renderGrammarStars();
          completeGrammarQuiz();
          return false;
        }
        grammarStepCompleted = false;
        grammarFirstAttempted = new Set();
        grammarFirstTryCorrect = new Set();
        grammarState = {
          active: true,
          items,
          index: 0,
          lock: false,
          pendingMessage: "Đúng câu và hoàn tất phần phân tích ngữ pháp.",
          revision: 0,
          shuffleSeed: `${Date.now()}:${Math.random()}:${currentNodeIndex}`,
          openSoundPlayed: false,
          awaitingCorrectAdvance: false,
          awaitingIndex: -1,
          skipFeedback: false,
          awaitingStart: true,
          started: false,
          startMessage: message || "Ready when you are.",
        };
        if (!isMobilePanelFlow()) {
          lockScorePanel();
          setAnswerEntryLocked(true);
        }
        updateNextButton(true);
        feedbackNode.textContent = "Speak da xong. Next da san sang. Grammar checkpoint la phan on them.";
        feedbackNode.classList.remove("is-error");
        feedbackNode.classList.add("is-ok");
        updateGrammarSilentButton();
        renderGrammarStars();
        showGrammarStartPanel(message, { activate: options.activate !== false });
        queueSpaceWProgressSave(100);
        return true;
      };

      const setNode = (node, index = 0) => {
        const nextNode = node || {};
        resetQuestionMode();
        resetParagraphMode();
        vocabModeActive = false;
        setVocabModeClass(false);
        setSpaceWModeClass(true);
        setVocabKeyboardLock(false);
        vocabModeTransitioning = false;
        hideVocabModePopup();
        clearVocabHintTimers();
        if (vocabCard) {
          vocabCard.classList.add("is-hidden");
        }
        renderVocabUnlearnedList();
        hideVocabSideCards();
        renderVocabLearnedPanel();
        if (vocabLearnedPanel) {
          vocabLearnedPanel.classList.add("is-hidden");
        }
        if (vocabLearnedConnector) {
          vocabLearnedConnector.classList.add("is-hidden");
        }
        resetVocabLearnedPanelPosition();
        if (cardNode) {
          cardNode.classList.remove("is-hidden");
        }
        currentNode = nextNode;
        currentNodeIndex = Math.max(0, Number(index) || 0);
        const vi = clean(nextNode.vi ?? nextNode.q ?? question) || defaults.vi;
        const en = clean(nextNode.en ?? nextNode.e ?? answer) || defaults.en;
        const nextIpa = clean(nextNode.ipa ?? nextNode.i ?? ipa) || defaults.ipa;
        const tokens = nextNode.tokens ?? nextNode.tk ?? [];
        voiceHint = clean(nextNode.voice ?? nextNode.vc ?? voiceHint);
        currentAccent = voiceAccentFromText(voiceHint);
        completedListenCount = 0;
        nextPanelCanShow = false;
        speakStepCompleted = Boolean(spaceWSpeakSkipSessionApproved);
        clearSpeakSkipPolling();
        setSpeakReportButtonState(spaceWSpeakSkipSessionApproved ? "accepted" : "idle");
        speakStarCount = 0;
        grammarStepCompleted = false;
        grammarFirstAttempted = new Set();
        grammarFirstTryCorrect = new Set();
        reviewCurrentHadError = false;
        reviewSpeakCompleted = Boolean(spaceWSpeakSkipSessionApproved);
        previousWordOk = [];
        pendingSpaceWordCheck = false;
        lastFalseWordKey = "";
        wordHintedKeys = new Set();
        renderScoreStars(null);
        renderSpeakStars();
        renderGrammarStars();
        stopWordHintWatch();
        renderIpaStars();
        setAnswerEntryLocked(false);
        questionNode.textContent = vi;
        renderEnglish(en, tokens, currentAccent);
        renderIpa(nodeIpaForAccent(nextNode, nextIpa, currentAccent), tokens, currentAccent);
        updateDesktopPanelLayout();
        updateSpaceWProgressLabel();
        accepted.length = 0;
        accepted.push(normalize(en));
        const extraAccept = nextNode.accept ?? nextNode.a ?? "";
        if (Array.isArray(extraAccept)) {
          extraAccept.map(normalize).filter(Boolean).forEach((item) => accepted.push(item));
        } else if (extraAccept) {
          String(extraAccept).split("|").map(normalize).filter(Boolean).forEach((item) => accepted.push(item));
        }
        wrongAttempts = 0;
        answerInput.value = "";
        renderAnswerHighlight();
        stopActiveAudio();
        hideSpeakPanel();
        hideHintPanel();
        hideAboutPanel({ resetUnlock: true });
        updateAboutTrainButton();
        syncHintAboutSwitchButtons();
        clearAllConnectors();
        ipaPanel.classList.remove("is-live", "is-speaking", "is-locked", "is-mobile-hidden");
        mobileUnlockedPanels.clear();
        mobileActivePanelKey = "";
        syncMobilePanelTabs();
        hideScorePanel(true);
        hideGrammarQuiz(false, true);
        updateNextButton(false);
        setPlaybackState(false);
        showHintPanel(nodeHintText(nextNode), true);
        scheduleWordHintWatch(scoreInputWords(answerInput.value));
        scheduleSpaceWTokenSupportForNode();
        feedbackNode.textContent = "Type the English answer. IPA opens automatically when it is correct.";
        feedbackNode.classList.remove("is-error", "is-ok");
        loadVoices();
        // Added 2026-07-09: returns the caret to the main translation input whenever Space_W advances to a new node.
        const focusSpaceWAnswerInputForNode = () => {
          if (
            currentNode !== nextNode ||
            !answerInput ||
            answerInput.disabled ||
            !cardNode ||
            cardNode.classList.contains("is-hidden") ||
            (authGate && !authGate.classList.contains("is-hidden")) ||
            (loadGate && !loadGate.classList.contains("is-hidden"))
          ) {
            return;
          }
          try {
            answerInput.focus({ preventScroll: true });
          } catch (error) {
            try { answerInput.focus(); } catch (_error) {}
          }
          try {
            const end = String(answerInput.value || "").length;
            answerInput.setSelectionRange(end, end);
          } catch (error) {
          }
        };
        window.requestAnimationFrame(focusSpaceWAnswerInputForNode);
        window.setTimeout(focusSpaceWAnswerInputForNode, 80);
        window.setTimeout(focusSpaceWAnswerInputForNode, 260);
        warmSpaceWAudioCacheForActiveLesson(lessonNodes, voiceSelect.value, lessonEffects, {
          startIndex: currentNodeIndex,
          startDelayMs: 500,
        });
        refreshIpaForAccent(selectedVoiceAccent());
          window.setTimeout(() => {
            if (currentNode === nextNode) {
              const play = () => {
                if (currentNode === nextNode) playNodeQuestionAudio(nextNode);
              };
              if (typeof window.__ftRunAfterLessonEntryGateOpen === "function") window.__ftRunAfterLessonEntryGateOpen(play);
              else play();
            }
          }, 180);
        queueSpaceWProgressSave(120);
        window.setTimeout(() => {
          if (currentNode === nextNode && !speakStepCompleted) {
            void pollSpeakSkipState().catch(() => {});
          }
          scheduleTranslateCardPin(1400, { force: true });
        }, 700);
        scheduleMobileInfiniteMotionSync(80);
        scheduleMobileInfiniteMotionSync(900);
      };

      const isVocabularyPayload = (payload) => Boolean(payload && payload.kind === "future_vocabulary_payload");
      const isQuestionPayload = (payload) => Boolean(payload && payload.kind === "future_question_payload");
      const isParagraphPayload = (payload) => Boolean(payload && payload.kind === "future_paragraph_payload");

      let paragraphPayload = null;
      let paragraphNodes = [];
      let paragraphNodeIndex = 0;
      let paragraphChildIndex = 0;
      let paragraphRevealed = [];
      let paragraphHints = new Set();
      let paragraphHintTimer = 0;
      let paragraphPosHintTimer = 0;
      let paragraphHintTicker = 0;
      let paragraphHintDeadline = 0;
      let paragraphHintPausedAfterAutoUnlock = false;
      let paragraphPosHintKey = "";
      let paragraphAdvanceTimer = 0;
      let paragraphAudioToken = 0;
      let paragraphPendingAudioRetry = null;
      let paragraphWordAudioTimers = [];
      let paragraphActiveAudios = new Set();
      let paragraphAudioHighlightFrame = 0;
      let paragraphAudioHighlightAudio = null;
      let paragraphAudioHighlightIndex = -1;
      let paragraphCurrentPlaybackKind = "";
      let paragraphCurrentPlaybackSignature = "";
      let paragraphCompleting = false;
      let paragraphExplanationIndex = 0;
      let paragraphWrongTokenCount = 0;
      let paragraphWrongSoundKey = "";
      let paragraphInputPulseTimer = 0;
      let paragraphWordNoteTimers = [];
      let paragraphAiFollowupKeys = new Set();
      let paragraphTokenHelperUsedKeys = new Set();
      let paragraphEls = null;
      let spaceSMatchedTokenKeys = new Set();
      let spaceLUnlockedTokenKeys = new Set();
      let spaceLUnlockChoiceAvailable = false;
      let spaceSUserRecorder = null;
      let spaceSUserAudioChunks = [];
      let spaceSUserAudioUrl = "";
      let spaceSReplayAudio = null;
      let spaceSPreferredVoiceMode = "main";
      let spaceSFailedReadSessions = 0;
      let spaceSManualInputUnlocked = false;
      let spaceSReadSessionHasInput = false;
      let spaceSReadSessionFinalized = false;
      let spaceSLastReadScore = 0;
      let spaceSAutoReplayAfterRecordingStop = false;
      let spaceSListeningIdleTimer = 0;
      let spaceSListeningLastTokenAt = 0;
      let spaceSListeningTokenCount = 0;
      const SPACE_S_REWARD_PLAYBACK_RATES = [0.5, 0.6, 0.7, 0.8, 0.9, 1];
      let spaceSRewardPlaybackRate = 0.7;
      let spaceSRewardSpeedDrag = null;
      const SPACE_S_PASS_SCORE = 80;
      const SPACE_S_IDLE_STOP_MS = 20000;

      function paragraphSpaceMode(payload = paragraphPayload) {
        const mode = clean(payload && (payload.space_mode || payload.spaceMode || payload.mode || payload.sm || "")).toLowerCase();
        const format = clean(payload && (payload.format || payload.fmt || "")).toLowerCase();
        const pathValue = clean(currentLessonSource && currentLessonSource.path).toLowerCase();
        if (mode === "space_l" || format === "space_l" || format === "space_l hidden listening" || pathValue.endsWith(".space_l")) {
          return "space_l";
        }
        if (mode === "space_s" || format === "space_s" || format === "space_s speaking unlock" || pathValue.endsWith(".space_s")) {
          return "space_s";
        }
        return "space_p";
      }

      function isSpaceSPayload(payload = paragraphPayload) {
        return paragraphSpaceMode(payload) === "space_s";
      }

      function isSpaceLPayload(payload = paragraphPayload) {
        return paragraphSpaceMode(payload) === "space_l";
      }

      function isSpaceSpeechPayload(payload = paragraphPayload) {
        const mode = paragraphSpaceMode(payload);
        return mode === "space_s" || mode === "space_l";
      }

      function isSpaceRewardPlaybackPayload(payload = paragraphPayload) {
        return isSpaceSPayload(payload) || isSpaceLPayload(payload);
      }

      function paragraphModeLabel() {
        const mode = paragraphSpaceMode();
        return mode === "space_l" ? "Space_L" : (mode === "space_s" ? "Space_S" : "Space_P");
      }

      function captureParagraphInputSelection(input) {
        if (!input || document.activeElement !== input || typeof input.selectionStart !== "number") {
          return null;
        }
        return {
          input,
          start: Math.max(0, Number(input.selectionStart) || 0),
          end: Math.max(0, Number(input.selectionEnd) || 0),
          direction: input.selectionDirection || "none",
        };
      }

      function restoreParagraphInputSelection(snapshot) {
        if (!snapshot || !snapshot.input || document.activeElement !== snapshot.input || typeof snapshot.input.setSelectionRange !== "function") {
          return;
        }
        const applySelection = () => {
          if (document.activeElement !== snapshot.input) {
            return;
          }
          const length = String(snapshot.input.value || "").length;
          const start = Math.max(0, Math.min(length, snapshot.start));
          const end = Math.max(start, Math.min(length, snapshot.end));
          try {
            snapshot.input.setSelectionRange(start, end, snapshot.direction);
          } catch (error) {
          }
        };
        applySelection();
        window.requestAnimationFrame(applySelection);
      }

      function spaceSTokenKey(childIndex = paragraphChildIndex, wordIndex = 0) {
        return `${Number(childIndex) || 0}:${Number(wordIndex) || 0}`;
      }

      function clearParagraphPlaybackMeta() {
        paragraphCurrentPlaybackKind = "";
        paragraphCurrentPlaybackSignature = "";
      }

      function isSpaceSListeningActive(els = paragraphEls) {
        return Boolean(
          spaceSUserRecorder
          || (typeof browserSpeechInputRecognition !== "undefined"
            && browserSpeechInputRecognition
            && els
            && browserSpeechInputButton === els.speech)
        );
      }

      function queueParagraphInputTailFollow(options = {}) {
        if (!isSpaceSpeechPayload()) {
          return;
        }
        const els = paragraphEls;
        const input = els && els.input;
        if (!input) {
          return;
        }
        const forceSelectionEnd = options && options.forceSelectionEnd !== false;
        const focusInput = Boolean(options && options.focusInput);
        const syncTail = () => {
          const liveEls = paragraphEls;
          const liveInput = liveEls && liveEls.input;
          if (!liveInput || liveInput !== input) {
            return;
          }
          const raw = String(liveInput.value || "");
          if (focusInput && typeof liveInput.focus === "function") {
            try {
              liveInput.focus({ preventScroll: true });
            } catch (error) {
              try {
                liveInput.focus();
              } catch (focusError) {
              }
            }
          }
          if (forceSelectionEnd && typeof liveInput.setSelectionRange === "function") {
            try {
              liveInput.setSelectionRange(raw.length, raw.length);
            } catch (error) {
            }
          }
          try {
            liveInput.scrollLeft = raw ? liveInput.scrollWidth : 0;
          } catch (error) {
          }
          if (liveEls && liveEls.inputGhost) {
            liveEls.inputGhost.style.setProperty("--paragraph-input-scroll", `${-(Number(liveInput.scrollLeft || 0) || 0)}px`);
          }
        };
        syncTail();
        window.requestAnimationFrame(() => {
          syncTail();
          window.requestAnimationFrame(syncTail);
        });
      }

      function setSpaceSMicLiveState(active = false) {
        const live = Boolean(active);
        const els = paragraphEls;
        if (els && els.micLive) {
          els.micLive.hidden = !live;
          els.micLive.classList.toggle("is-live", live);
          els.micLive.setAttribute("aria-hidden", live ? "false" : "true");
        }
        if (els && els.root) {
          els.root.classList.toggle("is-space-s-mic-live", live);
        }
      }

      function clearSpaceSListeningIdleWatch() {
        if (spaceSListeningIdleTimer) {
          window.clearInterval(spaceSListeningIdleTimer);
          spaceSListeningIdleTimer = 0;
        }
        spaceSListeningLastTokenAt = 0;
        spaceSListeningTokenCount = 0;
      }

      function noteSpaceSListeningTokenProgress(value = "") {
        if (!isSpaceSListeningActive()) {
          return;
        }
        const tokenCount = paragraphTypedWords(value).length;
        if (tokenCount > spaceSListeningTokenCount) {
          spaceSListeningTokenCount = tokenCount;
          spaceSListeningLastTokenAt = Date.now();
        }
      }

      function startSpaceSListeningIdleWatch() {
        clearSpaceSListeningIdleWatch();
        const els = paragraphEls;
        const input = els && els.input;
        spaceSListeningTokenCount = paragraphTypedWords(input ? input.value : "").length;
        spaceSListeningLastTokenAt = Date.now();
        spaceSListeningIdleTimer = window.setInterval(() => {
          if (!paragraphModeActive || !isSpaceSpeechPayload() || !isSpaceSListeningActive()) {
            clearSpaceSListeningIdleWatch();
            return;
          }
          const liveEls = paragraphEls;
          const liveInput = liveEls && liveEls.input;
          if (liveInput) {
            noteSpaceSListeningTokenProgress(liveInput.value);
          }
          if (!spaceSListeningLastTokenAt || Date.now() - spaceSListeningLastTokenAt < SPACE_S_IDLE_STOP_MS) {
            return;
          }
          clearSpaceSListeningIdleWatch();
          stopSpaceSListeningSession({ finalizeAttempt: true, autoReplayRecordedVoice: true });
          syncParagraphInput();
          if (liveEls && liveEls.status) {
            const raw = liveInput ? String(liveInput.value || "") : "";
            liveEls.status.textContent = raw.trim()
              ? "Stopped after 20s without a new token. Preparing replay."
              : "Mic stopped after 20s without a new token.";
          }
        }, 500);
      }

      function currentSpaceSReadScore(value = null) {
        const child = currentParagraphChild();
        return paragraphSpeechAnalysis(
          value == null ? (paragraphEls && paragraphEls.input ? paragraphEls.input.value : "") : value,
          child ? child.text : "",
        ).score;
      }

      function spaceSHasAltVoice(child = currentParagraphChild()) {
        if (!child || typeof child !== "object") {
          return false;
        }
        const alt = child.alt_audio || child.altAudio || child.audio_alt || child.audioAlt || null;
        return Boolean(alt && typeof alt === "object");
      }

      function spaceSVoiceClipForMode(mode = "main", child = currentParagraphChild()) {
        if (!child || typeof child !== "object") {
          return null;
        }
        return mode === "alt"
          ? (child.alt_audio || child.altAudio || child.audio_alt || child.audioAlt || child.audio || null)
          : (child.audio || null);
      }

      function spaceSResolvedVoiceMode(mode = "main", child = currentParagraphChild()) {
        return mode === "alt" && spaceSHasAltVoice(child) ? "alt" : "main";
      }

      function spaceSPreferredVoiceModeForChild(child = currentParagraphChild()) {
        return spaceSResolvedVoiceMode(spaceSPreferredVoiceMode, child);
      }

      function spaceSVoiceModeLabel(mode = "main", child = currentParagraphChild()) {
        const clip = spaceSVoiceClipForMode(mode, child);
        const clipLabel = clean(clip && (clip.voice_label || clip.voiceLabel || clip.label || clip.voice || clip.vc));
        if (clipLabel) {
          return clipLabel;
        }
        const fallback = mode === "alt"
          ? clean(child && (child.alt_voice || child.altVoice || child.av || ""))
          : clean(child && (child.voice || child.vc || ""));
        return fallback || (mode === "alt" ? "Second voice" : "Primary voice");
      }

      function spaceSVoiceMenuOptions(child = currentParagraphChild()) {
        const rows = [];
        const seen = new Set();
        [
          { mode: "main", clip: spaceSVoiceClipForMode("main", child) },
          { mode: "alt", clip: spaceSHasAltVoice(child) ? spaceSVoiceClipForMode("alt", child) : null },
        ].forEach((item) => {
          if (!item.clip) {
            return;
          }
          const label = spaceSVoiceModeLabel(item.mode, child);
          const dedupeKey = clean(
            item.clip.voice_key
            || item.clip.voiceKey
            || item.clip.voice
            || item.clip.url
            || item.clip.u
            || `${item.mode}:${label}`
          ).toLowerCase();
          if (dedupeKey && seen.has(dedupeKey)) {
            return;
          }
          if (dedupeKey) {
            seen.add(dedupeKey);
          }
          rows.push({ mode: item.mode, label, enabled: true });
        });
        return rows;
      }

      function setSpaceSPreferredVoiceMode(mode = "main", options = {}) {
        const child = options && options.child ? options.child : currentParagraphChild();
        spaceSPreferredVoiceMode = spaceSResolvedVoiceMode(mode, child);
        if (paragraphModeActive && isSpaceSpeechPayload()) {
          renderSpaceSSideCards();
        }
        return spaceSPreferredVoiceMode;
      }

      function ensureSpaceSVoiceMenu() {
        const existing = paragraphEls && paragraphEls.voiceMenu;
        if (existing && document.body.contains(existing)) {
          return existing;
        }
        const menu = document.createElement("div");
        menu.className = "ft-space-s-voice-menu";
        menu.hidden = true;
        menu.setAttribute("role", "menu");
        document.body.appendChild(menu);
        if (paragraphEls) {
          paragraphEls.voiceMenu = menu;
        }
        return menu;
      }

      function hideSpaceSVoiceMenu() {
        const menu = paragraphEls && paragraphEls.voiceMenu;
        if (menu) {
          menu.hidden = true;
          menu.textContent = "";
        }
      }

      function renderSpaceSVoiceMenu(child = currentParagraphChild()) {
        const menu = ensureSpaceSVoiceMenu();
        const activeMode = spaceSPreferredVoiceModeForChild(child);
        menu.textContent = "";
        spaceSVoiceMenuOptions(child).forEach((item) => {
          const button = document.createElement("button");
          button.type = "button";
          button.dataset.voiceMode = item.mode;
          button.className = "ft-space-s-voice-menu-action";
          button.disabled = !item.enabled;
          button.classList.toggle("is-selected", activeMode === item.mode);
          const label = document.createElement("span");
          label.textContent = item.label;
          const meta = document.createElement("span");
          meta.textContent = activeMode === item.mode ? "Active" : (item.enabled ? "Ready" : "Unavailable");
          button.appendChild(label);
          button.appendChild(meta);
          button.addEventListener("click", () => {
            const nextMode = setSpaceSPreferredVoiceMode(item.mode, { child });
            const els = paragraphEls;
            if (els && els.status) {
              els.status.textContent = `${spaceSVoiceModeLabel(nextMode, child)} is armed. Click the model voice card or press Alt to play.`;
            }
            hideSpaceSVoiceMenu();
          });
          menu.appendChild(button);
        });
        return menu;
      }

      function showSpaceSVoiceMenu(x = 0, y = 0, child = currentParagraphChild()) {
        if (!isSpaceSpeechPayload()) {
          return;
        }
        const menu = renderSpaceSVoiceMenu(child);
        menu.hidden = false;
        menu.style.left = "0px";
        menu.style.top = "0px";
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1280;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;
        const maxLeft = Math.max(8, viewportWidth - menu.offsetWidth - 12);
        const maxTop = Math.max(8, viewportHeight - menu.offsetHeight - 12);
        menu.style.left = `${Math.max(8, Math.min(maxLeft, Math.round(Number(x) || 0)))}px`;
        menu.style.top = `${Math.max(8, Math.min(maxTop, Math.round(Number(y) || 0)))}px`;
      }

      function syncSpaceSManualInputGate(score = spaceSLastReadScore) {
        const els = paragraphEls;
        if (!els || !els.input || !els.inputWrap || !els.inputRow) {
          return;
        }
        const speakingMode = isSpaceSpeechPayload();
        if (isSpaceLPayload()) {
          els.input.readOnly = false;
          els.inputWrap.classList.remove("is-manual-locked");
          els.inputRow.classList.remove("is-manual-locked");
          els.input.placeholder = Number(score || 0) >= SPACE_S_PASS_SCORE
            ? "Passed. Press Next when you are ready"
            : "Type freely, or press Ctrl to speak with Browser EN";
          return;
        }
        const locked = speakingMode && !spaceSManualInputUnlocked;
        els.input.readOnly = locked;
        els.inputWrap.classList.toggle("is-manual-locked", locked);
        els.inputRow.classList.toggle("is-manual-locked", locked);
        if (!speakingMode) {
          els.input.placeholder = "Type the English segment here";
          return;
        }
        if (locked) {
          els.input.placeholder = spaceSFailedReadSessions >= 1
            ? "One more read below 80% unlocks typing fallback"
            : "Read aloud first. Typing unlocks after 2 reads below 80%";
        } else if (Number(score || 0) >= SPACE_S_PASS_SCORE) {
          els.input.placeholder = "Passed. Press Next when you are ready";
        } else {
          els.input.placeholder = "Typing fallback unlocked. Fix the transcript or press Ctrl again";
        }
      }

      function stopSpaceSReplayAudio() {
        const audio = spaceSReplayAudio;
        if (!audio) {
          return false;
        }
        spaceSReplayAudio = null;
        try {
          audio.pause();
          audio.currentTime = 0;
        } catch (error) {
        }
        updateSpaceSReplayButton();
        return true;
      }

      function handleSpaceSReplayStopShortcut() {
        const els = ensureParagraphRuntime();
        if (spaceSReplayAudio && !spaceSReplayAudio.paused && !spaceSReplayAudio.ended) {
          stopSpaceSReplayAudio();
          if (els && els.status) {
            els.status.textContent = "Replay stopped.";
          }
          return true;
        }
        return false;
      }

      function updateSpaceSReplayButton() {
        const els = paragraphEls;
        if (!els || !els.replay) {
          return;
        }
        const speakingMode = isSpaceSpeechPayload();
        const isPlaying = Boolean(spaceSReplayAudio && !spaceSReplayAudio.paused && !spaceSReplayAudio.ended);
        els.replay.hidden = !speakingMode;
        els.replay.disabled = !speakingMode || (!spaceSUserAudioUrl && !isPlaying);
        els.replay.textContent = isPlaying ? "Stop" : "Replay";
        els.replay.title = isPlaying ? "Stop your recorded voice" : "Replay your recorded voice";
        els.replay.setAttribute("aria-label", isPlaying ? "Stop your recorded voice" : "Replay your recorded voice");
        els.replay.classList.toggle("is-ready", Boolean(spaceSUserAudioUrl || isPlaying));
        els.replay.classList.toggle("is-playing", isPlaying);
      }

      function stopSpaceSListeningSession(options = {}) {
        const els = paragraphEls;
        const finalizeAttempt = Boolean(options && options.finalizeAttempt);
        const autoReplayRecordedVoice = Boolean(options && options.autoReplayRecordedVoice);
        spaceSAutoReplayAfterRecordingStop = finalizeAttempt && autoReplayRecordedVoice;
        clearSpaceSListeningIdleWatch();
        if (
          els
          && typeof browserSpeechInputRecognition !== "undefined"
          && browserSpeechInputRecognition
          && browserSpeechInputButton === els.speech
          && typeof stopBrowserMultilingualInputDictation === "function"
        ) {
          stopBrowserMultilingualInputDictation();
        }
        const hadRecorder = stopSpaceSUserRecording();
        setSpaceSMicLiveState(false);
        if (spaceSAutoReplayAfterRecordingStop && !hadRecorder) {
          spaceSAutoReplayAfterRecordingStop = false;
        }
        if (finalizeAttempt && !spaceSReadSessionFinalized) {
          const raw = els && els.input ? String(els.input.value || "") : "";
          if (raw.trim() || isSpaceLPayload()) {
            const analysis = paragraphSpeechAnalysis(raw, currentParagraphChild() ? currentParagraphChild().text : "");
            const score = analysis.score;
            spaceSLastReadScore = score;
            if (isSpaceLPayload()) {
              unlockSpaceLMatchedTokens(analysis.matchedIndexes);
            }
            if (score >= SPACE_S_PASS_SCORE) {
              spaceSFailedReadSessions = 0;
              spaceLUnlockChoiceAvailable = false;
            } else if (isSpaceLPayload()) {
              spaceSFailedReadSessions = Math.min(2, spaceSFailedReadSessions + 1);
              if (spaceSFailedReadSessions >= 2) {
                spaceLUnlockChoiceAvailable = true;
                spaceSFailedReadSessions = 0;
                if (els && els.status) {
                  els.status.textContent = "Two reads logged. Choose one hidden block to unlock before your next recording.";
                }
              }
            } else if (!spaceSManualInputUnlocked) {
              spaceSFailedReadSessions = Math.min(2, spaceSFailedReadSessions + 1);
              if (spaceSFailedReadSessions >= 2) {
                spaceSManualInputUnlocked = true;
              }
            }
          }
          spaceSReadSessionHasInput = false;
          spaceSReadSessionFinalized = true;
          if (isSpaceLPayload()) {
            syncParagraphTokenClasses();
            renderSpaceSSideCards(spaceSLastReadScore);
            queueParagraphProgressSave(120);
          }
          syncSpaceSManualInputGate(spaceSLastReadScore);
        }
        if (!finalizeAttempt || !autoReplayRecordedVoice) {
          spaceSAutoReplayAfterRecordingStop = false;
        }
      }

      function setSpaceSRevealedForCurrentChild() {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        paragraphRevealed = children.map((child, index) => (
          index <= paragraphChildIndex ? paragraphTokenCountForChild(child) : 0
        ));
      }

      function spaceLUnlockedIndexesForChild(childIndex = paragraphChildIndex) {
        const unlocked = new Set();
        if (!(spaceLUnlockedTokenKeys instanceof Set)) {
          return unlocked;
        }
        spaceLUnlockedTokenKeys.forEach((key) => {
          const parts = String(key || "").split(":");
          if (parts.length >= 3) {
            if ((Number(parts[0] || 0) || 0) === paragraphNodeIndex && (Number(parts[1] || 0) || 0) === childIndex) {
              unlocked.add(Number(parts[2] || 0) || 0);
            }
          } else if ((Number(parts[0] || 0) || 0) === childIndex) {
            unlocked.add(Number(parts[1] || 0) || 0);
          }
        });
        return unlocked;
      }

      function spaceLTokenKey(childIndex = paragraphChildIndex, wordIndex = 0, nodeIndex = paragraphNodeIndex) {
        return `${Math.max(0, Number(nodeIndex) || 0)}:${Math.max(0, Number(childIndex) || 0)}:${Math.max(0, Number(wordIndex) || 0)}`;
      }

      function isSpaceLTokenUnlocked(childIndex = paragraphChildIndex, wordIndex = 0, nodeIndex = paragraphNodeIndex) {
        if (!(spaceLUnlockedTokenKeys instanceof Set)) {
          return false;
        }
        return spaceLUnlockedTokenKeys.has(spaceLTokenKey(childIndex, wordIndex, nodeIndex))
          || spaceLUnlockedTokenKeys.has(spaceSTokenKey(childIndex, wordIndex));
      }

      function unlockSpaceLMatchedTokens(matchedIndexes) {
        if (!isSpaceLPayload() || !(matchedIndexes instanceof Set)) {
          return 0;
        }
        let added = 0;
        matchedIndexes.forEach((wordIndex) => {
          const key = spaceLTokenKey(paragraphChildIndex, wordIndex);
          if (!spaceLUnlockedTokenKeys.has(key)) {
            spaceLUnlockedTokenKeys.add(key);
            added += 1;
          }
        });
        if (added > 0) {
          queueParagraphProgressSave(120);
        }
        return added;
      }

      function unlockSpaceLChosenToken(childIndex = paragraphChildIndex, wordIndex = -1) {
        if (!isSpaceLPayload() || !spaceLUnlockChoiceAvailable || childIndex !== paragraphChildIndex || wordIndex < 0) {
          return false;
        }
        const key = spaceLTokenKey(childIndex, wordIndex);
        if (isSpaceLTokenUnlocked(childIndex, wordIndex)) {
          return false;
        }
        spaceLUnlockedTokenKeys.add(key);
        spaceLUnlockChoiceAvailable = false;
        const child = currentParagraphChild();
        const parts = child ? paragraphWordParts(child.text) : [];
        const part = parts[wordIndex] || null;
        if (part) {
          playParagraphWordAudio(childIndex, wordIndex, part.word, 180);
        }
        syncParagraphTokenClasses();
        renderSpaceSSideCards(spaceSLastReadScore);
        updateParagraphProgress();
        queueParagraphProgressSave(120);
        const els = paragraphEls;
        if (els && els.status) {
          els.status.textContent = "Selected block unlocked. Speak again when ready.";
        }
        return true;
      }

      function handleSpaceLUnlockChoiceClick(event) {
        if (!isSpaceLPayload() || !spaceLUnlockChoiceAvailable || !event || !event.target || !event.target.closest) {
          return false;
        }
        const token = event.target.closest(".ft-paragraph-token");
        if (!token) {
          return false;
        }
        const childIndex = Number(token.dataset.child || 0) || 0;
        const wordIndex = Number(token.dataset.word || 0) || 0;
        if (!unlockSpaceLChosenToken(childIndex, wordIndex)) {
          return false;
        }
        event.preventDefault();
        event.stopPropagation();
        return true;
      }

      function setParagraphModeClass(enabled) {
        const active = Boolean(enabled);
        document.documentElement.classList.toggle("ft-space-p-mode", active);
        if (active && typeof setVocabModeClass === "function") {
          setVocabModeClass(false);
        }
      }

      function stopParagraphAudioPlayback() {
        paragraphAudioToken += 1;
        paragraphPendingAudioRetry = null;
        paragraphWordAudioTimers.forEach((timer) => window.clearTimeout(timer));
        paragraphWordAudioTimers = [];
        clearParagraphAudioHighlight();
        paragraphActiveAudios.forEach((entry) => {
          const audio = entry && entry.audio ? entry.audio : entry;
          try {
            audio.pause();
            audio.currentTime = 0;
          } catch (error) {
          }
          if (entry && typeof entry.done === "function") {
            try {
              entry.done(false);
            } catch (error) {
            }
          }
        });
        paragraphActiveAudios.clear();
        clearParagraphPlaybackMeta();
      }

      function clearParagraphTimers() {
        clearSpaceSListeningIdleWatch();
        if (paragraphHintTimer) {
          window.clearTimeout(paragraphHintTimer);
          paragraphHintTimer = 0;
        }
        if (paragraphPosHintTimer) {
          window.clearTimeout(paragraphPosHintTimer);
          paragraphPosHintTimer = 0;
        }
        if (paragraphHintTicker) {
          window.clearInterval(paragraphHintTicker);
          paragraphHintTicker = 0;
        }
        clearParagraphAudioHighlight();
        paragraphHintDeadline = 0;
        paragraphPosHintKey = "";
        updateParagraphHintCountdown();
        updateParagraphPosHint(false);
        if (paragraphAdvanceTimer) {
          window.clearTimeout(paragraphAdvanceTimer);
          paragraphAdvanceTimer = 0;
        }
        stopParagraphAudioPlayback();
        stopSpaceSReplayAudio();
        paragraphCompleting = false;
        if (paragraphInputPulseTimer) {
          window.clearTimeout(paragraphInputPulseTimer);
          paragraphInputPulseTimer = 0;
        }
        if (paragraphEls && paragraphEls.inputRow) {
          paragraphEls.inputRow.classList.remove("is-paragraph-typing", "is-paragraph-good", "is-paragraph-wrong");
        }
        if (paragraphEls && paragraphEls.inputGhost) {
          paragraphEls.inputGhost.textContent = "";
          paragraphEls.inputGhost.style.setProperty("--paragraph-input-scroll", "0px");
        }
        hideSpaceSVoiceMenu();
        updateSpaceSReplayButton();
        renderSpaceSSideCards();
        clearParagraphWordNoteTimers();
      }

      function ensureParagraphRuntime() {
        if (paragraphEls && paragraphEls.root) {
          return paragraphEls;
        }
        const root = document.createElement("section");
        root.className = "ft-paragraph-mode is-hidden notranslate";
        root.setAttribute("aria-label", "Future paragraph rewrite");
        root.setAttribute("translate", "no");
        root.innerHTML = `
         <div class="ft-paragraph-shell">
            <aside class="ft-space-s-side-card ft-space-s-spoken-card" aria-live="polite">
              <div class="ft-space-s-side-kicker">YOUR VOICE TOKENS</div>
              <div class="ft-space-s-side-title">Standby</div>
              <div class="ft-space-s-spoken-tokens"></div>
            </aside>
            <article class="ft-paragraph-card">
              <div class="ft-paragraph-card-head">
                <span class="ft-paragraph-card-title-group">
                  <span class="ft-paragraph-node-title"></span>
                  <span class="ft-paragraph-mic-live" hidden aria-hidden="true" title="Mic live">
                    <span class="ft-paragraph-mic-icon"><span class="ft-paragraph-mic-core"></span></span>
                    <span class="ft-paragraph-mic-bars" aria-hidden="true"><span></span><span></span><span></span></span>
                  </span>
                </span>
                <span class="ft-paragraph-card-label">PARAGRAPH MEMORY MATRIX</span>
                <span class="ft-paragraph-progress" aria-hidden="true"><span></span></span>
              </div>
              <div class="ft-paragraph-text"></div>
            </article>
            <aside class="ft-space-s-side-card ft-space-s-phonetic-card" aria-live="polite">
              <div class="ft-space-s-side-kicker">CURRENT PRONUNCIATION</div>
              <div class="ft-space-s-side-title">Phonetic guide</div>
              <div class="ft-space-s-phonetic-text"></div>
            </aside>
          </div>
          <article class="ft-paragraph-token-helper is-hidden" aria-hidden="true">
            <div class="ft-paragraph-token-helper-head">
              <span>Token Support</span>
              <button class="ft-paragraph-token-helper-close" type="button" aria-label="Close token support">x</button>
            </div>
            <div class="ft-paragraph-token-helper-note">Shuffled answer tokens. Reward policy follows the current mode.</div>
            <div class="ft-paragraph-token-helper-grid"></div>
          </article>
          <div class="ft-paragraph-word-notes is-hidden" aria-hidden="true">
            <aside class="ft-paragraph-word-note is-left">
              <div class="ft-paragraph-word-note-head">
                <div>
                  <div class="ft-paragraph-word-note-kicker">Meaning guide</div>
                  <div class="ft-paragraph-word-note-title" data-word-note-title-left></div>
                </div>
                <button class="ft-paragraph-word-note-close" type="button" aria-label="Close word guide">x</button>
              </div>
              <div class="ft-paragraph-word-note-body" data-word-note-meaning></div>
            </aside>
            <aside class="ft-paragraph-word-note is-right">
              <div class="ft-paragraph-word-note-head">
                <div>
                  <div class="ft-paragraph-word-note-kicker">Grammar system</div>
                  <div class="ft-paragraph-word-note-title" data-word-note-title-right></div>
                </div>
                <button class="ft-paragraph-word-note-close" type="button" aria-label="Close word guide">x</button>
              </div>
              <div class="ft-paragraph-word-note-body" data-word-note-grammar></div>
            </aside>
          </div>
          <div class="ft-paragraph-bottom-shell">
            <div class="ft-paragraph-guide-stack">
              <div class="ft-paragraph-pos-hint" aria-live="polite">
                <div class="ft-paragraph-pos-kicker">WORD TYPE</div>
                <div class="ft-paragraph-pos-label">STANDBY</div>
                <div class="ft-paragraph-pos-meaning"></div>
                <div class="ft-paragraph-pos-mask" aria-label="Current word character support"></div>
              </div>
            </div>
            <div class="ft-paragraph-dock">
              <div class="ft-paragraph-meaning"></div>
              <div class="ft-paragraph-input-row">
                <span class="ft-paragraph-input-wrap">
                  <span class="ft-paragraph-input-ghost" aria-hidden="true"></span>
                  <input class="ft-paragraph-input" type="text" autocomplete="off" spellcheck="false" placeholder="Type the English segment here">
                </span>
                <button class="ft-paragraph-replay" type="button" title="Replay sentence (Alt)" aria-label="Replay your recorded voice">Replay</button>
                <button class="ft-paragraph-speech" type="button" hidden aria-hidden="true">Speech</button>
                <button class="ft-paragraph-next" type="button" disabled>Next</button>
              </div>
              <div class="ft-paragraph-status"></div>
            </div>
            <div class="ft-paragraph-right-rail">
              <article class="ft-paragraph-reward-preview" aria-live="polite" title="Right click for token support">
                <span class="ft-paragraph-reward-speed" role="spinbutton" tabindex="0" aria-label="Reward voice speed" aria-valuemin="50" aria-valuemax="100" aria-valuenow="70">
                  <span class="ft-paragraph-reward-speed-rail" aria-hidden="true"></span>
                  <span class="ft-paragraph-reward-speed-value">70%</span>
                </span>
                <span class="ft-paragraph-reward-icon" aria-hidden="true"></span>
                <span class="ft-paragraph-feather-rain" aria-hidden="true">
                  <b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b>
                  <b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b>
                </span>
                <span class="ft-paragraph-reward-copy">
                  <b class="ft-paragraph-reward-title">Golden Magic Bow</b>
                  <small class="ft-paragraph-reward-state">Correct without token helper</small>
                </span>
              </article>
              <div class="ft-paragraph-hint-clock ft-paragraph-side-clock" aria-live="polite" role="button" tabindex="0" title="Right click for token support. Click for guidance.">
                <span class="ft-paragraph-hint-orb"><span class="ft-paragraph-hint-time">--</span></span>
                <span class="ft-paragraph-hint-meta"><strong>AUTO HINT</strong><span class="ft-paragraph-hint-state">STANDBY</span></span>
                <span class="ft-paragraph-self-meter">
                  <span class="ft-paragraph-self-chart" aria-hidden="true"><strong class="ft-paragraph-self-total">0%</strong></span>
                  <span class="ft-paragraph-self-legend">
                    <span class="ft-paragraph-self-row is-typed"><b>TYPED</b><strong class="ft-paragraph-typed-stat">0%</strong></span>
                    <span class="ft-paragraph-self-row is-hint"><b>HINT</b><strong class="ft-paragraph-hint-stat">0%</strong></span>
                    <span class="ft-paragraph-self-row is-wrong"><b>WRONG</b><strong class="ft-paragraph-wrong-stat">0%</strong></span>
                  </span>
                </span>
              </div>
              <aside class="ft-space-s-reward-speed-menu" hidden aria-hidden="true" role="menu" aria-label="Space_S reward voice speed"></aside>
            </div>
          </div>
          <div class="ft-paragraph-explain-layer is-hidden">
            <article class="ft-paragraph-explain-card" role="dialog" aria-modal="true" aria-label="Paragraph explanation">
              <div class="ft-paragraph-explain-head">
                <div>
                  <div class="ft-paragraph-explain-kicker">GUIDANCE UPLINK</div>
                  <div class="ft-paragraph-explain-title"></div>
                </div>
                <button class="ft-paragraph-explain-close" type="button" aria-label="Close explanation">&times;</button>
              </div>
              <div class="ft-paragraph-explain-body"></div>
              <div class="ft-paragraph-explain-foot">
                <button class="ft-paragraph-explain-nav ft-paragraph-explain-prev" type="button">PREVIOUS</button>
                <div class="ft-paragraph-explain-index"></div>
                <button class="ft-paragraph-explain-nav ft-paragraph-explain-next" type="button">NEXT</button>
              </div>
            </article>
          </div>
        `;
        document.body.appendChild(root);
        paragraphEls = {
          root,
          shell: root.querySelector(".ft-paragraph-shell"),
          card: root.querySelector(".ft-paragraph-card"),
          micLive: root.querySelector(".ft-paragraph-mic-live"),
          spokenCard: root.querySelector(".ft-space-s-spoken-card"),
          spokenTitle: root.querySelector(".ft-space-s-spoken-card .ft-space-s-side-title"),
          spokenTokens: root.querySelector(".ft-space-s-spoken-tokens"),
          phoneticCard: root.querySelector(".ft-space-s-phonetic-card"),
          phoneticTitle: root.querySelector(".ft-space-s-phonetic-card .ft-space-s-side-title"),
          phoneticText: root.querySelector(".ft-space-s-phonetic-text"),
          title: root.querySelector(".ft-paragraph-node-title"),
          text: root.querySelector(".ft-paragraph-text"),
          meaning: root.querySelector(".ft-paragraph-meaning"),
          inputRow: root.querySelector(".ft-paragraph-input-row"),
          inputWrap: root.querySelector(".ft-paragraph-input-wrap"),
          inputGhost: root.querySelector(".ft-paragraph-input-ghost"),
          input: root.querySelector(".ft-paragraph-input"),
          replay: root.querySelector(".ft-paragraph-replay"),
          speech: root.querySelector(".ft-paragraph-speech"),
          next: root.querySelector(".ft-paragraph-next"),
          status: root.querySelector(".ft-paragraph-status"),
          progress: root.querySelector(".ft-paragraph-progress"),
          rightRail: root.querySelector(".ft-paragraph-right-rail"),
          clock: root.querySelector(".ft-paragraph-hint-clock"),
          clockTime: root.querySelector(".ft-paragraph-hint-time"),
          clockMeta: root.querySelector(".ft-paragraph-hint-state"),
          selfChart: root.querySelector(".ft-paragraph-self-chart"),
          selfTotal: root.querySelector(".ft-paragraph-self-total"),
          typedStat: root.querySelector(".ft-paragraph-typed-stat"),
          hintStat: root.querySelector(".ft-paragraph-hint-stat"),
          wrongStat: root.querySelector(".ft-paragraph-wrong-stat"),
          rewardPreview: root.querySelector(".ft-paragraph-reward-preview"),
          rewardSpeed: root.querySelector(".ft-paragraph-reward-speed"),
          rewardSpeedValue: root.querySelector(".ft-paragraph-reward-speed-value"),
          rewardSpeedMenu: root.querySelector(".ft-space-s-reward-speed-menu"),
          rewardTitle: root.querySelector(".ft-paragraph-reward-title"),
          rewardState: root.querySelector(".ft-paragraph-reward-state"),
          tokenHelper: root.querySelector(".ft-paragraph-token-helper"),
          tokenHelperNote: root.querySelector(".ft-paragraph-token-helper-note"),
          tokenHelperGrid: root.querySelector(".ft-paragraph-token-helper-grid"),
          tokenHelperClose: root.querySelector(".ft-paragraph-token-helper-close"),
          guide: root.querySelector(".ft-paragraph-hint-clock"),
          guideCount: root.querySelector(".ft-paragraph-guide-count"),
          posHint: root.querySelector(".ft-paragraph-pos-hint"),
          posLabel: root.querySelector(".ft-paragraph-pos-label"),
          posMeaning: root.querySelector(".ft-paragraph-pos-meaning"),
          posMask: root.querySelector(".ft-paragraph-pos-mask"),
          wordNotes: root.querySelector(".ft-paragraph-word-notes"),
          wordNoteTitleLeft: root.querySelector("[data-word-note-title-left]"),
          wordNoteTitleRight: root.querySelector("[data-word-note-title-right]"),
          wordNoteMeaning: root.querySelector("[data-word-note-meaning]"),
          wordNoteGrammar: root.querySelector("[data-word-note-grammar]"),
          wordNoteCloseButtons: root.querySelectorAll(".ft-paragraph-word-note-close"),
          explainLayer: root.querySelector(".ft-paragraph-explain-layer"),
          explainTitle: root.querySelector(".ft-paragraph-explain-title"),
          explainBody: root.querySelector(".ft-paragraph-explain-body"),
          explainIndex: root.querySelector(".ft-paragraph-explain-index"),
          explainPrev: root.querySelector(".ft-paragraph-explain-prev"),
          explainNext: root.querySelector(".ft-paragraph-explain-next"),
          explainClose: root.querySelector(".ft-paragraph-explain-close"),
          voiceMenu: null,
        };
        ensureSpaceSVoiceMenu();
        paragraphEls.input.addEventListener("input", syncParagraphInput);
        paragraphEls.input.addEventListener("scroll", syncParagraphInputGhost);
        paragraphEls.input.addEventListener("future:speech-input-mutated", () => {
          if (!isSpaceSpeechPayload()) {
            return;
          }
          queueParagraphInputTailFollow({ forceSelectionEnd: true, focusInput: true });
        });
        paragraphEls.text.addEventListener("selectstart", (event) => event.preventDefault());
        paragraphEls.text.addEventListener("dragstart", (event) => event.preventDefault());
        paragraphEls.text.addEventListener("click", handleParagraphWordNoteClick);
        paragraphEls.wordNoteCloseButtons.forEach((button) => {
          button.addEventListener("click", closeParagraphWordNotes);
        });
        window.addEventListener("resize", () => {
          hideSpaceSVoiceMenu();
          positionParagraphWordNotes();
          positionParagraphPosHint();
          positionParagraphTokenHelper();
        });
        root.addEventListener("pointerdown", (event) => {
          if (!(event.target && event.target.closest && event.target.closest(".ft-space-s-voice-menu"))) {
            hideSpaceSVoiceMenu();
          }
          if (!(event.target && event.target.closest && event.target.closest(".ft-space-s-reward-speed-menu,.ft-paragraph-reward-preview"))) {
            hideSpaceSRewardSpeedMenu();
          }
          retryPendingParagraphAudio();
        }, { capture: true });
        root.addEventListener("focusin", retryPendingParagraphAudio);
        root.addEventListener("keydown", retryPendingParagraphAudio, { capture: true });
        root.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            hideSpaceSVoiceMenu();
            hideSpaceSRewardSpeedMenu();
          }
        }, { capture: true });
        paragraphEls.shell.addEventListener("scroll", hideSpaceSVoiceMenu, { passive: true });
        paragraphEls.shell.addEventListener("scroll", hideSpaceSRewardSpeedMenu, { passive: true });
        paragraphEls.text.addEventListener("scroll", hideSpaceSVoiceMenu, { passive: true });
        paragraphEls.text.addEventListener("scroll", hideSpaceSRewardSpeedMenu, { passive: true });
        window.addEventListener("keydown", handleParagraphSpaceSShortcut, { capture: true });
        paragraphEls.input.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !paragraphEls.next.disabled) {
            event.preventDefault();
            advanceParagraphChild();
          }
        });
        paragraphEls.next.addEventListener("click", () => advanceParagraphChild());
        paragraphEls.replay.addEventListener("click", () => {
          if (isSpaceSpeechPayload()) {
            replaySpaceSUserAudio();
            return;
          }
          playParagraphEnglishAudio(currentParagraphChild());
        });
        paragraphEls.replay.addEventListener("contextmenu", (event) => {
          if (!isSpaceSpeechPayload()) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          showSpaceSVoiceMenu(event.clientX, event.clientY, currentParagraphChild());
        });
        paragraphEls.phoneticCard.addEventListener("click", () => {
          if (!isSpaceSpeechPayload()) {
            return;
          }
          void playParagraphEnglishAudio(currentParagraphChild(), { centerCurrent: true });
        });
        paragraphEls.phoneticCard.addEventListener("contextmenu", (event) => {
          if (!isSpaceSpeechPayload()) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          showSpaceSVoiceMenu(event.clientX, event.clientY, currentParagraphChild());
        });
        paragraphEls.input.addEventListener("keydown", (event) => {
          if (!isSpaceSpeechPayload()) return;
          if (event.key === "Control" && !event.repeat && !event.altKey && !event.shiftKey && !event.metaKey) {
            event.preventDefault();
            void startParagraphSpeakingDictation();
          } else if (event.key === "Alt" && !event.ctrlKey && !event.shiftKey && !event.metaKey) {
            event.preventDefault();
            if (handleSpaceSReplayStopShortcut()) {
              return;
            }
            void playParagraphEnglishAudio(currentParagraphChild(), { centerCurrent: true });
          }
        });
        paragraphEls.guide.addEventListener("click", () => {
          if (isSpaceSpeechPayload()) {
            void playParagraphEnglishAudio(currentParagraphChild());
            return;
          }
          openParagraphExplanationPopup();
        });
        paragraphEls.rewardPreview.addEventListener("click", handleParagraphRewardPreviewClick);
        paragraphEls.rewardPreview.addEventListener("contextmenu", handleParagraphGuideContextMenu, { capture: true });
        paragraphEls.rewardSpeed.addEventListener("pointerdown", handleSpaceSRewardSpeedPointerDown);
        paragraphEls.rewardSpeed.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
        });
        paragraphEls.rewardSpeed.addEventListener("keydown", handleSpaceSRewardSpeedKeydown);
        paragraphEls.guide.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (isSpaceSpeechPayload()) {
              void playParagraphEnglishAudio(currentParagraphChild());
            } else {
              openParagraphExplanationPopup();
            }
          }
        });
        paragraphEls.explainClose.addEventListener("click", closeParagraphExplanationPopup);
        paragraphEls.explainLayer.addEventListener("click", (event) => {
          if (event.target === paragraphEls.explainLayer) {
            closeParagraphExplanationPopup();
          }
        });
        paragraphEls.explainPrev.addEventListener("click", () => {
          paragraphExplanationIndex = Math.max(0, paragraphExplanationIndex - 1);
          renderParagraphExplanationPopup();
        });
        paragraphEls.explainNext.addEventListener("click", () => {
          const items = paragraphExplanationItems();
          paragraphExplanationIndex = Math.min(Math.max(0, items.length - 1), paragraphExplanationIndex + 1);
          renderParagraphExplanationPopup();
        });
        paragraphEls.tokenHelperClose.addEventListener("click", closeParagraphTokenHelper);
        return paragraphEls;
      }

      function paragraphWordParts(text = "") {
        return (String(text || "").match(/\S+\s*/g) || []).map((part) => ({
          raw: part,
          word: part.replace(/\s+$/g, ""),
          space: (part.match(/\s+$/) || [""])[0],
        }));
      }

      function paragraphWordKey(value = "") {
        try {
          return String(value || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^\p{L}\p{N}]+/gu, "")
            .trim();
        } catch (error) {
          return normalize(value).replace(/[^a-z0-9]+/g, "");
        }
      }

      function paragraphTypedWords(value = "") {
        return String(value || "")
          .trim()
          .split(/\s+/)
          .map(paragraphWordKey)
          .filter(Boolean);
      }

      function paragraphSpokenWordParts(value = "") {
        return (String(value || "").trim().match(/\S+/g) || [])
          .map((word) => ({
            raw: word,
            key: paragraphWordKey(word),
          }))
          .filter((item) => item.key);
      }

      function spaceSChildPhoneticText(child = currentParagraphChild()) {
        if (!child || typeof child !== "object") {
          return "";
        }
        const direct = clean(
          child.ipa_uk || child.ipaUK || child.ipa || child.phonetic_ipa || child.phoneticIpa ||
          child.pronunciation || child.phonetic || child.transcription || ""
        );
        if (direct) {
          return direct;
        }
        const rows = Array.isArray(child.word_pos) ? child.word_pos : (Array.isArray(child.wordPos) ? child.wordPos : []);
        const fromRows = rows
          .map((row) => clean(row && (row.ipa_uk || row.ipaUK || row.ipa || row.phonetic || row.pronunciation || "")))
          .filter(Boolean);
        return fromRows.join(" ");
      }

      function spaceSChildPhoneticEntries(child = currentParagraphChild()) {
        if (!child || typeof child !== "object") {
          return [];
        }
        const rows = Array.isArray(child.word_pos) ? child.word_pos : (Array.isArray(child.wordPos) ? child.wordPos : []);
        if (!rows.length) {
          return [];
        }
        const rowsByIndex = new Map();
        rows.forEach((row, index) => {
          if (!row || typeof row !== "object") {
            return;
          }
          const rowIndex = Math.max(0, Math.floor(Number(row.index ?? row.i ?? index) || 0));
          rowsByIndex.set(rowIndex, row);
        });
        return paragraphWordParts(child.text || "").map((part, index) => {
          const row = rowsByIndex.get(index) || {};
          const ipa = clean(
            row.ipa_uk || row.ipaUK || row.ipa_us || row.ipaUS || row.ipa || row.phonetic || row.pronunciation || ""
          );
          if (!ipa) {
            return null;
          }
          return {
            index,
            word: clean(row.word || part.word),
            ipa,
          };
        }).filter(Boolean);
      }

      function centerParagraphCardInShell(behavior = "smooth") {
        const els = paragraphEls || ensureParagraphRuntime();
        if (!els || !els.shell || !els.card || els.shell.scrollHeight <= els.shell.clientHeight + 8) {
          return;
        }
        const targetTop = Math.max(
          0,
          els.card.offsetTop - Math.max(0, (els.shell.clientHeight - els.card.offsetHeight) * 0.5)
        );
        try {
          els.shell.scrollTo({ top: targetTop, behavior });
        } catch (error) {
          els.shell.scrollTop = targetTop;
        }
      }

      function centerParagraphChildInMatrix(childIndex = paragraphChildIndex, behavior = "smooth") {
        const els = paragraphEls || ensureParagraphRuntime();
        if (!els || !els.text || !els.text.querySelectorAll) {
          return;
        }
        const targetChild = Math.max(0, Math.floor(Number(childIndex || 0) || 0));
        const nodes = Array.from(els.text.querySelectorAll(
          `.ft-paragraph-token[data-child="${targetChild}"], .ft-paragraph-punct[data-child="${targetChild}"]`
        ));
        if (!nodes.length || els.text.scrollHeight <= els.text.clientHeight + 8) {
          return;
        }
        let top = Number.POSITIVE_INFINITY;
        let bottom = 0;
        nodes.forEach((node) => {
          top = Math.min(top, node.offsetTop);
          bottom = Math.max(bottom, node.offsetTop + node.offsetHeight);
        });
        if (!Number.isFinite(top)) {
          return;
        }
        const blockHeight = Math.max(24, bottom - top);
        const targetTop = Math.max(0, top - Math.max(0, (els.text.clientHeight - blockHeight) * 0.5) - 12);
        try {
          els.text.scrollTo({ top: targetTop, behavior });
        } catch (error) {
          els.text.scrollTop = targetTop;
        }
      }

      function centerParagraphFocusInViewport(childIndex = paragraphChildIndex, behavior = "smooth") {
        window.requestAnimationFrame(() => {
          centerParagraphCardInShell(behavior);
          centerParagraphChildInMatrix(childIndex, behavior);
        });
      }

      function scrollSpaceSLatestSpokenToken(container) {
        if (!container) {
          return;
        }
        const latest = container.querySelector(".ft-space-s-spoken-token.is-latest");
        if (!latest) {
          return;
        }
        window.requestAnimationFrame(() => {
          try {
            container.classList.add("is-following-latest");
            const latestBottom = latest.offsetTop + latest.offsetHeight;
            const targetTop = Math.max(0, latestBottom - container.clientHeight + 18);
            container.scrollTo({ top: targetTop, behavior: "smooth" });
            window.clearTimeout(container._ftSpaceSFollowTimer || 0);
            container._ftSpaceSFollowTimer = window.setTimeout(() => {
              container.classList.remove("is-following-latest");
            }, 720);
          } catch (error) {
            try {
              latest.scrollIntoView({ block: "end", inline: "nearest", behavior: "smooth" });
            } catch (innerError) {
            }
          }
        });
      }

      function pulseSpaceSSpokenToken(chip) {
        if (!chip) {
          return;
        }
        chip.classList.remove("is-fresh");
        try {
          void chip.offsetWidth;
        } catch (error) {
        }
        chip.classList.add("is-fresh");
        window.clearTimeout(chip._ftSpaceSFreshTimer || 0);
        chip._ftSpaceSFreshTimer = window.setTimeout(() => {
          chip.classList.remove("is-fresh");
        }, 520);
      }

      function renderSpaceSSpokenTokens(container, spoken = [], expected = [], matched = new Set()) {
        if (!container) {
          return false;
        }
        const previousCount = Math.max(0, Math.floor(Number(container.dataset.spokenCount || 0) || 0));
        const previousLatestRaw = String(container.dataset.spokenLatestRaw || "");
        const chips = Array.from(container.querySelectorAll(".ft-space-s-spoken-token"));
        const emptyNode = container.querySelector(".ft-space-s-empty");
        if (!spoken.length) {
          chips.forEach((chip) => {
            window.clearTimeout(chip._ftSpaceSFreshTimer || 0);
          });
          container.textContent = "";
          container.classList.remove("is-following-latest");
          const empty = document.createElement("span");
          empty.className = "ft-space-s-empty";
          empty.textContent = "Your spoken tokens will appear here.";
          container.appendChild(empty);
          container.dataset.spokenCount = "0";
          container.dataset.spokenLatestRaw = "";
          return previousCount > 0;
        }
        if (emptyNode) {
          emptyNode.remove();
        }
        let shouldScrollLatest = false;
        spoken.forEach((item, index) => {
          let chip = chips[index];
          const existed = Boolean(chip);
          if (!chip) {
            chip = document.createElement("span");
            chip.className = "ft-space-s-spoken-token";
            container.appendChild(chip);
          }
          const previousRaw = String(chip.dataset.raw || "");
          if (chip.textContent !== item.raw) {
            chip.textContent = item.raw;
          }
          chip.dataset.raw = item.raw;
          chip.dataset.key = item.key;
          chip.dataset.index = String(index);
          const exact = expected[index] && expected[index] === item.key;
          const anywhere = expected.includes(item.key);
          const isLatest = index === spoken.length - 1;
          chip.classList.toggle("is-good", exact || matched.has(index));
          chip.classList.toggle("is-near", !exact && anywhere);
          chip.classList.toggle("is-wrong", !exact && !anywhere);
          chip.classList.toggle("is-latest", isLatest);
          if (isLatest && (!existed || index >= previousCount || previousLatestRaw !== item.raw || previousRaw !== item.raw)) {
            pulseSpaceSSpokenToken(chip);
            shouldScrollLatest = true;
          } else {
            chip.classList.remove("is-fresh");
          }
        });
        for (let index = spoken.length; index < chips.length; index += 1) {
          const chip = chips[index];
          if (!chip) {
            continue;
          }
          window.clearTimeout(chip._ftSpaceSFreshTimer || 0);
          chip.remove();
        }
        container.dataset.spokenCount = String(spoken.length);
        container.dataset.spokenLatestRaw = String(spoken[spoken.length - 1] && spoken[spoken.length - 1].raw || "");
        return shouldScrollLatest;
      }

      function scrollSpaceSPhoneticChipIntoView(wordIndex = -1, childIndex = paragraphChildIndex) {
        if (!paragraphEls || !paragraphEls.phoneticText || wordIndex < 0) {
          return;
        }
        const container = paragraphEls.phoneticText;
        if (container.scrollHeight <= container.clientHeight + 8) {
          return;
        }
        const target = container.querySelector(
          `.ft-space-s-phonetic-chip[data-child="${Math.max(0, Number(childIndex || 0) || 0)}"][data-word="${Math.max(0, Number(wordIndex || 0) || 0)}"]`
        );
        if (!target) {
          return;
        }
        const top = target.offsetTop;
        const bottom = top + target.offsetHeight;
        const viewTop = container.scrollTop;
        const viewBottom = viewTop + container.clientHeight;
        if (top >= viewTop + 8 && bottom <= viewBottom - 8) {
          return;
        }
        const targetTop = bottom > viewBottom
          ? Math.max(0, bottom - container.clientHeight + 18)
          : Math.max(0, top - 18);
        try {
          container.scrollTo({ top: targetTop, behavior: "smooth" });
        } catch (error) {
          container.scrollTop = targetTop;
        }
      }

      function renderSpaceSSideCards(score = 0, analysis = null) {
        if (!paragraphEls || !paragraphEls.root) {
          return;
        }
        const speakingMode = isSpaceSpeechPayload();
        const listeningMode = isSpaceLPayload();
        const els = paragraphEls;
        [els.spokenCard, els.phoneticCard].forEach((card) => {
          if (card) {
            card.hidden = !speakingMode;
            card.setAttribute("aria-hidden", speakingMode ? "false" : "true");
          }
        });
        if (!speakingMode) {
          return;
        }
        const child = currentParagraphChild();
        const transcript = els.input ? String(els.input.value || "") : "";
        const spoken = paragraphSpokenWordParts(transcript);
        const expected = currentParagraphWords();
        const matched = new Set();
        if (spaceSMatchedTokenKeys instanceof Set) {
          spaceSMatchedTokenKeys.forEach((key) => {
            const parts = String(key || "").split(":");
            if ((Number(parts[0] || 0) || 0) === paragraphChildIndex) {
              matched.add(Number(parts[1] || 0) || 0);
            }
          });
        }
        if (analysis && analysis.matchedIndexes instanceof Set) {
          analysis.matchedIndexes.forEach((index) => matched.add(Number(index) || 0));
        }
        const unlockedForGuide = listeningMode ? spaceLUnlockedIndexesForChild(paragraphChildIndex) : matched;
        const voiceMode = spaceSPreferredVoiceModeForChild(child);
        if (els.spokenTitle) {
          els.spokenTitle.textContent = transcript ? `Score ${Math.max(0, Math.min(100, Math.round(score || 0)))}%` : "Press Ctrl to speak";
        }
        if (els.spokenTokens) {
          if (renderSpaceSSpokenTokens(els.spokenTokens, spoken, expected, matched)) {
            scrollSpaceSLatestSpokenToken(els.spokenTokens);
          }
        }
        const phonetic = spaceSChildPhoneticText(child);
        const phoneticEntries = spaceSChildPhoneticEntries(child);
        const unlockedPhoneticEntries = listeningMode
          ? phoneticEntries.filter((entry) => unlockedForGuide.has(entry.index))
          : phoneticEntries;
        if (els.phoneticTitle) {
          els.phoneticTitle.textContent = child ? `Segment ${paragraphChildIndex + 1} | ${spaceSVoiceModeLabel(voiceMode, child)}` : "Phonetic guide";
        }
        if (els.phoneticText) {
          els.phoneticText.textContent = "";
          els.phoneticText.classList.toggle("is-empty", !phonetic || (listeningMode && !unlockedPhoneticEntries.length && !unlockedForGuide.size));
          if (!phonetic) {
            els.phoneticText.textContent = "Phonetic data is not embedded for this segment yet.";
          } else if (listeningMode && !unlockedPhoneticEntries.length && !unlockedForGuide.size) {
            els.phoneticText.textContent = "IPA unlocks after each correct token.";
          } else if (unlockedPhoneticEntries.length) {
            const fragment = document.createDocumentFragment();
            unlockedPhoneticEntries.forEach((entry) => {
              const chip = document.createElement("span");
              chip.className = "ft-space-s-phonetic-chip";
              chip.dataset.child = String(paragraphChildIndex);
              chip.dataset.word = String(entry.index);
              const word = document.createElement("span");
              word.className = "ft-space-s-phonetic-word";
              word.textContent = entry.word || `Word ${entry.index + 1}`;
              const ipaNode = document.createElement("span");
              ipaNode.className = "ft-space-s-phonetic-ipa";
              ipaNode.textContent = entry.ipa;
              chip.appendChild(word);
              chip.appendChild(ipaNode);
              fragment.appendChild(chip);
            });
            els.phoneticText.appendChild(fragment);
          } else {
            const fallback = document.createElement("span");
            fallback.className = "ft-space-s-phonetic-fallback";
            fallback.textContent = listeningMode && !unlockedForGuide.size ? "IPA unlocks after each correct token." : phonetic;
            els.phoneticText.appendChild(fallback);
          }
        }
        if (els.phoneticCard) {
          els.phoneticCard.dataset.voiceMode = voiceMode;
        }
        syncParagraphTokenClasses();
      }

      function paragraphSpeechSimilarityScore(actual = "", expectedText = "") {
        return paragraphSpeechAnalysis(actual, expectedText).score;
      }

      function paragraphSpeechAnalysis(actual = "", expectedText = "") {
        const actualWords = paragraphTypedWords(actual);
        const expectedWords = paragraphTypedWords(expectedText);
        const matchedIndexes = new Set();
        if (!expectedWords.length || !actualWords.length) {
          return { score: 0, matchedIndexes, matched: 0, total: expectedWords.length };
        }
        let matched = 0;
        const used = new Set();
        expectedWords.forEach((word, expectedIndex) => {
          if (actualWords[expectedIndex] === word) {
            matched += 1;
            matchedIndexes.add(expectedIndex);
            used.add(expectedIndex);
          }
        });
        expectedWords.forEach((word, expectedIndex) => {
          if (matchedIndexes.has(expectedIndex)) return;
          const exactIndex = actualWords.findIndex((actual, index) => !used.has(index) && actual === word);
          if (exactIndex >= 0) {
            matched += 1;
            matchedIndexes.add(expectedIndex);
            used.add(exactIndex);
            return;
          }
          const fuzzyIndex = actualWords.findIndex((actual, index) => (
            !used.has(index)
            && actual.length > 2
            && word.length > 2
            && (actual.includes(word) || word.includes(actual))
          ));
          if (fuzzyIndex >= 0) {
            matched += 0.6;
            matchedIndexes.add(expectedIndex);
            used.add(fuzzyIndex);
          }
        });
        return {
          score: Math.max(0, Math.min(100, Math.round((matched / expectedWords.length) * 100))),
          matchedIndexes,
          matched,
          total: expectedWords.length,
        };
      }

      function clearSpaceSUserAudio() {
        stopSpaceSReplayAudio();
        if (spaceSUserAudioUrl) {
          try {
            URL.revokeObjectURL(spaceSUserAudioUrl);
          } catch (error) {
          }
        }
        spaceSUserAudioUrl = "";
        spaceSUserAudioChunks = [];
        if (paragraphEls && paragraphEls.replay) {
          paragraphEls.replay.disabled = true;
        }
        updateSpaceSReplayButton();
      }

      function stopSpaceSUserRecording() {
        const recorder = spaceSUserRecorder;
        spaceSUserRecorder = null;
        if (recorder) {
          try {
            if (recorder.state && recorder.state !== "inactive") {
              recorder.stop();
            }
          } catch (error) {
          }
        }
        setSpaceSMicLiveState(false);
        return Boolean(recorder);
      }

      async function startSpaceSUserRecording() {
        stopSpaceSUserRecording();
        spaceSAutoReplayAfterRecordingStop = false;
        clearSpaceSUserAudio();
        if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function" || typeof MediaRecorder === "undefined") {
          return false;
        }
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream);
          spaceSUserRecorder = recorder;
          recorder.ondataavailable = (event) => {
            if (event && event.data && event.data.size > 0) {
              spaceSUserAudioChunks.push(event.data);
            }
          };
          recorder.onstop = () => {
            try {
              stream.getTracks().forEach((track) => track.stop());
            } catch (error) {
            }
            if (spaceSUserAudioChunks.length) {
              const blob = new Blob(spaceSUserAudioChunks, { type: recorder.mimeType || "audio/webm" });
              spaceSUserAudioUrl = URL.createObjectURL(blob);
            }
            updateSpaceSReplayButton();
            const shouldAutoReplay = Boolean(spaceSAutoReplayAfterRecordingStop && spaceSUserAudioUrl && paragraphModeActive && isSpaceSpeechPayload());
            spaceSAutoReplayAfterRecordingStop = false;
            if (shouldAutoReplay) {
              window.setTimeout(() => {
                if (paragraphModeActive && isSpaceSpeechPayload()) {
                  replaySpaceSUserAudio({ skipFinalize: true, statusMessage: "Replaying your latest voice. Press Stop or Alt to stop." });
                }
              }, 160);
            }
          };
          recorder.start();
          setSpaceSMicLiveState(true);
          return true;
        } catch (error) {
          setSpaceSMicLiveState(false);
          return false;
        }
      }

      function replaySpaceSUserAudio(options = {}) {
        const els = ensureParagraphRuntime();
        if (spaceSReplayAudio && !spaceSReplayAudio.paused && !spaceSReplayAudio.ended) {
          stopSpaceSReplayAudio();
          updateSpaceSReplayButton();
          els.status.textContent = "Replay stopped.";
          return false;
        }
        if (!spaceSUserAudioUrl) {
          els.status.textContent = "No recorded voice yet. Press Ctrl and read first.";
          return false;
        }
        if (!(options && options.skipFinalize)) {
          stopSpaceSListeningSession({ finalizeAttempt: true });
        }
        stopParagraphAudioPlayback();
        try {
          const audio = new Audio(spaceSUserAudioUrl);
          spaceSReplayAudio = audio;
          updateSpaceSReplayButton();
          const clear = () => {
            if (spaceSReplayAudio === audio) {
              spaceSReplayAudio = null;
              updateSpaceSReplayButton();
            }
          };
          audio.addEventListener("ended", clear, { once: true });
          audio.addEventListener("pause", () => {
            if (audio.ended) {
              clear();
            }
          });
          audio.play().catch(() => {
            clear();
          });
          els.status.textContent = clean(options && options.statusMessage) || "Replaying your latest voice.";
          return true;
        } catch (error) {
          spaceSReplayAudio = null;
          updateSpaceSReplayButton();
          return false;
        }
      }

      function handleParagraphSpaceSShortcut(event) {
        if (!paragraphModeActive || !isSpaceSpeechPayload() || !paragraphEls || event.defaultPrevented) {
          return;
        }
        if (event.target === paragraphEls.input) {
          return;
        }
        if (event.key === "Control" && !event.repeat && !event.altKey && !event.shiftKey && !event.metaKey) {
          event.preventDefault();
          void startParagraphSpeakingDictation();
        } else if (event.key === "Alt" && !event.ctrlKey && !event.shiftKey && !event.metaKey) {
          event.preventDefault();
          if (handleSpaceSReplayStopShortcut()) {
            return;
          }
          void playParagraphEnglishAudio(currentParagraphChild(), { centerCurrent: true });
        }
      }

      async function startParagraphSpeakingDictation() {
        const els = ensureParagraphRuntime();
        if (!isSpaceSpeechPayload() || !els.input || !els.speech) return;
        if (isSpaceSListeningActive(els)) {
          stopSpaceSListeningSession({ finalizeAttempt: true, autoReplayRecordedVoice: true });
          if (els.status && !(spaceSUserRecorder && spaceSUserRecorder.state && spaceSUserRecorder.state !== "inactive")) {
            const raw = els.input ? String(els.input.value || "").trim() : "";
            if (isSpaceLPayload() && spaceLUnlockChoiceAvailable) {
              els.status.textContent = "Choose one highlighted hidden block to unlock.";
            } else {
              els.status.textContent = raw
                ? "Recording stopped. Preparing replay."
                : "Mic stopped.";
            }
          }
          return;
        }
        if (!spaceSReadSessionFinalized && els.input && String(els.input.value || "").trim()) {
          stopSpaceSListeningSession({ finalizeAttempt: true });
        }
        stopParagraphAudioPlayback();
        stopSpaceSReplayAudio();
        if (isSpaceLPayload() && spaceLUnlockChoiceAvailable) {
          spaceLUnlockChoiceAvailable = false;
        }
        els.input.value = "";
        spaceSMatchedTokenKeys = new Set();
        spaceSReadSessionHasInput = false;
        spaceSReadSessionFinalized = false;
        spaceSLastReadScore = 0;
        centerParagraphFocusInViewport(paragraphChildIndex);
        syncParagraphTokenClasses();
        renderSpaceSSideCards();
        syncParagraphInputGhost();
        syncSpaceSManualInputGate(0);
        updateSpaceSReplayButton();
        renderSpaceSSideCards();
        els.status.textContent = "Browser EN listening. Read the sentence.";
        await startSpaceSUserRecording();
        if (typeof toggleBrowserMultilingualInputDictation === "function") {
          await toggleBrowserMultilingualInputDictation(els.input, els.speech, "space_s_speaking", { language: "en-US" });
        } else if (typeof toggleFutureSpeechInputDictation === "function") {
          await toggleFutureSpeechInputDictation(els.input, els.speech, "space_s_speaking", { language: "en-US" });
        }
        if (isSpaceSListeningActive(els)) {
          setSpaceSMicLiveState(true);
          startSpaceSListeningIdleWatch();
        }
      }

      function paragraphCommittedInput(value = "", expected = []) {
        const raw = String(value || "");
        const words = paragraphTypedWords(raw);
        const hasTrailingSpace = /\s$/.test(raw);
        const completeExact = Boolean(
          expected.length &&
          words.length === expected.length &&
          words.every((word, index) => word === expected[index])
        );
        const committedCount = hasTrailingSpace || completeExact
          ? words.length
          : Math.max(0, words.length - 1);
        return {
          words,
          committed: words.slice(0, committedCount),
          partial: words[committedCount] || "",
          completeExact,
        };
      }

      function currentParagraphNode() {
        return paragraphNodes[paragraphNodeIndex] || null;
      }

      function currentParagraphChild() {
        const node = currentParagraphNode();
        return node && Array.isArray(node.children) ? node.children[paragraphChildIndex] || null : null;
      }

      function currentParagraphWords() {
        const child = currentParagraphChild();
        return paragraphWordParts(child ? child.text : "").map((part) => paragraphWordKey(part.word)).filter(Boolean);
      }

      function paragraphSegmentSupportKey(childIndex = paragraphChildIndex) {
        return `${paragraphRewardLessonIdentity()}:${paragraphNodeIndex}:${Math.max(0, Number(childIndex) || 0)}`;
      }

      function paragraphCurrentTokenSurfaces() {
        const child = currentParagraphChild();
        return paragraphWordParts(child ? child.text : "")
          .map((part) => clean(part.word))
          .filter((word) => paragraphWordKey(word));
      }

      function paragraphCurrentTokenItems() {
        const child = currentParagraphChild();
        return paragraphWordParts(child ? child.text : "")
          .map((part, index) => ({
            label: clean(part.word),
            wordIndex: index,
          }))
          .filter((item) => paragraphWordKey(item.label));
      }

      function shuffleParagraphTokens(tokens = []) {
        const items = (Array.isArray(tokens) ? tokens : []).slice();
        for (let index = items.length - 1; index > 0; index -= 1) {
          const swapIndex = Math.floor(Math.random() * (index + 1));
          const value = items[index];
          items[index] = items[swapIndex];
          items[swapIndex] = value;
        }
        return items;
      }

      // Added 2026-07-06: limits paragraph token support to a random set of upcoming untyped words.
      function paragraphCurrentSupportTokenItems(limit = 5) {
        const tokens = paragraphCurrentTokenItems();
        if (!tokens.length) {
          return { tokens: [], limited: false, remaining: 0 };
        }
        const els = ensureParagraphRuntime();
        const expected = currentParagraphWords();
        const inputState = paragraphCommittedInput(els.input ? els.input.value : "", expected);
        let matched = 0;
        for (let index = 0; index < inputState.committed.length && index < expected.length; index += 1) {
          if (inputState.committed[index] !== expected[index]) {
            break;
          }
          matched += 1;
        }
        const upcoming = tokens.filter((token) => {
          const rawWordIndex = token && typeof token === "object" ? Number(token.wordIndex) : -1;
          const wordIndex = Number.isFinite(rawWordIndex) ? Math.max(-1, Math.floor(rawWordIndex)) : -1;
          return wordIndex < 0 || wordIndex >= matched;
        });
        const safeLimit = Math.max(1, Math.floor(Number(limit) || 5));
        if (upcoming.length <= safeLimit) {
          return { tokens: shuffleParagraphTokens(upcoming), limited: false, remaining: upcoming.length };
        }
        return {
          tokens: shuffleParagraphTokens(upcoming).slice(0, safeLimit),
          limited: true,
          remaining: upcoming.length,
        };
      }

      function handleParagraphRewardPreviewClick(event) {
        const target = event && event.target && event.target.closest
          ? event.target.closest(".ft-paragraph-reward-preview")
          : null;
        if (!target || (paragraphEls && paragraphEls.rewardPreview && target !== paragraphEls.rewardPreview)) {
          return;
        }
        if (isSpaceRewardPlaybackPayload()) {
          if (event) {
            event.preventDefault();
            event.stopPropagation();
          }
          playParagraphRewardShotAnimation();
          void playParagraphEnglishAudio(currentParagraphChild(), {
            centerCurrent: true,
            playbackRate: spaceSRewardPlaybackRate,
          });
          return;
        }
        handleParagraphGuideContextMenu(event);
      }

      function syncSpaceSRewardSpeedBadge() {
        if (!paragraphEls || !paragraphEls.rewardSpeed) {
          return;
        }
        const percent = Math.round((Number(spaceSRewardPlaybackRate || 1) || 1) * 100);
        if (paragraphEls.rewardSpeedValue) {
          paragraphEls.rewardSpeedValue.textContent = `${percent}%`;
          paragraphEls.rewardSpeedValue.classList.remove("is-turning");
          void paragraphEls.rewardSpeedValue.offsetWidth;
          paragraphEls.rewardSpeedValue.classList.add("is-turning");
        } else {
          paragraphEls.rewardSpeed.textContent = `${percent}%`;
        }
        paragraphEls.rewardSpeed.title = `Reward voice speed ${percent}%`;
        paragraphEls.rewardSpeed.setAttribute("aria-valuenow", String(percent));
        const offset = (2 - spaceSRewardRateIndex()) * 3;
        paragraphEls.rewardSpeed.style.setProperty("--reward-speed-index", String(spaceSRewardRateIndex()));
        paragraphEls.rewardSpeed.style.setProperty("--reward-speed-offset", `${offset}px`);
        paragraphEls.rewardSpeed.hidden = !isSpaceRewardPlaybackPayload();
        paragraphEls.rewardSpeed.setAttribute("aria-hidden", isSpaceRewardPlaybackPayload() ? "false" : "true");
      }

      function spaceSRewardRateIndex(rate = spaceSRewardPlaybackRate) {
        const value = Number(rate || 0) || 0.7;
        const index = SPACE_S_REWARD_PLAYBACK_RATES.findIndex((item) => Math.abs(item - value) < 0.001);
        return index >= 0 ? index : 2;
      }

      function setSpaceSRewardPlaybackRateByIndex(index = spaceSRewardRateIndex(), options = {}) {
        const nextIndex = Math.max(0, Math.min(SPACE_S_REWARD_PLAYBACK_RATES.length - 1, Math.round(Number(index || 0) || 0)));
        const nextRate = SPACE_S_REWARD_PLAYBACK_RATES[nextIndex] || 0.7;
        if (Math.abs(nextRate - spaceSRewardPlaybackRate) < 0.001 && !options.force) {
          return false;
        }
        spaceSRewardPlaybackRate = nextRate;
        syncSpaceSRewardSpeedBadge();
        renderSpaceSRewardSpeedMenu();
        const els = paragraphEls;
        if (els && els.status && options.status !== false) {
          els.status.textContent = `Reward voice speed ${Math.round(nextRate * 100)}%. Click the wings to hear it.`;
        }
        return true;
      }

      function handleSpaceSRewardSpeedPointerDown(event) {
        if (!isSpaceRewardPlaybackPayload()) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        hideSpaceSRewardSpeedMenu();
        const startY = Number(event.clientY || 0) || 0;
        const startIndex = spaceSRewardRateIndex();
        spaceSRewardSpeedDrag = { startY, startIndex };
        paragraphEls.rewardSpeed.classList.add("is-dragging");
        try {
          paragraphEls.rewardSpeed.setPointerCapture(event.pointerId);
        } catch (error) {
        }
        const handleMove = (moveEvent) => {
          if (!spaceSRewardSpeedDrag) {
            return;
          }
          const delta = spaceSRewardSpeedDrag.startY - (Number(moveEvent.clientY || 0) || 0);
          const step = Math.round(delta / 22);
          setSpaceSRewardPlaybackRateByIndex(spaceSRewardSpeedDrag.startIndex + step, { status: false });
        };
        const handleUp = () => {
          window.removeEventListener("pointermove", handleMove, true);
          window.removeEventListener("pointerup", handleUp, true);
          window.removeEventListener("pointercancel", handleUp, true);
          spaceSRewardSpeedDrag = null;
          if (paragraphEls && paragraphEls.rewardSpeed) {
            paragraphEls.rewardSpeed.classList.remove("is-dragging");
          }
        };
        window.addEventListener("pointermove", handleMove, true);
        window.addEventListener("pointerup", handleUp, true);
        window.addEventListener("pointercancel", handleUp, true);
      }

      function handleSpaceSRewardSpeedKeydown(event) {
        if (!isSpaceRewardPlaybackPayload()) {
          return;
        }
        const key = event.key;
        if (key === "ArrowUp" || key === "ArrowRight") {
          event.preventDefault();
          event.stopPropagation();
          setSpaceSRewardPlaybackRateByIndex(spaceSRewardRateIndex() + 1);
        } else if (key === "ArrowDown" || key === "ArrowLeft") {
          event.preventDefault();
          event.stopPropagation();
          setSpaceSRewardPlaybackRateByIndex(spaceSRewardRateIndex() - 1);
        } else if (key === "Home") {
          event.preventDefault();
          event.stopPropagation();
          setSpaceSRewardPlaybackRateByIndex(0);
        } else if (key === "End") {
          event.preventDefault();
          event.stopPropagation();
          setSpaceSRewardPlaybackRateByIndex(SPACE_S_REWARD_PLAYBACK_RATES.length - 1);
        }
      }

      function hideSpaceSRewardSpeedMenu() {
        if (!paragraphEls || !paragraphEls.rewardSpeedMenu) {
          return;
        }
        paragraphEls.rewardSpeedMenu.hidden = true;
        paragraphEls.rewardSpeedMenu.setAttribute("aria-hidden", "true");
      }

      function renderSpaceSRewardSpeedMenu() {
        const menu = paragraphEls && paragraphEls.rewardSpeedMenu;
        if (!menu) {
          return null;
        }
        menu.textContent = "";
        const head = document.createElement("div");
        head.className = "ft-space-s-reward-speed-head";
        const title = document.createElement("strong");
        title.textContent = "Reward voice";
        const meta = document.createElement("span");
        meta.textContent = "Speed";
        head.appendChild(title);
        head.appendChild(meta);
        menu.appendChild(head);
        const grid = document.createElement("div");
        grid.className = "ft-space-s-reward-speed-grid";
        SPACE_S_REWARD_PLAYBACK_RATES.forEach((rate) => {
          const button = document.createElement("button");
          const percent = Math.round(rate * 100);
          button.type = "button";
          button.className = "ft-space-s-reward-speed-action";
          button.textContent = `${percent}%`;
          button.setAttribute("role", "menuitemradio");
          button.setAttribute("aria-checked", Math.abs(rate - spaceSRewardPlaybackRate) < 0.001 ? "true" : "false");
          button.classList.toggle("is-selected", Math.abs(rate - spaceSRewardPlaybackRate) < 0.001);
          button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            spaceSRewardPlaybackRate = rate;
            syncSpaceSRewardSpeedBadge();
            hideSpaceSRewardSpeedMenu();
            const els = ensureParagraphRuntime();
            if (els.status) {
              els.status.textContent = `Reward voice speed ${percent}%. Click the wings to hear it.`;
            }
          });
          grid.appendChild(button);
        });
        menu.appendChild(grid);
        return menu;
      }

      function showSpaceSRewardSpeedMenu(x = 0, y = 0) {
        if (!isSpaceSPayload()) {
          return;
        }
        const menu = renderSpaceSRewardSpeedMenu();
        if (!menu) {
          return;
        }
        menu.hidden = false;
        menu.setAttribute("aria-hidden", "false");
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1024;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 768;
        const width = 210;
        const height = 154;
        const left = Math.max(12, Math.min(viewportWidth - width - 12, Math.round(Number(x || 0) || 0)));
        const top = Math.max(12, Math.min(viewportHeight - height - 12, Math.round(Number(y || 0) || 0)));
        menu.style.left = `${left}px`;
        menu.style.top = `${top}px`;
      }

      function handleParagraphGuideContextMenu(event) {
        const target = event && event.target && event.target.closest
          ? event.target.closest(".ft-paragraph-reward-preview")
          : null;
        if (!target || (paragraphEls && paragraphEls.rewardPreview && target !== paragraphEls.rewardPreview)) {
          return;
        }
        if (isSpaceRewardPlaybackPayload()) {
          if (event) {
            event.preventDefault();
            event.stopPropagation();
          }
          showSpaceSRewardSpeedMenu(event && event.clientX, event && event.clientY);
          return;
        }
        if (event.type === "contextmenu") {
          event.preventDefault();
        }
        event.stopPropagation();
        openParagraphTokenHelper();
      }

      function paragraphCurrentPosHintKey() {
        return `${paragraphNodeIndex}:${paragraphChildIndex}:${Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0)}`;
      }

      function paragraphWordSurface(value = "") {
        const source = String(value || "");
        try {
          return source.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "") || source;
        } catch (error) {
          return source.replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, "") || source;
        }
      }

      function paragraphDisplayWordPieces(value = "") {
        const source = String(value || "");
        if (!source) {
          return { prefix: "", word: "", suffix: "" };
        }
        let hasCore = false;
        try {
          hasCore = /[\p{L}\p{N}]/u.test(source);
        } catch (error) {
          hasCore = /[A-Za-z0-9]/.test(source);
        }
        if (!hasCore) {
          return { prefix: source, word: "", suffix: "" };
        }
        const surface = paragraphWordSurface(source);
        const start = source.indexOf(surface);
        if (!surface || start < 0) {
          return { prefix: "", word: source, suffix: "" };
        }
        return {
          prefix: source.slice(0, start),
          word: surface,
          suffix: source.slice(start + surface.length),
        };
      }

      function paragraphWordPosFor(childIndex = 0, wordIndex = 0, word = "") {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        const child = children[Number(childIndex) || 0] || null;
        const items = child && Array.isArray(child.word_pos) ? child.word_pos : [];
        if (!items.length) {
          return null;
        }
        const wordKey = paragraphWordKey(word);
        const exact = items.find((item) => {
          const itemIndex = Math.max(0, Math.floor(Number(item && item.index) || 0));
          return itemIndex === wordIndex && (!item.word || paragraphWordKey(item.word) === wordKey);
        });
        const fallback = exact
          || items.find((item) => Math.max(0, Math.floor(Number(item && item.index) || 0)) === wordIndex)
          || items.find((item) => item && item.word && paragraphWordKey(item.word) === wordKey);
        return fallback || null;
      }

      function paragraphWordAudioFor(childIndex = 0, wordIndex = 0, word = "") {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        const child = children[Number(childIndex) || 0] || null;
        const items = child && Array.isArray(child.word_audio) ? child.word_audio : [];
        if (!items.length) {
          return null;
        }
        const wordKey = paragraphWordKey(word);
        const exact = items.find((item) => {
          const itemIndex = Math.max(0, Math.floor(Number(item && item.index) || 0));
          return itemIndex === wordIndex && (!item.word || paragraphWordKey(item.word) === wordKey);
        });
        const fallback = exact
          || items.find((item) => Math.max(0, Math.floor(Number(item && item.index) || 0)) === wordIndex)
          || items.find((item) => item && item.word && paragraphWordKey(item.word) === wordKey);
        if (!fallback || !normalizeAudioClip(fallback)) {
          return null;
        }
        return fallback;
      }

      function paragraphPlaybackClip(child = currentParagraphChild(), options = {}) {
        if (!child || typeof child !== "object") {
          return null;
        }
        if (options && options.alt) {
          return child.alt_audio || child.altAudio || child.audio_alt || child.audioAlt || child.audio || null;
        }
        return child.audio || null;
      }

      function clearParagraphAudioHighlight(audio = null) {
        if (audio && paragraphAudioHighlightAudio && audio !== paragraphAudioHighlightAudio) {
          return;
        }
        if (paragraphAudioHighlightFrame) {
          window.cancelAnimationFrame(paragraphAudioHighlightFrame);
          paragraphAudioHighlightFrame = 0;
        }
        paragraphAudioHighlightAudio = null;
        paragraphAudioHighlightIndex = -1;
        if (!paragraphEls || !paragraphEls.text) {
          return;
        }
        paragraphEls.text.querySelectorAll(".ft-paragraph-token.is-reading, .ft-paragraph-punct.is-reading").forEach((node) => {
          node.classList.remove("is-reading");
        });
        if (paragraphEls.phoneticText) {
          paragraphEls.phoneticText.querySelectorAll(".ft-space-s-phonetic-chip.is-reading").forEach((node) => {
            node.classList.remove("is-reading");
          });
        }
        if (paragraphEls.root) {
          paragraphEls.root.classList.remove("is-paragraph-audio-reading");
        }
      }

      function paragraphTimingTokens(child = currentParagraphChild()) {
        if (!child || typeof child !== "object") {
          return [];
        }
        const rows = Array.isArray(child.word_pos) ? child.word_pos : (Array.isArray(child.wordPos) ? child.wordPos : []);
        const rowsByIndex = new Map();
        rows.forEach((row, index) => {
          if (!row || typeof row !== "object") return;
          rowsByIndex.set(Math.max(0, Math.floor(Number(row.index ?? row.i ?? index) || 0)), row);
        });
        return paragraphWordParts(child.text || "").map((part, index) => {
          const row = rowsByIndex.get(index) || {};
          return {
            t: clean(row.word || part.word),
            i: clean(row.ipa_uk || row.ipaUK || row.ipa_us || row.ipaUS || row.ipa || row.phonetic || row.pronunciation || ""),
          };
        }).filter((item) => item.t);
      }

      function paragraphBuildWeightedTimings(child = currentParagraphChild(), durationMs = 0) {
        const tokens = paragraphTimingTokens(child);
        if (!tokens.length) {
          return [];
        }
        const text = clean(child && child.text);
        const requestedDuration = Math.max(0, Number(durationMs || 0) || 0);
        const baseDuration = Math.max(requestedDuration, estimateSpeechDuration(text, tokens));
        const weights = tokens.map((token) => {
          const tokenText = clean(token.t);
          const normalized = normalizeTimingToken(tokenText);
          let weight = Math.max(0.45, (normalized || tokenText).length || 1);
          if (/[.,!?;:]$/.test(tokenText)) {
            weight += 0.36;
          }
          const ipaText = clean(token.i);
          if (ipaText) {
            weight = Math.max(weight, ipaTimingWeight(ipaText));
          }
          return Math.max(0.45, weight);
        });
        const totalWeight = Math.max(0.01, weights.reduce((sum, value) => sum + Number(value || 0), 0));
        let leadMs = Math.min(90, baseDuration * 0.06);
        let tailMs = Math.min(120, baseDuration * 0.08);
        if (baseDuration <= leadMs + tailMs + 90) {
          leadMs = 0;
          tailMs = 0;
        }
        const usableMs = Math.max(80, baseDuration - leadMs - tailMs);
        const minSpan = 45;
        const lastIndex = tokens.length - 1;
        let cursor = leadMs;
        let cumulative = 0;
        return tokens.map((_token, index) => {
          const start = cursor;
          let end;
          if (index >= lastIndex) {
            end = Math.max(baseDuration - tailMs, start + 1);
          } else {
            cumulative += Number(weights[index] || 0);
            const predicted = leadMs + (usableMs * cumulative / totalWeight);
            const remaining = Math.max(1, lastIndex - index);
            const maxEnd = baseDuration - tailMs - (remaining * minSpan);
            end = Math.max(start + minSpan, predicted);
            if (maxEnd > start) {
              end = Math.min(end, maxEnd);
            }
          }
          end = Math.min(baseDuration, Math.max(start + 1, end));
          cursor = end;
          return {
            index,
            start: Math.round(start),
            end: Math.round(end),
          };
        });
      }

      function paragraphTimingsForClip(child = currentParagraphChild(), clip = null, audio = null) {
        const clipTimings = normalizeTimingList(Array.isArray(clip && (clip.timings ?? clip.tm)) ? (clip.timings ?? clip.tm) : []);
        const durationMs = Number.isFinite(audio && audio.duration) && audio.duration > 0
          ? audio.duration * 1000
          : Math.max(0, Number((clip && (clip.duration_ms ?? clip.durationMs ?? clip.d)) || 0) || 0);
        if (clipTimings.length) {
          return scaleTimingsToDuration(clipTimings, durationMs);
        }
        return paragraphBuildWeightedTimings(child, durationMs);
      }

      function setParagraphActiveHighlightIndex(activeIndex, childIndex = paragraphChildIndex) {
        if (!paragraphEls || !paragraphEls.text) {
          return;
        }
        const targetChild = Math.max(0, Math.floor(Number(childIndex || 0) || 0));
        if (paragraphAudioHighlightIndex !== activeIndex) {
          paragraphAudioHighlightIndex = activeIndex;
          scrollSpaceSPhoneticChipIntoView(activeIndex, targetChild);
        }
        paragraphEls.text.querySelectorAll(".ft-paragraph-token").forEach((item) => {
          const itemChild = Number(item.dataset.child || 0) || 0;
          const itemWord = Number(item.dataset.word || 0) || 0;
          item.classList.toggle("is-reading", itemChild === targetChild && itemWord === activeIndex);
        });
        paragraphEls.text.querySelectorAll(".ft-paragraph-punct").forEach((item) => {
          const itemChild = Number(item.dataset.child || 0) || 0;
          const itemWord = Number(item.dataset.word || 0) || 0;
          item.classList.toggle("is-reading", itemChild === targetChild && itemWord === activeIndex);
        });
        if (paragraphEls.phoneticText) {
          paragraphEls.phoneticText.querySelectorAll(".ft-space-s-phonetic-chip").forEach((item) => {
            const itemChild = Number(item.dataset.child || 0) || 0;
            const itemWord = Number(item.dataset.word || 0) || 0;
            item.classList.toggle("is-reading", itemChild === targetChild && itemWord === activeIndex);
          });
        }
      }

      function startParagraphAudioHighlight(audio, child = currentParagraphChild(), clip = null, childIndex = paragraphChildIndex) {
        if (!audio || !child || !isSpaceSpeechPayload()) {
          return;
        }
        const targetChild = Math.max(0, Math.floor(Number(childIndex || 0) || 0));
        const start = () => {
          const timings = paragraphTimingsForClip(child, clip, audio);
          if (!timings.length) {
            clearParagraphAudioHighlight(audio);
            return;
          }
          clearParagraphAudioHighlight();
          paragraphAudioHighlightAudio = audio;
          if (paragraphEls && paragraphEls.root) {
            paragraphEls.root.classList.add("is-paragraph-audio-reading");
          }
          const tick = () => {
            if (paragraphAudioHighlightAudio !== audio || !paragraphModeActive || currentParagraphChild() !== child) {
              return;
            }
            const elapsed = Math.max(0, (Number(audio.currentTime || 0) || 0) * 1000);
            let activeIndex = -1;
            for (const item of timings) {
              if (elapsed >= item.start && elapsed < item.end) {
                activeIndex = Number(item.index ?? item.i ?? 0) || 0;
                break;
              }
            }
            setParagraphActiveHighlightIndex(activeIndex, targetChild);
            if (!audio.paused && !audio.ended) {
              paragraphAudioHighlightFrame = window.requestAnimationFrame(tick);
            }
          };
          tick();
        };
        audio.addEventListener("loadedmetadata", start);
        audio.addEventListener("play", start);
        audio.addEventListener("pause", () => clearParagraphAudioHighlight(audio));
        audio.addEventListener("ended", () => clearParagraphAudioHighlight(audio));
      }

      const PARAGRAPH_POS_LABELS = {
        ADJ: "ADJ | adjective | tính từ",
        ADP: "ADP | preposition | giới từ",
        ADV: "ADV | adverb | trạng từ",
        AUX: "AUX | auxiliary verb | trợ động từ",
        CCONJ: "CCONJ | coordinating conjunction | liên từ đẳng lập",
        DET: "DET | determiner | từ hạn định",
        INTJ: "INTJ | interjection | thán từ",
        NOUN: "NOUN | noun | danh từ",
        NUM: "NUM | number | số từ",
        PART: "PART | particle | tiểu từ",
        PRON: "PRON | pronoun | đại từ",
        PROPN: "PROPN | proper noun | danh từ riêng",
        SCONJ: "SCONJ | subordinating conjunction | liên từ phụ thuộc",
        VERB: "VERB | verb | động từ",
        X: "X | unknown | chưa xác định",
      };

      function paragraphPosLabel(info = null) {
        const pos = clean(info && (info.pos || info.p)).toUpperCase();
        return PARAGRAPH_POS_LABELS[pos] || (pos ? `${pos} | part of speech | loại từ` : "WORD TYPE");
      }

      function paragraphEscapeRegExp(value = "") {
        return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      }

      function paragraphMeaningHintFor(childIndex = 0, wordIndex = 0, expectedWord = "", posInfo = null) {
        const note = paragraphWordNoteFor(childIndex, wordIndex, expectedWord);
        let value = preserveQuestionText(note && note.meaning ? note.meaning : "");
        if (!value) {
          return "";
        }
        const hiddenWords = [expectedWord, note && note.word, posInfo && (posInfo.lemma || posInfo.l)]
          .map((item) => clean(item))
          .filter(Boolean);
        Array.from(new Set(hiddenWords.map((item) => item.toLowerCase()))).forEach((item) => {
          value = value.replace(new RegExp(`\\b${paragraphEscapeRegExp(item)}\\b`, "gi"), "từ này");
        });
        return value.length > 170 ? `${value.slice(0, 167).trim()}...` : value;
      }

      function paragraphCurrentPartialWord(expected = []) {
        const els = ensureParagraphRuntime();
        const state = paragraphCommittedInput(els.input ? els.input.value : "", expected);
        return state.partial || "";
      }

      function renderParagraphPosMask(maskText = "", expectedWord = "") {
        const els = ensureParagraphRuntime();
        if (!els.posMask) {
          return;
        }
        els.posMask.textContent = "";
        const chars = Array.from(maskText || "");
        chars.forEach((char) => {
          const cell = document.createElement("span");
          cell.className = "ft-paragraph-pos-char";
          if (char === "*") {
            cell.classList.add("is-waiting");
          } else {
            cell.classList.add("is-ok");
          }
          cell.textContent = char || "*";
          els.posMask.appendChild(cell);
        });
        const correct = chars.filter((char) => char && char !== "*").length;
        const total = Math.max(1, Array.from(expectedWord || "").filter((char) => /[A-Za-z0-9]/.test(char)).length || chars.length);
        if (els.posHint) {
          els.posHint.style.setProperty("--paragraph-pos-score", `${Math.max(0, Math.min(100, Math.round((correct / total) * 100)))}%`);
        }
      }

      function updateParagraphPosHint(visible = true) {
        if (isSpaceSpeechPayload()) {
          visible = false;
        }
        if (!visible && (!paragraphEls || !paragraphEls.root)) {
          paragraphPosHintKey = "";
          return;
        }
        const els = ensureParagraphRuntime();
        if (!els.posHint || !els.posLabel || !els.posMask) {
          return;
        }
        const child = currentParagraphChild();
        const revealed = Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0);
        const parts = child ? paragraphWordParts(child.text) : [];
        const part = parts[revealed] || null;
        if (!visible || !paragraphModeActive || !child || !part) {
          paragraphPosHintKey = "";
          els.posHint.classList.remove("is-visible");
          els.posHint.classList.remove("is-meaning-live");
          els.posHint.style.setProperty("--paragraph-pos-score", "0%");
          els.posLabel.textContent = "STANDBY";
          if (els.posMeaning) {
            els.posMeaning.textContent = "";
          }
          els.posMask.textContent = "";
          return;
        }
        const expectedWord = paragraphWordSurface(part.word);
        const posInfo = paragraphWordPosFor(paragraphChildIndex, revealed, expectedWord);
        const label = paragraphPosLabel(posInfo);
        els.posLabel.textContent = "";
        const labelText = document.createElement("span");
        labelText.textContent = label;
        const detail = document.createElement("small");
        const remainingMs = paragraphHintDeadline ? Math.max(0, paragraphHintDeadline - Date.now()) : 0;
        const meaningLive = Boolean(paragraphHintDeadline && remainingMs <= 5000);
        detail.textContent = meaningLive ? "5 giây cuối: mở nghĩa" : "gợi ý loại từ";
        els.posLabel.append(labelText, detail);
        if (els.posMeaning) {
          els.posMeaning.textContent = meaningLive
            ? paragraphMeaningHintFor(paragraphChildIndex, revealed, expectedWord, posInfo)
            : "";
        }
        els.posHint.classList.toggle("is-meaning-live", meaningLive && Boolean(els.posMeaning && els.posMeaning.textContent));
        const expected = currentParagraphWords();
        const partial = paragraphCurrentPartialWord(expected);
        const masked = typeof maskedWordHint === "function"
          ? maskedWordHint(expectedWord, partial)
          : Array.from(expectedWord).map((char, index) => partial[index] && partial[index].toLowerCase() === char.toLowerCase() ? char : "*").join("");
        renderParagraphPosMask(masked, expectedWord);
        paragraphPosHintKey = paragraphCurrentPosHintKey();
        els.posHint.classList.add("is-visible");
        positionParagraphPosHint();
      }

      function paragraphWordNoteFor(childIndex = 0, wordIndex = 0, word = "") {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        const child = children[Number(childIndex) || 0] || null;
        const notes = child && Array.isArray(child.word_notes) ? child.word_notes : [];
        if (!notes.length) {
          return null;
        }
        const wordKey = paragraphWordKey(word);
        const exact = notes.find((note) => {
          const noteIndex = Math.max(0, Math.floor(Number(note && note.index) || 0));
          return noteIndex === wordIndex && (!note.word || paragraphWordKey(note.word) === wordKey);
        });
        const fallback = exact || notes.find((note) => Math.max(0, Math.floor(Number(note && note.index) || 0)) === wordIndex)
          || notes.find((note) => note && note.word && paragraphWordKey(note.word) === wordKey);
        if (!fallback) {
          return null;
        }
        const meaning = preserveQuestionText(fallback.meaning_note || fallback.meaningNote || fallback.meaning || fallback.m || "");
        const grammar = preserveQuestionText(fallback.grammar_note || fallback.grammarNote || fallback.grammar || fallback.g || "");
        if (!meaning && !grammar) {
          return null;
        }
        return {
          word: clean(fallback.word || word),
          meaning,
          grammar,
        };
      }

      function clearParagraphWordNoteTimers() {
        paragraphWordNoteTimers.forEach((timer) => window.clearTimeout(timer));
        paragraphWordNoteTimers = [];
      }

      function typeParagraphWordNoteText(target, text = "") {
        if (!target) {
          return;
        }
        const value = preserveQuestionText(text) || "No note has been added for this side yet.";
        target.textContent = "";
        target.classList.add("is-typing");
        const chars = Array.from(value);
        const step = () => {
          if (!chars.length) {
            target.classList.remove("is-typing");
            return;
          }
          target.textContent += chars.shift();
          target.scrollTop = target.scrollHeight;
          paragraphWordNoteTimers.push(window.setTimeout(step, Math.max(7, value.length > 220 ? 5 : 12)));
        };
        step();
      }

      function closeParagraphWordNotes() {
        clearParagraphWordNoteTimers();
        if (!paragraphEls || !paragraphEls.wordNotes) {
          return;
        }
        paragraphEls.wordNotes.classList.add("is-hidden");
        paragraphEls.wordNotes.setAttribute("aria-hidden", "true");
        positionParagraphPosHint();
      }

      function paragraphSidePanelMetrics() {
        const els = paragraphEls || ensureParagraphRuntime();
        if (!els.card || !els.card.getBoundingClientRect) {
          return null;
        }
        const rect = els.card.getBoundingClientRect();
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1280;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;
        const bottomReserve = Math.min(220, Math.max(120, viewportHeight * 0.22));
        const top = Math.max(72, Math.min(rect.top + 12, viewportHeight - bottomReserve - 144));
        const height = Math.max(132, Math.min(rect.height - 24, viewportHeight - top - bottomReserve));
        const targetWidth = viewportWidth * 0.12;
        const width = Math.max(72, targetWidth);
        const sideMargin = Math.max(5, viewportWidth * 0.01);
        const left = sideMargin;
        const right = sideMargin;
        return { top, height, width, left, right, viewportHeight, bottomReserve };
      }

      function positionParagraphWordNotes() {
        const els = ensureParagraphRuntime();
        if (!els.card || !els.wordNotes || els.wordNotes.classList.contains("is-hidden")) {
          positionParagraphPosHint();
          return;
        }
        const metrics = paragraphSidePanelMetrics();
        if (!metrics) {
          return;
        }
        const { top, height, width, left, right } = metrics;
        els.wordNotes.style.setProperty("--paragraph-note-top", `${Math.round(top)}px`);
        els.wordNotes.style.setProperty("--paragraph-note-height", `${Math.round(height)}px`);
        els.wordNotes.style.setProperty("--paragraph-note-width", `${Math.round(width)}px`);
        els.wordNotes.style.setProperty("--paragraph-note-left", `${Math.round(left)}px`);
        els.wordNotes.style.setProperty("--paragraph-note-right", `${Math.round(right)}px`);
        positionParagraphPosHint();
      }

      function positionParagraphPosHint() {
        const els = paragraphEls;
        if (!els || !els.posHint || !els.card || !els.posHint.classList.contains("is-visible")) {
          return;
        }
        if (window.getComputedStyle(els.posHint).position !== "fixed") {
          return;
        }
        const metrics = paragraphSidePanelMetrics();
        if (!metrics) {
          return;
        }
        let top = metrics.top;
        let maxHeight = Math.max(104, Math.min(260, metrics.height));
        if (els.wordNotes && !els.wordNotes.classList.contains("is-hidden")) {
          const leftNote = els.wordNotes.querySelector(".ft-paragraph-word-note.is-left");
          if (leftNote && leftNote.getBoundingClientRect) {
            const noteRect = leftNote.getBoundingClientRect();
            const nextTop = noteRect.bottom + 10;
            const limit = metrics.viewportHeight - metrics.bottomReserve - 8;
            top = Math.min(Math.max(metrics.top, nextTop), Math.max(metrics.top, limit - 104));
            maxHeight = Math.max(88, Math.min(220, limit - top));
          }
        }
        els.posHint.style.setProperty("--paragraph-pos-top", `${Math.round(top)}px`);
        els.posHint.style.setProperty("--paragraph-pos-left", `${Math.round(metrics.left)}px`);
        els.posHint.style.setProperty("--paragraph-pos-width", `${Math.round(metrics.width)}px`);
        els.posHint.style.setProperty("--paragraph-pos-max-height", `${Math.round(maxHeight)}px`);
      }

      function openParagraphWordNotesForToken(token) {
        const els = ensureParagraphRuntime();
        const childIndex = Number(token && token.dataset ? token.dataset.child : 0) || 0;
        const wordIndex = Number(token && token.dataset ? token.dataset.word : 0) || 0;
        const note = paragraphWordNoteFor(childIndex, wordIndex, token ? token.textContent : "");
        if (!note) {
          closeParagraphWordNotes();
          return;
        }
        clearParagraphWordNoteTimers();
        if (els.wordNoteTitleLeft) {
          els.wordNoteTitleLeft.textContent = note.word || clean(token.textContent);
        }
        if (els.wordNoteTitleRight) {
          els.wordNoteTitleRight.textContent = note.word || clean(token.textContent);
        }
        if (els.wordNotes) {
          els.wordNotes.classList.remove("is-hidden");
          els.wordNotes.setAttribute("aria-hidden", "false");
        }
        positionParagraphWordNotes();
        positionParagraphPosHint();
        typeParagraphWordNoteText(els.wordNoteMeaning, note.meaning);
        typeParagraphWordNoteText(els.wordNoteGrammar, note.grammar);
      }

      function openParagraphWordNotesForIndex(childIndex = paragraphChildIndex, wordIndex = 0) {
        const token = paragraphTokenNode(childIndex, wordIndex);
        if (!token || !token.classList.contains("is-revealed") || !token.classList.contains("has-word-note")) {
          return false;
        }
        openParagraphWordNotesForToken(token);
        return true;
      }

      function handleParagraphWordNoteClick(event) {
        if (handleSpaceLUnlockChoiceClick(event)) {
          return;
        }
        const token = event.target && event.target.closest ? event.target.closest(".ft-paragraph-token") : null;
        if (!token || !token.classList.contains("is-revealed")) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        const childIndex = Number(token.dataset.child || 0) || 0;
        const wordIndex = Number(token.dataset.word || 0) || 0;
        playParagraphWordAudio(childIndex, wordIndex, token.textContent);
        if (!token.classList.contains("has-word-note")) {
          closeParagraphWordNotes();
          return;
        }
        openParagraphWordNotesForToken(token);
      }

      function paragraphHintKeyFor(wordIndex, childIndex = paragraphChildIndex) {
        return `${paragraphNodeIndex}:${childIndex}:${wordIndex}`;
      }

      function paragraphSelfTypedStats() {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        let total = 0;
        let revealed = 0;
        let typed = 0;
        let hinted = 0;
        children.forEach((child, childIndex) => {
          const count = paragraphWordParts(child && child.text ? child.text : "").map((part) => paragraphWordKey(part.word)).filter(Boolean).length;
          const childRevealed = Math.max(0, Math.min(count, Number(paragraphRevealed[childIndex] || 0) || 0));
          total += count;
          revealed += childRevealed;
          for (let index = 0; index < childRevealed; index += 1) {
            if (paragraphHints.has(paragraphHintKeyFor(index, childIndex))) {
              hinted += 1;
            } else {
              typed += 1;
            }
          }
        });
        const wrong = Math.max(0, Math.min(Number(paragraphWrongTokenCount || 0) || 0, Math.max(0, total - typed - hinted)));
        const pct = (value) => total ? Math.max(0, Math.min(100, Math.round((value / total) * 100))) : 0;
        return {
          typed,
          hinted,
          wrong,
          revealed,
          total,
          typedPct: pct(typed),
          hintedPct: pct(hinted),
          wrongPct: pct(wrong),
        };
      }

      function updateParagraphSelfMeter() {
        if (!paragraphEls || !paragraphEls.selfChart) {
          return;
        }
        const stats = paragraphSelfTypedStats();
        const typedEnd = stats.total ? (stats.typed / stats.total) * 360 : 0;
        const hintEnd = stats.total ? ((stats.typed + stats.hinted) / stats.total) * 360 : 0;
        const wrongEnd = stats.total ? ((stats.typed + stats.hinted + stats.wrong) / stats.total) * 360 : 0;
        paragraphEls.selfChart.style.setProperty("--paragraph-typed-end", `${typedEnd}deg`);
        paragraphEls.selfChart.style.setProperty("--paragraph-hint-end", `${hintEnd}deg`);
        paragraphEls.selfChart.style.setProperty("--paragraph-wrong-end", `${wrongEnd}deg`);
        if (paragraphEls.selfTotal) {
          paragraphEls.selfTotal.textContent = `${stats.typed + stats.hinted + stats.wrong}/${stats.total}`;
        }
        if (paragraphEls.typedStat) {
          paragraphEls.typedStat.textContent = `${stats.typedPct}%`;
          paragraphEls.typedStat.title = `${stats.typed}/${stats.total}`;
        }
        if (paragraphEls.hintStat) {
          paragraphEls.hintStat.textContent = `${stats.hintedPct}%`;
          paragraphEls.hintStat.title = `${stats.hinted}/${stats.total}`;
        }
        if (paragraphEls.wrongStat) {
          paragraphEls.wrongStat.textContent = `${stats.wrongPct}%`;
          paragraphEls.wrongStat.title = `${stats.wrong}/${stats.total}`;
        }
        paragraphEls.clock && paragraphEls.clock.classList.toggle("has-hinted-token", stats.hinted > 0);
        paragraphEls.clock && paragraphEls.clock.classList.toggle("has-wrong-token", stats.wrong > 0);
      }

      function paragraphHintSeconds() {
        return Math.max(3, Math.min(300, Number(paragraphHintIdleSeconds) || Number(paragraphPayload && paragraphPayload.hint_seconds) || (DEFAULT_WORD_HINT_IDLE_MS / 1000)));
      }

      function updateParagraphHintCountdown() {
        if (!paragraphEls || !paragraphEls.clock) {
          return;
        }
        const seconds = paragraphHintSeconds();
        const now = Date.now();
        const remainingMs = paragraphHintDeadline ? Math.max(0, paragraphHintDeadline - now) : 0;
        const remainingSeconds = paragraphHintDeadline ? Math.ceil(remainingMs / 1000) : 0;
        const ratio = paragraphHintDeadline ? Math.max(0, Math.min(1, remainingMs / Math.max(1, seconds * 1000))) : 0;
        paragraphEls.clock.style.setProperty("--paragraph-hint-ratio", String(ratio));
        if (isSpaceSpeechPayload()) {
          paragraphEls.clockTime.textContent = "PLAY";
          paragraphEls.clockMeta.textContent = "AUDIO";
          return;
        }
        paragraphEls.clockTime.textContent = paragraphHintDeadline ? `${remainingSeconds}s` : "--";
        paragraphEls.clockMeta.textContent = paragraphHintDeadline ? "NEXT WORD" : "STANDBY";
        if (
          paragraphEls.posHint &&
          paragraphEls.posHint.classList.contains("is-visible") &&
          paragraphPosHintKey === paragraphCurrentPosHintKey()
        ) {
          updateParagraphPosHint(true);
        }
      }

      function paragraphExplanationItems(child = currentParagraphChild()) {
        const items = child && Array.isArray(child.explanations) ? child.explanations : [];
        return items
          .map((item, index) => {
            const source = item && typeof item === "object" ? item : { text: item };
            return {
              title: clean(source.title || source.t || `Guide Node ${index + 1}`),
              text: clean(source.text || source.body || source.b || source.content || source.value || ""),
            };
          })
          .filter((item) => item.title || item.text);
      }

      function updateParagraphExplanationButton() {
        const els = ensureParagraphRuntime();
        const count = paragraphExplanationItems().length;
        if (els.guideCount) {
          els.guideCount.textContent = String(count);
        }
        if (els.guide) {
          els.guide.classList.toggle("has-guides", count > 0);
          els.guide.title = count > 0 ? `Open ${count} guide node${count === 1 ? "" : "s"}` : "Open guidance";
        }
      }

      function paragraphTokenHelperUsedForCurrent(childIndex = paragraphChildIndex) {
        return paragraphTokenHelperUsedKeys.has(paragraphSegmentSupportKey(childIndex));
      }

      function paragraphTokenHelperPausesReward() {
        const mode = paragraphSpaceMode();
        return mode !== "space_p" && mode !== "space_l";
      }

      function paragraphCurrentRewardConfig(variant = paragraphBowRewardVariant()) {
        if (isSpaceLPayload()) {
          return paragraphSwordRewardConfig(variant);
        }
        if (isSpaceSPayload()) {
          return paragraphSaxRewardConfig(variant);
        }
        return paragraphBowRewardConfig(variant);
      }

      function updateParagraphRewardPreview() {
        if (!paragraphEls || !paragraphEls.rewardPreview) {
          return;
        }
        const reward = paragraphCurrentRewardConfig();
        const usedHelper = paragraphTokenHelperPausesReward() && paragraphTokenHelperUsedForCurrent();
        const rewardId = clean(reward && reward.id);
        paragraphEls.rewardPreview.classList.toggle("is-gold", !rewardId.includes("_silver"));
        paragraphEls.rewardPreview.classList.toggle("is-silver", rewardId.includes("_silver"));
        paragraphEls.rewardPreview.classList.toggle("is-space-p", paragraphSpaceMode() === "space_p");
        paragraphEls.rewardPreview.classList.toggle("is-space-s", isSpaceSPayload());
        paragraphEls.rewardPreview.classList.toggle("is-space-l", isSpaceLPayload());
        paragraphEls.rewardPreview.classList.toggle("is-used", usedHelper);
        paragraphEls.rewardPreview.hidden = false;
        paragraphEls.rewardPreview.setAttribute("aria-hidden", "false");
        paragraphEls.rewardPreview.title = isSpaceRewardPlaybackPayload()
          ? `${reward.name}: click to play, right click to set voice speed`
          : `${reward.name}: click for token support`;
        syncSpaceSRewardSpeedBadge();
        if (paragraphEls.rewardTitle) {
          paragraphEls.rewardTitle.textContent = reward.name;
        }
        if (paragraphEls.rewardState) {
          paragraphEls.rewardState.textContent = usedHelper
            ? "Token support used: reward paused"
            : `${paragraphModeLabel()} reward without token support`;
        }
      }

      function closeParagraphTokenHelper() {
        if (!paragraphEls || !paragraphEls.tokenHelper) {
          return;
        }
        paragraphEls.tokenHelper.classList.add("is-hidden");
        paragraphEls.tokenHelper.setAttribute("aria-hidden", "true");
      }

      function positionParagraphTokenHelper() {
        if (!paragraphEls || !paragraphEls.card || !paragraphEls.tokenHelper || paragraphEls.tokenHelper.classList.contains("is-hidden")) {
          return;
        }
        const cardRect = paragraphEls.card.getBoundingClientRect();
        const viewportWidth = Math.max(320, window.innerWidth || document.documentElement.clientWidth || 0);
        const viewportHeight = Math.max(320, window.innerHeight || document.documentElement.clientHeight || 0);
        const edgeGap = 5;
        const left = Math.max(cardRect.right + edgeGap, edgeGap);
        const availableWidth = viewportWidth - left - edgeGap;
        const width = Math.max(0, availableWidth);
        const isCramped = availableWidth < 220;
        const top = Math.min(
          Math.max(cardRect.top + 14, edgeGap),
          Math.max(edgeGap, viewportHeight - 180)
        );
        paragraphEls.tokenHelper.classList.toggle("is-cramped", isCramped);
        paragraphEls.tokenHelper.style.width = `${Math.round(width)}px`;
        paragraphEls.tokenHelper.style.left = `${Math.round(left)}px`;
        paragraphEls.tokenHelper.style.top = `${Math.round(top)}px`;
        paragraphEls.tokenHelper.style.maxHeight = `${Math.max(220, Math.round(viewportHeight - top - edgeGap))}px`;
      }

      function markParagraphTokenHelperUsed() {
        if (!paragraphTokenHelperPausesReward()) {
          updateParagraphRewardPreview();
          return;
        }
        paragraphTokenHelperUsedKeys.add(paragraphSegmentSupportKey());
        updateParagraphRewardPreview();
      }

      function playParagraphRewardShotAnimation() {
        if (!paragraphEls || !paragraphEls.rewardPreview) {
          return;
        }
        const card = paragraphEls.rewardPreview;
        const mode = paragraphSpaceMode();
        const animationClass = mode === "space_s" ? "is-feathering" : (mode === "space_l" ? "is-slashing" : (mode === "space_p" ? "is-firing" : ""));
        if (!animationClass) {
          return;
        }
        card.classList.remove("is-firing", "is-slashing", "is-feathering");
        void card.offsetWidth;
        card.classList.add(animationClass);
        window.clearTimeout(card._paragraphRewardShotTimer);
        card._paragraphRewardShotTimer = window.setTimeout(() => {
          card.classList.remove(animationClass);
        }, animationClass === "is-feathering" ? 1680 : 980);
      }

      function appendParagraphTokenHelperWord(word = "", wordIndex = -1) {
        const els = ensureParagraphRuntime();
        if (!els.input) {
          return;
        }
        markParagraphTokenHelperUsed();
        if (isSpaceLPayload() && wordIndex >= 0) {
          const key = spaceLTokenKey(paragraphChildIndex, wordIndex);
          if (!spaceLUnlockedTokenKeys.has(key)) {
            spaceLUnlockedTokenKeys.add(key);
            spaceLUnlockChoiceAvailable = false;
            syncParagraphTokenClasses();
            renderSpaceSSideCards(spaceSLastReadScore);
            updateParagraphProgress();
            queueParagraphProgressSave(120);
          }
        }
        const value = String(els.input.value || "");
        const prefix = value && !/\s$/.test(value) ? `${value} ` : value;
        els.input.value = `${prefix}${clean(word)} `;
        els.input.focus({ preventScroll: true });
        syncParagraphInput({ type: "input" });
      }

      function openParagraphTokenHelper() {
        const els = ensureParagraphRuntime();
        if (isSpaceSPayload() || !els.tokenHelper || !els.tokenHelperGrid) {
          return false;
        }
        const support = paragraphCurrentSupportTokenItems(5);
        const tokens = support.tokens;
        if (!tokens.length) {
          return false;
        }
        closeParagraphExplanationPopup();
        markParagraphTokenHelperUsed();
        playParagraphRewardShotAnimation();
        if (els.tokenHelperNote) {
          const tokenNote = support.limited
            ? `Showing 5 random upcoming tokens from ${support.remaining} untyped words.`
            : "Showing the remaining upcoming tokens.";
          els.tokenHelperNote.textContent = paragraphTokenHelperPausesReward()
            ? `${tokenNote} Using this support pauses this segment reward.`
            : (isSpaceLPayload()
              ? `${tokenNote} Space_L keeps this segment reward.`
              : `${tokenNote} Space_P keeps this segment reward.`);
        }
        els.tokenHelperGrid.textContent = "";
        tokens.forEach((token, index) => {
          const label = clean(token && typeof token === "object" ? token.label : token);
          const rawWordIndex = token && typeof token === "object" ? Number(token.wordIndex) : -1;
          const wordIndex = Number.isFinite(rawWordIndex) ? Math.max(-1, Math.floor(rawWordIndex)) : -1;
          if (!label) {
            return;
          }
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "ft-paragraph-token-helper-chip";
          chip.style.setProperty("--token-helper-order", String(index));
          chip.textContent = label;
          chip.addEventListener("click", () => appendParagraphTokenHelperWord(label, wordIndex));
          els.tokenHelperGrid.appendChild(chip);
        });
        els.tokenHelper.classList.remove("is-hidden");
        els.tokenHelper.setAttribute("aria-hidden", "false");
        positionParagraphTokenHelper();
        requestAnimationFrame(positionParagraphTokenHelper);
        if (els.status) {
          els.status.textContent = paragraphTokenHelperPausesReward()
            ? "Token support opened. This segment reward is paused."
            : (isSpaceLPayload()
              ? "Token support opened. Space_L reward stays available."
              : "Token support opened. Space_P reward stays available.");
        }
        return true;
      }

      function renderParagraphExplanationPopup() {
        const els = ensureParagraphRuntime();
        const items = paragraphExplanationItems();
        const total = items.length;
        if (!total) {
          els.explainTitle.textContent = "No guide nodes";
          els.explainBody.textContent = "This segment does not have explanation nodes yet.";
          els.explainIndex.textContent = "0 / 0";
          els.explainPrev.disabled = true;
          els.explainNext.disabled = true;
          return;
        }
        paragraphExplanationIndex = Math.max(0, Math.min(total - 1, Number(paragraphExplanationIndex) || 0));
        const item = items[paragraphExplanationIndex] || items[0];
        els.explainTitle.textContent = item.title || `Guide Node ${paragraphExplanationIndex + 1}`;
        els.explainBody.textContent = item.text || "No explanation text.";
        els.explainIndex.textContent = `${paragraphExplanationIndex + 1} / ${total}`;
        els.explainPrev.disabled = paragraphExplanationIndex <= 0;
        els.explainNext.disabled = paragraphExplanationIndex >= total - 1;
      }

      function openParagraphExplanationPopup() {
        const els = ensureParagraphRuntime();
        closeParagraphTokenHelper();
        renderParagraphExplanationPopup();
        els.explainLayer.classList.remove("is-hidden");
      }

      function closeParagraphExplanationPopup() {
        if (paragraphEls && paragraphEls.explainLayer) {
          paragraphEls.explainLayer.classList.add("is-hidden");
        }
      }

      function syncParagraphInputGhost(kind = "") {
        const els = ensureParagraphRuntime();
        const ghost = els.inputGhost;
        const input = els.input;
        if (!ghost || !input) {
          return null;
        }
        const safeKind = typeof kind === "string" && (kind === "good" || kind === "wrong" || kind === "typing") ? kind : "";
        const raw = String(input.value || "");
        const selectionEnd = Number(input.selectionEnd ?? raw.length);
        const inputFocused = document.activeElement === input;
        if (isSpaceSpeechPayload() && isSpaceSListeningActive(els) && (!inputFocused || selectionEnd >= raw.length)) {
          queueParagraphInputTailFollow({ forceSelectionEnd: true });
        }
        const shouldFollowTail = Boolean(
          raw
          && selectionEnd >= raw.length
          && (inputFocused || isSpaceSpeechPayload())
        );
        if (shouldFollowTail && input.scrollWidth > input.clientWidth + 2) {
          try {
            input.scrollLeft = input.scrollWidth;
          } catch (error) {
          }
        }
        ghost.style.setProperty("--paragraph-input-scroll", `${-(Number(input.scrollLeft || 0) || 0)}px`);
        ghost.textContent = "";
        if (!raw) {
          try {
            input.scrollLeft = 0;
          } catch (error) {
          }
          ghost.style.setProperty("--paragraph-input-scroll", "0px");
          return null;
        }
        const match = raw.match(/^([\s\S]*?)(\S+)(\s*)$/);
        if (!match) {
          ghost.textContent = raw;
          return null;
        }
        const beforeText = match[1] || "";
        const lastText = match[2] || "";
        const afterText = match[3] || "";
        if (beforeText) {
          const before = document.createElement("span");
          before.textContent = beforeText;
          ghost.appendChild(before);
        }
        const last = document.createElement("span");
        last.className = "ft-paragraph-input-last";
        if (safeKind) {
          last.classList.add(`is-${safeKind}`);
        }
        last.textContent = lastText;
        ghost.appendChild(last);
        if (afterText) {
          const after = document.createElement("span");
          after.textContent = afterText;
          ghost.appendChild(after);
        }
        return last;
      }

      function pulseParagraphInput(kind = "typing") {
        const els = ensureParagraphRuntime();
        const marker = syncParagraphInputGhost(kind);
        if (!marker) {
          return;
        }
        if (paragraphInputPulseTimer) {
          window.clearTimeout(paragraphInputPulseTimer);
          paragraphInputPulseTimer = 0;
        }
        const safeKind = kind === "good" || kind === "wrong" ? kind : "typing";
        marker.classList.remove("is-typing", "is-good", "is-wrong");
        void marker.offsetWidth;
        marker.classList.add(`is-${safeKind}`);
        paragraphInputPulseTimer = window.setTimeout(() => {
          marker.classList.remove("is-typing", "is-good", "is-wrong");
          paragraphInputPulseTimer = 0;
        }, safeKind === "good" ? 820 : 640);
      }

      function paragraphTotalSegments() {
        return paragraphNodes.reduce((sum, node) => sum + (Array.isArray(node.children) ? node.children.length : 0), 0);
      }

      function paragraphTokenCountForChild(child = {}) {
        return paragraphWordParts(child && child.text ? child.text : "")
          .map((part) => paragraphWordKey(part.word))
          .filter(Boolean)
          .length;
      }

      function paragraphTotalTokens() {
        return paragraphNodes.reduce((sum, node) => {
          const children = node && Array.isArray(node.children) ? node.children : [];
          return sum + children.reduce((childSum, child) => childSum + paragraphTokenCountForChild(child), 0);
        }, 0);
      }

      function paragraphCompletedTokensForSnapshot() {
        let done = 0;
        const speechMode = isSpaceSpeechPayload();
        const currentSpeechSegmentPassed = speechMode && spaceSLastReadScore >= SPACE_S_PASS_SCORE;
        paragraphNodes.forEach((node, nodeIndex) => {
          const children = node && Array.isArray(node.children) ? node.children : [];
          children.forEach((child, childIndex) => {
            const count = paragraphTokenCountForChild(child);
            if (nodeIndex < paragraphNodeIndex) {
              done += count;
            } else if (nodeIndex === paragraphNodeIndex) {
              if (childIndex < paragraphChildIndex) {
                done += count;
              } else if (childIndex === paragraphChildIndex) {
                // Space_S/L reveal the current sentence for speaking/listening guidance.
                // Visible words are not completed progress until the speech score passes.
                done += speechMode
                  ? (currentSpeechSegmentPassed ? count : 0)
                  : Math.max(0, Math.min(count, Number(paragraphRevealed[childIndex] || 0) || 0));
              }
            }
          });
        });
        return done;
      }

      function paragraphCompletedSegments() {
        let done = 0;
        paragraphNodes.forEach((node, nodeIndex) => {
          const children = Array.isArray(node.children) ? node.children : [];
          if (nodeIndex < paragraphNodeIndex) {
            done += children.length;
          } else if (nodeIndex === paragraphNodeIndex) {
            done += Math.min(paragraphChildIndex, children.length);
          }
        });
        return done;
      }

      function updateParagraphProgress() {
        const els = ensureParagraphRuntime();
        const total = Math.max(1, paragraphTotalSegments());
        const childWords = currentParagraphWords();
        const wordRatio = childWords.length ? Math.min(1, (paragraphRevealed[paragraphChildIndex] || 0) / childWords.length) : 0;
        const done = paragraphCompletedSegments() + wordRatio;
        const percent = Math.max(0, Math.min(100, Math.round((done / total) * 100)));
        els.progress.style.setProperty("--paragraph-progress", `${percent}%`);
        updateParagraphSelfMeter();
      }

      function renderParagraphCard() {
        const els = ensureParagraphRuntime();
        const node = currentParagraphNode();
        if (!node) {
          return;
        }
        closeParagraphWordNotes();
        els.title.textContent = node.title || `Paragraph Node ${paragraphNodeIndex + 1}`;
        els.text.textContent = "";
        const children = Array.isArray(node.children) ? node.children : [];
        const appendParagraphPunctuation = (value, childIndex, wordIndex, kind = "punct") => {
          if (!value) {
            return;
          }
          const punct = document.createElement("span");
          punct.className = `ft-paragraph-punct is-${kind}`;
          punct.dataset.child = String(childIndex);
          punct.dataset.word = String(wordIndex);
          punct.textContent = value;
          els.text.appendChild(punct);
        };
        children.forEach((child, childIndex) => {
          paragraphWordParts(child.text).forEach((part, wordIndex) => {
            const pieces = paragraphDisplayWordPieces(part.word);
            appendParagraphPunctuation(pieces.prefix, childIndex, wordIndex, "prefix");
            if (pieces.word) {
              const span = document.createElement("span");
              span.className = "ft-paragraph-token";
              span.dataset.child = String(childIndex);
              span.dataset.word = String(wordIndex);
              span.dataset.rawWord = part.word;
              span.textContent = pieces.word;
              const tag = document.createElement("span");
              tag.className = "ft-paragraph-token-tag";
              tag.setAttribute("aria-hidden", "true");
              span.appendChild(tag);
              els.text.appendChild(span);
            }
            appendParagraphPunctuation(pieces.suffix, childIndex, wordIndex, "suffix");
            if (part.space) {
              const space = document.createElement("span");
              space.className = "ft-paragraph-space";
              space.textContent = part.space;
              els.text.appendChild(space);
            }
          });
        });
        syncParagraphTokenClasses();
        updateParagraphProgress();
      }

      function syncParagraphTokenClasses() {
        const els = ensureParagraphRuntime();
        const child = currentParagraphChild();
        const speakingMode = isSpaceSpeechPayload();
        const hiddenListeningMode = isSpaceLPayload();
        if (els.root) {
          els.root.classList.toggle("is-space-l-choice-active", Boolean(hiddenListeningMode && spaceLUnlockChoiceAvailable));
        }
        let spaceSCurrentIndex = 0;
        if (speakingMode && child) {
          const parts = paragraphWordParts(child.text);
          const currentUnlocks = hiddenListeningMode ? spaceLUnlockedIndexesForChild(paragraphChildIndex) : null;
          spaceSCurrentIndex = parts.findIndex((_part, index) => (
            hiddenListeningMode
              ? !(currentUnlocks && currentUnlocks.has(index))
              : !spaceSMatchedTokenKeys.has(spaceSTokenKey(paragraphChildIndex, index))
          ));
          if (spaceSCurrentIndex < 0) {
            spaceSCurrentIndex = Math.max(0, parts.length - 1);
          }
        }
        els.text.querySelectorAll(".ft-paragraph-token").forEach((token) => {
          const childIndex = Number(token.dataset.child || 0) || 0;
          const wordIndex = Number(token.dataset.word || 0) || 0;
          const revealed = Number(paragraphRevealed[childIndex] || 0) || 0;
          const hintKey = paragraphHintKeyFor(wordIndex, childIndex);
          const spaceSMatched = speakingMode && spaceSMatchedTokenKeys.has(spaceSTokenKey(childIndex, wordIndex));
          const spaceLUnlocked = hiddenListeningMode && isSpaceLTokenUnlocked(childIndex, wordIndex);
          const spaceLHasAttempt = hiddenListeningMode && childIndex === paragraphChildIndex && Boolean(paragraphEls && paragraphEls.input && String(paragraphEls.input.value || "").trim());
          const spaceLHidden = hiddenListeningMode && childIndex === paragraphChildIndex && child && !spaceLUnlocked;
          const spaceLMissed = hiddenListeningMode && childIndex === paragraphChildIndex && spaceLUnlocked && spaceLHasAttempt && !spaceSMatched;
          const spaceLChoice = hiddenListeningMode && spaceLUnlockChoiceAvailable && childIndex === paragraphChildIndex && !spaceLUnlocked;
          token.classList.toggle("is-revealed", wordIndex < revealed);
          token.classList.toggle("is-active-segment", childIndex === paragraphChildIndex);
          token.classList.toggle("is-current", childIndex === paragraphChildIndex && (speakingMode ? wordIndex === spaceSCurrentIndex : wordIndex === revealed) && child);
          token.classList.toggle("is-space-s-matched", spaceSMatched);
          token.classList.toggle("is-space-l-unlocked", Boolean(spaceLUnlocked));
          token.classList.toggle("is-space-l-hidden", Boolean(spaceLHidden));
          token.classList.toggle("is-space-l-missed", Boolean(spaceLMissed));
          token.classList.toggle("is-space-l-choice", Boolean(spaceLChoice));
          token.classList.toggle("is-hinted", paragraphHints.has(hintKey));
          token.classList.toggle("has-word-note", wordIndex < revealed && Boolean(paragraphWordNoteFor(childIndex, wordIndex, token.textContent)));
        });
        els.text.querySelectorAll(".ft-paragraph-punct").forEach((punct) => {
          const childIndex = Number(punct.dataset.child || 0) || 0;
          const wordIndex = Number(punct.dataset.word || 0) || 0;
          const revealed = Number(paragraphRevealed[childIndex] || 0) || 0;
          const hintKey = paragraphHintKeyFor(wordIndex, childIndex);
          const spaceSMatched = speakingMode && spaceSMatchedTokenKeys.has(spaceSTokenKey(childIndex, wordIndex));
          const spaceLUnlocked = hiddenListeningMode && isSpaceLTokenUnlocked(childIndex, wordIndex);
          const spaceLHidden = hiddenListeningMode && childIndex === paragraphChildIndex && child && !spaceLUnlocked;
          const spaceLChoice = hiddenListeningMode && spaceLUnlockChoiceAvailable && childIndex === paragraphChildIndex && !spaceLUnlocked;
          punct.classList.toggle("is-revealed", wordIndex < revealed);
          punct.classList.toggle("is-active-segment", childIndex === paragraphChildIndex);
          punct.classList.toggle("is-space-l-hidden", Boolean(spaceLHidden));
          punct.classList.toggle("is-space-l-choice", Boolean(spaceLChoice));
          punct.classList.toggle("is-hinted", paragraphHints.has(hintKey));
        });
        if (els.phoneticText) {
          els.phoneticText.querySelectorAll(".ft-space-s-phonetic-chip").forEach((chip) => {
            const childIndex = Number(chip.dataset.child || 0) || 0;
            const wordIndex = Number(chip.dataset.word || 0) || 0;
            const spaceSMatched = speakingMode && spaceSMatchedTokenKeys.has(spaceSTokenKey(childIndex, wordIndex));
            chip.classList.toggle("is-active-segment", childIndex === paragraphChildIndex);
            chip.classList.toggle("is-current", childIndex === paragraphChildIndex && wordIndex === spaceSCurrentIndex && child);
            chip.classList.toggle("is-space-s-matched", spaceSMatched);
          });
        }
      }

      function renderParagraphDock(message = "") {
        const els = ensureParagraphRuntime();
        const child = currentParagraphChild();
        paragraphCompleting = false;
        paragraphExplanationIndex = 0;
        paragraphWrongTokenCount = 0;
        paragraphWrongSoundKey = "";
        closeParagraphTokenHelper();
        if (!child) {
          els.meaning.textContent = "Mission complete.";
          els.input.value = "";
          syncParagraphInputGhost();
          els.input.disabled = true;
          els.next.disabled = true;
          els.status.textContent = "All paragraph segments are complete.";
          updateParagraphExplanationButton();
          updateParagraphHintCountdown();
          updateParagraphSelfMeter();
          updateParagraphRewardPreview();
          updateParagraphPosHint(false);
          return;
        }
        const speakingMode = isSpaceSpeechPayload();
        const listeningMode = isSpaceLPayload();
        if (els.root) {
          els.root.classList.toggle("is-space-s", speakingMode);
          els.root.classList.toggle("is-space-l", listeningMode);
        }
        els.meaning.textContent = listeningMode
          ? "Hear the hidden English sentence and rebuild it aloud."
          : (speakingMode ? "Read the visible English sentence aloud." : (child.meaning || "Translate this meaning back into English."));
        els.input.value = "";
        if (speakingMode) {
          stopSpaceSListeningSession({ finalizeAttempt: false });
          clearSpaceSUserAudio();
          spaceSMatchedTokenKeys = new Set();
          spaceLUnlockChoiceAvailable = false;
          spaceSFailedReadSessions = 0;
          spaceSManualInputUnlocked = false;
          spaceSReadSessionHasInput = false;
          spaceSReadSessionFinalized = false;
          spaceSLastReadScore = 0;
          setSpaceSRevealedForCurrentChild();
          syncParagraphTokenClasses();
        }
        syncParagraphInputGhost();
        renderSpaceSSideCards();
        els.input.disabled = false;
        els.next.disabled = true;
        syncSpaceSManualInputGate(0);
        updateSpaceSReplayButton();
        if (els.guide) {
          els.guide.hidden = false;
          els.guide.title = speakingMode ? "Hear model sentence" : "Open guidance";
        }
        if (els.clockTime) {
          els.clockTime.textContent = speakingMode ? "PLAY" : "--";
        }
        const clockStrong = els.guide ? els.guide.querySelector(".ft-paragraph-hint-meta strong") : null;
        if (clockStrong) {
          clockStrong.textContent = speakingMode ? "MODEL" : "AUTO HINT";
        }
        if (els.clockMeta && speakingMode) {
          els.clockMeta.textContent = "AUDIO";
        }
        els.status.textContent = message || (
          speakingMode
            ? (listeningMode
              ? "Press Ctrl to rebuild the hidden sentence. Alt plays the selected model voice. Typing unlocks after 2 low-score reads."
              : "Press Ctrl to read. Alt plays the selected model voice. Typing unlocks after 2 low-score reads.")
            : `Segment ${paragraphChildIndex + 1}/${(currentParagraphNode().children || []).length}`
        );
        updateParagraphExplanationButton();
        updateParagraphRewardPreview();
        updateParagraphPosHint(false);
        if (els.explainLayer && !els.explainLayer.classList.contains("is-hidden")) {
          renderParagraphExplanationPopup();
        }
        window.setTimeout(() => {
          try {
            els.input.focus({ preventScroll: true });
          } catch (error) {
          }
        }, 80);
        const playInitialParagraphAudio = () => {
          if (speakingMode) void playParagraphEnglishAudio(child);
          else playParagraphMeaningAudio(child);
        };
        if (typeof window.__ftRunAfterLessonEntryGateOpen === "function") window.__ftRunAfterLessonEntryGateOpen(playInitialParagraphAudio);
        else playInitialParagraphAudio();
      }

      async function playParagraphClip(clip, token, volume = 0.96, options = {}) {
        const asset = normalizeAudioClip(clip);
        if (!asset || token !== paragraphAudioToken || !paragraphModeActive) {
          return false;
        }
        try {
          return Boolean(await playAudioClipOnce(asset, {
            volume,
            playbackRate: options.playbackRate,
            onAudio: (audio, done) => {
              if (options.kind) {
                paragraphCurrentPlaybackKind = options.kind;
              }
              if (options.signature) {
                paragraphCurrentPlaybackSignature = options.signature;
              }
              paragraphActiveAudios.add({ audio, done });
              if (options.highlightChild) {
                startParagraphAudioHighlight(audio, options.highlightChild, clip, options.highlightChildIndex);
              }
            },
            onAudioDone: (audio) => {
              clearParagraphAudioHighlight(audio);
              Array.from(paragraphActiveAudios).forEach((entry) => {
                if ((entry && entry.audio) === audio || entry === audio) {
                  paragraphActiveAudios.delete(entry);
                }
              });
              if (!paragraphActiveAudios.size) {
                clearParagraphPlaybackMeta();
              }
            },
          }));
        } catch (error) {
          return false;
        }
      }

      function queuePendingParagraphAudio(clip, token, volume = 0.96, options = {}) {
        if (!clip || token !== paragraphAudioToken || !paragraphModeActive) {
          return;
        }
        paragraphPendingAudioRetry = { clip, token, volume, options };
      }

      function retryPendingParagraphAudio() {
        const pending = paragraphPendingAudioRetry;
        if (!pending || pending.token !== paragraphAudioToken || !paragraphModeActive) {
          paragraphPendingAudioRetry = null;
          return;
        }
        paragraphPendingAudioRetry = null;
        void playParagraphClip(pending.clip, pending.token, pending.volume, pending.options || {}).then((ok) => {
          if (!ok && pending.token === paragraphAudioToken && paragraphModeActive) {
            queuePendingParagraphAudio(pending.clip, pending.token, pending.volume, pending.options || {});
          }
        });
      }

      function playParagraphMeaningAudio(child = currentParagraphChild()) {
        const clip = child && (child.meaning_audio || child.vi_audio);
        if (!clip) {
          return;
        }
        paragraphAudioToken += 1;
        const token = paragraphAudioToken;
        paragraphPendingAudioRetry = null;
        void playParagraphClip(clip, token, 0.96).then((ok) => {
          if (!ok && token === paragraphAudioToken && paragraphModeActive && currentParagraphChild() === child) {
            queuePendingParagraphAudio(clip, token, 0.96);
          }
        });
      }

      async function playParagraphEnglishAudio(child = currentParagraphChild(), options = {}) {
        const explicitAlt = Object.prototype.hasOwnProperty.call(options || {}, "alt");
        const requestedMode = explicitAlt
          ? spaceSResolvedVoiceMode(options && options.alt ? "alt" : "main", child)
          : (isSpaceSpeechPayload() ? spaceSPreferredVoiceModeForChild(child) : "main");
        const clip = paragraphPlaybackClip(child, { ...options, alt: requestedMode === "alt" });
        if (!clip) {
          return false;
        }
        if (options && options.syncPreferred && isSpaceSpeechPayload()) {
          setSpaceSPreferredVoiceMode(requestedMode, { child });
        }
        const targetChildIndex = Math.max(0, Math.floor(Number(options.childIndex ?? paragraphChildIndex) || 0));
        const playbackRate = Math.max(0.35, Math.min(2, Number(options.playbackRate || options.rate || 1) || 1));
        const rateKey = playbackRate === 1 ? "normal" : `rate-${Math.round(playbackRate * 100)}`;
        const signature = `${Math.max(0, Number(paragraphNodeIndex || 0) || 0)}:${targetChildIndex}:${requestedMode}:${rateKey}`;
        if (paragraphCurrentPlaybackKind === "model" && paragraphCurrentPlaybackSignature === signature && paragraphActiveAudios.size) {
          stopParagraphAudioPlayback();
          const els = ensureParagraphRuntime();
          if (els.status && isSpaceSpeechPayload()) {
            els.status.textContent = `${spaceSVoiceModeLabel(requestedMode, child)} stopped.`;
          }
          return false;
        }
        stopSpaceSListeningSession({ finalizeAttempt: true });
        stopSpaceSReplayAudio();
        stopParagraphAudioPlayback();
        if (options && options.centerCurrent && isSpaceSpeechPayload()) {
          centerParagraphFocusInViewport(targetChildIndex);
        }
        paragraphAudioToken += 1;
        const token = paragraphAudioToken;
        paragraphPendingAudioRetry = null;
        return playParagraphClip(clip, token, 0.98, {
          kind: "model",
          signature,
          playbackRate,
          highlightChild: isSpaceSpeechPayload() ? child : null,
          highlightChildIndex: targetChildIndex,
        });
      }

      function playParagraphWordAudio(childIndex = paragraphChildIndex, wordIndex = 0, word = "", delayMs = 0) {
        const clip = paragraphWordAudioFor(childIndex, wordIndex, word);
        if (!clip) {
          return false;
        }
        const scheduleToken = paragraphAudioToken;
        const run = () => {
          if (!paragraphModeActive || scheduleToken !== paragraphAudioToken) {
            return;
          }
          paragraphAudioToken += 1;
          const token = paragraphAudioToken;
          paragraphPendingAudioRetry = null;
          void playParagraphClip(clip, token, 0.94);
        };
        if (delayMs > 0) {
          const timer = window.setTimeout(() => {
            paragraphWordAudioTimers = paragraphWordAudioTimers.filter((item) => item !== timer);
            run();
          }, delayMs);
          paragraphWordAudioTimers.push(timer);
        } else {
          run();
        }
        return true;
      }

      function scheduleParagraphHint() {
        if (isSpaceSpeechPayload()) {
          clearParagraphHintTimer();
          return;
        }
        const keepPos = Boolean(paragraphPosHintKey && paragraphPosHintKey === paragraphCurrentPosHintKey());
        clearParagraphHintTimer({ keepPos });
        if (paragraphHintPausedAfterAutoUnlock) {
          updateParagraphHintCountdown();
          return;
        }
        if (!paragraphModeActive || !currentParagraphChild()) {
          updateParagraphHintCountdown();
          return;
        }
        const expected = currentParagraphWords();
        const revealed = Number(paragraphRevealed[paragraphChildIndex] || 0) || 0;
        if (!expected.length || revealed >= expected.length) {
          updateParagraphHintCountdown();
          return;
        }
        const seconds = paragraphHintSeconds();
        paragraphHintDeadline = Date.now() + (seconds * 1000);
        updateParagraphHintCountdown();
        if (keepPos) {
          updateParagraphPosHint(true);
        } else if (seconds > 5) {
          paragraphPosHintTimer = window.setTimeout(() => {
            paragraphPosHintTimer = 0;
            if (paragraphModeActive && paragraphHintDeadline && paragraphCurrentPosHintKey()) {
              updateParagraphPosHint(true);
            }
          }, 5000);
        }
        paragraphHintTicker = window.setInterval(updateParagraphHintCountdown, 250);
        paragraphHintTimer = window.setTimeout(() => {
          paragraphHintTimer = 0;
          if (paragraphHintTicker) {
            window.clearInterval(paragraphHintTicker);
            paragraphHintTicker = 0;
          }
          paragraphHintDeadline = 0;
          revealNextParagraphWord(true);
          updateParagraphHintCountdown();
        }, seconds * 1000);
      }

      function clearParagraphHintTimer(options = {}) {
        if (paragraphHintTimer) {
          window.clearTimeout(paragraphHintTimer);
          paragraphHintTimer = 0;
        }
        if (paragraphPosHintTimer) {
          window.clearTimeout(paragraphPosHintTimer);
          paragraphPosHintTimer = 0;
        }
        if (paragraphHintTicker) {
          window.clearInterval(paragraphHintTicker);
          paragraphHintTicker = 0;
        }
        paragraphHintDeadline = 0;
        updateParagraphHintCountdown();
        if (!options.keepPos) {
          updateParagraphPosHint(false);
        }
      }

      function revealNextParagraphWord(hinted = false) {
        const child = currentParagraphChild();
        if (!child) {
          return false;
        }
        const parts = paragraphWordParts(child.text);
        const current = Number(paragraphRevealed[paragraphChildIndex] || 0) || 0;
        if (current >= parts.length) {
          return false;
        }
        if (hinted) {
          paragraphHints.add(paragraphHintKeyFor(current));
          paragraphHintPausedAfterAutoUnlock = true;
        }
        paragraphRevealed[paragraphChildIndex] = current + 1;
        updateParagraphPosHint(false);
        syncParagraphTokenClasses();
        openParagraphWordNotesForIndex(paragraphChildIndex, current);
        updateParagraphProgress();
        queueParagraphProgressSave(120);
        const revealedPart = parts[current] || null;
        if (revealedPart) {
          playParagraphWordAudio(paragraphChildIndex, current, revealedPart.word, 260);
        }
        if (hinted && typeof renderAiAgentParagraphQuick === "function") {
          renderAiAgentParagraphQuick();
        }
        const els = ensureParagraphRuntime();
        els.status.textContent = hinted ? "Hint released. Type the revealed word and keep going." : "Word accepted.";
        if (paragraphRevealed[paragraphChildIndex] >= parts.length) {
          els.next.disabled = false;
        }
        return true;
      }

      function paragraphShouldResumePausedAfterAutoHint() {
        const expected = currentParagraphWords();
        const revealed = Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0);
        if (!expected.length || revealed <= 0 || revealed >= expected.length) {
          return false;
        }
        return paragraphHints.has(paragraphHintKeyFor(revealed - 1, paragraphChildIndex));
      }

      function paragraphRewardLessonIdentity() {
        const source = currentLessonSource || {};
        return clean(source.path || source.name || source.title || (paragraphPayload && paragraphPayload.title) || "space-p");
      }

      function paragraphBowRewardVariant() {
        return (paragraphReviewRunActive || isReviewPhase()) ? "silver" : "gold";
      }

      function paragraphBowRewardConfig(variant = "gold") {
        if (clean(variant).toLowerCase() === "silver") {
          return {
            id: "space_p_bow_silver",
            name: "Silver Magic Bow",
            use: "Earned by correctly recalling a Space_P sentence during review.",
          };
        }
        return {
          id: "space_p_bow_gold",
          name: "Golden Magic Bow",
          use: "Earned by completing a new Space_P sentence correctly.",
        };
      }

      function paragraphTokenNode(childIndex, wordIndex) {
        const els = ensureParagraphRuntime();
        return els.text.querySelector(`.ft-paragraph-token[data-child="${Number(childIndex) || 0}"][data-word="${Number(wordIndex) || 0}"]`);
      }

      function paragraphGuideRewardAnchor() {
        const els = ensureParagraphRuntime();
        const guide = els && els.guide;
        if (!guide || !guide.getBoundingClientRect) {
          return paragraphTokenNode(paragraphChildIndex, Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0));
        }
        return {
          getBoundingClientRect: () => {
            const rect = guide.getBoundingClientRect();
            const width = Math.max(18, Math.min(44, rect.width * 0.28));
            const height = Math.max(18, Math.min(44, rect.height * 0.28));
            return {
              left: rect.left + (rect.width / 2) - (width / 2),
              top: rect.bottom + 12,
              width,
              height,
              right: rect.left + (rect.width / 2) + (width / 2),
              bottom: rect.bottom + 12 + height,
            };
          },
        };
      }

      function paragraphBowRewardEventKey(childIndex = paragraphChildIndex, variant = "gold") {
        const node = currentParagraphNode() || {};
        const children = Array.isArray(node.children) ? node.children : [];
        const child = children[childIndex] || currentParagraphChild() || {};
        const raw = [
          paragraphRewardLessonIdentity(),
          clean(node && (node.id || node.title) || `node-${paragraphNodeIndex + 1}`),
          paragraphNodeIndex,
          childIndex,
          clean(child && (child.id || child.text || child.meaning) || `segment-${Math.max(0, Number(childIndex) || 0) + 1}`),
          clean(variant || "gold"),
          "segment-complete",
        ].join("|");
        return `space-p:${hashSpaceWText(raw)}`;
      }

      function awardParagraphBowOnce(childIndex = paragraphChildIndex) {
        if (paragraphTokenHelperPausesReward() && paragraphTokenHelperUsedForCurrent(childIndex)) {
          const els = paragraphEls || ensureParagraphRuntime();
          if (els && els.status) {
            els.status.textContent = "Segment complete. Token support was used, so this bow reward is paused.";
          }
          updateParagraphRewardPreview();
          return false;
        }
        const variant = paragraphBowRewardVariant();
        const config = paragraphBowRewardConfig(variant);
        return awardInventoryItemOnce(paragraphBowRewardEventKey(childIndex, variant), config, paragraphGuideRewardAnchor(), {
          tone: variant === "silver" ? "bowsilver" : "bowgold",
          feedback: () => {
            const els = paragraphEls || ensureParagraphRuntime();
            if (els && els.status) {
              els.status.textContent = variant === "silver" ? "Silver bow obtained." : "Golden bow obtained.";
            }
          },
        });
      }

      function paragraphSaxRewardConfig(variant = "gold") {
        if (clean(variant).toLowerCase() === "silver") {
          return {
            id: "space_s_sax_silver",
            name: "Silver Devil Wings",
            use: "Earned by correctly recalling a Space_S speaking sentence during review.",
          };
        }
        return {
          id: "space_s_sax_gold",
          name: "Golden Devil Wings",
          use: "Earned by reading a new Space_S speaking sentence correctly.",
        };
      }

      function paragraphSaxRewardEventKey(childIndex = paragraphChildIndex, variant = "gold") {
        const node = currentParagraphNode() || {};
        const children = Array.isArray(node.children) ? node.children : [];
        const child = children[childIndex] || currentParagraphChild() || {};
        const raw = [
          paragraphRewardLessonIdentity(),
          clean(node && (node.id || node.title) || `node-${paragraphNodeIndex + 1}`),
          paragraphNodeIndex,
          childIndex,
          clean(child && (child.id || child.text || child.meaning) || `segment-${Math.max(0, Number(childIndex) || 0) + 1}`),
          clean(variant || "gold"),
          "segment-pass",
        ].join("|");
        return `space-s:${hashSpaceWText(raw)}`;
      }

      function awardParagraphSaxOnce(childIndex = paragraphChildIndex) {
        if (paragraphTokenHelperUsedForCurrent(childIndex)) {
          const els = paragraphEls || ensureParagraphRuntime();
          if (els && els.status) {
            els.status.textContent = "Segment passed. Token support was used, so this wings reward is paused.";
          }
          updateParagraphRewardPreview();
          return false;
        }
        const variant = paragraphBowRewardVariant();
        const config = paragraphSaxRewardConfig(variant);
        return awardInventoryItemOnce(paragraphSaxRewardEventKey(childIndex, variant), config, paragraphGuideRewardAnchor(), {
          tone: variant === "silver" ? "saxsilver" : "saxgold",
          feedback: () => {
            const els = paragraphEls || ensureParagraphRuntime();
            if (els && els.status) {
              els.status.textContent = variant === "silver" ? "Silver devil wings obtained." : "Golden devil wings obtained.";
            }
          },
        });
      }

      function paragraphSwordRewardConfig(variant = "gold") {
        if (clean(variant).toLowerCase() === "silver") {
          return {
            id: "space_l_sword_silver",
            name: "Silver Great Sword",
            use: "Earned by correctly recalling a Space_L listening sentence during review.",
          };
        }
        return {
          id: "space_l_sword_gold",
          name: "Golden Great Sword",
          use: "Earned by completing a new Space_L listening sentence correctly.",
        };
      }

      function paragraphSwordRewardEventKey(childIndex = paragraphChildIndex, variant = "gold") {
        const node = currentParagraphNode() || {};
        const children = Array.isArray(node.children) ? node.children : [];
        const child = children[childIndex] || currentParagraphChild() || {};
        const raw = [
          paragraphRewardLessonIdentity(),
          clean(node && (node.id || node.title) || `node-${paragraphNodeIndex + 1}`),
          paragraphNodeIndex,
          childIndex,
          clean(child && (child.id || child.text || child.meaning) || `segment-${Math.max(0, Number(childIndex) || 0) + 1}`),
          clean(variant || "gold"),
          "segment-pass",
        ].join("|");
        return `space-l:${hashSpaceWText(raw)}`;
      }

      function awardParagraphSwordOnce(childIndex = paragraphChildIndex) {
        if (paragraphTokenHelperUsedForCurrent(childIndex)) {
          const els = paragraphEls || ensureParagraphRuntime();
          if (els && els.status) {
            els.status.textContent = "Segment passed. Token support was used, so this sword reward is paused.";
          }
          updateParagraphRewardPreview();
          return false;
        }
        const variant = paragraphBowRewardVariant();
        const config = paragraphSwordRewardConfig(variant);
        return awardInventoryItemOnce(paragraphSwordRewardEventKey(childIndex, variant), config, paragraphGuideRewardAnchor(), {
          tone: variant === "silver" ? "swordsilver" : "swordgold",
          feedback: () => {
            const els = paragraphEls || ensureParagraphRuntime();
            if (els && els.status) {
              els.status.textContent = variant === "silver" ? "Silver great sword obtained." : "Golden great sword obtained.";
            }
          },
        });
      }

      function paragraphAiFollowupKey(childIndex = paragraphChildIndex, hintedIndexes = []) {
        const source = currentLessonSource || {};
        const node = currentParagraphNode();
        return [
          clean(source.path || source.name || source.title || "space-p"),
          clean(node && (node.id || node.title) || `node-${paragraphNodeIndex + 1}`),
          paragraphNodeIndex,
          childIndex,
          (Array.isArray(hintedIndexes) ? hintedIndexes : []).join(","),
        ].join("|");
      }

      function paragraphAiFollowupContext(child, childIndex = paragraphChildIndex, hintedIndexes = []) {
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        const parts = paragraphWordParts(child && child.text ? child.text : "");
        const hintedWords = (Array.isArray(hintedIndexes) ? hintedIndexes : [])
          .map((index) => paragraphWordSurface(parts[index] ? parts[index].word : ""))
          .filter(Boolean);
        return {
          space: "space_p",
          lesson: clean(currentLessonSource && (currentLessonSource.title || currentLessonSource.name || currentLessonSource.path) || "Space_P"),
          file: clean(currentLessonSource && currentLessonSource.path || ""),
          runtime: {
            activity: "Space_P completed segment follow-up",
            node_title: clean(node && (node.title || node.name || node.id) || `Paragraph Node ${paragraphNodeIndex + 1}`),
            node_index: Math.max(0, Number(paragraphNodeIndex) || 0) + 1,
            node_count: Array.isArray(paragraphNodes) ? paragraphNodes.length : 0,
            segment_index: Math.max(0, Number(childIndex) || 0) + 1,
            segment_count: children.length,
            completed_segment_full_internal: preserveQuestionText(child && child.text || ""),
            vietnamese_prompt: preserveQuestionText(child && child.meaning || ""),
            hinted_words: hintedWords,
            hinted_word_count: hintedWords.length,
            support_policy: "The learner completed this Space_P segment but needed one or more auto hints. Generate a short tutor follow-up question about the likely grammar, word choice, or word order issue. Do not answer it yet.",
          },
          answer_policy: "Generate one short Vietnamese follow-up question only. The segment is already complete, so it may be referenced, but do not reveal future locked content.",
        };
      }

      async function requestParagraphAiFollowup(child, childIndex = paragraphChildIndex, hintedIndexes = []) {
        if (!authToken || !child || !Array.isArray(hintedIndexes) || !hintedIndexes.length) {
          return;
        }
        const key = paragraphAiFollowupKey(childIndex, hintedIndexes);
        if (paragraphAiFollowupKeys.has(key)) {
          return;
        }
        paragraphAiFollowupKeys.add(key);
        const context = paragraphAiFollowupContext(child, childIndex, hintedIndexes);
        try {
          const { payload } = await fetchAuthJson("/ai-agent/space-p/followup", {
            method: "POST",
            body: JSON.stringify({ context }),
          });
          const question = preserveQuestionText(payload && (payload.question_vi || payload.question || payload.text) || "");
          if (!question) {
            return;
          }
          setAiAgentSuggestion({
            id: `space-p-followup:${hashSpaceWText(key)}`,
            question_vi: question,
            context,
            created_at: new Date().toISOString(),
          });
          setAiAgentStatus("Space_P tutor follow-up is ready. Open Ghost AI.");
        } catch (error) {
          paragraphAiFollowupKeys.delete(key);
        }
      }

      function syncParagraphInput(event = null) {
        if (!paragraphModeActive) {
          return;
        }
        const keepPos = Boolean(paragraphPosHintKey && paragraphPosHintKey === paragraphCurrentPosHintKey());
        clearParagraphHintTimer({ keepPos });
        const els = ensureParagraphRuntime();
        const inputWasTouched = Boolean(event && event.type === "input");
        const userSelection = inputWasTouched ? captureParagraphInputSelection(els.input) : null;
        try {
          if (paragraphHintPausedAfterAutoUnlock && (inputWasTouched || String(els.input ? els.input.value || "" : "").length > 0)) {
            paragraphHintPausedAfterAutoUnlock = false;
          }
          const expected = currentParagraphWords();
          if (isSpaceSpeechPayload()) {
            const child = currentParagraphChild();
            const previousScore = Math.max(0, Number(spaceSLastReadScore || 0) || 0);
            const expectedText = child ? child.text : "";
            const analysis = paragraphSpeechAnalysis(els.input.value, expectedText);
            const score = analysis.score;
            const expectedCount = expected.length;
            setSpaceSRevealedForCurrentChild();
            spaceSMatchedTokenKeys = new Set();
            analysis.matchedIndexes.forEach((wordIndex) => {
              spaceSMatchedTokenKeys.add(spaceSTokenKey(paragraphChildIndex, wordIndex));
            });
            if (isSpaceLPayload() && isSpaceSListeningActive()) {
              unlockSpaceLMatchedTokens(analysis.matchedIndexes);
            }
            spaceSLastReadScore = score;
            spaceSReadSessionHasInput = Boolean(String(els.input.value || "").trim());
            noteSpaceSListeningTokenProgress(els.input.value);
            syncParagraphTokenClasses();
            updateParagraphProgress();
            syncParagraphInputGhost(score >= SPACE_S_PASS_SCORE ? "good" : (els.input.value ? "typing" : ""));
            syncSpaceSManualInputGate(score);
            renderSpaceSSideCards(score, analysis);
            els.next.disabled = score < SPACE_S_PASS_SCORE;
            els.status.textContent = els.input.value
              ? `Read score ${score}%. Matched ${Math.round(analysis.matched)}/${analysis.total || expectedCount}. ${score >= SPACE_S_PASS_SCORE ? "Passed. Next node unlocked." : (isSpaceLPayload() ? (spaceLUnlockChoiceAvailable ? "Choose one highlighted hidden block to unlock." : `${Math.max(0, 2 - spaceSFailedReadSessions)} read left before one hidden block unlocks.`) : (spaceSManualInputUnlocked ? "Typing fallback is unlocked." : `${Math.max(0, 2 - spaceSFailedReadSessions)} read left before typing unlocks.`))}`
              : "Press Ctrl to read with Browser EN. Alt plays the selected model voice.";
            if (score >= SPACE_S_PASS_SCORE && event && event.type === "input") {
              if (previousScore < SPACE_S_PASS_SCORE) {
                pulseParagraphInput("good");
                if (isSpaceSPayload()) {
                  awardParagraphSaxOnce(paragraphChildIndex);
                } else if (isSpaceLPayload()) {
                  awardParagraphSwordOnce(paragraphChildIndex);
                }
              }
              saveParagraphProgressNow();
            } else {
              queueParagraphProgressSave(180);
            }
            return;
          }
        const inputState = paragraphCommittedInput(els.input.value, expected);
        const typed = inputState.committed;
        let inputPulseKind = els.input.value ? "typing" : "";
        if (!els.input.value) {
          syncParagraphInputGhost();
        }
        let matched = 0;
        for (let index = 0; index < typed.length && index < expected.length; index += 1) {
          if (typed[index] !== expected[index]) {
            break;
          }
          matched += 1;
        }
        const previousRevealed = Math.max(0, Number(paragraphRevealed[paragraphChildIndex] || 0) || 0);
        paragraphWrongTokenCount = Math.max(0, Math.min(typed.length - matched, Math.max(0, expected.length - matched)));
        if (matched > previousRevealed) {
          inputPulseKind = "good";
          paragraphWrongSoundKey = "";
          paragraphRevealed[paragraphChildIndex] = matched;
          updateParagraphPosHint(false);
          syncParagraphTokenClasses();
          openParagraphWordNotesForIndex(paragraphChildIndex, matched - 1);
          updateParagraphProgress();
          queueParagraphProgressSave(120);
          if (matched < expected.length) {
            const child = currentParagraphChild();
            const parts = child ? paragraphWordParts(child.text) : [];
            const acceptedIndex = matched - 1;
            const acceptedPart = parts[acceptedIndex] || null;
            if (acceptedPart) {
              playParagraphWordAudio(paragraphChildIndex, acceptedIndex, acceptedPart.word, 260);
            }
          }
        }
        if (typed.length && matched < typed.length) {
          pulseParagraphInput("wrong");
          if (keepPos) {
            updateParagraphPosHint(true);
          }
          const wrongKey = `${paragraphNodeIndex}:${paragraphChildIndex}:${typed.length}:${typed.slice(matched).join("|")}`;
          if (wrongKey !== paragraphWrongSoundKey) {
            paragraphWrongSoundKey = wrongKey;
            void playEffectSoundAsync("false");
          }
          updateParagraphSelfMeter();
          els.status.textContent = "Not yet. Keep the English order precise.";
          queueParagraphProgressSave(180);
          if (!paragraphHintPausedAfterAutoUnlock) {
            scheduleParagraphHint();
          }
          return;
        }
        if (expected.length && inputState.completeExact && matched >= expected.length) {
          pulseParagraphInput("good");
          updateParagraphPosHint(false);
          paragraphWrongSoundKey = "";
          paragraphWrongTokenCount = 0;
          paragraphRevealed[paragraphChildIndex] = expected.length;
          syncParagraphTokenClasses();
          updateParagraphProgress();
          els.next.disabled = false;
          els.status.textContent = "Segment complete.";
          clearParagraphHintTimer();
          saveParagraphProgressNow();
          if (!paragraphCompleting && !paragraphAdvanceTimer) {
            paragraphCompleting = true;
            const completedChild = currentParagraphChild();
            const completedParts = completedChild ? paragraphWordParts(completedChild.text) : [];
            const completedChildIndex = paragraphChildIndex;
            const completedHintIndexes = expected
              .map((_word, index) => index)
              .filter((index) => paragraphHints.has(paragraphHintKeyFor(index, completedChildIndex)));
            const finalWordIndex = Math.max(0, expected.length - 1);
            const finalPart = completedParts[finalWordIndex] || null;
            const finalWordDelay = finalPart
              ? (playParagraphWordAudio(paragraphChildIndex, finalWordIndex, finalPart.word, 140) ? 720 : 0)
              : 0;
            awardParagraphBowOnce(paragraphChildIndex);
            if (completedHintIndexes.length) {
              void requestParagraphAiFollowup(completedChild, completedChildIndex, completedHintIndexes);
            }
            window.setTimeout(() => {
              if (!paragraphModeActive || currentParagraphChild() !== completedChild) {
                paragraphCompleting = false;
                return;
              }
              void playEffectSoundAsync("true");
              void playParagraphEnglishAudio(completedChild).finally(() => {
                if (!paragraphModeActive || currentParagraphChild() !== completedChild) {
                  paragraphCompleting = false;
                  return;
                }
                paragraphAdvanceTimer = window.setTimeout(() => {
                  paragraphAdvanceTimer = 0;
                  paragraphCompleting = false;
                  advanceParagraphChild();
                }, 350);
              });
            }, finalWordDelay);
          }
          return;
        }
        if (inputPulseKind) {
          pulseParagraphInput(inputPulseKind);
        }
        if (keepPos) {
          updateParagraphPosHint(true);
        }
        paragraphWrongSoundKey = "";
        paragraphWrongTokenCount = 0;
        updateParagraphSelfMeter();
        els.status.textContent = inputState.partial
          ? "Typing current word..."
          : (matched ? "Good. Continue the segment." : `Segment ${paragraphChildIndex + 1}/${(currentParagraphNode().children || []).length}`);
        queueParagraphProgressSave(180);
        if (!paragraphHintPausedAfterAutoUnlock) {
          scheduleParagraphHint();
        } else {
          updateParagraphHintCountdown();
        }
        } finally {
          restoreParagraphInputSelection(userSelection);
        }
      }

      function advanceParagraphChild() {
        if (!paragraphModeActive) {
          return;
        }
        clearParagraphTimers();
        const node = currentParagraphNode();
        const children = node && Array.isArray(node.children) ? node.children : [];
        if (isSpaceSpeechPayload()) {
          stopSpaceSListeningSession({ finalizeAttempt: false });
          clearSpaceSUserAudio();
          spaceSMatchedTokenKeys = new Set();
        }
        if (paragraphChildIndex < children.length - 1) {
          paragraphChildIndex += 1;
          paragraphWrongSoundKey = "";
          paragraphHintPausedAfterAutoUnlock = false;
          renderParagraphDock();
        if (isSpaceSpeechPayload()) {
            setSpaceSRevealedForCurrentChild();
          }
          syncParagraphTokenClasses();
          updateParagraphProgress();
          saveParagraphProgressNow();
          scheduleParagraphHint();
          centerParagraphFocusInViewport(paragraphChildIndex);
          return;
        }
        if (paragraphNodeIndex < paragraphNodes.length - 1) {
          paragraphNodeIndex += 1;
          paragraphChildIndex = 0;
          paragraphRevealed = new Array((currentParagraphNode().children || []).length).fill(0);
          spaceLUnlockChoiceAvailable = false;
          if (isSpaceSpeechPayload()) {
            setSpaceSRevealedForCurrentChild();
          }
          paragraphHints = new Set();
          paragraphWrongTokenCount = 0;
          paragraphWrongSoundKey = "";
          paragraphHintPausedAfterAutoUnlock = false;
          renderParagraphCard();
          renderParagraphDock("New paragraph node online.");
          saveParagraphProgressNow();
          scheduleParagraphHint();
          centerParagraphFocusInViewport(paragraphChildIndex);
          return;
        }
        completeParagraphPayload();
      }

      function resetParagraphMode(options = {}) {
        clearParagraphTimers();
        paragraphModeActive = false;
        paragraphReviewRunActive = false;
        paragraphActiveRunId = "";
        setLoadVoiceLock(false);
        paragraphPayload = null;
        paragraphNodes = [];
        paragraphNodeIndex = 0;
        paragraphChildIndex = 0;
        paragraphRevealed = [];
        paragraphHints = new Set();
        paragraphHintPausedAfterAutoUnlock = false;
        paragraphPosHintKey = "";
        paragraphExplanationIndex = 0;
        paragraphWrongTokenCount = 0;
        paragraphWrongSoundKey = "";
        paragraphAiFollowupKeys = new Set();
        paragraphTokenHelperUsedKeys = new Set();
        spaceSMatchedTokenKeys = new Set();
        spaceLUnlockedTokenKeys = new Set();
        spaceLUnlockChoiceAvailable = false;
        spaceSFailedReadSessions = 0;
        spaceSManualInputUnlocked = false;
        spaceSReadSessionHasInput = false;
        spaceSReadSessionFinalized = false;
        spaceSLastReadScore = 0;
        stopSpaceSListeningSession({ finalizeAttempt: false });
        clearSpaceSUserAudio();
        stopParagraphAudioPlayback();
        setSpaceSMicLiveState(false);
        setParagraphModeClass(false);
        if (!options.keepPending) {
          pendingParagraphPayload = null;
        }
        if (paragraphEls && paragraphEls.root) {
          paragraphEls.root.classList.add("is-hidden");
          closeParagraphExplanationPopup();
          closeParagraphWordNotes();
          updateParagraphPosHint(false);
        }
      }

      async function completeParagraphPayload() {
        const els = ensureParagraphRuntime();
        const mode = paragraphSpaceMode();
        const completionKind = mode === "space_l" ? "space_l_complete" : (mode === "space_s" ? "space_s_complete" : "space_p_complete");
        els.status.textContent = mode === "space_l" ? "Listening unlock complete." : (mode === "space_s" ? "Speaking unlock complete." : "Paragraph rewrite complete.");
        els.input.disabled = true;
        els.next.disabled = true;
        stopSpaceSListeningSession({ finalizeAttempt: false });
        clearParagraphTimers();
        saveParagraphProgressNow();
        await delay(350);
        resetParagraphMode({ keepPending: true });
        void reportLessonCompleted(completionKind);
      }

      async function enterParagraphPayloadNow(payload, options = {}) {
        const normalized = normalizeParagraphPayload(payload);
        if (!normalized.nodes.length) {
          setLoadStatus("This paragraph lesson has no valid paragraph node.", true);
          return false;
        }
        updateFutureAppRoute(paragraphSpaceMode(normalized), { replace: futureAppRouteFromLocation() === "lesson_vault" });
        if (!currentParagraphProgressCache.progressKey || currentParagraphProgressCache.identity !== paragraphProgressIdentityFor(normalized, normalized.nodes)) {
          configureParagraphProgressCache(normalized, normalized.nodes);
        }
        const cachedSavedProgress = currentParagraphProgressCache && currentParagraphProgressCache.savedProgress && typeof currentParagraphProgressCache.savedProgress === "object"
          ? currentParagraphProgressCache.savedProgress
          : null;
        const cachedResumeState = !options.forceNewRun && !options.resumeState && cachedSavedProgress && cachedSavedProgress.state && typeof cachedSavedProgress.state === "object"
          ? normalizeParagraphResumeState(cachedSavedProgress.state, normalized)
          : null;
        const resumeState = options.forceNewRun
          ? null
          : (options.resumeState && typeof options.resumeState === "object"
            ? normalizeParagraphResumeState(options.resumeState, normalized)
            : cachedResumeState);
        const reviewRun = Boolean(
          options.reviewRun
          || (resumeState && (resumeState.reviewing || resumeState.reviewRun))
        );
        resetCurrentMissionCrystalAwards();
        resetSpaceWCache();
        resetQuestionMode();
        vocabModeActive = false;
        setVocabModeClass(false);
        paragraphModeActive = true;
        paragraphReviewRunActive = reviewRun;
        paragraphActiveRunId = clean(resumeState && (resumeState.runId || resumeState.run_id))
          || `space-p-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
        setParagraphModeClass(true);
        paragraphPayload = normalized;
        paragraphNodes = normalized.nodes;
        paragraphNodeIndex = resumeState
          ? resumeState.currentIndex
          : Math.max(0, Math.min(normalized.nodes.length - 1, Number(options.startIndex || 0) || 0));
        paragraphChildIndex = resumeState ? resumeState.childIndex : 0;
        paragraphRevealed = resumeState
          ? resumeState.revealed.slice()
          : new Array((currentParagraphNode().children || []).length).fill(0);
        if (isSpaceSpeechPayload(normalized)) {
          setSpaceSRevealedForCurrentChild();
        }
        paragraphHints = new Set(resumeState ? resumeState.hints : []);
        spaceLUnlockedTokenKeys = new Set(resumeState && Array.isArray(resumeState.spaceLUnlockedTokens) ? resumeState.spaceLUnlockedTokens : []);
        spaceLUnlockChoiceAvailable = false;
        paragraphHintPausedAfterAutoUnlock = resumeState ? paragraphShouldResumePausedAfterAutoHint() : false;
        paragraphWrongTokenCount = resumeState ? resumeState.wrongTokenCount : 0;
        paragraphWrongSoundKey = "";
        paragraphAiFollowupKeys = new Set();
        paragraphTokenHelperUsedKeys = new Set();
        lessonNodes = normalized.nodes;
        pendingParagraphPayload = null;
        pendingVocabularyPayload = null;
        pendingQuestionPayload = null;
        pendingLessonNodes = [];
        pendingLessonEffects = {};
        lessonEffects = normalizeEffectSounds(normalized.effects || {});
        currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(normalized);
        setQuestionInventoryHudVisible(true);
        void loadQuestionInventory();
        const els = ensureParagraphRuntime();
        els.root.classList.remove("is-hidden");
        if (loadGate) {
          loadGate.classList.add("is-hidden");
          loadGate.classList.remove("is-file-ready");
        }
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
        hideCompletionGate();
        setTtsStatus(`${paragraphModeLabel()} ready.`);
        renderParagraphCard();
        renderParagraphDock(
          resumeState
            ? `Saved ${paragraphModeLabel()} progress restored.`
            : (isSpaceLPayload(normalized)
              ? "Listen and rebuild the hidden sentence."
              : (isSpaceSPayload(normalized)
                ? "Read each sentence aloud to unlock the next one."
                : "Rewrite the segment from Vietnamese to English."))
        );
        centerParagraphFocusInViewport(paragraphChildIndex);
        if (resumeState && resumeState.inputValue && els.input) {
          els.input.value = resumeState.inputValue;
          syncParagraphInputGhost();
          pulseParagraphInput("typing");
        }
        scheduleParagraphHint();
        saveParagraphProgressNow();
        warmParagraphAudioCacheForLesson(normalized, {
          startIndex: paragraphNodeIndex,
          startChildIndex: paragraphChildIndex,
          label: "Space_P",
          includeEffects: true,
          startDelayMs: 450,
          delayMs: 85,
          status: false,
        });
        return true;
      }

      const questionAnswerKey = (value) => {
        try {
          return clean(value)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^\p{L}\p{N}]+/gu, " ")
            .trim();
        } catch (error) {
          return normalize(value);
        }
      };

      const questionAcceptedAnswers = (question) => {
        const source = question && typeof question === "object" ? question : {};
        const values = [source.answer, ...(Array.isArray(source.answers) ? source.answers : [])];
        const result = [];
        const seen = new Set();
        values.forEach((value) => {
          const cleaned = clean(value && typeof value === "object" ? value.text : value);
          const key = questionAnswerKey(cleaned);
          if (cleaned && key && !seen.has(key)) {
            seen.add(key);
            result.push(cleaned);
          }
        });
        return result.length ? result : (clean(source.answer) ? [clean(source.answer)] : []);
      };

      const isQuestionGuideItem = (question) => clean(question && question.type).toLowerCase() === "guide";

      const isQuestionSelectItem = (question) => clean(question && question.type).toLowerCase() === "select";

      const isQuestionTypedItem = (question) => (
        !isQuestionGuideItem(question)
        && !isQuestionSelectItem(question)
        && (clean(question && question.type).toLowerCase() === "input" || !(Array.isArray(question && question.wrong) && question.wrong.length))
      );

      const questionSelectAnswerTokens = (question) => {
        const source = question && typeof question === "object" ? question : {};
        const explicitTokens = source.tokens ?? source.select_tokens ?? source.selectTokens;
        if (explicitTokens !== undefined && explicitTokens !== null) {
          return splitQuestionSelectTokens(explicitTokens);
        }
        return splitQuestionSelectTokens(source.answer || "");
      };

      const questionSelectAnswerText = (question) => questionSelectAnswerTokens(question).join(" ");

      const questionSelectTargets = (question) => {
        const targets = question && question.select_targets && typeof question.select_targets === "object"
          ? question.select_targets
          : {};
        return {
          root_text: preserveQuestionText(targets.root_text ?? targets.rootText ?? ""),
          root_ranges: Array.isArray(targets.root_ranges ?? targets.rootRanges ?? targets.root_segments ?? targets.rootSegments)
            ? (targets.root_ranges ?? targets.rootRanges ?? targets.root_segments ?? targets.rootSegments).map((entry) => {
              const raw = entry && typeof entry === "object" ? entry : {};
              return {
                start: Math.max(0, Math.floor(Number(raw.start ?? raw.s ?? 0) || 0)),
                end: Math.max(0, Math.floor(Number(raw.end ?? raw.e ?? 0) || 0)),
                text: preserveQuestionText(raw.text ?? raw.t ?? ""),
              };
            }).filter((entry) => entry.end > entry.start || entry.text)
            : [],
          regions: normalizeQuestionPictureRegions(targets.regions ?? targets.picture_regions ?? targets.pictureRegions ?? []),
          region_color: optionalQuestionPictureRegionColor(targets.region_color ?? targets.regionColor ?? targets.color ?? targets.c),
        };
      };

      const questionSelectSourceText = (question) => {
        const source = question && typeof question === "object" ? question : {};
        const targets = questionSelectTargets(source);
        if (targets.root_ranges.length) {
          return targets.root_ranges.map((entry) => preserveQuestionText(entry.text)).filter(Boolean).join(" ");
        }
        if (targets.root_text) {
          return targets.root_text;
        }
        const explicit = preserveQuestionText(source.select_source ?? source.selectSource ?? source.source_text ?? source.sourceText ?? source.token_source ?? source.tokenSource ?? "");
        if (explicit) {
          return explicit;
        }
        const highlights = Array.isArray(source.root_highlights) ? source.root_highlights : [];
        const highlight = highlights.find((entry) => preserveQuestionText(entry && entry.text));
        if (highlight) {
          return preserveQuestionText(highlight.text);
        }
        const rootCard = questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root
          ? questionCurrentNode.cards.root
          : {};
        return preserveQuestionText(rootCard.text ?? questionCurrentNode?.root ?? "");
      };

      const questionSelectSourceTokens = (question) => {
        const sourceText = questionSelectSourceText(question);
        const matches = sourceText.match(/[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu) || [];
        const answerTokens = questionSelectAnswerTokens(question);
        const result = [];
        matches.forEach((token) => {
          const value = clean(token);
          if (value) {
            result.push(value);
          }
        });
        const sourceKeys = new Map();
        result.forEach((token) => {
          const key = questionAnswerKey(token);
          sourceKeys.set(key, (sourceKeys.get(key) || 0) + 1);
        });
        answerTokens.forEach((token) => {
          const key = questionAnswerKey(token);
          const needed = answerTokens.filter((item) => questionAnswerKey(item) === key).length;
          const existing = sourceKeys.get(key) || 0;
          if (key && existing < needed) {
            result.push(token);
            sourceKeys.set(key, existing + 1);
          }
        });
        return result;
      };

      const questionTokenCounts = (tokens) => {
        const counts = new Map();
        (Array.isArray(tokens) ? tokens : []).forEach((token) => {
          const key = questionAnswerKey(token);
          if (key) {
            counts.set(key, (counts.get(key) || 0) + 1);
          }
        });
        return counts;
      };

      const questionTokenCountsMatch = (leftTokens, rightTokens) => {
        const left = questionTokenCounts(leftTokens);
        const right = questionTokenCounts(rightTokens);
        if (left.size !== right.size) {
          return false;
        }
        for (const [key, count] of left.entries()) {
          if ((right.get(key) || 0) !== count) {
            return false;
          }
        }
        return true;
      };

      const questionExactCounts = (values = []) => {
        const counts = new Map();
        (Array.isArray(values) ? values : []).forEach((value) => {
          const key = clean(value);
          if (key) {
            counts.set(key, (counts.get(key) || 0) + 1);
          }
        });
        return counts;
      };

      const questionExactCountsMatch = (leftValues = [], rightValues = []) => {
        const left = questionExactCounts(leftValues);
        const right = questionExactCounts(rightValues);
        if (left.size !== right.size) {
          return false;
        }
        for (const [key, count] of left.entries()) {
          if ((right.get(key) || 0) !== count) {
            return false;
          }
        }
        return true;
      };

      const questionSelectedTokenValues = () => Array.from(document.querySelectorAll(".ft-q-select-token.is-selected, .ft-q-select-root-token.is-selected"))
        .map((button) => clean(button.dataset ? (button.dataset.token || button.dataset.qSelectToken) : button.textContent))
        .filter(Boolean);

      const questionSelectedRootTokenEntries = () => Array.from(document.querySelectorAll(".ft-q-select-root-token.is-selected"))
        .map((button) => {
          const start = Math.max(0, Math.floor(Number(button.dataset ? button.dataset.qSelectStart : 0) || 0));
          const end = Math.max(start, Math.floor(Number(button.dataset ? button.dataset.qSelectEnd : start) || start));
          const token = clean(button.dataset ? button.dataset.qSelectToken : button.textContent);
          return token && end > start
            ? { node: button, start, end, token, key: `${start}:${end}:${questionAnswerKey(token)}` }
            : null;
        })
        .filter(Boolean);

      const questionSelectRootAnswerEntries = (question) => {
        const rootText = preserveQuestionText((questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root && questionCurrentNode.cards.root.text) || questionTypingFullText || "");
        if (!rootText) {
          return [];
        }
        const ranges = typeof questionSelectRootRangesForItem === "function" ? questionSelectRootRangesForItem(question) : [];
        const wordPattern = /[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu;
        const entries = [];
        ranges.forEach((range) => {
          if (!range || range.end <= range.start) {
            return;
          }
          const segment = rootText.slice(range.start, range.end);
          wordPattern.lastIndex = 0;
          let match;
          while ((match = wordPattern.exec(segment)) !== null) {
            const token = clean(match[0]);
            const start = range.start + match.index;
            const end = start + match[0].length;
            if (token && end > start) {
              entries.push({ start, end, token, key: `${start}:${end}:${questionAnswerKey(token)}` });
            }
          }
        });
        return entries;
      };

      const questionSelectRootAnswerKeys = (question) => questionSelectRootAnswerEntries(question).map((entry) => entry.key);

      const questionSelectUsesRootPositionTargets = (question) => questionSelectRootAnswerKeys(question).length > 0;

      const questionSelectRegionKey = (region, index = 0) => clean(region && (region.id || region.label || region.name || region.i)) || `r${index + 1}`;

      const questionSelectRequiredRegions = (question) => questionSelectTargets(question).regions.map(questionSelectRegionKey);

      const questionSelectedRegionValues = () => questionPictureRegionLayer
        ? Array.from(questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer.is-selected"))
          .map((node) => clean(node.dataset ? node.dataset.selectRegion : ""))
          .filter(Boolean)
        : [];

      const questionSelectRegionsMatch = (left, right) => {
        const leftKeys = (Array.isArray(left) ? left : []).map(clean).filter(Boolean).sort();
        const rightKeys = (Array.isArray(right) ? right : []).map(clean).filter(Boolean).sort();
        return leftKeys.length === rightKeys.length && leftKeys.every((value, index) => value === rightKeys[index]);
      };

      const questionSelectRequiredTotal = (question) => {
        const rootKeys = questionSelectRootAnswerKeys(question);
        return (rootKeys.length ? rootKeys.length : questionSelectAnswerTokens(question).length) + questionSelectRequiredRegions(question).length;
      };

      const questionSelectSelectedTotal = () => questionSelectedTokenValues().length + questionSelectedRegionValues().length;

      const questionSelectCorrectSelectedTotal = (question) => {
        const rootKeys = questionSelectRootAnswerKeys(question);
        if (rootKeys.length) {
          const requiredRootCounts = questionExactCounts(rootKeys);
          const selectedRootCounts = questionExactCounts(questionSelectedRootTokenEntries().map((entry) => entry.key));
          let rootTotal = 0;
          requiredRootCounts.forEach((requiredCount, key) => {
            rootTotal += Math.min(requiredCount, selectedRootCounts.get(key) || 0);
          });
          const requiredRegions = new Set(questionSelectRequiredRegions(question));
          rootTotal += questionSelectedRegionValues().filter((value) => requiredRegions.has(value)).length;
          return rootTotal;
        }
        const requiredTokenCounts = questionTokenCounts(questionSelectAnswerTokens(question));
        const selectedTokenCounts = questionTokenCounts(questionSelectedTokenValues());
        let total = 0;
        requiredTokenCounts.forEach((requiredCount, key) => {
          total += Math.min(requiredCount, selectedTokenCounts.get(key) || 0);
        });
        const requiredRegions = new Set(questionSelectRequiredRegions(question));
        total += questionSelectedRegionValues().filter((value) => requiredRegions.has(value)).length;
        return total;
      };

      const updateQuestionSelectProgressCard = (question = currentQuestionItem()) => {
        if (!qChoiceList || !question || !isQuestionSelectItem(question)) {
          if (qSelectSubmitButton) {
            qSelectSubmitButton.classList.add("ft-q-show-answer-hidden");
            qSelectSubmitButton.disabled = true;
          }
          return;
        }
        let progress = qChoiceList.querySelector(".ft-q-select-progress");
        if (!progress) {
          progress = document.createElement("div");
          progress.className = "ft-q-select-progress";
          qChoiceList.prepend(progress);
        }
        const selected = questionSelectSelectedTotal();
        const total = questionSelectRequiredTotal(question);
        const targets = questionSelectTargets(question);
        const hasTargets = Boolean(targets.root_text || targets.root_ranges.length || targets.regions.length);
        const label = hasTargets ? "Select on Root text / Picture card" : "No Root/Picture target set";
        progress.innerHTML = `<strong>${selected}/${total || 0}</strong><span>${label}</span>`;
        if (qSelectSubmitButton) {
          const picked = questionSelectSelectedTotal();
          qSelectSubmitButton.classList.remove("ft-q-show-answer-hidden");
          qSelectSubmitButton.disabled = !picked || Boolean(questionSelectCompletionTimer);
          qSelectSubmitButton.title = picked
            ? `Confirm selected targets (${picked}/${total || 0})`
            : "Select answer targets first";
          qSelectSubmitButton.setAttribute("aria-disabled", qSelectSubmitButton.disabled ? "true" : "false");
        }
      };

      const focusQuestionSelectSubmitButton = (delay = 20) => {
        if (!qSelectSubmitButton) {
          return;
        }
        window.setTimeout(() => {
          if (
            qSelectSubmitButton
            && !qSelectSubmitButton.disabled
            && !qSelectSubmitButton.classList.contains("ft-q-show-answer-hidden")
            && document.body.contains(qSelectSubmitButton)
          ) {
            qSelectSubmitButton.focus({ preventScroll: true });
          }
        }, delay);
      };

      const clearQuestionSelectAnswerLitTargets = () => {
        document.querySelectorAll(".ft-q-select-root-overlay.is-answer-lit, .ft-q-select-root-merge.is-answer-lit, .ft-q-picture-region.is-select-answer.is-answer-lit").forEach((node) => {
          node.classList.remove("is-answer-lit");
          node.style.removeProperty("--q-answer-lit-delay");
        });
      };

      const clearQuestionSelectCompletionState = () => {
        questionSelectCompletionToken += 1;
        if (questionSelectCompletionTimer) {
          window.clearTimeout(questionSelectCompletionTimer);
          questionSelectCompletionTimer = 0;
        }
        if (qChoiceList) {
          qChoiceList.classList.remove("is-select-complete");
        }
        if (questionSelectConnectorLayer) {
          questionSelectConnectorLayer.classList.remove("is-complete");
        }
        clearQuestionSelectAnswerLitTargets();
        document.querySelectorAll(".ft-q-select-root-overlay.is-confirming, .ft-q-select-root-merge.is-confirming, .ft-q-picture-region.is-select-answer.is-confirming, .ft-q-select-root-overlay.is-token-wrong, .ft-q-picture-region.is-select-answer.is-token-wrong").forEach((node) => {
          node.classList.remove("is-confirming", "is-token-wrong");
        });
      };

      const markQuestionSelectSubmittedState = (question, ok = false) => {
        const requiredRootKeys = questionSelectRootAnswerKeys(question);
        const useRootKeys = requiredRootKeys.length > 0;
        const requiredRootCounts = questionExactCounts(requiredRootKeys);
        const seenRootCounts = new Map();
        const requiredTokenCounts = questionTokenCounts(questionSelectAnswerTokens(question));
        const seenTokenCounts = new Map();
        document.querySelectorAll(".ft-q-select-root-token.is-selected").forEach((node) => {
          const start = Math.max(0, Math.floor(Number(node.dataset ? node.dataset.qSelectStart : 0) || 0));
          const end = Math.max(start, Math.floor(Number(node.dataset ? node.dataset.qSelectEnd : start) || start));
          const token = clean(node.dataset ? node.dataset.qSelectToken : node.textContent);
          const exactKey = `${start}:${end}:${questionAnswerKey(token)}`;
          const tokenKey = questionAnswerKey(token);
          let tokenOk = Boolean(ok);
          if (!tokenOk && useRootKeys) {
            const nextCount = (seenRootCounts.get(exactKey) || 0) + 1;
            seenRootCounts.set(exactKey, nextCount);
            tokenOk = exactKey && requiredRootCounts.has(exactKey) && nextCount <= (requiredRootCounts.get(exactKey) || 0);
          } else if (!tokenOk) {
            const nextCount = (seenTokenCounts.get(tokenKey) || 0) + 1;
            seenTokenCounts.set(tokenKey, nextCount);
            tokenOk = tokenKey && requiredTokenCounts.has(tokenKey) && nextCount <= (requiredTokenCounts.get(tokenKey) || 0);
          }
          node.classList.toggle("is-token-wrong", !tokenOk);
        });
        const requiredRegions = new Set(questionSelectRequiredRegions(question));
        if (questionPictureRegionLayer) {
          questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer.is-selected").forEach((node) => {
            const key = clean(node.dataset ? node.dataset.selectRegion : "");
            node.classList.toggle("is-token-wrong", !ok && !requiredRegions.has(key));
          });
        }
        refreshQuestionSelectRootMergedHighlights();
      };

      const resetQuestionSelectSelections = (question = currentQuestionItem(), options = {}) => {
        const animate = options && options.animate !== false;
        const selectedNodes = Array.from(document.querySelectorAll(".ft-q-select-root-token.is-selected, .ft-q-select-root-merge, .ft-q-picture-region.is-select-answer.is-selected"));
        if (animate && selectedNodes.length) {
          selectedNodes.forEach((node, index) => {
            node.classList.add("is-shattering");
            node.style.animationDelay = `${Math.min(180, index * 18)}ms`;
          });
        }
        window.setTimeout(() => {
          document.querySelectorAll(".ft-q-select-root-token.is-selected, .ft-q-select-root-token.is-token-wrong, .ft-q-select-root-token.is-confirming").forEach((node) => {
            node.classList.remove("is-selected", "is-token-wrong", "is-confirming", "is-shattering");
            node.style.removeProperty("animation-delay");
          });
          document.querySelectorAll(".ft-q-select-root-merge").forEach((node) => node.remove());
          if (questionPictureRegionLayer) {
            questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer").forEach((node) => {
              node.classList.remove("is-selected", "is-token-wrong", "is-confirming", "is-shattering", "is-answer-lit");
              node.style.removeProperty("animation-delay");
              node.style.removeProperty("--q-answer-lit-delay");
            });
          }
          clearQuestionSelectAnswerLitTargets();
          hideQuestionSelectConnectors();
          updateQuestionSelectProgressCard(question);
        }, animate && selectedNodes.length ? 560 : 0);
      };

      const markQuestionSelectCompletionState = () => {
        if (qChoiceList) {
          qChoiceList.classList.add("is-select-complete");
        }
        const layer = ensureQuestionSelectConnectorLayer();
        if (layer) {
          layer.classList.add("is-complete");
        }
        document.querySelectorAll(".ft-q-select-root-overlay.is-selected, .ft-q-select-root-merge, .ft-q-picture-region.is-select-answer.is-selected").forEach((node) => {
          node.classList.add("is-confirming");
        });
      };

      const runQuestionSelectCorrectSequence = (item, sourceNode) => {
        clearQuestionSelectCompletionState();
        const token = ++questionSelectCompletionToken;
        if (qSelectSubmitButton) {
          qSelectSubmitButton.disabled = true;
        }
        markQuestionSelectCompletionState();
        setQuestionAnswerFeedback("Selection confirmed. Routing to the question card...", "ok");
        void playEffectSoundAsync("true");
        runQuestionSelectAnswerRevealConnectors(questionLastPointerClient);
        questionSelectCompletionTimer = window.setTimeout(() => {
          questionSelectCompletionTimer = 0;
          if (token !== questionSelectCompletionToken || !questionModeActive || currentQuestionItem() !== item) {
            return;
          }
          const finish = () => {
            if (token !== questionSelectCompletionToken || !questionModeActive || currentQuestionItem() !== item) {
              return;
            }
            clearQuestionSelectCompletionState();
            checkQuestionAnswer(questionSelectAnswerText(item) || clean(item && item.answer), sourceNode, { skipSound: true });
          };
          if (isQuestionMobileFlow()) {
            finish();
            return;
          }
          smoothReturnQuestionCardOnlyView(finish);
        }, 2600);
      };

      const questionSelectCheckCompletion = (item, sourceNode) => {
        const requiredRootKeys = questionSelectRootAnswerKeys(item);
        const selectedRootKeys = questionSelectedRootTokenEntries().map((entry) => entry.key);
        const useRootKeys = requiredRootKeys.length > 0;
        const requiredTokens = useRootKeys ? [] : questionSelectAnswerTokens(item);
        const selectedTokens = useRootKeys ? [] : questionSelectedTokenValues();
        const requiredRegions = questionSelectRequiredRegions(item);
        const selectedRegions = questionSelectedRegionValues();
        const selectedCount = (useRootKeys ? selectedRootKeys.length : selectedTokens.length) + selectedRegions.length;
        const requiredCount = (useRootKeys ? requiredRootKeys.length : requiredTokens.length) + requiredRegions.length;
        updateQuestionSelectProgressCard(item);
        refreshQuestionSelectRootMergedHighlights();
        if (requiredCount && selectedCount < requiredCount) {
          questionWrongAttempts += 1;
          queueQuestionProgressSave(220);
          resetQuestionSelectSelections(item, { animate: true });
          void playEffectSoundAsync("false");
          setQuestionAnswerFeedback(questionWrongAttempts >= 2 ? "Sai 2 lần. Bạn có thể hiện đáp án." : `Selected ${selectedCount}/${requiredCount} targets. Select more and try again.`, "error");
          if (questionWrongAttempts >= 2) {
            revealQuestionAnswerButton();
          }
          return;
        }
        const ok = (useRootKeys ? questionExactCountsMatch(selectedRootKeys, requiredRootKeys) : questionTokenCountsMatch(selectedTokens, requiredTokens))
          && questionSelectRegionsMatch(selectedRegions, requiredRegions);
        if (ok) {
          markQuestionSelectSubmittedState(item, true);
          runQuestionSelectCorrectSequence(item, sourceNode);
          return;
        }
        questionWrongAttempts += 1;
        queueQuestionProgressSave(220);
        resetQuestionSelectSelections(item, { animate: true });
        void playEffectSoundAsync("false");
        const errorText = questionWrongAttempts >= 2 ? "Sai 2 lần. Bạn có thể hiện đáp án." : "Some selected targets are not correct yet.";
        setQuestionAnswerFeedback(errorText, "error");
        if (questionWrongAttempts >= 2) {
          revealQuestionAnswerButton();
        }
      };

      const submitQuestionSelectAnswer = () => {
        const item = currentQuestionItem();
        if (!item || !isQuestionSelectItem(item) || questionSelectCompletionTimer) {
          return;
        }
        const selectedCount = questionSelectSelectedTotal();
        if (!selectedCount) {
          setQuestionAnswerFeedback("Select at least one target before locking your answer.", "error");
          void playEffectSoundAsync("false");
          return;
        }
        if (qSelectSubmitButton) {
          qSelectSubmitButton.disabled = true;
        }
        questionSelectCheckCompletion(item, qSelectSubmitButton || qQuestionCard || qRootCard);
        updateQuestionSelectProgressCard(item);
      };

      const questionClientPointInShell = (clientPoint = null) => {
        if (!shellNode || !shellNode.getBoundingClientRect) {
          return { x: 0, y: 0 };
        }
        const shellRect = shellNode.getBoundingClientRect();
        const point = clientPoint && Number.isFinite(Number(clientPoint.x)) && Number.isFinite(Number(clientPoint.y))
          ? clientPoint
          : (qShowAnswerButton && qShowAnswerButton.getBoundingClientRect
            ? (() => {
              const rect = qShowAnswerButton.getBoundingClientRect();
              return { x: rect.left + rect.width * 0.5, y: rect.top + rect.height * 0.5 };
            })()
            : { x: window.innerWidth * 0.5, y: window.innerHeight * 0.5 });
        return {
          x: questionUnscaleLayoutValue(point.x - shellRect.left),
          y: questionUnscaleLayoutValue(point.y - shellRect.top),
        };
      };
