

      const positionQuestionRootInfo = (sourceNode, options = {}) => {
        if (!shellNode || !questionRootInfoCard || !questionRootInfoConnector || !sourceNode) {
          return;
        }
        const isQuestion = Boolean(options && options.isQuestion);
        const shellRect = shellNode.getBoundingClientRect();
        const sourceRect = sourceNode.getBoundingClientRect();
        const isRegionQuestion = Boolean(isQuestion && options.regionMode);
        const pictureRect = qPictureCard && qPictureCard.classList.contains("is-live")
          ? qPictureCard.getBoundingClientRect()
          : sourceRect;
        const shellWidth = questionUnscaleLayoutValue(shellRect.width);
        const shellHeight = questionUnscaleLayoutValue(shellRect.height);
        const sourceLeft = questionUnscaleLayoutValue(sourceRect.left - shellRect.left);
        const sourceTop = questionUnscaleLayoutValue(sourceRect.top - shellRect.top);
        const sourceWidth = questionUnscaleLayoutValue(sourceRect.width);
        const sourceHeight = questionUnscaleLayoutValue(sourceRect.height);
        const sourceRight = sourceLeft + sourceWidth;
        const sourceBottom = sourceTop + sourceHeight;
        const rootRect = qRootCard && qRootCard.getBoundingClientRect ? qRootCard.getBoundingClientRect() : sourceRect;
        const rootLeft = questionUnscaleLayoutValue(rootRect.left - shellRect.left);
        const rootTop = questionUnscaleLayoutValue(rootRect.top - shellRect.top);
        const rootWidth = questionUnscaleLayoutValue(rootRect.width);
        const rootHeight = questionUnscaleLayoutValue(rootRect.height);
        const rootRight = rootLeft + rootWidth;
        const rootBottom = rootTop + rootHeight;
        const pictureLeft = questionUnscaleLayoutValue(pictureRect.left - shellRect.left);
        const pictureTop = questionUnscaleLayoutValue(pictureRect.top - shellRect.top);
        const pictureWidth = questionUnscaleLayoutValue(pictureRect.width);
        const pictureHeight = questionUnscaleLayoutValue(pictureRect.height);
        const pictureRight = pictureLeft + pictureWidth;
        const pictureBottom = pictureTop + pictureHeight;
        const highlightLinkMode = Boolean(isQuestion && options.payload && options.payload.anchor === "highlight");
        const splitLayout = isQuestion && questionSplitDesktopLayoutActive() ? questionSplitLayoutMetrics() : null;
        let cardWidth = isQuestion
          ? (splitLayout
            ? splitLayout.rightWidth
            : (highlightLinkMode
              ? Math.min(420, Math.max(310, Math.min(rootWidth * 0.52, shellWidth * 0.32)))
              : Math.min(430, Math.max(310, shellWidth * 0.34))))
          : Math.min(360, Math.max(260, shellWidth * 0.28));
        const sourceCenterX = sourceLeft + sourceWidth / 2;
        const sourceCenterY = sourceTop + sourceHeight / 2;
        let left = isQuestion
          ? sourceCenterX - cardWidth / 2
          : sourceRight + 28;
        let top = isQuestion
          ? sourceBottom + 54
          : sourceTop - 12;
        const placement = clean(options.placement || "auto").toLowerCase();
        if (splitLayout) {
          left = splitLayout.rightLeft;
          top = rootTop;
        } else if (highlightLinkMode) {
          left = sourceCenterX - cardWidth / 2;
          if (rootWidth > cardWidth + 44) {
            left = Math.max(rootLeft + 22, Math.min(left, rootRight - cardWidth - 22));
          }
          top = rootBottom + Math.max(26, Math.min(42, rootHeight * 0.08));
          if (placement === "above") {
            top = Math.max(16, rootTop - 190);
          } else if (placement === "auto" && top > shellHeight - 190 && sourceTop > rootTop + rootHeight * 0.28) {
            top = Math.max(16, rootTop - 190);
          }
        } else if (isQuestion && (placement === "above" || (placement === "auto" && sourceCenterY > shellHeight * 0.46))) {
          top = sourceTop - 166;
        }
        if (isRegionQuestion && !splitLayout) {
          const gap = Math.max(42, Math.min(78, pictureWidth * 0.14));
          const verticalUnit = pictureRegionQuestionVerticalUnit(options.payload || questionRootInfoActivePayload || {});
          const targetY = pictureTop + pictureHeight * (0.18 + verticalUnit * 0.64);
          left = pictureRight + gap;
          top = targetY - 84;
        }
        if (!isQuestion && left + cardWidth > shellWidth - 16) {
          left = Math.max(16, sourceLeft - cardWidth - 28);
        }
        if (splitLayout) {
          left = splitLayout.rightLeft;
        } else if (!isRegionQuestion) {
          left = Math.max(16, Math.min(left, Math.max(16, shellWidth - cardWidth - 16)));
        } else {
          left = Math.max(pictureRight + 28, left);
        }
        top = Math.max(16, Math.min(top, Math.max(16, shellHeight - 180)));
        questionRootInfoCard.style.width = `${cardWidth}px`;
        if (splitLayout) {
          questionRootInfoCard.style.maxWidth = `${cardWidth}px`;
          questionRootInfoCard.style.maxHeight = `${Math.max(260, shellHeight - top - 42)}px`;
          questionRootInfoCard.style.overflowY = "auto";
        } else {
          questionRootInfoCard.style.removeProperty("max-width");
          questionRootInfoCard.style.removeProperty("max-height");
          questionRootInfoCard.style.removeProperty("overflow-y");
        }
        questionRootInfoCard.style.left = `${left}px`;
        questionRootInfoCard.style.top = `${top}px`;
        let cardRect = questionRootInfoCard.getBoundingClientRect();
        if (isRegionQuestion && !splitLayout) {
          const verticalUnit = pictureRegionQuestionVerticalUnit(options.payload || questionRootInfoActivePayload || {});
          const cardHeight = questionUnscaleLayoutValue(cardRect.height);
          const targetY = pictureTop + pictureHeight * (0.18 + verticalUnit * 0.64);
          top = Math.max(16, Math.min(targetY - cardHeight / 2, Math.max(16, shellHeight - cardHeight - 44)));
          questionRootInfoCard.style.top = `${top}px`;
          cardRect = questionRootInfoCard.getBoundingClientRect();
        }
        const cardLeft = questionUnscaleLayoutValue(cardRect.left - shellRect.left);
        const cardTop = questionUnscaleLayoutValue(cardRect.top - shellRect.top);
        const cardWidthMeasured = questionUnscaleLayoutValue(cardRect.width);
        const cardHeightMeasured = questionUnscaleLayoutValue(cardRect.height);
        const cardRight = cardLeft + cardWidthMeasured;
        const cardBottom = cardTop + cardHeightMeasured;
        const defaultStart = highlightLinkMode
          ? {
            x: Math.min(rootRight + 10, Math.max(sourceRight + 8, sourceLeft + sourceWidth * 0.72)),
            y: sourceCenterY,
          }
          : {
            x: sourceCenterX,
            y: sourceCenterY,
          };
        const end = splitLayout
          ? {
            x: cardLeft,
            y: cardTop + Math.min(cardHeightMeasured * 0.42, 88),
          }
          : (highlightLinkMode
          ? (cardLeft >= sourceRight + 30
            ? {
              x: cardLeft,
              y: cardTop + Math.min(cardHeightMeasured * 0.34, 82),
            }
            : {
              x: Math.max(cardLeft + 30, Math.min(sourceRight + 42, cardRight - 30)),
              y: cardTop,
            })
          : {
            x: cardLeft + (cardLeft > sourceLeft ? 0 : cardWidthMeasured),
            y: cardTop + Math.min(cardHeightMeasured * 0.42, 60),
          });
        if (!isQuestion) {
          ensureQuestionRootInfoConnectorBaseSegments(questionRootInfoConnector);
          questionRootInfoConnector.classList.remove("is-elbow");
          questionRootInfoConnector.classList.remove("is-region-rail");
          questionRootInfoConnector.classList.remove("is-highlight-rail");
          positionQuestionLine(questionRootInfoConnector, defaultStart, end);
          questionRootInfoExtraConnectors.forEach((connector) => {
            connector.classList.remove("is-live", "is-focused", "is-elbow", "is-region-rail", "is-highlight-rail");
          });
          return;
        }
        const highlightAnchorStarts = (() => {
          if (!highlightLinkMode || !qRootText || !sourceNode) {
            return [];
          }
          const ranges = questionRootHighlightRangesForItem(currentQuestionItem())
            .filter((range) => range && Number(range.end) > Number(range.start) && !range.selectTarget);
          const sourceIndexes = new Set(ranges.map((range) => Math.max(0, Number(range.sourceIndex) || 0)));
          const highlightNodes = Array.from(qRootText.querySelectorAll(".ft-q-root-highlight:not(.is-select-target)"))
            .filter((node) => {
              const index = Math.max(0, Number(node && node.dataset && node.dataset.qhIndex) || 0);
              return sourceIndexes.size ? sourceIndexes.has(index) : node === sourceNode;
            });
          const nodes = highlightNodes.length
            ? highlightNodes
            : [sourceNode].filter((node) => node && node.getBoundingClientRect);
          const seen = new Set();
          return nodes.map((node, index) => {
            const rect = node.getBoundingClientRect();
            if (!rect || rect.width <= 0 || rect.height <= 0) {
              return null;
            }
            const left = questionUnscaleLayoutValue(rect.left - shellRect.left);
            const top = questionUnscaleLayoutValue(rect.top - shellRect.top);
            const width = questionUnscaleLayoutValue(rect.width);
            const height = questionUnscaleLayoutValue(rect.height);
            const key = `${Math.round(left)}:${Math.round(top)}:${Math.round(width)}:${Math.round(height)}`;
            if (seen.has(key)) {
              return null;
            }
            seen.add(key);
            return {
              x: Math.min(rootRight + 10, Math.max(left + width + 8, left + width * 0.72)),
              y: top + height / 2,
              index,
              rect: {
                left,
                top,
                right: left + width,
                bottom: top + height,
                width,
                height,
              },
            };
          }).filter(Boolean);
        })();
        const starts = Array.isArray(options.regionStarts) && options.regionStarts.length
          ? options.regionStarts
          : (highlightAnchorStarts.length ? highlightAnchorStarts : [defaultStart]);
        const rootDecorationRects = [
          document.getElementById("ft-q-root-hud"),
        ].map((node) => {
          if (!node || !node.getBoundingClientRect) {
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
          }, 16);
        }).filter(Boolean);
        const rootTextLineRects = (() => {
          if (!qRootText || !qRootText.querySelectorAll) {
            return [];
          }
          const rects = [];
          Array.from(qRootText.querySelectorAll(".ft-q-root-line")).forEach((line) => {
            const fallbackRect = line.getBoundingClientRect();
            let inkRects = [];
            if (document.createRange) {
              try {
                const range = document.createRange();
                range.selectNodeContents(line);
                inkRects = Array.from(range.getClientRects()).filter((rect) => rect && rect.width > 1 && rect.height > 1);
                range.detach && range.detach();
              } catch (error) {
                inkRects = [];
              }
            }
            const usableRects = inkRects.length ? inkRects : [fallbackRect];
            usableRects.forEach((rect) => {
              if (!rect || rect.width <= 1 || rect.height <= 1) {
                return;
              }
              const left = questionUnscaleLayoutValue(rect.left - shellRect.left);
              const top = questionUnscaleLayoutValue(rect.top - shellRect.top);
              const width = questionUnscaleLayoutValue(rect.width);
              const height = questionUnscaleLayoutValue(rect.height);
              rects.push({
                left: left - 2,
                top: top - 2,
                right: left + width + 2,
                bottom: top + height + 2,
                width: width + 4,
                height: height + 4,
              });
            });
          });
          return rects.sort((leftRect, rightRect) => leftRect.top - rightRect.top || leftRect.left - rightRect.left);
        })();
        const highlightLaneIntersectsText = (y) => rootTextLineRects.some((rect) => (
          y > rect.top + 2 && y < rect.bottom - 2
        ));
        const questionHighlightConnectorLaneY = (safeStart, desiredY, index = 0) => {
          if (!rootTextLineRects.length || !safeStart) {
            return desiredY;
          }
          const preferred = Number.isFinite(Number(desiredY)) ? Number(desiredY) : safeStart.y;
          const sourceLine = rootTextLineRects.find((rect) => safeStart.y >= rect.top - 1 && safeStart.y <= rect.bottom + 1)
            || rootTextLineRects.slice().sort((leftRect, rightRect) => (
              Math.abs((leftRect.top + leftRect.bottom) / 2 - safeStart.y) - Math.abs((rightRect.top + rightRect.bottom) / 2 - safeStart.y)
            ))[0];
          const candidates = [];
          rootTextLineRects.forEach((rect, rectIndex) => {
            const next = rootTextLineRects[rectIndex + 1];
            if (next && next.top - rect.bottom >= 4) {
              candidates.push((rect.bottom + next.top) / 2);
            }
          });
          if (sourceLine) {
            candidates.push(sourceLine.top - 7 - index * 3);
            candidates.push(sourceLine.bottom + 7 + index * 3);
            const before = rootTextLineRects.filter((rect) => rect.bottom <= sourceLine.top - 2).pop();
            const after = rootTextLineRects.find((rect) => rect.top >= sourceLine.bottom + 2);
            if (before && sourceLine.top - before.bottom >= 4) {
              candidates.push((before.bottom + sourceLine.top) / 2 - index * 2);
            }
            if (after && after.top - sourceLine.bottom >= 4) {
              candidates.push((sourceLine.bottom + after.top) / 2 + index * 2);
            }
          }
          const clampedCandidates = candidates
            .map((value) => Math.max(rootTop + 14, Math.min(rootBottom - 14, value)))
            .filter((value, candidateIndex, values) => Number.isFinite(value) && values.findIndex((other) => Math.abs(other - value) < 1) === candidateIndex);
          if (!clampedCandidates.length) {
            const fallback = sourceLine
              ? (preferred < safeStart.y ? sourceLine.top - 10 : sourceLine.bottom + 10)
              : preferred;
            return Math.max(rootTop + 14, Math.min(rootBottom - 14, fallback));
          }
          clampedCandidates.sort((leftValue, rightValue) => {
            const leftPenalty = highlightLaneIntersectsText(leftValue) ? 900 : 0;
            const rightPenalty = highlightLaneIntersectsText(rightValue) ? 900 : 0;
            const leftScore = Math.abs(leftValue - preferred) + Math.abs(leftValue - safeStart.y) * 0.16 + leftPenalty;
            const rightScore = Math.abs(rightValue - preferred) + Math.abs(rightValue - safeStart.y) * 0.16 + rightPenalty;
            return leftScore - rightScore;
          });
          return clampedCandidates[0];
        };
        const questionHighlightConnectorLaneClear = (y, startX, endX) => {
          const left = Math.min(startX, endX);
          const right = Math.max(startX, endX);
          const crossesText = rootTextLineRects.some((rect) => (
            y > rect.top + 1
            && y < rect.bottom - 1
            && Math.max(left, rect.left) < Math.min(right, rect.right)
          ));
          const crossesDecoration = rootDecorationRects.some((rect) => (
            y > rect.top - 1
            && y < rect.bottom + 1
            && Math.max(left, rect.left) < Math.min(right, rect.right)
          ));
          return !crossesText && !crossesDecoration;
        };
        const questionHighlightSmartLaneY = (safeStart, desiredY, startX, endX, index = 0) => {
          const firstLane = questionHighlightConnectorLaneY(safeStart, desiredY, index);
          const sourceRect = safeStart && safeStart.rect ? safeStart.rect : null;
          const candidates = [
            firstLane,
            desiredY,
            sourceRect ? sourceRect.top - 9 - index * 3 : null,
            sourceRect ? sourceRect.bottom + 9 + index * 3 : null,
            ...rootTextLineRects.flatMap((rect, rectIndex) => {
              const next = rootTextLineRects[rectIndex + 1];
              return next && next.top - rect.bottom >= 5 ? [(rect.bottom + next.top) / 2] : [];
            }),
            ...rootDecorationRects.flatMap((rect) => [rect.top - 24 - index * 6, rect.bottom + 24 + index * 6]),
            rootTop + 16 + index * 4,
            rootBottom - 16 - index * 4,
          ]
            .filter((value) => Number.isFinite(Number(value)))
            .map((value) => Math.max(rootTop + 14, Math.min(rootBottom - 14, Number(value))));
          const unique = Array.from(new Set(candidates.map((value) => Math.round(value))));
          unique.sort((leftValue, rightValue) => {
            const leftClear = questionHighlightConnectorLaneClear(leftValue, startX, endX) ? 0 : 3000;
            const rightClear = questionHighlightConnectorLaneClear(rightValue, startX, endX) ? 0 : 3000;
            const leftText = highlightLaneIntersectsText(leftValue) ? 800 : 0;
            const rightText = highlightLaneIntersectsText(rightValue) ? 800 : 0;
            const leftScore = leftClear + leftText + Math.abs(leftValue - firstLane) + Math.abs(leftValue - desiredY) * 0.18;
            const rightScore = rightClear + rightText + Math.abs(rightValue - firstLane) + Math.abs(rightValue - desiredY) * 0.18;
            return leftScore - rightScore;
          });
          return unique.length ? unique[0] : firstLane;
        };
        const routeHighlightAroundDecorations = (safeStart, routeX, laneY, endPoint, options = {}) => {
          const terminalX = endPoint.x - (Number(options.endOffsetX) || 0);
          const sourceRect = safeStart && safeStart.rect ? safeStart.rect : null;
          const anchor = sourceRect
            ? {
              x: sourceRect.left + sourceRect.width / 2,
              y: sourceRect.bottom + 2,
            }
            : safeStart;
          const textExitX = Math.max(
            anchor.x + 28,
            Math.min(
              rootRight + 18,
              Math.max(
                ...rootTextLineRects.map((rect) => rect.right),
                sourceRect ? sourceRect.right : safeStart.x,
              ) + 18,
            ),
          );
          const preferredDropY = sourceRect
            ? Math.max(sourceRect.bottom + 10, Math.min(laneY, sourceRect.bottom + Math.max(18, sourceRect.height * 0.72)))
            : laneY;
          const cleanLaneY = questionHighlightSmartLaneY(safeStart, preferredDropY, anchor.x, terminalX, options.index);
          const routeLaneY = cleanLaneY > anchor.y + 4 ? cleanLaneY : Math.max(anchor.y + 14, cleanLaneY);
          const basePath = [
            anchor,
            { x: anchor.x, y: routeLaneY },
            { x: textExitX, y: routeLaneY },
            { x: routeX, y: routeLaneY },
            { x: terminalX, y: routeLaneY },
            endPoint,
          ];
          const hit = rootDecorationRects.find((rect) => (
            questionRouteSegmentHitsRect(basePath[2], basePath[3], rect)
            || questionRouteSegmentHitsRect(basePath[3], basePath[4], rect)
          ));
          if (!hit) {
            return basePath;
          }
          const index = Math.max(0, Number(options.index) || 0);
          const goUp = routeLaneY <= safeStart.y;
          const bypassX = Math.max(
            Math.min(textExitX, routeX) + 18,
            Math.min(Math.max(anchor.x, routeX) - 18, hit.left - 20),
          );
          const bypassY = goUp
            ? Math.max(rootTop + 18, hit.top - 22 - index * 7)
            : Math.min(rootBottom - 18, hit.bottom + 22 + index * 7);
          const cleanBypassY = questionHighlightSmartLaneY(safeStart, bypassY, textExitX, terminalX, index);
          return [
            anchor,
            { x: anchor.x, y: routeLaneY },
            { x: textExitX, y: routeLaneY },
            { x: textExitX, y: cleanBypassY },
            { x: bypassX, y: cleanBypassY },
            { x: routeX, y: cleanBypassY },
            { x: terminalX, y: cleanBypassY },
            endPoint,
          ];
        };
        if (splitLayout) {
          const compactPath = (points = []) => {
            const result = [];
            points.forEach((point) => {
              const cleanPoint = {
                x: Number(point && point.x) || 0,
                y: Number(point && point.y) || 0,
              };
              const last = result[result.length - 1];
              const prev = result[result.length - 2];
              if (last && Math.abs(last.x - cleanPoint.x) <= 0.5 && Math.abs(last.y - cleanPoint.y) <= 0.5) {
                return;
              }
              if (prev && last) {
                const sameX = Math.abs(prev.x - last.x) <= 0.5 && Math.abs(last.x - cleanPoint.x) <= 0.5;
                const sameY = Math.abs(prev.y - last.y) <= 0.5 && Math.abs(last.y - cleanPoint.y) <= 0.5;
                if (sameX || sameY) {
                  result[result.length - 1] = cleanPoint;
                  return;
                }
              }
              result.push(cleanPoint);
            });
            return result;
          };
          starts.forEach((start, index) => {
            const connector = ensureQuestionRootInfoConnectorAt(index);
            if (!connector) {
              return;
            }
            connector.classList.add("is-live");
            connector.classList.add("is-focused");
            connector.classList.add("is-elbow");
            connector.classList.add("is-region-rail");
            connector.classList.toggle("is-highlight-rail", highlightLinkMode);
            const safeStart = {
              x: Number(start && start.x) || sourceCenterX,
              y: Number(start && start.y) || sourceCenterY,
            };
            const routeX = safeStart.x <= cardLeft
              ? Math.max(safeStart.x + 18, Math.min(cardLeft - 22, safeStart.x + Math.max(44, (cardLeft - safeStart.x) * 0.52)))
              : Math.min(safeStart.x - 18, Math.max(cardLeft - 22, safeStart.x - Math.max(44, (safeStart.x - cardLeft) * 0.52)));
            const path = compactPath(
              highlightLinkMode
                ? routeHighlightAroundDecorations(safeStart, routeX, end.y, end, { index })
                : [safeStart, { x: routeX, y: safeStart.y }, { x: routeX, y: end.y }, end],
            );
            const segments = ensureQuestionRegionConnectorSegments(connector, Math.max(1, path.length - 1));
            segments.forEach((segment, segmentIndex) => {
              positionQuestionRootInfoSegment(segment, path[segmentIndex], path[segmentIndex + 1]);
            });
          });
          questionRootInfoExtraConnectors.forEach((connector, index) => {
            if (index >= starts.length - 1) {
              connector.classList.remove("is-live", "is-focused", "is-elbow", "is-region-rail", "is-highlight-rail");
            }
          });
          return;
        }
        if (isRegionQuestion) {
          const pictureShellRect = {
            left: pictureLeft,
            top: pictureTop,
            right: pictureRight,
            bottom: pictureBottom,
          };
          const regionRects = starts
            .map((start, index) => {
              const rect = start && start.rect ? inflateQuestionRouteRect(start.rect, 12) : null;
              return rect ? { ...rect, sourceIndex: Number.isInteger(start.index) ? start.index : index } : null;
            })
            .filter(Boolean);
          starts.forEach((start, index) => {
            const connector = ensureQuestionRootInfoConnectorAt(index);
            if (!connector) {
              return;
            }
            connector.classList.add("is-live");
            connector.classList.add("is-focused");
            connector.classList.add("is-elbow");
            connector.classList.add("is-region-rail");
            connector.classList.remove("is-highlight-rail");
            const railY = cardBottom + 18 + Math.min(index, 3) * 6;
            const railStart = { x: cardLeft - 18, y: railY };
            const railEnd = { x: cardLeft + Math.min(cardRight - cardLeft - 26, Math.max(150, (cardRight - cardLeft) * 0.72)), y: railY };
            const obstacles = regionRects.filter((rect) => rect.sourceIndex !== (Number.isInteger(start.index) ? start.index : index));
            const route = routeQuestionRegionConnector(start, railStart, obstacles, {
              pictureLeft: pictureShellRect.left,
              pictureRight: pictureShellRect.right,
              pictureTop: pictureShellRect.top,
              pictureBottom: pictureShellRect.bottom,
              margin: 14,
            });
            const path = route.concat([railEnd]);
            const segments = ensureQuestionRegionConnectorSegments(connector, Math.max(1, path.length - 1));
            segments.forEach((segment, segmentIndex) => {
              positionQuestionRootInfoSegment(segment, path[segmentIndex], path[segmentIndex + 1]);
            });
          });
          questionRootInfoExtraConnectors.forEach((connector, index) => {
            if (index >= starts.length - 1) {
              connector.classList.remove("is-live", "is-focused", "is-elbow", "is-region-rail", "is-highlight-rail");
            }
          });
          return;
        }
        if (highlightLinkMode) {
          const compactPath = (points = []) => {
            const result = [];
            points.forEach((point) => {
              const cleanPoint = {
                x: Number(point && point.x) || 0,
                y: Number(point && point.y) || 0,
              };
              const last = result[result.length - 1];
              const prev = result[result.length - 2];
              if (last && Math.abs(last.x - cleanPoint.x) <= 0.5 && Math.abs(last.y - cleanPoint.y) <= 0.5) {
                return;
              }
              if (prev && last) {
                const sameX = Math.abs(prev.x - last.x) <= 0.5 && Math.abs(last.x - cleanPoint.x) <= 0.5;
                const sameY = Math.abs(prev.y - last.y) <= 0.5 && Math.abs(last.y - cleanPoint.y) <= 0.5;
                if (sameX || sameY) {
                  result[result.length - 1] = cleanPoint;
                  return;
                }
              }
              result.push(cleanPoint);
            });
            return result;
          };
          const cardIsRight = cardLeft >= sourceRight + 30;
          const rightLaneX = cardIsRight
            ? Math.max(sourceRight + 34, Math.min(cardLeft - 26, sourceRight + Math.max(58, (cardLeft - sourceRight) * 0.46)))
            : Math.max(rootRight + 24, sourceRight + 34);
          const upperLaneY = Math.max(18, Math.min(
            Math.min(sourceTop - 24, end.y),
            Math.max(rootTop + 18, Math.min(sourceCenterY - 36, rootTop + rootHeight * 0.28)),
          ));
          const lowerLaneY = Math.min(shellHeight - 18, Math.max(
            Math.max(sourceBottom + 24, end.y),
            Math.min(rootBottom - 18, Math.max(sourceCenterY + 36, rootTop + rootHeight * 0.72)),
          ));
          const useUpperLane = end.y <= sourceCenterY || sourceCenterY > rootTop + rootHeight * 0.48;
          const laneY = cardIsRight ? end.y : (useUpperLane ? upperLaneY : lowerLaneY);
          starts.forEach((start, index) => {
            const connector = ensureQuestionRootInfoConnectorAt(index);
            if (!connector) {
              return;
            }
            connector.classList.add("is-live");
            connector.classList.add("is-focused");
            connector.classList.add("is-elbow");
            connector.classList.add("is-region-rail");
            connector.classList.add("is-highlight-rail");
            const safeStart = {
              x: Math.min(rootRight + 10, Math.max(Number(start && start.x) || sourceRight + 8, sourceRight + 8)),
              y: Number(start && start.y) || sourceCenterY,
            };
            const localLaneY = cardIsRight
              ? end.y
              : (useUpperLane
                ? Math.min(laneY - index * 10, safeStart.y - 20)
                : Math.max(laneY + index * 10, safeStart.y + 20));
            const path = compactPath([
              ...routeHighlightAroundDecorations(safeStart, rightLaneX, localLaneY, end, {
                index,
                endOffsetX: cardIsRight ? 18 : 0,
              }),
            ]);
            const segments = ensureQuestionRegionConnectorSegments(connector, Math.max(1, path.length - 1));
            segments.forEach((segment, segmentIndex) => {
              positionQuestionRootInfoSegment(segment, path[segmentIndex], path[segmentIndex + 1]);
            });
          });
        } else {
          starts.forEach((start, index) => {
            const connector = ensureQuestionRootInfoConnectorAt(index);
            if (!connector) {
              return;
            }
            ensureQuestionRootInfoConnectorBaseSegments(connector);
            connector.classList.add("is-live");
            connector.classList.add("is-focused");
            connector.classList.add("is-elbow");
            connector.classList.remove("is-region-rail");
            connector.classList.remove("is-highlight-rail");
            const direction = end.x >= start.x ? 1 : -1;
            const run = Math.max(58, Math.min(190, Math.abs(end.x - start.x) * 0.55));
            const bend = { x: start.x + direction * run, y: end.y };
            const diagonal = connector.querySelector(".ft-q-root-info-connector-segment.is-diagonal");
            const horizontal = connector.querySelector(".ft-q-root-info-connector-segment.is-horizontal");
            positionQuestionRootInfoSegment(diagonal, start, bend);
            positionQuestionRootInfoSegment(horizontal, bend, end);
          });
        }
        questionRootInfoExtraConnectors.forEach((connector, index) => {
          if (index >= starts.length - 1) {
            connector.classList.remove("is-live", "is-focused", "is-elbow", "is-region-rail", "is-highlight-rail");
          }
        });
      };

      const prepareQuestionRootInfo = (sourceNode, forcedPayload = null) => {
        const card = ensureQuestionRootInfoLayer();
        const payload = forcedPayload && typeof forcedPayload === "object" ? forcedPayload : null;
        const isQuestion = Boolean(payload && payload.text);
        const anchorSource = isQuestion && (payload.anchor === "picture" || payload.anchor === "picture_regions") ? questionRootPictureAnchorNode() : sourceNode;
        if (!card || !anchorSource) {
          return false;
        }
        questionRootInfoActiveAnchor = anchorSource;
        questionRootInfoActivePayload = payload;
        const title = card.querySelector(".ft-q-root-info-title");
        if (title) {
          title.textContent = isQuestion
            ? "Linking Question"
            : "Root Signal";
        }
        const body = card.querySelector(".ft-q-root-info-body");
        if (body) {
          body.style.removeProperty("min-height");
          body.textContent = isQuestion
            ? preserveQuestionText(payload.text)
            : preserveQuestionText(sourceNode.getAttribute("data-qh-info") || sourceNode.textContent || "");
          const stableHeight = Math.ceil(body.getBoundingClientRect().height || 0);
          if (stableHeight > 0) {
            body.style.minHeight = `${stableHeight}px`;
          }
        }
        card.classList.toggle("is-question", isQuestion);
        card.classList.toggle("is-picture-region-question", Boolean(isQuestion && payload && payload.anchor === "picture_regions"));
        card.classList.add("is-preparing");
        card.classList.remove("is-live");
        const regionMode = Boolean(isQuestion && payload && payload.anchor === "picture_regions");
        if (regionMode) {
          applyQuestionPictureRegionColor(questionCurrentNode, payload);
        }
        const regionStarts = regionMode
          ? questionPictureRegionAnchorPoints(payload.regions || [])
          : [];
        if (!regionStarts.length && (!payload || payload.anchor !== "picture_regions") && !questionPictureRegionPromptLocked) {
          hideQuestionPictureRegions();
        }
        positionQuestionRootInfo(anchorSource, { isQuestion, placement: payload && payload.placement, regionStarts, regionMode, payload });
        hideQuestionRootInfoConnectors();
        return true;
      };

      const showQuestionRootInfo = (sourceNode, forcedPayload = null) => {
        const card = ensureQuestionRootInfoLayer();
        const payload = forcedPayload && typeof forcedPayload === "object" ? forcedPayload : null;
        const isQuestion = Boolean(payload && payload.text);
        const anchorSource = isQuestion && (payload.anchor === "picture" || payload.anchor === "picture_regions") ? questionRootPictureAnchorNode() : sourceNode;
        if (!card || !anchorSource) {
          return;
        }
        questionRootInfoActiveAnchor = anchorSource;
        questionRootInfoActivePayload = payload;
        const title = card.querySelector(".ft-q-root-info-title");
        if (title) {
          title.textContent = isQuestion
            ? "Linking Question"
            : "Root Signal";
        }
        const text = isQuestion
          ? payload.text
          : (sourceNode.getAttribute("data-qh-info") || sourceNode.textContent || "");
        card.classList.toggle("is-question", isQuestion);
        card.classList.toggle("is-picture-region-question", Boolean(isQuestion && payload && payload.anchor === "picture_regions"));
        card.classList.remove("is-preparing");
        card.classList.add("is-live");
        if (questionRootInfoConnector) {
          questionRootInfoConnector.classList.add("is-live");
          questionRootInfoConnector.classList.add("is-focused");
        }
        typeQuestionRootInfoText(text);
        window.requestAnimationFrame(() => {
          const regionMode = Boolean(isQuestion && payload && payload.anchor === "picture_regions");
          if (regionMode) {
            applyQuestionPictureRegionColor(questionCurrentNode, payload);
          }
          const regionStarts = regionMode
            ? questionPictureRegionAnchorPoints(payload.regions || [])
            : [];
          if (!regionStarts.length && (!payload || payload.anchor !== "picture_regions") && !questionPictureRegionPromptLocked) {
            hideQuestionPictureRegions();
          }
          positionQuestionRootInfo(anchorSource, { isQuestion, placement: payload && payload.placement, regionStarts, regionMode, payload });
          scheduleQuestionSideLayout();
        });
      };

      const repositionActiveQuestionRootInfo = () => {
        if (
          !questionRootInfoCard
          || !(questionRootInfoCard.classList.contains("is-live") || questionRootInfoCard.classList.contains("is-preparing"))
          || !questionRootInfoActiveAnchor
        ) {
          return;
        }
        const payload = questionRootInfoActivePayload && typeof questionRootInfoActivePayload === "object" ? questionRootInfoActivePayload : null;
        const isQuestion = Boolean(payload && payload.text);
        const anchorSource = isQuestion && (payload.anchor === "picture" || payload.anchor === "picture_regions")
          ? questionRootPictureAnchorNode()
          : questionRootInfoActiveAnchor;
        const regionMode = Boolean(isQuestion && payload.anchor === "picture_regions");
        if (regionMode) {
          applyQuestionPictureRegionColor(questionCurrentNode, payload);
        }
        const regionStarts = regionMode
          ? questionPictureRegionAnchorPoints(payload.regions || [])
          : [];
        positionQuestionRootInfo(anchorSource, { isQuestion, placement: payload && payload.placement, regionStarts, regionMode, payload });
      };

      const attachQuestionRootHighlightEvents = () => {
        if (!qRootText) {
          return;
        }
        const suppressRootSignalForSelectMobile = questionRootHoverSignalIsSelectMobileHidden();
        qRootText.querySelectorAll(".ft-q-select-root-token").forEach((node) => {
          node.addEventListener("pointerdown", (event) => {
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
              event.stopImmediatePropagation();
            }
          }, true);
          node.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === "function") {
              event.stopImmediatePropagation();
            }
            handleQuestionSelectRootTokenClick(node);
          }, true);
          if (!suppressRootSignalForSelectMobile) {
            node.addEventListener("mouseenter", (event) => {
              showQuestionRootHoverInfo(node, event);
            });
            node.addEventListener("mousemove", (event) => {
              positionQuestionRootHoverInfo(node, event);
            });
            node.addEventListener("mouseleave", () => {
              hideQuestionRootHoverInfo();
            });
          }
        });
        qRootText.querySelectorAll(".ft-q-root-highlight").forEach((node) => {
          if (node.classList.contains("is-select-target")) {
            if (!suppressRootSignalForSelectMobile) {
              node.addEventListener("mouseenter", (event) => {
                showQuestionRootHoverInfo(node, event);
              });
              node.addEventListener("mousemove", (event) => {
                positionQuestionRootHoverInfo(node, event);
              });
              node.addEventListener("mouseleave", () => {
                hideQuestionRootHoverInfo();
              });
            }
            node.addEventListener("pointerdown", (event) => {
              if (event.target && event.target.closest && event.target.closest(".ft-q-select-root-token")) {
                return;
              }
              event.preventDefault();
              event.stopPropagation();
              if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
              }
            }, true);
            node.addEventListener("click", (event) => {
              if (event.target && event.target.closest && event.target.closest(".ft-q-select-root-token")) {
                return;
              }
              event.preventDefault();
              event.stopPropagation();
              if (typeof event.stopImmediatePropagation === "function") {
                event.stopImmediatePropagation();
              }
              handleQuestionSelectRootRangeClick(node);
            }, true);
            return;
          }
          if (suppressRootSignalForSelectMobile) {
            return;
          }
          node.addEventListener("mouseenter", (event) => {
            showQuestionRootHoverInfo(node, event);
          });
          node.addEventListener("mousemove", (event) => {
            positionQuestionRootHoverInfo(node, event);
          });
          node.addEventListener("mouseleave", () => {
            hideQuestionRootHoverInfo();
          });
          node.addEventListener("click", (event) => {
            if (event.target && event.target.closest && event.target.closest(".ft-q-select-root-token")) {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            showQuestionRootHoverInfo(node, event);
          });
        });
      };

      const isQuestionMobileLandscapeFlow = () => window.matchMedia("(pointer: coarse) and (orientation: landscape) and (max-height: 760px)").matches;
      const isQuestionMobileFlow = () => window.matchMedia("(max-width: 900px), (pointer: coarse) and (max-height: 760px)").matches;
      const questionPanelLive = (node) => Boolean(node && (node.classList.contains("is-live") || node.classList.contains("is-preparing") || node.classList.contains("is-hiding")));
      const questionMobilePanelAvailable = (panel = "root") => {
        const key = clean(panel || "root").toLowerCase();
        if (!questionModeActive || !isQuestionMobileFlow()) {
          return false;
        }
        if (key === "root") {
          return Boolean(qRootCard && !qRootCard.classList.contains("is-hidden"));
        }
        if (key === "audio") {
          return questionPanelLive(qAudioCard);
        }
        if (key === "picture") {
          return questionPanelLive(qPictureCard);
        }
        if (key === "question") {
          return questionPanelLive(qQuestionCard)
            || Boolean(questionRootInfoCard && questionRootInfoCard.classList.contains("is-question") && questionPanelLive(questionRootInfoCard));
        }
        if (key === "info") {
          return questionPanelLive(qInfoCard);
        }
        return false;
      };

      const questionMobileAvailablePanels = () => ["root", "audio", "picture", "question", "info"].filter(questionMobilePanelAvailable);
      const questionMobilePanelForNode = (node) => {
        if (!node || !node.classList) {
          return "";
        }
        if (node === qAudioCard || node.classList.contains("ft-q-audio-card")) return "audio";
        if (node === qPictureCard || node.classList.contains("ft-q-picture-card")) return "picture";
        if (
          node === qQuestionCard
          || node === questionRootInfoCard
          || node.classList.contains("ft-q-question-card")
          || node.classList.contains("ft-q-root-info-card")
          || node.classList.contains("ft-q-picture-answer-card")
          || node.classList.contains("ft-q-picture-answer-layer")
        ) return "question";
        if (node === qInfoCard || node.classList.contains("ft-q-info-card")) return "info";
        if (node === qRootCard || node.classList.contains("ft-q-root-card")) return "root";
        return "";
      };

      const setQuestionMobilePanel = (panel = "root", options = {}) => {
        if (!stageNode) {
          return;
        }
        let key = clean(panel || "root").toLowerCase();
        if (!["root", "audio", "picture", "question", "info"].includes(key)) {
          key = "root";
        }
        if (isQuestionMobileFlow() && !questionMobilePanelAvailable(key)) {
          const available = questionMobileAvailablePanels();
          key = available[available.length - 1] || "root";
        }
        questionMobileActivePanel = key;
        stageNode.dataset.qMobilePanel = key;
        ["root", "audio", "picture", "question", "info"].forEach((name) => {
          stageNode.classList.toggle(`is-q-mobile-panel-${name}`, key === name);
        });
        qMobileTabButtons.forEach((button) => {
          const buttonKey = button.dataset.qPanel || "";
          const available = questionMobilePanelAvailable(buttonKey);
          button.hidden = !available;
          const active = buttonKey === key && available;
          const attention = Boolean(
            available
            && !active
            && buttonKey === "info"
            && questionPanelLive(qInfoCard)
          );
          button.classList.toggle("is-active", active);
          button.classList.toggle("is-attention", attention);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        if (!options.skipFocus && isQuestionMobileFlow()) {
          const target = key === "root"
            ? qRootCard
            : (key === "audio"
              ? qAudioCard
              : (key === "picture"
                ? qPictureCard
                : (key === "info"
                  ? qInfoCard
                  : (questionRootInfoCard && questionRootInfoCard.classList.contains("is-question") && questionPanelLive(questionRootInfoCard)
                    ? questionRootInfoCard
                    : qQuestionCard))));
          if (target && target.focus && key !== "root") {
            try {
              target.focus({ preventScroll: true });
            } catch (error) {
            }
          }
        }
      };

      const syncQuestionMobilePanels = (preferredPanel = "") => {
        if (!stageNode) {
          return;
        }
        questionMobilePanelSyncFrame = 0;
        if (!questionModeActive || !isQuestionMobileFlow()) {
          stageNode.classList.remove("is-q-mobile-panel-root", "is-q-mobile-panel-audio", "is-q-mobile-panel-picture", "is-q-mobile-panel-question", "is-q-mobile-panel-info");
          qMobileTabButtons.forEach((button) => {
            button.hidden = true;
            button.classList.remove("is-active");
            button.classList.remove("is-attention");
            button.setAttribute("aria-pressed", "false");
          });
          return;
        }
        if (preferredPanel && questionMobilePanelAvailable(preferredPanel)) {
          setQuestionMobilePanel(preferredPanel, { skipFocus: true });
          return;
        }
        if (!questionMobilePanelAvailable(questionMobileActivePanel)) {
          const available = questionMobileAvailablePanels();
          setQuestionMobilePanel(available[available.length - 1] || "root", { skipFocus: true });
          return;
        }
        setQuestionMobilePanel(questionMobileActivePanel, { skipFocus: true });
      };

      const scheduleQuestionMobilePanelsSync = (preferredPanel = "") => {
        if (!qMobileTabs || !window.requestAnimationFrame) {
          syncQuestionMobilePanels(preferredPanel);
          return;
        }
        if (preferredPanel && questionMobilePanelAvailable(preferredPanel)) {
          questionMobileActivePanel = preferredPanel;
        }
        if (questionMobilePanelSyncFrame) {
          return;
        }
        questionMobilePanelSyncFrame = window.requestAnimationFrame(() => syncQuestionMobilePanels(preferredPanel));
      };

      function clearQuestionInputAutoFocusTimers() {
        questionInputAutoFocusTimers.forEach((timer) => window.clearTimeout(timer));
        questionInputAutoFocusTimers.clear();
      }

      function focusQuestionTypingInput(input, options = {}) {
        if (!input || !input.focus) {
          return false;
        }
        const item = options.item || null;
        const pictureInput = Boolean(options.pictureInput);
        const delays = Array.isArray(options.delays) && options.delays.length
          ? options.delays
          : [0, 70, 180, 360];
        clearQuestionInputAutoFocusTimers();
        const tryFocus = () => {
          if (!questionModeActive || !input || !input.isConnected || input.disabled) {
            return false;
          }
          if (item && (questionCurrentQuestions[questionQuestionIndex] || null) !== item) {
            return false;
          }
          if (isQuestionMobileFlow()) {
            if (pictureInput) {
              setQuestionMobilePicturePage("answers");
            }
            syncQuestionMobilePanels("question");
          }
          try {
            input.focus({ preventScroll: true });
          } catch (error) {
            try {
              input.focus();
            } catch (_) {
            }
          }
          try {
            const length = typeof input.value === "string" ? input.value.length : 0;
            if (typeof input.setSelectionRange === "function") {
              input.setSelectionRange(length, length);
            }
          } catch (_) {
          }
          const hostCard = input.closest ? input.closest(".ft-q-question-card, .ft-q-picture-answer-card") : null;
          if (hostCard && hostCard.classList && hostCard.classList.contains("ft-q-question-card")) {
            activateQuestionCardFx(hostCard, 1200);
          }
          return document.activeElement === input;
        };
        tryFocus();
        delays.forEach((delay) => {
          const wait = Math.max(0, Number(delay) || 0);
          if (wait <= 0) {
            window.requestAnimationFrame(tryFocus);
            return;
          }
          const timer = window.setTimeout(() => {
            questionInputAutoFocusTimers.delete(timer);
            window.requestAnimationFrame(tryFocus);
          }, wait);
          questionInputAutoFocusTimers.add(timer);
        });
        return true;
      }

      const installQuestionMobilePanelObserver = () => {
        if (!window.MutationObserver || !shellNode || questionMobilePanelObserver) {
          return;
        }
        questionMobilePanelObserver = new MutationObserver((mutations) => {
          if (mutations.every((mutation) => mutation.target && mutation.target.closest && mutation.target.closest(".ft-q-mobile-tabs"))) {
            return;
          }
          scheduleQuestionMobilePanelsSync("");
        });
        [qRootCard, qAudioCard, qPictureCard, qQuestionCard, qInfoCard, shellNode].filter(Boolean).forEach((node) => {
          questionMobilePanelObserver.observe(node, {
            attributes: true,
            attributeFilter: ["class"],
            childList: node === shellNode,
            subtree: node === shellNode,
          });
        });
      };

      const QUESTION_RESPONSIVE_BASE_WIDTH = 1680;
      const QUESTION_RESPONSIVE_BASE_HEIGHT = 900;
      const QUESTION_RESPONSIVE_MIN_SCALE = 0.72;
      const QUESTION_RESPONSIVE_LANDSCAPE_MIN_SCALE = 0.56;
      const QUESTION_CARD_TOP_SAFE_INSET_PX = 76;

      const questionViewportSize = () => {
        const visualViewport = window.visualViewport || null;
        const width = stageNode && stageNode.clientWidth
          ? stageNode.clientWidth
          : (visualViewport && visualViewport.width) || window.innerWidth || 0;
        const height = stageNode && stageNode.clientHeight
          ? stageNode.clientHeight
          : (visualViewport && visualViewport.height) || window.innerHeight || 0;
        return {
          width: Math.max(0, Number(width) || 0),
          height: Math.max(0, Number(height) || 0),
        };
      };

      const computeQuestionResponsiveScale = () => {
        if (!stageNode || !stageNode.classList.contains("is-question-mode") || isQuestionMobileFlow()) {
          return 1;
        }
        const viewport = questionViewportSize();
        if (!viewport.width || !viewport.height) {
          return 1;
        }
        const scale = Math.min(
          1,
          viewport.width / QUESTION_RESPONSIVE_BASE_WIDTH,
          viewport.height / QUESTION_RESPONSIVE_BASE_HEIGHT,
        );
        return Math.max(isQuestionMobileLandscapeFlow() ? QUESTION_RESPONSIVE_LANDSCAPE_MIN_SCALE : QUESTION_RESPONSIVE_MIN_SCALE, scale);
      };

      const applyQuestionResponsiveScale = (force = false) => {
        const viewport = questionViewportSize();
        const scale = Math.round(computeQuestionResponsiveScale() * 1000) / 1000;
        const landscape = isQuestionMobileLandscapeFlow();
        if (stageNode) {
          const layoutHeight = viewport.height ? viewport.height / Math.max(0.1, scale) : 0;
          if (layoutHeight) {
            stageNode.style.setProperty("--q-question-layout-vh", `${layoutHeight.toFixed(2)}px`);
            if (landscape) {
              stageNode.style.setProperty("--q-question-top-padding", `${Math.max(28, layoutHeight * 0.06).toFixed(2)}px`);
            } else {
              stageNode.style.removeProperty("--q-question-top-padding");
            }
            stageNode.style.setProperty(
              "--q-question-bottom-padding",
              `${(layoutHeight * (landscape ? 0.28 : (isQuestionVisualProfileActive() ? 0.56 : 0.48))).toFixed(2)}px`,
            );
          }
          stageNode.classList.toggle("is-question-mobile-landscape", landscape);
        }
        if (!force && Math.abs(scale - questionResponsiveScale) < 0.008) {
          return questionResponsiveScale;
        }
        questionResponsiveScale = scale;
        if (stageNode) {
          stageNode.style.setProperty("--q-question-ui-scale", scale.toFixed(3));
          stageNode.classList.toggle("is-question-responsive-scaled", scale < 0.995);
        }
        return questionResponsiveScale;
      };

      const clearQuestionResponsiveScale = () => {
        questionResponsiveScale = 1;
        if (stageNode) {
          stageNode.style.removeProperty("--q-question-ui-scale");
          stageNode.style.removeProperty("--q-question-layout-vh");
          stageNode.style.removeProperty("--q-question-top-padding");
          stageNode.style.removeProperty("--q-question-bottom-padding");
          stageNode.classList.remove("is-question-responsive-scaled", "is-question-mobile-landscape");
        }
      };

      const questionResponsiveLayoutScale = () => Math.max(0.1, questionResponsiveScale || 1);

      const questionUnscaleLayoutValue = (value) => (Number(value) || 0) / questionResponsiveLayoutScale();

      const questionSplitDesktopLayoutActive = () => Boolean(
        questionModeActive
        && stageNode
        && shellNode
        && !isQuestionMobileFlow()
      );

      const questionCurrentNodeHasAudioCard = () => {
        const audio = questionCardData(questionCurrentNode, "audio");
        return Boolean(audio && audio.url);
      };

      const questionSplitLayoutMetrics = () => {
        if (!stageNode) {
          return null;
        }
        const stageWidth = questionUnscaleLayoutValue(stageNode.clientWidth || window.innerWidth || 1180);
        if (!stageWidth || stageWidth < 720) {
          return null;
        }
        const sidePad = Math.max(22, Math.min(54, stageWidth * 0.028));
        const gap = Math.max(24, Math.min(56, stageWidth * 0.034));
        const columnWidth = Math.max(320, Math.floor((stageWidth - sidePad * 2 - gap) / 2));
        const audioInSplitLane = Boolean(qAudioCard && (
          qAudioCard.classList.contains("is-live")
          || qAudioCard.classList.contains("is-preparing")
          || questionCurrentNodeHasAudioCard()
        ));
        const audioWidth = audioInSplitLane
          ? Math.max(280, Math.min(360, columnWidth * 0.72))
          : 0;
        const audioLeft = audioInSplitLane
          ? Math.max(sidePad, Math.round(stageWidth * 0.5 - audioWidth * 0.5))
          : sidePad;
        const rootLeft = audioInSplitLane
          ? audioLeft + audioWidth + gap
          : sidePad;
        const rightLeft = rootLeft + columnWidth + gap;
        const shellWidth = Math.max(stageWidth, rightLeft + columnWidth + sidePad);
        return {
          shellWidth: Math.ceil(shellWidth),
          left: rootLeft,
          gap,
          rootWidth: columnWidth,
          audioLeft,
          audioWidth,
          rightLeft,
          rightWidth: columnWidth,
        };
      };

      function questionRootTypingTopPadding(layoutViewportHeight = 0, profileActive = false, rootHeight = 0) {
        const viewportHeight = Math.max(1, Number(layoutViewportHeight) || 0);
        const measuredRootHeight = Math.max(0, Number(rootHeight) || 0);
        const safeTop = Math.max(0, questionUnscaleLayoutValue(QUESTION_ROOT_TOP_SCREEN_GAP));
        if (!measuredRootHeight || measuredRootHeight >= viewportHeight * 0.68) {
          return safeTop;
        }
        const centeredTop = (viewportHeight - measuredRootHeight) / 2;
        return Math.max(safeTop, centeredTop);
      }

      function questionCurrentRootTopPadding() {
        if (!shellNode || !qRootCard) {
          return null;
        }
        const shellStyle = getComputedStyle(shellNode);
        const shellPaddingTop = Number.parseFloat(shellStyle.paddingTop);
        if (Number.isFinite(shellPaddingTop) && shellPaddingTop >= 0) {
          return shellPaddingTop;
        }
        if (qRootCard.offsetParent === shellNode && Number.isFinite(qRootCard.offsetTop)) {
          return Math.max(0, qRootCard.offsetTop);
        }
        const shellRect = shellNode.getBoundingClientRect();
        const rootRect = qRootCard.getBoundingClientRect();
        if (!shellRect.height || !rootRect.height) {
          return null;
        }
        return Math.max(0, questionUnscaleLayoutValue(rootRect.top - shellRect.top));
      }

      function questionRootReserveHighlightRanges(node, rootText = "") {
        const source = preserveQuestionText(rootText);
        const ranges = [];
        const pushRanges = (highlights, promptText = "") => {
          questionRootHighlightRanges(source, highlights, promptText).forEach((range) => {
            ranges.push({ ...range, sourceIndex: ranges.length });
          });
        };
        if (node && typeof node === "object") {
          pushRanges(node.root_highlights ?? node.rootHighlights ?? node.highlights ?? node.rh, "");
        }
        const questions = questionCardData(node, "questions");
        (Array.isArray(questions) ? questions : []).forEach((item) => {
          if (!item || typeof item !== "object") {
            return;
          }
          pushRanges(item.root_highlights ?? item.rootHighlights ?? item.highlights ?? item.rh, item.question);
        });
        return ranges;
      }

      function measureQuestionRootReservedHeight(text, node = questionCurrentNode) {
        if (!qRootCard || !qRootText) {
          return null;
        }
        const source = preserveQuestionText(text);
        if (!source) {
          return null;
        }
        const previousHtml = qRootText.innerHTML;
        const previousClass = qRootText.getAttribute("class");
        const previousReserve = qRootCard.style.getPropertyValue("--q-root-reserved-height");
        qRootCard.style.removeProperty("--q-root-reserved-height");
        qRootText.innerHTML = renderQuestionRootMarkup(source, [], {
          ranges: questionRootReserveHighlightRanges(node, source),
        });
        const textViewportHeight = qRootText.clientHeight || 0;
        const textFullHeight = qRootText.scrollHeight || textViewportHeight;
        const cardHeight = qRootCard.offsetHeight || questionUnscaleLayoutValue(qRootCard.getBoundingClientRect().height) || 0;
        const cardChrome = Math.max(0, cardHeight - textViewportHeight);
        const measured = Math.ceil(Math.max(cardHeight, textFullHeight + cardChrome));
        qRootText.innerHTML = previousHtml;
        if (previousClass === null) {
          qRootText.removeAttribute("class");
        } else {
          qRootText.setAttribute("class", previousClass);
        }
        if (previousReserve) {
          qRootCard.style.setProperty("--q-root-reserved-height", previousReserve);
        } else {
          qRootCard.style.removeProperty("--q-root-reserved-height");
        }
        return measured > 0 ? measured : null;
      }

      const isQuestionCardInLayout = (node) => Boolean(node && (
        node.classList.contains("is-live") || node.classList.contains("is-preparing")
      ));

      const questionCameraNodes = () => [
        qRootCard,
        qPictureCard,
        qAudioCard,
        qQuestionCard,
        qInfoCard,
        questionRootInfoCard,
        ...(questionPictureAnswerLayer ? Array.from(questionPictureAnswerLayer.querySelectorAll(".ft-q-picture-answer-card.is-live, .ft-q-picture-answer-card.is-preparing")) : []),
      ].filter((node) => {
        if (!node || node.classList.contains("is-hidden")) {
          return false;
        }
        if (node.classList.contains("ft-q-picture-answer-card")) {
          return true;
        }
        return node === qRootCard || isQuestionCardInLayout(node);
      });

      const questionGeometryBounds = (nodes = []) => {
        const rects = nodes
          .map((node) => node.getBoundingClientRect())
          .filter((rect) => rect.width > 0 && rect.height > 0);
        if (!rects.length) {
          return null;
        }
        return rects.reduce((bounds, rect) => ({
          left: Math.min(bounds.left, rect.left),
          top: Math.min(bounds.top, rect.top),
          right: Math.max(bounds.right, rect.right),
          bottom: Math.max(bounds.bottom, rect.bottom),
        }), {
          left: rects[0].left,
          top: rects[0].top,
          right: rects[0].right,
          bottom: rects[0].bottom,
        });
      };

      const clearQuestionManualFocusTimer = () => {
        if (questionManualFocusTimer) {
          window.clearTimeout(questionManualFocusTimer);
          questionManualFocusTimer = 0;
        }
        questionFocusPointerState = null;
        questionManualFocusTarget = null;
      };

      const questionCameraEaseInOut = (value) => {
        const t = Math.max(0, Math.min(1, Number(value) || 0));
        return t < 0.5
          ? 4 * t * t * t
          : 1 - Math.pow(-2 * t + 2, 3) / 2;
      };

      const stopQuestionCameraScrollAnimation = () => {
        questionCameraScrollToken += 1;
        if (questionCameraScrollFrame) {
          window.cancelAnimationFrame(questionCameraScrollFrame);
          questionCameraScrollFrame = 0;
        }
      };

      const animateQuestionStageScrollTo = (top, left, duration = QUESTION_CAMERA_PAN_SETTLE_MS) => {
        if (!stageNode) {
          return false;
        }
        stopQuestionCameraScrollAnimation();
        const startTop = stageNode.scrollTop;
        const startLeft = stageNode.scrollLeft;
        const targetTop = Math.max(0, Number(top) || 0);
        const targetLeft = Math.max(0, Number(left) || 0);
        const deltaTop = targetTop - startTop;
        const deltaLeft = targetLeft - startLeft;
        const safeDuration = Math.max(180, Number(duration) || QUESTION_CAMERA_PAN_SETTLE_MS);
        if (Math.abs(deltaTop) < 1 && Math.abs(deltaLeft) < 1) {
          stageNode.scrollTop = targetTop;
          stageNode.scrollLeft = targetLeft;
          return true;
        }
        const token = questionCameraScrollToken;
        const startedAt = performance.now();
        const step = (now) => {
          if (token !== questionCameraScrollToken || !stageNode) {
            return;
          }
          const progress = Math.min(1, (now - startedAt) / safeDuration);
          const eased = questionCameraEaseInOut(progress);
          stageNode.scrollTop = startTop + deltaTop * eased;
          stageNode.scrollLeft = startLeft + deltaLeft * eased;
          if (progress < 1) {
            questionCameraScrollFrame = window.requestAnimationFrame(step);
          } else {
            stageNode.scrollTop = targetTop;
            stageNode.scrollLeft = targetLeft;
            questionCameraScrollFrame = 0;
          }
        };
        questionCameraScrollFrame = window.requestAnimationFrame(step);
        return true;
      };

      function centerQuestionRootHorizontalOrigin(options = {}) {
        if (!stageNode || !qRootCard || qRootCard.classList.contains("is-hidden") || isQuestionMobileFlow()) {
          return false;
        }
        if (questionSplitDesktopLayoutActive()) {
          const rootRect = qRootCard.getBoundingClientRect();
          const stageRect = stageNode.getBoundingClientRect();
          if (!rootRect.width || !stageRect.width) {
            return false;
          }
          const viewportCenterX = stageRect.left + stageNode.clientWidth / 2;
          const rootCenterX = rootRect.left + rootRect.width / 2;
          const maxScrollLeft = Math.max(0, stageNode.scrollWidth - stageNode.clientWidth);
          const nextScrollLeft = Math.max(0, Math.min(maxScrollLeft, stageNode.scrollLeft + rootCenterX - viewportCenterX));
          if (Math.abs(nextScrollLeft - stageNode.scrollLeft) < 1) {
            return false;
          }
          if ((options.behavior || "auto") === "smooth") {
            return animateQuestionStageScrollTo(stageNode.scrollTop, nextScrollLeft, options.duration || 520);
          }
          stopQuestionCameraScrollAnimation();
          stageNode.scrollLeft = nextScrollLeft;
          return true;
        }
        const rootRect = qRootCard.getBoundingClientRect();
        const stageRect = stageNode.getBoundingClientRect();
        if (!rootRect.width || !stageRect.width) {
          return false;
        }
        const viewportCenterX = stageRect.left + stageNode.clientWidth / 2;
        const rootCenterX = rootRect.left + rootRect.width / 2;
        const maxScrollLeft = Math.max(0, stageNode.scrollWidth - stageNode.clientWidth);
        const nextScrollLeft = Math.max(0, Math.min(maxScrollLeft, stageNode.scrollLeft + rootCenterX - viewportCenterX));
        if (Math.abs(nextScrollLeft - stageNode.scrollLeft) < 1) {
          return false;
        }
        if ((options.behavior || "auto") === "smooth") {
          return animateQuestionStageScrollTo(stageNode.scrollTop, nextScrollLeft, options.duration || 520);
        }
        stopQuestionCameraScrollAnimation();
        stageNode.scrollLeft = nextScrollLeft;
        return true;
      }

      const spaceNavigatorLearningActive = () => {
        const authOpen = Boolean(authGate && !authGate.classList.contains("is-hidden"));
        const loadOpen = Boolean(loadGate && !loadGate.classList.contains("is-hidden"));
        const fullscreenGateOpen = Boolean(startFullscreenGate && !startFullscreenGate.classList.contains("is-hidden"));
        const vocabGateOpen = Boolean(vocabPreflightGate && !vocabPreflightGate.hidden);
        if (authOpen || loadOpen || fullscreenGateOpen || vocabGateOpen) {
          return false;
        }
        const cardVisible = Boolean(cardNode && !cardNode.classList.contains("is-hidden"));
        const vocabVisible = Boolean(vocabModeActive || (vocabCard && !vocabCard.classList.contains("is-hidden")));
        const questionVisible = Boolean(questionModeActive || (stageNode && stageNode.classList.contains("is-question-mode")));
        return Boolean(cardVisible || vocabVisible || questionVisible);
      };

      const spaceNavigatorScrollTarget = () => {
        if (stageNode && stageNode.classList.contains("is-question-mode")) {
          return stageNode;
        }
        if (stageNode && (stageNode.scrollWidth > stageNode.clientWidth + 2 || stageNode.scrollHeight > stageNode.clientHeight + 2)) {
          return stageNode;
        }
        return document.scrollingElement || document.documentElement;
      };

      const SPACE_NAVIGATOR_REVEAL_RADIUS = 50;

      const setSpaceNavigatorNearPointer = (near) => {
        spaceNavigatorNearPointer = Boolean(near);
        if (spaceNavigatorNode) {
          spaceNavigatorNode.classList.toggle("is-near", spaceNavigatorNearPointer);
        }
      };

      const updateSpaceNavigatorVisibility = () => {
        if (!spaceNavigatorNode) {
          return;
        }
        const live = spaceNavigatorLearningActive();
        spaceNavigatorNode.classList.toggle("is-live", live);
        if (!live) {
          setSpaceNavigatorNearPointer(false);
        }
      };

      const updateSpaceNavigatorNearPointer = (event) => {
        if (!spaceNavigatorNode || !spaceNavigatorLearningActive()) {
          setSpaceNavigatorNearPointer(false);
          return;
        }
        if (event && event.pointerType && event.pointerType !== "mouse") {
          setSpaceNavigatorNearPointer(true);
          return;
        }
        const rect = spaceNavigatorNode.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          setSpaceNavigatorNearPointer(false);
          return;
        }
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const distance = Math.hypot((event ? event.clientX : 0) - centerX, (event ? event.clientY : 0) - centerY);
        setSpaceNavigatorNearPointer(distance <= SPACE_NAVIGATOR_REVEAL_RADIUS || spaceNavigatorPointerId || spaceNavigatorNode.classList.contains("is-coasting"));
      };

      const applySpaceNavigatorVisual = (vector = spaceNavigatorVisualVector) => {
        if (!spaceNavigatorNode) {
          return;
        }
        const speed = Math.hypot(spaceNavigatorVelocity.x, spaceNavigatorVelocity.y);
        const rect = spaceNavigatorNode.getBoundingClientRect();
        const radius = Math.max(1, Math.min(rect.width, rect.height) / 2);
        const x = vector.x * radius * 0.72;
        const y = vector.y * radius * 0.72;
        const angle = Math.atan2(vector.y, vector.x) * 180 / Math.PI;
        const visualPower = Math.max(0, Math.min(1, Math.max(vector.power, Math.min(1, speed / 1500) * 0.74)));
        spaceNavigatorNode.style.setProperty("--nav-x", `${x.toFixed(2)}px`);
        spaceNavigatorNode.style.setProperty("--nav-y", `${y.toFixed(2)}px`);
        spaceNavigatorNode.style.setProperty("--nav-power", `${visualPower.toFixed(3)}`);
        spaceNavigatorNode.style.setProperty("--nav-speed", `${Math.min(1, speed / 1500).toFixed(3)}`);
        spaceNavigatorNode.style.setProperty("--nav-conic-angle", `${(35 + Math.min(1, speed / 1500) * 22).toFixed(2)}deg`);
        spaceNavigatorNode.style.setProperty("--nav-vector-width", `${(18 + visualPower * 34).toFixed(2)}px`);
        spaceNavigatorNode.style.setProperty("--nav-vector-opacity", `${(0.28 + visualPower * 0.72).toFixed(3)}`);
        spaceNavigatorNode.style.setProperty("--nav-dot-opacity", `${(0.26 + visualPower * 0.74).toFixed(3)}`);
        spaceNavigatorNode.style.setProperty("--nav-tilt-x", `${(vector.x * 7).toFixed(2)}deg`);
        spaceNavigatorNode.style.setProperty("--nav-tilt-y", `${(-vector.y * 7).toFixed(2)}deg`);
        spaceNavigatorNode.style.setProperty("--nav-angle", `${Number.isFinite(angle) ? angle.toFixed(2) : 0}deg`);
      };

      const spaceNavigatorVectorForEvent = (event) => {
        if (!spaceNavigatorNode) {
          return { x: 0, y: 0, power: 0 };
        }
        const rect = spaceNavigatorNode.getBoundingClientRect();
        const radius = Math.max(1, Math.min(rect.width, rect.height) / 2);
        const rawX = (event.clientX - (rect.left + rect.width / 2)) / radius;
        const rawY = (event.clientY - (rect.top + rect.height / 2)) / radius;
        const length = Math.hypot(rawX, rawY);
        if (length < 0.08) {
          return { x: 0, y: 0, power: 0 };
        }
        const clipped = Math.min(1, length);
        return {
          x: rawX / Math.max(length, 1),
          y: rawY / Math.max(length, 1),
          power: clipped,
        };
      };

      const refreshSpaceNavigatorDependentLayout = () => {
        if (questionModeActive) {
          return;
        }
        if (allPanelConnectors().some((node) => node.classList.contains("is-live"))) {
          positionConnector();
        }
        if (vocabModeActive) {
          positionVocabWeakConnector();
          positionVocabLearnedPanel();
          positionVocabSideCards();
        }
      };

      const scrollBySpaceNavigatorDelta = (deltaLeft, deltaTop) => {
        const target = spaceNavigatorScrollTarget();
        if (!target) {
          return;
        }
        const maxLeft = Math.max(0, target.scrollWidth - target.clientWidth);
        const maxTop = Math.max(0, target.scrollHeight - target.clientHeight);
        const nextLeft = Math.max(0, Math.min(maxLeft, target.scrollLeft + (Number(deltaLeft) || 0)));
        const nextTop = Math.max(0, Math.min(maxTop, target.scrollTop + (Number(deltaTop) || 0)));
        if (Math.abs(nextLeft - target.scrollLeft) < 0.2 && Math.abs(nextTop - target.scrollTop) < 0.2) {
          return;
        }
        target.scrollLeft = nextLeft;
        target.scrollTop = nextTop;
        refreshSpaceNavigatorDependentLayout();
      };

      const SPACE_KEYBOARD_NAV_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]);

      const isSpaceKeyboardTextEntryTarget = (target) => Boolean(
        target
        && target.closest
        && target.closest("input,textarea,select,[contenteditable]:not([contenteditable='false']),[role='textbox'],.ft-chat-modal,.ft-paint-modal,.ft-game-modal,.ft-world-modal,.ft-cup-modal,.ft-cup-reward-modal,.ft-image-viewer,.ft-voice-picker,.ft-load-gate,.ft-auth-gate,.ft-vocab-preflight-gate")
      );

      const spaceKeyboardNavigationAllowed = (event) => {
        if (!event || !SPACE_KEYBOARD_NAV_KEYS.has(event.key) || event.altKey || event.ctrlKey || event.metaKey) {
          return false;
        }
        if (!spaceNavigatorLearningActive()) {
          return false;
        }
        if (isSpaceKeyboardTextEntryTarget(event.target) || isSpaceKeyboardTextEntryTarget(document.activeElement)) {
          return false;
        }
        return true;
      };

      const spaceKeyboardNavigationVector = () => {
        let x = 0;
        let y = 0;
        if (spaceKeyboardNavigatorKeys.has("ArrowLeft")) x -= 1;
        if (spaceKeyboardNavigatorKeys.has("ArrowRight")) x += 1;
        if (spaceKeyboardNavigatorKeys.has("ArrowUp")) y -= 1;
        if (spaceKeyboardNavigatorKeys.has("ArrowDown")) y += 1;
        const length = Math.hypot(x, y);
        return length ? { x: x / length, y: y / length, power: 1 } : { x: 0, y: 0, power: 0 };
      };

      const stopSpaceKeyboardNavigation = () => {
        if (spaceKeyboardNavigatorFrame) {
          window.cancelAnimationFrame(spaceKeyboardNavigatorFrame);
          spaceKeyboardNavigatorFrame = 0;
        }
        spaceKeyboardNavigatorKeys.clear();
        spaceKeyboardNavigatorLastTick = 0;
        spaceKeyboardNavigatorVelocity = { x: 0, y: 0 };
        if (spaceNavigatorNode && !spaceNavigatorPointerId) {
          spaceNavigatorVisualVector = { x: 0, y: 0, power: 0 };
          spaceNavigatorVelocity = { x: 0, y: 0 };
          applySpaceNavigatorVisual();
          spaceNavigatorNode.classList.remove("is-active");
        }
      };

      const stepSpaceKeyboardNavigation = (now) => {
        const direction = spaceKeyboardNavigationVector();
        if (!direction.power) {
          stopSpaceKeyboardNavigation();
          return;
        }
        const last = spaceKeyboardNavigatorLastTick || now;
        const delta = Math.max(0, Math.min(50, now - last));
        spaceKeyboardNavigatorLastTick = now;
        const targetSpeed = stageNode && stageNode.classList.contains("is-question-mode") ? 920 : 760;
        const response = 1 - Math.exp(-delta / 82);
        spaceKeyboardNavigatorVelocity.x += (direction.x * targetSpeed - spaceKeyboardNavigatorVelocity.x) * response;
        spaceKeyboardNavigatorVelocity.y += (direction.y * targetSpeed - spaceKeyboardNavigatorVelocity.y) * response;
        scrollBySpaceNavigatorDelta(
          spaceKeyboardNavigatorVelocity.x * delta / 1000,
          spaceKeyboardNavigatorVelocity.y * delta / 1000,
        );
        if (spaceNavigatorNode) {
          spaceNavigatorNode.classList.add("is-active");
          spaceNavigatorVisualVector = direction;
          spaceNavigatorVelocity = { ...spaceKeyboardNavigatorVelocity };
          applySpaceNavigatorVisual(direction);
        }
        spaceKeyboardNavigatorFrame = window.requestAnimationFrame(stepSpaceKeyboardNavigation);
      };

      const installSpaceKeyboardNavigation = () => {
        window.addEventListener("keydown", (event) => {
          if (!spaceKeyboardNavigationAllowed(event)) {
            return;
          }
          event.preventDefault();
          stopQuestionCameraScrollAnimation();
          clearQuestionManualFocusTimer();
          stopSpaceNavigatorMotion();
          spaceKeyboardNavigatorKeys.add(event.key);
          if (!spaceKeyboardNavigatorFrame) {
            spaceKeyboardNavigatorLastTick = performance.now();
            spaceKeyboardNavigatorFrame = window.requestAnimationFrame(stepSpaceKeyboardNavigation);
          }
        }, true);
        window.addEventListener("keyup", (event) => {
          if (!SPACE_KEYBOARD_NAV_KEYS.has(event.key)) {
            return;
          }
          if (spaceKeyboardNavigatorKeys.has(event.key)) {
            event.preventDefault();
            spaceKeyboardNavigatorKeys.delete(event.key);
            if (!spaceKeyboardNavigatorKeys.size) {
              stopSpaceKeyboardNavigation();
            }
          }
        }, true);
        window.addEventListener("blur", stopSpaceKeyboardNavigation);
      };

      const stopSpaceNavigatorMotion = () => {
        if (spaceNavigatorFrame) {
          window.cancelAnimationFrame(spaceNavigatorFrame);
          spaceNavigatorFrame = 0;
        }
        spaceNavigatorPointerId = 0;
        spaceNavigatorLastTick = 0;
        spaceNavigatorVector = { x: 0, y: 0, power: 0 };
        spaceNavigatorVisualVector = { x: 0, y: 0, power: 0 };
        spaceNavigatorVelocity = { x: 0, y: 0 };
        if (spaceNavigatorNode) {
          spaceNavigatorNode.classList.remove("is-active");
          spaceNavigatorNode.classList.remove("is-coasting");
        }
        applySpaceNavigatorVisual();
      };

      const releaseSpaceNavigatorMotion = () => {
        spaceNavigatorPointerId = 0;
        if (spaceNavigatorNode) {
          spaceNavigatorNode.classList.remove("is-active");
        }
        if (Math.hypot(spaceNavigatorVelocity.x, spaceNavigatorVelocity.y) > 12) {
          if (spaceNavigatorNode) {
            spaceNavigatorNode.classList.add("is-coasting");
          }
          if (!spaceNavigatorFrame) {
            spaceNavigatorLastTick = performance.now();
            spaceNavigatorFrame = window.requestAnimationFrame(stepSpaceNavigatorMotion);
          }
        } else {
          stopSpaceNavigatorMotion();
        }
      };

      const stepSpaceNavigatorMotion = (now) => {
        if (!spaceNavigatorNode) {
          spaceNavigatorFrame = 0;
          return;
        }
        const last = spaceNavigatorLastTick || now;
        const delta = Math.max(0, Math.min(50, now - last));
        spaceNavigatorLastTick = now;
        const pointerActive = Boolean(spaceNavigatorPointerId && spaceNavigatorNode.classList.contains("is-active"));
        if (pointerActive) {
          const power = Math.max(0, Math.min(1, spaceNavigatorVector.power));
          const targetSpeed = (170 + Math.pow(power, 1.18) * 1560);
          const targetX = spaceNavigatorVector.x * targetSpeed;
          const targetY = spaceNavigatorVector.y * targetSpeed;
          const response = 1 - Math.exp(-delta / 96);
          spaceNavigatorVelocity.x += (targetX - spaceNavigatorVelocity.x) * response;
          spaceNavigatorVelocity.y += (targetY - spaceNavigatorVelocity.y) * response;
          spaceNavigatorVisualVector = { ...spaceNavigatorVector };
        } else {
          const friction = Math.exp(-delta / 620);
          spaceNavigatorVelocity.x *= friction;
          spaceNavigatorVelocity.y *= friction;
          const speed = Math.hypot(spaceNavigatorVelocity.x, spaceNavigatorVelocity.y);
          if (speed > 0.1) {
            spaceNavigatorVisualVector = {
              x: spaceNavigatorVelocity.x / speed,
              y: spaceNavigatorVelocity.y / speed,
              power: Math.min(1, speed / 1500),
            };
          }
        }
        const speed = Math.hypot(spaceNavigatorVelocity.x, spaceNavigatorVelocity.y);
        scrollBySpaceNavigatorDelta(spaceNavigatorVelocity.x * delta / 1000, spaceNavigatorVelocity.y * delta / 1000);
        applySpaceNavigatorVisual();
        if (pointerActive || speed > 7) {
          spaceNavigatorFrame = window.requestAnimationFrame(stepSpaceNavigatorMotion);
          return;
        }
        stopSpaceNavigatorMotion();
      };

      const ensureSpaceNavigator = () => {
        if (!stageNode) {
          return null;
        }
        if (spaceNavigatorNode) {
          return spaceNavigatorNode;
        }
        spaceNavigatorNode = document.createElement("button");
        spaceNavigatorNode.type = "button";
        spaceNavigatorNode.className = "ft-space-navigator";
        spaceNavigatorNode.setAttribute("aria-label", "Move view");
        spaceNavigatorNode.innerHTML = '<span class="ft-space-navigator-grid"></span><span class="ft-space-navigator-ring is-a"></span><span class="ft-space-navigator-ring is-b"></span><span class="ft-space-navigator-spark is-one"></span><span class="ft-space-navigator-spark is-two"></span><span class="ft-space-navigator-vector"></span><span class="ft-space-navigator-core"></span><span class="ft-space-navigator-dot"></span>';
        stageNode.appendChild(spaceNavigatorNode);
        applySpaceNavigatorVisual();
        spaceNavigatorNode.addEventListener("pointerdown", (event) => {
          if (event.pointerType === "mouse" && event.button !== 0) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          updateSpaceNavigatorVisibility();
          if (!spaceNavigatorLearningActive()) {
            return;
          }
          stopQuestionCameraScrollAnimation();
          clearQuestionManualFocusTimer();
          spaceNavigatorPointerId = event.pointerId;
          spaceNavigatorVector = spaceNavigatorVectorForEvent(event);
          spaceNavigatorVisualVector = { ...spaceNavigatorVector };
          if (spaceNavigatorVector.power) {
            const kick = 360 + spaceNavigatorVector.power * 420;
            spaceNavigatorVelocity.x += spaceNavigatorVector.x * kick;
            spaceNavigatorVelocity.y += spaceNavigatorVector.y * kick;
          }
          spaceNavigatorNode.classList.add("is-active");
          spaceNavigatorNode.classList.remove("is-coasting");
          applySpaceNavigatorVisual();
          spaceNavigatorLastTick = performance.now();
          if (!spaceNavigatorFrame) {
            spaceNavigatorFrame = window.requestAnimationFrame(stepSpaceNavigatorMotion);
          }
          try {
            spaceNavigatorNode.setPointerCapture(event.pointerId);
          } catch (error) {
          }
        });
        spaceNavigatorNode.addEventListener("pointermove", (event) => {
          if (!spaceNavigatorPointerId || event.pointerId !== spaceNavigatorPointerId) {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          spaceNavigatorVector = spaceNavigatorVectorForEvent(event);
          spaceNavigatorVisualVector = { ...spaceNavigatorVector };
          applySpaceNavigatorVisual();
        });
        const stopPointer = (event) => {
          if (spaceNavigatorPointerId && event && event.pointerId && event.pointerId !== spaceNavigatorPointerId) {
            return;
          }
          releaseSpaceNavigatorMotion();
        };
        spaceNavigatorNode.addEventListener("pointerup", stopPointer);
        spaceNavigatorNode.addEventListener("pointercancel", stopSpaceNavigatorMotion);
        window.addEventListener("pointerdown", (event) => {
          if (
            spaceNavigatorNode
            && spaceNavigatorNode.classList.contains("is-coasting")
            && !(event.target && event.target.closest && event.target.closest(".ft-space-navigator"))
          ) {
            stopSpaceNavigatorMotion();
          }
        }, true);
        window.addEventListener("pointermove", updateSpaceNavigatorNearPointer, { passive: true });
        window.addEventListener("blur", () => setSpaceNavigatorNearPointer(false));
        const observedNodes = [authGate, loadGate, startFullscreenGate, vocabPreflightGate, cardNode, vocabCard, stageNode, qRootCard].filter(Boolean);
        if (window.MutationObserver && !spaceNavigatorObserver) {
          spaceNavigatorObserver = new MutationObserver(() => updateSpaceNavigatorVisibility());
          observedNodes.forEach((node) => spaceNavigatorObserver.observe(node, { attributes: true, attributeFilter: ["class", "hidden"] }));
        }
        window.addEventListener("resize", () => window.requestAnimationFrame(updateSpaceNavigatorVisibility));
        window.setTimeout(updateSpaceNavigatorVisibility, 0);
        return spaceNavigatorNode;
      };

      const clearQuestionCamera = (options = {}) => {
        const resetReveal = options.resetReveal !== false;
        clearQuestionManualFocusTimer();
        stopQuestionCameraScrollAnimation();
        stopSpaceNavigatorMotion();
        if (questionSideLayoutFrame) {
          window.cancelAnimationFrame(questionSideLayoutFrame);
          questionSideLayoutFrame = 0;
        }
        if (questionSideLayoutFollowFrame) {
          window.cancelAnimationFrame(questionSideLayoutFollowFrame);
          questionSideLayoutFollowFrame = 0;
        }
        if (questionResizeLayoutTimer) {
          window.clearTimeout(questionResizeLayoutTimer);
          questionResizeLayoutTimer = 0;
        }
        if (questionViewportLayoutTimer) {
          window.clearTimeout(questionViewportLayoutTimer);
          questionViewportLayoutTimer = 0;
        }
        if (questionViewportLayoutFrame) {
          window.cancelAnimationFrame(questionViewportLayoutFrame);
          questionViewportLayoutFrame = 0;
        }
        questionViewportLayoutForce = false;
        questionViewportLayoutGuidance = false;
        questionViewportLayoutDelaySet = null;
        if (resetReveal) {
          questionCardsRevealSettled = false;
          updateQuestionIdleStaticState();
        }
        questionCameraTransform = "";
        if (shellNode) {
          shellNode.style.removeProperty("--q-camera-transform");
        }
        if (stageNode) {
          stageNode.classList.remove("is-question-fit-measuring");
          if (resetReveal) {
            stageNode.scrollTop = 0;
            stageNode.scrollLeft = 0;
          }
        }
      };

      const restoreQuestionCamera = () => {
        if (!shellNode) {
          return;
        }
        if (questionCameraTransform) {
          shellNode.style.setProperty("--q-camera-transform", questionCameraTransform);
        } else {
          shellNode.style.removeProperty("--q-camera-transform");
        }
      };

      const questionCameraFocusNode = (targetNode) => {
        if (targetNode === qAudioCard && qPlayButton && qPlayButton.getBoundingClientRect().width) {
          return qPlayButton;
        }
        return targetNode;
      };

      const applyQuestionCameraFocus = (targetNode, options = {}) => {
        if (!stageNode || !shellNode || !targetNode || isQuestionMobileFlow()) {
          clearQuestionCamera({ resetReveal: false });
          return false;
        }
        if (questionSplitDesktopLayoutActive() && !options.allowSplitPan) {
          restoreQuestionCamera();
          stopQuestionCameraScrollAnimation();
          return false;
        }
        restoreQuestionCamera();
        const focusNode = questionCameraFocusNode(targetNode);
        const targetRect = focusNode.getBoundingClientRect();
        const stageRect = stageNode.getBoundingClientRect();
        if (!targetRect.width || !targetRect.height || !stageRect.width || !stageRect.height) {
          return false;
        }
        const alignYNode = options.alignYTarget || options.topReferenceNode || null;
        const alignYRect = alignYNode && typeof alignYNode.getBoundingClientRect === "function"
          ? alignYNode.getBoundingClientRect()
          : null;
        const verticalRect = alignYRect && alignYRect.width > 0 && alignYRect.height > 0
          ? alignYRect
          : targetRect;
        const targetCenterX = targetRect.left + targetRect.width / 2;
        const targetCenterY = targetRect.top + targetRect.height / 2;
        const viewportCenterX = stageRect.left + stageNode.clientWidth / 2;
        const viewportCenterY = stageRect.top + stageNode.clientHeight / 2;
        const maxScrollTop = Math.max(0, stageNode.scrollHeight - stageNode.clientHeight);
        const maxScrollLeft = Math.max(0, stageNode.scrollWidth - stageNode.clientWidth);
        const topOffset = Number.isFinite(Number(options.topOffset)) ? Number(options.topOffset) : 0;
        const desiredViewportTop = stageRect.top + Math.max(0, topOffset);
        let nextScrollTopRaw = options.alignY === "top"
          ? stageNode.scrollTop + verticalRect.top - desiredViewportTop
          : stageNode.scrollTop + targetCenterY - viewportCenterY;
        const topSafeInset = Number.isFinite(Number(options.topSafeInset))
          ? Math.max(0, Number(options.topSafeInset))
          : (targetNode === qQuestionCard ? QUESTION_CARD_TOP_SAFE_INSET_PX : 0);
        if (topSafeInset > 0) {
          const safeViewportTop = stageRect.top + topSafeInset;
          const maxScrollForSafeTop = stageNode.scrollTop + verticalRect.top - safeViewportTop;
          nextScrollTopRaw = Math.min(nextScrollTopRaw, maxScrollForSafeTop);
        }
        const nextScrollTop = Math.max(0, Math.min(maxScrollTop, nextScrollTopRaw));
        const nextScrollLeft = Math.max(0, Math.min(maxScrollLeft, stageNode.scrollLeft + targetCenterX - viewportCenterX));
        if ((options.behavior || "smooth") === "smooth") {
          animateQuestionStageScrollTo(nextScrollTop, nextScrollLeft, options.duration || QUESTION_CAMERA_PAN_SETTLE_MS);
        } else if (typeof stageNode.scrollTo === "function") {
          stopQuestionCameraScrollAnimation();
          try {
            stageNode.scrollTo({ top: nextScrollTop, left: nextScrollLeft, behavior: "auto" });
          } catch (error) {
            stageNode.scrollTop = nextScrollTop;
            stageNode.scrollLeft = nextScrollLeft;
          }
        } else {
          stopQuestionCameraScrollAnimation();
          stageNode.scrollTop = nextScrollTop;
          stageNode.scrollLeft = nextScrollLeft;
        }
        return true;
      };

      const settleQuestionCameraFocus = (targetNode, onDone = null, passes = 2) => {
        const run = (remaining) => {
          window.requestAnimationFrame(() => {
            if (!questionModeActive || !targetNode) {
              return;
            }
            positionQuestionSideCards();
            applyQuestionCameraFocus(targetNode, { behavior: "auto" });
            if (remaining > 1) {
              run(remaining - 1);
            } else if (typeof onDone === "function") {
              onDone();
            }
          });
        };
        run(Math.max(1, passes || 1));
      };

      const questionAnswerInfoWidth = (rootWidth = 760, questionWidth = 0) => {
        const preferred = Math.max(180, Math.min(380, (Number(rootWidth) || 760) * 0.56));
        const measuredQuestionWidth = Number(questionWidth) || 0;
        if (measuredQuestionWidth > 0) {
          const strictLimit = measuredQuestionWidth / 3;
          return Math.min(strictLimit, Math.max(80, Math.min(preferred, strictLimit)));
        }
        return Math.max(80, Math.min(preferred, 380));
      };

      const questionAnswerInfoReserveWidth = () => {
        if (!qRootCard || !shellNode) {
          return 460;
        }
        const rootRect = qRootCard.getBoundingClientRect();
        const shellRect = shellNode.getBoundingClientRect();
        const questionRect = qQuestionCard && qQuestionCard.getBoundingClientRect
          ? qQuestionCard.getBoundingClientRect()
          : null;
        const rootWidth = questionUnscaleLayoutValue(rootRect.width || 760);
        const questionWidth = questionRect && questionRect.width
          ? questionUnscaleLayoutValue(questionRect.width)
          : 0;
        const shellWidth = questionUnscaleLayoutValue(shellRect.width || (stageNode ? stageNode.clientWidth : 980));
        const gap = shellWidth >= 900
          ? Math.max(58, Math.min(96, rootWidth * 0.11))
          : Math.max(28, Math.min(48, rootWidth * 0.06));
        const infoWidth = questionAnswerInfoWidth(rootWidth, questionWidth);
        return (infoWidth + gap) * questionResponsiveLayoutScale();
      };

      const questionCardClusterCameraTarget = (options = {}) => {
        if (!qQuestionCard || !isQuestionCardInLayout(qQuestionCard)) {
          return null;
        }
        const nodes = [qQuestionCard];
        const includeInfo = options.includeInfo !== false;
        const infoLive = Boolean(includeInfo && qInfoCard && isQuestionCardInLayout(qInfoCard));
        if (infoLive) {
          nodes.push(qInfoCard);
        }
        const bounds = questionGeometryBounds(nodes);
        if (!bounds) {
          return qQuestionCard;
        }
        let left = bounds.left;
        const reserveInfo = options.reserveInfo !== false;
        if (reserveInfo && !infoLive) {
          const questionRect = qQuestionCard.getBoundingClientRect();
          if (questionRect.width > 0 && questionRect.height > 0) {
            left = Math.min(left, questionRect.left - questionAnswerInfoReserveWidth());
          }
        }
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

      const keepQuestionCardClusterInView = (options = {}) => {
        if (questionHighlightCameraFocusToken && options.force !== true) {
          return false;
        }
        if (!questionModeActive || !qQuestionCard || !isQuestionCardInLayout(qQuestionCard) || isQuestionMobileFlow() || questionSplitDesktopLayoutActive()) {
          return false;
        }
        const passes = Math.max(1, Math.floor(Number(options.passes) || 2));
        const behavior = clean(options.behavior || "auto") || "auto";
        const onDone = typeof options.onDone === "function" ? options.onDone : null;
        const run = (remaining) => {
          window.requestAnimationFrame(() => {
            if (questionHighlightCameraFocusToken && options.force !== true) {
              return;
            }
            if (!questionModeActive || !qQuestionCard || !isQuestionCardInLayout(qQuestionCard)) {
              return;
            }
            fitQuestionCameraToCard(qQuestionCard);
            positionQuestionSideCards({ force: Boolean(options.force) });
            const focusTarget = questionCardClusterCameraTarget({
              includeInfo: options.includeInfo !== false,
              reserveInfo: options.reserveInfo !== false,
            }) || qQuestionCard;
            applyQuestionCameraFocus(focusTarget, {
              behavior,
              duration: options.duration || 260,
              topSafeInset: QUESTION_CARD_TOP_SAFE_INSET_PX,
            });
            if (remaining > 1) {
              run(remaining - 1);
            } else if (onDone) {
              onDone();
            }
          });
        };
        run(passes);
        return true;
      };

      const keepQuestionCardOnlyInView = (options = {}) => keepQuestionCardClusterInView({
        ...options,
        includeInfo: false,
        reserveInfo: false,
      });

      const smoothReturnQuestionCardOnlyView = (onDone = null) => {
        clearQuestionCardOnlyViewTimers();
        const token = questionCardOnlyViewToken;
        keepQuestionCardOnlyInView({
          passes: 1,
          behavior: "smooth",
          duration: QUESTION_HIGHLIGHT_RETURN_PAN_MS,
          force: true,
        });
        const doneTimer = window.setTimeout(() => {
          questionCardOnlyViewTimers.delete(doneTimer);
          if (token !== questionCardOnlyViewToken) {
            return;
          }
          if (typeof onDone === "function") {
            onDone();
          }
        }, QUESTION_HIGHLIGHT_RETURN_PAN_MS + 140);
        questionCardOnlyViewTimers.add(doneTimer);
        const settleTimer = window.setTimeout(() => {
          questionCardOnlyViewTimers.delete(settleTimer);
          if (token !== questionCardOnlyViewToken || questionHighlightCameraFocusToken) {
            return;
          }
          keepQuestionCardOnlyInView({ passes: 1, behavior: "auto" });
        }, QUESTION_HIGHLIGHT_RETURN_PAN_MS + 520);
        questionCardOnlyViewTimers.add(settleTimer);
      };

      const settleQuestionCardOnlyView = (delays = [0, 90, 260, 620]) => {
        clearQuestionCardOnlyViewTimers();
        const token = questionCardOnlyViewToken;
        const steps = Array.isArray(delays) && delays.length ? delays : [0];
        steps.forEach((delay) => {
          const timer = window.setTimeout(() => {
            questionCardOnlyViewTimers.delete(timer);
            if (token !== questionCardOnlyViewToken || questionHighlightCameraFocusToken) {
              return;
            }
            keepQuestionCardOnlyInView({ passes: 1, behavior: "auto" });
          }, Math.max(0, Number(delay) || 0));
          questionCardOnlyViewTimers.add(timer);
        });
      };

      const scheduleQuestionSideLayout = (passes = 2) => {
        if (questionSideLayoutFrame) {
          return;
        }
        const layoutPasses = isQuestionMobilePerformanceSurface() && questionCardsRevealSettled && !questionRevealAnimationsActive
          ? 1
          : Math.max(1, Number(passes) || 1);
        questionSideLayoutFrame = window.requestAnimationFrame(() => {
          questionSideLayoutFrame = 0;
          positionQuestionSideCards();
          if (layoutPasses > 1 && !questionSideLayoutFollowFrame) {
            questionSideLayoutFollowFrame = window.requestAnimationFrame(() => {
              questionSideLayoutFollowFrame = 0;
              positionQuestionSideCards();
            });
          }
        });
      };

      const questionNow = () => (
        typeof performance !== "undefined" && performance && typeof performance.now === "function"
          ? performance.now()
          : Date.now()
      );

      const scheduleQuestionResizeLayout = () => {
        if (questionResizeLayoutTimer || questionSideLayoutFrame) {
          return;
        }
        const now = questionNow();
        const idleSettled = Boolean(questionCardsRevealSettled && !questionRevealAnimationsActive && !questionCameraScrollFrame);
        const minGap = isQuestionMobilePerformanceSurface()
          ? (idleSettled ? 320 : 86)
          : (idleSettled ? 180 : 34);
        const delay = Math.max(0, minGap - (now - questionResizeLayoutLastAt));
        questionResizeLayoutTimer = window.setTimeout(() => {
          questionResizeLayoutTimer = 0;
          questionResizeLayoutLastAt = questionNow();
          const settledNow = Boolean(questionCardsRevealSettled && !questionRevealAnimationsActive && !questionCameraScrollFrame);
          scheduleQuestionSideLayout(settledNow ? 1 : 2);
        }, delay);
      };

      const scheduleQuestionViewportLayoutRefresh = (delayMs = 80, options = {}) => {
        if (!questionModeActive) {
          return;
        }
        questionViewportLayoutForce = questionViewportLayoutForce || Boolean(options.force);
        questionViewportLayoutGuidance = questionViewportLayoutGuidance || options.guidance !== false;
        if (Array.isArray(options.guidanceDelays)) {
          questionViewportLayoutDelaySet = options.guidanceDelays;
        }
        const queueFrame = () => {
          if (questionViewportLayoutFrame) {
            return;
          }
          questionViewportLayoutFrame = window.requestAnimationFrame(() => {
            questionViewportLayoutFrame = 0;
            const force = questionViewportLayoutForce;
            const shouldSettleGuidance = questionViewportLayoutGuidance;
            const guidanceDelays = questionViewportLayoutDelaySet;
            questionViewportLayoutForce = false;
            questionViewportLayoutGuidance = false;
            questionViewportLayoutDelaySet = null;
            if (!questionModeActive) {
              return;
            }
            if (force) {
              positionQuestionSideCards({ force: true });
            } else {
              scheduleQuestionResizeLayout();
            }
            if (shouldSettleGuidance && (questionGuidanceBranchNodes.length || isQuestionPictureRegionPromptPinned())) {
              if (Array.isArray(guidanceDelays) && guidanceDelays.length) {
                settleQuestionGuidanceLayout(...guidanceDelays);
              } else {
                settleQuestionGuidanceLayout(0, isQuestionMobilePerformanceSurface() ? 260 : 140);
              }
            }
            updateSpaceNavigatorVisibility();
          });
        };
        if (questionViewportLayoutTimer) {
          return;
        }
        const wait = Math.max(0, Number(delayMs) || 0);
        if (wait > 0) {
          questionViewportLayoutTimer = window.setTimeout(() => {
            questionViewportLayoutTimer = 0;
            queueFrame();
          }, wait);
          return;
        }
        queueFrame();
      };

      const panQuestionCameraTo = (targetNode, onDone, delay = QUESTION_CAMERA_PAN_SETTLE_MS, options = {}) => {
        clearQuestionCameraPanTimer();
        const panToken = questionCameraPanToken;
        window.requestAnimationFrame(() => {
          if (panToken !== questionCameraPanToken || !questionModeActive || !targetNode) {
            return;
          }
          positionQuestionSideCards({ force: Boolean(options.forceLayout) });
          const resolvedTarget = typeof targetNode === "function" ? targetNode() : targetNode;
          if (!resolvedTarget) {
            return;
          }
          if (questionSplitDesktopLayoutActive() && !options.allowSplitPan) {
            restoreQuestionCamera();
            stopQuestionCameraScrollAnimation();
            questionCameraPanTimer = window.setTimeout(() => {
              questionCameraPanTimer = 0;
              if (panToken !== questionCameraPanToken) {
                return;
              }
              if (questionModeActive && typeof onDone === "function") {
                onDone();
              }
            }, Math.min(90, Math.max(0, Number(delay) || 0)));
            return;
          }
          const cameraOptions = { ...options };
          delete cameraOptions.forceLayout;
          applyQuestionCameraFocus(resolvedTarget, cameraOptions);
          questionCameraPanTimer = window.setTimeout(() => {
            questionCameraPanTimer = 0;
            if (panToken !== questionCameraPanToken) {
              return;
            }
            if (questionModeActive && typeof onDone === "function") {
              onDone();
            }
          }, delay);
        });
      };

      const QUESTION_CENTER_CARD_SELECTOR = ".ft-q-root-card, .ft-q-picture-card, .ft-q-audio-card, .ft-q-question-card, .ft-q-info-card, .ft-q-root-info-card, .ft-q-picture-answer-card";

      const clearQuestionCardFxActive = (card) => {
        if (!card || !card.classList) {
          return;
        }
        const timer = questionCardFxTimers.get(card);
        if (timer) {
          window.clearTimeout(timer);
        }
        questionCardFxTimers.delete(card);
        if (card.classList.contains("is-card-fx-hover")) {
          return;
        }
        card.classList.remove("is-card-fx-active");
      };

      const setQuestionCardFxHover = (card, active) => {
        if (!card || !card.classList || !isQuestionCenterTargetVisible(card)) {
          return;
        }
        card.classList.toggle("is-card-fx-hover", Boolean(active));
      };

      const activateQuestionCardFx = (card, duration = 1200) => {
        if (!card || !card.classList || !isQuestionCenterTargetVisible(card)) {
          return;
        }
        card.classList.add("is-card-fx-active");
        const previous = questionCardFxTimers.get(card);
        if (previous) {
          window.clearTimeout(previous);
        }
        const timer = window.setTimeout(() => {
          if (card.classList.contains("is-card-fx-hover")) {
            questionCardFxTimers.delete(card);
            return;
          }
          card.classList.remove("is-card-fx-active");
          questionCardFxTimers.delete(card);
        }, Math.max(350, Number(duration) || 1200));
        questionCardFxTimers.set(card, timer);
      };

      const releaseQuestionCardFxHover = (card, duration = 900) => {
        if (!card || !card.classList || !isQuestionCenterTargetVisible(card)) {
          return;
        }
        setQuestionCardFxHover(card, false);
        if (card.classList.contains("is-card-fx-active")) {
          activateQuestionCardFx(card, duration);
        }
      };

      const clearAllQuestionCardFxActive = () => {
        if (!shellNode) {
          return;
        }
        shellNode.querySelectorAll(".is-card-fx-active, .is-card-fx-hover").forEach((card) => {
          const timer = questionCardFxTimers.get(card);
          if (timer) {
            window.clearTimeout(timer);
          }
          questionCardFxTimers.delete(card);
          card.classList.remove("is-card-fx-active", "is-card-fx-hover");
        });
      };

      const questionCardFxTargetFromEvent = (event) => {
        const target = event && event.target;
        if (!target || typeof target.closest !== "function") {
          return null;
        }
        const card = target.closest(QUESTION_CENTER_CARD_SELECTOR);
        return card && stageNode && stageNode.contains(card) ? card : null;
      };

      const pulseQuestionCardFxFromEvent = (event, duration = 1200) => {
        const card = questionCardFxTargetFromEvent(event);
        if (card) {
          activateQuestionCardFx(card, duration);
        }
      };

      const setQuestionCardFxHoverFromEvent = (event, active) => {
        const card = questionCardFxTargetFromEvent(event);
        if (card) {
          setQuestionCardFxHover(card, active);
        }
        return card;
      };

      const clearQuestionRootFocus = () => {
        if (questionRootFocusTimer) {
          window.clearTimeout(questionRootFocusTimer);
          questionRootFocusTimer = 0;
        }
        if (qRootCard) {
          qRootCard.classList.remove("is-card-focused");
        }
      };

      const activateQuestionRootFocus = (duration = 2600) => {
        if (!qRootCard) {
          return;
        }
        if (questionRootFocusTimer) {
          window.clearTimeout(questionRootFocusTimer);
        }
        qRootCard.classList.add("is-card-focused");
        activateQuestionCardFx(qRootCard, duration);
        questionRootFocusTimer = window.setTimeout(() => {
          questionRootFocusTimer = 0;
          qRootCard.classList.remove("is-card-focused");
        }, Math.max(600, Number(duration) || 2600));
      };

      const isQuestionCenterTargetVisible = (node) => {
        if (!node || node.classList.contains("is-hidden")) {
          return false;
        }
        if (node === qRootCard) {
          return true;
        }
        if (node === questionRootInfoCard) {
          return node.classList.contains("is-live");
        }
        if (node.classList && node.classList.contains("ft-q-picture-answer-card")) {
          return node.classList.contains("is-live");
        }
        return isQuestionCardInLayout(node);
      };

      const isQuestionCardCenterNavigationReady = () => Boolean(
        questionModeActive &&
        questionCardsRevealSettled &&
        qQuestionCard &&
        qQuestionCard.classList.contains("is-live")
      );

      const fitQuestionCameraToCard = (targetNode) => {
        if (!stageNode || !shellNode || !targetNode || isQuestionMobileFlow() || questionSplitDesktopLayoutActive()) {
          return 1;
        }
        questionManualFocusTarget = targetNode;
        questionCameraTransform = "";
        restoreQuestionCamera();
        positionQuestionSideCards();
        const targetRect = targetNode.getBoundingClientRect();
        if (!targetRect.width || !targetRect.height) {
          return 1;
        }
        return 1;
      };

      const centerQuestionCardInView = (targetNode) => {
        if (questionHighlightCameraFocusToken) {
          return false;
        }
        if (!isQuestionCardCenterNavigationReady() || !isQuestionCenterTargetVisible(targetNode)) {
          return false;
        }
        if (isQuestionMobileFlow()) {
          try {
            targetNode.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
          } catch (error) {
            targetNode.scrollIntoView();
          }
          return true;
        }
        clearQuestionManualFocusTimer();
        fitQuestionCameraToCard(targetNode);
        window.requestAnimationFrame(() => {
          if (!isQuestionCardCenterNavigationReady() || !isQuestionCenterTargetVisible(targetNode)) {
            return;
          }
          positionQuestionSideCards();
          applyQuestionCameraFocus(targetNode, { behavior: "smooth" });
          questionManualFocusTimer = window.setTimeout(() => {
            questionManualFocusTimer = 0;
            if (isQuestionCardCenterNavigationReady() && isQuestionCenterTargetVisible(targetNode)) {
              settleQuestionCameraFocus(targetNode, null, 2);
            }
          }, QUESTION_CAMERA_PAN_SETTLE_MS + 120);
        });
        return true;
      };

      const questionCenterEventIsInteractive = (target) => Boolean(target && typeof target.closest === "function" && target.closest(
        "button, input, textarea, select, a, [role='button'], [contenteditable='true']"
      ));

      const handleQuestionCardClick = (event) => {
        if (questionHighlightCameraFocusToken) {
          return;
        }
        if (!isQuestionCardCenterNavigationReady()) {
          return;
        }
        const rawTarget = event && event.target;
        if (!rawTarget || typeof rawTarget.closest !== "function") {
          return;
        }
        if (questionCenterEventIsInteractive(rawTarget)) {
          return;
        }
        const targetCard = rawTarget.closest(QUESTION_CENTER_CARD_SELECTOR);
        if (!targetCard || !stageNode || !stageNode.contains(targetCard)) {
          return;
        }
        centerQuestionCardInView(targetCard);
      };

      const handleQuestionCardPointerDown = (event) => {
        if (questionHighlightCameraFocusToken) {
          questionFocusPointerState = null;
          return;
        }
        if (!isQuestionCardCenterNavigationReady()) {
          questionFocusPointerState = null;
          return;
        }
        if (event.pointerType === "mouse" && event.button !== 0) {
          questionFocusPointerState = null;
          return;
        }
        const rawTarget = event && event.target;
        if (!rawTarget || typeof rawTarget.closest !== "function") {
          questionFocusPointerState = null;
          return;
        }
        if (questionCenterEventIsInteractive(rawTarget)) {
          questionFocusPointerState = null;
          return;
        }
        const targetCard = rawTarget.closest(QUESTION_CENTER_CARD_SELECTOR);
        questionFocusPointerState = targetCard && stageNode && stageNode.contains(targetCard)
          ? {
            pointerId: event.pointerId,
            card: targetCard,
            x: event.clientX,
            y: event.clientY,
          }
          : null;
        if (targetCard) {
          activateQuestionCardFx(targetCard, 1800);
        }
      };

      const handleQuestionCardPointerUp = (event) => {
        if (questionHighlightCameraFocusToken) {
          questionFocusPointerState = null;
          return;
        }
        const state = questionFocusPointerState;
        questionFocusPointerState = null;
        if (!state || state.pointerId !== event.pointerId) {
          return;
        }
        const moved = Math.hypot(event.clientX - state.x, event.clientY - state.y);
        if (moved > 8) {
          return;
        }
        centerQuestionCardInView(state.card);
        activateQuestionCardFx(state.card, 2600);
      };

      const fitQuestionPictureCardToImage = () => {
        if (!qPictureCard || !qPictureImg || isQuestionMobileFlow()) {
          return;
        }
        const naturalWidth = Number(qPictureImg.naturalWidth || 0);
        const naturalHeight = Number(qPictureImg.naturalHeight || 0);
        const layoutScale = questionResponsiveLayoutScale();
        const pictureRectWidth = qPictureCard.getBoundingClientRect().width;
        const fallbackWidth = Math.max(220, Math.round((pictureRectWidth ? questionUnscaleLayoutValue(pictureRectWidth) : 360) - 54));
        const baseWidth = naturalWidth || fallbackWidth;
        const baseHeight = naturalHeight || Math.round(baseWidth * 0.75);
        const shellRect = shellNode ? shellNode.getBoundingClientRect() : null;
        const viewportHeight = Math.max((window.innerHeight || 0) / layoutScale, shellRect ? questionUnscaleLayoutValue(shellRect.height) : 0);
        const viewportWidth = Math.max((window.innerWidth || 0) / layoutScale, shellRect ? questionUnscaleLayoutValue(shellRect.width) : 0);
        const maxRenderHeight = Math.max(220, Math.min(420, Math.round(viewportHeight * 0.42)));
        const maxRenderWidth = Math.max(280, Math.min(560, Math.round(viewportWidth * 0.32)));
        let renderWidth = Math.max(96, Math.round(baseWidth * questionPictureZoom));
        let renderHeight = Math.max(72, Math.round(baseHeight * questionPictureZoom));
        if (renderHeight > maxRenderHeight) {
          const ratio = maxRenderHeight / renderHeight;
          renderHeight = maxRenderHeight;
          renderWidth = Math.max(96, Math.round(renderWidth * ratio));
        }
        if (renderWidth > maxRenderWidth) {
          const ratio = maxRenderWidth / renderWidth;
          renderWidth = maxRenderWidth;
          renderHeight = Math.max(72, Math.round(renderHeight * ratio));
        }
        qPictureCard.style.setProperty("--q-picture-zoom", questionPictureZoom.toFixed(2));
        qPictureCard.style.setProperty("--q-picture-render-width", `${renderWidth}px`);
        qPictureCard.style.setProperty("--q-picture-render-height", `${renderHeight}px`);
        qPictureCard.style.setProperty("--q-picture-card-width", `${Math.max(260, renderWidth + 54)}px`);
      };

      const setQuestionPictureZoom = (value = 1) => {
        questionPictureZoom = Math.max(0.35, Math.min(3, Number(value) || 1));
        fitQuestionPictureCardToImage();
        scheduleQuestionSideLayout();
      };

      const resetQuestionPictureNaturalSize = () => {
        if (!qPictureCard) {
          return;
        }
        qPictureCard.style.removeProperty("--q-picture-natural-width");
        qPictureCard.style.removeProperty("--q-picture-render-width");
        qPictureCard.style.removeProperty("--q-picture-render-height");
        qPictureCard.style.removeProperty("--q-picture-card-width");
        setQuestionPictureZoom(1);
      };

      const QUESTION_PICTURE_SKINS = ["q-picture-skin-1", "q-picture-skin-2", "q-picture-skin-3", "q-picture-skin-4", "q-picture-skin-5"];
      const QUESTION_SHIP_CLASSES = ["q-ship-1", "q-ship-2", "q-ship-3", "q-ship-4", "q-ship-5"];

      const clearQuestionPictureSkin = () => {
        if (!qPictureCard) {
          return;
        }
        qPictureCard.classList.remove(...QUESTION_PICTURE_SKINS);
      };

      const applyQuestionShipType = (node) => {
        if (!qPictureCard) {
          return;
        }
        const root = questionCardData(node, "root") || {};
        const rawShip = clean(node && (node.ship_type || node.shipType || node.st) || root.ship_type || root.shipType || root.st || "random").toLowerCase();
        let ship = /^ship-[1-5]$/.test(rawShip) ? rawShip : "random";
        qPictureCard.classList.remove(...QUESTION_SHIP_CLASSES);
        if (ship === "random") {
          let nextShipIndex = 1 + Math.floor(Math.random() * QUESTION_SHIP_CLASSES.length);
          if (QUESTION_SHIP_CLASSES.length > 1 && nextShipIndex === questionLastShipIndex) {
            nextShipIndex = (nextShipIndex % QUESTION_SHIP_CLASSES.length) + 1;
          }
          questionLastShipIndex = nextShipIndex;
          ship = `ship-${nextShipIndex}`;
        } else {
          questionLastShipIndex = Number(ship.replace("ship-", "")) || questionLastShipIndex;
        }
        qPictureCard.classList.add(`q-${ship}`);
      };

      const currentQuestionShipIndex = () => {
        if (!qPictureCard) {
          return questionLastShipIndex || 1;
        }
        for (let index = 1; index <= QUESTION_SHIP_CLASSES.length; index += 1) {
          if (qPictureCard.classList.contains(`q-ship-${index}`)) {
            return index;
          }
        }
        return questionLastShipIndex || 1;
      };

      const setQuestionShipIndex = (index) => {
        if (!qPictureCard) {
          return;
        }
        const total = QUESTION_SHIP_CLASSES.length;
        const normalized = ((Number(index) || 1) - 1 + total) % total + 1;
        questionLastShipIndex = normalized;
        qPictureCard.classList.remove(...QUESTION_SHIP_CLASSES);
        qPictureCard.classList.add(`q-ship-${normalized}`);
      };

      const stepQuestionShip = (direction = 1) => {
        setQuestionShipIndex(currentQuestionShipIndex() + (Number(direction) || 1));
      };

      const applyRandomQuestionPictureSkin = () => {
        if (!qPictureCard) {
          return;
        }
        clearQuestionPictureSkin();
        let nextSkin = 1 + Math.floor(Math.random() * QUESTION_PICTURE_SKINS.length);
        if (QUESTION_PICTURE_SKINS.length > 1 && nextSkin === questionLastPictureSkin) {
          nextSkin = (nextSkin % QUESTION_PICTURE_SKINS.length) + 1;
        }
        questionLastPictureSkin = nextSkin;
        qPictureCard.classList.add(`q-picture-skin-${nextSkin}`);
      };

      const applyQuestionPictureNaturalSize = () => {
        if (!qPictureCard || !qPictureImg) {
          return;
        }
        const naturalWidth = Number(qPictureImg.naturalWidth || 0);
        if (naturalWidth > 0) {
          qPictureCard.style.setProperty("--q-picture-natural-width", `${naturalWidth}px`);
        } else {
          qPictureCard.style.removeProperty("--q-picture-natural-width");
        }
        fitQuestionPictureCardToImage();
        scheduleQuestionSideLayout();
      };

      const hideQuestionSideCards = (clearContent = false) => {
        if (!isQuestionPictureRegionPromptPinned()) {
          hideQuestionPictureRegions();
        }
        [qPictureCard, qAudioCard, qConnectorPicture, qConnectorAudio].forEach((node) => {
          if (node) {
            node.classList.remove("is-live", "is-preparing", "is-connector-focused", "is-focused");
          }
        });
        if (qAudioCard) {
          qAudioCard.classList.remove("is-playing");
        }
        if (clearContent) {
          if (qPictureImg) {
            qPictureImg.removeAttribute("src");
            qPictureImg.alt = "";
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
        }
      };

      const prepareQuestionAudioSideCard = (node = questionCurrentNode) => {
        if (!qAudioCard) {
          return false;
        }
        const audio = questionCardData(node, "audio");
        if (!audio || !audio.url) {
          return false;
        }
        if (qAudioText) {
          qAudioText.textContent = clean(audio.text || "Audio ready.");
        }
        if (qAudioVoice) {
          qAudioVoice.textContent = clean(audio.voice_label || audio.voice || "Build voice");
        }
        qAudioCard.classList.add("is-preparing");
        qAudioCard.classList.remove("is-live");
        return true;
      };

      const showQuestionAudioSideCard = (node = questionCurrentNode) => {
        if (!qAudioCard || (!qAudioCard.classList.contains("is-preparing") && !qAudioCard.classList.contains("is-live") && !prepareQuestionAudioSideCard(node))) {
          return false;
        }
        qAudioCard.classList.remove("is-preparing");
        qAudioCard.classList.add("is-live");
        if (qConnectorAudio) {
          qConnectorAudio.classList.add("is-live");
        }
        return true;
      };

      const prepareQuestionPictureSideCard = (node = questionCurrentNode) => {
        if (!qPictureCard) {
          return false;
        }
        const picture = questionCardData(node, "picture");
        if (!picture || !picture.url) {
          return false;
        }
        resetQuestionPictureNaturalSize();
        applyQuestionPictureRegionColor(node);
        applyRandomQuestionPictureSkin();
        applyQuestionShipType(node);
        if (qPictureImg) {
          qPictureImg.src = serverAssetUrl(picture.url);
          qPictureImg.alt = clean(picture.caption || picture.name || "");
          qPictureImg.draggable = false;
          if (qPictureImg.complete) {
            applyQuestionPictureNaturalSize();
          }
        }
        if (qPictureCaption) {
          qPictureCaption.textContent = clean(picture.caption || picture.name || "");
        }
        qPictureCard.classList.add("is-preparing");
        qPictureCard.classList.remove("is-live");
        return true;
      };

      const waitQuestionPictureLayoutReady = (onReady) => {
        const settlePictureLayout = () => {
          applyQuestionPictureNaturalSize();
          positionQuestionSideCards({ force: true });
          window.requestAnimationFrame(() => {
            positionQuestionSideCards({ force: true });
            window.requestAnimationFrame(onReady);
          });
        };
        if (!qPictureImg || qPictureImg.complete || !qPictureImg.src) {
          settlePictureLayout();
          return;
        }
        let settled = false;
        const finish = () => {
          if (settled) {
            return;
          }
          settled = true;
          settlePictureLayout();
        };
        const timeout = window.setTimeout(finish, 320);
        qPictureImg.addEventListener("load", () => {
          window.clearTimeout(timeout);
          finish();
        }, { once: true });
        qPictureImg.addEventListener("error", () => {
          window.clearTimeout(timeout);
          finish();
        }, { once: true });
      };

      const showQuestionPictureSideCard = (node = questionCurrentNode) => {
        if (!qPictureCard || (!qPictureCard.classList.contains("is-preparing") && !qPictureCard.classList.contains("is-live") && !prepareQuestionPictureSideCard(node))) {
          return false;
        }
        qPictureCard.classList.remove("is-preparing");
        qPictureCard.classList.add("is-live");
        if (qConnectorPicture) {
          qConnectorPicture.classList.add("is-live");
        }
        return true;
      };

      const renderQuestionSideCards = (node = questionCurrentNode) => {
        hideQuestionSideCards(false);
        if (!node) {
          return false;
        }
        const audioShown = showQuestionAudioSideCard(node);
        const pictureShown = showQuestionPictureSideCard(node);
        const shown = Boolean(audioShown || pictureShown);
        scheduleQuestionSideLayout();
        if (questionRootInfoActivePayload && questionRootInfoActivePayload.anchor === "picture_regions") {
          window.requestAnimationFrame(repositionActiveQuestionRootInfo);
        }
        return shown;
      };

      const clearQuestionPositionStyles = () => {
        [qRootCard, qPictureCard, qAudioCard, qQuestionCard, qInfoCard, qConnectorPicture, qConnectorAudio, qConnectorQuestion, qConnectorInfo].forEach((node) => {
          if (!node) {
            return;
          }
          [
            "left",
            "top",
            "right",
            "bottom",
            "width",
            "max-width",
            "height",
            "max-height",
            "margin-left",
            "justify-self",
            "overflow-y",
            "transform",
            "transform-origin",
          ].forEach((name) => node.style.removeProperty(name));
        });
      };

      const shellPoint = (rect, xRatio, yRatio) => {
        const shellRect = shellNode ? shellNode.getBoundingClientRect() : { left: 0, top: 0 };
        return {
          x: questionUnscaleLayoutValue(rect.left - shellRect.left + rect.width * xRatio),
          y: questionUnscaleLayoutValue(rect.top - shellRect.top + rect.height * yRatio),
        };
      };

      const positionQuestionLine = (line, start, end) => {
        if (!line || !start || !end) {
          return;
        }
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const length = Math.max(1, Math.hypot(dx, dy));
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        line.style.left = `${start.x}px`;
        line.style.top = `${start.y}px`;
        line.style.width = `${length}px`;
        line.style.transform = `translateY(-50%) rotate(${angle}deg)`;
        line.style.transformOrigin = "left center";
      };

      const questionLayoutRootAnchorSnapshot = () => {
        if (!stageNode || !qRootCard || qRootCard.classList.contains("is-hidden") || isQuestionMobileFlow()) {
          return null;
        }
        if (questionSplitDesktopLayoutActive()) {
          return null;
        }
        if (qRootCard.classList.contains("is-typing")) {
          return null;
        }
        if (questionCardsRevealSettled || questionCameraScrollFrame) {
          return null;
        }
        const rect = qRootCard.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return null;
        }
        return {
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2,
          scrollLeft: stageNode.scrollLeft,
          scrollTop: stageNode.scrollTop,
        };
      };

      const restoreQuestionLayoutRootAnchor = (snapshot) => {
        if (!snapshot || !stageNode || !qRootCard || qRootCard.classList.contains("is-hidden") || isQuestionMobileFlow()) {
          return;
        }
        if (questionSplitDesktopLayoutActive()) {
          return;
        }
        if (qRootCard.classList.contains("is-typing")) {
          return;
        }
        if (questionCardsRevealSettled || questionCameraScrollFrame) {
          return;
        }
        const rect = qRootCard.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return;
        }
        const nextX = rect.left + rect.width / 2;
        const nextY = rect.top + rect.height / 2;
        const dx = nextX - snapshot.x;
        const dy = nextY - snapshot.y;
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) {
          return;
        }
        const maxLeft = Math.max(0, stageNode.scrollWidth - stageNode.clientWidth);
        const maxTop = Math.max(0, stageNode.scrollHeight - stageNode.clientHeight);
        stageNode.scrollLeft = Math.max(0, Math.min(maxLeft, snapshot.scrollLeft + dx));
        stageNode.scrollTop = Math.max(0, Math.min(maxTop, snapshot.scrollTop + dy));
      };

      const questionLayoutNodeSignature = (node) => {
        if (!node) {
          return "x";
        }
        return [
          node.classList.contains("is-live") ? "l" : "-",
          node.classList.contains("is-preparing") ? "p" : "-",
          node.classList.contains("is-hidden") ? "h" : "-",
          Math.round(node.offsetWidth || 0),
          Math.round(node.offsetHeight || 0),
        ].join("");
      };

      const questionSideLayoutSignature = () => [
        questionModeActive ? "1" : "0",
        questionCardsRevealSettled ? "s" : "r",
        questionRevealAnimationsActive ? "a" : "-",
        isQuestionVisualProfileActive() ? "vp" : "vn",
        questionResponsiveScale.toFixed(3),
        stageNode ? Math.round(stageNode.clientWidth || 0) : 0,
        stageNode ? Math.round(stageNode.clientHeight || 0) : 0,
        Math.round((window.visualViewport && window.visualViewport.height) || window.innerHeight || 0),
        questionCurrentNode && questionCurrentNode.id ? questionCurrentNode.id : currentNodeIndex,
        questionQuestionIndex,
        questionManualFocusTarget && questionManualFocusTarget.id ? questionManualFocusTarget.id : "",
        questionPictureZoom.toFixed(2),
        questionPictureAnswerActive ? "pa" : "p-",
        questionPictureAnswerOptionValues.length,
        questionRootInfoActivePayload && questionRootInfoActivePayload.anchor ? questionRootInfoActivePayload.anchor : "",
        questionLayoutNodeSignature(qRootCard),
        questionLayoutNodeSignature(qPictureCard),
        questionLayoutNodeSignature(qAudioCard),
        questionLayoutNodeSignature(qQuestionCard),
        questionLayoutNodeSignature(qInfoCard),
        questionRootInfoCard && questionRootInfoCard.classList.contains("is-live") ? "ri" : "r-",
      ].join("|");

      function positionQuestionSideCards(options = {}) {
        const mobileFlow = questionModeActive && isQuestionMobileFlow();
        if (!questionModeActive || !qRootCard || qRootCard.classList.contains("is-hidden") || !shellNode || mobileFlow) {
          questionSideLayoutCacheKey = "";
          clearQuestionPositionStyles();
          clearQuestionCamera({ resetReveal: !mobileFlow });
          clearQuestionResponsiveScale();
          if (shellNode) {
            shellNode.style.removeProperty("--q-layout-width");
            shellNode.style.removeProperty("--q-layout-height");
            shellNode.style.removeProperty("--q-root-height");
            shellNode.style.removeProperty("--q-question-top-padding");
            shellNode.style.removeProperty("--q-stage-shell-justify");
          }
          return;
        }
        applyQuestionResponsiveScale();
        const canUseLayoutCache = !options.force
          && questionCardsRevealSettled
          && !questionRevealAnimationsActive
          && !questionCameraScrollFrame;
        const layoutCacheKey = canUseLayoutCache ? questionSideLayoutSignature() : "";
        if (canUseLayoutCache && layoutCacheKey && layoutCacheKey === questionSideLayoutCacheKey) {
          return;
        }
        const layoutScale = questionResponsiveLayoutScale();
        const hadCameraTransform = Boolean(questionCameraTransform && shellNode);
        const layoutAnchorSnapshot = questionLayoutRootAnchorSnapshot();
        let layoutCompleted = false;
        try {
          if (hadCameraTransform) {
            shellNode.style.removeProperty("--q-camera-transform");
          }
          const profileActive = isQuestionVisualProfileActive();
          const stageWidth = stageNode ? questionUnscaleLayoutValue(stageNode.clientWidth) : questionUnscaleLayoutValue(window.innerWidth || 980);
          const splitMetrics = questionSplitDesktopLayoutActive() ? questionSplitLayoutMetrics() : null;
          if (splitMetrics) {
            shellNode.style.setProperty("--q-stage-shell-justify", "start");
            shellNode.style.setProperty("--q-layout-width", `${splitMetrics.shellWidth}px`);
            qRootCard.style.width = `${splitMetrics.rootWidth}px`;
            qRootCard.style.maxWidth = `${splitMetrics.rootWidth}px`;
            qRootCard.style.marginLeft = `${splitMetrics.left}px`;
            qRootCard.style.justifySelf = "start";
          } else {
            qRootCard.style.removeProperty("width");
            qRootCard.style.removeProperty("max-width");
            qRootCard.style.removeProperty("margin-left");
            qRootCard.style.removeProperty("justify-self");
          }
          const rootWidthEstimate = (splitMetrics && splitMetrics.rootWidth) || qRootCard.offsetWidth || 760;
          const viewportHeight = stageNode && stageNode.clientHeight
            ? stageNode.clientHeight
            : ((window.visualViewport && window.visualViewport.height) || window.innerHeight || 720);
          const layoutViewportHeight = Math.max(1, questionUnscaleLayoutValue(viewportHeight));
          const baseShellWidth = Math.max(profileActive ? 1180 : 980, stageWidth || 0);
          const roughGap = baseShellWidth >= 900
            ? Math.max(58, Math.min(96, rootWidthEstimate * 0.11))
            : Math.max(28, Math.min(48, rootWidthEstimate * 0.06));
          const audioReach = isQuestionCardInLayout(qAudioCard)
            ? Math.max(300, Math.min(360, rootWidthEstimate * 0.6)) + roughGap
            : 0;
          const pictureWidth = isQuestionCardInLayout(qPictureCard)
            ? Number.parseFloat(getComputedStyle(qPictureCard).getPropertyValue("--q-picture-card-width")) ||
              qPictureCard.offsetWidth ||
              360
            : 0;
          const pictureReach = pictureWidth ? pictureWidth + roughGap : 0;
          const infoReach = (isQuestionCardInLayout(qInfoCard) || isQuestionCardInLayout(qQuestionCard)) ? 420 + roughGap : 0;
          const pictureAnswerReach = questionPictureAnswerActive
            ? pictureReach + Math.max(760, Math.min(980, (stageWidth || baseShellWidth) * 0.58))
            : 0;
          const sideReach = Math.max(audioReach, pictureReach, infoReach, pictureAnswerReach);
          if (splitMetrics) {
            shellNode.style.setProperty("--q-stage-shell-justify", "start");
            shellNode.style.setProperty("--q-layout-width", `${splitMetrics.shellWidth}px`);
          } else if (sideReach > 0) {
            const viewportBuffer = Math.max(stageWidth || 0, profileActive ? 1180 : 980) * (profileActive ? 1.12 : 1);
            shellNode.style.setProperty("--q-stage-shell-justify", "start");
            shellNode.style.setProperty(
              "--q-layout-width",
              `${Math.ceil(Math.max(baseShellWidth, rootWidthEstimate + sideReach * 2 + viewportBuffer))}px`,
            );
          } else {
            shellNode.style.removeProperty("--q-layout-width");
            shellNode.style.removeProperty("--q-stage-shell-justify");
          }
          const rootHeightEstimate = qRootCard.offsetHeight
            || questionUnscaleLayoutValue(qRootCard.getBoundingClientRect().height)
            || 360;
          shellNode.style.setProperty("--q-root-height", `${Math.ceil(rootHeightEstimate)}px`);
          if (qRootCard.classList.contains("is-typing") || Number.isFinite(Number(questionTypingRootReservedHeight))) {
            const measuredTypingTop = questionCurrentRootTopPadding();
            const pinnedTypingTop = Number.isFinite(Number(questionTypingRootTopPadding))
              ? Number(questionTypingRootTopPadding)
              : (Number.isFinite(Number(measuredTypingTop))
                ? Number(measuredTypingTop)
                : questionRootTypingTopPadding(layoutViewportHeight, profileActive, questionTypingRootReservedHeight || rootHeightEstimate));
            shellNode.style.setProperty(
              "--q-question-top-padding",
              `${Math.ceil(pinnedTypingTop)}px`,
            );
          } else if (rootHeightEstimate > layoutViewportHeight * 0.92) {
            const rootFocusTopBuffer = Math.max(
              profileActive ? 34 : 28,
              Math.min(layoutViewportHeight * 0.62, Math.max(260, layoutViewportHeight * 0.55)),
            );
            shellNode.style.setProperty("--q-question-top-padding", `${Math.ceil(rootFocusTopBuffer)}px`);
          } else {
            shellNode.style.removeProperty("--q-question-top-padding");
          }
          const shellRect = shellNode.getBoundingClientRect();
          const rootRect = qRootCard.getBoundingClientRect();
          if (!shellRect.width || !rootRect.width) {
            return;
          }
          const shellWidth = questionUnscaleLayoutValue(shellRect.width);
          const rootWidth = questionUnscaleLayoutValue(rootRect.width);
          const rootHeight = questionUnscaleLayoutValue(rootRect.height);
          const rootLayoutHeight = Math.max(
            qRootCard.offsetHeight || 0,
            rootHeight,
          );
          shellNode.style.setProperty("--q-root-height", `${Math.ceil(rootLayoutHeight)}px`);
          const rootLeft = questionUnscaleLayoutValue(rootRect.left - shellRect.left);
          const rootTop = questionUnscaleLayoutValue(rootRect.top - shellRect.top);
          const rootRight = rootLeft + rootWidth;
          const gap = shellWidth >= 900
            ? Math.max(58, Math.min(96, rootWidth * 0.11))
            : Math.max(28, Math.min(48, rootWidth * 0.06));
          if (isQuestionCardInLayout(qPictureCard)) {
            fitQuestionPictureCardToImage();
            const cardWidth = Number.parseFloat(getComputedStyle(qPictureCard).getPropertyValue("--q-picture-card-width")) ||
              questionUnscaleLayoutValue(qPictureCard.getBoundingClientRect().width) ||
              320;
            if (splitMetrics) {
              const pictureWidth = Math.max(260, Math.min(splitMetrics.rootWidth, Math.round(cardWidth)));
              const pictureGap = Math.max(28, Math.min(52, layoutViewportHeight * 0.052));
              const rootVisualBottom = rootTop + rootLayoutHeight + 10;
              qPictureCard.style.left = `${splitMetrics.left}px`;
              qPictureCard.style.right = "auto";
              qPictureCard.style.top = `${rootVisualBottom + pictureGap}px`;
              qPictureCard.style.width = `${pictureWidth}px`;
            } else {
              const pictureLift = Math.max(34, Math.min(92, rootHeight * 0.18));
              qPictureCard.style.left = `${rootRight + gap}px`;
              qPictureCard.style.right = "auto";
              qPictureCard.style.top = `${Math.max(0, rootTop - pictureLift)}px`;
              qPictureCard.style.width = `${Math.max(260, Math.round(cardWidth))}px`;
            }
            const pictureRect = qPictureCard.getBoundingClientRect();
            if (splitMetrics) {
              positionQuestionLine(
                qConnectorPicture,
                shellPoint(rootRect, 0.28, 1),
                shellPoint(pictureRect, 0.28, 0),
              );
            } else {
              positionQuestionLine(
                qConnectorPicture,
                shellPoint(rootRect, 1, 0.26),
                shellPoint(pictureRect, 0, 0.42),
              );
            }
          }
          if (isQuestionCardInLayout(qAudioCard)) {
            const audioWidth = splitMetrics
              ? Math.max(280, Math.min(360, splitMetrics.audioWidth || splitMetrics.rootWidth * 0.72))
              : Math.max(300, Math.min(360, rootWidth * 0.6));
            qAudioCard.style.width = `${audioWidth}px`;
            qAudioCard.style.left = splitMetrics
              ? `${Math.max(12, splitMetrics.audioLeft || (rootLeft - splitMetrics.gap - audioWidth))}px`
              : `${rootLeft - gap - audioWidth}px`;
            qAudioCard.style.right = "auto";
            qAudioCard.style.top = splitMetrics
              ? `${rootTop + Math.max(0, Math.min(34, rootHeight * 0.08))}px`
              : `${rootTop + Math.max(12, rootHeight * 0.16)}px`;
            qAudioCard.style.transform = "none";
            const audioRect = qAudioCard.getBoundingClientRect();
            const audioCoreRect = qPlayButton && qPlayButton.getBoundingClientRect().width
              ? qPlayButton.getBoundingClientRect()
              : audioRect;
            if (splitMetrics) {
              positionQuestionLine(
                qConnectorAudio,
                shellPoint(rootRect, 0, 0.34),
                shellPoint(audioCoreRect, 0.5, 0.5),
              );
            } else {
              positionQuestionLine(
                qConnectorAudio,
                shellPoint(rootRect, 0, 0.42),
                shellPoint(audioCoreRect, 0.5, 0.5),
              );
            }
          }
          if (isQuestionCardInLayout(qQuestionCard)) {
            let questionWidth = 0;
            if (splitMetrics) {
              const splitAudioHeight = isQuestionCardInLayout(qAudioCard)
                ? Math.max(126, questionUnscaleLayoutValue(qAudioCard.getBoundingClientRect().height || qAudioCard.offsetHeight || 126))
                : 0;
              const splitQuestionTop = rootTop + (splitAudioHeight ? splitAudioHeight + 30 : 0);
              questionWidth = Math.max(320, splitMetrics.rightWidth);
              qQuestionCard.style.width = `${questionWidth}px`;
              qQuestionCard.style.maxWidth = `${questionWidth}px`;
              qQuestionCard.style.left = `${splitMetrics.rightLeft}px`;
              qQuestionCard.style.top = `${splitQuestionTop}px`;
              qQuestionCard.style.maxHeight = `${Math.max(260, layoutViewportHeight - splitQuestionTop - 42)}px`;
              qQuestionCard.style.overflowY = "auto";
            } else {
              const focusFitActive = questionManualFocusTarget === qQuestionCard;
              const stageViewportWidth = stageNode ? questionUnscaleLayoutValue(stageNode.clientWidth) : questionUnscaleLayoutValue(window.innerWidth || shellWidth || 980);
              const focusSafeInline = Math.max(48, Math.min(144, stageViewportWidth * 0.12));
              const focusMaxWidth = focusFitActive
                ? Math.max(560, stageViewportWidth - focusSafeInline)
                : Number.POSITIVE_INFINITY;
              const inputQuestion = qQuestionCard.classList.contains("is-input-question");
              const questionBaseWidth = Math.min(rootWidth || QUESTION_ROOT_BASE_WIDTH, QUESTION_ROOT_BASE_WIDTH);
              const questionMaxWidth = Math.max(320, (questionBaseWidth + 10) * (inputQuestion ? 1.2 : 1));
              const questionAvailableWidth = Math.max(320, Math.min(shellWidth - 72, focusMaxWidth));
              questionWidth = Math.min(questionMaxWidth, questionAvailableWidth);
              qQuestionCard.style.width = `${questionWidth}px`;
              qQuestionCard.style.removeProperty("max-width");
              qQuestionCard.style.left = `${rootLeft + rootWidth / 2 - questionWidth / 2}px`;
              qQuestionCard.style.top = `${rootTop + rootHeight + Math.max(48, gap * 0.9)}px`;
              qQuestionCard.style.removeProperty("max-height");
              qQuestionCard.style.removeProperty("overflow-y");
            }
            qQuestionCard.style.right = "auto";
            qQuestionCard.style.transform = "none";
            const questionRect = qQuestionCard.getBoundingClientRect();
            if (splitMetrics) {
              positionQuestionLine(
                qConnectorQuestion,
                shellPoint(rootRect, 1, 0.28),
                shellPoint(questionRect, 0, 0.28),
              );
            } else {
              positionQuestionLine(
                qConnectorQuestion,
                shellPoint(rootRect, 0.5, 1),
                shellPoint(questionRect, 0.5, 0),
              );
            }
          }
          if (isQuestionCardInLayout(qInfoCard) && isQuestionCardInLayout(qQuestionCard)) {
            const questionRect = qQuestionCard.getBoundingClientRect();
            const questionLeft = questionUnscaleLayoutValue(questionRect.left - shellRect.left);
            const questionTop = questionUnscaleLayoutValue(questionRect.top - shellRect.top);
            const questionWidth = questionUnscaleLayoutValue(questionRect.width);
            const questionHeight = questionUnscaleLayoutValue(questionRect.height);
            const infoWidth = splitMetrics
              ? Math.max(300, Math.min(questionWidth, splitMetrics.rightWidth))
              : questionAnswerInfoWidth(rootWidth, questionWidth);
            qInfoCard.style.width = `${infoWidth}px`;
            qInfoCard.style.left = splitMetrics
              ? `${questionLeft}px`
              : `${questionLeft - gap - infoWidth}px`;
            qInfoCard.style.top = splitMetrics
              ? `${questionTop + questionHeight + 18}px`
              : `${questionTop + Math.max(8, questionHeight * 0.16)}px`;
            qInfoCard.style.right = "auto";
            qInfoCard.style.transform = "none";
            const infoRect = qInfoCard.getBoundingClientRect();
            if (splitMetrics) {
              positionQuestionLine(
                qConnectorInfo,
                shellPoint(questionRect, 0.08, 1),
                shellPoint(infoRect, 0.08, 0),
              );
            } else {
              positionQuestionLine(
                qConnectorInfo,
                shellPoint(infoRect, 1, 0.28),
                shellPoint(questionRect, 0, 0.34),
              );
            }
          }
          const liveCards = questionCameraNodes();
          const requiredBottom = liveCards.reduce((bottom, node) => {
            const rect = node.getBoundingClientRect();
            return Math.max(bottom, questionUnscaleLayoutValue(rect.bottom - shellRect.top));
          }, questionUnscaleLayoutValue(rootRect.bottom - shellRect.top));
          const hasQuestionCard = isQuestionCardInLayout(qQuestionCard);
          const bottomReserve = hasQuestionCard
            ? Math.max(profileActive ? 500 : 420, Math.min(profileActive ? 1280 : 1100, layoutViewportHeight * (profileActive ? 1.18 : 1.05)))
            : Math.max(profileActive ? 220 : 180, Math.min(profileActive ? 620 : 520, layoutViewportHeight * (profileActive ? 0.68 : 0.58)));
          if (liveCards.some((node) => node !== qRootCard)) {
            shellNode.style.setProperty("--q-layout-height", `${Math.ceil(requiredBottom + bottomReserve)}px`);
          } else {
            shellNode.style.removeProperty("--q-layout-height");
          }
          repositionActiveQuestionRootInfo();
          positionQuestionPictureAnswerCards();
          positionQuestionSelectConnectors();
          restoreQuestionLayoutRootAnchor(layoutAnchorSnapshot);
          restoreQuestionCamera();
          layoutCompleted = true;
        } finally {
          if (layoutCompleted && canUseLayoutCache) {
            questionSideLayoutCacheKey = layoutCacheKey;
          } else if (!canUseLayoutCache) {
            questionSideLayoutCacheKey = "";
          }
          if (hadCameraTransform) {
            restoreQuestionCamera();
          }
          if (stageNode) {
            stageNode.classList.remove("is-question-fit-measuring");
          }
        }
      }

      const orderQuestionOptionsByPreviousRender = (options = [], previousOrder = []) => {
        const byKey = new Map();
        options.forEach((option) => {
          const key = questionAnswerKey(option);
          if (key && !byKey.has(key)) {
            byKey.set(key, option);
          }
        });
        const used = new Set();
        const ordered = [];
        previousOrder.forEach((option) => {
          const key = questionAnswerKey(option);
          if (!key || used.has(key) || !byKey.has(key)) {
            return;
          }
          used.add(key);
          ordered.push(byKey.get(key));
        });
        options.forEach((option) => {
          const key = questionAnswerKey(option);
          if (!key || used.has(key)) {
            return;
          }
          used.add(key);
          ordered.push(option);
        });
        return ordered;
      };

      const renderQuestionChoices = (question, state = {}) => {
        if (!qChoiceList) {
          return [];
        }
        const previousOrder = state.preserveOrder
          ? Array.from(qChoiceList.querySelectorAll("[data-answer]"))
            .map((button) => clean(button.dataset ? button.dataset.answer : ""))
            .filter(Boolean)
          : [];
        qChoiceList.innerHTML = "";
        clearQuestionGuidanceBranches(1);
        questionGuidanceNodeMap.clear();
        questionGuidanceUnlockedPaths.clear();
        questionGuidanceUnlockedAnswerIndex.clear();
        questionGuidanceUnlockedAnswerValue.clear();
        questionGuidancePinnedPaths.clear();
        const guide = isQuestionGuideItem(question) || Boolean(state.guide);
        const selectMode = isQuestionSelectItem(question);
        qChoiceList.classList.toggle("is-select-token-grid", false);
        if (selectMode) {
          qChoiceList.classList.remove("is-picture-question-branch");
        }
        if (selectMode) {
          updateQuestionSelectProgressCard(question);
          return questionSelectAnswerTokens(question);
        }
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
          button.className = "ft-q-choice";
          if (guide) {
            button.classList.add("is-guide");
          } else {
            button.type = "button";
          }
          button.dataset.answer = option;
          button.dataset.slot = String(index + 1).padStart(2, "0");
          const guideNode = questionGuidanceTreeEntryForOption(question, option, index);
          const hasExtraBranch = questionGuidanceNodeHasBranch(guideNode);
          const extraBranchReady = hasExtraBranch && (guide || (state.locked && state.selectedOk));
          if (questionAnswerKey(option) === questionAnswerKey(state.selectedValue)) {
            button.classList.add(state.selectedOk ? "is-correct" : "is-wrong");
          }
          if (state.locked && !extraBranchReady) {
            button.disabled = true;
          }
          const copy = document.createElement("span");
          copy.className = "ft-q-choice-copy";
          const kicker = document.createElement("span");
          kicker.className = "ft-q-choice-kicker";
          kicker.textContent = `${guide ? "Data" : "Choice"} ${String(index + 1).padStart(2, "0")}`;
          const label = document.createElement("span");
          label.className = "ft-q-choice-label";
          label.textContent = option;
          copy.append(kicker, label);
          button.appendChild(copy);
          const tail = document.createElement("span");
          tail.className = "ft-q-choice-tail";
          const signal = document.createElement("span");
          signal.className = "ft-q-choice-signal";
          signal.setAttribute("aria-hidden", "true");
          signal.innerHTML = "<i></i><i></i><i></i>";
          tail.appendChild(signal);
          if (shouldQuestionAnswerAudioShowButton(question, option) && questionCardAnswerAudioClip(question, option)) {
            const audioButton = document.createElement("span");
            audioButton.className = "ft-q-answer-audio";
            audioButton.textContent = "Play";
            audioButton.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();
              stopQuestionAudio();
              stopGrammarAudio();
              if (typeof stopQuestionCardActiveAudio === "function") {
                stopQuestionCardActiveAudio();
              }
              void playQuestionCardClip(questionCardAnswerAudioClip(question, option));
            });
            tail.appendChild(audioButton);
          }
          button.appendChild(tail);
          if (!guide && !extraBranchReady) {
            button.addEventListener("click", () => checkQuestionAnswer(option, button));
          }
          if (extraBranchReady) {
            const guidePath = `choice-${index}`;
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
          qChoiceList.appendChild(button);
        });
        return ordered;
      };

      const clearQuestionInputBranchTrigger = () => {
        if (!qInputRow) {
          return;
        }
        const trigger = qInputRow.querySelector("[data-q-input-branch]");
        if (trigger && trigger.parentNode) {
          trigger.parentNode.removeChild(trigger);
        }
      };

      const renderQuestionInputBranchTrigger = (question, enabled = false) => {
        clearQuestionInputBranchTrigger();
        if (!enabled || !qInputRow || !question) {
          return false;
        }
        const guideNode = questionGuidanceTreeEntryForOption(question, question.answer, 0);
        if (!questionGuidanceNodeHasBranch(guideNode)) {
          return false;
        }
        const path = "input-0";
        questionGuidanceNodeMap.set(path, guideNode);
        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "ft-q-action ft-q-input-branch has-guidance-children";
        trigger.textContent = "Linked branch";
        trigger.dataset.qInputBranch = "1";
        trigger.dataset.answer = question.answer || "";
        trigger.dataset.slot = "01";
        trigger.dataset.guidancePath = path;
        trigger.dataset.guidanceDepth = "0";
        trigger.setAttribute("aria-expanded", "false");
        appendQuestionGuidanceChildBadge(trigger);
        wireQuestionGuidanceCard(trigger);
        qInputRow.appendChild(trigger);
        return true;
      };

      const ensureQuestionPictureAnswerLayer = () => {
        if (!shellNode) {
          return null;
        }
        if (!questionPictureAnswerLayer) {
          questionPictureAnswerLayer = document.createElement("div");
          questionPictureAnswerLayer.className = "ft-q-picture-answer-layer";
          questionPictureAnswerLayer.addEventListener("click", (event) => {
            const card = event.target && event.target.closest
              ? event.target.closest(".has-guidance-children")
              : null;
            if (card && questionPictureAnswerLayer.contains(card) && openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: true })) {
              event.preventDefault();
              event.stopPropagation();
            }
          });
          questionPictureAnswerLayer.addEventListener("pointerover", (event) => {
            if (isQuestionMobileFlow()) {
              return;
            }
            const card = event.target && event.target.closest
              ? event.target.closest(".has-guidance-children")
              : null;
            if (card && questionPictureAnswerLayer.contains(card)) {
              scheduleQuestionGuidanceOpen(card, 28);
            }
          });
          questionPictureAnswerLayer.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") {
              return;
            }
            const card = event.target && event.target.closest
              ? event.target.closest(".has-guidance-children")
              : null;
            if (card && questionPictureAnswerLayer.contains(card) && openQuestionGuidanceCard(card, { forceOpen: true, preservePinned: false, pan: true })) {
              event.preventDefault();
              event.stopPropagation();
            }
          });
          shellNode.appendChild(questionPictureAnswerLayer);
        }
        return questionPictureAnswerLayer;
      };

      function questionMobilePicturePromptActive() {
        return Boolean(
          questionRootInfoCard
          && questionRootInfoCard.classList.contains("is-question")
          && questionPanelLive(questionRootInfoCard)
        );
      }

      function ensureQuestionMobilePicturePager() {
        if (!shellNode) {
          return null;
        }
        if (!questionMobilePicturePager) {
          questionMobilePicturePager = document.createElement("div");
          questionMobilePicturePager.className = "ft-q-mobile-picture-pager";
          questionMobilePicturePager.setAttribute("role", "toolbar");
          questionMobilePicturePager.setAttribute("aria-label", "Linking question pages");
          questionMobilePicturePager.innerHTML = `
            <button class="ft-q-mobile-picture-page-btn" type="button" data-mobile-picture-page="prompt">Question</button>
            <button class="ft-q-mobile-picture-page-btn" type="button" data-mobile-picture-page="answers">Answers</button>
            <button class="ft-q-mobile-picture-page-btn" type="button" data-mobile-picture-page="link" hidden>Link</button>
            <button class="ft-q-mobile-picture-page-btn is-back" type="button" data-mobile-picture-action="back" hidden>Back</button>
            <button class="ft-q-mobile-picture-page-btn is-next" type="button" data-mobile-picture-action="next" disabled>Next</button>
          `;
          questionMobilePicturePager.addEventListener("click", (event) => {
            const button = event.target && event.target.closest
              ? event.target.closest(".ft-q-mobile-picture-page-btn")
              : null;
            if (!button || !questionMobilePicturePager.contains(button)) {
              return;
            }
            event.preventDefault();
            event.stopPropagation();
            const action = clean(button.dataset.mobilePictureAction || "");
            if (action === "back") {
              closeQuestionMobileGuidancePage();
              return;
            }
            if (action === "next") {
              const nextButton = questionRootInfoPromptNode("[data-root-info-next]");
              if (nextButton && !nextButton.disabled) {
                nextButton.click();
              }
              return;
            }
            const page = clean(button.dataset.mobilePicturePage || "");
            if (page) {
              setQuestionMobilePicturePage(page);
            }
          });
          shellNode.insertBefore(questionMobilePicturePager, shellNode.firstElementChild || null);
        }
        return questionMobilePicturePager;
      }

      function setQuestionMobilePicturePage(page = "answers") {
        let nextPage = clean(page || "answers").toLowerCase();
        if (!["prompt", "answers", "link"].includes(nextPage)) {
          nextPage = "answers";
        }
        if (nextPage === "link" && !questionMobileGuidanceStack.length) {
          nextPage = "answers";
        }
        questionMobilePicturePage = nextPage;
        if (shellNode) {
          shellNode.dataset.mobilePicturePage = nextPage;
        }
        if (questionPictureAnswerLayer) {
          questionPictureAnswerLayer.dataset.mobilePage = nextPage;
          questionPictureAnswerLayer.classList.toggle("is-mobile-guidance-page", nextPage === "link" && questionMobileGuidanceStack.length > 0);
        }
        syncQuestionMobilePicturePager();
      }

      function syncQuestionMobilePicturePager() {
        const pager = ensureQuestionMobilePicturePager();
        const active = Boolean(
          pager
          && questionModeActive
          && isQuestionMobileFlow()
          && questionMobilePicturePromptActive()
          && questionPictureAnswerActive
        );
        if (!active) {
          if (pager) {
            pager.classList.remove("is-live");
          }
          if (shellNode) {
            delete shellNode.dataset.mobilePicturePage;
          }
          if (questionPictureAnswerLayer) {
            delete questionPictureAnswerLayer.dataset.mobilePage;
            questionPictureAnswerLayer.classList.remove("is-mobile-guidance-page");
          }
          return;
        }
        if (questionMobilePicturePage === "link" && !questionMobileGuidanceStack.length) {
          questionMobilePicturePage = "answers";
        }
        if (!questionMobilePicturePage) {
          questionMobilePicturePage = "answers";
        }
        if (shellNode) {
          shellNode.dataset.mobilePicturePage = questionMobilePicturePage;
        }
        if (questionPictureAnswerLayer) {
          questionPictureAnswerLayer.dataset.mobilePage = questionMobilePicturePage;
          questionPictureAnswerLayer.classList.toggle("is-mobile-guidance-page", questionMobilePicturePage === "link" && questionMobileGuidanceStack.length > 0);
        }
        pager.classList.add("is-live");
        pager.querySelectorAll("[data-mobile-picture-page]").forEach((button) => {
          const page = clean(button.dataset.mobilePicturePage || "");
          const isLink = page === "link";
          button.hidden = isLink && !questionMobileGuidanceStack.length;
          button.classList.toggle("is-active", page === questionMobilePicturePage && (!isLink || questionMobileGuidanceStack.length));
          button.setAttribute("aria-pressed", page === questionMobilePicturePage ? "true" : "false");
        });
        const backButton = pager.querySelector("[data-mobile-picture-action='back']");
        if (backButton) {
          backButton.hidden = !questionMobileGuidanceStack.length;
          backButton.disabled = !questionMobileGuidanceStack.length;
        }
        const nextButton = pager.querySelector("[data-mobile-picture-action='next']");
        const promptNext = questionRootInfoPromptNode("[data-root-info-next]");
        if (nextButton) {
          nextButton.disabled = !promptNext || promptNext.disabled;
        }
      }

      function resetQuestionMobilePicturePager() {
        questionMobileGuidanceStack = [];
        questionMobilePicturePage = "answers";
        if (questionMobilePicturePager) {
          questionMobilePicturePager.classList.remove("is-live");
        }
        if (shellNode) {
          delete shellNode.dataset.mobilePicturePage;
        }
        if (questionPictureAnswerLayer) {
          delete questionPictureAnswerLayer.dataset.mobilePage;
          questionPictureAnswerLayer.classList.remove("is-mobile-guidance-page");
          questionPictureAnswerLayer.querySelectorAll(".ft-q-mobile-guidance-page").forEach((page) => page.remove());
        }
      }

      function questionMobileGuidanceTitle(parentCard, node, path) {
        const cardLabel = parentCard && parentCard.querySelector
          ? parentCard.querySelector(".ft-q-picture-answer-label, .ft-q-choice-label, .ft-q-choice-copy")
          : null;
        return preserveQuestionText(cardLabel && cardLabel.textContent)
          || preserveQuestionText(node && (node.title || node.question || node.main || node.body))
          || clean(path)
          || "Linked branch";
      }

      function closeQuestionMobileGuidancePage() {
        if (!questionMobileGuidanceStack.length) {
          setQuestionMobilePicturePage("answers");
          return;
        }
        questionMobileGuidanceStack.pop();
        const previous = questionMobileGuidanceStack[questionMobileGuidanceStack.length - 1];
        if (!previous) {
          if (questionPictureAnswerLayer) {
            questionPictureAnswerLayer.querySelectorAll(".ft-q-mobile-guidance-page").forEach((page) => page.remove());
          }
          setQuestionMobilePicturePage("answers");
          return;
        }
        renderQuestionMobileGuidancePage(previous, { noEnter: true, fromHistory: true });
        setQuestionMobilePicturePage("link");
      }

      function openQuestionMobileGuidancePage(parentCard, node, path, depth = 1, options = {}) {
        const layer = questionPictureAnswerLayer || ensureQuestionPictureAnswerLayer();
        if (!layer || !node) {
          return false;
        }
        const safePath = clean(path || "link");
        const safeDepth = Math.max(1, Math.floor(Number(depth) || 1));
        questionGuidanceNodeMap.set(safePath, node);
        cancelQuestionGuidanceClose(safePath);
        layer.classList.remove("is-preparing");
        layer.classList.add("is-live");
        questionPictureAnswerActive = true;
        const entry = {
          parentCard,
          node,
          path: safePath,
          depth: safeDepth,
          title: questionMobileGuidanceTitle(parentCard, node, safePath),
        };
        if (!options.fromHistory) {
          const existingIndex = questionMobileGuidanceStack.findIndex((item) => item && item.path === safePath);
          if (existingIndex >= 0) {
            questionMobileGuidanceStack = questionMobileGuidanceStack.slice(0, existingIndex + 1);
            questionMobileGuidanceStack[existingIndex] = entry;
          } else if (safeDepth <= 1 && !safePath.includes(".")) {
            questionMobileGuidanceStack = [entry];
          } else {
            questionMobileGuidanceStack.push(entry);
          }
        }
        if (parentCard && parentCard.classList) {
          parentCard.classList.add("is-guidance-open");
          parentCard.setAttribute("aria-expanded", "true");
        }
        renderQuestionMobileGuidancePage(entry, options);
        setQuestionMobilePicturePage("link");
        scheduleQuestionMobilePanelsSync("question");
        return true;
      }
