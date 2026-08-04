
      const FT_EDITABLE_SELECTOR = "input, textarea, [role='textbox'], [contenteditable='true'], [contenteditable=''], [contenteditable]:not([contenteditable='false'])";
      const ftEditableTarget = (eventTarget) => {
        const direct = eventTarget && eventTarget.closest ? eventTarget.closest(FT_EDITABLE_SELECTOR) : null;
        if (direct) {
          return direct;
        }
        try {
          const active = document.activeElement;
          return active && active.matches && active.matches(FT_EDITABLE_SELECTOR) ? active : null;
        } catch (error) {
          return null;
        }
      };
      const ftSelectEditable = (node) => {
        if (!node) {
          return false;
        }
        try {
          if (node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement) {
            node.focus({ preventScroll: true });
            node.select();
            return true;
          }
          node.focus({ preventScroll: true });
          const selection = window.getSelection && window.getSelection();
          if (!selection || !document.createRange) {
            return false;
          }
          const range = document.createRange();
          range.selectNodeContents(node);
          selection.removeAllRanges();
          selection.addRange(range);
          return true;
        } catch (error) {
          return false;
        }
      };
      const ftStopProtectedBrowserAction = (event, message = "") => {
        try {
          event.preventDefault();
          event.stopImmediatePropagation();
          event.stopPropagation();
        } catch (error) {}
        try {
          const selection = window.getSelection && window.getSelection();
          if (selection && selection.removeAllRanges) {
            selection.removeAllRanges();
          }
        } catch (error) {}
        if (message) {
          try {
            document.documentElement.dataset.ftGuardMessage = message;
          } catch (error) {}
        }
        return false;
      };
      const ftProtectedShortcut = (event) => {
        const key = String(event.key || "").toLowerCase();
        const code = String(event.code || "").toLowerCase();
        const ctrlOrMeta = Boolean(event.ctrlKey || event.metaKey);
        const shift = Boolean(event.shiftKey);
        const alt = Boolean(event.altKey);
        if (key === "f12" || code === "f12") {
          return "Developer tools are disabled.";
        }
        if (ctrlOrMeta && ["s", "u", "p"].includes(key)) {
          return "Browser save/source/print shortcuts are disabled.";
        }
        if (ctrlOrMeta && shift && ["i", "j", "c", "k", "s"].includes(key)) {
          return "Developer tools shortcuts are disabled.";
        }
        if (event.metaKey && alt && ["i", "j", "c", "u"].includes(key)) {
          return "Developer tools shortcuts are disabled.";
        }
        return "";
      };
      document.addEventListener("keydown", (event) => {
        const key = String(event.key || "").toLowerCase();
        if ((event.ctrlKey || event.metaKey) && key === "a") {
          const editable = ftEditableTarget(event && event.target);
          if (editable) {
            event.preventDefault();
            event.stopImmediatePropagation();
            ftSelectEditable(editable);
            return;
          }
          event.preventDefault();
          event.stopImmediatePropagation();
          try {
            const selection = window.getSelection && window.getSelection();
            if (selection && selection.removeAllRanges) {
              selection.removeAllRanges();
            }
          } catch (error) {}
        }
        const protectedMessage = ftProtectedShortcut(event);
        if (protectedMessage) {
          return ftStopProtectedBrowserAction(event, protectedMessage);
        }
      }, true);
      document.addEventListener("selectstart", (event) => {
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        ftStopProtectedBrowserAction(event);
      }, true);
      document.addEventListener("contextmenu", (event) => {
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        if (
          event
          && event.target
          && event.target.closest
          && event.target.closest("#ft-pdf-goto,#ft-pdf-compact-goto,#ft-pdf-pen-toggle,#ft-pdf-compact-pen,#ft-pdf-audio-toggle,#ft-pdf-compact-audio,#ft-pdf-eraser-toggle,#ft-pdf-compact-eraser,#ft-pdf-text-toggle,#ft-pdf-compact-text,#ft-pdf-pin-page-toggle,#ft-pdf-compact-pin-page,#ft-pdf-pin-image-toggle,#ft-pdf-compact-pin-image,#ft-pdf-local-image-toggle,#ft-pdf-compact-local-image,.ft-pdf-pen-popover,.ft-pdf-audio-popover,.ft-pdf-eraser-popover,.ft-pdf-text-popover,.ft-pdf-pin-popover,.ft-pdf-local-image-popover,.ft-pdf-pinned-region-float,.ft-space-s-phonetic-card,.ft-paragraph-replay,.ft-space-s-voice-menu")
        ) {
          return;
        }
        if (
          event
          && event.target
          && event.target.closest
          && event.target.closest(".ft-pdf-page-wrap")
          && typeof pdfModeActive !== "undefined"
          && pdfModeActive
        ) {
          return;
        }
        if (event && event.target && event.target.closest && event.target.closest(".ft-server-browser")) {
          event.preventDefault();
          return;
        }
        ftStopProtectedBrowserAction(event, "Context menu is disabled.");
      }, true);
      document.addEventListener("dragstart", (event) => {
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        ftStopProtectedBrowserAction(event, "Dragging page content is disabled.");
      }, true);
      document.addEventListener("copy", (event) => {
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        try {
          if (event.clipboardData) {
            event.clipboardData.setData("text/plain", "");
          }
        } catch (error) {}
        ftStopProtectedBrowserAction(event, "Copy is disabled outside input fields.");
      }, true);
      document.addEventListener("cut", (event) => {
        if (ftEditableTarget(event && event.target)) {
          return;
        }
        try {
          if (event.clipboardData) {
            event.clipboardData.setData("text/plain", "");
          }
        } catch (error) {}
        ftStopProtectedBrowserAction(event, "Cut is disabled outside input fields.");
      }, true);
      window.addEventListener("beforeprint", (event) => ftStopProtectedBrowserAction(event, "Printing is disabled."), true);
      document.addEventListener("selectionchange", () => {
        try {
          const active = ftEditableTarget(document.activeElement);
          if (active) {
            return;
          }
          const selection = window.getSelection && window.getSelection();
          if (selection && !selection.isCollapsed) {
            selection.removeAllRanges();
          }
        } catch (error) {}
      });
      const params = new URLSearchParams(window.location.search);
      const runtimeHtmlSource = `<!doctype html>\n${document.documentElement.outerHTML}`;
      const WINDOW_BOOTSTRAP_PREFIX = "FTG_BOOTSTRAP:";
      const parseSerializedBootstrap = (raw) => {
        if (!raw) {
          return null;
        }
        try {
          const parsed = JSON.parse(String(raw));
          return parsed && typeof parsed === "object" ? parsed : null;
        } catch (error) {
          return null;
        }
      };
      const readSessionBootstrap = () => {
        const key = params.get("ft_state_key");
        if (!key) {
          return null;
        }
        try {
          const raw = window.sessionStorage && window.sessionStorage.getItem(key);
          if (raw) {
            window.sessionStorage.removeItem(key);
          }
          return parseSerializedBootstrap(raw);
        } catch (error) {
          return null;
        }
      };
      const readLocalBootstrap = () => {
        const key = params.get("ft_state_key");
        if (!key) {
          return null;
        }
        try {
          const raw = window.localStorage && window.localStorage.getItem(key);
          if (raw) {
            window.localStorage.removeItem(key);
          }
          return parseSerializedBootstrap(raw);
        } catch (error) {
          return null;
        }
      };
      const readWindowNameBootstrap = () => {
        const rawName = String(window.name || "");
        if (!rawName.startsWith(WINDOW_BOOTSTRAP_PREFIX)) {
          return null;
        }
        const parsed = parseSerializedBootstrap(rawName.slice(WINDOW_BOOTSTRAP_PREFIX.length));
        if (parsed) {
          try {
            window.name = "";
          } catch (error) {
            // Window name is only a bootstrap transport; leaving it is harmless.
          }
        }
        return parsed;
      };
      const transportedBootstrapState = readSessionBootstrap() || readLocalBootstrap() || readWindowNameBootstrap();
      let bootstrapState = transportedBootstrapState || (window.__FTG_BOOTSTRAP__ && typeof window.__FTG_BOOTSTRAP__ === "object"
        ? window.__FTG_BOOTSTRAP__
        : null);
      if (params.get("ft_popup") === "1" || (bootstrapState && bootstrapState.popupFullscreen)) {
        document.documentElement.classList.add("ft-popup-fullscreen");
      }
      const awaitingExternalBootstrap = (Boolean(window.__FTG_AWAIT_BOOTSTRAP__) || params.get("ft_await") === "1") && !bootstrapState;
      const stageNode = document.querySelector(".ft-stage");
      const shellNode = document.querySelector(".ft-shell");
      const QUESTION_VISUAL_PROFILE_OFF_VALUES = new Set(["0", "false", "off", "no", "legacy"]);
      const questionVisualProfileParam = String(params.get("ft_q_profile") || params.get("ft_preview_profile") || "").trim().toLowerCase();
      const questionVisualProfileEnabled = !QUESTION_VISUAL_PROFILE_OFF_VALUES.has(questionVisualProfileParam);
      const isQuestionVisualProfileActive = () => Boolean(stageNode && stageNode.classList.contains("is-question-preview-profile"));
      const setQuestionVisualProfileActive = (active) => {
        const enabled = Boolean(active) && questionVisualProfileEnabled;
        document.documentElement.classList.toggle("ft-q-preview-profile", enabled);
        if (stageNode) {
          stageNode.classList.toggle("is-question-preview-profile", enabled);
        }
      };
      const cardNode = document.querySelector(".ft-card");
      const fullscreenButton = document.getElementById("ft-fullscreen");
      const aiAgentButton = document.getElementById("ft-ai-agent-button");
      const aiAgentPopup = document.getElementById("ft-ai-agent-popup");
      const aiAgentClose = document.getElementById("ft-ai-agent-close");
      const aiAgentInput = document.getElementById("ft-ai-agent-input");
      const aiAgentVietnameseToggle = document.getElementById("ft-ai-agent-vietnamese-toggle");
      const aiAgentSpeechMode = document.getElementById("ft-ai-agent-speech-mode");
      const aiAgentViSttButton = document.getElementById("ft-ai-agent-vi-stt");
      const aiAgentSubmit = document.getElementById("ft-ai-agent-submit");
      const aiAgentTranslateEn = document.getElementById("ft-ai-agent-translate-en");
      const aiAgentStatus = document.getElementById("ft-ai-agent-status");
      const aiAgentThinking = document.getElementById("ft-ai-agent-thinking");
      const aiAgentThinkingTime = document.getElementById("ft-ai-agent-thinking-time");
      const aiAgentGhostEnPopup = document.getElementById("ft-ai-ghost-en-popup");
      const aiAgentGhostEnClose = document.getElementById("ft-ai-ghost-en-close");
      const aiAgentGhostEnSource = document.getElementById("ft-ai-ghost-en-source");
      const aiAgentGhostEnText = document.getElementById("ft-ai-ghost-en-text");
      const aiAgentGhostEnStatus = document.getElementById("ft-ai-ghost-en-status");
      const aiAgentGhostEnDetail = document.getElementById("ft-ai-ghost-en-detail");
      const aiAgentGhostEnVoiceButtons = Array.from(document.querySelectorAll("[data-ghost-en-voice]"));
      const aiAgentGhostEnSpeed = document.getElementById("ft-ai-ghost-en-speed");
      const aiAgentGhostEnSpeedValue = aiAgentGhostEnSpeed ? aiAgentGhostEnSpeed.querySelector(".ft-ai-ghost-en-speed-value") : null;
      const aiAgentGhostEnVoiceSelect = document.getElementById("ft-ai-ghost-en-voice-select");
      const aiAgentGhostEnRead = document.getElementById("ft-ai-ghost-en-read");
      const aiAgentGhostEnReplay = document.getElementById("ft-ai-ghost-en-replay");
      const aiAgentGhostEnMic = document.getElementById("ft-ai-ghost-en-mic");
      const aiAgentGhostEnReading = document.getElementById("ft-ai-ghost-en-reading");
      const aiAgentGhostEnReadingLabel = document.getElementById("ft-ai-ghost-en-reading-label");
      const aiAgentSuggestion = document.getElementById("ft-ai-agent-suggestion");
      const aiAgentSuggestionText = document.getElementById("ft-ai-agent-suggestion-text");
      const aiAgentSuggestionUse = document.getElementById("ft-ai-agent-suggestion-use");
      const aiAgentSuggestionDismiss = document.getElementById("ft-ai-agent-suggestion-dismiss");
      const aiAgentVocabQuick = document.getElementById("ft-ai-agent-vocab-quick");
      const aiAgentVocabQuickButtons = Array.from(document.querySelectorAll("[data-ai-vocab-quick]"));
      const aiAgentParagraphQuick = document.getElementById("ft-ai-agent-paragraph-quick");
      const aiAgentParagraphQuickList = document.getElementById("ft-ai-agent-paragraph-quick-list");
      const aiAgentModeButtons = Array.from(document.querySelectorAll("[data-ai-agent-mode]"));
      let aiAgentPopupResumeAfterNotice = false;
      let aiAgentThinkingStartedAt = 0;
      let aiAgentThinkingTimer = 0;
      let aiAgentPendingSuggestion = null;
      let aiAgentSuggestionPulseTimer = 0;
      let aiAgentSuggestionAcknowledged = false;
      let aiAgentActiveNotice = null;
      let aiAgentHistoryCache = [];
      let aiAgentOneShotContextPatch = null;
      let aiAgentGhostEnDetailMap = {};
      let aiAgentGhostEnLastTranslation = "";
      let aiAgentGhostEnHoverTimer = 0;
      // Added 2026-07-01: lets Ghost EN translate cancel/retry without spamming Server 2.
      const AI_AGENT_TRANSLATE_EN_COOLDOWN_MS = 10000;
      let aiAgentTranslateEnAbortController = null;
      let aiAgentTranslateEnRequestId = 0;
      let aiAgentTranslateEnLastStartedAt = 0;
      let aiAgentGhostEnVoiceAccent = "uk";
      let aiAgentGhostEnPlaybackRate = 1;
      let aiAgentGhostEnPreferredVoice = "";
      let aiAgentGhostEnPreferredVoiceLabel = "";
      let aiAgentGhostEnPreferenceSaveTimer = 0;
      let aiAgentGhostEnAudioPlayer = null;
      let aiAgentGhostEnVoicesLoaded = false;
      let aiAgentGhostEnParagraphPlayer = null;
      let aiAgentGhostEnParagraphRequestId = 0;
      let aiAgentGhostEnVoiceHighlightFrame = 0;
      let aiAgentGhostEnParagraphTimingPayload = null;
      let aiAgentGhostEnRecognition = null;
      let aiAgentGhostEnRecognizing = false;
      let aiAgentGhostEnRecognitionManualStop = false;
      let aiAgentGhostEnRecognitionTranscript = "";
      let aiAgentGhostEnRecognitionChunk = "";
      let aiAgentGhostEnMatchedTokenIndexes = new Set();
      let aiAgentGhostEnMatchedTokenTimes = new Map();
      let aiAgentGhostEnMicStartedAt = 0;
      let aiAgentGhostEnMicReplaying = false;
      let aiAgentGhostEnReplayTimer = 0;
      let aiAgentGhostEnReplayFrame = 0;
      let aiAgentGhostEnMicStream = null;
      let aiAgentGhostEnMicRecorder = null;
      let aiAgentGhostEnMicChunks = [];
      let aiAgentGhostEnMicReplayAudio = null;
      let aiAgentGhostEnMicReplayUrl = "";
      let aiAgentGhostEnLastMicReplayBlob = null;
      const mobileToolsToggle = document.getElementById("ft-mobile-tools-toggle");
      const chatButton = document.getElementById("ft-chat-button");
      const streamButton = document.getElementById("ft-stream-button");
      const screenButton = document.getElementById("ft-screen-button");
      const webRecordButton = document.getElementById("ft-web-record-button");
      const adminScreenButton = document.getElementById("ft-admin-screen-button");
      const paintButton = document.getElementById("ft-paint-button");
      const mobileAnimationButton = document.getElementById("ft-mobile-animation-button");
      const clearAudioCacheButton = document.getElementById("ft-clear-audio-cache-button");
      const cursorButton = document.getElementById("ft-cursor-button");
      const speakSkipAdminButton = document.getElementById("ft-speak-admin-button");
      const gameButton = document.getElementById("ft-game-button");
      const portalButton = document.getElementById("ft-portal-button");
      const vaultButton = document.getElementById("ft-vault-button");
      const cupButton = document.getElementById("ft-cup-button");
      const workerToolbarButton = document.getElementById("ft-worker-toolbar-button");
      const npcSwitchButton = document.getElementById("ft-npc-switch-button");
      const npcSwitchModal = document.getElementById("ft-npc-switch-modal");
      const npcSwitchClose = document.getElementById("ft-npc-switch-close");
      const npcSwitchList = document.getElementById("ft-npc-switch-list");
      const npcSwitchStatus = document.getElementById("ft-npc-switch-status");
      const npcSwitchReset = document.getElementById("ft-npc-switch-reset");
      const npcSwitchBuffInput = document.getElementById("ft-npc-switch-buff-input");
      const npcSwitchBuffAdd = document.getElementById("ft-npc-switch-buff-add");
      const pdfCompactDock = document.getElementById("ft-pdf-compact-dock");
      const pdfCompactToggle = document.getElementById("ft-pdf-compact-toggle");
      const pdfCompactControls = document.getElementById("ft-pdf-compact-controls");
      const pdfCompactPrev = document.getElementById("ft-pdf-compact-prev");
      const pdfCompactNext = document.getElementById("ft-pdf-compact-next");
      const pdfCompactQuality = document.getElementById("ft-pdf-compact-quality");
      const pdfCompactGoto = document.getElementById("ft-pdf-compact-goto");
      const pdfCompactPageGhost = document.getElementById("ft-pdf-compact-pageghost");
      const pdfCompactZoomOut = document.getElementById("ft-pdf-compact-zoom-out");
      const pdfCompactZoomIn = document.getElementById("ft-pdf-compact-zoom-in");
      const pdfCompactAiAssist = document.getElementById("ft-pdf-compact-ai-assist");
      const pdfCompactEye = document.getElementById("ft-pdf-compact-eye");
      const pdfCompactScan = document.getElementById("ft-pdf-compact-scan");
      const pdfCompactPen = document.getElementById("ft-pdf-compact-pen");
      const pdfCompactAudio = document.getElementById("ft-pdf-compact-audio");
      const pdfCompactEraser = document.getElementById("ft-pdf-compact-eraser");
      const pdfCompactText = document.getElementById("ft-pdf-compact-text");
      const pdfCompactPinPage = document.getElementById("ft-pdf-compact-pin-page");
      const pdfCompactPinImage = document.getElementById("ft-pdf-compact-pin-image");
      const pdfCompactLocalImage = document.getElementById("ft-pdf-compact-local-image");
      const pdfCompactConsole = document.getElementById("ft-pdf-compact-console");
      const chatDot = document.getElementById("ft-chat-dot");
      const cupModal = document.getElementById("ft-cup-modal");
      const cupClose = document.getElementById("ft-cup-close");
      const cupTitle = document.getElementById("ft-cup-title");
      const cupTypePicker = document.getElementById("ft-cup-type-picker");
      const cupTypeSelect = document.getElementById("ft-cup-type");
      const cupTypeButton = document.getElementById("ft-cup-type-button");
      const cupTypeMenu = document.getElementById("ft-cup-type-menu");
      const cupTypeCurrentLabel = document.getElementById("ft-cup-type-current-label");
      const cupTypeOptions = Array.from(document.querySelectorAll("[data-cup-type]"));
      const cupPodium = document.getElementById("ft-cup-podium");
      const cupViewers = document.getElementById("ft-cup-viewers");
      const cupWorldChatLog = document.getElementById("ft-cup-world-chat-log");
      const cupWorldChatInput = document.getElementById("ft-cup-world-chat-input");
      const cupWorldChatSend = document.getElementById("ft-cup-world-chat-send");
      const cupViewerPopover = document.getElementById("ft-cup-viewer-popover");
      const cupViewerClose = document.getElementById("ft-cup-viewer-close");
      const cupViewerList = document.getElementById("ft-cup-viewer-list");
      const cupList = document.getElementById("ft-cup-list");
      const cupStatus = document.getElementById("ft-cup-status");
      const cupRewardModal = document.getElementById("ft-cup-reward-modal");
      const cupRewardClose = document.getElementById("ft-cup-reward-close");
      const cupRewardTitle = document.getElementById("ft-cup-reward-title");
      const cupRewardBody = document.getElementById("ft-cup-reward-body");
      const cupStatusComposer = document.getElementById("ft-cup-status-composer");
      const cupStatusInput = document.getElementById("ft-cup-status-input");
      const cupStatusSave = document.getElementById("ft-cup-status-save");
      const cupTabs = Array.from(document.querySelectorAll("[data-cup-scope]"));
      let currentCupScope = "day";
      let currentCupType = "space_v";
      let cupLeaderboardCache = { at: 0, type: "space_v", boards: {}, users: [], viewers: [], myStatuses: {}, chat: [], reactionOptions: [] };
      let cupPendingCompletion = null;
      const cupLeaderboardHttpCache = new Map();
      let cupLeaderboardRefreshTimer = 0;
      let cupRewardConfig = {};
      let cupCloseContinuation = null;
      const HOLOGRAM_CURSOR_KEY = "future_hologram_cursor_enabled";
      let hologramCursorUserOverride = "";
      const hologramCursorStorageKey = () => {
        const authInput = document.getElementById("ft-auth-user");
        let savedUser = "";
        try {
          savedUser = localStorage.getItem("future_lesson_auth_user") || "";
        } catch (error) {
          savedUser = "";
        }
        const username = clean(hologramCursorUserOverride || (authInput && authInput.value) || savedUser || "guest").toLowerCase();
        return `${HOLOGRAM_CURSOR_KEY}:${username || "guest"}`;
      };
      const readHologramCursorEnabled = () => {
        return false;
      };
      let hologramCursorEnabled = readHologramCursorEnabled();
      let hologramCursorController = null;
      const saveHologramCursorPreference = () => {
        try {
          localStorage.setItem(hologramCursorStorageKey(), "0");
        } catch (error) {
        }
      };
      const updateHologramCursorButton = () => {
        if (!cursorButton) {
          return;
        }
        cursorButton.classList.remove("is-active", "is-visible");
        cursorButton.hidden = true;
        cursorButton.setAttribute("aria-pressed", "false");
        cursorButton.setAttribute("aria-label", "Browser cursor effects removed");
        cursorButton.title = "Browser cursor effects removed";
      };
      const initHologramCursor = () => {
        const root = document.documentElement;
        const cursor = document.getElementById("ft-holo-cursor");
        const clearCursorState = () => {
          root.classList.remove("ft-holo-cursor-ready", "ft-holo-cursor-active", "ft-holo-cursor-down", "ft-holo-cursor-pointer", "ft-holo-cursor-drag", "ft-holo-cursor-native", "ft-holo-cursor-idle");
          root.classList.add("ft-holo-cursor-hidden");
          if (cursor) {
            cursor.remove();
          }
        };
        hologramCursorEnabled = false;
        hologramCursorController = { apply: clearCursorState, clear: clearCursorState };
        clearCursorState();
      };
      const applyHologramCursorPreference = () => {
        updateHologramCursorButton();
        initHologramCursor();
        if (hologramCursorController) {
          hologramCursorController.apply();
        }
      };
      const loadHologramCursorSettings = () => {
        hologramCursorEnabled = readHologramCursorEnabled();
        applyHologramCursorPreference();
        return hologramCursorEnabled;
      };
      const applyHologramCursorPayload = (payload = {}) => {
        hologramCursorEnabled = false;
        saveHologramCursorPreference();
        applyHologramCursorPreference();
        return false;
      };
      const syncHologramCursorPreferenceToServer = async () => {
        if (!authToken) {
          return;
        }
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              hologram_cursor: {
                enabled: Boolean(hologramCursorEnabled),
              },
            }),
          });
        } catch (error) {
          // Local storage remains the offline fallback.
        }
      };
      const setHologramCursorEnabled = (enabled, options = {}) => {
        hologramCursorEnabled = false;
        saveHologramCursorPreference();
        applyHologramCursorPreference();
        if (!options || options.sync !== false) {
          void syncHologramCursorPreferenceToServer();
        }
      };
      const toggleHologramCursor = () => {
        setHologramCursorEnabled(false);
      };
      initHologramCursor();
      updateHologramCursorButton();
      const chatModal = document.getElementById("ft-chat-modal");
      const chatClose = document.getElementById("ft-chat-close");
      const chatLog = document.getElementById("ft-chat-log");
      const chatViInput = document.getElementById("ft-chat-vi-input");
      const chatViSend = document.getElementById("ft-chat-vi-send");
      const chatViVoiceSelect = document.getElementById("ft-chat-vi-voice");
      const chatViAudioToggle = document.getElementById("ft-chat-vi-audio-toggle");
      const chatViSpeechMode = document.getElementById("ft-chat-vi-speech-mode");
      const chatViSttButton = document.getElementById("ft-chat-vi-stt");
      const chatInput = document.getElementById("ft-chat-input");
      const chatSend = document.getElementById("ft-chat-send");
      const chatVoiceSelect = document.getElementById("ft-chat-voice");
      const chatAudioToggle = document.getElementById("ft-chat-audio-toggle");
      const chatAttach = document.getElementById("ft-chat-attach");
      const chatMic = document.getElementById("ft-chat-mic");
      const chatVoiceSend = document.getElementById("ft-chat-voice-send");
      const chatVoiceCancel = document.getElementById("ft-chat-voice-cancel");
      const chatFileInput = document.getElementById("ft-chat-file");
      const chatStatus = document.getElementById("ft-chat-status");
      const speakSkipAdminModal = document.getElementById("ft-speak-admin-modal");
      const speakSkipAdminClose = document.getElementById("ft-speak-admin-close");
      const speakSkipAdminRefresh = document.getElementById("ft-speak-admin-refresh");
      const speakSkipAdminAcceptAll = document.getElementById("ft-speak-admin-accept-all");
      const speakSkipAdminList = document.getElementById("ft-speak-admin-list");
      const speakSkipAdminStatus = document.getElementById("ft-speak-admin-status");
      const adminScreenModal = document.getElementById("ft-admin-screen-modal");
      const adminScreenClose = document.getElementById("ft-admin-screen-close");
      const adminScreenRefresh = document.getElementById("ft-admin-screen-refresh");
      const adminScreenStop = document.getElementById("ft-admin-screen-stop");
      const adminScreenList = document.getElementById("ft-admin-screen-list");
      const adminScreenStatus = document.getElementById("ft-admin-screen-status");
      const adminScreenModeButton = document.getElementById("ft-admin-screen-mode");
      const adminScreenMicButton = document.getElementById("ft-admin-screen-mic");
      const adminScreenCheckPath = document.getElementById("ft-admin-screen-check-path");
      const adminScreenLog = document.getElementById("ft-admin-screen-log");
      const adminScreenView = document.getElementById("ft-admin-screen-view");
      const adminScreenVideo = document.getElementById("ft-admin-screen-video");
      const adminScreenImg = document.getElementById("ft-admin-screen-img");
      const adminScreenPlaceholder = document.getElementById("ft-admin-screen-placeholder");
      const adminScreenFullscreen = document.getElementById("ft-admin-screen-fullscreen");
      const adminScreenReconnect = document.getElementById("ft-admin-screen-reconnect");
      const imageViewer = document.getElementById("ft-image-viewer");
      const imageViewerImg = document.getElementById("ft-image-viewer-img");
      const imageViewerClose = document.getElementById("ft-image-viewer-close");
      const imageViewerDownload = document.getElementById("ft-image-viewer-download");
      const imageViewerZoomOut = document.getElementById("ft-image-viewer-zoom-out");
      const imageViewerZoomReset = document.getElementById("ft-image-viewer-zoom-reset");
      const imageViewerZoomIn = document.getElementById("ft-image-viewer-zoom-in");
      const paintModal = document.getElementById("ft-paint-modal");
      const paintCard = document.getElementById("ft-paint-card");
      const paintSyncStatus = document.getElementById("ft-paint-sync");
      const paintClose = document.getElementById("ft-paint-close");
      const paintCanvas = document.getElementById("ft-paint-canvas");
      const paintToolCursor = document.getElementById("ft-paint-tool-cursor");
      const paintClearSweep = document.getElementById("ft-paint-clear-sweep");
      const paintModeButtons = Array.from(document.querySelectorAll("[data-paint-mode]"));
      const paintClear = document.getElementById("ft-paint-clear");
      const paintImage = document.getElementById("ft-paint-image");
      const paintPaste = document.getElementById("ft-paint-paste");
      const paintDelete = document.getElementById("ft-paint-delete");
      const paintZoomOut = document.getElementById("ft-paint-zoom-out");
      const paintZoomIn = document.getElementById("ft-paint-zoom-in");
      const paintZoomLabel = document.getElementById("ft-paint-zoom-label");
      const paintFullscreen = document.getElementById("ft-paint-fullscreen");
      const paintTab = document.getElementById("ft-paint-tab");
      const paintImageFile = document.getElementById("ft-paint-image-file");
      const paintColor = document.getElementById("ft-paint-color");
      const paintSize = document.getElementById("ft-paint-size");
      const gameModal = document.getElementById("ft-game-modal");
      const gameClose = document.getElementById("ft-game-close");
      const gameSeatsInput = document.getElementById("ft-game-seats");
      const gameWordLimitInput = document.getElementById("ft-game-word-limit");
      const gameRoomCodeInput = document.getElementById("ft-game-room-code");
      const gameCreateButton = document.getElementById("ft-game-create");
      const gameJoinButton = document.getElementById("ft-game-join");
      const gameReadyButton = document.getElementById("ft-game-ready");
      const gameCancelButton = document.getElementById("ft-game-cancel");
      const gameRoomList = document.getElementById("ft-game-room-list");
      const gameSeatsList = document.getElementById("ft-game-seats-list");
      const gameVocabGrid = document.getElementById("ft-game-vocab-grid");
      const gameStatus = document.getElementById("ft-game-status");
      const worldModal = document.getElementById("ft-world-modal");
      const worldMenuTrigger = document.getElementById("ft-world-menu-trigger");
      const worldClose = document.getElementById("ft-world-close");
      const worldCloseMenu = document.getElementById("ft-world-close-menu");
      const worldExitButton = document.getElementById("ft-world-exit-button");
      const worldInventoryButton = document.getElementById("ft-world-inventory-button");
      const worldCard = document.querySelector(".ft-world-card");
      const worldTitle = document.getElementById("ft-world-title");
      const worldStage = document.getElementById("ft-world-stage");
      const worldArena = document.getElementById("ft-world-arena");
      const worldPlayers = document.getElementById("ft-world-players");
      const worldBattleLinks = document.getElementById("ft-world-battle-links");
      const worldPointMarker = document.getElementById("ft-world-point-marker");
      const worldMoveMarker = document.getElementById("ft-world-move-marker");
      const worldWitch = document.getElementById("ft-world-witch");
      const worldWitchBubble = document.getElementById("ft-world-witch-bubble");
      const worldChatForm = document.getElementById("ft-world-chat-form");
      const worldChatInput = document.getElementById("ft-world-chat-input");
      const worldCommandInput = document.getElementById("ft-world-command-input");
      const worldCommandSend = document.getElementById("ft-world-command-send");
      const worldCommandHelp = document.getElementById("ft-world-command-help");
      const worldCommandList = document.getElementById("ft-world-command-list");
      const worldTrainingHistory = document.getElementById("ft-world-training-history");
      const worldTrainingHistoryTitle = document.getElementById("ft-world-training-history-title");
      const worldTrainingHistoryList = document.getElementById("ft-world-training-history-list");
      const worldGameButton = document.getElementById("ft-world-game-button");
      const worldGameList = document.getElementById("ft-world-game-list");
      const worldTargetChip = document.getElementById("ft-world-target-chip");
      const worldPointButton = document.getElementById("ft-world-point-button");
      const worldPositionChip = document.getElementById("ft-world-position-chip");
      const worldLocateButton = document.getElementById("ft-world-locate-button");
      const worldFollowButton = document.getElementById("ft-world-follow-button");
      const worldNpcButton = document.getElementById("ft-world-npc-button");
      const worldNpcList = document.getElementById("ft-world-npc-list");
      const worldKeypassButton = document.getElementById("ft-world-keypass-button");
      const worldKeypassTitle = document.getElementById("ft-world-keypass-title");
      const worldKeypassStatus = document.getElementById("ft-world-keypass-status");
      const worldStatus = document.getElementById("ft-world-status");
      const worldStatusText = document.getElementById("ft-world-status-text");
      const worldTrainingPortal = document.getElementById("ft-world-training-portal");
      const worldTrainingField = document.getElementById("ft-world-training-field");
      const worldTrainingExitGate = document.getElementById("ft-world-training-exit-gate");
      const worldTrainingMapSlimes = document.getElementById("ft-world-training-slime-map");
      const worldTrainingModal = document.getElementById("ft-world-training-modal");
      const worldTrainingClose = document.getElementById("ft-world-training-close");
      const worldTrainingStats = document.getElementById("ft-world-training-stats");
      const worldTrainingSlimes = document.getElementById("ft-world-training-slimes");
      const worldTrainingTarget = document.getElementById("ft-world-training-target");
      const worldTrainingQuestion = document.getElementById("ft-world-training-question");
      const worldTrainingAnswerForm = document.getElementById("ft-world-training-answer-form");
      const worldTrainingViToggle = document.getElementById("ft-world-training-vi-toggle");
      const worldTrainingSpeechMode = document.getElementById("ft-world-training-speech-mode");
      const worldTrainingSpeechMic = document.getElementById("ft-world-training-speech-mic");
      const worldTrainingAnswer = document.getElementById("ft-world-training-answer");
      const worldTrainingSubmit = document.getElementById("ft-world-training-submit");
      const worldTrainingReset = document.getElementById("ft-world-training-reset");
      const worldTrainingLog = document.getElementById("ft-world-training-log");
      const worldInvitePanel = document.getElementById("ft-world-invite-panel");
      const worldInviteTitle = document.getElementById("ft-world-invite-title");
      const worldInviteCopy = document.getElementById("ft-world-invite-copy");
      const worldInviteAccept = document.getElementById("ft-world-invite-accept");
      const worldInviteDecline = document.getElementById("ft-world-invite-decline");
      const worldBattleModal = document.getElementById("ft-world-battle-modal");
      const worldBattleCard = worldBattleModal ? worldBattleModal.querySelector(".ft-world-battle-card") : null;
      const worldBattleLeft = document.getElementById("ft-world-battle-left");
      const worldBattleRight = document.getElementById("ft-world-battle-right");
      const worldBattleTimer = document.getElementById("ft-world-battle-timer");
      const worldBattlePhase = document.getElementById("ft-world-battle-phase");
      const worldBattleQuestion = document.getElementById("ft-world-battle-question");
      const worldBattleAnswerForm = document.getElementById("ft-world-battle-answer-form");
      const worldBattleAnswer = document.getElementById("ft-world-battle-answer");
      const worldBattleSpeechMic = document.getElementById("ft-world-battle-speech-mic");
      const worldBattleSubmit = document.getElementById("ft-world-battle-submit");
      const worldBattleSkills = document.getElementById("ft-world-battle-skills");
      const worldBattleLog = document.getElementById("ft-world-battle-log");
      const worldBattleForfeit = document.getElementById("ft-world-battle-forfeit");
      const worldBattleResult = document.getElementById("ft-world-battle-result");
      const worldBattleResultKicker = document.getElementById("ft-world-battle-result-kicker");
      const worldBattleResultTitle = document.getElementById("ft-world-battle-result-title");
      const worldBattleResultCopy = document.getElementById("ft-world-battle-result-copy");
      const worldBattleResultReward = document.getElementById("ft-world-battle-result-reward");
      const worldBattleResultClose = document.getElementById("ft-world-battle-result-close");
      const worldSkinShop = document.getElementById("ft-world-skin-shop");
      const worldSkinShopClose = document.getElementById("ft-world-shop-close");
      const worldSkinList = document.getElementById("ft-world-skin-list");
      const worldCrystalCount = document.getElementById("ft-world-crystal-count");
      const worldInventoryGrid = document.getElementById("ft-world-inventory-grid");
      const worldInventoryInfo = document.getElementById("ft-world-inventory-info");
      const worldShopReply = document.getElementById("ft-world-shop-reply");
      const worldShopInput = document.getElementById("ft-world-shop-input");
      const worldShopSend = document.getElementById("ft-world-shop-send");
      const worldInventoryModal = document.getElementById("ft-world-inventory-modal");
      const worldInventoryClose = document.getElementById("ft-world-inventory-close");
      const worldLoadoutName = document.getElementById("ft-world-loadout-name");
      const worldPocketCount = document.getElementById("ft-world-pocket-count");
      const worldPocketGrid = document.getElementById("ft-world-pocket-grid");
      const worldPocketInfo = document.getElementById("ft-world-pocket-info");
      const worldTrainingLoadoutPanel = document.getElementById("ft-world-training-loadout-panel");
      const worldTrainingQuickSkill = document.getElementById("ft-world-training-quick-skill");
      const worldTrainingQuickSkillMeta = document.getElementById("ft-world-training-quick-skill-meta");
      const worldTrainingQuickSkillCooldown = document.getElementById("ft-world-training-quick-skill-cooldown");
      const paintTextInput = document.getElementById("ft-paint-text-input");
      const userButton = document.getElementById("ft-user-button");
      const userAvatar = document.getElementById("ft-user-avatar");
      const userAvatarImg = document.getElementById("ft-user-avatar-img");
      const userNameNode = document.getElementById("ft-user-name");
      const userMenu = document.getElementById("ft-user-menu");
      const userMenuAvatar = document.getElementById("ft-user-menu-avatar");
      const userMenuAvatarImg = document.getElementById("ft-user-menu-avatar-img");
      const userMenuName = document.getElementById("ft-user-menu-name");
      const userAvatarStatus = document.getElementById("ft-user-avatar-status");
      const userAvatarUploadButton = document.getElementById("ft-user-avatar-upload");
      const userAvatarFileInput = document.getElementById("ft-user-avatar-file");
      const profileEditOpenButton = document.getElementById("ft-profile-edit-open");
      const pdfAdminUserOpenButton = document.getElementById("ft-pdf-admin-user-open");
      const pdfAdminUserPanel = document.getElementById("ft-pdf-admin-user-panel");
      const pdfAdminUserSelect = document.getElementById("ft-pdf-admin-user-select");
      const pdfAdminUserApply = document.getElementById("ft-pdf-admin-user-apply");
      const pdfAdminUserClear = document.getElementById("ft-pdf-admin-user-clear");
      const pdfAdminUserStatus = document.getElementById("ft-pdf-admin-user-status");
      const pdfAdminUserNote = document.getElementById("ft-pdf-admin-user-note");
      const profileModal = document.getElementById("ft-profile-modal");
      const profileCloseButton = document.getElementById("ft-profile-close");
      const profileAvatarNode = document.getElementById("ft-profile-avatar");
      const profileNameNode = document.getElementById("ft-profile-name");
      const profileUserNode = document.getElementById("ft-profile-user");
      const profileGalleryNode = document.getElementById("ft-profile-gallery");
      const profileIntroNode = document.getElementById("ft-profile-intro");
      const profileEditModal = document.getElementById("ft-profile-edit-modal");
      const profileEditCloseButton = document.getElementById("ft-profile-edit-close");
      const profileEditEmail = document.getElementById("ft-profile-edit-email");
      const profileEditIntro = document.getElementById("ft-profile-edit-intro");
      const profileEditGallery = document.getElementById("ft-profile-edit-gallery");
      const profileEditSave = document.getElementById("ft-profile-edit-save");
      const profileEditStatus = document.getElementById("ft-profile-edit-status");
      const profilePhotoFileInput = document.getElementById("ft-profile-photo-file");
      const logoutButton = document.getElementById("ft-logout");
      const inventoryOpenButton = document.getElementById("ft-inventory-open");
      const inventoryModal = document.getElementById("ft-inventory-modal");
      const inventoryCloseButton = document.getElementById("ft-inventory-close");
      const inventoryGrid = document.getElementById("ft-inventory-grid");
      const inventoryInfo = document.getElementById("ft-inventory-info");
      const startFullscreenGate = document.getElementById("ft-start-fullscreen");
      const startFullscreenMain = document.getElementById("ft-start-fullscreen-main");
      const startFullscreenSkip = document.getElementById("ft-start-fullscreen-skip");
      const authFullscreenButton = document.getElementById("ft-auth-fullscreen");
      const loginVaultPreview = document.getElementById("ft-login-vault-preview");
      const authGate = document.getElementById("ft-auth-gate");
      const authPanel = document.querySelector(".ft-auth-panel");
      const authConnectors = document.getElementById("ft-auth-connectors");
      const authConnectorLines = document.getElementById("ft-auth-connector-lines");
      const authConnectorNodes = document.getElementById("ft-auth-connector-nodes");
      const authHudList = document.getElementById("ft-auth-hud-list");
      const authHudStatusText = document.getElementById("ft-auth-hud-status-text");
      const authHudStamp = document.getElementById("ft-auth-hud-stamp");
      const authModeNode = document.getElementById("ft-auth-mode");
      const authTitle = document.getElementById("ft-auth-title");
      const authLoginTab = document.getElementById("ft-auth-login-tab");
      const authRegisterTab = document.getElementById("ft-auth-register-tab");
      const authSessionUser = document.getElementById("ft-auth-session-user");
      const authSwitch = document.getElementById("ft-auth-switch");
      const authUser = document.getElementById("ft-auth-user");
      const authPass = document.getElementById("ft-auth-pass");
      const authPassToggle = document.getElementById("ft-auth-pass-toggle");
      const authConfirm = document.getElementById("ft-auth-confirm");
      const authFullName = document.getElementById("ft-auth-full-name");
      const authGender = document.getElementById("ft-auth-gender");
      const authBirth = document.getElementById("ft-auth-birth");
      const authEmail = document.getElementById("ft-auth-email");
      const authForgot = document.getElementById("ft-auth-forgot");
      const authResetPanel = document.getElementById("ft-auth-reset-panel");
      const authResetCode = document.getElementById("ft-auth-reset-code");
      const authResetSend = document.getElementById("ft-auth-reset-send");
      const authSubmit = document.getElementById("ft-auth-submit");
      const authStatus = document.getElementById("ft-auth-status");
      const questionNode = document.getElementById("ft-question-title");
      const progressNode = document.getElementById("ft-progress");
      const answerInputWrap = document.getElementById("ft-input-wrap");
      const answerInput = document.getElementById("ft-answer");
      const answerInputHighlight = document.getElementById("ft-input-highlight");
      const checkButton = document.getElementById("ft-check");
      const translationAboutButton = document.getElementById("ft-translation-about");
      const feedbackNode = document.getElementById("ft-feedback");
      const qRootCard = document.getElementById("ft-q-root-card");
      const qRootText = document.getElementById("ft-q-root-text");
      const qRootHudLines = document.getElementById("ft-q-root-hud-lines");
      const qRootChoiceSignal = document.getElementById("ft-q-root-choice-signal");
      const qRootChoiceSignalState = document.getElementById("ft-q-root-choice-signal-state");
      const qRootChoiceSignalText = document.getElementById("ft-q-root-choice-signal-text");
      const qProgress = document.getElementById("ft-q-progress");
      const qAnimationToggle = document.getElementById("ft-q-animation-toggle");
      const qAnimationEnergy = document.getElementById("ft-q-animation-energy");
      const qAnimationPanel = qAnimationEnergy ? qAnimationEnergy.closest(".ft-q-root-switches") : null;
      const qSideCardToggle = document.getElementById("ft-q-side-card-toggle");
      const qRootNoticeReplayButton = document.getElementById("ft-q-notice-replay");
      const qSelectSubmitButton = document.getElementById("ft-q-select-submit");
      const qSkipTypeButton = document.getElementById("ft-q-skip-type");
      const qFeedback = document.getElementById("ft-q-feedback");
      const qMobileTabs = document.getElementById("ft-q-mobile-tabs");
      const qMobileTabButtons = Array.from(document.querySelectorAll(".ft-q-mobile-tab[data-q-panel]"));
      if (qMobileTabs && stageNode && qMobileTabs.parentElement !== stageNode) {
        stageNode.insertBefore(qMobileTabs, shellNode || stageNode.firstElementChild);
      }
      const qConnectorPicture = document.getElementById("ft-q-connector-picture");
      const qConnectorAudio = document.getElementById("ft-q-connector-audio");
      const qConnectorQuestion = document.getElementById("ft-q-connector-question");
      const qConnectorInfo = document.getElementById("ft-q-connector-info");
      const qPictureCard = document.getElementById("ft-q-picture-card");
      const qPictureImg = document.getElementById("ft-q-picture-img");
      const qPictureCaption = document.getElementById("ft-q-picture-caption");
      const qPictureZoomOut = document.getElementById("ft-q-picture-zoom-out");
      const qPictureZoomReset = document.getElementById("ft-q-picture-zoom-reset");
      const qPictureZoomIn = document.getElementById("ft-q-picture-zoom-in");
      const qPictureMotionButton = document.getElementById("ft-q-picture-motion");
      const qShipPrevButton = document.getElementById("ft-q-ship-prev");
      const qShipNextButton = document.getElementById("ft-q-ship-next");
      const qAudioCard = document.getElementById("ft-q-audio-card");
      const qAudioText = document.getElementById("ft-q-audio-text");
      const qPlayButton = document.getElementById("ft-q-play");
      const qAudioMotionButton = document.getElementById("ft-q-audio-motion");
      const qAudioVoice = document.getElementById("ft-q-audio-voice");
      const qQuestionCard = document.getElementById("ft-q-question-card");
      const qQuestionCount = document.getElementById("ft-q-question-count");
      const qInputLengthRadar = document.getElementById("ft-q-input-length-radar");
      const qInputLengthCount = document.getElementById("ft-q-input-length-count");
      const qInputLengthLabel = document.getElementById("ft-q-input-length-label");
      const qQuestionAudioButton = document.getElementById("ft-q-question-audio");
      const qQuestionText = document.getElementById("ft-q-question-text");
      const qChoiceList = document.getElementById("ft-q-choice-list");
      const qInputRow = document.getElementById("ft-q-input-row");
      const qAnswerInput = document.getElementById("ft-q-answer");
      const qCheckButton = document.getElementById("ft-q-check");
      const qShowAnswerButton = document.getElementById("ft-q-show-answer");
      const qNextButton = document.getElementById("ft-q-next");
      const qAnswerFeedback = document.getElementById("ft-q-answer-feedback");
      const qInfoCard = document.getElementById("ft-q-info-card");
      const qInfoText = document.getElementById("ft-q-info-text");
      const qInfoPlayButton = document.getElementById("ft-q-info-play");
      const qRootNotice = document.getElementById("ft-q-root-notice");
      const qRootNoticeAvatar = document.getElementById("ft-q-root-notice-avatar");
      const qRootNoticeEn = document.getElementById("ft-q-root-notice-en");
      const qRootNoticeVi = document.getElementById("ft-q-root-notice-vi");
      const qRootNoticeVoice = document.getElementById("ft-q-root-notice-voice");
      if (qRootNotice && stageNode && qRootNotice.parentElement !== stageNode) {
        stageNode.appendChild(qRootNotice);
      }
      const vocabCard = document.getElementById("ft-vocab-card");
      const vocabCardSignal = document.getElementById("ft-vocab-card-signal");
      const vocabTitle = document.getElementById("ft-vocab-title");
      const vocabProgress = document.getElementById("ft-vocab-progress");
      const vocabMeta = document.getElementById("ft-vocab-meta");
      const vocabAnswer = document.getElementById("ft-vocab-answer");
      const vocabFeedback = document.getElementById("ft-vocab-feedback");
      const vocabStrip = document.getElementById("ft-vocab-strip");
      const vocabTimer = document.getElementById("ft-vocab-timer");
      const vocabTimerText = document.getElementById("ft-vocab-timer-text");
      const vocabModePopup = document.getElementById("ft-vocab-mode-popup");
      const vocabModeTitle = document.getElementById("ft-vocab-mode-title");
      const vocabModeText = document.getElementById("ft-vocab-mode-text");
      const vocabVoiceSwitch = document.getElementById("ft-vocab-voice-switch");
      const vocabVoiceOptions = Array.from(document.querySelectorAll(".ft-vocab-voice-option[data-voice]"));
      const vocabLearnedPanel = document.getElementById("ft-vocab-learned-panel");
      const vocabLearnedCount = document.getElementById("ft-vocab-learned-count");
      const vocabCurrentStatus = document.getElementById("ft-vocab-current-status");
      const vocabLearnedFilter = document.getElementById("ft-vocab-learned-filter");
      const vocabLearnedList = document.getElementById("ft-vocab-learned-list");
      const vocabLearnedConnector = document.getElementById("ft-vocab-learned-connector");
      const vocabLearnedPath = document.getElementById("ft-vocab-learned-path");
      const vocabUnlearnedPanel = document.getElementById("ft-vocab-unlearned-panel");
      const vocabUnlearnedCount = document.getElementById("ft-vocab-unlearned-count");
      const vocabUnlearnedList = document.getElementById("ft-vocab-unlearned-list");
      const vocabWeakConnector = document.getElementById("ft-vocab-weak-connector");
      const vocabWeakPath = document.getElementById("ft-vocab-weak-path");
      const vocabDetailPanel = document.getElementById("ft-vocab-detail-panel");
      const vocabDetailWord = document.getElementById("ft-vocab-detail-word");
      const vocabDetailList = document.getElementById("ft-vocab-detail-list");
      const vocabPicturePanel = document.getElementById("ft-vocab-picture-panel");
      const vocabPictureFrame = document.getElementById("ft-vocab-picture-frame");
      const vocabPictureImg = document.getElementById("ft-vocab-picture-img");
      const vocabPictureCaption = document.getElementById("ft-vocab-picture-caption");
      const vocabImageLightbox = document.getElementById("ft-vocab-image-lightbox");
      const vocabImageLightboxClose = document.getElementById("ft-vocab-image-lightbox-close");
      const vocabImageLightboxImg = document.getElementById("ft-vocab-image-lightbox-img");
      const vocabImageLightboxPrev = document.getElementById("ft-vocab-image-lightbox-prev");
      const vocabImageLightboxNext = document.getElementById("ft-vocab-image-lightbox-next");
      const vocabImageLightboxPage = document.getElementById("ft-vocab-image-lightbox-page");
      const vocabImageLightboxWord = document.getElementById("ft-vocab-image-lightbox-word");
      const vocabImageLightboxMeaning = document.getElementById("ft-vocab-image-lightbox-meaning");
      const vocabImageLightboxCaption = document.getElementById("ft-vocab-image-lightbox-caption");
      const vocabSideConnector = document.getElementById("ft-vocab-side-connector");
      const vocabDetailPath = document.getElementById("ft-vocab-detail-path");
      const vocabPicturePath = document.getElementById("ft-vocab-picture-path");
      const vocabPreflightGate = document.getElementById("ft-vocab-preflight-gate");
      const vocabPreflightTitle = document.getElementById("ft-vocab-preflight-title");
      const vocabPreflightText = document.getElementById("ft-vocab-preflight-text");
      const vocabPreflightCount = document.getElementById("ft-vocab-preflight-count");
      const vocabPreflightFiles = document.getElementById("ft-vocab-preflight-files");
      const vocabPreflightRemaining = document.getElementById("ft-vocab-preflight-remaining");
      const vocabPreflightLearn = document.getElementById("ft-vocab-preflight-learn");
      const vocabPreflightSkip = document.getElementById("ft-vocab-preflight-skip");
      const vocabPreflightStatus = document.getElementById("ft-vocab-preflight-status");
      const lessonEntryVocabAlert = document.getElementById("ft-entry-vocab-alert");
      const lessonEntryVocabAlertCount = document.getElementById("ft-entry-vocab-alert-count");
      const lessonEntryVocabAlertPacks = document.getElementById("ft-entry-vocab-alert-packs");
      const lessonEntryVocabAlertDetail = document.getElementById("ft-entry-vocab-alert-detail");
      const lessonEntryVocabAlertLearn = document.getElementById("ft-entry-vocab-alert-learn");
      const lessonEntryVocabAlertSkip = document.getElementById("ft-entry-vocab-alert-skip");
      const mobileTabs = document.getElementById("ft-mobile-tabs");
      const mobileTabButtons = Array.from(document.querySelectorAll(".ft-mobile-tab[data-panel]"));
      const connectorNode = document.getElementById("ft-connector");
      const connectorSvg = document.getElementById("ft-connector-svg");
      const connectorPath = document.getElementById("ft-connector-path");
      const connectorGlow = document.getElementById("ft-connector-glow");
      const ipaPanel = document.getElementById("ft-ipa-panel");
      const ipaNode = document.getElementById("ft-ipa");
      const ipaStars = document.getElementById("ft-ipa-stars");
      const englishNode = document.getElementById("ft-english");
      const speakPanel = document.getElementById("ft-speak-panel");
      const speakScore = document.getElementById("ft-speak-score");
      const speakStars = document.getElementById("ft-speak-stars");
      const speakMessage = document.getElementById("ft-speak-message");
      const speakModeToggleButton = document.getElementById("ft-speak-mode-toggle");
      const speakModeLabel = document.getElementById("ft-speak-mode-label");
      const speakRecordButton = document.getElementById("ft-speak-record");
      const speakReplayButton = document.getElementById("ft-speak-replay");
      const speakClearButton = document.getElementById("ft-speak-clear");
      const speakReportButton = document.getElementById("ft-speak-report");
      const speakWaveCanvas = document.getElementById("ft-speak-wave");
      const speakWaveLabel = document.getElementById("ft-speak-wave-label");
      const speakTranscript = document.getElementById("ft-speak-transcript");
      const speakWordsNode = document.getElementById("ft-speak-words");
      const speakStatus = document.getElementById("ft-speak-status");
      const scorePanel = document.getElementById("ft-score-panel");
      const scoreValue = document.getElementById("ft-score-value");
      const scoreMessage = document.getElementById("ft-score-message");
      const scoreStars = document.getElementById("ft-score-stars");
      const scoreCountdown = document.getElementById("ft-score-countdown");
      const scoreClockHand = document.getElementById("ft-score-clock-hand");
      const scoreWordsNode = document.getElementById("ft-score-words");
      const scoreHint = document.getElementById("ft-score-hint");
      const hintPanel = document.getElementById("ft-hint-panel");
      const hintText = document.getElementById("ft-hint-text");
      const hintAboutToggle = document.getElementById("ft-hint-about-toggle");
      const aboutPanel = document.getElementById("ft-about-panel");
      const aboutCount = document.getElementById("ft-about-count");
      const aboutQuestion = document.getElementById("ft-about-question");
      const aboutAnswer = document.getElementById("ft-about-answer");
      const aboutPreviewButton = document.getElementById("ft-about-preview");
      const aboutNextButton = document.getElementById("ft-about-next");
      const aboutTrainButton = document.getElementById("ft-about-train");
      const aboutHintToggle = document.getElementById("ft-about-hint-toggle");
      const grammarPanel = document.getElementById("ft-grammar-panel");
      const grammarProgress = document.getElementById("ft-grammar-progress");
      const grammarStars = document.getElementById("ft-grammar-stars");
      const grammarPrompt = document.getElementById("ft-grammar-prompt");
      const grammarStartGate = document.getElementById("ft-grammar-start-gate");
      const grammarStartButton = document.getElementById("ft-grammar-start");
      const grammarTarget = document.getElementById("ft-grammar-target");
      const grammarOptionsNode = document.getElementById("ft-grammar-options");
      const grammarFeedback = document.getElementById("ft-grammar-feedback");
      const grammarSkipButton = document.getElementById("ft-grammar-skip");
      const grammarSilentButton = document.getElementById("ft-grammar-silent");
      const voiceShell = document.getElementById("ft-voice-shell");
      const voiceProxy = document.getElementById("ft-voice-proxy");
      const voiceProxyText = document.getElementById("ft-voice-proxy-text");
      const voiceSelect = document.getElementById("ft-voice");
      const voicePicker = document.getElementById("ft-voice-picker");
      const voicePickerList = document.getElementById("ft-voice-picker-list");
      const voicePickerClose = document.getElementById("ft-voice-picker-close");
      const playButton = document.getElementById("ft-play");
      const nextButton = document.getElementById("ft-next");
      const ttsStatus = document.getElementById("ft-tts-status");
      const loadGate = document.getElementById("ft-load-gate");
      const loadFullscreenButton = document.getElementById("ft-load-fullscreen");
      const loadVoiceShell = document.getElementById("ft-load-voice-shell");
      const loadVoiceProxy = document.getElementById("ft-load-voice-proxy");
      const loadVoiceProxyText = document.getElementById("ft-load-voice-proxy-text");
      const loadStartButton = document.getElementById("ft-load-start");
      const loadReviewButton = document.getElementById("ft-load-review");
      const loadReviewTrainButton = document.getElementById("ft-load-review-train");
      const loadEnterNowButton = document.getElementById("ft-load-enter-now");
      const fileInput = document.getElementById("ft-file-input");
      const loadStatus = document.getElementById("ft-load-status");
      const lessonEntryGate = document.getElementById("ft-lesson-entry-gate");
      const lessonEntryGateFrame = document.getElementById("ft-entry-gate-frame");
      const lessonEntryGateKicker = document.getElementById("ft-entry-gate-kicker");
      const lessonEntryGateTitle = document.getElementById("ft-entry-gate-title");
      const lessonEntryGate2Status = document.getElementById("ft-entry-gate2-status");
      const lessonEntryGate2Led = document.getElementById("ft-entry-gate2-led");
      const lessonEntryPrimaryLed = document.getElementById("ft-entry-primary-led");
       const lessonEntryGateClock = document.getElementById("ft-entry-gate-clock");
       const lessonEntryPdfStream = document.getElementById("ft-entry-pdf-stream");
       const lessonEntryPdfStreamPhase = document.getElementById("ft-entry-pdf-stream-phase");
       const lessonEntryPdfStreamPercent = document.getElementById("ft-entry-pdf-stream-percent");
       const lessonEntryPdfStreamGraph = document.getElementById("ft-entry-pdf-stream-graph");
       const lessonEntryPdfStreamProgressRing = document.getElementById("ft-entry-pdf-stream-progress-ring");
       const lessonEntryPdfStreamFill = document.getElementById("ft-entry-pdf-stream-fill");
       const lessonEntryPdfStreamChunk = document.getElementById("ft-entry-pdf-stream-chunk");
       const lessonEntryPdfStreamBytes = document.getElementById("ft-entry-pdf-stream-bytes");
       const lessonEntryGateOpenButton = document.getElementById("ft-entry-gate-open");
      const lessonEntryGateContinueButton = document.getElementById("ft-entry-gate-continue");
      const lessonEntryGateTrainButton = document.getElementById("ft-entry-gate-train");
      const lessonEntryGateExitButton = document.getElementById("ft-entry-gate-exit");
      const topLoading = document.getElementById("ft-top-loading");
      const topLoadingText = document.getElementById("ft-top-loading-text");
      const serverOpenButton = document.getElementById("ft-server-open");
      const taskOpenButton = document.getElementById("ft-task-open");
      const serverBrowser = document.getElementById("ft-server-browser");
      const serverBrowserLayout = document.getElementById("ft-server-browser-layout");
      const serverBrowserTabs = document.getElementById("ft-server-browser-tabs");
      const serverBrowserTabButtons = Array.from(document.querySelectorAll(".ft-server-browser-tab[data-server-panel]"));
      const serverBrowserNoticeTab = document.getElementById("ft-server-browser-tab-notice");
      const serverFullscreenButton = document.getElementById("ft-server-fullscreen");
      const serverCloseButton = document.getElementById("ft-server-close");
      const serverPathNode = document.getElementById("ft-server-path");
      const serverNavNode = document.getElementById("ft-server-nav");
      const serverBackButton = document.getElementById("ft-server-back");
      const serverRecentFileButton = document.getElementById("ft-server-recent-file");
      const serverRecentFileNameNode = document.getElementById("ft-server-recent-name");
      const serverRecentFilePopover = document.getElementById("ft-server-recent-popover");
      const serverWorkerRegisterButtons = Array.from(document.querySelectorAll("#ft-worker-toolbar-button, #ft-worker-open, #ft-server-worker-register"));
      const serverListNode = document.getElementById("ft-server-list");
      const taskModal = document.getElementById("ft-task-modal");
      const taskCloseButton = document.getElementById("ft-task-close");
      const taskStatsRefreshButton = document.getElementById("ft-task-stats-refresh");
      const taskEffectTestPendingButton = document.getElementById("ft-task-effect-test-pending");
      const taskEffectTestOverdueButton = document.getElementById("ft-task-effect-test-overdue");
      const taskNoticeAdmin = document.getElementById("ft-task-notice-admin");
      const taskNoticeReset = document.getElementById("ft-task-notice-reset");
      const taskNoticeCloseButton = document.getElementById("ft-task-notice-close");
      const taskNoticeText = document.getElementById("ft-task-notice-text");
      const taskNoticeTextEn = document.getElementById("ft-task-notice-text-en");
      const taskNoticeTextVi = document.getElementById("ft-task-notice-text-vi");
      const taskNoticeLanguage = document.getElementById("ft-task-notice-language");
      const taskNoticeVoice = document.getElementById("ft-task-notice-voice");
      const taskNoticeVoiceEn = document.getElementById("ft-task-notice-voice-en");
      const taskNoticeVoiceVi = document.getElementById("ft-task-notice-voice-vi");
      const taskNoticePaneEn = document.getElementById("ft-task-notice-pane-en");
      const taskNoticePaneVi = document.getElementById("ft-task-notice-pane-vi");
      const taskNoticeTranslateEn = document.getElementById("ft-task-notice-translate-en");
      const taskNoticeTranslateVi = document.getElementById("ft-task-notice-translate-vi");
      const taskNoticeStyle = document.getElementById("ft-task-notice-style");
      const taskNoticeName = document.getElementById("ft-task-notice-name");
      const taskNoticeAvatar = document.getElementById("ft-task-notice-avatar");
      const taskNoticeAvatarUpload = document.getElementById("ft-task-notice-avatar-upload");
      const taskNoticeAvatarFile = document.getElementById("ft-task-notice-avatar-file");
      const taskNoticeRepeatCount = document.getElementById("ft-task-notice-repeat-count");
      const taskNoticeBackGap = document.getElementById("ft-task-notice-back-gap");
      const taskNoticeOnce = document.getElementById("ft-task-notice-once");
      const taskNoticeDay = document.getElementById("ft-task-notice-day");
      const taskNoticeAlways = document.getElementById("ft-task-notice-always");
      const taskNoticeUntilComplete = document.getElementById("ft-task-notice-until-complete");
      const taskNoticeAudio = document.getElementById("ft-task-notice-audio");
      const taskNoticeAck = document.getElementById("ft-task-notice-ack");
      const taskNoticeAdd = document.getElementById("ft-task-notice-add");
      const taskNoticeSendNow = document.getElementById("ft-task-notice-send-now");
      const taskNoticePreview = document.getElementById("ft-task-notice-preview");
      const taskNoticeState = document.getElementById("ft-task-notice-state");
      const taskNoticeList = document.getElementById("ft-task-notice-list");
      const taskUserNotice = document.getElementById("ft-task-user-notice");
      const taskUserNoticeFace = document.getElementById("ft-task-user-notice-face");
      const taskUserNoticeAvatar = document.getElementById("ft-task-user-notice-avatar");
      const taskUserNoticeName = document.getElementById("ft-task-user-notice-name");
      const taskUserNoticeVoice = document.getElementById("ft-task-user-notice-voice");
      const taskUserNoticeText = document.getElementById("ft-task-user-notice-text");
      const taskUserNoticeTextCopy = document.getElementById("ft-task-user-notice-text-copy");
      const taskUserNoticeSub = document.getElementById("ft-task-user-notice-sub");
      const taskUserNoticeTranslation = document.getElementById("ft-task-user-notice-translation");
      const taskUserNoticeTranslationText = document.getElementById("ft-task-user-notice-translation-text");
      const taskUserNoticeTranslationCopy = document.getElementById("ft-task-user-notice-translation-copy");
      const taskUserNoticeRead = document.getElementById("ft-task-user-notice-read");
      const aiNoticeSave = document.getElementById("ft-ai-notice-save");
      const aiNoticeSaveTitle = document.getElementById("ft-ai-notice-save-title");
      const aiNoticeSaveButton = document.getElementById("ft-ai-notice-save-button");
      const aiNoticeSaveStatus = document.getElementById("ft-ai-notice-save-status");
      const aiNoticeHistoryButton = document.getElementById("ft-ai-notice-history-button");
      const aiHistoryPanel = document.getElementById("ft-ai-history-panel");
      const aiHistoryClose = document.getElementById("ft-ai-history-close");
      const aiHistoryList = document.getElementById("ft-ai-history-list");
      const aiHistoryDetail = document.getElementById("ft-ai-history-detail");
      const aiHistoryDetailTitle = document.getElementById("ft-ai-history-detail-title");
      const aiHistoryDetailEn = document.getElementById("ft-ai-history-detail-en");
      const aiHistoryDetailVi = document.getElementById("ft-ai-history-detail-vi");
      const taskAiMetricMeters = Array.from(document.querySelectorAll("[data-ai-meter]"));
      const taskUserNoticeScrollButtons = Array.from(document.querySelectorAll("[data-task-notice-scroll]"));
      const taskTitleNode = document.getElementById("ft-task-title");
      const taskModeSwitchButton = document.getElementById("ft-task-mode-switch");
      const taskSpaceFoldersButton = document.getElementById("ft-task-space-folders");
      const taskNoticeToggleButton = document.getElementById("ft-task-notice-toggle");
      const serverTaskOwnerNode = document.getElementById("ft-server-task-owner");
      const taskLearningSummaryNode = document.getElementById("ft-task-learning-summary");
      const taskSummaryNode = document.getElementById("ft-task-summary");
      const taskTotalNode = document.getElementById("ft-task-total");
      const taskCriticalNode = document.getElementById("ft-task-critical");
      const taskCompleteNode = document.getElementById("ft-task-complete");
      const serverTaskListNode = document.getElementById("ft-server-task-list");
      const completeGate = document.getElementById("ft-complete-gate");
      const completeMessage = document.getElementById("ft-complete-message");
      const completeLessonNode = document.getElementById("ft-complete-lesson");
      const completeNodesNode = document.getElementById("ft-complete-nodes");
      const completeRunsNode = document.getElementById("ft-complete-runs");
      const completeCrystalTotalNode = document.getElementById("ft-complete-crystal-total");
      const completeCrystalGrid = document.getElementById("ft-complete-crystal-grid");
      const completeReviewButton = document.getElementById("ft-complete-review");
      const completeSelectButton = document.getElementById("ft-complete-select");
      const sampleButton = document.getElementById("ft-sample");
      const createPanelConnector = (name) => {
        const node = connectorNode.cloneNode(true);
        node.id = `ft-connector-${name}`;
        node.dataset.panel = name;
        node.classList.remove("is-live", "is-complete", "is-active", "is-dim");
        node.querySelectorAll("[id]").forEach((child) => child.removeAttribute("id"));
        const gradient = node.querySelector("linearGradient");
        if (gradient) {
          gradient.id = `ft-connector-gradient-${name}`;
          const path = node.querySelector(".ft-connector-path");
          if (path) {
            path.style.stroke = `url(#${gradient.id})`;
          }
        }
        connectorNode.parentNode.insertBefore(node, connectorNode);
        return node;
      };
      const scoreConnector = createPanelConnector("score");
      const hintConnector = createPanelConnector("hint");
      const aboutConnector = createPanelConnector("about");
      const grammarConnector = createPanelConnector("grammar");
      const speakConnector = createPanelConnector("speak");
      const ipaConnector = connectorNode;
      ipaConnector.dataset.panel = "ipa";
      const EDGE_TRUSTED_CLIENT_TOKEN = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
      const EDGE_VOICE_LIST_URL = `https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclienttoken=${EDGE_TRUSTED_CLIENT_TOKEN}`;
      const EDGE_WS_URL = `wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=${EDGE_TRUSTED_CLIENT_TOKEN}`;
      const EDGE_AUDIO_FORMAT = "audio-24khz-48kbitrate-mono-mp3";
      const CONNECTOR_DRAW_MS = 720;

      const defaults = {
        vi: "Tôi muốn một ly nước.",
        en: "I would like a glass of water.",
        ipa: "/aɪ wʊd laɪk ə ɡlæs əv ˈwɔːtər/",
      };

      const clean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();
      const FUTURE_ROUTE_ALIASES = {
        login: "login",
        auth: "login",
        lesson_vault: "lesson_vault",
        vault: "lesson_vault",
        lessons: "lesson_vault",
        space_w: "space_w",
        spacew: "space_w",
        w: "space_w",
        space_v: "space_v",
        spacev: "space_v",
        v: "space_v",
        space_b: "space_v",
        spaceb: "space_v",
        b: "space_v",
        space_q: "space_q",
        spaceq: "space_q",
        q: "space_q",
        space_p: "space_p",
        spacep: "space_p",
        p: "space_p",
        space_s: "space_s",
        spaces: "space_s",
        s: "space_s",
        space_l: "space_l",
        spacel: "space_l",
        l: "space_l",
        space_pdf: "space_pdf",
        spacepdf: "space_pdf",
        pdf: "space_pdf",
        space_picture: "space_picture",
        spacepicture: "space_picture",
        picture: "space_picture",
        image: "space_picture",
      };
      const FUTURE_ROUTE_PATHS = {
        login: "/login",
        lesson_vault: "/lesson_vault",
        space_w: "/space_w",
        space_v: "/space_v",
        space_q: "/space_q",
        space_p: "/space_p",
        space_s: "/space_s",
        space_l: "/space_l",
        space_pdf: "/space_pdf",
        space_picture: "/space_picture",
      };
      const FUTURE_APP_TITLE_BRAND = "QM-Tech";
      const FUTURE_FRONTEND_BUILD_STAMP = "2026-07-07 02:19:25";
      let futureFrontendVersionState = {
        version: "local-build",
        updatedAt: FUTURE_FRONTEND_BUILD_STAMP,
        label: `Frontend version local-build | updated ${FUTURE_FRONTEND_BUILD_STAMP}`,
      };
      const FUTURE_ROUTE_TITLE_LABELS = {
        login: "Login",
        lesson_vault: "Lesson Vault",
        space_w: "Space W",
        space_v: "Space V",
        space_q: "Space Q",
        space_p: "Space P",
        space_s: "Space S",
        space_l: "Space L",
        space_pdf: "Space PDF",
        space_picture: "Space Picture",
      };
      const normalizeFutureAppRoute = (route = "") => FUTURE_ROUTE_ALIASES[clean(route).toLowerCase().replace(/[-\s]+/g, "_")] || "";
      const futureAppRouteFromLocation = () => {
        const pathname = String(window.location.pathname || "/").replace(/\/+$/, "") || "/";
        const lower = pathname.toLowerCase();
        let tail = "";
        if (lower === "/" || lower === "/future.html" || lower === "/future") {
          tail = "login";
        } else if (lower.startsWith("/future.html/")) {
          tail = pathname.slice("/future.html/".length).split("/")[0] || "";
        } else {
          tail = pathname.replace(/^\/+/, "").split("/")[0] || "";
        }
        return normalizeFutureAppRoute(tail);
      };
      const FUTURE_ROUTE_TREE_PARAM = "tree";
      const FUTURE_ROUTE_FILE_PARAM = "file";
      const FUTURE_ROUTE_PROCESS_PARAM = "process";
      const cleanFutureRoutePathValue = (pathValue = "") => String(pathValue || "")
        .replace(/\\/g, "/")
        .replace(/[\r\n\t]+/g, " ")
        .replace(/^\/+|\/+$/g, "")
        .split("/")
        .map((part) => part.trim())
        .filter(Boolean)
        .join("/");
      const futureRouteParentForPath = (pathValue = "") => {
        const raw = cleanFutureRoutePathValue(pathValue);
        const slash = raw.lastIndexOf("/");
        return slash > 0 ? raw.slice(0, slash) : "";
      };
      const futureRouteSpaceForFilePath = (pathValue = "") => {
        const lower = cleanFutureRoutePathValue(pathValue).toLowerCase();
        if (lower.endsWith(".space_b")) return "space_v";
        if (lower.endsWith(".space_v")) return "space_v";
        if (lower.endsWith(".space_q")) return "space_q";
        if (lower.endsWith(".space_p")) return "space_p";
        if (lower.endsWith(".space_s")) return "space_s";
        if (lower.endsWith(".space_l")) return "space_l";
        if (lower.endsWith(".space_w")) return "space_w";
        if (lower.endsWith(".pdf")) return "space_pdf";
        if (/\.(png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i.test(lower)) return "space_picture";
        return "";
      };
      const futureRouteStateFromLocation = () => {
        const params = new URLSearchParams(window.location.search || "");
        const file = cleanFutureRoutePathValue(params.get(FUTURE_ROUTE_FILE_PARAM) || "");
        const tree = cleanFutureRoutePathValue(params.get(FUTURE_ROUTE_TREE_PARAM) || "");
        const process = normalizeFutureAppRoute(params.get(FUTURE_ROUTE_PROCESS_PARAM) || "") || futureRouteSpaceForFilePath(file);
        return {
          route: futureAppRouteFromLocation(),
          tree,
          file,
          process,
          task_owner: clean(params.get("task_owner") || params.get("owner") || ""),
          page: Math.max(0, Math.floor(Number(params.get("page") || 0) || 0)),
        };
      };
      // Added 2026-07-07: shows frontend build/update time in the tab and login HUD so stale client cache is obvious.
      const shortFrontendVersionText = (value = "") => {
        const text = clean(value);
        if (!text) return "local-build";
        const match = text.match(/[0-9a-f]{10,}/i);
        if (match) return match[0].slice(0, 10);
        return text.replace(/^W\/"?|"?$/g, "").slice(0, 18);
      };
      const frontendVersionTitleSuffix = () => clean(futureFrontendVersionState.updatedAt || FUTURE_FRONTEND_BUILD_STAMP);
      const updateAuthHudVersionLine = () => {
        if (!authHudList) return;
        let row = document.getElementById("ft-auth-hud-version");
        if (!row) {
          row = document.createElement("div");
          row.className = "ft-auth-hud-message ft-auth-hud-version";
          row.id = "ft-auth-hud-version";
          authHudList.appendChild(row);
        }
        row.textContent = clean(futureFrontendVersionState.label) || `Frontend version local-build | updated ${FUTURE_FRONTEND_BUILD_STAMP}`;
      };
      // Added 2026-07-05: keeps the browser tab title aligned with the active QM-Tech space.
      const updateFutureDocumentTitle = (routeState = {}) => {
        const route = normalizeFutureAppRoute(routeState.route || "") || futureAppRouteFromLocation() || "login";
        const process = normalizeFutureAppRoute(routeState.process || "");
        const label = FUTURE_ROUTE_TITLE_LABELS[process || route] || FUTURE_ROUTE_TITLE_LABELS[route] || "Lesson Vault";
        const filePath = cleanFutureRoutePathValue(routeState.file || routeState.path || "");
        const rawName = clean(routeState.name || (filePath ? filePath.split("/").pop() : ""));
        const lessonName = clean(rawName.replace(/\.(space_w|space_v|space_b|space_q|space_p|space_s|space_l|pdf|txt|png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i, ""));
        const titleParts = [FUTURE_APP_TITLE_BRAND, label];
        if (lessonName && !["login", "lesson_vault"].includes(route)) {
          titleParts.push(lessonName.length > 56 ? `${lessonName.slice(0, 53)}...` : lessonName);
        }
        titleParts.push(frontendVersionTitleSuffix());
        document.title = titleParts.filter(Boolean).join(" - ");
      };
      updateFutureDocumentTitle(futureRouteStateFromLocation());
      updateAuthHudVersionLine();
      const updateFutureAppRoute = (route = "", options = {}) => {
        const key = normalizeFutureAppRoute(route) || "login";
        const targetPath = FUTURE_ROUTE_PATHS[key] || "/login";
        const params = new URLSearchParams(window.location.search || "");
        params.delete(FUTURE_ROUTE_TREE_PARAM);
        params.delete(FUTURE_ROUTE_FILE_PARAM);
        params.delete(FUTURE_ROUTE_PROCESS_PARAM);
        params.delete("task_owner");
        params.delete("owner");
        params.delete("page");
        const currentSource = typeof currentLessonSource === "object" && currentLessonSource ? currentLessonSource : {};
        const optionFile = cleanFutureRoutePathValue(options.file || options.path || "");
        const currentFile = cleanFutureRoutePathValue(currentSource.path || "");
        const filePath = optionFile || (key.startsWith("space_") ? currentFile : "");
        const fallbackTree = filePath ? futureRouteParentForPath(filePath) : "";
        const optionTree = cleanFutureRoutePathValue(options.tree || options.browserPath || "");
        const currentTree = cleanFutureRoutePathValue(typeof serverBrowserPath === "string" ? serverBrowserPath : "");
        const storedTree = typeof getStoredServerPath === "function" ? cleanFutureRoutePathValue(getStoredServerPath()) : "";
        const treePath = optionTree || fallbackTree || (key === "lesson_vault" ? (currentTree || storedTree) : "");
        const taskOwner = clean(options.task_owner || options.taskOwner || "");
        const processKey = normalizeFutureAppRoute(options.process || "") || (filePath ? futureRouteSpaceForFilePath(filePath) : (key.startsWith("space_") ? key : ""));
        if (key !== "login") {
          if (treePath) {
            params.set(FUTURE_ROUTE_TREE_PARAM, treePath);
          }
          if (filePath) {
            params.set(FUTURE_ROUTE_FILE_PARAM, filePath);
          }
          if (processKey) {
            params.set(FUTURE_ROUTE_PROCESS_PARAM, processKey);
          }
          if (taskOwner) {
            params.set("task_owner", taskOwner);
          }
          if (Number(options.page || 0) > 0) {
            params.set("page", String(Math.max(1, Math.floor(Number(options.page) || 1))));
          }
        }
        updateFutureDocumentTitle({
          route: key,
          tree: treePath,
          file: filePath,
          process: processKey,
          task_owner: taskOwner,
          name: options.name || "",
        });
        const query = params.toString();
        const nextUrl = `${targetPath}${query ? `?${query}` : ""}${window.location.hash || ""}`;
        const currentUrl = `${window.location.pathname}${window.location.search || ""}${window.location.hash || ""}`;
        if (nextUrl === currentUrl || !window.history || typeof window.history.pushState !== "function") {
          return;
        }
        const method = options.replace ? "replaceState" : "pushState";
        try {
          window.history[method]({ futureRoute: key }, "", nextUrl);
        } catch (error) {
        }
      };
      const routeForLessonPayload = (payload = {}) => {
        if (isVocabularyPayload(payload)) {
          return "space_v";
        }
        if (isQuestionPayload(payload)) {
          return "space_q";
        }
        if (isParagraphPayload(payload)) {
          return "space_p";
        }
        return "space_w";
      };
      const AUTH_PASSWORD_MOTION_MS = 1800;
      const AUTH_LOGIN_CONNECTOR_FX_ENABLED = true;
      const AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED = false;
      const setAuthIdleMotionPaused = (paused) => {
        const authVisible = Boolean(authGate && !authGate.classList.contains("is-hidden"));
        document.documentElement.classList.toggle("ft-auth-idle-motion-paused", Boolean(paused && authVisible));
      };
      const isMobileAuthMotionSurface = () => window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
      const stopAuthFocusMotion = () => {
        if (authMotionTimer) {
          window.clearTimeout(authMotionTimer);
          authMotionTimer = 0;
        }
        if (authMotionWarmTimer) {
          window.clearTimeout(authMotionWarmTimer);
          authMotionWarmTimer = 0;
        }
        if (authGate) {
          authGate.classList.remove("is-auth-password-focus", "is-auth-motion-warming", "is-auth-motion-full");
        }
        setAuthIdleMotionPaused(true);
        startAuthConnectorOutro();
      };
      const canRunAuthFocusMotion = () => {
        if (!authGate) {
          return false;
        }
        const authVisible = !authGate.classList.contains("is-hidden");
        const fullscreenPromptVisible = Boolean(
          startFullscreenGate && !startFullscreenGate.classList.contains("is-hidden"),
        );
        return authVisible && !fullscreenPromptVisible && !isMobileAuthMotionSurface();
      };
      const pulseAuthFocusMotion = (durationMs = AUTH_PASSWORD_MOTION_MS) => {
        if (!canRunAuthFocusMotion()) {
          stopAuthFocusMotion();
          return;
        }
        setAuthIdleMotionPaused(false);
        authGate.classList.add("is-auth-password-focus");
        startAuthConnectorIntro();
        if (!authGate.classList.contains("is-auth-motion-full") && !authGate.classList.contains("is-auth-motion-warming")) {
          authGate.classList.add("is-auth-motion-warming");
          if (authMotionWarmTimer) {
            window.clearTimeout(authMotionWarmTimer);
          }
          authMotionWarmTimer = window.setTimeout(() => {
            authMotionWarmTimer = 0;
            window.requestAnimationFrame(() => {
              window.requestAnimationFrame(() => {
                if (!canRunAuthFocusMotion() || !authGate || !authGate.classList.contains("is-auth-password-focus")) {
                  return;
                }
                authGate.classList.remove("is-auth-motion-warming");
                authGate.classList.add("is-auth-motion-full");
              });
            });
          }, 220);
        }
        if (authMotionTimer) {
          window.clearTimeout(authMotionTimer);
          authMotionTimer = 0;
        }
        if (authPass && document.activeElement === authPass) {
          return;
        }
        authMotionTimer = window.setTimeout(() => {
          authMotionTimer = 0;
          if (authPass && document.activeElement === authPass && canRunAuthFocusMotion()) {
            setAuthIdleMotionPaused(false);
            authGate.classList.add("is-auth-password-focus");
            return;
          }
          stopAuthFocusMotion();
        }, Math.max(450, Number(durationMs) || AUTH_PASSWORD_MOTION_MS));
      };
      const syncAuthPasswordFocusMotion = () => {
        const passwordFocused = Boolean(authPass && document.activeElement === authPass);
        if (!passwordFocused || !canRunAuthFocusMotion()) {
          stopAuthFocusMotion();
          return;
        }
        pulseAuthFocusMotion();
      };
      const syncServerWorkspaceOpenState = () => {
        document.documentElement.classList.toggle("ft-server-workspace-open", Boolean(serverBrowser && !serverBrowser.hidden));
      };
      if (serverBrowser && window.MutationObserver) {
        new MutationObserver(syncServerWorkspaceOpenState).observe(serverBrowser, {
          attributes: true,
          attributeFilter: ["hidden"],
        });
      }
      syncServerWorkspaceOpenState();
      const preserveQuestionText = (value) => String(value == null ? "" : value)
        .replace(/\r\n?/g, "\n")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/\n{4,}/g, "\n\n\n")
        .replace(/^\n+|\n+$/g, "");
      const escapeHtml = (value) => String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
      const clampRuntimeProgressPercent = (value) => Math.max(0, Math.min(100, Number(value) || 0));
      const renderRuntimeProgress = (target, options = {}) => {
        if (!target) {
          return;
        }
        const total = Math.max(0, Math.floor(Number(options.total || 0) || 0));
        const done = Math.max(0, Math.min(total || Math.max(0, Math.floor(Number(options.done || 0) || 0)), Math.floor(Number(options.done || 0) || 0)));
        const percent = total > 0
          ? clampRuntimeProgressPercent((done / total) * 100)
          : clampRuntimeProgressPercent(options.percent);
        const label = clean(options.label || "Progress");
        const value = clean(options.value || `${done}/${total}`);
        const detail = clean(options.detail || `${Math.round(percent)}%`);
        const detailItems = Array.isArray(options.detailItems)
          ? options.detailItems.map((item) => clean(item)).filter(Boolean)
          : [];
        const detailMarkup = detailItems.length
          ? `<span class="ft-runtime-progress-chips">${detailItems.map((item) => `<i>${escapeHtml(item)}</i>`).join("")}</span>`
          : `<span>${escapeHtml(detail)}</span>`;
        const className = clean(options.className || "");
        target.classList.add("has-runtime-progress");
        target.innerHTML = `
          <span class="ft-runtime-progress ${escapeHtml(className)}" style="--ft-runtime-progress: ${percent.toFixed(2)}%;">
            <span class="ft-runtime-progress-head"><b>${escapeHtml(label)}</b>${detailMarkup}</span>
            <span class="ft-runtime-progress-track"><span class="ft-runtime-progress-fill"></span><span class="ft-runtime-progress-value">${escapeHtml(value)}</span></span>
          </span>
        `;
      };
      const clearRuntimeProgress = (target, text = "") => {
        if (!target) {
          return;
        }
        target.classList.remove("has-runtime-progress");
        target.textContent = text;
      };
      const hardenLearningInput = (input) => {
        if (!input) {
          return;
        }
        const stamp = Math.random().toString(36).slice(2);
        const attrs = {
          autocomplete: "one-time-code",
          autocapitalize: "none",
          autocorrect: "off",
          spellcheck: "false",
          inputmode: "text",
          enterkeyhint: "done",
          "aria-autocomplete": "none",
          "data-form-type": "other",
          "data-lpignore": "true",
          "data-1p-ignore": "true",
          "data-bwignore": "true",
          "data-bitwarden-watching": "0",
          "data-protonpass-ignore": "true",
          "data-keeper-ignore": "true",
          "data-dashlane-ignore": "true",
          "data-roboform": "off",
          "data-gramm": "false",
          "data-ms-editor": "false",
          name: `ft_field_${stamp}`,
        };
        Object.entries(attrs).forEach(([key, value]) => input.setAttribute(key, value));
        input.readOnly = true;
        const unlock = () => {
          input.readOnly = false;
        };
        input.addEventListener("pointerdown", unlock, { once: true });
        input.addEventListener("touchstart", unlock, { once: true, passive: true });
        input.addEventListener("focus", unlock);
      };
      hardenLearningInput(answerInput);
      hardenLearningInput(vocabAnswer);
      hardenLearningInput(qAnswerInput);

      const hardenPrivateInput = (input, key = "private") => {
        if (!input) {
          return;
        }
        const stamp = Math.random().toString(36).slice(2);
        const secretField = key.includes("secret") || input.classList.contains("ft-secret-input");
        if (secretField && input.type !== "text") {
          try {
            input.type = "text";
          } catch (error) {
          }
        }
        if (secretField) {
          input.classList.add("ft-secret-input");
          input.setAttribute("inputmode", "text");
        }
        const attrs = {
          autocomplete: "one-time-code",
          autocorrect: "off",
          spellcheck: "false",
          translate: "no",
          "aria-autocomplete": "none",
          "data-form-type": "other",
          "data-lpignore": "true",
          "data-1p-ignore": "true",
          "data-bwignore": "true",
          "data-bitwarden-watching": "0",
          "data-protonpass-ignore": "true",
          "data-keeper-ignore": "true",
          "data-dashlane-ignore": "true",
          "data-roboform": "off",
          "data-gramm": "false",
          "data-ms-editor": "false",
          name: `ft_field_${stamp}`,
        };
        if (input.type !== "date") {
          attrs.autocapitalize = key === "full_name" ? "words" : "none";
          attrs.inputmode = "text";
          attrs.enterkeyhint = key === "login_id" || key === "confirm_secret" || key === "full_name" ? "next" : "go";
        }
        Object.entries(attrs).forEach(([attr, value]) => input.setAttribute(attr, value));
        input.readOnly = true;
        const unlock = () => {
          input.readOnly = false;
        };
        input.addEventListener("pointerdown", unlock, { once: true });
        input.addEventListener("touchstart", unlock, { once: true, passive: true });
        input.addEventListener("focus", unlock);
      };

      [document.documentElement, document.body, authGate, loadGate, serverBrowser].forEach((node) => {
        if (!node) {
          return;
        }
        node.setAttribute("translate", "no");
        node.classList.add("notranslate");
      });
      hardenPrivateInput(authUser, "login_id");
      hardenPrivateInput(authPass, "login_secret");
      hardenPrivateInput(authConfirm, "confirm_secret");
      hardenPrivateInput(authFullName, "full_name");
      hardenPrivateInput(authBirth, "birth_date");
      hardenPrivateInput(authEmail, "recovery_email");
      hardenPrivateInput(profileEditEmail, "recovery_email");
      if (authGender) {
        authGender.setAttribute("autocomplete", "one-time-code");
        authGender.setAttribute("translate", "no");
        authGender.setAttribute("data-form-type", "other");
      }

      const WHISPER_SERVER_PORT = clean(params.get("whisper_port")) || "8765";
      const normalizeWhisperBase = (value) => clean(value).replace(/\/+$/, "");
      const addWhisperCandidate = (items, value) => {
        const base = normalizeWhisperBase(value);
        if (base && !items.includes(base)) {
          items.push(base);
        }
      };
      const isLocalWhisperHost = () => {
        const host = clean(location.hostname).toLowerCase();
        return location.protocol === "file:"
          || host === "localhost"
          || host === "127.0.0.1"
          || host === "::1"
          || host === "[::1]";
      };
      const buildWhisperCandidates = () => {
        const items = [];
        const configured = clean(params.get("whisper") || params.get("whisper_url"));
        if (configured) {
          configured.split(/[|,;]/).forEach((item) => addWhisperCandidate(items, item));
        }
        if (
          /^https?:$/i.test(location.protocol)
          && (
            location.protocol === "http:"
            || !/(^|\.)googleusercontent\.com$/i.test(location.hostname || "")
            && !/(^|\.)sites\.google\.com$/i.test(location.hostname || "")
          )
        ) {
          addWhisperCandidate(items, location.origin);
        }
        if (isLocalWhisperHost()) {
          addWhisperCandidate(items, `http://127.0.0.1:${WHISPER_SERVER_PORT}`);
          addWhisperCandidate(items, `http://localhost:${WHISPER_SERVER_PORT}`);
        }
        return items;
      };
      const WHISPER_SERVER_CANDIDATES = buildWhisperCandidates();
      const WHISPER_SERVER_URL = WHISPER_SERVER_CANDIDATES[0] || `http://127.0.0.1:${WHISPER_SERVER_PORT}`;
      const ANTI_ROBOT_HEADER = "X-Future-Anti-Robot";
      let antiRobotToken = "";
      let antiRobotTokenAt = 0;
      let antiRobotTokenPromise = null;
      const antiRobotTokenIsFresh = () => antiRobotToken && Date.now() - antiRobotTokenAt < 16 * 60 * 1000;
      const fetchWithTimeout = async (url, options = {}, timeoutMs = 7000) => {
        const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        let timedOut = false;
        const numericTimeoutMs = Number(timeoutMs);
        const useTimeout = Number.isFinite(numericTimeoutMs) ? numericTimeoutMs > 0 : true;
        const safeTimeoutMs = useTimeout ? Math.max(1200, Number.isFinite(numericTimeoutMs) ? numericTimeoutMs : 7000) : 0;
        // Honor a caller-provided AbortSignal (e.g. superseded Lesson Vault
        // loads) by forwarding its abort to our internal controller. Aborts
        // that come from the external signal are not timeouts.
        const externalSignal = options && options.signal ? options.signal : null;
        let externalAborted = false;
        let onExternalAbort = null;
        if (externalSignal && controller) {
          if (externalSignal.aborted) {
            externalAborted = true;
            try { controller.abort(); } catch (abortError) {}
          } else {
            onExternalAbort = () => {
              externalAborted = true;
              try { controller.abort(); } catch (abortError) {}
            };
            try { externalSignal.addEventListener("abort", onExternalAbort, { once: true }); } catch (listenError) {}
          }
        }
        const forwardOptions = { ...options };
        delete forwardOptions.signal;
        const timer = controller && useTimeout
          ? window.setTimeout(() => {
            try {
              timedOut = true;
              controller.abort();
            } catch (error) {
              // The request is already settled.
            }
          }, safeTimeoutMs)
          : 0;
        try {
          return await fetch(url, {
            ...forwardOptions,
            ...(controller ? { signal: controller.signal } : (externalSignal ? { signal: externalSignal } : {})),
          });
        } catch (error) {
          if (externalAborted) {
            const abortError = new Error("Request superseded.");
            abortError.name = "AbortError";
            abortError.isAbortError = true;
            throw abortError;
          }
          if (timedOut || (error && clean(error.name).toLowerCase() === "aborterror")) {
            throw new Error(`Request timed out after ${Math.round(safeTimeoutMs / 1000)}s.`);
          }
          throw error;
        } finally {
          if (timer) {
            window.clearTimeout(timer);
          }
          if (externalSignal && onExternalAbort) {
            try { externalSignal.removeEventListener("abort", onExternalAbort); } catch (removeError) {}
          }
        }
      };

      // Added 2026-07-02: caches Server 2 audio locally across app users in the same browser profile.
      const installFutureAudioCacheLayer = () => {
        if (window.__futureAudioCacheLayerInstalled) {
          return;
        }
        window.__futureAudioCacheLayerInstalled = true;
        const nativeFetch = window.fetch ? window.fetch.bind(window) : null;
        const nativePlay = window.HTMLMediaElement && window.HTMLMediaElement.prototype && window.HTMLMediaElement.prototype.play;
        if (!nativeFetch) {
          return;
        }
        const DB_NAME = "future_server2_audio_cache_v1";
        const AUDIO_STORE = "audio";
        const AUDIO_META_STORE = "meta";
        const SPEAK_PREFIX = "future_pdf_speak_payload:";
        const blobUrlByKey = new Map();
        const pendingAudioByKey = new Map();
        const revisionedQmSoundUrlBySemanticKey = new Map();
        const mediaOriginalSrc = new WeakMap();
        const audioFetchControllers = new Set();
        let dbPromise = null;
        let audioDb = null;
        let audioCacheGeneration = 0;
        let forceNetworkReloadGeneration = -1;
        const audioCacheTrace = [];
        const recordAudioCacheTrace = (event = {}) => {
          audioCacheTrace.push({ at: new Date().toISOString(), generation: audioCacheGeneration, ...event });
          if (audioCacheTrace.length > 200) audioCacheTrace.splice(0, audioCacheTrace.length - 200);
          window.__futureAudioCacheTrace = audioCacheTrace;
          try {
            document.documentElement.dataset.futureAudioEpoch = String(globalAudioCacheEpoch || 0);
            document.documentElement.dataset.futureAudioGeneration = String(audioCacheGeneration);
            document.documentElement.dataset.futureAudioTrace = JSON.stringify(audioCacheTrace.slice(-30));
          } catch (error) {}
        };
        const LAST_SEEN_AUDIO_CACHE_EPOCH_KEY = "last_seen_audio_cache_epoch";
        let globalAudioCacheEpoch = 0;
        try { globalAudioCacheEpoch = Math.max(0, Number(localStorage.getItem(LAST_SEEN_AUDIO_CACHE_EPOCH_KEY) || 0) || 0); } catch (error) {}
        const localClean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();
        // Added 2026-07-30: shares one current-revision lookup across every player in the active tab.
        const qmSoundSemanticKey = (url) => {
          if (!url || url.pathname.toLowerCase() !== "/server-data/qm-sound") {
            return "";
          }
          return Array.from(url.searchParams.entries())
            .filter(([name]) => !["v", "revision", "rev", "audio_epoch", "file_rev", "ts", "cache"].includes(localClean(name).toLowerCase()))
            .sort((a, b) => `${a[0]}=${a[1]}`.localeCompare(`${b[0]}=${b[1]}`))
            .map(([name, value]) => `${name}=${value}`)
            .join("&");
        };
        // Added 2026-07-31: sync callers may reuse an already-resolved protocol URL; network resolution remains async.
        const revisionSafeAudioUrl = (value = "") => {
          const raw = localClean(value);
          if (!raw || raw.startsWith("blob:") || raw.startsWith("data:")) {
            return "";
          }
          try {
            const url = new URL(raw, window.location.href);
            url.hash = "";
            if (url.pathname.toLowerCase() === "/server-data/qm-sound") {
              const epoch = Math.max(0, Number(url.searchParams.get("audio_epoch") || 0) || 0);
              const revision = localClean(url.searchParams.get("file_rev") || "");
              if (!epoch || !revision || revision.toLowerCase() === "missing" || revision === "0") {
                const mapped = revisionedQmSoundUrlBySemanticKey.get(qmSoundSemanticKey(url));
                if (mapped) {
                  return mapped;
                }
              }
            }
            return url.href;
          } catch (error) {
            return "";
          }
        };
        const canonicalAudioUrl = revisionSafeAudioUrl;
        const stableHash = async (value = "") => {
          const text = String(value == null ? "" : value);
          try {
            if (window.crypto && window.crypto.subtle && window.TextEncoder) {
              const bytes = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
              return Array.from(new Uint8Array(bytes)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
            }
          } catch (error) {}
          let hash = 2166136261;
          for (let index = 0; index < text.length; index += 1) {
            hash ^= text.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
          }
          return (hash >>> 0).toString(16);
        };
        const stableAudioRequestKey = async (href = "") => {
          try {
            const parsed = new URL(href, window.location.href);
            parsed.hash = "";
            const path = parsed.pathname.toLowerCase();
            if (path === "/server-data/qm-sound") {
              const epoch = Math.max(0, Number(parsed.searchParams.get("audio_epoch") || 0) || 0);
              const revision = localClean(parsed.searchParams.get("file_rev") || "");
              if (!epoch || !revision || revision.toLowerCase() === "missing" || revision === "0") {
                return "";
              }
              const semanticParams = Array.from(parsed.searchParams.entries())
                .filter(([name]) => !["v", "revision", "rev", "ts", "cache"].includes(localClean(name).toLowerCase()))
                .sort((a, b) => `${a[0]}=${a[1]}`.localeCompare(`${b[0]}=${b[1]}`));
              return `media-audio:v3:qm-sound:${await stableHash(JSON.stringify({ semanticParams, epoch, revision }))}`;
            }
            if (parsed.searchParams.has("path")) {
              const relPath = localClean(parsed.searchParams.get("path") || "").replace(/\\/g, "/").toLowerCase();
              const revision = localClean(parsed.searchParams.get("v") || parsed.searchParams.get("revision") || parsed.searchParams.get("rev") || "");
              if (relPath) {
                return `media-audio:v2:path:${relPath}:${revision}`;
              }
            }
            parsed.searchParams.delete("ts");
            parsed.searchParams.delete("cache");
            return `media-audio:v2:url:${await stableHash(parsed.href)}`;
          } catch (error) {
            return `media-audio:v1:url:${await stableHash(href)}`;
          }
        };
        const openAudioDb = () => {
          if (!("indexedDB" in window)) {
            return Promise.resolve(null);
          }
          if (dbPromise) {
            return dbPromise;
          }
          dbPromise = new Promise((resolve) => {
            const request = indexedDB.open(DB_NAME, 1);
            request.onerror = () => resolve(null);
            request.onupgradeneeded = () => {
              const db = request.result;
              if (!db.objectStoreNames.contains(AUDIO_STORE)) {
                db.createObjectStore(AUDIO_STORE, { keyPath: "key" });
              }
              if (!db.objectStoreNames.contains(AUDIO_META_STORE)) {
                db.createObjectStore(AUDIO_META_STORE, { keyPath: "key" });
              }
            };
            request.onsuccess = () => {
              audioDb = request.result || null;
              if (audioDb) {
                audioDb.onversionchange = () => {
                  try { audioDb.close(); } catch (error) {}
                  if (audioDb === request.result) audioDb = null;
                  dbPromise = null;
                };
                audioDb.onclose = () => {
                  if (audioDb === request.result) audioDb = null;
                };
              }
              resolve(audioDb);
            };
           });
          return dbPromise;
        };
        const readAudioRecord = async (key = "") => {
          const db = await openAudioDb();
          if (!db || !key) {
            return null;
          }
          return new Promise((resolve) => {
            try {
              const request = db.transaction(AUDIO_STORE, "readonly").objectStore(AUDIO_STORE).get(key);
              request.onerror = () => resolve(null);
              request.onsuccess = () => {
                const row = request.result || null;
                if (row && Number(row.audio_epoch || 0) > 0 && Number(row.audio_epoch || 0) !== globalAudioCacheEpoch) {
                  recordAudioCacheTrace({ type: "indexeddb-reject-epoch", key, record_epoch: Number(row.audio_epoch || 0), audio_epoch: globalAudioCacheEpoch });
                  resolve(null);
                  return;
                }
                if (row) recordAudioCacheTrace({ type: "indexeddb-hit", key, url: row.url || "", audio_epoch: Number(row.audio_epoch || 0), file_rev: row.file_rev || "" });
                resolve(row);
              };
            } catch (error) {
              resolve(null);
            }
          });
        };
        const writeAudioRecord = async (record = {}) => {
          const db = await openAudioDb();
          if (!db || !record || !record.key || !(record.blob instanceof Blob)) {
            return false;
          }
          let audioEpoch = 0;
          let fileRevision = "";
          try {
            const parsed = new URL(localClean(record.url || ""), window.location.href);
            if (parsed.pathname.toLowerCase() === "/server-data/qm-sound") {
              audioEpoch = Math.max(0, Number(parsed.searchParams.get("audio_epoch") || 0) || 0);
              fileRevision = localClean(parsed.searchParams.get("file_rev") || "");
              if (!audioEpoch || !fileRevision || audioEpoch !== globalAudioCacheEpoch) return false;
            }
          } catch (error) {}
          const storedRecord = {
            ...record,
            audio_epoch: audioEpoch,
            file_rev: fileRevision,
            generation: audioCacheGeneration,
          };
          return new Promise((resolve) => {
            try {
              const tx = db.transaction([AUDIO_STORE, AUDIO_META_STORE], "readwrite");
              tx.objectStore(AUDIO_STORE).put(storedRecord);
              tx.objectStore(AUDIO_META_STORE).put({
                key: storedRecord.key,
                url: storedRecord.url || "",
                mime: storedRecord.mime || "",
                size: Number(storedRecord.blob.size || 0) || 0,
                audio_epoch: audioEpoch,
                file_rev: fileRevision,
                generation: audioCacheGeneration,
                createdAt: storedRecord.createdAt || new Date().toISOString(),
              });
              tx.oncomplete = () => resolve(true);
              tx.onerror = () => resolve(false);
            } catch (error) {
              resolve(false);
            }
          });
        };
        // Added 2026-07-31: clears only browser audio state and fences in-flight writes from resurrecting stale audio.
        const clearFutureAudioCache = async (options = {}) => {
          const nextEpoch = Math.max(0, Number(options && options.epoch || globalAudioCacheEpoch || 0) || 0);
          audioCacheGeneration += 1;
          forceNetworkReloadGeneration = audioCacheGeneration;
          recordAudioCacheTrace({ type: "clear-start", audio_epoch: nextEpoch, source: localClean(options && options.source || "local") });
          audioFetchControllers.forEach((controller) => {
            try { controller.abort(); } catch (error) {}
          });
          audioFetchControllers.clear();
          if (nextEpoch) globalAudioCacheEpoch = nextEpoch;
          const staleBlobUrls = Array.from(blobUrlByKey.values());
          blobUrlByKey.clear();
          pendingAudioByKey.clear();
          revisionedQmSoundUrlBySemanticKey.clear();
          staleBlobUrls.forEach((value) => {
            if (typeof value === "string" && value.startsWith("blob:")) {
              try { URL.revokeObjectURL(value); } catch (error) {}
            }
          });
          document.querySelectorAll("audio, video").forEach((media) => {
            const source = String(mediaOriginalSrc.get(media) || media.currentSrc || media.src || "");
            if (!source.startsWith("blob:") && !audioUrlLooksCacheable(source, {})) return;
            try { media.pause(); } catch (error) {}
            try {
              media.removeAttribute("src");
              media.querySelectorAll("source").forEach((sourceNode) => sourceNode.removeAttribute("src"));
              media.load();
            } catch (error) {}
            try { mediaOriginalSrc.delete(media); } catch (error) {}
          });
          try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (error) {}
          try {
            for (let index = localStorage.length - 1; index >= 0; index -= 1) {
              const key = localStorage.key(index) || "";
              if (key.startsWith(SPEAK_PREFIX)) localStorage.removeItem(key);
            }
          } catch (error) {}
          let cacheStorageDeleted = [];
          try {
            if (window.caches && typeof window.caches.keys === "function") {
              const names = await window.caches.keys();
              const audioNames = names.filter((name) => /audio|speak|voice|tts/i.test(String(name || "")));
              const results = await Promise.all(audioNames.map(async (name) => ({ name, deleted: await window.caches.delete(name) })));
              cacheStorageDeleted = results.filter((row) => row.deleted).map((row) => row.name);
            }
          } catch (error) {}
          let lessonCacheResult = { ok: true, deleted: false };
          if (typeof window.__futureClearLessonAudioCache === "function") {
            try {
              lessonCacheResult = await window.__futureClearLessonAudioCache();
            } catch (error) {
              lessonCacheResult = { ok: false, deleted: false, error: String(error && error.message || error || "lesson-cache-clear-failed") };
            }
          }
          const db = audioDb;
          audioDb = null;
          dbPromise = null;
          if (db) {
            try {
              await new Promise((resolve) => {
                const stores = [AUDIO_STORE, AUDIO_META_STORE].filter((name) => db.objectStoreNames.contains(name));
                if (!stores.length) { resolve(); return; }
                const tx = db.transaction(stores, "readwrite");
                stores.forEach((name) => tx.objectStore(name).clear());
                tx.oncomplete = () => resolve();
                tx.onerror = () => resolve();
                tx.onabort = () => resolve();
              });
            } catch (error) {}
          }
          try { if (db) db.close(); } catch (error) {}
          let deleted = false;
          if ("indexedDB" in window) deleted = await new Promise((resolve) => {
            let settled = false;
            const finish = (value) => {
              if (settled) return;
              settled = true;
              resolve(Boolean(value));
            };
            try {
              const request = indexedDB.deleteDatabase(DB_NAME);
              request.onsuccess = () => finish(true);
              request.onerror = () => finish(false);
              request.onblocked = () => finish(false);
            } catch (error) {
              finish(false);
            }
          });
          let activeReloadResult = { ok: true, active: false, reason: "no-active-space-v" };
          if (options.reloadActive !== false && typeof window.__futureReloadCurrentSpaceVAudioCache === "function") {
            try {
              activeReloadResult = await window.__futureReloadCurrentSpaceVAudioCache({ audioEpoch: nextEpoch });
            } catch (error) {
              activeReloadResult = { ok: false, active: true, error: String(error && error.message || error || "space-v-audio-reload-failed") };
            }
          }
          if (nextEpoch) {
            try { localStorage.setItem(LAST_SEEN_AUDIO_CACHE_EPOCH_KEY, String(nextEpoch)); } catch (error) {}
          }
          recordAudioCacheTrace({ type: "clear-complete", audio_epoch: nextEpoch, deleted, cache_storage_deleted: cacheStorageDeleted });
          return {
            ok: lessonCacheResult.ok !== false && activeReloadResult.ok !== false && (!("indexedDB" in window) || deleted),
            deleted,
            database: DB_NAME,
            lesson: lessonCacheResult,
            active_reload: activeReloadResult,
            audio_epoch: nextEpoch,
            generation: audioCacheGeneration,
            cache_storage_deleted: cacheStorageDeleted,
          };
        };
        window.__futureClearAudioCache = clearFutureAudioCache;
        const audioUrlLooksCacheable = (url = "", options = {}) => {
          const href = canonicalAudioUrl(url);
          if (!href) {
            return false;
          }
          const method = localClean(options && options.method || "GET").toUpperCase();
          if (method && method !== "GET" && method !== "HEAD") {
            return false;
          }
          const lower = href.toLowerCase();
          const headers = options && options.headers;
          let accept = "";
          try {
            accept = headers instanceof Headers ? localClean(headers.get("Accept") || headers.get("accept") || "") : localClean(headers && (headers.Accept || headers.accept) || "");
          } catch (error) {}
          return (
            /\.(mp3|wav|ogg|m4a|aac|flac|webm)(\?|$)/i.test(lower) ||
            lower.includes("/server-data/qm-sound") ||
            lower.includes("/server-data/asset") ||
            lower.includes("/sound/") ||
            lower.includes("/audio/") ||
            lower.includes("/voice/") ||
            lower.includes("/tts/") ||
            accept.toLowerCase().includes("audio/")
          );
        };
        const extractSpeakAudioPath = (payload = {}) => {
          const audio = payload && typeof payload.audio === "object" ? payload.audio : {};
          return localClean(
            payload.audio_path ||
            payload.audioPath ||
            payload.path ||
            payload.url ||
            audio.path ||
            audio.url ||
            ""
          );
        };
        const serverAssetLikeUrl = (path = "", baseUrl = window.location.href) => {
          const raw = localClean(path);
          if (!raw) {
            return "";
          }
          try {
            if (/^https?:\/\//i.test(raw) || raw.startsWith("/")) {
              return new URL(raw, baseUrl).href;
            }
            return new URL(`/server-data/asset?path=${encodeURIComponent(raw)}`, window.location.origin).href;
          } catch (error) {
            return "";
          }
        };
        const createAudioFetchController = () => {
          if (!("AbortController" in window)) return null;
          const controller = new AbortController();
          audioFetchControllers.add(controller);
          return controller;
        };
        const releaseAudioFetchController = (controller) => {
          if (controller) audioFetchControllers.delete(controller);
        };
        // Added 2026-07-31: legacy/direct callers resolve metadata first, so the audio request itself is always exact.
        const resolveQmSoundProtocolUrl = async (value = "") => {
          const raw = localClean(value);
          if (!raw) return "";
          let url;
          try { url = new URL(raw, window.location.href); } catch (error) { return raw; }
          if (url.pathname.toLowerCase() !== "/server-data/qm-sound") return url.href;
          const semanticKey = qmSoundSemanticKey(url);
          const requestedEpoch = Math.max(0, Number(url.searchParams.get("audio_epoch") || 0) || 0);
          const fileRevision = localClean(url.searchParams.get("file_rev") || "");
          if (requestedEpoch && fileRevision && fileRevision.toLowerCase() !== "missing" && fileRevision !== "0") {
            if (requestedEpoch > globalAudioCacheEpoch) {
              await clearFutureAudioCache({ epoch: requestedEpoch, reloadActive: false, source: "protocol-url" });
            }
            if (requestedEpoch === globalAudioCacheEpoch) {
              revisionedQmSoundUrlBySemanticKey.set(semanticKey, url.href);
              return url.href;
            }
          }
          const mapped = revisionedQmSoundUrlBySemanticKey.get(semanticKey);
          if (mapped) return mapped;
          const meta = new URL("/server-data/qm-sound-meta", window.location.origin);
          Array.from(url.searchParams.entries()).forEach(([name, entryValue]) => {
            if (!["v", "revision", "rev", "audio_epoch", "file_rev", "ts", "cache"].includes(localClean(name).toLowerCase())) {
              meta.searchParams.append(name, entryValue);
            }
          });
          const taskGeneration = audioCacheGeneration;
          const controller = createAudioFetchController();
          try {
            const response = await nativeFetch(meta.href, {
              method: "GET",
              cache: "no-store",
              credentials: "same-origin",
              signal: controller ? controller.signal : undefined,
              headers: { "Accept": "application/json" },
            });
            const payload = await response.json().catch(() => ({}));
            recordAudioCacheTrace({ type: "metadata", url: meta.href, status: response.status, network: true });
            if (taskGeneration !== audioCacheGeneration || !response.ok || !payload || payload.ok === false) return url.href;
            const serverEpoch = Math.max(0, Number(payload.audio_epoch || 0) || 0);
            const serverRevision = localClean(payload.file_rev || "");
            const exactUrl = localClean(payload.url || "");
            if (!serverEpoch || !serverRevision || !exactUrl) return url.href;
            if (serverEpoch > globalAudioCacheEpoch) {
              await clearFutureAudioCache({ epoch: serverEpoch, reloadActive: false, source: "metadata" });
            }
            const resolved = new URL(exactUrl, window.location.origin).href;
            revisionedQmSoundUrlBySemanticKey.set(semanticKey, resolved);
            return resolved;
          } catch (error) {
            return url.href;
          } finally {
            releaseAudioFetchController(controller);
          }
        };
        const resolveCachedAudioUrl = async (url = "", options = {}) => {
          const href = await resolveQmSoundProtocolUrl(canonicalAudioUrl(url));
          if (!href || !audioUrlLooksCacheable(href, options)) {
            return href || url;
          }
          const persistentKey = await stableAudioRequestKey(href);
          const parsedHref = new URL(href, window.location.href);
          const semanticKey = qmSoundSemanticKey(parsedHref);
          const pendingKey = persistentKey || `media-audio:v2:qm-current:${await stableHash(semanticKey || href)}`;
          if (blobUrlByKey.has(persistentKey || pendingKey)) {
            return blobUrlByKey.get(persistentKey || pendingKey);
          }
          if (pendingAudioByKey.has(pendingKey)) {
            return pendingAudioByKey.get(pendingKey);
          }
          const task = (async () => {
            const taskGeneration = audioCacheGeneration;
            const cached = persistentKey ? await readAudioRecord(persistentKey) : null;
            if (taskGeneration !== audioCacheGeneration) return href;
            if (cached && cached.blob instanceof Blob) {
              const blobUrl = URL.createObjectURL(cached.blob);
              blobUrlByKey.set(persistentKey, blobUrl);
              return blobUrl;
            }
            const controller = createAudioFetchController();
            let response;
            try {
              response = await nativeFetch(href, {
              ...options,
              method: "GET",
              cache: taskGeneration === forceNetworkReloadGeneration ? "reload" : (persistentKey ? "force-cache" : "no-store"),
              signal: controller ? controller.signal : undefined,
              headers: {
                ...(options && options.headers && !(options.headers instanceof Headers) ? options.headers : {}),
                "Accept": "audio/*,*/*",
              },
              });
            } finally {
              releaseAudioFetchController(controller);
            }
            recordAudioCacheTrace({
              type: "audio-network",
              url: href,
              status: Number(response && response.status || 0),
              cache_mode: taskGeneration === forceNetworkReloadGeneration ? "reload" : (persistentKey ? "force-cache" : "no-store"),
              audio_epoch: Number(new URL(href, window.location.href).searchParams.get("audio_epoch") || 0) || 0,
              file_rev: localClean(new URL(href, window.location.href).searchParams.get("file_rev") || ""),
              server_cache_source: localClean(response && response.headers && response.headers.get("X-Future-Audio-Cache-Source") || ""),
            });
            if (!response || !response.ok) {
              return href;
            }
            const contentType = localClean(response.headers && response.headers.get("content-type") || "");
            if (contentType && !contentType.toLowerCase().includes("audio") && !/\.(mp3|wav|ogg|m4a|aac|flac|webm)(\?|$)/i.test(href)) {
              return href;
            }
            const blob = await response.blob();
            if (taskGeneration !== audioCacheGeneration) return href;
            if (!(blob instanceof Blob) || !blob.size) {
              return href;
            }
            let resolvedUrl = href;
            let resolvedKey = persistentKey;
            const responseRevision = localClean(response.headers && response.headers.get("X-Future-Audio-Revision") || "");
            const responseEpoch = Math.max(0, Number(response.headers && response.headers.get("X-Future-Audio-Cache-Epoch") || 0) || 0);
            if (!resolvedKey && semanticKey && responseRevision) {
              const versioned = new URL(href, window.location.href);
              versioned.searchParams.delete("v");
              versioned.searchParams.delete("revision");
              versioned.searchParams.delete("rev");
              versioned.searchParams.set("audio_epoch", String(responseEpoch || globalAudioCacheEpoch || 0));
              versioned.searchParams.set("file_rev", responseRevision);
              resolvedUrl = versioned.href;
              revisionedQmSoundUrlBySemanticKey.set(semanticKey, resolvedUrl);
              resolvedKey = await stableAudioRequestKey(resolvedUrl);
            }
            if (resolvedKey) {
                if (taskGeneration !== audioCacheGeneration) return href;
               await writeAudioRecord({
                key: resolvedKey,
                url: resolvedUrl,
                blob,
                mime: contentType || blob.type || "audio/mpeg",
                createdAt: new Date().toISOString(),
              });
              recordAudioCacheTrace({ type: "indexeddb-write", key: resolvedKey, url: resolvedUrl, audio_epoch: responseEpoch, file_rev: responseRevision });
            }
            const blobUrl = URL.createObjectURL(blob);
            blobUrlByKey.set(resolvedKey || pendingKey, blobUrl);
            blobUrlByKey.set(pendingKey, blobUrl);
            return blobUrl;
          })().catch(() => href).finally(() => {
            pendingAudioByKey.delete(pendingKey);
          });
          pendingAudioByKey.set(pendingKey, task);
          return task;
        };
        const speakCacheKeyFromRequest = async (url = "", options = {}) => {
          const method = localClean(options && options.method || "GET").toUpperCase();
          if (method !== "POST") {
            return "";
          }
          let path = "";
          try {
            path = new URL(String(url), window.location.href).pathname;
          } catch (error) {
            return "";
          }
          if (path !== "/pdf/speak") {
            return "";
          }
          const body = typeof options.body === "string" ? options.body : "";
          if (!body) {
            return "";
          }
          let parsed = null;
          try {
            parsed = JSON.parse(body);
          } catch (error) {
            parsed = null;
          }
          const text = localClean(parsed && (parsed.text || parsed.message || parsed.prompt) || body);
          const voice = localClean(parsed && (parsed.voice || parsed.voice_id || parsed.voiceId) || "");
          const mode = localClean(parsed && (parsed.mode || parsed.speakMode || parsed.speak_mode) || "");
          if (!text || !voice) {
            return "";
          }
          return `${SPEAK_PREFIX}${await stableHash(JSON.stringify({ text, voice, mode }))}`;
        };
        const readSpeakPayload = (key = "") => {
          if (!key) {
            return null;
          }
          try {
            const raw = window.localStorage && window.localStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
          } catch (error) {
            return null;
          }
        };
        const writeSpeakPayload = (key = "", payload = {}) => {
          if (!key || !payload || typeof payload !== "object") {
            return;
          }
          try {
            window.localStorage && window.localStorage.setItem(key, JSON.stringify({
              ok: true,
              cachedAt: new Date().toISOString(),
              payload,
            }));
          } catch (error) {}
        };
        window.__futureAudioCacheManager = {
          clear: clearFutureAudioCache,
          epoch: () => globalAudioCacheEpoch,
          generation: () => audioCacheGeneration,
          trace: () => audioCacheTrace.slice(),
          resetTrace: () => { audioCacheTrace.length = 0; window.__futureAudioCacheTrace = audioCacheTrace; },
          resolveQmSoundUrl: resolveQmSoundProtocolUrl,
          resolveAudioUrl: resolveCachedAudioUrl,
          syncEpoch: async (serverEpoch, options = {}) => {
            const epoch = Math.max(0, Number(serverEpoch || 0) || 0);
            let seen = 0;
            try { seen = Math.max(0, Number(localStorage.getItem(LAST_SEEN_AUDIO_CACHE_EPOCH_KEY) || 0) || 0); } catch (error) {}
            if (!epoch || epoch <= seen) {
              globalAudioCacheEpoch = Math.max(globalAudioCacheEpoch, seen, epoch);
              return { ok: true, changed: false, audio_epoch: globalAudioCacheEpoch };
            }
            const result = await clearFutureAudioCache({ ...options, epoch, source: "server-epoch" });
            return { ...result, changed: true, audio_epoch: epoch };
          },
        };
        try {
          if (window.speechSynthesis && !window.speechSynthesis.__futureAudioFallbackTraced) {
            const nativeSpeechSpeak = window.speechSynthesis.speak.bind(window.speechSynthesis);
            window.speechSynthesis.speak = (utterance) => {
              recordAudioCacheTrace({ type: "browser-speech-fallback", text: localClean(utterance && utterance.text || "") });
              return nativeSpeechSpeak(utterance);
            };
            window.speechSynthesis.__futureAudioFallbackTraced = true;
          }
        } catch (error) {}
        window.__futureResolveCachedAudioUrl = resolveCachedAudioUrl;
        window.__futureRevisionSafeAudioUrl = revisionSafeAudioUrl;
        window.fetch = async (input, options = {}) => {
          const url = typeof input === "string" ? input : (input && input.url ? input.url : "");
          const method = localClean(options && options.method || (input && input.method) || "GET").toUpperCase();
          const speakKey = await speakCacheKeyFromRequest(url, { ...options, method });
          if (speakKey) {
            const cachedSpeak = readSpeakPayload(speakKey);
            const cachedPayload = cachedSpeak && cachedSpeak.payload;
            const audioPath = extractSpeakAudioPath(cachedPayload || {});
            if (audioPath) {
              const audioUrl = serverAssetLikeUrl(audioPath, url);
              if (audioUrl) {
                const cachedAudioUrl = await resolveCachedAudioUrl(audioUrl);
                if (cachedAudioUrl && cachedAudioUrl.startsWith("blob:")) {
                  return new Response(JSON.stringify(cachedPayload), {
                    status: 200,
                    headers: { "Content-Type": "application/json", "X-Future-Audio-Cache": "hit" },
                  });
                }
              }
            }
          }
          if (method === "GET" && audioUrlLooksCacheable(url, options)) {
            const cachedUrl = await resolveCachedAudioUrl(url, options);
            if (cachedUrl && cachedUrl.startsWith("blob:")) {
              const blobResponse = await nativeFetch(cachedUrl);
              return new Response(await blobResponse.blob(), {
                status: 200,
                headers: { "Content-Type": "audio/mpeg", "X-Future-Audio-Cache": "hit" },
              });
            }
            if (cachedUrl) {
              input = cachedUrl;
            }
          }
          const fetchGeneration = audioCacheGeneration;
          const response = await nativeFetch(input, options);
          if (speakKey) {
            const clone = response.clone();
            clone.json().then((payload) => {
              if (fetchGeneration !== audioCacheGeneration) return;
              if (!clone.ok || !payload || payload.ok === false) {
                return;
              }
              writeSpeakPayload(speakKey, payload);
              const audioPath = extractSpeakAudioPath(payload);
              const audioUrl = serverAssetLikeUrl(audioPath, url);
              if (audioUrl) {
                void resolveCachedAudioUrl(audioUrl);
              }
            }).catch(() => {});
          } else if (method === "GET" && audioUrlLooksCacheable(url, options)) {
            const clone = response.clone();
            clone.blob().then(async (blob) => {
              if (fetchGeneration !== audioCacheGeneration) return;
              if (!response.ok || !(blob instanceof Blob) || !blob.size) {
                return;
              }
              const href = canonicalAudioUrl(url);
              const key = await stableAudioRequestKey(href);
              if (!key) {
                return;
              }
              await writeAudioRecord({
                key,
                url: href,
                blob,
                mime: localClean(response.headers && response.headers.get("content-type") || "") || blob.type || "audio/mpeg",
                createdAt: new Date().toISOString(),
              });
            }).catch(() => {});
          }
          return response;
        };
        if (nativePlay && window.HTMLMediaElement && window.HTMLMediaElement.prototype) {
          window.HTMLMediaElement.prototype.play = function patchedFutureAudioPlay(...args) {
            try {
              const current = canonicalAudioUrl(this.currentSrc || this.src || "");
              if (current) {
                mediaOriginalSrc.set(this, current);
              }
              const original = mediaOriginalSrc.get(this) || current;
              if (original && audioUrlLooksCacheable(original, {})) {
                return resolveCachedAudioUrl(original).then((cachedUrl) => {
                  if (cachedUrl && this.src !== cachedUrl) {
                    this.src = cachedUrl;
                  }
                  recordAudioCacheTrace({
                    type: "media-play",
                    requested_url: original,
                    resolved_url: cachedUrl || original,
                    current_src: this.currentSrc || this.src || "",
                  });
                  return nativePlay.apply(this, args);
                }).catch(() => nativePlay.apply(this, args));
              }
            } catch (error) {}
            return nativePlay.apply(this, args);
          };
        }
      };
      installFutureAudioCacheLayer();
      const FRONTEND_CACHE_VERSION_KEY = "future_frontend_cache_version";
      const FRONTEND_CACHE_RELOAD_KEY = "future_frontend_cache_reload_version";
      const FRONTEND_CACHE_PENDING_KEY = "future_frontend_cache_pending_version";
      const rememberFrontendCacheVersion = (version = "", changed = false) => {
        try {
          localStorage.setItem(FRONTEND_CACHE_VERSION_KEY, version);
          if (changed) {
            localStorage.removeItem("future_server_data_manifest_refreshed_at");
            localStorage.removeItem("future_server_data_manifest_signature");
          }
        } catch (error) {
        }
        try {
          sessionStorage.removeItem(FRONTEND_CACHE_RELOAD_KEY);
          sessionStorage.removeItem(FRONTEND_CACHE_PENDING_KEY);
        } catch (error) {
        }
      };
      const checkFrontendCacheVersion = async (base = WHISPER_SERVER_URL) => {
        if (!base || location.protocol === "file:") {
          return;
        }
        try {
          const response = await fetchWithTimeout(`${base}/frontend-version?ts=${Date.now()}`, {
            method: "GET",
            headers: { "Accept": "application/json" },
            mode: "cors",
            cache: "no-store",
          }, 3500);
          const payload = await response.json().catch(() => ({}));
          const version = clean(payload && (payload.version || payload.etag || payload.updated_at));
          if (!version) {
            return;
          }
          const updatedAt = clean(payload && (payload.updated_at || payload.updatedAt || payload.time || "")) || FUTURE_FRONTEND_BUILD_STAMP;
          futureFrontendVersionState = {
            version,
            updatedAt,
            label: `Frontend version ${shortFrontendVersionText(version)} | updated ${updatedAt}`,
          };
          updateFutureDocumentTitle(futureRouteStateFromLocation());
          updateAuthHudVersionLine();
          let previous = "";
          try {
            previous = clean(localStorage.getItem(FRONTEND_CACHE_VERSION_KEY) || "");
          } catch (error) {
          }
          if (previous && previous !== version) {
            rememberFrontendCacheVersion(version, true);
            return;
          }
          rememberFrontendCacheVersion(version, false);
        } catch (error) {
        }
      };
      void checkFrontendCacheVersion(WHISPER_SERVER_URL);
      const refreshAntiRobotToken = async (base = WHISPER_SERVER_URL) => {
        if (antiRobotTokenIsFresh()) {
          return antiRobotToken;
        }
        if (antiRobotTokenPromise) {
          return antiRobotTokenPromise;
        }
        antiRobotTokenPromise = fetchWithTimeout(`${base}/anti-robot/challenge?ts=${Date.now()}`, {
          method: "GET",
          headers: { "Accept": "application/json" },
          mode: "cors",
          cache: "no-store",
        }, 2600)
          .then((response) => response.json().catch(() => ({})))
          .then((payload) => {
            const nextToken = clean(payload && payload.token);
            if (nextToken) {
              antiRobotToken = nextToken;
              antiRobotTokenAt = Date.now();
            }
            return antiRobotToken;
          })
          .catch(() => antiRobotToken)
          .finally(() => {
            antiRobotTokenPromise = null;
          });
        return antiRobotTokenPromise;
      };
      const antiRobotHeaders = async (base, headers = {}) => {
        const nextHeaders = { ...(headers || {}) };
        const token = await refreshAntiRobotToken(base);
        if (token) {
          nextHeaders[ANTI_ROBOT_HEADER] = token;
        }
        return nextHeaders;
      };
      void refreshAntiRobotToken(WHISPER_SERVER_URL);
      const WHISPER_MODEL = clean(params.get("whisper_model")) || "small";
      const AUTH_TOKEN_KEY = "future_lesson_auth_token";
      const AUTH_COOKIE_NAME = "future_lesson_auth_token";
      const AUTH_USER_KEY = "future_lesson_auth_user";
      const RELOAD_SESSION_KEY = "future_lesson_reload_session";
      const RELOAD_SESSION_TTL_MS = 10 * 60 * 1000;
      const SERVER_LAST_PATH_KEY = "future_lesson_server_last_path";
      const SERVER_LAST_FILE_KEY = "future_lesson_server_last_file";
      const SERVER_RECENT_FILES_KEY = "future_lesson_server_recent_files";
      const QUESTION_MOTION_KEY = "future_question_card_motion";
      const QUESTION_SIDE_CARDS_KEY = "future_question_side_cards";
      const QUESTION_ANIMATION_KEY = "future_question_animation";
      const SPACE_W_PROGRESS_PREFIX = "future_space_w_progress";
      const SPACE_Q_PROGRESS_PREFIX = "future_space_q_progress";
      const SPACE_V_PROGRESS_PREFIX = "future_space_v_progress";
      const SPACE_P_PROGRESS_PREFIX = "future_space_p_progress";
      const SPACE_V_VOCAB_SYNC_PREFIX = "future_space_v_vocab_sync";
      const SPACE_V_VOICE_KEY = "future_space_v_voice";
      const SPACE_W_VOICE_PREFIX = "future_space_w_voice";
      const SPACE_W_GLOBAL_VOICE_KEY = "future_space_w_global_voice";
      const SPACE_W_DEFAULT_VOICE = "sot:en-GB";
      const SPACE_W_AUDIO_DB_NAME = "future_space_w_audio_cache";
      const SPACE_W_AUDIO_STORE = "audio";
      const SPACE_W_AUDIO_DB_VERSION = 2;
      const SPACE_W_AUDIO_CACHE_MAX_ENTRIES = 8000;
      const SPACE_W_AUDIO_CACHE_MAX_BYTES = 512 * 1024 * 1024;
      const SPACE_W_AUDIO_CACHE_MIN_BYTES = 64 * 1024 * 1024;
      const PDF_ADMIN_ACTING_USER_KEY = "future_pdf_admin_acting_user";
      let authMode = "login";
      let authResetApproved = false;
      let authToken = "";
      let currentAuthUsername = "";
      let currentAuthIsAdmin = false;
      let currentAuthProfile = {};
      let pdfAdminActingUser = "";
      let pdfAdminUserRows = [];
      let pdfAdminUsersLoadedAt = 0;
      let pdfAdminUserBusy = false;
      let activeNpcActor = null;
      let npcSwitchRoster = [];
      let npcSwitchRosterLoadedAt = 0;
      let profileEditPhotos = [];
      let profileEditUploadSlot = -1;
      const publicProfileCache = new Map();
      const authCookieSecureSuffix = () => (window.location.protocol === "https:" ? "; Secure" : "");
      const readFutureCookie = (name = "") => {
        const target = `${encodeURIComponent(name)}=`;
        return String(document.cookie || "")
          .split(";")
          .map((part) => part.trim())
          .filter(Boolean)
          .reduce((found, part) => {
            if (found || !part.startsWith(target)) {
              return found;
            }
            try {
              return decodeURIComponent(part.slice(target.length));
            } catch (error) {
              return part.slice(target.length);
            }
          }, "");
      };
      const persistAuthToken = (token = "") => {
        const nextToken = clean(token);
        if (!nextToken) {
          return "";
        }
        authToken = nextToken;
        try {
          localStorage.setItem(AUTH_TOKEN_KEY, nextToken);
        } catch (error) {
        }
        try {
          document.cookie = `${encodeURIComponent(AUTH_COOKIE_NAME)}=${encodeURIComponent(nextToken)}; Max-Age=86400; Path=/; SameSite=Lax${authCookieSecureSuffix()}`;
        } catch (error) {
        }
        return nextToken;
      };
      const getStoredAuthToken = () => {
        try {
          const stored = clean(localStorage.getItem(AUTH_TOKEN_KEY) || "");
          if (stored) {
            return stored;
          }
        } catch (error) {
        }
        return clean(readFutureCookie(AUTH_COOKIE_NAME));
      };
      const clearStoredServerLastFileState = (username = "") => {
        const user = clean(username || currentAuthUsername || (authUser && authUser.value) || "");
        if (!user) {
          return;
        }
        try {
          localStorage.removeItem(`${SERVER_LAST_FILE_KEY}:${user}`);
          localStorage.removeItem(`${SERVER_LAST_PATH_KEY}:${user}`);
          localStorage.removeItem(`${SERVER_RECENT_FILES_KEY}:${user}`);
        } catch (error) {
        }
      };
      const forgetStoredAuthToken = () => {
        try {
          localStorage.removeItem(AUTH_TOKEN_KEY);
        } catch (error) {
        }
        try {
          document.cookie = `${encodeURIComponent(AUTH_COOKIE_NAME)}=; Max-Age=0; Path=/; SameSite=Lax${authCookieSecureSuffix()}`;
        } catch (error) {
        }
      };
      let authMotionTimer = 0;
      let authMotionWarmTimer = 0;
      let authConnectorFrame = 0;
      let authConnectorProgress = 0;
      let authConnectorTarget = 0;
      let authConnectorElements = [];
      let authConnectorBendSeeds = [];
      let authConnectorPhaseSlots = [0, 0.5, 0, 0.5];
      let authConnectorCornerFlashed = [false, false, false, false];
      let authConnectorConnectedCount = 0;
      let authConnectorShockwaveFired = false;
      let authPanelFxLayer = null;
      let authPanelShockwaveNode = null;
      let authCornerFlashNodes = [];
      let taskNoticeProfile = { speaker_name: "", avatar: "", notice_style: "hologram", draft_text: "", draft_text_en: "", draft_text_vi: "", active_language: "vi" };
      let taskNoticeProfileSyncTimer = 0;
      let authSessionMonitorTimer = 0;
      let authSessionInvalidating = false;
      let reloadSessionRestorePending = false;
      let openLessonVaultAfterLogoutLogin = false;
      let loginVaultBackdropSerial = 0;
      let loginVaultBackdropBusy = false;

      // Added 2026-07-07: lets a signed-in learner download one reusable worker package from the Group/Lesson Vault controls.
      if (serverWorkerRegisterButtons.length) {
        serverWorkerRegisterButtons.forEach((serverWorkerRegisterButton) => serverWorkerRegisterButton.addEventListener("click", async () => {
          serverWorkerRegisterButtons.forEach((button) => { button.disabled = true; });
          const previous = serverWorkerRegisterButton.title || "";
          try {
            const headers = {};
            const token = clean(authToken || getStoredAuthToken());
            if (token) headers["X-Future-Auth"] = token;
            const response = await fetch("/distributed-worker/download", {
              method: "GET",
              headers,
              cache: "no-store",
            });
            if (!response.ok) {
              const payload = await response.json().catch(() => ({}));
              throw new Error(payload.error || "Could not download worker package.");
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "future_distributed_worker.zip";
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 8000);
            serverWorkerRegisterButtons.forEach((button) => {
              button.title = "Worker package downloaded. Run start_worker.bat on this PC.";
            });
            if (typeof setLoadStatus === "function") {
              setLoadStatus("Worker package downloaded. Run start_worker.bat on this PC.");
            }
          } catch (error) {
            const message = error && error.message ? error.message : "Could not download worker package.";
            serverWorkerRegisterButtons.forEach((button) => {
              button.title = message;
            });
            if (typeof setLoadStatus === "function") {
              setLoadStatus(message, true);
            }
          } finally {
            window.setTimeout(() => {
              serverWorkerRegisterButtons.forEach((button) => {
                button.disabled = false;
                button.title = previous || button.title;
              });
            }, 1200);
          }
        }));
      }
      let learnerChatOpen = false;
      let learnerChatLastId = 0;
      let learnerChatUnread = 0;
      let learnerChatPollTimer = 0;
      let learnerChatPollInFlight = false;
      let learnerChatPendingOperation = null;
      const learnerChatMessages = [];
      const learnerChatPlayedAudioIds = new Set();
      let learnerChatViAudioEnabled = false;
      let learnerChatViVoice = "edge:vi-VN-NamMinhNeural";
      let learnerChatViVoiceLabel = "Edge | Vietnamese VN | Nam Minh";
      let learnerChatAudioEnabled = false;
      let learnerChatVoice = "male-us";
      let learnerChatVoiceLabel = "People | Male US";
      const LEARNER_CHAT_VOICES_CACHE_MS = 300000;
      const SHARED_CHAT_VOICES_CACHE_MS = 1800000;
      const SHARED_CHAT_VOICES_PERSIST_MS = 86400000;
      let sharedChatVoicesPayload = null;
      let sharedChatVoicesLoadedAt = 0;
      let sharedChatVoicesCacheUser = "";
      let sharedChatVoicesPromise = null;
      const sharedChatVoicesStorageKey = (username = "") => `future:chat-voices:${clean(username).toLowerCase() || "guest"}`;
      const readStoredSharedChatVoices = (username = "") => {
        try {
          const raw = localStorage.getItem(sharedChatVoicesStorageKey(username));
          if (!raw) return null;
          const data = JSON.parse(raw);
          const payload = data && data.payload && typeof data.payload === "object" ? data.payload : null;
          const savedAt = Number(data && data.saved_at || 0);
          if (!payload || !savedAt || Date.now() - savedAt > SHARED_CHAT_VOICES_PERSIST_MS) {
            return null;
          }
          return { payload, savedAt };
        } catch (error) {
          return null;
        }
      };
      const writeStoredSharedChatVoices = (username = "", payload = {}) => {
        try {
          localStorage.setItem(sharedChatVoicesStorageKey(username), JSON.stringify({
            payload: payload && typeof payload === "object" ? payload : {},
            saved_at: Date.now(),
          }));
        } catch (error) {
        }
      };
      // Added 2026-07-01: shares the /chat/voices catalog across Lesson Vault, Ghost EN, chat, and PDF controls.
      const fetchSharedChatVoices = async (options = {}) => {
        if (!authToken) {
          throw new Error("Chua dang nhap.");
        }
        const force = Boolean(options && options.force);
        const cacheUser = clean(currentAuthUsername || "").toLowerCase();
        const cacheFresh = sharedChatVoicesPayload &&
          sharedChatVoicesCacheUser === cacheUser &&
          Date.now() - sharedChatVoicesLoadedAt < SHARED_CHAT_VOICES_CACHE_MS;
        if (!force && cacheFresh) {
          return { payload: sharedChatVoicesPayload };
        }
        if (!force && cacheUser) {
          const stored = readStoredSharedChatVoices(cacheUser);
          if (stored) {
            sharedChatVoicesPayload = stored.payload;
            sharedChatVoicesLoadedAt = stored.savedAt;
            sharedChatVoicesCacheUser = cacheUser;
            return { payload: sharedChatVoicesPayload };
          }
        }
        if (!sharedChatVoicesPromise || force || sharedChatVoicesCacheUser !== cacheUser) {
          sharedChatVoicesCacheUser = cacheUser;
          sharedChatVoicesPromise = fetchAuthJson("/chat/voices")
            .then((result) => {
              sharedChatVoicesPayload = result && result.payload && typeof result.payload === "object" ? result.payload : {};
              sharedChatVoicesLoadedAt = Date.now();
              writeStoredSharedChatVoices(cacheUser, sharedChatVoicesPayload);
              return { payload: sharedChatVoicesPayload };
            })
            .finally(() => {
              sharedChatVoicesPromise = null;
            });
        }
        return sharedChatVoicesPromise;
      };
      let learnerChatVoicesLoadedAt = 0;
      let learnerChatVoicesCacheUser = "";
      let learnerChatVoicesPayload = null;
      let learnerChatVoicesPromise = null;
      let learnerChatRecorder = null;
      let learnerChatRecordStream = null;
      let learnerChatRecordChunks = [];
      let learnerChatRecordBlob = null;
      let learnerChatRecordMode = "en";
      let learnerChatRecordStartedAt = 0;
      let learnerChatRecordTimer = 0;
      let learnerChatRecordCanceled = false;
      let zipformerViInputRecorder = null;
      let zipformerViInputStream = null;
      let zipformerViInputChunks = [];
      let zipformerViInputTarget = null;
      let zipformerViInputButton = null;
      let zipformerViInputScope = "";
      let zipformerViInputStartedAt = 0;
      let zipformerViInputTimer = 0;
      let zipformerViCtrlToggleCandidate = null;
      let browserSpeechInputRecognition = null;
      let browserSpeechInputUserEditController = null;
      let browserSpeechInputUserEditTarget = null;
      let browserSpeechInputTarget = null;
      let browserSpeechInputButton = null;
      let browserSpeechInputScope = "";
      let browserSpeechInputBaseValue = "";
      let browserSpeechInputLastRenderedValue = "";
      let browserSpeechInputLastSpeechText = "";
      let browserSpeechInputDraftStart = -1;
      let browserSpeechInputDraftEnd = -1;
      let browserSpeechInputDraftText = "";
      let browserSpeechInputAnchorStart = -1;
      let browserSpeechInputFinalText = "";
      let browserSpeechInputInterimText = "";
      let browserSpeechInputStartedAt = 0;
      let browserSpeechInputTimer = 0;
      let browserSpeechInputLastActivityAt = 0;
      let browserSpeechInputLastActivityValue = "";
      let browserSpeechInputLastChunkAt = 0;
      let browserSpeechInputSubmitOnEnd = false;
      let browserSpeechInputStopping = false;
      let browserSpeechInputAutoRestartCount = 0;
      let browserSpeechInputTypingRestore = null;
      let learnerStreamSession = null;
      let learnerStreamPollTimer = 0;
      let learnerStreamPollInFlight = false;
      let learnerStreamRecorder = null;
      let learnerStreamMedia = null;
      let learnerStreamSegmentTimer = 0;
      let learnerStreamRecordChunks = [];
      let learnerStreamLastChunkId = 0;
      let learnerStreamAudioChain = Promise.resolve();
      let learnerStreamPeer = null;
      let learnerStreamRemoteAudio = null;
      let learnerStreamRemoteCandidateId = 0;
      let learnerStreamOfferSet = false;
      let learnerStreamAnswerSent = false;
      let learnerStreamOfferKey = "";
      let learnerStreamAutoAccepting = false;
      let learnerScreenSession = null;
      let learnerScreenPollTimer = 0;
      let learnerScreenPollInFlight = false;
      let learnerScreenCaptureStream = null;
      let learnerScreenVideo = null;
      let learnerScreenCanvas = null;
      let learnerScreenFrameTimer = 0;
      let learnerScreenSending = false;
      let learnerScreenPeer = null;
      let learnerScreenRemoteCandidateId = 0;
      let learnerScreenOfferSet = false;
      let learnerScreenAnswerSent = false;
      let learnerScreenOfferKey = "";
      let learnerScreenControlChannel = null;
      let learnerScreenControlPollTimer = 0;
      let learnerScreenControlPolling = false;
      let learnerScreenControlAfter = 0;
      let learnerScreenRemoteCursorNode = null;
      let learnerScreenRemoteCursor = null;
      let learnerScreenRemoteCursorFrame = 0;
      let learnerScreenAutoPromptSessionId = "";
      let learnerScreenAutoPromptTimer = 0;
      let learnerScreenCaptureStarting = false;
      let learnerScreenAudioRecorder = null;
      let learnerScreenAudioChunks = [];
      let learnerScreenAudioSegmentTimer = 0;
      let learnerScreenMicStream = null;
      let learnerScreenAudioContext = null;
      let learnerScreenAudioMixStream = null;
      let learnerScreenAudioMixNodes = [];
      let learnerScreenMicUpgradeTimer = 0;
      let learnerScreenMicUpgradeRunning = false;
      let learnerScreenAudioRelayAutoRestart = false;
      let learnerScreenRemoteAudio = null;
      let learnerScreenAdminAudioLastChunkId = 0;
      let learnerScreenAdminAudioPollTimer = 0;
      let learnerScreenAdminAudioPolling = false;
      let learnerScreenAdminAudioQueue = [];
      let learnerScreenAdminAudioPlaying = false;
      let learnerScreenAdminAudioCurrent = null;
      let learnerScreenAdminRelayMediaSource = null;
      let learnerScreenAdminRelaySourceBuffer = null;
      let learnerScreenAdminRelayObjectUrl = "";
      let learnerScreenAdminRelayPendingBuffers = [];
      let learnerScreenAdminRelayMime = "";
      let adminScreenOpen = false;
      let adminScreenUsers = [];
      let adminScreenUser = "";
      let adminScreenSession = null;
      let adminScreenPeer = null;
      let adminScreenRemoteAudio = null;
      let adminScreenAudioLastChunkId = 0;
      let adminScreenAudioPollTimer = 0;
      let adminScreenAudioPolling = false;
      let adminScreenAudioQueue = [];
      let adminScreenAudioPlaying = false;
      let adminScreenCurrentAudio = null;
      let adminScreenRelayMediaSource = null;
      let adminScreenRelaySourceBuffer = null;
      let adminScreenRelayObjectUrl = "";
      let adminScreenRelayPendingBuffers = [];
      let adminScreenRelayMime = "";
      let adminScreenAudioDropped = 0;
      let adminScreenMicStream = null;
      let adminScreenMicRecorder = null;
      let adminScreenMicEnabled = false;
      let adminScreenMicSending = false;
      let adminScreenMicSegmentTimer = 0;
      let adminScreenMicRelayAutoRestart = false;
      let adminScreenControlChannel = null;
      let adminScreenRemoteCandidateId = 0;
      let adminScreenOfferSent = false;
      let adminScreenAnswerSet = false;
      let adminScreenPollTimer = 0;
      let adminScreenFrameTimer = 0;
      let adminScreenFrameId = 0;
      let adminScreenControlQueue = [];
      let adminScreenControlSending = false;
      let adminScreenControlTimer = 0;
      let adminScreenControlLastSentAt = 0;
      let adminScreenPointerActive = false;
      let adminScreenTransportMode = "";
      let adminScreenTransportLogRows = [];
      let adminScreenTransportPreference = "auto";
      let adminScreenRelayLastFrameAt = 0;
      let adminScreenRelayLastFrameId = 0;
      let adminScreenRelayFps = 0;
      let adminScreenRelayFrameChars = 0;
      let adminScreenRelayFrameWidth = 0;
      let adminScreenRelayFrameHeight = 0;
      let learnerScreenBinaryFrameEnabled = true;
      let learnerScreenFrameLastElapsedMs = 0;
      let learnerScreenFrameLastEncodeMs = 0;
      let learnerScreenFrameLastUploadMs = 0;
      let learnerScreenFrameLastBytes = 0;
      let learnerScreenFrameLastMode = "";
      const LEARNER_SCREEN_WEBRTC_WIDTH = 1280;
      const LEARNER_SCREEN_WEBRTC_HEIGHT = 720;
      const LEARNER_SCREEN_WEBRTC_BITRATE = 6500000;
      const LEARNER_SCREEN_WEBRTC_FRAMERATE = 30;
      const LEARNER_SCREEN_PREVIEW_MAX_WIDTH = 1280;
      const LEARNER_SCREEN_PREVIEW_MAX_HEIGHT = 720;
      const LEARNER_SCREEN_PREVIEW_QUALITY = 0.68;
      const LEARNER_SCREEN_PREVIEW_MIME = "image/webp";
      const LEARNER_SCREEN_PREVIEW_TARGET_FPS = 10;
      const LEARNER_SCREEN_PREVIEW_INTERVAL_MS = Math.round(1000 / LEARNER_SCREEN_PREVIEW_TARGET_FPS);
      const LEARNER_SCREEN_PREVIEW_FRAMES_ENABLED = true;
      const LEARNER_SCREEN_PREVIEW_BINARY_ENABLED = true;
      const LEARNER_SCREEN_WEBRTC_ENABLED = true;
      const LEARNER_SCREEN_AUDIO_RELAY_MS = 360;
      const SCREEN_AUDIO_RELAY_MEDIA_SOURCE_ENABLED = false;
      const ADMIN_SCREEN_AUDIO_POLL_MS = 240;
      const LEARNER_SCREEN_CONTROL_POLL_MS = 60;
      const LEARNER_CHAT_POLL_OPEN_MS = 2500;
      const LEARNER_CHAT_POLL_IDLE_MS = 8000;
      const LEARNER_STREAM_POLL_ACTIVE_MS = 900;
      const LEARNER_STREAM_POLL_IDLE_MS = 5000;
      const LEARNER_SCREEN_POLL_ACTIVE_MS = 1200;
      const LEARNER_SCREEN_POLL_IDLE_MS = 6000;
      const SERVER_WORKSPACE_IDLE_POLL_MS = 10000;
      const isServerWorkspaceOpen = () => Boolean(serverBrowser && !serverBrowser.hidden);
      const serverWorkspacePollDelay = (baseMs, idleMs = SERVER_WORKSPACE_IDLE_POLL_MS) => (
        isServerWorkspaceOpen() ? Math.max(Number(baseMs) || 0, Number(idleMs) || SERVER_WORKSPACE_IDLE_POLL_MS) : baseMs
      );
      const chatImageViewerState = {
        zoom: 1,
        x: 0,
        y: 0,
        dragging: false,
        pointerId: 0,
        startX: 0,
        startY: 0,
        originX: 0,
        originY: 0,
      };
      let learnerPaintOpen = false;
      let learnerPaintMode = "pen";
      let learnerPaintPointer = null;
      let learnerPaintSelectedId = "";
      let learnerPaintIdSeed = 1;
      let learnerPaintBufferCanvas = null;
      let learnerPaintSelection = null;
      let learnerPaintTextEditor = null;
      let learnerPaintRevision = 0;
      let learnerPaintPollTimer = 0;
      let learnerPaintSyncTimer = 0;
      let learnerPaintCursorTimer = 0;
      let learnerPaintCursorSending = false;
      let learnerPaintLastCursorSentAt = 0;
      let learnerPaintLocalCursor = null;
      let learnerPaintRemoteCursor = null;
      let learnerPaintRemoteCursorNode = null;
      let learnerPaintTopStatusTimer = 0;
      let learnerPaintApplyingRemote = false;
      let learnerPaintSyncing = false;
      let learnerPaintServerConnected = false;
      let learnerPaintPollInFlight = false;
      let learnerPaintPendingSyncAfterConnect = false;
      let learnerPaintZoom = 1;
      let learnerPaintAutoOpenDone = false;
      let learnerPaintClearAnimating = false;
      let learnerPaintAutoEraseFrame = 0;
      let learnerPaintPenSize = 6;
      let learnerPaintEraserSize = 7;
      let learnerPaintTextSizeLevel = 6;
      let learnerPaintLastDustAt = 0;
      let learnerPaintSelectFirstPoint = null;
      let learnerPaintSelectMarkerNode = null;
      const LEARNER_PAINT_BOARD_WIDTH = 1920;
      const LEARNER_PAINT_BOARD_HEIGHT = 1080;
      const learnerPaintAutoOpen = new URLSearchParams(window.location.search || "").get("paint") === "1";
      const learnerPaintObjects = [];
      const LEARNER_PAINT_POLL_INTERVAL_MS = 10000;
      const LEARNER_PAINT_CURSOR_SYNC_INTERVAL_MS = 750;
      let authAnnouncementTimer = 0;
      let authAnnouncementSignature = "";
      let questionMotionSettings = { picture: "always", audio: "always" };
      let questionCardEffectsPaused = false;
      let questionAnimationsPaused = false;
      let questionRevealAnimationOverrideActive = false;
      let questionRevealAnimationRestorePaused = false;
      let questionAnimationChargeTimer = 0;
      let questionAnimationDischargeTimer = 0;
      let questionAnimationRebootTimer = 0;
      let questionAnimationRebootToken = 0;
      let questionIntroBootPending = false;
      let questionIntroBootTimer = 0;
      let questionIntroBootToken = 0;
      let questionModeActive = false;
      let questionCardsRevealSettled = false;
      let questionRevealAnimationsActive = false;
      let questionMobileLoadSmoothingTimer = 0;
      let questionViewportLayoutTimer = 0;
      let questionViewportLayoutFrame = 0;
      let questionViewportLayoutForce = false;
      let questionViewportLayoutGuidance = false;
      let questionViewportLayoutDelaySet = null;

      const setAuthStatus = (message, tone = "") => {
        if (!authStatus) {
          return;
        }
        authStatus.textContent = message || "";
        authStatus.classList.toggle("is-error", tone === "error");
        authStatus.classList.toggle("is-ok", tone === "ok");
      };

      const authNoticeFirstUpper = (value) => {
        const raw = clean(value);
        if (!raw) {
          return "";
        }
        const chars = Array.from(raw);
        for (let index = 0; index < chars.length; index += 1) {
          const char = chars[index];
          if (char.toLocaleLowerCase("vi-VN") !== char.toLocaleUpperCase("vi-VN")) {
            chars[index] = char.toLocaleUpperCase("vi-VN");
            return chars.join("");
          }
        }
        return raw;
      };

      const normalizeAuthAnnouncements = (items) => {
        const source = Array.isArray(items) ? items : [];
        return source
          .map((item) => authNoticeFirstUpper(item))
          .filter(Boolean)
          .slice(0, 8);
      };

      const renderAuthAnnouncements = (items, meta = {}) => {
        if (!authHudList) {
          return;
        }
        const rows = normalizeAuthAnnouncements(items);
        const fallback = rows.length ? rows : [
          "Chào mừng học viên đến hệ thống luyện dịch Future.",
          "Hãy đăng nhập để tải bài học và bắt đầu luyện tập.",
        ];
        const signature = JSON.stringify({ rows: fallback, updated_at: meta.updated_at || "", status: meta.status || "" });
        if (signature === authAnnouncementSignature) {
          return;
        }
        authAnnouncementSignature = signature;
        authHudList.textContent = "";
        fallback.forEach((text) => {
          const item = document.createElement("div");
          item.className = "ft-auth-hud-message";
          item.textContent = text;
          authHudList.appendChild(item);
        });
        if (authHudStatusText) {
          authHudStatusText.textContent = meta.status || (meta.updated_at ? `server feed ${meta.updated_at}` : "server feed ready");
        }
        if (authHudStamp) {
          authHudStamp.textContent = meta.updated_at ? "UPDATED" : "LIVE FEED";
        }
        updateAuthHudVersionLine();
      };

      const publicServerJsonResponseCache = new Map();
      const PUBLIC_SERVER_JSON_CACHE_SCHEMA_VERSION = 1;
      const fetchPublicServerJson = async (path) => {
        const errors = [];
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const normalizedPath = String(path || "")
          .replace(/([?&])ts=[^&]*/g, "$1")
          .replace(/\?&/g, "?")
          .replace(/&&+/g, "&")
          .replace(/[?&]$/, "");
        for (const base of candidates) {
          try {
            const cacheKey = `${base}|${normalizedPath}`;
            const cached = publicServerJsonResponseCache.get(cacheKey);
            const headers = {};
            const canRevalidate = Boolean(
              cached &&
              Number(cached.schema_version || 0) === PUBLIC_SERVER_JSON_CACHE_SCHEMA_VERSION &&
              cached.payload && typeof cached.payload === "object" &&
              clean(cached.etag)
            );
            if (canRevalidate) {
              headers["If-None-Match"] = cached.etag;
            }
            let response = await fetch(`${base}${path}`, {
              method: "GET",
              mode: "cors",
              cache: "no-store",
              headers,
            });
            if (response.status === 304 && canRevalidate) {
              return cached.payload;
            }
            if (response.status === 304) {
              response = await fetch(`${base}${path}`, {
                method: "GET",
                mode: "cors",
                cache: "no-store",
                headers: {},
              });
            }
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.ok === false) {
              throw new Error(clean(payload.error) || `Server loi ${response.status}`);
            }
            const etag = clean(response.headers && response.headers.get ? response.headers.get("ETag") : "");
            if (etag) {
              publicServerJsonResponseCache.set(cacheKey, {
                schema_version: PUBLIC_SERVER_JSON_CACHE_SCHEMA_VERSION,
                etag,
                payload,
              });
            }
            return payload;
          } catch (error) {
            errors.push(`${base}: ${error && error.message ? error.message : error}`);
          }
        }
        throw new Error(errors.join(" | "));
      };

      const refreshAuthAnnouncements = async () => {
        try {
          const payload = await fetchPublicServerJson(`/announcements?ts=${Date.now()}`);
          renderAuthAnnouncements(payload.items || [], {
            updated_at: clean(payload.updated_at),
            status: payload.updated_at ? "server notice synced" : "server feed ready",
          });
        } catch (error) {
          renderAuthAnnouncements([], { status: "waiting for server feed" });
        }
      };

      const startAuthAnnouncements = () => {
        void refreshAuthAnnouncements();
        if (authAnnouncementTimer) {
          return;
        }
        authAnnouncementTimer = window.setInterval(refreshAuthAnnouncements, 8000);
      };

      const stopAuthAnnouncements = () => {
        if (!authAnnouncementTimer) {
          return;
        }
        window.clearInterval(authAnnouncementTimer);
        authAnnouncementTimer = 0;
      };

      // Added 2026-07-01: show the server notice feed immediately on the initial login gate.
      if (authGate && !authGate.classList.contains("is-hidden")) {
        startAuthAnnouncements();
      }

      const AUTH_DNA_BRANCH_COUNT = 4;
      const AUTH_DNA_RUNG_COUNT = 18;
      const AUTH_DNA_EDGE_SEED = 0.28;
      const authEaseInOut = (value) => {
        const t = Math.max(0, Math.min(1, Number(value) || 0));
        return t * t * t * (t * (t * 6 - 15) + 10);
      };
      const clampAuthUnit = (value) => Math.max(0, Math.min(1, Number(value) || 0));
      const authConnectorPhaseUnit = (value) => {
        const phase = Number(value) || 0;
        return ((phase % 1) + 1) % 1;
      };
      const authConnectorCycleDelay = (duration, phase) => `${-(duration * authConnectorPhaseUnit(phase)).toFixed(3)}s`;
      const authConnectorPathPhaseOffset = (kind) => {
        if (kind === "strand-a") {
          return 0.25;
        }
        if (kind === "strand-b") {
          return 0.5;
        }
        if (kind === "spark") {
          return 0.75;
        }
        return 0;
      };
      const authConnectorPathDuration = (kind) => {
        if (kind === "glow") {
          return 6.9;
        }
        if (kind === "spark") {
          return 2.025;
        }
        return 3.525;
      };
      const authConnectorRungPhase = (branchPhase, rung) => {
        const stagger = (rung % 2 === 0 ? 0.25 : 0.5);
        const chain = (rung * stagger) + ((Math.floor(rung / 3) % 2) * 0.25);
        return branchPhase + chain;
      };
      const authConnectorBranchLag = (index) => authConnectorPhaseSlots[index] ?? 0;
      const authConnectorBranchProgress = (progress, index) => {
        const lag = authConnectorBranchLag(index);
        const safeProgress = clampAuthUnit(progress);
        if (lag <= 0) {
          return safeProgress;
        }
        if (authConnectorTarget > 0.5) {
          return clampAuthUnit((safeProgress - lag) / (1 - lag));
        }
        return clampAuthUnit(safeProgress / (1 - lag));
      };
      const resetAuthConnectorImpactFx = () => {
        authConnectorCornerFlashed = [false, false, false, false];
        authConnectorConnectedCount = 0;
        authConnectorShockwaveFired = false;
        authCornerFlashNodes.forEach((node) => node?.classList.remove("is-flashing"));
        authPanelShockwaveNode?.classList.remove("is-shocking");
      };
      const applyAuthConnectorAnimationPhases = () => {
        authConnectorElements.forEach((branch, index) => {
          if (!branch) {
            return;
          }
          const branchPhase = authConnectorBranchLag(index);
          Object.entries(branch.paths || {}).forEach(([kind, path]) => {
            if (!path) {
              return;
            }
            path.style.animationDelay = authConnectorCycleDelay(
              authConnectorPathDuration(kind),
              branchPhase + authConnectorPathPhaseOffset(kind),
            );
          });
          (branch.rungs || []).forEach((line, rung) => {
            if (!line) {
              return;
            }
            line.style.animationDelay = authConnectorCycleDelay(2.475, authConnectorRungPhase(branchPhase, rung));
          });
          Object.values(branch.nodes || {}).forEach((node, nodeIndex) => {
            if (node) {
              node.style.animationDelay = authConnectorCycleDelay(2.1, branchPhase + (nodeIndex ? 0.5 : 0.25));
            }
          });
        });
      };
      const randomizeAuthConnectorBends = () => {
        authConnectorPhaseSlots = [0, 0.5, 0, 0.5];
        resetAuthConnectorImpactFx();
        authConnectorBendSeeds = Array.from({ length: AUTH_DNA_BRANCH_COUNT }, (_unused, index) => ({
          phase: (Math.random() * Math.PI * 2) + (index * 0.7),
          bendBoost: 0.82 + (Math.random() * 0.5),
          bendWaves: -0.12 + (Math.random() * 0.28),
          strandWaves: -0.18 + (Math.random() * 0.34),
          diagonal: -0.015 + (Math.random() * 0.03),
        }));
        applyAuthConnectorAnimationPhases();
      };
      const authConnectorBendSeed = (index) => authConnectorBendSeeds[index] || {
        phase: index * 0.72,
        bendBoost: 1,
        bendWaves: 0,
        strandWaves: 0,
        diagonal: 0,
      };

      const clearAuthConnectorFrame = () => {
        if (authConnectorFrame) {
          window.cancelAnimationFrame(authConnectorFrame);
          authConnectorFrame = 0;
        }
      };

      const ensureAuthConnectorPaths = () => {
        if (!authConnectorLines) {
          return;
        }
        if (authConnectorLines.dataset.kind === "corner-dna-v2" && authConnectorLines.childNodes.length) {
          return;
        }
        authConnectorLines.textContent = "";
        authConnectorLines.dataset.kind = "corner-dna-v2";
        authConnectorElements = [];
        if (authConnectorNodes) {
          authConnectorNodes.textContent = "";
        }
        for (let index = 0; index < AUTH_DNA_BRANCH_COUNT; index += 1) {
          const branch = { paths: {}, rungs: [], nodes: {} };
          ["glow", "strand-a", "strand-b", "spark"].forEach((kind) => {
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.classList.add(`ft-auth-connector-${kind}`);
            path.dataset.index = String(index);
            branch.paths[kind] = path;
            authConnectorLines.appendChild(path);
          });
          for (let rung = 0; rung < AUTH_DNA_RUNG_COUNT; rung += 1) {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.classList.add("ft-auth-connector-rung");
            if (rung % 5 === 1 || rung % 5 === 4) {
              line.classList.add("is-hot");
            }
            line.dataset.index = String(index);
            line.dataset.rung = String(rung);
            branch.rungs[rung] = line;
            authConnectorLines.appendChild(line);
          }
          if (authConnectorNodes) {
            ["outer", "inner"].forEach((kind) => {
              const node = document.createElementNS("http://www.w3.org/2000/svg", "circle");
              node.classList.add("ft-auth-node");
              node.dataset.index = String(index);
              node.dataset.node = kind;
              node.setAttribute("r", kind === "inner" ? "4.8" : "3.6");
              branch.nodes[kind] = node;
              authConnectorNodes.appendChild(node);
            });
          }
          authConnectorElements[index] = branch;
        }
        applyAuthConnectorAnimationPhases();
      };

      const dnaPoint = (start, end, t, amplitude, phase, waves = 2.2, bend = 0, bendPhase = 0, bendWaves = 0.85) => {
        const sx = Number(start[0]);
        const sy = Number(start[1]);
        const ex = Number(end[0]);
        const ey = Number(end[1]);
        const dx = ex - sx;
        const dy = ey - sy;
        const length = Math.max(1, Math.hypot(dx, dy));
        const nx = -dy / length;
        const ny = dx / length;
        const taper = Math.sin(Math.PI * t);
        const centerCurve = bend * taper * Math.sin((t * Math.PI * 2 * bendWaves) + bendPhase);
        const strandWave = amplitude * taper * Math.sin((t * Math.PI * 2 * waves) + phase);
        const offset = centerCurve + strandWave;
        return [sx + (dx * t) + (nx * offset), sy + (dy * t) + (ny * offset)];
      };

      const dnaPath = (start, end, amplitude, phase, waves = 2.2, steps = 34, bend = 0, bendPhase = 0, bendWaves = 0.85) => {
        const points = [];
        for (let step = 0; step <= steps; step += 1) {
          points.push(dnaPoint(start, end, step / steps, amplitude, phase, waves, bend, bendPhase, bendWaves));
        }
        return points.map((point, index) => `${index ? "L" : "M"} ${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(" ");
      };

      const dnaPartialPath = (start, end, visible, amplitude, phase, waves = 2.2, steps = 72, bend = 0, bendPhase = 0, bendWaves = 0.85) => {
        const maxT = clampAuthUnit(visible);
        if (maxT <= 0.002) {
          return "";
        }
        const count = Math.max(4, Math.ceil(steps * maxT));
        const points = [];
        for (let step = 0; step <= count; step += 1) {
          const t = (step / count) * maxT;
          points.push(dnaPoint(start, end, t, amplitude, phase, waves, bend, bendPhase, bendWaves));
        }
        return points.map((point, index) => `${index ? "L" : "M"} ${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(" ");
      };

      const setLineEndpoints = (line, a, b) => {
        if (!line) {
          return;
        }
        line.setAttribute("x1", a[0].toFixed(1));
        line.setAttribute("y1", a[1].toFixed(1));
        line.setAttribute("x2", b[0].toFixed(1));
        line.setAttribute("y2", b[1].toFixed(1));
      };

      const ensureAuthPanelFxLayer = () => {
        if (!authGate) {
          return null;
        }
        if (authPanelFxLayer) {
          return authPanelFxLayer;
        }
        authPanelFxLayer = document.createElement("div");
        authPanelFxLayer.className = "ft-auth-panel-fx";
        authPanelFxLayer.setAttribute("aria-hidden", "true");
        authPanelShockwaveNode = document.createElement("span");
        authPanelShockwaveNode.className = "ft-auth-panel-shockwave";
        authPanelFxLayer.appendChild(authPanelShockwaveNode);
        authCornerFlashNodes = [];
        for (let index = 0; index < AUTH_DNA_BRANCH_COUNT; index += 1) {
          const flash = document.createElement("span");
          flash.className = `ft-auth-corner-flash is-corner-${index}`;
          authCornerFlashNodes[index] = flash;
          authPanelFxLayer.appendChild(flash);
        }
        authGate.appendChild(authPanelFxLayer);
        return authPanelFxLayer;
      };

      const positionAuthPanelFxLayer = (panelRect = null) => {
        if (!authPanel || !authGate) {
          return;
        }
        const layer = ensureAuthPanelFxLayer();
        if (!layer) {
          return;
        }
        const rect = panelRect || authPanel.getBoundingClientRect();
        const gateRect = authGate.getBoundingClientRect();
        layer.style.left = `${(rect.left - gateRect.left).toFixed(1)}px`;
        layer.style.top = `${(rect.top - gateRect.top).toFixed(1)}px`;
        layer.style.width = `${rect.width.toFixed(1)}px`;
        layer.style.height = `${rect.height.toFixed(1)}px`;
        layer.style.borderRadius = window.getComputedStyle(authPanel).borderRadius || "24px";
      };

      const restartAuthClassAnimation = (node, className) => {
        if (!node) {
          return;
        }
        node.classList.remove(className);
        void node.offsetWidth;
        node.classList.add(className);
      };

      const triggerAuthCornerImpact = (index, panelRect = null) => {
        if (!AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED) {
          return;
        }
        positionAuthPanelFxLayer(panelRect);
        const flash = authCornerFlashNodes[index];
        restartAuthClassAnimation(flash, "is-flashing");
        window.setTimeout(() => flash?.classList.remove("is-flashing"), 1100);
      };

      const triggerAuthPanelShockwave = (panelRect = null) => {
        if (!AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED) {
          return;
        }
        positionAuthPanelFxLayer(panelRect);
        restartAuthClassAnimation(authPanelShockwaveNode, "is-shocking");
        window.setTimeout(() => authPanelShockwaveNode?.classList.remove("is-shocking"), 1500);
      };

      const authConnectorImpactProgressThreshold = (index) => (
        authConnectorBranchLag(index) >= 0.5 ? 0.92 : 0.88
      );

      const markAuthConnectorImpact = (index, panelRect = null) => {
        if (authConnectorCornerFlashed[index]) {
          return;
        }
        authConnectorCornerFlashed[index] = true;
        authConnectorConnectedCount += 1;
        if (AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED) {
          triggerAuthCornerImpact(index, panelRect);
        }
        if (authConnectorConnectedCount >= AUTH_DNA_BRANCH_COUNT && !authConnectorShockwaveFired) {
          authConnectorShockwaveFired = true;
          if (AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED) {
            window.setTimeout(() => triggerAuthPanelShockwave(panelRect), 140);
          }
        }
      };

      const positionAuthConnectors = (progress = authConnectorProgress) => {
        if (!AUTH_LOGIN_CONNECTOR_FX_ENABLED) {
          clearAuthConnectorFrame();
          authConnectorProgress = 0;
          authConnectorTarget = 0;
          if (authGate) {
            authGate.classList.remove("is-auth-connectors-active", "is-auth-motion-exit");
          }
          if (authConnectorLines && authConnectorLines.childNodes.length) {
            authConnectorLines.textContent = "";
          }
          if (authConnectorNodes && authConnectorNodes.childNodes.length) {
            authConnectorNodes.textContent = "";
          }
          authConnectorElements = [];
          resetAuthConnectorImpactFx();
          return;
        }
        if (!authConnectors || !authPanel || !authGate || authGate.classList.contains("is-hidden")) {
          return;
        }
        ensureAuthConnectorPaths();
        const amount = Math.max(0, Math.min(1, Number(progress) || 0));
        const width = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
        const height = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
        const rect = authPanel.getBoundingClientRect();
        if (AUTH_LOGIN_CONNECTOR_IMPACT_FX_ENABLED) {
          positionAuthPanelFxLayer(rect);
        }
        authConnectors.setAttribute("viewBox", `0 0 ${width} ${height}`);
        const endpoints = [
          { start: [rect.left + 8, rect.top + 8], end: [14, 14], bendPhase: -0.45 },
          { start: [rect.right - 8, rect.top + 8], end: [width - 14, 14], bendPhase: 0.72 },
          { start: [rect.right - 8, rect.bottom - 8], end: [width - 14, height - 14], bendPhase: -0.88 },
          { start: [rect.left + 8, rect.bottom - 8], end: [14, height - 14], bendPhase: 0.55 },
        ];
        endpoints.forEach((item, index) => {
          const seed = authConnectorBendSeed(index);
          const branchAmount = authConnectorBranchProgress(amount, index);
          const edgeSeed = authConnectorTarget > 0.5
            ? AUTH_DNA_EDGE_SEED * authEaseInOut(clampAuthUnit(branchAmount / 0.16))
            : 0;
          const drawAmount = authConnectorTarget > 0.5
            ? Math.min(1, edgeSeed + (branchAmount * (1 - edgeSeed)))
            : branchAmount;
          if (authConnectorTarget > 0.5 && branchAmount >= authConnectorImpactProgressThreshold(index)) {
            markAuthConnectorImpact(index, rect);
          }
          const edgePoint = item.end;
          const panelPoint = item.start;
          const length = Math.hypot(edgePoint[0] - panelPoint[0], edgePoint[1] - panelPoint[1]);
          const growthScale = clampAuthUnit((drawAmount - 0.02) / 0.38);
          const amplitude = Math.max(10, Math.min(34, length * 0.045)) * (0.72 + (growthScale * 0.42));
          const bend = Math.max(9, Math.min(42, length * 0.05)) * (0.62 + (growthScale * 0.5)) * seed.bendBoost;
          const waves = Math.max(2.1, Math.min(3.55, length / 230 + seed.strandWaves));
          const bendWaves = 0.72 + ((index % 2) * 0.16) + seed.bendWaves;
          const bendPhase = item.bendPhase + seed.phase;
          const branch = authConnectorElements[index] || {};
          const paths = branch.paths || {};
          if (drawAmount <= 0.001) {
            Object.values(paths).forEach((path) => path?.setAttribute("d", ""));
            (branch.rungs || []).forEach((rungLine) => {
              if (rungLine) {
                rungLine.style.display = "none";
                rungLine.style.opacity = "0";
              }
            });
            return;
          }
          const glow = dnaPartialPath(edgePoint, panelPoint, drawAmount, amplitude * 0.22, Math.PI * 0.35, 1.15, 72, bend, bendPhase, bendWaves);
          const strandA = dnaPartialPath(edgePoint, panelPoint, drawAmount, amplitude, 0, waves, 96, bend, bendPhase, bendWaves);
          const strandB = dnaPartialPath(edgePoint, panelPoint, drawAmount, amplitude, Math.PI, waves, 96, bend, bendPhase, bendWaves);
          const spark = dnaPartialPath(edgePoint, panelPoint, drawAmount, amplitude * 0.55, Math.PI * 0.5, waves, 96, bend * 0.76, bendPhase + 0.35, bendWaves);
          paths.glow?.setAttribute("d", glow);
          paths["strand-a"]?.setAttribute("d", strandA);
          paths["strand-b"]?.setAttribute("d", strandB);
          paths.spark?.setAttribute("d", spark);
          const outerNode = branch.nodes && branch.nodes.outer;
          const innerNode = branch.nodes && branch.nodes.inner;
          if (outerNode) {
            outerNode.setAttribute("cx", edgePoint[0].toFixed(1));
            outerNode.setAttribute("cy", edgePoint[1].toFixed(1));
          }
          if (innerNode) {
            const tipPoint = dnaPoint(edgePoint, panelPoint, drawAmount, amplitude * 0.32, 0, waves, bend, bendPhase, bendWaves);
            innerNode.setAttribute("cx", tipPoint[0].toFixed(1));
            innerNode.setAttribute("cy", tipPoint[1].toFixed(1));
          }
          for (let rung = 0; rung < AUTH_DNA_RUNG_COUNT; rung += 1) {
            const t = (rung + 0.5) / AUTH_DNA_RUNG_COUNT;
            const rungProgress = clampAuthUnit((drawAmount - t + 0.055) / 0.105);
            const diagonalShift = ((rung % 2 === 0 ? 1 : -1) * 0.04 + Math.sin((rung + index + seed.phase) * 0.78) * 0.014 + seed.diagonal) * clampAuthUnit(drawAmount * 1.35);
            const twinT = clampAuthUnit(t + diagonalShift);
            const a = dnaPoint(edgePoint, panelPoint, t, amplitude, 0, waves, bend, bendPhase, bendWaves);
            const b = dnaPoint(edgePoint, panelPoint, twinT, amplitude, Math.PI, waves, bend, bendPhase, bendWaves);
            const rungLine = branch.rungs && branch.rungs[rung];
            if (rungLine) {
              rungLine.style.display = rungProgress <= 0.02 ? "none" : "";
              rungLine.style.opacity = rungProgress <= 0.02 ? "0" : (0.18 + (rungProgress * 0.74)).toFixed(3);
              setLineEndpoints(rungLine, a, b);
            }
          }
        });
      };

      const runAuthConnectorMotion = (targetProgress = 1, durationMs = 760) => {
        if (!AUTH_LOGIN_CONNECTOR_FX_ENABLED || !authGate || !authConnectors || !canRunAuthFocusMotion()) {
          clearAuthConnectorFrame();
          authConnectorProgress = 0;
          authConnectorTarget = 0;
          if (authGate) {
            authGate.classList.remove("is-auth-connectors-active", "is-auth-motion-exit");
          }
          return;
        }
        const target = Math.max(0, Math.min(1, Number(targetProgress) || 0));
        if (!authConnectorFrame && Math.abs(authConnectorProgress - target) < 0.004) {
          authConnectorProgress = target;
          authConnectorTarget = target;
          if (target > 0.001) {
            authGate.classList.add("is-auth-connectors-active");
          }
          positionAuthConnectors(authConnectorProgress);
          return;
        }
        const start = authConnectorProgress;
        const duration = Math.max(180, Number(durationMs) || 760);
        const startedAt = performance.now();
        clearAuthConnectorFrame();
        authConnectorTarget = target;
        authGate.classList.add("is-auth-connectors-active");
        authGate.classList.toggle("is-auth-motion-exit", target <= 0);
        const step = (now) => {
          const t = Math.max(0, Math.min(1, (now - startedAt) / duration));
          authConnectorProgress = start + ((target - start) * authEaseInOut(t));
          positionAuthConnectors(authConnectorProgress);
          if (t < 1) {
            authConnectorFrame = window.requestAnimationFrame(step);
            return;
          }
          authConnectorFrame = 0;
          authConnectorProgress = target;
          positionAuthConnectors(authConnectorProgress);
          if (target <= 0.001) {
            authGate.classList.remove("is-auth-connectors-active", "is-auth-motion-exit");
            resetAuthConnectorImpactFx();
          } else {
            authGate.classList.remove("is-auth-motion-exit");
          }
        };
        authConnectorFrame = window.requestAnimationFrame(step);
      };

      const startAuthConnectorIntro = () => {
        if (!AUTH_LOGIN_CONNECTOR_FX_ENABLED) {
          return;
        }
        if (authConnectorFrame && authConnectorTarget >= 0.999) {
          return;
        }
        if (authConnectorTarget < 0.5) {
          resetAuthConnectorImpactFx();
        }
        if (authConnectorProgress <= 0.03) {
          randomizeAuthConnectorBends();
        }
        runAuthConnectorMotion(1, authConnectorProgress > 0.25 ? 3300 : 5100);
      };

      const startAuthConnectorOutro = () => {
        if (!AUTH_LOGIN_CONNECTOR_FX_ENABLED) {
          clearAuthConnectorFrame();
          authConnectorProgress = 0;
          authConnectorTarget = 0;
          if (authGate) {
            authGate.classList.remove("is-auth-connectors-active", "is-auth-motion-exit");
          }
          resetAuthConnectorImpactFx();
          return;
        }
        if (!authGate || authGate.classList.contains("is-hidden") || authConnectorProgress <= 0.001) {
          clearAuthConnectorFrame();
          authConnectorProgress = 0;
          authConnectorTarget = 0;
          if (authGate) {
            authGate.classList.remove("is-auth-connectors-active", "is-auth-motion-exit");
          }
          return;
        }
        runAuthConnectorMotion(0, 3900);
      };

      const setAuthMode = (mode, profile = {}) => {
        authMode = mode === "register" || mode === "profile" || mode === "session" || mode === "reset" ? mode : "login";
        if (authMode !== "reset") {
          authResetApproved = false;
        }
        if (!authGate) {
          return;
        }
        authGate.classList.toggle("is-register", authMode === "register");
        authGate.classList.toggle("is-profile", authMode === "profile");
        authGate.classList.toggle("is-session", authMode === "session");
        authGate.classList.toggle("is-reset", authMode === "reset");
        authGate.classList.toggle("is-reset-approved", authMode === "reset" && authResetApproved);
        authLoginTab.classList.toggle("is-active", authMode === "login");
        authRegisterTab.classList.toggle("is-active", authMode === "register");
        if (authMode === "register") {
          authModeNode.textContent = "REGISTER REQUEST";
          authTitle.textContent = "Create Student Account";
          authSubmit.textContent = "Send Request";
          authPass.setAttribute("autocomplete", "one-time-code");
          authPass.setAttribute("enterkeyhint", "next");
        } else if (authMode === "profile") {
          authModeNode.textContent = "PROFILE REQUIRED";
          authTitle.textContent = "Complete Profile";
          authSubmit.textContent = "Save Profile";
          authPass.setAttribute("autocomplete", "one-time-code");
          authPass.setAttribute("enterkeyhint", "next");
        } else if (authMode === "session") {
          authModeNode.textContent = "ACTIVE SESSION";
          authTitle.textContent = "Active Session";
          authSubmit.textContent = "Verify & Enter";
          authPass.setAttribute("autocomplete", "one-time-code");
          authPass.setAttribute("enterkeyhint", "go");
        } else if (authMode === "reset") {
          authModeNode.textContent = authResetApproved ? "RESET APPROVED" : "PASSWORD RESET";
          authTitle.textContent = authResetApproved ? "Set New Password" : "Request Password Reset";
          authSubmit.textContent = authResetApproved ? "Change Password" : "Send Request";
          if (authResetSend) {
            authResetSend.textContent = authResetApproved ? "Approved - enter new password" : "Send / check approval";
          }
          authPass.setAttribute("autocomplete", "new-password");
          authPass.setAttribute("enterkeyhint", authResetApproved ? "next" : "done");
        } else {
          authModeNode.textContent = "ACCOUNT GATE";
          authTitle.textContent = "Student Login";
          authSubmit.textContent = "Verify & Enter";
          authPass.setAttribute("autocomplete", "one-time-code");
          authPass.setAttribute("enterkeyhint", "go");
        }
        if (profile && typeof profile === "object") {
          authFullName.value = profile.full_name || authFullName.value || "";
          authGender.value = profile.gender || authGender.value || "";
          authBirth.value = profile.birth_date || authBirth.value || "";
          if (authEmail) {
            authEmail.value = profile.email || profile.gmail || authEmail.value || "";
          }
        }
        window.requestAnimationFrame(positionAuthConnectors);
        window.setTimeout(positionAuthConnectors, 260);
      };

      const authProfilePayload = () => ({
        full_name: clean(authFullName.value),
        gender: clean(authGender.value),
        birth_date: clean(authBirth.value),
        email: authEmail ? clean(authEmail.value) : "",
      });

      const isAuthSessionFailureReason = (reason) => ["missing_token", "invalid_token", "session_expired", "session_replaced"].includes(clean(reason).toLowerCase());

      const authSessionFailureMessage = (reason) => {
        const code = clean(reason).toLowerCase();
        if (code === "session_replaced") {
          return "This account just signed in somewhere else, so this session was signed out.";
        }
        if (code === "session_expired") {
          return "Your login session expired. Sign in again.";
        }
        if (code === "invalid_token") {
          return "Your login session is no longer valid. Sign in again.";
        }
        return "Sign in to continue.";
      };

      const resetActiveLearningModesForAuth = (options = {}) => {
        const keepLoginBackdrop = Boolean(options.keepLoginBackdrop);
        try {
          sessionStorage.removeItem(RELOAD_SESSION_KEY);
        } catch (error) {
        }
        try {
          if (typeof stopParagraphAudioPlayback === "function") {
            stopParagraphAudioPlayback();
          }
        } catch (error) {
        }
        try {
          if (typeof resetParagraphMode === "function") {
            resetParagraphMode();
          }
        } catch (error) {
        }
        try {
          if (typeof resetQuestionMode === "function") {
            resetQuestionMode();
          }
        } catch (error) {
        }
        try {
          if (typeof resetSpaceWCache === "function") {
            resetSpaceWCache();
          }
        } catch (error) {
        }
        try {
          if (typeof resetPdfMode === "function") {
            resetPdfMode();
          }
        } catch (error) {
        }
        try {
          vocabAnswerAudioToken += 1;
          vocabModeActive = false;
          vocabModeTransitioning = false;
          if (typeof hideVocabModePopup === "function") {
            hideVocabModePopup();
          }
          if (typeof clearVocabHintTimers === "function") {
            clearVocabHintTimers();
          }
          if (vocabCard) {
            vocabCard.classList.add("is-hidden");
            resetVocabCardRevealStyles();
          }
          if (vocabAnswer) {
            vocabAnswer.value = "";
            vocabAnswer.disabled = false;
            vocabAnswer.readOnly = false;
            vocabAnswer.setAttribute("aria-busy", "false");
          }
          resetVocabLearnedPanelPosition();
          resetVocabUnlearnedPanelPosition();
          resetVocabSideCardPositions();
        } catch (error) {
        }
        try {
          if (cardNode) {
            cardNode.classList.add("is-hidden");
          }
          if (stageNode) {
            stageNode.classList.remove("is-question-mode", "is-question-idle-static");
          }
          if (shellNode) {
            shellNode.classList.remove("is-space-w-active");
          }
          setSpaceWModeClass(false);
          setParagraphModeClass(false);
          setQuestionInventoryHudVisible(false);
        } catch (error) {
        }
        try {
          hideVocabPreflightGate();
          stopTaskNoticeImmediatePolling();
          stopLearnerChatPolling();
          stopLearnerStreamPolling();
          stopLearnerScreenPolling();
          stopLearnerPaintPolling();
          setLearnerChatVisible(false);
        } catch (error) {
        }
        try {
          if (typeof closeSharedWorld === "function") {
            closeSharedWorld();
          }
        } catch (error) {
        }
        if (!keepLoginBackdrop) {
          try {
            if (serverBrowser) {
              serverBrowser.hidden = true;
              serverBrowser.classList.remove("is-open");
              syncServerWorkspaceOpenState();
            }
          } catch (error) {
          }
        }
      };

      const stopAuthSessionMonitor = () => {
        if (authSessionMonitorTimer) {
          window.clearInterval(authSessionMonitorTimer);
          authSessionMonitorTimer = 0;
        }
      };

      const invalidateAuthSession = (reason = "") => {
        const message = authSessionFailureMessage(reason);
        if (authSessionInvalidating) {
          return message;
        }
        authSessionInvalidating = true;
        currentAuthUsername = "";
        hologramCursorUserOverride = "";
        pendingSpaceWAfterVocabulary = null;
        currentVocabularyMission = null;
        vocabPreflightState = null;
        vocabPreflightBuildToken += 1;
        spaceWVocabBuildGuardPath = "";
        spaceWVocabSkipPaths = new Set();
        spaceWVocabClearedPaths = new Set();
        resetActiveLearningModesForAuth();
        showLoginGate(message);
        window.setTimeout(() => {
          authSessionInvalidating = false;
        }, 0);
        return message;
      };

      const fetchAuthJson = async (path, options = {}) => {
        const errors = [];
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const rawOptions = options && typeof options === "object" ? options : {};
        const fetchOptions = { ...rawOptions };
        const hasTimeoutOverride = Object.prototype.hasOwnProperty.call(fetchOptions, "timeoutMs");
        const timeoutOverride = hasTimeoutOverride ? Number(fetchOptions.timeoutMs) : null;
        const ifNoneMatch = clean(fetchOptions.ifNoneMatch || "");
        const notModifiedPayload = fetchOptions.notModifiedPayload && typeof fetchOptions.notModifiedPayload === "object"
          ? fetchOptions.notModifiedPayload
          : null;
        const canRevalidate = Boolean(ifNoneMatch && notModifiedPayload);
        delete fetchOptions.timeoutMs;
        delete fetchOptions.silentTimeout;
        delete fetchOptions.ifNoneMatch;
        delete fetchOptions.notModifiedPayload;
        const authJsonTimeoutForPath = (value = "") => {
          const target = clean(value);
          if (target === "/auth/me") {
            return 14400;
          }
          if (target === "/auth/login") {
            return 28800;
          }
          if (target.startsWith("/pdf/") || target.startsWith("/picture/")) {
            return 0;
          }
          if (
            target === "/ai-agent/ask" ||
            target === "/word-agent/ask" ||
            target === "/pdf/agent-explain" ||
            target === "/ai-agent/space-p/followup"
          ) {
            return 150000;
          }
          if (target === "/pdf/create-vocabulary") {
            return 0;
          }
          if (target.startsWith("/world/")) {
            return 0;
          }
          if (target === "/qmdict/update") {
            return 0;
          }
          return 36000;
        };
        // Added 2026-07-04: keeps login/auth checks alive while Cloudflare tunnel reconnects.
        const authJsonRetryCountForPath = (value = "") => {
          const target = clean(value);
          if (target === "/auth/me" || target === "/auth/login") {
            return 3;
          }
          return 1;
        };
        const authJsonLabelForPath = (value = "") => {
          const target = clean(value);
          if (target === "/pdf/agent-explain") {
            return "Ghost Eye Agent";
          }
          if (target.startsWith("/pdf/") || target.startsWith("/picture/")) {
            return "Ghost Eye";
          }
          if (target === "/word-agent/ask") {
            return "Ghost Word Agent";
          }
          if (target === "/ai-agent/ask" || target === "/ai-agent/space-p/followup") {
            return "Ghost AI";
          }
          if (target.startsWith("/world/")) {
            return "QM-City";
          }
          if (target === "/qmdict/update") {
            return "QmDict";
          }
          return "auth server";
        };
        const timeoutMs = hasTimeoutOverride ? timeoutOverride : authJsonTimeoutForPath(path);
        const friendlyAuthError = (status, payload = {}) => {
          const reason = clean(payload.reason || payload.code || "").toLowerCase();
          if (path === "/auth/login") {
            if (reason === "missing_username") {
              return "Vui lòng nhập tên tài khoản.";
            }
            if (reason === "missing_password") {
              return "Vui lòng nhập mật khẩu.";
            }
            if (reason === "nouser") {
              return "Tài khoản không tồn tại. Hãy kiểm tra lại tên đăng nhập.";
            }
            if (reason === "wrongpass") {
              return "Mật khẩu không đúng. Hãy nhập lại mật khẩu.";
            }
            if (reason === "login_locked") {
              const retry = Number(payload.retry_after || 0);
              const seconds = Number.isFinite(retry) && retry > 0 ? Math.ceil(retry) : 300;
              return `Tài khoản tạm khóa do nhập sai quá nhiều. Thử lại sau khoảng ${seconds} giây.`;
            }
          }
          if (status === 429) {
            const retry = Number(payload.retry_after || 0);
            const seconds = Number.isFinite(retry) && retry > 0 ? Math.ceil(retry) : 5;
            return clean(payload.error) || `Yêu cầu hơi nhanh. Thử lại sau ${seconds} giây.`;
          }
          return clean(payload.error) || `Máy chủ báo lỗi ${status}.`;
        };
        const retryCount = authJsonRetryCountForPath(path);
        for (const base of candidates) {
          for (let attempt = 1; attempt <= retryCount; attempt += 1) {
            try {
              const headers = await antiRobotHeaders(base, {
                "Content-Type": "application/json",
                ...(options.headers || {}),
              });
              if (!authToken) {
                authToken = getStoredAuthToken();
              }
              if (authToken) {
                headers.Authorization = `Bearer ${authToken}`;
              }
              if (path === "/auth/preferences") {
                headers["X-Future-Response-Mode"] = "preferences-compact-v1";
              }
              if (canRevalidate) {
                headers["If-None-Match"] = ifNoneMatch;
              }
              let response = await fetchWithTimeout(`${base}${path}`, {
                ...fetchOptions,
                headers,
                mode: "cors",
                cache: "no-store",
              }, timeoutMs);
              if (response.status === 304 && !notModifiedPayload) {
                delete headers["If-None-Match"];
                response = await fetchWithTimeout(`${base}${path}`, {
                  ...fetchOptions,
                  headers,
                  mode: "cors",
                  cache: "no-store",
                }, timeoutMs);
              }
              const responseEtag = clean(response.headers && response.headers.get ? response.headers.get("ETag") : "");
              if (response.status === 304 && notModifiedPayload) {
                return { base, payload: notModifiedPayload, notModified: true, etag: responseEtag || ifNoneMatch };
              }
              const payload = await response.json().catch(() => ({}));
              if (!response.ok || payload.ok === false) {
                const finalReason = clean(payload.reason || payload.code || "").toLowerCase();
                const finalMessage = response.status === 401 && authToken && isAuthSessionFailureReason(finalReason)
                  ? invalidateAuthSession(finalReason)
                  : friendlyAuthError(response.status, payload);
                const error = new Error(finalMessage);
                error.status = response.status;
                error.reason = finalReason;
                error.fromFutureServer = payload && payload.ok === false;
                throw error;
              }
              return { base, payload, etag: responseEtag };
            } catch (error) {
              if (error && error.fromFutureServer && error.status >= 400 && error.status < 500) {
                throw error;
              }
              errors.push(`${base} attempt ${attempt}: ${error && error.message ? error.message : error}`);
              if (attempt < retryCount) {
                await new Promise((resolve) => window.setTimeout(resolve, 700 * attempt));
              }
            }
          }
        }
        throw new Error(`Khong ket noi duoc ${authJsonLabelForPath(path)}. Da thu: ${errors.join(" | ")}`);
      };

      let futureFrontendReloadToken = "";
      let futureFrontendReloading = false;
      let futureFrontendVersionPollInFlight = false;
      const FUTURE_AUDIO_CACHE_CLEAR_TOKEN_KEY = "future_audio_cache_clear_token";
      // Added 2026-07-31: gives local and server-broadcast audio clears one shared animated confirmation.
      const showFutureAudioCacheClearNotice = (result = {}, source = "local") => {
        const existing = document.getElementById("future-audio-cache-notice");
        if (existing) existing.remove();
        const notice = document.createElement("div");
        notice.id = "future-audio-cache-notice";
        notice.className = `future-audio-cache-notice${result && result.ok === false ? " is-warning" : ""}`;
        const activeReload = result && result.active_reload && result.active_reload.active;
        const detail = activeReload
          ? `Space_V audio reloaded from Continue position ${Math.max(1, Number(result.active_reload.startIndex || 0) + 1)}.`
          : (source === "server" ? "Server command applied on this device." : "Fresh audio will cache again when learning resumes.");
        notice.innerHTML = `<span class="future-audio-cache-notice-orb" aria-hidden="true"></span><span><b>${result && result.ok === false ? "Audio cache needs another tab" : "Audio cache cleared"}</b><small>${detail}</small></span>`;
        document.body.append(notice);
        window.requestAnimationFrame(() => notice.classList.add("is-visible"));
        window.setTimeout(() => {
          notice.classList.remove("is-visible");
          window.setTimeout(() => notice.remove(), 320);
        }, 3600);
      };
      const showFutureServerUpdateNotice = (payload = {}) => {
        const existing = document.querySelector(".future-update-notice-overlay");
        if (existing) {
          return existing;
        }
        const overlay = document.createElement("div");
        overlay.className = "future-update-notice-overlay";
        overlay.setAttribute("role", "status");
        overlay.setAttribute("aria-live", "assertive");

        const panel = document.createElement("div");
        panel.className = "future-update-notice-panel";

        const signal = document.createElement("div");
        signal.className = "future-update-notice-signal";
        signal.setAttribute("aria-hidden", "true");

        const copy = document.createElement("div");
        copy.className = "future-update-notice-copy";

        const title = document.createElement("div");
        title.className = "future-update-notice-title";
        title.textContent = "Đang đồng bộ phiên bản mới";

        const message = document.createElement("div");
        message.className = "future-update-notice-message";
        message.textContent = "Máy chủ vừa gửi yêu cầu cập nhật. Ứng dụng sẽ tự làm mới trong vài giây để áp dụng phiên bản ổn định nhất.";

        const meta = document.createElement("div");
        meta.className = "future-update-notice-meta";
        meta.textContent = clean(payload.reload_reason || "") ? "Yêu cầu cập nhật từ máy chủ" : "Cập nhật theo yêu cầu từ máy chủ";

        const progress = document.createElement("div");
        progress.className = "future-update-notice-progress";
        progress.setAttribute("aria-hidden", "true");
        const bar = document.createElement("span");
        progress.append(bar);

        copy.append(title, message, meta, progress);
        panel.append(signal, copy);
        overlay.append(panel);
        document.body.append(overlay);
        window.requestAnimationFrame(() => overlay.classList.add("is-visible"));
        return overlay;
      };
      const pollFutureFrontendVersion = async () => {
        if (futureFrontendReloading || futureFrontendVersionPollInFlight) {
          return;
        }
        futureFrontendVersionPollInFlight = true;
        try {
          const response = await fetch(`/frontend-version?ts=${Date.now()}`, {
            cache: "no-store",
            credentials: "same-origin",
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok || !payload || payload.ok === false) {
            return;
          }
          // Prefer the actual delivered asset version for normal updates. The
          // dashboard reload token is a separate command channel and may stay
          // unchanged while future.js/future.css are rebuilt.
          const versionToken = clean(payload.version || payload.etag || "");
          const controlToken = clean(payload.reload_token || "");
          const serverAudioEpoch = Math.max(0, Number(payload.global_audio_cache_epoch || 0) || 0);
          let audioEpochResult = null;
          if (serverAudioEpoch && window.__futureAudioCacheManager && typeof window.__futureAudioCacheManager.syncEpoch === "function") {
            audioEpochResult = await window.__futureAudioCacheManager.syncEpoch(serverAudioEpoch, { reloadActive: true });
            if (audioEpochResult && audioEpochResult.changed) {
              showFutureAudioCacheClearNotice(audioEpochResult, "server");
            }
          }
          const token = versionToken || controlToken;
          if (!token) {
            return;
          }
          if (!futureFrontendReloadToken) {
            futureFrontendReloadToken = token;
          }
          const command = clean(payload.reload_command || "").toLowerCase();
          if (command === "clear-audio-cache") {
            futureFrontendReloadToken = controlToken || token;
            let processedToken = "";
            try { processedToken = clean(localStorage.getItem(FUTURE_AUDIO_CACHE_CLEAR_TOKEN_KEY) || ""); } catch (error) {}
            if (processedToken !== (controlToken || token)) {
              try { localStorage.setItem(FUTURE_AUDIO_CACHE_CLEAR_TOKEN_KEY, controlToken || token); } catch (error) {}
            }
            return;
          }
          if (token !== futureFrontendReloadToken) {
            futureFrontendReloading = true;
            try {
              sessionStorage.setItem("future-client-reloaded-at", String(Date.now()));
            } catch (error) {
            }
            showFutureServerUpdateNotice(payload);
            window.setTimeout(() => {
              window.location.reload();
            }, 5000);
          }
        } catch (error) {
        } finally {
          futureFrontendVersionPollInFlight = false;
        }
      };
      window.setTimeout(() => {
        void pollFutureFrontendVersion();
        window.setInterval(() => void pollFutureFrontendVersion(), document.hidden ? 60000 : 30000);
      }, 3500);

      const fetchAuthForm = async (path, formData, timeoutMs = 12000) => {
        const errors = [];
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        for (const base of candidates) {
          try {
            const headers = await antiRobotHeaders(base, {});
            if (!authToken) {
              authToken = getStoredAuthToken();
            }
            if (authToken) {
              headers.Authorization = `Bearer ${authToken}`;
            }
            const completionTraceId = clean(window.__ftCompletionTraceId || "");
            if (completionTraceId && Number(window.__ftCompletionTraceUntil || 0) > Date.now()) {
              headers["X-Future-Completion-Trace"] = completionTraceId;
            }
            const response = await fetchWithTimeout(`${base}${path}`, {
              method: "POST",
              headers,
              body: formData,
              mode: "cors",
              cache: "no-store",
            }, timeoutMs);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.ok === false) {
              const finalReason = clean(payload.reason || payload.code || "").toLowerCase();
              const finalMessage = response.status === 401 && authToken && isAuthSessionFailureReason(finalReason)
                ? invalidateAuthSession(finalReason)
                : (clean(payload.error) || `May chu bao loi ${response.status}.`);
              const error = new Error(finalMessage);
              error.status = response.status;
              error.reason = finalReason;
              error.fromFutureServer = payload && payload.ok === false;
              throw error;
            }
            return { base, payload };
          } catch (error) {
            if (error && error.fromFutureServer && error.status >= 400 && error.status < 500) {
              throw error;
            }
            errors.push(`${base}: ${error && error.message ? error.message : error}`);
          }
        }
        throw new Error(`Khong upload duoc tep. Da thu: ${errors.join(" | ")}`);
      };

      const setLearnerChatStatus = (message, tone = "") => {
        if (!chatStatus) {
          return;
        }
        chatStatus.textContent = message || "";
        chatStatus.classList.toggle("is-error", tone === "error");
      };

      const updateLearnerChatBadge = () => {
        const count = Math.max(0, Number(learnerChatUnread || 0));
        if (chatDot) {
          chatDot.textContent = count > 99 ? "99+" : String(count);
        }
        if (chatButton) {
          chatButton.classList.toggle("has-unread", count > 0);
        }
      };

      const learnerChatAudioPath = (item = {}) => clean(
        item.audio_path ||
        (item.audio && (item.audio.path || item.audio.url)) ||
        item.audio_url ||
        ""
      );

      const learnerChatAudioSrc = (item = {}) => {
        const path = learnerChatAudioPath(item);
        if (!path) {
          return "";
        }
        return resolveServerAssetUrl(path);
      };

      const learnerChatAttachments = (item = {}) => {
        const rows = Array.isArray(item.attachments) ? [...item.attachments] : [];
        if (item.attachment && typeof item.attachment === "object") {
          rows.push(item.attachment);
        }
        return rows.filter((row) => row && (row.path || row.url));
      };

      const chatAttachmentUrl = (attachment = {}, download = false) => {
        let raw = download
          ? attachment.download_url || attachment.downloadUrl || attachment.url || ""
          : attachment.url || "";
        if (!raw && attachment.path) {
          raw = `/chat/attachment?path=${encodeURIComponent(attachment.path)}${download ? "&download=1" : ""}`;
        }
        return resolveServerAssetUrl(raw);
      };

      const formatChatAttachmentSize = (size) => {
        const value = Number(size || 0);
        if (!value) {
          return "";
        }
        if (value >= 1024 * 1024) {
          return `${(value / (1024 * 1024)).toFixed(value >= 10 * 1024 * 1024 ? 0 : 1)} MB`;
        }
        if (value >= 1024) {
          return `${Math.round(value / 1024)} KB`;
        }
        return `${value} B`;
      };

      const applyChatImageViewerTransform = () => {
        if (!imageViewerImg) {
          return;
        }
        imageViewerImg.style.transform = `translate(${chatImageViewerState.x}px, ${chatImageViewerState.y}px) scale(${chatImageViewerState.zoom})`;
        if (imageViewerZoomReset) {
          imageViewerZoomReset.textContent = `${Math.round(chatImageViewerState.zoom * 100)}%`;
        }
      };

      const resetChatImageViewerTransform = () => {
        chatImageViewerState.zoom = 1;
        chatImageViewerState.x = 0;
        chatImageViewerState.y = 0;
        chatImageViewerState.dragging = false;
        if (imageViewerImg) {
          imageViewerImg.classList.remove("is-dragging");
        }
        applyChatImageViewerTransform();
      };

      const setChatImageViewerZoom = (zoom) => {
        chatImageViewerState.zoom = Math.max(0.25, Math.min(6, Number(zoom) || 1));
        applyChatImageViewerTransform();
      };

      const openChatImageViewer = (src, downloadSrc = "", name = "") => {
        if (!imageViewer || !imageViewerImg) {
          window.open(src, "_blank", "noopener");
          return;
        }
        resetChatImageViewerTransform();
        imageViewerImg.src = src;
        imageViewerImg.alt = name || "Chat image";
        if (imageViewerDownload) {
          imageViewerDownload.href = downloadSrc || src;
          imageViewerDownload.setAttribute("download", name || "chat-image");
        }
        imageViewer.classList.add("is-open");
        imageViewer.setAttribute("aria-hidden", "false");
      };

      const closeChatImageViewer = () => {
        if (!imageViewer) {
          return;
        }
        resetChatImageViewerTransform();
        imageViewer.classList.remove("is-open");
        imageViewer.setAttribute("aria-hidden", "true");
        if (imageViewerImg) {
          imageViewerImg.removeAttribute("src");
        }
      };

      const beginChatImageViewerDrag = (event) => {
        if (!imageViewerImg || !imageViewer || !imageViewer.classList.contains("is-open")) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        chatImageViewerState.dragging = true;
        chatImageViewerState.pointerId = event.pointerId;
        chatImageViewerState.startX = event.clientX;
        chatImageViewerState.startY = event.clientY;
        chatImageViewerState.originX = chatImageViewerState.x;
        chatImageViewerState.originY = chatImageViewerState.y;
        imageViewerImg.classList.add("is-dragging");
        try {
          imageViewerImg.setPointerCapture(event.pointerId);
        } catch (error) {}
      };

      const moveChatImageViewerDrag = (event) => {
        if (!chatImageViewerState.dragging) {
          return;
        }
        event.preventDefault();
        chatImageViewerState.x = chatImageViewerState.originX + event.clientX - chatImageViewerState.startX;
        chatImageViewerState.y = chatImageViewerState.originY + event.clientY - chatImageViewerState.startY;
        applyChatImageViewerTransform();
      };

      const endChatImageViewerDrag = (event) => {
        if (!chatImageViewerState.dragging) {
          return;
        }
        chatImageViewerState.dragging = false;
        if (imageViewerImg) {
          imageViewerImg.classList.remove("is-dragging");
          try {
            imageViewerImg.releasePointerCapture(event.pointerId);
          } catch (error) {}
        }
      };

      const scrollLearnerChatToBottom = () => {
        if (!chatLog) {
          return;
        }
        const apply = () => {
          chatLog.scrollTop = chatLog.scrollHeight;
        };
        apply();
        window.requestAnimationFrame(apply);
        window.setTimeout(apply, 80);
        window.setTimeout(apply, 260);
      };

      const renderLearnerChatAttachments = (message, item = {}, scrollOnImageLoad = false) => {
        const attachments = learnerChatAttachments(item);
        if (!attachments.length) {
          return;
        }
        const wrap = document.createElement("div");
        wrap.className = "ft-chat-attachments";
        attachments.forEach((attachment) => {
          const name = clean(attachment.name || "attachment") || "attachment";
          const src = chatAttachmentUrl(attachment);
          const downloadSrc = chatAttachmentUrl(attachment, true) || src;
          const mime = clean(attachment.mime || "");
          const isImage = clean(attachment.kind || "").toLowerCase() === "image" || mime.startsWith("image/");
          const isAudio = clean(attachment.kind || "").toLowerCase() === "audio" || mime.startsWith("audio/");
          if (isImage) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "ft-chat-thumb";
            button.title = name;
            const img = document.createElement("img");
            if (scrollOnImageLoad) {
              img.addEventListener("load", scrollLearnerChatToBottom, { once: true });
            }
            img.src = src;
            img.alt = name;
            button.appendChild(img);
            button.addEventListener("click", (event) => {
              event.stopPropagation();
              openChatImageViewer(src, downloadSrc, name);
            });
            wrap.appendChild(button);
          } else if (isAudio) {
            const audioWrap = document.createElement("div");
            audioWrap.className = "ft-chat-audio-clip";
            const audio = document.createElement("audio");
            audio.controls = true;
            audio.preload = "metadata";
            audio.src = src;
            const link = document.createElement("a");
            link.className = "ft-chat-audio-download";
            link.href = downloadSrc;
            link.download = name;
            link.target = "_blank";
            link.rel = "noopener";
            const size = formatChatAttachmentSize(attachment.size);
            link.textContent = size ? `${name} | ${size}` : name;
            audioWrap.append(audio, link);
            wrap.appendChild(audioWrap);
          } else {
            const link = document.createElement("a");
            link.className = "ft-chat-file";
            link.href = downloadSrc;
            link.download = name;
            link.target = "_blank";
            link.rel = "noopener";
            const size = formatChatAttachmentSize(attachment.size);
            link.textContent = size ? `${name} | ${size}` : name;
            wrap.appendChild(link);
          }
        });
        message.appendChild(wrap);
      };

      const playLearnerChatAudio = (item = {}, force = false) => {
        const id = Number(item.id || 0);
        if (!force && id && learnerChatPlayedAudioIds.has(id)) {
          return;
        }
        const src = learnerChatAudioSrc(item);
        if (!src) {
          return;
        }
        const audio = new Audio(src);
        audio.play()
          .then(() => {
            if (id) {
              learnerChatPlayedAudioIds.add(id);
            }
          })
          .catch(() => {});
      };

      const playLatestLearnerChatAudio = () => {
        if (!learnerChatOpen) {
          return;
        }
        const item = [...learnerChatMessages]
          .reverse()
          .find((row) => row && row.sender === "admin" && learnerChatAudioPath(row) && !learnerChatPlayedAudioIds.has(Number(row.id || 0)));
        if (item) {
          playLearnerChatAudio(item);
        }
      };

      const playNewLearnerChatAudio = (items = []) => {
        if (!learnerChatOpen) {
          return;
        }
        const rows = Array.isArray(items) ? items : [];
        const item = [...rows]
          .reverse()
          .find((row) => row && row.sender === "admin" && learnerChatAudioPath(row) && !learnerChatPlayedAudioIds.has(Number(row.id || 0)));
        if (item) {
          playLearnerChatAudio(item);
        }
      };

      const renderLearnerChatMessages = (options = {}) => {
        if (!chatLog) {
          return;
        }
        const shouldScroll = Boolean(options && options.scroll);
        chatLog.textContent = "";
        if (!learnerChatMessages.length) {
          const empty = document.createElement("div");
          empty.className = "ft-chat-msg";
          empty.textContent = "No messages yet.";
          chatLog.appendChild(empty);
          return;
        }
        learnerChatMessages.forEach((item) => {
          const message = document.createElement("div");
          const audioPath = learnerChatAudioPath(item);
          message.className = "ft-chat-msg" + (item.sender === "user" ? " is-me" : "") + (audioPath ? " has-audio" : "");
          const text = document.createElement("div");
          text.className = "ft-chat-text";
          text.textContent = item.text || "";
          if (item.text) {
            message.appendChild(text);
          }
          renderLearnerChatAttachments(message, item, shouldScroll);
          if (item.audio_error) {
            const audioError = document.createElement("div");
            audioError.className = "ft-chat-audio-error";
            audioError.textContent = `Voice error: ${clean(item.audio_error)}`;
            message.appendChild(audioError);
          }
          if (!message.childNodes.length) {
            message.textContent = "Attachment";
          }
          if (item.sender === "user") {
            const readState = document.createElement("div");
            readState.className = "ft-chat-read-state";
            readState.textContent = item.peer_read ? "Seen" : "Sent";
            message.appendChild(readState);
          }
          if (audioPath) {
            message.title = "Click to play voice";
            message.addEventListener("click", () => playLearnerChatAudio(item, true));
          }
          chatLog.appendChild(message);
        });
        if (shouldScroll) {
          scrollLearnerChatToBottom();
        }
      };

      const appendLearnerChatMessages = (items) => {
        const rows = Array.isArray(items) ? items : [];
        if (!rows.length) {
          return false;
        }
        const known = new Set(learnerChatMessages.map((item) => Number(item.id || 0)));
        let changed = false;
        const added = [];
        rows.forEach((item) => {
          const id = Number(item && item.id || 0);
          if (!id || known.has(id)) {
            return;
          }
          known.add(id);
          learnerChatMessages.push(item);
          added.push(item);
          learnerChatLastId = Math.max(learnerChatLastId, id);
          changed = true;
        });
        if (changed) {
          learnerChatMessages.sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
          renderLearnerChatMessages({ scroll: true });
          playNewLearnerChatAudio(added);
        }
        return changed;
      };

      const updateLearnerChatReadMarkers = (read = {}) => {
        const adminRead = Number(read.admin_read || read.adminRead || 0);
        if (!adminRead) {
          return false;
        }
        let changed = false;
        learnerChatMessages.forEach((item) => {
          if (!item || item.sender !== "user") {
            return;
          }
          const nextRead = Number(item.id || 0) <= adminRead;
          if (Boolean(item.peer_read) !== nextRead) {
            item.peer_read = nextRead;
            item.read_state = nextRead ? "seen" : "sent";
            changed = true;
          }
        });
        return changed;
      };

      const pollLearnerChat = async () => {
        if (!authToken || !learnerChatOpen || learnerChatPollInFlight) {
          return;
        }
        learnerChatPollInFlight = true;
        try {
          const openFlag = learnerChatOpen ? "1" : "0";
          const noticeAfter = Math.max(0, Number(taskNoticeImmediateLastId || 0) || 0);
          const result = await fetchAuthJson(`/chat/poll?since=${encodeURIComponent(String(learnerChatLastId))}&open=${openFlag}&notice_after=${encodeURIComponent(String(noticeAfter))}`);
          const payload = result.payload || {};
          const appended = appendLearnerChatMessages(payload.messages || []);
          consumeTaskNoticeImmediatePayload(payload);
          const readChanged = updateLearnerChatReadMarkers(payload.read || {});
          if (readChanged) {
            renderLearnerChatMessages();
          }
          learnerChatUnread = learnerChatOpen ? 0 : Number(payload.unread || 0);
          updateLearnerChatBadge();
          if (learnerChatOpen) {
            setLearnerChatStatus("");
          }
        } catch (error) {
          if (learnerChatOpen) {
            setLearnerChatStatus(error && error.message ? error.message : "Chat server is unavailable.", "error");
          }
        } finally {
          learnerChatPollInFlight = false;
        }
      };

      const stopLearnerChatPolling = () => {
        if (learnerChatPollTimer) {
          window.clearTimeout(learnerChatPollTimer);
          learnerChatPollTimer = 0;
        }
      };

      const learnerChatPollDelay = () => {
        const base = learnerChatOpen ? LEARNER_CHAT_POLL_OPEN_MS : LEARNER_CHAT_POLL_IDLE_MS;
        return learnerChatOpen ? base : serverWorkspacePollDelay(base);
      };

      const scheduleLearnerChatPolling = (delayMs = learnerChatPollDelay()) => {
        stopLearnerChatPolling();
        if (!authToken || !learnerChatOpen) {
          return;
        }
        learnerChatPollTimer = window.setTimeout(async () => {
          learnerChatPollTimer = 0;
          await pollLearnerChat();
          if (learnerChatOpen) {
            scheduleLearnerChatPolling();
          }
        }, Math.max(1000, Number(delayMs) || learnerChatPollDelay()));
      };

      const startLearnerChatPolling = () => {
        stopLearnerChatPolling();
        if (!authToken || !learnerChatOpen) {
          return;
        }
        void pollLearnerChat();
        scheduleLearnerChatPolling();
      };

      let speakSkipAdminRows = [];

      function setSpeakSkipAdminStatus(message = "", kind = "") {
        if (!speakSkipAdminStatus) {
          return;
        }
        speakSkipAdminStatus.textContent = message || "";
        speakSkipAdminStatus.classList.toggle("is-error", kind === "error");
        speakSkipAdminStatus.classList.toggle("is-ok", kind === "ok");
      }

      function closeSpeakSkipAdminModal() {
        if (!speakSkipAdminModal) {
          return;
        }
        speakSkipAdminModal.classList.remove("is-open");
        speakSkipAdminModal.setAttribute("aria-hidden", "true");
      }

      function formatSpeakSkipTime(value = "") {
        const text = clean(value);
        if (!text) {
          return "";
        }
        const parsed = new Date(text);
        if (Number.isNaN(parsed.getTime())) {
          return text.replace("T", " ").slice(0, 19);
        }
        try {
          return parsed.toLocaleString();
        } catch (error) {
          return text.replace("T", " ").slice(0, 19);
        }
      }

      function renderSpeakSkipAdminRequests(rows = []) {
        if (!speakSkipAdminList) {
          return;
        }
        speakSkipAdminList.replaceChildren();
        const pending = Array.isArray(rows) ? rows.filter((row) => clean(row && row.status).toLowerCase() === "pending") : [];
        if (speakSkipAdminAcceptAll) {
          speakSkipAdminAcceptAll.disabled = !pending.length;
        }
        if (!pending.length) {
          const empty = document.createElement("div");
          empty.className = "ft-speak-admin-empty";
          empty.textContent = "No pending Speak skip requests.";
          speakSkipAdminList.appendChild(empty);
          return;
        }
        pending.forEach((row) => {
          const item = document.createElement("article");
          item.className = "ft-speak-admin-item";
          const main = document.createElement("div");
          main.className = "ft-speak-admin-item-main";
          const title = document.createElement("div");
          title.className = "ft-speak-admin-item-title";
          const nodeNumber = Math.max(1, Number(row.nodeIndex ?? row.node_index ?? 0) + 1 || 1);
          title.textContent = `${clean(row.username || "user")} · Node ${nodeNumber}`;
          const meta = document.createElement("div");
          meta.className = "ft-speak-admin-item-meta";
          const parts = [
            clean(row.title || "Space_W"),
            formatSpeakSkipTime(row.updatedAt || row.createdAt),
          ].filter(Boolean);
          meta.textContent = parts.join(" · ");
          const expected = document.createElement("div");
          expected.className = "ft-speak-admin-item-text";
          expected.textContent = clean(row.expected || row.reason || "Learner reported a Speak scoring error.");
          main.append(title, meta, expected);

          const actions = document.createElement("div");
          actions.className = "ft-speak-admin-item-actions";
          const accept = document.createElement("button");
          accept.className = "is-accept";
          accept.type = "button";
          accept.textContent = "Accept";
          accept.addEventListener("click", () => {
            void respondSpeakSkipAdmin({ id: row.id, username: row.username });
          });
          const acceptUser = document.createElement("button");
          acceptUser.type = "button";
          acceptUser.textContent = "Accept user";
          acceptUser.addEventListener("click", () => {
            void respondSpeakSkipAdmin({ username: row.username, all: true });
          });
          actions.append(accept, acceptUser);
          item.append(main, actions);
          speakSkipAdminList.appendChild(item);
        });
      }

      async function loadSpeakSkipAdminRequests() {
        if (!currentAuthIsAdmin) {
          setSpeakSkipAdminStatus("Only admin users can review Speak requests.", "error");
          renderSpeakSkipAdminRequests([]);
          return;
        }
        setSpeakSkipAdminStatus("Loading requests...");
        try {
          const result = await fetchAuthJson("/space-w/speak-skip/list?status=pending");
          speakSkipAdminRows = Array.isArray(result && result.payload && result.payload.requests) ? result.payload.requests : [];
          renderSpeakSkipAdminRequests(speakSkipAdminRows);
          const count = speakSkipAdminRows.filter((row) => clean(row && row.status).toLowerCase() === "pending").length;
          setSpeakSkipAdminStatus(count ? `${count} pending request${count === 1 ? "" : "s"}.` : "All Speak requests are clear.", count ? "" : "ok");
        } catch (error) {
          renderSpeakSkipAdminRequests([]);
          setSpeakSkipAdminStatus(`Could not load Speak requests: ${error && error.message ? error.message : error}`, "error");
        }
      }

      async function openSpeakSkipAdminModal() {
        if (!speakSkipAdminModal || !currentAuthIsAdmin) {
          return;
        }
        speakSkipAdminModal.classList.add("is-open");
        speakSkipAdminModal.setAttribute("aria-hidden", "false");
        await loadSpeakSkipAdminRequests();
      }

      async function respondSpeakSkipAdmin(options = {}) {
        if (!currentAuthIsAdmin) {
          setSpeakSkipAdminStatus("Only admin users can approve Speak skip requests.", "error");
          return;
        }
        const payload = {
          id: clean(options.id || ""),
          username: clean(options.username || ""),
          all: Boolean(options.all),
          action: clean(options.action || "accept") || "accept",
        };
        setSpeakSkipAdminStatus(payload.all ? "Accepting selected requests..." : "Accepting request...");
        try {
          await fetchAuthJson("/space-w/speak-skip/respond", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setSpeakSkipAdminStatus("Speak skip approved. The learner can continue this file.", "ok");
          await loadSpeakSkipAdminRequests();
        } catch (error) {
          setSpeakSkipAdminStatus(`Could not approve request: ${error && error.message ? error.message : error}`, "error");
        }
      }

      function setAiAgentStatus(message = "", isError = false) {
        if (!aiAgentStatus) {
          return;
        }
        aiAgentStatus.textContent = clean(message) || "Ghost AI answer, bilingual panels, Michael voice.";
        aiAgentStatus.classList.toggle("is-error", Boolean(isError));
      }

      function formatAiAgentThinkingElapsed(ms = 0) {
        const totalSeconds = Math.max(0, Math.floor((Number(ms) || 0) / 1000));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
      }

      function updateAiAgentThinkingTime() {
        if (!aiAgentThinkingTime || !aiAgentThinkingStartedAt) {
          return;
        }
        aiAgentThinkingTime.textContent = formatAiAgentThinkingElapsed(Date.now() - aiAgentThinkingStartedAt);
      }

      function setAiAgentThinking(active = false) {
        const enabled = Boolean(active);
        if (aiAgentThinkingTimer) {
          window.clearInterval(aiAgentThinkingTimer);
          aiAgentThinkingTimer = 0;
        }
        if (enabled) {
          aiAgentThinkingStartedAt = Date.now();
          if (aiAgentThinkingTime) {
            aiAgentThinkingTime.textContent = "00:00";
          }
          updateAiAgentThinkingTime();
          aiAgentThinkingTimer = window.setInterval(updateAiAgentThinkingTime, 250);
        } else {
          aiAgentThinkingStartedAt = 0;
          if (aiAgentThinkingTime) {
            aiAgentThinkingTime.textContent = "00:00";
          }
        }
        if (aiAgentPopup) {
          aiAgentPopup.classList.toggle("is-thinking", enabled);
        }
        if (aiAgentThinking) {
          aiAgentThinking.setAttribute("aria-hidden", enabled ? "false" : "true");
        }
      }

      function renderAiAgentSuggestion() {
        const questionText = preserveQuestionText(aiAgentPendingSuggestion && (
          aiAgentPendingSuggestion.question_vi
          || aiAgentPendingSuggestion.question
          || aiAgentPendingSuggestion.text
        ) || "");
        if (aiAgentSuggestionText) {
          aiAgentSuggestionText.textContent = questionText;
        }
        if (aiAgentSuggestion) {
          aiAgentSuggestion.classList.toggle("is-hidden", !questionText);
          aiAgentSuggestion.setAttribute("aria-hidden", questionText ? "false" : "true");
        }
        if (aiAgentButton) {
          aiAgentButton.classList.toggle("has-ai-suggestion", Boolean(questionText && !aiAgentSuggestionAcknowledged));
        }
      }

      function setAiAgentSuggestion(suggestion = null) {
        aiAgentPendingSuggestion = suggestion && typeof suggestion === "object" ? suggestion : null;
        aiAgentSuggestionAcknowledged = false;
        renderAiAgentSuggestion();
        if (aiAgentSuggestionPulseTimer) {
          window.clearTimeout(aiAgentSuggestionPulseTimer);
          aiAgentSuggestionPulseTimer = 0;
        }
        if (aiAgentButton && aiAgentPendingSuggestion) {
          aiAgentButton.classList.remove("is-suggestion-pulse");
          void aiAgentButton.offsetWidth;
          aiAgentButton.classList.add("is-suggestion-pulse");
          aiAgentSuggestionPulseTimer = window.setTimeout(() => {
            aiAgentSuggestionPulseTimer = 0;
            aiAgentButton.classList.remove("is-suggestion-pulse");
          }, 3700);
        }
      }

      function clearAiAgentSuggestion() {
        aiAgentSuggestionAcknowledged = false;
        setAiAgentSuggestion(null);
      }

      function useAiAgentSuggestion() {
        const questionText = preserveQuestionText(aiAgentPendingSuggestion && (
          aiAgentPendingSuggestion.question_vi
          || aiAgentPendingSuggestion.question
          || aiAgentPendingSuggestion.text
        ) || "");
        if (!questionText) {
          return;
        }
        setAiAgentMode("detailed");
        const suggestionForRequest = aiAgentPendingSuggestion && typeof aiAgentPendingSuggestion === "object"
          ? aiAgentPendingSuggestion
          : null;
        void submitAiAgentQuestion({
          message: questionText,
          clearInput: false,
          skipSuggestion: true,
          contextPatch: {
            kind: "space_p_auto_hint_followup_direct",
            question_vi: questionText,
            source: suggestionForRequest && suggestionForRequest.context || {},
          },
          autoSaveTitle: "Space_P follow-up",
        });
        clearAiAgentSuggestion();
      }

      function renderAiAgentVocabQuick() {
        if (!aiAgentVocabQuick) {
          return;
        }
        const visible = aiAgentCurrentSpaceName() === "space_v";
        aiAgentVocabQuick.classList.toggle("is-hidden", !visible);
        aiAgentVocabQuick.setAttribute("aria-hidden", visible ? "false" : "true");
      }

      function paragraphAiHintedWordEntries() {
        if (aiAgentCurrentSpaceName() !== "space_p") {
          return [];
        }
        try {
          const node = typeof currentParagraphNode === "function" ? currentParagraphNode() : null;
          const children = node && Array.isArray(node.children) ? node.children : [];
          if (!children.length || !paragraphHints || typeof paragraphHints.has !== "function") {
            return [];
          }
          const entries = [];
          const minChildIndex = Math.max(0, Math.floor(Number(paragraphChildIndex || 0) || 0) - 1);
          const maxChildIndex = Math.max(0, Math.floor(Number(paragraphChildIndex || 0) || 0));
          children.forEach((child, childIndex) => {
            if (childIndex < minChildIndex || childIndex > maxChildIndex) {
              return;
            }
            const segmentText = preserveQuestionText(child && child.text || "");
            const meaning = preserveQuestionText(child && (child.meaning || child.vi || child.vietnamese || child.translation) || "");
            paragraphWordParts(segmentText).forEach((part, wordIndex) => {
              if (!paragraphHints.has(paragraphHintKeyFor(wordIndex, childIndex))) {
                return;
              }
              const word = paragraphWordSurface(part.word || "") || paragraphWordKey(part.word || "");
              if (!word) {
                return;
              }
              entries.push({
                id: `${paragraphNodeIndex}:${childIndex}:${wordIndex}`,
                word,
                childIndex,
                wordIndex,
                segmentText,
                meaning,
                nodeTitle: preserveQuestionText(node.title || `Paragraph Node ${paragraphNodeIndex + 1}`),
                isCurrent: childIndex === paragraphChildIndex,
              });
            });
          });
          entries.sort((a, b) => {
            if (a.isCurrent !== b.isCurrent) return a.isCurrent ? -1 : 1;
            if (a.childIndex !== b.childIndex) return a.childIndex - b.childIndex;
            return a.wordIndex - b.wordIndex;
          });
          return entries.slice(0, 80);
        } catch (error) {
          return [];
        }
      }

      function renderAiAgentParagraphQuick() {
        if (!aiAgentParagraphQuick || !aiAgentParagraphQuickList) {
          return;
        }
        const entries = paragraphAiHintedWordEntries();
        const visible = aiAgentCurrentSpaceName() === "space_p" && entries.length > 0;
        aiAgentParagraphQuick.classList.toggle("is-hidden", !visible);
        aiAgentParagraphQuick.setAttribute("aria-hidden", visible ? "false" : "true");
        aiAgentParagraphQuickList.textContent = "";
        if (!visible) {
          return;
        }
        entries.forEach((entry) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "ft-ai-agent-paragraph-quick-button";
          button.dataset.paragraphHintId = entry.id;
          const word = document.createElement("span");
          word.className = "ft-ai-agent-paragraph-quick-word";
          word.textContent = entry.word;
          const meta = document.createElement("span");
          meta.className = "ft-ai-agent-paragraph-quick-meta";
          meta.textContent = `S${entry.childIndex + 1} · W${entry.wordIndex + 1}`;
          button.append(word, meta);
          button.addEventListener("click", () => {
            void runAiAgentParagraphQuick(entry);
          });
          aiAgentParagraphQuickList.appendChild(button);
        });
      }

      function buildAiAgentParagraphQuickPrompt(entry = {}) {
        const word = preserveQuestionText(entry.word || "this hinted word");
        const details = [
          entry.nodeTitle ? `Paragraph node: ${entry.nodeTitle}` : "",
          entry.meaning ? `Vietnamese prompt for this segment: ${entry.meaning}` : "",
          Number.isFinite(Number(entry.childIndex)) ? `Segment number: ${Number(entry.childIndex) + 1}` : "",
          `Hinted word already revealed to learner: ${word}`,
        ].filter(Boolean).join("\n");
        return [
          `For Space_P, explain why I may have needed an auto hint for the word "${word}".`,
          details,
          "The hinted word is already visible, so you may discuss that word directly. Do not reveal any other unrevealed Space_P words or complete future locked text.",
          "Explain the meaning in context, grammar role, word order or collocation reason, and give one short similar example.",
        ].filter(Boolean).join("\n");
      }

      async function runAiAgentParagraphQuick(entry = {}) {
        if (aiAgentCurrentSpaceName() !== "space_p") {
          setAiAgentStatus("Space_P hinted-word asks are available while rewriting paragraphs.", true);
          return;
        }
        setAiAgentMode("detailed");
        const contextPatch = {
          kind: "space_p_hinted_word_quick_ask",
          hinted_word: preserveQuestionText(entry.word || ""),
          child_index: entry.childIndex,
          word_index: entry.wordIndex,
          vietnamese_prompt: preserveQuestionText(entry.meaning || ""),
          node_title: preserveQuestionText(entry.nodeTitle || ""),
        };
        await submitAiAgentQuestion({
          message: buildAiAgentParagraphQuickPrompt(entry),
          contextPatch,
          autoSaveTitle: contextPatch.hinted_word || "Space_P hinted word",
          clearInput: false,
        });
      }

      function currentAiAgentVocabLabel(runtime = {}) {
        const word = preserveQuestionText(runtime.current_vocabulary_word || "");
        if (word) {
          return `the word "${word}"`;
        }
        return "the current Space_V vocabulary item";
      }

      function buildAiAgentVocabQuickPrompt(kind = "usage") {
        const context = aiAgentContextPayload();
        const runtime = context && context.runtime && typeof context.runtime === "object" ? context.runtime : {};
        const target = currentAiAgentVocabLabel(runtime);
        const meaning = preserveQuestionText(runtime.meaning_prompt || "");
        const pos = preserveQuestionText(runtime.part_of_speech || "");
        const details = [
          meaning ? `Vietnamese meaning shown to learner: ${meaning}` : "",
          pos ? `Part of speech: ${pos}` : "",
          runtime.phase ? `Space_V phase: ${runtime.phase}` : "",
        ].filter(Boolean).join("\n");
        if (clean(kind).toLowerCase() === "context") {
          return [
            `For Space_V, explain in what real-life contexts I can use ${target}.`,
            details,
            "Give practical situations, 3 short examples, and one warning about common misuse. Answer clearly in English and Vietnamese.",
          ].filter(Boolean).join("\n");
        }
        return [
          `For Space_V, explain how to use ${target} correctly.`,
          details,
          "Explain grammar pattern, collocations, pronunciation or spelling note if useful, then give 3 short learner-friendly examples. Answer clearly in English and Vietnamese.",
        ].filter(Boolean).join("\n");
      }

