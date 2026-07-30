

      function renderQuestionMobileGuidancePage(entry, options = {}) {
        const layer = questionPictureAnswerLayer || ensureQuestionPictureAnswerLayer();
        if (!layer || !entry || !entry.node) {
          return false;
        }
        const node = entry.node;
        const path = clean(entry.path || "link");
        const depth = Math.max(1, Math.floor(Number(entry.depth) || 1));
        layer.querySelectorAll(".ft-q-mobile-guidance-page").forEach((page) => page.remove());
        questionGuidanceBranchNodes = questionGuidanceBranchNodes.filter((nodeItem) => (
          nodeItem && nodeItem.isConnected && !(nodeItem.closest && nodeItem.closest(".ft-q-mobile-guidance-page"))
        ));
        const page = document.createElement("div");
        page.className = "ft-q-mobile-guidance-page";
        page.dataset.guidanceOwner = path;
        page.dataset.guidanceDepth = String(depth);
        const header = document.createElement("div");
        header.className = "ft-q-mobile-guidance-head";
        header.innerHTML = `
          <span class="ft-q-mobile-guidance-kicker">Linked page ${String(questionMobileGuidanceStack.length || 1).padStart(2, "0")}</span>
          <span class="ft-q-mobile-guidance-title"></span>
        `;
        const title = header.querySelector(".ft-q-mobile-guidance-title");
        if (title) {
          title.textContent = entry.title || "Linked branch";
        }
        page.appendChild(header);
        const quizBranch = questionGuidanceNodeIsQuestion(node);
        const quizType = clean(node && node.type).toLowerCase();
        const quizUnlocked = !quizBranch || questionGuidanceUnlockedPaths.has(path);
        const rawChildren = quizBranch ? [] : (Array.isArray(node.children) ? node.children : []);
        const mainText = quizBranch ? preserveQuestionText(node.question) : preserveQuestionText(node.main);
        const children = quizBranch
          ? []
          : (rawChildren.length
            ? rawChildren
            : (mainText ? [{ title: "Info detail", body: mainText, main: "" }] : []));
        const enterNodes = [];
        const mainNode = document.createElement("div");
        mainNode.className = "ft-q-guidance-branch-main";
        mainNode.dataset.guidanceDepth = String(depth);
        mainNode.dataset.guidanceOwner = path;
        mainNode.classList.toggle("is-guidance-question-prompt", quizBranch);
        if (!options.noEnter) {
          prepareQuestionGuidanceEnter(mainNode, "0ms");
        }
        mainNode.textContent = quizBranch
          ? (mainText || "Branch question")
          : (rawChildren.length ? (mainText || "Branch link") : "Detail link");
        page.appendChild(mainNode);
        questionGuidanceBranchNodes.push(mainNode);
        enterNodes.push(mainNode);
        const ownerCard = entry.parentCard && entry.parentCard.isConnected ? entry.parentCard : page;
        let childCards = [];
        if (quizBranch && quizUnlocked) {
          const answerIndex = Math.max(0, Math.floor(Number(questionGuidanceUnlockedAnswerIndex.get(path)) || 0));
          const answerValue = preserveQuestionText(questionGuidanceUnlockedAnswerValue.get(path))
            || questionGuidanceAnswerOptionsForNode(node)[answerIndex]
            || "";
          if (quizType === "input") {
            const childNode = questionGuidanceDisplayChildForAnswer(node, path, answerIndex);
            childCards = [createQuestionGuidanceInputCard(ownerCard, node, path, depth, {
              ...options,
              answered: true,
              answerValue,
              childNode,
              childPath: childNode ? `${path}.${answerIndex}` : "",
            })];
          } else {
            const optionsList = questionGuidanceChoiceOptions(node);
            const correctKey = questionAnswerKey(questionGuidanceAnswerOptionsForNode(node)[answerIndex] || questionGuidanceAcceptedAnswers(node)[0] || "");
            childCards = optionsList.map((option, index) => {
              const childNode = questionGuidanceDisplayChildForAnswer(node, path, index);
              return createQuestionGuidanceChoiceCard(ownerCard, node, path, depth, option, index, {
                ...options,
                answered: true,
                correct: questionAnswerKey(option) === correctKey,
                childNode,
                childPath: childNode ? `${path}.${index}` : "",
              });
            });
          }
        } else if (quizBranch) {
          childCards = quizType === "input"
            ? [createQuestionGuidanceInputCard(ownerCard, node, path, depth, options)]
            : shuffleIndexes(questionGuidanceChoiceOptions(node).length).map((optionIndex, index) => (
              createQuestionGuidanceChoiceCard(ownerCard, node, path, depth, questionGuidanceChoiceOptions(node)[optionIndex], index, options)
            ));
        } else {
          childCards = children.map((child, index) => {
            const childPath = `${path}.${index}`;
            questionGuidanceNodeMap.set(childPath, child);
            const card = createQuestionGuidanceBranchCard(child, childPath, depth, index, options);
            card.dataset.guidanceOwner = path;
            return card;
          });
        }
        childCards.forEach((card) => {
          card.dataset.guidanceOwner = path;
          card.style.removeProperty("left");
          card.style.removeProperty("top");
          card.style.removeProperty("width");
          page.appendChild(card);
          questionGuidanceBranchNodes.push(card);
          enterNodes.push(card);
        });
        layer.appendChild(page);
        if (!options.noEnter) {
          startQuestionGuidanceEnter(enterNodes);
        }
        if ((options.autoOpenFirstChild || options.restoreUnlocked !== false) && !options.noEnter) {
          const nextCard = preferredQuestionGuidanceChildCard(childCards, node, path);
          if (nextCard && options.autoOpenFirstChild) {
            window.setTimeout(() => {
              if (nextCard.isConnected && questionModeActive && isQuestionMobileFlow()) {
                openQuestionGuidanceCard(nextCard, {
                  forceOpen: true,
                  preservePinned: false,
                  pan: false,
                  restoreUnlocked: true,
                });
              }
            }, 260);
          }
        }
        syncQuestionMobilePicturePager();
        return true;
      }

      const hideQuestionPictureAnswerCards = () => {
        questionPictureRegionPromptLocked = false;
        questionPictureAnswerActive = false;
        questionPictureAnswerPreparedItem = null;
        questionPictureAnswerOptionValues = [];
        questionPictureAnswerFeedbackNode = null;
        questionGuidanceBranchNodes = [];
        questionGuidanceNodeMap.clear();
        questionGuidanceUnlockedPaths.clear();
        questionGuidanceUnlockedAnswerIndex.clear();
        questionGuidanceUnlockedAnswerValue.clear();
        questionGuidancePinnedPaths.clear();
        resetQuestionMobilePicturePager();
        resetQuestionPicturePromptControls();
        if (questionPictureAnswerLayer) {
          questionPictureAnswerLayer.classList.remove("is-live", "is-preparing", "is-layout-pending");
          questionPictureAnswerLayer.innerHTML = "";
        }
        if (questionRootInfoCard) {
          questionRootInfoCard.classList.remove("is-picture-answer-layout-pending");
        }
        questionPictureAnswerConnectors = [];
      };

      const questionGuidanceTreeEntryForOption = (question, option, optionIndex = -1) => {
        const tree = question && question.guidance_tree && typeof question.guidance_tree === "object" ? question.guidance_tree : null;
        const items = tree && Array.isArray(tree.items) ? tree.items : [];
        const key = questionAnswerKey(option);
        return items.find((entry) => questionAnswerKey(entry && entry.text) === key)
          || (Number.isInteger(optionIndex) && optionIndex >= 0 ? items[optionIndex] : null)
          || (items.length === 1 ? items[0] : null)
          || items.find((entry) => !questionAnswerKey(entry && entry.text))
          || null;
      };

      const questionGuidanceNodeHasBranch = (node) => Boolean(
        node && (
          preserveQuestionText(node.main)
          || questionGuidanceNodeIsQuestion(node)
          || (Array.isArray(node.children) && node.children.length)
        )
      );

      function questionGuidanceNodeIsQuestion(node) {
        const type = clean(node && node.type).toLowerCase();
        return Boolean(
          node
          && (type === "choice" || type === "input")
          && preserveQuestionText(node.question)
          && clean(node.answer)
        );
      }

      const questionGuidanceAcceptedAnswers = (node) => {
        const answer = clean(node && node.answer);
        const type = clean(node && node.type).toLowerCase();
        const values = type === "input" && Array.isArray(node && node.answers)
          ? node.answers
          : [answer];
        const seen = new Set();
        return values
          .map(clean)
          .filter((value) => {
            const key = questionAnswerKey(value);
            if (!value || !key || seen.has(key)) {
              return false;
            }
            seen.add(key);
            return true;
          });
      };

      const questionGuidanceChoiceOptions = (node) => {
        const answer = clean(node && node.answer);
        const wrong = Array.isArray(node && node.wrong) ? node.wrong : [];
        const seen = new Set();
        return [answer, ...wrong.map(clean)]
          .filter((value) => {
            const key = questionAnswerKey(value);
            if (!value || !key || seen.has(key)) {
              return false;
            }
            seen.add(key);
            return true;
          });
      };

      const questionGuidanceAnswerOptionsForNode = (node) => (
        clean(node && node.type).toLowerCase() === "input"
          ? questionGuidanceAcceptedAnswers(node)
          : questionGuidanceChoiceOptions(node)
      );

      const questionGuidanceAnswerChildKey = (child) => questionAnswerKey(
        clean(child && (child.answer_option || child.answerOption || child.option || child.title))
      );

      const questionGuidanceNodeUsesAnswerChildren = (node) => {
        const children = Array.isArray(node && node.children) ? node.children : [];
        const options = questionGuidanceAnswerOptionsForNode(node);
        if (!questionGuidanceNodeIsQuestion(node) || !children.length || !options.length) {
          return false;
        }
        return options.some((option, index) => {
          const child = children[index];
          return child && questionGuidanceAnswerChildKey(child) === questionAnswerKey(option);
        });
      };

      const questionGuidanceAnswerIndexForValue = (node, value) => {
        const key = questionAnswerKey(value);
        return questionGuidanceAnswerOptionsForNode(node).findIndex((option) => questionAnswerKey(option) === key);
      };

      const questionGuidanceUnlockedChildrenForNode = (node, path) => {
        const rawChildren = Array.isArray(node && node.children) ? node.children : [];
        if (!questionGuidanceNodeIsQuestion(node) || !questionGuidanceNodeUsesAnswerChildren(node)) {
          return rawChildren;
        }
        if (clean(node && node.type).toLowerCase() === "choice") {
          const optionKeys = questionGuidanceAnswerOptionsForNode(node).map((option) => questionAnswerKey(option));
          const matched = [];
          const leftovers = [];
          rawChildren.forEach((child) => {
            const index = optionKeys.indexOf(questionGuidanceAnswerChildKey(child));
            if (index >= 0) {
              matched[index] = child;
            } else {
              leftovers.push(child);
            }
          });
          return matched.filter(Boolean).concat(leftovers);
        }
        const answerIndex = Math.max(0, Math.floor(Number(questionGuidanceUnlockedAnswerIndex.get(path)) || 0));
        const answerOptions = questionGuidanceAnswerOptionsForNode(node);
        const answerKey = questionAnswerKey(answerOptions[answerIndex] || answerOptions[0] || "");
        const answerChild = rawChildren.find((child) => questionGuidanceAnswerChildKey(child) === answerKey)
          || rawChildren[answerIndex];
        if (!answerChild) {
          return [];
        }
        if (preserveQuestionText(answerChild.body) || preserveQuestionText(answerChild.main) || questionGuidanceNodeIsQuestion(answerChild)) {
          return [answerChild];
        }
        const nested = Array.isArray(answerChild.children) ? answerChild.children : [];
        if (nested.length) {
          return nested;
        }
        return [];
      };

      const questionGuidanceDisplayChildForAnswer = (node, path, answerIndex = 0) => {
        if (!questionGuidanceNodeIsQuestion(node)) {
          return null;
        }
        const children = questionGuidanceUnlockedChildrenForNode(node, path);
        if (!children.length) {
          return null;
        }
        const type = clean(node && node.type).toLowerCase();
        if (type === "choice") {
          return children[Math.max(0, Math.floor(Number(answerIndex) || 0))] || null;
        }
        if (children.length === 1) {
          return children[0];
        }
        return {
          main: "Answer branch",
          children,
        };
      };

      const questionGuidancePathDepth = (path) => Math.max(0, String(path || "").split(".").length - 1);

      const appendQuestionGuidanceChildBadge = (card) => {
        if (!card || card.querySelector(".ft-q-guidance-child-orbit")) {
          return;
        }
        const target = card.querySelector(".ft-q-picture-answer-kicker, .ft-q-choice-kicker") || card;
        const badge = document.createElement("span");
        badge.className = "ft-q-guidance-child-orbit";
        badge.innerHTML = "<i></i><span>Linked</span>";
        if (target.classList) {
          target.classList.add("has-guidance-orbit");
        }
        target.appendChild(badge);
      };

      const finishQuestionGuidanceEnter = (node) => {
        if (!node || !node.classList) {
          return;
        }
        window.setTimeout(() => {
          if (node.isConnected) {
            node.classList.remove("is-guidance-entering");
          }
        }, 2200);
      };

      const prepareQuestionGuidanceEnter = (node, delay = "0ms") => {
        if (!node || !node.classList) {
          return node;
        }
        node.classList.add("is-guidance-prime");
        node.style.setProperty("--q-guidance-delay", delay);
        return node;
      };

      const startQuestionGuidanceEnter = (nodes) => {
        const list = (Array.isArray(nodes) ? nodes : [nodes]).filter((node) => node && node.classList);
        if (!list.length) {
          return;
        }
        window.requestAnimationFrame(() => {
          list.forEach((node) => {
            if (!node.isConnected) {
              return;
            }
            node.classList.remove("is-guidance-prime");
            node.classList.add("is-guidance-entering");
            finishQuestionGuidanceEnter(node);
          });
        });
      };

      const questionGuidanceLayoutRectInLayer = (node, layer, layerRect = null) => {
        if (!node || !layer) {
          return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
        }
        const left = Number.parseFloat(node.style && node.style.left);
        const top = Number.parseFloat(node.style && node.style.top);
        const width = Number(node.offsetWidth) || 0;
        const height = Number(node.offsetHeight) || 0;
        if (Number.isFinite(left) && Number.isFinite(top) && width && height && (node.parentElement === layer || layer.contains(node))) {
          return {
            left,
            top,
            right: left + width,
            bottom: top + height,
            width,
            height,
          };
        }
        const rect = node.getBoundingClientRect();
        const base = layerRect || layer.getBoundingClientRect();
        const rectLeft = questionUnscaleLayoutValue(rect.left - base.left);
        const rectTop = questionUnscaleLayoutValue(rect.top - base.top);
        const rectWidth = questionUnscaleLayoutValue(rect.width || 0);
        const rectHeight = questionUnscaleLayoutValue(rect.height || 0);
        return {
          left: rectLeft,
          top: rectTop,
          right: rectLeft + rectWidth,
          bottom: rectTop + rectHeight,
          width: rectWidth,
          height: rectHeight,
        };
      };

      const clearQuestionGuidanceBranches = (minDepth = 1, options = {}) => {
        const depth = Math.max(1, Math.floor(Number(minDepth) || 1));
        const openScope = shellNode || questionPictureAnswerLayer;
        const pinnedOwners = new Set(
          options.preservePinned && openScope
            ? Array.from(openScope.querySelectorAll(".has-guidance-children.is-guidance-pinned"))
              .map((card) => clean(card.dataset.guidancePath || ""))
              .filter(Boolean)
            : []
        );
        questionGuidanceBranchNodes = questionGuidanceBranchNodes.filter((node) => {
          const nodeDepth = Math.max(1, Math.floor(Number(node && node.dataset && node.dataset.guidanceDepth) || 1));
          const ownerPath = clean(node && node.dataset && node.dataset.guidanceOwner);
          if (nodeDepth >= depth && ownerPath && pinnedOwners.has(ownerPath)) {
            return true;
          }
          if (nodeDepth >= depth) {
            if (node && node.parentNode) {
              node.parentNode.removeChild(node);
            }
            return false;
          }
          return true;
        });
        if (openScope) {
          openScope.querySelectorAll(".is-guidance-open").forEach((card) => {
            const cardDepth = Math.max(0, Math.floor(Number(card.dataset.guidanceDepth) || 0));
            if (cardDepth >= depth - 1 && !(options.preservePinned && card.classList.contains("is-guidance-pinned"))) {
              card.classList.remove("is-guidance-open");
              card.setAttribute("aria-expanded", "false");
            }
          });
        }
        Array.from(questionGuidanceNodeMap.keys()).forEach((path) => {
          const pathDepth = questionGuidancePathDepth(path);
          const keepPinnedMap = options.preservePinned && Array.from(pinnedOwners).some((ownerPath) => (
            path === ownerPath || path.startsWith(`${ownerPath}.`)
          ));
          if (pathDepth >= depth && !keepPinnedMap) {
            questionGuidanceNodeMap.delete(path);
          }
        });
        Array.from(questionGuidanceCloseTimers.keys()).forEach((path) => {
          if (questionGuidancePathDepth(path) >= depth - 1) {
            cancelQuestionGuidanceClose(path);
          }
        });
      };

      const questionGuidanceNodeForCard = (card) => {
        if (!card) {
          return null;
        }
        const path = clean(card.dataset.guidancePath || "");
        if (path && questionGuidanceNodeMap.has(path)) {
          return questionGuidanceNodeMap.get(path);
        }
        const item = currentQuestionItem();
        const option = clean(card.dataset.answer || "");
        const slot = Math.max(0, (Math.floor(Number(card.dataset.slot) || 1) || 1) - 1);
        const node = questionGuidanceTreeEntryForOption(item, option, slot);
        if (path && node) {
          questionGuidanceNodeMap.set(path, node);
        }
        return node || null;
      };

      const focusQuestionGuidanceCardOnClick = (card) => {
        if (!card || !card.isConnected) {
          return false;
        }
        window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
          if (questionModeActive && card.isConnected) {
            centerQuestionCardInView(card);
          }
        }));
        return true;
      };

      const scheduleQuestionGuidanceOpen = (card, delay = 110) => {
        if (!card || !card.classList || !card.classList.contains("has-guidance-children")) {
          return false;
        }
        if (isQuestionMobileFlow()) {
          return false;
        }
        const path = clean(card.dataset.guidancePath || "");
        if (path) {
          cancelQuestionGuidanceClose(path);
        }
        const previous = questionGuidanceHoverTimers.get(card);
        if (previous) {
          window.clearTimeout(previous);
        }
        const run = () => {
          questionGuidanceHoverTimers.delete(card);
          if (card.isConnected && !card.classList.contains("is-guidance-open")) {
            openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: false });
          }
        };
        if (delay <= 0) {
          run();
          return true;
        }
        const timer = window.setTimeout(run, Math.max(0, Number(delay) || 0));
        questionGuidanceHoverTimers.set(card, timer);
        return true;
      };

      const cancelQuestionGuidanceClose = (path) => {
        const key = clean(path);
        if (!key || !questionGuidanceCloseTimers.has(key)) {
          return;
        }
        window.clearTimeout(questionGuidanceCloseTimers.get(key));
        questionGuidanceCloseTimers.delete(key);
      };

      const questionGuidanceElementBelongsToPath = (node, path) => {
        const key = clean(path);
        if (!node || !node.dataset || !key) {
          return false;
        }
        const owner = clean(node.dataset.guidanceOwner || "");
        const nodePath = clean(node.dataset.guidancePath || "");
        return owner === key
          || owner.startsWith(`${key}.`)
          || nodePath === key
          || nodePath.startsWith(`${key}.`);
      };

      const questionGuidancePathIsHovered = (path) => {
        const key = clean(path);
        const scope = shellNode || questionPictureAnswerLayer;
        if (!key || !scope) {
          return false;
        }
        const candidates = scope.querySelectorAll("[data-guidance-path], [data-guidance-owner]");
        for (const node of candidates) {
          if (!questionGuidanceElementBelongsToPath(node, key)) {
            continue;
          }
          try {
            const active = document.activeElement;
            const keepFocusedInput = active
              && node.contains(active)
              && active.matches
              && active.matches("input, textarea, select, [contenteditable='true']");
            if (node.matches(":hover") || keepFocusedInput) {
              return true;
            }
          } catch (error) {
          }
        }
        return false;
      };

      const scheduleQuestionGuidanceCloseForPath = (path, depth = 1, ownerCard = null, delay = 180) => {
        const key = clean(path);
        if (!key) {
          return false;
        }
        cancelQuestionGuidanceClose(key);
        const timer = window.setTimeout(() => {
          questionGuidanceCloseTimers.delete(key);
          if (questionGuidancePathIsHovered(key)) {
            return;
          }
          clearQuestionGuidanceBranches(depth, { preservePinned: false });
          if (ownerCard && ownerCard.classList) {
            ownerCard.classList.remove("is-guidance-open", "is-guidance-pinned");
            ownerCard.setAttribute("aria-expanded", "false");
          }
        }, Math.max(0, Number(delay) || 0));
        questionGuidanceCloseTimers.set(key, timer);
        return true;
      };

      const wireQuestionGuidanceHoverNode = (node, path, depth, ownerCard = null) => {
        if (!node || !node.addEventListener || node.dataset.guidanceHoverWired === "1") {
          return node;
        }
        node.dataset.guidanceHoverWired = "1";
        const key = clean(path);
        node.addEventListener("pointerenter", () => cancelQuestionGuidanceClose(key));
        node.addEventListener("mouseenter", () => cancelQuestionGuidanceClose(key));
        return node;
      };

      const wireQuestionGuidanceCard = (card) => {
        if (!card || !card.classList || card.dataset.guidanceWired === "1") {
          return card;
        }
        card.dataset.guidanceWired = "1";
        card.setAttribute("aria-expanded", "false");
        card.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: true });
        });
        card.addEventListener("pointerenter", () => {
          if (isQuestionMobileFlow()) {
            return;
          }
          scheduleQuestionGuidanceOpen(card, 28);
        });
        card.addEventListener("mouseenter", () => {
          if (isQuestionMobileFlow()) {
            return;
          }
          scheduleQuestionGuidanceOpen(card, 28);
        });
        card.addEventListener("focus", () => {
          if (isQuestionMobileFlow()) {
            return;
          }
          openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: false });
        });
        card.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: true });
          }
        });
        return card;
      };

      const openQuestionGuidanceCard = (card, options = {}) => {
        if (!card || !card.isConnected || !card.classList || !card.classList.contains("has-guidance-children")) {
          return false;
        }
        const node = questionGuidanceNodeForCard(card);
        if (!questionGuidanceNodeHasBranch(node)) {
          return false;
        }
        const slot = Math.max(0, (Math.floor(Number(card.dataset.slot) || 1) || 1) - 1);
        const path = clean(card.dataset.guidancePath || `answer-${slot}`);
        const depth = Math.max(1, Math.floor(Number(card.dataset.guidanceDepth) || 0) + 1);
        toggleQuestionGuidanceBranch(card, node, path, depth, options);
        card.setAttribute("aria-expanded", card.classList.contains("is-guidance-open") ? "true" : "false");
        return true;
      };

      const createQuestionGuidanceBranchCard = (node, path, depth, index, options = {}) => {
        const card = document.createElement("div");
        card.className = "ft-q-picture-answer-card is-guide is-live is-guidance-branch-card";
        card.dataset.guidancePath = path;
        card.dataset.guidanceDepth = String(depth);
        const answerDelay = `${index * 36}ms`;
        card.style.setProperty("--q-answer-delay", answerDelay);
        if (!options.noEnter) {
          prepareQuestionGuidanceEnter(card, answerDelay);
        }
        const kicker = document.createElement("span");
        kicker.className = "ft-q-picture-answer-kicker";
        kicker.textContent = `Info ${String(index + 1).padStart(2, "0")}`;
        const label = document.createElement("span");
        label.className = "ft-q-picture-answer-label";
        const title = clean(node && node.title) || "Info card";
        const body = preserveQuestionText(node && node.body);
        label.textContent = body ? `${title}\n${body}` : title;
        card.append(kicker, label);
          if (questionGuidanceNodeHasBranch(node)) {
            card.classList.add("has-guidance-children");
            appendQuestionGuidanceChildBadge(card);
            card.tabIndex = 0;
            wireQuestionGuidanceCard(card);
          }
        return card;
      };

      const questionGuidancePromptNodeForPath = (path) => questionGuidanceBranchNodes.find((node) => (
        node
        && node.classList
        && node.classList.contains("ft-q-guidance-branch-main")
        && clean(node.dataset.guidanceOwner) === clean(path)
      )) || null;

      const setQuestionGuidancePromptFeedback = (path, message = "", tone = "") => {
        let prompt = questionGuidancePromptNodeForPath(path);
        if (!prompt && questionPictureAnswerLayer) {
          const targetPath = clean(path);
          prompt = Array.from(questionPictureAnswerLayer.querySelectorAll(".ft-q-mobile-guidance-page .ft-q-guidance-branch-main"))
            .find((node) => clean(node && node.dataset && node.dataset.guidanceOwner) === targetPath) || null;
        }
        if (!prompt) {
          return;
        }
        let feedback = prompt.querySelector(".ft-q-guidance-branch-feedback");
        if (!feedback) {
          feedback = document.createElement("span");
          feedback.className = "ft-q-guidance-branch-feedback";
          prompt.appendChild(feedback);
        }
        feedback.textContent = clean(message);
        prompt.classList.toggle("is-guidance-question-ok", tone === "ok");
        prompt.classList.toggle("is-guidance-question-error", tone === "error");
      };

      const unlockQuestionGuidanceBranchChildren = (parentCard, node, path, depth, sourceCard = null, answerIndex = 0, answerValue = "") => {
        questionGuidanceUnlockedPaths.add(path);
        const safeIndex = Math.max(0, Math.floor(Number(answerIndex) || 0));
        questionGuidanceUnlockedAnswerIndex.set(path, safeIndex);
        const savedValue = preserveQuestionText(answerValue) || questionGuidanceAnswerOptionsForNode(node)[safeIndex] || "";
        if (savedValue) {
          questionGuidanceUnlockedAnswerValue.set(path, savedValue);
        }
        setQuestionGuidancePromptFeedback(path, "Unlocked", "ok");
        if (sourceCard && sourceCard.classList) {
          sourceCard.classList.remove("is-wrong");
          sourceCard.classList.add("is-correct");
        }
        window.setTimeout(() => {
          if (isQuestionMobileFlow()) {
            toggleQuestionGuidanceBranch(parentCard || sourceCard, node, path, depth, {
              forceOpen: true,
              preservePinned: false,
              pan: false,
              autoOpenFirstChild: true,
            });
            return;
          }
          if (!parentCard || !parentCard.isConnected) {
            return;
          }
          parentCard.classList.remove("is-guidance-open");
          clearQuestionGuidanceBranches(depth, { preservePinned: false });
          toggleQuestionGuidanceBranch(parentCard, node, path, depth, {
            forceOpen: true,
            preservePinned: false,
            pan: true,
            autoOpenFirstChild: true,
          });
        }, 260);
      };

      const checkQuestionGuidanceBranchAnswer = (parentCard, node, path, depth, value, sourceCard = null) => {
        const wanted = questionAnswerKey(value);
        const ok = questionGuidanceAcceptedAnswers(node).some((answer) => questionAnswerKey(answer) === wanted);
        if (!ok) {
          setQuestionGuidancePromptFeedback(path, "Try again", "error");
          if (sourceCard && sourceCard.classList) {
            sourceCard.classList.add("is-wrong");
            window.setTimeout(() => sourceCard.isConnected && sourceCard.classList.remove("is-wrong"), 760);
          }
          return false;
        }
        awardQuestionBookOnce(sourceCard || parentCard || questionPictureAnswerLayer || qQuestionCard || qRootCard, {
          kind: "branch",
          path,
        });
        unlockQuestionGuidanceBranchChildren(parentCard, node, path, depth, sourceCard, questionGuidanceAnswerIndexForValue(node, value), value);
        return true;
      };

      const createQuestionGuidanceChoiceCard = (parentCard, node, path, depth, option, index, options = {}) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "ft-q-picture-answer-card is-live is-guidance-branch-card is-guidance-question-answer";
        card.dataset.guidanceDepth = String(depth);
        card.dataset.guidanceOwner = path;
        card.dataset.answer = option;
        if (options.answered) {
          card.classList.add("is-guidance-answer-answered");
          if (options.correct) {
            card.classList.add("is-correct");
          }
        }
        if (options.childPath && questionGuidanceNodeHasBranch(options.childNode)) {
          card.dataset.guidancePath = options.childPath;
          questionGuidanceNodeMap.set(options.childPath, options.childNode);
          card.classList.add("has-guidance-children");
          appendQuestionGuidanceChildBadge(card);
          card.tabIndex = 0;
        }
        const answerDelay = `${index * 42}ms`;
        card.style.setProperty("--q-answer-delay", answerDelay);
        if (!options.noEnter) {
          prepareQuestionGuidanceEnter(card, answerDelay);
        }
        card.innerHTML = `<span class="ft-q-picture-answer-kicker">Branch ${String(index + 1).padStart(2, "0")}</span><span class="ft-q-picture-answer-label"></span>`;
        const label = card.querySelector(".ft-q-picture-answer-label");
        if (label) {
          label.textContent = option;
        }
        if (options.childPath && questionGuidanceNodeHasBranch(options.childNode)) {
          wireQuestionGuidanceCard(card);
        } else if (!options.answered) {
          card.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            checkQuestionGuidanceBranchAnswer(parentCard, node, path, depth, option, card);
          });
        }
        return card;
      };

      const createQuestionGuidanceInputCard = (parentCard, node, path, depth, options = {}) => {
        const card = document.createElement("div");
        card.className = "ft-q-picture-answer-card is-input is-live is-guidance-branch-card is-guidance-question-answer";
        card.dataset.guidanceDepth = String(depth);
        card.dataset.guidanceOwner = path;
        if (options.answered) {
          card.classList.add("is-guidance-input-answered", "is-correct");
        }
        if (options.childPath && questionGuidanceNodeHasBranch(options.childNode)) {
          card.dataset.guidancePath = options.childPath;
          questionGuidanceNodeMap.set(options.childPath, options.childNode);
          card.classList.add("has-guidance-children");
          appendQuestionGuidanceChildBadge(card);
          card.tabIndex = 0;
        }
        card.style.setProperty("--q-answer-delay", "0ms");
        if (!options.noEnter) {
          prepareQuestionGuidanceEnter(card, "0ms");
        }
        card.innerHTML = `
          <span class="ft-q-picture-answer-kicker">Branch input</span>
          <input class="ft-q-picture-answer-input" autocomplete="one-time-code" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Type answer">
          <span class="ft-q-picture-answer-actions">
            <button class="ft-q-picture-answer-action" type="button">Check</button>
          </span>
        `;
        const input = card.querySelector(".ft-q-picture-answer-input");
        const check = card.querySelector(".ft-q-picture-answer-action");
        if (options.answered) {
          if (input) {
            input.value = preserveQuestionText(options.answerValue) || "";
            input.readOnly = true;
          }
          if (check) {
            check.textContent = "Correct";
            check.setAttribute("aria-disabled", "true");
          }
          if (options.childPath && questionGuidanceNodeHasBranch(options.childNode)) {
            wireQuestionGuidanceCard(card);
          }
          return card;
        }
        const runCheck = () => checkQuestionGuidanceBranchAnswer(parentCard, node, path, depth, input ? input.value : "", card);
        if (check) {
          check.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            runCheck();
          });
        }
        if (input) {
          input.addEventListener("keydown", (event) => {
            if (event.key !== "Enter") {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            runCheck();
          });
        }
        return card;
      };

      const preferredQuestionGuidanceChildCard = (childCards, node, path) => {
        const cards = (Array.isArray(childCards) ? childCards : []).filter((card) => (
          card
          && card.isConnected
          && card.classList
          && card.classList.contains("has-guidance-children")
        ));
        if (!cards.length) {
          return null;
        }
        const restored = cards.find((card) => {
          const childPath = clean(card.dataset.guidancePath || "");
          return childPath && questionGuidanceUnlockedPaths.has(childPath);
        });
        if (restored) {
          return restored;
        }
        if (!questionGuidanceUnlockedPaths.has(path)) {
          return null;
        }
        const preferredIndex = Math.max(0, Math.floor(Number(questionGuidanceUnlockedAnswerIndex.get(path)) || 0));
        const preferred = cards.find((card) => {
          const childPath = clean(card.dataset.guidancePath || "");
          return childPath.endsWith(`.${preferredIndex}`);
        });
        if (preferred) {
          return preferred;
        }
        return clean(node && node.type).toLowerCase() === "choice" ? null : cards[0];
      };

      const positionQuestionGuidanceConnector = (connector, start, end) => {
        if (!connector) {
          return;
        }
        if (!connector.dataset.partsReady) {
          connector.innerHTML = `
            <i class="ft-q-guidance-branch-connector-segment is-start"></i>
            <i class="ft-q-guidance-branch-connector-segment is-vertical"></i>
            <i class="ft-q-guidance-branch-connector-segment is-end"></i>
            <b class="ft-q-guidance-branch-connector-node is-start"></b>
            <b class="ft-q-guidance-branch-connector-node is-elbow is-elbow-start"></b>
            <b class="ft-q-guidance-branch-connector-node is-elbow is-elbow-end"></b>
            <b class="ft-q-guidance-branch-connector-node is-end"></b>
          `;
          connector.dataset.partsReady = "1";
        }
        const startX = Number(start && start.x) || 0;
        const startY = Number(start && start.y) || 0;
        const endX = Number(end && end.x) || startX;
        const endY = Number(end && end.y) || startY;
        const dx = endX - startX;
        const elbowX = dx >= 0
          ? Math.min(endX - 24, Math.max(startX + 26, startX + Math.max(34, dx * 0.42)))
          : Math.max(endX + 24, Math.min(startX - 26, startX + Math.min(-34, dx * 0.42)));
        const left = Math.min(startX, endX, elbowX) - 8;
        const top = Math.min(startY, endY) - 8;
        const localStartX = startX - left;
        const localStartY = startY - top;
        const localEndX = endX - left;
        const localEndY = endY - top;
        const localElbowX = elbowX - left;
        const first = connector.querySelector(".is-start.ft-q-guidance-branch-connector-segment");
        const vertical = connector.querySelector(".is-vertical");
        const last = connector.querySelector(".is-end.ft-q-guidance-branch-connector-segment");
        const startNode = connector.querySelector(".ft-q-guidance-branch-connector-node.is-start");
        const elbowStartNode = connector.querySelector(".ft-q-guidance-branch-connector-node.is-elbow-start");
        const elbowEndNode = connector.querySelector(".ft-q-guidance-branch-connector-node.is-elbow-end");
        const endNode = connector.querySelector(".ft-q-guidance-branch-connector-node.is-end");
        connector.style.left = `${left}px`;
        connector.style.top = `${top}px`;
        connector.style.width = `${Math.max(1, Math.abs(Math.max(startX, endX, elbowX) - left) + 8)}px`;
        connector.style.height = `${Math.max(1, Math.abs(Math.max(startY, endY) - top) + 8)}px`;
        connector.style.transform = "none";
        if (first) {
          first.style.left = `${Math.min(localStartX, localElbowX) - 1}px`;
          first.style.top = `${localStartY - 1}px`;
          first.style.width = `${Math.max(16, Math.abs(localElbowX - localStartX) + 2)}px`;
        }
        if (vertical) {
          vertical.style.left = `${localElbowX - 1}px`;
          vertical.style.top = `${Math.min(localStartY, localEndY) - 1}px`;
          vertical.style.height = `${Math.max(3, Math.abs(localEndY - localStartY) + 2)}px`;
        }
        if (last) {
          last.style.left = `${Math.min(localElbowX, localEndX) - 1}px`;
          last.style.top = `${localEndY - 1}px`;
          last.style.width = `${Math.max(16, Math.abs(localEndX - localElbowX) + 2)}px`;
        }
        if (startNode) {
          startNode.style.left = `${localStartX}px`;
          startNode.style.top = `${localStartY}px`;
        }
        if (elbowStartNode) {
          elbowStartNode.style.left = `${localElbowX}px`;
          elbowStartNode.style.top = `${localStartY}px`;
        }
        if (elbowEndNode) {
          elbowEndNode.style.left = `${localElbowX}px`;
          elbowEndNode.style.top = `${localEndY}px`;
        }
        if (endNode) {
          endNode.style.left = `${localEndX}px`;
          endNode.style.top = `${localEndY}px`;
        }
      };

      function toggleQuestionGuidanceBranch(parentCard, node, path, depth = 1, options = {}) {
        const layer = questionPictureAnswerLayer || ensureQuestionPictureAnswerLayer();
        if (!layer || !node) {
          return;
        }
        if (isQuestionMobileFlow()) {
          openQuestionMobileGuidancePage(parentCard, node, path, depth, options);
          return;
        }
        if (!parentCard) {
          return;
        }
        cancelQuestionGuidanceClose(path);
        layer.classList.remove("is-preparing");
        layer.classList.add("is-live");
        const alreadyOpen = parentCard.classList.contains("is-guidance-open");
        if (alreadyOpen) {
          if (options.pin) {
            parentCard.classList.add("is-guidance-pinned");
            if (path) {
              questionGuidancePinnedPaths.add(path);
            }
          }
          if (options.forceOpen || options.pin) {
            parentCard.setAttribute("aria-expanded", "true");
            if (options.pan === true) {
              focusQuestionGuidanceCardOnClick(parentCard);
            }
            return;
          }
          clearQuestionGuidanceBranches(depth, { preservePinned: Boolean(options.preservePinned) });
          return;
        }
        clearQuestionGuidanceBranches(depth, { preservePinned: Boolean(options.preservePinned) });
        parentCard.classList.add("is-guidance-open");
        parentCard.classList.toggle("is-guidance-pinned", Boolean(options.pin));
        if (options.pin && path) {
          questionGuidancePinnedPaths.add(path);
        }
        parentCard.setAttribute("aria-expanded", "true");
        const quizBranch = questionGuidanceNodeIsQuestion(node);
        const quizType = clean(node && node.type).toLowerCase();
        const quizUnlocked = !quizBranch || questionGuidanceUnlockedPaths.has(path);
        const rawChildren = quizBranch ? [] : (Array.isArray(node.children) ? node.children : []);
        const mainText = quizBranch ? preserveQuestionText(node.question) : preserveQuestionText(node.main);
        const children = quizBranch
          ? []
          : (rawChildren.length
          ? rawChildren
          : (mainText ? [{ title: "Info detail", body: mainText, main: "" }] : []));
        if (!mainText && !children.length && !quizBranch) {
          return;
        }
        const layerRect = layer.getBoundingClientRect();
        const parentRect = questionGuidanceLayoutRectInLayer(parentCard, layer, layerRect);
        const parentRight = parentRect.right;
        const parentCenterY = parentRect.top + parentRect.height / 2;
        const cardWidth = 300;
        const enterNodes = [];
        const mainNode = document.createElement("div");
        mainNode.className = "ft-q-guidance-branch-main";
        mainNode.dataset.guidanceDepth = String(depth);
        mainNode.dataset.guidanceOwner = path;
        mainNode.classList.toggle("is-guidance-question-prompt", quizBranch);
        if (!options.noEnter) {
          prepareQuestionGuidanceEnter(mainNode, "0ms");
        }
        mainNode.textContent = quizBranch
          ? (mainText || "Branch question")
          : (rawChildren.length ? (mainText || "Branch link") : "Detail link");
        layer.appendChild(mainNode);
        questionGuidanceBranchNodes.push(mainNode);
        enterNodes.push(mainNode);
        wireQuestionGuidanceHoverNode(mainNode, path, depth, parentCard);
        const mainLeft = parentRight + 24;
        mainNode.style.left = `${mainLeft}px`;
        mainNode.style.top = `${Math.max(12, parentCenterY - 18)}px`;
        let childCards = [];
        if (quizBranch && quizUnlocked) {
          const answerIndex = Math.max(0, Math.floor(Number(questionGuidanceUnlockedAnswerIndex.get(path)) || 0));
          const answerValue = preserveQuestionText(questionGuidanceUnlockedAnswerValue.get(path))
            || questionGuidanceAnswerOptionsForNode(node)[answerIndex]
            || "";
          if (quizType === "input") {
            const childNode = questionGuidanceDisplayChildForAnswer(node, path, answerIndex);
            childCards = [createQuestionGuidanceInputCard(parentCard, node, path, depth, {
              ...options,
              answered: true,
              answerValue,
              childNode,
              childPath: childNode ? `${path}.${answerIndex}` : "",
            })];
          } else {
            const optionsList = questionGuidanceChoiceOptions(node);
            const correctKey = questionAnswerKey(questionGuidanceAnswerOptionsForNode(node)[answerIndex] || questionGuidanceAcceptedAnswers(node)[0] || "");
            childCards = optionsList.map((option, index) => {
              const childNode = questionGuidanceDisplayChildForAnswer(node, path, index);
              return createQuestionGuidanceChoiceCard(parentCard, node, path, depth, option, index, {
                ...options,
                answered: true,
                correct: questionAnswerKey(option) === correctKey,
                childNode,
                childPath: childNode ? `${path}.${index}` : "",
              });
            });
          }
        } else if (quizBranch) {
          childCards = quizType === "input"
            ? [createQuestionGuidanceInputCard(parentCard, node, path, depth, options)]
            : shuffleIndexes(questionGuidanceChoiceOptions(node).length).map((optionIndex, index) => (
              createQuestionGuidanceChoiceCard(parentCard, node, path, depth, questionGuidanceChoiceOptions(node)[optionIndex], index, options)
            ));
        } else {
          childCards = children.map((child, index) => {
            const childPath = `${path}.${index}`;
            questionGuidanceNodeMap.set(childPath, child);
            const card = createQuestionGuidanceBranchCard(child, childPath, depth, index, options);
            card.dataset.guidanceOwner = path;
            layer.appendChild(card);
            questionGuidanceBranchNodes.push(card);
            enterNodes.push(card);
            wireQuestionGuidanceHoverNode(card, path, depth, parentCard);
            card.style.width = `${cardWidth}px`;
            card.style.left = `${mainLeft + 96}px`;
            card.style.top = `${Math.max(12, parentCenterY + index * 86)}px`;
            return card;
          });
        }
        if (quizBranch) {
          childCards.forEach((card) => {
            card.dataset.guidanceOwner = path;
            layer.appendChild(card);
            questionGuidanceBranchNodes.push(card);
            enterNodes.push(card);
            wireQuestionGuidanceHoverNode(card, path, depth, parentCard);
            card.style.width = `${cardWidth}px`;
            card.style.left = `${mainLeft + 96}px`;
            card.style.top = `${Math.max(12, parentCenterY)}px`;
          });
        }
        window.requestAnimationFrame(() => {
          if (!parentCard.isConnected || !mainNode.isConnected) {
            return;
          }
          const freshLayerRect = layer.getBoundingClientRect();
          const freshParentRect = questionGuidanceLayoutRectInLayer(parentCard, layer, freshLayerRect);
          const freshParentRight = freshParentRect.right;
          const freshParentCenterY = freshParentRect.top + freshParentRect.height / 2;
          mainNode.style.left = `${freshParentRight + 24}px`;
          mainNode.style.top = `${Math.max(12, freshParentCenterY - 18)}px`;
          childCards.forEach((card, index) => {
            card.style.width = `${cardWidth}px`;
            card.style.left = `${freshParentRight + 24 + 96}px`;
            card.style.top = `${Math.max(12, freshParentCenterY + index * 86)}px`;
          });
          window.requestAnimationFrame(() => {
          if (!parentCard.isConnected || !mainNode.isConnected) {
            return;
          }
          const layerRect = layer.getBoundingClientRect();
          const parentRect = questionGuidanceLayoutRectInLayer(parentCard, layer, layerRect);
          const parentRight = parentRect.right;
          const parentCenterY = parentRect.top + parentRect.height / 2;
          const mainRect = questionGuidanceLayoutRectInLayer(mainNode, layer, layerRect);
          const mainLeft = mainRect.left;
          const mainRight = mainRect.right;
          const mainTop = mainRect.top;
          const mainHeight = Math.max(36, mainRect.height || 36);
          const mainCenterY = mainTop + mainHeight / 2;
          const leadConnector = document.createElement("div");
          leadConnector.className = "ft-q-guidance-branch-connector is-lead";
          leadConnector.dataset.guidanceDepth = String(depth);
          leadConnector.dataset.guidanceOwner = path;
          if (!options.noEnter) {
            prepareQuestionGuidanceEnter(leadConnector, "44ms");
          }
          layer.appendChild(leadConnector);
          questionGuidanceBranchNodes.push(leadConnector);
          enterNodes.push(leadConnector);
          wireQuestionGuidanceHoverNode(leadConnector, path, depth, parentCard);
          positionQuestionGuidanceConnector(leadConnector, {
            x: parentRight,
            y: parentCenterY,
          }, {
            x: mainLeft,
            y: mainCenterY,
          });
          const childLeft = mainRight + 54;
          const gap = 14;
          const heights = childCards.map((card) => Math.max(72, questionGuidanceLayoutRectInLayer(card, layer, layerRect).height || 72));
          const totalHeight = heights.reduce((sum, height) => sum + height, 0) + gap * Math.max(0, childCards.length - 1);
          const majorObstacleRects = [qRootCard, qPictureCard, questionRootInfoCard]
            .map((node) => {
              if (!node || !node.getBoundingClientRect || node.classList.contains("is-hidden")) {
                return null;
              }
              if (
                node !== qRootCard
                && !node.classList.contains("is-live")
                && !node.classList.contains("is-preparing")
              ) {
                return null;
              }
              const rect = questionGuidanceLayoutRectInLayer(node, layer, layerRect);
              if (!rect.width || !rect.height) {
                return null;
              }
              return inflateQuestionRouteRect(rect, node === qPictureCard ? 30 : 24);
            })
            .filter(Boolean);
          const occupiedRects = Array.from(layer.querySelectorAll(".ft-q-picture-answer-card.is-live"))
            .filter((card) => card !== parentCard && !childCards.includes(card))
            .map((card) => questionGuidanceLayoutRectInLayer(card, layer, layerRect))
            .concat(majorObstacleRects)
            .filter((rect) => rect.right > childLeft - 18 && rect.left < childLeft + cardWidth + 18);
          const stackOverlaps = (candidateTop) => {
            let scanTop = candidateTop;
            for (let index = 0; index < heights.length; index += 1) {
              const scanBottom = scanTop + heights[index];
              const hit = occupiedRects.find((rect) => scanBottom > rect.top - gap && scanTop < rect.bottom + gap);
              if (hit) {
                return hit.bottom + gap - scanTop;
              }
              scanTop = scanBottom + gap;
            }
            return 0;
          };
          let top = Math.max(12, parentCenterY - totalHeight / 2);
          for (let guard = 0; guard < 16; guard += 1) {
            const push = stackOverlaps(top);
            if (!push) {
              break;
            }
            top += push;
          }
          let requiredRight = mainRight + 96;
          let requiredBottom = mainTop + mainHeight + 180;
          childCards.forEach((card, index) => {
            card.style.width = `${cardWidth}px`;
            card.style.left = `${childLeft}px`;
            card.style.top = `${top}px`;
            const connector = document.createElement("div");
            connector.className = "ft-q-guidance-branch-connector";
            connector.dataset.guidanceDepth = String(depth);
            connector.dataset.guidanceOwner = path;
            if (!options.noEnter) {
              prepareQuestionGuidanceEnter(connector, `${index * 36}ms`);
            }
            layer.appendChild(connector);
            questionGuidanceBranchNodes.push(connector);
            enterNodes.push(connector);
            wireQuestionGuidanceHoverNode(connector, path, depth, parentCard);
            positionQuestionGuidanceConnector(connector, {
              x: mainRight,
              y: mainCenterY,
            }, {
              x: childLeft,
              y: top + heights[index] / 2,
            });
            requiredRight = Math.max(requiredRight, childLeft + cardWidth + 120);
            requiredBottom = Math.max(requiredBottom, top + heights[index] + 240);
            top += heights[index] + gap;
          });
          if (shellNode && requiredRight > (Number.parseFloat(shellNode.style.getPropertyValue("--q-layout-width")) || 0)) {
            shellNode.style.setProperty("--q-layout-width", `${Math.ceil(requiredRight)}px`);
          }
          if (shellNode && requiredBottom > (Number.parseFloat(shellNode.style.getPropertyValue("--q-layout-height")) || 0)) {
            shellNode.style.setProperty("--q-layout-height", `${Math.ceil(requiredBottom)}px`);
          }
          scheduleQuestionSideLayout();
          if (!options.noEnter) {
            startQuestionGuidanceEnter(enterNodes);
          }
          if ((options.autoOpenFirstChild || options.restoreUnlocked !== false) && !options.noEnter) {
            const nextCard = preferredQuestionGuidanceChildCard(childCards, node, path);
            if (nextCard) {
              window.setTimeout(() => {
                if (nextCard.isConnected && questionModeActive) {
                  openQuestionGuidanceCard(nextCard, {
                    forceOpen: true,
                    preservePinned: false,
                    pan: Boolean(options.autoOpenFirstChild && options.pan),
                    restoreUnlocked: true,
                  });
                }
              }, options.autoOpenFirstChild ? 420 : 120);
            }
          }
          window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
            if (questionModeActive && options.pan === true) {
              focusQuestionGuidanceCardOnClick(parentCard);
            }
          }));
          });
        });
      }

      const findQuestionGuidanceCardByPath = (path) => {
        const targetPath = clean(path);
        if (!targetPath || !shellNode) {
          return null;
        }
        return Array.from(shellNode.querySelectorAll(".has-guidance-children")).find((card) => (
          clean(card && card.dataset && card.dataset.guidancePath) === targetPath
        )) || null;
      };

      const relayoutQuestionGuidanceBranches = () => {
        if (isQuestionMobileFlow()) {
          return false;
        }
        if (!questionModeActive || !questionPictureAnswerLayer || !questionGuidanceBranchNodes.length) {
          return false;
        }
        const openScope = shellNode || questionPictureAnswerLayer;
        const openBranches = Array.from(openScope.querySelectorAll(".has-guidance-children.is-guidance-open"))
          .map((card) => {
            const path = clean(card && card.dataset && card.dataset.guidancePath);
            const node = questionGuidanceNodeForCard(card);
            const cardDepth = Math.max(0, Math.floor(Number(card && card.dataset && card.dataset.guidanceDepth) || 0));
            return {
              cardDepth,
              depth: Math.max(1, cardDepth + 1),
              node,
              path,
              pinned: Boolean(card && card.classList && card.classList.contains("is-guidance-pinned")),
            };
          })
          .filter((entry) => entry.path && questionGuidanceNodeHasBranch(entry.node))
          .sort((a, b) => a.cardDepth - b.cardDepth);
        if (!openBranches.length) {
          return false;
        }
        openBranches.forEach((entry) => {
          questionGuidanceNodeMap.set(entry.path, entry.node);
        });
        clearQuestionGuidanceBranches(1, { preservePinned: false });
        openBranches.forEach((entry) => {
          questionGuidanceNodeMap.set(entry.path, entry.node);
        });
        openBranches.forEach((entry) => {
          const card = findQuestionGuidanceCardByPath(entry.path);
          if (!card || !card.isConnected) {
            return;
          }
          card.classList.remove("is-guidance-open", "is-guidance-pinned");
          toggleQuestionGuidanceBranch(card, entry.node, entry.path, entry.depth, {
            noEnter: true,
            preservePinned: false,
          });
        });
        return true;
      };

      const scheduleQuestionGuidanceRelayout = (delay = 80) => {
        if (isQuestionMobileFlow()) {
          return;
        }
        if (!questionPictureAnswerLayer || !questionGuidanceBranchNodes.length) {
          return;
        }
        if (questionGuidanceRelayoutFrame) {
          window.clearTimeout(questionGuidanceRelayoutFrame);
        }
        questionGuidanceRelayoutFrame = window.setTimeout(() => {
          questionGuidanceRelayoutFrame = 0;
          window.requestAnimationFrame(() => {
            positionQuestionSideCards({ force: true });
            relayoutQuestionGuidanceBranches();
          });
        }, Math.max(0, Number(delay) || 0));
      };

      const settleQuestionGuidanceLayout = (...delays) => {
        const steps = delays.length
          ? delays
          : (isQuestionMobilePerformanceSurface() ? [0, 220, 620] : [0, 90, 220, 520, 900]);
        const token = questionGuidanceSettleToken + 1;
        questionGuidanceSettleToken = token;
        steps.forEach((delay) => {
          window.setTimeout(() => {
            if (token !== questionGuidanceSettleToken || !questionModeActive) {
              return;
            }
            scheduleQuestionResizeLayout();
            scheduleQuestionGuidanceRelayout(0);
          }, Math.max(0, Number(delay) || 0));
        });
      };

      function questionRootInfoPromptNode(selector) {
        return questionRootInfoCard ? questionRootInfoCard.querySelector(selector) : null;
      }

      function clearQuestionPicturePromptFeedbackLayout() {
        const feedback = questionRootInfoPromptNode(".ft-q-root-info-feedback");
        if (questionRootInfoCard) {
          questionRootInfoCard.classList.remove("has-floating-feedback");
        }
        if (!feedback) {
          return;
        }
        feedback.classList.remove("is-floating");
        ["left", "top", "right", "bottom", "width", "max-width", "--q-picture-feedback-width"].forEach((name) => {
          feedback.style.removeProperty(name);
        });
      }

      function questionPicturePromptFeedbackVisible(feedback) {
        return Boolean(
          feedback
          && questionRootInfoCard
          && questionRootInfoCard.classList.contains("is-picture-region-question")
          && clean(feedback.textContent || "").length
        );
      }

      function positionQuestionPicturePromptFeedback(cards = [], shellRect = null, promptRect = null) {
        const feedback = questionRootInfoPromptNode(".ft-q-root-info-feedback");
        if (
          !questionPicturePromptFeedbackVisible(feedback)
          || isQuestionMobileFlow()
          || !shellNode
          || !questionRootInfoCard
          || !Array.isArray(cards)
          || !cards.length
        ) {
          clearQuestionPicturePromptFeedbackLayout();
          return;
        }
        const safeShellRect = shellRect || shellNode.getBoundingClientRect();
        const safePromptRect = promptRect || questionRootInfoCard.getBoundingClientRect();
        if (!safeShellRect.width || !safePromptRect.width) {
          clearQuestionPicturePromptFeedbackLayout();
          return;
        }
        const answerBounds = questionUnionClientRects(
          cards
            .map((card) => card && card.getBoundingClientRect ? card.getBoundingClientRect() : null)
            .filter((rect) => rect && rect.width > 0 && rect.height > 0),
        );
        if (!answerBounds) {
          clearQuestionPicturePromptFeedbackLayout();
          return;
        }
        const stageRect = stageNode && stageNode.getBoundingClientRect
          ? stageNode.getBoundingClientRect()
          : { left: 0, top: 0, right: window.innerWidth || safeShellRect.right, bottom: window.innerHeight || safeShellRect.bottom };
        const viewportLeft = questionUnscaleLayoutValue(stageRect.left - safeShellRect.left) + 18;
        const viewportRight = questionUnscaleLayoutValue(stageRect.right - safeShellRect.left) - 18;
        const viewportTop = questionUnscaleLayoutValue(stageRect.top - safeShellRect.top) + 18;
        const viewportBottom = questionUnscaleLayoutValue(stageRect.bottom - safeShellRect.top) - 18;
        const promptLeft = questionUnscaleLayoutValue(safePromptRect.left - safeShellRect.left);
        const promptTop = questionUnscaleLayoutValue(safePromptRect.top - safeShellRect.top);
        const answerLeft = questionUnscaleLayoutValue(answerBounds.left - safeShellRect.left);
        const answerRight = questionUnscaleLayoutValue(answerBounds.right - safeShellRect.left);
        const answerTop = questionUnscaleLayoutValue(answerBounds.top - safeShellRect.top);
        const answerBottom = questionUnscaleLayoutValue(answerBounds.bottom - safeShellRect.top);
        const gap = 16;
        const availableRight = Math.max(0, viewportRight - answerRight - gap);
        const preferredWidth = Math.max(190, Math.min(280, availableRight || 240));
        const width = Math.max(170, Math.min(preferredWidth, Math.max(170, viewportRight - viewportLeft)));
        let left = answerRight + gap;
        if (left + width > viewportRight) {
          left = Math.max(answerLeft + gap, viewportRight - width);
        }
        left = Math.max(viewportLeft, Math.min(left, viewportRight - width));
        feedback.classList.add("is-floating");
        questionRootInfoCard.classList.add("has-floating-feedback");
        feedback.style.setProperty("--q-picture-feedback-width", `${Math.round(width)}px`);
        feedback.style.width = `${Math.round(width)}px`;
        feedback.style.left = `${Math.round(left - promptLeft)}px`;
        feedback.style.right = "auto";
        feedback.style.bottom = "auto";
        const feedbackHeight = Math.max(34, questionUnscaleLayoutValue(feedback.getBoundingClientRect().height || 34));
        const answerCenterY = answerTop + (answerBottom - answerTop) / 2;
        const top = Math.max(
          viewportTop,
          Math.min(answerCenterY - feedbackHeight / 2, viewportBottom - feedbackHeight),
        );
        feedback.style.top = `${Math.round(top - promptTop)}px`;
      }

      function resetQuestionPicturePromptControls() {
        questionPicturePromptFeedbackToken += 1;
        if (questionPicturePromptFeedbackTimer) {
          window.clearTimeout(questionPicturePromptFeedbackTimer);
          questionPicturePromptFeedbackTimer = 0;
        }
        const audioButton = questionRootInfoPromptNode("[data-root-info-audio]");
        const nextButton = questionRootInfoPromptNode("[data-root-info-next]");
        const feedback = questionRootInfoPromptNode(".ft-q-root-info-feedback");
        if (audioButton) {
          audioButton.classList.add("ft-q-show-answer-hidden");
        }
        if (nextButton) {
          nextButton.disabled = true;
        }
        if (feedback) {
          feedback.textContent = "";
          feedback.classList.remove("is-ok", "is-error");
        }
        clearQuestionPicturePromptFeedbackLayout();
        questionPictureAnswerFeedbackNode = null;
      }

      function setQuestionPicturePromptFeedback(message = "", tone = "") {
        const feedback = questionRootInfoPromptNode(".ft-q-root-info-feedback");
        if (!feedback) {
          return;
        }
        questionPicturePromptFeedbackToken += 1;
        if (questionPicturePromptFeedbackTimer) {
          window.clearTimeout(questionPicturePromptFeedbackTimer);
          questionPicturePromptFeedbackTimer = 0;
        }
        const text = clean(message);
        const routedToRoot = setQuestionRootChoiceSignalStatus(text, tone);
        if (routedToRoot) {
          feedback.textContent = "";
          feedback.classList.remove("is-ok", "is-error");
          questionPictureAnswerFeedbackNode = null;
          clearQuestionPicturePromptFeedbackLayout();
          window.requestAnimationFrame(positionQuestionPictureAnswerCards);
          return;
        }
        feedback.classList.toggle("is-ok", tone === "ok");
        feedback.classList.toggle("is-error", tone === "error");
        questionPictureAnswerFeedbackNode = feedback;
        if (!text) {
          feedback.textContent = "";
          clearQuestionPicturePromptFeedbackLayout();
          return;
        }
        const token = questionPicturePromptFeedbackToken;
        const color = tone === "ok" ? "#6cf0a4" : (tone === "error" ? "#ff6f91" : "#46f0d7");
        let index = 0;
        const tick = () => {
          if (token !== questionPicturePromptFeedbackToken || !feedback.isConnected) {
            return;
          }
          index = Math.min(text.length, index + Math.max(1, Math.ceil(text.length / 34)));
          const visible = text.slice(0, index);
          const activeIndex = Math.max(0, visible.length - 1);
          feedback.innerHTML = renderQuestionRootTrailSegment(visible, 0, activeIndex, color);
          if (index < text.length) {
            questionPicturePromptFeedbackTimer = window.setTimeout(tick, 18 + Math.random() * 18);
          } else {
            questionPicturePromptFeedbackTimer = window.setTimeout(() => {
              if (token === questionPicturePromptFeedbackToken && feedback.isConnected) {
                feedback.textContent = text;
                window.requestAnimationFrame(positionQuestionPictureAnswerCards);
              }
              questionPicturePromptFeedbackTimer = 0;
            }, 360);
          }
        };
        window.requestAnimationFrame(positionQuestionPictureAnswerCards);
        tick();
      }

      function setQuestionPicturePromptNextEnabled(enabled) {
        const nextButton = questionRootInfoPromptNode("[data-root-info-next]");
        if (nextButton) {
          nextButton.disabled = !enabled;
        }
        updateQuestionProgressLabel();
        syncQuestionMobilePicturePager();
      }

      function configureQuestionPicturePromptControls(question, state = {}) {
        if (!questionRootInfoCard || !questionRootInfoCard.classList.contains("is-question")) {
          return;
        }
        const audioButton = questionRootInfoPromptNode("[data-root-info-audio]");
        const promptClip = questionCardAudioClip(question && question.audio);
        if (audioButton) {
          audioButton.classList.toggle("ft-q-show-answer-hidden", !promptClip);
        }
        setQuestionPicturePromptNextEnabled(Boolean(state.nextEnabled));
        setQuestionPicturePromptFeedback(state.feedback || "", state.feedbackTone || "");
      }

      const setQuestionPictureAnswerFeedback = (message = "", tone = "") => {
        setQuestionPicturePromptFeedback(message, tone);
      };

      const setQuestionPictureAnswerControls = (locked) => {
        if (!questionPictureAnswerLayer) {
          return;
        }
        questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card").forEach((node) => {
          if (node instanceof HTMLButtonElement) {
            node.disabled = Boolean(locked) && !node.classList.contains("has-guidance-children");
          }
        });
        const input = questionPictureAnswerLayer.querySelector(".ft-q-picture-answer-input");
        if (input) {
          input.disabled = Boolean(locked);
        }
      };

      const setQuestionPictureAnswerNextEnabled = (enabled) => {
        setQuestionPicturePromptNextEnabled(enabled);
        if (questionPictureAnswerLayer) {
          questionPictureAnswerLayer.querySelectorAll("[data-picture-answer-next]").forEach((button) => {
            button.disabled = !enabled;
          });
        }
        updateQuestionProgressLabel();
      };

      // Added 2026-07-07: hide Space_Q linking answers until their desktop layout is stable.
      const setQuestionPictureAnswerLayoutPending = (pending) => {
        if (questionPictureAnswerLayer) {
          questionPictureAnswerLayer.classList.toggle("is-layout-pending", Boolean(pending));
        }
        if (questionRootInfoCard) {
          questionRootInfoCard.classList.toggle("is-picture-answer-layout-pending", Boolean(pending));
        }
      };

      const renderQuestionPictureAnswerCards = (question, state = {}) => {
        const layer = ensureQuestionPictureAnswerLayer();
        if (!layer || !question) {
          return [];
        }
        const prepareOnly = Boolean(state.prepareOnly);
        const cardStateClass = prepareOnly ? "is-preparing" : "is-live";
        const previousOrder = state.preserveOrder
          ? Array.from(layer.querySelectorAll("[data-answer]"))
            .map((card) => clean(card.dataset ? card.dataset.answer : ""))
            .filter(Boolean)
          : [];
        layer.innerHTML = "";
        resetQuestionMobilePicturePager();
        questionGuidanceBranchNodes = [];
        questionGuidanceNodeMap.clear();
        questionGuidanceUnlockedPaths.clear();
        questionGuidanceUnlockedAnswerIndex.clear();
        questionGuidanceUnlockedAnswerValue.clear();
        questionGuidancePinnedPaths.clear();
        questionPictureAnswerConnectors = [];
        questionPictureAnswerFeedbackNode = null;
        const guide = isQuestionGuideItem(question) || Boolean(state.guide);
        const typed = isQuestionTypedItem(question);
        const answerCards = [];
        const selectedKey = questionAnswerKey(state.selectedValue || "");
        configureQuestionPicturePromptControls(question, state);
        if (typed) {
          const card = document.createElement("div");
          card.className = `ft-q-picture-answer-card is-input ${cardStateClass}`;
          card.style.setProperty("--q-answer-delay", "0ms");
          card.innerHTML = `
            <span class="ft-q-picture-answer-kicker">Written Answer</span>
            <input class="ft-q-picture-answer-input" autocomplete="one-time-code" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Nhập đáp án">
            <span class="ft-q-picture-answer-actions">
              <button class="ft-q-picture-answer-action" type="button" data-picture-answer-check>Check</button>
              <button class="ft-q-picture-answer-action is-secondary" type="button" data-picture-answer-show>Hiện đáp án</button>
            </span>
          `;
          const input = card.querySelector(".ft-q-picture-answer-input");
          const check = card.querySelector("[data-picture-answer-check]");
          const show = card.querySelector("[data-picture-answer-show]");
          if (input && clean(state.inputValue)) {
            input.value = clean(state.inputValue);
          }
          if (check) {
            check.addEventListener("click", () => checkQuestionAnswer(input ? input.value : ""));
          }
          if (show) {
            show.addEventListener("click", showQuestionAnswer);
          }
          if (input) {
            input.addEventListener("keydown", (event) => {
              if (event.key === "Enter") {
                if (handleQuestionEnterNext(event)) {
                  return;
                }
                event.preventDefault();
                checkQuestionAnswer(input.value);
              }
            });
          }
          const guideNode = questionGuidanceTreeEntryForOption(question, question.answer, 0);
          if (state.locked && state.selectedOk && questionGuidanceNodeHasBranch(guideNode)) {
            const guidePath = "input-0";
            questionGuidanceNodeMap.set(guidePath, guideNode);
            card.dataset.answer = question.answer || "";
            card.dataset.slot = "01";
            card.dataset.guidancePath = guidePath;
            card.dataset.guidanceDepth = "0";
            card.classList.add("has-guidance-children");
            appendQuestionGuidanceChildBadge(card);
            card.tabIndex = 0;
            wireQuestionGuidanceCard(card);
          }
          layer.appendChild(card);
          answerCards.push(card);
          if (state.locked) {
            setTimeout(() => {
              if (input) input.disabled = true;
              if (check) check.disabled = true;
            }, 0);
          }
        } else {
          const options = [question.answer, ...(Array.isArray(question.wrong) ? question.wrong : [])]
            .map(clean)
            .filter(Boolean);
          const deduped = [];
          const seen = new Set();
          options.forEach((option) => {
            const key = questionAnswerKey(option);
            if (!key || seen.has(key)) {
              return;
            }
            seen.add(key);
            deduped.push(option);
          });
          const ordered = guide
            ? deduped
            : (previousOrder.length
              ? orderQuestionOptionsByPreviousRender(deduped, previousOrder)
              : shuffleIndexes(deduped.length).map((index) => deduped[index]));
          ordered.forEach((option, index) => {
            const button = document.createElement(guide ? "div" : "button");
            button.className = `ft-q-picture-answer-card ${guide ? "is-guide " : ""}${cardStateClass}`;
            if (!guide) {
              button.type = "button";
            }
            button.dataset.answer = option;
            button.dataset.slot = String(index + 1).padStart(2, "0");
            button.style.setProperty("--q-answer-delay", `${index * 90}ms`);
            const guideNode = questionGuidanceTreeEntryForOption(question, option, index);
            const hasExtraBranch = questionGuidanceNodeHasBranch(guideNode);
            const extraBranchReady = hasExtraBranch && (guide || (state.locked && state.selectedOk));
            button.innerHTML = `<span class="ft-q-picture-answer-kicker">${guide ? "Data" : "Answer"} ${String(index + 1).padStart(2, "0")}</span><span class="ft-q-picture-answer-label"></span>`;
            const label = button.querySelector(".ft-q-picture-answer-label");
            if (label) {
              label.textContent = option;
            }
            const key = questionAnswerKey(option);
            if (selectedKey && key === selectedKey) {
              button.classList.add(state.selectedOk ? "is-correct" : "is-wrong");
            }
            if (state.locked && !extraBranchReady && button instanceof HTMLButtonElement) {
              button.disabled = true;
            }
            if (!guide && !extraBranchReady) {
              button.addEventListener("click", () => checkQuestionAnswer(option, button));
            }
            if (extraBranchReady) {
              const guidePath = `answer-${index}`;
              questionGuidanceNodeMap.set(guidePath, guideNode);
              button.dataset.guidancePath = guidePath;
              button.dataset.guidanceDepth = "0";
              button.classList.add("has-guidance-children");
              appendQuestionGuidanceChildBadge(button);
              button.tabIndex = 0;
              if (!guide && button instanceof HTMLButtonElement) {
                button.disabled = false;
                button.type = "button";
              }
              wireQuestionGuidanceCard(button);
            }
            layer.appendChild(button);
            answerCards.push(button);
          });
        }
        answerCards.forEach((card, index) => {
          const connector = document.createElement("div");
          connector.className = "ft-q-picture-answer-connector";
          const delay = card && card.style ? (card.style.getPropertyValue("--q-answer-delay") || `${index * 90}ms`) : `${index * 90}ms`;
          connector.style.setProperty("--q-answer-delay", delay);
          layer.appendChild(connector);
          questionPictureAnswerConnectors.push(connector);
        });
        layer.classList.toggle("is-preparing", prepareOnly);
        layer.classList.toggle("is-live", !prepareOnly);
        setQuestionPictureAnswerLayoutPending(true);
        questionPictureAnswerActive = true;
        questionPictureAnswerPreparedItem = prepareOnly ? question : null;
        questionPictureAnswerOptionValues = typed ? [question.answer] : Array.from(layer.querySelectorAll(".ft-q-picture-answer-card[data-answer]")).map((button) => clean(button.dataset.answer));
        syncQuestionMobilePicturePager();
        window.requestAnimationFrame(() => {
          positionQuestionPictureAnswerCards();
          const input = layer.querySelector(".ft-q-picture-answer-input");
          if (!prepareOnly && typed && input && !state.locked && !state.selectedOk && state.autoFocusInput !== false) {
            focusQuestionTypingInput(input, {
              item: question,
              pictureInput: true,
              delays: isQuestionMobileFlow() ? [0, 70, 180, 360] : [0, 80],
            });
          }
        });
        return questionPictureAnswerOptionValues.slice();
      };

      const activatePreparedQuestionPictureAnswerCards = (question, state = {}) => {
        if (
          !questionPictureAnswerLayer
          || questionPictureAnswerPreparedItem !== question
          || !questionPictureAnswerLayer.classList.contains("is-preparing")
        ) {
          return renderQuestionPictureAnswerCards(question, state);
        }
        questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card.is-preparing").forEach((card) => {
          card.classList.remove("is-preparing");
          card.classList.add("is-live");
        });
        questionPictureAnswerLayer.classList.remove("is-preparing");
        questionPictureAnswerLayer.classList.add("is-live");
        setQuestionPictureAnswerLayoutPending(true);
        questionPictureAnswerActive = true;
        questionPictureAnswerPreparedItem = null;
        configureQuestionPicturePromptControls(question, state);
        syncQuestionMobilePicturePager();
        window.requestAnimationFrame(() => {
          positionQuestionPictureAnswerCards();
          const typed = isQuestionTypedItem(question);
          const input = questionPictureAnswerLayer.querySelector(".ft-q-picture-answer-input");
          if (typed && input && !state.locked && !state.selectedOk && state.autoFocusInput !== false) {
            focusQuestionTypingInput(input, {
              item: question,
              pictureInput: true,
              delays: isQuestionMobileFlow() ? [0, 70, 180, 360] : [0, 80],
            });
          }
        });
        return questionPictureAnswerOptionValues.slice();
      };

      const ensureQuestionPictureAnswerElbowConnectorParts = (connector) => {
        if (!connector) {
          return { segments: [], nodes: [] };
        }
        if (connector.dataset.splitElbowParts !== "1") {
          connector.dataset.splitElbowParts = "1";
          connector.innerHTML = [
            '<span class="ft-q-picture-answer-connector-segment is-horizontal-out"></span>',
            '<span class="ft-q-picture-answer-connector-segment is-vertical-drop"></span>',
            '<span class="ft-q-picture-answer-connector-segment is-horizontal-in"></span>',
            '<span class="ft-q-picture-answer-connector-node is-source"></span>',
            '<span class="ft-q-picture-answer-connector-node is-corner"></span>',
            '<span class="ft-q-picture-answer-connector-node is-target"></span>',
          ].join("");
        }
        return {
          segments: Array.from(connector.querySelectorAll(".ft-q-picture-answer-connector-segment")),
          nodes: Array.from(connector.querySelectorAll(".ft-q-picture-answer-connector-node")),
        };
      };

      const clearQuestionPictureAnswerElbowConnector = (connector) => {
        if (!connector || connector.dataset.splitElbowParts !== "1") {
          return;
        }
        connector.dataset.splitElbowParts = "0";
        connector.innerHTML = "";
      };

      const positionQuestionPictureAnswerElbowConnector = (connector, start, branchX, end) => {
        if (!connector || !start || !end) {
          return;
        }
        const safeBranchX = Number(branchX) || start.x;
        connector.style.left = "0px";
        connector.style.top = "0px";
        connector.style.width = "0px";
        connector.style.height = "0px";
        connector.style.transform = "none";
        connector.style.transformOrigin = "left center";
        connector.classList.add("is-split-elbow");
        const parts = ensureQuestionPictureAnswerElbowConnectorParts(connector);
        const path = [
          start,
          { x: safeBranchX, y: start.y },
          { x: safeBranchX, y: end.y },
          end,
        ];
        parts.segments.forEach((segment, index) => {
          positionQuestionRootInfoSegment(segment, path[index], path[index + 1]);
        });
        const nodePoints = [path[0], path[1], path[3]];
        parts.nodes.forEach((node, index) => {
          const point = nodePoints[index] || path[0];
          node.style.left = `${point.x}px`;
          node.style.top = `${point.y}px`;
        });
      };

      const positionQuestionPictureAnswerCards = (attempt = 0) => {
        if (
          !questionPictureAnswerActive
          || !questionPictureAnswerLayer
          || !shellNode
          || !questionRootInfoCard
          || !(questionRootInfoCard.classList.contains("is-live") || questionRootInfoCard.classList.contains("is-preparing"))
        ) {
          return;
        }
        const retryLayout = () => {
          if (attempt >= 8) {
            return;
          }
          window.requestAnimationFrame(() => positionQuestionPictureAnswerCards(attempt + 1));
        };
        const shellRect = shellNode.getBoundingClientRect();
        const promptRect = questionRootInfoCard.getBoundingClientRect();
        const cards = Array.from(questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card:not(.is-guidance-branch-card).is-live, .ft-q-picture-answer-card:not(.is-guidance-branch-card).is-preparing"));
        if (!cards.length || !shellRect.width || !promptRect.width) {
          setQuestionPictureAnswerLayoutPending(true);
          retryLayout();
          return;
        }
        if (isQuestionMobileFlow()) {
          clearQuestionPicturePromptFeedbackLayout();
          cards.forEach((card) => {
            ["left", "top", "right", "bottom", "width", "height", "transform"].forEach((name) => card.style.removeProperty(name));
          });
          questionPictureAnswerConnectors.forEach((connector) => {
            connector.classList.remove("is-live", "is-split-elbow");
            clearQuestionPictureAnswerElbowConnector(connector);
            ["left", "top", "width", "height", "transform", "transform-origin"].forEach((name) => connector.style.removeProperty(name));
          });
          setQuestionPictureAnswerLayoutPending(false);
          return;
        }
        const shellWidth = questionUnscaleLayoutValue(shellRect.width);
        const promptWidth = questionUnscaleLayoutValue(promptRect.width);
        const promptHeight = questionUnscaleLayoutValue(promptRect.height);
        const promptLeft = questionUnscaleLayoutValue(promptRect.left - shellRect.left);
        const promptTop = questionUnscaleLayoutValue(promptRect.top - shellRect.top);
        const promptRight = promptLeft + promptWidth;
        const isInput = cards[0].classList.contains("is-input");
        const rail = 54;
        const requestAnswerLayoutWidth = (requiredWidth) => {
          const nextWidth = Math.ceil(Number(requiredWidth) || 0);
          const currentWidth = Number.parseFloat(shellNode.style.getPropertyValue("--q-layout-width")) || 0;
          if (!nextWidth || Math.abs(currentWidth - nextWidth) < 1) {
            return false;
          }
          shellNode.style.setProperty("--q-layout-width", `${nextWidth}px`);
          setQuestionPictureAnswerLayoutPending(true);
          window.requestAnimationFrame(() => positionQuestionPictureAnswerCards(attempt + 1));
          return true;
        };
        const answerAvoidRects = [qRootCard, qPictureCard, qAudioCard, qQuestionCard]
          .map((node) => {
            if (!node || !node.getBoundingClientRect || node.classList.contains("is-hidden")) {
              return null;
            }
            if (node !== qRootCard && !node.classList.contains("is-live") && !node.classList.contains("is-preparing")) {
              return null;
            }
            const rect = node.getBoundingClientRect();
            if (!rect.width || !rect.height) {
              return null;
            }
            return inflateQuestionRouteRect({
              left: questionUnscaleLayoutValue(rect.left - shellRect.left),
              top: questionUnscaleLayoutValue(rect.top - shellRect.top),
              right: questionUnscaleLayoutValue(rect.right - shellRect.left),
              bottom: questionUnscaleLayoutValue(rect.bottom - shellRect.top),
            }, node === qRootCard ? 24 : 22);
          })
          .filter(Boolean);
        const pushAnswerStackClear = (left, width, top, heights, gapValue = 14) => {
          let nextTop = Math.max(16, Math.round(top));
          const stackHeight = heights.reduce((sum, height) => sum + height, 0) + gapValue * Math.max(0, heights.length - 1);
          const right = left + width;
          for (let guard = 0; guard < 12; guard += 1) {
            const hit = answerAvoidRects.find((rect) => (
              right > rect.left
              && left < rect.right
              && nextTop + stackHeight > rect.top
              && nextTop < rect.bottom
            ));
            if (!hit) {
              break;
            }
            nextTop = Math.max(nextTop + 1, Math.ceil(hit.bottom + gapValue));
          }
          return nextTop;
        };
        const ensureAnswerLayoutHeight = () => {
          const answerBottom = cards.reduce((bottom, card) => {
            const rect = card.getBoundingClientRect();
            return Math.max(bottom, questionUnscaleLayoutValue(rect.bottom - shellRect.top));
          }, 0);
          if (!answerBottom) {
            return;
          }
          const reserve = Math.max(220, Math.min(560, (stageNode ? questionUnscaleLayoutValue(stageNode.clientHeight) : 720) * 0.46));
          const requiredHeight = Math.ceil(answerBottom + reserve);
          const currentHeight = Number.parseFloat(shellNode.style.getPropertyValue("--q-layout-height")) || 0;
          if (requiredHeight > currentHeight + 2) {
            shellNode.style.setProperty("--q-layout-height", `${requiredHeight}px`);
          }
        };
        const splitMetrics = questionSplitDesktopLayoutActive() ? questionSplitLayoutMetrics() : null;
        if (splitMetrics) {
          const gap = 14;
          const rightColumnRight = splitMetrics.rightLeft + splitMetrics.rightWidth;
          const feedback = questionRootInfoPromptNode(".ft-q-root-info-feedback");
          const feedbackVisible = questionPicturePromptFeedbackVisible(feedback);
          const feedbackGap = feedbackVisible ? 16 : 0;
          const feedbackReserve = feedbackVisible
            ? Math.max(190, Math.min(280, splitMetrics.rightWidth * 0.38))
            : 0;
          const maxCardWidth = Math.max(220, splitMetrics.rightWidth - 74 - feedbackReserve - feedbackGap);
          const cardWidth = isInput
            ? Math.min(460, Math.max(320, Math.min(maxCardWidth, promptWidth - 36)))
            : Math.min(340, Math.max(230, Math.min(maxCardWidth, promptWidth * 0.72)));
          cards.forEach((card) => {
            card.style.width = `${cardWidth}px`;
          });
          const heights = cards.map((card) => Math.max(isInput ? 104 : 74, questionUnscaleLayoutValue(card.getBoundingClientRect().height || (isInput ? 104 : 74))));
          let left = Math.max(promptLeft + 48, splitMetrics.rightLeft + 40);
          left = Math.min(left, rightColumnRight - cardWidth - feedbackReserve - feedbackGap - 14);
          left = Math.max(splitMetrics.rightLeft + 18, left);
          let top = Math.round(promptTop + promptHeight + 18);
          cards.forEach((card, index) => {
            card.style.left = `${Math.round(left)}px`;
            card.style.top = `${Math.round(top)}px`;
            top += heights[index] + gap;
          });
          ensureAnswerLayoutHeight();
          const promptAfter = questionRootInfoCard.getBoundingClientRect();
          const promptAfterLeft = questionUnscaleLayoutValue(promptAfter.left - shellRect.left);
          const promptAfterTop = questionUnscaleLayoutValue(promptAfter.top - shellRect.top);
          const promptAfterHeight = questionUnscaleLayoutValue(promptAfter.height);
          const trunkX = Math.max(splitMetrics.rightLeft - Math.max(28, Math.min(44, splitMetrics.gap * 0.7)), promptAfterLeft - 42);
          cards.forEach((card, index) => {
            const connector = questionPictureAnswerConnectors[index];
            if (!connector) {
              return;
            }
            const rect = card.getBoundingClientRect();
            const start = {
              x: promptAfterLeft,
              y: promptAfterTop + Math.min(promptAfterHeight * 0.62, Math.max(38, promptAfterHeight - 24)) + Math.min(index, 5) * 4,
            };
            const end = {
              x: questionUnscaleLayoutValue(rect.left - shellRect.left),
              y: questionUnscaleLayoutValue(rect.top - shellRect.top + rect.height / 2),
            };
            connector.classList.add("is-live");
            positionQuestionPictureAnswerElbowConnector(connector, start, trunkX, end);
          });
          positionQuestionPicturePromptFeedback(cards, shellRect, promptAfter);
          setQuestionPictureAnswerLayoutPending(false);
          return;
        }
        if (isInput) {
          const card = cards[0];
          const width = Math.min(460, Math.max(340, promptWidth * 1.08));
          card.style.width = `${width}px`;
          const cardHeight = Math.max(96, questionUnscaleLayoutValue(card.getBoundingClientRect().height || 96));
          const left = promptRight + rail;
          const top = pushAnswerStackClear(left, width, promptTop + Math.max(0, (promptHeight - cardHeight) / 2), [cardHeight], 18);
          const requiredWidth = left + width + 96;
          if (requiredWidth > shellWidth + 2 && requestAnswerLayoutWidth(requiredWidth)) {
            return;
          }
          card.style.left = `${Math.max(16, Math.round(left))}px`;
          card.style.top = `${Math.max(16, Math.round(top))}px`;
        } else {
          const gap = 14;
          const cardWidth = Math.min(320, Math.max(260, promptWidth * 0.78));
          cards.forEach((card) => {
            card.style.width = `${cardWidth}px`;
          });
          const heights = cards.map((card) => Math.max(72, questionUnscaleLayoutValue(card.getBoundingClientRect().height || 72)));
          const totalHeight = heights.reduce((sum, height) => sum + height, 0) + gap * Math.max(0, cards.length - 1);
          const promptCenterY = promptTop + promptHeight / 2;
          let left = promptRight + rail;
          const requiredWidth = left + cardWidth + 96;
          if (requiredWidth > shellWidth + 2 && requestAnswerLayoutWidth(requiredWidth)) {
            return;
          }
          left = Math.max(16, Math.round(left));
          let top = pushAnswerStackClear(left, cardWidth, promptCenterY - totalHeight / 2, heights, gap);
          cards.forEach((card, index) => {
            card.style.left = `${left}px`;
            card.style.top = `${top}px`;
            top += heights[index] + gap;
          });
        }
        ensureAnswerLayoutHeight();
        const promptAfter = questionRootInfoCard.getBoundingClientRect();
        cards.forEach((card, index) => {
          const connector = questionPictureAnswerConnectors[index];
          if (!connector) {
            return;
          }
          const rect = card.getBoundingClientRect();
          const cardIsRight = rect.left >= promptAfter.left + promptAfter.width / 2;
          const start = {
            x: questionUnscaleLayoutValue(promptAfter.left - shellRect.left + (cardIsRight ? promptAfter.width : 0)),
            y: questionUnscaleLayoutValue(promptAfter.top - shellRect.top + Math.min(promptAfter.height * 0.58, promptAfter.height - 24)),
          };
          const end = {
            x: questionUnscaleLayoutValue(rect.left - shellRect.left + (cardIsRight ? 0 : rect.width)),
            y: questionUnscaleLayoutValue(rect.top - shellRect.top + rect.height / 2),
          };
          connector.classList.add("is-live");
          const trunkX = cardIsRight
            ? Math.max(start.x + 28, Math.min(end.x - 22, start.x + Math.max(42, (end.x - start.x) * 0.44)))
            : Math.min(start.x - 28, Math.max(end.x + 22, start.x - Math.max(42, (start.x - end.x) * 0.44)));
          positionQuestionPictureAnswerElbowConnector(connector, start, trunkX, end);
        });
        positionQuestionPicturePromptFeedback(cards, shellRect, promptAfter);
        setQuestionPictureAnswerLayoutPending(false);
      };

      const currentQuestionItem = () => questionCurrentQuestions[questionQuestionIndex] || null;

      const questionNodeQuestionCount = (node = null) => {
        const questions = node && node.cards && Array.isArray(node.cards.questions) ? node.cards.questions : [];
        return questions.length;
      };

      // Added 2026-07-20: Space_Q progress weights each question by its recursive guidance-card workload.
      const questionGuidanceNodeCount = (value = null) => {
        if (Array.isArray(value)) {
          return value.reduce((sum, item) => sum + questionGuidanceNodeCount(item), 0);
        }
        if (!value || typeof value !== "object") {
          return 0;
        }
        const children = Array.isArray(value.children) ? value.children : (Array.isArray(value.items) ? value.items : []);
        return 1 + questionGuidanceNodeCount(children);
      };

      const questionItemRecursiveCount = (question = null) => {
        const tree = question && question.guidance_tree && typeof question.guidance_tree === "object" ? question.guidance_tree : null;
        const items = tree && Array.isArray(tree.items) ? tree.items : [];
        return 1 + questionGuidanceNodeCount(items);
      };

      const questionNodeRecursiveCount = (node = null) => {
        const questions = node && node.cards && Array.isArray(node.cards.questions) ? node.cards.questions : [];
        return questions.reduce((sum, question) => sum + questionItemRecursiveCount(question), 0);
      };

      const questionTotalDirectCount = () => (Array.isArray(questionNodes) ? questionNodes : [])
        .reduce((sum, node) => sum + questionNodeQuestionCount(node), 0);

      const questionTotalQuestionCount = () => (Array.isArray(questionNodes) ? questionNodes : [])
        .reduce((sum, node) => sum + questionNodeRecursiveCount(node), 0);

      const questionCurrentItemCanCountComplete = () => {
        if (!currentQuestionItem()) {
          return false;
        }
        const rootInfoNext = questionRootInfoPromptNode("[data-root-info-next]");
        const rootInfoReady = Boolean(rootInfoNext && !rootInfoNext.disabled);
        const pictureAnswerNext = questionPictureAnswerLayer
          ? questionPictureAnswerLayer.querySelector("[data-picture-answer-next]")
          : null;
        const pictureAnswerReady = Boolean(pictureAnswerNext && !pictureAnswerNext.disabled);
        const questionNextReady = Boolean(qNextButton && !qNextButton.disabled);
        return questionNextReady || rootInfoReady || pictureAnswerReady;
      };

      const questionProgressStats = () => {
        const totalNodes = Math.max(0, Array.isArray(questionNodes) ? questionNodes.length : 0);
        const totalDirectQuestions = questionTotalDirectCount();
        const totalQuestions = questionTotalQuestionCount();
        const currentIndex = Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0));
        let completedQuestions = 0;
        let completedDirectQuestions = 0;
        let completedNodes = 0;
        if (questionPayload && questionPayload.order === "shuffle") {
          const future = new Set((Array.isArray(questionQueue) ? questionQueue : []).map((index) => Number(index)));
          (Array.isArray(questionNodes) ? questionNodes : []).forEach((node, index) => {
            if (index === currentIndex || future.has(index)) {
              return;
            }
            completedNodes += 1;
            completedDirectQuestions += questionNodeQuestionCount(node);
            completedQuestions += questionNodeRecursiveCount(node);
          });
        } else {
          (Array.isArray(questionNodes) ? questionNodes : []).forEach((node, index) => {
            if (index >= currentIndex) {
              return;
            }
            completedNodes += 1;
            completedDirectQuestions += questionNodeQuestionCount(node);
            completedQuestions += questionNodeRecursiveCount(node);
          });
        }
        const currentTotal = Math.max(0, Array.isArray(questionCurrentQuestions) ? questionCurrentQuestions.length : 0);
        const currentDone = Math.max(0, Math.min(
          currentTotal,
          Math.floor(Number(questionQuestionIndex || 0) || 0) + (questionCurrentItemCanCountComplete() ? 1 : 0),
        ));
        completedDirectQuestions += currentDone;
        completedQuestions += (Array.isArray(questionCurrentQuestions) ? questionCurrentQuestions : [])
          .slice(0, currentDone)
          .reduce((sum, question) => sum + questionItemRecursiveCount(question), 0);
        if (currentTotal > 0 && currentDone >= currentTotal) {
          completedNodes += 1;
        }
        const done = completedNodes + completedQuestions;
        const total = totalNodes + totalQuestions;
        const percent = total > 0 ? (done / total) * 100 : 0;
        return {
          done,
          total,
          completedQuestions,
          totalQuestions,
          completedDirectQuestions: Math.max(0, completedDirectQuestions),
          totalDirectQuestions,
          firstTryCorrect: Math.max(0, questionFirstTryCorrectKeys.size),
          completedNodes: Math.max(0, Math.min(totalNodes, completedNodes)),
          totalNodes,
          percent,
        };
      };

      const updateQuestionProgressLabel = () => {
        if (!qProgress) {
          return;
        }
        const stats = questionProgressStats();
        if (!stats.totalNodes && !stats.totalQuestions) {
          clearRuntimeProgress(qProgress, "");
          return;
        }
        renderRuntimeProgress(qProgress, {
          done: stats.done,
          total: stats.total,
          label: "Question progress",
          value: `Topics ${stats.completedNodes}/${stats.totalNodes}`,
          detail: stats.totalQuestions
            ? `Total ${stats.done}/${stats.total} · Questions ${stats.totalDirectQuestions}`
            : `${Math.round(stats.percent)}%`,
          detailItems: stats.totalQuestions
            ? [
              `Total ${stats.done}/${stats.total}`,
              `Questions ${stats.totalDirectQuestions}`,
              `True first ${Math.min(stats.firstTryCorrect, stats.totalDirectQuestions)}/${stats.totalDirectQuestions}`,
            ]
            : [],
          className: "is-space-q",
        });
      };

      const resetQuestionAttemptRewardState = () => {
        questionRunAttemptSeed = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
        questionAttemptSerial = 0;
        questionCurrentAttemptSignature = "";
        questionCurrentAttemptKey = "";
        questionFirstTryAnsweredKeys.clear();
        questionFirstTryCorrectKeys.clear();
      };

      const questionFirstTryProgressKey = (item = currentQuestionItem()) => {
        const node = questionCurrentNode || {};
        return [
          clean(node.id || `node-${questionNodePointer || currentNodeIndex || 0}`),
          Math.max(0, Math.floor(Number(questionQuestionIndex || 0) || 0)),
          clean(item && (item.id || item.question || item.answer) || "question"),
        ].join("|");
      };

      const recordQuestionFirstTryAnswer = (item = currentQuestionItem(), ok = false) => {
        const key = questionFirstTryProgressKey(item);
        if (!key || questionFirstTryAnsweredKeys.has(key)) {
          return false;
        }
        questionFirstTryAnsweredKeys.add(key);
        if (ok) {
          questionFirstTryCorrectKeys.add(key);
        }
        updateQuestionProgressLabel();
        return true;
      };

      const questionAttemptSignatureForItem = (item = currentQuestionItem()) => {
        const node = questionCurrentNode || {};
        return [
          questionRunAttemptSeed,
          clean(node.id || `node-${questionNodePointer || currentNodeIndex || 0}`),
          Math.max(0, Math.floor(Number(questionQuestionIndex || 0) || 0)),
          clean(item && (item.id || item.question || item.answer) || "question"),
        ].join("|");
      };

      const ensureQuestionAttemptRewardKey = (item = currentQuestionItem()) => {
        if (!item) {
          questionCurrentAttemptSignature = "";
          questionCurrentAttemptKey = "";
          return "";
        }
        if (!questionRunAttemptSeed) {
          resetQuestionAttemptRewardState();
        }
        const signature = questionAttemptSignatureForItem(item);
        if (signature !== questionCurrentAttemptSignature) {
          questionAttemptSerial += 1;
          questionCurrentAttemptSignature = signature;
          questionCurrentAttemptKey = `attempt-${questionRunAttemptSeed}-${questionAttemptSerial}`;
        }
        return questionCurrentAttemptKey;
      };

      const questionRootNoticeTurns = (notice) => {
        if (!notice || typeof notice !== "object") {
          return [];
        }
        if (Array.isArray(notice.turns)) {
          return notice.turns.filter((turn) => turn && typeof turn === "object");
        }
        return [notice].filter(Boolean);
      };

      const questionRootNoticeTurnKey = (turn) => {
        const avatar = turn && turn.avatar && typeof turn.avatar === "object" ? turn.avatar : {};
        const speaker = clean(turn && (turn.speaker || turn.name));
        if (speaker) {
          return `speaker:${speaker.toLowerCase()}`;
        }
        return [
          clean(turn && (turn.voice_label || turn.voice)),
          clean(avatar.url),
        ].join("|").toLowerCase();
      };

      const questionRootNoticeAvailable = (item) => {
        const notice = item && item.root_notice ? item.root_notice : null;
        return questionRootNoticeTurns(notice).some((turn) => {
          const clip = turn && turn.audio ? normalizeAudioClip(turn.audio) : null;
          return Boolean(turn && (clean(turn.english || turn.vietnamese) || clip));
        });
      };

      const updateQuestionRootNoticeReplayButton = () => {
        if (!qRootNoticeReplayButton) {
          return;
        }
        const available = Boolean(questionModeActive && questionCardsRevealSettled && questionRootNoticeAvailable(currentQuestionItem()));
        qRootNoticeReplayButton.disabled = !available;
        qRootNoticeReplayButton.title = available
          ? "Replay this root notice"
          : "No notice for this question";
        qRootNoticeReplayButton.setAttribute("aria-disabled", available ? "false" : "true");
      };

      const orderQuestionItems = (items = []) => {
        return orderQuestionEntries(items).map((entry) => entry.item);
      };

      const orderQuestionEntries = (items = [], savedOrder = []) => {
        const source = Array.isArray(items) ? items.slice() : [];
        if (!source.length) {
          return [];
        }
        const entries = source.map((item, index) => ({
          item,
          index,
          order: Math.max(0, Math.floor(Number(item && item.order) || 0)),
        }));
        const restoredOrder = [];
        const restoredUsed = new Set();
        if (Array.isArray(savedOrder) && savedOrder.length) {
          savedOrder.forEach((value) => {
            const index = Math.floor(Number(value));
            if (index >= 0 && index < entries.length && !restoredUsed.has(index)) {
              restoredUsed.add(index);
              restoredOrder.push(entries[index]);
            }
          });
          if (restoredOrder.length === entries.length) {
            return restoredOrder;
          }
        }
        const fixed = entries
          .filter((entry) => entry.order > 0)
          .sort((left, right) => left.order - right.order || left.index - right.index);
        const floatingSource = entries.filter((entry) => entry.order <= 0 && !restoredUsed.has(entry.index));
        const floating = shuffleIndexes(floatingSource.length)
          .map((shuffleIndex) => floatingSource[shuffleIndex]);
        const slots = new Array(source.length).fill(null);
        restoredOrder.forEach((entry, position) => {
          if (position < slots.length) {
            slots[position] = entry;
          }
        });
        fixed.forEach((entry) => {
          if (restoredUsed.has(entry.index)) {
            return;
          }
          let position = Math.max(0, Math.min(slots.length - 1, entry.order - 1));
          while (position < slots.length && slots[position]) {
            position += 1;
          }
          if (position >= slots.length) {
            position = slots.length - 1;
            while (position >= 0 && slots[position]) {
              position -= 1;
            }
          }
          if (position >= 0) {
            slots[position] = entry.item;
          }
        });
        let floatingIndex = 0;
        return slots.map((slot) => slot || floating[floatingIndex++]).filter(Boolean);
      };

      const questionCardAudioClip = (audioConfig) => {
        const source = audioConfig && typeof audioConfig === "object" ? audioConfig : {};
        const mode = clean(source.mode).toLowerCase() || ((source.url || source.base64) ? "click" : "");
        if (!mode || mode === "off") {
          return null;
        }
        return normalizeAudioClip(source.url || source.base64 ? source : {
          mime: source.mime || "audio/mpeg",
          url: source.url || "",
          base64: source.base64 || "",
        });
      };

      const questionCardAnswerAudioSource = (question, value) => {
        const source = question && question.answer_audio && typeof question.answer_audio === "object" ? question.answer_audio : {};
        const wanted = questionAnswerKey(value);
        const items = Array.isArray(source.items) ? source.items : [];
        const match = items.find((entry) => entry && typeof entry === "object" && questionAnswerKey(entry.text || entry.t || entry.answer || entry.a) === wanted);
        return match || source;
      };

      const questionCardAnswerAudioClip = (question, value) => {
        return questionCardAudioClip(questionCardAnswerAudioSource(question, value));
      };

      const questionAnswerInfoSource = (question, value) => {
        const source = question && question.answer_info && typeof question.answer_info === "object" ? question.answer_info : {};
        const wanted = questionAnswerKey(value);
        const items = Array.isArray(source.items) ? source.items : [];
        return items.find((entry) => entry && typeof entry === "object" && questionAnswerKey(entry.text || entry.t || entry.answer || entry.a) === wanted) || null;
      };

      const shouldQuestionAnswerAudioShowButton = (question, value) => {
        return shouldQuestionAudioShowButton(questionCardAnswerAudioSource(question, value));
      };

      const shouldQuestionAudioAutoPlay = (audioConfig) => {
        const source = audioConfig && typeof audioConfig === "object" ? audioConfig : {};
        const mode = clean(source.mode).toLowerCase();
        return mode === "auto" || mode === "both";
      };

      const shouldQuestionAudioShowButton = (audioConfig) => {
        const source = audioConfig && typeof audioConfig === "object" ? audioConfig : {};
        const mode = clean(source.mode).toLowerCase() || ((source.url || source.base64) ? "click" : "");
        return mode === "click" || mode === "both";
      };

      const playQuestionCardClip = (clip) => {
        const asset = normalizeAudioClip(clip);
        if (!asset) {
          return Promise.resolve(false);
        }
        stopQuestionCardActiveAudio();
        let finished = false;
        const active = {
          active: true,
          audio: null,
          done: null,
          promise: null,
          stop: null,
        };
        const playback = new Promise(async (resolve) => {
          const done = (ok = true) => {
            if (finished) {
              return;
            }
            finished = true;
            active.active = false;
            if (questionCardActiveAudio === active) {
              questionCardActiveAudio = null;
            }
            resolve(ok);
          };
          active.done = done;
          try {
            if (asset.kind === "speak") {
              active.stop = () => stopGrammarAudio();
              questionCardActiveAudio = active;
              playSelectedEnglishGrammarText(asset.text, [])
                .then(done)
                .catch(() => done(false));
              return;
            }
            await preloadAudioClip(asset, null);
            const audio = new Audio(cachedAudioClipUrl(asset));
            active.audio = audio;
            active.stop = () => {
              audio.pause();
              audio.currentTime = 0;
            };
            audio.preload = "auto";
            normalizeAudioPlaybackSpeed(audio);
            audio.volume = 0.94;
            audio.onended = () => done(true);
            audio.onerror = () => done(false);
            questionCardActiveAudio = active;
            const started = audio.play();
            if (started && typeof started.catch === "function") {
              started.catch(() => done(false));
            }
          } catch (error) {
            done(false);
          }
        });
        active.promise = playback;
        return playback;
      };

      const playQuestionPromptAudio = () => {
        const item = currentQuestionItem();
        const clip = questionCardAudioClip(item && item.audio);
        return playQuestionCardClip(clip);
      };

      const clearQuestionRootNoticeVoiceDelay = (result = false) => {
        if (questionRootNoticeVoiceDelayTimer) {
          window.clearTimeout(questionRootNoticeVoiceDelayTimer);
          questionRootNoticeVoiceDelayTimer = 0;
        }
        if (typeof questionRootNoticeVoiceDelayResolve === "function") {
          const resolve = questionRootNoticeVoiceDelayResolve;
          questionRootNoticeVoiceDelayResolve = null;
          resolve(result);
        }
      };

      const waitQuestionRootNoticeVoiceCue = (token) => {
        clearQuestionRootNoticeVoiceDelay(false);
        return new Promise(async (resolve) => {
          questionRootNoticeVoiceDelayResolve = resolve;
          questionRootNoticeVoiceDelayTimer = window.setTimeout(() => {
            questionRootNoticeVoiceDelayTimer = 0;
            questionRootNoticeVoiceDelayResolve = null;
            resolve(token === questionRootNoticeTypingToken && !!qRootNotice && qRootNotice.classList.contains("is-live"));
          }, QUESTION_ROOT_NOTICE_VOICE_DELAY_MS);
        });
      };

      const stopQuestionRootNotice = () => {
        questionRootNoticeTypingToken += 1;
        if (typeof questionRootNoticePendingFinish === "function") {
          const finish = questionRootNoticePendingFinish;
          questionRootNoticePendingFinish = null;
          finish(false);
        }
        if (questionRootNoticeCompletionTimer) {
          window.clearTimeout(questionRootNoticeCompletionTimer);
          questionRootNoticeCompletionTimer = 0;
        }
        if (questionRootNoticeBootTimer) {
          window.clearTimeout(questionRootNoticeBootTimer);
          questionRootNoticeBootTimer = 0;
        }
        clearQuestionRootNoticeVoiceDelay(false);
        if (questionRootNoticeTypingTimer) {
          window.clearTimeout(questionRootNoticeTypingTimer);
          questionRootNoticeTypingTimer = 0;
        }
        if (questionRootNoticeAudio) {
          try {
            questionRootNoticeAudio.pause();
            questionRootNoticeAudio.currentTime = 0;
          } catch (error) {}
          questionRootNoticeAudio = null;
        }
        if (qRootNotice) {
          qRootNotice.classList.remove("is-live", "is-speaking", "is-hiding", "is-notice-replay-animating", "has-avatar");
        }
        if (qRootNoticeAvatar) {
          const image = qRootNoticeAvatar.querySelector("img");
          if (image) {
            image.removeAttribute("src");
          }
        }
        if (qRootNoticeEn) {
          qRootNoticeEn.textContent = "";
        }
        if (qRootNoticeVi) {
          qRootNoticeVi.textContent = "";
        }
        if (qRootNoticeVoice) {
          qRootNoticeVoice.textContent = "";
        }
      };

      const setQuestionRootNoticeAvatar = (turn) => {
        if (!qRootNotice || !qRootNoticeAvatar) {
          return;
        }
        const avatar = turn && turn.avatar && typeof turn.avatar === "object" ? turn.avatar : {};
        const url = clean(avatar.url || turn && (turn.avatar_url || turn.avatarUrl || turn.picture_url || turn.pictureUrl));
        const image = qRootNoticeAvatar.querySelector("img");
        if (url && image) {
          image.src = resolveServerAssetUrl(url);
          qRootNotice.classList.add("has-avatar");
        } else {
          if (image) {
            image.removeAttribute("src");
          }
          qRootNotice.classList.remove("has-avatar");
        }
      };

      const questionRootNoticeSpeakerLabel = (turn, clip) => {
        const speaker = clean(turn && (turn.speaker || turn.name || turn.character));
        if (speaker) {
          return speaker;
        }
        const voiceLabel = clean(turn && (turn.voice_label || turn.label || turn.voice));
        if (voiceLabel) {
          return voiceLabel;
        }
        return clip ? "VOICE READY" : "Typing only";
      };

      const typeQuestionRootNoticeText = (notice, token) => {
        if (!qRootNoticeEn || !qRootNoticeVi || token !== questionRootNoticeTypingToken) {
          return Promise.resolve(false);
        }
        const english = preserveQuestionText(notice && notice.english);
        const vietnamese = preserveQuestionText(notice && notice.vietnamese);
        const fullText = english && vietnamese ? `${english}\n${vietnamese}` : (english || vietnamese);
        qRootNoticeEn.textContent = "";
        qRootNoticeVi.textContent = "";
        if (!fullText) {
          return Promise.resolve(true);
        }
        let index = 0;
        const englishLength = english.length;
        return new Promise(async (resolve) => {
          const tick = () => {
            if (token !== questionRootNoticeTypingToken) {
              resolve(false);
              return;
            }
            index += Math.max(1, Math.ceil(fullText.length / 90));
            const visible = fullText.slice(0, index);
            qRootNoticeEn.textContent = visible.slice(0, englishLength);
            qRootNoticeVi.textContent = visible.slice(english && vietnamese ? englishLength + 1 : englishLength);
            if (index < fullText.length) {
              questionRootNoticeTypingTimer = window.setTimeout(tick, 20 + Math.random() * 26);
            } else {
              questionRootNoticeTypingTimer = 0;
              resolve(true);
            }
          };
          tick();
        });
      };

      const playQuestionRootNoticeAudio = (notice, token) => {
        const clip = notice && notice.audio ? normalizeAudioClip(notice.audio) : null;
        if (!clip || clip.kind === "speak") {
          return Promise.resolve(false);
        }
        return new Promise(async (resolve) => {
          let settled = false;
          const done = () => {
            if (settled) {
              return;
            }
            settled = true;
            if (token === questionRootNoticeTypingToken && qRootNotice) {
              qRootNotice.classList.remove("is-speaking");
            }
            if (token === questionRootNoticeTypingToken) {
              questionRootNoticeAudio = null;
            }
            resolve(true);
          };
          try {
            await preloadAudioClip(clip, null);
            const audio = new Audio(cachedAudioClipUrl(clip));
            questionRootNoticeAudio = audio;
            audio.volume = 0.92;
            normalizeAudioPlaybackSpeed(audio);
            if (qRootNotice) {
              qRootNotice.classList.add("is-speaking");
            }
            audio.addEventListener("ended", done, { once: true });
            audio.addEventListener("error", done, { once: true });
            const started = audio.play();
            if (started && typeof started.catch === "function") {
              started.catch(done);
            }
          } catch (error) {
            if (qRootNotice) {
              qRootNotice.classList.remove("is-speaking");
            }
            questionRootNoticeAudio = null;
            done();
          }
        });
      };

      const hideQuestionRootNoticeBetweenTurns = (token) => new Promise((resolve) => {
        if (!qRootNotice || !qRootNotice.classList.contains("is-live")) {
          resolve(true);
          return;
        }
        qRootNotice.classList.remove("is-speaking");
        qRootNotice.classList.add("is-hiding");
        window.setTimeout(() => {
          if (token !== questionRootNoticeTypingToken) {
            resolve(false);
            return;
          }
          if (qRootNotice) {
            qRootNotice.classList.remove("is-live", "is-hiding", "has-avatar");
          }
          resolve(true);
        }, QUESTION_ROOT_NOTICE_HIDE_MS);
      });

      const showQuestionRootNoticeTurn = (turn, token, options = {}) => {
        const clip = turn && turn.audio ? normalizeAudioClip(turn.audio) : null;
        const hasText = clean(turn && (turn.english || turn.vietnamese));
        if (!turn || (!hasText && !clip)) {
          return Promise.resolve(false);
        }
        const sameSpeaker = Boolean(options.sameSpeaker && qRootNotice && qRootNotice.classList.contains("is-live"));
        if (qRootNotice) {
          qRootNotice.classList.remove("is-speaking", "is-hiding");
          qRootNotice.classList.toggle("is-notice-replay-animating", Boolean(options.allowAnimation));
          if (!sameSpeaker) {
            qRootNotice.classList.remove("is-live");
            void qRootNotice.offsetWidth;
            qRootNotice.classList.add("is-live");
          }
        }
        setQuestionRootNoticeAvatar(turn);
        if (qRootNoticeVoice) {
          qRootNoticeVoice.textContent = questionRootNoticeSpeakerLabel(turn, clip);
        }
        if (qRootNoticeEn) {
          qRootNoticeEn.textContent = "";
        }
        if (qRootNoticeVi) {
          qRootNoticeVi.textContent = "";
        }
        return new Promise((resolve) => {
          const startTurn = () => {
            questionRootNoticeBootTimer = 0;
            if (token !== questionRootNoticeTypingToken || !qRootNotice || !qRootNotice.classList.contains("is-live")) {
              resolve(false);
              return;
            }
            const typingDone = typeQuestionRootNoticeText(turn, token);
            const audioDone = clip
              ? waitQuestionRootNoticeVoiceCue(token).then((ready) => (
                ready ? playQuestionRootNoticeAudio(turn, token) : false
              ))
              : Promise.resolve(false);
            Promise.all([typingDone, audioDone]).then(() => resolve(token === questionRootNoticeTypingToken));
          };
          if (sameSpeaker) {
            startTurn();
          } else {
            questionRootNoticeBootTimer = window.setTimeout(startTurn, QUESTION_ROOT_NOTICE_BOOT_MS);
          }
        });
      };

      const showQuestionRootNotice = (question, options = {}) => {
        const notice = question && question.root_notice ? question.root_notice : null;
        const turns = questionRootNoticeTurns(notice).filter((turn) => {
          const clip = turn && turn.audio ? normalizeAudioClip(turn.audio) : null;
          return Boolean(turn && (clean(turn.english || turn.vietnamese) || clip));
        });
        if (!turns.length) {
          stopQuestionRootNotice();
          return Promise.resolve(false);
        }
        stopQuestionRootNotice();
        const token = questionRootNoticeTypingToken;
        return new Promise((resolve) => {
          questionRootNoticePendingFinish = resolve;
          const runTurn = (index, previousKey = "") => {
            if (token !== questionRootNoticeTypingToken) {
              if (questionRootNoticePendingFinish === resolve) {
                questionRootNoticePendingFinish = null;
                resolve(false);
              }
              return;
            }
            const turn = turns[index];
            const currentKey = questionRootNoticeTurnKey(turn);
            const sameSpeaker = Boolean(index > 0 && previousKey && currentKey && currentKey === previousKey);
            const showNext = () => {
              showQuestionRootNoticeTurn(turn, token, {
                allowAnimation: options.allowAnimation,
                sameSpeaker,
              }).then((shown) => {
                if (!shown || token !== questionRootNoticeTypingToken) {
                  if (questionRootNoticePendingFinish === resolve) {
                    questionRootNoticePendingFinish = null;
                    resolve(Boolean(shown));
                  }
                  return;
                }
                if (index >= turns.length - 1) {
                  if (questionRootNoticePendingFinish === resolve) {
                    questionRootNoticePendingFinish = null;
                    resolve(true);
                  }
                  return;
                }
                runTurn(index + 1, currentKey);
              });
            };
            if (index > 0 && !sameSpeaker) {
              hideQuestionRootNoticeBetweenTurns(token).then((ready) => {
                if (ready) {
                  showNext();
                } else if (questionRootNoticePendingFinish === resolve) {
                  questionRootNoticePendingFinish = null;
                  resolve(false);
                }
              });
            } else {
              showNext();
            }
          };
          runTurn(0, "");
        });
      };

      const replayQuestionRootNotice = () => {
        const item = currentQuestionItem();
        if (!questionRootNoticeAvailable(item)) {
          updateQuestionRootNoticeReplayButton();
          setQuestionFeedback("This question has no root notice.", "error");
          return Promise.resolve(false);
        }
        setQuestionFeedback("Replaying root notice...", "ok");
        return showQuestionRootNotice(item, { allowAnimation: true }).then((shown) => {
          if (!shown) {
            return false;
          }
          if (questionRootNoticeCompletionTimer) {
            window.clearTimeout(questionRootNoticeCompletionTimer);
          }
          questionRootNoticeCompletionTimer = window.setTimeout(() => {
            questionRootNoticeCompletionTimer = 0;
            stopQuestionRootNotice();
          }, QUESTION_ROOT_NOTICE_AFTER_MS);
          return true;
        });
      };

      const clearQuestionInfoHideTimer = () => {
        if (questionInfoHideTimer) {
          window.clearTimeout(questionInfoHideTimer);
          questionInfoHideTimer = 0;
        }
      };

      const finishQuestionInfoHide = () => {
        clearQuestionInfoHideTimer();
        if (qInfoCard) {
          qInfoCard.classList.remove("is-live", "is-hiding", "is-info-presenting", "is-connector-focused");
          clearQuestionCardFxActive(qInfoCard);
        }
        if (qConnectorInfo) {
          qConnectorInfo.classList.remove("is-live", "is-focused");
        }
        if (qInfoText) {
          qInfoText.textContent = "";
        }
        clearQuestionRootChoiceSignalInfo();
        if (qInfoPlayButton) {
          qInfoPlayButton.classList.add("ft-q-show-answer-hidden");
        }
      };

      const hideQuestionInfoCard = (options = {}) => {
        if (questionInfoTypingTimer) {
          window.clearTimeout(questionInfoTypingTimer);
          questionInfoTypingTimer = 0;
        }
        stopQuestionInfoRevealWait();
        questionInfoAudioClip = null;
        const wait = Boolean(options && options.wait);
        const immediate = Boolean(options && options.immediate);
        const canAnimate = Boolean(
          !immediate
          && qInfoCard
          && (qInfoCard.classList.contains("is-live") || qInfoCard.classList.contains("is-hiding"))
        );
        if (!canAnimate) {
          finishQuestionInfoHide();
          return wait ? Promise.resolve(false) : false;
        }
        clearQuestionInfoHideTimer();
        qInfoCard.classList.remove("is-live");
        qInfoCard.classList.add("is-hiding", "is-info-presenting");
        if (qConnectorInfo) {
          qConnectorInfo.classList.add("is-focused");
        }
        const promise = new Promise((resolve) => {
          questionInfoHideTimer = window.setTimeout(() => {
            finishQuestionInfoHide();
            resolve(true);
          }, QUESTION_INFO_CARD_HIDE_MS);
        });
        return wait ? promise : true;
      };

      const typeQuestionInfoText = (text) => {
        if (!qInfoText) {
          return;
        }
        if (questionInfoTypingTimer) {
          window.clearTimeout(questionInfoTypingTimer);
          questionInfoTypingTimer = 0;
        }
        const fullText = clean(text);
        qInfoText.textContent = "";
        let index = 0;
        const tick = () => {
          index += Math.max(1, Math.ceil(fullText.length / 80));
          qInfoText.textContent = fullText.slice(0, index);
          if (index < fullText.length) {
            questionInfoTypingTimer = window.setTimeout(tick, 18 + Math.random() * 24);
          } else {
            questionInfoTypingTimer = 0;
          }
        };
        tick();
      };

      const showQuestionRootChoiceSignalInfo = (info) => {
        if (!info || !clean(info.info_text) || !questionRootChoiceSignalShouldRoute()) {
          return false;
        }
        questionInfoAudioClip = null;
        clearQuestionInfoHideTimer();
        if (qInfoCard) {
          qInfoCard.classList.remove("is-live", "is-hiding", "is-info-presenting", "is-connector-focused");
          clearQuestionCardFxActive(qInfoCard);
        }
        if (qConnectorInfo) {
          qConnectorInfo.classList.remove("is-live", "is-focused");
        }
        if (qInfoText) {
          qInfoText.textContent = "";
        }
        if (qInfoPlayButton) {
          qInfoPlayButton.classList.add("ft-q-show-answer-hidden");
        }
        beginQuestionInfoRevealWait(Math.max(260, Math.round(QUESTION_INFO_CARD_REVEAL_MS * 0.55)));
        const mode = clean(info.mode).toLowerCase();
        const audioClip = questionCardAudioClip(info.audio);
        if (mode === "audio" && audioClip) {
          questionInfoAudioClip = audioClip;
          setQuestionRootChoiceSignalInfo(info.info_text, "", { force: true });
          void playQuestionCardClip(audioClip);
        } else {
          setQuestionRootChoiceSignalInfo(info.info_text, "", { force: true });
        }
        return true;
      };

      const showQuestionAnswerInfo = (question, value) => {
        const info = questionAnswerInfoSource(question, value);
        if (!info || !clean(info.info_text)) {
          hideQuestionInfoCard();
          return false;
        }
        if (showQuestionRootChoiceSignalInfo(info)) {
          return true;
        }
        questionInfoAudioClip = null;
        clearQuestionInfoHideTimer();
        if (qInfoCard) {
          qInfoCard.classList.remove("is-hiding");
          qInfoCard.classList.add("is-live", "is-info-presenting", "is-connector-focused");
          activateQuestionCardFx(qInfoCard, QUESTION_INFO_CARD_REVEAL_MS + 900);
        }
        if (qConnectorInfo) {
          qConnectorInfo.classList.add("is-live", "is-focused");
        }
        beginQuestionInfoRevealWait(QUESTION_INFO_CARD_REVEAL_MS);
        const mode = clean(info.mode).toLowerCase();
        const audioClip = questionCardAudioClip(info.audio);
        if (mode === "audio" && audioClip) {
          questionInfoAudioClip = audioClip;
          if (qInfoPlayButton) {
            qInfoPlayButton.classList.remove("ft-q-show-answer-hidden");
          }
          typeQuestionInfoText(info.info_text);
          void playQuestionCardClip(audioClip);
        } else {
          if (qInfoPlayButton) {
            qInfoPlayButton.classList.add("ft-q-show-answer-hidden");
          }
          typeQuestionInfoText(info.info_text);
        }
        scheduleQuestionSideLayout();
        keepQuestionCardOnlyInView({ passes: 2 });
        settleQuestionCardOnlyView([120, 360]);
        return true;
      };

      const autoplayQuestionItemAudio = (item, optionValues = []) => {
        const sequence = [];
        if (item && shouldQuestionAudioAutoPlay(item.audio)) {
          const promptClip = questionCardAudioClip(item.audio);
          if (promptClip) {
            sequence.push(promptClip);
          }
        }
        if (item) {
          optionValues.forEach((value) => {
            const answerSource = questionCardAnswerAudioSource(item, value);
            const answerClip = shouldQuestionAudioAutoPlay(answerSource) ? questionCardAudioClip(answerSource) : null;
            if (answerClip) {
              sequence.push(answerClip);
            }
          });
        }
        if (sequence.length) {
          void playGrammarAudioSequence(sequence);
        }
      };

      const revealQuestionAnswerButton = () => {
        if (qShowAnswerButton) {
          qShowAnswerButton.classList.remove("ft-q-show-answer-hidden");
        }
      };

      const syncedPictureQuestionPayloadForItem = (payload, item) => {
        if (!payload || typeof payload !== "object") {
          return null;
        }
        const questionText = preserveQuestionText(item && item.question);
        const text = questionText || preserveQuestionText(payload.text);
        return text ? { ...payload, text } : null;
      };

      const questionItemCardMode = (item) => normalizeQuestionCardMode(
        item && (item.card_mode ?? item.cardMode ?? item.question_card_mode ?? item.questionCardMode ?? item.display_mode ?? item.displayMode ?? item.cm),
        "question",
      );

      const questionItemUsesLinkingCard = (item) => !isQuestionSelectItem(item) && questionItemCardMode(item) === "linking";

      const questionRootPictureQuestionForItem = (item, ranges = []) => {
        if (isQuestionSelectItem(item)) {
          return null;
        }
        const rangeItems = Array.isArray(ranges) ? ranges : [];
        const wantsLinkingCard = questionItemUsesLinkingCard(item);
        if (wantsLinkingCard) {
          const highlightRange = rangeItems.find((range) => range && Number(range.end) > Number(range.start) && (!range.pictureQuestion || (range.pictureQuestion.anchor || "highlight") === "highlight"));
          if (highlightRange) {
            const payload = syncedPictureQuestionPayloadForItem({
              ...(highlightRange.pictureQuestion || {}),
              anchor: "highlight",
              placement: (highlightRange.pictureQuestion && highlightRange.pictureQuestion.placement) || "auto",
            }, item);
            return payload ? { payload, sourceIndex: highlightRange.sourceIndex } : null;
          }
        }
        const regionRange = rangeItems.find((range) => {
          if (!range || !range.pictureQuestion) {
            return false;
          }
          return range.pictureQuestion.anchor === "picture_regions"
            && normalizeQuestionPictureRegions(range.pictureQuestion.regions || []).length > 0;
        });
        if (regionRange) {
          const payload = syncedPictureQuestionPayloadForItem({ ...regionRange.pictureQuestion, anchor: "picture_regions" }, item);
          return payload ? { payload, sourceIndex: regionRange.sourceIndex } : null;
        }
        const fromRange = rangeItems.find((range) => range && range.pictureQuestion);
        if (fromRange) {
          const payload = syncedPictureQuestionPayloadForItem(fromRange.pictureQuestion, item);
          return payload ? { payload, sourceIndex: fromRange.sourceIndex } : null;
        }
        const rawHighlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        for (let index = 0; index < rawHighlights.length; index += 1) {
          const payload = questionRootPictureQuestionPayload(rawHighlights[index], item && item.question);
          if (payload && payload.text && payload.anchor === "picture_regions" && normalizeQuestionPictureRegions(payload.regions || []).length) {
            return { payload: { ...payload, anchor: "picture_regions" }, sourceIndex: index };
          }
        }
        for (let index = 0; index < rawHighlights.length; index += 1) {
          const payload = questionRootPictureQuestionPayload(rawHighlights[index], item && item.question);
          if (payload && payload.text) {
            return { payload: { ...payload, anchor: payload.anchor || "picture" }, sourceIndex: index };
          }
        }
        if (questionItemUsesLinkingCard(item)) {
          const firstRange = rangeItems.find((range) => range && Number(range.end) > Number(range.start));
          const anchor = firstRange ? "highlight" : "root";
          return {
            payload: {
              text: preserveQuestionText(item && item.question),
              anchor,
              placement: "auto",
            },
            sourceIndex: firstRange ? Math.max(0, Number(firstRange.sourceIndex) || 0) : -1,
          };
        }
        return null;
      };

      const questionLinkingQuestionEntryForItem = (item, ranges = []) => {
        if (isQuestionSelectItem(item)) {
          return null;
        }
        const entry = questionRootPictureQuestionForItem(item, ranges);
        if (!entry || !entry.payload || !entry.payload.text) {
          return null;
        }
        if (questionItemUsesLinkingCard(item) || entry.payload.anchor === "picture_regions") {
          return entry;
        }
        return null;
      };

      const questionPictureRegionEntryForItem = (item, ranges = []) => {
        if (isQuestionSelectItem(item)) {
          return null;
        }
        const rangeItems = Array.isArray(ranges) ? ranges : [];
        for (const range of rangeItems) {
          if (!range || !range.pictureQuestion) {
            continue;
          }
          const syncedPayload = syncedPictureQuestionPayloadForItem(range.pictureQuestion, item);
          const regions = normalizeQuestionPictureRegions(syncedPayload && syncedPayload.regions ? syncedPayload.regions : []);
          if (syncedPayload && syncedPayload.anchor === "picture_regions" && regions.length) {
            return {
              payload: { ...syncedPayload, anchor: "picture_regions", regions },
              sourceIndex: range.sourceIndex,
            };
          }
        }
        const rawHighlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        for (let index = 0; index < rawHighlights.length; index += 1) {
          const payload = questionRootPictureQuestionPayload(rawHighlights[index], item && item.question);
          const regions = normalizeQuestionPictureRegions(payload && payload.regions ? payload.regions : []);
          if (payload && payload.text && payload.anchor === "picture_regions" && regions.length) {
            return { payload: { ...payload, anchor: "picture_regions", regions }, sourceIndex: index };
          }
        }
        return null;
      };

      const currentQuestionUsesPictureRegions = () => Boolean(questionPictureRegionEntryForItem(currentQuestionItem(), []));

      const questionHighlightCameraFocusEnabled = (highlight) => {
        if (!highlight || typeof highlight !== "object") {
          return false;
        }
        const keys = [
          "camera_focus",
          "cameraFocus",
          "focus",
          "f",
          "pan_to_highlight",
          "panToHighlight",
          "pan",
          "follow",
          "move_view",
          "moveView",
        ];
        let value;
        let found = false;
        for (const key of keys) {
          if (Object.prototype.hasOwnProperty.call(highlight, key)) {
            value = highlight[key];
            found = true;
            break;
          }
        }
        if (!found) {
          return false;
        }
        if (typeof value === "boolean") {
          return value;
        }
        if (typeof value === "number") {
          return value !== 0;
        }
        const text = clean(value).toLowerCase();
        return ["1", "true", "yes", "y", "on", "checked", "tick", "pan", "focus"].includes(text);
      };

      const questionItemShouldFocusHighlights = (item, ranges = []) => {
        const highlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        if (!highlights.length) {
          return false;
        }
        if (isQuestionSelectItem(item) && Array.isArray(ranges) && ranges.length) {
          return true;
        }
        const rangeIndexes = Array.isArray(ranges) && ranges.length
          ? new Set(ranges.map((range) => Math.max(0, Number(range && range.sourceIndex) || 0)))
          : null;
        return highlights.some((highlight, index) => (
          (!rangeIndexes || rangeIndexes.has(index)) && questionHighlightCameraFocusEnabled(highlight)
        ));
      };

      const questionRootHighlightRangeSourceIndex = (range) => (
        Math.max(0, Number(range && range.sourceIndex) || 0)
      );

      const questionRootHighlightRangeShouldFocus = (item, range, options = {}) => {
        if (options.focusAllRanges === true) {
          return true;
        }
        if (isQuestionSelectItem(item) && range) {
          return true;
        }
        const highlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        return questionHighlightCameraFocusEnabled(highlights[questionRootHighlightRangeSourceIndex(range)]);
      };

      const questionRootHighlightRangesForItem = (item) => {
        if (!qRootText) {
          return [];
        }
        const rootText = questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
        const highlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        const ranges = questionRootHighlightRanges(rootText, highlights, item && item.question)
          .sort((left, right) => left.start - right.start || left.end - right.end);
        if (isQuestionSelectItem(item)) {
          return ranges.map((range) => ({ ...range, pictureQuestion: null }));
        }
        return ranges;
      };

      const questionRootHighlightRangesSignature = (ranges = []) => (
        (Array.isArray(ranges) ? ranges : [])
          .map((range) => {
            const start = Math.max(0, Math.floor(Number(range && range.start) || 0));
            const end = Math.max(start, Math.floor(Number(range && range.end) || start));
            const sourceIndex = Math.max(0, Math.floor(Number(range && range.sourceIndex) || 0));
            const render = clean(range && range.render);
            return `${sourceIndex}:${start}:${end}:${render}`;
          })
          .join("|")
      );

      const questionRootHighlightFocusNode = (ranges = []) => {
        if (!qRootText || !Array.isArray(ranges) || !ranges.length) {
          return qRootCard;
        }
        const rootText = questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
        const firstRange = ranges[0] || {};
        const lineIndex = Math.max(0, preserveQuestionText(rootText).slice(0, Math.max(0, firstRange.start || 0)).split("\n").length - 1);
        const lines = Array.from(qRootText.querySelectorAll(".ft-q-root-line"));
        return lines[Math.min(lineIndex, Math.max(0, lines.length - 1))] || qRootCard;
      };

      const questionUnionClientRects = (rects = []) => {
        const usable = rects.filter((rect) => rect && rect.width > 0 && rect.height > 0);
        if (!usable.length) {
          return null;
        }
        const left = Math.min(...usable.map((rect) => rect.left));
        const top = Math.min(...usable.map((rect) => rect.top));
        const right = Math.max(...usable.map((rect) => rect.right));
        const bottom = Math.max(...usable.map((rect) => rect.bottom));
        return {
          left,
          top,
          right,
          bottom,
          x: left,
          y: top,
          width: Math.max(1, right - left),
          height: Math.max(1, bottom - top),
        };
      };

      const questionTextRangeClientRect = (container, startOffset = 0, endOffset = 0) => {
        if (!container || !document.createRange || !document.createTreeWalker) {
          return null;
        }
        const textLength = (container.textContent || "").length;
        const start = Math.max(0, Math.min(textLength, Math.floor(Number(startOffset) || 0)));
        const end = Math.max(start, Math.min(textLength, Math.ceil(Number(endOffset) || start)));
        if (end <= start) {
          return null;
        }
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
        let offset = 0;
        let node = null;
        let startNode = null;
        let endNode = null;
        let startNodeOffset = 0;
        let endNodeOffset = 0;
        let lastTextNode = null;
        while ((node = walker.nextNode())) {
          const length = (node.nodeValue || "").length;
          const nextOffset = offset + length;
          if (length > 0) {
            lastTextNode = node;
          }
          if (!startNode && start <= nextOffset) {
            startNode = node;
            startNodeOffset = Math.max(0, Math.min(length, start - offset));
          }
          if (startNode && end <= nextOffset) {
            endNode = node;
            endNodeOffset = Math.max(0, Math.min(length, end - offset));
            break;
          }
          offset = nextOffset;
        }
        if (!startNode || !lastTextNode) {
          return null;
        }
        if (!endNode) {
          endNode = lastTextNode;
          endNodeOffset = (lastTextNode.nodeValue || "").length;
        }
        try {
          const range = document.createRange();
          range.setStart(startNode, startNodeOffset);
          range.setEnd(endNode, endNodeOffset);
          const rect = questionUnionClientRects(Array.from(range.getClientRects()));
          range.detach && range.detach();
          return rect;
        } catch (error) {
          return null;
        }
      };

      function hideQuestionRootScrollbarChrome() {
        if (questionRootScrollbarHideTimer) {
          window.clearTimeout(questionRootScrollbarHideTimer);
          questionRootScrollbarHideTimer = 0;
        }
        if (qRootText) {
          qRootText.classList.remove("is-root-scrollbar-active");
        }
      }

      function signalQuestionRootTextScroll() {
        if (!qRootText) {
          return;
        }
        qRootText.classList.add("is-root-scrollbar-active");
        scheduleQuestionSelectRootOverlayReposition();
        if (questionRootScrollbarHideTimer) {
          window.clearTimeout(questionRootScrollbarHideTimer);
        }
        questionRootScrollbarHideTimer = window.setTimeout(() => {
          questionRootScrollbarHideTimer = 0;
          if (qRootText) {
            qRootText.classList.remove("is-root-scrollbar-active");
          }
        }, 2000);
      }

      if (qRootText) {
        qRootText.addEventListener("scroll", signalQuestionRootTextScroll, { passive: true });
      }

      document.addEventListener("selectstart", (event) => {
        const target = event && event.target;
        if (!target || typeof target.closest !== "function") {
          return;
        }
        if (target.closest("input,textarea,select,[contenteditable='true'],[contenteditable='']")) {
          return;
        }
        if (target.closest(".ft-q-root-card,.ft-q-audio-card,.ft-q-picture-card,.ft-q-question-card,.ft-q-root-info-card,.ft-q-picture-answer-card,.ft-q-guidance-layer")) {
          event.preventDefault();
        }
      }, true);

      const scrollQuestionRootTextToNode = (node, behavior = "auto", blockRatio = 0.34) => {
        if (!qRootText || !node || !node.isConnected || qRootText.scrollHeight <= qRootText.clientHeight + 2) {
          return false;
        }
        const textRect = qRootText.getBoundingClientRect();
        const nodeRect = node.getBoundingClientRect();
        if (!textRect.height || !nodeRect.height) {
          return false;
        }
        const currentTop = qRootText.scrollTop || 0;
        const relativeTop = nodeRect.top - textRect.top + currentTop;
        const targetTop = Math.max(0, relativeTop - qRootText.clientHeight * Math.max(0, Math.min(0.82, blockRatio)));
        if (Math.abs(targetTop - currentTop) < 2) {
          return false;
        }
        signalQuestionRootTextScroll();
        if (typeof qRootText.scrollTo === "function") {
          try {
            qRootText.scrollTo({ top: targetTop, behavior });
            return true;
          } catch (error) {
          }
        }
        qRootText.scrollTop = targetTop;
        return true;
      };

      const scrollQuestionRootTextToRange = (range, behavior = "auto") => {
        if (!qRootText || !range || qRootText.scrollHeight <= qRootText.clientHeight + 2) {
          return false;
        }
        const rootText = questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
        const rangeStart = Math.max(0, Number.isFinite(Number(range.start)) ? Number(range.start) : Number(range.index) || 0);
        const lineIndex = Math.max(0, preserveQuestionText(rootText).slice(0, rangeStart).split("\n").length - 1);
        const lines = Array.from(qRootText.querySelectorAll(".ft-q-root-line"));
        const lineNode = lines[Math.min(lineIndex, Math.max(0, lines.length - 1))];
        return scrollQuestionRootTextToNode(lineNode, behavior);
      };

      const questionRootCardFitsStageView = () => {
        if (!stageNode || !qRootCard) {
          return true;
        }
        const rootRect = qRootCard.getBoundingClientRect();
        const stageRect = stageNode.getBoundingClientRect();
        if (!rootRect.height || !stageRect.height) {
          return true;
        }
        const textRect = qRootText && typeof qRootText.getBoundingClientRect === "function"
          ? qRootText.getBoundingClientRect()
          : null;
        const rootHeight = textRect && textRect.height > 0
          ? Math.max(rootRect.height, textRect.height + 72)
          : rootRect.height;
        return rootHeight <= Math.max(120, stageRect.height + 16);
      };

      const questionRootHighlightFocusRect = (ranges = []) => {
        if (!qRootText || !Array.isArray(ranges) || !ranges.length) {
          return null;
        }
        const rootText = questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
        const lines = Array.from(qRootText.querySelectorAll(".ft-q-root-line"));
        const rects = [];
        let lineStart = 0;
        preserveQuestionText(rootText).split("\n").forEach((line, lineIndex) => {
          const lineNode = lines[lineIndex];
          const lineEnd = lineStart + line.length;
          if (lineNode) {
            ranges.forEach((range) => {
              if (!range || range.start >= lineEnd || range.end <= lineStart) {
                return;
              }
              const localStart = Math.max(0, range.start - lineStart);
              const localEnd = Math.min(line.length, range.end - lineStart);
              const rect = questionTextRangeClientRect(lineNode, localStart, localEnd);
              if (rect) {
                rects.push(rect);
              }
            });
          }
          lineStart = lineEnd + 1;
        });
        return questionUnionClientRects(rects);
      };

      const questionRectCameraTarget = (rect) => (
        rect && rect.width > 0 && rect.height > 0
          ? { getBoundingClientRect: () => rect }
          : null
      );

      const questionRootPromptOverviewCameraTarget = () => {
        if (!qRootCard || !stageNode || !shellNode) {
          return qRootCard || qQuestionCard || questionRootInfoCard;
        }
        return {
          getBoundingClientRect: () => {
            const rects = [];
            const rootRect = qRootCard.getBoundingClientRect();
            if (rootRect && rootRect.width > 0 && rootRect.height > 0) {
              rects.push(rootRect);
            }
            if (qQuestionCard && isQuestionCardInLayout(qQuestionCard)) {
              const questionRect = qQuestionCard.getBoundingClientRect();
              if (questionRect.width > 0 && questionRect.height > 0) {
                rects.push(questionRect);
              }
            }
            if (questionRootInfoCard && (questionRootInfoCard.classList.contains("is-live") || questionRootInfoCard.classList.contains("is-preparing"))) {
              const infoRect = questionRootInfoCard.getBoundingClientRect();
              if (infoRect.width > 0 && infoRect.height > 0) {
                rects.push(infoRect);
              }
            }
            if (questionPictureAnswerLayer) {
              Array.from(questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card.is-live, .ft-q-picture-answer-card.is-preparing")).forEach((node) => {
                const answerRect = node.getBoundingClientRect();
                if (answerRect.width > 0 && answerRect.height > 0) {
                  rects.push(answerRect);
                }
              });
            }
            if (questionSplitDesktopLayoutActive()) {
              const split = questionSplitLayoutMetrics();
              const shellRect = shellNode.getBoundingClientRect();
              const scale = questionResponsiveLayoutScale();
              if (split && shellRect.width > 0 && rootRect && rootRect.width > 0) {
                const laneLeft = shellRect.left + split.rightLeft * scale;
                const laneWidth = split.rightWidth * scale;
                const stageHeight = stageNode.clientHeight || window.innerHeight || 720;
                const laneHeight = Math.max(240, Math.min(stageHeight * 0.78, Math.max(rootRect.height, 360)));
                rects.push({
                  left: laneLeft,
                  top: rootRect.top,
                  right: laneLeft + laneWidth,
                  bottom: rootRect.top + laneHeight,
                  x: laneLeft,
                  y: rootRect.top,
                  width: laneWidth,
                  height: laneHeight,
                });
              }
            }
            const bounds = questionUnionClientRects(rects);
            if (!bounds) {
              return rootRect && rootRect.width > 0
                ? rootRect
                : { left: 0, top: 0, right: 1, bottom: 1, width: 1, height: 1 };
            }
            const pad = questionSplitDesktopLayoutActive() ? 14 : 8;
            return {
              left: bounds.left - pad,
              top: bounds.top,
              right: bounds.right + pad,
              bottom: bounds.bottom,
              x: bounds.left - pad,
              y: bounds.top,
              width: Math.max(1, bounds.right - bounds.left + pad * 2),
              height: Math.max(1, bounds.bottom - bounds.top),
            };
          },
        };
      };

      const questionRootHighlightCameraTarget = (ranges = [], options = {}) => {
        if (!options.forceRange && questionRootCardFitsStageView()) {
          return qRootCard;
        }
        return {
          getBoundingClientRect: () => {
            const rect = questionRootHighlightFocusRect(ranges);
            if (rect && rect.width > 0 && rect.height > 0) {
              return rect;
            }
            const fallback = questionRootHighlightFocusNode(ranges) || qRootCard;
            return fallback && typeof fallback.getBoundingClientRect === "function"
              ? fallback.getBoundingClientRect()
              : { left: 0, top: 0, right: 1, bottom: 1, width: 1, height: 1 };
          },
        };
      };

      const waitQuestionRootHighlightRangesBeforePrompt = (item, ranges = [], onDone, options = {}) => {
        const safeRanges = Array.isArray(ranges) ? ranges : [];
        const rangeSignature = questionRootHighlightRangesSignature(safeRanges);
        const fastRepeatHighlight = Boolean(
          rangeSignature
          && questionCurrentNode
          && questionRootHighlightLastNode === questionCurrentNode
          && questionRootHighlightLastSignature === rangeSignature
        );
        const hasNotice = questionRootNoticeAvailable(item);
        const keepHighlightInRootPromptOverview = Boolean(
          safeRanges.length
          && questionSplitDesktopLayoutActive()
          && options.keepRootPromptOverview !== false
        );
        const shouldFocusHighlight = !keepHighlightInRootPromptOverview && Boolean(safeRanges.length) && (
          fastRepeatHighlight || options.focus === true || (
            options.focus !== false && questionItemShouldFocusHighlights(item, safeRanges)
          )
        );
        const highlightFocusToken = shouldFocusHighlight ? beginQuestionHighlightCameraFocus() : 0;
        stopQuestionRootNotice();
        if (fastRepeatHighlight) {
          const rootText = options.rootText || questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
          if (qRootText) {
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: safeRanges });
            attachQuestionRootHighlightEvents();
          }
          showQuestionRootPictureQuestionBubble(item, safeRanges);
          if (hasNotice) {
            showQuestionRootNotice(item).then((shown) => {
              const settleMs = shown ? QUESTION_ROOT_NOTICE_AFTER_MS : 0;
              window.setTimeout(() => {
                endQuestionHighlightCameraFocus(highlightFocusToken);
                questionRootHighlightLastSignature = rangeSignature;
                questionRootHighlightLastNode = questionCurrentNode || null;
                if (typeof onDone === "function") {
                  onDone();
                }
              }, settleMs);
            });
          } else {
            endQuestionHighlightCameraFocus(highlightFocusToken);
            questionRootHighlightLastSignature = rangeSignature;
            questionRootHighlightLastNode = questionCurrentNode || null;
            if (typeof onDone === "function") {
              window.requestAnimationFrame(onDone);
            }
          }
          return true;
        }
        const finishAfterHighlight = () => {
          const finishAfterNotice = () => {
            questionRootNoticeCompletionTimer = 0;
            stopQuestionRootNotice();
            endQuestionHighlightCameraFocus(highlightFocusToken);
            if (rangeSignature) {
              questionRootHighlightLastSignature = rangeSignature;
              questionRootHighlightLastNode = questionCurrentNode || null;
            }
            if (typeof onDone === "function") {
              onDone();
            }
          };
          if (!hasNotice) {
            finishAfterNotice();
            return;
          }
          showQuestionRootNotice(item).then((shown) => {
            if (shown) {
              questionRootNoticeCompletionTimer = window.setTimeout(finishAfterNotice, QUESTION_ROOT_NOTICE_AFTER_MS);
            } else {
              finishAfterNotice();
            }
          });
        };
        if (!safeRanges.length) {
          if (!hasNotice) {
            endQuestionHighlightCameraFocus(highlightFocusToken);
            if (typeof onDone === "function") {
              window.requestAnimationFrame(onDone);
            }
            return false;
          }
          finishAfterHighlight();
          return true;
        }
        const runHighlight = () => {
          const highlightPanOptions = options.panOptions && typeof options.panOptions === "object"
            ? { ...options.panOptions }
            : (questionSplitDesktopLayoutActive() ? { allowSplitPan: true } : undefined);
          if (highlightPanOptions && questionSplitDesktopLayoutActive()) {
            highlightPanOptions.allowSplitPan = true;
          }
          applyQuestionRootHighlight(item, finishAfterHighlight, {
            ranges: safeRanges,
            settleMs: fastRepeatHighlight
              ? 0
              : (Number.isFinite(Number(options.settleMs))
                ? Math.max(0, Number(options.settleMs))
                : (shouldFocusHighlight ? QUESTION_HIGHLIGHT_RETURN_DELAY_MS : (hasNotice ? 0 : QUESTION_ROOT_HIGHLIGHT_SETTLE_MS))),
            focusEachRange: shouldFocusHighlight,
            focusAllRanges: options.focus === true,
            panDelayMs: options.panDelayMs,
            panOptions: highlightPanOptions,
            showPictureBubble: options.showPictureBubble,
            fastRepeatHighlight,
          });
        };
        if (keepHighlightInRootPromptOverview) {
          panQuestionCameraTo(questionRootPromptOverviewCameraTarget(), runHighlight, 500, {
            duration: 500,
            allowSplitPan: true,
            forceLayout: true,
            alignY: "top",
            topOffset: 12,
          });
          return true;
        }
        runHighlight();
        if (!shouldFocusHighlight) {
          settleQuestionCardOnlyView([0, 120, 360]);
        }
        return true;
      };

      const waitQuestionRootHighlightBeforePrompt = (item, onDone, options = {}) => (
        waitQuestionRootHighlightRangesBeforePrompt(item, questionRootHighlightRangesForItem(item), onDone, options)
      );

      const showQuestionRootPictureQuestionBubble = (item, ranges = []) => {
        const entry = questionRootPictureQuestionForItem(item, ranges);
        if (!entry || !entry.payload || !entry.payload.text) {
          return false;
        }
        const sourceNode = entry.payload.anchor === "picture" || entry.payload.anchor === "picture_regions"
          ? questionRootPictureAnchorNode()
          : (qRootText && qRootText.querySelector(`[data-qh-index="${entry.sourceIndex}"]`));
        if (entry.payload.anchor === "picture_regions") {
          questionPictureRegionPromptLocked = true;
        }
        showQuestionRootInfo(sourceNode || questionRootPictureAnchorNode(), entry.payload);
        return true;
      };

      const questionLinkingPromptAnchorNode = (entry = null, ranges = []) => {
        const payload = entry && entry.payload && typeof entry.payload === "object" ? entry.payload : {};
        if (payload.anchor === "picture" || payload.anchor === "picture_regions") {
          return questionRootPictureAnchorNode();
        }
        if (payload.anchor === "highlight" && qRootText) {
          const sourceIndex = Math.max(0, Number(entry && entry.sourceIndex) || 0);
          const explicitNode = qRootText.querySelector(`[data-qh-index="${sourceIndex}"]`);
          if (explicitNode) {
            return explicitNode;
          }
          const rangeItems = Array.isArray(ranges) ? ranges : [];
          const matched = rangeItems.find((range) => Math.max(0, Number(range && range.sourceIndex) || 0) === sourceIndex);
          return questionRootHighlightFocusNode(matched ? [matched] : rangeItems) || qRootCard || qRootText;
        }
        return qRootCard || qRootText || questionRootPictureAnchorNode();
      };

      const setQuestionAnswerControls = (locked) => {
        if (qAnswerInput) {
          qAnswerInput.disabled = Boolean(locked);
        }
        if (qCheckButton) {
          qCheckButton.disabled = Boolean(locked);
        }
        if (qChoiceList) {
          qChoiceList.querySelectorAll("button").forEach((button) => {
            button.disabled = Boolean(locked) && !button.classList.contains("has-guidance-children");
          });
        }
      };

      const preparePictureRegionQuestionPrompt = () => {
        const item = currentQuestionItem();
        const ranges = questionRootHighlightRangesForItem(item);
        const entry = questionLinkingQuestionEntryForItem(item, ranges);
        if (!entry || !entry.payload || !entry.payload.text) {
          return false;
        }
        hideQuestionPictureAnswerCards();
        questionPictureRegionPromptLocked = true;
        if (qQuestionCard) {
          qQuestionCard.classList.remove("is-live", "is-preparing", "is-connector-focused", "is-input-question", "is-select-target-card");
        }
        if (qConnectorQuestion) {
          qConnectorQuestion.classList.remove("is-live", "is-focused");
        }
        if (qChoiceList) {
          qChoiceList.innerHTML = "";
          qChoiceList.classList.remove("is-picture-question-branch", "is-select-token-grid");
        }
        if (qInputRow) {
          qInputRow.classList.remove("is-picture-question-block");
        }
        clearQuestionInputAccent();
        setQuestionAnswerFeedback("");
        prepareQuestionRootInfo(questionLinkingPromptAnchorNode(entry, ranges), entry.payload);
        const guide = isQuestionGuideItem(item);
        renderQuestionPictureAnswerCards(item, {
          prepareOnly: true,
          guide,
          locked: guide,
          nextEnabled: guide,
        });
        positionQuestionSideCards();
        repositionActiveQuestionRootInfo();
        positionQuestionPictureAnswerCards();
        return true;
      };

      const showPictureRegionQuestionPrompt = (item = currentQuestionItem(), ranges = []) => {
        const safeRanges = Array.isArray(ranges) && ranges.length ? ranges : questionRootHighlightRangesForItem(item);
        const entry = questionLinkingQuestionEntryForItem(item, safeRanges);
        if (!entry || !entry.payload || !entry.payload.text) {
          return false;
        }
        ensureQuestionAttemptRewardKey(item);
        questionPictureRegionPromptLocked = true;
        if (qQuestionCard) {
          qQuestionCard.classList.remove("is-live", "is-preparing", "is-connector-focused", "is-input-question", "is-select-target-card");
        }
        if (qConnectorQuestion) {
          qConnectorQuestion.classList.remove("is-live", "is-focused");
        }
        const activePayload = questionRootInfoActivePayload && typeof questionRootInfoActivePayload === "object"
          ? questionRootInfoActivePayload
          : null;
        const alreadyShowingPrompt = Boolean(
          questionRootInfoCard
          && questionRootInfoCard.classList.contains("is-live")
          && activePayload
          && activePayload.anchor === "picture_regions"
          && preserveQuestionText(activePayload.text) === preserveQuestionText(entry.payload.text)
          && optionalQuestionPictureRegionColor(activePayload.region_color ?? activePayload.regionColor ?? activePayload.color ?? activePayload.c) === optionalQuestionPictureRegionColor(entry.payload.region_color ?? entry.payload.regionColor ?? entry.payload.color ?? entry.payload.c)
          && JSON.stringify(normalizeQuestionPictureRegions(activePayload.regions || [])) === JSON.stringify(normalizeQuestionPictureRegions(entry.payload.regions || []))
        );
        if (alreadyShowingPrompt) {
          repositionActiveQuestionRootInfo();
        } else {
          showQuestionRootInfo(questionLinkingPromptAnchorNode(entry, safeRanges), entry.payload);
        }
        const guide = isQuestionGuideItem(item);
        const typed = isQuestionTypedItem(item);
        const optionValues = activatePreparedQuestionPictureAnswerCards(item, {
          guide,
          locked: guide,
          nextEnabled: guide,
        });
        if (typed && questionPictureAnswerLayer) {
          focusQuestionTypingInput(questionPictureAnswerLayer.querySelector(".ft-q-picture-answer-input"), {
            item,
            pictureInput: true,
            delays: isQuestionMobileFlow() ? [0, 70, 180, 360] : [80, 180],
          });
        }
        autoplayQuestionItemAudio(item, optionValues);
        scheduleQuestionSideLayout();
        settleQuestionPictureRegionPrompt();
        return true;
      };

      const questionPictureRegionCameraTarget = () => {
        const nodes = questionPictureRegionLayer
          ? Array.from(questionPictureRegionLayer.querySelectorAll(".ft-q-picture-region"))
          : [];
        const rects = nodes
          .map((node) => node.getBoundingClientRect())
          .filter((rect) => rect && rect.width > 0 && rect.height > 0);
        if (!rects.length) {
          return qPictureCard && qPictureCard.classList.contains("is-live") ? qPictureCard : questionRootPictureAnchorNode();
        }
        if (rects.length === 1) {
          return nodes[0];
        }
        const left = Math.min(...rects.map((rect) => rect.left));
        const top = Math.min(...rects.map((rect) => rect.top));
        const right = Math.max(...rects.map((rect) => rect.right));
        const bottom = Math.max(...rects.map((rect) => rect.bottom));
        return {
          getBoundingClientRect: () => ({
            left,
            top,
            right,
            bottom,
            width: Math.max(1, right - left),
            height: Math.max(1, bottom - top),
          }),
        };
      };

      const questionPicturePromptCameraTarget = () => (
        questionRootInfoCard && questionRootInfoCard.classList.contains("is-live")
          ? questionRootInfoCard
          : (qPictureCard && qPictureCard.classList.contains("is-live") ? qPictureCard : questionRootPictureAnchorNode())
      );

      const questionPicturePromptAnswerCameraTarget = () => {
        const nodes = [];
        if (questionRootInfoCard && (questionRootInfoCard.classList.contains("is-live") || questionRootInfoCard.classList.contains("is-preparing"))) {
          nodes.push(questionRootInfoCard);
        }
        if (questionPictureAnswerLayer) {
          nodes.push(...Array.from(questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card.is-live, .ft-q-picture-answer-card.is-preparing")));
        }
        const bounds = questionGeometryBounds(nodes);
        if (!bounds) {
          return questionPicturePromptCameraTarget();
        }
        const left = bounds.left;
        const top = bounds.top;
        const right = bounds.right;
        const bottom = bounds.bottom;
        return {
          getBoundingClientRect: () => ({
            left,
            top,
            right,
            bottom,
            width: Math.max(1, right - left),
            height: Math.max(1, bottom - top),
          }),
        };
      };

      const runPictureRegionQuestionRevealSequence = (item = currentQuestionItem(), ranges = []) => {
        const safeRanges = Array.isArray(ranges) && ranges.length ? ranges : questionRootHighlightRangesForItem(item);
        const entry = questionLinkingQuestionEntryForItem(item, safeRanges);
        if (!entry || !entry.payload || !entry.payload.text) {
          return false;
        }
        const regionMode = entry.payload.anchor === "picture_regions";
        const node = questionCurrentNode;
        if (isQuestionMobileFlow()) {
          const token = ++questionRevealToken;
          beginQuestionRevealAnimationOverride();
          setQuestionRevealAnimationsActive(false);
          if (!preparePictureRegionQuestionPrompt()) {
            endQuestionRevealAnimationOverride({ discharge: false });
            return false;
          }
          if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
            return false;
          }
          showPictureRegionQuestionPrompt(item, safeRanges);
          scheduleQuestionSideLayout(1);
          scheduleQuestionMobilePanelsSync("question");
          endQuestionRevealAnimationOverride({ discharge: false });
          updateQuestionRootNoticeReplayButton();
          return true;
        }
        const token = ++questionRevealToken;
        beginQuestionRevealAnimationOverride();
        setQuestionRevealAnimationsActive(true);
        if (!preparePictureRegionQuestionPrompt()) {
          setQuestionRevealAnimationsActive(false);
          endQuestionRevealAnimationOverride({ discharge: true });
          return false;
        }
        positionQuestionSideCards();
        repositionActiveQuestionRootInfo();
        positionQuestionPictureAnswerCards();
        const hasPictureRegions = regionMode && normalizeQuestionPictureRegions(entry.payload.regions || []).length > 0;
        const shouldFocusRegion = Boolean(hasPictureRegions);
        const regionFocusToken = shouldFocusRegion ? beginQuestionHighlightCameraFocus() : 0;

        const finishSequence = () => {
          if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
            endQuestionHighlightCameraFocus(regionFocusToken);
            return;
          }
          questionRevealTimer = window.setTimeout(() => {
            if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
              endQuestionHighlightCameraFocus(regionFocusToken);
              return;
            }
            questionRevealTimer = 0;
            endQuestionHighlightCameraFocus(regionFocusToken);
            setQuestionRevealAnimationsActive(false);
            endQuestionRevealAnimationOverride({ discharge: true });
            updateQuestionRootNoticeReplayButton();
          }, 620);
        };

        const showPrompt = () => {
          if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
            return;
          }
          startQuestionPicturePromptStartupSequence(token);
          showPictureRegionQuestionPrompt(item, safeRanges);
        };

        const showPromptAndReturn = () => {
          const startPromptAfterAnchorScan = () => {
            showPrompt();
            window.setTimeout(() => {
              if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                endQuestionHighlightCameraFocus(regionFocusToken);
                return;
              }
              positionQuestionSideCards();
              repositionActiveQuestionRootInfo();
              positionQuestionPictureAnswerCards();
              const promptTarget = questionPicturePromptCameraTarget();
              panQuestionCameraTo(promptTarget, () => {
                if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                  endQuestionHighlightCameraFocus(regionFocusToken);
                  return;
                }
                window.setTimeout(() => {
                  if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                    endQuestionHighlightCameraFocus(regionFocusToken);
                    return;
                  }
                  positionQuestionPictureAnswerCards();
                  panQuestionCameraTo(questionPicturePromptAnswerCameraTarget(), finishSequence, 620, {
                    duration: 620,
                  });
                }, 220);
              }, 500, {
                duration: 500,
              });
            }, shouldFocusRegion ? 500 : 120);
          };
          if (hasPictureRegions) {
            renderQuestionPictureRegions(entry.payload.regions || []);
            window.setTimeout(startPromptAfterAnchorScan, shouldFocusRegion ? 300 : 120);
            return;
          }
          startPromptAfterAnchorScan();
        };

        if (shouldFocusRegion) {
          renderQuestionPictureRegions(entry.payload.regions || []);
          window.requestAnimationFrame(() => {
            if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
              endQuestionHighlightCameraFocus(regionFocusToken);
              return;
            }
            panQuestionCameraTo(() => {
              renderQuestionPictureRegions(entry.payload.regions || []);
              return questionPictureRegionCameraTarget();
            }, showPromptAndReturn, 500, {
              duration: 500,
              forceLayout: true,
            });
          });
        } else {
          showPromptAndReturn();
        }
        return true;
      };
