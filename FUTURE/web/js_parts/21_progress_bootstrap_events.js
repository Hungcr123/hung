

      // Added 2026-07-21: retries reuse the snapshot operation ID stored with the local checkpoint.
      const createSpaceWProgressOperationId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `space-w-${window.crypto.randomUUID()}`;
        }
        return `space-w-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      };

      // Added 2026-07-21: Space_Q retries reuse the durable local snapshot operation ID.
      const createQuestionProgressOperationId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `space-q-${window.crypto.randomUUID()}`;
        }
        return `space-q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      };

      const saveSpaceWProgressNow = () => {
        if (spaceWProgressSaveTimer) {
          window.clearTimeout(spaceWProgressSaveTimer);
          spaceWProgressSaveTimer = 0;
        }
        if (!canSaveSpaceWProgress()) {
          return false;
        }
        spaceWNodeProgress = mergedSpaceWNodeProgress();
        const snapshot = runtimeSnapshot();
        delete snapshot.nodes;
        delete snapshot.effects;
        snapshot.nodeCount = lessonNodes.length;
        snapshot.savedAt = new Date().toISOString();
        snapshot.syncOperationId = createSpaceWProgressOperationId();
        snapshot.nodeProgress = { ...spaceWNodeProgress };
        snapshot.reviewing = Boolean(reviewModeActive);
        snapshot.reviewRun = Boolean(reviewModeActive);
        snapshot.activeRun = Boolean(!lessonCompletionSent && !reviewFinished);
        snapshot.complete = Boolean(lessonCompletionSent);
        snapshot.lessonComplete = Boolean(lessonCompletionSent);
        const progressNodeTotal = Math.max(0, lessonNodes.length);
        const rootNodeCount = Math.max(0, lessonNodes.filter((node) => !isSpaceWTrainingNode(node)).length);
        const normalSentenceCount = rootNodeCount;
        const trainSentenceCount = Math.max(0, spaceWTrainModeExpanded
          ? lessonNodes.filter((node) => isSpaceWTrainingNode(node)).length
          : collectSpaceWTrainModeNodes().length);
        const progressTotal = progressNodeTotal * 2;
        const reviewDone = Math.max(0, Math.min(progressNodeTotal, reviewMasteredIndexes.size));
        const progressDone = lessonCompletionSent || reviewFinished
          ? progressTotal
          : (reviewModeActive ? progressNodeTotal + reviewDone : Math.max(0, Math.min(progressNodeTotal, currentNodeIndex)));
        snapshot.runId = spaceWActiveRunId;
        snapshot.progressDone = progressDone;
        snapshot.progressTotal = progressTotal;
        snapshot.rootNodeCount = rootNodeCount;
        snapshot.normalSentenceCount = normalSentenceCount;
        snapshot.trainSentenceCount = trainSentenceCount;
        snapshot.sentenceCount = normalSentenceCount + trainSentenceCount;
        const record = {
          version: 1,
          identity: currentSpaceWCache.identity,
          savedAt: snapshot.savedAt,
          title: clean(currentLessonSource.title || currentLessonSource.name || "Space_W"),
          nodeIndex: currentNodeIndex,
          nodeCount: lessonNodes.length,
          runId: spaceWActiveRunId,
          progressDone,
          progressTotal,
          rootNodeCount,
          normalSentenceCount,
          trainSentenceCount,
          sentenceCount: normalSentenceCount + trainSentenceCount,
          syncOperationId: snapshot.syncOperationId,
          activeRun: snapshot.activeRun,
          reviewing: snapshot.reviewing,
          reviewRun: snapshot.reviewRun,
          complete: snapshot.complete,
          lessonComplete: snapshot.lessonComplete,
          pendingServerSync: true,
          state: snapshot,
        };
        const ok = writeSpaceWJson(currentSpaceWCache.progressKey, record);
        if (ok) {
          currentSpaceWCache.savedProgress = record;
          updateSpaceWReviewButton();
          if (typeof spaceWProgressOverrideFromRecord === "function") {
            const progressOverride = spaceWProgressOverrideFromRecord(record);
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
        }
        queueSpaceWServerProgressSync(record, 350);
        return ok ? record : false;
      };

      const queueSpaceWProgressSave = (delayMs = 250) => {
        if (!canSaveSpaceWProgress()) {
          return;
        }
        if (spaceWProgressSaveTimer) {
          window.clearTimeout(spaceWProgressSaveTimer);
        }
        spaceWProgressSaveTimer = window.setTimeout(saveSpaceWProgressNow, Math.max(40, Number(delayMs) || 250));
      };

      const questionProgressSnapshot = () => {
        const progressStats = questionProgressStats();
        const questionDone = Math.max(0, Math.floor(Number(progressStats.done || 0) || 0));
        const questionTotal = Math.max(0, Math.floor(Number(progressStats.total || 0) || 0));
        const questionComplete = Boolean(questionTotal && questionDone >= questionTotal);
        return {
          identity: currentQuestionProgressCache.identity,
          title: clean(currentLessonSource.title || currentLessonSource.name || "Space_Q"),
          currentIndex: Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0)),
          nodeIndex: Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0)),
          nodePointer: Math.max(1, Math.floor(Number(questionNodePointer || currentNodeIndex + 1) || 1)),
          nodeCount: questionNodes.length,
          queue: Array.isArray(questionQueue) ? questionQueue.slice() : [],
          questionIndex: Math.max(0, Math.floor(Number(questionQuestionIndex || 0) || 0)),
          questionOrder: Array.isArray(questionCurrentQuestionOrder) ? questionCurrentQuestionOrder.slice() : [],
          questionCount: Array.isArray(questionCurrentQuestions) ? questionCurrentQuestions.length : 0,
          questionDone,
          questionTotal,
          recursiveQuestionDone: Math.max(0, Math.floor(Number(progressStats.completedQuestions || 0) || 0)),
          recursiveQuestionTotal: Math.max(0, Math.floor(Number(progressStats.totalQuestions || 0) || 0)),
          directQuestionDone: Math.max(0, Math.floor(Number(progressStats.completedDirectQuestions || 0) || 0)),
          directQuestionTotal: Math.max(0, Math.floor(Number(progressStats.totalDirectQuestions || 0) || 0)),
          firstTryCorrect: Math.max(0, questionFirstTryCorrectKeys.size),
          firstTryAnswered: Math.max(0, questionFirstTryAnsweredKeys.size),
          completedNodes: progressStats.completedNodes,
          totalNodes: progressStats.totalNodes,
          reviewing: Boolean(questionReviewRunActive),
          reviewRun: Boolean(questionReviewRunActive),
          activeRun: Boolean(!questionReviewRunActive && !questionComplete),
          runId: questionActiveRunId,
          complete: questionComplete,
          lessonComplete: questionComplete,
          wrongAttempts: Math.max(0, Math.floor(Number(questionWrongAttempts || 0) || 0)),
          feedback: qFeedback ? qFeedback.textContent : "",
          savedAt: new Date().toISOString(),
          lessonSource: { ...(currentLessonSource || {}) },
        };
      };

      // Added 2026-07-20: animation/reveal callbacks must not POST identical Space_Q checkpoints repeatedly.
      const questionProgressSemanticSignature = (snapshot = {}) => JSON.stringify([
        clean(snapshot.identity || ""),
        clean(snapshot.runId || ""),
        Math.max(0, Math.floor(Number(snapshot.currentIndex || 0) || 0)),
        Math.max(0, Math.floor(Number(snapshot.nodePointer || 0) || 0)),
        Array.isArray(snapshot.queue) ? snapshot.queue : [],
        Math.max(0, Math.floor(Number(snapshot.questionIndex || 0) || 0)),
        Array.isArray(snapshot.questionOrder) ? snapshot.questionOrder : [],
        Math.max(0, Math.floor(Number(snapshot.wrongAttempts || 0) || 0)),
        Math.max(0, Math.floor(Number(snapshot.questionDone || 0) || 0)),
        Math.max(0, Math.floor(Number(snapshot.questionTotal || 0) || 0)),
        Math.max(0, Math.floor(Number(snapshot.completedNodes || 0) || 0)),
        Math.max(0, Math.floor(Number(snapshot.totalNodes || 0) || 0)),
        Boolean(snapshot.reviewing || snapshot.reviewRun),
        Boolean(snapshot.activeRun),
        Boolean(snapshot.complete || snapshot.lessonComplete),
      ]);

      const canSaveQuestionProgress = () => Boolean(
        currentQuestionProgressCache &&
        currentQuestionProgressCache.progressKey &&
        questionModeActive &&
        questionPayload &&
        questionNodes.length &&
        questionCurrentNode &&
        loadGate.classList.contains("is-hidden")
      );

      const saveQuestionProgressNow = () => {
        if (questionProgressSaveTimer) {
          window.clearTimeout(questionProgressSaveTimer);
          questionProgressSaveTimer = 0;
        }
        if (!canSaveQuestionProgress()) {
          return false;
        }
        const snapshot = questionProgressSnapshot();
        snapshot.syncOperationId = createQuestionProgressOperationId();
        const semanticSignature = questionProgressSemanticSignature(snapshot);
        if (
          semanticSignature === questionProgressLastSemanticSignature
          && currentQuestionProgressCache.savedProgress
          && currentQuestionProgressCache.savedProgress.state
        ) {
          return currentQuestionProgressCache.savedProgress;
        }
        const record = {
          version: 1,
          identity: currentQuestionProgressCache.identity,
          savedAt: snapshot.savedAt,
          title: snapshot.title,
          nodeIndex: snapshot.currentIndex,
          nodeCount: questionNodes.length,
          runId: snapshot.runId,
          syncOperationId: snapshot.syncOperationId,
          activeRun: Boolean(snapshot.activeRun),
          reviewing: Boolean(snapshot.reviewing || snapshot.reviewRun),
          reviewRun: Boolean(snapshot.reviewing || snapshot.reviewRun),
          complete: Boolean(snapshot.complete),
          lessonComplete: Boolean(snapshot.lessonComplete),
          pendingServerSync: true,
          state: snapshot,
        };
        const ok = writeSpaceWJson(currentQuestionProgressCache.progressKey, record);
        if (ok) {
          questionProgressLastSemanticSignature = semanticSignature;
          currentQuestionProgressCache.savedProgress = record;
          updateQuestionProgressButtons();
          if (typeof questionProgressOverrideFromRecord === "function") {
            const progressOverride = questionProgressOverrideFromRecord(record);
            if (progressOverride) {
              const progressPaths = typeof currentQuestionProgressPaths === "function"
                ? currentQuestionProgressPaths(record)
                : [currentLessonSource && currentLessonSource.path].map((path) => normalizeServerPathValue(path || "")).filter(Boolean);
              setLessonProgressOverride(progressPaths, progressOverride, 120000);
              if (typeof rememberLessonVaultProgressPin === "function") {
                rememberLessonVaultProgressPin(progressPaths, progressOverride, 120000);
              }
              if (typeof pinVisibleLessonVaultProgressRing === "function") {
                pinVisibleLessonVaultProgressRing(progressPaths, progressOverride, { retryMs: 120 });
              }
              if (typeof clearLessonProgressDisplayCaches === "function") {
                clearLessonProgressDisplayCaches(progressPaths, "Space_Q");
              }
            }
          }
        }
        queueQuestionServerProgressSync(record, 0);
        return ok ? record : null;
      };

      const queueQuestionProgressSave = (delayMs = 250) => {
        if (!canSaveQuestionProgress()) {
          return;
        }
        if (questionProgressSaveTimer) {
          window.clearTimeout(questionProgressSaveTimer);
        }
        questionProgressSaveTimer = window.setTimeout(saveQuestionProgressNow, Math.max(40, Number(delayMs) || 250));
      };

      const requestRealFullscreen = async () => {
        if (!isPopupFullscreenMode()) {
          return false;
        }
        if (isMobileVoicePicker()) {
          return false;
        }
        if (document.fullscreenElement || !document.documentElement.requestFullscreen) {
          return Boolean(document.fullscreenElement);
        }
        try {
          await document.documentElement.requestFullscreen({ navigationUI: "hide" });
          return true;
        } catch (error) {
          // Fullscreen requires a gesture in many browsers; the popup layout still fills the window.
          return false;
        }
      };

      const requestAnyFullscreen = async () => {
        if (document.fullscreenElement) {
          return true;
        }
        if (!document.documentElement.requestFullscreen) {
          return false;
        }
        try {
          await document.documentElement.requestFullscreen({ navigationUI: "hide" });
          return true;
        } catch (error) {
          return false;
        }
      };

      const hideStartFullscreenGate = () => {
        if (startFullscreenGate) {
          startFullscreenGate.classList.add("is-hidden");
        }
        window.setTimeout(syncAuthPasswordFocusMotion, 0);
      };

      const showStartFullscreenGate = () => {
        if (startFullscreenGate) {
          startFullscreenGate.classList.remove("is-hidden");
        }
        syncAuthPasswordFocusMotion();
      };

      const shouldShowStartFullscreenGate = () => {
        return false;
      };

      const shouldShowMobileLogoutFullscreenGate = () => {
        if (!shouldShowStartFullscreenGate()) {
          return false;
        }
        return window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
      };

      const showMobileLogoutFullscreenGate = () => {
        if (!shouldShowMobileLogoutFullscreenGate()) {
          return;
        }
        showStartFullscreenGate();
        window.setTimeout(() => {
          if (startFullscreenMain && typeof startFullscreenMain.focus === "function") {
            startFullscreenMain.focus({ preventScroll: true });
          }
        }, 80);
      };

      const startClientFullscreen = async () => {
        const opened = await requestAnyFullscreen();
        hideStartFullscreenGate();
        setFullscreenStatus(
          opened
            ? "Da mo fullscreen tren may khach."
            : "Trinh duyet khong cho fullscreen tu dong. Trang van dang hien thi tran man hinh.",
          false,
        );
      };

      const installPopupFullscreenGesture = () => {
        if (!isPopupFullscreenMode() || isMobileVoicePicker()) {
          return;
        }
        let installed = true;
        const removeGestureListeners = () => {
          if (!installed) {
            return;
          }
          installed = false;
          window.removeEventListener("pointerdown", trigger, true);
          window.removeEventListener("keydown", trigger, true);
          window.removeEventListener("touchstart", trigger, true);
        };
        const trigger = (event) => {
          const target = event && event.target;
          if (target && target.closest && target.closest("button,input,select,textarea,label")) {
            removeGestureListeners();
            return;
          }
          void requestRealFullscreen();
          removeGestureListeners();
        };
        window.addEventListener("pointerdown", trigger, true);
        window.addEventListener("keydown", trigger, true);
        window.addEventListener("touchstart", trigger, true);
        window.setTimeout(() => {
          positionConnector();
        }, 700);
      };

      const serializeBootstrapState = (state) => JSON.stringify(state || {})
        .replace(/</g, "\\u003c")
        .replace(/\u2028/g, "\\u2028")
        .replace(/\u2029/g, "\\u2029");

      const stripBootstrapScripts = (html) => String(html || "")
        .replace(/^\s*<!doctype[^>]*>\s*/i, "")
        .replace(/<script\b[^>]*id=["']ft-bootstrap-state["'][^>]*>[\s\S]*?<\/script>\s*/gi, "");

      const addPopupClassToHtml = (html) => String(html || "").replace(/<html\b([^>]*)>/i, (match, attrs) => {
        const safeAttrs = /\stranslate\s*=/.test(attrs) ? attrs : `${attrs} translate="no"`;
        const hasClass = /\sclass\s*=/.test(safeAttrs);
        if (!hasClass) {
          return `<html${safeAttrs} class="ft-popup-fullscreen notranslate">`;
        }
        return `<html${safeAttrs.replace(/\sclass=(["'])(.*?)\1/i, (classMatch, quote, classes) => {
          const classList = clean(`${classes} ft-popup-fullscreen notranslate`).split(/\s+/).filter(Boolean);
          return ` class=${quote}${Array.from(new Set(classList)).join(" ")}${quote}`;
        })}>`;
      });

      const insertBootstrapMarker = (html, snapshot) => {
        const markerScript = `<script id="ft-bootstrap-state">window.__FTG_BOOTSTRAP__=${serializeBootstrapState(snapshot)};window.__FTG_AWAIT_BOOTSTRAP__=false;<\\/script>`;
        return String(html || "").replace("<script>", `${markerScript}\n<script>`);
      };

      const childWindowHtml = (snapshot) => {
        const cleanHtml = addPopupClassToHtml(stripBootstrapScripts(runtimeHtmlSource));
        return insertBootstrapMarker(cleanHtml, snapshot);
      };

      const shouldUseStandalonePopupRuntime = () => {
        const host = clean(window.location.hostname).toLowerCase();
        const path = clean(window.location.pathname).toLowerCase();
        const href = clean(window.location.href).toLowerCase();
        return host.includes("googleusercontent.com") ||
          path.includes("inner-frame-minified.html") ||
          path.includes("/embeds/") ||
          href.includes("inner-frame-minified.html");
      };

      const writeChildHtml = (child, html) => {
        child.document.open();
        child.document.write(html);
        child.document.close();
      };

      const popupRuntimeUrl = (stateKey = "") => {
        const url = new URL(window.location.href);
        url.searchParams.set("ft_popup", "1");
        url.searchParams.set("cb", String(Date.now()));
        if (stateKey) {
          url.searchParams.set("ft_state_key", stateKey);
          url.searchParams.set("ft_await", "1");
        } else {
          url.searchParams.delete("ft_state_key");
          url.searchParams.delete("ft_await");
        }
        return url.href;
      };

      const escapeHtmlAttr = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      const aboutBlankLoaderShellHtml = (url) => `<!doctype html>
<html lang="vi" translate="no" class="notranslate">
<head>
  <meta charset="utf-8">
  <meta name="google" content="notranslate">
  <meta name="googlebot" content="notranslate">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Future Fullscreen</title>
  <style>
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: #071112;
    }
    iframe {
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      height: 100dvh;
      border: 0;
      background: #071112;
    }
    a {
      position: fixed;
      left: 12px;
      bottom: 12px;
      z-index: 2;
      padding: 10px 12px;
      border: 1px solid rgba(70, 240, 215, 0.35);
      border-radius: 12px;
      background: rgba(3, 13, 14, 0.74);
      color: #effefa;
      font: 800 12px "Segoe UI", Arial, sans-serif;
      text-decoration: none;
    }
  </style>
</head>
<body translate="no" class="notranslate">
  <iframe src="${escapeHtmlAttr(url)}" allow="fullscreen; autoplay"></iframe>
  <a href="${escapeHtmlAttr(url)}">Mở trực tiếp</a>
</body>
</html>`;

      const fullscreenWindowFeatures = () => {
        const screenWidth = Math.max(screen.availWidth || 0, screen.width || 0, window.outerWidth || 0, 1024);
        const screenHeight = Math.max(screen.availHeight || 0, screen.height || 0, window.outerHeight || 0, 768);
        return {
          screenWidth,
          screenHeight,
          features: [
            "popup=yes",
            "fullscreen=yes",
            "toolbar=no",
            "location=no",
            "menubar=no",
            "scrollbars=yes",
            "resizable=yes",
            "left=0",
            "top=0",
            `width=${screenWidth}`,
            `height=${screenHeight}`,
          ].join(","),
        };
      };

      const setFullscreenStatus = (message, isError = false) => {
        if (!loadGate.classList.contains("is-hidden")) {
          setLoadStatus(message, isError);
        } else {
          setTtsStatus(message, isError);
        }
      };

      const googleSitesHostUrl = () => {
        const current = clean(window.location.href);
        const referrer = clean(document.referrer);
        const isHttp = (value) => /^https?:\/\//i.test(value);
        try {
          const ref = referrer && new URL(referrer);
          if (ref && ref.hostname.includes("sites.google.com")) {
            ref.searchParams.set("ft_fullscreen_window", "1");
            ref.searchParams.set("cb", String(Date.now()));
            return ref.href;
          }
        } catch (error) {
        }
        try {
          const cur = current && new URL(current);
          if (cur && cur.hostname.includes("sites.google.com")) {
            cur.searchParams.set("ft_fullscreen_window", "1");
            cur.searchParams.set("cb", String(Date.now()));
            return cur.href;
          }
        } catch (error) {
        }
        return isHttp(referrer) ? referrer : current;
      };

      const openGoogleSitesWindowFullscreen = () => {
        const { screenWidth, screenHeight, features } = fullscreenWindowFeatures();
        const url = googleSitesHostUrl();
        const child = window.open(url, "_blank", features);
        if (!child) {
          setFullscreenStatus("Popup bi chan. Hay cho phep popup de mo cua so fullscreen.", true);
          return null;
        }
        try {
          child.moveTo(0, 0);
          child.resizeTo(screenWidth, screenHeight);
        } catch (error) {
          // Browsers may ignore window sizing, but the page still opens in its own tab/window.
        }
        try {
          child.focus();
        } catch (error) {
        }
          setFullscreenStatus("Da mo cua so Google Sites rieng. Hay chon goi bai hoc trong cua so moi.", false);
        return child;
      };

      const activateEmbeddedFocusFullscreen = async () => {
        document.documentElement.classList.add("ft-popup-fullscreen");
        let opened = false;
        try {
          if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
            await document.documentElement.requestFullscreen({ navigationUI: "hide" });
            opened = true;
          }
        } catch (error) {
          opened = false;
        }
        setFullscreenStatus(
          opened
            ? "Đã mở fullscreen trực tiếp trong Google Sites."
            : "Đã chuyển sang chế độ học trực tiếp trong Google Sites. Chọn gói bài học để vào học.",
          false,
        );
        window.setTimeout(() => {
          updateDesktopPanelLayout();
          positionConnector();
        }, 140);
      };

      const openPopupLoaderFullscreen = () => {
        if (shouldUseStandalonePopupRuntime()) {
          return openGoogleSitesWindowFullscreen();
        }
        const { screenWidth, screenHeight, features } = fullscreenWindowFeatures();
        const child = window.open("about:blank", "_blank", features);
        if (!child) {
          setFullscreenStatus("Popup bi chan. Hay cho phep popup de mo fullscreen.", true);
          return null;
        }
        const runtimeUrl = popupRuntimeUrl();
        const useStandalone = shouldUseStandalonePopupRuntime();
        const html = useStandalone
          ? `<!doctype html>\n${childWindowHtml({ popupFullscreen: true, loadHidden: false, nodes: [] })}`
          : aboutBlankLoaderShellHtml(runtimeUrl);
        let wroteAboutBlank = false;
        try {
          writeChildHtml(child, html);
          wroteAboutBlank = true;
        } catch (error) {
          wroteAboutBlank = false;
        }
        if (!wroteAboutBlank) {
          if (useStandalone) {
            setFullscreenStatus("Khong tao duoc cua so fullscreen doc lap trong Google Sites.", true);
          } else {
            try {
              child.location.replace(runtimeUrl);
            } catch (error) {
              setFullscreenStatus("Khong tao duoc cua so fullscreen rieng.", true);
            }
          }
        }
        try {
          child.moveTo(0, 0);
          child.resizeTo(screenWidth, screenHeight);
        } catch (error) {
          // Browsers can block moving/resizing tabs; CSS still fills the available viewport.
        }
        child.focus();
        return child;
      };

      const openAboutBlankFullscreen = () => {
        if (!loadGate.classList.contains("is-hidden")) {
          openPopupLoaderFullscreen();
          return;
        }
        const snapshot = { ...runtimeSnapshot(), popupFullscreen: true };
        const useStandalone = shouldUseStandalonePopupRuntime();
        if (useStandalone) {
          openGoogleSitesWindowFullscreen();
          return;
        }
        const serializedSnapshot = serializeBootstrapState(snapshot);
        const stateKey = `ftg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        let runtimeUrl = "";
        try {
          if (window.sessionStorage) {
            window.sessionStorage.setItem(stateKey, serializedSnapshot);
          }
          if (window.localStorage) {
            window.localStorage.setItem(stateKey, serializedSnapshot);
          }
          runtimeUrl = popupRuntimeUrl(stateKey);
          window.setTimeout(() => {
            try {
              if (window.sessionStorage) {
                window.sessionStorage.removeItem(stateKey);
              }
              if (window.localStorage) {
                window.localStorage.removeItem(stateKey);
              }
            } catch (error) {
              // The popup normally removes this after reading it.
            }
          }, 60000);
        } catch (error) {
          runtimeUrl = popupRuntimeUrl(stateKey);
        }
        const { screenWidth, screenHeight, features } = fullscreenWindowFeatures();
        const child = window.open("about:blank", "_blank", features);
        if (!child) {
          setFullscreenStatus("Popup bi chan. Hay cho phep popup de mo man hinh rieng.", true);
          return;
        }
        let acknowledged = false;
        let attempts = 0;
        let retryTimer = 0;
        try {
          child.__FTG_PENDING_BOOTSTRAP__ = snapshot;
          child.name = `${WINDOW_BOOTSTRAP_PREFIX}${serializedSnapshot}`;
        } catch (error) {
          // postMessage below is still the main transport.
        }
        const sendSnapshot = () => {
          if (acknowledged || child.closed) {
            if (retryTimer) {
              window.clearInterval(retryTimer);
            }
            window.removeEventListener("message", handleChildMessage);
            return;
          }
          attempts += 1;
          try {
            child.postMessage({ type: "FTG_BOOTSTRAP_STATE", state: snapshot }, "*");
          } catch (error) {
            setTtsStatus("Khong gui duoc du lieu sang cua so fullscreen.", true);
          }
          if (attempts >= 18 && retryTimer) {
            window.clearInterval(retryTimer);
            retryTimer = 0;
          }
        };
        const handleChildMessage = (event) => {
          if (event.source !== child || !event.data || typeof event.data !== "object") {
            return;
          }
          if (event.data.type === "FTG_CHILD_READY") {
            sendSnapshot();
          } else if (event.data.type === "FTG_BOOTSTRAP_ACK") {
            acknowledged = true;
            if (retryTimer) {
              window.clearInterval(retryTimer);
              retryTimer = 0;
            }
            window.removeEventListener("message", handleChildMessage);
          }
        };
        window.addEventListener("message", handleChildMessage);
        let navigatedToRuntime = false;
        try {
          child.location.replace(runtimeUrl);
          navigatedToRuntime = true;
        } catch (error) {
          navigatedToRuntime = false;
        }
        if (!navigatedToRuntime) {
          try {
            writeChildHtml(child, aboutBlankLoaderShellHtml(runtimeUrl));
          } catch (error) {
            setTtsStatus("Khong mo duoc cua so fullscreen bang URL that.", true);
          }
        }
        try {
          child.__FTG_PENDING_BOOTSTRAP__ = snapshot;
          child.name = `${WINDOW_BOOTSTRAP_PREFIX}${serializedSnapshot}`;
        } catch (error) {
          // Some mobile browsers only allow postMessage after the new tab owns focus.
        }
        try {
          child.moveTo(0, 0);
          child.resizeTo(screenWidth, screenHeight);
        } catch (error) {
          // Browsers can block moving/resizing tabs; CSS still fills the available viewport.
        }
        child.focus();
        window.setTimeout(sendSnapshot, 80);
        retryTimer = window.setInterval(sendSnapshot, 420);
      };

      const toggleFullscreen = async () => {
        if (document.fullscreenElement && document.exitFullscreen) {
          await document.exitFullscreen();
          return;
        }
        if (shouldUseStandalonePopupRuntime() && !isPopupFullscreenMode()) {
          openGoogleSitesWindowFullscreen();
          return;
        }
        if (isPopupFullscreenMode()) {
          if (isMobileVoicePicker()) {
            setFullscreenStatus("Day da la cua so hoc rieng, hay chon goi bai hoc o day.", false);
            return;
          }
          const opened = await requestRealFullscreen();
          if (!opened) {
            setFullscreenStatus("Trinh duyet khong cho fullscreen that, nhung cua so nay da la ban mo rieng.", false);
          }
          return;
        }
        if (isMobileVoiceList() && !loadGate.classList.contains("is-hidden")) {
          openPopupLoaderFullscreen();
          return;
        }
        try {
          if (!document.documentElement.requestFullscreen) {
            throw new Error("Fullscreen API unavailable.");
          }
          await document.documentElement.requestFullscreen({ navigationUI: "hide" });
        } catch (error) {
          openAboutBlankFullscreen();
        }
      };

      const applyRuntimeState = (state) => {
        if (!state || !Array.isArray(state.nodes) || !state.nodes.length) {
          return false;
        }
        stopActiveAudio();
        bootstrapState = state;
        lessonNodes = state.nodes;
        lessonEffects = normalizeEffectSounds(state.effects || state.sounds || state.fx || lessonEffects);
        if (state.spaceWCache && typeof state.spaceWCache === "object" && state.spaceWCache.identity) {
          const voiceKey = spaceWGlobalVoiceStorageKey();
          const preferredVoice = normalizeSpaceWVoiceRecord(spaceWVoicePreference);
          const savedVoice = readGlobalSpaceWVoiceRecord() || (preferredVoice.value ? preferredVoice : null) || defaultSpaceWVoiceRecord();
          currentSpaceWCache = {
            identity: clean(state.spaceWCache.identity),
            progressKey: clean(state.spaceWCache.progressKey),
            voiceKey,
            voiceValue: clean(savedVoice && savedVoice.value),
            voiceLabel: clean(savedVoice && savedVoice.label),
            voiceApplied: false,
            savedProgress: currentSpaceWCache.savedProgress || null,
          };
          updateSpaceWReviewButton();
        }
        spaceWNodeProgress = state.nodeProgress && typeof state.nodeProgress === "object" ? { ...state.nodeProgress } : {};
        reviewModeActive = Boolean(state.reviewModeActive);
        reviewQueue = Array.isArray(state.reviewQueue) ? state.reviewQueue.map((item) => Math.max(0, Number(item) || 0)).filter((item) => item < lessonNodes.length) : [];
        reviewMasteredIndexes = new Set(Array.isArray(state.reviewMastered) ? state.reviewMastered.map((item) => Math.max(0, Number(item) || 0)).filter((item) => item < lessonNodes.length) : []);
        reviewCurrentHadError = Boolean(state.reviewCurrentHadError);
        const restoredSpeakSkipWasTemporary = Boolean(state.spaceWSpeakSkipSessionApproved);
        spaceWSpeakSkipSessionApproved = false;
        reviewSpeakCompleted = restoredSpeakSkipWasTemporary ? false : Boolean(state.reviewSpeakCompleted);
        reviewFinished = Boolean(state.reviewFinished);
        spaceWActiveRunId = clean(state.runId || state.run_id || spaceWActiveRunId) || `space-w-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
        const restoredTrainCount = lessonNodes.filter((node) => isSpaceWTrainingNode(node)).length;
        spaceWTrainModeLocked = Boolean(state.spaceWTrainModeLocked || restoredTrainCount);
        spaceWTrainModeExpanded = Boolean(state.spaceWTrainModeExpanded || restoredTrainCount);
        spaceWTrainModeRootCount = Math.max(
          0,
          Math.floor(Number(state.spaceWTrainModeRootCount) || 0) || lessonNodes.filter((node) => !isSpaceWTrainingNode(node)).length,
        );
        spaceWTrainModeBatch = Math.max(0, Math.floor(Number(state.spaceWTrainModeBatch) || 0));
        spaceWTrainModeBuffer = [];
        spaceWTrainModeOriginalCount = spaceWTrainModeExpanded ? spaceWTrainModeRootCount : 0;
        currentLessonSource = state.lessonSource && typeof state.lessonSource === "object"
          ? { ...state.lessonSource }
          : currentLessonSource;
        lessonCompletionSent = Boolean(state.lessonCompletionSent);
        loadGate.classList.toggle("is-hidden", Boolean(state.loadHidden));
        const index = Math.max(0, Math.min(lessonNodes.length - 1, Number(state.index || 0)));
        setNode(lessonNodes[index], index);
        aboutUnlockedForCurrentNode = Boolean(state.aboutUnlocked || state.aboutLive);
        syncHintAboutSwitchButtons();
        reviewCurrentHadError = Boolean(state.reviewCurrentHadError);
        reviewSpeakCompleted = restoredSpeakSkipWasTemporary ? false : Boolean(state.reviewSpeakCompleted);
        answerInput.value = clean(state.input || "");
        wordHintedKeys = new Set(Array.isArray(state.wordHintedKeys)
          ? state.wordHintedKeys.map((item) => clean(item)).filter(Boolean)
          : []);
        if (clean(answerInput.value)) {
          hideHintPanel();
        }
        updateLiveScoring(false);
        completedListenCount = Math.max(0, Math.min(IPA_STAR_FULL_LISTENS, Number(state.listenCount || 0) || 0));
        renderIpaStars();
        nextPanelCanShow = Boolean(state.nextPanelCanShow);
        speakStepCompleted = restoredSpeakSkipWasTemporary ? false : Boolean(state.speakStepCompleted);
        speakStarCount = Math.max(0, Math.min(5, Number(state.speakStarCount || 0) || 0));
        renderSpeakStars();
        grammarStepCompleted = Boolean(state.grammarStepCompleted);
        if (nextPanelCanShow || answerInput.disabled || grammarState.active) {
          stopWordHintWatch();
        } else {
          scheduleWordHintWatch(scoreInputWords(answerInput.value));
        }
        voiceHint = clean(state.voiceHint || state.selectedVoice || voiceHint);
        loadVoices();
        const appliedGlobalVoice = applyCachedSpaceWVoice(true);
        const selectedVoice = appliedGlobalVoice ? "" : clean(state.selectedVoice);
        if (selectedVoice && Array.from(voiceSelect.options).some((option) => option.value === selectedVoice)) {
          voiceSelect.value = selectedVoice;
        }
        updateVoiceSelectTone();
        refreshIpaForAccent(selectedVoiceAccent());
        const restoreUnlockedPanels = () => {
          if (state.aboutLive) {
            showAboutPanel(currentNode, false);
            if (aboutItems.length) {
              renderAboutItem(Math.max(0, Number(state.aboutIndex || 0) || 0));
            }
          }
          if (state.speakLive) {
            showSpeakPanel(false);
          }
          if (state.grammarLive && grammarStepCompleted && grammarPanel) {
            grammarPanel.classList.add("is-live", "is-locked");
            revealMobilePanel("grammar");
          }
          restoreMobilePanelTabs(state);
        };
        // 2026-07-23: a checkpoint can save after listening while the card is hidden;
        // restore the Listen card whenever Speak is still incomplete.
        const restorePendingListenCard = Boolean(
          nextPanelCanShow
          && !speakStepCompleted
          && !state.grammarLive
        );
        if (state.ipaLive || restorePendingListenCard) {
          revealIpa(clean(state.feedback) || "Ready.");
          window.setTimeout(restoreUnlockedPanels, CONNECTOR_DRAW_MS + 80);
        } else {
          restoreUnlockedPanels();
        }
        if (!state.deferInitialProgressSave) {
          queueSpaceWProgressSave(120);
        }
        try {
          window.__FTG_PENDING_BOOTSTRAP__ = null;
          if (window.opener && window.opener !== window) {
            window.opener.postMessage({ type: "FTG_BOOTSTRAP_ACK" }, "*");
          }
        } catch (error) {
          // The parent can disappear after opening; the lesson is already loaded.
        }
        return true;
      };

      const applyBootstrapState = () => applyRuntimeState(bootstrapState);

      const loadSampleLesson = () => {
        lessonNodes = [
          {
            vi: question,
            en: answer,
            ipa,
            ipa_us: "/aɪ wʊd laɪk ə ɡlæs əv ˈwɔtər/",
            ipa_uk: "/aɪ wʊd laɪk ə ɡlɑːs əv ˈwɔːtə/",
            voice: "sot:en-US",
            tokens: [
              { text: "I", start: 0, end: 1, ipa: "aɪ", ipa_us: "aɪ", ipa_uk: "aɪ" },
              { text: "would", start: 2, end: 7, ipa: "wʊd", ipa_us: "wʊd", ipa_uk: "wʊd" },
              { text: "like", start: 8, end: 12, ipa: "laɪk", ipa_us: "laɪk", ipa_uk: "laɪk" },
              { text: "a", start: 13, end: 14, ipa: "ə", ipa_us: "ə", ipa_uk: "ə" },
              { text: "glass", start: 15, end: 20, ipa: "ɡlæs", ipa_us: "ɡlæs", ipa_uk: "ɡlɑːs" },
              { text: "of", start: 21, end: 23, ipa: "əv", ipa_us: "əv", ipa_uk: "əv" },
              { text: "water", start: 24, end: 29, ipa: "ˈwɔtər", ipa_us: "ˈwɔtər", ipa_uk: "ˈwɔːtə" },
            ],
            scoring: [
              { t: "I", n: "i", p: "PRON", d: "nsubj", h: "like" },
              { t: "would", n: "would", p: "AUX", d: "aux", h: "like" },
              { t: "like", n: "like", p: "VERB", d: "ROOT", h: "like" },
              { t: "a", n: "a", p: "DET", d: "det", h: "glass" },
              { t: "glass", n: "glass", p: "NOUN", d: "obj", h: "like" },
              { t: "of", n: "of", p: "ADP", d: "prep", h: "glass" },
              { t: "water", n: "water", p: "NOUN", d: "pobj", h: "of" },
            ],
          },
        ];
        resetSpaceWTrainMode();
        reviewModeActive = false;
        reviewQueue = [];
        reviewMasteredIndexes = new Set();
        reviewCurrentHadError = false;
        reviewSpeakCompleted = false;
        reviewFinished = false;
        loadGate.classList.add("is-hidden");
        setNode(lessonNodes[0], 0);
      };

      const nextReviewIndex = () => {
        if (!reviewQueue.length) {
          return -1;
        }
        const position = Math.floor(Math.random() * reviewQueue.length);
        const [index] = reviewQueue.splice(position, 1);
        return Number(index);
      };

      const setNextReviewNode = () => {
        const index = nextReviewIndex();
        if (index < 0 || !lessonNodes[index]) {
          reviewModeActive = false;
          reviewFinished = true;
          reviewQueue = [];
          updateNextButton(false);
          setPlaybackState(false, "Đã hoàn thành toàn bộ vòng ôn.");
          feedbackNode.textContent = "Hoàn thành: tất cả node đã đúng liên tục không lỗi.";
          feedbackNode.classList.remove("is-error");
          feedbackNode.classList.add("is-ok");
          saveSpaceWProgressNow();
          showCompletionGate();
          void reportLessonCompleted("review_complete");
          return;
        }
        setNode(lessonNodes[index], index);
        feedbackNode.textContent = `Vòng ôn: nhập tiếng Anh thật sạch, nghe 1 lần rồi Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}%.`;
      };

      const beginReviewMode = () => {
        reviewModeActive = true;
        reviewFinished = false;
        reviewMasteredIndexes = new Set();
        reviewQueue = shuffleIndexes(lessonNodes.length);
        reviewCurrentHadError = false;
        reviewSpeakCompleted = false;
        // Added 2026-07-24: persist the stage-2 flag atomically with the
        // checkpoint; a stage-1-only snapshot must never resemble completion.
        saveSpaceWProgressNow();
        setNextReviewNode();
      };

      const goNextNode = () => {
        saveSpaceWProgressNow();
        if (isReviewPhase()) {
          if (completedListenCount < requiredListenCount()) {
            setPlaybackState(false, listenStatusText());
            return;
          }
          if (!reviewSpeakCompleted) {
          setPlaybackState(false, listenStatusText() || `Hãy Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}% trước khi Next.`);
            showSpeakPanel(true);
            return;
          }
          if (reviewCurrentHadError) {
            reviewQueue.push(currentNodeIndex);
          } else {
            reviewMasteredIndexes.add(currentNodeIndex);
          }
          setNextReviewNode();
          return;
        }
        if (currentNodeIndex >= lessonNodes.length - 1) {
          if (completedListenCount < requiredListenCount()) {
            setPlaybackState(false, listenStatusText() || `Cần nghe hết câu tiếng Anh ${requiredListenCount()} lần trước khi Next.`);
            return;
          }
          if (!speakStepCompleted) {
            setPlaybackState(false, listenStatusText() || `Hãy Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}% trước khi Next.`);
            showSpeakPanel(true);
            return;
          }
          if (recordSpaceWTrainModeNodeComplete({ flushAtLessonEnd: true })) {
            setNode(lessonNodes[currentNodeIndex + 1], currentNodeIndex + 1);
            return;
          }
          if (completedListenCount >= requiredListenCount() && reviewCanStart()) {
            beginReviewMode();
            return;
          }
          setPlaybackState(false, "Đã hết node trong bài.");
          return;
        }
        if (completedListenCount < REQUIRED_FULL_LISTENS) {
          setPlaybackState(false, listenStatusText() || `Cần nghe hết câu tiếng Anh ${REQUIRED_FULL_LISTENS} lần trước khi Next.`);
          return;
        }
        if (!speakStepCompleted) {
          setPlaybackState(false, listenStatusText() || `Hãy Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}% trước khi Next.`);
          showSpeakPanel(true);
          return;
        }
        if (recordSpaceWTrainModeNodeComplete()) {
          setNode(lessonNodes[currentNodeIndex + 1], currentNodeIndex + 1);
          return;
        }
        setNode(lessonNodes[currentNodeIndex + 1], currentNodeIndex + 1);
      };

      const isCurrentSpaceWAnswerComplete = (result = null) => {
        const typed = normalize(answerInput.value);
        if (!typed) {
          return false;
        }
        if (!accepted.length) {
          const visibleAnswer = normalize(englishNode.textContent);
          if (visibleAnswer) {
            accepted.push(visibleAnswer);
          }
        }
        return Boolean(accepted.includes(typed) || (result && result.complete));
      };

      const spaceWCupConfig = (variant = "gold") => (variant === "iron"
        ? {
            id: "space_w_cup_iron",
            name: "Silver Practice Cup",
            use: "Earned by correctly recalling a Space_W sentence during review.",
          }
        : {
            id: "space_w_cup_gold",
            name: "Golden Mastery Cup",
            use: "Earned when a new Space_W sentence is answered correctly the first time.",
          });

      const spaceWCupRewardEventKey = (variant = "gold") => {
        const source = currentLessonSource || {};
        const node = currentNode || {};
        const raw = [
          clean(source.path || source.name || source.title || "space-w"),
          clean(node.id || node.en || node.e || `node-${currentNodeIndex + 1}`),
          currentNodeIndex,
          variant,
        ].join("|");
        return `space-w:${hashSpaceWText(raw)}`;
      };

      const awardSpaceWCupOnce = (variant = "gold") => {
        if (typeof awardInventoryItemOnce !== "function") {
          return false;
        }
        const tone = variant === "iron" ? "cupiron" : "cupgold";
        return awardInventoryItemOnce(spaceWCupRewardEventKey(variant), spaceWCupConfig(variant), answerInput, {
          tone,
          feedback: (awardedItem) => {
            if (feedbackNode) {
              feedbackNode.textContent = `Cup obtained: ${awardedItem.name}.`;
              feedbackNode.classList.remove("is-error");
              feedbackNode.classList.add("is-ok");
            }
          },
        });
      };

      const checkAnswer = (options = {}) => {
        scheduleTranslateCardPin(900, { force: true });
        const typed = normalize(answerInput.value);
        if (!accepted.length) {
          const visibleAnswer = normalize(englishNode.textContent);
          if (visibleAnswer) {
            accepted.push(visibleAnswer);
          }
        }
        if (!typed) {
          feedbackNode.textContent = "Hãy nhập câu tiếng Anh.";
          feedbackNode.classList.add("is-error");
          feedbackNode.classList.remove("is-ok");
          queueSpaceWProgressSave(100);
          scheduleTranslateCardPin(900, { force: true });
          return;
        }
        const scoreResult = options && options.scoreResult ? options.scoreResult : updateLiveScoring(true);
        if (accepted.includes(typed) || scoreResult.complete) {
          wrongAttempts = 0;
          if (isReviewPhase()) {
            if (!reviewCurrentHadError) {
              awardSpaceWCupOnce("iron");
            }
          } else {
            awardSpaceWCupOnce("gold");
          }
          const aboutShown = showAboutPanelAfterCorrect();
          if (isReviewPhase()) {
            revealIpa(reviewCurrentHadError
              ? "Đúng rồi, nhưng lượt này đã có lỗi nên node sẽ quay lại vòng ôn."
              : `Đúng sạch. Hãy nghe 1 lần rồi Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}%.`, { preferredPanel: aboutShown ? aboutPanel : null });
          } else {
            revealIpa("Dung cau. IPA da mo, tiep theo hay hoan thanh Speak scoring.", { preferredPanel: aboutShown ? aboutPanel : null });
          }
          if (aboutShown) {
            window.setTimeout(() => {
              if (currentNode && normalizeNodeAboutItems(currentNode).length) {
                showAboutPanelAfterCorrect();
              }
            }, CONNECTOR_DRAW_MS + 80);
          }
          scheduleTranslateCardPin(1500, { force: true });
          return;
        }
        if (isReviewPhase()) {
          reviewCurrentHadError = true;
          updateNextButton();
        }
        wrongAttempts += 1;
        if (wrongAttempts >= 3) {
          revealIpa("Sai 3 lần, mở IPA để ôn lại.");
          return;
        }
        feedbackNode.textContent = `Chưa đúng, thử lại nhé. (${wrongAttempts}/3)`;
        feedbackNode.classList.add("is-error");
        feedbackNode.classList.remove("is-ok");
        queueSpaceWProgressSave(100);
        scheduleTranslateCardPin(1100, { force: true });
      };

      const maybeAutoUnlockSpaceWAnswer = (result = null) => {
        if (nextPanelCanShow || !answerInput || answerInput.disabled || grammarState.active) {
          return false;
        }
        const scoreResult = result || scoreInputWords(answerInput.value);
        if (!isCurrentSpaceWAnswerComplete(scoreResult)) {
          return false;
        }
        checkAnswer({ scoreResult });
        return true;
      };

      if (checkButton) {
        checkButton.addEventListener("click", checkAnswer);
        checkButton.addEventListener("pointerup", (event) => {
          event.preventDefault();
          checkAnswer();
        });
        checkButton.addEventListener("touchend", (event) => {
          event.preventDefault();
          checkAnswer();
        }, { passive: false });
        checkButton.addEventListener("touchstart", (event) => {
          event.stopPropagation();
        }, { passive: true });
      }
      if (translationAboutButton) {
        translationAboutButton.addEventListener("click", openAboutFromTranslationNode);
      }
      playButton.addEventListener("click", playEnglish);
      nextButton.addEventListener("click", goNextNode);
      if (hintAboutToggle) {
        hintAboutToggle.addEventListener("click", switchHintToAbout);
      }
      if (aboutHintToggle) {
        aboutHintToggle.addEventListener("click", switchAboutToHint);
      }
      if (aboutPreviewButton) {
        aboutPreviewButton.addEventListener("click", () => {
          if (aboutItems.length) {
            renderAboutItem(aboutIndex - 1);
            updateAboutConnector(true);
          }
        });
      }
      if (aboutNextButton) {
        aboutNextButton.addEventListener("click", () => {
          if (aboutItems.length) {
            renderAboutItem(aboutIndex + 1);
            updateAboutConnector(true);
          }
        });
      }
      if (aboutTrainButton) {
        aboutTrainButton.addEventListener("click", enableSpaceWTrainMode);
      }
      const isMobileToolsSurface = () => true;

      const FT_TOOLS_STYLE_CLASSES = ["ft-tools-style-1", "ft-tools-style-2", "ft-tools-style-3", "ft-tools-style-4", "ft-tools-style-5", "ft-tools-style-wave"];
      const pickMobileToolsStyle = () => {
        const root = document.documentElement;
        root.classList.remove.apply(root.classList, FT_TOOLS_STYLE_CLASSES);
        root.classList.add("ft-tools-style-wave");
      };

      const setMobileToolsOpen = (open) => {
        const active = Boolean(open) && isMobileToolsSurface();
        if (active && !document.documentElement.classList.contains("ft-mobile-tools-open")) {
          pickMobileToolsStyle();
        }
        document.documentElement.classList.toggle("ft-mobile-tools-open", active);
        if (mobileToolsToggle) {
          mobileToolsToggle.classList.toggle("is-active", active);
          mobileToolsToggle.setAttribute("aria-expanded", active ? "true" : "false");
          mobileToolsToggle.setAttribute("aria-label", active ? "Hide tools" : "Show tools");
        }
      };

      const toggleMobileTools = () => {
        setMobileToolsOpen(!document.documentElement.classList.contains("ft-mobile-tools-open"));
      };

      let webRecordStream = null;
      let webRecordRecorder = null;
      let webRecordChunks = [];
      let webRecordStartedAt = 0;
      let webRecordTimer = 0;
      let webRecordMime = "";

      const mobileToolButtons = () => [mobileToolsToggle, chatButton, streamButton, screenButton, webRecordButton, adminScreenButton, paintButton, mobileAnimationButton, clearAudioCacheButton, speakSkipAdminButton, cursorButton, gameButton, portalButton, vaultButton, cupButton, workerToolbarButton, npcSwitchButton]
        .filter(Boolean);

      const eventInsideMobileTools = (event) => {
        const target = event && event.target;
        return Boolean(target && mobileToolButtons().some((button) => button.contains(target)));
      };

      const formatWebRecordElapsed = () => {
        const elapsed = Math.max(0, Math.floor((Date.now() - webRecordStartedAt) / 1000));
        const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const seconds = String(elapsed % 60).padStart(2, "0");
        return `${minutes}:${seconds}`;
      };

      const webRecordSetButton = (mode = "idle") => {
        if (!webRecordButton) {
          return;
        }
        const recording = mode === "recording";
        const selecting = mode === "selecting";
        webRecordButton.classList.toggle("is-recording", recording);
        webRecordButton.classList.toggle("is-selecting", selecting);
        webRecordButton.setAttribute("aria-pressed", recording ? "true" : "false");
        webRecordButton.setAttribute("aria-label", recording ? `Stop web recording ${formatWebRecordElapsed()}` : selecting ? "Choose screen to record" : "Record web screen");
        webRecordButton.title = recording ? `Recording ${formatWebRecordElapsed()} - click to stop and download` : selecting ? "Choose screen to record" : "Record web screen";
      };

      const webRecordPickMime = () => {
        if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") {
          return "";
        }
        return [
          "video/webm;codecs=vp9,opus",
          "video/webm;codecs=vp8,opus",
          "video/webm"
        ].find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
      };

      const requestWebRecordStream = async () => {
        try {
          return await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
        } catch (error) {
          const name = clean(error && error.name || "");
          if (/NotAllowedError|SecurityError|AbortError/i.test(name)) {
            throw error;
          }
          return await navigator.mediaDevices.getDisplayMedia({ video: true });
        }
      };

      const webRecordCleanup = () => {
        if (webRecordTimer) {
          window.clearInterval(webRecordTimer);
          webRecordTimer = 0;
        }
        if (webRecordStream) {
          try {
            webRecordStream.getTracks().forEach((track) => track.stop());
          } catch (error) {
          }
        }
        webRecordStream = null;
        webRecordRecorder = null;
        webRecordStartedAt = 0;
        webRecordMime = "";
        webRecordSetButton("idle");
      };

      const webRecordDownload = (blob) => {
        if (!blob || !blob.size) {
          setLoadStatus("No web recording data was saved.", true);
          return;
        }
        const extension = (webRecordMime || blob.type || "").includes("mp4") ? "mp4" : "webm";
        const stamp = new Date().toISOString().replace(/[:.]/g, "-");
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `future-web-record-${stamp}.${extension}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 30000);
        setLoadStatus("Web recording downloaded.");
      };

      const stopWebRecording = (reason = "user") => {
        if (!webRecordRecorder) {
          webRecordCleanup();
          return;
        }
        const recorder = webRecordRecorder;
        try {
          if (recorder.state !== "inactive" && typeof recorder.requestData === "function") {
            recorder.requestData();
          }
        } catch (error) {
        }
        try {
          if (recorder.state !== "inactive") {
            recorder.stop();
            setLoadStatus(reason === "track-ended" ? "Screen sharing ended. Saving recording..." : "Saving web recording...");
            return;
          }
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not stop web recording.", true);
        }
        webRecordCleanup();
      };

      const startWebRecording = async () => {
        if (!navigator.mediaDevices || typeof navigator.mediaDevices.getDisplayMedia !== "function" || !window.MediaRecorder) {
          setLoadStatus("This browser does not support web screen recording.", true);
          return;
        }
        webRecordSetButton("selecting");
        setLoadStatus("Choose the screen or browser tab to record.");
        try {
          const stream = await requestWebRecordStream();
          webRecordStream = stream;
          webRecordChunks = [];
          webRecordMime = webRecordPickMime();
          const recorder = webRecordMime ? new MediaRecorder(stream, { mimeType: webRecordMime }) : new MediaRecorder(stream);
          webRecordRecorder = recorder;
          recorder.addEventListener("dataavailable", (event) => {
            if (event && event.data && event.data.size > 0) {
              webRecordChunks.push(event.data);
            }
          });
          recorder.addEventListener("stop", () => {
            const type = webRecordMime || (webRecordChunks[0] && webRecordChunks[0].type) || "video/webm";
            const blob = new Blob(webRecordChunks, { type });
            webRecordDownload(blob);
            webRecordChunks = [];
            webRecordCleanup();
          }, { once: true });
          recorder.addEventListener("error", (event) => {
            const message = event && event.error && event.error.message ? event.error.message : "Web recording failed.";
            setLoadStatus(message, true);
            webRecordCleanup();
          });
          stream.getVideoTracks().forEach((track) => {
            track.addEventListener("ended", () => stopWebRecording("track-ended"), { once: true });
          });
          webRecordStartedAt = Date.now();
          recorder.start();
          webRecordSetButton("recording");
          webRecordTimer = window.setInterval(webRecordSetButton.bind(null, "recording"), 1000);
          setLoadStatus("Web recording started. Click the record button again to save.");
        } catch (error) {
          webRecordCleanup();
          setLoadStatus(error && error.message ? error.message : "Could not start web recording.", true);
        }
      };

      const toggleWebRecording = () => {
        if (webRecordRecorder && webRecordRecorder.state !== "inactive") {
          stopWebRecording("user");
          return;
        }
        void startWebRecording();
      };

      mobileTabButtons.forEach((button) => {
        button.addEventListener("click", () => toggleMobilePanel(button.dataset.panel || ""));
      });
      fullscreenButton.addEventListener("click", toggleFullscreen);
      if (pdfCompactToggle) {
        pdfCompactToggle.hidden = false;
        pdfCompactToggle.setAttribute("aria-hidden", "false");
        pdfCompactToggle.classList.add("is-visible");
        pdfCompactToggle.addEventListener("click", () => {
          if (pdfModeActive && typeof setPdfCompactToolbar === "function") {
            setPdfCompactToolbar(!pdfCompactToolbarEnabled);
          }
        });
      }
      if (pdfCompactPrev) {
        pdfCompactPrev.addEventListener("click", () => {
          if (pdfModeActive) void pdfGoToPage((pdfState.page || 1) - 1);
        });
      }
      if (pdfCompactNext) {
        pdfCompactNext.addEventListener("click", () => {
          if (pdfModeActive) void pdfGoToPage((pdfState.page || 1) + 1);
        });
      }
      if (pdfCompactGoto) {
        pdfCompactGoto.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && pdfModeActive) {
            event.preventDefault();
            void pdfGoToPage(pdfCompactGoto.value || pdfState.page || 1);
          }
        });
        pdfCompactGoto.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (typeof renderPdfPageHistoryPopup === "function") {
            renderPdfPageHistoryPopup(event.currentTarget);
          }
        });
        pdfCompactGoto.addEventListener("mousedown", (event) => {
          if (event.button === 2) {
            event.preventDefault();
            event.stopPropagation();
            if (typeof renderPdfPageHistoryPopup === "function") {
              renderPdfPageHistoryPopup(event.currentTarget);
            }
          }
        });
      }
      if (pdfCompactZoomOut) {
        pdfCompactZoomOut.addEventListener("click", () => {
          if (pdfModeActive) setPdfZoom((pdfState.viewZoom || 1) - 0.15);
        });
      }
      if (pdfCompactZoomIn) {
        pdfCompactZoomIn.addEventListener("click", () => {
          if (pdfModeActive) setPdfZoom((pdfState.viewZoom || 1) + 0.15);
        });
      }
      if (typeof pdfCompactAiAssist !== "undefined" && pdfCompactAiAssist) {
        pdfCompactAiAssist.addEventListener("click", () => {
          if (pdfModeActive) togglePdfAiAssistRegions();
        });
      }
      if (pdfCompactEye) {
        pdfCompactEye.addEventListener("click", () => {
          if (pdfModeActive) togglePdfSelectionMode();
        });
        pdfCompactEye.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (pdfModeActive) openPdfOcrEnginePopover(event);
        });
        pdfCompactEye.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfOcrEnginePopover(event);
        });
      }
      if (pdfCompactScan) {
        pdfCompactScan.addEventListener("click", () => {
          if (pdfModeActive) void scanPdfCurrentPage();
        });
        pdfCompactScan.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (pdfModeActive) openPdfScanSourcePopover(event);
        });
        pdfCompactScan.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfScanSourcePopover(event);
        });
      }
      document.addEventListener("pointerdown", (event) => {
        if (!pdfOcrEnginePopover || pdfOcrEnginePopover.classList.contains("is-hidden")) {
          return;
        }
        const target = event.target;
        if (pdfOcrEnginePopover.contains(target) || (pdfCompactEye && pdfCompactEye.contains(target))) {
          return;
        }
        hidePdfOcrEnginePopover();
      });
      document.addEventListener("pointerdown", (event) => {
        if (!pdfScanSourcePopover || pdfScanSourcePopover.classList.contains("is-hidden")) {
          return;
        }
        const target = event.target;
        if (pdfScanSourcePopover.contains(target) || (pdfCompactScan && pdfCompactScan.contains(target))) {
          return;
        }
        hidePdfScanSourcePopover();
      });
      if (pdfCompactPen) {
        pdfCompactPen.addEventListener("click", () => {
          if (pdfModeActive) togglePdfPenMode();
        });
        pdfCompactPen.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          if (pdfModeActive) openPdfPenPopover(event);
        });
        pdfCompactPen.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfPenPopover(event);
        });
      }
      if (pdfCompactAudio) {
        pdfCompactAudio.addEventListener("click", () => {
          if (pdfModeActive) togglePdfSharedAudioInsertMode();
        });
        pdfCompactAudio.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
        });
        pdfCompactAudio.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) {
            event.preventDefault();
            event.stopPropagation();
            togglePdfSharedAudioInsertMode();
          }
        });
      }
      if (pdfCompactEraser) {
        pdfCompactEraser.addEventListener("click", () => {
          if (pdfModeActive) togglePdfEraserMode();
        });
        pdfCompactEraser.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          if (pdfModeActive) openPdfEraserPopover(event);
        });
        pdfCompactEraser.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfEraserPopover(event);
        });
      }
      if (pdfCompactText) {
        pdfCompactText.addEventListener("click", () => {
          if (pdfModeActive) togglePdfTextMode();
        });
        pdfCompactText.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          if (pdfModeActive) openPdfTextPopover(event);
        });
        pdfCompactText.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfTextPopover(event);
        });
      }
      if (pdfCompactPinPage) {
        pdfCompactPinPage.addEventListener("click", () => {
          if (pdfModeActive && typeof setPdfPinnedPage === "function") setPdfPinnedPage();
        });
      }
      if (pdfCompactPinImage) {
        pdfCompactPinImage.addEventListener("click", () => {
          if (pdfModeActive) addPdfPinnedRegionFromSelection();
        });
        pdfCompactPinImage.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          if (pdfModeActive) openPdfPinnedRegionPopover(event);
        });
        pdfCompactPinImage.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive) openPdfPinnedRegionPopover(event);
        });
      }
      if (typeof pdfCompactLocalImage !== "undefined" && pdfCompactLocalImage) {
        pdfCompactLocalImage.addEventListener("click", (event) => {
          if (pdfModeActive && typeof openPdfLocalImagePopover === "function") openPdfLocalImagePopover(event);
        });
        pdfCompactLocalImage.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (pdfModeActive && typeof openPdfLocalImagePopover === "function") openPdfLocalImagePopover(event);
        });
        pdfCompactLocalImage.addEventListener("pointerdown", (event) => {
          if (event && event.button === 2 && pdfModeActive && typeof openPdfLocalImagePopover === "function") {
            event.preventDefault();
            event.stopPropagation();
            openPdfLocalImagePopover(event);
          }
        });
      }
      if (pdfCompactConsole) {
        pdfCompactConsole.addEventListener("click", () => {
          if (pdfModeActive) setPdfGhostConsoleVisible(!pdfState.ghostConsoleVisible);
        });
      }
      window.addEventListener("resize", () => window.requestAnimationFrame(syncPdfCompactDock), { passive: true });
      window.addEventListener("resize", () => {
        if (aiAgentGhostEnPopup && aiAgentGhostEnPopup.classList.contains("is-open")) {
          window.requestAnimationFrame(positionAiAgentGhostEnPopup);
        }
      }, { passive: true });
      if (aiAgentButton) {
        aiAgentButton.addEventListener("click", (event) => {
          event.stopPropagation();
          aiAgentSuggestionAcknowledged = true;
          aiAgentButton.classList.remove("is-suggestion-pulse");
          renderAiAgentSuggestion();
          if (aiAgentPopup && aiAgentPopup.classList.contains("is-open")) {
            closeAiAgentPopup();
          } else {
            setMobileToolsOpen(false);
            openAiAgentPopup();
          }
        });
      }
      if (aiAgentClose) {
        aiAgentClose.addEventListener("click", closeAiAgentPopup);
      }
      if (aiAgentSubmit) {
        aiAgentSubmit.addEventListener("click", () => void submitAiAgentQuestion());
      }
      if (aiAgentTranslateEn) {
        aiAgentTranslateEn.addEventListener("click", () => void translateAiAgentInputToEnglish());
      }
      if (aiAgentGhostEnClose) {
        aiAgentGhostEnClose.addEventListener("click", closeAiAgentGhostEnPopup);
      }
      if (aiAgentGhostEnPopup) {
        aiAgentGhostEnPopup.addEventListener("pointerdown", (event) => event.stopPropagation());
        aiAgentGhostEnPopup.addEventListener("keydown", (event) => {
          if (event.key !== "Control" || event.repeat) return;
          event.preventDefault();
          event.stopPropagation();
          void toggleAiAgentGhostEnMic();
        });
      }
      if (aiAgentGhostEnDetail) {
        aiAgentGhostEnDetail.addEventListener("pointerdown", (event) => event.stopPropagation());
      }
      aiAgentGhostEnVoiceButtons.forEach((button) => {
        button.addEventListener("click", () => {
          setAiAgentGhostEnVoiceAccent(button.dataset.ghostEnVoice || "uk");
        });
      });
      if (aiAgentGhostEnSpeed) {
        let ghostEnSpeedPointerId = null;
        let ghostEnSpeedStartY = 0;
        let ghostEnSpeedStartIndex = 0;
        let ghostEnSpeedSuppressClick = false;
        const finishGhostEnSpeedDrag = (event) => {
          if (ghostEnSpeedPointerId === null || event.pointerId !== ghostEnSpeedPointerId) return;
          try {
            aiAgentGhostEnSpeed.releasePointerCapture(event.pointerId);
          } catch (error) {
          }
          if (ghostEnSpeedSuppressClick) {
            const percent = Math.round(normalizeAiAgentGhostEnPlaybackRate(aiAgentGhostEnPlaybackRate) * 100);
            setAiAgentGhostEnStatus(`Ghost EN reading speed ${percent}%.`);
          }
          ghostEnSpeedPointerId = null;
          ghostEnSpeedStartY = 0;
          ghostEnSpeedStartIndex = 0;
          window.setTimeout(() => {
            ghostEnSpeedSuppressClick = false;
          }, 0);
        };
        aiAgentGhostEnSpeed.addEventListener("pointerdown", (event) => {
          if (event.button !== undefined && event.button !== 0) return;
          event.preventDefault();
          event.stopPropagation();
          ghostEnSpeedPointerId = event.pointerId;
          ghostEnSpeedStartY = Number(event.clientY || 0) || 0;
          ghostEnSpeedStartIndex = aiAgentGhostEnPlaybackRateIndex();
          ghostEnSpeedSuppressClick = false;
          aiAgentGhostEnSpeed.focus({ preventScroll: true });
          try {
            aiAgentGhostEnSpeed.setPointerCapture(event.pointerId);
          } catch (error) {
          }
        });
        aiAgentGhostEnSpeed.addEventListener("pointermove", (event) => {
          if (ghostEnSpeedPointerId === null || event.pointerId !== ghostEnSpeedPointerId) return;
          event.preventDefault();
          event.stopPropagation();
          const deltaY = ghostEnSpeedStartY - (Number(event.clientY || 0) || 0);
          if (Math.abs(deltaY) < 6) return;
          ghostEnSpeedSuppressClick = true;
          const stepDelta = Math.trunc(deltaY / 14);
          setAiAgentGhostEnPlaybackRateByIndex(ghostEnSpeedStartIndex + stepDelta, { status: false });
        });
        aiAgentGhostEnSpeed.addEventListener("pointerup", finishGhostEnSpeedDrag);
        aiAgentGhostEnSpeed.addEventListener("pointercancel", finishGhostEnSpeedDrag);
        aiAgentGhostEnSpeed.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (ghostEnSpeedSuppressClick) return;
          const delta = event.shiftKey ? -1 : 1;
          setAiAgentGhostEnPlaybackRateByIndex(aiAgentGhostEnPlaybackRateIndex() + delta);
        });
        aiAgentGhostEnSpeed.addEventListener("keydown", (event) => {
          const key = event.key;
          if (key === "ArrowUp" || key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            setAiAgentGhostEnPlaybackRateByIndex(aiAgentGhostEnPlaybackRateIndex() + 1);
          } else if (key === "ArrowDown" || key === "ArrowLeft") {
            event.preventDefault();
            event.stopPropagation();
            setAiAgentGhostEnPlaybackRateByIndex(aiAgentGhostEnPlaybackRateIndex() - 1);
          } else if (key === "Home") {
            event.preventDefault();
            event.stopPropagation();
            setAiAgentGhostEnPlaybackRateByIndex(0);
          } else if (key === "End") {
            event.preventDefault();
            event.stopPropagation();
            setAiAgentGhostEnPlaybackRateByIndex(AI_AGENT_GHOST_EN_PLAYBACK_RATES.length - 1);
          }
        });
      }
      if (aiAgentGhostEnVoiceSelect) {
        aiAgentGhostEnVoiceSelect.addEventListener("pointerdown", () => {
          void loadAiAgentGhostEnVoiceOptions(false);
        });
        aiAgentGhostEnVoiceSelect.addEventListener("focus", () => {
          void loadAiAgentGhostEnVoiceOptions(false);
        });
        aiAgentGhostEnVoiceSelect.addEventListener("change", () => {
          handleAiAgentGhostEnVoiceSelectionChanged();
        });
      }
      if (aiAgentGhostEnRead) {
        aiAgentGhostEnRead.addEventListener("click", () => {
          void playAiAgentGhostEnParagraphVoice();
        });
      }
      if (aiAgentGhostEnMic) {
        aiAgentGhostEnMic.addEventListener("click", () => {
          void toggleAiAgentGhostEnMic();
        });
      }
      if (aiAgentGhostEnReplay) {
        aiAgentGhostEnReplay.addEventListener("click", () => {
          void replayAiAgentGhostEnMicSample();
        });
      }
      if (aiAgentGhostEnText) {
        aiAgentGhostEnText.addEventListener("pointerover", (event) => {
          const token = event.target && event.target.closest ? event.target.closest(".ft-ai-ghost-en-token") : null;
          if (!token) return;
          window.clearTimeout(aiAgentGhostEnHoverTimer);
          aiAgentGhostEnHoverTimer = window.setTimeout(() => showAiAgentGhostEnWordDetail(token), 60);
        });
        aiAgentGhostEnText.addEventListener("pointerout", (event) => {
          const token = event.target && event.target.closest ? event.target.closest(".ft-ai-ghost-en-token") : null;
          if (!token) return;
          const related = event.relatedTarget;
          if (related && token.contains(related)) return;
          token.classList.remove("is-active");
        });
        aiAgentGhostEnText.addEventListener("pointerleave", () => {
          window.clearTimeout(aiAgentGhostEnHoverTimer);
          aiAgentGhostEnText.querySelectorAll(".ft-ai-ghost-en-token.is-active").forEach((node) => node.classList.remove("is-active"));
        });
        aiAgentGhostEnText.addEventListener("click", (event) => {
          const token = event.target && event.target.closest ? event.target.closest(".ft-ai-ghost-en-token") : null;
          if (token) {
            showAiAgentGhostEnWordDetail(token);
            void playAiAgentGhostEnWordAudio(token.dataset.word || token.textContent || "", token);
          }
        });
        aiAgentGhostEnText.addEventListener("keydown", (event) => {
          if (!event || (event.key !== "Enter" && event.key !== " ")) return;
          const token = event.target && event.target.closest ? event.target.closest(".ft-ai-ghost-en-token") : null;
          if (!token) return;
          event.preventDefault();
          showAiAgentGhostEnWordDetail(token);
          void playAiAgentGhostEnWordAudio(token.dataset.word || token.textContent || "", token);
        });
      }
      if (aiAgentSuggestionUse) {
        aiAgentSuggestionUse.addEventListener("click", useAiAgentSuggestion);
      }
      if (aiAgentSuggestionDismiss) {
        aiAgentSuggestionDismiss.addEventListener("click", clearAiAgentSuggestion);
      }
      aiAgentVocabQuickButtons.forEach((button) => {
        button.addEventListener("click", () => {
          void runAiAgentVocabQuick(button.dataset.aiVocabQuick || "usage");
        });
      });
      aiAgentModeButtons.forEach((button) => {
        button.addEventListener("click", () => setAiAgentMode(button.dataset.aiAgentMode || "spoken"));
      });
      setAiAgentMode(getAiAgentMode(), false);
      attachVietnameseTypingSupport(aiAgentInput, aiAgentVietnameseToggle, "ghost_ai_agent");
      initSpeechInputModeControl(aiAgentSpeechMode, "ghost_ai_agent", aiAgentViSttButton);
      if (aiAgentViSttButton) {
        aiAgentViSttButton.addEventListener("click", () => {
          void toggleFutureSpeechInputDictation(aiAgentInput, aiAgentViSttButton, "ghost_ai_agent");
        });
      }
      if (worldTrainingAnswer) {
        worldTrainingAnswer.dataset.vietnameseTypingActive = "0";
      }
      attachVietnameseTypingSupport(worldTrainingAnswer, worldTrainingViToggle, "qm_city_training_translate_vi");
      initSpeechInputModeControl(worldTrainingSpeechMode, "qm_city_training_answer", worldTrainingSpeechMic);
      if (worldTrainingSpeechMic) {
        worldTrainingSpeechMic.addEventListener("click", () => {
          void toggleWorldTrainingSpeechInput();
        });
      }
      if (worldBattleSpeechMic) {
        worldBattleSpeechMic.addEventListener("click", () => {
          void toggleWorldBattleSpeechInput();
        });
      }
      if (worldBattleAnswer) {
        worldBattleAnswer.dataset.vietnameseTypingActive = "0";
      }
      attachVietnameseTypingSupport(worldBattleAnswer, worldBattleViToggle, "qm_city_battle_translate_vi");
      initSpeechInputModeControl(worldBattleSpeechMode, "qm_city_battle_answer", worldBattleSpeechMic);
      const focusTextInputEnd = (input) => {
        if (!input) return;
        try {
          if (typeof input.focus === "function") input.focus();
          const length = String(input.value || "").length;
          if (typeof input.setSelectionRange === "function") {
            input.setSelectionRange(length, length);
          }
        } catch (error) {
        }
      };
      const clearFastGhostInputText = (input) => {
        if (!input) return;
        input.value = "";
        if (typeof browserSpeechInputTarget !== "undefined" && browserSpeechInputTarget === input) {
          browserSpeechInputBaseValue = "";
          browserSpeechInputLastRenderedValue = "";
          browserSpeechInputLastSpeechText = "";
          browserSpeechInputDraftStart = -1;
          browserSpeechInputDraftEnd = -1;
          browserSpeechInputDraftText = "";
          browserSpeechInputAnchorStart = -1;
          browserSpeechInputFinalText = "";
          browserSpeechInputInterimText = "";
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        if (
          typeof syncPdfAgentInputPreview === "function"
          && typeof pdfEls !== "undefined"
          && pdfEls
          && (input === pdfEls.askInput || input === pdfEls.askInputPreviewBody)
        ) {
          syncPdfAgentInputPreview();
        }
        focusTextInputEnd(input);
      };
      const openFastGhostSpeechInput = () => {
        if (aiAgentInput && aiAgentViSttButton) {
          setMobileToolsOpen(false);
          if (typeof openAiAgentPopup === "function") {
            openAiAgentPopup();
          }
          window.requestAnimationFrame(() => {
            focusTextInputEnd(aiAgentInput);
            if (typeof ensureFutureSpeechInputDictation === "function") {
              void ensureFutureSpeechInputDictation(aiAgentInput, aiAgentViSttButton, "ghost_ai_agent");
            }
          });
        }
      };
      document.addEventListener("keydown", (event) => {
        if (
          event
          && clean(event.key).toLowerCase() === "w"
          && !event.repeat
          && event.altKey
          && !event.ctrlKey
          && !event.metaKey
          && !event.shiftKey
          && typeof pdfModeActive !== "undefined"
          && pdfModeActive
        ) {
          event.preventDefault();
          if (typeof togglePdfPinnedRegionFloat === "function") {
            togglePdfPinnedRegionFloat();
          }
          return;
        }
        if (
          event
          && clean(event.key).toLowerCase() === "e"
          && !event.repeat
          && event.altKey
          && !event.ctrlKey
          && !event.metaKey
          && !event.shiftKey
          && typeof pdfModeActive !== "undefined"
          && pdfModeActive
        ) {
          event.preventDefault();
          if (typeof togglePdfPinnedPage === "function") {
            void togglePdfPinnedPage();
          }
          return;
        }
        if (
          !event
          || clean(event.key).toLowerCase() !== "q"
          || event.repeat
          || !event.altKey
          || event.ctrlKey
          || event.metaKey
          || event.shiftKey
        ) {
          return;
        }
        event.preventDefault();
        openFastGhostSpeechInput();
      }, true);
      document.addEventListener("keydown", (event) => {
        if (!event || event.key !== "`" || event.repeat || event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        const target = document.activeElement;
        const isGhostAiInput = Boolean(aiAgentInput && target === aiAgentInput);
        const isGhostEyeInput = Boolean(
          typeof pdfEls !== "undefined"
          && pdfEls
          && (target === pdfEls.askInput || target === pdfEls.askInputPreviewBody)
        );
        if (!isGhostAiInput && !isGhostEyeInput) {
          return;
        }
        event.preventDefault();
        clearFastGhostInputText(target);
      }, true);
      document.addEventListener("keydown", handleZipformerViInputCtrlKeyDown, true);
      document.addEventListener("keyup", handleZipformerViInputCtrlKeyUp, true);
      document.addEventListener("keydown", handleSharedWorldTrainingServerSpeechCtrlKeyDown, true);
      document.addEventListener("keyup", handleSharedWorldTrainingServerSpeechCtrlKeyUp, true);
      if (aiAgentInput) {
        aiAgentInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submitAiAgentQuestion();
          }
        });
      }
      if (aiAgentPopup) {
        aiAgentPopup.addEventListener("pointerdown", (event) => event.stopPropagation());
      }
      if (mobileToolsToggle) {
        mobileToolsToggle.addEventListener("click", (event) => {
          event.stopPropagation();
          toggleMobileTools();
        });
      }
      if (authFullscreenButton) {
        authFullscreenButton.addEventListener("click", toggleFullscreen);
      }
      if (!shouldShowStartFullscreenGate()) {
        hideStartFullscreenGate();
      }
      if (startFullscreenMain) {
        startFullscreenMain.addEventListener("click", () => {
          void startClientFullscreen();
        });
      }
      if (startFullscreenSkip) {
        startFullscreenSkip.addEventListener("click", hideStartFullscreenGate);
      }
      document.addEventListener("fullscreenchange", () => {
        if (document.fullscreenElement) {
          hideStartFullscreenGate();
        }
        scheduleQuestionViewportLayoutRefresh(80, {
          force: true,
          guidanceDelays: [0, 180, 420, 860],
        });
      });
      if (authLoginTab) {
        authLoginTab.addEventListener("click", () => {
          setAuthMode("login");
          setAuthStatus("Sign in to continue.");
        });
      }
      if (authRegisterTab) {
        authRegisterTab.addEventListener("click", () => {
          setAuthMode("register");
          setAuthStatus("Your registration request is waiting for server approval.");
        });
      }
      if (authPassToggle) {
        authPassToggle.addEventListener("click", () => {
          const visible = authPass && !authPass.classList.contains("is-visible");
          [authPass, authConfirm].forEach((node) => {
            if (node) {
              node.classList.toggle("is-visible", Boolean(visible));
            }
          });
          authPassToggle.classList.toggle("is-visible", Boolean(visible));
          authPassToggle.setAttribute("aria-label", visible ? "Hide password" : "Show password");
          authPassToggle.setAttribute("title", visible ? "Hide password" : "Show password");
        });
      }
      if (authForgot) {
        authForgot.addEventListener("click", () => {
          if (authMode === "reset") {
            authResetApproved = false;
            setAuthMode("login");
            setAuthStatus("Sign in to continue.");
            return;
          }
          authResetApproved = false;
          setAuthMode("reset");
          setAuthStatus("Enter your username, then send a request. After admin approval, check again to set a new password.");
        });
      }
      if (authResetSend) {
        authResetSend.addEventListener("click", async () => {
          const username = clean(authUser && authUser.value || "");
          if (!username) {
            setAuthStatus("Enter your username before sending a reset request.", "error");
            return;
          }
          authResetSend.disabled = true;
          setAuthStatus("Sending request to admin...");
          try {
            const result = await fetchAuthJson("/auth/password-reset/request", {
              method: "POST",
              body: JSON.stringify({ username }),
            });
            const payload = result && result.payload || {};
            if (payload.status === "approved") {
              authResetApproved = true;
              authPass.value = "";
              authConfirm.value = "";
              setAuthMode("reset");
              setAuthStatus("Admin approved. Enter and confirm your new password.", "ok");
              window.setTimeout(() => focusAuthNode(authPass), 40);
              return;
            }
            authResetApproved = false;
            setAuthMode("reset");
            setAuthStatus("Password reset request sent. Ask the admin to approve it on the Server 2 dashboard.", "ok");
          } catch (error) {
            setAuthStatus(error && error.message ? error.message : "Could not send the request.", "error");
          } finally {
            authResetSend.disabled = false;
          }
        });
      }
      if (authSwitch) {
        authSwitch.addEventListener("click", () => {
          showLoginGate("Sign in with another account.");
        });
      }
      if (userButton) {
        userButton.addEventListener("click", (event) => {
          event.stopPropagation();
          const isOpen = userMenu && userMenu.classList.toggle("is-open");
          userButton.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
      }
      if (logoutButton) {
        logoutButton.addEventListener("click", (event) => {
          event.stopPropagation();
          logoutAuth();
        });
      }
      if (inventoryOpenButton) {
        inventoryOpenButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          openQuestionInventoryPopup();
        });
      }
      if (profileEditOpenButton) {
        profileEditOpenButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          openProfileEditCard();
        });
      }
      if (pdfAdminUserOpenButton) {
        pdfAdminUserOpenButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!currentAuthIsAdmin || !pdfAdminUserPanel) {
            return;
          }
          pdfAdminUserPanel.hidden = !pdfAdminUserPanel.hidden;
          if (!pdfAdminUserPanel.hidden) {
            void loadPdfAdminUsers();
          }
        });
      }
      if (pdfAdminUserApply) {
        pdfAdminUserApply.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void applyPdfAdminActingUser(pdfAdminUserSelect ? pdfAdminUserSelect.value : "");
        });
      }
      if (pdfAdminUserClear) {
        pdfAdminUserClear.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void applyPdfAdminActingUser("");
        });
      }
      if (pdfAdminUserSelect) {
        pdfAdminUserSelect.addEventListener("change", (event) => {
          event.stopPropagation();
          setPdfAdminUserStatus(pdfAdminUserSelect.value ? `Ready to act as @${pdfAdminUserSelect.value}` : "Ready to save as admin.");
        });
      }
      if (userMenuAvatar) {
        userMenuAvatar.classList.add("is-profile-clickable");
        userMenuAvatar.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void openPublicProfileCard(activeWorldUsername() || currentAuthUsername);
        });
      }
      if (userAvatarUploadButton && userAvatarFileInput) {
        userAvatarUploadButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          userAvatarFileInput.click();
        });
        userAvatarFileInput.addEventListener("change", () => {
          const file = userAvatarFileInput.files && userAvatarFileInput.files[0];
          if (file) {
            void uploadCurrentUserAvatar(file);
          }
        });
      }
      if (profileCloseButton) {
        profileCloseButton.addEventListener("click", (event) => {
          event.preventDefault();
          closePublicProfileCard();
        });
      }
      if (profileModal) {
        profileModal.addEventListener("click", (event) => {
          if (event.target === profileModal) {
            closePublicProfileCard();
          }
        });
      }
      if (profileEditCloseButton) {
        profileEditCloseButton.addEventListener("click", (event) => {
          event.preventDefault();
          closeProfileEditCard();
        });
      }
      if (profileEditModal) {
        profileEditModal.addEventListener("click", (event) => {
          if (event.target === profileEditModal) {
            closeProfileEditCard();
          }
        });
      }
      if (profileEditSave) {
        profileEditSave.addEventListener("click", (event) => {
          event.preventDefault();
          void saveProfileEditCard();
        });
      }
      if (profilePhotoFileInput) {
        profilePhotoFileInput.addEventListener("change", () => {
          const file = profilePhotoFileInput.files && profilePhotoFileInput.files[0];
          if (file) {
            void uploadProfileEditPhoto(file);
          }
        });
      }
      if (inventoryCloseButton) {
        inventoryCloseButton.addEventListener("click", (event) => {
          event.preventDefault();
          closeQuestionInventoryPopup();
        });
      }
      if (inventoryModal) {
        inventoryModal.addEventListener("click", (event) => {
          if (event.target === inventoryModal) {
            closeQuestionInventoryPopup();
          }
        });
      }
      if (chatButton) {
        chatButton.addEventListener("click", (event) => {
          event.stopPropagation();
          openLearnerChat();
        });
      }
      if (streamButton) {
        streamButton.addEventListener("click", (event) => {
          event.stopPropagation();
          void requestOrAcceptLearnerStream();
        });
      }
      if (screenButton) {
        screenButton.addEventListener("click", (event) => {
          event.stopPropagation();
          void requestOrAcceptLearnerScreen();
        });
      }
      if (typeof webRecordButton !== "undefined" && webRecordButton) {
        webRecordButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          toggleWebRecording();
        });
      }
      if (adminScreenButton) {
        adminScreenButton.addEventListener("click", (event) => {
          event.stopPropagation();
          void openAdminScreenModal();
        });
      }
      if (adminScreenClose) {
        adminScreenClose.addEventListener("click", closeAdminScreenModal);
      }
      if (adminScreenRefresh) {
        adminScreenRefresh.addEventListener("click", () => void loadAdminScreenUsers());
      }
      if (adminScreenModeButton) {
        adminScreenModeButton.addEventListener("click", () => cycleAdminScreenTransportPreference());
      }
      if (adminScreenMicButton) {
        adminScreenMicButton.addEventListener("click", () => void toggleAdminScreenMic());
      }
      if (adminScreenCheckPath) {
        adminScreenCheckPath.addEventListener("click", () => void writeAdminScreenTransportLog("manual-check", true));
      }
      if (adminScreenStop) {
        adminScreenStop.addEventListener("click", () => void stopAdminScreenSession());
      }
      if (adminScreenReconnect) {
        adminScreenReconnect.addEventListener("click", () => void reconnectAdminScreen());
      }
      if (adminScreenFullscreen) {
        adminScreenFullscreen.addEventListener("click", () => {
          const target = adminScreenView || adminScreenModal || document.documentElement;
          if (!target) return;
          if (document.fullscreenElement && document.exitFullscreen) {
            void document.exitFullscreen();
          } else if (target.requestFullscreen) {
            void target.requestFullscreen({ navigationUI: "hide" }).catch(() => {});
          }
        });
      }
      if (adminScreenModal) {
        adminScreenModal.addEventListener("click", (event) => {
          if (event.target === adminScreenModal) {
            closeAdminScreenModal();
          }
        });
      }
      if (adminScreenView) {
        adminScreenView.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          queueAdminScreenPointer(event, "click", { urgent: true });
        });
        adminScreenView.addEventListener("pointermove", (event) => {
          if (adminScreenPointerActive || Number(event.buttons || 0) > 0) {
            event.preventDefault();
            queueAdminScreenPointer(event, "pointermove", { urgent: true });
            return;
          }
          queueAdminScreenPointer(event, "cursor", { dispatch: false });
        });
        adminScreenView.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          adminScreenPointerActive = true;
          adminScreenView.focus({ preventScroll: true });
          try { adminScreenView.setPointerCapture(event.pointerId); } catch (error) {}
          queueAdminScreenPointer(event, "pointerdown", { urgent: true });
        });
        adminScreenView.addEventListener("pointerup", (event) => {
          event.preventDefault();
          adminScreenPointerActive = false;
          try { adminScreenView.releasePointerCapture(event.pointerId); } catch (error) {}
          queueAdminScreenPointer(event, "pointerup", { urgent: true });
          queueAdminScreenPointer(event, "click", { urgent: true });
        });
        adminScreenView.addEventListener("pointercancel", (event) => {
          adminScreenPointerActive = false;
          try { adminScreenView.releasePointerCapture(event.pointerId); } catch (error) {}
          queueAdminScreenControl({ type: "cursor", visible: false, dispatch: false }, true);
        });
        adminScreenView.addEventListener("pointerleave", () => {
          adminScreenPointerActive = false;
          queueAdminScreenControl({ type: "cursor", visible: false, dispatch: false }, true);
        });
        adminScreenView.addEventListener("wheel", (event) => {
          const point = adminScreenFittedPoint(event);
          if (!point) return;
          event.preventDefault();
          queueAdminScreenControl({
            type: "wheel",
            x: point.x,
            y: point.y,
            deltaX: Number(event.deltaX || 0),
            deltaY: Number(event.deltaY || 0),
            ctrl: Boolean(event.ctrlKey),
            alt: Boolean(event.altKey),
            shift: Boolean(event.shiftKey),
            meta: Boolean(event.metaKey),
          }, true);
        }, { passive: false });
        adminScreenView.addEventListener("keydown", (event) => {
          if (!adminScreenOpen || !adminScreenSession || adminScreenSession.state !== "active") return;
          event.preventDefault();
          queueAdminScreenControl({
            type: "keydown",
            key: event.key || "",
            code: event.code || "",
            repeat: Boolean(event.repeat),
            ctrl: Boolean(event.ctrlKey),
            alt: Boolean(event.altKey),
            shift: Boolean(event.shiftKey),
            meta: Boolean(event.metaKey),
          }, true);
        });
        adminScreenView.addEventListener("keyup", (event) => {
          if (!adminScreenOpen || !adminScreenSession || adminScreenSession.state !== "active") return;
          event.preventDefault();
          queueAdminScreenControl({
            type: "keyup",
            key: event.key || "",
            code: event.code || "",
            repeat: Boolean(event.repeat),
            ctrl: Boolean(event.ctrlKey),
            alt: Boolean(event.altKey),
            shift: Boolean(event.shiftKey),
            meta: Boolean(event.metaKey),
          }, true);
        });
      }
      if (paintButton) {
        paintButton.addEventListener("click", (event) => {
          event.stopPropagation();
          openLearnerPaint();
        });
      }
      if (mobileAnimationButton) {
        mobileAnimationButton.addEventListener("click", (event) => {
          event.stopPropagation();
          toggleMobileAnimationEnabled();
        });
      }
      if (speakSkipAdminButton) {
        speakSkipAdminButton.addEventListener("click", (event) => {
          event.stopPropagation();
          setMobileToolsOpen(false);
          void openSpeakSkipAdminModal();
        });
      }
      if (speakSkipAdminClose) {
        speakSkipAdminClose.addEventListener("click", closeSpeakSkipAdminModal);
      }
      if (speakSkipAdminRefresh) {
        speakSkipAdminRefresh.addEventListener("click", () => {
          void loadSpeakSkipAdminRequests();
        });
      }
      if (speakSkipAdminAcceptAll) {
        speakSkipAdminAcceptAll.addEventListener("click", () => {
          void respondSpeakSkipAdmin({ all: true });
        });
      }
      if (speakSkipAdminModal) {
        speakSkipAdminModal.addEventListener("click", (event) => {
          if (event.target === speakSkipAdminModal) {
            closeSpeakSkipAdminModal();
          }
        });
      }
      if (cursorButton) {
        cursorButton.addEventListener("click", (event) => {
          event.stopPropagation();
          toggleHologramCursor();
        });
      }
      if (gameButton) {
        gameButton.addEventListener("click", (event) => {
          event.stopPropagation();
          openGameLobby();
        });
      }
      if (portalButton) {
        portalButton.addEventListener("click", (event) => {
          event.stopPropagation();
          openSharedWorld();
        });
      }
      if (vaultButton) {
        // Exit is distinct from Lesson Vault Home: persist the active Space_V run before leaving the Space.
        vaultButton.addEventListener("click", (event) => {
          event.stopPropagation();
          setMobileToolsOpen(false);
          // 2026-08-03: capture Space_Q before the exit-gate animation can clear runtime state.
          let questionProgressRecord = null;
          if (questionModeActive && typeof saveQuestionProgressNow === "function") {
            const saved = saveQuestionProgressNow();
            questionProgressRecord = saved && typeof saved === "object" ? saved : null;
          }
          let vocabProgressRecord = null;
          if (vocabModeActive && typeof window.__ftPeekSpaceVProgressBeforeBack === "function") {
            const peekResult = window.__ftPeekSpaceVProgressBeforeBack({ setOverride: false });
            vocabProgressRecord = peekResult && peekResult.progress ? peekResult.progress : null;
          }
          if (vocabModeActive && typeof window.__ftFlushSpaceVProgressBeforeBack === "function") {
            // Added 2026-07-21: Exit renders from the durable local snapshot; Server 2 sync/outbox must not block navigation.
            void window.__ftFlushSpaceVProgressBeforeBack({ notice: true, setOverride: false });
          }
          // The compact progress POST already patches Server 2 RAM/SQLite and the local
          // Lesson Vault/Space Task caches. Do not follow it with duplicate GET/recompute work.
          returnToServerFileSelection({ vocabProgressRecord, questionProgressRecord });
        });
      }
      if (cupButton) {
        cupButton.addEventListener("click", (event) => {
          event.stopPropagation();
          openCupLeaderboard({ scope: "day" });
        });
      }
      if (npcSwitchButton) {
        npcSwitchButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!currentAuthIsAdmin) {
            showTopNotice("Only admins can switch NPC identities.", "error", { duration: 3000 });
            return;
          }
          setMobileToolsOpen(false);
          setNpcSwitchOpen(true);
          renderNpcSwitchRoster();
          void loadNpcSwitchRoster(!npcSwitchRoster.length).catch((error) => {
            setNpcSwitchStatus(error && error.message ? error.message : "Could not load NPC racers.");
          });
        });
      }
      if (npcSwitchClose) {
        npcSwitchClose.addEventListener("click", (event) => {
          event.preventDefault();
          setNpcSwitchOpen(false);
        });
      }
      if (npcSwitchModal) {
        npcSwitchModal.addEventListener("click", (event) => {
          if (event.target === npcSwitchModal) {
            setNpcSwitchOpen(false);
          }
        });
      }
      if (npcSwitchReset) {
        npcSwitchReset.addEventListener("click", (event) => {
          event.preventDefault();
          setActiveNpcActor(null);
          renderNpcSwitchRoster();
          setNpcSwitchStatus("Returned to the real admin account.");
          setNpcSwitchOpen(false);
          showTopNotice("Returned to real admin identity.", "ok", { duration: 3000 });
        });
      }
      if (npcSwitchBuffAdd) {
        npcSwitchBuffAdd.addEventListener("click", (event) => {
          event.preventDefault();
          void buffSelectedNpcRacer();
        });
      }
      if (npcSwitchBuffInput) {
        npcSwitchBuffInput.addEventListener("input", () => {
          const value = normalizeNpcBuffAmount();
          if (value > 0) npcSwitchBuffInput.value = String(value);
          if (Number(npcSwitchBuffInput.value || 0) > 25) npcSwitchBuffInput.value = "25";
        });
        npcSwitchBuffInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void buffSelectedNpcRacer();
          }
        });
      }
      if (cupClose) {
        cupClose.addEventListener("click", closeCupLeaderboard);
      }
      if (cupModal) {
        cupModal.addEventListener("click", (event) => {
          if (event.target === cupModal) {
            closeCupLeaderboard();
          }
        });
      }
      if (cupViewerClose) {
        cupViewerClose.addEventListener("click", closeCupViewerPopover);
      }
      if (cupViewerPopover) {
        cupViewerPopover.addEventListener("click", (event) => {
          event.stopPropagation();
        });
      }
      if (cupRewardClose) {
        cupRewardClose.addEventListener("click", closeCupRewardPopup);
      }
      if (cupRewardModal) {
        cupRewardModal.addEventListener("click", (event) => {
          if (event.target === cupRewardModal) {
            closeCupRewardPopup();
          }
        });
      }
      cupTabs.forEach((button) => {
        button.addEventListener("click", () => {
          currentCupScope = clean(button.dataset.cupScope || "total") || "total";
          closeCupViewerPopover();
          const rows = normalizeCupType(cupLeaderboardCache.type || currentCupType) === currentCupType
            ? ((cupLeaderboardCache.boards && cupLeaderboardCache.boards[currentCupScope]) || [])
            : [];
          renderCupLeaderboard(rows, currentCupScope);
          if (!rows.length) {
            void loadCupLeaderboard(false);
          }
        });
      });
      if (cupTypeSelect) {
        cupTypeSelect.addEventListener("change", () => {
          selectCupType(cupTypeSelect.value || "space_v", true);
        });
      }
      if (cupTypeButton) {
        cupTypeButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setCupTypeMenuOpen(!(cupTypeMenu && cupTypeMenu.classList.contains("is-open")));
        });
        cupTypeButton.addEventListener("keydown", (event) => {
          if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setCupTypeMenuOpen(true);
            const activeOption = cupTypeOptions.find((option) => option.classList.contains("is-selected")) || cupTypeOptions[0];
            if (activeOption) activeOption.focus();
          }
        });
      }
      cupTypeOptions.forEach((option, index) => {
        option.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          selectCupType(option.dataset.cupType || "space_v", true);
          if (cupTypeButton) cupTypeButton.focus();
        });
        option.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            setCupTypeMenuOpen(false);
            if (cupTypeButton) cupTypeButton.focus();
            return;
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectCupType(option.dataset.cupType || "space_v", true);
            if (cupTypeButton) cupTypeButton.focus();
            return;
          }
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const direction = event.key === "ArrowDown" ? 1 : -1;
            const next = cupTypeOptions[(index + direction + cupTypeOptions.length) % cupTypeOptions.length];
            if (next) next.focus();
          }
        });
      });
      document.addEventListener("click", (event) => {
        const clickedPicker = cupTypePicker && cupTypePicker.contains(event.target);
        const clickedMenu = cupTypeMenu && cupTypeMenu.contains(event.target);
        if (!clickedPicker && !clickedMenu) {
          setCupTypeMenuOpen(false);
        }
      });
      window.addEventListener("resize", updateCupTypeMenuPlacement);
      window.addEventListener("scroll", updateCupTypeMenuPlacement, true);
      if (cupStatusSave) {
        cupStatusSave.addEventListener("click", () => {
          void saveCupStatus();
        });
      }
      if (cupStatusInput) {
        cupStatusInput.addEventListener("input", () => {
          validateCupStatusInput(true);
        });
        cupStatusInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void saveCupStatus();
          }
        });
      }
      if (cupWorldChatSend) {
        cupWorldChatSend.addEventListener("click", () => {
          void sendCupWorldChat();
        });
      }
      if (cupWorldChatInput) {
        cupWorldChatInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendCupWorldChat();
          }
        });
      }
      document.addEventListener("pointerdown", (event) => {
        if (!document.documentElement.classList.contains("ft-mobile-tools-open")) {
          return;
        }
        if (eventInsideMobileTools(event)) {
          return;
        }
        setMobileToolsOpen(false);
      }, true);
      window.addEventListener("resize", () => {
        if (!isMobileToolsSurface()) {
          setMobileToolsOpen(false);
        }
        if (cupModal && cupModal.classList.contains("is-open")) {
          window.requestAnimationFrame(positionCupSocialBubbles);
        }
      });
      if (gameClose) {
        gameClose.addEventListener("click", closeGameLobby);
      }
      if (gameModal) {
        gameModal.addEventListener("click", (event) => {
          if (event.target === gameModal) {
            closeGameLobby();
          }
        });
      }
      if (worldMenuTrigger) {
        worldMenuTrigger.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          toggleSharedWorldCloseMenu();
        });
        worldMenuTrigger.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          toggleSharedWorldCloseMenu();
        });
      }
      if (worldExitButton) {
        worldExitButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          closeSharedWorld();
        });
      }
      if (worldInventoryButton) {
        worldInventoryButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void openSharedWorldInventory();
        });
      }
      if (worldCharacterButton) {
        worldCharacterButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (sharedWorldCharacterPickerOpen) {
            closeSharedWorldCharacterPicker();
            return;
          }
          void openSharedWorldCharacterPicker();
        });
      }
      [worldAdminToolsButton, worldBattleAdminToolsButton].forEach((button) => {
        if (!button) return;
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldAdminToolsOpen(!sharedWorldAdminToolsOpen);
        });
      });
      if (worldCharacterClose) {
        worldCharacterClose.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          closeSharedWorldCharacterPicker();
        });
      }
      if (worldCharacterModal) {
        worldCharacterModal.addEventListener("click", (event) => {
          if (event.target === worldCharacterModal) {
            closeSharedWorldCharacterPicker();
          }
        });
      }
      if (worldCharacterGrid) {
        let characterDeckDrag = null;
        let characterDeckSuppressClickUntil = 0;
        worldCharacterGrid.addEventListener("pointerdown", (event) => {
          if (event.button !== 0) return;
          const targetCard = event.target && event.target.closest ? event.target.closest("[data-character-kind]") : null;
          characterDeckDrag = {
            pointerId: event.pointerId,
            startX: event.clientX,
            scrollLeft: worldCharacterGrid.scrollLeft,
            moved: false,
            targetKind: targetCard ? targetCard.dataset.characterKind || "" : "",
          };
          worldCharacterGrid.classList.add("is-dragging");
          if (worldCharacterGrid.setPointerCapture) {
            worldCharacterGrid.setPointerCapture(event.pointerId);
          }
        });
        worldCharacterGrid.addEventListener("pointermove", (event) => {
          if (!characterDeckDrag || characterDeckDrag.pointerId !== event.pointerId) return;
          const dx = event.clientX - characterDeckDrag.startX;
          if (Math.abs(dx) > 4) characterDeckDrag.moved = true;
          worldCharacterGrid.scrollLeft = characterDeckDrag.scrollLeft - dx;
          if (characterDeckDrag.moved) event.preventDefault();
        });
        const finishCharacterDeckDrag = (event) => {
          if (!characterDeckDrag || characterDeckDrag.pointerId !== event.pointerId) return;
          const drag = characterDeckDrag;
          window.setTimeout(() => { characterDeckDrag = null; }, 0);
          worldCharacterGrid.classList.remove("is-dragging");
          if (drag.moved || !drag.targetKind) return;
          const button = worldCharacterGrid.querySelector(`[data-character-kind="${CSS.escape(drag.targetKind)}"]`);
          if (!button || button.getAttribute("aria-disabled") === "true") return;
          characterDeckSuppressClickUntil = Date.now() + 450;
          event.preventDefault();
          event.stopPropagation();
          void chooseSharedWorldCharacter(drag.targetKind || "");
        };
        worldCharacterGrid.addEventListener("pointerup", finishCharacterDeckDrag);
        worldCharacterGrid.addEventListener("pointercancel", finishCharacterDeckDrag);
        worldCharacterGrid.addEventListener("click", (event) => {
          if (Date.now() < characterDeckSuppressClickUntil) {
            event.preventDefault();
            event.stopPropagation();
            return;
          }
          if (characterDeckDrag && characterDeckDrag.moved) {
            event.preventDefault();
            event.stopPropagation();
            return;
          }
          const button = event.target && event.target.closest ? event.target.closest("[data-character-kind]") : null;
          if (!button || button.getAttribute("aria-disabled") === "true") return;
          event.preventDefault();
          event.stopPropagation();
          void chooseSharedWorldCharacter(button.dataset.characterKind || "");
        });
        worldCharacterGrid.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          const button = event.target && event.target.closest ? event.target.closest("[data-character-kind]") : null;
          if (!button || button.getAttribute("aria-disabled") === "true") return;
          event.preventDefault();
          event.stopPropagation();
          void chooseSharedWorldCharacter(button.dataset.characterKind || "");
        });
      }
      if (worldInventoryClose) {
        worldInventoryClose.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          closeSharedWorldInventory();
        });
      }
      if (worldInventoryModal) {
        worldInventoryModal.addEventListener("click", (event) => {
          if (event.target === worldInventoryModal) {
            closeSharedWorldInventory();
          }
        });
      }
      if (worldTrainingClose) {
        worldTrainingClose.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldTrainingQuestionOpen(false);
        });
      }
      if (worldTrainingModal) {
        worldTrainingModal.addEventListener("click", (event) => {
          if (event.target === worldTrainingModal) {
            setSharedWorldTrainingQuestionOpen(false);
          }
        });
      }
      if (worldArena) {
        worldArena.addEventListener("click", (event) => {
          if (sharedWorldMapMode !== "training") {
            return;
          }
          const target = event.target;
          if (target && target.closest && (
            target.closest("[data-slime-id]")
            || target.closest(".ft-world-player")
            || target.closest("#ft-world-training-modal")
          )) {
            return;
          }
          setSharedWorldTrainingQuestionOpen(false);
        });
      }
      const handleSharedWorldTrainingSlimeClick = (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-slime-id]") : null;
          if (!button || button.classList.contains("is-defeated")) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          selectSharedWorldTrainingSlime(button.dataset.slimeId || "");
      };
      [worldTrainingSlimes, worldTrainingMapSlimes].forEach((node) => {
        if (node) {
          node.addEventListener("click", handleSharedWorldTrainingSlimeClick);
        }
      });
      if (worldTrainingAnswerForm) {
        worldTrainingAnswerForm.addEventListener("submit", (event) => {
          event.preventDefault();
          event.stopPropagation();
          submitSharedWorldTrainingAnswer();
        });
      }
      if (worldTrainingChoices) {
        worldTrainingChoices.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-combat-choice]") : null;
          if (!button || button.disabled) return;
          const choiceStartedAt = performance.now();
          event.preventDefault();
          event.stopPropagation();
          worldTrainingChoices.querySelectorAll("[data-combat-choice]").forEach((row) => { row.disabled = true; });
          button.classList.add("is-selected");
          const selected = worldTrainingSelectedSlime();
          const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
          const correctIndex = Number(question.client_correct_choice_index ?? question.clientCorrectChoiceIndex);
          const selectedIndex = Number(button.dataset.combatChoiceIndex);
          if (Number.isInteger(correctIndex) && Number.isInteger(selectedIndex)) {
            button.classList.add(selectedIndex === correctIndex ? "is-client-correct" : "is-client-wrong");
            const correctButton = worldTrainingChoices.querySelector(`[data-combat-choice-index="${correctIndex}"]`);
            if (correctButton && correctButton !== button) correctButton.classList.add("is-client-correct");
          }
          window.__ftTrainingChoiceImmediate = {
            immediateMs: Math.round((performance.now() - choiceStartedAt) * 1000) / 1000,
            selectedIndex,
            correctIndex,
            at: Date.now(),
          };
          console.info("[FTG][TrainingChoiceImmediate]", JSON.stringify(window.__ftTrainingChoiceImmediate));
          submitSharedWorldTrainingAnswer(button.dataset.combatChoice || "");
        });
      }
      if (worldTrainingQuestion) {
        worldTrainingQuestion.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-training-audio-play]") : null;
          if (!button) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const selected = worldTrainingSelectedSlime();
          const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
          void playSharedWorldTrainingAudioQuestion(question);
        });
      }
      if (worldTrainingAnswer) {
        ["pointerdown", "mousedown", "touchstart", "click", "focus"].forEach((eventName) => {
          worldTrainingAnswer.addEventListener(eventName, () => {
            if (typeof requestAnyFullscreen === "function") {
              void requestAnyFullscreen();
            }
          }, { capture: true });
        });
      }
      if (worldTrainingStats) {
        worldTrainingStats.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-training-stat]") : null;
          if (!button || button.disabled) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          upgradeSharedWorldTrainingStat(button.dataset.worldTrainingStat || "");
        });
      }
      if (worldTrainingLoadoutPanel) {
        worldTrainingLoadoutPanel.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-training-stat],[data-world-training-skill-upgrade],[data-world-training-skill-cast]") : null;
          if (!button || button.disabled) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          if (button.dataset.worldTrainingStat) {
            upgradeSharedWorldTrainingStat(button.dataset.worldTrainingStat || "");
          } else if (button.dataset.worldTrainingSkillUpgrade) {
            upgradeSharedWorldTrainingSkill(button.dataset.worldTrainingSkillUpgrade || "");
          } else if (button.dataset.worldTrainingSkillCast) {
            void castSharedWorldTrainingSkill(button.dataset.worldTrainingSkillCast || "earthquake");
          }
        });
      }
      if (worldTrainingQuickSkill) {
        worldTrainingQuickSkill.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (worldTrainingQuickSkill.disabled) {
            const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
            if (activeBattle && clean(activeBattle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open")) {
              const players = sharedWorldBattlePlayersForView(activeBattle);
              renderSharedWorldBattleCombatHud(activeBattle, players.self);
            } else {
              renderSharedWorldTrainingQuickSkill();
            }
            return;
          }
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          if (battle && clean(battle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open")) {
            void castSharedWorldBattleSkill("inferno");
            return;
          }
          void castSharedWorldTrainingSkill(worldTrainingQuickSkill.dataset.worldTrainingSkillCast || "earthquake");
        });
      }
      if (worldTrainingReset) {
        worldTrainingReset.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          resetSharedWorldTraining();
        });
      }
      if (worldModal) {
        worldModal.addEventListener("click", (event) => {
          if (event.target === worldModal) {
            if (sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.status) === "active") {
              setSharedWorldStatus("Finish the battle or press Forfeit to leave with a loss.", "error");
              return;
            }
            closeSharedWorld();
          }
        });
      }
      document.addEventListener("click", (event) => {
        if (!worldCloseMenu || !worldCloseMenu.classList.contains("is-open")) {
          return;
        }
        const target = event.target;
        if (target && target.closest && (target.closest("#ft-world-close-menu") || target.closest("#ft-world-menu-trigger"))) {
          return;
        }
        setSharedWorldCloseMenuOpen(false);
      });
      document.addEventListener("click", (event) => {
        if (!worldGameList || worldGameList.hasAttribute("hidden")) {
          return;
        }
        const target = event.target;
        if (target && target.closest && (target.closest("#ft-world-game-list") || target.closest("#ft-world-game-button"))) {
          return;
        }
        setSharedWorldGameListOpen(false);
      });
      if (worldChatForm) {
        worldChatForm.addEventListener("submit", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (document.activeElement === worldCommandInput) {
            void runSharedWorldCommand(worldCommandInput ? worldCommandInput.value : "").then(() => {
              if (worldCommandInput) {
                worldCommandInput.value = "";
              }
            });
          } else {
            void sendSharedWorldChat();
          }
        });
      }
      if (worldCommandSend) {
        worldCommandSend.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void runSharedWorldCommand(worldCommandInput ? worldCommandInput.value : "").then(() => {
            if (worldCommandInput) {
              worldCommandInput.value = "";
              worldCommandInput.focus();
            }
          });
        });
      }
      if (worldCommandHelp && worldCommandList) {
        worldCommandHelp.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const opening = worldCommandList.hasAttribute("hidden");
          if (opening) {
            worldCommandList.removeAttribute("hidden");
          } else {
            worldCommandList.setAttribute("hidden", "");
          }
          worldCommandHelp.setAttribute("aria-expanded", opening ? "true" : "false");
        });
      }
      if (worldGameButton && worldGameList) {
        worldGameButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const opening = worldGameList.hasAttribute("hidden");
          setSharedWorldGameListOpen(opening);
        });
      }
      if (worldGameList) {
        worldGameList.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-game]") : null;
          if (!button || !worldCommandInput) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const game = clean(button.dataset.worldGame || "fireball_vocab");
          const label = button.textContent ? clean(button.textContent) : sharedWorldBattleGameLabel(game);
          worldCommandInput.value = `Would you like to play ${label} with me?`;
          worldCommandInput.focus();
          worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
          setSharedWorldGameListOpen(false);
          setSharedWorldStatus("Press Run to send this battle invite to the selected learner.", "ok");
        });
      }
      if (worldInvitePanel) {
        worldInvitePanel.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-invite-action][data-invite-id]") : null;
          if (!button) return;
          event.preventDefault();
          event.stopPropagation();
          void respondSharedWorldBattleInvite(clean(button.dataset.worldInviteAction) === "accept", clean(button.dataset.inviteId));
        });
      }
      if (worldBattleAnswerForm) {
        worldBattleAnswerForm.addEventListener("submit", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void submitSharedWorldBattleAnswer();
        });
      }
      if (worldBattleChoices) {
        worldBattleChoices.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-combat-choice]") : null;
          if (!button || button.disabled) return;
          const choiceStartedAt = performance.now();
          event.preventDefault();
          event.stopPropagation();
          worldBattleChoices.dataset.combatChoiceLocked = "1";
          worldBattleChoices.querySelectorAll("[data-combat-choice]").forEach((row) => { row.disabled = true; });
          button.classList.add("is-selected");
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          const question = battle && battle.question && typeof battle.question === "object" ? battle.question : {};
          const correctIndex = Number(question.client_correct_choice_index ?? question.clientCorrectChoiceIndex);
          const selectedIndex = Number(button.dataset.combatChoiceIndex);
          if (Number.isInteger(correctIndex) && Number.isInteger(selectedIndex)) {
            button.classList.add(selectedIndex === correctIndex ? "is-client-correct" : "is-client-wrong");
            const correctButton = worldBattleChoices.querySelector(`[data-combat-choice-index="${correctIndex}"]`);
            if (correctButton && correctButton !== button) correctButton.classList.add("is-client-correct");
          }
          window.__ftPvpChoiceImmediate = {
            immediateMs: Math.round((performance.now() - choiceStartedAt) * 1000) / 1000,
            selectedIndex,
            correctIndex,
            at: Date.now(),
          };
          console.info("[FTG][PvpChoiceImmediate]", JSON.stringify(window.__ftPvpChoiceImmediate));
          void submitSharedWorldBattleAnswer(button.dataset.combatChoice || "");
        });
      }
      if (worldBattleAnswer) {
        let battleAnswerFullscreenPending = false;
        const requestBattleAnswerFullscreen = () => {
          const fullscreenNode = document.fullscreenElement
            || document.webkitFullscreenElement
            || document.mozFullScreenElement
            || document.msFullscreenElement;
          const root = document.documentElement;
          const requestFullscreen = root && (
            root.requestFullscreen
            || root.webkitRequestFullscreen
            || root.mozRequestFullScreen
            || root.msRequestFullscreen
          );
          if (battleAnswerFullscreenPending || fullscreenNode || !root || !requestFullscreen) {
            return;
          }
          battleAnswerFullscreenPending = true;
          let requestResult = null;
          try {
            requestResult = requestFullscreen.call(root, { navigationUI: "hide" });
          } catch (error) {
            battleAnswerFullscreenPending = false;
            return;
          }
          Promise.resolve(requestResult).catch(() => false).finally(() => {
            window.setTimeout(() => {
              battleAnswerFullscreenPending = false;
            }, 160);
          });
        };
        const fullscreenInputEvents = ["pointerdown", "mousedown", "touchstart", "click", "focus"];
        fullscreenInputEvents.forEach((eventName) => {
          worldBattleAnswer.addEventListener(eventName, requestBattleAnswerFullscreen, { capture: true });
        });
        if (worldBattleAnswerForm) {
          ["pointerdown", "mousedown", "touchstart", "click"].forEach((eventName) => {
            worldBattleAnswerForm.addEventListener(eventName, requestBattleAnswerFullscreen, { capture: true });
          });
        }
        ["pointerdown", "mousedown", "touchstart"].forEach((eventName) => {
          document.addEventListener(eventName, (event) => {
            if (!worldBattleModal || worldBattleModal.getAttribute("aria-hidden") === "true" || !worldBattleAnswerForm) {
              return;
            }
            const target = event.target && event.target.closest ? event.target.closest("#ft-world-battle-answer-form, #ft-world-battle-answer") : null;
            const rect = worldBattleAnswerForm.getBoundingClientRect();
            const pointInsideAnswer = Number.isFinite(event.clientX) && Number.isFinite(event.clientY)
              && event.clientX >= rect.left
              && event.clientX <= rect.right
              && event.clientY >= rect.top
              && event.clientY <= rect.bottom;
            if (target || pointInsideAnswer) {
              requestBattleAnswerFullscreen();
            }
          }, { capture: true });
        });
      }
      if (worldBattleSkills) {
        worldBattleSkills.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-skill]") : null;
          if (!button || button.disabled) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          void castSharedWorldBattleSkill(button.dataset.worldSkill || "");
        });
      }
      if (worldBattleForfeit) {
        worldBattleForfeit.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (sharedWorldBattleDesignerOpen) {
            closeSharedWorldBattleDesigner();
            return;
          }
          void forfeitSharedWorldBattle(false);
        });
      }
      if (worldBattleQuestion) {
        worldBattleQuestion.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-training-audio-play]") : null;
          if (!button) return;
          event.preventDefault();
          event.stopPropagation();
          const question = selectedSharedWorldBattleQuestion();
          void playSharedWorldTrainingAudioQuestion(question);
        });
      }
      if (worldBattleBasicOrbit) {
        worldBattleBasicOrbit.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-battle-basic-kind]") : null;
          if (!button) return;
          event.preventDefault();
          event.stopPropagation();
          void selectSharedWorldBattleBasicSkill(button.dataset.battleBasicKind || "");
        });
      }
      if (worldBattleUltimateSkill) {
        worldBattleUltimateSkill.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!worldBattleUltimateSkill.disabled) void castSharedWorldBattleSkill("inferno");
        });
      }
      if (worldBattleAvatarButton) {
        worldBattleAvatarButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          const { self } = sharedWorldBattlePlayersForView(battle || {});
          const point = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self));
          if (point) centerSharedWorldBattleViewportOn(point, true);
        });
      }
      if (worldBattleResultClose) {
        worldBattleResultClose.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          dismissSharedWorldBattleResult();
        });
      }
      window.addEventListener("pagehide", forfeitSharedWorldBattleOnUnload);
      document.addEventListener("visibilitychange", handleSharedWorldBattleVisibilityChange);
      if (worldStage) {
        worldStage.addEventListener("pointerdown", beginSharedWorldStagePan);
        worldStage.addEventListener("pointermove", updateSharedWorldStagePan);
        worldStage.addEventListener("pointerup", endSharedWorldStagePan);
        worldStage.addEventListener("pointercancel", endSharedWorldStagePan);
        worldStage.addEventListener("click", handleSharedWorldStageClick);
      }
      if (worldTrainingAvatarButton) {
        worldTrainingAvatarButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (typeof hideSharedWorldTrainingHistory === "function") {
            hideSharedWorldTrainingHistory();
          }
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          if (battle && clean(battle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open")) {
            const { self } = sharedWorldBattlePlayersForView(battle);
            const point = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self));
            if (point) centerSharedWorldBattleViewportOn(point, true);
            return;
          }
          if (typeof centerSharedWorldViewportOn === "function") {
            const self = typeof getSharedWorldSelfPosition === "function" ? getSharedWorldSelfPosition() : null;
            if (self) {
              centerSharedWorldViewportOn(self.x, self.y, true);
            }
          }
        });
        worldTrainingAvatarButton.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldTrainingBasicSkillsOpen(true);
        });
        worldTrainingAvatarButton.addEventListener("pointerdown", (event) => {
          if (event.button !== 2) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldTrainingBasicSkillsOpen(true);
        });
      }
      if (worldTrainingBasicSkillsClose) {
        worldTrainingBasicSkillsClose.addEventListener("click", () => setSharedWorldTrainingBasicSkillsOpen(false));
      }
      if (worldTrainingBasicSkillsGrid) {
        let trainingBasicPointerDrag = null;
        let trainingBasicDragSuppressClickUntil = 0;
        const trainingBasicDropSlotAt = (x, y) => {
          const target = document.elementFromPoint(x, y);
          return target && target.closest ? target.closest("[data-training-basic-slot]") : null;
        };
        const clearTrainingBasicPointerDrag = () => {
          if (!trainingBasicPointerDrag) return;
          if (trainingBasicPointerDrag.ghost) trainingBasicPointerDrag.ghost.remove();
          if (trainingBasicPointerDrag.button) trainingBasicPointerDrag.button.classList.remove("is-pointer-dragging");
          if (worldTrainingBasicSlots) worldTrainingBasicSlots.querySelectorAll(".is-drag-over").forEach((slot) => slot.classList.remove("is-drag-over"));
          trainingBasicPointerDrag = null;
        };
        worldTrainingBasicSkillsGrid.addEventListener("pointerdown", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-training-basic-kind]") : null;
          if (!button || button.disabled || event.button !== 0 || button.dataset.trainingBasicDraggable !== "true") return;
          trainingBasicPointerDrag = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, kind: button.dataset.trainingBasicKind || "", button, ghost: null, slot: null };
          if (button.setPointerCapture) button.setPointerCapture(event.pointerId);
        });
        worldTrainingBasicSkillsGrid.addEventListener("pointermove", (event) => {
          const drag = trainingBasicPointerDrag;
          if (!drag || drag.pointerId !== event.pointerId) return;
          if (!drag.ghost && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < 6) return;
          if (!drag.ghost) {
            const icon = drag.button.querySelector(".ft-world-training-basic-skill-icon");
            drag.ghost = icon ? icon.cloneNode(true) : document.createElement("span");
            drag.ghost.classList.add("ft-world-training-basic-pointer-ghost");
            document.body.appendChild(drag.ghost);
            drag.button.classList.add("is-pointer-dragging");
            window.__ftTrainingBasicLoadoutTrace = { action: "dragstart", kind: drag.kind, at: Date.now() };
            console.info("[FTG][TrainingBasicLoadout]", window.__ftTrainingBasicLoadoutTrace);
          }
          drag.ghost.style.transform = `translate3d(${Math.round(event.clientX - 29)}px, ${Math.round(event.clientY - 29)}px, 0)`;
          if (drag.slot) drag.slot.classList.remove("is-drag-over");
          drag.slot = trainingBasicDropSlotAt(event.clientX, event.clientY);
          if (drag.slot) drag.slot.classList.add("is-drag-over");
          event.preventDefault();
        });
        const finishTrainingBasicPointerDrag = (event) => {
          const drag = trainingBasicPointerDrag;
          if (!drag || drag.pointerId !== event.pointerId) return;
          if (drag.ghost) {
            const slot = drag.slot || trainingBasicDropSlotAt(event.clientX, event.clientY);
            trainingBasicDragSuppressClickUntil = Date.now() + 350;
            if (slot) assignSharedWorldTrainingBasicSlot(slot.dataset.trainingBasicSlot || 0, drag.kind);
            event.preventDefault();
          }
          clearTrainingBasicPointerDrag();
        };
        worldTrainingBasicSkillsGrid.addEventListener("pointerup", finishTrainingBasicPointerDrag);
        worldTrainingBasicSkillsGrid.addEventListener("pointercancel", clearTrainingBasicPointerDrag);
        // 2026-08-11: Capture release outside the palette when pointer capture/CUA ends over a drop slot.
        document.addEventListener("pointerup", finishTrainingBasicPointerDrag);
        document.addEventListener("pointercancel", clearTrainingBasicPointerDrag);
        window.addEventListener("blur", clearTrainingBasicPointerDrag);
        const showTrainingBasicGuide = (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-training-basic-kind]") : null;
          const definition = button ? sharedWorldTrainingBasicDefinition(button.dataset.trainingBasicKind || "") : null;
          if (definition) renderSharedWorldTrainingBasicSkillGuide(definition);
        };
        worldTrainingBasicSkillsGrid.addEventListener("pointerover", showTrainingBasicGuide);
        worldTrainingBasicSkillsGrid.addEventListener("focusin", showTrainingBasicGuide);
        worldTrainingBasicSkillsGrid.addEventListener("click", (event) => {
          if (Date.now() < trainingBasicDragSuppressClickUntil) {
            event.preventDefault();
            event.stopPropagation();
            return;
          }
          const button = event.target && event.target.closest ? event.target.closest("[data-training-basic-kind]") : null;
          if (!button || button.disabled) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          chooseSharedWorldTrainingBasicSkill(button.dataset.trainingBasicKind || "");
        });
      }
      if (worldTrainingBasicSlots) {
        worldTrainingBasicSlots.addEventListener("dragover", (event) => {
          if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
          event.preventDefault();
          const slot = event.target && event.target.closest ? event.target.closest("[data-training-basic-slot]") : null;
          if (slot) slot.classList.add("is-drag-over");
        });
        worldTrainingBasicSlots.addEventListener("dragleave", (event) => {
          const slot = event.target && event.target.closest ? event.target.closest("[data-training-basic-slot]") : null;
          if (slot) slot.classList.remove("is-drag-over");
        });
        worldTrainingBasicSlots.addEventListener("drop", (event) => {
          event.preventDefault();
          const slot = event.target && event.target.closest ? event.target.closest("[data-training-basic-slot]") : null;
          const kind = event.dataTransfer ? event.dataTransfer.getData("text/plain") : "";
          if (slot && kind) assignSharedWorldTrainingBasicSlot(slot.dataset.trainingBasicSlot || 0, kind);
        });
        worldTrainingBasicSlots.addEventListener("click", (event) => {
          const slot = event.target && event.target.closest ? event.target.closest("[data-training-basic-slot]") : null;
          if (slot && slot.dataset.trainingBasicKind) chooseSharedWorldTrainingBasicSkill(slot.dataset.trainingBasicKind);
        });
      }
      if (worldTrainingBasicOrbit) {
        worldTrainingBasicOrbit.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-training-basic-orbit-kind]") : null;
          if (button) chooseSharedWorldTrainingBasicSkill(button.dataset.trainingBasicOrbitKind || "");
        });
      }
      window.addEventListener("pagehide", () => {
        if (worldModal && worldModal.classList.contains("is-open")) {
          writeSharedWorldCheckpoint();
        }
      });
      document.addEventListener("keydown", handleSharedWorldObstacleArrowPan, true);
      if (worldWitch) {
        worldWitch.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          selectSharedWorldTarget("witch");
          primeSharedWorldWitchCommand();
        });
      }
      if (worldTargetChip) {
        worldTargetChip.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          insertSharedWorldTargetIntoCommand();
        });
      }
      if (worldPointButton) {
        worldPointButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldPickingPosition(!sharedWorldPickingPosition);
        });
      }
      if (worldPositionChip) {
        worldPositionChip.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          insertSharedWorldPositionIntoCommand();
        });
      }
      if (worldNpcButton && worldNpcList) {
        worldNpcButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const opening = worldNpcList.hasAttribute("hidden");
          if (opening) {
            worldNpcList.removeAttribute("hidden");
          } else {
            worldNpcList.setAttribute("hidden", "");
          }
          worldNpcButton.setAttribute("aria-expanded", opening ? "true" : "false");
        });
      }
      if (worldNpcList) {
        worldNpcList.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-world-npc]") : null;
          if (!button || !worldCommandInput) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          const npc = clean(button.textContent || button.dataset.worldNpc || "Mystic Witch");
          worldCommandInput.value = `go to ${npc}`;
          worldCommandInput.focus();
          worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
          worldNpcList.setAttribute("hidden", "");
          if (worldNpcButton) {
            worldNpcButton.setAttribute("aria-expanded", "false");
          }
        });
      }
      if (worldLocateButton) {
        worldLocateButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          centerSharedWorldOnSelf(true);
        });
      }
      if (worldFollowButton) {
        worldFollowButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldFollowSelf(!sharedWorldFollowSelf, true);
        });
      }
      if (worldKeypassButton) {
        worldKeypassButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void buySharedWorldKeyboardPass();
        });
      }
      if (worldSkinShopClose) {
        worldSkinShopClose.addEventListener("click", closeSharedWorldSkinShop);
      }
      if (worldSkinShop) {
        worldSkinShop.addEventListener("click", (event) => {
          if (event.target === worldSkinShop) {
            closeSharedWorldSkinShop();
          }
        });
      }
      if (worldShopSend) {
        worldShopSend.addEventListener("click", () => {
          const text = clean(worldShopInput && worldShopInput.value);
          if (!text) return;
          if (worldShopInput) worldShopInput.value = "";
          handleSharedWorldWitchText(text);
        });
      }
      if (worldShopInput) {
        worldShopInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const text = clean(worldShopInput.value);
            if (!text) return;
            worldShopInput.value = "";
            handleSharedWorldWitchText(text);
          }
        });
      }
      window.addEventListener("keydown", handleSharedWorldKeyboard, true);
      window.addEventListener("keyup", handleSharedWorldKeyboardUp, true);
      window.addEventListener("blur", stopSharedWorldKeyboardLoop);
      if (gameCreateButton) {
        gameCreateButton.addEventListener("click", () => {
          void createGameRoom().catch((error) => setGameStatus(error && error.message ? error.message : "Could not create room.", "error"));
        });
      }
      if (gameJoinButton) {
        gameJoinButton.addEventListener("click", () => {
          void joinGameRoom().catch((error) => setGameStatus(error && error.message ? error.message : "Could not join room.", "error"));
        });
      }
      if (gameReadyButton) {
        gameReadyButton.addEventListener("click", () => {
          void setGameReady(true).catch((error) => setGameStatus(error && error.message ? error.message : "Could not send ready signal.", "error"));
        });
      }
      if (gameCancelButton) {
        gameCancelButton.addEventListener("click", () => {
          void cancelGameRoom().catch((error) => setGameStatus(error && error.message ? error.message : "Could not cancel room.", "error"));
        });
      }
      paintModeButtons.forEach((button) => {
        button.addEventListener("click", () => setLearnerPaintMode(button.dataset.paintMode || "select"));
      });
      if (paintClear) {
        paintClear.addEventListener("click", () => void clearLearnerPaint());
      }
      if (paintDelete) {
        paintDelete.addEventListener("click", deleteLearnerPaintSelection);
      }
      if (paintImage) {
        paintImage.addEventListener("click", () => {
          if (paintImageFile) {
            paintImageFile.click();
          }
        });
      }
      if (paintImageFile) {
        paintImageFile.addEventListener("change", () => {
          const file = paintImageFile.files && paintImageFile.files[0];
          if (file) {
            addLearnerPaintImageFile(file);
          }
          paintImageFile.value = "";
        });
      }
      if (paintPaste) {
        paintPaste.addEventListener("click", () => void pasteLearnerPaintImageFromClipboard());
      }
      if (paintZoomOut) {
        paintZoomOut.addEventListener("click", () => setLearnerPaintZoom(learnerPaintZoom / 1.18));
      }
      if (paintZoomIn) {
        paintZoomIn.addEventListener("click", () => setLearnerPaintZoom(learnerPaintZoom * 1.18));
      }
      if (paintFullscreen) {
        paintFullscreen.addEventListener("click", () => void toggleLearnerPaintFullscreen());
      }
      if (paintTab) {
        paintTab.addEventListener("click", openLearnerPaintInTab);
      }
      [paintColor, paintSize, paintTextInput].filter(Boolean).forEach((control) => {
        ["pointerdown", "mousedown", "touchstart", "click", "keydown", "keyup"].forEach((name) => {
          control.addEventListener(name, (event) => event.stopPropagation());
        });
      });
      if (paintTextInput) {
        paintTextInput.addEventListener("input", () => {
          if (learnerPaintTextEditor) {
            learnerPaintTextEditor.value = paintTextInput.value || "";
          }
        });
      }
      if (paintSize) {
        paintSize.addEventListener("input", syncLearnerPaintSizeFromControl);
        paintSize.addEventListener("change", syncLearnerPaintSizeFromControl);
      }
      if (paintCanvas) {
        paintCanvas.addEventListener("pointerdown", handleLearnerPaintPointerDown);
        paintCanvas.addEventListener("pointermove", handleLearnerPaintPointerMove);
        paintCanvas.addEventListener("pointerup", handleLearnerPaintPointerEnd);
        paintCanvas.addEventListener("pointercancel", handleLearnerPaintPointerEnd);
        paintCanvas.addEventListener("pointerenter", (event) => {
          updateLearnerPaintLocalCursor(event, true);
          updateLearnerPaintToolCursor(event, true);
        });
        paintCanvas.addEventListener("pointermove", (event) => {
          updateLearnerPaintLocalCursor(event, true);
          updateLearnerPaintToolCursor(event, true);
        });
        paintCanvas.addEventListener("pointerleave", (event) => {
          updateLearnerPaintLocalCursor(event, false);
          hideLearnerPaintToolCursor();
        });
        if ("ResizeObserver" in window) {
          const paintObserver = new ResizeObserver(() => {
            if (learnerPaintOpen) {
              resizeLearnerPaintCanvas();
            }
          });
          paintObserver.observe(paintCanvas);
        }
        window.addEventListener("resize", () => {
          if (learnerPaintOpen) {
            resizeLearnerPaintCanvas();
          }
        });
        document.addEventListener("fullscreenchange", () => {
          if (learnerPaintOpen) {
            syncLearnerPaintFullscreenButton();
            scheduleLearnerPaintViewportRefresh();
          }
        });
      }
      if (paintClose) {
        paintClose.addEventListener("click", closeLearnerPaint);
      }
      if (paintModal) {
        paintModal.addEventListener("click", (event) => {
          if (event.target === paintModal) {
            closeLearnerPaint();
          }
        });
      }
      if (chatAudioToggle) {
        chatAudioToggle.addEventListener("click", () => {
          learnerChatAudioEnabled = !learnerChatAudioEnabled;
          renderLearnerChatVoiceSettings();
          void syncLearnerChatVoiceSettings();
        });
      }
      if (chatViAudioToggle) {
        chatViAudioToggle.addEventListener("click", () => {
          learnerChatViAudioEnabled = !learnerChatViAudioEnabled;
          renderLearnerChatVoiceSettings();
          void syncLearnerChatVoiceSettings();
        });
      }
      if (chatAttach && chatFileInput) {
        chatAttach.addEventListener("click", () => chatFileInput.click());
        chatFileInput.addEventListener("change", () => {
          void uploadLearnerChatFiles(chatFileInput.files, activeLearnerChatMode());
        });
      }
      if (chatMic) {
        chatMic.addEventListener("click", () => {
          if (learnerChatRecorder && learnerChatRecorder.state === "recording") {
            stopLearnerChatRecording();
          } else {
            void startLearnerChatRecording();
          }
        });
      }
      if (chatViSttButton) {
        initSpeechInputModeControl(chatViSpeechMode, "learner_chat_vi_input", chatViSttButton);
        chatViSttButton.addEventListener("click", () => {
          void toggleFutureSpeechInputDictation(chatViInput, chatViSttButton, "learner_chat_vi_input");
        });
      }
      if (chatVoiceSend) {
        chatVoiceSend.addEventListener("click", () => void sendLearnerChatVoice());
      }
      if (chatVoiceCancel) {
        chatVoiceCancel.addEventListener("click", cancelLearnerChatVoice);
      }
      if (chatVoiceSelect) {
        chatVoiceSelect.addEventListener("change", () => {
          learnerChatVoice = chatVoiceSelect.value || "male-us";
          const option = chatVoiceSelect.options[chatVoiceSelect.selectedIndex];
          learnerChatVoiceLabel = option ? option.textContent || learnerChatVoice : learnerChatVoice;
          learnerChatAudioEnabled = true;
          renderLearnerChatVoiceSettings();
          void syncLearnerChatVoiceSettings();
        });
      }
      if (worldPenToggle) {
        worldPenToggle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldObstacleMode("draw");
        });
      }
      if (worldPenPortal) {
        worldPenPortal.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldObstacleMode("portal");
        });
      }
      if (worldPenMap) {
        worldPenMap.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!sharedWorldObstacleEditorAllowed()) {
            return;
          }
          setSharedWorldObstacleMode("off");
          if (sharedWorldMapMode === "training") {
            closeSharedWorldTraining({ placeAtTarget: true, targetPoint: sharedWorldCityDefaultPoint });
          } else {
            openSharedWorldTraining({ entryPoint: sharedWorldTrainingDefaultPoint });
          }
        });
      }
      if (worldPenBattle) {
        worldPenBattle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldObstacleMode("off");
          void openSharedWorldBattleDesigner();
        });
      }
      if (worldPenEraser) {
        worldPenEraser.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldObstacleMode("erase");
        });
      }
      if (worldPenSize) {
        worldPenSize.addEventListener("input", () => {
          renderSharedWorldObstacleEditor();
        });
      }
      if (worldPenClear) {
        worldPenClear.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const mapLabel = sharedWorldMapMode === "training" ? "Training" : "QM-City";
          if (!sharedWorldObstacleEditorAllowed() || !window.confirm(`Clear every ${mapLabel} obstacle stroke?`)) {
            return;
          }
          void postSharedWorldObstacle({ action: "clear" }).catch((error) => {
            setSharedWorldStatus(error && error.message ? error.message : "Could not clear obstacles.", "error");
          });
        });
      }
      if (worldBattlePen) {
        worldBattlePen.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldBattleObstacleMode("draw");
        });
      }
      if (worldBattlePortalPen) {
        worldBattlePortalPen.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldBattleObstacleMode("portal");
        });
      }
      if (worldBattleCityMap) {
        worldBattleCityMap.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          closeSharedWorldBattleDesigner();
        });
      }
      if (worldBattleMapLabel) {
        worldBattleMapLabel.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
        });
      }
      if (worldBattleErase) {
        worldBattleErase.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setSharedWorldBattleObstacleMode("erase");
        });
      }
      if (worldBattlePenSize) {
        worldBattlePenSize.addEventListener("input", renderSharedWorldBattleDesigner);
      }
      if (worldBattleClear) {
        worldBattleClear.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (sharedWorldObstacleEditorAllowed() && window.confirm("Clear every Battle-map obstacle stroke?")) {
            void postSharedWorldBattleObstacle({ action: "clear" }).catch((error) => setSharedWorldStatus(error && error.message ? error.message : "Could not clear Battle obstacles.", "error"));
          }
        });
      }
      if (worldAdminCharacterSelect) {
        worldAdminCharacterSelect.addEventListener("change", () => {
          setSharedWorldAdminCharacterPreview(worldAdminCharacterSelect.value || "male");
        });
      }
      if (worldAdminBasicAttack) {
        worldAdminBasicAttack.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          triggerSharedWorldAdminTrainingAttack(false);
        });
      }
      if (worldAdminUltimateAttack) {
        worldAdminUltimateAttack.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          triggerSharedWorldAdminTrainingAttack(true);
        });
      }
      if (worldObstacleCanvas) {
        worldObstacleCanvas.addEventListener("pointerdown", beginSharedWorldObstaclePointer);
        worldObstacleCanvas.addEventListener("pointermove", moveSharedWorldObstaclePointer);
        worldObstacleCanvas.addEventListener("pointerup", endSharedWorldObstaclePointer);
        worldObstacleCanvas.addEventListener("pointercancel", endSharedWorldObstaclePointer);
        worldObstacleCanvas.addEventListener("contextmenu", configureSharedWorldPortalAtEvent);
      }
      if (worldBattleObstacleCanvas) {
        worldBattleObstacleCanvas.addEventListener("pointerdown", beginSharedWorldBattleObstaclePointer);
        worldBattleObstacleCanvas.addEventListener("pointermove", moveSharedWorldBattleObstaclePointer);
        worldBattleObstacleCanvas.addEventListener("pointerup", endSharedWorldBattleObstaclePointer);
        worldBattleObstacleCanvas.addEventListener("pointercancel", endSharedWorldBattleObstaclePointer);
      }
      if (worldBattleMap) {
        // Viewport owns pointer capture during camera drag; listen there so a tap
        // on empty map space still becomes a movement click after the capture ends.
        if (worldBattleViewport) worldBattleViewport.addEventListener("click", handleSharedWorldBattleMapClick);
        else worldBattleMap.addEventListener("click", handleSharedWorldBattleMapClick);
      }
      if (worldBattleViewport) {
        worldBattleViewport.addEventListener("pointerdown", beginSharedWorldBattleViewportPan);
        worldBattleViewport.addEventListener("pointermove", moveSharedWorldBattleViewportPan);
        worldBattleViewport.addEventListener("pointerup", endSharedWorldBattleViewportPan);
        worldBattleViewport.addEventListener("pointercancel", endSharedWorldBattleViewportPan);
      }
      document.addEventListener("keydown", (event) => {
        if (!worldBattleModal || !worldBattleModal.classList.contains("is-open") || sharedWorldBattleDesignerOpen) return;
        if (event.target && event.target.closest && event.target.closest("input,textarea,select,[contenteditable='true']")) return;
        const delta = { ArrowLeft: [-0.025, 0], ArrowRight: [0.025, 0], ArrowUp: [0, -0.035], ArrowDown: [0, 0.035] }[event.key];
        if (!delta || Date.now() - sharedWorldBattleMoveSyncAt < 110) return;
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") return;
        event.preventDefault();
        event.stopPropagation();
        sharedWorldBattleMoveSyncAt = Date.now();
        const { self } = sharedWorldBattlePlayersForView(battle);
        const current = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self)) || { x: 0.22, y: 0.58 };
        void moveSharedWorldBattlePlayer({ x: current.x + delta[0], y: current.y + delta[1] });
      }, { capture: true });
      if (worldPortalTargetMap) {
        worldPortalTargetMap.addEventListener("change", () => renderSharedWorldPortalTargetRegions(""));
      }
      if (worldPortalMenuSave) {
        worldPortalMenuSave.addEventListener("click", saveSharedWorldPortalMenu);
      }
      [worldPortalMenuClose, worldPortalMenuCancel].filter(Boolean).forEach((button) => {
        button.addEventListener("click", closeSharedWorldPortalMenu);
      });
      if (clearAudioCacheButton) {
        clearAudioCacheButton.addEventListener("click", async (event) => {
          event.stopPropagation();
          if (clearAudioCacheButton.disabled || typeof window.__futureClearAudioCache !== "function") return;
          clearAudioCacheButton.disabled = true;
          clearAudioCacheButton.classList.add("is-clearing");
          const result = await window.__futureClearAudioCache();
          clearAudioCacheButton.classList.remove("is-clearing");
          clearAudioCacheButton.classList.add(result && result.ok === false ? "is-warning" : "is-cleared");
          clearAudioCacheButton.disabled = false;
          showFutureAudioCacheClearNotice(result, "local");
          window.setTimeout(() => clearAudioCacheButton.classList.remove("is-cleared", "is-warning"), 1800);
        });
      }
      if (chatViVoiceSelect) {
        chatViVoiceSelect.addEventListener("change", () => {
          learnerChatViVoice = chatViVoiceSelect.value || "edge:vi-VN-NamMinhNeural";
          const option = chatViVoiceSelect.options[chatViVoiceSelect.selectedIndex];
          learnerChatViVoiceLabel = option ? option.textContent || learnerChatViVoice : learnerChatViVoice;
          learnerChatViAudioEnabled = true;
          renderLearnerChatVoiceSettings();
          void syncLearnerChatVoiceSettings();
        });
      }
      if (chatClose) {
        chatClose.addEventListener("click", closeLearnerChat);
      }
      if (chatModal) {
        chatModal.addEventListener("click", (event) => {
          if (event.target === chatModal) {
            closeLearnerChat();
          }
        });
      }
      if (chatSend) {
        chatSend.addEventListener("click", () => {
          void sendLearnerChat("en");
        });
      }
      if (chatViSend) {
        chatViSend.addEventListener("click", () => {
          void sendLearnerChat("vi");
        });
      }
      if (chatInput) {
        chatInput.addEventListener("paste", handleLearnerChatPaste);
        chatInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendLearnerChat("en");
          }
        });
      }
      if (chatViInput) {
        chatViInput.addEventListener("paste", handleLearnerChatPaste);
        chatViInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendLearnerChat("vi");
          }
        });
      }
      if (chatModal) {
        chatModal.addEventListener("paste", handleLearnerChatPaste);
      }
      if (imageViewerClose) {
        imageViewerClose.addEventListener("click", closeChatImageViewer);
      }
      if (imageViewerZoomOut) {
        imageViewerZoomOut.addEventListener("click", (event) => {
          event.stopPropagation();
          setChatImageViewerZoom(chatImageViewerState.zoom / 1.25);
        });
      }
      if (imageViewerZoomIn) {
        imageViewerZoomIn.addEventListener("click", (event) => {
          event.stopPropagation();
          setChatImageViewerZoom(chatImageViewerState.zoom * 1.25);
        });
      }
      if (imageViewerZoomReset) {
        imageViewerZoomReset.addEventListener("click", (event) => {
          event.stopPropagation();
          resetChatImageViewerTransform();
        });
      }
      if (imageViewer) {
        imageViewer.addEventListener("click", (event) => {
          if (event.target === imageViewer) {
            closeChatImageViewer();
          }
        });
        imageViewer.addEventListener("wheel", (event) => {
          if (!imageViewer.classList.contains("is-open")) {
            return;
          }
          event.preventDefault();
          setChatImageViewerZoom(chatImageViewerState.zoom * (event.deltaY < 0 ? 1.12 : 1 / 1.12));
        }, { passive: false });
      }
      if (imageViewerImg) {
        imageViewerImg.addEventListener("pointerdown", beginChatImageViewerDrag);
        imageViewerImg.addEventListener("pointermove", moveChatImageViewerDrag);
        imageViewerImg.addEventListener("pointerup", endChatImageViewerDrag);
        imageViewerImg.addEventListener("pointercancel", endChatImageViewerDrag);
        imageViewerImg.addEventListener("click", (event) => event.stopPropagation());
      }
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && learnerChatOpen) {
          closeLearnerChat();
        }
        if (event.key === "Escape" && adminScreenOpen) {
          closeAdminScreenModal();
        }
        if (event.key === "Escape" && imageViewer && imageViewer.classList.contains("is-open")) {
          closeChatImageViewer();
        }
        if (event.key === "Escape" && learnerPaintOpen) {
          closeLearnerPaint();
        }
        if (event.key === "Escape" && gameModal && gameModal.classList.contains("is-open")) {
          closeGameLobby();
        }
        if (event.key === "Escape" && worldInventoryModal && worldInventoryModal.classList.contains("is-open")) {
          closeSharedWorldInventory();
          return;
        }
        if (event.key === "Escape" && worldCloseMenu && worldCloseMenu.classList.contains("is-open")) {
          setSharedWorldCloseMenuOpen(false);
          return;
        }
        if (event.key === "Escape" && worldModal && worldModal.classList.contains("is-open")) {
          if (sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.status) === "active") {
            setSharedWorldStatus("Battle is locked. Use Forfeit if you want to leave.", "error");
            return;
          }
          closeSharedWorld();
        }
        if (event.key === "Escape" && inventoryModal && inventoryModal.classList.contains("is-open")) {
          closeQuestionInventoryPopup();
        }
        if (event.key === "Escape" && cupModal && cupModal.classList.contains("is-open")) {
          closeCupLeaderboard();
        }
        if (event.key === "Escape" && cupRewardModal && cupRewardModal.classList.contains("is-open")) {
          closeCupRewardPopup();
        }
        if ((event.key === "Delete" || event.key === "Backspace") && learnerPaintOpen && learnerPaintSelection && !learnerPaintTextEditor) {
          event.preventDefault();
          deleteLearnerPaintSelection();
        }
        if (event.key === "Enter" && learnerPaintOpen && learnerPaintSelection && !learnerPaintTextEditor) {
          event.preventDefault();
          commitLearnerPaintSelection();
          renderLearnerPaint();
          scheduleLearnerPaintSync(80);
          setLearnerPaintSyncStatus("Picture fixed on canvas.");
        }
      });
      document.addEventListener("paste", (event) => {
        if (!learnerPaintOpen || !paintModal || !paintModal.classList.contains("is-open")) {
          return;
        }
        const items = Array.from(event.clipboardData && event.clipboardData.items || []);
        const imageItem = items.find((item) => item && String(item.type || "").startsWith("image/"));
        if (!imageItem) {
          return;
        }
        event.preventDefault();
        const file = imageItem.getAsFile();
        if (file) {
          addLearnerPaintImageFile(file);
        }
      });
      document.addEventListener("click", (event) => {
        if (!userMenu || !userButton) {
          return;
        }
        const target = event.target;
        if (target && target.closest && (target.closest("#ft-user-menu") || target.closest("#ft-user-button"))) {
          return;
        }
        userMenu.classList.remove("is-open");
        userButton.setAttribute("aria-expanded", "false");
      });
      if (authSubmit) {
        authSubmit.addEventListener("click", () => {
          void handleAuthSubmit();
        });
      }
      const focusAuthNode = (node) => {
        if (node && typeof node.focus === "function") {
          node.readOnly = false;
          window.setTimeout(() => node.focus({ preventScroll: true }), 30);
        }
      };
      const isAuthEnterAction = (event) => event && (
        event.key === "Enter" ||
        event.code === "Enter" ||
        event.keyCode === 13 ||
        event.which === 13
      );
      const focusAuthPasswordFromUser = (event = null) => {
        if (event && typeof event.preventDefault === "function") {
          event.preventDefault();
        }
        if (clean(authUser && authUser.value)) {
          focusAuthNode(authPass);
        }
      };
      if (authGate) {
        authGate.addEventListener("focusin", (event) => {
          if (event && event.target === authPass) {
            pulseAuthFocusMotion();
            return;
          }
          window.setTimeout(syncAuthPasswordFocusMotion, 0);
        });
        authGate.addEventListener("focusout", () => window.setTimeout(syncAuthPasswordFocusMotion, 0));
      }
      if (authUser) {
        authUser.addEventListener("focus", () => {
          requestAutoFullscreenForSpaceOpen();
          stopAuthFocusMotion();
        });
        authUser.addEventListener("pointerdown", () => {
          requestAutoFullscreenForSpaceOpen();
          stopAuthFocusMotion();
        });
        authUser.addEventListener("input", () => {
          stopAuthFocusMotion();
          if (typeof resetLoginVaultWarmupForInput === "function") {
            resetLoginVaultWarmupForInput();
          }
        });
        authUser.addEventListener("keydown", (event) => {
          if (!isAuthEnterAction(event)) {
            return;
          }
          focusAuthPasswordFromUser(event);
        });
        authUser.addEventListener("keyup", (event) => {
          if (!isAuthEnterAction(event)) {
            return;
          }
          focusAuthPasswordFromUser(event);
        });
        authUser.addEventListener("change", () => {
          if (authGate && authGate.classList.contains("is-hidden")) {
            return;
          }
          window.setTimeout(syncAuthPasswordFocusMotion, 70);
        });
        authUser.addEventListener("blur", () => {
          if (authGate && authGate.classList.contains("is-hidden")) {
            return;
          }
          window.setTimeout(syncAuthPasswordFocusMotion, 90);
        });
      }
      if (authPass) {
        authPass.addEventListener("focus", () => {
          requestAutoFullscreenForSpaceOpen();
          pulseAuthFocusMotion();
        });
        authPass.addEventListener("blur", () => window.setTimeout(syncAuthPasswordFocusMotion, 0));
        authPass.addEventListener("input", () => pulseAuthFocusMotion());
        authPass.addEventListener("pointerdown", () => {
          requestAutoFullscreenForSpaceOpen();
          pulseAuthFocusMotion();
        });
        authPass.addEventListener("keydown", (event) => {
          pulseAuthFocusMotion();
          if (event.key !== "Enter") {
            return;
          }
          event.preventDefault();
          if (!clean(authUser.value)) {
            focusAuthNode(authUser);
            return;
          }
          if (!authPass.value) {
            return;
          }
          if (authMode === "register") {
            focusAuthNode(authConfirm);
            return;
          }
          if (authMode === "profile") {
            focusAuthNode(authFullName);
            return;
          }
          void handleAuthSubmit();
        });
      }
      if (authConfirm) {
        authConfirm.addEventListener("focus", stopAuthFocusMotion);
        authConfirm.addEventListener("pointerdown", stopAuthFocusMotion);
        authConfirm.addEventListener("keydown", (event) => {
          if (event.key !== "Enter") {
            return;
          }
          event.preventDefault();
          if (authMode === "register") {
            focusAuthNode(authFullName);
          }
        });
      }
      if (authFullName) {
        authFullName.addEventListener("focus", stopAuthFocusMotion);
        authFullName.addEventListener("pointerdown", stopAuthFocusMotion);
        authFullName.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            focusAuthNode(authGender);
          }
        });
      }
      if (authGender) {
        authGender.addEventListener("focus", stopAuthFocusMotion);
        authGender.addEventListener("pointerdown", stopAuthFocusMotion);
        authGender.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            focusAuthNode(authBirth);
          }
        });
      }
      if (authBirth) {
        authBirth.addEventListener("focus", stopAuthFocusMotion);
        authBirth.addEventListener("pointerdown", stopAuthFocusMotion);
        authBirth.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void handleAuthSubmit();
          }
        });
      }
      if (loadFullscreenButton) {
        loadFullscreenButton.addEventListener("click", toggleFullscreen);
      }
      [serverOpenButton, taskOpenButton].filter(Boolean).forEach((button) => {
        button.addEventListener("pointerdown", requestAutoFullscreenForSpaceOpen, true);
        button.addEventListener("click", requestAutoFullscreenForSpaceOpen, true);
      });
      [serverBrowser, taskModal].filter(Boolean).forEach((surface) => {
        surface.addEventListener("pointerdown", requestAutoFullscreenForSpaceOpen, true);
        surface.addEventListener("click", requestAutoFullscreenForSpaceOpen, true);
        surface.addEventListener("focusin", requestAutoFullscreenForSpaceOpen, true);
      });
      voiceProxy.addEventListener("click", (event) => {
        if (openVoicePicker(true)) {
          event.preventDefault();
        }
      });
      if (loadVoiceProxy) {
        loadVoiceProxy.addEventListener("click", (event) => {
          event.preventDefault();
          openVoicePicker(true);
        });
      }
      if (loadStartButton) {
        loadStartButton.addEventListener("click", () => {
          const startOptions = lessonEntryGateFastStartRequested ? { skipAudioPrepare: true } : {};
          lessonEntryGateFastStartRequested = false;
          void startPreparedLessonNew(startOptions).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not start a new study.", true);
          });
        });
      }
      if (loadReviewButton) {
        loadReviewButton.addEventListener("click", () => {
          requestAutoFullscreenForSpaceOpen();
          if (pendingVocabularyPayload) {
            if (isVocabCompletionRecord(currentVocabProgressCache && currentVocabProgressCache.savedProgress)) {
              void startPreparedLessonNew({ skipAudioPrepare: true, reviewRun: true }).catch((error) => {
                setLoadStatus(error && error.message ? error.message : "Could not start a new review.", true);
              });
              return;
            }
            void startSavedVocabProgress({ skipAudioPrepare: true });
            return;
          }
          if (pendingQuestionPayload) {
            void continuePreparedLessonFromSavedProgress({ skipAudioPrepare: true }).catch((error) => {
              setLoadStatus(error && error.message ? error.message : "Could not restore saved Space_Q progress.", true);
            });
            return;
          }
          if (pendingParagraphPayload) {
            void startSavedParagraphProgress({ skipAudioPrepare: true });
            return;
          }
          // Added 2026-07-21: revalidate Space_W before Continue so a newer device checkpoint wins.
          void continuePreparedLessonFromSavedProgress({ skipAudioPrepare: true }).catch((error) => {
            setLoadStatus(error && error.message ? error.message : "Could not restore saved Space_W progress.", true);
          });
        });
      }
      if (loadReviewTrainButton) {
        loadReviewTrainButton.addEventListener("click", () => {
          requestAutoFullscreenForSpaceOpen();
          void startSpaceWTrainReviewFromSaved({ skipAudioPrepare: true });
        });
      }
      if (loadEnterNowButton) {
        loadEnterNowButton.addEventListener("click", enterLoadedLessonNow);
      }
      if (serverOpenButton) {
        serverOpenButton.addEventListener("click", openServerBrowser);
      }
      qMobileTabButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          const panel = clean(button.dataset.qPanel || "root").toLowerCase();
          setQuestionMobilePanel(panel);
        });
      });
      installQuestionMobilePanelObserver();
      serverBrowserTabButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          const panel = clean(button.dataset.serverPanel || "vault").toLowerCase();
          if (panel === "notice" && !serverBrowserPanelAvailable("notice")) {
            setLoadStatus("Open a learner folder before editing task notices.", true);
            setServerBrowserPanel("vault");
            return;
          }
          if (panel === "task") {
            if (taskModal) {
              taskModal.hidden = false;
            }
            void loadLessonTasks(serverTaskOwnerContext || currentAuthUsername, { fresh: true }).catch((error) => {
              renderLessonTaskPanel({ task_owner: clean(serverTaskOwnerContext || currentAuthUsername), tasks: [], admin: currentAuthIsAdmin });
              setLoadStatus(error && error.message ? error.message : "Could not load lesson tasks.", true);
            });
          }
          setServerBrowserPanel(panel);
        });
      });
      if (taskStatsRefreshButton) {
        taskStatsRefreshButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void refreshLearningStats(serverTaskOwnerContext || currentAuthUsername);
        });
      }
      if (taskModeSwitchButton) {
        taskModeSwitchButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          taskBoardMode = "space";
          renderLessonTaskPanel(currentTaskPayload);
        });
      }
      if (taskSpaceFoldersButton) {
        taskSpaceFoldersButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          replayLatestTaskNotice();
        });
      }
      if (taskNoticeToggleButton) {
        taskNoticeToggleButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const owner = clean(serverTaskOwnerContext || currentAuthUsername);
          if (!owner || !currentAuthIsAdmin) {
            setLoadStatus("Open a learner folder before editing task notices.", true);
            setTaskNoticeAdminOpen(false);
            return;
          }
          setTaskNoticeAdminOpen(!taskNoticeAdminOpen, { focus: true });
        });
      }
      if (taskNoticeCloseButton) {
        taskNoticeCloseButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setTaskNoticeAdminOpen(false);
        });
      }
      if (taskEffectTestPendingButton) {
        taskEffectTestPendingButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          testLessonTaskEffects("pending");
        });
      }
      if (taskEffectTestOverdueButton) {
        taskEffectTestOverdueButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          testLessonTaskEffects("overdue");
        });
      }
      if (taskNoticeLanguage) {
        taskNoticeLanguage.addEventListener("change", () => {
          taskNoticeSetActiveLanguage(taskNoticeLanguage.value === "en" ? "en" : "vi");
          scheduleTaskNoticeProfilePreferenceSync(0);
        });
      }
      if (taskNoticeStyle) {
        taskNoticeStyle.addEventListener("change", () => {
          scheduleTaskNoticeProfilePreferenceSync(0);
        });
      }
      [
        [taskNoticeTextEn, "en"],
        [taskNoticeTextVi, "vi"],
      ].forEach(([node, language]) => {
        if (!node) return;
        node.addEventListener("focus", () => taskNoticeSetActiveLanguage(language));
        node.addEventListener("pointerdown", () => taskNoticeSetActiveLanguage(language));
        node.addEventListener("input", () => {
          taskNoticeSetActiveLanguage(language);
          scheduleTaskNoticeProfilePreferenceSync(700);
        });
        node.addEventListener("blur", () => {
          syncTaskNoticeLegacyFields();
          scheduleTaskNoticeProfilePreferenceSync(0);
        });
      });
      if (taskNoticeVoiceEn) {
        taskNoticeVoiceEn.addEventListener("change", () => {
          taskNoticeSetActiveLanguage("en");
          syncTaskNoticeLegacyFields();
        });
      }
      if (taskNoticeVoiceVi) {
        taskNoticeVoiceVi.addEventListener("change", () => {
          taskNoticeSetActiveLanguage("vi");
          syncTaskNoticeLegacyFields();
        });
      }
      if (taskNoticeTranslateEn) {
        taskNoticeTranslateEn.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void translateTaskNoticeToEnglish({ activate: false });
        });
      }
      if (taskNoticeTranslateVi) {
        taskNoticeTranslateVi.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void translateTaskNoticeToVietnamese({ activate: false });
        });
      }
      if (taskNoticeReset) {
        taskNoticeReset.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          resetTaskNoticeEditor();
        });
      }
      if (taskNoticeAdd) {
        taskNoticeAdd.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void saveTaskNotice();
        });
      }
      if (taskNoticeSendNow) {
        taskNoticeSendNow.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void saveTaskNotice({ sendNow: true });
        });
      }
      if (taskNoticePreview) {
        taskNoticePreview.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void previewTaskNoticeStyle();
        });
      }
      if (taskNoticeAvatarUpload && taskNoticeAvatarFile) {
        taskNoticeAvatarUpload.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          taskNoticeAvatarFile.click();
        });
        taskNoticeAvatarFile.addEventListener("change", () => {
          void uploadTaskNoticeAvatar();
        });
      }
      [taskNoticeName, taskNoticeAvatar].filter(Boolean).forEach((control) => {
        control.addEventListener("change", () => {
          scheduleTaskNoticeProfilePreferenceSync(0);
        });
        control.addEventListener("blur", () => {
          scheduleTaskNoticeProfilePreferenceSync(0);
        });
      });
      if (taskUserNoticeRead) {
        taskUserNoticeRead.addEventListener("pointerdown", (event) => event.stopPropagation());
      }
      if (aiNoticeSaveTitle) {
        aiNoticeSaveTitle.addEventListener("pointerdown", (event) => event.stopPropagation());
        aiNoticeSaveTitle.addEventListener("input", updateAiNoticeSaveButton);
        aiNoticeSaveTitle.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void saveAiNoticeHistory();
          }
        });
      }
      if (aiNoticeSaveButton) {
        aiNoticeSaveButton.addEventListener("pointerdown", (event) => event.stopPropagation());
        aiNoticeSaveButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void saveAiNoticeHistory();
        });
      }
      if (aiNoticeHistoryButton) {
        aiNoticeHistoryButton.addEventListener("pointerdown", (event) => event.stopPropagation());
        aiNoticeHistoryButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void openAiHistoryPanel();
        });
      }
      if (aiHistoryClose) {
        aiHistoryClose.addEventListener("pointerdown", (event) => event.stopPropagation());
        aiHistoryClose.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          closeAiHistoryPanel();
        });
      }
      if (aiHistoryPanel) {
        aiHistoryPanel.addEventListener("pointerdown", (event) => event.stopPropagation());
      }
      taskUserNoticeScrollButtons.forEach((button) => {
        button.addEventListener("pointerdown", (event) => event.stopPropagation());
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const direction = Math.max(-1, Math.min(1, Number(button.dataset.taskNoticeScroll || 0) || 0));
          const target = taskUserNoticeTextCopy || taskUserNoticeText;
          if (!target || !direction) {
            return;
          }
          const distance = Math.max(78, Math.round((target.clientHeight || 120) * 0.72));
          if (typeof target.scrollBy === "function") {
            target.scrollBy({ top: direction * distance, behavior: "smooth" });
          } else {
            target.scrollTop += direction * distance;
          }
        });
      });
      if (serverFullscreenButton) {
        serverFullscreenButton.addEventListener("click", toggleFullscreen);
      }
      if (serverCloseButton) {
        serverCloseButton.addEventListener("click", closeServerBrowser);
      }
      if (serverBrowser) {
        serverBrowser.addEventListener("pointerover", (event) => {
          const taskCard = event.target && event.target.closest ? event.target.closest(".ft-task-card") : null;
          if (taskCard) {
            triggerServerWorkspaceMotionBurst(taskCard, event.relatedTarget, { source: "hover" });
            if (!event.relatedTarget || !taskCard.contains(event.relatedTarget)) {
              scheduleTaskHoverPreview(taskCard);
            }
          }
        }, { passive: true });
        serverBrowser.addEventListener("pointerout", (event) => {
          const taskCard = event.target && event.target.closest ? event.target.closest(".ft-task-card") : null;
          if (taskCard && (!event.relatedTarget || !taskCard.contains(event.relatedTarget))) {
            hideTaskHoverPreview(taskCard);
          }
        }, { passive: true });
        serverBrowser.addEventListener("focusin", (event) => {
          const taskCard = event.target && event.target.closest ? event.target.closest(".ft-task-card") : null;
          if (taskCard) {
            scheduleTaskHoverPreview(taskCard);
          }
          triggerServerWorkspaceMotionBurst(event.target, event.relatedTarget, { source: "focus" });
        });
        serverBrowser.addEventListener("click", (event) => {
          if (event.target === serverBrowser) {
            triggerServerWorkspaceMotionBurst(serverBrowser, null, { source: "click" });
            return;
          }
          triggerServerWorkspaceMotionBurst(event.target, null, { source: "click" });
        });
      }
      if (vocabPreflightLearn) {
        vocabPreflightLearn.addEventListener("click", () => {
          void startVocabularyMissionFromPreflight();
        });
      }
      if (vocabPreflightSkip) {
        vocabPreflightSkip.addEventListener("click", () => {
          vocabPreflightBuildToken += 1;
          spaceWVocabBuildGuardPath = "";
          const state = vocabPreflightState || {};
          const pending = pendingSpaceWAfterVocabulary || {};
          const sourcePath = clean((pending.source && pending.source.path) || state.source_path || (currentVocabularyMission && currentVocabularyMission.source_path)).replace(/\\/g, "/");
          if (sourcePath) {
            spaceWVocabSkipPaths.add(sourcePath);
          }
          void resumeSpaceWAfterVocabulary();
        });
      }
      if (lessonEntryVocabAlertLearn && vocabPreflightLearn) {
        lessonEntryVocabAlertLearn.addEventListener("click", () => {
          vocabPreflightLearn.click();
          void releaseLessonEntryGateAfterVocabChoice();
        });
      }
      if (lessonEntryVocabAlertSkip && vocabPreflightSkip) {
        lessonEntryVocabAlertSkip.addEventListener("click", () => {
          vocabPreflightSkip.click();
          void releaseLessonEntryGateAfterVocabChoice();
        });
      }
      if (vocabPreflightGate) {
        vocabPreflightGate.addEventListener("click", (event) => {
          if (event.target === vocabPreflightGate && !vocabPreflightBusy) {
            setVocabPreflightStatus("Choose a route to continue this mission.");
          }
        });
      }
      if (vocabPictureFrame) {
        vocabPictureFrame.addEventListener("click", () => {
          openVocabImageLightbox();
        });
        vocabPictureFrame.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          openVocabImageLightbox();
        });
      }
      if (vocabImageLightboxClose) {
        vocabImageLightboxClose.addEventListener("click", closeVocabImageLightbox);
      }
      if (vocabImageLightboxPrev) {
        vocabImageLightboxPrev.addEventListener("click", () => stepVocabImageLightbox(-1));
      }
      if (vocabImageLightboxNext) {
        vocabImageLightboxNext.addEventListener("click", () => stepVocabImageLightbox(1));
      }
      if (vocabImageLightbox) {
        vocabImageLightbox.addEventListener("click", (event) => {
          if (event.target === vocabImageLightbox || (event.target && event.target.classList && event.target.classList.contains("ft-vocab-image-lightbox-backdrop"))) {
            closeVocabImageLightbox();
          }
        });
      }
      if (qSkipTypeButton) {
        qSkipTypeButton.addEventListener("click", skipQuestionTyping);
      }
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && vocabImageLightbox && vocabImageLightbox.classList.contains("is-open")) {
          event.preventDefault();
          closeVocabImageLightbox();
          return;
        }
        if (vocabImageLightbox && vocabImageLightbox.classList.contains("is-open") && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
          event.preventDefault();
          stepVocabImageLightbox(event.key === "ArrowLeft" ? -1 : 1);
          return;
        }
        if (!qRootCard || !qRootCard.classList.contains("is-typing")) {
          return;
        }
        if (event.key !== "Escape") {
          return;
        }
        const target = event.target;
        if (target && target.closest && target.closest("input, textarea, select, [contenteditable='true']")) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        skipQuestionTyping();
      }, true);
      if (qPlayButton) {
        qPlayButton.addEventListener("click", playQuestionAudio);
      }
      if (qShipPrevButton) {
        qShipPrevButton.addEventListener("click", () => stepQuestionShip(-1));
      }
      if (qShipNextButton) {
        qShipNextButton.addEventListener("click", () => stepQuestionShip(1));
      }
      if (qQuestionAudioButton) {
        qQuestionAudioButton.addEventListener("click", () => {
          void playQuestionPromptAudio();
        });
      }
      if (qInfoPlayButton) {
        qInfoPlayButton.addEventListener("click", () => {
          if (questionInfoAudioClip) {
            void playQuestionCardClip(questionInfoAudioClip);
          }
        });
      }
      if (qSideCardToggle) {
        qSideCardToggle.addEventListener("click", toggleQuestionSideCards);
      }
      if (qAnimationToggle) {
        qAnimationToggle.addEventListener("click", toggleQuestionAnimation);
      }
      if (qRootNoticeReplayButton) {
        qRootNoticeReplayButton.addEventListener("pointerdown", (event) => event.stopPropagation());
        qRootNoticeReplayButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void replayQuestionRootNotice();
        });
      }
      if (stageNode) {
        stageNode.addEventListener("pointermove", (event) => {
          if (Number.isFinite(Number(event.clientX)) && Number.isFinite(Number(event.clientY))) {
            questionLastPointerClient = { x: event.clientX, y: event.clientY };
          }
        }, { passive: true });
        stageNode.addEventListener("pointerdown", handleQuestionCardPointerDown, true);
        stageNode.addEventListener("pointerover", (event) => {
          const card = setQuestionCardFxHoverFromEvent(event, true);
          if (card) {
            activateQuestionCardFx(card, 0);
          }
        }, true);
        stageNode.addEventListener("pointermove", (event) => setQuestionCardFxHoverFromEvent(event, true), true);
        stageNode.addEventListener("pointerout", (event) => {
          const card = questionCardFxTargetFromEvent(event);
          if (!card) {
            return;
          }
          const nextTarget = event.relatedTarget;
          if (nextTarget && card.contains(nextTarget)) {
            return;
          }
          releaseQuestionCardFxHover(card, 1100);
        }, true);
        stageNode.addEventListener("pointerup", handleQuestionCardPointerUp, true);
        stageNode.addEventListener("click", handleQuestionCardClick, true);
        stageNode.addEventListener("focusin", (event) => pulseQuestionCardFxFromEvent(event, 2200), true);
        stageNode.addEventListener("keydown", handleQuestionEnterNext, true);
      }
      if (qRootCard) {
        qRootCard.tabIndex = 0;
        qRootCard.addEventListener("pointerdown", () => {
          try {
            qRootCard.focus({ preventScroll: true });
          } catch (_) {
            qRootCard.focus();
          }
          activateQuestionRootFocus(2600);
        });
        qRootCard.addEventListener("focusin", () => activateQuestionRootFocus(2200));
        qRootCard.addEventListener("focusout", (event) => {
          if (!qRootCard.contains(event.relatedTarget)) {
            clearQuestionRootFocus();
          }
        });
      }
      if (qPictureImg) {
        qPictureImg.addEventListener("load", () => {
          applyQuestionPictureNaturalSize();
          if (questionRootInfoActivePayload && questionRootInfoActivePayload.anchor === "picture_regions") {
            window.requestAnimationFrame(repositionActiveQuestionRootInfo);
          }
        });
        qPictureImg.addEventListener("dragstart", (event) => event.preventDefault());
      }
      if (qPictureZoomOut) {
        qPictureZoomOut.addEventListener("click", () => setQuestionPictureZoom(questionPictureZoom - 0.15));
      }
      if (qPictureZoomIn) {
        qPictureZoomIn.addEventListener("click", () => setQuestionPictureZoom(questionPictureZoom + 0.15));
      }
      if (qPictureZoomReset) {
        qPictureZoomReset.addEventListener("click", () => {
          resetQuestionPictureNaturalSize();
          applyQuestionPictureNaturalSize();
        });
      }
      if (shellNode) {
        let pictureConnectorPointerActive = false;
        let pictureConnectorFocusActive = false;
        let pictureConnectorPointerTimer = 0;
        let pictureConnectorFocusTimer = 0;
        const isPictureConnectorMotionTarget = (target) => Boolean(
          target
          && target.closest
          && target.closest("#ft-q-picture-card, .ft-q-root-info-card.is-picture-region-question, .ft-q-picture-region"),
        );
        const updatePictureConnectorMotion = () => {
          shellNode.classList.toggle("is-picture-card-hovering", Boolean(pictureConnectorPointerActive || pictureConnectorFocusActive));
        };
        const setPictureConnectorPointerMotion = (active, duration = 1200) => {
          if (pictureConnectorPointerTimer) {
            window.clearTimeout(pictureConnectorPointerTimer);
            pictureConnectorPointerTimer = 0;
          }
          pictureConnectorPointerActive = Boolean(active);
          updatePictureConnectorMotion();
          if (pictureConnectorPointerActive && Number(duration) > 0) {
            pictureConnectorPointerTimer = window.setTimeout(() => {
              pictureConnectorPointerTimer = 0;
              pictureConnectorPointerActive = false;
              updatePictureConnectorMotion();
            }, Math.max(350, Number(duration) || 1200));
          }
        };
        const setPictureConnectorFocusMotion = (active, duration = 2400) => {
          if (pictureConnectorFocusTimer) {
            window.clearTimeout(pictureConnectorFocusTimer);
            pictureConnectorFocusTimer = 0;
          }
          pictureConnectorFocusActive = Boolean(active);
          updatePictureConnectorMotion();
          if (pictureConnectorFocusActive) {
            pictureConnectorFocusTimer = window.setTimeout(() => {
              pictureConnectorFocusTimer = 0;
              pictureConnectorFocusActive = false;
              updatePictureConnectorMotion();
            }, Math.max(600, Number(duration) || 2400));
          }
        };
        const pulsePictureConnectorPointerMotion = (event) => {
          if (!isPictureConnectorMotionTarget(event.target)) {
            return;
          }
          setPictureConnectorPointerMotion(true, 0);
        };
        shellNode.addEventListener("pointerover", pulsePictureConnectorPointerMotion);
        shellNode.addEventListener("pointermove", pulsePictureConnectorPointerMotion);
        shellNode.addEventListener("pointerout", (event) => {
          if (!pictureConnectorPointerActive) {
            return;
          }
          const nextTarget = event.relatedTarget;
          if (nextTarget && shellNode.contains(nextTarget) && isPictureConnectorMotionTarget(nextTarget)) {
            return;
          }
          setPictureConnectorPointerMotion(false);
        });
        shellNode.addEventListener("focusin", (event) => {
          if (!isPictureConnectorMotionTarget(event.target)) {
            return;
          }
          setPictureConnectorFocusMotion(true, 2200);
        });
        shellNode.addEventListener("focusout", (event) => {
          const nextTarget = event.relatedTarget;
          if (nextTarget && shellNode.contains(nextTarget) && isPictureConnectorMotionTarget(nextTarget)) {
            return;
          }
          setPictureConnectorFocusMotion(false);
        });
      }
      questionConnectorPairs().forEach(([card, connector]) => {
        if (!card || !connector) {
          return;
        }
        card.tabIndex = 0;
        card.addEventListener("pointerdown", () => {
          try {
            card.focus({ preventScroll: true });
          } catch (_) {
            card.focus();
          }
          activateQuestionCardFx(card, 2600);
          activateQuestionConnector(card, connector, true);
        });
        card.addEventListener("focusin", () => {
          activateQuestionCardFx(card, 2200);
          activateQuestionConnector(card, connector, true);
        });
        card.addEventListener("focusout", (event) => {
          if (!card.contains(event.relatedTarget)) {
            clearQuestionConnectorFocus();
            clearQuestionCardFxActive(card);
          }
        });
      });
      if (qCheckButton) {
        qCheckButton.addEventListener("click", () => checkQuestionAnswer(qAnswerInput ? qAnswerInput.value : ""));
      }
      if (qAnswerInput) {
        qAnswerInput.addEventListener("input", handleQuestionAnswerInputValue);
        qAnswerInput.addEventListener("scroll", updateQuestionInputScrollbar, { passive: true });
        qAnswerInput.addEventListener("focus", () => {
          syncQuestionAnswerInputMemory();
          resizeQuestionAnswerInput();
        });
        qAnswerInput.addEventListener("keydown", (event) => {
          if (event.key !== "Enter") {
            return;
          }
          if (handleQuestionEnterNext(event)) {
            return;
          }
          event.preventDefault();
          checkQuestionAnswer(qAnswerInput.value);
        });
      }
      if (qShowAnswerButton) {
        qShowAnswerButton.addEventListener("click", showQuestionAnswer);
      }
      if (qSelectSubmitButton) {
        qSelectSubmitButton.addEventListener("pointerdown", (event) => {
          if (Number.isFinite(Number(event.clientX)) && Number.isFinite(Number(event.clientY))) {
            questionLastPointerClient = { x: event.clientX, y: event.clientY };
          }
          event.stopPropagation();
        });
        qSelectSubmitButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          submitQuestionSelectAnswer();
        });
      }
      if (qNextButton) {
        qNextButton.addEventListener("click", goQuestionNext);
      }
      if (completeReviewButton) {
        completeReviewButton.addEventListener("click", restartCurrentLessonFromBeginning);
      }
      if (completeSelectButton) {
        completeSelectButton.addEventListener("click", returnToServerFileSelection);
      }
      voicePickerClose.addEventListener("click", closeVoicePicker);
      voicePicker.addEventListener("click", (event) => {
        if (event.target === voicePicker) {
          closeVoicePicker();
        }
      });
      [ipaPanel, speakPanel].filter(Boolean).forEach((panel) => {
        panel.tabIndex = 0;
        panel.addEventListener("pointerdown", () => {
          try {
            panel.focus({ preventScroll: true });
          } catch (error) {
            try { panel.focus(); } catch (focusError) {}
          }
        });
      });
      const spaceWPanelHasFocus = (panel) => Boolean(
        panel
        && (
          document.activeElement === panel
          || panel.contains(document.activeElement)
          || panel.classList.contains("is-active-panel")
        )
      );
      const focusSpaceWListenCard = () => {
        if (!ipaPanel) {
          return;
        }
        try {
          ipaPanel.focus({ preventScroll: true });
        } catch (error) {
          try { ipaPanel.focus(); } catch (focusError) {}
        }
        setActivePanel(ipaPanel);
        if (ipaPanel.classList.contains("is-live")) {
          positionConnectorTo(ipaPanel);
        }
      };
      const handleSpaceWControlShortcut = () => {
        const listenLive = Boolean(ipaPanel && ipaPanel.classList.contains("is-live"));
        const speakLive = Boolean(speakPanel && speakPanel.classList.contains("is-live"));
        if (!listenLive && !speakLive) {
          return false;
        }
        if (speakLive && spaceWPanelHasFocus(speakPanel)) {
          toggleSpeakRecording();
          return true;
        }
        if (listenLive && spaceWPanelHasFocus(ipaPanel)) {
          focusSpaceWListenCard();
          void playEnglish();
          return true;
        }
        if (!speakLive && listenLive) {
          focusSpaceWListenCard();
          void playEnglish();
          return true;
        }
        if (speakLive) {
          toggleSpeakRecording();
          return true;
        }
        focusSpaceWListenCard();
        void playEnglish();
        return true;
      };
      document.addEventListener("keydown", (event) => {
        if (event.key === "F11") {
          event.preventDefault();
          event.stopPropagation();
          void (async () => {
            if (document.fullscreenElement && document.exitFullscreen) {
              await document.exitFullscreen();
              return;
            }
            const opened = await requestAnyFullscreen();
            if (!opened) {
              await toggleFullscreen();
            }
          })();
          return;
        }
        if (event.key === "Escape") {
          closeVoicePicker();
        }
        if ((event.key === "Control" || event.key === "Alt") && !event.repeat && handleSpaceWControlShortcut()) {
          event.preventDefault();
          event.stopPropagation();
        }
      }, true);
      voiceSelect.addEventListener("change", () => {
        voiceHint = voiceSelect.options[voiceSelect.selectedIndex]?.textContent || voiceSelect.value;
        updateVoiceSelectTone();
        refreshIpaForAccent(selectedVoiceAccent());
        setTtsStatus(listenStatusText());
        rememberCurrentSpaceWVoice();
        queueSpaceWProgressSave(120);
        warmSpaceWAudioCache(pendingLessonNodes.length ? pendingLessonNodes : lessonNodes, voiceSelect.value, {
          loadStatus: false,
          startIndex: currentNodeIndex,
          nodeLimit: LESSON_AUDIO_BACKGROUND_NODE_LIMIT,
          maxItems: 2,
          startDelayMs: 700,
        });
      });
      if (grammarOptionsNode) {
        grammarOptionsNode.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest(".ft-grammar-option") : null;
          if (!button || !grammarOptionsNode.contains(button)) {
            return;
          }
          handleGrammarOption(button.dataset.value, button);
        });
      }
      if (grammarSkipButton) {
        grammarSkipButton.addEventListener("click", skipGrammarQuestion);
        updateGrammarSkipButton();
      }
      if (grammarStartButton) {
        grammarStartButton.addEventListener("click", startGrammarQuizFromGate);
        setGrammarStartVisible(false);
      }
      if (grammarSilentButton) {
        grammarSilentButton.addEventListener("click", toggleGrammarSilent);
        updateGrammarSilentButton();
      }
      if (speakRecordButton) {
        speakRecordButton.addEventListener("click", toggleSpeakRecording);
      }
      if (speakModeToggleButton) {
        speakModeToggleButton.addEventListener("click", async () => {
          if (speakBusy || (speakRecorder && speakRecorder.state === "recording") || speakRecognitionActive) {
            return;
          }
          try {
            await refreshServerSettings();
          } catch (error) {
          }
          if (speakAiCheckVoiceServerManaged) {
            setSpeakStatus("Server Whisper is OFF. Browser live voice check is forced.", "");
            return;
          }
          speakAiCheckVoiceFallbackActive = false;
          setSpeakAiCheckVoice(!speakAiCheckVoice, true);
          resetSpeakResult();
          showSpeakPanel(true);
          setSpeakStatus(speakAiCheckVoice
            ? "AI check voice is ON. Record will use server speech analysis."
            : "AI check voice is OFF. Record will use browser live voice check.", "");
        });
      }
      if (speakReplayButton) {
        speakReplayButton.addEventListener("click", () => {
          void playSpeakReplay(false);
        });
        updateSpeakReplayButton();
        drawSpeakWave();
      }
      if (scoreWordsNode) {
        scoreWordsNode.addEventListener("click", handleSpaceWScoringAudioTokenClick);
        scoreWordsNode.addEventListener("keydown", handleSpaceWScoringAudioTokenKeydown);
      }
      if (speakWordsNode) {
        speakWordsNode.addEventListener("click", handleSpaceWScoringAudioTokenClick);
        speakWordsNode.addEventListener("keydown", handleSpaceWScoringAudioTokenKeydown);
      }
      [scoreHint, scoreMessage].forEach((node) => {
        if (node) {
          node.addEventListener("click", handleSpaceWScoreHintAudioClick);
        }
      });
      [hintText, aboutQuestion, aboutAnswer].forEach((node) => {
        if (node) {
          node.addEventListener("click", handleSpaceWUnlockedTextAudioClick);
        }
      });
      if (speakClearButton) {
        speakClearButton.addEventListener("click", () => {
          cancelSpeakRecording();
          resetSpeakResult();
          showSpeakPanel(true);
        });
      }
      if (speakReportButton) {
        speakReportButton.addEventListener("click", () => {
          void requestSpeakSkip();
        });
      }
      fileInput.addEventListener("change", handleLessonFileSelection);
      const fileLabel = fileInput.closest(".ft-file-label");
      if (fileLabel) {
        fileLabel.addEventListener("click", (event) => {
          if (event.target === fileInput) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          try {
            fileInput.click();
          } catch (error) {
            setLoadStatus("Trình duyệt chặn mở chọn file. Hãy bấm lại nút Chọn gói bài học.", true);
          }
        });
      }
      if (sampleButton) {
        sampleButton.addEventListener("click", loadSampleLesson);
      }
      let pendingBootstrapTimer = 0;
      const consumePendingBootstrapState = () => {
        const pending = window.__FTG_PENDING_BOOTSTRAP__;
        if (!pending || typeof pending !== "object") {
          return false;
        }
        if (applyRuntimeState(pending)) {
          if (pendingBootstrapTimer) {
            window.clearInterval(pendingBootstrapTimer);
            pendingBootstrapTimer = 0;
          }
          setLoadStatus("");
          return true;
        }
        return false;
      };
      window.addEventListener("message", (event) => {
        const data = event.data;
        if (!data || typeof data !== "object" || data.type !== "FTG_BOOTSTRAP_STATE") {
          return;
        }
        if (event.source && window.opener && event.source !== window.opener) {
          return;
        }
        if (applyRuntimeState(data.state)) {
          if (pendingBootstrapTimer) {
            window.clearInterval(pendingBootstrapTimer);
            pendingBootstrapTimer = 0;
          }
          setLoadStatus("");
        }
      });
      if (awaitingExternalBootstrap) {
        try {
          if (window.opener && window.opener !== window) {
            window.opener.postMessage({ type: "FTG_CHILD_READY" }, "*");
          }
        } catch (error) {
          setLoadStatus("Chua ket noi duoc cua so chinh.", true);
        }
        if (!consumePendingBootstrapState()) {
          setLoadStatus("Dang nhan du lieu tu cua so chinh...");
          pendingBootstrapTimer = window.setInterval(consumePendingBootstrapState, 160);
          window.setTimeout(() => {
            if (pendingBootstrapTimer) {
              window.clearInterval(pendingBootstrapTimer);
              pendingBootstrapTimer = 0;
            }
          }, 8000);
        }
      }
      const installDragScroll = () => {
        const interactiveSelector = [
          "button",
          "input",
          "select",
          "textarea",
          "label",
          "a",
          "[role='button']",
          "[class*='-card']",
          "[class*='-panel']",
          "[class*='-modal']",
          ".ft-space-navigator",
          ".ft-voice-picker",
          ".ft-load-gate",
          ".ft-auth-gate",
          ".ft-vocab-preflight-gate",
          ".ft-vocab-learned-panel",
          ".ft-game-modal",
          ".ft-world-modal",
          ".ft-cup-modal",
          ".ft-cup-reward-modal",
        ].join(",");
        const state = {
          active: false,
          pointerId: 0,
          startX: 0,
          startY: 0,
          scrollLeft: 0,
          scrollTop: 0,
          target: null,
        };
        const scrollTarget = () => {
          const doc = document.scrollingElement || document.documentElement;
          if (stageNode && (stageNode.scrollHeight > stageNode.clientHeight + 2 || stageNode.scrollWidth > stageNode.clientWidth + 2)) {
            return stageNode;
          }
          return doc;
        };
        const isScrollable = (node) => node && (node.scrollHeight > node.clientHeight + 2 || node.scrollWidth > node.clientWidth + 2);
        const stop = () => {
          if (!state.active) {
            return;
          }
          state.active = false;
          state.target = null;
          document.body.classList.remove("ft-drag-scroll-active");
        };
        const onPointerDown = (event) => {
          if (event.pointerType === "mouse" && event.button !== 0) {
            return;
          }
          const target = event.target;
          if (target && target.closest && target.closest(interactiveSelector)) {
            return;
          }
          const nextTarget = scrollTarget();
          if (!isScrollable(nextTarget)) {
            return;
          }
          stopQuestionCameraScrollAnimation();
          clearQuestionManualFocusTimer();
          stopSpaceNavigatorMotion();
          stopSpaceKeyboardNavigation();
          state.active = true;
          state.pointerId = event.pointerId;
          state.startX = event.clientX;
          state.startY = event.clientY;
          state.scrollLeft = nextTarget.scrollLeft;
          state.scrollTop = nextTarget.scrollTop;
          state.target = nextTarget;
          document.body.classList.add("ft-drag-scroll-active");
          try {
            stageNode && stageNode.setPointerCapture && stageNode.setPointerCapture(event.pointerId);
          } catch (error) {
          }
        };
        const onPointerMove = (event) => {
          if (!state.active || event.pointerId !== state.pointerId || !state.target) {
            return;
          }
          event.preventDefault();
          const dx = event.clientX - state.startX;
          const dy = event.clientY - state.startY;
          const sensitivity = event.pointerType === "mouse" ? 1.55 : 1.22;
          state.target.scrollLeft = state.scrollLeft - dx * sensitivity;
          state.target.scrollTop = state.scrollTop - dy * sensitivity;
          if (allPanelConnectors().some((node) => node.classList.contains("is-live"))) {
            positionConnector();
          }
        };
        if (stageNode) {
          stageNode.addEventListener("pointerdown", onPointerDown);
        }
        window.addEventListener("pointermove", onPointerMove, { passive: false });
        window.addEventListener("pointerup", stop);
        window.addEventListener("pointercancel", stop);
      };
      void restoreAuthSession();
      loadVoices();
      loadEdgeVoiceCatalog();
      applyBootstrapState();
      installPopupFullscreenGesture();
      installDragScroll();
      ensureSpaceNavigator();
      installSpaceKeyboardNavigation();
      if ("speechSynthesis" in window) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
      }
      const refreshVoiceListForViewport = () => {
        const nextMode = isMobileVoiceList() ? "mobile" : "desktop";
        if (nextMode !== lastVoiceListMode) {
          loadVoices();
        }
      };
      setupMobileInfiniteMotionSaver();
      let appViewportLayoutFrame = 0;
      let appViewportLayoutTimer = 0;
      let appViewportLayoutForce = false;
      const runAppViewportLayoutRefresh = () => {
        appViewportLayoutFrame = 0;
        const force = appViewportLayoutForce;
        appViewportLayoutForce = false;
        updateDesktopPanelLayout();
        positionConnector();
        positionVocabWeakConnector();
        positionVocabLearnedPanel();
        positionVocabSideCards();
        if (questionModeActive) {
          scheduleQuestionViewportLayoutRefresh(force ? 90 : 70, {
            force,
            guidanceDelays: force ? [0, 260, 620] : [0, 220],
          });
        } else {
          positionQuestionSideCards();
        }
        positionAuthConnectors();
        syncMobilePanelTabs();
        updateSpaceNavigatorVisibility();
        refreshVoiceListForViewport();
        scheduleTranslateCardPin(900);
        scheduleVocabCardPin(force ? 1200 : 900, force ? { force: true } : {});
      };
      const scheduleAppViewportLayoutRefresh = (delayMs = 0, options = {}) => {
        appViewportLayoutForce = appViewportLayoutForce || Boolean(options.force);
        const queueFrame = () => {
          if (!appViewportLayoutFrame) {
            appViewportLayoutFrame = window.requestAnimationFrame(runAppViewportLayoutRefresh);
          }
        };
        const wait = Math.max(0, Number(delayMs) || 0);
        if (wait > 0) {
          if (appViewportLayoutTimer) {
            window.clearTimeout(appViewportLayoutTimer);
          }
          appViewportLayoutTimer = window.setTimeout(() => {
            appViewportLayoutTimer = 0;
            queueFrame();
          }, wait);
          return;
        }
        if (appViewportLayoutTimer) {
          window.clearTimeout(appViewportLayoutTimer);
          appViewportLayoutTimer = 0;
        }
        queueFrame();
      };
      window.addEventListener("resize", () => {
        scheduleAppViewportLayoutRefresh(0);
        scheduleQuestionSelectRootOverlayReposition();
      });
      window.addEventListener("orientationchange", () => {
        scheduleAppViewportLayoutRefresh(260, { force: true });
        scheduleQuestionSelectRootOverlayReposition();
      });
      if (window.visualViewport) {
        let viewportLayoutTimer = 0;
        let viewportLayoutFrame = 0;
        let viewportLayoutForce = false;
        const scheduleViewportLayoutRefresh = (delayMs = 90) => {
          viewportLayoutForce = viewportLayoutForce || delayMs <= 80;
          if (viewportLayoutTimer || viewportLayoutFrame) {
            return;
          }
          viewportLayoutTimer = window.setTimeout(() => {
            viewportLayoutTimer = 0;
            viewportLayoutFrame = window.requestAnimationFrame(() => {
              viewportLayoutFrame = 0;
              const force = viewportLayoutForce;
              viewportLayoutForce = false;
              if (questionModeActive) {
                scheduleQuestionViewportLayoutRefresh(force ? 80 : 120, {
                  force,
                  guidanceDelays: force ? [0, 260] : [0, 280],
                });
              }
              if (vocabModeActive) {
                positionVocabLearnedPanel();
                scheduleVocabCardPin(900, { force: true });
              } else {
                scheduleTranslateCardPin(720);
              }
              updateSpaceNavigatorVisibility();
              scheduleQuestionSelectRootOverlayReposition();
            });
          }, Math.max(40, Number(delayMs) || 90));
        };
        window.visualViewport.addEventListener("resize", () => scheduleViewportLayoutRefresh(70), { passive: true });
        window.visualViewport.addEventListener("scroll", () => scheduleViewportLayoutRefresh(130), { passive: true });
      }
      if ("ResizeObserver" in window) {
        const questionLayoutObserver = new ResizeObserver(() => {
          scheduleQuestionViewportLayoutRefresh(questionRevealAnimationsActive ? 120 : 220, {
            force: false,
            guidanceDelays: questionRevealAnimationsActive ? [0, 360] : [0, 320],
          });
          scheduleQuestionSelectRootOverlayReposition();
        });
        window.__ftQuestionLayoutObserver = questionLayoutObserver;
        [qRootCard, qPictureCard, qAudioCard, qQuestionCard, qInfoCard].forEach((node) => {
          if (node) {
            questionLayoutObserver.observe(node);
          }
        });
        const vocabLayoutObserver = new ResizeObserver(() => window.requestAnimationFrame(positionVocabLearnedPanel));
        window.__ftVocabLayoutObserver = vocabLayoutObserver;
        [vocabCard, vocabLearnedPanel].forEach((node) => {
          if (node) {
            vocabLayoutObserver.observe(node);
          }
        });
      }
      answerInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          maybeAutoUnlockSpaceWAnswer(updateLiveScoringWithInputSound(true));
          return;
        }
        if (event.key === " " || event.code === "Space") {
          pendingSpaceWordCheck = true;
        }
      });
      answerInput.addEventListener("input", (event) => {
        clearWordTimeoutHint();
        const hasTypedText = Boolean(clean(answerInput.value));
        if (hasTypedText) {
          hideHintPanel();
        }
        const result = updateLiveScoringWithInputSound(false);
        if (!hasTypedText && !nextPanelCanShow) {
          showHintPanel(nodeHintText(currentNode), true);
        }
        if (pendingSpaceWordCheck || event.data === " " || /\s$/.test(answerInput.value || "")) {
          playFalseForCompletedWord(result);
        }
        maybeAutoUnlockSpaceWAnswer(result);
        if (typeof updateSpaceWTokenSupportTypedHighlights === "function") {
          updateSpaceWTokenSupportTypedHighlights();
        }
        pendingSpaceWordCheck = false;
        scheduleTranslateCardPin(360);
        queueSpaceWProgressSave(350);
      });
      answerInput.addEventListener("focus", () => scheduleTranslateCardPin(1800, { force: true }));
      answerInput.addEventListener("blur", () => scheduleTranslateCardPin(900, { force: true }));
      answerInput.addEventListener("scroll", syncAnswerHighlightScroll);
      window.addEventListener("resize", updateSpaceWTokenSupportVisibility);
      window.addEventListener("orientationchange", updateSpaceWTokenSupportVisibility);
      if (vocabAnswer) {
        vocabAnswer.addEventListener("input", () => {
          if (vocabAnswer.disabled || vocabAnswer.readOnly) {
            return;
          }
          clearVocabActiveHint();
          scheduleVocabTypeHintTimer(vocabItems[vocabCurrentIndex] || null, vocabCurrentIndex);
          scheduleVocabCardPin(420);
          scheduleVocabCupLeaderboardPrewarm(1800, { minGapMs: 15000 });
          scheduleCurrentLessonVaultCacheWarm(2200, { minGapMs: 45000 });
        });
        vocabAnswer.addEventListener("focus", () => scheduleVocabCardPin(1800, { force: true }));
        vocabAnswer.addEventListener("blur", () => scheduleVocabCardPin(900, { force: true }));
        vocabAnswer.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            if (typeof postSpaceVClientEvent === "function") {
              postSpaceVClientEvent("answer_keydown_enter", {
                typed: vocabAnswer.value,
                reason: `readonly=${Boolean(vocabAnswer.readOnly)} busy=${Boolean(vocabAnswerBusy)}`,
              });
            }
            void checkVocabAnswer();
          }
        });
        vocabAnswer.addEventListener("beforeinput", (event) => {
          if (vocabAnswer.disabled || vocabAnswer.readOnly) {
            event.preventDefault();
            return;
          }
          if (/insertFromPaste|insertFromDrop|insertReplacementText/i.test(event.inputType || "")) {
            event.preventDefault();
            setVocabFeedback("Typing only. Paste is blocked in Vocabulary mode.", "error");
            scheduleVocabCardPin(900, { force: true });
          }
        });
        ["paste", "drop", "cut", "copy"].forEach((eventName) => {
          vocabAnswer.addEventListener(eventName, (event) => {
            event.preventDefault();
            setVocabFeedback("Typing only. Clipboard actions are blocked here.", "error");
            scheduleVocabCardPin(900, { force: true });
          });
        });
      }
      vocabVoiceOptions.forEach((button) => {
        button.addEventListener("click", () => {
          setVocabVoice(button.dataset.voice || "sot:en-GB", { repairAudio: true });
        });
      });
      if (vocabLearnedFilter) {
        vocabLearnedFilter.addEventListener("input", () => {
          vocabRegistryFilterText = clean(vocabLearnedFilter.value).toLowerCase();
          renderVocabLearnedPanel();
          window.requestAnimationFrame(positionVocabLearnedPanel);
        });
      }
      void refreshServerSettings();
      const scheduleServerSettingsRefresh = () => {
        window.setTimeout(async () => {
          await refreshServerSettings();
          scheduleServerSettingsRefresh();
        }, document.hidden ? 180000 : 60000);
      };
      scheduleServerSettingsRefresh();
      window.addEventListener("focus", () => {
        void refreshServerSettings();
      });

      window.FutureTranslationGate = {
        setData(next) {
          lessonNodes = [next || {}];
          loadGate.classList.add("is-hidden");
          setNode(lessonNodes[0], 0);
        },
        async loadCode(rawCode) {
          const payload = await decodeFuturePayload(rawCode);
          setCurrentLessonSource({ source: "bridge", name: "bridge.Space_W" }, payload);
          loadLessonPayload(payload);
        },
      };
      const runInjectedPreviewCode = async () => {
        const rawPreviewCode = clean(window.__FTG_PREVIEW_CODE__ || "");
        if (!rawPreviewCode) {
          return;
        }
        try {
          completeAuth({ username: "Preview" });
          setLoadStatus("Opening preview...");
          const payload = await decodeFuturePayload(rawPreviewCode);
          const previewName = isParagraphPayload(payload)
              ? (payload.space_mode === "space_l" ? "preview.Space_L" : (payload.space_mode === "space_s" ? "preview.Space_S" : "preview.Space_P"))
            : (isVocabularyPayload(payload) ? "preview.Space_V" : (isQuestionPayload(payload) ? "preview.Space_Q" : "preview.Space_W"));
          setCurrentLessonSource({ source: "preview", name: previewName }, payload);
          loadLessonPayload(payload);
        } catch (error) {
          const message = error && error.message ? error.message : "Could not open preview payload.";
          setLoadStatus(message, true);
          setTtsStatus(message, true);
        }
      };
      if (window.__FTG_PREVIEW_CODE__) {
        window.setTimeout(() => {
          void runInjectedPreviewCode();
        }, 120);
      }
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
          void refreshServerSettings();
          return;
        }
        if (document.visibilityState === "hidden") {
          saveSpaceWProgressNow();
          saveQuestionProgressNow();
          saveVocabProgressNow();
          if (typeof window.__ftKeepaliveSpaceVProgress === "function") {
            window.__ftKeepaliveSpaceVProgress("visibility_hidden");
          }
          saveParagraphProgressNow();
          writeReloadSessionState();
        }
      });
      window.addEventListener("pagehide", () => {
        saveSpaceWProgressNow();
        saveQuestionProgressNow();
        saveVocabProgressNow();
        saveParagraphProgressNow();
        if (typeof window.__ftKeepaliveSpaceVProgress === "function") {
          window.__ftKeepaliveSpaceVProgress("pagehide");
        }
        writeReloadSessionState();
      }, { passive: true });
      window.addEventListener("beforeunload", () => {
        saveSpaceWProgressNow();
        saveQuestionProgressNow();
        saveVocabProgressNow();
        if (typeof window.__ftKeepaliveSpaceVProgress === "function") {
          window.__ftKeepaliveSpaceVProgress("beforeunload");
        }
        saveParagraphProgressNow();
        writeReloadSessionState();
        stopActiveAudio();
        cancelSpeakRecording();
        clearSpeakRecording();
      });
      window.addEventListener("popstate", handleFutureRouteNavigation);
    
