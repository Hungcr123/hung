

      const questionSelectTargetCameraTarget = (item = currentQuestionItem()) => {
        if (!item || !isQuestionSelectItem(item)) {
          return null;
        }
        const ranges = questionRootHighlightRangesForItem(item);
        if (ranges.length) {
          return questionRootHighlightCameraTarget(ranges, { forceRange: true }) || qRootCard || qRootText;
        }
        const targets = questionSelectTargets(item);
        if (targets.regions.length && qPictureCard && qPictureCard.classList.contains("is-live")) {
          return questionPictureRegionCameraTarget();
        }
        return qRootCard || qRootText || qPictureCard;
      };

      const scheduleQuestionSelectTargetView = (item = currentQuestionItem(), delayMs = 2000) => {
        if (!item || !isQuestionSelectItem(item) || isQuestionMobileFlow()) {
          return;
        }
        const token = questionCardOnlyViewToken;
        const timer = window.setTimeout(() => {
          questionCardOnlyViewTimers.delete(timer);
          if (
            token !== questionCardOnlyViewToken
            || questionHighlightCameraFocusToken
            || !questionModeActive
            || currentQuestionItem() !== item
          ) {
            return;
          }
          const target = questionSelectTargetCameraTarget(item);
          if (!target) {
            return;
          }
          panQuestionCameraTo(target, () => {
            if (questionModeActive && currentQuestionItem() === item) {
              hideQuestionSelectConnectors();
            }
          }, 760, {
            duration: 760,
            forceLayout: true,
          });
        }, Math.max(0, Number(delayMs) || 0));
        questionCardOnlyViewTimers.add(timer);
      };

      const applyQuestionRootHighlight = (item, onDone = null, options = {}) => {
        let latestRanges = Array.isArray(options.ranges) ? options.ranges : [];
        const finishHighlight = () => {
          if (!options || options.showPictureBubble !== false) {
            showQuestionRootPictureQuestionBubble(item, latestRanges);
          }
          if (typeof onDone === "function") {
            const settleMs = Math.max(0, Number.isFinite(Number(options.settleMs))
              ? Number(options.settleMs)
              : (isQuestionMobileFlow() ? 0 : (latestRanges.length ? QUESTION_ROOT_HIGHLIGHT_SETTLE_MS : 0)));
            window.setTimeout(onDone, settleMs);
          }
        };
        if (!qRootText) {
          finishHighlight();
          return;
        }
        const rootText = options.rootText || questionTypingFullText || preserveQuestionText(questionCurrentNode && (questionCurrentNode.root || (questionCardData(questionCurrentNode, "root") || {}).text));
        const highlights = item && Array.isArray(item.root_highlights) ? item.root_highlights : [];
        const ranges = latestRanges.length
          ? latestRanges
          : questionRootHighlightRanges(rootText, highlights, item && item.question)
            .sort((left, right) => left.start - right.start || left.end - right.end);
        latestRanges = ranges;
        stopQuestionRootHighlightAnimation();
        hideQuestionRootInfo();
        if (!ranges.length) {
          qRootText.innerHTML = renderQuestionRootMarkup(rootText);
          attachQuestionRootHighlightEvents();
          finishHighlight();
          return;
        }
        if (isQuestionMobileFlow()) {
          qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges });
          attachQuestionRootHighlightEvents();
          finishHighlight();
          return;
        }
        const steps = questionRootHighlightSteps(ranges);
        if (!steps.length) {
          qRootText.innerHTML = renderQuestionRootMarkup(rootText);
          attachQuestionRootHighlightEvents();
          finishHighlight();
          return;
        }
        const cometTracks = questionRootHighlightCometTracks(ranges, rootText);
        const highlightCometTracks = cometTracks.length
          ? cometTracks
          : steps.map((step) => ({ start: step.index, end: step.index + 1, color: step.color }));
        const highlightBatchCount = Math.max(1, questionRootHighlightBatchesFor(highlightCometTracks).length);
        const token = ++questionRootHighlightToken;
        const sortedRanges = ranges
          .slice()
          .sort((left, right) => left.start - right.start || left.end - right.end);
        let lastHighlightScrollKey = "";
        const scrollToActiveHighlight = (range) => {
          if (!range) {
            return;
          }
          const key = `${Math.floor(Number(range.start) || 0)}:${Math.floor(Number(range.end) || 0)}:${Math.floor(Number(range.index) || -1)}`;
          if (key === lastHighlightScrollKey) {
            return;
          }
          lastHighlightScrollKey = key;
          scrollQuestionRootTextToRange(range, "auto");
        };
        if (options.fastRepeatHighlight) {
          const completeFastHighlight = () => {
            if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
              return;
            }
            qRootText.classList.add("is-fast-repeat-highlight");
            const totalBudgetMs = questionRootHighlightScanDurationMs(highlightCometTracks, { fast: true }) + 90;
            const settleMs = 70;
            const scanDurationMs = Math.max(320, totalBudgetMs - settleMs);
            const scanStartedAt = performance.now();
            let lastPaintBucket = -1;
            const paintFast = () => {
              if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
                return;
              }
              const elapsedMs = Math.max(0, performance.now() - scanStartedAt);
              const ratio = Math.min(1, elapsedMs / scanDurationMs);
              const paintBucket = Math.floor(ratio * QUESTION_ROOT_HIGHLIGHT_PAINT_BUCKETS);
              if (paintBucket !== lastPaintBucket || ratio >= 1) {
                const batchState = questionRootHighlightBatchStateAt(highlightCometTracks, ratio);
                const activeSteps = batchState.activeSteps;
                const activeStep = batchState.activeStep || steps[Math.min(steps.length - 1, Math.floor(ratio * steps.length))] || steps[0];
                scrollToActiveHighlight(activeStep);
                qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], {
                  ranges: batchState.visibleRanges,
                  activeSteps,
                  activeColor: activeStep.color,
                });
                lastPaintBucket = paintBucket;
              }
              if (ratio >= 1) {
                questionRootHighlightTimer = window.setTimeout(() => {
                  if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
                    return;
                  }
                  qRootText.classList.remove("is-fast-repeat-highlight");
                  qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges });
                  attachQuestionRootHighlightEvents();
                  questionRootHighlightTimer = 0;
                  finishHighlight();
                }, settleMs);
                return;
              }
              questionRootHighlightTimer = window.setTimeout(paintFast, QUESTION_ROOT_HIGHLIGHT_FRAME_MS);
            };
            paintFast();
          };
          const firstRange = sortedRanges[0];
          if (options.focusEachRange && firstRange && questionRootHighlightRangeShouldFocus(item, firstRange, options)) {
            scrollQuestionRootTextToRange(firstRange, "auto");
            const focusTarget = questionRootHighlightCameraTarget(sortedRanges, { forceRange: true }) || qRootCard || qRootText;
            if (focusTarget) {
              const panDelayMs = Math.max(0, Number.isFinite(Number(options.panDelayMs))
                ? Number(options.panDelayMs)
                : 520);
              const panOptions = options.panOptions && typeof options.panOptions === "object"
                ? options.panOptions
                : { duration: 420 };
              panQuestionCameraTo(focusTarget, completeFastHighlight, panDelayMs, panOptions);
              return;
            }
          }
          completeFastHighlight();
          return;
        }
        if (options.focusEachRange) {
          const parallelPanDelayMs = Math.max(0, Number.isFinite(Number(options.panDelayMs))
            ? Number(options.panDelayMs)
            : QUESTION_HIGHLIGHT_PAN_SETTLE_MS + QUESTION_HIGHLIGHT_PAN_BEFORE_SCAN_DELAY_MS + 140);
          const parallelPanOptions = options.panOptions && typeof options.panOptions === "object"
            ? options.panOptions
            : { duration: QUESTION_HIGHLIGHT_PAN_SETTLE_MS };
          const runParallelFocusScan = () => {
            if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
              return;
            }
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: [] });
            const scanDurationMs = questionRootHighlightScanDurationMs(highlightCometTracks, { focus: true });
            const startedAt = performance.now();
            let lastPaintBucket = -1;
            const paintParallel = () => {
              if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
                return;
              }
              const ratio = Math.min(1, Math.max(0, (performance.now() - startedAt) / scanDurationMs));
              const paintBucket = Math.floor(ratio * QUESTION_ROOT_HIGHLIGHT_PAINT_BUCKETS);
              if (paintBucket !== lastPaintBucket || ratio >= 1) {
                const batchState = questionRootHighlightBatchStateAt(highlightCometTracks, ratio);
                const activeSteps = batchState.activeSteps;
                const activeStep = batchState.activeStep || steps[Math.min(steps.length - 1, Math.floor(ratio * steps.length))] || steps[0];
                scrollToActiveHighlight(activeStep);
                qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], {
                  ranges: batchState.visibleRanges,
                  activeSteps,
                  activeColor: activeStep.color,
                });
                lastPaintBucket = paintBucket;
              }
              if (ratio >= 1) {
                questionRootHighlightTimer = 0;
                qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges });
                attachQuestionRootHighlightEvents();
                finishHighlight();
                return;
              }
              questionRootHighlightTimer = window.setTimeout(paintParallel, QUESTION_ROOT_HIGHLIGHT_FRAME_MS);
            };
            questionRootHighlightTimer = window.setTimeout(paintParallel, 80);
          };
          const shouldPanToHighlights = sortedRanges.some((range) => questionRootHighlightRangeShouldFocus(item, range, options));
          if (shouldPanToHighlights) {
            scrollQuestionRootTextToRange(sortedRanges[0], "auto");
            const focusTarget = questionRootHighlightCameraTarget(sortedRanges, { forceRange: true }) || qRootCard || qRootText;
            if (focusTarget) {
              panQuestionCameraTo(focusTarget, runParallelFocusScan, parallelPanDelayMs, parallelPanOptions);
              return;
            }
          }
          runParallelFocusScan();
          return;
          const completedRanges = [];
          let rangeIndex = 0;
          const panDelayMs = Math.max(0, Number.isFinite(Number(options.panDelayMs))
            ? Number(options.panDelayMs)
            : QUESTION_HIGHLIGHT_PAN_SETTLE_MS + QUESTION_HIGHLIGHT_PAN_BEFORE_SCAN_DELAY_MS + 140);
          const panOptions = options.panOptions && typeof options.panOptions === "object"
            ? options.panOptions
            : { duration: QUESTION_HIGHLIGHT_PAN_SETTLE_MS };
          qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: [] });
          const finishSequence = () => {
            if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
              return;
            }
            questionRootHighlightTimer = 0;
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges });
            attachQuestionRootHighlightEvents();
            finishHighlight();
          };
          const runNextRange = () => {
            if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
              return;
            }
            if (rangeIndex >= sortedRanges.length) {
              finishSequence();
              return;
            }
            const activeRange = sortedRanges[rangeIndex];
            rangeIndex += 1;
            if (!activeRange || activeRange.end <= activeRange.start) {
              runNextRange();
              return;
            }
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: completedRanges });
            let visibleInRange = 0;
            const rangeLength = Math.max(0, activeRange.end - activeRange.start);
            const paintRange = () => {
              if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
                return;
              }
              visibleInRange = Math.min(rangeLength, visibleInRange + 1);
              const activeIndex = Math.max(activeRange.start, activeRange.start + visibleInRange - 1);
              const partialRange = {
                ...activeRange,
                end: activeRange.start + visibleInRange,
              };
              qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], {
                ranges: completedRanges.concat(partialRange),
                activeIndex,
                activeColor: activeRange.color,
              });
              if (visibleInRange === 1 || visibleInRange % 12 === 0) {
                scrollQuestionRootTextToRange(partialRange, "auto");
              }
              if (visibleInRange >= rangeLength) {
                completedRanges.push(activeRange);
                qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: completedRanges });
                questionRootHighlightTimer = window.setTimeout(runNextRange, 240);
                return;
              }
              questionRootHighlightTimer = window.setTimeout(paintRange, 18);
            };
            const startPaint = () => {
              if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
                return;
              }
              questionRootHighlightTimer = window.setTimeout(paintRange, 80);
            };
            if (questionRootHighlightRangeShouldFocus(item, activeRange, options)) {
              scrollQuestionRootTextToRange(activeRange, "auto");
              const focusTarget = questionRootHighlightCameraTarget([activeRange], { forceRange: true }) || qRootCard || qRootText;
              if (focusTarget) {
                panQuestionCameraTo(focusTarget, startPaint, panDelayMs, panOptions);
                return;
              }
            }
            startPaint();
          };
          runNextRange();
          return;
        }
        const scanDurationMs = questionRootHighlightScanDurationMs(highlightCometTracks);
        const scanStartedAt = performance.now();
        let lastPaintBucket = -1;
        qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges: [] });
        const paint = () => {
          if (token !== questionRootHighlightToken || !questionModeActive || !qRootText) {
            return;
          }
          const ratio = Math.min(1, Math.max(0, (performance.now() - scanStartedAt) / scanDurationMs));
          const paintBucket = Math.floor(ratio * QUESTION_ROOT_HIGHLIGHT_PAINT_BUCKETS);
          if (paintBucket !== lastPaintBucket || ratio >= 1) {
            const batchState = questionRootHighlightBatchStateAt(highlightCometTracks, ratio);
            const activeSteps = batchState.activeSteps;
            const activeStep = batchState.activeStep || steps[Math.min(steps.length - 1, Math.floor(ratio * steps.length))] || steps[0];
            scrollToActiveHighlight(activeStep);
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], {
              ranges: batchState.visibleRanges,
              activeSteps,
              activeColor: activeStep.color,
            });
            lastPaintBucket = paintBucket;
          }
          if (ratio >= 1) {
            questionRootHighlightTimer = 0;
            qRootText.innerHTML = renderQuestionRootMarkup(rootText, [], { ranges });
            attachQuestionRootHighlightEvents();
            finishHighlight();
            return;
          }
          questionRootHighlightTimer = window.setTimeout(paint, QUESTION_ROOT_HIGHLIGHT_FRAME_MS);
        };
        questionRootHighlightTimer = window.setTimeout(paint, 80);
      };

      const showQuestionItem = (options = {}) => {
        const item = currentQuestionItem();
        clearQuestionCardRevealSequence();
        endQuestionHighlightCameraFocus();
        clearQuestionCardOnlyViewTimers();
        updateQuestionRootNoticeReplayButton();
        clearQuestionAdvanceTimer();
        stopGrammarAudio();
        hideQuestionInfoCard();
        hideQuestionRootHoverInfo();
        hideQuestionRootInfo(true);
        clearQuestionSelectCompletionState();
        clearQuestionSelectTargets();
        clearQuestionGuidanceBranches(1);
        questionGuidanceNodeMap.clear();
        questionGuidanceUnlockedPaths.clear();
        questionGuidanceUnlockedAnswerIndex.clear();
        questionGuidanceUnlockedAnswerValue.clear();
        questionGuidancePinnedPaths.clear();
        clearQuestionInputBranchTrigger();
        questionWrongAttempts = 0;
        ensureQuestionAttemptRewardKey(item);
        setQuestionAnswerControls(false);
        setQuestionAnswerFeedback("");
        if (qShowAnswerButton) {
          qShowAnswerButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qNextButton) {
          qNextButton.disabled = true;
        }
        updateQuestionProgressLabel();
        if (qQuestionAudioButton) {
          qQuestionAudioButton.classList.add("ft-q-show-answer-hidden");
        }
        if (!item) {
          clearQuestionInputAccent();
          if (qQuestionCard) {
            qQuestionCard.classList.remove("is-input-question", "is-select-target-card");
          }
          setQuestionFeedback("Node complete. Moving to the next root.", "ok");
          window.setTimeout(() => {
            if (questionModeActive) {
              showNextQuestionNode();
            }
          }, 720);
          return;
        }
        const linkingPromptRanges = questionRootHighlightRangesForItem(item);
        const linkingQuestionEntry = questionLinkingQuestionEntryForItem(item, linkingPromptRanges);
        const usesLinkingQuestionPrompt = Boolean(linkingQuestionEntry);
        if (usesLinkingQuestionPrompt) {
          // Added 2026-07-07: linking/picture-region prompts own the visible question layer, so do not flash the previous question card.
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
          const revealLinkingQuestionPrompt = () => {
            runPictureRegionQuestionRevealSequence(item, linkingPromptRanges);
          };
          if (!options || !options.skipRootHighlight) {
            waitQuestionRootHighlightRangesBeforePrompt(item, linkingPromptRanges, revealLinkingQuestionPrompt, {
              focus: true,
              showPictureBubble: false,
              settleMs: 500,
              panOptions: { duration: 900 },
            });
          } else {
            revealLinkingQuestionPrompt();
          }
          return;
        }
        hideQuestionPictureAnswerCards();
        const pendingRootHighlightRanges = (!options || !options.skipRootHighlight)
          ? questionRootHighlightRangesForItem(item)
          : [];
        const pendingRootNotice = (!options || !options.skipRootHighlight)
          ? questionRootNoticeAvailable(item)
          : false;
        const pendingRootHighlightSignature = questionRootHighlightRangesSignature(pendingRootHighlightRanges);
        const pendingRootHighlightFastRepeat = Boolean(
          pendingRootHighlightSignature
          && questionCurrentNode
          && questionRootHighlightLastNode === questionCurrentNode
          && questionRootHighlightLastSignature === pendingRootHighlightSignature
        );
        const deferQuestionCardForRootPrelude = Boolean(
          pendingRootNotice
          || (pendingRootHighlightRanges.length && (pendingRootHighlightFastRepeat || questionItemShouldFocusHighlights(item, pendingRootHighlightRanges)))
        );
        const revealDeferredQuestionCard = () => {
          if (!deferQuestionCardForRootPrelude) {
            return;
          }
          if (qQuestionCard) {
            qQuestionCard.classList.add("is-live");
            qQuestionCard.classList.remove("is-preparing");
          }
          if (qConnectorQuestion) {
            qConnectorQuestion.classList.add("is-live");
          }
          positionQuestionSideCards({ force: true });
          scheduleQuestionSideLayout();
        };
        if (qQuestionCard) {
          qQuestionCard.classList.toggle("is-live", !deferQuestionCardForRootPrelude);
          qQuestionCard.classList.toggle("is-preparing", deferQuestionCardForRootPrelude);
        }
        if (qConnectorQuestion) {
          qConnectorQuestion.classList.toggle("is-live", !deferQuestionCardForRootPrelude);
        }
        if (qQuestionCount) {
          qQuestionCount.textContent = `${questionQuestionIndex + 1} / ${questionCurrentQuestions.length}`;
        }
        if (qQuestionText) {
          qQuestionText.textContent = item.question;
        }
        const renderDeferredSelectTargets = () => {
          if (questionModeActive && currentQuestionItem() === item) {
            renderQuestionSelectTargetsForItem(item);
          }
        };
        let rootHighlightQueued = false;
        if ((!options || !options.skipRootHighlight) && (pendingRootHighlightRanges.length || pendingRootNotice)) {
          if (deferQuestionCardForRootPrelude) {
            rootHighlightQueued = waitQuestionRootHighlightRangesBeforePrompt(item, pendingRootHighlightRanges, () => {
              renderDeferredSelectTargets();
              revealDeferredQuestionCard();
              smoothReturnQuestionCardOnlyView(runQuestionCardIntro);
            }, { settleMs: 500 });
          } else {
            waitQuestionRootHighlightRangesBeforePrompt(item, pendingRootHighlightRanges, null, { focus: false, settleMs: 500 });
          }
        }
        const hasPromptAudioButton = shouldQuestionAudioShowButton(item.audio) && questionCardAudioClip(item.audio);
        if (qQuestionAudioButton) {
          qQuestionAudioButton.classList.toggle("ft-q-show-answer-hidden", !hasPromptAudioButton);
        }
        if (qAnswerInput) {
          qAnswerInput.value = "";
          syncQuestionAnswerInputMemory();
          resizeQuestionAnswerInput();
          clearQuestionInputFlare();
        }
        const guide = isQuestionGuideItem(item);
        const typed = isQuestionTypedItem(item);
        const selectTargets = questionSelectTargets(item);
        const selectTargetMode = isQuestionSelectItem(item) && Boolean(selectTargets.root_text || selectTargets.root_ranges.length || selectTargets.regions.length);
        if (qQuestionCard) {
          qQuestionCard.classList.toggle("is-input-question", typed);
          qQuestionCard.classList.toggle("is-select-target-card", selectTargetMode);
        }
        updateQuestionInputLengthRadar(item, typed);
        const pictureQuestionEntry = questionRootPictureQuestionForItem(item, []);
        const hasPictureQuestionBranch = Boolean(pictureQuestionEntry && pictureQuestionEntry.payload && pictureQuestionEntry.payload.text);
        if (qChoiceList) {
          qChoiceList.classList.toggle("is-picture-question-branch", hasPictureQuestionBranch && !typed);
        }
        if (qInputRow) {
          qInputRow.classList.toggle("is-picture-question-block", hasPictureQuestionBranch && typed);
        }
        let optionValues = typed ? [item.answer] : [];
        if (qInputRow) {
          qInputRow.classList.toggle("ft-q-show-answer-hidden", !typed);
        }
        applyQuestionInputAccent(typed);
        if (typed) {
          resizeQuestionAnswerInput();
        }
        if (qChoiceList) {
          qChoiceList.classList.toggle("ft-q-show-answer-hidden", typed);
        }
        if (!typed) {
          optionValues = renderQuestionChoices(item, { guide });
        }
        if (isQuestionSelectItem(item) && !rootHighlightQueued) {
          renderQuestionSelectTargetsForItem(item);
        }
        if (guide && qNextButton) {
          qNextButton.disabled = true;
        }
        if (isQuestionMobileFlow()) {
          if (qQuestionCard) {
            qQuestionCard.classList.remove("is-preparing");
            qQuestionCard.classList.add("is-live");
          }
          if (qConnectorQuestion) {
            qConnectorQuestion.classList.remove("is-live", "is-focused");
          }
          if (guide && qNextButton) {
            qNextButton.disabled = false;
            updateQuestionProgressLabel();
          }
          scheduleQuestionSideLayout(1);
          scheduleQuestionMobilePanelsSync("question");
          if (typed && qAnswerInput) {
            focusQuestionTypingInput(qAnswerInput, {
              item,
              delays: [0, 70, 180, 360],
            });
          }
          autoplayQuestionItemAudio(item, optionValues);
          return;
        }
        primeQuestionCardRevealSequence();
        const finishQuestionCardIntro = () => {
          if (typed) {
            focusQuestionTypingInput(qAnswerInput, {
              item,
              delays: [80, 180],
            });
          }
          if (guide && qNextButton) {
            qNextButton.disabled = false;
            updateQuestionProgressLabel();
          }
          autoplayQuestionItemAudio(item, optionValues);
          if (selectTargetMode) {
            scheduleQuestionSelectTargetView(item, 2000);
          }
        };
        const runQuestionCardIntro = () => {
          if (!runQuestionCardRevealSequence({ onDone: finishQuestionCardIntro })) {
            finishQuestionCardIntro();
          }
        };
        const runQuestionCardIntroImmediately = () => {
          keepQuestionCardOnlyInView({ passes: 1, behavior: "auto", force: true });
          window.requestAnimationFrame(() => {
            if (questionModeActive && currentQuestionItem() === item) {
              runQuestionCardIntro();
            }
          });
        };
        scheduleQuestionSideLayout();
        if (!rootHighlightQueued) {
          revealDeferredQuestionCard();
          runQuestionCardIntroImmediately();
        }
      };

      const advanceQuestionItem = () => {
        clearQuestionAdvanceTimer();
        endQuestionHighlightCameraFocus();
        clearQuestionCardOnlyViewTimers();
        clearQuestionManualFocusTimer();
        questionPictureRegionPromptLocked = false;
        if (qNextButton) {
          qNextButton.disabled = true;
        }
        questionQuestionIndex += 1;
        updateQuestionProgressLabel();
        queueQuestionProgressSave(120);
        if (questionQuestionIndex >= questionCurrentQuestions.length) {
          setQuestionFeedback("All questions in this node are complete.", "ok");
          window.setTimeout(() => {
            if (questionModeActive) {
              showNextQuestionNode();
            }
          }, 760);
          return;
        }
        warmQuestionAudioCacheForLesson(questionPayload || { nodes: questionNodes, effects: lessonEffects }, {
          startIndex: currentNodeIndex,
          startQuestionIndex: questionQuestionIndex,
          questionOrder: questionCurrentQuestionOrder,
          nodeOrder: [currentNodeIndex, ...questionQueue],
          label: "Space_Q",
          includeEffects: false,
          status: false,
          startDelayMs: 60,
          delayMs: 70,
          workers: 2,
        });
        showQuestionItem();
        queueQuestionProgressSave(180);
      };

      const goQuestionNext = async () => {
        if (qNextButton && qNextButton.disabled) {
          return;
        }
        if (questionNextTransitionActive) {
          return;
        }
        questionNextTransitionActive = true;
        const transitionNode = questionCurrentNode;
        const transitionIndex = questionQuestionIndex;
        if (qNextButton) {
          qNextButton.disabled = true;
        }
        try {
          if (questionExplanationPresentationIsActive()) {
            showQuestionWaitNotice();
            await waitForQuestionExplanationPresentation();
            hideQuestionWaitNotice();
          }
          if (!questionModeActive || questionCurrentNode !== transitionNode || questionQuestionIndex !== transitionIndex) {
            return;
          }
          if (isQuestionMobileFlow()) {
            hideQuestionInfoCard({ immediate: true });
            advanceQuestionItem();
            return;
          }
          await Promise.all([
            runQuestionCardExitSequence(),
            hideQuestionInfoCard({ wait: true }),
          ]);
          if (!questionModeActive || questionCurrentNode !== transitionNode || questionQuestionIndex !== transitionIndex) {
            return;
          }
          advanceQuestionItem();
        } finally {
          hideQuestionWaitNotice();
          questionNextTransitionActive = false;
        }
      };

      const questionNextCanAdvanceFromEnter = () => Boolean(
        questionModeActive
        && qNextButton
        && !qNextButton.disabled
        && !questionNextTransitionActive
      );

      const focusQuestionNextControl = (delayMs = 80) => {
        const focusNow = () => {
          if (!questionModeActive || questionNextTransitionActive) {
            return false;
          }
          const rootInfoNext = questionRootInfoPromptNode("[data-root-info-next]");
          const questionNextVisible = Boolean(
            qNextButton
            && !qNextButton.disabled
            && qQuestionCard
            && isQuestionCardInLayout(qQuestionCard)
          );
          const rootInfoRect = rootInfoNext && rootInfoNext.getBoundingClientRect
            ? rootInfoNext.getBoundingClientRect()
            : null;
          const rootInfoNextVisible = Boolean(
            rootInfoNext
            && !rootInfoNext.disabled
            && rootInfoRect
            && rootInfoRect.width > 0
            && rootInfoRect.height > 0
          );
          const target = questionNextVisible ? qNextButton : (rootInfoNextVisible ? rootInfoNext : null);
          if (!target) {
            return false;
          }
          try {
            target.focus({ preventScroll: true });
          } catch (error) {
            try {
              target.focus();
            } catch (_) {
            }
          }
          if (target === qNextButton && qQuestionCard) {
            activateQuestionCardFx(qQuestionCard, 1400);
          }
          return document.activeElement === target;
        };
        window.requestAnimationFrame(() => {
          if (!focusNow()) {
            window.setTimeout(focusNow, Math.max(0, Number(delayMs) || 0));
          }
        });
      };

      const handleQuestionEnterNext = (event) => {
        if (
          !event
          || event.key !== "Enter"
          || event.repeat
          || event.isComposing
          || event.altKey
          || event.ctrlKey
          || event.metaKey
        ) {
          return false;
        }
        if (!questionNextCanAdvanceFromEnter()) {
          return false;
        }
        const target = event.target;
        const fromQuestionCard = Boolean(qQuestionCard && target && qQuestionCard.contains(target));
        const fromPictureAnswer = Boolean(questionPictureAnswerLayer && target && questionPictureAnswerLayer.contains(target));
        if (!fromQuestionCard && !fromPictureAnswer) {
          return false;
        }
        event.preventDefault();
        event.stopPropagation();
        void goQuestionNext();
        return true;
      };

      const checkQuestionAnswer = (value = "", sourceButton = null, options = {}) => {
        const item = currentQuestionItem();
        if (!item) {
          return;
        }
        if (isQuestionGuideItem(item)) {
          return;
        }
        stopQuestionAudio();
        stopGrammarAudio();
        if (typeof stopQuestionCardActiveAudio === "function") {
          stopQuestionCardActiveAudio();
        }
        const wanted = questionAnswerKey(value);
        const ok = questionAcceptedAnswers(item).some((answer) => questionAnswerKey(answer) === wanted);
        const typed = isQuestionTypedItem(item);
        const pictureMode = Boolean(questionLinkingQuestionEntryForItem(item, questionRootHighlightRangesForItem(item)));
        const firstAttemptCorrect = ok && questionWrongAttempts === 0;
        recordQuestionFirstTryAnswer(item, firstAttemptCorrect);
        if (!options || !options.skipSound) {
          void playEffectSoundAsync(ok ? "true" : "false");
        }
        const infoShown = showQuestionAnswerInfo(item, typed ? (ok ? "__typed_correct__" : "__typed_wrong__") : value);
        if (!infoShown && typed) {
          showQuestionAnswerInfo(item, value);
        }
        if (ok) {
          if (pictureMode) {
            renderQuestionPictureAnswerCards(item, {
              selectedValue: value,
              selectedOk: true,
              locked: true,
              preserveOrder: true,
              inputValue: value,
              feedback: "Correct. Press Next to continue.",
              feedbackTone: "ok",
              nextEnabled: true,
            });
            setQuestionPictureAnswerControls(true);
            setQuestionPictureAnswerNextEnabled(true);
          } else {
            renderQuestionChoices(item, { selectedValue: value, selectedOk: true, locked: true, preserveOrder: true });
            setQuestionAnswerControls(true);
            if (typed) {
              renderQuestionInputBranchTrigger(item, true);
            }
          }
          setQuestionAnswerFeedback("Correct. Press Next to continue.", "ok");
          awardQuestionBookOnce(sourceButton || qAnswerInput || qQuestionCard || questionRootInfoCard || qRootCard, {
            kind: "question",
          });
          if (qNextButton) {
            qNextButton.disabled = false;
          }
          updateQuestionProgressLabel();
          focusQuestionNextControl(90);
          clearQuestionAdvanceTimer();
          queueQuestionProgressSave(120);
          return;
        }
        questionWrongAttempts += 1;
        queueQuestionProgressSave(220);
        const errorText = questionWrongAttempts >= 2 ? "Sai 2 lần. Bạn có thể hiện đáp án." : "Chưa đúng. Thử lại lần nữa.";
        if (pictureMode) {
          renderQuestionPictureAnswerCards(item, {
            selectedValue: value,
            selectedOk: false,
            locked: false,
            preserveOrder: true,
            inputValue: value,
            feedback: errorText,
            feedbackTone: "error",
          });
        } else {
          renderQuestionChoices(item, { selectedValue: value, selectedOk: false, locked: false, preserveOrder: true, selectedTokens: options && Array.isArray(options.selectedTokens) ? options.selectedTokens : [] });
          if (typed) {
            clearQuestionInputBranchTrigger();
          }
        }
        setQuestionAnswerFeedback(questionWrongAttempts >= 2 ? "Sai 2 lần. Bạn có thể hiện đáp án." : "Chưa đúng. Thử lại lần nữa.", "error");
        if (questionWrongAttempts >= 2) {
          revealQuestionAnswerButton();
        }
      };

      const showQuestionAnswer = (event = null) => {
        const item = currentQuestionItem();
        if (!item) {
          return;
        }
        stopQuestionAudio();
        stopGrammarAudio();
        if (typeof stopQuestionCardActiveAudio === "function") {
          stopQuestionCardActiveAudio();
        }
        if (isQuestionSelectItem(item)) {
          showQuestionSelectAnswerReveal(item, event);
          return;
        }
        if (questionLinkingQuestionEntryForItem(item, questionRootHighlightRangesForItem(item))) {
          renderQuestionPictureAnswerCards(item, {
            selectedValue: item.answer,
            selectedOk: true,
            locked: false,
            preserveOrder: true,
            feedback: `Đáp án: ${item.answer}`,
            feedbackTone: "ok",
            nextEnabled: true,
          });
          setQuestionPictureAnswerNextEnabled(true);
        }
        setQuestionAnswerFeedback(`Đáp án: ${item.answer}`, "ok");
        if (isQuestionTypedItem(item) && !questionLinkingQuestionEntryForItem(item, questionRootHighlightRangesForItem(item))) {
          renderQuestionInputBranchTrigger(item, true);
        }
        if (qChoiceList) {
          qChoiceList.querySelectorAll("button").forEach((button) => {
            if (questionAnswerKey(button.dataset.answer || button.textContent) === questionAnswerKey(item.answer)) {
              button.classList.add("is-correct");
            }
          });
        }
        if (qNextButton) {
          qNextButton.disabled = false;
        }
        updateQuestionProgressLabel();
        focusQuestionNextControl(90);
        queueQuestionProgressSave(120);
      };

      const questionTypingDelayFor = (previousChar = "") => {
        if (previousChar === "\n") {
          return 38;
        }
        if (/[.!?,;:]/.test(previousChar)) {
          return 28;
        }
        if (/\s/.test(previousChar)) {
          return 14;
        }
        return 12;
      };

      const prepareQuestionPromptCard = () => {
        if (!qQuestionCard || !questionCurrentQuestions.length) {
          return false;
        }
        const item = currentQuestionItem();
        ensureQuestionAttemptRewardKey(item);
        if (questionLinkingQuestionEntryForItem(item, questionRootHighlightRangesForItem(item))) {
          return preparePictureRegionQuestionPrompt();
        }
        if (qQuestionCount) {
          qQuestionCount.textContent = `${questionQuestionIndex + 1} / ${questionCurrentQuestions.length}`;
        }
        if (qQuestionText) {
          qQuestionText.textContent = item && item.question ? item.question : "";
        }
        setQuestionAnswerControls(false);
        setQuestionAnswerFeedback("");
        if (qShowAnswerButton) {
          qShowAnswerButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qNextButton) {
          qNextButton.disabled = true;
        }
        if (qQuestionAudioButton) {
          qQuestionAudioButton.classList.add("ft-q-show-answer-hidden");
        }
        if (qAnswerInput) {
          qAnswerInput.value = "";
          syncQuestionAnswerInputMemory();
          resizeQuestionAnswerInput();
          clearQuestionInputFlare();
        }
        const guide = isQuestionGuideItem(item);
        const typed = item && isQuestionTypedItem(item);
        const selectTargets = item ? questionSelectTargets(item) : null;
        const selectTargetMode = item && isQuestionSelectItem(item) && Boolean(selectTargets && (selectTargets.root_text || selectTargets.root_ranges.length || selectTargets.regions.length));
        if (qSelectSubmitButton) {
          qSelectSubmitButton.classList.toggle("ft-q-show-answer-hidden", !selectTargetMode);
          qSelectSubmitButton.disabled = true;
          qSelectSubmitButton.title = selectTargetMode ? "Select answer targets first" : "Selection lock is available only for selection questions";
        }
        if (qQuestionCard) {
          qQuestionCard.classList.toggle("is-input-question", Boolean(typed));
          qQuestionCard.classList.toggle("is-select-target-card", Boolean(selectTargetMode));
        }
        updateQuestionInputLengthRadar(item, Boolean(typed));
        const pictureQuestionEntry = item ? questionRootPictureQuestionForItem(item, []) : null;
        const hasPictureQuestionBranch = Boolean(pictureQuestionEntry && pictureQuestionEntry.payload && pictureQuestionEntry.payload.text);
        if (qInputRow) {
          qInputRow.classList.toggle("ft-q-show-answer-hidden", !typed);
          qInputRow.classList.toggle("is-picture-question-block", hasPictureQuestionBranch && typed);
        }
        applyQuestionInputAccent(Boolean(typed));
        if (typed) {
          resizeQuestionAnswerInput();
        }
        if (qChoiceList) {
          qChoiceList.classList.toggle("ft-q-show-answer-hidden", typed);
          qChoiceList.classList.toggle("is-picture-question-branch", hasPictureQuestionBranch && !typed);
          if (typed) {
            qChoiceList.innerHTML = "";
          } else if (item) {
            renderQuestionChoices(item, { guide });
          }
        }
        if (item && isQuestionSelectItem(item)) {
          renderQuestionSelectTargetsForItem(item);
        }
        if (qConnectorQuestion) {
          qConnectorQuestion.classList.remove("is-live");
        }
        qQuestionCard.classList.add("is-preparing");
        qQuestionCard.classList.remove("is-live");
        return true;
      };

      const showQuestionPromptCard = (node, options = {}) => {
        if (questionLinkingQuestionEntryForItem(currentQuestionItem(), questionRootHighlightRangesForItem(currentQuestionItem()))) {
          startQuestionPicturePromptStartupSequence(questionRevealToken);
          return showPictureRegionQuestionPrompt(currentQuestionItem(), questionRootHighlightRangesForItem(currentQuestionItem()));
        }
        if (!qQuestionCard || (!qQuestionCard.classList.contains("is-preparing") && !prepareQuestionPromptCard())) {
          return false;
        }
        qQuestionCard.classList.remove("is-preparing");
        qQuestionCard.classList.add("is-live");
        if (qConnectorQuestion) {
          qConnectorQuestion.classList.add("is-live");
        }
        window.requestAnimationFrame(() => {
          if (questionModeActive && questionCurrentNode === node) {
            showQuestionItem(options);
          }
        });
        return true;
      };

      const revealQuestionCards = () => {
        stopQuestionReveal();
        setQuestionRevealAnimationsActive(true);
        const node = questionCurrentNode;
        const revealNodeIndex = currentNodeIndex;
        const picture = questionCardData(node, "picture");
        const audio = questionCardData(node, "audio");
        const questions = questionCardData(node, "questions");
        if (qRootCard) {
          qRootCard.classList.remove("is-typing");
          qRootCard.classList.add("is-typed");
        }
        setQuestionRootTypingProgress(questionTypingFullText.length || 1, questionTypingFullText.length || 1);
        if (qSkipTypeButton) {
          qSkipTypeButton.disabled = true;
        }
        const resumeState = pendingQuestionResumeState && pendingQuestionResumeState.currentIndex === currentNodeIndex
          ? pendingQuestionResumeState
          : null;
        questionCardsRevealSettled = false;
        const sourceQuestions = Array.isArray(questions) ? questions : [];
        const canReusePreparedQuestionOrder = Boolean(
          questionCurrentNode === node
          && questionCurrentQuestions.length === sourceQuestions.length
          && questionCurrentQuestionOrder.length === sourceQuestions.length
        );
        if (!canReusePreparedQuestionOrder) {
          const orderedQuestionEntries = orderQuestionEntries(
            sourceQuestions,
            resumeState && Array.isArray(resumeState.questionOrder) ? resumeState.questionOrder : [],
          );
          questionCurrentQuestions = orderedQuestionEntries.map((entry) => entry.item);
          questionCurrentQuestionOrder = orderedQuestionEntries.map((entry) => entry.index);
        }
        questionQuestionIndex = resumeState
          ? Math.max(0, Math.min(Math.max(0, questionCurrentQuestions.length - 1), Math.floor(Number(resumeState.questionIndex || 0) || 0)))
          : 0;
        if (resumeState) {
          questionWrongAttempts = Math.max(0, Math.floor(Number(resumeState.wrongAttempts || 0) || 0));
          pendingQuestionResumeState = null;
        }
        warmQuestionAudioCacheForLesson(questionPayload || { nodes: questionNodes, effects: lessonEffects }, {
          startIndex: currentNodeIndex,
          startQuestionIndex: questionQuestionIndex,
          questionOrder: questionCurrentQuestionOrder,
          nodeOrder: [currentNodeIndex, ...questionQueue],
          label: "Space_Q",
          includeEffects: false,
          status: false,
          startDelayMs: 80,
          delayMs: 90,
          workers: 1,
        });
        window.setTimeout(() => {
          if (!questionModeActive || questionCurrentNode !== node || currentNodeIndex !== revealNodeIndex) {
            return;
          }
          warmQuestionAudioCacheForLesson(questionPayload || { nodes: questionNodes, effects: lessonEffects }, {
            startIndex: currentNodeIndex,
            startQuestionIndex: questionQuestionIndex,
            questionOrder: questionCurrentQuestionOrder,
            nodeOrder: [currentNodeIndex, ...questionQueue],
            label: "Space_Q",
            includeEffects: false,
            status: false,
            startDelayMs: 0,
            delayMs: 45,
            workers: 2,
          });
        }, 5200);
        queueQuestionProgressSave(resumeState ? 220 : 160);
        updateQuestionRootNoticeReplayButton();
        const firstQuestionItem = currentQuestionItem();
        const firstQuestionRootHighlightRanges = firstQuestionItem
          ? questionRootHighlightRangesForItem(firstQuestionItem)
          : [];
        const firstQuestionLinkingEntry = questionLinkingQuestionEntryForItem(firstQuestionItem, firstQuestionRootHighlightRanges);
        const firstUsesPictureRegionPrompt = Boolean(firstQuestionLinkingEntry);
        const firstQuestionHasPictureRegions = Boolean(
          firstQuestionLinkingEntry
          && firstQuestionLinkingEntry.payload
          && firstQuestionLinkingEntry.payload.anchor === "picture_regions"
          && normalizeQuestionPictureRegions(firstQuestionLinkingEntry.payload.regions || []).length
        );
        const firstQuestionHasRootNotice = questionRootNoticeAvailable(firstQuestionItem);
        const steps = [];
        if (audio && audio.url && qAudioCard) {
          steps.push({
            target: () => (qPlayButton && qPlayButton.getBoundingClientRect().width ? qPlayButton : qAudioCard),
            prepare: () => prepareQuestionAudioSideCard(node),
            show: () => showQuestionAudioSideCard(node),
            panDelayMs: 980,
            panOptions: { duration: 940, allowSplitPan: true, forceLayout: true },
            settleAfterShow: "smooth",
            settleDelayMs: 360,
            settleTarget: () => (qPlayButton && qPlayButton.getBoundingClientRect().width ? qPlayButton : qAudioCard),
          });
        }
        if (picture && picture.url && qPictureCard) {
          steps.push({
            target: qPictureCard,
            prepare: () => prepareQuestionPictureSideCard(node),
            beforePan: (next) => waitQuestionPictureLayoutReady(next),
            show: () => showQuestionPictureSideCard(node),
            panOptions: { duration: 940, allowSplitPan: true, forceLayout: true },
            settleAfterShow: "smooth",
            settleDelayMs: 2100,
            settleTarget: () => questionRootPromptOverviewCameraTarget(),
            settlePanOptions: { duration: 980, allowSplitPan: true, forceLayout: true, alignY: "top", topOffset: 12 },
          });
        }
        if (firstQuestionRootHighlightRanges.length || firstQuestionHasRootNotice) {
          steps.push({
            run: (next) => {
              setQuestionFeedback("Scanning root signal...", "ok");
              waitQuestionRootHighlightRangesBeforePrompt(firstQuestionItem, firstQuestionRootHighlightRanges, next, {
                focus: firstUsesPictureRegionPrompt && questionSplitDesktopLayoutActive() ? false : (firstUsesPictureRegionPrompt ? true : undefined),
                showPictureBubble: false,
                settleMs: 500,
                panOptions: firstUsesPictureRegionPrompt ? { duration: 900 } : undefined,
              });
            },
          });
        }
        if (questionCurrentQuestions.length && firstUsesPictureRegionPrompt) {
          const picturePromptStep = firstQuestionHasPictureRegions
            ? {
              target: () => questionPictureRegionCameraTarget(),
              prepare: () => preparePictureRegionQuestionPrompt(),
              beforeShow: () => startQuestionPicturePromptStartupSequence(questionRevealToken),
              show: () => showPictureRegionQuestionPrompt(currentQuestionItem(), firstQuestionRootHighlightRanges),
              panDelayMs: 500,
              panOptions: { duration: 500, allowSplitPan: true, forceLayout: true },
              settleAfterShow: "smooth",
              settleDelayMs: 500,
              settleTarget: () => questionPicturePromptAnswerCameraTarget(),
              settlePanOptions: { duration: 620, allowSplitPan: true, forceLayout: true },
            }
            : {
              target: () => (questionSplitDesktopLayoutActive() ? questionRootPromptOverviewCameraTarget() : questionPicturePromptCameraTarget()),
              prepare: () => preparePictureRegionQuestionPrompt(),
              beforeShow: () => startQuestionPicturePromptStartupSequence(questionRevealToken),
              show: () => showPictureRegionQuestionPrompt(currentQuestionItem(), firstQuestionRootHighlightRanges),
              showBeforePan: true,
              panDelayMs: 500,
              panOptions: { duration: 500, allowSplitPan: true, forceLayout: true, alignY: "top", topOffset: 12 },
              settleAfterShow: "smooth",
              settleWhenShownBeforePan: true,
              settleDelayMs: 220,
              settleTarget: () => (questionSplitDesktopLayoutActive() ? questionRootPromptOverviewCameraTarget() : questionPicturePromptAnswerCameraTarget()),
              settlePanOptions: { duration: 500, allowSplitPan: true, forceLayout: true, alignY: "top", topOffset: 12 },
            };
          steps.push(picturePromptStep);
        } else if (questionCurrentQuestions.length && qQuestionCard) {
          steps.push({
            target: () => (questionSplitDesktopLayoutActive() ? questionRootPromptOverviewCameraTarget() : qQuestionCard),
            prepare: () => prepareQuestionPromptCard(),
            show: () => showQuestionPromptCard(node, { skipRootHighlight: true }),
            panDelayMs: 500,
            panOptions: { duration: 500, allowSplitPan: true, forceLayout: true, alignY: "top", topOffset: 12 },
            settleAfterShow: "smooth",
            settleTarget: () => (questionSplitDesktopLayoutActive() ? questionRootPromptOverviewCameraTarget() : qQuestionCard),
            settlePanOptions: { duration: 500, allowSplitPan: true, forceLayout: true, alignY: "top", topOffset: 12 },
          });
        }
        const finishReveal = () => {
          questionRevealTimer = 0;
          scheduleQuestionSideLayout();
          questionCardsRevealSettled = true;
          setQuestionRevealAnimationsActive(false);
          endQuestionMobileLoadSmoothing();
          endQuestionRevealAnimationOverride({ discharge: !isQuestionMobileFlow() });
          updateQuestionRootNoticeReplayButton();
          queueQuestionProgressSave(260);
          if (questionCurrentQuestions.length) {
            settleQuestionCardOnlyView([0, 140, 420]);
            setQuestionFeedback("Question module ready.", "ok");
            return;
          }
          setQuestionFeedback("Root complete. Advancing...", "ok");
          window.setTimeout(() => {
            if (questionModeActive && questionCurrentNode === node) {
              showNextQuestionNode();
            }
          }, 1200);
        };
        if (isQuestionMobileFlow()) {
          const token = ++questionRevealToken;
          clearQuestionCamera({ resetReveal: false });
          setQuestionRevealAnimationsActive(false);
          if (qRootText && firstQuestionRootHighlightRanges.length) {
            qRootText.innerHTML = renderQuestionRootMarkup(questionTypingFullText, [], { ranges: firstQuestionRootHighlightRanges });
            attachQuestionRootHighlightEvents();
            if (isQuestionSelectItem(firstQuestionItem)) {
              renderQuestionSelectTargetsForItem(firstQuestionItem);
            }
          }
          let preferredMobilePanel = "root";
          if (audio && audio.url && qAudioCard && prepareQuestionAudioSideCard(node)) {
            showQuestionAudioSideCard(node);
            preferredMobilePanel = "audio";
          }
          if (picture && picture.url && qPictureCard && prepareQuestionPictureSideCard(node)) {
            showQuestionPictureSideCard(node);
            preferredMobilePanel = "picture";
          }
          if (questionCurrentQuestions.length && firstUsesPictureRegionPrompt) {
            if (preparePictureRegionQuestionPrompt()) {
              showPictureRegionQuestionPrompt(currentQuestionItem(), firstQuestionRootHighlightRanges);
              preferredMobilePanel = "question";
            }
          } else if (questionCurrentQuestions.length && qQuestionCard) {
            if (prepareQuestionPromptCard()) {
              showQuestionItem({ skipRootHighlight: true });
              preferredMobilePanel = "question";
            }
          }
          if (token === questionRevealToken && questionModeActive && questionCurrentNode === node) {
            positionQuestionPictureAnswerCards();
            scheduleQuestionSideLayout(1);
            scheduleQuestionMobilePanelsSync(preferredMobilePanel);
            finishReveal();
          }
          return;
        }
        if (!steps.length) {
          finishReveal();
          return;
        }
        setQuestionFeedback("Root complete. Moving to modules...", "ok");
        const token = ++questionRevealToken;
        const runStep = (stepIndex) => {
          if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
            return;
          }
          const step = steps[stepIndex];
          const skipStep = () => {
            if (stepIndex >= steps.length - 1) {
              finishReveal();
            } else {
              runStep(stepIndex + 1);
            }
          };
          const prepareStep = () => {
            if (!step || !step.prepare()) {
              skipStep();
              return false;
            }
            positionQuestionSideCards();
            return true;
          };
          const panToStepTarget = () => {
            let shownBeforePan = false;
            const showStep = () => {
              if (typeof step.beforeShow === "function") {
                step.beforeShow();
              }
              const shown = typeof step.show === "function" ? step.show() : false;
              if (typeof step.afterShow === "function") {
                step.afterShow(Boolean(shown));
              }
              return shown;
            };
            const startPan = () => {
              const stepTarget = typeof step.target === "function" ? step.target() : step.target;
              const stepPanDelay = Number.isFinite(Number(step.panDelayMs))
                ? Math.max(0, Number(step.panDelayMs))
                : QUESTION_CAMERA_PAN_SETTLE_MS;
              const stepPanOptions = step.panOptions && typeof step.panOptions === "object"
                ? step.panOptions
                : {};
              panQuestionCameraTo(stepTarget, () => {
                if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                  return;
                }
                if (!shownBeforePan) {
                  showStep();
                }
                positionQuestionSideCards();
                scheduleQuestionSideLayout();
                const queueNext = () => {
                  if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                    return;
                  }
                  if (stepIndex >= steps.length - 1) {
                    finishReveal();
                    return;
                  }
                  runStep(stepIndex + 1);
                };
                const afterSettle = () => {
                  questionRevealTimer = window.setTimeout(() => window.requestAnimationFrame(queueNext), QUESTION_CARD_REVEAL_SETTLE_MS);
                };
                const shouldSettleAfterStep = Boolean(step.settleAfterShow) && (!shownBeforePan || step.settleWhenShownBeforePan);
                if (shouldSettleAfterStep) {
                  window.setTimeout(() => {
                    if (token === questionRevealToken && questionModeActive && questionCurrentNode === node) {
                      positionQuestionSideCards();
                      if (isQuestionPictureRegionPromptPinned()) {
                        repositionActiveQuestionRootInfo();
                        positionQuestionPictureAnswerCards();
                      }
                      const settleTarget = typeof step.settleTarget === "function"
                        ? step.settleTarget()
                        : (typeof step.target === "function" ? step.target() : step.target);
                      const settlePanOptions = step.settlePanOptions && typeof step.settlePanOptions === "object"
                        ? step.settlePanOptions
                        : stepPanOptions;
                      if (step.settleAfterShow === "smooth") {
                        panQuestionCameraTo(settleTarget, afterSettle, QUESTION_CAMERA_PAN_SETTLE_MS, settlePanOptions);
                      } else {
                        settleQuestionCameraFocus(settleTarget, afterSettle, 3);
                      }
                    }
                  }, Math.max(0, Number(step.settleDelayMs) || 90));
                } else {
                  afterSettle();
                }
              }, stepPanDelay, stepPanOptions);
            };
            if (step.showBeforePan && typeof step.show === "function") {
              shownBeforePan = Boolean(showStep());
              positionQuestionSideCards();
              scheduleQuestionSideLayout();
              window.requestAnimationFrame(() => {
                if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                  return;
                }
                positionQuestionSideCards();
                if (isQuestionPictureRegionPromptPinned()) {
                  repositionActiveQuestionRootInfo();
                  positionQuestionPictureAnswerCards();
                }
                window.requestAnimationFrame(startPan);
              });
              return;
            }
            startPan();
          };
          if (!step) {
            skipStep();
            return;
          }
          if (typeof step.run === "function") {
            step.run(() => {
              if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
                return;
              }
              if (stepIndex >= steps.length - 1) {
                finishReveal();
              } else {
                runStep(stepIndex + 1);
              }
            });
            return;
          }
          if (step.prepareAfterBeforePan && typeof step.beforePan === "function") {
            step.beforePan(() => {
              if (token === questionRevealToken && questionModeActive && questionCurrentNode === node && prepareStep()) {
                panToStepTarget();
              }
            });
          } else if (prepareStep()) {
            if (typeof step.beforePan === "function") {
              step.beforePan(() => {
                if (token === questionRevealToken && questionModeActive && questionCurrentNode === node) {
                  panToStepTarget();
                }
              });
            } else {
              panToStepTarget();
            }
          } else {
            return;
          }
        };
        const runRevealSteps = () => {
          if (token !== questionRevealToken || !questionModeActive || questionCurrentNode !== node) {
            return;
          }
          if (!steps.length) {
            finishReveal();
            return;
          }
          window.requestAnimationFrame(() => runStep(0));
        };
        runRevealSteps();
      };

      const typeQuestionRoot = (text) => {
        stopQuestionTyping();
        stopQuestionReveal();
        setQuestionRevealAnimationsActive(true);
        stopQuestionRootHighlightAnimation();
        questionTypingFullText = preserveQuestionText(text);
        if (qRootCard) {
          qRootCard.classList.remove("is-typed");
          qRootCard.classList.add("is-typing");
        }
        setQuestionRootTypingProgress(0, questionTypingFullText.length || 1);
        if (qRootText) {
          qRootText.innerHTML = "";
          qRootText.scrollTop = 0;
          hideQuestionRootScrollbarChrome();
        }
        hideQuestionTypingComet();
        if (!questionTypingFullText) {
          if (qRootCard) {
            qRootCard.classList.remove("is-layout-staging");
          }
          setQuestionTypingSkipAvailable(false);
          revealQuestionCards();
          return;
        }
        if (isQuestionMobileFlow()) {
          setQuestionTypingSkipAvailable(false);
          hideQuestionTypingComet();
          setQuestionRootTypingProgress(questionTypingFullText.length || 1, questionTypingFullText.length || 1);
          if (qRootText) {
            qRootText.innerHTML = renderQuestionRootMarkup(questionTypingFullText);
            qRootText.scrollTop = 0;
            attachQuestionRootHighlightEvents();
          }
          if (qRootCard) {
            qRootCard.classList.remove("is-layout-staging", "is-typing");
            qRootCard.classList.add("is-typed");
          }
          setQuestionFeedback("Root signal ready.", "ok");
          revealQuestionCards();
          return;
        }
        setQuestionTypingSkipAvailable(true);
        pinQuestionRootTypingLayout(questionTypingFullText, questionCurrentNode);
        if (qRootCard) {
          qRootCard.classList.remove("is-layout-staging");
        }
        setQuestionFeedback("Typing root signal...", "ok");
        const token = ++questionTypingToken;
        const total = questionTypingFullText.length;
        const tracks = questionRootTypingTracks(questionTypingFullText, 3);
        const startedAt = window.performance ? window.performance.now() : Date.now();
        const duration = questionRootTypingDuration(questionTypingFullText);
        let lastPaintBucket = -1;
        const paint = () => {
          if (token !== questionTypingToken) {
            return;
          }
          if (!qRootText) {
            if (qRootCard) {
              qRootCard.classList.remove("is-layout-staging");
            }
            revealQuestionCards();
            return;
          }
          const now = window.performance ? window.performance.now() : Date.now();
          const ratio = Math.max(0, Math.min(1, (now - startedAt) / duration));
          const paintBucket = Math.floor(ratio * 96);
          if (paintBucket !== lastPaintBucket || ratio >= 1) {
            const revealState = questionRootTypingRevealState(questionTypingFullText, tracks, ratio);
            setQuestionRootTypingProgress(Math.round(total * ratio), total);
            renderQuestionRootTypingMarkup(questionTypingFullText, revealState.revealRanges, revealState.activeSteps);
            lastPaintBucket = paintBucket;
          }
          if (paintBucket <= 1 || paintBucket % 8 === 0 || ratio >= 1) {
            keepQuestionRootTypingTopVisible();
          }
          if (ratio >= 1) {
            questionTypingTimer = 0;
            setQuestionTypingSkipAvailable(false);
            hideQuestionTypingComet();
            qRootText.innerHTML = renderQuestionRootMarkup(questionTypingFullText);
            keepQuestionRootTypingTopVisible();
            revealQuestionCards();
            return;
          }
          questionTypingTimer = window.setTimeout(paint, 24);
        };
        paint();
      };

      const skipQuestionTyping = () => {
        stopQuestionTyping();
        stopQuestionReveal();
        setQuestionRootTypingProgress(questionTypingFullText.length || 1, questionTypingFullText.length || 1);
        hideQuestionTypingComet();
        if (qRootText) {
          qRootText.innerHTML = renderQuestionRootMarkup(questionTypingFullText);
        }
        if (qRootCard) {
          qRootCard.classList.remove("is-layout-staging");
        }
        revealQuestionCards();
      };

      const showQuestionNodeByIndex = (nodeIndex) => {
        const node = questionNodes[nodeIndex] || null;
        questionCurrentNode = node;
        currentNode = node;
        currentNodeIndex = nodeIndex;
        questionCurrentQuestions = [];
        questionCurrentQuestionOrder = [];
        questionQuestionIndex = 0;
        questionTypingRootTopPadding = null;
        questionTypingRootReservedHeight = null;
        if (qRootCard) {
          qRootCard.style.removeProperty("--q-root-reserved-height");
        }
        hideQuestionCards();
        stopQuestionAudio();
        clearQuestionCamera();
        questionCardsRevealSettled = false;
        if (qRootNoticeReplayButton) {
          qRootNoticeReplayButton.disabled = true;
          qRootNoticeReplayButton.title = "No notice for this question";
          qRootNoticeReplayButton.setAttribute("aria-disabled", "true");
        }
        if (!node) {
          endQuestionMobileLoadSmoothing();
          setQuestionFeedback("Space_Q complete.", "ok");
          saveQuestionProgressNow();
          void reportLessonCompleted("space_q_complete");
          return;
        }
        const preloadQuestionItems = Array.isArray(questionCardData(node, "questions")) ? questionCardData(node, "questions") : [];
        const preloadResumeState = pendingQuestionResumeState && pendingQuestionResumeState.currentIndex === nodeIndex
          ? pendingQuestionResumeState
          : null;
        const preloadQuestionEntries = orderQuestionEntries(
          preloadQuestionItems,
          preloadResumeState && Array.isArray(preloadResumeState.questionOrder) ? preloadResumeState.questionOrder : [],
        );
        questionCurrentQuestions = preloadQuestionEntries.map((entry) => entry.item);
        questionCurrentQuestionOrder = preloadQuestionEntries.map((entry) => entry.index);
        questionQuestionIndex = preloadResumeState
          ? Math.max(0, Math.min(Math.max(0, questionCurrentQuestions.length - 1), Math.floor(Number(preloadResumeState.questionIndex || 0) || 0)))
          : 0;
        beginQuestionRevealAnimationOverride();
        setQuestionRevealAnimationsActive(true);
        if (qRootCard) {
          qRootCard.classList.remove("is-hidden");
          qRootCard.classList.remove("is-typing", "is-typed");
          qRootCard.classList.add("is-layout-staging");
        }
        scheduleQuestionMobilePanelsSync("root");
        if (qRootText) {
          qRootText.innerHTML = "";
          qRootText.scrollTop = 0;
          hideQuestionRootScrollbarChrome();
        }
        setQuestionRootTypingProgress(0, preserveQuestionText(node.root).length || 1);
        updateQuestionProgressLabel();
        if (!pendingQuestionResumeState) {
          queueQuestionProgressSave(180);
        }
        applyQuestionRootStyle(node);
        if (shellNode) {
          shellNode.style.removeProperty("--q-question-top-padding");
        }
        positionQuestionSideCards({ force: true });
        centerQuestionRootHorizontalOrigin();
        scheduleQuestionSideLayout();
        if (qSkipTypeButton) {
          qSkipTypeButton.disabled = true;
        }
        const startRootTyping = () => {
          if (!questionModeActive || questionCurrentNode !== node) {
            return;
          }
          typeQuestionRoot(node.root);
        };
        const scheduleRootTypingAfterOpen = () => {
          if (questionRootOpenTypingTimer) {
            window.clearTimeout(questionRootOpenTypingTimer);
            questionRootOpenTypingTimer = 0;
          }
          if (isQuestionMobileFlow()) {
            startRootTyping();
            return;
          }
          if (qRootCard) {
            qRootCard.classList.remove("is-layout-staging");
          }
          setQuestionFeedback("Root panel stabilizing...", "ok");
          questionRootOpenTypingTimer = window.setTimeout(() => {
            questionRootOpenTypingTimer = 0;
            startRootTyping();
          }, QUESTION_ROOT_OPEN_TYPING_DELAY_MS);
        };
        if (questionIntroBootPending && !isQuestionMobileFlow()) {
          questionIntroBootPending = false;
          runQuestionInitialBootIntro(scheduleRootTypingAfterOpen);
        } else {
          questionIntroBootPending = false;
          scheduleRootTypingAfterOpen();
        }
      };

      function showNextQuestionNode() {
        if (!questionModeActive) {
          return;
        }
        if (!questionQueue.length) {
          endQuestionMobileLoadSmoothing();
          setQuestionFeedback("Mission complete.", "ok");
          saveQuestionProgressNow();
          void reportLessonCompleted("space_q_complete");
          return;
        }
        const nextIndex = questionQueue.shift();
        questionNodePointer += 1;
        showQuestionNodeByIndex(nextIndex);
      }

      const playQuestionAudio = async () => {
        const audio = questionCardData(questionCurrentNode, "audio");
        if (!audio || !audio.url) {
          setQuestionFeedback("Audio card chưa có dữ liệu.", "error");
          return;
        }
        stopQuestionAudio();
        const clip = normalizeAudioClip({
          mime: clean(audio.mime) || "audio/mpeg",
          url: audio.url,
        });
        if (clip) {
          await preloadAudioClip(clip, null);
        }
        questionAudio = new Audio(clip ? cachedAudioClipUrl(clip) : serverAssetUrl(audio.url));
        if (qPlayButton) {
          qPlayButton.disabled = false;
        }
        const finishAudio = (message = "Audio playback complete.", tone = "ok") => {
          if (qAudioCard) {
            qAudioCard.classList.remove("is-playing");
          }
          if (qPlayButton) {
            qPlayButton.disabled = false;
          }
          setQuestionFeedback(message, tone);
        };
        questionAudio.addEventListener("playing", () => {
          if (qAudioCard) {
            qAudioCard.classList.add("is-playing");
          }
        }, { once: true });
        questionAudio.addEventListener("ended", () => finishAudio("Audio playback complete.", "ok"), { once: true });
        questionAudio.addEventListener("error", () => finishAudio("Audio playback failed.", "error"), { once: true });
        questionAudio.play()
          .then(() => setQuestionFeedback("Playing audio card...", "ok"))
          .catch((error) => setQuestionFeedback(error && error.message ? error.message : "Không phát được audio.", "error"));
      };

      const enterQuestionPayloadNow = async (payload, options = {}) => {
        const normalized = normalizeQuestionPayload(payload);
        if (!normalized.nodes.length) {
          setLoadStatus("File Space_Q chưa có node Root hợp lệ.", true);
          return false;
        }
        updateFutureAppRoute("space_q", { replace: futureAppRouteFromLocation() === "lesson_vault" });
        beginQuestionMobileLoadSmoothing(4800);
        if (!currentQuestionProgressCache.progressKey || currentQuestionProgressCache.identity !== questionProgressIdentityFor(normalized, normalized.nodes)) {
          configureQuestionProgressCache(normalized, normalized.nodes);
        }
        const forceNewRun = Boolean(options.forceNewRun);
        const resumeState = forceNewRun ? null : normalizeQuestionResumeState(options.resumeState || null, normalized.nodes.length);
        const reviewRun = Boolean(options.reviewRun || (resumeState && (resumeState.reviewing || resumeState.reviewRun)));
        const sequenceNodeOrder = normalized.nodes.map((_node, index) => index);
        const plannedQuestionQueue = normalized.order === "shuffle"
          ? (resumeState ? resumeState.queue.slice() : shuffleIndexes(normalized.nodes.length))
          : (resumeState
            ? sequenceNodeOrder.filter((index) => index !== resumeState.currentIndex && index >= resumeState.currentIndex)
            : sequenceNodeOrder.slice());
        const plannedStartIndex = resumeState
          ? (normalized.order === "shuffle" ? resumeState.currentIndex : Math.max(0, Math.min(normalized.nodes.length - 1, resumeState.currentIndex)))
          : (plannedQuestionQueue[0] ?? 0);
        const plannedCacheOrder = [plannedStartIndex, ...plannedQuestionQueue];
        questionRewardConfig = normalizeQuestionRewards(normalized.rewards || {});
        questionCrystalAwardedKeys.clear();
        resetCurrentMissionCrystalAwards();
        resetQuestionAttemptRewardState();
        questionInventoryState = readLocalQuestionInventory();
        updateQuestionInventoryHud();
        const audioStartIndex = options.startIndex ?? plannedStartIndex;
        warmQuestionAudioCacheForLesson(normalized, {
          startIndex: audioStartIndex,
          startQuestionIndex: resumeState ? Math.max(0, Math.floor(Number(resumeState.questionIndex || 0) || 0)) : 0,
          questionOrder: resumeState && Array.isArray(resumeState.questionOrder) ? resumeState.questionOrder : [],
          nodeOrder: plannedCacheOrder,
          label: "Space_Q",
          maxNodes: 1,
          maxTasks: 6,
          includeEffects: false,
          currentQuestionOnly: true,
          startDelayMs: 90,
          delayMs: 70,
          workers: 1,
          status: false,
        });
        resetQuestionMode({ keepPending: true });
        resetParagraphMode();
        questionModeActive = true;
        questionReviewRunActive = reviewRun;
        questionActiveRunId = clean(resumeState && (resumeState.runId || resumeState.run_id))
          || `space-q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
        setVocabModeClass(false);
        setSpaceWModeClass(false);
        scheduleMobileInfiniteMotionSync(80);
        setQuestionInventoryHudVisible(true);
        void loadQuestionInventory();
        if (stageNode) {
          stageNode.classList.add("is-question-mode");
          setQuestionMobilePanel("root", { skipFocus: true });
          beginQuestionMobileLoadSmoothing(4800);
          setQuestionVisualProfileActive(true);
          applyQuestionResponsiveScale(true);
          stageNode.scrollLeft = 0;
        }
        try {
          const doc = document.scrollingElement || document.documentElement;
          doc.scrollLeft = 0;
          window.scrollTo({ left: 0, top: window.scrollY || doc.scrollTop || 0, behavior: "instant" });
        } catch (error) {
        }
        questionPayload = normalized;
        questionNodes = normalized.nodes;
        lessonNodes = questionNodes;
        pendingQuestionResumeState = forceNewRun ? null : resumeState;
        pendingQuestionPayload = null;
        pendingVocabularyPayload = null;
        pendingParagraphPayload = null;
        pendingLessonNodes = [];
        pendingLessonEffects = {};
        questionQueue = plannedQuestionQueue.slice();
        questionNodePointer = 0;
        questionIntroBootPending = true;
        lessonEffects = normalizeEffectSounds(normalized.effects || {});
        loadGate.classList.add("is-hidden");
        loadGate.classList.remove("is-file-ready");
        updateLoadEnterNowButton();
        cardNode.classList.add("is-hidden");
        if (vocabCard) {
          vocabCard.classList.add("is-hidden");
        }
        vocabModeActive = false;
        setVocabKeyboardLock(false);
        hideVocabModePopup();
        [vocabDetailPanel, vocabPicturePanel, vocabUnlearnedPanel, vocabWeakConnector, vocabSideConnector, vocabLearnedPanel, vocabLearnedConnector].forEach((node) => {
          if (node) {
            node.classList.add("is-hidden");
          }
        });
        hideSpeakPanel();
        hideHintPanel();
        hideScorePanel(true);
        hideGrammarQuiz(false, true);
        clearAllConnectors();
        stopActiveAudio();
        stopQuestionAudio();
        hideCompletionGate();
        setTtsStatus("Space_Q ready.");
        if (isQuestionMobilePerformanceSurface()) {
          await new Promise((resolve) => {
            window.requestAnimationFrame(() => window.requestAnimationFrame(resolve));
          });
        }
        if (!forceNewRun && resumeState && questionNodes[resumeState.currentIndex]) {
          showQuestionNodeByIndex(resumeState.currentIndex);
        } else {
          showNextQuestionNode();
        }
        if (forceNewRun) {
          saveQuestionProgressNow();
        }
        return true;
      };

      const vocabWordKey = (item) => normalize(item && item.word ? item.word : "");

      const vocabItemByIndex = (index) => vocabItems[Number(index)] || null;

      const resetVocabLearnedPanelPosition = () => {
        if (!vocabLearnedPanel) {
          return;
        }
        ["left", "top", "right", "bottom", "width", "max-height"].forEach((name) => vocabLearnedPanel.style.removeProperty(name));
        if (vocabLearnedList) {
          vocabLearnedList.style.removeProperty("max-height");
        }
      };

      const renderVocabLearnedPanel = (currentItem = null) => {
        if (!vocabLearnedPanel || !vocabLearnedCount || !vocabCurrentStatus || !vocabLearnedList) {
          return;
        }
        const item = currentItem || vocabItems[vocabCurrentIndex] || null;
        const key = vocabWordKey(item);
        const known = Boolean(key && vocabKnownAtStartKeys.has(key));
        if (vocabCardSignal) {
          vocabCardSignal.textContent = item ? (known ? "OLD SIGNAL" : "NEW SIGNAL") : "STANDBY";
          vocabCardSignal.classList.toggle("is-old", known);
          vocabCardSignal.classList.toggle("is-new", !known);
        }
        const show = Boolean(vocabModeActive && vocabPhase === "probe" && !vocabModeTransitioning && vocabCard && !vocabCard.classList.contains("is-hidden"));
        vocabLearnedPanel.classList.toggle("is-hidden", !show);
        if (vocabLearnedConnector) {
          vocabLearnedConnector.classList.toggle("is-hidden", !show || isMobilePanelFlow());
        }
        if (!show) {
          resetVocabLearnedPanelPosition();
          return;
        }
        const totalText = vocabRegistryError
          ? "Memory offline"
          : vocabRegistryLoading && !vocabRegistryLoaded
          ? "Scanning memory..."
          : `${vocabRegistryTotal} learned ${vocabRegistryTotal === 1 ? "word" : "words"}`;
        vocabLearnedCount.textContent = totalText;
        vocabCurrentStatus.classList.toggle("is-old", known);
        vocabCurrentStatus.classList.toggle("is-new", !known);
        vocabCurrentStatus.textContent = item && item.word
          ? `Current signal: ${known ? "OLD MEMORY" : "NEW WORD"}`
          : "Current word: STANDBY";

        const filter = vocabRegistryFilterText || "";
        const filterLower = filter.toLowerCase();
        const safeRegistryWords = key
          ? vocabRegistryWords.filter((entry) => entry.key !== key)
          : vocabRegistryWords;
        const source = filterLower
          ? safeRegistryWords.filter((entry) => {
              const haystack = `${entry.word || ""} ${entry.meaning || ""} ${entry.pron || ""} ${entry.type || ""}`.toLowerCase();
              return haystack.includes(filterLower);
            })
          : safeRegistryWords;
        const visible = source.slice(0, VOCAB_REGISTRY_RENDER_LIMIT);
        const fragment = document.createDocumentFragment();
        vocabLearnedList.textContent = "";
        if (!vocabRegistryLoaded && vocabRegistryLoading) {
          const row = document.createElement("div");
          row.className = "ft-vocab-learned-item is-note";
          row.textContent = "Loading user lexicon memory...";
          fragment.appendChild(row);
        } else if (!visible.length) {
          const row = document.createElement("div");
          row.className = "ft-vocab-learned-item is-note";
          row.textContent = vocabRegistryError
            ? "Server lexicon memory is not available."
            : filter ? "No learned word matched this filter." : "No learned words synced yet.";
          fragment.appendChild(row);
        } else {
          visible.forEach((entry) => {
            const row = document.createElement("div");
            row.className = "ft-vocab-learned-item";
            const word = document.createElement("strong");
            word.textContent = entry.word || entry.key || "";
            const meaning = document.createElement("small");
            const meta = [entry.meaning, entry.type, entry.count ? `${entry.count}x` : ""].filter(Boolean).join(" | ");
            meaning.textContent = meta || "Learned memory";
            row.append(word, meaning);
            fragment.appendChild(row);
          });
          if (source.length > visible.length) {
            const row = document.createElement("div");
            row.className = "ft-vocab-learned-item is-note";
            row.textContent = `Showing ${visible.length} / ${source.length} matches. Use filter to narrow it.`;
            fragment.appendChild(row);
          }
        }
        vocabLearnedList.appendChild(fragment);
        window.requestAnimationFrame(positionVocabLearnedPanel);
      };

      const loadVocabRegistry = async (force = false, fresh = false) => {
        if (vocabRegistryLoading || (vocabRegistryLoaded && !force)) {
          return;
        }
        const cachedRegistry = typeof readVocabRegistryLocalCache === "function"
          ? readVocabRegistryLocalCache(currentAuthUsername || "")
          : null;
        const hadCachedRegistry = typeof applyVocabRegistryLocalCache === "function"
          ? applyVocabRegistryLocalCache(currentAuthUsername || "")
          : false;
        vocabRegistryLoading = true;
        vocabRegistryError = "";
        renderVocabLearnedPanel();
        try {
          const result = await fetchServerJson(fresh ? "/vocab/registry?fresh=1" : "/vocab/registry", fresh ? {} : {
            ifNoneMatch: clean(cachedRegistry && cachedRegistry.etag || ""),
            notModifiedPayload: cachedRegistry,
          });
          const payload = result && result.payload ? result.payload : {};
          const words = Array.isArray(payload.words) ? payload.words : [];
          vocabRegistryWords = words
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
          vocabRegistryKeys = new Set(vocabRegistryWords.map((entry) => entry.key));
          const periodSource = payload.period_keys && typeof payload.period_keys === "object" ? payload.period_keys : {};
          vocabRegistryPeriodKeys = {
            day: new Set((Array.isArray(periodSource.day) ? periodSource.day : []).map((key) => normalize(key)).filter(Boolean)),
            week: new Set((Array.isArray(periodSource.week) ? periodSource.week : []).map((key) => normalize(key)).filter(Boolean)),
            month: new Set((Array.isArray(periodSource.month) ? periodSource.month : []).map((key) => normalize(key)).filter(Boolean)),
          };
          vocabRegistryTotal = Number(payload.total_words || vocabRegistryWords.length) || vocabRegistryWords.length;
          vocabRegistryLoaded = true;
          if (typeof writeVocabRegistryLocalCache === "function") {
            writeVocabRegistryLocalCache({
              ...payload,
              words: vocabRegistryWords,
              total_words: vocabRegistryTotal,
              etag: clean(result && result.etag || cachedRegistry && cachedRegistry.etag || ""),
              source: "server",
            }, currentAuthUsername || "");
          }
        } catch (error) {
          vocabRegistryLoaded = true;
          vocabRegistryError = hadCachedRegistry ? "" : (error && error.message ? error.message : "memory offline");
        } finally {
          vocabRegistryLoading = false;
          renderVocabLearnedPanel();
        }
      };

      const vocabAnchorLayout = () => {
        if (!shellNode || !vocabCard) {
          return null;
        }
        const shellRect = shellNode.getBoundingClientRect();
        const cardRect = vocabCard.getBoundingClientRect();
        if (!shellRect.width || !cardRect.width) {
          return null;
        }
        const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
        const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
        const edge = Math.max(8, Math.min(14, viewportWidth * 0.01));
        const gap = Math.max(12, Math.min(24, viewportWidth * 0.014));
        const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
        const shellLeft = shellRect.left;
        const shellTop = shellRect.top;
        const minPanelWidth = viewportWidth < 1180 ? 190 : 238;
        const sidePreferred = Math.max(220, Math.min(340, Math.round(viewportWidth * 0.24)));
        const leftSpace = Math.max(0, cardRect.left - edge - gap);
        const rightSpace = Math.max(0, viewportWidth - edge - cardRect.right - gap);
        const topRail = clamp(cardRect.top - shellTop + Math.min(cardRect.height * 0.05, 18), edge - shellTop, Math.max(edge, viewportHeight - shellTop - 180));
        const bottomRail = clamp(cardRect.bottom - shellTop - Math.min(cardRect.height * 0.34, 150), edge - shellTop, Math.max(edge, viewportHeight - shellTop - 180));
        const slotWidth = (side, preferred = sidePreferred, minimum = minPanelWidth) => {
          const available = side === "left" ? leftSpace : rightSpace;
          if (available < Math.min(170, minimum)) {
            return 0;
          }
          return Math.max(Math.min(minimum, available), Math.min(preferred, available));
        };
        const slotLeft = (side, width) => side === "left"
          ? cardRect.left - shellLeft - width - gap
          : cardRect.right - shellLeft + gap;
        const clampLeft = (left, width) => clamp(left, edge - shellLeft, viewportWidth - shellLeft - width - edge);
        const clampTop = (top, height = 170) => clamp(top, edge - shellTop, Math.max(edge, viewportHeight - shellTop - height - 14));
        const fallbackBelow = (preferredTop = cardRect.bottom - shellTop + 12, preferredWidth = cardRect.width) => {
          const width = Math.max(240, Math.min(preferredWidth, shellRect.width - 20, viewportWidth - (edge * 2)));
          return {
            side: "below",
            width,
            left: clampLeft(cardRect.left - shellLeft + ((cardRect.width - width) / 2), width),
            top: Math.max(edge - shellTop, preferredTop),
          };
        };
        const sideSlot = (side, options = {}) => {
          const preferred = Number(options.preferred) || sidePreferred;
          const minimum = Number(options.minimum) || minPanelWidth;
          const width = slotWidth(side, preferred, minimum);
          if (!width) {
            return null;
          }
          return {
            side,
            width,
            left: clampLeft(slotLeft(side, width), width),
          };
        };
        return {
          shellRect,
          cardRect,
          viewportWidth,
          viewportHeight,
          edge,
          gap,
          leftSpace,
          rightSpace,
          topRail,
          bottomRail,
          clamp,
          clampTop,
          fallbackBelow,
          sideSlot,
        };
      };

      const positionVocabLearnedPanel = () => {
        if (!vocabLearnedPanel || !shellNode || !vocabCard) {
          return;
        }
        if (vocabLearnedPanel.classList.contains("is-hidden") || isMobilePanelFlow()) {
          resetVocabLearnedPanelPosition();
          if (vocabLearnedConnector) {
            vocabLearnedConnector.classList.add("is-hidden");
          }
          return;
        }
        const layout = vocabAnchorLayout();
        if (!layout) {
          return;
        }
        const { shellRect, cardRect, viewportHeight, topRail } = layout;
        const preferredSide = layout.leftSpace >= 180 ? "left" : "right";
        const slot = layout.sideSlot(preferredSide, {
          preferred: Math.max(260, Math.min(360, Math.round(layout.viewportWidth * 0.27))),
          minimum: 206,
        }) || layout.sideSlot(preferredSide === "left" ? "right" : "left", {
          preferred: 320,
          minimum: 206,
        }) || layout.fallbackBelow(cardRect.bottom - shellRect.top + 12, cardRect.width);
        const top = slot.side === "below" ? slot.top : layout.clampTop(topRail, 190);
        const maxHeight = Math.max(170, Math.min(430, viewportHeight - shellRect.top - top - 16));
        vocabLearnedPanel.style.right = "auto";
        vocabLearnedPanel.style.bottom = "auto";
        vocabLearnedPanel.style.maxHeight = `${Math.round(maxHeight)}px`;
        if (vocabLearnedList) {
          vocabLearnedList.style.maxHeight = `${Math.max(92, Math.round(maxHeight - 176))}px`;
        }
        if (slot.side !== "below") {
          const width = Math.round(slot.width);
          vocabLearnedPanel.style.left = `${Math.round(slot.left)}px`;
          vocabLearnedPanel.style.top = `${Math.round(top)}px`;
          vocabLearnedPanel.style.width = `${width}px`;
          if (vocabLearnedConnector && vocabLearnedPath) {
            vocabLearnedConnector.classList.remove("is-hidden");
            const freshPanelRect = vocabLearnedPanel.getBoundingClientRect();
            const startX = slot.side === "left" ? freshPanelRect.right - shellRect.left - 8 : freshPanelRect.left - shellRect.left + 8;
            const startY = freshPanelRect.top - shellRect.top + Math.min(freshPanelRect.height * 0.46, 150);
            const endX = slot.side === "left" ? cardRect.left - shellRect.left + 18 : cardRect.right - shellRect.left - 18;
            const endY = cardRect.top - shellRect.top + Math.min(cardRect.height * 0.44, 180);
            const curve = Math.max(44, Math.min(150, Math.abs(endX - startX) * 0.38));
            vocabLearnedPath.setAttribute("d", slot.side === "left"
              ? `M ${startX} ${startY} C ${startX + curve} ${startY - 14}, ${endX - curve} ${endY + 18}, ${endX} ${endY}`
              : `M ${startX} ${startY} C ${startX - curve} ${startY - 14}, ${endX + curve} ${endY + 18}, ${endX} ${endY}`);
          }
          return;
        }
        const belowMaxHeight = Math.max(170, Math.min(320, viewportHeight - shellRect.top - slot.top - 16));
        vocabLearnedPanel.style.left = `${Math.round(slot.left)}px`;
        vocabLearnedPanel.style.top = `${Math.round(slot.top)}px`;
        vocabLearnedPanel.style.width = `${Math.round(slot.width)}px`;
        vocabLearnedPanel.style.maxHeight = `${Math.round(belowMaxHeight)}px`;
        if (vocabLearnedList) {
          vocabLearnedList.style.maxHeight = `${Math.max(90, belowMaxHeight - 176)}px`;
        }
        if (vocabLearnedConnector) {
          vocabLearnedConnector.classList.add("is-hidden");
        }
      };

      const vocabCanProbeIndex = (index) => {
        const item = vocabItemByIndex(index);
        const key = vocabWordKey(item);
        return Boolean(item && key && !vocabLearnedKeys.has(key) && !vocabStudyKeys.has(key));
      };

      const vocabRemainingProbeIndexes = () => shuffleIndexes(vocabItems.length).filter(vocabCanProbeIndex);

      // Added 2026-07-26: duplicate/normalized Space_V word keys can make the
      // learned-key count smaller than the card count after the final card.
      const vocabAllProbeWordsLearned = () => {
        const keys = vocabItems.map(vocabWordKey).filter(Boolean);
        return Boolean(keys.length && keys.every((key) => vocabLearnedKeys.has(key)));
      };

      const setVocabFeedback = (message, mode = "") => {
        if (!vocabFeedback) {
          return;
        }
        vocabFeedback.textContent = message;
        vocabFeedback.classList.toggle("is-error", mode === "error");
        vocabFeedback.classList.toggle("is-ok", mode === "ok");
      };

      const resetVocabCardRevealStyles = () => {
        if (!vocabCard) {
          return;
        }
        vocabCard.classList.remove("is-vocab-visibility-forced");
        ["opacity", "transform", "visibility", "animation", "pointer-events"].forEach((name) => {
          vocabCard.style.removeProperty(name);
        });
      };

      const forceVocabCardVisible = () => {
        if (!vocabCard || vocabCard.classList.contains("is-hidden")) {
          return false;
        }
        vocabCard.classList.add("is-vocab-visibility-forced");
        vocabCard.style.visibility = "visible";
        vocabCard.style.opacity = "1";
        vocabCard.style.transform = "translateY(0) scaleY(1)";
        vocabCard.style.animation = "none";
        vocabCard.style.pointerEvents = "auto";
        return true;
      };

      const ensureVocabCardVisible = (options = {}) => {
        if (!vocabModeActive || !vocabCard || vocabCard.classList.contains("is-hidden")) {
          return false;
        }
        const style = window.getComputedStyle ? window.getComputedStyle(vocabCard) : null;
        const rect = vocabCard.getBoundingClientRect ? vocabCard.getBoundingClientRect() : { width: 0, height: 0 };
        const opacity = style ? Number.parseFloat(style.opacity) : 1;
        const broken = Boolean(options.force)
          || (style && (style.display === "none" || style.visibility === "hidden"))
          || !Number.isFinite(opacity)
          || opacity < 0.18
          || rect.width < 80
          || rect.height < 80;
        return broken ? forceVocabCardVisible() : false;
      };

      const scheduleVocabCardVisibilityGuard = (options = {}) => {
        if (!vocabCard) {
          return;
        }
        const check = () => ensureVocabCardVisible(options);
        window.requestAnimationFrame(check);
        [760, 1760, 3200].forEach((delay) => {
          window.setTimeout(check, delay);
        });
      };

      const applyVocabPhaseVisualState = () => {
        if (!vocabCard) {
          return;
        }
        vocabCard.classList.remove(
          "is-probe",
          "is-drill",
          "is-shuffle",
          "shuffle-corner-1",
          "shuffle-corner-2",
          "shuffle-corner-3",
          "shuffle-corner-4",
        );
        vocabCard.classList.add(`is-${vocabPhase || "probe"}`);
        if (vocabPhase === "shuffle") {
          const corner = ((Math.max(1, Number(vocabShuffleRound) || 1) - 1) % 4) + 1;
          vocabCard.classList.add(`shuffle-corner-${corner}`);
          scheduleVocabCardPin(1400, { force: true });
        }
        scheduleMobileInfiniteMotionSync(80);
        scheduleVocabCardVisibilityGuard();
      };

      const setVocabInputLocked = (locked) => {
        if (!vocabAnswer) {
          return;
        }
        const lockActive = Boolean(locked);
        const resetLockActive = Date.now() < vocabInputResetUntil;
        vocabAnswer.disabled = resetLockActive;
        vocabAnswer.readOnly = lockActive && !resetLockActive;
        vocabAnswer.setAttribute("aria-busy", lockActive || resetLockActive ? "true" : "false");
        if (vocabCard) {
          vocabCard.classList.toggle("is-input-locked", Boolean(lockActive || resetLockActive));
        }
        if (lockActive && !resetLockActive && document.activeElement === vocabAnswer) {
          window.setTimeout(() => vocabAnswer.focus({ preventScroll: true }), 20);
        }
      };

      const resetVocabInputForNewWord = (options = {}) => {
        if (!vocabAnswer) {
          return 0;
        }
        const token = ++vocabInputResetToken;
        const lockMs = Math.max(0, Number(options.lockMs ?? 180) || 0);
        vocabInputResetUntil = Date.now() + lockMs;
        vocabAnswer.value = "";
        vocabAnswer.disabled = lockMs > 0;
        vocabAnswer.readOnly = false;
        const finalLockActive = vocabCompletionFinalizing || vocabPhase === "complete";
        if (vocabCompletionFinalizing || vocabPhase === "complete") {
          vocabAnswer.disabled = true;
          vocabAnswer.readOnly = true;
        }
        vocabAnswer.setAttribute("aria-busy", lockMs > 0 || finalLockActive ? "true" : "false");
        if (vocabCard) {
          vocabCard.classList.toggle("is-input-locked", lockMs > 0 || finalLockActive);
        }
        window.setTimeout(() => {
          if (vocabInputResetToken !== token || !vocabAnswer) {
            return;
          }
          if (vocabCompletionFinalizing || vocabPhase === "complete") {
            vocabAnswer.disabled = true;
            vocabAnswer.readOnly = true;
            vocabAnswer.setAttribute("aria-busy", "true");
            return;
          }
          vocabInputResetUntil = 0;
          vocabAnswer.disabled = false;
          vocabAnswer.readOnly = false;
          vocabAnswer.setAttribute("aria-busy", "false");
          if (vocabCard) {
            vocabCard.classList.remove("is-input-locked");
          }
          if (options.focus !== false) {
            vocabAnswer.focus({ preventScroll: true });
            scheduleVocabCardPin(1400, { force: true });
          }
        }, lockMs + 20);
        return token;
      };

      const dismissSoftKeyboard = () => {
        const active = document.activeElement;
        if (active && /^(INPUT|TEXTAREA|SELECT)$/i.test(active.tagName || "")) {
          try {
            active.blur();
          } catch (error) {
          }
        }
      };

      const revealVocabAnswerMeta = (item, extraItems = []) => {
        renderVocabMeta(item, extraItems, { revealIpa: true });
      };

      const hideVocabModePopup = () => {
        if (vocabModePopupTimer) {
          window.clearTimeout(vocabModePopupTimer);
          vocabModePopupTimer = 0;
        }
        if (vocabModePopup) {
          vocabModePopup.classList.add("is-hidden");
          vocabModePopup.classList.remove("is-drill", "is-shuffle", "is-probe");
        }
      };

      const isVocabModePopupVisible = () => Boolean(
        vocabModePopup && !vocabModePopup.classList.contains("is-hidden")
      );

      const showVocabModePopup = (title, message, mode = "drill", duration = 2000) => new Promise((resolve) => {
        if (!vocabModePopup) {
          window.setTimeout(resolve, Math.max(0, duration));
          return;
        }
        hideVocabModePopup();
        const holdOpen = !Number.isFinite(Number(duration)) || Number(duration) <= 0;
        resetVocabInputForNewWord({ lockMs: holdOpen ? 12000 : Math.max(600, Number(duration) || 2000), focus: false });
        vocabModePopup.classList.remove("is-hidden", "is-drill", "is-shuffle", "is-probe");
        vocabModePopup.classList.add(`is-${mode}`);
        if (vocabModeTitle) {
          vocabModeTitle.textContent = title;
        }
        if (vocabModeText) {
          vocabModeText.textContent = message;
        }
        if (holdOpen) {
          return;
        }
        vocabModePopupTimer = window.setTimeout(() => {
          hideVocabModePopup();
          resolve();
        }, Math.max(600, Number(duration) || 2000));
      });

      const setVocabTimerState = (message = "Signal armed", mode = "") => {
        if (!vocabTimer) {
          return;
        }
        vocabTimer.classList.remove("is-hidden", "is-alert", "is-answer", "is-miss");
        vocabTimer.classList.toggle("is-alert", mode === "alert");
        vocabTimer.classList.toggle("is-answer", mode === "answer");
        vocabTimer.classList.toggle("is-miss", mode === "miss");
        if (vocabTimerText) {
          vocabTimerText.textContent = message;
        }
      };

      const restartVocabTimerClock = () => {
        const hand = vocabTimer && vocabTimer.querySelector(".ft-vocab-timer-orbit i:first-child");
        if (!hand) {
          return;
        }
        hand.style.animation = "none";
        void hand.offsetWidth;
        hand.style.removeProperty("animation");
      };

      const clearVocabActiveHint = () => {
        vocabActiveHintKind = "";
        vocabActiveHintIndex = -1;
        vocabActiveHintPhase = "";
        if (vocabMeta) {
          vocabMeta.querySelectorAll(".ft-vocab-chip.is-hint-active, .ft-vocab-chip.is-type-float").forEach((chip) => {
            chip.classList.remove("is-hint-active", "is-type-float");
          });
        }
      };

      const clearVocabHintTimers = (hideTimer = true) => {
        vocabQuestionToken += 1;
        vocabHintToken += 1;
        vocabHintTimers.forEach((timer) => window.clearTimeout(timer));
        vocabHintTimers = [];
        vocabIdleHintToken += 1;
        if (vocabIdleHintTimer) {
          window.clearTimeout(vocabIdleHintTimer);
          vocabIdleHintTimer = 0;
        }
        clearVocabActiveHint();
        vocabAutoRevealLock = false;
        if (hideTimer && vocabTimer) {
          vocabTimer.classList.add("is-hidden");
          vocabTimer.classList.remove("is-alert", "is-answer", "is-miss");
        }
      };

      const vocabCurrentAnswerIsSolved = (item) => Boolean(
        item && vocabAnswer && normalize(vocabAnswer.value) === normalize(item.word)
      );

      const applyVocabActiveHint = () => {
        if (!vocabMeta) {
          return;
        }
        vocabMeta.querySelectorAll(".ft-vocab-chip.is-hint-active, .ft-vocab-chip.is-type-float").forEach((chip) => {
          chip.classList.remove("is-hint-active", "is-type-float");
        });
        if (
          !vocabActiveHintKind
          || Number(vocabActiveHintIndex) !== Number(vocabCurrentIndex)
          || clean(vocabActiveHintPhase) !== clean(vocabPhase)
        ) {
          return;
        }
        const chip = vocabMeta.querySelector(`[data-vocab-hint-kind="${vocabActiveHintKind}"]`);
        if (!chip) {
          return;
        }
        chip.classList.remove("is-placeholder");
        chip.removeAttribute("aria-hidden");
        chip.classList.add("is-hint-active");
        if (vocabActiveHintKind === "type") {
          chip.classList.add("is-type-float");
        }
      };

      const setVocabActiveHint = (kind, item = (vocabItems[vocabCurrentIndex] || null), index = vocabCurrentIndex) => {
        const cleanKind = clean(kind);
        if (!cleanKind || !item || Number(index) !== Number(vocabCurrentIndex)) {
          return;
        }
        vocabActiveHintKind = cleanKind;
        vocabActiveHintIndex = Number(index);
        vocabActiveHintPhase = clean(vocabPhase);
        applyVocabActiveHint();
      };

      const scheduleVocabTypeHintTimer = (item, absoluteIndex) => {
        vocabIdleHintToken += 1;
        if (vocabIdleHintTimer) {
          window.clearTimeout(vocabIdleHintTimer);
          vocabIdleHintTimer = 0;
        }
        if (!item || !clean(item.type)) {
          return;
        }
        const token = vocabIdleHintToken;
        const questionToken = vocabQuestionToken;
        const index = Number(absoluteIndex);
        const phase = clean(vocabPhase);
        const wordKey = vocabWordKey(item);
        vocabIdleHintTimer = window.setTimeout(() => {
          vocabIdleHintTimer = 0;
          if (
            token !== vocabIdleHintToken
            || questionToken !== vocabQuestionToken
            || Number(vocabCurrentIndex) !== index
            || clean(vocabPhase) !== phase
            || vocabWordKey(vocabItems[vocabCurrentIndex] || null) !== wordKey
            || vocabCurrentAnswerIsSolved(item)
          ) {
            return;
          }
          setVocabActiveHint("type", item, index);
        }, 5000);
      };

      const vocabLetterCount = (item) => clean(item && item.word ? item.word : "").replace(/\s+/g, "").length;

      const routeAfterVocabUnlearned = () => {
        clearVocabHintTimers();
        if (vocabStudyIndexes.length >= VOCAB_BATCH_SIZE) {
          startVocabDrill();
        } else {
          startNextVocabProbe();
        }
      };

      const scheduleVocabProbeHintTimers = (item, absoluteIndex) => {
        clearVocabHintTimers(false);
        if (!item || vocabPhase !== "probe") {
          if (vocabTimer) {
            vocabTimer.classList.add("is-hidden");
          }
          return;
        }
        const token = ++vocabHintToken;
        const questionToken = vocabQuestionToken;
        const index = Number(absoluteIndex);
        const wordKey = vocabWordKey(item);
        const letters = vocabLetterCount(item);
        const firstLetter = clean(item.word).trim().charAt(0);
        const expected = normalize(item.word);
        const isSolvedText = () => Boolean(vocabAnswer && normalize(vocabAnswer.value) === expected);
        const sameQuestion = () => (
          token === vocabHintToken
          && questionToken === vocabQuestionToken
          && vocabPhase === "probe"
          && vocabCurrentIndex === index
          && vocabWordKey(vocabItems[vocabCurrentIndex] || null) === wordKey
        );
        const isActive = () => sameQuestion() && !isSolvedText();
        setVocabTimerState("Clock armed. Three markers unlock help during one orbit.");
        restartVocabTimerClock();
        vocabHintTimers = [
          window.setTimeout(() => {
            if (!isActive()) {
              return;
            }
            renderVocabMeta(item, [`Hint: ${letters} letters`]);
            setVocabActiveHint("letters", item, index);
            setVocabTimerState(`Marker 1: ${letters} letters.`, "alert");
            setVocabFeedback("Hint unlocked: word length.", "error");
          }, 15000),
          window.setTimeout(() => {
            if (!isActive()) {
              return;
            }
            renderVocabMeta(item, [`Hint: ${letters} letters`, `First letter: ${firstLetter || "?"}`]);
            setVocabActiveHint("first-letter", item, index);
            setVocabTimerState(`Marker 2: first letter ${firstLetter || "?"}.`, "alert");
            setVocabFeedback("Signal boost unlocked: first letter.", "error");
          }, 25000),
          window.setTimeout(async () => {
            if (!isActive()) {
              return;
            }
            vocabAutoRevealLock = true;
            addVocabUnlearnedIndex(index);
            revealVocabAnswerMeta(item, [`Hint: ${letters} letters`, `First letter: ${firstLetter || "?"}`, `Answer: ${item.word}`]);
            setVocabTimerState("Final marker: answer revealed and routed to training.", "answer");
            setVocabFeedback("Answer revealed. Added to Unlearned Words.", "error");
            if (vocabAnswer) {
              vocabAnswer.value = item.word;
            }
            vocabAnswerBusy = true;
            setVocabInputLocked(true);
            await playEffectSoundAsync("false");
            await playVocabAudio();
            vocabAnswerBusy = false;
            setVocabInputLocked(false);
            if (sameQuestion()) {
              routeAfterVocabUnlearned();
            }
          }, 45000),
        ];
      };

      const resetVocabUnlearnedPanelPosition = () => {
        if (!vocabUnlearnedPanel) {
          return;
        }
        ["left", "top", "right", "bottom", "width", "max-height"].forEach((name) => vocabUnlearnedPanel.style.removeProperty(name));
        if (vocabUnlearnedList) {
          vocabUnlearnedList.style.removeProperty("max-height");
        }
      };

      const positionVocabUnlearnedPanel = () => {
        if (!vocabUnlearnedPanel || !shellNode || !vocabCard) {
          return;
        }
        if (vocabUnlearnedPanel.classList.contains("is-hidden") || isMobilePanelFlow()) {
          resetVocabUnlearnedPanelPosition();
          return;
        }
        const layout = vocabAnchorLayout();
        if (!layout) {
          return;
        }
        const { shellRect, cardRect, viewportHeight, topRail } = layout;
        const slot = layout.sideSlot("right", {
          preferred: Math.max(238, Math.min(330, Math.round(layout.viewportWidth * 0.235))),
          minimum: 190,
        }) || layout.sideSlot("left", { preferred: 300, minimum: 190 })
          || layout.fallbackBelow(cardRect.bottom - shellRect.top + 12, cardRect.width);
        const top = slot.side === "below" ? slot.top : layout.clampTop(topRail, 150);
        const maxHeight = Math.max(140, Math.min(330, viewportHeight - shellRect.top - top - 16));
        vocabUnlearnedPanel.style.right = "auto";
        vocabUnlearnedPanel.style.bottom = "auto";
        vocabUnlearnedPanel.style.left = `${Math.round(slot.left)}px`;
        vocabUnlearnedPanel.style.top = `${Math.round(top)}px`;
        vocabUnlearnedPanel.style.width = `${Math.round(slot.width)}px`;
        vocabUnlearnedPanel.style.maxHeight = `${Math.round(maxHeight)}px`;
        if (vocabUnlearnedList) {
          vocabUnlearnedList.style.maxHeight = `${Math.max(74, Math.round(maxHeight - 116))}px`;
        }
      };

      const positionVocabWeakConnector = () => {
        if (!vocabWeakConnector || !vocabWeakPath || !shellNode || !vocabCard || !vocabUnlearnedPanel) {
          return;
        }
        if (vocabWeakConnector.classList.contains("is-hidden") || vocabUnlearnedPanel.classList.contains("is-hidden")) {
          return;
        }
        if (isMobilePanelFlow()) {
          resetVocabUnlearnedPanelPosition();
          return;
        }
        positionVocabUnlearnedPanel();
        const shellRect = shellNode.getBoundingClientRect();
        const cardRect = vocabCard.getBoundingClientRect();
        const panelRect = vocabUnlearnedPanel.getBoundingClientRect();
        if (!shellRect.width || !cardRect.width || !panelRect.width) {
          return;
        }
        const panelOnLeft = panelRect.left + (panelRect.width / 2) < cardRect.left + (cardRect.width / 2);
        const startX = panelOnLeft ? cardRect.left - shellRect.left + 16 : cardRect.right - shellRect.left - 16;
        const startY = cardRect.top - shellRect.top + Math.min(cardRect.height * 0.3, 92);
        const endX = panelOnLeft ? panelRect.right - shellRect.left - 12 : panelRect.left - shellRect.left + 12;
        const endY = panelRect.top - shellRect.top + Math.min(panelRect.height * 0.5, 128);
        const curve = Math.max(52, Math.min(170, Math.abs(endX - startX) * 0.45));
        vocabWeakPath.setAttribute("d", panelOnLeft
          ? `M ${startX} ${startY} C ${startX - curve} ${startY - 18}, ${endX + curve} ${endY + 18}, ${endX} ${endY}`
          : `M ${startX} ${startY} C ${startX + curve} ${startY - 18}, ${endX - curve} ${endY + 18}, ${endX} ${endY}`);
      };

      const resetVocabSideCardPositions = () => {
        [vocabDetailPanel, vocabPicturePanel].forEach((panel) => {
          if (!panel) {
            return;
          }
          ["left", "top", "right", "bottom", "width", "max-height"].forEach((name) => panel.style.removeProperty(name));
        });
      };

      const vocabSideCardsVisible = () => vocabModeActive && vocabPhase === "drill";
      const vocabDetailCardVisible = () => vocabSideCardsVisible() && Boolean(vocabCurrentHadError);

      const hideVocabSideConnectors = () => {
        if (vocabSideConnector) {
          vocabSideConnector.classList.add("is-hidden");
        }
        [vocabDetailPath, vocabPicturePath].forEach((path) => {
          if (path) {
            path.style.display = "none";
          }
        });
      };

      const positionVocabSideConnectors = (shellRect, cardRect) => {
        if (!vocabSideConnector || !vocabDetailPath || !vocabPicturePath || isMobilePanelFlow()) {
          hideVocabSideConnectors();
          return;
        }
        const detailVisible = Boolean(vocabDetailPanel && !vocabDetailPanel.classList.contains("is-hidden"));
        const pictureVisible = Boolean(vocabPicturePanel && !vocabPicturePanel.classList.contains("is-hidden"));
        vocabSideConnector.classList.toggle("is-hidden", !(detailVisible || pictureVisible));
        if (detailVisible) {
          const detailRect = vocabDetailPanel.getBoundingClientRect();
          const startX = cardRect.left - shellRect.left + 16;
          const startY = cardRect.top - shellRect.top + Math.min(cardRect.height * 0.24, 76);
          const endX = detailRect.right - shellRect.left - 12;
          const endY = detailRect.top - shellRect.top + Math.min(detailRect.height * 0.56, 140);
          const curve = Math.max(48, Math.min(150, Math.abs(endX - startX) * 0.45));
          vocabDetailPath.style.display = "";
          vocabDetailPath.setAttribute("d", `M ${startX} ${startY} C ${startX - curve} ${startY - 12}, ${endX + curve} ${endY + 18}, ${endX} ${endY}`);
        } else {
          vocabDetailPath.style.display = "none";
        }
        if (pictureVisible) {
          const pictureRect = vocabPicturePanel.getBoundingClientRect();
          const startX = cardRect.right - shellRect.left - 18;
          const startY = cardRect.bottom - shellRect.top - Math.min(cardRect.height * 0.24, 82);
          const endX = pictureRect.left - shellRect.left + 12;
          const endY = pictureRect.top - shellRect.top + Math.min(pictureRect.height * 0.35, 92);
          const curve = Math.max(56, Math.min(170, Math.abs(endX - startX) * 0.42));
          vocabPicturePath.style.display = "";
          vocabPicturePath.setAttribute("d", `M ${startX} ${startY} C ${startX + curve} ${startY + 18}, ${endX - curve} ${endY - 18}, ${endX} ${endY}`);
        } else {
          vocabPicturePath.style.display = "none";
        }
      };

      const positionVocabSideCards = () => {
        if (!shellNode || !vocabCard) {
          return;
        }
        if (isMobilePanelFlow()) {
          resetVocabSideCardPositions();
          hideVocabSideConnectors();
          positionVocabLearnedPanel();
          return;
        }
        const shellRect = shellNode.getBoundingClientRect();
        const cardRect = vocabCard.getBoundingClientRect();
        if (!shellRect.width || !cardRect.width) {
          return;
        }
        positionVocabLearnedPanel();
        positionVocabUnlearnedPanel();
        const layout = vocabAnchorLayout();
        if (!layout) {
          return;
        }
        if (vocabDetailPanel && !vocabDetailPanel.classList.contains("is-hidden")) {
          const detailRect = vocabDetailPanel.getBoundingClientRect();
          const slot = layout.sideSlot("left", {
            preferred: Math.max(240, Math.min(360, Math.round(layout.viewportWidth * 0.25))),
            minimum: 190,
          }) || layout.sideSlot("right", { preferred: 320, minimum: 190 })
            || layout.fallbackBelow(cardRect.bottom - shellRect.top + 14, cardRect.width);
          const width = slot.width;
          const left = slot.left;
          const top = slot.side === "below"
            ? slot.top
            : layout.clampTop(layout.bottomRail, Math.max(160, detailRect.height));
          const maxHeight = Math.max(130, Math.min(300, layout.viewportHeight - shellRect.top - top - 14));
          vocabDetailPanel.style.width = `${Math.round(width)}px`;
          vocabDetailPanel.style.maxHeight = `${Math.round(maxHeight)}px`;
          vocabDetailPanel.style.left = `${Math.round(left)}px`;
          vocabDetailPanel.style.top = `${Math.round(top)}px`;
          vocabDetailPanel.style.right = "auto";
          vocabDetailPanel.style.bottom = "auto";
        }
        if (vocabPicturePanel && !vocabPicturePanel.classList.contains("is-hidden")) {
          const pictureRect = vocabPicturePanel.getBoundingClientRect();
          const unlearnedRect = vocabUnlearnedPanel && !vocabUnlearnedPanel.classList.contains("is-hidden")
            ? vocabUnlearnedPanel.getBoundingClientRect()
            : null;
          const slot = layout.sideSlot("right", {
            preferred: Math.max(230, Math.min(330, Math.round(layout.viewportWidth * 0.235))),
            minimum: 190,
          }) || layout.sideSlot("left", { preferred: 300, minimum: 190 })
            || layout.fallbackBelow(cardRect.bottom - shellRect.top + 14, cardRect.width);
          const width = slot.width;
          const topAnchor = unlearnedRect && slot.side !== "below"
            ? unlearnedRect.bottom - shellRect.top + 10
            : layout.bottomRail;
          const top = slot.side === "below"
            ? slot.top
            : layout.clampTop(Math.max(topAnchor, cardRect.bottom - shellRect.top - Math.min(pictureRect.height, 180)), Math.max(160, pictureRect.height));
          const maxHeight = Math.max(140, Math.min(320, layout.viewportHeight - shellRect.top - top - 14));
          vocabPicturePanel.style.width = `${Math.round(width)}px`;
          vocabPicturePanel.style.maxHeight = `${Math.round(maxHeight)}px`;
          vocabPicturePanel.style.left = `${Math.round(slot.left)}px`;
          vocabPicturePanel.style.top = `${Math.round(top)}px`;
          vocabPicturePanel.style.right = "auto";
          vocabPicturePanel.style.bottom = "auto";
        }
        positionVocabSideConnectors(shellRect, cardRect);
      };

      const maskVocabAnswerText = (text, item) => {
        return clean(text);
      };

      const renderVocabDetailCard = (item) => {
        if (!vocabDetailPanel || !vocabDetailWord || !vocabDetailList) {
          return;
        }
        const rawEntries = item && item.detail && Array.isArray(item.detail.items) ? item.detail.items : [];
        const fallbackEntries = item ? [
          item.type ? { kind: "pos", text: item.type } : null,
          item.meaning ? { kind: "def", text: item.meaning } : null,
          item.pron ? { kind: "ipa", text: `IPA ${item.pron}` } : null,
        ].filter(Boolean) : [];
        const entries = rawEntries.length ? rawEntries : fallbackEntries;
        const shouldShow = Boolean(vocabDetailCardVisible() && entries.length);
        vocabDetailPanel.classList.toggle("is-hidden", !shouldShow);
        vocabDetailList.textContent = "";
        if (!shouldShow) {
          return;
        }
        vocabDetailWord.textContent = item.word;
        entries.forEach((entry) => {
          const row = document.createElement("div");
          row.className = "ft-vocab-detail-row";
          const kind = clean(entry.kind ?? entry.k ?? "line") || "line";
          const text = clean(entry.text ?? entry.t ?? "");
          const enText = clean(entry.en ?? entry.e ?? text);
          const viText = clean(entry.vi ?? entry.v ?? "");
          row.dataset.kind = kind;
          if (kind === "ex") {
            const en = document.createElement("span");
            en.textContent = maskVocabAnswerText(enText || text, item);
            row.appendChild(en);
            if (viText) {
              const vi = document.createElement("small");
              vi.textContent = viText;
              row.appendChild(vi);
            }
          } else {
            row.textContent = maskVocabAnswerText(text || enText || viText, item);
          }
          vocabDetailList.appendChild(row);
        });
        window.requestAnimationFrame(positionVocabSideCards);
      };

      // 2026-07-21: Request durable browser storage without making lesson execution depend on permission or quota.
      const ensureOfflineStoragePersistence = (forceRefresh = false) => {
        const now = Date.now();
        if (
          offlineStoragePersistencePromise
          && !forceRefresh
          && now - offlineStorageLastCheckedAt < OFFLINE_STORAGE_ESTIMATE_REFRESH_MS
        ) {
          return offlineStoragePersistencePromise;
        }
        offlineStorageLastCheckedAt = now;
        offlineStoragePersistencePromise = (async () => {
          let persistent = false;
          let usage = 0;
          let quota = 0;
          try {
            if (navigator.storage && typeof navigator.storage.persisted === "function") {
              persistent = Boolean(await navigator.storage.persisted());
            }
            if (!persistent && navigator.storage && typeof navigator.storage.persist === "function") {
              persistent = Boolean(await navigator.storage.persist());
            }
            if (navigator.storage && typeof navigator.storage.estimate === "function") {
              const estimate = await navigator.storage.estimate();
              usage = Math.max(0, Number(estimate && estimate.usage || 0) || 0);
              quota = Math.max(0, Number(estimate && estimate.quota || 0) || 0);
            }
          } catch (error) {
          }
          const ratio = quota > 0 ? usage / quota : 0;
          offlineStoragePressure = ratio >= 0.85 ? "critical" : (ratio >= 0.7 ? "high" : "normal");
          window.__futureOfflineStorageState = {
            persistent,
            limited: offlineStoragePressure === "critical" && Boolean(window.__futureOfflineStorageState && window.__futureOfflineStorageState.limited),
            pressure: offlineStoragePressure,
            usage,
            quota,
            checkedAt: Date.now(),
          };
          if (offlineStoragePressure !== "normal") {
            void (async () => {
              await pruneVocabImageCache();
              if (typeof pruneSpaceWAudioCache === "function") {
                await pruneSpaceWAudioCache({ pressure: offlineStoragePressure });
              }
            })();
          }
          return window.__futureOfflineStorageState;
        })();
        return offlineStoragePersistencePromise;
      };

      // 2026-07-21: Persist secondary images with bounded IndexedDB LRU so offline study never depends on them.
      const openVocabImageDb = () => {
        if (vocabImageDbPromise) {
          return vocabImageDbPromise;
        }
        if (!("indexedDB" in window)) {
          return Promise.reject(new Error("IndexedDB unavailable."));
        }
        vocabImageDbPromise = new Promise((resolve, reject) => {
          const request = indexedDB.open(VOCAB_IMAGE_DB_NAME, VOCAB_IMAGE_DB_VERSION);
          request.onupgradeneeded = () => {
            const db = request.result;
            const store = db.objectStoreNames.contains(VOCAB_IMAGE_DB_STORE)
              ? request.transaction.objectStore(VOCAB_IMAGE_DB_STORE)
              : db.createObjectStore(VOCAB_IMAGE_DB_STORE, { keyPath: "key" });
            // 2026-07-30: remove every previously downloaded Internet vocabulary image during the local-only cutover.
            if (Number(request.oldVersion || 0) < 3) {
              store.clear();
            }
            if (!store.indexNames.contains("accessAt")) {
              store.createIndex("accessAt", "accessAt", { unique: false });
            }
            if (!store.indexNames.contains("assetId")) {
              store.createIndex("assetId", "assetId", { unique: true });
            }
          };
          request.onsuccess = () => {
            const db = request.result;
            db.onversionchange = () => {
              try { db.close(); } catch (error) {}
              vocabImageDbPromise = null;
            };
            if ("onclose" in db) {
              db.onclose = () => { vocabImageDbPromise = null; };
            }
            resolve(db);
          };
          request.onerror = () => {
            vocabImageDbPromise = null;
            reject(request.error || new Error("Vocabulary image cache unavailable."));
          };
        });
        return vocabImageDbPromise;
      };

      const deleteVocabImageRecord = async (assetId) => {
        try {
          const db = await openVocabImageDb();
          await new Promise((resolve, reject) => {
            const request = db.transaction(VOCAB_IMAGE_DB_STORE, "readwrite").objectStore(VOCAB_IMAGE_DB_STORE).delete(assetId);
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
          });
        } catch (error) {
        }
      };

      const rememberVocabImageBlobUrl = (assetId, blob) => {
        if (!assetId || !(blob instanceof Blob) || !blob.size) {
          return "";
        }
        const previous = vocabImageBlobUrls.get(assetId);
        if (previous) {
          URL.revokeObjectURL(previous);
          vocabImageBlobUrls.delete(assetId);
        }
        const url = URL.createObjectURL(blob);
        vocabImageBlobUrls.set(assetId, url);
        while (vocabImageBlobUrls.size > 32) {
          const oldestKey = vocabImageBlobUrls.keys().next().value;
          const oldestUrl = vocabImageBlobUrls.get(oldestKey);
          if (oldestUrl) {
            URL.revokeObjectURL(oldestUrl);
          }
          vocabImageBlobUrls.delete(oldestKey);
        }
        return url;
      };

      const pruneVocabImageCache = async () => {
        try {
          const db = await openVocabImageDb();
          let byteLimit = VOCAB_IMAGE_CACHE_MAX_BYTES;
          if (navigator.storage && typeof navigator.storage.estimate === "function") {
            const estimate = await navigator.storage.estimate().catch(() => null);
            const quota = Number(estimate && estimate.quota || 0);
            if (quota > 0) {
              byteLimit = Math.max(8 * 1024 * 1024, Math.min(byteLimit, Math.floor(quota * 0.03)));
            }
          }
          let keptBytes = 0;
          let keptEntries = 0;
          const removeKeys = [];
          // 2026-07-21: cursor pruning keeps peak RAM bounded even when an old browser cache is hundreds of MB.
          await new Promise((resolve, reject) => {
            const transaction = db.transaction(VOCAB_IMAGE_DB_STORE, "readonly");
            const store = transaction.objectStore(VOCAB_IMAGE_DB_STORE);
            const source = store.indexNames.contains("accessAt") ? store.index("accessAt") : store;
            const request = source.openCursor(null, "prev");
            request.onsuccess = () => {
              const cursor = request.result;
              if (!cursor) {
                resolve(true);
                return;
              }
              const row = cursor.value && typeof cursor.value === "object" ? cursor.value : {};
              const bytes = Math.max(0, Number(row.bytes || (row.blob && row.blob.size) || 0) || 0);
              if (keptEntries >= VOCAB_IMAGE_CACHE_MAX_ENTRIES || keptBytes + bytes > byteLimit) {
                removeKeys.push(clean(row.key));
              } else {
                keptEntries += 1;
                keptBytes += bytes;
              }
              cursor.continue();
            };
            request.onerror = () => reject(request.error);
          });
          if (!removeKeys.length) {
            return { removed: 0, keptEntries, keptBytes, byteLimit };
          }
          await new Promise((resolve) => {
            const transaction = db.transaction(VOCAB_IMAGE_DB_STORE, "readwrite");
            const store = transaction.objectStore(VOCAB_IMAGE_DB_STORE);
            removeKeys.forEach((key) => key && store.delete(key));
            transaction.oncomplete = () => resolve(true);
            transaction.onerror = () => resolve(false);
            transaction.onabort = () => resolve(false);
          });
          return { removed: removeKeys.length, keptEntries, keptBytes, byteLimit };
        } catch (error) {
          return { removed: 0, keptEntries: 0, keptBytes: 0, byteLimit: 0, error: clean(error && (error.name || error.message)) };
        }
      };

      const vocabImageAssetId = (wordKey = "") => `vocab-image:${clean(wordKey).toLowerCase()}`;

      const vocabImageBlobSha256 = async (blob) => {
        if (!(blob instanceof Blob) || !blob.size || !window.crypto || !crypto.subtle) {
          return "";
        }
        const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
        return `sha256:${Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
      };

      const readVocabImageRecord = async (assetId) => {
        if (!assetId) {
          return null;
        }
        try {
          const db = await openVocabImageDb();
          const record = await new Promise((resolve, reject) => {
            const request = db.transaction(VOCAB_IMAGE_DB_STORE, "readonly").objectStore(VOCAB_IMAGE_DB_STORE).get(assetId);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
          });
          const image = normalizeVocabularyImage(record && record.image);
          const blob = record && record.blob;
          if (
            !record
            || Number(record.mediaKeyVersion || 0) !== VOCAB_IMAGE_MEDIA_KEY_VERSION
            || clean(record.assetId) !== assetId
            || !/^sha256:[a-f0-9]{64}$/i.test(clean(record.contentHash))
            || !(blob instanceof Blob)
            || !blob.size
            || Number(record.bytes || 0) !== blob.size
            || !/^image\//i.test(clean(blob.type))
            || clean(record.mimeType) !== clean(blob.type)
            || !image.url
          ) {
            if (record) {
              void deleteVocabImageRecord(assetId);
            }
            return null;
          }
          const actualHash = await vocabImageBlobSha256(blob);
          if (!actualHash || actualHash !== clean(record.contentHash)) {
            void deleteVocabImageRecord(assetId);
            return null;
          }
          const blobUrl = rememberVocabImageBlobUrl(assetId, blob);
          if (!blobUrl) {
            return null;
          }
          if (Date.now() - Number(record.accessAt || 0) > 60 * 60 * 1000) {
            record.accessAt = Date.now();
            try {
              db.transaction(VOCAB_IMAGE_DB_STORE, "readwrite").objectStore(VOCAB_IMAGE_DB_STORE).put(record);
            } catch (error) {
            }
          }
          return {
            ...image,
            url: blobUrl,
            remoteUrl: image.url,
            assetId,
            contentHash: clean(record.contentHash),
            bytes: blob.size,
            mimeType: clean(blob.type),
            persistent: true,
          };
        } catch (error) {
          return null;
        }
      };

      const fetchAndPersistVocabImage = async (assetId, image, assetMetadata = {}) => {
        const normalized = normalizeVocabularyImage(image);
        const remoteUrl = resolveServerAssetUrl(normalized.url);
        if (!assetId || !remoteUrl || remoteUrl.startsWith("data:") || remoteUrl.startsWith("blob:")) {
          return normalized;
        }
        try {
          const storageState = await ensureOfflineStoragePersistence();
          if (storageState && storageState.pressure === "critical") {
            return normalized;
          }
          const response = await fetch(remoteUrl, { cache: "force-cache", headers: { "Accept": "image/*,*/*" } });
          if (!response.ok) {
            return normalized;
          }
          const blob = await response.blob();
          if (!(blob instanceof Blob) || !blob.size || blob.size > 5 * 1024 * 1024 || !/^image\//i.test(clean(blob.type))) {
            return normalized;
          }
          const contentHash = await vocabImageBlobSha256(blob);
          if (!contentHash) {
            return normalized;
          }
          const now = Date.now();
          const db = await openVocabImageDb();
          const record = {
            key: assetId,
            assetId,
            mediaKeyVersion: VOCAB_IMAGE_MEDIA_KEY_VERSION,
            contentHash,
            metadataRevision: clean(assetMetadata.metadata_revision || assetMetadata.metadataRevision || ""),
            image: normalized,
            blob,
            bytes: blob.size,
            mimeType: clean(blob.type),
            savedAt: now,
            accessAt: now,
          };
          const writeRecord = () => new Promise((resolve, reject) => {
            const request = db.transaction(VOCAB_IMAGE_DB_STORE, "readwrite").objectStore(VOCAB_IMAGE_DB_STORE).put({
              ...record,
            });
            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
          });
          try {
            await writeRecord();
          } catch (writeError) {
            if (clean(writeError && writeError.name) !== "QuotaExceededError") {
              throw writeError;
            }
            await pruneVocabImageCache();
            try {
              await writeRecord();
            } catch (retryError) {
              offlineStoragePressure = "critical";
              window.__futureOfflineStorageState = {
                ...(window.__futureOfflineStorageState || {}),
                limited: true,
                pressure: "critical",
                lastError: clean(retryError && (retryError.name || retryError.message) || "QuotaExceededError"),
                checkedAt: Date.now(),
              };
              return normalized;
            }
          }
          vocabImagePersistentWrites += 1;
          if (vocabImagePersistentWrites % 8 === 0) {
            void ensureOfflineStoragePersistence(true).then(() => pruneVocabImageCache());
          }
          const blobUrl = rememberVocabImageBlobUrl(assetId, blob);
          return blobUrl ? {
            ...normalized,
            url: blobUrl,
            remoteUrl: normalized.url,
            assetId,
            contentHash,
            bytes: blob.size,
            mimeType: clean(blob.type),
            persistent: true,
          } : normalized;
        } catch (error) {
          return normalized;
        }
      };

      // 2026-07-21: Predict one real next Space_V item without expanding speculative server work.
      const nextLikelyVocabImageItem = () => {
        let index = -1;
        if (vocabPhase === "drill") {
          index = Number(vocabStudyIndexes[vocabDrillIndex + 1]);
        } else if (vocabPhase === "shuffle") {
          index = Number(vocabShuffleQueue[0]);
        } else {
          index = Number(vocabQueue.find((candidate) => vocabCanProbeIndex(candidate)));
        }
        return Number.isInteger(index) && index >= 0 ? vocabItemByIndex(index) : null;
      };

      // 2026-07-21: Keep one decoded next image client-side; metadata prefetch alone does not fetch image bytes.
      const prefetchVocabImageBytes = (image) => {
        const url = resolveServerAssetUrl(image && image.url ? image.url : "");
        if (!url || vocabImageBytePrefetches.has(url)) {
          return;
        }
        const preload = new Image();
        preload.decoding = "async";
        vocabImageBytePrefetches.set(url, preload);
        while (vocabImageBytePrefetches.size > 12) {
          vocabImageBytePrefetches.delete(vocabImageBytePrefetches.keys().next().value);
        }
        preload.onerror = () => vocabImageBytePrefetches.delete(url);
        preload.src = url;
      };

      const ensureVocabItemImageLazy = (item, options = {}) => {
        if (!item || !item.word) {
          return;
        }
        const existing = normalizeVocabularyImage(item.image || {});
        if (existing.url && (item.imageGalleryLoaded || clean(existing.source).toLowerCase() !== "local picture folder")) {
          if (options.prefetchBytes) {
            prefetchVocabImageBytes(existing);
          }
          return;
        }
        const key = vocabWordKey(item);
        const cachedResult = vocabImageResultCache.get(key);
        if (cachedResult && Number(cachedResult.expiresAt || 0) > Date.now()) {
          if (cachedResult.image && cachedResult.image.url) {
            item.image = cachedResult.image;
            item.images = Array.isArray(cachedResult.images) ? cachedResult.images.map(normalizeVocabularyImage).filter((entry) => entry.url) : [cachedResult.image];
            item.imageSelectedIndex = Math.max(0, Math.min(item.images.length - 1, Number(cachedResult.selectedIndex || 0) || 0));
            item.imageGalleryLoaded = true;
            if (options.prefetchBytes) {
              prefetchVocabImageBytes(cachedResult.image);
            }
            const current = currentVocabItem();
            if (vocabSideCardsVisible() && current && vocabWordKey(current) === key) {
              renderVocabPictureCard(item);
            }
          }
          return;
        }
        if (cachedResult) {
          vocabImageResultCache.delete(key);
        }
        if (!key || vocabImageFetchInflight.has(key)) {
          return;
        }
        const assetId = vocabImageAssetId(key);
        const token = ++vocabImageLoadToken;
        vocabImageFetchInflight.add(key);
        (async () => {
          const persistentImage = await readVocabImageRecord(assetId);
          if (persistentImage && persistentImage.url) {
            vocabImageRetryCounts.delete(key);
            vocabImageResultCache.set(key, {
              image: persistentImage,
              expiresAt: Date.now() + 24 * 60 * 60 * 1000,
            });
            item.image = persistentImage;
            if (options.prefetchBytes) {
              prefetchVocabImageBytes(persistentImage);
            }
            const current = currentVocabItem();
            if (current && vocabWordKey(current) === key && token <= vocabImageLoadToken) {
              renderVocabPictureCard(item);
              window.requestAnimationFrame(positionVocabSideCards);
            }
          }
          const result = await fetchServerJson(`/vocab/image?word=${encodeURIComponent(item.word)}`);
          const payload = result && result.payload && typeof result.payload === "object" ? result.payload : result;
          const image = normalizeVocabularyImage(payload && payload.image);
          const images = Array.isArray(payload && payload.images)
            ? payload.images.map(normalizeVocabularyImage).filter((entry) => entry.url)
            : [];
          if (payload && payload.pending) {
            const attempts = Number(vocabImageRetryCounts.get(key) || 0) + 1;
            const retryMs = Math.max(800, Math.min(5000, Number(payload.retry_after_ms || 1400) || 1400));
            vocabImageRetryCounts.set(key, attempts);
            vocabImageResultCache.set(key, {
              image: null,
              expiresAt: Date.now() + retryMs,
            });
            if (attempts <= 12) {
              window.setTimeout(() => {
                const current = currentVocabItem();
                if (current && vocabWordKey(current) === key) {
                  vocabImageResultCache.delete(key);
                  ensureVocabItemImageLazy(current);
                }
              }, retryMs + 40);
            } else {
              vocabImageRetryCounts.delete(key);
              vocabImageResultCache.set(key, { image: null, expiresAt: Date.now() + 10 * 60 * 1000 });
            }
            return;
          }
          vocabImageRetryCounts.delete(key);
          const serverAsset = payload && payload.asset && typeof payload.asset === "object" ? payload.asset : {};
          // Local picture responses use normal HTTP caching; do not download a second copy into IndexedDB.
          const selectedIndex = Math.max(0, Math.min(Math.max(0, images.length - 1), Number(payload && payload.selected_index || 0) || 0));
          const displayImage = images[selectedIndex] || image;
          vocabImageResultCache.set(key, {
            image: displayImage.url ? displayImage : null,
            images,
            selectedIndex,
            expiresAt: Date.now() + (image.url ? 24 * 60 * 60 * 1000 : 10 * 60 * 1000),
          });
          while (vocabImageResultCache.size > 512) {
            vocabImageResultCache.delete(vocabImageResultCache.keys().next().value);
          }
          if (!displayImage.url) {
            return;
          }
          item.image = displayImage;
          item.images = images.length ? images : [displayImage];
          item.imageSelectedIndex = selectedIndex;
          item.imageGalleryLoaded = true;
          if (options.prefetchBytes) {
            prefetchVocabImageBytes(displayImage);
          }
          const current = currentVocabItem();
          if (current && vocabWordKey(current) === key && token <= vocabImageLoadToken) {
            renderVocabPictureCard(item);
            window.requestAnimationFrame(positionVocabSideCards);
          }
          })()
          .catch(() => {})
          .finally(() => {
            vocabImageFetchInflight.delete(key);
          });
      };

      // 2026-07-21: Start bounded next-image work only after the current image is visibly ready.
      const scheduleNextVocabImagePrefetch = (item) => {
        if (vocabImagePrefetchTimer) {
          window.clearTimeout(vocabImagePrefetchTimer);
        }
        const currentKey = vocabWordKey(item);
        vocabImagePrefetchTimer = window.setTimeout(() => {
          vocabImagePrefetchTimer = 0;
          const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
          if (
            !vocabModeActive
            || !currentKey
            || vocabWordKey(currentVocabItem()) !== currentKey
            || offlineStoragePressure === "high"
            || offlineStoragePressure === "critical"
            || (connection && (connection.saveData || /(^|-)2g$/i.test(clean(connection.effectiveType))))
          ) {
            return;
          }
          const nextItem = nextLikelyVocabImageItem();
          if (!nextItem || vocabWordKey(nextItem) === currentKey) {
            return;
          }
          ensureVocabItemImageLazy(nextItem, { prefetchBytes: true });
        }, 120);
      };

      let vocabImageLightboxReturnFocus = null;
      let vocabImageLightboxState = { itemKey: "", word: "", images: [], index: 0, initialIndex: 0 };

      const renderVocabImageLightboxSlide = () => {
        const images = Array.isArray(vocabImageLightboxState.images) ? vocabImageLightboxState.images : [];
        const index = Math.max(0, Math.min(Math.max(0, images.length - 1), Number(vocabImageLightboxState.index || 0) || 0));
        const image = images[index] || {};
        vocabImageLightboxState.index = index;
        if (vocabImageLightboxImg) {
          vocabImageLightboxImg.src = resolveServerAssetUrl(image.url || "");
          vocabImageLightboxImg.alt = clean(vocabImageLightboxMeaning && vocabImageLightboxMeaning.textContent) || clean(vocabImageLightboxState.word) || "Vocabulary image";
        }
        if (vocabImageLightboxCaption) vocabImageLightboxCaption.textContent = [image.source || "Image signal", image.credit].filter(Boolean).join(" | ");
        if (vocabImageLightboxPage) vocabImageLightboxPage.textContent = `${images.length ? index + 1 : 0} / ${images.length}`;
        const multiple = images.length > 1;
        if (vocabImageLightboxPrev) vocabImageLightboxPrev.disabled = !multiple;
        if (vocabImageLightboxNext) vocabImageLightboxNext.disabled = !multiple;
      };

      const stepVocabImageLightbox = (delta = 1) => {
        const total = vocabImageLightboxState.images.length;
        if (total <= 1) return false;
        vocabImageLightboxState.index = (vocabImageLightboxState.index + (delta < 0 ? -1 : 1) + total) % total;
        renderVocabImageLightboxSlide();
        return true;
      };

      // 2026-08-04: opens the active Space_V visual in a dedicated near-fullscreen study lightbox.
      const openVocabImageLightbox = () => {
        if (!vocabImageLightbox || !vocabImageLightboxImg || !vocabPictureImg || !vocabPicturePanel) return false;
        const src = clean(vocabPictureImg.currentSrc || vocabPictureImg.getAttribute("src") || "");
        if (!src || vocabPicturePanel.classList.contains("is-hidden")) return false;
        const item = currentVocabItem() || {};
        const images = (Array.isArray(item.images) ? item.images : [item.image]).map(normalizeVocabularyImage).filter((image) => image.url);
        if (!images.length) return false;
        const selectedId = clean(item.image && item.image.id);
        const selectedIdIndex = images.findIndex((image) => selectedId && clean(image.id).toLowerCase() === selectedId.toLowerCase());
        const fallbackIndex = Math.max(0, Math.min(images.length - 1, Number(item.imageSelectedIndex || 0) || 0));
        const selectedIndex = selectedIdIndex >= 0 ? selectedIdIndex : fallbackIndex;
        vocabImageLightboxState = {
          itemKey: vocabWordKey(item),
          word: clean(item.word),
          images,
          index: selectedIndex,
          initialIndex: selectedIndex,
        };
        vocabImageLightboxReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : vocabPictureFrame;
        if (vocabImageLightboxWord) vocabImageLightboxWord.textContent = clean(item.word || "Vocabulary image");
        if (vocabImageLightboxMeaning) vocabImageLightboxMeaning.textContent = clean(item.meaning || "Visual reference");
        renderVocabImageLightboxSlide();
        vocabImageLightbox.classList.add("is-open");
        vocabImageLightbox.setAttribute("aria-hidden", "false");
        document.documentElement.classList.add("ft-vocab-image-lightbox-open");
        window.requestAnimationFrame(() => vocabImageLightboxClose && vocabImageLightboxClose.focus({ preventScroll: true }));
        return true;
      };

      // 2026-08-04: restores the exact Space_V study surface and prior keyboard focus after image viewing.
      const closeVocabImageLightbox = () => {
        if (!vocabImageLightbox || !vocabImageLightbox.classList.contains("is-open")) return false;
        vocabImageLightbox.classList.remove("is-open");
        vocabImageLightbox.setAttribute("aria-hidden", "true");
        document.documentElement.classList.remove("ft-vocab-image-lightbox-open");
        const returnFocus = vocabImageLightboxReturnFocus;
        vocabImageLightboxReturnFocus = null;
        const state = vocabImageLightboxState;
        const current = currentVocabItem();
        const selected = state.images[state.index] || null;
        if (selected && current && vocabWordKey(current) === state.itemKey) {
          current.image = selected;
          current.images = state.images.slice();
          current.imageSelectedIndex = state.index;
          current.imageGalleryLoaded = true;
          vocabImageResultCache.set(state.itemKey, {
            image: selected,
            images: state.images.slice(),
            selectedIndex: state.index,
            expiresAt: Date.now() + 24 * 60 * 60 * 1000,
          });
          renderVocabPictureCard(current);
          if (state.index !== state.initialIndex && selected.id && state.word) {
            const operationId = window.crypto && typeof window.crypto.randomUUID === "function"
              ? `vocab-image-${window.crypto.randomUUID()}`
              : `vocab-image-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
            current.imageSelectionOperationId = operationId;
            void fetchServerJson("/vocab/image-primary", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                word: state.word,
                image_id: selected.id,
                operation_id: operationId,
                selected_epoch: Date.now() / 1000,
              }),
            }).then((result) => {
              const payload = result && result.payload && typeof result.payload === "object" ? result.payload : result;
              const active = currentVocabItem();
              if (!active || vocabWordKey(active) !== state.itemKey || active.imageSelectionOperationId !== operationId) return;
              const acceptedId = clean(payload && payload.image_id).toLowerCase();
              const acceptedIndex = acceptedId
                ? state.images.findIndex((image) => clean(image.id).toLowerCase() === acceptedId)
                : -1;
              if (acceptedIndex >= 0 && acceptedIndex !== state.index) {
                active.image = state.images[acceptedIndex];
                active.imageSelectedIndex = acceptedIndex;
                vocabImageResultCache.set(state.itemKey, {
                  image: active.image,
                  images: state.images.slice(),
                  selectedIndex: acceptedIndex,
                  expiresAt: Date.now() + 24 * 60 * 60 * 1000,
                });
                renderVocabPictureCard(active);
              }
            }).catch((error) => console.warn("FTG vocab image primary save failed", error));
          }
        }
        vocabImageLightboxState = { itemKey: "", word: "", images: [], index: 0, initialIndex: 0 };
        if (returnFocus && typeof returnFocus.focus === "function") {
          window.setTimeout(() => returnFocus.focus({ preventScroll: true }), 80);
        }
        return true;
      };

      const renderVocabPictureCard = (item) => {
        if (!vocabPicturePanel || !vocabPictureImg || !vocabPictureCaption) {
          return;
        }
        const image = item && item.image ? item.image : {};
        const url = resolveServerAssetUrl(image.url || "");
        const shouldShow = Boolean(vocabSideCardsVisible() && url);
        vocabPicturePanel.classList.toggle("is-hidden", !shouldShow);
        if (!shouldShow) {
          closeVocabImageLightbox();
          vocabPictureImg.removeAttribute("src");
          vocabPictureCaption.textContent = "";
          if (vocabSideCardsVisible()) {
            ensureVocabItemImageLazy(item);
          }
          return;
        }
        vocabPictureImg.alt = clean(item.meaning || item.word || "Vocabulary image");
        vocabPictureImg.onload = () => {
          if (vocabWordKey(currentVocabItem()) === vocabWordKey(item)) {
            scheduleNextVocabImagePrefetch(item);
          }
        };
        if (vocabPictureImg.getAttribute("src") !== url) {
          vocabPictureImg.src = url;
        }
        vocabPictureImg.onerror = () => {
          vocabPicturePanel.classList.add("is-hidden");
          positionVocabSideCards();
        };
        vocabPictureCaption.textContent = [image.source || "Image signal", image.credit].filter(Boolean).join(" | ");
        window.requestAnimationFrame(positionVocabSideCards);
      };

      const renderVocabSideCards = (item) => {
        renderVocabDetailCard(item);
        renderVocabPictureCard(item);
        window.setTimeout(positionVocabSideCards, 180);
      };

      const hideVocabSideCards = () => {
        closeVocabImageLightbox();
        if (vocabDetailPanel) {
          vocabDetailPanel.classList.add("is-hidden");
        }
        if (vocabPicturePanel) {
          vocabPicturePanel.classList.add("is-hidden");
        }
        hideVocabSideConnectors();
        resetVocabSideCardPositions();
      };

      const renderVocabUnlearnedList = () => {
        if (!vocabUnlearnedPanel || !vocabUnlearnedList || !vocabUnlearnedCount) {
          return;
        }
        const items = vocabStudyIndexes.map(vocabItemByIndex).filter(Boolean);
        const shouldShow = Boolean(items.length && vocabModeActive && vocabPhase === "probe");
        vocabUnlearnedPanel.classList.toggle("is-hidden", !shouldShow);
        if (vocabWeakConnector) {
          vocabWeakConnector.classList.toggle("is-hidden", !shouldShow);
        }
        if (!shouldShow) {
          resetVocabUnlearnedPanelPosition();
        }
        vocabUnlearnedCount.textContent = `${Math.min(items.length, VOCAB_BATCH_SIZE)} / ${VOCAB_BATCH_SIZE}`;
        vocabUnlearnedList.textContent = "";
        items.forEach((item, index) => {
          const row = document.createElement("div");
          row.className = "ft-vocab-unlearned-item";
          const number = document.createElement("span");
          number.textContent = String(index + 1).padStart(2, "0");
          const word = document.createElement("span");
          word.textContent = item.word;
          const meaning = document.createElement("small");
          meaning.textContent = item.meaning;
          row.append(number, word, meaning);
          vocabUnlearnedList.appendChild(row);
        });
        if (shouldShow) {
          window.requestAnimationFrame(positionVocabWeakConnector);
          window.setTimeout(positionVocabWeakConnector, 220);
        }
      };

      const addVocabUnlearnedIndex = (index, options = {}) => {
        const item = vocabItemByIndex(index);
        const key = vocabWordKey(item);
        if (!item || !key || vocabStudyKeys.has(key)) {
          return false;
        }
        vocabStudyKeys.add(key);
        vocabStudyIndexes.push(Number(index));
        renderVocabUnlearnedList();
        if (options.deferSave && typeof queueVocabProgressSave === "function") {
          queueVocabProgressSave(600);
        } else if (typeof saveVocabProgressCheckpointNow === "function") {
          saveVocabProgressCheckpointNow("unlearned");
        } else if (typeof saveVocabProgressNow === "function") {
          saveVocabProgressNow();
        }
        return true;
      };

      const renderVocabStrip = () => {
        if (!vocabStrip) {
          return;
        }
        const shouldShow = vocabModeActive && vocabPhase === "probe";
        vocabStrip.classList.toggle("is-hidden", !shouldShow);
        vocabStrip.textContent = "";
        if (!shouldShow) {
          return;
        }
        vocabBatch.forEach((item) => {
          const token = document.createElement("span");
          token.className = "ft-vocab-token";
          const learned = vocabLearnedKeys.has(vocabWordKey(item));
          const unlearned = vocabStudyKeys.has(vocabWordKey(item));
          token.classList.toggle("is-done", learned);
          token.textContent = learned || unlearned ? item.word : "*".repeat(Math.max(1, clean(item.word).length));
          vocabStrip.appendChild(token);
        });
      };

      const renderVocabMeta = (item, extraItems = [], options = {}) => {
        if (!vocabMeta) {
          return;
        }
        const vocabDrillRepetitionText = () => `Repetition ${Math.min(vocabDrillCorrectCount, 10)} / 10`;
        const hintKindForText = (text) => {
          if (/^hint\s*:/i.test(text)) {
            return "letters";
          }
          if (/^first\s+letter\s*:/i.test(text)) {
            return "first-letter";
          }
          return "";
        };
        const extras = (Array.isArray(extraItems) ? extraItems : [extraItems])
          .map(clean)
          .filter(Boolean)
          .filter((text) => !/^(answer|correct|round clear)\s*:/i.test(text));
        const hasLetterHint = extras.some((text) => hintKindForText(text) === "letters");
        if (vocabPhase === "shuffle" && item && item.word && !hasLetterHint) {
          extras.push(`Hint: ${clean(item.word).replace(/\s+/g, "").length} letters`);
        }
        const hasRoundMeta = extras.some((text) => /^round\s+\d+\s*\/\s*\d+/i.test(text));
        if (vocabPhase === "shuffle" && !hasRoundMeta) {
          extras.push(`Round ${Math.min(vocabShuffleRound || 1, 5)} / 5`);
        }
        let hasRepetitionMeta = extras.some((text) => /^repetition\s+\d+\s*\/\s*\d+/i.test(text));
        if (vocabPhase === "drill" && !hasRepetitionMeta) {
          extras.push(vocabDrillRepetitionText());
          hasRepetitionMeta = true;
        }
        const revealIpa = Boolean(options.revealIpa || vocabPhase === "drill");
        const revealHelpMeta = Boolean(revealIpa || options.revealHints || vocabCurrentHadError || vocabPhase === "drill");
        const revealAnswerWord = Boolean(
          options.revealWord
          || options.revealAnswerWord
          || (revealIpa && vocabPhase !== "drill" && vocabPhase !== "shuffle")
          || (vocabPhase === "drill" && vocabCurrentHadError)
        );
        const reserveRevealLayout = Boolean(revealIpa || vocabPhase === "shuffle" || vocabPhase === "drill");
        const reserveAnswerWord = Boolean(item && item.word && (revealAnswerWord || vocabPhase === "shuffle" || vocabPhase === "drill"));
        vocabMeta.classList.toggle("is-reveal", reserveRevealLayout);
        vocabMeta.classList.toggle("has-reserved-help", Boolean(item && (item.pron || item.type || reserveAnswerWord)));
        vocabMeta.classList.toggle("has-repetition", Boolean(hasRepetitionMeta));
        vocabMeta.textContent = "";
        [
          item && item.pron ? { text: item.pron, label: "IPA", kind: "ipa", hidden: !revealIpa } : null,
          reserveAnswerWord ? { text: item.word, kind: "answer-word", hidden: !revealAnswerWord } : null,
          item && item.type ? { text: item.type, kind: "type", hintKind: "type", hidden: !revealHelpMeta } : null,
          ...extras.map((text) => ({
            text: hintKindForText(text) === "letters" ? text.replace(/^hint\s*:\s*/i, "") : text,
            label: hintKindForText(text) === "letters" ? "Hint" : "",
            kind: /^ipa\b/i.test(text) ? "ipa" : (/^round\s+\d+\s*\/\s*\d+/i.test(text) ? "round" : (/^repetition\s+\d+\s*\/\s*\d+/i.test(text) ? "repetition" : (hintKindForText(text) ? "hint" : ""))),
            hintKind: hintKindForText(text),
            hidden: Boolean(hintKindForText(text) && !revealHelpMeta),
          })),
        ].filter((entry) => entry && entry.text).forEach((entry) => {
          const chip = document.createElement("span");
          chip.className = "ft-vocab-chip";
          if (entry.hintKind) {
            chip.dataset.vocabHintKind = entry.hintKind;
          }
          if (entry.kind === "ipa") {
            chip.classList.add("is-ipa");
          }
          if (entry.kind === "answer-word") {
            chip.classList.add("is-answer-word");
          }
          if (entry.kind === "type") {
            chip.classList.add("is-type");
          }
          if (entry.kind === "hint") {
            chip.classList.add("is-hint");
          }
          if (entry.kind === "round") {
            chip.classList.add("is-round");
            if (options.roundFlash) {
              chip.classList.add("is-round-flash");
            }
          }
          if (entry.kind === "repetition") {
            chip.classList.add("is-repetition");
            if (options.repetitionFlash) {
              chip.classList.add("is-repetition-flash");
            }
          }
          if (entry.hidden) {
            chip.classList.add("is-placeholder");
            chip.setAttribute("aria-hidden", "true");
          }
          if (entry.label) {
            const labelNode = document.createElement("span");
            labelNode.className = "ft-vocab-chip-label";
            labelNode.textContent = entry.label;
            chip.appendChild(labelNode);
          }
          const textNode = document.createElement("span");
          textNode.className = "ft-vocab-chip-text";
          textNode.textContent = entry.text;
          chip.appendChild(textNode);
          vocabMeta.appendChild(chip);
        });
        applyVocabActiveHint();
      };

      const vocabProgressText = () => {
        const total = vocabItems.length;
        if (vocabPhase === "drill") {
          return `Training ${Math.min(vocabDrillIndex + 1, vocabStudyIndexes.length)} / ${vocabStudyIndexes.length}`;
        }
        if (vocabPhase === "shuffle") {
          return `Shuffle round ${Math.min(vocabShuffleRound, 5)} / 5 | Correct ${vocabShuffleCorrectCount} / ${vocabShuffleOriginal.length}`;
        }
        return `Learned ${vocabLearnedKeys.size} / ${total} | Unlearned ${vocabStudyIndexes.length} / ${VOCAB_BATCH_SIZE}`;
      };

      const vocabProgressStats = () => {
        const total = Math.max(0, Array.isArray(vocabItems) ? vocabItems.length : 0);
        const learned = Math.max(0, Math.min(total, vocabLearnedKeys.size));
        let detail = `${Math.round(total ? (learned / total) * 100 : 0)}%`;
        if (vocabPhase === "drill") {
          detail = `Training ${Math.min(vocabDrillIndex + 1, Math.max(1, vocabStudyIndexes.length))}/${Math.max(1, vocabStudyIndexes.length)}`;
        } else if (vocabPhase === "shuffle") {
          detail = `Shuffle ${Math.min(vocabShuffleRound || 1, 5)}/5 | Correct ${vocabShuffleCorrectCount}/${Math.max(1, vocabShuffleOriginal.length)}`;
        }
        return {
          done: learned,
          total,
          label: "Space_V progress",
          value: `Words ${learned}/${total}`,
          detail,
        };
      };

      const updateVocabRuntimeProgress = () => {
        if (!vocabProgress) {
          return;
        }
        const stats = vocabProgressStats();
        if (!stats.total) {
          clearRuntimeProgress(vocabProgress, vocabProgressText());
          return;
        }
        renderRuntimeProgress(vocabProgress, {
          done: stats.done,
          total: stats.total,
          label: stats.label,
          value: stats.value,
          detail: stats.detail,
          className: "is-space-v",
        });
      };

      const clearVocabMeaningAudioRef = (audio = null) => {
        if (!audio || vocabMeaningAudioRef === audio) {
          vocabMeaningAudioRef = null;
          vocabMeaningAudioDone = null;
        }
      };

      const trackVocabMeaningAudioOptions = () => ({
        onAudio: (audio, done) => {
          vocabMeaningAudioRef = audio;
          vocabMeaningAudioDone = done;
        },
        onAudioDone: (audio) => clearVocabMeaningAudioRef(audio),
      });

      const stopVocabMeaningAudio = () => {
        vocabMeaningAudioToken += 1;
        const audio = vocabMeaningAudioRef;
        const done = vocabMeaningAudioDone;
        clearVocabMeaningAudioRef();
        if (audio) {
          try {
            audio.pause();
            audio.currentTime = 0;
            audio.removeAttribute("src");
            audio.load();
          } catch (error) {
          }
          if (activeAudio === audio) {
            activeAudio = null;
          }
        }
        if (typeof done === "function") {
          try {
            done(false);
          } catch (error) {
          }
        }
      };

      const playVocabMeaningAudio = async (item) => {
        if (!item) {
          return;
        }
        stopVocabMeaningAudio();
        const token = vocabMeaningAudioToken;
        const playOptions = {
          ...trackVocabMeaningAudioOptions(),
          shouldPlay: () => token === vocabMeaningAudioToken,
        };
        if (item.static_answer || item.staticAnswer) {
          const voiceKey = selectedVocabVoiceKey();
          const shortKey = /en-us/i.test(voiceKey) ? "us" : "uk";
          const questionAudio = item.question_audio || item.questionAudio || {};
          const clip = questionAudio[voiceKey] || questionAudio[voiceKey.toLowerCase()] || questionAudio[shortKey] || questionAudio["sot:en-GB"] || questionAudio.uk || questionAudio["sot:en-US"] || questionAudio.us;
          if (clip) {
            const played = await playAudioClipOnce(clip, { volume: 0.96, ...playOptions });
            if (played) {
              return;
            }
          }
          if (item.meaning && token === vocabMeaningAudioToken) {
            await playSoundOfText(item.meaning, /en-us/i.test(voiceKey) ? "en-US" : "en-GB", playOptions);
          }
          return;
        }
        const clip = item.audio && (item.audio["sot:vi-VN"] || item.audio["sot:vi-vn"] || item.audio.vi);
        if (clip) {
          const played = await playAudioClipOnce(clip, { volume: 0.96, ...playOptions });
          if (played) {
            return;
          }
        }
        if (item.meaning && token === vocabMeaningAudioToken) {
          await playSoundOfText(item.meaning, "vi-VN", playOptions);
        }
      };

      const showVocabItem = (item, absoluteIndex = -1, options = {}) => {
        stopVocabMeaningAudio();
        vocabAnswerBusy = false;
        setVocabInputLocked(false);
        if (vocabCard) {
          vocabCard.classList.remove("is-hidden");
          resetVocabCardRevealStyles();
        }
        vocabCurrentIndex = Number(absoluteIndex);
        applyVocabPhaseVisualState();
        const nextPulseKey = `${vocabPhase}:${Number(absoluteIndex)}:${vocabWordKey(item)}`;
        if (options.pulse !== false && nextPulseKey !== lastVocabPulseKey) {
          pulseVocabCard(options.pulseMode || "word");
        }
        lastVocabPulseKey = nextPulseKey;
        if (!options.keepError) {
          vocabCurrentHadError = false;
        }
        if (vocabTitle) {
          vocabTitle.textContent = item.meaning || "Dictionary meaning is syncing...";
        }
        updateVocabRuntimeProgress();
        const warmAudioIndex = Number(absoluteIndex);
        const warmAudioKey = vocabWordKey(item);
        window.setTimeout(() => {
          if (
            vocabCurrentIndex !== warmAudioIndex
            || vocabWordKey(vocabItems[vocabCurrentIndex] || null) !== warmAudioKey
          ) {
            return;
          }
          preloadVocabItemAudio(item, { includeAlternates: false, includeMeaning: true });
          preloadVocabularyAudioCache(vocabItems, {
            focusIndex: absoluteIndex,
            lookAhead: VOCAB_AUDIO_LOOKAHEAD,
            includeAlternates: false,
            includeMeaning: true,
            includeAll: false,
            maxItems: VOCAB_AUDIO_LOOKAHEAD,
          });
        }, options.playMeaning === false ? 80 : 520);
        renderVocabMeta(item, options.extraMeta || [], options);
        renderVocabStrip();
        renderVocabUnlearnedList();
        renderVocabLearnedPanel(item);
        renderVocabSideCards(item);
        if (vocabAnswer) {
          if (options.clearInput !== false) {
            const lockForPopup = options.lockInput === true || (options.lockInput !== false && isVocabModePopupVisible());
            resetVocabInputForNewWord({ lockMs: lockForPopup ? Math.max(120, Number(options.lockMs || 190) || 190) : 0, focus: true });
          }
          window.setTimeout(() => {
            if (Date.now() >= vocabInputResetUntil) {
              vocabAnswer.focus({ preventScroll: true });
              scheduleVocabCardPin(1400, { force: true });
            }
          }, 80);
        }
        setVocabFeedback(options.message || "Answer with the English word.");
        scheduleVocabCardPin(1100, { force: true });
        scheduleVocabCardVisibilityGuard();
        scheduleMobileInfiniteMotionSync(80);
        if (vocabPhase === "probe" && options.timer !== false) {
          scheduleVocabProbeHintTimers(item, absoluteIndex);
        } else {
          clearVocabHintTimers();
        }
        scheduleVocabTypeHintTimer(item, absoluteIndex);
        if (options.playMeaning !== false) {
          const meaningWordKey = vocabWordKey(item);
          const meaningAudioToken = vocabMeaningAudioToken;
          window.setTimeout(() => {
            const playCurrentMeaning = () => {
              if (
                meaningAudioToken === vocabMeaningAudioToken
                && vocabCurrentIndex === Number(absoluteIndex)
                && vocabWordKey(vocabItems[vocabCurrentIndex] || null) === meaningWordKey
              ) {
                void playVocabMeaningAudio(item);
              }
            };
            if (typeof window.__ftRunAfterLessonEntryGateOpen === "function") window.__ftRunAfterLessonEntryGateOpen(playCurrentMeaning);
            else playCurrentMeaning();
          }, 180);
        }
        queueVocabProgressSave(180);
      };

      const completeVocabularyMission = async () => {
        if (vocabCompletionFinalizing || lessonCompletionSent) {
          return;
        }
        if (!vocabItems.length || !vocabAllProbeWordsLearned()) {
          return;
        }
        vocabCompletionFinalizing = true;
        hideVocabModePopup();
        clearVocabHintTimers();
        stopVocabMeaningAudio();
        setVocabInputLocked(true);
        if (vocabAnswer) {
          vocabAnswer.value = "";
          vocabAnswer.disabled = true;
          vocabAnswer.readOnly = true;
          vocabAnswer.setAttribute("aria-busy", "true");
          vocabAnswer.blur();
        }
        dismissSoftKeyboard();
        void showVocabModePopup(
          "Updating rewards",
          "Saving your final answer and preparing the leaderboard.",
          "probe",
          0
        );
        if (vocabProgressSaveTimer) {
          window.clearTimeout(vocabProgressSaveTimer);
          vocabProgressSaveTimer = 0;
        }
        if (vocabServerProgressSaveTimer) {
          window.clearTimeout(vocabServerProgressSaveTimer);
          vocabServerProgressSaveTimer = 0;
        }
        pendingVocabServerProgressRecord = null;
        vocabItems.forEach((item) => {
          const key = vocabWordKey(item);
          if (key) {
            vocabLearnedKeys.add(key);
          }
        });
        vocabStudyIndexes = [];
        vocabStudyKeys = new Set();
        vocabBatch = [];
        vocabQueue = [];
        vocabShuffleOriginal = [];
        vocabShuffleQueue = [];
        vocabCurrentIndex = vocabItems.length;
        vocabPhase = "complete";
        renderVocabUnlearnedList();
        hideVocabSideCards();
        setVocabFeedback("Vocabulary mission complete.", "ok");
        const completeState = {
          ...vocabProgressSnapshot(),
          currentIndex: vocabItems.length,
          learned: Array.from(vocabLearnedKeys),
          learnedWords: currentVocabLearnedWordRecords(),
          activeRun: false,
          active_run: false,
          reviewing: false,
          reviewRun: false,
          complete: true,
          registryReady: true,
          vocabComplete: true,
          lessonComplete: true,
          lessonCompletionSent: true,
          asyncVocabularySync: true,
        };
        completeState.syncOperationId = createVocabProgressOperationId();
        const completeRecord = {
          version: 2,
          action: "complete",
          identity: currentVocabProgressCache.identity,
          savedAt: completeState.savedAt,
          title: completeState.title,
          path: currentVocabServerPath(),
          nodeIndex: vocabItems.length,
          nodeCount: vocabItems.length,
          learnedCount: Array.isArray(completeState.learned) ? completeState.learned.length : vocabItems.length,
          completionRunId: clean(vocabActiveRunId),
          completion_run_id: clean(vocabActiveRunId),
          syncOperationId: completeState.syncOperationId,
          pendingServerSync: true,
          state: completeState,
          activeRun: false,
          active_run: false,
          complete: true,
          registryReady: true,
          vocabComplete: true,
          lessonComplete: true,
          lessonCompletionSent: true,
          asyncVocabularySync: true,
        };
        persistVocabCompletionLocally(completeRecord);
        writeVocabLearnedSyncRecord(completeRecord, { force: true });
        let progressPayload = null;
        try {
          progressPayload = await sendVocabServerProgress(completeRecord, "complete");
        } catch (error) {
        }
        const registryQueued = typeof acknowledgeVocabRegistrySyncQueued === "function"
          && acknowledgeVocabRegistrySyncQueued(completeRecord, progressPayload);
        if (!registryQueued) {
          scheduleVocabRegistrySync(80);
        }
        updateVocabProgressButtons();
        void handleVocabularyMissionCompletion().finally(() => {
          vocabCompletionFinalizing = false;
        });
      };

      const startNextVocabProbe = () => {
        if (vocabModeTransitioning) {
          return;
        }
        clearVocabHintTimers();
        vocabPhase = "probe";
        applyVocabPhaseVisualState();
        renderVocabUnlearnedList();
        queueVocabProgressSave(180);
        const remaining = vocabRemainingProbeIndexes();
        if (vocabStudyIndexes.length >= VOCAB_BATCH_SIZE || (!remaining.length && vocabStudyIndexes.length)) {
          startVocabDrill(true);
          return;
        }
        if (!remaining.length) {
          completeVocabularyMission();
          return;
        }
        if (!vocabQueue.some(vocabCanProbeIndex)) {
          vocabQueue = remaining;
        }
        while (vocabQueue.length) {
          const index = vocabQueue.shift();
          if (vocabCanProbeIndex(index)) {
            vocabBatch = shuffleIndexes(vocabItems.length)
              .filter((idx) => vocabCanProbeIndex(idx) || vocabStudyKeys.has(vocabWordKey(vocabItemByIndex(idx))))
              .slice(0, VOCAB_BATCH_SIZE)
              .map(vocabItemByIndex)
              .filter(Boolean);
            vocabAttemptCounts.set(vocabWordKey(vocabItemByIndex(index)), 0);
            showVocabItem(vocabItemByIndex(index), index);
            saveVocabProgressNow();
            return;
          }
        }
        completeVocabularyMission();
      };

      const startVocabDrill = (withIntro = true) => {
        if (!vocabStudyIndexes.length) {
          startNextVocabProbe();
          return;
        }
        if (withIntro) {
          if (vocabModeTransitioning) {
            return;
          }
          vocabModeTransitioning = true;
          clearVocabHintTimers();
          hideVocabSideCards();
          renderVocabLearnedPanel();
          showVocabModePopup(
            "Training core online",
            "10 repetition mode is loading. Dictionary and visual cards unlock here.",
            "drill",
            2000,
          ).then(() => {
            vocabModeTransitioning = false;
            startVocabDrill(false);
          });
          return;
        }
        clearVocabHintTimers();
        vocabPhase = "drill";
        applyVocabPhaseVisualState();
        renderVocabUnlearnedList();
        renderVocabLearnedPanel();
        vocabDrillIndex = 0;
        vocabDrillCorrectCount = 0;
        vocabDrillFailCount = 0;
        queueVocabProgressSave(180);
        showCurrentVocabDrillItem();
      };

      const showCurrentVocabDrillItem = (options = {}) => {
        if (vocabDrillIndex >= vocabStudyIndexes.length) {
          startVocabShuffle(true);
          return;
        }
        const index = vocabStudyIndexes[vocabDrillIndex];
        const item = vocabItemByIndex(index);
        showVocabItem(item, index, {
          message: "Training mode. Type this word 10 times.",
          clearInput: options.clearInput,
          lockInput: options.lockInput,
        });
      };

      const transitionToNextVocabDrillItem = () => {
        vocabDrillIndex += 1;
        vocabDrillCorrectCount = 0;
        vocabDrillFailCount = 0;
        queueVocabProgressSave(100);

        if (vocabDrillIndex >= vocabStudyIndexes.length) {
          showCurrentVocabDrillItem({ clearInput: true, lockInput: true });
          return;
        }

        const nextIndex = vocabStudyIndexes[vocabDrillIndex];
        const nextItem = vocabItemByIndex(nextIndex);
        vocabModeTransitioning = true;
        clearVocabHintTimers();
        hideVocabSideCards();
        showVocabModePopup(
          "Next word loading",
          `Preparing ${clean(nextItem && (nextItem.meaning || nextItem.word)) || "the next training word"}. Input will unlock when the new card is ready.`,
          "drill",
          1500,
        ).then(() => {
          vocabModeTransitioning = false;
          showCurrentVocabDrillItem({ clearInput: true, lockInput: false });
        });
      };

      const startVocabShuffle = (withIntro = true) => {
        if (withIntro) {
          if (vocabModeTransitioning) {
            return;
          }
          vocabModeTransitioning = true;
          clearVocabHintTimers();
          hideVocabSideCards();
          renderVocabLearnedPanel();
          showVocabModePopup(
            "Shuffle matrix online",
            "Five randomized rounds begin now. Gear position changes each round.",
            "shuffle",
            2000,
          ).then(() => {
            vocabModeTransitioning = false;
            startVocabShuffle(false);
          });
          return;
        }
        clearVocabHintTimers();
        vocabPhase = "shuffle";
        applyVocabPhaseVisualState();
        renderVocabUnlearnedList();
        hideVocabSideCards();
        renderVocabLearnedPanel();
        vocabShuffleOriginal = [...vocabStudyIndexes];
        vocabShuffleRound = 1;
        vocabShuffleRoundPulsePending = true;
        vocabShuffleCorrectCount = 0;
        vocabShuffleFailCount = 0;
        queueVocabProgressSave(180);
        scheduleVocabCardPin(1800, { force: true });
        scheduleMobileInfiniteMotionSync(80);
        startVocabShuffleRound();
      };

      const startVocabShuffleRound = (options = {}) => {
        if (vocabShuffleRound > 5) {
          finishVocabShuffle();
          return;
        }
        applyVocabPhaseVisualState();
        vocabShuffleRoundPulsePending = true;
        vocabShuffleQueue = shuffleIndexes(vocabShuffleOriginal.length).map((localIndex) => vocabShuffleOriginal[localIndex]);
        vocabShuffleCorrectCount = 0;
        vocabShuffleFailCount = 0;
        queueVocabProgressSave(180);
        scheduleVocabCardPin(1600, { force: true });
        showNextVocabShuffleQuestion(options);
      };

      const showNextVocabShuffleQuestion = (options = {}) => {
        if (!vocabShuffleQueue.length) {
          vocabShuffleRound += 1;
          if (vocabShuffleRound > 5) {
            window.setTimeout(() => startVocabShuffleRound({ ...options, clearInput: true }), 500);
            return;
          }
          if (vocabModeTransitioning) {
            return;
          }
          vocabModeTransitioning = true;
          clearVocabHintTimers();
          hideVocabSideCards();
          showVocabModePopup(
            `Shuffle round ${Math.min(vocabShuffleRound, 5)} online`,
            `Round ${Math.min(vocabShuffleRound, 5)} of 5 is loading. Input unlocks on the next card.`,
            "shuffle",
            1200,
          ).then(() => {
            vocabModeTransitioning = false;
            startVocabShuffleRound({ ...options, clearInput: true });
          });
          return;
        }
        const index = options.pendingShuffleIndex == null
          ? vocabShuffleQueue.shift()
          : Math.max(0, Number(options.pendingShuffleIndex) || 0);
        const item = vocabItemByIndex(index);
        const roundPulse = vocabShuffleRoundPulsePending;
        vocabShuffleFailCount = 0;
        if (!options.skipWordPopup) {
          vocabModeTransitioning = true;
          clearVocabHintTimers();
          hideVocabSideCards();
          showVocabModePopup(
            "Shuffle word signal",
            `Round ${Math.min(vocabShuffleRound, 5)} of 5. Next word is ready.`,
            "shuffle",
            760,
          ).then(() => {
            vocabModeTransitioning = false;
            showNextVocabShuffleQuestion({ ...options, pendingShuffleIndex: index, skipWordPopup: true });
          });
          return;
        }
        showVocabItem(item, index, {
          message: "Shuffle check. Answer correctly to clear this round.",
          extraMeta: [`Round ${Math.min(vocabShuffleRound, 5)} / 5`],
          roundFlash: roundPulse,
          pulse: !roundPulse,
          clearInput: options.clearInput,
        });
        scheduleVocabCardPin(1800, { force: true });
        scheduleMobileInfiniteMotionSync(80);
        if (roundPulse) {
          vocabShuffleRoundPulsePending = false;
          window.setTimeout(() => {
            pulseVocabCard("round");
            scheduleVocabCardPin(1800, { force: true });
            scheduleMobileInfiniteMotionSync(80);
          }, 30);
        }
      };

      const finishVocabShuffle = () => {
        clearVocabHintTimers();
        const recycled = [...vocabStudyIndexes];
        recycled.forEach((index) => {
          const key = vocabWordKey(vocabItemByIndex(index));
          if (key && !vocabKnownAtStartKeys.has(key)) {
            vocabBlueCrystalReadyKeys.add(key);
          }
        });
        vocabStudyIndexes = [];
        vocabStudyKeys = new Set();
        vocabAttemptCounts = new Map();
        vocabBatch = [];
        renderVocabUnlearnedList();
        hideVocabSideCards();
        const recycledSet = new Set(recycled.map((idx) => Number(idx)));
        const remainingProbe = shuffleIndexes(vocabItems.length).filter((idx) => vocabCanProbeIndex(idx));
        vocabQueue = shuffleIndexes(remainingProbe.length).map((order) => remainingProbe[order]);
        if (vocabQueue.length > 1 && recycledSet.has(Number(vocabQueue[0]))) {
          const firstFreshPosition = vocabQueue.findIndex((idx) => !recycledSet.has(Number(idx)));
          if (firstFreshPosition > 0) {
            [vocabQueue[0], vocabQueue[firstFreshPosition]] = [vocabQueue[firstFreshPosition], vocabQueue[0]];
          }
        }
        setVocabFeedback("Training cycle complete. These words return to the check queue.", "ok");
        queueVocabProgressSave(180);
        showVocabModePopup(
          "Review loop restored",
          "Shuffle cycle complete. Returning trained words to the check queue.",
          "probe",
          2000,
        ).then(() => {
          startNextVocabProbe();
        });
      };

      const currentVocabItem = () => vocabItems[vocabCurrentIndex] || null;

      const vocabCrystalConfig = (tone = "yellow") => {
        const key = clean(tone).toLowerCase();
        if (key === "blue") {
          return {
            id: "vocab_crystal_blue",
            name: "Silver Axe",
            use: "Forged when a word returns after 10 drills and 5 shuffle rounds and is answered correctly.",
          };
        }
        if (key === "green") {
          return {
            id: "vocab_crystal_green",
            name: "Silver Axe",
            use: "Forged by correctly recalling vocabulary already stored in memory.",
          };
        }
        return {
          id: "vocab_crystal_yellow",
          name: "Golden Axe",
          use: "Forged when a new vocabulary word is learned cleanly.",
        };
      };

      const vocabRewardEventKey = (tone = "yellow", item = null) => {
        const word = vocabWordKey(item);
        const source = currentLessonSource || {};
        const raw = [
          clean(source.path || source.name || source.title || "space-v"),
          word,
          clean(tone || "yellow"),
        ].join("|");
        return `space-v:${hashSpaceWText(raw)}`;
      };

      const awardVocabCrystalOnce = (tone = "yellow", item = null) => {
        const config = vocabCrystalConfig(tone);
        return awardInventoryItemOnce(vocabRewardEventKey(tone, item), config, vocabCard || cardNode, {
          tone,
          feedback: (awardedItem) => setVocabFeedback(`Axe obtained: ${awardedItem.name}.`, "ok"),
        });
      };

      const vocabVoiceAccent = (voiceKey = vocabVoiceKey) => /en-gb/i.test(voiceKey) ? "uk" : "us";

      const normalizeVocabVoiceKey = (voiceKey = "") => /en-us/i.test(clean(voiceKey)) ? "sot:en-US" : "sot:en-GB";

      const vocabVoiceUserStorageKey = (username = currentAuthUsername || "") => {
        const user = clean(username).toLowerCase();
        return user ? `${SPACE_V_VOICE_KEY}:${encodeURIComponent(user)}` : SPACE_V_VOICE_KEY;
      };

      const vocabVoiceUserMetaKey = (username = currentAuthUsername || "") => `${vocabVoiceUserStorageKey(username)}:meta`;

      let vocabVoicePreferenceEpoch = 0;
      let vocabVoiceSelectionEpoch = 0;
      let vocabVoiceServerRevision = 0;

      const readStoredVocabVoice = () => {
        try {
          const user = clean(currentAuthUsername || "");
          const raw = user
            ? localStorage.getItem(vocabVoiceUserStorageKey(user))
            : localStorage.getItem(SPACE_V_VOICE_KEY);
          const meta = user ? JSON.parse(localStorage.getItem(vocabVoiceUserMetaKey(user)) || "{}") : {};
          vocabVoicePreferenceEpoch = Math.max(0, Number(meta && meta.updated_epoch || 0) || 0);
          return normalizeVocabVoiceKey(raw || "sot:en-GB");
        } catch (error) {
          return "sot:en-GB";
        }
      };

      const writeStoredVocabVoice = (voiceKey = "", updatedEpoch = 0) => {
        try {
          const normalized = normalizeVocabVoiceKey(voiceKey);
          const user = clean(currentAuthUsername || "");
          const key = vocabVoiceUserStorageKey(user);
          if (!user) {
            localStorage.setItem(SPACE_V_VOICE_KEY, normalized);
            return { voice: normalized, updated_epoch: 0 };
          }
          // Server-provided epochs are authoritative; never replace them with
          // a fast browser clock that could resurrect a stale tab's accent.
          const suppliedEpoch = Number(updatedEpoch) || 0;
          const epoch = suppliedEpoch > 0
            ? suppliedEpoch
            : Math.max(vocabVoicePreferenceEpoch || 0, Date.now() / 1000);
          vocabVoicePreferenceEpoch = epoch;
          localStorage.setItem(vocabVoiceUserMetaKey(user), JSON.stringify({ updated_epoch: epoch, updated_at: new Date(epoch * 1000).toISOString() }));
          localStorage.setItem(key, normalized);
          return { voice: normalized, updated_epoch: epoch, updated_at: new Date(epoch * 1000).toISOString() };
        } catch (error) {
          return { voice: normalizeVocabVoiceKey(voiceKey), updated_epoch: Number(updatedEpoch) || 0 };
        }
      };

      const syncVocabVoicePreferenceToServer = async (preference = {}) => {
        if (!authToken || !clean(currentAuthUsername || "") || !preference.voice) {
          return false;
        }
        try {
          const requestSelectionEpoch = vocabVoiceSelectionEpoch;
          const result = await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              _expected_server_revision: vocabVoiceServerRevision,
              vocab_audio: {
                voice: normalizeVocabVoiceKey(preference.voice),
                updated_at: clean(preference.updated_at) || new Date().toISOString(),
                updated_epoch: Number(preference.updated_epoch || 0) || 0,
              },
            }),
          });
          const returned = result && result.preferences && typeof result.preferences === "object" ? result.preferences : {};
          vocabVoiceServerRevision = Math.max(vocabVoiceServerRevision, Number(returned._serverRevision || (result && result.server_revision) || 0) || 0);
          if (returned._preferenceConflict && requestSelectionEpoch === vocabVoiceSelectionEpoch) {
            const serverPreference = returned.vocab_audio || returned.vocabAudio;
            if (serverPreference && serverPreference.voice) {
              vocabVoiceKey = normalizeVocabVoiceKey(serverPreference.voice);
              vocabVoicePreferenceEpoch = Math.max(0, Number(serverPreference.updated_epoch || 0) || 0);
              writeStoredVocabVoice(vocabVoiceKey, vocabVoicePreferenceEpoch);
              currentAccent = vocabVoiceAccent(vocabVoiceKey);
              syncVocabVoiceSwitch();
            }
          }
          return Boolean(result && result.ok !== false);
        } catch (error) {
          return false;
        }
      };

      const applyVocabAudioPreferencePayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const preference = source.vocab_audio || source.vocabAudio || source.space_v_voice || source.spaceVVoice;
        const localVoice = readStoredVocabVoice();
        const localEpoch = vocabVoicePreferenceEpoch;
        vocabVoiceServerRevision = Math.max(0, Number(source._serverRevision || source.server_revision || 0) || 0);
        if (preference && typeof preference === "object" && preference.voice) {
          const serverEpoch = Math.max(0, Number(preference.updated_epoch || 0) || 0);
          // A server preference is authoritative on login/reload. A local
          // clock cannot prove that an offline value is newer than it.
          vocabVoiceKey = normalizeVocabVoiceKey(preference.voice);
          vocabVoicePreferenceEpoch = serverEpoch;
          writeStoredVocabVoice(vocabVoiceKey, serverEpoch);
        } else {
          vocabVoiceKey = localVoice;
          if (localEpoch > 0) {
            void syncVocabVoicePreferenceToServer(writeStoredVocabVoice(localVoice, localEpoch));
          }
        }
        currentAccent = vocabVoiceAccent(vocabVoiceKey);
        vocabVoiceSelectionEpoch += 1;
        syncVocabVoiceSwitch();
        return vocabVoiceKey;
      };

      const syncVocabVoiceSwitch = () => {
        const activeKey = clean(vocabVoiceKey || "sot:en-GB");
        if (vocabVoiceSwitch) {
          vocabVoiceSwitch.classList.toggle("is-us", /en-us/i.test(activeKey));
        }
        vocabVoiceOptions.forEach((button) => {
          const active = clean(button.dataset.voice) === activeKey;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
      };

      const mergeRefreshedVocabAudio = (item, result) => {
        if (!item || !result || !result.clip) {
          return false;
        }
        const voice = normalizeVocabVoiceKey(result.voice || result.clip.voice || "");
        const shortKey = /en-us/i.test(voice) ? "us" : "uk";
        item.audio = item.audio && typeof item.audio === "object" ? item.audio : {};
        item.audio[voice] = result.clip;
        item.audio[voice.toLowerCase()] = result.clip;
        item.audio[shortKey] = result.clip;
        if (result.audio && typeof result.audio === "object") {
          Object.entries(result.audio).forEach(([key, clip]) => {
            if (key && clip && typeof clip === "object") {
              item.audio[key] = clip;
            }
          });
        }
        if (typeof invalidateCachedAudioClip === "function") {
          invalidateCachedAudioClip(result.clip);
        }
        return true;
      };

      const refreshCurrentVocabAccentAudio = async (voiceKey = selectedVocabVoiceKey(), item = currentVocabItem()) => {
        const targetWord = clean(item && (item.word || item.w || item.en || item.text || ""));
        const targetVoice = normalizeVocabVoiceKey(voiceKey);
        const selectionEpoch = vocabVoiceSelectionEpoch;
        if (!targetWord || !/^sot:en-(gb|us)$/i.test(targetVoice)) {
          return false;
        }
        try {
          setVocabFeedback(
            /en-us/i.test(targetVoice) ? "Repairing American audio..." : "Repairing British audio...",
            "ok",
          );
          const headers = { "Content-Type": "application/json", "Accept": "application/json" };
          if (!authToken && typeof getStoredAuthToken === "function") {
            authToken = getStoredAuthToken();
          }
          if (authToken) {
            headers.Authorization = `Bearer ${authToken}`;
          }
          const finalHeaders = typeof antiRobotHeaders === "function"
            ? await antiRobotHeaders("", headers)
            : headers;
          const response = await fetch("/space-v/refresh-audio", {
            method: "POST",
            headers: finalHeaders,
            credentials: "same-origin",
            cache: "no-store",
            body: JSON.stringify({ word: targetWord, voice: targetVoice }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok || payload.ok === false) {
            if (response.status === 429) {
              const limit = Math.max(1, Math.round(Number(payload.limit) || 20));
              setVocabFeedback(`Audio repair limit reached: ${limit}/day. Admin is unlimited.`, "error");
              return false;
            }
            throw new Error(clean(payload.error) || `Audio repair failed (${response.status}).`);
          }
          if (mergeRefreshedVocabAudio(item, payload)) {
            const stillSelected = selectionEpoch === vocabVoiceSelectionEpoch && targetVoice === selectedVocabVoiceKey();
            if (stillSelected) {
              vocabVoiceKey = targetVoice;
              currentAccent = vocabVoiceAccent(targetVoice);
              const preference = writeStoredVocabVoice(targetVoice, Math.max(vocabVoicePreferenceEpoch + 0.001, Date.now() / 1000));
              void syncVocabVoicePreferenceToServer(preference);
              syncVocabVoiceSwitch();
            }
            preloadVocabItemAudio(item, {
              selectedValue: targetVoice,
              includeAlternates: false,
              includeMeaning: false,
              forceReload: true,
            });
            setVocabFeedback(
              /en-us/i.test(targetVoice) ? "American audio repaired and selected." : "British audio repaired and selected.",
              "ok",
            );
            return true;
          }
        } catch (error) {
          setVocabFeedback(error && error.message ? error.message : "Audio repair failed.", "error");
        }
        return false;
      };

      const setVocabVoice = (voiceKey = "sot:en-GB", options = {}) => {
        const nextKey = normalizeVocabVoiceKey(voiceKey);
        vocabVoiceKey = nextKey;
        vocabVoiceSelectionEpoch += 1;
        currentAccent = vocabVoiceAccent(nextKey);
        if (options.persist !== false) {
          const preference = writeStoredVocabVoice(nextKey, Math.max(vocabVoicePreferenceEpoch + 0.001, Date.now() / 1000));
          void syncVocabVoicePreferenceToServer(preference);
        }
        syncVocabVoiceSwitch();
        if (vocabModeActive && vocabItems.length) {
          preloadVocabularyAudioCache(vocabItems, {
            focusIndex: vocabCurrentIndex,
            lookAhead: VOCAB_AUDIO_LOOKAHEAD,
            selectedValue: nextKey,
            includeAlternates: false,
            includeMeaning: true,
            includeAll: false,
            maxItems: VOCAB_AUDIO_LOOKAHEAD,
          });
          warmVocabularyAudioCacheForLesson({ kind: "future_vocabulary_payload", words: vocabItems, effects: lessonEffects }, {
            startIndex: vocabCurrentIndex,
            selectedValue: nextKey,
            includeAlternates: false,
            includeMeaning: true,
            startDelayMs: 500,
            delayMs: 45,
            status: false,
          });
        }
        if (options.silent !== true) {
          setVocabFeedback(
            currentAccent === "uk" ? "Vocabulary voice set to British English." : "Vocabulary voice set to American English.",
            "ok",
          );
        }
        if (options.play && currentVocabItem()) {
          void playVocabAudio(nextKey);
        }
        if (options.repairAudio) {
          void refreshCurrentVocabAccentAudio(nextKey, currentVocabItem());
        }
      };

      const selectedVocabVoiceKey = () => clean(vocabVoiceKey) || "sot:en-GB";

      const vocabAudioPriorityIndexes = (items = vocabItems, options = {}) => {
        const total = Array.isArray(items) ? items.length : 0;
        const indexes = [];
        const seen = new Set();
        const addIndex = (value) => {
          const index = Math.floor(Number(value));
          if (!Number.isFinite(index) || index < 0 || index >= total || seen.has(index)) {
            return;
          }
          seen.add(index);
          indexes.push(index);
        };
        if (Array.isArray(options.indexes)) {
          options.indexes.forEach(addIndex);
        }
        addIndex(options.focusIndex);
        addIndex(vocabCurrentIndex);
        const lookAhead = Math.max(1, Math.min(total || 1, Math.floor(Number(options.lookAhead) || VOCAB_AUDIO_LOOKAHEAD)));
        if (vocabPhase === "drill") {
          const start = Math.max(0, Math.floor(Number(vocabDrillIndex) || 0));
          vocabStudyIndexes.slice(start, start + lookAhead).forEach(addIndex);
        } else if (vocabPhase === "shuffle") {
          vocabShuffleQueue.slice(0, lookAhead).forEach(addIndex);
        } else {
          vocabQueue.slice(0, lookAhead).forEach(addIndex);
        }
        if (options.includeAll !== false) {
          for (let index = 0; index < total; index += 1) {
            addIndex(index);
          }
        }
        return indexes;
      };

      const collectVocabAudioClips = (items = vocabItems, options = {}) => {
        const clips = [];
        const seen = new Set();
        const addClip = (clip) => {
          const key = audioClipCacheKey(clip);
          if (!key || seen.has(key)) {
            return;
          }
          seen.add(key);
          clips.push(clip);
        };
        const sourceItems = Array.isArray(items) ? items : [];
        const selectedValue = clean(options.selectedValue || selectedVocabVoiceKey());
        const orderedIndexes = options.preserveOrder
          ? sourceItems.map((_item, index) => index)
          : vocabAudioPriorityIndexes(sourceItems, options);
        const maxItems = Math.max(0, Math.floor(Number(options.maxItems || options.itemLimit || 0) || 0));
        const activeIndexes = maxItems ? orderedIndexes.slice(0, maxItems) : orderedIndexes;
        const orderedItems = activeIndexes.map((index) => sourceItems[index]).filter(Boolean);
        orderedItems.filter(Boolean).forEach((item) => {
          vocabularyAudioClipsForItem(item, selectedValue, {
            includeAlternates: options.includeAlternates !== false,
            includeMeaning: options.includeMeaning !== false,
          }).forEach(addClip);
        });
        return clips;
      };

      const preloadVocabularyAudioCache = (items = vocabItems, options = {}) => {
        const clips = collectVocabAudioClips(items, options);
        const token = ++vocabAudioCacheToken;
        if (!clips.length) {
          return Promise.resolve({ total: 0, ready: 0, failed: 0, canceled: false, keys: [] });
        }
        let cursor = 0;
        let ready = 0;
        let failed = 0;
        const workerCount = Math.min(VOCAB_AUDIO_PRELOAD_WORKERS, clips.length);
        const runWorker = async () => {
          while (token === vocabAudioCacheToken && cursor < clips.length) {
            const clip = clips[cursor];
            cursor += 1;
            if (await preloadAudioClip(clip, null, { forceReload: Boolean(options.forceReload) })) {
              ready += 1;
            } else {
              failed += 1;
            }
          }
        };
        return Promise.all(Array.from({ length: workerCount }, () => runWorker())).then(() => ({
          total: clips.length,
          ready,
          failed,
          canceled: token !== vocabAudioCacheToken,
          keys: clips.map((clip) => audioClipCacheKey(clip)).filter(Boolean),
        }));
      };

      const preloadVocabItemAudio = (item, options = {}) => {
        if (!item || !item.audio) {
          return;
        }
        collectVocabAudioClips([item], {
          preserveOrder: true,
          includeAlternates: options.includeAlternates !== false,
          includeMeaning: options.includeMeaning !== false,
          selectedValue: options.selectedValue || selectedVocabVoiceKey(),
        }).forEach((clip) => {
          void preloadAudioClip(clip, null, { forceReload: Boolean(options.forceReload) });
        });
      };

      // Added 2026-07-31: after a Group audio-cache clear, preserve Continue
      // progress and rebuild the active Space_V cache from the current word.
      window.__futureReloadCurrentSpaceVAudioCache = async () => {
        if (!vocabModeActive || !Array.isArray(vocabItems) || !vocabItems.length) {
          return { ok: true, active: false, reason: "no-active-space-v" };
        }
        stopVocabMeaningAudio();
        stopActiveAudio();
        const startIndex = Math.max(0, Math.min(vocabItems.length - 1, Number(vocabCurrentIndex) || 0));
        const priority = await preloadVocabularyAudioCache(vocabItems, {
          focusIndex: startIndex,
          lookAhead: VOCAB_AUDIO_LOOKAHEAD,
          selectedValue: selectedVocabVoiceKey(),
          includeAlternates: false,
          includeMeaning: true,
          includeAll: false,
          maxItems: VOCAB_AUDIO_LOOKAHEAD,
          forceReload: true,
        });
        warmVocabularyAudioCacheForLesson({ kind: "future_vocabulary_payload", words: vocabItems, effects: lessonEffects }, {
          startIndex,
          selectedValue: selectedVocabVoiceKey(),
          includeAlternates: false,
          includeMeaning: true,
          forceReload: true,
          excludeAudioKeys: priority.keys || [],
          startDelayMs: 120,
          delayMs: 45,
          status: false,
        });
        return { ok: priority.failed === 0, active: true, startIndex, total: priority.total, ready: priority.ready, failed: priority.failed };
      };

      const pulseVocabCard = (mode = "word") => {
        if (!vocabCard || vocabCard.classList.contains("is-hidden")) {
          return;
        }
        window.clearTimeout(vocabPulseTimer);
        vocabCard.classList.remove("is-word-pulse", "is-round-pulse");
        void vocabCard.offsetWidth;
        vocabCard.classList.add(mode === "round" ? "is-round-pulse" : "is-word-pulse");
        vocabPulseTimer = window.setTimeout(() => {
          vocabCard.classList.remove("is-word-pulse", "is-round-pulse");
        }, mode === "round" ? 1250 : 980);
      };

      vocabVoiceKey = readStoredVocabVoice();
      currentAccent = vocabVoiceAccent(vocabVoiceKey);
      syncVocabVoiceSwitch();
      window.addEventListener("storage", (event) => {
        const user = clean(currentAuthUsername || "");
        if (!user || event.key !== vocabVoiceUserStorageKey(user)) {
          return;
        }
        let incomingEpoch = 0;
        try {
          const meta = JSON.parse(localStorage.getItem(vocabVoiceUserMetaKey(user)) || "{}");
          incomingEpoch = Math.max(0, Number(meta && meta.updated_epoch || 0) || 0);
        } catch (error) {
        }
        if (incomingEpoch < vocabVoicePreferenceEpoch) {
          return;
        }
        vocabVoicePreferenceEpoch = incomingEpoch;
        vocabVoiceKey = normalizeVocabVoiceKey(event.newValue || "sot:en-GB");
        currentAccent = vocabVoiceAccent(vocabVoiceKey);
        vocabVoiceSelectionEpoch += 1;
        // Accent asset IDs include voice and revision; cancel only the old
        // preload plan and preserve unrelated Space audio blob URLs.
        vocabAudioCacheToken += 1;
        syncVocabVoiceSwitch();
      });

      const playVocabAudio = async (voiceKey = selectedVocabVoiceKey(), itemOverride = null, options = {}) => {
        const item = itemOverride || currentVocabItem();
        if (!item) {
          return false;
        }
        if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
          return false;
        }
        const shortKey = /en-gb/i.test(voiceKey) ? "uk" : "us";
        const clip = (item.audio && (item.audio[voiceKey] || item.audio[voiceKey.toLowerCase()] || item.audio[shortKey])) || null;
        if (clip) {
          const clipPlayed = await playAudioClipOnce(clip, options);
          if (clipPlayed) {
            return true;
          }
        }
        if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
          return false;
        }
        const sotPlayed = await playSoundOfText(item.word, voiceKey.replace(/^sot:/i, "") || "en-US", options);
        if (sotPlayed) {
          return true;
        }
        // Added 2026-07-31: do not bypass the server audio contract after a
        // SOT miss; browser speech is allowed only from the explicit final
        // `tts_all_generation_failed` path inside playSoundOfText().
        return false;
      };

      const playVocabAnswerThen = async (item, index, nextStep, options = {}) => {
        const keepLockedAfterPlayback = Boolean(options.keepLockedAfterPlayback);
        const lockDuringPlayback = options.lockDuringPlayback !== false;
        const expectedWordKey = vocabWordKey(item);
        const playbackToken = ++vocabAnswerAudioToken;
        const playOptions = {
          shouldPlay: () => playbackToken === vocabAnswerAudioToken && vocabModeActive,
        };
        if (lockDuringPlayback) {
          vocabAnswerBusy = true;
          setVocabInputLocked(true);
        }
        try {
          await playVocabAudio(selectedVocabVoiceKey(), item, playOptions);
        } finally {
          if (lockDuringPlayback) {
            vocabAnswerBusy = false;
            if (!keepLockedAfterPlayback) {
              setVocabInputLocked(false);
            }
          }
        }
        if (playbackToken !== vocabAnswerAudioToken || !vocabModeActive) {
          return;
        }
        if (
          vocabCurrentIndex === Number(index)
          && vocabWordKey(vocabItems[vocabCurrentIndex] || null) === expectedWordKey
          && typeof nextStep === "function"
        ) {
          nextStep();
        } else if (lockDuringPlayback && keepLockedAfterPlayback) {
          setVocabInputLocked(false);
        }
      };

      const postSpaceVClientEvent = () => {};

      // 2026-07-20: Keep Space_V answer feedback immediate even when cached MP3 assets arrive late.
      const playVocabFeedbackSound = (name) => playGeneratedEffectTone(name).then((played) => (
        played ? true : playEffectSoundAsync(name)
      ));

      const checkVocabProbeAnswer = async (item, typed, rawText) => {
        scheduleVocabCardPin(1200, { force: true });
        const key = vocabWordKey(item);
        const expected = normalize(item.word);
        const attempts = Number(vocabAttemptCounts.get(key) || 0);
        const index = vocabCurrentIndex;
        if (typed === expected) {
          clearVocabHintTimers();
          if (vocabKnownAtStartKeys.has(key)) {
            awardVocabCrystalOnce("green", item);
          } else if (vocabBlueCrystalReadyKeys.has(key)) {
            awardVocabCrystalOnce("blue", item);
            vocabBlueCrystalReadyKeys.delete(key);
          } else {
            awardVocabCrystalOnce("yellow", item);
          }
          vocabLearnedKeys.add(key);
          updateVocabRuntimeProgress();
          postSpaceVClientEvent("progress_after_probe_correct", { item, typed, reason: "probe_correct" });
          const shouldCompleteMission = !vocabRemainingProbeIndexes().length && !vocabStudyIndexes.length;
          if (shouldCompleteMission) {
            setVocabInputLocked(true);
          }
          revealVocabAnswerMeta(item, [`Correct: ${item.word}`]);
          setVocabFeedback(
            shouldCompleteMission
              ? `Final answer accepted: ${item.word}. Completing this vocabulary pack.`
              : `Correct: ${item.word}. Playing the answer.`,
            "ok",
          );
          scheduleVocabCardPin(1600, { force: true });
          renderVocabStrip();
          renderVocabLearnedPanel(item);
          queueVocabProgressSave(600);
          void playVocabFeedbackSound("true");
          await delay(140);
          await playVocabAnswerThen(item, index, () => window.setTimeout(() => {
            if (shouldCompleteMission) {
              completeVocabularyMission();
              return;
            }
            startNextVocabProbe();
          }, shouldCompleteMission ? 120 : 220), { keepLockedAfterPlayback: shouldCompleteMission });
          return;
        }
        if (!rawText && attempts <= 0) {
          clearVocabHintTimers(false);
          addVocabUnlearnedIndex(vocabCurrentIndex, { deferSave: true });
          revealVocabAnswerMeta(item, [`Answer: ${item.word}`]);
          setVocabTimerState("Miss signal: answer playback before training route.", "miss");
          setVocabFeedback("Skipped. Added to Unlearned Words. Playing the answer first.", "error");
          scheduleVocabCardPin(1600, { force: true });
          await playVocabFeedbackSound("false");
          await playVocabAnswerThen(item, index, routeAfterVocabUnlearned);
          return;
        }
        if (attempts <= 0) {
          vocabAttemptCounts.set(key, 1);
          vocabCurrentHadError = true;
          void playVocabFeedbackSound("false");
          const letters = clean(item.word).replace(/\s+/g, "").length;
          renderVocabMeta(item, [`Hint: ${letters} letters`]);
          setVocabActiveHint("letters", item, index);
          setVocabTimerState("Miss signal logged. Timer stays online.", "miss");
          setVocabFeedback("Not correct. One more try.", "error");
          scheduleVocabCardPin(1200, { force: true });
          queueVocabProgressSave(600);
          if (vocabAnswer) {
            vocabAnswer.value = "";
            vocabAnswer.focus({ preventScroll: true });
          }
          return;
        }
        clearVocabHintTimers(false);
        addVocabUnlearnedIndex(vocabCurrentIndex, { deferSave: true });
        revealVocabAnswerMeta(item, [`Answer: ${item.word}`]);
        setVocabTimerState("Second miss: answer playback before training route.", "miss");
        setVocabFeedback("Second miss. Added to Unlearned Words. Playing the answer first.", "error");
        scheduleVocabCardPin(1600, { force: true });
        await playVocabFeedbackSound("false");
        await playVocabAnswerThen(item, index, routeAfterVocabUnlearned);
      };

      const checkVocabDrillAnswer = async (item, typed) => {
        scheduleVocabCardPin(1200, { force: true });
        const expected = normalize(item.word);
        if (typed !== expected) {
          vocabDrillFailCount += 1;
          vocabCurrentHadError = true;
          void playVocabFeedbackSound("false");
          renderVocabMeta(item, [`Answer: ${item.word}`], { revealWord: true });
          renderVocabSideCards(item);
          setVocabFeedback("Training miss. Type the visible word again.", "error");
          scheduleVocabCardPin(1200, { force: true });
          queueVocabProgressSave(600);
          if (vocabAnswer) {
            vocabAnswer.value = "";
            vocabAnswer.focus({ preventScroll: true });
          }
          return;
        }
        const index = vocabCurrentIndex;
        clearVocabHintTimers(false);
        vocabDrillCorrectCount += 1;
        vocabCurrentHadError = false;
        updateVocabRuntimeProgress();
        postSpaceVClientEvent("progress_after_drill_correct", { item, typed, reason: "drill_correct" });
        void playVocabFeedbackSound("true");
        renderVocabMeta(item, [], { repetitionFlash: true });
        if (vocabDetailPanel) {
          vocabDetailPanel.classList.add("is-hidden");
        }
        window.requestAnimationFrame(positionVocabSideCards);
        queueVocabProgressSave(600);
        if (vocabDrillCorrectCount >= 10) {
          setVocabFeedback(`Training complete: ${item.word}. Playing word audio.`, "ok");
          scheduleVocabCardPin(1600, { force: true });
          await playVocabAnswerThen(item, index, () => {
            transitionToNextVocabDrillItem();
          });
          return;
        }
        setVocabFeedback("Good. Listen and keep typing until 10 repetitions.", "ok");
        scheduleVocabCardPin(1400, { force: true });
        await playVocabAnswerThen(item, index, null, { lockDuringPlayback: false });
      };

      const checkVocabShuffleAnswer = async (item, typed) => {
        scheduleVocabCardPin(1200, { force: true });
        const expected = normalize(item.word);
        if (typed === expected) {
          const index = vocabCurrentIndex;
          const finalShuffleAnswer = vocabShuffleRound >= 5 && !vocabShuffleQueue.length;
          clearVocabHintTimers(false);
          vocabShuffleCorrectCount += 1;
          vocabShuffleFailCount = 0;
          updateVocabRuntimeProgress();
          postSpaceVClientEvent("progress_after_shuffle_correct", { item, typed, reason: "shuffle_correct" });
          renderVocabMeta(item, [`Round clear: ${item.word}`], {
            revealIpa: true,
            revealWord: true,
          });
          setVocabFeedback(`Round clear: ${item.word}. Playing answer signal.`, "ok");
          scheduleVocabCardPin(1600, { force: true });
          void playVocabFeedbackSound("true");
          queueVocabProgressSave(600);
          await delay(140);
          await playVocabAnswerThen(
            item,
            index,
            () => window.setTimeout(() => {
              if (finalShuffleAnswer) {
                finishVocabShuffle();
                return;
              }
              showNextVocabShuffleQuestion({ clearInput: true });
            }, finalShuffleAnswer ? 120 : 220),
            { keepLockedAfterPlayback: true },
          );
          return;
        }
        vocabShuffleFailCount += 1;
        void playVocabFeedbackSound("false");
        queueVocabProgressSave(600);
        const extra = [`Hint: ${clean(item.word).replace(/\s+/g, "").length} letters`];
        renderVocabMeta(item, extra, {
          revealIpa: true,
          revealWord: vocabShuffleFailCount >= 2,
        });
        setVocabActiveHint("letters", item, vocabCurrentIndex);
        setVocabFeedback("Shuffle miss. Try this word again.", "error");
        scheduleVocabCardPin(1200, { force: true });
        if (vocabAnswer) {
          vocabAnswer.value = "";
          vocabAnswer.focus({ preventScroll: true });
        }
      };

      const checkVocabAnswer = async () => {
        scheduleVocabCardPin(900, { force: true });
        stopVocabMeaningAudio();
        const item = currentVocabItem();
        if (!item || !vocabAnswer) {
          postSpaceVClientEvent("answer_blocked", { reason: !item ? "missing_item" : "missing_input" });
          return;
        }
        const clearFastVocabInput = () => {
          if (vocabAnswer && (vocabPhase === "drill" || vocabPhase === "shuffle")) {
            vocabAnswer.value = "";
          }
        };
        postSpaceVClientEvent("answer_enter", {
          item,
          typed: vocabAnswer.value,
          reason: `busy=${Boolean(vocabAnswerBusy)} readonly=${Boolean(vocabAnswer.readOnly)} phase=${vocabPhase}`,
        });
        if (vocabAnswerBusy) {
          clearFastVocabInput();
          setVocabFeedback("Answer playback is running. Please wait for the next signal.", "ok");
          postSpaceVClientEvent("answer_blocked", { item, typed: vocabAnswer.value, reason: "answer_busy" });
          return;
        }
        if (vocabAutoRevealLock) {
          setVocabFeedback("Answer is already revealed. Routing this word to training.", "error");
          postSpaceVClientEvent("answer_blocked", { item, typed: vocabAnswer.value, reason: "auto_reveal_lock" });
          return;
        }
        const now = Date.now();
        const suppressRapidSubmit = vocabPhase !== "drill";
        if (suppressRapidSubmit && now < vocabAnswerSubmitLockUntil) {
          postSpaceVClientEvent("answer_blocked", { item, typed: vocabAnswer.value, reason: "submit_lock" });
          return;
        }
        if (vocabAnswer.disabled) {
          postSpaceVClientEvent("answer_blocked", { item, reason: "input_reset_lock" });
          return;
        }
        if (vocabCompletionFinalizing || vocabPhase === "complete") {
          vocabAnswer.value = "";
          setVocabFeedback("Final reward update is running. Please wait for the leaderboard.", "ok");
          postSpaceVClientEvent("answer_blocked", { item, reason: "completion_finalizing" });
          return;
        }
        if (vocabAnswer.readOnly) {
          clearFastVocabInput();
          setVocabFeedback("Next vocabulary signal is loading. Please wait.", "ok");
          postSpaceVClientEvent("answer_blocked", { item, typed: vocabAnswer.value, reason: "input_readonly" });
          return;
        }
        vocabAnswerSubmitLockUntil = suppressRapidSubmit ? now + 220 : 0;
        const rawText = clean(vocabAnswer.value);
        const typed = normalize(vocabAnswer.value);
        postSpaceVClientEvent("answer_submit", { item, typed, reason: rawText ? "typed" : "empty" });
        if (rawText) {
          vocabAnswer.value = "";
        }
        if (vocabPhase === "probe") {
          await checkVocabProbeAnswer(item, typed, rawText);
          return;
        }
        if (vocabPhase === "drill") {
          await checkVocabDrillAnswer(item, typed);
          return;
        }
        if (vocabPhase === "shuffle") {
          await checkVocabShuffleAnswer(item, typed);
        }
      };

      const enterVocabularyPayloadNow = async (payload, options = {}) => {
        const normalized = normalizeCompactVocabPayload(payload);
        if (!normalized.words.length) {
          setLoadStatus("File vocabulary chua co tu hop le.", true);
          return false;
        }
        void ensureOfflineStoragePersistence();
        updateFutureAppRoute("space_v", { replace: futureAppRouteFromLocation() === "lesson_vault" });
        if (!currentVocabProgressCache.progressKey || currentVocabProgressCache.identity !== vocabProgressIdentityFor(normalized, normalized.words)) {
          configureVocabProgressCache(normalized, normalized.words);
        }
        const resumeState = options.resumeState && typeof options.resumeState === "object" ? options.resumeState : null;
        if (!options.skipAudioPrepare && loadGate && !loadGate.classList.contains("is-hidden")) {
          setLoadStatus("Vocabulary audio will warm progressively while the first card opens.");
        }
        if (authToken && (typeof hasVocabRegistrySyncDirty !== "function" || hasVocabRegistrySyncDirty())) {
          scheduleVocabRegistrySync(1800);
        }
        if (authToken && !vocabRegistryLoaded && typeof applyVocabRegistryLocalCache === "function") {
          applyVocabRegistryLocalCache(currentAuthUsername || "");
        }
        try {
          resetCurrentMissionCrystalAwards();
          resetQuestionMode();
          resetParagraphMode();
          lessonCompletionSent = false;
          completionSyncBusy = false;
          vocabCompletionFinalizing = false;
          vocabReviewRunActive = Boolean(options.reviewRun || (resumeState && (resumeState.reviewing || resumeState.reviewRun)));
          vocabActiveRunId = clean(resumeState && (resumeState.runId || resumeState.run_id)) || `space-v-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
          vocabModeTransitioning = false;
          hideVocabModePopup();
          clearVocabHintTimers();
          vocabImageLoadToken += 1;
          vocabImageFetchInflight.clear();
          vocabImageResultCache.clear();
          vocabImageRetryCounts.clear();
          vocabImageBytePrefetches.clear();
          vocabImageBlobUrls.forEach((url) => URL.revokeObjectURL(url));
          vocabImageBlobUrls.clear();
          if (vocabImagePrefetchTimer) {
            window.clearTimeout(vocabImagePrefetchTimer);
            vocabImagePrefetchTimer = 0;
          }
          vocabModeActive = true;
          setVocabModeClass(true);
          setSpaceWModeClass(false);
          scheduleMobileInfiniteMotionSync(80);
          setQuestionInventoryHudVisible(true);
          void loadQuestionInventory();
          scheduleVocabCupLeaderboardPrewarm(1800, { minGapMs: 30000 });
          vocabItems = normalized.words;
          vocabQueue = resumeState && Array.isArray(resumeState.queue)
            ? resumeState.queue.map((idx) => Math.max(0, Number(idx) || 0)).filter((idx) => idx < vocabItems.length)
            : shuffleIndexes(vocabItems.length);
          vocabBatch = [];
          vocabRoundQueue = [];
          vocabCurrentIndex = resumeState ? Math.max(-1, Math.floor(Number(resumeState.currentIndex) || -1)) : -1;
          vocabCurrentHadError = false;
          vocabLearnedKeys = new Set(Array.isArray(resumeState && resumeState.learned) ? resumeState.learned.map(clean).filter(Boolean) : []);
          vocabAttemptCounts = new Map(Array.isArray(resumeState && resumeState.attempts) ? resumeState.attempts : []);
          vocabStudyIndexes = Array.isArray(resumeState && resumeState.studyIndexes)
            ? resumeState.studyIndexes.map((idx) => Math.max(0, Number(idx) || 0)).filter((idx) => idx < vocabItems.length)
            : [];
          vocabStudyIndexes = vocabStudyIndexes.filter((idx) => {
            const key = vocabWordKey(vocabItemByIndex(idx));
            return Boolean(key && !vocabLearnedKeys.has(key));
          });
          vocabStudyKeys = new Set(vocabStudyIndexes.map((idx) => vocabWordKey(vocabItemByIndex(idx))).filter(Boolean));
          vocabKnownAtStartKeys = new Set(vocabRegistryKeys);
          vocabBlueCrystalReadyKeys = new Set(Array.isArray(resumeState && resumeState.blueReady) ? resumeState.blueReady.map(clean).filter(Boolean) : []);
          vocabPhase = clean(resumeState && resumeState.phase) || "probe";
          vocabQueue = vocabQueue.filter(vocabCanProbeIndex);
          if (vocabPhase === "probe" && vocabCurrentIndex >= 0 && !vocabCanProbeIndex(vocabCurrentIndex)) {
            vocabCurrentIndex = -1;
          }
          applyVocabPhaseVisualState();
          vocabDrillIndex = Math.max(0, Math.floor(Number(resumeState && resumeState.drillIndex) || 0));
          vocabDrillCorrectCount = Math.max(0, Math.floor(Number(resumeState && resumeState.drillCorrectCount) || 0));
          vocabDrillFailCount = Math.max(0, Math.floor(Number(resumeState && resumeState.drillFailCount) || 0));
          vocabShuffleOriginal = Array.isArray(resumeState && resumeState.shuffleOriginal) ? resumeState.shuffleOriginal.map((idx) => Math.max(0, Number(idx) || 0)).filter((idx) => idx < vocabItems.length) : [];
          vocabShuffleRound = Math.max(0, Math.floor(Number(resumeState && resumeState.shuffleRound) || 0));
          vocabShuffleQueue = Array.isArray(resumeState && resumeState.shuffleQueue) ? resumeState.shuffleQueue.map((idx) => Math.max(0, Number(idx) || 0)).filter((idx) => idx < vocabItems.length) : [];
          vocabShuffleCorrectCount = Math.max(0, Math.floor(Number(resumeState && resumeState.shuffleCorrectCount) || 0));
          vocabShuffleFailCount = Math.max(0, Math.floor(Number(resumeState && resumeState.shuffleFailCount) || 0));
          currentVocabularyMission = normalized.mission && typeof normalized.mission === "object" ? normalized.mission : null;
          lessonNodes = vocabItems.map((item) => ({ vi: item.meaning, en: item.word }));
          lessonEffects = normalizeEffectSounds(normalized.effects || {});
          preloadLessonEffectSounds();
          pendingVocabularyPayload = null;
          pendingParagraphPayload = null;
          pendingLessonNodes = [];
          pendingLessonEffects = {};
          currentLessonSource.title = currentLessonSource.title || lessonTitleFromPayload(normalized);
          loadGate.classList.add("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus("");
          stopActiveAudio();
          stopVocabMeaningAudio();
          hideSpeakPanel();
          hideHintPanel();
          hideScorePanel(true);
          hideGrammarQuiz(false, true);
          clearAllConnectors();
          if (cardNode) {
            cardNode.classList.add("is-hidden");
          }
          if (vocabCard) {
            vocabCard.classList.remove("is-hidden");
            resetVocabCardRevealStyles();
          }
          syncVocabMobilePin();
          scheduleVocabCardPin(1800, { force: true });
          scheduleVocabCardVisibilityGuard();
          window.requestAnimationFrame(() => {
            syncVocabMobilePin();
            scheduleVocabCardPin(1800, { force: true });
            scheduleVocabCardVisibilityGuard();
          });
          renderVocabUnlearnedList();
          renderVocabLearnedPanel();
          if (authToken) {
            scheduleVocabRegistrySync(4000);
          }
          window.setTimeout(positionVocabLearnedPanel, 140);
          if (vocabPhase === "drill") {
            showCurrentVocabDrillItem();
          } else if (vocabPhase === "shuffle") {
            showNextVocabShuffleQuestion();
          } else if (vocabStudyIndexes.length >= VOCAB_BATCH_SIZE) {
            startVocabDrill(true);
          } else if (resumeState && vocabCurrentIndex >= 0 && vocabItemByIndex(vocabCurrentIndex)) {
            showVocabItem(vocabItemByIndex(vocabCurrentIndex), vocabCurrentIndex, {
              message: "Saved Space_V progress restored.",
              clearInput: true,
            });
          } else {
            startNextVocabProbe();
          }
          const initialProgressRecord = options.deferInitialProgressSave
            ? null
            : saveVocabProgressNow({ queueServerSync: false });
          if (initialProgressRecord) {
            initialProgressRecord.action = options.forceNewRun ? "new_run" : "autosave";
            if (options.forceNewRun && initialProgressRecord.state) {
              initialProgressRecord.state.newRun = true;
              initialProgressRecord.state.forceNewRun = true;
            }
            queueVocabServerProgressSync(initialProgressRecord, 0);
          }
          warmVocabularyAudioCacheForLesson(normalized, {
            startIndex: Math.max(0, Number(vocabCurrentIndex) || 0),
            label: "Space_V",
            includeAlternates: false,
            includeMeaning: true,
            startDelayMs: 700,
            delayMs: 45,
            status: false,
          });
          return true;
        } catch (error) {
          loadGate.classList.remove("is-hidden");
          loadGate.classList.remove("is-file-ready");
          setLoadStatus(error && error.message ? error.message : "Khong mo duoc vocabulary pack.", true);
          return false;
        }
      };

      const normalizeLessonPayloadNodes = (payload) => {
        const nodes = Array.isArray(payload && payload.nodes)
          ? payload.nodes
          : (Array.isArray(payload && payload.n) ? payload.n : []);
        const cleanNodes = nodes
          .map((node) => ({
            ...node,
            vi: clean(node.vi ?? node.q ?? ""),
            en: clean(node.en ?? node.e ?? ""),
            ipa: clean(node.ipa ?? node.i ?? ""),
          }))
          .filter((node) => node.vi && node.en);
        if (!cleanNodes.length) {
          throw new Error("Bài học chưa có node hợp lệ.");
        }
        return cleanNodes;
      };

      const shouldAutoStartLoadedFileInPopup = () => {
        const protocol = clean(window.location.protocol).toLowerCase();
        const href = clean(window.location.href).toLowerCase();
        return isPopupFullscreenMode() ||
          protocol === "about:" ||
          protocol === "blob:" ||
          href === "about:blank" ||
          params.get("ft_popup") === "1" ||
          Boolean(bootstrapState && bootstrapState.popupFullscreen) ||
          Boolean(window.opener && window.opener !== window);
      };
