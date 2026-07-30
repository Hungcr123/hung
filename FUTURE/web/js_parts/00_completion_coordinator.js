      const handleSpaceCompletion = (responsePayload = {}, lessonContext = {}, ui = {}) => {
        const response = responsePayload && typeof responsePayload === "object" ? responsePayload : {};
        const board = response.space_leaderboard && typeof response.space_leaderboard === "object"
          ? response.space_leaderboard
          : {};
        const hasBoardPayload = Boolean(response.space_leaderboard && typeof response.space_leaderboard === "object");
        const context = lessonContext && typeof lessonContext === "object" ? lessonContext : {};
        const normalizeType = (value = "") => {
          const safe = String(value || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
          if (["space_v", "space_w", "space_q", "space_p", "space_s", "space_l"].includes(safe)) return safe;
          if (safe === "v" || safe === "spacev") return "space_v";
          if (safe === "w" || safe === "spacew") return "space_w";
          if (safe === "q" || safe === "spaceq") return "space_q";
          if (safe === "p" || safe === "spacep") return "space_p";
          if (safe === "s" || safe === "spaces") return "space_s";
          if (safe === "l" || safe === "spacel") return "space_l";
          return "space_v";
        };
        const sourcePath = String(context.sourcePath || "").split(/[?#]/, 1)[0].toLowerCase();
        const suffixType = /\.space_w$/i.test(sourcePath)
          ? "space_w"
          : (/\.space_q$/i.test(sourcePath)
            ? "space_q"
            : (/\.space_p$/i.test(sourcePath)
              ? "space_p"
              : (/\.space_l$/i.test(sourcePath)
                ? "space_l"
                : (/\.space_s$/i.test(sourcePath) ? "space_s" : ""))));
        const boardType = normalizeType(response.leaderboard_type || board.type || context.boardType || suffixType || context.fallbackType);
        const recorded = Boolean(response.recorded || board.recorded);
        const duplicate = Boolean(response.duplicate || board.duplicate || response.deduplicated);
        const completionConfirmed = Boolean(
          context.completionAlreadyConfirmed ||
          response.completion_confirmed ||
          response.database_event_committed ||
          response.logged ||
          response.deduplicated,
        );
        const shouldOpenTop = Boolean(
          context.allowOpen !== false &&
          completionConfirmed &&
          (recorded || duplicate || hasBoardPayload || context.completionAlreadyConfirmed || response.deduplicated) &&
          boardType !== "space_v",
        );
        if (recorded && typeof ui.invalidateLeaderboard === "function") {
          ui.invalidateLeaderboard(boardType);
        }
        if (shouldOpenTop && typeof ui.openTopLeaderboard === "function") {
            ui.openTopLeaderboard(boardType, response);
        }
        return { boardType, recorded, duplicate, completionConfirmed, shouldOpenTop };
      };

      // Added 2026-07-24: first completion stays green; a later active/review run or second completion is orange.
      const resolveLessonProgressRepeatState = (source = {}) => {
        const state = source && typeof source === "object" ? source : {};
        const completedRuns = Math.max(0, Math.floor(Number(state.completedRuns || 0) || 0));
        return Boolean(
          completedRuns > 1 ||
          (
            completedRuns > 0 &&
            !state.isCompleteDisplay &&
            (state.activeRun || state.relearning || state.reviewing || state.canShowPartial)
          )
        );
      };

      const resolveSpaceRunNavigation = (record = {}, spaceType = "") => {
        const source = record && typeof record === "object" ? record : {};
        const state = source.state && typeof source.state === "object" ? source.state : {};
        const normalizeSpace = (value = "") => {
          const safe = String(value || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
          if (safe === "v" || safe === "spacev" || safe === "space_v") return "space_v";
          if (safe === "w" || safe === "spacew" || safe === "space_w") return "space_w";
          if (safe === "q" || safe === "spaceq" || safe === "space_q") return "space_q";
          if (safe === "p" || safe === "spacep" || safe === "space_p") return "space_p";
          if (safe === "l" || safe === "spacel" || safe === "space_l") return "space_l";
          if (safe === "s" || safe === "spaces" || safe === "space_s") return "space_s";
          return safe;
        };
        const number = (...values) => values.reduce((best, value) => {
          const next = Math.max(0, Math.floor(Number(value) || 0));
          return Math.max(best, next);
        }, 0);
        const flag = (...values) => values.some((value) => {
          if (value === true || value === 1) return true;
          const normalized = String(value ?? "").trim().toLowerCase();
          return normalized === "true" || normalized === "1" || normalized === "yes";
        });
        const space = normalizeSpace(spaceType || source.space || state.space);
        const runId = String(source.runId || source.run_id || state.runId || state.run_id || "").trim();
        const activeRun = flag(source.activeRun, source.active_run, state.activeRun, state.active_run);
        const reviewing = flag(source.reviewing, source.reviewRun, state.reviewing, state.reviewRun, state.reviewModeActive);
        const completionMarkers = ["complete", "completed", "lessonComplete", "lessonCompletionSent", "vocabComplete"];
        let currentRunComplete = completionMarkers.some((key) => flag(source[key], state[key]));
        let total = number(source.nodeCount, state.nodeCount);
        let done = number(source.nodeIndex, state.currentIndex, state.nodeIndex, state.index);
        if (space === "space_w") {
          total = number(source.progressTotal, state.progressTotal, total ? total * 2 : 0);
          done = number(source.progressDone, state.progressDone, done);
          currentRunComplete = currentRunComplete || flag(source.reviewFinished, state.reviewFinished);
        } else if (space === "space_v") {
          const learned = Array.isArray(state.learned) ? new Set(state.learned.map((item) => String(item || "").trim().toLowerCase()).filter(Boolean)).size : 0;
          done = number(source.learnedCount, source.learned_count, state.learnedCount, state.learned_count, learned);
        } else if (space === "space_q") {
          total = number(total, state.questionTotal, state.totalQuestions);
          done = number(done, state.questionDone, state.completedQuestions, state.questionsDone);
        } else if (["space_p", "space_l", "space_s"].includes(space)) {
          total = number(total, state.totalSegments, state.segmentTotal, state.totalTokens, state.tokenTotal);
          done = number(done, state.completedSegments, state.segmentDone, state.completedTokens, state.tokenDone);
        }
        const completeByCount = Boolean(total && done >= total);
        if (completeByCount) {
          currentRunComplete = true;
        }
        // An identified active run owns navigation even when lifetime-complete markers are still present.
        // Added 2026-07-26: old Space_V saves can keep activeRun=true after the
        // final word; the completed count must close that stale run on resume.
        if (activeRun && !(space === "space_v" && completeByCount)) {
          currentRunComplete = false;
        }
        const completedRuns = number(
          source.mine,
          source.completedRuns,
          source.completed_runs,
          state.completedRuns,
          state.completed_runs,
        );
        const checkpointAvailable = Boolean(
          done > 0 ||
          reviewing ||
          (Array.isArray(state.queue) && state.queue.length) ||
          (state.nodeProgress && typeof state.nodeProgress === "object" && Object.keys(state.nodeProgress).length),
        );
        const currentRunExists = Boolean(
          activeRun ||
          (!currentRunComplete && runId) ||
          (!currentRunComplete && checkpointAvailable),
        );
        const resumeAvailable = Boolean(currentRunExists && !currentRunComplete);
        const lifetimeComplete = Boolean(completedRuns > 0 || currentRunComplete);
        return {
          space,
          runId,
          activeRun,
          currentRunExists,
          currentRunComplete,
          lifetimeComplete,
          completedRuns,
          done,
          total,
          resumeAvailable,
          navigationMode: resumeAvailable ? "study" : (lifetimeComplete ? "completed" : "fresh"),
        };
      };

      if (typeof module !== "undefined" && module.exports) {
        module.exports = { handleSpaceCompletion, resolveLessonProgressRepeatState, resolveSpaceRunNavigation };
      }
