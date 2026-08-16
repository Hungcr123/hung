      // Added 2026-08-12: one avatar-energy renderer is reused by City and Training.
      const renderSharedWorldTrainingAvatarEnergy = (stats = {}, arena = {}) => {
        const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (worldBattleModal && worldBattleModal.classList.contains("is-open") && activeBattle && clean(activeBattle.id)) {
          window.__ftAvatarEnergyOwnerTrace = {
            owner: "battle",
            rejectedOwner: "training",
            battleId: clean(activeBattle.id),
            at: Date.now(),
          };
          return;
        }
        const levelStats = sharedWorldTrainingLevelStats(stats);
        const hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || stats.max_hp || 100) || 0));
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        const currentExp = Math.max(0, Math.floor(Number(levelStats.current_exp || levelStats.currentExp || 0) || 0));
        const exp = Math.max(0, Math.floor(Number(levelStats.exp || 0) || 0));
        const nextExp = Math.max(currentExp, Math.floor(Number(levelStats.next_exp || levelStats.nextExp || currentExp) || currentExp));
        let expProgress = Number(levelStats.progress);
        if (!Number.isFinite(expProgress)) expProgress = nextExp > currentExp ? (exp - currentExp) / (nextExp - currentExp) : 0;
        const setRing = (name, value) => worldTrainingAvatarButton && worldTrainingAvatarButton.style.setProperty(`--avatar-${name}-fill`, `${Math.max(0, Math.min(100, Math.round(value * 100)))}%`);
        setRing("hp", maxHp ? hp / maxHp : 0);
        setRing("mp", maxMana ? mana / maxMana : 0);
        setRing("exp", Math.max(0, Math.min(1, expProgress)));
        if (worldTrainingAvatarButton) {
          worldTrainingAvatarButton.style.setProperty("--avatar-hp-half", `${Math.max(0, Math.min(50, Math.round((maxHp ? hp / maxHp : 0) * 50)))}%`);
          worldTrainingAvatarButton.style.setProperty("--avatar-mp-half", `${Math.max(0, Math.min(50, Math.round((maxMana ? mana / maxMana : 0) * 50)))}%`);
          const levelLabel = worldTrainingAvatarEnergy && worldTrainingAvatarEnergy.querySelector(".ft-world-training-avatar-level");
          if (levelLabel) levelLabel.textContent = `Lv ${Math.max(1, Math.floor(Number(levelStats.level || 1) || 1))}`;
          worldTrainingAvatarButton.setAttribute("aria-label", `Character energy: HP ${hp}/${maxHp}, MP ${mana}/${maxMana}, EXP ${Math.round(Math.max(0, Math.min(1, expProgress)) * 100)}%`);
          window.__ftAvatarEnergyOwnerTrace = { owner: "training", hp, maxHp, mana, maxMana, at: Date.now() };
        }
      };

      // Added 2026-08-13: cache immutable Training combat inputs; live combat stays server-authoritative.
      const readSharedWorldTrainingBaselineCache = () => {
        try {
          const row = JSON.parse(localStorage.getItem("future_training_baseline_v1") || "null");
          const username = clean(activeWorldUsername() || currentAuthUsername || "").toLowerCase();
          if (row && clean(row.username).toLowerCase() === username && row.payload && typeof row.payload === "object") return row;
        } catch (_error) {}
        return null;
      };

      const loadSharedWorldTrainingBaseline = async () => {
        const cached = readSharedWorldTrainingBaselineCache();
        try {
          const response = await fetchAuthJson("/world/training/baseline", {
            timeoutMs: 0,
            silentTimeout: true,
            ifNoneMatch: clean(cached && cached.etag || ""),
            notModifiedPayload: cached && cached.payload,
          });
          const payload = response && response.payload && response.payload.training_baseline
            ? response.payload.training_baseline
            : (response && response.payload ? response.payload : null);
          if (!payload || typeof payload !== "object") return cached && cached.payload || null;
          sharedWorldTrainingBaselineCache = payload;
          sharedWorldTrainingBaselineEtag = clean(response && response.etag || cached && cached.etag || "");
          try {
            localStorage.setItem("future_training_baseline_v1", JSON.stringify({
              username: clean(activeWorldUsername() || currentAuthUsername || ""),
              etag: sharedWorldTrainingBaselineEtag,
              payload,
              at: Date.now(),
            }));
          } catch (_error) {}
          window.__ftTrainingBaselineTrace = {
            source: response && response.notModified ? "etag-304" : "network-update",
            etag: sharedWorldTrainingBaselineEtag,
            level: Number(payload.stats && payload.stats.level || 0),
            slimes: Array.isArray(payload.slimes) ? payload.slimes.length : 0,
            at: Date.now(),
          };
          console.info("[FTG][TrainingBaseline]", window.__ftTrainingBaselineTrace);
          return payload;
        } catch (_error) {
          sharedWorldTrainingBaselineCache = cached && cached.payload || null;
          sharedWorldTrainingBaselineEtag = clean(cached && cached.etag || "");
          return sharedWorldTrainingBaselineCache;
        }
      };

      // Added 2026-08-13: persist non-durable Training combat only for this browser login session.
      const openSharedWorldTrainingSessionCombatDatabase = () => {
        if (sharedWorldTrainingSessionCombatDatabasePromise) return sharedWorldTrainingSessionCombatDatabasePromise;
        sharedWorldTrainingSessionCombatDatabasePromise = new Promise((resolve) => {
          if (!("indexedDB" in window)) return resolve(null);
          const request = indexedDB.open("future_training_session_combat_v1", 1);
          request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains("checkpoints")) {
              request.result.createObjectStore("checkpoints", { keyPath: "key" });
            }
          };
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(null);
          request.onblocked = () => resolve(null);
        });
        return sharedWorldTrainingSessionCombatDatabasePromise;
      };

      const sharedWorldTrainingSessionCombatKey = (arena = null) => {
        const username = clean(activeWorldUsername() || currentAuthUsername || "guest").toLowerCase() || "guest";
        const arenaId = clean(arena && arena.id || "arena");
        return `${username}:${sharedWorldTrainingSessionCombatSessionId}:${arenaId}`;
      };

      const writeSharedWorldTrainingSessionCombatCheckpoint = async () => {
        // Server owns shared Slime HP/mana; never persist a client combat snapshot.
        return false;
        /* istanbul ignore next */
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training;
        const arena = training && training.arena;
        if (!arena || !Array.isArray(arena.slimes)) return false;
        const database = await openSharedWorldTrainingSessionCombatDatabase();
        if (!database) return false;
        const row = {
          key: sharedWorldTrainingSessionCombatKey(arena),
          username: clean(activeWorldUsername() || currentAuthUsername || "").toLowerCase(),
          sessionId: sharedWorldTrainingSessionCombatSessionId,
          arenaId: clean(arena.id || ""),
          playerHp: Number(arena.player_hp ?? arena.playerHp ?? 0),
          playerMana: Number(arena.player_mana ?? arena.playerMana ?? 0),
          slimes: arena.slimes.map((slime) => ({
            id: clean(slime && slime.id || ""),
            hp: Number(slime && slime.hp || 0),
            mana: Number(slime && (slime.mana ?? slime.mp) || 0),
            mood: clean(slime && slime.mood || ""),
            respawnGeneration: Math.max(0, Number(slime && (slime.respawn_generation ?? slime.respawnGeneration) || 0) || 0),
          })).filter((slime) => slime.id),
          updatedAt: Date.now(),
        };
        return new Promise((resolve) => {
          const transaction = database.transaction("checkpoints", "readwrite");
          transaction.objectStore("checkpoints").put(row);
          transaction.oncomplete = () => resolve(true);
          transaction.onerror = () => resolve(false);
          transaction.onabort = () => resolve(false);
        });
      };

      const readSharedWorldTrainingSessionCombatCheckpoint = async (arena = null) => {
        return null;
        /* istanbul ignore next */
        const database = await openSharedWorldTrainingSessionCombatDatabase();
        if (!database || !arena) return null;
        return new Promise((resolve) => {
          const request = database.transaction("checkpoints", "readonly").objectStore("checkpoints").get(sharedWorldTrainingSessionCombatKey(arena));
          request.onsuccess = () => resolve(request.result && typeof request.result === "object" ? request.result : null);
          request.onerror = () => resolve(null);
        });
      };

      const mergeSharedWorldTrainingSessionCombatCheckpoint = async (training = null) => {
        return training;
        /* istanbul ignore next */
        const arena = training && training.arena;
        if (!arena || !Array.isArray(arena.slimes)) return training;
        const checkpoint = await readSharedWorldTrainingSessionCombatCheckpoint(arena);
        if (!checkpoint || clean(checkpoint.sessionId) !== sharedWorldTrainingSessionCombatSessionId) return training;
        arena.player_hp = Number(checkpoint.playerHp ?? arena.player_hp ?? arena.playerHp ?? 0);
        arena.player_mana = Number(checkpoint.playerMana ?? arena.player_mana ?? arena.playerMana ?? 0);
        const byId = new Map((checkpoint.slimes || []).map((slime) => [clean(slime && slime.id || ""), slime]));
        let respawnRepaired = false;
        arena.slimes.forEach((slime) => {
          const local = byId.get(clean(slime && slime.id || ""));
          if (!local) return;
          const serverHp = Math.max(0, Number(slime.hp || 0) || 0);
          const serverMaxHp = Math.max(1, Number(slime.max_hp || slime.maxHp || serverHp || 1) || 1);
          const serverMood = clean(slime.mood || "").toLowerCase();
          const serverRespawnGeneration = Math.max(0, Number(slime.respawn_generation ?? slime.respawnGeneration ?? 0) || 0);
          const localRespawnGeneration = Math.max(0, Number(local.respawnGeneration ?? local.respawn_generation ?? 0) || 0);
          // Added 2026-08-14: a new server life must keep winning after mood
          // changes from respawn to roam, so stale local HP cannot return.
          if ((serverRespawnGeneration > localRespawnGeneration || serverMood === "respawn") && serverHp >= serverMaxHp) {
            local.hp = serverMaxHp;
            local.mana = Number(slime.mana ?? slime.mp ?? 0);
            local.mood = clean(slime.mood || "respawn");
            local.respawnGeneration = serverRespawnGeneration;
            respawnRepaired = true;
            return;
          }
          slime.hp = Number(local.hp ?? slime.hp ?? 0);
          slime.mana = Number(local.mana ?? slime.mana ?? 0);
          slime.mood = clean(local.mood || slime.mood || "");
          slime.respawn_generation = localRespawnGeneration;
        });
        if (respawnRepaired) {
          checkpoint.updatedAt = Date.now();
          const database = await openSharedWorldTrainingSessionCombatDatabase();
          if (database) {
            await new Promise((resolve) => {
              const transaction = database.transaction("checkpoints", "readwrite");
              transaction.objectStore("checkpoints").put(checkpoint);
              transaction.oncomplete = () => resolve(true);
              transaction.onerror = () => resolve(false);
              transaction.onabort = () => resolve(false);
            });
          }
        }
        window.__ftTrainingSessionCombatTrace = {
          source: respawnRepaired ? "server-respawn-repaired-checkpoint" : "indexeddb-session",
          arenaId: clean(arena.id || ""),
          respawnRepaired,
          at: Date.now(),
        };
        console.info("[FTG][TrainingSessionCombat]", window.__ftTrainingSessionCombatTrace);
        return training;
      };

      const clearSharedWorldTrainingSessionCombatCheckpoint = async (arena = null) => {
        const database = await openSharedWorldTrainingSessionCombatDatabase();
        if (!database || !arena) return false;
        return new Promise((resolve) => {
          const transaction = database.transaction("checkpoints", "readwrite");
          transaction.objectStore("checkpoints").delete(sharedWorldTrainingSessionCombatKey(arena));
          transaction.oncomplete = () => resolve(true);
          transaction.onerror = () => resolve(false);
          transaction.onabort = () => resolve(false);
        });
      };

      const clearSharedWorldTrainingSessionCombat = async () => {
        const database = await openSharedWorldTrainingSessionCombatDatabase();
        if (!database) return false;
        const username = clean(activeWorldUsername() || currentAuthUsername || "").toLowerCase();
        return new Promise((resolve) => {
          const transaction = database.transaction("checkpoints", "readwrite");
          const request = transaction.objectStore("checkpoints").openCursor();
          request.onsuccess = () => {
            const cursor = request.result;
            if (!cursor) return;
            const row = cursor.value || {};
            if (clean(row.username).toLowerCase() === username && clean(row.sessionId) === sharedWorldTrainingSessionCombatSessionId) {
              cursor.delete();
            }
            cursor.continue();
          };
          transaction.oncomplete = () => resolve(true);
          transaction.onerror = () => resolve(false);
          transaction.onabort = () => resolve(false);
        });
      };

      const applySharedWorldTrainingLocalBasicResult = (slimeId = "", correct = false) => {
        return null;
        /* istanbul ignore next */
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training;
        const arena = training && training.arena;
        const stats = training && training.stats;
        if (!arena || !stats || !Array.isArray(arena.slimes)) return null;
        const slime = arena.slimes.find((row) => clean(row && row.id || "") === clean(slimeId));
        if (!slime) return null;
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        const combat = sharedWorldTrainingBaselineCache && sharedWorldTrainingBaselineCache.combat || {};
        let damage = 0;
        if (correct) {
          damage = Math.max(1, Math.floor(Number(stats.strength || 1) || 1));
          slime.hp = Math.max(0, Math.floor(Number(slime.hp || 0) || 0) - damage);
          slime.mood = slime.hp > 0 ? "hurt" : "defeated";
          arena.player_mana = Math.min(maxMana, Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0)) + Math.max(0, Number(combat.basic_mana_gain || 8) || 8));
        } else {
          damage = Math.max(1, Math.ceil(maxHp * Math.max(0, Number(combat.wrong_damage_ratio || 0.1) || 0.1)));
          arena.player_hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || maxHp) || maxHp) - damage);
          slime.mana = Math.min(Math.max(1, Number(slime.max_mana || slime.maxMana || 20) || 20), Math.max(0, Number(slime.mana || 0) || 0) + Math.max(0, Number(combat.slime_wrong_mana_gain || 6) || 6));
        }
        renderSharedWorldTrainingStats(stats, arena);
        renderSharedWorldTrainingSlimes(arena);
        window.__ftTrainingLocalCombatTrace = {
          correct: Boolean(correct),
          slimeId: clean(slimeId),
          damage,
          slimeHp: Number(slime.hp || 0),
          playerHp: Number(arena.player_hp || arena.playerHp || maxHp),
          playerMana: Number(arena.player_mana || arena.playerMana || 0),
          serverWriteExpected: Number(slime.hp || 0) <= 0 ? "kill-only" : "none",
          at: Date.now(),
        };
        void writeSharedWorldTrainingSessionCombatCheckpoint();
        return window.__ftTrainingLocalCombatTrace;
      };

      const applySharedWorldTrainingLocalSkillResult = (skillId = "", targetSlimeId = "", slimePositions = [], radiusX = 0.32, radiusY = 0.44) => {
        return { serverAuthoritative: true, skillId: clean(skillId), targetSlimeId: clean(targetSlimeId) };
        /* istanbul ignore next */
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training;
        const arena = training && training.arena;
        const stats = training && training.stats;
        const skill = sharedWorldTrainingSkillById(skillId);
        if (!arena || !stats || !skill || !Array.isArray(arena.slimes)) return null;
        const manaCost = Math.max(0, Math.floor(Number(skill.mana_cost || skill.manaCost || 0) || 0));
        const currentMana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        if (currentMana < manaCost) return null;
        const damagePercent = Math.max(1, Number(skill.damage_percent || skill.damagePercent || 100) || 100);
        const damage = Math.max(1, Math.round(Math.max(1, Number(stats.strength || 1) || 1) * damagePercent / 100));
        const positionRows = new Map((Array.isArray(slimePositions) ? slimePositions : []).map((row) => [clean(row && row.id || ""), row]));
        const target = positionRows.get(clean(targetSlimeId));
        const center = target || { x: 0.5, y: 0.5 };
        const affected = [];
        arena.slimes.forEach((slime) => {
          if (!slime || Math.max(0, Number(slime.hp || 0) || 0) <= 0) return;
          const point = positionRows.get(clean(slime.id)) || { x: slime.tx ?? slime.x, y: slime.ty ?? slime.y };
          const distance = Math.hypot((Number(point.x) - Number(center.x)) / Math.max(0.02, radiusX), (Number(point.y) - Number(center.y)) / Math.max(0.02, radiusY));
          if (distance > 1) return;
          slime.hp = Math.max(0, Math.floor(Number(slime.hp || 0) || 0) - damage);
          slime.mood = slime.hp > 0 ? "hurt" : "defeated";
          affected.push({ slimeId: clean(slime.id), hp: slime.hp });
        });
        if (!affected.length) return null;
        arena.player_mana = Math.max(0, currentMana - manaCost);
        renderSharedWorldTrainingStats(stats, arena);
        renderSharedWorldTrainingSlimes(arena);
        window.__ftTrainingLocalSkillTrace = {
          skillId: clean(skillId),
          damage,
          manaCost,
          affected,
          serverWriteExpected: affected.some((row) => row.hp <= 0) ? "kill-only" : "none",
          at: Date.now(),
        };
        console.info("[FTG][TrainingLocalSkill]", window.__ftTrainingLocalSkillTrace);
        return window.__ftTrainingLocalSkillTrace;
      };

      window.__ftTrainingLocalCombatProbe = (iterations = 5000) => {
        const count = Math.max(100, Math.min(50000, Math.floor(Number(iterations || 5000) || 5000)));
        const startedAt = performance.now();
        let hp = 700;
        let mana = 0;
        let checksum = 0;
        for (let index = 0; index < count; index += 1) {
          const correct = index % 5 !== 0;
          if (correct) {
            const damage = index % 11 === 0 ? 24 : 12;
            hp = Math.max(0, hp - damage);
            mana = Math.min(100, mana + 8);
            if (hp <= 0) hp = 700;
          } else {
            mana = Math.max(0, mana - 6);
          }
          checksum += hp + mana;
        }
        const elapsedMs = performance.now() - startedAt;
        return {
          ok: true,
          iterations: count,
          elapsedMs: Math.round(elapsedMs * 1000) / 1000,
          averageMicroseconds: Math.round((elapsedMs * 1000 / count) * 1000) / 1000,
          checksum,
          networkRequests: 0,
          durableWrites: 0,
        };
      };
      if (new URLSearchParams(window.location.search).get("ft_training_local_probe") === "1") {
        window.setTimeout(() => console.info("[FTG][TrainingLocalCombatProbe]", JSON.stringify(window.__ftTrainingLocalCombatProbe(20000))), 0);
      }

      const renderSharedWorldTrainingPlayerVitals = (stats = {}, arena = {}) => {
        const key = (clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner").toLowerCase();
        const node = sharedWorldNodes.get(key) || (ensureSharedWorldSelfNode() || {}).node;
        if (!node) {
          return;
        }
        const levelStats = sharedWorldTrainingLevelStats(stats);
        renderSharedWorldLevel(node, levelStats);
        // Added 2026-08-11: unify Training identity, EXP, HP, and MP in one game HUD panel.
        let hud = node.querySelector(".ft-world-training-player-hud");
        if (!hud) {
          hud = document.createElement("div");
          hud.className = "ft-world-training-player-hud";
          node.appendChild(hud);
        }
        const nameRow = node.querySelector(".ft-world-name-row");
        const levelRow = node.querySelector(".ft-world-level");
        if (nameRow && nameRow.parentElement !== hud) hud.appendChild(nameRow);
        const levelBadge = levelRow && levelRow.querySelector(".ft-world-level-badge");
        if (levelBadge && levelBadge.parentElement !== nameRow) nameRow && nameRow.appendChild(levelBadge);
        if (levelRow && levelRow.parentElement !== node) node.appendChild(levelRow);
        let vitals = node.querySelector(".ft-world-training-vitals");
        if (!vitals) {
          vitals = document.createElement("div");
          vitals.className = "ft-world-training-vitals";
        }
        if (vitals.parentElement !== hud) {
          hud.appendChild(vitals);
        }
        const hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || stats.max_hp || 100) || 0));
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        vitals.innerHTML = `
          <span class="ft-world-training-vital" title="HP ${hp}/${maxHp}"><b>HP</b><span><i style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166;--bar-glow:rgba(255,103,93,.36)"></i></span><small>${hp}</small></span>
          <span class="ft-world-training-vital" title="Mana ${mana}/${maxMana}"><b>MP</b><span><i style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0;--bar-glow:rgba(70,240,215,.36)"></i></span><small>${mana}</small></span>
        `;
        renderSharedWorldTrainingAvatarEnergy(stats, arena);
      };

      const renderSharedWorldTrainingStats = (stats = {}, arena = {}) => {
        if (!worldTrainingStats) {
          return;
        }
        const levelStats = sharedWorldTrainingLevelStats(stats);
        const hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || stats.max_hp || 100) || 0));
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        const points = Math.max(0, Math.floor(Number(stats.available_points || stats.availablePoints || 0) || 0));
        const rows = sharedWorldTrainingStatRows(stats);
        worldTrainingStats.innerHTML = `
          <div class="ft-world-training-stat-title">Character core</div>
          <div class="ft-world-training-player-bars">
            <div class="ft-world-training-bar" style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166"><span>HP ${hp}/${maxHp}</span><span></span></div>
            <div class="ft-world-training-bar" style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0"><span>Mana ${mana}/${maxMana}</span><span></span></div>
          </div>
          <div class="ft-world-training-stat-title">Lv ${Math.max(1, Math.floor(Number(levelStats.level || 1) || 1))} upgrade points: ${points}</div>
          <div class="ft-world-training-upgrades">
            ${rows.map(([key, label, value, title]) => `
              <div class="ft-world-training-upgrade">
                <span><b>${label}</b><small title="${title}"> ${Math.max(0, Math.floor(Number(value || 0) || 0))}</small></span>
                <button type="button" data-world-training-stat="${key}" ${points <= 0 ? "disabled" : ""}>+</button>
              </div>
            `).join("")}
          </div>
        `;
        renderSharedWorldTrainingLoadoutPanel();
        renderSharedWorldTrainingQuickSkill();
        renderSharedWorldTrainingBasicOrbit();
        renderSharedWorldTrainingPlayerVitals(stats, arena);
      };

      // Added 2026-08-14: derive stable initial slime positions locally so the
      // server only supplies identity/stats and never owns visual coordinates.
      const sharedWorldTrainingFrontendSpawnPoint = (row = {}, index = 0, count = 1) => {
        const source = `${clean(row && row.id || `slime_${index + 1}`)}:${Number(row && (row.motion_seed || row.motionSeed) || 0) || 0}`;
        let hash = 2166136261;
        for (let cursor = 0; cursor < source.length; cursor += 1) {
          hash ^= source.charCodeAt(cursor);
          hash = Math.imul(hash, 16777619);
        }
        const unit = () => {
          hash = (Math.imul(hash, 1664525) + 1013904223) >>> 0;
          return hash / 4294967296;
        };
        const columns = Math.max(1, Math.ceil(Math.sqrt(Math.max(1, count) * 1.25)));
        const rows = Math.max(1, Math.ceil(Math.max(1, count) / columns));
        const column = Math.max(0, index % columns);
        const line = Math.max(0, Math.floor(index / columns));
        const jitterX = (unit() - 0.5) * 0.11;
        const jitterY = (unit() - 0.5) * 0.08;
        return {
          x: sharedWorldClamp(0.16 + ((column + 0.5) / columns) * 0.68 + jitterX),
          y: sharedWorldClamp(0.18 + ((line + 0.5) / rows) * 0.48 + jitterY),
        };
      };

      const renderSharedWorldTrainingSlimes = (arena = {}) => {
        const host = sharedWorldTrainingSlimeHost();
        if (!host) {
          return;
        }
        const selectedId = clean(arena.selected_id || arena.selectedId || "");
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        [worldTrainingSlimes, worldTrainingMapSlimes].forEach((node) => {
          if (node && node !== host) {
            node.innerHTML = "";
          }
        });
        const existingButtons = new Map(
          Array.from(host.querySelectorAll("[data-slime-id]"))
            .map((node) => [clean(node.dataset.slimeId || ""), node])
            .filter(([id]) => Boolean(id))
        );
        const seen = new Set();
        slimes.forEach((slime, index) => {
          const row = slime && typeof slime === "object" ? slime : {};
          const hp = Math.max(0, Math.floor(Number(row.hp || 0) || 0));
          const maxHp = Math.max(1, Math.floor(Number(row.max_hp || row.maxHp || hp || 1) || 1));
          const mana = Math.max(0, Math.floor(Number(row.mana || row.mp || 0) || 0));
          const maxMana = Math.max(1, Math.floor(Number(row.max_mana || row.maxMana || 1) || 1));
          const id = clean(row.id || `slime_${index + 1}`);
          if (!id) {
            return;
          }
          seen.add(id);
          let button = existingButtons.get(id) || null;
          const fallbackPoint = sharedWorldTrainingFrontendSpawnPoint(row, index, slimes.length);
          const moveStartedAt = Number(row.move_started_at || 0) || 0;
          const moveDuration = Math.max(0, Number(row.move_duration || 0) || 0);
          const moveProgress = moveDuration > 0 && moveStartedAt > 0
            ? Math.max(0, Math.min(1, ((Date.now() + sharedWorldTrainingServerClockOffsetMs) / 1000 - moveStartedAt) / moveDuration))
            : 1;
          const trajectoryPoint = {
            x: sharedWorldClamp(Number(row.from_x ?? row.x ?? row.tx ?? fallbackPoint.x) + (Number(row.to_x ?? row.x ?? row.tx ?? fallbackPoint.x) - Number(row.from_x ?? row.x ?? row.tx ?? fallbackPoint.x)) * moveProgress, fallbackPoint.x),
            y: sharedWorldClamp(Number(row.from_y ?? row.y ?? row.ty ?? fallbackPoint.y) + (Number(row.to_y ?? row.y ?? row.ty ?? fallbackPoint.y) - Number(row.from_y ?? row.y ?? row.ty ?? fallbackPoint.y)) * moveProgress, fallbackPoint.y),
          };
          const movementSeq = Math.max(0, Math.floor(Number(row.movement_seq || 0) || 0));
          const movementChanged = movementSeq > 0 && String(button && button.dataset && button.dataset.movementSeq || "") !== String(movementSeq);
          const rawPoint = movementChanged && moveDuration > 0
            ? { x: sharedWorldClamp(row.to_x, trajectoryPoint.x), y: sharedWorldClamp(row.to_y, trajectoryPoint.y) }
            : trajectoryPoint;
          const previousX = Number(button && button.dataset.slimeX);
          const previousY = Number(button && button.dataset.slimeY);
          let roam = sharedWorldTrainingSlimeRoamState.get(id);
          const previousRoamHp = roam ? Number(roam.lastHp || 0) : hp;
          const respawned = roam && Number(roam.lastHp || 0) <= 0 && hp > 0;
          if (!roam || respawned) {
            const seed = Math.max(1, Math.floor(Number(row.motion_seed || row.motionSeed || (index + 1) * 997) || 1));
            roam = {
              x: rawPoint.x,
              y: rawPoint.y,
              homeX: rawPoint.x,
              homeY: rawPoint.y,
              lastHp: hp,
              seed,
              nextMoveAt: Date.now() + 900 + (seed % 3200),
              moveCount: 0,
            };
            sharedWorldTrainingSlimeRoamState.set(id, roam);
          }
          if (row.x != null || row.y != null || row.tx != null || row.ty != null) {
            roam.x = rawPoint.x;
            roam.y = rawPoint.y;
            roam.homeX = rawPoint.x;
            roam.homeY = rawPoint.y;
          }
          roam.lastHp = hp;
          // Preserve roaming through death; only respawn resets to the locally derived spawn point.
          const displayPoint = {
            x: sharedWorldClamp(roam.x, rawPoint.x),
            y: sharedWorldClamp(roam.y, rawPoint.y),
          };
          const spawnDelta = Math.hypot(displayPoint.x - rawPoint.x, displayPoint.y - rawPoint.y);
          if (spawnDelta > 0.002) {
            const signature = `${id}:${displayPoint.x.toFixed(3)}:${displayPoint.y.toFixed(3)}:${rawPoint.x.toFixed(3)}:${rawPoint.y.toFixed(3)}`;
            if (window.__ftTrainingSlimePositionOwnerSignature !== signature) {
              window.__ftTrainingSlimePositionOwnerSignature = signature;
              window.__ftTrainingSlimePositionOwnerTrace = {
                slimeId: id,
                owner: "frontend",
                frontend: { x: displayPoint.x, y: displayPoint.y },
                frontendSpawn: { x: rawPoint.x, y: rawPoint.y },
                serverCoordinatesPresent: Boolean(row.x != null || row.y != null || row.tx != null || row.ty != null),
                serverPositionIgnored: Boolean(row.x != null || row.y != null || row.tx != null || row.ty != null),
                delta: spawnDelta,
                at: Date.now(),
              };
              console.info("[FTG][TrainingSlimePositionOwner]", window.__ftTrainingSlimePositionOwnerTrace);
            }
          }
          if (previousRoamHp > 0 && hp <= 0) {
            window.__ftTrainingSlimeDeathAnchorTrace = {
              slimeId: id,
              anchor: "last-roam-position",
              roam: { x: displayPoint.x, y: displayPoint.y },
              frontendSpawn: { x: rawPoint.x, y: rawPoint.y },
              avoidedSnapDistance: Math.hypot(displayPoint.x - rawPoint.x, displayPoint.y - rawPoint.y),
              at: Date.now(),
            };
            console.info("[FTG][TrainingSlimeDeathAnchor]", window.__ftTrainingSlimeDeathAnchorTrace);
          }
          const legalPoint = displayPoint;
          roam.x = legalPoint.x;
          roam.y = legalPoint.y;
          const x = Math.max(4, Math.min(96, legalPoint.x * 100));
          const y = Math.max(8, Math.min(72, legalPoint.y * 100));
          if (!button) {
            button = document.createElement("button");
            button.type = "button";
            button.className = "ft-world-training-slime is-initial-layout";
            host.appendChild(button);
            window.requestAnimationFrame(() => button.classList.remove("is-initial-layout"));
          }
          button.dataset.slimeId = id;
          const generation = Math.max(1, Math.floor(Number(row.generation ?? row.respawn_generation ?? 1) || 1));
          const previousGeneration = Math.max(0, Math.floor(Number(button.dataset.generation || 0) || 0));
          if (previousGeneration && previousGeneration !== generation) {
            button.classList.remove("is-hopping", "is-hit", "is-hurt", "is-defeated");
            window.clearTimeout(button._worldTrainingHopTimer);
            button._worldTrainingHopTimer = 0;
          }
          button.dataset.generation = String(generation);
          const xText = x.toFixed(2);
          const yText = y.toFixed(2);
          button.dataset.slimeX = xText;
          button.dataset.slimeY = yText;
          button.dataset.worldDepthY = (y / 100).toFixed(4);
          button.dataset.movementSeq = String(movementSeq);
          if (button.style.getPropertyValue("--slime-x") !== xText) button.style.setProperty("--slime-x", xText);
          if (button.style.getPropertyValue("--slime-y") !== yText) button.style.setProperty("--slime-y", yText);
          const motionSeed = Math.max(0, Math.floor(Number(row.motion_seed || row.motionSeed || index * 997) || 0));
          button.style.setProperty("--slime-idle-delay", `${-((motionSeed % 2800) / 1000).toFixed(3)}s`);
          const slimeName = clean(row.name || "Slime");
          const slimeLevel = Math.max(1, Math.floor(Number(row.level || 1) || 1));
          const title = `${slimeName} Lv ${slimeLevel} - click to target`;
          if (button.title !== title) button.title = title;
          const isSelected = id === selectedId;
          button.classList.toggle("is-selected", isSelected);
          button.classList.toggle("is-defeated", hp <= 0);
          // Position changes from server renders are deliberately silent. Only the
          // independent frontend roam scheduler may start a travel animation.
          if (!Number.isFinite(previousX) || !Number.isFinite(previousY)) {
            button.classList.remove("is-hopping");
          } else if (movementChanged || Math.hypot(x - previousX, y - previousY) > 0.18) {
            const duration = movementChanged ? Math.max(220, Math.round((1 - moveProgress) * moveDuration * 1000)) : 760;
            button.style.setProperty("--slime-hop-duration", `${duration}ms`);
            button.classList.remove("is-hopping");
            void button.offsetWidth;
            button.classList.add("is-hopping");
            window.clearTimeout(button._worldTrainingHopTimer);
            button._worldTrainingHopTimer = window.setTimeout(() => {
              button.classList.remove("is-hopping");
              button._worldTrainingHopTimer = 0;
            }, duration + 60);
          }
          const visualKinds = ["is-kind-word", "is-kind-sentence", "is-kind-audio", "is-kind-translate"];
          const visualKind = visualKinds[index % visualKinds.length];
          const visualSignature = `${visualKind}:${index % 5 === 4 ? "fang" : "slime"}`;
          if (button.dataset.visualSignature !== visualSignature) {
            button.classList.remove(
              "is-kind-word", "is-kind-sentence", "is-kind-audio", "is-kind-translate", "is-enemy-fangbeast",
              "is-slime-color-1", "is-slime-color-2", "is-slime-color-3", "is-slime-color-4", "is-slime-color-5", "is-slime-color-6"
            );
            button.classList.add(visualKind);
            if (index % 5 === 4) button.classList.add("is-enemy-fangbeast");
            button.dataset.visualSignature = visualSignature;
          }
          const hudSignature = `${slimeName}:${slimeLevel}:${hp}:${maxHp}:${mana}:${maxMana}`;
          if (button.dataset.hudSignature !== hudSignature) {
            button.innerHTML = `
            <span class="ft-world-training-slime-focus-arrow" aria-hidden="true"></span>
            <span class="ft-world-training-slime-crest" aria-hidden="true"></span>
            <span class="ft-world-training-slime-core" aria-hidden="true"></span>
            <span class="ft-world-training-slime-fangs" aria-hidden="true"></span>
            <span class="ft-world-training-slime-stun" aria-hidden="true"></span>
            <span class="ft-world-training-slime-overhead">
              <span class="ft-world-training-slime-name"><b>${slimeName}</b><span>Lv ${slimeLevel}</span></span>
              <span class="ft-world-training-mini-bars">
                <span class="ft-world-training-mini-bar" title="HP ${hp}/${maxHp}"><i style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166"></i></span>
                <span class="ft-world-training-mini-bar" title="Mana ${mana}/${maxMana}"><i style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0"></i></span>
              </span>
            </span>
          `;
            button.dataset.hudSignature = hudSignature;
          }
          button.style.setProperty("--slime-arrow-top", "-72px");
        });
        Array.from(host.querySelectorAll("[data-slime-id]")).forEach((node) => {
          if (!seen.has(clean(node.dataset.slimeId || ""))) {
            sharedWorldTrainingSlimeRoamState.delete(clean(node.dataset.slimeId || ""));
            node.remove();
          }
        });
        scheduleSharedWorldCharacterDepthOrder();
      };

      const stepSharedWorldTrainingLocalSlimes = () => {
        if (!sharedWorldTrainingIsActive()) {
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        if (!slimes.length) {
          return;
        }
        const now = Date.now();
        if (now < sharedWorldTrainingSlimeSelectionQuietUntil) {
          return;
        }
        const selectedId = clean(arena.selected_id || arena.selectedId || "");
        const host = sharedWorldTrainingSlimeHost();
        if (!host) {
          return;
        }
        if (host.querySelector("[data-slime-id].is-hopping")) {
          return;
        }
        const count = slimes.length;
        for (let offset = 0; offset < count; offset += 1) {
          const index = (sharedWorldTrainingSlimeRoamCursor + offset) % count;
          const slime = slimes[index];
          const row = slime && typeof slime === "object" ? slime : {};
          const id = clean(row.id || "");
          const hp = Math.max(0, Math.floor(Number(row.hp || 0) || 0));
          if (!id || hp <= 0) {
            continue;
          }
          const roam = sharedWorldTrainingSlimeRoamState.get(id);
          if (!roam) {
            continue;
          }
          if (id === selectedId) {
            roam.nextMoveAt = Math.max(Number(roam.nextMoveAt || 0), now + 1800);
            continue;
          }
          if (now < Number(roam.nextMoveAt || 0)) {
            continue;
          }
          // One slime per scheduler tick prevents synchronized herd movement.
          sharedWorldTrainingSlimeRoamCursor = (index + 1) % count;
          roam.seed = (Math.imul(roam.seed, 1664525) + 1013904223) >>> 0;
          const randomA = roam.seed / 4294967296;
          roam.seed = (Math.imul(roam.seed, 1664525) + 1013904223) >>> 0;
          const randomB = roam.seed / 4294967296;
          const baseX = sharedWorldClamp(roam.x);
          const baseY = sharedWorldClamp(roam.y);
          const angle = randomA * Math.PI * 2;
          const distanceX = 0.012 + randomB * 0.019;
          const distanceY = 0.008 + randomB * 0.014;
          const desired = {
            x: sharedWorldClamp(baseX + Math.cos(angle) * distanceX, baseX),
            y: sharedWorldClamp(baseY + Math.sin(angle) * distanceY, baseY),
          };
          const homeDistance = Math.hypot(desired.x - roam.homeX, desired.y - roam.homeY);
          if (homeDistance > 0.065) {
            desired.x = sharedWorldClamp(baseX + (roam.homeX - baseX) * 0.48, baseX);
            desired.y = sharedWorldClamp(baseY + (roam.homeY - baseY) * 0.48, baseY);
          }
          const projectedTarget = sharedWorldProjectOrthogonalDestination(
            { x: baseX, y: baseY },
            desired,
          );
          const adjusted = Math.hypot(projectedTarget.x - desired.x, projectedTarget.y - desired.y) > 0.001;
          const stepDistance = Math.hypot(projectedTarget.x - baseX, projectedTarget.y - baseY);
          const pauseMs = randomB > 0.86 ? 5600 + randomA * 2200 : 2400 + randomA * 3100;
          roam.nextMoveAt = now + pauseMs;
          if (stepDistance < 0.003) {
            continue;
          }
          roam.x = projectedTarget.x;
          roam.y = projectedTarget.y;
          roam.moveCount += 1;
          row.tx = projectedTarget.x;
          row.ty = projectedTarget.y;
          const node = Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((item) => clean(item.dataset.slimeId || "") === id);
          if (node) {
            const x = Math.max(4, Math.min(96, projectedTarget.x * 100));
            const y = Math.max(8, Math.min(72, projectedTarget.y * 100));
            const duration = Math.round(720 + randomB * 260);
            node.dataset.slimeX = x.toFixed(2);
            node.dataset.slimeY = y.toFixed(2);
            node.dataset.worldDepthY = (y / 100).toFixed(4);
            node.style.setProperty("--slime-x", x.toFixed(2));
            node.style.setProperty("--slime-y", y.toFixed(2));
            node.style.setProperty("--slime-hop-duration", `${duration}ms`);
            node.classList.remove("is-hopping");
            void node.offsetWidth;
            node.classList.add("is-hopping");
            window.clearTimeout(node._worldTrainingHopTimer);
            node._worldTrainingHopTimer = window.setTimeout(() => {
              node.classList.remove("is-hopping");
              node._worldTrainingHopTimer = 0;
            }, duration + 60);
            scheduleSharedWorldCharacterDepthOrder();
          }
          window.__ftTrainingSlimeRoamTrace = {
            slimeId: id,
            from: { x: Number(baseX.toFixed(4)), y: Number(baseY.toFixed(4)) },
            to: { x: Number(projectedTarget.x.toFixed(4)), y: Number(projectedTarget.y.toFixed(4)) },
            stepPercent: Number((stepDistance * 100).toFixed(2)),
            selected: false,
            obstacleAdjusted: adjusted,
            hoppingCount: host.querySelectorAll(".is-hopping").length,
            nextMoveInMs: Math.round(pauseMs),
            at: Date.now(),
          };
          console.info("[FTG][TrainingSlimeRoam]", window.__ftTrainingSlimeRoamTrace);
          break;
        }
      };

      // Added 2026-08-10: immediately move Training slimes out of newly loaded or painted collision strokes.
      const rescueSharedWorldTrainingBlockedSlimes = () => {
        // Collision edits are server-owned; never rewrite shared coordinates in DOM state.
        return;
        /* istanbul ignore next */
        if (sharedWorldMapMode !== "training") {
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training
          ? sharedWorldTrainingState.training
          : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        let changed = false;
        slimes.forEach((slime) => {
          const row = slime && typeof slime === "object" ? slime : null;
          if (!row || Math.max(0, Number(row.hp || 0) || 0) <= 0) {
            return;
          }
          const current = {
            x: sharedWorldClamp(row.tx != null ? row.tx : row.x),
            y: sharedWorldClamp(row.ty != null ? row.ty : row.y),
          };
          if (!sharedWorldPointBlocked(current, 28)) {
            return;
          }
          const escape = sharedWorldFindEscapePoint(current, 28);
          row.x = escape.x;
          row.y = escape.y;
          row.tx = escape.x;
          row.ty = escape.y;
          const roam = sharedWorldTrainingSlimeRoamState.get(clean(row.id || ""));
          if (roam) {
            roam.x = escape.x;
            roam.y = escape.y;
            roam.homeX = escape.x;
            roam.homeY = escape.y;
          }
          changed = true;
        });
        if (changed) {
          renderSharedWorldTrainingSlimes(arena);
        }
      };

      const startSharedWorldTrainingLocalMotion = () => {
        // Shared Slime coordinates are server-authoritative; only CSS interpolates.
        stopSharedWorldTrainingLocalMotion({ preserveState: true });
      };

      const stopSharedWorldTrainingLocalMotion = (options = {}) => {
        if (sharedWorldTrainingLocalMotionTimer) {
          window.clearInterval(sharedWorldTrainingLocalMotionTimer);
          sharedWorldTrainingLocalMotionTimer = 0;
        }
        if (options && options.preserveState) {
          return;
        }
        sharedWorldTrainingSlimeRoamState.clear();
        sharedWorldTrainingSlimeRoamCursor = 0;
        sharedWorldTrainingSlimeSelectionQuietUntil = 0;
      };

      const renderSharedWorldTrainingLog = (arena = {}) => {
        if (!worldTrainingLog) {
          return;
        }
        const log = Array.isArray(arena.log) ? arena.log : [];
        worldTrainingLog.innerHTML = "";
        log.slice(-10).reverse().forEach((item) => {
          const row = item && typeof item === "object" ? item : {};
          const node = document.createElement("div");
          const type = clean(row.type || "");
          node.classList.toggle("is-hit", type === "hit" || type === "clear");
          node.classList.toggle("is-hurt", type === "hurt" || type === "restore");
          node.textContent = clean(row.text || row.message || "Practice log updated.");
          worldTrainingLog.appendChild(node);
        });
      };

      const createSharedWorldTrainingGhostSlime = (event = {}, options = {}) => {
        if (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp") {
          return sharedWorldTrainingCombatOverride.targetNode && sharedWorldTrainingCombatOverride.targetNode.isConnected
            ? sharedWorldTrainingCombatOverride.targetNode
            : null;
        }
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return null;
        }
        const slimeId = clean(event.slime_id || event.slimeId || "defeated-slime");
        const liveHost = sharedWorldTrainingSlimeHost();
        const liveNode = slimeId && liveHost
          ? Array.from(liveHost.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset && node.dataset.slimeId || "") === slimeId)
          : null;
        const liveX = Number(liveNode && liveNode.dataset && liveNode.dataset.slimeX);
        const liveY = Number(liveNode && liveNode.dataset && liveNode.dataset.slimeY);
        const x = Math.max(4, Math.min(96, Number.isFinite(liveX) ? liveX : 50));
        const y = Math.max(8, Math.min(72, Number.isFinite(liveY) ? liveY : 50));
        const defeated = options && Object.prototype.hasOwnProperty.call(options, "defeated") ? Boolean(options.defeated) : true;
        const ghost = document.createElement("span");
        ghost.className = `ft-world-training-slime ${defeated ? "is-defeated" : "is-hurt"}`;
        ghost.dataset.slimeId = slimeId;
        ghost.dataset.slimeX = x.toFixed(2);
        ghost.dataset.slimeY = y.toFixed(2);
        ghost.style.setProperty("--slime-x", x.toFixed(2));
        ghost.style.setProperty("--slime-y", y.toFixed(2));
        ghost.innerHTML = `
          <span class="ft-world-training-slime-core" aria-hidden="true"></span>
          <span class="ft-world-training-slime-name"><b>${escapeHtml(clean(event.slime_name || event.slimeName || "Slime"))}</b><span>Lv ${Math.max(1, Math.floor(Number(event.slime_level || event.slimeLevel || 1) || 1))}</span></span>
        `;
        effectHost.appendChild(ghost);
        window.setTimeout(() => ghost.remove(), defeated ? 1550 : 1220);
        return ghost;
      };

      const sharedWorldTrainingEffectSize = () => {
        const effectHost = sharedWorldTrainingEffectHost();
        const fallback = worldTrainingField || worldArena;
        return {
          host: effectHost,
          width: Math.max(1, Number((effectHost && effectHost.clientWidth) || (fallback && fallback.clientWidth) || (worldArena && worldArena.scrollWidth) || 1)),
          height: Math.max(1, Number((effectHost && effectHost.clientHeight) || (fallback && fallback.clientHeight) || (worldArena && worldArena.scrollHeight) || 1)),
        };
      };

      const sharedWorldTrainingPointFromNormalized = (x = 0.5, y = 0.5) => {
        const size = sharedWorldTrainingEffectSize();
        return {
          x: sharedWorldClamp(x, 0.5) * size.width,
          y: sharedWorldClamp(y, 0.5) * size.height,
        };
      };

      const sharedWorldTrainingNodePoint = (node, yRatio = 0.32) => {
        const size = sharedWorldTrainingEffectSize();
        if (!node || !size.host) {
          return { x: size.width * 0.5, y: size.height * 0.5 };
        }
        const rawX = Number(node.dataset && node.dataset.slimeX);
        const rawY = Number(node.dataset && node.dataset.slimeY);
        if (Number.isFinite(rawX) && Number.isFinite(rawY)) {
          return {
            x: Math.max(0, Math.min(size.width, (rawX / 100) * size.width)),
            y: Math.max(0, Math.min(size.height, (rawY / 100) * size.height)),
          };
        }
        const hostRect = size.host.getBoundingClientRect();
        const rect = node.getBoundingClientRect();
        return {
          x: rect.left + rect.width * 0.5 - hostRect.left,
          y: rect.top + rect.height * yRatio - hostRect.top,
        };
      };

      const sharedWorldTrainingSelfPoint = () => {
        if (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.sourceNode) {
          return sharedWorldTrainingNodePoint(sharedWorldTrainingCombatOverride.sourceNode, 0.38);
        }
        const key = (clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner").toLowerCase();
        const pos = sharedWorldPositions.get(key);
        if (pos && Number.isFinite(Number(pos.x)) && Number.isFinite(Number(pos.y))) {
          return sharedWorldTrainingPointFromNormalized(pos.x, pos.y);
        }
        const selfNode = sharedWorldNodes.get(key);
        return sharedWorldTrainingNodePoint(selfNode, 0.38);
      };

      const sharedWorldTrainingCombatSelf = () => (
        sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.sourceNode
          ? { node: sharedWorldTrainingCombatOverride.sourceNode }
          : ensureSharedWorldSelfNode()
      );

      // Added 2026-08-11: anchor player rewards above the unified Training HUD instead of the character body.
      const sharedWorldTrainingPlayerHudPoint = () => {
        const size = sharedWorldTrainingEffectSize();
        const key = (clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner").toLowerCase();
        const selfNode = sharedWorldNodes.get(key) || (ensureSharedWorldSelfNode() || {}).node;
        const hud = selfNode && selfNode.querySelector(".ft-world-training-player-hud");
        if (!size.host || !hud) {
          return sharedWorldTrainingSelfPoint();
        }
        const hostRect = size.host.getBoundingClientRect();
        const hudRect = hud.getBoundingClientRect();
        return {
          x: Math.max(0, Math.min(size.width, hudRect.left + hudRect.width * 0.5 - hostRect.left)),
          y: Math.max(0, Math.min(size.height, hudRect.top - hostRect.top)),
        };
      };

      // Added 2026-08-14: damage text belongs above the Slime HUD while impact
      // art stays centered on the body.
      const sharedWorldTrainingSlimeDamagePoint = (target = null, fallback = {}) => {
        const size = sharedWorldTrainingEffectSize();
        const overhead = target && target.querySelector ? target.querySelector(".ft-world-training-slime-overhead") : null;
        if (!size.host || !overhead) return fallback;
        const hostRect = size.host.getBoundingClientRect();
        const rect = overhead.getBoundingClientRect();
        return {
          x: Math.max(0, Math.min(size.width, rect.left + rect.width * 0.5 - hostRect.left)),
          y: Math.max(0, Math.min(size.height, rect.top - hostRect.top - 12)),
        };
      };

      const flushSharedWorldTrainingImpactRender = () => {
        const effectHost = sharedWorldTrainingEffectHost();
        sharedWorldTrainingProjectileLockUntil = 0;
        const deferredPayload = sharedWorldTrainingDeferredRenderPayload;
        const deferredShared = sharedWorldTrainingDeferredSharedSnapshot;
        sharedWorldTrainingDeferredRenderPayload = null;
        sharedWorldTrainingDeferredSharedSnapshot = null;
        const trace = {
          feedbackBeforeHpRender: true,
          damageFloatsBeforeHpRender: effectHost ? effectHost.querySelectorAll(".ft-world-training-damage-float").length : 0,
          deferredPayload: Boolean(deferredPayload),
          at: Date.now(),
        };
        if (deferredPayload && typeof renderSharedWorldTraining === "function") {
          renderSharedWorldTraining(deferredPayload);
        }
        if (deferredShared) applySharedWorldTrainingSharedSnapshot(deferredShared, "impact-release");
        window.__ftTrainingImpactCommitTrace = trace;
        console.info("[FTG][TrainingImpactCommit]", JSON.stringify(trace));
      };

      const finishSharedWorldTrainingImpactRender = (onImpact = null) => {
        const deferredToExplosionFrame = typeof onImpact === "function" && onImpact() === "defer-render";
        if (!deferredToExplosionFrame) flushSharedWorldTrainingImpactRender();
      };

      // Added 2026-08-12: PvP damage labels anchor above the HP/MP panel instead of the character body.
      const sharedWorldBattleDamageHudPoint = (node = null) => {
        const size = sharedWorldTrainingEffectSize();
        const stats = node && node.querySelector(".ft-world-battle-stats");
        const head = node && node.querySelector(".ft-world-battle-player-head");
        if (!size.host || (!stats && !head)) {
          const fallback = sharedWorldTrainingNodePoint(node, 0.08);
          return { x: fallback.x, y: Math.max(0, fallback.y - 48) };
        }
        const hostRect = size.host.getBoundingClientRect();
        const rects = [stats, head].filter(Boolean).map((hud) => hud.getBoundingClientRect());
        const left = Math.min(...rects.map((rect) => rect.left));
        const right = Math.max(...rects.map((rect) => rect.right));
        const top = Math.min(...rects.map((rect) => rect.top));
        return {
          x: Math.max(0, Math.min(size.width, left + (right - left) * 0.5 - hostRect.left)),
          y: Math.max(0, Math.min(size.height, top - hostRect.top - 34)),
        };
      };

      const sharedWorldTrainingEventTargetPoint = (event = {}, target = null) => {
        if (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp" && target && target.isConnected) {
          return sharedWorldBattleDamageHudPoint(target);
        }
        let liveTarget = target && target.isConnected ? target : null;
        if (!liveTarget) {
          const slimeId = clean(event && (event.slime_id || event.slimeId) || "");
          const host = slimeId ? sharedWorldTrainingSlimeHost() : null;
          liveTarget = host && Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset && node.dataset.slimeId || "") === slimeId);
        }
        if (liveTarget && liveTarget.isConnected) {
          return sharedWorldTrainingNodePoint(liveTarget, 0.34);
        }
        const xValue = event.slime_x != null ? event.slime_x : event.slimeX;
        const yValue = event.slime_y != null ? event.slime_y : event.slimeY;
        if (Number.isFinite(Number(xValue)) && Number.isFinite(Number(yValue))) {
          return sharedWorldTrainingPointFromNormalized(Number(xValue), Number(yValue));
        }
        return sharedWorldTrainingNodePoint(target, 0.34);
      };

      // Added 2026-08-17: remote Training/PvP casts must face the actual target before the first animation frame.
      const faceSharedWorldTrainingCastSource = (event = {}, target = null, sourceNode = null, mode = "") => {
        const node = sourceNode || (sharedWorldTrainingCombatSelf() || {}).node;
        if (!node || !node.isConnected) return null;
        const start = sharedWorldTrainingNodePoint(node, 0.38);
        const end = sharedWorldTrainingEventTargetPoint(event, target);
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return null;
        setSharedWorldFacing(node, dx, dy, true);
        const facing = Math.abs(dy) > Math.abs(dx) * 0.72
          ? (dy < 0 ? "up" : "down")
          : (dx < 0 ? "left" : "right");
        const trace = Array.isArray(window.__ftRemoteSkillFacingTrace) ? window.__ftRemoteSkillFacingTrace : [];
        trace.push({
          mode: clean(mode || sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode || "training"),
          attacker: clean(event.attacker || event.username || node.dataset && node.dataset.username || ""),
          target: clean(event.slime_id || event.slimeId || event.primary_slime_id || event.primarySlimeId || ""),
          facing,
          dx: Math.round(dx),
          dy: Math.round(dy),
          at: Date.now(),
        });
        window.__ftRemoteSkillFacingTrace = trace.slice(-80);
        return facing;
      };

      // Added 2026-08-11: explosions use the rendered target visual's feet instead of the actor midpoint.
      const sharedWorldTrainingTargetFootPoint = (target = null) => {
        const size = sharedWorldTrainingEffectSize();
        if (!size.host || !target || !target.isConnected) {
          return sharedWorldTrainingEventTargetPoint({}, target);
        }
        const sprite = target.querySelector(".ft-world-battle-character-sprite, .ft-world-character-sprite, .ft-world-character, .ft-world-training-slime-core") || target;
        const hostRect = size.host.getBoundingClientRect();
        const spriteRect = sprite.getBoundingClientRect();
        return {
          x: Math.max(0, Math.min(size.width, spriteRect.left + spriteRect.width * 0.5 - hostRect.left)),
          y: Math.max(0, Math.min(size.height, spriteRect.bottom - hostRect.top)),
          targetRect: {
            left: spriteRect.left - hostRect.left,
            top: spriteRect.top - hostRect.top,
            width: spriteRect.width,
            height: spriteRect.height,
          },
        };
      };

      // Added 2026-08-13: aim PvP basic projectiles at the rendered opponent's abdomen.
      const sharedWorldBattleTargetAbdomenPoint = (target = null) => {
        const size = sharedWorldTrainingEffectSize();
        if (!size.host || !target || !target.isConnected) {
          return sharedWorldTrainingEventTargetPoint({}, target);
        }
        const sprite = target.querySelector(".ft-world-battle-character-sprite") || target;
        const hostRect = size.host.getBoundingClientRect();
        const spriteRect = sprite.getBoundingClientRect();
        return {
          x: Math.max(0, Math.min(size.width, spriteRect.left + spriteRect.width * 0.5 - hostRect.left)),
          y: Math.max(0, Math.min(size.height, spriteRect.top + spriteRect.height * 0.55 - hostRect.top)),
          spriteRect: {
            left: spriteRect.left - hostRect.left,
            top: spriteRect.top - hostRect.top,
            width: spriteRect.width,
            height: spriteRect.height,
          },
        };
      };

      // Added 2026-07-08: makes hits push slimes away from the caster and briefly stun strong hits.
      const applySharedWorldTrainingSlimeImpactPhysics = (target = null, event = {}, options = {}) => {
        if (!target || (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp")) {
          return;
        }
        const start = sharedWorldTrainingSelfPoint();
        const end = sharedWorldTrainingEventTargetPoint(event, target);
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const length = Math.max(1, Math.hypot(dx, dy));
        const power = Math.max(12, Math.min(34, Number(options.power || (event.critical || event.criticalHit ? 30 : 20)) || 20));
        const knockX = (dx / length) * power;
        const knockY = Math.max(-18, Math.min(18, (dy / length) * power * 0.45 - 8));
        const rotate = Math.max(-18, Math.min(18, (dx / length) * 14));
        target.style.setProperty("--slime-knock-x", `${knockX.toFixed(1)}px`);
        target.style.setProperty("--slime-knock-y", `${knockY.toFixed(1)}px`);
        target.style.setProperty("--slime-recoil-x", `${(knockX * 0.22).toFixed(1)}px`);
        target.style.setProperty("--slime-hit-rotate", `${rotate.toFixed(1)}deg`);
        target.style.setProperty("--slime-recoil-rotate", `${(rotate * -0.32).toFixed(1)}deg`);
        target.classList.remove("is-knocked", "is-stunned");
        void target.offsetWidth;
        target.classList.add("is-knocked");
        const stun = Boolean(options.stun || event.critical || event.criticalHit || event.slime_defeated || event.slimeDefeated);
        if (stun) {
          target.classList.add("is-stunned");
        }
        window.setTimeout(() => target.classList.remove("is-knocked"), 740);
        if (stun) {
          window.setTimeout(() => target.classList.remove("is-stunned"), 1280);
        }
      };

      // Added 2026-08-10: home the frame-9 projectile onto the slime's live position.
      const triggerSharedWorldTrainingDirectSkill = (event = {}, target = null, onImpact = null) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        const pvp = Boolean(combatOverride && combatOverride.mode === "pvp");
        const visualGeneration = sharedWorldTrainingVisualGeneration;
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const effectHost = sharedWorldTrainingEffectHost();
        if (!event || !event.correct) {
          return;
        }
        if (!effectHost) {
          if (typeof onImpact === "function") {
            onImpact();
          }
          return;
        }
        const skill = event.skill && typeof event.skill === "object" ? event.skill : {};
        const critical = Boolean(event.critical || event.criticalHit);
        const tone = clean(skill.tone || skill.id || "fireball").toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "fireball";
        const start = sharedWorldTrainingSelfPoint();
        let currentX = start.x;
        let currentY = start.y - 12;
        const targetId = clean(event.slime_id || event.slimeId || target && target.dataset && target.dataset.slimeId || "");
        let lastKnownTargetPoint = null;
        const resolveLiveTarget = () => {
          if (target && target.isConnected) return target;
          if (!targetId || !effectHost || typeof effectHost.querySelector !== "function") return null;
          const escapedId = typeof CSS !== "undefined" && CSS.escape ? CSS.escape(targetId) : targetId.replace(/([\\"'])/g, "\\$1");
          return document.querySelector(`[data-slime-id="${escapedId}"]`) || document.querySelector(`.ft-world-training-slime[data-slime-id="${escapedId}"]`);
        };
        const liveTargetPoint = () => {
          const liveTarget = resolveLiveTarget();
          if (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp" && liveTarget) {
            return sharedWorldBattleTargetAbdomenPoint(liveTarget);
          }
          const point = liveTarget
            ? sharedWorldTrainingNodePoint(liveTarget, 0.34)
            : (lastKnownTargetPoint || sharedWorldTrainingEventTargetPoint(event, target));
          lastKnownTargetPoint = { x: point.x, y: point.y };
          return { x: point.x, y: point.y - 18 };
        };
        const firstTarget = liveTargetPoint();
        const initialDx = firstTarget.x - currentX;
        const initialDy = firstTarget.y - currentY;
        // Keep short-range Training shots visible for roughly half a second too.
        // The previous 520px/s floor made nearby slimes look like they were hit at the hand.
        const initialDistance = Math.max(1, Math.hypot(initialDx, initialDy));
        const flightSpeed = Math.max(150, Math.min(900, initialDistance / 0.58));
        const expectedFlightMs = Math.round(initialDistance / flightSpeed * 1000);
        const minimumVisibleFlightMs = Math.max(360, Math.min(580, expectedFlightMs));
        window.__ftTrainingProjectileTrace = {
          stage: "created",
          map: sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp"
            ? "battle-pvp"
            : (event && event.preview_only ? "training-test" : "training-real"),
          targetId,
          start: { x: currentX, y: currentY },
          destination: { x: firstTarget.x, y: firstTarget.y },
          distance: Math.round(Math.hypot(firstTarget.x - currentX, firstTarget.y - currentY)),
          flightSpeed: Math.round(flightSpeed),
          expectedFlightMs,
          minimumVisibleFlightMs,
          targetConnected: Boolean(resolveLiveTarget()),
          at: Date.now(),
        };
        console.info("[FTG][TrainingProjectile]", JSON.stringify(window.__ftTrainingProjectileTrace));
        if (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp") {
          window.__ftPvpBasicProjectileTrace = {
            anchor: "target-abdomen",
            target: clean(event.slime_id || event.slimeId || ""),
            start: { x: currentX, y: currentY },
            destination: { x: firstTarget.x, y: firstTarget.y },
            targetSpriteRect: firstTarget.spriteRect || null,
            abdomenRatio: 0.55,
            at: Date.now(),
          };
          console.info("[FTG][PvpBasicProjectile]", window.__ftPvpBasicProjectileTrace);
        }
        const shot = document.createElement("span");
        shot.className = `ft-world-training-skill-shot is-${tone} is-skill-orb${critical ? " is-critical" : ""}`;
        shot.style.setProperty("--skill-current-x", `${currentX}px`);
        shot.style.setProperty("--skill-current-y", `${currentY}px`);
        shot.style.setProperty("--skill-angle", `${(Math.atan2(initialDy, initialDx) * 180 / Math.PI).toFixed(2)}deg`);
        shot.style.setProperty("--skill-orb-scale", `${Math.max(0.86, Math.min(1.28, initialDistance / 420))}`);
        shot.innerHTML = "";
        effectHost.appendChild(shot);
        // Keep polling/state renders from replacing the live target until this orb impacts.
        if (!(combatOverride && combatOverride.mode === "training-remote")) {
          sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 1900);
        }
        let previousTime = 0;
        let elapsedMs = 0;
        let finished = false;
        const finish = () => {
          if (finished) {
            return;
          }
          finished = true;
          shot.remove();
          finishSharedWorldTrainingImpactRender(onImpact);
        };
        const chase = (time) => {
          if (finished) {
            return;
          }
          if (!pvp && (visualGeneration !== sharedWorldTrainingVisualGeneration || !sharedWorldTrainingIsActive())) {
            finished = true;
            shot.remove();
            return;
          }
          if (!sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) {
            finished = true;
            shot.remove();
            return;
          }
          if (!previousTime) {
            previousTime = time;
          }
          const deltaSeconds = Math.min(0.05, Math.max(0.001, (time - previousTime) / 1000));
          previousTime = time;
          elapsedMs += deltaSeconds * 1000;
          const destination = liveTargetPoint();
          const dx = destination.x - currentX;
          const dy = destination.y - currentY;
          const distance = Math.hypot(dx, dy);
          if ((distance <= 18 && elapsedMs >= minimumVisibleFlightMs) || elapsedMs >= 2400) {
            shot.style.setProperty("--skill-current-x", `${destination.x}px`);
            shot.style.setProperty("--skill-current-y", `${destination.y}px`);
            window.__ftTrainingProjectileTrace = {
              ...(window.__ftTrainingProjectileTrace || {}),
              stage: "impact",
              elapsedMs: Math.round(elapsedMs),
              targetConnected: Boolean(resolveLiveTarget()),
              at: Date.now(),
            };
            console.info("[FTG][TrainingProjectile]", JSON.stringify(window.__ftTrainingProjectileTrace));
            finish();
            return;
          }
          const step = Math.min(distance, flightSpeed * deltaSeconds);
          currentX += dx / distance * step;
          currentY += dy / distance * step;
          shot.style.setProperty("--skill-current-x", `${currentX}px`);
          shot.style.setProperty("--skill-current-y", `${currentY}px`);
          shot.style.setProperty("--skill-angle", `${(Math.atan2(dy, dx) * 180 / Math.PI).toFixed(2)}deg`);
          window.requestAnimationFrame(chase);
        };
        window.requestAnimationFrame(chase);
      };

      const sharedWorldCharacterAssetState = {
        ready: false,
        promise: null,
        images: [],
        databasePromise: null,
        objectUrls: new Map(),
        etags: new Map(),
      };

      const SHARED_WORLD_CHARACTER_SELECT_FRAME_URL = "/future-assets/character_select_frame_2.png";
      const SHARED_WORLD_CHARACTER_CHANGE_BUTTON_URL = "/future-assets/character_change_button.png";
      const SHARED_WORLD_CHARACTER_MALE_CARD_URL = "/future-assets/character_male_default_card.png";
      const SHARED_WORLD_CHARACTER_FEMALE_CARD_URL = "/future-assets/character_female_default_card.png";
      const SHARED_WORLD_CHARACTER_SCORPIO_CARD_URL = "/future-assets/character_scorpio_card.png";
      const SHARED_WORLD_CHARACTER_CARD_ASSETS = [
        [SHARED_WORLD_CHARACTER_SELECT_FRAME_URL, "--qm-character-select-frame"],
        [SHARED_WORLD_CHARACTER_MALE_CARD_URL, "--qm-male-card"],
        [SHARED_WORLD_CHARACTER_FEMALE_CARD_URL, "--qm-female-card"],
        [SHARED_WORLD_CHARACTER_SCORPIO_CARD_URL, "--qm-scorpio-card"],
      ];
      const SHARED_WORLD_CHARACTER_CARD_REVALIDATE_MS = 5 * 60 * 1000;
      let sharedWorldCharacterSelectFramePromise = null;
      let sharedWorldCharacterCardDeckPromise = null;
      let sharedWorldCharacterCardDeckHydratePromise = null;
      let sharedWorldCharacterCardDeckRevalidatedAt = 0;

      const sharedWorldCharacterAssets = [
        ["/future-assets/map_loading.png", "--qm-map-loading"],
        ["/future-assets/qm_city_map.png", "--qm-city-map"],
        ["/future-assets/train_map_1.png", "--qm-training-map"],
        ["/future-assets/qm_city_battle_map_1.png", "--qm-battle-map"],
        [SHARED_WORLD_CHARACTER_CHANGE_BUTTON_URL, "--qm-character-change-button"],
        ...SHARED_WORLD_CHARACTER_CARD_ASSETS,
        ["/future-assets/character_male_default_stand_atlas.png", "--qm-male-stand"],
        ["/future-assets/character_male_default_run_atlas.png", "--qm-male-run"],
        ["/future-assets/character_male_default_stand_style_2_atlas.png", "--qm-male-stand-style-2"],
        ["/future-assets/character_male_default_run_side_atlas.png", "--qm-male-run-side"],
        ["/future-assets/character_male_default_run_down_style_2_atlas.png", "--qm-male-run-down-style-2"],
        ["/future-assets/character_male_default_run_up_style_2_atlas.png", "--qm-male-run-up-style-2"],
        ["/future-assets/character_male_default_skill_1_atlas.png", "--qm-male-skill-one"],
        ["/future-assets/character_male_default_skill_2_atlas.png", "--qm-male-skill-two"],
        ["/future-assets/character_male_default_skill_2_projectile.png", "--qm-male-skill-two-projectile"],
        ["/future-assets/character_male_default_ultimate_style_5_atlas.png", "--qm-male-ultimate-style-5"],
        ["/future-assets/character_male_default_ultimate_style_5_burn_enemy_atlas.png", "--qm-male-ultimate-style-5-burn-enemy"],
        ["/future-assets/character_male_default_ultimate_burn_enemy.png", "--qm-male-ultimate-burn"],
        ["/future-assets/character_male_default_ultimate_skill_button.png", "--qm-male-ultimate-skill-button"],
        ["/future-assets/character_male_default_avatar.png", "--qm-male-avatar"],
        ["/future-assets/character_male_default_basic_enemy_explosion_atlas.png", "--qm-male-basic-enemy-explosion"],
        ...Array.from({ length: 8 }, (_unused, index) => [
          `/future-assets/character_male_default_enemy_explosion_${index + 1}.png`,
          `--qm-male-enemy-explosion-${index + 1}`,
        ]),
        ...Array.from({ length: 8 }, (_unused, index) => [
          `/future-assets/character_male_default_basic_skill_${index + 1}.png`,
          `--qm-male-basic-skill-${index + 1}`,
        ]),
        ["/future-assets/character_female_default_stand_atlas.png", "--qm-female-stand"],
        ["/future-assets/character_female_default_run_down_atlas.png", "--qm-female-run-down"],
        ["/future-assets/character_female_default_run_up_atlas.png", "--qm-female-run-up"],
        ["/future-assets/character_female_default_run_left_atlas.png", "--qm-female-run-left"],
        ["/future-assets/character_female_default_run_right_atlas.png", "--qm-female-run-right"],
        ["/future-assets/character_female_default_ranged_down_right_atlas.png", "--qm-female-ranged-down-right"],
        ["/future-assets/character_female_default_ranged_down_left_atlas.png", "--qm-female-ranged-down-left"],
        ["/future-assets/character_female_default_ranged_up_right_atlas.png", "--qm-female-ranged-up-right"],
        ["/future-assets/character_female_default_ranged_up_left_atlas.png", "--qm-female-ranged-up-left"],
        ["/future-assets/character_female_default_ranged_up_spear_atlas.png", "--qm-female-ranged-up-spear"],
        ["/future-assets/character_female_default_ranged_attack_impact.png", "--qm-female-ranged-impact"],
        ["/future-assets/character_female_default_ultimate_right_atlas.png", "--qm-female-ultimate-right"],
        ["/future-assets/character_female_default_ultimate_left_atlas.png", "--qm-female-ultimate-left"],
        ["/future-assets/character_female_default_ultimate_projectile.png", "--qm-female-ultimate-projectile"],
        ["/future-assets/character_female_default_ultimate_impact_atlas.png", "--qm-female-ultimate-impact"],
        ["/future-assets/character_female_default_ultimate_skill_button.png", "--qm-female-ultimate-skill-button"],
        ["/future-assets/character_female_default_avatar_1.png", "--qm-female-avatar-one"],
        ...Array.from({ length: 10 }, (_unused, index) => [
          `/future-assets/character_female_default_basic_skill_${index + 1}.png`,
          `--qm-female-basic-skill-${index + 1}`,
        ]),
        ["/future-assets/character_scorpio_stand_atlas.png", "--qm-scorpio-stand"],
        ["/future-assets/character_scorpio_run_down_atlas.png", "--qm-scorpio-run-down"],
        ["/future-assets/character_scorpio_run_side_atlas.png", "--qm-scorpio-run-side"],
        ["/future-assets/character_scorpio_run_up_atlas.png", "--qm-scorpio-run-up"],
        ["/future-assets/character_scorpio_basic_1_atlas.png", "--qm-scorpio-basic-one"],
        ["/future-assets/character_scorpio_basic_2_atlas.png", "--qm-scorpio-basic-two"],
        ["/future-assets/character_scorpio_basic_3_atlas.png", "--qm-scorpio-basic-three"],
        ["/future-assets/character_scorpio_homing_arrow_1.png", "--qm-scorpio-arrow-one"],
        ["/future-assets/character_scorpio_homing_arrow_2.png", "--qm-scorpio-arrow-two"],
        ["/future-assets/character_scorpio_basic_burn_atlas.png", "--qm-scorpio-basic-burn"],
        ["/future-assets/character_scorpio_ultimate_atlas.png", "--qm-scorpio-ultimate"],
        ["/future-assets/character_scorpio_ultimate_burn_1_atlas.png", "--qm-scorpio-ultimate-burn-one"],
        ["/future-assets/character_scorpio_ultimate_burn_2_atlas.png", "--qm-scorpio-ultimate-burn-two"],
        ["/future-assets/character_scorpio_avatar.png", "--qm-scorpio-avatar"],
        ["/future-assets/character_scorpio_ultimate_skill_button.png", "--qm-scorpio-ultimate-skill-button"],
        ...Array.from({ length: 10 }, (_unused, index) => [
          `/future-assets/character_scorpio_basic_skill_${index + 1}.png`,
          `--qm-scorpio-basic-skill-${index + 1}`,
        ]),
      ];

      // Added 2026-08-10: persist QM-City animation blobs while ETag remains the server revision authority.
      const openSharedWorldCharacterAssetDatabase = () => {
        if (sharedWorldCharacterAssetState.databasePromise) {
          return sharedWorldCharacterAssetState.databasePromise;
        }
        sharedWorldCharacterAssetState.databasePromise = new Promise((resolve) => {
          if (!("indexedDB" in window)) {
            resolve(null);
            return;
          }
          const request = indexedDB.open("future_qm_city_character_asset_cache_v1", 1);
          request.onupgradeneeded = () => {
            const database = request.result;
            if (!database.objectStoreNames.contains("assets")) {
              database.createObjectStore("assets", { keyPath: "url" });
            }
          };
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(null);
          request.onblocked = () => resolve(null);
        });
        return sharedWorldCharacterAssetState.databasePromise;
      };

      const readSharedWorldCharacterAsset = async (url = "") => {
        const database = await openSharedWorldCharacterAssetDatabase();
        if (!database) {
          return null;
        }
        return new Promise((resolve) => {
          const request = database.transaction("assets", "readonly").objectStore("assets").get(url);
          request.onsuccess = () => resolve(request.result && request.result.blob instanceof Blob ? request.result : null);
          request.onerror = () => resolve(null);
        });
      };

      const writeSharedWorldCharacterAsset = async (row = {}) => {
        const database = await openSharedWorldCharacterAssetDatabase();
        if (!database || !(row.blob instanceof Blob)) {
          return false;
        }
        return new Promise((resolve) => {
          const transaction = database.transaction("assets", "readwrite");
          transaction.objectStore("assets").put(row);
          transaction.oncomplete = () => resolve(true);
          transaction.onerror = () => resolve(false);
          transaction.onabort = () => resolve(false);
        });
      };

      const decodeSharedWorldCharacterAsset = (source = "") => new Promise((resolve) => {
        const image = new Image();
        image.decoding = "async";
        sharedWorldCharacterAssetState.images.push(image);
        let settled = false;
        const finish = () => {
          if (settled) {
            return;
          }
          settled = true;
          if (typeof image.decode === "function") {
            image.decode().catch(() => {}).finally(resolve);
            return;
          }
          resolve();
        };
        image.addEventListener("load", finish, { once: true });
        image.addEventListener("error", finish, { once: true });
        image.src = source;
        if (image.complete && image.naturalWidth > 0) {
          finish();
        }
      });

      const loadSharedWorldCharacterAssetRow = async ([url, cssVariable], trace = null) => {
        const cached = await readSharedWorldCharacterAsset(url);
        const headers = {};
        if (cached && clean(cached.etag)) {
          headers["If-None-Match"] = clean(cached.etag);
        }
        let blob = null;
        let etag = clean(cached && cached.etag || "");
        let mode = "network-first";
        try {
          const response = await fetch(url, { cache: "no-store", credentials: "same-origin", headers });
          if (response.status === 304 && cached) {
            blob = cached.blob;
            mode = sharedWorldCharacterAssetState.objectUrls.has(url) ? "memory-304" : "idb-304";
          } else if (response.ok) {
            blob = await response.blob();
            etag = clean(response.headers.get("ETag") || "");
            mode = cached ? "network-update" : "network-first";
            await writeSharedWorldCharacterAsset({ url, etag, blob, updatedAt: Date.now() });
          }
        } catch (_error) {
          if (cached) {
            blob = cached.blob;
            mode = "idb-offline";
          }
        }
        let source = url;
        if (mode === "memory-304") {
          source = sharedWorldCharacterAssetState.objectUrls.get(url);
        } else if (blob instanceof Blob) {
          const previous = sharedWorldCharacterAssetState.objectUrls.get(url);
          source = URL.createObjectURL(blob);
          sharedWorldCharacterAssetState.objectUrls.set(url, source);
          if (cssVariable) {
            document.documentElement.style.setProperty(cssVariable, `url("${source}")`);
          }
          if (previous && previous !== source) {
            URL.revokeObjectURL(previous);
          }
        } else {
          mode = "direct-fallback";
        }
        if (etag) {
          sharedWorldCharacterAssetState.etags.set(url, etag);
        }
        if (mode !== "memory-304") {
          await decodeSharedWorldCharacterAsset(source);
        }
        if (Array.isArray(trace)) {
          trace.push({ url, mode, etag });
          window.__ftQmCityCharacterAssetCacheTrace = trace.slice();
        }
        return { url, mode, etag, source };
      };

      // Added 2026-08-17: paint the character deck from durable IndexedDB before any ETag revalidation.
      const hydrateSharedWorldCharacterAssetFromIdb = async ([url, cssVariable], trace = null) => {
        if (sharedWorldCharacterAssetState.objectUrls.has(url)) {
          const source = sharedWorldCharacterAssetState.objectUrls.get(url);
          if (cssVariable && source) {
            document.documentElement.style.setProperty(cssVariable, `url("${source}")`);
          }
          if (Array.isArray(trace)) {
            trace.push({ url, mode: "memory", etag: clean(sharedWorldCharacterAssetState.etags.get(url) || "") });
            window.__ftQmCityCharacterCardHydrateTrace = trace.slice();
          }
          return { url, mode: "memory", source };
        }
        const cached = await readSharedWorldCharacterAsset(url);
        if (!cached || !(cached.blob instanceof Blob)) {
          if (Array.isArray(trace)) {
            trace.push({ url, mode: "miss", etag: "" });
            window.__ftQmCityCharacterCardHydrateTrace = trace.slice();
          }
          return { url, mode: "miss", source: url };
        }
        const source = URL.createObjectURL(cached.blob);
        sharedWorldCharacterAssetState.objectUrls.set(url, source);
        const etag = clean(cached.etag || "");
        if (etag) {
          sharedWorldCharacterAssetState.etags.set(url, etag);
        }
        if (cssVariable) {
          document.documentElement.style.setProperty(cssVariable, `url("${source}")`);
        }
        if (Array.isArray(trace)) {
          trace.push({ url, mode: "idb-hydrate", etag });
          window.__ftQmCityCharacterCardHydrateTrace = trace.slice();
        }
        return { url, mode: "idb-hydrate", etag, source };
      };

      const hydrateSharedWorldCharacterCardDeckFromIdb = () => {
        if (sharedWorldCharacterCardDeckHydratePromise) {
          return sharedWorldCharacterCardDeckHydratePromise;
        }
        const trace = [];
        sharedWorldCharacterCardDeckHydratePromise = (async () => {
          for (const asset of SHARED_WORLD_CHARACTER_CARD_ASSETS) {
            await hydrateSharedWorldCharacterAssetFromIdb(asset, trace);
          }
          window.__ftQmCityCharacterCardHydrateTrace = trace.slice();
          console.info("[FTG][QMCityCharacterCardHydrate]", JSON.stringify({
            assets: trace.length,
            modes: trace.reduce((result, row) => {
              result[row.mode] = (result[row.mode] || 0) + 1;
              return result;
            }, {}),
          }));
        })().finally(() => {
          sharedWorldCharacterCardDeckHydratePromise = null;
        });
        return sharedWorldCharacterCardDeckHydratePromise;
      };

      const preloadSharedWorldCharacterSelectFrame = () => {
        if (sharedWorldCharacterSelectFramePromise) {
          return sharedWorldCharacterSelectFramePromise;
        }
        sharedWorldCharacterSelectFramePromise = decodeSharedWorldCharacterAsset(
          sharedWorldCharacterAssetState.objectUrls.get(SHARED_WORLD_CHARACTER_SELECT_FRAME_URL)
          || SHARED_WORLD_CHARACTER_SELECT_FRAME_URL
        );
        return sharedWorldCharacterSelectFramePromise;
      };

      const preloadSharedWorldCharacterCardDeck = () => {
        if (sharedWorldCharacterCardDeckPromise) {
          return sharedWorldCharacterCardDeckPromise;
        }
        if (Date.now() - sharedWorldCharacterCardDeckRevalidatedAt < SHARED_WORLD_CHARACTER_CARD_REVALIDATE_MS) {
          return hydrateSharedWorldCharacterCardDeckFromIdb();
        }
        const trace = [];
        sharedWorldCharacterCardDeckPromise = (async () => {
          await hydrateSharedWorldCharacterCardDeckFromIdb();
          for (const asset of SHARED_WORLD_CHARACTER_CARD_ASSETS) {
            await loadSharedWorldCharacterAssetRow(asset, trace);
          }
          sharedWorldCharacterCardDeckRevalidatedAt = Date.now();
          window.__ftQmCityCharacterCardCacheTrace = trace.slice();
          console.info("[FTG][QMCityCharacterCardCache]", JSON.stringify({
            assets: trace.length,
            modes: trace.reduce((result, row) => {
              result[row.mode] = (result[row.mode] || 0) + 1;
              return result;
            }, {}),
          }));
        })().finally(() => {
          sharedWorldCharacterCardDeckPromise = null;
        });
        return sharedWorldCharacterCardDeckPromise;
      };

      // Added 2026-08-10: validate cached atlases on every QM-City entry and decode all missing assets before combat.
      const preloadSharedWorldCharacterAssets = (revalidate = false) => {
        if (sharedWorldCharacterAssetState.promise) {
          return sharedWorldCharacterAssetState.promise;
        }
        if (sharedWorldCharacterAssetState.ready && !revalidate) {
          return Promise.resolve();
        }
        const trace = [];
        const orderedAssets = sharedWorldCharacterAssets.slice().sort(([leftUrl], [rightUrl]) => {
          const priority = (url) => {
            if (url.includes("map_loading.png")) return 0;
            if (url.includes("train_map_1.png")) return 1;
            if (url.includes("qm_city_battle_map_1.png")) return 2;
            if (url.includes("qm_city_map.png")) return 3;
            if (/skill_[12]_atlas|skill_2_projectile|ranged_|ultimate_(?:style|right|left|projectile|impact|burn)/.test(url)) return 4;
            if (/stand_atlas|run_/.test(url)) return 5;
            return 6;
          };
          return priority(leftUrl) - priority(rightUrl);
        });
        sharedWorldCharacterAssetState.promise = (async () => {
          const criticalMaps = orderedAssets.splice(0, 2);
          for (const asset of criticalMaps) {
            await loadSharedWorldCharacterAssetRow(asset, trace);
          }
          let cursor = 0;
          const workers = Array.from({ length: 3 }, async () => {
            while (cursor < orderedAssets.length) {
              const asset = orderedAssets[cursor];
              cursor += 1;
              await loadSharedWorldCharacterAssetRow(asset, trace);
            }
          });
          await Promise.all(workers);
        })().then(() => {
          sharedWorldCharacterAssetState.ready = true;
          window.__ftQmCityCharacterAssetCacheTrace = trace;
          const modes = trace.reduce((result, row) => {
            result[row.mode] = (result[row.mode] || 0) + 1;
            return result;
          }, {});
          document.documentElement.dataset.qmCharacterAssetCacheCount = String(trace.length);
          document.documentElement.dataset.qmCharacterAssetCacheModes = JSON.stringify(modes);
          console.info("[FTG][QMCityCharacterAssetCache]", JSON.stringify({ assets: trace.length, modes }));
        }).finally(() => {
          sharedWorldCharacterAssetState.promise = null;
        });
        return sharedWorldCharacterAssetState.promise;
      };

      // Added 2026-08-12: targeted runtime proof for Battle-map IndexedDB and conditional ETag revalidation.
      window.__ftSharedWorldAssetCacheProbe = async (url = "/future-assets/qm_city_battle_map_1.png") => {
        const assetUrl = clean(url) || "/future-assets/qm_city_battle_map_1.png";
        const cachedBefore = await readSharedWorldCharacterAsset(assetUrl);
        const headers = {};
        if (cachedBefore && clean(cachedBefore.etag)) {
          headers["If-None-Match"] = clean(cachedBefore.etag);
        }
        const response = await fetch(assetUrl, { cache: "no-store", credentials: "same-origin", headers });
        let mode = "network-first";
        let responseEtag = clean(response.headers.get("ETag") || cachedBefore && cachedBefore.etag || "");
        if (response.status === 304 && cachedBefore) {
          mode = "idb-304";
        } else if (response.ok) {
          const blob = await response.blob();
          mode = cachedBefore ? "network-update" : "network-first";
          await writeSharedWorldCharacterAsset({ url: assetUrl, etag: responseEtag, blob, updatedAt: Date.now() });
        }
        const cachedAfter = await readSharedWorldCharacterAsset(assetUrl);
        const result = {
          url: assetUrl,
          mode,
          status: response.status,
          sentIfNoneMatch: clean(cachedBefore && cachedBefore.etag || ""),
          etag: clean(cachedAfter && cachedAfter.etag || responseEtag),
          blobBytes: Number(cachedAfter && cachedAfter.blob && cachedAfter.blob.size || 0),
          blobType: clean(cachedAfter && cachedAfter.blob && cachedAfter.blob.type || ""),
        };
        window.__ftSharedWorldAssetCacheProbeResult = result;
        console.info("[FTG][SharedWorldAssetCacheProbe]", result);
        return result;
      };

      // Added 2026-08-10: finish the female spell impact before applying slime damage or defeat state.
      const triggerSharedWorldTrainingFemaleRangedImpact = (event = {}, target = null, onImpact = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          finishSharedWorldTrainingImpactRender(onImpact);
          return;
        }
        const isPvpImpact = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const point = target && target.isConnected
          ? (isPvpImpact ? sharedWorldTrainingTargetFootPoint(target) : sharedWorldTrainingNodePoint(target, 0.34))
          : sharedWorldTrainingEventTargetPoint(event, target);
        const impact = document.createElement("span");
        impact.className = "ft-world-training-female-ranged-impact";
        impact.classList.toggle("is-pvp-impact", isPvpImpact);
        impact.style.setProperty("--female-impact-x", `${point.x}px`);
        impact.style.setProperty("--female-impact-y", `${point.y}px`);
        if (isPvpImpact) {
          window.__ftPvpFemaleImpactTrace = {
            anchor: "target-feet",
            x: Math.round(point.x * 100) / 100,
            y: Math.round(point.y * 100) / 100,
            width: 356,
            height: 356,
            scale: 2,
            at: Date.now(),
          };
          console.info("[FTG][PvpFemaleImpact]", window.__ftPvpFemaleImpactTrace);
        }
        effectHost.appendChild(impact);
        let feedbackApplied = false;
        const applyFeedback = () => {
          if (feedbackApplied) return;
          feedbackApplied = true;
          finishSharedWorldTrainingImpactRender(onImpact);
        };
        window.requestAnimationFrame(applyFeedback);
        let finished = false;
        const finish = () => {
          if (finished) {
            return;
          }
          finished = true;
          impact.remove();
          applyFeedback();
        };
        impact.addEventListener("animationend", finish, { once: true });
        window.setTimeout(finish, 760);
      };

      // Added 2026-08-10: alternate spear frames while homing onto the slime's live position.
      const triggerSharedWorldTrainingFemaleSpear = (event = {}, target = null, onImpact = null) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        const pvp = Boolean(combatOverride && combatOverride.mode === "pvp");
        const visualGeneration = sharedWorldTrainingVisualGeneration;
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          triggerSharedWorldTrainingFemaleRangedImpact(event, target, onImpact);
          return;
        }
        const start = sharedWorldTrainingSelfPoint();
        let currentX = start.x;
        let currentY = start.y - 66;
        const liveTargetPoint = () => {
          const point = target && target.isConnected
            ? sharedWorldTrainingNodePoint(target, 0.34)
            : sharedWorldTrainingEventTargetPoint(event, target);
          return { x: point.x, y: point.y - 12 };
        };
        const firstTarget = liveTargetPoint();
        const initialDx = firstTarget.x - currentX;
        const initialDy = firstTarget.y - currentY;
        const initialDistance = Math.max(72, Math.hypot(initialDx, initialDy));
        const flightSpeed = Math.max(500, Math.min(1050, initialDistance / 0.74));
        const spear = document.createElement("span");
        spear.className = "ft-world-training-female-ranged-spear";
        spear.style.setProperty("--female-spear-x", `${currentX}px`);
        spear.style.setProperty("--female-spear-y", `${currentY}px`);
        // The source spear points about 24 degrees above its local x-axis; compensate so its tip tracks the target vector.
        spear.style.setProperty("--female-spear-angle", `${(Math.atan2(initialDy, initialDx) * 180 / Math.PI + 24).toFixed(2)}deg`);
        effectHost.appendChild(spear);
        let previousTime = 0;
        let elapsedMs = 0;
        let finished = false;
        const finish = () => {
          if (finished) {
            return;
          }
          finished = true;
          spear.remove();
          const previousOverride = sharedWorldTrainingCombatOverride;
          sharedWorldTrainingCombatOverride = combatOverride;
          try {
            triggerSharedWorldTrainingFemaleRangedImpact(event, target, onImpact);
          } finally {
            sharedWorldTrainingCombatOverride = previousOverride;
          }
        };
        const chase = (time) => {
          if (finished) {
            return;
          }
          if (!pvp && (visualGeneration !== sharedWorldTrainingVisualGeneration || !sharedWorldTrainingIsActive())) {
            finished = true;
            spear.remove();
            return;
          }
          if (!sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) {
            finished = true;
            spear.remove();
            return;
          }
          if (!previousTime) {
            previousTime = time;
          }
          const deltaSeconds = Math.min(0.05, Math.max(0.001, (time - previousTime) / 1000));
          previousTime = time;
          elapsedMs += deltaSeconds * 1000;
          const destination = liveTargetPoint();
          const dx = destination.x - currentX;
          const dy = destination.y - currentY;
          const distance = Math.hypot(dx, dy);
          if (distance <= 18 || elapsedMs >= 2400) {
            spear.style.setProperty("--female-spear-x", `${destination.x}px`);
            spear.style.setProperty("--female-spear-y", `${destination.y}px`);
            finish();
            return;
          }
          const step = Math.min(distance, flightSpeed * deltaSeconds);
          currentX += dx / distance * step;
          currentY += dy / distance * step;
          spear.style.setProperty("--female-spear-x", `${currentX}px`);
          spear.style.setProperty("--female-spear-y", `${currentY}px`);
          spear.style.setProperty("--female-spear-angle", `${(Math.atan2(dy, dx) * 180 / Math.PI + 24).toFixed(2)}deg`);
          window.requestAnimationFrame(chase);
        };
        window.requestAnimationFrame(chase);
      };

      // Added 2026-08-10: randomly play one complete female ranged combo; target position only flips it horizontally.
      const triggerSharedWorldTrainingFemaleRangedSkill = (event = {}, target = null, onImpact = null) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        if (!sharedWorldCharacterAssetState.ready) {
          preloadSharedWorldCharacterAssets().then(() => {
            const previousOverride = sharedWorldTrainingCombatOverride;
            sharedWorldTrainingCombatOverride = combatOverride;
            try {
              triggerSharedWorldTrainingFemaleRangedSkill(event, target, onImpact);
            } finally {
              sharedWorldTrainingCombatOverride = previousOverride;
            }
          });
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        if (!self || !self.node) {
          triggerSharedWorldTrainingFemaleRangedImpact(event, target, onImpact);
          return;
        }
        const start = sharedWorldTrainingSelfPoint();
        const end = target && target.isConnected
          ? sharedWorldTrainingNodePoint(target, 0.34)
          : sharedWorldTrainingEventTargetPoint(event, target);
        const combo = Math.random() < 0.5 ? "up" : "down";
        const direction = end.x < start.x ? "left" : "right";
        setSharedWorldFacing(self.node, end.x - start.x, end.y - start.y, true);
        const frameDuration = 130;
        const comboDuration = combo === "up" ? frameDuration * 10 : frameDuration * 11;
        const castClasses = [
          "is-training-cast",
          "is-training-critical-cast",
          "is-female-ranged-up",
          "is-female-ranged-down",
          "is-female-ranged-left",
          "is-female-ranged-right",
        ];
        const isRemoteTrainingCast = Boolean(combatOverride && combatOverride.mode === "training-remote");
        const remoteCastToken = isRemoteTrainingCast
          ? clean(self.node.dataset.trainingRemoteCastToken || "")
          : "";
        let castNode = self.node;
        if (isRemoteTrainingCast) {
          const effectHost = sharedWorldTrainingEffectHost();
          const sourcePoint = sharedWorldTrainingNodePoint(self.node, 0.5);
          if (effectHost) {
            castNode = document.createElement("span");
            castNode.className = "ft-world-player ft-world-training-remote-female-cast is-character-female-default";
            castNode.style.left = `${sourcePoint.x}px`;
            castNode.style.top = `${sourcePoint.y}px`;
            castNode.innerHTML = '<span class="ft-world-character-stage"><span class="ft-world-character" aria-hidden="true"></span></span>';
            effectHost.appendChild(castNode);
            self.node.classList.add("is-training-remote-cast-source");
          }
        }
        castNode.classList.remove(...castClasses);
        castNode.classList.add("is-training-cast", `is-female-ranged-${combo}`, `is-female-ranged-${direction}`);
        if (event.critical || event.criticalHit) {
          castNode.classList.add("is-training-critical-cast");
        }
        if (isRemoteTrainingCast) {
          window.requestAnimationFrame(() => {
            const character = castNode && castNode.querySelector(".ft-world-character");
            if (!castNode || !castNode.isConnected || !character) return;
            const playerStyle = window.getComputedStyle(castNode);
            const characterStyle = window.getComputedStyle(character);
            const trace = {
              eventId: clean(event.event_id || event.eventId || ""),
              attacker: clean(event.attacker || event.username || ""),
              combo,
              direction,
              detachedOverlay: castNode !== self.node,
              sourceClasses: self.node.className,
              overlayClasses: castNode.className,
              player: {
                filter: playerStyle.filter,
                isolation: playerStyle.isolation,
                willChange: playerStyle.willChange,
                contain: playerStyle.contain,
                background: playerStyle.backgroundColor,
                boxShadow: playerStyle.boxShadow,
              },
              character: {
                filter: characterStyle.filter,
                isolation: characterStyle.isolation,
                willChange: characterStyle.willChange,
                contain: characterStyle.contain,
                background: characterStyle.backgroundColor,
                boxShadow: characterStyle.boxShadow,
                image: characterStyle.backgroundImage,
                animation: characterStyle.animationName,
                transform: characterStyle.transform,
              },
              at: Date.now(),
            };
            window.__ftTrainingFemaleRemoteCastTrace = trace;
            console.info("[FTG][TrainingFemaleRemoteCast]", JSON.stringify(trace));
          });
        }
        window.setTimeout(() => {
          castNode.classList.remove(...castClasses);
          if (castNode !== self.node) castNode.remove();
          if (!remoteCastToken || self.node.dataset.trainingRemoteCastToken === remoteCastToken) {
            self.node.classList.remove("is-training-remote-cast-source");
          }
          setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        }, comboDuration + 100);
        // The up source releases at frame 9; the down combo launches at frame 6
        // so its projectile remains visible before the Battle hit feedback.
        const projectileDelay = frameDuration * (combo === "up" ? 8 : 5);
        window.setTimeout(() => {
          const previousOverride = sharedWorldTrainingCombatOverride;
          sharedWorldTrainingCombatOverride = combatOverride;
          try {
            window.__ftFemaleRangedProjectileTrace = {
              combo,
              direction,
              delayMs: projectileDelay,
              targetConnected: Boolean(target && target.isConnected),
              at: Date.now(),
            };
            console.info("[FTG][FemaleRangedProjectile]", window.__ftFemaleRangedProjectileTrace);
            triggerSharedWorldTrainingFemaleSpear(event, target, onImpact);
          } finally {
            sharedWorldTrainingCombatOverride = previousOverride;
          }
        }, projectileDelay);
      };

      // Added 2026-08-16: Scorpio burn begins at contact and releases the shared damage callback once.
      const triggerSharedWorldScorpioBurn = (event = {}, target = null, onImpact = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        const pvp = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        if (!effectHost || !sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) {
          finishSharedWorldTrainingImpactRender(onImpact);
          return;
        }
        const point = pvp && target && target.isConnected
          ? sharedWorldBattleTargetAbdomenPoint(target)
          : (target && target.isConnected ? sharedWorldTrainingNodePoint(target, 0.38) : sharedWorldTrainingEventTargetPoint(event, target));
        const burn = document.createElement("span");
        burn.className = "ft-world-training-scorpio-burn";
        burn.style.setProperty("--scorpio-burn-x", `${point.x}px`);
        burn.style.setProperty("--scorpio-burn-y", `${point.y}px`);
        effectHost.appendChild(burn);
        window.__ftScorpioBasicTrace = {
          ...(window.__ftScorpioBasicTrace || {}),
          stage: "burn",
          targetConnected: Boolean(target && target.isConnected),
          at: Date.now(),
        };
        console.info("[FTG][ScorpioBasic]", window.__ftScorpioBasicTrace);
        window.setTimeout(() => {
          if (!sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) return;
          finishSharedWorldTrainingImpactRender(onImpact);
        }, 220);
        window.setTimeout(() => burn.remove(), 820);
      };

      // Added 2026-08-16: show arrow frame 1 in front, then let frame 2 home onto the live target.
      const triggerSharedWorldScorpioProjectile = (event = {}, target = null, onImpact = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        const combatOverride = sharedWorldTrainingCombatOverride;
        const pvp = Boolean(combatOverride && combatOverride.mode === "pvp");
        const visualGeneration = sharedWorldTrainingVisualGeneration;
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        if (!effectHost) {
          triggerSharedWorldScorpioBurn(event, target, onImpact);
          return;
        }
        const source = sharedWorldTrainingSelfPoint();
        const targetId = clean(event.slime_id || event.slimeId || target && target.dataset && target.dataset.slimeId || "");
        const resolveLiveTarget = () => {
          if (target && target.isConnected) return target;
          if (!targetId) return null;
          const escapedId = typeof CSS !== "undefined" && CSS.escape ? CSS.escape(targetId) : targetId.replace(/([\\"'])/g, "\\$1");
          return document.querySelector(`[data-slime-id="${escapedId}"]`);
        };
        const liveTargetPoint = () => {
          const liveTarget = resolveLiveTarget();
          if (pvp && liveTarget) return sharedWorldBattleTargetAbdomenPoint(liveTarget);
          return liveTarget ? sharedWorldTrainingNodePoint(liveTarget, 0.38) : sharedWorldTrainingEventTargetPoint(event, target);
        };
        const firstTarget = liveTargetPoint();
        const firstDx = firstTarget.x - source.x;
        const firstDy = firstTarget.y - source.y;
        const firstDistance = Math.max(1, Math.hypot(firstDx, firstDy));
        // Updated 2026-08-16: clear both the actor and arrow radii so frame 1 cannot hide under the caster.
        const frameOneSpawnDistance = 228;
        let currentX = source.x + firstDx / firstDistance * frameOneSpawnDistance;
        let currentY = source.y + firstDy / firstDistance * frameOneSpawnDistance - 8;
        const arrow = document.createElement("span");
        arrow.className = "ft-world-training-scorpio-arrow is-frame-one";
        arrow.style.setProperty("--scorpio-arrow-x", `${currentX}px`);
        arrow.style.setProperty("--scorpio-arrow-y", `${currentY}px`);
        arrow.style.setProperty("--scorpio-arrow-angle", `${(Math.atan2(firstDy, firstDx) * 180 / Math.PI).toFixed(2)}deg`);
        effectHost.appendChild(arrow);
        if (!(combatOverride && combatOverride.mode === "training-remote")) {
          sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 2500);
        }
        window.__ftScorpioBasicTrace = {
          ...(window.__ftScorpioBasicTrace || {}),
          stage: "projectile-frame-1",
          targetId,
          spawnDistance: frameOneSpawnDistance,
          start: { x: Math.round(currentX), y: Math.round(currentY) },
          at: Date.now(),
        };
        console.info("[FTG][ScorpioBasic]", window.__ftScorpioBasicTrace);
        let previousTime = 0;
        let elapsedMs = 0;
        let frameTwo = false;
        const frameOneHoldMs = 260;
        const flightSpeed = Math.max(420, Math.min(1080, firstDistance / 0.62));
        const chase = (time) => {
          if (!arrow.isConnected || !sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)
            || (!pvp && (visualGeneration !== sharedWorldTrainingVisualGeneration || !sharedWorldTrainingIsActive()))) {
            arrow.remove();
            return;
          }
          if (!previousTime) previousTime = time;
          const deltaSeconds = Math.min(0.05, Math.max(0.001, (time - previousTime) / 1000));
          previousTime = time;
          elapsedMs += deltaSeconds * 1000;
          if (!frameTwo && elapsedMs >= frameOneHoldMs) {
            frameTwo = true;
            arrow.classList.remove("is-frame-one");
            arrow.classList.add("is-frame-two");
            window.__ftScorpioBasicTrace = {
              ...(window.__ftScorpioBasicTrace || {}),
              stage: "projectile-frame-2",
              frameOneHeldMs: Math.round(elapsedMs),
              targetId,
              at: Date.now(),
            };
            console.info("[FTG][ScorpioBasic]", window.__ftScorpioBasicTrace);
          }
          if (!frameTwo) {
            window.requestAnimationFrame(chase);
            return;
          }
          const destination = liveTargetPoint();
          const dx = destination.x - currentX;
          const dy = destination.y - currentY;
          const distance = Math.hypot(dx, dy);
          if ((distance <= 20 && elapsedMs >= frameOneHoldMs + 190) || elapsedMs >= 2600) {
            arrow.remove();
            window.__ftScorpioBasicTrace = {
              ...(window.__ftScorpioBasicTrace || {}),
              stage: "contact",
              elapsedMs: Math.round(elapsedMs),
              targetConnected: Boolean(resolveLiveTarget()),
              at: Date.now(),
            };
            console.info("[FTG][ScorpioBasic]", window.__ftScorpioBasicTrace);
            triggerSharedWorldScorpioBurn(event, resolveLiveTarget() || target, onImpact);
            return;
          }
          const step = Math.min(distance, flightSpeed * deltaSeconds);
          if (distance > 0) {
            currentX += dx / distance * step;
            currentY += dy / distance * step;
          }
          arrow.style.setProperty("--scorpio-arrow-x", `${currentX}px`);
          arrow.style.setProperty("--scorpio-arrow-y", `${currentY}px`);
          arrow.style.setProperty("--scorpio-arrow-angle", `${(Math.atan2(dy, dx) * 180 / Math.PI).toFixed(2)}deg`);
          window.requestAnimationFrame(chase);
        };
        window.requestAnimationFrame(chase);
      };

      // Added 2026-08-16: test and real Scorpio Basics share the same random cast and damage callback.
      const triggerSharedWorldScorpioBasicSkill = (event = {}, target = null, onImpact = null) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        const self = sharedWorldTrainingCombatSelf();
        if (!self || !self.node) {
          triggerSharedWorldScorpioProjectile(event, target, onImpact);
          return;
        }
        const start = sharedWorldTrainingSelfPoint();
        const end = target && target.isConnected
          ? sharedWorldTrainingNodePoint(target, 0.38)
          : sharedWorldTrainingEventTargetPoint(event, target);
        const skillIndex = 1 + Math.floor(Math.random() * 3);
        const frameCounts = { 1: 8, 2: 6, 3: 7 };
        const releaseFrames = { 1: 6, 2: 5, 3: 6 };
        const frameDuration = 130;
        const castDuration = frameCounts[skillIndex] * frameDuration;
        const releaseDelay = (releaseFrames[skillIndex] - 1) * frameDuration;
        const castClasses = [
          "is-training-cast",
          "is-training-critical-cast",
          "is-scorpio-basic-cast",
          "is-scorpio-basic-1",
          "is-scorpio-basic-2",
          "is-scorpio-basic-3",
          "is-scorpio-cast-left",
          "is-scorpio-cast-right",
        ];
        setSharedWorldFacing(self.node, end.x - start.x, end.y - start.y, true);
        self.node.classList.remove(...castClasses);
        self.node.classList.add("is-training-cast", "is-scorpio-basic-cast", `is-scorpio-basic-${skillIndex}`, end.x < start.x ? "is-scorpio-cast-left" : "is-scorpio-cast-right");
        if (event.critical || event.criticalHit) self.node.classList.add("is-training-critical-cast");
        if (!(combatOverride && combatOverride.mode === "training-remote")) {
          sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 3300);
        }
        window.__ftScorpioBasicTrace = {
          stage: "cast",
          skillIndex,
          releaseFrame: releaseFrames[skillIndex],
          releaseDelay,
          preview: Boolean(event.preview_only || event.previewOnly),
          at: Date.now(),
        };
        console.info("[FTG][ScorpioBasic]", window.__ftScorpioBasicTrace);
        window.setTimeout(() => {
          const previousOverride = sharedWorldTrainingCombatOverride;
          sharedWorldTrainingCombatOverride = combatOverride;
          try {
            triggerSharedWorldScorpioProjectile(event, target, onImpact);
          } finally {
            sharedWorldTrainingCombatOverride = previousOverride;
          }
        }, releaseDelay);
        window.setTimeout(() => self.node.classList.remove(...castClasses), castDuration + 80);
      };

      const triggerSharedWorldTrainingSkill = (event = {}, target = null, onImpact = null) => {
        if (!event || !event.correct) {
          return;
        }
        const combatOverride = sharedWorldTrainingCombatOverride;
        const pvp = Boolean(combatOverride && combatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        // 2026-08-12: do not spend the first cast's CSS duration while its atlas is still loading.
        if (!sharedWorldCharacterAssetState.ready) {
          preloadSharedWorldCharacterAssets().then(() => {
            if (!sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) return;
            const previousOverride = sharedWorldTrainingCombatOverride;
            sharedWorldTrainingCombatOverride = combatOverride;
            try {
              triggerSharedWorldTrainingSkill(event, target, onImpact);
            } finally {
              sharedWorldTrainingCombatOverride = previousOverride;
            }
          });
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        const runtimeMap = sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp"
          ? "battle-pvp"
          : (event && event.preview_only ? "training-test" : "training-real");
        window.__ftTrainingBasicSkillRuntime = {
          map: runtimeMap,
          targetId: clean(event.slime_id || event.slimeId || target && target.dataset && target.dataset.slimeId || ""),
          targetConnected: Boolean(target && target.isConnected),
          effectHost: Boolean(sharedWorldTrainingEffectHost()),
          source: "triggerSharedWorldTrainingSkill",
          at: Date.now(),
        };
        console.info("[FTG][TrainingBasicSkillRuntime]", JSON.stringify(window.__ftTrainingBasicSkillRuntime));
        if (self && self.node && self.node.classList.contains("is-character-scorpio")) {
          triggerSharedWorldScorpioBasicSkill(event, target, onImpact);
          return;
        }
        if (self && self.node && self.node.classList.contains("is-character-female-default")) {
          if (!(combatOverride && combatOverride.mode === "training-remote")) {
            sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 4800);
          }
          triggerSharedWorldTrainingFemaleRangedSkill(event, target, onImpact);
          return;
        }
        // Lock the target roster from cast start, not only from frame-6 projectile creation.
        // Poll responses must not replace the slime while the male cast atlas is preparing.
        if (!(combatOverride && combatOverride.mode === "training-remote")) {
          sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 2450);
        }
        window.__ftTrainingBasicSkillRuntime = {
          ...(window.__ftTrainingBasicSkillRuntime || {}),
          castStarted: true,
          renderLockedUntil: Math.round(sharedWorldTrainingProjectileLockUntil),
          at: Date.now(),
        };
        console.info("[FTG][TrainingBasicSkillRuntime]", JSON.stringify(window.__ftTrainingBasicSkillRuntime));
        const castDuration = event.critical || event.criticalHit ? 1500 : 1440;
        if (self && self.node) {
          const standingCharacter = self.node.querySelector(".ft-world-character");
          const standingRect = standingCharacter ? standingCharacter.getBoundingClientRect() : null;
          const start = sharedWorldTrainingSelfPoint();
          const end = sharedWorldTrainingEventTargetPoint(event, target);
          setSharedWorldFacing(self.node, end.x - start.x, end.y - start.y, true);
          self.node.classList.remove("is-training-cast", "is-training-critical-cast");
          self.node.classList.add("is-training-cast");
          window.requestAnimationFrame(() => {
            const castCharacter = self.node && self.node.querySelector(".ft-world-character");
            const castRect = castCharacter ? castCharacter.getBoundingClientRect() : null;
            window.__ftTrainingMaleBasicAnchorTrace = {
              map: runtimeMap,
              standingFoot: standingRect ? Math.round(standingRect.bottom * 10) / 10 : null,
              castFoot: castRect ? Math.round(castRect.bottom * 10) / 10 : null,
              footDelta: standingRect && castRect ? Math.round((castRect.bottom - standingRect.bottom) * 10) / 10 : null,
              standingHeight: standingRect ? Math.round(standingRect.height * 10) / 10 : null,
              castHeight: castRect ? Math.round(castRect.height * 10) / 10 : null,
              at: Date.now(),
            };
            console.info("[FTG][TrainingMaleBasicAnchor]", JSON.stringify(window.__ftTrainingMaleBasicAnchorTrace));
          });
          if (event.critical || event.criticalHit) {
            self.node.classList.add("is-training-critical-cast");
          }
          const clearCast = () => {
            self.node.classList.remove("is-training-cast", "is-training-critical-cast");
          };
          window.setTimeout(clearCast, castDuration);
        }
        // Frame 6 begins after five 120 ms steps in the 12-frame cast atlas.
        window.setTimeout(() => {
          if (!sharedWorldPvpAnimationLifecycleValid(lifecycleGeneration, pvp)) return;
          const previousOverride = sharedWorldTrainingCombatOverride;
          sharedWorldTrainingCombatOverride = combatOverride;
          try {
            triggerSharedWorldTrainingDirectSkill(event, target, onImpact);
          } finally {
            sharedWorldTrainingCombatOverride = previousOverride;
          }
        }, 600);
      };

      // Added 2026-08-12: keep compact runtime proof for every ultimate AoE target and damage block.
      const traceSharedWorldUltimateDamageRuntime = (stage = "", detail = {}) => {
        const entry = {
          stage: clean(stage),
          map: sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp" ? "battle-pvp" : "training",
          at: Date.now(),
          ...(detail && typeof detail === "object" ? detail : {}),
        };
        const trace = Array.isArray(window.__ftUltimateDamageTrace) ? window.__ftUltimateDamageTrace : [];
        trace.push(entry);
        if (trace.length > 80) trace.splice(0, trace.length - 80);
        window.__ftUltimateDamageTrace = trace;
        console.info("[FTG][UltimateDamage]", entry);
        return entry;
      };

      // Added 2026-08-11: show ultimate damage without replacing movement or sprite-atlas animations.
      const animateSharedWorldUltimateDamageTarget = (target = null) => {
        if (!target || !target.isConnected) return;
        const visual = target.querySelector(".ft-world-character, .ft-world-battle-character-sprite, .ft-world-training-slime-core") || target;
        if (!visual || typeof visual.animate !== "function") return;
        visual.animate([
          { filter: "brightness(1) saturate(1)", opacity: 1 },
          { filter: "brightness(2.15) saturate(0.35) drop-shadow(0 0 18px rgba(255, 96, 72, .95))", opacity: 0.72, offset: 0.18 },
          { filter: "brightness(0.72) saturate(1.7) drop-shadow(0 0 12px rgba(255, 174, 68, .75))", opacity: 0.9, offset: 0.44 },
          { filter: "brightness(1.55) saturate(1.15)", opacity: 1, offset: 0.68 },
          { filter: "brightness(1) saturate(1)", opacity: 1 },
        ], { duration: 760, easing: "cubic-bezier(.16,.84,.24,1)" });
      };

      // 2026-08-13: cancel PvP ultimate work as soon as its battle lifecycle has closed.
      const sharedWorldUltimateLifecycleValid = (generation = 0, pvp = false) => !pvp || (
        generation === sharedWorldBattleLifecycleGeneration
        && worldBattleModal
        && worldBattleModal.classList.contains("is-open")
      );

      const sharedWorldPvpAnimationLifecycleValid = (generation = 0, pvp = false) => !pvp || (
        generation === sharedWorldBattleLifecycleGeneration
        && document.visibilityState === "visible"
        && worldBattleModal
        && worldBattleModal.classList.contains("is-open")
      );

      const queueSharedWorldUltimateTimeout = (callback, delayMs = 0, pvp = false) => pvp
        ? queueSharedWorldBattleVisualTimeout(callback, delayMs)
        : window.setTimeout(callback, delayMs);

      // Updated 2026-08-11: play impact frames 11-12 once at the homing projectile's AoE center.
      const triggerSharedWorldTrainingFemaleUltimateImpact = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return;
        }
        const pvp = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        if (!sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) return;
        const pvpTarget = Boolean(pvp && target && target.isConnected);
        const centerX = Number(event.impact_center_x != null ? event.impact_center_x : event.impactCenterX);
        const centerY = Number(event.impact_center_y != null ? event.impact_center_y : event.impactCenterY);
        const point = pvpTarget
          ? sharedWorldTrainingTargetFootPoint(target)
          : Number.isFinite(centerX) && Number.isFinite(centerY)
          ? sharedWorldTrainingPointFromNormalized(centerX, centerY)
          : (target && target.isConnected ? sharedWorldTrainingNodePoint(target, 0.42) : sharedWorldTrainingEventTargetPoint(event, target));
        const impact = document.createElement("span");
        impact.className = "ft-world-training-female-ultimate-impact";
        impact.style.setProperty("--female-ultimate-impact-x", `${point.x}px`);
        impact.style.setProperty("--female-ultimate-impact-y", `${point.y}px`);
        effectHost.appendChild(impact);
        const affected = Array.isArray(event.affected) ? event.affected : [];
        queueSharedWorldUltimateTimeout(() => {
          if (!sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) return;
          const host = sharedWorldTrainingSlimeHost();
          affected.forEach((row) => {
            const id = clean(row && (row.slime_id || row.slimeId) || "");
            const hitTarget = host && Array.from(host.querySelectorAll("[data-slime-id]")).find((node) => clean(node.dataset.slimeId || "") === id);
            traceSharedWorldUltimateDamageRuntime("target-resolved", {
              pipeline: "female-ultimate",
              targetId: id,
              targetFound: Boolean(hitTarget),
              damage: Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0)),
            });
            if (hitTarget) {
              hitTarget.classList.add("is-hit");
              animateSharedWorldUltimateDamageTarget(hitTarget);
              applySharedWorldTrainingSlimeImpactPhysics(hitTarget, row, { stun: true, power: 36 });
              queueSharedWorldUltimateTimeout(() => hitTarget.classList.remove("is-hit"), 760, pvp);
            }
            if (!event.preview_only && !event.previewOnly) {
              const rowDamage = Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0));
              const rowPoint = hitTarget
                ? (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp"
                  ? sharedWorldBattleDamageHudPoint(hitTarget)
                  : sharedWorldTrainingNodePoint(hitTarget, 0.34))
                : sharedWorldTrainingEventTargetPoint(row, null);
              showSharedWorldTrainingDamageFloatAtPoint(rowPoint, `-${rowDamage} HP`, "critical", { y: -30 });
              if (row && (row.slime_defeated || row.slimeDefeated)) {
                showSharedWorldTrainingDamageFloatAtPoint(rowPoint, "SLIME DOWN", "defeat", { y: -68 });
              }
            }
          });
          showSharedWorldTrainingImpactBurst(point, "critical");
        }, 210, pvp);
        queueSharedWorldUltimateTimeout(() => impact.remove(), 920, pvp);
      };

      // Added 2026-08-10: frame 13 uses its bright tip as the live vector endpoint and homes onto a moving slime.
      const triggerSharedWorldTrainingFemaleUltimateProjectile = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          triggerSharedWorldTrainingFemaleUltimateImpact(event, target);
          return;
        }
        const pvp = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const visualGeneration = sharedWorldTrainingVisualGeneration;
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const selfPoint = sharedWorldTrainingSelfPoint();
        const liveTargetPoint = () => {
          const point = target && target.isConnected
            ? sharedWorldTrainingNodePoint(target, 0.4)
            : sharedWorldTrainingEventTargetPoint(event, target);
          return { x: point.x, y: point.y - 8 };
        };
        const firstTarget = liveTargetPoint();
        const direction = firstTarget.x < selfPoint.x ? -1 : 1;
        let currentX = selfPoint.x + direction * 118;
        let currentY = selfPoint.y - 70;
        const initialDx = firstTarget.x - currentX;
        const initialDy = firstTarget.y - currentY;
        const initialDistance = Math.max(80, Math.hypot(initialDx, initialDy));
        const flightSpeed = Math.max(640, Math.min(1320, initialDistance / 0.68));
        const projectile = document.createElement("span");
        projectile.className = "ft-world-training-female-ultimate-projectile";
        projectile.style.setProperty("--female-ultimate-projectile-x", `${currentX}px`);
        projectile.style.setProperty("--female-ultimate-projectile-y", `${currentY}px`);
        projectile.style.setProperty("--female-ultimate-projectile-angle", `${(Math.atan2(initialDy, initialDx) * 180 / Math.PI).toFixed(2)}deg`);
        effectHost.appendChild(projectile);
        let previousTime = 0;
        let elapsedMs = 0;
        let finished = false;
        let sampledTarget = firstTarget;
        let sampledAt = 0;
        const finish = () => {
          if (finished) {
            return;
          }
          finished = true;
          projectile.remove();
          if (sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) {
            triggerSharedWorldTrainingFemaleUltimateImpact(event, target);
          }
        };
        const chase = (time) => {
          if (finished || !projectile.isConnected || !sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)
            || (!pvp && (visualGeneration !== sharedWorldTrainingVisualGeneration || !sharedWorldTrainingIsActive()))) {
            projectile.remove();
            finished = true;
            return;
          }
          if (!previousTime) {
            previousTime = time;
          }
          const deltaSeconds = Math.min(0.05, Math.max(0.001, (time - previousTime) / 1000));
          previousTime = time;
          elapsedMs += deltaSeconds * 1000;
          if (!sampledAt || time - sampledAt >= 84) {
            sampledTarget = liveTargetPoint();
            sampledAt = time;
          }
          const destination = sampledTarget;
          const dx = destination.x - currentX;
          const dy = destination.y - currentY;
          const distance = Math.hypot(dx, dy);
          if (distance <= 22 || elapsedMs >= 2600) {
            projectile.style.setProperty("--female-ultimate-projectile-x", `${destination.x}px`);
            projectile.style.setProperty("--female-ultimate-projectile-y", `${destination.y}px`);
            finish();
            return;
          }
          const step = Math.min(distance, flightSpeed * deltaSeconds);
          currentX += dx / distance * step;
          currentY += dy / distance * step;
          projectile.style.setProperty("--female-ultimate-projectile-x", `${currentX}px`);
          projectile.style.setProperty("--female-ultimate-projectile-y", `${currentY}px`);
          projectile.style.setProperty("--female-ultimate-projectile-angle", `${(Math.atan2(dy, dx) * 180 / Math.PI).toFixed(2)}deg`);
          window.requestAnimationFrame(chase);
        };
        window.requestAnimationFrame(chase);
      };

      // Updated 2026-08-11: female default replaces Earthquake with frames 1-9, beam 13, then AoE frames 11-12.
      const triggerSharedWorldTrainingFemaleUltimate = (event = {}) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        if (!sharedWorldCharacterAssetState.ready) {
          preloadSharedWorldCharacterAssets().then(() => {
            const previousOverride = sharedWorldTrainingCombatOverride;
            sharedWorldTrainingCombatOverride = combatOverride;
            try {
              triggerSharedWorldTrainingFemaleUltimate(event);
            } finally {
              sharedWorldTrainingCombatOverride = previousOverride;
            }
          });
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        const pvp = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const effectHost = sharedWorldTrainingEffectHost();
        if (!self || !self.node || !effectHost) {
          return;
        }
        const pvpAnchorProbe = sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp"
          ? (self.node.querySelector(".ft-world-character") || null)
          : null;
        const pvpAnchorBefore = pvpAnchorProbe ? pvpAnchorProbe.getBoundingClientRect() : null;
        const host = sharedWorldTrainingSlimeHost();
        const targets = (Array.isArray(event.affected) ? event.affected : []).map((row) => {
          const targetId = clean(row && (row.slime_id || row.slimeId) || "");
          let target = host && Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === targetId);
          if (!target) {
            target = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row && (row.slime_defeated || row.slimeDefeated)) });
          }
          return { row, target };
        });
        const primary = targets.find(({ row }) => clean(row && (row.slime_id || row.slimeId) || "") === clean(event.primary_slime_id || event.primarySlimeId || "")) || targets[0] || null;
        const start = sharedWorldTrainingSelfPoint();
        const end = primary
          ? sharedWorldTrainingEventTargetPoint(primary.row, primary.target)
          : { x: start.x + 180, y: start.y };
        const direction = end.x < start.x ? "left" : "right";
        const castClasses = [
          "is-training-cast",
          "is-female-ultimate-cast",
          "is-female-ultimate-left",
          "is-female-ultimate-right",
        ];
        self.node.classList.remove(...castClasses, "is-earthquake-cast");
        setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        self.node.classList.add("is-training-cast", "is-female-ultimate-cast", `is-female-ultimate-${direction}`);
        if (pvpAnchorProbe && pvpAnchorBefore) {
          window.requestAnimationFrame(() => {
            const after = pvpAnchorProbe.getBoundingClientRect();
            window.__ftPvpFemaleUltimateAnchorTrace = {
              sharedPipeline: "triggerSharedWorldBattleCast>triggerSharedWorldTrainingFemaleUltimate",
              beforeBottom: Number(pvpAnchorBefore.bottom.toFixed(2)),
              duringBottom: Number(after.bottom.toFixed(2)),
              bottomDelta: Number((after.bottom - pvpAnchorBefore.bottom).toFixed(2)),
              beforeCenterX: Number((pvpAnchorBefore.left + pvpAnchorBefore.width / 2).toFixed(2)),
              duringCenterX: Number((after.left + after.width / 2).toFixed(2)),
              at: Date.now(),
            };
            console.info("[FTG][PvpFemaleUltimateAnchor]", window.__ftPvpFemaleUltimateAnchorTrace);
          });
        }
        const frameDuration = 135;
        const castDuration = frameDuration * 9;
        queueSharedWorldUltimateTimeout(() => {
          if (primary && sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) {
            triggerSharedWorldTrainingFemaleUltimateProjectile(event, primary.target);
          }
        }, castDuration, pvp);
        queueSharedWorldUltimateTimeout(() => {
          if (!sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) return;
          self.node.classList.remove(...castClasses);
          setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        }, castDuration + 180, pvp);
      };

      // Added 2026-08-14: Male Default uses only Style 5; frame 7 starts the enemy explosion.
      const triggerSharedWorldTrainingMaleUltimate = (event = {}) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        if (!sharedWorldCharacterAssetState.ready) {
          preloadSharedWorldCharacterAssets().then(() => {
            const previousOverride = sharedWorldTrainingCombatOverride;
            sharedWorldTrainingCombatOverride = combatOverride;
            try {
              triggerSharedWorldTrainingMaleUltimate(event);
            } finally {
              sharedWorldTrainingCombatOverride = previousOverride;
            }
          });
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        const pvp = Boolean(sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const effectHost = sharedWorldTrainingEffectHost();
        if (!self || !self.node || !effectHost) {
          return;
        }
        const host = sharedWorldTrainingSlimeHost();
        let targetId = clean(event.primary_slime_id || event.primarySlimeId || "");
        if (!targetId && !pvp) {
          const fallbackTarget = sharedWorldAdminTrainingTarget();
          targetId = clean(fallbackTarget && fallbackTarget.dataset && fallbackTarget.dataset.slimeId || "");
          if (targetId) {
            event = {
              ...event,
              primary_slime_id: targetId,
              slime_id: targetId,
              affected: Array.isArray(event.affected) && event.affected.length
                ? event.affected
                : [{ slime_id: targetId, damage: event.damage || 0 }],
            };
          }
        }
        let target = targetId && host
          ? Array.from(host.querySelectorAll("[data-slime-id]")).find((node) => clean(node.dataset.slimeId || "") === targetId)
          : null;
        if (!target && targetId) {
          const row = (Array.isArray(event.affected) ? event.affected : []).find((item) => clean(item && (item.slime_id || item.slimeId) || "") === targetId);
          if (row) {
            target = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row.slime_defeated || row.slimeDefeated) });
          }
        }
        if (!target) {
          return;
        }
        // 2026-08-11: reacquire the moving Slime before every facing decision so Male Nộ never uses a stale DOM position.
        const resolveLiveTarget = () => {
          const liveHost = sharedWorldTrainingSlimeHost();
          const liveTarget = targetId && liveHost
            ? Array.from(liveHost.querySelectorAll("[data-slime-id]")).find((node) => clean(node.dataset.slimeId || "") === targetId)
            : null;
          if (liveTarget) {
            target = liveTarget;
          }
          return target;
        };
        const castToken = ++sharedWorldMaleUltimateCastToken;
        const castClasses = [
          "is-training-cast",
          "is-male-ultimate-cast",
          "is-male-ultimate-style-5",
          "is-male-ultimate-left",
          "is-male-ultimate-right",
        ];
        let direction = "";
        let trackingDirection = true;
        const syncDirection = () => {
          const liveTarget = resolveLiveTarget();
          const selfPoint = sharedWorldTrainingSelfPoint();
          const liveTargetPoint = liveTarget && liveTarget.isConnected
            ? sharedWorldTrainingNodePoint(liveTarget, 0.38)
            : sharedWorldTrainingEventTargetPoint(event, liveTarget);
          const nextDirection = liveTargetPoint.x < selfPoint.x ? "left" : "right";
          if (nextDirection !== direction || !self.node.classList.contains(`is-male-ultimate-${nextDirection}`)) {
            direction = nextDirection;
            self.node.classList.remove("is-male-ultimate-left", "is-male-ultimate-right");
            setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
            self.node.classList.add(`is-male-ultimate-${direction}`);
          }
          return liveTargetPoint;
        };
        const trackDirection = () => {
          if (!trackingDirection || castToken !== sharedWorldMaleUltimateCastToken || !self.node.isConnected
            || !sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) {
            return;
          }
          syncDirection();
          queueSharedWorldUltimateTimeout(trackDirection, 90, pvp);
        };
        self.node.classList.remove(...castClasses, "is-earthquake-cast");
        self.node.classList.add("is-training-cast", "is-male-ultimate-cast", "is-male-ultimate-style-5");
        syncDirection();
        queueSharedWorldUltimateTimeout(trackDirection, 90, pvp);
        const frameDuration = 150;
        const castDuration = frameDuration * 9;
        const burnDelay = frameDuration * 6;
        const burn = () => {
          if (castToken !== sharedWorldMaleUltimateCastToken || !sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) {
            return;
          }
          const liveTarget = resolveLiveTarget();
          syncDirection();
          const livePoint = liveTarget && liveTarget.isConnected
            ? sharedWorldTrainingTargetFootPoint(liveTarget)
            : sharedWorldTrainingEventTargetPoint(event, liveTarget);
          const burst = document.createElement("span");
          burst.className = "ft-world-training-male-ultimate-burn is-ground-underlay";
          burst.style.setProperty("--male-ultimate-burn-x", `${livePoint.x}px`);
          burst.style.setProperty("--male-ultimate-burn-y", `${livePoint.y}px`);
          const underlayHost = typeof sharedWorldTrainingUnderlayHost === "function"
            ? (sharedWorldTrainingUnderlayHost() || effectHost)
            : effectHost;
          underlayHost.appendChild(burst);
          const targetType = liveTarget && liveTarget.classList.contains("is-character-female-default")
            ? "battle-female"
            : (liveTarget && liveTarget.classList.contains("is-character-male-default")
              ? "battle-male"
              : "slime");
          window.__ftMaleUltimateStyle5Trace = {
            style: 5,
            characterFrames: 9,
            impactFrames: 10,
            impactStartedAtFrame: 7,
            targetId,
            targetFound: Boolean(liveTarget),
            anchor: "target-feet",
            targetType,
            targetFoot: { x: livePoint.x, y: livePoint.y },
            targetRect: livePoint.targetRect || null,
            burstLayer: underlayHost.id,
            impactMounted: Boolean(burst.isConnected),
            characterAssetMode: (window.__ftQmCityCharacterAssetCacheTrace || []).find((row) => clean(row && row.url || "").includes("ultimate_style_5_atlas.png")) || null,
            impactAssetMode: (window.__ftQmCityCharacterAssetCacheTrace || []).find((row) => clean(row && row.url || "").includes("ultimate_style_5_burn_enemy_atlas.png")) || null,
            at: Date.now(),
          };
          console.info("[FTG][MaleUltimateStyle5]", window.__ftMaleUltimateStyle5Trace);
          queueSharedWorldUltimateTimeout(() => {
            if (!burst.isConnected || !liveTarget || !liveTarget.isConnected) return;
            const targetSprite = liveTarget.querySelector(
              ".ft-world-battle-character-sprite, .ft-world-character-sprite, .ft-world-character, .ft-world-training-slime-core"
            ) || liveTarget;
            const targetDomRect = targetSprite.getBoundingClientRect();
            const burstRect = burst.getBoundingClientRect();
            const layerRect = underlayHost.getBoundingClientRect();
            const domTrace = {
              targetType,
              targetFootViewportY: Math.round(targetDomRect.bottom * 100) / 100,
              burstCenterViewportY: Math.round((burstRect.top + burstRect.height * 0.5) * 100) / 100,
              centerFootDelta: Math.round((burstRect.top + burstRect.height * 0.5 - targetDomRect.bottom) * 100) / 100,
              targetZIndex: getComputedStyle(liveTarget).zIndex,
              burstZIndex: getComputedStyle(burst).zIndex,
              layerZIndex: getComputedStyle(underlayHost).zIndex,
              layerParent: underlayHost.parentElement && underlayHost.parentElement.className || "",
              layerRect: { left: layerRect.left, top: layerRect.top, width: layerRect.width, height: layerRect.height },
              targetRect: { left: targetDomRect.left, top: targetDomRect.top, width: targetDomRect.width, height: targetDomRect.height },
              burstRect: { left: burstRect.left, top: burstRect.top, width: burstRect.width, height: burstRect.height },
              at: Date.now(),
            };
            window.__ftMaleUltimateStyle5DomTrace = domTrace;
            console.info("[FTG][MaleUltimateStyle5DOM]", domTrace);
          }, 48, pvp);
          const affected = Array.isArray(event.affected) && event.affected.length
            ? event.affected
            : [{ slime_id: targetId, damage: event.damage || 0 }];
          showSharedWorldTrainingImpactBurst(livePoint, "critical");
          affected.forEach((row, index) => {
            const affectedId = clean(row && (row.slime_id || row.slimeId) || "");
            let hitTarget = affectedId && host
              ? Array.from(host.querySelectorAll("[data-slime-id]")).find((node) => clean(node.dataset.slimeId || "") === affectedId)
              : null;
            if (!hitTarget && affectedId === targetId) hitTarget = liveTarget;
            if (!hitTarget && row) {
              hitTarget = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row.slime_defeated || row.slimeDefeated) });
            }
            traceSharedWorldUltimateDamageRuntime("target-resolved", {
              pipeline: "male-ultimate",
              targetId: affectedId,
              targetFound: Boolean(hitTarget),
              ghost: Boolean(hitTarget && hitTarget.classList.contains("is-training-ghost")),
              damage: Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0)),
            });
            const hitPoint = hitTarget && hitTarget.isConnected
              ? (sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp"
                ? sharedWorldBattleDamageHudPoint(hitTarget)
                : sharedWorldTrainingNodePoint(hitTarget, 0.32))
              : sharedWorldTrainingEventTargetPoint(row, hitTarget);
            window.setTimeout(() => {
              if (hitTarget) {
                hitTarget.classList.add("is-hit");
                animateSharedWorldUltimateDamageTarget(hitTarget);
                applySharedWorldTrainingSlimeImpactPhysics(hitTarget, row, { stun: true, power: 42 });
                window.setTimeout(() => hitTarget.classList.remove("is-hit"), 760);
              }
              if (!event.preview_only && !event.previewOnly) {
                const damage = Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0));
                showSharedWorldTrainingDamageFloatAtPoint(hitPoint, `-${damage} HP`, "critical", { y: -34 });
                if (row && (row.slime_defeated || row.slimeDefeated)) {
                  showSharedWorldTrainingDamageFloatAtPoint(hitPoint, "SLIME DOWN", "defeat", { y: -72 });
                }
              }
            }, index * 55);
          });
          queueSharedWorldUltimateTimeout(() => burst.remove(), 1180, pvp);
        };
        queueSharedWorldUltimateTimeout(burn, burnDelay, pvp);
        queueSharedWorldUltimateTimeout(() => {
          if (castToken !== sharedWorldMaleUltimateCastToken) {
            return;
          }
          trackingDirection = false;
          self.node.classList.remove(...castClasses);
          setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        }, castDuration + 170, pvp);
      };

      // Added 2026-08-16: Scorpio frame 5 burns every server-confirmed enemy with an independent random variant.
      const triggerSharedWorldTrainingScorpioUltimate = (event = {}) => {
        const combatOverride = sharedWorldTrainingCombatOverride;
        if (!sharedWorldCharacterAssetState.ready) {
          preloadSharedWorldCharacterAssets().then(() => {
            const previousOverride = sharedWorldTrainingCombatOverride;
            sharedWorldTrainingCombatOverride = combatOverride;
            try {
              triggerSharedWorldTrainingScorpioUltimate(event);
            } finally {
              sharedWorldTrainingCombatOverride = previousOverride;
            }
          });
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        const effectHost = sharedWorldTrainingEffectHost();
        const pvp = Boolean(combatOverride && combatOverride.mode === "pvp");
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        if (!self || !self.node || !effectHost) return;
        const castToken = ++sharedWorldScorpioUltimateCastToken;
        const castClasses = [
          "is-training-cast",
          "is-scorpio-ultimate-cast",
          "is-scorpio-ultimate-left",
          "is-scorpio-ultimate-right",
        ];
        const affected = Array.isArray(event.affected) ? event.affected : [];
        const host = sharedWorldTrainingSlimeHost();
        const primaryId = clean(event.primary_slime_id || event.primarySlimeId || affected[0]?.slime_id || affected[0]?.slimeId || "");
        let primaryTarget = pvp && combatOverride && combatOverride.targetNode ? combatOverride.targetNode : null;
        if (!primaryTarget && host && primaryId) {
          primaryTarget = Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === primaryId) || null;
        }
        const selfPoint = sharedWorldTrainingSelfPoint();
        const targetPoint = primaryTarget && primaryTarget.isConnected
          ? sharedWorldTrainingNodePoint(primaryTarget, 0.38)
          : sharedWorldTrainingEventTargetPoint(event, primaryTarget);
        const direction = targetPoint.x < selfPoint.x ? "left" : "right";
        self.node.classList.remove(...castClasses, "is-earthquake-cast");
        self.node.classList.add("is-training-cast", "is-scorpio-ultimate-cast", `is-scorpio-ultimate-${direction}`);
        setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        const frameDuration = 150;
        const burnDelay = frameDuration * 4;
        const castDuration = frameDuration * 6;
        if (!(combatOverride && combatOverride.mode === "training-remote")) {
          sharedWorldTrainingProjectileLockUntil = Math.max(sharedWorldTrainingProjectileLockUntil, performance.now() + 1900);
        }
        queueSharedWorldUltimateTimeout(() => {
          if (castToken !== sharedWorldScorpioUltimateCastToken || !sharedWorldUltimateLifecycleValid(lifecycleGeneration, pvp)) return;
          const variants = [];
          affected.forEach((row, index) => {
            const targetId = clean(row && (row.slime_id || row.slimeId) || "");
            let target = pvp && combatOverride && combatOverride.targetNode ? combatOverride.targetNode : null;
            if (!target && host && targetId) {
              target = Array.from(host.querySelectorAll("[data-slime-id]"))
                .find((node) => clean(node.dataset.slimeId || "") === targetId) || null;
            }
            if (!target && row) target = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row.slime_defeated || row.slimeDefeated) });
            const point = pvp && target && target.isConnected
              ? sharedWorldBattleTargetAbdomenPoint(target)
              : (target && target.isConnected ? sharedWorldTrainingNodePoint(target, 0.38) : sharedWorldTrainingEventTargetPoint(row, target));
            const variant = Math.random() < 0.5 ? 1 : 2;
            variants.push({ targetId, variant });
            const burn = document.createElement("span");
            burn.className = `ft-world-training-scorpio-ultimate-burn is-variant-${variant}`;
            burn.style.setProperty("--scorpio-ultimate-burn-x", `${point.x}px`);
            burn.style.setProperty("--scorpio-ultimate-burn-y", `${point.y}px`);
            effectHost.appendChild(burn);
            if (target) {
              target.classList.add("is-hit");
              animateSharedWorldUltimateDamageTarget(target);
              applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: true, power: 34 });
              window.setTimeout(() => target && target.classList.remove("is-hit"), 720);
            }
            if (!event.preview_only && !event.previewOnly) {
              const damage = Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0));
              showSharedWorldTrainingDamageFloatAtPoint(point, `-${damage} HP`, "critical", { y: -40 - (index % 2) * 8 });
            }
            queueSharedWorldUltimateTimeout(() => burn.remove(), 1820, pvp);
          });
          window.__ftScorpioUltimateTrace = {
            stage: "frame-5-burn",
            characterFrames: 6,
            burnFrame: 5,
            affected: affected.length,
            variants,
            preview: Boolean(event.preview_only || event.previewOnly),
            at: Date.now(),
          };
          console.info("[FTG][ScorpioUltimate]", window.__ftScorpioUltimateTrace);
        }, burnDelay, pvp);
        queueSharedWorldUltimateTimeout(() => {
          if (castToken !== sharedWorldScorpioUltimateCastToken) return;
          self.node.classList.remove(...castClasses);
          setSharedWorldFacing(self.node, direction === "left" ? -1 : 1, 0, true);
        }, castDuration + 140, pvp);
      };

      const triggerSharedWorldTrainingEarthquake = (event = {}) => {
        const self = sharedWorldTrainingCombatSelf();
        const affectedRows = Array.isArray(event.affected) ? event.affected : [];
        traceSharedWorldUltimateDamageRuntime("event-received", {
          skillId: clean(event.skill_id || event.skillId || (event.skill && event.skill.id) || ""),
          primaryTargetId: clean(event.primary_slime_id || event.primarySlimeId || event.slime_id || event.slimeId || ""),
          affectedCount: affectedRows.length,
          affected: affectedRows.map((row) => ({
            id: clean(row && (row.slime_id || row.slimeId) || ""),
            damage: Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0)),
            defeated: Boolean(row && (row.slime_defeated || row.slimeDefeated)),
          })),
        });
        if (self && self.node && self.node.classList.contains("is-character-female-default")) {
          triggerSharedWorldTrainingFemaleUltimate(event);
          return;
        }
        if (self && self.node && self.node.classList.contains("is-character-scorpio")) {
          triggerSharedWorldTrainingScorpioUltimate(event);
          return;
        }
        const skillId = clean(event.skill_id || event.skillId || (event.skill && event.skill.id) || "").toLowerCase();
        if (skillId === "male-ultimate") {
          triggerSharedWorldTrainingMaleUltimate(event);
          return;
        }
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return;
        }
        const playerX = Number(event.player_x != null ? event.player_x : event.playerX);
        const playerY = Number(event.player_y != null ? event.player_y : event.playerY);
        const center = Number.isFinite(playerX) && Number.isFinite(playerY)
          ? sharedWorldTrainingPointFromNormalized(playerX, playerY)
          : sharedWorldTrainingSelfPoint();
        const radius = Math.max(120, Math.floor(Number(event.radius_px || event.radiusPx || 400) || 400));
        const quake = document.createElement("span");
        quake.className = "ft-world-training-earthquake";
        quake.style.setProperty("--quake-x", `${center.x}px`);
        quake.style.setProperty("--quake-y", `${center.y}px`);
        quake.style.setProperty("--quake-radius", `${radius}px`);
        const core = document.createElement("span");
        core.className = "ft-world-training-quake-core";
        quake.appendChild(core);
        for (let index = 0; index < 18; index += 1) {
          const crack = document.createElement("span");
          crack.className = "ft-world-training-quake-crack";
          const angle = index * 20 + (index % 3 === 0 ? -8 : (index % 3 === 1 ? 6 : 13));
          const length = Math.max(105, radius * (0.45 + (index % 5) * 0.055));
          crack.style.setProperty("--crack-angle", `${angle}deg`);
          crack.style.setProperty("--crack-length", `${length}px`);
          crack.style.setProperty("--crack-y", `${(index % 2 ? 1 : -1) * (6 + (index % 4) * 3)}px`);
          crack.style.setProperty("--crack-delay", `${index * 22}ms`);
          crack.style.setProperty("--branch-left", `${34 + (index % 4) * 8}%`);
          crack.style.setProperty("--branch-left-b", `${56 + (index % 3) * 7}%`);
          crack.style.setProperty("--branch-length", `${34 + (index % 5) * 8}px`);
          crack.style.setProperty("--branch-length-b", `${28 + (index % 4) * 7}px`);
          crack.style.setProperty("--branch-a", `${(index % 2 ? 1 : -1) * (28 + (index % 3) * 8)}deg`);
          crack.style.setProperty("--branch-b", `${(index % 2 ? -1 : 1) * (32 + (index % 4) * 6)}deg`);
          quake.appendChild(crack);
        }
        for (let index = 0; index < 22; index += 1) {
          const chip = document.createElement("span");
          chip.className = "ft-world-training-quake-chip";
          const angle = index * (360 / 22) + (index % 2 ? 7 : -5);
          chip.style.setProperty("--chip-angle", `${angle}deg`);
          chip.style.setProperty("--chip-distance", `${Math.max(80, radius * (0.28 + (index % 6) * 0.035))}px`);
          chip.style.setProperty("--chip-lift", `${-8 - (index % 5) * 5}px`);
          chip.style.setProperty("--chip-size", `${5 + (index % 4) * 2}px`);
          chip.style.setProperty("--chip-delay", `${80 + index * 18}ms`);
          quake.appendChild(chip);
        }
        effectHost.appendChild(quake);
        const legacySelf = ensureSharedWorldSelfNode();
        if (legacySelf && legacySelf.node) {
          legacySelf.node.classList.add("is-earthquake-cast");
          window.setTimeout(() => legacySelf.node.classList.remove("is-earthquake-cast"), 1120);
        }
        const affected = Array.isArray(event.affected) ? event.affected : [];
        affected.forEach((row, index) => {
          const targetId = clean(row && (row.slime_id || row.slimeId) || "");
          const host = sharedWorldTrainingSlimeHost();
          let target = host && Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === targetId);
          if (!target) {
            target = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row && (row.slime_defeated || row.slimeDefeated)) });
          }
          const damage = Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0));
          traceSharedWorldUltimateDamageRuntime("target-resolved", {
            pipeline: "generic-ultimate",
            targetId,
            targetFound: Boolean(target),
            ghost: Boolean(target && target.classList.contains("is-training-ghost")),
            damage,
          });
          const point = sharedWorldTrainingEventTargetPoint(row, target);
          window.setTimeout(() => {
            if (target) {
              target.classList.add("is-hit");
              animateSharedWorldUltimateDamageTarget(target);
              applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: true, power: 28 });
              window.setTimeout(() => target.classList.remove("is-hit"), 720);
            }
            showSharedWorldTrainingImpactBurst(point, "critical");
            showSharedWorldTrainingDamageFloatAtPoint(point, `-${damage} HP`, "critical", { y: -18 });
            if (row && (row.slime_defeated || row.slimeDefeated)) {
              showSharedWorldTrainingDamageFloatAtPoint(point, "SLIME DOWN", "defeat", { y: -58 });
            }
          }, 280 + index * 70);
        });
        window.setTimeout(() => quake.remove(), 1850);
      };

      // Added 2026-08-11: let admin hung preview either default character and spam visual-only attacks.
      const sharedWorldAdminTrainingTarget = () => {
        const host = sharedWorldTrainingSlimeHost();
        if (!host) {
          return null;
        }
        const selected = typeof worldTrainingSelectedSlime === "function" ? worldTrainingSelectedSlime() : null;
        const selectedId = clean(selected && selected.id || "");
        return Array.from(host.querySelectorAll("[data-slime-id]")).find((node) => clean(node.dataset.slimeId || "") === selectedId)
          || host.querySelector("[data-slime-id]");
      };

      const sharedWorldAdminTrainingPreviewEvent = (target = null) => {
        const slimeId = clean(target && target.dataset && target.dataset.slimeId || "preview-slime");
        const slimeX = sharedWorldClamp((Number(target && target.dataset && target.dataset.slimeX) || 50) / 100, 0.5);
        const slimeY = sharedWorldClamp((Number(target && target.dataset && target.dataset.slimeY) || 50) / 100, 0.5);
        const affected = [{ slime_id: slimeId, slime_x: slimeX, slime_y: slimeY, damage: 0 }];
        return {
          correct: true,
          preview_only: true,
          primary_slime_id: slimeId,
          slime_id: slimeId,
          slime_x: slimeX,
          slime_y: slimeY,
          impact_center_x: slimeX,
          impact_center_y: slimeY,
          affected,
        };
      };

      // Added 2026-08-16: publish the RAM-first character switch without cancelling the current route.
      const syncSharedWorldAdminCharacterPresence = async () => {
        if (!authToken || !worldModal || !worldModal.classList.contains("is-open")) return;
        const position = getSharedWorldSelfPosition();
        const current = {
          x: sharedWorldClamp(position && position.x, 0.5),
          y: sharedWorldClamp(position && position.y, 0.5),
        };
        const destination = {
          x: sharedWorldClamp(position && position.tx, current.x),
          y: sharedWorldClamp(position && position.ty, current.y),
        };
        try {
          const response = await fetchAuthJson("/world/move", {
            method: "POST",
            body: JSON.stringify({
              x: destination.x,
              y: destination.y,
              current_x: current.x,
              current_y: current.y,
              map_mode: sharedWorldMapMode,
              ...activeWorldActorPayload(),
            }),
            timeoutMs: 12000,
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorld(result);
          void refreshSharedWorldBattle();
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not sync the selected character.", "error");
        }
      };

      const setSharedWorldAdminCharacterPreview = (gender = "") => {
        if (!sharedWorldObstacleEditorAllowed()) {
          return;
        }
        sharedWorldAdminCharacterPreview = normalizeSharedWorldCharacterKind(gender);
        try {
          window.localStorage.setItem(SHARED_WORLD_ADMIN_CHARACTER_STORAGE_KEY, sharedWorldAdminCharacterPreview);
        } catch (error) {
          if (error && error.name !== "SecurityError") console.warn("[FTG][ScorpioCharacter] preview save failed", error);
        }
        void syncSharedWorldAdminCharacterPresence();
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (battle && clean(battle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open")) {
          const { self } = sharedWorldBattlePlayersForView(battle);
          renderSharedWorldBattlePlayer(worldBattleLeft, battle, self, "left");
          renderSharedWorldBattleCombatHud(battle, self);
          renderSharedWorldAdminTrainingTestTools();
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        if (self && self.node) {
          const displayName = clean((self.node.querySelector(".ft-world-name-label") || {}).textContent || activeWorldUsername() || currentAuthUsername || "hung");
          renderSharedWorldName(self.node, displayName, sharedWorldAdminCharacterPreview);
        }
        setSharedWorldTrainingBasicSkillsOpen(false);
        renderSharedWorldTrainingQuickSkill();
        renderSharedWorldTrainingBasicSkills();
        renderSharedWorldAdminTrainingTestTools();
      };

      const triggerSharedWorldAdminTrainingAttack = async (ultimate = false) => {
        if (!sharedWorldObstacleEditorAllowed()) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (battle && clean(battle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open")) {
          const battleId = clean(battle.id);
          const sequence = ++sharedWorldAdminBattleTestSequence;
          const queuedAt = performance.now();
          const runAdminBattleTest = async () => {
            const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
            if (!activeBattle || clean(activeBattle.id) !== battleId || clean(activeBattle.status) !== "active") return;
            const startedAt = performance.now();
            const actor = sharedWorldTrainingCombatSelf();
            const castClasses = [
              "is-training-cast",
              "is-training-critical-cast",
              "is-female-ranged-up",
              "is-female-ranged-down",
              "is-female-ranged-left",
              "is-female-ranged-right",
              "is-female-ultimate-cast",
              "is-female-ultimate-left",
              "is-female-ultimate-right",
              "is-male-ultimate-cast",
              "is-male-ultimate-style-5",
              "is-male-ultimate-left",
              "is-male-ultimate-right",
              "is-scorpio-basic-cast",
              "is-scorpio-basic-1",
              "is-scorpio-basic-2",
              "is-scorpio-basic-3",
              "is-scorpio-cast-left",
              "is-scorpio-cast-right",
              "is-scorpio-ultimate-cast",
              "is-scorpio-ultimate-left",
              "is-scorpio-ultimate-right",
              "is-earthquake-cast",
            ];
            const preExistingCastClasses = actor && actor.node
              ? castClasses.filter((className) => actor.node.classList.contains(className))
              : [];
            // Added 2026-08-14: invalidate late atlas callbacks before a queued test cast.
            if (preExistingCastClasses.some((className) => className.startsWith("is-male-ultimate"))) {
              sharedWorldMaleUltimateCastToken += 1;
            }
            if (preExistingCastClasses.some((className) => className.startsWith("is-scorpio-ultimate"))) {
              sharedWorldScorpioUltimateCastToken += 1;
            }
            if (actor && actor.node) {
              actor.node.classList.remove(...castClasses);
            }
            window.__ftPvpAdminTestQueueTrace = {
              sequence,
              battleId,
              attack: ultimate ? "ultimate" : "basic",
              stage: "started",
              queueWaitMs: Math.round(startedAt - queuedAt),
              preExistingCastClasses,
              cleanedCastClasses: preExistingCastClasses.slice(),
              at: Date.now(),
            };
            console.info("[FTG][PvpAdminTestQueue]", window.__ftPvpAdminTestQueueTrace);
            try {
              const response = await fetchAuthJson("/world/battle/admin-test-attack", {
                method: "POST",
                body: JSON.stringify({ battle_id: battleId, attack: ultimate ? "ultimate" : "basic", ...activeWorldActorPayload() }),
                timeoutMs: 20000,
              });
              const result = response && response.payload ? response.payload : response;
              renderSharedWorldBattle(result);
              // Added 2026-08-14: serialize admin previews so repeated Nộ casts cannot leave overlapping atlas ownership.
              // Basic is 1440-1500ms in the shared atlas; leave a cleanup margin
              // so a following Nộ cast cannot overlap its final frame/timer.
              const scorpioCharacter = Boolean(actor && actor.node && actor.node.classList.contains("is-character-scorpio"));
              const scorpioBasic = scorpioCharacter && !ultimate;
              const scorpioUltimate = scorpioCharacter && ultimate;
              const visualGapMs = scorpioBasic ? 3400 : (scorpioUltimate ? 2600 : (ultimate ? 1700 : 1650));
              await new Promise((resolve) => window.setTimeout(resolve, visualGapMs));
              const finishedActor = sharedWorldTrainingCombatSelf();
              if (finishedActor && finishedActor.node) {
                if (finishedActor.node.classList.contains("is-male-ultimate-cast")) {
                  sharedWorldMaleUltimateCastToken += 1;
                }
                if (finishedActor.node.classList.contains("is-scorpio-ultimate-cast")) {
                  sharedWorldScorpioUltimateCastToken += 1;
                }
                finishedActor.node.classList.remove(...castClasses);
              }
              window.__ftPvpAdminTestQueueTrace = {
                sequence,
                battleId,
                attack: ultimate ? "ultimate" : "basic",
                stage: "completed",
                queueWaitMs: Math.round(startedAt - queuedAt),
                runMs: Math.round(performance.now() - startedAt),
                actorStillCasting: Boolean(castClasses.some((className) => sharedWorldTrainingCombatSelf()?.node?.classList.contains(className))),
                visualGapMs,
                at: Date.now(),
              };
              console.info("[FTG][PvpAdminTestQueue]", window.__ftPvpAdminTestQueueTrace);
              setSharedWorldStatus(`Admin ${ultimate ? "Skill Nộ" : "Basic Attack"}: damage persisted, test remains unlimited.`, "ok");
            } catch (error) {
              window.__ftPvpAdminTestQueueTrace = {
                sequence,
                battleId,
                attack: ultimate ? "ultimate" : "basic",
                stage: "failed",
                error: clean(error && error.message),
                at: Date.now(),
              };
              console.info("[FTG][PvpAdminTestQueue]", window.__ftPvpAdminTestQueueTrace);
              setSharedWorldStatus(error && error.message ? error.message : "Admin Battle test attack failed.", "error");
            }
          };
          sharedWorldAdminBattleTestQueue = sharedWorldAdminBattleTestQueue.catch(() => {}).then(runAdminBattleTest);
          return sharedWorldAdminBattleTestQueue;
        }
        if (sharedWorldMapMode !== "training") return;
        const target = sharedWorldAdminTrainingTarget();
        if (!target) {
          setSharedWorldStatus("Choose or wait for a Slime before testing an animation.", "error");
          return;
        }
        const self = sharedWorldTrainingCombatSelf();
        const size = sharedWorldTrainingEffectSize();
        const radiusPx = Math.max(1, Math.min(size.width, size.height) / 2);
        const host = sharedWorldTrainingSlimeHost();
        const slimePositions = host ? Array.from(host.querySelectorAll("[data-slime-id]")).map((node) => ({
          id: clean(node.dataset && node.dataset.slimeId || ""),
          x: sharedWorldClamp((Number(node.dataset && node.dataset.slimeX) || 50) / 100),
          y: sharedWorldClamp((Number(node.dataset && node.dataset.slimeY) || 50) / 100),
        })).filter((row) => row.id) : [];
        const viewportNode = host && host.closest ? (host.closest(".ft-world-stage") || host) : host;
        const viewportRect = viewportNode && viewportNode.getBoundingClientRect ? viewportNode.getBoundingClientRect() : null;
        const visibleEnemyIds = host && viewportRect
          ? Array.from(host.querySelectorAll("[data-slime-id]")).filter((node) => {
              const rect = node.getBoundingClientRect();
              return rect.right >= viewportRect.left && rect.left <= viewportRect.right
                && rect.bottom >= viewportRect.top && rect.top <= viewportRect.bottom;
            }).map((node) => clean(node.dataset && node.dataset.slimeId || "")).filter(Boolean)
          : [];
        const targetId = clean(target.dataset && target.dataset.slimeId || "");
        const skill = self && self.node && self.node.classList.contains("is-character-female-default")
          ? "female-ultimate"
          : (self && self.node && self.node.classList.contains("is-character-scorpio") ? "scorpio-ultimate" : "male-ultimate");
        let result = null;
        let event = {};
        setSharedWorldTrainingBusy(true);
        try {
          const response = await fetchAuthJson("/world/training/admin-test-attack", {
            method: "POST",
            timeoutMs: 20000,
            body: JSON.stringify({
              attack: ultimate ? "ultimate" : "basic",
              skill,
              target_slime_id: targetId,
              radius_x: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.width))),
              radius_y: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.height))),
              radius_px: radiusPx,
              viewport_width: size.width,
              viewport_height: size.height,
              slime_positions: slimePositions,
              visible_enemy_ids: visibleEnemyIds,
            }),
          });
          result = response && response.payload ? response.payload : response;
          event = result && result.training && result.training.event && typeof result.training.event === "object"
            ? { ...result.training.event, preview_only: true, previewOnly: true, affected: Array.isArray(result.training.event.affected) ? [...result.training.event.affected] : [] }
            : {};
          renderSharedWorldTraining(result);
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Admin Training test attack failed.", "error");
        } finally {
          setSharedWorldTrainingBusy(false);
        }
        window.__ftAdminCombatDamageTrace = {
          map: "training",
          attack: ultimate ? "ultimate" : "basic",
          targetId,
          damage: Math.max(0, Number(event.damage || 0) || 0),
          affected: Array.isArray(event.affected) ? event.affected.length : (event.slime_id || event.slimeId ? 1 : 0),
          radiusPx: ultimate ? radiusPx : 0,
          at: Date.now(),
        };
        console.info("[FTG][AdminCombatDamage]", window.__ftAdminCombatDamageTrace);
        if (result) {
          setSharedWorldStatus(`Admin ${ultimate ? "Skill Nộ" : "Basic Attack"}: damage persisted${ultimate ? `, AoE ${Math.round(radiusPx)}px from target` : ""}.`, "ok");
        }
      };

      const showSharedWorldTrainingDamageFloatAtPoint = (point = {}, text = "", tone = "", offset = {}) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !clean(text)) {
          if (/^-\d+\s*HP$/i.test(clean(text))) {
            traceSharedWorldUltimateDamageRuntime("damage-float-skipped", {
              text: clean(text),
              tone: clean(tone),
              reason: !effectHost ? "missing-effect-host" : "empty-text",
            });
          }
          return null;
        }
        const x = Math.max(0, Number(point.x || 0) + Number(offset.x || 0));
        const y = Math.max(0, Number(point.y || 0) + Number(offset.y || 0));
        const damage = document.createElement("span");
        damage.className = `ft-world-training-damage-float ${tone ? `is-${tone}` : ""}`;
        damage.style.setProperty("--damage-x", `${x}px`);
        damage.style.setProperty("--damage-y", `${y}px`);
        damage.textContent = text;
        effectHost.appendChild(damage);
        if (/^-\d+\s*HP$/i.test(clean(text)) && tone === "critical") {
          traceSharedWorldUltimateDamageRuntime("damage-float-mounted", {
            text: clean(text),
            tone: clean(tone),
            x: Math.round(x),
            y: Math.round(y),
            hostId: clean(effectHost.id || ""),
            connected: damage.isConnected,
            blockCount: effectHost.querySelectorAll(".ft-world-training-damage-float").length,
          });
        }
        window.setTimeout(() => damage.remove(), tone === "defeat" ? 1650 : (tone === "critical" ? 1580 : 1300));
        return damage;
      };

      const showSharedWorldTrainingDamageFloat = (node, text = "", tone = "", offset = {}) => {
        if (!node || !clean(text)) {
          return;
        }
        const point = sharedWorldTrainingNodePoint(node, tone === "player" ? 0.38 : 0.32);
        showSharedWorldTrainingDamageFloatAtPoint(point, text, tone, offset);
      };

      const showSharedWorldTrainingImpactBurst = (point = {}, tone = "") => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return;
        }
        const burst = document.createElement("span");
        burst.className = `ft-world-training-impact-burst ${tone ? `is-${tone}` : ""}`;
        burst.style.setProperty("--impact-x", `${Math.max(0, Number(point.x || 0))}px`);
        burst.style.setProperty("--impact-y", `${Math.max(0, Number(point.y || 0))}px`);
        effectHost.appendChild(burst);
        window.setTimeout(() => burst.remove(), tone === "critical" ? 1160 : 920);
      };

      const sharedWorldTrainingCrystalItemTone = (item = {}) => {
        const id = clean(item && (item.id || item.item_id || item.itemId) || "").toLowerCase();
        if (id === "space_q_spellbook_gold" || id === "leaderboard_space_q_crystal") return "bookgold";
        if (id === "space_q_spellbook_silver") return "booksilver";
        if (id === "space_p_bow_gold" || id === "paragraph_crystal_golden") return "bowgold";
        if (id === "space_p_bow_silver") return "bowsilver";
        if (id === "space_s_sax_gold") return "saxgold";
        if (id === "space_s_sax_silver") return "saxsilver";
        if (id === "space_l_sword_gold") return "swordgold";
        if (id === "space_l_sword_silver") return "swordsilver";
        if (/gold|yellow/.test(id)) return "golden";
        if (/blue/.test(id)) return "blue";
        if (/green/.test(id)) return "green";
        if (/paragraph|purple|prism|crystal$/.test(id)) return "purple";
        return "";
      };

      const showSharedWorldTrainingCorpse = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return null;
        }
        const point = sharedWorldTrainingEventTargetPoint(event, target);
        const question = clean(event.question_prompt || event.questionPrompt || "");
        const expected = clean(event.expected_answer || event.expectedAnswer || event.answer || "");
        const userAnswer = clean(event.user_answer || event.userAnswer || "");
        const userAnswerHtml = sharedWorldTrainingAnswerTokenHtml(userAnswer, expected);
        const corpse = document.createElement("span");
        corpse.className = "ft-world-training-corpse";
        corpse.style.setProperty("--corpse-x", `${point.x}px`);
        corpse.style.setProperty("--corpse-y", `${point.y}px`);
        corpse.innerHTML = `
          <span class="ft-world-training-corpse-card">
            ${question ? `<b>Question</b><span>${escapeHtml(question)}</span>` : ""}
            <b>Correct answer</b>
            <span>${escapeHtml(expected || "Answer cleared")}</span>
            <b>Your answer</b>
            <span class="is-user">${userAnswerHtml}</span>
          </span>
          <span class="ft-world-training-corpse-core" aria-hidden="true"></span>
        `;
        effectHost.appendChild(corpse);
        window.setTimeout(() => corpse.remove(), 10200);
        return corpse;
      };

      const appendSharedWorldTrainingHistory = (event = {}) => {
        if (!worldTrainingHistoryList) {
          return;
        }
        const defeated = Boolean(event.slime_defeated || event.slimeDefeated);
        const type = clean(event.type || "").toLowerCase();
        const hurt = type === "hurt" || event.correct === false;
        const slimeName = clean(event.slime_name || event.slimeName || "Slime");
        const question = clean(event.question_prompt || event.questionPrompt || "");
        const expected = clean(event.expected_answer || event.expectedAnswer || event.answer || "");
        const userAnswer = clean(event.user_answer || event.userAnswer || "");
        const damage = Math.max(0, Math.floor(Number(event.damage || 0) || 0));
        const healAmount = Math.max(0, Math.floor(Number(event.heal_amount || event.healAmount || 0) || 0));
        const userAnswerHtml = sharedWorldTrainingAnswerTokenHtml(userAnswer, expected);
        const title = defeated ? `${slimeName} defeated` : hurt ? `${slimeName} countered` : `${slimeName} hit`;
        if (worldTrainingHistoryTitle) {
          worldTrainingHistoryTitle.textContent = `${title}${damage ? (hurt ? ` - ${damage} HP lost` : ` - ${damage} damage`) : ""}${healAmount ? ` | +${healAmount} HP` : ""}`;
        }
        if (worldTrainingHistory) {
          worldTrainingHistory.setAttribute("aria-hidden", "false");
        }
        if (typeof scheduleSharedWorldTrainingHistoryHide === "function") {
          scheduleSharedWorldTrainingHistoryHide();
        }
        worldTrainingHistoryList.innerHTML = "";
        const article = document.createElement("article");
        article.innerHTML = `
          <b>${escapeHtml(title)}</b>
          ${question ? `<span>${escapeHtml(question)}</span>` : ""}
          ${expected ? `<b>Correct answer</b><span class="is-correct">${escapeHtml(expected)}</span>` : ""}
          <b>Your answer</b><span class="is-user">${userAnswerHtml}</span>
          ${healAmount ? `<b>Critical recovery</b><span class="is-correct">${escapeHtml(`+${healAmount} HP`)}</span>` : ""}
          ${hurt && damage ? `<b>Counter</b><span>${escapeHtml(`-${damage} HP`)}</span>` : ""}
        `;
        worldTrainingHistoryList.prepend(article);
      };

      const stopSharedWorldTrainingLootWatch = () => {
        if (sharedWorldTrainingLootTimer) {
          window.clearInterval(sharedWorldTrainingLootTimer);
          sharedWorldTrainingLootTimer = 0;
        }
      };

      const collectSharedWorldTrainingLoot = (dropKey = "", reason = "auto") => {
        const record = sharedWorldTrainingLootDrops.get(dropKey);
        if (!record || record.collecting) {
          return false;
        }
        record.collecting = true;
        const node = record.node;
        const target = sharedWorldTrainingSelfPoint();
        if (node) {
          node.classList.add("is-collecting");
          node.style.setProperty("--loot-target-x", `${target.x}px`);
          node.style.setProperty("--loot-target-y", `${target.y}px`);
        }
        const item = record.item && typeof record.item === "object" ? record.item : { id: "crystal", name: canonicalRewardName("crystal", "Reward Item") };
        window.setTimeout(() => {
          try {
            awardInventoryItemOnce(record.eventKey, item, node || null, {
              tone: item.id || "crystal",
              feedback: () => setSharedWorldStatus(`Item collected${reason === "near" ? " nearby" : ""}: ${clean(canonicalRewardName(item.id, item.name))}`, "ok"),
            });
          } catch (error) {
            setSharedWorldStatus("Item collected, inventory sync will retry soon.", "ok");
          }
          if (node && node.parentNode) {
            node.parentNode.removeChild(node);
          }
          sharedWorldTrainingLootDrops.delete(dropKey);
          if (!sharedWorldTrainingLootDrops.size) {
            stopSharedWorldTrainingLootWatch();
          }
        }, 700);
        return true;
      };

      const startSharedWorldTrainingLootWatch = () => {
        if (sharedWorldTrainingLootTimer) {
          return;
        }
        sharedWorldTrainingLootTimer = window.setInterval(() => {
          if (!sharedWorldTrainingLootDrops.size || sharedWorldMapMode !== "training") {
            stopSharedWorldTrainingLootWatch();
            return;
          }
          const selfPoint = sharedWorldTrainingSelfPoint();
          sharedWorldTrainingLootDrops.forEach((record, key) => {
            if (!record || record.collecting) return;
            if (Math.hypot((record.x || 0) - selfPoint.x, (record.y || 0) - selfPoint.y) <= 20) {
              collectSharedWorldTrainingLoot(key, "near");
            }
          });
        }, 260);
      };

      const spawnSharedWorldTrainingLootDrops = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        const drops = Array.isArray(event.crystal_drops) ? event.crystal_drops : (Array.isArray(event.crystalDrops) ? event.crystalDrops : []);
        if (!effectHost || !drops.length) {
          return;
        }
        const base = sharedWorldTrainingEventTargetPoint(event, target);
        drops.slice(0, 3).forEach((drop, index) => {
          const row = drop && typeof drop === "object" ? drop : {};
          const item = row.item && typeof row.item === "object" ? row.item : row;
          const dropKey = clean(row.id || `${event.event_id || event.eventId || Date.now()}_${index}`);
          const eventKey = `qm-city-training-loot:${dropKey}:${clean(item.id || "crystal")}`;
          if (!dropKey || sharedWorldTrainingLootDrops.has(dropKey)) {
            return;
          }
          const angle = (-80 + index * 80 + Math.random() * 28) * Math.PI / 180;
          const radius = 34 + Math.random() * 24;
          const x = Math.max(10, base.x + Math.cos(angle) * radius);
          const y = Math.max(10, base.y + Math.sin(angle) * radius + 16);
          const node = document.createElement("span");
          const tone = sharedWorldTrainingCrystalItemTone(item);
          node.className = `ft-world-training-loot ${tone ? `is-${tone}` : ""}`;
          node.style.setProperty("--loot-x", `${x}px`);
          node.style.setProperty("--loot-y", `${y}px`);
          node.title = clean(canonicalRewardName(item.id, item.name));
          effectHost.appendChild(node);
          sharedWorldTrainingLootDrops.set(dropKey, { node, item, eventKey, x, y, collecting: false });
          window.setTimeout(() => collectSharedWorldTrainingLoot(dropKey, "auto"), 10000);
        });
        startSharedWorldTrainingLootWatch();
      };

      const triggerSharedWorldTrainingCounterLeap = (event = {}, slimeNode = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !slimeNode) {
          return;
        }
        const start = sharedWorldTrainingEventTargetPoint(event, slimeNode);
        const end = sharedWorldTrainingSelfPoint();
        const leap = document.createElement("span");
        leap.className = "ft-world-training-counter-leap";
        leap.style.setProperty("--leap-start-x", `${start.x - 36}px`);
        leap.style.setProperty("--leap-start-y", `${start.y - 31}px`);
        leap.style.setProperty("--leap-end-x", `${end.x - 36}px`);
        leap.style.setProperty("--leap-end-y", `${end.y - 31}px`);
        leap.style.setProperty("--leap-mid-x", `${(start.x + end.x) / 2 - 36}px`);
        leap.style.setProperty("--leap-mid-y", `${(start.y + end.y) / 2 - 92}px`);
        effectHost.appendChild(leap);
        showSharedWorldTrainingImpactBurst(end, "player");
        showSharedWorldTrainingDamageFloatAtPoint(end, `-${Math.max(0, Math.floor(Number(event.damage || 0) || 0))} HP`, "player", { y: -28 });
        const slimeManaGain = Math.max(0, Math.floor(Number(event.slime_mana_gain || event.slimeManaGain || 0) || 0));
        if (slimeManaGain) {
          showSharedWorldTrainingDamageFloatAtPoint(start, `+${slimeManaGain} MP`, "mana", { y: -40 });
        }
        window.setTimeout(() => leap.remove(), 1120);
      };

      const triggerSharedWorldTrainingSlimeSpit = (event = {}, slimeNode = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !slimeNode) {
          return;
        }
        const start = sharedWorldTrainingEventTargetPoint(event, slimeNode);
        const end = sharedWorldTrainingSelfPoint();
        const spit = document.createElement("span");
        spit.className = "ft-world-training-slime-spit";
        spit.style.setProperty("--spit-start-x", `${start.x - 19}px`);
        spit.style.setProperty("--spit-start-y", `${start.y - 16}px`);
        spit.style.setProperty("--spit-end-x", `${end.x - 19}px`);
        spit.style.setProperty("--spit-end-y", `${end.y - 16}px`);
        effectHost.appendChild(spit);
        const damage = Math.max(0, Math.floor(Number(event.damage || 0) || 0));
        window.setTimeout(() => {
          showSharedWorldTrainingImpactBurst(end, "player");
          showSharedWorldTrainingDamageFloatAtPoint(end, `-${damage} HP`, "player", { y: -28 });
        }, 650);
        const slimeManaGain = Math.max(0, Math.floor(Number(event.slime_mana_gain || event.slimeManaGain || 0) || 0));
        if (slimeManaGain) {
          showSharedWorldTrainingDamageFloatAtPoint(start, `+${slimeManaGain} MP`, "mana", { y: -40 });
        }
        window.setTimeout(() => spit.remove(), 940);
      };

      const flashSharedWorldTrainingEvent = (event = {}) => {
        const row = event && typeof event === "object" ? event : {};
        const clientActionId = clean(row.client_action_id || row.clientActionId || "");
        const optimisticRecord = clientActionId ? sharedWorldTrainingOptimisticActions.get(clientActionId) : null;
        if (optimisticRecord && !row.client_preview) {
          sharedWorldTrainingOptimisticActions.delete(clientActionId);
        }
        const eventId = clean(row.event_id || row.eventId || row.id || "");
        const eventKey = eventId || `${clean(row.type)}:${clean(row.slime_id || row.slimeId)}:${clean(row.damage)}:${clean(row.answer)}:${clean(row.slime_hp || row.slimeHp)}:${row.critical ? "critical" : "normal"}`;
        const host = sharedWorldTrainingSlimeHost();
        if (!host || !clean(row.type) || sharedWorldTrainingLastEventKey === eventKey) {
          return;
        }
        if (clean(row.type).toLowerCase() === "select") {
          sharedWorldTrainingLastEventKey = eventKey;
          return;
        }
        if (clean(row.type).toLowerCase() === "skill") {
          sharedWorldTrainingLastEventKey = eventKey;
          playEffectSound("true");
          triggerSharedWorldTrainingEarthquake(row);
          return;
        }
        sharedWorldTrainingLastEventKey = eventKey;
        const targetId = clean(row.slime_id || row.slimeId || "");
        let target = Array.from(host.querySelectorAll("[data-slime-id]"))
          .find((node) => clean(node.dataset.slimeId || "") === targetId);
        if (!target && row.correct) {
          target = createSharedWorldTrainingGhostSlime(row);
        } else if (!target && clean(row.type) === "hurt") {
          target = createSharedWorldTrainingGhostSlime(row, { defeated: false });
        }
        if (target) {
          target.classList.remove("is-hit", "is-hurt");
          void target.offsetWidth;
          if (row.client_preview) {
            if (row.correct) {
              playEffectSound("true");
              triggerSharedWorldTrainingSkill(row, target, () => {
                const previewPoint = target && target.isConnected
                  ? sharedWorldTrainingNodePoint(target, 0.34)
                  : sharedWorldTrainingEventTargetPoint(row, target);
                const previewDamagePoint = sharedWorldTrainingSlimeDamagePoint(target, previewPoint);
                const previewDamage = Math.max(0, Math.floor(Number(row.damage || 0) || 0));
                const optimisticPreview = clientActionId ? sharedWorldTrainingOptimisticActions.get(clientActionId) : null;
                const commitPreview = () => {
                  if (optimisticPreview) optimisticPreview.visualCommitted = true;
                  target.classList.remove("is-hit");
                  void target.offsetWidth;
                  target.classList.add("is-hit");
                  applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: false });
                  showSharedWorldTrainingImpactBurst(previewPoint, "");
                  showSharedWorldTrainingDamageFloatAtPoint(previewDamagePoint, `-${previewDamage} HP`, "", { y: -8 });
                  window.setTimeout(() => target.classList.remove("is-hit"), 720);
                };
                const previewSelf = sharedWorldTrainingCombatSelf();
                const malePreview = Boolean(previewSelf && previewSelf.node && previewSelf.node.classList.contains("is-character-male-default"));
                if (malePreview) {
                  showSharedWorldMaleBasicEnemyExplosion(previewPoint, previewSelf.node, () => {
                    commitPreview();
                    flushSharedWorldTrainingImpactRender();
                  });
                  return "defer-render";
                }
                commitPreview();
              });
            } else {
              playEffectSound("false");
              triggerSharedWorldTrainingSlimeSpit(row, target);
            }
            return;
          }
          if (row.correct) {
            if (!optimisticRecord) playEffectSound("true");
            const damage = Math.max(0, Math.floor(Number(row.damage || 0) || 0));
            const critical = Boolean(row.critical || row.criticalHit);
            const earned = Math.max(0, Math.floor(Number(row.earned_words || row.earnedWords || row.exp || 0) || 0));
            const manaGain = Math.max(0, Math.floor(Number(row.mana_gain || row.manaGain || 0) || 0));
            const healAmount = Math.max(0, Math.floor(Number(row.heal_amount || row.healAmount || 0) || 0));
            const targetPoint = sharedWorldTrainingEventTargetPoint(row, target);
            const playerHudPoint = sharedWorldTrainingPlayerHudPoint();
            const answerLabel = clean(row.expected_answer || row.expectedAnswer || row.read_text || row.readText || row.answer || sharedWorldTrainingSpeech.expectedText || "");
            if (answerLabel) {
              showSharedWorldTrainingDamageFloatAtPoint(playerHudPoint, answerLabel.length > 72 ? `${answerLabel.slice(0, 69)}...` : answerLabel, "answer", { y: -76 });
            }
            appendSharedWorldTrainingHistory(row);
            const showHitFeedback = () => {
              const impactPoint = target && target.isConnected
                ? sharedWorldTrainingNodePoint(target, 0.34)
                : targetPoint;
              const damagePoint = sharedWorldTrainingSlimeDamagePoint(target, impactPoint);
              let committed = false;
              const commitDamage = () => {
                if (committed) return;
                committed = true;
                target.classList.remove("is-hit");
                void target.offsetWidth;
                target.classList.add("is-hit");
                applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: critical });
                showSharedWorldTrainingImpactBurst(impactPoint, critical ? "critical" : "");
                if (critical) {
                  showSharedWorldTrainingDamageFloatAtPoint(playerHudPoint, "CRITICAL x2", "critical", { y: -46 });
                }
                showSharedWorldTrainingDamageFloatAtPoint(damagePoint, `-${damage} HP`, critical ? "critical" : "", { y: critical ? -16 : -8 });
                if (manaGain) {
                  showSharedWorldTrainingDamageFloatAtPoint(playerHudPoint, `+${manaGain} MP`, "mana", { x: -48, y: -18 });
                }
                if (healAmount) {
                  showSharedWorldTrainingDamageFloatAtPoint(playerHudPoint, `+${healAmount} HP`, "heal", { x: 48, y: -18 });
                }
                if (earned) {
                  showSharedWorldTrainingDamageFloatAtPoint(playerHudPoint, `+${earned} EXP`, "exp", { y: healAmount || manaGain ? -46 : -28 });
                }
                if (row.slime_defeated || row.slimeDefeated || clean(row.type) === "clear") {
                  showSharedWorldTrainingDamageFloatAtPoint(damagePoint, "SLIME DOWN", "defeat", { y: -48 });
                  showSharedWorldTrainingCorpse(row, target);
                  spawnSharedWorldTrainingLootDrops(row, target);
                }
                window.setTimeout(() => target.classList.remove("is-hit"), 720);
              };
              const selfForExplosion = sharedWorldTrainingCombatSelf();
              const maleBasic = Boolean(selfForExplosion && selfForExplosion.node && selfForExplosion.node.classList.contains("is-character-male-default"));
              if (maleBasic) {
                showSharedWorldMaleBasicEnemyExplosion(impactPoint, null, () => {
                  commitDamage();
                  flushSharedWorldTrainingImpactRender();
                });
                return "defer-render";
              }
              commitDamage();
            };
            if (optimisticRecord) {
              if (!optimisticRecord.visualCommitted) showHitFeedback();
            }
            else triggerSharedWorldTrainingSkill(row, target, showHitFeedback);
          } else {
            if (!optimisticRecord) playEffectSound("false");
            appendSharedWorldTrainingHistory(row);
            if (!optimisticRecord) triggerSharedWorldTrainingSlimeSpit(row, target);
          }
          if (!row.correct) {
            target.classList.add("is-hurt");
            window.setTimeout(() => target.classList.remove("is-hurt"), 720);
          }
        }
      };

      // Added 2026-08-13: male default Basic Skill impact uses the eight source PNG frames.
      const showSharedWorldMaleBasicEnemyExplosion = (point = {}, sourceNode = null, onDamageFrame = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        const self = sharedWorldTrainingCombatSelf();
        const fallbackMale = typeof document !== "undefined"
          ? document.querySelector('.ft-world-player.is-self.is-character-male-default, .ft-world-player.is-character-male-default[data-username]')
          : null;
        const actorNode = sourceNode || (self && self.node ? self.node : fallbackMale);
        const eligible = Boolean(actorNode && actorNode.classList.contains("is-character-male-default"));
        window.__ftMaleBasicEnemyExplosionTrace = {
          mounted: Boolean(effectHost && eligible),
          effectHost: Boolean(effectHost),
          maleDefault: eligible,
          actorClass: actorNode ? actorNode.className : "",
          map: sharedWorldTrainingCombatOverride && sharedWorldTrainingCombatOverride.mode === "pvp" ? "battle-pvp" : "training",
          x: Math.round(Number(point.x || 0)),
          y: Math.round(Number(point.y || 0)),
          at: Date.now(),
        };
        console.info("[FTG][MaleBasicEnemyExplosion]", JSON.stringify(window.__ftMaleBasicEnemyExplosionTrace));
        if (!effectHost || !eligible) {
          if (typeof onDamageFrame === "function") onDamageFrame();
          return;
        }
        const impact = document.createElement("span");
        impact.className = "ft-world-training-male-basic-enemy-explosion";
        const hostRect = effectHost.getBoundingClientRect();
        const viewportX = hostRect.left + Number(point.x || 0);
        const viewportY = hostRect.top + Number(point.y || 0);
        impact.style.position = "fixed";
        impact.style.left = `${viewportX}px`;
        impact.style.top = `${viewportY}px`;
        impact.style.zIndex = "2147480000";
        impact.style.setProperty("--impact-x", "0px");
        impact.style.setProperty("--impact-y", "0px");
        impact.style.backgroundImage = "none";
        impact.style.width = "276px";
        impact.style.height = "276px";
        impact.style.transform = "translate(-50%, -56%) scale(.72)";
        document.body.appendChild(impact);
        const frames = Array.from({ length: 8 }, (_unused, index) => `/future-assets/character_male_default_enemy_explosion_${index + 1}.png`);
        const frameNodes = frames.map((src, index) => {
          const node = document.createElement("img");
          node.alt = "";
          node.draggable = false;
          node.width = 720;
          node.height = 720;
          node.style.position = "absolute";
          node.style.inset = "0";
          node.style.width = "100%";
          node.style.height = "100%";
          node.style.objectFit = "contain";
          node.style.display = "block";
          node.style.opacity = index === 0 ? "1" : "0";
          node.style.transition = "none";
          node.src = sharedWorldCharacterAssetState.objectUrls.get(src) || src;
          impact.appendChild(node);
          return node;
        });
        let frameIndex = 0;
        const frameTimer = window.setInterval(() => {
          frameIndex += 1;
          if (frameIndex >= frames.length) {
            window.clearInterval(frameTimer);
            impact.remove();
            return;
          }
          frameNodes.forEach((node, index) => { node.style.opacity = index === frameIndex ? "1" : "0"; });
          impact.style.transform = `translate(-50%, -56%) scale(${(0.72 + frameIndex * 0.055).toFixed(3)})`;
          if (frameIndex === 4 && typeof onDamageFrame === "function") {
            window.__ftMaleBasicEnemyExplosionTrace.damageFrame = 5;
            window.__ftMaleBasicEnemyExplosionTrace.damageCommittedAt = Date.now();
            console.info("[FTG][MaleBasicEnemyExplosionDamageFrame]", JSON.stringify(window.__ftMaleBasicEnemyExplosionTrace));
            onDamageFrame();
          }
        }, 94);
        window.__ftMaleBasicEnemyExplosionTrace.frameCount = 8;
        window.__ftMaleBasicEnemyExplosionTrace.domNode = impact.isConnected;
        window.__ftMaleBasicEnemyExplosionTrace.frameSrc = frameNodes[0].src;
        window.__ftMaleBasicEnemyExplosionTrace.frameNodes = frameNodes.length;
        window.__ftMaleBasicEnemyExplosionTrace.viewportX = Math.round(viewportX);
        window.__ftMaleBasicEnemyExplosionTrace.viewportY = Math.round(viewportY);
        window.__ftMaleBasicEnemyExplosionTrace.parent = "body";
        window.__ftMaleBasicEnemyExplosionTrace.zIndex = impact.style.zIndex;
        console.info("[FTG][MaleBasicEnemyExplosionDOM]", JSON.stringify(window.__ftMaleBasicEnemyExplosionTrace));
      };

      // Added 2026-08-11: split a combined prompt so the instruction and question content can be styled independently.
      const sharedWorldTrainingQuestionParts = (question = {}, fallback = "") => {
        const prompt = clean(question.prompt || fallback);
        const explicitContent = clean(question.content || question.question_text || question.questionText || question.cue || question.source_text || question.sourceText || "");
        if (explicitContent && explicitContent !== prompt) {
          const promptLower = prompt.toLocaleLowerCase();
          const contentLower = explicitContent.toLocaleLowerCase();
          const suffixAt = promptLower.endsWith(contentLower) ? prompt.length - explicitContent.length : -1;
          const instruction = suffixAt >= 0
            ? clean(prompt.slice(0, suffixAt).replace(/[:：\-–—]\s*$/, ""))
            : prompt;
          return { instruction: instruction || clean(fallback), content: explicitContent };
        }
        const separator = prompt.search(/[:：]/);
        if (separator >= 0 && clean(prompt.slice(separator + 1))) {
          return {
            instruction: clean(prompt.slice(0, separator + 1)),
            content: clean(prompt.slice(separator + 1)),
          };
        }
        return { instruction: prompt, content: "" };
      };

      // Added 2026-08-12: safely highlights the exact Grammar target without trusting server-authored HTML.
      const sharedWorldTrainingQuestionContentHtml = (question = {}, content = "") => {
        const text = clean(content);
        const kind = clean(question.training_kind || question.trainingKind || question.kind || "").toLowerCase();
        const target = clean(question.target_word || question.targetWord || "");
        if (kind !== "space_grammar_pos_choice" || !text || !target) return escapeHtml(text);
        let start = Number(question.target_start ?? question.targetStart);
        let end = Number(question.target_end ?? question.targetEnd);
        const validRange = Number.isInteger(start) && Number.isInteger(end) && start >= 0 && end > start
          && end <= text.length && text.slice(start, end).toLocaleLowerCase() === target.toLocaleLowerCase();
        if (!validRange) {
          start = text.toLocaleLowerCase().indexOf(target.toLocaleLowerCase());
          end = start >= 0 ? start + target.length : -1;
        }
        if (start < 0 || end <= start) return escapeHtml(text);
        return `${escapeHtml(text.slice(0, start))}<mark class="ft-world-training-question-target">${escapeHtml(text.slice(start, end))}</mark>${escapeHtml(text.slice(end))}`;
      };

      // Added 2026-08-11: renders the shared three-choice combat control used by Training and PvP.
      const renderSharedWorldCombatChoices = (host = null, form = null, question = {}, enabled = true) => {
        if (!host || !form) return false;
        const choices = Array.isArray(question.choices) ? question.choices.slice(0, 3) : [];
        const active = choices.length === 3;
        form.classList.toggle("is-choice-mode", active);
        host.hidden = !active;
        if (!active) {
          host.replaceChildren();
          host.dataset.combatChoiceSignature = "";
          host.dataset.combatChoiceLocked = "0";
          return false;
        }
        const normalized = choices.map((choice) => {
          const row = choice && typeof choice === "object" ? choice : { label: clean(choice), value: clean(choice) };
          return { label: clean(row.label || row.value || ""), value: clean(row.value || row.label || "") };
        });
        const signature = JSON.stringify({
          id: clean(question.id || question.question_id || question.questionId || question.created_at || ""),
          prompt: clean(question.prompt || question.question || question.text || question.request || question.instruction || ""),
          kind: clean(question.training_kind || question.trainingKind || question.kind || question.type || ""),
          choices: normalized,
        });
        const existing = host.querySelectorAll("[data-combat-choice]");
        if (host.dataset.combatChoiceSignature === signature && existing.length === normalized.length) {
          if (host.dataset.combatChoiceLocked !== "1") {
            existing.forEach((button) => {
              button.disabled = !enabled || !clean(button.dataset.combatChoice);
            });
          }
          return true;
        }
        host.replaceChildren();
        host.dataset.combatChoiceSignature = signature;
        host.dataset.combatChoiceLocked = "0";
        normalized.forEach((row, index) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "ft-world-combat-choice";
          button.dataset.combatChoice = clean(row.value || row.label || "");
          button.dataset.combatChoiceIndex = String(index);
          button.disabled = !enabled || !button.dataset.combatChoice;
          button.innerHTML = `<strong>${escapeHtml(clean(row.label || row.value || ""))}</strong>`;
          host.appendChild(button);
        });
        return true;
      };

      const previewSharedWorldCombatChoice = (host = null, selectedAnswer = "", correct = false) => {
        if (!host) return;
        host.dataset.combatChoiceLocked = "1";
        host.querySelectorAll("[data-combat-choice]").forEach((button) => {
          const selected = clean(button.dataset.combatChoice) === clean(selectedAnswer);
          button.disabled = true;
          button.classList.toggle("is-correct-preview", selected && correct);
          button.classList.toggle("is-wrong-preview", selected && !correct);
        });
      };

      // Added 2026-08-11: Training and PvP render every Basic Skill question through one panel contract.
      const renderSharedWorldTrainingQuestionPanel = (questionRoot, question = {}, options = {}) => {
        if (!questionRoot) return { speech: false, serverSpeech: false, audio: false, translate: false, browserSpeech: false };
        const selected = options.selected !== false;
        const targetId = clean(options.targetId || "");
        const context = clean(options.context || "training") || "training";
        const isChoiceQuestion = selected && Array.isArray(question.choices) && question.choices.length === 3;
        const isSpeechQuestion = selected && !isChoiceQuestion && sharedWorldTrainingQuestionIsSpeech(question);
        const isServerSpeechQuestion = selected && !isChoiceQuestion && sharedWorldTrainingQuestionIsServerSpeech(question);
        const isAudioQuestion = selected && !isChoiceQuestion && sharedWorldTrainingQuestionIsAudioInput(question);
        const isTranslateQuestion = selected && !isChoiceQuestion && sharedWorldTrainingQuestionIsTranslateVi(question);
        const browserSpeechQuestion = selected && !isChoiceQuestion && sharedWorldTrainingUsesBrowserSpeechInput(question);
        questionRoot.classList.toggle("is-speech-question", isSpeechQuestion);
        questionRoot.classList.toggle("is-server-speech-question", isServerSpeechQuestion);
        questionRoot.classList.toggle("is-audio-question", isAudioQuestion);
        if (!selected) {
          questionRoot.textContent = clean(options.emptyText || "Choose a target to start training.");
        } else if (isChoiceQuestion) {
          const promptParts = sharedWorldTrainingQuestionParts(question, clean(options.fallbackText || "Choose the correct answer."));
          questionRoot.innerHTML = `
            <span class="ft-world-training-question-instruction">${escapeHtml(promptParts.instruction)}</span>
            ${promptParts.content ? `<span class="ft-world-training-question-content">${sharedWorldTrainingQuestionContentHtml(question, promptParts.content)}</span>` : ""}
          `;
        } else if (isSpeechQuestion) {
          const readText = sharedWorldTrainingSpeechText(question);
          const ipa = clean(question.ipa || question.ipa_uk || question.ipaUk || question.ipa_us || question.ipaUs || "");
          const hideReadText = sharedWorldTrainingQuestionIsViPromptSpeech(question);
          const promptText = clean(question.prompt || (hideReadText ? "Speak the English answer from the Vietnamese cue." : "Read this aloud."));
          const cueText = clean(question.meaning || question.translation || question.vietnamese || "");
          const promptLabel = hideReadText ? "Speak the English answer from this Vietnamese cue." : promptText;
          const primaryReadText = hideReadText ? (cueText || promptText) : readText;
          questionRoot.innerHTML = `
            <span class="ft-world-training-read-card${hideReadText ? " is-vi-cue" : ""}">
              <span class="ft-world-training-question-instruction">${escapeHtml(promptLabel)}</span>
              ${primaryReadText ? `<span class="ft-world-training-read-text">${escapeHtml(primaryReadText)}</span>` : ""}
              ${ipa && !hideReadText ? `<span class="ft-world-training-read-ipa">${escapeHtml(ipa)}</span>` : ""}
              <span class="ft-world-training-read-status" data-training-read-status></span>
            </span>
          `;
          if (context === "training") renderSharedWorldTrainingSpeechStatus(question, targetId, questionRoot);
          else renderSharedWorldTrainingMicOnlyStatus(questionRoot.querySelector("[data-training-read-status]"), false);
        } else if (isServerSpeechQuestion) {
          const promptParts = sharedWorldTrainingQuestionParts(question, "Speak the Vietnamese translation for this English sentence.");
          questionRoot.innerHTML = `
            <span class="ft-world-training-read-card is-vi-cue is-server-speech">
              <span class="ft-world-training-question-instruction">${escapeHtml(promptParts.instruction)}</span>
              <span class="ft-world-training-read-text">${escapeHtml(promptParts.content || "English sentence is loading.")}</span>
              <span class="ft-world-training-read-status" data-training-server-speech-status></span>
            </span>
          `;
          if (context === "training") renderSharedWorldTrainingServerSpeechStatus(question, targetId, questionRoot);
          else renderSharedWorldTrainingMicOnlyStatus(questionRoot.querySelector("[data-training-server-speech-status]"), false);
        } else if (isTranslateQuestion) {
          const promptParts = sharedWorldTrainingQuestionParts(question, "Translate this sentence to Vietnamese.");
          questionRoot.innerHTML = `
            <span class="ft-world-training-read-card is-vi-cue is-translate-vi">
              <span class="ft-world-training-question-instruction">${escapeHtml(promptParts.instruction)}</span>
              ${promptParts.content ? `<span class="ft-world-training-read-text">${escapeHtml(promptParts.content)}</span>` : ""}
              <span class="ft-world-training-read-status" data-training-server-speech-status></span>
            </span>
          `;
          if (context === "training") renderSharedWorldTrainingServerSpeechStatus(question, targetId, questionRoot);
          else renderSharedWorldTrainingMicOnlyStatus(questionRoot.querySelector("[data-training-server-speech-status]"), false);
        } else if (isAudioQuestion) {
          questionRoot.innerHTML = `
            <span class="ft-world-training-audio-card">
              <span class="ft-world-training-audio-orb" aria-hidden="true"></span>
              <span class="ft-world-training-audio-copy">
                <b>${escapeHtml(clean(question.prompt || "Listen and type the English answer."))}</b>
                <small>${escapeHtml(clean(question.type || "Audio dictation"))}</small>
              </span>
              <button class="ft-world-training-audio-play" type="button" data-training-audio-play aria-label="Replay audio">Play</button>
            </span>
          `;
          if (options.autoPlayAudio) maybePlaySharedWorldTrainingAudioQuestion(question, targetId);
        } else {
          const promptParts = sharedWorldTrainingQuestionParts(question, clean(options.fallbackText || "The practice gate is preparing a new word."));
          questionRoot.innerHTML = `
            <span class="ft-world-training-question-instruction">${escapeHtml(promptParts.instruction)}</span>
            ${promptParts.content ? `<span class="ft-world-training-question-content">${sharedWorldTrainingQuestionContentHtml(question, promptParts.content)}</span>` : ""}
          `;
        }
        return { speech: isSpeechQuestion, serverSpeech: isServerSpeechQuestion, audio: isAudioQuestion, translate: isTranslateQuestion, browserSpeech: browserSpeechQuestion };
      };

      const renderSharedWorldTraining = (payload = {}) => {
        const training = payload.training && typeof payload.training === "object" ? payload.training : payload;
        sharedWorldTrainingState = { training };
        const pendingEvent = training && training.event && typeof training.event === "object" ? training.event : (payload.event && typeof payload.event === "object" ? payload.event : {});
        const terminalEvent = Boolean(pendingEvent.slime_defeated || pendingEvent.slimeDefeated || pendingEvent.player_defeated || pendingEvent.cleared);
        if (performance.now() < sharedWorldTrainingProjectileLockUntil) {
          const previousTraining = sharedWorldTrainingDeferredRenderPayload && sharedWorldTrainingDeferredRenderPayload.training;
          const previousEvent = previousTraining && previousTraining.event;
          if (clean(pendingEvent.type) || !clean(previousEvent && previousEvent.type)) {
            sharedWorldTrainingDeferredRenderPayload = payload;
          }
          window.__ftTrainingBasicSkillRuntime = {
            ...(window.__ftTrainingBasicSkillRuntime || {}),
            renderDeferred: true,
            reason: "projectile-in-flight",
            at: Date.now(),
          };
          console.info("[FTG][TrainingBasicSkillRuntime]", window.__ftTrainingBasicSkillRuntime);
          return;
        }
        const stats = training.stats && typeof training.stats === "object" ? training.stats : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        scheduleSharedWorldTrainingRespawnRefresh(arena);
        sharedWorldTrainingBasicSkillKind = clean(arena.basic_skill_kind || arena.basicSkillKind || sharedWorldTrainingBasicSkillKind || "audio_word") || "audio_word";
        if (Array.isArray(arena.basic_skill_loadout) || Array.isArray(arena.basicSkillLoadout)) {
          const persistedLoadout = arena.basic_skill_loadout || arena.basicSkillLoadout;
          const nextLoadout = typeof sharedWorldTrainingNormalizeBasicLoadout === "function"
            ? sharedWorldTrainingNormalizeBasicLoadout(persistedLoadout)
            : persistedLoadout.slice(0, 3);
          if (nextLoadout.some(Boolean) || !sharedWorldTrainingBasicLoadout.some(Boolean)) sharedWorldTrainingBasicLoadout = nextLoadout;
        }
        const selected = worldTrainingSelectedSlime();
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : null;
        const question = selected ? (selectedQuestion || (arena.question && typeof arena.question === "object" ? arena.question : {})) : {};
        const selectedId = clean(selected && selected.id || arena.selected_id || arena.selectedId || "");
        renderSharedWorldCombatChoices(worldTrainingChoices, worldTrainingAnswerForm, question, Boolean(selected));
        const trainingEvent = (training.event && typeof training.event === "object") ? training.event : ((payload.event && typeof payload.event === "object") ? payload.event : null);
        if (trainingEvent) {
          flashSharedWorldTrainingEvent(trainingEvent);
          if (training && typeof training === "object") {
            delete training.event;
          }
          if (performance.now() < sharedWorldTrainingProjectileLockUntil) {
            sharedWorldTrainingDeferredRenderPayload = payload;
            return;
          }
        }
        renderSharedWorldTrainingStats(stats, arena);
        renderSharedWorldTrainingSlimes(arena);
        renderSharedWorldTrainingLog(arena);
        if (worldTrainingTarget) {
          const selectedName = selected ? `${clean(selected.name || "Slime")} Lv ${Math.max(1, Math.floor(Number(selected.level || 1) || 1))}` : "Choose a slime";
          worldTrainingTarget.textContent = selectedName;
        }
        if (worldTrainingQuestion) {
          const isAudioQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsAudioInput(question);
          if (!isAudioQuestion && sharedWorldTrainingAudioKey) {
            sharedWorldTrainingAudioKey = "";
            stopSharedWorldTrainingAudio();
          }
          renderSharedWorldTrainingQuestionPanel(worldTrainingQuestion, question, {
            selected: Boolean(selected), targetId: selectedId, context: "training", autoPlayAudio: true,
            emptyText: "Choose a slime to start training.",
          });
        }
        if (worldTrainingAnswer) {
          const speechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const translateQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsTranslateVi(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const browserSpeechLanguage = clean(question.speech_language || question.speechLanguage || "").toLowerCase();
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingAnswer.disabled = localSpeechQuestion;
          worldTrainingAnswer.dataset.vietnameseTypingActive = (translateQuestion || serverSpeechQuestion) && !speechQuestion ? "1" : "0";
          worldTrainingAnswer.placeholder = browserSpeechQuestion
            ? (browserSpeechLanguage === "en" || browserSpeechLanguage.startsWith("en-")
              ? "Type English or press Mic and speak English..."
              : "Type Vietnamese or press Mic and speak Vietnamese...")
            : (localSpeechQuestion
              ? "Use your microphone. Read until all tokens are detected."
              : (legacyServerSpeechQuestion ? "Type Vietnamese or press Ctrl to speak Vietnamese..." : (translateQuestion ? "Nhap ban dich tieng Viet..." : "Type the English answer...")));
        }
        if (worldTrainingAnswerForm) {
          const speechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingAnswerForm.classList.toggle("is-speech-mode", speechQuestion || serverSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-browser-speech-mode", browserSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-legacy-speech-mode", legacyServerSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-local-speech-mode", localSpeechQuestion);
          worldTrainingAnswerForm.setAttribute("aria-hidden", localSpeechQuestion ? "true" : "false");
        }
        if (worldTrainingViToggle) {
          const translateQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsTranslateVi(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const showVietnameseTypingToggle = Boolean(translateQuestion || (serverSpeechQuestion && browserSpeechQuestion));
          worldTrainingViToggle.hidden = !showVietnameseTypingToggle;
          worldTrainingViToggle.setAttribute("aria-hidden", showVietnameseTypingToggle ? "false" : "true");
        }
        if (worldTrainingSubmit) {
          const speechQuestion = selected && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = selected && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const browserSpeechInputActive = Boolean(
            typeof browserSpeechInputRecognition !== "undefined"
            && browserSpeechInputRecognition
            && typeof browserSpeechInputTarget !== "undefined"
            && browserSpeechInputTarget === worldTrainingAnswer
          );
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingSubmit.hidden = true;
          worldTrainingSubmit.setAttribute("aria-hidden", "true");
          worldTrainingSubmit.disabled = !selected || sharedWorldTrainingLoading || localSpeechQuestion || (browserSpeechQuestion && browserSpeechInputActive);
          worldTrainingSubmit.textContent = localSpeechQuestion || legacyServerSpeechQuestion
            ? (localSpeechQuestion ? "Mic live" : "Ctrl mic")
            : (browserSpeechQuestion ? (browserSpeechInputActive ? "Mic recording" : "Speech strike") : (selected && sharedWorldTrainingQuestionIsTranslateVi(question) ? "Translate strike" : "Strike"));
        }
        if (trainingEvent) {
          if (trainingEvent.cleared) {
            setSharedWorldStatus("Practice field cleared. A fresh set of slimes is ready.", "ok");
          } else if (trainingEvent.player_defeated || trainingEvent.return_to_city) {
            setSharedWorldStatus("Your fire core fainted. Returning to QM-City center.", "error");
            window.setTimeout(() => {
              if (sharedWorldTrainingIsActive()) {
                closeSharedWorldTraining();
              }
            }, 950);
          } else if (clean(trainingEvent.type).toLowerCase() === "skill") {
            const affected = Array.isArray(trainingEvent.affected) ? trainingEvent.affected.length : 0;
            const skillName = clean(trainingEvent.skill && trainingEvent.skill.name) || "Skill";
            const manaCost = Math.max(0, Math.floor(Number(trainingEvent.mana_cost || trainingEvent.manaCost || 0) || 0));
            setSharedWorldStatus(`${skillName} shook the field: ${affected} slime${affected === 1 ? "" : "s"} hit${trainingEvent.damage ? `, ${trainingEvent.damage} damage each` : ""}${manaCost ? ` · -${manaCost} MP` : ""}.`, "ok");
          } else if (trainingEvent.correct) {
            const earned = Math.max(0, Math.floor(Number(trainingEvent.earned_words || trainingEvent.earnedWords || 0) || 0));
            const healAmount = Math.max(0, Math.floor(Number(trainingEvent.heal_amount || trainingEvent.healAmount || 0) || 0));
            const skillName = clean(trainingEvent.skill && trainingEvent.skill.name) || "Training hit";
            const critical = Boolean(trainingEvent.critical || trainingEvent.criticalHit);
            setSharedWorldStatus(`${skillName} landed${critical ? " Critical x2" : ""}${trainingEvent.damage ? `: ${trainingEvent.damage} damage` : ""}${healAmount ? ` | +${healAmount} HP` : ""}${earned ? ` | +${earned} EXP` : ""}.`, "ok");
          } else if (trainingEvent.type === "hurt") {
            setSharedWorldStatus(`Slime countered${trainingEvent.damage ? `: ${trainingEvent.damage} damage` : ""}.`, "error");
          }
        }
        const selectedAlive = Boolean(selected && Math.max(0, Math.floor(Number(selected.hp || 0) || 0)) > 0);
        const questionOpen = Boolean(worldTrainingModal && worldTrainingModal.classList.contains("is-question-open"));
        const browserSpeechInputActive = Boolean(
          typeof browserSpeechInputRecognition !== "undefined"
          && browserSpeechInputRecognition
          && typeof browserSpeechInputTarget !== "undefined"
          && browserSpeechInputTarget === worldTrainingAnswer
        );
        if (selectedAlive && questionOpen && sharedWorldTrainingQuestionIsSpeech(question) && !sharedWorldTrainingUsesBrowserSpeechInput(question)) {
          maybeStartSharedWorldTrainingSpeech(question, selectedId);
        } else if (!selected || !sharedWorldTrainingQuestionIsSpeech(question) || sharedWorldTrainingUsesBrowserSpeechInput(question)) {
          sharedWorldTrainingAutoSpeechKey = "";
          if (sharedWorldTrainingSpeech.active && sharedWorldTrainingUsesBrowserSpeechInput(question) && !browserSpeechInputActive) {
            stopSharedWorldTrainingSpeech({ clearOverhead: false });
          } else if (!sharedWorldTrainingSpeech.active) {
            const holdUntil = Number(sharedWorldTrainingSpeech.holdUntil || 0);
            const holdActive = holdUntil && Date.now() < holdUntil;
            const heldExpected = clean(sharedWorldTrainingSpeech.expectedText || "");
            const heldTranscript = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
            if (holdActive && heldExpected && heldTranscript) {
              const passRatio = sharedWorldTrainingSpeech.passRatio || sharedWorldTrainingSpeechPassRatio(question, heldExpected);
              const heldQuestion = clean(sharedWorldTrainingSpeech.scoringLanguage || "") === "vi"
                ? { training_kind: "translate_vi_speech", server_speech: true }
                : question;
              const result = typeof sharedWorldTrainingSpeechScoreBundle === "function"
                ? sharedWorldTrainingSpeechScoreBundle(heldQuestion, heldTranscript, heldExpected, passRatio)
                : scoreSharedWorldTrainingSpeech(heldTranscript, heldExpected, passRatio);
              renderSharedWorldTrainingSpeechOverhead(heldTranscript, result);
            } else {
              sharedWorldTrainingSpeech.expectedText = "";
              sharedWorldTrainingSpeech.passRatio = 1;
              sharedWorldTrainingSpeech.holdUntil = 0;
              sharedWorldTrainingSpeech.scoringLanguage = "";
              clearSharedWorldTrainingSpeechOverhead();
            }
          }
        }
        if (selectedAlive && questionOpen && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)) {
          renderSharedWorldTrainingServerSpeechStatus(question, selectedId);
        } else if (!selected || !sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)) {
          if (sharedWorldTrainingServerSpeech.active && !sharedWorldTrainingServerSpeech.busy) {
            cancelSharedWorldTrainingServerSpeech();
          }
          sharedWorldTrainingServerSpeechCtrlCandidate = "";
        }
      };

      const stopSharedWorldTrainingPolling = () => {
        sharedWorldTrainingRealtimeGeneration += 1;
        if (sharedWorldTrainingPollTimer) {
          window.clearTimeout(sharedWorldTrainingPollTimer);
          sharedWorldTrainingPollTimer = 0;
        }
        if (sharedWorldTrainingRespawnTimer) {
          window.clearTimeout(sharedWorldTrainingRespawnTimer);
          sharedWorldTrainingRespawnTimer = 0;
        }
        if (sharedWorldTrainingAutoReselectTimer) {
          window.clearTimeout(sharedWorldTrainingAutoReselectTimer);
          sharedWorldTrainingAutoReselectTimer = 0;
        }
      };

      const startSharedWorldTrainingPolling = () => {
        stopSharedWorldTrainingPolling();
        const generation = sharedWorldTrainingRealtimeGeneration;
        const waitForNextRevision = async (initial = false) => {
          if (generation !== sharedWorldTrainingRealtimeGeneration || !sharedWorldTrainingIsActive()) return;
          const result = await loadSharedWorldTrainingShared({ wait: !initial });
          if (generation !== sharedWorldTrainingRealtimeGeneration || !sharedWorldTrainingIsActive()) return;
          sharedWorldTrainingRealtimeFailures = result ? 0 : Math.min(6, sharedWorldTrainingRealtimeFailures + 1);
          const retryDelay = result ? 0 : Math.min(5000, 250 * (2 ** (sharedWorldTrainingRealtimeFailures - 1)));
          sharedWorldTrainingPollTimer = window.setTimeout(() => {
            sharedWorldTrainingPollTimer = 0;
            void waitForNextRevision(false);
          }, retryDelay);
        };
        void waitForNextRevision(true);
      };

      // Added 2026-08-16: replay another user's Training cast from shared combat deltas.
      const queueSharedWorldTrainingRemoteCombatEvents = (shared = {}) => {
        const events = Array.isArray(shared.combat_events || shared.combatEvents) ? (shared.combat_events || shared.combatEvents) : [];
        const selfUsername = clean(activeWorldUsername() || currentAuthUsername).toLowerCase();
        const pendingEvents = [];
        events.forEach((raw) => {
          const row = raw && typeof raw === "object" ? raw : {};
          const eventId = clean(row.event_id || row.eventId || "");
          if (!eventId || sharedWorldTrainingSeenCombatEvents.has(eventId)) return;
          sharedWorldTrainingSeenCombatEvents.add(eventId);
          while (sharedWorldTrainingSeenCombatEvents.size > 128) {
            sharedWorldTrainingSeenCombatEvents.delete(sharedWorldTrainingSeenCombatEvents.values().next().value);
          }
          const attacker = clean(row.attacker || row.username || "").toLowerCase();
          const ageMs = Math.max(0, Date.now() - ((Number(row.at_epoch || row.atEpoch || 0) || 0) * 1000));
          if (!attacker || attacker === selfUsername || ageMs > 12000) return;
          pendingEvents.push(row);
        });
        pendingEvents
          .sort((left, right) => (Number(left.at_epoch || left.atEpoch || 0) || 0) - (Number(right.at_epoch || right.atEpoch || 0) || 0))
          .slice(-12)
          .forEach((row) => {
          if (!sharedWorldTrainingIsActive()) return;
          const attacker = clean(row.attacker || row.username || "").toLowerCase();
          const eventId = clean(row.event_id || row.eventId || "");
          const attackerNode = sharedWorldNodes.get(attacker);
          const targetId = clean(row.slime_id || row.slimeId || row.primary_slime_id || row.primarySlimeId || "");
          const slimeHost = sharedWorldTrainingSlimeHost();
          const targetNode = slimeHost && Array.from(slimeHost.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === targetId);
          if (!attackerNode || !attackerNode.isConnected) return;
          const remoteCastToken = `${eventId}:${performance.now().toFixed(3)}`;
          attackerNode.dataset.trainingRemoteCastToken = remoteCastToken;
          attackerNode.classList.add("is-training-remote-cast");
          const previousOverride = sharedWorldTrainingCombatOverride;
          sharedWorldTrainingCombatOverride = { sourceNode: attackerNode, targetNode, targetHost: slimeHost, effectParent: worldCard, mode: "training-remote" };
          try {
            faceSharedWorldTrainingCastSource(row, targetNode, attackerNode, "training-remote");
            flashSharedWorldTrainingEvent({ ...row, remote_shared_event: true });
          } finally {
            sharedWorldTrainingCombatOverride = previousOverride;
          }
          window.setTimeout(() => {
            if (attackerNode.dataset.trainingRemoteCastToken !== remoteCastToken) return;
            delete attackerNode.dataset.trainingRemoteCastToken;
            attackerNode.classList.remove("is-training-remote-cast");
          }, 5200);
          const trace = Array.isArray(window.__ftTrainingRemoteCombatTrace) ? window.__ftTrainingRemoteCombatTrace : [];
          trace.push({
            eventId,
            attacker,
            targetId,
            ageMs: Math.max(0, Math.round(Date.now() - ((Number(row.at_epoch || row.atEpoch || 0) || 0) * 1000))),
            at: Date.now(),
          });
          window.__ftTrainingRemoteCombatTrace = trace.slice(-80);
        });
      };

      // Added 2026-08-14: shared HP waits for the projectile/explosion impact instead of jumping early.
      const applySharedWorldTrainingSharedSnapshot = (shared = {}, source = "delta-update") => {
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training;
        const arena = training && training.arena;
        if (!arena) return shared;
        const selectedId = clean(arena.selected_id || arena.selectedId || "");
        const currentQuestion = arena.question && typeof arena.question === "object" ? arena.question : {};
        const previousSelected = selectedId && Array.isArray(arena.slimes)
          ? arena.slimes.find((row) => clean(row && row.id) === selectedId)
          : null;
        const incomingSlimes = Array.isArray(shared.slimes) ? shared.slimes : [];
        const incomingSelected = selectedId
          ? incomingSlimes.find((row) => clean(row && row.id) === selectedId)
          : null;
        const previousGeneration = Math.max(0, Math.floor(Number(previousSelected && (previousSelected.generation ?? previousSelected.respawn_generation) || 0) || 0));
        const incomingGeneration = Math.max(0, Math.floor(Number(incomingSelected && (incomingSelected.generation ?? incomingSelected.respawn_generation) || 0) || 0));
        const staleSelection = Boolean(selectedId && (
          !incomingSelected
          || Math.max(0, Number(incomingSelected.hp || 0) || 0) <= 0
          || (previousGeneration > 0 && incomingGeneration > 0 && previousGeneration !== incomingGeneration)
        ));
        if (staleSelection) {
          arena.selected_id = "";
          arena.selectedId = "";
          arena.question = {};
          sharedWorldTrainingSelectSeq += 1;
          setSharedWorldTrainingQuestionOpen(false);
        }
        arena.slimes = incomingSlimes.map((row) => ({
          ...row,
          question: !staleSelection && clean(row.id) === selectedId ? currentQuestion : {},
        }));
        arena.shared_revision = Number(shared.revision || 0) || 0;
        arena.shared_arena_id = clean(shared.id || "training_shared_v1");
        renderSharedWorldTrainingSlimes(arena);
        if (staleSelection && !sharedWorldTrainingAutoReselectTimer) {
          const nextTarget = arena.slimes.find((row) => Math.max(0, Number(row && row.hp || 0) || 0) > 0);
          if (nextTarget) {
            sharedWorldTrainingAutoReselectTimer = window.setTimeout(() => {
              sharedWorldTrainingAutoReselectTimer = 0;
              if (sharedWorldTrainingIsActive()) selectSharedWorldTrainingSlime(clean(nextTarget.id || ""));
            }, 120);
          }
        }
        queueSharedWorldTrainingRemoteCombatEvents(shared);
        scheduleSharedWorldTrainingRespawnRefresh(arena);
        window.__ftTrainingSharedFeedTrace = {
          revision: arena.shared_revision,
          slimes: arena.slimes.length,
          etag: sharedWorldTrainingSharedEtag,
          source,
          at: Date.now(),
        };
        const latestCombatEvent = Array.isArray(shared.combat_events) && shared.combat_events.length
          ? shared.combat_events[shared.combat_events.length - 1]
          : {};
        document.documentElement.dataset.trainingSharedRevision = String(arena.shared_revision);
        document.documentElement.dataset.trainingSharedCombatEvent = JSON.stringify({
          id: clean(latestCombatEvent.event_id || ""),
          attacker: clean(latestCombatEvent.attacker || ""),
          type: clean(latestCombatEvent.type || ""),
        });
        console.info("[FTG][TrainingSharedFeed]", window.__ftTrainingSharedFeedTrace);
        return shared;
      };

      // Added 2026-08-14: one revisioned shared Slime feed; user HP/questions stay private.
      const loadSharedWorldTrainingShared = async (options = {}) => {
        if (!authToken || !sharedWorldTrainingIsActive()) return null;
        const wait = Boolean(options && options.wait);
        try {
          const sinceRevision = Number(sharedWorldTrainingSharedCache && sharedWorldTrainingSharedCache.revision || 0) || 0;
          const endpoint = wait
            ? `/world/training/shared/wait?since_revision=${encodeURIComponent(sinceRevision)}&timeout=1.35`
            : "/world/training/shared";
          const response = await fetchAuthJson(endpoint, {
            timeoutMs: wait ? 7000 : 0,
            silentTimeout: true,
            ifNoneMatch: wait ? "" : sharedWorldTrainingSharedEtag,
            notModifiedPayload: sharedWorldTrainingSharedCache,
          });
          const result = response && response.payload ? response.payload : response;
          const shared = result && result.training_shared && typeof result.training_shared === "object"
            ? result.training_shared
            : (result && Array.isArray(result.slimes) && result.id ? result : null);
          if (!shared) return sharedWorldTrainingSharedCache;
          const serverEpoch = Number(shared.server_epoch || shared.serverEpoch || 0) || 0;
          if (!(response && response.notModified) && serverEpoch > 0) {
            sharedWorldTrainingServerClockOffsetMs = serverEpoch * 1000 - Date.now();
          }
          const previousRevision = Number(sharedWorldTrainingSharedCache && sharedWorldTrainingSharedCache.revision || 0) || 0;
          sharedWorldTrainingSharedCache = shared;
          sharedWorldTrainingSharedEtag = clean(response && response.etag || sharedWorldTrainingSharedEtag);
          if ((Number(shared.revision || 0) || 0) === previousRevision) return shared;
          sharedWorldTrainingSharedFastUntil = Date.now() + 4500;
          if (performance.now() < sharedWorldTrainingProjectileLockUntil) {
            sharedWorldTrainingDeferredSharedSnapshot = shared;
            console.info("[FTG][TrainingSharedFeedDeferred]", JSON.stringify({
              revision: Number(shared.revision || 0) || 0,
              reason: "projectile-in-flight",
              at: Date.now(),
            }));
            return shared;
          }
          return applySharedWorldTrainingSharedSnapshot(shared, response && response.notModified ? "etag-304" : "delta-update");
        } catch (_error) {
          return null;
        }
      };

      // Added 2026-08-11: refresh once when the earliest defeated slime reaches its durable respawn timestamp.
      const scheduleSharedWorldTrainingRespawnRefresh = (arena = {}) => {
        if (sharedWorldTrainingRespawnTimer) {
          window.clearTimeout(sharedWorldTrainingRespawnTimer);
          sharedWorldTrainingRespawnTimer = 0;
        }
        const respawnEpochs = (Array.isArray(arena.slimes) ? arena.slimes : [])
          .filter((slime) => slime && Math.max(0, Number(slime.hp || 0) || 0) <= 0)
          .map((slime) => Number(slime.respawn_at || slime.respawnAt || 0) || 0)
          .filter((epoch) => epoch > 0);
        if (!respawnEpochs.length || !sharedWorldTrainingIsActive()) {
          return;
        }
        const delayMs = Math.max(180, Math.min(10000, Math.ceil(Math.min(...respawnEpochs) * 1000 - Date.now() + 140)));
        sharedWorldTrainingRespawnTimer = window.setTimeout(() => {
          sharedWorldTrainingRespawnTimer = 0;
          void loadSharedWorldTraining(false, { quiet: true });
        }, delayMs);
      };

      const loadSharedWorldTraining = async (focusInput = false, options = {}) => {
        if (!authToken || !sharedWorldTrainingIsActive()) {
          return;
        }
        const quiet = Boolean(options && options.quiet);
        const requestSeq = ++sharedWorldTrainingRequestSeq;
        if (!quiet) {
          setSharedWorldTrainingBusy(true);
        }
        try {
          if (!sharedWorldTrainingBaselineCache) await loadSharedWorldTrainingBaseline();
          const response = await fetchAuthJson(`/world/training/state?ts=${Date.now()}&refresh=1`, { timeoutMs: 0, silentTimeout: true });
          if (requestSeq !== sharedWorldTrainingRequestSeq) {
            return;
          }
          const result = response && response.payload ? response.payload : response;
          const trainingPayload = result && result.training ? result.training : result;
          const trainingEvent = trainingPayload && trainingPayload.event && typeof trainingPayload.event === "object" ? trainingPayload.event : {};
          if (trainingEvent.slime_defeated || trainingEvent.slimeDefeated || trainingEvent.player_defeated || trainingEvent.cleared) {
            await clearSharedWorldTrainingSessionCombatCheckpoint(trainingPayload && trainingPayload.arena);
          } else {
            await mergeSharedWorldTrainingSessionCombatCheckpoint(trainingPayload);
          }
          renderSharedWorldTraining(result);
          if (focusInput && worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
          return result;
        } catch (error) {
          if (!quiet) {
            setSharedWorldStatus(error && error.message ? error.message : "Could not load practice gate.", "error");
          }
        } finally {
          if (!quiet && requestSeq === sharedWorldTrainingRequestSeq) {
            setSharedWorldTrainingBusy(false);
          }
        }
      };

      const postSharedWorldTraining = async (path, body = {}, focusInput = true, options = {}) => {
        if (!authToken) {
          return;
        }
        const background = Boolean(options && options.background);
        if (!background) setSharedWorldTrainingBusy(true);
        try {
          const response = await fetchAuthJson(path, {
            method: "POST",
            timeoutMs: 0,
            body: JSON.stringify(body || {}),
          });
          const result = response && response.payload ? response.payload : response;
          const trainingPayload = result && result.training ? result.training : result;
          const trainingEvent = trainingPayload && trainingPayload.event && typeof trainingPayload.event === "object" ? trainingPayload.event : {};
          if (trainingEvent.slime_defeated || trainingEvent.slimeDefeated || trainingEvent.player_defeated || trainingEvent.cleared) {
            await clearSharedWorldTrainingSessionCombatCheckpoint(trainingPayload && trainingPayload.arena);
          } else {
            await mergeSharedWorldTrainingSessionCombatCheckpoint(trainingPayload);
          }
          if (!options || options.render !== false) {
            renderSharedWorldTraining(result);
          }
          if (focusInput && worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
          return result;
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Practice gate action failed.", "error");
          return null;
        } finally {
          if (!background) setSharedWorldTrainingBusy(false);
        }
      };

      // Added 2026-08-16: fully suspend the old Training runtime before City starts rendering.
      const suspendSharedWorldTrainingRuntime = () => {
        sharedWorldTrainingVisualGeneration += 1;
        sharedWorldMaleUltimateCastToken += 1;
        sharedWorldScorpioUltimateCastToken += 1;
        sharedWorldTrainingProjectileLockUntil = 0;
        sharedWorldTrainingDeferredRenderPayload = null;
        sharedWorldTrainingDeferredSharedSnapshot = null;
        sharedWorldTrainingCombatOverride = null;
        sharedWorldTrainingOptimisticActions.clear();
        stopSharedWorldTrainingPolling();
        stopSharedWorldTrainingLocalMotion();
        const castClasses = [
          "is-training-cast", "is-training-critical-cast", "is-training-remote-cast-source", "is-scorpio-basic-cast",
          "is-scorpio-basic-1", "is-scorpio-basic-2", "is-scorpio-basic-3",
          "is-scorpio-cast-left", "is-scorpio-cast-right", "is-scorpio-ultimate-cast",
          "is-scorpio-ultimate-left", "is-scorpio-ultimate-right", "is-earthquake-cast",
        ];
        sharedWorldNodes.forEach((node) => node && node.classList.remove(...castClasses));
        if (worldTrainingField) {
          worldTrainingField.querySelectorAll("#ft-world-training-effects, #ft-world-training-underlay-effects")
            .forEach((node) => node.remove());
        }
        if (worldTrainingMapSlimes) worldTrainingMapSlimes.innerHTML = "";
      };

      const openSharedWorldTraining = (options = {}) => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de mo khu luyen tap.");
          return;
        }
        const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.status) === "active";
        if (activeBattle) {
          setSharedWorldStatus("Finish the current battle before entering Slime Training Field.", "error");
          return;
        }
        const restoreCheckpoint = options && options.restoreCheckpoint && options.restoreCheckpoint.mapMode === "training"
          ? options.restoreCheckpoint
          : null;
        const entryStartedAt = performance.now();
        const prefetchedTraining = sharedWorldTrainingState && sharedWorldTrainingState.training
          ? sharedWorldTrainingState.training
          : null;
        sharedWorldMapMode = "training";
        sharedWorldObstacles = normalizeSharedWorldObstacles(sharedWorldObstacleSets.training);
        sharedWorldObstacleMode = "off";
        sharedWorldObstacleDraft = null;
        sharedWorldTrainingAutoSpeechKey = "";
        sharedWorldTrainingAudioKey = "";
        sharedWorldRequestSeq += 1;
        startSharedWorldBattlePolling();
        clearSharedWorldFollowTarget();
        setSharedWorldPickingPosition(false);
        if (worldCard) {
          worldCard.classList.add("is-training-map");
        }
        renderSharedWorldObstacleEditor();
        if (worldTitle) {
          worldTitle.textContent = "Slime Training Field";
        }
        if (worldTrainingField) {
          worldTrainingField.hidden = false;
          worldTrainingField.setAttribute("aria-hidden", "false");
        }
        if (worldTrainingModal) {
          worldTrainingModal.classList.add("is-open");
          worldTrainingModal.setAttribute("aria-hidden", "false");
        }
        if (worldTrainingMapSlimes && !prefetchedTraining) {
          worldTrainingMapSlimes.innerHTML = "";
        }
        if (worldTrainingTarget) {
          worldTrainingTarget.textContent = "Loading slime field";
        }
        if (worldTrainingQuestion) {
          worldTrainingQuestion.textContent = "Refreshing your training slimes...";
        }
        if (worldTrainingHistoryTitle) {
          worldTrainingHistoryTitle.textContent = "No training hit yet";
        }
        if (worldTrainingHistoryList) {
          worldTrainingHistoryList.innerHTML = '<article class="is-empty">Hit or defeat a slime to review the question, correct answer, and your answer here.</article>';
        }
        if (typeof hideSharedWorldTrainingHistory === "function") {
          hideSharedWorldTrainingHistory();
        }
        if (prefetchedTraining) {
          renderSharedWorldTraining({ training: prefetchedTraining });
        }
        if (sharedWorldTrainingPresenceState) {
          renderSharedWorld({ world: sharedWorldTrainingPresenceState });
        }
        setSharedWorldTrainingQuestionOpen(false);
        const entryPoint = restoreCheckpoint || options.entryPoint || sharedWorldTrainingDefaultPoint;
        setSharedWorldSelfPosition(entryPoint, { center: true, smooth: false });
        void moveSharedWorldPlayer(entryPoint);
        if (restoreCheckpoint && worldStage) {
          window.requestAnimationFrame(() => {
            const maxLeft = Math.max(0, worldArena.scrollWidth - worldStage.clientWidth);
            const maxTop = Math.max(0, worldArena.scrollHeight - worldStage.clientHeight);
            worldStage.scrollTo({
              left: Math.max(0, Math.min(maxLeft, restoreCheckpoint.viewLeft)),
              top: Math.max(0, Math.min(maxTop, restoreCheckpoint.viewTop)),
              behavior: "auto",
            });
          });
        }
        void postSharedWorldObstacle({ action: "get", map: "training" }).catch(() => {});
        setSharedWorldStatus("Slime Training Field opened. Move on the map, select a slime, then answer in English.", "ok");
        startSharedWorldTrainingLocalMotion();
        startSharedWorldTrainingPolling();
        startSharedWorldPolling();
        window.__ftTrainingEntryPerf = {
          cachedState: Boolean(prefetchedTraining),
          mapAssetReady: sharedWorldCharacterAssetState.ready,
          openedMs: Math.round((performance.now() - entryStartedAt) * 10) / 10,
          at: Date.now(),
        };
        window.requestAnimationFrame(() => {
          window.__ftTrainingEntryPerf.firstPaintMs = Math.round((performance.now() - entryStartedAt) * 10) / 10;
          console.info("[FTG][TrainingEntryPerf]", JSON.stringify(window.__ftTrainingEntryPerf));
          hideSharedWorldMapLoading();
        });
        void loadSharedWorldTraining(false, { quiet: Boolean(prefetchedTraining) }).then(() => {
          window.__ftTrainingEntryPerf.stateReadyMs = Math.round((performance.now() - entryStartedAt) * 10) / 10;
        });
      };

      const closeSharedWorldTraining = (options = {}) => {
        const wasTraining = sharedWorldMapMode === "training";
        const placeAtTarget = Boolean(options && options.placeAtTarget);
        const preserveCheckpoint = Boolean(options && options.preserveCheckpoint);
        const returnPoint = options && options.targetPoint && typeof options.targetPoint === "object"
          ? { x: sharedWorldClamp(options.targetPoint.x, sharedWorldCityDefaultPoint.x), y: sharedWorldClamp(options.targetPoint.y, sharedWorldCityDefaultPoint.y) }
          : sharedWorldCityDefaultPoint;
        if (typeof hideSharedWorldTrainingHistory === "function") {
          hideSharedWorldTrainingHistory();
        }
        hideSharedWorldMoveMarker(false);
        suspendSharedWorldTrainingRuntime();
        sharedWorldMapMode = "city";
        if (!preserveCheckpoint) {
          writeSharedWorldCheckpoint(returnPoint);
        }
        sharedWorldObstacles = normalizeSharedWorldObstacles(sharedWorldObstacleSets.city);
        if (worldCard) {
          worldCard.classList.remove("is-training-map");
        }
        renderCachedSharedWorldCity();
        renderSharedWorldObstacleEditor();
        if (worldTitle) {
          worldTitle.textContent = "QM-City";
        }
        if (worldTrainingField) {
          worldTrainingField.setAttribute("aria-hidden", "true");
          worldTrainingField.hidden = true;
        }
        if (worldTrainingModal) {
          worldTrainingModal.classList.remove("is-open");
          worldTrainingModal.setAttribute("aria-hidden", "true");
        }
        if (worldTrainingMapSlimes) {
          worldTrainingMapSlimes.innerHTML = "";
        }
        setSharedWorldTrainingQuestionOpen(false);
        sharedWorldTrainingRequestSeq += 1;
        sharedWorldTrainingLoading = false;
        sharedWorldTrainingAutoSpeechKey = "";
        if (sharedWorldTrainingSkillCooldownTimer) {
          window.clearInterval(sharedWorldTrainingSkillCooldownTimer);
          sharedWorldTrainingSkillCooldownTimer = 0;
        }
        stopSharedWorldTrainingSpeech();
        stopSharedWorldTrainingLootWatch();
        sharedWorldTrainingLootDrops.forEach((record) => {
          if (record && record.node && record.node.parentNode) {
            record.node.parentNode.removeChild(record.node);
          }
        });
        sharedWorldTrainingLootDrops.clear();
        setSharedWorldTrainingBusy(false);
        if (wasTraining && worldModal && worldModal.classList.contains("is-open")) {
          if (placeAtTarget) {
            sharedWorldNeedInitialCenter = false;
            const self = setSharedWorldSelfPosition(returnPoint, { center: true, smooth: false });
            if (self && self.point) {
              void moveSharedWorldPlayer(self.point);
            } else {
              void refreshSharedWorld();
            }
          } else {
            sharedWorldNeedInitialCenter = true;
            const citySelf = getSharedWorldSelfPosition();
            void moveSharedWorldPlayer({
              x: sharedWorldClamp(citySelf.tx != null ? citySelf.tx : citySelf.x),
              y: sharedWorldClamp(citySelf.ty != null ? citySelf.ty : citySelf.y),
            });
          }
          void refreshSharedWorldBattle();
          startSharedWorldPolling();
          startSharedWorldBattlePolling();
          setSharedWorldStatus(placeAtTarget ? "Returned through the linked portal region." : "Returned to QM-City center.", "ok");
        }
      };

      // Added 2026-08-16: a cold question is built outside the gameplay lock, then fetched from RAM without another user click.
      const refreshSharedWorldTrainingQuestionUntilReady = (slimeId = "", selectSeq = 0, attempt = 0) => {
        if (!slimeId || selectSeq !== sharedWorldTrainingSelectSeq || attempt >= 8 || !sharedWorldTrainingIsActive()) {
          return;
        }
        window.setTimeout(async () => {
          if (selectSeq !== sharedWorldTrainingSelectSeq || !sharedWorldTrainingIsActive()) return;
          await loadSharedWorldTraining(false, { quiet: true });
          if (selectSeq !== sharedWorldTrainingSelectSeq) return;
          const selected = worldTrainingSelectedSlime();
          const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
          if (clean(selected && selected.id || "") !== slimeId) return;
          if (clean(question.prompt || question.content || "")) {
            setSharedWorldTrainingQuestionOpen(true);
            console.info("[FTG][TrainingQuestionTransition]", {
              phase: "question-ready-after-ram-refresh",
              slimeId,
              selectSeq,
              attempt: attempt + 1,
            });
            if (worldTrainingAnswer && (!worldTrainingAnswerForm || !worldTrainingAnswerForm.classList.contains("is-choice-mode"))) {
              worldTrainingAnswer.focus();
            }
            return;
          }
          refreshSharedWorldTrainingQuestionUntilReady(slimeId, selectSeq, attempt + 1);
        }, Math.min(900, 260 + attempt * 110));
      };

      const selectSharedWorldTrainingSlime = (slimeId = "") => {
        const id = clean(slimeId);
        if (!id) {
          return;
        }
        const selected = worldTrainingSelectedSlime();
        const selectedId = clean(selected && selected.id || "");
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        if (sharedWorldTrainingSpeech.active) {
          if (selectedId === id && sharedWorldTrainingQuestionIsSpeech(selectedQuestion)) {
            setSharedWorldTrainingQuestionOpen(true);
            restartSharedWorldTrainingSpeech(selectedQuestion, id);
            return;
          }
          stopSharedWorldTrainingSpeech();
          sharedWorldTrainingAutoSpeechKey = "";
          scheduleSharedWorldTrainingSpeechOverheadClear();
        }
        if (sharedWorldTrainingServerSpeech.active) {
          if (selectedId === id && sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)) {
            setSharedWorldTrainingQuestionOpen(true);
            renderSharedWorldTrainingServerSpeechStatus(selectedQuestion, id);
            return;
          }
          cancelSharedWorldTrainingServerSpeech();
        }
        if (selectedId === id && sharedWorldTrainingQuestionIsSpeech(selectedQuestion)) {
          setSharedWorldTrainingQuestionOpen(true);
          restartSharedWorldTrainingSpeech(selectedQuestion, id);
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : null;
        const slimes = arena && Array.isArray(arena.slimes) ? arena.slimes : [];
        const targetSlime = slimes.find((item) => clean(item && item.id) === id);
        if (!arena || !targetSlime) {
          void loadSharedWorldTraining(true);
          return;
        }
        arena.selected_id = id;
        arena.selectedId = id;
        sharedWorldTrainingSlimeSelectionQuietUntil = Date.now() + 1250;
        renderSharedWorldTrainingSlimes(arena);
        if (worldTrainingTarget) {
          worldTrainingTarget.textContent = `${clean(targetSlime.name || "Slime")} Lv ${Math.max(1, Math.floor(Number(targetSlime.level || 1) || 1))}`;
        }
        const self = getSharedWorldSelfPosition() || { x: 0.5, y: 0.5 };
        const trainingKind = sharedWorldTrainingBasicSkillKind === "random"
          ? sharedWorldTrainingRandomBasicKind()
          : sharedWorldTrainingBasicSkillKind;
        const selectSeq = ++sharedWorldTrainingSelectSeq;
        console.info("[FTG][TrainingQuestionTransition]", {
          phase: "target-selected-awaiting-question",
          slimeId: id,
          trainingKind,
          selectSeq,
          preservedPanel: true,
        });
        void postSharedWorldTraining("/world/training/select", {
          slime_id: id,
          training_kind: trainingKind,
          player_x: self.x,
          player_y: self.y,
        }, false, { render: false }).then((result) => {
          if (!result || selectSeq !== sharedWorldTrainingSelectSeq) {
            return;
          }
          renderSharedWorldTraining(result);
          const currentSelected = worldTrainingSelectedSlime();
          if (clean(currentSelected && currentSelected.id || "") !== id) {
            return;
          }
          const currentQuestion = currentSelected.question && typeof currentSelected.question === "object"
            ? currentSelected.question
            : {};
          if (!clean(currentQuestion.prompt || currentQuestion.content || "")) {
            console.info("[FTG][TrainingQuestionTransition]", {
              phase: "question-preparing-ram-refresh",
              slimeId: id,
              trainingKind,
              selectSeq,
            });
            refreshSharedWorldTrainingQuestionUntilReady(id, selectSeq);
            return;
          }
          setSharedWorldTrainingQuestionOpen(true);
          console.info("[FTG][TrainingQuestionTransition]", {
            phase: "question-ready-panel-open",
            slimeId: id,
            trainingKind: clean(currentSelected.question && (currentSelected.question.training_kind || currentSelected.question.trainingKind) || trainingKind),
            selectSeq,
          });
          if (worldTrainingAnswer && (!worldTrainingAnswerForm || !worldTrainingAnswerForm.classList.contains("is-choice-mode"))) {
            worldTrainingAnswer.focus();
          }
        });
      };

      const submitSharedWorldTrainingAnswer = (selectedAnswer = "") => {
        const selected = worldTrainingSelectedSlime();
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        const browserSpeechQuestion = selected && sharedWorldTrainingUsesBrowserSpeechInput(selectedQuestion);
        const browserSpeechInputActive = Boolean(
          typeof browserSpeechInputRecognition !== "undefined"
          && browserSpeechInputRecognition
          && typeof browserSpeechInputTarget !== "undefined"
          && browserSpeechInputTarget === worldTrainingAnswer
        );
        if (browserSpeechQuestion && browserSpeechInputActive) {
          setSharedWorldTrainingQuestionOpen(true);
          renderSharedWorldTrainingServerSpeechStatus(selectedQuestion, selected.id);
          setSharedWorldStatus("Mic is still recording. Press Ctrl or the mic button again to stop and score.", "error");
          return;
        }
        if (sharedWorldTrainingSpeech.active && !browserSpeechQuestion) {
          setSharedWorldStatus("Mic challenge is active. Read the shown text before the slime timer ends.", "error");
          return;
        }
        if ((sharedWorldTrainingServerSpeech.active || sharedWorldTrainingServerSpeech.busy) && !browserSpeechQuestion) {
          setSharedWorldStatus("Vietnamese speech challenge is active. Press Ctrl again to stop and score.", "error");
          return;
        }
        const answer = clean(selectedAnswer || (worldTrainingAnswer && worldTrainingAnswer.value));
        if (!answer) {
          setSharedWorldTrainingQuestionOpen(true);
          setSharedWorldStatus(
            sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
              ? "Speak or type the Vietnamese answer before striking the slime."
              : "Type the English answer before striking the slime.",
            "error"
          );
          if (worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
          return;
        }
        if (worldTrainingAnswer) {
          worldTrainingAnswer.value = "";
        }
        if (browserSpeechQuestion && (sharedWorldTrainingQuestionIsSpeech(selectedQuestion) || sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion))) {
          const expectedText = sharedWorldTrainingSpeechText(selectedQuestion);
          const passRatio = sharedWorldTrainingSpeechPassRatio(selectedQuestion, expectedText);
          const score = typeof sharedWorldTrainingSpeechScoreBundle === "function"
            ? sharedWorldTrainingSpeechScoreBundle(selectedQuestion, answer, expectedText, passRatio)
            : scoreSharedWorldTrainingSpeech(answer, expectedText, passRatio);
          const vietnameseSpeechPayload = sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
            ? { server_speech: true, speech_language: "vi", browser_speech: true, browserSpeech: true }
            : {};
          void postSharedWorldTraining("/world/training/answer", {
            answer,
            slime_id: selected ? clean(selected.id) : "",
            generation: selected ? Math.max(1, Math.floor(Number(selected.generation ?? selected.respawn_generation ?? 1) || 1)) : 0,
            client_action_id: `training_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`,
            ...vietnameseSpeechPayload,
            local_speech_passed: Boolean(score.passed),
            local_speech_percent: Math.max(0, Math.min(100, Number(score && score.score || 0) || 0)),
            local_speech_correct: Math.max(0, Number(score && score.correct || 0) || 0),
            local_speech_total: Math.max(0, Number(score && score.total || 0) || 0),
            local_speech_reason: score.passed ? "browser_speech_input" : "browser_speech_partial",
            local_speech_expected: expectedText,
          }, true);
          return;
        }
        const speechPayload = browserSpeechQuestion && (
          sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
          || sharedWorldTrainingQuestionIsTranslateVi(selectedQuestion)
        )
          ? { server_speech: true, speech_language: "vi" }
          : {};
        const choices = Array.isArray(selectedQuestion.choices) ? selectedQuestion.choices.slice(0, 3) : [];
        const selectedIndex = choices.findIndex((choice) => clean(choice && typeof choice === "object" ? (choice.value || choice.label) : choice) === answer);
        const correctIndex = Number(selectedQuestion.client_correct_choice_index ?? selectedQuestion.clientCorrectChoiceIndex);
        const clientFirst = choices.length === 3 && Number.isInteger(correctIndex) && correctIndex >= 0 && selectedIndex >= 0;
        const clientActionId = `training_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
        const pendingKey = `training:${clean(selectedQuestion.id)}:${clean(selected && selected.id)}`;
        if (clientFirst && sharedWorldCombatPendingAnswers.has(pendingKey)) return;
        if (clientFirst) {
          sharedWorldCombatPendingAnswers.add(pendingKey);
          previewSharedWorldCombatChoice(worldTrainingChoices, answer, selectedIndex === correctIndex);
        }
        if (clientFirst && selected) {
          const correct = selectedIndex === correctIndex;
          sharedWorldTrainingOptimisticActions.set(clientActionId, { correct, at: performance.now() });
          flashSharedWorldTrainingEvent({
            event_id: `preview_${clientActionId}`,
            client_action_id: clientActionId,
            client_preview: true,
            type: correct ? "hit" : "hurt",
            correct,
            damage: correct ? Math.max(1, Math.floor(Number((sharedWorldTrainingState && sharedWorldTrainingState.training && sharedWorldTrainingState.training.stats && sharedWorldTrainingState.training.stats.strength) || 1) || 1)) : 0,
            slime_id: clean(selected.id),
            slime_name: clean(selected.name || "Slime"),
            slime_level: Number(selected.level || 1) || 1,
            slime_x: selected.tx ?? selected.x,
            slime_y: selected.ty ?? selected.y,
          });
          if (!correct) {
            applySharedWorldTrainingLocalBasicResult(clean(selected.id), false);
          }
        }
        const startedAt = performance.now();
        void postSharedWorldTraining("/world/training/answer", {
          answer,
          slime_id: selected ? clean(selected.id) : "",
          client_action_id: clientActionId,
          generation: selected ? Math.max(1, Math.floor(Number(selected.generation ?? selected.respawn_generation ?? 1) || 1)) : 0,
          defer_next_question: clientFirst,
          ...speechPayload,
        }, true, { background: clientFirst, render: !clientFirst }).then((result) => {
          if (!result && clientActionId) {
            sharedWorldTrainingOptimisticActions.delete(clientActionId);
          }
          window.__ftTrainingChoiceLatency = {
            clientFirst,
            actionId: clientActionId,
            responseMs: Math.round((performance.now() - startedAt) * 10) / 10,
            at: Date.now(),
          };
          console.info("[FTG][TrainingChoiceLatency]", JSON.stringify(window.__ftTrainingChoiceLatency));
          const nextArena = result && result.training && result.training.arena && typeof result.training.arena === "object" ? result.training.arena : {};
          const nextSlimeId = clean(nextArena.selected_id || nextArena.selectedId || "");
          const nextQuestion = nextArena.question && typeof nextArena.question === "object" ? nextArena.question : {};
          if (!clientFirst || !result) return;
          if (!nextSlimeId || clean(nextQuestion.prompt || nextQuestion.answer)) {
            renderSharedWorldTraining(result);
            return;
          }
          console.info("[FTG][TrainingQuestionTransition]", {
            phase: "answer-confirmed-awaiting-next-question",
            slimeId: nextSlimeId,
            trainingKind: clean(nextArena.basic_skill_kind || nextArena.basicSkillKind || sharedWorldTrainingBasicSkillKind),
            preservedPanel: true,
          });
          const self = getSharedWorldSelfPosition() || { x: 0.5, y: 0.5 };
          void fetchAuthJson("/world/training/select", {
            method: "POST",
            timeoutMs: 0,
            body: JSON.stringify({
              slime_id: nextSlimeId,
              training_kind: clean(nextArena.basic_skill_kind || nextArena.basicSkillKind || sharedWorldTrainingBasicSkillKind),
              player_x: self.x,
              player_y: self.y,
            }),
          }).then((nextResponse) => {
            renderSharedWorldTraining(nextResponse && nextResponse.payload ? nextResponse.payload : nextResponse);
          }).catch((error) => {
            setSharedWorldStatus(error && error.message ? error.message : "Could not preload the next question.", "error");
            window.setTimeout(() => {
              if (sharedWorldMapMode === "training") {
                void postSharedWorldTraining("/world/training/select", {
                  slime_id: nextSlimeId,
                  training_kind: clean(nextArena.basic_skill_kind || nextArena.basicSkillKind || sharedWorldTrainingBasicSkillKind),
                  player_x: self.x,
                  player_y: self.y,
                }, true);
              }
            }, 500);
          });
        }).finally(() => {
          if (clientFirst) sharedWorldCombatPendingAnswers.delete(pendingKey);
        });
      };

      const upgradeSharedWorldTrainingStat = (stat = "") => {
        const key = clean(stat);
        if (!key) {
          return;
        }
        void postSharedWorldTraining("/world/training/upgrade", { stat: key }, false);
      };

      const upgradeSharedWorldTrainingSkill = (skillId = "") => {
        const key = clean(skillId || "earthquake");
        if (!key) {
          return;
        }
        void postSharedWorldTraining("/world/training/upgrade", { skill: key }, false);
      };

      const startSharedWorldTrainingSkillCooldown = (skillId = "earthquake", seconds = 10) => {
        const key = clean(skillId || "earthquake") || "earthquake";
        const duration = Math.max(1, Number(seconds || 10) || 10);
        sharedWorldTrainingSkillCooldownSeconds.set(key, duration);
        sharedWorldTrainingSkillCooldownUntil.set(key, Date.now() + duration * 1000);
        renderSharedWorldTrainingQuickSkill();
      };

      const castSharedWorldTrainingSkill = async (skillId = "earthquake") => {
        const key = clean(skillId || "earthquake") || "earthquake";
        if (sharedWorldTrainingLoading) {
          setSharedWorldStatus("Training action is still resolving.", "error");
          return;
        }
        const cooldownUntil = Number(sharedWorldTrainingSkillCooldownUntil.get(key) || 0);
        const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
        if (remaining > 0) {
          setSharedWorldStatus(`Skill cooling down: ${remaining}s.`, "error");
          renderSharedWorldTrainingQuickSkill();
          return;
        }
        const skill = sharedWorldTrainingSkillById(key);
        const size = sharedWorldTrainingEffectSize();
        const targetedUltimate = key === "male-ultimate" || key === "female-ultimate";
        const radiusPx = targetedUltimate
          ? Math.max(1, Math.min(size.width, size.height) / 2)
          : Math.max(1, Math.floor(Number(skill.radius_px || skill.radiusPx || 400) || 400));
        const pos = getSharedWorldSelfPosition();
        const host = sharedWorldTrainingSlimeHost();
        const liveSelectedNode = host && host.querySelector ? host.querySelector("[data-slime-id].is-selected") : null;
        const targetSlimeId = clean(liveSelectedNode && liveSelectedNode.dataset && liveSelectedNode.dataset.slimeId
          || (sharedWorldTrainingState && sharedWorldTrainingState.training && sharedWorldTrainingState.training.arena && sharedWorldTrainingState.training.arena.selected_id)
          || "");
        const targetRow = Array.isArray(sharedWorldTrainingState?.training?.arena?.slimes)
          ? sharedWorldTrainingState.training.arena.slimes.find((row) => clean(row && row.id || "") === targetSlimeId)
          : null;
        const viewportNode = host && host.closest ? (host.closest(".ft-world-stage") || host) : host;
        const viewportRect = viewportNode && viewportNode.getBoundingClientRect ? viewportNode.getBoundingClientRect() : null;
        const visibleEnemyIds = host && viewportRect
          ? Array.from(host.querySelectorAll("[data-slime-id]")).filter((node) => {
              const rect = node.getBoundingClientRect();
              return rect.right >= viewportRect.left && rect.left <= viewportRect.right
                && rect.bottom >= viewportRect.top && rect.top <= viewportRect.bottom;
            }).map((node) => clean(node.dataset && node.dataset.slimeId || "")).filter(Boolean)
          : [];
        const result = await postSharedWorldTraining("/world/training/skill", {
          skill: key,
          player_x: sharedWorldClamp(pos.x),
          player_y: sharedWorldClamp(pos.y),
          radius_x: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.width))),
          radius_y: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.height))),
          radius_px: radiusPx,
          target_slime_id: targetSlimeId,
          generation: targetRow ? Math.max(1, Math.floor(Number(targetRow.generation ?? targetRow.respawn_generation ?? 1) || 1)) : 0,
          visible_enemy_ids: visibleEnemyIds,
          client_action_id: `training_skill_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`,
        }, false);
        if (!result) return;
        // 2026-08-11: expose real Nộ HP results separately from the admin visual-only preview.
        const resultArena = result && result.training && result.training.arena && typeof result.training.arena === "object" ? result.training.arena : {};
        const resultTarget = (Array.isArray(resultArena.slimes) ? resultArena.slimes : []).find((row) => clean(row && row.id || "") === targetSlimeId) || null;
        const resultEvent = result && result.training && result.training.event && typeof result.training.event === "object" ? result.training.event : {};
        window.__ftTrainingSkillCastTrace = {
          skillId: key,
          targetSlimeId,
          damage: Math.max(0, Number(resultEvent.damage || 0) || 0),
          targetHp: resultTarget ? Math.max(0, Number(resultTarget.hp || 0) || 0) : null,
          affected: Array.isArray(resultEvent.affected) ? resultEvent.affected.length : 0,
          at: Date.now(),
        };
        console.info("[FTG][TrainingSkillCast]", window.__ftTrainingSkillCastTrace);
        if (result && result.training) {
          const event = result.training.event && typeof result.training.event === "object" ? result.training.event : {};
          startSharedWorldTrainingSkillCooldown(key, Math.max(1, Number(event.cooldown_seconds || event.cooldownSeconds || 10) || 10));
        }
      };

      const resetSharedWorldTraining = () => {
        void postSharedWorldTraining("/world/training/reset", {}, true);
      };

      const sharedWorldCommandListOpen = () => Boolean(worldCommandList && !worldCommandList.hasAttribute("hidden"));

      const sharedWorldTargetLabel = (target) => clean(target && (target.displayName || target.display_name || target.username));

      const sharedWorldInviteProfileLabel = (invite = {}, side = "from") => {
        const row = invite && typeof invite === "object" ? invite : {};
        const profile = row[`${side}_profile`] || row[`${side}Profile`] || {};
        const direct = row[`${side}_display_name`] || row[`${side}DisplayName`] || "";
        const username = clean(row[side] || "");
        const rosterRow = username ? sharedWorldRoster.get(username.toLowerCase()) : null;
        return clean(direct)
          || clean(profile && (profile.display_name || profile.displayName || profile.full_name || profile.fullName))
          || sharedWorldTargetLabel(rosterRow)
          || username
          || "learner";
      };

      const sharedWorldInviteCharacterAvatar = (invite = {}) => {
        const profile = invite && typeof invite === "object"
          ? (invite.from_profile || invite.fromProfile || {})
          : {};
        const kind = normalizeSharedWorldCharacterKind(profile.character_kind || profile.characterKind || profile.gender || "male");
        if (kind === "female") return "/future-assets/character_female_default_avatar_1.png";
        if (kind === "scorpio") return "/future-assets/character_scorpio_avatar.png";
        return "/future-assets/character_male_default_avatar.png";
      };

      const stopSharedWorldBattleInviteCountdown = () => {
        if (sharedWorldBattleInviteCountdownTimer) {
          window.clearInterval(sharedWorldBattleInviteCountdownTimer);
          sharedWorldBattleInviteCountdownTimer = 0;
        }
      };

      // Added 2026-08-16: render a bounded newest-first invite queue with one shared countdown timer.
      const renderSharedWorldBattleInvites = (incomingInvites = [], blocked = false) => {
        stopSharedWorldBattleInviteCountdown();
        if (!worldInvitePanel || !worldInviteList) return;
        const now = Date.now();
        const rows = (blocked || !Array.isArray(incomingInvites) ? [] : incomingInvites)
          .filter((invite) => {
            const expiresMs = Math.max(0, Number(invite && (invite.expires_epoch || invite.expiresEpoch) || 0) * 1000);
            return clean(invite && invite.id || "") && (!expiresMs || expiresMs > now);
          });
        const liveIds = new Set(rows.map((invite) => clean(invite && invite.id || "")).filter(Boolean));
        worldInviteList.querySelectorAll(".ft-world-invite-card[data-invite-id]").forEach((card) => {
          if (!liveIds.has(clean(card.dataset.inviteId))) card.remove();
        });
        rows.forEach((invite) => {
          const inviteId = clean(invite.id);
          const expiresMs = Math.max(0, Number(invite.expires_epoch || invite.expiresEpoch || 0) * 1000);
          let card = Array.from(worldInviteList.querySelectorAll(".ft-world-invite-card[data-invite-id]"))
            .find((node) => clean(node.dataset.inviteId) === inviteId) || null;
          const isNewCard = !card;
          if (!card) {
            card = document.createElement("article");
            card.className = "ft-world-invite-card";
            card.dataset.inviteId = inviteId;
          }
          card.dataset.expiresMs = String(expiresMs || (now + 10000));

          const avatar = card.querySelector(".ft-world-invite-avatar") || document.createElement("img");
          avatar.className = "ft-world-invite-avatar";
          avatar.src = sharedWorldInviteCharacterAvatar(invite);
          avatar.alt = `${sharedWorldInviteProfileLabel(invite, "from")} character`;

          const copy = card.querySelector(".ft-world-invite-copy") || document.createElement("div");
          copy.className = "ft-world-invite-copy";
          const kicker = copy.querySelector(".ft-world-invite-kicker") || document.createElement("span");
          kicker.className = "ft-world-invite-kicker";
          const expiry = kicker.querySelector("[data-invite-expires]") || document.createElement("span");
          expiry.className = "ft-world-invite-expiry";
          expiry.dataset.inviteExpires = "1";
          if (!expiry.parentNode) kicker.append("Battle invite ", expiry);
          const title = copy.querySelector("strong") || document.createElement("strong");
          title.textContent = sharedWorldInviteProfileLabel(invite, "from");
          const message = copy.querySelector("p") || document.createElement("p");
          message.textContent = clean(invite.message) || `Invited you to ${sharedWorldBattleGameLabel(invite.game)}.`;
          if (!title.parentNode) copy.append(kicker, title, message);

          let actions = card.querySelector(".ft-world-invite-actions");
          if (!actions) {
            actions = document.createElement("div");
            actions.className = "ft-world-invite-actions";
            [["accept", "Accept"], ["decline", "Decline"]].forEach(([action, label]) => {
              const button = document.createElement("button");
              button.type = "button";
              button.dataset.worldInviteAction = action;
              button.textContent = label;
              actions.appendChild(button);
            });
          }
          actions.querySelectorAll("[data-world-invite-action]").forEach((button) => {
            button.dataset.inviteId = inviteId;
          });
          if (isNewCard) card.append(avatar, copy, actions);
          // Re-appending an existing node only reorders it; its entrance animation does not replay.
          worldInviteList.appendChild(card);
        });
        const newlyRenderedIds = rows
          .map((invite) => clean(invite && invite.id || ""))
          .filter((inviteId) => inviteId && !sharedWorldBattleInviteSeenIds.has(inviteId));
        if (newlyRenderedIds.length) {
          newlyRenderedIds.forEach((inviteId) => sharedWorldBattleInviteSeenIds.add(inviteId));
          void fetchAuthJson("/world/battle/invite-seen", {
            method: "POST",
            body: JSON.stringify({ invite_ids: newlyRenderedIds, ...activeWorldActorPayload() }),
          }).catch(() => {
            newlyRenderedIds.forEach((inviteId) => sharedWorldBattleInviteSeenIds.delete(inviteId));
          });
        }
        worldInvitePanel.hidden = !rows.length;
        if (!rows.length) {
          sharedWorldBattleInviteId = "";
          return;
        }
        sharedWorldBattleInviteId = clean(rows[0].id);
        const updateCountdowns = () => {
          let expired = false;
          worldInviteList.querySelectorAll(".ft-world-invite-card[data-invite-id]").forEach((card) => {
            const remaining = Math.max(0, Math.ceil((Number(card.dataset.expiresMs || 0) - Date.now()) / 1000));
            const label = card.querySelector("[data-invite-expires]");
            if (label) label.textContent = `${remaining}s`;
            if (remaining <= 0) {
              if (sharedWorldBattleInviteId === clean(card.dataset.inviteId)) sharedWorldBattleInviteId = "";
              card.remove();
              expired = true;
            }
          });
          if (!worldInviteList.children.length) {
            stopSharedWorldBattleInviteCountdown();
            worldInvitePanel.hidden = true;
          }
          if (expired) void refreshSharedWorldBattle();
        };
        updateCountdowns();
        if (!worldInvitePanel.hidden) sharedWorldBattleInviteCountdownTimer = window.setInterval(updateCountdowns, 250);
      };

      const sharedWorldGenderSymbol = (gender = "") => {
        const key = clean(gender).toLowerCase();
        if (key === "female") return "♀︎";
        if (key === "male") return "♂︎";
        return "◇︎";
      };

      const sharedWorldNameKey = (value = "") => clean(value)
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\u0111/g, "d")
        .replace(/\u0110/g, "d")
        .replace(/đ/g, "d")
        .replace(/[^a-z0-9]+/g, " ")
        .trim();

      const setSharedWorldGameListOpen = (open = false) => {
        if (!worldGameButton || !worldGameList) {
          return;
        }
        if (open) {
          worldGameList.removeAttribute("hidden");
        } else {
          worldGameList.setAttribute("hidden", "");
        }
        worldGameButton.setAttribute("aria-expanded", open ? "true" : "false");
      };

      const sharedWorldBattleUserKey = (value = "") => clean(value).toLowerCase();

      const traceSharedWorldPvpTrainingRuntime = (stage = "", detail = {}) => {
        const row = { stage: clean(stage), at: Date.now(), ...(detail && typeof detail === "object" ? detail : {}) };
        const trace = Array.isArray(window.__ftPvpTrainingRuntimeTrace) ? window.__ftPvpTrainingRuntimeTrace : [];
        trace.push(row);
        window.__ftPvpTrainingRuntimeTrace = trace.slice(-120);
        console.info("[FTG][PvPTrainingRuntime]", row);
      };
      traceSharedWorldPvpTrainingRuntime("boot", { version: "training-shared-v2", basic: "triggerSharedWorldTrainingSkill", ultimate: "triggerSharedWorldTrainingEarthquake" });

      const sharedWorldBattlePercent = (value) => {
        const number = Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
        return `${number}%`;
      };

      const sharedWorldBattleGameLabel = (id = "") => {
        const key = clean(id || "fireball_vocab");
        if (key === "fireball_vocab") {
          return "QM-City Character Battle";
        }
        return key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
      };

      const sharedWorldBattleMoveLabel = (effect = "", damage = 0) => {
        const key = clean(effect).toLowerCase();
        const strongDamage = Math.max(0, Math.round(Number(damage) || 0)) >= 30;
        if (key === "inferno" || key === "ultimate" || key === "triple" || strongDamage) return "Skill Nộ";
        if (key === "basic_attack" || key === "basic") return "Đánh thường";
        if (key === "laser") return "Laser Beam";
        if (key === "meteor") return "Meteor Strike";
        if (key === "shield") return "Crystal Guard";
        if (key === "drain") return "Mana Drain";
        if (key === "phoenix" || key === "heal") return "Phoenix Pulse";
        if (key === "fire" || key === "fireball" || key === "laser") return "Đánh thường";
        return key ? key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Đánh thường";
      };

      // 2026-08-13: compact lifecycle evidence for late PvP responses, timers, and duplicate results.
      const traceSharedWorldBattleLifecycle = (stage = "", detail = {}) => {
        const entry = {
          stage: clean(stage),
          generation: sharedWorldBattleLifecycleGeneration,
          battleId: clean(detail && detail.battleId || ""),
          at: Date.now(),
          ...(detail && typeof detail === "object" ? detail : {}),
        };
        const trace = Array.isArray(window.__ftPvpLifecycleTrace) ? window.__ftPvpLifecycleTrace : [];
        trace.push(entry);
        if (trace.length > 120) trace.splice(0, trace.length - 120);
        window.__ftPvpLifecycleTrace = trace;
        window.__ftPvpLifecycleStats = trace.reduce((stats, row) => {
          stats.total += 1;
          stats[row.stage] = (stats[row.stage] || 0) + 1;
          return stats;
        }, { total: 0 });
        console.info("[FTG][PvpLifecycle]", entry);
        return entry;
      };

      const sharedWorldBattleIdClosed = (battleId = "") => {
        const key = clean(battleId);
        if (!key) return false;
        const expiresAt = Number(sharedWorldBattleClosedIds.get(key) || 0);
        if (expiresAt > Date.now()) return true;
        if (expiresAt) sharedWorldBattleClosedIds.delete(key);
        return false;
      };

      const closeSharedWorldBattleLifecycle = (battleId = "", reason = "close") => {
        const key = clean(battleId);
        if (key) sharedWorldBattleClosedIds.set(key, Date.now() + 120000);
        sharedWorldBattleLifecycleGeneration += 1;
        sharedWorldBattleRequestSeq += 1;
        traceSharedWorldBattleLifecycle("closed", { battleId: key, reason: clean(reason) || "close" });
        return sharedWorldBattleLifecycleGeneration;
      };

      // 2026-08-13: one gate for every late Battle response/error after exit or result dismissal.
      const sharedWorldBattleAsyncStillCurrent = (battleId = "", generation = 0, requestSeq = 0) => Boolean(
        generation === sharedWorldBattleLifecycleGeneration
        && (!requestSeq || requestSeq === sharedWorldBattleRequestSeq)
        && !sharedWorldBattleIdClosed(battleId)
        && worldModal
        && worldModal.classList.contains("is-open")
      );

      const stopSharedWorldBattleCountdown = () => {
        if (sharedWorldBattleTimer) {
          window.clearInterval(sharedWorldBattleTimer);
          sharedWorldBattleTimer = 0;
        }
      };

      const queueSharedWorldBattleVisualTimeout = (callback, delayMs = 0) => {
        const generation = sharedWorldBattleLifecycleGeneration;
        const battleId = clean(sharedWorldBattleState && sharedWorldBattleState.battle && sharedWorldBattleState.battle.id || "");
        const id = window.setTimeout(() => {
          sharedWorldBattleVisualTimers.delete(id);
          if (
            generation !== sharedWorldBattleLifecycleGeneration
            || sharedWorldBattleIdClosed(battleId)
            || !worldModal
            || !worldModal.classList.contains("is-open")
            || !worldBattleModal
            || !worldBattleModal.classList.contains("is-open")
          ) {
            traceSharedWorldBattleLifecycle("timer-rejected", { battleId, scheduledGeneration: generation });
            return;
          }
          try {
            callback();
          } catch (error) {
            traceSharedWorldBattleLifecycle("callback-error", {
              battleId,
              message: clean(error && error.message || String(error || "Battle callback failed")),
            });
          }
        }, Math.max(0, Math.round(Number(delayMs) || 0)));
        sharedWorldBattleVisualTimers.add(id);
        return id;
      };

      const clearSharedWorldBattleVisualState = () => {
        sharedWorldBattleVisualTimers.forEach((id) => window.clearTimeout(id));
        sharedWorldBattleVisualTimers.clear();
        if (worldBattleCard) {
          worldBattleCard.classList.remove(
            "is-casting-left",
            "is-casting-right",
            "is-attack-fire",
            "is-attack-laser",
            "is-attack-meteor",
            "is-attack-inferno"
          );
          worldBattleCard.querySelectorAll(".ft-world-battle-heal-burst").forEach((node) => node.remove());
        }
        const combatPlayers = new Set([
          worldBattleLeft,
          worldBattleRight,
          ...document.querySelectorAll(".ft-world-player"),
        ]);
        combatPlayers.forEach((node) => {
          if (!node) {
            return;
          }
          if (node._worldBattleSpeechTimer) {
            window.clearTimeout(node._worldBattleSpeechTimer);
            node._worldBattleSpeechTimer = 0;
          }
          node.classList.remove(
            "is-training-cast",
            "is-training-critical-cast",
            "is-female-ranged-up",
            "is-female-ranged-down",
            "is-female-ranged-left",
            "is-female-ranged-right",
            "is-female-ultimate-cast",
            "is-female-ultimate-left",
            "is-female-ultimate-right",
            "is-male-ultimate-cast",
            "is-male-ultimate-style-5",
            "is-male-ultimate-left",
            "is-male-ultimate-right",
            "is-scorpio-basic-cast",
            "is-scorpio-basic-1",
            "is-scorpio-basic-2",
            "is-scorpio-basic-3",
            "is-scorpio-cast-left",
            "is-scorpio-cast-right",
            "is-scorpio-ultimate-cast",
            "is-scorpio-ultimate-left",
            "is-scorpio-ultimate-right",
            "is-earthquake-cast",
            "is-speaking",
            "is-skill-heal",
            "is-skill-shield",
            "is-skill-drain",
            "is-skill-inferno",
            "is-hit",
            "is-battle-defeated",
            "is-loot-loss",
            "is-loot-gain",
            "is-turn-jump"
          );
          const callout = node.querySelector(".ft-world-battle-callout");
          if (callout) {
            callout.textContent = "";
          }
        });
      };

      // Added 2026-08-14: resume PvP from one current snapshot instead of replaying throttled background animations.
      const releaseSharedWorldBattleCombatRender = (reason = "impact", skipDeferredVisual = false) => {
        sharedWorldBattleCombatRenderLockUntil = 0;
        const deferred = sharedWorldBattleDeferredCombatPayload;
        sharedWorldBattleDeferredCombatPayload = null;
        if (deferred && deferred.battle && skipDeferredVisual) {
          sharedWorldBattleLastLogKey = sharedWorldBattleLatestLogKey(deferred.battle);
        }
        traceSharedWorldPvpTrainingRuntime("combat-render-release", {
          reason,
          deferred: Boolean(deferred),
          skipDeferredVisual: Boolean(skipDeferredVisual),
        });
        const deferredBattleId = clean(deferred && deferred.battle && deferred.battle.id || "");
        if (deferred && (!deferredBattleId || !sharedWorldBattleIdClosed(deferredBattleId))) {
          renderSharedWorldBattle(deferred);
        } else if (deferredBattleId) {
          traceSharedWorldBattleLifecycle("deferred-render-rejected", { battleId: deferredBattleId, reason });
        }
      };

      const handleSharedWorldBattleVisibilityChange = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || !clean(battle.id) || !worldBattleModal || !worldBattleModal.classList.contains("is-open")) return;
        if (document.visibilityState === "hidden") {
          traceSharedWorldPvpTrainingRuntime("background-hidden", { battleId: clean(battle.id) });
          return;
        }
        clearSharedWorldBattleVisualState();
        sharedWorldTrainingCombatOverride = null;
        sharedWorldBattleOptimisticActions.clear();
        releaseSharedWorldBattleCombatRender("visibility-resume", true);
        traceSharedWorldPvpTrainingRuntime("background-resync", { battleId: clean(battle.id) });
        void refreshSharedWorldBattle();
      };

      const updateSharedWorldBattleCountdown = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          if (worldBattleTimer) {
            worldBattleTimer.textContent = "--";
          }
          stopSharedWorldBattleCountdown();
          return;
        }
        const deadlineEpoch = Number(battle.deadline_epoch || battle.deadlineEpoch || 0);
        const serverEpoch = Number(battle.server_epoch || battle.serverEpoch || 0);
        const nowEpoch = serverEpoch > 0 ? serverEpoch + ((Date.now() - Number(sharedWorldBattleState && sharedWorldBattleState.receivedAt || Date.now())) / 1000) : Date.now() / 1000;
        const remaining = deadlineEpoch > 0 ? Math.max(0, Math.ceil(deadlineEpoch - nowEpoch)) : 30;
        if (worldBattleTimer) {
          worldBattleTimer.textContent = String(remaining).padStart(2, "0");
        }
        if (remaining <= 0) {
          queueSharedWorldBattleVisualTimeout(() => void refreshSharedWorldBattle(), 450);
        }
      };

      const startSharedWorldBattleCountdown = () => {
        stopSharedWorldBattleCountdown();
        updateSharedWorldBattleCountdown();
        sharedWorldBattleTimer = window.setInterval(updateSharedWorldBattleCountdown, 1000);
      };

      const sharedWorldBattlePlayersForView = (battle = {}) => {
        const players = Array.isArray(battle.players) ? battle.players.map((item) => clean(item)).filter(Boolean) : [];
        const me = clean(activeWorldUsername());
        const self = players.find((item) => sharedWorldBattleUserKey(item) === sharedWorldBattleUserKey(me)) || players[0] || me;
        const opponent = players.find((item) => sharedWorldBattleUserKey(item) !== sharedWorldBattleUserKey(self)) || players[1] || "";
        return { self, opponent };
      };

      // 2026-08-13: recover a client-first answer if next-question hydration stalls.
      const clearSharedWorldBattleAnswerRecovery = () => {
        if (sharedWorldBattleAnswerRecoveryTimer) {
          window.clearTimeout(sharedWorldBattleAnswerRecoveryTimer);
          sharedWorldBattleAnswerRecoveryTimer = 0;
        }
      };

      const scheduleSharedWorldBattleAnswerRecovery = (battleId = "", pendingKey = "", choiceSignature = "") => {
        clearSharedWorldBattleAnswerRecovery();
        sharedWorldBattleAnswerRecoveryTimer = window.setTimeout(async () => {
          sharedWorldBattleAnswerRecoveryTimer = 0;
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          if (!battle || clean(battle.id) !== clean(battleId) || clean(battle.status) !== "active") return;
          if (!worldBattleChoices || worldBattleChoices.dataset.combatChoiceLocked !== "1") return;
          if (choiceSignature && worldBattleChoices.dataset.combatChoiceSignature !== choiceSignature) return;
          traceSharedWorldBattleLifecycle("answer-lock-recovery", { battleId, pendingKey });
          try {
            await refreshSharedWorldBattle();
          } finally {
            const current = sharedWorldBattleState && sharedWorldBattleState.battle;
            if (!current || clean(current.id) !== clean(battleId) || clean(current.status) !== "active") return;
            if (choiceSignature && worldBattleChoices.dataset.combatChoiceSignature !== choiceSignature) return;
            sharedWorldCombatPendingAnswers.delete(pendingKey);
            worldBattleChoices.dataset.combatChoiceLocked = "0";
            worldBattleChoices.querySelectorAll("[data-combat-choice]").forEach((button) => {
              button.disabled = false;
              button.classList.remove("is-correct-preview", "is-wrong-preview");
            });
            traceSharedWorldBattleLifecycle("answer-lock-released", { battleId, pendingKey });
          }
        }, 3600);
      };

      // Added 2026-08-11: Battle actors use the same orthogonal run loop as the Training map.
      const setSharedWorldBattleActorFacing = (node, from = {}, to = {}) => {
        if (!node) return;
        const dx = Number(to.x || 0) - Number(from.x || 0);
        const dy = Number(to.y || 0) - Number(from.y || 0);
        let facing = "down";
        if (Math.abs(dx) >= Math.abs(dy) && Math.abs(dx) > 0.00001) facing = dx < 0 ? "left" : "right";
        else if (Math.abs(dy) > 0.00001) facing = dy < 0 ? "up" : "down";
        ["left", "right", "up", "down"].forEach((name) => node.classList.toggle(`is-facing-${name}`, name === facing));
        const character = node.querySelector(".ft-world-battle-character-sprite");
        if (character) character.style.setProperty("--world-facing", facing === "left" ? "-1" : "1");
      };

      // Added 2026-08-16: lower grounded shadows must win the actor stacking order in PvP.
      const refreshSharedWorldBattleCharacterDepthOrder = () => {
        [worldBattleLeft, worldBattleRight]
          .filter(Boolean)
          .sort((left, right) => {
            const yDelta = Number(left.dataset.battleY || 0) - Number(right.dataset.battleY || 0);
            if (Math.abs(yDelta) > 0.000001) return yDelta;
            return clean(left.dataset.slimeId || left.dataset.username).localeCompare(clean(right.dataset.slimeId || right.dataset.username));
          })
          .forEach((node, index) => {
            node.style.zIndex = String(12 + index);
          });
      };

      const sharedWorldBattleMapSize = () => ({ width: 1672, height: 941 });

      const sharedWorldBattleObstacleSegmentDistancePx = (point, start, end) => {
        const { width, height } = sharedWorldBattleMapSize();
        const px = Number(point.x) * width;
        const py = Number(point.y) * height;
        const ax = Number(start.x) * width;
        const ay = Number(start.y) * height;
        const bx = Number(end.x) * width;
        const by = Number(end.y) * height;
        const dx = bx - ax;
        const dy = by - ay;
        const lengthSquared = dx * dx + dy * dy;
        const ratio = lengthSquared > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSquared)) : 0;
        return Math.hypot(px - (ax + dx * ratio), py - (ay + dy * ratio));
      };

      // Added 2026-08-12: Battle actors collide with the Battle Pen snapshot, excluding portal regions.
      const sharedWorldBattlePointBlocked = (point, characterRadius = 18) => sharedWorldBattleObstacles.strokes.some((stroke) => {
        if (clean(stroke.kind).toLowerCase() === "portal") return false;
        const points = Array.isArray(stroke.points) ? stroke.points : [];
        const limit = Math.max(6, Number(stroke.size) || 32) / 2 + Math.max(0, characterRadius);
        for (let index = 1; index < points.length; index += 1) {
          if (sharedWorldBattleObstacleSegmentDistancePx(point, points[index - 1], points[index]) <= limit) return true;
        }
        return false;
      });

      const sharedWorldBattleFindEscapePoint = (point, characterRadius = 18) => {
        const origin = { x: sharedWorldClamp(point && point.x), y: sharedWorldClamp(point && point.y) };
        if (!sharedWorldBattlePointBlocked(origin, characterRadius)) return origin;
        const { width, height } = sharedWorldBattleMapSize();
        const centreVector = { x: (0.5 - origin.x) * width, y: (0.5 - origin.y) * height };
        const centreLength = Math.hypot(centreVector.x, centreVector.y);
        const directions = centreLength > 0.001
          ? [{ x: centreVector.x / centreLength, y: centreVector.y / centreLength }]
          : [];
        for (let index = 0; index < 24; index += 1) {
          const angle = (Math.PI * 2 * index) / 24;
          directions.push({ x: Math.cos(angle), y: Math.sin(angle) });
        }
        for (let radiusPx = 6; radiusPx <= 720; radiusPx += 6) {
          for (const direction of directions) {
            const candidate = {
              x: sharedWorldClamp(origin.x + (direction.x * radiusPx) / width),
              y: sharedWorldClamp(origin.y + (direction.y * radiusPx) / height),
            };
            if (!sharedWorldBattlePointBlocked(candidate, characterRadius)) return candidate;
          }
        }
        return origin;
      };

      const sharedWorldBattleSegmentClear = (start, end, characterRadius = 18) => {
        const { width, height } = sharedWorldBattleMapSize();
        const distancePx = Math.hypot((end.x - start.x) * width, (end.y - start.y) * height);
        const steps = Math.max(1, Math.min(420, Math.ceil(distancePx / 5)));
        for (let index = 1; index <= steps; index += 1) {
          const ratio = index / steps;
          if (sharedWorldBattlePointBlocked({
            x: start.x + (end.x - start.x) * ratio,
            y: start.y + (end.y - start.y) * ratio,
          }, characterRadius)) return false;
        }
        return true;
      };

      const sharedWorldMakeBattleOrthogonalPath = (start = {}, target = {}, characterRadius = 18) => {
        const startPoint = { x: sharedWorldClamp(start.x), y: sharedWorldClamp(start.y) };
        const escapeStart = sharedWorldBattleFindEscapePoint(startPoint, characterRadius);
        const goal = sharedWorldBattleFindEscapePoint(target, characterRadius);
        const prefix = Math.hypot(escapeStart.x - startPoint.x, escapeStart.y - startPoint.y) > 0.0005 ? [escapeStart] : [];
        const axisCandidates = [
          [{ x: goal.x, y: escapeStart.y }, goal],
          [{ x: escapeStart.x, y: goal.y }, goal],
        ];
        for (const candidate of axisCandidates) {
          const compact = candidate.filter((point, index) => {
            const previous = index ? candidate[index - 1] : escapeStart;
            return Math.hypot(point.x - previous.x, point.y - previous.y) > 0.0005;
          });
          if (compact.every((point, index) => sharedWorldBattleSegmentClear(index ? compact[index - 1] : escapeStart, point, characterRadius))) {
            return prefix.concat(compact);
          }
        }
        const columns = 84;
        const rows = 44;
        const minX = 0.025;
        const maxX = 0.975;
        const minY = 0.04;
        const maxY = 0.96;
        const toPoint = (column, row) => ({
          x: minX + (column / (columns - 1)) * (maxX - minX),
          y: minY + (row / (rows - 1)) * (maxY - minY),
        });
        const toCell = (point) => ({
          column: Math.max(0, Math.min(columns - 1, Math.round(((point.x - minX) / (maxX - minX)) * (columns - 1)))),
          row: Math.max(0, Math.min(rows - 1, Math.round(((point.y - minY) / (maxY - minY)) * (rows - 1)))),
        });
        const nearestFreeCell = (point) => {
          const base = toCell(point);
          for (let radius = 0; radius < Math.max(columns, rows); radius += 1) {
            for (let row = base.row - radius; row <= base.row + radius; row += 1) {
              for (let column = base.column - radius; column <= base.column + radius; column += 1) {
                if (column < 0 || row < 0 || column >= columns || row >= rows) continue;
                const candidate = toPoint(column, row);
                if (!sharedWorldBattlePointBlocked(candidate, characterRadius)) return { column, row };
              }
            }
          }
          return base;
        };
        const startCell = nearestFreeCell(escapeStart);
        const goalCell = nearestFreeCell(goal);
        const cellId = (column, row) => row * columns + column;
        const startId = cellId(startCell.column, startCell.row);
        const goalId = cellId(goalCell.column, goalCell.row);
        const open = [{ ...startCell, id: startId, g: 0, f: 0 }];
        const cameFrom = new Map();
        const cost = new Map([[startId, 0]]);
        const neighbours = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        let found = false;
        while (open.length && cameFrom.size < 6000) {
          open.sort((left, right) => left.f - right.f);
          const current = open.shift();
          if (current.id === goalId) { found = true; break; }
          for (const [deltaColumn, deltaRow] of neighbours) {
            const column = current.column + deltaColumn;
            const row = current.row + deltaRow;
            if (column < 0 || row < 0 || column >= columns || row >= rows) continue;
            const nextPoint = toPoint(column, row);
            const currentPoint = toPoint(current.column, current.row);
            if (sharedWorldBattlePointBlocked(nextPoint, characterRadius) || !sharedWorldBattleSegmentClear(currentPoint, nextPoint, characterRadius)) continue;
            const id = cellId(column, row);
            const nextCost = current.g + 1;
            if (nextCost >= (cost.get(id) ?? Infinity)) continue;
            cost.set(id, nextCost);
            cameFrom.set(id, current.id);
            const heuristic = Math.abs(column - goalCell.column) + Math.abs(row - goalCell.row);
            open.push({ column, row, id, g: nextCost, f: nextCost + heuristic });
          }
        }
        if (!found) return prefix;
        const cells = [goalId];
        while (cells[0] !== startId && cameFrom.has(cells[0])) cells.unshift(cameFrom.get(cells[0]));
        const rawPath = cells.slice(1).map((id) => toPoint(id % columns, Math.floor(id / columns)));
        const path = [];
        let previous = escapeStart;
        let previousAxis = "";
        rawPath.forEach((point) => {
          const axis = Math.abs(point.x - previous.x) >= Math.abs(point.y - previous.y) ? "x" : "y";
          if (previousAxis && axis !== previousAxis) path.push(previous);
          previousAxis = axis;
          previous = point;
        });
        if (rawPath.length) path.push(rawPath[rawPath.length - 1]);
        if (sharedWorldBattleSegmentClear(path[path.length - 1] || escapeStart, goal, characterRadius)) path.push(goal);
        return prefix.concat(path);
      };

      const rescueSharedWorldBattleBlockedActors = () => {
        sharedWorldBattleActorPoints.forEach((point, key) => {
          if (!sharedWorldBattlePointBlocked(point)) return;
          const escape = sharedWorldBattleFindEscapePoint(point);
          sharedWorldBattleActorTargets.delete(key);
          queueSharedWorldBattleActorPath(key, escape, point);
        });
      };

      const queueSharedWorldBattleActorPath = (username = "", destination = {}, currentOverride = null) => {
        const key = sharedWorldBattleUserKey(username);
        if (!key) return null;
        const current = currentOverride || sharedWorldBattleActorPoints.get(key) || destination;
        const requestedTarget = { x: sharedWorldClamp(destination.x, current.x), y: sharedWorldClamp(destination.y, current.y) };
        const target = sharedWorldBattleFindEscapePoint(requestedTarget);
        const previous = sharedWorldBattleActorTargets.get(key);
        const activeQueue = sharedWorldBattlePathQueues.get(key);
        if (previous && Array.isArray(activeQueue) && activeQueue.length && Math.hypot(previous.x - target.x, previous.y - target.y) < 0.0005) return target;
        sharedWorldBattleActorTargets.set(key, target);
        const queue = sharedWorldMakeBattleOrthogonalPath(current, target);
        if (queue.length) sharedWorldBattlePathQueues.set(key, queue);
        else sharedWorldBattlePathQueues.delete(key);
        if (!sharedWorldBattleMotionFrame) {
          sharedWorldBattleMotionLastAt = performance.now();
          sharedWorldBattleMotionFrame = window.requestAnimationFrame(runSharedWorldBattleMotion);
        }
        return target;
      };

      const runSharedWorldBattleMotion = (now) => {
        sharedWorldBattleMotionFrame = 0;
        if (!worldBattleModal || !worldBattleModal.classList.contains("is-open")) {
          sharedWorldBattlePathQueues.clear();
          return;
        }
        const dt = Math.min(0.05, Math.max(0.001, (now - sharedWorldBattleMotionLastAt) / 1000));
        sharedWorldBattleMotionLastAt = now;
        let moving = false;
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        sharedWorldBattlePathQueues.forEach((queue, key) => {
          const node = sharedWorldBattleNodeForUser(key, battle || {});
          const current = sharedWorldBattleActorPoints.get(key);
          const target = Array.isArray(queue) ? queue[0] : null;
          if (!node || !current || !target) {
            if (node) node.classList.remove("is-moving");
            return;
          }
          if (node.classList.contains("is-training-cast")) {
            node.classList.remove("is-moving");
            moving = true;
            return;
          }
          const mapRect = worldBattleMap ? worldBattleMap.getBoundingClientRect() : { width: 1672, height: 941 };
          const dx = target.x - current.x;
          const dy = target.y - current.y;
          const distancePx = Math.hypot(dx * mapRect.width, dy * mapRect.height);
          const stepPx = 285 * dt;
          const ratio = distancePx > stepPx ? stepPx / distancePx : 1;
          const next = { x: current.x + dx * ratio, y: current.y + dy * ratio };
          if (!sharedWorldBattlePointBlocked(current) && sharedWorldBattlePointBlocked(next)) {
            const destination = sharedWorldBattleActorTargets.get(key) || current;
            sharedWorldBattleActorTargets.delete(key);
            queueSharedWorldBattleActorPath(key, destination, current);
            moving = true;
            return;
          }
          sharedWorldBattleActorPoints.set(key, next);
          node.style.left = `${(next.x * 100).toFixed(3)}%`;
          node.style.top = `${(next.y * 100).toFixed(3)}%`;
          node.dataset.battleX = String(next.x);
          node.dataset.battleY = String(next.y);
          node.classList.add("is-moving");
          setSharedWorldBattleActorFacing(node, current, target);
          if (ratio >= 1) queue.shift();
          if (!queue.length) node.classList.remove("is-moving");
          else moving = true;
          const { self } = sharedWorldBattlePlayersForView(battle || {});
          if (key === sharedWorldBattleUserKey(self) && ratio >= 1 && !queue.length) {
            hideSharedWorldBattleMoveMarker(true);
          }
        });
        refreshSharedWorldBattleCharacterDepthOrder();
        if (moving || Array.from(sharedWorldBattlePathQueues.values()).some((queue) => Array.isArray(queue) && queue.length)) {
          sharedWorldBattleMotionFrame = window.requestAnimationFrame(runSharedWorldBattleMotion);
        }
      };

      const renderSharedWorldBattlePlayer = (node, battle = {}, username = "", side = "left") => {
        if (!node) {
          return;
        }
        const userKey = clean(username);
        const profiles = battle.profiles && typeof battle.profiles === "object" ? battle.profiles : {};
        const profile = profiles[userKey] || profiles[sharedWorldBattleUserKey(userKey)] || {};
        const displayName = clean(profile.display_name || profile.displayName || userKey || "Learner");
        const level = Math.max(1, Math.floor(Number(profile.level || 1) || 1));
        const profileGenderKey = normalizeSharedWorldCharacterKind(profile.character_kind || profile.characterKind || profile.gender || "male");
        const genderKey = side === "left" && sharedWorldObstacleEditorAllowed() && sharedWorldAdminCharacterPreview
          ? sharedWorldAdminCharacterPreview
          : profileGenderKey;
        const avatarUrl = genderKey === "female"
          ? "/future-assets/character_female_default_avatar_1.png"
          : genderKey === "scorpio"
            ? "/future-assets/character_scorpio_avatar.png"
            : "/future-assets/character_male_default_avatar.png";
        const hp = Math.max(0, Math.min(100, Math.round(Number((battle.hp || {})[userKey] ?? 100) || 0)));
        const mp = Math.max(0, Math.min(100, Math.round(Number((battle.mp || {})[userKey] ?? 0) || 0)));
        const turn = sharedWorldBattleUserKey(battle.turn) === sharedWorldBattleUserKey(userKey);
        const positions = battle.positions && typeof battle.positions === "object" ? battle.positions : {};
        const fallbackPoint = side === "left" ? { x: 0.22, y: 0.68 } : { x: 0.78, y: 0.68 };
        const rawPoint = positions[userKey] || positions[sharedWorldBattleUserKey(userKey)] || fallbackPoint;
        const point = {
          x: sharedWorldClamp(rawPoint && rawPoint.x, fallbackPoint.x),
          y: sharedWorldClamp(rawPoint && rawPoint.y, fallbackPoint.y),
        };
        const actorKey = sharedWorldBattleUserKey(userKey);
        const npcKeys = new Set((Array.isArray(battle.npc_bots) ? battle.npc_bots : []).map((item) => sharedWorldBattleUserKey(item)).filter(Boolean));
        const clientNpc = npcKeys.has(actorKey);
        let clientNpcPoint = null;
        if (clientNpc) {
          let motion = sharedWorldBattleNpcMotion.get(actorKey);
          if (!motion) {
            const seed = sharedWorldNpcHash(`${activeWorldUsername()}|battle|${actorKey}|${clean(battle.id)}`);
            motion = {
              point: { x: 0.58 + ((seed & 255) / 255) * 0.26, y: 0.24 + (((seed >>> 8) & 255) / 255) * 0.55 },
              target: null,
              attacks: 0,
              threshold: 1 + (seed % 3),
              moveAfter: 0,
            };
            sharedWorldBattleNpcMotion.set(actorKey, motion);
          }
          const recent = Array.isArray(battle.log) ? battle.log.slice(-8) : [];
          const latestAttackKey = recent.map((row) => clean(row && (row.event_id || row.eventId || `${row.at}|${row.type}|${row.text}`))).reverse().find((key, index) => {
            const row = recent[recent.length - 1 - index] || {};
            return clean(row.attacker || row.caster) === userKey && ["hit", "skill"].includes(clean(row.type));
          }) || "";
          if (latestAttackKey && motion.lastAttackKey !== latestAttackKey) {
            motion.lastAttackKey = latestAttackKey;
            motion.attacks += 1;
            if (motion.attacks >= motion.threshold) motion.moveAfter = Date.now() + 800;
          }
          if (motion.moveAfter && Date.now() >= motion.moveAfter && !motion.target) {
            const salt = sharedWorldNpcHash(`${actorKey}|${motion.lastAttackKey}|${motion.threshold}`);
            motion.target = { x: 0.54 + ((salt & 255) / 255) * 0.38, y: 0.20 + (((salt >>> 8) & 255) / 255) * 0.63 };
            motion.attacks = 0;
            motion.threshold = 1 + ((salt >>> 16) % 3);
            motion.moveAfter = 0;
          }
          if (motion.target) {
            const currentPoint = sharedWorldBattleActorPoints.get(actorKey) || motion.point;
            const legalTarget = queueSharedWorldBattleActorPath(userKey, motion.target, currentPoint);
            motion.point = legalTarget || currentPoint;
            motion.target = null;
          }
          clientNpcPoint = sharedWorldBattleActorPoints.get(actorKey) || motion.point;
        }
        const displayedPoint = sharedWorldBattleActorPoints.get(actorKey);
        if (!displayedPoint) {
          const initialPoint = sharedWorldBattleFindEscapePoint(clientNpcPoint || point);
          sharedWorldBattleActorPoints.set(actorKey, initialPoint);
          sharedWorldBattleActorTargets.set(actorKey, initialPoint);
          node.style.left = `${(initialPoint.x * 100).toFixed(3)}%`;
          node.style.top = `${(initialPoint.y * 100).toFixed(3)}%`;
        } else if (!clientNpc) {
          queueSharedWorldBattleActorPath(userKey, point, displayedPoint);
        }
        const activePoint = sharedWorldBattleActorPoints.get(actorKey) || point;
        node.dataset.battleX = String(activePoint.x);
        node.dataset.battleY = String(activePoint.y);
        node.dataset.slimeId = userKey;
        node.classList.add("ft-world-player");
        node.classList.toggle("is-turn", turn);
        node.classList.toggle("is-left", side === "left");
        node.classList.toggle("is-right", side !== "left");
        node.classList.toggle("is-self", side === "left");
        node.classList.toggle("is-opponent", side !== "left");
        node.classList.toggle("is-target-selected", side !== "left" && sharedWorldBattleUserKey(sharedWorldBattleSelectedTarget) === actorKey);
        node.classList.toggle("is-character-male-default", genderKey === "male");
        node.classList.toggle("is-character-female-default", genderKey === "female");
        node.classList.toggle("is-character-scorpio", genderKey === "scorpio");
        node.classList.toggle("is-healthy", hp >= 70);
        node.classList.toggle("is-wounded", hp < 70 && hp >= 40);
        node.classList.toggle("is-critical", hp < 40);
        // Updated 2026-08-16: a reused PvP node must not retain the previous battle's defeated vanish state.
        if (clean(battle.status) === "active" && hp > 0) {
          node.classList.remove("is-battle-defeated");
          node.style.removeProperty("visibility");
          node.style.removeProperty("opacity");
        }
        node.style.setProperty("--battle-hit-x-pre", side === "left" ? "10px" : "-10px");
        node.style.setProperty("--battle-hit-x-full", side === "left" ? "-46px" : "46px");
        node.style.setProperty("--battle-hit-x-land", side === "left" ? "-28px" : "28px");
        node.style.setProperty("--battle-hit-x-recoil", side === "left" ? "8px" : "-8px");
        node.style.setProperty("--battle-hit-rotate-pre", side === "left" ? "10deg" : "-10deg");
        node.style.setProperty("--battle-hit-rotate-full", side === "left" ? "-18deg" : "18deg");
        node.style.setProperty("--battle-hit-rotate-land", side === "left" ? "-13deg" : "13deg");
        node.style.setProperty("--battle-hit-rotate-recoil", side === "left" ? "5deg" : "-5deg");
        node.style.setProperty("--battle-smoke-x-a", side === "left" ? "8px" : "-8px");
        node.style.setProperty("--battle-smoke-x-b", side === "left" ? "16px" : "-16px");
        node.style.setProperty("--battle-smoke-x-c", side === "left" ? "28px" : "-28px");
        const hpTier = Math.max(0, Math.min(9, Math.floor((100 - hp) / 10)));
        for (let index = 0; index < 10; index += 1) {
          node.classList.toggle(`is-hp-tier-${index}`, index === hpTier);
        }
        node.classList.toggle("is-self-turn", turn && side === "left");
        const otherName = (Array.isArray(battle.players) ? battle.players : []).find((name) => sharedWorldBattleUserKey(name) !== sharedWorldBattleUserKey(userKey));
        const otherRawPoint = otherName ? (positions[otherName] || positions[sharedWorldBattleUserKey(otherName)]) : null;
        const facing = otherRawPoint && Number(otherRawPoint.x) < point.x ? "-1" : "1";
        if (!node.classList.contains("is-moving")) {
          setSharedWorldBattleActorFacing(node, activePoint, otherRawPoint || { x: activePoint.x + (side === "left" ? 1 : -1), y: activePoint.y });
        }
        const renderKey = [userKey, displayName, avatarUrl, genderKey, side].join("|");
        if (node.dataset.battlePlayerRenderKey !== renderKey || !node.querySelector(".ft-world-battle-character-sprite")) {
          node.dataset.battlePlayerRenderKey = renderKey;
          node.innerHTML = `
            <div class="ft-world-battle-player-head">
              <div class="ft-world-battle-avatar">
                <span>${escapeHtml(displayName.slice(0, 1).toUpperCase() || "?")}</span>
                <img src="${escapeHtml(avatarUrl)}" alt="${genderKey === "female" ? "Female default" : genderKey === "scorpio" ? "Cung Bọ Cạp" : "Male default"}" onerror="this.style.display='none'">
              </div>
              <div class="ft-world-battle-name">
                <strong title="${escapeHtml(displayName)}">${escapeHtml(displayName)}</strong>
                <span>Lv ${level}${turn ? " · Turn" : ""}</span>
              </div>
            </div>
            <div class="ft-world-battle-character" aria-hidden="true">
              <span class="ft-world-battle-callout"></span>
              <span class="ft-world-character-shadow" aria-hidden="true"></span>
              <div class="ft-world-battle-character-sprite ft-world-character is-${genderKey}-default" style="--world-facing:${facing}">
                <span class="ft-world-battle-crystal-loot is-gain"><b>+1</b></span>
                <span class="ft-world-battle-crystal-loot is-loss"><b>-1</b></span>
              </div>
            </div>
            <div class="ft-world-battle-stats">
              <div class="ft-world-battle-meter is-hp">
                <div class="ft-world-battle-meter-label"><span>HP</span><b></b></div>
                <div class="ft-world-battle-meter-track"><span></span></div>
              </div>
              <div class="ft-world-battle-meter is-mp">
                <div class="ft-world-battle-meter-label"><span>MP</span><b></b></div>
                <div class="ft-world-battle-meter-track"><span></span></div>
              </div>
            </div>
          `;
        }
        const character = node.querySelector(".ft-world-battle-character-sprite");
        if (character) {
          character.style.setProperty("--world-facing", facing);
          character.classList.toggle("is-male-default", genderKey === "male");
          character.classList.toggle("is-female-default", genderKey === "female");
          character.classList.toggle("is-scorpio", genderKey === "scorpio");
          if (!character.dataset.battleRunListener) {
            character.dataset.battleRunListener = "1";
            character.addEventListener("animationiteration", (event) => {
              if (!node.classList.contains("is-character-female-default") || !node.classList.contains("is-moving")) return;
              if (event.animationName === "ftWorldCharacterFemaleRunEffectFive" || event.animationName === "ftWorldCharacterFemaleRunEffectSix") {
                node.classList.toggle("is-female-run-effect-six", Math.random() >= 0.5);
              }
            });
          }
        }
        const statusNode = node.querySelector(".ft-world-battle-name span");
        if (statusNode) {
          statusNode.textContent = `Lv ${level}${turn ? " · Turn" : ""}`;
        }
        const hpMeter = node.querySelector(".ft-world-battle-meter.is-hp");
        if (hpMeter) {
          hpMeter.style.setProperty("--meter-value", sharedWorldBattlePercent(hp));
          const hpValue = hpMeter.querySelector(".ft-world-battle-meter-label b");
          if (hpValue) hpValue.textContent = `${hp}/100`;
        }
        const mpMeter = node.querySelector(".ft-world-battle-meter.is-mp");
        if (mpMeter) {
          mpMeter.style.setProperty("--meter-value", sharedWorldBattlePercent(mp));
          const mpValue = mpMeter.querySelector(".ft-world-battle-meter-label b");
          if (mpValue) mpValue.textContent = `${mp}/100`;
        }
        refreshSharedWorldBattleCharacterDepthOrder();
      };

      const sharedWorldBattleNodeForUser = (username = "", battle = {}) => {
        const { self, opponent } = sharedWorldBattlePlayersForView(battle || {});
        if (sharedWorldBattleUserKey(username) === sharedWorldBattleUserKey(self)) {
          return worldBattleLeft;
        }
        if (sharedWorldBattleUserKey(username) === sharedWorldBattleUserKey(opponent)) {
          return worldBattleRight;
        }
        return null;
      };

      // 2026-08-12: measure the live actor HUD so cast labels never overlap its name or meters.
      const positionSharedWorldBattleCalloutAboveHud = (node = null, callout = null) => {
        const character = node && node.querySelector(".ft-world-battle-character");
        const stats = node && node.querySelector(".ft-world-battle-stats");
        const head = node && node.querySelector(".ft-world-battle-player-head");
        if (!character || !callout || (!stats && !head)) return false;
        const characterRect = character.getBoundingClientRect();
        const hudTop = Math.min(...[stats, head].filter(Boolean).map((hud) => hud.getBoundingClientRect().top));
        const calloutHeight = Math.max(34, callout.offsetHeight || 0);
        const top = hudTop - characterRect.top - calloutHeight - 28;
        callout.style.setProperty("--battle-callout-top", `${Math.round(top)}px`);
        window.__ftPvpCalloutHudTrace = {
          hudTop: Math.round(hudTop),
          characterTop: Math.round(characterRect.top),
          calloutHeight: Math.round(calloutHeight),
          calloutTop: Math.round(top),
          clearance: 28,
          at: Date.now(),
        };
        console.info("[FTG][PvpCalloutHud]", window.__ftPvpCalloutHudTrace);
        return true;
      };

      const triggerSharedWorldBattleSpeech = (username = "", label = "", duration = 2050) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(username, battle || {});
        if (!node) {
          return;
        }
        const callout = node.querySelector(".ft-world-battle-callout");
        if (callout) {
          callout.textContent = clean(label) || "Cast";
          positionSharedWorldBattleCalloutAboveHud(node, callout);
        }
        if (node._worldBattleSpeechTimer) {
          window.clearTimeout(node._worldBattleSpeechTimer);
          node._worldBattleSpeechTimer = 0;
        }
        node.classList.remove("is-speaking");
        void node.offsetWidth;
        node.classList.add("is-speaking");
        node._worldBattleSpeechTimer = queueSharedWorldBattleVisualTimeout(() => {
          node.classList.remove("is-speaking");
          if (callout) {
            callout.textContent = "";
          }
          node._worldBattleSpeechTimer = 0;
        }, Math.max(900, Math.round(Number(duration) || 2050)));
      };

      // Added 2026-08-11: fly the supplied default-character attack art between the two live PvP actors.
      const triggerSharedWorldBattleProjectile = (attackerNode, targetNode, gender = "male", ultimate = false, impactDelay = 720, missed = false, missMeta = {}) => {
        if (!worldBattleCard || !attackerNode || !targetNode) {
          return;
        }
        const visualGender = gender === "scorpio" ? "male" : gender;
        const source = attackerNode.querySelector(".ft-world-battle-character-sprite") || attackerNode;
        const target = targetNode.querySelector(".ft-world-battle-character-sprite") || targetNode;
        const cardRect = worldBattleCard.getBoundingClientRect();
        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const startX = sourceRect.left - cardRect.left + (sourceRect.width / 2);
        const startY = sourceRect.top - cardRect.top + (sourceRect.height * 0.46);
        const targetX = targetRect.left - cardRect.left + (targetRect.width / 2);
        const targetY = targetRect.top - cardRect.top + (targetRect.height * 0.44);
        const missSide = clean(missMeta && (missMeta.impact_offset_side || missMeta.impactOffsetSide || missMeta.side || "")).toLowerCase();
        const missDirection = missSide === "left" ? -1 : (missSide === "right" ? 1 : (targetX >= startX ? 1 : -1));
        const offsetX = Number(missMeta && (missMeta.impact_offset_x != null ? missMeta.impact_offset_x : missMeta.impactOffsetX));
        const offsetY = Number(missMeta && (missMeta.impact_offset_y != null ? missMeta.impact_offset_y : missMeta.impactOffsetY));
        const nearMissX = Number.isFinite(offsetX) && Math.abs(offsetX) > 0.001
          ? Math.max(66, Math.min(132, Math.abs(offsetX) * Math.max(cardRect.width, 1)))
          : Math.max(76, targetRect.width * 0.62);
        const nearMissY = Number.isFinite(offsetY)
          ? offsetY * Math.max(cardRect.height, 1)
          : -Math.max(24, targetRect.height * 0.16);
        const endX = missed ? targetX + (missDirection * nearMissX) : targetX;
        const endY = missed ? targetY + nearMissY : targetY;
        const dx = endX - startX;
        const dy = endY - startY;
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        const shot = document.createElement("span");
        shot.className = `ft-world-battle-character-shot is-${visualGender}${ultimate ? " is-ultimate" : " is-basic"}`;
        shot.style.left = `${startX}px`;
        shot.style.top = `${startY}px`;
        shot.style.setProperty("--battle-shot-dx", `${dx}px`);
        shot.style.setProperty("--battle-shot-dy", `${dy}px`);
        shot.style.setProperty("--battle-shot-angle", `${angle.toFixed(2)}deg`);
        shot.style.setProperty("--battle-shot-duration", `${Math.max(320, impactDelay)}ms`);
        worldBattleCard.appendChild(shot);
        queueSharedWorldBattleVisualTimeout(() => shot.remove(), impactDelay + 120);
        queueSharedWorldBattleVisualTimeout(() => {
          if (!worldBattleCard) {
            return;
          }
          const impact = document.createElement("span");
          impact.className = `ft-world-battle-character-impact is-${visualGender}${ultimate ? " is-ultimate" : " is-basic"}${missed ? " is-miss" : ""}`;
          impact.style.left = `${endX}px`;
          impact.style.top = `${endY}px`;
          worldBattleCard.appendChild(impact);
          if (missed) {
            const miss = document.createElement("span");
            miss.className = "ft-world-battle-miss-label";
            miss.textContent = "MISS";
            miss.style.left = `${endX}px`;
            miss.style.top = `${endY - Math.max(34, targetRect.height * 0.26)}px`;
            worldBattleCard.appendChild(miss);
            queueSharedWorldBattleVisualTimeout(() => miss.remove(), 860);
          }
          queueSharedWorldBattleVisualTimeout(() => impact.remove(), ultimate ? 1180 : 760);
        }, impactDelay);
      };

      const renderSharedWorldBattleCombatHud = (battle = {}, self = "") => {
        if (!worldTrainingSkillDock || !worldBattleCard) return;
        const battlePreferredKind = clean(battle.preferred_question_kind || "");
        if (battlePreferredKind && sharedWorldTrainingBasicSkillDefinitions.some((skill) => skill.kind === battlePreferredKind)) {
          sharedWorldTrainingBasicSkillKind = battlePreferredKind;
        }
        const battleLoadout = Array.isArray(battle.basic_skill_loadout) ? battle.basic_skill_loadout : null;
        if (battleLoadout && typeof sharedWorldTrainingNormalizeBasicLoadout === "function") {
          const nextLoadout = sharedWorldTrainingNormalizeBasicLoadout(battleLoadout);
          if (nextLoadout.some(Boolean) || !sharedWorldTrainingBasicLoadout.some(Boolean)) sharedWorldTrainingBasicLoadout = nextLoadout;
        }
        const battleId = clean(battle.id);
        if (battleId && sharedWorldBattleLoadoutHydratedId !== battleId && sharedWorldBattleLoadoutHydratingId !== battleId
          && typeof loadSharedWorldTrainingInventorySnapshot === "function") {
          sharedWorldBattleLoadoutHydratingId = battleId;
          void loadSharedWorldTrainingInventorySnapshot().finally(() => {
            sharedWorldBattleLoadoutHydratingId = "";
            sharedWorldBattleLoadoutHydratedId = battleId;
            if (sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.id) === battleId) {
              const currentBattle = sharedWorldBattleState.battle;
              const currentKind = clean(currentBattle.preferred_question_kind || "");
              if (currentKind) sharedWorldTrainingBasicSkillKind = currentKind;
              renderSharedWorldBattleCombatHud(currentBattle, self);
            }
          });
        }
        if (!sharedWorldBattleTrainingDockHomeParent) {
          sharedWorldBattleTrainingDockHomeParent = worldTrainingSkillDock.parentNode;
          sharedWorldBattleTrainingDockHomeNext = worldTrainingSkillDock.nextSibling;
        }
        if (worldTrainingSkillDock.parentNode !== worldBattleCard) worldBattleCard.appendChild(worldTrainingSkillDock);
        const profiles = battle.profiles && typeof battle.profiles === "object" ? battle.profiles : {};
        const profile = profiles[self] || profiles[sharedWorldBattleUserKey(self)] || {};
        const profileGenderKey = normalizeSharedWorldCharacterKind(profile.character_kind || profile.characterKind || profile.gender || "male");
        const genderKey = sharedWorldBattleUserKey(self) === "hung" && sharedWorldObstacleEditorAllowed() && sharedWorldAdminCharacterPreview
          ? sharedWorldAdminCharacterPreview
          : profileGenderKey;
        const hp = Math.max(0, Math.min(100, Math.round(Number((battle.hp || {})[self] ?? 100) || 0)));
        const mp = Math.max(0, Math.min(100, Math.round(Number((battle.mp || {})[self] ?? 0) || 0)));
        const level = Math.max(1, Math.floor(Number(profile.level || 1) || 1));
        const status = clean(battle.status);
        if (battleId !== sharedWorldBattleSkillCooldownBattleId) {
          sharedWorldBattleSkillCooldownBattleId = battleId;
          sharedWorldBattleSkillCooldownUntil = 0;
          sharedWorldBattleFinalImpactAt = 0;
        }
        const cooldownRemainingMs = Math.max(0, sharedWorldBattleSkillCooldownUntil - Date.now());
        const cooldownRemaining = Math.max(0, Math.ceil(cooldownRemainingMs / 1000));
        const cooldownFill = cooldownRemainingMs > 0
          ? Math.max(0, Math.min(100, Math.round((1 - cooldownRemainingMs / (sharedWorldBattleSkillCooldownSeconds * 1000)) * 100)))
          : 100;
        const ultimateSkillId = genderKey === "female" ? "female-ultimate" : genderKey === "scorpio" ? "scorpio-ultimate" : "male-ultimate";
        // 2026-08-13: PvP Nộ uses its isolated 0-100 battle meter, not Training character mana cost.
        const ultimateManaCost = 100;
        const ultimateManaFill = mp;
        const hudSignature = [battleId, genderKey, hp, mp, level, status, cooldownRemaining, cooldownFill, ultimateManaCost, ultimateManaFill].join("|");
        const hudChanged = hudSignature !== sharedWorldBattleHudSignature;
        const hudStats = window.__ftPvpHudRenderStats && typeof window.__ftPvpHudRenderStats === "object"
          ? window.__ftPvpHudRenderStats
          : { calls: 0, writes: 0, skipped: 0, orbitBuilds: 0 };
        hudStats.calls += 1;
        if (hudChanged) hudStats.writes += 1;
        else hudStats.skipped += 1;
        hudStats.last = { battleId, gender: genderKey, hp, mp, level, status, at: Date.now() };
        window.__ftPvpHudRenderStats = hudStats;
        if (hudChanged) {
          sharedWorldBattleHudSignature = hudSignature;
          syncSharedWorldTrainingAvatarPresentation(genderKey, worldBattleCard);
        }
        worldTrainingSkillDock.classList.add("is-pvp-training-dock");
        const dockHidden = status !== "active";
        if (worldTrainingSkillDock.hidden !== dockHidden) worldTrainingSkillDock.hidden = dockHidden;
        if (worldTrainingAvatarButton && hudChanged) {
          const energyValues = {
            "--avatar-hp-fill": `${hp}%`,
            "--avatar-mp-fill": `${mp}%`,
            "--avatar-hp-half": `${hp / 2}%`,
            "--avatar-mp-half": `${mp / 2}%`,
          };
          Object.entries(energyValues).forEach(([name, value]) => {
            const key = `avatar:${name}`;
            if (sharedWorldBattleHudValues.get(key) === value) return;
            sharedWorldBattleHudValues.set(key, value);
            worldTrainingAvatarButton.style.setProperty(name, value);
          });
          window.__ftAvatarEnergyOwnerTrace = {
            owner: "battle",
            battleId: clean(battle.id),
            hp,
            mp,
            at: Date.now(),
          };
        }
        const levelLabel = worldTrainingAvatarEnergy && worldTrainingAvatarEnergy.querySelector(".ft-world-training-avatar-level");
        if (levelLabel && levelLabel.textContent !== `Lv ${level}`) levelLabel.textContent = `Lv ${level}`;
        const orbitSignature = `${genderKey}|${sharedWorldTrainingBasicSkillKind}|${sharedWorldTrainingBasicLoadout.join(",")}`;
        if (worldTrainingBasicOrbit && orbitSignature !== sharedWorldBattleOrbitSignature) {
          sharedWorldBattleOrbitSignature = orbitSignature;
          hudStats.orbitBuilds += 1;
          worldTrainingBasicOrbit.innerHTML = sharedWorldTrainingBasicLoadout.map((kind, slot) => {
            const skill = sharedWorldTrainingBasicDefinition(kind);
            return skill
              ? `<button type="button" class="ft-world-training-basic-orbit-skill is-filled ${skill.kind === sharedWorldTrainingBasicSkillKind ? "is-selected" : ""}" data-training-basic-orbit-kind="${escapeHtml(skill.kind)}" title="${escapeHtml(skill.title)}"><span class="ft-world-training-basic-skill-icon" style="--basic-skill-image:var(--qm-${genderKey}-basic-skill-${skill.index}, url('/future-assets/character_${genderKey === "scorpio" ? "scorpio" : `${genderKey}_default`}_basic_skill_${skill.index}.png'))"></span></button>`
              : `<span class="ft-world-training-basic-orbit-skill is-empty"><small>${slot + 1}</small></span>`;
          }).join("");
        }
        if (worldTrainingQuickSkill && hudChanged) {
          const cooling = cooldownRemaining > 0;
          const ready = status === "active" && mp >= ultimateManaCost && !cooling;
          worldTrainingQuickSkill.dataset.worldTrainingSkillCast = ultimateSkillId;
          worldTrainingQuickSkill.dataset.worldTrainingManaCost = String(ultimateManaCost);
          worldTrainingQuickSkill.classList.toggle("is-female-ultimate", genderKey === "female");
          worldTrainingQuickSkill.classList.toggle("is-male-ultimate", genderKey === "male");
          worldTrainingQuickSkill.classList.toggle("is-scorpio-ultimate", genderKey === "scorpio");
          worldTrainingQuickSkill.classList.toggle("is-ready", ready);
          worldTrainingQuickSkill.classList.toggle("is-cooling", cooling);
          worldTrainingQuickSkill.classList.toggle("is-locked", false);
          worldTrainingQuickSkill.classList.toggle("is-low-mana", !cooling && mp < ultimateManaCost);
          worldTrainingQuickSkill.disabled = !ready;
          const manaFill = `${ultimateManaFill}%`;
          if (sharedWorldBattleHudValues.get("quick:--skill-mana-fill") !== manaFill
            || worldTrainingQuickSkill.style.getPropertyValue("--skill-mana-fill") !== manaFill) {
            sharedWorldBattleHudValues.set("quick:--skill-mana-fill", manaFill);
            worldTrainingQuickSkill.style.setProperty("--skill-mana-fill", manaFill);
          }
          const cooldownFillValue = `${cooldownFill}%`;
          if (sharedWorldBattleHudValues.get("quick:--skill-cooldown-fill") !== cooldownFillValue
            || worldTrainingQuickSkill.style.getPropertyValue("--skill-cooldown-fill") !== cooldownFillValue) {
            sharedWorldBattleHudValues.set("quick:--skill-cooldown-fill", cooldownFillValue);
            worldTrainingQuickSkill.style.setProperty("--skill-cooldown-fill", cooldownFillValue);
          }
          const title = worldTrainingQuickSkill.querySelector(".ft-world-training-quick-skill-copy b");
          if (title) title.textContent = "Skill Nộ";
          if (worldTrainingQuickSkillMeta) worldTrainingQuickSkillMeta.textContent = cooling ? `Cooldown ${cooldownRemaining}s` : (ready ? "Ready · 100%" : `${mp}%`);
          if (worldTrainingQuickSkillCooldown) worldTrainingQuickSkillCooldown.textContent = cooling ? `${cooldownRemaining}` : "";
        }
        if (cooldownRemaining > 0 && !sharedWorldBattleSkillCooldownTimer) {
          sharedWorldBattleSkillCooldownTimer = window.setInterval(() => {
            const currentBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
            if (!currentBattle || clean(currentBattle.status) !== "active" || !worldBattleModal || !worldBattleModal.classList.contains("is-open")) {
              window.clearInterval(sharedWorldBattleSkillCooldownTimer);
              sharedWorldBattleSkillCooldownTimer = 0;
              return;
            }
            const players = sharedWorldBattlePlayersForView(currentBattle);
            renderSharedWorldBattleCombatHud(currentBattle, players.self);
          }, 250);
        } else if (cooldownRemaining <= 0 && sharedWorldBattleSkillCooldownTimer) {
          window.clearInterval(sharedWorldBattleSkillCooldownTimer);
          sharedWorldBattleSkillCooldownTimer = 0;
        }
      };

      const restoreSharedWorldBattleTrainingDock = () => {
        if (!worldTrainingSkillDock || !sharedWorldBattleTrainingDockHomeParent) return;
        // 2026-08-16: polling a closed Battle must not clear the live Training avatar every tick.
        const wasBattleDock = worldTrainingSkillDock.classList.contains("is-pvp-training-dock")
          || worldTrainingSkillDock.parentNode !== sharedWorldBattleTrainingDockHomeParent;
        if (!wasBattleDock) return;
        sharedWorldBattleHudSignature = "";
        sharedWorldBattleOrbitSignature = "";
        sharedWorldBattleHudValues.clear();
        if (sharedWorldBattleSkillCooldownTimer) window.clearInterval(sharedWorldBattleSkillCooldownTimer);
        sharedWorldBattleSkillCooldownTimer = 0;
        sharedWorldBattleSkillCooldownUntil = 0;
        sharedWorldBattleSkillCooldownBattleId = "";
        worldTrainingSkillDock.classList.remove("is-pvp-training-dock");
        worldTrainingSkillDock.hidden = false;
        sharedWorldBattleTrainingDockHomeParent.insertBefore(worldTrainingSkillDock, sharedWorldBattleTrainingDockHomeNext && sharedWorldBattleTrainingDockHomeNext.parentNode === sharedWorldBattleTrainingDockHomeParent ? sharedWorldBattleTrainingDockHomeNext : null);
        if (worldBattleCard) worldBattleCard.classList.remove("has-female-default-training-controls", "has-male-default-training-controls", "has-scorpio-training-controls");
        if (worldTrainingAvatarButton) {
          worldTrainingAvatarButton.classList.remove("is-female-default", "is-male-default", "is-scorpio");
          worldTrainingAvatarButton.style.removeProperty("--training-avatar-image");
        }
      };

      const mountSharedWorldBattleAdminTools = () => {
        if (!worldAdminAnimationTest || !worldBattleCard || !sharedWorldObstacleEditorAllowed()) return;
        if (!sharedWorldBattleAdminToolsHomeParent) {
          sharedWorldBattleAdminToolsHomeParent = worldAdminAnimationTest.parentNode;
          sharedWorldBattleAdminToolsHomeNext = worldAdminAnimationTest.nextSibling;
        }
        const host = worldBattleDesignerTools;
        if (host && worldAdminAnimationTest.parentNode !== host) host.append(worldAdminAnimationTest);
      };

      const restoreSharedWorldBattleAdminTools = () => {
        if (!worldAdminAnimationTest || !sharedWorldBattleAdminToolsHomeParent) return;
        worldAdminAnimationTest.hidden = true;
        sharedWorldBattleAdminToolsHomeParent.insertBefore(
          worldAdminAnimationTest,
          sharedWorldBattleAdminToolsHomeNext && sharedWorldBattleAdminToolsHomeNext.parentNode === sharedWorldBattleAdminToolsHomeParent
            ? sharedWorldBattleAdminToolsHomeNext
            : null
        );
      };

      const selectSharedWorldBattleBasicSkill = async (kind = "") => {
        const definition = sharedWorldTrainingBasicDefinition(kind);
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!definition || definition.disabled || !battle || clean(battle.status) !== "active") return;
        sharedWorldTrainingBasicSkillKind = definition.kind;
        const { self } = sharedWorldBattlePlayersForView(battle);
        if (self) {
          if (!battle.preferred_question_kinds || typeof battle.preferred_question_kinds !== "object") {
            battle.preferred_question_kinds = {};
          }
          battle.preferred_question_kinds[self] = definition.kind;
          battle.preferred_question_kind = definition.kind;
          if (battle.questions && typeof battle.questions === "object") {
            battle.questions[self] = {};
          }
          if (clean(battle.turn) === clean(self)) {
            battle.question = {};
          }
        }
        const point = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self)) || { x: 0.5, y: 0.58 };
        renderSharedWorldBattleCombatHud(battle, self);
        traceSharedWorldPvpTrainingRuntime("basic-skill-selected", { battleId: clean(battle.id), actor: clean(self), kind: definition.kind, trainingPicker: "qm_city_training_pick_question" });
        try {
          const questionRequestId = `skill_${clean(battle.id)}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
          const response = await fetchAuthJson("/world/battle/move", {
            method: "POST",
            body: JSON.stringify({ battle_id: clean(battle.id), x: point.x, y: point.y, current_x: point.x, current_y: point.y, training_kind: definition.kind, basic_skill_loadout: sharedWorldTrainingBasicLoadout, refresh_question: true, question_request_id: questionRequestId, ...activeWorldActorPayload() }),
          });
          renderSharedWorldBattle(response && response.payload ? response.payload : response);
          setSharedWorldStatus(`${definition.title} selected for PvP.`, "ok");
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not change PvP basic skill.", "error");
        }
      };

      const triggerSharedWorldBattleCast = (attacker = "", target = "", effect = "basic_attack", damage = 0, missed = false, onImpact = null, missMeta = {}) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const attackerNode = sharedWorldBattleNodeForUser(attacker, battle || {});
        const targetNode = sharedWorldBattleNodeForUser(target, battle || {});
        if (!worldBattleCard || !attackerNode || !targetNode) return 0;
        const effectKey = clean(effect).toLowerCase();
        const ultimateCast = ["inferno", "ultimate", "triple"].includes(effectKey) || Math.max(0, Math.round(Number(damage) || 0)) >= 30;
        const targetPoint = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(target)) || { x: 0.5, y: 0.58 };
        const attackerGender = attackerNode.classList.contains("is-character-female-default")
          ? "female"
          : (attackerNode.classList.contains("is-character-scorpio") ? "scorpio" : "male");
        const combatOverride = { sourceNode: attackerNode, targetNode, targetHost: worldBattleMap, effectParent: worldBattleCard, mode: "pvp" };
        sharedWorldTrainingCombatOverride = combatOverride;
        queueSharedWorldBattleVisualTimeout(() => {
          if (sharedWorldTrainingCombatOverride === combatOverride) sharedWorldTrainingCombatOverride = null;
        }, 4200);
        const trainingEvent = {
          correct: !missed,
          critical: ultimateCast,
          criticalHit: ultimateCast,
          damage: Math.max(0, Math.round(Number(damage) || 0)),
          slime_id: clean(target),
          primary_slime_id: clean(target),
          slime_x: targetPoint.x,
          slime_y: targetPoint.y,
          skill_id: ultimateCast ? (attackerGender === "female" ? "female-ultimate" : attackerGender === "scorpio" ? "scorpio-ultimate" : "male-ultimate") : "basic-attack",
          skill: { id: ultimateCast ? "ultimate" : "fireball", tone: ultimateCast ? "ultimate" : "fireball" },
          affected: [{ slime_id: clean(target), slime_x: targetPoint.x, slime_y: targetPoint.y, damage: Math.max(0, Math.round(Number(damage) || 0)), slime_defeated: Number((battle.hp || {})[target] || 0) <= 0 }],
        };
        faceSharedWorldTrainingCastSource(trainingEvent, targetNode, attackerNode, "pvp");
        traceSharedWorldPvpTrainingRuntime("combat-dispatch", {
          battleId: clean(battle && battle.id), attacker: clean(attacker), target: clean(target), missed: Boolean(missed), ultimate: ultimateCast,
          trainingFunction: ultimateCast ? "triggerSharedWorldTrainingEarthquake" : "triggerSharedWorldTrainingSkill",
        });
        triggerSharedWorldBattleSpeech(attacker, sharedWorldBattleMoveLabel(effectKey, damage), ultimateCast ? 2300 : 1900);
        if (missed) {
          const delay = ultimateCast ? 820 : 520;
          triggerSharedWorldBattleProjectile(attackerNode, targetNode, attackerGender, ultimateCast, delay, true, missMeta);
          sharedWorldBattleFinalImpactAt = Math.max(sharedWorldBattleFinalImpactAt, performance.now() + delay + (ultimateCast ? 900 : 620));
          return delay;
        }
        if (ultimateCast) {
          triggerSharedWorldTrainingEarthquake(trainingEvent);
          // Female cast normally finishes in ~2.8s (9 frames + homing flight + impact); keep only a small safety margin.
          sharedWorldBattleFinalImpactAt = Math.max(sharedWorldBattleFinalImpactAt, performance.now() + (attackerGender === "female" ? 3100 : attackerGender === "scorpio" ? 2550 : 2250));
          return attackerGender === "female" ? 1450 : attackerGender === "scorpio" ? 1050 : 1100;
        }
        triggerSharedWorldTrainingSkill(trainingEvent, targetNode, () => {
          if (attackerGender === "female") {
            if (typeof onImpact === "function") onImpact();
            return;
          }
          const impactPoint = sharedWorldBattleTargetAbdomenPoint(targetNode);
          showSharedWorldMaleBasicEnemyExplosion(impactPoint, attackerNode, () => {
            if (typeof onImpact === "function") onImpact();
            flushSharedWorldTrainingImpactRender();
          });
          return "defer-render";
        });
        sharedWorldBattleFinalImpactAt = Math.max(sharedWorldBattleFinalImpactAt, performance.now() + (attackerGender === "female" ? 1900 : 1850));
        // Keep Battle's hit/render timing identical to the Training Field cast atlases.
        return attackerGender === "female" ? 1430 : 1440;
      };

      const triggerSharedWorldBattleHealBurst = (caster = "") => {
        if (!worldBattleCard) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(caster, battle || {});
        if (!node) {
          return;
        }
        const anchor = node.querySelector(".ft-world-battle-character") || node;
        const cardRect = worldBattleCard.getBoundingClientRect();
        const anchorRect = anchor.getBoundingClientRect();
        const burst = document.createElement("div");
        burst.className = "ft-world-battle-heal-burst";
        burst.style.setProperty("--heal-left", `${anchorRect.left - cardRect.left + (anchorRect.width / 2)}px`);
        burst.style.setProperty("--heal-top", `${anchorRect.top - cardRect.top + 8}px`);
        burst.innerHTML = "<b>++++</b>";
        worldBattleCard.appendChild(burst);
        queueSharedWorldBattleVisualTimeout(() => {
          burst.remove();
        }, 3100);
      };

      const triggerSharedWorldBattleSkill = (entry = {}) => {
        const row = entry && typeof entry === "object" ? entry : {};
        const caster = clean(row.caster || row.attacker || "");
        const target = clean(row.target || "");
        const effect = clean(row.effect || row.skill || "").toLowerCase();
        const className = effect === "heal" || effect === "phoenix"
          ? "is-skill-heal"
          : (effect === "shield" ? "is-skill-shield" : (effect === "drain" ? "is-skill-drain" : "is-skill-inferno"));
        if (caster) {
          triggerSharedWorldBattleSpeech(caster, sharedWorldBattleMoveLabel(effect || row.skill || "inferno", 0), className === "is-skill-heal" ? 2500 : 1900);
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const casterNode = sharedWorldBattleNodeForUser(caster, battle || {});
        const targetNode = sharedWorldBattleNodeForUser(target, battle || {});
        const pulse = (node) => {
          if (!node) return;
          node.classList.remove(className);
          void node.offsetWidth;
          node.classList.add(className);
          queueSharedWorldBattleVisualTimeout(() => node.classList.remove(className), className === "is-skill-heal" ? 3200 : 1060);
        };
        pulse(casterNode);
        if (className === "is-skill-heal") {
          triggerSharedWorldBattleHealBurst(caster);
        }
        if (effect === "drain") {
          queueSharedWorldBattleVisualTimeout(() => pulse(targetNode), 90);
        }
      };

      const triggerSharedWorldBattleHit = (target = "", damage = 0, ultimate = false, attacker = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(target, battle || {});
        if (!node) {
          return;
        }
        node.classList.remove("is-hit");
        void node.offsetWidth;
        node.classList.add("is-hit");
        if (ultimate) {
          animateSharedWorldUltimateDamageTarget(node);
        }
        const hitDamage = Math.max(0, Math.round(Number(damage) || 0));
        if (hitDamage) {
          const hitPoint = sharedWorldBattleDamageHudPoint(node);
          showSharedWorldTrainingDamageFloatAtPoint(hitPoint, `-${hitDamage} HP`, ultimate ? "critical" : "", { y: ultimate ? -18 : -10 });
        }
        queueSharedWorldBattleVisualTimeout(() => {
          node.classList.remove("is-hit");
        }, 780);
      };

      const triggerSharedWorldBattleLoot = (attacker = "", target = "", loot = {}) => {
        const data = loot && typeof loot === "object" ? loot : {};
        const moved = Math.max(0, Math.round(Number(data.transferred || 0) || 0));
        if (moved <= 0) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const attackerNode = sharedWorldBattleNodeForUser(attacker, battle || {});
        const targetNode = sharedWorldBattleNodeForUser(target, battle || {});
        if (targetNode) {
          targetNode.classList.remove("is-loot-loss");
          void targetNode.offsetWidth;
          targetNode.classList.add("is-loot-loss");
          queueSharedWorldBattleVisualTimeout(() => targetNode.classList.remove("is-loot-loss"), 920);
        }
        if (attackerNode) {
          queueSharedWorldBattleVisualTimeout(() => {
            attackerNode.classList.remove("is-loot-gain");
            void attackerNode.offsetWidth;
            attackerNode.classList.add("is-loot-gain");
            queueSharedWorldBattleVisualTimeout(() => attackerNode.classList.remove("is-loot-gain"), 1220);
          }, 220);
        }
      };

      const triggerSharedWorldBattleTurnJump = (username = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(username, battle || {});
        if (!node) {
          return;
        }
        node.classList.remove("is-turn-jump");
        void node.offsetWidth;
        node.classList.add("is-turn-jump");
        queueSharedWorldBattleVisualTimeout(() => {
          node.classList.remove("is-turn-jump");
        }, 1040);
      };

      const sharedWorldBattleHitEventFromLog = (item = {}) => {
        const row = item && typeof item === "object" ? item : {};
        let attacker = clean(row.attacker || "");
        let target = clean(row.target || "");
        let effect = clean(row.effect || "");
        let damage = Math.max(0, Math.round(Number(row.damage) || 0));
        const loot = row.loot && typeof row.loot === "object" ? row.loot : {};
        const text = clean(row.text || "");
        if ((!attacker || !target) && text) {
          const match = text.match(/^(.+?)\s+hit\s+(.+?)(?:\s+with\s+([a-z_-]+))?\s+for\s+(\d+)/i);
          if (match) {
            attacker = attacker || clean(match[1]);
            target = target || clean(match[2]);
            effect = effect || clean(match[3]);
            damage = damage || Math.max(0, Math.round(Number(match[4]) || 0));
          }
        }
        if (!effect && /laser/i.test(text)) {
          effect = "laser";
        }
        if (!effect && (/inferno/i.test(text) || damage >= 30)) {
          effect = "inferno";
        }
        return { attacker, target, effect: effect || "basic_attack", damage, loot, missed: Boolean(row.missed), missMeta: row };
      };

      const sharedWorldBattleLatestLogKey = (battle = {}) => {
        const logs = Array.isArray(battle.log) ? battle.log : [];
        const last = logs[logs.length - 1] || null;
        return last ? `${clean(battle.id)}|${clean(last.event_id || last.eventId || "") || `${clean(last.seq)}|${clean(last.at)}|${clean(last.type)}|${clean(last.text)}`}` : "";
      };

      const renderSharedWorldBattleLog = (battle = {}) => {
        if (!worldBattleLog) {
          return;
        }
        const logs = Array.isArray(battle.log) ? battle.log.slice(-8) : [];
        worldBattleLog.innerHTML = "";
        logs.forEach((item) => {
          const row = document.createElement("div");
          row.textContent = clean(item && item.text) || "Battle event.";
          worldBattleLog.appendChild(row);
        });
        const last = logs[logs.length - 1] || null;
        const key = sharedWorldBattleLatestLogKey(battle);
        if (key && key !== sharedWorldBattleLastLogKey) {
          sharedWorldBattleLastLogKey = key;
          const clientActionId = clean(last && (last.client_action_id || last.clientActionId) || "");
          const optimisticRecord = clientActionId ? sharedWorldBattleOptimisticActions.get(clientActionId) : null;
          if (optimisticRecord) sharedWorldBattleOptimisticActions.delete(clientActionId);
          if (clean(last.type) === "hit") {
            const { attacker, target, effect, damage, loot } = sharedWorldBattleHitEventFromLog(last);
            const ultimateHit = ["inferno", "ultimate", "triple"].includes(clean(effect).toLowerCase()) || damage >= 30;
            if (optimisticRecord && optimisticRecord.visualOwned && !ultimateHit) {
              if (optimisticRecord.visualCommitted) triggerSharedWorldBattleLoot(attacker, target, loot);
              else optimisticRecord.pendingLoot = { attacker, target, loot };
            } else if (!ultimateHit) {
              triggerSharedWorldBattleCast(attacker, target, effect, damage, false, () => {
                triggerSharedWorldBattleHit(target, damage, false, attacker);
                triggerSharedWorldBattleLoot(attacker, target, loot);
              });
            } else {
              const impactDelay = optimisticRecord
                ? Math.max(0, Math.round(Number(optimisticRecord.impactAt || 0) - performance.now()))
                : triggerSharedWorldBattleCast(attacker, target, effect, damage);
              queueSharedWorldBattleVisualTimeout(() => {
                triggerSharedWorldBattleHit(target, damage, true, attacker);
                triggerSharedWorldBattleLoot(attacker, target, loot);
              }, Math.max(0, Math.round(Number(impactDelay) || 0)));
            }
          } else if (clean(last.type) === "miss") {
            const { attacker, target, effect, damage, missMeta } = sharedWorldBattleHitEventFromLog(last);
            if (!optimisticRecord || last.dodged || last.dodge) triggerSharedWorldBattleCast(attacker, target, effect, damage, true, null, missMeta);
            const manaGain = Math.max(0, Math.round(Number(last.mana_gain || last.manaGain) || 0));
            const manaTarget = clean(last.mana_target || last.manaTarget || target);
            const manaNode = sharedWorldBattleNodeForUser(manaTarget, battle);
            if (manaGain && manaNode) {
              const manaPoint = sharedWorldTrainingNodePoint(manaNode, 0.34);
              showSharedWorldTrainingDamageFloatAtPoint(manaPoint, `+${manaGain} MP`, "mana", { y: -62 });
            }
          } else if (clean(last.type) === "skill") {
            triggerSharedWorldBattleSkill(last);
          }
        }
      };

      const renderSharedWorldBattleQuestionText = (battle = {}, question = {}, status = "active", phase = "question", self = "") => {
        if (!worldBattleQuestion) {
          return;
        }
        const putPlain = (text = "") => {
          worldBattleQuestion.classList.remove("has-structured");
          worldBattleQuestion.textContent = text;
        };
        if (status === "finished") {
          const reward = battle.reward && typeof battle.reward === "object" ? battle.reward : {};
          const moved = Math.max(0, Math.round(Number(reward.transferred || 0) || 0));
          putPlain(clean(battle.message) || `Battle complete. Crystal transfer: ${moved}.`);
          return;
        }
        if (phase === "reveal") {
          const answer = clean(question.answer_text || "") || "...";
          const meaning = clean(question.meaning || question.translation || question.vietnamese || "");
          putPlain(`Correct answer: ${answer}${meaning ? `\nMeaning: ${meaning}` : ""}`);
          return;
        }
        worldBattleQuestion.classList.remove("has-structured");
        renderSharedWorldTrainingQuestionPanel(worldBattleQuestion, question, {
          selected: true,
          targetId: sharedWorldBattleUserKey(self),
          context: "battle",
          autoPlayAudio: true,
          fallbackText: "The next battle question is loading.",
        });
      };

      const sharedWorldBattleAnswerPlaceholder = (question = {}, phase = "question", canAnswer = false) => {
        if (phase === "reveal") {
          return "Correct answer is being revealed...";
        }
        if (!canAnswer) {
          return "Wait for your turn...";
        }
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || row.battle_kind || row.battleKind || "").toLowerCase();
        if (kind === "translate_vi" || kind === "translate_vi_speech" || row.server_speech || row.serverSpeech) {
          return "Type the Vietnamese answer...";
        }
        if (kind === "audio_word" || kind === "audio_sentence" || clean(row.audio_text || row.audioText)) {
          return "Listen, then type the English answer...";
        }
        if (kind === "read_word" || kind === "read_sentence" || kind === "speak_vi_word" || kind === "speak_vi_sentence" || row.local_speech || row.localSpeech) {
          return "Type the spoken English answer...";
        }
        if (kind === "sentence") {
          return "Type the English sentence...";
        }
        return "Type the English answer...";
      };

      const sharedWorldBattleQuestionSupportsSpeechInput = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || row.battle_kind || row.battleKind || "").toLowerCase();
        return Boolean(
          kind === "translate_vi"
          || kind === "translate_vi_speech"
          || kind === "read_word"
          || kind === "read_sentence"
          || kind === "speak_vi_word"
          || kind === "speak_vi_sentence"
          || row.server_speech
          || row.serverSpeech
          || row.local_speech
          || row.localSpeech
          || clean(row.read_text || row.readText)
        );
      };

      const setSharedWorldBattleResultOpen = (open = false) => {
        if (!worldBattleResult) {
          return;
        }
        const active = Boolean(open);
        worldBattleResult.classList.toggle("is-open", active);
        worldBattleResult.setAttribute("aria-hidden", active ? "false" : "true");
      };

      const renderSharedWorldBattleResult = (battle = {}, self = "") => {
        if (!worldBattleResult) {
          return;
        }
        const battleId = clean(battle.id || "");
        if (!battleId || sharedWorldBattleIdClosed(battleId)) {
          traceSharedWorldBattleLifecycle("result-rejected-closed", { battleId });
          return;
        }
        if (sharedWorldBattleResultShownId === battleId && worldBattleResult.classList.contains("is-open")) {
          traceSharedWorldBattleLifecycle("result-duplicate-rejected", { battleId });
          return;
        }
        sharedWorldBattleResultShownId = battleId;
        const winner = clean(battle.winner || "");
        const loser = clean(battle.loser || "");
        const selfWins = sharedWorldBattleUserKey(winner) === sharedWorldBattleUserKey(self);
        const profiles = battle.profiles && typeof battle.profiles === "object" ? battle.profiles : {};
        const winnerProfile = profiles[winner] || profiles[sharedWorldBattleUserKey(winner)] || {};
        const loserProfile = profiles[loser] || profiles[sharedWorldBattleUserKey(loser)] || {};
        const winnerName = clean(winnerProfile.display_name || winnerProfile.displayName || winner || "Winner");
        const loserName = clean(loserProfile.display_name || loserProfile.displayName || loser || "Opponent");
        const reward = battle.reward && typeof battle.reward === "object" ? battle.reward : {};
        const moved = Math.max(0, Math.round(Number(reward.transferred || 0) || 0));
        worldBattleResult.classList.toggle("is-loss", !selfWins);
        if (worldBattleResultKicker) {
          worldBattleResultKicker.textContent = selfWins ? "Arena victory" : "Arena defeat";
        }
        if (worldBattleResultTitle) {
          worldBattleResultTitle.textContent = selfWins ? "Victory" : "Defeat";
        }
        if (worldBattleResultCopy) {
          const transfer = moved ? `${moved} crystal${moved === 1 ? "" : "s"} moved from ${loserName} to ${winnerName}.` : "No crystals were transferred.";
          worldBattleResultCopy.textContent = `${winnerName} wins this QM-City Character Battle. ${transfer}`;
        }
        if (worldBattleResultReward) {
          worldBattleResultReward.innerHTML = "";
          const items = Array.isArray(reward.items) ? reward.items : [];
          if (items.length) {
            items.forEach((item) => {
              const pill = document.createElement("span");
              const quantity = Math.max(0, Math.round(Number(item && item.quantity) || 0));
              pill.textContent = `${selfWins ? "+" : "-"}${quantity} ${clean(item && item.name) || "Crystal"}`;
              worldBattleResultReward.appendChild(pill);
            });
          } else {
            const pill = document.createElement("span");
            pill.textContent = moved ? `${selfWins ? "+" : "-"}${moved} battle crystal${moved === 1 ? "" : "s"}` : "No crystal moved";
            worldBattleResultReward.appendChild(pill);
          }
        }
        setSharedWorldBattleResultOpen(true);
        traceSharedWorldBattleLifecycle("result-opened", { battleId, winner, selfWins });
      };

      // 2026-08-13: finish the killing animation, remove the loser, then reveal the result.
      const scheduleSharedWorldBattleResultAfterFinalCast = (battle = {}, self = "") => {
        const battleId = clean(battle.id || "");
        if (!battleId || sharedWorldBattleResultShownId === battleId) return;
        if (sharedWorldBattleFinishingId === battleId) {
          if (clean(battle.status) === "finished") sharedWorldBattlePendingFinish = { battle, self };
          return;
        }
        sharedWorldBattleFinishing = true;
        sharedWorldBattleFinishingId = battleId;
        sharedWorldBattlePendingFinish = { battle, self };
        setSharedWorldBattleResultOpen(false);
        const castRemaining = Math.max(0, sharedWorldBattleFinalImpactAt - performance.now());
        const loser = clean(battle.loser || "");
        const loserNode = sharedWorldBattleNodeForUser(loser, battle);
        const vanishDelay = Math.max(450, castRemaining + 120);
        const resultDelay = vanishDelay + 780;
        traceSharedWorldBattleLifecycle("result-waiting-final-cast", { battleId, loser, castRemaining: Math.round(castRemaining), vanishDelay, resultDelay });
        const beginLoserVanish = () => {
          const extendedRemaining = sharedWorldBattleFinalImpactAt - performance.now();
          if (extendedRemaining > 40) {
            sharedWorldBattleResultRevealTimer = queueSharedWorldBattleVisualTimeout(beginLoserVanish, extendedRemaining + 120);
            return;
          }
          if (loserNode && loserNode.isConnected) loserNode.classList.add("is-battle-defeated");
          traceSharedWorldBattleLifecycle("loser-vanishing", { battleId, loser });
          sharedWorldBattleResultRevealTimer = queueSharedWorldBattleVisualTimeout(() => {
            sharedWorldBattleResultRevealTimer = 0;
            sharedWorldBattleFinishing = false;
            sharedWorldBattleFinishingId = "";
            const pending = sharedWorldBattlePendingFinish && clean(sharedWorldBattlePendingFinish.battle && sharedWorldBattlePendingFinish.battle.id) === battleId
              ? sharedWorldBattlePendingFinish
              : { battle, self };
            sharedWorldBattlePendingFinish = null;
            renderSharedWorldBattleResult(pending.battle, pending.self);
            if (!sharedWorldBattleFinishTimer) {
              sharedWorldBattleFinishTimer = window.setTimeout(() => {
                sharedWorldBattleFinishTimer = 0;
                dismissSharedWorldBattleResult();
              }, 4200);
            }
          }, 780);
        };
        sharedWorldBattleResultRevealTimer = queueSharedWorldBattleVisualTimeout(beginLoserVanish, vanishDelay);
      };

      // Added 2026-08-11: finishing PvP must not leak live Speech Combat state into QM-City.
      const resetSharedWorldBattleSpeechUi = () => {
        try {
          if (typeof stopFutureSpeechInputForTarget === "function") stopFutureSpeechInputForTarget(worldBattleAnswer);
          if (typeof cancelBrowserMultilingualInputDictation === "function" && typeof browserSpeechInputTarget !== "undefined" && browserSpeechInputTarget === worldBattleAnswer) {
            cancelBrowserMultilingualInputDictation();
          }
          if (typeof stopSharedWorldTrainingSpeech === "function") stopSharedWorldTrainingSpeech();
        } catch (error) {
        }
        document.querySelectorAll(".ft-world-training-speech-live").forEach((node) => node.remove());
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.remove("is-browser-listening", "is-speech-mode", "is-browser-speech-mode", "is-legacy-speech-mode", "is-local-speech-mode", "is-speech-ready", "is-your-turn");
        }
        if (worldBattleSpeechMic) worldBattleSpeechMic.setAttribute("aria-pressed", "false");
      };

      const dismissSharedWorldBattleResult = () => {
        if (sharedWorldBattleFinishTimer) {
          window.clearTimeout(sharedWorldBattleFinishTimer);
          sharedWorldBattleFinishTimer = 0;
        }
        if (sharedWorldBattleResultRevealTimer) {
          window.clearTimeout(sharedWorldBattleResultRevealTimer);
          sharedWorldBattleVisualTimers.delete(sharedWorldBattleResultRevealTimer);
          sharedWorldBattleResultRevealTimer = 0;
        }
        sharedWorldBattleFinishingId = "";
        sharedWorldBattleFinalImpactAt = 0;
        sharedWorldBattlePendingLethalId = "";
        sharedWorldBattlePendingFinish = null;
        clearSharedWorldBattleAnswerRecovery();
        sharedWorldTrainingCombatOverride = null;
        resetSharedWorldBattleSpeechUi();
        restoreSharedWorldBattleTrainingDock();
        restoreSharedWorldBattleAdminTools();
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (battle && clean(battle.id)) {
          sharedWorldBattleDismissedFinishedId = clean(battle.id);
          closeSharedWorldBattleLifecycle(battle.id, "result-dismissed");
        }
        sharedWorldBattleDeferredCombatPayload = null;
        sharedWorldBattleCombatRenderLockUntil = 0;
        sharedWorldBattleOptimisticActions.clear();
        sharedWorldMaleUltimateCastToken += 1;
        sharedWorldScorpioUltimateCastToken += 1;
        sharedWorldBattleFinishing = false;
        sharedWorldBattleAcceptedSnapshot = { id: "", epoch: 0, seq: 0 };
        startSharedWorldBattlePolling();
        clearSharedWorldBattleVisualState();
        setSharedWorldBattleResultOpen(false);
        if (worldBattleModal) {
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.remove("is-your-turn");
        }
        if (sharedWorldBattleState && typeof sharedWorldBattleState === "object") {
          sharedWorldBattleState = { ...sharedWorldBattleState, battle: null, receivedAt: Date.now() };
        }
        void refreshSharedWorld();
      };

      const hardCloseSharedWorldBattleUi = () => {
        const closingBattleId = clean(sharedWorldBattleState && sharedWorldBattleState.battle && sharedWorldBattleState.battle.id || "");
        closeSharedWorldBattleLifecycle(closingBattleId, "hard-close");
        stopSharedWorldBattleCountdown();
        stopSharedWorldBattlePolling();
        clearSharedWorldBattleVisualState();
        sharedWorldBattleLoading = false;
        sharedWorldBattleLoadingAt = 0;
        sharedWorldBattleRequestSeq += 1;
        sharedWorldBattleAcceptedSnapshot = { id: "", epoch: 0, seq: 0 };
        sharedWorldBattleReadyRequestId = "";
        sharedWorldBattleReadyRequestInFlight = false;
        sharedWorldBattleResultShownId = "";
        sharedWorldBattleFinishing = false;
        sharedWorldBattleFinishingId = "";
        sharedWorldBattleFinalImpactAt = 0;
        sharedWorldBattlePendingLethalId = "";
        sharedWorldBattlePendingFinish = null;
        clearSharedWorldBattleAnswerRecovery();
        sharedWorldBattleInviteId = "";
        sharedWorldBattleLastLogKey = "";
        sharedWorldBattleLastTurnKey = "";
        resetSharedWorldBattleSpeechUi();
        sharedWorldTrainingCombatOverride = null;
        restoreSharedWorldBattleTrainingDock();
        restoreSharedWorldBattleAdminTools();
        sharedWorldBattleSelectedTarget = "";
        sharedWorldBattleActorTargets.clear();
        sharedWorldBattlePathQueues.clear();
        document.querySelectorAll(".ft-world-battle-player").forEach((node) => {
          if (node._worldBattleSpeechTimer) {
            window.clearTimeout(node._worldBattleSpeechTimer);
            sharedWorldBattleVisualTimers.delete(node._worldBattleSpeechTimer);
            node._worldBattleSpeechTimer = 0;
          }
        });
        if (sharedWorldBattleMotionFrame) window.cancelAnimationFrame(sharedWorldBattleMotionFrame);
        sharedWorldBattleMotionFrame = 0;
        if (sharedWorldBattleFinishTimer) window.clearTimeout(sharedWorldBattleFinishTimer);
        sharedWorldBattleFinishTimer = 0;
        sharedWorldBattleState = null;
        sharedWorldActiveBattlePairs = [];
        sharedWorldBattleLinkNodes.clear();
        if (worldBattleLinks) {
          worldBattleLinks.innerHTML = "";
        }
        if (worldInvitePanel) {
          stopSharedWorldBattleInviteCountdown();
          worldInvitePanel.hidden = true;
          if (worldInviteList) worldInviteList.replaceChildren();
        }
        setSharedWorldBattleResultOpen(false);
        if (worldBattleModal) {
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.remove("is-your-turn");
        }
        if (worldBattleAnswer) {
          worldBattleAnswer.disabled = true;
          worldBattleAnswer.value = "";
          worldBattleAnswer.dataset.turnKey = "";
        }
        if (worldBattleSubmit) {
          worldBattleSubmit.disabled = true;
        }
        if (worldBattleSpeechMic) {
          worldBattleSpeechMic.hidden = true;
          worldBattleSpeechMic.disabled = true;
        }
        sharedWorldBattleDesignerOpen = false;
        sharedWorldBattleObstacleMode = "off";
        sharedWorldBattleObstacleDraft = null;
        sharedWorldBattleMapPrimedId = "";
        sharedWorldBattleActorPoints.clear();
        hideSharedWorldBattleMoveMarker(false);
        if (worldBattleCard) {
          worldBattleCard.classList.remove("is-battle-designer", "is-live-battle");
        }
        try {
          if (
            typeof browserSpeechInputTarget !== "undefined"
            && browserSpeechInputTarget === worldBattleAnswer
            && typeof cancelBrowserMultilingualInputDictation === "function"
          ) {
            cancelBrowserMultilingualInputDictation();
          }
        } catch (error) {
        }
      };

      // Added 2026-08-11: Battle-map viewport and admin-only Pen editor.
      const renderSharedWorldBattleObstacles = () => {
        if (!worldBattleObstacleCanvas) return;
        const context = worldBattleObstacleCanvas.getContext("2d");
        if (!context) return;
        context.clearRect(0, 0, worldBattleObstacleCanvas.width, worldBattleObstacleCanvas.height);
        if (!sharedWorldBattleDesignerOpen || sharedWorldBattleObstacleMode === "off") return;
        const rows = sharedWorldBattleObstacles.strokes.slice();
        if (sharedWorldBattleObstacleDraft) rows.push(sharedWorldBattleObstacleDraft);
        rows.forEach((stroke) => {
          const points = Array.isArray(stroke.points) ? stroke.points : [];
          if (points.length < 2) return;
          context.beginPath();
          context.moveTo(points[0].x * 1672, points[0].y * 941);
          points.slice(1).forEach((point) => context.lineTo(point.x * 1672, point.y * 941));
          context.lineWidth = Math.max(6, Number(stroke.size) || 32);
          context.lineCap = "round";
          context.lineJoin = "round";
          const erasing = stroke === sharedWorldBattleObstacleDraft && sharedWorldBattleObstacleMode === "erase";
          const portal = clean(stroke.kind).toLowerCase() === "portal";
          if (portal && points.length >= 3) {
            context.closePath();
            context.fillStyle = "rgba(68,220,184,.14)";
            context.fill();
          }
          context.strokeStyle = erasing ? "rgba(255,88,112,.72)" : (portal ? "rgba(96,255,222,.76)" : "rgba(255,209,102,.58)");
          context.shadowColor = erasing ? "rgba(255,88,112,.9)" : (portal ? "rgba(68,220,184,.9)" : "rgba(70,240,215,.78)");
          context.shadowBlur = 12;
          context.stroke();
        });
        context.shadowBlur = 0;
      };

      // Added 2026-08-11: prove Battle Pen uses the same viewport anchor and panel styling as City/Training.
      const traceSharedWorldBattlePenPanelLayout = () => {
        if (!worldBattleDesignerTools || worldBattleDesignerTools.hidden) return;
        window.requestAnimationFrame(() => {
          if (!worldBattleDesignerTools || worldBattleDesignerTools.hidden) return;
          const rect = worldBattleDesignerTools.getBoundingClientRect();
          const style = getComputedStyle(worldBattleDesignerTools);
          const referenceStyle = worldPenTools ? getComputedStyle(worldPenTools) : null;
          const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
          const row = {
            map: "battle_pvp",
            top: Number(rect.top.toFixed(2)),
            right: Number((viewportWidth - rect.right).toFixed(2)),
            width: Number(rect.width.toFixed(2)),
            height: Number(rect.height.toFixed(2)),
            viewportWidth,
            buttonCount: worldBattleDesignerTools.querySelectorAll("button").length,
            labels: Array.from(worldBattleDesignerTools.querySelectorAll("button")).map((node) => clean(node.textContent)),
            position: style.position,
            padding: style.padding,
            gap: style.gap,
            borderRadius: style.borderRadius,
            cityReference: referenceStyle ? {
              top: referenceStyle.top,
              right: referenceStyle.right,
              padding: referenceStyle.padding,
              gap: referenceStyle.gap,
              borderRadius: referenceStyle.borderRadius,
            } : null,
            sameAnchorAsCity: Boolean(referenceStyle && Math.abs(rect.top - parseFloat(referenceStyle.top || "0")) < 1 && Math.abs((viewportWidth - rect.right) - parseFloat(referenceStyle.right || "0")) < 1),
            samePanelClass: worldBattleDesignerTools.classList.contains("ft-world-pen-tools"),
            at: Date.now(),
          };
          const key = JSON.stringify({ top: row.top, right: row.right, width: row.width, height: row.height, viewportWidth: row.viewportWidth, labels: row.labels });
          if (worldBattleDesignerTools.dataset.layoutTraceKey === key) return;
          worldBattleDesignerTools.dataset.layoutTraceKey = key;
          window.__ftBattlePenPanelLayoutTrace = row;
          console.info("[FTG][BattlePenPanelLayout]", row);
        });
      };

      const renderSharedWorldBattleDesigner = () => {
        const allowed = sharedWorldObstacleEditorAllowed();
        const adminVisible = sharedWorldAdminToolsVisible();
        if (worldPenBattle) worldPenBattle.hidden = !allowed;
        if (worldPenBattle) {
          worldPenBattle.classList.toggle("is-active", allowed && sharedWorldBattleDesignerOpen);
          worldPenBattle.setAttribute("aria-pressed", allowed && sharedWorldBattleDesignerOpen ? "true" : "false");
        }
        const battleOpen = Boolean(worldBattleModal && worldBattleModal.classList.contains("is-open"));
        if (worldBattleAdminToolsButton) {
          worldBattleAdminToolsButton.hidden = !allowed || !battleOpen;
          worldBattleAdminToolsButton.classList.toggle("is-active", adminVisible);
          worldBattleAdminToolsButton.setAttribute("aria-pressed", adminVisible ? "true" : "false");
        }
        // Keep the admin Pen toolbar visible in Battle just like City; only the map
        // editing state hides actors and enables the canvas.
        if (worldBattleDesignerTools) worldBattleDesignerTools.hidden = !(adminVisible && battleOpen);
        if (worldBattleCard) worldBattleCard.classList.toggle("is-battle-designer", allowed && sharedWorldBattleDesignerOpen);
        if (worldBattlePen) {
          const active = sharedWorldBattleObstacleMode === "draw";
          worldBattlePen.classList.toggle("is-active", active);
          worldBattlePen.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldBattlePortalPen) {
          const active = sharedWorldBattleObstacleMode === "portal";
          worldBattlePortalPen.classList.toggle("is-active", active);
          worldBattlePortalPen.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldBattleErase) {
          const active = sharedWorldBattleObstacleMode === "erase";
          worldBattleErase.classList.toggle("is-active", active);
          worldBattleErase.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldBattlePenSizeOutput) worldBattlePenSizeOutput.textContent = String(Number(worldBattlePenSize && worldBattlePenSize.value) || 36);
        if (worldBattleForfeit) worldBattleForfeit.textContent = sharedWorldBattleDesignerOpen ? "Close designer" : "Forfeit";
        renderSharedWorldBattleObstacles();
        traceSharedWorldBattlePenPanelLayout();
      };

      const postSharedWorldBattleObstacle = async (payload = {}) => {
        const response = await fetchAuthJson("/world/battle/obstacles", { method: "POST", body: JSON.stringify(payload) });
        const result = response && response.payload ? response.payload : response;
        if (result && result.battle_obstacles) {
          sharedWorldBattleObstacles = normalizeSharedWorldObstacles(result.battle_obstacles);
          void writeSharedWorldObstacleCache({
            key: "battle",
            etag: `\"qm-obstacles-battle-${sharedWorldBattleObstacles.revision}\"`,
            payload: sharedWorldBattleObstacles,
            updatedAt: Date.now(),
          });
          renderSharedWorldBattleObstacles();
          rescueSharedWorldBattleBlockedActors();
        }
        return result;
      };

      const centerSharedWorldBattleViewportOn = (point = { x: 0.5, y: 0.5 }, smooth = false) => {
        if (!worldBattleViewport || !worldBattleMap) return;
        const left = sharedWorldClamp(point.x, 0.5) * worldBattleMap.scrollWidth - worldBattleViewport.clientWidth / 2;
        const top = sharedWorldClamp(point.y, 0.5) * worldBattleMap.scrollHeight - worldBattleViewport.clientHeight / 2;
        worldBattleViewport.scrollTo({
          left: Math.max(0, Math.min(worldBattleMap.scrollWidth - worldBattleViewport.clientWidth, left)),
          top: Math.max(0, Math.min(worldBattleMap.scrollHeight - worldBattleViewport.clientHeight, top)),
          behavior: smooth ? "smooth" : "auto",
        });
      };

      const openSharedWorldBattleDesigner = async () => {
        if (!sharedWorldObstacleEditorAllowed() || !worldBattleModal) return;
        sharedWorldBattleDesignerOpen = true;
        sharedWorldBattleObstacleMode = "draw";
        worldBattleModal.classList.add("is-open");
        worldBattleModal.setAttribute("aria-hidden", "false");
        setSharedWorldBattleResultOpen(false);
        renderSharedWorldBattleDesigner();
        try {
          await postSharedWorldBattleObstacle({ action: "get" });
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not load Battle-map obstacles.", "error");
        }
        renderSharedWorldBattleDesigner();
        window.requestAnimationFrame(() => centerSharedWorldBattleViewportOn({ x: 0.5, y: 0.54 }, false));
      };

      const closeSharedWorldBattleDesigner = () => {
        sharedWorldBattleDesignerOpen = false;
        sharedWorldBattleObstacleMode = "off";
        sharedWorldBattleObstacleDraft = null;
        renderSharedWorldBattleDesigner();
        restoreSharedWorldBattleAdminTools();
        renderSharedWorldObstacleEditor();
        if (worldBattleModal) {
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
        }
      };

      const sharedWorldBattleMapPointFromEvent = (event) => {
        if (!worldBattleMap) return null;
        const rect = worldBattleMap.getBoundingClientRect();
        if (!rect.width || !rect.height) return null;
        return {
          x: sharedWorldClamp((event.clientX - rect.left) / rect.width),
          y: sharedWorldClamp((event.clientY - rect.top) / rect.height),
        };
      };

      // Added 2026-08-11: show the same destination arrow used by City/Training on Battle-map clicks.
      const showSharedWorldBattleMoveMarker = (point = {}) => {
        if (!worldBattleMap || !point) return;
        if (!sharedWorldBattleMoveMarker || !sharedWorldBattleMoveMarker.isConnected) {
          sharedWorldBattleMoveMarker = document.createElement("div");
          sharedWorldBattleMoveMarker.className = "ft-world-move-marker ft-world-battle-move-marker";
          sharedWorldBattleMoveMarker.setAttribute("aria-hidden", "true");
          sharedWorldBattleMoveMarker.innerHTML = "<span></span><i></i><b></b><em></em>";
          worldBattleMap.appendChild(sharedWorldBattleMoveMarker);
        }
        if (sharedWorldBattleMoveMarker._hideTimer) window.clearTimeout(sharedWorldBattleMoveMarker._hideTimer);
        sharedWorldBattleMoveMarker.style.setProperty("--move-x", `${(sharedWorldClamp(point.x) * 100).toFixed(2)}%`);
        sharedWorldBattleMoveMarker.style.setProperty("--move-y", `${(sharedWorldClamp(point.y) * 100).toFixed(2)}%`);
        sharedWorldBattleMoveMarker.classList.remove("is-visible", "is-arrived");
        void sharedWorldBattleMoveMarker.offsetWidth;
        sharedWorldBattleMoveMarker.classList.add("is-visible");
      };

      const hideSharedWorldBattleMoveMarker = (arrived = false) => {
        const marker = sharedWorldBattleMoveMarker;
        if (!marker) return;
        if (marker._hideTimer) window.clearTimeout(marker._hideTimer);
        if (arrived && marker.classList.contains("is-visible")) {
          marker.classList.add("is-arrived");
          marker._hideTimer = window.setTimeout(() => marker.classList.remove("is-visible", "is-arrived"), 430);
          return;
        }
        marker.classList.remove("is-visible", "is-arrived");
      };

      const moveSharedWorldBattlePlayer = async (point = {}) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active" || sharedWorldBattleDesignerOpen) return;
        const battleId = clean(battle.id);
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const { self } = sharedWorldBattlePlayersForView(battle);
        const key = sharedWorldBattleUserKey(self);
        const selfNode = sharedWorldBattleNodeForUser(self, battle);
        if (selfNode && selfNode.classList.contains("is-training-cast")) return;
        const current = sharedWorldBattleActorPoints.get(key) || { x: 0.22, y: 0.58 };
        const destination = { x: sharedWorldClamp(point.x, current.x), y: sharedWorldClamp(point.y, current.y) };
        showSharedWorldBattleMoveMarker(destination);
        traceSharedWorldPvpTrainingRuntime("move-request", { battleId: clean(battle.id), actor: clean(self), from: current, to: destination, movementFunction: "queueSharedWorldBattleActorPath" });
        const legalDestination = queueSharedWorldBattleActorPath(self, destination, current) || destination;
        try {
          const response = await fetchAuthJson("/world/battle/move", { method: "POST", body: JSON.stringify({ battle_id: clean(battle.id), x: legalDestination.x, y: legalDestination.y, current_x: current.x, current_y: current.y, ...activeWorldActorPayload() }) });
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) {
            traceSharedWorldBattleLifecycle("move-response-rejected", { battleId, lifecycleGeneration });
            return;
          }
          renderSharedWorldBattle(response && response.payload ? response.payload : response);
        } catch (error) {
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) return;
          setSharedWorldStatus(error && error.message ? error.message : "Could not move in Battle map.", "error");
        }
      };

      const setSharedWorldBattleObstacleMode = (mode = "off") => {
        const next = sharedWorldBattleDesignerOpen && ["draw", "portal", "erase"].includes(mode) ? mode : "off";
        sharedWorldBattleObstacleMode = sharedWorldBattleObstacleMode === next ? "off" : next;
        sharedWorldBattleObstacleDraft = null;
        renderSharedWorldBattleDesigner();
      };

      const beginSharedWorldBattleObstaclePointer = (event) => {
        if (!sharedWorldBattleDesignerOpen || sharedWorldBattleObstacleMode === "off" || (event.button != null && event.button !== 0)) return;
        const point = sharedWorldBattleMapPointFromEvent(event);
        if (!point) return;
        event.preventDefault();
        event.stopPropagation();
        sharedWorldBattleObstacleDraft = {
          id: `battle-draft-${Date.now()}`,
          size: Math.max(8, Math.min(160, Number(worldBattlePenSize && worldBattlePenSize.value) || 36)),
          points: [point],
          pointerId: event.pointerId,
        };
        try { worldBattleObstacleCanvas.setPointerCapture(event.pointerId); } catch (_error) {}
      };

      const moveSharedWorldBattleObstaclePointer = (event) => {
        const draft = sharedWorldBattleObstacleDraft;
        const point = sharedWorldBattleMapPointFromEvent(event);
        if (!draft || draft.pointerId !== event.pointerId || !point) return;
        const previous = draft.points[draft.points.length - 1];
        if (Math.hypot((point.x - previous.x) * 1672, (point.y - previous.y) * 941) < 4) return;
        event.preventDefault();
        draft.points.push(point);
        renderSharedWorldBattleObstacles();
      };

      const endSharedWorldBattleObstaclePointer = (event) => {
        const draft = sharedWorldBattleObstacleDraft;
        if (!draft || draft.pointerId !== event.pointerId) return;
        event.preventDefault();
        event.stopPropagation();
        sharedWorldBattleObstacleDraft = null;
        if (draft.points.length < 2) {
          renderSharedWorldBattleObstacles();
          return;
        }
        const optimistic = { id: draft.id, size: draft.size, points: draft.points, kind: sharedWorldBattleObstacleMode === "portal" ? "portal" : "obstacle" };
        if (sharedWorldBattleObstacleMode === "erase") {
          void postSharedWorldBattleObstacle({ action: "erase", stroke: optimistic }).catch((error) => setSharedWorldStatus(error && error.message ? error.message : "Could not erase Battle obstacle.", "error"));
          return;
        }
        sharedWorldBattleObstacles.strokes.push(optimistic);
        renderSharedWorldBattleObstacles();
        rescueSharedWorldBattleBlockedActors();
        void postSharedWorldBattleObstacle({ action: "add", stroke: optimistic }).catch((error) => {
          sharedWorldBattleObstacles.strokes = sharedWorldBattleObstacles.strokes.filter((stroke) => stroke.id !== optimistic.id);
          renderSharedWorldBattleObstacles();
          setSharedWorldStatus(error && error.message ? error.message : "Could not save Battle obstacle.", "error");
        });
      };

      const beginSharedWorldBattleViewportPan = (event) => {
        if (!worldBattleViewport || sharedWorldBattleDesignerOpen || (event.button != null && event.button !== 0)) return;
        if (event.target && event.target.closest && event.target.closest("button,input,label,.ft-world-battle-referee,.ft-world-battle-player")) return;
        sharedWorldBattleViewportDrag = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, left: worldBattleViewport.scrollLeft, top: worldBattleViewport.scrollTop, moved: false };
        try { worldBattleViewport.setPointerCapture(event.pointerId); } catch (_error) {}
      };

      const moveSharedWorldBattleViewportPan = (event) => {
        const drag = sharedWorldBattleViewportDrag;
        if (!drag || drag.pointerId !== event.pointerId || !worldBattleViewport) return;
        const dx = event.clientX - drag.x;
        const dy = event.clientY - drag.y;
        if (!drag.moved && Math.hypot(dx, dy) < 6) return;
        drag.moved = true;
        event.preventDefault();
        worldBattleViewport.scrollLeft = drag.left - dx;
        worldBattleViewport.scrollTop = drag.top - dy;
      };

      const endSharedWorldBattleViewportPan = (event) => {
        const drag = sharedWorldBattleViewportDrag;
        if (!drag || drag.pointerId !== event.pointerId) return;
        sharedWorldBattleViewportDrag = null;
        if (drag.moved) {
          sharedWorldBattleSuppressClick = true;
          window.setTimeout(() => { sharedWorldBattleSuppressClick = false; }, 0);
        }
      };

      const handleSharedWorldBattleMapClick = (event) => {
        if (sharedWorldBattleSuppressClick || sharedWorldBattleDesignerOpen || !worldBattleMap) return;
        traceSharedWorldPvpTrainingRuntime("map-click", { targetTag: clean(event.target && event.target.tagName), x: event.clientX, y: event.clientY });
        const actor = event.target && event.target.closest ? event.target.closest(".ft-world-battle-player") : null;
        if (actor) {
          if (!actor.classList.contains("is-opponent")) return;
          const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
          const { opponent } = sharedWorldBattlePlayersForView(battle || {});
          sharedWorldBattleSelectedTarget = opponent;
          if (worldBattleRight) worldBattleRight.classList.add("is-target-selected");
          if (worldBattleAnswer && !worldBattleAnswer.disabled) {
            queueSharedWorldBattleVisualTimeout(() => worldBattleAnswer.focus({ preventScroll: true }), 80);
          }
          setSharedWorldStatus(`${clean(((battle.profiles || {})[opponent] || {}).display_name || opponent)} selected as PvP target.`, "ok");
          traceSharedWorldPvpTrainingRuntime("target-selected", { battleId: clean(battle && battle.id), target: clean(opponent), targetNode: "ft-world-battle-right" });
          return;
        }
        if (event.target && event.target.closest && event.target.closest("button,input,label,.ft-world-battle-referee,.ft-world-battle-skill-dock")) return;
        const point = sharedWorldBattleMapPointFromEvent(event);
        if (point) void moveSharedWorldBattlePlayer(point);
      };

      // Added 2026-08-16: each client confirms the arena is mounted before combat unlocks.
      const ensureSharedWorldBattleClientReady = async (battle = {}, username = "") => {
        const battleId = clean(battle.id || "");
        const userKey = clean(username || "");
        if (!battleId || !userKey || clean(battle.status) !== "active") return;
        const readyPlayers = (Array.isArray(battle.ready_players) ? battle.ready_players : (Array.isArray(battle.readyPlayers) ? battle.readyPlayers : []))
          .map((item) => sharedWorldBattleUserKey(item));
        if (readyPlayers.includes(sharedWorldBattleUserKey(userKey))) {
          if (sharedWorldBattleReadyRequestId === battleId) sharedWorldBattleReadyRequestInFlight = false;
          return;
        }
        if (sharedWorldBattleReadyRequestInFlight && sharedWorldBattleReadyRequestId === battleId) return;
        sharedWorldBattleReadyRequestId = battleId;
        sharedWorldBattleReadyRequestInFlight = true;
        const positions = battle.positions && typeof battle.positions === "object" ? battle.positions : {};
        const point = positions[userKey] || positions[sharedWorldBattleUserKey(userKey)] || { x: 0.5, y: 0.58 };
        try {
          const response = await fetchAuthJson("/world/battle/move", {
            method: "POST",
            body: JSON.stringify({
              battle_id: battleId,
              x: sharedWorldClamp(point.x, 0.5),
              y: sharedWorldClamp(point.y, 0.58),
              current_x: sharedWorldClamp(point.x, 0.5),
              current_y: sharedWorldClamp(point.y, 0.58),
              client_ready: true,
              ...activeWorldActorPayload(),
            }),
            timeoutMs: 12000,
          });
          const result = response && response.payload ? response.payload : response;
          traceSharedWorldBattleLifecycle("client-ready", { battleId, user: userKey });
          renderSharedWorldBattle(result);
        } catch (error) {
          sharedWorldBattleReadyRequestId = "";
          scheduleSharedWorldReconnect(error && error.message ? error.message : "Could not enter the Battle arena.");
        } finally {
          sharedWorldBattleReadyRequestInFlight = false;
        }
      };

      const renderSharedWorldBattle = (payload = {}) => {
        if (!worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        let incomingBattle = payload && typeof payload === "object" && payload.battle && typeof payload.battle === "object"
          ? payload.battle
          : null;
        if (incomingBattle && sharedWorldBattleIdClosed(incomingBattle.id)) {
          traceSharedWorldBattleLifecycle("closed-battle-envelope-rendered", {
            battleId: clean(incomingBattle.id),
            status: clean(incomingBattle.status),
            incomingInvites: Array.isArray(payload && payload.incoming_invites) ? payload.incoming_invites.length : 0,
          });
          // The Battle snapshot is stale, but invites/revisions beside it are new.
          payload = { ...(payload && typeof payload === "object" ? payload : {}), battle: null };
          incomingBattle = null;
        }
        if (incomingBattle && clean(incomingBattle.id) && document.visibilityState === "hidden") {
          sharedWorldBattleDeferredCombatPayload = payload;
          traceSharedWorldPvpTrainingRuntime("combat-render-deferred", {
            battleId: clean(incomingBattle.id),
            reason: "background-hidden",
          });
          return;
        }
        const pendingOwnedVisual = Array.from(sharedWorldBattleOptimisticActions.values())
          .find((row) => row && row.visualOwned && !row.visualCommitted);
        if (incomingBattle && pendingOwnedVisual && performance.now() < sharedWorldBattleCombatRenderLockUntil) {
          sharedWorldBattleDeferredCombatPayload = payload;
          traceSharedWorldPvpTrainingRuntime("combat-render-deferred", {
            battleId: clean(incomingBattle.id),
            reason: "basic-impact-pending",
            actionId: clean(pendingOwnedVisual.actionId || ""),
          });
          return;
        }
        if (incomingBattle && clean(incomingBattle.id)) {
          const incomingId = clean(incomingBattle.id);
          const incomingEpoch = Math.max(0, Number(incomingBattle.updated_epoch || incomingBattle.updatedEpoch || 0) || 0);
          const incomingSeq = Math.max(0, Math.floor(Number(incomingBattle.updated_seq || incomingBattle.updatedSeq || 0) || 0));
          const accepted = sharedWorldBattleAcceptedSnapshot || { id: "", epoch: 0, seq: 0 };
          const sameBattle = clean(accepted.id) === incomingId;
          const staleMissingEpoch = sameBattle && Number(accepted.epoch || 0) > 0 && incomingEpoch <= 0;
          const staleEpoch = sameBattle && incomingEpoch > 0 && Number(accepted.epoch || 0) > 0 && incomingEpoch < Number(accepted.epoch || 0);
          const staleSeq = sameBattle && incomingEpoch > 0 && incomingEpoch === Number(accepted.epoch || 0) && incomingSeq < Number(accepted.seq || 0);
          if (staleMissingEpoch || staleEpoch || staleSeq) {
            window.__ftPvpSnapshotTrace = {
              stage: "stale-rejected",
              battleId: incomingId,
              incomingEpoch,
              incomingSeq,
              acceptedEpoch: Number(accepted.epoch || 0),
              acceptedSeq: Number(accepted.seq || 0),
              at: Date.now(),
            };
            return;
          }
          if (!sameBattle || incomingEpoch > Number(accepted.epoch || 0)
            || (incomingEpoch === Number(accepted.epoch || 0) && incomingSeq >= Number(accepted.seq || 0))) {
            sharedWorldBattleAcceptedSnapshot = { id: incomingId, epoch: incomingEpoch, seq: incomingSeq };
          }
          const currentBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
          if (currentBattle && clean(currentBattle.id) === incomingId && clean(incomingBattle.status) === "active") {
            if (!clean(incomingBattle.preferred_question_kind || "")) {
              incomingBattle.preferred_question_kind = clean(currentBattle.preferred_question_kind || "");
            }
            if (!Array.isArray(incomingBattle.basic_skill_loadout) && Array.isArray(currentBattle.basic_skill_loadout)) {
              incomingBattle.basic_skill_loadout = currentBattle.basic_skill_loadout.slice(0, 3);
            }
            if ((!incomingBattle.question || !clean(incomingBattle.question.prompt || ""))
              && currentBattle.question && clean(currentBattle.question.prompt || "")) {
              incomingBattle.question = { ...currentBattle.question, can_answer: false };
              traceSharedWorldBattleLifecycle("question-handoff-preserved", {
                battleId: incomingId,
                prompt: clean(currentBattle.question.prompt || "").slice(0, 80),
                kind: clean(currentBattle.question.training_kind || currentBattle.question.trainingKind || currentBattle.question.kind || ""),
              });
            }
          }
        }
        sharedWorldBattleState = payload && typeof payload === "object" ? payload : null;
        if (sharedWorldBattleState) {
          sharedWorldBattleState.receivedAt = Date.now();
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const activeBattle = battle && clean(battle.id);
        const inviteBlockingBattle = activeBattle && clean(battle.status) === "active";
        const battleObstacleRevision = Math.max(0, Number(
          sharedWorldBattleState && (sharedWorldBattleState.battle_obstacle_revision || sharedWorldBattleState.battleObstacleRevision) || 0
        ) || 0);
        if (!sharedWorldObstacleCacheLoaded.has("battle") || battleObstacleRevision !== Number(sharedWorldBattleObstacles.revision || 0)) {
          void loadSharedWorldObstacleSnapshot("battle", battleObstacleRevision).then(() => renderSharedWorldBattleObstacles());
        }
        renderSharedWorldBattleInvites(
          Array.isArray(sharedWorldBattleState && sharedWorldBattleState.incoming_invites)
            ? sharedWorldBattleState.incoming_invites
            : [],
          Boolean(inviteBlockingBattle),
        );
        if (!inviteBlockingBattle && Array.isArray(sharedWorldBattleState && sharedWorldBattleState.outgoing_invites) && sharedWorldBattleState.outgoing_invites.length) {
          const outgoing = sharedWorldBattleState.outgoing_invites[0] || {};
          setSharedWorldStatus(`Battle invite pending for ${sharedWorldInviteProfileLabel(outgoing, "to")}.`, "ok");
        }
        if (!worldBattleModal) {
          return;
        }
        if (!activeBattle) {
          restoreSharedWorldBattleTrainingDock();
          restoreSharedWorldBattleAdminTools();
          if (worldBattleCard) worldBattleCard.classList.remove("is-live-battle");
          if (sharedWorldBattleDesignerOpen) {
            renderSharedWorldBattleDesigner();
            return;
          }
          setSharedWorldBattleResultOpen(false);
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
          if (worldBattleAnswerForm) {
            worldBattleAnswerForm.classList.remove("is-your-turn");
          }
          stopSharedWorldBattleCountdown();
          startSharedWorldBattlePolling();
          return;
        }
        if (clean(battle.status) === "finished" && sharedWorldBattleDismissedFinishedId === clean(battle.id)) {
          setSharedWorldBattleResultOpen(false);
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
          if (worldBattleAnswerForm) {
            worldBattleAnswerForm.classList.remove("is-your-turn");
          }
          stopSharedWorldBattleCountdown();
          startSharedWorldBattlePolling();
          return;
        }
        if (clean(battle.status) === "active") {
          sharedWorldBattleDismissedFinishedId = "";
          if (sharedWorldBattleResultShownId && sharedWorldBattleResultShownId !== clean(battle.id)) sharedWorldBattleResultShownId = "";
        }
        worldBattleModal.classList.add("is-open");
        worldBattleModal.setAttribute("aria-hidden", "false");
        if (worldBattleCard) worldBattleCard.classList.toggle("is-live-battle", clean(battle.status) === "active" || clean(battle.status) === "finished");
        sharedWorldBattleDesignerOpen = false;
        sharedWorldBattleObstacleMode = "off";
        renderSharedWorldBattleDesigner();
        const { self, opponent } = sharedWorldBattlePlayersForView(battle);
        const readyPlayers = (Array.isArray(battle.ready_players) ? battle.ready_players : (Array.isArray(battle.readyPlayers) ? battle.readyPlayers : []))
          .map((item) => sharedWorldBattleUserKey(item));
        const combatReady = Boolean(battle.combat_ready || battle.combatReady) && readyPlayers.length >= 2;
        traceSharedWorldPvpTrainingRuntime("render", {
          battleId: clean(battle.id), status: clean(battle.status), self: clean(self), opponent: clean(opponent),
          combatFunctions: ["triggerSharedWorldTrainingSkill", "triggerSharedWorldTrainingEarthquake"],
          questionPanel: "ft-world-battle-referee", hud: "ft-world-battle-skill-dock",
        });
        if (!sharedWorldBattleSelectedTarget) sharedWorldBattleSelectedTarget = opponent;
        renderSharedWorldBattlePlayer(worldBattleLeft, battle, self, "left");
        renderSharedWorldBattlePlayer(worldBattleRight, battle, opponent, "right");
        renderSharedWorldBattleCombatHud(battle, self);
        if (!combatReady) void ensureSharedWorldBattleClientReady(battle, self);
        mountSharedWorldBattleAdminTools();
        renderSharedWorldAdminTrainingTestTools();
        if (sharedWorldBattleMapPrimedId !== clean(battle.id)) {
          sharedWorldBattleMapPrimedId = clean(battle.id);
          const selfPoint = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self)) || { x: 0.22, y: 0.58 };
          queueSharedWorldBattleVisualTimeout(() => centerSharedWorldBattleViewportOn(selfPoint, false), 0);
        }
        const question = battle.question && typeof battle.question === "object" ? battle.question : {};
        const status = clean(battle.status || "active");
        const canAnswer = combatReady && status === "active" && Boolean(question.can_answer);
        const phase = clean(battle.phase || "question");
        const turnJumpKey = `${clean(battle.id)}|${clean(battle.turn)}|${phase}|${clean(question.created_at || "")}`;
        if (status === "active" && clean(battle.turn) && phase !== "reveal" && turnJumpKey !== sharedWorldBattleLastTurnKey) {
          sharedWorldBattleLastTurnKey = turnJumpKey;
          triggerSharedWorldBattleTurnJump(battle.turn);
        }
        const turnName = clean(((battle.profiles || {})[battle.turn] || {}).display_name || battle.turn || "");
        if (worldBattlePhase) {
          if (status === "active" && !combatReady) {
            worldBattlePhase.textContent = `Waiting for both players to enter (${readyPlayers.length}/2)`;
          } else if (status === "finished") {
            worldBattlePhase.textContent = clean(battle.winner) === self ? "Victory secured" : "Battle finished";
          } else if (phase === "reveal") {
            worldBattlePhase.textContent = "Answer reveal - next turn soon";
          } else if (canAnswer) {
            worldBattlePhase.textContent = phase === "free" ? "Free attack - choose a skill and strike" : (phase === "steal" ? "Steal chance - answer now" : "Your turn - cast the word");
          } else {
            worldBattlePhase.textContent = `Waiting for ${turnName || "opponent"}`;
          }
        }
        renderSharedWorldBattleQuestionText(battle, question, status, phase, self);
        const battleChoiceMode = renderSharedWorldCombatChoices(worldBattleChoices, worldBattleAnswerForm, question, canAnswer);
        const battleQuestionTrace = {
          battleId: clean(battle.id),
          kind: clean(question.training_kind || question.trainingKind || question.kind || question.battle_kind || question.battleKind || ""),
          prompt: clean(question.prompt || "").slice(0, 80),
          createdAt: clean(question.created_at || question.createdAt || ""),
          activeSkill: clean(battle.preferred_question_kind || sharedWorldTrainingBasicSkillKind || ""),
          panelRect: worldBattleQuestion && typeof worldBattleQuestion.getBoundingClientRect === "function"
            ? (() => { const rect = worldBattleQuestion.getBoundingClientRect(); return { width: Math.round(rect.width), height: Math.round(rect.height), top: Math.round(rect.top), left: Math.round(rect.left) }; })()
            : null,
          choices: Array.isArray(question.choices) ? question.choices.length : 0,
          choiceMode: Boolean(battleChoiceMode),
          canAnswer: Boolean(canAnswer),
          phase,
          at: Date.now(),
        };
        window.__ftPvpQuestionTrace = battleQuestionTrace;
        console.info("[FTG][PvpQuestion]", battleQuestionTrace);
        if (worldBattleAnswer) {
          worldBattleAnswer.disabled = !canAnswer;
          worldBattleAnswer.placeholder = sharedWorldBattleAnswerPlaceholder(question, phase, canAnswer);
          const turnKey = `${clean(battle.id)}|${clean(battle.turn)}|${phase}|${clean(question.created_at)}`;
          if (canAnswer && !worldBattleAnswerForm.classList.contains("is-choice-mode") && worldBattleAnswer.dataset.turnKey !== turnKey) {
            worldBattleAnswer.dataset.turnKey = turnKey;
            worldBattleAnswer.value = "";
            queueSharedWorldBattleVisualTimeout(() => worldBattleAnswer && worldBattleAnswer.focus(), 60);
          }
        }
        if (worldBattleSubmit) {
          worldBattleSubmit.disabled = !canAnswer;
        }
        if (worldBattleSpeechMic) {
          const showSpeechMic = canAnswer && sharedWorldBattleQuestionSupportsSpeechInput(question);
          worldBattleSpeechMic.hidden = !showSpeechMic;
          worldBattleSpeechMic.disabled = !showSpeechMic;
          worldBattleSpeechMic.title = showSpeechMic ? "Speak this battle answer" : "Speech answer unavailable for this question";
        }
        if (worldBattleViToggle) {
          const showViToggle = canAnswer && (
            sharedWorldTrainingQuestionIsTranslateVi(question)
            || sharedWorldTrainingQuestionIsServerSpeech(question)
          );
          worldBattleViToggle.hidden = !showViToggle;
          worldBattleViToggle.setAttribute("aria-hidden", showViToggle ? "false" : "true");
        }
        if (worldBattleSpeechMode) {
          worldBattleSpeechMode.hidden = !canAnswer;
        }
        if (worldBattleAnswerForm) {
          const speechQuestion = canAnswer && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = canAnswer && sharedWorldTrainingQuestionIsServerSpeech(question);
          const translateQuestion = canAnswer && sharedWorldTrainingQuestionIsTranslateVi(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldBattleAnswer.disabled = !canAnswer || localSpeechQuestion;
          worldBattleAnswer.dataset.vietnameseTypingActive = (translateQuestion || serverSpeechQuestion) && !speechQuestion ? "1" : "0";
          worldBattleAnswer.placeholder = browserSpeechQuestion
            ? "Type English or press Mic and speak..."
            : (localSpeechQuestion ? "Use your microphone. Read until all tokens are detected." : (legacyServerSpeechQuestion ? "Type Vietnamese or press Ctrl to speak Vietnamese..." : (translateQuestion ? "Nhap ban dich tieng Viet..." : "Type the English answer...")));
          worldBattleAnswerForm.classList.toggle("is-speech-mode", speechQuestion || serverSpeechQuestion);
          worldBattleAnswerForm.classList.toggle("is-browser-speech-mode", browserSpeechQuestion);
          worldBattleAnswerForm.classList.toggle("is-legacy-speech-mode", legacyServerSpeechQuestion);
          worldBattleAnswerForm.classList.toggle("is-local-speech-mode", localSpeechQuestion);
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.toggle("is-your-turn", canAnswer);
          worldBattleAnswerForm.classList.toggle("is-speech-ready", Boolean(canAnswer && sharedWorldBattleQuestionSupportsSpeechInput(question)));
        }
        const selfMp = Math.max(0, Math.round(Number((battle.mp || {})[self] || 0) || 0));
        if (worldBattleSkills) {
          worldBattleSkills.querySelectorAll("[data-world-skill]").forEach((button) => {
            button.disabled = !combatReady || status !== "active" || selfMp < 100;
            button.title = selfMp >= 100 ? "Cast this full-mana skill." : "Requires 100 MP.";
          });
        }
        renderSharedWorldBattleLog(battle);
        if (status === "active") {
          if (sharedWorldBattleFinishTimer) window.clearTimeout(sharedWorldBattleFinishTimer);
          sharedWorldBattleFinishTimer = 0;
          const lethalPending = sharedWorldBattlePendingLethalId === clean(battle.id);
          if (!lethalPending) {
            sharedWorldBattleFinishing = false;
            sharedWorldBattleFinishingId = "";
          }
          if (lethalPending) {
            startSharedWorldBattlePolling();
          } else {
            setSharedWorldBattleResultOpen(false);
          }
          startSharedWorldBattleCountdown();
          startSharedWorldBattlePolling();
        } else {
          sharedWorldBattlePendingLethalId = "";
          clearSharedWorldBattleAnswerRecovery();
          stopSharedWorldBattleCountdown();
          // Keep the sleeping watcher alive so both clients receive the same
          // terminal snapshot and later invitations without a manual reload.
          startSharedWorldBattlePolling();
          resetSharedWorldBattleSpeechUi();
          scheduleSharedWorldBattleResultAfterFinalCast(battle, self);
        }
      };

      const refreshSharedWorldBattle = async () => {
        if (!authToken || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        if (sharedWorldRuntimeDeferredForGate) {
          return;
        }
        const now = Date.now();
        if (sharedWorldBattleLoading && now - sharedWorldBattleLoadingAt < 900) {
          return;
        }
        sharedWorldBattleLoading = true;
        sharedWorldBattleLoadingAt = now;
        const requestSeq = ++sharedWorldBattleRequestSeq;
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const requestBattleId = clean(sharedWorldBattleState && sharedWorldBattleState.battle && sharedWorldBattleState.battle.id || "");
        try {
          const response = await fetchAuthJson(`/world/battle/state${activeWorldActorQuery()}`, { timeoutMs: 0 });
          const result = response && response.payload ? response.payload : response;
          sharedWorldBattleRealtimeRevision = Math.max(
            sharedWorldBattleRealtimeRevision,
            Math.max(0, Number(result && result.battle_realtime_revision || 0) || 0),
          );
          const responseBattle = result && result.battle && typeof result.battle === "object" ? result.battle : null;
          const rawResponseBattleId = clean(responseBattle && responseBattle.id || "");
          const closedFinishedBattle = Boolean(
            rawResponseBattleId
            && clean(responseBattle && responseBattle.status) === "finished"
            && sharedWorldBattleIdClosed(rawResponseBattleId)
          );
          // Added 2026-08-16: a dismissed finished snapshot must not discard
          // the outer invite queue that arrived in the same state response.
          const renderResult = closedFinishedBattle
            ? { ...(result && typeof result === "object" ? result : {}), battle: null }
            : result;
          const responseBattleId = closedFinishedBattle ? "" : rawResponseBattleId;
          const lifecycleBattleId = responseBattleId && responseBattleId !== requestBattleId ? responseBattleId : requestBattleId;
          const lifecycleGateBattleId = closedFinishedBattle ? "" : lifecycleBattleId;
          if (!sharedWorldBattleAsyncStillCurrent(lifecycleGateBattleId, lifecycleGeneration, requestSeq)) {
            traceSharedWorldBattleLifecycle("state-response-rejected", { battleId: requestBattleId, requestSeq, lifecycleGeneration });
            return;
          }
          if (closedFinishedBattle) {
            traceSharedWorldBattleLifecycle("closed-finished-envelope-accepted", {
              battleId: rawResponseBattleId,
              incomingInvites: Array.isArray(result && result.incoming_invites) ? result.incoming_invites.length : 0,
              requestSeq,
            });
          }
          if (responseBattleId && responseBattleId !== requestBattleId) {
            traceSharedWorldBattleLifecycle("new-battle-handoff", { battleId: responseBattleId, previousBattleId: requestBattleId, requestSeq });
          }
          renderSharedWorldBattle(renderResult);
        } catch (error) {
          if (!sharedWorldBattleAsyncStillCurrent(requestBattleId, lifecycleGeneration, requestSeq)) {
            traceSharedWorldBattleLifecycle("state-error-rejected", {
              battleId: requestBattleId,
              requestSeq,
              lifecycleGeneration,
              message: clean(error && error.message || ""),
            });
            return;
          }
          const message = error && error.message ? error.message : "";
          scheduleSharedWorldReconnect(message || "Could not load battle state.");
        } finally {
          if (requestSeq === sharedWorldBattleRequestSeq) {
            sharedWorldBattleLoading = false;
            sharedWorldBattleLoadingAt = 0;
          }
        }
      };

      const sendSharedWorldBattleInvite = async (game = "fireball_vocab", message = "") => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!target || clean(target.username).toLowerCase() === clean(activeWorldUsername()).toLowerCase()) {
          setSharedWorldStatus("Select another learner before sending a battle invite.", "error");
          return;
        }
        if (target.isPlaying) {
          setSharedWorldStatus(`${sharedWorldTargetLabel(target)} is already playing a battle. Choose another learner.`, "error");
          return;
        }
        // 2026-08-16: inviting is UI-only; Battle spawn positions apply after both clients enter the arena.
        const body = {
          target: clean(target.username),
          game: clean(game || "fireball_vocab"),
          message: clean(message) || "Would you like to play QM-City Character Battle with me?",
          ...activeWorldActorPayload(),
        };
        try {
          const response = await fetchAuthJson("/world/battle/invite", {
            method: "POST",
            body: JSON.stringify(body),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          traceSharedWorldBattleLifecycle("invite-response", {
            battleId: clean(result && result.battle && result.battle.id || ""),
            target: clean(target.username),
            inviteId: clean(result && result.invite && result.invite.id || ""),
            revision: Math.max(0, Number(result && result.battle_realtime_revision || 0) || 0),
          });
          renderSharedWorldBattle(result);
          if (result && result.invite_spam_blocked) {
            setSharedWorldStatus(`Invite already delivered. Retry in ${Math.max(1, Number(result.retry_after || 1))}s.`, "error");
          } else if (result && result.invite_refreshed) {
            setSharedWorldStatus(`Existing invite for ${sharedWorldTargetLabel(target)} extended to 10 seconds.`, "ok");
          } else {
            setSharedWorldStatus(`Battle invite sent to ${sharedWorldTargetLabel(target)}.`, "ok");
          }
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not send battle invite.", "error");
        }
      };

      const respondSharedWorldBattleInvite = async (accept = false, requestedInviteId = "") => {
        const inviteId = clean(requestedInviteId || sharedWorldBattleInviteId);
        if (!inviteId) {
          return;
        }
        sharedWorldBattleInviteId = inviteId;
        try {
          const response = await fetchAuthJson("/world/battle/respond", {
            method: "POST",
            body: JSON.stringify({ invite_id: inviteId, accept: Boolean(accept), ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          traceSharedWorldBattleLifecycle("respond-response", {
            battleId: clean(result && result.battle && result.battle.id || ""),
            inviteId,
            accepted: Boolean(accept),
            revision: Math.max(0, Number(result && result.battle_realtime_revision || 0) || 0),
          });
          renderSharedWorldBattle(result);
          setSharedWorldStatus(accept ? "Battle accepted." : "Battle declined.", accept ? "ok" : "");
        } catch (error) {
          const message = clean(error && error.message || "Could not respond to battle invite.");
          if (message.toLowerCase().includes("no longer available")) {
            traceSharedWorldBattleLifecycle("stale-invite-cleared", {
              inviteId,
              accepted: Boolean(accept),
            });
            const staleCard = worldInviteList ? worldInviteList.querySelector(`[data-invite-id="${CSS.escape(inviteId)}"]`) : null;
            if (staleCard) staleCard.remove();
            if (sharedWorldBattleInviteId === inviteId) sharedWorldBattleInviteId = "";
            if (worldInvitePanel && worldInviteList && !worldInviteList.children.length) worldInvitePanel.hidden = true;
            void refreshSharedWorldBattle();
          }
          setSharedWorldStatus(message, "error");
        }
      };

      const submitSharedWorldBattleAnswer = async (selectedAnswer = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active" || !worldBattleAnswer) {
          return;
        }
        const answer = clean(selectedAnswer || worldBattleAnswer.value);
        const battleId = clean(battle.id);
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const question = battle.question && typeof battle.question === "object" ? battle.question : {};
        const preferredBattleKind = clean(battle.preferred_question_kind || "");
        if (preferredBattleKind && question && typeof question === "object" && !clean(question.training_kind || question.trainingKind || question.kind)) {
          question.training_kind = preferredBattleKind;
        }
        const choices = Array.isArray(question.choices) ? question.choices.slice(0, 3) : [];
        const selectedIndex = choices.findIndex((choice) => clean(choice && typeof choice === "object" ? (choice.value || choice.label) : choice) === answer);
        const correctIndex = Number(question.client_correct_choice_index ?? question.clientCorrectChoiceIndex);
        const clientFirst = choices.length === 3 && Number.isInteger(correctIndex) && correctIndex >= 0 && selectedIndex >= 0;
        const clientActionId = clientFirst
          ? `pvp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
          : "";
        const pendingKey = `pvp:${clean(battle.id)}:${clean(question.id)}`;
        const choiceSignature = worldBattleChoices ? (worldBattleChoices.dataset.combatChoiceSignature || "") : "";
        if (clientFirst && sharedWorldCombatPendingAnswers.has(pendingKey)) return;
        if (clientFirst) {
          sharedWorldCombatPendingAnswers.add(pendingKey);
          previewSharedWorldCombatChoice(worldBattleChoices, answer, selectedIndex === correctIndex);
          scheduleSharedWorldBattleAnswerRecovery(battleId, pendingKey, choiceSignature);
        }
        if (clientFirst) {
          const { self, opponent } = sharedWorldBattlePlayersForView(battle);
          const correct = selectedIndex === correctIndex;
          const opponentHp = Math.max(0, Math.round(Number((battle.hp || {})[opponent] ?? 100) || 0));
          const predictedDamage = correct ? 10 : 0;
          if (predictedDamage >= opponentHp && opponentHp > 0) {
            sharedWorldBattlePendingLethalId = battleId;
            traceSharedWorldBattleLifecycle("lethal-answer-predicted", { battleId, opponent, opponentHp, predictedDamage });
          }
          const optimisticRecord = {
            actionId: clientActionId,
            correct,
            visualOwned: correct,
            visualCommitted: false,
            at: performance.now(),
          };
          sharedWorldBattleOptimisticActions.set(clientActionId, optimisticRecord);
          if (correct) {
            sharedWorldBattleCombatRenderLockUntil = performance.now() + 3200;
            const impactDelay = triggerSharedWorldBattleCast(self, opponent, "basic_attack", 10, false, () => {
              if (optimisticRecord.visualCommitted) return;
              optimisticRecord.visualCommitted = true;
              triggerSharedWorldBattleHit(opponent, 10, false, self);
              if (optimisticRecord.pendingLoot) {
                const pendingLoot = optimisticRecord.pendingLoot;
                optimisticRecord.pendingLoot = null;
                triggerSharedWorldBattleLoot(pendingLoot.attacker, pendingLoot.target, pendingLoot.loot);
              }
              releaseSharedWorldBattleCombatRender("basic-impact-frame-5");
            });
            optimisticRecord.impactAt = performance.now() + Math.max(0, impactDelay);
          } else {
            triggerSharedWorldBattleCast(self, opponent, "basic_attack", 0, true);
          }
          if (sharedWorldBattlePendingLethalId === battleId) {
            scheduleSharedWorldBattleResultAfterFinalCast({
              ...battle,
              status: "client-finishing",
              winner: self,
              loser: opponent,
              hp: { ...(battle.hp || {}), [opponent]: 0 },
              reward: { transferred: 0, items: [], pending: true },
            }, self);
          }
        }
        traceSharedWorldPvpTrainingRuntime("answer-submit", { battleId: clean(battle.id), actor: clean(activeWorldUsername()), answerLength: answer.length, panel: "shared-training-question-panel" });
        worldBattleAnswer.value = "";
        const startedAt = performance.now();
        try {
          const response = await fetchAuthJson("/world/battle/answer", {
            method: "POST",
            body: JSON.stringify({
              battle_id: clean(battle.id),
              answer,
              client_action_id: clientActionId,
              defer_next_question: clientFirst,
              ...activeWorldActorPayload(),
            }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) {
            traceSharedWorldBattleLifecycle("answer-response-rejected", { battleId, lifecycleGeneration });
            return;
          }
          const responseBattle = result && result.battle && typeof result.battle === "object" ? result.battle : {};
          if (clientFirst && clean(responseBattle.status) === "active"
            && (!responseBattle.question || !clean(responseBattle.question.prompt))) {
            responseBattle.question = { ...question, can_answer: false };
          }
          renderSharedWorldBattle(result);
          if (clean(responseBattle.status) !== "active"
            || worldBattleChoices.dataset.combatChoiceSignature !== (choiceSignature || "")) {
            clearSharedWorldBattleAnswerRecovery();
          }
          window.__ftPvpChoiceLatency = {
            clientFirst,
            actionId: clientActionId,
            responseMs: Math.round((performance.now() - startedAt) * 10) / 10,
            at: Date.now(),
          };
          console.info("[FTG][PvpChoiceLatency]", JSON.stringify(window.__ftPvpChoiceLatency));
          if (clientFirst && result && result.battle && clean(result.battle.status) === "active" && sharedWorldBattlePendingLethalId !== battleId) {
            const currentBattle = result.battle;
            const { self } = sharedWorldBattlePlayersForView(currentBattle);
            const point = sharedWorldBattleActorPoints.get(sharedWorldBattleUserKey(self)) || { x: 0.5, y: 0.58 };
            void fetchAuthJson("/world/battle/move", {
              method: "POST",
              timeoutMs: 0,
              body: JSON.stringify({
                battle_id: clean(currentBattle.id),
                x: point.x,
                y: point.y,
                current_x: point.x,
                current_y: point.y,
                training_kind: clean(question.training_kind || question.trainingKind || sharedWorldTrainingBasicSkillKind),
                refresh_question: true,
                question_request_id: `answer_${clientActionId}`,
                ...activeWorldActorPayload(),
              }),
            }).then((nextResponse) => {
              if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) {
                traceSharedWorldBattleLifecycle("answer-preload-response-rejected", { battleId, lifecycleGeneration });
                return;
              }
              renderSharedWorldBattle(nextResponse && nextResponse.payload ? nextResponse.payload : nextResponse);
            }).catch((error) => {
              if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) return;
              setSharedWorldStatus(error && error.message ? error.message : "Could not preload the next PvP question.", "error");
            });
          }
        } catch (error) {
          if (clientActionId) sharedWorldBattleOptimisticActions.delete(clientActionId);
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) return;
          setSharedWorldStatus(error && error.message ? error.message : "Could not cast answer.", "error");
        } finally {
          if (clientFirst) sharedWorldCombatPendingAnswers.delete(pendingKey);
        }
      };

      const castSharedWorldBattleSkill = async (skill = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          return;
        }
        const battleId = clean(battle.id);
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        const remaining = Math.max(0, Math.ceil((sharedWorldBattleSkillCooldownUntil - Date.now()) / 1000));
        if (remaining > 0) {
          setSharedWorldStatus(`Skill cooling down: ${remaining}s.`, "error");
          const players = sharedWorldBattlePlayersForView(battle);
          renderSharedWorldBattleCombatHud(battle, players.self);
          return;
        }
        const { self, opponent } = sharedWorldBattlePlayersForView(battle);
        const currentMp = Math.max(0, Math.round(Number((battle.mp || {})[self] || 0) || 0));
        if (currentMp < 100) {
          renderSharedWorldBattleCombatHud(battle, self);
          setSharedWorldStatus("Battle mana must reach 100% before using Skill Nộ.", "error");
          return;
        }
        const clientActionId = `pvp_ultimate_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
        if (sharedWorldBattleOptimisticActions.has(clientActionId)) return;
        const damagePreview = 35;
        const opponentHp = Math.max(0, Math.round(Number((battle.hp || {})[opponent] ?? 100) || 0));
        if (damagePreview >= opponentHp && opponentHp > 0) {
          sharedWorldBattlePendingLethalId = battleId;
          traceSharedWorldBattleLifecycle("lethal-ultimate-predicted", { battleId, opponent, opponentHp, predictedDamage: damagePreview });
        }
        const impactDelay = triggerSharedWorldBattleCast(self, opponent, "ultimate", damagePreview);
        if (sharedWorldBattlePendingLethalId === battleId) {
          scheduleSharedWorldBattleResultAfterFinalCast({
            ...battle,
            status: "client-finishing",
            winner: self,
            loser: opponent,
            hp: { ...(battle.hp || {}), [opponent]: 0 },
            reward: { transferred: 0, items: [], pending: true },
          }, self);
        }
        sharedWorldBattleOptimisticActions.set(clientActionId, {
          ultimate: true,
          at: performance.now(),
          impactAt: performance.now() + Math.max(0, impactDelay),
        });
        battle.mp = battle.mp && typeof battle.mp === "object" ? battle.mp : {};
        battle.mp[self] = 0;
        sharedWorldBattleHudSignature = "";
        renderSharedWorldBattleCombatHud(battle, self);
        traceSharedWorldPvpTrainingRuntime("ultimate-submit", {
          battleId, actor: clean(self), target: clean(opponent), skill: clean(skill), clientActionId,
          combatFunction: "triggerSharedWorldTrainingEarthquake", animationStarted: true, impactDelay,
        });
        try {
          const response = await fetchAuthJson("/world/battle/skill", {
            method: "POST",
            body: JSON.stringify({ battle_id: battleId, skill: clean(skill), client_action_id: clientActionId, ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) {
            traceSharedWorldBattleLifecycle("skill-response-rejected", { battleId, lifecycleGeneration });
            return;
          }
          sharedWorldBattleSkillCooldownBattleId = battleId;
          sharedWorldBattleSkillCooldownUntil = Date.now() + sharedWorldBattleSkillCooldownSeconds * 1000;
          sharedWorldBattleHudSignature = "";
          renderSharedWorldBattle(result);
          traceSharedWorldPvpTrainingRuntime("ultimate-confirmed", { battleId, actor: clean(self), target: clean(opponent), clientActionId });
        } catch (error) {
          sharedWorldBattleOptimisticActions.delete(clientActionId);
          if (sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.id) === battleId) {
            const activeBattle = sharedWorldBattleState.battle;
            activeBattle.mp = activeBattle.mp && typeof activeBattle.mp === "object" ? activeBattle.mp : {};
            activeBattle.mp[self] = currentMp;
            sharedWorldBattleHudSignature = "";
            renderSharedWorldBattleCombatHud(activeBattle, self);
          }
          traceSharedWorldPvpTrainingRuntime("ultimate-failed", { battleId, actor: clean(self), target: clean(opponent), clientActionId, error: clean(error && error.message) });
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) return;
          setSharedWorldStatus(error && error.message ? error.message : "Could not cast skill.", "error");
        }
      };

      const forfeitSharedWorldBattle = async (silent = false) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          return;
        }
        const battleId = clean(battle.id);
        const lifecycleGeneration = sharedWorldBattleLifecycleGeneration;
        traceSharedWorldBattleLifecycle("forfeit-request", { battleId, silent: Boolean(silent), lifecycleGeneration });
        try {
          const response = await fetchAuthJson("/world/battle/forfeit", {
            method: "POST",
            body: JSON.stringify({ battle_id: clean(battle.id), ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          if (!sharedWorldBattleAsyncStillCurrent(battleId, lifecycleGeneration)) {
            traceSharedWorldBattleLifecycle("forfeit-response-rejected", { battleId, silent: Boolean(silent), lifecycleGeneration });
            return;
          }
          if (silent) {
            sharedWorldBattleState = result;
          } else {
            renderSharedWorldBattle(result);
          }
          if (!silent) {
            setSharedWorldStatus("Battle forfeited. Wager transferred to the opponent.", "error");
          }
        } catch (error) {
          if (!silent) {
            setSharedWorldStatus(error && error.message ? error.message : "Could not forfeit battle.", "error");
          }
        }
      };

      const forfeitSharedWorldBattleOnUnload = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active" || !authToken) {
          return;
        }
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const base = candidates[0] || "";
        if (!base) {
          return;
        }
        try {
          fetch(`${base}/world/battle/forfeit`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${authToken}`,
              ...(antiRobotToken ? { [ANTI_ROBOT_HEADER]: antiRobotToken } : {}),
            },
            body: JSON.stringify({ battle_id: clean(battle.id), ...activeWorldActorPayload() }),
            keepalive: true,
            mode: "cors",
          });
        } catch (error) {
          // Best-effort forfeit on tab close.
        }
      };

      // 2026-08-13: deterministic browser proof for exit/result races without mutating server battle state.
      window.__ftPvpExitLifecycleProbe = async () => {
        if (!worldModal || !worldBattleModal || !worldBattleResult) {
          return { ok: false, reason: "battle-dom-missing" };
        }
        const savedState = sharedWorldBattleState;
        const savedGeneration = sharedWorldBattleLifecycleGeneration;
        const savedDismissed = sharedWorldBattleDismissedFinishedId;
        const savedShown = sharedWorldBattleResultShownId;
        const savedDeferred = sharedWorldBattleDeferredCombatPayload;
        const savedRenderLock = sharedWorldBattleCombatRenderLockUntil;
        const savedWorldOpen = worldModal.classList.contains("is-open");
        const savedBattleOpen = worldBattleModal.classList.contains("is-open");
        const probeId = `pvp-exit-probe-${Date.now()}`;
        const battle = {
          id: probeId,
          status: "finished",
          players: ["probe_self", "probe_enemy"],
          winner: "probe_enemy",
          loser: "probe_self",
          profiles: {
            probe_self: { display_name: "Probe Self", gender: "male", level: 1 },
            probe_enemy: { display_name: "Probe Enemy", gender: "female", level: 1 },
          },
          hp: { probe_self: 0, probe_enemy: 50 },
          mp: { probe_self: 0, probe_enemy: 30 },
          reward: { transferred: 0, items: [] },
          log: [],
          question: {},
        };
        try {
          worldModal.classList.add("is-open");
          worldBattleModal.classList.add("is-open");
          sharedWorldBattleState = { battle };
          sharedWorldBattleResultShownId = "";
          sharedWorldBattleClosedIds.delete(probeId);
          renderSharedWorldBattleResult(battle, "probe_self");
          renderSharedWorldBattleResult(battle, "probe_self");
          let staleTimerRan = 0;
          queueSharedWorldBattleVisualTimeout(() => { staleTimerRan += 1; }, 20);
          sharedWorldBattleDeferredCombatPayload = { battle: { ...battle, updated_epoch: Date.now() / 1000, updated_seq: 3 } };
          sharedWorldBattleCombatRenderLockUntil = performance.now() + 3000;
          closeSharedWorldBattleLifecycle(probeId, "runtime-probe-exit");
          worldBattleModal.classList.remove("is-open");
          releaseSharedWorldBattleCombatRender("runtime-probe-late-impact");
          renderSharedWorldBattle({ battle: { ...battle, updated_epoch: Date.now() / 1000, updated_seq: 2 } });
          await new Promise((resolve) => window.setTimeout(resolve, 60));
          const trace = (Array.isArray(window.__ftPvpLifecycleTrace) ? window.__ftPvpLifecycleTrace : [])
            .filter((row) => row.battleId === probeId);
          const count = (stage) => trace.filter((row) => row.stage === stage).length;
          const result = {
            ok: count("result-opened") === 1
              && count("result-duplicate-rejected") === 1
              && count("render-rejected-closed") === 1
              && count("deferred-render-rejected") === 1
              && count("timer-rejected") === 1
              && count("callback-error") === 0
              && staleTimerRan === 0
              && !worldBattleModal.classList.contains("is-open"),
            battleId: probeId,
            resultOpened: count("result-opened"),
            duplicateResultsRejected: count("result-duplicate-rejected"),
            lateFinishedSnapshotsRejected: count("render-rejected-closed"),
            lateDeferredSnapshotsRejected: count("deferred-render-rejected"),
            staleTimersRejected: count("timer-rejected"),
            callbackErrors: count("callback-error"),
            staleTimerRan,
            modalOpenAfterLateImpact: worldBattleModal.classList.contains("is-open"),
            trace,
          };
          window.__ftPvpExitLifecycleProbeResult = result;
          console.info("[FTG][PvpExitLifecycleProbe]", result);
          return result;
        } finally {
          setSharedWorldBattleResultOpen(false);
          sharedWorldBattleState = savedState;
          sharedWorldBattleLifecycleGeneration = Math.max(sharedWorldBattleLifecycleGeneration, savedGeneration);
          sharedWorldBattleDismissedFinishedId = savedDismissed;
          sharedWorldBattleResultShownId = savedShown;
          sharedWorldBattleDeferredCombatPayload = savedDeferred;
          sharedWorldBattleCombatRenderLockUntil = savedRenderLock;
          sharedWorldBattleClosedIds.delete(probeId);
          worldModal.classList.toggle("is-open", savedWorldOpen);
          worldBattleModal.classList.toggle("is-open", savedBattleOpen);
        }
      };

      // 2026-08-13: prove the result waits for impact and loser disappearance.
      window.__ftPvpFinalCastResultProbe = async () => {
        if (!worldModal || !worldBattleModal || !worldBattleResult || !worldBattleLeft || !worldBattleRight) {
          return { ok: false, reason: "battle-dom-missing" };
        }
        const savedState = sharedWorldBattleState;
        const savedShown = sharedWorldBattleResultShownId;
        const savedFinishing = sharedWorldBattleFinishing;
        const savedFinishingId = sharedWorldBattleFinishingId;
        const savedImpactAt = sharedWorldBattleFinalImpactAt;
        const savedWorldOpen = worldModal.classList.contains("is-open");
        const savedBattleOpen = worldBattleModal.classList.contains("is-open");
        const self = clean(activeWorldUsername()) || "probe_self";
        const loser = "probe_loser";
        const probeId = `pvp-final-cast-probe-${Date.now()}`;
        const battle = {
          id: probeId,
          status: "finished",
          players: [self, loser],
          winner: self,
          loser,
          profiles: {
            [self]: { display_name: "Probe Winner", gender: "female", level: 8 },
            [loser]: { display_name: "Probe Loser", gender: "male", level: 8 },
          },
          hp: { [self]: 60, [loser]: 0 },
          mp: { [self]: 0, [loser]: 0 },
          positions: { [self]: { x: 0.3, y: 0.62 }, [loser]: { x: 0.7, y: 0.62 } },
          reward: { transferred: 0, items: [] },
        };
        try {
          worldModal.classList.add("is-open");
          worldBattleModal.classList.add("is-open");
          sharedWorldBattleState = { battle };
          sharedWorldBattleResultShownId = "";
          sharedWorldBattleFinishing = false;
          sharedWorldBattleFinishingId = "";
          sharedWorldBattleClosedIds.delete(probeId);
          renderSharedWorldBattlePlayer(worldBattleLeft, battle, self, "left");
          renderSharedWorldBattlePlayer(worldBattleRight, battle, loser, "right");
          clearSharedWorldBattleVisualState();
          sharedWorldBattleFinalImpactAt = performance.now() + 320;
          const startedAt = performance.now();
          scheduleSharedWorldBattleResultAfterFinalCast({ ...battle, status: "client-finishing", reward: { transferred: 0, items: [], pending: true } }, self);
          window.setTimeout(() => scheduleSharedWorldBattleResultAfterFinalCast({ ...battle, reward: { transferred: 2, items: [] } }, self), 80);
          await new Promise((resolve) => window.setTimeout(resolve, 160));
          const beforeImpact = {
            elapsed: Math.round(performance.now() - startedAt),
            resultOpen: worldBattleResult.classList.contains("is-open"),
            loserDefeated: worldBattleRight.classList.contains("is-battle-defeated"),
          };
          await new Promise((resolve) => window.setTimeout(resolve, 410));
          const afterImpact = {
            elapsed: Math.round(performance.now() - startedAt),
            resultOpen: worldBattleResult.classList.contains("is-open"),
            loserDefeated: worldBattleRight.classList.contains("is-battle-defeated"),
          };
          await new Promise((resolve) => window.setTimeout(resolve, 760));
          const afterVanish = {
            elapsed: Math.round(performance.now() - startedAt),
            resultOpen: worldBattleResult.classList.contains("is-open"),
            loserDefeated: worldBattleRight.classList.contains("is-battle-defeated"),
          };
          const trace = (Array.isArray(window.__ftPvpLifecycleTrace) ? window.__ftPvpLifecycleTrace : [])
            .filter((row) => row.battleId === probeId);
          const stages = trace.map((row) => row.stage);
          const result = {
            ok: !beforeImpact.resultOpen
              && !beforeImpact.loserDefeated
              && !afterImpact.resultOpen
              && afterImpact.loserDefeated
              && afterVanish.resultOpen
              && clean(worldBattleResultCopy && worldBattleResultCopy.textContent).includes("2 crystals")
              && stages.indexOf("loser-vanishing") < stages.indexOf("result-opened"),
            battleId: probeId,
            beforeImpact,
            afterImpact,
            afterVanish,
            resultCopy: clean(worldBattleResultCopy && worldBattleResultCopy.textContent),
            stages,
          };
          window.__ftPvpFinalCastResultProbeResult = result;
          console.info("[FTG][PvpFinalCastResultProbe]", JSON.stringify(result));
          return result;
        } finally {
          if (sharedWorldBattleFinishTimer) window.clearTimeout(sharedWorldBattleFinishTimer);
          sharedWorldBattleFinishTimer = 0;
          clearSharedWorldBattleVisualState();
          setSharedWorldBattleResultOpen(false);
          sharedWorldBattleState = savedState;
          sharedWorldBattleResultShownId = savedShown;
          sharedWorldBattleFinishing = savedFinishing;
          sharedWorldBattleFinishingId = savedFinishingId;
          sharedWorldBattleFinalImpactAt = savedImpactAt;
          sharedWorldBattleClosedIds.delete(probeId);
          worldModal.classList.toggle("is-open", savedWorldOpen);
          worldBattleModal.classList.toggle("is-open", savedBattleOpen);
        }
      };

      // 2026-08-13: prove a stalled three-choice question cannot remain locked forever.
      window.__ftPvpAnswerLockRecoveryProbe = async () => {
        if (!worldModal || !worldBattleModal || !worldBattleChoices) return { ok: false, reason: "battle-dom-missing" };
        const savedState = sharedWorldBattleState;
        const savedWorldOpen = worldModal.classList.contains("is-open");
        const savedBattleOpen = worldBattleModal.classList.contains("is-open");
        const savedLoading = sharedWorldBattleLoading;
        const probeId = `pvp-lock-probe-${Date.now()}`;
        const pendingKey = `pvp:${probeId}:question`;
        const signature = "pvp-lock-probe-signature";
        try {
          worldModal.classList.add("is-open");
          worldBattleModal.classList.add("is-open");
          sharedWorldBattleState = { battle: { id: probeId, status: "active", players: [clean(activeWorldUsername()) || "probe", "enemy"] } };
          sharedWorldBattleLoading = true;
          sharedWorldBattleLoadingAt = Date.now();
          worldBattleChoices.innerHTML = '<button data-combat-choice="a" disabled class="is-correct-preview">A</button>';
          worldBattleChoices.dataset.combatChoiceSignature = signature;
          worldBattleChoices.dataset.combatChoiceLocked = "1";
          sharedWorldCombatPendingAnswers.add(pendingKey);
          scheduleSharedWorldBattleAnswerRecovery(probeId, pendingKey, signature);
          await new Promise((resolve) => window.setTimeout(resolve, 3750));
          const button = worldBattleChoices.querySelector("[data-combat-choice]");
          const result = {
            ok: worldBattleChoices.dataset.combatChoiceLocked === "0"
              && !sharedWorldCombatPendingAnswers.has(pendingKey)
              && Boolean(button && !button.disabled && !button.classList.contains("is-correct-preview")),
            locked: worldBattleChoices.dataset.combatChoiceLocked,
            pending: sharedWorldCombatPendingAnswers.has(pendingKey),
            buttonDisabled: Boolean(button && button.disabled),
          };
          console.info("[FTG][PvpAnswerLockRecoveryProbe]", JSON.stringify(result));
          return result;
        } finally {
          clearSharedWorldBattleAnswerRecovery();
          sharedWorldCombatPendingAnswers.delete(pendingKey);
          worldBattleChoices.replaceChildren();
          worldBattleChoices.dataset.combatChoiceSignature = "";
          worldBattleChoices.dataset.combatChoiceLocked = "0";
          sharedWorldBattleState = savedState;
          sharedWorldBattleLoading = savedLoading;
          sharedWorldBattleLoadingAt = 0;
          worldModal.classList.toggle("is-open", savedWorldOpen);
          worldBattleModal.classList.toggle("is-open", savedBattleOpen);
        }
      };

      // 2026-08-13: prove repeated PvP snapshots no longer repaint the circular energy HUD.
      window.__ftPvpHudStabilityProbe = () => {
        if (!worldBattleCard || !worldTrainingSkillDock || !worldTrainingAvatarButton) {
          return { ok: false, reason: "battle-hud-dom-missing" };
        }
        const previousStats = { ...(window.__ftPvpHudRenderStats || {}) };
        const previousHudSignature = sharedWorldBattleHudSignature;
        const previousOrbitSignature = sharedWorldBattleOrbitSignature;
        const battleId = `pvp-hud-probe-${Date.now()}`;
        const self = "probe_female";
        const battle = {
          id: battleId,
          status: "active",
          profiles: { [self]: { gender: "female", level: 8 } },
          hp: { [self]: 73 },
          mp: { [self]: 86 },
        };
        try {
          sharedWorldBattleHudSignature = "";
          sharedWorldBattleOrbitSignature = "";
          window.__ftPvpHudRenderStats = { calls: 0, writes: 0, skipped: 0, orbitBuilds: 0 };
          for (let index = 0; index < 25; index += 1) renderSharedWorldBattleCombatHud(battle, self);
          battle.mp[self] = 96;
          renderSharedWorldBattleCombatHud(battle, self);
          const stats = { ...(window.__ftPvpHudRenderStats || {}) };
          const result = {
            ok: stats.calls === 26 && stats.writes === 2 && stats.skipped === 24 && stats.orbitBuilds === 1,
            ...stats,
            manaFill: worldTrainingQuickSkill ? worldTrainingQuickSkill.style.getPropertyValue("--skill-mana-fill") : "",
          };
          window.__ftPvpHudStabilityProbeResult = result;
          console.info("[FTG][PvpHudStabilityProbe]", result);
          return result;
        } finally {
          window.__ftPvpHudRenderStats = previousStats;
          sharedWorldBattleHudSignature = previousHudSignature;
          sharedWorldBattleOrbitSignature = previousOrbitSignature;
        }
      };

      // 2026-08-13: deterministic proof that every in-flight Battle path is inert after City exit.
      window.__ftPvpLateAsyncProbe = async () => {
        const savedState = sharedWorldBattleState;
        const savedGeneration = sharedWorldBattleLifecycleGeneration;
        const savedWorldOpen = Boolean(worldModal && worldModal.classList.contains("is-open"));
        const savedBattleOpen = Boolean(worldBattleModal && worldBattleModal.classList.contains("is-open"));
        const battleId = `pvp-async-probe-${Date.now()}`;
        const stages = [
          "state-response-rejected",
          "state-error-rejected",
          "move-response-rejected",
          "answer-response-rejected",
          "answer-preload-response-rejected",
          "skill-response-rejected",
          "forfeit-response-rejected",
        ];
        try {
          if (worldModal) worldModal.classList.add("is-open");
          if (worldBattleModal) worldBattleModal.classList.add("is-open");
          sharedWorldBattleState = { battle: { id: battleId, status: "active" } };
          sharedWorldBattleClosedIds.delete(battleId);
          const generation = sharedWorldBattleLifecycleGeneration;
          closeSharedWorldBattleLifecycle(battleId, "late-async-runtime-probe");
          if (worldBattleModal) worldBattleModal.classList.remove("is-open");
          await Promise.resolve();
          const accepted = sharedWorldBattleAsyncStillCurrent(battleId, generation);
          stages.forEach((stage) => traceSharedWorldBattleLifecycle(stage, {
            battleId,
            lifecycleGeneration: generation,
            probe: true,
          }));
          const trace = (Array.isArray(window.__ftPvpLifecycleTrace) ? window.__ftPvpLifecycleTrace : [])
            .filter((row) => row.battleId === battleId);
          const result = {
            ok: !accepted && stages.every((stage) => trace.some((row) => row.stage === stage)),
            battleId,
            acceptedAfterExit: accepted,
            rejectedPaths: stages.filter((stage) => trace.some((row) => row.stage === stage)),
            callbackErrors: trace.filter((row) => row.stage === "callback-error").length,
          };
          window.__ftPvpLateAsyncProbeResult = result;
          console.info("[FTG][PvpLateAsyncProbe]", result);
          return result;
        } finally {
          sharedWorldBattleState = savedState;
          sharedWorldBattleLifecycleGeneration = Math.max(sharedWorldBattleLifecycleGeneration, savedGeneration);
          sharedWorldBattleClosedIds.delete(battleId);
          if (worldModal) worldModal.classList.toggle("is-open", savedWorldOpen);
          if (worldBattleModal) worldBattleModal.classList.toggle("is-open", savedBattleOpen);
        }
      };

      // 2026-08-13: prove both default characters unlock locally when mana is full and cooldown reaches zero.
      window.__ftPvpUltimateCooldownProbe = () => {
        if (!worldBattleCard || !worldTrainingQuickSkill || !worldBattleModal) return { ok: false, reason: "battle-hud-dom-missing" };
        const savedState = sharedWorldBattleState;
        const savedUntil = sharedWorldBattleSkillCooldownUntil;
        const savedSignature = sharedWorldBattleHudSignature;
        const savedOpen = worldBattleModal.classList.contains("is-open");
        const results = [];
        try {
          worldBattleModal.classList.add("is-open");
          ["female", "male"].forEach((gender) => {
            const self = `probe_${gender}`;
            const battle = {
              id: `pvp-cooldown-${gender}-${Date.now()}`,
              status: "active",
              profiles: { [self]: { gender, level: 8 } },
              hp: { [self]: 100 },
              mp: { [self]: 0 },
            };
            sharedWorldBattleState = { battle };
            sharedWorldBattleSkillCooldownUntil = 0;
            sharedWorldBattleHudSignature = "";
            renderSharedWorldBattleCombatHud(battle, self);
            const empty = {
              disabled: worldTrainingQuickSkill.disabled,
              manaFill: worldTrainingQuickSkill.style.getPropertyValue("--skill-mana-fill"),
              avatarFill: worldTrainingAvatarButton && worldTrainingAvatarButton.style.getPropertyValue("--avatar-mp-fill"),
            };
            battle.mp[self] = 90;
            sharedWorldBattleHudSignature = "";
            renderSharedWorldBattleCombatHud(battle, self);
            const partial = {
              disabled: worldTrainingQuickSkill.disabled,
              manaFill: worldTrainingQuickSkill.style.getPropertyValue("--skill-mana-fill"),
              avatarFill: worldTrainingAvatarButton && worldTrainingAvatarButton.style.getPropertyValue("--avatar-mp-fill"),
            };
            battle.mp[self] = 100;
            sharedWorldBattleSkillCooldownUntil = Date.now() + 2400;
            sharedWorldBattleHudSignature = "";
            renderSharedWorldBattleCombatHud(battle, self);
            const cooling = {
              disabled: worldTrainingQuickSkill.disabled,
              classCooling: worldTrainingQuickSkill.classList.contains("is-cooling"),
              seconds: clean(worldTrainingQuickSkillCooldown && worldTrainingQuickSkillCooldown.textContent),
            };
            sharedWorldBattleSkillCooldownUntil = Date.now() - 1;
            sharedWorldBattleHudSignature = "";
            renderSharedWorldBattleCombatHud(battle, self);
            const ready = {
              disabled: worldTrainingQuickSkill.disabled,
              classCooling: worldTrainingQuickSkill.classList.contains("is-cooling"),
              classReady: worldTrainingQuickSkill.classList.contains("is-ready"),
              meta: clean(worldTrainingQuickSkillMeta && worldTrainingQuickSkillMeta.textContent),
              manaCost: Number(worldTrainingQuickSkill.dataset.worldTrainingManaCost || 0),
              manaFill: worldTrainingQuickSkill.style.getPropertyValue("--skill-mana-fill"),
            };
            results.push({ gender, empty, partial, cooling, ready });
          });
          const result = {
            ok: results.every((row) => row.empty.disabled && row.empty.manaFill === "0%" && row.empty.avatarFill === "0%"
              && row.partial.disabled && row.partial.manaFill === "90%" && row.partial.avatarFill === "90%"
              && row.cooling.disabled && row.cooling.classCooling && Number(row.cooling.seconds) > 0
              && !row.ready.disabled && !row.ready.classCooling && row.ready.classReady
              && row.ready.manaCost === 100 && row.ready.manaFill === "100%" && row.ready.meta === "Ready · 100%"),
            localOnly: true,
            results,
          };
          window.__ftPvpUltimateCooldownProbeResult = result;
          console.info("[FTG][PvpUltimateCooldownProbe]", result);
          return result;
        } finally {
          sharedWorldBattleState = savedState;
          sharedWorldBattleSkillCooldownUntil = savedUntil;
          sharedWorldBattleHudSignature = savedSignature;
          worldBattleModal.classList.toggle("is-open", savedOpen);
        }
      };
      if (new URLSearchParams(window.location.search).get("ft_pvp_ultimate_probe") === "1") {
        window.setTimeout(() => console.info("[FTG][PvpUltimateManaProbe]", JSON.stringify(window.__ftPvpUltimateCooldownProbe())), 0);
      }
      if (clean(params.get("ft_pvp_exit_probe"))) {
        window.setTimeout(() => {
          void window.__ftPvpExitLifecycleProbe()
            .then(() => window.__ftPvpHudStabilityProbe())
            .then(() => window.__ftPvpLateAsyncProbe())
            .then(() => window.__ftPvpUltimateCooldownProbe())
            .then(() => window.__ftPvpFinalCastResultProbe())
            .then(() => window.__ftPvpAnswerLockRecoveryProbe());
        }, 250);
      }

      const sharedWorldSkinArtClass = (skin = {}) => `is-${clean(skin.id || skin.name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "neon-orb"}`;

      const sharedWorldCrystalQuantity = () => {
        const inventory = sharedWorldInventory && sharedWorldInventory.inventory ? sharedWorldInventory.inventory : sharedWorldInventory;
        const items = inventory && inventory.items && typeof inventory.items === "object" ? inventory.items : {};
        const item = items[sharedWorldVocabularyCrystalId] || items.space_v_crystal || items.vocabulary_crystal || {};
        return Math.max(0, Math.round(Number(item.quantity || item.count || 0) || 0));
      };

      const sharedWorldInventoryToneForId = (id = "") => {
        const key = clean(id).toLowerCase();
        if (key === "character_scorpio_5_star_card" || key === "character_scorpio_card") return "scorpio-card";
        if (key === "space_q_spellbook_gold" || key === "leaderboard_space_q_crystal") return "bookgold";
        if (key === "space_q_spellbook_silver") return "booksilver";
        if (key === "space_p_bow_gold" || key === "paragraph_crystal_golden") return "bowgold";
        if (key === "space_p_bow_silver") return "bowsilver";
        if (key === "space_s_sax_gold") return "saxgold";
        if (key === "space_s_sax_silver") return "saxsilver";
        if (key === "space_l_sword_gold") return "swordgold";
        if (key === "space_l_sword_silver") return "swordsilver";
        if (key.includes("cup_gold") || key.includes("cupgold")) return "cupgold";
        if (key.includes("cup_iron") || key.includes("cupiron")) return "cupiron";
        if (key === "vocab_crystal_blue" || key === "vocab_crystal_green") return "easy";
        if (key === "vocab_crystal_yellow" || key === "leaderboard_space_v_crystal" || key === "leaderboard_crystal_rare" || key === "crystal" || key.includes("space_v") || key.includes("spacev")) return "spacev";
        if (key === "leaderboard_crystal_easy") return "easy";
        if (key.includes("gold")) return "golden";
        if (key.includes("yellow")) return "yellow";
        if (key.includes("blue")) return "blue";
        if (key.includes("green")) return "green";
        if (key.includes("badge")) return "badge";
        if (key.includes("rare")) return "rare";
        if (key.includes("easy") || key.includes("review")) return "easy";
        if (key.includes("space_q") || key.includes("spaceq")) return "spaceq";
        if (key.includes("space_w") || key.includes("spacew")) return "spacew";
        if (key.includes("space_v") || key.includes("spacev")) return "spacev";
        return "prism";
      };

      const REWARD_ITEM_DISPLAY = {
        character_scorpio_5_star_card: { name: "Scorpio 5-Star Character Card", use: "Unlocks the Scorpio hero in QM-City, Training Field, and Battle." },
        character_scorpio_card: { name: "Scorpio 5-Star Character Card", use: "Unlocks the Scorpio hero in QM-City, Training Field, and Battle." },
        crystal: { name: "Golden Axe", use: "Forged by defeating vocabulary slimes and clean answers." },
        vocab_crystal_yellow: { name: "Golden Axe", use: "Forged when a new vocabulary word is learned cleanly." },
        vocab_crystal_blue: { name: "Silver Axe", use: "Forged when a word returns after 10 drills and 5 shuffle rounds and is answered correctly." },
        vocab_crystal_green: { name: "Silver Axe", use: "Forged by correctly recalling vocabulary already stored in memory." },
        leaderboard_space_v_crystal: { name: "Golden Axe", use: "Awarded for Space_V leaderboard standing." },
        leaderboard_crystal_rare: { name: "Golden Axe", use: "Awarded from leaderboard ranks for strong first-time vocabulary progress." },
        leaderboard_crystal_easy: { name: "Silver Axe", use: "Awarded from leaderboard ranks for steady vocabulary review progress." },
        leaderboard_space_q_crystal: { name: "Golden Magic Book", use: "Awarded from Space_Q leaderboard ranks." },
        space_q_spellbook_gold: { name: "Golden Magic Book", use: "Earned by completing a new Space_Q node correctly and awarded from Space_Q leaderboard ranks." },
        space_q_spellbook_silver: { name: "Silver Magic Book", use: "Earned by completing a Space_Q review node correctly." },
        paragraph_crystal_golden: { name: "Golden Magic Bow", use: "Legacy Space_P reward now displayed as a Golden Magic Bow." },
        space_p_bow_gold: { name: "Golden Magic Bow", use: "Earned by completing a new Space_P sentence correctly and awarded from Space_P leaderboard ranks." },
        space_p_bow_silver: { name: "Silver Magic Bow", use: "Earned by correctly recalling a Space_P sentence during review." },
        space_s_sax_gold: { name: "Golden Devil Wings", use: "Earned by reading a new Space_S speaking sentence correctly and awarded from Space_S leaderboard ranks." },
        space_s_sax_silver: { name: "Silver Devil Wings", use: "Earned by correctly recalling a Space_S speaking sentence during review and awarded from Space_S leaderboard ranks." },
        space_l_sword_gold: { name: "Golden Great Sword", use: "Earned by completing a new Space_L listening sentence correctly and awarded from Space_L leaderboard ranks." },
        space_l_sword_silver: { name: "Silver Great Sword", use: "Earned by correctly recalling a Space_L listening sentence during review and awarded from Space_L leaderboard ranks." },
        space_w_cup_gold: { name: "Golden Mastery Cup", use: "Earned when a new Space_W sentence is answered correctly the first time." },
        space_w_cup_iron: { name: "Silver Practice Cup", use: "Earned by correctly recalling a Space_W sentence during review." },
      };
      const mergeRewardDisplayItems = (list) => {
        const merged = [];
        const byName = new Map();
        (Array.isArray(list) ? list : []).forEach((it) => {
          const name = clean(it && it.name) || "Reward Item";
          if (byName.has(name)) {
            byName.get(name).quantity += Math.max(0, Math.floor(Number(it.quantity || 0) || 0));
          } else {
            const copy = { ...it, quantity: Math.max(0, Math.floor(Number(it.quantity || 0) || 0)) };
            byName.set(name, copy);
            merged.push(copy);
          }
        });
        return merged;
      };
      const canonicalRewardName = (id, fallback) => {
        const key = clean(id).toLowerCase();
        return (REWARD_ITEM_DISPLAY[key] && REWARD_ITEM_DISPLAY[key].name) || clean(fallback) || "Reward Item";
      };
      const canonicalRewardUse = (id, fallback) => {
        const key = clean(id).toLowerCase();
        return (REWARD_ITEM_DISPLAY[key] && REWARD_ITEM_DISPLAY[key].use) || preserveQuestionText(fallback) || "Stores learning energy for future item upgrades.";
      };

      const sharedWorldInventoryItemsForDisplay = () => {
        const inventory = sharedWorldInventory && sharedWorldInventory.inventory ? sharedWorldInventory.inventory : sharedWorldInventory;
        const items = Object.values((inventory && inventory.items) || {})
          .map((item) => ({
            id: clean(item && (item.id || item.item_id) || "crystal").toLowerCase() || "crystal",
            name: canonicalRewardName(item && (item.id || item.item_id), item && item.name),
            use: canonicalRewardUse(item && (item.id || item.item_id), item && (item.use || item.description)),
            quantity: Math.max(0, Math.floor(Number(item && (item.quantity || item.count) || 0) || 0)),
          }))
          .filter((item) => item.quantity > 0);
        if (!items.length) {
          items.push({
            id: sharedWorldVocabularyCrystalId,
            name: "Vocabulary Crystal",
            use: "Currency for QM-City transformations.",
            quantity: 0,
          });
        }
        return mergeRewardDisplayItems(items).sort((a, b) => {
          const order = ["character_scorpio_5_star_card", "character_scorpio_card", "space_q_spellbook_gold", "leaderboard_space_q_crystal", "space_q_spellbook_silver", "space_p_bow_gold", "paragraph_crystal_golden", "space_p_bow_silver", "space_s_sax_gold", "space_s_sax_silver", "space_l_sword_gold", "space_l_sword_silver", "space_w_cup_gold", "space_w_cup_iron", "leaderboard_space_v_crystal", "leaderboard_crystal_rare", "leaderboard_crystal_easy", "vocab_crystal_yellow", "vocab_crystal_blue", "vocab_crystal_green", "crystal"];
          return (order.indexOf(a.id) < 0 ? 99 : order.indexOf(a.id)) - (order.indexOf(b.id) < 0 ? 99 : order.indexOf(b.id));
        });
      };

      const sharedWorldInventoryQuantity = (id = "") => {
        const key = clean(id).toLowerCase();
        if (!key) return 0;
        const inventory = sharedWorldInventory && sharedWorldInventory.inventory ? sharedWorldInventory.inventory : sharedWorldInventory;
        const items = inventory && inventory.items && typeof inventory.items === "object" ? inventory.items : {};
        const direct = items[key] || null;
        if (direct) return Math.max(0, Math.floor(Number(direct.quantity || direct.count || 0) || 0));
        return Object.values(items).reduce((total, item) => {
          const itemKey = clean(item && (item.id || item.item_id)).toLowerCase();
          return total + (itemKey === key ? Math.max(0, Math.floor(Number(item.quantity || item.count || 0) || 0)) : 0);
        }, 0);
      };

      const sharedWorldProfileDefaultCharacterKind = () => (
        clean(currentAuthProfile && (currentAuthProfile.gender || currentAuthProfile.sex || "")).toLowerCase() === "female" ? "female" : "male"
      );

      const sharedWorldAdminCanUseAllCharacters = () => clean(currentAuthUsername).toLowerCase() === "hung";

      const sharedWorldActualCharacterKind = () => {
        const self = typeof getSharedWorldSelfPosition === "function" ? getSharedWorldSelfPosition() : null;
        const ownKey = clean(currentAuthUsername).toLowerCase();
        const roster = ownKey && sharedWorldRoster ? sharedWorldRoster.get(ownKey) : null;
        return normalizeSharedWorldCharacterKind(
          (roster && (roster.characterKind || roster.character_kind))
          || (self && (self.characterKind || self.character_kind))
          || (currentAuthProfile && (currentAuthProfile.character_kind || currentAuthProfile.characterKind))
          || sharedWorldProfileDefaultCharacterKind()
        );
      };

      const sharedWorldCurrentCharacterKind = () => {
        const carouselKind = clean(sharedWorldCharacterCarouselKind).toLowerCase();
        if (sharedWorldCharacterPickerOpen && ["male", "female", "scorpio"].includes(carouselKind)) {
          return carouselKind;
        }
        return sharedWorldActualCharacterKind();
      };

      const sharedWorldAvailableCharacterCards = () => {
        const defaultKind = sharedWorldProfileDefaultCharacterKind();
        const adminAll = sharedWorldAdminCanUseAllCharacters();
        const defaults = adminAll ? ["male", "female"] : [defaultKind];
        const cards = defaults.map((kind) => ({
          kind,
          name: kind === "female" ? "Female Default" : "Male Default",
          rarity: "Starter",
          owned: true,
          image: kind === "female" ? "/future-assets/character_female_default_card.png" : "/future-assets/character_male_default_card.png",
        }));
        const hasScorpio = adminAll || sharedWorldInventoryQuantity("character_scorpio_5_star_card") > 0 || sharedWorldInventoryQuantity("character_scorpio_card") > 0;
        cards.push({
          kind: "scorpio",
          name: "Scorpio",
          rarity: "5-Star",
          owned: hasScorpio,
          image: "/future-assets/character_scorpio_card.png",
        });
        return cards;
      };

      const sharedWorldCharacterCarouselSlot = (cards = [], kind = "", activeKind = "") => {
        const rows = Array.isArray(cards) ? cards : [];
        const index = rows.findIndex((card) => card && card.kind === kind);
        const activeIndex = rows.findIndex((card) => card && card.kind === activeKind);
        if (index < 0 || activeIndex < 0) return "";
        if (rows.length <= 1) return "center";
        const delta = (index - activeIndex + rows.length) % rows.length;
        if (delta === 0) return "center";
        if (rows.length === 2) return "right";
        if (delta === 1) return "right";
        return "left";
      };

      const centerSharedWorldCharacterCard = (kind = "", smooth = true) => {
        void kind;
        void smooth;
      };

      const renderSharedWorldCharacterCards = () => {
        if (!worldCharacterGrid) return;
        const focusKind = sharedWorldCurrentCharacterKind();
        const actualKind = sharedWorldActualCharacterKind();
        const cards = sharedWorldAvailableCharacterCards();
        const focusCard = cards.find((card) => card && card.kind === focusKind) || null;
        worldCharacterGrid.classList.toggle("has-locked-preview", Boolean(focusCard && !focusCard.owned));
        const liveKinds = new Set(cards.map((card) => card.kind));
        worldCharacterGrid.querySelectorAll("[data-character-kind]").forEach((node) => {
          if (!liveKinds.has(node.dataset.characterKind || "")) node.remove();
        });
        cards.forEach((card) => {
          let button = worldCharacterGrid.querySelector(`[data-character-kind="${CSS.escape(card.kind)}"]`);
          if (!button) {
            button = document.createElement("article");
            button.className = "ft-world-character-pick";
            button.dataset.characterKind = card.kind;
            worldCharacterGrid.appendChild(button);
          }
          const slot = sharedWorldCharacterCarouselSlot(cards, card.kind, focusKind);
          button.className = "ft-world-character-pick";
          button.classList.toggle("is-active", card.kind === actualKind);
          button.classList.toggle("is-preview", card.kind === focusKind && card.kind !== actualKind);
          button.classList.toggle("is-left", slot === "left");
          button.classList.toggle("is-center", slot === "center");
          button.classList.toggle("is-right", slot === "right");
          button.classList.toggle("is-locked", !card.owned);
          button.setAttribute("role", "button");
          button.tabIndex = !sharedWorldCharacterChanging ? 0 : -1;
          button.setAttribute("aria-label", `${card.kind === actualKind ? "Current" : card.owned ? "Select" : "Locked preview"} ${card.name}`);
          if (sharedWorldCharacterChanging) {
            button.setAttribute("aria-disabled", "true");
          } else {
            button.removeAttribute("aria-disabled");
          }
          const cardImage = sharedWorldCharacterAssetState.objectUrls.get(card.image) || card.image;
          if (button.dataset.characterImage !== cardImage) {
            button.dataset.characterImage = cardImage;
            button.innerHTML = `
              <div class="ft-world-character-art"><img alt="" src="${cardImage}"></div>
            `;
          }
          button.querySelector(".ft-world-character-lock")?.remove();
          if (!card.owned) {
            const lock = document.createElement("span");
            lock.className = "ft-world-character-lock";
            lock.setAttribute("aria-hidden", "true");
            button.appendChild(lock);
          }
        });
        window.requestAnimationFrame(() => centerSharedWorldCharacterCard(focusKind, false));
      };

      const openSharedWorldCharacterPicker = async () => {
        setSharedWorldCloseMenuOpen(false);
        await hydrateSharedWorldCharacterCardDeckFromIdb();
        sharedWorldCharacterPickerOpen = true;
        sharedWorldCharacterCarouselKind = sharedWorldCurrentCharacterKind();
        renderSharedWorldCharacterCards();
        if (worldCharacterModal) {
          worldCharacterModal.classList.add("is-open");
          worldCharacterModal.setAttribute("aria-hidden", "false");
        }
        if (worldCharacterButton) {
          worldCharacterButton.classList.add("is-active");
          worldCharacterButton.setAttribute("aria-pressed", "true");
        }
        void preloadSharedWorldCharacterCardDeck().then(() => {
          if (sharedWorldCharacterPickerOpen) {
            renderSharedWorldCharacterCards();
          }
        });
        await loadSharedWorldInventory();
        renderSharedWorldCharacterCards();
      };

      const closeSharedWorldCharacterPicker = () => {
        sharedWorldCharacterPickerOpen = false;
        sharedWorldCharacterCarouselKind = "";
        if (worldCharacterModal) {
          worldCharacterModal.classList.remove("is-open");
          worldCharacterModal.setAttribute("aria-hidden", "true");
        }
        if (worldCharacterButton) {
          worldCharacterButton.classList.remove("is-active");
          worldCharacterButton.setAttribute("aria-pressed", "false");
        }
      };

      const chooseSharedWorldCharacter = async (kind = "") => {
        const characterKind = normalizeSharedWorldCharacterKind(kind);
        if (!authToken || !["male", "female", "scorpio"].includes(characterKind) || sharedWorldCharacterChanging) return;
        const selectedCard = sharedWorldAvailableCharacterCards().find((card) => card && card.kind === characterKind) || null;
        sharedWorldCharacterCarouselKind = characterKind;
        renderSharedWorldCharacterCards();
        centerSharedWorldCharacterCard(characterKind, true);
        if (selectedCard && !selectedCard.owned) {
          window.__ftCharacterSelectTrace = { action: "locked-preview", kind: characterKind, at: Date.now() };
          console.info("[FTG][CharacterSelect]", window.__ftCharacterSelectTrace);
          setSharedWorldStatus("This character card is locked.", "error");
          return;
        }
        window.__ftCharacterSelectTrace = { action: "select-start", kind: characterKind, at: Date.now() };
        console.info("[FTG][CharacterSelect]", window.__ftCharacterSelectTrace);
        sharedWorldCharacterChanging = true;
        try {
          const response = await fetchAuthJson("/world/character", {
            method: "POST",
            body: JSON.stringify({
              ...activeWorldActorPayload(),
              character_kind: characterKind,
              characterKind,
              map: sharedWorldMapMode,
              map_mode: sharedWorldMapMode,
              mapMode: sharedWorldMapMode,
            }),
          });
          const result = response && response.payload ? response.payload : response;
          if (result && result.inventory) {
            sharedWorldInventory = result.inventory;
          }
          const worldPayload = result && result.world && typeof result.world === "object"
            ? result.world
            : (result && (Array.isArray(result.players) || result.map_mode || result.mapMode) ? result : null);
          if (worldPayload) {
            renderSharedWorld(worldPayload, { lightweightMoveAck: false });
          }
          const selected = normalizeSharedWorldCharacterKind(result && (result.character_kind || result.characterKind || characterKind));
          currentAuthProfile = { ...currentAuthProfile, character_kind: selected, characterKind: selected };
          const activeKey = clean(activeWorldUsername() || currentAuthUsername || "").toLowerCase();
          if (activeKey && sharedWorldRoster) {
            const existing = sharedWorldRoster.get(activeKey) || {};
            sharedWorldRoster.set(activeKey, {
              ...existing,
              username: clean(existing.username || activeWorldUsername() || currentAuthUsername),
              character_kind: selected,
              characterKind: selected,
            });
          }
          if (sharedWorldObstacleEditorAllowed()) {
            sharedWorldAdminCharacterPreview = selected;
            try {
              window.localStorage.setItem(SHARED_WORLD_ADMIN_CHARACTER_STORAGE_KEY, selected);
            } catch (error) {
              if (error && error.name !== "SecurityError") console.warn("[FTG][ScorpioCharacter] preview save failed", error);
            }
            if (worldAdminCharacterSelect) {
              worldAdminCharacterSelect.value = selected;
            }
          }
          const self = typeof ensureSharedWorldSelfNode === "function" ? ensureSharedWorldSelfNode() : null;
          if (self && self.node) {
            const displayName = clean((self.node.querySelector(".ft-world-name-label") || {}).textContent || activeWorldUsername() || currentAuthUsername || "hung");
            self.node.dataset.characterKind = selected;
            renderSharedWorldName(self.node, displayName, selected);
          }
          if (activeKey && typeof CSS !== "undefined" && CSS.escape) {
            document.querySelectorAll(`.ft-world-player[data-username="${CSS.escape(activeKey)}"]`).forEach((node) => {
              node.dataset.characterKind = selected;
              const displayName = clean((node.querySelector(".ft-world-name-label") || {}).textContent || activeKey);
              renderSharedWorldName(node, displayName, selected);
            });
          }
          renderSharedWorldTrainingQuickSkill();
          renderSharedWorldTrainingBasicSkills();
          renderSharedWorldAdminTrainingTestTools();
          window.__ftCharacterSelectTrace = { action: "select-ok", kind: selected, mapMode: sharedWorldMapMode, at: Date.now() };
          console.info("[FTG][CharacterSelect]", window.__ftCharacterSelectTrace);
          setSharedWorldStatus(`Playing as ${selected === "scorpio" ? "Scorpio" : (selected === "female" ? "Female Default" : "Male Default")}.`, "ok");
          sharedWorldCharacterCarouselKind = selected;
          if (selected !== characterKind) {
            renderSharedWorldCharacterCards();
            centerSharedWorldCharacterCard(selected, true);
          }
        } catch (error) {
          sharedWorldCharacterCarouselKind = "";
          renderSharedWorldCharacterCards();
          window.__ftCharacterSelectTrace = { action: "select-error", kind: characterKind, message: error && error.message ? error.message : "", at: Date.now() };
          console.warn("[FTG][CharacterSelect]", window.__ftCharacterSelectTrace);
          setSharedWorldStatus(error && error.message ? error.message : "Could not change character.", "error");
        } finally {
          sharedWorldCharacterChanging = false;
        }
      };

      const renderSharedWorldInventoryInfo = (item = null) => {
        if (!worldInventoryInfo) {
          return;
        }
        const data = item || sharedWorldInventoryItemsForDisplay()[0];
        worldInventoryInfo.innerHTML = "";
        const kicker = document.createElement("span");
        kicker.className = "ft-inventory-info-kicker";
        kicker.textContent = "QM-City currency";
        const name = document.createElement("span");
        name.className = "ft-inventory-info-name";
        name.textContent = clean(data && data.name) || "Vocabulary Crystal";
        const use = document.createElement("span");
        use.className = "ft-inventory-info-use";
        use.textContent = preserveQuestionText(data && data.use) || "Currency for QM-City transformations.";
        const count = document.createElement("span");
        count.className = "ft-inventory-info-count";
        count.textContent = `Owned x${Math.max(0, Math.floor(Number(data && data.quantity || 0) || 0))}`;
        worldInventoryInfo.append(kicker, name, use, count);
      };

      const renderSharedWorldInventoryPanel = () => {
        if (worldCrystalCount) {
          const count = sharedWorldCrystalQuantity();
          worldCrystalCount.textContent = `${count} vocabulary crystal${count === 1 ? "" : "s"} available for transformations.`;
        }
        if (!worldInventoryGrid) {
          return;
        }
        const items = sharedWorldInventoryItemsForDisplay();
        worldInventoryGrid.innerHTML = "";
        for (let index = 0; index < 24; index += 1) {
          const item = items[index] || null;
          const slot = document.createElement(item ? "button" : "span");
          if (item) {
            slot.type = "button";
          }
          slot.className = "ft-inventory-slot";
          if (item) {
            const tone = sharedWorldInventoryToneForId(item.id);
            slot.classList.add("has-item");
            slot.setAttribute("aria-label", `${item.name}, owned ${item.quantity}`);
            slot.innerHTML = `
              <span class="ft-inventory-gem ${tone ? `is-${tone}` : ""}" aria-hidden="true"></span>
              <span class="ft-inventory-slot-count">x${item.quantity}</span>
            `;
            const showItem = () => renderSharedWorldInventoryInfo(item);
            slot.addEventListener("mouseenter", showItem);
            slot.addEventListener("focus", showItem);
            slot.addEventListener("click", showItem);
          } else {
            slot.setAttribute("aria-hidden", "true");
          }
          worldInventoryGrid.appendChild(slot);
        }
        renderSharedWorldInventoryInfo(items[0]);
      };

      const renderSharedWorldPocketInfo = (item = null) => {
        if (!worldPocketInfo) {
          return;
        }
        const data = item || sharedWorldInventoryItemsForDisplay()[0];
        worldPocketInfo.innerHTML = "";
        const kicker = document.createElement("span");
        kicker.className = "ft-inventory-info-kicker";
        kicker.textContent = "Crystal inventory";
        const name = document.createElement("span");
        name.className = "ft-inventory-info-name";
        name.textContent = clean(data && data.name) || "Vocabulary Crystal";
        const use = document.createElement("span");
        use.className = "ft-inventory-info-use";
        use.textContent = preserveQuestionText(data && data.use) || "Currency for QM-City transformations.";
        const count = document.createElement("span");
        count.className = "ft-inventory-info-count";
        count.textContent = `Owned x${Math.max(0, Math.floor(Number(data && data.quantity || 0) || 0))}`;
        worldPocketInfo.append(kicker, name, use, count);
      };

      const renderSharedWorldInventoryModal = () => {
        if (worldLoadoutName) {
          const fullName = clean(currentAuthProfile && (currentAuthProfile.full_name || currentAuthProfile.fullName || currentAuthProfile.display_name || currentAuthProfile.displayName));
          worldLoadoutName.textContent = fullName || clean(currentAuthUsername) || "Character";
        }
        if (worldPocketCount) {
          const count = sharedWorldCrystalQuantity();
          worldPocketCount.textContent = `${count} vocabulary crystal${count === 1 ? "" : "s"} available.`;
        }
        if (!worldPocketGrid) {
          return;
        }
        const items = sharedWorldInventoryItemsForDisplay();
        worldPocketGrid.innerHTML = "";
        for (let index = 0; index < 25; index += 1) {
          const item = items[index] || null;
          const slot = document.createElement(item ? "button" : "span");
          if (item) {
            slot.type = "button";
          }
          slot.className = "ft-inventory-slot";
          if (item) {
            const tone = sharedWorldInventoryToneForId(item.id);
            slot.classList.add("has-item");
            slot.setAttribute("aria-label", `${item.name}, owned ${item.quantity}`);
            slot.innerHTML = `
              <span class="ft-inventory-gem ${tone ? `is-${tone}` : ""}" aria-hidden="true"></span>
              <span class="ft-inventory-slot-count">x${item.quantity}</span>
            `;
            const showItem = () => renderSharedWorldPocketInfo(item);
            slot.addEventListener("mouseenter", showItem);
            slot.addEventListener("focus", showItem);
            slot.addEventListener("click", showItem);
          } else {
            slot.setAttribute("aria-hidden", "true");
          }
          worldPocketGrid.appendChild(slot);
        }
        renderSharedWorldPocketInfo(items[0]);
        renderSharedWorldTrainingLoadoutPanel();
      };

      const openSharedWorldInventory = async () => {
        setSharedWorldCloseMenuOpen(false);
        renderSharedWorldInventoryModal();
        if (worldInventoryModal) {
          worldInventoryModal.classList.add("is-open");
          worldInventoryModal.setAttribute("aria-hidden", "false");
        }
        void loadSharedWorldInventory();
        void loadSharedWorldTrainingInventorySnapshot();
      };

      const closeSharedWorldInventory = () => {
        if (worldInventoryModal) {
          worldInventoryModal.classList.remove("is-open");
          worldInventoryModal.setAttribute("aria-hidden", "true");
        }
      };

      const loadSharedWorldInventory = async () => {
        if (!authToken) {
          return null;
        }
        try {
          const response = await fetchAuthJson("/inventory");
          sharedWorldInventory = response && response.payload ? response.payload : response;
          renderSharedWorldShop();
          renderSharedWorldInventoryModal();
          if (sharedWorldCharacterPickerOpen) {
            renderSharedWorldCharacterCards();
          }
          return sharedWorldInventory;
        } catch (error) {
          sharedWorldInventory = null;
          renderSharedWorldShop();
          renderSharedWorldInventoryModal();
          if (sharedWorldCharacterPickerOpen) {
            renderSharedWorldCharacterCards();
          }
          return null;
        }
      };

      const loadSharedWorldTrainingInventorySnapshot = async () => {
        if (!authToken) {
          return null;
        }
        try {
          const response = await fetchAuthJson("/world/training/state", { timeoutMs: 0, silentTimeout: true });
          const result = response && response.payload ? response.payload : response;
          if (result && result.training) {
            sharedWorldTrainingState = { training: result.training };
            const arena = result.training.arena && typeof result.training.arena === "object" ? result.training.arena : {};
            const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle;
            const battleKind = activeBattle && clean(activeBattle.preferred_question_kind || "");
            sharedWorldTrainingBasicSkillKind = battleKind || clean(arena.basic_skill_kind || arena.basicSkillKind || sharedWorldTrainingBasicSkillKind) || sharedWorldTrainingBasicSkillKind;
            if (Array.isArray(arena.basic_skill_loadout) || Array.isArray(arena.basicSkillLoadout)) {
              const nextLoadout = sharedWorldTrainingNormalizeBasicLoadout(arena.basic_skill_loadout || arena.basicSkillLoadout);
              if (nextLoadout.some(Boolean) || !sharedWorldTrainingBasicLoadout.some(Boolean)) sharedWorldTrainingBasicLoadout = nextLoadout;
            }
            if (sharedWorldMapMode === "training") {
              renderSharedWorldTrainingStats(result.training.stats || {}, arena);
            } else {
              renderSharedWorldTrainingLoadoutPanel();
              renderSharedWorldTrainingQuickSkill();
              renderSharedWorldTrainingBasicOrbit();
              renderSharedWorldTrainingAvatarEnergy(result.training.stats || {}, arena);
            }
          }
          return result;
        } catch (error) {
          renderSharedWorldTrainingLoadoutPanel();
          renderSharedWorldTrainingQuickSkill();
          return null;
        }
      };

      const normalizeSharedWorldKeyboardPass = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        return {
          enabled: Boolean(source.enabled),
          expires_at: clean(source.expires_at || source.expiresAt || ""),
          remaining_seconds: Math.max(0, Math.floor(Number(source.remaining_seconds || source.remainingSeconds || 0) || 0)),
          cost: Math.max(1, Math.floor(Number(source.cost || 10) || 10)),
        };
      };

      const sharedWorldKeyboardRemainingMs = () => {
        const expires = Date.parse(sharedWorldKeyboardPass.expires_at || "");
        if (Number.isFinite(expires)) {
          return Math.max(0, expires - Date.now());
        }
        return Math.max(0, Number(sharedWorldKeyboardPass.remaining_seconds || 0) * 1000);
      };

      const sharedWorldArrowMoveAllowed = () => true;

      const formatSharedWorldCountdown = (ms = 0) => {
        const total = Math.max(0, Math.ceil(ms / 1000));
        const minutes = Math.floor(total / 60);
        const seconds = total % 60;
        return `${minutes}:${String(seconds).padStart(2, "0")}`;
      };

      const renderSharedWorldKeyboardPass = () => {
        if (!worldKeypassButton) {
          return;
        }
        worldKeypassButton.hidden = true;
        worldKeypassButton.setAttribute("aria-hidden", "true");
        const remaining = sharedWorldKeyboardRemainingMs();
        const active = currentAuthIsAdmin || remaining > 0;
        worldKeypassButton.classList.toggle("is-active", active);
        worldKeypassButton.disabled = sharedWorldKeyboardPassBuying;
        if (worldKeypassTitle) {
          worldKeypassTitle.textContent = currentAuthIsAdmin ? "Admin Arrows" : active ? "Arrow Pass" : "Buy Arrows";
        }
        if (worldKeypassStatus) {
          worldKeypassStatus.textContent = currentAuthIsAdmin
            ? "Unlocked for admin"
            : active
              ? `Active ${formatSharedWorldCountdown(remaining)}`
              : `${sharedWorldKeyboardPass.cost || 10} random crystals / 1 hour`;
        }
      };

      const startSharedWorldKeyboardPassTimer = () => {
        if (sharedWorldKeyboardPassTimer) {
          window.clearInterval(sharedWorldKeyboardPassTimer);
        }
        sharedWorldKeyboardPassTimer = window.setInterval(renderSharedWorldKeyboardPass, 1000);
      };

      const stopSharedWorldKeyboardPassTimer = () => {
        if (sharedWorldKeyboardPassTimer) {
          window.clearInterval(sharedWorldKeyboardPassTimer);
          sharedWorldKeyboardPassTimer = 0;
        }
      };

      const loadSharedWorldKeyboardPass = async () => {
        if (!authToken) {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/keyboard-pass");
          const payload = response && response.payload ? response.payload : response;
          sharedWorldKeyboardPass = normalizeSharedWorldKeyboardPass(payload.keyboard_pass || payload.keyboardPass || {});
          renderSharedWorldKeyboardPass();
        } catch (error) {
          renderSharedWorldKeyboardPass();
        }
      };

      const buySharedWorldKeyboardPass = async () => {
        if (!authToken || currentAuthIsAdmin || sharedWorldKeyboardPassBuying || sharedWorldKeyboardRemainingMs() > 0) {
          renderSharedWorldKeyboardPass();
          return;
        }
        sharedWorldKeyboardPassBuying = true;
        renderSharedWorldKeyboardPass();
        try {
          const response = await fetchAuthJson("/world/keyboard-pass", { method: "POST", body: JSON.stringify({}) });
          const payload = response && response.payload ? response.payload : response;
          sharedWorldKeyboardPass = normalizeSharedWorldKeyboardPass(payload.keyboard_pass || payload.keyboardPass || {});
          if (payload.inventory) {
            sharedWorldInventory = { inventory: payload.inventory };
            renderSharedWorldShop();
            renderSharedWorldInventoryModal();
          } else {
            void loadSharedWorldInventory();
          }
          setSharedWorldStatus("Arrow movement unlocked for 1 hour.", "ok");
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not buy arrow movement.", "error");
        } finally {
          sharedWorldKeyboardPassBuying = false;
          renderSharedWorldKeyboardPass();
        }
      };

      const sharedWorldFindSkin = (query = "") => {
        const key = sharedWorldNameKey(query);
        if (!key) return null;
        return normalizeSharedWorldSkins(sharedWorldSkinSettings).find((skin) => sharedWorldNameKey(skin.name) === key || sharedWorldNameKey(skin.id) === key)
          || normalizeSharedWorldSkins(sharedWorldSkinSettings).find((skin) => sharedWorldNameKey(skin.name).includes(key) || key.includes(sharedWorldNameKey(skin.name)))
          || null;
      };

      const showSharedWorldWitchBubble = (message = "", durationMs = 5200) => {
        if (!worldWitchBubble) {
          return;
        }
        window.clearTimeout(sharedWorldWitchBubbleTimer);
        worldWitchBubble.textContent = clean(message);
        worldWitchBubble.classList.toggle("is-visible", Boolean(clean(message)));
        if (durationMs > 0) {
          sharedWorldWitchBubbleTimer = window.setTimeout(() => {
            worldWitchBubble.classList.remove("is-visible");
          }, durationMs);
        }
      };

      const renderSharedWorldShop = () => {
        if (!worldSkinList) {
          return;
        }
        const skins = normalizeSharedWorldSkins(sharedWorldSkinSettings);
        worldSkinList.textContent = "";
        skins.forEach((skin) => {
          const card = document.createElement("section");
          card.className = "ft-world-skin-card";
          card.dataset.skinId = skin.id;
          const art = document.createElement("div");
          art.className = `ft-world-skin-art ${sharedWorldSkinArtClass(skin)}`;
          if (skin.image) {
            art.style.backgroundImage = `url("${skin.image.replace(/"/g, "%22")}")`;
            art.style.backgroundSize = "cover";
            art.style.backgroundPosition = "center";
          }
          const name = document.createElement("div");
          name.className = "ft-world-skin-name";
          name.textContent = skin.name;
          const meta = document.createElement("div");
          meta.className = "ft-world-skin-meta";
          meta.textContent = `${skin.price} vocabulary crystals`;
          const desc = document.createElement("div");
          desc.className = "ft-world-skin-desc";
          desc.textContent = skin.description || "Ask the witch for the price and transformation details.";
          card.append(art, name, meta, desc);
          card.addEventListener("click", () => {
            if (worldShopInput) {
              worldShopInput.value = `how much is ${skin.name}`;
              worldShopInput.focus();
            }
          });
          worldSkinList.appendChild(card);
        });
        renderSharedWorldInventoryPanel();
      };

      const openSharedWorldSkinShop = async () => {
        renderSharedWorldShop();
        if (worldSkinShop) {
          worldSkinShop.classList.add("is-open");
          worldSkinShop.setAttribute("aria-hidden", "false");
        }
        void loadSharedWorldInventory();
        if (worldShopInput) {
          window.setTimeout(() => worldShopInput.focus(), 80);
        }
      };

      const closeSharedWorldSkinShop = () => {
        if (worldSkinShop) {
          worldSkinShop.classList.remove("is-open");
          worldSkinShop.setAttribute("aria-hidden", "true");
        }
      };

      const sharedWorldWitchSpeechBody = (text = "") => {
        const raw = clean(text).replace(/^\s*(mystic\s+witch|witch|phu\s+thuy|wizard|mage)\s*[,:\-]\s*/i, "");
        return raw;
      };

      const sharedWorldWitchShapeRequest = (text = "") => {
        const value = sharedWorldNameKey(sharedWorldWitchSpeechBody(text));
        const hasShopVerb = /\b(change|transform|switch|buy|purchase|shop|store|build|make|create|craft|open|need|want|wand|like)\b/.test(value);
        const hasShopObject = /\b(shape|form|skin|appearance|shop|store|buy|purchase|build|make|create|craft|something|thing|transformation)\b/.test(value);
        return hasShopVerb && hasShopObject;
      };

      const sharedWorldWitchPriceRequest = (text = "") => {
        const raw = sharedWorldWitchSpeechBody(text);
        const match = raw.match(/(?:how\s+much\s+(?:is|for)|price\s+of|cost\s+of|how\s+much\s+does)\s+(.+?)(?:\s+cost)?\??$/i);
        return match ? clean(match[1]) : "";
      };

      const primeSharedWorldWitchCommand = () => {
        if (!worldCommandInput) {
          return;
        }
        const current = clean(worldCommandInput.value);
        if (!current || /^move\s+to\b/i.test(current) || /^witch\s*[,:\-]/i.test(current) || /^mystic\s+witch\s*[,:\-]/i.test(current)) {
          worldCommandInput.value = "Mystic Witch, ";
        } else if (!/^(mystic\s+witch|witch)\s*[,:\-]/i.test(current)) {
          worldCommandInput.value = `Mystic Witch, ${current}`;
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const primeSharedWorldPlayerCommand = (target = null) => {
        if (!worldCommandInput || !target) {
          return;
        }
        const label = sharedWorldTargetLabel(target);
        if (!label) {
          return;
        }
        const current = clean(worldCommandInput.value);
        if (!current || /^move\s+to\b/i.test(current) || /^follow\b/i.test(current)) {
          worldCommandInput.value = `move to ${label}`;
        } else {
          worldCommandInput.value = `${current} ${label}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const handleSharedWorldWitchText = (text = "") => {
        const priceTarget = sharedWorldWitchPriceRequest(text);
        if (priceTarget) {
          const skin = sharedWorldFindSkin(priceTarget);
          const reply = skin
            ? `${skin.name} costs ${skin.price} vocabulary crystals.`
            : "I cannot find that form yet. Please choose a skin from the list.";
          showSharedWorldWitchBubble(reply, 6800);
          if (worldShopReply) {
            worldShopReply.textContent = reply;
          }
          return true;
        }
        if (sharedWorldWitchShapeRequest(text)) {
          if (sharedWorldSelectedTargetKey !== "witch" && !(worldSkinShop && worldSkinShop.classList.contains("is-open"))) {
            setSharedWorldStatus("Move to Mystic Witch first, then ask for transformation.", "error");
            showSharedWorldWitchBubble("Come closer first. Use: move to witch", 5200);
            return true;
          }
          showSharedWorldWitchBubble("All right. Which form do you want to transform into?", 5200);
          window.clearTimeout(sharedWorldShopOpenTimer);
          sharedWorldShopOpenTimer = window.setTimeout(() => {
            void openSharedWorldSkinShop();
          }, 2200);
          return true;
        }
        return false;
      };

      // Added 2026-08-11: attach the city PvP shortcut to the selected actor so it follows that actor's center.
      const ensureSharedWorldTargetBattleAction = (node = null) => {
        if (!node || !node.querySelector) {
          return null;
        }
        let action = node.querySelector(":scope > .ft-world-target-actions");
        if (!action) {
          action = document.createElement("div");
          action.className = "ft-world-target-actions";
          action.innerHTML = `
            <button class="ft-world-target-battle" type="button" title="Battle PvP" aria-label="Invite to Battle PvP">
              <span aria-hidden="true"></span>
              <b>Battle PvP</b>
            </button>
          `;
        }
        const button = action.querySelector(".ft-world-target-battle");
        if (button && button.dataset.battleInviteBound !== "1") {
          button.dataset.battleInviteBound = "1";
          ["pointerdown", "pointerup", "pointercancel"].forEach((eventName) => {
            button.addEventListener(eventName, (event) => event.stopPropagation());
          });
          button.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            const key = clean(node.dataset.username || "").toLowerCase();
            const target = key ? selectSharedWorldTarget(key) : null;
            if (!target || button.disabled || button.classList.contains("is-sending")) {
              return;
            }
            button.classList.add("is-sending");
            try {
              await sendSharedWorldBattleInvite("fireball_vocab", "Would you like to play QM-City Character Battle PvP with me?");
            } finally {
              button.classList.remove("is-sending");
            }
          });
        }
        if (!action.parentNode) node.append(action);
        return action;
      };

      const renderSharedWorldTargetBattleAction = (node = null, target = null) => {
        const action = ensureSharedWorldTargetBattleAction(node);
        const button = action && action.querySelector(".ft-world-target-battle");
        if (!button) {
          return;
        }
        const playing = Boolean(target && target.isPlaying);
        button.disabled = playing;
        button.title = playing ? `${sharedWorldTargetLabel(target)} is already in a battle` : `Battle PvP with ${sharedWorldTargetLabel(target)}`;
      };

      const renderSharedWorldSelectedTarget = () => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!worldTargetChip) {
          return;
        }
        if (!target) {
          worldTargetChip.hidden = true;
          worldTargetChip.textContent = "";
          worldTargetChip.removeAttribute("data-target-key");
          return;
        }
        const label = sharedWorldTargetLabel(target);
        worldTargetChip.hidden = false;
        worldTargetChip.dataset.targetKey = sharedWorldSelectedTargetKey;
        worldTargetChip.textContent = target.isPlaying ? `Playing: ${label}` : `Target: ${label}`;
        worldTargetChip.title = target.isPlaying ? `${label} is already in a battle` : `Insert ${label} into command`;
      };

      const syncSharedWorldNpcRoster = () => {
        if (!worldWitch) {
          return;
        }
        const witch = {
          username: "witch",
          displayName: "Mystic Witch",
          x: 0.74,
          y: 0.34,
          tx: 0.74,
          ty: 0.34,
          npc: "witch",
        };
        sharedWorldRoster.set("witch", witch);
        worldWitch.classList.toggle("is-target-selected", sharedWorldSelectedTargetKey === "witch");
        renderSharedWorldTargetBattleAction(worldWitch, witch);
      };

      const selectSharedWorldTarget = (username = "") => {
        const key = clean(username).toLowerCase();
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!key || key === me) {
          setSharedWorldStatus("Select another player before using target commands.", "error");
          return;
        }
        const target = sharedWorldRoster.get(key);
        if (!target) {
          return;
        }
        sharedWorldSelectedTargetKey = key;
        sharedWorldNodes.forEach((node, itemKey) => {
          node.classList.toggle("is-target-selected", itemKey === key);
        });
        if (worldWitch) {
          worldWitch.classList.toggle("is-target-selected", key === "witch");
        }
        renderSharedWorldSelectedTarget();
        if (key === "witch") {
          showSharedWorldWitchBubble("What do you need from me?", 6500);
        }
        setSharedWorldStatus(`${sharedWorldTargetLabel(target)} selected. Use Interact commands such as move to ${sharedWorldTargetLabel(target)}.`, "ok");
        return target;
      };

      const clearSharedWorldTargetSelection = () => {
        if (!sharedWorldSelectedTargetKey) {
          return;
        }
        sharedWorldSelectedTargetKey = "";
        sharedWorldNodes.forEach((node) => node.classList.remove("is-target-selected"));
        if (worldWitch) {
          worldWitch.classList.remove("is-target-selected");
        }
        renderSharedWorldSelectedTarget();
      };

      const insertSharedWorldTargetIntoCommand = () => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!target || !worldCommandInput) {
          return;
        }
        const label = sharedWorldTargetLabel(target);
        const value = clean(worldCommandInput.value);
        if (!value || /^move\s+to\b/i.test(value)) {
          worldCommandInput.value = `move to ${label}`;
        } else {
          worldCommandInput.value = `${value} ${label}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const renderSharedWorldPositionPoint = () => {
        if (worldPositionChip) {
          if (!sharedWorldSelectedPoint) {
            worldPositionChip.hidden = true;
            worldPositionChip.textContent = "";
          } else {
            const x = Math.round(sharedWorldSelectedPoint.x * 100);
            const y = Math.round(sharedWorldSelectedPoint.y * 100);
            worldPositionChip.hidden = false;
            worldPositionChip.textContent = `Point: ${x}/${y}`;
            worldPositionChip.title = `Insert point ${x} ${y} into command`;
          }
        }
        if (worldPointMarker) {
          if (!sharedWorldSelectedPoint) {
            worldPointMarker.classList.remove("is-visible");
          } else {
            worldPointMarker.style.setProperty("--point-x", `${(sharedWorldSelectedPoint.x * 100).toFixed(2)}%`);
            worldPointMarker.style.setProperty("--point-y", `${(sharedWorldSelectedPoint.y * 100).toFixed(2)}%`);
            worldPointMarker.classList.add("is-visible");
          }
        }
      };

      const showSharedWorldMoveMarker = (point = {}) => {
        if (!worldMoveMarker || !point) {
          return;
        }
        if (sharedWorldMoveMarkerHideTimer) {
          window.clearTimeout(sharedWorldMoveMarkerHideTimer);
          sharedWorldMoveMarkerHideTimer = 0;
        }
        sharedWorldMoveMarkerPoint = {
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        };
        worldMoveMarker.style.setProperty("--move-x", `${(sharedWorldMoveMarkerPoint.x * 100).toFixed(2)}%`);
        worldMoveMarker.style.setProperty("--move-y", `${(sharedWorldMoveMarkerPoint.y * 100).toFixed(2)}%`);
        worldMoveMarker.classList.remove("is-visible", "is-arrived");
        void worldMoveMarker.offsetWidth;
        worldMoveMarker.classList.add("is-visible");
      };

      const hideSharedWorldMoveMarker = (arrived = false) => {
        sharedWorldMoveMarkerPoint = null;
        if (!worldMoveMarker) {
          return;
        }
        if (sharedWorldMoveMarkerHideTimer) {
          window.clearTimeout(sharedWorldMoveMarkerHideTimer);
          sharedWorldMoveMarkerHideTimer = 0;
        }
        if (arrived && worldMoveMarker.classList.contains("is-visible")) {
          worldMoveMarker.classList.remove("is-arrived");
          void worldMoveMarker.offsetWidth;
          worldMoveMarker.classList.add("is-arrived");
          sharedWorldMoveMarkerHideTimer = window.setTimeout(() => {
            worldMoveMarker.classList.remove("is-visible", "is-arrived");
            sharedWorldMoveMarkerHideTimer = 0;
          }, 430);
          return;
        }
        worldMoveMarker.classList.remove("is-visible", "is-arrived");
      };

      const updateSharedWorldMoveMarkerArrival = () => {
        if (!sharedWorldMoveMarkerPoint) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const x = sharedWorldClamp(self.x);
        const y = sharedWorldClamp(self.y);
        const tx = sharedWorldClamp(self.tx, x);
        const ty = sharedWorldClamp(self.ty, y);
        const nearCurrent = Math.hypot(x - sharedWorldMoveMarkerPoint.x, y - sharedWorldMoveMarkerPoint.y) < 0.012;
        const nearTarget = Math.hypot(tx - sharedWorldMoveMarkerPoint.x, ty - sharedWorldMoveMarkerPoint.y) < 0.004;
        const queueActive = sharedWorldHasPath(clean(activeWorldUsername()).toLowerCase());
        if (nearCurrent && nearTarget && !queueActive) {
          hideSharedWorldMoveMarker(true);
        }
      };

      const setSharedWorldPickingPosition = (enabled) => {
        sharedWorldPickingPosition = Boolean(enabled);
        if (worldStage) {
          worldStage.classList.toggle("is-picking-position", sharedWorldPickingPosition);
        }
        if (worldPointButton) {
          worldPointButton.classList.toggle("is-active", sharedWorldPickingPosition);
          worldPointButton.textContent = sharedWorldPickingPosition ? "Pick..." : "Point";
        }
        if (sharedWorldPickingPosition) {
          setSharedWorldStatus("Click a position inside QM-City, then use the Point block with move to.", "ok");
        }
      };

      const sharedWorldPointFromArenaEvent = (event) => {
        if (!worldArena) {
          return null;
        }
        const rect = worldArena.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return null;
        }
        return {
          x: sharedWorldClamp((event.clientX - rect.left) / rect.width),
          y: sharedWorldClamp((event.clientY - rect.top) / rect.height),
        };
      };

      const sharedWorldObstacleEditorAllowed = () => clean(currentAuthUsername).toLowerCase() === "hung";
      const sharedWorldAdminToolsVisible = () => sharedWorldObstacleEditorAllowed() && sharedWorldAdminToolsOpen;
      const setSharedWorldAdminToolsOpen = (open) => {
        sharedWorldAdminToolsOpen = Boolean(open) && sharedWorldObstacleEditorAllowed();
        renderSharedWorldObstacleEditor();
      };

      const sharedWorldObstacleMapSize = () => sharedWorldMapMode === "training"
        ? { width: 3344, height: 941 }
        : { width: 3332, height: 941 };

      const normalizeSharedWorldObstacles = (value = {}) => {
        const source = value && typeof value === "object" ? value : {};
        const strokes = (Array.isArray(source.strokes) ? source.strokes : []).map((raw, index) => {
          const row = raw && typeof raw === "object" ? raw : {};
          const points = (Array.isArray(row.points) ? row.points : []).map((point) => ({
            x: Math.max(0, Math.min(1, Number(point && point.x) || 0)),
            y: Math.max(0, Math.min(1, Number(point && point.y) || 0)),
          })).filter((point, pointIndex, items) => pointIndex === 0 || Math.hypot(point.x - items[pointIndex - 1].x, point.y - items[pointIndex - 1].y) > 0.0002);
          if (points.length < 2) {
            return null;
          }
          return {
            id: clean(row.id || `stroke-${index + 1}`),
            size: Math.max(6, Math.min(180, Number(row.size) || 32)),
            points,
            kind: clean(row.kind).toLowerCase() === "portal" ? "portal" : "obstacle",
            regionId: clean(row.region_id || row.regionId || ""),
            regionName: clean(row.region_name || row.regionName || row.name || "Portal") || "Portal",
            targetMap: ["city", "training"].includes(clean(row.target_map || row.targetMap).toLowerCase()) ? clean(row.target_map || row.targetMap).toLowerCase() : "",
            targetRegionName: clean(row.target_region_name || row.targetRegionName || ""),
            targetX: sharedWorldClamp(row.target_x != null ? row.target_x : row.targetX, 0.5),
            targetY: sharedWorldClamp(row.target_y != null ? row.target_y : row.targetY, 0.5),
          };
        }).filter(Boolean);
        return {
          revision: Math.max(0, Math.floor(Number(source.revision) || 0)),
          updated_at_epoch: Math.max(0, Number(source.updated_at_epoch) || 0),
          strokes,
        };
      };

      const renderSharedWorldObstacleCanvas = () => {
        if (!worldObstacleCanvas) {
          return;
        }
        const context = worldObstacleCanvas.getContext("2d");
        if (!context) {
          return;
        }
        context.clearRect(0, 0, worldObstacleCanvas.width, worldObstacleCanvas.height);
        if (!sharedWorldObstacleEditorAllowed() || sharedWorldObstacleMode === "off" || !["city", "training"].includes(sharedWorldMapMode)) {
          return;
        }
        const rows = sharedWorldObstacles.strokes.slice();
        if (sharedWorldObstacleDraft && Array.isArray(sharedWorldObstacleDraft.points)) {
          rows.push(sharedWorldObstacleDraft);
        }
        rows.forEach((stroke) => {
          const points = Array.isArray(stroke.points) ? stroke.points : [];
          if (points.length < 2) {
            return;
          }
          context.beginPath();
          context.moveTo(points[0].x * worldObstacleCanvas.width, points[0].y * worldObstacleCanvas.height);
          points.slice(1).forEach((point) => context.lineTo(point.x * worldObstacleCanvas.width, point.y * worldObstacleCanvas.height));
          context.lineWidth = Math.max(6, Number(stroke.size) || 32);
          context.lineCap = "round";
          context.lineJoin = "round";
          const eraserDraft = stroke === sharedWorldObstacleDraft && sharedWorldObstacleMode === "erase";
          const portalStroke = clean(stroke.kind).toLowerCase() === "portal";
          if (portalStroke && points.length >= 3) {
            context.closePath();
            context.fillStyle = "rgba(68, 220, 184, 0.14)";
            context.fill();
          }
          context.strokeStyle = eraserDraft
            ? "rgba(255, 88, 112, 0.68)"
            : (portalStroke ? "rgba(96, 255, 222, 0.76)" : "rgba(255, 209, 102, 0.48)");
          context.shadowColor = eraserDraft
            ? "rgba(255, 88, 112, 0.82)"
            : (portalStroke ? "rgba(68, 220, 184, 0.9)" : "rgba(34, 228, 255, 0.66)");
          context.shadowBlur = 12;
          context.stroke();
        });
        context.shadowBlur = 0;
      };

      const renderSharedWorldObstacleEditor = () => {
        const allowed = sharedWorldObstacleEditorAllowed();
        const adminVisible = sharedWorldAdminToolsVisible();
        if (worldObstacleCanvas) {
          const { width, height } = sharedWorldObstacleMapSize();
          if (worldObstacleCanvas.width !== width) worldObstacleCanvas.width = width;
          if (worldObstacleCanvas.height !== height) worldObstacleCanvas.height = height;
          worldObstacleCanvas.setAttribute("aria-label", `${sharedWorldMapMode === "training" ? "Training" : "QM-City"} obstacle editor`);
        }
        if (worldPenTools) {
          worldPenTools.hidden = !adminVisible;
        }
        if (worldAdminToolsButton) {
          worldAdminToolsButton.hidden = !allowed;
          worldAdminToolsButton.classList.toggle("is-active", adminVisible);
          worldAdminToolsButton.setAttribute("aria-pressed", adminVisible ? "true" : "false");
        }
        renderSharedWorldAdminTrainingTestTools();
        renderSharedWorldBattleDesigner();
        if (!allowed && sharedWorldObstacleMode !== "off") {
          sharedWorldObstacleMode = "off";
        }
        const editing = adminVisible && sharedWorldObstacleMode !== "off" && ["city", "training"].includes(sharedWorldMapMode);
        if (worldStage) {
          worldStage.classList.toggle("is-obstacle-editing", editing);
        }
        if (worldPenToggle) {
          const active = sharedWorldObstacleMode === "draw";
          worldPenToggle.classList.toggle("is-active", active);
          worldPenToggle.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldPenPortal) {
          const active = sharedWorldObstacleMode === "portal";
          worldPenPortal.classList.toggle("is-active", active);
          worldPenPortal.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldPenMap) {
          worldPenMap.textContent = sharedWorldMapMode === "training" ? "Map: Training" : "Map: City";
          worldPenMap.title = sharedWorldMapMode === "training" ? "Switch editor to QM-City" : "Switch editor to Training";
        }
        if (worldPenEraser) {
          const active = sharedWorldObstacleMode === "erase";
          worldPenEraser.classList.toggle("is-active", active);
          worldPenEraser.setAttribute("aria-pressed", active ? "true" : "false");
        }
        if (worldPenSizeOutput && worldPenSize) {
          worldPenSizeOutput.value = String(Math.round(Number(worldPenSize.value) || 36));
          worldPenSizeOutput.textContent = worldPenSizeOutput.value;
        }
        renderSharedWorldObstacleCanvas();
      };

      const renderSharedWorldAdminTrainingTestTools = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const battleEnabled = Boolean(battle && clean(battle.status) === "active" && worldBattleModal && worldBattleModal.classList.contains("is-open"));
        const visible = sharedWorldAdminToolsVisible();
        const enabled = visible && (sharedWorldMapMode === "training" || battleEnabled);
        if (worldAdminAnimationTest) {
          worldAdminAnimationTest.hidden = !visible;
        }
        if (worldAdminCharacterSelect) {
          const self = battleEnabled ? { node: worldBattleLeft } : (typeof ensureSharedWorldSelfNode === "function" ? ensureSharedWorldSelfNode() : null);
          worldAdminCharacterSelect.value = sharedWorldCharacterKindFromNode(self && self.node);
          worldAdminCharacterSelect.disabled = !visible;
        }
        if (worldAdminBasicAttack) {
          worldAdminBasicAttack.disabled = !enabled;
        }
        if (worldAdminUltimateAttack) {
          worldAdminUltimateAttack.disabled = !enabled;
        }
      };

      const syncSharedWorldObstacles = (value = {}, map = sharedWorldMapMode) => {
        const next = normalizeSharedWorldObstacles(value);
        const key = map === "training" ? "training" : "city";
        if (next.revision < sharedWorldObstacleSets[key].revision) {
          return;
        }
        sharedWorldObstacleSets[key] = next;
        if (key !== sharedWorldMapMode) {
          return;
        }
        sharedWorldObstacles = next;
        rescueSharedWorldBlockedPositions();
        rescueSharedWorldTrainingBlockedSlimes();
        renderSharedWorldObstacleEditor();
      };

      // Added 2026-08-12: persists small revisioned collision snapshots independently from actor polling.
      const openSharedWorldObstacleCacheDatabase = () => {
        if (sharedWorldObstacleCacheDatabasePromise) return sharedWorldObstacleCacheDatabasePromise;
        sharedWorldObstacleCacheDatabasePromise = new Promise((resolve) => {
          if (!("indexedDB" in window)) return resolve(null);
          const request = indexedDB.open("future_qm_world_obstacle_cache_v1", 1);
          request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains("snapshots")) request.result.createObjectStore("snapshots", { keyPath: "key" });
          };
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(null);
          request.onblocked = () => resolve(null);
        });
        return sharedWorldObstacleCacheDatabasePromise;
      };

      const readSharedWorldObstacleCache = async (key = "") => {
        const database = await openSharedWorldObstacleCacheDatabase();
        if (!database) return null;
        return new Promise((resolve) => {
          const request = database.transaction("snapshots", "readonly").objectStore("snapshots").get(key);
          request.onsuccess = () => resolve(request.result && typeof request.result === "object" ? request.result : null);
          request.onerror = () => resolve(null);
        });
      };

      const writeSharedWorldObstacleCache = async (row = {}) => {
        const database = await openSharedWorldObstacleCacheDatabase();
        if (!database) return false;
        return new Promise((resolve) => {
          const transaction = database.transaction("snapshots", "readwrite");
          transaction.objectStore("snapshots").put(row);
          transaction.oncomplete = () => resolve(true);
          transaction.onerror = () => resolve(false);
          transaction.onabort = () => resolve(false);
        });
      };

      const loadSharedWorldObstacleSnapshot = async (map = "city", expectedRevision = 0) => {
        const key = map === "battle" ? "battle" : (map === "training" ? "training" : "city");
        if (sharedWorldObstacleCacheLoading.has(key)) return sharedWorldObstacleCacheLoading.get(key);
        const loading = (async () => {
          const cached = await readSharedWorldObstacleCache(key);
          const cachedPayload = cached && cached.payload && typeof cached.payload === "object" ? cached.payload : null;
          if (cachedPayload) {
            if (key === "battle") {
              sharedWorldBattleObstacles = normalizeSharedWorldObstacles(cachedPayload);
              rescueSharedWorldBattleBlockedActors();
            }
            else syncSharedWorldObstacles(cachedPayload, key);
          }
          if (cachedPayload && Number(expectedRevision || 0) > 0 && Number(cachedPayload.revision || 0) === Number(expectedRevision)) {
            sharedWorldObstacleCacheLoaded.add(key);
            window.__ftWorldObstacleCacheTrace = { map: key, revision: Number(cachedPayload.revision || 0), source: "indexeddb-revision-hit", strokes: cachedPayload.strokes.length, at: Date.now() };
            return cachedPayload;
          }
          const path = key === "battle" ? "/world/battle/obstacles/snapshot" : `/world/obstacles/snapshot?map=${encodeURIComponent(key)}`;
          const response = await fetchAuthJson(path, {
            timeoutMs: 0,
            ifNoneMatch: clean(cached && cached.etag || ""),
            notModifiedPayload: cachedPayload ? { ok: true, map: key, obstacles: cachedPayload, battle_obstacles: cachedPayload } : null,
          });
          const payload = response && response.payload ? response.payload : response;
          const next = normalizeSharedWorldObstacles(key === "battle" ? payload && payload.battle_obstacles : payload && payload.obstacles);
          if (key === "battle") {
            sharedWorldBattleObstacles = next;
            rescueSharedWorldBattleBlockedActors();
          }
          else syncSharedWorldObstacles(next, key);
          await writeSharedWorldObstacleCache({ key, etag: clean(response && response.etag || ""), payload: next, updatedAt: Date.now() });
          sharedWorldObstacleCacheLoaded.add(key);
          window.__ftWorldObstacleCacheTrace = { map: key, revision: next.revision, source: response && response.notModified ? "etag-304" : "network-update", strokes: next.strokes.length, at: Date.now() };
          return next;
        })().finally(() => sharedWorldObstacleCacheLoading.delete(key));
        sharedWorldObstacleCacheLoading.set(key, loading);
        return loading;
      };

      const sharedWorldObstacleSegmentDistancePx = (point, start, end) => {
        const { width, height } = sharedWorldObstacleMapSize();
        const px = Number(point.x) * width;
        const py = Number(point.y) * height;
        const ax = Number(start.x) * width;
        const ay = Number(start.y) * height;
        const bx = Number(end.x) * width;
        const by = Number(end.y) * height;
        const dx = bx - ax;
        const dy = by - ay;
        const lengthSq = dx * dx + dy * dy;
        if (lengthSq <= 0.0001) {
          return Math.hypot(px - ax, py - ay);
        }
        const ratio = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSq));
        return Math.hypot(px - (ax + ratio * dx), py - (ay + ratio * dy));
      };

      // 2026-08-11: Portal Pen regions use the closed freehand shape, not a hard-coded gate coordinate.
      const sharedWorldPointInsidePortalStroke = (point, stroke) => {
        const points = Array.isArray(stroke && stroke.points) ? stroke.points : [];
        if (!point || points.length < 3) {
          return false;
        }
        let inside = false;
        let previous = points[points.length - 1];
        points.forEach((current) => {
          const crosses = (previous.y > point.y) !== (current.y > point.y);
          if (crosses) {
            const crossingX = previous.x + ((point.y - previous.y) * (current.x - previous.x)) / ((current.y - previous.y) || 1e-9);
            if (point.x < crossingX) {
              inside = !inside;
            }
          }
          previous = current;
        });
        return inside;
      };

      const sharedWorldPortalStrokeDistancePx = (point, stroke) => {
        if (sharedWorldPointInsidePortalStroke(point, stroke)) {
          return 0;
        }
        const points = Array.isArray(stroke && stroke.points) ? stroke.points : [];
        let distance = Number.POSITIVE_INFINITY;
        for (let index = 1; index < points.length; index += 1) {
          distance = Math.min(distance, sharedWorldObstacleSegmentDistancePx(point, points[index - 1], points[index]));
        }
        if (points.length >= 3) {
          distance = Math.min(distance, sharedWorldObstacleSegmentDistancePx(point, points[points.length - 1], points[0]));
        }
        return distance;
      };

      const closeSharedWorldPortalMenu = () => {
        sharedWorldPortalEditingStrokeId = "";
        if (worldPortalMenu) {
          worldPortalMenu.hidden = true;
        }
      };

      const renderSharedWorldPortalTargetRegions = (selectedName = "") => {
        if (!worldPortalTargetMap || !worldPortalTargetRegion) {
          return;
        }
        const targetMap = clean(worldPortalTargetMap.value).toLowerCase();
        const previous = clean(selectedName || worldPortalTargetRegion.value);
        worldPortalTargetRegion.innerHTML = "";
        const centerOption = document.createElement("option");
        centerOption.value = "";
        centerOption.textContent = targetMap === "unlinked" ? "No destination" : "Map center";
        worldPortalTargetRegion.appendChild(centerOption);
        if (["city", "training"].includes(targetMap)) {
          const names = Array.from(new Set((sharedWorldObstacleSets[targetMap].strokes || [])
            .filter((stroke) => clean(stroke.kind).toLowerCase() === "portal")
            .map((stroke) => clean(stroke.regionName))
            .filter(Boolean))).sort((left, right) => left.localeCompare(right));
          names.forEach((name) => {
            const option = document.createElement("option");
            option.value = name;
            option.textContent = name;
            worldPortalTargetRegion.appendChild(option);
          });
        }
        worldPortalTargetRegion.disabled = targetMap === "unlinked";
        worldPortalTargetRegion.value = Array.from(worldPortalTargetRegion.options).some((option) => option.value === previous) ? previous : "";
      };

      const saveSharedWorldPortalMenu = () => {
        const strokeId = clean(sharedWorldPortalEditingStrokeId);
        const regionName = clean(worldPortalRegionName && worldPortalRegionName.value);
        const targetMap = clean(worldPortalTargetMap && worldPortalTargetMap.value).toLowerCase();
        const targetRegionName = clean(worldPortalTargetRegion && worldPortalTargetRegion.value);
        if (!strokeId || !regionName || !["city", "training", "unlinked"].includes(targetMap)) {
          setSharedWorldStatus("Choose a portal name and target map.", "error");
          return;
        }
        if (worldPortalMenuSave) {
          worldPortalMenuSave.disabled = true;
        }
        void postSharedWorldObstacle({
          action: "set_portal",
          id: strokeId,
          region_name: regionName,
          target_map: targetMap,
          target_region_name: targetMap === "unlinked" ? "" : targetRegionName,
        }).then(() => {
          closeSharedWorldPortalMenu();
          setSharedWorldStatus(targetMap === "unlinked"
            ? `Portal ${regionName} is saved but not linked.`
            : `Portal ${regionName} links to ${targetMap}${targetRegionName ? ` / ${targetRegionName}` : " center"}.`, "ok");
        }).catch((error) => {
          setSharedWorldStatus(error && error.message ? error.message : "Could not configure portal region.", "error");
        }).finally(() => {
          if (worldPortalMenuSave) {
            worldPortalMenuSave.disabled = false;
          }
        });
        document.querySelectorAll([
          ".ft-world-training-female-ranged-impact",
          ".ft-world-training-female-ranged-spear",
          ".ft-world-training-scorpio-burn",
          ".ft-world-training-scorpio-arrow",
          ".ft-world-training-female-ultimate-impact",
          ".ft-world-training-female-ultimate-projectile",
          ".ft-world-training-male-ultimate-burn",
          ".ft-world-training-earthquake",
          ".ft-world-training-male-basic-enemy-explosion",
        ].join(",")).forEach((node) => node.remove());
      };

      // 2026-08-11: show a real map/portal chooser instead of requiring typed link syntax.
      const configureSharedWorldPortalAtEvent = async (event) => {
        if (!sharedWorldObstacleEditorAllowed() || !worldObstacleCanvas) {
          return;
        }
        if (Date.now() - sharedWorldPortalMenuOpenedAt < 350) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        const point = sharedWorldObstaclePointFromEvent(event);
        if (!point) {
          return;
        }
        const candidates = sharedWorldObstacles.strokes
          .filter((stroke) => clean(stroke.kind).toLowerCase() === "portal")
          .map((stroke) => ({ stroke, distance: sharedWorldPortalStrokeDistancePx(point, stroke) }))
          .filter((row) => row.distance <= Math.max(42, Number(row.stroke.size || 32) / 2 + 28))
          .sort((left, right) => left.distance - right.distance);
        if (!candidates.length) {
          event.preventDefault();
          setSharedWorldStatus("Right-click inside a named portal region.", "error");
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        const stroke = candidates[0].stroke;
        sharedWorldPortalMenuOpenedAt = Date.now();
        sharedWorldPortalEditingStrokeId = clean(stroke.id);
        if (worldPortalRegionName) {
          worldPortalRegionName.value = clean(stroke.regionName || "Portal");
        }
        if (worldPortalTargetMap) {
          worldPortalTargetMap.value = ["city", "training"].includes(clean(stroke.targetMap).toLowerCase())
            ? clean(stroke.targetMap).toLowerCase()
            : "unlinked";
        }
        renderSharedWorldPortalTargetRegions(clean(stroke.targetRegionName));
        if (worldPortalMenu) {
          worldPortalMenu.hidden = false;
          const menuWidth = Math.max(280, worldPortalMenu.offsetWidth || 320);
          const menuHeight = Math.max(260, worldPortalMenu.offsetHeight || 300);
          worldPortalMenu.style.left = `${Math.max(12, Math.min(window.innerWidth - menuWidth - 12, event.clientX))}px`;
          worldPortalMenu.style.top = `${Math.max(12, Math.min(window.innerHeight - menuHeight - 12, event.clientY))}px`;
        }
        if (worldPortalRegionName) {
          worldPortalRegionName.focus();
          worldPortalRegionName.select();
        }
        await Promise.all([
          postSharedWorldObstacle({ action: "get", map: "city" }).catch(() => null),
          postSharedWorldObstacle({ action: "get", map: "training" }).catch(() => null),
        ]);
        if (sharedWorldPortalEditingStrokeId === clean(stroke.id)) {
          renderSharedWorldPortalTargetRegions(clean(stroke.targetRegionName));
        }
      };

      const sharedWorldPortalTargetPoint = (portal) => {
        const targetMap = clean(portal && portal.targetMap).toLowerCase();
        const targetRegionName = clean(portal && portal.targetRegionName).toLowerCase();
        if (!targetRegionName || !["city", "training"].includes(targetMap)) {
          return { x: 0.5, y: 0.5, regionId: "" };
        }
        const targetSet = sharedWorldObstacleSets[targetMap] || { strokes: [] };
        const targetStrokes = (Array.isArray(targetSet.strokes) ? targetSet.strokes : []).filter((stroke) => (
          clean(stroke.kind).toLowerCase() === "portal"
          && clean(stroke.regionName).toLowerCase() === targetRegionName
        ));
        const points = targetStrokes.flatMap((stroke) => Array.isArray(stroke.points) ? stroke.points : []);
        if (!points.length) {
          return { x: 0.5, y: 0.5, regionId: "" };
        }
        return {
          x: sharedWorldClamp(points.reduce((sum, point) => sum + Number(point.x || 0), 0) / points.length),
          y: sharedWorldClamp(points.reduce((sum, point) => sum + Number(point.y || 0), 0) / points.length),
          regionId: clean(targetStrokes[0] && (targetStrokes[0].regionId || targetStrokes[0].id)),
        };
      };

      // Added 2026-08-12: shows the cached portal artwork before any map-switch work starts.
      const showSharedWorldMapLoading = (targetMap = "") => {
        if (!worldCard) return;
        let overlay = worldCard.querySelector("[data-world-map-loading]");
        if (!overlay) {
          overlay = document.createElement("div");
          overlay.className = "ft-world-map-loading";
          overlay.dataset.worldMapLoading = "true";
          overlay.setAttribute("aria-live", "polite");
          worldCard.appendChild(overlay);
        }
        const training = clean(targetMap).toLowerCase() === "training";
        overlay.innerHTML = `
          <span class="ft-world-map-loading-copy">
            <small>PORTAL SYNCHRONIZATION</small>
            <strong>${training ? "Entering Slime Training Field" : "Returning to QM-City"}</strong>
            <i aria-hidden="true"><b></b></i>
          </span>
        `;
        overlay.classList.add("is-visible");
        overlay.setAttribute("aria-hidden", "false");
        window.clearTimeout(overlay._worldMapLoadingSafetyTimer);
        const loadingId = `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
        overlay.dataset.worldMapLoadingId = loadingId;
        window.__ftWorldMapLoadingTrace = {
          stage: "shown",
          loadingId,
          fromMap: clean(sharedWorldMapMode || "city"),
          targetMap: clean(targetMap),
          assetCacheReady: Boolean(sharedWorldCharacterAssetState.ready),
          at: Date.now(),
        };
        console.info("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
        // 2026-08-13: a cold IndexedDB/network request must never trap the user behind the portal cover.
        overlay._worldMapLoadingSafetyTimer = window.setTimeout(() => {
          if (overlay.dataset.worldMapLoadingId !== loadingId || !overlay.classList.contains("is-visible")) return;
          window.__ftWorldMapLoadingTrace = {
            ...(window.__ftWorldMapLoadingTrace || {}),
            stage: "safety-released",
            elapsedMs: Date.now() - Number((window.__ftWorldMapLoadingTrace || {}).at || Date.now()),
            activeMap: clean(sharedWorldMapMode || "city"),
            at: Date.now(),
          };
          console.warn("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
          hideSharedWorldMapLoading("safety-timeout");
        }, 8000);
      };

      // Added 2026-08-12: releases the portal cover only after the destination has painted once.
      const hideSharedWorldMapLoading = (reason = "painted") => {
        const overlay = worldCard && worldCard.querySelector("[data-world-map-loading]");
        if (!overlay) return;
        window.clearTimeout(overlay._worldMapLoadingSafetyTimer);
        overlay._worldMapLoadingSafetyTimer = 0;
        window.requestAnimationFrame(() => {
          overlay.classList.remove("is-visible");
          overlay.setAttribute("aria-hidden", "true");
          window.__ftWorldMapLoadingTrace = {
            ...(window.__ftWorldMapLoadingTrace || {}),
            stage: "hidden",
            reason: clean(reason || "painted"),
            activeMap: clean(sharedWorldMapMode || "city"),
            at: Date.now(),
          };
          console.info("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
        });
      };

      // 2026-08-13: use cached obstacle geometry if first-load revalidation is slow.
      const refreshSharedWorldPortalTargetWithDeadline = async (targetMap = "", timeoutMs = 2600) => {
        let timeoutId = 0;
        const startedAt = performance.now();
        const timeout = new Promise((resolve) => {
          timeoutId = window.setTimeout(() => resolve({ timedOut: true }), Math.max(500, Number(timeoutMs || 2600) || 2600));
        });
        const refresh = postSharedWorldObstacle({ action: "get", map: targetMap })
          .then(() => ({ timedOut: false, ok: true }))
          .catch((error) => ({ timedOut: false, ok: false, error: clean(error && error.message) }));
        const result = await Promise.race([refresh, timeout]);
        window.clearTimeout(timeoutId);
        window.__ftWorldMapLoadingTrace = {
          ...(window.__ftWorldMapLoadingTrace || {}),
          stage: result && result.timedOut ? "obstacles-cache-fallback" : "obstacles-refreshed",
          obstacleRefreshMs: Math.round((performance.now() - startedAt) * 10) / 10,
          obstacleRefreshOk: Boolean(result && result.ok),
          targetMap: clean(targetMap),
          at: Date.now(),
        };
        console.info("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
        return result;
      };

      // 2026-08-13: warm map/combat assets before a cold portal switch without blocking forever.
      const preloadSharedWorldPortalDestinationWithDeadline = async (targetMap = "", timeoutMs = 2200) => {
        const startedAt = performance.now();
        let timeoutId = 0;
        const timeout = new Promise((resolve) => {
          timeoutId = window.setTimeout(() => resolve({ timedOut: true }), Math.max(700, Number(timeoutMs || 2200) || 2200));
        });
        const preload = Promise.resolve()
          .then(() => preloadSharedWorldCharacterAssets())
          .then(() => ({ timedOut: false, ok: true }))
          .catch((error) => ({ timedOut: false, ok: false, error: clean(error && error.message) }));
        const result = await Promise.race([preload, timeout]);
        window.clearTimeout(timeoutId);
        window.__ftWorldMapLoadingTrace = {
          ...(window.__ftWorldMapLoadingTrace || {}),
          stage: result && result.timedOut ? "asset-preload-background" : "asset-preload-ready",
          assetPreloadMs: Math.round((performance.now() - startedAt) * 10) / 10,
          assetPreloadOk: Boolean(result && result.ok),
          assetCacheReady: Boolean(sharedWorldCharacterAssetState.ready),
          targetMap: clean(targetMap),
          at: Date.now(),
        };
        console.info("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
        return result;
      };

      // 2026-08-11: named Portal Pen regions replace fixed QM-City/Training gate coordinates.
      const maybeActivateSharedWorldPortal = () => {
        const self = getSharedWorldSelfPosition();
        const portals = sharedWorldObstacles.strokes.filter((stroke) => clean(stroke.kind).toLowerCase() === "portal");
        const touched = portals
          .map((stroke) => ({ stroke, distance: sharedWorldPortalStrokeDistancePx(self, stroke) }))
          .filter((row) => row.distance <= Math.max(54, Number(row.stroke.size || 32) / 2 + 34))
          .sort((left, right) => left.distance - right.distance)[0];
        if (!touched) {
          if (Date.now() >= sharedWorldPortalCooldownUntil) {
            sharedWorldPortalLastRegionId = "";
          }
          return false;
        }
        const portal = touched.stroke;
        const regionId = clean(portal.regionId || portal.id);
        if (!portal.targetMap || Date.now() < sharedWorldPortalCooldownUntil || (regionId && regionId === sharedWorldPortalLastRegionId)) {
          return false;
        }
        const targetMap = clean(portal.targetMap).toLowerCase();
        if (!["city", "training"].includes(targetMap)) {
          return false;
        }
        sharedWorldPortalLastRegionId = regionId;
        sharedWorldPortalCooldownUntil = Date.now() + 1800;
        writeSharedWorldCheckpoint(self);
        showSharedWorldMapLoading(targetMap);
        void Promise.all([
          refreshSharedWorldPortalTargetWithDeadline(targetMap),
          preloadSharedWorldPortalDestinationWithDeadline(targetMap),
        ]).then(() => {
          const targetPoint = sharedWorldPortalTargetPoint(portal);
          sharedWorldPortalLastRegionId = targetPoint.regionId || regionId;
          sharedWorldPortalCooldownUntil = Date.now() + 1800;
          if (targetMap === "training" && sharedWorldMapMode !== "training") {
            openSharedWorldTraining({ entryPoint: targetPoint });
            return;
          }
          if (targetMap === "city" && sharedWorldMapMode === "training") {
            closeSharedWorldTraining({ placeAtTarget: true, targetPoint });
            window.requestAnimationFrame(() => {
              window.requestAnimationFrame(() => hideSharedWorldMapLoading());
            });
            return;
          }
          setSharedWorldSelfPosition(targetPoint, { center: true, smooth: false });
          hideSharedWorldMapLoading();
        }).catch((error) => {
          window.__ftWorldMapLoadingTrace = {
            ...(window.__ftWorldMapLoadingTrace || {}),
            stage: "transition-error",
            error: clean(error && error.message),
            at: Date.now(),
          };
          console.error("[FTG][WorldMapLoading]", JSON.stringify(window.__ftWorldMapLoadingTrace));
          hideSharedWorldMapLoading("transition-error");
        });
        return true;
      };

      const sharedWorldPointBlocked = (point, characterRadius = 18) => sharedWorldObstacles.strokes.some((stroke) => {
        if (clean(stroke.kind).toLowerCase() === "portal") {
          return false;
        }
        const points = Array.isArray(stroke.points) ? stroke.points : [];
        const limit = Math.max(6, Number(stroke.size) || 32) / 2 + Math.max(0, characterRadius);
        for (let index = 1; index < points.length; index += 1) {
          if (sharedWorldObstacleSegmentDistancePx(point, points[index - 1], points[index]) <= limit) {
            return true;
          }
        }
        return false;
      });

      // Added 2026-08-10: move actors out of a newly painted stroke toward the map centre.
      const sharedWorldFindEscapePoint = (point, characterRadius = 18) => {
        const origin = {
          x: sharedWorldClamp(point && point.x),
          y: sharedWorldClamp(point && point.y),
        };
        if (!sharedWorldPointBlocked(origin, characterRadius)) {
          return origin;
        }
        const { width, height } = sharedWorldObstacleMapSize();
        const centreDx = (0.5 - origin.x) * width;
        const centreDy = (0.5 - origin.y) * height;
        const centreLength = Math.hypot(centreDx, centreDy);
        const directions = [];
        if (centreLength > 0.001) {
          directions.push({ x: centreDx / centreLength, y: centreDy / centreLength });
        }
        for (let index = 0; index < 24; index += 1) {
          const angle = (Math.PI * 2 * index) / 24;
          const direction = { x: Math.cos(angle), y: Math.sin(angle) };
          if (!directions.length || Math.abs(direction.x - directions[0].x) > 0.01 || Math.abs(direction.y - directions[0].y) > 0.01) {
            directions.push(direction);
          }
        }
        for (let radiusPx = 6; radiusPx <= 720; radiusPx += 6) {
          for (const direction of directions) {
            const candidate = {
              x: sharedWorldClamp(origin.x + (direction.x * radiusPx) / width),
              y: sharedWorldClamp(origin.y + (direction.y * radiusPx) / height),
            };
            if (!sharedWorldPointBlocked(candidate, characterRadius)) {
              return candidate;
            }
          }
        }
        return origin;
      };

      const rescueSharedWorldBlockedPositions = () => {
        if (!sharedWorldPositions || !sharedWorldPathQueues) {
          return;
        }
        sharedWorldPositions.forEach((position, key) => {
          if (
            !position
            || !["city", "training"].includes(sharedWorldMapMode)
            || clean(position.mapMode || "city") !== sharedWorldMapMode
            || !sharedWorldPointBlocked(position)
          ) {
            return;
          }
          const escape = sharedWorldFindEscapePoint(position);
          const { width, height } = sharedWorldObstacleMapSize();
          if (Math.hypot((escape.x - position.x) * width, (escape.y - position.y) * height) <= 1) {
            return;
          }
          position.tx = escape.x;
          position.ty = escape.y;
          position.path = [{ x: escape.x, y: escape.y }];
          sharedWorldPathQueues.set(key, position.path.slice());
        });
      };

      const sharedWorldProjectSegment = (start, end) => {
        const from = { x: sharedWorldClamp(start.x), y: sharedWorldClamp(start.y) };
        const to = { x: sharedWorldClamp(end.x, from.x), y: sharedWorldClamp(end.y, from.y) };
        const { width, height } = sharedWorldObstacleMapSize();
        const distancePx = Math.hypot((to.x - from.x) * width, (to.y - from.y) * height);
        const steps = Math.max(1, Math.min(900, Math.ceil(distancePx / 5)));
        const startedBlocked = sharedWorldPointBlocked(from);
        let escaped = !startedBlocked;
        let lastSafe = from;
        for (let index = 1; index <= steps; index += 1) {
          const ratio = index / steps;
          const candidate = { x: from.x + (to.x - from.x) * ratio, y: from.y + (to.y - from.y) * ratio };
          const blocked = sharedWorldPointBlocked(candidate);
          if (startedBlocked && !escaped) {
            lastSafe = candidate;
            if (!blocked) {
              escaped = true;
            }
            continue;
          }
          if (blocked) {
            return lastSafe;
          }
          lastSafe = candidate;
        }
        return to;
      };

      const sharedWorldProjectOrthogonalDestination = (start, end) => {
        const from = { x: sharedWorldClamp(start.x), y: sharedWorldClamp(start.y) };
        const to = { x: sharedWorldClamp(end.x, from.x), y: sharedWorldClamp(end.y, from.y) };
        const corner = Math.abs(to.x - from.x) >= Math.abs(to.y - from.y)
          ? { x: to.x, y: from.y }
          : { x: from.x, y: to.y };
        const first = sharedWorldProjectSegment(from, corner);
        if (Math.hypot(first.x - corner.x, first.y - corner.y) > 0.0001) {
          return first;
        }
        return sharedWorldProjectSegment(corner, to);
      };

      const sharedWorldObstaclePointFromEvent = (event) => {
        if (!worldObstacleCanvas) {
          return null;
        }
        const rect = worldObstacleCanvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return null;
        }
        return {
          x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
          y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
        };
      };

      const postSharedWorldObstacle = async (payload = {}) => {
        const requestedMap = clean(payload && payload.map).toLowerCase() === "training"
          ? "training"
          : (clean(payload && payload.map).toLowerCase() === "city" ? "city" : sharedWorldMapMode);
        const response = await fetchAuthJson("/world/obstacles", { method: "POST", body: JSON.stringify({ ...payload, map: requestedMap }) });
        const result = response && response.payload ? response.payload : response;
        if (result && result.obstacles) {
          const resultMap = clean(result.map || requestedMap).toLowerCase() === "training" ? "training" : "city";
          const next = normalizeSharedWorldObstacles(result.obstacles);
          syncSharedWorldObstacles(next, resultMap);
          void writeSharedWorldObstacleCache({
            key: resultMap,
            etag: `\"qm-obstacles-${resultMap}-${next.revision}\"`,
            payload: next,
            updatedAt: Date.now(),
          });
        }
        return result;
      };

      const deleteSharedWorldObstacleAt = (point) => {
        let best = null;
        sharedWorldObstacles.strokes.forEach((stroke) => {
          const points = stroke.points || [];
          for (let index = 1; index < points.length; index += 1) {
            const distance = sharedWorldObstacleSegmentDistancePx(point, points[index - 1], points[index]);
            if (distance <= Number(stroke.size || 32) / 2 + 18 && (!best || distance < best.distance)) {
              best = { stroke, distance };
            }
          }
        });
        if (!best || sharedWorldObstacleDeleting.has(best.stroke.id)) {
          return;
        }
        sharedWorldObstacleDeleting.add(best.stroke.id);
        sharedWorldObstacles.strokes = sharedWorldObstacles.strokes.filter((stroke) => stroke.id !== best.stroke.id);
        renderSharedWorldObstacleCanvas();
        void postSharedWorldObstacle({ action: "delete", id: best.stroke.id }).catch((error) => {
          setSharedWorldStatus(error && error.message ? error.message : "Could not erase obstacle.", "error");
          void refreshSharedWorld();
        }).finally(() => sharedWorldObstacleDeleting.delete(best.stroke.id));
      };

      const beginSharedWorldObstaclePointer = (event) => {
        if (!sharedWorldObstacleEditorAllowed() || sharedWorldObstacleMode === "off" || !["city", "training"].includes(sharedWorldMapMode)) {
          return;
        }
        if (event.button === 2) {
          event.preventDefault();
          event.stopPropagation();
          void configureSharedWorldPortalAtEvent(event);
          return;
        }
        if (event.button != null && event.button !== 0) {
          return;
        }
        const point = sharedWorldObstaclePointFromEvent(event);
        if (!point) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        sharedWorldObstacleDraft = {
          id: `draft-${Date.now()}`,
          size: Math.max(8, Math.min(160, Number(worldPenSize && worldPenSize.value) || 36)),
          points: [point],
          pointerId: event.pointerId,
          kind: sharedWorldObstacleMode === "portal" ? "portal" : "obstacle",
        };
        try {
          worldObstacleCanvas.setPointerCapture(event.pointerId);
        } catch (_error) {
        }
      };

      const moveSharedWorldObstaclePointer = (event) => {
        const point = sharedWorldObstaclePointFromEvent(event);
        if (!sharedWorldObstacleDraft || sharedWorldObstacleDraft.pointerId !== event.pointerId || !point) {
          return;
        }
        const previous = sharedWorldObstacleDraft.points[sharedWorldObstacleDraft.points.length - 1];
        const { width, height } = sharedWorldObstacleMapSize();
        if (Math.hypot((point.x - previous.x) * width, (point.y - previous.y) * height) < 4) {
          return;
        }
        event.preventDefault();
        sharedWorldObstacleDraft.points.push(point);
        renderSharedWorldObstacleCanvas();
      };

      const endSharedWorldObstaclePointer = (event) => {
        const draft = sharedWorldObstacleDraft;
        if (!draft || draft.pointerId !== event.pointerId) {
          return;
        }
        event.preventDefault();
        sharedWorldObstacleDraft = null;
        if (draft.points.length < 2) {
          renderSharedWorldObstacleCanvas();
          return;
        }
        const optimistic = { id: draft.id, size: draft.size, points: draft.points, kind: draft.kind || "obstacle" };
        if (sharedWorldObstacleMode === "erase") {
          renderSharedWorldObstacleCanvas();
          void postSharedWorldObstacle({ action: "erase", stroke: optimistic }).catch((error) => {
            renderSharedWorldObstacleCanvas();
            setSharedWorldStatus(error && error.message ? error.message : "Could not erase obstacle area.", "error");
          });
          return;
        }
        if (sharedWorldObstacleMode === "portal") {
          const portalCount = sharedWorldObstacles.strokes.filter((stroke) => clean(stroke.kind).toLowerCase() === "portal").length;
          const regionName = `Portal ${portalCount + 1}`;
          optimistic.regionId = draft.id;
          optimistic.regionName = regionName;
          optimistic.targetMap = "";
          sharedWorldObstacles.strokes.push(optimistic);
          renderSharedWorldObstacleCanvas();
          void postSharedWorldObstacle({ action: "add_portal", region_name: regionName, stroke: optimistic }).then(() => {
            setSharedWorldStatus(`${regionName} saved. Right-click the painted region to choose its target.`, "ok");
          }).catch((error) => {
              sharedWorldObstacles.strokes = sharedWorldObstacles.strokes.filter((stroke) => stroke.id !== optimistic.id);
              renderSharedWorldObstacleCanvas();
              setSharedWorldStatus(error && error.message ? error.message : "Could not save portal region.", "error");
            });
          return;
        }
        sharedWorldObstacles.strokes.push(optimistic);
        renderSharedWorldObstacleCanvas();
        void postSharedWorldObstacle({ action: "add", stroke: optimistic }).catch((error) => {
          sharedWorldObstacles.strokes = sharedWorldObstacles.strokes.filter((stroke) => stroke.id !== optimistic.id);
          renderSharedWorldObstacleCanvas();
          setSharedWorldStatus(error && error.message ? error.message : "Could not save obstacle.", "error");
        });
      };

      const setSharedWorldObstacleMode = (mode = "off") => {
        const next = sharedWorldObstacleEditorAllowed() && ["draw", "portal", "erase"].includes(mode) ? mode : "off";
        sharedWorldObstacleMode = sharedWorldObstacleMode === next ? "off" : next;
        sharedWorldObstacleDraft = null;
        closeSharedWorldPortalMenu();
        if (sharedWorldObstacleMode !== "off" && sharedWorldFollowFrame) {
          window.cancelAnimationFrame(sharedWorldFollowFrame);
          sharedWorldFollowFrame = 0;
        }
        renderSharedWorldObstacleEditor();
      };

      const selectSharedWorldPositionPoint = (point) => {
        if (!point) {
          return;
        }
        sharedWorldSelectedPoint = {
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        };
        renderSharedWorldPositionPoint();
        setSharedWorldPickingPosition(false);
        setSharedWorldStatus(`Point selected: ${Math.round(sharedWorldSelectedPoint.x * 100)} / ${Math.round(sharedWorldSelectedPoint.y * 100)}.`, "ok");
      };

      const sharedWorldMapPointerBlocked = (target) => Boolean(
        target
        && target.closest
        && target.closest([
          "button",
          "input",
          "textarea",
          "select",
          "[contenteditable='true']",
          ".ft-world-player",
          ".ft-world-npc",
          ".ft-world-witch",
          "[data-slime-id]",
          "#ft-world-training-modal",
          "#ft-world-command-lane",
          ".ft-world-command-lane",
          ".ft-world-dock",
          ".ft-world-close-menu",
          ".ft-world-status",
          ".ft-world-skin-shop",
          ".ft-world-inventory-modal",
        ].join(","))
      );

      const moveSharedWorldToMapPoint = (point = {}) => {
        if (!point) {
          return;
        }
        clearSharedWorldTargetSelection();
        clearSharedWorldFollowTarget();
        const destination = { x: sharedWorldClamp(point.x), y: sharedWorldClamp(point.y) };
        showSharedWorldMoveMarker(destination);
        void moveSharedWorldPlayer(destination);
      };

      const handleSharedWorldObstacleArrowPan = (event) => {
        if (!worldStage || !worldModal || !worldModal.classList.contains("is-open") || sharedWorldObstacleMode === "off" || !["city", "training"].includes(sharedWorldMapMode)) {
          return;
        }
        const target = event.target;
        if (target && target.closest && target.closest("input, textarea, select, [contenteditable='true']")) {
          return;
        }
        const stepX = Math.max(120, Math.round(worldStage.clientWidth * 0.14));
        const stepY = Math.max(90, Math.round(worldStage.clientHeight * 0.14));
        const moves = {
          ArrowLeft: [-stepX, 0],
          ArrowRight: [stepX, 0],
          ArrowUp: [0, -stepY],
          ArrowDown: [0, stepY],
        };
        const move = moves[event.key];
        if (!move) {
          return;
        }
        event.preventDefault();
        worldStage.scrollLeft += move[0];
        worldStage.scrollTop += move[1];
      };

      const beginSharedWorldStagePan = (event) => {
        if (!worldStage || !worldModal || !worldModal.classList.contains("is-open") || sharedWorldPickingPosition || sharedWorldObstacleMode !== "off") {
          return;
        }
        if (event.button != null && event.button !== 0) {
          return;
        }
        if (sharedWorldMapPointerBlocked(event.target)) {
          return;
        }
        sharedWorldStageDrag = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          scrollLeft: worldStage.scrollLeft,
          scrollTop: worldStage.scrollTop,
          nextScrollLeft: worldStage.scrollLeft,
          nextScrollTop: worldStage.scrollTop,
          eventCount: 0,
          frameCount: 0,
          startedAt: performance.now(),
          lastFrameAt: 0,
          maxFrameGap: 0,
          moved: false,
        };
        try {
          if (typeof worldStage.setPointerCapture === "function" && event.pointerId != null) {
            worldStage.setPointerCapture(event.pointerId);
          }
        } catch (error) {}
      };

      // Added 2026-08-09: coalesce QM-City screen pan updates to one DOM scroll write per animation frame.
      const flushSharedWorldStagePan = (now = performance.now()) => {
        sharedWorldStagePanFrame = 0;
        if (!worldStage || !sharedWorldStageDrag) {
          return;
        }
        const drag = sharedWorldStageDrag;
        if (drag.lastFrameAt) {
          drag.maxFrameGap = Math.max(drag.maxFrameGap || 0, now - drag.lastFrameAt);
        }
        drag.lastFrameAt = now;
        drag.frameCount = (drag.frameCount || 0) + 1;
        worldStage.scrollLeft = drag.nextScrollLeft;
        worldStage.scrollTop = drag.nextScrollTop;
      };

      const scheduleSharedWorldStagePanFlush = () => {
        if (sharedWorldStagePanFrame || !worldStage || !sharedWorldStageDrag) {
          return;
        }
        sharedWorldStagePanFrame = window.requestAnimationFrame(flushSharedWorldStagePan);
      };

      const cancelSharedWorldStagePanFrame = () => {
        if (sharedWorldStagePanFrame) {
          window.cancelAnimationFrame(sharedWorldStagePanFrame);
          sharedWorldStagePanFrame = 0;
        }
      };

      const updateSharedWorldStagePan = (event) => {
        if (!worldStage || !sharedWorldStageDrag || (event.pointerId != null && sharedWorldStageDrag.pointerId !== event.pointerId)) {
          return;
        }
        const dx = event.clientX - sharedWorldStageDrag.startX;
        const dy = event.clientY - sharedWorldStageDrag.startY;
        if (!sharedWorldStageDrag.moved && Math.hypot(dx, dy) < 5) {
          return;
        }
        sharedWorldStageDrag.moved = true;
        sharedWorldStageDrag.eventCount = (sharedWorldStageDrag.eventCount || 0) + 1;
        sharedWorldStageDrag.nextScrollLeft = sharedWorldStageDrag.scrollLeft - dx;
        sharedWorldStageDrag.nextScrollTop = sharedWorldStageDrag.scrollTop - dy;
        worldStage.classList.add("is-panning");
        scheduleSharedWorldStagePanFlush();
        event.preventDefault();
      };

      const endSharedWorldStagePan = (event) => {
        if (!worldStage || !sharedWorldStageDrag || (event.pointerId != null && sharedWorldStageDrag.pointerId !== event.pointerId)) {
          return;
        }
        const didMove = Boolean(sharedWorldStageDrag.moved);
        if (didMove) {
          cancelSharedWorldStagePanFrame();
          flushSharedWorldStagePan();
          const drag = sharedWorldStageDrag;
          window.__ftQmCityMovePerfTrace = {
            stage: "pan-end",
            events: Math.max(0, Number(drag.eventCount || 0)),
            frames: Math.max(0, Number(drag.frameCount || 0)),
            coalesced: Math.max(0, Number(drag.eventCount || 0) - Number(drag.frameCount || 0)),
            durationMs: Math.round(performance.now() - Number(drag.startedAt || performance.now())),
            maxFrameGapMs: Math.round(Number(drag.maxFrameGap || 0)),
          };
          if (window.console && typeof window.console.debug === "function") {
            window.console.debug("[FTG][QMCityMovePerf]", window.__ftQmCityMovePerfTrace);
          }
        }
        try {
          if (typeof worldStage.releasePointerCapture === "function" && event.pointerId != null) {
            worldStage.releasePointerCapture(event.pointerId);
          }
        } catch (error) {}
        worldStage.classList.remove("is-panning");
        sharedWorldStageDrag = null;
        if (didMove) {
          sharedWorldSuppressNextMapClick = true;
          window.setTimeout(() => {
            sharedWorldSuppressNextMapClick = false;
          }, 120);
        }
      };

      const handleSharedWorldStageClick = (event) => {
        if (!worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        if (sharedWorldObstacleMode !== "off") {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        if (sharedWorldSuppressNextMapClick) {
          event.preventDefault();
          event.stopPropagation();
          sharedWorldSuppressNextMapClick = false;
          return;
        }
        if (sharedWorldMapPointerBlocked(event.target)) {
          return;
        }
        const point = sharedWorldPointFromArenaEvent(event);
        if (!point) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (sharedWorldPickingPosition) {
          selectSharedWorldPositionPoint(point);
          return;
        }
        if (sharedWorldMapMode === "training") {
          setSharedWorldTrainingQuestionOpen(false);
        }
        moveSharedWorldToMapPoint(point);
      };

      const insertSharedWorldPositionIntoCommand = () => {
        if (!sharedWorldSelectedPoint || !worldCommandInput) {
          return;
        }
        const x = Math.round(sharedWorldSelectedPoint.x * 100);
        const y = Math.round(sharedWorldSelectedPoint.y * 100);
        const value = clean(worldCommandInput.value);
        if (!value || /^move\s+to\b/i.test(value)) {
          worldCommandInput.value = `move to ${x} ${y}`;
        } else {
          worldCommandInput.value = `${value} ${x} ${y}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const resolveSharedWorldTarget = (name = "") => {
        const query = sharedWorldNameKey(name);
        if (!query) {
          return null;
        }
        const rows = Array.from(sharedWorldRoster.values());
        return rows.find((item) => sharedWorldNameKey(item.username) === query || sharedWorldNameKey(sharedWorldTargetLabel(item)) === query)
          || rows.find((item) => sharedWorldNameKey(sharedWorldTargetLabel(item)).includes(query) || sharedWorldNameKey(item.username).includes(query))
          || null;
      };

      const sharedWorldNearTargetPoint = (target) => {
        if (!target) {
          return null;
        }
        const targetX = sharedWorldClamp(target.tx != null ? target.tx : target.x);
        const targetY = sharedWorldClamp(target.ty != null ? target.ty : target.y);
        const self = getSharedWorldSelfPosition();
        let dx = sharedWorldClamp(self.x) - targetX;
        let dy = sharedWorldClamp(self.y) - targetY;
        let distance = Math.hypot(dx, dy);
        if (distance < 0.02) {
          let seed = 0;
          clean(target.username || target.displayName || "").split("").forEach((char) => {
            seed += char.charCodeAt(0);
          });
          const angle = ((seed % 360) / 180) * Math.PI;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }
        const gap = 0.18;
        return {
          x: sharedWorldClamp(targetX + (dx / distance) * gap),
          y: sharedWorldClamp(targetY + (dy / distance) * gap),
        };
      };

      const clearSharedWorldFollowTarget = () => {
        sharedWorldFollowTargetKey = "";
        sharedWorldFollowMoveAt = 0;
      };

      const updateSharedWorldFollowTarget = () => {
        if (sharedWorldRuntimeDeferredForGate || !sharedWorldFollowTargetKey || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const target = sharedWorldRoster.get(sharedWorldFollowTargetKey);
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!target || clean(target.username).toLowerCase() === me) {
          clearSharedWorldFollowTarget();
          return;
        }
        const now = Date.now();
        if (now - sharedWorldFollowMoveAt < 900) {
          return;
        }
        const point = sharedWorldNearTargetPoint(target);
        if (!point) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        if (Math.hypot(sharedWorldClamp(self.tx, self.x) - point.x, sharedWorldClamp(self.ty, self.y) - point.y) < 0.018) {
          return;
        }
        sharedWorldFollowMoveAt = now;
        void moveSharedWorldPlayer(point);
      };

      const createSharedWorldNode = (username = "") => {
        const node = document.createElement("div");
        node.className = "ft-world-player is-facing-down";
        node.dataset.facing = "down";
        node.dataset.username = username;
        node.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const target = selectSharedWorldTarget(node.dataset.username || "");
          if (target) {
            primeSharedWorldPlayerCommand(target);
          }
        });
        node.innerHTML = `
          <span class="ft-world-target-arrow" aria-hidden="true"></span>
          <div class="ft-world-rank-badge" hidden></div>
          <div class="ft-world-playing-badge" aria-hidden="true">Playing</div>
          <div class="ft-world-top-tooltip" hidden></div>
          <div class="ft-world-bubble"></div>
          <div class="ft-world-level" aria-hidden="true">
            <span class="ft-world-level-badge">Lv 1</span>
            <span class="ft-world-exp-bar"><span></span></span>
            <span class="ft-world-exp-text">0/25</span>
          </div>
          <div class="ft-world-character-stage" aria-hidden="true">
            <span class="ft-world-character-shadow"></span>
            <div class="ft-world-fireball ft-world-character">
              <span class="ft-world-eye is-left"></span>
              <span class="ft-world-eye is-right"></span>
              <span class="ft-world-cheek is-left"></span>
              <span class="ft-world-cheek is-right"></span>
              <span class="ft-world-smile"></span>
            </div>
          </div>
          <div class="ft-world-name-row">
            <div class="ft-world-name"></div>
            <span class="ft-world-gender" title="other">◇</span>
          </div>
        `;
        ensureSharedWorldTargetBattleAction(node);
        const character = node.querySelector(".ft-world-character");
        if (character) {
          // Added 2026-08-10: choose female run frame 5 or 6 on each completed loop.
          character.addEventListener("animationiteration", (event) => {
            if (!node.classList.contains("is-character-female-default") || !node.classList.contains("is-moving")) {
              return;
            }
            if (event.animationName === "ftWorldCharacterFemaleRunEffectFive" || event.animationName === "ftWorldCharacterFemaleRunEffectSix") {
              node.classList.toggle("is-female-run-effect-six", Math.random() >= 0.5);
            }
          });
        }
        return node;
      };

      const renderSharedWorldName = (node, displayName = "", gender = "") => {
        const nameNode = node && node.querySelector ? node.querySelector(".ft-world-name") : null;
        if (!nameNode) {
          return;
        }
        const genderNode = node.querySelector(".ft-world-gender");
        if (!genderNode) {
          return;
        }
        const rawGenderKey = clean(gender).toLowerCase();
        const selfKey = (clean(activeWorldUsername() || currentAuthUsername || "") || "").toLowerCase();
        const nodeKey = clean(node.dataset.username || "").toLowerCase();
        const genderKey = sharedWorldAdminCharacterPreview && sharedWorldObstacleEditorAllowed() && nodeKey === selfKey
          ? sharedWorldAdminCharacterPreview
          : rawGenderKey;
        const characterKind = normalizeSharedWorldCharacterKind(genderKey);
        const labelText = clean(displayName) || "Learner";
        const signature = `${labelText}\u0000${genderKey}\u0000${characterKind}`;
        if (node.dataset.nameCharacterSignature === signature) return;
        node.dataset.nameCharacterSignature = signature;
        nameNode.innerHTML = "";
        const label = document.createElement("span");
        label.className = "ft-world-name-label";
        label.textContent = labelText;
        nameNode.append(label);
        const femaleDefault = characterKind === "female";
        const scorpio = characterKind === "scorpio";
        node.classList.toggle("is-character-female-default", femaleDefault);
        node.classList.toggle("is-character-male-default", characterKind === "male");
        node.classList.toggle("is-character-scorpio", scorpio);
        node.dataset.characterId = scorpio ? "character_scorpio" : (femaleDefault ? "character_female_default" : "character_male_default");
        if (femaleDefault && !node.dataset.femaleRunVariant) {
          node.dataset.femaleRunVariant = Math.random() >= 0.5 ? "six" : "five";
          node.classList.toggle("is-female-run-effect-six", node.dataset.femaleRunVariant === "six");
        } else if (!femaleDefault) {
          node.classList.remove("is-female-run-effect-five", "is-female-run-effect-six");
          delete node.dataset.femaleRunVariant;
        }
        genderNode.className = `ft-world-gender ${genderKey === "female" || scorpio ? "is-female" : genderKey === "other" ? "is-other" : ""}`;
        genderNode.textContent = scorpio ? "♏" : sharedWorldGenderSymbol(genderKey);
        genderNode.title = scorpio ? "Cung Bọ Cạp" : (genderKey || "other");
      };

      const renderSharedWorldLevel = (node, level = {}) => {
        if (!node || !node.querySelector) {
          return;
        }
        const data = level && typeof level === "object" ? level : {};
        const badge = node.querySelector(".ft-world-level-badge");
        const bar = node.querySelector(".ft-world-exp-bar");
        const text = node.querySelector(".ft-world-exp-text");
        const currentLevel = Math.max(1, Math.floor(Number(data.level || 1) || 1));
        const exp = Math.max(0, Math.floor(Number(data.exp || 0) || 0));
        const currentExp = Math.max(0, Math.floor(Number(data.current_exp || data.currentExp || 0) || 0));
        const nextExp = Math.max(currentExp, Math.floor(Number(data.next_exp || data.nextExp || currentExp) || currentExp));
        const maxLevel = Boolean(data.max_level || data.maxLevel);
        let progress = Number(data.progress);
        if (!Number.isFinite(progress)) {
          progress = maxLevel ? 1 : ((nextExp > currentExp) ? (exp - currentExp) / (nextExp - currentExp) : 0);
        }
        progress = Math.max(0, Math.min(1, progress));
        const signature = `${currentLevel}:${exp}:${currentExp}:${nextExp}:${maxLevel ? 1 : 0}:${progress.toFixed(4)}`;
        if (node.dataset.levelSignature === signature) return;
        node.dataset.levelSignature = signature;
        if (badge) {
          badge.textContent = `Lv ${currentLevel}`;
        }
        if (bar) {
          bar.style.setProperty("--level-progress", `${(progress * 100).toFixed(1)}%`);
        }
        if (text) {
          text.textContent = maxLevel ? `${exp} MAX` : `${exp}/${nextExp}`;
        }
      };

      const renderSharedWorldTopMeta = (node, player = {}) => {
        if (!node || !node.querySelector) {
          return;
        }
        const badge = node.querySelector(".ft-world-rank-badge");
        const tooltip = node.querySelector(".ft-world-top-tooltip");
        const monthlyBadge = player && typeof player.monthly_badge === "object" ? player.monthly_badge : {};
        const titleRows = Array.isArray(player.top_titles) ? player.top_titles : [];
        const signature = JSON.stringify({ monthlyBadge, titleRows });
        if (node.dataset.topMetaSignature === signature) return;
        node.dataset.topMetaSignature = signature;
        if (badge) {
          const scopeRank = { month: 3, week: 2, day: 1 };
          const champions = titleRows
            .filter((item) => item && Math.floor(Number(item.rank || 0) || 0) === 1 && scopeRank[clean(item.scope).toLowerCase()])
            .sort((x, y) => (scopeRank[clean(y.scope).toLowerCase()] || 0) - (scopeRank[clean(x.scope).toLowerCase()] || 0));
          let best = champions[0] || null;
          let scope = best ? clean(best.scope).toLowerCase() : "";
          let label = best ? clean(best.label || best.title || "") : "";
          let period = "";
          if (!best) {
            label = clean(monthlyBadge.label || monthlyBadge.title || "");
            scope = label ? clean(monthlyBadge.scope || "month").toLowerCase() : "";
            period = clean(monthlyBadge.period_key || "");
          }
          badge.classList.remove("is-day", "is-week", "is-month");
          if (label) {
            if (scope === "day" || scope === "week" || scope === "month") {
              badge.classList.add(`is-${scope}`);
            }
            badge.hidden = false;
            badge.title = best ? `${label} - ${Math.max(0, Math.floor(Number(best.score || 0) || 0))} words` : period;
            badge.innerHTML = `
              <span class="ft-world-rank-crown" aria-hidden="true">
                <svg viewBox="0 0 24 20" focusable="false">
                  <path fill="currentColor" d="M2.6 6.2 6 11 12 3.2 18 11l3.4-4.8c.7-1 2.2-.4 2 .8l-1.7 9.3c-.1.7-.7 1.2-1.4 1.2H4.7c-.7 0-1.3-.5-1.4-1.2L1.6 7c-.2-1.2 1.3-1.8 2-.8Z"/>
                  <circle cx="2.7" cy="5" r="1.5" fill="currentColor"/>
                  <circle cx="12" cy="2.4" r="1.7" fill="currentColor"/>
                  <circle cx="21.3" cy="5" r="1.5" fill="currentColor"/>
                </svg>
              </span>
              <span class="ft-world-rank-label"></span>
            `;
            const labelNode = badge.querySelector(".ft-world-rank-label");
            if (labelNode) {
              labelNode.textContent = label;
            }
          } else {
            badge.hidden = true;
            badge.title = "";
            badge.innerHTML = "";
          }
        }
        if (!tooltip) {
          return;
        }
        const rows = Array.isArray(player.top_titles) ? player.top_titles : [];
        tooltip.innerHTML = "";
        if (!rows.length) {
          tooltip.hidden = true;
          return;
        }
        tooltip.hidden = false;
        rows.slice(0, 3).forEach((item) => {
          const line = document.createElement("div");
          line.className = "ft-world-top-line";
          const title = document.createElement("span");
          title.textContent = clean(item.label || item.title || item.scope || "Top");
          const score = document.createElement("b");
          score.textContent = `${Math.max(0, Math.floor(Number(item.score || 0) || 0))}`;
          line.append(title, score);
          tooltip.appendChild(line);
        });
      };

      let sharedWorldCharacterDepthFrame = 0;

      // Added 2026-08-16: City and Training share one ground-Y order across players, NPCs, and enemies.
      const refreshSharedWorldCharacterDepthOrder = () => {
        sharedWorldCharacterDepthFrame = 0;
        if (!worldArena) return;
        const actors = Array.from(worldArena.querySelectorAll(".ft-world-player, .ft-world-npc, .ft-world-training-slime"))
          .filter((node) => node.isConnected && !node.closest(".ft-world-training-effects"));
        const depthFor = (node) => {
          const explicit = Number(node.dataset.worldDepthY);
          if (Number.isFinite(explicit)) return explicit;
          const cssY = Number.parseFloat(getComputedStyle(node).getPropertyValue("--world-y"));
          return Number.isFinite(cssY) ? cssY / 100 : 0;
        };
        actors.sort((left, right) => {
          const yDelta = depthFor(left) - depthFor(right);
          if (Math.abs(yDelta) > 0.000001) return yDelta;
          return clean(left.dataset.username || left.dataset.slimeId || left.id).localeCompare(clean(right.dataset.username || right.dataset.slimeId || right.id));
        });
        actors.forEach((node, index) => {
          const rank = String(100 + index);
          if (node.dataset.worldDepthRank === rank) return;
          node.dataset.worldDepthRank = rank;
          node.style.zIndex = rank;
        });
      };

      const scheduleSharedWorldCharacterDepthOrder = () => {
        if (sharedWorldCharacterDepthFrame) return;
        sharedWorldCharacterDepthFrame = window.requestAnimationFrame(refreshSharedWorldCharacterDepthOrder);
      };

      const applySharedWorldNodePosition = (node, x, y) => {
        if (!node) {
          return;
        }
        const groundedX = sharedWorldClamp(x);
        const groundedY = sharedWorldClamp(y);
        node.style.setProperty("--world-x", `${(groundedX * 100).toFixed(2)}%`);
        node.style.setProperty("--world-y", `${(groundedY * 100).toFixed(2)}%`);
        node.dataset.worldDepthY = groundedY.toFixed(5);
        scheduleSharedWorldCharacterDepthOrder();
      };

      const sharedWorldHasPath = (key = "") => {
        const safeKey = clean(key).toLowerCase();
        const queue = sharedWorldPathQueues.get(safeKey);
        return Array.isArray(queue) && queue.length > 0;
      };

      const clearSharedWorldPath = (key = "") => {
        const safeKey = clean(key).toLowerCase();
        if (!safeKey) {
          return;
        }
        sharedWorldPathQueues.delete(safeKey);
        const pos = sharedWorldPositions.get(safeKey);
        if (pos && Array.isArray(pos.path)) {
          pos.path = [];
        }
      };

      const sharedWorldMakeOrthogonalPath = (start = {}, target = {}) => {
        const { width: obstacleWidth, height: obstacleHeight } = sharedWorldObstacleMapSize();
        const startPoint = { x: sharedWorldClamp(start.x), y: sharedWorldClamp(start.y) };
        const requestedTarget = { x: sharedWorldClamp(target.x), y: sharedWorldClamp(target.y) };
        const escapeStart = sharedWorldPointBlocked(startPoint) ? sharedWorldFindEscapePoint(startPoint) : startPoint;
        const goal = sharedWorldPointBlocked(requestedTarget) ? sharedWorldFindEscapePoint(requestedTarget) : requestedTarget;
        const axisPath = (from, to) => {
          const points = [];
          if (Math.abs(to.x - from.x) >= Math.abs(to.y - from.y)) {
            if (Math.abs(to.x - from.x) > 0.002) points.push({ x: to.x, y: from.y });
            if (Math.abs(to.y - from.y) > 0.002) points.push({ x: to.x, y: to.y });
          } else {
            if (Math.abs(to.y - from.y) > 0.002) points.push({ x: from.x, y: to.y });
            if (Math.abs(to.x - from.x) > 0.002) points.push({ x: to.x, y: to.y });
          }
          return points;
        };
        const prefix = axisPath(startPoint, escapeStart);
        const segmentClear = (from, to) => {
          const distancePx = Math.hypot((to.x - from.x) * obstacleWidth, (to.y - from.y) * obstacleHeight);
          const steps = Math.max(1, Math.min(240, Math.ceil(distancePx / 8)));
          for (let index = 1; index <= steps; index += 1) {
            const ratio = index / steps;
            if (sharedWorldPointBlocked({ x: from.x + (to.x - from.x) * ratio, y: from.y + (to.y - from.y) * ratio })) {
              return false;
            }
          }
          return true;
        };
        const directAxis = axisPath(escapeStart, goal);
        if (directAxis.length && directAxis.every((point, index) => segmentClear(index ? directAxis[index - 1] : escapeStart, point))) {
          return prefix.concat(directAxis);
        }
        const minX = 0.04;
        const minY = 0.04;
        const maxX = 0.96;
        const maxY = 0.96;
        const columns = 96;
        const rows = 30;
        const toPoint = (column, row) => ({
          x: minX + (column / (columns - 1)) * (maxX - minX),
          y: minY + (row / (rows - 1)) * (maxY - minY),
        });
        const toCell = (point) => ({
          column: Math.max(0, Math.min(columns - 1, Math.round(((point.x - minX) / (maxX - minX)) * (columns - 1)))),
          row: Math.max(0, Math.min(rows - 1, Math.round(((point.y - minY) / (maxY - minY)) * (rows - 1)))),
        });
        const nearestFreeCell = (point) => {
          const base = toCell(point);
          for (let radius = 0; radius < Math.max(columns, rows); radius += 1) {
            for (let row = base.row - radius; row <= base.row + radius; row += 1) {
              for (let column = base.column - radius; column <= base.column + radius; column += 1) {
                if (column < 0 || row < 0 || column >= columns || row >= rows) continue;
                const candidate = toPoint(column, row);
                if (!sharedWorldPointBlocked(candidate) && segmentClear(point, candidate)) return { column, row };
              }
            }
          }
          return base;
        };
        const startCell = nearestFreeCell(escapeStart);
        const goalCell = nearestFreeCell(goal);
        const cellId = (column, row) => row * columns + column;
        const startId = cellId(startCell.column, startCell.row);
        const goalId = cellId(goalCell.column, goalCell.row);
        const open = [{ column: startCell.column, row: startCell.row, id: startId, f: 0, g: 0 }];
        const cameFrom = new Map();
        const cost = new Map([[startId, 0]]);
        const heuristic = (column, row) => Math.hypot((column - goalCell.column) * obstacleWidth / columns, (row - goalCell.row) * obstacleHeight / rows);
        const neighbours = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        let found = false;
        while (open.length && cameFrom.size < 12000) {
          open.sort((a, b) => a.f - b.f);
          const current = open.shift();
          if (current.id === goalId) { found = true; break; }
          for (const [deltaColumn, deltaRow] of neighbours) {
            const column = current.column + deltaColumn;
            const row = current.row + deltaRow;
            if (column < 0 || row < 0 || column >= columns || row >= rows) continue;
            const next = toPoint(column, row);
            const currentPoint = toPoint(current.column, current.row);
            if (sharedWorldPointBlocked(next) || !segmentClear(currentPoint, next)) continue;
            const id = cellId(column, row);
            const nextCost = current.g + Math.hypot(deltaColumn * obstacleWidth / columns, deltaRow * obstacleHeight / rows);
            if (nextCost >= (cost.get(id) ?? Infinity)) continue;
            cost.set(id, nextCost);
            cameFrom.set(id, current.id);
            open.push({ column, row, id, g: nextCost, f: nextCost + heuristic(column, row) });
          }
        }
        if (!found) {
          return prefix.concat([goal]);
        }
        const cells = [goalId];
        while (cells[0] !== startId) {
          const parent = cameFrom.get(cells[0]);
          if (parent == null) break;
          cells.unshift(parent);
        }
        const rawPath = cells.slice(1).map((id) => toPoint(id % columns, Math.floor(id / columns)));
        const orthogonal = [];
        let previous = escapeStart;
        let previousDirection = null;
        rawPath.forEach((point) => {
          const direction = {
            x: Math.sign(point.x - previous.x),
            y: Math.sign(point.y - previous.y),
          };
          if (previousDirection && (direction.x !== previousDirection.x || direction.y !== previousDirection.y)) {
            orthogonal.push(previous);
          }
          previousDirection = direction;
          previous = point;
        });
        if (rawPath.length) {
          orthogonal.push(rawPath[rawPath.length - 1]);
        }
        const tail = axisPath(orthogonal.length ? orthogonal[orthogonal.length - 1] : escapeStart, goal);
        return prefix.concat(orthogonal, tail);
      };

      const setSharedWorldOrthogonalPath = (key = "", target = {}) => {
        const safeKey = clean(key).toLowerCase();
        if (!safeKey || !target) {
          return null;
        }
        let pos = sharedWorldPositions.get(safeKey);
        if (!pos) {
          pos = { x: target.x, y: target.y, tx: target.x, ty: target.y };
          sharedWorldPositions.set(safeKey, pos);
        }
        const requestedDestination = {
          x: sharedWorldClamp(target.x),
          y: sharedWorldClamp(target.y),
        };
        const destination = sharedWorldPointBlocked(requestedDestination)
          ? sharedWorldFindEscapePoint(requestedDestination)
          : requestedDestination;
        const path = sharedWorldMakeOrthogonalPath({ x: pos.x, y: pos.y }, destination);
        pos.tx = destination.x;
        pos.ty = destination.y;
        pos.goalX = destination.x;
        pos.goalY = destination.y;
        pos.blockedSince = 0;
        pos.path = path.slice();
        if (path.length) {
          sharedWorldPathQueues.set(safeKey, path);
        } else {
          sharedWorldPathQueues.delete(safeKey);
        }
        return pos;
      };

      const sharedWorldMotionTargetFor = (key = "", pos = {}) => {
        const safeKey = clean(key).toLowerCase();
        const queue = Array.isArray(pos.path) && pos.path.length
          ? pos.path
          : sharedWorldPathQueues.get(safeKey);
        if (Array.isArray(queue) && queue.length) {
          return queue[0];
        }
        return {
          x: sharedWorldClamp(pos.tx, pos.x),
          y: sharedWorldClamp(pos.ty, pos.y),
        };
      };

      const advanceSharedWorldPathIfReached = (key = "", pos = {}) => {
        const safeKey = clean(key).toLowerCase();
        const queue = Array.isArray(pos.path) && pos.path.length
          ? pos.path
          : sharedWorldPathQueues.get(safeKey);
        if (!Array.isArray(queue) || !queue.length) {
          return false;
        }
        queue.shift();
        if (queue.length) {
          pos.path = queue;
          sharedWorldPathQueues.set(safeKey, queue);
          return true;
        }
        pos.path = [];
        sharedWorldPathQueues.delete(safeKey);
        pos.x = sharedWorldClamp(pos.tx, pos.x);
        pos.y = sharedWorldClamp(pos.ty, pos.y);
        return false;
      };

      const syncSharedWorldBattleLinks = () => {
        if (!worldBattleLinks || !worldArena) {
          return;
        }
        const pairs = Array.isArray(sharedWorldActiveBattlePairs) ? sharedWorldActiveBattlePairs : [];
        const activeKeys = new Set();
        pairs.forEach((pair) => {
          const row = pair && typeof pair === "object" ? pair : {};
          const players = Array.isArray(row.players)
            ? row.players.map((item) => clean(item).toLowerCase()).filter(Boolean)
            : [];
          if (players.length < 2) {
            return;
          }
          const first = players[0];
          const second = players[1];
          const posA = sharedWorldPositions.get(first);
          const posB = sharedWorldPositions.get(second);
          if (!posA || !posB) {
            return;
          }
          const key = clean(row.id) || players.slice(0, 2).sort().join(":");
          activeKeys.add(key);
          let link = sharedWorldBattleLinkNodes.get(key);
          if (!link) {
            link = document.createElement("div");
            link.className = "ft-world-battle-link";
            const label = document.createElement("b");
            label.textContent = "Playing";
            link.appendChild(label);
            sharedWorldBattleLinkNodes.set(key, link);
            worldBattleLinks.appendChild(link);
          }
          const x1 = sharedWorldClamp(posA.x) * worldArena.scrollWidth;
          const y1 = sharedWorldClamp(posA.y) * worldArena.scrollHeight;
          const x2 = sharedWorldClamp(posB.x) * worldArena.scrollWidth;
          const y2 = sharedWorldClamp(posB.y) * worldArena.scrollHeight;
          const dx = x2 - x1;
          const dy = y2 - y1;
          const length = Math.max(18, Math.hypot(dx, dy));
          const angle = Math.atan2(dy, dx) * 180 / Math.PI;
          link.style.left = `${x1}px`;
          link.style.top = `${y1}px`;
          link.style.width = `${length}px`;
          link.style.transform = `translateY(-50%) rotate(${angle}deg)`;
        });
        Array.from(sharedWorldBattleLinkNodes.entries()).forEach(([key, node]) => {
          if (!activeKeys.has(key)) {
            node.remove();
            sharedWorldBattleLinkNodes.delete(key);
          }
        });
      };

      const setSharedWorldFacing = (node, dx = 0, dy = 0, force = false) => {
        if (!node || (Math.abs(dx) < 0.006 && Math.abs(dy) < 0.006)) {
          return;
        }
        const nextFacing = Math.abs(dy) > Math.abs(dx) * 0.72
          ? (dy < 0 ? "up" : "down")
          : (dx < 0 ? "left" : "right");
        const now = Date.now();
        if (node.dataset.facing === nextFacing) {
          return;
        }
        if (!force && Number(node.dataset.facingAt || 0) && now - Number(node.dataset.facingAt || 0) < 320) {
          return;
        }
        node.dataset.facing = nextFacing;
        node.dataset.facingAt = String(now);
        ["left", "right", "up", "down"].forEach((direction) => {
          node.classList.toggle(`is-facing-${direction}`, nextFacing === direction);
        });
      };

      const sharedWorldUseLocalSelfMotion = (key = "") => {
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!me || clean(key).toLowerCase() !== me) {
          return false;
        }
        return sharedWorldHeldArrows.size > 0
          || sharedWorldKeyboardSyncing
          || Boolean(sharedWorldKeyboardQueuedPoint)
          || sharedWorldHasPath(me)
          || (Date.now() - sharedWorldLocalMoveAt < 1800);
      };

      const centerSharedWorldViewportOn = (x = 0.5, y = 0.5, smooth = false) => {
        if (!worldStage || !worldArena) {
          return;
        }
        const left = sharedWorldClamp(x) * worldArena.scrollWidth - worldStage.clientWidth / 2;
        const top = sharedWorldClamp(y) * worldArena.scrollHeight - worldStage.clientHeight / 2;
        worldStage.scrollTo({
          left: Math.max(0, Math.min(worldArena.scrollWidth - worldStage.clientWidth, left)),
          top: Math.max(0, Math.min(worldArena.scrollHeight - worldStage.clientHeight, top)),
          behavior: smooth ? "smooth" : "auto",
        });
      };

      const ensureSharedWorldSelfVisible = (smooth = true) => {
        if (!worldStage || !worldArena || sharedWorldObstacleMode !== "off" || sharedWorldFollowSelf || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const x = sharedWorldClamp(self.x) * worldArena.scrollWidth;
        const y = sharedWorldClamp(self.y) * worldArena.scrollHeight;
        const margin = Math.max(92, Math.min(worldStage.clientWidth, worldStage.clientHeight) * 0.16);
        const left = worldStage.scrollLeft;
        const top = worldStage.scrollTop;
        const right = left + worldStage.clientWidth;
        const bottom = top + worldStage.clientHeight;
        const outside = x < left + margin || x > right - margin || y < top + margin || y > bottom - margin;
        if (!outside) {
          return;
        }
        const now = Date.now();
        if (now - sharedWorldAutoLocateAt < 900) {
          return;
        }
        sharedWorldAutoLocateAt = now;
        centerSharedWorldViewportOn(self.x, self.y, smooth);
      };

      const scheduleSharedWorldMotion = () => {
        if (sharedWorldMotionFrame || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        sharedWorldMotionLastAt = performance.now();
        sharedWorldMotionFrame = window.requestAnimationFrame(stepSharedWorldMotion);
      };

      const stepSharedWorldMotion = (now) => {
        sharedWorldMotionFrame = 0;
        const dt = Math.min(40, Math.max(8, now - (sharedWorldMotionLastAt || now)));
        sharedWorldMotionLastAt = now;
        const activeUsername = clean(activeWorldUsername()).toLowerCase();
        const rows = Array.from(sharedWorldPositions.entries()).filter(([, pos]) => clean(pos && pos.mapMode || "city") === sharedWorldMapMode);
        let moving = false;
        let selfMoving = false;
        const meKey = activeUsername;
        rows.forEach(([key, pos]) => {
          const motionTarget = sharedWorldMotionTargetFor(key, pos);
          let dx = sharedWorldClamp(motionTarget.x, pos.x) - sharedWorldClamp(pos.x);
          let dy = sharedWorldClamp(motionTarget.y, pos.y) - sharedWorldClamp(pos.y);
          let facingDx = dx;
          let facingDy = dy;
          const arenaWidth = Math.max(1, Number(worldArena && worldArena.scrollWidth) || 1);
          const arenaHeight = Math.max(1, Number(worldArena && worldArena.scrollHeight) || 1);
          const pixelDx = dx * arenaWidth;
          const pixelDy = dy * arenaHeight;
          const dist = Math.hypot(pixelDx, pixelDy);
          const node = sharedWorldNodes.get(key);
          if (node && node.classList.contains("is-training-cast")) {
            node.classList.remove("is-moving");
            applySharedWorldNodePosition(node, pos.x, pos.y);
            if (dist > 2 || sharedWorldHasPath(key)) moving = true;
            return;
          }
          let nodeMoving = false;
          if (dist > 2) {
            const horizontalRatio = Math.abs(pixelDx) / dist;
            const directionalSpeedMultiplier = 1 + (0.75 * horizontalRatio);
            const speed = (0.26 + Math.min(0.12, dist * 0.0005)) * directionalSpeedMultiplier;
            const step = Math.min(dist, dt * speed);
            const candidate = {
              x: sharedWorldClamp(pos.x + (pixelDx / dist) * step / arenaWidth),
              y: sharedWorldClamp(pos.y + (pixelDy / dist) * step / arenaHeight),
            };
            const escapingPaintedObstacle = sharedWorldPointBlocked(pos);
            let advancedThisFrame = false;
            if (sharedWorldPointBlocked(candidate) && !escapingPaintedObstacle) {
              pos.blockedSince = Number(pos.blockedSince) || now;
              if (now - pos.blockedSince < 3000) {
                const goal = { x: sharedWorldClamp(pos.goalX, pos.tx), y: sharedWorldClamp(pos.goalY, pos.ty) };
                const reroute = sharedWorldMakeOrthogonalPath({ x: pos.x, y: pos.y }, goal);
                pos.path = reroute.slice();
                if (reroute.length) {
                  sharedWorldPathQueues.set(key, reroute);
                  const slideTarget = reroute[0];
                  const slidePixelDx = (sharedWorldClamp(slideTarget.x) - pos.x) * arenaWidth;
                  const slidePixelDy = (sharedWorldClamp(slideTarget.y) - pos.y) * arenaHeight;
                  const slideDistance = Math.hypot(slidePixelDx, slidePixelDy);
                  if (slideDistance > 0.5) {
                    const slideCandidate = {
                      x: sharedWorldClamp(pos.x + (slidePixelDx / slideDistance) * Math.min(step, slideDistance) / arenaWidth),
                      y: sharedWorldClamp(pos.y + (slidePixelDy / slideDistance) * Math.min(step, slideDistance) / arenaHeight),
                    };
                    if (!sharedWorldPointBlocked(slideCandidate)) {
                      pos.x = slideCandidate.x;
                      pos.y = slideCandidate.y;
                      facingDx = slideTarget.x - pos.x;
                      facingDy = slideTarget.y - pos.y;
                      pos.blockedSince = 0;
                      advancedThisFrame = true;
                    }
                  }
                }
              } else {
                pos.tx = pos.x;
                pos.ty = pos.y;
                pos.goalX = pos.x;
                pos.goalY = pos.y;
                pos.path = [];
                pos.blockedSince = 0;
                sharedWorldPathQueues.delete(key);
              }
            } else {
              pos.x = candidate.x;
              pos.y = candidate.y;
              pos.blockedSince = 0;
              advancedThisFrame = true;
            }
            moving = true;
            nodeMoving = advancedThisFrame || (Number(pos.blockedSince) > 0 && now - Number(pos.blockedSince) < 180);
            if (key === meKey && advancedThisFrame) {
              selfMoving = true;
              sharedWorldLocalMoveAt = Date.now();
            }
          } else {
            pos.x = sharedWorldClamp(motionTarget.x, pos.x);
            pos.y = sharedWorldClamp(motionTarget.y, pos.y);
            if (advanceSharedWorldPathIfReached(key, pos)) {
              moving = true;
              nodeMoving = true;
              if (key === meKey) {
                selfMoving = true;
                sharedWorldLocalMoveAt = Date.now();
              }
            } else {
              pos.x = sharedWorldClamp(pos.tx, pos.x);
              pos.y = sharedWorldClamp(pos.ty, pos.y);
            }
          }
          setSharedWorldFacing(node, facingDx, facingDy);
          if (node) {
            node.classList.toggle("is-moving", nodeMoving);
          }
          applySharedWorldNodePosition(node, pos.x, pos.y);
        });
        if (sharedWorldFollowSelf && sharedWorldObstacleMode === "off") {
          scheduleSharedWorldFollowCenter();
        } else if (selfMoving && sharedWorldObstacleMode === "off") {
          ensureSharedWorldSelfVisible(true);
        }
        if (selfMoving && sharedWorldObstacleMode === "off") {
          maybeActivateSharedWorldPortal();
        }
        updateSharedWorldMoveMarkerArrival();
        syncSharedWorldBattleLinks();
        if (moving && worldModal && worldModal.classList.contains("is-open")) {
          sharedWorldMotionFrame = window.requestAnimationFrame(stepSharedWorldMotion);
        }
      };
