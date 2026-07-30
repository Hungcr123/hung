

      const markQuestionSelectAnswerTargets = (item) => {
        const requiredRootKeys = questionSelectRootAnswerKeys(item);
        const usedRootCounts = new Map();
        const rootKeyCounts = questionExactCounts(requiredRootKeys);
        const requiredTokenCounts = questionTokenCounts(questionSelectAnswerTokens(item));
        const usedTokenCounts = new Map();
        document.querySelectorAll(".ft-q-select-root-token").forEach((node) => {
          node.classList.remove("is-selected", "is-token-wrong", "is-confirming", "is-answer-lit");
          node.style.removeProperty("--q-answer-lit-delay");
          const start = Math.max(0, Math.floor(Number(node.dataset ? node.dataset.qSelectStart : 0) || 0));
          const end = Math.max(start, Math.floor(Number(node.dataset ? node.dataset.qSelectEnd : start) || start));
          const token = clean(node.dataset ? node.dataset.qSelectToken : node.textContent);
          const exactKey = `${start}:${end}:${questionAnswerKey(token)}`;
          const key = questionAnswerKey(token);
          if (requiredRootKeys.length) {
            const used = usedRootCounts.get(exactKey) || 0;
            const needed = rootKeyCounts.get(exactKey) || 0;
            if (exactKey && used < needed) {
              usedRootCounts.set(exactKey, used + 1);
              node.classList.add("is-selected", "is-confirming");
            }
            return;
          }
          const used = usedTokenCounts.get(key) || 0;
          const needed = requiredTokenCounts.get(key) || 0;
          if (key && used < needed) {
            usedTokenCounts.set(key, used + 1);
            node.classList.add("is-selected", "is-confirming");
          }
        });
        if (questionPictureRegionLayer) {
          const requiredRegions = new Set(questionSelectRequiredRegions(item));
          questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer").forEach((node) => {
            const key = clean(node.dataset ? node.dataset.selectRegion : "");
            node.classList.remove("is-selected", "is-token-wrong", "is-confirming", "is-answer-lit");
            node.style.removeProperty("--q-answer-lit-delay");
            if (requiredRegions.has(key)) {
              node.classList.add("is-selected", "is-confirming");
            }
          });
        }
        refreshQuestionSelectRootMergedHighlights();
        qRootText?.querySelectorAll(".ft-q-select-root-merge").forEach((node) => node.classList.add("is-confirming"));
        updateQuestionSelectProgressCard(item);
      };

      const questionSelectRevealAnswerNodes = () => {
        const nodes = [];
        if (qRootText) {
          const merged = Array.from(qRootText.querySelectorAll(".ft-q-select-root-merge"));
          const mergedEntries = new Set();
          merged.forEach((node) => {
            nodes.push(node);
            const rect = node.getBoundingClientRect();
            qRootText.querySelectorAll(".ft-q-select-root-overlay.is-selected").forEach((button) => {
              const buttonRect = button.getBoundingClientRect();
              if (
                buttonRect.left >= rect.left - 1
                && buttonRect.right <= rect.right + 1
                && buttonRect.top >= rect.top - 1
                && buttonRect.bottom <= rect.bottom + 1
              ) {
                mergedEntries.add(button);
              }
            });
          });
          qRootText.querySelectorAll(".ft-q-select-root-overlay.is-selected").forEach((node) => {
            if (!mergedEntries.has(node)) {
              nodes.push(node);
            }
          });
        }
        if (questionPictureRegionLayer) {
          questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer.is-selected").forEach((node) => nodes.push(node));
        }
        return nodes.filter((node) => node && node.getBoundingClientRect);
      };

      const runQuestionSelectAnswerRevealConnectors = (startClientPoint = null) => {
        if (!shellNode) {
          return;
        }
        const layer = ensureQuestionSelectConnectorLayer();
        if (!layer) {
          return;
        }
        if (questionSelectAnswerRevealTimer) {
          window.clearTimeout(questionSelectAnswerRevealTimer);
          questionSelectAnswerRevealTimer = 0;
        }
        questionSelectAnswerRevealActive = true;
        layer.innerHTML = "";
        layer.classList.remove("is-complete");
        layer.classList.add("is-live", "is-answer-reveal");
        const start = questionClientPointInShell(startClientPoint);
        const anchors = questionSelectRevealAnswerNodes();
        clearQuestionSelectAnswerLitTargets();
        appendQuestionSelectConnectorNode(layer, start, "is-source");
        anchors.forEach((node, index) => {
          const rect = questionSelectRectInShell(node, 0);
          if (!rect) {
            return;
          }
          node.classList.add("is-answer-lit");
          node.style.setProperty("--q-answer-lit-delay", `${Math.min(620, 380 + index * 48)}ms`);
          const target = { x: rect.cx, y: rect.cy };
          const elbowX = start.x + Math.max(36, Math.min(180, Math.abs(target.x - start.x) * 0.38)) * (target.x >= start.x ? 1 : -1);
          const elbowA = { x: elbowX, y: start.y };
          const elbowB = { x: elbowX, y: target.y };
          const delay = `${Math.min(420, index * 72)}ms`;
          [appendQuestionSelectConnectorSegment(layer, start, elbowA, "is-branch"),
            appendQuestionSelectConnectorSegment(layer, elbowA, elbowB, "is-branch is-elbow"),
            appendQuestionSelectConnectorSegment(layer, elbowB, target, "is-terminal")].forEach((segment) => {
            if (segment) {
              segment.style.animationDelay = delay;
            }
          });
          [appendQuestionSelectConnectorNode(layer, elbowA, "is-junction"),
            appendQuestionSelectConnectorNode(layer, elbowB, "is-junction"),
            appendQuestionSelectConnectorNode(layer, target, "is-end")].forEach((dot) => {
            if (dot) {
              dot.style.animationDelay = delay;
            }
          });
        });
        questionSelectAnswerRevealTimer = window.setTimeout(() => {
          questionSelectAnswerRevealTimer = 0;
          questionSelectAnswerRevealActive = false;
          if (stageNode) {
            stageNode.classList.remove("is-question-select-answer-revealing");
          }
          if (layer) {
            layer.innerHTML = "";
            layer.classList.remove("is-live", "is-answer-reveal");
          }
          clearQuestionSelectAnswerLitTargets();
        }, 2850);
      };

      const showQuestionSelectAnswerReveal = (item, event = null) => {
        if (!item || !isQuestionSelectItem(item)) {
          return false;
        }
        renderQuestionSelectTargetsForItem(item);
        if (stageNode) {
          stageNode.classList.add("is-question-select-answer-revealing");
        }
        markQuestionSelectAnswerTargets(item);
        setQuestionAnswerFeedback(`Answer: ${questionSelectAnswerText(item) || clean(item.answer)}`, "ok");
        setQuestionAnswerControls(true);
        if (qShowAnswerButton) {
          qShowAnswerButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qNextButton) {
          qNextButton.disabled = false;
        }
        updateQuestionProgressLabel();
        if (qSelectSubmitButton) {
          qSelectSubmitButton.disabled = true;
        }
        const startClientPoint = event && Number.isFinite(Number(event.clientX))
          ? { x: event.clientX, y: event.clientY }
          : questionLastPointerClient;
        const reveal = () => {
          if (!questionModeActive || currentQuestionItem() !== item) {
            return;
          }
          runQuestionSelectAnswerRevealConnectors(startClientPoint);
          focusQuestionNextControl(2850);
          queueQuestionProgressSave(120);
        };
        if (isQuestionMobileFlow()) {
          setQuestionMobilePanel("root", { skipFocus: true });
          window.setTimeout(reveal, 140);
          return true;
        }
        const target = qRootCard || questionSelectTargetCameraTarget(item) || qRootText;
        if (target) {
          panQuestionCameraTo(target, reveal, 880, {
            duration: 880,
            forceLayout: true,
          });
        } else {
          reveal();
        }
        return true;
      };

      const handleQuestionSelectTokenClick = (button) => {
        const item = currentQuestionItem();
        if (!button || !item || !isQuestionSelectItem(item) || isQuestionGuideItem(item)) {
          return;
        }
        if (button.disabled || button.classList.contains("is-locked")) {
          return;
        }
        if (questionSelectCompletionTimer) {
          return;
        }
        const token = clean(button.dataset ? button.dataset.token : button.textContent);
        if (!token) {
          return;
        }
        const selected = button.classList.toggle("is-selected");
        button.classList.remove("is-token-correct", "is-token-wrong", "is-token-pulse");
        void button.offsetWidth;
        if (!selected) {
          setQuestionAnswerFeedback("Token removed. Select the full answer again.", "");
          updateQuestionSelectProgressCard(item);
          focusQuestionSelectSubmitButton();
          return;
        }
        button.classList.add("is-token-pulse");
        void playEffectSoundAsync("open");
        updateQuestionSelectProgressCard(item);
        setQuestionAnswerFeedback("Targets selected. Press Lock when you are ready.", "");
        focusQuestionSelectSubmitButton();
      };

      const questionAnswerCharacterCount = (value) => Array.from(clean(value)).length;
      const questionAnswerWordCount = (value) => {
        const text = clean(value);
        return text ? text.split(/\s+/).filter(Boolean).length : 0;
      };

      function questionInputCountTargetDisplay(counts) {
        const unique = Array.from(new Set((Array.isArray(counts) ? counts : [])
          .map((count) => Math.max(0, Math.floor(Number(count) || 0)))
          .filter((count) => count > 0))).sort((a, b) => a - b);
        if (!unique.length) {
          return "";
        }
        if (unique.length === 1) {
          return String(unique[0]);
        }
        return `${unique[0]}-${unique[unique.length - 1]}`;
      }

      function questionInputLengthDisplay(question, value = qAnswerInput ? qAnswerInput.value : "") {
        const accepted = questionAcceptedAnswers(question);
        const charTarget = questionInputCountTargetDisplay(accepted.map(questionAnswerCharacterCount));
        const wordTarget = questionInputCountTargetDisplay(accepted.map(questionAnswerWordCount));
        if (!charTarget && !wordTarget) {
          return null;
        }
        const typedChars = questionAnswerCharacterCount(value);
        const typedWords = questionAnswerWordCount(value);
        const primary = wordTarget ? `${typedWords}/${wordTarget}` : `${typedChars}/${charTarget}`;
        const label = wordTarget && charTarget ? `${typedChars}/${charTarget} ký tự` : "Ký tự";
        return {
          primary,
          label,
          title: wordTarget
            ? `Số từ đã nhập: ${primary}. Số ký tự: ${typedChars}/${charTarget || "?"}.`
            : `Số ký tự đã nhập: ${primary}.`,
          signature: `${primary}|${label}`,
        };
      }

      function updateQuestionInputLengthRadar(question, enabled = false) {
        if (!qInputLengthRadar || !qInputLengthCount) {
          return;
        }
        const display = enabled && question ? questionInputLengthDisplay(question) : null;
        const primary = display && display.primary ? display.primary : "";
        qInputLengthRadar.classList.toggle("ft-q-show-answer-hidden", !display);
        if (!primary) {
          qInputLengthCount.textContent = "0";
          if (qInputLengthLabel) {
            qInputLengthLabel.textContent = "Từ";
          }
          qInputLengthRadar.dataset.answerLength = "";
          qInputLengthRadar.removeAttribute("title");
          qInputLengthRadar.classList.remove("is-length-updated");
          return;
        }
        qInputLengthCount.textContent = primary;
        if (qInputLengthLabel) {
          qInputLengthLabel.textContent = display.label || "Từ";
        }
        qInputLengthRadar.title = display.title || "";
        if (qInputLengthRadar.dataset.answerLength !== display.signature) {
          qInputLengthRadar.dataset.answerLength = display.signature;
          qInputLengthRadar.classList.remove("is-length-updated");
          void qInputLengthRadar.offsetWidth;
          qInputLengthRadar.classList.add("is-length-updated");
        }
      }

      const setQuestionFeedback = (message, tone = "") => {
        if (!qFeedback) {
          return;
        }
        qFeedback.textContent = message;
        qFeedback.classList.toggle("is-ok", tone === "ok");
        qFeedback.classList.toggle("is-error", tone === "error");
      };

      const questionRootChoiceSignalDesktopAvailable = () => Boolean(
        qRootChoiceSignal
        && qRootChoiceSignalState
        && qRootChoiceSignalText
        && qRootCard
        && !qRootCard.classList.contains("is-hidden")
        && window.matchMedia("(min-width: 761px)").matches
      );

      const questionRootChoiceSignalCurrentItem = () => {
        try {
          return currentQuestionItem();
        } catch (_) {
          return null;
        }
      };

      const questionRootChoiceSignalShouldRoute = (options = {}) => {
        if (!questionRootChoiceSignalDesktopAvailable()) {
          return false;
        }
        if (options && options.force) {
          return true;
        }
        const item = questionRootChoiceSignalCurrentItem();
        if (!item || isQuestionGuideItem(item) || isQuestionTypedItem(item)) {
          return false;
        }
        return true;
      };

      const updateQuestionRootChoiceSignalLive = () => {
        if (!qRootChoiceSignal || !qRootChoiceSignalState || !qRootChoiceSignalText) {
          return false;
        }
        const hasStatus = Boolean(clean(qRootChoiceSignalState.textContent || ""));
        const hasInfo = Boolean(clean(qRootChoiceSignalText.textContent || ""));
        const live = hasStatus || hasInfo;
        qRootChoiceSignal.classList.toggle("is-live", live);
        return live;
      };

      const clearQuestionRootChoiceSignalStatus = () => {
        if (qRootChoiceSignalState) {
          qRootChoiceSignalState.textContent = "";
        }
        if (qRootChoiceSignal) {
          qRootChoiceSignal.classList.remove("is-ok", "is-error");
        }
        updateQuestionRootChoiceSignalLive();
      };

      const clearQuestionRootChoiceSignalInfo = () => {
        if (questionInfoTypingTimer) {
          window.clearTimeout(questionInfoTypingTimer);
          questionInfoTypingTimer = 0;
        }
        if (qRootChoiceSignalText) {
          qRootChoiceSignalText.textContent = "";
          qRootChoiceSignalText.scrollTop = 0;
        }
        updateQuestionRootChoiceSignalLive();
      };

      const clearQuestionRootChoiceSignal = () => {
        clearQuestionRootChoiceSignalStatus();
        clearQuestionRootChoiceSignalInfo();
      };

      const setQuestionRootChoiceSignalStatus = (message, tone = "", options = {}) => {
        const text = clean(message);
        if (!text) {
          clearQuestionRootChoiceSignalStatus();
          return false;
        }
        if (!questionRootChoiceSignalShouldRoute(options)) {
          return false;
        }
        qRootChoiceSignalState.textContent = text;
        qRootChoiceSignal.classList.toggle("is-ok", tone === "ok");
        qRootChoiceSignal.classList.toggle("is-error", tone === "error");
        updateQuestionRootChoiceSignalLive();
        return true;
      };

      const typeQuestionRootChoiceSignalText = (text) => {
        if (!qRootChoiceSignalText) {
          return;
        }
        if (questionInfoTypingTimer) {
          window.clearTimeout(questionInfoTypingTimer);
          questionInfoTypingTimer = 0;
        }
        const fullText = clean(text);
        qRootChoiceSignalText.textContent = "";
        qRootChoiceSignalText.scrollTop = 0;
        let index = 0;
        const cometColor = "#ff9f2f";
        const tick = () => {
          index = Math.min(fullText.length, index + Math.max(1, Math.ceil(fullText.length / 76)));
          const visible = fullText.slice(0, index);
          const activeIndex = Math.max(0, visible.length - 1);
          qRootChoiceSignalText.innerHTML = renderQuestionRootTrailSegment(visible, 0, activeIndex, cometColor);
          if (index < fullText.length) {
            questionInfoTypingTimer = window.setTimeout(tick, 14 + Math.random() * 18);
          } else {
            questionInfoTypingTimer = window.setTimeout(() => {
              qRootChoiceSignalText.textContent = fullText;
              questionInfoTypingTimer = 0;
            }, 260);
          }
        };
        tick();
      };

      const setQuestionRootChoiceSignalInfo = (message, tone = "", options = {}) => {
        const text = clean(message);
        if (!text) {
          clearQuestionRootChoiceSignalInfo();
          return false;
        }
        if (!questionRootChoiceSignalShouldRoute(options)) {
          return false;
        }
        if (tone) {
          qRootChoiceSignal.classList.toggle("is-ok", tone === "ok");
          qRootChoiceSignal.classList.toggle("is-error", tone === "error");
        }
        qRootChoiceSignal.classList.add("is-live");
        if (options && options.immediate) {
          if (questionInfoTypingTimer) {
            window.clearTimeout(questionInfoTypingTimer);
            questionInfoTypingTimer = 0;
          }
          qRootChoiceSignalText.textContent = text;
          qRootChoiceSignalText.scrollTop = 0;
          updateQuestionRootChoiceSignalLive();
        } else {
          typeQuestionRootChoiceSignalText(text);
        }
        return true;
      };

      const setQuestionAnswerFeedback = (message, tone = "") => {
        if (!qAnswerFeedback) {
          return;
        }
        const routedToRoot = setQuestionRootChoiceSignalStatus(message, tone);
        qAnswerFeedback.classList.toggle("is-routed-to-root", routedToRoot);
        if (routedToRoot) {
          qAnswerFeedback.textContent = "";
          qAnswerFeedback.classList.remove("is-ok", "is-error");
          return;
        }
        qAnswerFeedback.textContent = message;
        qAnswerFeedback.classList.toggle("is-ok", tone === "ok");
        qAnswerFeedback.classList.toggle("is-error", tone === "error");
      };

      const questionConnectorPairs = () => [
        [qPictureCard, qConnectorPicture],
        [qAudioCard, qConnectorAudio],
        [qQuestionCard, qConnectorQuestion],
        [qInfoCard, qConnectorInfo],
      ];

      const clearQuestionConnectorFocus = () => {
        if (questionConnectorFocusTimer) {
          window.clearTimeout(questionConnectorFocusTimer);
          questionConnectorFocusTimer = 0;
        }
        questionConnectorPairs().forEach(([card, connector]) => {
          if (card) {
            card.classList.remove("is-connector-focused");
          }
          if (connector) {
            connector.classList.remove("is-focused");
          }
        });
        if (questionRootInfoConnector) {
          if (!questionRootInfoConnector.classList.contains("is-region-rail")) {
            questionRootInfoConnector.classList.remove("is-focused");
          }
        }
        questionRootInfoExtraConnectors.forEach((connector) => {
          if (!connector.classList.contains("is-region-rail")) {
            connector.classList.remove("is-focused");
          }
        });
      };

      const activateQuestionConnector = (card, connector, transient = true) => {
        if (!card || !connector || !card.classList.contains("is-live") || !connector.classList.contains("is-live")) {
          return;
        }
        clearQuestionConnectorFocus();
        card.classList.add("is-connector-focused");
        connector.classList.add("is-focused");
        if (transient) {
          questionConnectorFocusTimer = window.setTimeout(clearQuestionConnectorFocus, 2600);
        }
      };

      const hideQuestionCards = () => {
        setQuestionRevealAnimationsActive(false);
        if (shellNode) {
          shellNode.classList.remove("is-picture-card-hovering");
        }
        hideQuestionPictureAnswerCards();
        hideQuestionRootInfo(true);
        clearQuestionConnectorFocus();
        clearQuestionRootFocus();
        clearAllQuestionCardFxActive();
        stopQuestionReveal();
        stopQuestionRootHighlightAnimation();
        stopQuestionRootNotice();
        if (questionInfoTypingTimer) {
          window.clearTimeout(questionInfoTypingTimer);
          questionInfoTypingTimer = 0;
        }
        stopQuestionInfoRevealWait();
        clearQuestionInfoHideTimer();
        questionInfoAudioClip = null;
        [qPictureCard, qAudioCard, qQuestionCard, qInfoCard, qConnectorPicture, qConnectorAudio, qConnectorQuestion, qConnectorInfo].forEach((node) => {
          if (node) {
            node.classList.remove("is-live", "is-preparing", "is-hiding", "is-info-presenting", "is-connector-focused", "is-focused");
          }
        });
        if (qQuestionCard) {
          qQuestionCard.classList.remove("is-input-question");
        }
        updateQuestionInputLengthRadar(null, false);
        if (shellNode) {
          shellNode.style.removeProperty("--q-layout-height");
          shellNode.style.removeProperty("--q-stage-shell-justify");
        }
        if (qPictureImg) {
          qPictureImg.removeAttribute("src");
          qPictureImg.alt = "";
        }
        resetQuestionPictureNaturalSize();
        clearQuestionPictureSkin();
        if (qPictureCard) {
          qPictureCard.classList.remove(...QUESTION_SHIP_CLASSES);
          qPictureCard.style.removeProperty("--q-picture-region-color");
          qPictureCard.style.removeProperty("--q-picture-region-rgb");
        }
        if (qPictureCaption) {
          qPictureCaption.textContent = "";
        }
        if (qAudioText) {
          qAudioText.textContent = "";
        }
        if (qAudioVoice) {
          qAudioVoice.textContent = "";
        }
        if (qAudioCard) {
          qAudioCard.classList.remove("is-playing");
        }
        if (qRootCard) {
          qRootCard.classList.remove("is-typing");
          qRootCard.classList.remove("is-layout-staging");
          qRootCard.style.setProperty("--q-root-type-progress", "0%");
        }
        if (qQuestionText) {
          qQuestionText.textContent = "";
        }
        if (qQuestionAudioButton) {
          qQuestionAudioButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qSelectSubmitButton) {
          qSelectSubmitButton.classList.add("ft-q-show-answer-hidden");
          qSelectSubmitButton.disabled = true;
        }
        if (qInfoText) {
          qInfoText.textContent = "";
        }
        clearQuestionRootChoiceSignal();
        if (qInfoPlayButton) {
          qInfoPlayButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qChoiceList) {
          qChoiceList.innerHTML = "";
          qChoiceList.classList.remove("is-picture-question-branch", "is-select-token-grid");
        }
        if (qAnswerInput) {
          qAnswerInput.value = "";
          syncQuestionAnswerInputMemory();
          resizeQuestionAnswerInput();
          clearQuestionInputFlare();
        }
        if (qInputRow) {
          qInputRow.classList.remove("is-picture-question-block");
        }
        clearQuestionInputAccent();
        if (qQuestionCount) {
          qQuestionCount.textContent = "0/0";
        }
        setQuestionAnswerFeedback("");
      };

      function ensureQuestionTypingSkipPortal() {
        if (questionTypingSkipPortalButton || !document.body) {
          return questionTypingSkipPortalButton;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "ft-q-typing-skip-portal";
        button.textContent = "Skip typing";
        button.title = "Skip root typing";
        button.addEventListener("click", () => skipQuestionTyping());
        document.body.appendChild(button);
        questionTypingSkipPortalButton = button;
        return button;
      }

      function setQuestionTypingSkipAvailable(active) {
        const live = Boolean(active);
        if (stageNode) {
          stageNode.classList.toggle("is-question-root-typing", live);
        }
        if (qSkipTypeButton) {
          qSkipTypeButton.disabled = !live;
        }
        const portal = live ? ensureQuestionTypingSkipPortal() : questionTypingSkipPortalButton;
        if (portal) {
          portal.disabled = !live;
          portal.classList.toggle("is-live", live);
        }
      }

      function pinQuestionRootTypingLayout(text = questionTypingFullText, node = questionCurrentNode) {
        if (!stageNode || !shellNode || !qRootCard || isQuestionMobileFlow()) {
          return;
        }
        const viewport = questionViewportSize();
        const layoutHeight = viewport.height
          ? viewport.height / questionResponsiveLayoutScale()
          : 720;
        const reservedHeight = measureQuestionRootReservedHeight(text, node);
        questionTypingRootReservedHeight = Number.isFinite(Number(reservedHeight))
          ? Math.max(0, Number(reservedHeight))
          : null;
        if (questionTypingRootReservedHeight) {
          qRootCard.style.setProperty("--q-root-reserved-height", `${Math.ceil(questionTypingRootReservedHeight)}px`);
          shellNode.style.setProperty("--q-root-height", `${Math.ceil(questionTypingRootReservedHeight)}px`);
        } else {
          qRootCard.style.removeProperty("--q-root-reserved-height");
        }
        questionTypingRootTopPadding = questionRootTypingTopPadding(
          layoutHeight,
          isQuestionVisualProfileActive(),
          questionTypingRootReservedHeight,
        );
        shellNode.style.setProperty(
          "--q-question-top-padding",
          `${Math.ceil(questionTypingRootTopPadding)}px`,
        );
        if (stageNode.scrollTop > 0) {
          stageNode.scrollTop = 0;
        }
        positionQuestionSideCards({ force: true });
        centerQuestionRootHorizontalOrigin();
      }

      function keepQuestionRootTypingTopVisible() {
        if (!stageNode || !qRootCard || !qRootCard.classList.contains("is-typing") || isQuestionMobileFlow()) {
          return false;
        }
        const rootRect = qRootCard.getBoundingClientRect();
        const stageRect = stageNode.getBoundingClientRect();
        if (!rootRect.height || !stageRect.height) {
          return false;
        }
        const safeTop = stageRect.top + Math.max(14, Math.min(42, stageNode.clientHeight * 0.055));
        if (rootRect.top >= safeTop) {
          return false;
        }
        const maxTop = Math.max(0, stageNode.scrollHeight - stageNode.clientHeight);
        const nextTop = Math.max(0, Math.min(maxTop, stageNode.scrollTop + rootRect.top - safeTop));
        if (Math.abs(nextTop - stageNode.scrollTop) < 1) {
          return false;
        }
        stageNode.scrollTop = nextTop;
        return true;
      }

      const stopQuestionTyping = () => {
        questionTypingToken += 1;
        if (questionRootOpenTypingTimer) {
          window.clearTimeout(questionRootOpenTypingTimer);
          questionRootOpenTypingTimer = 0;
        }
        if (questionTypingTimer) {
          window.clearTimeout(questionTypingTimer);
          questionTypingTimer = 0;
        }
        setQuestionTypingSkipAvailable(false);
        hideQuestionTypingComet();
        if (qRootCard) {
          qRootCard.classList.remove("is-typing");
        }
      };

      const clearQuestionCameraPanTimer = () => {
        questionCameraPanToken += 1;
        if (questionCameraPanTimer) {
          window.clearTimeout(questionCameraPanTimer);
          questionCameraPanTimer = 0;
        }
      };

      function clearQuestionCardOnlyViewTimers() {
        questionCardOnlyViewToken += 1;
        questionCardOnlyViewTimers.forEach((timer) => window.clearTimeout(timer));
        questionCardOnlyViewTimers.clear();
      }

      function beginQuestionHighlightCameraFocus() {
        questionHighlightCameraFocusToken += 1;
        clearQuestionCardOnlyViewTimers();
        clearQuestionManualFocusTimer();
        return questionHighlightCameraFocusToken;
      }

      function endQuestionHighlightCameraFocus(token = questionHighlightCameraFocusToken) {
        if (!token || token === questionHighlightCameraFocusToken) {
          questionHighlightCameraFocusToken = 0;
        }
      }

      function clearQuestionInputFlare() {
        if (questionInputFlareTimer) {
          window.clearTimeout(questionInputFlareTimer);
          questionInputFlareTimer = 0;
        }
        if (qInputRow) {
          qInputRow.querySelectorAll(".ft-q-input-char-flare").forEach((node) => node.remove());
        }
      }

      function syncQuestionAnswerInputMemory() {
        questionAnswerInputLastValue = qAnswerInput ? qAnswerInput.value : "";
      }

      function questionAnswerInputMaxHeight(input) {
        const style = window.getComputedStyle(input);
        const fontSize = Number.parseFloat(style.fontSize) || 28;
        let lineHeight = Number.parseFloat(style.lineHeight);
        if (!Number.isFinite(lineHeight)) {
          lineHeight = fontSize * 1.18;
        }
        const padding = (Number.parseFloat(style.paddingTop) || 0) + (Number.parseFloat(style.paddingBottom) || 0);
        const border = (Number.parseFloat(style.borderTopWidth) || 0) + (Number.parseFloat(style.borderBottomWidth) || 0);
        return Math.ceil((lineHeight * 3) + padding + border);
      }

      function updateQuestionInputScrollbar() {
        if (!qAnswerInput) {
          return;
        }
        const scrollHeight = qAnswerInput.scrollHeight || 0;
        const clientHeight = qAnswerInput.clientHeight || 0;
        const scrollable = scrollHeight > clientHeight + 1;
        qAnswerInput.classList.toggle("is-scrollable", scrollable);
      }

      function resizeQuestionAnswerInput() {
        if (!qAnswerInput) {
          return;
        }
        qAnswerInput.style.height = "auto";
        const maxHeight = questionAnswerInputMaxHeight(qAnswerInput);
        const nextHeight = Math.min(qAnswerInput.scrollHeight || maxHeight, maxHeight);
        qAnswerInput.style.height = `${Math.max(0, nextHeight)}px`;
        updateQuestionInputScrollbar();
      }

      function measureQuestionInputTextWidth(input, text) {
        if (!measureQuestionInputTextWidth.canvas) {
          measureQuestionInputTextWidth.canvas = document.createElement("canvas");
        }
        const context = measureQuestionInputTextWidth.canvas.getContext("2d");
        if (!context) {
          return 0;
        }
        const style = window.getComputedStyle(input);
        context.font = `${style.fontStyle} ${style.fontVariant} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
        return context.measureText(text).width;
      }

      function questionInputCaretPoint(input, beforeText, rawChar) {
        if (!questionInputCaretPoint.mirror) {
          const mirror = document.createElement("div");
          mirror.setAttribute("aria-hidden", "true");
          mirror.style.position = "fixed";
          mirror.style.left = "-10000px";
          mirror.style.top = "-10000px";
          mirror.style.visibility = "hidden";
          mirror.style.pointerEvents = "none";
          mirror.style.whiteSpace = "pre-wrap";
          mirror.style.overflowWrap = "break-word";
          mirror.style.wordBreak = "break-word";
          document.body.appendChild(mirror);
          questionInputCaretPoint.mirror = mirror;
        }
        const mirror = questionInputCaretPoint.mirror;
        const style = window.getComputedStyle(input);
        const mirroredProperties = [
          "boxSizing",
          "fontFamily",
          "fontSize",
          "fontStyle",
          "fontVariant",
          "fontWeight",
          "letterSpacing",
          "lineHeight",
          "paddingTop",
          "paddingRight",
          "paddingBottom",
          "paddingLeft",
          "borderTopWidth",
          "borderRightWidth",
          "borderBottomWidth",
          "borderLeftWidth",
        ];
        mirroredProperties.forEach((property) => {
          mirror.style[property] = style[property];
        });
        mirror.style.width = `${input.clientWidth}px`;
        mirror.textContent = beforeText || "";
        const marker = document.createElement("span");
        marker.textContent = rawChar === " " ? "\u00a0" : (rawChar || "\u200b");
        mirror.appendChild(marker);
        const fallbackCharWidth = measureQuestionInputTextWidth(input, rawChar || "M") || 12;
        const markerWidth = marker.offsetWidth || fallbackCharWidth;
        const x = input.offsetLeft + marker.offsetLeft + (markerWidth * 0.5) - input.scrollLeft;
        const y = input.offsetTop + marker.offsetTop + ((marker.offsetHeight || Number.parseFloat(style.lineHeight) || 28) * 0.5) - input.scrollTop;
        return { x, y };
      }

      function showQuestionInputCharFlare(rawChar = "") {
        if (!qInputRow || !qAnswerInput || !rawChar) {
          return;
        }
        resizeQuestionAnswerInput();
        clearQuestionInputFlare();
        const char = rawChar === " " ? "|" : rawChar;
        const input = qAnswerInput;
        const style = window.getComputedStyle(input);
        const caret = typeof input.selectionStart === "number" ? input.selectionStart : input.value.length;
        const beforeText = input.value.slice(0, Math.max(0, caret - rawChar.length));
        const paddingLeft = Number.parseFloat(style.paddingLeft) || 0;
        const paddingRight = Number.parseFloat(style.paddingRight) || 0;
        const caretPoint = questionInputCaretPoint(input, beforeText, rawChar);
        const minX = input.offsetLeft + paddingLeft + 8;
        const maxX = input.offsetLeft + input.clientWidth - paddingRight - 8;
        const minY = input.offsetTop + 14;
        const maxY = input.offsetTop + input.clientHeight - 14;
        const x = Math.max(minX, Math.min(maxX, caretPoint.x));
        const y = Math.max(minY, Math.min(maxY, caretPoint.y));
        const flare = document.createElement("span");
        flare.className = "ft-q-input-char-flare";
        flare.textContent = char;
        flare.style.setProperty("--q-input-flare-x", `${x}px`);
        flare.style.setProperty("--q-input-flare-y", `${y}px`);
        flare.style.setProperty("--q-input-flare-size", style.fontSize || "32px");
        qInputRow.appendChild(flare);
        questionInputFlareTimer = window.setTimeout(() => {
          flare.remove();
          questionInputFlareTimer = 0;
        }, 760);
      }

      function handleQuestionAnswerInputValue() {
        if (!qAnswerInput) {
          return;
        }
        const value = qAnswerInput.value;
        const previous = questionAnswerInputLastValue || "";
        const caret = typeof qAnswerInput.selectionStart === "number" ? qAnswerInput.selectionStart : value.length;
        const addedCount = value.length - previous.length;
        resizeQuestionAnswerInput();
        const item = currentQuestionItem();
        updateQuestionInputLengthRadar(item, Boolean(item && isQuestionTypedItem(item)));
        if (addedCount > 0) {
          const inserted = value.slice(Math.max(0, caret - addedCount), caret) || value.slice(Math.max(0, caret - 1), caret);
          showQuestionInputCharFlare(inserted.slice(-1));
        }
        questionAnswerInputLastValue = value;
      }

      function clearQuestionInputAccent() {
        if (qInputRow) {
          qInputRow.style.removeProperty("--q-input-accent-rgb");
          qInputRow.style.removeProperty("--q-input-accent");
          qInputRow.style.removeProperty("--q-input-accent-soft");
          qInputRow.style.removeProperty("--q-input-accent-glow");
          qInputRow.style.removeProperty("--q-input-text-color");
          qInputRow.style.removeProperty("--q-input-text-rgb");
        }
        if (qAnswerInput) {
          qAnswerInput.classList.remove("is-prysm-text");
        }
      }

      function questionInputTextStyleForNode(node = questionCurrentNode) {
        const root = questionCardData(node, "root") || {};
        const color = safeQuestionHexColor(
          root.input_text_color ?? root.inputTextColor ?? root.itc ?? node?.input_text_color ?? node?.inputTextColor ?? node?.itc,
          QUESTION_INPUT_DEFAULT_TEXT_COLOR,
        );
        const prysm = questionBool(
          root.input_text_prysm ?? root.inputTextPrysm ?? root.input_prysm ?? root.prysm ?? node?.input_text_prysm ?? node?.inputTextPrysm ?? node?.input_prysm ?? node?.prysm,
        );
        return { color, prysm };
      }

      function applyQuestionInputAccent(enabled = true) {
        if (!qInputRow) {
          return;
        }
        if (!enabled) {
          clearQuestionInputAccent();
          return;
        }
        const accent = QUESTION_INPUT_ACCENT;
        qInputRow.style.setProperty("--q-input-accent-rgb", accent.rgb);
        qInputRow.style.setProperty("--q-input-accent", accent.color);
        qInputRow.style.setProperty("--q-input-accent-soft", `rgba(${accent.rgb}, 0.18)`);
        qInputRow.style.setProperty("--q-input-accent-glow", `rgba(${accent.rgb}, 0.38)`);
        const textStyle = questionInputTextStyleForNode();
        const textRgb = questionColorToRgb(textStyle.color, QUESTION_INPUT_DEFAULT_TEXT_COLOR);
        qInputRow.style.setProperty("--q-input-text-color", textStyle.color);
        qInputRow.style.setProperty("--q-input-text-rgb", textRgb.join(", "));
        if (qAnswerInput) {
          qAnswerInput.classList.toggle("is-prysm-text", Boolean(textStyle.prysm));
        }
      }

      function clearQuestionCardRevealSequence() {
        questionCardRevealToken += 1;
        questionCardRevealTimers.forEach((timer) => window.clearTimeout(timer));
        questionCardRevealTimers.clear();
        if (qQuestionCard) {
          qQuestionCard.classList.remove("is-question-reveal-sequence", "is-prompt-revealing", "is-question-exiting");
          qQuestionCard.removeAttribute("data-reveal-skin");
        }
        if (qChoiceList) {
          qChoiceList.querySelectorAll(".ft-q-choice").forEach((choice) => {
            choice.classList.remove("is-choice-revealed");
            choice.style.removeProperty("--q-choice-reveal-delay");
          });
        }
        if (qInputRow) {
          qInputRow.classList.remove("is-choice-revealed");
          qInputRow.style.removeProperty("--q-choice-reveal-delay");
        }
      }

      function nextQuestionCardRevealSkin() {
        let nextSkin = 1 + Math.floor(Math.random() * 10);
        if (nextSkin === questionCardRevealSkin) {
          nextSkin = (nextSkin % 10) + 1;
        }
        questionCardRevealSkin = nextSkin;
        return nextSkin;
      }

      function primeQuestionCardRevealSequence() {
        clearQuestionCardRevealSequence();
        if (!qQuestionCard) {
          return false;
        }
        qQuestionCard.dataset.revealSkin = String(nextQuestionCardRevealSkin());
        qQuestionCard.classList.add("is-question-reveal-sequence");
        const targets = qChoiceList
          ? Array.from(qChoiceList.querySelectorAll(".ft-q-choice"))
          : [];
        targets.forEach((choice, index) => {
          choice.classList.remove("is-choice-revealed");
          choice.style.setProperty("--q-choice-reveal-delay", `${index * QUESTION_CARD_CHOICE_REVEAL_STEP_MS}ms`);
        });
        if (qInputRow && !qInputRow.classList.contains("ft-q-show-answer-hidden")) {
          qInputRow.classList.remove("is-choice-revealed");
          qInputRow.style.setProperty("--q-choice-reveal-delay", "0ms");
        }
        return true;
      }

      function questionCardRevealTargets() {
        const targets = qChoiceList
          ? Array.from(qChoiceList.querySelectorAll(".ft-q-choice"))
          : [];
        if (qInputRow && !qInputRow.classList.contains("ft-q-show-answer-hidden")) {
          targets.push(qInputRow);
        }
        return targets;
      }

      function ensureQuestionWaitNotice() {
        if (questionWaitNoticeNode && questionWaitNoticeNode.isConnected) {
          return questionWaitNoticeNode;
        }
        questionWaitNoticeNode = document.createElement("div");
        questionWaitNoticeNode.className = "ft-q-wait-notice";
        questionWaitNoticeNode.setAttribute("role", "status");
        questionWaitNoticeNode.setAttribute("aria-live", "polite");
        questionWaitNoticeNode.innerHTML = "<div class=\"ft-q-wait-panel\"><div class=\"ft-q-wait-copy\"><strong>Signal hold</strong><span>Đang hoàn tất phần giải thích...</span></div><button class=\"ft-q-wait-skip\" type=\"button\" data-q-wait-skip aria-label=\"Bỏ qua âm thanh giải thích\">Skip</button></div>";
        const skipButton = questionWaitNoticeNode.querySelector("[data-q-wait-skip]");
        if (skipButton) {
          skipButton.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (skipQuestionExplanationPresentation()) {
              hideQuestionWaitNotice();
            }
          });
        }
        document.body.appendChild(questionWaitNoticeNode);
        return questionWaitNoticeNode;
      }

      function showQuestionWaitNotice() {
        const node = ensureQuestionWaitNotice();
        window.requestAnimationFrame(() => node.classList.add("is-live"));
      }

      function hideQuestionWaitNotice() {
        if (questionWaitNoticeNode) {
          questionWaitNoticeNode.classList.remove("is-live");
        }
      }

      const questionCardAudioIsActive = () => Boolean(
        questionCardActiveAudio && questionCardActiveAudio.active
      );

      const waitForQuestionCardAudio = () => (
        questionCardAudioIsActive() && questionCardActiveAudio.promise
          ? questionCardActiveAudio.promise.catch(() => false)
          : Promise.resolve(false)
      );

      const questionExplanationPresentationIsActive = () => Boolean(
        questionCardAudioIsActive() || questionInfoTypingTimer || questionInfoRevealTimer
      );

      function stopQuestionCardActiveAudio() {
        const active = questionCardActiveAudio;
        if (!active || !active.active) {
          return false;
        }
        questionCardActiveAudio = null;
        active.active = false;
        try {
          if (typeof active.stop === "function") {
            active.stop();
          } else if (active.audio) {
            active.audio.pause();
            active.audio.currentTime = 0;
          }
        } catch (error) {
          // Question explanation audio is optional.
        }
        if (typeof active.done === "function") {
          active.done(false);
        }
        return true;
      }

      function stopQuestionInfoTypingWait() {
        if (!questionInfoTypingTimer) {
          return false;
        }
        window.clearTimeout(questionInfoTypingTimer);
        questionInfoTypingTimer = 0;
        return true;
      }

      function stopQuestionInfoRevealWait() {
        if (!questionInfoRevealTimer) {
          return false;
        }
        window.clearTimeout(questionInfoRevealTimer);
        questionInfoRevealTimer = 0;
        if (typeof questionInfoRevealResolve === "function") {
          questionInfoRevealResolve(false);
        }
        questionInfoRevealResolve = null;
        questionInfoRevealPromise = null;
        return true;
      }

      function beginQuestionInfoRevealWait(durationMs = QUESTION_INFO_CARD_REVEAL_MS) {
        stopQuestionInfoRevealWait();
        questionInfoRevealPromise = new Promise((resolve) => {
          questionInfoRevealResolve = resolve;
          questionInfoRevealTimer = window.setTimeout(() => {
            questionInfoRevealTimer = 0;
            questionInfoRevealResolve = null;
            questionInfoRevealPromise = null;
            resolve(true);
          }, Math.max(180, Number(durationMs) || QUESTION_INFO_CARD_REVEAL_MS));
        });
      }

      function skipQuestionExplanationPresentation() {
        const stoppedAudio = stopQuestionCardActiveAudio();
        const stoppedTyping = stopQuestionInfoTypingWait();
        const stoppedReveal = stopQuestionInfoRevealWait();
        return stoppedAudio || stoppedTyping || stoppedReveal;
      }

      const waitForQuestionInfoTyping = () => new Promise((resolve) => {
        if (!questionInfoTypingTimer) {
          resolve(false);
          return;
        }
        const startedAt = performance.now();
        const check = () => {
          if (!questionInfoTypingTimer || performance.now() - startedAt > 12000) {
            resolve(true);
            return;
          }
          window.setTimeout(check, 80);
        };
        check();
      });

      const waitForQuestionInfoReveal = () => (
        questionInfoRevealPromise
          ? questionInfoRevealPromise.catch(() => false)
          : Promise.resolve(false)
      );

      const waitForQuestionExplanationPresentation = async () => {
        if (!questionExplanationPresentationIsActive()) {
          return false;
        }
        await Promise.all([
          waitForQuestionCardAudio(),
          waitForQuestionInfoTyping(),
          waitForQuestionInfoReveal(),
        ]);
        return true;
      };

      const runQuestionCardExitSequence = () => new Promise((resolve) => {
        if (!qQuestionCard || !qQuestionCard.classList.contains("is-live")) {
          resolve(false);
          return;
        }
        clearQuestionCardRevealSequence();
        qQuestionCard.classList.add("is-question-exiting");
        window.setTimeout(() => {
          if (qQuestionCard) {
            qQuestionCard.classList.remove("is-question-exiting");
          }
          resolve(true);
        }, QUESTION_CARD_EXIT_MS);
      });

      function runQuestionCardRevealSequence(options = {}) {
        if (!qQuestionCard || !qQuestionCard.classList.contains("is-live")) {
          return false;
        }
        questionCardRevealToken += 1;
        questionCardRevealTimers.forEach((timer) => window.clearTimeout(timer));
        questionCardRevealTimers.clear();
        const token = questionCardRevealToken;
        const onDone = typeof options.onDone === "function" ? options.onDone : null;
        if (!qQuestionCard.dataset.revealSkin) {
          qQuestionCard.dataset.revealSkin = String(nextQuestionCardRevealSkin());
        }
        qQuestionCard.classList.add("is-question-reveal-sequence", "is-prompt-revealing");
        const targets = questionCardRevealTargets();
        targets.forEach((target, index) => {
          target.classList.remove("is-choice-revealed");
          target.style.setProperty("--q-choice-reveal-delay", `${index * QUESTION_CARD_CHOICE_REVEAL_STEP_MS}ms`);
        });
        const finish = () => {
          if (token !== questionCardRevealToken) {
            return;
          }
          qQuestionCard.classList.remove("is-question-reveal-sequence", "is-prompt-revealing");
          targets.forEach((target) => {
            target.classList.remove("is-choice-revealed");
            target.style.removeProperty("--q-choice-reveal-delay");
          });
          if (onDone) {
            onDone();
          }
        };
        const scanTimer = window.setTimeout(() => {
          questionCardRevealTimers.delete(scanTimer);
          if (token !== questionCardRevealToken) {
            return;
          }
          if (!targets.length) {
            finish();
            return;
          }
          targets.forEach((target, index) => {
            const revealTimer = window.setTimeout(() => {
              questionCardRevealTimers.delete(revealTimer);
              if (token !== questionCardRevealToken) {
                return;
              }
              target.classList.add("is-choice-revealed");
            }, index * QUESTION_CARD_CHOICE_REVEAL_STEP_MS);
            questionCardRevealTimers.add(revealTimer);
          });
          const totalMs = (targets.length - 1) * QUESTION_CARD_CHOICE_REVEAL_STEP_MS + 620;
          const finishTimer = window.setTimeout(() => {
            questionCardRevealTimers.delete(finishTimer);
            finish();
          }, totalMs);
          questionCardRevealTimers.add(finishTimer);
        }, QUESTION_CARD_PROMPT_SCAN_MS);
        questionCardRevealTimers.add(scanTimer);
        return true;
      }

      const stopQuestionReveal = () => {
        questionRevealToken += 1;
        endQuestionHighlightCameraFocus();
        clearQuestionCardOnlyViewTimers();
        clearQuestionCameraPanTimer();
        clearQuestionCardRevealSequence();
        hideQuestionWaitNotice();
        questionNextTransitionActive = false;
        stopQuestionCameraScrollAnimation();
        setQuestionRevealAnimationsActive(false);
        if (stageNode && stageNode.classList.contains("is-question-picture-prompt-startup")) {
          stageNode.classList.remove("is-question-picture-prompt-startup");
          clearQuestionRebootPhaseClasses();
        }
        if (questionRevealTimer) {
          window.clearTimeout(questionRevealTimer);
          questionRevealTimer = 0;
        }
      };

      const stopQuestionRootHighlightAnimation = () => {
        questionRootHighlightToken += 1;
        if (questionRootHighlightTimer) {
          window.clearTimeout(questionRootHighlightTimer);
          questionRootHighlightTimer = 0;
        }
        if (qRootText) {
          qRootText.classList.remove("is-fast-repeat-highlight");
        }
      };

      const setQuestionRootTypingProgress = (value, total = questionTypingFullText.length || 1) => {
        if (!qRootCard) {
          return;
        }
        const safeTotal = Math.max(1, total || 1);
        const ratio = Math.max(0, Math.min(1, value / safeTotal));
        qRootCard.style.setProperty("--q-root-type-progress", `${(ratio * 100).toFixed(2)}%`);
      };

      const stopQuestionAudio = () => {
        if (questionAudio) {
          try {
            questionAudio.pause();
            questionAudio.currentTime = 0;
          } catch (error) {
          }
        }
        questionAudio = null;
        if (qAudioCard) {
          qAudioCard.classList.remove("is-playing");
        }
        if (qPlayButton) {
          qPlayButton.disabled = false;
        }
      };

      const clearQuestionAdvanceTimer = () => {
        if (questionAdvanceTimer) {
          window.clearTimeout(questionAdvanceTimer);
          questionAdvanceTimer = 0;
        }
      };

      const resetQuestionMode = (options = {}) => {
        const keepPending = Boolean(options.keepPending);
        questionIntroBootPending = false;
        endQuestionMobileLoadSmoothing();
        endQuestionRevealAnimationOverride({ discharge: false });
        clearQuestionIntroBootState();
        questionModeActive = false;
        setQuestionInventoryHudVisible(false);
        stopQuestionTyping();
        clearQuestionAdvanceTimer();
        stopQuestionAudio();
        hideQuestionCards();
        clearQuestionCamera();
        if (qRootCard) {
          qRootCard.classList.add("is-hidden");
          qRootCard.classList.remove("is-typed", "is-layout-staging");
        }
        if (qRootText) {
          qRootText.innerHTML = "";
          qRootText.scrollTop = 0;
          hideQuestionRootScrollbarChrome();
        }
        if (qProgress) {
          clearRuntimeProgress(qProgress, "");
        }
        if (qFeedback) {
          qFeedback.textContent = "Root signal is loading.";
          qFeedback.classList.remove("is-ok", "is-error");
        }
        if (qNextButton) {
          qNextButton.disabled = true;
        }
        if (qSkipTypeButton) {
          qSkipTypeButton.disabled = false;
        }
        if (qRootNoticeReplayButton) {
          qRootNoticeReplayButton.disabled = true;
          qRootNoticeReplayButton.title = "No notice for this question";
          qRootNoticeReplayButton.setAttribute("aria-disabled", "true");
        }
        setQuestionAnswerControls(false);
        questionPayload = null;
        questionNodes = [];
        questionQueue = [];
        questionNodePointer = 0;
        questionReviewRunActive = false;
        questionActiveRunId = "";
        questionCurrentNode = null;
        questionCurrentQuestions = [];
        questionCurrentQuestionOrder = [];
        questionQuestionIndex = 0;
        questionWrongAttempts = 0;
        questionCurrentAttemptSignature = "";
        questionCurrentAttemptKey = "";
        questionTypingFullText = "";
        questionTypingRootTopPadding = null;
        questionTypingRootReservedHeight = null;
        if (!keepPending) {
          pendingQuestionPayload = null;
          resetQuestionProgressCache();
        }
        if (stageNode) {
          setQuestionVisualProfileActive(false);
          stageNode.classList.remove("is-question-mode");
          stageNode.classList.remove("is-question-idle-static");
        }
        clearQuestionResponsiveScale();
        if (shellNode) {
          shellNode.style.removeProperty("--q-layout-width");
          shellNode.style.removeProperty("--q-layout-height");
          shellNode.style.removeProperty("--q-root-height");
          shellNode.style.removeProperty("--q-question-top-padding");
          shellNode.style.removeProperty("--q-stage-shell-justify");
          delete shellNode.dataset.qConnectorStyle;
        }
        if (qRootCard) {
          qRootCard.style.removeProperty("--q-root-reserved-height");
        }
      };

      const questionCardData = (node, key) => {
        const cards = node && node.cards && typeof node.cards === "object" ? node.cards : {};
        return cards[key] || null;
      };

      const applyQuestionRootStyle = (node) => {
        const root = questionCardData(node, "root") || {};
        const size = Math.max(18, Math.min(120, Number(root.font_size ?? root.fontSize ?? root.fs ?? 0) || 0));
        const connectorStyle = clean(node && (node.connector_style || node.connectorStyle || node.cs) || root.connector_style || root.connectorStyle || root.cs || "connector-1") || "connector-1";
        if (shellNode) {
          shellNode.dataset.qConnectorStyle = /^connector-(?:[1-9]|10)$/.test(connectorStyle) ? connectorStyle : "connector-1";
        }
        if (!qRootText) {
          return;
        }
        if (size) {
          qRootText.style.setProperty("--q-root-font-size", `${size}px`);
        } else {
          qRootText.style.removeProperty("--q-root-font-size");
        }
      };

      const applyQuestionPictureRegionColor = (node, payload = null) => {
        if (!qPictureCard) {
          return;
        }
        const picture = questionCardData(node, "picture") || {};
        const override = payload && typeof payload === "object"
          ? optionalQuestionPictureRegionColor(payload.region_color ?? payload.regionColor ?? payload.color ?? payload.c)
          : "";
        const color = safeQuestionPictureRegionColor(
          override
          || picture.region_color
          || picture.regionColor
          || picture.region
          || picture.rc
          || (node && (node.picture_region_color || node.pictureRegionColor)),
        );
        const rgb = questionColorToRgb(color).join(", ");
        qPictureCard.style.setProperty("--q-picture-region-color", color);
        qPictureCard.style.setProperty("--q-picture-region-rgb", rgb);
      };

      const safeQuestionHighlightColor = (color) => {
        const value = clean(color);
        return /^#[0-9a-f]{3,8}$/i.test(value) ? value : "#46f0d7";
      };

      const clampQuestionRatio = (value, fallback = 0) => {
        const number = Number(value);
        if (!Number.isFinite(number)) {
          return Math.max(0, Math.min(1, Number(fallback) || 0));
        }
        return Math.max(0, Math.min(1, number));
      };

      const normalizeQuestionPictureRegions = (source) => {
        const values = Array.isArray(source) ? source : [];
        return values.map((entry, index) => {
          const raw = Array.isArray(entry)
            ? { x: entry[0], y: entry[1], w: entry[2], h: entry[3] }
            : (entry && typeof entry === "object" ? entry : {});
          const x = clampQuestionRatio(raw.x ?? raw.left ?? raw.l, 0);
          const y = clampQuestionRatio(raw.y ?? raw.top ?? raw.t, 0);
          let w = clampQuestionRatio(raw.w ?? raw.width ?? raw.rw, 0);
          let h = clampQuestionRatio(raw.h ?? raw.height ?? raw.rh, 0);
          if (x + w > 1) {
            w = Math.max(0.002, 1 - x);
          }
          if (y + h > 1) {
            h = Math.max(0.002, 1 - y);
          }
          const item = {
            id: clean(raw.id ?? raw.i ?? `r${index + 1}`),
            label: clean(raw.label ?? raw.name ?? raw.n ?? String.fromCharCode(65 + Math.min(index, 25))),
            shape: "rect",
            x,
            y,
            w,
            h,
          };
          const color = optionalQuestionPictureRegionColor(raw.color ?? raw.c ?? raw.border_color ?? raw.borderColor);
          if (color) {
            item.color = color;
          }
          return item;
        }).filter((region) => region.w > 0.002 && region.h > 0.002);
      };

      const parseQuestionPictureRegions = (text = "") => {
        const raw = clean(text);
        if (!raw) {
          return [];
        }
        try {
          return normalizeQuestionPictureRegions(JSON.parse(raw));
        } catch (error) {
          return [];
        }
      };

      function questionRootPictureQuestionPayload(entry = {}, fallbackText = "") {
        const data = entry && typeof entry === "object" ? entry : {};
        const raw = data.picture_question && typeof data.picture_question === "object"
          ? data.picture_question
          : (data.pictureQuestion && typeof data.pictureQuestion === "object" ? data.pictureQuestion : (data.pq && typeof data.pq === "object" ? data.pq : {}));
        const rawText = preserveQuestionText(
          raw.text ?? raw.question ?? raw.q ?? data.picture_question_text ?? data.question_bubble ?? data.questionBubble ?? "",
        );
        const regions = normalizeQuestionPictureRegions(raw.regions ?? raw.picture_regions ?? raw.rs ?? data.picture_regions ?? data.regions ?? []);
        const hasPictureQuestionData = Boolean(
          (raw && Object.keys(raw).length)
          || rawText
          || regions.length
        );
        if (!hasPictureQuestionData) {
          return null;
        }
        const text = preserveQuestionText(fallbackText) || rawText;
        if (!text) {
          return null;
        }
        const anchorRaw = clean(raw.anchor ?? raw.a ?? data.anchor).toLowerCase();
        const anchor = /^(?:highlight|root_highlight|text|root_text)$/i.test(anchorRaw)
          ? "highlight"
          : (/^(?:picture|ship)$/i.test(anchorRaw)
            ? "picture"
            : (/^(?:picture_regions|picture-region|regions|region)$/i.test(anchorRaw) || regions.length ? "picture_regions" : "highlight"));
        const placement = /^(?:above|below)$/i.test(clean(raw.placement ?? raw.p ?? data.placement))
          ? clean(raw.placement ?? raw.p ?? data.placement).toLowerCase()
          : "auto";
        const payload = { text, anchor, placement };
        const regionColor = optionalQuestionPictureRegionColor(
          raw.region_color
          ?? raw.regionColor
          ?? raw.color
          ?? raw.c
          ?? data.picture_region_color
          ?? data.pictureRegionColor
        );
        if (regionColor) {
          payload.region_color = regionColor;
        }
        if (regions.length) {
          payload.regions = regions;
        }
        return payload;
      }

      const questionRootHighlightRanges = (text, highlights = [], pictureQuestionText = "") => {
        const source = preserveQuestionText(text);
        return (Array.isArray(highlights) ? highlights : []).map((entry, sourceIndex) => {
          const data = entry && typeof entry === "object" ? entry : {};
          let start = Math.max(0, Math.floor(Number(data.start ?? data.s ?? 0) || 0));
          let end = Math.max(0, Math.floor(Number(data.end ?? data.e ?? 0) || 0));
          const needle = preserveQuestionText(data.text ?? data.t ?? "");
          if (!(end > start) && needle) {
            const found = source.indexOf(needle);
            if (found >= 0) {
              start = found;
              end = found + needle.length;
            }
          } else if (needle && source.slice(start, end) !== needle) {
            const found = source.indexOf(needle);
            if (found >= 0) {
              start = found;
              end = found + needle.length;
            }
          }
          start = Math.max(0, Math.min(source.length, start));
          end = Math.max(start, Math.min(source.length, end));
          return {
            start,
            end,
            text: needle,
            color: safeQuestionHighlightColor(data.color ?? data.c),
            style: clean(data.style ?? data.st ?? "style-1") || "style-1",
            render: /^(?:block|box|old|background)$/i.test(clean(data.render ?? data.mode ?? data.m ?? "text")) ? "block" : "text",
            info: preserveQuestionText(data.info ?? data.note ?? data.card ?? data.i ?? ""),
            sourceIndex,
            pictureQuestion: questionRootPictureQuestionPayload(data, pictureQuestionText),
          };
        }).filter((entry) => entry.end > entry.start);
      };

      const questionRootActiveTrailIndex = (text = "") => {
        const source = preserveQuestionText(text);
        for (let index = source.length - 1; index >= 0; index -= 1) {
          if (!/\s/.test(source.charAt(index))) {
            return index;
          }
        }
        return source ? source.length - 1 : -1;
      };

      const questionRootTypingColors = ["#46f0d7", "#ffd65f", "#d86cff"];

      const questionRootTypingTracks = (text = "", maxComets = 3) => {
        const source = preserveQuestionText(text);
        const total = source.length;
        if (!total) {
          return [];
        }
        const trackCount = Math.max(1, Math.min(3, maxComets, total));
        const tracks = [];
        for (let trackIndex = 0; trackIndex < trackCount; trackIndex += 1) {
          let start = Math.floor((total * trackIndex) / trackCount);
          let end = trackIndex === trackCount - 1 ? total : Math.floor((total * (trackIndex + 1)) / trackCount);
          while (start < end && /\s/.test(source.charAt(start))) {
            start += 1;
          }
          while (end > start && /\s/.test(source.charAt(end - 1))) {
            end -= 1;
          }
          if (end > start) {
            tracks.push({
              start,
              end,
              color: questionRootTypingColors[trackIndex % questionRootTypingColors.length],
            });
          }
        }
        return tracks.length ? tracks : [{
          start: 0,
          end: total,
          color: questionRootTypingColors[0],
        }];
      };

      const questionRootTypingDuration = (text = "") => {
        const sourceLength = preserveQuestionText(text).length;
        return Math.max(1400, Math.min(4600, Math.round(sourceLength * 7.5)));
      };

      const questionRootTypingVisibleIndex = (source = "", start = 0, end = 0, cursor = 0) => {
        const safeStart = Math.max(0, Math.min(source.length, start));
        const safeEnd = Math.max(safeStart, Math.min(source.length, end));
        if (safeEnd <= safeStart) {
          return -1;
        }
        const safeCursor = Math.max(safeStart, Math.min(safeEnd - 1, cursor));
        for (let index = safeCursor; index >= safeStart; index -= 1) {
          if (!/\s/.test(source.charAt(index))) {
            return index;
          }
        }
        for (let index = safeCursor + 1; index < safeEnd; index += 1) {
          if (!/\s/.test(source.charAt(index))) {
            return index;
          }
        }
        return safeCursor;
      };

      const questionRootTypingRevealState = (text = "", tracks = [], ratio = 0) => {
        const source = preserveQuestionText(text);
        const progress = Math.max(0, Math.min(1, Number(ratio) || 0));
        const revealRanges = [];
        const activeSteps = [];
        tracks.forEach((track) => {
          if (!track || track.end <= track.start) {
            return;
          }
          const span = track.end - track.start;
          const revealEnd = progress >= 1
            ? track.end
            : Math.max(track.start, Math.min(track.end, track.start + Math.floor(span * progress)));
          if (revealEnd > track.start) {
            revealRanges.push({ start: track.start, end: revealEnd });
          }
          if (progress > 0 && progress < 1) {
            const activeIndex = questionRootTypingVisibleIndex(source, track.start, track.end, Math.max(track.start, revealEnd - 1));
            if (activeIndex >= 0) {
              activeSteps.push({
                index: activeIndex,
                color: safeQuestionHighlightColor(track.color || questionRootTypingColors[0]),
              });
            }
          }
        });
        return { revealRanges, activeSteps };
      };

      const renderQuestionRootTrailSegment = (text, globalStart, activeIndex = -1, activeColor = "#46f0d7") => {
        if (!text) {
          return "";
        }
        const activeEntries = (Array.isArray(activeIndex) ? activeIndex : (Number.isInteger(activeIndex) ? [{ index: activeIndex, color: activeColor }] : []))
          .map((entry) => (typeof entry === "number" ? { index: entry, color: activeColor } : entry))
          .filter((entry) => entry && Number.isInteger(entry.index) && entry.index >= globalStart && entry.index < globalStart + text.length)
          .sort((left, right) => left.index - right.index);
        if (!activeEntries.length) {
          return escapeHtml(text);
        }
        let cursor = 0;
        let html = "";
        activeEntries.forEach((entry) => {
          const localIndex = entry.index - globalStart;
          if (localIndex < cursor) {
            return;
          }
          if (localIndex > cursor) {
            html += escapeHtml(text.slice(cursor, localIndex));
          }
          const cometColor = safeQuestionHighlightColor(entry.color || activeColor);
          html += `<span class="ft-q-root-comet-char" style="--q-comet-color:${cometColor}"><span class="ft-q-root-comet-particles" aria-hidden="true"></span><span class="ft-q-root-comet-glyph">${escapeHtml(text.charAt(localIndex))}</span></span>`;
          cursor = localIndex + 1;
        });
        if (cursor < text.length) {
          html += escapeHtml(text.slice(cursor));
        }
        return html;
      };

      const questionRootTypingSegmentVisible = (ranges = [], start = 0, end = 0) => ranges.some((range) => (
        range && start >= range.start && end <= range.end
      ));

      const renderQuestionRootTypingRevealSegment = (text, globalStart, revealRanges = [], activeSteps = []) => {
        const source = String(text || "");
        if (!source) {
          return "";
        }
        const lineStart = globalStart;
        const lineEnd = globalStart + source.length;
        const clippedRanges = (Array.isArray(revealRanges) ? revealRanges : [])
          .map((range) => ({
            start: Math.max(lineStart, Math.min(lineEnd, Math.floor(Number(range && range.start) || 0))),
            end: Math.max(lineStart, Math.min(lineEnd, Math.floor(Number(range && range.end) || 0))),
          }))
          .filter((range) => range.end > range.start);
        const activeEntries = (Array.isArray(activeSteps) ? activeSteps : [])
          .filter((entry) => entry && Number.isInteger(entry.index) && entry.index >= lineStart && entry.index < lineEnd)
          .sort((left, right) => left.index - right.index);
        const points = new Set([0, source.length]);
        clippedRanges.forEach((range) => {
          points.add(range.start - lineStart);
          points.add(range.end - lineStart);
        });
        activeEntries.forEach((entry) => {
          const localIndex = entry.index - lineStart;
          points.add(localIndex);
          points.add(localIndex + 1);
        });
        const orderedPoints = Array.from(points)
          .filter((point) => Number.isFinite(point) && point >= 0 && point <= source.length)
          .sort((left, right) => left - right);
        const activeByIndex = new Map(activeEntries.map((entry) => [entry.index, entry]));
        let html = "";
        for (let pointIndex = 0; pointIndex < orderedPoints.length - 1; pointIndex += 1) {
          const start = orderedPoints[pointIndex];
          const end = orderedPoints[pointIndex + 1];
          if (end <= start) {
            continue;
          }
          const globalIndex = lineStart + start;
          const activeEntry = activeByIndex.get(globalIndex);
          if (activeEntry && end === start + 1) {
            const cometColor = safeQuestionHighlightColor(activeEntry.color || questionRootTypingColors[0]);
            html += `<span class="ft-q-root-comet-char" style="--q-comet-color:${cometColor}"><span class="ft-q-root-comet-particles" aria-hidden="true"></span><span class="ft-q-root-comet-glyph">${escapeHtml(source.charAt(start))}</span></span>`;
            continue;
          }
          const chunk = source.slice(start, end);
          if (questionRootTypingSegmentVisible(clippedRanges, globalIndex, lineStart + end)) {
            html += escapeHtml(chunk);
          } else {
            html += `<span class="ft-q-root-hidden-char">${escapeHtml(chunk)}</span>`;
          }
        }
        return html;
      };

      const renderQuestionRootSelectSegment = (text, globalStart, sourceIndex = 0) => {
        const source = String(text || "");
        if (!source) {
          return "";
        }
        const wordPattern = /[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu;
        let cursor = 0;
        let html = "";
        let match;
        while ((match = wordPattern.exec(source)) !== null) {
          const word = match[0];
          const localStart = match.index;
          const localEnd = localStart + word.length;
          if (localStart > cursor) {
            html += escapeHtml(source.slice(cursor, localStart));
          }
          const tokenIndex = `${sourceIndex}-${globalStart + localStart}`;
          html += `<button class="ft-q-select-root-token" type="button" data-q-select-kind="root" data-q-select-token="${escapeHtml(word)}" data-q-select-index="${escapeHtml(tokenIndex)}">${escapeHtml(word)}</button>`;
          cursor = localEnd;
        }
        if (cursor < source.length) {
          html += escapeHtml(source.slice(cursor));
        }
        return html;
      };

      const renderQuestionRootLineSegments = (line, lineStart, ranges, options = {}) => {
        const activeSteps = Array.isArray(options.activeSteps) ? options.activeSteps : null;
        const activeIndex = activeSteps || (Number.isInteger(options.activeIndex) ? options.activeIndex : -1);
        const activeColor = safeQuestionHighlightColor(options.activeColor);
        const overlaps = ranges
          .map((range, index) => ({
            start: Math.max(0, range.start - lineStart),
            end: Math.min(line.length, range.end - lineStart),
            color: range.color,
            style: /^style-(?:[1-9]|10)$/.test(range.style) ? range.style : "style-1",
            render: range.render === "block" ? "block" : "text",
            info: range.info,
            selectTarget: Boolean(range.selectTarget),
            selectStealth: Boolean(range.selectStealth),
            sourceIndex: Number.isInteger(range.sourceIndex) ? range.sourceIndex : index,
            pictureQuestion: range.pictureQuestion || null,
            index,
          }))
          .filter((range) => range.end > range.start)
          .sort((left, right) => left.start - right.start || (right.selectTarget ? 1 : 0) - (left.selectTarget ? 1 : 0) || left.end - right.end);
        if (!overlaps.length) {
          return renderQuestionRootTrailSegment(line, lineStart, activeIndex, activeColor);
        }
        let html = "";
        let cursor = 0;
        overlaps.forEach((range) => {
          const start = Math.max(cursor, range.start);
          const end = Math.max(start, range.end);
          if (start > cursor) {
            html += renderQuestionRootTrailSegment(line.slice(cursor, start), lineStart + cursor, activeIndex, activeColor);
          }
          if (end > start) {
            const pictureQuestion = range.pictureQuestion || {};
            const pictureRegions = pictureQuestion.regions && pictureQuestion.regions.length ? JSON.stringify(pictureQuestion.regions) : "";
            const content = range.selectTarget
              ? renderQuestionRootSelectSegment(line.slice(start, end), lineStart + start, range.sourceIndex)
              : renderQuestionRootTrailSegment(line.slice(start, end), lineStart + start, activeIndex, activeColor);
            html += `<span class="ft-q-root-highlight hl-${range.style} is-${range.render} ${range.selectTarget ? "is-select-target" : ""} ${range.selectStealth ? "is-select-stealth" : ""}" data-qh-index="${range.sourceIndex}" data-qh-info="${escapeHtml(range.info || "")}" data-qh-picture-question="${escapeHtml(pictureQuestion.text || "")}" data-qh-anchor="${escapeHtml(pictureQuestion.anchor || "")}" data-qh-placement="${escapeHtml(pictureQuestion.placement || "")}" data-qh-regions="${escapeHtml(pictureRegions)}" style="--q-highlight-color:${range.color};--q-highlight-delay:${Math.min(420, range.index * 90)}ms">${content}</span>`;
            cursor = end;
          }
        });
        if (cursor < line.length) {
          html += renderQuestionRootTrailSegment(line.slice(cursor), lineStart + cursor, activeIndex, activeColor);
        }
        return html;
      };

      const renderQuestionRootMarkup = (text, highlights = [], options = {}) => {
        const source = preserveQuestionText(text);
        if (!source) {
          if (qRootText) {
            qRootText.classList.remove("has-block-highlight");
          }
          return "";
        }
        const activeSteps = Array.isArray(options.activeSteps) ? options.activeSteps : null;
        const activeIndex = activeSteps || (Number.isInteger(options.activeIndex) ? options.activeIndex : -1);
        const activeColor = safeQuestionHighlightColor(options.activeColor);
        const ranges = Array.isArray(options.ranges) ? options.ranges : questionRootHighlightRanges(source, highlights);
        if (qRootText) {
          qRootText.classList.toggle("has-block-highlight", ranges.some((range) => range.render === "block"));
        }
        let offset = 0;
        return source.split("\n").map((line) => {
          const bulletMatch = line.match(/^([ \t]*)([-+=*])(\s+|$)(.*)$/);
          const lineStart = offset;
          const lineEnd = offset + line.length;
          const lineHasHighlight = ranges.some((range) => range.start < lineEnd && range.end > lineStart);
          const lineHtml = renderQuestionRootLineSegments(line, offset, ranges, { activeIndex, activeColor, activeSteps });
          const lineHasTrail = Array.isArray(activeSteps)
            ? activeSteps.some((entry) => entry && entry.index >= lineStart && entry.index < lineEnd)
            : activeIndex >= lineStart && activeIndex < lineEnd;
          offset += line.length + 1;
          if (bulletMatch) {
            if (!lineHasHighlight && !lineHasTrail) {
              return `<span class="ft-q-root-line is-bullet">${escapeHtml(bulletMatch[1])}<span class="ft-q-root-bullet">${escapeHtml(bulletMatch[2])}</span>${escapeHtml(bulletMatch[4])}</span>`;
            }
            return `<span class="ft-q-root-line is-bullet">${lineHtml}</span>`;
          }
          return `<span class="ft-q-root-line">${lineHtml}</span>`;
        }).join("");
      };

      function ensureQuestionTypingComet() {
        if (!qRootCard) {
          return null;
        }
        if (!questionTypingCometNode) {
          questionTypingCometNode = document.createElement("span");
          questionTypingCometNode.className = "ft-q-typing-comet";
          questionTypingCometNode.setAttribute("aria-hidden", "true");
          questionTypingCometNode.innerHTML = '<span class="ft-q-root-comet-char" style="--q-comet-color:#46f0d7"><span class="ft-q-root-comet-particles" aria-hidden="true"></span><span class="ft-q-root-comet-glyph">&#10022;</span></span>';
        }
        if (questionTypingCometNode.parentNode !== qRootCard) {
          qRootCard.appendChild(questionTypingCometNode);
        }
        return questionTypingCometNode;
      }

      function hideQuestionTypingComet() {
        if (questionTypingCometNode) {
          questionTypingCometNode.classList.remove("is-live");
        }
        if (qRootText) {
          qRootText.querySelectorAll(".ft-q-typing-comet-anchor").forEach((node) => node.remove());
        }
      }

      function positionQuestionTypingComet(anchor) {
        const comet = ensureQuestionTypingComet();
        if (!comet || !qRootCard || !qRootText || !anchor || !anchor.isConnected) {
          return;
        }
        const anchorRect = anchor.getBoundingClientRect();
        const cardRect = qRootCard.getBoundingClientRect();
        const textStyle = window.getComputedStyle(qRootText);
        const fontSize = Math.max(12, Number.parseFloat(textStyle.fontSize) || 32);
        const lineHeight = Math.max(fontSize, Number.parseFloat(textStyle.lineHeight) || fontSize * 1.04);
        const x = questionUnscaleLayoutValue(anchorRect.left - cardRect.left);
        const anchorHeight = anchorRect.height ? questionUnscaleLayoutValue(anchorRect.height) : lineHeight;
        const y = questionUnscaleLayoutValue(anchorRect.top - cardRect.top) + anchorHeight * 0.36;
        comet.style.fontSize = `${fontSize}px`;
        comet.style.lineHeight = `${lineHeight}px`;
        comet.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        comet.classList.add("is-live");
      }

      function renderQuestionRootTypingMarkup(fullText = "", revealRanges = [], activeSteps = []) {
        if (!qRootText) {
          return;
        }
        const source = preserveQuestionText(fullText);
        if (qRootText) {
          qRootText.classList.remove("has-block-highlight");
        }
        if (!source) {
          qRootText.innerHTML = "";
          hideQuestionTypingComet();
          return;
        }
        let offset = 0;
        qRootText.innerHTML = source.split("\n").map((line) => {
          const lineHtml = renderQuestionRootTypingRevealSegment(line, offset, revealRanges, activeSteps);
          offset += line.length + 1;
          return `<span class="ft-q-root-line">${lineHtml}</span>`;
        }).join("");
        hideQuestionTypingComet();
      }

      const questionRootHighlightSteps = (ranges = []) => {
        const steps = [];
        ranges
          .slice()
          .sort((left, right) => left.start - right.start || left.end - right.end)
          .forEach((range) => {
            for (let index = range.start; index < range.end; index += 1) {
              steps.push({ index, color: range.color });
            }
          });
        return steps;
      };

      const questionRootHighlightCometTracks = (ranges = [], rootText = "") => {
        const source = preserveQuestionText(rootText);
        const tracks = [];
        const wordPattern = /[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu;
        const desiredCometCountForWordCount = (wordCount = 0) => {
          const count = Math.max(0, Math.floor(Number(wordCount) || 0));
          if (count <= 9) return 1;
          if (count <= 20) return 2;
          return Math.max(1, Math.min(3, Math.ceil(count / 10)));
        };
        ranges
          .slice()
          .sort((left, right) => left.start - right.start || left.end - right.end)
          .forEach((range) => {
            if (!range || range.end <= range.start) {
              return;
            }
            const start = Math.max(0, Math.min(source.length, Math.floor(Number(range.start) || 0)));
            const end = Math.max(start, Math.min(source.length, Math.floor(Number(range.end) || start)));
            const segment = source.slice(start, end);
            wordPattern.lastIndex = 0;
            const words = [];
            let match;
            while ((match = wordPattern.exec(segment)) !== null) {
              words.push({
                start: start + match.index,
                end: start + match.index + match[0].length,
              });
            }
            if (!words.length) {
              const charLength = Math.max(1, end - start);
              const chunkCount = Math.max(1, Math.min(3, Math.ceil(charLength / 72)));
              const approxChunk = Math.max(1, Math.ceil(charLength / chunkCount));
              for (let cursor = start; cursor < end; cursor += approxChunk) {
                tracks.push({
                  start: cursor,
                  end: Math.min(end, cursor + approxChunk),
                  color: range.color,
                  sourceRange: range,
                  wordCount: 0,
                });
              }
              return;
            }
            const cometCount = desiredCometCountForWordCount(words.length);
            const wordsPerComet = Math.max(1, Math.ceil(words.length / cometCount));
            for (let index = 0; index < words.length; index += wordsPerComet) {
              const chunk = words.slice(index, index + wordsPerComet);
              const first = chunk[0];
              const last = chunk[chunk.length - 1];
              tracks.push({
                start: first.start,
                end: last.end,
                color: range.color,
                sourceRange: range,
                wordCount: chunk.length,
              });
            }
          });
        return tracks.filter((track) => track.end > track.start);
      };

      const QUESTION_ROOT_HIGHLIGHT_MAX_COMETS = 3;
      const QUESTION_ROOT_HIGHLIGHT_FRAME_MS = 32;
      const QUESTION_ROOT_HIGHLIGHT_PAINT_BUCKETS = 72;

      const questionRootHighlightTrackWordCount = (tracks = []) => (Array.isArray(tracks) ? tracks : [])
        .reduce((total, track) => total + Math.max(0, Math.floor(Number(track && track.wordCount) || 0)), 0);

      const questionRootHighlightScanDurationMs = (tracks = [], options = {}) => {
        const source = (Array.isArray(tracks) ? tracks : []).filter((track) => track && track.end > track.start);
        const wordCount = questionRootHighlightTrackWordCount(source);
        const batchCount = Math.max(1, questionRootHighlightBatchesFor(source).length);
        const compactWords = wordCount > 0 && wordCount <= 5;
        const shortWords = wordCount > 0 && wordCount <= 9;
        const baseMs = compactWords ? 520 : (shortWords ? 680 : 760);
        const perWordMs = compactWords ? 34 : (shortWords ? 38 : 42);
        const perBatchMs = compactWords ? 70 : (shortWords ? 110 : 190);
        const minMs = compactWords ? 420 : (shortWords ? 560 : 760);
        const maxMs = options && options.focus ? 2200 : 2100;
        const estimate = baseMs + Math.max(0, wordCount || source.length * 5) * perWordMs + Math.max(0, batchCount - 1) * perBatchMs;
        return Math.max(minMs, Math.min(maxMs, Math.round(estimate)));
      };

      const questionRootHighlightBatchesFor = (tracks = []) => {
        const source = (Array.isArray(tracks) ? tracks : []).filter((track) => track && track.end > track.start);
        const batches = [];
        for (let index = 0; index < source.length; index += QUESTION_ROOT_HIGHLIGHT_MAX_COMETS) {
          batches.push(source.slice(index, index + QUESTION_ROOT_HIGHLIGHT_MAX_COMETS));
        }
        return batches;
      };

      const questionRootHighlightBatchStateAt = (tracks = [], ratio = 0) => {
        const source = (Array.isArray(tracks) ? tracks : []).filter((track) => track && track.end > track.start);
        if (!source.length) {
          return { activeSteps: [], visibleRanges: [], activeStep: null, batchCount: 0 };
        }
        const progress = Math.max(0, Math.min(1, Number(ratio) || 0));
        const batchCount = Math.max(1, Math.ceil(source.length / QUESTION_ROOT_HIGHLIGHT_MAX_COMETS));
        const scaled = progress >= 1 ? batchCount : progress * batchCount;
        const batchIndex = Math.min(batchCount - 1, Math.max(0, Math.floor(scaled)));
        const batchRatio = progress >= 1 ? 1 : Math.max(0, Math.min(1, scaled - batchIndex));
        const batchStart = batchIndex * QUESTION_ROOT_HIGHLIGHT_MAX_COMETS;
        const completedTracks = source.slice(0, batchStart);
        const activeTracks = source.slice(batchStart, batchStart + QUESTION_ROOT_HIGHLIGHT_MAX_COMETS);
        const visibleRanges = completedTracks.map((track) => ({
          start: track.start,
          end: track.end,
          color: track.color,
          sourceRange: track.sourceRange,
        }));
        const activeSteps = activeTracks.map((track) => {
          const span = Math.max(1, track.end - track.start);
          const activeIndex = Math.max(track.start, Math.min(track.end - 1, track.start + Math.floor(batchRatio * span)));
          if (batchRatio > 0 || progress >= 1) {
            visibleRanges.push({
              start: track.start,
              end: Math.max(track.start + 1, Math.min(track.end, activeIndex + 1)),
              color: track.color,
              sourceRange: track.sourceRange,
            });
          }
          return {
            index: activeIndex,
            color: track.color,
            start: track.start,
            end: track.end,
          };
        });
        return {
          activeSteps,
          visibleRanges,
          activeStep: activeSteps[0] || null,
          batchCount,
        };
      };

      const questionRootHighlightTrackStepsAt = (tracks = [], ratio = 0) => {
        const progress = Math.max(0, Math.min(1, Number(ratio) || 0));
        return (Array.isArray(tracks) ? tracks : [])
          .map((track) => {
            if (!track || track.end <= track.start) {
              return null;
            }
            const span = Math.max(1, track.end - track.start);
            return {
              index: Math.max(track.start, Math.min(track.end - 1, track.start + Math.floor(progress * span))),
              color: track.color,
            };
          })
          .filter(Boolean);
      };

      const visibleQuestionRootHighlightRanges = (ranges = [], visibleCount = 0) => {
        let remaining = Math.max(0, Math.floor(Number(visibleCount) || 0));
        return ranges
          .slice()
          .sort((left, right) => left.start - right.start || left.end - right.end)
          .map((range) => {
            if (remaining <= 0) {
              return null;
            }
            const length = Math.max(0, range.end - range.start);
            const take = Math.min(length, remaining);
            remaining -= length;
            return take > 0 ? { ...range, end: range.start + take } : null;
          })
          .filter(Boolean);
      };

      const visibleQuestionRootHighlightRangesAt = (ranges = [], ratio = 0) => {
        const progress = Math.max(0, Math.min(1, Number(ratio) || 0));
        return (Array.isArray(ranges) ? ranges : [])
          .slice()
          .sort((left, right) => left.start - right.start || left.end - right.end)
          .map((range) => {
            if (!range || range.end <= range.start) {
              return null;
            }
            const length = Math.max(1, range.end - range.start);
            const take = Math.max(1, Math.min(length, Math.ceil(length * progress)));
            return { ...range, end: range.start + take };
          })
          .filter(Boolean);
      };

      const ensureQuestionRootInfoLayer = () => {
        if (!shellNode) {
          return null;
        }
        if (!questionRootInfoCard) {
          questionRootInfoCard = document.createElement("aside");
          questionRootInfoCard.className = "ft-q-root-info-card";
          questionRootInfoCard.innerHTML = '<p class="ft-q-root-info-title">Root Signal</p><p class="ft-q-root-info-meta" aria-hidden="true"><span>Region Link</span><span>Anchor Trace</span><span>Signal Stable</span></p><p class="ft-q-root-info-body"></p><div class="ft-q-root-info-actions"><button class="ft-q-root-info-action is-secondary ft-q-show-answer-hidden" type="button" data-root-info-audio>Listen</button><button class="ft-q-root-info-action" type="button" data-root-info-next disabled>Next</button></div><p class="ft-q-root-info-feedback" aria-live="polite"></p>';
          const rootInfoAudio = questionRootInfoCard.querySelector("[data-root-info-audio]");
          const rootInfoNext = questionRootInfoCard.querySelector("[data-root-info-next]");
          if (rootInfoAudio) {
            rootInfoAudio.addEventListener("click", () => {
              void playQuestionPromptAudio();
            });
          }
          if (rootInfoNext) {
            rootInfoNext.addEventListener("click", () => {
              if (!rootInfoNext.disabled) {
                advanceQuestionItem();
              }
            });
          }
          shellNode.appendChild(questionRootInfoCard);
        }
        if (!questionRootInfoConnector) {
          questionRootInfoConnector = document.createElement("div");
          questionRootInfoConnector.className = "ft-q-root-info-connector";
          questionRootInfoConnector.innerHTML = '<span class="ft-q-root-info-connector-segment is-diagonal"></span><span class="ft-q-root-info-connector-segment is-horizontal"></span>';
          shellNode.appendChild(questionRootInfoConnector);
        }
        return questionRootInfoCard;
      };

      const ensureQuestionRootInfoConnectorAt = (index = 0) => {
        if (!shellNode) {
          return null;
        }
        if (index <= 0) {
          return questionRootInfoConnector;
        }
        const extraIndex = index - 1;
        while (questionRootInfoExtraConnectors.length <= extraIndex) {
          const connector = document.createElement("div");
          connector.className = "ft-q-root-info-connector";
          connector.innerHTML = '<span class="ft-q-root-info-connector-segment is-diagonal"></span><span class="ft-q-root-info-connector-segment is-horizontal"></span>';
          shellNode.appendChild(connector);
          questionRootInfoExtraConnectors.push(connector);
        }
        return questionRootInfoExtraConnectors[extraIndex];
      };

      const ensureQuestionRootInfoConnectorBaseSegments = (connector) => {
        if (!connector) {
          return;
        }
        if (
          connector.dataset.regionSegments === "1"
          || !connector.querySelector(".ft-q-root-info-connector-segment.is-diagonal")
          || !connector.querySelector(".ft-q-root-info-connector-segment.is-horizontal")
        ) {
          connector.dataset.regionSegments = "0";
          connector.innerHTML = '<span class="ft-q-root-info-connector-segment is-diagonal"></span><span class="ft-q-root-info-connector-segment is-horizontal"></span>';
        }
      };

      const ensureQuestionRegionConnectorSegments = (connector, count = 0) => {
        if (!connector) {
          return [];
        }
        const safeCount = Math.max(1, Math.min(18, Math.floor(Number(count) || 1)));
        if (connector.dataset.regionSegments !== "1" || connector.dataset.regionSegmentCount !== String(safeCount)) {
          connector.dataset.regionSegments = "1";
          connector.dataset.regionSegmentCount = String(safeCount);
          connector.innerHTML = Array.from({ length: safeCount }, (_item, index) => (
            `<span class="ft-q-root-info-connector-segment is-region-path is-region-path-${index}"></span>`
          )).join("");
        }
        return Array.from(connector.querySelectorAll(".ft-q-root-info-connector-segment.is-region-path"));
      };

      const allQuestionRootInfoConnectors = () => [questionRootInfoConnector, ...questionRootInfoExtraConnectors].filter(Boolean);

      const hideQuestionRootInfoConnectors = () => {
        allQuestionRootInfoConnectors().forEach((connector) => {
          connector.classList.remove("is-live");
          connector.classList.remove("is-focused");
          connector.classList.remove("is-elbow");
          connector.classList.remove("is-region-rail");
          connector.classList.remove("is-highlight-rail");
        });
      };

      const ensureQuestionRootHoverInfoLayer = () => {
        if (!shellNode) {
          return null;
        }
        if (!questionRootHoverInfoCard) {
          questionRootHoverInfoCard = document.createElement("aside");
          questionRootHoverInfoCard.className = "ft-q-root-info-card is-root-hover-signal";
          questionRootHoverInfoCard.innerHTML = '<p class="ft-q-root-info-title">Root Signal</p><p class="ft-q-root-info-meta" aria-hidden="true"><span>Anchor Trace</span><span>Signal Stable</span><span>Root Note</span></p><p class="ft-q-root-info-body"></p>';
          shellNode.appendChild(questionRootHoverInfoCard);
        }
        if (!questionRootHoverInfoConnector) {
          questionRootHoverInfoConnector = document.createElement("div");
          questionRootHoverInfoConnector.className = "ft-q-root-info-connector is-root-hover-signal";
          shellNode.appendChild(questionRootHoverInfoConnector);
        }
        return questionRootHoverInfoCard;
      };

      const hideQuestionRootHoverInfo = () => {
        if (questionRootHoverInfoTypingTimer) {
          window.clearTimeout(questionRootHoverInfoTypingTimer);
          questionRootHoverInfoTypingTimer = 0;
        }
        if (questionRootHoverInfoCard) {
          questionRootHoverInfoCard.classList.remove("is-live");
          questionRootHoverInfoCard.classList.remove("is-preparing");
          questionRootHoverInfoCard.classList.remove("is-question");
          questionRootHoverInfoCard.classList.remove("is-picture-region-question");
          questionRootHoverInfoCard.classList.remove("is-cursor-follow-signal");
        }
        if (questionRootHoverInfoConnector) {
          questionRootHoverInfoConnector.classList.remove("is-live");
          questionRootHoverInfoConnector.classList.remove("is-focused");
          questionRootHoverInfoConnector.classList.remove("is-elbow");
          questionRootHoverInfoConnector.classList.remove("is-region-rail");
          questionRootHoverInfoConnector.classList.remove("is-cursor-follow-signal");
        }
      };

      const questionRootHoverSignalIsSelectMobileHidden = () => (
        isQuestionSelectItem(currentQuestionItem())
      );

      const questionRootHoverSignalShouldFollowPointer = () => (
        false
      );

      const questionIsSelectAnswerSurface = (node) => Boolean(
        node
        && typeof node.closest === "function"
        && node.closest(".ft-q-select-root-token,.ft-q-select-root-overlay,.ft-q-root-highlight.is-select-target,.ft-q-select-root-merge,.ft-q-picture-region.is-select-answer")
      );

      const questionRootHoverInfoTextForSource = (sourceNode) => {
        if (!sourceNode) {
          return "";
        }
        const ownInfo = sourceNode.getAttribute && sourceNode.getAttribute("data-qh-info");
        if (ownInfo) {
          return ownInfo;
        }
        const datasetInfo = sourceNode.dataset && sourceNode.dataset.qhInfo;
        if (datasetInfo) {
          return datasetInfo;
        }
        const parentHighlight = sourceNode.closest && sourceNode.closest(".ft-q-root-highlight");
        const parentInfo = parentHighlight && parentHighlight.getAttribute && parentHighlight.getAttribute("data-qh-info");
        if (parentInfo) {
          return parentInfo;
        }
        if (questionIsSelectAnswerSurface(sourceNode)) {
          return "Root selection signal.";
        }
        return sourceNode.textContent || "";
      };

      const questionVisibleBoundsInShell = () => {
        if (!shellNode || !shellNode.getBoundingClientRect) {
          return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
        }
        const shellRect = shellNode.getBoundingClientRect();
        const viewportRect = stageNode && stageNode.getBoundingClientRect
          ? stageNode.getBoundingClientRect()
          : shellRect;
        const left = questionUnscaleLayoutValue(viewportRect.left - shellRect.left);
        const top = questionUnscaleLayoutValue(viewportRect.top - shellRect.top);
        const width = questionUnscaleLayoutValue(viewportRect.width);
        const height = questionUnscaleLayoutValue(viewportRect.height);
        return {
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
        };
      };

      const questionRectInShellFromClientRect = (rect, pad = 0) => {
        if (!rect || !shellNode || !shellNode.getBoundingClientRect) {
          return null;
        }
        const shellRect = shellNode.getBoundingClientRect();
        const left = questionUnscaleLayoutValue(rect.left - shellRect.left) - pad;
        const top = questionUnscaleLayoutValue(rect.top - shellRect.top) - pad;
        const width = questionUnscaleLayoutValue(rect.width) + pad * 2;
        const height = questionUnscaleLayoutValue(rect.height) + pad * 2;
        return {
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
          cx: left + width / 2,
          cy: top + height / 2,
        };
      };

      const questionRectOverlapArea = (left, top, width, height, rect) => {
        if (!rect) {
          return 0;
        }
        const right = left + width;
        const bottom = top + height;
        const overlapWidth = Math.max(0, Math.min(right, rect.right) - Math.max(left, rect.left));
        const overlapHeight = Math.max(0, Math.min(bottom, rect.bottom) - Math.max(top, rect.top));
        return overlapWidth * overlapHeight;
      };

      const questionNearestPointOnRectEdge = (point, rect) => {
        if (!point || !rect) {
          return point || { x: 0, y: 0 };
        }
        const clampedX = Math.max(rect.left, Math.min(rect.right, point.x));
        const clampedY = Math.max(rect.top, Math.min(rect.bottom, point.y));
        const distances = [
          { x: rect.left, y: clampedY, d: Math.abs(point.x - rect.left) },
          { x: rect.right, y: clampedY, d: Math.abs(point.x - rect.right) },
          { x: clampedX, y: rect.top, d: Math.abs(point.y - rect.top) },
          { x: clampedX, y: rect.bottom, d: Math.abs(point.y - rect.bottom) },
        ];
        distances.sort((left, right) => left.d - right.d);
        return { x: distances[0].x, y: distances[0].y };
      };

      const positionQuestionRootHoverInfoAtPointer = (sourceNode, pointerEvent) => {
        const card = ensureQuestionRootHoverInfoLayer();
        if (!shellNode || !card || !questionRootHoverInfoConnector || !sourceNode || !pointerEvent) {
          return;
        }
        const shellRect = shellNode.getBoundingClientRect();
        const visible = questionVisibleBoundsInShell();
        const visiblePad = 12;
        const mouse = {
          x: questionUnscaleLayoutValue(pointerEvent.clientX - shellRect.left),
          y: questionUnscaleLayoutValue(pointerEvent.clientY - shellRect.top),
        };
        const visibleWidth = Math.max(260, visible.width - visiblePad * 2);
        const cardWidth = Math.min(330, Math.max(250, visibleWidth * 0.34));
        card.classList.add("is-cursor-follow-signal");
        card.style.width = `${cardWidth}px`;
        const measuredRect = card.getBoundingClientRect();
        const cardHeight = Math.min(
          Math.max(96, questionUnscaleLayoutValue(measuredRect.height || 142)),
          Math.max(96, visible.height - visiblePad * 2),
        );
        const rootTextRect = qRootText && qRootText.getBoundingClientRect
          ? questionRectInShellFromClientRect(qRootText.getBoundingClientRect(), 10)
          : null;
        const sourceRect = sourceNode && sourceNode.getBoundingClientRect
          ? questionRectInShellFromClientRect(sourceNode.getBoundingClientRect(), 8)
          : null;
        const offsetX = 24;
        const offsetY = 22;
        const clampLeft = (value) => Math.max(visible.left + visiblePad, Math.min(value, visible.right - cardWidth - visiblePad));
        const clampTop = (value) => Math.max(visible.top + visiblePad, Math.min(value, visible.bottom - cardHeight - visiblePad));
        const rawCandidates = [
          { left: mouse.x + offsetX, top: mouse.y + offsetY, bias: 0 },
          { left: mouse.x + offsetX, top: mouse.y - cardHeight - offsetY, bias: 32 },
          { left: mouse.x - cardWidth - offsetX, top: mouse.y + offsetY, bias: 42 },
          { left: mouse.x - cardWidth - offsetX, top: mouse.y - cardHeight - offsetY, bias: 58 },
          rootTextRect ? { left: rootTextRect.right + 18, top: mouse.y + offsetY, bias: 74 } : null,
          rootTextRect ? { left: rootTextRect.left - cardWidth - 18, top: mouse.y + offsetY, bias: 86 } : null,
          rootTextRect ? { left: mouse.x + offsetX, top: rootTextRect.bottom + 18, bias: 98 } : null,
          rootTextRect ? { left: mouse.x + offsetX, top: rootTextRect.top - cardHeight - 18, bias: 110 } : null,
        ].filter(Boolean);
        const ranked = rawCandidates.map((candidate) => {
          const left = clampLeft(candidate.left);
          const top = clampTop(candidate.top);
          const moved = Math.abs(left - candidate.left) + Math.abs(top - candidate.top);
          const rootOverlap = questionRectOverlapArea(left, top, cardWidth, cardHeight, rootTextRect);
          const sourceOverlap = questionRectOverlapArea(left, top, cardWidth, cardHeight, sourceRect);
          const isRightBottom = left >= mouse.x && top >= mouse.y;
          return {
            left,
            top,
            score:
              candidate.bias
              + moved * 0.8
              + rootOverlap * 0.032
              + sourceOverlap * 0.22
              + (isRightBottom ? 0 : 18),
          };
        }).sort((left, right) => left.score - right.score);
        const chosen = ranked[0] || { left: clampLeft(mouse.x + offsetX), top: clampTop(mouse.y + offsetY) };
        card.style.left = `${chosen.left}px`;
        card.style.top = `${chosen.top}px`;
        const cardRect = {
          left: chosen.left,
          top: chosen.top,
          right: chosen.left + cardWidth,
          bottom: chosen.top + cardHeight,
          width: cardWidth,
          height: cardHeight,
        };
        const end = questionNearestPointOnRectEdge(mouse, cardRect);
        questionRootHoverInfoConnector.classList.add("is-cursor-follow-signal");
        questionRootHoverInfoConnector.classList.remove("is-elbow");
        questionRootHoverInfoConnector.classList.remove("is-region-rail");
        positionQuestionLine(questionRootHoverInfoConnector, mouse, end);
      };

      const positionQuestionRootHoverInfo = (sourceNode, pointerEvent = null) => {
        const card = ensureQuestionRootHoverInfoLayer();
        if (!shellNode || !card || !questionRootHoverInfoConnector || !sourceNode) {
          return;
        }
        if (questionRootHoverSignalShouldFollowPointer() && pointerEvent && Number.isFinite(Number(pointerEvent.clientX)) && Number.isFinite(Number(pointerEvent.clientY))) {
          positionQuestionRootHoverInfoAtPointer(sourceNode, pointerEvent);
          return;
        }
        card.classList.remove("is-cursor-follow-signal");
        questionRootHoverInfoConnector.classList.remove("is-cursor-follow-signal");
        const shellRect = shellNode.getBoundingClientRect();
        const sourceRect = sourceNode.getBoundingClientRect();
        const shellWidth = questionUnscaleLayoutValue(shellRect.width);
        const shellHeight = questionUnscaleLayoutValue(shellRect.height);
        const sourceLeft = questionUnscaleLayoutValue(sourceRect.left - shellRect.left);
        const sourceTop = questionUnscaleLayoutValue(sourceRect.top - shellRect.top);
        const sourceWidth = questionUnscaleLayoutValue(sourceRect.width);
        const sourceHeight = questionUnscaleLayoutValue(sourceRect.height);
        const sourceRight = sourceLeft + sourceWidth;
        const sourceCenterX = sourceLeft + sourceWidth / 2;
        const sourceCenterY = sourceTop + sourceHeight / 2;
        const cardWidth = Math.min(360, Math.max(260, shellWidth * 0.28));
        let left = sourceRight + 28;
        if (left + cardWidth > shellWidth - 16) {
          left = Math.max(16, sourceLeft - cardWidth - 28);
        }
        left = Math.max(16, Math.min(left, Math.max(16, shellWidth - cardWidth - 16)));
        const top = Math.max(16, Math.min(sourceTop - 12, Math.max(16, shellHeight - 180)));
        card.style.width = `${cardWidth}px`;
        card.style.left = `${left}px`;
        card.style.top = `${top}px`;
        const cardRect = card.getBoundingClientRect();
        const cardLeft = questionUnscaleLayoutValue(cardRect.left - shellRect.left);
        const cardTop = questionUnscaleLayoutValue(cardRect.top - shellRect.top);
        const cardWidthMeasured = questionUnscaleLayoutValue(cardRect.width);
        const cardHeightMeasured = questionUnscaleLayoutValue(cardRect.height);
        const start = { x: sourceCenterX, y: sourceCenterY };
        const end = {
          x: cardLeft + (cardLeft > sourceLeft ? 0 : cardWidthMeasured),
          y: cardTop + Math.min(cardHeightMeasured * 0.42, 60),
        };
        questionRootHoverInfoConnector.classList.remove("is-elbow");
        questionRootHoverInfoConnector.classList.remove("is-region-rail");
        positionQuestionLine(questionRootHoverInfoConnector, start, end);
      };

      const typeQuestionRootHoverInfoText = (text) => {
        const body = questionRootHoverInfoCard && questionRootHoverInfoCard.querySelector(".ft-q-root-info-body");
        if (!body) {
          return;
        }
        if (questionRootHoverInfoTypingTimer) {
          window.clearTimeout(questionRootHoverInfoTypingTimer);
          questionRootHoverInfoTypingTimer = 0;
        }
        const fullText = preserveQuestionText(text) || "No annotation text.";
        body.style.removeProperty("min-height");
        body.textContent = fullText;
        const stableHeight = Math.ceil(body.getBoundingClientRect().height || 0);
        if (stableHeight > 0) {
          body.style.minHeight = `${stableHeight}px`;
        }
        body.textContent = "";
        let index = 0;
        const tick = () => {
          index += Math.max(1, Math.ceil(fullText.length / 70));
          body.textContent = fullText.slice(0, index);
          if (index < fullText.length) {
            questionRootHoverInfoTypingTimer = window.setTimeout(tick, 16 + Math.random() * 22);
          } else {
            questionRootHoverInfoTypingTimer = 0;
          }
        };
        tick();
      };

      const showQuestionRootHoverInfo = (sourceNode, pointerEvent = null) => {
        if (questionRootHoverSignalIsSelectMobileHidden()) {
          hideQuestionRootHoverInfo();
          return;
        }
        const card = ensureQuestionRootHoverInfoLayer();
        if (!card || !sourceNode) {
          return;
        }
        const title = card.querySelector(".ft-q-root-info-title");
        if (title) {
          title.textContent = "Root Signal";
        }
        card.classList.remove("is-question");
        card.classList.remove("is-picture-region-question");
        card.classList.remove("is-preparing");
        card.classList.add("is-live");
        if (questionRootHoverInfoConnector) {
          questionRootHoverInfoConnector.classList.add("is-live");
          questionRootHoverInfoConnector.classList.add("is-focused");
        }
        typeQuestionRootHoverInfoText(questionRootHoverInfoTextForSource(sourceNode));
        window.requestAnimationFrame(() => positionQuestionRootHoverInfo(sourceNode, pointerEvent));
      };

      const ensureQuestionPictureRegionLayer = () => {
        const frame = qPictureCard && qPictureCard.querySelector(".ft-q-picture-frame");
        if (!frame) {
          return null;
        }
        if (!questionPictureRegionLayer) {
          questionPictureRegionLayer = document.createElement("div");
          questionPictureRegionLayer.className = "ft-q-picture-region-layer";
          frame.appendChild(questionPictureRegionLayer);
        } else if (questionPictureRegionLayer.parentNode !== frame) {
          frame.appendChild(questionPictureRegionLayer);
        }
        return questionPictureRegionLayer;
      };

      const hideQuestionPictureRegions = () => {
        if (questionPictureRegionLayer) {
          questionPictureRegionLayer.classList.remove("is-live");
          questionPictureRegionLayer.innerHTML = "";
        }
      };

      const renderQuestionPictureRegions = (regions = []) => {
        const cleanRegions = normalizeQuestionPictureRegions(regions);
        const layer = ensureQuestionPictureRegionLayer();
        if (!layer || !qPictureImg || !qPictureImg.getBoundingClientRect().width || !cleanRegions.length) {
          if (!(cleanRegions.length && questionPictureRegionPromptLocked)) {
            hideQuestionPictureRegions();
          }
          return [];
        }
        const frameRect = layer.parentNode.getBoundingClientRect();
        const imageRect = qPictureImg.getBoundingClientRect();
        layer.innerHTML = "";
        const regionRects = [];
        cleanRegions.forEach((region, index) => {
          const left = questionUnscaleLayoutValue(imageRect.left - frameRect.left + imageRect.width * region.x);
          const top = questionUnscaleLayoutValue(imageRect.top - frameRect.top + imageRect.height * region.y);
          const width = questionUnscaleLayoutValue(imageRect.width * region.w);
          const height = questionUnscaleLayoutValue(imageRect.height * region.h);
          const node = document.createElement("span");
          node.className = "ft-q-picture-region";
          node.dataset.regionId = region.id || `r${index + 1}`;
          node.style.left = `${left}px`;
          node.style.top = `${top}px`;
          node.style.width = `${Math.max(8, width)}px`;
          node.style.height = `${Math.max(8, height)}px`;
          node.style.setProperty("--q-region-delay", `${index * 110}ms`);
          const color = optionalQuestionPictureRegionColor(region.color ?? region.c ?? region.border_color ?? region.borderColor);
          if (color) {
            node.style.setProperty("--q-picture-region-color", color);
            node.style.setProperty("--q-picture-region-rgb", questionColorToRgb(color).join(", "));
          }
          node.innerHTML = '<i></i><i></i><i></i>';
          layer.appendChild(node);
          regionRects.push(node.getBoundingClientRect());
        });
        layer.classList.add("is-live");
        return regionRects;
      };

      const questionPictureRegionAnchorPoints = (regions = []) => {
        if (!shellNode) {
          return [];
        }
        const regionRects = renderQuestionPictureRegions(regions);
        const shellRect = shellNode.getBoundingClientRect();
        return regionRects.map((rect, index) => ({
          x: questionUnscaleLayoutValue(rect.right - shellRect.left),
          y: questionUnscaleLayoutValue(rect.top - shellRect.top + rect.height / 2),
          index,
          rect: {
            left: questionUnscaleLayoutValue(rect.left - shellRect.left),
            top: questionUnscaleLayoutValue(rect.top - shellRect.top),
            right: questionUnscaleLayoutValue(rect.right - shellRect.left),
            bottom: questionUnscaleLayoutValue(rect.bottom - shellRect.top),
            width: questionUnscaleLayoutValue(rect.width),
            height: questionUnscaleLayoutValue(rect.height),
          },
        }));
      };

      const hideQuestionSelectConnectors = () => {
        questionSelectAnswerRevealActive = false;
        if (questionSelectAnswerRevealTimer) {
          window.clearTimeout(questionSelectAnswerRevealTimer);
          questionSelectAnswerRevealTimer = 0;
        }
        if (questionSelectConnectorLayer) {
          questionSelectConnectorLayer.innerHTML = "";
          questionSelectConnectorLayer.classList.remove("is-live", "is-complete", "is-answer-reveal");
        }
      };

      const ensureQuestionSelectConnectorLayer = () => {
        if (!shellNode) {
          return null;
        }
        if (!questionSelectConnectorLayer) {
          questionSelectConnectorLayer = document.createElement("div");
          questionSelectConnectorLayer.className = "ft-q-select-connector-layer";
          shellNode.appendChild(questionSelectConnectorLayer);
        } else if (questionSelectConnectorLayer.parentNode !== shellNode) {
          shellNode.appendChild(questionSelectConnectorLayer);
        }
        return questionSelectConnectorLayer;
      };

      const questionSelectRectInShell = (node, pad = 0) => {
        if (!node || !node.getBoundingClientRect || !shellNode) {
          return null;
        }
        const rect = node.getBoundingClientRect();
        const shellRect = shellNode.getBoundingClientRect();
        const left = questionUnscaleLayoutValue(rect.left - shellRect.left) - pad;
        const top = questionUnscaleLayoutValue(rect.top - shellRect.top) - pad;
        const width = questionUnscaleLayoutValue(rect.width) + pad * 2;
        const height = questionUnscaleLayoutValue(rect.height) + pad * 2;
        if (width <= 0 || height <= 0) {
          return null;
        }
        return {
          node,
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
          cx: left + width * 0.5,
          cy: top + height * 0.5,
        };
      };

      const questionSelectObstacleRects = (anchors = []) => {
        const nodes = new Set((Array.isArray(anchors) ? anchors : []).filter(Boolean));
        if (qRootText) {
          qRootText.querySelectorAll(".ft-q-select-root-merge, .ft-q-select-root-overlay.is-selected").forEach((node) => nodes.add(node));
        }
        if (questionPictureRegionLayer) {
          questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer.is-selected").forEach((node) => nodes.add(node));
        }
        return Array.from(nodes)
          .map((node) => questionSelectRectInShell(node, 8))
          .filter(Boolean);
      };

      const questionSelectShellBounds = () => {
        if (!shellNode || !shellNode.getBoundingClientRect) {
          return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
        }
        const rect = shellNode.getBoundingClientRect();
        const width = questionUnscaleLayoutValue(rect.width);
        const height = questionUnscaleLayoutValue(rect.height);
        return { left: 0, top: 0, right: width, bottom: height, width, height };
      };

      const questionSelectSegmentHitsHorizontal = (x1, x2, y, obstacles = [], ignoredNode = null) => {
        const left = Math.min(x1, x2);
        const right = Math.max(x1, x2);
        return obstacles.some((rect) => {
          if (!rect || rect.node === ignoredNode) {
            return false;
          }
          return y >= rect.top && y <= rect.bottom && Math.max(left, rect.left) <= Math.min(right, rect.right);
        });
      };

      const questionSelectSegmentHitsVertical = (x, y1, y2, obstacles = [], ignoredNode = null) => {
        const top = Math.min(y1, y2);
        const bottom = Math.max(y1, y2);
        return obstacles.some((rect) => {
          if (!rect || rect.node === ignoredNode) {
            return false;
          }
          return x >= rect.left && x <= rect.right && Math.max(top, rect.top) <= Math.min(bottom, rect.bottom);
        });
      };

      const questionSelectClampLaneY = (laneY, anchorRect = null) => {
        const bounds = questionSelectShellBounds();
        if (!bounds.height) {
          return laneY;
        }
        const pad = 18;
        const minY = bounds.top + pad;
        const maxY = Math.max(minY, bounds.bottom - pad);
        const safeY = Math.max(minY, Math.min(maxY, laneY));
        if (anchorRect && safeY >= anchorRect.top && safeY <= anchorRect.bottom) {
          return laneY < anchorRect.cy
            ? Math.max(minY, anchorRect.top - pad)
            : Math.min(maxY, anchorRect.bottom + pad);
        }
        return safeY;
      };

      const questionSelectLaneScore = (anchorRect, startX, trunkX, laneY, obstacles, ignoredNode = null) => {
        let score = Math.abs(laneY - anchorRect.cy) * 0.08;
        if (questionSelectSegmentHitsVertical(startX, anchorRect.cy, laneY, obstacles, ignoredNode)) {
          score += 10000;
        }
        if (questionSelectSegmentHitsHorizontal(startX, trunkX, laneY, obstacles, ignoredNode)) {
          score += 10000;
        }
        const left = Math.min(startX, trunkX);
        const right = Math.max(startX, trunkX);
        obstacles.forEach((rect) => {
          if (!rect || rect.node === ignoredNode) {
            return;
          }
          const overlapsX = Math.max(left, rect.left) <= Math.min(right, rect.right);
          if (!overlapsX) {
            return;
          }
          if (laneY >= rect.top && laneY <= rect.bottom) {
            score += 1500;
            return;
          }
          const distanceY = Math.min(Math.abs(laneY - rect.top), Math.abs(laneY - rect.bottom));
          if (distanceY < 14) {
            score += (14 - distanceY) * 12;
          }
        });
        return score;
      };

      const appendQuestionSelectConnectorSegment = (layer, start, end, className = "") => {
        if (!layer || !start || !end || Math.hypot(end.x - start.x, end.y - start.y) < 1) {
          return null;
        }
        const line = document.createElement("span");
        line.className = `ft-q-select-connector ${className}`.trim();
        layer.appendChild(line);
        positionQuestionLine(line, start, end);
        return line;
      };

      const appendQuestionSelectConnectorNode = (layer, point, className = "") => {
        if (!layer || !point) {
          return null;
        }
        const node = document.createElement("span");
        node.className = `ft-q-select-connector-node ${className}`.trim();
        node.style.left = `${point.x}px`;
        node.style.top = `${point.y}px`;
        layer.appendChild(node);
        return node;
      };

      const chooseQuestionSelectBranchLane = (anchorRect, startX, trunkX, obstacles, index = 0) => {
        const baseY = anchorRect.cy;
        const spread = 18 + (index % 4) * 8;
        const rawCandidates = [
          anchorRect.top - spread,
          anchorRect.bottom + spread,
          baseY - 42 - (index % 3) * 13,
          baseY + 42 + (index % 3) * 13,
          baseY - 74 - (index % 2) * 16,
          baseY + 74 + (index % 2) * 16,
        ];
        const candidates = [];
        rawCandidates.forEach((laneY) => {
          const clamped = Math.round(questionSelectClampLaneY(laneY, anchorRect) * 10) / 10;
          if (Number.isFinite(clamped) && !candidates.some((value) => Math.abs(value - clamped) < 1)) {
            candidates.push(clamped);
          }
        });
        const ranked = candidates
          .map((laneY) => ({
            laneY,
            score: questionSelectLaneScore(anchorRect, startX, trunkX, laneY, obstacles, anchorRect.node),
          }))
          .sort((left, right) => left.score - right.score);
        return ranked.length ? ranked[0].laneY : baseY;
      };

      const positionQuestionSelectConnectors = () => {
        if (!questionSelectAnswerRevealActive) {
          hideQuestionSelectConnectors();
          return;
        }
        const item = currentQuestionItem();
        const layer = ensureQuestionSelectConnectorLayer();
        if (!layer || !item || !isQuestionSelectItem(item) || !qQuestionCard || !isQuestionCardInLayout(qQuestionCard) || !shellNode) {
          hideQuestionSelectConnectors();
          return;
        }
        const anchors = [
          ...(qRootText ? Array.from(qRootText.querySelectorAll(".ft-q-select-root-merge")) : []),
          ...Array.from(document.querySelectorAll(".ft-q-select-root-token.is-selected:not(.is-merged)")),
          ...(questionPictureRegionLayer ? Array.from(questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer.is-selected")) : []),
        ].filter((node) => node && node.getBoundingClientRect);
        layer.innerHTML = "";
        if (!anchors.length) {
          layer.classList.remove("is-live");
          return;
        }
        const anchorRects = anchors.map((anchor) => questionSelectRectInShell(anchor, 0)).filter(Boolean);
        const cardRect = questionSelectRectInShell(qQuestionCard, 0);
        if (!anchorRects.length || !cardRect) {
          layer.classList.remove("is-live");
          return;
        }
        const obstacles = questionSelectObstacleRects(anchors);
        const shellBounds = questionSelectShellBounds();
        const minLeft = Math.min(...anchorRects.map((rect) => rect.left));
        const maxRight = Math.max(...anchorRects.map((rect) => rect.right));
        const avgX = anchorRects.reduce((sum, rect) => sum + rect.cx, 0) / anchorRects.length;
        const leftRoom = Math.max(0, minLeft - shellBounds.left);
        const rightRoom = Math.max(0, shellBounds.right - maxRight);
        let goRight = cardRect.cx >= avgX;
        if (cardRect.left >= maxRight + 20) {
          goRight = true;
        } else if (cardRect.right <= minLeft - 20) {
          goRight = false;
        } else if (Math.abs(rightRoom - leftRoom) > 72) {
          goRight = rightRoom >= leftRoom;
        }
        const branchGap = 6;
        const trunkGap = 34;
        const shellPad = 18;
        let trunkX = goRight ? maxRight + trunkGap : minLeft - trunkGap;
        if (goRight && cardRect.left > maxRight) {
          trunkX = Math.min(trunkX, cardRect.left - 28);
          trunkX = Math.max(trunkX, maxRight + 16);
        } else if (!goRight && cardRect.right < minLeft) {
          trunkX = Math.max(trunkX, cardRect.right + 28);
          trunkX = Math.min(trunkX, minLeft - 16);
        }
        if (shellBounds.width) {
          trunkX = Math.max(shellBounds.left + shellPad, Math.min(shellBounds.right - shellPad, trunkX));
        }
        if (trunkX > cardRect.left - 8 && trunkX < cardRect.right + 8) {
          const leftCandidate = cardRect.left - 30;
          const rightCandidate = cardRect.right + 30;
          const canUseLeft = leftCandidate > shellBounds.left + shellPad;
          const canUseRight = rightCandidate < shellBounds.right - shellPad;
          if (goRight && canUseLeft && leftCandidate > maxRight + 12) {
            trunkX = leftCandidate;
          } else if (!goRight && canUseRight && rightCandidate < minLeft - 12) {
            trunkX = rightCandidate;
          } else if (canUseRight && (!canUseLeft || rightRoom >= leftRoom)) {
            trunkX = rightCandidate;
            goRight = true;
          } else if (canUseLeft) {
            trunkX = leftCandidate;
            goRight = false;
          }
        }
        let end;
        if (trunkX <= cardRect.left) {
          end = { x: cardRect.left, y: cardRect.cy };
        } else if (trunkX >= cardRect.right) {
          end = { x: cardRect.right, y: cardRect.cy };
        } else {
          const avgY = anchorRects.reduce((sum, rect) => sum + rect.cy, 0) / anchorRects.length;
          end = avgY <= cardRect.cy
            ? { x: cardRect.cx, y: cardRect.top }
            : { x: cardRect.cx, y: cardRect.bottom };
        }
        const junctions = [];
        anchorRects.forEach((rect, index) => {
          const sourceRight = trunkX >= rect.cx;
          const start = {
            x: sourceRight ? rect.right + branchGap : rect.left - branchGap,
            y: rect.cy,
          };
          const directBlocked = questionSelectSegmentHitsHorizontal(start.x, trunkX, start.y, obstacles, rect.node);
          const laneY = directBlocked ? chooseQuestionSelectBranchLane(rect, start.x, trunkX, obstacles, index) : start.y;
          const junction = { x: trunkX, y: laneY };
          appendQuestionSelectConnectorNode(layer, start, "is-source");
          if (Math.abs(laneY - start.y) > 1) {
            appendQuestionSelectConnectorSegment(layer, start, { x: start.x, y: laneY }, "is-branch is-elbow");
            appendQuestionSelectConnectorNode(layer, { x: start.x, y: laneY }, "is-elbow");
          }
          appendQuestionSelectConnectorSegment(layer, { x: start.x, y: laneY }, junction, "is-branch");
          appendQuestionSelectConnectorNode(layer, junction, "is-junction");
          junctions.push(junction);
        });
        const trunkTop = Math.min(end.y, ...junctions.map((point) => point.y));
        const trunkBottom = Math.max(end.y, ...junctions.map((point) => point.y));
        appendQuestionSelectConnectorSegment(layer, { x: trunkX, y: trunkTop }, { x: trunkX, y: trunkBottom }, "is-trunk");
        appendQuestionSelectConnectorSegment(layer, { x: trunkX, y: end.y }, end, "is-terminal");
        appendQuestionSelectConnectorNode(layer, end, "is-end");
        layer.classList.add("is-live");
      };

      const questionSelectRootRangesForItem = (item) => {
        const targets = questionSelectTargets(item);
        const rootText = preserveQuestionText((questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root && questionCurrentNode.cards.root.text) || questionTypingFullText || "");
        if (!rootText) {
          return [];
        }
        if (targets.root_ranges.length) {
          return targets.root_ranges.map((entry, index) => {
            let start = Math.max(0, Math.min(rootText.length, Math.floor(Number(entry.start) || 0)));
            let end = Math.max(0, Math.min(rootText.length, Math.floor(Number(entry.end) || 0)));
            const text = preserveQuestionText(entry.text);
            if ((!end || end <= start) && text) {
              const found = rootText.indexOf(text);
              if (found >= 0) {
                start = found;
                end = found + text.length;
              }
            }
            if (end <= start) {
              return null;
            }
            return {
              start,
              end,
              text: rootText.slice(start, end),
              color: "#6cf0a4",
              style: "style-4",
              render: "block",
              info: "Select the answer words in this highlighted signal.",
              sourceIndex: 9100 + index,
              selectTarget: true,
            };
          }).filter(Boolean);
        }
        const targetText = targets.root_text;
        if (!targetText) {
          return [];
        }
        const found = rootText.indexOf(targetText);
        if (found < 0) {
          return [];
        }
        return [{
          start: found,
          end: found + targetText.length,
          text: targetText,
          color: "#6cf0a4",
          style: "style-4",
          render: "block",
          info: "Select the answer words in this highlighted signal.",
          sourceIndex: 9100,
          selectTarget: true,
        }];
      };

      const clearQuestionSelectRootOverlays = () => {
        if (!qRootText) {
          return;
        }
        qRootText.querySelectorAll(".ft-q-select-root-overlay-layer").forEach((node) => node.remove());
      };

      const questionRootLineForOffset = (rootText = "", offset = 0) => {
        const lines = preserveQuestionText(rootText).split("\n");
        const safeOffset = Math.max(0, Math.floor(Number(offset) || 0));
        let lineStart = 0;
        for (let index = 0; index < lines.length; index += 1) {
          const line = lines[index] || "";
          const lineEnd = lineStart + line.length;
          if (safeOffset >= lineStart && safeOffset <= lineEnd) {
            return { index, lineStart, lineEnd, line };
          }
          lineStart = lineEnd + 1;
        }
        const fallbackIndex = Math.max(0, lines.length - 1);
        const fallbackLine = lines[fallbackIndex] || "";
        return {
          index: fallbackIndex,
          lineStart: Math.max(0, preserveQuestionText(rootText).length - fallbackLine.length),
          lineEnd: preserveQuestionText(rootText).length,
          line: fallbackLine,
        };
      };

      const questionRootTextPositionInHost = (host, offset = 0) => {
        if (!host) {
          return null;
        }
        const targetOffset = Math.max(0, Math.floor(Number(offset) || 0));
        const walker = document.createTreeWalker(
          host,
          NodeFilter.SHOW_TEXT,
          {
            acceptNode(node) {
              return node && node.parentElement && node.parentElement.closest(".ft-q-select-root-overlay-layer")
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT;
            },
          },
        );
        let cursor = 0;
        let lastNode = null;
        let node = walker.nextNode();
        while (node) {
          const length = (node.nodeValue || "").length;
          if (targetOffset <= cursor + length) {
            return { node, offset: Math.max(0, Math.min(length, targetOffset - cursor)) };
          }
          cursor += length;
          lastNode = node;
          node = walker.nextNode();
        }
        return lastNode ? { node: lastNode, offset: (lastNode.nodeValue || "").length } : null;
      };

      const createQuestionRootTextRange = (rootText, start, end) => {
        if (!qRootText || end <= start) {
          return null;
        }
        const startLine = questionRootLineForOffset(rootText, start);
        const endLine = questionRootLineForOffset(rootText, end);
        if (!startLine || !endLine || startLine.index !== endLine.index) {
          return null;
        }
        const lineNodes = Array.from(qRootText.querySelectorAll(".ft-q-root-line"));
        const host = lineNodes[startLine.index];
        if (!host) {
          return null;
        }
        const startPosition = questionRootTextPositionInHost(host, start - startLine.lineStart);
        const endPosition = questionRootTextPositionInHost(host, end - startLine.lineStart);
        if (!startPosition || !endPosition) {
          return null;
        }
        const range = document.createRange();
        range.setStart(startPosition.node, startPosition.offset);
        range.setEnd(endPosition.node, endPosition.offset);
        return range;
      };

      const currentQuestionRootTextForSelectOverlay = () => preserveQuestionText(
        (questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root && questionCurrentNode.cards.root.text)
          || questionTypingFullText
          || "",
      );

      const positionQuestionSelectRootNode = (node, rect, rootRect) => {
        if (!node || !rect || !rootRect || !qRootText) {
          return;
        }
        node.style.left = `${questionUnscaleLayoutValue(rect.left - rootRect.left) + qRootText.scrollLeft}px`;
        node.style.top = `${questionUnscaleLayoutValue(rect.top - rootRect.top) + qRootText.scrollTop}px`;
        node.style.width = `${Math.max(6, questionUnscaleLayoutValue(rect.width))}px`;
        node.style.height = `${Math.max(8, questionUnscaleLayoutValue(rect.height))}px`;
      };

      const repositionQuestionSelectRootOverlays = (rootText = "") => {
        if (!qRootText) {
          return;
        }
        const layer = qRootText.querySelector(".ft-q-select-root-overlay-layer");
        if (!layer) {
          return;
        }
        const overlayRootText = preserveQuestionText(rootText || currentQuestionRootTextForSelectOverlay());
        const rootRect = qRootText.getBoundingClientRect();
        layer.style.height = `${Math.max(qRootText.scrollHeight, qRootText.clientHeight)}px`;
        layer.style.width = `${Math.max(qRootText.scrollWidth, qRootText.clientWidth)}px`;
        Array.from(layer.querySelectorAll(".ft-q-select-root-overlay")).forEach((button) => {
          const start = Number(button.dataset ? button.dataset.qSelectStart : NaN);
          const end = Number(button.dataset ? button.dataset.qSelectEnd : NaN);
          if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
            return;
          }
          const domRange = createQuestionRootTextRange(overlayRootText, start, end);
          if (!domRange) {
            return;
          }
          const rects = Array.from(domRange.getClientRects()).filter((rect) => rect && rect.width > 0 && rect.height > 0);
          if (typeof domRange.detach === "function") {
            domRange.detach();
          }
          if (!rects.length) {
            return;
          }
          const rectIndex = Math.max(0, Math.min(rects.length - 1, Number(button.dataset ? button.dataset.qSelectRectIndex : 0) || 0));
          positionQuestionSelectRootNode(button, rects[rectIndex] || rects[0], rootRect);
        });
        refreshQuestionSelectRootMergedHighlights();
      };

      const scheduleQuestionSelectRootOverlayReposition = (rootText = "") => {
        if (questionSelectRootOverlayFrame) {
          return;
        }
        questionSelectRootOverlayFrame = window.requestAnimationFrame(() => {
          questionSelectRootOverlayFrame = 0;
          repositionQuestionSelectRootOverlays(rootText);
        });
      };

      const renderQuestionSelectRootOverlays = (selectRanges = [], rootText = "") => {
        if (!qRootText || !selectRanges.length) {
          return false;
        }
        clearQuestionSelectRootOverlays();
        const layer = document.createElement("span");
        layer.className = "ft-q-select-root-overlay-layer";
        layer.setAttribute("aria-hidden", "true");
        layer.style.height = `${Math.max(qRootText.scrollHeight, qRootText.clientHeight)}px`;
        layer.style.width = `${Math.max(qRootText.scrollWidth, qRootText.clientWidth)}px`;
        qRootText.appendChild(layer);
        const rootRect = qRootText.getBoundingClientRect();
        const wordPattern = /[\p{L}\p{N}]+(?:['’\-][\p{L}\p{N}]+)*/gu;
        let overlayCount = 0;
        selectRanges.forEach((range, rangeIndex) => {
          const source = preserveQuestionText(rootText).slice(range.start, range.end);
          wordPattern.lastIndex = 0;
          let match;
          while ((match = wordPattern.exec(source)) !== null) {
            const word = match[0];
            const tokenStart = range.start + match.index;
            const tokenEnd = tokenStart + word.length;
            const domRange = createQuestionRootTextRange(rootText, tokenStart, tokenEnd);
            if (!domRange) {
              continue;
            }
            const rects = Array.from(domRange.getClientRects()).filter((rect) => rect && rect.width > 0 && rect.height > 0);
            if (typeof domRange.detach === "function") {
              domRange.detach();
            }
            rects.forEach((rect, rectIndex) => {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "ft-q-select-root-token ft-q-select-root-overlay";
              button.dataset.qSelectKind = "root";
              button.dataset.qSelectToken = word;
              button.dataset.qSelectIndex = `${Number.isInteger(range.sourceIndex) ? range.sourceIndex : rangeIndex}-${tokenStart}-${rectIndex}`;
              button.dataset.qSelectRange = `${Number.isInteger(range.sourceIndex) ? range.sourceIndex : rangeIndex}`;
              button.dataset.qSelectStart = String(tokenStart);
              button.dataset.qSelectEnd = String(tokenEnd);
              button.dataset.qSelectRectIndex = String(rectIndex);
              button.dataset.qhInfo = preserveQuestionText(range.info || "Root selection signal.");
              button.setAttribute("aria-label", "Select text token");
              positionQuestionSelectRootNode(button, rect, rootRect);
              layer.appendChild(button);
              overlayCount += 1;
            });
          }
        });
        if (!overlayCount) {
          layer.remove();
          return false;
        }
        scheduleQuestionSelectRootOverlayReposition(rootText);
        return true;
      };

      const refreshQuestionSelectRootMergedHighlights = () => {
        if (!qRootText) {
          return;
        }
        const layer = qRootText.querySelector(".ft-q-select-root-overlay-layer");
        if (!layer) {
          return;
        }
        layer.querySelectorAll(".ft-q-select-root-merge").forEach((node) => node.remove());
        const buttons = Array.from(layer.querySelectorAll(".ft-q-select-root-overlay"));
        buttons.forEach((button) => button.classList.remove("is-merged"));
        const rootText = preserveQuestionText((questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root && questionCurrentNode.cards.root.text) || questionTypingFullText || "");
        const selected = buttons
          .filter((button) => button.classList.contains("is-selected") && !button.classList.contains("is-token-wrong"))
          .map((button) => {
            const start = Number(button.dataset ? button.dataset.qSelectStart : NaN);
            const end = Number(button.dataset ? button.dataset.qSelectEnd : NaN);
            return {
              button,
              start,
              end,
              range: clean(button.dataset ? button.dataset.qSelectRange : ""),
            };
          })
          .filter((entry) => Number.isFinite(entry.start) && Number.isFinite(entry.end) && entry.end > entry.start)
          .sort((left, right) => left.start - right.start || left.end - right.end);
        const groups = [];
        selected.forEach((entry) => {
          const group = groups[groups.length - 1];
          const gap = group ? rootText.slice(group.end, entry.start) : "";
          const isAdjacent = group && group.range === entry.range && entry.start >= group.end && /^\s*$/.test(gap);
          if (isAdjacent) {
            group.end = Math.max(group.end, entry.end);
            group.entries.push(entry);
            return;
          }
          groups.push({
            start: entry.start,
            end: entry.end,
            range: entry.range,
            entries: [entry],
          });
        });
        const rootRect = qRootText.getBoundingClientRect();
        groups.filter((group) => group.entries.length > 1).forEach((group) => {
          const domRange = createQuestionRootTextRange(rootText, group.start, group.end);
          if (!domRange) {
            return;
          }
          const rects = Array.from(domRange.getClientRects()).filter((rect) => rect && rect.width > 0 && rect.height > 0);
          if (typeof domRange.detach === "function") {
            domRange.detach();
          }
          if (!rects.length) {
            return;
          }
          group.entries.forEach((entry) => entry.button.classList.add("is-merged"));
          rects.forEach((rect) => {
            const merged = document.createElement("span");
            merged.className = "ft-q-select-root-merge";
            merged.style.left = `${questionUnscaleLayoutValue(rect.left - rootRect.left) + qRootText.scrollLeft}px`;
            merged.style.top = `${questionUnscaleLayoutValue(rect.top - rootRect.top) + qRootText.scrollTop}px`;
            merged.style.width = `${Math.max(6, questionUnscaleLayoutValue(rect.width))}px`;
            merged.style.height = `${Math.max(8, questionUnscaleLayoutValue(rect.height))}px`;
            layer.prepend(merged);
          });
        });
      };

      const renderQuestionSelectRootTargets = (item) => {
        if (!qRootText || !item || !isQuestionSelectItem(item)) {
          return false;
        }
        const rootText = preserveQuestionText((questionCurrentNode && questionCurrentNode.cards && questionCurrentNode.cards.root && questionCurrentNode.cards.root.text) || questionTypingFullText || "");
        if (!rootText) {
          return false;
        }
        const selectRanges = [{
          start: 0,
          end: rootText.length,
          text: rootText,
          color: "#6cf0a4",
          style: "style-4",
          render: "none",
          info: "Select any word in the question root.",
          sourceIndex: 9100,
          selectTarget: true,
        }];
        const baseRanges = questionRootHighlightRangesForItem(item).filter((range) => !range.selectTarget);
        qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: baseRanges });
        renderQuestionSelectRootOverlays(selectRanges, rootText);
        refreshQuestionSelectRootMergedHighlights();
        attachQuestionRootHighlightEvents();
        return true;
      };

      const handleQuestionSelectRootTokenClick = (button) => {
        const item = currentQuestionItem();
        if (!button || !item || !isQuestionSelectItem(item)) {
          return;
        }
        if (questionSelectCompletionTimer) {
          return;
        }
        const token = clean(button.dataset ? button.dataset.qSelectToken : button.textContent);
        if (!token) {
          return;
        }
        const selected = button.classList.toggle("is-selected");
        button.classList.remove("is-token-wrong");
        if (!selected) {
          updateQuestionSelectProgressCard(item);
          refreshQuestionSelectRootMergedHighlights();
          setQuestionAnswerFeedback("Target removed. Select the full answer again.", "");
          focusQuestionSelectSubmitButton();
          return;
        }
        refreshQuestionSelectRootMergedHighlights();
        updateQuestionSelectProgressCard(item);
        void playEffectSoundAsync("open");
        setQuestionAnswerFeedback("Targets selected. Press Lock when you are ready.", "");
        focusQuestionSelectSubmitButton();
      };

      const handleQuestionSelectRootRangeClick = (node) => {
        if (!node || !node.querySelectorAll) {
          return;
        }
        const tokens = Array.from(node.querySelectorAll(".ft-q-select-root-token"));
        if (!tokens.length) {
          return;
        }
        const allSelected = tokens.every((token) => token.classList.contains("is-selected"));
        const targets = allSelected
          ? tokens
          : tokens.filter((token) => !token.classList.contains("is-selected"));
        targets.forEach((token) => handleQuestionSelectRootTokenClick(token));
      };

      const handleQuestionSelectRegionClick = (node) => {
        const item = currentQuestionItem();
        if (!node || !item || !isQuestionSelectItem(item)) {
          return;
        }
        if (questionSelectCompletionTimer) {
          return;
        }
        stopQuestionAudio();
        stopQuestionCardActiveAudio();
        const regionKey = clean(node.dataset ? node.dataset.selectRegion : "");
        if (!regionKey) {
          return;
        }
        const selected = node.classList.toggle("is-selected");
        node.classList.remove("is-token-wrong");
        if (!selected) {
          updateQuestionSelectProgressCard(item);
          setQuestionAnswerFeedback("Region removed. Select the full answer again.", "");
          focusQuestionSelectSubmitButton();
          return;
        }
        updateQuestionSelectProgressCard(item);
        void playEffectSoundAsync("open");
        setQuestionAnswerFeedback("Targets selected. Press Lock when you are ready.", "");
        focusQuestionSelectSubmitButton();
      };

      const renderQuestionSelectPictureTargets = (item) => {
        if (!item || !isQuestionSelectItem(item)) {
          return false;
        }
        const targets = questionSelectTargets(item);
        if (!targets.regions.length) {
          return false;
        }
        if (targets.region_color) {
          applyQuestionPictureRegionColor(questionCurrentNode, { region_color: targets.region_color });
        }
        renderQuestionPictureRegions(targets.regions);
        if (!questionPictureRegionLayer) {
          return false;
        }
        questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region").forEach((node, index) => {
          node.classList.add("is-select-answer");
          node.dataset.selectRegion = questionSelectRegionKey(targets.regions[index], index);
          node.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            handleQuestionSelectRegionClick(node);
          });
        });
        return true;
      };

      const renderQuestionSelectTargetsForItem = (item = currentQuestionItem()) => {
        if (!item || !isQuestionSelectItem(item)) {
          return false;
        }
        renderQuestionSelectRootTargets(item);
        renderQuestionSelectPictureTargets(item);
        updateQuestionSelectProgressCard(item);
        hideQuestionSelectConnectors();
        return true;
      };

      const clearQuestionSelectTargets = () => {
        clearQuestionSelectCompletionState();
        hideQuestionSelectConnectors();
        if (qSelectSubmitButton) {
          qSelectSubmitButton.classList.add("ft-q-show-answer-hidden");
          qSelectSubmitButton.disabled = true;
        }
        clearQuestionSelectRootOverlays();
        if (qRootText && qRootText.querySelector(".ft-q-root-highlight.is-select-target")) {
          qRootText.innerHTML = renderQuestionRootMarkup(questionTypingFullText);
          attachQuestionRootHighlightEvents();
        }
        if (questionPictureRegionLayer) {
          questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region.is-select-answer").forEach((node) => {
            node.classList.remove("is-select-answer", "is-selected");
            delete node.dataset.selectRegion;
          });
        }
      };

      const isQuestionPictureRegionPromptPinned = () => Boolean(
        questionPictureRegionPromptLocked
        && questionRootInfoActivePayload
        && questionRootInfoActivePayload.anchor === "picture_regions",
      );

      const settleQuestionPictureRegionPrompt = () => {
        [0, 80, 220, 520].forEach((delay) => {
          window.setTimeout(() => {
            if (isQuestionPictureRegionPromptPinned()) {
              repositionActiveQuestionRootInfo();
            }
          }, delay);
        });
      };

      const hideQuestionRootInfo = (force = false) => {
        hideQuestionRootHoverInfo();
        if (!force && isQuestionPictureRegionPromptPinned()) {
          repositionActiveQuestionRootInfo();
          return;
        }
        if (force) {
          questionPictureRegionPromptLocked = false;
        }
        if (questionRootInfoTypingTimer) {
          window.clearTimeout(questionRootInfoTypingTimer);
          questionRootInfoTypingTimer = 0;
        }
        questionRootInfoActiveAnchor = null;
        questionRootInfoActivePayload = null;
        if (questionRootInfoCard) {
          questionRootInfoCard.classList.remove("is-live");
          questionRootInfoCard.classList.remove("is-preparing");
          questionRootInfoCard.classList.remove("is-question");
          questionRootInfoCard.classList.remove("is-picture-region-question");
          const body = questionRootInfoCard.querySelector(".ft-q-root-info-body");
          if (body) {
            body.style.removeProperty("min-height");
          }
        }
        resetQuestionPicturePromptControls();
        hideQuestionRootInfoConnectors();
        hideQuestionPictureRegions();
        scheduleQuestionSideLayout();
      };

      const typeQuestionRootInfoText = (text) => {
        const body = questionRootInfoCard && questionRootInfoCard.querySelector(".ft-q-root-info-body");
        if (!body) {
          return;
        }
        if (questionRootInfoTypingTimer) {
          window.clearTimeout(questionRootInfoTypingTimer);
          questionRootInfoTypingTimer = 0;
        }
        const fullText = preserveQuestionText(text) || "No annotation text.";
        body.style.removeProperty("min-height");
        body.textContent = fullText;
        const stableHeight = Math.ceil(body.getBoundingClientRect().height || 0);
        if (stableHeight > 0) {
          body.style.minHeight = `${stableHeight}px`;
        }
        body.textContent = "";
        let index = 0;
        const tick = () => {
          index += Math.max(1, Math.ceil(fullText.length / 70));
          body.textContent = fullText.slice(0, index);
          if (questionRootInfoActivePayload && questionRootInfoActivePayload.anchor === "picture_regions") {
            window.requestAnimationFrame(repositionActiveQuestionRootInfo);
          }
          if (index < fullText.length) {
            questionRootInfoTypingTimer = window.setTimeout(tick, 16 + Math.random() * 22);
          } else {
            questionRootInfoTypingTimer = 0;
          }
        };
        tick();
      };

      const questionRootPictureAnchorNode = () => {
        if (qPictureCard && qPictureCard.classList.contains("is-live")) {
          return qPictureCard.querySelector(".ft-q-picture-ship-core")
            || qPictureCard.querySelector(".ft-q-picture-ship")
            || qPictureCard;
        }
        return qPictureCard || qRootCard;
      };

      const positionQuestionRootInfoSegment = (segment, start, end) => {
        if (!segment || !start || !end) {
          return;
        }
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const length = Math.max(1, Math.hypot(dx, dy));
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        segment.style.left = `${start.x}px`;
        segment.style.top = `${start.y}px`;
        segment.style.width = `${length}px`;
        segment.style.transform = `translateY(-50%) rotate(${angle}deg)`;
      };

      const inflateQuestionRouteRect = (rect, margin = 10) => ({
        left: Math.min(rect.left, rect.right) - margin,
        top: Math.min(rect.top, rect.bottom) - margin,
        right: Math.max(rect.left, rect.right) + margin,
        bottom: Math.max(rect.top, rect.bottom) + margin,
      });

      const questionRouteSegmentHitsRect = (start, end, rect) => {
        if (!start || !end || !rect) {
          return false;
        }
        const minX = Math.min(start.x, end.x);
        const maxX = Math.max(start.x, end.x);
        const minY = Math.min(start.y, end.y);
        const maxY = Math.max(start.y, end.y);
        if (Math.abs(start.y - end.y) <= 0.5) {
          const y = start.y;
          return y >= rect.top && y <= rect.bottom && Math.max(minX, rect.left) < Math.min(maxX, rect.right);
        }
        if (Math.abs(start.x - end.x) <= 0.5) {
          const x = start.x;
          return x >= rect.left && x <= rect.right && Math.max(minY, rect.top) < Math.min(maxY, rect.bottom);
        }
        const samples = Math.max(6, Math.ceil(Math.hypot(end.x - start.x, end.y - start.y) / 18));
        for (let index = 1; index < samples; index += 1) {
          const ratio = index / samples;
          const x = start.x + (end.x - start.x) * ratio;
          const y = start.y + (end.y - start.y) * ratio;
          if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
            return true;
          }
        }
        return false;
      };

      const routeQuestionRegionConnector = (start, target, obstacles = [], context = {}) => {
        const cleanStart = { x: Number(start && start.x) || 0, y: Number(start && start.y) || 0 };
        const cleanTarget = { x: Number(target && target.x) || 0, y: Number(target && target.y) || 0 };
        const routeMargin = Math.max(10, Math.min(22, Number(context.margin) || 14));
        const pictureRight = Number(context.pictureRight) || Math.max(cleanStart.x, cleanTarget.x);
        const pictureLeft = Number(context.pictureLeft) || 0;
        const pictureTop = Number(context.pictureTop) || 0;
        const pictureBottom = Number(context.pictureBottom) || 0;
        const busX = Math.max(
          pictureRight + routeMargin * 1.35,
          cleanStart.x + routeMargin * 2,
          cleanTarget.x,
          ...obstacles.map((rect) => rect.right + routeMargin),
        );
        const xValues = [
          cleanStart.x,
          cleanTarget.x,
          cleanStart.x + routeMargin,
          cleanTarget.x - routeMargin,
          busX,
          pictureRight + routeMargin,
          pictureRight + routeMargin * 2.2,
          pictureLeft - routeMargin,
        ];
        const yValues = [
          cleanStart.y,
          cleanTarget.y,
          pictureTop - routeMargin,
          pictureBottom + routeMargin,
        ];
        obstacles.forEach((rect) => {
          xValues.push(rect.left - routeMargin, rect.right + routeMargin);
          yValues.push(rect.top - routeMargin, rect.bottom + routeMargin);
        });
        const uniq = (values) => Array.from(new Set(values
          .map((value) => Math.round(Number(value) || 0))
          .filter((value) => Number.isFinite(value))))
          .sort((left, right) => left - right);
        const xs = uniq(xValues);
        const ys = uniq(yValues);
        const keyFor = (x, y) => `${x},${y}`;
        const parseKey = (key) => {
          const [x, y] = key.split(",").map((value) => Number(value) || 0);
          return { x, y };
        };
        const segmentClear = (a, b) => !obstacles.some((rect) => questionRouteSegmentHitsRect(a, b, rect));
        const startKey = keyFor(Math.round(cleanStart.x), Math.round(cleanStart.y));
        const targetKey = keyFor(Math.round(cleanTarget.x), Math.round(cleanTarget.y));
        const distances = new Map([[startKey, 0]]);
        const previous = new Map();
        const turns = new Map([[startKey, 0]]);
        const directionTo = new Map([[startKey, ""]]);
        const visited = new Set();
        const candidateKeys = [];
        xs.forEach((x) => ys.forEach((y) => candidateKeys.push(keyFor(x, y))));
        const neighborKeys = (point) => {
          const result = [];
          const xIndex = xs.indexOf(point.x);
          const yIndex = ys.indexOf(point.y);
          if (xIndex > 0) result.push(keyFor(xs[xIndex - 1], point.y));
          if (xIndex >= 0 && xIndex < xs.length - 1) result.push(keyFor(xs[xIndex + 1], point.y));
          if (yIndex > 0) result.push(keyFor(point.x, ys[yIndex - 1]));
          if (yIndex >= 0 && yIndex < ys.length - 1) result.push(keyFor(point.x, ys[yIndex + 1]));
          return result;
        };
        while (visited.size < candidateKeys.length) {
          let currentKey = "";
          let currentScore = Number.POSITIVE_INFINITY;
          candidateKeys.forEach((key) => {
            if (visited.has(key)) {
              return;
            }
            const distance = distances.get(key);
            if (!Number.isFinite(distance)) {
              return;
            }
            const point = parseKey(key);
            const heuristic = Math.abs(point.x - cleanTarget.x) + Math.abs(point.y - cleanTarget.y);
            const score = distance + heuristic * 0.15 + (turns.get(key) || 0) * routeMargin * 0.8;
            if (score < currentScore) {
              currentScore = score;
              currentKey = key;
            }
          });
          if (!currentKey || currentKey === targetKey) {
            break;
          }
          visited.add(currentKey);
          const current = parseKey(currentKey);
          neighborKeys(current).forEach((nextKey) => {
            if (visited.has(nextKey)) {
              return;
            }
            const next = parseKey(nextKey);
            if (!segmentClear(current, next)) {
              return;
            }
            const direction = Math.abs(next.x - current.x) > Math.abs(next.y - current.y) ? "h" : "v";
            const turnPenalty = directionTo.get(currentKey) && directionTo.get(currentKey) !== direction ? 1 : 0;
            const distance = (distances.get(currentKey) || 0) + Math.abs(next.x - current.x) + Math.abs(next.y - current.y) + turnPenalty * routeMargin * 1.8;
            if (distance < (distances.get(nextKey) ?? Number.POSITIVE_INFINITY)) {
              distances.set(nextKey, distance);
              previous.set(nextKey, currentKey);
              turns.set(nextKey, (turns.get(currentKey) || 0) + turnPenalty);
              directionTo.set(nextKey, direction);
            }
          });
        }
        if (!previous.has(targetKey) && startKey !== targetKey) {
          return [cleanStart, { x: busX, y: cleanStart.y }, { x: busX, y: cleanTarget.y }, cleanTarget];
        }
        const path = [];
        let cursor = targetKey;
        path.unshift(parseKey(cursor));
        while (cursor !== startKey) {
          cursor = previous.get(cursor);
          if (!cursor) {
            return [cleanStart, { x: busX, y: cleanStart.y }, { x: busX, y: cleanTarget.y }, cleanTarget];
          }
          path.unshift(parseKey(cursor));
        }
        const compact = [];
        path.forEach((point) => {
          const last = compact[compact.length - 1];
          const prev = compact[compact.length - 2];
          if (last && Math.abs(last.x - point.x) <= 0.5 && Math.abs(last.y - point.y) <= 0.5) {
            return;
          }
          if (prev && last) {
            const sameX = Math.abs(prev.x - last.x) <= 0.5 && Math.abs(last.x - point.x) <= 0.5;
            const sameY = Math.abs(prev.y - last.y) <= 0.5 && Math.abs(last.y - point.y) <= 0.5;
            if (sameX || sameY) {
              compact[compact.length - 1] = point;
              return;
            }
          }
          compact.push(point);
        });
        return compact.length > 1 ? compact : [cleanStart, cleanTarget];
      };

      const stableQuestionUnit = (value = "") => {
        const text = preserveQuestionText(value);
        let hash = 2166136261;
        for (let index = 0; index < text.length; index += 1) {
          hash ^= text.charCodeAt(index);
          hash = Math.imul(hash, 16777619);
        }
        return ((hash >>> 0) % 1000) / 999;
      };

      const pictureRegionQuestionVerticalUnit = (payload = {}) => {
        if (payload && Number.isFinite(payload.__regionVerticalUnit)) {
          return payload.__regionVerticalUnit;
        }
        const seed = `${payload && payload.text ? payload.text : ""}|${JSON.stringify(payload && payload.regions ? payload.regions : [])}`;
        const unit = stableQuestionUnit(seed);
        if (payload && typeof payload === "object") {
          payload.__regionVerticalUnit = unit;
        }
        return unit;
      };
