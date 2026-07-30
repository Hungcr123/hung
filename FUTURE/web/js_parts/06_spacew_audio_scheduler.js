
      const spaceWDesktopMotionSurface = () => Boolean(
        !mobileStaticMotionSurface() &&
        !questionModeActive &&
        !vocabModeActive &&
        cardNode &&
        !cardNode.classList.contains("is-hidden") &&
        authGate &&
        authGate.classList.contains("is-hidden") &&
        loadGate &&
        loadGate.classList.contains("is-hidden")
      );
      const pdfStaticMotionSurface = () => Boolean(
        typeof pdfModeActive !== "undefined" &&
        pdfModeActive &&
        document.documentElement.classList.contains("ft-space-pdf-mode")
      );
      const mobileStaticMotionActive = () => !mobileAnimationEnabled && !pdfStaticMotionSurface() && (
        mobileStaticMotionSurface() ||
        spaceWDesktopMotionSurface()
      );
      const updateMobileAnimationButton = () => {
        const enabled = Boolean(mobileAnimationEnabled);
        document.documentElement.classList.toggle("ft-lesson-vault-motion-on", enabled);
        document.documentElement.classList.toggle("ft-lesson-vault-motion-off", !enabled);
        if (!mobileAnimationButton) {
          return;
        }
        mobileAnimationButton.classList.toggle("is-active", enabled);
        mobileAnimationButton.setAttribute("aria-pressed", enabled ? "true" : "false");
        mobileAnimationButton.title = enabled ? "Animation engine online" : "Animation engine offline";
        mobileAnimationButton.setAttribute("aria-label", enabled ? "Turn learning motion off" : "Turn learning motion on");
      };
      const setMobileAnimationEnabled = (enabled, persist = true) => {
        const nextEnabled = Boolean(enabled);
        const turningOn = nextEnabled && !mobileAnimationEnabled;
        const turningOff = !nextEnabled && mobileAnimationEnabled;
        mobileAnimationEnabled = nextEnabled;
        if (persist) {
          try {
            localStorage.setItem(MOBILE_ANIMATION_STORAGE_KEY, mobileAnimationEnabled ? "1" : "0");
          } catch (error) {
          }
        }
        if (animationEngineEnableTimer) {
          window.clearTimeout(animationEngineEnableTimer);
          animationEngineEnableTimer = 0;
        }
        if (turningOn) {
          document.documentElement.classList.add("ft-animation-engine-no-entry");
          if (mobileAnimationButton) {
            mobileAnimationButton.classList.add("is-active");
            mobileAnimationButton.setAttribute("aria-pressed", "true");
            mobileAnimationButton.title = "Animation engine booting";
            mobileAnimationButton.setAttribute("aria-label", "Animation engine booting");
          }
          startAnimationEngineBootSequence();
          animationEngineEnableTimer = window.setTimeout(() => {
            animationEngineEnableTimer = 0;
            updateMobileAnimationButton();
            scheduleMobileInfiniteMotionSync();
            scheduleMobileInfiniteMotionSync(240);
            clearLearningStatsMotionCycle();
          }, 760);
          return;
        }
        if (turningOff) {
          if (animationEngineBootTimer) {
            window.clearTimeout(animationEngineBootTimer);
            animationEngineBootTimer = 0;
          }
          document.documentElement.classList.remove("ft-animation-engine-booting");
          document.documentElement.classList.remove("ft-animation-engine-no-entry");
          if (mobileAnimationButton) {
            mobileAnimationButton.classList.remove("is-booting");
          }
        }
        updateMobileAnimationButton();
        scheduleMobileInfiniteMotionSync();
        scheduleMobileInfiniteMotionSync(240);
        if (mobileAnimationEnabled) {
          clearLearningStatsMotionCycle();
        } else if (!pdfStaticMotionSurface()) {
          scheduleLearningStatsMotionCycle(1000);
        } else {
          clearLearningStatsMotionCycle();
        }
      };
      const toggleMobileAnimationEnabled = () => {
        setMobileAnimationEnabled(!mobileAnimationEnabled);
      };
      const syncVocabMobilePin = () => {
        const active = Boolean(
          mobileStaticMotionActive() &&
          vocabModeActive &&
          !questionModeActive &&
          vocabCard &&
          !vocabCard.classList.contains("is-hidden") &&
          loadGate &&
          loadGate.classList.contains("is-hidden") &&
          authGate &&
          authGate.classList.contains("is-hidden")
        );
        document.documentElement.classList.toggle("ft-vocab-mobile-pin", active);
        if (stageNode) {
          stageNode.classList.toggle("is-vocab-mobile-pin", active);
        }
        if (shellNode) {
          shellNode.classList.toggle("is-vocab-mobile-pin", active);
        }
        return active;
      };
      const mobileMotionRootFor = (source) => {
        if (!source || !source.closest) {
          return null;
        }
        return source.closest(
          ".ft-card, .ft-vocab-card, .ft-q-root-card, .ft-q-audio-card, .ft-q-picture-card, .ft-q-question-card, .ft-q-info-card, .ft-q-root-info-card, .ft-q-picture-answer-card, .ft-auth-panel, .ft-load-panel, .ft-vocab-preflight-card, .ft-space-navigator, .ft-chat-modal, .ft-paint-modal, .ft-world-modal, .ft-cup-modal, .ft-cup-reward-modal, button, input, textarea, select",
        ) || source;
      };
      const mobileAnimationTarget = (animation) => {
        const target = animation && animation.effect && animation.effect.target ? animation.effect.target : null;
        return target && target.element ? target.element : target;
      };
      const mobileAnimationIsInfinite = (animation) => {
        if (!animation || !animation.effect) {
          return false;
        }
        const timing = animation.effect.getComputedTiming ? animation.effect.getComputedTiming() : (animation.effect.getTiming ? animation.effect.getTiming() : {});
        return timing && timing.iterations === Infinity;
      };
      const mobileAnimationAllowedSelectors = [
        ".ft-mobile-motion-live",
        ".ft-speak-panel.is-recording",
        ".ft-speak-panel.is-processing",
        ".ft-speak-panel.is-playing",
        ".ft-ipa-panel.is-speaking",
        ".ft-server-browser .ft-server-item.is-selected",
        ".ft-server-browser .ft-server-learned-badge",
        ".ft-server-browser .ft-vault-progress",
        ".ft-task-modal .ft-task-card.is-pending",
        ".ft-task-modal .ft-task-card.is-overdue",
        ".ft-task-modal .ft-task-card.is-selected",
        ".ft-task-modal.is-testing-pending",
        ".ft-task-modal.is-testing-overdue",
        ".ft-pdf-space.is-rendering-page",
        ".ft-pdf-stage-loader",
        ".ft-pdf-status.is-busy",
        ".ft-pdf-button.is-busy",
        ".ft-pdf-compact-action.is-busy",
        ".ft-pdf-page-wrap.is-shift-selecting",
        ".ft-pdf-selection-point.is-visible",
        ".ft-pdf-selection.is-tech-burst",
        ".ft-pdf-selection.is-materializing",
        ".ft-pdf-selection.is-twin-building",
        ".ft-pdf-selection-svg.is-union-pulse",
        ".ft-pdf-build-point",
        ".ft-pdf-build-line",
        ".ft-pdf-navigator:hover",
        ".ft-pdf-navigator.is-active",
        ".ft-pdf-navigator.is-coasting",
        ".ft-pdf-agent-card.is-loading",
        ".ft-pdf-speak-wave-panel.is-processing",
        ".ft-pdf-speak-wave-panel.is-recording",
        ".ft-pdf-speak-wave-panel.is-playing",
        ".ft-pdf-speak-wave-panel.is-listening",
        ".ft-pdf-button.is-speak-training-hint",
        ".is-recording",
        ".is-processing",
        ".is-playing",
        ".is-speaking",
      ].join(", ");
      const mobileAnimationAllowed = (target) => Boolean(target && target.closest && target.closest(mobileAnimationAllowedSelectors));
      const resumeMobilePausedInfiniteAnimations = () => {
        mobilePausedInfiniteAnimations.forEach((animation) => {
          try {
            animation.play();
          } catch (error) {
          }
        });
        mobilePausedInfiniteAnimations.clear();
      };
      const syncMobileInfiniteMotion = () => {
        mobileInfiniteMotionFrame = 0;
        const mobileSurface = mobileStaticMotionSurface();
        const spaceWDesktopSurface = spaceWDesktopMotionSurface();
        const pdfSurface = pdfStaticMotionSurface();
        const active = mobileStaticMotionActive();
        document.documentElement.classList.toggle("ft-mobile-static-motion", active && mobileSurface);
        document.documentElement.classList.toggle("ft-spacew-static-motion", active && spaceWDesktopSurface);
        document.documentElement.classList.toggle("ft-pdf-static-motion", active && pdfSurface);
        updateMobileAnimationButton();
        if (!document.getAnimations || !active) {
          document.documentElement.classList.remove("ft-spacew-static-motion");
          document.documentElement.classList.remove("ft-pdf-static-motion");
          resumeMobilePausedInfiniteAnimations();
          return;
        }
        if (questionModeActive && questionRevealAnimationsActive) {
          scheduleMobileInfiniteMotionSync(760);
          return;
        }
        const animations = document.getAnimations({ subtree: true });
        const animationSet = new Set(animations);
        animations.forEach((animation) => {
          if (!mobileAnimationIsInfinite(animation)) {
            return;
          }
          const target = mobileAnimationTarget(animation);
          if (mobileAnimationAllowed(target)) {
            if (mobilePausedInfiniteAnimations.has(animation)) {
              mobilePausedInfiniteAnimations.delete(animation);
              try {
                animation.play();
              } catch (error) {
              }
            }
            return;
          }
          if (animation.playState !== "paused") {
            try {
              animation.pause();
            } catch (error) {
            }
          }
          mobilePausedInfiniteAnimations.add(animation);
        });
        mobilePausedInfiniteAnimations.forEach((animation) => {
          const target = mobileAnimationTarget(animation);
          if (!animationSet.has(animation) || !mobileAnimationIsInfinite(animation) || mobileAnimationAllowed(target)) {
            mobilePausedInfiniteAnimations.delete(animation);
            try {
              animation.play();
            } catch (error) {
            }
          }
        });
      };
      const scheduleMobileInfiniteMotionSync = (delayMs = 0) => {
        if (!document.getAnimations) {
          return;
        }
        if (mobileInfiniteMotionSyncTimer) {
          window.clearTimeout(mobileInfiniteMotionSyncTimer);
          mobileInfiniteMotionSyncTimer = 0;
        }
        const scheduleFrame = () => {
          if (!mobileInfiniteMotionFrame) {
            mobileInfiniteMotionFrame = window.requestAnimationFrame(syncMobileInfiniteMotion);
          }
        };
        if (delayMs > 0) {
          mobileInfiniteMotionSyncTimer = window.setTimeout(() => {
            mobileInfiniteMotionSyncTimer = 0;
            scheduleFrame();
          }, delayMs);
          return;
        }
        scheduleFrame();
      };
      const markMobileMotionLive = (source, durationMs = 1400) => {
        const root = mobileMotionRootFor(source);
        if (!root || !root.classList) {
          return;
        }
        root.classList.add("ft-mobile-motion-live");
        scheduleMobileInfiniteMotionSync();
        window.setTimeout(() => {
          root.classList.remove("ft-mobile-motion-live");
          scheduleMobileInfiniteMotionSync();
        }, Math.max(260, Number(durationMs) || 1400));
      };
      const setupMobileInfiniteMotionSaver = () => {
        updateMobileAnimationButton();
        const refresh = () => {
          scheduleMobileInfiniteMotionSync();
          scheduleMobileInfiniteMotionSync(420);
          if (typeof scheduleQuestionMobilePanelsSync === "function") {
            scheduleQuestionMobilePanelsSync();
          }
        };
        document.addEventListener("pointerdown", (event) => markMobileMotionLive(event.target, 1600), true);
        document.addEventListener("focusin", (event) => markMobileMotionLive(event.target, 2200), true);
        document.addEventListener("mouseover", (event) => markMobileMotionLive(event.target, 1200), true);
        window.addEventListener("resize", refresh);
        window.addEventListener("orientationchange", () => scheduleMobileInfiniteMotionSync(320));
        if (window.visualViewport) {
          window.visualViewport.addEventListener("resize", () => scheduleMobileInfiniteMotionSync(120));
        }
        if (window.MutationObserver && document.body && !mobileInfiniteMotionObserver) {
          mobileInfiniteMotionObserver = new MutationObserver(() => scheduleMobileInfiniteMotionSync(260));
          mobileInfiniteMotionObserver.observe(document.body, {
            childList: true,
            subtree: false,
          });
        }
        scheduleMobileInfiniteMotionSync();
        window.setTimeout(() => scheduleMobileInfiniteMotionSync(), 700);
        window.setTimeout(() => scheduleMobileInfiniteMotionSync(), 1800);
      };
      const translateCardPinReady = () => Boolean(
        isPhonePanelTabs() &&
        !vocabModeActive &&
        !questionModeActive &&
        !nextPanelCanShow &&
        (!ipaPanel || !ipaPanel.classList.contains("is-live")) &&
        (!speakPanel || !speakPanel.classList.contains("is-live")) &&
        (!grammarPanel || !grammarPanel.classList.contains("is-live")) &&
        cardNode &&
        !cardNode.classList.contains("is-hidden") &&
        loadGate &&
        loadGate.classList.contains("is-hidden") &&
        authGate &&
        authGate.classList.contains("is-hidden")
      );
      const setTranslateKeyboardLock = (active) => {
        document.documentElement.classList.toggle("ft-translate-keyboard-lock", Boolean(active) && translateCardPinReady());
      };
      const pinTranslateCardToViewportTop = (options = {}) => {
        if (!translateCardPinReady()) {
          setTranslateKeyboardLock(false);
          return false;
        }
        const now = Date.now();
        const force = Boolean(options.force);
        const inputActive = document.activeElement === answerInput;
        if (!force && !inputActive && now > translateKeyboardPinUntil) {
          setTranslateKeyboardLock(false);
          return false;
        }
        const viewport = window.visualViewport || null;
        const viewportOffsetTop = Number(viewport && viewport.offsetTop) || 0;
        const topGap = Math.max(0, Number(options.topGap ?? 6) || 0);
        const rect = cardNode.getBoundingClientRect();
        const pageTop = rect.top + window.scrollY;
        const targetY = Math.max(0, Math.round(pageTop - viewportOffsetTop - topGap));
        setTranslateKeyboardLock(true);
        if (Math.abs(window.scrollY - targetY) > 1) {
          window.scrollTo({ top: targetY, left: 0, behavior: "auto" });
        }
        if (stageNode && !stageNode.classList.contains("is-question-mode")) {
          stageNode.scrollTop = 0;
        }
        return true;
      };
      const scheduleTranslateCardPin = (durationMs = 720, options = {}) => {
        if (!translateCardPinReady()) {
          setTranslateKeyboardLock(false);
          return;
        }
        translateKeyboardPinUntil = Math.max(translateKeyboardPinUntil, Date.now() + Math.max(80, Number(durationMs) || 720));
        if (translateKeyboardPinFrame) {
          return;
        }
        const tick = () => {
          translateKeyboardPinFrame = 0;
          const active = pinTranslateCardToViewportTop(options);
          if (active && Date.now() < translateKeyboardPinUntil) {
            window.setTimeout(() => {
              translateKeyboardPinFrame = window.requestAnimationFrame(tick);
            }, 48);
          } else if (!active) {
            setTranslateKeyboardLock(false);
          }
        };
        translateKeyboardPinFrame = window.requestAnimationFrame(tick);
      };
      const vocabCardPinReady = () => Boolean(
        syncVocabMobilePin()
      );
      const setVocabKeyboardLock = (active) => {
        if (!active) {
          syncVocabMobilePin();
        }
        document.documentElement.classList.toggle("ft-vocab-keyboard-lock", Boolean(active) && vocabCardPinReady());
      };
      const pinVocabCardToViewportTop = (options = {}) => {
        if (!vocabCardPinReady()) {
          setVocabKeyboardLock(false);
          return false;
        }
        const now = Date.now();
        const force = Boolean(options.force);
        const inputActive = document.activeElement === vocabAnswer;
        if (!force && !inputActive && now > vocabKeyboardPinUntil) {
          setVocabKeyboardLock(false);
          return false;
        }
        const viewport = window.visualViewport || null;
        const viewportOffsetTop = Number(viewport && viewport.offsetTop) || 0;
        const viewportHeight = Math.max(1, Number(viewport && viewport.height) || window.innerHeight || document.documentElement.clientHeight || 1);
        const viewportWidth = Math.max(1, Number(viewport && viewport.width) || window.innerWidth || document.documentElement.clientWidth || 1);
        const defaultTopGap = Math.round(Math.max(72, Math.min(216, viewportHeight * 0.2)));
        const topGap = Math.max(0, Number(options.topGap ?? defaultTopGap) || 0);
        const bottomGap = Math.max(28, Math.min(96, Math.round(viewportHeight * 0.08)));
        const rect = vocabCard.getBoundingClientRect();
        const safeTop = viewportOffsetTop + topGap;
        const safeBottom = viewportOffsetTop + viewportHeight - bottomGap;
        const alreadyStable = rect.top >= safeTop - 6 && rect.bottom <= safeBottom + 6;
        const pageTop = rect.top + window.scrollY;
        setVocabKeyboardLock(true);
        if (!alreadyStable) {
          const targetTop = rect.top < safeTop
            ? topGap
            : Math.max(topGap, viewportHeight - bottomGap - Math.min(rect.height, viewportHeight - topGap - bottomGap));
          const targetY = Math.max(0, Math.round(pageTop - viewportOffsetTop - targetTop));
          if (Math.abs(window.scrollY - targetY) > 1) {
            window.scrollTo({ top: targetY, left: window.scrollX, behavior: "auto" });
          }
          if (
            stageNode
            && !stageNode.classList.contains("is-question-mode")
            && Math.abs(stageNode.scrollTop || 0) <= 2
          ) {
            stageNode.scrollTop = 0;
          }
        }
        return true;
      };
      const scheduleVocabCardPin = (durationMs = 720, options = {}) => {
        if (!vocabCardPinReady()) {
          setVocabKeyboardLock(false);
          return;
        }
        vocabKeyboardPinOptions = {
          ...vocabKeyboardPinOptions,
          ...options,
          force: Boolean(options.force || vocabKeyboardPinOptions.force),
        };
        vocabKeyboardPinUntil = Math.max(vocabKeyboardPinUntil, Date.now() + Math.max(80, Number(durationMs) || 720));
        if (vocabKeyboardPinFrame) {
          return;
        }
        const tick = () => {
          const active = pinVocabCardToViewportTop(vocabKeyboardPinOptions);
          if (active && Date.now() < vocabKeyboardPinUntil) {
            window.setTimeout(() => {
              vocabKeyboardPinFrame = window.requestAnimationFrame(tick);
            }, 48);
          } else if (!active) {
            vocabKeyboardPinFrame = 0;
            vocabKeyboardPinOptions = {};
            setVocabKeyboardLock(false);
          } else {
            vocabKeyboardPinFrame = 0;
            vocabKeyboardPinOptions = {};
          }
        };
        vocabKeyboardPinFrame = window.requestAnimationFrame(tick);
      };
      const revealMobilePanel = (key) => {
        if (key === "ipa") {
          stopGrammarAudio();
          stopSpeakReplay();
        }
        setMobilePanelUnlocked(key, true);
        mobileActivePanelKey = key;
        syncMobilePanelTabs();
      };
      const toggleMobilePanel = (key) => {
        const targetKey = mobileTabTargetKey(key);
        if (!isPhonePanelTabs() || !mobileUnlockedPanels.has(targetKey)) {
          return;
        }
        const panel = mobilePanelForKey(targetKey);
        if (!panel || !panel.classList.contains("is-live")) {
          return;
        }
        if (targetKey === "ipa") {
          stopGrammarAudio();
          stopSpeakReplay();
        }
        mobileActivePanelKey = mobileActivePanelKey === targetKey ? "" : targetKey;
        syncMobilePanelTabs();
        queueSpaceWProgressSave(120);
      };
      const restoreMobilePanelTabs = (state = {}) => {
        mobileUnlockedPanels.clear();
        if (Array.isArray(state.mobileUnlockedPanels)) {
          state.mobileUnlockedPanels
            .map((item) => clean(item))
            .filter((item) => mobilePanelKeys.has(item))
            .forEach((item) => mobileUnlockedPanels.add(item));
        }
        if (!mobileUnlockedPanels.size) {
          [
            ["score", state.scoreLive],
            ["hint", state.hintLive],
            ["about", state.aboutLive],
            ["ipa", state.ipaLive],
            ["speak", state.speakLive],
            ["grammar", state.grammarLive],
          ].forEach(([key, live]) => {
            if (live) {
              mobileUnlockedPanels.add(key);
            }
          });
        }
        mobilePanelEntries().forEach(([key, panel]) => {
          if (!panel || !panel.classList.contains("is-live")) {
            mobileUnlockedPanels.delete(key);
          }
        });
        const active = clean(state.mobileActivePanelKey || mobileActivePanelKey);
        mobileActivePanelKey = mobilePanelKeys.has(active) && mobileUnlockedPanels.has(active) ? active : "";
        syncMobilePanelTabs();
      };

      const stableElementRect = (element) => {
        if (!element) {
          return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 };
        }
        const liveRect = element.getBoundingClientRect();
        const parent = element.offsetParent;
        if (!parent) {
          return liveRect;
        }
        const parentRect = parent.getBoundingClientRect();
        const width = element.offsetWidth || liveRect.width || 0;
        const height = element.offsetHeight || liveRect.height || 0;
        const left = parentRect.left + element.offsetLeft;
        const top = parentRect.top + element.offsetTop;
        return {
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
          x: left,
          y: top,
        };
      };

      const updateDesktopPanelLayout = () => {
        if (!shellNode || !cardNode) {
          return;
        }
        const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
        const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
        const baseSpaceWViewportWidth = 1536;
        const baseSpaceWViewportHeight = 864;
        const machineScale = clamp(
          Math.min(viewportWidth / baseSpaceWViewportWidth, viewportHeight / baseSpaceWViewportHeight),
          0.82,
          1
        );
        const compactSpaceWDesktop = Boolean(
          document.documentElement.classList.contains("ft-space-w-mode") &&
          stageNode &&
          stageNode.classList.contains("is-space-w-mode") &&
          !isMobilePanelFlow()
        );
        const layoutScale = compactSpaceWDesktop ? machineScale : 1;
        document.documentElement.style.setProperty("--space-w-layout-scale", layoutScale.toFixed(4));
        if (compactSpaceWDesktop) {
          const baseCardWidth = Math.min(560 * layoutScale, viewportWidth * 0.44);
          const speakPanelTop = clamp(viewportHeight * 0.135, 88 * layoutScale, 118 * layoutScale);
          const listenPanelTop = clamp(viewportHeight * 0.165, 112 * layoutScale, 148 * layoutScale);
          const cardTopOffset = clamp(speakPanelTop * 3, viewportHeight * 0.28, viewportHeight * 0.36);
          document.documentElement.style.setProperty("--space-w-shell-width", `${Math.min(1380 * layoutScale, viewportWidth + 160 * layoutScale).toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-shell-min-width", `${Math.min(1180 * layoutScale, viewportWidth + 160 * layoutScale).toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-card-width", `${Math.max(330 * layoutScale, baseCardWidth).toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-card-margin-top", `${cardTopOffset.toFixed(1)}px`);
          document.documentElement.style.removeProperty("--space-w-card-max-height");
          document.documentElement.style.setProperty("--space-w-listen-panel-top", `${listenPanelTop.toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-listen-panel-max-height", `${Math.max(220, viewportHeight - listenPanelTop - 64 * layoutScale).toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-speak-panel-top", `${speakPanelTop.toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-speak-panel-max-height", `${Math.max(220, viewportHeight - speakPanelTop - 64 * layoutScale).toFixed(1)}px`);
          document.documentElement.style.setProperty("--space-w-stage-pad", `${Math.max(4, 5 * layoutScale).toFixed(1)}px`);
        } else {
          ["--space-w-shell-width", "--space-w-shell-min-width", "--space-w-card-width", "--space-w-card-margin-top", "--space-w-card-max-height", "--space-w-listen-panel-top", "--space-w-listen-panel-max-height", "--space-w-speak-panel-top", "--space-w-speak-panel-max-height", "--space-w-stage-pad"].forEach((property) => {
            document.documentElement.style.removeProperty(property);
          });
        }
        const resetInlinePanelBox = (panel) => {
          if (!panel) {
            return;
          }
          ["top", "bottom", "left", "right"].forEach((property) => panel.style.removeProperty(property));
        };
        if (isMobilePanelFlow()) {
          [grammarPanel, hintPanel, aboutPanel, scorePanel].forEach(resetInlinePanelBox);
          shellNode.style.removeProperty("--space-w-panel-stack-height");
          return;
        }
        const shellRect = shellNode.getBoundingClientRect();
        const cardRect = stableElementRect(cardNode);
        const gap = 18 * layoutScale;
        const compactRailGap = 12 * layoutScale;
        const compactCardWidth = compactSpaceWDesktop
          ? Math.max(330 * layoutScale, Math.min(560 * layoutScale, viewportWidth * 0.44))
          : Math.min(500, viewportWidth * 0.38);
        const compactRailSpace = Math.max(0, (viewportWidth - compactCardWidth) / 2);
        const compactLeftRailWidth = `${clamp(compactRailSpace - 16 * layoutScale, 300 * layoutScale, 370 * layoutScale).toFixed(1)}px`;
        const compactScoreSoloWidth = compactLeftRailWidth;
        const compactRightRailWidth = `${clamp(compactRailSpace - 10 * layoutScale, 270 * layoutScale, 360 * layoutScale).toFixed(1)}px`;
        const top = Math.max(0, cardRect.bottom - shellRect.top + gap);
        const panelBottomScrollReserve = Math.max(56 * layoutScale, 32);
        let requiredStackHeight = 0;
        const noteStackHeight = (value) => {
          if (Number.isFinite(value)) {
            requiredStackHeight = Math.max(requiredStackHeight, value);
          }
        };
        const noteLivePanelHeight = (panel) => {
          if (!panel || !panel.classList || !panel.classList.contains("is-live")) {
            return;
          }
          const panelHeight = panel.offsetHeight || panel.getBoundingClientRect().height || 0;
          noteStackHeight(Math.ceil(top + panelHeight + gap));
        };
        if (grammarPanel) {
          grammarPanel.style.bottom = "auto";
          grammarPanel.style.left = "auto";
          grammarPanel.style.right = "0px";
          if (compactSpaceWDesktop) {
            grammarPanel.style.width = compactRightRailWidth;
          } else {
            grammarPanel.style.removeProperty("width");
          }
          const shouldStackGrammar = Boolean(
            ipaPanel &&
            grammarPanel.classList.contains("is-live") &&
            ipaPanel.classList.contains("is-live"),
          );
          if (shouldStackGrammar) {
            const ipaRect = stableElementRect(ipaPanel);
            const grammarHeight = grammarPanel.offsetHeight || grammarPanel.getBoundingClientRect().height || 0;
            const stackedTop = Math.max(0, ipaRect.bottom - shellRect.top + gap);
            grammarPanel.style.top = `${stackedTop.toFixed(1)}px`;
            noteStackHeight(Math.ceil(stackedTop + grammarHeight + gap));
          } else {
            grammarPanel.style.top = `${top.toFixed(1)}px`;
          }
        }
        if (hintPanel) {
          hintPanel.style.top = `${top.toFixed(1)}px`;
          hintPanel.style.bottom = "auto";
          hintPanel.style.left = "50%";
          hintPanel.style.right = "auto";
          noteLivePanelHeight(hintPanel);
        }
        if (aboutPanel) {
          aboutPanel.style.top = `${top.toFixed(1)}px`;
          aboutPanel.style.bottom = "auto";
          aboutPanel.style.left = "50%";
          aboutPanel.style.right = "auto";
          noteLivePanelHeight(aboutPanel);
        }
        if (speakPanel && compactSpaceWDesktop) {
          speakPanel.style.left = "0px";
          speakPanel.style.right = "auto";
          speakPanel.style.top = `var(--space-w-speak-panel-top, ${(62 * layoutScale).toFixed(1)}px)`;
          speakPanel.style.bottom = "auto";
          speakPanel.style.width = compactLeftRailWidth;
          if (speakPanel.classList.contains("is-live")) {
            const speakRect = stableElementRect(speakPanel);
            const speakHeight = speakPanel.offsetHeight || speakRect.height || 0;
            const speakTop = Math.max(0, speakRect.top - shellRect.top);
            noteStackHeight(Math.ceil(speakTop + speakHeight + gap));
          }
        } else if (speakPanel) {
          ["top", "bottom", "left", "right", "width"].forEach((property) => speakPanel.style.removeProperty(property));
        }
        if (scorePanel) {
          scorePanel.style.left = "0px";
          scorePanel.style.right = "auto";
          const placeSoloScorePanel = (widthValue = "") => {
            const scoreHeight = scorePanel.offsetHeight || scorePanel.getBoundingClientRect().height || 0;
            const viewportBottomInShell = Math.max(0, viewportHeight - shellRect.top - 14 * layoutScale);
            const maxTop = Math.max(0, viewportBottomInShell - scoreHeight);
            const soloTop = Math.max(0, Math.min(top, maxTop));
            scorePanel.style.top = `${soloTop.toFixed(1)}px`;
            scorePanel.style.bottom = "auto";
            if (widthValue) {
              scorePanel.style.width = widthValue;
            }
            scorePanel.style.removeProperty("max-height");
            if (scorePanel.classList.contains("is-live")) {
              noteStackHeight(Math.ceil(soloTop + scoreHeight + gap));
            }
          };
          if (compactSpaceWDesktop) {
            const shouldStackCompactScore = Boolean(
              speakPanel &&
              scorePanel.classList.contains("is-live") &&
              speakPanel.classList.contains("is-live")
            );
            if (shouldStackCompactScore) {
              const speakRect = stableElementRect(speakPanel);
              scorePanel.classList.add("is-compact-score-stacked");
              scorePanel.classList.remove("is-compact-score-solo");
              const stackedTop = Math.max(18 * layoutScale, speakRect.bottom - shellRect.top + compactRailGap);
              scorePanel.style.top = `${stackedTop.toFixed(1)}px`;
              scorePanel.style.bottom = "auto";
              scorePanel.style.width = compactLeftRailWidth;
              scorePanel.style.removeProperty("max-height");
              const scoreHeight = scorePanel.offsetHeight || scorePanel.getBoundingClientRect().height || 0;
              noteStackHeight(Math.ceil(stackedTop + scoreHeight + gap));
            } else {
              scorePanel.classList.add("is-compact-score-solo");
              scorePanel.classList.remove("is-compact-score-stacked");
              placeSoloScorePanel(compactScoreSoloWidth);
            }
          } else {
            scorePanel.classList.remove("is-compact-score-solo", "is-compact-score-stacked");
            ["width", "max-height"].forEach((property) => scorePanel.style.removeProperty(property));
            const shouldStackScore = Boolean(
              speakPanel &&
              scorePanel.classList.contains("is-live") &&
              speakPanel.classList.contains("is-live"),
            );
            if (shouldStackScore) {
              const speakRect = stableElementRect(speakPanel);
              const scoreHeight = scorePanel.offsetHeight || scorePanel.getBoundingClientRect().height || 0;
              const stackedTop = Math.max(0, speakRect.bottom - shellRect.top + gap);
              scorePanel.style.top = `${stackedTop.toFixed(1)}px`;
              scorePanel.style.bottom = "auto";
              noteStackHeight(Math.ceil(stackedTop + scoreHeight + gap));
            } else {
              placeSoloScorePanel();
            }
          }
        }
        if (requiredStackHeight > 0) {
          shellNode.style.setProperty("--space-w-panel-stack-height", `${Math.ceil(requiredStackHeight + panelBottomScrollReserve)}px`);
        } else {
          shellNode.style.removeProperty("--space-w-panel-stack-height");
        }
      };

      let desktopPanelLayoutFrame = 0;
      const scheduleDesktopPanelLayout = () => {
        if (desktopPanelLayoutFrame || isMobilePanelFlow()) {
          return;
        }
        desktopPanelLayoutFrame = window.requestAnimationFrame(() => {
          desktopPanelLayoutFrame = 0;
          updateDesktopPanelLayout();
          [speakPanel, scorePanel, ipaPanel, grammarPanel].forEach((panel) => {
            if (panel && panel.classList.contains("is-live")) {
              positionConnectorTo(panel);
            }
          });
        });
      };

      const setActivePanel = (panel) => {
        connectorTargetPanel = panel || null;
        allPanels().forEach((item) => {
          item.classList.toggle("is-active-panel", Boolean(panel && item === panel));
        });
        allPanels().forEach((item) => {
          const node = connectorForPanel(item);
          const isLive = item.classList.contains("is-live");
          const keepIpaConnectorBright = Boolean(item === ipaPanel && isLive);
          node.classList.toggle("is-active", Boolean(panel && item === panel && isLive));
          node.classList.toggle("is-dim", Boolean(isLive && !keepIpaConnectorBright && (!panel || item !== panel)));
        });
      };

      const hidePanelConnector = (panel) => {
        const node = connectorForPanel(panel);
        node.classList.remove("is-live", "is-complete", "is-active", "is-dim");
      };

      const clearAllConnectors = () => {
        allPanelConnectors().forEach((node) => {
          node.classList.remove("is-live", "is-complete", "is-active", "is-dim");
        });
        setActivePanel(null);
      };

      const autoPanToPanel = (panel) => {
        if (!panel || isMobilePanelFlow()) {
          return;
        }
        window.requestAnimationFrame(() => {
          updateDesktopPanelLayout();
          const rect = panel.getBoundingClientRect();
          const margin = 28;
          let dx = 0;
          let dy = 0;
          if (rect.right > window.innerWidth - margin) {
            dx = rect.right - window.innerWidth + margin;
          } else if (rect.left < margin) {
            dx = rect.left - margin;
          }
          if (rect.bottom > window.innerHeight - margin) {
            dy = rect.bottom - window.innerHeight + margin;
          } else if (rect.top < margin) {
            dy = rect.top - margin;
          }
          if (Math.abs(dx) < 1 && Math.abs(dy) < 1) {
            return;
          }
          const scrollTarget = stageNode && (stageNode.scrollWidth > stageNode.clientWidth + 2 || stageNode.scrollHeight > stageNode.clientHeight + 2)
            ? stageNode
            : window;
          scrollTarget.scrollBy({ left: dx, top: dy, behavior: "smooth" });
          window.setTimeout(positionConnector, 260);
          window.setTimeout(positionConnector, 620);
        });
      };

      const setConnectorPath = (startX, startY, endX, endY, targetConnector = ipaConnector) => {
        const svg = targetConnector && targetConnector.querySelector(".ft-connector-svg");
        const path = targetConnector && targetConnector.querySelector(".ft-connector-path");
        const glow = targetConnector && targetConnector.querySelector(".ft-connector-glow");
        if (!targetConnector || !svg || !path || !glow) {
          return;
        }
        const pad = 22;
        const left = Math.min(startX, endX) - pad;
        const top = Math.min(startY, endY) - pad;
        const width = Math.max(44, Math.abs(endX - startX) + pad * 2);
        const height = Math.max(44, Math.abs(endY - startY) + pad * 2);
        const sx = startX - left;
        const sy = startY - top;
        const ex = endX - left;
        const ey = endY - top;
        const dx = ex - sx;
        const dy = ey - sy;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const nx = -dy / distance;
        const ny = dx / distance;
        const amplitude = clamp(distance * 0.045, 5, 18);
        const waveCount = distance > 420 ? 5 : 4;
        const segments = waveCount * 2;
        let d = `M ${sx.toFixed(1)} ${sy.toFixed(1)}`;
        for (let index = 1; index <= segments; index += 1) {
          const t0 = (index - 1) / segments;
          const t1 = index / segments;
          const tm = (t0 + t1) / 2;
          const waveMid = Math.sin(tm * Math.PI * waveCount) * amplitude;
          const waveEnd = Math.sin(t1 * Math.PI * waveCount) * amplitude;
          const cx = sx + dx * tm + nx * waveMid;
          const cy = sy + dy * tm + ny * waveMid;
          const px = sx + dx * t1 + nx * waveEnd;
          const py = sy + dy * t1 + ny * waveEnd;
          d += ` Q ${cx.toFixed(1)} ${cy.toFixed(1)}, ${px.toFixed(1)} ${py.toFixed(1)}`;
        }

        targetConnector.style.setProperty("--connector-left", `${left.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-top", `${top.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-width", `${width.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-height", `${height.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-start-x", `${sx.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-start-y", `${sy.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-end-x", `${ex.toFixed(1)}px`);
        targetConnector.style.setProperty("--connector-end-y", `${ey.toFixed(1)}px`);
        svg.setAttribute("viewBox", `0 0 ${width.toFixed(1)} ${height.toFixed(1)}`);
        path.setAttribute("d", d);
        glow.setAttribute("d", d);
        let length = Math.hypot(ex - sx, ey - sy);
        try {
          length = path.getTotalLength();
        } catch (error) {
          // SVG measurement can fail before layout is ready; geometric length keeps the draw natural.
        }
        targetConnector.style.setProperty("--connector-length", `${Math.max(1, Math.ceil(length))}`);
        targetConnector.style.setProperty("--connector-draw-ms", `${CONNECTOR_DRAW_MS}ms`);
      };

      const measureFinalPanelRect = (panel) => {
        updateDesktopPanelLayout();
        const alreadyLive = panel.classList.contains("is-live");
        if (!alreadyLive) {
          panel.classList.add("is-measuring");
        }
        const rect = panel.getBoundingClientRect();
        if (!alreadyLive) {
          panel.classList.remove("is-measuring");
        }
        return rect;
      };

      const positionConnectorTo = (targetPanel = ipaPanel) => {
        if (!shellNode || !cardNode || !targetPanel) {
          return;
        }
        if (isMobilePanelFlow()) {
          const targetConnector = connectorForPanel(targetPanel);
          if (targetConnector) {
            [
              "--connector-top",
              "--connector-left",
              "--connector-width",
              "--connector-height",
              "--connector-start-x",
              "--connector-start-y",
              "--connector-end-x",
              "--connector-end-y",
            ].forEach((property) => targetConnector.style.removeProperty(property));
          }
          return true;
        }
        updateDesktopPanelLayout();
        const targetConnector = connectorForPanel(targetPanel);
        const shellRect = shellNode.getBoundingClientRect();
        const cardRect = stableElementRect(cardNode);
        const panelRect = measureFinalPanelRect(targetPanel);
        if (!shellRect.width || !shellRect.height || !cardRect.width || !cardRect.height || !panelRect.width || !panelRect.height) {
          return;
        }

        const cornerPad = 12;
        let best = null;
        if (!isMobilePanelFlow()) {
          if (targetPanel === speakPanel) {
            best = {
              start: { x: cardRect.left + cornerPad, y: cardRect.top + cornerPad },
              end: { x: panelRect.right - cornerPad, y: panelRect.bottom - cornerPad },
            };
          } else if (targetPanel === scorePanel) {
            best = {
              start: { x: cardRect.left + cornerPad, y: cardRect.bottom - cornerPad },
              end: { x: panelRect.right - cornerPad, y: panelRect.top + cornerPad },
            };
          } else if (targetPanel === hintPanel || targetPanel === aboutPanel) {
            best = {
              start: { x: cardRect.left + cardRect.width / 2, y: cardRect.bottom - cornerPad },
              end: { x: panelRect.left + panelRect.width / 2, y: panelRect.top + cornerPad },
            };
          } else if (targetPanel === grammarPanel) {
            best = {
              start: { x: cardRect.right - cornerPad, y: cardRect.bottom - cornerPad },
              end: { x: panelRect.left + cornerPad, y: panelRect.top + cornerPad },
            };
          } else {
            best = {
              start: { x: cardRect.right - cornerPad, y: cardRect.top + cornerPad },
              end: { x: panelRect.left + cornerPad, y: panelRect.bottom - cornerPad },
            };
          }
        } else {
          const cardCenterX = cardRect.left + cardRect.width / 2;
          const panelCenterX = panelRect.left + panelRect.width / 2;
          const cardCorners = [
            { x: cardRect.left + 10, y: cardRect.top + 10 },
            { x: cardRect.right - 10, y: cardRect.top + 10 },
            { x: cardRect.right - 10, y: cardRect.bottom - 10 },
            { x: cardRect.left + 10, y: cardRect.bottom - 10 },
          ];
          const panelCorners = [
            { x: panelRect.left + 10, y: panelRect.top + 10 },
            { x: panelRect.right - 10, y: panelRect.top + 10 },
            { x: panelRect.right - 10, y: panelRect.bottom - 10 },
            { x: panelRect.left + 10, y: panelRect.bottom - 10 },
          ];
          cardCorners.forEach((start) => {
            panelCorners.forEach((end) => {
              const dx = end.x - start.x;
              const dy = end.y - start.y;
              const crossesCard = end.x < cardCenterX ? start.x > cardCenterX : start.x < cardCenterX;
              const crossesPanel = panelCenterX < cardCenterX ? end.x > panelCenterX : end.x < panelCenterX;
              const penalty = (crossesCard || crossesPanel) ? 90000 : 0;
              const score = dx * dx + dy * dy + penalty;
              if (!best || score < best.score) {
                best = { start, end, score };
              }
            });
          });
        }

        setConnectorPath(
          best.start.x - shellRect.left,
          best.start.y - shellRect.top,
          best.end.x - shellRect.left,
          best.end.y - shellRect.top,
          targetConnector,
        );
        return true;
      };

      const positionConnector = () => {
        let positioned = false;
        allPanels().forEach((panel) => {
          if (panel.classList.contains("is-live")) {
            positioned = positionConnectorTo(panel) || positioned;
          }
        });
        if (!positioned) {
          return positionConnectorTo(ipaPanel);
        }
        return positioned;
      };

      const revealIpa = (message = "Chính xác.", options = {}) => {
        const preferredPanel = options && options.preferredPanel ? options.preferredPanel : null;
        const preferredPanelIsLive = () => Boolean(preferredPanel && preferredPanel.classList.contains("is-live"));
        feedbackNode.textContent = message;
        feedbackNode.classList.remove("is-error");
        feedbackNode.classList.add("is-ok");
        hideSpaceWTokenSupport(true);
        stopWordHintWatch();
        if (revealTimer) {
          window.clearTimeout(revealTimer);
          revealTimer = 0;
        }
        if (connectorTimer) {
          window.clearTimeout(connectorTimer);
          connectorTimer = 0;
        }
        if (!isMobilePanelFlow()) {
          lockScorePanel();
          lockGrammarPanel();
        }
        setAnswerEntryLocked(true, { force: true });
        const visualPanel = preferredPanelIsLive() ? preferredPanel : ipaPanel;
        const activeConnector = connectorForPanel(visualPanel);
        activeConnector.classList.remove("is-live", "is-complete", "is-dim");
        ipaPanel.classList.remove("is-live", "is-mobile-hidden");
        setActivePanel(visualPanel);
        positionConnectorTo(visualPanel);
        void activeConnector.offsetWidth;
        void activeConnector.querySelector(".ft-connector-path").getBoundingClientRect();
        activeConnector.classList.add("is-live");
        setActivePanel(visualPanel);
        connectorTimer = window.setTimeout(() => {
          activeConnector.classList.add("is-complete");
          if (preferredPanelIsLive()) {
            setActivePanel(preferredPanel);
          } else {
            setActivePanel(ipaPanel);
          }
          connectorTimer = 0;
        }, Math.max(120, CONNECTOR_DRAW_MS - 90));
        revealTimer = window.setTimeout(() => {
          ipaPanel.classList.add("is-live");
          ipaConnector.classList.remove("is-dim");
          positionConnectorTo(ipaPanel);
          ipaConnector.classList.add("is-live", "is-complete");
          if (preferredPanelIsLive()) {
            setMobilePanelUnlocked("ipa", true);
            if (preferredPanel === aboutPanel) {
              revealMobilePanel("about");
              updateAboutConnector(true);
            } else {
              setActivePanel(preferredPanel);
              syncMobilePanelTabs();
            }
          } else {
            setActivePanel(ipaPanel);
            revealMobilePanel("ipa");
          }
          if (completedListenCount < requiredListenCount()) {
            if (isMobilePanelFlow()) {
              setSpeakStatus(`Hãy nghe trọn câu tiếng Anh ${requiredListenCount()} lần trước khi Speak.`, "");
            } else {
              hideSpeakPanel();
            }
          } else {
            showSpeakPanel(false);
          }
          autoPanToPanel(preferredPanelIsLive() ? preferredPanel : ipaPanel);
          window.requestAnimationFrame(positionConnector);
          window.setTimeout(positionConnector, 260);
          revealTimer = 0;
          queueSpaceWProgressSave(120);
        }, CONNECTOR_DRAW_MS);
        updateNextButton(true);
        const listenMessage = listenStatusText();
        if (listenMessage) {
          setTtsStatus(listenMessage);
        }
        queueSpaceWProgressSave(160);
      };

      const setTtsStatus = (message, isError = false) => {
        ttsStatus.textContent = message;
        ttsStatus.classList.toggle("is-error", Boolean(isError));
      };

      const syncTopLoadingStatus = (message = "", isError = false) => {
        if (!topLoading || !topLoadingText) {
          return;
        }
        if (topLoadingForceVisible) {
          return;
        }
        const activeGate = Boolean(
          loadGate
          && !loadGate.classList.contains("is-hidden")
          && !loadGate.classList.contains("is-file-ready")
        );
        const renderingPdfPage = Boolean(
          pdfModeActive
          && pdfCompactToolbarEnabled
          && pdfEls
          && pdfEls.root
          && pdfEls.root.classList.contains("is-rendering-page")
        );
        const activePdfCompact = Boolean(pdfModeActive && pdfCompactToolbarEnabled && !renderingPdfPage);
        const text = clean(message || "");
        const show = Boolean((activeGate || activePdfCompact) && text);
        topLoadingText.textContent = text || "Loading...";
        topLoading.classList.toggle("is-visible", show);
        topLoading.classList.toggle("is-error", Boolean(isError));
        topLoading.setAttribute("aria-hidden", show ? "false" : "true");
      };

      let loadStatusAutoClearTimer = 0;
      let loadStatusAutoHideTimer = 0;
      let topLoadingForceVisible = false;
      let topLoadingForceHideTimer = 0;
      const setTopOperationStatus = (message = "", options = {}) => {
        if (!topLoading || !topLoadingText) {
          return;
        }
        if (topLoadingForceHideTimer) {
          window.clearTimeout(topLoadingForceHideTimer);
          topLoadingForceHideTimer = 0;
        }
        const text = clean(message || "");
        topLoadingForceVisible = Boolean(text);
        if (!text) {
          topLoading.classList.remove("is-visible", "is-error", "is-working");
          topLoading.style.removeProperty("--ft-working-progress");
          topLoading.setAttribute("aria-hidden", "true");
          return;
        }
        const progress = Math.max(0.04, Math.min(1, Number(options.progress || 0.25) || 0.25));
        topLoadingText.textContent = text;
        topLoading.style.setProperty("--ft-working-progress", String(progress));
        topLoading.classList.add("is-visible");
        topLoading.classList.toggle("is-error", Boolean(options.isError));
        topLoading.classList.toggle("is-working", Boolean(options.working));
        topLoading.setAttribute("aria-hidden", "false");
        const autoHideMs = Math.max(0, Number(options.autoHideMs || 0) || 0);
        if (autoHideMs > 0) {
          const expected = text;
          topLoadingForceHideTimer = window.setTimeout(() => {
            if (topLoadingText && clean(topLoadingText.textContent || "") === expected) {
              setTopOperationStatus("");
            }
          }, autoHideMs);
        }
      };
      const clearLoadStatusAutoTimers = () => {
        if (loadStatusAutoClearTimer) {
          window.clearTimeout(loadStatusAutoClearTimer);
          loadStatusAutoClearTimer = 0;
        }
        if (loadStatusAutoHideTimer) {
          window.clearTimeout(loadStatusAutoHideTimer);
          loadStatusAutoHideTimer = 0;
        }
      };
      if (topLoading) {
        const hideTopLoadingOnHover = () => {
          clearLoadStatusAutoTimers();
          if (topLoadingForceHideTimer) {
            window.clearTimeout(topLoadingForceHideTimer);
            topLoadingForceHideTimer = 0;
          }
          topLoadingForceVisible = false;
          if (loadStatus) {
            loadStatus.textContent = "";
            loadStatus.classList.remove("is-hiding", "is-error");
          }
          topLoading.classList.remove("is-visible", "is-error", "is-working");
          topLoading.style.removeProperty("--ft-working-progress");
          topLoading.setAttribute("aria-hidden", "true");
        };
        topLoading.addEventListener("pointerenter", hideTopLoadingOnHover, { passive: true });
        topLoading.addEventListener("mouseenter", hideTopLoadingOnHover, { passive: true });
      }

      const shouldAutoHideLoadStatus = (message = "", isError = false) => {
        const normalized = clean(message || "");
        if (/\bcompleted\b/i.test(normalized)) {
          return false;
        }
        return Boolean(normalized);
      };

      const setLoadStatus = (message, isError = false) => {
        clearLoadStatusAutoTimers();
        loadStatus.classList.remove("is-hiding");
        loadStatus.textContent = message;
        loadStatus.classList.toggle("is-error", Boolean(isError));
        syncTopLoadingStatus(message, isError);
        if (!shouldAutoHideLoadStatus(message, isError)) {
          return;
        }
        const expected = clean(message || "");
        loadStatusAutoClearTimer = window.setTimeout(() => {
          if (clean(loadStatus.textContent || "") !== expected) {
            return;
          }
          loadStatus.classList.add("is-hiding");
          loadStatusAutoHideTimer = window.setTimeout(() => {
            if (clean(loadStatus.textContent || "") === expected) {
              loadStatus.textContent = "";
              loadStatus.classList.remove("is-hiding", "is-error");
              syncTopLoadingStatus("", false);
            }
          }, 240);
        }, 3000);
      };

      if (loadGate && topLoading && window.MutationObserver) {
        new MutationObserver(() => {
          syncTopLoadingStatus(loadStatus ? loadStatus.textContent : "", Boolean(loadStatus && loadStatus.classList.contains("is-error")));
        }).observe(loadGate, { attributes: true, attributeFilter: ["class"] });
      }

      window.addEventListener("error", (event) => {
        const message = event && event.message ? event.message : "Lỗi runtime trong trang.";
        if (loadGate && !loadGate.classList.contains("is-hidden")) {
          setLoadStatus(message, true);
        }
        setTtsStatus(message, true);
      });

      window.addEventListener("unhandledrejection", (event) => {
        const reason = event && event.reason;
        const message = reason && reason.message ? reason.message : "Lỗi async trong trang.";
        if (loadGate && !loadGate.classList.contains("is-hidden")) {
          setLoadStatus(message, true);
        }
        setTtsStatus(message, true);
      });

      const delay = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

      const decodeBase64Url = (value) => {
        const base64 = String(value || "").replace(/-/g, "+").replace(/_/g, "/");
        const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
        const binary = window.atob(padded);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
          bytes[index] = binary.charCodeAt(index);
        }
        return bytes;
      };

      const gunzipBytes = async (bytes) => {
        if (!("DecompressionStream" in window)) {
          throw new Error("Trình duyệt này chưa hỗ trợ giải nén FTG1. Hãy dùng Chrome hoặc Edge mới.");
        }
        const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
        const buffer = await new Response(stream).arrayBuffer();
        return new Uint8Array(buffer);
      };

      const normalizeCompactFuturePayload = (payload = {}) => ({
        kind: "future_translation_payload",
        version: Number(payload.v || 1) || 1,
        title: clean(payload.t),
        effects: payload.fx || payload.effects || payload.sounds || {},
        study: payload.st || payload.study || {},
        nodes: (Array.isArray(payload.n) ? payload.n : []).map((item) => ({
          vi: item.q,
          en: item.e,
          ipa: item.i,
          ipa_us: item.iu,
          ipa_uk: item.ik,
          accept: item.a,
          voice: item.vc,
          tokens: item.tk,
          timings: item.tm,
          duration_ms: item.d,
          audio: item.au ? { mime: item.au[0], base64: item.au[1], url: item.au[2] || "" } : null,
          question_audio: item.vq || item.question_audio || item.questionAudio,
          audio_voices: item.av,
          analysis: item.an,
          scoring: item.sc,
          grammar_questions: item.gq || item.grammar_questions || item.grammarQuiz,
          meanings: item.mn,
          hint: item.hint || item.ht || item.guide || item.note || item.tip || "",
          ab: item.ab || item.about || item.abouts || item.qa || item.qas || item.info || item.infos || item.expert || item.experts || item.expert_notes || item.expertNotes || [],
          xp: item.xp || item.practice || item.extra_practice || item.extraPractice || item.supplemental || item.training || item.train || [],
        })),
      });

      const normalizeVocabularyAudioMap = (raw) => {
        const source = raw && typeof raw === "object" ? raw : {};
        const out = {};
        Object.entries(source).forEach(([key, value]) => {
          const cleanKey = clean(key);
          const clip = normalizeAudioClip(value);
          if (cleanKey && clip) {
            out[cleanKey] = clip;
          }
        });
        return out;
      };

      const vocabularyMeaningAudioClip = (meaning = "") => {
        const text = clean(meaning);
        return text
          ? { m: "audio/mpeg", u: `/server-data/qm-sound?meaning=${encodeURIComponent(text)}`, src: "QMLearn/Data/meaning" }
          : null;
      };

      const attachVocabularyMeaningAudio = (audio = {}, meaning = "", options = {}) => {
        const out = audio && typeof audio === "object" ? { ...audio } : {};
        if (options.attach === false) {
          return out;
        }
        const clip = vocabularyMeaningAudioClip(meaning);
        if (clip) {
          out["sot:vi-VN"] = clip;
          out.vi = clip;
        }
        return out;
      };

      const normalizeVocabularyDetail = (raw) => {
        const source = raw && typeof raw === "object" ? raw : {};
        const rawItems = Array.isArray(source.items) ? source.items : (Array.isArray(source.i) ? source.i : []);
        const items = rawItems.map((entry) => {
          if (Array.isArray(entry)) {
            return { kind: clean(entry[0]), text: clean(entry[1]), en: clean(entry[2]), vi: clean(entry[3]) };
          }
          const item = entry && typeof entry === "object" ? entry : {};
          return {
            kind: clean(item.kind ?? item.k ?? ""),
            text: clean(item.text ?? item.t ?? ""),
            en: clean(item.en ?? item.e ?? ""),
            vi: clean(item.vi ?? item.v ?? ""),
          };
        }).filter((item) => item.kind || item.text || item.en || item.vi);
        return {
          source: clean(source.source ?? source.src ?? "dict_all"),
          key: clean(source.key ?? source.k ?? ""),
          items,
        };
      };

      const normalizeVocabularyImage = (raw) => {
        const source = raw && typeof raw === "object" ? raw : {};
        return {
          url: clean(source.url ?? source.u ?? source.src ?? ""),
          source: clean(source.source ?? source.s ?? ""),
          credit: clean(source.credit ?? source.c ?? source.title ?? ""),
        };
      };

      const normalizeVocabularyWords = (rawWords, options = {}) => {
        const words = Array.isArray(rawWords) ? rawWords : [];
        const staticAnswer = Boolean(options.staticAnswer);
        return words
          .map((item) => {
            if (Array.isArray(item)) {
              const meaning = clean(item[1]);
              return {
                word: clean(item[0]),
                meaning,
                static_answer: staticAnswer,
                pron: clean(item[2]),
                type: clean(item[3]),
                audio: attachVocabularyMeaningAudio(normalizeVocabularyAudioMap(item[4] || {}), meaning, { attach: !staticAnswer }),
                question_audio: normalizeVocabularyAudioMap(item[7] || item[8] || {}),
                detail: normalizeVocabularyDetail(item[5] || {}),
                image: normalizeVocabularyImage(item[6] || {}),
              };
            }
            const raw = item && typeof item === "object" ? item : {};
            const meaning = clean(raw.meaning ?? raw.m ?? raw.vi ?? raw.q ?? "");
            const itemStaticAnswer = staticAnswer || Boolean(raw.static_answer ?? raw.staticAnswer ?? raw.sa);
            return {
              word: clean(raw.word ?? raw.w ?? raw.en ?? raw.e ?? ""),
              meaning,
              static_answer: itemStaticAnswer,
              pron: clean(raw.pron ?? raw.p ?? raw.ipa ?? raw.i ?? ""),
              type: clean(raw.type ?? raw.ty ?? raw.pos ?? ""),
              audio: attachVocabularyMeaningAudio(normalizeVocabularyAudioMap(raw.audio ?? raw.au ?? raw.audios ?? {}), meaning, { attach: !itemStaticAnswer }),
              question_audio: normalizeVocabularyAudioMap(raw.question_audio ?? raw.questionAudio ?? raw.qau ?? raw.qa ?? {}),
              detail: normalizeVocabularyDetail(raw.detail ?? raw.d ?? {}),
              image: normalizeVocabularyImage(raw.image ?? raw.im ?? raw.img ?? {}),
            };
          })
          .filter((item) => item.word);
      };

      const normalizeQuestionType = (value) => {
        const key = clean(value).toLowerCase().replace(/[-\s]+/g, "_");
        if (["input", "typed", "text", "tu_luan", "essay", "written"].includes(key)) {
          return "input";
        }
        if (["select", "token_select", "word_select", "select_tokens", "select_words", "chon_tu", "chon_token"].includes(key)) {
          return "select";
        }
        if (["guide", "guidance", "instruction", "instructions", "demo", "show", "presentation", "huong_dan"].includes(key)) {
          return "guide";
        }
        return "choice";
      };

      const splitQuestionSelectTokens = (value) => {
        if (Array.isArray(value)) {
          return value.map((entry) => clean(entry && typeof entry === "object" ? (entry.text ?? entry.token ?? entry.value ?? entry.t) : entry)).filter(Boolean);
        }
        const raw = preserveQuestionText(value);
        if (!raw) {
          return [];
        }
        const lines = raw.split(/\r?\n+/).map(clean).filter(Boolean);
        if (lines.length > 1) {
          return lines;
        }
        return clean(raw).split(/\s+/).map(clean).filter(Boolean);
      };

      const normalizeQuestionCardMode = (value, fallback = "question") => {
        const key = clean(value).toLowerCase().replace(/[-\s]+/g, "_");
        if (["linking", "link", "linked", "linked_question", "linking_question", "picture", "picture_question", "question_picture", "question_picture_card"].includes(key)) {
          return "linking";
        }
        if (["question", "normal", "card", "question_card", "default"].includes(key)) {
          return "question";
        }
        return fallback === "linking" ? "linking" : "question";
      };

      const normalizeQuestionRewards = (source = {}) => {
        const data = source && typeof source === "object" ? source : {};
        const rawCrystal = data.crystal && typeof data.crystal === "object" ? data.crystal : data;
        const rawNodeNew = data.node_new && typeof data.node_new === "object" ? data.node_new : {};
        const rawNodeReview = data.node_review && typeof data.node_review === "object" ? data.node_review : {};
        const name = clean(rawCrystal.name ?? rawCrystal.title ?? rawCrystal.n ?? "Golden Magic Book") || "Golden Magic Book";
        const use = preserveQuestionText(rawCrystal.use ?? rawCrystal.purpose ?? rawCrystal.description ?? rawCrystal.u ?? "Earned by completing a new Space_Q node correctly.") || "Earned by completing a new Space_Q node correctly.";
        return {
          crystal: {
            id: clean(rawCrystal.id ?? "space_q_spellbook_gold").toLowerCase() || "space_q_spellbook_gold",
            name,
            use,
          },
          node_new: {
            id: clean(rawNodeNew.id ?? "space_q_spellbook_gold").toLowerCase() || "space_q_spellbook_gold",
            name: clean(rawNodeNew.name ?? rawNodeNew.title ?? "Golden Magic Book") || "Golden Magic Book",
            use: preserveQuestionText(rawNodeNew.use ?? rawNodeNew.purpose ?? rawNodeNew.description ?? "Earned by completing a new Space_Q node correctly.") || "Earned by completing a new Space_Q node correctly.",
          },
          node_review: {
            id: clean(rawNodeReview.id ?? "space_q_spellbook_silver").toLowerCase() || "space_q_spellbook_silver",
            name: clean(rawNodeReview.name ?? rawNodeReview.title ?? "Silver Magic Book") || "Silver Magic Book",
            use: preserveQuestionText(rawNodeReview.use ?? rawNodeReview.purpose ?? rawNodeReview.description ?? "Earned by completing a Space_Q review node correctly.") || "Earned by completing a Space_Q review node correctly.",
          },
        };
      };

      const normalizeGuidanceTreeNode = (source) => {
        const data = source && typeof source === "object" ? source : {};
        const children = (Array.isArray(data.children) ? data.children : (Array.isArray(data.items) ? data.items : []))
          .map(normalizeGuidanceTreeNode)
          .filter(Boolean);
        const title = clean(data.title ?? data.label ?? data.name ?? data.t ?? "");
        const body = preserveQuestionText(data.body ?? data.content ?? data.text ?? data.info ?? data.b ?? "");
        const main = preserveQuestionText(data.main ?? data.connector ?? data.lead ?? data.m ?? "");
        const answerOption = clean(data.answer_option ?? data.answerOption ?? data.option ?? data.ao ?? "");
        const quizType = normalizeQuestionType(data.type ?? data.mode ?? data.kind ?? data.quiz_type ?? data.question_type ?? "");
        const question = preserveQuestionText(data.question ?? data.prompt ?? data.q ?? "");
        const answer = clean(data.answer ?? data.correct ?? data.a ?? "");
        const wrongSource = Array.isArray(data.wrong) ? data.wrong
          : (Array.isArray(data.wrongs) ? data.wrongs
            : (Array.isArray(data.options) ? data.options
              : (Array.isArray(data.w) ? data.w : [])));
        const answerSource = Array.isArray(data.answers) ? data.answers
          : (Array.isArray(data.accept) ? data.accept
            : (Array.isArray(data.accepts) ? data.accepts
              : (Array.isArray(data.alts) ? data.alts : [])));
        const wrong = wrongSource.map((value) => clean(value && typeof value === "object" ? (value.text ?? value.answer ?? value.a) : value)).filter(Boolean);
        const answers = answerSource.map((value) => clean(value && typeof value === "object" ? (value.text ?? value.answer ?? value.a) : value)).filter(Boolean);
        const hasQuiz = Boolean(question && answer && (quizType === "choice" || quizType === "input"));
        if (!title && !body && !main && !children.length && !hasQuiz) {
          return null;
        }
        const payload = {
          title: title || (hasQuiz ? "Question branch" : "Info card"),
          body,
          main,
          children,
        };
        if (answerOption) {
          payload.answer_option = answerOption;
        }
        if (hasQuiz) {
          payload.type = quizType;
          payload.question = question;
          payload.answer = answer;
          if (quizType === "input") {
            const accepted = [];
            const seenAccepted = new Set();
            [answer, ...answers, ...wrong].forEach((value) => {
              const key = questionAnswerKey(value);
              if (value && key && !seenAccepted.has(key)) {
                seenAccepted.add(key);
                accepted.push(value);
              }
            });
            payload.answers = accepted.length ? accepted : [answer];
          } else {
            const answerKey = questionAnswerKey(answer);
            payload.wrong = wrong.filter((value, index, list) => (
              questionAnswerKey(value) !== answerKey
              && list.findIndex((item) => questionAnswerKey(item) === questionAnswerKey(value)) === index
            ));
          }
        }
        return payload;
      };

      const normalizeGuidanceTreePayload = (source) => {
        const data = source && typeof source === "object" ? source : {};
        const rawItems = Array.isArray(data.items) ? data.items : (Array.isArray(data.answers) ? data.answers : []);
        const items = rawItems.map((entry) => {
          const raw = entry && typeof entry === "object" ? entry : {};
          const children = (Array.isArray(raw.children) ? raw.children : (Array.isArray(raw.items) ? raw.items : []))
            .map(normalizeGuidanceTreeNode)
            .filter(Boolean);
          const text = clean(raw.text ?? raw.answer ?? raw.target ?? raw.a ?? "");
          const main = preserveQuestionText(raw.main ?? raw.connector ?? raw.lead ?? raw.m ?? "");
          const quizNode = normalizeGuidanceTreeNode(raw);
          const hasQuiz = Boolean(quizNode && quizNode.question && quizNode.answer && (quizNode.type === "choice" || quizNode.type === "input"));
          if (!text && !main && !children.length && !hasQuiz) {
            return null;
          }
          const payload = { text, main, children };
          if (hasQuiz) {
            payload.type = quizNode.type;
            payload.question = quizNode.question;
            payload.answer = quizNode.answer;
            if (quizNode.type === "input") {
              payload.answers = Array.isArray(quizNode.answers) ? quizNode.answers : [quizNode.answer];
            } else {
              payload.wrong = Array.isArray(quizNode.wrong) ? quizNode.wrong : [];
            }
          }
          return payload;
        }).filter(Boolean);
        return items.length ? { items } : null;
      };

      const normalizeQuestionSelectTargets = (source) => {
        const data = source && typeof source === "object" ? source : {};
        const rootText = preserveQuestionText(data.root_text ?? data.rootText ?? data.text ?? data.target_text ?? data.targetText ?? "");
        const rootRangesRaw = Array.isArray(data.root_ranges ?? data.rootRanges ?? data.root_segments ?? data.rootSegments)
          ? (data.root_ranges ?? data.rootRanges ?? data.root_segments ?? data.rootSegments)
          : [];
        const rootRanges = rootRangesRaw.map((entry) => {
          const raw = entry && typeof entry === "object" ? entry : {};
          return {
            start: Math.max(0, Math.floor(Number(raw.start ?? raw.s ?? 0) || 0)),
            end: Math.max(0, Math.floor(Number(raw.end ?? raw.e ?? 0) || 0)),
            text: preserveQuestionText(raw.text ?? raw.t ?? ""),
          };
        }).filter((entry) => entry.end > entry.start || entry.text);
        const regions = normalizeQuestionPictureRegions(data.regions ?? data.picture_regions ?? data.pictureRegions ?? []);
        const color = optionalQuestionPictureRegionColor(data.region_color ?? data.regionColor ?? data.color ?? data.c);
        const payload = {};
        if (rootText) {
          payload.root_text = rootText;
        }
        if (rootRanges.length) {
          payload.root_ranges = rootRanges;
        }
        if (regions.length) {
          payload.regions = regions;
        }
        if (color) {
          payload.region_color = color;
        }
        return Object.keys(payload).length ? payload : null;
      };

      const normalizeCompactVocabPayload = (payload = {}) => {
        const rawKind = clean(payload.k || payload.kind_key || payload.space || payload.mode || "").toLowerCase();
        const dyn = payload.dyn && typeof payload.dyn === "object" ? payload.dyn : {};
        const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {};
        const lessonId = clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || meta.lesson_id || meta.lessonId);
        const staticAnswer = rawKind === "ftb" || rawKind === "space_b" || clean(payload.mode).toLowerCase() === "static_answer" || dyn.qmdict === false;
        return {
          kind: "future_vocabulary_payload",
          lesson_id: lessonId,
          lessonId,
          identity: lessonId,
          version: Number(payload.v || payload.version || 1) || 1,
          title: clean(payload.t || payload.title || "Future vocabulary"),
          effects: payload.fx || payload.effects || payload.sounds || {},
          study: payload.st || payload.study || {},
          batch: payload.batch || payload.b || {},
          mission: payload.mission || payload.ms || {},
          voices: payload.voices || payload.vc || [],
          static_answer: staticAnswer,
          words: normalizeVocabularyWords(payload.w || payload.words || payload.entries || payload.e || [], { staticAnswer }),
        };
      };

      const normalizeQuestionItem = (item = {}, index = 0) => {
        const raw = item && typeof item === "object" ? item : {};
        const wrong = Array.isArray(raw.wrong || raw.wrongs || raw.options)
          ? (raw.wrong || raw.wrongs || raw.options)
          : [];
        const typeKey = normalizeQuestionType(raw.type || raw.mode || raw.ty);
        const rawAnswerText = preserveQuestionText(raw.answer ?? raw.a ?? raw.correct ?? "");
        const rawSelectTokens = raw.tokens ?? raw.select_tokens ?? raw.selectTokens ?? raw.tk ?? rawAnswerText;
        const selectTokens = typeKey === "select" ? splitQuestionSelectTokens(rawSelectTokens) : [];
        const answer = typeKey === "select" && selectTokens.length ? selectTokens.join(" ") : clean(rawAnswerText);
        const acceptedSource = Array.isArray(raw.answers || raw.accept || raw.accepts)
          ? (raw.answers || raw.accept || raw.accepts)
          : [];
        const questionText = clean(raw.question ?? raw.q ?? raw.prompt ?? "");
        const normalizeQuestionAudioConfig = (source, fallbackMode = "") => {
          const data = source && typeof source === "object" ? source : {};
          const mode = clean(data.mode ?? data.playback ?? fallbackMode).toLowerCase();
          return {
            mode: ["auto", "click", "both"].includes(mode) ? mode : "",
            voice: clean(data.voice ?? data.v ?? ""),
            voice_label: clean(data.voice_label ?? data.label ?? ""),
            mime: clean(data.mime ?? data.m ?? "audio/mpeg"),
            url: clean(data.url ?? data.u ?? data.path ?? ""),
            base64: clean(data.base64 ?? data.b ?? data.data ?? ""),
            text: clean(data.text ?? data.t ?? ""),
            items: Array.isArray(data.items ?? data.i) ? (data.items ?? data.i) : [],
          };
        };
        const normalizeQuestionInfoConfig = (source) => {
          const data = source && typeof source === "object" ? source : {};
          const items = Array.isArray(data.items ?? data.i) ? (data.items ?? data.i) : [];
          return {
            items: items.map((entry) => {
              const item = entry && typeof entry === "object" ? entry : {};
              const mode = clean(item.mode ?? item.info_mode ?? item.m ?? "").toLowerCase();
              return {
                text: clean(item.text ?? item.t ?? item.answer ?? item.a ?? ""),
                info_text: clean(item.info_text ?? item.info ?? item.explain ?? item.explanation ?? ""),
                mode: mode === "audio" ? "audio" : (mode === "type" || mode === "typing" ? "type" : ""),
                voice: clean(item.voice ?? item.v ?? ""),
                voice_label: clean(item.voice_label ?? item.label ?? ""),
                audio: normalizeQuestionAudioConfig(item.audio ?? item.au ?? item.clip ?? item),
              };
            }).filter((entry) => entry.text && entry.info_text),
          };
        };
        const normalizeQuestionRootNoticeTurn = (source) => {
          const data = source && typeof source === "object" ? source : {};
          const english = preserveQuestionText(data.english ?? data.en ?? data.text ?? data.t ?? "");
          const vietnamese = preserveQuestionText(data.vietnamese ?? data.vi ?? data.translation ?? data.v ?? "");
          const audio = normalizeQuestionAudioConfig(data.audio ?? data.au ?? data.clip ?? {});
          const voice = clean(data.voice ?? data.voice_key ?? data.voiceKey ?? data.vk ?? audio.voice ?? "");
          const avatarSource = data.avatar && typeof data.avatar === "object" ? data.avatar : {};
          const avatarUrl = clean(data.avatar_url ?? data.avatarUrl ?? data.avatar_path ?? data.avatarPath ?? data.picture_url ?? data.pictureUrl ?? data.image_url ?? data.imageUrl ?? avatarSource.url ?? "");
          const payload = {
            english,
            vietnamese,
            voice,
            voice_label: clean(data.voice_label ?? data.label ?? audio.voice_label ?? ""),
            speaker: clean(data.speaker ?? data.speaker_name ?? data.speakerName ?? data.character ?? data.character_name ?? data.name ?? ""),
            avatar: avatarUrl ? {
              url: resolveServerAssetUrl(avatarUrl),
              name: clean(avatarSource.name ?? data.avatar_name ?? data.avatarName ?? ""),
            } : null,
            audio,
          };
          return english || vietnamese || audio.url || audio.base64 ? payload : null;
        };
        const normalizeQuestionRootNotice = (source) => {
          const data = source && typeof source === "object" ? source : {};
          const rawTurns = Array.isArray(data.turns) ? data.turns
            : (Array.isArray(data.items) ? data.items
              : (Array.isArray(data.dialogue) ? data.dialogue
                : (Array.isArray(data.dialog) ? data.dialog : [])));
          if (rawTurns.length) {
            const turns = rawTurns.map(normalizeQuestionRootNoticeTurn).filter(Boolean);
            return turns.length ? { turns } : null;
          }
          const turn = normalizeQuestionRootNoticeTurn(data);
          return turn ? {
            english: turn.english,
            vietnamese: turn.vietnamese,
            voice: turn.voice,
            voice_label: turn.voice_label,
            speaker: turn.speaker,
            avatar: turn.avatar,
            audio: turn.audio,
            turns: [turn],
          } : null;
        };
        const normalizeQuestionRootHighlights = (source) => {
          const values = Array.isArray(source) ? source : [];
          return values.map((entry) => {
            const data = entry && typeof entry === "object" ? entry : {};
            const start = Math.max(0, Math.floor(Number(data.start ?? data.s ?? 0) || 0));
            const end = Math.max(0, Math.floor(Number(data.end ?? data.e ?? 0) || 0));
            const color = clean(data.color ?? data.c ?? "");
            const pictureQuestion = questionRootPictureQuestionPayload(data, questionText);
            const item = {
              start,
              end,
              text: preserveQuestionText(data.text ?? data.t ?? ""),
              color: /^#[0-9a-f]{3,8}$/i.test(color) ? color : "#46f0d7",
              style: clean(data.style ?? data.st ?? "style-1") || "style-1",
              render: /^(?:block|box|old|background)$/i.test(clean(data.render ?? data.mode ?? data.m ?? "text")) ? "block" : "text",
              info: preserveQuestionText(data.info ?? data.note ?? data.card ?? data.i ?? ""),
            };
            const focusValue = data.camera_focus ?? data.cameraFocus ?? data.pan_to_highlight ?? data.panToHighlight ?? data.move_view ?? data.moveView ?? data.focus ?? data.pan ?? data.follow ?? data.f ?? data.cf;
            const focusText = typeof focusValue === "string" ? clean(focusValue).toLowerCase() : "";
            const cameraFocus = focusValue === true
              || (typeof focusValue === "number" && focusValue !== 0)
              || ["1", "true", "yes", "y", "on", "checked", "tick", "pan", "focus"].includes(focusText);
            if (cameraFocus) {
              item.camera_focus = true;
            }
            if (pictureQuestion) {
              item.picture_question = pictureQuestion;
            }
            return item;
          }).filter((entry) => entry.end > entry.start || entry.text || entry.picture_question);
        };
        const rawCardMode = raw.card_mode ?? raw.cardMode ?? raw.question_card_mode ?? raw.questionCardMode ?? raw.display_mode ?? raw.displayMode ?? raw.cm;
        const inferredCardMode = normalizeQuestionCardMode(
          rawCardMode,
          normalizeQuestionRootHighlights(raw.root_highlights ?? raw.rootHighlights ?? raw.highlights ?? raw.rh)
            .some((entry) => entry && entry.picture_question) ? "linking" : "question",
        );
        const acceptedPool = typeKey === "select" ? [] : (acceptedSource.length ? acceptedSource : (typeKey === "input" ? wrong : []));
        const acceptedAnswers = [];
        const acceptedKeys = new Set();
        [answer, ...acceptedPool.map((value) => clean(value && typeof value === "object" ? (value.text ?? value.answer ?? value.a) : value))].forEach((value) => {
          const key = questionAnswerKey(value);
          if (value && key && !acceptedKeys.has(key)) {
            acceptedKeys.add(key);
            acceptedAnswers.push(value);
          }
        });
        const filteredWrong = typeKey === "select" ? [] : wrong
          .map((value) => clean(value && typeof value === "object" ? (value.text ?? value.answer ?? value.a) : value))
          .filter((value) => value && !acceptedKeys.has(questionAnswerKey(value)));
        return {
          id: clean(raw.id || raw.i || `q-${index + 1}`),
          type: typeKey,
          card_mode: inferredCardMode,
          order: Math.max(0, Math.floor(Number(raw.order ?? raw.o ?? raw.sort ?? raw.stt ?? 0) || 0)),
          question: questionText,
          answer,
          tokens: selectTokens,
          select_targets: normalizeQuestionSelectTargets(raw.select_targets ?? raw.selectTargets ?? raw.selection_targets ?? raw.selectionTargets ?? raw.stg),
          answers: acceptedAnswers.length ? acceptedAnswers : (answer ? [answer] : []),
          wrong: filteredWrong,
          audio: normalizeQuestionAudioConfig(raw.audio ?? raw.question_audio ?? raw.questionAudio ?? raw.qa),
          answer_audio: normalizeQuestionAudioConfig(raw.answer_audio ?? raw.answerAudio ?? raw.aa),
          answer_info: normalizeQuestionInfoConfig(raw.answer_info ?? raw.answerInfo ?? raw.ai),
          root_highlights: normalizeQuestionRootHighlights(raw.root_highlights ?? raw.rootHighlights ?? raw.highlights ?? raw.rh),
          root_notice: normalizeQuestionRootNotice(raw.root_notice ?? raw.rootNotice ?? raw.notice ?? raw.rn),
          guidance_tree: normalizeGuidanceTreePayload(raw.guidance_tree ?? raw.guidanceTree ?? raw.guide_tree ?? raw.gt),
        };
      };

      const normalizeQuestionNode = (node = {}, index = 0) => {
        const raw = node && typeof node === "object" ? node : {};
        const cards = raw.cards && typeof raw.cards === "object" ? raw.cards : {};
        const rootCard = cards.root && typeof cards.root === "object" ? cards.root : {};
        const picture = cards.picture || raw.picture || raw.pic || null;
        const audio = cards.audio || raw.audio || raw.au || null;
        const questions = cards.questions || raw.questions || raw.qs || [];
        const rootText = preserveQuestionText(raw.root ?? raw.r ?? rootCard.text ?? rootCard.t ?? "");
        const rootFontSize = Math.max(18, Math.min(120, Number(rootCard.font_size ?? rootCard.fontSize ?? rootCard.fs ?? raw.root_font_size ?? raw.rootFontSize ?? raw.rfs ?? 0) || 0));
        const inputTextColor = safeQuestionHexColor(rootCard.input_text_color ?? rootCard.inputTextColor ?? rootCard.itc ?? raw.input_text_color ?? raw.inputTextColor ?? raw.itc, QUESTION_INPUT_DEFAULT_TEXT_COLOR);
        const inputTextPrysm = questionBool(rootCard.input_text_prysm ?? rootCard.inputTextPrysm ?? rootCard.input_prysm ?? rootCard.prysm ?? raw.input_text_prysm ?? raw.inputTextPrysm ?? raw.input_prysm ?? raw.prysm);
        const connectorStyle = clean(raw.connector_style ?? raw.connectorStyle ?? raw.cs ?? rootCard.connector_style ?? rootCard.connectorStyle ?? rootCard.cs ?? "connector-1") || "connector-1";
        const shipType = clean(raw.ship_type ?? raw.shipType ?? raw.st ?? rootCard.ship_type ?? rootCard.shipType ?? rootCard.st ?? "random").toLowerCase() || "random";
        const normalizedShipType = /^ship-[1-5]$/.test(shipType) || shipType === "random" ? shipType : "random";
        return {
          id: clean(raw.id || raw.i || `node-${index + 1}`),
          root: rootText,
          connector_style: /^connector-(?:[1-9]|10)$/.test(connectorStyle) ? connectorStyle : "connector-1",
          ship_type: normalizedShipType,
          cards: {
            root: { text: rootText, font_size: rootFontSize || 0, connector_style: connectorStyle, ship_type: normalizedShipType, input_text_color: inputTextColor, input_text_prysm: inputTextPrysm },
            picture: picture && typeof picture === "object" ? {
              url: clean(picture.url || picture.u || picture.path || ""),
              caption: clean(picture.caption || picture.c || picture.name || ""),
              name: clean(picture.name || ""),
              region_color: safeQuestionPictureRegionColor(picture.region_color ?? picture.regionColor ?? picture.region ?? picture.rc ?? raw.picture_region_color ?? raw.pictureRegionColor),
            } : null,
            audio: audio && typeof audio === "object" ? {
              id: clean(audio.id || audio.i || ""),
              text: clean(audio.text || audio.t || ""),
              voice: clean(audio.voice || audio.v || ""),
              voice_label: clean(audio.voice_label || audio.label || ""),
              mime: clean(audio.mime || audio.m || "audio/mpeg"),
              url: clean(audio.url || audio.u || audio.path || ""),
            } : null,
            questions: (Array.isArray(questions) ? questions : [])
              .map(normalizeQuestionItem)
              .filter((item) => item.question && item.answer),
          },
        };
      };

      const normalizeQuestionPayload = (payload = {}) => ({
        kind: "future_question_payload",
        k: "ftq",
        lesson_id: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
        lessonId: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
        identity: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
        version: Number(payload.v || payload.version || 1) || 1,
        title: clean(payload.t || payload.title || "Future Question"),
        order: clean(payload.order || payload.o || "sequence").toLowerCase() === "shuffle" ? "shuffle" : "sequence",
        effects: payload.fx || payload.effects || payload.sounds || {},
        study: payload.st || payload.study || {},
        rewards: normalizeQuestionRewards(payload.rewards || payload.reward || payload.rw || {}),
        nodes: (Array.isArray(payload.n) ? payload.n : (Array.isArray(payload.nodes) ? payload.nodes : []))
          .map(normalizeQuestionNode)
          .filter((node) => node.root),
      });

      const normalizeParagraphChild = (child = {}, index = 0) => {
        const source = child && typeof child === "object" ? child : {};
        const explanations = Array.isArray(source.explanations || source.exp || source.e)
          ? (source.explanations || source.exp || source.e)
          : [];
        const rawWordNotes = Array.isArray(source.word_notes || source.wordNotes || source.wn)
          ? (source.word_notes || source.wordNotes || source.wn)
          : [];
        const rawWordPos = Array.isArray(source.word_pos || source.wordPos || source.wp)
          ? (source.word_pos || source.wordPos || source.wp)
          : [];
        const rawWordAudio = Array.isArray(source.word_audio || source.wordAudio || source.wa)
          ? (source.word_audio || source.wordAudio || source.wa)
          : [];
        return {
          id: clean(source.id || source.i || `child-${index + 1}`),
          text: clean(source.text || source.en || source.t),
          meaning: clean(source.meaning || source.vi || source.m),
          audio: source.audio && typeof source.audio === "object" ? source.audio : null,
          alt_audio: source.alt_audio && typeof source.alt_audio === "object"
            ? source.alt_audio
            : (source.altAudio && typeof source.altAudio === "object"
              ? source.altAudio
              : (source.audio_alt && typeof source.audio_alt === "object"
                ? source.audio_alt
                : (source.audioAlt && typeof source.audioAlt === "object" ? source.audioAlt : null))),
          meaning_audio: source.meaning_audio && typeof source.meaning_audio === "object"
            ? source.meaning_audio
            : (source.vi_audio && typeof source.vi_audio === "object" ? source.vi_audio : null),
          ipa: clean(source.ipa || source.i || source.phonetic_ipa || source.phoneticIpa || source.phonetic || source.pronunciation || ""),
          ipa_us: clean(source.ipa_us || source.ipaUS || source.iu || source.ius || source.us_ipa || source.usIpa || ""),
          ipa_uk: clean(source.ipa_uk || source.ipaUK || source.ik || source.iuk || source.uk_ipa || source.ukIpa || ""),
          explanations: explanations
            .map((item, expIndex) => {
              const exp = item && typeof item === "object" ? item : { text: item };
              return {
                title: clean(exp.title || exp.t || `Explanation ${expIndex + 1}`),
                text: clean(exp.text || exp.body || exp.b || exp.content),
              };
            })
            .filter((item) => item.title || item.text),
          word_notes: rawWordNotes
            .map((item, noteIndex) => {
              const note = item && typeof item === "object" ? item : {};
              const noteIndexValue = Number(note.index ?? note.token_index ?? note.tokenIndex ?? noteIndex);
              return {
                index: Math.max(0, Math.floor(Number.isFinite(noteIndexValue) ? noteIndexValue : noteIndex)),
                word: clean(note.word || note.token || note.w),
                meaning_note: preserveQuestionText(note.meaning_note ?? note.meaningNote ?? note.meaning ?? note.m ?? ""),
                grammar_note: preserveQuestionText(note.grammar_note ?? note.grammarNote ?? note.grammar ?? note.g ?? ""),
              };
            })
            .filter((item) => item.word || item.meaning_note || item.grammar_note),
          word_pos: rawWordPos
            .map((item, posIndex) => {
              const pos = item && typeof item === "object" ? item : {};
              const posIndexValue = Number(pos.index ?? pos.token_index ?? pos.tokenIndex ?? pos.i ?? posIndex);
              return {
                index: Math.max(0, Math.floor(Number.isFinite(posIndexValue) ? posIndexValue : posIndex)),
                word: clean(pos.word || pos.token || pos.t || pos.w),
                pos: clean(pos.pos || pos.p).toUpperCase(),
                tag: clean(pos.tag || pos.tg),
                lemma: clean(pos.lemma || pos.l),
                dep: clean(pos.dep || pos.d),
                head: clean(pos.head || pos.h),
                ipa: clean(pos.ipa || pos.i || pos.phonetic || pos.pronunciation || ""),
                ipa_us: clean(pos.ipa_us || pos.ipaUS || pos.iu || pos.ius || pos.us_ipa || pos.usIpa || ""),
                ipa_uk: clean(pos.ipa_uk || pos.ipaUK || pos.ik || pos.iuk || pos.uk_ipa || pos.ukIpa || ""),
              };
            })
            .filter((item) => item.word || item.pos || item.tag || item.lemma || item.dep || item.head || item.ipa || item.ipa_us || item.ipa_uk),
          word_audio: rawWordAudio
            .map((item, audioIndex) => {
              const audio = item && typeof item === "object" ? item : {};
              const audioIndexValue = Number(audio.index ?? audio.token_index ?? audio.tokenIndex ?? audio.i ?? audioIndex);
              return {
                index: Math.max(0, Math.floor(Number.isFinite(audioIndexValue) ? audioIndexValue : audioIndex)),
                word: clean(audio.word || audio.token || audio.t || audio.w),
                url: clean(audio.url || audio.u || audio.src),
                mime: clean(audio.mime || audio.m || "audio/mpeg"),
                voice: clean(audio.voice || audio.v || "sot:en-GB"),
                source: clean(audio.source || audio.origin || audio.s),
              };
            })
            .filter((item) => item.word || item.url),
        };
      };

      const normalizeParagraphPayload = (payload = {}) => {
        const rawNodes = Array.isArray(payload.nodes)
          ? payload.nodes
          : (Array.isArray(payload.n) ? payload.n : []);
        const nodes = rawNodes
          .map((node, index) => {
            const source = node && typeof node === "object" ? node : {};
            const children = (Array.isArray(source.children || source.c) ? (source.children || source.c) : [])
              .map(normalizeParagraphChild)
              .filter((child) => child.text && child.meaning);
            const text = clean(source.text || source.root || source.r || source.t) || children.map((child) => child.text).join(" ");
            return {
              id: clean(source.id || source.i || `pnode-${index + 1}`),
              title: clean(source.title || source.name || source.tt || `Paragraph Node ${index + 1}`),
              text,
              voice: clean(source.voice || source.vc || payload.voice || payload.vc || "kokoro:am_adam"),
              vi_voice: clean(source.vi_voice || source.viVoice || source.vv || payload.vi_voice || payload.viVoice || "edge:vi-VN-NamMinhNeural"),
              alt_voice: clean(source.alt_voice || source.altVoice || source.av || payload.alt_voice || payload.altVoice || "kokoro:af_jessica"),
              ipa: clean(source.ipa || source.i || source.phonetic_ipa || source.phoneticIpa || source.phonetic || ""),
              ipa_us: clean(source.ipa_us || source.ipaUS || source.iu || source.ius || source.us_ipa || source.usIpa || ""),
              ipa_uk: clean(source.ipa_uk || source.ipaUK || source.ik || source.iuk || source.uk_ipa || source.ukIpa || ""),
              children,
            };
          })
          .filter((node) => node.children.length);
        return {
          kind: "future_paragraph_payload",
          k: "ftp",
          lesson_id: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
          lessonId: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
          identity: clean(payload.lesson_id || payload.lessonId || payload.identity || payload.lesson || (payload.meta && (payload.meta.lesson_id || payload.meta.lessonId))),
          space_mode: ["space_s", "space_l"].includes(clean(payload.space_mode || payload.spaceMode || payload.mode || payload.sm || "").toLowerCase())
            ? clean(payload.space_mode || payload.spaceMode || payload.mode || payload.sm || "").toLowerCase()
            : "space_p",
          format: clean(payload.format || payload.fmt || ""),
          version: Number(payload.version || payload.v || 1) || 1,
          title: clean(payload.title || payload.t || "Future Paragraph Rewrite") || "Future Paragraph Rewrite",
          effects: payload.fx || payload.effects || payload.sounds || {},
          hint_seconds: Math.max(3, Math.min(300, Number(payload.hint_seconds || payload.hintSeconds || payload.hint || 30) || 30)),
          nodes,
          study: payload.study || payload.st || {},
        };
      };

      const resolveServerAssetUrl = (path) => {
        const rawPath = clean(path).replace(/\\/g, "/");
        if (!rawPath) {
          return "";
        }
        if (/^https?:\/\//i.test(rawPath) || rawPath.startsWith("data:") || rawPath.startsWith("blob:")) {
          return rawPath;
        }
        const base = WHISPER_SERVER_CANDIDATES[0] || WHISPER_SERVER_URL || window.location.origin;
        if (rawPath.startsWith("/")) {
          return `${base}${rawPath}`;
        }
        const raw = rawPath.replace(/^\/+/, "");
        return `${base}/server-data/asset?path=${encodeURIComponent(raw)}`;
      };

      const futureStructureTextCache = new Map();

      // 2026-07-20: Share immutable hash-named Structure loads across concurrent Space boot paths.
      const loadFutureStructureText = (structurePath) => {
        const assetUrl = resolveServerAssetUrl(structurePath);
        const cached = futureStructureTextCache.get(assetUrl);
        if (cached) {
          futureStructureTextCache.delete(assetUrl);
          futureStructureTextCache.set(assetUrl, cached);
          return cached;
        }
        const pending = fetch(assetUrl, { cache: "no-store" })
          .then(async (response) => {
            if (!response.ok) {
              throw new Error(`Không tải được Structure: ${response.status}`);
            }
            return decodeUtf8Buffer(await response.arrayBuffer());
          })
          .catch((error) => {
            futureStructureTextCache.delete(assetUrl);
            throw error;
          });
        futureStructureTextCache.set(assetUrl, pending);
        while (futureStructureTextCache.size > 24) {
          futureStructureTextCache.delete(futureStructureTextCache.keys().next().value);
        }
        return pending;
      };

      const decodeFuturePayload = async (rawCode) => {
        const rawText = String(rawCode || "").trim();
        if (rawText.startsWith("{")) {
          const manifest = JSON.parse(rawText);
          if (manifest && manifest.k === "ftg_manifest" && manifest.structure) {
            return decodeFuturePayload(await loadFutureStructureText(manifest.structure));
          }
          if (manifest && manifest.k === "ftg" && Array.isArray(manifest.n)) {
            return normalizeCompactFuturePayload(manifest);
          }
          if (manifest && (manifest.k === "ftv" || manifest.k === "ftb") && Array.isArray(manifest.w)) {
            return normalizeCompactVocabPayload(manifest);
          }
          if (manifest && manifest.k === "ftq" && Array.isArray(manifest.n)) {
            return normalizeQuestionPayload(manifest);
          }
          if (manifest && manifest.k === "ftp" && Array.isArray(manifest.nodes || manifest.n)) {
            return normalizeParagraphPayload(manifest);
          }
          if (manifest && manifest.kind === "future_vocabulary_payload") {
            return normalizeCompactVocabPayload(manifest);
          }
          if (manifest && manifest.kind === "future_question_payload" && Array.isArray(manifest.nodes)) {
            return normalizeQuestionPayload(manifest);
          }
          if (manifest && manifest.kind === "future_paragraph_payload" && Array.isArray(manifest.nodes)) {
            return normalizeParagraphPayload(manifest);
          }
          if (manifest && manifest.kind === "future_translation_payload" && Array.isArray(manifest.nodes)) {
            return {
              ...manifest,
              effects: manifest.effects || manifest.sounds || manifest.fx || {},
              study: manifest.study || manifest.st || {},
            };
          }
        }
        const code = rawText.replace(/\s+/g, "").trim();
        if (!code.startsWith("FTG1.")) {
          throw new Error("File chưa đúng định dạng FTG1.");
        }
        const compressed = decodeBase64Url(code.slice(5));
        const bytes = await gunzipBytes(compressed);
        const payload = JSON.parse(new TextDecoder("utf-8").decode(bytes));
        if (payload && payload.kind === "future_translation_payload" && Array.isArray(payload.nodes)) {
          return {
            ...payload,
            effects: payload.effects || payload.sounds || payload.fx || {},
            study: payload.study || payload.st || {},
          };
        }
        if (payload && payload.k === "ftg" && Array.isArray(payload.n)) {
          return normalizeCompactFuturePayload(payload);
        }
        if (payload && (payload.k === "ftv" || payload.k === "ftb") && Array.isArray(payload.w)) {
          return normalizeCompactVocabPayload(payload);
        }
        if (payload && payload.k === "ftq" && Array.isArray(payload.n)) {
          return normalizeQuestionPayload(payload);
        }
        if (payload && payload.k === "ftp" && Array.isArray(payload.nodes || payload.n)) {
          return normalizeParagraphPayload(payload);
        }
        if (payload && payload.kind === "future_vocabulary_payload") {
          return normalizeCompactVocabPayload(payload);
        }
        if (payload && payload.kind === "future_question_payload" && Array.isArray(payload.nodes)) {
          return normalizeQuestionPayload(payload);
        }
        if (payload && payload.kind === "future_paragraph_payload" && Array.isArray(payload.nodes)) {
          return normalizeParagraphPayload(payload);
        }
        throw new Error("File không chứa dữ liệu future hợp lệ.");
      };

      const clearHighlight = () => {
        if (highlightFrame) {
          window.cancelAnimationFrame(highlightFrame);
          highlightFrame = 0;
        }
        if (highlightTimer) {
          window.clearTimeout(highlightTimer);
          highlightTimer = 0;
        }
        englishNode.querySelectorAll(".ft-word.is-reading").forEach((node) => node.classList.remove("is-reading"));
        ipaNode.querySelectorAll(".ft-ipa-token.is-reading").forEach((node) => node.classList.remove("is-reading"));
      };

      const tokenIpaForAccent = (token, accent = currentAccent) => {
        const wantsUk = accent === "uk";
        return clean(
          wantsUk
            ? (token?.ipa_uk ?? token?.iuk ?? token?.ik ?? token?.uk ?? token?.ipa ?? token?.i ?? "")
            : (token?.ipa_us ?? token?.ius ?? token?.iu ?? token?.us ?? token?.ipa ?? token?.i ?? ""),
        );
      };

      const nodeIpaForAccent = (node, fallback = "", accent = currentAccent) => {
        const wantsUk = accent === "uk";
        return clean(
          wantsUk
            ? (node?.ipa_uk ?? node?.iuk ?? node?.ik ?? node?.uk_ipa ?? node?.ipa ?? node?.i ?? fallback)
            : (node?.ipa_us ?? node?.ius ?? node?.iu ?? node?.us_ipa ?? node?.ipa ?? node?.i ?? fallback),
        ) || clean(fallback);
      };

      const voiceAccentFromText = (value) => {
        const raw = clean(value).toLowerCase();
        if (/(female-uk|en-gb|en_gb|\buk\b|\bgb\b|british|sonia|ryan|edge:en-gb|sot:en-gb|kokoro:b[fm]_)/.test(raw)) {
          return "uk";
        }
        return "us";
      };

      const selectedVoiceAccent = () => {
        const option = voiceSelect.options[voiceSelect.selectedIndex];
        const selectedText = option?.textContent || "";
        const embeddedVoice = option?.dataset?.voice || "";
        return voiceAccentFromText(`${voiceSelect.value} ${selectedText} ${embeddedVoice} ${voiceHint}`);
      };

      const updateVoiceSelectTone = () => {
        const embedded = String(voiceSelect.value || "").startsWith("embedded:");
        voiceSelect.classList.toggle("is-embedded-selected", embedded);
        if (voiceShell) {
          voiceShell.classList.toggle("is-embedded-selected", embedded);
        }
        if (loadVoiceShell) {
          loadVoiceShell.classList.toggle("is-embedded-selected", embedded);
        }
        updateVoiceProxyLabel();
      };

      const applySelectedVoiceValue = (value) => {
        const selected = clean(value);
        if (selected && Array.from(voiceSelect.options).some((option) => option.value === selected)) {
          voiceSelect.value = selected;
        }
        voiceHint = voiceSelect.options[voiceSelect.selectedIndex]?.textContent || voiceSelect.value || voiceHint;
        updateVoiceSelectTone();
        refreshIpaForAccent(selectedVoiceAccent());
        setTtsStatus(listenStatusText());
      };

      const isMobileVoicePicker = () => window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
      const isMobileVoiceList = () => window.matchMedia("(max-width: 760px)").matches;
      const isPopupFullscreenMode = () => document.documentElement.classList.contains("ft-popup-fullscreen");
      const canShowDirectOnlineVoices = () => !isMobileVoiceList();
      let lastVoiceListMode = "";
      let loadVoiceLockedLabel = "";

      const updateVoiceProxyLabel = () => {
        if (!voiceSelect) {
          return;
        }
        const selected = voiceSelect.options[voiceSelect.selectedIndex];
        const label = clean(selected && selected.textContent) || "Browser English voice";
        const proxyLabel = loadVoiceLockedLabel || label;
        if (voiceProxyText) {
          voiceProxyText.textContent = proxyLabel;
        }
        if (loadVoiceProxyText) {
          loadVoiceProxyText.textContent = proxyLabel;
        }
      };

      const paragraphVoiceDisplayLabel = (voiceKey = "") => {
        const key = clean(voiceKey).toLowerCase();
        if (key === "kokoro:am_adam") {
          return "People | Male Adam";
        }
        if (key === "kokoro:af_jessica") {
          return "People | Female Jessica";
        }
        if (key.startsWith("kokoro:")) {
          return `People | ${clean(voiceKey).replace(/^kokoro:/i, "")}`;
        }
        if (key.startsWith("edge:vi-vn-namminhneural")) {
          return "Edge | Vietnamese VN | Nam Minh";
        }
        return clean(voiceKey) || "People | Male Adam";
      };

      const paragraphPayloadVoiceLabel = (payload = null) => {
        const node = payload && Array.isArray(payload.nodes) ? payload.nodes[0] : null;
        const child = node && Array.isArray(node.children) ? node.children[0] : null;
        const clip = child && child.audio && typeof child.audio === "object" ? child.audio : null;
        const voice = clean((clip && clip.voice) || (node && node.voice) || (payload && (payload.voice || payload.vc)) || "kokoro:am_adam");
        return `${paragraphVoiceDisplayLabel(voice)} | embedded Space_P audio`;
      };

      const setLoadVoiceLock = (locked = false, label = "") => {
        loadVoiceLockedLabel = locked ? clean(label) : "";
        if (loadVoiceShell) {
          loadVoiceShell.classList.toggle("is-locked-voice", Boolean(loadVoiceLockedLabel));
        }
        if (loadVoiceProxy) {
          loadVoiceProxy.disabled = Boolean(loadVoiceLockedLabel);
          loadVoiceProxy.setAttribute("aria-disabled", loadVoiceLockedLabel ? "true" : "false");
        }
        if (loadVoiceLockedLabel) {
          closeVoicePicker();
        }
        updateVoiceProxyLabel();
      };

      const pickerClassForOption = (option) => {
        if (!option) {
          return "";
        }
        if (option.classList.contains("ft-embedded-option")) {
          return "is-embedded";
        }
        if (option.classList.contains("ft-sot-option")) {
          return "is-sot";
        }
        if (option.classList.contains("ft-microsoft-option")) {
          return "is-microsoft";
        }
        return "";
      };

      const addPickerOption = (option) => {
        if (!voicePickerList || !option || option.disabled) {
          return;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = `ft-voice-choice ${pickerClassForOption(option)}`.trim();
        if (option.value === voiceSelect.value) {
          button.classList.add("is-active");
        }
        button.dataset.value = option.value;
        button.setAttribute("role", "option");
        button.setAttribute("aria-selected", option.value === voiceSelect.value ? "true" : "false");
        button.innerHTML = `<span class="ft-voice-choice-dot" aria-hidden="true"></span><span class="ft-voice-choice-text"></span>`;
        button.querySelector(".ft-voice-choice-text").textContent = clean(option.textContent) || "Voice";
        button.addEventListener("click", () => {
          voiceSelect.value = option.value;
          voiceSelect.dispatchEvent(new Event("change", { bubbles: true }));
          closeVoicePicker();
        });
        voicePickerList.appendChild(button);
      };

      const buildVoicePicker = () => {
        if (!voicePickerList) {
          return;
        }
        voicePickerList.innerHTML = "";
        Array.from(voiceSelect.children).forEach((child) => {
          if (child.tagName === "OPTGROUP") {
            const options = Array.from(child.children).filter((option) => !option.disabled);
            if (!options.length) {
              return;
            }
            const group = document.createElement("div");
            group.className = "ft-voice-picker-group";
            group.textContent = child.label || "Voices";
            voicePickerList.appendChild(group);
            options.forEach(addPickerOption);
            return;
          }
          if (child.tagName === "OPTION") {
            addPickerOption(child);
          }
        });
      };

      let voicePickerCloseTimer = 0;

      const openVoicePicker = (force = false) => {
        if (loadVoiceLockedLabel) {
          return false;
        }
        if (!voicePicker || (!force && !isMobileVoicePicker())) {
          return false;
        }
        loadVoices();
        if (voicePickerCloseTimer) {
          window.clearTimeout(voicePickerCloseTimer);
          voicePickerCloseTimer = 0;
        }
        buildVoicePicker();
        voicePicker.classList.remove("is-closing");
        voicePicker.classList.add("is-open");
        voicePicker.setAttribute("aria-hidden", "false");
        if (voiceProxy) {
          voiceProxy.setAttribute("aria-expanded", "true");
        }
        if (loadVoiceProxy) {
          loadVoiceProxy.setAttribute("aria-expanded", "true");
        }
        const activeChoice = voicePickerList && voicePickerList.querySelector(".ft-voice-choice.is-active");
        if (activeChoice) {
          window.setTimeout(() => activeChoice.scrollIntoView({ block: "nearest" }), 40);
        }
        return true;
      };

      const closeVoicePicker = () => {
        if (!voicePicker || !voicePicker.classList.contains("is-open")) {
          return;
        }
        voicePicker.classList.remove("is-open");
        voicePicker.classList.add("is-closing");
        voicePicker.setAttribute("aria-hidden", "true");
        if (voiceProxy) {
          voiceProxy.setAttribute("aria-expanded", "false");
        }
        if (loadVoiceProxy) {
          loadVoiceProxy.setAttribute("aria-expanded", "false");
        }
        if (voicePickerCloseTimer) {
          window.clearTimeout(voicePickerCloseTimer);
        }
        voicePickerCloseTimer = window.setTimeout(() => {
          voicePicker.classList.remove("is-closing");
          voicePickerCloseTimer = 0;
        }, 190);
      };

      const renderEnglish = (text, tokens = [], accent = currentAccent) => {
        const rawText = String(text || "");
        const cleanTokens = Array.isArray(tokens) ? tokens : [];
        englishNode.textContent = "";
        if (!cleanTokens.length) {
          englishNode.textContent = rawText;
          return;
        }
        let cursor = 0;
        cleanTokens.forEach((token, index) => {
          const start = Math.max(0, Number(token.start ?? token.s ?? cursor) || 0);
          const end = Math.max(start, Number(token.end ?? token.e ?? start) || start);
          if (start > cursor) {
            englishNode.appendChild(document.createTextNode(rawText.slice(cursor, start)));
          }
          const span = document.createElement("span");
          span.className = "ft-word";
          span.dataset.tokenIndex = String(index);
          span.dataset.ipa = tokenIpaForAccent(token, accent);
          span.dataset.ipaUs = tokenIpaForAccent(token, "us");
          span.dataset.ipaUk = tokenIpaForAccent(token, "uk");
          span.title = clean(span.dataset.ipa || token.lemma || token.l || "");
          span.textContent = rawText.slice(start, end) || clean(token.text ?? token.t);
          englishNode.appendChild(span);
          cursor = end;
        });
        if (cursor < rawText.length) {
          englishNode.appendChild(document.createTextNode(rawText.slice(cursor)));
        }
      };

      const renderIpa = (text, tokens = [], accent = currentAccent) => {
        const rawText = clean(text);
        const cleanTokens = Array.isArray(tokens) ? tokens : [];
        const tokenIpas = cleanTokens
          .map((token, index) => ({
            index,
            ipa: tokenIpaForAccent(token, accent),
            text: clean(token.text ?? token.t ?? ""),
          }))
          .filter((item) => item.ipa);
        ipaNode.textContent = "";
        if (!tokenIpas.length) {
          ipaNode.textContent = rawText;
          return;
        }
        ipaNode.appendChild(document.createTextNode("/"));
        tokenIpas.forEach((item, order) => {
          if (order) {
            ipaNode.appendChild(document.createTextNode(" "));
          }
          const span = document.createElement("span");
          span.className = "ft-ipa-token";
          span.dataset.tokenIndex = String(item.index);
          span.title = item.text;
          span.textContent = item.ipa;
          ipaNode.appendChild(span);
        });
        ipaNode.appendChild(document.createTextNode("/"));
      };

      const refreshIpaForAccent = (accent = selectedVoiceAccent()) => {
        if (!currentNode) {
          return;
        }
        currentAccent = accent === "uk" ? "uk" : "us";
        const en = clean(currentNode.en ?? currentNode.e ?? englishNode.textContent) || defaults.en;
        const fallbackIpa = clean(currentNode.ipa ?? currentNode.i ?? ipaNode.textContent) || defaults.ipa;
        const tokens = currentNode.tokens ?? currentNode.tk ?? [];
        renderEnglish(en, tokens, currentAccent);
        renderIpa(nodeIpaForAccent(currentNode, fallbackIpa, currentAccent), tokens, currentAccent);
      };

      const edgePrettyName = (shortName) => {
        const raw = clean(shortName);
        const suffix = raw.split("-").pop() || raw;
        return suffix.replace(/Neural$/i, "").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim() || raw;
      };

      const edgeRegionLabel = (locale) => {
        const raw = clean(locale);
        const region = raw.split("-")[1] || "";
        return `English ${region.toUpperCase() || raw || "US"}`.trim();
      };

      const edgeLabel = (name, locale) => `Edge | ${edgeRegionLabel(locale)} | ${edgePrettyName(name)}`;
      const microsoftLabel = (name, locale) => `Microsoft | ${edgeRegionLabel(locale)} | ${edgePrettyName(name)}`;

      const normalizeEdgeRecord = (record) => {
        const name = clean(record && (record.ShortName || record.shortName || record.name));
        const locale = clean(record && (record.Locale || record.locale)) || name.split("-").slice(0, 2).join("-") || "en-US";
        if (!name || !locale.toLowerCase().startsWith("en")) {
          return null;
        }
        return {
          label: edgeLabel(name, locale),
          name,
          locale,
          gender: clean(record && (record.Gender || record.gender)) || (/\b(guy|davis|ryan)\b/i.test(name) ? "Male" : "Female"),
        };
      };

      const edgeSortKey = (voice) => `${voice.locale}|${voice.gender === "Female" ? "0" : "1"}|${voice.label}`;

      const loadEdgeVoiceCatalog = async () => {
        if (edgeCatalogRequested) {
          return;
        }
        edgeCatalogRequested = true;
        try {
          const response = await fetch(EDGE_VOICE_LIST_URL, { headers: { "Accept": "application/json" } });
          if (!response.ok) {
            return;
          }
          const records = await response.json();
          const seen = new Set();
          const voices = [];
          for (const record of Array.isArray(records) ? records : []) {
            const voice = normalizeEdgeRecord(record);
            if (!voice || seen.has(voice.name.toLowerCase())) {
              continue;
            }
            seen.add(voice.name.toLowerCase());
            voices.push(voice);
          }
          if (voices.length) {
            edgeVoices = voices.sort((a, b) => edgeSortKey(a).localeCompare(edgeSortKey(b)));
            loadVoices();
          }
        } catch (error) {
          edgeVoices = edgeVoiceDefaults.slice();
        }
      };

      const isEnglishVoice = (voice) => {
        const lang = String(voice.lang || "").toLowerCase();
        const name = String(voice.name || "").toLowerCase();
        return lang.startsWith("en") || name.includes("english");
      };

      const voiceRank = (voice) => {
        const name = String(voice.name || "").toLowerCase();
        const lang = String(voice.lang || "").toLowerCase();
        let score = 0;
        if (name.includes("microsoft")) score -= 40;
        if (name.includes("natural")) score -= 30;
        if (name.includes("aria")) score -= 18;
        if (name.includes("jenny")) score -= 16;
        if (name.includes("sonia")) score -= 14;
        if (name.includes("guy")) score -= 12;
        if (lang === "en-us") score -= 8;
        if (lang.startsWith("en-")) score -= 4;
        return score;
      };

      const normalizeVoiceHint = (value) => clean(value).toLowerCase();

      const optionText = (option) => `${option.value} ${option.textContent}`.toLowerCase();

      const findOption = (options, predicate) => options.find((option) => predicate(optionText(option), option));

      const canonicalVoiceKey = (value) => {
        const raw = clean(value).toLowerCase();
        if (!raw) {
          return "";
        }
        const stripped = raw.replace(/^embedded:/, "");
        if (stripped.startsWith("sot:")) {
          return `sot:${stripped.split(":", 2)[1] || ""}`;
        }
        if (stripped.startsWith("soundoftext:")) {
          return `sot:${stripped.split(":", 2)[1] || ""}`;
        }
        if (stripped.startsWith("edge:") || stripped.startsWith("microsoft:")) {
          return `microsoft:${stripped.split(":", 2)[1] || ""}`;
        }
        if (stripped === "female-us" || stripped === "us" || stripped === "en-us") {
          return "sot:en-us";
        }
        if (stripped === "female-uk" || stripped === "uk" || stripped === "en-gb") {
          return "sot:en-gb";
        }
        return stripped;
      };

      const isCachedSoundOfText = (asset) => {
        const key = canonicalVoiceKey(asset && asset.voice);
        const label = clean(asset && asset.label).toLowerCase();
        return key.startsWith("sot:") || label.includes("sound of text") || label.includes("sot |");
      };

      const preferredVoiceOption = (options, previousValue) => {
        const hint = normalizeVoiceHint(voiceHint);
        const previous = clean(previousValue);
        const cloudMatch = /(?:edge|microsoft):([a-z]{2}-[a-z]{2}-[a-z0-9-]+)/i.exec(hint);
        const hintedCloudName = cloudMatch ? clean(cloudMatch[1]).toLowerCase() : "";
        const kokoroUk = /kokoro:bm_|kokoro:bf_/.test(hint);
        const kokoroUs = /kokoro:am_|kokoro:af_/.test(hint);
        const wantsUk = kokoroUk || /\b(female-uk|en-gb|uk|gb|british|sonia|ryan)\b/.test(hint);
        const wantsUs = kokoroUs || /\b(female-us|male-us|en-us|us|american|aria|jenny|guy|davis)\b/.test(hint);
        const wantsMale = /kokoro:[ab]m_/.test(hint) || /\b(male-us|guy|davis|ryan|male)\b/.test(hint);
        const wantsFemale = /kokoro:[ab]f_/.test(hint) || /\b(female-uk|female-us|aria|jenny|sonia|female)\b/.test(hint);
        const isSotUkOption = (option) => /sot:en-gb|female uk|sound of text.*uk/i.test(`${option.value || ""} ${option.dataset?.voice || ""} ${option.textContent || ""}`);
        const isSotUsOption = (option) => /sot:en-us|female us|sound of text.*us/i.test(`${option.value || ""} ${option.dataset?.voice || ""} ${option.textContent || ""}`);

        return options.find((option) => option.value === previous) ||
          findOption(options, (text) => hint && text.includes(hint)) ||
          (hintedCloudName && findOption(options, (_text, option) => canonicalVoiceKey(option.value).endsWith(hintedCloudName))) ||
          (wantsUk && findOption(options, (_text, option) => isSotUkOption(option))) ||
          (wantsUs && findOption(options, (_text, option) => isSotUsOption(option))) ||
          (wantsUk && findOption(options, (text, option) => option.value.startsWith("microsoft:") && text.includes("en-gb"))) ||
          (wantsUs && wantsMale && findOption(options, (text, option) => option.value.startsWith("microsoft:") && (text.includes("guy") || text.includes("davis") || text.includes("ryan") || text.includes("male")))) ||
          (wantsUs && wantsFemale && findOption(options, (text, option) => option.value.startsWith("microsoft:") && (text.includes("aria") || text.includes("jenny") || text.includes("female")))) ||
          (wantsUk && findOption(options, (text, option) => option.value === "sot:en-GB" || (option.value.startsWith("browser:") && text.includes("en-gb")))) ||
          (wantsUs && wantsMale && findOption(options, (text, option) => option.value.startsWith("browser:") && (text.includes("guy") || text.includes("davis") || text.includes("david") || text.includes("mark") || text.includes("male")))) ||
          (wantsUs && wantsFemale && findOption(options, (text, option) => option.value === "sot:en-US" || (option.value.startsWith("browser:") && (text.includes("aria") || text.includes("jenny") || text.includes("zira") || text.includes("female"))))) ||
          (wantsUs && findOption(options, (text, option) => option.value.startsWith("browser:") && text.includes("en-us"))) ||
          (wantsUk && findOption(options, (text, option) => option.value.startsWith("browser:") && text.includes("english"))) ||
          findOption(options, (_text, option) => isSotUkOption(option)) ||
          findOption(options, (_text, option) => isSotUsOption(option)) ||
          findOption(options, (text, option) => option.value.startsWith("browser:") && text.includes("english")) ||
          options[0];
      };

      const loadVoices = () => {
        const previousValue = voiceSelect.value;
        const voiceListMode = isMobileVoiceList() ? "mobile" : "desktop";
        const showDirectOnlineVoices = canShowDirectOnlineVoices();
        const allVoices = "speechSynthesis" in window ? window.speechSynthesis.getVoices() : [];
        speechVoices = allVoices.filter(isEnglishVoice).sort((a, b) => {
          const englishRank = Number(!isEnglishVoice(a)) - Number(!isEnglishVoice(b));
          const ranked = voiceRank(a) - voiceRank(b);
          const langRank = String(a.lang || "").localeCompare(String(b.lang || ""));
          return englishRank || ranked || langRank || String(a.name).localeCompare(String(b.name));
        });

        voiceSelect.innerHTML = "";
        const rawEmbeddedAssets = getEmbeddedAudioAssets().map((asset, index) => ({ ...asset, __index: index }));
        const cachedKeys = new Set();
        const cachedSoundOfText = [];
        const cachedOtherAudio = [];
        rawEmbeddedAssets.forEach((asset) => {
          const identity = canonicalVoiceKey(asset.voice || asset.id || asset.__index) || `asset:${asset.id || asset.__index}`;
          if (cachedKeys.has(identity)) {
            return;
          }
          cachedKeys.add(identity);
          if (isCachedSoundOfText(asset)) {
            cachedSoundOfText.push(asset);
          } else {
            cachedOtherAudio.push(asset);
          }
        });

        const appendCachedGroup = (label, assets) => {
          if (!assets.length) {
            return;
          }
          const embeddedGroup = document.createElement("optgroup");
          embeddedGroup.label = label;
          embeddedGroup.className = "ft-voice-group ft-voice-group-embedded";
          assets.forEach((asset) => {
            const option = document.createElement("option");
            option.value = `embedded:${asset.voice || asset.id || asset.__index}`;
            option.textContent = `Cached | ${asset.label}`;
            option.className = "ft-embedded-option";
            option.dataset.voice = asset.voice || "";
            embeddedGroup.appendChild(option);
          });
          voiceSelect.appendChild(embeddedGroup);
        };

        appendCachedGroup("Cached Sound of Text", cachedSoundOfText);
        appendCachedGroup("Cached audio in lesson pack", cachedOtherAudio);

        const sotGroup = document.createElement("optgroup");
        sotGroup.label = "Sound of Text";
        sotGroup.className = "ft-voice-group ft-voice-group-sot";
        soundOfTextVoices.forEach(([label, voice]) => {
          const value = `sot:${voice}`;
          if (cachedKeys.has(canonicalVoiceKey(value))) {
            return;
          }
          const option = document.createElement("option");
          option.value = value;
          option.textContent = `${label} (${voice})`;
          option.className = "ft-sot-option";
          sotGroup.appendChild(option);
        });
        if (sotGroup.children.length) {
          voiceSelect.appendChild(sotGroup);
        }

        if (showDirectOnlineVoices) {
          const microsoftGroup = document.createElement("optgroup");
          microsoftGroup.label = "Microsoft online";
          microsoftGroup.className = "ft-voice-group ft-voice-group-microsoft";
          if (edgeVoices.length) {
            edgeVoices.forEach((voice) => {
              const value = `microsoft:${voice.name}`;
              if (cachedKeys.has(canonicalVoiceKey(value))) {
                return;
              }
              const option = document.createElement("option");
              option.value = value;
              option.textContent = `${microsoftLabel(voice.name, voice.locale)} (${voice.name})`;
              option.className = "ft-microsoft-option";
              microsoftGroup.appendChild(option);
            });
          }
          if (microsoftGroup.children.length) {
            voiceSelect.appendChild(microsoftGroup);
          }
        }

        if (speechVoices.length) {
          const browserGroup = document.createElement("optgroup");
          browserGroup.label = "Browser English voices";
          browserGroup.className = "ft-voice-group ft-voice-group-browser";
          speechVoices.forEach((voice, index) => {
            const option = document.createElement("option");
            option.value = `browser:${index}`;
            option.textContent = `${voice.name} (${voice.lang || "unknown"})`;
            option.className = "ft-browser-option";
            browserGroup.appendChild(option);
          });
          voiceSelect.appendChild(browserGroup);
        } else {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "Browser voices are loading...";
          option.className = "ft-loading-option";
          option.disabled = true;
          voiceSelect.appendChild(option);
        }

        const options = Array.from(voiceSelect.options).filter((option) => !option.disabled);
        const matchedOption = options.find((option) => option.value === previousValue) ||
          preferredVoiceOption(options, previousValue) ||
          options.find((option) => option.value.startsWith("embedded:"));

        if (matchedOption) {
          voiceSelect.value = matchedOption.value;
        }
        applyCachedSpaceWVoice(false);
        if (currentNode) {
          refreshIpaForAccent(selectedVoiceAccent());
        }
        lastVoiceListMode = voiceListMode;
        updateVoiceSelectTone();
        if (voicePicker && voicePicker.classList.contains("is-open")) {
          buildVoicePicker();
        }
        setTtsStatus("");
      };

      const getSelectedBrowserVoice = () => {
        const match = /^browser:(\d+)$/.exec(voiceSelect.value);
        if (!match) return null;
        return speechVoices[Number(match[1])] || null;
      };

      const base64UrlToBase64 = (value) => {
        const base64 = String(value || "").replace(/-/g, "+").replace(/_/g, "/");
        return base64 + "=".repeat((4 - (base64.length % 4)) % 4);
      };

      const serverAssetUrl = (path) => {
        return resolveServerAssetUrl(path);
      };

      const decodeUtf8Buffer = (buffer) => {
        const bytes = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer || []);
        try {
          return new TextDecoder("utf-8", { fatal: false }).decode(bytes).replace(/^\uFEFF/, "");
        } catch (error) {
          let text = "";
          bytes.forEach((value) => {
            text += String.fromCharCode(value);
          });
          try {
            return decodeURIComponent(escape(text)).replace(/^\uFEFF/, "");
          } catch (_error) {
            return text.replace(/^\uFEFF/, "");
          }
        }
      };

      const normalizeEffectSounds = (raw) => {
        const source = raw && typeof raw === "object" ? raw : {};
        const effects = {};
        Object.entries(source).forEach(([rawKey, rawValue]) => {
          const key = clean(rawKey).toLowerCase();
          if (!key || !rawValue) {
            return;
          }
          let mime = "audio/mpeg";
          let base64 = "";
          let url = "";
          if (Array.isArray(rawValue)) {
            mime = clean(rawValue[0]) || mime;
            base64 = clean(rawValue[1]);
          } else if (typeof rawValue === "object") {
            mime = clean(rawValue.mime ?? rawValue.m) || mime;
            base64 = clean(rawValue.base64 ?? rawValue.b ?? rawValue.data);
            url = clean(rawValue.url ?? rawValue.u ?? rawValue.src);
          } else {
            base64 = clean(rawValue);
          }
          if (base64 || url) {
            effects[key] = { mime, base64, url };
          }
        });
        if (effects.false && !effects.fall) {
          effects.fall = effects.false;
        }
        return effects;
      };

      let generatedEffectAudioContext = null;
      const DEFAULT_LESSON_EFFECTS = Object.freeze({
        true: { mime: "audio/mpeg", url: "Sound/fx-true_a76ad961cb10db7ab6c8a928b2581711b5ae65b9.mp3" },
        false: { mime: "audio/mpeg", url: "Sound/fx-false_1ee7795e2be3b283e45d8f6b3e1a0e166bb6d4cc.mp3" },
      });

      // 2026-07-20: Keep answer feedback audible when older lesson payloads omit embedded effect clips.
      const lessonEffectClip = (name) => {
        const key = clean(name).toLowerCase();
        const normalizedKey = key === "fall" || key === "wrong" ? "false" : (key === "correct" || key === "ok" ? "true" : key);
        return lessonEffects[key] || lessonEffects[normalizedKey] || DEFAULT_LESSON_EFFECTS[normalizedKey] || null;
      };

      const playGeneratedEffectTone = (name) => new Promise((resolve) => {
        const key = clean(name).toLowerCase();
        if (!["true", "correct", "ok", "false", "wrong", "fall"].includes(key)) {
          resolve(false);
          return;
        }
        try {
          const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextCtor) {
            resolve(false);
            return;
          }
          if (!generatedEffectAudioContext) {
            generatedEffectAudioContext = new AudioContextCtor();
          }
          const ctx = generatedEffectAudioContext;
          const startTone = () => {
            const success = ["true", "correct", "ok"].includes(key);
            const now = ctx.currentTime;
            const duration = success ? 0.26 : 0.22;
            const master = ctx.createGain();
            master.gain.setValueAtTime(0.0001, now);
            master.gain.exponentialRampToValueAtTime(success ? 0.13 : 0.10, now + 0.018);
            master.gain.exponentialRampToValueAtTime(0.0001, now + duration);
            master.connect(ctx.destination);
            const makeOsc = (type, startFreq, endFreq, offset = 0) => {
              const osc = ctx.createOscillator();
              const gain = ctx.createGain();
              osc.type = type;
              osc.frequency.setValueAtTime(startFreq, now + offset);
              osc.frequency.exponentialRampToValueAtTime(endFreq, now + duration);
              gain.gain.setValueAtTime(type === "sine" ? 0.9 : 0.34, now + offset);
              osc.connect(gain);
              gain.connect(master);
              osc.start(now + offset);
              osc.stop(now + duration + 0.015);
            };
            if (success) {
              makeOsc("sine", 640, 980, 0);
              makeOsc("triangle", 960, 1420, 0.035);
            } else {
              makeOsc("triangle", 360, 180, 0);
              makeOsc("sawtooth", 220, 120, 0.025);
            }
            window.setTimeout(() => resolve(true), Math.ceil((duration + 0.03) * 1000));
          };
          if (ctx.state === "suspended") {
            ctx.resume().then(startTone).catch(() => resolve(false));
          } else {
            startTone();
          }
        } catch (error) {
          resolve(false);
        }
      });

      const playEffectSound = (name) => {
        void playEffectSoundAsync(name);
      };

      const normalizeAudioClip = (raw) => {
        if (!raw) {
          return null;
        }
        if (typeof raw === "object" && !Array.isArray(raw) && (raw.kind === "speak" || raw.speak)) {
          return {
            kind: "speak",
            text: clean(raw.text ?? raw.speak),
            fallback: normalizeAudioSequence(raw.fallback),
          };
        }
        let mime = "audio/mpeg";
        let base64 = "";
        let url = "";
        if (Array.isArray(raw)) {
          mime = clean(raw[0]) || mime;
          base64 = clean(raw[1]);
        } else if (typeof raw === "object") {
          mime = clean(raw.mime ?? raw.m) || mime;
          base64 = clean(raw.base64 ?? raw.b ?? raw.data);
          url = clean(raw.url ?? raw.u ?? raw.src);
        } else {
          base64 = clean(raw);
        }
        return (base64 || url) ? {
          mime,
          base64,
          url,
          assetId: typeof raw === "object" ? clean(raw.asset_id ?? raw.assetId ?? raw.aid ?? "") : "",
          contentHash: typeof raw === "object" ? clean(raw.content_hash ?? raw.contentHash ?? raw.sha256 ?? "") : "",
          bytes: typeof raw === "object" ? Math.max(0, Number(raw.bytes ?? raw.size ?? 0) || 0) : 0,
        } : null;
      };

      const normalizeAudioSequence = (raw) => {
        if (!raw) {
          return [];
        }
        if (Array.isArray(raw)) {
          const directClip = normalizeAudioClip(raw);
          if (directClip && typeof raw[0] === "string" && typeof raw[1] === "string") {
            return [directClip];
          }
          return raw.map(normalizeAudioClip).filter(Boolean);
        }
        return [normalizeAudioClip(raw)].filter(Boolean);
      };

      const audioClipUrl = (clip) => clip.url ? serverAssetUrl(clip.url) : `data:${clean(clip.mime) || "audio/mpeg"};base64,${base64UrlToBase64(clip.base64)}`;

      const audioClipCacheKey = (clip) => {
        const asset = normalizeAudioClip(clip);
        if (!asset || asset.kind === "speak") {
          return "";
        }
        const assetId = audioMediaAssetId(asset);
        if (assetId) {
          return `${GENERIC_MEDIA_AUDIO_CACHE_PREFIX}${assetId}`;
        }
        if (asset.url) {
          return `url:${audioClipUrl(asset)}`;
        }
        if (asset.base64) {
          return `data:${clean(asset.mime) || "audio/mpeg"}:${asset.base64.length}:${asset.base64.slice(0, 80)}`;
        }
        return "";
      };

      const mediaBlobSha256 = async (blob) => {
        if (!(blob instanceof Blob) || !blob.size || !window.crypto || !crypto.subtle) {
          return "";
        }
        const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
        return `sha256:${Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
      };

      const audioMediaAssetId = (clip) => {
        const asset = normalizeAudioClip(clip);
        if (!asset || asset.kind === "speak") {
          return "";
        }
        if (asset.assetId) {
          return clean(asset.assetId).toLowerCase();
        }
        if (asset.base64) {
          return `audio-data:${hashSpaceWText(`${clean(asset.mime)}|${asset.base64.length}|${asset.base64.slice(0, 160)}`)}`;
        }
        try {
          const parsed = new URL(audioClipUrl(asset), window.location.origin);
          const pathAsset = clean(parsed.searchParams.get("path") || "").replace(/\\/g, "/").toLowerCase();
          if (pathAsset) {
            return `audio-path:${pathAsset}`;
          }
          const meaning = clean(parsed.searchParams.get("meaning") || "");
          if (meaning) {
            return `audio-meaning:${hashSpaceWText(meaning.toLowerCase())}`;
          }
          const semanticParams = Array.from(parsed.searchParams.entries())
            .filter(([name]) => !["v", "ts", "cache", "version"].includes(clean(name).toLowerCase()))
            .sort((a, b) => `${a[0]}=${a[1]}`.localeCompare(`${b[0]}=${b[1]}`));
          return `audio-route:${hashSpaceWText(`${parsed.pathname.toLowerCase()}|${JSON.stringify(semanticParams)}`)}`;
        } catch (error) {
          return `audio-url:${hashSpaceWText(clean(asset.url).toLowerCase())}`;
        }
      };

      const audioMediaPersistentKey = (clip) => {
        const assetId = audioMediaAssetId(clip);
        return assetId ? `${GENERIC_MEDIA_AUDIO_CACHE_PREFIX}${assetId}` : "";
      };

      const cachedAudioClipUrl = (clip) => {
        const asset = normalizeAudioClip(clip);
        if (!asset || asset.kind === "speak") {
          return "";
        }
        const key = audioClipCacheKey(asset);
        return (key && cachedAudioClipUrls.get(key)) || audioClipUrl(asset);
      };

      const preloadAudioClip = async (clip, token = null, options = {}) => {
        const asset = normalizeAudioClip(clip);
        if (!asset || asset.kind === "speak") {
          return false;
        }
        const key = audioClipCacheKey(asset);
        if (!key) {
          return false;
        }
        const forceReload = Boolean(options && options.forceReload);
        const priorityPlayback = Boolean(options && options.priorityPlayback);
        if (!forceReload && (cachedAudioClipUrls.has(key) || key.startsWith("data:"))) {
          return true;
        }
        if (!forceReload && !priorityPlayback && pendingAudioClipPreloads.has(key)) {
          return pendingAudioClipPreloads.get(key);
        }
        const url = audioClipUrl(asset);
        const persistentKey = audioMediaPersistentKey(asset);
        const legacyPersistentKey = `${GENERIC_AUDIO_CACHE_PREFIX}${key}`;
        const rememberCachedRecord = async (cached, sourceKey = persistentKey) => {
          if (!cached || !(cached.blob instanceof Blob)) {
            return false;
          }
          if (!isUsableCachedAudioBlob(cached.blob)) {
            await deleteSpaceWAudioRecord(sourceKey);
            return false;
          }
          const actualHash = await mediaBlobSha256(cached.blob);
          if (!actualHash || (clean(cached.content_hash) && clean(cached.content_hash) !== actualHash)) {
            await deleteSpaceWAudioRecord(sourceKey);
            return false;
          }
          if (sourceKey !== persistentKey || !clean(cached.content_hash) || clean(cached.asset_id) !== audioMediaAssetId(asset)) {
            const migrated = await writeSpaceWAudioRecord({
              ...cached,
              key: persistentKey,
              asset_id: audioMediaAssetId(asset),
              content_hash: actualHash,
              bytes: cached.blob.size,
              mime: clean(cached.blob.type) || clean(asset.mime) || "audio/mpeg",
              media_key_version: 1,
              migrated_at: new Date().toISOString(),
            });
            if (migrated && sourceKey !== persistentKey) {
              void deleteSpaceWAudioRecord(sourceKey);
            }
          }
          const previousUrl = cachedAudioClipUrls.get(key);
          if (previousUrl && previousUrl.startsWith("blob:")) {
            URL.revokeObjectURL(previousUrl);
          }
          cachedAudioClipUrls.set(key, URL.createObjectURL(cached.blob));
          return true;
        };
        const fetchAudioBlob = async (useNative = false) => {
          const fetchAudio = useNative && typeof window.__futureNativeAudioFetch === "function"
            ? window.__futureNativeAudioFetch
            : fetch;
          try {
            const response = await fetchAudio(url, { cache: forceReload ? "reload" : "force-cache", headers: { "Accept": "audio/*,*/*" } });
            if (!response.ok) {
              return null;
            }
            return await response.blob();
          } catch (error) {
            return null;
          }
        };
        const rememberFetchedBlob = async (blob) => {
          if (!isUsableCachedAudioBlob(blob)) {
            return false;
          }
          if (token !== null && token !== vocabAudioCacheToken) {
            return false;
          }
          const contentHash = await mediaBlobSha256(blob);
          if (!contentHash) {
            return false;
          }
          const previousUrl = cachedAudioClipUrls.get(key);
          if (previousUrl && previousUrl.startsWith("blob:")) {
            URL.revokeObjectURL(previousUrl);
          }
          cachedAudioClipUrls.set(key, URL.createObjectURL(blob));
          const record = {
            key: persistentKey,
            asset_id: audioMediaAssetId(asset),
            content_hash: contentHash,
            bytes: blob.size,
            blob,
            mime: clean(blob.type) || clean(asset.mime) || "audio/mpeg",
            media_key_version: 1,
            access_at: Date.now(),
            created_at: new Date().toISOString(),
          };
          const stored = await writeSpaceWAudioRecord(record);
          if (!stored) {
            window.__futureOfflineStorageState = {
              ...(window.__futureOfflineStorageState || {}),
              limited: true,
              pressure: "critical",
              lastError: "audio_cache_write_failed",
              checkedAt: Date.now(),
            };
          }
          return true;
        };
        const task = (async () => {
          if (!forceReload) {
            const cached = await readSpaceWAudioRecord(persistentKey);
            if (await rememberCachedRecord(cached, persistentKey)) {
              return true;
            }
            const legacy = await readSpaceWAudioRecord(legacyPersistentKey);
            if (await rememberCachedRecord(legacy, legacyPersistentKey)) {
              return true;
            }
          }
          return rememberFetchedBlob(await fetchAudioBlob(priorityPlayback));
        })();
        if (!priorityPlayback) {
          pendingAudioClipPreloads.set(key, task);
        }
        return task.finally(() => {
          if (pendingAudioClipPreloads.get(key) === task) {
            pendingAudioClipPreloads.delete(key);
          }
        });
      };

      const playAudioClipOnce = (clip, options = {}) => new Promise((resolve) => {
        const asset = normalizeAudioClip(clip);
        if (!asset) {
          resolve(false);
          return;
        }
        if (asset.kind === "speak") {
          playSelectedEnglishGrammarText(asset.text, asset.fallback, {
            stopToken: options.stopToken,
            currentStopToken: options.currentStopToken,
          }).then(resolve).catch(() => resolve(false));
          return;
        }
        if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
          resolve(false);
          return;
        }
        let finished = false;
        let audioRef = null;
        const done = (ok = true) => {
          if (finished) {
            return;
          }
          finished = true;
          if (audioRef && typeof options.onAudioDone === "function") {
            try {
              options.onAudioDone(audioRef);
            } catch (error) {
            }
          }
          if (audioRef && activeAudio === audioRef) {
            activeAudio = null;
          }
          resolve(ok);
        };
        void (async () => {
        try {
          const startToken = Number(options.stopToken || 0) || 0;
          // 2026-07-20: Feedback effects must start inside the Enter/click gesture; cache work may finish later.
          if (options.immediateUserGesture) {
            void preloadAudioClip(asset, null, { priorityPlayback: true });
          } else {
            await preloadAudioClip(asset, null, { priorityPlayback: true });
          }
          if (startToken && Number(options.currentStopToken && options.currentStopToken()) !== startToken) {
            done(false);
            return;
          }
          const audio = new Audio(cachedAudioClipUrl(asset));
          audioRef = audio;
          activeAudio = audio;
          audio.preload = "auto";
          normalizeAudioPlaybackSpeed(audio);
          const playbackRate = Math.max(0.35, Math.min(2, Number(options.playbackRate || options.rate || 1) || 1));
          if (playbackRate !== 1) {
            try {
              audio.defaultPlaybackRate = playbackRate;
              audio.playbackRate = playbackRate;
            } catch (error) {
            }
          }
          audio.volume = Number(options.volume ?? 0.92) || 0.92;
          if (typeof options.onAudio === "function") {
            try {
              options.onAudio(audio, done);
            } catch (error) {
            }
          }
          audio.onended = () => done(true);
          audio.onerror = () => done(false);
          if (options.trackGrammar) {
            activeGrammarAudio = { audio, done };
          }
          const started = audio.play();
          if (started && typeof started.catch === "function") {
            started.catch(() => done(false));
          }
        } catch (error) {
          done(false);
        }
        })();
      });

      const playEffectSoundAsync = (name) => {
        const key = clean(name).toLowerCase();
        const effect = lessonEffectClip(key);
        if (!effect) {
          return playGeneratedEffectTone(key);
        }
        return playAudioClipOnce(effect, { volume: 0.9, immediateUserGesture: true }).then((ok) => {
          if (ok === false) {
            return playGeneratedEffectTone(key);
          }
          return ok;
        }).catch(() => playGeneratedEffectTone(key));
      };

      const preloadLessonEffectSounds = () => {
        Object.values({ ...DEFAULT_LESSON_EFFECTS, ...(lessonEffects || {}) }).forEach((clip) => {
          void preloadAudioClip(clip, null);
        });
      };

      const stopGrammarAudio = () => {
        grammarAudioStopToken += 1;
        if (!activeGrammarAudio) {
          return;
        }
        const active = activeGrammarAudio;
        const audio = active.audio || active;
        activeGrammarAudio = null;
        try {
          audio.pause();
          audio.currentTime = 0;
        } catch (error) {
          // Grammar narration is optional.
        }
        if (typeof active.done === "function") {
          active.done(false);
        }
      };

      const playGrammarAudioSequence = async (sequence) => {
        const clips = normalizeAudioSequence(sequence);
        if (!clips.length) {
          return false;
        }
        stopGrammarAudio();
        const sequenceToken = grammarAudioStopToken;
        for (const clip of clips) {
          if (sequenceToken !== grammarAudioStopToken) {
            break;
          }
          await playAudioClipOnce(clip, {
            trackGrammar: true,
            volume: 0.94,
            stopToken: sequenceToken,
            currentStopToken: () => grammarAudioStopToken,
          });
          if (sequenceToken !== grammarAudioStopToken) {
            break;
          }
        }
        activeGrammarAudio = null;
        return true;
      };

      const normalizeEmbeddedAudioAsset = (item, index = 0) => {
        if (Array.isArray(item)) {
          return {
            id: clean(item[0]) || `voice-${index}`,
            label: clean(item[1]) || `Embedded voice ${index + 1}`,
            mime: clean(item[2]) || "audio/mpeg",
            base64: clean(item[3]),
            timings: Array.isArray(item[4]) ? item[4] : [],
            duration_ms: Number(item[5] || 0) || 0,
            voice: clean(item[6]),
            url: clean(item[7]),
          };
        }
        if (!item || typeof item !== "object") {
          return null;
        }
        return {
          id: clean(item.id ?? item.k ?? item.key) || `voice-${index}`,
          label: clean(item.label ?? item.name ?? item.l) || `Embedded voice ${index + 1}`,
          mime: clean(item.mime ?? item.m) || "audio/mpeg",
          base64: clean(item.base64 ?? item.b ?? item.data),
          url: clean(item.url ?? item.u ?? item.src),
          timings: Array.isArray(item.timings ?? item.tm) ? (item.timings ?? item.tm) : [],
          duration_ms: Number(item.duration_ms ?? item.d ?? 0) || 0,
          voice: clean(item.voice ?? item.vc ?? item.v),
        };
      };

      const getEmbeddedAudioAssetsForNode = (node = currentNode) => {
        const assets = [];
        const rawAssets = Array.isArray(node?.audio_voices ?? node?.av)
          ? (node.audio_voices ?? node.av)
          : [];
        rawAssets.forEach((item, index) => {
          const asset = normalizeEmbeddedAudioAsset(item, index);
          if (asset && (asset.base64 || asset.url)) {
            assets.push(asset);
          }
        });
        if (node && node.audio && (node.audio.base64 || node.audio.url)) {
          assets.unshift({
            id: "default",
            label: `Embedded audio (${clean(node.voice) || "lesson voice"})`,
            mime: clean(node.audio.mime) || "audio/mpeg",
            base64: clean(node.audio.base64),
            url: clean(node.audio.url),
            timings: Array.isArray(node.timings) ? node.timings : [],
            duration_ms: Number(node.duration_ms || 0) || 0,
            voice: clean(node.voice),
          });
        }
        return assets;
      };

      const getEmbeddedAudioAssets = () => getEmbeddedAudioAssetsForNode(currentNode);

      const findEmbeddedAudioAsset = (value) => {
        const id = clean(String(value || "").replace(/^embedded:/i, ""));
        return getEmbeddedAudioAssets().find((asset, index) => clean(asset.voice) === id || clean(asset.id) === id || String(index) === id) || null;
      };

      const findEmbeddedAudioAssetForNode = (node, value) => {
        const id = clean(String(value || "").replace(/^embedded:/i, ""));
        if (!id) {
          return null;
        }
        return getEmbeddedAudioAssetsForNode(node).find((asset, index) => (
          clean(asset.voice) === id ||
          clean(asset.id) === id ||
          String(index) === id
        )) || null;
      };

      const getEmbeddedAudioUrl = (asset = null) => {
        if (asset && (asset.base64 || asset.url)) {
          return asset.url ? serverAssetUrl(asset.url) : `data:${clean(asset.mime) || "audio/mpeg"};base64,${base64UrlToBase64(asset.base64)}`;
        }
        const audio = currentNode && currentNode.audio;
        if (!audio || (!audio.base64 && !audio.url)) {
          return "";
        }
        return audio.url ? serverAssetUrl(audio.url) : `data:${clean(audio.mime) || "audio/mpeg"};base64,${base64UrlToBase64(audio.base64)}`;
      };

      const getTokenElements = () => Array.from(englishNode.querySelectorAll(".ft-word"));
      const getIpaTokenElements = () => Array.from(ipaNode.querySelectorAll(".ft-ipa-token"));
      const getCurrentTokens = () => Array.isArray(currentNode && (currentNode.tokens ?? currentNode.tk)) ? (currentNode.tokens ?? currentNode.tk) : [];

      const normalizeTimingToken = (value) => clean(value).replace(/[^0-9A-Za-z']/g, "");

      const ipaTimingWeight = (ipaText) => {
        const ipa = clean(ipaText);
        if (!ipa) {
          return 0;
        }
        const compact = ipa.replace(/\s+/g, "");
        const vowelMatches = compact.match(/[iyɨʉɯuɪʏʊeøɘɵɤoəɛœɜɞʌɔæɐaɶɑɒɚɝ]/gu) || [];
        const stressCount = (ipa.match(/[ˈˌ]/gu) || []).length;
        return Math.max(
          compact.length * 0.52,
          (vowelMatches.length * 1.45) + (stressCount * 0.2),
        );
      };

      const tokenTimingWeight = (token, index = 0) => {
        const wordEl = getTokenElements()[index];
        const tokenText = clean(token?.text ?? token?.t ?? wordEl?.textContent ?? "");
        const normalized = normalizeTimingToken(tokenText);
        let weight = Math.max(0.45, (normalized || tokenText).length || 1);
        if (/[.,!?;:]$/.test(tokenText)) {
          weight += 0.36;
        }
        const ipaText = clean(tokenIpaForAccent(token, currentAccent) || wordEl?.dataset?.ipa || token?.ipa || token?.i || "");
        if (ipaText) {
          weight = Math.max(weight, ipaTimingWeight(ipaText));
        }
        return Math.max(0.45, weight);
      };

      const estimateSpeechDuration = (text, tokens = []) => {
        const tokenCount = Math.max(1, Array.isArray(tokens) && tokens.length ? tokens.length : clean(text).split(/\s+/).filter(Boolean).length);
        const compactLength = Math.max(1, clean(text).replace(/\s+/g, "").length);
        const estimate = (tokenCount * 420) + (compactLength * 18) + 160;
        return Math.max(720, Math.min(18000, estimate));
      };

      const buildWeightedTimings = (durationMs = 0, options = {}) => {
        const tokens = getCurrentTokens();
        const wordItems = getTokenElements();
        const count = Math.max(1, tokens.length || wordItems.length || 1);
        const text = clean(englishNode.textContent);
        const requestedDuration = Math.max(0, Number(durationMs || currentNode?.duration_ms || 0) || 0);
        const estimatedDuration = estimateSpeechDuration(text, tokens.length ? tokens : wordItems.map((node) => ({ t: node.textContent, i: node.dataset.ipa })));
        const baseDuration = options.fitToDuration && requestedDuration > 0
          ? Math.max(360, requestedDuration)
          : Math.max(requestedDuration, estimatedDuration);
        const entries = Array.from({ length: count }, (_item, index) => tokens[index] || { t: wordItems[index]?.textContent || "", i: wordItems[index]?.dataset?.ipa || "" });
        const weights = entries.map((token, index) => tokenTimingWeight(token, index));
        const totalWeight = Math.max(0.01, weights.reduce((sum, value) => sum + Number(value || 0), 0));
        let leadMs = Math.min(90, baseDuration * 0.06);
        let tailMs = Math.min(120, baseDuration * 0.08);
        if (baseDuration <= leadMs + tailMs + 90) {
          leadMs = 0;
          tailMs = 0;
        }
        const usableMs = Math.max(80, baseDuration - leadMs - tailMs);
        const minSpan = 45;
        const lastIndex = entries.length - 1;
        let cursor = leadMs;
        let cumulative = 0;
        return entries.map((_token, index) => {
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
      };

      const normalizeTimingList = (timings) => (Array.isArray(timings) ? timings : [])
        .map((item, index) => ({
          index: Number(item.index ?? item.i ?? index) || 0,
          start: Number(item.start ?? item.s ?? 0) || 0,
          end: Number(item.end ?? item.e ?? 0) || 0,
        }))
        .filter((item) => item.end > item.start);

      const scaleTimingsToDuration = (timings, durationMs = 0) => {
        const normalized = normalizeTimingList(timings);
        const target = Math.max(0, Number(durationMs || 0) || 0);
        const lastEnd = Math.max(...normalized.map((item) => Number(item.end || 0) || 0), 0);
        if (!target || !lastEnd || Math.abs(target - lastEnd) < 24) {
          return normalized;
        }
        const ratio = target / lastEnd;
        return normalized.map((item) => ({
          index: item.index,
          start: Math.round(item.start * ratio),
          end: Math.max(Math.round(item.start * ratio) + 1, Math.round(item.end * ratio)),
        }));
      };

      const getNodeTimings = (durationMs = 0, options = {}) => {
        const tokens = getCurrentTokens();
        if (tokens.length || getTokenElements().length) {
          return buildWeightedTimings(durationMs, options);
        }
        const raw = Array.isArray(currentNode && currentNode.timings) ? currentNode.timings : [];
        const mapped = normalizeTimingList(raw);
        return mapped.length
          ? (options.fitToDuration ? scaleTimingsToDuration(mapped, durationMs) : mapped)
          : buildWeightedTimings(durationMs, options);
      };

      const setActiveHighlightIndex = (activeIndex) => {
        const wordItems = getTokenElements();
        const ipaItems = getIpaTokenElements();
        wordItems.forEach((item, index) => item.classList.toggle("is-reading", index === activeIndex));
        ipaItems.forEach((item) => item.classList.toggle("is-reading", Number(item.dataset.tokenIndex) === activeIndex));
      };

      const highlightAt = (ms, timings) => {
        if (!getTokenElements().length && !getIpaTokenElements().length) {
          return;
        }
        let activeIndex = -1;
        for (const item of timings) {
          if (ms >= item.start && ms < item.end) {
            activeIndex = item.index;
            break;
          }
        }
        setActiveHighlightIndex(activeIndex);
      };

      const tokenIndexForChar = (charIndex) => {
        const target = Math.max(0, Number(charIndex || 0) || 0);
        const tokens = getCurrentTokens();
        if (tokens.length) {
          for (let index = 0; index < tokens.length; index += 1) {
            const token = tokens[index] || {};
            const start = Math.max(0, Number(token.start ?? token.s ?? 0) || 0);
            const end = Math.max(start, Number(token.end ?? token.e ?? start) || start);
            if (target >= start && target <= end) {
              return index;
            }
            if (target < start) {
              return Math.max(0, index - 1);
            }
          }
          return tokens.length - 1;
        }
        const text = englishNode.textContent || "";
        const matches = Array.from(text.matchAll(/[A-Za-z]+(?:'[A-Za-z]+)?/g));
        for (let index = 0; index < matches.length; index += 1) {
          const match = matches[index];
          if (target >= match.index && target <= match.index + match[0].length) {
            return index;
          }
        }
        const nextIndex = matches.findIndex((match) => target < match.index);
        if (nextIndex > 0) {
          return nextIndex - 1;
        }
        return Math.max(0, (matches.length || getTokenElements().length || 1) - 1);
      };

      const startAudioHighlight = (audio, timings) => {
        clearHighlight();
        const tick = () => {
          if (!audio || audio.paused || audio.ended) {
            return;
          }
          highlightAt(audio.currentTime * 1000, timings);
          highlightFrame = window.requestAnimationFrame(tick);
        };
        tick();
      };

      const startTimerHighlight = (durationMs) => {
        clearHighlight();
        const timings = getNodeTimings(durationMs);
        const started = performance.now();
        const tick = () => {
          const elapsed = performance.now() - started;
          highlightAt(elapsed, timings);
          if (elapsed <= durationMs + 120) {
            highlightFrame = window.requestAnimationFrame(tick);
          }
        };
        tick();
      };

      const isReviewPhase = () => Boolean(reviewModeActive);

      const requiredListenCount = () => isReviewPhase() ? REVIEW_REQUIRED_LISTENS : REQUIRED_FULL_LISTENS;

      const shuffleIndexes = (count) => {
        const out = Array.from({ length: Math.max(0, Number(count) || 0) }, (_item, index) => index);
        for (let index = out.length - 1; index > 0; index -= 1) {
          const swapIndex = Math.floor(Math.random() * (index + 1));
          [out[index], out[swapIndex]] = [out[swapIndex], out[index]];
        }
        return out;
      };

      const reviewCanStart = () => Boolean(
        !reviewModeActive &&
        !reviewFinished &&
        lessonNodes.length &&
        currentNodeIndex >= lessonNodes.length - 1
      );

      const hasNextNode = () => {
        if (reviewModeActive) {
          return true;
        }
        if (lessonNodes.length > 1 && currentNodeIndex < lessonNodes.length - 1) {
          return true;
        }
        return reviewCanStart();
      };

      const listenStatusText = () => {
        if (!nextPanelCanShow) {
          return "";
        }
        const required = requiredListenCount();
        const count = Math.min(required, completedListenCount);
        if (spaceWSpeakSkipSessionApproved) {
          if (count < required) {
            return `Speak skip approved for this file. Listen ${count}/${required} before Next.`;
          }
          return "Speak skip approved for this file. Next is ready.";
        }
        if (isReviewPhase()) {
          if (count < required) {
            return `Vòng ôn: nghe trọn câu tiếng Anh 1 lần trước khi mở Speak. (${count}/${required})`;
          }
          if (!reviewSpeakCompleted) {
            return `Đã nghe đủ. Hãy Speak đạt ít nhất ${SPEAK_UNLOCK_SCORE}% để hoàn thành node này.`;
          }
          return reviewCurrentHadError
            ? "Lượt này có lỗi, node sẽ quay lại vòng ôn."
            : "Lượt này không sai. Node được tính là xong.";
        }
        if (!speakStepCompleted) {
          if (count < required) {
            return `IPA đã mở. Hãy nghe trọn câu tiếng Anh ${required} lần trước khi mở Speak. (${count}/${required})`;
          }
          return `Speak đã mở. Hãy ghi âm và đạt ít nhất ${SPEAK_UNLOCK_SCORE}% để mở Next.`;
        }
        if (!grammarStepCompleted) {
          return "Speak đã đạt yêu cầu. Next đã sẵn sàng; grammar checkpoint là phần ôn thêm.";
        }
        if (!hasNextNode()) {
          return "";
        }
        return count >= required
          ? "Đã nghe đủ 3 lần. Bạn có thể chuyển sang bước tiếp theo."
          : `Cần nghe hết câu tiếng Anh ít nhất ${required} lần trước khi Next. (${count}/${required})`;
      };

      const SPACE_W_TOKEN_SUPPORT_DELAY_MS = 60000;
      let spaceWTokenSupportTimer = 0;
      let spaceWTokenSupportNodeIndex = -1;
      let spaceWTokenSupportMode = "hidden";
      let spaceWTokenSupportCard = null;
      let spaceWTokenSupportTitle = null;
      let spaceWTokenSupportMeta = null;
      let spaceWTokenSupportTokens = null;
      let spaceWTokenSupportStartedAt = 0;
      let spaceWTokenSupportCountdownTimer = 0;
      let spaceWTokenSupportCountdownNode = null;
      let spaceWTokenSupportCountdownValue = null;
      let spaceWTokenSupportConnector = null;
      let spaceWTokenSupportConnectorPath = null;
      let spaceWTokenSupportConnectorGlow = null;
      let spaceWTokenSupportConnectorStart = null;
      let spaceWTokenSupportConnectorEnd = null;
      let spaceWTokenSupportReflowRaf = 0;
      let spaceWTokenSupportReflowBound = false;
      let spaceWTokenSupportSurfaceGuardBound = false;
      let spaceWTokenSupportRenderedNodeIndex = -1;
      let spaceWTokenSupportRenderedEntries = [];

      const spaceWTokenSupportShuffle = (items = []) => {
        const out = items.slice();
        for (let index = out.length - 1; index > 0; index -= 1) {
          const swapIndex = Math.floor(Math.random() * (index + 1));
          [out[index], out[swapIndex]] = [out[swapIndex], out[index]];
        }
        return out;
      };

      const spaceWTokenSupportWords = (options = {}) => {
        const sourceWords = typeof getNodeScoringWords === "function" ? getNodeScoringWords(currentNode) : [];
        const keepDuplicates = Boolean(options.keepDuplicates);
        const seen = new Set();
        return sourceWords
          .map((item) => clean(item && (item.text || item.t || item.word || item.norm)))
          .filter((text) => {
            const key = normalizeWord(text);
            if (!text || !key || (!keepDuplicates && seen.has(key))) {
              return false;
            }
            seen.add(key);
            return true;
          });
      };

      const SPACE_W_TOKEN_SUPPORT_MAX_BLOCKS = 12;

      const spaceWTokenSupportEntries = () => {
        const words = spaceWTokenSupportWords({ keepDuplicates: true });
        if (words.length > SPACE_W_TOKEN_SUPPORT_MAX_BLOCKS) {
          const groupCount = SPACE_W_TOKEN_SUPPORT_MAX_BLOCKS;
          const baseGroupSize = Math.floor(words.length / groupCount);
          let extraWords = words.length % groupCount;
          const groups = [];
          let start = 0;
          for (let groupIndex = 0; groupIndex < groupCount; groupIndex += 1) {
            const groupSize = baseGroupSize + (extraWords > 0 ? 1 : 0);
            extraWords = Math.max(0, extraWords - 1);
            const groupWords = words.slice(start, start + groupSize);
            groups.push({
              type: "group",
              words: groupWords,
              start,
              key: groupWords.map((word) => normalizeWord(word)).join("|"),
            });
            start += groupSize;
          }
          return spaceWTokenSupportShuffle(groups);
        }
        return spaceWTokenSupportShuffle(words.map((word, index) => ({
          type: "word",
          words: [word],
          start: index,
          key: normalizeWord(word),
        })));
      };

      const spaceWTokenSupportTypedWords = () => {
        const text = clean(answerInput && answerInput.value);
        if (!text) {
          return [];
        }
        return text.split(/\s+/).map((word) => normalizeWord(word)).filter(Boolean);
      };

      const updateSpaceWTokenSupportTypedHighlights = () => {
        if (!spaceWTokenSupportTokens || spaceWTokenSupportMode !== "tokens") {
          return;
        }
        const typedWords = spaceWTokenSupportTypedWords();
        const typedKeySet = new Set(typedWords);
        spaceWTokenSupportTokens.querySelectorAll("[data-spacew-token-entry]").forEach((entryNode) => {
          const start = Number(entryNode.getAttribute("data-spacew-token-start"));
          let complete = true;
          entryNode.querySelectorAll("[data-spacew-token-key]").forEach((chip, offset) => {
            const key = clean(chip.getAttribute("data-spacew-token-key"));
            const sequenceIndex = Number.isFinite(start) && start >= 0 ? start + offset : -1;
            const isTyped = sequenceIndex >= 0
              ? typedWords[sequenceIndex] === key
              : typedKeySet.has(key);
            chip.classList.toggle("is-typed", isTyped);
            chip.setAttribute("aria-pressed", isTyped ? "true" : "false");
            if (!isTyped) {
              complete = false;
            }
          });
          entryNode.classList.toggle("is-complete", complete && entryNode.querySelectorAll("[data-spacew-token-key]").length > 1);
        });
      };

      const scheduleSpaceWTokenSupportReflow = () => {
        if (spaceWTokenSupportMode === "hidden" || !spaceWTokenSupportCard || spaceWTokenSupportCard.hidden) {
          return;
        }
        if (spaceWTokenSupportReflowRaf) {
          return;
        }
        spaceWTokenSupportReflowRaf = window.requestAnimationFrame(() => {
          spaceWTokenSupportReflowRaf = 0;
          positionSpaceWTokenSupportCard();
        });
      };

      const bindSpaceWTokenSupportReflow = () => {
        if (spaceWTokenSupportReflowBound) {
          return;
        }
        spaceWTokenSupportReflowBound = true;
        window.addEventListener("resize", scheduleSpaceWTokenSupportReflow, { passive: true });
        window.addEventListener("scroll", scheduleSpaceWTokenSupportReflow, { passive: true, capture: true });
        if (window.visualViewport) {
          window.visualViewport.addEventListener("resize", scheduleSpaceWTokenSupportReflow, { passive: true });
          window.visualViewport.addEventListener("scroll", scheduleSpaceWTokenSupportReflow, { passive: true });
        }
      };

      const ensureSpaceWTokenSupportCard = () => {
        if (spaceWTokenSupportCard) {
          return spaceWTokenSupportCard;
        }
        const card = document.createElement("button");
        card.type = "button";
        card.className = "ft-spacew-token-support";
        card.setAttribute("aria-live", "polite");
        card.setAttribute("aria-label", "Open Space W token support");
        card.hidden = true;
        card.innerHTML = `
          <span class="ft-spacew-token-support-icon ft-inventory-gem is-cupgold" aria-hidden="true"></span>
          <span class="ft-spacew-token-support-copy">
            <b></b>
            <small></small>
          </span>
          <span class="ft-spacew-token-support-tokens" aria-hidden="true"></span>
        `;
        spaceWTokenSupportTitle = card.querySelector("b");
        spaceWTokenSupportMeta = card.querySelector("small");
        spaceWTokenSupportTokens = card.querySelector(".ft-spacew-token-support-tokens");
        card.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (spaceWTokenSupportMode === "reward") {
            showSpaceWTokenSupportTokens();
          }
        });
        document.body.appendChild(card);
        spaceWTokenSupportCard = card;
        bindSpaceWTokenSupportReflow();
        bindSpaceWTokenSupportSurfaceGuard();
        return card;
      };

      const ensureSpaceWTokenSupportConnector = () => {
        if (spaceWTokenSupportConnector && spaceWTokenSupportConnector.isConnected) {
          return spaceWTokenSupportConnector;
        }
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.classList.add("ft-spacew-token-support-link");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("focusable", "false");
        svg.hidden = true;
        svg.innerHTML = `
          <path class="ft-spacew-token-support-link-glow"></path>
          <path class="ft-spacew-token-support-link-line"></path>
          <circle class="ft-spacew-token-support-link-dot is-card" r="4"></circle>
          <circle class="ft-spacew-token-support-link-dot is-anchor" r="5"></circle>
        `;
        document.body.appendChild(svg);
        spaceWTokenSupportConnector = svg;
        spaceWTokenSupportConnectorGlow = svg.querySelector(".ft-spacew-token-support-link-glow");
        spaceWTokenSupportConnectorPath = svg.querySelector(".ft-spacew-token-support-link-line");
        spaceWTokenSupportConnectorStart = svg.querySelector(".ft-spacew-token-support-link-dot.is-card");
        spaceWTokenSupportConnectorEnd = svg.querySelector(".ft-spacew-token-support-link-dot.is-anchor");
        return svg;
      };

      const hideSpaceWTokenSupportConnector = () => {
        if (spaceWTokenSupportConnector) {
          spaceWTokenSupportConnector.hidden = true;
        }
      };

      const destroySpaceWTokenSupportConnector = () => {
        document.querySelectorAll(".ft-spacew-token-support-link").forEach((node) => {
          node.remove();
        });
        spaceWTokenSupportConnector = null;
        spaceWTokenSupportConnectorGlow = null;
        spaceWTokenSupportConnectorPath = null;
        spaceWTokenSupportConnectorStart = null;
        spaceWTokenSupportConnectorEnd = null;
      };

      const spaceWTokenSupportRouteActive = () => Boolean(
        document.documentElement.classList.contains("ft-space-w-mode") ||
        (stageNode && stageNode.classList.contains("is-space-w-mode"))
      );

      const spaceWTokenSupportSurfaceActive = () => Boolean(
        spaceWTokenSupportRouteActive() &&
        cardNode &&
        !cardNode.classList.contains("is-hidden")
      );

      const updateSpaceWTokenSupportConnector = () => {
        const card = spaceWTokenSupportCard;
        const svg = ensureSpaceWTokenSupportConnector();
        if (!spaceWTokenSupportSurfaceActive() || !card || card.hidden || !svg || !cardNode) {
          hideSpaceWTokenSupportConnector();
          return;
        }
        const cardRect = card.getBoundingClientRect();
        const anchorRect = cardNode.getBoundingClientRect();
        if (cardRect.width < 20 || cardRect.height < 20 || anchorRect.width < 20 || anchorRect.height < 20) {
          hideSpaceWTokenSupportConnector();
          return;
        }
        const cardOnRight = cardRect.left >= anchorRect.right - 4;
        const startX = cardOnRight ? cardRect.left + 18 : cardRect.right - 18;
        const startY = Math.max(cardRect.top + 22, Math.min(cardRect.bottom - 10, cardRect.bottom - 14));
        const endX = anchorRect.right + 4;
        const endY = Math.max(anchorRect.top + 12, Math.min(anchorRect.bottom - 18, anchorRect.top + 22));
        const direction = cardOnRight ? 1 : -1;
        const bendOffset = Math.max(46, Math.min(138, Math.abs(startX - endX) * 0.54));
        const bendX1 = endX + (direction * bendOffset);
        const bendX2 = startX - (direction * Math.max(24, bendOffset * 0.45));
        const liftY = Math.min(endY, startY) - Math.max(18, Math.min(42, Math.abs(startY - endY) * 0.36));
        const path = `M ${Math.round(endX)} ${Math.round(endY)} C ${Math.round(bendX1)} ${Math.round(liftY)}, ${Math.round(bendX2)} ${Math.round(liftY)}, ${Math.round(startX)} ${Math.round(startY)}`;
        svg.hidden = false;
        if (spaceWTokenSupportConnectorPath) {
          spaceWTokenSupportConnectorPath.setAttribute("d", path);
        }
        if (spaceWTokenSupportConnectorGlow) {
          spaceWTokenSupportConnectorGlow.setAttribute("d", path);
        }
        if (spaceWTokenSupportConnectorStart) {
          spaceWTokenSupportConnectorStart.setAttribute("cx", String(Math.round(startX)));
          spaceWTokenSupportConnectorStart.setAttribute("cy", String(Math.round(startY)));
        }
        if (spaceWTokenSupportConnectorEnd) {
          spaceWTokenSupportConnectorEnd.setAttribute("cx", String(Math.round(endX)));
          spaceWTokenSupportConnectorEnd.setAttribute("cy", String(Math.round(endY)));
        }
      };

      const ensureSpaceWTokenSupportCountdown = () => {
        if (spaceWTokenSupportCountdownNode && spaceWTokenSupportCountdownNode.isConnected) {
          return spaceWTokenSupportCountdownNode;
        }
        if (!cardNode) {
          return null;
        }
        const node = document.createElement("div");
        node.className = "ft-spacew-support-countdown";
        node.hidden = true;
        node.setAttribute("aria-live", "polite");
        node.innerHTML = `
          <span class="ft-spacew-support-countdown-ring" aria-hidden="true"></span>
          <span class="ft-spacew-support-countdown-copy">
            <b>Token support</b>
            <small>01:00</small>
          </span>
        `;
        spaceWTokenSupportCountdownValue = node.querySelector("small");
        cardNode.appendChild(node);
        spaceWTokenSupportCountdownNode = node;
        return node;
      };

      const formatSpaceWTokenSupportTime = (milliseconds) => {
        const totalSeconds = Math.max(0, Math.ceil(milliseconds / 1000));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
      };

      const updateSpaceWTokenSupportCountdown = () => {
        const node = ensureSpaceWTokenSupportCountdown();
        if (!node || !spaceWTokenSupportStartedAt || spaceWTokenSupportMode !== "hidden") {
          return;
        }
        const elapsed = Math.max(0, Date.now() - spaceWTokenSupportStartedAt);
        const remaining = Math.max(0, SPACE_W_TOKEN_SUPPORT_DELAY_MS - elapsed);
        const progress = Math.min(1, elapsed / SPACE_W_TOKEN_SUPPORT_DELAY_MS);
        node.hidden = false;
        node.style.setProperty("--spacew-support-countdown-progress", `${Math.round(progress * 100)}%`);
        if (spaceWTokenSupportCountdownValue) {
          spaceWTokenSupportCountdownValue.textContent = formatSpaceWTokenSupportTime(remaining);
        }
        if (remaining <= 0) {
          node.hidden = true;
        }
      };

      const hideSpaceWTokenSupportCountdown = (clearStartedAt = true) => {
        if (spaceWTokenSupportCountdownTimer) {
          window.clearInterval(spaceWTokenSupportCountdownTimer);
          spaceWTokenSupportCountdownTimer = 0;
        }
        if (clearStartedAt) {
          spaceWTokenSupportStartedAt = 0;
        }
        if (spaceWTokenSupportCountdownNode) {
          spaceWTokenSupportCountdownNode.hidden = true;
        }
      };

      const startSpaceWTokenSupportCountdown = () => {
        hideSpaceWTokenSupportCountdown(false);
        spaceWTokenSupportStartedAt = Date.now();
        updateSpaceWTokenSupportCountdown();
        spaceWTokenSupportCountdownTimer = window.setInterval(updateSpaceWTokenSupportCountdown, 500);
      };

      const positionSpaceWTokenSupportCard = () => {
        const card = ensureSpaceWTokenSupportCard();
        if (!spaceWTokenSupportSurfaceActive()) {
          hideSpaceWTokenSupport(true);
          return;
        }
        if (!card || card.hidden || !cardNode) {
          hideSpaceWTokenSupportConnector();
          return;
        }
        const margin = 10;
        const gap = 42;
        const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
        const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
        const anchorRect = cardNode.getBoundingClientRect();
        if (anchorRect.width < 20 || anchorRect.height < 20 || anchorRect.bottom < 0 || anchorRect.top > viewportHeight) {
          hideSpaceWTokenSupportConnector();
          return;
        }
        const rightSpace = viewportWidth - anchorRect.right - margin - gap;
        const preferredWidth = spaceWTokenSupportMode === "tokens" ? 390 : 258;
        const width = Math.min(
          preferredWidth,
          Math.max(212, rightSpace > 180 ? rightSpace : viewportWidth - (margin * 2)),
        );
        card.style.setProperty("--spacew-token-support-width", `${Math.round(width)}px`);
        const cardRect = card.getBoundingClientRect();
        let left = anchorRect.right + gap;
        if (left + width > viewportWidth - margin) {
          left = viewportWidth - width - margin;
        }
        const height = cardRect.height || (spaceWTokenSupportMode === "tokens" ? 180 : 78);
        const verticalGap = spaceWTokenSupportMode === "tokens" ? 22 : 16;
        const safeTop = Math.min(90, Math.max(58, viewportHeight * 0.09));
        let top = anchorRect.top - height - verticalGap;
        left = Math.min(viewportWidth - width - margin, Math.max(margin, left));
        if (height > viewportHeight - (margin * 2)) {
          top = margin;
        } else {
          top = Math.min(viewportHeight - height - margin, Math.max(safeTop, top));
        }
        card.style.left = `${Math.round(left)}px`;
        card.style.top = `${Math.round(top)}px`;
        window.requestAnimationFrame(updateSpaceWTokenSupportConnector);
      };

      const hideSpaceWTokenSupport = (clearTimer = false) => {
        if (clearTimer && spaceWTokenSupportTimer) {
          window.clearTimeout(spaceWTokenSupportTimer);
          spaceWTokenSupportTimer = 0;
        }
        if (clearTimer) {
          hideSpaceWTokenSupportCountdown(true);
        }
        spaceWTokenSupportMode = "hidden";
        spaceWTokenSupportRenderedNodeIndex = -1;
        spaceWTokenSupportRenderedEntries = [];
        if (spaceWTokenSupportCard) {
          spaceWTokenSupportCard.hidden = true;
          spaceWTokenSupportCard.classList.remove("is-visible", "is-reward", "is-tokens", "is-cup-release");
        }
        if (clearTimer) {
          destroySpaceWTokenSupportConnector();
        } else {
          hideSpaceWTokenSupportConnector();
        }
      };

      const spaceWTokenSupportBlockingPanelLive = () => [ipaPanel, speakPanel, grammarPanel].some((panel) => (
        panel && panel.classList && panel.classList.contains("is-live")
      ));

      const clearSpaceWPanelOverlaysForRouteLeave = () => {
        const lastSpaceVFlushAt = Number(window.__ftSpaceVRouteLeaveFlushStartedAt || 0) || 0;
        if (Date.now() - lastSpaceVFlushAt < 1800) {
          // A caller that can await the save already started it.
        } else if (typeof window.__ftFlushSpaceVProgressBeforeBack === "function") {
          window.__ftSpaceVRouteLeaveFlushStartedAt = Date.now();
          void window.__ftFlushSpaceVProgressBeforeBack({ notice: true });
        } else if (typeof window.__ftKeepaliveSpaceVProgress === "function") {
          window.__ftSpaceVRouteLeaveFlushStartedAt = Date.now();
          window.__ftKeepaliveSpaceVProgress("route_leave");
        }
        if (revealTimer) {
          window.clearTimeout(revealTimer);
          revealTimer = 0;
        }
        if (connectorTimer) {
          window.clearTimeout(connectorTimer);
          connectorTimer = 0;
        }
        hideSpaceWTokenSupport(true);
        hideSpaceWTokenSupportCountdown(true);
        clearAllConnectors();
        allPanels().forEach((panel) => {
          panel.classList.remove("is-live", "is-complete", "is-active", "is-dim", "is-mobile-hidden", "is-active-panel");
        });
        mobileUnlockedPanels.clear();
        mobileActivePanelKey = "";
        syncMobilePanelTabs();
      };

      window.__ftClearSpaceWOverlaysForRouteLeave = clearSpaceWPanelOverlaysForRouteLeave;

      const spaceWTokenSupportEligible = () => Boolean(
        spaceWTokenSupportSurfaceActive() &&
        currentNode &&
        spaceWTokenSupportNodeIndex === currentNodeIndex &&
        cardNode &&
        !cardNode.classList.contains("is-hidden") &&
        authGate &&
        authGate.classList.contains("is-hidden") &&
        loadGate &&
        loadGate.classList.contains("is-hidden") &&
        !questionModeActive &&
        !vocabModeActive &&
        !nextPanelCanShow &&
        answerInput &&
        !answerInput.disabled &&
        !spaceWTokenSupportBlockingPanelLive() &&
        spaceWTokenSupportWords().length > 1
      );

      const syncSpaceWTokenSupportSurfaceGuard = () => {
        if (!spaceWTokenSupportRouteActive()) {
          hideSpaceWTokenSupport(true);
          return;
        }
        if (spaceWTokenSupportMode === "hidden") {
          return;
        }
        const loadGateVisible = Boolean(loadGate && !loadGate.classList.contains("is-hidden"));
        const translateCardHidden = Boolean(!cardNode || cardNode.classList.contains("is-hidden"));
        if (!spaceWTokenSupportSurfaceActive() || loadGateVisible || translateCardHidden || spaceWTokenSupportBlockingPanelLive()) {
          hideSpaceWTokenSupport(true);
          return;
        }
        if (!spaceWTokenSupportEligible()) {
          hideSpaceWTokenSupport(false);
        }
      };

      const bindSpaceWTokenSupportSurfaceGuard = () => {
        if (spaceWTokenSupportSurfaceGuardBound) {
          return;
        }
        spaceWTokenSupportSurfaceGuardBound = true;
        if (window.MutationObserver) {
          const observer = new MutationObserver(syncSpaceWTokenSupportSurfaceGuard);
          if (loadGate) {
            observer.observe(loadGate, { attributes: true, attributeFilter: ["class"] });
          }
          if (cardNode) {
            observer.observe(cardNode, { attributes: true, attributeFilter: ["class"] });
          }
          observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
          if (document.body) {
            observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
          }
          if (stageNode) {
            observer.observe(stageNode, { attributes: true, attributeFilter: ["class"] });
          }
          allPanels().forEach((panel) => {
            observer.observe(panel, { attributes: true, attributeFilter: ["class"] });
          });
        }
        window.addEventListener("popstate", clearSpaceWPanelOverlaysForRouteLeave, { passive: true });
        window.addEventListener("hashchange", clearSpaceWPanelOverlaysForRouteLeave, { passive: true });
        window.addEventListener("pagehide", clearSpaceWPanelOverlaysForRouteLeave, { passive: true });
      };

      const showSpaceWTokenSupportReward = () => {
        if (!spaceWTokenSupportEligible()) {
          hideSpaceWTokenSupport(false);
          return;
        }
        hideSpaceWTokenSupportCountdown(true);
        const card = ensureSpaceWTokenSupportCard();
        spaceWTokenSupportMode = "reward";
        card.hidden = false;
        card.classList.add("is-visible", "is-reward");
        card.classList.remove("is-tokens", "is-cup-release");
        if (spaceWTokenSupportTitle) {
          spaceWTokenSupportTitle.textContent = "Golden Mastery Cup";
        }
        if (spaceWTokenSupportMeta) {
          spaceWTokenSupportMeta.textContent = "Token support ready";
        }
        if (spaceWTokenSupportTokens) {
          spaceWTokenSupportTokens.textContent = "";
          spaceWTokenSupportTokens.setAttribute("aria-hidden", "true");
        }
        card.setAttribute("aria-label", "Open shuffled answer tokens");
        window.requestAnimationFrame(positionSpaceWTokenSupportCard);
      };

      const showSpaceWTokenSupportTokens = () => {
        if (!spaceWTokenSupportEligible()) {
          hideSpaceWTokenSupport(true);
          return;
        }
        const card = ensureSpaceWTokenSupportCard();
        const entries = (
          spaceWTokenSupportRenderedNodeIndex === currentNodeIndex &&
          Array.isArray(spaceWTokenSupportRenderedEntries) &&
          spaceWTokenSupportRenderedEntries.length
        )
          ? spaceWTokenSupportRenderedEntries
          : spaceWTokenSupportEntries();
        spaceWTokenSupportRenderedNodeIndex = currentNodeIndex;
        spaceWTokenSupportRenderedEntries = entries.slice();
        const wordCount = entries.reduce((total, entry) => total + ((entry.words && entry.words.length) || 0), 0);
        spaceWTokenSupportMode = "tokens";
        card.hidden = false;
        card.classList.add("is-visible", "is-tokens");
        card.classList.remove("is-reward");
        if (spaceWTokenSupportTitle) {
          spaceWTokenSupportTitle.textContent = "Token support";
        }
        if (spaceWTokenSupportMeta) {
          spaceWTokenSupportMeta.textContent = wordCount > SPACE_W_TOKEN_SUPPORT_MAX_BLOCKS
            ? `Default support - ${entries.length} shuffled blocks`
            : `Default support - ${wordCount} shuffled tokens`;
        }
        if (spaceWTokenSupportTokens) {
          spaceWTokenSupportTokens.textContent = "";
          spaceWTokenSupportTokens.setAttribute("aria-hidden", "false");
          entries.forEach((entry) => {
            const entryNode = document.createElement("span");
            entryNode.className = "ft-spacew-token-support-entry";
            entryNode.setAttribute("data-spacew-token-entry", entry.type || "word");
            entryNode.setAttribute("data-spacew-token-start", String(Number.isFinite(entry.start) ? entry.start : -1));
            (entry.words || []).forEach((word) => {
              const chip = document.createElement("span");
              chip.className = "ft-spacew-token-support-word";
              chip.setAttribute("data-spacew-token-key", normalizeWord(word));
              chip.setAttribute("aria-pressed", "false");
              chip.textContent = word;
              entryNode.appendChild(chip);
            });
            spaceWTokenSupportTokens.appendChild(entryNode);
          });
          updateSpaceWTokenSupportTypedHighlights();
        }
        card.setAttribute("aria-label", "Shuffled Space W answer tokens");
        window.requestAnimationFrame(positionSpaceWTokenSupportCard);
      };

      const updateSpaceWTokenSupportVisibility = () => {
        if (spaceWTokenSupportMode === "hidden") {
          return;
        }
        if (!spaceWTokenSupportEligible()) {
          hideSpaceWTokenSupport(false);
          return;
        }
        window.requestAnimationFrame(positionSpaceWTokenSupportCard);
      };

      const scheduleSpaceWTokenSupportForNode = () => {
        hideSpaceWTokenSupport(true);
        spaceWTokenSupportNodeIndex = currentNodeIndex;
        if (!currentNode || spaceWTokenSupportWords().length <= 1) {
          return;
        }
        startSpaceWTokenSupportCountdown();
        spaceWTokenSupportTimer = window.setTimeout(() => {
          spaceWTokenSupportTimer = 0;
          hideSpaceWTokenSupportCountdown(true);
          showSpaceWTokenSupportTokens();
        }, SPACE_W_TOKEN_SUPPORT_DELAY_MS);
      };

      const registerCompletedListen = () => {
        if (!ipaPanel.classList.contains("is-live")) {
          return;
        }
        completedListenCount = Math.min(IPA_STAR_FULL_LISTENS, completedListenCount + 1);
        renderIpaStars();
        if (spaceWSpeakSkipSessionApproved && completedListenCount >= requiredListenCount() && nextPanelCanShow) {
          speakStepCompleted = true;
          reviewSpeakCompleted = true;
          showSpeakPanel(true);
          setSpeakReportButtonState("accepted");
          setSpeakStatus("Admin approved Speak skip for this file. Speak card stays visible and Next is unlocked.", "ok");
        }
        if (isReviewPhase() && completedListenCount >= requiredListenCount() && nextPanelCanShow && !reviewSpeakCompleted) {
          showSpeakPanel(true);
          setSpeakStatus(`Đã nghe đủ. Bấm Record và đạt ít nhất ${SPEAK_UNLOCK_SCORE}% để hoàn thành.`, "");
        }
        if (!isReviewPhase() && completedListenCount >= requiredListenCount() && nextPanelCanShow && !speakStepCompleted && !grammarStepCompleted && !grammarState.active) {
          showSpeakPanel(true);
          setSpeakStatus(`Speak đã mở. Hãy đạt ít nhất ${SPEAK_UNLOCK_SCORE}% để mở Next.`, "");
        }
        updateNextButton();
        queueSpaceWProgressSave(100);
      };

      const setPlaybackState = (isPlaying, message = "", isError = false) => {
        playButton.disabled = Boolean(isPlaying);
        playButton.classList.toggle("is-loading", Boolean(isPlaying));
        ipaPanel.classList.toggle("is-speaking", Boolean(isPlaying));
        scheduleMobileInfiniteMotionSync();
        setTtsStatus(!isPlaying && !message ? listenStatusText() : message, isError);
      };

      const stopActiveAudio = () => {
        if ("speechSynthesis" in window) {
          window.speechSynthesis.cancel();
        }
        clearHighlight();
        if (activeAudio) {
          activeAudio.pause();
          activeAudio.removeAttribute("src");
          activeAudio.load();
          activeAudio = null;
        }
      };

      const normalizeAudioPlaybackSpeed = (audio) => {
        if (!audio) {
          return;
        }
        try {
          audio.defaultPlaybackRate = 1;
          audio.playbackRate = 1;
          if ("preservesPitch" in audio) {
            audio.preservesPitch = true;
          }
          if ("mozPreservesPitch" in audio) {
            audio.mozPreservesPitch = true;
          }
          if ("webkitPreservesPitch" in audio) {
            audio.webkitPreservesPitch = true;
          }
        } catch (error) {
          // Some mobile browsers expose these fields as readonly for certain streams.
        }
      };

      const browserSpeechRate = () => isMobileVoiceList() ? 1.02 : 0.98;

      const playAudioUrl = (url, timingsOverride = null, options = {}) => new Promise((resolve, reject) => {
        const audio = new Audio(url);
        activeAudio = audio;
        audio.preload = "auto";
        normalizeAudioPlaybackSpeed(audio);
        let settled = false;
        const startupTimer = window.setTimeout(() => {
          if (settled) {
            return;
          }
          settled = true;
          try {
            audio.pause();
            audio.removeAttribute("src");
            audio.load();
          } catch (error) {
          }
          reject(new Error("Audio timed out"));
        }, 18000);
        const finish = (callback, value) => {
          if (settled) {
            return;
          }
          settled = true;
          window.clearTimeout(startupTimer);
          if (activeAudio === audio) {
            activeAudio = null;
          }
          if (typeof options.onAudioDone === "function") {
            try {
              options.onAudioDone(audio);
            } catch (error) {
            }
          }
          callback(value);
        };
        const markStarted = () => {
          if (!settled) {
            window.clearTimeout(startupTimer);
          }
        };
        const timingsForAudio = () => {
          const durationMs = Number.isFinite(audio.duration) && audio.duration > 0
            ? audio.duration * 1000
            : Number(currentNode?.duration_ms || 0);
          if (Array.isArray(timingsOverride) && timingsOverride.length) {
            return scaleTimingsToDuration(timingsOverride, durationMs);
          }
          return getNodeTimings(durationMs, { fitToDuration: true });
        };
        audio.onloadedmetadata = () => {
          markStarted();
          startAudioHighlight(audio, timingsForAudio());
        };
        audio.onplay = () => {
          markStarted();
          startAudioHighlight(audio, timingsForAudio());
        };
        audio.onended = () => {
          clearHighlight();
          registerCompletedListen();
          finish(resolve);
        };
        audio.onerror = () => finish(reject, new Error("Audio failed"));
        if (typeof options.onAudio === "function") {
          try {
            options.onAudio(audio, () => finish(resolve, false));
          } catch (error) {
          }
        }
        const started = audio.play();
        if (started && typeof started.catch === "function") {
          started.catch((error) => finish(reject, error));
        }
      });

      const fetchAudioBlob = async (url, options = {}) => {
        const timeoutMs = Math.max(3000, Number(options.timeoutMs || 18000) || 18000);
        let timeoutId = 0;
        let controller = null;
        const fetchOptions = { headers: { "Accept": "audio/*,*/*" } };
        if ("AbortController" in window) {
          controller = new AbortController();
          fetchOptions.signal = controller.signal;
          timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
        }
        try {
          const response = await fetch(url, fetchOptions);
          if (!response.ok) {
            throw new Error(`Audio HTTP ${response.status}`);
          }
          return await response.blob();
        } finally {
          if (timeoutId) {
            window.clearTimeout(timeoutId);
          }
        }
      };

      const decodeAudioBlob = async (blob) => {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
          return null;
        }
        const audioContext = new AudioContextCtor();
        try {
          return await audioContext.decodeAudioData(await blob.arrayBuffer());
        } finally {
          if (typeof audioContext.close === "function") {
            const closed = audioContext.close();
            if (closed && typeof closed.catch === "function") {
              closed.catch(() => {});
            }
          }
        }
      };

      const audioRmsRows = (buffer) => {
        if (!buffer || !buffer.length || !buffer.sampleRate || !buffer.numberOfChannels) {
          return [];
        }
        const samples = buffer.getChannelData(0);
        const sampleRate = buffer.sampleRate;
        const windowSize = Math.max(128, Math.round(sampleRate * 0.018));
        const hopSize = Math.max(64, Math.round(sampleRate * 0.012));
        const rows = [];
        let maxLevel = 0;
        for (let offset = 0; offset < samples.length; offset += hopSize) {
          const end = Math.min(samples.length, offset + windowSize);
          let sum = 0;
          for (let index = offset; index < end; index += 1) {
            const value = samples[index] || 0;
            sum += value * value;
          }
          const level = Math.sqrt(sum / Math.max(1, end - offset));
          maxLevel = Math.max(maxLevel, level);
          rows.push({
            time: ((offset + ((end - offset) / 2)) / sampleRate) * 1000,
            level,
          });
        }
        if (!rows.length || maxLevel <= 0) {
          return rows;
        }
        return rows.map((row) => ({ time: row.time, level: row.level / maxLevel }));
      };

      const buildAudioGuidedTimings = (buffer) => {
        const durationMs = Math.max(0, Number(buffer && buffer.duration ? buffer.duration * 1000 : 0) || 0);
        const base = getNodeTimings(durationMs, { fitToDuration: true });
        if (!durationMs || base.length < 2) {
          return base;
        }
        const rows = audioRmsRows(buffer);
        if (rows.length < 6) {
          return base;
        }
        const searchRadius = clamp(durationMs / Math.max(6, base.length * 2.4), 80, 220);
        const minGap = clamp(durationMs / Math.max(10, base.length * 2.8), 45, 180);
        const boundaries = [];
        let previous = 0;

        for (let index = 0; index < base.length - 1; index += 1) {
          const remainingBoundaries = base.length - index - 2;
          const latest = Math.max(previous + minGap, durationMs - ((remainingBoundaries + 1) * minGap));
          const predicted = clamp(Number(base[index].end || 0) || 0, previous + minGap, latest);
          const low = clamp(predicted - searchRadius, previous + minGap, latest);
          const high = clamp(predicted + searchRadius, low, latest);
          let bestTime = predicted;
          let bestScore = Infinity;

          for (const row of rows) {
            if (row.time < low || row.time > high) {
              continue;
            }
            const distance = Math.abs(row.time - predicted) / Math.max(1, searchRadius);
            const score = (row.level * 1.8) + (distance * 0.45);
            if (score < bestScore) {
              bestScore = score;
              bestTime = row.time;
            }
          }

          const boundary = clamp(bestTime, previous + minGap, latest);
          boundaries.push(boundary);
          previous = boundary;
        }

        let start = 0;
        return base.map((item, index) => {
          const end = index < boundaries.length ? boundaries[index] : durationMs;
          const safeEnd = Math.max(start + 1, Math.min(durationMs, end));
          const timing = {
            index: item.index,
            start: Math.round(start),
            end: Math.round(safeEnd),
          };
          start = safeEnd;
          return timing;
        });
      };

      const buildAudioGuidedTimingsFromBlob = async (blob) => {
        const buffer = await decodeAudioBlob(blob);
        return buffer ? buildAudioGuidedTimings(buffer) : [];
      };

      const openSpaceWAudioDb = () => {
        if (!("indexedDB" in window)) {
          return Promise.reject(new Error("IndexedDB unavailable."));
        }
        if (spaceWAudioDbPromise) {
          return spaceWAudioDbPromise;
        }
        spaceWAudioDbPromise = new Promise((resolve, reject) => {
          const request = indexedDB.open(SPACE_W_AUDIO_DB_NAME, SPACE_W_AUDIO_DB_VERSION);
          request.onupgradeneeded = () => {
            const db = request.result;
            const store = db.objectStoreNames.contains(SPACE_W_AUDIO_STORE)
              ? request.transaction.objectStore(SPACE_W_AUDIO_STORE)
              : db.createObjectStore(SPACE_W_AUDIO_STORE, { keyPath: "key" });
            if (!store.indexNames.contains("access_at")) {
              store.createIndex("access_at", "access_at", { unique: false });
            }
            const cursorRequest = store.openCursor();
            cursorRequest.onsuccess = () => {
              const cursor = cursorRequest.result;
              if (!cursor) return;
              const row = cursor.value && typeof cursor.value === "object" ? cursor.value : {};
              const blob = row.blob;
              cursor.update({
                ...row,
                bytes: Math.max(0, Number(row.bytes || (blob && blob.size) || 0) || 0),
                access_at: Math.max(1, Number(row.access_at || Date.parse(row.created_at || "") || Date.now()) || Date.now()),
              });
              cursor.continue();
            };
          };
          request.onsuccess = () => {
            const db = request.result;
            db.onversionchange = () => {
              try { db.close(); } catch (error) {}
              spaceWAudioDbPromise = null;
            };
            if ("onclose" in db) {
              db.onclose = () => { spaceWAudioDbPromise = null; };
            }
            resolve(db);
          };
          request.onerror = () => reject(request.error || new Error("Audio cache could not open."));
        }).catch((error) => {
          spaceWAudioDbPromise = null;
          throw error;
        });
        return spaceWAudioDbPromise;
      };

      const readSpaceWAudioRecord = async (key) => {
        if (!key) {
          return null;
        }
        try {
          const db = await openSpaceWAudioDb();
          return await new Promise((resolve) => {
            const transaction = db.transaction(SPACE_W_AUDIO_STORE, "readonly");
            const request = transaction.objectStore(SPACE_W_AUDIO_STORE).get(key);
            request.onsuccess = () => {
              const record = request.result;
              if (record && record.blob instanceof Blob && Date.now() - Number(record.access_at || 0) > 60 * 60 * 1000) {
                try {
                  const write = db.transaction(SPACE_W_AUDIO_STORE, "readwrite").objectStore(SPACE_W_AUDIO_STORE).put({
                    ...record,
                    bytes: Math.max(0, Number(record.bytes || record.blob.size || 0) || 0),
                    access_at: Date.now(),
                  });
                  write.onerror = () => {};
                } catch (error) {
                }
              }
              resolve(record && record.blob instanceof Blob ? record : null);
            };
            request.onerror = () => resolve(null);
          });
        } catch (error) {
          return null;
        }
      };

      const deleteSpaceWAudioRecord = async (key) => {
        if (!key) {
          return false;
        }
        try {
          const db = await openSpaceWAudioDb();
          return await new Promise((resolve) => {
            const transaction = db.transaction(SPACE_W_AUDIO_STORE, "readwrite");
            transaction.objectStore(SPACE_W_AUDIO_STORE).delete(key);
            transaction.oncomplete = () => resolve(true);
            transaction.onerror = () => resolve(false);
            transaction.onabort = () => resolve(false);
          });
        } catch (error) {
          return false;
        }
      };

      const isUsableCachedAudioBlob = (blob) => {
        if (!(blob instanceof Blob)) {
          return false;
        }
        const size = Number(blob.size || 0);
        if (!Number.isFinite(size) || size < 256) {
          return false;
        }
        const mime = clean(blob.type || "").toLowerCase();
        return !mime || mime.startsWith("audio/") || mime === "application/octet-stream";
      };

      // Added 2026-07-21: stream audio LRU metadata one record at a time so oversized legacy caches do not load all blobs into RAM.
      const pruneSpaceWAudioCache = async (options = {}) => {
        try {
          const db = await openSpaceWAudioDb();
          const estimate = navigator.storage && typeof navigator.storage.estimate === "function"
            ? await navigator.storage.estimate().catch(() => null)
            : null;
          const quota = Math.max(0, Number(estimate && estimate.quota || 0) || 0);
          const pressure = clean(options.pressure || offlineStoragePressure).toLowerCase();
          let byteLimit = SPACE_W_AUDIO_CACHE_MAX_BYTES;
          if (quota > 0) {
            byteLimit = Math.max(SPACE_W_AUDIO_CACHE_MIN_BYTES, Math.min(byteLimit, Math.floor(quota * 0.2)));
          }
          if (pressure === "high") byteLimit = Math.max(SPACE_W_AUDIO_CACHE_MIN_BYTES, Math.floor(byteLimit * 0.5));
          if (pressure === "critical") byteLimit = Math.max(SPACE_W_AUDIO_CACHE_MIN_BYTES, Math.floor(byteLimit * 0.25));
          const incomingBytes = Math.max(0, Number(options.incomingBytes || 0) || 0);
          const entryLimit = pressure === "critical" ? 2000 : (pressure === "high" ? 4000 : SPACE_W_AUDIO_CACHE_MAX_ENTRIES);
          const removeKeys = [];
          let keptBytes = 0;
          let keptEntries = 0;
          await new Promise((resolve, reject) => {
            const transaction = db.transaction(SPACE_W_AUDIO_STORE, "readonly");
            const store = transaction.objectStore(SPACE_W_AUDIO_STORE);
            const source = store.indexNames.contains("access_at") ? store.index("access_at") : store;
            const request = source.openCursor(null, "prev");
            request.onsuccess = () => {
              const cursor = request.result;
              if (!cursor) {
                resolve(true);
                return;
              }
              const row = cursor.value && typeof cursor.value === "object" ? cursor.value : {};
              const bytes = Math.max(0, Number(row.bytes || (row.blob && row.blob.size) || 0) || 0);
              const keep = keptEntries < entryLimit && keptBytes + bytes + incomingBytes <= byteLimit;
              if (keep) {
                keptEntries += 1;
                keptBytes += bytes;
              } else {
                removeKeys.push(clean(row.key));
              }
              cursor.continue();
            };
            request.onerror = () => reject(request.error);
          });
          if (removeKeys.length) {
            await new Promise((resolve) => {
              const transaction = db.transaction(SPACE_W_AUDIO_STORE, "readwrite");
              const store = transaction.objectStore(SPACE_W_AUDIO_STORE);
              removeKeys.forEach((key) => key && store.delete(key));
              transaction.oncomplete = () => resolve(true);
              transaction.onerror = () => resolve(false);
              transaction.onabort = () => resolve(false);
            });
          }
          return { removed: removeKeys.length, keptEntries, keptBytes, byteLimit };
        } catch (error) {
          return { removed: 0, keptEntries: 0, keptBytes: 0, byteLimit: 0, error: clean(error && (error.name || error.message)) };
        }
      };

      const writeSpaceWAudioRecord = async (record, retryAfterPrune = true) => {
        if (!record || !record.key || !isUsableCachedAudioBlob(record.blob)) {
          return false;
        }
        const storedRecord = {
          ...record,
          bytes: Math.max(0, Number(record.bytes || record.blob.size || 0) || 0),
          access_at: Date.now(),
          created_at: clean(record.created_at || new Date().toISOString()),
        };
        try {
          const db = await openSpaceWAudioDb();
          const stored = await new Promise((resolve) => {
            const transaction = db.transaction(SPACE_W_AUDIO_STORE, "readwrite");
            transaction.objectStore(SPACE_W_AUDIO_STORE).put(storedRecord);
            transaction.oncomplete = () => resolve(true);
            transaction.onerror = () => resolve(false);
            transaction.onabort = () => resolve(false);
          });
          if (stored) {
            spaceWAudioPersistentWrites += 1;
            if (spaceWAudioPersistentWrites % 16 === 0) void pruneSpaceWAudioCache();
            return true;
          }
          if (retryAfterPrune) {
            if (typeof pruneVocabImageCache === "function") await pruneVocabImageCache();
            await pruneSpaceWAudioCache({ incomingBytes: storedRecord.bytes, pressure: "critical" });
            return writeSpaceWAudioRecord(storedRecord, false);
          }
          window.__futureOfflineStorageState = {
            ...(window.__futureOfflineStorageState || {}),
            limited: true,
            pressure: "critical",
            lastError: "audio_cache_write_failed",
            checkedAt: Date.now(),
          };
          offlineStoragePressure = "critical";
          return false;
        } catch (error) {
          if (retryAfterPrune) {
            if (typeof pruneVocabImageCache === "function") await pruneVocabImageCache();
            await pruneSpaceWAudioCache({ incomingBytes: storedRecord.bytes, pressure: "critical" });
            return writeSpaceWAudioRecord(storedRecord, false);
          }
          return false;
        }
      };

      const normalizedCacheVoiceValue = (selectedValue) => {
        const raw = clean(selectedValue || "");
        if (raw.startsWith("sot:")) {
          return `sot:${clean(raw.slice(4)) || "en-US"}`;
        }
        if (raw.startsWith("edge:") || raw.startsWith("microsoft:")) {
          return `microsoft:${clean(raw.replace(/^(edge|microsoft):/i, "")) || "en-US-AriaNeural"}`;
        }
        return "";
      };

      const spaceWAudioCacheKey = (text, selectedValue) => {
        const phrase = clean(text);
        const voice = normalizedCacheVoiceValue(selectedValue);
        if (!phrase || !voice) {
          return "";
        }
        return ["media-tts", "v1", voice, hashSpaceWText(phrase.toLowerCase().replace(/\s+/g, " "))].join(":");
      };

      // 2026-07-21: Read old per-user TTS keys once, then migrate the same media into the shared client cache.
      const legacySpaceWAudioCacheKey = (text, selectedValue) => {
        const phrase = clean(text);
        const voice = normalizedCacheVoiceValue(selectedValue);
        if (!phrase || !voice) {
          return "";
        }
        const source = currentSpaceWCache && currentSpaceWCache.identity
          ? currentSpaceWCache.identity
          : hashSpaceWText(clean(currentLessonSource.title || currentLessonSource.name || "space-w"));
        return [spaceWUserKey(), source, voice, hashSpaceWText(phrase.toLowerCase().replace(/\s+/g, " "))].join(":");
      };

      const requestSoundOfTextBlob = async (text, voice) => {
        const url = await requestSoundOfTextUrl(text, voice);
        return fetchAudioBlob(url);
      };

      // Added 2026-07-15: checks Server 2 sound cache first, then asks worker to create missing Space_W listen audio.
      const requestServerSpaceWTtsAudio = async (text, selectedValue) => {
        const voiceValue = normalizedCacheVoiceValue(selectedValue);
        if (!voiceValue) {
          return null;
        }
        const cachedUrl = `/server-data/qm-sound?word=${encodeURIComponent(text)}&voice=${encodeURIComponent(voiceValue)}`;
        try {
          const cachedBlob = await fetchAudioBlob(cachedUrl, { timeoutMs: 8000 });
          if (cachedBlob instanceof Blob && cachedBlob.size > 0) {
            return {
              blob: cachedBlob,
              timings: [],
              mime: clean(cachedBlob.type) || "audio/mpeg",
              serverPath: cachedUrl,
              serverCached: true,
            };
          }
        } catch (error) {
        }
        if (typeof fetchAuthJson !== "function") {
          return null;
        }
        const { payload } = await fetchAuthJson("/pdf/speak", {
          method: "POST",
          timeoutMs: 120000,
          body: JSON.stringify({
            text,
            voice: voiceValue,
          }),
        });
        const source = payload && typeof payload === "object" ? payload : {};
        const audioPath = clean(source.audio_path || source.audioPath || source.path || (source.audio && (source.audio.path || source.audio.url)) || "");
        const audioUrl = audioPath
          ? (/^(https?:|data:|blob:|\/server-data\/)/i.test(audioPath)
            ? audioPath
            : `/server-data/asset?path=${encodeURIComponent(audioPath)}`)
          : "";
        if (!audioUrl) {
          return null;
        }
        const blob = await fetchAudioBlob(audioUrl, { timeoutMs: 45000 });
        return {
          blob,
          timings: Array.isArray(source.timings)
            ? source.timings
            : (Array.isArray(source.timing_tokens) ? source.timing_tokens : (Array.isArray(source.timingTokens) ? source.timingTokens : [])),
          mime: clean(source.audio_mime || source.audioMime || source.mime || (source.audio && source.audio.mime) || blob.type) || "audio/mpeg",
          serverPath: audioPath,
        };
      };

      const requestSoundOfTextUrl = async (text, voice) => {
        const createResponse = await fetch("https://api.soundoftext.com/sounds", {
          method: "POST",
          headers: {
            "Accept": "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            engine: "Google",
            data: { text, voice },
          }),
        });
        if (!createResponse.ok) {
          throw new Error(`Sound of Text HTTP ${createResponse.status}`);
        }
        const created = await createResponse.json();
        if (!created || !created.success || !created.id) {
          throw new Error("Sound of Text did not return an id");
        }

        for (let attempt = 0; attempt < 22; attempt += 1) {
          await delay(attempt ? 420 : 260);
          const statusResponse = await fetch(`https://api.soundoftext.com/sounds/${encodeURIComponent(created.id)}`, {
            headers: { "Accept": "application/json" },
          });
          if (!statusResponse.ok) {
            throw new Error(`Sound of Text status HTTP ${statusResponse.status}`);
          }
          const status = await statusResponse.json();
          if (status && status.status === "Done" && status.location) {
            return status.location;
          }
          if (status && status.status === "Error") {
            throw new Error("Sound of Text could not create this audio");
          }
        }
        throw new Error("Sound of Text timed out");
      };

      const xmlEscape = (value) => String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");

      const makeRequestId = () => {
        const bytes = new Uint8Array(16);
        if (window.crypto && window.crypto.getRandomValues) {
          window.crypto.getRandomValues(bytes);
        } else {
          for (let index = 0; index < bytes.length; index += 1) {
            bytes[index] = Math.floor(Math.random() * 256);
          }
        }
        return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
      };

      const edgeMessage = (headers, body = "") =>
        Object.entries(headers).map(([key, value]) => `${key}:${value}`).join("\r\n") + "\r\n\r\n" + body;

      const getEdgeVoiceInfo = (value) => {
        const name = clean(String(value || "").replace(/^(edge|microsoft):/i, ""));
        return edgeVoices.find((voice) => voice.name.toLowerCase() === name.toLowerCase()) ||
          normalizeEdgeRecord({ ShortName: name, Locale: name.split("-").slice(0, 2).join("-") || "en-US" });
      };

      const requestEdgeTtsBlob = (text, voiceInfo) => new Promise((resolve, reject) => {
        const voice = voiceInfo || getEdgeVoiceInfo("en-US-AriaNeural");
        if (!voice || !voice.name) {
          reject(new Error("Missing Edge voice."));
          return;
        }
        const requestId = makeRequestId();
        const chunks = [];
        let settled = false;
        let socket = null;
        const finish = (error, url = "") => {
          if (settled) {
            return;
          }
          settled = true;
          window.clearTimeout(timeoutId);
          try {
            if (socket) {
              socket.close();
            }
          } catch (closeError) {
            // Ignore close races.
          }
          if (error) {
            reject(error);
            return;
          }
          resolve(url);
        };
        const timeoutId = window.setTimeout(() => finish(new Error("Edge TTS timed out.")), 30000);
        socket = new WebSocket(`${EDGE_WS_URL}&ConnectionId=${requestId}`);
        socket.binaryType = "arraybuffer";

        socket.onopen = () => {
          const speechConfig = {
            context: {
              synthesis: {
                audio: {
                  metadataoptions: { sentenceBoundaryEnabled: false, wordBoundaryEnabled: false },
                  outputFormat: EDGE_AUDIO_FORMAT,
                },
              },
            },
          };
          socket.send(edgeMessage(
            {
              "X-Timestamp": new Date().toISOString(),
              "Content-Type": "application/json; charset=utf-8",
              Path: "speech.config",
            },
            JSON.stringify(speechConfig),
          ));

          const locale = clean(voice.locale) || "en-US";
          const gender = clean(voice.gender) || "Female";
          const ssml =
            `<speak version='1.0' xml:lang='${xmlEscape(locale)}'>` +
            `<voice xml:lang='${xmlEscape(locale)}' xml:gender='${xmlEscape(gender)}' name='${xmlEscape(voice.name)}'>` +
            `<prosody rate='0%'>${xmlEscape(text)}</prosody>` +
            "</voice></speak>";
          socket.send(edgeMessage(
            {
              "X-RequestId": requestId,
              "X-Timestamp": new Date().toISOString(),
              "Content-Type": "application/ssml+xml",
              Path: "ssml",
            },
            ssml,
          ));
        };

        socket.onmessage = (event) => {
          if (typeof event.data === "string") {
            if (event.data.includes("Path:turn.end")) {
              if (!chunks.length) {
                finish(new Error("Edge TTS returned empty audio."));
                return;
              }
              finish(null, new Blob(chunks, { type: "audio/mpeg" }));
            }
            return;
          }
          const buffer = event.data;
          if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 3) {
            return;
          }
          const bytes = new Uint8Array(buffer);
          const headerLength = (bytes[0] << 8) + bytes[1];
          const audioOffset = 2 + headerLength;
          if (audioOffset < bytes.length) {
            chunks.push(bytes.slice(audioOffset));
          }
        };
        socket.onerror = () => finish(new Error("Edge TTS websocket failed."));
        socket.onclose = () => {
          if (!settled && chunks.length) {
            finish(null, new Blob(chunks, { type: "audio/mpeg" }));
          } else if (!settled) {
            finish(new Error("Edge TTS connection closed."));
          }
        };
      });

      const requestEdgeTtsUrl = async (text, voiceInfo) => URL.createObjectURL(await requestEdgeTtsBlob(text, voiceInfo));

      const requestSpaceWTtsBlob = async (text, selectedValue) => {
        const voiceValue = normalizedCacheVoiceValue(selectedValue);
        if (voiceValue.startsWith("sot:")) {
          const serverAudio = await requestServerSpaceWTtsAudio(text, voiceValue).catch(() => null);
          if (serverAudio && serverAudio.blob instanceof Blob) {
            return serverAudio.blob;
          }
          return requestSoundOfTextBlob(text, voiceValue.slice(4) || "en-US");
        }
        if (voiceValue.startsWith("microsoft:")) {
          return requestEdgeTtsBlob(text, getEdgeVoiceInfo(voiceValue));
        }
        throw new Error("Voice is not cacheable.");
      };

      const getOrCreateSpaceWTtsAudio = async (text, selectedValue, options = {}) => {
        const phrase = clean(text);
        const voiceValue = normalizedCacheVoiceValue(selectedValue);
        const key = spaceWAudioCacheKey(phrase, voiceValue);
        if (!phrase || !voiceValue || !key) {
          return null;
        }
        let cached = await readSpaceWAudioRecord(key);
        const legacyKey = legacySpaceWAudioCacheKey(phrase, voiceValue);
        if (!cached && legacyKey && legacyKey !== key) {
          const legacy = await readSpaceWAudioRecord(legacyKey);
          if (legacy && legacy.blob instanceof Blob) {
            const migrated = await writeSpaceWAudioRecord({ ...legacy, key, shared_media: true, migrated_at: new Date().toISOString() });
            if (migrated) {
              void deleteSpaceWAudioRecord(legacyKey);
              cached = { ...legacy, key };
            }
          }
        }
        if (cached && cached.blob instanceof Blob) {
          return {
            key,
            blob: cached.blob,
            timings: Array.isArray(cached.timings) ? cached.timings : [],
            cached: true,
          };
        }
        if (pendingSpaceWAudioCacheTasks.has(key)) {
          return pendingSpaceWAudioCacheTasks.get(key);
        }
        const task = (async () => {
          const blob = await requestSpaceWTtsBlob(phrase, voiceValue);
          let timings = [];
          try {
            timings = await buildAudioGuidedTimingsFromBlob(blob);
          } catch (error) {
            timings = [];
          }
          await writeSpaceWAudioRecord({
            key,
            blob,
            timings,
            mime: clean(blob.type) || "audio/mpeg",
            voice: voiceValue,
            text_hash: hashSpaceWText(phrase.toLowerCase().replace(/\s+/g, " ")),
            lesson: currentSpaceWCache.identity || "",
            node: Number(options.nodeIndex ?? currentNodeIndex) || 0,
            created_at: new Date().toISOString(),
          });
          return { key, blob, timings, cached: false };
        })().finally(() => {
          pendingSpaceWAudioCacheTasks.delete(key);
        });
        pendingSpaceWAudioCacheTasks.set(key, task);
        return task;
      };

      const spaceWUrlAudioCacheKey = (url) => {
        const source = clean(url);
        if (!source || /^data:|^blob:/i.test(source)) {
          return "";
        }
        const assetId = audioMediaAssetId({ url: source });
        return assetId ? `${GENERIC_MEDIA_AUDIO_CACHE_PREFIX}${assetId}` : "";
      };

      // 2026-07-21: Preserve already-downloaded per-user URL audio while moving it to stable shared media identity.
      const legacySpaceWUrlAudioCacheKey = (url) => {
        const source = clean(url);
        if (!source || /^data:|^blob:/i.test(source)) {
          return "";
        }
        if (/\/server-data\/qm-sound(?:\?|$)/i.test(source)) {
          return [spaceWUserKey(), "qm-sound-url", hashSpaceWText(source)].join(":");
        }
        const lessonKey = currentSpaceWCache && currentSpaceWCache.identity
          ? currentSpaceWCache.identity
          : hashSpaceWText(clean(currentLessonSource.title || currentLessonSource.name || "space-w"));
        return [spaceWUserKey(), lessonKey, "embedded-url", hashSpaceWText(source)].join(":");
      };

      const getOrCreateSpaceWUrlAudio = async (url, timings = [], options = {}) => {
        const source = clean(url);
        const key = spaceWUrlAudioCacheKey(source);
        if (!source || !key) {
          return null;
        }
        let cached = await readSpaceWAudioRecord(key);
        const legacyKey = legacySpaceWUrlAudioCacheKey(source);
        if (!cached && legacyKey && legacyKey !== key) {
          const legacy = await readSpaceWAudioRecord(legacyKey);
          if (legacy && legacy.blob instanceof Blob) {
            const migrated = await writeSpaceWAudioRecord({ ...legacy, key, shared_media: true, migrated_at: new Date().toISOString() });
            if (migrated) {
              void deleteSpaceWAudioRecord(legacyKey);
              cached = { ...legacy, key };
            }
          }
        }
        if (cached && cached.blob instanceof Blob) {
          return {
            key,
            blob: cached.blob,
            timings: Array.isArray(cached.timings) ? cached.timings : (Array.isArray(timings) ? timings : []),
            cached: true,
          };
        }
        if (pendingSpaceWAudioCacheTasks.has(key)) {
          return pendingSpaceWAudioCacheTasks.get(key);
        }
        const task = (async () => {
          const blob = await fetchAudioBlob(source, { timeoutMs: Number(options.timeoutMs || 18000) || 18000 });
          const nextTimings = Array.isArray(timings) && timings.length ? timings : [];
          await writeSpaceWAudioRecord({
            key,
            blob,
            timings: nextTimings,
            mime: clean(blob.type) || "audio/mpeg",
            voice: clean(options.voice || "embedded"),
            lesson: currentSpaceWCache.identity || "",
            node: Number(options.nodeIndex ?? currentNodeIndex) || 0,
            source_url_hash: hashSpaceWText(source),
            created_at: new Date().toISOString(),
          });
          return { key, blob, timings: nextTimings, cached: false };
        })().finally(() => {
          pendingSpaceWAudioCacheTasks.delete(key);
        });
        pendingSpaceWAudioCacheTasks.set(key, task);
        return task;
      };

      const spaceWNodeEnglishText = (node = {}) => clean(node.en ?? node.e ?? node.answer ?? "");

      const lessonCachePriorityIndexes = (length = 0, startIndex = 0) => {
        const total = Math.max(0, Number(length) || 0);
        if (!total) {
          return [];
        }
        const start = Math.max(0, Math.min(total - 1, Math.round(Number(startIndex) || 0)));
        const order = [start];
        for (let offset = 1; order.length < total; offset += 1) {
          const forward = start + offset;
          const backward = start - offset;
          if (forward < total) {
            order.push(forward);
          }
          if (backward >= 0) {
            order.push(backward);
          }
        }
        return order;
      };

      const orderNodesForCache = (nodes = [], startIndex = 0) => {
        const source = Array.isArray(nodes) ? nodes : [];
        return lessonCachePriorityIndexes(source.length, startIndex)
          .map((index) => ({ node: source[index], index }))
          .filter((item) => item.node);
      };

      const prioritizedAudioTasks = (tasks = [], startIndex = 0) => {
        const center = Math.max(0, Math.round(Number(startIndex) || 0));
        return (Array.isArray(tasks) ? tasks : [])
          .map((task, order) => ({ task, order }))
          .sort((left, right) => {
            const leftPriority = Number(left.task && left.task.priorityIndex);
            const rightPriority = Number(right.task && right.task.priorityIndex);
            const leftHasPriority = Number.isFinite(leftPriority);
            const rightHasPriority = Number.isFinite(rightPriority);
            if (leftHasPriority || rightHasPriority) {
              return (leftHasPriority ? leftPriority : Number.MAX_SAFE_INTEGER)
                - (rightHasPriority ? rightPriority : Number.MAX_SAFE_INTEGER)
                || left.order - right.order;
            }
            const leftNode = Number.isFinite(Number(left.task && left.task.nodeIndex)) ? Number(left.task.nodeIndex) : Number.MAX_SAFE_INTEGER;
            const rightNode = Number.isFinite(Number(right.task && right.task.nodeIndex)) ? Number(right.task.nodeIndex) : Number.MAX_SAFE_INTEGER;
            const leftDistance = leftNode === Number.MAX_SAFE_INTEGER ? Number.MAX_SAFE_INTEGER : Math.abs(leftNode - center);
            const rightDistance = rightNode === Number.MAX_SAFE_INTEGER ? Number.MAX_SAFE_INTEGER : Math.abs(rightNode - center);
            return leftDistance - rightDistance || leftNode - rightNode || left.order - right.order;
          })
          .map((entry) => entry.task);
      };
