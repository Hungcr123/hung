
      // Added 2026-07-15: local PDF/Picture page progress drives Lesson Vault/Space Task UI without server recompute.
      const pdfProgressOverrideFromRecord = (record = null) => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const total = Math.max(0, Math.floor(Number(source.pages ?? state.pages ?? source.nodeCount ?? state.nodeCount ?? (pdfState && pdfState.pages) ?? 0) || 0));
        if (!total) {
          return null;
        }
        const mode = clean(source.mode || state.mode || (pdfState && pdfState.mode) || "pdf") === "picture" ? "picture" : "pdf";
        const page = Math.max(1, Math.min(total, Math.floor(Number(source.page ?? state.page ?? 1) || 1)));
        const done = page;
        const percent = Math.max(0, Math.min(100, Math.round((done / total) * 100)));
        return {
          space: mode === "picture" ? "Space_Picture" : "Space_PDF",
          label: "Page",
          done,
          total,
          percent,
          text: `${done}/${total}`,
          node_done: done,
          node_total: total,
          nodes_text: `${done}/${total}`,
          completed: done >= total,
          in_progress: done > 0 && done < total,
          activeRun: done > 0 && done < total,
          syncing: true,
          pending_sync: true,
        };
      };

      const syncPdfLessonProgressOverride = (record = null) => {
        if (typeof setLessonProgressOverride !== "function") {
          return null;
        }
        const progress = pdfProgressOverrideFromRecord(record);
        if (!progress) {
          return null;
        }
        const paths = [
          typeof currentLessonStudyPath === "function" ? currentLessonStudyPath() : "",
          pdfState && pdfState.path,
          currentLessonSource && currentLessonSource.path,
          currentLessonSource && currentLessonSource.effective_path,
          currentLessonSource && currentLessonSource.link_target,
          currentLessonSource && currentLessonSource.linked_path,
          record && record.path,
          record && record.legacy_path,
        ].map((path) => normalizeServerPathValue(path || "")).filter(Boolean);
        if (!paths.length) {
          return progress;
        }
        setLessonProgressOverride(paths, progress, 120000);
        if (typeof rememberLessonVaultProgressPin === "function") {
          rememberLessonVaultProgressPin(paths, progress, 120000);
        }
        if (typeof pinVisibleLessonVaultProgressRing === "function") {
          pinVisibleLessonVaultProgressRing(paths, progress, { retryMs: 80 });
        }
        if (typeof clearLessonProgressDisplayCaches === "function") {
          clearLessonProgressDisplayCaches(paths, progress.space || "");
        }
        return progress;
      };

      const renderPdfPage = async (options = {}) => {
        if (!pdfModeActive || !pdfState.path || !pdfEls) {
          return;
        }
        if (!(options && options.skipDrawingFlush) && typeof flushPdfDrawingBeforePageChange === "function") {
          await flushPdfDrawingBeforePageChange();
        }
        const requestToken = ++pdfRenderRequestToken;
        pdfPrefetchSerial += 1;
        abortPdfPrefetchRequests();
        stopPdfBackgroundPageCache();
        if (pdfState && pdfState.localImageActive && typeof isPdfLocalImageRuntimeValid === "function" && !isPdfLocalImageRuntimeValid()) {
          resetPdfLocalImageRuntimeState();
          renderPdfLocalImageUi();
        }
        const isLocalImageMode = Boolean(pdfState && pdfState.localImageActive && (typeof isPdfLocalImageRuntimeValid !== "function" || isPdfLocalImageRuntimeValid()));
        const isPictureMode = pdfState.mode === "picture";
        const requestState = {
          mode: pdfState.mode || "pdf",
          path: normalizeServerPathValue(pdfState.path || ""),
          page: Math.max(1, Math.min(Math.max(1, pdfState.pages || 1), Math.floor(Number(pdfState.page || 1) || 1))),
          scale: pdfState.scale || 2,
        };
        const isCurrentRenderRequest = () => (
          pdfModeActive
          && requestToken === pdfRenderRequestToken
          && Boolean(pdfState.localImageActive) === isLocalImageMode
          && pdfState.mode === requestState.mode
          && normalizeServerPathValue(pdfState.path || "") === requestState.path
          && Math.max(1, Math.floor(Number(pdfState.page || 1) || 1)) === requestState.page
          && String(pdfState.scale || 2) === String(requestState.scale || 2)
        );
        const clearVocab = options && Object.prototype.hasOwnProperty.call(options, "clearVocab") ? Boolean(options.clearVocab) : true;
        if (!isPictureMode) {
          ensurePdfRenderScaleForView();
          requestState.scale = pdfState.scale || requestState.scale;
        }
        const requestCacheKey = pdfPageCacheKey(requestState.page, requestState);
        const totalPages = Math.max(1, Math.floor(Number(pdfState.pages || 1) || 1));
        const pageLabel = `${isPictureMode ? "Picture" : "PDF"} ${requestState.page}/${totalPages}`;
        const renderMessage = isPictureMode
          ? `Dang tai ${pageLabel}...`
          : (options.reason === "resolution" ? `Dang lam net ${pageLabel}...` : `Dang tai ${pageLabel}...`);
        setPdfStatus(renderMessage);
        setPdfPageRendering(true, renderMessage);
        clearPdfPenCanvas();
        if (clearVocab) {
          updatePdfVocabStats(null);
        }
        try {
          if (isLocalImageMode) {
            const slotIndex = Math.max(0, Math.min(3, Math.floor(Number(pdfState.localImageSlotIndex || 0) || 0)));
            const slot = typeof activePdfLocalImageSlot === "function" ? activePdfLocalImageSlot() : null;
            const url = clean(pdfState.localImageDataUrl || (slot && slot.dataUrl) || "");
            if (!url || !/^(data:image\/|blob:)/i.test(url)) {
              throw new Error("This local image slot is empty.");
            }
            await new Promise((resolve, reject) => {
              let settled = false;
              const finish = (ok, error = null) => {
                if (settled) return;
                settled = true;
                pdfEls.image.onload = null;
                pdfEls.image.onerror = null;
                if (ok) resolve();
                else reject(error || new Error("Could not open this local image."));
              };
              if (pdfEls.image.src === url && pdfEls.image.complete) {
                finish(true);
                return;
              }
              pdfEls.image.onload = () => finish(true);
              pdfEls.image.onerror = () => finish(false, new Error("Could not open this local image."));
              pdfEls.image.src = url;
            });
            if (!isCurrentRenderRequest()) {
              return;
            }
            if (pdfEls.wrap) {
              pdfEls.wrap.classList.remove("is-empty");
            }
            pdfState.pagePointWidth = Number(pdfEls.image.naturalWidth || pdfState.localImageWidth || 1) || 1;
            pdfState.pagePointHeight = Number(pdfEls.image.naturalHeight || pdfState.localImageHeight || 1) || 1;
            pdfState.baseDisplayWidth = 0;
            applyPdfZoom();
            if (typeof schedulePdfPageSideDataLoad === "function") {
              schedulePdfPageSideDataLoad(220, { source: "local_image_render" });
            } else {
              void loadPdfDrawingLayer({ clientSource: "pdf_render_local_image_drawing" });
            }
            pdfAudioMarkers = [];
            pdfState.audioMarkers = [];
            if (typeof renderPdfSharedAudioMarkers === "function") {
              renderPdfSharedAudioMarkers();
            }
            pdfState.aiRegionNotices = [];
            pdfState.aiRegionQuestions = [];
            if (typeof renderPdfAiRegionNoticeHitboxes === "function") {
              renderPdfAiRegionNoticeHitboxes();
            }
            syncPdfSelectionOverlay(true);
            updatePdfChrome();
            setPdfStatus(`Local image slot ${slotIndex + 1}. Ghost Eye ready for OCR. Use Return in Local Images to go back.`);
            return;
          }
          const cachedFull = pdfPageCache.get(requestCacheKey);
          if (!(cachedFull && cachedFull.url)) {
            await loadPdfPageQuickPreview(requestState, isCurrentRenderRequest);
            if (!isCurrentRenderRequest()) {
              return;
            }
          } else {
            showPdfLoaderThumbnail(cachedFull.url);
          }
          const entry = await fetchPdfPageCached(requestState.page, { trackProgress: true, isCurrent: isCurrentRenderRequest });
          if (!isCurrentRenderRequest()) {
            return;
          }
          const url = entry.url;
          pdfState.objectUrl = url;
          await new Promise((resolve, reject) => {
            if (!isCurrentRenderRequest()) {
              resolve();
              return;
            }
            let settled = false;
            let loadTimer = 0;
            const finish = (ok, error = null) => {
              if (settled) return;
              settled = true;
              if (loadTimer) {
                window.clearTimeout(loadTimer);
                loadTimer = 0;
              }
              pdfEls.image.onload = null;
              pdfEls.image.onerror = null;
              if (ok) resolve();
              else reject(error || new Error(isPictureMode ? "Could not render picture." : "Could not render PDF image."));
            };
            if (pdfEls.image.src === url && pdfEls.image.complete) {
              finish(true);
              return;
            }
            pdfEls.image.onload = () => {
              finish(true);
            };
            pdfEls.image.onerror = () => {
              pdfPageCache.delete(requestCacheKey);
              finish(false, new Error(isPictureMode ? "Could not render picture." : "Could not render PDF image."));
            };
            loadTimer = window.setTimeout(() => {
              if (!isCurrentRenderRequest()) {
                finish(true);
                return;
              }
              pdfPageCache.delete(requestCacheKey);
              finish(false, new Error(isPictureMode ? "Picture loading timed out. Please retry." : "PDF page loading timed out. Please retry."));
            }, 18000);
            pdfEls.image.src = url;
          });
          if (!isCurrentRenderRequest()) {
            return;
          }
          if (pdfEls.wrap) {
            pdfEls.wrap.classList.remove("is-empty");
          }
          if (!isPictureMode && pdfEls.image.naturalWidth && pdfState.scale) {
            pdfState.pagePointWidth = Number(pdfEls.image.naturalWidth) / Math.max(0.5, Number(pdfState.scale || 1) || 1);
            pdfState.pagePointHeight = Number(pdfEls.image.naturalHeight || 0) / Math.max(0.5, Number(pdfState.scale || 1) || 1);
          }
          pdfState.baseDisplayWidth = 0;
          applyPdfZoom();
          if (typeof schedulePdfPageSideDataLoad === "function") {
            schedulePdfPageSideDataLoad(360, { source: "render_page_complete" });
          } else {
            void loadPdfDrawingLayer({ clientSource: "pdf_render_drawing" });
            void loadPdfSharedAudioMarkers({ clientSource: "pdf_render_audio" });
            void loadPdfAiRegionNotices({ clientSource: "pdf_render_notices" });
            void loadPdfAiRegionQuestions({ clientSource: "pdf_render_questions" });
          }
          syncPdfSelectionOverlay(true);
          updatePdfChrome();
          const timing = entry && entry.timing ? entry.timing : null;
          const timingText = timing
            ? `Load ${Math.round(Number(timing.networkMs || 0))}ms${Number(timing.serverMs || 0) ? ` | server ${Math.round(Number(timing.serverMs || 0))}ms` : ""}${Number(timing.bytes || 0) ? ` | ${Math.round(Number(timing.bytes || 0) / 1024)}KB` : ""}. `
            : "";
          setPdfStatus(`${isPictureMode ? "Picture" : (pdfState.hasTextLayer ? "Digital PDF" : "Image PDF")}. ${timingText}${!isPictureMode ? `Render ${Math.round((Number(pdfState.scale || 1) || 1) * 100)}%. ` : ""}${pdfState.tesseractReady ? "Ghost Eye ready." : "Ghost Eye limited."} Press \` to select one region.`);
          prefetchPdfNeighborPages();
        } catch (error) {
          if (isCurrentRenderRequest()) {
            setPdfStatus(error && error.message ? error.message : (isPictureMode ? "Could not render picture." : "Could not render PDF page."), true);
          }
        } finally {
          // Updated 2026-07-22: the latest request owns the shared loader even if
          // progress restore changed page/scale while that request was running.
          if (requestToken === pdfRenderRequestToken) {
            setPdfPageRendering(false);
          }
        }
      };

      const pdfGoToPage = async (pageValue) => {
        const initialPdfLoadPending = Boolean(
          pdfEls && pdfEls.root && pdfEls.root.classList.contains("is-rendering-page")
          && Math.max(1, Number(pdfState.pages || 1) || 1) <= 1
        );
        if (initialPdfLoadPending) {
          return;
        }
        const totalPages = Math.max(1, pdfState.pages || 1);
        const rawPage = Math.floor(Number(pageValue) || 1);
        const currentPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1));
        const direction = rawPage === currentPage + 1 ? 1 : (rawPage === currentPage - 1 ? -1 : 0);
        const pendingBase = pdfPendingPage || currentPage;
        const page = Math.max(1, Math.min(totalPages, direction ? pendingBase + direction : rawPage));
        if (pdfState && pdfState.localImageActive && typeof isPdfLocalImageRuntimeValid === "function" && !isPdfLocalImageRuntimeValid()) {
          resetPdfLocalImageRuntimeState();
          renderPdfLocalImageUi();
        }
        if (pdfState && pdfState.localImageActive) {
          await openPdfLocalImageSlot(page - 1);
          return;
        }
        if (page === pdfState.page && !pdfPendingPage && pdfEls && pdfEls.image && pdfEls.image.src) {
          return;
        }
        pdfPendingPage = page;
        if (pdfPageNavigationPromise) {
          return await pdfPageNavigationPromise;
        }
        pdfPageNavigationPromise = (async () => {
          while (pdfPendingPage) {
            let targetPage = pdfPendingPage;
            pdfPendingPage = 0;
            if (typeof flushPdfDrawingBeforePageChange === "function") {
              await flushPdfDrawingBeforePageChange();
            }
            if (pdfPendingPage) {
              targetPage = pdfPendingPage;
              pdfPendingPage = 0;
            }
            if (targetPage === pdfState.page && pdfEls && pdfEls.image && pdfEls.image.src) {
              continue;
            }
            const previousPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1));
            pdfPageNavigationSerial += 1;
            if (typeof pdfProgressSaveTimer !== "undefined" && pdfProgressSaveTimer) {
              window.clearTimeout(pdfProgressSaveTimer);
              pdfProgressSaveTimer = 0;
            }
            clearPdfGhostScanStateForPageChange();
            pdfState.page = targetPage;
            updatePdfChrome();
            if (typeof recordPdfPageVisit === "function") {
              recordPdfPageVisit(targetPage, { deferSave: true });
            }
            if (typeof savePdfProgressLocalNow === "function") {
              savePdfProgressLocalNow({ skipLastFilePost: true });
            }
            await renderPdfPage({ skipDrawingFlush: true });
            schedulePdfProgressSave(700, {
              source: "pdf_page_turn",
              uiAction: "pdf.page_turn",
              trigger: targetPage === previousPage + 1 ? "next" : (targetPage === previousPage - 1 ? "previous" : "jump"),
              fromPage: previousPage,
              toPage: targetPage,
              retry: 0,
              skipLastFilePost: true,
            });
          }
        })();
        try {
          return await pdfPageNavigationPromise;
        } finally {
          pdfPageNavigationPromise = null;
        }
      };

      const setPdfSelectionArmed = (armed = false) => {
        if (!pdfEls || !pdfEls.wrap) {
          return;
        }
        const next = Boolean(armed);
        pdfEls.wrap.classList.toggle("is-selecting", next);
        if (pdfEls.selectButton) {
          pdfEls.selectButton.classList.toggle("is-active", next);
        }
        syncPdfCompactDock();
      };

      const setPdfShiftSelectionActive = (active = false) => {
        pdfShiftSelectionActive = Boolean(active);
        if (pdfEls && pdfEls.wrap) {
          pdfEls.wrap.classList.toggle("is-shift-selecting", pdfShiftSelectionActive);
        }
      };

      const hasPdfAppendableSelection = () => Boolean(
        pdfState
        && (
          (Array.isArray(pdfState.selections) && pdfState.selections.length)
          || (
            pdfState.selection
            && Number(pdfState.selection.w || 0) > 0
            && Number(pdfState.selection.h || 0) > 0
          )
        )
      );

      const isPdfAppendSelectionRequested = (event = null) => Boolean(
        hasPdfAppendableSelection()
        && (pdfShiftSelectionActive || Boolean(event && event.shiftKey))
      );

      const consumePdfAppendSelectionRequest = () => {
        if (pdfShiftSelectionActive) {
          setPdfShiftSelectionActive(false);
        }
      };

      const armPdfSelectionOnce = () => {
        if (!pdfEls || !pdfEls.wrap) {
          return;
        }
        clearPdfSelectionOverlay();
        setPdfSelectionArmed(true);
        const surface = pdfState.mode === "picture" ? "picture" : "PDF page";
        setPdfStatus(`Ghost Eye armed once. Draw one rectangle on the ${surface}. After that, drag returns to pan.`);
      };

      const togglePdfSelectionMode = () => {
        const hasPointSelection = Boolean(pdfPointSelectStart);
        const selectionCount = Array.isArray(pdfState && pdfState.selections) ? pdfState.selections.length : 0;
        const hasSelection = Boolean(
          pdfState
          && (
            selectionCount
            || (
              pdfState.selection
              && Number(pdfState.selection.w || 0) > 0
              && Number(pdfState.selection.h || 0) > 0
            )
          )
        );
        if (hasSelection && pdfShiftSelectionActive) {
          if (pdfState && pdfState.ghostConsoleVisible) {
            setPdfGhostConsoleVisible(false, { silent: true });
          }
          clearPdfPointSelection();
          setPdfSelectionArmed(true);
          setPdfStatus("Ghost Eye add-region armed. Draw one more rectangle; Shift again cancels add mode.");
          return;
        }
        if (hasPointSelection || hasSelection) {
          setPdfShiftSelectionActive(false);
          clearPdfSelectionOverlay();
          setPdfSelectionArmed(false);
          setPdfGhostConsoleVisible(false, { silent: true });
          schedulePdfProgressSave(120);
          setPdfStatus(hasPointSelection ? "Ghost Eye points cleared. Press ` or right-click to start again." : "Ghost Eye region cleared. Press ` again to draw a new region.");
          return;
        }
        const isArmed = Boolean(pdfEls && pdfEls.wrap && pdfEls.wrap.classList.contains("is-selecting"));
        if (isArmed) {
          setPdfShiftSelectionActive(false);
          setPdfSelectionArmed(false);
          clearPdfSelectionOverlay();
          setPdfGhostConsoleVisible(false, { silent: true });
          schedulePdfProgressSave(120);
          setPdfStatus("Ghost Eye selection cancelled. Press ` again to draw one region.");
          return;
        }
        if (pdfState && pdfState.ghostConsoleVisible) {
          setPdfGhostConsoleVisible(false, { silent: true });
        }
        armPdfSelectionOnce();
      };

      function handlePdfKeyboardShortcuts(event) {
        if (!pdfModeActive || event.repeat) {
          return;
        }
        if (event.key === "Control" && pdfEls && pdfEls.speakModal && !pdfEls.speakModal.classList.contains("is-hidden")) {
          event.preventDefault();
          void togglePdfSpeakTrainingRecording();
          return;
        }
        const target = event.target;
        const editable = target && (
          /^(input|textarea|select)$/i.test(target.tagName || "")
          || target.isContentEditable
        );
        if (editable) {
          return;
        }
        if (event.key === "Shift") {
          event.preventDefault();
          if (hasPdfAppendableSelection()) {
            const next = !pdfShiftSelectionActive;
            setPdfShiftSelectionActive(next);
            setPdfGhostConsoleVisible(false, { silent: true });
            if (next) {
              setPdfStatus("Ghost Eye add-region armed. Select one more region now; no need to hold Shift.");
            } else {
              setPdfStatus("Ghost Eye add-region mode cancelled.");
            }
          } else {
            setPdfShiftSelectionActive(false);
            setPdfStatus("Create one Ghost Eye region first, then press Shift to add another region.");
          }
          return;
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          void pdfGoToPage((pdfState.page || 1) - 1);
          return;
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          void pdfGoToPage((pdfState.page || 1) + 1);
          return;
        }
        if (event.key === "`" || event.code === "Backquote") {
          event.preventDefault();
          togglePdfSelectionMode();
        }
      }

      function handlePdfKeyboardUp(event) {
        if (!pdfModeActive) {
          return;
        }
      }

      const pdfPointInImage = (event) => {
        if (!pdfEls || !pdfEls.image) {
          return null;
        }
        const rect = pdfEls.image.getBoundingClientRect();
        const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
        const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
        return { x, y, width: rect.width, height: rect.height };
      };

      const paintPdfSelection = (start, end) => {
        if (!pdfEls || !pdfEls.selection || !start || !end) {
          return;
        }
        const left = Math.min(start.x, end.x);
        const top = Math.min(start.y, end.y);
        const width = Math.abs(end.x - start.x);
        const height = Math.abs(end.y - start.y);
        Object.assign(pdfEls.selection.style, {
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
        });
        pdfEls.selection.classList.toggle("is-visible", width > 4 && height > 4);
      };

      const commitPdfSelectionFromPoints = (start, end, options = {}) => {
        if (!start || !end || !start.width || !start.height) {
          return false;
        }
        const left = Math.min(start.x, end.x);
        const top = Math.min(start.y, end.y);
        const width = Math.abs(end.x - start.x);
        const height = Math.abs(end.y - start.y);
        if (width < 12 || height < 12) {
          if (pdfEls && pdfEls.selection) pdfEls.selection.classList.remove("is-visible");
          clearPdfPointSelection();
          setPdfSelectionArmed(false);
          setPdfStatus("Selection is too small.", true);
          return false;
        }
        const nextSelection = {
          x: left / start.width,
          y: top / start.height,
          w: width / start.width,
          h: height / start.height,
        };
        const appendMode = Boolean(options.append);
        const currentSelections = normalizePdfSelectionList(
          Array.isArray(pdfState.selections) && pdfState.selections.length
            ? pdfState.selections
            : (pdfState.selection ? [pdfState.selection] : [])
        );
        pdfState.selections = appendMode ? [...currentSelections, nextSelection].slice(-12) : [nextSelection];
        pdfState.selection = nextSelection;
        clearPdfPointSelection();
        syncPdfSelectionOverlay();
        updatePdfChrome();
        renderPdfAiRegionNoticeHitboxes();
        runPdfSelectionTwinBuild(start, end, { latestOnly: true });
        window.setTimeout(() => {
          schedulePdfSelectionTechBurst(10000);
        }, 900);
        setPdfSelectionArmed(false);
        schedulePdfProgressSave(120, { skipLastFileSync: true });
        if (options.status) {
          setPdfStatus(options.status);
        }
        consumePdfAppendSelectionRequest();
        void runPdfOcrSelection({ append: appendMode, selection: nextSelection });
        return true;
      };

      function handlePdfRightClickPointSelection(event) {
        if (!pdfModeActive || !pdfEls || !pdfEls.wrap || !pdfEls.image) {
          return;
        }
        const point = pdfPointInImage(event);
        if (!point || !point.width || !point.height) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        const hasExistingSelection = Boolean(
          pdfState
          && (
            (Array.isArray(pdfState.selections) && pdfState.selections.length)
            || pdfState.selection
          )
        );
        const appendMode = Boolean(hasExistingSelection && (pdfShiftSelectionActive || event.shiftKey));
        if (!pdfPointSelectStart) {
          if (!appendMode) {
            clearPdfSelectionOverlay({ skipAiRegionRender: true });
          }
          setPdfSelectionArmed(false);
          setPdfGhostConsoleVisible(false, { silent: true });
          pdfPointSelectStart = { ...point, append: appendMode };
          showPdfSelectionPoint(point);
          setPdfStatus(appendMode
            ? "Ghost Eye add-point locked. Right-click the second corner to add this region."
            : "Ghost Eye point locked. Right-click the second corner to create the region.");
          return;
        }
        const start = pdfPointSelectStart;
        paintPdfSelection(start, point);
        commitPdfSelectionFromPoints(start, point, {
          append: Boolean(start.append || appendMode),
          status: (start.append || appendMode)
            ? "Ghost Eye added another region."
            : "Ghost Eye region created from two points.",
        });
      }

      function isPdfTextDraftEventTarget(target) {
        return Boolean(target && target.closest && target.closest(".ft-pdf-text-draft"));
      }

      function handlePdfRightPointerSelection(event) {
        const isRightButton = event && (event.button === 2 || (Number(event.buttons || 0) & 2));
        if (!isRightButton) {
          return;
        }
        if (isPdfTextDraftEventTarget(event && event.target)) {
          return;
        }
        if (typeof pdfSharedAudioMarkerTarget === "function" && pdfSharedAudioMarkerTarget(event && event.target)) {
          return;
        }
        pdfRightClickPointHandledAt = Date.now();
        handlePdfRightClickPointSelection(event);
      }

      function handlePdfRightContextSelection(event) {
        if (isPdfTextDraftEventTarget(event && event.target)) {
          return;
        }
        if (typeof pdfSharedAudioMarkerTarget === "function" && pdfSharedAudioMarkerTarget(event && event.target)) {
          return;
        }
        if (Date.now() - pdfRightClickPointHandledAt < 650) {
          if (event) {
            event.preventDefault();
            event.stopPropagation();
          }
          return;
        }
        handlePdfRightClickPointSelection(event);
      }

      function startPdfRegionDrag(event) {
        if (!pdfModeActive || !pdfEls || !pdfEls.wrap) {
          return;
        }
        if (isPdfTextDraftEventTarget(event && event.target)) {
          return;
        }
        if (typeof handlePdfSharedAudioStagePointerDown === "function" && handlePdfSharedAudioStagePointerDown(event)) {
          return;
        }
        if (!pdfEls.wrap.classList.contains("is-selecting")) {
          return;
        }
        const point = pdfPointInImage(event);
        if (!point || !point.width || !point.height) {
          return;
        }
        event.preventDefault();
        pdfSelectDrag = { start: point, end: point, pointerId: event.pointerId };
        try {
          pdfEls.wrap.setPointerCapture(event.pointerId);
        } catch (error) {
        }
        paintPdfSelection(point, point);
      }

      function movePdfRegionDrag(event) {
        if (!pdfSelectDrag || !pdfModeActive) {
          return;
        }
        const point = pdfPointInImage(event);
        if (!point) {
          return;
        }
        pdfSelectDrag.end = point;
        paintPdfSelection(pdfSelectDrag.start, pdfSelectDrag.end);
      }

      function finishPdfRegionDrag(event) {
        if (!pdfSelectDrag || !pdfModeActive) {
          return;
        }
        const drag = pdfSelectDrag;
        pdfSelectDrag = null;
        try {
          if (pdfEls && pdfEls.wrap) pdfEls.wrap.releasePointerCapture(drag.pointerId);
        } catch (error) {
        }
        const end = pdfPointInImage(event) || drag.end;
        const left = Math.min(drag.start.x, end.x);
        const top = Math.min(drag.start.y, end.y);
        const width = Math.abs(end.x - drag.start.x);
        const height = Math.abs(end.y - drag.start.y);
        if (width < 12 || height < 12 || !drag.start.width || !drag.start.height) {
          if (pdfEls && pdfEls.selection) pdfEls.selection.classList.remove("is-visible");
          setPdfSelectionArmed(false);
          setPdfStatus("Selection is too small.", true);
          return;
        }
        commitPdfSelectionFromPoints(drag.start, end, {
          append: isPdfAppendSelectionRequested(event),
          status: isPdfAppendSelectionRequested(event) ? "Ghost Eye added another dragged region." : "",
        });
      }

      function startPdfPanDrag(event) {
        if (!pdfModeActive || !pdfEls || !pdfEls.stage || !pdfEls.wrap) {
          return;
        }
        if (isPdfTextDraftEventTarget(event && event.target)) {
          return;
        }
        if (typeof handlePdfSharedAudioStagePointerDown === "function" && handlePdfSharedAudioStagePointerDown(event)) {
          return;
        }
        if (pdfEls.wrap.classList.contains("is-selecting")) {
          return;
        }
        if (event.button != null && event.button !== 0) {
          return;
        }
        const interactive = event.target && event.target.closest
          ? event.target.closest("button,input,textarea,select,a,[data-pdf-action]")
          : null;
        if (interactive) {
          return;
        }
        event.preventDefault();
        pdfPanDrag = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          scrollLeft: pdfEls.stage.scrollLeft,
          scrollTop: pdfEls.stage.scrollTop,
        };
        pdfEls.stage.classList.add("is-panning");
        try {
          pdfEls.stage.setPointerCapture(event.pointerId);
        } catch (error) {
        }
      }

      function movePdfPanDrag(event) {
        if (!pdfPanDrag || !pdfModeActive || !pdfEls || !pdfEls.stage) {
          return;
        }
        event.preventDefault();
        const dx = event.clientX - pdfPanDrag.startX;
        const dy = event.clientY - pdfPanDrag.startY;
        pdfEls.stage.scrollLeft = pdfPanDrag.scrollLeft - dx;
        pdfEls.stage.scrollTop = pdfPanDrag.scrollTop - dy;
      }

      function finishPdfPanDrag(event) {
        if (!pdfPanDrag || !pdfEls || !pdfEls.stage) {
          return;
        }
        try {
          pdfEls.stage.releasePointerCapture(pdfPanDrag.pointerId);
        } catch (error) {
        }
        pdfPanDrag = null;
        pdfEls.stage.classList.remove("is-panning");
      }

      const pdfWordKey = (value = "") => clean(value)
        .replace(/[\u2018\u2019`´]/g, "'")
        .toLowerCase()
        .replace(/\b([a-z]+)'s\b/g, "$1")
        .replace(/\s+/g, " ")
        .trim();

      const pdfStorePhoneticIpa = (keyValue = "", row = {}) => {
        const key = pdfWordKey(keyValue || (row && (row.key || row.text || row.word || "")));
        if (!key || !row || typeof row !== "object") {
          return null;
        }
        if (!pdfState.phoneticIpaByKey || typeof pdfState.phoneticIpaByKey !== "object") {
          pdfState.phoneticIpaByKey = {};
        }
        const normalized = {
          key,
          text: clean(row.text || row.word || keyValue || key),
          ipa: clean(row.ipa || row.pron || ""),
          ipa_us: clean(row.ipa_us || row.ipaUS || row.pron_us || row.pronUS || ""),
          ipa_uk: clean(row.ipa_uk || row.ipaUK || row.pron_uk || row.pronUK || ""),
          lemma: clean(row.lemma || ""),
          source: clean(row.source || ""),
        };
        pdfState.phoneticIpaByKey[key] = normalized;
        return normalized;
      };

      const pdfIpaRowForSurface = (surfaceText = "", details = []) => {
        const surfaceKey = pdfWordKey(surfaceText);
        if (surfaceKey && pdfState.phoneticIpaByKey && pdfState.phoneticIpaByKey[surfaceKey]) {
          return pdfState.phoneticIpaByKey[surfaceKey];
        }
        const list = Array.isArray(details) ? details : [details];
        for (const item of list) {
          if (!item || typeof item !== "object") {
            continue;
          }
          const surface = clean(item.surface || "");
          const word = clean(item.word || "");
          const row = {
            text: surface || word || surfaceText,
            ipa: clean(item.ipa || item.pron || ""),
            ipa_us: clean(item.ipa_us || item.pron_us || ""),
            ipa_uk: clean(item.ipa_uk || item.pron_uk || ""),
            lemma: word,
            source: clean(item.ipa || item.ipa_us || item.ipa_uk ? "server_cache" : "dictionary"),
          };
          if (row.ipa || row.ipa_us || row.ipa_uk) {
            return row;
          }
          const wordKey = pdfWordKey(word);
          if (wordKey && pdfState.phoneticIpaByKey && pdfState.phoneticIpaByKey[wordKey]) {
            return pdfState.phoneticIpaByKey[wordKey];
          }
        }
        return null;
      };

      const renderPdfSurfaceIpaNode = (node, row = null, loading = false) => {
        if (!node) {
          return;
        }
        node.textContent = "";
        const label = document.createElement("b");
        label.textContent = "IPA";
        node.appendChild(label);
        const safeRow = row && typeof row === "object" ? row : {};
        const uk = clean(safeRow.ipa_uk || "");
        const us = clean(safeRow.ipa_us || "");
        const ipa = clean(safeRow.ipa || "");
        const parts = [];
        if (uk) parts.push(`UK /${uk}/`);
        if (us && us !== uk) parts.push(`US /${us}/`);
        if (!parts.length && ipa) parts.push(`/${ipa}/`);
        const value = document.createElement("span");
        value.textContent = parts.length ? parts.join("  |  ") : (loading ? "loading..." : "not cached yet");
        node.appendChild(value);
      };

      const updatePdfSurfaceIpaNodes = (keyValue = "", row = null) => {
        const key = pdfWordKey(keyValue);
        if (!key) {
          return;
        }
        document.querySelectorAll(".ft-pdf-word-detail-surface-ipa[data-ipa-key]").forEach((node) => {
          if (pdfWordKey(node.getAttribute("data-ipa-key") || "") === key) {
            renderPdfSurfaceIpaNode(node, row || (pdfState.phoneticIpaByKey && pdfState.phoneticIpaByKey[key]));
          }
        });
      };

      const loadPdfSurfaceIpa = async (surfaceText = "", details = []) => {
        const text = clean(surfaceText);
        const key = pdfWordKey(text);
        if (!text || !key || (pdfState.phoneticIpaByKey && pdfState.phoneticIpaByKey[key]) || pdfPhoneticIpaPending.has(key)) {
          return;
        }
        const cachedRow = pdfIpaRowForSurface(text, details);
        if (cachedRow && (clean(cachedRow.ipa || "") || clean(cachedRow.ipa_us || "") || clean(cachedRow.ipa_uk || ""))) {
          const row = pdfStorePhoneticIpa(key, { ...cachedRow, text: clean(cachedRow.text || text) });
          if (row) {
            updatePdfSurfaceIpaNodes(key, row);
            const lemmaKey = pdfWordKey(row.lemma || "");
            if (lemmaKey) {
              pdfStorePhoneticIpa(lemmaKey, row);
              updatePdfSurfaceIpaNodes(lemmaKey, row);
            }
          }
          return;
        }
        pdfPhoneticIpaPending.add(key);
        try {
          const result = await fetchServerJson("/phonetic/ipa", {
            method: "POST",
            body: JSON.stringify({ term: text }),
            headers: { "Content-Type": "application/json" },
          });
          const payload = result && result.payload ? result.payload : {};
          const entry = payload.entry && typeof payload.entry === "object" ? payload.entry : null;
          const row = entry ? pdfStorePhoneticIpa(entry.key || key, entry) : null;
          if (row) {
            updatePdfSurfaceIpaNodes(key, row);
            const wordKey = pdfWordKey(row.lemma || "");
            if (wordKey) {
              updatePdfSurfaceIpaNodes(wordKey, row);
            }
          }
        } catch (error) {
          const fallback = pdfIpaRowForSurface(text, details);
          updatePdfSurfaceIpaNodes(key, fallback);
        } finally {
          pdfPhoneticIpaPending.delete(key);
        }
      };

      const buildPdfVocabDetailMap = (stats = {}) => {
        const source = stats && typeof stats === "object" ? stats : {};
        const latestAgent = source.word_agent_latest && typeof source.word_agent_latest === "object"
          ? source.word_agent_latest
          : {};
        Object.entries(latestAgent).forEach(([key, row]) => {
          const safeKey = pdfWordKey(key);
          if (safeKey && row && typeof row === "object") {
            if (!pdfState.wordAgentLatestByKey || typeof pdfState.wordAgentLatestByKey !== "object") {
              pdfState.wordAgentLatestByKey = {};
            }
            pdfState.wordAgentLatestByKey[safeKey] = row;
          }
        });
        const phoneticMap = source.phonetic_ipa && typeof source.phonetic_ipa === "object"
          ? source.phonetic_ipa
          : (source.phoneticIpa && typeof source.phoneticIpa === "object" ? source.phoneticIpa : {});
        Object.entries(phoneticMap).forEach(([key, row]) => {
          const safeKey = pdfWordKey(key);
          if (safeKey && row && typeof row === "object") {
            if (!pdfState.phoneticIpaByKey || typeof pdfState.phoneticIpaByKey !== "object") {
              pdfState.phoneticIpaByKey = {};
            }
            pdfState.phoneticIpaByKey[safeKey] = {
              key: safeKey,
              text: clean(row.text || row.word || key),
              ipa: clean(row.ipa || row.pron || ""),
              ipa_us: clean(row.ipa_us || row.ipaUS || row.pron_us || row.pronUS || ""),
              ipa_uk: clean(row.ipa_uk || row.ipaUK || row.pron_uk || row.pronUK || ""),
              lemma: clean(row.lemma || ""),
              source: clean(row.source || ""),
            };
          }
        });
        const cleanArray = (value) => {
          const list = Array.isArray(value) ? value : [];
          const seen = new Set();
          return list.map((item) => clean(item)).filter((item) => {
            const key = pdfWordKey(item);
            if (!key || seen.has(key)) {
              return false;
            }
            seen.add(key);
            return true;
          }).slice(0, 18);
        };
        const cleanExamples = (value, fallbackEn = "", fallbackVi = "") => {
          const list = Array.isArray(value) ? value : [];
          const out = [];
          list.forEach((item) => {
            if (!item) {
              return;
            }
            if (typeof item === "object") {
              const en = clean(item.en || item.english || item.example || "");
              const vi = clean(item.vi || item.vietnamese || item.translation || "");
              if (en || vi) {
                out.push({ en, vi });
              }
            } else {
              const en = clean(item);
              if (en) {
                out.push({ en, vi: "" });
              }
            }
          });
          if (!out.length && (clean(fallbackEn) || clean(fallbackVi))) {
            out.push({ en: clean(fallbackEn), vi: clean(fallbackVi) });
          }
          return out.slice(0, 8);
        };
        const rows = []
          .concat(Array.isArray(source.words) ? source.words : [])
          .concat(Array.isArray(source.unknown_words) ? source.unknown_words : [])
          .concat(Array.isArray(source.known_words) ? source.known_words : [])
          .concat(Array.isArray(source.phrases) ? source.phrases : [])
          .concat(Array.isArray(source.unknown_phrases) ? source.unknown_phrases : [])
          .concat(Array.isArray(source.known_phrases) ? source.known_phrases : [])
          .concat(Array.isArray(source.phrasal_verbs) ? source.phrasal_verbs : [])
          .concat(Array.isArray(source.unknown_phrasal_verbs) ? source.unknown_phrasal_verbs : []);
        const map = {};
        const mergeWordDetail = (base = {}, incoming = {}) => {
          const next = { ...(base && typeof base === "object" ? base : {}) };
          const source = incoming && typeof incoming === "object" ? incoming : {};
          [
            "word", "surface", "meaning", "pron", "type", "pron_us", "pron_uk",
            "ipa", "ipa_us", "ipa_uk", "usage", "context", "note", "match_mode", "kind",
          ].forEach((field) => {
            const current = clean(next[field] || "");
            const value = clean(source[field] || "");
            if (!current && value) {
              next[field] = value;
            }
          });
          ["collocations", "examples", "notes"].forEach((field) => {
            const current = Array.isArray(next[field]) ? next[field] : [];
            const value = Array.isArray(source[field]) ? source[field] : [];
            if (!current.length && value.length) {
              next[field] = value;
            }
          });
          return next;
        };
        const addDetail = (keyValue, item) => {
          const key = pdfWordKey(keyValue);
          if (!key || !item || typeof item !== "object") {
            return;
          }
          const detail = {
            word: clean(item.word || item.w || ""),
            surface: clean(item.surface || item.token || item.original || ""),
            meaning: clean(item.meaning || item.m || ""),
            pron: clean(item.pron || item.p || ""),
            type: clean(item.type || item.ty || item.pos || ""),
            pron_us: clean(item.pron_us || item.pronUS || ""),
            pron_uk: clean(item.pron_uk || item.pronUK || ""),
            ipa: clean(item.ipa || item.surface_ipa || item.surfaceIpa || ""),
            ipa_us: clean(item.ipa_us || item.ipaUS || item.surface_ipa_us || item.surfaceIpaUS || ""),
            ipa_uk: clean(item.ipa_uk || item.ipaUK || item.surface_ipa_uk || item.surfaceIpaUK || ""),
            usage: clean(item.usage || ""),
            context: clean(item.context || ""),
            note: clean(item.note || item.notes_text || ""),
            match_mode: clean(item.match_mode || item.matchMode || ""),
            kind: clean(item.kind || ""),
            collocations: cleanArray(item.collocations),
            examples: cleanExamples(item.examples, item.example || "", item.example_vi || item.exampleVi || ""),
            notes: cleanArray(item.notes),
          };
          const ipaRow = (pdfState.phoneticIpaByKey && (
            pdfState.phoneticIpaByKey[pdfWordKey(detail.surface)]
            || pdfState.phoneticIpaByKey[pdfWordKey(detail.word)]
            || pdfState.phoneticIpaByKey[key]
          )) || null;
          if (ipaRow && typeof ipaRow === "object") {
            detail.ipa = detail.ipa || clean(ipaRow.ipa || "");
            detail.ipa_us = detail.ipa_us || clean(ipaRow.ipa_us || "");
            detail.ipa_uk = detail.ipa_uk || clean(ipaRow.ipa_uk || "");
          }
          const detailKey = pdfWordKey(detail.word);
          if (!detail.word || !detailKey) {
            return;
          }
          if (!Array.isArray(map[key])) {
            map[key] = [];
          }
          const existingIndex = map[key].findIndex((existing) => pdfWordKey(existing.word) === detailKey);
          if (existingIndex >= 0) {
            map[key][existingIndex] = mergeWordDetail(map[key][existingIndex], detail);
          } else {
            map[key].push(detail);
          }
        };
        rows.forEach((item) => {
          if (!item || typeof item !== "object") {
            return;
          }
          const key = pdfWordKey(item.word || item.w || "");
          if (key) {
            addDetail(key, item);
          }
          const surfaceKey = pdfWordKey(item.surface || item.token || item.original || "");
          if (surfaceKey && surfaceKey !== key) {
            addDetail(surfaceKey, item);
          }
        });
        const tokenDetails = source.token_details && typeof source.token_details === "object"
          ? source.token_details
          : (source.tokenDetails && typeof source.tokenDetails === "object" ? source.tokenDetails : {});
        Object.entries(tokenDetails).forEach(([token, details]) => {
          const list = Array.isArray(details) ? details : [details];
          list.forEach((item) => {
            addDetail(token, item);
            addDetail(item && (item.word || item.w), item);
          });
        });
        return map;
      };

      const pdfPhraseRowsFromStats = (stats = {}) => {
        const source = stats && typeof stats === "object" ? stats : {};
        const rows = []
          .concat(Array.isArray(source.phrases) ? source.phrases : [])
          .concat(Array.isArray(source.unknown_phrases) ? source.unknown_phrases : [])
          .concat(Array.isArray(source.known_phrases) ? source.known_phrases : [])
          .concat(Array.isArray(source.phrasal_verbs) ? source.phrasal_verbs : [])
          .concat(Array.isArray(source.unknown_phrasal_verbs) ? source.unknown_phrasal_verbs : []);
        const seen = new Set();
        return rows
          .filter((item) => item && typeof item === "object")
          .map((item) => {
            const word = clean(item.word || item.w || "");
            const surface = clean(item.surface || item.token || item.original || word);
            const text = surface || word;
            const tokens = (text.match(/[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?/g) || []).map(pdfWordKey).filter(Boolean);
            const key = pdfWordKey(surface || word);
            if (!key || tokens.length < 2 || seen.has(key)) {
              return null;
            }
            seen.add(key);
            return {
              key,
              word,
              surface,
              tokens,
              kind: clean(item.kind || item.type || ""),
            };
          })
          .filter(Boolean)
          .sort((left, right) => right.tokens.length - left.tokens.length || left.key.localeCompare(right.key));
      };

      const pdfPhraseUnknownKeys = (stats = {}) => {
        const source = stats && typeof stats === "object" ? stats : {};
        const rows = []
          .concat(Array.isArray(source.unknown_phrases) ? source.unknown_phrases : [])
          .concat(Array.isArray(source.unknown_phrasal_verbs) ? source.unknown_phrasal_verbs : []);
        const keys = new Set();
        rows.forEach((item) => {
          const word = clean(item && (item.word || item.w || ""));
          const surface = clean(item && (item.surface || item.token || item.original || word));
          [word, surface].forEach((value) => {
            const key = pdfWordKey(value);
            if (key) {
              keys.add(key);
            }
          });
        });
        return keys;
      };

      const buildPdfPhraseRanges = (parts = [], phraseRows = [], phraseUnknownKeys = new Set()) => {
        const wordParts = [];
        parts.forEach((part, partIndex) => {
          if (part && part.isWord) {
            wordParts.push({ ...part, partIndex });
          }
        });
        if (!wordParts.length || !phraseRows.length) {
          return new Map();
        }
        const rangesByStart = new Map();
        const usedWordPositions = new Set();
        const separatorAllowsPhrase = (fromPartIndex, toPartIndex) => {
          for (let partIndex = fromPartIndex + 1; partIndex < toPartIndex; partIndex += 1) {
            const separator = parts[partIndex];
            if (separator && !separator.isWord && /[.!?;:\r\n]/.test(separator.text || "")) {
              return false;
            }
          }
          return true;
        };
        for (let wordIndex = 0; wordIndex < wordParts.length; wordIndex += 1) {
          if (usedWordPositions.has(wordIndex)) {
            continue;
          }
          for (const phrase of phraseRows) {
            const tokens = Array.isArray(phrase.tokens) ? phrase.tokens : [];
            if (tokens.length < 2 || wordIndex + tokens.length > wordParts.length) {
              continue;
            }
            let matched = true;
            for (let offset = 0; offset < tokens.length; offset += 1) {
              const current = wordParts[wordIndex + offset];
              if (!current || current.key !== tokens[offset]) {
                matched = false;
                break;
              }
              if (offset > 0) {
                const previous = wordParts[wordIndex + offset - 1];
                if (!separatorAllowsPhrase(previous.partIndex, current.partIndex)) {
                  matched = false;
                  break;
                }
              }
            }
            if (!matched) {
              continue;
            }
            const startPart = wordParts[wordIndex].partIndex;
            const endPart = wordParts[wordIndex + tokens.length - 1].partIndex;
            const detailKey = pdfWordKey(phrase.surface || phrase.word || phrase.key);
            rangesByStart.set(startPart, {
              startPart,
              endPart,
              detailKey,
              isUnknown: phraseUnknownKeys.has(detailKey) || phraseUnknownKeys.has(pdfWordKey(phrase.word)),
              isPhrasal: /phrasal|cụm\s+động\s+từ/i.test(`${phrase.kind} ${phrase.word}`),
            });
            for (let offset = 0; offset < tokens.length; offset += 1) {
              usedWordPositions.add(wordIndex + offset);
            }
            break;
          }
        }
        return rangesByStart;
      };

      const pdfWordDetailPageName = (page = "") => {
        const value = clean(page).toLowerCase();
        return ["basic", "usage", "agent"].includes(value) ? value : "basic";
      };

      const setPdfWordDetailPage = (page = "basic") => {
        const next = pdfWordDetailPageName(page);
        pdfState.wordDetailPage = next;
        if (!pdfEls || !pdfEls.wordDetail) {
          return;
        }
        pdfEls.wordDetail.querySelectorAll(".ft-pdf-word-page-tab").forEach((button) => {
          const active = clean(button.getAttribute("data-page")) === next;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-selected", active ? "true" : "false");
        });
        pdfEls.wordDetail.querySelectorAll(".ft-pdf-word-detail-page").forEach((panel) => {
          const active = clean(panel.getAttribute("data-page")) === next;
          panel.classList.toggle("is-active", active);
          panel.setAttribute("aria-hidden", active ? "false" : "true");
        });
      };

      const fillPdfWordAgentSharedPanel = (node, row = null, word = "") => {
        if (!node) {
          return;
        }
        node.innerHTML = "";
        const title = document.createElement("span");
        title.className = "ft-pdf-word-agent-shared-title";
        const body = document.createElement("div");
        body.className = "ft-pdf-word-agent-shared-body";
        if (row && !row.__empty) {
          title.textContent = `Latest Shared Agent | ${clean(row.username || "shared")} | ${clean(row.created_at || "")}`;
          body.textContent = preserveQuestionText(row.answer_vi || row.vietnamese || row.text || "No saved answer.");
        } else if (row && row.__empty) {
          title.textContent = "Latest Shared Agent";
          body.textContent = `No shared Agent explanation has been saved for ${word || "this word"} yet.`;
        } else {
          title.textContent = "Latest Shared Agent";
          body.textContent = "Loading shared Agent memory...";
        }
        node.append(title, body);
      };

      const updatePdfWordAgentSharedPanels = (wordKey = "") => {
        if (!pdfEls || !pdfEls.wordDetail) {
          return;
        }
        const key = pdfWordKey(wordKey);
        if (!key) {
          return;
        }
        const latest = pdfState.wordAgentLatestByKey && pdfState.wordAgentLatestByKey[key];
        const escapedKey = window.CSS && CSS.escape ? CSS.escape(key) : key.replace(/["\\]/g, "\\$&");
        pdfEls.wordDetail.querySelectorAll(`[data-word-agent-key="${escapedKey}"]`).forEach((node) => {
          fillPdfWordAgentSharedPanel(node, latest || null, node.getAttribute("data-word") || "");
        });
      };

      const loadPdfWordAgentLatestForDetail = async (entry = {}) => {
        const word = clean(entry.word || entry.surface || "");
        const key = pdfWordKey(word);
        if (!word || !key || !authToken) {
          return;
        }
        if (!pdfState.wordAgentLatestByKey || typeof pdfState.wordAgentLatestByKey !== "object") {
          pdfState.wordAgentLatestByKey = {};
        }
        if (Object.prototype.hasOwnProperty.call(pdfState.wordAgentLatestByKey || {}, key)) {
          updatePdfWordAgentSharedPanels(key);
          return;
        }
        try {
          const result = await fetchAuthJson(`/word-agent/history?word=${encodeURIComponent(word)}&limit=1`);
          const rows = Array.isArray(result.payload && result.payload.history) ? result.payload.history : [];
          pdfState.wordAgentLatestByKey[key] = rows[0] || { __empty: true, word };
          updatePdfWordAgentSharedPanels(key);
        } catch (error) {
          pdfState.wordAgentLatestByKey[key] = {
            __empty: true,
            word,
            error: clean(error && error.message ? error.message : "Could not load shared Agent memory."),
          };
          updatePdfWordAgentSharedPanels(key);
        }
      };

      const renderPdfFoundText = (text = "", stats = null) => {
        if (!pdfEls || !pdfEls.ocrText) {
          return;
        }
        const sourceText = preserveQuestionText(text || "");
        const sourceStats = stats && typeof stats === "object" ? stats : {};
        const detailMap = buildPdfVocabDetailMap(sourceStats);
        const unknownKeys = new Set((Array.isArray(sourceStats.unknown_words) ? sourceStats.unknown_words : [])
          .map((item) => pdfWordKey(item && (item.word || item.w || item)))
          .filter(Boolean));
        (Array.isArray(sourceStats.unknown_tokens) ? sourceStats.unknown_tokens : []).forEach((token) => {
          const key = pdfWordKey(token);
          if (key) {
            unknownKeys.add(key);
          }
        });
        pdfState.vocabDetailMap = detailMap;
        hidePdfWordDetail({ force: true });
        pdfEls.ocrText.textContent = "";
        if (!sourceText) {
          pdfEls.ocrText.textContent = "No text detected.";
          return;
        }
        const fragment = document.createDocumentFragment();
        const parts = sourceText.match(/[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?|[^A-Za-z0-9]+/g) || [sourceText];
        parts.forEach((part) => {
          if (/^[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?$/.test(part)) {
            const key = pdfWordKey(part);
            const span = document.createElement("span");
            span.className = "ft-pdf-word-token";
            span.textContent = part;
            if (Array.isArray(detailMap[key]) && detailMap[key].length) {
              span.dataset.wordKey = key;
            }
            if (unknownKeys.has(key)) {
              span.classList.add("is-new");
            }
            fragment.appendChild(span);
          } else {
            fragment.appendChild(document.createTextNode(part));
          }
        });
        pdfEls.ocrText.appendChild(fragment);
      };

      const renderPdfFoundTextWithPhrases = (text = "", stats = null) => {
        if (!pdfEls || !pdfEls.ocrText) {
          return;
        }
        const sourceText = preserveQuestionText(text || "");
        const sourceStats = stats && typeof stats === "object" ? stats : {};
        const detailMap = buildPdfVocabDetailMap(sourceStats);
        const phraseRows = pdfPhraseRowsFromStats(sourceStats);
        const phraseUnknownKeys = pdfPhraseUnknownKeys(sourceStats);
        const unknownKeys = new Set((Array.isArray(sourceStats.unknown_words) ? sourceStats.unknown_words : [])
          .map((item) => pdfWordKey(item && (item.word || item.w || item)))
          .filter(Boolean));
        (Array.isArray(sourceStats.unknown_tokens) ? sourceStats.unknown_tokens : []).forEach((token) => {
          const key = pdfWordKey(token);
          if (key) {
            unknownKeys.add(key);
          }
        });
        pdfState.vocabDetailMap = detailMap;
        hidePdfWordDetail({ force: true });
        pdfEls.ocrText.textContent = "";
        if (!sourceText) {
          pdfEls.ocrText.textContent = "No text detected.";
          return;
        }
        const rawParts = sourceText.match(/[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?|[^A-Za-z0-9]+/g) || [sourceText];
        const wordPattern = /^[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?$/;
        const parts = rawParts.map((part) => ({
          text: part,
          isWord: wordPattern.test(part),
          key: wordPattern.test(part) ? pdfWordKey(part) : "",
        }));
        const phraseRanges = buildPdfPhraseRanges(parts, phraseRows, phraseUnknownKeys);
        const fragment = document.createDocumentFragment();
        for (let partIndex = 0; partIndex < parts.length; partIndex += 1) {
          const phraseRange = phraseRanges.get(partIndex);
          if (phraseRange) {
            const phraseSpan = document.createElement("span");
            phraseSpan.className = "ft-pdf-word-token ft-pdf-phrase-token";
            phraseSpan.dataset.wordKey = phraseRange.detailKey;
            if (phraseRange.isUnknown) {
              phraseSpan.classList.add("is-new");
            }
            if (phraseRange.isPhrasal) {
              phraseSpan.classList.add("is-phrasal-verb");
            }
            phraseSpan.textContent = parts.slice(partIndex, phraseRange.endPart + 1).map((item) => item.text).join("");
            fragment.appendChild(phraseSpan);
            partIndex = phraseRange.endPart;
            continue;
          }
          const part = parts[partIndex];
          if (part.isWord) {
            const key = part.key;
            const span = document.createElement("span");
            span.className = "ft-pdf-word-token";
            span.textContent = part.text;
            if (Array.isArray(detailMap[key]) && detailMap[key].length) {
              span.dataset.wordKey = key;
            }
            if (unknownKeys.has(key)) {
              span.classList.add("is-new");
            }
            fragment.appendChild(span);
          } else {
            fragment.appendChild(document.createTextNode(part.text));
          }
        }
        pdfEls.ocrText.appendChild(fragment);
      };

      const hidePdfWordDetail = (options = {}) => {
        if (!pdfEls || !pdfEls.wordDetail) {
          return;
        }
        if (pdfState.wordDetailPinned && !(options && options.force)) {
          return;
        }
        pdfState.wordDetailPinned = false;
        pdfState.pinnedWordKey = "";
        pdfState.wordDetailEntries = [];
        pdfState.wordDetailSurface = "";
        pdfEls.wordDetail.classList.add("is-hidden");
        pdfEls.wordDetail.classList.remove("is-pinned");
        pdfEls.wordDetail.setAttribute("aria-hidden", "true");
      };

      const closePinnedPdfWordDetail = () => {
        hidePdfWordDetail({ force: true });
      };

      // Added 2026-07-14: lets PDF/Picture word detail play warmed QMLearn US/UK audio without a TTS request.
      const pdfWordDetailAudioUrl = (entry = {}, voice = "") => {
        const audio = entry && typeof entry.audio === "object" ? entry.audio : {};
        const voiceKey = clean(voice);
        const shortKey = voiceKey.toLowerCase().endsWith("en-us") ? "us" : (voiceKey.toLowerCase().endsWith("en-gb") ? "uk" : "");
        const clip = audio[voiceKey] || audio[voiceKey.replace(/^sot:/i, "")] || audio[shortKey] || {};
        if (!clip || typeof clip !== "object") {
          return "";
        }
        return clean(clip.u || clip.url || clip.path || clip.audio_path || clip.audioPath || "");
      };

      const prefetchPdfWordDetailAudio = (entry = {}, voice = "") => {
        const url = pdfWordDetailAudioUrl(entry, voice);
        if (!url) {
          return;
        }
        try {
          if (typeof getOrCreateSpaceWUrlAudio === "function") {
            void getOrCreateSpaceWUrlAudio(url, [], {
              voice,
              nodeIndex: pdfState.currentPage || 0,
              timeoutMs: 9000,
            }).catch(() => {});
            return;
          }
          const audio = new Audio(serverAssetUrl(url));
          audio.preload = "metadata";
          audio.load();
        } catch (error) {
        }
      };

      // Added 2026-07-14: plays PDF/Picture word-detail audio from IndexedDB first, then caches the server URL blob.
      const playPdfIndexedAudioUrl = async (url = "", voice = "") => {
        const source = clean(url);
        if (!source || typeof getOrCreateSpaceWUrlAudio !== "function") {
          return false;
        }
        let objectUrl = "";
        try {
          const cached = await getOrCreateSpaceWUrlAudio(source, [], {
            voice,
            nodeIndex: pdfState.currentPage || 0,
            timeoutMs: 9000,
          });
          if (!cached || !(cached.blob instanceof Blob)) {
            return false;
          }
          if (pdfAudioPlayer) {
            try {
              pdfAudioPlayer.pause();
            } catch (error) {
            }
          }
          objectUrl = URL.createObjectURL(cached.blob);
          pdfAudioPlayer = new Audio(objectUrl);
          await pdfAudioPlayer.play();
          window.setTimeout(() => {
            try {
              URL.revokeObjectURL(objectUrl);
            } catch (error) {
            }
          }, 1000);
          return true;
        } catch (error) {
          if (objectUrl) {
            try {
              URL.revokeObjectURL(objectUrl);
            } catch (cleanupError) {
            }
          }
          return false;
        }
      };

      const editPdfQmDictField = async (detailIndex = 0, field = "", button = null) => {
        if (!currentAuthIsAdmin) {
          setPdfStatus("Only admins can edit QmDict.", true);
          return;
        }
        const index = Math.max(0, Math.floor(Number(detailIndex) || 0));
        const targetField = field === "type" ? "type" : (field === "meaning" ? "meaning" : "");
        if (!targetField) {
          return;
        }
        const entries = Array.isArray(pdfState.wordDetailEntries) ? pdfState.wordDetailEntries : [];
        const entry = entries[index];
        const word = clean(entry && entry.word);
        if (!entry || !word) {
          setPdfStatus("No QmDict entry is selected.", true);
          return;
        }
        const label = targetField === "meaning" ? "meaning" : "type";
        const entryKind = clean(entry.kind || "");
        const isPhraseEntry = Boolean(
          clean(entry.word || "").includes(" ") ||
          /phrase|phrasal|cụm/i.test(`${entryKind} ${entry.type || ""}`)
        );
        const dictionaryLabel = isPhraseEntry ? "phrase" : "QmDict";
        const currentValue = clean(entry[targetField] || "");
        const nextValue = window.prompt(`Edit ${dictionaryLabel} ${label} for "${word}"`, currentValue);
        if (nextValue === null) {
          return;
        }
        const cleanedValue = clean(nextValue);
        if (!cleanedValue || cleanedValue === currentValue) {
          return;
        }
        if (button) {
          button.classList.add("is-busy");
          button.disabled = true;
        }
        try {
          setPdfStatus(`Updating ${dictionaryLabel} ${label}...`);
          const body = {
            word,
            meaning: targetField === "meaning" ? cleanedValue : clean(entry.meaning || ""),
            type: targetField === "type" ? cleanedValue : clean(entry.type || ""),
            source: isPhraseEntry ? "phrase" : "qmdict",
          };
          const { payload } = await fetchAuthJson("/qmdict/update", {
            method: "POST",
            body: JSON.stringify(body),
          });
          const updated = payload && payload.entry && typeof payload.entry === "object" ? payload.entry : {};
          const nextEntry = {
            ...entry,
            ...updated,
            word: clean(updated.word || entry.word || word),
            meaning: clean(updated.meaning || body.meaning),
            type: clean(updated.type || body.type),
          };
          pdfState.wordDetailEntries = entries.map((item, itemIndex) => (itemIndex === index ? nextEntry : item));
          const updateKey = pdfWordKey(nextEntry.word || word);
          const surfaceKey = pdfWordKey(entry.surface || pdfState.wordDetailSurface || word);
          [updateKey, surfaceKey].filter(Boolean).forEach((key) => {
            const rows = Array.isArray(pdfState.vocabDetailMap && pdfState.vocabDetailMap[key]) ? pdfState.vocabDetailMap[key] : [];
            if (!rows.length) {
              return;
            }
            pdfState.vocabDetailMap[key] = rows.map((row) => (
              pdfWordKey(row && row.word) === updateKey
                ? { ...row, meaning: nextEntry.meaning, type: nextEntry.type }
                : row
            ));
          });
          showPdfWordDetail(pdfState.wordDetailEntries, null, {
            pinned: pdfState.wordDetailPinned,
            wordKey: pdfState.pinnedWordKey,
            surface: pdfState.wordDetailSurface,
          });
          setPdfStatus("QmDict updated. Space_V files will sync when opened.");
        } catch (error) {
          setPdfStatus(error && error.message ? error.message : "Could not update QmDict.", true);
        } finally {
          if (button) {
            button.classList.remove("is-busy");
            button.disabled = false;
          }
        }
      };

      const showPdfWordDetail = (detail = {}, event = null, options = {}) => {
        const details = (Array.isArray(detail) ? detail : [detail])
          .filter((item) => item && typeof item === "object" && clean(item.word || ""));
        if (!pdfEls || !pdfEls.wordDetail || !details.length) {
          hidePdfWordDetail();
          return;
        }
        const pinned = Boolean(options && options.pinned);
        const node = pdfEls.wordDetail;
        node.innerHTML = "";
        pdfState.wordDetailPinned = pinned;
        pdfState.pinnedWordKey = clean(options && options.wordKey);
        pdfState.wordDetailEntries = details.map((item) => ({ ...item }));
        node.classList.toggle("is-pinned", pinned);
        if (pinned) {
          const close = document.createElement("button");
          close.className = "ft-pdf-word-detail-close";
          close.type = "button";
          close.textContent = "x";
          close.setAttribute("aria-label", "Close word detail");
          close.setAttribute("data-pdf-action", "closeWordDetail");
          node.appendChild(close);
        }
        const topGroup = document.createElement("div");
        topGroup.className = "ft-pdf-word-detail-top";
        const title = document.createElement("p");
        title.className = "ft-pdf-word-detail-title";
        title.textContent = details.length > 1 ? `Word Detail | ${details.length} results` : "Word Detail";
        topGroup.appendChild(title);
        const surfaceText = clean(options && options.surface) || clean(details[0] && details[0].surface);
        pdfState.wordDetailSurface = surfaceText;
        const makePageTabs = () => {
          const tabs = document.createElement("div");
          tabs.className = "ft-pdf-word-page-tabs";
          [
            ["basic", "Info"],
            ["usage", "Usage"],
            ["agent", "Shared Agent"],
          ].forEach(([page, label]) => {
            const button = document.createElement("button");
            button.className = "ft-pdf-word-page-tab";
            button.type = "button";
            button.textContent = label;
            button.setAttribute("data-pdf-action", "wordDetailPage");
            button.setAttribute("data-page", page);
            tabs.appendChild(button);
          });
          return tabs;
        };
        const surface = document.createElement("div");
        surface.className = "ft-pdf-word-detail-surface";
        if (surfaceText) {
          const surfaceMain = document.createElement("div");
          surfaceMain.className = "ft-pdf-word-detail-surface-main";
          const surfaceLabel = document.createElement("span");
          surfaceLabel.textContent = "Original token";
          const surfaceValue = document.createElement("strong");
          surfaceValue.textContent = surfaceText;
          surfaceMain.append(surfaceLabel, surfaceValue);
          const ipaLine = document.createElement("div");
          ipaLine.className = "ft-pdf-word-detail-surface-ipa";
          ipaLine.setAttribute("data-ipa-key", pdfWordKey(surfaceText));
          const ipaRow = pdfIpaRowForSurface(surfaceText, details);
          renderPdfSurfaceIpaNode(ipaLine, ipaRow, !ipaRow);
          surfaceMain.appendChild(ipaLine);
          surface.append(surfaceMain, makePageTabs());
        } else {
          const surfaceMain = document.createElement("div");
          surfaceMain.className = "ft-pdf-word-detail-surface-main";
          const surfaceLabel = document.createElement("span");
          surfaceLabel.textContent = "Word detail pages";
          const surfaceValue = document.createElement("strong");
          surfaceValue.textContent = clean(details[0] && details[0].word) || "Selected entry";
          surfaceMain.append(surfaceLabel, surfaceValue);
          surface.append(surfaceMain, makePageTabs());
        }
        topGroup.appendChild(surface);
        node.appendChild(topGroup);
        const resultsWrap = document.createElement("div");
        resultsWrap.className = `ft-pdf-word-detail-results${details.length > 1 ? " is-multiple" : ""}`;
        details.forEach((entry, index) => {
          const section = document.createElement("section");
          section.className = "ft-pdf-word-detail-entry";
          const basicPage = document.createElement("div");
          basicPage.className = "ft-pdf-word-detail-page";
          basicPage.setAttribute("data-page", "basic");
          const headRow = document.createElement("div");
          headRow.className = "ft-pdf-word-head-row";
          const main = document.createElement("div");
          main.className = "ft-pdf-word-main";
          const word = document.createElement("span");
          word.className = "ft-pdf-word-lemma";
          word.textContent = clean(entry.word || "");
          main.appendChild(word);
          const pronText = clean(entry.pron || "");
          if (pronText) {
            const pron = document.createElement("span");
            pron.className = "ft-pdf-word-pron-inline";
            pron.textContent = `/${pronText}/`;
            main.appendChild(pron);
          }
          const audioRow = document.createElement("div");
          audioRow.className = "ft-pdf-word-audio-row";
          [
            ["US", "sot:en-US"],
            ["UK", "sot:en-GB"],
          ].forEach(([label, voice]) => {
            const audioUrl = pdfWordDetailAudioUrl(entry, voice);
            const audioButton = document.createElement("button");
            audioButton.className = `ft-pdf-word-audio-button${audioUrl ? " is-cached" : ""}`;
            audioButton.type = "button";
            audioButton.textContent = label;
            audioButton.setAttribute("data-pdf-action", "wordAudio");
            audioButton.setAttribute("data-word", clean(entry.word || ""));
            audioButton.setAttribute("data-voice", voice);
            if (audioUrl) {
              audioButton.setAttribute("data-audio-url", audioUrl);
              audioButton.title = `${label} audio is ready`;
            }
            audioRow.appendChild(audioButton);
          });
          const addKey = pdfWordKey(entry.word || "");
          const alreadyAdded = Boolean(addKey && pdfState.unlearnedWords && pdfState.unlearnedWords[addKey]);
          const addButton = document.createElement("button");
          addButton.className = `ft-pdf-word-audio-button ft-pdf-word-add-button${alreadyAdded ? " is-added" : ""}`;
          addButton.type = "button";
          addButton.textContent = alreadyAdded ? "Added" : "Add";
          addButton.title = alreadyAdded ? "Already in Unlearned Words" : "Add this word to Unlearned Words";
          addButton.disabled = alreadyAdded;
          addButton.setAttribute("data-pdf-action", "addWordDetailUnlearned");
          addButton.setAttribute("data-detail-index", String(index));
          addButton.setAttribute("data-word-key", addKey);
          audioRow.appendChild(addButton);
          headRow.append(main, audioRow);
          basicPage.appendChild(headRow);
          const surface = clean(entry.surface || "");
          if (surface && pdfWordKey(surface) !== pdfWordKey(entry.word || "")) {
            const source = document.createElement("p");
            source.className = "ft-pdf-word-detail-source";
            source.textContent = `Matched from "${surface}"`;
            basicPage.appendChild(source);
          }
          const grid = document.createElement("div");
          grid.className = "ft-pdf-word-detail-grid";
          [
            ["Meaning", clean(entry.meaning || "No meaning data")],
            ["Type", clean(entry.type || "Not available")],
            ["Kind", clean(entry.kind || (clean(entry.word || "").includes(" ") ? "phrase" : "word"))],
          ].forEach(([label, value]) => {
            const row = document.createElement("div");
            row.className = "ft-pdf-word-detail-grid-row";
            const labelNode = document.createElement("span");
            labelNode.textContent = `${label}: `;
            const valueNode = document.createElement("div");
            valueNode.className = "ft-pdf-word-detail-value";
            valueNode.textContent = value;
            row.appendChild(labelNode);
            row.appendChild(valueNode);
            if (currentAuthIsAdmin && (label === "Meaning" || label === "Type")) {
              const editButton = document.createElement("button");
              editButton.className = "ft-pdf-word-qmdict-edit";
              editButton.type = "button";
              editButton.textContent = "Edit";
              editButton.title = `Edit ${clean(entry.kind || "").includes("phrase") || clean(entry.word || "").includes(" ") ? "phrase" : "QmDict"} ${label.toLowerCase()}`;
              editButton.setAttribute("data-pdf-action", "editQmDictField");
              editButton.setAttribute("data-detail-index", String(index));
              editButton.setAttribute("data-field", label === "Meaning" ? "meaning" : "type");
              row.appendChild(editButton);
            }
            grid.appendChild(row);
          });
          basicPage.appendChild(grid);
          const usagePreviewText = preserveQuestionText(entry.usage || "");
          const previewExamples = Array.isArray(entry.examples) ? entry.examples : [];
          if (usagePreviewText || previewExamples.length) {
            const preview = document.createElement("div");
            preview.className = "ft-pdf-word-detail-rich ft-pdf-word-detail-basic-preview";
            if (usagePreviewText) {
              const usageRow = document.createElement("div");
              usageRow.className = "ft-pdf-word-detail-rich-row";
              const usageLabel = document.createElement("b");
              usageLabel.textContent = "Usage";
              const usageValue = document.createElement("span");
              usageValue.textContent = usagePreviewText;
              usageRow.append(usageLabel, usageValue);
              preview.appendChild(usageRow);
            }
            if (previewExamples.length) {
              const example = previewExamples[0] || {};
              const en = clean(example.en || example.english || example.example || "");
              const vi = clean(example.vi || example.vietnamese || example.translation || "");
              if (en || vi) {
                const exampleRow = document.createElement("div");
                exampleRow.className = "ft-pdf-word-detail-rich-row";
                const exampleLabel = document.createElement("b");
                exampleLabel.textContent = "Example";
                const line = document.createElement("span");
                line.className = "ft-pdf-word-example-row";
                if (en) {
                  const enNode = document.createElement("strong");
                  enNode.textContent = en;
                  line.appendChild(enNode);
                }
                if (vi) {
                  const viNode = document.createElement("small");
                  viNode.textContent = `Meaning: ${vi}`;
                  line.appendChild(viNode);
                }
                exampleRow.append(exampleLabel, line);
                preview.appendChild(exampleRow);
              }
            }
            basicPage.appendChild(preview);
          }
          section.appendChild(basicPage);
          const usagePage = document.createElement("div");
          usagePage.className = "ft-pdf-word-detail-page";
          usagePage.setAttribute("data-page", "usage");
          const rich = document.createElement("div");
          rich.className = "ft-pdf-word-detail-rich";
          const appendRichRow = (label, value) => {
            const text = preserveQuestionText(value || "");
            if (!text) {
              return;
            }
            const row = document.createElement("div");
            row.className = "ft-pdf-word-detail-rich-row";
            const labelNode = document.createElement("b");
            labelNode.textContent = label;
            const valueNode = document.createElement("span");
            valueNode.textContent = text;
            row.append(labelNode, valueNode);
            rich.appendChild(row);
          };
          appendRichRow("Usage", entry.usage);
          appendRichRow("Context", entry.context);
          appendRichRow("Note", entry.note);
          if (clean(entry.match_mode || "")) {
            appendRichRow("Match", entry.match_mode);
          }
          const collocations = Array.isArray(entry.collocations) ? entry.collocations.map(clean).filter(Boolean) : [];
          if (collocations.length) {
            const row = document.createElement("div");
            row.className = "ft-pdf-word-detail-rich-row";
            const labelNode = document.createElement("b");
            labelNode.textContent = "Collocations";
            const chips = document.createElement("div");
            chips.className = "ft-pdf-word-detail-chip-row";
            collocations.slice(0, 16).forEach((value) => {
              const chip = document.createElement("span");
              chip.className = "ft-pdf-word-detail-chip";
              chip.textContent = value;
              chips.appendChild(chip);
            });
            row.append(labelNode, chips);
            rich.appendChild(row);
          }
          const examples = Array.isArray(entry.examples) ? entry.examples : [];
          if (examples.length) {
            const row = document.createElement("div");
            row.className = "ft-pdf-word-detail-rich-row";
            const labelNode = document.createElement("b");
            labelNode.textContent = "Examples";
            row.appendChild(labelNode);
            examples.slice(0, 5).forEach((example) => {
              const line = document.createElement("span");
              line.className = "ft-pdf-word-example-row";
              const en = clean(example && (example.en || example.english || example.example || ""));
              const vi = clean(example && (example.vi || example.vietnamese || example.translation || ""));
              if (en) {
                const enNode = document.createElement("strong");
                enNode.textContent = en;
                line.appendChild(enNode);
              }
              if (vi) {
                const viNode = document.createElement("small");
                viNode.textContent = `Meaning: ${vi}`;
                line.appendChild(viNode);
              }
              if (line.childNodes.length) {
                row.appendChild(line);
              }
            });
            rich.appendChild(row);
          }
          const notes = Array.isArray(entry.notes) ? entry.notes.map(clean).filter(Boolean) : [];
          if (notes.length) {
            appendRichRow("Extra Notes", notes.slice(0, 8).join("; "));
          }
          if (rich.childNodes.length) {
            usagePage.appendChild(rich);
          } else {
            const empty = document.createElement("div");
            empty.className = "ft-pdf-word-detail-rich-row";
            empty.textContent = "No usage/context data has been added for this entry yet.";
            usagePage.appendChild(empty);
          }
          section.appendChild(usagePage);
          const agentPage = document.createElement("div");
          agentPage.className = "ft-pdf-word-detail-page";
          agentPage.setAttribute("data-page", "agent");
          const agentShared = document.createElement("div");
          const wordKey = pdfWordKey(entry.word || entry.surface || "");
          agentShared.className = "ft-pdf-word-agent-shared";
          agentShared.setAttribute("data-word-agent-key", wordKey);
          agentShared.setAttribute("data-word", clean(entry.word || ""));
          fillPdfWordAgentSharedPanel(agentShared, pdfState.wordAgentLatestByKey && pdfState.wordAgentLatestByKey[wordKey], clean(entry.word || ""));
          agentPage.appendChild(agentShared);
          section.appendChild(agentPage);
          resultsWrap.appendChild(section);
        });
        node.appendChild(resultsWrap);
        if (pinned) {
          const footer = document.createElement("div");
          footer.className = "ft-pdf-word-detail-footer";
          const note = document.createElement("span");
          note.className = "ft-pdf-word-detail-footer-note";
          note.textContent = "Agent actions stay visible";
          const actions = document.createElement("div");
          actions.className = "ft-pdf-word-detail-actions";
          const ask = document.createElement("button");
          ask.className = "ft-pdf-word-agent-button";
          ask.type = "button";
          ask.textContent = "Ask Agent For This Word";
          ask.setAttribute("data-pdf-action", "askWordAgent");
          ask.setAttribute("data-detail-index", "0");
          const history = document.createElement("button");
          history.className = "ft-pdf-word-agent-button";
          history.type = "button";
          history.textContent = "History About";
          history.setAttribute("data-pdf-action", "wordAgentHistory");
          history.setAttribute("data-detail-index", "0");
          actions.append(ask, history);
          footer.append(note, actions);
          node.appendChild(footer);
        }
        node.classList.remove("is-hidden");
        node.setAttribute("aria-hidden", "false");
        setPdfWordDetailPage("basic");
        if (surfaceText) {
          void loadPdfSurfaceIpa(surfaceText, details);
        }
        if (pinned) {
          details.slice(0, 4).forEach((entry) => {
            prefetchPdfWordDetailAudio(entry, "sot:en-US");
            prefetchPdfWordDetailAudio(entry, "sot:en-GB");
            void loadPdfWordAgentLatestForDetail(entry);
          });
        }
        const wordRect = node.getBoundingClientRect();
        const width = Math.min(window.innerWidth - 28, Math.max(320, wordRect.width || Math.round(window.innerWidth * 0.5)));
        const height = Math.max(160, wordRect.height || node.offsetHeight || 160);
        const consoleRect = pdfEls.root ? pdfEls.root.querySelector(".ft-pdf-ocr-card").getBoundingClientRect() : null;
        let left = consoleRect ? consoleRect.left - width - 18 : ((event && event.clientX) ? event.clientX + 18 : 18);
        if (left < 12) {
          left = Math.min(window.innerWidth - width - 12, ((event && event.clientX) ? event.clientX + 18 : 18));
        }
        const rawTop = event && event.clientY ? event.clientY - 30 : window.innerHeight * 0.24;
        const top = Math.max(12, Math.min(window.innerHeight - height - 12, rawTop));
        node.style.left = `${Math.max(12, left)}px`;
        node.style.top = `${top}px`;
      };

      function handlePdfFoundWordMove(event) {
        if (pdfState.wordDetailPinned) {
          return;
        }
        const target = event.target && event.target.closest ? event.target.closest(".ft-pdf-word-token[data-word-key]") : null;
        if (!target || !pdfEls || !pdfEls.ocrText || !pdfEls.ocrText.contains(target)) {
          hidePdfWordDetail();
          return;
        }
        const detail = pdfState.vocabDetailMap && pdfState.vocabDetailMap[target.dataset.wordKey];
        showPdfWordDetail(detail, event, {
          surface: target.textContent || "",
          wordKey: target.dataset.wordKey || "",
        });
      }

      function handlePdfFoundWordClick(event) {
        const target = event.target && event.target.closest ? event.target.closest(".ft-pdf-word-token[data-word-key]") : null;
        if (!target || !pdfEls || !pdfEls.ocrText || !pdfEls.ocrText.contains(target)) {
          return;
        }
        event.preventDefault();
        const detail = pdfState.vocabDetailMap && pdfState.vocabDetailMap[target.dataset.wordKey];
        showPdfWordDetail(detail, event, {
          pinned: true,
          surface: target.textContent || "",
          wordKey: target.dataset.wordKey || "",
        });
      }

      async function commitPdfExploreTextEdits() {
        if (!pdfModeActive || !pdfEls || !pdfEls.exploreInput) {
          return;
        }
        const editedText = normalizePdfGhostEyeTextCase(pdfEls.exploreInput.value || "").trim();
        const requestSerial = ++pdfExploreAnalyzeSerial;
        closePdfTranslationPopup();
        if (pdfEls.translation) {
          pdfEls.translation.textContent = "Vietnamese translation will appear here.";
        }
        pdfState.translation = "";
        pdfState.vocabMission = null;
        hidePdfWordDetail({ force: true });
        if (!editedText) {
          pdfState.ocrText = "";
          pdfState.ocrRawText = "";
          pdfState.ocrFilteredText = "";
          pdfState.ocrViewMode = "raw";
          renderPdfFoundTextWithPhrases("", {});
          updatePdfVocabStats(null);
          updatePdfVocabularyMissionButtons();
          setPdfOcrTab("found");
          schedulePdfProgressSave(180);
          setPdfStatus("Text Found cleared. Edit Text To Explore and press Enter to sync.");
          return;
        }
        setPdfGhostEyeTextState(editedText, { resetView: true });
        if (pdfEls.ocrText) {
          pdfEls.ocrText.textContent = "Ghost Eye is analyzing edited text...";
        }
        setPdfStatus("Ghost Eye is analyzing edited text...");
        try {
          const { payload } = await fetchAuthJson("/pdf/analyze-text?client_source=pdf_explore_input_analyze", {
            method: "POST",
            body: JSON.stringify({
              path: pdfState.path || "",
              page: pdfState.page || 1,
              text: editedText,
            }),
          });
          if (requestSerial !== pdfExploreAnalyzeSerial) {
            return;
          }
          const nextText = normalizePdfGhostEyeTextCase(payload.text || editedText);
          const vocab = payload && payload.vocabulary && typeof payload.vocabulary === "object" ? payload.vocabulary : {};
          setPdfGhostEyeTextState(nextText, { resetView: true });
          if (pdfEls.exploreInput && pdfEls.exploreInput.value !== nextText) {
            pdfEls.exploreInput.value = nextText;
          }
          renderPdfGhostEyeTextByMode(vocab);
          updatePdfVocabStats(vocab);
          updatePdfVocabularyMissionButtons();
          setPdfOcrTab("found");
          schedulePdfProgressSave(180);
          const unknown = Math.max(0, Number(vocab.unknown || 0) || 0);
          const total = Math.max(0, Number(vocab.total || 0) || 0);
          setPdfStatus(`Text To Explore synced. Unknown vocabulary: ${unknown}/${total}.`);
        } catch (error) {
          if (requestSerial !== pdfExploreAnalyzeSerial) {
            return;
          }
          setPdfGhostEyeTextState(editedText, { resetView: true });
          renderPdfGhostEyeTextByMode({});
          updatePdfVocabStats(null);
          updatePdfVocabularyMissionButtons();
          setPdfOcrTab("found");
          schedulePdfProgressSave(180);
          setPdfStatus(error && error.message ? error.message : "Could not analyze edited text.", true);
        }
      }

      const joinPdfGhostText = (...parts) => parts
        .map((part) => normalizePdfGhostEyeTextCase(part || ""))
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

      const loadPdfBrowserOcrEngine = () => {
        if (window.Tesseract && typeof window.Tesseract.recognize === "function") {
          return Promise.resolve(window.Tesseract);
        }
        if (pdfBrowserOcrScriptPromise) {
          return pdfBrowserOcrScriptPromise;
        }
        pdfBrowserOcrScriptPromise = new Promise((resolve, reject) => {
          const existing = document.querySelector(`script[src="${PDF_BROWSER_OCR_SCRIPT_URL}"]`);
          if (existing) {
            existing.addEventListener("load", () => {
              if (window.Tesseract && typeof window.Tesseract.recognize === "function") resolve(window.Tesseract);
              else reject(new Error("Browser OCR library loaded without Tesseract."));
            }, { once: true });
            existing.addEventListener("error", () => reject(new Error("Could not load Browser OCR library.")), { once: true });
            return;
          }
          const script = document.createElement("script");
          script.src = PDF_BROWSER_OCR_SCRIPT_URL;
          script.async = true;
          script.onload = () => {
            if (window.Tesseract && typeof window.Tesseract.recognize === "function") resolve(window.Tesseract);
            else reject(new Error("Browser OCR library loaded without Tesseract."));
          };
          script.onerror = () => reject(new Error("Could not load Browser OCR library."));
          document.head.appendChild(script);
        });
        return pdfBrowserOcrScriptPromise;
      };

      const capturePdfSelectionCanvasForBrowserOcr = (selection = null) => {
        const rect = normalizePdfSelectionState(selection || (pdfState && pdfState.selection));
        if (!rect || !pdfEls || !pdfEls.image || !pdfEls.image.naturalWidth || !pdfEls.image.naturalHeight) {
          return null;
        }
        const image = pdfEls.image;
        const sourceX = Math.max(0, Math.round(rect.x * image.naturalWidth));
        const sourceY = Math.max(0, Math.round(rect.y * image.naturalHeight));
        const sourceW = Math.max(1, Math.min(image.naturalWidth - sourceX, Math.round(rect.w * image.naturalWidth)));
        const sourceH = Math.max(1, Math.min(image.naturalHeight - sourceY, Math.round(rect.h * image.naturalHeight)));
        const scale = 1;
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(sourceW * scale));
        canvas.height = Math.max(1, Math.round(sourceH * scale));
        const context = canvas.getContext("2d", { willReadFrequently: true });
        if (!context) {
          return null;
        }
        context.imageSmoothingEnabled = true;
        context.imageSmoothingQuality = "high";
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, sourceX, sourceY, sourceW, sourceH, 0, 0, canvas.width, canvas.height);
        if (pdfEls.drawCanvas && pdfEls.drawCanvas.width && pdfEls.drawCanvas.height) {
          try {
            syncPdfPenCanvasSize();
            const drawSourceX = Math.max(0, Math.round(rect.x * pdfEls.drawCanvas.width));
            const drawSourceY = Math.max(0, Math.round(rect.y * pdfEls.drawCanvas.height));
            const drawSourceW = Math.max(1, Math.min(pdfEls.drawCanvas.width - drawSourceX, Math.round(rect.w * pdfEls.drawCanvas.width)));
            const drawSourceH = Math.max(1, Math.min(pdfEls.drawCanvas.height - drawSourceY, Math.round(rect.h * pdfEls.drawCanvas.height)));
            context.drawImage(
              pdfEls.drawCanvas,
              drawSourceX,
              drawSourceY,
              drawSourceW,
              drawSourceH,
              0,
              0,
              canvas.width,
              canvas.height
            );
          } catch (error) {
          }
        }
        return canvas;
      };

      const optimizePdfBrowserOcrCanvas = (canvas = null) => {
        if (!canvas || !canvas.width || !canvas.height) {
          return canvas;
        }
        const context = canvas.getContext("2d", { willReadFrequently: true });
        if (!context) {
          return canvas;
        }
        try {
          const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
          const data = imageData.data;
          for (let index = 0; index < data.length; index += 4) {
            const alpha = data[index + 3];
            if (alpha < 18) {
              data[index] = 255;
              data[index + 1] = 255;
              data[index + 2] = 255;
              data[index + 3] = 255;
              continue;
            }
            const gray = (0.299 * data[index]) + (0.587 * data[index + 1]) + (0.114 * data[index + 2]);
            const boosted = Math.max(0, Math.min(255, Math.round((gray - 128) * 1.22 + 128)));
            const value = boosted > 246 ? 255 : (boosted < 52 ? 0 : boosted);
            data[index] = value;
            data[index + 1] = value;
            data[index + 2] = value;
            data[index + 3] = 255;
          }
          context.putImageData(imageData, 0, 0);
        } catch (error) {
        }
        return canvas;
      };

      const analyzePdfBrowserOcrTextOnServer = async (text = "") => {
        const { payload } = await fetchAuthJson("/pdf/analyze-text?client_source=pdf_browser_ocr_analyze", {
          method: "POST",
          body: JSON.stringify({
            path: pdfState.path || "",
            page: pdfState.page || 1,
            text: normalizePdfGhostEyeTextCase(text || ""),
          }),
        });
        return payload || {};
      };

      const runPdfBrowserOcrSelection = async (requestRect = null) => {
        const cropCanvas = capturePdfSelectionCanvasForBrowserOcr(requestRect);
        if (!cropCanvas) {
          throw new Error("Browser OCR could not crop this region.");
        }
        setPdfStatus("Browser OCR is loading on this device...");
        const tesseract = await loadPdfBrowserOcrEngine();
        const englishOnly = normalizePdfOcrEngine(pdfOcrEngine) === "browser-en";
        const ocrLang = englishOnly ? "eng" : "vie+eng";
        const ocrCanvas = englishOnly ? optimizePdfBrowserOcrCanvas(cropCanvas) : cropCanvas;
        setPdfStatus(englishOnly ? "Browser OCR is reading with Only EN fast mode..." : "Browser OCR is reading with EN+VI mode...");
        const result = await tesseract.recognize(ocrCanvas, ocrLang, {
          ...(englishOnly ? {
            preserve_interword_spaces: "1",
            tessedit_pageseg_mode: "6",
          } : {}),
          logger(info) {
            if (!info || !info.status) {
              return;
            }
            const progress = Math.max(0, Math.min(100, Math.round((Number(info.progress || 0) || 0) * 100)));
            const label = englishOnly ? "Browser OCR EN" : "Browser OCR EN+VI";
            setPdfStatus(progress ? `${label}: ${info.status} ${progress}%` : `${label}: ${info.status}`);
          },
        });
        const browserText = normalizePdfGhostEyeTextCase(result && result.data ? result.data.text || "" : "");
        setPdfStatus("Browser OCR text ready. Sending text to server for vocabulary...");
        const payload = await analyzePdfBrowserOcrTextOnServer(browserText);
        return {
          ...payload,
          text: normalizePdfGhostEyeTextCase(payload.text || browserText),
          page: payload.page || pdfState.page,
          engine: "browser-ocr",
          browser_ocr: true,
        };
      };

      const resetPdfOcrAppendBatch = () => {
        pdfOcrActiveBatch += 1;
        pdfOcrAppendSequence = 0;
        pdfOcrAppendBaseFound = "";
        pdfOcrAppendBaseExplore = "";
        pdfOcrAppendSlots = [];
      };

      const renderPdfOcrAppendBatch = (latestVocab = {}) => {
        const texts = pdfOcrAppendSlots
          .slice()
          .sort((left, right) => Number(left.order || 0) - Number(right.order || 0))
          .map((slot) => normalizePdfGhostEyeTextCase(slot.text || ""))
          .filter(Boolean);
        const foundText = joinPdfGhostText(pdfOcrAppendBaseFound, ...texts);
        const exploreText = joinPdfGhostText(pdfOcrAppendBaseExplore, ...texts);
        setPdfGhostEyeTextState(foundText, { resetView: false });
        if (pdfEls && pdfEls.ocrText) {
          renderPdfGhostEyeTextByMode(latestVocab || {});
        }
        if (pdfEls && pdfEls.exploreInput) {
          pdfEls.exploreInput.value = exploreText || "";
        }
        return { foundText, exploreText };
      };

      const runPdfOcrSelection = async (options = {}) => {
        if (!pdfState.selection || !pdfState.path) {
          setPdfStatus("Select a PDF region first.", true);
          return;
        }
        const appendMode = Boolean(options.append);
        const requestRect = normalizePdfSelectionState(options.selection || pdfState.selection);
        if (!requestRect) {
          setPdfStatus("Select a valid PDF region first.", true);
          return;
        }
        let requestBatch = pdfOcrActiveBatch;
        let appendSlot = null;
        if (!appendMode) {
          resetPdfOcrAppendBatch();
          requestBatch = pdfOcrActiveBatch;
        } else {
          if (!pdfOcrAppendSlots.length) {
            pdfOcrAppendBaseFound = normalizePdfGhostEyeTextCase(pdfState.ocrRawText || pdfState.ocrText || "");
            pdfOcrAppendBaseExplore = normalizePdfGhostEyeTextCase(pdfEls && pdfEls.exploreInput ? pdfEls.exploreInput.value : pdfState.ocrText || "");
          }
          appendSlot = {
            order: pdfOcrAppendSequence += 1,
            text: "",
            pending: true,
          };
          pdfOcrAppendSlots.push(appendSlot);
        }
        pdfExploreAnalyzeSerial += 1;
        setPdfStatus(appendMode ? "Ghost Eye is reading and adding another region..." : "Ghost Eye is reading the selected region...");
        if (!appendMode && pdfEls && pdfEls.ocrText) {
          pdfEls.ocrText.textContent = "Ghost Eye is reading the selected region...";
        }
        if (!appendMode && pdfEls && pdfEls.exploreInput) {
          pdfEls.exploreInput.value = "";
        }
        closePdfTranslationPopup();
        if (pdfEls && pdfEls.translation) {
          pdfEls.translation.textContent = "Vietnamese translation will appear here.";
        }
        if (!appendMode) {
          pdfState.ocrText = "";
          pdfState.ocrRawText = "";
          pdfState.ocrFilteredText = "";
          pdfState.ocrViewMode = "raw";
        }
        pdfState.translation = "";
        if (!appendMode) {
          updatePdfVocabStats(null);
        }
        try {
          let payload = null;
          if (normalizePdfOcrEngine(pdfOcrEngine) !== "server") {
            payload = await runPdfBrowserOcrSelection(requestRect);
          } else {
            const endpoint = pdfState.mode === "picture" ? "/picture/ocr?client_source=picture_two_point_ocr" : "/pdf/ocr?client_source=pdf_two_point_ocr";
            const result = await fetchAuthJson(endpoint, {
              method: "POST",
              body: JSON.stringify({
                path: pdfState.path,
                page: pdfState.page,
                scale: Math.max(2.4, Math.min(6.5, Number(pdfState.scale || 2.4) || 2.4)),
                rect: requestRect,
              }),
            });
            payload = result.payload || {};
          }
          const text = normalizePdfGhostEyeTextCase(payload.text || "");
          const vocab = payload && payload.vocabulary && typeof payload.vocabulary === "object" ? payload.vocabulary : {};
          if (requestBatch !== pdfOcrActiveBatch) {
            return;
          }
          if (appendMode) {
            if (!appendSlot) {
              return;
            }
            appendSlot.text = text;
            appendSlot.pending = false;
            renderPdfOcrAppendBatch(vocab);
          } else {
            setPdfGhostEyeTextState(text, { resetView: true });
            if (pdfEls && pdfEls.ocrText) {
              renderPdfGhostEyeTextByMode(vocab);
            }
            if (pdfEls && pdfEls.exploreInput) {
              pdfEls.exploreInput.value = text || "";
            }
          }
          setPdfGhostConsoleVisible(true, { silent: true });
          setPdfOcrTab("found");
          if (pdfEls && pdfEls.ocrMeta) {
            const regionCount = Array.isArray(pdfState.selections) && pdfState.selections.length ? pdfState.selections.length : 1;
            const engineLabel = payload && payload.browser_ocr ? "Browser OCR" : "Server OCR";
            pdfEls.ocrMeta.textContent = `Ghost Eye | ${engineLabel} | ${pdfState.mode === "picture" ? "Image" : "Page"} ${payload.page || pdfState.page} | Regions ${regionCount}`;
          }
          updatePdfVocabStats(vocab);
          syncPdfSelectionOverlay(true);
          const pendingCount = appendMode ? pdfOcrAppendSlots.filter((slot) => slot.pending).length : 0;
          setPdfStatus(appendMode
            ? (pendingCount ? `Ghost Eye added this region. Waiting for ${pendingCount} more region${pendingCount === 1 ? "" : "s"}...` : "Ghost Eye added all selected regions. Text Found and Text To Explore were joined.")
            : "Ghost Eye text is ready. Edit Text to Explore if needed.");
          schedulePdfProgressSave(250, { skipLastFileSync: true });
        } catch (error) {
          let message = error && error.message ? error.message : "Ghost Eye could not read this region.";
          if (/tesseract|ocr/i.test(message)) {
            message = "Ghost Eye could not read this region. Try a clearer or larger selection.";
          }
          if (appendMode && appendSlot && requestBatch === pdfOcrActiveBatch) {
            appendSlot.pending = false;
            appendSlot.text = "";
            renderPdfOcrAppendBatch({});
          }
          if (!appendMode && pdfEls && pdfEls.ocrText) {
            pdfEls.ocrText.textContent = message;
          }
          hidePdfWordDetail();
          setPdfStatus(message, true);
        }
      };

      const runPdfCacheOcrCurrentPage = async () => {
        const pictureRow = pdfState.mode === "picture" && Array.isArray(pdfState.pictureImages)
          ? (pdfState.pictureImages[Math.max(0, Math.floor(Number(pdfState.page || 1) || 1) - 1)] || null)
          : null;
        const { payload } = await fetchAuthJson("/pdf/cache-ocr-page?client_source=pdf_cache_ocr_current_page", {
          method: "POST",
          body: JSON.stringify({
            path: pdfState.path,
            page: pdfState.page,
            mode: pdfState.mode === "picture" ? "picture" : "pdf",
            name: pdfState.name || "",
            title: pdfState.title || "",
            folder: pdfState.mode === "picture" ? (pdfState.title || pdfState.name || "") : "",
            image: pictureRow && pictureRow.name ? pictureRow.name : "",
          }),
        });
        return payload || {};
      };

      const updatePdfVocabStats = (stats = null) => {
        pdfState.vocabStats = stats && typeof stats === "object" ? stats : null;
        if (!pdfState.vocabStats) {
          pdfState.vocabMission = null;
          pdfState.vocabDetailMap = {};
          hidePdfWordDetail();
        }
        if (!pdfEls || !pdfEls.vocabStats) {
          return;
        }
        if (!pdfState.vocabStats) {
          pdfEls.vocabStats.textContent = "Vocabulary: not scanned";
          updatePdfVocabularyMissionButtons();
          return;
        }
        const total = Math.max(0, Number(pdfState.vocabStats.total || 0) || 0);
        const unknown = Math.max(0, Number(pdfState.vocabStats.unknown || 0) || 0);
        const known = Math.max(0, Number(pdfState.vocabStats.known || 0) || 0);
        const phraseUnknown = Math.max(0, Number(pdfState.vocabStats.phrase_unknown || 0) || 0);
        const phraseTotal = Math.max(0, Number(pdfState.vocabStats.phrase_total || 0) || 0);
        const phrasalUnknown = Math.max(0, Number(pdfState.vocabStats.phrasal_verb_unknown || 0) || 0);
        const phrasalTotal = Math.max(0, Number(pdfState.vocabStats.phrasal_verb_total || 0) || 0);
        const phraseText = phraseTotal ? ` | Phrases: ${phraseUnknown}/${phraseTotal}` : "";
        const phrasalText = phrasalTotal ? ` | Phrasal verbs: ${phrasalUnknown}/${phrasalTotal}` : "";
        pdfEls.vocabStats.textContent = `Unknown words: ${unknown}/${total} | Known: ${known}${phraseText}${phrasalText}`;
        updatePdfVocabularyMissionButtons();
      };

      const updatePdfVocabularyMissionButtons = () => {
        updatePdfVocabularyCreateUi();
        if (!pdfEls || !pdfEls.learnNow) {
          return;
        }
        const files = pdfState.vocabMission && Array.isArray(pdfState.vocabMission.files) ? pdfState.vocabMission.files : [];
        pdfEls.learnNow.hidden = files.length <= 0;
      };

      const resetPdfVocabularyMissionForBankChange = () => {
        if (pdfState && pdfState.vocabMission) {
          pdfState.vocabMission = null;
        }
        updatePdfVocabularyMissionButtons();
      };

      const renderPdfUnlearnedButton = () => {
        const count = Object.keys(pdfState.unlearnedWords || {}).length;
        if (pdfEls && pdfEls.unlearnedOpen) {
          pdfEls.unlearnedOpen.textContent = count ? `Unlearned Words (${count})` : "Unlearned Words";
        }
        if (pdfEls && pdfEls.unlearnedSubtitle) {
          pdfEls.unlearnedSubtitle.textContent = count
            ? `${count} word${count === 1 ? "" : "s"} ready for an Immediate Mission Space_V pack.`
            : "Collect new words from Ghost Eye before creating a Space_V mission.";
        }
      };

      const updatePdfWordDetailUnlearnedButtons = () => {
        if (!pdfEls || !pdfEls.wordDetail) {
          return;
        }
        pdfEls.wordDetail.querySelectorAll('[data-pdf-action="addWordDetailUnlearned"]').forEach((button) => {
          const key = pdfWordKey(button.getAttribute("data-word-key") || "");
          const added = Boolean(key && pdfState.unlearnedWords && pdfState.unlearnedWords[key]);
          button.disabled = added;
          button.textContent = added ? "Added" : "Add";
          button.title = added ? "Already in Unlearned Words" : "Add this word to Unlearned Words";
          button.classList.toggle("is-added", added);
        });
      };

      const pdfUnknownDetailsFromStats = (stats = null) => {
        const source = stats && typeof stats === "object" ? stats : pdfState.vocabStats;
        if (!source || typeof source !== "object") {
          return [];
        }
        const out = new Map();
        const add = (item) => {
          const detail = normalizePdfWordDetail(item);
          const key = pdfWordKey(detail && detail.word);
          if (detail && key && !out.has(key)) {
            out.set(key, detail);
          }
        };
        (Array.isArray(source.unknown_words) ? source.unknown_words : []).forEach(add);
        const tokenDetails = source.token_details && typeof source.token_details === "object"
          ? source.token_details
          : (source.tokenDetails && typeof source.tokenDetails === "object" ? source.tokenDetails : {});
        (Array.isArray(source.unknown_tokens) ? source.unknown_tokens : []).forEach((token) => {
          const key = pdfWordKey(token);
          const details = tokenDetails && tokenDetails[key];
          (Array.isArray(details) ? details : [details]).forEach(add);
        });
        return Array.from(out.values());
      };

      const addPdfUnknownWordsToBank = () => {
        const details = pdfUnknownDetailsFromStats();
        if (!details.length) {
          setPdfStatus("No unlearned words are available from the current Ghost Eye text.", true);
          return;
        }
        let added = 0;
        pdfState.unlearnedWords = pdfState.unlearnedWords || {};
        details.forEach((detail) => {
          const key = pdfWordKey(detail.word);
          if (!key || pdfState.unlearnedWords[key]) {
            return;
          }
          pdfState.unlearnedWords[key] = detail;
          added += 1;
        });
        if (added > 0) {
          resetPdfVocabularyMissionForBankChange();
        }
        savePdfUnlearnedBank();
        renderPdfUnlearnedPopup();
        setPdfStatus(added ? `Added ${added} unlearned word${added === 1 ? "" : "s"} to the word bank.` : "These unlearned words are already in the word bank.");
      };

      const addPdfWordDetailToBank = (index = 0) => {
        const list = Array.isArray(pdfState.wordDetailEntries) ? pdfState.wordDetailEntries : [];
        const safeIndex = Math.max(0, Math.min(list.length - 1, Math.floor(Number(index) || 0)));
        const detail = normalizePdfWordDetail(list[safeIndex] || {});
        const key = pdfWordKey(detail && detail.word);
        if (!detail || !key) {
          setPdfStatus("No word detail is available to add.", true);
          return;
        }
        pdfState.unlearnedWords = pdfState.unlearnedWords && typeof pdfState.unlearnedWords === "object"
          ? pdfState.unlearnedWords
          : {};
        if (pdfState.unlearnedWords[key]) {
          updatePdfWordDetailUnlearnedButtons();
          setPdfStatus(`"${detail.word}" is already in Unlearned Words.`);
          return;
        }
        pdfState.unlearnedWords[key] = {
          ...detail,
          surface: detail.surface || pdfState.wordDetailSurface || detail.word,
        };
        resetPdfVocabularyMissionForBankChange();
        savePdfUnlearnedBank();
        updatePdfWordDetailUnlearnedButtons();
        renderPdfUnlearnedPopup();
        setPdfStatus(`Added "${detail.word}" to Unlearned Words.`);
      };

      const renderPdfUnlearnedPopup = () => {
        renderPdfUnlearnedButton();
        updatePdfVocabularyCreateUi();
        if (!pdfEls || !pdfEls.unlearnedList) {
          return;
        }
        const words = Object.values(pdfState.unlearnedWords || {})
          .map(normalizePdfWordDetail)
          .filter(Boolean)
          .sort((a, b) => pdfWordKey(a.word).localeCompare(pdfWordKey(b.word)));
        pdfEls.unlearnedList.innerHTML = "";
        if (!words.length) {
          const empty = document.createElement("div");
          empty.className = "ft-pdf-unlearned-empty";
          empty.textContent = "No unlearned words have been added yet.";
          pdfEls.unlearnedList.appendChild(empty);
          return;
        }
        words.forEach((detail) => {
          const row = document.createElement("div");
          row.className = "ft-pdf-unlearned-row";
          const word = document.createElement("div");
          word.className = "ft-pdf-unlearned-word";
          word.textContent = detail.word;
          const meta = document.createElement("div");
          meta.className = "ft-pdf-unlearned-meta";
          const surface = detail.surface && pdfWordKey(detail.surface) !== pdfWordKey(detail.word) ? `From "${detail.surface}" | ` : "";
          meta.textContent = `${surface}${detail.type || "Type not available"} | ${detail.meaning || "No meaning data"}`;
          const remove = document.createElement("button");
          remove.className = "ft-pdf-button";
          remove.type = "button";
          remove.textContent = "Remove";
          remove.setAttribute("data-pdf-action", "removeUnlearned");
          remove.setAttribute("data-word-key", pdfWordKey(detail.word));
          row.append(word, meta, remove);
          pdfEls.unlearnedList.appendChild(row);
        });
      };

      const openPdfUnlearnedPopup = () => {
        renderPdfUnlearnedPopup();
        if (pdfEls && pdfEls.unlearnedModal) {
          pdfEls.unlearnedModal.classList.remove("is-hidden");
          pdfEls.unlearnedModal.setAttribute("aria-hidden", "false");
        }
      };

      const closePdfUnlearnedPopup = () => {
        if (pdfEls && pdfEls.unlearnedModal) {
          pdfEls.unlearnedModal.classList.add("is-hidden");
          pdfEls.unlearnedModal.setAttribute("aria-hidden", "true");
        }
      };

      const removePdfUnlearnedWord = (keyValue = "") => {
        const key = pdfWordKey(keyValue);
        if (!key || !pdfState.unlearnedWords || !pdfState.unlearnedWords[key]) {
          return;
        }
        delete pdfState.unlearnedWords[key];
        resetPdfVocabularyMissionForBankChange();
        savePdfUnlearnedBank();
        updatePdfWordDetailUnlearnedButtons();
        renderPdfUnlearnedPopup();
      };

      const clearPdfUnlearnedBank = (options = {}) => {
        const keepMission = Boolean(options.keepMission);
        const silent = Boolean(options.silent);
        pdfState.unlearnedWords = {};
        if (!keepMission) {
          resetPdfVocabularyMissionForBankChange();
        }
        savePdfUnlearnedBank();
        updatePdfWordDetailUnlearnedButtons();
        renderPdfUnlearnedPopup();
        if (!silent) {
          setPdfStatus("Unlearned word bank cleared.");
        }
      };

      const createPdfUnlearnedVocabularyMission = async () => {
        if (pdfState.vocabCreateBusy) {
          setPdfStatus(pdfState.vocabCreateMessage || pdfVocabularyCreateBusyText(pdfState.vocabCreateKind || "unlearned"));
          return;
        }
        if (!pdfState.path) {
          setPdfStatus("Open a PDF or picture first.", true);
          return;
        }
        const words = Object.values(pdfState.unlearnedWords || {})
          .map(normalizePdfWordDetail)
          .filter((item) => item && clean(item.word));
        if (!words.length) {
          setPdfStatus("Add unlearned words first.", true);
          return;
        }
        const requestPath = pdfState.path;
        const requestPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1));
        const requestMode = pdfState.mode === "picture" ? "picture" : "pdf";
        setPdfVocabularyCreateBusy(true, {
          kind: "unlearned",
          message: "Word bank forge is creating Space_V packs. You can keep changing pages.",
        });
        const requestBusyStartedAt = pdfState.vocabCreateStartedAt;
        try {
          const { payload } = await fetchAuthJson("/pdf/create-vocabulary?client_source=pdf_create_vocabulary", {
            method: "POST",
            body: JSON.stringify({
              path: requestPath,
              page: requestPage,
              text: words.map((item) => clean(item.word)).join("\n"),
              word_items: words,
              include_known: false,
              source: "unlearned_word_bank",
            }),
          });
          const files = Array.isArray(payload.files) ? payload.files : [];
          const stillOnRequestDocument = pdfState.path === requestPath
            && pdfState.mode === requestMode
            && pdfState.vocabCreateStartedAt === requestBusyStartedAt;
          if (!stillOnRequestDocument) {
            return;
          }
          pdfState.vocabMission = {
            mission_id: clean(payload.mission_id || ""),
            files,
            page: Number(payload.page || requestPage) || requestPage,
            folder: normalizeServerPathValue(payload.mission_folder || (files[0] && files[0].path ? serverParentPathForFile(files[0].path) : "")),
          };
          invalidateServerBrowserDataAfterMutation();
          const stillOnRequestPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1)) === requestPage;
          setPdfVocabularyCreateBusy(false);
          if (stillOnRequestPage && payload.vocabulary && typeof payload.vocabulary === "object") {
            updatePdfVocabStats(payload.vocabulary);
          } else {
            updatePdfVocabularyMissionButtons();
          }
          if (!files.length) {
            setPdfStatus("No new Space_V pack was needed for this word bank.");
            return;
          }
          clearPdfUnlearnedBank({ keepMission: true, silent: true });
          closePdfUnlearnedPopup();
          setPdfStatus(`Unlearned word mission ready: ${files.length} Space_V pack${files.length === 1 ? "" : "s"}.`);
        } catch (error) {
          if (pdfState.path === requestPath && pdfState.mode === requestMode && pdfState.vocabCreateStartedAt === requestBusyStartedAt) {
            setPdfVocabularyCreateBusy(false);
            setPdfStatus(error && error.message ? error.message : "Could not create vocabulary from unlearned words.", true);
          }
        }
      };

      const scanPdfCurrentPage = async () => {
        if (!pdfState.path) {
          setPdfStatus("Open a PDF first.", true);
          return;
        }
        if (pdfState.scanBusy) {
          setPdfStatus("Ghost Eye is already scanning this page.");
          return;
        }
        pdfExploreAnalyzeSerial += 1;
        pdfState.scanBusy = true;
        revealPdfGhostConsoleForScan({ silent: true });
        syncPdfCompactDock();
        setPdfStatus("Ghost Eye is scanning the full page...");
        if (pdfEls && pdfEls.ocrText) {
          pdfEls.ocrText.textContent = "Ghost Eye is scanning the full page...";
        }
        closePdfTranslationPopup();
        updatePdfVocabStats(null);
        try {
          let payload = null;
          pdfScanPageSource = typeof readEffectivePdfScanPageSourcePreference === "function"
            ? readEffectivePdfScanPageSourcePreference()
            : readPdfScanPageSourcePreference();
          syncPdfCompactDock();
          const localImageMode = Boolean(pdfState && pdfState.localImageActive);
          const preferCacheOcr = normalizePdfScanPageSource(pdfScanPageSource) === "cache";
          if (localImageMode) {
            setPdfStatus(preferCacheOcr
              ? "Local Images are browser-only. Ghost Eye is scanning this local image with Browser OCR..."
              : "Ghost Eye is scanning this local image with Browser OCR...");
            payload = await runPdfBrowserOcrSelection({ x: 0, y: 0, w: 1, h: 1 });
          } else if (preferCacheOcr) {
            setPdfStatus("Ghost Eye is checking Cache OCR for this page...");
            const cachePayload = await runPdfCacheOcrCurrentPage();
            if (cachePayload && cachePayload.cache_hit) {
              payload = cachePayload;
              setPdfStatus("Cache OCR hit. Loading cached page text...");
            } else {
              const reason = clean(cachePayload && cachePayload.reason ? cachePayload.reason : "cache_missing");
              const folder = clean(cachePayload && cachePayload.cache_folder ? cachePayload.cache_folder : "");
              const root = clean(cachePayload && cachePayload.cache_root ? cachePayload.cache_root : "");
              const tried = Array.isArray(cachePayload && cachePayload.candidates) ? cachePayload.candidates.map(clean).filter(Boolean).slice(0, 4).join(" | ") : "";
              throw new Error(`Cache OCR missing: ${reason}${folder ? ` | folder: ${folder}` : ""}${root ? ` | root: ${root}` : ""}${tried ? ` | tried: ${tried}` : ""}`);
            }
          }
          if (!payload && !preferCacheOcr && normalizePdfOcrEngine(pdfOcrEngine) !== "server") {
            payload = await runPdfBrowserOcrSelection({ x: 0, y: 0, w: 1, h: 1 });
          } else if (!payload && !preferCacheOcr) {
            const endpoint = pdfState.mode === "picture" ? "/picture/scan-image" : "/pdf/scan-page";
            const result = await fetchAuthJson(endpoint, {
              method: "POST",
              body: JSON.stringify({
                path: pdfState.path,
                page: pdfState.page,
              }),
            });
            payload = result.payload || {};
          }
          const text = normalizePdfGhostEyeTextCase(payload.text || "");
          const vocab = payload && payload.vocabulary && typeof payload.vocabulary === "object" ? payload.vocabulary : {};
          setPdfGhostEyeTextState(text, { resetView: true });
          if (pdfEls && pdfEls.ocrText) {
            renderPdfGhostEyeTextByMode(vocab);
          }
          if (pdfEls && pdfEls.exploreInput) {
            pdfEls.exploreInput.value = text || "";
          }
          revealPdfGhostConsoleForScan({ silent: true });
          if (pdfEls && pdfEls.ocrMeta) {
            const engineLabel = payload && payload.cache_hit ? "Cache OCR" : (payload && payload.browser_ocr ? "Browser OCR" : "Server OCR");
            const surfaceLabel = localImageMode ? "local image" : (pdfState.mode === "picture" ? "picture" : "page");
            const pageLabel = localImageMode ? "Slot" : (pdfState.mode === "picture" ? "Image" : "Page");
            pdfEls.ocrMeta.textContent = `Ghost Eye full ${surfaceLabel} | ${engineLabel} | ${pageLabel} ${payload.page || pdfState.page}`;
          }
          updatePdfVocabStats(vocab);
          pdfState.vocabMission = null;
          updatePdfVocabularyMissionButtons();
          const unknown = Math.max(0, Number(vocab.unknown || 0) || 0);
          const total = Math.max(0, Number(vocab.total || 0) || 0);
          const readySource = payload && payload.cache_hit ? "Cache OCR" : (payload && payload.browser_ocr ? "Browser OCR" : "Server OCR");
          setPdfStatus(`${readySource} full ${localImageMode ? "local image" : (pdfState.mode === "picture" ? "picture" : "page")} ready. Unknown vocabulary: ${unknown}/${total}.`);
          schedulePdfProgressSave(250);
        } catch (error) {
          let message = error && error.message ? error.message : "Ghost Eye could not scan this page.";
          if (!/cache\s+ocr/i.test(message) && /tesseract|ocr/i.test(message)) {
            message = "Ghost Eye could not scan this page. Try a clearer page or a smaller region.";
          }
          setPdfStatus(message, true);
          if (pdfEls && pdfEls.ocrText) {
            pdfEls.ocrText.textContent = message;
          }
          hidePdfWordDetail();
        } finally {
          pdfState.scanBusy = false;
          syncPdfCompactDock();
        }
      };

      const createPdfVocabularyMission = async () => {
        if (pdfState.vocabCreateBusy) {
          setPdfStatus(pdfState.vocabCreateMessage || pdfVocabularyCreateBusyText(pdfState.vocabCreateKind || "page"));
          return;
        }
        if (!pdfState.path) {
          setPdfStatus("Open a PDF first.", true);
          return;
        }
        const text = pdfExploreText();
        const requestPath = pdfState.path;
        const requestPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1));
        const requestMode = pdfState.mode === "picture" ? "picture" : "pdf";
        setPdfVocabularyCreateBusy(true, {
          kind: "page",
          message: `Vocabulary forge is creating Space_V packs for ${requestMode === "picture" ? "image" : "page"} ${requestPage}. You can keep changing pages.`,
        });
        const requestBusyStartedAt = pdfState.vocabCreateStartedAt;
        try {
          const { payload } = await fetchAuthJson("/pdf/create-vocabulary?client_source=pdf_create_vocabulary", {
            method: "POST",
            body: JSON.stringify({
              path: requestPath,
              page: requestPage,
              text,
            }),
          });
          const files = Array.isArray(payload.files) ? payload.files : [];
          const stillOnRequestDocument = pdfState.path === requestPath
            && pdfState.mode === requestMode
            && pdfState.vocabCreateStartedAt === requestBusyStartedAt;
          if (!stillOnRequestDocument) {
            return;
          }
          pdfState.vocabMission = {
            mission_id: clean(payload.mission_id || ""),
            files,
            page: Number(payload.page || requestPage) || requestPage,
            folder: normalizeServerPathValue(payload.mission_folder || (files[0] && files[0].path ? serverParentPathForFile(files[0].path) : "")),
          };
          invalidateServerBrowserDataAfterMutation();
          const stillOnRequestPage = Math.max(1, Math.floor(Number(pdfState.page || 1) || 1)) === requestPage;
          setPdfVocabularyCreateBusy(false);
          if (stillOnRequestPage && payload.vocabulary && typeof payload.vocabulary === "object") {
            updatePdfVocabStats(payload.vocabulary);
          } else {
            updatePdfVocabularyMissionButtons();
          }
          if (!files.length) {
            setPdfStatus(`No new vocabulary is required for ${requestMode === "picture" ? "this image" : `page ${requestPage}`}.`);
            return;
          }
          setPdfStatus(`Vocabulary ready from ${requestMode === "picture" ? "image" : `page ${requestPage}`}: ${files.length} Space_V pack${files.length === 1 ? "" : "s"}.`);
        } catch (error) {
          if (pdfState.path === requestPath && pdfState.mode === requestMode && pdfState.vocabCreateStartedAt === requestBusyStartedAt) {
            setPdfVocabularyCreateBusy(false);
            setPdfStatus(error && error.message ? error.message : "Could not create vocabulary packs.", true);
          }
        }
      };

      const learnPdfVocabularyNow = async () => {
        const files = pdfState.vocabMission && Array.isArray(pdfState.vocabMission.files) ? pdfState.vocabMission.files : [];
        const first = files.find((item) => item && item.path);
        if (!first) {
          setPdfStatus("Create vocabulary packs first.", true);
          return;
        }
        const missionFolder = normalizeServerPathValue(
          (pdfState.vocabMission && pdfState.vocabMission.folder)
          || serverParentPathForFile(first.path)
        );
        if (missionFolder) {
          rememberServerPath(missionFolder);
        }
        rememberServerFile(first, { syncNow: true });
        await loadServerLessonFile({
          ...first,
          extension: ".Space_V",
          type: "file",
          name: first.name || first.path.split("/").pop() || "Vocabulary.Space_V",
        });
      };

      const pdfExploreText = () => preserveQuestionText(
        (pdfEls && pdfEls.exploreInput ? pdfEls.exploreInput.value : "")
        || pdfState.ocrText
        || (pdfEls && pdfEls.ocrText ? pdfEls.ocrText.textContent : "")
        || ""
      );

      const translatePdfOcrText = async () => {
        const text = pdfExploreText();
        if (!text) {
          setPdfStatus("Text to Explore is empty.", true);
          return;
        }
        const cached = readCachedPdfTranslation(text);
        if (cached) {
          pdfState.translation = preserveQuestionText(cached.translated || "");
          openPdfTranslationPopup(pdfState.translation || "No translation returned.");
          setPdfStatus("Loaded cached Vietnamese translation.");
          schedulePdfProgressSave(180);
          return;
        }
        setPdfStatus("Translating with server...");
        openPdfTranslationPopup("Server is translating...");
        try {
          const { payload } = await fetchAuthJson("/pdf/translate?client_source=pdf_translate_explore_text", {
            method: "POST",
            body: JSON.stringify({ text, target: "vi", source: "auto" }),
          });
          pdfState.translation = preserveQuestionText(payload.translated || "");
          storeCachedPdfTranslation(text, pdfState.translation);
          openPdfTranslationPopup(pdfState.translation || "No translation returned.");
          setPdfStatus("Translation ready.");
          schedulePdfProgressSave(250);
        } catch (error) {
          const message = error && error.message ? error.message : "Translate failed.";
          openPdfTranslationPopup(message);
          setPdfStatus(message, true);
        }
      };

      const speakPdfExploreText = async () => {
        const text = pdfExploreText();
        if (!text) {
          setPdfStatus("Text to Explore is empty.", true);
          return;
        }
        const voice = clean(pdfEls && pdfEls.voice ? pdfEls.voice.value : "") || "kokoro:am_adam";
        setPdfStatus("Preparing Ghost Eye voice...");
        try {
          const { payload } = await fetchAuthJson("/pdf/speak?client_source=pdf_speak", {
            method: "POST",
            body: JSON.stringify({ text, voice }),
          });
          const audio = payload && payload.audio && typeof payload.audio === "object" ? payload.audio : {};
          const audioPath = clean(audio.path || payload.audio_path || "");
          if (!audioPath) {
            throw new Error("No voice file returned.");
          }
          if (pdfAudioPlayer) {
            try {
              pdfAudioPlayer.pause();
            } catch (error) {
            }
          }
          pdfAudioPlayer = new Audio(serverAssetUrl(audioPath));
          await pdfAudioPlayer.play();
          setPdfStatus(`Playing ${clean(payload.voice_label || audio.label || "Ghost Eye voice")}.`);
        } catch (error) {
          setPdfStatus(error && error.message ? error.message : "Could not play Ghost Eye voice.", true);
        }
      };

      const playPdfWordAudio = async (word = "", voice = "", audioUrl = "") => {
        const text = clean(word);
        const voiceKey = clean(voice);
        const cachedUrl = clean(audioUrl);
        if (!text || !voiceKey) {
          setPdfStatus("No word audio target.", true);
          return;
        }
        setPdfStatus(`Preparing ${voiceKey.endsWith("en-US") ? "US" : "UK"} audio for ${text}...`);
        try {
          if (cachedUrl) {
            try {
              const playedLocal = await playPdfIndexedAudioUrl(cachedUrl, voiceKey);
              if (playedLocal) {
                setPdfStatus(`Playing ${text} (${voiceKey.endsWith("en-US") ? "US" : "UK"}) from local cache.`);
                return;
              }
              if (pdfAudioPlayer) {
                try {
                  pdfAudioPlayer.pause();
                } catch (error) {
                }
              }
              pdfAudioPlayer = new Audio(serverAssetUrl(cachedUrl));
              await pdfAudioPlayer.play();
              setPdfStatus(`Playing ${text} (${voiceKey.endsWith("en-US") ? "US" : "UK"}) from cache.`);
              return;
            } catch (error) {
              setPdfStatus("Cached audio missed. Asking server for a fresh clip...");
            }
          }
          const { payload } = await fetchAuthJson("/pdf/speak?client_source=pdf_speak", {
            method: "POST",
            body: JSON.stringify({ text, voice: voiceKey }),
          });
          const audio = payload && payload.audio && typeof payload.audio === "object" ? payload.audio : {};
          const audioPath = clean(audio.path || payload.audio_path || "");
          if (!audioPath) {
            throw new Error("No word audio returned.");
          }
          const playedLocal = await playPdfIndexedAudioUrl(audioPath, voiceKey);
          if (playedLocal) {
            setPdfStatus(`Playing ${text} (${voiceKey.endsWith("en-US") ? "US" : "UK"}) from local cache.`);
            return;
          }
          if (pdfAudioPlayer) {
            try {
              pdfAudioPlayer.pause();
            } catch (error) {
            }
          }
          pdfAudioPlayer = new Audio(serverAssetUrl(audioPath));
          await pdfAudioPlayer.play();
          setPdfStatus(`Playing ${text} (${voiceKey.endsWith("en-US") ? "US" : "UK"}).`);
        } catch (error) {
          setPdfStatus(error && error.message ? error.message : "Could not play word audio.", true);
        }
      };

      const formatPdfAgentThinkingTime = (elapsedMs = 0) => {
        const total = Math.max(0, Math.floor(Number(elapsedMs || 0) / 1000));
        const minutes = String(Math.floor(total / 60)).padStart(2, "0");
        const seconds = String(total % 60).padStart(2, "0");
        return `${minutes}:${seconds}`;
      };

      const setPdfAgentThinking = (active) => {
        if (pdfAgentThinkingTimer) {
          clearInterval(pdfAgentThinkingTimer);
          pdfAgentThinkingTimer = 0;
        }
        if (!pdfEls || !pdfEls.agentThinkingTime) {
          return;
        }
        if (!active) {
          pdfAgentThinkingStartedAt = 0;
          pdfEls.agentThinkingTime.textContent = "00:00";
          return;
        }
        pdfAgentThinkingStartedAt = Date.now();
        const tick = () => {
          pdfEls.agentThinkingTime.textContent = formatPdfAgentThinkingTime(Date.now() - pdfAgentThinkingStartedAt);
        };
        tick();
        pdfAgentThinkingTimer = window.setInterval(tick, 500);
      };

      const openPdfAgentPopup = (text = "", options = {}) => {
        if (!pdfEls || !pdfEls.agentModal || !pdfEls.agentCard || !pdfEls.agentAnswer) {
          return;
        }
        const loading = Boolean(options && options.loading);
        pdfEls.agentModal.classList.remove("is-hidden");
        pdfEls.agentModal.setAttribute("aria-hidden", "false");
        pdfEls.agentCard.classList.toggle("is-loading", loading);
        setPdfAgentThinking(loading);
        pdfEls.agentAnswer.textContent = preserveQuestionText(text || "");
        if (pdfEls.agentFootnote) {
          pdfEls.agentFootnote.textContent = clean(options && options.footnote) || "Uses Text to Explore as context.";
        }
      };

      const setPdfAgentPopupHtml = (html = "", options = {}) => {
        if (!pdfEls || !pdfEls.agentModal || !pdfEls.agentCard || !pdfEls.agentAnswer) {
          return;
        }
        const loading = Boolean(options && options.loading);
        pdfEls.agentModal.classList.remove("is-hidden");
        pdfEls.agentModal.setAttribute("aria-hidden", "false");
        pdfEls.agentCard.classList.toggle("is-loading", loading);
        setPdfAgentThinking(loading);
        pdfEls.agentAnswer.innerHTML = html || "";
        if (pdfEls.agentFootnote) {
          pdfEls.agentFootnote.textContent = clean(options && options.footnote) || "Uses Text to Explore as context.";
        }
      };

      const setPdfAgentHistoryBackVisible = (visible) => {
        if (pdfEls && pdfEls.agentCard) {
          pdfEls.agentCard.classList.toggle("has-history-back", Boolean(visible));
        }
      };

      const closePdfAgentPopup = () => {
        if (!pdfEls || !pdfEls.agentModal || !pdfEls.agentCard) {
          return;
        }
        setPdfAgentThinking(false);
        setPdfAgentHistoryBackVisible(false);
        pdfEls.agentCard.classList.remove("is-loading");
        pdfEls.agentModal.classList.add("is-hidden");
        pdfEls.agentModal.setAttribute("aria-hidden", "true");
      };

      const pdfAgentHistoryRows = (rows = []) => (Array.isArray(rows) ? rows : [])
        .filter((item) => item && typeof item === "object")
        .filter((item) => {
          const space = clean(item.space || "");
          const kind = clean(item.context && item.context.kind);
          return space === "space_pdf" || space === "space_picture" || kind === "space_pdf_ghost_eye" || kind === "space_picture_ghost_eye";
        });

      const showPdfAgentHistoryEntry = (id = "") => {
        const wanted = clean(id);
        const item = (pdfState.agentHistory || []).find((row) => clean(row && row.id) === wanted);
        if (!item) {
          return;
        }
        openPdfAgentPopup(preserveQuestionText(item.vietnamese || item.answer_vi || item.text || "No saved answer."), {
          loading: false,
          footnote: `${clean(item.title || "Saved Ghost Eye answer")} | ${clean(item.created_at || item.updated_at || "")}`,
        });
        setPdfAgentHistoryBackVisible(true);
      };

      const renderPdfAgentHistoryPopup = () => {
        const rows = pdfAgentHistoryRows(pdfState.agentHistory || []);
        pdfState.agentBackMode = "pdf";
        setPdfAgentHistoryBackVisible(false);
        if (!rows.length) {
          setPdfAgentPopupHtml('<div class="ft-pdf-agent-history-empty">No Ghost Eye Agent history yet.</div>', {
            loading: false,
            footnote: "History",
          });
          return;
        }
        const html = `<div class="ft-pdf-agent-history-list">${rows.map((item) => {
          const title = escapeHtml(clean(item.title || "Ghost Eye answer"));
          const meta = escapeHtml(clean(item.created_at || item.updated_at || ""));
          const preview = escapeHtml(clean(item.vietnamese || item.answer_vi || item.text || "").slice(0, 260));
          const id = escapeHtml(clean(item.id || ""));
          return `<button class="ft-pdf-agent-history-row" type="button" data-pdf-action="showPdfAgentHistory" data-history-id="${id}">
            <span class="ft-pdf-agent-history-title">${title}</span>
            <span class="ft-pdf-agent-history-meta">${meta}</span>
            <span class="ft-pdf-agent-history-preview">${preview}</span>
          </button>`;
        }).join("")}</div>`;
        setPdfAgentPopupHtml(html, {
          loading: false,
          footnote: `${rows.length} saved Ghost Eye answer${rows.length === 1 ? "" : "s"}`,
        });
      };

      const openPdfAgentHistoryPopup = async () => {
        setPdfAgentHistoryBackVisible(false);
        pdfState.agentBackMode = "pdf";
        setPdfAgentPopupHtml('<div class="ft-pdf-agent-history-empty">Loading Ghost Eye Agent history...</div>', {
          loading: true,
          footnote: "History",
        });
        try {
          const { payload } = await fetchAuthJson("/ai-agent/history?limit=120");
          pdfState.agentHistory = pdfAgentHistoryRows(payload && payload.history);
          renderPdfAgentHistoryPopup();
        } catch (error) {
          const message = escapeHtml(error && error.message ? error.message : "Could not load Ghost Eye Agent history.");
          setPdfAgentPopupHtml(`<div class="ft-pdf-agent-history-empty">${message}</div>`, {
            loading: false,
            footnote: "History failed",
          });
        }
      };

      const pdfWordAgentPayload = (index = 0) => {
        const list = Array.isArray(pdfState.wordDetailEntries) ? pdfState.wordDetailEntries : [];
        const safeIndex = Math.max(0, Math.min(list.length - 1, Math.floor(Number(index) || 0)));
        const detail = list[safeIndex] || {};
        const word = clean(detail.word || detail.surface || pdfState.wordDetailSurface || "");
        if (!word) {
          return null;
        }
        return {
          word,
          surface: clean(pdfState.wordDetailSurface || detail.surface || word),
          detail,
          question: `Explain ${word}: usage, contexts, examples, and common mistakes.`,
          page: pdfState.page || 1,
          title: pdfState.title || pdfState.name || (pdfState.mode === "picture" ? "Picture" : "PDF"),
          file: pdfState.path || "",
          space: pdfState.mode === "picture" ? "space_picture" : "space_pdf",
        };
      };

      const showPdfWordAgentHistoryEntry = (id = "") => {
        const wanted = clean(id);
        const item = (pdfState.wordAgentHistory || []).find((row) => clean(row && row.id) === wanted);
        if (!item) {
          return;
        }
        pdfState.agentBackMode = "word";
        openPdfAgentPopup(preserveQuestionText(item.answer_vi || item.vietnamese || item.text || "No saved answer."), {
          loading: false,
          footnote: `${clean(item.word || "Word Agent")} | ${clean(item.username || "shared")} | ${clean(item.created_at || "")}`,
        });
        setPdfAgentHistoryBackVisible(true);
      };

      const renderPdfWordAgentHistoryPopup = () => {
        const rows = (Array.isArray(pdfState.wordAgentHistory) ? pdfState.wordAgentHistory : [])
          .filter((item) => item && typeof item === "object");
        pdfState.agentBackMode = "word";
        setPdfAgentHistoryBackVisible(false);
        if (!rows.length) {
          setPdfAgentPopupHtml('<div class="ft-pdf-agent-history-empty">No shared Word Agent history for this word yet.</div>', {
            loading: false,
            footnote: "Shared Word Agent history",
          });
          return;
        }
        const term = clean(rows[0] && rows[0].word) || "this word";
        const html = `<div class="ft-pdf-agent-history-list">${rows.map((item) => {
          const title = escapeHtml(clean(item.word || term));
          const user = escapeHtml(clean(item.username || "shared"));
          const meta = escapeHtml(clean(item.created_at || ""));
          const preview = escapeHtml(clean(item.answer_vi || item.vietnamese || item.text || "").slice(0, 300));
          const id = escapeHtml(clean(item.id || ""));
          return `<button class="ft-pdf-agent-history-row" type="button" data-pdf-action="showWordAgentHistory" data-history-id="${id}">
            <span class="ft-pdf-agent-history-title">${title}</span>
            <span class="ft-pdf-agent-history-meta">${user} | ${meta}</span>
            <span class="ft-pdf-agent-history-preview">${preview}</span>
          </button>`;
        }).join("")}</div>`;
        setPdfAgentPopupHtml(html, {
          loading: false,
          footnote: `${rows.length} shared answer${rows.length === 1 ? "" : "s"} about ${term}`,
        });
      };

      const openPdfWordAgentHistoryPopup = async (index = 0) => {
        const payload = pdfWordAgentPayload(index);
        if (!payload) {
          setPdfStatus("Click a word or phrase first.", true);
          return;
        }
        pdfState.agentBackMode = "word";
        setPdfAgentPopupHtml('<div class="ft-pdf-agent-history-empty">Loading shared Word Agent history...</div>', {
          loading: true,
          footnote: payload.word,
        });
        try {
          const result = await fetchAuthJson(`/word-agent/history?word=${encodeURIComponent(payload.word)}&limit=120`);
          pdfState.wordAgentHistory = Array.isArray(result.payload && result.payload.history) ? result.payload.history : [];
          renderPdfWordAgentHistoryPopup();
        } catch (error) {
          const message = escapeHtml(error && error.message ? error.message : "Could not load shared Word Agent history.");
          setPdfAgentPopupHtml(`<div class="ft-pdf-agent-history-empty">${message}</div>`, {
            loading: false,
            footnote: "History failed",
          });
        }
      };

      const askPdfWordAgent = async (index = 0) => {
        const payload = pdfWordAgentPayload(index);
        if (!payload) {
          setPdfStatus("Click a word or phrase first.", true);
          return;
        }
        pdfState.agentBackMode = "word";
        openPdfAgentPopup(`Ghost Word Agent is studying "${payload.word}"...`, {
          loading: true,
          footnote: "Usage, contexts, and examples",
        });
        setPdfStatus("Ghost Word Agent is thinking...");
        try {
          const result = await fetchAuthJson("/word-agent/ask", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          const answer = preserveQuestionText(result.payload && (result.payload.answer_vi || result.payload.answer || ""));
          if (result.payload && result.payload.entry) {
            pdfState.wordAgentHistory = [result.payload.entry].concat(Array.isArray(result.payload.history) ? result.payload.history : []);
            const latestKey = pdfWordKey(result.payload.entry.word || result.payload.entry.surface || payload.word);
            if (latestKey) {
              if (!pdfState.wordAgentLatestByKey || typeof pdfState.wordAgentLatestByKey !== "object") {
                pdfState.wordAgentLatestByKey = {};
              }
              pdfState.wordAgentLatestByKey[latestKey] = result.payload.entry;
              updatePdfWordAgentSharedPanels(latestKey);
            }
          }
          openPdfAgentPopup(answer || "Ghost Word Agent returned no explanation.", {
            loading: false,
            footnote: `${payload.word}${result.payload && result.payload.model ? ` | ${result.payload.model}` : ""}`,
          });
          setPdfAgentHistoryBackVisible(false);
          setPdfStatus("Ghost Word Agent explanation is ready.");
        } catch (error) {
          const message = error && error.message ? error.message : "Ghost Word Agent could not answer now.";
          openPdfAgentPopup(message, {
            loading: false,
            footnote: "Request failed",
          });
          setPdfStatus(message, true);
        }
      };

      const askPdfAgent = async () => {
        const exploreText = pdfExploreText();
        if (!exploreText) {
          setPdfStatus("Add Text to Explore before asking Ghost AI.", true);
          return;
        }
        const prompt = clean(pdfEls && pdfEls.askInput ? pdfEls.askInput.value : "") || "Explain this Ghost Eye text for me.";
        openPdfAgentPopup("Ghost Eye Agent is reading the text and preparing a Vietnamese explanation...", {
          loading: true,
          footnote: `${pdfState.mode === "picture" ? "Image" : "Page"} ${pdfState.page || 1} | Vietnamese explanation`,
        });
        setPdfStatus("Ghost Eye Agent is thinking...");
        try {
          const { payload } = await fetchAuthJson("/pdf/agent-explain?client_source=pdf_agent_explain", {
            method: "POST",
            body: JSON.stringify({
              question: prompt,
              text: exploreText,
              page: pdfState.page,
              title: pdfState.title || pdfState.name || "PDF",
              path: pdfState.path || "",
            }),
          });
          const answer = preserveQuestionText(payload && (payload.answer_vi || payload.answer || payload.text || ""));
          if (payload && payload.history_entry) {
            pdfState.agentHistory = pdfAgentHistoryRows([payload.history_entry, ...(pdfState.agentHistory || [])]);
          }
          openPdfAgentPopup(answer || "Ghost Eye Agent returned no explanation.", {
            loading: false,
            footnote: `${pdfState.mode === "picture" ? "Image" : "Page"} ${pdfState.page || 1}${payload && payload.model ? ` | ${payload.model}` : ""}`,
          });
          setPdfStatus("Ghost Eye Agent explanation is ready.");
        } catch (error) {
          const message = error && error.message ? error.message : "Ghost Eye Agent could not answer now.";
          openPdfAgentPopup(message, {
            loading: false,
            footnote: "Request failed",
          });
          setPdfStatus(message, true);
        }
      };

      // Added 2026-07-05: lets the PDF/Picture loading overlay paint before slow first-open metadata or render work.
      const waitForPdfOpenLoadingPaint = async (message = "") => {
        if (!pdfEls || !pdfEls.root) {
          return;
        }
        setPdfPageRendering(true, clean(message || "") || "Preparing page...");
        if (typeof updatePdfChrome === "function") {
          updatePdfChrome();
        }
        await new Promise((resolve) => window.requestAnimationFrame(() => resolve()));
        await new Promise((resolve) => window.setTimeout(resolve, 0));
      };

      const enterPdfServerFile = async (entry = {}, options = {}) => {
        const filePath = serverLearningPathForEntry(entry) || normalizeServerPathValue(entry.path || entry.file || entry.name || "");
        if (!filePath) {
          throw new Error("Missing PDF path.");
        }
        // Keep the link location for navigation/focus while the canonical path serves bytes/state.
        const displayPath = normalizeServerPathValue(entry.display_path || entry.displayPath || entry.path || filePath);
        const linkedPath = normalizeServerPathValue(entry.linked_path || entry.linkedPath || (displayPath !== filePath ? displayPath : ""));
        requestAutoFullscreenForSpaceOpen();
        const requestedPdfPage = Math.max(0, Math.floor(Number(options.page || 0) || 0));
        const forceRequestedPdfPage = requestedPdfPage > 0 && options.forcePage === true;
        const openNavigationSerial = pdfPageNavigationSerial;
        const localPdfProgress = readPdfLocalProgress(filePath);
        let restoredPdfProgress = localPdfProgress;
        hideActiveLessonSurfaceForLoad(`Opening ${entry.name || "PDF"}...`);
        ensurePdfModeElements();
        pdfModeActive = true;
        if (typeof syncPdfAdminUserControls === "function") {
          syncPdfAdminUserControls();
        }
        pdfAudioInsertActive = false;
        pdfAudioMarkerMoveId = "";
        pdfAudioMarkerDrag = null;
        pdfAudioMarkerEditingId = "";
        pdfAudioPopoverMode = "audio";
        pdfAudioPopoverSnapshot = "";
        pdfAudioPopoverSaving = false;
        pdfAudioPopoverDrag = null;
        pdfAudioMicCtrlCandidate = false;
        pdfAudioMarkers = [];
        pdfAudioMarkerCache = {};
        pdfAudioMarkerLoadToken += 1;
        stopPdfSharedAudioPlayback();
        closePdfSharedAudioPopover({ silent: true });
        if (pdfEls && pdfEls.audioFile) {
          pdfEls.audioFile.value = "";
        }
        document.documentElement.classList.add("ft-space-pdf-mode");
        loadPdfCompactToolbarSettings();
        if (loadGate) {
          loadGate.classList.add("is-hidden");
        }
        if (pdfEls.root) {
          pdfEls.root.classList.remove("is-hidden");
          pdfEls.root.setAttribute("aria-hidden", "false");
        }
        clearPdfRenderedImage();
        setPdfPageRendering(true, "Loading PDF metadata...");
        pdfState.mode = "pdf";
        pdfState.path = filePath;
        pdfState.lessonId = clean(entry.lesson_id || entry.lessonId || "");
        pdfState.lessonHandle = "";
        pdfState.documentId = clean(entry.document_id || entry.documentId || "");
        const pdfLessonDescriptorPromise = openPdfLessonDescriptor(filePath, entry);
        pdfState.name = entry.name || filePath.split("/").pop() || "PDF";
        pdfState.title = pdfState.name.replace(/\.pdf$/i, "");
        pdfState.page = forceRequestedPdfPage ? requestedPdfPage : Math.max(1, Number(localPdfProgress.page || 1) || 1);
        pdfState.pinnedPages = Array.isArray(localPdfProgress.pinnedPages) ? localPdfProgress.pinnedPages.slice() : localPdfProgress.state && Array.isArray(localPdfProgress.state.pinnedPages) ? localPdfProgress.state.pinnedPages.slice() : localPdfProgress.pinnedPage ? [localPdfProgress.pinnedPage] : localPdfProgress.state && localPdfProgress.state.pinnedPage ? [localPdfProgress.state.pinnedPage] : [];
        pdfState.pinnedPagesUpdatedAt = clean(localPdfProgress.pinnedPagesUpdatedAt || (localPdfProgress.state && localPdfProgress.state.pinnedPagesUpdatedAt) || "");
        pdfState.pages = 1;
        pdfState.scale = 2.4;
        pdfState.viewZoom = Math.max(0.45, Math.min(2.8, Number(localPdfProgress.state && localPdfProgress.state.viewZoom || 1) || 1));
        pdfState.baseDisplayWidth = 0;
        pdfState.pagePointWidth = 0;
        pdfState.pagePointHeight = 0;
        pdfState.hasTextLayer = false;
        pdfState.tesseractReady = false;
        pdfState.selection = null;
        pdfState.ocrText = "";
        pdfState.ocrRawText = "";
        pdfState.ocrFilteredText = "";
        pdfState.ocrViewMode = "raw";
        pdfState.translation = "";
        pdfState.translationCache = {};
        pdfState.ghostConsoleFloating = false;
        pdfState.ghostConsolePosition = null;
        pdfState.translationPosition = null;
        pdfState.vocabStats = null;
        pdfState.vocabMission = null;
        pdfState.vocabDetailMap = {};
        pdfState.ghostConsoleVisible = !pdfCompactToolbarEnabled;
        pdfState.ocrTab = "found";
        pdfState.pictureImages = [];
        pdfState.audioMarkers = [];
        resetPdfLocalImageRuntimeState();
        pdfState.unlearnedWords = readPdfUnlearnedBank(filePath);
        pdfState.wordDetailPinned = false;
        pdfState.pinnedWordKey = "";
        resetPdfFloatingPanelsUi();
        loadPdfPinnedRegions();
        loadPdfLocalImageSlots();
        renderPdfUnlearnedButton();
        setPdfGhostConsoleVisible(pdfState.ghostConsoleVisible, { silent: true });
        closePdfUnlearnedPopup();
        closePdfAgentPopup();
        closePdfTranslationPopup();
        hidePdfWordDetail({ force: true });
        setPdfOcrTab("found");
        if (pdfEls.ocrText) {
          pdfEls.ocrText.textContent = "Select a region on the PDF to find text.";
        }
        if (pdfEls.exploreInput) {
          pdfEls.exploreInput.value = "";
        }
        if (pdfEls.translation) {
          pdfEls.translation.textContent = "Vietnamese translation will appear here.";
        }
        syncPdfSharedAudioUi();
        setCurrentLessonSource({
          source: "server",
          path: displayPath,
          lesson_id: clean(entry.lesson_id || entry.file_id || ""),
          file_id: clean(entry.lesson_id || entry.file_id || ""),
          effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || ""),
          link_target: normalizeServerPathValue(entry.link_target || ""),
          linked_path: linkedPath,
          task_owner: clean(entry.task_owner || serverTaskOwnerContext || currentAuthUsername || ""),
          name: pdfState.name,
          title: pdfState.title,
          study: entry.study || null,
        });
        rememberServerFile({
          ...entry,
          path: displayPath,
          display_path: displayPath,
          effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || ""),
          link_target: normalizeServerPathValue(entry.link_target || ""),
          linked_path: linkedPath,
        }, { syncNow: true });
        updateFutureAppRoute("space_pdf", {
          file: displayPath,
          tree: serverParentPathForFile(displayPath),
          process: "space_pdf",
          page: pdfState.page,
          replace: Boolean(options.replaceRoute),
        });
        closeServerBrowser();
        stopServerBrowserAutoRefresh();
        stopServerBrowserManifestPoll();
        scheduleMobileInfiniteMotionSync(120);
        if (typeof loadPdfUiSettings === "function") {
          loadPdfUiSettings();
        }
        setPdfStatus("Loading PDF metadata...");
        await waitForPdfOpenLoadingPaint("Loading PDF metadata...");
        try {
          await pdfLessonDescriptorPromise;
          const query = new URLSearchParams();
          query.set("path", filePath);
          appendPdfLessonIdentityQuery(query, filePath);
          query.set("warm_page", String(pdfState.page || 1));
          query.set("warm_scale", "3.2");
          query.set("defer_render", "1");
          query.set("quick", "1");
          query.set("client_source", "pdf_open_info");
          const { payload } = await fetchAuthJson(`/pdf/info?${query.toString()}`);
          const info = payload && payload.pdf && typeof payload.pdf === "object" ? payload.pdf : {};
          pdfState.pages = Math.max(1, Number(info.pages || 1) || 1);
          pdfState.title = clean(info.title || "") || pdfState.title;
          pdfState.fileEtag = clean(info.file_etag || info.etag || "");
          pdfState.fileMtime = clean(info.mtime || info.file_mtime || "");
          pdfState.size = Math.max(0, Number(info.size || info.bytes || 0) || 0);
          const firstPage = info.first_page && typeof info.first_page === "object" ? info.first_page : {};
          pdfState.pagePointWidth = Math.max(0, Number(firstPage.width || 0) || 0);
          pdfState.pagePointHeight = Math.max(0, Number(firstPage.height || 0) || 0);
          pdfState.hasTextLayer = Boolean(info.has_text_layer || (info.text_layer && info.text_layer.has_text_layer));
          pdfState.tesseractReady = Boolean(info.ghost_eye_ready || clean(info.tesseract_path || ""));
          const pdfInfoIsQuick = Boolean(info.quick);
          if (!forceRequestedPdfPage) {
            await pdfLessonDescriptorPromise;
            const savedProgress = await fetchPdfSavedProgress(filePath);
            if (savedProgress && savedProgress.page) {
              restoredPdfProgress = savedProgress;
              pdfState.page = Math.max(1, Number(savedProgress.page || pdfState.page) || pdfState.page);
              if (savedProgress.state && savedProgress.state.viewZoom) {
                pdfState.viewZoom = Math.max(0.45, Math.min(2.8, Number(savedProgress.state.viewZoom || pdfState.viewZoom) || pdfState.viewZoom));
              }
              pdfState.pinnedPages = normalizedPdfPinnedPages(savedProgress.pinnedPages || (savedProgress.state && savedProgress.state.pinnedPages) || (savedProgress.pinnedPage ? [savedProgress.pinnedPage] : []) || (savedProgress.state && savedProgress.state.pinnedPage ? [savedProgress.state.pinnedPage] : []) || pdfState.pinnedPages || []);
              pdfState.pinnedPagesUpdatedAt = clean(savedProgress.pinnedPagesUpdatedAt || (savedProgress.state && savedProgress.state.pinnedPagesUpdatedAt) || pdfState.pinnedPagesUpdatedAt || "");
            }
          }
          pdfState.page = pdfInfoIsQuick ? Math.max(1, Math.floor(Number(pdfState.page || 1) || 1)) : Math.max(1, Math.min(pdfState.pages, pdfState.page));
          pdfState.pinnedPages = normalizedPdfPinnedPages(pdfState.pinnedPages || []);
          pdfState.scale = pdfPreferredRenderScale();
          const pdfFileBytes = Math.max(0, Number(pdfState.size || pdfState.bytes || info.size || info.bytes || 0) || 0);
          // Updated 2026-07-22: large PDFs also populate the shared browser chunk cache after first paint.
          const shouldWarmSourceFile = pdfFileBytes > 0;
          if (pdfEls.ocrMeta) {
            const textLayerLabel = pdfState.hasTextLayer ? "Digital source" : "Image source";
            const eyeLabel = pdfState.tesseractReady ? "Ghost Eye ready" : "Ghost Eye limited";
            pdfEls.ocrMeta.textContent = `${textLayerLabel} | ${eyeLabel}`;
          }
          setPdfStatus("Opening PDF page cache...");
          updatePdfChrome();
          updateFutureAppRoute("space_pdf", {
            file: displayPath,
            tree: serverParentPathForFile(displayPath),
            process: "space_pdf",
            page: pdfState.page,
            replace: true,
          });
          if (typeof recordPdfPageVisit === "function") {
            recordPdfPageVisit(pdfState.page, { deferSave: true });
          }
          await renderPdfPage();
          if (shouldWarmSourceFile && typeof warmPdfSourceFileCache === "function") {
            void warmPdfSourceFileCache(info, { trackProgress: true }).then((sourceWarmResult) => {
              if (!sourceWarmResult || !sourceWarmResult.bytes) {
                return;
              }
              if (pdfModeActive && pdfState.mode === "pdf" && normalizeServerPathValue(pdfState.path || "") === filePath) {
                prefetchPdfNeighborPages();
              }
            }).catch((error) => {
              if (window && window.console && typeof window.console.debug === "function") {
                window.console.debug("[Future PDF] Background PDF source warm skipped", error);
              }
            });
          }
          if (pdfModeActive && pdfState.mode === "pdf" && normalizeServerPathValue(pdfState.path || "") === filePath) {
            prefetchPdfNeighborPages();
          }
          if (restoredPdfProgress && Math.max(1, Number(restoredPdfProgress.page || 1) || 1) === pdfState.page) {
            restorePdfGhostProgressState(restoredPdfProgress, { silent: true });
          }
          if (openNavigationSerial === pdfPageNavigationSerial) {
            schedulePdfProgressSave(800, {
              source: "pdf_open_restore",
              uiAction: "pdf.open_restore",
              trigger: "open",
              retry: 0,
            });
          }
        } catch (error) {
          setPdfPageRendering(false);
          setPdfStatus(error && error.message ? error.message : "Could not open PDF.", true);
        }
      };

      const enterPictureServerFile = async (entry = {}, options = {}) => {
        const filePath = serverLearningPathForEntry(entry) || normalizeServerPathValue(entry.path || entry.file || entry.name || "");
        if (!filePath) {
          throw new Error("Missing picture path.");
        }
        // Keep the link location for navigation/focus while the canonical path serves bytes/state.
        const displayPath = normalizeServerPathValue(entry.display_path || entry.displayPath || entry.path || filePath);
        const linkedPath = normalizeServerPathValue(entry.linked_path || entry.linkedPath || (displayPath !== filePath ? displayPath : ""));
        requestAutoFullscreenForSpaceOpen();
        const requestedPage = Math.max(0, Math.floor(Number(options.page || 0) || 0));
        const forceRequestedPage = requestedPage > 0 && options.forcePage === true;
        const openNavigationSerial = pdfPageNavigationSerial;
        const localPdfProgress = readPdfLocalProgress(filePath);
        let restoredPictureProgress = localPdfProgress;
        hideActiveLessonSurfaceForLoad(`Opening ${entry.name || "picture"}...`);
        ensurePdfModeElements();
        pdfModeActive = true;
        if (typeof syncPdfAdminUserControls === "function") {
          syncPdfAdminUserControls();
        }
        pdfAudioInsertActive = false;
        pdfAudioMarkerMoveId = "";
        pdfAudioMarkerDrag = null;
        pdfAudioMarkerEditingId = "";
        pdfAudioPopoverMode = "audio";
        pdfAudioPopoverSnapshot = "";
        pdfAudioPopoverSaving = false;
        pdfAudioPopoverDrag = null;
        pdfAudioMicCtrlCandidate = false;
        pdfAudioMarkers = [];
        pdfAudioMarkerCache = {};
        pdfAudioMarkerLoadToken += 1;
        stopPdfSharedAudioPlayback();
        closePdfSharedAudioPopover({ silent: true });
        if (pdfEls && pdfEls.audioFile) {
          pdfEls.audioFile.value = "";
        }
        document.documentElement.classList.add("ft-space-pdf-mode");
        loadPdfCompactToolbarSettings();
        if (loadGate) {
          loadGate.classList.add("is-hidden");
        }
        if (pdfEls.root) {
          pdfEls.root.classList.remove("is-hidden");
          pdfEls.root.setAttribute("aria-hidden", "false");
        }
        clearPdfRenderedImage();
        setPdfPageRendering(true, "Loading picture folder...");
        pdfState.mode = "picture";
        pdfState.path = filePath;
        pdfState.lessonId = clean(entry.lesson_id || entry.lessonId || "");
        pdfState.lessonHandle = "";
        pdfState.documentId = clean(entry.document_id || entry.documentId || "");
        const pictureLessonDescriptorPromise = openPdfLessonDescriptor(filePath, entry);
        pdfState.name = entry.name || filePath.split("/").pop() || "Picture";
        pdfState.title = typeof futureFriendlyDisplayName === "function"
          ? futureFriendlyDisplayName(pdfState.name)
          : pdfState.name.replace(/\.(png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i, "");
        pdfState.page = forceRequestedPage ? requestedPage : Math.max(1, Number(localPdfProgress.page || 1) || 1);
        pdfState.pinnedPages = Array.isArray(localPdfProgress.pinnedPages) ? localPdfProgress.pinnedPages.slice() : localPdfProgress.state && Array.isArray(localPdfProgress.state.pinnedPages) ? localPdfProgress.state.pinnedPages.slice() : localPdfProgress.pinnedPage ? [localPdfProgress.pinnedPage] : localPdfProgress.state && localPdfProgress.state.pinnedPage ? [localPdfProgress.state.pinnedPage] : [];
        pdfState.pinnedPagesUpdatedAt = clean(localPdfProgress.pinnedPagesUpdatedAt || (localPdfProgress.state && localPdfProgress.state.pinnedPagesUpdatedAt) || "");
        pdfState.pages = 1;
        pdfState.scale = 2;
        pdfState.viewZoom = Math.max(0.45, Math.min(2.8, Number(localPdfProgress.state && localPdfProgress.state.viewZoom || 1) || 1));
        pdfState.baseDisplayWidth = 0;
        pdfState.pagePointWidth = 0;
        pdfState.pagePointHeight = 0;
        pdfState.hasTextLayer = false;
        pdfState.tesseractReady = false;
        pdfState.selection = null;
        pdfState.ocrText = "";
        pdfState.ocrRawText = "";
        pdfState.ocrFilteredText = "";
        pdfState.ocrViewMode = "raw";
        pdfState.translation = "";
        pdfState.translationCache = {};
        pdfState.ghostConsoleFloating = false;
        pdfState.ghostConsolePosition = null;
        pdfState.translationPosition = null;
        pdfState.vocabStats = null;
        pdfState.vocabMission = null;
        pdfState.vocabDetailMap = {};
        pdfState.ghostConsoleVisible = !pdfCompactToolbarEnabled;
        pdfState.ocrTab = "found";
        pdfState.pictureImages = [];
        pdfState.audioMarkers = [];
        resetPdfLocalImageRuntimeState();
        pdfState.unlearnedWords = readPdfUnlearnedBank(filePath);
        pdfState.wordDetailPinned = false;
        pdfState.pinnedWordKey = "";
        resetPdfFloatingPanelsUi();
        loadPdfPinnedRegions();
        loadPdfLocalImageSlots();
        renderPdfUnlearnedButton();
        setPdfGhostConsoleVisible(pdfState.ghostConsoleVisible, { silent: true });
        closePdfUnlearnedPopup();
        closePdfAgentPopup();
        closePdfTranslationPopup();
        hidePdfWordDetail({ force: true });
        setPdfOcrTab("found");
        if (pdfEls.ocrText) {
          pdfEls.ocrText.textContent = "Select a region on the picture to find text.";
        }
        if (pdfEls.exploreInput) {
          pdfEls.exploreInput.value = "";
        }
        if (pdfEls.translation) {
          pdfEls.translation.textContent = "Vietnamese translation will appear here.";
        }
        syncPdfSharedAudioUi();
        setCurrentLessonSource({
          source: "server",
          path: displayPath,
          lesson_id: clean(entry.lesson_id || entry.file_id || ""),
          file_id: clean(entry.lesson_id || entry.file_id || ""),
          effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || ""),
          link_target: normalizeServerPathValue(entry.link_target || ""),
          linked_path: linkedPath,
          task_owner: clean(entry.task_owner || serverTaskOwnerContext || currentAuthUsername || ""),
          name: pdfState.name,
          title: pdfState.title,
          study: entry.study || null,
        });
        rememberServerFile({
          ...entry,
          path: displayPath,
          display_path: displayPath,
          effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || ""),
          link_target: normalizeServerPathValue(entry.link_target || ""),
          linked_path: linkedPath,
        }, { syncNow: true });
        updateFutureAppRoute("space_picture", {
          file: displayPath,
          tree: serverParentPathForFile(displayPath),
          process: "space_picture",
          page: pdfState.page,
          replace: Boolean(options.replaceRoute),
        });
        closeServerBrowser();
        stopServerBrowserAutoRefresh();
        stopServerBrowserManifestPoll();
        scheduleMobileInfiniteMotionSync(120);
        if (typeof loadPdfUiSettings === "function") {
          loadPdfUiSettings();
        }
        setPdfStatus("Loading picture folder...");
        await waitForPdfOpenLoadingPaint("Loading picture folder...");
        try {
          await pictureLessonDescriptorPromise;
          const query = new URLSearchParams();
          query.set("path", filePath);
          appendPdfLessonIdentityQuery(query, filePath);
          query.set("client_source", "picture_open_info");
          const { payload } = await fetchAuthJson(`/picture/info?${query.toString()}`);
          const info = payload && payload.picture && typeof payload.picture === "object" ? payload.picture : {};
          pdfState.pages = Math.max(1, Number(info.pages || 1) || 1);
          pdfState.pictureImages = Array.isArray(info.images) ? info.images : [];
          pdfState.title = clean(info.title || "") || pdfState.title;
          pdfState.hasTextLayer = false;
          pdfState.tesseractReady = Boolean(info.ghost_eye_ready);
          const selectedPicturePage = Math.max(1, Number(info.page || 1) || 1);
          if (!forceRequestedPage) {
            await pictureLessonDescriptorPromise;
            const savedProgress = await fetchPdfSavedProgress(filePath);
            if (savedProgress && savedProgress.page) {
              restoredPictureProgress = savedProgress;
              pdfState.page = Math.max(1, Number(savedProgress.page || pdfState.page) || pdfState.page);
              if (savedProgress.state && savedProgress.state.viewZoom) {
                pdfState.viewZoom = Math.max(0.45, Math.min(2.8, Number(savedProgress.state.viewZoom || pdfState.viewZoom) || pdfState.viewZoom));
              }
              pdfState.pinnedPages = normalizedPdfPinnedPages(savedProgress.pinnedPages || (savedProgress.state && savedProgress.state.pinnedPages) || (savedProgress.pinnedPage ? [savedProgress.pinnedPage] : []) || (savedProgress.state && savedProgress.state.pinnedPage ? [savedProgress.state.pinnedPage] : []) || pdfState.pinnedPages || []);
              pdfState.pinnedPagesUpdatedAt = clean(savedProgress.pinnedPagesUpdatedAt || (savedProgress.state && savedProgress.state.pinnedPagesUpdatedAt) || pdfState.pinnedPagesUpdatedAt || "");
            } else {
              pdfState.page = selectedPicturePage;
            }
          }
          pdfState.page = Math.max(1, Math.min(pdfState.pages, pdfState.page));
          pdfState.pinnedPages = normalizedPdfPinnedPages(pdfState.pinnedPages || []);
          if (pdfEls.ocrMeta) {
            pdfEls.ocrMeta.textContent = `${pdfState.pages} image${pdfState.pages === 1 ? "" : "s"} | ${pdfState.tesseractReady ? "Ghost Eye ready" : "Ghost Eye limited"}`;
          }
          updatePdfChrome();
          updateFutureAppRoute("space_picture", {
            file: displayPath,
            tree: serverParentPathForFile(displayPath),
            process: "space_picture",
            page: pdfState.page,
            replace: true,
          });
          if (typeof recordPdfPageVisit === "function") {
            recordPdfPageVisit(pdfState.page, { deferSave: true });
          }
          await renderPdfPage();
          if (restoredPictureProgress && Math.max(1, Number(restoredPictureProgress.page || 1) || 1) === pdfState.page) {
            restorePdfGhostProgressState(restoredPictureProgress, { silent: true });
          }
          if (openNavigationSerial === pdfPageNavigationSerial) {
            schedulePdfProgressSave(800, {
              source: "picture_open_restore",
              uiAction: "picture.open_restore",
              trigger: "open",
              retry: 0,
            });
          }
        } catch (error) {
          setPdfPageRendering(false);
          setPdfStatus(error && error.message ? error.message : "Could not open picture.", true);
        }
      };

      const reloadPdfCurrentDocumentForViewer = async (options = {}) => {
        if (!pdfModeActive || !pdfState || !pdfState.path) {
          return false;
        }
        const source = currentLessonSource && typeof currentLessonSource === "object" ? currentLessonSource : {};
        const entry = {
          path: pdfState.path,
          name: pdfState.name || pdfState.title || pdfState.path.split("/").pop() || "",
          effective_path: normalizeServerPathValue(source.effective_path || source.link_target || ""),
          link_target: normalizeServerPathValue(source.link_target || ""),
          study: source.study || null,
        };
        if (options.statusMessage) {
          setPdfStatus(options.statusMessage);
        }
        if (pdfState.mode === "picture") {
          await enterPictureServerFile(entry, { replaceRoute: true });
        } else {
          await enterPdfServerFile(entry, { replaceRoute: true });
        }
        return true;
      };

      function requestAutoFullscreenForSpaceOpen() {
        if (document.fullscreenElement || !document.documentElement || !document.documentElement.requestFullscreen) {
          return;
        }
        try {
          const request = document.documentElement.requestFullscreen({ navigationUI: "hide" });
          if (request && typeof request.then === "function") {
            request.then(() => {
              if (startFullscreenGate) {
                startFullscreenGate.classList.add("is-hidden");
              }
            }).catch(() => {});
          }
        } catch (_error) {
        }
      }

      // Added 2026-07-02: lets Lesson Vault/task "Let's go" honor an explicit PDF/Picture resume page from row metadata.
      const pdfResumePageFromLessonEntry = (entry = {}) => {
        const filePath = normalizeServerPathValue(entry.path || entry.effective_path || entry.link_target || entry.linked_path || "");
        const seen = new Set();
        const pageKeys = new Set([
          "page",
          "currentPage",
          "current_page",
          "pdfPage",
          "pdf_page",
          "picturePage",
          "picture_page",
          "lastPage",
          "last_page",
          "resumePage",
          "resume_page",
        ]);
        const nodeKeys = new Set(["nodeIndex", "node_index", "currentIndex", "current_index"]);
        const textKeys = new Set(["progress_text", "progressText", "text", "label", "status", "title", "message"]);
        const parsePositiveInt = (value) => {
          const number = Math.floor(Number(value));
          return Number.isFinite(number) && number > 0 ? number : 0;
        };
        const parseTextPage = (value = "") => {
          const text = clean(value || "");
          if (!text) {
            return 0;
          }
          const labeled = text.match(/\b(?:page|trang)\s*[:#-]?\s*(\d{1,5})\b/i);
          if (labeled) {
            return parsePositiveInt(labeled[1]);
          }
          const fraction = text.match(/\b(\d{1,5})\s*[\/\u2044\u2215\\|]\s*(\d{1,5})\b/);
          if (fraction) {
            return parsePositiveInt(fraction[1]);
          }
          return 0;
        };
        const visit = (value, key = "", depth = 0) => {
          if (value == null || depth > 5) {
            return 0;
          }
          if (typeof value === "number") {
            return pageKeys.has(key) ? parsePositiveInt(value) : 0;
          }
          if (typeof value === "string") {
            if (pageKeys.has(key)) {
              return parsePositiveInt(value) || parseTextPage(value);
            }
            return textKeys.has(key) ? parseTextPage(value) : 0;
          }
          if (typeof value !== "object") {
            return 0;
          }
          if (seen.has(value)) {
            return 0;
          }
          seen.add(value);
          for (const [childKey, childValue] of Object.entries(value)) {
            const direct = pageKeys.has(childKey) ? (parsePositiveInt(childValue) || parseTextPage(childValue)) : 0;
            if (direct) {
              return direct;
            }
          }
          for (const [childKey, childValue] of Object.entries(value)) {
            if (nodeKeys.has(childKey)) {
              const node = Math.floor(Number(childValue));
              if (Number.isFinite(node) && node >= 0) {
                return node + 1;
              }
            }
          }
          for (const [childKey, childValue] of Object.entries(value)) {
            const nested = visit(childValue, childKey, depth + 1);
            if (nested) {
              return nested;
            }
          }
          return 0;
        };
        const serverPage = visit(entry, "", 0);
        if (serverPage > 0) {
          return serverPage;
        }
        if (filePath && typeof readPdfLocalProgress === "function") {
          const localProgress = readPdfLocalProgress(filePath);
          const localPage = Math.max(1, Math.floor(Number(localProgress && localProgress.page) || 0));
          if (localPage > 0) {
            return localPage;
          }
        }
        return 0;
      };

      const loadServerLessonFile = async (entry) => {
        if (!entry || !entry.path || serverBrowserBusy) {
          return;
        }
        const learningEntry = serverLearningEntry(entry);
        const learningPath = serverLearningPathForEntry(entry) || entry.path;
        const displayPath = normalizeServerPathValue(entry.path || learningPath);
        const openPath = normalizeServerPathValue(learningPath || displayPath);
        const clickedPath = normalizeServerPathValue(displayPath || entry.path || openPath);
        const linkedPath = displayPath && openPath && normalizeTaskPath(displayPath) !== normalizeTaskPath(openPath) ? displayPath : "";
        const entryExtension = clean(entry.extension || (String(openPath || entry.path || "").match(/\.[^.\\/]+$/) || [""])[0]).toLowerCase();
        const entryOpenOwnsLastFileSync = entryExtension === ".pdf" || isSpacePictureExtension(entryExtension);
        requestAutoFullscreenForSpaceOpen();
        if (serverLessonProgressPrefetchTimer) {
          window.clearTimeout(serverLessonProgressPrefetchTimer);
          serverLessonProgressPrefetchTimer = 0;
        }
        serverBrowserBusy = true;
        setSelectedTaskPath(clickedPath || openPath || entry.path);
        if (!entryOpenOwnsLastFileSync) {
          rememberServerFile({
            ...entry,
            path: clickedPath || displayPath || entry.path,
            sourcePath: displayPath || normalizeServerPathValue(entry.path || ""),
            effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || openPath || learningPath || ""),
            link_target: normalizeServerPathValue(entry.link_target || ""),
            linked_path: linkedPath || normalizeServerPathValue(entry.linked_path || ""),
          }, { syncNow: true });
        }
        pendingSpaceWAfterVocabulary = null;
        currentVocabularyMission = null;
        vocabPreflightState = null;
        forgetVocabPreflightDecisionForPath(displayPath || learningPath);
        hideActiveLessonSurfaceForLoad(`Dang nap ${entry.name || "goi bai hoc"} tu server...`);
        setServerBrowserLoading("Dang tai file...");
        let progressPromise = null;
        try {
          if (entryExtension === ".pdf") {
            const resumePage = pdfResumePageFromLessonEntry(entry);
            await enterPdfServerFile({
              ...entry,
              path: clickedPath || entry.path,
              effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || openPath || ""),
              link_target: normalizeServerPathValue(entry.link_target || ""),
              linked_path: linkedPath || normalizeServerPathValue(entry.linked_path || ""),
            }, resumePage ? { page: resumePage, forcePage: true } : {});
            return;
          }
          if (isSpacePictureExtension(entryExtension)) {
            const resumePage = pdfResumePageFromLessonEntry(entry);
            await enterPictureServerFile({
              ...entry,
              path: clickedPath || entry.path,
              effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || openPath || ""),
              link_target: normalizeServerPathValue(entry.link_target || ""),
              linked_path: linkedPath || normalizeServerPathValue(entry.linked_path || ""),
            }, resumePage ? { page: resumePage, forcePage: true } : {});
            return;
          }
          const result = await fetchServerText(`/server-data/file?path=${encodeURIComponent(openPath || entry.path)}`);
          const text = String(result.text || "").replace(/^\uFEFF/, "");
          if (!text.trim()) {
            const emptyError = new Error("Immediate Mission pack is no longer available.");
            emptyError.immediateEmpty = serverPathIsImmediateMission(openPath || entry.path || displayPath || learningPath);
            throw emptyError;
          }
          setLoadStatus("Dang giai nen va kiem tra bai hoc...");
          const payload = await decodeFuturePayload(text);
          setCurrentLessonSource({
            source: "server",
            path: clickedPath || displayPath || openPath || learningPath,
            lesson_id: clean(entry.lesson_id || entry.file_id || ""),
            file_id: clean(entry.lesson_id || entry.file_id || ""),
            effective_path: normalizeServerPathValue(entry.effective_path || entry.link_target || openPath || learningPath || ""),
            link_target: normalizeServerPathValue(entry.link_target || ""),
            linked_path: linkedPath || normalizeServerPathValue(entry.linked_path || ""),
            task_owner: clean(entry.task_owner || serverTaskOwnerContext || currentAuthUsername || ""),
            name: entry.name || entry.path,
            study: entry.study || null,
          }, payload);
          updateFutureAppRoute(routeForLessonPayload(payload), {
            file: clickedPath || displayPath || openPath || learningPath,
            tree: serverParentPathForFile(clickedPath || displayPath || openPath || learningPath),
            process: routeForLessonPayload(payload),
          });
          closeServerBrowser();
          if (shouldAutoStartLoadedFileInPopup() && (isVocabularyPayload(payload) || isQuestionPayload(payload))) {
            setLoadStatus("Da nap file tu server. Dang mo giao dien hoc...");
            await delay(20);
            loadLessonPayload(payload);
          } else {
            progressPromise = fetchServerProgressForEntry({ ...learningEntry, path: openPath || learningPath || displayPath }).catch((error) => ({
              space: serverLessonProgressSpaceForPath(openPath || displayPath || learningPath, entry.extension),
              payload: {},
              failed: true,
              error,
            }));
            prepareLessonPayloadForGate(payload, { serverProgressPromise: progressPromise });
          }
        } catch (error) {
          console.error("FTG load server Space_W failed", error);
          pendingVocabularyPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          resetSpaceWCache();
          if (error && error.immediateEmpty) {
            setLoadStatus("Immediate Mission pack da hoc xong hoac da duoc don. Dang cap nhat danh sach...", false);
          } else {
            setLoadStatus(error && error.message ? error.message : "Khong nap duoc file tren server.", true);
          }
          await loadServerDataPath(serverBrowserPath, true, serverTaskOwnerContext);
        } finally {
          serverBrowserBusy = false;
        }
      };

      // Added 2026-06-30: reads visible x/y progress from any chip text variant on a Lesson Vault row.
      function lessonVaultProgressTextFromNode(node = null) {
        if (!node) {
          return "";
        }
        const candidates = [];
        const pushText = (value = "") => {
          const text = clean(value || "");
          if (text && !candidates.includes(text)) {
            candidates.push(text);
          }
        };
        const pushNodeText = (target = null) => {
          if (!target) {
            return;
          }
          pushText(target.innerText || "");
          pushText(target.textContent || "");
          if (target.getAttribute) {
            pushText(target.getAttribute("aria-label") || "");
            pushText(target.getAttribute("title") || "");
            pushText(target.getAttribute("data-progress") || "");
            pushText(target.getAttribute("data-progress-text") || "");
            pushText(target.getAttribute("data-value") || "");
          }
          if (target.dataset) {
            Object.values(target.dataset).forEach(pushText);
          }
        };
        pushNodeText(node);
        if (node.querySelectorAll) {
          Array.from(node.querySelectorAll(".ft-server-chip, .ft-server-chip-row, .ft-task-hover-chip, .ft-lesson-progress-value, [aria-label], [title], [data-progress], [data-progress-text], [data-value]"))
            .slice(0, 120)
            .forEach(pushNodeText);
        }
        for (const text of candidates) {
          const match = text.match(/(\d+)\s*[\/\u2044\u2215\\|]\s*(\d+)/);
          if (match) {
            return `${match[1]}/${match[2]}`;
          }
        }
        return "";
      }

      // Added 2026-06-30: keeps manual Space_V chart sync debuggable when the visible chip cannot be parsed.
      function lessonVaultProgressDebugTextFromNode(node = null) {
        if (!node) {
          return "";
        }
        const text = clean((node.innerText || node.textContent || "").replace(/\s+/g, " "));
        return text.length > 110 ? `${text.slice(0, 110)}...` : text;
      }

      // Added 2026-06-30: builds the vault chart from the same progress text/percent that feeds file chips.
      function lessonVaultProgressFromStudyChipFields(study = {}, entry = {}) {
        const source = study && typeof study === "object" ? study : {};
        const progress = source.progress && typeof source.progress === "object" ? source.progress : {};
        const progressText = clean(source.progress_text || source.progressText || progress.text || "");
        const match = progressText.match(/(\d+)\s*[\/\u2044\u2215\\|]\s*(\d+)/);
        if (!match) {
          return null;
        }
        const done = Math.max(0, Math.floor(Number(match[1]) || 0));
        const total = Math.max(0, Math.floor(Number(match[2]) || 0));
        if (!total || done >= total) {
          return null;
        }
        const percentSource = source.progress_percent ?? source.progressPercent ?? progress.percent;
        const percent = Math.max(0, Math.min(99, Math.round(Number(percentSource ?? ((done / total) * 100)) || 0)));
        const extension = clean(entry && entry.extension).toLowerCase();
        const entryStudy = entry && entry.study && typeof entry.study === "object" ? entry.study : {};
        const learnedBefore = typeof lessonStudyCompletedRunCount === "function"
          ? lessonStudyCompletedRunCount(entryStudy, { includeAdmin: true }) > 0
          : Math.max(0, Math.floor(Number(entryStudy.mine || entryStudy.completed_runs || entryStudy.completedRuns || entryStudy.admin_mine || 0) || 0)) > 0;
        return {
          space: (extension === ".space_v" || extension === ".space_b") ? "Space_V" : clean(progress.space || ""),
          label: learnedBefore ? "Relearn" : ((extension === ".space_v" || extension === ".space_b") ? "Words" : clean(progress.label || "Progress")),
          done,
          total,
          percent,
          text: `${done}/${total}`,
          completed: false,
          in_progress: true,
          activeRun: true,
          previously_completed: learnedBefore || undefined,
          previouslyCompleted: learnedBefore || undefined,
          relearning: learnedBefore || undefined,
          relearnLabel: learnedBefore ? "Relearn" : undefined,
          syncing: Boolean(progress.syncing || progress.pending_sync),
        };
      }

      // Added 2026-07-03: prevents vocabulary/count chips from inventing progress charts without a real active run.
      function lessonVaultChipCanDriveProgressChart(progress = null) {
        return Boolean(progress && typeof progress === "object" && lessonProgressIsActivePartial(progress));
      }

      // Added 2026-07-22: PDF/Picture page totals are structural metadata, never a legacy progress fallback such as 1/1.
      function lessonVaultStructuralPageTotal(study = {}, entry = {}) {
        const extension = clean(entry && entry.extension).toLowerCase();
        if (extension !== ".pdf" && extension !== ".space_pdf" && extension !== ".space_picture" && !isSpacePictureExtension(extension)) {
          return 0;
        }
        const source = study && typeof study === "object" ? study : {};
        return Math.max(
          0,
          Math.floor(Number(source.nodes || entry.nodes || entry.node_count || 0) || 0),
        );
      }

      // Added 2026-07-03: keeps completed Lesson Vault rows at 100% instead of showing a stale Space_V review/autosave partial.
      function lessonVaultCompletedProgressForStudy(study = {}, entry = {}) {
        const source = study && typeof study === "object" ? study : {};
        const mine = typeof lessonStudyCompletedRunCount === "function"
          ? lessonStudyCompletedRunCount(source)
          : Math.max(0, Math.floor(Number(source.mine || source.completed_runs || source.completedRuns || 0) || 0));
        if (!mine) {
          return null;
        }
        const progress = source.progress && typeof source.progress === "object" ? source.progress : {};
        const structuralPageTotal = lessonVaultStructuralPageTotal(source, entry);
        const total = Math.max(
          1,
          structuralPageTotal || Math.floor(Number(progress.total ?? source.nodes ?? entry.nodes ?? entry.node_count ?? 1) || 1),
        );
        const extension = clean(entry && entry.extension).toLowerCase();
        const space = clean(progress.space || serverLessonProgressSpaceForPath(entry.path || "", extension) || "");
        return {
          space,
          label: clean(progress.label || (space === "Space_V" ? "Words" : "Progress")),
          done: total,
          total,
          percent: 100,
          text: `${total}/${total}`,
          completed: true,
          in_progress: false,
          activeRun: false,
          reviewing: false,
          savedAt: clean(progress.savedAt || source.mine_last || source.last || ""),
          updatedAt: clean(progress.updatedAt || source.mine_last || source.last || ""),
        };
      }

      // Added 2026-07-03: separates brand-new 0/x autosave noise from relearning progress on already learned Space_V rows.
      function lessonVaultDisplayProgressForStudy(study = {}, entry = {}, pinnedProgress = null) {
        const source = study && typeof study === "object" ? study : {};
        const learnedBefore = typeof lessonStudyCompletedRunCount === "function"
          ? lessonStudyCompletedRunCount(source) > 0
          : Math.max(0, Math.floor(Number(source.mine || source.completed_runs || source.completedRuns || 0) || 0)) > 0;
        const completionTimestamp = Math.max(
          typeof parseLessonProgressTimestamp === "function"
            ? parseLessonProgressTimestamp(source.mine_last || source.last || "")
            : 0,
          typeof parseLessonProgressTimestamp === "function"
            ? parseLessonProgressTimestamp(source.completedAt || source.completed_at || "")
            : 0,
        );
        const pinnedSource = pinnedProgress && typeof pinnedProgress === "object" ? pinnedProgress : null;
        const sourceProgress = source.progress && typeof source.progress === "object" ? source.progress : null;
        // Added 2026-07-15: trust the newest progress record so stale local pins cannot beat the server login snapshot.
        const progressTimestamp = (progress = null) => {
          const row = progress && typeof progress === "object" ? progress : {};
          if (typeof parseLessonProgressTimestamp === "function") {
            return Math.max(
              parseLessonProgressTimestamp(row.updatedAt || row.updated_at || ""),
              parseLessonProgressTimestamp(row.savedAt || row.saved_at || ""),
            );
          }
          const value = clean(row.updatedAt || row.updated_at || row.savedAt || row.saved_at || "");
          const parsed = value ? Date.parse(value) : 0;
          return Number.isFinite(parsed) ? parsed : 0;
        };
        const sourceActive = lessonProgressIsActivePartial(sourceProgress);
        const pinnedActive = lessonProgressIsActivePartial(pinnedSource);
        const pinnedSpace = clean(pinnedSource && pinnedSource.space);
        const pinnedIsPageProgress = pinnedSpace === "Space_PDF" || pinnedSpace === "Space_Picture";
        const sourceProgressTs = progressTimestamp(sourceProgress);
        const pinnedProgressTs = progressTimestamp(pinnedSource);
        let rawProgress = pinnedActive && pinnedIsPageProgress
          ? pinnedSource
          : sourceActive && pinnedActive
          ? (pinnedProgressTs && (!sourceProgressTs || pinnedProgressTs > sourceProgressTs) ? pinnedSource : sourceProgress)
          : (pinnedActive ? pinnedSource : sourceProgress || pinnedSource);
        const extension = clean(entry && entry.extension).toLowerCase();
        const structuralQuestionTotal = extension === ".space_q"
          ? Math.max(
            0,
            Math.floor(Number(source.total_nodes || source.totalNodes || entry.total_nodes || 0) || 0),
            Math.floor(Number(source.nodes || entry.nodes || 0) || 0) + Math.floor(Number(source.questions || entry.questions || 0) || 0),
          )
          : 0;
        const structuralPageTotal = lessonVaultStructuralPageTotal(source, entry);
        const savedPageTotal = Math.max(0, Math.floor(Number(rawProgress && rawProgress.total || 0) || 0));
        if (rawProgress && structuralPageTotal && structuralPageTotal !== savedPageTotal) {
          const savedDone = Math.max(
            0,
            Math.floor(Number(rawProgress.done ?? rawProgress.node_done ?? rawProgress.nodeDone ?? 0) || 0),
          );
          const done = Math.max(0, Math.min(structuralPageTotal, savedDone));
          rawProgress = {
            ...rawProgress,
            done,
            total: structuralPageTotal,
            percent: structuralPageTotal ? Math.round((done / structuralPageTotal) * 100) : 0,
            text: `${done}/${structuralPageTotal}`,
            node_done: done,
            node_total: structuralPageTotal,
            nodes_text: `${done}/${structuralPageTotal}`,
          };
        }
        const savedQuestionTotal = Math.max(0, Math.floor(Number(rawProgress && rawProgress.total || 0) || 0));
        if (rawProgress && structuralQuestionTotal > savedQuestionTotal) {
          const savedDone = Math.max(0, Math.floor(Number(rawProgress.done || 0) || 0));
          const done = savedQuestionTotal
            ? Math.round(savedDone * structuralQuestionTotal / savedQuestionTotal)
            : savedDone;
          rawProgress = {
            ...rawProgress,
            done: Math.max(0, Math.min(structuralQuestionTotal, done)),
            total: structuralQuestionTotal,
            percent: structuralQuestionTotal ? Math.round((done / structuralQuestionTotal) * 100) : 0,
            text: `${Math.max(0, Math.min(structuralQuestionTotal, done))}/${structuralQuestionTotal}`,
          };
        }
        if (rawProgress && lessonProgressIsActivePartial(rawProgress)) {
          const done = Math.max(0, Math.floor(Number(rawProgress.done ?? rawProgress.node_done ?? rawProgress.nodeDone ?? 0) || 0));
          const progressTimestamp = Math.max(sourceProgressTs, pinnedProgressTs);
          const activeRunId = clean(rawProgress.runId || rawProgress.run_id || "");
          // An identified New Study run owns the current chart, including 0/N.
          // Lifetime completion timestamps only control the Learned chip.
          const staleAfterCompletion = !activeRunId && learnedBefore && completionTimestamp && progressTimestamp && progressTimestamp <= completionTimestamp;
          if ((done > 0 || learnedBefore || activeRunId || rawProgress.activeRun || rawProgress.active_run) && !staleAfterCompletion) {
            return learnedBefore
              ? { ...rawProgress, previously_completed: true, previouslyCompleted: true, relearning: true, relearnLabel: "Relearn" }
              : rawProgress;
          }
          return learnedBefore ? lessonVaultCompletedProgressForStudy(source, entry) : null;
        }
        return learnedBefore ? lessonVaultCompletedProgressForStudy(source, entry) : rawProgress;
      }

      // Added 2026-06-30: shares Shift-click chip-to-chart repair with Lesson Vault Back rendering.
      function syncLessonVaultChartFromChip(paths = [], entry = {}, options = {}) {
        if (!serverListNode) {
          return false;
        }
        const extension = clean(entry && entry.extension).toLowerCase();
        const wantedSpaceClass = (extension === ".space_w")
          ? "is-space-w"
          : ((extension === ".space_v" || extension === ".space_b") ? "is-space-v" : "");
        const wantedPaths = new Set((Array.isArray(paths) ? paths : [paths])
          .map((path) => normalizeTaskPath(normalizeServerPathValue(path || "")))
          .filter(Boolean));
        const directItem = options && options.item && options.item.classList ? options.item : null;
        const candidates = directItem
          ? [directItem]
          : Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file.is-space-v, .ft-server-item.is-file.is-space-w"));
        const row = candidates.find((item) => {
          if (!item || !item.classList) {
            return false;
          }
          if (wantedSpaceClass && !item.classList.contains(wantedSpaceClass)) {
            return false;
          }
          if (!wantedSpaceClass && !item.classList.contains("is-space-v") && !item.classList.contains("is-space-w")) {
            return false;
          }
          if (!wantedPaths.size) {
            return item === directItem;
          }
          const itemPaths = [
            item.dataset.path || "",
            item.dataset.effectivePath || "",
            item.dataset.linkTarget || "",
            item.dataset.linkedPath || "",
            item.dataset.sourcePath || "",
            item.dataset.originalPath || "",
          ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
          return itemPaths.some((value) => wantedPaths.has(value));
        });
        if (!row) {
          const retryMs = Math.max(0, Number(options.retryMs || 0) || 0);
          if (retryMs) {
            window.setTimeout(() => {
              syncLessonVaultChartFromChip(paths, entry, { ...options, retryMs: 0 });
            }, retryMs);
          }
          return false;
        }
        const chips = row.querySelector(".ft-server-chip-row") || row;
        // Added 2026-07-15: prefer the real study progress record over visible chips; Space_V chips can show Node x/y resume text.
        const fallbackProgress = options && options.progress && typeof options.progress === "object"
          ? options.progress
          : ((entry.study && entry.study.progress && typeof entry.study.progress === "object") ? entry.study.progress : null);
        const pinPaths = wantedPaths.size
          ? Array.from(wantedPaths)
          : [
            row.dataset.path,
            row.dataset.effectivePath,
            row.dataset.linkTarget,
            row.dataset.linkedPath,
            row.dataset.sourcePath,
            row.dataset.originalPath,
          ];
        const activePinnedProgress = typeof lessonVaultProgressPinForPaths === "function"
          ? lessonVaultProgressPinForPaths(pinPaths)
          : (typeof lessonProgressOverrideForPaths === "function" ? lessonProgressOverrideForPaths(pinPaths) : null);
        const displayFallback = (fallbackProgress || activePinnedProgress)
          ? lessonVaultDisplayProgressForStudy(entry.study || {}, entry, activePinnedProgress || fallbackProgress)
          : null;
        const chipText = lessonVaultChipCanDriveProgressChart(displayFallback)
          ? (lessonVaultProgressTextFromNode(chips) || lessonVaultProgressTextFromNode(row))
          : "";
        const progressFromChip = chipText
          ? lessonVaultProgressFromStudyChipFields({ progress_text: chipText }, entry)
          : null;
        const progress = displayFallback || progressFromChip;
        if (!progress) {
          if (options && options.notice && typeof setTopOperationStatus === "function") {
            const debugText = lessonVaultProgressDebugTextFromNode(chips) || lessonVaultProgressDebugTextFromNode(row);
            const label = row.classList.contains("is-space-w") ? "Space_W" : "Space_V";
            setTopOperationStatus(`${label} chart sync needs a progress chip like 4/10.${debugText ? ` Row: ${debugText}` : ""}`, {
              isError: true,
              autoHideMs: 6200,
            });
          }
          return false;
        }
        const iconColumn = row.querySelector(".ft-server-icon-column");
        if (!iconColumn) {
          return false;
        }
        Array.from(iconColumn.children).forEach((child) => {
          if (child && child.classList && child.classList.contains("ft-vault-progress") && !child.classList.contains("ft-vault-progress-admin")) {
            child.remove();
          }
        });
        const progressNode = createLessonProgressNode(entry.study || {}, "ft-vault-progress", { progress });
        if (progressNode) {
          iconColumn.appendChild(progressNode);
          row.classList.add("has-progress");
        }
        setLessonProgressOverride(pinPaths, progress, 300000);
        if (typeof rememberLessonVaultProgressPin === "function") {
          rememberLessonVaultProgressPin(pinPaths, progress, 300000);
        }
        if (options && options.motion) {
          triggerServerWorkspaceMotionBurst(row, null, { source: "select" });
        }
        if (options && options.notice && typeof setTopOperationStatus === "function") {
          const label = row.classList.contains("is-space-w") ? "Space_W" : "Space_V";
          setTopOperationStatus(`${label} chart synced from chip ${progress.text} - ${progress.percent}%.`, {
            working: false,
            progress: 1,
            autoHideMs: 2600,
          });
        }
        return true;
      }

      function syncSpaceVLessonVaultChartFromChip(paths = [], entry = {}, options = {}) {
        return syncLessonVaultChartFromChip(paths, entry, options);
      }

      const renderServerDataList = (payload = {}) => {
        if (!serverListNode) {
          return;
        }
        const timelineStartedAt = browserTimingNow();
        ensureLoginTimelineMetrics();
        if (typeof applyLessonVaultProgressSnapshotToPayload === "function" && !(payload && payload.__ftLessonVaultProgressSnapshotApplied)) {
          payload = applyLessonVaultProgressSnapshotToPayload(payload);
        }
        serverListNode.textContent = "";
        const localCacheOnly = Boolean(payload && payload.local_cache_only);
        disconnectServerVaultVisibilityObserver();
        serverBrowserPath = normalizeServerPathValue(payload.path || "");
        setServerBrowserPathLabel(serverBrowserPath);
        const deferredTaskBoard = Boolean(payload.task_board_deferred);
        const payloadTaskOwner = lessonVaultTaskOwnerForPath(serverBrowserPath, payload.task_owner || "", payload);
        if (payloadTaskOwner && !authUsernameMatches(payload.task_owner || "", payloadTaskOwner)) {
          payload.task_owner = payloadTaskOwner;
        }
        const deferredOwner = clean(payloadTaskOwner || (!payload.admin ? payload.username || "" : ""));
        const deferredSpaceTaskPayload = payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        // Added 2026-07-15: Back/local-cache route can rebuild Space Task from the login/local panel cache without a server GET.
        const cachedTaskPanelRow = deferredOwner && typeof getLessonTaskPanelCacheRow === "function"
          ? getLessonTaskPanelCacheRow(deferredOwner)
          : null;
        const cachedTaskPanelPayload = cachedTaskPanelRow && cachedTaskPanelRow.payload && typeof cachedTaskPanelRow.payload === "object"
          ? cachedTaskPanelRow.payload
          : null;
        const canReuseCurrentTaskPayload = Boolean(
          deferredTaskBoard
          && deferredOwner
          && (
            (currentTaskPayload && authUsernameMatches(deferredOwner, clean(currentTaskPayload.task_owner || "")))
            || (cachedTaskPanelPayload && authUsernameMatches(deferredOwner, clean(cachedTaskPanelPayload.task_owner || "")))
          )
        );
        const reusableTaskPayload = currentTaskPayload && authUsernameMatches(deferredOwner, clean(currentTaskPayload.task_owner || ""))
          ? currentTaskPayload
          : (cachedTaskPanelPayload || currentTaskPayload);
        if (payloadTaskOwner) {
          serverTaskOwnerContext = payloadTaskOwner;
          if (deferredTaskBoard) {
            renderLessonTaskPanel({
              ...(canReuseCurrentTaskPayload ? reusableTaskPayload : {}),
              task_owner: deferredOwner,
              admin: Boolean(payload.admin),
              tasks: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.tasks) ? reusableTaskPayload.tasks : [],
              space_tasks: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.space_tasks) ? reusableTaskPayload.space_tasks : [],
              space_task: canReuseCurrentTaskPayload
                ? {
                  ...(reusableTaskPayload.space_task && typeof reusableTaskPayload.space_task === "object" ? reusableTaskPayload.space_task : {}),
                  ...deferredSpaceTaskPayload,
                  deferred: true,
                }
                : { ...deferredSpaceTaskPayload, deferred: true },
              learning_stats: canReuseCurrentTaskPayload ? reusableTaskPayload.learning_stats || null : null,
              task_notices: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.task_notices) ? reusableTaskPayload.task_notices : [],
            });
          } else {
            renderLessonTaskPanel({ ...payload, task_owner: payloadTaskOwner });
          }
        } else if (!payload.admin && clean(payload.username || "")) {
          serverTaskOwnerContext = clean(payload.username || "");
          if (deferredTaskBoard) {
            renderLessonTaskPanel({
              ...(canReuseCurrentTaskPayload ? reusableTaskPayload : {}),
              task_owner: serverTaskOwnerContext,
              admin: Boolean(payload.admin),
              tasks: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.tasks) ? reusableTaskPayload.tasks : [],
              space_tasks: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.space_tasks) ? reusableTaskPayload.space_tasks : [],
              space_task: canReuseCurrentTaskPayload
                ? {
                  ...(reusableTaskPayload.space_task && typeof reusableTaskPayload.space_task === "object" ? reusableTaskPayload.space_task : {}),
                  ...deferredSpaceTaskPayload,
                  deferred: true,
                }
                : { ...deferredSpaceTaskPayload, deferred: true },
              learning_stats: canReuseCurrentTaskPayload ? reusableTaskPayload.learning_stats || null : null,
              task_notices: canReuseCurrentTaskPayload && Array.isArray(reusableTaskPayload.task_notices) ? reusableTaskPayload.task_notices : [],
            });
          } else {
            renderLessonTaskPanel({ ...payload, task_owner: serverTaskOwnerContext, tasks: Array.isArray(payload.tasks) ? payload.tasks : [] });
          }
        } else {
          renderLessonTaskPanel({ task_owner: "", tasks: [], admin: Boolean(payload.admin) });
        }
        if (typeof window !== "undefined" && typeof window.__ftRecordLoginTimelinePhase === "function") {
          window.__ftRecordLoginTimelinePhase("renderServerDataList", browserTimingNow() - timelineStartedAt);
        }
          const spaceTaskPayload = deferredTaskBoard && canReuseCurrentTaskPayload
            ? {
              ...(currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object" ? currentTaskPayload.space_task : {}),
              ...deferredSpaceTaskPayload,
            }
            : deferredSpaceTaskPayload;
          const currentPreferredTaskFolders = currentTaskPayload
            && currentTaskPayload.space_task
            && Array.isArray(currentTaskPayload.space_task.preferred_folders)
            ? currentTaskPayload.space_task.preferred_folders
            : [];
          const payloadPreferredFoldersAreStale = typeof spaceTaskPayloadIsStaleForOwner === "function"
            ? spaceTaskPayloadIsStaleForOwner(payloadTaskOwner || (!payload.admin ? payload.username || "" : ""), spaceTaskPayload)
            : false;
          const effectivePreferredTaskFolders = Array.isArray(spaceTaskPayload.preferred_folders)
            ? (payloadPreferredFoldersAreStale ? currentPreferredTaskFolders : spaceTaskPayload.preferred_folders)
            : (localCacheOnly ? currentPreferredTaskFolders : []);
          serverBrowserPreferredTaskFolderOwner = clean(payloadTaskOwner || (!payload.admin ? payload.username || "" : ""));
          serverBrowserPreferredTaskFolders = [...effectivePreferredTaskFolders];
        const serverEntryIsAdminRoot = (entry = {}) => {
          if (!payload.admin || !entry || entry.type !== "folder") return false;
          const adminUsername = clean(currentAuthUsername || payload.username || "");
          if (!adminUsername) return false;
          const entryPath = normalizeTaskPath(normalizeServerPathValue(entry.path || ""));
          const entryParts = entryPath.split("/").filter(Boolean);
          if (entryParts.length !== 1) return false;
          const entryTop = clean(entryParts[0] || "");
          const entryName = clean(entry.name || serverFolderDisplayName(entry));
          const entryOwner = clean(entry.owner || "").toLowerCase();
          if (entry.virtual_common || entryPath === "common" || serverPathIsImmediateMissionRoot(entryPath)) {
            return false;
          }
          if (entryOwner === "system-admin" && !authUsernameMatches(entryTop || entryName, adminUsername)) {
            return false;
          }
          return authUsernameMatches(entryTop || entryName, adminUsername) || authUsernameMatches(entryName, adminUsername);
        };
        const serverVaultEntryRank = (entry = {}) => {
          const entryPath = normalizeServerPathValue(entry.path || "");
          if (entry.type === "folder" && (entry.virtual_common || normalizeTaskPath(entryPath) === "common")) {
            return 0;
          }
          if (serverEntryIsAdminRoot(entry)) {
            return 1;
          }
          if (entry.type === "folder" && serverPathIsImmediateMissionRoot(entryPath)) {
            return 2;
          }
          return entry.type === "folder" ? 3 : 4;
        };
        const rawEntries = Array.isArray(payload.entries) ? payload.entries.slice() : [];
        // Updated 2026-07-27: root and user-folder views expose the shared Common root;
        // common/common-child views must not render a nested Common shortcut.
        const payloadPathTop = serverPathTop(payload.path || serverBrowserPath || "");
        const adminTargetOwner = clean(payload.task_owner || "");
        const hasCommonRoot = rawEntries.some((entry) => (
          entry && entry.type === "folder" && (
            Boolean(entry.virtual_common) || normalizeTaskPath(entry.path || "") === "common"
          )
        ));
        // Added 2026-07-29: only admins may see the shared Common shortcut while browsing a learner folder.
        if (payload.admin && currentAuthIsAdmin && adminTargetOwner && (!payloadPathTop || payloadPathTop === adminTargetOwner.toLowerCase()) && !hasCommonRoot) {
          rawEntries.unshift({
            name: "common",
            path: "common",
            type: "folder",
            size: 0,
            modified: 0,
            owner: "shared",
            task_owner: adminTargetOwner,
            virtual_common: true,
          });
        }
        const entries = rawEntries.filter((entry) => {
          if (!entry || entry.type !== "folder") {
            return true;
          }
          const entryPath = normalizeTaskPath(entry.path || "");
          const isCommonFolder = Boolean(
            entry.virtual_common
            || entryPath === "common"
            || entryPath.endsWith("/common")
            || clean(entry.name || "").toLowerCase() === "common"
          );
          if (!isCommonFolder || !payloadPathTop || payloadPathTop === "common") {
            return true;
          }
          return Boolean(payload.admin && currentAuthIsAdmin);
        }).map((entry) => (
          typeof applyLessonVaultProgressSnapshotToEntry === "function"
            ? applyLessonVaultProgressSnapshotToEntry(entry)
            : entry
        )).slice().sort((left, right) => {
          const rankDiff = serverVaultEntryRank(left) - serverVaultEntryRank(right);
          if (rankDiff) return rankDiff;
          return String(serverFolderDisplayName(left)).localeCompare(String(serverFolderDisplayName(right)), undefined, { numeric: true, sensitivity: "base" });
        });
        serverCurrentEntries = entries.map((entry) => (entry && typeof entry === "object" ? { ...entry } : entry)).filter(Boolean);
        const lastFilePath = getStoredServerFile();
        const preferredFolderPath = getStoredServerPath();
        const parentPath = normalizeServerPathValue(payload.parent || serverParentPathForFile(serverBrowserPath));
        setServerBrowserBackControl(serverBrowserPath, parentPath, parentPath ? clean(payload.task_owner || "") : "");
        if (!entries.length && !serverBrowserPath) {
          const empty = document.createElement("div");
          empty.className = "ft-server-empty";
          empty.textContent = "No lesson packs in QM-Home yet.";
          serverListNode.appendChild(empty);
          return;
        }
          const preferredTaskFolderSet = new Set(
            effectivePreferredTaskFolders
              .map((item) => normalizeTaskPath(item))
              .filter(Boolean)
          );
        const fragment = document.createDocumentFragment();
        let vaultIndex = 0;
        entries.forEach((entry) => {
          const item = document.createElement("button");
          item.className = `ft-server-item ${entry.type === "file" ? "is-file" : "is-folder"}`;
          item.classList.add("is-vault-inert");
          item.dataset.vaultIndex = String(vaultIndex++);
          item.dataset.path = normalizeServerPathValue(entry.path || "");
          item.dataset.effectivePath = normalizeServerPathValue(entry.effective_path || entry.link_target || "");
          item.dataset.linkTarget = normalizeServerPathValue(entry.link_target || "");
          item.dataset.linkedPath = normalizeServerPathValue(entry.linked_path || "");
          item.dataset.sourcePath = normalizeServerPathValue(entry.sourcePath || "");
          item.dataset.originalPath = normalizeServerPathValue(entry.original_path || "");
          item.classList.toggle("is-space-w", entry.type === "file" && clean(entry.extension).toLowerCase() === ".space_w");
          item.classList.toggle("is-space-v", entry.type === "file" && [".space_v", ".space_b"].includes(clean(entry.extension).toLowerCase()));
          item.classList.toggle("is-space-q", entry.type === "file" && clean(entry.extension).toLowerCase() === ".space_q");
          item.classList.toggle("is-space-p", entry.type === "file" && clean(entry.extension).toLowerCase() === ".space_p");
          item.classList.toggle("is-space-pdf", entry.type === "file" && (clean(entry.extension).toLowerCase() === ".pdf" || isSpacePictureExtension(clean(entry.extension).toLowerCase())));
          const entryProgressPaths = [
            entry.path,
            entry.effective_path,
            entry.link_target,
            entry.linked_path,
            entry.sourcePath,
            entry.original_path,
          ];
          const entryProgressView = splitLessonProgressForViewer(entry.study || {}, entryProgressPaths, payload.task_owner || payload.username || "");
          const entryStudy = entryProgressView.study || {};
          const pinnedEntryProgress = typeof lessonVaultProgressPinForPaths === "function"
            ? lessonVaultProgressPinForPaths(entryProgressPaths)
            : null;
          let entryProgress = lessonVaultDisplayProgressForStudy(entryStudy, entry, pinnedEntryProgress);
          const entryExtension = clean(entry && entry.extension).toLowerCase();
          const entrySpaceQTotal = entryExtension === ".space_q"
            ? Math.max(
              0,
              Math.floor(Number(entryStudy.total_nodes || entryStudy.totalNodes || entry.total_nodes || 0) || 0),
              Math.floor(Number(entryStudy.nodes || entry.nodes || 0) || 0) + Math.floor(Number(entryStudy.questions || entry.questions || 0) || 0),
            )
            : 0;
          if (entryProgress && entrySpaceQTotal > Math.max(0, Math.floor(Number(entryProgress.total || 0) || 0))) {
            const priorTotal = Math.max(0, Math.floor(Number(entryProgress.total || 0) || 0));
            const priorDone = Math.max(0, Math.floor(Number(entryProgress.done || 0) || 0));
            const done = priorTotal ? Math.round(priorDone * entrySpaceQTotal / priorTotal) : priorDone;
            entryProgress = {
              ...entryProgress,
              done: Math.max(0, Math.min(entrySpaceQTotal, done)),
              total: entrySpaceQTotal,
              percent: entrySpaceQTotal ? Math.round((done / entrySpaceQTotal) * 100) : 0,
              text: `${Math.max(0, Math.min(entrySpaceQTotal, done))}/${entrySpaceQTotal}`,
              node_done: Math.max(0, Math.min(entrySpaceQTotal, done)),
              node_total: entrySpaceQTotal,
              nodes_text: `${Math.max(0, Math.min(entrySpaceQTotal, done))}/${entrySpaceQTotal}`,
            };
          }
          if (entryProgress && (!entryStudy.progress || typeof entryStudy.progress !== "object")) {
            entryStudy.progress = { ...entryProgress };
          } else if (entryProgress) {
            entryStudy.progress = { ...(entryStudy.progress || {}), ...entryProgress };
          }
          // Added 2026-07-15: keep Lesson Vault chips on the same local progress snapshot as the ring after Back.
          const entryForDisplay = entry && typeof entry === "object" ? { ...entry, study: entryStudy } : entry;
          const entryProgressPartial = lessonProgressIsActivePartial(entryProgress);
          const progressMarksUserLearned = Boolean(
            entryProgress
            && !entryProgress.reviewing
            && !entryProgress.reviewRun
            && (
              entryProgress.completed
              || entryProgress.complete
              || entryProgress.lessonComplete
              || (
                Number(entryProgress.percent || 0) >= 100
                && Number(entryProgress.total || 0) > 0
                && Number(entryProgress.done || 0) >= Number(entryProgress.total || 0)
              )
            )
          );
          const studyMarksUserLearned = typeof lessonStudyCompletedRunCount === "function"
            ? lessonStudyCompletedRunCount(entryStudy) > 0
            : Number(entryStudy && (entryStudy.mine || entryStudy.completed_runs || entryStudy.completedRuns) || 0) > 0;
          const userLearnedFile = entry.type === "file" && (studyMarksUserLearned || progressMarksUserLearned);
          item.classList.toggle("has-task", entry.type === "file" && Boolean(entry.task));
          item.classList.toggle("is-task-complete", entry.type === "file" && Boolean(entry.task && entry.task.completed));
          const adminProgress = payload.admin && entry ? entryProgressView.adminProgress : null;
          const adminProgressPartial = lessonProgressIsActivePartial(adminProgress);
          const suppressStaleAdminProgress = Boolean(entryProgressPartial && !adminProgressPartial);
          const adminPriorCompletion = payload.admin && entry ? adminProgressHasPriorCompletion(entry.study || {}, adminProgress) : false;
          const adminLearnedFile = entry.type === "file" && Boolean(
            adminPriorCompletion ||
            (
              !entryProgressPartial &&
              adminProgress &&
              !adminProgress.reviewing &&
              (
                adminProgress.completed ||
                adminProgress.complete ||
                Number(adminProgress.percent || 0) >= 100
              )
            )
          );
          item.classList.toggle("is-studied", userLearnedFile);
          item.classList.toggle("is-admin-studied", adminLearnedFile);
          const progressNode = (entry.type === "file" || (entry.study && entry.study.progress))
            ? (
              (entryProgress ? createLessonProgressNode(entryStudy, "ft-vault-progress", { progress: entryProgress }) : null) ||
              createLessonProgressNode(entryStudy, "ft-vault-progress")
            )
            : null;
          const adminProgressNode = entry.type === "file" && adminProgress && !suppressStaleAdminProgress
            ? createLessonProgressNode(entry.study || {}, "ft-vault-progress ft-vault-progress-admin", {
              progress: adminProgress,
              variantClass: "is-admin-progress",
              ownerBadge: "AD",
              ownerLabel: "Admin progress",
              labelText: "Admin in progress",
              title: `Admin progress: ${clean(adminProgress.text || "")} - ${Number(adminProgress.percent || 0)}%`,
            })
            : null;
          item.classList.toggle("has-progress", Boolean(progressNode || adminProgressNode));
          item.classList.toggle("has-admin-progress", Boolean(adminProgressNode));
          const entryPath = normalizeServerPathValue(entry.path);
          const isLastFile = entry.type === "file" && entryPath && entryPath === lastFilePath;
          const isPreferredFolder = entry.type === "folder" && entryPath && entryPath === preferredFolderPath;
          const entrySelectedPaths = [
            entry.path,
            entry.effective_path,
            entry.link_target,
            entry.linked_path,
            entry.sourcePath,
            entry.source_path,
            entry.original_path,
          ].map((value) => normalizeTaskPath(value)).filter(Boolean);
          const isSelectedEntry = Boolean(serverBrowserFocusedFilePath && entrySelectedPaths.includes(normalizeTaskPath(serverBrowserFocusedFilePath)));
          const isFocusedTaskFile = entry.type === "file" && isSelectedEntry;
          const isSpaceTaskFolder = entry.type === "folder" && entryPath && preferredTaskFolderSet.has(normalizeTaskPath(entryPath));
          const isCommonRootFolder = entry.type === "folder" && (entry.virtual_common || normalizeTaskPath(entryPath) === "common");
          const isAdminRootFolder = serverEntryIsAdminRoot(entry);
          const isImmediateMissionRootFolder = entry.type === "folder" && serverPathIsImmediateMissionRoot(entryPath);
          item.classList.toggle("is-last", isLastFile);
          item.classList.toggle("is-preferred-folder", isPreferredFolder);
          item.classList.toggle("is-space-task-folder", isSpaceTaskFolder);
          item.classList.toggle("is-common-root", isCommonRootFolder);
          item.classList.toggle("is-admin-root", isAdminRootFolder);
          item.classList.toggle("is-immediate-mission-root", isImmediateMissionRootFolder);
          item.classList.toggle("is-selected", Boolean(isSelectedEntry));
          item.classList.toggle("is-task-focus", Boolean(isFocusedTaskFile));
          const displayLessonTitle = entry.type === "file" ? lessonDisplayName(entryForDisplay) : "";
          if (entry.type === "file" && displayLessonTitle) {
            item.title = `${displayLessonTitle} | ${serverLessonMeta(entryForDisplay)} | Click to select. Use Let's go to open.`;
          } else if (entry.type === "folder" && entry.virtual_common) {
            item.title = `Click to select. Click again to open common lessons for ${clean(entry.task_owner || payload.task_owner || "this learner")}.`;
          } else if (entry.type === "folder") {
            item.title = "Click to select. Click again to open this folder.";
          } else if (entry.type === "file") {
            item.title = "Click to select. Use Let's go to open.";
          }
          if (isLastFile || isPreferredFolder) {
            item.setAttribute("aria-current", "true");
          }
          item.type = "button";
          const mirrorSweep = document.createElement("span");
          mirrorSweep.className = "ft-click-mirror-sweep";
          mirrorSweep.setAttribute("aria-hidden", "true");
          const iconColumn = document.createElement("span");
          iconColumn.className = "ft-server-icon-column";
          const icon = document.createElement("span");
          icon.className = "ft-server-icon";
          icon.setAttribute("aria-hidden", "true");
          if (entry.type === "file") {
            const extension = clean(entry.extension).toLowerCase();
            icon.appendChild(createFutureFileTypeLogo(entry.path || "", extension, "", "ft-server-type-mark"));
          } else if (entry.type === "folder") {
            const docs = document.createElement("span");
            docs.className = "ft-folder-doc-stack";
            ["a", "b", "c"].forEach((name) => {
              const doc = document.createElement("span");
              doc.className = `ft-folder-doc is-${name}`;
              docs.appendChild(doc);
            });
            const lid = document.createElement("span");
            lid.className = "ft-folder-lid";
            icon.append(docs, lid);
          }
          const name = document.createElement("span");
          name.className = "ft-server-name";
          name.textContent = entry.type === "file" ? (displayLessonTitle || lessonDisplayName(entry)) : serverFolderDisplayName(entry);
          const main = document.createElement("span");
          main.className = "ft-server-main";
          const titleRow = document.createElement("span");
          titleRow.className = "ft-server-title-row";
          titleRow.appendChild(name);
          const chips = document.createElement("span");
          chips.className = "ft-server-chip-row";
          appendServerInfoChips(chips, entryForDisplay);
          if (entry.type === "file" && entry.task) {
            const taskOwnerLabel = clean(entry.task.creator_role || "").toLowerCase() === "user" ? "My task" : "Admin task";
            chips.appendChild(addTaskChipClass(createServerChip(entry.task.completed ? "Task completed" : taskOwnerLabel, entry.task.completed ? "learned" : "date")));
            if (!entry.task.completed) {
              chips.appendChild(addTaskChipClass(createServerChip(taskSeverityLabel(entry.task.severity), clean(entry.task.severity).toLowerCase() === "critical" ? "total" : "date")));
            }
          }
          const footerRow = document.createElement("span");
          footerRow.className = "ft-server-footer-row";
          footerRow.appendChild(chips);
          const fileActions = entry.type === "file" ? document.createElement("span") : null;
          if (fileActions) {
            fileActions.className = "ft-server-file-actions";
            if (userLearnedFile) {
              const learnedBadge = document.createElement("span");
              learnedBadge.className = "ft-server-learned-badge";
              learnedBadge.textContent = currentAuthIsAdmin && entryStudy.admin_view ? "User Learned" : "Learned";
              fileActions.appendChild(learnedBadge);
            }
            if (adminLearnedFile) {
              const adminLearnedBadge = document.createElement("span");
              adminLearnedBadge.className = "ft-server-learned-badge is-admin-learned";
              adminLearnedBadge.textContent = "Admin Learned";
              fileActions.appendChild(adminLearnedBadge);
            }
          }
          const progressChipText = lessonVaultProgressTextFromNode(chips) || lessonVaultProgressTextFromNode(item);
          const chipCanDriveChart = lessonVaultChipCanDriveProgressChart(pinnedEntryProgress) || lessonVaultChipCanDriveProgressChart(entryProgress);
          const chipTextProgress = chipCanDriveChart && progressChipText && typeof lessonVaultProgressFromStudyChipFields === "function"
            ? lessonVaultProgressFromStudyChipFields({ progress_text: progressChipText }, { ...entry, study: entryStudy })
            : null;
          // Added 2026-07-15: Space_V chips can include Node x/y resume text; the chart must follow learned-word progress first.
          const visibleProgress = entryProgress || pinnedEntryProgress || chipTextProgress;
          const visibleProgressNode = visibleProgress
            ? createLessonProgressNode(entryStudy, "ft-vault-progress", { progress: visibleProgress })
            : progressNode;
          item.classList.toggle("has-progress", Boolean(visibleProgressNode || adminProgressNode));
          iconColumn.appendChild(icon);
          if (visibleProgressNode) {
            iconColumn.appendChild(visibleProgressNode);
          }
          if (adminProgressNode) {
            iconColumn.appendChild(adminProgressNode);
          }
          main.appendChild(titleRow);
          main.appendChild(footerRow);
          item.append(mirrorSweep, iconColumn, main);
          if (entry.type === "file" && fileActions) {
            const goButton = createLessonGoButton();
            goButton.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();
              triggerFutureFileLogoMotion(item, { source: "go" });
              const displayPath = normalizeServerPathValue(entry.path || "");
              setSelectedTaskPath(entry.path);
              updateFutureAppRoute("lesson_vault", {
                tree: serverBrowserPath || serverParentPathForFile(entry.path),
                file: displayPath,
                process: futureRouteSpaceForFilePath(displayPath),
                replace: true,
              });
              loadServerLessonFile(entry);
            });
            fileActions.appendChild(goButton);
          }
          const taskTargetUser = clean(payload.task_owner || payload.username || currentAuthUsername);
          if (entry.type === "file" && taskTargetUser) {
            const addButton = document.createElement("button");
            addButton.type = "button";
            addButton.className = "ft-server-task-add";
            setLessonTaskAddButtonState(addButton, entry.task || null);
            addButton.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();
              void addLessonTask(taskTargetUser, entry, addButton);
            });
            if (fileActions) {
              fileActions.appendChild(addButton);
            } else {
              footerRow.appendChild(addButton);
            }
          }
          if (fileActions) {
            item.appendChild(fileActions);
          }
          const folderTaskManageAllowed = Boolean(taskTargetUser && (payload.admin || authUsernameMatches(taskTargetUser, currentAuthUsername)));
          const folderTaskSelectable = entry.type === "folder" && normalizeTaskPath(entryPath).includes("/") && !isImmediateMissionRootFolder;
          if (folderTaskSelectable && folderTaskManageAllowed) {
            const chooseFolderButton = document.createElement("button");
            chooseFolderButton.type = "button";
            chooseFolderButton.className = "ft-server-task-add ft-server-folder-task-choose";
            setFolderTaskChooseButtonState(chooseFolderButton, isSpaceTaskFolder);
            chooseFolderButton.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();
              void chooseSpaceTaskFolder(taskTargetUser, entry, chooseFolderButton);
            });
            footerRow.appendChild(chooseFolderButton);
          }
          item.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (event.shiftKey && entry.type === "file" && (item.classList.contains("is-space-v") || item.classList.contains("is-space-w"))) {
              const manualPaths = [
                entry.path,
                entry.effective_path,
                entry.link_target,
                entry.linked_path,
                entry.sourcePath,
                entry.original_path,
              ];
              syncLessonVaultChartFromChip(manualPaths, entry, { item, motion: true, notice: true });
              return;
            }
            const alreadySelected = Boolean(entryPath && normalizeTaskPath(serverBrowserFocusedFilePath) === normalizeTaskPath(entryPath));
            if (alreadySelected) {
              window.clearTimeout(item._futureMotionBurstTimer || 0);
              item.classList.remove("is-motion-burst");
              if (entry.type === "folder") {
                if (typeof rememberLessonVaultFolder === "function") {
                  rememberLessonVaultFolder(entry.path, clean(entry.task_owner || payload.task_owner || serverTaskOwnerContext || currentAuthUsername || ""), "folder_open");
                }
                loadServerDataPath(entry.path, false, clean(entry.task_owner || payload.task_owner || ""), {
                  // Added 2026-07-15: opening a selected Lesson Vault folder should not start verify/prefetch GET storms.
                  localCacheOnly: true,
                  skipBackgroundVerify: true,
                  skipChildPrefetch: true,
                  skipTaskBoardHydrate: true,
                  skipRouteLeaveFlush: true,
                  source: "lesson_vault_folder_open",
                });
                return;
              }
              setLoadStatus("File selected. Use Let's go to open this lesson.");
              if (entry.type === "file" && typeof announceSpaceVFileStats === "function") {
                void announceSpaceVFileStats(entry, item, clean(entry.task_owner || payload.task_owner || serverTaskOwnerContext || currentAuthUsername || ""));
              }
              triggerServerWorkspaceMotionBurst(item, null, { source: "select" });
              return;
            }
            if (entry.type === "folder") {
              setSelectedTaskPath(entry.path);
              rememberServerPath(entry.path);
              if (typeof rememberLessonVaultFolder === "function") {
                rememberLessonVaultFolder(entry.path, clean(entry.task_owner || payload.task_owner || serverTaskOwnerContext || currentAuthUsername || ""), "folder_select");
              }
              if (currentAuthIsAdmin) {
                const selectedTop = serverPathTop(entry.path || "");
                if (selectedTop && selectedTop !== "common") {
                  serverTaskOwnerContext = selectedTop;
                }
              }
              setLoadStatus("Folder selected. Click again to open this folder.");
              triggerServerWorkspaceMotionBurst(item, null, { source: "select" });
              return;
            }
            setSelectedTaskPath(entry.path);
            // 2026-07-24: selection is local-only; opening via Let's go owns server sync/prefetch.
            const displayPath = normalizeServerPathValue(entry.path || "");
            updateFutureAppRoute("lesson_vault", {
              tree: serverBrowserPath || serverParentPathForFile(entry.path),
              file: displayPath,
              process: futureRouteSpaceForFilePath(displayPath),
              replace: true,
            });
            setLoadStatus("File selected. Use Let's go to open this lesson.");
            if (typeof announceSpaceVFileStats === "function") {
              void announceSpaceVFileStats(entry, item, clean(entry.task_owner || payload.task_owner || serverTaskOwnerContext || currentAuthUsername || ""));
            }
            triggerServerWorkspaceMotionBurst(item, null, { source: "select" });
          });
          item.addEventListener("contextmenu", (event) => {
            showServerContextMenu(event, entry);
          });
          fragment.appendChild(item);
          if (entry.type === "file" && typeof hydrateVisibleLessonVaultFileProgress === "function" && !payload.local_cache_only) {
            hydrateVisibleLessonVaultFileProgress(entry, item, clean(entry.task_owner || payload.task_owner || payload.username || currentAuthUsername || ""));
          }
        });
        if (fragment.childNodes.length) {
          serverListNode.appendChild(fragment);
        }
        const folderTaskOwner = clean(payload.task_owner || (!payload.admin ? payload.username || "" : ""));
        if (folderTaskOwner) {
          syncVisibleFolderTaskChooseButtonsForOwner(folderTaskOwner);
        }
        if (typeof syncVisibleServerTaskRows === "function") {
          syncVisibleServerTaskRows(currentTaskPayload);
        }
        scheduleServerVaultVisibilityRefresh();
        if (serverBrowserFocusedFilePath) {
          window.setTimeout(scrollFocusedServerFileIntoView, 80);
        }
      };

      const deferredTaskBoardHydrateTimers = new Map();
      const deferredTaskBoardHydrateLastAt = new Map();

      // Added 2026-06-30: reuses the normal file-select side effects after Back returns to Lesson Vault.
      const selectServerLessonVaultEntryFromPayload = (payload = {}, paths = [], options = {}) => {
        const orderedPaths = (Array.isArray(paths) ? paths : [paths])
          .map((path) => normalizeTaskPath(normalizeServerPathValue(path || "")))
          .filter(Boolean);
        const wantedPaths = new Set(orderedPaths);
        if (!wantedPaths.size || !payload || !Array.isArray(payload.entries)) {
          return false;
        }
        const matchesEntry = (entry = {}) => [
          entry.path,
          entry.effective_path,
          entry.link_target,
          entry.linked_path,
          entry.sourcePath,
          entry.source_path,
          entry.original_path,
          serverLearningPathForEntry(entry),
        ].some((value) => wantedPaths.has(normalizeTaskPath(normalizeServerPathValue(value || ""))));
        const primaryPath = orderedPaths[0] || "";
        let entry = payload.entries.find((row) => (
          row && row.type === "file" && primaryPath && normalizeTaskPath(normalizeServerPathValue(row.path || "")) === primaryPath
        )) || payload.entries.find((row) => row && row.type === "file" && matchesEntry(row));
        if (!entry) {
          const row = Array.from(document.querySelectorAll(".ft-server-item.is-file")).find((node) => {
            const itemPaths = [
              node.dataset.path,
              node.dataset.effectivePath,
              node.dataset.linkTarget,
              node.dataset.linkedPath,
              node.dataset.sourcePath,
              node.dataset.originalPath,
            ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
            return itemPaths.some((value) => wantedPaths.has(value));
          });
          if (row) {
            entry = {
              type: "file",
              path: normalizeServerPathValue(row.dataset.path || ""),
              effective_path: normalizeServerPathValue(row.dataset.effectivePath || ""),
              link_target: normalizeServerPathValue(row.dataset.linkTarget || ""),
              linked_path: normalizeServerPathValue(row.dataset.linkedPath || ""),
            };
          }
        }
        if (!entry) {
          return false;
        }
        const displayPath = normalizeServerPathValue(entry.path || "");
        if (!displayPath) {
          return false;
          }
          setSelectedTaskPath(displayPath);
          // Added 2026-07-28: focusing/restoring a vault row must stay local; only an explicit open flow syncs last-file.
          if (!(options && options.rememberFile === false)) {
            rememberServerFile(entry, { syncNow: Boolean(options && options.syncNow) });
          }
        const shouldUpdateRoute = !(options && options.updateRoute === false);
        updateFutureAppRoute("lesson_vault", {
          tree: serverBrowserPath || serverParentPathForFile(displayPath),
          file: shouldUpdateRoute ? displayPath : "",
          process: shouldUpdateRoute ? futureRouteSpaceForFilePath(displayPath) : "",
          replace: true,
        });
        if (!(options && options.skipProgressPrefetch)) {
          scheduleServerLessonProgressPrefetch(serverLearningEntry(entry));
        }
        const item = Array.from(document.querySelectorAll(".ft-server-item.is-file")).find((node) => {
          const itemPaths = [
            node.dataset.path,
            node.dataset.effectivePath,
            node.dataset.linkTarget,
            node.dataset.linkedPath,
            node.dataset.sourcePath,
            node.dataset.originalPath,
          ].map((value) => normalizeTaskPath(normalizeServerPathValue(value || ""))).filter(Boolean);
          return itemPaths.some((value) => wantedPaths.has(value));
        });
        if (item) {
          if (!(options && options.skipFileStats)) {
            void announceSpaceVFileStats(entry, item, clean(entry.task_owner || payload.task_owner || ""));
          }
          if (!(options && options.skipChartSync) && (item.classList.contains("is-space-v") || item.classList.contains("is-space-w")) && typeof syncLessonVaultChartFromChip === "function") {
            syncLessonVaultChartFromChip(paths, entry, {
              item,
              progress: options && options.progress,
              retryMs: Number(options && options.retryMs || 0) || 0,
            });
          }
          if (options && options.progress && typeof pinVisibleLessonVaultProgressRing === "function") {
            pinVisibleLessonVaultProgressRing(paths, options.progress, {
              retryMs: Math.max(80, Number(options && options.retryMs || 0) || 0),
            });
          }
          if (options && options.motion) {
            triggerServerWorkspaceMotionBurst(item, null, { source: "select" });
          }
          {
            window.clearTimeout(item._futureTaskFocusBurstTimer || 0);
            item.classList.remove("is-task-focus-burst");
            void item.offsetWidth;
            item.classList.add("is-task-focus-burst");
            item._futureTaskFocusBurstTimer = window.setTimeout(() => {
              item.classList.remove("is-task-focus-burst");
              item._futureTaskFocusBurstTimer = 0;
            }, 2400);
          }
          window.setTimeout(scrollFocusedServerFileIntoView, 80);
        }
        return true;
      };

      const scheduleDeferredTaskBoardHydrate = (payload = {}) => {
        const targetOwner = clean(payload.task_owner || (!payload.admin ? payload.username || "" : ""));
        if (!payload || !payload.task_board_deferred || !targetOwner || !authToken) {
          return;
        }
        const cachedRow = getLessonTaskPanelCacheRow(targetOwner);
        const cachedPayload = cachedRow && cachedRow.payload && typeof cachedRow.payload === "object" ? cachedRow.payload : null;
        const cachedOwner = cachedPayload ? clean(cachedPayload.task_owner || cachedPayload.username || "") : "";
        const cachedRows = cachedPayload ? lessonTaskDisplayRows(cachedPayload) : [];
        const cachedSpaceTask = cachedPayload && cachedPayload.space_task && typeof cachedPayload.space_task === "object" ? cachedPayload.space_task : null;
        const cachedPending = Boolean(cachedSpaceTask && cachedSpaceTask.pending);
        const cachedFailed = Boolean(cachedSpaceTask && cachedSpaceTask.failed);
        const cachedSettled = Boolean(cachedSpaceTask && (cachedSpaceTask.ready || cachedSpaceTask.empty || cachedSpaceTask.failed || cachedSpaceTask.pending === false));
        const cachedLooksUsable = Boolean(
          cachedPayload &&
          authUsernameMatches(cachedOwner, targetOwner) &&
          !cachedFailed &&
          (cachedRows.length || (cachedSettled && !cachedPending))
        );
        if (cachedLooksUsable || (cachedRow && Date.now() - Number(cachedRow.at || 0) < LESSON_TASK_PANEL_REFRESH_MIN_MS)) {
          void loadLessonTasks(targetOwner, { localCacheOnly: true }).catch(() => {});
          return;
        }
        const key = targetOwner.toLowerCase();
        if (deferredTaskBoardHydrateTimers.has(key)) {
          return;
        }
        const lastAt = Number(deferredTaskBoardHydrateLastAt.get(key) || 0);
        if (Date.now() - lastAt < 30000) {
          return;
        }
        const timer = window.setTimeout(() => {
          deferredTaskBoardHydrateTimers.delete(key);
          deferredTaskBoardHydrateLastAt.set(key, Date.now());
          void loadLessonTasks(targetOwner, { fresh: true }).catch(() => {});
        }, 2800);
        deferredTaskBoardHydrateTimers.set(key, timer);
      };

      const hydrateDeferredTaskBoardNow = (payload = {}) => {
        const targetOwner = clean(payload.task_owner || (!payload.admin ? payload.username || "" : ""));
        if (!payload || !payload.task_board_deferred || !targetOwner || !authToken) {
          return;
        }
        const key = targetOwner.toLowerCase();
        const timer = deferredTaskBoardHydrateTimers.get(key);
        if (timer) {
          window.clearTimeout(timer);
          deferredTaskBoardHydrateTimers.delete(key);
        }
        deferredTaskBoardHydrateLastAt.delete(key);
        if (typeof clearLessonTaskPanelCacheForOwner === "function") {
          if (!window.__ftLessonVaultProgressHydrationPausedUntil || Number(window.__ftLessonVaultProgressHydrationPausedUntil || 0) < Date.now()) {
            clearLessonTaskPanelCacheForOwner(targetOwner);
          }
        }
        // Progress hydration may be paused during local route repaint, but the
        // target user's task panel still needs its scoped server response.
        void loadLessonTasks(targetOwner, { fresh: true }).catch(() => {});
      };

      const lessonTaskPanelNeedsOwnerHydration = (targetOwner = "") => {
        const owner = clean(targetOwner || "");
        const currentOwner = clean(currentTaskPayload && currentTaskPayload.task_owner || "");
        const currentRows = currentTaskPayload ? lessonTaskDisplayRows(currentTaskPayload) : [];
        return Boolean(owner && (!authUsernameMatches(owner, currentOwner) || !currentRows.length));
      };

      // Added 2026-07-09: keeps Space Task populated after vault navigation renders a deferred task payload.
      const shouldHydrateDeferredTaskBoardImmediately = (payload = {}, requestPath = "", explicitNow = false) => {
        const targetOwner = clean(payload.task_owner || (!payload.admin ? payload.username || "" : ""));
        if (!payload || !payload.task_board_deferred || !targetOwner || !authToken) {
          return false;
        }
        if (explicitNow) {
          return true;
        }
        const pathKey = normalizeTaskPath(requestPath || payload.path || "");
        if (!pathKey || pathKey === "common") {
          return true;
        }
        const currentOwner = clean(currentTaskPayload && currentTaskPayload.task_owner || "");
        const currentRows = currentTaskPayload ? lessonTaskDisplayRows(currentTaskPayload) : [];
        if (!authUsernameMatches(currentOwner, targetOwner) || !currentRows.length) {
          return true;
        }
        return Boolean(
          serverBrowserActivePanel === "task"
          || (taskModal && !taskModal.hidden)
          || (serverTaskPanel && !serverTaskPanel.hidden)
        );
      };

      let serverBrowserAutoRefreshTimer = 0;
      let serverBrowserAutoRefreshBusy = false;
      let serverBrowserManifestPollTimer = 0;
      let serverBrowserManifestReloadSignature = "";
      let serverBrowserAuthOpenBusy = false;
      let serverBrowserRecentLoadKey = "";
      let serverBrowserRecentLoadAt = 0;
      let serverBrowserLoadSerial = 0;
      let serverBrowserActiveAbort = null;
      const serverBrowserLoadKey = (pathValue = "", taskOwner = "") => `${normalizeServerPathValue(pathValue || "")}::${clean(taskOwner || "")}`;
      const SERVER_BROWSER_AUTO_REFRESH_MS = 60 * 60 * 1000;
      const LOGIN_VAULT_WARMUP_TTL_MS = 60 * 60 * 1000;
      const LOGIN_VAULT_WARMUP_WAIT_MS = 900;
      let loginVaultWarmupSerial = 0;
      let loginVaultWarmupState = {
        username: "",
        path: "",
        status: "idle",
        promise: null,
        payload: null,
        error: "",
        at: 0,
      };
      const loginVaultWarmupStats = window.__futureLoginVaultWarmupStats = window.__futureLoginVaultWarmupStats || {
        fetchMs: 0,
        composeMs: 0,
        progressApplyMs: 0,
        rowSyncMs: 0,
        finalizeMs: 0,
        lastUsername: "",
        lastPath: "",
      };
      let loginVaultTreePreloadCache = {
        username: "",
        etag: "",
        payload: null,
        at: 0,
      };
      let loginVaultCommonTreePreloadCache = {
        key: "__common_tree__",
        etag: "",
        payload: null,
        at: 0,
      };

      const loginVaultTreePreloadStorageKey = (username = "") => `future_login_tree_preload_cache_v1:${clean(username).toLowerCase()}`;
      const LOGIN_VAULT_TREE_PRELOAD_CACHE_NAME = "future-login-tree-preload-cache-v1";
      const LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA = "v1";
      const LOGIN_VAULT_TREE_PRELOAD_DB_NAME = "future-login-tree-preload-cache-db-v1";
      const LOGIN_VAULT_TREE_PRELOAD_DB_STORE = "entries";
      const loginVaultTreePreloadCacheRequestUrl = (username = "") => `/__future_cache__/login-tree-preload?user=${encodeURIComponent(clean(username).toLowerCase())}`;
      let loginVaultTreePreloadDbPromise = null;
      const loginVaultTreePreloadCacheStats = window.__futureLoginVaultTreePreloadCacheStats = window.__futureLoginVaultTreePreloadCacheStats || {
        indexedDbHits: 0,
        cacheStorageHits: 0,
        corruptRows: 0,
        removedRows: 0,
        writeFailures: 0,
        quotaFailures: 0,
        sessionStorageReadMs: 0,
        indexedDbReadMs: 0,
        cacheStorageReadMs: 0,
        jsonParseMs: 0,
        sessionStorageWriteMs: 0,
        indexedDbWriteMs: 0,
        cacheStorageWriteMs: 0,
        jsonStringifyMs: 0,
        lastError: "",
        lastInvalidKey: "",
      };
      const browserTimingNow = () => (typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now());
      const ensureLoginTimelineMetrics = () => {
        if (typeof window === "undefined") {
          return null;
        }
        const metrics = window.__ftLoginTimelineMetrics = window.__ftLoginTimelineMetrics || { counts: {}, totalMs: {}, maxMs: {} };
        if (typeof window.__ftRecordLoginTimelinePhase !== "function") {
          window.__ftRecordLoginTimelinePhase = (phase = "", ms = 0) => {
            const key = clean(phase);
            if (!key) {
              return;
            }
            const duration = Math.max(0, Number(ms) || 0);
            metrics.counts[key] = Number(metrics.counts[key] || 0) + 1;
            metrics.totalMs[key] = Number((Number(metrics.totalMs[key] || 0) + duration).toFixed(3));
            metrics.maxMs[key] = Math.max(Number(metrics.maxMs[key] || 0), duration);
          };
        }
        return metrics;
      };

      const openLoginVaultTreePreloadDb = () => {
        if (!("indexedDB" in window)) {
          return Promise.resolve(null);
        }
        if (loginVaultTreePreloadDbPromise) {
          return loginVaultTreePreloadDbPromise;
        }
        loginVaultTreePreloadDbPromise = new Promise((resolve) => {
          try {
            const request = indexedDB.open(LOGIN_VAULT_TREE_PRELOAD_DB_NAME, 1);
            request.onerror = () => resolve(null);
            request.onupgradeneeded = () => {
              const db = request.result;
              if (!db.objectStoreNames.contains(LOGIN_VAULT_TREE_PRELOAD_DB_STORE)) {
                db.createObjectStore(LOGIN_VAULT_TREE_PRELOAD_DB_STORE, { keyPath: "key" });
              }
            };
            request.onsuccess = () => resolve(request.result || null);
          } catch (error) {
            resolve(null);
          }
        });
        return loginVaultTreePreloadDbPromise;
      };

      const readLoginVaultTreePreloadIndexedDb = async (username = "") => {
        const normalized = clean(username).toLowerCase();
        if (!normalized) {
          return null;
        }
        const db = await openLoginVaultTreePreloadDb();
        if (!db) {
          return null;
        }
        const startedAt = browserTimingNow();
        return new Promise((resolve) => {
          try {
            const request = db.transaction(LOGIN_VAULT_TREE_PRELOAD_DB_STORE, "readonly").objectStore(LOGIN_VAULT_TREE_PRELOAD_DB_STORE).get(normalized);
            request.onerror = () => {
              loginVaultTreePreloadCacheStats.indexedDbReadMs += Math.max(0, browserTimingNow() - startedAt);
              resolve(null);
            };
            request.onsuccess = () => {
              loginVaultTreePreloadCacheStats.indexedDbReadMs += Math.max(0, browserTimingNow() - startedAt);
              resolve(request.result || null);
            };
          } catch (error) {
            loginVaultTreePreloadCacheStats.indexedDbReadMs += Math.max(0, browserTimingNow() - startedAt);
            resolve(null);
          }
        });
      };

      const removeLoginVaultTreePreloadIndexedDb = async (username = "", reason = "") => {
        const normalized = clean(username).toLowerCase();
        if (!normalized) {
          return;
        }
        const db = await openLoginVaultTreePreloadDb();
        if (!db) {
          return;
        }
        return new Promise((resolve) => {
          try {
            const tx = db.transaction(LOGIN_VAULT_TREE_PRELOAD_DB_STORE, "readwrite");
            tx.oncomplete = () => resolve();
            tx.onerror = () => resolve();
            tx.objectStore(LOGIN_VAULT_TREE_PRELOAD_DB_STORE).delete(normalized);
            loginVaultTreePreloadCacheStats.removedRows += 1;
            loginVaultTreePreloadCacheStats.lastInvalidKey = normalized;
            loginVaultTreePreloadCacheStats.lastError = clean(reason);
          } catch (error) {
            resolve();
          }
        });
      };

      const writeLoginVaultTreePreloadIndexedDb = async (username = "", row = null) => {
        const normalized = clean(username).toLowerCase();
        if (!normalized || !row || typeof row !== "object") {
          return;
        }
        const db = await openLoginVaultTreePreloadDb();
        if (!db) {
          return;
        }
        const startedAt = browserTimingNow();
        return new Promise((resolve) => {
          try {
            const tx = db.transaction(LOGIN_VAULT_TREE_PRELOAD_DB_STORE, "readwrite");
            tx.oncomplete = () => {
              loginVaultTreePreloadCacheStats.indexedDbWriteMs += Math.max(0, browserTimingNow() - startedAt);
              resolve();
            };
            tx.onerror = () => {
              loginVaultTreePreloadCacheStats.indexedDbWriteMs += Math.max(0, browserTimingNow() - startedAt);
              loginVaultTreePreloadCacheStats.writeFailures += 1;
              const errorName = clean(tx.error && tx.error.name);
              if (errorName === "QuotaExceededError") {
                loginVaultTreePreloadCacheStats.quotaFailures += 1;
              }
              loginVaultTreePreloadCacheStats.lastError = errorName || "indexeddb-write-error";
              resolve();
            };
            tx.objectStore(LOGIN_VAULT_TREE_PRELOAD_DB_STORE).put({ key: normalized, ...row });
          } catch (error) {
            loginVaultTreePreloadCacheStats.indexedDbWriteMs += Math.max(0, browserTimingNow() - startedAt);
            loginVaultTreePreloadCacheStats.writeFailures += 1;
            const errorName = clean(error && error.name);
            if (errorName === "QuotaExceededError") {
              loginVaultTreePreloadCacheStats.quotaFailures += 1;
            }
            loginVaultTreePreloadCacheStats.lastError = errorName || clean(error && error.message) || "indexeddb-write-exception";
            resolve();
          }
        });
      };

      const readLoginVaultCommonTreePreloadCache = async () => {
        if (clean(loginVaultCommonTreePreloadCache.etag) && loginVaultCommonTreePreloadCache.payload && typeof loginVaultCommonTreePreloadCache.payload === "object") {
          return loginVaultCommonTreePreloadCache;
        }
        try {
          const row = await readLoginVaultTreePreloadIndexedDb("__common_tree__");
          const meta = row && typeof row === "object" && row.meta && typeof row.meta === "object" ? row.meta : null;
          if (
            row &&
            clean(row.etag) &&
            row.payload &&
            typeof row.payload === "object" &&
            meta &&
            clean(meta.frontend_build_stamp) === clean(FUTURE_FRONTEND_BUILD_STAMP) &&
            clean(meta.schema_version) === LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA &&
            clean(meta.common_manifest_signature) &&
            clean(meta.manifest_integrity_signature)
          ) {
            loginVaultCommonTreePreloadCache = {
              key: "__common_tree__",
              etag: clean(row.etag),
              payload: row.payload,
              meta,
              at: Number(row.at || 0) || 0,
            };
            loginVaultTreePreloadCacheStats.indexedDbHits += 1;
            try {
              console.info("[future-tree-preload-cache] common indexeddb hit");
            } catch (error) {
            }
          } else if (row) {
            loginVaultTreePreloadCacheStats.corruptRows += 1;
            await removeLoginVaultTreePreloadIndexedDb("__common_tree__", "invalid-common-tree-row");
          }
        } catch (error) {
          loginVaultTreePreloadCacheStats.corruptRows += 1;
          loginVaultTreePreloadCacheStats.lastError = clean(error && error.message) || "common-tree-read-error";
          await removeLoginVaultTreePreloadIndexedDb("__common_tree__", "common-tree-read-error");
        }
        return loginVaultCommonTreePreloadCache;
      };

      const rememberLoginVaultCommonTreePreloadCache = async (etag = "", payload = null) => {
        const tag = clean(etag);
        if (!tag || !payload || typeof payload !== "object") {
          return;
        }
        const meta = {
          schema_version: LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA,
          frontend_build_stamp: clean(FUTURE_FRONTEND_BUILD_STAMP),
          common_manifest_signature: clean(payload.common_manifest_signature || payload.common_revision || ""),
          manifest_integrity_signature: clean(payload.manifest_integrity_signature || ""),
          manifest_updated_at: clean(payload.manifest_updated_at || ""),
          format: clean(payload.format || payload.format_version || ""),
          payload_byte_size: 0,
        };
        loginVaultCommonTreePreloadCache = { key: "__common_tree__", etag: tag, payload, meta, at: Date.now() };
        try {
          const stringifyStartedAt = browserTimingNow();
          const encoded = JSON.stringify(loginVaultCommonTreePreloadCache);
          loginVaultTreePreloadCacheStats.jsonStringifyMs += Math.max(0, browserTimingNow() - stringifyStartedAt);
          loginVaultCommonTreePreloadCache.meta.payload_byte_size = encoded.length;
          loginVaultCommonTreePreloadCache.meta.payload_encoded = encoded;
        } catch (error) {
        }
        await writeLoginVaultTreePreloadIndexedDb("__common_tree__", loginVaultCommonTreePreloadCache);
      };

      let loginVaultTreePayloadComposeCache = {
        key: "",
        payload: null,
      };

      const composeLoginVaultTreePayload = (commonPayload = null, overlayPayload = null, username = "") => {
        const common = commonPayload && typeof commonPayload === "object" ? commonPayload : {};
        const overlay = overlayPayload && typeof overlayPayload === "object" ? overlayPayload : {};
        const cacheKey = [
          clean(username).toLowerCase(),
          clean(common.common_manifest_signature || common.common_revision || ""),
          clean(overlay.overlay_manifest_signature || overlay.overlay_revision || ""),
          clean(common.manifest_integrity_signature || overlay.manifest_integrity_signature || ""),
          clean(common.manifest_updated_at || overlay.manifest_updated_at || ""),
          clean(common.format || overlay.format || "compact-v1"),
          Array.isArray(common.rows) ? common.rows.length : 0,
          Array.isArray(overlay.rows) ? overlay.rows.length : 0,
        ].join("|");
        if (loginVaultTreePayloadComposeCache.key === cacheKey && loginVaultTreePayloadComposeCache.payload) {
          return loginVaultTreePayloadComposeCache.payload;
        }
        const commonRows = Array.isArray(common.rows) ? common.rows : [];
        const overlayRows = Array.isArray(overlay.rows) ? overlay.rows : [];
        const entryColumns = Array.isArray(common.entry_columns) && common.entry_columns.length
          ? common.entry_columns
          : (Array.isArray(overlay.entry_columns) ? overlay.entry_columns : []);
        const payload = {
          ok: true,
          username: clean(username),
          admin: Boolean(overlay.admin),
          common_manifest_signature: clean(common.common_manifest_signature || common.common_revision || ""),
          overlay_manifest_signature: clean(overlay.overlay_manifest_signature || ""),
          manifest_signature: `${clean(common.common_manifest_signature || common.common_revision || "")}:${clean(overlay.overlay_revision || overlay.overlay_manifest_signature || "")}`,
          manifest_integrity_signature: clean(common.manifest_integrity_signature || overlay.manifest_integrity_signature || ""),
          manifest_updated_at: clean(common.manifest_updated_at || overlay.manifest_updated_at || ""),
          format: clean(common.format || overlay.format || "compact-v1"),
          common,
          userOverlay: overlay,
          entry_columns: entryColumns,
          rows: [...commonRows, ...overlayRows],
          row_count: commonRows.length + overlayRows.length,
        };
        loginVaultTreePayloadComposeCache = { key: cacheKey, payload };
        return payload;
      };

      // Added 2026-07-28: decode one authenticated preload folder locally so task focus never falls through to /server-data/list.
      const loginVaultTreeFolderPayloadFromCache = (relativePath = "", taskOwner = "") => {
        const wantedPath = normalizeServerPathValue(relativePath || "");
        const treePayload = loginVaultTreePayloadComposeCache && loginVaultTreePayloadComposeCache.payload;
        const rows = treePayload && Array.isArray(treePayload.rows) ? treePayload.rows : [];
        const row = rows.slice().reverse().find((candidate) => normalizeServerPathValue(candidate && candidate.path || "") === wantedPath);
        if (!row) {
          return null;
        }
        const columns = Array.isArray(treePayload.entry_columns) ? treePayload.entry_columns : [];
        const entries = (Array.isArray(row.entries) ? row.entries : []).map((values) => {
          const source = Array.isArray(values) ? values : [];
          return columns.reduce((entry, column, index) => {
            if (source[index] !== undefined) {
              entry[column] = source[index];
            }
            return entry;
          }, {});
        });
        return {
          ok: true,
          path: wantedPath,
          parent: normalizeServerPathValue(row.parent || serverParentPathForFile(wantedPath)),
          username: clean(treePayload.username || currentAuthUsername || ""),
          task_owner: clean(taskOwner || ""),
          admin: Boolean(treePayload.admin),
          entries,
          entry_columns: columns,
          manifest_signature: clean(treePayload.manifest_signature || ""),
          common_manifest_signature: clean(treePayload.common_manifest_signature || ""),
          overlay_manifest_signature: clean(treePayload.overlay_manifest_signature || ""),
          manifest_integrity_signature: clean(treePayload.manifest_integrity_signature || ""),
          local_cache_only: true,
        };
      };

      // Added 2026-07-26: keep login tree snapshots across tab close/reopen with a persistent browser cache.
      const readLoginVaultTreePreloadPersistentCache = async (username = "") => {
        const normalized = clean(username).toLowerCase();
        if (!normalized) {
          return null;
        }
        try {
          const row = await readLoginVaultTreePreloadIndexedDb(normalized);
          if (row && clean(row.username).toLowerCase() === normalized && clean(row.etag) && row.payload && typeof row.payload === "object") {
            const meta = row.meta && typeof row.meta === "object" ? row.meta : null;
          if (
            meta &&
            clean(meta.frontend_build_stamp) === clean(FUTURE_FRONTEND_BUILD_STAMP) &&
            clean(meta.schema_version) === LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA &&
            (clean(meta.common_manifest_signature) || clean(meta.overlay_manifest_signature) || clean(meta.manifest_signature)) &&
            clean(meta.manifest_integrity_signature)
          ) {
              const normalizedRow = {
                username: normalized,
                etag: clean(row.etag),
                payload: row.payload,
                meta,
                at: Number(row.at || 0) || 0,
              };
              loginVaultTreePreloadCache = normalizedRow;
              loginVaultTreePreloadCacheStats.indexedDbHits += 1;
              try {
                console.info("[future-tree-preload-cache] indexeddb hit", normalized);
              } catch (error) {
              }
              try {
                sessionStorage.setItem(loginVaultTreePreloadStorageKey(normalized), JSON.stringify(normalizedRow));
              } catch (error) {
              }
              return normalizedRow;
            }
            loginVaultTreePreloadCacheStats.corruptRows += 1;
            await removeLoginVaultTreePreloadIndexedDb(normalized, "invalid-user-overlay-row");
          }
        } catch (error) {
          loginVaultTreePreloadCacheStats.corruptRows += 1;
          loginVaultTreePreloadCacheStats.lastError = clean(error && error.message) || "user-overlay-read-error";
          await removeLoginVaultTreePreloadIndexedDb(normalized, "user-overlay-read-error");
        }
        if (typeof caches === "undefined") {
          return null;
        }
        try {
          const cacheReadStartedAt = browserTimingNow();
          const cache = await caches.open(LOGIN_VAULT_TREE_PRELOAD_CACHE_NAME);
          const response = await cache.match(loginVaultTreePreloadCacheRequestUrl(normalized));
          loginVaultTreePreloadCacheStats.cacheStorageReadMs += Math.max(0, browserTimingNow() - cacheReadStartedAt);
          if (!response || clean(response.headers.get("X-Future-Cache-Schema")) !== LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA) {
            return null;
          }
          if (clean(response.headers.get("X-Future-Cache-Username")).toLowerCase() !== normalized) {
            return null;
          }
          const etag = clean(response.headers.get("X-Future-Source-Etag"));
          if (!etag) {
            return null;
          }
          const responseText = await response.text();
          const parseStartedAt = browserTimingNow();
          const payload = JSON.parse(responseText || "{}");
          loginVaultTreePreloadCacheStats.jsonParseMs += Math.max(0, browserTimingNow() - parseStartedAt);
          if (!payload || typeof payload !== "object" || !payload.payload || typeof payload.payload !== "object") {
            return null;
          }
          const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {};
          if (clean(meta.frontend_build_stamp) !== clean(FUTURE_FRONTEND_BUILD_STAMP)) {
            return null;
          }
          if (clean(meta.schema_version) !== LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA) {
            return null;
          }
          if (!(clean(meta.common_manifest_signature) || clean(meta.overlay_manifest_signature) || clean(meta.manifest_signature)) || !clean(meta.manifest_integrity_signature)) {
            return null;
          }
          const row = {
            username: normalized,
            etag,
            payload: payload.payload,
            meta,
            at: Number(payload.at || 0) || 0,
          };
          loginVaultTreePreloadCache = row;
          loginVaultTreePreloadCacheStats.cacheStorageHits += 1;
          try {
            console.info("[future-tree-preload-cache] cachestorage hit", normalized);
          } catch (error) {
          }
          try {
            sessionStorage.setItem(loginVaultTreePreloadStorageKey(normalized), JSON.stringify(row));
          } catch (error) {
          }
          return row;
        } catch (error) {
          loginVaultTreePreloadCacheStats.lastError = clean(error && error.message) || "cachestorage-read-error";
          return null;
        }
      };

      const readLoginVaultTreePreloadCache = async (username = "") => {
        const normalized = clean(username).toLowerCase();
        if (!normalized || clean(loginVaultTreePreloadCache.username).toLowerCase() === normalized) {
          return loginVaultTreePreloadCache;
        }
        try {
          const readStartedAt = browserTimingNow();
          const raw = sessionStorage.getItem(loginVaultTreePreloadStorageKey(normalized)) || "{}";
          loginVaultTreePreloadCacheStats.sessionStorageReadMs += Math.max(0, browserTimingNow() - readStartedAt);
          const parseStartedAt = browserTimingNow();
          const row = JSON.parse(raw);
          loginVaultTreePreloadCacheStats.jsonParseMs += Math.max(0, browserTimingNow() - parseStartedAt);
          const meta = row && typeof row === "object" && row.meta && typeof row.meta === "object" ? row.meta : null;
          if (
            row &&
            clean(row.username).toLowerCase() === normalized &&
            clean(row.etag) &&
            row.payload &&
            typeof row.payload === "object" &&
            meta &&
            clean(meta.frontend_build_stamp) === clean(FUTURE_FRONTEND_BUILD_STAMP) &&
            clean(meta.schema_version) === LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA
          ) {
            loginVaultTreePreloadCache = {
              username: normalized,
              etag: clean(row.etag),
              payload: row.payload,
              meta,
              at: Number(row.at || 0) || 0,
            };
          }
        } catch (error) {
        }
        const persistent = await readLoginVaultTreePreloadPersistentCache(normalized);
        if (persistent && typeof persistent === "object") {
          return persistent;
        }
        return loginVaultTreePreloadCache;
      };

      const rememberLoginVaultTreePreloadCache = async (username = "", etag = "", payload = null) => {
        const normalized = clean(username).toLowerCase();
        const tag = clean(etag);
        if (!normalized || !tag || !payload || typeof payload !== "object") {
          return;
        }
        const meta = {
          schema_version: LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA,
          frontend_build_stamp: clean(FUTURE_FRONTEND_BUILD_STAMP),
          common_manifest_signature: clean(payload.common_manifest_signature || ""),
          overlay_manifest_signature: clean(payload.overlay_manifest_signature || ""),
          manifest_signature: clean(payload.manifest_signature || ""),
          manifest_integrity_signature: clean(payload.manifest_integrity_signature || ""),
          manifest_updated_at: clean(payload.manifest_updated_at || ""),
          format: clean(payload.format || ""),
          payload_byte_size: 0,
        };
        loginVaultTreePreloadCache = { username: normalized, etag: tag, payload, meta, at: Date.now() };
        try {
          loginVaultTreePreloadCache.meta.payload_byte_size = 0;
          const stringifyStartedAt = browserTimingNow();
          const encoded = JSON.stringify(loginVaultTreePreloadCache);
          loginVaultTreePreloadCacheStats.jsonStringifyMs += Math.max(0, browserTimingNow() - stringifyStartedAt);
          loginVaultTreePreloadCache.meta.payload_byte_size = encoded.length;
          loginVaultTreePreloadCache.meta.payload_encoded = encoded;
          const writeStartedAt = browserTimingNow();
          sessionStorage.setItem(
            loginVaultTreePreloadStorageKey(normalized),
            encoded
          );
          loginVaultTreePreloadCacheStats.sessionStorageWriteMs += Math.max(0, browserTimingNow() - writeStartedAt);
        } catch (error) {
        }
        await writeLoginVaultTreePreloadIndexedDb(normalized, loginVaultTreePreloadCache);
        if (typeof caches === "undefined") {
          return;
        }
        try {
          const stringifyStartedAt = browserTimingNow();
          const encoded = loginVaultTreePreloadCache.meta && typeof loginVaultTreePreloadCache.meta.payload_encoded === "string"
            ? loginVaultTreePreloadCache.meta.payload_encoded
            : JSON.stringify(loginVaultTreePreloadCache);
          loginVaultTreePreloadCacheStats.jsonStringifyMs += Math.max(0, browserTimingNow() - stringifyStartedAt);
          const writeStartedAt = browserTimingNow();
          const cache = await caches.open(LOGIN_VAULT_TREE_PRELOAD_CACHE_NAME);
          await cache.put(loginVaultTreePreloadCacheRequestUrl(normalized), new Response(encoded, {
            headers: {
              "Content-Type": "application/json; charset=utf-8",
              "X-Future-Cache-Schema": LOGIN_VAULT_TREE_PRELOAD_CACHE_SCHEMA,
              "X-Future-Cache-Username": normalized,
              "X-Future-Source-Etag": tag,
            },
          }));
          loginVaultTreePreloadCacheStats.cacheStorageWriteMs += Math.max(0, browserTimingNow() - writeStartedAt);
        } catch (error) {
          loginVaultTreePreloadCacheStats.writeFailures += 1;
          const errorName = clean(error && error.name);
          if (errorName === "QuotaExceededError") {
            loginVaultTreePreloadCacheStats.quotaFailures += 1;
          }
          loginVaultTreePreloadCacheStats.lastError = errorName || clean(error && error.message) || "cachestorage-write-error";
        }
      };

      let loginVaultPreloadCache = {
        username: "",
        etag: "",
        payload: null,
        at: 0,
      };

      const loginVaultPreloadStorageKey = (username = "") => `future_login_preload_cache_v1:${clean(username).toLowerCase()}`;

      const readLoginVaultPreloadCache = (username = "") => {
        const normalized = clean(username).toLowerCase();
        if (!normalized || clean(loginVaultPreloadCache.username).toLowerCase() === normalized) {
          return loginVaultPreloadCache;
        }
        try {
          const readStartedAt = browserTimingNow();
          const raw = sessionStorage.getItem(loginVaultPreloadStorageKey(normalized)) || "{}";
          loginVaultTreePreloadCacheStats.sessionStorageReadMs += Math.max(0, browserTimingNow() - readStartedAt);
          const parseStartedAt = browserTimingNow();
          const row = JSON.parse(raw);
          loginVaultTreePreloadCacheStats.jsonParseMs += Math.max(0, browserTimingNow() - parseStartedAt);
          if (row && clean(row.username).toLowerCase() === normalized && clean(row.etag) && row.payload && typeof row.payload === "object") {
            loginVaultPreloadCache = {
              username: normalized,
              etag: clean(row.etag),
              payload: row.payload,
              at: Number(row.at || 0) || 0,
            };
          }
        } catch (error) {
        }
        return loginVaultPreloadCache;
      };

      const rememberLoginVaultPreloadCache = (username = "", etag = "", payload = null) => {
        const normalized = clean(username).toLowerCase();
        const tag = clean(etag);
        if (!normalized || !tag || !payload || typeof payload !== "object") {
          return;
        }
        loginVaultPreloadCache = { username: normalized, etag: tag, payload, at: Date.now() };
        try {
          const stringifyStartedAt = browserTimingNow();
          sessionStorage.setItem(
            loginVaultPreloadStorageKey(normalized),
            JSON.stringify(loginVaultPreloadCache)
          );
          loginVaultTreePreloadCacheStats.sessionStorageWriteMs += Math.max(0, browserTimingNow() - stringifyStartedAt);
        } catch (error) {
        }
      };

      const clearLoginVaultPreloadCacheForUser = (username = "") => {
        const normalized = clean(username).toLowerCase().toLowerCase();
        if (!normalized) {
          return;
        }
        if (clean(loginVaultPreloadCache.username).toLowerCase() === normalized) {
          loginVaultPreloadCache = {
            username: "",
            etag: "",
            payload: null,
            at: 0,
          };
        }
        try {
          sessionStorage.removeItem(loginVaultPreloadStorageKey(normalized));
        } catch (error) {
        }
      };

      const loginVaultWarmupUsername = () => clean(authUser && authUser.value);

      const resetLoginVaultWarmupForInput = () => {
        const username = loginVaultWarmupUsername();
        if (!username || username.toLowerCase() !== clean(loginVaultWarmupState.username).toLowerCase()) {
          loginVaultWarmupSerial += 1;
          loginVaultWarmupState = {
            username,
            path: "",
            status: "idle",
            promise: null,
            payload: null,
            error: "",
            at: 0,
          };
        }
      };

      const focusAuthUsernameForCorrection = () => {
        if (!authUser || authGate && authGate.classList.contains("is-hidden")) {
          return;
        }
        window.setTimeout(() => {
          try {
            authUser.focus({ preventScroll: true });
            if (typeof authUser.select === "function") {
              authUser.select();
            }
          } catch (error) {
          }
        }, 30);
      };

      const startLoginVaultWarmup = (reason = "") => {
        if (authMode !== "login") {
          return Promise.resolve(null);
        }
        const username = loginVaultWarmupUsername();
        if (!username) {
          return Promise.resolve(null);
        }
        const pathValue = typeof getStoredServerPath === "function" ? normalizeServerPathValue(getStoredServerPath()) : "";
        const sameWarmup = clean(loginVaultWarmupState.username).toLowerCase() === username.toLowerCase()
          && normalizeServerPathValue(loginVaultWarmupState.path || "") === pathValue;
        if (
          sameWarmup
          && loginVaultWarmupState.status === "ready"
          && Date.now() - Number(loginVaultWarmupState.at || 0) < LOGIN_VAULT_WARMUP_TTL_MS
        ) {
          return Promise.resolve(loginVaultWarmupState);
        }
        if (sameWarmup && loginVaultWarmupState.promise) {
          return loginVaultWarmupState.promise;
        }
        const serial = ++loginVaultWarmupSerial;
        loginVaultWarmupState = {
          username,
          path: pathValue,
          status: "checking",
          promise: null,
          payload: null,
          error: "",
          at: Date.now(),
        };
        if (reason !== "submit") {
          setAuthStatus("Dang kiem tra tai khoan...");
        }
        const promise = (async () => {
          const usernameQuery = new URLSearchParams();
          usernameQuery.set("username", username);
          const check = await fetchAuthJson(`/auth/username?${usernameQuery.toString()}`, {
            method: "GET",
            timeoutMs: 3600,
          });
          if (serial !== loginVaultWarmupSerial || loginVaultWarmupUsername().toLowerCase() !== username.toLowerCase()) {
            return null;
          }
          const userPayload = check && check.payload && typeof check.payload === "object" ? check.payload : {};
          if (!userPayload.valid) {
            loginVaultWarmupState = {
              ...loginVaultWarmupState,
              status: "invalid",
              promise: null,
              error: clean(userPayload.message || "Ten tai khoan chua hop le."),
              at: Date.now(),
            };
            setAuthStatus(loginVaultWarmupState.error, "error");
            focusAuthUsernameForCorrection();
            return loginVaultWarmupState;
          }
          if (!userPayload.exists) {
            const pending = Boolean(userPayload.pending);
            const message = pending
              ? "Tai khoan nay dang cho admin duyet."
              : "Tai khoan khong ton tai. Hay kiem tra lai ten dang nhap.";
            loginVaultWarmupState = {
              ...loginVaultWarmupState,
              status: pending ? "pending" : "missing",
              promise: null,
              error: message,
              at: Date.now(),
            };
            setAuthStatus(message, "error");
            focusAuthUsernameForCorrection();
            return loginVaultWarmupState;
          }
          if (reason !== "submit") {
            loginVaultWarmupState = {
              ...loginVaultWarmupState,
              status: "verified",
              promise: null,
              error: "",
              at: Date.now(),
            };
            setAuthStatus("Da tim thay tai khoan. Nhap mat khau de vao.", "ok");
            return loginVaultWarmupState;
          }
          loginVaultWarmupState = {
            ...loginVaultWarmupState,
            status: "preloading",
            at: Date.now(),
          };
          loginVaultWarmupStats.lastUsername = username;
          loginVaultWarmupStats.lastPath = pathValue;
          const preloadQuery = new URLSearchParams();
          preloadQuery.set("username", username);
          preloadQuery.set("response", "compact-v2");
          if (pathValue) {
            preloadQuery.set("path", pathValue);
          }
          const cachedLoginPreload = readLoginVaultPreloadCache(username);
          const canRevalidateLoginPreload = clean(cachedLoginPreload.username).toLowerCase() === username.toLowerCase()
            && clean(cachedLoginPreload.etag)
            && cachedLoginPreload.payload
            && typeof cachedLoginPreload.payload === "object";
          const cachedCommonTreePreload = await readLoginVaultCommonTreePreloadCache();
          const canRevalidateCommonTreePreload = clean(cachedCommonTreePreload.etag)
            && cachedCommonTreePreload.payload
            && typeof cachedCommonTreePreload.payload === "object";
          const cachedUserOverlayPreload = await readLoginVaultTreePreloadCache(username);
          const canRevalidateUserOverlayPreload = clean(cachedUserOverlayPreload.username).toLowerCase() === username.toLowerCase()
            && clean(cachedUserOverlayPreload.etag)
            && cachedUserOverlayPreload.payload
            && typeof cachedUserOverlayPreload.payload === "object";
          const fetchStartedAt = browserTimingNow();
          const [preload, commonTreeSnapshot, userOverlaySnapshot] = await Promise.all([
            fetchServerJson(`/server-data/login-preload?${preloadQuery.toString()}`, {
              timeoutMs: 45000,
              cache: "no-cache",
              ifNoneMatch: canRevalidateLoginPreload ? clean(cachedLoginPreload.etag) : "",
              notModifiedPayload: canRevalidateLoginPreload ? cachedLoginPreload.payload : null,
            }),
            fetchServerJson("/server-data/common-tree", {
              timeoutMs: 45000,
              // Revalidate the shared machine cache by ETag; unchanged common trees return 304.
              cache: "no-cache",
              ifNoneMatch: canRevalidateCommonTreePreload ? clean(cachedCommonTreePreload.etag) : "",
              notModifiedPayload: canRevalidateCommonTreePreload ? cachedCommonTreePreload.payload : null,
            }),
            fetchServerJson("/server-data/user-overlay", {
              timeoutMs: 45000,
              cache: "no-cache",
              ifNoneMatch: canRevalidateUserOverlayPreload ? clean(cachedUserOverlayPreload.etag) : "",
              notModifiedPayload: canRevalidateUserOverlayPreload ? cachedUserOverlayPreload.payload : null,
            }),
          ]);
          loginVaultWarmupStats.fetchMs += Math.max(0, browserTimingNow() - fetchStartedAt);
          if (serial !== loginVaultWarmupSerial || loginVaultWarmupUsername().toLowerCase() !== username.toLowerCase()) {
            return null;
          }
          const composeStartedAt = browserTimingNow();
          const preloadPayload = preload && preload.payload && typeof preload.payload === "object" ? preload.payload : {};
          const commonTreePayload = commonTreeSnapshot && commonTreeSnapshot.payload && typeof commonTreeSnapshot.payload === "object" ? commonTreeSnapshot.payload : {};
          const userOverlayPayload = userOverlaySnapshot && userOverlaySnapshot.payload && typeof userOverlaySnapshot.payload === "object" ? userOverlaySnapshot.payload : {};
          const treePayload = composeLoginVaultTreePayload(commonTreePayload, userOverlayPayload, username);
          loginVaultWarmupStats.composeMs += Math.max(0, browserTimingNow() - composeStartedAt);
          if (preloadPayload && typeof preloadPayload === "object" && clean(preload.etag)) {
            rememberLoginVaultPreloadCache(username, clean(preload.etag), preloadPayload);
          }
          if (commonTreePayload && typeof commonTreePayload === "object" && clean(commonTreeSnapshot && commonTreeSnapshot.etag)) {
            await rememberLoginVaultCommonTreePreloadCache(clean(commonTreeSnapshot.etag), commonTreePayload);
          }
          if (userOverlayPayload && typeof userOverlayPayload === "object" && clean(userOverlaySnapshot && userOverlaySnapshot.etag)) {
            await rememberLoginVaultTreePreloadCache(username, clean(userOverlaySnapshot.etag), userOverlayPayload);
          }
          if (
            typeof loadVocabRegistry === "function" &&
            clean(currentAuthUsername || "").toLowerCase() === username.toLowerCase()
          ) {
            // Added 2026-07-28: keep login CPU light; local Earn cache is used immediately and server refresh is not part of the login path.
            if (typeof applyVocabRegistryLocalCache === "function") {
              applyVocabRegistryLocalCache(username);
            }
          }
          const progressApplyStartedAt = browserTimingNow();
          if (preloadPayload.progress_snapshots && typeof preloadPayload.progress_snapshots === "object" && typeof rememberLessonVaultProgressSnapshot === "function") {
            Object.values(preloadPayload.progress_snapshots).forEach((snapshot) => {
              rememberLessonVaultProgressSnapshot(snapshot);
              if (typeof rememberPdfProgressLoginSnapshot === "function") {
                rememberPdfProgressLoginSnapshot(snapshot);
              }
            });
          } else if (preloadPayload.preload && preloadPayload.preload.progress_snapshot && typeof rememberPdfProgressLoginSnapshot === "function") {
            // Updated 2026-07-22: compact-v2 keeps the canonical nested snapshot without duplicating JSON bytes.
            rememberPdfProgressLoginSnapshot(preloadPayload.preload.progress_snapshot);
          }
          loginVaultWarmupStats.progressApplyMs += Math.max(0, browserTimingNow() - progressApplyStartedAt);
          const rowSyncStartedAt = browserTimingNow();
          if (preloadPayload.last_file_state && typeof applyServerLastFileState === "function") {
            applyServerLastFileState(preloadPayload.last_file_state, { render: true });
          }
          if (preloadPayload.preload && typeof applyLessonVaultProgressSnapshotToPayload === "function") {
            preloadPayload.preload = applyLessonVaultProgressSnapshotToPayload(preloadPayload.preload);
          }
          const treePreloadRows = Array.isArray(treePayload.rows) ? treePayload.rows : [];
          const treeEntryColumns = Array.isArray(treePayload.entry_columns) ? treePayload.entry_columns : [];
          if (treePreloadRows.length && !loginVaultCommonTreePreloadCache.payload) {
            loginVaultCommonTreePreloadCache.payload = treePayload.common || commonTreePayload || null;
          }
          loginVaultWarmupStats.rowSyncMs += Math.max(0, browserTimingNow() - rowSyncStartedAt);
          const finalizeStartedAt = browserTimingNow();
          loginVaultWarmupState = {
            ...loginVaultWarmupState,
            status: "ready",
            promise: null,
            payload: (preloadPayload.preload && !preloadPayload.preload.preload_meta_only)
              ? preloadPayload.preload
              : {
                ok: true,
                username,
                path: pathValue,
                preload_meta_only: true,
                progress_snapshot: preloadPayload.preload && preloadPayload.preload.progress_snapshot
                  ? preloadPayload.preload.progress_snapshot
                  : null,
              },
            treePreloadCount: Number(treePayload.row_count || treePreloadRows.length || 0) || 0,
            error: "",
            at: Date.now(),
          };
          loginVaultWarmupStats.finalizeMs += Math.max(0, browserTimingNow() - finalizeStartedAt);
          return loginVaultWarmupState;
        })().catch((error) => {
          if (serial !== loginVaultWarmupSerial || loginVaultWarmupUsername().toLowerCase() !== username.toLowerCase()) {
            return null;
          }
          const message = error && error.message ? error.message : "Chua nap truoc duoc Lesson Vault.";
          loginVaultWarmupState = {
            ...loginVaultWarmupState,
            status: "error",
            promise: null,
            payload: null,
            error: message,
            at: Date.now(),
          };
          if (reason !== "submit") {
            setAuthStatus(message, "error");
          }
          return loginVaultWarmupState;
        });
        loginVaultWarmupState.promise = promise;
        return promise;
      };

      const waitForLoginVaultWarmup = async (username = "", maxWaitMs = LOGIN_VAULT_WARMUP_WAIT_MS) => {
        const target = clean(username || loginVaultWarmupUsername()).toLowerCase();
        if (!target || clean(loginVaultWarmupState.username).toLowerCase() !== target || !loginVaultWarmupState.promise) {
          return loginVaultWarmupState;
        }
        const timeout = new Promise((resolve) => window.setTimeout(() => resolve(null), Math.max(120, Number(maxWaitMs || 0))));
        await Promise.race([loginVaultWarmupState.promise, timeout]).catch(() => null);
        return loginVaultWarmupState;
      };

      const stopServerBrowserAutoRefresh = () => {
        if (serverBrowserAutoRefreshTimer) {
          window.clearTimeout(serverBrowserAutoRefreshTimer);
          serverBrowserAutoRefreshTimer = 0;
        }
      };

      const stopServerBrowserManifestPoll = () => {
        if (serverBrowserManifestPollTimer) {
          window.clearTimeout(serverBrowserManifestPollTimer);
          serverBrowserManifestPollTimer = 0;
        }
      };

      const canAutoRefreshServerBrowser = () => Boolean(
        authToken &&
        serverBrowser &&
        !serverBrowser.hidden &&
        !(typeof pdfModeActive !== "undefined" && pdfModeActive) &&
        !document.documentElement.classList.contains("ft-space-pdf-mode") &&
        serverBrowserActivePanel === "vault" &&
        document.visibilityState !== "hidden"
      );

      const scheduleServerBrowserAutoRefresh = (delayMs = SERVER_BROWSER_AUTO_REFRESH_MS) => {
        stopServerBrowserAutoRefresh();
        if (!canAutoRefreshServerBrowser()) {
          return;
        }
        serverBrowserAutoRefreshTimer = window.setTimeout(async () => {
          serverBrowserAutoRefreshTimer = 0;
          if (!canAutoRefreshServerBrowser() || serverBrowserAutoRefreshBusy) {
            scheduleServerBrowserAutoRefresh();
            return;
          }
          serverBrowserAutoRefreshBusy = true;
          try {
            await loadServerDataPath(serverBrowserPath || "", true, serverTaskOwnerContext, {
              silent: true,
              autoRefresh: true,
            });
          } catch (error) {
          } finally {
            serverBrowserAutoRefreshBusy = false;
            scheduleServerBrowserAutoRefresh();
          }
        }, Math.max(1200, Number(delayMs || SERVER_BROWSER_AUTO_REFRESH_MS)));
      };

      const refreshVisibleServerBrowserAfterManifestChange = async (signature = "") => {
        const nextSignature = clean(signature || "");
        if (!nextSignature || serverBrowserManifestReloadSignature === nextSignature || serverBrowserAutoRefreshBusy || serverBrowserBusy) {
          return;
        }
        serverBrowserManifestReloadSignature = nextSignature;
        serverBrowserAutoRefreshBusy = true;
        try {
          setLoadStatus("Lesson Vault manifest updated. Refreshing current folder...");
          await loadServerDataPath(serverBrowserPath || "", true, serverTaskOwnerContext, {
            silent: true,
            fresh: true,
            autoRefresh: true,
          });
          setLoadStatus("Lesson Vault manifest updated.");
        } catch (error) {
        } finally {
          serverBrowserAutoRefreshBusy = false;
        }
      };

      const scheduleServerBrowserManifestPoll = (delayMs = SERVER_BROWSER_MANIFEST_POLL_MS) => {
        stopServerBrowserManifestPoll();
        if (!canAutoRefreshServerBrowser()) {
          return;
        }
        serverBrowserManifestPollTimer = window.setTimeout(async () => {
          serverBrowserManifestPollTimer = 0;
          if (!canAutoRefreshServerBrowser()) {
            return;
          }
          const previousSignature = getServerBrowserManifestSignature();
          try {
            const nextSignature = await refreshServerBrowserManifestSignatureIfNeeded({ force: true });
            if (nextSignature && previousSignature && nextSignature !== previousSignature) {
              await refreshVisibleServerBrowserAfterManifestChange(nextSignature);
            }
          } catch (error) {
          } finally {
            scheduleServerBrowserManifestPoll();
          }
        }, Math.max(3000, Number(delayMs || SERVER_BROWSER_MANIFEST_POLL_MS)));
      };

      const loadServerDataPath = async (relativePath = "", keepOpen = false, taskOwnerOverride = "", options = {}) => {
        if (!serverBrowser || !serverListNode) {
          return null;
        }
        const loadTimelineNow = () => browserTimingNow();
        let loadPhaseMark = loadTimelineNow();
        const recordLoadPhase = (phase = "") => {
          if (typeof window === "undefined" || typeof window.__ftRecordLoginTimelinePhase !== "function") {
            loadPhaseMark = loadTimelineNow();
            return;
          }
          const now = loadTimelineNow();
          window.__ftRecordLoginTimelinePhase(`loadServerDataPath:${phase}`, now - loadPhaseMark);
          loadPhaseMark = now;
        };
        const requestPath = normalizeServerPathValue(relativePath || "");
        const silent = Boolean(options && options.silent);
        const autoRefresh = Boolean(options && options.autoRefresh);
        const hydrateTaskBoardNow = Boolean(options && options.hydrateTaskBoardNow);
        const skipTaskBoardHydrate = Boolean(options && options.skipTaskBoardHydrate);
        const skipBackgroundVerify = Boolean(options && options.skipBackgroundVerify);
        const skipChildPrefetch = Boolean(options && options.skipChildPrefetch);
        // 2026-07-21: Space Task card focus is transient UI state; only an actual lesson open persists last-file state.
        const skipFolderPersist = Boolean(options && options.skipFolderPersist);
        const localCacheOnly = Boolean(options && options.localCacheOnly);
        const throwOnError = Boolean(options && options.throwOnError);
        const taskOwner = lessonVaultTaskOwnerForPath(requestPath, taskOwnerOverride || "");
        if (typeof window !== "undefined" && typeof window.__ftVaultRealtimeStart !== "function") {
          const state = window.__ftVaultRealtimeState = window.__ftVaultRealtimeState || {
            owner: "", path: "", revision: 0, timer: 0, channel: null, storageBound: false,
          };
          const applyRevision = (owner = "", revision = 0) => {
            const target = clean(owner).toLowerCase();
            const next = Math.max(0, Math.floor(Number(revision || 0) || 0));
            if (!target || target !== clean(state.owner).toLowerCase() || next <= state.revision) return;
            state.revision = next;
            if (state.path && document.visibilityState !== "hidden") {
              void loadServerDataPath(state.path, true, state.owner, { fresh: true, silent: true, autoRefresh: true, source: "vault_revision_delta" });
            }
          };
          // Added 2026-07-30: stale tabs must stop Vault polling when their auth session expires.
          const stop = () => {
            if (state.timer) {
              window.clearInterval(state.timer);
              state.timer = 0;
            }
            state.owner = "";
            state.path = "";
            state.revision = 0;
            window.__ftVaultRealtimeActive = false;
          };
          const poll = async () => {
            if (!state.owner || document.visibilityState === "hidden") return;
            try {
              const response = await fetchServerJson(`/server-data/vault-revision?user=${encodeURIComponent(state.owner)}`);
              const payload = response && response.payload && typeof response.payload === "object" ? response.payload : {};
              applyRevision(state.owner, payload.vault_revision);
            } catch (error) {
              if (Number(error && error.httpStatus || 0) === 401 || Number(error && error.httpStatus || 0) === 403) stop();
            }
          };
          window.__ftVaultRealtimeStart = (owner = "", path = "") => {
            state.owner = clean(owner || currentAuthUsername || "");
            state.path = normalizeServerPathValue(path || serverBrowserPath || "");
            window.__ftVaultRealtimeActive = Boolean(state.owner);
            if (!state.channel && typeof BroadcastChannel === "function") {
              try {
                state.channel = new BroadcastChannel("future-vault-revision-v1");
                state.channel.onmessage = (event) => applyRevision(event && event.data && event.data.owner, event && event.data && event.data.revision);
              } catch (error) { state.channel = null; }
            }
            if (!state.timer) state.timer = window.setInterval(() => void poll(), 5000);
            void poll();
          };
          window.__ftVaultRealtimePublish = (payload = {}) => {
            const owner = clean(payload.owner || state.owner);
            const revision = Number(payload.revision || 0) || 0;
            if (owner.toLowerCase() === clean(state.owner).toLowerCase()) state.revision = Math.max(state.revision, revision);
            try { localStorage.setItem("future-vault-revision", JSON.stringify({ owner, revision, at: Date.now() })); } catch (error) {}
            try { state.channel && state.channel.postMessage({ owner, revision }); } catch (error) {}
          };
          if (!state.storageBound) {
            state.storageBound = true;
            window.addEventListener("storage", (event) => {
              if (event.key !== "future-vault-revision") return;
              try { const row = JSON.parse(event.newValue || "{}"); applyRevision(row.owner, row.revision); } catch (error) {}
            });
          }
        }
        if (typeof window !== "undefined" && typeof window.__ftVaultRealtimeStart === "function") {
          window.__ftVaultRealtimeStart(clean(taskOwner || currentAuthUsername || ""), requestPath);
        }
        let forceFresh = Boolean(options && options.fresh);
        recordLoadPhase("init");
        if (!autoRefresh && !silent && !(options && options.skipRouteLeaveFlush) && typeof window.__ftFlushSpaceVProgressBeforeBack === "function") {
          window.__ftSpaceVRouteLeaveFlushStartedAt = Date.now();
          const flushResult = await window.__ftFlushSpaceVProgressBeforeBack({ notice: true });
          if (flushResult && flushResult.ok === false) {
            return null;
          }
        }
        if (!autoRefresh && !silent && !(options && options.skipRouteLeaveFlush) && typeof window.__ftFlushSpacePdfProgressBeforeBack === "function") {
          try {
            window.__ftFlushSpacePdfProgressBeforeBack();
          } catch (error) {
          }
        }
        if (!autoRefresh && typeof window.__ftClearSpaceWOverlaysForRouteLeave === "function") {
          window.__ftClearSpaceWOverlaysForRouteLeave();
        }
        recordLoadPhase("route-leave-flush");
        const loadKey = serverBrowserLoadKey(requestPath, taskOwner);
        // Supersede any in-flight load so fast open/back/open no longer renders
        // a stale folder or blocks behind an older request.
        const mySerial = ++serverBrowserLoadSerial;
        const isStaleLoad = () => mySerial !== serverBrowserLoadSerial;
        if (serverBrowserActiveAbort) {
          try { serverBrowserActiveAbort.abort(); } catch (abortError) {}
          serverBrowserActiveAbort = null;
        }
        const loadAbort = (typeof AbortController !== "undefined") ? new AbortController() : null;
        serverBrowserActiveAbort = loadAbort;
        recordLoadPhase("abort-setup");
        if (!forceFresh && !autoRefresh && serverBrowserRecentLoadKey === loadKey && Date.now() - serverBrowserRecentLoadAt < 900) {
          const recentCachedRow = getCachedServerBrowserListRow(requestPath, taskOwner, { allowStale: localCacheOnly });
          if (recentCachedRow && recentCachedRow.payload) {
            if (localCacheOnly) {
              window.__ftLessonVaultProgressHydrationPausedUntil = Date.now() + 15000;
            }
            const renderPayload = localCacheOnly ? { ...recentCachedRow.payload, local_cache_only: true } : recentCachedRow.payload;
            if (!keepOpen) {
              serverBrowser.hidden = false;
              syncServerWorkspaceOpenState();
            }
            renderServerDataList(renderPayload);
            if (!skipFolderPersist && typeof rememberLessonVaultFolder === "function") {
              rememberLessonVaultFolder(requestPath, taskOwner, localCacheOnly ? "folder_restore_local_cache" : "folder_restore_cache");
            }
            if (!skipTaskBoardHydrate && shouldHydrateDeferredTaskBoardImmediately(renderPayload, requestPath, hydrateTaskBoardNow)) {
              hydrateDeferredTaskBoardNow(renderPayload);
            } else if (!skipTaskBoardHydrate) {
              scheduleDeferredTaskBoardHydrate(renderPayload);
            }
            if (!skipChildPrefetch) {
              prefetchServerBrowserChildFolders(renderPayload, taskOwner);
            }
            recordLoadPhase("recent-cache-return");
            return renderPayload;
          }
        }
        const currentRoute = futureAppRouteFromLocation();
        if (!currentRoute || currentRoute === "lesson_vault") {
          const routeState = futureRouteStateFromLocation();
          const routeFile = currentRoute === "lesson_vault" ? cleanFutureRoutePathValue(routeState.file || "") : "";
          const keepRouteFile = Boolean(routeFile && futureRouteParentForPath(routeFile) === requestPath);
          updateFutureAppRoute("lesson_vault", {
            tree: requestPath,
            file: keepRouteFile ? routeFile : "",
            process: keepRouteFile ? (routeState.process || futureRouteSpaceForFilePath(routeFile)) : "",
            task_owner: taskOwner,
            replace: Boolean(keepOpen || currentRoute === "lesson_vault"),
          });
        }
        if (!keepOpen) {
          serverBrowser.hidden = false;
          syncServerWorkspaceOpenState();
        }
        setServerBrowserBackControl(requestPath, serverParentPathForFile(requestPath), requestPath ? taskOwner : "");
        recordLoadPhase("route-ui");
        let cachedRow = forceFresh ? null : getCachedServerBrowserListRow(requestPath, taskOwner, { allowStale: localCacheOnly });
        let cachedPayload = cachedRow && cachedRow.payload ? cachedRow.payload : null;
        if (!cachedPayload && localCacheOnly && typeof loginVaultTreeFolderPayloadFromCache === "function") {
          cachedPayload = loginVaultTreeFolderPayloadFromCache(requestPath, taskOwner);
          if (cachedPayload && typeof rememberServerBrowserList === "function") {
            rememberServerBrowserList(requestPath, taskOwner, cachedPayload);
          }
        }
        if (
          cachedPayload
          && !localCacheOnly
          && typeof serverBrowserLinkedFolderSnapshotNeedsHydration === "function"
          && serverBrowserLinkedFolderSnapshotNeedsHydration(requestPath, taskOwner, cachedPayload)
        ) {
          cachedRow = null;
          cachedPayload = null;
        }
        let loadingPlaceholderTimer = 0;
        // User-initiated navigation (QM-Home, back, breadcrumb, recent file,
        // folder open) should not block on manifest revalidation. Serve the
        // cached folder immediately and verify/refresh in the background.
        if (cachedPayload && !forceFresh && !autoRefresh) {
          if (localCacheOnly) {
            window.__ftLessonVaultProgressHydrationPausedUntil = Date.now() + 15000;
          }
          const renderPayload = localCacheOnly ? { ...cachedPayload, local_cache_only: true } : cachedPayload;
          renderServerDataList(renderPayload);
          if (!localCacheOnly && !skipTaskBoardHydrate && shouldHydrateDeferredTaskBoardImmediately(renderPayload, requestPath, hydrateTaskBoardNow)) {
            hydrateDeferredTaskBoardNow(renderPayload);
          } else if (!localCacheOnly && !skipTaskBoardHydrate) {
            scheduleDeferredTaskBoardHydrate(renderPayload);
          }
          if (!skipFolderPersist && typeof rememberLessonVaultFolder === "function") {
            rememberLessonVaultFolder(requestPath, taskOwner, localCacheOnly ? "folder_restore_local_cache" : "folder_restore_cache");
          }
          if (!skipChildPrefetch) {
            prefetchServerBrowserChildFolders(renderPayload, taskOwner);
          }
          rememberServerPath(cachedPayload && cachedPayload.path || requestPath);
          if (!silent) {
            setLoadStatus("Loaded lesson vault from cache.");
          }
          serverBrowserRecentLoadKey = loadKey;
          serverBrowserRecentLoadAt = Date.now();
          if (serverBrowserActiveAbort === loadAbort) {
            serverBrowserActiveAbort = null;
          }
          if (skipBackgroundVerify) {
            scheduleServerBrowserAutoRefresh();
            scheduleServerBrowserManifestPoll();
            recordLoadPhase("cache-return-skip-verify");
            return renderPayload;
          }
          const cachedAt = Number(cachedRow.at || 0);
          const shouldHydrateCachedPayload = Boolean(cachedPayload && cachedPayload.preauth);
          void (async () => {
            try {
              const previousSignature = getServerBrowserManifestSignature();
              const nextSignature = await refreshServerBrowserManifestSignatureIfNeeded();
              if (isStaleLoad()) {
                return;
              }
              const stillCached = getCachedServerBrowserListRow(requestPath, taskOwner);
              const signatureChanged = Boolean(nextSignature && previousSignature && nextSignature !== previousSignature);
              const cacheAge = stillCached ? Date.now() - Number(stillCached.at || cachedAt) : Infinity;
              if (!stillCached || signatureChanged || cacheAge >= SERVER_BROWSER_LIST_REFRESH_MIN_MS || shouldHydrateCachedPayload) {
                await loadServerDataPath(requestPath, true, taskOwner, {
                  silent: true,
                  fresh: shouldHydrateCachedPayload,
                  autoRefresh: true,
                });
              }
            } catch (error) {
            }
          })();
          scheduleServerBrowserAutoRefresh();
          scheduleServerBrowserManifestPoll();
          recordLoadPhase("cache-return-with-background");
          return renderPayload;
        }
        if (cachedPayload) {
          if (localCacheOnly) {
            window.__ftLessonVaultProgressHydrationPausedUntil = Date.now() + 15000;
          }
          const renderPayload = localCacheOnly ? { ...cachedPayload, local_cache_only: true } : cachedPayload;
          renderServerDataList(renderPayload);
          if (!localCacheOnly && !skipTaskBoardHydrate && shouldHydrateDeferredTaskBoardImmediately(renderPayload, requestPath, hydrateTaskBoardNow)) {
            hydrateDeferredTaskBoardNow(renderPayload);
          } else if (!localCacheOnly && !skipTaskBoardHydrate) {
            scheduleDeferredTaskBoardHydrate(renderPayload);
          }
          if (!skipChildPrefetch) {
            prefetchServerBrowserChildFolders(renderPayload, taskOwner);
          }
          recordLoadPhase("stale-cache-render");
          await refreshServerBrowserManifestSignatureIfNeeded();
          recordLoadPhase("manifest-refresh");
          if (isStaleLoad()) {
            return cachedPayload;
          }
          const verifiedCachedRow = forceFresh ? null : getCachedServerBrowserListRow(requestPath, taskOwner);
          if (!verifiedCachedRow || !verifiedCachedRow.payload) {
            cachedRow = null;
            cachedPayload = null;
            if (!silent) {
              setLoadStatus("Lesson Vault manifest changed. Checking server...");
            }
          }
        }
        if (cachedPayload) {
          const cacheAge = Date.now() - Number(cachedRow.at || 0);
          const waitMs = SERVER_BROWSER_LIST_REFRESH_MIN_MS - cacheAge;
          if (waitMs > 0) {
            rememberServerPath(cachedPayload && cachedPayload.path || requestPath);
            if (!silent) {
              setLoadStatus("Loaded lesson vault from cache.");
            }
            if (!autoRefresh) {
              scheduleServerBrowserAutoRefresh();
              scheduleServerBrowserManifestPoll();
            }
            serverBrowserRecentLoadKey = loadKey;
            serverBrowserRecentLoadAt = Date.now();
            recordLoadPhase("verified-cache-return");
            return cachedPayload;
          } else if (!silent) {
            setLoadStatus("Loaded lesson vault from cache. Checking server...");
          }
        } else if (localCacheOnly) {
          // Added 2026-07-15: lesson Back may repaint from the current in-memory rows only; it must not fall through to /server-data/list.
          window.__ftLessonVaultProgressHydrationPausedUntil = Date.now() + 15000;
          const localPayload = {
            ok: true,
            path: requestPath,
            task_owner: taskOwner,
            entries: Array.isArray(serverCurrentEntries) ? serverCurrentEntries : [],
            local_cache_only: true,
          };
          if (localPayload.entries.length) {
            renderServerDataList(localPayload);
            if (!skipFolderPersist && typeof rememberLessonVaultFolder === "function") {
              rememberLessonVaultFolder(requestPath, taskOwner, "folder_restore_local_only");
            }
            rememberServerPath(requestPath);
            serverBrowserRecentLoadKey = loadKey;
            serverBrowserRecentLoadAt = Date.now();
          }
          if (serverBrowserActiveAbort === loadAbort) {
            serverBrowserActiveAbort = null;
          }
          recordLoadPhase("local-cache-return");
          return localPayload;
        } else {
          if (!silent) {
            loadingPlaceholderTimer = window.setTimeout(() => {
              setServerBrowserLoading("Reading QM-Home...");
            }, 900);
          }
        }
        try {
          const query = new URLSearchParams();
          query.set("path", requestPath);
          if (taskOwner) {
            query.set("task_owner", taskOwner);
          }
          query.set("defer_task_board", "1");
          if (!requestPath || normalizeTaskPath(requestPath) === "common") {
            query.set("include_space_task", "1");
          }
          if (forceFresh) {
            query.set("fresh", "1");
          }
          if (options && options.source) {
            query.set("client_source", clean(options.source || ""));
          }
          const result = await fetchServerJson(`/server-data/list?${query.toString()}`, loadAbort ? { signal: loadAbort.signal } : {});
          recordLoadPhase("fetch-list");
          if (loadingPlaceholderTimer) {
            window.clearTimeout(loadingPlaceholderTimer);
            loadingPlaceholderTimer = 0;
          }
          // A newer open/back superseded this load while it was in flight.
          if (isStaleLoad()) {
            rememberServerBrowserList(requestPath, taskOwner, result.payload);
            return result.payload || null;
          }
          if (serverBrowserActiveAbort === loadAbort) {
            serverBrowserActiveAbort = null;
          }
          const resolvedPath = clean(result.payload && result.payload.path || requestPath);
          rememberServerBrowserList(resolvedPath || requestPath, taskOwner, result.payload);
          rememberServerPath(resolvedPath);
          // Added 2026-07-21: replace stale restored folder routes with the nearest existing server folder.
          if (normalizeTaskPath(resolvedPath) !== normalizeTaskPath(requestPath)) {
            updateFutureAppRoute("lesson_vault", {
              tree: resolvedPath,
              task_owner: taskOwner,
              replace: true,
            });
          }
          if (!silent) {
            setLoadStatus(`Connected to ${serverDisplayPathLabel(result.payload && result.payload.path || requestPath)}.`);
          }
          await new Promise((resolve) => window.requestAnimationFrame(resolve));
          recordLoadPhase("before-server-render");
          renderServerDataList(result.payload);
          recordLoadPhase("server-render");
          if (!skipFolderPersist && typeof rememberLessonVaultFolder === "function") {
            rememberLessonVaultFolder(resolvedPath, taskOwner, "folder_restore_server");
          }
          if (!skipTaskBoardHydrate && shouldHydrateDeferredTaskBoardImmediately(result.payload, resolvedPath, hydrateTaskBoardNow)) {
            hydrateDeferredTaskBoardNow(result.payload || {});
          } else if (!skipTaskBoardHydrate) {
            scheduleDeferredTaskBoardHydrate(result.payload || {});
          }
          serverBrowserRecentLoadKey = loadKey;
          serverBrowserRecentLoadAt = Date.now();
          if (!skipChildPrefetch) {
            prefetchServerBrowserChildFolders(result.payload, taskOwner);
          }
          if (!autoRefresh) {
            scheduleServerBrowserAutoRefresh();
            scheduleServerBrowserManifestPoll();
          }
          recordLoadPhase("server-return");
          return result.payload || null;
        } catch (error) {
          if (loadingPlaceholderTimer) {
            window.clearTimeout(loadingPlaceholderTimer);
            loadingPlaceholderTimer = 0;
          }
          if (serverBrowserActiveAbort === loadAbort) {
            serverBrowserActiveAbort = null;
          }
          // A newer open/back aborted this load on purpose. Stay silent so the
          // superseded request never flashes an error over the current folder.
          const wasAborted = Boolean(error && (clean(error.name).toLowerCase() === "aborterror" || error.isAbortError));
          if (isStaleLoad() || wasAborted) {
            return cachedPayload || null;
          }
          const diag = typeof classifyServerJsonError === "function"
            ? classifyServerJsonError(error, requestPath)
            : { kind: "unknown", label: "unknown" };
          const friendlyByKind = {
            network: "Mat ket noi mang. Khong tai duoc Lesson Vault tu server.",
            timeout: "Server phan hoi qua lau (timeout) khi tai Lesson Vault.",
            http: "Server tra ve loi khi tai Lesson Vault.",
            server_app: "Server bao loi xu ly khi tai Lesson Vault.",
            client: "Loi phia trinh duyet khi tai Lesson Vault.",
            unknown: "Khong tai duoc Lesson Vault.",
          };
          console.warn("[Future] Lesson Vault server fallback failed", {
            kind: diag.kind,
            label: diag.label,
            path: requestPath,
            taskOwner: taskOwner || "",
            httpStatus: error && error.httpStatus ? error.httpStatus : null,
            usedCache: Boolean(cachedPayload),
            online: typeof navigator !== "undefined" ? navigator.onLine : null,
            at: new Date().toISOString(),
            message: error && error.message ? error.message : String(error),
          });
          if (cachedPayload) {
            if (!silent) {
              setLoadStatus(`Dang dung Lesson Vault tu cache. ${friendlyByKind[diag.kind] || friendlyByKind.unknown}`, true);
            }
            if (!autoRefresh) {
              scheduleServerBrowserAutoRefresh();
              scheduleServerBrowserManifestPoll();
            }
            return cachedPayload;
          }
          const message = friendlyByKind[diag.kind] || (error && error.message ? error.message : "Could not read QM-Home.");
          if (!silent) {
            showServerBrowserPathError(requestPath, message, taskOwner);
            setLoadStatus(message, true);
          }
          if (throwOnError) {
            throw error;
          }
          return null;
        }
      };

      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && canAutoRefreshServerBrowser()) {
          scheduleServerBrowserAutoRefresh();
          scheduleServerBrowserManifestPoll();
        } else {
          stopServerBrowserAutoRefresh();
          stopServerBrowserManifestPoll();
        }
      });

      const openServerBrowser = () => {
        const localFolder = typeof getStoredLessonVaultFolderState === "function" ? getStoredLessonVaultFolderState(serverTaskOwnerContext || currentAuthUsername || "") : null;
        const targetTree = serverBrowserPath || (localFolder && localFolder.path) || getStoredServerPath() || "";
        const targetOwner = clean((localFolder && localFolder.task_owner) || lessonVaultTaskOwnerForPath(targetTree, serverTaskOwnerContext || ""));
        window.__ftLessonVaultLocalRouteUntil = Date.now() + 15000;
        updateFutureAppRoute("lesson_vault", { tree: targetTree, task_owner: targetOwner });
        setServerBrowserPanel("vault");
        loadServerDataPath(targetTree, false, targetOwner, {
          // Added 2026-07-28: Lesson Vault Home restores the authenticated preload locally.
          localCacheOnly: true,
          skipBackgroundVerify: true,
          skipChildPrefetch: true,
          skipTaskBoardHydrate: true,
          skipRouteLeaveFlush: true,
          source: "lesson_vault_home_local_cache",
        });
        window.setTimeout(() => startTaskNoticeImmediatePolling(), 0);
      };

      const openServerBrowserAfterAuth = async (options = {}) => {
        const openTimelineNow = () => browserTimingNow();
        let openPhaseMark = openTimelineNow();
        const recordOpenPhase = (phase = "") => {
          if (typeof window === "undefined" || typeof window.__ftRecordLoginTimelinePhase !== "function") {
            openPhaseMark = openTimelineNow();
            return;
          }
          const now = openTimelineNow();
          window.__ftRecordLoginTimelinePhase(`openServerBrowserAfterAuth:${phase}`, now - openPhaseMark);
          openPhaseMark = now;
        };
        const revealAfterLoad = Boolean(options && options.revealAfterLoad);
        const silent = Boolean(options && options.silent);
        const fresh = Boolean(options && options.fresh);
        const throwOnError = Boolean(options && options.throwOnError);
        const skipLastFileSync = Boolean(options && options.skipLastFileSync);
        const skipTaskBoardHydrate = Boolean(options && options.skipTaskBoardHydrate);
        const skipBackgroundVerify = Boolean(options && options.skipBackgroundVerify);
        const skipChildPrefetch = Boolean(options && options.skipChildPrefetch);
        serverBrowserAuthOpenBusy = true;
        try {
          if (!skipLastFileSync && typeof syncServerLastFileFromServer === "function") {
            await syncServerLastFileFromServer({ render: true });
          }
          recordOpenPhase("last-file-sync");
          const routeState = futureRouteStateFromLocation();
          const restoreTarget = typeof resolveLessonVaultRestoreTarget === "function"
            ? await resolveLessonVaultRestoreTarget({
              routeTree: routeState.route === "lesson_vault" ? routeState.tree : "",
              routeTaskOwner: routeState.route === "lesson_vault" ? routeState.task_owner : "",
            })
            : {
              tree: routeState.route === "lesson_vault" ? routeState.tree : (getStoredServerPath() || ""),
              task_owner: routeState.route === "lesson_vault" ? routeState.task_owner : "",
            };
          recordOpenPhase("resolve-target");
          const targetTree = restoreTarget.tree || "";
          const targetOwner = clean(restoreTarget.task_owner || "");
          const warmupPayload = !fresh && loginVaultWarmupState && typeof loginVaultWarmupState.payload === "object"
            ? loginVaultWarmupState.payload
            : null;
          const warmupPath = normalizeServerPathValue(
            warmupPayload && (warmupPayload.path || loginVaultWarmupState.path || "")
          );
          const canUseWarmupPayload = Boolean(
            warmupPayload
            && clean(loginVaultWarmupState.status || "").toLowerCase() === "ready"
            && clean(loginVaultWarmupState.username || "").toLowerCase() === clean(currentAuthUsername || "").toLowerCase()
            && warmupPath === normalizeServerPathValue(targetTree)
            && (
              Array.isArray(warmupPayload.entries) && warmupPayload.entries.length
              || Array.isArray(warmupPayload.rows) && warmupPayload.rows.length
              || !warmupPayload.preload_meta_only
            )
          );
          updateFutureAppRoute("lesson_vault", {
            tree: targetTree,
            file: routeState.route === "lesson_vault" ? routeState.file : "",
            process: routeState.route === "lesson_vault" ? routeState.process : "",
            task_owner: targetOwner || (routeState.route === "lesson_vault" ? routeState.task_owner : ""),
            replace: futureAppRouteFromLocation() === "lesson_vault",
          });
          serverBrowserPath = "";
          setServerBrowserPanel("vault");
          recordOpenPhase("route-panel");
          if (revealAfterLoad && serverBrowser) {
            serverBrowser.hidden = true;
            syncServerWorkspaceOpenState();
          }
          if (canUseWarmupPayload) {
            rememberServerBrowserList(targetTree, clean(warmupPayload.task_owner || ""), warmupPayload);
          }
          recordOpenPhase("warmup-cache");
          const payload = await loadServerDataPath(targetTree, revealAfterLoad, targetOwner || (routeState.route === "lesson_vault" ? routeState.task_owner : ""), {
            silent,
            fresh: fresh || (canUseWarmupPayload && !skipBackgroundVerify),
            hydrateTaskBoardNow: !skipTaskBoardHydrate,
            skipTaskBoardHydrate,
            skipBackgroundVerify,
            skipChildPrefetch,
            throwOnError,
          });
          recordOpenPhase("load-path");
          if (revealAfterLoad && serverBrowser) {
            serverBrowser.hidden = false;
            syncServerWorkspaceOpenState();
            startTaskNoticeImmediatePolling();
          }
          if (routeState.route === "lesson_vault" && routeState.file) {
            setSelectedTaskPath(routeState.file);
          }
          if (!skipTaskBoardHydrate && serverBrowser && !serverBrowser.hidden) {
            startTaskNoticeImmediatePolling();
          }
          recordOpenPhase("finalize");
          return payload;
        } finally {
          serverBrowserAuthOpenBusy = false;
        }
      };

      const schedulePostAuthLessonVaultHydration = (payload = null, targetOwner = "") => {
        if (!payload || typeof payload !== "object") {
          return;
        }
        const owner = clean(targetOwner || payload.task_owner || payload.username || currentAuthUsername || "");
        const run = () => {
          try {
            if (shouldHydrateDeferredTaskBoardImmediately(payload, payload.path || "", false)) {
              hydrateDeferredTaskBoardNow(payload);
            } else {
              scheduleDeferredTaskBoardHydrate(payload);
            }
          } catch (error) {
          }
          try {
            prefetchServerBrowserChildFolders(payload, owner);
          } catch (error) {
          }
          try {
            if (typeof loadServerDataPath === "function") {
              void loadServerDataPath(payload.path || serverBrowserPath || "", true, owner, {
                silent: true,
                // 2026-07-27: the authenticated open just loaded this folder; reuse it instead of a second post-login GET.
                localCacheOnly: true,
                skipRouteLeaveFlush: true,
                skipBackgroundVerify: true,
                skipTaskBoardHydrate: true,
                skipChildPrefetch: true,
              }).catch(() => {});
            }
          } catch (error) {
          }
        };
        if (typeof window.requestIdleCallback === "function") {
          window.requestIdleCallback(run, { timeout: 1800 });
        } else {
          window.setTimeout(run, 900);
        }
      };

      const handleFutureRouteNavigation = () => {
        const routeState = futureRouteStateFromLocation();
        updateFutureDocumentTitle(routeState);
        const route = routeState.route;
        if (route === "login") {
          const routeBackdropToken = clean(authToken || getStoredAuthToken());
          const routeBackdropUser = clean(currentAuthUsername || (() => {
            try {
              return localStorage.getItem(AUTH_USER_KEY) || "";
            } catch (error) {
              return "";
            }
          })() || (authUser && authUser.value) || "");
          try {
            sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (error) {
          }
          clearStoredAuthToken();
          authToken = "";
          reloadSessionRestorePending = false;
          showLoginGate("Hay dang nhap de bat dau.", {
            backdropToken: routeBackdropToken,
            backdropUser: routeBackdropUser,
          });
          return;
        }
        if (route === "lesson_vault" && authToken) {
          if (serverBrowserAuthOpenBusy) {
            return;
          }
          setServerBrowserPanel("vault");
          void (async () => {
            try {
              const localRouteOnly = Number(window.__ftLessonVaultLocalRouteUntil || 0) > Date.now();
              if (!localRouteOnly && typeof syncServerLastFileFromServer === "function") {
                await syncServerLastFileFromServer({ render: true });
              }
              const restoreTarget = typeof resolveLessonVaultRestoreTarget === "function"
                ? await resolveLessonVaultRestoreTarget({
                  routeTree: routeState.tree,
                  routeTaskOwner: routeState.task_owner,
                })
                : {
                  tree: routeState.tree || serverBrowserPath || getStoredServerPath() || "",
                  task_owner: routeState.task_owner || "",
                };
              const routeTargetOwner = clean(restoreTarget.task_owner || routeState.task_owner || "");
              await loadServerDataPath(restoreTarget.tree || routeState.tree || serverBrowserPath || getStoredServerPath() || "", false, routeTargetOwner, localRouteOnly ? {
                // Added 2026-07-15: route sync after a breadcrumb click must not re-fetch the same Lesson Vault folder from Server 2.
                skipBackgroundVerify: true,
                skipChildPrefetch: true,
                skipTaskBoardHydrate: !lessonTaskPanelNeedsOwnerHydration(routeTargetOwner),
                skipRouteLeaveFlush: true,
                localCacheOnly: true,
                source: "lesson_vault_route_local_cache",
              } : {});
              if (routeState.file) {
                setSelectedTaskPath(routeState.file);
              } else if (typeof getStoredServerFile === "function") {
                const syncedFile = getStoredServerFile();
                if (syncedFile) {
                  setSelectedTaskPath(syncedFile);
                }
              }
            } catch (_error) {
              const localRouteOnly = Number(window.__ftLessonVaultLocalRouteUntil || 0) > Date.now();
              const restoreTarget = typeof resolveLessonVaultRestoreTarget === "function"
                ? await resolveLessonVaultRestoreTarget({
                  routeTree: routeState.tree,
                  routeTaskOwner: routeState.task_owner,
                })
                : {
                  tree: routeState.tree || serverBrowserPath || getStoredServerPath() || "",
                  task_owner: routeState.task_owner || "",
                };
              const routeTargetOwner = clean(restoreTarget.task_owner || routeState.task_owner || "");
              loadServerDataPath(restoreTarget.tree || routeState.tree || serverBrowserPath || getStoredServerPath() || "", false, routeTargetOwner, localRouteOnly ? {
                skipBackgroundVerify: true,
                skipChildPrefetch: true,
                skipTaskBoardHydrate: !lessonTaskPanelNeedsOwnerHydration(routeTargetOwner),
                skipRouteLeaveFlush: true,
                localCacheOnly: true,
                source: "lesson_vault_route_local_cache_error",
              } : {});
              if (routeState.file) {
                setSelectedTaskPath(routeState.file);
              }
            }
          })();
          return;
        }
        if (route && route.startsWith("space_") && routeState.file && authToken) {
          reloadSessionRestorePending = true;
          void restoreLessonAfterReloadSession({
            mode: routeState.process || route,
            path: routeState.file,
            browserPath: routeState.tree || futureRouteParentForPath(routeState.file),
            source: {
              source: "server",
              path: routeState.file,
              name: routeState.file.split("/").pop() || routeState.file,
            },
          }).finally(() => {
            reloadSessionRestorePending = false;
          });
        }
      };

      const spaceWCurrentNodeProgressState = () => ({
        index: currentNodeIndex,
        input: answerInput.value,
        feedback: feedbackNode.textContent,
        wordHintedKeys: Array.from(wordHintedKeys),
        listenCount: completedListenCount,
        nextPanelCanShow,
        speakStepCompleted: spaceWSpeakSkipSessionApproved ? false : speakStepCompleted,
        speakStarCount,
        grammarStepCompleted,
        grammarState: {
          active: Boolean(grammarState.active),
          index: Number(grammarState.index || 0) || 0,
          revision: Number(grammarState.revision || 0) || 0,
          awaitingStart: Boolean(grammarState.awaitingStart),
          awaitingCorrectAdvance: Boolean(grammarState.awaitingCorrectAdvance),
        },
        grammarFirstAttempted: Array.from(grammarFirstAttempted),
        grammarFirstTryCorrect: Array.from(grammarFirstTryCorrect),
        ipaLive: ipaPanel.classList.contains("is-live"),
        scoreLive: scorePanel.classList.contains("is-live"),
        hintLive: hintPanel.classList.contains("is-live"),
        aboutLive: aboutPanel && aboutPanel.classList.contains("is-live"),
        aboutIndex,
        aboutUnlocked: aboutUnlockedForCurrentNode,
        speakLive: speakPanel.classList.contains("is-live"),
        grammarLive: grammarPanel.classList.contains("is-live"),
        mobileActivePanelKey,
        mobileUnlockedPanels: Array.from(mobileUnlockedPanels),
        reviewModeActive,
        reviewCurrentHadError,
        reviewSpeakCompleted: spaceWSpeakSkipSessionApproved ? false : reviewSpeakCompleted,
        wrongAttempts,
        updatedAt: new Date().toISOString(),
      });

      const mergedSpaceWNodeProgress = () => {
        const merged = { ...(spaceWNodeProgress || {}) };
        if (currentNode && lessonNodes.length) {
          merged[String(currentNodeIndex)] = spaceWCurrentNodeProgressState();
        }
        return merged;
      };

      const runtimeSnapshot = () => ({
        nodes: lessonNodes.length ? lessonNodes : [currentNode || {
          vi: questionNode.textContent,
          en: englishNode.textContent,
          ipa: ipaNode.textContent,
          voice: voiceHint || voiceSelect.value,
        }],
        index: currentNodeIndex,
        input: answerInput.value,
        wordHintedKeys: Array.from(wordHintedKeys),
        feedback: feedbackNode.textContent,
        voiceHint,
        selectedVoice: voiceSelect.value,
        ipaLive: ipaPanel.classList.contains("is-live"),
        scoreLive: scorePanel.classList.contains("is-live"),
        hintLive: hintPanel.classList.contains("is-live"),
        aboutLive: aboutPanel && aboutPanel.classList.contains("is-live"),
        aboutIndex,
        aboutUnlocked: aboutUnlockedForCurrentNode,
        speakLive: speakPanel.classList.contains("is-live"),
        grammarLive: grammarPanel.classList.contains("is-live"),
        mobileActivePanelKey,
        mobileUnlockedPanels: Array.from(mobileUnlockedPanels),
        loadHidden: loadGate.classList.contains("is-hidden"),
        listenCount: completedListenCount,
        nextPanelCanShow,
        speakStepCompleted: spaceWSpeakSkipSessionApproved ? false : speakStepCompleted,
        speakStarCount,
        grammarStepCompleted,
        reviewModeActive,
        reviewQueue,
        reviewMastered: Array.from(reviewMasteredIndexes),
        reviewCurrentHadError,
        reviewSpeakCompleted: spaceWSpeakSkipSessionApproved ? false : reviewSpeakCompleted,
        reviewFinished,
        runId: spaceWActiveRunId,
        spaceWTrainModeLocked,
        spaceWTrainModeExpanded,
        spaceWTrainModeRootCount,
        spaceWTrainModeBatch,
        lessonSource: currentLessonSource,
        lessonCompletionSent,
        effects: lessonEffects,
        nodeProgress: mergedSpaceWNodeProgress(),
        spaceWCache: currentSpaceWCache && currentSpaceWCache.identity ? {
          identity: currentSpaceWCache.identity,
          progressKey: currentSpaceWCache.progressKey,
          voiceKey: currentSpaceWCache.voiceKey,
        } : null,
      });

      const canSaveSpaceWProgress = () => Boolean(
        currentSpaceWCache &&
        currentSpaceWCache.progressKey &&
        lessonNodes.length &&
        currentNode &&
        !questionModeActive &&
        !vocabModeActive &&
        loadGate.classList.contains("is-hidden")
      );

