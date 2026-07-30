

      const renderSharedWorld = (payload = {}) => {
        if (!worldPlayers || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        if (sharedWorldMapMode === "training") {
          return;
        }
        const world = payload.world && typeof payload.world === "object" ? payload.world : payload;
        const players = Array.isArray(world.players) ? world.players : [];
        const me = clean(world.me || activeWorldUsername()).toLowerCase();
        sharedWorldActiveBattlePairs = Array.isArray(world.active_battles || world.activeBattles)
          ? (world.active_battles || world.activeBattles)
          : [];
        const playingKeys = new Set();
        sharedWorldActiveBattlePairs.forEach((pair) => {
          const row = pair && typeof pair === "object" ? pair : {};
          (Array.isArray(row.players) ? row.players : []).forEach((name) => {
            const key = clean(name).toLowerCase();
            if (key) {
              playingKeys.add(key);
            }
          });
        });
        if (world.keyboard_pass || world.keyboardPass) {
          sharedWorldKeyboardPass = normalizeSharedWorldKeyboardPass(world.keyboard_pass || world.keyboardPass || {});
          renderSharedWorldKeyboardPass();
        }
        const seen = new Set();
        sharedWorldRoster.clear();
        players.forEach((player) => {
          const username = clean(player.username);
          if (!username) {
            return;
          }
          const key = username.toLowerCase();
          seen.add(key);
          let node = sharedWorldNodes.get(key);
          if (!node) {
            node = createSharedWorldNode(username);
            sharedWorldNodes.set(key, node);
            worldPlayers.appendChild(node);
          }
          const displayName = clean(player.display_name || username);
          const currentX = sharedWorldClamp(player.x != null ? player.x : player.tx);
          const currentY = sharedWorldClamp(player.y != null ? player.y : player.ty);
          const targetX = sharedWorldClamp(player.tx != null ? player.tx : currentX);
          const targetY = sharedWorldClamp(player.ty != null ? player.ty : currentY);
          sharedWorldRoster.set(key, {
            username,
            displayName,
            gender: clean(player.gender || "other").toLowerCase() || "other",
            topTitles: Array.isArray(player.top_titles) ? player.top_titles : [],
            monthlyBadge: player.monthly_badge && typeof player.monthly_badge === "object" ? player.monthly_badge : {},
            isPlaying: playingKeys.has(key),
            x: currentX,
            y: currentY,
            tx: targetX,
            ty: targetY,
          });
          node.dataset.username = username;
          node.dataset.displayName = displayName;
          node.title = key === me ? "This is you" : `Select ${displayName}`;
          let pos = sharedWorldPositions.get(key);
          if (!pos) {
            pos = { x: currentX, y: currentY, tx: targetX, ty: targetY };
            sharedWorldPositions.set(key, pos);
            applySharedWorldNodePosition(node, pos.x, pos.y);
          } else {
            if (!sharedWorldUseLocalSelfMotion(key)) {
              const targetChanged = Math.hypot(sharedWorldClamp(pos.tx, pos.x) - targetX, sharedWorldClamp(pos.ty, pos.y) - targetY) > 0.002;
              if (targetChanged) {
                setSharedWorldOrthogonalPath(key, { x: targetX, y: targetY });
              } else {
                pos.tx = targetX;
                pos.ty = targetY;
              }
            }
          }
          node.classList.toggle("is-me", key === me);
          node.classList.toggle("is-target-selected", key === sharedWorldSelectedTargetKey && key !== me);
          node.classList.toggle("is-playing", playingKeys.has(key));
          renderSharedWorldName(node, displayName, player.gender || "other");
          renderSharedWorldLevel(node, player.character_level || player.characterLevel || {});
          renderSharedWorldTopMeta(node, player);
          const bubble = node.querySelector(".ft-world-bubble");
          const chat = clean(player.chat || "");
          if (bubble) {
            bubble.textContent = chat;
            const chatting = Boolean(chat && sharedWorldRecent(player.chat_at));
            bubble.classList.toggle("is-visible", chatting);
            node.classList.toggle("is-chatting", chatting);
          }
          const action = clean(player.action || "").toLowerCase();
          const actionAt = clean(player.action_at || "");
          const actionActive = sharedWorldActions.includes(action) && sharedWorldRecent(actionAt, 3600);
          const actionKey = actionActive ? `${action}:${actionAt}` : "";
          if (node.dataset.actionKey !== actionKey) {
            sharedWorldActions.forEach((item) => node.classList.remove(`is-action-${item}`));
            if (actionActive) {
              void node.offsetWidth;
              node.classList.add(`is-action-${action}`);
            }
            node.dataset.actionKey = actionKey;
          } else if (actionActive) {
            node.classList.add(`is-action-${action}`);
          } else {
            sharedWorldActions.forEach((item) => node.classList.remove(`is-action-${item}`));
          }
        });
        Array.from(sharedWorldNodes.entries()).forEach(([key, node]) => {
          if (!seen.has(key)) {
            node.remove();
            sharedWorldNodes.delete(key);
            sharedWorldPositions.delete(key);
            sharedWorldPathQueues.delete(key);
          }
        });
        if (sharedWorldSelectedTargetKey && !seen.has(sharedWorldSelectedTargetKey)) {
          if (sharedWorldSelectedTargetKey !== "witch") {
            sharedWorldSelectedTargetKey = "";
          }
        }
        syncSharedWorldBattleLinks();
        syncSharedWorldNpcRoster();
        renderSharedWorldSelectedTarget();
        renderSharedWorldPositionPoint();
        if (sharedWorldNeedInitialCenter) {
          const self = sharedWorldRoster.get(me);
          if (self) {
            window.requestAnimationFrame(() => centerSharedWorldViewportOn(self.x, self.y, false));
            sharedWorldNeedInitialCenter = false;
          }
        }
        if (sharedWorldFollowSelf) {
          scheduleSharedWorldFollowCenter();
        }
        scheduleSharedWorldMotion();
        updateSharedWorldFollowTarget();
      };

      const clearSharedWorldReconnect = () => {
        sharedWorldReconnectAttempts = 0;
        if (sharedWorldReconnectTimer) {
          window.clearTimeout(sharedWorldReconnectTimer);
          sharedWorldReconnectTimer = 0;
        }
      };

      const scheduleSharedWorldReconnect = (message = "") => {
        if (!authToken || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const safeMessage = clean(message);
        if (safeMessage) {
          setSharedWorldStatus(`${safeMessage} Reconnecting...`, "error");
        }
        if (sharedWorldReconnectTimer) {
          return;
        }
        const delay = Math.min(4200, 700 + (sharedWorldReconnectAttempts * 520));
        sharedWorldReconnectAttempts += 1;
        sharedWorldReconnectTimer = window.setTimeout(() => {
          sharedWorldReconnectTimer = 0;
          void refreshSharedWorld();
          void refreshSharedWorldBattle();
        }, delay);
      };

      const refreshSharedWorld = async () => {
        if (!authToken || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        if (sharedWorldMapMode === "training") {
          return;
        }
        const now = Date.now();
        if (sharedWorldLoading && now - sharedWorldLoadingAt < 900) {
          return;
        }
        sharedWorldLoading = true;
        sharedWorldLoadingAt = now;
        const requestSeq = ++sharedWorldRequestSeq;
        try {
          const response = await fetchAuthJson(`/world/state${activeWorldActorQuery()}`, { timeoutMs: 0, silentTimeout: true });
          if (requestSeq !== sharedWorldRequestSeq || !worldModal || !worldModal.classList.contains("is-open")) {
            return;
          }
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
          clearSharedWorldReconnect();
          if (!sharedWorldBattlePollingTimer && !(worldBattleResult && worldBattleResult.classList.contains("is-open"))) {
            void refreshSharedWorldBattle();
          }
        } catch (error) {
          scheduleSharedWorldReconnect(error && error.message ? error.message : "Could not load shared world.");
        } finally {
          if (requestSeq === sharedWorldRequestSeq) {
            sharedWorldLoading = false;
            sharedWorldLoadingAt = 0;
          }
        }
      };

      const stopSharedWorldPolling = () => {
        if (sharedWorldPollingTimer) {
          window.clearInterval(sharedWorldPollingTimer);
          sharedWorldPollingTimer = 0;
        }
      };

      const stopSharedWorldBattlePolling = () => {
        if (sharedWorldBattlePollingTimer) {
          window.clearInterval(sharedWorldBattlePollingTimer);
          sharedWorldBattlePollingTimer = 0;
        }
      };

      const startSharedWorldPolling = () => {
        stopSharedWorldPolling();
        sharedWorldPollingTimer = window.setInterval(() => {
          void refreshSharedWorld();
        }, 520);
      };

      const startSharedWorldBattlePolling = () => {
        stopSharedWorldBattlePolling();
        sharedWorldBattlePollingTimer = window.setInterval(() => {
          void refreshSharedWorldBattle();
        }, 520);
      };

      const openSharedWorld = () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de mo shared world.");
          return;
        }
        if (worldModal) {
          worldModal.classList.add("is-open");
          worldModal.setAttribute("aria-hidden", "false");
        }
        if (typeof requestAnyFullscreen === "function") {
          void requestAnyFullscreen();
        }
        hideSharedWorldMoveMarker(false);
        sharedWorldPathQueues.clear();
        sharedWorldNeedInitialCenter = true;
        loadSharedWorldFollowPreference();
        setMobileToolsOpen(false);
        setSharedWorldStatus("Click the map to move your fireball in L-shaped paths. Drag the map to pan the viewport.", "ok");
        syncSharedWorldNpcRoster();
        renderSharedWorldShop();
        void refreshServerSettings();
        void loadSharedWorldInventory();
        void refreshSharedWorld();
        void refreshSharedWorldBattle();
        renderSharedWorldKeyboardPass();
        startSharedWorldPolling();
        startSharedWorldBattlePolling();
      };

      const closeSharedWorld = () => {
        const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.status) === "active";
        if (activeBattle) {
          void forfeitSharedWorldBattle(true);
        }
        if (worldModal) {
          worldModal.classList.remove("is-open");
          worldModal.setAttribute("aria-hidden", "true");
        }
        sharedWorldRequestSeq += 1;
        sharedWorldLoading = false;
        sharedWorldLoadingAt = 0;
        if (sharedWorldMotionFrame) {
          window.cancelAnimationFrame(sharedWorldMotionFrame);
          sharedWorldMotionFrame = 0;
        }
        if (sharedWorldFollowFrame) {
          window.cancelAnimationFrame(sharedWorldFollowFrame);
          sharedWorldFollowFrame = 0;
        }
        setSharedWorldPickingPosition(false);
        clearSharedWorldFollowTarget();
        stopSharedWorldKeyboardLoop();
        sharedWorldKeyboardSyncing = false;
        sharedWorldKeyboardSyncStartedAt = 0;
        sharedWorldKeyboardQueuedPoint = null;
        sharedWorldLocalMoveAt = 0;
        sharedWorldSelectedPoint = null;
        sharedWorldPathQueues.clear();
        hideSharedWorldMoveMarker(false);
        renderSharedWorldPositionPoint();
        setSharedWorldGameListOpen(false);
        if (worldCommandList) {
          worldCommandList.setAttribute("hidden", "");
        }
        setSharedWorldCloseMenuOpen(false);
        window.clearTimeout(sharedWorldWitchBubbleTimer);
        sharedWorldWitchBubbleTimer = 0;
        if (worldWitchBubble) {
          worldWitchBubble.classList.remove("is-visible");
        }
        window.clearTimeout(sharedWorldShopOpenTimer);
        sharedWorldShopOpenTimer = 0;
        closeSharedWorldInventory();
        closeSharedWorldSkinShop();
        closeSharedWorldTraining();
        stopSharedWorldPolling();
        hardCloseSharedWorldBattleUi();
        clearSharedWorldReconnect();
        hideSharedWorldStatus();
        stopSharedWorldKeyboardPassTimer();
      };

      window.addEventListener("online", () => {
        if (worldModal && worldModal.classList.contains("is-open")) {
          setSharedWorldStatus("Connection restored. Syncing QM-City...", "ok");
          clearSharedWorldReconnect();
          void refreshSharedWorld();
          void refreshSharedWorldBattle();
        }
      });

      window.addEventListener("offline", () => {
        if (worldModal && worldModal.classList.contains("is-open")) {
          scheduleSharedWorldReconnect("Connection lost.");
        }
      });

      const moveSharedWorldPlayer = async (point) => {
        if (!authToken || !point) {
          return;
        }
        const key = clean(activeWorldUsername()).toLowerCase();
        const destination = {
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        };
        const pos = setSharedWorldOrthogonalPath(key, destination);
        sharedWorldLocalMoveAt = Date.now();
        scheduleSharedWorldMotion();
        if (sharedWorldFollowSelf) {
          scheduleSharedWorldFollowCenter();
        }
        if (sharedWorldMapMode === "training") {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/move", {
            method: "POST",
            body: JSON.stringify({ x: destination.x, y: destination.y, current_x: pos ? pos.x : destination.x, current_y: pos ? pos.y : destination.y, ...activeWorldActorPayload() }),
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not move in shared world.", "error");
        }
      };

      const getSharedWorldSelfPosition = () => {
        const key = clean(activeWorldUsername()).toLowerCase();
        const pos = sharedWorldPositions.get(key);
        if (pos) {
          return pos;
        }
        return { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
      };

      const sharedWorldFollowStorageKey = () => `future_qm_city_follow_${clean(activeWorldUsername() || "guest").toLowerCase() || "guest"}`;

      const renderSharedWorldFollowButton = () => {
        if (!worldFollowButton) {
          return;
        }
        worldFollowButton.classList.toggle("is-active", sharedWorldFollowSelf);
        worldFollowButton.setAttribute("aria-pressed", sharedWorldFollowSelf ? "true" : "false");
        worldFollowButton.textContent = sharedWorldFollowSelf ? "Following" : "Follow";
      };

      const loadSharedWorldFollowPreference = () => {
        sharedWorldFollowSelf = false;
        renderSharedWorldFollowButton();
      };

      const saveSharedWorldFollowPreference = () => {
        try {
          if (window.localStorage) {
            window.localStorage.setItem(sharedWorldFollowStorageKey(), sharedWorldFollowSelf ? "1" : "0");
          }
        } catch (error) {
          // Follow mode is an optional viewport preference.
        }
      };

      const centerSharedWorldOnSelf = (smooth = true) => {
        const self = getSharedWorldSelfPosition();
        centerSharedWorldViewportOn(self.x, self.y, smooth);
      };

      const scheduleSharedWorldFollowCenter = () => {
        if (!sharedWorldFollowSelf || sharedWorldFollowFrame || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        sharedWorldFollowFrame = window.requestAnimationFrame(() => {
          sharedWorldFollowFrame = 0;
          centerSharedWorldOnSelf(false);
        });
      };

      const setSharedWorldFollowSelf = (enabled, centerNow = true) => {
        sharedWorldFollowSelf = Boolean(enabled);
        saveSharedWorldFollowPreference();
        renderSharedWorldFollowButton();
        if (sharedWorldFollowSelf && centerNow) {
          centerSharedWorldOnSelf(true);
        }
      };

      const moveSharedWorldBy = (dx = 0, dy = 0) => {
        const pos = getSharedWorldSelfPosition();
        const next = {
          x: sharedWorldClamp((pos.tx != null ? pos.tx : pos.x) + dx),
          y: sharedWorldClamp((pos.ty != null ? pos.ty : pos.y) + dy),
        };
        return moveSharedWorldPlayer(next);
      };

      const sharedWorldArrowDeltaMap = {
        arrowup: [0, -1],
        arrowdown: [0, 1],
        arrowleft: [-1, 0],
        arrowright: [1, 0],
      };

      const syncSharedWorldKeyboardTarget = async (point) => {
        if (!authToken || !point) {
          return;
        }
        if (sharedWorldMapMode === "training") {
          return;
        }
        const now = Date.now();
        if (sharedWorldKeyboardSyncing && now - sharedWorldKeyboardSyncStartedAt < 1200) {
          sharedWorldKeyboardQueuedPoint = point;
          return;
        }
        if (sharedWorldKeyboardSyncing) {
          sharedWorldKeyboardSyncing = false;
        }
        sharedWorldKeyboardSyncing = true;
        sharedWorldKeyboardSyncStartedAt = now;
        try {
          const pos = getSharedWorldSelfPosition();
          const response = await fetchAuthJson("/world/move", {
            method: "POST",
            body: JSON.stringify({ x: point.x, y: point.y, current_x: pos.x, current_y: pos.y, ...activeWorldActorPayload() }),
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not sync arrow movement.", "error");
        } finally {
          sharedWorldKeyboardSyncing = false;
          sharedWorldKeyboardSyncStartedAt = 0;
          const queued = sharedWorldKeyboardQueuedPoint;
          sharedWorldKeyboardQueuedPoint = null;
          if (queued) {
            void syncSharedWorldKeyboardTarget(queued);
          }
        }
      };

      const stopSharedWorldKeyboardLoop = () => {
        sharedWorldHeldArrows.clear();
        sharedWorldKeyboardLastAt = 0;
        if (sharedWorldKeyboardFrame) {
          window.cancelAnimationFrame(sharedWorldKeyboardFrame);
          sharedWorldKeyboardFrame = 0;
        }
      };

      const stepSharedWorldKeyboardLoop = (now) => {
        sharedWorldKeyboardFrame = 0;
        if (!sharedWorldHeldArrows.size || !worldModal || !worldModal.classList.contains("is-open")) {
          sharedWorldKeyboardLastAt = 0;
          return;
        }
        const dt = Math.min(34, Math.max(10, now - (sharedWorldKeyboardLastAt || now)));
        sharedWorldKeyboardLastAt = now;
        let dx = 0;
        let dy = 0;
        sharedWorldHeldArrows.forEach((key) => {
          const delta = sharedWorldArrowDeltaMap[key];
          if (delta) {
            dx += delta[0];
            dy += delta[1];
          }
        });
        const length = Math.hypot(dx, dy);
        if (length > 0) {
          clearSharedWorldFollowTarget();
          const key = clean(activeWorldUsername()).toLowerCase();
          let pos = sharedWorldPositions.get(key);
          if (!pos) {
            pos = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
            sharedWorldPositions.set(key, pos);
          }
          const move = dt * 0.00017;
          const target = {
            x: sharedWorldClamp((pos.tx != null ? pos.tx : pos.x) + (dx / length) * move),
            y: sharedWorldClamp((pos.ty != null ? pos.ty : pos.y) + (dy / length) * move),
          };
          pos.tx = target.x;
          pos.ty = target.y;
          sharedWorldLocalMoveAt = Date.now();
          const node = sharedWorldNodes.get(key);
          setSharedWorldFacing(node, dx);
          scheduleSharedWorldMotion();
          if (now - sharedWorldKeyboardSyncAt > 150) {
            sharedWorldKeyboardSyncAt = now;
            void syncSharedWorldKeyboardTarget(target);
          } else {
            sharedWorldKeyboardQueuedPoint = target;
          }
        }
        sharedWorldKeyboardFrame = window.requestAnimationFrame(stepSharedWorldKeyboardLoop);
      };

      const startSharedWorldKeyboardLoop = () => {
        if (sharedWorldKeyboardFrame) {
          return;
        }
        sharedWorldKeyboardLastAt = performance.now();
        sharedWorldKeyboardFrame = window.requestAnimationFrame(stepSharedWorldKeyboardLoop);
      };

      const sendSharedWorldAction = async (action = "") => {
        const safeAction = clean(action).toLowerCase();
        if (!safeAction) {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/action", {
            method: "POST",
            body: JSON.stringify({ action: safeAction, ...activeWorldActorPayload() }),
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
          setSharedWorldStatus(safeAction === "stop" ? "Action stopped." : `${safeAction} action started.`, "ok");
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not run QM-City action.", "error");
        }
      };

      const runSharedWorldCommand = async (raw = "") => {
        const original = clean(raw);
        const command = original.toLowerCase().replace(/\s+/g, " ").trim();
        if (!command) {
          return;
        }
        if (handleSharedWorldWitchText(original)) {
          return;
        }
        const inviteKey = sharedWorldNameKey(original);
        if (
          inviteKey.includes("fireball")
          || inviteKey.includes("vocabulary battle")
          || inviteKey.includes("ban cau lua")
          || (inviteKey.includes("play") && inviteKey.includes("game"))
        ) {
          await sendSharedWorldBattleInvite("fireball_vocab", original);
          return;
        }
        if (/^(stop\s+follow|stop\s+following|unfollow)$/i.test(command)) {
          clearSharedWorldFollowTarget();
          setSharedWorldStatus("Follow mode stopped.", "ok");
          return;
        }
        const followMatch = original.match(/^follow(?:\s+(him|her|them|target|player|.+))?$/i);
        if (followMatch) {
          const rawTarget = clean(followMatch[1] || "");
          let target = null;
          if (!rawTarget || /^(him|her|them|target|player)$/i.test(rawTarget)) {
            target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
          } else {
            target = resolveSharedWorldTarget(rawTarget);
          }
          if (!target || clean(target.username).toLowerCase() === clean(activeWorldUsername()).toLowerCase()) {
            setSharedWorldStatus("Select another player first, then type follow him or follow her.", "error");
            return;
          }
          sharedWorldSelectedTargetKey = clean(target.username).toLowerCase();
          sharedWorldFollowTargetKey = sharedWorldSelectedTargetKey;
          renderSharedWorldSelectedTarget();
          updateSharedWorldFollowTarget();
          setSharedWorldStatus(`Following ${sharedWorldTargetLabel(target)}. Type stop follow to stop.`, "ok");
          return;
        }
        const moveToMatch = command.match(/^(?:move|go)\s+to\s+(-?\d+(?:\.\d+)?)\s*(?:,|;|\s)\s*(-?\d+(?:\.\d+)?)$/);
        if (moveToMatch) {
          clearSharedWorldFollowTarget();
          const rawX = Number(moveToMatch[1]);
          const rawY = Number(moveToMatch[2]);
          const point = {
            x: sharedWorldClamp(Math.abs(rawX) > 1 ? rawX / 100 : rawX),
            y: sharedWorldClamp(Math.abs(rawY) > 1 ? rawY / 100 : rawY),
          };
          await moveSharedWorldPlayer(point);
          setSharedWorldStatus(`Moving to ${Math.round(point.x * 100)} / ${Math.round(point.y * 100)}.`, "ok");
          return;
        }
        const moveToNameMatch = original.match(/^(?:move|go)\s+to\s+(.+)$/i);
        if (moveToNameMatch) {
          clearSharedWorldFollowTarget();
          const target = resolveSharedWorldTarget(moveToNameMatch[1]);
          if (!target || clean(target.username).toLowerCase() === clean(activeWorldUsername()).toLowerCase()) {
            setSharedWorldStatus("Target player was not found. Click a player first or use the exact name.", "error");
            return;
          }
          const point = sharedWorldNearTargetPoint(target);
          sharedWorldSelectedTargetKey = clean(target.username).toLowerCase();
          sharedWorldNodes.forEach((node, itemKey) => {
            node.classList.toggle("is-target-selected", itemKey === sharedWorldSelectedTargetKey);
          });
          renderSharedWorldSelectedTarget();
          await moveSharedWorldPlayer(point);
          if (clean(target.npc).toLowerCase() === "witch" || clean(target.username).toLowerCase() === "witch") {
            showSharedWorldWitchBubble("What do you need from me?", 7600);
          }
          setSharedWorldStatus(`Moving near ${sharedWorldTargetLabel(target)}.`, "ok");
          return;
        }
        const directMoves = {
          up: [0, -sharedWorldMoveStep],
          "move up": [0, -sharedWorldMoveStep],
          down: [0, sharedWorldMoveStep],
          "move down": [0, sharedWorldMoveStep],
          left: [-sharedWorldMoveStep, 0],
          "move left": [-sharedWorldMoveStep, 0],
          right: [sharedWorldMoveStep, 0],
          "move right": [sharedWorldMoveStep, 0],
        };
        if (directMoves[command]) {
          clearSharedWorldFollowTarget();
          const [dx, dy] = directMoves[command];
          await moveSharedWorldBy(dx, dy);
          setSharedWorldStatus(`Moving ${command.replace("move ", "")}.`, "ok");
          return;
        }
        const action = command === "jumb" ? "jump" : command;
        if ([...sharedWorldActions, "stop"].includes(action)) {
          await sendSharedWorldAction(action);
          return;
        }
        setSharedWorldStatus("Unknown command. Open Interact to see valid commands.", "error");
      };

      const sharedWorldTextEntryTarget = (target) => Boolean(
        target
        && target.closest
        && target.closest("input,textarea,select,[contenteditable]:not([contenteditable='false']),[role='textbox']")
      );

      const handleSharedWorldKeyboard = (event) => {
        if (!worldModal || !worldModal.classList.contains("is-open") || event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        if (sharedWorldCommandListOpen()) {
          const key = clean(event.key);
          if (key === "ArrowUp" || key === "ArrowDown" || key === "PageUp" || key === "PageDown" || key === "Home" || key === "End") {
            event.preventDefault();
            event.stopImmediatePropagation();
            const delta = key === "ArrowUp" ? -42
              : key === "ArrowDown" ? 42
                : key === "PageUp" ? -180
                  : key === "PageDown" ? 180
                    : 0;
            if (key === "Home") {
              worldCommandList.scrollTop = 0;
            } else if (key === "End") {
              worldCommandList.scrollTop = worldCommandList.scrollHeight;
            } else {
              worldCommandList.scrollTop += delta;
            }
            return;
          }
        }
        if (sharedWorldTextEntryTarget(event.target) || sharedWorldTextEntryTarget(document.activeElement)) {
          return;
        }
        const key = clean(event.key).toLowerCase();
        if (sharedWorldArrowDeltaMap[key]) {
          return;
        }
      };

      const handleSharedWorldKeyboardUp = (event) => {
        if (!worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        stopSharedWorldKeyboardLoop();
      };

      const sendSharedWorldChat = async () => {
        const message = clean(worldChatInput && worldChatInput.value);
        if (!message) {
          return;
        }
        if (worldChatInput) {
          worldChatInput.value = "";
        }
        try {
          const selectedTarget = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
          const response = await fetchAuthJson("/world/chat", {
            method: "POST",
            body: JSON.stringify({
              message,
              selected_target: sharedWorldSelectedTargetKey || "",
              selected_target_name: selectedTarget ? sharedWorldTargetLabel(selectedTarget) : "",
              ...activeWorldActorPayload(),
            }),
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
          setSharedWorldStatus("Chat bubble sent.", "ok");
          if (sharedWorldSelectedTargetKey === "witch" || (worldSkinShop && worldSkinShop.classList.contains("is-open"))) {
            handleSharedWorldWitchText(message);
          }
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not send shared world chat.", "error");
        }
      };

      let gameRoomState = null;
      let gamePollingTimer = 0;
      let gameBattleState = null;
      let gameBattleTimer = 0;
      const gameSelectedWords = new Map();

      const setGameStatus = (message = "", tone = "") => {
        if (!gameStatus) {
          return;
        }
        gameStatus.textContent = message || "";
        gameStatus.classList.toggle("is-error", tone === "error");
        gameStatus.classList.toggle("is-ok", tone === "ok");
      };

      const stopGamePolling = () => {
        if (gamePollingTimer) {
          window.clearInterval(gamePollingTimer);
          gamePollingTimer = 0;
        }
      };

      const startGamePolling = () => {
        stopGamePolling();
        gamePollingTimer = window.setInterval(() => {
          if (gameModal && gameModal.classList.contains("is-open")) {
            void refreshGameState();
          }
        }, 2200);
      };

      const normalizeGameAnswer = (value = "") => clean(value)
        .toLowerCase()
        .replace(/['’`]/g, "")
        .replace(/[^a-z0-9]+/g, " ")
        .trim();

      const stopGameBattleLoop = () => {
        if (gameBattleTimer) {
          window.cancelAnimationFrame(gameBattleTimer);
          gameBattleTimer = 0;
        }
      };

      const gameBattleRounds = (battle = {}) => Array.isArray(battle.rounds)
        ? battle.rounds.map((round) => ({
          round: Number(round.round || 1),
          monsters: Array.isArray(round.monsters) ? round.monsters.map((monster) => ({ ...monster })) : [],
        }))
        : [];

      const createGameBattleState = (room, battle) => ({
        roomId: clean(room && room.id),
        rounds: gameBattleRounds(battle),
        roundIndex: 0,
        queue: [],
        active: [],
        nextSpawnAt: 0,
        lastTick: 0,
        castleHp: Number(battle && battle.castle_hp || 1000),
        maxCastleHp: Number(battle && battle.castle_hp || 1000),
        crystals: Number(battle && battle.crystals || 120),
        score: 0,
        towers: 1,
        powerLevel: 1,
        rangeLevel: 1,
        phase: "running",
        status: "Type the English word that matches a monster meaning.",
        startedAt: Date.now(),
      });

      const fillGameBattleQueue = () => {
        if (!gameBattleState) {
          return;
        }
        const round = gameBattleState.rounds[gameBattleState.roundIndex] || { monsters: [] };
        gameBattleState.queue = (round.monsters || []).map((monster, index) => ({
          ...monster,
          uid: `${gameBattleState.roundIndex + 1}-${index + 1}-${clean(monster.key || monster.word)}`,
          hp: Number(monster.hp || 120),
          maxHp: Number(monster.hp || 120),
          progress: 0,
          labelOffset: (index % 2 === 0 ? -16 : 16),
          hitFlash: 0,
        }));
        gameBattleState.active = [];
        gameBattleState.nextSpawnAt = 0;
      };

      const ensureGameBattleState = (room, battle) => {
        const roomId = clean(room && room.id);
        if (!gameBattleState || gameBattleState.roomId !== roomId) {
          gameBattleState = createGameBattleState(room, battle);
          fillGameBattleQueue();
        }
        return gameBattleState;
      };

      const gameBattleDamage = () => 85 + gameBattleState.powerLevel * 42 + gameBattleState.towers * 24;
      const gameBattleRange = () => Math.min(48, 24 + gameBattleState.rangeLevel * 6);
      const gameBattlePathPoints = [
        { x: 5, y: 76 },
        { x: 17, y: 26 },
        { x: 31, y: 60 },
        { x: 44, y: 82 },
        { x: 58, y: 36 },
        { x: 72, y: 24 },
        { x: 83, y: 50 },
        { x: 94, y: 38 },
      ];

      const gameBattleFallbackPathPoint = (progress = 0) => {
        const points = gameBattlePathPoints;
        const value = Math.max(0, Math.min(100, Number(progress || 0)));
        const scaled = (value / 100) * (points.length - 1);
        const index = Math.min(points.length - 2, Math.floor(scaled));
        const t = scaled - index;
        const start = points[index];
        const end = points[index + 1];
        const x = start.x + (end.x - start.x) * t;
        const y = start.y + (end.y - start.y) * t;
        const angle = Math.atan2(end.y - start.y, end.x - start.x) * 180 / Math.PI;
        return { x, y, angle };
      };

      const gameBattlePathPoint = (lane, progress = 0) => {
        const path = lane && lane.querySelector(".ft-game-path-core");
        if (!path || typeof path.getTotalLength !== "function") {
          return gameBattleFallbackPathPoint(progress);
        }
        try {
          const value = Math.max(0, Math.min(100, Number(progress || 0)));
          const total = path.getTotalLength();
          const length = total * value / 100;
          const point = path.getPointAtLength(length);
          const tangent = path.getPointAtLength(Math.min(total, length + 2));
          return {
            x: point.x / 10,
            y: point.y / 3,
            angle: Math.atan2(tangent.y - point.y, tangent.x - point.x) * 180 / Math.PI,
          };
        } catch (error) {
          return gameBattleFallbackPathPoint(progress);
        }
      };

      const updateGameBattleView = () => {
        if (!gameBattleState) {
          return;
        }
        const root = gameVocabGrid && gameVocabGrid.querySelector(".ft-game-playfield");
        if (!root) {
          return;
        }
        const setText = (selector, text) => {
          const node = root.querySelector(selector);
          if (node) {
            node.textContent = text;
          }
        };
        setText("[data-game-round]", `${Math.min(gameBattleState.roundIndex + 1, gameBattleState.rounds.length)} / ${gameBattleState.rounds.length}`);
        setText("[data-game-castle]", `${Math.max(0, Math.round(gameBattleState.castleHp))} HP`);
        setText("[data-game-crystals]", `${Math.max(0, Math.round(gameBattleState.crystals))}`);
        setText("[data-game-score]", `${gameBattleState.score}`);
        setText("[data-game-status]", gameBattleState.status);
        setText("[data-game-towers]", `${gameBattleState.towers} tower${gameBattleState.towers > 1 ? "s" : ""} | P${gameBattleState.powerLevel} | R${gameBattleState.rangeLevel}`);
        const rangeNode = root.querySelector(".ft-game-range");
        if (rangeNode) {
          rangeNode.style.width = `${Math.max(240, gameBattleRange() * 5)}px`;
        }
        const lane = root.querySelector(".ft-game-battle-lane");
        if (lane) {
          lane.querySelectorAll(".ft-game-monster").forEach((node) => node.remove());
          gameBattleState.active.forEach((monster) => {
            const point = gameBattlePathPoint(lane, monster.progress);
            const monsterType = clean(monster.type || monster.pos || monster.partOfSpeech || "Vocabulary");
            const monsterHp = Math.max(1, Math.round(monster.hp));
            const node = document.createElement("div");
            node.className = `ft-game-monster${monster.hitFlash > performance.now() ? " is-hit" : ""}`;
            node.style.setProperty("--monster-left", `${point.x}%`);
            node.style.setProperty("--monster-top", `${point.y}%`);
            node.style.setProperty("--monster-angle", `${point.angle}deg`);
            node.style.setProperty("--monster-label-y", `${monster.labelOffset || 0}px`);
            node.innerHTML = `
              <div class="ft-game-tank" aria-hidden="true">
                <div class="ft-game-tank-track is-top"></div>
                <div class="ft-game-tank-track is-bottom"></div>
                <div class="ft-game-tank-body"></div>
                <div class="ft-game-tank-turret"></div>
                <div class="ft-game-tank-cannon"></div>
                <div class="ft-game-tank-scan"></div>
              </div>
              <div class="ft-game-monster-label">
                <strong>${clean(monster.meaning || monster.word || "Unknown")}</strong>
                <small>${monsterType} | Wave ${gameBattleState.roundIndex + 1} | ${monsterHp} HP</small>
                <div class="ft-game-hpbar"><span style="--hp:${Math.max(0, Math.min(100, (monster.hp / Math.max(1, monster.maxHp)) * 100))}%"></span></div>
              </div>
            `;
            lane.appendChild(node);
          });
        }
        const input = root.querySelector("#ft-game-battle-input");
        if (input && document.activeElement !== input && gameBattleState.phase !== "complete") {
          input.focus({ preventScroll: true });
        }
        const nextWave = root.querySelector("[data-game-next-wave]");
        if (nextWave) {
          nextWave.disabled = gameBattleState.phase !== "break";
        }
      };

      const gameBattleSpawnMonster = (now) => {
        if (!gameBattleState || gameBattleState.phase !== "running") {
          return;
        }
        if (!gameBattleState.queue.length || gameBattleState.active.length >= 3 || now < gameBattleState.nextSpawnAt) {
          return;
        }
        const monster = gameBattleState.queue.shift();
        monster.progress = 0;
        gameBattleState.active.push(monster);
        gameBattleState.nextSpawnAt = now + 2600;
      };

      const finishGameBattleRoundIfNeeded = () => {
        if (!gameBattleState || gameBattleState.phase !== "running") {
          return;
        }
        if (gameBattleState.queue.length || gameBattleState.active.length) {
          return;
        }
        if (gameBattleState.roundIndex >= gameBattleState.rounds.length - 1) {
          gameBattleState.phase = "complete";
          gameBattleState.status = "Mission complete. All waves cleared.";
          stopGameBattleLoop();
          updateGameBattleView();
          return;
        }
        gameBattleState.phase = "break";
        gameBattleState.status = "Wave cleared. Upgrade towers, then launch the next wave.";
      };

      const startNextGameBattleWave = () => {
        if (!gameBattleState || gameBattleState.phase !== "break") {
          return;
        }
        gameBattleState.roundIndex += 1;
        gameBattleState.phase = "running";
        gameBattleState.status = "Next wave incoming.";
        fillGameBattleQueue();
        startGameBattleLoop();
        updateGameBattleView();
      };

      const tickGameBattle = (now) => {
        if (!gameBattleState || !gameVocabGrid || !gameVocabGrid.querySelector(".ft-game-playfield")) {
          stopGameBattleLoop();
          return;
        }
        if (!gameBattleState.lastTick) {
          gameBattleState.lastTick = now;
        }
        const dt = Math.min(0.08, Math.max(0, (now - gameBattleState.lastTick) / 1000));
        gameBattleState.lastTick = now;
        if (gameBattleState.phase === "running") {
          gameBattleSpawnMonster(now);
          const speedBoost = 4.0 + gameBattleState.roundIndex * 0.9;
          gameBattleState.active.forEach((monster) => {
            monster.progress += dt * speedBoost * Number(monster.speed || 1);
          });
          const escaped = gameBattleState.active.filter((monster) => monster.progress >= 100);
          if (escaped.length) {
            gameBattleState.castleHp -= escaped.length * (80 + gameBattleState.roundIndex * 35);
            gameBattleState.status = `${escaped.length} monster breached the castle shield.`;
            gameBattleState.active = gameBattleState.active.filter((monster) => monster.progress < 100);
            if (gameBattleState.castleHp <= 0) {
              gameBattleState.castleHp = 0;
              gameBattleState.phase = "complete";
              gameBattleState.status = "Castle collapsed. Rebuild and try again.";
            }
          }
          finishGameBattleRoundIfNeeded();
        }
        updateGameBattleView();
        if (gameBattleState.phase !== "complete") {
          gameBattleTimer = window.requestAnimationFrame(tickGameBattle);
        }
      };

      const startGameBattleLoop = () => {
        stopGameBattleLoop();
        gameBattleState.lastTick = 0;
        gameBattleTimer = window.requestAnimationFrame(tickGameBattle);
      };

      const gameBattleApplyDamage = (monster, damage) => {
        monster.hp -= damage;
        monster.hitFlash = performance.now() + 260;
        if (monster.hp <= 0) {
          gameBattleState.active = gameBattleState.active.filter((item) => item !== monster);
          gameBattleState.score += 1;
          gameBattleState.crystals += Number(monster.reward || 4);
          gameBattleState.status = `Destroyed ${clean(monster.word)}.`;
        } else {
          gameBattleState.status = `Hit ${clean(monster.word)} for ${Math.round(damage)} damage.`;
        }
      };

      const submitGameBattleAnswer = () => {
        const input = gameVocabGrid && gameVocabGrid.querySelector("#ft-game-battle-input");
        if (!gameBattleState || !input) {
          return;
        }
        const answer = normalizeGameAnswer(input.value);
        input.value = "";
        if (!answer) {
          gameBattleState.status = "Type an English answer first.";
          updateGameBattleView();
          return;
        }
        const range = gameBattleRange();
        const target = gameBattleState.active.find((monster) => normalizeGameAnswer(monster.word) === answer && monster.progress >= 100 - range)
          || gameBattleState.active.find((monster) => normalizeGameAnswer(monster.word) === answer);
        if (!target) {
          gameBattleState.status = "No matching monster in range.";
          updateGameBattleView();
          return;
        }
        gameBattleApplyDamage(target, gameBattleDamage());
        finishGameBattleRoundIfNeeded();
        updateGameBattleView();
      };

      const spendGameCrystals = (cost) => {
        if (!gameBattleState || gameBattleState.crystals < cost) {
          if (gameBattleState) {
            gameBattleState.status = `Need ${cost} crystals.`;
            updateGameBattleView();
          }
          return false;
        }
        gameBattleState.crystals -= cost;
        return true;
      };

      const toggleGameBattleFullscreen = async () => {
        const target = gameVocabGrid && gameVocabGrid.querySelector(".ft-game-playfield")
          ? gameVocabGrid.querySelector(".ft-game-playfield")
          : (gameModal || document.documentElement);
        try {
          if (document.fullscreenElement === target) {
            await document.exitFullscreen();
          } else if (target && target.requestFullscreen) {
            if (document.fullscreenElement) {
              await document.exitFullscreen();
            }
            await target.requestFullscreen();
          }
        } catch (error) {
          setGameStatus(error && error.message ? error.message : "Fullscreen is not available.", "error");
        }
      };

      const renderGameBattleShell = (room, battle) => {
        if (!gameVocabGrid || !gameBattleState) {
          return;
        }
        stopGamePolling();
        gameVocabGrid.textContent = "";
        const playfield = document.createElement("section");
        playfield.className = "ft-game-playfield";
        playfield.innerHTML = `
          <div class="ft-game-battle-hud">
            <div class="ft-game-battle-stat">Wave<strong data-game-round>1 / 3</strong></div>
            <div class="ft-game-battle-stat">Castle<strong data-game-castle>1000 HP</strong></div>
            <div class="ft-game-battle-stat">Crystals<strong data-game-crystals>120</strong></div>
            <div class="ft-game-battle-stat">Kills<strong data-game-score>0</strong></div>
          </div>
          <div class="ft-game-battle-lane">
            <svg class="ft-game-path-svg" viewBox="0 0 1000 300" preserveAspectRatio="none" aria-hidden="true">
              <path class="ft-game-path-shadow" d="M 50 228 C 150 72 258 58 318 168 S 458 274 572 128 S 724 46 828 145 S 914 224 948 116"></path>
              <path class="ft-game-path-core" d="M 50 228 C 150 72 258 58 318 168 S 458 274 572 128 S 724 46 828 145 S 914 224 948 116"></path>
              <path class="ft-game-path-dash" d="M 50 228 C 150 72 258 58 318 168 S 458 274 572 128 S 724 46 828 145 S 914 224 948 116"></path>
              <circle class="ft-game-path-node" cx="50" cy="228" r="9"></circle>
              <circle class="ft-game-path-node" cx="318" cy="168" r="7"></circle>
              <circle class="ft-game-path-node" cx="572" cy="128" r="7"></circle>
              <circle class="ft-game-path-node" cx="828" cy="145" r="7"></circle>
              <circle class="ft-game-path-node" cx="948" cy="116" r="10"></circle>
            </svg>
            <div class="ft-game-range"></div>
            <div class="ft-game-castle">CASTLE</div>
            <div class="ft-game-tower"><span>T</span></div>
          </div>
          <input class="ft-game-battle-input" id="ft-game-battle-input" type="text" inputmode="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Type English word and press Enter">
          <div class="ft-game-battle-controls">
            <button class="ft-game-battle-control" type="button" data-game-build>Build tower -50</button>
            <button class="ft-game-battle-control" type="button" data-game-power>Power + -35</button>
            <button class="ft-game-battle-control" type="button" data-game-range>Range + -30</button>
            <button class="ft-game-battle-control" type="button" data-game-storm>Crystal storm -70</button>
            <button class="ft-game-battle-control" type="button" data-game-fullscreen>Fullscreen</button>
            <button class="ft-game-battle-control" type="button" data-game-cancel-battle>Cancel room</button>
            <button class="ft-game-battle-control" type="button" data-game-next-wave>Launch next wave</button>
            <div class="ft-game-battle-stat ft-game-battle-loadout" data-game-towers>1 tower | P1 | R1</div>
            <div class="ft-game-battle-stat ft-game-battle-status" data-game-status>Battle ready.</div>
          </div>
        `;
        gameVocabGrid.appendChild(playfield);
        const input = playfield.querySelector("#ft-game-battle-input");
        if (input) {
          input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              submitGameBattleAnswer();
            }
          });
        }
        const bind = (selector, fn) => {
          const node = playfield.querySelector(selector);
          if (node) {
            node.addEventListener("click", fn);
          }
        };
        bind("[data-game-build]", () => {
          if (spendGameCrystals(50)) {
            gameBattleState.towers += 1;
            gameBattleState.status = "New tower online.";
            updateGameBattleView();
          }
        });
        bind("[data-game-power]", () => {
          if (spendGameCrystals(35)) {
            gameBattleState.powerLevel += 1;
            gameBattleState.status = "Tower power upgraded.";
            updateGameBattleView();
          }
        });
        bind("[data-game-range]", () => {
          if (spendGameCrystals(30)) {
            gameBattleState.rangeLevel += 1;
            gameBattleState.status = "Tower range expanded.";
            updateGameBattleView();
          }
        });
        bind("[data-game-storm]", () => {
          if (spendGameCrystals(70)) {
            gameBattleState.active.slice().forEach((monster) => gameBattleApplyDamage(monster, 95));
            gameBattleState.status = "Crystal storm discharged.";
            finishGameBattleRoundIfNeeded();
            updateGameBattleView();
          }
        });
        bind("[data-game-next-wave]", startNextGameBattleWave);
        bind("[data-game-fullscreen]", () => void toggleGameBattleFullscreen());
        bind("[data-game-cancel-battle]", () => void cancelGameRoom().catch((error) => setGameStatus(error && error.message ? error.message : "Could not cancel room.", "error")));
        updateGameBattleView();
        startGameBattleLoop();
      };

      const startGameBattleFromRoom = (room, battle) => {
        ensureGameBattleState(room, battle);
        renderGameBattleShell(room, battle);
      };

      const renderGameRoomList = (rooms = []) => {
        if (!gameRoomList) {
          return;
        }
        gameRoomList.textContent = "";
        if (!rooms.length) {
          const empty = document.createElement("div");
          empty.className = "ft-game-room";
          empty.innerHTML = "<strong>No open rooms</strong><small>Create a room to start.</small>";
          gameRoomList.appendChild(empty);
          return;
        }
        rooms.forEach((room) => {
          const button = document.createElement("button");
          button.className = "ft-game-room";
          button.type = "button";
          button.innerHTML = `<strong>${clean(room.id)}</strong><small>${(room.players || []).length} / ${room.seat_count} seats | ${room.word_limit} words</small>`;
          button.addEventListener("click", () => {
            if (gameRoomCodeInput) {
              gameRoomCodeInput.value = clean(room.id);
            }
            void joinGameRoom(clean(room.id));
          });
          gameRoomList.appendChild(button);
        });
      };

      const currentGameRoomId = () => clean(gameRoomState && gameRoomState.id);

      const renderGameRoom = (room = null) => {
        if (!gameSeatsList || !gameVocabGrid) {
          return;
        }
        if (!room) {
          gameRoomState = null;
          gameBattleState = null;
          stopGameBattleLoop();
          gameSeatsList.textContent = "";
          gameVocabGrid.textContent = "";
          return;
        }
        gameRoomState = room || gameRoomState;
        const currentRoom = gameRoomState || {};
        renderGameRoomList([currentRoom]);
        const players = Array.isArray(currentRoom.players) ? currentRoom.players : [];
        gameSeatsList.textContent = "";
        for (let seat = 1; seat <= Math.max(1, Number(currentRoom.seat_count || 1)); seat += 1) {
          const player = players.find((item) => Number(item.seat) === seat);
          const card = document.createElement("div");
          card.className = "ft-game-seat";
          if (player && player.host) {
            card.classList.add("is-host");
          }
          if (player && player.ready) {
            card.classList.add("is-ready");
          }
          card.innerHTML = player
            ? `<strong>${clean(player.username)}</strong><small>${player.host ? "Host" : "Player"} | ${player.ready ? "Ready" : "Drafting"} | selected ${player.selected_for || 0}</small>`
            : `<strong>Empty seat ${seat}</strong><small>Waiting for player.</small>`;
          gameSeatsList.appendChild(card);
        }
        gameVocabGrid.textContent = "";
        const ownSelectionKey = clean(currentAuthUsername).toLowerCase();
        if (!currentRoom.selections || typeof currentRoom.selections !== "object") {
          currentRoom.selections = {};
        }
        const ownSelections = currentRoom.selections[ownSelectionKey] || (currentRoom.selections[ownSelectionKey] = {});
        const battle = currentRoom.battle && currentRoom.battle.players ? currentRoom.battle : null;
        const ownBattle = battle && battle.players ? battle.players[ownSelectionKey] : null;
        if (ownBattle) {
          startGameBattleFromRoom(currentRoom, ownBattle);
          return;
        } else if (players.length === 1 && Number(currentRoom.seat_count || 1) === 1) {
          const soloPanel = document.createElement("section");
          soloPanel.className = "ft-game-battle";
          const ownPlayer = players[0] || {};
          const vocabCount = Array.isArray(ownPlayer.vocabulary) ? ownPlayer.vocabulary.length : 0;
          soloPanel.innerHTML = `
            <strong>Solo defense ready</strong>
            <small>Press Ready and the system will draw up to ${Math.max(1, Math.min(50, Number(currentRoom.word_limit || 50)))} learned words from your vocabulary registry to build 3 monster waves.</small>
            <div class="ft-game-wave-grid">
              <div class="ft-game-wave"><strong>Source</strong><br>${vocabCount} learned words visible</div>
              <div class="ft-game-wave"><strong>Mode</strong><br>System-generated monsters</div>
              <div class="ft-game-wave"><strong>Rounds</strong><br>3 escalating waves</div>
            </div>
            <button class="ft-game-action" type="button" data-game-solo-ready>Start solo battle</button>
          `;
          gameVocabGrid.appendChild(soloPanel);
          const soloReadyButton = soloPanel.querySelector("[data-game-solo-ready]");
          if (soloReadyButton) {
            soloReadyButton.addEventListener("click", () => {
              void setGameReady(true).catch((error) => setGameStatus(error && error.message ? error.message : "Could not start solo battle.", "error"));
            });
          }
        }
        players.filter((player) => clean(player.username).toLowerCase() !== ownSelectionKey).forEach((player) => {
          const panel = document.createElement("section");
          panel.className = "ft-game-vocab-panel";
          const serverSelected = Array.isArray(ownSelections[player.username]) ? ownSelections[player.username] : null;
          const selected = serverSelected
            ? new Set(serverSelected.map((item) => clean(item && (item.key || item.word || item)).toLowerCase()).filter(Boolean))
            : (gameSelectedWords.get(player.username) || new Set());
          gameSelectedWords.set(player.username, selected);
          const words = Array.isArray(player.vocabulary) ? player.vocabulary : [];
          const limit = Math.max(1, Math.min(50, Number(currentRoom.word_limit || 50)));
          const title = document.createElement("div");
          title.innerHTML = `<strong>${clean(player.username)}</strong><small>Choose up to ${limit} words for this opponent. ${selected.size}/${limit}</small>`;
          const list = document.createElement("div");
          list.className = "ft-game-word-list";
          words.forEach((word) => {
            const key = clean(word.key || word.word).toLowerCase();
            const row = document.createElement("button");
            row.className = "ft-game-word";
            row.type = "button";
            row.disabled = clean(currentRoom.status) === "battle";
            row.classList.toggle("is-selected", selected.has(key));
            row.innerHTML = `<strong>${clean(word.word)}</strong><small>${clean(word.meaning) || "No meaning"}</small>`;
            row.addEventListener("click", () => {
              if (selected.has(key)) {
                selected.delete(key);
              } else if (selected.size < limit) {
                selected.add(key);
              }
              gameSelectedWords.set(player.username, selected);
              ownSelections[player.username] = Array.from(selected).map((item) => ({ key: item, word: item }));
              renderGameRoom(currentRoom);
              void submitGameSelection(player.username);
            });
            list.appendChild(row);
          });
          panel.appendChild(title);
          panel.appendChild(list);
          gameVocabGrid.appendChild(panel);
        });
      };

      const refreshGameState = async () => {
        if (!authToken) {
          return;
        }
        const roomId = currentGameRoomId();
        const response = await fetchAuthJson(roomId ? `/game/state?room=${encodeURIComponent(roomId)}` : "/game/state");
        const result = response && response.payload ? response.payload : response;
        if (result.room) {
          renderGameRoom(result.room);
          setGameStatus(clean(result.room.status) === "battle" ? `Room ${result.room.id} battle protocol armed.` : `Room ${result.room.id} online.`, "ok");
        } else {
          renderGameRoom(null);
          renderGameRoomList(result.rooms || []);
          setGameStatus("Choose an open room or create a new battle room.");
        }
      };

      const openGameLobby = () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de mo game.");
          return;
        }
        if (gameModal) {
          gameModal.classList.add("is-open");
          gameModal.setAttribute("aria-hidden", "false");
        }
        setGameStatus("Game lobby online.");
        void refreshGameState().catch((error) => setGameStatus(error && error.message ? error.message : "Could not load game lobby.", "error"));
        startGamePolling();
      };

      const closeGameLobby = () => {
        if (gameModal) {
          gameModal.classList.remove("is-open");
          gameModal.setAttribute("aria-hidden", "true");
        }
        stopGamePolling();
        stopGameBattleLoop();
      };

      const createGameRoom = async () => {
        gameBattleState = null;
        stopGameBattleLoop();
        const response = await fetchAuthJson("/game/create", {
          method: "POST",
          body: JSON.stringify({
            seat_count: gameSeatsInput ? gameSeatsInput.value : 2,
            word_limit: gameWordLimitInput ? gameWordLimitInput.value : 50,
          }),
        });
        const result = response && response.payload ? response.payload : response;
        gameSelectedWords.clear();
        renderGameRoom(result.room);
        if (gameRoomCodeInput) {
          gameRoomCodeInput.value = clean(result.room && result.room.id);
        }
        const seatCount = Number(result.room && result.room.seat_count || 1);
        setGameStatus(seatCount === 1 ? `Created solo room ${clean(result.room && result.room.id)}. Press Ready to build monster waves.` : `Created room ${clean(result.room && result.room.id)}.`, "ok");
      };

      const joinGameRoom = async (roomId = "") => {
        gameBattleState = null;
        stopGameBattleLoop();
        const targetRoom = clean(roomId || (gameRoomCodeInput && gameRoomCodeInput.value)).toUpperCase();
        if (!targetRoom) {
          setGameStatus("Enter a room code first.", "error");
          return;
        }
        const response = await fetchAuthJson("/game/join", {
          method: "POST",
          body: JSON.stringify({ room: targetRoom }),
        });
        const result = response && response.payload ? response.payload : response;
        gameSelectedWords.clear();
        renderGameRoom(result.room);
        setGameStatus(`Joined room ${clean(result.room && result.room.id)}.`, "ok");
      };

      const submitGameSelection = async (target) => {
        const roomId = currentGameRoomId();
        if (!roomId || !target) {
          return;
        }
        const selected = Array.from(gameSelectedWords.get(target) || []);
        const response = await fetchAuthJson("/game/select", {
          method: "POST",
          body: JSON.stringify({ room: roomId, target, words: selected }),
        });
        const result = response && response.payload ? response.payload : response;
        renderGameRoom(result.room);
      };

      const setGameReady = async (ready = true) => {
        const roomId = currentGameRoomId();
        if (!roomId) {
          setGameStatus("Create or join a room first.", "error");
          return;
        }
        const response = await fetchAuthJson("/game/ready", {
          method: "POST",
          body: JSON.stringify({ room: roomId, ready }),
        });
        const result = response && response.payload ? response.payload : response;
        renderGameRoom(result.room);
        setGameStatus(clean(result.room && result.room.status) === "battle" ? "Battle waves generated." : (ready ? "Ready signal sent." : "Ready cancelled."), "ok");
      };

      const cancelGameRoom = async () => {
        const roomId = currentGameRoomId();
        if (!roomId) {
          setGameStatus("No active room to cancel.", "error");
          return;
        }
        const response = await fetchAuthJson("/game/cancel", {
          method: "POST",
          body: JSON.stringify({ room: roomId }),
        });
        const result = response && response.payload ? response.payload : response;
        stopGameBattleLoop();
        gameBattleState = null;
        gameRoomState = null;
        gameSelectedWords.clear();
        if (gameSeatsList) {
          gameSeatsList.textContent = "";
        }
        if (gameVocabGrid) {
          gameVocabGrid.textContent = "";
        }
        if (gameRoomCodeInput) {
          gameRoomCodeInput.value = "";
        }
        renderGameRoomList(result.rooms || []);
        setGameStatus(result.cancelled ? `Room ${roomId} cancelled.` : `Left room ${roomId}.`, "ok");
        startGamePolling();
      };

      const toggleLearnerPaintFullscreen = async () => {
        if (!paintModal && !paintCard) {
          return;
        }
        try {
          if (document.fullscreenElement) {
            await document.exitFullscreen();
          } else if (typeof requestAnyFullscreen === "function") {
            await requestAnyFullscreen();
          } else if (document.documentElement && document.documentElement.requestFullscreen) {
            await document.documentElement.requestFullscreen({ navigationUI: "hide" });
          }
        } catch (error) {
          setLearnerPaintSyncStatus(error && error.message ? error.message : "Fullscreen is not available.");
        } finally {
          syncLearnerPaintFullscreenButton();
        }
        scheduleLearnerPaintViewportRefresh();
      };

      const openLearnerPaintInTab = () => {
        try {
          const url = new URL(window.location.href);
          url.searchParams.set("paint", "1");
          const next = window.open(url.toString(), "_blank", "noopener");
          if (!next) {
            setLearnerPaintSyncStatus("Browser blocked the new tab.");
          }
        } catch (error) {
          setLearnerPaintSyncStatus(error && error.message ? error.message : "Could not open new tab.");
        }
      };

      const clearLearnerPaintNow = () => {
        cancelLearnerPaintTextEditor();
        clearLearnerPaintSelectAnchor();
        learnerPaintSelection = null;
        learnerPaintPointer = null;
        learnerPaintObjects.splice(0, learnerPaintObjects.length);
        learnerPaintSelectedId = "";
        const ctx = learnerPaintBufferCtx();
        if (ctx && learnerPaintBufferCanvas) {
          ctx.clearRect(0, 0, learnerPaintBufferCanvas.width, learnerPaintBufferCanvas.height);
        }
        renderLearnerPaint();
        scheduleLearnerPaintSync(80);
      };

      const learnerPaintClearOrigin = () => {
        learnerPaintEnsureBuffer();
        const stage = paintCanvas && paintCanvas.parentElement;
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        const fallback = {
          x: boardWidth / 2,
          y: 0,
          visualX: "50%",
          visualY: "8%",
          radius: Math.hypot(boardWidth, boardHeight),
        };
        if (!paintCanvas || !stage) {
          return fallback;
        }
        const canvasRect = paintCanvas.getBoundingClientRect();
        const stageRect = stage.getBoundingClientRect();
        const clearRect = paintClear && paintClear.getBoundingClientRect ? paintClear.getBoundingClientRect() : null;
        const clientX = clearRect && clearRect.width ? clearRect.left + clearRect.width / 2 : canvasRect.left + canvasRect.width / 2;
        const clientY = clearRect && clearRect.height ? clearRect.top + clearRect.height / 2 : canvasRect.top;
        const boardX = learnerPaintClamp((clientX - canvasRect.left) * boardWidth / Math.max(1, canvasRect.width), 0, boardWidth);
        const boardY = learnerPaintClamp((clientY - canvasRect.top) * boardHeight / Math.max(1, canvasRect.height), 0, boardHeight);
        const visualX = clientX - stageRect.left + stage.scrollLeft;
        const visualY = clientY - stageRect.top + stage.scrollTop;
        const radius = Math.max(
          Math.hypot(boardX, boardY),
          Math.hypot(boardWidth - boardX, boardY),
          Math.hypot(boardX, boardHeight - boardY),
          Math.hypot(boardWidth - boardX, boardHeight - boardY)
        );
        return {
          x: boardX,
          y: boardY,
          visualX: `${Math.max(0, visualX).toFixed(1)}px`,
          visualY: `${Math.max(0, visualY).toFixed(1)}px`,
          radius,
        };
      };

      const learnerPaintAutoEraseBounds = (eraserSize = 36) => {
        const ctx = learnerPaintBufferCtx();
        if (!ctx || !learnerPaintBufferCanvas) {
          return [];
        }
        const width = learnerPaintBufferCanvas.width;
        const height = learnerPaintBufferCanvas.height;
        let imageData = null;
        try {
          imageData = ctx.getImageData(0, 0, width, height);
        } catch (error) {
          return [];
        }
        const data = imageData.data;
        const scanStep = Math.max(5, Math.min(12, Math.round(eraserSize / 5)));
        const points = [];
        for (let y = 0; y < height; y += scanStep) {
          for (let x = 0; x < width; x += scanStep) {
            let hit = false;
            for (let yy = 0; yy < scanStep && y + yy < height && !hit; yy += 2) {
              for (let xx = 0; xx < scanStep && x + xx < width; xx += 2) {
                const alpha = data[(((y + yy) * width + (x + xx)) * 4) + 3];
                if (alpha > 6) {
                  hit = true;
                  break;
                }
              }
            }
            if (hit) {
              points.push({
                x: learnerPaintClamp(x + scanStep / 2, 0, width),
                y: learnerPaintClamp(y + scanStep / 2, 0, height),
              });
            }
          }
        }
        if (!points.length) {
          return [];
        }
        const clusterCount = Math.max(1, Math.min(6, points.length));
        const sorted = points.slice().sort((a, b) => (a.x + a.y * 0.18) - (b.x + b.y * 0.18));
        let seeds = Array.from({ length: clusterCount }, (_, index) => {
          const sampleIndex = Math.min(sorted.length - 1, Math.round((index + 0.5) * sorted.length / clusterCount));
          return { x: sorted[sampleIndex].x, y: sorted[sampleIndex].y };
        });
        let clusters = [];
        for (let iteration = 0; iteration < 4; iteration += 1) {
          clusters = Array.from({ length: clusterCount }, () => ({ points: [], sumX: 0, sumY: 0 }));
          points.forEach((point) => {
            let bestIndex = 0;
            let bestDistance = Infinity;
            seeds.forEach((seed, index) => {
              const dx = point.x - seed.x;
              const dy = point.y - seed.y;
              const distance = dx * dx + dy * dy;
              if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = index;
              }
            });
            const cluster = clusters[bestIndex];
            cluster.points.push(point);
            cluster.sumX += point.x;
            cluster.sumY += point.y;
          });
          seeds = clusters.map((cluster, index) => {
            if (!cluster.points.length) {
              return seeds[index] || points[index % points.length];
            }
            return {
              x: cluster.sumX / cluster.points.length,
              y: cluster.sumY / cluster.points.length,
            };
          });
        }
        return clusters
          .filter((cluster) => cluster.points.length)
          .map((cluster) => {
            let minX = Infinity;
            let minY = Infinity;
            let maxX = -Infinity;
            let maxY = -Infinity;
            cluster.points.forEach((point) => {
              minX = Math.min(minX, point.x);
              minY = Math.min(minY, point.y);
              maxX = Math.max(maxX, point.x);
              maxY = Math.max(maxY, point.y);
            });
            const pad = Math.max(16, eraserSize * 0.9);
            return {
              x: learnerPaintClamp(minX - pad, 0, width),
              y: learnerPaintClamp(minY - pad, 0, height),
              w: learnerPaintClamp(maxX - minX + pad * 2, 1, width),
              h: learnerPaintClamp(maxY - minY + pad * 2, 1, height),
              weight: cluster.points.length,
            };
          })
          .sort((a, b) => b.weight - a.weight);
      };

      const learnerPaintAutoErasePath = (bounds, eraserSize = 36) => {
        const width = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const height = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        const x0 = learnerPaintClamp(bounds.x, 0, width);
        const y0 = learnerPaintClamp(bounds.y, 0, height);
        const x1 = learnerPaintClamp(bounds.x + bounds.w, 0, width);
        const y1 = learnerPaintClamp(bounds.y + bounds.h, 0, height);
        const step = Math.max(18, eraserSize * 0.64);
        const path = [];
        let rowIndex = 0;
        for (let y = y0; y <= y1; y += step) {
          const yy = learnerPaintClamp(y, y0, y1);
          if (rowIndex % 2 === 0) {
            path.push({ x: x0, y: yy }, { x: x1, y: yy });
          } else {
            path.push({ x: x1, y: yy }, { x: x0, y: yy });
          }
          rowIndex += 1;
        }
        if (path.length < 2) {
          path.push({ x: x0, y: y0 }, { x: x1, y: y1 });
        }
        return path;
      };

      const learnerPaintAutoEraseTrack = (path) => {
        const distances = [0];
        let total = 0;
        for (let index = 1; index < path.length; index += 1) {
          total += Math.hypot(path[index].x - path[index - 1].x, path[index].y - path[index - 1].y);
          distances.push(total);
        }
        return { path, distances, total: Math.max(1, total) };
      };

      const learnerPaintTrackPointAt = (track, distance) => {
        const target = learnerPaintClamp(distance, 0, track.total || 1);
        const path = track.path || [];
        const distances = track.distances || [];
        if (path.length < 2) {
          return path[0] || { x: 0, y: 0 };
        }
        for (let index = 1; index < path.length; index += 1) {
          if (target <= distances[index]) {
            const start = path[index - 1];
            const end = path[index];
            const segmentLength = Math.max(1, distances[index] - distances[index - 1]);
            const local = (target - distances[index - 1]) / segmentLength;
            return {
              x: start.x + (end.x - start.x) * local,
              y: start.y + (end.y - start.y) * local,
            };
          }
        }
        return path[path.length - 1];
      };

      const createLearnerPaintAutoEraserNode = (visualSize = 48, index = 0, ringSize = 34) => {
        const stage = paintCanvas && paintCanvas.parentElement;
        if (!stage) {
          return null;
        }
        const node = document.createElement("div");
        node.className = "ft-paint-auto-eraser";
        node.setAttribute("aria-hidden", "true");
        node.style.setProperty("--auto-eraser-size", `${visualSize.toFixed(1)}px`);
        node.style.setProperty("--auto-eraser-ring", `${ringSize.toFixed(1)}px`);
        node.style.setProperty("--auto-eraser-tilt", `${(-22 + index * 9).toFixed(1)}deg`);
        node.appendChild(document.createElement("span"));
        stage.appendChild(node);
        window.requestAnimationFrame(() => node.classList.add("is-live"));
        return node;
      };

      const learnerPaintAutoEraserVisibleBox = (visualSize = 48) => {
        const stage = paintCanvas && paintCanvas.parentElement;
        const canvasRect = paintCanvas && paintCanvas.getBoundingClientRect ? paintCanvas.getBoundingClientRect() : null;
        const width = Math.max(1, Number(stage && stage.clientWidth || 0) || Number(canvasRect && canvasRect.width || 0) || LEARNER_PAINT_BOARD_WIDTH);
        const height = Math.max(1, Number(stage && stage.clientHeight || 0) || Number(canvasRect && canvasRect.height || 0) || LEARNER_PAINT_BOARD_HEIGHT);
        const left = Math.max(0, Number(stage && stage.scrollLeft || 0));
        const top = Math.max(0, Number(stage && stage.scrollTop || 0));
        return {
          left,
          top,
          right: left + width,
          bottom: top + height,
          width,
          height,
          pad: Math.max(visualSize * 1.55, 86),
        };
      };

      const learnerPaintRandomBetween = (min, max) => {
        const a = Number(min || 0);
        const b = Number(max || 0);
        if (b <= a) {
          return (a + b) / 2;
        }
        return a + Math.random() * (b - a);
      };

      const learnerPaintMixDisplayPoint = (from, to, amount) => {
        const t = learnerPaintClamp(Number(amount || 0), 0, 1);
        const a = from || to || { x: 0, y: 0 };
        const b = to || from || { x: 0, y: 0 };
        return {
          x: a.x + (b.x - a.x) * t,
          y: a.y + (b.y - a.y) * t,
        };
      };

      const learnerPaintAutoEraserOffscreenDisplayPoint = (visualSize = 48, index = 0, side = null, anchor = null) => {
        const box = learnerPaintAutoEraserVisibleBox(visualSize);
        const pad = box.pad + Math.random() * Math.max(18, visualSize * 0.75);
        const safeLeft = box.left + Math.min(box.width / 2, pad * 0.7);
        const safeRight = box.right - Math.min(box.width / 2, pad * 0.7);
        const safeTop = box.top + Math.min(box.height / 2, pad * 0.7);
        const safeBottom = box.bottom - Math.min(box.height / 2, pad * 0.7);
        const chosenSide = side == null ? ((index + Math.floor(Math.random() * 4)) % 4) : side;
        const wiggleX = box.width * 0.16;
        const wiggleY = box.height * 0.16;
        if (chosenSide === 0) {
          return {
            x: anchor ? learnerPaintClamp(anchor.x + learnerPaintRandomBetween(-wiggleX, wiggleX), safeLeft, safeRight) : learnerPaintRandomBetween(safeLeft, safeRight),
            y: box.top - pad,
          };
        }
        if (chosenSide === 1) {
          return {
            x: box.right + pad,
            y: anchor ? learnerPaintClamp(anchor.y + learnerPaintRandomBetween(-wiggleY, wiggleY), safeTop, safeBottom) : learnerPaintRandomBetween(safeTop, safeBottom),
          };
        }
        if (chosenSide === 2) {
          return {
            x: anchor ? learnerPaintClamp(anchor.x + learnerPaintRandomBetween(-wiggleX, wiggleX), safeLeft, safeRight) : learnerPaintRandomBetween(safeLeft, safeRight),
            y: box.bottom + pad,
          };
        }
        return {
          x: box.left - pad,
          y: anchor ? learnerPaintClamp(anchor.y + learnerPaintRandomBetween(-wiggleY, wiggleY), safeTop, safeBottom) : learnerPaintRandomBetween(safeTop, safeBottom),
        };
      };

      const learnerPaintAutoEraserExitDisplayPoint = (displayPoint, visualSize = 48, index = 0) => {
        const box = learnerPaintAutoEraserVisibleBox(visualSize);
        if (!displayPoint) {
          return learnerPaintAutoEraserOffscreenDisplayPoint(visualSize, index);
        }
        const edges = [
          { side: 0, distance: Math.abs(displayPoint.y - box.top) },
          { side: 1, distance: Math.abs(box.right - displayPoint.x) },
          { side: 2, distance: Math.abs(box.bottom - displayPoint.y) },
          { side: 3, distance: Math.abs(displayPoint.x - box.left) },
        ].sort((a, b) => a.distance - b.distance);
        const side = edges[Math.min(edges.length - 1, Math.random() < 0.74 ? 0 : 1)].side;
        return learnerPaintAutoEraserOffscreenDisplayPoint(visualSize, index, side, displayPoint);
      };

      const positionLearnerPaintAutoEraserDisplayNode = (node, displayPoint, angle = 0, visualSize = 48, scale = 1) => {
        if (!node || !displayPoint) {
          return;
        }
        const safeAngle = Number.isFinite(angle) ? angle : 0;
        const safeScale = learnerPaintClamp(Number(scale || 1), 0.72, 1.16);
        const left = displayPoint.x - visualSize / 2;
        const top = displayPoint.y - visualSize / 2;
        node.style.transform = `translate3d(${left.toFixed(1)}px, ${top.toFixed(1)}px, 0) rotate(${safeAngle.toFixed(3)}rad) rotate(var(--auto-eraser-tilt)) scale(${safeScale.toFixed(3)})`;
      };

      const positionLearnerPaintAutoEraserNode = (node, point, angle = 0, visualSize = 48) => {
        const displayPoint = learnerPaintDisplayPoint(point);
        if (!node || !displayPoint) {
          return;
        }
        positionLearnerPaintAutoEraserDisplayNode(node, displayPoint, angle, visualSize, 1);
      };

      const eraseLearnerPaintAutoSegment = (from, to, eraserSize = 36) => {
        const ctx = learnerPaintBufferCtx();
        if (!ctx) {
          return;
        }
        ctx.save();
        ctx.globalCompositeOperation = "destination-out";
        ctx.lineWidth = eraserSize;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = "#000";
        ctx.fillStyle = "#000";
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(to.x, to.y, eraserSize / 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      };

      const runLearnerPaintSmartErasers = () => new Promise((resolve) => {
        const ctx = learnerPaintBufferCtx();
        if (!ctx || !learnerPaintBufferCanvas || !paintCanvas) {
          resolve(false);
          return;
        }
        const eraserSize = Math.max(24, learnerPaintStrokeSize(true) * 1.35);
        const visualSize = 48;
        const canvasRect = paintCanvas.getBoundingClientRect();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        const canvasScale = Math.min(
          Math.max(0.01, Number(canvasRect.width || 0) / Math.max(1, boardWidth)),
          Math.max(0.01, Number(canvasRect.height || 0) / Math.max(1, boardHeight))
        );
        const eraserCursorDiameter = Math.max(14, eraserSize * canvasScale);
        const ringSize = learnerPaintClamp(eraserCursorDiameter * 2.2, visualSize * 1.25, visualSize * 2.25);
        const bounds = learnerPaintAutoEraseBounds(eraserSize).slice(0, 6);
        if (!bounds.length) {
          resolve(false);
          return;
        }
        const tracks = bounds.map((box, index) => {
          const track = learnerPaintAutoEraseTrack(learnerPaintAutoErasePath(box, eraserSize));
          const firstBoardPoint = track.path[0] || { x: box.x, y: box.y };
          const lastBoardPoint = track.path[track.path.length - 1] || firstBoardPoint;
          const enterTo = learnerPaintDisplayPoint(firstBoardPoint) || { x: 0, y: 0 };
          const exitFrom = learnerPaintDisplayPoint(lastBoardPoint) || enterTo;
          return {
            ...track,
            delay: 0,
            enterFrom: learnerPaintAutoEraserOffscreenDisplayPoint(visualSize, index),
            enterTo,
            entryDuration: learnerPaintClamp(1320 + Math.random() * 520 + index * 70, 1320, 2400),
            duration: learnerPaintClamp(track.total * 2.65, 2600, 10500),
            exitFrom,
            exitTo: learnerPaintAutoEraserExitDisplayPoint(exitFrom, visualSize, index),
            exitDuration: learnerPaintClamp(660 + Math.random() * 280 + index * 28, 660, 1120),
            node: createLearnerPaintAutoEraserNode(visualSize, index, ringSize),
            last: null,
            done: false,
          };
        });
        const startedAt = performance.now();
        let lastRenderAt = 0;
        window.cancelAnimationFrame(learnerPaintAutoEraseFrame);
        const animate = (now) => {
          let active = false;
          let needsRender = false;
          tracks.forEach((track) => {
            if (track.done) {
              return;
            }
            const elapsed = now - startedAt - track.delay;
            if (elapsed < 0) {
              active = true;
              positionLearnerPaintAutoEraserDisplayNode(track.node, track.enterFrom, -0.35, visualSize, 0.88);
              return;
            }
            if (elapsed < track.entryDuration) {
              active = true;
              const entryProgress = learnerPaintClamp(elapsed / Math.max(1, track.entryDuration), 0, 1);
              const easedEntry = entryProgress * entryProgress * entryProgress * (entryProgress * (entryProgress * 6 - 15) + 10);
              const displayPoint = learnerPaintMixDisplayPoint(track.enterFrom, track.enterTo, easedEntry);
              const angle = Math.atan2(track.enterTo.y - track.enterFrom.y, track.enterTo.x - track.enterFrom.x || 1);
              positionLearnerPaintAutoEraserDisplayNode(track.node, displayPoint, angle, visualSize, 0.88 + easedEntry * 0.12);
              return;
            }
            const eraseElapsed = elapsed - track.entryDuration;
            if (eraseElapsed > track.duration) {
              const exitElapsed = eraseElapsed - track.duration;
              if (exitElapsed < track.exitDuration) {
                active = true;
                const exitProgress = learnerPaintClamp(exitElapsed / Math.max(1, track.exitDuration), 0, 1);
                const easedExit = exitProgress < 0.5
                  ? 2 * exitProgress * exitProgress
                  : 1 - Math.pow(-2 * exitProgress + 2, 2) / 2;
                const displayPoint = learnerPaintMixDisplayPoint(track.exitFrom, track.exitTo, easedExit);
                const angle = Math.atan2(track.exitTo.y - track.exitFrom.y, track.exitTo.x - track.exitFrom.x || 1);
                positionLearnerPaintAutoEraserDisplayNode(track.node, displayPoint, angle, visualSize, 1 - easedExit * 0.1);
                return;
              }
              track.done = true;
              if (track.node) {
                const node = track.node;
                track.node = null;
                window.setTimeout(() => node.remove(), 80);
              }
              return;
            }
            const progress = learnerPaintClamp(eraseElapsed / Math.max(1, track.duration), 0, 1);
            const eased = progress < 0.5
              ? 2 * progress * progress
              : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            const current = learnerPaintTrackPointAt(track, track.total * eased);
            const previous = track.last || current;
            if (Math.hypot(current.x - previous.x, current.y - previous.y) > 0.2) {
              eraseLearnerPaintAutoSegment(previous, current, eraserSize);
            } else {
              eraseLearnerPaintAutoSegment(current, current, eraserSize);
            }
            needsRender = true;
            const angle = Math.atan2(current.y - previous.y, current.x - previous.x || 1);
            positionLearnerPaintAutoEraserNode(track.node, current, angle, visualSize);
            track.last = current;
            active = true;
          });
          if (!active || (needsRender && now - lastRenderAt >= 25)) {
            lastRenderAt = now;
            renderLearnerPaint();
          }
          if (active) {
            learnerPaintAutoEraseFrame = window.requestAnimationFrame(animate);
            return;
          }
          tracks.forEach((track) => {
            if (track.node) {
              track.node.classList.remove("is-live");
              const node = track.node;
              track.node = null;
              window.setTimeout(() => node.remove(), 220);
            }
          });
          learnerPaintAutoEraseFrame = 0;
          resolve(true);
        };
        learnerPaintAutoEraseFrame = window.requestAnimationFrame(animate);
      });

      const runLearnerPaintClearSweep = (origin = null) => new Promise((resolve) => {
        void origin;
        runLearnerPaintSmartErasers().then(resolve).catch(() => resolve(false));
      });

      const clearLearnerPaint = async () => {
        if (learnerPaintClearAnimating) {
          return;
        }
        learnerPaintClearAnimating = true;
        if (paintClear) {
          paintClear.classList.add("is-clearing");
          paintClear.setAttribute("aria-busy", "true");
        }
        if (learnerPaintTextEditor) {
          commitLearnerPaintTextEditor();
        }
        commitLearnerPaintSelection();
        clearLearnerPaintSelectAnchor();
        learnerPaintPointer = null;
        learnerPaintSelectedId = "";
        setLearnerPaintSyncStatus("Auto erasers are clearing the board...");
        try {
          const animated = await runLearnerPaintClearSweep();
          if (!animated) {
            setLearnerPaintSyncStatus("Paint board is already clean.");
          }
        } finally {
          window.cancelAnimationFrame(learnerPaintAutoEraseFrame);
          learnerPaintAutoEraseFrame = 0;
          if (paintCanvas && paintCanvas.parentElement) {
            paintCanvas.parentElement.querySelectorAll(".ft-paint-auto-eraser").forEach((node) => node.remove());
          }
          learnerPaintObjects.splice(0, learnerPaintObjects.length);
          learnerPaintSelection = null;
          const ctx = learnerPaintBufferCtx();
          if (ctx && learnerPaintBufferCanvas) {
            ctx.clearRect(0, 0, learnerPaintBufferCanvas.width, learnerPaintBufferCanvas.height);
          }
          renderLearnerPaint();
          scheduleLearnerPaintSync(80);
          if (paintClear) {
            paintClear.classList.remove("is-clearing");
            paintClear.removeAttribute("aria-busy");
          }
          learnerPaintClearAnimating = false;
        }
      };

      const deleteLearnerPaintSelection = () => {
        if (!learnerPaintSelection) {
          setLearnerPaintSyncStatus("Select or insert a picture first.");
          return;
        }
        learnerPaintSelection = null;
        learnerPaintPointer = null;
        renderLearnerPaint();
        scheduleLearnerPaintSync(80);
      };

      const addLearnerPaintImageFromDataUrl = (dataUrl) => {
        const source = String(dataUrl || "");
        if (!source.startsWith("data:image/")) {
          setLearnerPaintSyncStatus("Clipboard does not contain an image.");
          return;
        }
        commitLearnerPaintSelection();
        cancelLearnerPaintTextEditor();
        learnerPaintEnsureBuffer();
        const image = new Image();
        image.onload = () => {
          const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
          const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
          const naturalWidth = Math.max(1, image.naturalWidth || image.width || boardWidth);
          const naturalHeight = Math.max(1, image.naturalHeight || image.height || boardHeight);
          const width = Math.max(24, Math.round(naturalWidth));
          const height = Math.max(24, Math.round(naturalHeight));
          const canvas = document.createElement("canvas");
          canvas.width = naturalWidth;
          canvas.height = naturalHeight;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(image, 0, 0, naturalWidth, naturalHeight);
          }
          learnerPaintSelection = {
            x: Math.round(learnerPaintClamp((boardWidth - width) / 2, 0, Math.max(0, boardWidth - Math.min(width, boardWidth)))),
            y: Math.round(learnerPaintClamp((boardHeight - height) / 2, 0, Math.max(0, boardHeight - Math.min(height, boardHeight)))),
            w: width,
            h: height,
            imageData: null,
            canvas,
            kind: "image",
          };
          setLearnerPaintMode("select");
          renderLearnerPaint();
          scheduleLearnerPaintSync(120);
          setLearnerPaintSyncStatus("Picture inserted. Drag it or pull the corner to resize.");
        };
        image.onerror = () => setLearnerPaintSyncStatus("Could not load picture.");
        image.src = source;
      };

      const addLearnerPaintImageFile = (file) => {
        if (!file || !String(file.type || "").startsWith("image/")) {
          setLearnerPaintSyncStatus("Choose an image file.");
          return;
        }
        const reader = new FileReader();
        reader.onload = () => addLearnerPaintImageFromDataUrl(String(reader.result || ""));
        reader.onerror = () => setLearnerPaintSyncStatus("Could not read picture.");
        reader.readAsDataURL(file);
      };

      const pasteLearnerPaintImageFromClipboard = async () => {
        if (navigator.clipboard && navigator.clipboard.read) {
          try {
            const items = await navigator.clipboard.read();
            for (const item of items) {
              const imageType = item.types.find((type) => String(type || "").startsWith("image/"));
              if (imageType) {
                const blob = await item.getType(imageType);
                addLearnerPaintImageFile(blob);
                return;
              }
            }
          } catch (error) {
          }
        }
        setLearnerPaintSyncStatus("Copy an image, then press Ctrl+V while Paint is open.");
      };

      const learnerPaintResolutionScale = () => Math.max(1, Math.min(
        LEARNER_PAINT_BOARD_WIDTH / 1200,
        LEARNER_PAINT_BOARD_HEIGHT / 720
      ));

      const learnerPaintCurrentSize = () => learnerPaintModeSize(learnerPaintMode);

      const learnerPaintStrokeSize = (eraser = false) => (
        eraser
          ? Math.max(12, learnerPaintEraserSize * 2.6 * learnerPaintResolutionScale())
          : Math.max(1, learnerPaintPenSize * learnerPaintResolutionScale())
      );

      const learnerPaintCurrentTextSize = () => learnerPaintClamp(
        (14 + learnerPaintCurrentSize() * 2.2) * learnerPaintResolutionScale(),
        16 * learnerPaintResolutionScale(),
        82 * learnerPaintResolutionScale()
      );

      const drawLearnerPaintDotToBuffer = (point, eraser = false) => {
        const ctx = learnerPaintBufferCtx();
        if (!ctx) {
          return;
        }
        const sizeValue = learnerPaintStrokeSize(eraser);
        ctx.save();
        ctx.globalCompositeOperation = eraser ? "destination-out" : "source-over";
        ctx.fillStyle = paintColor && paintColor.value || "#0f172a";
        ctx.beginPath();
        ctx.arc(point.x, point.y, sizeValue / 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      };

      const drawLearnerPaintLineToBuffer = (from, to, eraser = false) => {
        const ctx = learnerPaintBufferCtx();
        if (!ctx) {
          return;
        }
        ctx.save();
        ctx.globalCompositeOperation = eraser ? "destination-out" : "source-over";
        ctx.lineWidth = learnerPaintStrokeSize(eraser);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = paintColor && paintColor.value || "#0f172a";
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
        ctx.restore();
      };

      const drawLearnerPaintTextToBuffer = (options = {}) => {
        const text = String(options.text == null ? "" : options.text).trim();
        if (!text) {
          return;
        }
        const ctx = learnerPaintBufferCtx();
        if (!ctx) {
          return;
        }
        const size = Math.max(10, Number(options.size || learnerPaintCurrentTextSize()));
        const lines = learnerPaintTextLines(text);
        ctx.save();
        ctx.fillStyle = options.color || paintColor && paintColor.value || "#0f172a";
        ctx.font = `900 ${size}px Inter, Segoe UI, system-ui, sans-serif`;
        ctx.textBaseline = "top";
        lines.forEach((line, index) => {
          ctx.fillText(line || " ", Number(options.x || 0), Number(options.y || 0) + index * size * 1.24);
        });
        ctx.restore();
      };

      const cancelLearnerPaintTextEditor = () => {
        if (learnerPaintTextEditor) {
          learnerPaintTextEditor.remove();
          learnerPaintTextEditor = null;
        }
      };

      const commitLearnerPaintTextEditor = () => {
        const editor = learnerPaintTextEditor;
        if (!editor) {
          return;
        }
        learnerPaintTextEditor = null;
        const text = String(editor.value || "").trim();
        if (text) {
          drawLearnerPaintTextToBuffer({
            text,
            x: Number(editor.dataset.paintX || 0),
            y: Number(editor.dataset.paintY || 0),
            color: editor.dataset.paintColor || paintColor && paintColor.value || "#0f172a",
            size: Number(editor.dataset.paintSize || learnerPaintCurrentTextSize()),
          });
          if (paintTextInput) {
            paintTextInput.value = text;
          }
        }
        editor.remove();
        renderLearnerPaint();
        scheduleLearnerPaintSync(120);
      };

      const showLearnerPaintTextEditor = (point) => {
        commitLearnerPaintSelection();
        cancelLearnerPaintTextEditor();
        if (!paintCanvas) {
          return;
        }
        const stage = paintCanvas.parentElement;
        if (!stage) {
          return;
        }
        const canvasRect = paintCanvas.getBoundingClientRect();
        const stageRect = stage.getBoundingClientRect();
        const size = learnerPaintCurrentTextSize();
        learnerPaintEnsureBuffer();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        const displayX = point.x * canvasRect.width / Math.max(1, boardWidth);
        const displayY = point.y * canvasRect.height / Math.max(1, boardHeight);
        const displaySize = learnerPaintClamp(size * Math.min(
          canvasRect.width / Math.max(1, boardWidth),
          canvasRect.height / Math.max(1, boardHeight)
        ), 12, 72);
        const editor = document.createElement("textarea");
        editor.className = "ft-paint-text-editor";
        editor.value = String(paintTextInput && paintTextInput.value || "").trim();
        editor.placeholder = "Type text";
        editor.dataset.paintX = String(point.x);
        editor.dataset.paintY = String(point.y);
        editor.dataset.paintColor = paintColor && paintColor.value || "#0f172a";
        editor.dataset.paintSize = String(size);
        editor.style.left = `${learnerPaintClamp(canvasRect.left - stageRect.left + displayX, 12, Math.max(12, stageRect.width - 180))}px`;
        editor.style.top = `${learnerPaintClamp(canvasRect.top - stageRect.top + displayY, 12, Math.max(12, stageRect.height - 76))}px`;
        editor.style.fontSize = `${displaySize}px`;
        editor.style.color = editor.dataset.paintColor;
        ["pointerdown", "mousedown", "click", "touchstart"].forEach((name) => {
          editor.addEventListener(name, (event) => event.stopPropagation());
        });
        editor.addEventListener("keydown", (event) => {
          event.stopPropagation();
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            commitLearnerPaintTextEditor();
          } else if (event.key === "Escape") {
            event.preventDefault();
            cancelLearnerPaintTextEditor();
            renderLearnerPaint();
          }
        });
        editor.addEventListener("input", () => {
          if (paintTextInput) {
            paintTextInput.value = editor.value;
          }
        });
        editor.addEventListener("blur", () => {
          window.setTimeout(() => {
            if (learnerPaintTextEditor === editor) {
              commitLearnerPaintTextEditor();
            }
          }, 80);
        });
        stage.appendChild(editor);
        learnerPaintTextEditor = editor;
        editor.focus({ preventScroll: true });
        editor.select();
        window.setTimeout(() => editor.focus({ preventScroll: true }), 30);
      };

      const beginLearnerPaintStroke = (point) => {
        commitLearnerPaintSelection();
        cancelLearnerPaintTextEditor();
        const eraser = learnerPaintMode === "eraser";
        drawLearnerPaintDotToBuffer(point, eraser);
        learnerPaintPointer = { type: "draw", last: point, eraser };
        renderLearnerPaint();
      };

      const createLearnerPaintSelection = (rect) => {
        const safeRect = {
          x: Math.round(learnerPaintClamp(rect.x, 0, learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : rect.x)),
          y: Math.round(learnerPaintClamp(rect.y, 0, learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : rect.y)),
          w: Math.round(Math.max(0, rect.w)),
          h: Math.round(Math.max(0, rect.h)),
        };
        if (!learnerPaintBufferCanvas || safeRect.w < 5 || safeRect.h < 5) {
          learnerPaintSelection = null;
          return;
        }
        safeRect.w = Math.min(safeRect.w, learnerPaintBufferCanvas.width - safeRect.x);
        safeRect.h = Math.min(safeRect.h, learnerPaintBufferCanvas.height - safeRect.y);
        if (safeRect.w < 5 || safeRect.h < 5) {
          learnerPaintSelection = null;
          return;
        }
        const ctx = learnerPaintBufferCtx();
        const imageData = ctx.getImageData(safeRect.x, safeRect.y, safeRect.w, safeRect.h);
        ctx.clearRect(safeRect.x, safeRect.y, safeRect.w, safeRect.h);
        learnerPaintSelection = {
          ...safeRect,
          imageData,
          canvas: learnerPaintSelectionCanvas(imageData),
        };
      };

      const handleLearnerPaintSelectPoint = (point) => {
        if (!point) {
          return;
        }
        if (!learnerPaintSelectFirstPoint) {
          clearLearnerPaintSelectAnchor();
          learnerPaintSelectFirstPoint = { x: point.x, y: point.y };
          learnerPaintSelectMarkerNode = spawnLearnerPaintSelectPoint(learnerPaintSelectFirstPoint, 1, true);
          setLearnerPaintSyncStatus("Select the second point to cast a frame.");
          return;
        }
        const firstPoint = { ...learnerPaintSelectFirstPoint };
        const secondPoint = { x: point.x, y: point.y };
        const rect = learnerPaintRect(firstPoint, secondPoint);
        spawnLearnerPaintSelectPoint(secondPoint, 2, false);
        window.setTimeout(() => {
          clearLearnerPaintSelectAnchor();
          if (rect.w < 5 || rect.h < 5) {
            setLearnerPaintSyncStatus("Selection is too small.");
            renderLearnerPaint();
            return;
          }
          spawnLearnerPaintSelectFrameCast(rect);
          window.setTimeout(() => {
            createLearnerPaintSelection(rect);
            renderLearnerPaint();
            scheduleLearnerPaintSync(120);
          }, 320);
        }, 620);
      };

      const handleLearnerPaintPointerDown = (event) => {
        if (!paintCanvas || !learnerPaintOpen) {
          return;
        }
        event.preventDefault();
        const point = learnerPaintCanvasPoint(event);
        updateLearnerPaintToolCursor(event, true);
        try {
          paintCanvas.setPointerCapture(event.pointerId);
        } catch (error) {}
        if (learnerPaintMode === "pen" || learnerPaintMode === "eraser") {
          if (learnerPaintMode === "pen") {
            spawnLearnerPaintPenDust(point);
          } else {
            setLearnerPaintEraserCursorActive(true);
          }
          beginLearnerPaintStroke(point);
          return;
        }
        if (learnerPaintMode === "text") {
          spawnLearnerPaintToolBurst(point, "text");
          showLearnerPaintTextEditor(point);
          return;
        }
        cancelLearnerPaintTextEditor();
        const selectionBounds = learnerPaintSelectionBounds();
        const handleBounds = selectionBounds ? learnerPaintHandleBounds(selectionBounds) : null;
        if (handleBounds && learnerPaintPointInBounds(point, handleBounds, 2)) {
          clearLearnerPaintSelectAnchor();
          learnerPaintPointer = {
            type: "resize-selection",
            start: point,
            origin: {
              x: learnerPaintSelection.x,
              y: learnerPaintSelection.y,
              w: learnerPaintSelection.w,
              h: learnerPaintSelection.h,
            },
          };
          return;
        }
        if (selectionBounds && learnerPaintPointInBounds(point, selectionBounds, 0)) {
          clearLearnerPaintSelectAnchor();
          learnerPaintPointer = {
            type: "move-selection",
            start: point,
            origin: { x: learnerPaintSelection.x, y: learnerPaintSelection.y },
          };
          return;
        }
        if (learnerPaintSelection) {
          commitLearnerPaintSelection();
        }
        learnerPaintPointer = null;
        handleLearnerPaintSelectPoint(point);
        renderLearnerPaint();
      };

      const handleLearnerPaintPointerMove = (event) => {
        if (!paintCanvas || !learnerPaintPointer) {
          return;
        }
        event.preventDefault();
        const point = learnerPaintCanvasPoint(event);
        if (learnerPaintPointer.type === "draw") {
          const lastPoint = learnerPaintPointer.last || point;
          if (Math.hypot(point.x - lastPoint.x, point.y - lastPoint.y) >= 0.8) {
            drawLearnerPaintLineToBuffer(lastPoint, point, Boolean(learnerPaintPointer.eraser));
            learnerPaintPointer.last = point;
            renderLearnerPaint();
            if (learnerPaintPointer.eraser) {
              setLearnerPaintEraserCursorActive(true);
            } else {
              spawnLearnerPaintPenDust(point);
            }
          }
          return;
        }
        if (learnerPaintPointer.type === "select-region") {
          learnerPaintPointer.current = point;
          renderLearnerPaint();
          return;
        }
        if (learnerPaintPointer.type === "move-selection" && learnerPaintSelection) {
          const dx = point.x - learnerPaintPointer.start.x;
          const dy = point.y - learnerPaintPointer.start.y;
          const maxX = Math.max(0, (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : paintCanvas.clientWidth) - learnerPaintSelection.w);
          const maxY = Math.max(0, (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : paintCanvas.clientHeight) - learnerPaintSelection.h);
          learnerPaintSelection.x = learnerPaintClamp(learnerPaintPointer.origin.x + dx, 0, maxX);
          learnerPaintSelection.y = learnerPaintClamp(learnerPaintPointer.origin.y + dy, 0, maxY);
          renderLearnerPaint();
          scheduleLearnerPaintSync(180);
          return;
        }
        if (learnerPaintPointer.type === "resize-selection" && learnerPaintSelection) {
          const dx = point.x - learnerPaintPointer.start.x;
          const dy = point.y - learnerPaintPointer.start.y;
          const origin = learnerPaintPointer.origin || learnerPaintSelection;
          const maxW = Math.max(12, (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : paintCanvas.clientWidth) - origin.x);
          const maxH = Math.max(12, (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : paintCanvas.clientHeight) - origin.y);
          learnerPaintSelection.w = learnerPaintClamp(origin.w + dx, 12, maxW);
          learnerPaintSelection.h = learnerPaintClamp(origin.h + dy, 12, maxH);
          renderLearnerPaint();
          scheduleLearnerPaintSync(180);
        }
      };

      const handleLearnerPaintPointerEnd = (event) => {
        if (!paintCanvas) {
          return;
        }
        try {
          paintCanvas.releasePointerCapture(event.pointerId);
        } catch (error) {}
        if (!learnerPaintPointer) {
          setLearnerPaintEraserCursorActive(false);
          return;
        }
        const pointerType = learnerPaintPointer.type;
        if (learnerPaintPointer.type === "select-region") {
          const rect = learnerPaintRect(learnerPaintPointer.start, learnerPaintPointer.current || learnerPaintPointer.start);
          createLearnerPaintSelection(rect);
          renderLearnerPaint();
        }
        if (pointerType === "move-selection" || pointerType === "resize-selection") {
          renderLearnerPaint();
        }
        learnerPaintPointer = null;
        setLearnerPaintEraserCursorActive(false);
        if (pointerType === "draw" || pointerType === "move-selection" || pointerType === "resize-selection") {
          scheduleLearnerPaintSync(120);
        }
      };

      const learnerChatChannelConfig = (mode = "en") => {
        const vietnamese = mode === "vi";
        return {
          mode: vietnamese ? "vi" : "en",
          input: vietnamese ? chatViInput : chatInput,
          button: vietnamese ? chatViSend : chatSend,
          audioEnabled: vietnamese ? learnerChatViAudioEnabled : learnerChatAudioEnabled,
          voice: vietnamese ? (learnerChatViVoice || "edge:vi-VN-NamMinhNeural") : (learnerChatVoice || "male-us"),
          voiceLabel: vietnamese ? (learnerChatViVoiceLabel || "") : (learnerChatVoiceLabel || ""),
        };
      };

      const activeLearnerChatMode = () => {
        if (document.activeElement === chatViInput || document.activeElement === chatViVoiceSelect || document.activeElement === chatViAudioToggle) {
          return "vi";
        }
        if (document.activeElement === chatInput || document.activeElement === chatVoiceSelect || document.activeElement === chatAudioToggle) {
          return "en";
        }
        const viDraft = String(chatViInput && chatViInput.value || "").trim();
        const enDraft = String(chatInput && chatInput.value || "").trim();
        if (viDraft && !enDraft) {
          return "vi";
        }
        return "en";
      };

      const setLearnerChatSending = (disabled) => {
        if (chatViSend) {
          chatViSend.disabled = disabled;
        }
        if (chatSend) {
          chatSend.disabled = disabled;
        }
        if (chatMic && learnerChatRecorder && learnerChatRecorder.state === "recording") {
          chatMic.disabled = false;
        } else if (chatMic) {
          chatMic.disabled = disabled;
        }
      };

      // 2026-07-20: reuse the same operation ID after a lost response so Server 2 can return the committed message.
      const createLearnerChatOperationId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
          return `chat-${window.crypto.randomUUID()}`;
        }
        return `chat-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
      };

      const sendLearnerChat = async (mode = "en") => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de gui tin nhan.");
          return;
        }
        const config = learnerChatChannelConfig(mode);
        const text = String(config.input && config.input.value || "").trim();
        if (!text) {
          return;
        }
        setLearnerChatSending(true);
        setLearnerChatStatus("Sending...");
        const operationKey = `${config.mode}:${text}`;
        if (!learnerChatPendingOperation || learnerChatPendingOperation.key !== operationKey) {
          learnerChatPendingOperation = { key: operationKey, id: createLearnerChatOperationId() };
        }
        try {
          const result = await fetchAuthJson("/chat/send", {
            method: "POST",
            body: JSON.stringify({
              text,
              language: config.mode,
              audio_enabled: Boolean(config.audioEnabled),
              voice: config.voice,
              voice_label: config.voiceLabel,
              operation_id: learnerChatPendingOperation.id,
            }),
          });
          if (config.input) {
            config.input.value = "";
          }
          appendLearnerChatMessages([result.payload && result.payload.message].filter(Boolean));
          learnerChatPendingOperation = null;
          setLearnerChatStatus("");
          void pollLearnerChat();
        } catch (error) {
          setLearnerChatStatus(error && error.message ? error.message : "Could not send message.", "error");
        } finally {
          setLearnerChatSending(false);
        }
      };

      const uploadLearnerChatFiles = async (fileList, mode = "", options = {}) => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de gui tep.");
          return;
        }
        const files = Array.from(fileList || []).filter(Boolean);
        if (!files.length) {
          return;
        }
        const config = learnerChatChannelConfig(mode || activeLearnerChatMode());
        const includeDraft = options.includeDraft !== false;
        setLearnerChatSending(true);
        if (chatAttach) {
          chatAttach.disabled = true;
        }
        const draft = includeDraft ? String(config.input && config.input.value || "").trim() : "";
        setLearnerChatStatus(options.status || `Uploading ${files.length} file${files.length > 1 ? "s" : ""}...`);
        try {
          for (let index = 0; index < files.length; index += 1) {
            const form = new FormData();
            form.append("file", files[index], files[index].name || `attachment-${index + 1}`);
            if (index === 0 && draft) {
              form.append("text", draft);
              form.append("language", config.mode);
              form.append("audio_enabled", config.audioEnabled ? "1" : "0");
              form.append("voice", config.voice);
              form.append("voice_label", config.voiceLabel);
            }
            const result = await fetchAuthForm("/chat/upload", form);
            appendLearnerChatMessages([result.payload && result.payload.message].filter(Boolean));
          }
          if (config.input && draft) {
            config.input.value = "";
          }
          setLearnerChatStatus("");
          void pollLearnerChat();
          return true;
        } catch (error) {
          setLearnerChatStatus(error && error.message ? error.message : "Could not upload file.", "error");
          return false;
        } finally {
          setLearnerChatSending(false);
          if (chatAttach) {
            chatAttach.disabled = false;
          }
          if (chatFileInput) {
            chatFileInput.value = "";
          }
        }
      };

      const learnerChatRecorderMimeType = () => {
        if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") {
          return "";
        }
        return [
          "audio/webm;codecs=opus",
          "audio/webm",
          "audio/mp4",
          "audio/ogg;codecs=opus",
        ].find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
      };

      const learnerChatAudioExtension = (mime = "") => {
        const value = clean(mime).toLowerCase();
        if (value.includes("mp4") || value.includes("m4a")) return "m4a";
        if (value.includes("ogg")) return "ogg";
        if (value.includes("wav")) return "wav";
        return "webm";
      };

      const encodeLearnerChatWav = (audioBuffer) => {
        const channels = Math.min(2, Math.max(1, audioBuffer.numberOfChannels || 1));
        const sampleRate = audioBuffer.sampleRate || 44100;
        const frames = audioBuffer.length || 0;
        const bytesPerSample = 2;
        const blockAlign = channels * bytesPerSample;
        const dataSize = frames * blockAlign;
        const buffer = new ArrayBuffer(44 + dataSize);
        const view = new DataView(buffer);
        const writeString = (offset, value) => {
          for (let i = 0; i < value.length; i += 1) {
            view.setUint8(offset + i, value.charCodeAt(i));
          }
        };
        writeString(0, "RIFF");
        view.setUint32(4, 36 + dataSize, true);
        writeString(8, "WAVE");
        writeString(12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, channels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * blockAlign, true);
        view.setUint16(32, blockAlign, true);
        view.setUint16(34, bytesPerSample * 8, true);
        writeString(36, "data");
        view.setUint32(40, dataSize, true);
        const channelData = Array.from({ length: channels }, (_, index) => audioBuffer.getChannelData(index));
        let offset = 44;
        for (let frame = 0; frame < frames; frame += 1) {
          for (let channel = 0; channel < channels; channel += 1) {
            const sample = Math.max(-1, Math.min(1, channelData[channel][frame] || 0));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
            offset += bytesPerSample;
          }
        }
        return new Blob([buffer], { type: "audio/wav" });
      };

      const learnerChatVoiceUploadFile = async (blob) => {
        const fallbackExtension = learnerChatAudioExtension(blob && blob.type);
        const fallback = () => new File([blob], `voice-message-${Date.now()}.${fallbackExtension}`, { type: (blob && blob.type) || "audio/webm" });
        try {
          const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
          if (!AudioContextCtor || !blob || typeof blob.arrayBuffer !== "function") {
            return fallback();
          }
          const context = new AudioContextCtor();
          try {
            const sourceBuffer = await blob.arrayBuffer();
            const audioBuffer = await new Promise((resolve, reject) => {
              const result = context.decodeAudioData(sourceBuffer.slice(0), resolve, reject);
              if (result && typeof result.then === "function") {
                result.then(resolve, reject);
              }
            });
            const wavBlob = encodeLearnerChatWav(audioBuffer);
            return new File([wavBlob], `voice-message-${Date.now()}.wav`, { type: "audio/wav" });
          } finally {
            if (typeof context.close === "function") {
              context.close().catch(() => {});
            }
          }
        } catch (error) {
          return fallback();
        }
      };

      const zipformerViInputDefaultLabel = (button) => {
        if (!button) return "Mic";
        if (!button.dataset.zipformerViIdleLabel) {
          button.dataset.zipformerViIdleLabel = clean(button.textContent) || "Mic";
        }
        return button.dataset.zipformerViIdleLabel || "Mic";
      };

      const setZipformerViInputButtonState = (button, state = "idle") => {
        if (!button) return;
        const idleLabel = zipformerViInputDefaultLabel(button);
        const recording = state === "recording";
        button.classList.toggle("is-recording", recording);
        button.classList.toggle("is-busy", state === "sending");
        button.setAttribute("aria-pressed", recording ? "true" : "false");
        button.disabled = state === "sending";
        if (state === "recording") {
          button.textContent = "Stop";
        } else if (state === "sending") {
          button.textContent = "...";
        } else {
          button.textContent = idleLabel;
        }
      };

      const setZipformerViInputStatus = (target, message = "", tone = "") => {
        const isError = tone === "error";
        if (target === aiAgentInput) {
          setAiAgentStatus(message || "Vietnamese Zipformer speech input is ready.", isError);
          return;
        }
        if (target === worldTrainingAnswer) {
          setSharedWorldStatus(message || "Vietnamese Zipformer speech input is ready.", isError ? "error" : "");
          return;
        }
        if (target === chatViInput || target === chatInput) {
          setLearnerChatStatus(message, tone);
          return;
        }
        if (
          typeof pdfEls !== "undefined"
          && pdfEls
          && target === pdfEls.audioText
          && typeof setPdfSharedAudioStatus === "function"
        ) {
          const speechLabel = typeof pdfSharedAudioSpeechLabel === "function" ? pdfSharedAudioSpeechLabel() : "Browser";
          const popupMessage = clean(message || "Browser speech input is ready.").replace(/Browser VI\+EN/g, speechLabel);
          const listening = /listening/i.test(clean(message || ""));
          setPdfSharedAudioStatus(popupMessage, { error: isError, busy: listening && !isError });
          return;
        }
        if (
          typeof pdfEls !== "undefined"
          && pdfEls
          && (target === pdfEls.askInput || target === pdfEls.askInputPreviewBody)
        ) {
          if (typeof setPdfStatus === "function") {
            setPdfStatus(message || "Vietnamese Zipformer speech input is ready.", isError);
          }
          if (pdfEls.agentFootnote && message) {
            pdfEls.agentFootnote.textContent = message;
          }
        }
      };

      const appendZipformerViTextToInput = (input, text) => {
        const value = clean(text);
        if (!input || !value) return false;
        const current = String(input.value || "");
        const start = typeof input.selectionStart === "number" ? input.selectionStart : current.length;
        const end = typeof input.selectionEnd === "number" ? input.selectionEnd : start;
        const needsSpaceBefore = start > 0 && current[start - 1] && !/\s/.test(current[start - 1]);
        const needsSpaceAfter = end < current.length && current[end] && !/\s/.test(current[end]);
        const inserted = `${needsSpaceBefore ? " " : ""}${value}${needsSpaceAfter ? " " : ""}`;
        input.value = `${current.slice(0, start)}${inserted}${current.slice(end)}`;
        const cursor = start + inserted.length;
        if (typeof input.setSelectionRange === "function") {
          input.setSelectionRange(cursor, cursor);
        }
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        if (typeof input.focus === "function") {
          input.focus();
        }
        if (
          typeof syncPdfAgentInputPreview === "function"
          && typeof pdfEls !== "undefined"
          && pdfEls
          && (input === pdfEls.askInput || input === pdfEls.askInputPreviewBody)
        ) {
          syncPdfAgentInputPreview();
        }
        return true;
      };

      const SPEECH_INPUT_MODE_KEY = "future_speech_input_mode";
      const SPEECH_INPUT_MODE_MIGRATION_KEY = "future_speech_input_mode_migrated";
      const speechInputModeControllers = [];
      const normalizeSpeechInputMode = (value) => clean(value).toLowerCase() === "zipformer" ? "zipformer" : "browser";
      const speechInputModeUserKey = () => {
        try {
          if (typeof aiAgentModeUserKey === "function") return aiAgentModeUserKey();
        } catch (error) {
        }
        const user = clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase();
        return user || "guest";
      };
      const speechInputModeStorageKey = (scope = "") => `${SPEECH_INPUT_MODE_KEY}:${clean(scope) || "default"}:${speechInputModeUserKey()}`;
      const speechInputModeControlForScope = (scope = "") => {
        const value = clean(scope);
        if (value === "ghost_ai_agent") return aiAgentSpeechMode;
        if (value === "learner_chat_vi_input") return chatViSpeechMode;
        if (value === "qm_city_training_answer") return worldTrainingSpeechMode;
        if (value === "ghost_eye_agent" && typeof pdfEls !== "undefined" && pdfEls) return pdfEls.askSpeechMode || null;
        return null;
      };
      const speechInputDefaultMode = () => "browser";
      const readSpeechInputMode = (scope = "", control = null) => {
        if (control && control.value) return normalizeSpeechInputMode(control.value);
        try {
          const key = speechInputModeStorageKey(scope);
          const stored = localStorage.getItem(key);
          if (stored) {
            const normalizedStored = normalizeSpeechInputMode(stored);
            if (clean(scope) === "ghost_eye_agent" && normalizedStored === "zipformer") {
              const migrationKey = `${SPEECH_INPUT_MODE_MIGRATION_KEY}:ghost_eye_agent:${speechInputModeUserKey()}`;
              if (localStorage.getItem(migrationKey) !== "1") {
                localStorage.setItem(key, "browser");
                localStorage.setItem(migrationKey, "1");
                return "browser";
              }
            }
            return normalizedStored;
          }
        } catch (error) {
        }
        const node = speechInputModeControlForScope(scope);
        if (node && node.value) return normalizeSpeechInputMode(node.value);
        return speechInputDefaultMode(scope);
      };
      const speechInputModeLabel = (mode = "browser") => normalizeSpeechInputMode(mode) === "zipformer" ? "Zipformer VI" : "Browser VI+EN";
      const applySpeechInputModeControlLabel = (control, mode = "browser") => {
        if (!control) return;
        const normalized = normalizeSpeechInputMode(mode);
        if ("value" in control) control.value = normalized;
        if (String(control.tagName || "").toLowerCase() === "button") {
          const label = speechInputModeLabel(normalized);
          control.textContent = label;
          control.setAttribute("aria-pressed", normalized === "zipformer" ? "true" : "false");
          control.title = `Speech input: ${label}`;
        }
      };
      const writeSpeechInputMode = (scope = "", mode = "browser") => {
        const normalized = normalizeSpeechInputMode(mode);
        try {
          localStorage.setItem(speechInputModeStorageKey(scope), normalized);
        } catch (error) {
        }
        return normalized;
      };
      const setSpeechInputButtonModeHint = (button, scope = "") => {
        if (!button) return;
        const mode = readSpeechInputMode(scope);
        const label = speechInputModeLabel(mode);
        button.dataset.speechInputMode = mode;
        button.setAttribute("aria-label", `${label} speech input`);
        button.title = `${label} speech input`;
      };
      const initSpeechInputModeControl = (control, scope = "", button = null) => {
        if (!control) return;
        const sync = () => {
          const saved = readSpeechInputMode(scope, null);
          applySpeechInputModeControlLabel(control, saved);
          setSpeechInputButtonModeHint(button, scope);
          if (clean(scope) === "ghost_eye_agent" && typeof syncPdfAgentInputPreview === "function") {
            syncPdfAgentInputPreview();
          }
        };
        sync();
        const applyChange = (modeValue) => {
          const nextMode = writeSpeechInputMode(scope, modeValue);
          applySpeechInputModeControlLabel(control, nextMode);
          if (nextMode === "zipformer" && browserSpeechInputRecognition && browserSpeechInputButton === button) {
            cancelBrowserMultilingualInputDictation();
          }
          setSpeechInputButtonModeHint(button, scope);
          if (clean(scope) === "ghost_eye_agent" && typeof syncPdfAgentInputPreview === "function") {
            syncPdfAgentInputPreview();
          }
          if (clean(scope) === "qm_city_training_answer") {
            try {
              if (typeof renderSharedWorldTraining === "function" && sharedWorldTrainingState) {
                renderSharedWorldTraining(sharedWorldTrainingState);
              }
            } catch (error) {
            }
          }
        };
        if (String(control.tagName || "").toLowerCase() === "button") {
          control.addEventListener("click", () => {
            const current = readSpeechInputMode(scope, control);
            applyChange(current === "zipformer" ? "browser" : "zipformer");
          });
        } else {
          control.addEventListener("change", () => {
            applyChange(control.value);
          });
        }
        speechInputModeControllers.push({ sync, scope, button });
      };
      const syncSpeechInputModeControlsForUser = () => {
        speechInputModeControllers.forEach((controller) => {
          try {
            controller.sync();
          } catch (error) {
          }
        });
      };
      const setBrowserSpeechInputButtonState = (button, state = "idle") => {
        if (!button) return;
        const idleLabel = zipformerViInputDefaultLabel(button);
        const recording = state === "recording";
        button.classList.toggle("is-recording", recording);
        button.classList.toggle("is-busy", state === "sending");
        button.setAttribute("aria-pressed", recording ? "true" : "false");
        button.disabled = state === "sending";
        if (state === "recording") {
          button.textContent = "Stop";
        } else if (state === "sending") {
          button.textContent = "...";
        } else {
          button.textContent = idleLabel;
        }
      };
      const setBrowserSpeechInputStatus = (target, message = "", tone = "") => {
        const isError = tone === "error";
        if (target === worldTrainingAnswer) {
          setSharedWorldStatus(message || "Browser VI+EN speech input is ready.", isError ? "error" : "");
          return;
        }
        if (target === worldBattleAnswer) {
          setSharedWorldStatus(message || "Battle speech input is ready.", isError ? "error" : "");
          return;
        }
        if (target === aiAgentInput) {
          setAiAgentStatus(message || "Browser VI+EN speech input is ready.", isError);
          return;
        }
        if (target === chatViInput || target === chatInput) {
          setLearnerChatStatus(message, tone);
          return;
        }
        if (
          typeof pdfEls !== "undefined"
          && pdfEls
          && (target === pdfEls.askInput || target === pdfEls.askInputPreviewBody)
        ) {
          if (typeof setPdfStatus === "function") {
            setPdfStatus(message || "Browser VI+EN speech input is ready.", isError);
          }
          if (pdfEls.agentFootnote && message) {
            pdfEls.agentFootnote.textContent = message;
          }
        }
      };
      const browserSpeechInputDebugLog = (stage = "", data = {}) => {
        try {
          const scope = clean((data && data.scope) || browserSpeechInputScope || "");
          if (scope !== "ghost_ai_agent" && scope !== "ghost_eye_agent") {
            return;
          }
          const row = {
            at: new Date().toISOString(),
            stage: clean(stage),
            scope,
            targetId: browserSpeechInputTarget && browserSpeechInputTarget.id || "",
            finalLength: clean(browserSpeechInputFinalText || "").length,
            interimLength: clean(browserSpeechInputInterimText || "").length,
            ...(data && typeof data === "object" ? data : {}),
          };
          window.__futureSpeechInputDebug = Array.isArray(window.__futureSpeechInputDebug)
            ? window.__futureSpeechInputDebug.slice(-79)
            : [];
          window.__futureSpeechInputDebug.push(row);
          if (window.localStorage && window.localStorage.getItem("future_debug_speech_input") === "1") {
            console.info("[Future Speech Input]", row);
          }
        } catch (error) {
        }
      };
      const selectedSharedWorldTrainingQuestion = () => {
        try {
          const selected = typeof worldTrainingSelectedSlime === "function" ? worldTrainingSelectedSlime() : null;
          return selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        } catch (error) {
          return {};
        }
      };
      const selectedSharedWorldBattleQuestion = () => {
        try {
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          return battle && battle.question && typeof battle.question === "object" ? battle.question : {};
        } catch (error) {
          return {};
        }
      };
      const sharedWorldBattleBrowserSpeechKind = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        return clean(row.training_kind || row.trainingKind || row.kind || row.battle_kind || row.battleKind || "").toLowerCase();
      };
      const sharedWorldBattleBrowserSpeechUsesVietnamese = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = sharedWorldBattleBrowserSpeechKind(row);
        return Boolean(kind === "translate_vi" || kind === "translate_vi_speech" || row.server_speech || row.serverSpeech);
      };
      const sharedWorldBattleBrowserSpeechExpectedText = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        if (sharedWorldBattleBrowserSpeechUsesVietnamese(row)) {
          return clean(row.answer_text || row.answerText || row.meaning || row.translation || row.vietnamese || row.answer || "");
        }
        return clean(row.read_text || row.readText || row.audio_text || row.audioText || row.source_text || row.sourceText || row.answer_text || row.answerText || row.answer || "");
      };
      const sharedWorldBrowserSpeechQuestionForTarget = (target) => {
        if (target === worldBattleAnswer) {
          return selectedSharedWorldBattleQuestion();
        }
        return selectedSharedWorldTrainingQuestion();
      };
      const sharedWorldBrowserSpeechExpectedTextForTarget = (target, question = {}) => {
        if (target === worldBattleAnswer) {
          return sharedWorldBattleBrowserSpeechExpectedText(question);
        }
        return typeof sharedWorldTrainingSpeechText === "function"
          ? sharedWorldTrainingSpeechText(question)
          : clean(question.answer_text || question.answerText || question.answer || question.meaning || "");
      };
      const sharedWorldBrowserSpeechUsesVietnameseForTarget = (target, question = {}) => {
        if (target === worldBattleAnswer) {
          return sharedWorldBattleBrowserSpeechUsesVietnamese(question);
        }
        return Boolean(
          typeof sharedWorldTrainingQuestionSupportsVietnameseSpeech === "function"
          && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)
        );
      };
      const qmCitySpeechTokenDebugLog = (stage = "", data = {}) => {
        try {
          const row = {
            at: new Date().toISOString(),
            stage: clean(stage),
            ...(data && typeof data === "object" ? data : {}),
          };
          window.__qmCitySpeechTokenDebug = Array.isArray(window.__qmCitySpeechTokenDebug)
            ? window.__qmCitySpeechTokenDebug.slice(-79)
            : [];
          window.__qmCitySpeechTokenDebug.push(row);
          console.info("[QM-City Browser VI+EN]", row);
        } catch (error) {
        }
      };
      const browserWorldTrainingSpeechLayer = () => {
        if (!worldCard) {
          qmCitySpeechTokenDebugLog("layer_missing_world_card");
          return null;
        }
        let layer = worldCard.querySelector("#ft-world-training-speech-layer");
        if (!layer) {
          layer = document.createElement("div");
          layer.id = "ft-world-training-speech-layer";
          layer.className = "ft-world-training-speech-layer";
          layer.setAttribute("aria-hidden", "true");
          worldCard.appendChild(layer);
          qmCitySpeechTokenDebugLog("layer_created");
        }
        return layer;
      };
      const browserWorldTrainingSpeechAnchorPoint = (layer = null) => {
        const anchor = document.querySelector(".ft-world-card.is-training-map .ft-world-player.is-me .ft-world-fireball")
          || document.querySelector(".ft-world-card.is-training-map .ft-world-player.is-me")
          || document.querySelector(".ft-world-player.is-me .ft-world-fireball")
          || document.querySelector(".ft-world-player.is-me");
        if (!anchor || !layer || !worldCard || !anchor.getBoundingClientRect || !worldCard.getBoundingClientRect) {
          qmCitySpeechTokenDebugLog("anchor_missing", {
            hasAnchor: Boolean(anchor),
            hasLayer: Boolean(layer),
            hasWorldCard: Boolean(worldCard),
            isTrainingMap: Boolean(worldCard && worldCard.classList && worldCard.classList.contains("is-training-map")),
          });
          return null;
        }
        const layerRect = layer.getBoundingClientRect();
        const rect = anchor.getBoundingClientRect();
        const point = {
          x: Math.max(12, Math.min(Math.max(12, layerRect.width - 12), rect.left + rect.width * 0.5 - layerRect.left)),
          y: Math.max(24, Math.min(Math.max(24, layerRect.height - 12), rect.top - layerRect.top - 8)),
        };
        qmCitySpeechTokenDebugLog("anchor_point", {
          x: Math.round(point.x),
          y: Math.round(point.y),
          anchorClass: clean(anchor.className || ""),
        });
        return point;
      };
      const browserWorldTrainingNormalizeSpeechToken = (value = "") => clean(value)
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[\u0111\u0110]/g, "d")
        .toLowerCase()
        .replace(/['\u2019]/g, "")
        .replace(/[^a-z0-9]+/g, "");
      const browserWorldTrainingSpeechTokenParts = (text = "") => Array.from(clean(text).matchAll(/[\p{L}\p{N}]+(?:['\u2019][\p{L}\p{N}]+)?/gu))
        .map((match) => ({ text: clean(match[0]), norm: browserWorldTrainingNormalizeSpeechToken(match[0]) }))
        .filter((row) => row.norm);
      const browserWorldTrainingSpeechTokenRows = (text = "", expectedText = "") => {
        const expectedCounts = new Map();
        browserWorldTrainingSpeechTokenParts(expectedText).forEach((row) => {
          expectedCounts.set(row.norm, (expectedCounts.get(row.norm) || 0) + 1);
        });
        return browserWorldTrainingSpeechTokenParts(text).map((row) => {
          const count = expectedCounts.get(row.norm) || 0;
          if (count > 0) {
            expectedCounts.set(row.norm, count - 1);
            return { ...row, status: "correct" };
          }
          return { ...row, status: "wrong" };
        });
      };
      const spawnBrowserWorldTrainingSpeechTokenBlock = (token = {}, index = 0) => {
        const layer = browserWorldTrainingSpeechLayer();
        const point = browserWorldTrainingSpeechAnchorPoint(layer);
        const text = clean(token && token.text || "");
        if (!layer || !point || !text) {
          qmCitySpeechTokenDebugLog("token_spawn_failed", {
            hasLayer: Boolean(layer),
            hasPoint: Boolean(point),
            text,
          });
          return false;
        }
        const status = clean(token.status || "").toLowerCase() === "correct" ? "correct" : "wrong";
        const block = document.createElement("span");
        block.className = `ft-world-training-speech-token-flight is-${status}`;
        block.textContent = text.length > 18 ? `${text.slice(0, 16)}...` : text;
        const drift = ((index % 5) - 2) * 12;
        block.style.setProperty("--token-x", `${Math.round(point.x)}px`);
        block.style.setProperty("--token-y", `${Math.round(point.y)}px`);
        block.style.setProperty("--token-drift-small", `${Math.round(drift * 0.18)}px`);
        block.style.setProperty("--token-drift-mid", `${Math.round(drift * 0.78)}px`);
        block.style.setProperty("--token-drift", `${drift}px`);
        layer.appendChild(block);
        qmCitySpeechTokenDebugLog("token_spawned", {
          text,
          status,
          index,
          x: Math.round(point.x),
          y: Math.round(point.y),
        });
        window.setTimeout(() => block.remove(), 1350);
        return true;
      };
      const setBrowserWorldTrainingSpeechMicBeacon = (active = false) => {
        const layer = browserWorldTrainingSpeechLayer();
        const existing = layer && layer.querySelector ? layer.querySelector(".ft-world-training-speech-mic-beacon") : null;
        if (!active) {
          if (existing) {
            existing.remove();
            qmCitySpeechTokenDebugLog("mic_beacon_removed");
          }
          return false;
        }
        const point = browserWorldTrainingSpeechAnchorPoint(layer);
        if (!layer || !point) {
          qmCitySpeechTokenDebugLog("mic_beacon_failed", { hasLayer: Boolean(layer), hasPoint: Boolean(point) });
          return false;
        }
        const beacon = existing || document.createElement("span");
        if (!existing) {
          beacon.className = "ft-world-training-speech-mic-beacon";
          beacon.textContent = "MIC";
          layer.appendChild(beacon);
        }
        beacon.style.setProperty("--mic-x", `${Math.round(point.x)}px`);
        beacon.style.setProperty("--mic-y", `${Math.round(point.y)}px`);
        qmCitySpeechTokenDebugLog(existing ? "mic_beacon_positioned" : "mic_beacon_created", {
          x: Math.round(point.x),
          y: Math.round(point.y),
        });
        return true;
      };
      const renderBrowserWorldTrainingSpeechTokenFlights = (text = "", expectedText = "") => {
        const currentScreen = typeof targetCurrentScreen === "function" ? targetCurrentScreen() : "";
        if (currentScreen && currentScreen !== "world" && !(worldModal && worldModal.classList.contains("is-open"))) {
          qmCitySpeechTokenDebugLog("token_flights_skip_screen", { currentScreen });
          return false;
        }
        const rows = browserWorldTrainingSpeechTokenRows(text, expectedText);
        const previousCount = Math.max(0, Math.floor(Number(sharedWorldTrainingSpeech.browserFlightTokenCount || 0) || 0));
        qmCitySpeechTokenDebugLog("token_flights", {
          textLength: clean(text).length,
          expectedLength: clean(expectedText).length,
          rows: rows.length,
          previousCount,
          newRows: Math.max(0, rows.length - previousCount),
        });
        if (rows.length < previousCount) {
          sharedWorldTrainingSpeech.browserFlightTokenCount = rows.length;
          return false;
        }
        rows.slice(previousCount).forEach((row, offset) => {
          spawnBrowserWorldTrainingSpeechTokenBlock(row, previousCount + offset);
        });
        sharedWorldTrainingSpeech.browserFlightTokenCount = rows.length;
        return rows.length > previousCount;
      };
      const setBrowserWorldTrainingMicLive = (target, active = false) => {
        if (target !== worldTrainingAnswer && target !== worldBattleAnswer) {
          return false;
        }
        const shouldActivate = Boolean(active);
        if (!shouldActivate) {
          try {
            if (typeof setSharedWorldTrainingMicEnergy === "function") {
              setSharedWorldTrainingMicEnergy(false);
            }
            setBrowserWorldTrainingSpeechMicBeacon(false);
            if (worldTrainingAnswerForm) {
              worldTrainingAnswerForm.classList.remove("is-browser-listening");
            }
            if (worldBattleAnswerForm) {
              worldBattleAnswerForm.classList.remove("is-browser-listening");
            }
            sharedWorldTrainingSpeech.active = false;
            sharedWorldTrainingSpeech.passed = false;
          } catch (error) {
          }
          return true;
        }
        try {
          const question = sharedWorldBrowserSpeechQuestionForTarget(target);
          const expectedText = sharedWorldBrowserSpeechExpectedTextForTarget(target, question);
          if (!expectedText) {
            return false;
          }
          if (typeof setSharedWorldTrainingMicEnergy === "function") {
            setSharedWorldTrainingMicEnergy(true);
          }
          if (worldTrainingAnswerForm) {
            worldTrainingAnswerForm.classList.toggle("is-browser-listening", target === worldTrainingAnswer);
          }
          if (worldBattleAnswerForm) {
            worldBattleAnswerForm.classList.toggle("is-browser-listening", target === worldBattleAnswer);
          }
          sharedWorldTrainingSpeech.active = true;
          sharedWorldTrainingSpeech.passed = false;
          sharedWorldTrainingSpeech.posted = false;
          sharedWorldTrainingSpeech.revealTarget = false;
          sharedWorldTrainingSpeech.flightTokenCount = typeof sharedWorldTrainingSpeechExpectedWords === "function"
            ? sharedWorldTrainingSpeechExpectedWords(target && target.value || "").length
            : 0;
          sharedWorldTrainingSpeech.browserFlightTokenCount = browserWorldTrainingSpeechTokenParts(target && target.value || "").length;
          qmCitySpeechTokenDebugLog("mic_live_started", {
            questionKind: clean(question.training_kind || question.trainingKind || question.kind || ""),
            supportsVietnameseSpeech: sharedWorldBrowserSpeechUsesVietnameseForTarget(target, question),
            baseTokenCount: sharedWorldTrainingSpeech.browserFlightTokenCount,
          });
          return true;
        } catch (error) {
          qmCitySpeechTokenDebugLog("mic_live_start_error", { message: error && error.message ? error.message : String(error) });
          return false;
        }
      };
      const renderBrowserWorldTrainingSpeechOverhead = (text = "", target = browserSpeechInputTarget) => {
        if (target !== worldTrainingAnswer && target !== worldBattleAnswer) {
          return false;
        }
        try {
          const question = sharedWorldBrowserSpeechQuestionForTarget(target);
          const supportsVietnameseSpeech = sharedWorldBrowserSpeechUsesVietnameseForTarget(target, question);
          const expectedText = sharedWorldBrowserSpeechExpectedTextForTarget(target, question);
          if (!expectedText || typeof renderSharedWorldTrainingSpeechOverhead !== "function") {
            qmCitySpeechTokenDebugLog("overhead_skip", {
              reason: !expectedText ? "missing_expected_text" : "missing_overhead_renderer",
              questionKind: clean(question.training_kind || question.trainingKind || question.kind || ""),
              hasAnswerText: Boolean(clean(question.answer_text || question.answerText || "")),
              hasAnswer: Boolean(clean(question.answer || "")),
              textLength: clean(text).length,
            });
            return false;
          }
          const passRatio = typeof sharedWorldTrainingSpeechPassRatio === "function"
            ? sharedWorldTrainingSpeechPassRatio(question, expectedText)
            : 0.6;
          sharedWorldTrainingSpeech.expectedText = expectedText;
          sharedWorldTrainingSpeech.passRatio = passRatio;
          sharedWorldTrainingSpeech.hideTarget = Boolean(supportsVietnameseSpeech && sharedWorldTrainingSpeech.active && !sharedWorldTrainingSpeech.revealTarget);
          sharedWorldTrainingSpeech.scoringLanguage = supportsVietnameseSpeech ? "vi" : "en";
          sharedWorldTrainingSpeech.transcript = clean(text);
          sharedWorldTrainingSpeech.chunk = "";
          const result = typeof sharedWorldTrainingSpeechScoreBundle === "function"
            ? sharedWorldTrainingSpeechScoreBundle(question, text, expectedText, passRatio)
            : (typeof scoreSharedWorldTrainingSpeech === "function" ? scoreSharedWorldTrainingSpeech(text, expectedText, passRatio) : null);
          if (result && typeof result === "object") {
            result.review = result.review || (
              typeof sharedWorldTrainingVietnameseSpeechReview === "function"
                ? sharedWorldTrainingVietnameseSpeechReview(text, expectedText)
                : null
            );
          }
          renderSharedWorldTrainingSpeechOverhead(text, result);
          renderBrowserWorldTrainingSpeechTokenFlights(text, expectedText);
          if (target === worldTrainingAnswer && typeof renderSharedWorldTrainingServerSpeechStatus === "function") {
            const selected = typeof worldTrainingSelectedSlime === "function" ? worldTrainingSelectedSlime() : null;
            renderSharedWorldTrainingServerSpeechStatus(question, selected && selected.id);
          }
          qmCitySpeechTokenDebugLog("overhead_rendered", {
            questionKind: clean(question.training_kind || question.trainingKind || question.kind || ""),
            supportsVietnameseSpeech,
            expectedLength: clean(expectedText).length,
            textLength: clean(text).length,
          });
          return true;
        } catch (error) {
          qmCitySpeechTokenDebugLog("overhead_render_error", { message: error && error.message ? error.message : String(error) });
          return false;
        }
      };
      const browserSpeechInputLanguage = (target, scope = "", options = {}) => {
        const explicit = clean(options && options.language);
        if (explicit) return explicit;
        if (target === aiAgentInput || clean(scope) === "ghost_ai_agent" || clean(scope) === "ghost_eye_agent") return "vi-VN";
        if (target === worldTrainingAnswer) {
          const question = selectedSharedWorldTrainingQuestion();
          try {
            if (
              typeof sharedWorldTrainingQuestionSupportsVietnameseSpeech === "function"
              && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)
            ) {
              return "vi-VN";
            }
          } catch (error) {
          }
          try {
            if (
              typeof sharedWorldTrainingQuestionIsTranslateVi === "function"
              && sharedWorldTrainingQuestionIsTranslateVi(question)
            ) {
              return "vi-VN";
            }
          } catch (error) {
          }
          return "en-US";
        }
        if (target === worldBattleAnswer) {
          return sharedWorldBattleBrowserSpeechUsesVietnamese(selectedSharedWorldBattleQuestion()) ? "vi-VN" : "en-US";
        }
        if (
          typeof pdfEls !== "undefined"
          && pdfEls
          && target === pdfEls.audioText
          && typeof pdfSharedAudioSpeechLanguage === "function"
        ) {
          return pdfSharedAudioSpeechLanguage();
        }
        if (target === chatViInput || clean(scope) === "learner_chat_vi_input") return "vi-VN";
        return "vi-VN";
      };
      const suspendVietnameseTypingDuringBrowserSpeech = (target, scope = "") => {
        restoreVietnameseTypingAfterBrowserSpeech();
      };
      const restoreVietnameseTypingAfterBrowserSpeech = () => {
        const restore = browserSpeechInputTypingRestore;
        browserSpeechInputTypingRestore = null;
        if (!restore || !restore.target || !restore.target.dataset) {
          return;
        }
        if (restore.hadDatasetValue) {
          restore.target.dataset.vietnameseTypingActive = restore.previousValue;
        } else {
          delete restore.target.dataset.vietnameseTypingActive;
        }
        try {
          if (typeof syncVietnameseTypingSupportForUser === "function") {
            syncVietnameseTypingSupportForUser();
          }
        } catch (error) {
        }
      };
      const browserSpeechInputText = () => clean(`${browserSpeechInputFinalText || ""} ${browserSpeechInputInterimText || ""}`);
      const dispatchBrowserSpeechInputEvents = (input) => {
        if (!input) return;
        const hasDataset = Boolean(input.dataset);
        const hadDatasetValue = hasDataset && Object.prototype.hasOwnProperty.call(input.dataset, "vietnameseTypingActive");
        const previousValue = hasDataset ? input.dataset.vietnameseTypingActive || "" : "";
        if (hasDataset) {
          input.dataset.vietnameseTypingActive = "0";
        }
        try {
          input.dispatchEvent(new CustomEvent("future:speech-input-mutated", { bubbles: false }));
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
        } finally {
          if (hasDataset) {
            if (hadDatasetValue) {
              input.dataset.vietnameseTypingActive = previousValue;
            } else {
              delete input.dataset.vietnameseTypingActive;
            }
          }
        }
      };
      const browserSpeechInputSelectionPoint = (input) => {
        try {
          if (input && typeof input.selectionStart === "number") return input.selectionStart;
        } catch (error) {
        }
        return input && typeof input.value === "string" ? input.value.length : 0;
      };
      const browserSpeechInputSelectionRange = (input) => {
        const value = String(input && input.value || "");
        let start = value.length;
        let end = value.length;
        try {
          if (input && typeof input.selectionStart === "number") start = input.selectionStart;
          if (input && typeof input.selectionEnd === "number") end = input.selectionEnd;
        } catch (error) {
        }
        start = Math.max(0, Math.min(value.length, start));
        end = Math.max(start, Math.min(value.length, end));
        return { start, end };
      };
      const setBrowserSpeechInputSelection = (input, start = 0, end = start) => {
        if (!input || typeof input.setSelectionRange !== "function") return;
        const length = String(input.value || "").length;
        const safeStart = Math.max(0, Math.min(length, Math.floor(Number(start) || 0)));
        const safeEnd = Math.max(safeStart, Math.min(length, Math.floor(Number(end) || safeStart)));
        try {
          input.setSelectionRange(safeStart, safeEnd);
        } catch (error) {
        }
      };
      const browserSpeechInputFindDraftRange = (input) => {
        const value = String(input && input.value || "");
        const rawDraftText = String(browserSpeechInputDraftText || "");
        const trimmedDraftText = clean(browserSpeechInputInterimText || "");
        let start = browserSpeechInputDraftStart;
        let end = browserSpeechInputDraftEnd;
        const rangeText = start >= 0 && end >= start ? value.slice(start, end) : "";
        let found = Boolean(
          (rawDraftText || trimmedDraftText)
          && start >= 0
          && end >= start
          && end <= value.length
          && (
            (rawDraftText && rangeText === rawDraftText)
            || (trimmedDraftText && rangeText.trim() === trimmedDraftText)
          )
        );
        if (!found && (rawDraftText || trimmedDraftText)) {
          const needle = rawDraftText && value.includes(rawDraftText) ? rawDraftText : trimmedDraftText;
          const first = needle ? value.indexOf(needle) : -1;
          const last = needle ? value.lastIndexOf(needle) : -1;
          if (first >= 0 && first === last) {
            start = first;
            end = first + needle.length;
            found = true;
          }
        }
        return { found, start, end };
      };
      const resetBrowserSpeechInputDraftMemory = () => {
        browserSpeechInputDraftStart = -1;
        browserSpeechInputDraftEnd = -1;
        browserSpeechInputDraftText = "";
        browserSpeechInputInterimText = "";
      };
      const detachBrowserSpeechInputUserEditListener = () => {
        if (browserSpeechInputUserEditController) {
          try {
            browserSpeechInputUserEditController.abort();
          } catch (error) {
          }
        }
        if (browserSpeechInputUserEditTarget && typeof browserSpeechInputUserEditTarget.removeEventListener === "function") {
          try {
            browserSpeechInputUserEditTarget.removeEventListener("input", handleBrowserSpeechInputUserEdit);
            browserSpeechInputUserEditTarget.removeEventListener("click", handleBrowserSpeechInputUserEdit);
            browserSpeechInputUserEditTarget.removeEventListener("keyup", handleBrowserSpeechInputUserEdit);
            browserSpeechInputUserEditTarget.removeEventListener("select", handleBrowserSpeechInputUserEdit);
          } catch (error) {
          }
        }
        browserSpeechInputUserEditController = null;
        browserSpeechInputUserEditTarget = null;
      };
      const attachBrowserSpeechInputUserEditListener = (input) => {
        detachBrowserSpeechInputUserEditListener();
        if (!input || typeof input.addEventListener !== "function") return;
        browserSpeechInputUserEditTarget = input;
        try {
          browserSpeechInputUserEditController = new AbortController();
          input.addEventListener("input", handleBrowserSpeechInputUserEdit, { signal: browserSpeechInputUserEditController.signal });
          input.addEventListener("click", handleBrowserSpeechInputUserEdit, { signal: browserSpeechInputUserEditController.signal });
          input.addEventListener("keyup", handleBrowserSpeechInputUserEdit, { signal: browserSpeechInputUserEditController.signal });
          input.addEventListener("select", handleBrowserSpeechInputUserEdit, { signal: browserSpeechInputUserEditController.signal });
        } catch (error) {
          browserSpeechInputUserEditController = null;
          input.addEventListener("input", handleBrowserSpeechInputUserEdit);
          input.addEventListener("click", handleBrowserSpeechInputUserEdit);
          input.addEventListener("keyup", handleBrowserSpeechInputUserEdit);
          input.addEventListener("select", handleBrowserSpeechInputUserEdit);
        }
      };
      const handleBrowserSpeechInputUserEdit = (event = null) => {
        const input = event && event.currentTarget;
        if (!input || input !== browserSpeechInputTarget || !browserSpeechInputRecognition) return;
        if (event && event.isTrusted === false) return;
        const value = String(input.value || "");
        const selection = browserSpeechInputSelectionRange(input);
        const draftRange = browserSpeechInputFindDraftRange(input);
        const inputType = String(event && event.inputType || "");
        const eventType = String(event && event.type || "");
        if (!value) {
          resetBrowserSpeechInputDraftMemory();
          browserSpeechInputAnchorStart = selection.start;
          browserSpeechInputLastSpeechText = "";
          browserSpeechInputLastRenderedValue = "";
          browserSpeechInputLastActivityValue = "";
          return;
        }
        if (draftRange.found) {
          const selectionTouchesDraft = selection.start <= draftRange.end && selection.end >= draftRange.start;
          if (eventType === "input" && (selectionTouchesDraft || inputType.startsWith("delete"))) {
            resetBrowserSpeechInputDraftMemory();
          }
        }
        browserSpeechInputAnchorStart = selection.start;
        browserSpeechInputLastSpeechText = "";
        browserSpeechInputLastRenderedValue = value;
        browserSpeechInputLastActivityValue = value;
      };
      // Added 2026-07-14: Web Speech can resend prior final text; keep Ghost Eye caret inserts to only the new dictated tail.
      const browserSpeechInputFreshFinalChunk = (finalText = "") => {
        const current = clean(finalText);
        const previous = clean(browserSpeechInputFinalText || "");
        if (!current || !previous) return current;
        if (current === previous) return "";
        const lowerCurrent = current.toLowerCase();
        const lowerPrevious = previous.toLowerCase();
        if (lowerCurrent === lowerPrevious) return "";
        if (lowerCurrent.startsWith(`${lowerPrevious} `)) {
          return clean(current.slice(previous.length));
        }
        return current;
      };
      const browserSpeechInputInsertText = (input, text = "", draft = false, options = {}) => {
        if (!input) return false;
        const insertText = clean(text);
        if (!insertText) return false;
        const value = String(input.value || "");
        const preserveSelection = Boolean(options && options.preserveSelection);
        const selection = browserSpeechInputSelectionRange(input);
        let start = Number.isFinite(Number(options && options.start)) ? Number(options.start) : browserSpeechInputSelectionPoint(input);
        let end = Number.isFinite(Number(options && options.end)) ? Number(options.end) : start;
        if (!(options && Number.isFinite(Number(options.end)))) {
          try {
            if (typeof input.selectionEnd === "number" && !(options && Number.isFinite(Number(options.start)))) end = input.selectionEnd;
          } catch (error) {
          }
        }
        start = Math.max(0, Math.min(value.length, start));
        end = Math.max(start, Math.min(value.length, end));
        const before = value.slice(0, start);
        const after = value.slice(end);
        const spacerBefore = before && insertText && !/\s$/.test(before) ? " " : "";
        const spacerAfter = after && insertText && !/^\s/.test(after) ? " " : "";
        const insertion = `${spacerBefore}${insertText}${spacerAfter}`;
        input.value = `${before}${insertion}${after}`;
        const cursor = before.length + insertion.length;
        if (preserveSelection) {
          const delta = insertion.length - (end - start);
          const adjustPoint = (point) => {
            if (point < start) return point;
            if (point > end) return point + delta;
            return cursor;
          };
          setBrowserSpeechInputSelection(input, adjustPoint(selection.start), adjustPoint(selection.end));
        } else if (typeof input.setSelectionRange === "function") {
          input.setSelectionRange(cursor, cursor);
        }
        if (draft) {
          browserSpeechInputDraftStart = before.length;
          browserSpeechInputDraftEnd = browserSpeechInputDraftStart + insertion.length;
          browserSpeechInputDraftText = insertion;
          browserSpeechInputAnchorStart = browserSpeechInputDraftStart;
        } else {
          browserSpeechInputDraftStart = -1;
          browserSpeechInputDraftEnd = -1;
          browserSpeechInputDraftText = "";
          browserSpeechInputAnchorStart = cursor;
        }
        browserSpeechInputLastRenderedValue = input.value;
        return true;
      };
      const browserSpeechInputRemoveDraft = (input, options = {}) => {
        if (!input) return false;
        const preserveSelection = options && options.preserveSelection !== false;
        const selection = browserSpeechInputSelectionRange(input);
        const value = String(input.value || "");
        const draftRange = browserSpeechInputFindDraftRange(input);
        const start = draftRange.start;
        const end = draftRange.end;
        if (draftRange.found) {
          input.value = `${value.slice(0, start)}${value.slice(end)}`;
          if (preserveSelection) {
            const removed = end - start;
            const adjustPoint = (point) => {
              if (point <= start) return point;
              if (point >= end) return point - removed;
              return start;
            };
            setBrowserSpeechInputSelection(input, adjustPoint(selection.start), adjustPoint(selection.end));
          } else {
            setBrowserSpeechInputSelection(input, start, start);
          }
        }
        browserSpeechInputDraftStart = -1;
        browserSpeechInputDraftEnd = -1;
        browserSpeechInputDraftText = "";
        browserSpeechInputLastRenderedValue = input.value;
        return draftRange.found;
      };
      const commitBrowserSpeechInputDraftToDom = (input, finalText = "", interim = "") => {
        if (!input) return false;
        const beforeValue = String(input.value || "");
        const selectionBefore = browserSpeechInputSelectionRange(input);
        const draftRange = browserSpeechInputFindDraftRange(input);
        const hasDraftRange = Boolean(draftRange.found);
        const speechStart = hasDraftRange
          ? draftRange.start
          : Math.max(0, Math.min(beforeValue.length, browserSpeechInputAnchorStart >= 0 ? browserSpeechInputAnchorStart : selectionBefore.start));
        const selectionInDraft = hasDraftRange
          && selectionBefore.start >= draftRange.start
          && selectionBefore.start <= draftRange.end
          && selectionBefore.end >= draftRange.start
          && selectionBefore.end <= draftRange.end;
        const preserveUserSelection = hasDraftRange && !selectionInDraft;
        browserSpeechInputRemoveDraft(input);
        const currentLength = String(input.value || "").length;
        let insertAt = Math.max(0, Math.min(currentLength, speechStart));
        const insertedFinal = browserSpeechInputInsertText(input, finalText, false, {
          start: insertAt,
          end: insertAt,
          preserveSelection: preserveUserSelection,
        });
        if (insertedFinal) insertAt = browserSpeechInputAnchorStart;
        const insertedInterim = browserSpeechInputInsertText(input, interim, true, {
          start: insertAt,
          end: insertAt,
          preserveSelection: preserveUserSelection,
        });
        browserSpeechInputLastRenderedValue = String(input.value || "");
        browserSpeechInputLastSpeechText = browserSpeechInputText();
        return insertedFinal || insertedInterim || beforeValue !== String(input.value || "");
      };
      const renderBrowserSpeechInputDraft = () => {
        const input = browserSpeechInputTarget;
        const text = browserSpeechInputText();
        if (!input) return false;
        browserSpeechInputLastRenderedValue = String(input.value || "");
        browserSpeechInputLastSpeechText = text;
        dispatchBrowserSpeechInputEvents(input);
        if (typeof input.focus === "function") {
          input.focus();
        }
        if (
          typeof syncPdfAgentInputPreview === "function"
          && typeof pdfEls !== "undefined"
          && pdfEls
          && (input === pdfEls.askInput || input === pdfEls.askInputPreviewBody)
        ) {
          syncPdfAgentInputPreview();
        }
        if (input === worldTrainingAnswer) {
          qmCitySpeechTokenDebugLog("draft_input", {
            textLength: text.length,
            inputLength: input.value.length,
            finalLength: clean(browserSpeechInputFinalText || "").length,
            interimLength: clean(browserSpeechInputInterimText || "").length,
          });
        }
        renderBrowserWorldTrainingSpeechOverhead(input.value, input);
        return Boolean(text);
      };
      const stopBrowserSpeechInputTimer = () => {
        if (browserSpeechInputTimer) {
          window.clearInterval(browserSpeechInputTimer);
          browserSpeechInputTimer = 0;
        }
      };
      const resetBrowserSpeechInputState = (keepDraft = true) => {
        const target = browserSpeechInputTarget;
        stopBrowserSpeechInputTimer();
        detachBrowserSpeechInputUserEditListener();
        if (keepDraft) {
          renderBrowserSpeechInputDraft();
        } else if (target === worldTrainingAnswer || target === worldBattleAnswer) {
          try {
            sharedWorldTrainingSpeech.expectedText = "";
            sharedWorldTrainingSpeech.passRatio = 1;
            sharedWorldTrainingSpeech.transcript = "";
            sharedWorldTrainingSpeech.chunk = "";
            sharedWorldTrainingSpeech.hideTarget = false;
            sharedWorldTrainingSpeech.revealTarget = false;
            sharedWorldTrainingSpeech.holdUntil = 0;
            sharedWorldTrainingSpeech.scoringLanguage = "";
            sharedWorldTrainingSpeech.flightTokenCount = 0;
            sharedWorldTrainingSpeech.browserFlightTokenCount = 0;
            clearSharedWorldTrainingSpeechOverhead();
          } catch (error) {
          }
        }
        setBrowserWorldTrainingMicLive(target, false);
        restoreVietnameseTypingAfterBrowserSpeech();
        const button = browserSpeechInputButton;
        setBrowserSpeechInputButtonState(button, "idle");
        browserSpeechInputRecognition = null;
        browserSpeechInputTarget = null;
        browserSpeechInputButton = null;
        browserSpeechInputScope = "";
        browserSpeechInputBaseValue = "";
        browserSpeechInputLastRenderedValue = "";
        browserSpeechInputLastSpeechText = "";
        browserSpeechInputDraftStart = -1;
        browserSpeechInputDraftEnd = -1;
        browserSpeechInputDraftText = "";
        browserSpeechInputAnchorStart = -1;
        browserSpeechInputFinalText = "";
        browserSpeechInputInterimText = "";
        browserSpeechInputStartedAt = 0;
        browserSpeechInputLastActivityAt = 0;
        browserSpeechInputLastActivityValue = "";
        browserSpeechInputLastChunkAt = 0;
        browserSpeechInputSubmitOnEnd = false;
        browserSpeechInputStopping = false;
        browserSpeechInputAutoRestartCount = 0;
      };
      const stopBrowserMultilingualInputDictation = () => {
        browserSpeechInputStopping = true;
        const recognition = browserSpeechInputRecognition;
        if (recognition) {
          try {
            recognition.stop();
            return true;
          } catch (error) {
            try { recognition.abort(); } catch (innerError) {}
          }
        }
        resetBrowserSpeechInputState(true);
        return false;
      };
      const stopFutureSpeechInputForTarget = (target) => {
        if (!target) return false;
        let stopped = false;
        if (browserSpeechInputRecognition && browserSpeechInputTarget === target) {
          stopped = stopBrowserMultilingualInputDictation() || stopped;
        }
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording" && zipformerViInputTarget === target) {
          stopZipformerViInputDictation();
          stopped = true;
        }
        return stopped;
      };
      const cancelBrowserMultilingualInputDictation = () => {
        const recognition = browserSpeechInputRecognition;
        if (recognition) {
          try { recognition.onresult = null; recognition.onerror = null; recognition.onend = null; recognition.abort(); } catch (error) {}
        }
        resetBrowserSpeechInputState(false);
      };
      const finishBrowserSpeechInput = () => {
        const target = browserSpeechInputTarget;
        const submitOnEnd = Boolean(browserSpeechInputSubmitOnEnd);
        const hasText = renderBrowserSpeechInputDraft();
        browserSpeechInputDebugLog("finish", { hasText, submitOnEnd });
        setBrowserSpeechInputStatus(target, hasText ? "Browser VI+EN added text." : "Browser VI+EN did not hear clear text.", hasText ? "" : "error");
        if (hasText && target === worldTrainingAnswer) {
          try {
            sharedWorldTrainingSpeech.holdUntil = Date.now() + 2800;
            sharedWorldTrainingSpeech.revealTarget = true;
            sharedWorldTrainingSpeech.hideTarget = false;
          } catch (error) {
          }
        }
        resetBrowserSpeechInputState(true);
        if (!hasText && target === worldTrainingAnswer) {
          try {
            sharedWorldTrainingSpeech.expectedText = "";
            sharedWorldTrainingSpeech.passRatio = 1;
            sharedWorldTrainingSpeech.transcript = "";
            sharedWorldTrainingSpeech.chunk = "";
            sharedWorldTrainingSpeech.hideTarget = false;
            sharedWorldTrainingSpeech.revealTarget = false;
            clearSharedWorldTrainingSpeechOverhead();
          } catch (error) {
          }
        }
        if (hasText && submitOnEnd && target === worldTrainingAnswer && worldTrainingAnswerForm) {
          window.setTimeout(() => {
            if (worldTrainingAnswer && clean(worldTrainingAnswer.value)) {
              worldTrainingAnswerForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            }
          }, 80);
        }
        if (hasText && submitOnEnd && target === worldBattleAnswer && worldBattleAnswerForm) {
          window.setTimeout(() => {
            if (worldBattleAnswer && clean(worldBattleAnswer.value)) {
              worldBattleAnswerForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            }
          }, 80);
        }
      };
      const startBrowserMultilingualInputDictation = async (target, button, scope = "", options = {}) => {
        if (!target || !button) return;
        const RecognitionCtor = browserSpeechRecognitionCtor();
        if (!RecognitionCtor) {
          setBrowserSpeechInputStatus(target, "Browser VI+EN speech recognition is unavailable here.", "error");
          return;
        }
        try {
          if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording") {
            stopZipformerViInputDictation();
          }
        } catch (error) {
        }
        if (browserSpeechInputRecognition) {
          stopBrowserMultilingualInputDictation();
          await new Promise((resolve) => window.setTimeout(resolve, 120));
        }
        const recognition = new RecognitionCtor();
        browserSpeechInputRecognition = recognition;
        browserSpeechInputTarget = target;
        browserSpeechInputButton = button;
        browserSpeechInputScope = clean(scope);
        attachBrowserSpeechInputUserEditListener(target);
        browserSpeechInputBaseValue = String(target.value || "");
        browserSpeechInputLastRenderedValue = String(target.value || "");
        browserSpeechInputLastSpeechText = "";
        browserSpeechInputDraftStart = -1;
        browserSpeechInputDraftEnd = -1;
        browserSpeechInputDraftText = "";
        browserSpeechInputAnchorStart = -1;
        browserSpeechInputFinalText = "";
        browserSpeechInputInterimText = "";
        browserSpeechInputStartedAt = Date.now();
        browserSpeechInputLastActivityAt = browserSpeechInputStartedAt;
        browserSpeechInputLastActivityValue = String(target.value || "");
        browserSpeechInputLastChunkAt = browserSpeechInputStartedAt;
        browserSpeechInputSubmitOnEnd = Boolean(options && options.submitOnEnd);
        browserSpeechInputStopping = false;
        browserSpeechInputAutoRestartCount = 0;
        suspendVietnameseTypingDuringBrowserSpeech(target, scope);
        recognition.lang = browserSpeechInputLanguage(target, scope, options);
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        browserSpeechInputDebugLog("start", {
          scope: clean(scope),
          language: recognition.lang,
          baseLength: clean(browserSpeechInputBaseValue || "").length,
        });
        recognition.onresult = (event) => {
          let finalText = "";
          let interim = "";
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const result = event.results[index];
            const value = clean(result && result[0] && result[0].transcript || "");
            if (!value) continue;
            if (result.isFinal) finalText = clean(`${finalText} ${value}`);
            else interim = clean(`${interim} ${value}`);
          }
          const freshFinalText = browserSpeechInputFreshFinalChunk(finalText);
          const domChanged = commitBrowserSpeechInputDraftToDom(target, freshFinalText, interim);
          if (freshFinalText) {
            browserSpeechInputFinalText = clean(`${browserSpeechInputFinalText} ${freshFinalText}`);
          } else if (finalText && !browserSpeechInputFinalText) {
            browserSpeechInputFinalText = clean(finalText);
          }
          browserSpeechInputAutoRestartCount = 0;
          browserSpeechInputInterimText = interim;
          renderBrowserSpeechInputDraft();
          browserSpeechInputDebugLog("result", {
            scope: clean(scope),
            domChanged,
            isFinalChunk: Boolean(freshFinalText),
            finalChunkLength: clean(freshFinalText).length,
            cachedFinalLength: clean(finalText).length,
            interimChunkLength: clean(interim).length,
            inputLength: target && target.value ? String(target.value).length : 0,
          });
          setBrowserSpeechInputStatus(target, "Browser VI+EN listening...");
        };
        recognition.onerror = (event) => {
          const code = clean(event && event.error || "");
          if (code && code !== "no-speech") {
            setBrowserSpeechInputStatus(target, `Browser VI+EN: ${code}`, "error");
          }
        };
        recognition.onend = () => {
          browserSpeechInputDebugLog("end", {
            scope: clean(scope),
            stopping: Boolean(browserSpeechInputStopping),
            restartCount: browserSpeechInputAutoRestartCount,
          });
          if (
            !browserSpeechInputStopping
            && browserSpeechInputRecognition === recognition
            && browserSpeechInputTarget === target
            && browserSpeechInputAutoRestartCount < 30
          ) {
            browserSpeechInputAutoRestartCount += 1;
            try {
              recognition.start();
              setBrowserSpeechInputStatus(target, "Browser VI+EN listening...");
              return;
            } catch (error) {
            }
          }
          finishBrowserSpeechInput();
        };
        try {
          recognition.start();
        } catch (error) {
          resetBrowserSpeechInputState(false);
          setBrowserSpeechInputStatus(target, error && error.message ? error.message : "Could not start Browser VI+EN speech input.", "error");
          return;
        }
        setBrowserSpeechInputButtonState(button, "recording");
        setBrowserSpeechInputStatus(target, "Browser VI+EN listening...");
        setBrowserWorldTrainingMicLive(target, true);
        renderBrowserWorldTrainingSpeechOverhead("", target);
        const allowIdleAutoStop = clean(scope) !== "space_s_speaking";
        browserSpeechInputTimer = window.setInterval(() => {
          const now = Date.now();
          const seconds = Math.max(0, Math.round((now - browserSpeechInputStartedAt) / 1000));
          setBrowserSpeechInputStatus(target, `Browser VI+EN listening... ${seconds}s`);
          const currentValue = String(target && target.value || "");
          if (currentValue !== browserSpeechInputLastActivityValue) {
            browserSpeechInputLastActivityValue = currentValue;
            browserSpeechInputLastActivityAt = now;
          }
          if (
            allowIdleAutoStop
            && browserSpeechInputRecognition === recognition
            && !browserSpeechInputStopping
            && browserSpeechInputLastActivityAt
            && now - browserSpeechInputLastActivityAt >= 20000
          ) {
            setBrowserSpeechInputStatus(target, "Browser VI+EN stopped after 20s without new text.");
            stopBrowserMultilingualInputDictation();
          }
        }, 500);
      };
      const toggleBrowserMultilingualInputDictation = async (target, button, scope = "", options = {}) => {
        if (browserSpeechInputRecognition && browserSpeechInputButton === button) {
          stopBrowserMultilingualInputDictation();
          return;
        }
        await startBrowserMultilingualInputDictation(target, button, scope, options);
      };
      const toggleFutureSpeechInputDictation = async (target, button, scope = "", options = {}) => {
        const mode = readSpeechInputMode(scope);
        setSpeechInputButtonModeHint(button, scope);
        if (mode === "zipformer") {
          if (browserSpeechInputRecognition) {
            cancelBrowserMultilingualInputDictation();
          }
          await toggleZipformerViInputDictation(target, button, scope);
          return;
        }
        await toggleBrowserMultilingualInputDictation(target, button, scope, options);
      };
      const ensureFutureSpeechInputDictation = async (target, button, scope = "", options = {}) => {
        if (!target || !button) return;
        if (browserSpeechInputRecognition && browserSpeechInputButton === button) {
          return;
        }
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording" && zipformerViInputButton === button) {
          return;
        }
        await toggleFutureSpeechInputDictation(target, button, scope, options);
      };
      const toggleWorldTrainingSpeechInput = async () => {
        if (!worldTrainingAnswer || !worldTrainingSpeechMic) return;
        const mode = readSpeechInputMode("qm_city_training_answer");
        const selected = typeof worldTrainingSelectedSlime === "function" ? worldTrainingSelectedSlime() : null;
        const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        if (
          mode === "zipformer"
          && typeof sharedWorldTrainingQuestionSupportsVietnameseSpeech === "function"
          && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)
          && typeof toggleSharedWorldTrainingServerSpeech === "function"
        ) {
          setSpeechInputButtonModeHint(worldTrainingSpeechMic, "qm_city_training_answer");
          await toggleSharedWorldTrainingServerSpeech();
          return;
        }
        await toggleFutureSpeechInputDictation(
          worldTrainingAnswer,
          worldTrainingSpeechMic,
          "qm_city_training_answer",
          { submitOnEnd: true }
        );
      };

      const toggleWorldBattleSpeechInput = async () => {
        if (!worldBattleAnswer || !worldBattleSpeechMic || worldBattleSpeechMic.hidden || worldBattleSpeechMic.disabled) {
          return;
        }
        const question = selectedSharedWorldBattleQuestion();
        const language = sharedWorldBattleBrowserSpeechUsesVietnamese(question) ? "vi-VN" : "en-US";
        await toggleBrowserMultilingualInputDictation(
          worldBattleAnswer,
          worldBattleSpeechMic,
          "qm_city_battle_answer",
          { submitOnEnd: true, language }
        );
      };

      const finishZipformerViInputDictation = async (blob, target, button, scope = "") => {
        if (!blob || !blob.size) {
          setZipformerViInputButtonState(button, "idle");
          setZipformerViInputStatus(target, "No audio captured.", "error");
          return;
        }
        setZipformerViInputButtonState(button, "sending");
        setZipformerViInputStatus(target, "Recognizing Vietnamese with local Zipformer...");
        try {
          const file = await learnerChatVoiceUploadFile(blob);
          const form = new FormData();
          form.append("audio", file, file.name || `zipformer-vi-${Date.now()}.wav`);
          form.append("source", clean(scope) || "ai_input_zipformer_vi");
          form.append("language", "vi");
          const response = await fetchAuthForm("/transcribe-zipformer-vi", form, 60000);
          const payload = response && response.payload ? response.payload : response;
          const text = clean(payload && (payload.text || payload.transcript || "")).toLocaleLowerCase("vi-VN");
          if (!text) {
            setZipformerViInputStatus(target, "Zipformer did not hear clear Vietnamese text.", "error");
            return;
          }
          appendZipformerViTextToInput(target, text);
          if (target === worldTrainingAnswer && worldTrainingAnswerForm && clean(worldTrainingAnswer.value)) {
            window.setTimeout(() => {
              worldTrainingAnswerForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            }, 80);
          }
          const elapsed = Number(payload && payload.elapsed_ms || 0);
          setZipformerViInputStatus(target, elapsed ? `Zipformer added text (${elapsed}ms).` : "Zipformer added text.");
        } catch (error) {
          setZipformerViInputStatus(target, error && error.message ? error.message : "Vietnamese Zipformer STT failed.", "error");
        } finally {
          setZipformerViInputButtonState(button, "idle");
        }
      };

      const stopZipformerViInputTimer = () => {
        if (zipformerViInputTimer) {
          window.clearInterval(zipformerViInputTimer);
          zipformerViInputTimer = 0;
        }
      };

      const stopZipformerViInputDictation = () => {
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording") {
          zipformerViInputRecorder.stop();
        }
      };

      const cancelZipformerViInputDictation = () => {
        stopZipformerViInputTimer();
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording") {
          zipformerViInputRecorder.stop();
        }
        if (zipformerViInputStream) {
          zipformerViInputStream.getTracks().forEach((track) => track.stop());
        }
        setZipformerViInputButtonState(zipformerViInputButton, "idle");
        zipformerViInputRecorder = null;
        zipformerViInputStream = null;
        zipformerViInputChunks = [];
        zipformerViInputTarget = null;
        zipformerViInputButton = null;
        zipformerViInputScope = "";
        zipformerViInputStartedAt = 0;
      };

      const startZipformerViInputDictation = async (target, button, scope = "") => {
        if (!target || !button) return;
        if (!authToken) {
          showLoginGate("Hay dang nhap de dung ghi am Zipformer.");
          return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
          setZipformerViInputStatus(target, "Trinh duyet chua ho tro ghi am.", "error");
          return;
        }
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording") {
          stopZipformerViInputDictation();
          await new Promise((resolve) => window.setTimeout(resolve, 120));
        }
        cancelZipformerViInputDictation();
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mimeType = learnerChatRecorderMimeType();
          const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
          zipformerViInputRecorder = recorder;
          zipformerViInputStream = stream;
          zipformerViInputChunks = [];
          zipformerViInputTarget = target;
          zipformerViInputButton = button;
          zipformerViInputScope = clean(scope) || "ai_input_zipformer_vi";
          zipformerViInputStartedAt = Date.now();
          recorder.addEventListener("dataavailable", (event) => {
            if (event.data && event.data.size) {
              zipformerViInputChunks.push(event.data);
            }
          });
          recorder.addEventListener("stop", () => {
            const activeTarget = zipformerViInputTarget;
            const activeButton = zipformerViInputButton;
            const activeScope = zipformerViInputScope;
            const type = recorder.mimeType || mimeType || "audio/webm";
            const blob = new Blob(zipformerViInputChunks, { type });
            stopZipformerViInputTimer();
            if (zipformerViInputStream) {
              zipformerViInputStream.getTracks().forEach((track) => track.stop());
            }
            zipformerViInputRecorder = null;
            zipformerViInputStream = null;
            zipformerViInputChunks = [];
            zipformerViInputTarget = null;
            zipformerViInputButton = null;
            zipformerViInputScope = "";
            zipformerViInputStartedAt = 0;
            void finishZipformerViInputDictation(blob, activeTarget, activeButton, activeScope);
          });
          recorder.start();
          setZipformerViInputButtonState(button, "recording");
          setZipformerViInputStatus(target, "Recording Vietnamese... press Stop when done.");
          zipformerViInputTimer = window.setInterval(() => {
            const seconds = Math.max(0, Math.round((Date.now() - zipformerViInputStartedAt) / 1000));
            setZipformerViInputStatus(target, `Recording Vietnamese... ${seconds}s`);
          }, 500);
        } catch (error) {
          cancelZipformerViInputDictation();
          setZipformerViInputStatus(target, error && error.message ? error.message : "Khong mo duoc mic.", "error");
        }
      };

      const toggleZipformerViInputDictation = async (target, button, scope = "") => {
        if (zipformerViInputRecorder && zipformerViInputRecorder.state === "recording" && zipformerViInputButton === button) {
          stopZipformerViInputDictation();
          return;
        }
        await startZipformerViInputDictation(target, button, scope);
      };

      const zipformerViInputBindingForTarget = (target) => {
        if (target === aiAgentInput && aiAgentViSttButton) {
          return { target: aiAgentInput, button: aiAgentViSttButton, scope: "ghost_ai_agent" };
        }
        if (target === chatViInput && chatViSttButton) {
          return { target: chatViInput, button: chatViSttButton, scope: "learner_chat_vi_input" };
        }
        if (target === worldTrainingAnswer && worldTrainingSpeechMic) {
          return { target: worldTrainingAnswer, button: worldTrainingSpeechMic, scope: "qm_city_training_answer" };
        }
        if (target === worldBattleAnswer && worldBattleSpeechMic && !worldBattleSpeechMic.hidden) {
          return { target: worldBattleAnswer, button: worldBattleSpeechMic, scope: "qm_city_battle_answer" };
        }
        if (
          typeof pdfEls !== "undefined"
          && pdfEls
          && pdfEls.askViSttButton
          && (target === pdfEls.askInput || target === pdfEls.askInputPreviewBody)
        ) {
          return { target, button: pdfEls.askViSttButton, scope: "ghost_eye_agent" };
        }
        return null;
      };

      const handleZipformerViInputCtrlKeyDown = (event) => {
        if (!event) return;
        if (event.key === "Control" && !event.repeat && !event.altKey && !event.shiftKey && !event.metaKey) {
          zipformerViCtrlToggleCandidate = zipformerViInputBindingForTarget(document.activeElement);
          return;
        }
        if (event.ctrlKey && zipformerViCtrlToggleCandidate) {
          zipformerViCtrlToggleCandidate = null;
        }
      };

      const handleZipformerViInputCtrlKeyUp = (event) => {
        if (!event || event.key !== "Control") return;
        const candidate = zipformerViCtrlToggleCandidate;
        zipformerViCtrlToggleCandidate = null;
        if (!candidate) return;
        const activeBinding = zipformerViInputBindingForTarget(document.activeElement);
        if (!activeBinding || activeBinding.target !== candidate.target || activeBinding.button !== candidate.button) {
          return;
        }
        event.preventDefault();
        if (candidate.scope === "qm_city_training_answer") {
          void toggleWorldTrainingSpeechInput();
        } else if (candidate.scope === "qm_city_battle_answer") {
          void toggleWorldBattleSpeechInput();
        } else if (candidate.scope === "ghost_ai_agent" || candidate.scope === "ghost_eye_agent" || candidate.scope === "learner_chat_vi_input") {
          void toggleFutureSpeechInputDictation(candidate.target, candidate.button, candidate.scope);
        } else {
          void toggleZipformerViInputDictation(candidate.target, candidate.button, candidate.scope);
        }
      };

      const stopLearnerChatRecordTimer = () => {
        if (learnerChatRecordTimer) {
          window.clearInterval(learnerChatRecordTimer);
          learnerChatRecordTimer = 0;
        }
      };

      const setLearnerChatRecordUi = (state = "idle", message = "") => {
        const recording = state === "recording";
        const ready = state === "ready";
        if (chatMic) {
          chatMic.textContent = recording ? "Stop mic" : "Mic";
          chatMic.classList.toggle("is-recording", recording);
          chatMic.disabled = state === "sending";
        }
        if (chatVoiceSend) {
          chatVoiceSend.hidden = !ready;
          chatVoiceSend.disabled = state === "sending";
        }
        if (chatVoiceCancel) {
          chatVoiceCancel.hidden = !(ready || recording);
          chatVoiceCancel.disabled = state === "sending";
        }
        if (message) {
          setLearnerChatStatus(message);
        }
      };

      const stopLearnerChatRecording = () => {
        if (learnerChatRecorder && learnerChatRecorder.state === "recording") {
          learnerChatRecorder.stop();
        }
      };

      const cancelLearnerChatVoice = () => {
        learnerChatRecordCanceled = true;
        if (learnerChatRecorder && learnerChatRecorder.state === "recording") {
          learnerChatRecorder.stop();
        }
        if (learnerChatRecordStream) {
          learnerChatRecordStream.getTracks().forEach((track) => track.stop());
        }
        learnerChatRecorder = null;
        learnerChatRecordStream = null;
        learnerChatRecordChunks = [];
        learnerChatRecordBlob = null;
        learnerChatRecordStartedAt = 0;
        stopLearnerChatRecordTimer();
        setLearnerChatRecordUi("idle", "");
      };

      const startLearnerChatRecording = async () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de ghi am.");
          return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
          setLearnerChatStatus("Trinh duyet chua ho tro ghi am trong message.", "error");
          return;
        }
        cancelLearnerChatVoice();
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mimeType = learnerChatRecorderMimeType();
          const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
          learnerChatRecorder = recorder;
          learnerChatRecordStream = stream;
          learnerChatRecordChunks = [];
          learnerChatRecordBlob = null;
        learnerChatRecordMode = activeLearnerChatMode();
        learnerChatRecordStartedAt = Date.now();
        learnerChatRecordCanceled = false;
          recorder.addEventListener("dataavailable", (event) => {
            if (event.data && event.data.size) {
              learnerChatRecordChunks.push(event.data);
            }
          });
          recorder.addEventListener("stop", () => {
          stopLearnerChatRecordTimer();
          if (learnerChatRecordCanceled) {
            learnerChatRecordCanceled = false;
            return;
          }
          const type = recorder.mimeType || mimeType || "audio/webm";
            learnerChatRecordBlob = new Blob(learnerChatRecordChunks, { type });
            if (learnerChatRecordStream) {
              learnerChatRecordStream.getTracks().forEach((track) => track.stop());
            }
            learnerChatRecordStream = null;
            learnerChatRecorder = null;
            if (learnerChatRecordBlob && learnerChatRecordBlob.size) {
              const seconds = Math.max(1, Math.round((Date.now() - learnerChatRecordStartedAt) / 1000));
              setLearnerChatRecordUi("ready", `Voice ready (${seconds}s). Press Send voice or Cancel.`);
            } else {
              cancelLearnerChatVoice();
              setLearnerChatStatus("Khong co audio de gui.", "error");
            }
          });
          recorder.start();
          setLearnerChatRecordUi("recording", "Recording voice... press Stop mic when done.");
          learnerChatRecordTimer = window.setInterval(() => {
            const seconds = Math.max(0, Math.round((Date.now() - learnerChatRecordStartedAt) / 1000));
            setLearnerChatRecordUi("recording", `Recording voice... ${seconds}s`);
          }, 500);
        } catch (error) {
          cancelLearnerChatVoice();
          setLearnerChatStatus(error && error.message ? error.message : "Khong mo duoc mic.", "error");
        }
      };

      const sendLearnerChatVoice = async () => {
        const blob = learnerChatRecordBlob;
        if (!blob || !blob.size) {
          setLearnerChatStatus("Chua co ban ghi am de gui.", "error");
          return;
        }
        setLearnerChatRecordUi("sending", "Preparing voice...");
        try {
          const file = await learnerChatVoiceUploadFile(blob);
          const sent = await uploadLearnerChatFiles([file], learnerChatRecordMode || activeLearnerChatMode(), {
            includeDraft: false,
            status: "Sending voice...",
          });
          if (sent) {
            learnerChatRecordBlob = null;
            learnerChatRecordChunks = [];
            setLearnerChatRecordUi("idle", "Voice sent.");
          } else {
            setLearnerChatRecordUi("ready", "Voice is still ready. Try Send voice again.");
          }
        } catch (error) {
          setLearnerChatRecordUi("ready", error && error.message ? error.message : "Could not send voice.");
        }
      };

      const handleLearnerChatPaste = (event) => {
        if (!learnerChatOpen || !event.clipboardData || event.defaultPrevented || event.futureChatPasteHandled) {
          return;
        }
        const files = Array.from(event.clipboardData.files || []).filter((file) => file && file.size);
        if (!files.length) {
          return;
        }
        event.futureChatPasteHandled = true;
        event.preventDefault();
        const mode = event.target === chatViInput ? "vi" : event.target === chatInput ? "en" : activeLearnerChatMode();
        void uploadLearnerChatFiles(files, mode);
      };

      const renderLearnerChatVoiceSettings = () => {
        if (chatViAudioToggle) {
          chatViAudioToggle.classList.toggle("is-on", learnerChatViAudioEnabled);
          chatViAudioToggle.textContent = learnerChatViAudioEnabled ? "VI audio on" : "VI audio off";
          chatViAudioToggle.setAttribute("aria-pressed", learnerChatViAudioEnabled ? "true" : "false");
        }
        if (chatViVoiceSelect && learnerChatViVoice) {
          chatViVoiceSelect.value = learnerChatViVoice;
          const option = chatViVoiceSelect.options[chatViVoiceSelect.selectedIndex];
          learnerChatViVoiceLabel = option ? option.textContent || learnerChatViVoiceLabel : learnerChatViVoiceLabel;
        }
        if (chatAudioToggle) {
          chatAudioToggle.classList.toggle("is-on", learnerChatAudioEnabled);
          chatAudioToggle.textContent = learnerChatAudioEnabled ? "EN audio on" : "EN audio off";
          chatAudioToggle.setAttribute("aria-pressed", learnerChatAudioEnabled ? "true" : "false");
        }
        if (chatVoiceSelect && learnerChatVoice) {
          chatVoiceSelect.value = learnerChatVoice;
          const option = chatVoiceSelect.options[chatVoiceSelect.selectedIndex];
          learnerChatVoiceLabel = option ? option.textContent || learnerChatVoiceLabel : learnerChatVoiceLabel;
        }
      };

      const applyLearnerChatVoicePayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const viVoice = source.chat_voice_vi || source.chatVoiceVi || source.chatVoiceVI || {};
        if (viVoice && typeof viVoice === "object") {
          learnerChatViAudioEnabled = Boolean(viVoice.enabled ?? viVoice.audio_enabled ?? viVoice.audioEnabled);
          learnerChatViVoice = clean(viVoice.voice || viVoice.value || viVoice.id || learnerChatViVoice || "edge:vi-VN-NamMinhNeural") || "edge:vi-VN-NamMinhNeural";
          learnerChatViVoiceLabel = clean(viVoice.label || viVoice.name || learnerChatViVoiceLabel) || learnerChatViVoiceLabel;
        }
        const voice = source.chat_voice || source.chatVoice || {};
        if (voice && typeof voice === "object") {
          learnerChatAudioEnabled = Boolean(voice.enabled ?? voice.audio_enabled ?? voice.audioEnabled);
          learnerChatVoice = clean(voice.voice || voice.value || voice.id || learnerChatVoice || "male-us") || "male-us";
          learnerChatVoiceLabel = clean(voice.label || voice.name || learnerChatVoiceLabel) || learnerChatVoiceLabel;
        }
        renderLearnerChatVoiceSettings();
      };

      const syncLearnerChatVoiceSettings = async () => {
        if (!authToken) {
          return;
        }
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              chat_voice_vi: {
                enabled: Boolean(learnerChatViAudioEnabled),
                voice: learnerChatViVoice || "edge:vi-VN-NamMinhNeural",
                label: learnerChatViVoiceLabel || "",
              },
              chat_voice: {
                enabled: Boolean(learnerChatAudioEnabled),
                voice: learnerChatVoice || "male-us",
                label: learnerChatVoiceLabel || "",
              },
            }),
          });
        } catch (error) {
        }
      };

      const renderLearnerVoiceSelect = (select, rows, fallbackKey, fallbackLabel) => {
        if (!select) {
          return;
        }
        const items = Array.isArray(rows) && rows.length ? rows.slice() : [{ key: fallbackKey, label: fallbackLabel }];
        if (fallbackKey && !items.some((item) => item && item.key === fallbackKey)) {
          items.unshift({ key: fallbackKey, label: fallbackLabel });
        }
        const previous = select.value || fallbackKey;
        select.textContent = "";
        items.forEach((item) => {
          const option = document.createElement("option");
          option.value = item.key || "";
          option.textContent = item.label || item.key || "Voice";
          select.appendChild(option);
        });
        if (previous && items.some((item) => item.key === previous)) {
          select.value = previous;
        } else if (fallbackKey && items.some((item) => item.key === fallbackKey)) {
          select.value = fallbackKey;
        }
      };

      const loadLearnerChatVoices = async (options = {}) => {
        if ((!chatVoiceSelect && !chatViVoiceSelect) || !authToken) {
          return;
        }
        try {
          const force = Boolean(options && options.force);
          const cacheUser = clean(currentAuthUsername || "").toLowerCase();
          const cacheFresh = learnerChatVoicesPayload &&
            learnerChatVoicesCacheUser === cacheUser &&
            Date.now() - learnerChatVoicesLoadedAt < LEARNER_CHAT_VOICES_CACHE_MS;
          let result = null;
          if (!force && cacheFresh) {
            result = learnerChatVoicesPayload;
          } else {
            if (!learnerChatVoicesPromise || force || learnerChatVoicesCacheUser !== cacheUser) {
              learnerChatVoicesCacheUser = cacheUser;
              learnerChatVoicesPromise = fetchSharedChatVoices({ force })
                .then((payload) => {
                  learnerChatVoicesPayload = payload;
                  learnerChatVoicesLoadedAt = Date.now();
                  return payload;
                })
                .finally(() => {
                  learnerChatVoicesPromise = null;
                });
            }
            result = await learnerChatVoicesPromise;
          }
          const enRows = Array.isArray(result.payload && result.payload.en) ? result.payload.en : [];
          const viRows = Array.isArray(result.payload && result.payload.vi) ? result.payload.vi : [];
          renderLearnerVoiceSelect(chatViVoiceSelect, viRows, "edge:vi-VN-NamMinhNeural", "Edge | Vietnamese VN | Nam Minh");
          renderLearnerVoiceSelect(chatVoiceSelect, enRows, "male-us", "People | Male US");
          if (!viRows.some((item) => item.key === learnerChatViVoice) && viRows.length) {
            learnerChatViVoice = viRows[0].key || learnerChatViVoice;
            learnerChatViVoiceLabel = viRows[0].label || learnerChatViVoiceLabel;
          }
          if (!enRows.some((item) => item.key === learnerChatVoice) && enRows.length) {
            learnerChatVoice = enRows[0].key || learnerChatVoice;
            learnerChatVoiceLabel = enRows[0].label || learnerChatVoiceLabel;
          }
          if (chatViVoiceSelect && chatViVoiceSelect.value) {
            learnerChatViVoice = chatViVoiceSelect.value;
            const option = chatViVoiceSelect.options[chatViVoiceSelect.selectedIndex];
            learnerChatViVoiceLabel = option ? option.textContent || learnerChatViVoiceLabel : learnerChatViVoiceLabel;
          }
          if (chatVoiceSelect && chatVoiceSelect.value) {
            learnerChatVoice = chatVoiceSelect.value;
            const option = chatVoiceSelect.options[chatVoiceSelect.selectedIndex];
            learnerChatVoiceLabel = option ? option.textContent || learnerChatVoiceLabel : learnerChatVoiceLabel;
          }
          renderLearnerChatVoiceSettings();
        } catch (error) {
          renderLearnerVoiceSelect(chatViVoiceSelect, [], "edge:vi-VN-NamMinhNeural", "Edge | Vietnamese VN | Nam Minh");
          renderLearnerVoiceSelect(chatVoiceSelect, [], "male-us", "People | Male US");
          if (chatViVoiceSelect && chatViVoiceSelect.value) {
            learnerChatViVoice = chatViVoiceSelect.value;
          }
          if (chatVoiceSelect && chatVoiceSelect.value) {
            learnerChatVoice = chatVoiceSelect.value;
          }
          renderLearnerChatVoiceSettings();
        }
      };

      const fileToDataUrl = (blob) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(reader.error || new Error("Could not read audio chunk."));
        reader.readAsDataURL(blob);
      });

      const playStreamChunk = (chunk = {}) => {
        const data = String(chunk.data || "");
        if (!data) {
          return;
        }
        learnerStreamAudioChain = learnerStreamAudioChain
          .catch(() => {})
          .then(() => new Promise((resolve) => {
            const audio = new Audio(data);
            audio.onended = resolve;
            audio.onerror = resolve;
            audio.play().catch(resolve);
          }));
      };

      const DEFAULT_WEBRTC_ICE_SERVERS = [
        { urls: ["stun:stun.l.google.com:19302"] },
        { urls: ["stun:global.stun.twilio.com:3478"] },
      ];
      const normalizeWebRtcIceUrls = (value) => {
        const source = Array.isArray(value) ? value : String(value || "").split(/[\s,;|]+/);
        const seen = new Set();
        const urls = [];
        source.forEach((item) => {
          const raw = String(item || "").trim();
          const lower = raw.toLowerCase();
          if (!raw || (!lower.startsWith("stun:") && !lower.startsWith("turn:") && !lower.startsWith("turns:"))) {
            return;
          }
          if (seen.has(lower)) {
            return;
          }
          seen.add(lower);
          urls.push(raw);
        });
        return urls.slice(0, 16);
      };
      const normalizeWebRtcIceServers = (value) => {
        const source = Array.isArray(value) ? value : [value];
        const seen = new Set();
        const servers = [];
        source.forEach((item) => {
          const data = item && typeof item === "object" ? item : null;
          const urls = normalizeWebRtcIceUrls(data ? (data.urls || data.url || "") : item);
          if (!urls.length) {
            return;
          }
          const key = urls.map((url) => url.toLowerCase()).join("|");
          if (seen.has(key)) {
            return;
          }
          seen.add(key);
          const row = { urls };
          if (data && data.username) {
            row.username = String(data.username || "");
          }
          if (data && data.credential) {
            row.credential = String(data.credential || "");
          }
          servers.push(row);
        });
        return servers.slice(0, 12);
      };
      const webRtcConfig = {
        iceServers: normalizeWebRtcIceServers(DEFAULT_WEBRTC_ICE_SERVERS),
      };
      const webRtcHasTurnRelay = () => normalizeWebRtcIceServers(webRtcConfig.iceServers).some((server) => (
        (server.urls || []).some((url) => String(url || "").toLowerCase().startsWith("turn"))
      ));
      const applyWebRtcSettings = (payload = {}) => {
        const nested = payload && payload.webrtc && typeof payload.webrtc === "object" ? payload.webrtc : {};
        const configured = normalizeWebRtcIceServers(
          nested.ice_servers || nested.iceServers || payload.webrtc_ice_servers || payload.webrtcIceServers || DEFAULT_WEBRTC_ICE_SERVERS,
        );
        webRtcConfig.iceServers = configured.length ? configured : normalizeWebRtcIceServers(DEFAULT_WEBRTC_ICE_SERVERS);
        const forceRelay = nested.force_relay === true || nested.forceRelay === true || payload.webrtc_force_relay === true || payload.webrtcForceRelay === true;
        if (forceRelay) {
          webRtcConfig.iceTransportPolicy = "relay";
        } else {
          delete webRtcConfig.iceTransportPolicy;
        }
      };

      const ensureLearnerStreamRemoteAudio = () => {
        if (!learnerStreamRemoteAudio) {
          learnerStreamRemoteAudio = document.createElement("audio");
          learnerStreamRemoteAudio.autoplay = true;
          learnerStreamRemoteAudio.playsInline = true;
          learnerStreamRemoteAudio.controls = false;
          learnerStreamRemoteAudio.style.display = "none";
          document.body.appendChild(learnerStreamRemoteAudio);
        }
        return learnerStreamRemoteAudio;
      };

      const sendLearnerWebRtcSignal = async (type, data) => {
        if (!learnerStreamSession || !type || !data) {
          return;
        }
        await fetchAuthJson("/stream/signal", {
          method: "POST",
          body: JSON.stringify({
            session: learnerStreamSession.id,
            type,
            data,
          }),
        });
      };

      const stopLearnerStreamMedia = () => {
        if (learnerStreamSegmentTimer) {
          window.clearTimeout(learnerStreamSegmentTimer);
          learnerStreamSegmentTimer = 0;
        }
        if (learnerStreamRecorder && learnerStreamRecorder.state !== "inactive") {
          try { learnerStreamRecorder.stop(); } catch (error) {}
        }
        learnerStreamRecorder = null;
        learnerStreamRecordChunks = [];
        if (learnerStreamMedia) {
          learnerStreamMedia.getTracks().forEach((track) => track.stop());
        }
        learnerStreamMedia = null;
        if (learnerStreamPeer) {
          try { learnerStreamPeer.close(); } catch (error) {}
        }
        learnerStreamPeer = null;
        learnerStreamRemoteCandidateId = 0;
        learnerStreamOfferSet = false;
        learnerStreamAnswerSent = false;
        learnerStreamOfferKey = "";
        if (learnerStreamRemoteAudio) {
          learnerStreamRemoteAudio.srcObject = null;
        }
      };

      const resetLearnerStreamPeer = () => {
        if (learnerStreamPeer) {
          try { learnerStreamPeer.close(); } catch (error) {}
        }
        learnerStreamPeer = null;
        learnerStreamRemoteCandidateId = 0;
        learnerStreamOfferSet = false;
        learnerStreamAnswerSent = false;
        learnerStreamOfferKey = "";
        if (learnerStreamRemoteAudio) {
          learnerStreamRemoteAudio.srcObject = null;
        }
      };

      const postLearnerStreamChunk = async (blob) => {
        if (!learnerStreamSession || !blob || !blob.size) {
          return;
        }
        const data = await fileToDataUrl(blob);
        await fetchAuthJson("/stream/chunk", {
          method: "POST",
          body: JSON.stringify({
            session: learnerStreamSession.id,
            data,
            mime: blob.type || "audio/webm",
          }),
        });
      };

      const startLearnerStreamChunkRelay = () => {
        if (!learnerStreamSession || learnerStreamSession.state !== "active" || !learnerStreamMedia || !window.MediaRecorder) {
          return;
        }
        if (learnerStreamRecorder && learnerStreamRecorder.state !== "inactive") {
          return;
        }
        const mimeType = learnerChatRecorderMimeType();
        let recorder = null;
        try {
          recorder = new MediaRecorder(learnerStreamMedia, mimeType ? { mimeType } : undefined);
        } catch (error) {
          setLearnerChatStatus("Khong tao duoc relay mic cho admin.", "error");
          return;
        }
        learnerStreamRecorder = recorder;
        learnerStreamRecordChunks = [];
        recorder.addEventListener("dataavailable", (event) => {
          if (event.data && event.data.size) {
            void postLearnerStreamChunk(event.data).catch(() => {});
          }
        });
        recorder.addEventListener("stop", () => {
          learnerStreamRecordChunks = [];
          if (learnerStreamRecorder === recorder) {
            learnerStreamRecorder = null;
          }
        });
        try {
          recorder.start(240);
        } catch (error) {
          learnerStreamRecorder = null;
          setLearnerChatStatus("Khong bat dau relay mic cho admin.", "error");
        }
      };

      const startLearnerStreamMedia = async () => {
        if (!learnerStreamSession || learnerStreamPeer) {
          if (learnerStreamSession && learnerStreamSession.state === "active" && learnerStreamMedia) {
            startLearnerStreamChunkRelay();
          }
          return;
        }
        if (!window.RTCPeerConnection || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setLearnerChatStatus("Trinh duyet khong ho tro WebRTC/mic.", "error");
          return;
        }
        if (!learnerStreamMedia) {
          learnerStreamMedia = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
          });
        }
        startLearnerStreamChunkRelay();
        learnerStreamPeer = new RTCPeerConnection(webRtcConfig);
        learnerStreamMedia.getAudioTracks().forEach((track) => learnerStreamPeer.addTrack(track, learnerStreamMedia));
        learnerStreamPeer.addEventListener("icecandidate", (event) => {
          if (event.candidate) {
            void sendLearnerWebRtcSignal("candidate", event.candidate.toJSON());
          }
        });
        learnerStreamPeer.addEventListener("track", (event) => {
          const audio = ensureLearnerStreamRemoteAudio();
          const stream = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
          audio.srcObject = stream;
          audio.play().catch(() => {
            setLearnerChatStatus("Stream connected. Bam Stream/chat neu trinh duyet chan autoplay.");
          });
        });
        learnerStreamPeer.addEventListener("connectionstatechange", () => {
          if (!learnerStreamPeer) return;
          setLearnerChatStatus(`WebRTC: ${learnerStreamPeer.connectionState}`);
        });
        setLearnerChatStatus("Stream WebRTC ready, waiting offer.");
      };

      const updateLearnerStreamUi = () => {
        const active = learnerStreamSession && learnerStreamSession.state === "active";
        const pending = learnerStreamSession && /^pending_/.test(learnerStreamSession.state || "");
        if (streamButton) {
          streamButton.classList.toggle("is-active", Boolean(active || pending));
          streamButton.title = active ? "Streaming live mic" : pending ? "Stream request pending" : "Request live mic stream";
        }
      };

      const autoAcceptLearnerStream = async () => {
        if (!authToken || !learnerStreamSession || learnerStreamSession.state !== "pending_user" || learnerStreamAutoAccepting) {
          return;
        }
        learnerStreamAutoAccepting = true;
        try {
          const result = await fetchAuthJson("/stream/action", {
            method: "POST",
            body: JSON.stringify({ session: learnerStreamSession.id, action: "accept" }),
          });
          await handleLearnerStreamSession(result.payload && result.payload.session || {});
        } catch (error) {
          setLearnerChatStatus("Admin dang yeu cau stream. Bam Stream de chap nhan.");
        } finally {
          learnerStreamAutoAccepting = false;
        }
      };

      const handleLearnerStreamSession = async (session = {}) => {
        const nextId = session && session.id ? session.id : "";
        if (nextId && learnerStreamSession && learnerStreamSession.id && learnerStreamSession.id !== nextId) {
          stopLearnerStreamMedia();
        }
        learnerStreamSession = session && session.id ? session : null;
        updateLearnerStreamUi();
        if (!learnerStreamSession) {
          stopLearnerStreamMedia();
          return;
        }
        if (learnerStreamSession.state === "active") {
          try {
            await startLearnerStreamMedia();
          } catch (error) {
            setLearnerChatStatus(error && error.message ? error.message : "Khong mo duoc mic.", "error");
          }
        } else if (learnerStreamSession.state === "pending_user") {
          setLearnerChatStatus("Admin dang yeu cau stream. Dang thu tu dong bat mic...");
          void autoAcceptLearnerStream();
        } else if (learnerStreamSession.state === "pending_admin") {
          setLearnerChatStatus("Dang cho admin chap nhan stream.");
        } else {
          stopLearnerStreamMedia();
        }
      };

      const pollLearnerWebRtcSignals = async () => {
        if (!learnerStreamSession || learnerStreamSession.state !== "active" || !learnerStreamPeer) {
          return;
        }
        const result = await fetchAuthJson(`/stream/signal?session=${encodeURIComponent(learnerStreamSession.id)}&after=${encodeURIComponent(String(learnerStreamRemoteCandidateId))}`);
        const payload = result.payload || {};
        if (payload.session && payload.session.state && payload.session.state !== "active") {
          await handleLearnerStreamSession(payload.session);
          return;
        }
        const offerKey = payload.offer ? `${payload.offer.type || ""}:${payload.offer.sdp || ""}` : "";
        if (payload.offer && offerKey && offerKey !== learnerStreamOfferKey) {
          if (learnerStreamPeer && learnerStreamOfferKey) {
            resetLearnerStreamPeer();
            await startLearnerStreamMedia();
          }
          if (!learnerStreamPeer) {
            await startLearnerStreamMedia();
          }
          if (!learnerStreamPeer) {
            return;
          }
          await learnerStreamPeer.setRemoteDescription(new RTCSessionDescription(payload.offer));
          learnerStreamOfferSet = true;
          learnerStreamOfferKey = offerKey;
          const answer = await learnerStreamPeer.createAnswer();
          await learnerStreamPeer.setLocalDescription(answer);
          await sendLearnerWebRtcSignal("answer", learnerStreamPeer.localDescription.toJSON());
          learnerStreamAnswerSent = true;
        }
        const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
        for (const item of candidates) {
          if (item.candidate && learnerStreamOfferSet) {
            learnerStreamRemoteCandidateId = Math.max(learnerStreamRemoteCandidateId, Number(item.id || 0));
            try {
              await learnerStreamPeer.addIceCandidate(new RTCIceCandidate(item.candidate));
            } catch (error) {
            }
          }
        }
      };

      const pollLearnerStream = async () => {
        if (!authToken || learnerStreamPollInFlight) {
          return;
        }
        learnerStreamPollInFlight = true;
        try {
          const state = await fetchAuthJson("/stream/state");
          await handleLearnerStreamSession(state.payload && state.payload.session || {});
          if (learnerStreamSession && learnerStreamSession.state === "active") {
            await pollLearnerWebRtcSignals();
          }
        } catch (error) {
        } finally {
          learnerStreamPollInFlight = false;
        }
      };

      // Added 2026-07-01: keeps live stream polling off until the learner explicitly enables it.
      const shouldKeepLearnerStreamPolling = () => {
        const state = learnerStreamSession && learnerStreamSession.state || "";
        return Boolean(authToken && state && ["active", "pending_user", "pending_admin"].includes(state));
      };

      const learnerStreamPollDelay = () => {
        const state = learnerStreamSession && learnerStreamSession.state || "";
        const base = ["active", "pending_user", "pending_admin"].includes(state)
          ? LEARNER_STREAM_POLL_ACTIVE_MS
          : LEARNER_STREAM_POLL_IDLE_MS;
        return state ? base : serverWorkspacePollDelay(base);
      };

      const scheduleLearnerStreamPolling = (delayMs = learnerStreamPollDelay()) => {
        if (learnerStreamPollTimer) {
          window.clearTimeout(learnerStreamPollTimer);
          learnerStreamPollTimer = 0;
        }
        if (!authToken) {
          return;
        }
        if (!shouldKeepLearnerStreamPolling()) {
          return;
        }
        learnerStreamPollTimer = window.setTimeout(async () => {
          learnerStreamPollTimer = 0;
          await pollLearnerStream();
          scheduleLearnerStreamPolling();
        }, Math.max(500, Number(delayMs) || learnerStreamPollDelay()));
      };

      const startLearnerStreamPolling = () => {
        if (learnerStreamPollTimer) {
          window.clearTimeout(learnerStreamPollTimer);
          learnerStreamPollTimer = 0;
        }
        if (!authToken) {
          return;
        }
        void pollLearnerStream().finally(() => {
          if (shouldKeepLearnerStreamPolling()) {
            scheduleLearnerStreamPolling();
          }
        });
      };

      const stopLearnerStreamPolling = () => {
        if (learnerStreamPollTimer) {
          window.clearTimeout(learnerStreamPollTimer);
          learnerStreamPollTimer = 0;
        }
        learnerStreamPollInFlight = false;
        stopLearnerStreamMedia();
        learnerStreamSession = null;
        updateLearnerStreamUi();
      };

      const requestOrAcceptLearnerStream = async () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de stream.");
          return;
        }
        try {
          if (learnerStreamSession && learnerStreamSession.state === "pending_user") {
            const result = await fetchAuthJson("/stream/action", {
              method: "POST",
              body: JSON.stringify({ session: learnerStreamSession.id, action: "accept" }),
            });
            await handleLearnerStreamSession(result.payload && result.payload.session || {});
            startLearnerStreamPolling();
            return;
          }
          if (learnerStreamSession && learnerStreamSession.state === "active") {
            await fetchAuthJson("/stream/action", {
              method: "POST",
              body: JSON.stringify({ session: learnerStreamSession.id, action: "end" }),
            });
            await handleLearnerStreamSession({});
            stopLearnerStreamPolling();
            return;
          }
          const result = await fetchAuthJson("/stream/request", { method: "POST", body: JSON.stringify({}) });
          await handleLearnerStreamSession(result.payload && result.payload.session || {});
          startLearnerStreamPolling();
        } catch (error) {
          setLearnerChatStatus(error && error.message ? error.message : "Khong bat dau duoc stream.", "error");
        }
      };

      const screenControlClamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));

      const ensureLearnerScreenRemoteCursorNode = () => {
        if (learnerScreenRemoteCursorNode && learnerScreenRemoteCursorNode.isConnected) {
          return learnerScreenRemoteCursorNode;
        }
        const node = document.createElement("div");
        node.className = "ft-paint-remote-cursor ft-screen-remote-cursor";
        node.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.className = "ft-paint-remote-label";
        label.textContent = "Admin";
        node.appendChild(label);
        document.body.appendChild(node);
        learnerScreenRemoteCursorNode = node;
        return node;
      };

      const hideLearnerScreenRemoteCursor = () => {
        learnerScreenRemoteCursor = null;
        if (learnerScreenRemoteCursorFrame) {
          window.cancelAnimationFrame(learnerScreenRemoteCursorFrame);
          learnerScreenRemoteCursorFrame = 0;
        }
        if (learnerScreenRemoteCursorNode) {
          learnerScreenRemoteCursorNode.classList.remove("is-visible");
        }
      };

      const learnerScreenCommandPoint = (command = {}) => ({
        x: screenControlClamp(command.x, 0, 1) * Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1),
        y: screenControlClamp(command.y, 0, 1) * Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1),
      });

      const tickLearnerScreenRemoteCursor = () => {
        const node = learnerScreenRemoteCursorNode;
        const state = learnerScreenRemoteCursor;
        if (!node || !state || !state.visible) {
          learnerScreenRemoteCursorFrame = 0;
          return;
        }
        const now = performance && typeof performance.now === "function" ? performance.now() : Date.now();
        const dt = Math.min(0.05, Math.max(0.008, (now - Number(state.lastTick || now)) / 1000 || 0.016));
        state.lastTick = now;
        const dx = state.targetX - state.x;
        const dy = state.targetY - state.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 0.35 && Math.hypot(state.vx || 0, state.vy || 0) < 8) {
          state.x = state.targetX;
          state.y = state.targetY;
          state.vx = 0;
          state.vy = 0;
          node.style.transform = `translate3d(${state.x.toFixed(1)}px, ${state.y.toFixed(1)}px, 0)`;
          learnerScreenRemoteCursorFrame = 0;
          return;
        }
        const stiffness = distance > 380 ? 130 : distance > 140 ? 104 : 86;
        const damping = distance > 380 ? 18 : 21;
        state.vx = Number(state.vx || 0) + ((dx * stiffness) - (Number(state.vx || 0) * damping)) * dt;
        state.vy = Number(state.vy || 0) + ((dy * stiffness) - (Number(state.vy || 0) * damping)) * dt;
        const speed = Math.hypot(state.vx, state.vy);
        const maxSpeed = distance > 380 ? 3000 : distance > 140 ? 2200 : 1300;
        if (speed > maxSpeed) {
          const ratio = maxSpeed / Math.max(1, speed);
          state.vx *= ratio;
          state.vy *= ratio;
        }
        state.x += state.vx * dt;
        state.y += state.vy * dt;
        node.style.transform = `translate3d(${state.x.toFixed(1)}px, ${state.y.toFixed(1)}px, 0)`;
        learnerScreenRemoteCursorFrame = window.requestAnimationFrame(tickLearnerScreenRemoteCursor);
      };

      const moveLearnerScreenRemoteCursorTo = (point = {}) => {
        const x = Number(point.x || 0) || 0;
        const y = Number(point.y || 0) || 0;
        const now = performance && typeof performance.now === "function" ? performance.now() : Date.now();
        if (!learnerScreenRemoteCursor) {
          learnerScreenRemoteCursor = { x, y, targetX: x, targetY: y, vx: 0, vy: 0, lastTick: now, visible: true };
        } else {
          learnerScreenRemoteCursor.targetX = x;
          learnerScreenRemoteCursor.targetY = y;
          learnerScreenRemoteCursor.visible = true;
        }
        if (!learnerScreenRemoteCursorFrame) {
          learnerScreenRemoteCursorFrame = window.requestAnimationFrame(tickLearnerScreenRemoteCursor);
        }
      };

      const syncLearnerPaintCursorFromScreenPoint = (point = {}, visible = true) => {
        if (!learnerPaintOpen || !paintCanvas || typeof updateLearnerPaintToolCursor !== "function") {
          return;
        }
        updateLearnerPaintToolCursor({
          clientX: Number(point.x || 0) || 0,
          clientY: Number(point.y || 0) || 0,
          pointerType: "mouse",
        }, visible);
      };

      const renderLearnerScreenRemoteCursor = (command = {}) => {
        if (!command || command.visible === false) {
          hideLearnerScreenRemoteCursor();
          syncLearnerPaintCursorFromScreenPoint({}, false);
          return;
        }
        const node = ensureLearnerScreenRemoteCursorNode();
        if (!node) {
          return;
        }
        const point = learnerScreenCommandPoint(command);
        const label = node.querySelector(".ft-paint-remote-label");
        if (label) {
          label.textContent = "Admin | Screen";
        }
        moveLearnerScreenRemoteCursorTo(point);
        syncLearnerPaintCursorFromScreenPoint(point, true);
        node.classList.add("is-visible");
      };

      const learnerScreenRemoteTargetAt = (point) => {
        const x = screenControlClamp(point && point.x, 0, Math.max(1, window.innerWidth || 1));
        const y = screenControlClamp(point && point.y, 0, Math.max(1, window.innerHeight || 1));
        return document.elementFromPoint(x, y) || document.body || document.documentElement;
      };

      const learnerScreenModifierPayload = (command = {}) => ({
        ctrlKey: Boolean(command.ctrl),
        altKey: Boolean(command.alt),
        shiftKey: Boolean(command.shift),
        metaKey: Boolean(command.meta),
      });

      const learnerScreenCanScroll = (node, axis, delta) => {
        if (!node || !Number(delta)) {
          return false;
        }
        if (axis === "y") {
          const maxTop = Math.max(0, Number(node.scrollHeight || 0) - Number(node.clientHeight || 0));
          const top = Number(node.scrollTop || 0);
          return delta > 0 ? top < maxTop - 1 : top > 1;
        }
        const maxLeft = Math.max(0, Number(node.scrollWidth || 0) - Number(node.clientWidth || 0));
        const left = Number(node.scrollLeft || 0);
        return delta > 0 ? left < maxLeft - 1 : left > 1;
      };

      const learnerScreenScrollableTarget = (target, deltaX = 0, deltaY = 0) => {
        let node = target && target.nodeType === 1 ? target : null;
        while (node && node !== document.body && node !== document.documentElement) {
          try {
            const style = window.getComputedStyle(node);
            const canScrollY = node.scrollHeight > node.clientHeight && /(auto|scroll|overlay)/i.test(style.overflowY || "");
            const canScrollX = node.scrollWidth > node.clientWidth && /(auto|scroll|overlay)/i.test(style.overflowX || "");
            const wantsY = Math.abs(Number(deltaY || 0)) >= Math.abs(Number(deltaX || 0));
            if (
              (canScrollY && learnerScreenCanScroll(node, "y", deltaY)) ||
              (canScrollX && learnerScreenCanScroll(node, "x", deltaX)) ||
              (wantsY && canScrollY) ||
              (!wantsY && canScrollX)
            ) {
              return node;
            }
          } catch (error) {
          }
          node = node.parentElement;
        }
        return document.scrollingElement || document.documentElement || document.body;
      };

      const learnerScreenScrollPosition = (target) => {
        if (!target) return { left: 0, top: 0 };
        if (target === document.scrollingElement || target === document.documentElement || target === document.body) {
          return {
            left: Number(window.scrollX || document.documentElement.scrollLeft || document.body.scrollLeft || 0),
            top: Number(window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0),
          };
        }
        return { left: Number(target.scrollLeft || 0), top: Number(target.scrollTop || 0) };
      };

      const learnerScreenApplyScroll = (target, deltaX, deltaY) => {
        if (!target) return;
        if (target === document.scrollingElement || target === document.documentElement || target === document.body) {
          window.scrollBy({ left: deltaX, top: deltaY, behavior: "auto" });
        } else if (typeof target.scrollBy === "function") {
          target.scrollBy({ left: deltaX, top: deltaY, behavior: "auto" });
        } else {
          target.scrollLeft += deltaX;
          target.scrollTop += deltaY;
        }
      };

      const dispatchLearnerScreenPointerCommand = (command = {}) => {
        const point = learnerScreenCommandPoint(command);
        renderLearnerScreenRemoteCursor(command);
        if (command.dispatch === false || command.type === "cursor") {
          return;
        }
        const target = learnerScreenRemoteTargetAt(point);
        const button = Number.isFinite(Number(command.button)) ? Number(command.button) : 0;
        const buttons = Number.isFinite(Number(command.buttons)) ? Number(command.buttons) : 0;
        const base = {
          bubbles: true,
          cancelable: true,
          composed: true,
          view: window,
          clientX: point.x,
          clientY: point.y,
          screenX: Math.round((window.screenX || 0) + point.x),
          screenY: Math.round((window.screenY || 0) + point.y),
          button,
          buttons,
          ...learnerScreenModifierPayload(command),
        };
        if (typeof target.focus === "function" && (command.type === "pointerdown" || command.type === "click")) {
          try {
            target.focus({ preventScroll: true });
          } catch (error) {
            try { target.focus(); } catch (focusError) {}
          }
        }
        if (window.PointerEvent && command.type.startsWith("pointer")) {
          target.dispatchEvent(new PointerEvent(command.type, {
            ...base,
            pointerId: 991,
            pointerType: "mouse",
            isPrimary: true,
          }));
        }
        const mouseMap = {
          pointermove: "mousemove",
          pointerdown: "mousedown",
          pointerup: "mouseup",
          click: "click",
          dblclick: "dblclick",
        };
        const mouseType = mouseMap[command.type];
        if (mouseType) {
          if (mouseType === "click" && typeof target.click === "function") {
            target.click();
          } else {
            target.dispatchEvent(new MouseEvent(mouseType, base));
          }
        }
        if (command.type === "wheel") {
          const deltaX = Number(command.delta_x || command.deltaX || 0) || 0;
          const deltaY = Number(command.delta_y || command.deltaY || 0) || 0;
          const scrollTarget = learnerScreenScrollableTarget(target, deltaX, deltaY);
          const beforeScroll = learnerScreenScrollPosition(scrollTarget);
          const wheelEvent = new WheelEvent("wheel", {
            ...base,
            deltaX,
            deltaY,
            deltaMode: 0,
          });
          const accepted = target.dispatchEvent(wheelEvent);
          const afterScroll = learnerScreenScrollPosition(scrollTarget);
          const alreadyScrolled = Math.abs(afterScroll.left - beforeScroll.left) > 0.5 || Math.abs(afterScroll.top - beforeScroll.top) > 0.5;
          if (!alreadyScrolled) {
            learnerScreenApplyScroll(scrollTarget, deltaX, deltaY);
          }
        }
      };

      const applyLearnerScreenKeyboardDefault = (command = {}) => {
        const target = document.activeElement;
        if (!target) {
          return;
        }
        const tag = String(target.tagName || "").toLowerCase();
        const editable = tag === "input" || tag === "textarea";
        if (!editable || target.disabled || target.readOnly || command.ctrl || command.alt || command.meta) {
          return;
        }
        const key = String(command.key || "");
        const start = Number(target.selectionStart ?? target.value.length);
        const end = Number(target.selectionEnd ?? start);
        const value = String(target.value || "");
        let nextValue = null;
        let nextCursor = start;
        if (key.length === 1) {
          nextValue = value.slice(0, start) + key + value.slice(end);
          nextCursor = start + key.length;
        } else if (key === "Backspace" && start !== end) {
          nextValue = value.slice(0, start) + value.slice(end);
          nextCursor = start;
        } else if (key === "Backspace" && start > 0) {
          nextValue = value.slice(0, start - 1) + value.slice(end);
          nextCursor = start - 1;
        } else if (key === "Delete" && start !== end) {
          nextValue = value.slice(0, start) + value.slice(end);
          nextCursor = start;
        } else if (key === "Delete" && end < value.length) {
          nextValue = value.slice(0, start) + value.slice(end + 1);
          nextCursor = start;
        } else if (key === "Enter" && tag === "textarea") {
          nextValue = value.slice(0, start) + "\n" + value.slice(end);
          nextCursor = start + 1;
        }
        if (nextValue === null) {
          return;
        }
        target.value = nextValue;
        try {
          target.setSelectionRange(nextCursor, nextCursor);
        } catch (error) {
        }
        target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: key.length === 1 ? key : null }));
      };

      const dispatchLearnerScreenKeyCommand = (command = {}) => {
        const target = document.activeElement || document.body || document.documentElement;
        const event = new KeyboardEvent(command.type, {
          bubbles: true,
          cancelable: true,
          composed: true,
          key: String(command.key || ""),
          code: String(command.code || ""),
          repeat: Boolean(command.repeat),
          ...learnerScreenModifierPayload(command),
        });
        const accepted = target.dispatchEvent(event);
        if (command.type === "keydown" && accepted && !event.defaultPrevented) {
          applyLearnerScreenKeyboardDefault(command);
        }
      };

      const applyLearnerScreenControlCommand = (command = {}) => {
        const type = clean(command.type || "").toLowerCase();
        if (!type) {
          return;
        }
        if (type === "keydown" || type === "keyup") {
          dispatchLearnerScreenKeyCommand(command);
          return;
        }
        dispatchLearnerScreenPointerCommand(command);
      };

      const attachLearnerScreenControlChannel = (channel) => {
        if (!channel) {
          return;
        }
        learnerScreenControlChannel = channel;
        channel.addEventListener("message", (event) => {
          try {
            const payload = JSON.parse(String(event.data || "{}"));
            const commands = Array.isArray(payload.commands)
              ? payload.commands
              : (payload.command ? [payload.command] : []);
            commands.forEach((command) => applyLearnerScreenControlCommand(command));
          } catch (error) {
          }
        });
        channel.addEventListener("close", () => {
          if (learnerScreenControlChannel === channel) {
            learnerScreenControlChannel = null;
          }
        });
      };

      const pollLearnerScreenControl = async () => {
        if (!authToken || learnerScreenControlPolling || !learnerScreenSession || learnerScreenSession.state !== "active") {
          return;
        }
        learnerScreenControlPolling = true;
        try {
          const result = await fetchAuthJson(`/screen/control?session=${encodeURIComponent(learnerScreenSession.id)}&after=${encodeURIComponent(String(learnerScreenControlAfter || 0))}`);
          const payload = result.payload || {};
          if (payload.session && payload.session.state && payload.session.state !== "active") {
            handleLearnerScreenSession(payload.session);
            return;
          }
          const commands = Array.isArray(payload.commands) ? payload.commands : [];
          commands.forEach((command) => {
            learnerScreenControlAfter = Math.max(learnerScreenControlAfter, Number(command.id || 0));
            applyLearnerScreenControlCommand(command);
          });
        } catch (error) {
        } finally {
          learnerScreenControlPolling = false;
        }
      };

      const startLearnerScreenControlPolling = () => {
        if (learnerScreenControlPollTimer) {
          return;
        }
        void pollLearnerScreenControl();
        learnerScreenControlPollTimer = window.setInterval(() => {
          void pollLearnerScreenControl();
        }, LEARNER_SCREEN_CONTROL_POLL_MS);
      };

      const stopLearnerScreenControlPolling = (resetAfter = false) => {
        if (learnerScreenControlPollTimer) {
          window.clearInterval(learnerScreenControlPollTimer);
          learnerScreenControlPollTimer = 0;
        }
        learnerScreenControlPolling = false;
        if (resetAfter) {
          learnerScreenControlAfter = 0;
        }
        hideLearnerScreenRemoteCursor();
      };

      const updateLearnerScreenUi = () => {
        const active = learnerScreenSession && learnerScreenSession.state === "active";
        const pending = learnerScreenSession && learnerScreenSession.state === "pending_user";
        if (screenButton) {
          screenButton.classList.toggle("is-active", Boolean(active || pending));
          screenButton.title = active
            ? "Screen preview is running"
            : pending
              ? "Admin requested screen preview. Click to choose the browser tab/window."
              : "Screen preview";
        }
      };

      const stopLearnerScreenCapture = () => {
        clearLearnerScreenAutoPrompt();
        learnerScreenCaptureStarting = false;
        stopLearnerScreenAudioRelay();
        stopLearnerScreenAdminAudioPolling();
        if (learnerScreenFrameTimer) {
          window.clearTimeout(learnerScreenFrameTimer);
          learnerScreenFrameTimer = 0;
        }
        stopLearnerScreenControlPolling();
        learnerScreenSending = false;
        if (learnerScreenCaptureStream) {
          learnerScreenCaptureStream.getTracks().forEach((track) => track.stop());
        }
        learnerScreenCaptureStream = null;
        if (learnerScreenVideo) {
          learnerScreenVideo.srcObject = null;
        }
        if (learnerScreenPeer) {
          try { learnerScreenPeer.close(); } catch (error) {}
        }
        learnerScreenPeer = null;
        learnerScreenControlChannel = null;
        learnerScreenRemoteCandidateId = 0;
        learnerScreenOfferSet = false;
        learnerScreenAnswerSent = false;
        learnerScreenOfferKey = "";
      };

      const resetLearnerScreenPeer = () => {
        if (learnerScreenPeer) {
          try { learnerScreenPeer.close(); } catch (error) {}
        }
        learnerScreenPeer = null;
        learnerScreenControlChannel = null;
        learnerScreenRemoteCandidateId = 0;
        learnerScreenOfferSet = false;
        learnerScreenAnswerSent = false;
        learnerScreenOfferKey = "";
      };

      const clearLearnerScreenAutoPrompt = () => {
        if (learnerScreenAutoPromptTimer) {
          window.clearTimeout(learnerScreenAutoPromptTimer);
          learnerScreenAutoPromptTimer = 0;
        }
      };

      const scheduleLearnerScreenAutoPrompt = (session = {}) => {
        const sessionId = clean(session && session.id);
        if (!sessionId || learnerScreenCaptureStream || learnerScreenCaptureStarting) {
          return;
        }
        if (learnerScreenAutoPromptSessionId === sessionId) {
          return;
        }
        learnerScreenAutoPromptSessionId = sessionId;
        clearLearnerScreenAutoPrompt();
        learnerScreenAutoPromptTimer = window.setTimeout(() => {
          learnerScreenAutoPromptTimer = 0;
          if (!authToken || !learnerScreenSession || learnerScreenSession.id !== sessionId || learnerScreenSession.state !== "pending_user") {
            return;
          }
          try {
            window.focus();
          } catch (error) {
          }
          setMobileToolsOpen(false);
          setLearnerChatStatus("Admin vua yeu cau Screen. Dang mo nhanh hop chon cua so hien tai...");
          void startLearnerScreenCapture({ autoPrompt: true });
        }, 80);
      };

      const handleLearnerScreenSession = (session = {}) => {
        const nextId = session && session.id ? session.id : "";
        if (nextId && learnerScreenSession && learnerScreenSession.id && learnerScreenSession.id !== nextId) {
          learnerScreenControlAfter = 0;
          stopLearnerScreenCapture();
        }
        learnerScreenSession = session && session.id ? session : null;
        updateLearnerScreenUi();
        if (!learnerScreenSession) {
          stopLearnerScreenControlPolling(true);
          stopLearnerScreenCapture();
          return;
        }
        if (learnerScreenSession.state === "pending_user") {
          setLearnerChatStatus("Admin dang yeu cau xem man hinh. Dang thu mo hop chon cua so hien tai...");
          scheduleLearnerScreenAutoPrompt(learnerScreenSession);
        } else if (learnerScreenSession.state === "active") {
          clearLearnerScreenAutoPrompt();
          startLearnerScreenControlPolling();
          if (learnerScreenCaptureStream) {
            void startLearnerScreenAudioRelay();
            scheduleLearnerScreenMicRelayUpgrade();
            startLearnerScreenAdminAudioPolling();
            setLearnerChatStatus("Dang stream man hinh realtime.");
          } else {
            startLearnerScreenAdminAudioPolling();
            setLearnerChatStatus("Screen dang active. Bam Screen de chon lai tab/cua so.");
          }
        } else {
          clearLearnerScreenAutoPrompt();
          stopLearnerScreenControlPolling(true);
          stopLearnerScreenCapture();
        }
      };

      const endLearnerScreenSession = async () => {
        const session = learnerScreenSession;
        learnerScreenSession = null;
        if (learnerScreenPollTimer) {
          window.clearTimeout(learnerScreenPollTimer);
          learnerScreenPollTimer = 0;
        }
        learnerScreenPollInFlight = false;
        updateLearnerScreenUi();
        stopLearnerScreenControlPolling(true);
        stopLearnerScreenCapture();
        if (authToken && session && session.id && ["pending_user", "active"].includes(session.state || "")) {
          try {
            await fetchAuthJson("/screen/action", {
              method: "POST",
              body: JSON.stringify({ session: session.id, action: "end" }),
            });
          } catch (error) {
          }
        }
      };

      const ensureLearnerScreenNodes = () => {
        if (!learnerScreenVideo) {
          learnerScreenVideo = document.createElement("video");
          learnerScreenVideo.muted = true;
          learnerScreenVideo.playsInline = true;
          learnerScreenVideo.style.display = "none";
          document.body.appendChild(learnerScreenVideo);
        }
        if (!learnerScreenCanvas) {
          learnerScreenCanvas = document.createElement("canvas");
        }
        return { video: learnerScreenVideo, canvas: learnerScreenCanvas };
      };

      const sendLearnerScreenWebRtcSignal = async (type, data) => {
        if (!learnerScreenSession || !type || !data) {
          return;
        }
        await fetchAuthJson("/screen/signal", {
          method: "POST",
          body: JSON.stringify({
            session: learnerScreenSession.id,
            type,
            data,
          }),
        });
      };

      const canvasToLearnerScreenBlob = (canvas, quality = LEARNER_SCREEN_PREVIEW_QUALITY) => new Promise((resolve) => {
        if (!canvas || typeof canvas.toBlob !== "function") {
          resolve(null);
          return;
        }
        canvas.toBlob((blob) => {
          resolve(blob || null);
        }, LEARNER_SCREEN_PREVIEW_MIME, quality);
      });

      const blobToLearnerScreenDataUrl = (blob) => new Promise((resolve) => {
        if (!blob || typeof FileReader === "undefined") {
          resolve("");
          return;
        }
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => resolve("");
        reader.readAsDataURL(blob);
      });

      const canvasToLearnerScreenJpeg = async (canvas, quality = LEARNER_SCREEN_PREVIEW_QUALITY) => {
        const blob = await canvasToLearnerScreenBlob(canvas, quality);
        if (blob) {
          return blobToLearnerScreenDataUrl(blob);
        }
        try {
          return canvas ? canvas.toDataURL(LEARNER_SCREEN_PREVIEW_MIME, quality) : "";
        } catch (error) {
          return "";
        }
      };

      const learnerScreenPeerConnected = () => Boolean(
        learnerScreenPeer
        && (
          ["connected", "completed"].includes(learnerScreenPeer.iceConnectionState || "")
          || learnerScreenPeer.connectionState === "connected"
        ),
      );

      const learnerScreenPreviewInterval = () => {
        return learnerScreenPeerConnected() ? Math.max(LEARNER_SCREEN_PREVIEW_INTERVAL_MS, 1500) : LEARNER_SCREEN_PREVIEW_INTERVAL_MS;
      };

      const scheduleLearnerScreenFrameLoop = (delayMs = 160) => {
        if (!LEARNER_SCREEN_PREVIEW_FRAMES_ENABLED) {
          if (learnerScreenFrameTimer) {
            window.clearTimeout(learnerScreenFrameTimer);
            learnerScreenFrameTimer = 0;
          }
          return;
        }
        if (learnerScreenFrameTimer) {
          window.clearTimeout(learnerScreenFrameTimer);
        }
        learnerScreenFrameTimer = window.setTimeout(async () => {
          learnerScreenFrameTimer = 0;
          const startedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
          await sendLearnerScreenFrame();
          if (learnerScreenSession && learnerScreenSession.state === "active" && learnerScreenCaptureStream) {
            const finishedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
            const elapsed = Math.max(0, finishedAt - startedAt);
            const targetDelay = Math.max(16, learnerScreenPreviewInterval() - elapsed);
            scheduleLearnerScreenFrameLoop(targetDelay);
          }
        }, Math.max(16, Number(delayMs) || LEARNER_SCREEN_PREVIEW_INTERVAL_MS));
      };
