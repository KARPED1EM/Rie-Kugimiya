// @ts-check
import {
  loadStateFromStorage,
  saveStateToStorage,
  state,
  setActiveSessionId,
  setLastServerHash,
  upsertMessages,
  setReadTimestamp,
} from "./state.js";
import * as api from "./api.js";
import { WsClient } from "./ws.js";
import { GlobalWsClient } from "./globalWs.js";
import { renderSessionListView, showSessionListView } from "../views/sessionList.js";
import { renderChatSession, showChatSession, showChatView, ensureChatSessionContainer, setWsClient, dropChatSessionContainer, refreshVisibleAvatars } from "../views/chatView.js";
import { showSettingsModal, showErrorModal, showConfirmModal } from "../ui/modal.js";
import { showToast } from "../ui/toast.js";
import { appendDebugLog, setDebugPanelVisible } from "../ui/debugPanel.js";
import { reconnectController } from "./reconnect.js";

export function createApp() {
  /** @type {Map<string, WsClient>} */
  const wsClientsBySession = new Map();
  /** @type {WsClient | null} */
  let activeWsClient = null;
  const globalWsClient = new GlobalWsClient();
  let localDebugAckSent = false;

  async function init() {
    loadStateFromStorage();
    await syncStartup();
    setupGlobalListeners();
    startStatusClock();
    showMainShell();
    connectGlobalWs();
    ensureSessionConnections();
    renderCurrentView();
  }

  async function syncStartup() {
    let serverHash = "";
    try {
      serverHash = await api.fetchServerHash();
    } catch (error) {
      await handleStartupError("Failed to fetch server hash.", syncStartup);
      return;
    }

    if (!serverHash) {
      await handleStartupError("Server hash empty.", syncStartup);
      return;
    }

    const shouldFullSync = state.lastServerHash !== serverHash;
    if (shouldFullSync) {
      const ok = await fullSync();
      if (!ok) {
        await handleStartupError("Full sync failed.", syncStartup);
        return;
      }
    }

    await incrementalMessageSync();
    setLastServerHash(serverHash);
    saveStateToStorage();
  }

  async function fullSync() {
    try {
      const [characters, sessions, config] = await Promise.all([
        api.fetchCharacters(),
        api.fetchSessions(),
        api.fetchConfig(),
      ]);

      state.characters = characters;
      state.sessions = sessions;
      state.config = config;
      state.userAvatar = await api.fetchUserAvatar();

      setActiveSessionId(null);
      ensureSessionConnections();
      saveStateToStorage();
      return true;
    } catch (error) {
      return false;
    }
  }

  async function incrementalMessageSync() {
    for (const session of state.sessions) {
      const cached = state.messageCache.get(session.id) || [];
      const lastTs =
        cached.length > 0 ? Math.max(...cached.map((m) => m.timestamp)) : 0;

      try {
        const messages = await api.fetchMessages(session.id, lastTs);
        if (messages.length > 0) {
          upsertMessages(session.id, messages);
        }

        const lastReadFromServer = getLastReadFromMessages(
          state.messageCache.get(session.id) || [],
        );
        if (lastReadFromServer > 0) {
          setReadTimestamp(session.id, lastReadFromServer);
        }
      } catch {
        // ignore per-session errors
      }
    }
    saveStateToStorage();
  }

  function getLastReadFromMessages(messages) {
    let lastRead = 0;
    for (const msg of messages) {
      if (msg.is_read && !msg.is_recalled) {
        lastRead = Math.max(lastRead, msg.timestamp);
      }
    }
    return lastRead;
  }

  function ensureSessionConnections() {
    const existingIds = new Set(wsClientsBySession.keys());
    const currentIds = new Set(state.sessions.map((s) => s.id));

    for (const id of existingIds) {
      if (!currentIds.has(id)) {
        wsClientsBySession.get(id)?.close();
        wsClientsBySession.delete(id);
      }
    }

    for (const session of state.sessions) {
      if (wsClientsBySession.has(session.id)) continue;
      const client = new WsClient(session.id);
      client.onMessage((event) => handleWsMessage(event, session.id));
      client.onOpen(() => {
        reconnectController.markConnected(session.id);
        if (isConfigValid(state.config)) {
          client.initRin(state.config);
        }
      });
      client.onClose(() => reconnectController.markDisconnected(session.id));
      client.connect();
      reconnectController.register(session.id, () => client.connect());
      wsClientsBySession.set(session.id, client);
    }

    updateActiveClient();
  }

  function updateActiveClient() {
    activeWsClient = state.activeSessionId
      ? wsClientsBySession.get(state.activeSessionId) || null
      : null;
    setWsClient(activeWsClient);
  }

  function updateDebugModeUI() {
    const debugEnabled = state.debugEnabled === true;
    setDebugPanelVisible(debugEnabled);
    if (debugEnabled && !localDebugAckSent) {
      localDebugAckSent = true;
      appendDebugLog({
        timestamp: Date.now() / 1000,
        level: "info",
        category: "system",
        message: "Debug mode enabled (client)",
      });
    }
    if (!debugEnabled) localDebugAckSent = false;
  }

  function handleWsMessage(event, sourceSessionId) {
    switch (event.type) {
      case "history": {
        const messages = event.data.messages || [];
        if (sourceSessionId) {
          upsertMessages(sourceSessionId, messages);
        }
        if (sourceSessionId) {
          ensureChatSessionContainer(sourceSessionId);
        }
        if (sourceSessionId === state.activeSessionId && !isChatViewHidden()) {
          renderChatSession(sourceSessionId, { scrollOnEnter: true });
        } else {
          renderSessionListView();
        }
        saveStateToStorage();
        break;
      }
      case "message": {
        const msg = event.data;
        if (!msg || !msg.session_id) return;
        upsertMessages(msg.session_id, [msg]);

        if (state.debugEnabled && msg.type === "system-emotion") {
          appendDebugLog({
            timestamp: Date.now() / 1000,
            level: "info",
            category: "emotion",
            message: `Emotion update received for ${msg.session_id}`,
          });
        }

        ensureChatSessionContainer(msg.session_id);
        renderChatSession(msg.session_id, { scrollOnEnter: false });
        if (msg.session_id !== state.activeSessionId || isChatViewHidden()) {
          renderSessionListView();
        }
        saveStateToStorage();
        break;
      }
      case "session_recreated": {
        const { old_session_id, new_session_id } = event.data;
        if (!old_session_id || !new_session_id) return;

        const idx = state.sessions.findIndex((s) => s.id === old_session_id);
        if (idx >= 0) {
          state.sessions[idx].id = new_session_id;
          state.sessions[idx].is_active = false;
        }

        // Drop old cache entirely; the new session will deliver a fresh history.
        state.messageCache.delete(old_session_id);
        state.messageCache.delete(new_session_id);
        state.readTimestampBySession.delete(old_session_id);
        state.readTimestampBySession.delete(new_session_id);

        if (state.activeSessionId === old_session_id) {
          setActiveSessionId(new_session_id);
          updateActiveClient();
          ensureChatSessionContainer(new_session_id);
          if (!isChatViewHidden()) showChatSession(new_session_id, true);
        }

        dropChatSessionContainer(old_session_id);

        wsClientsBySession.get(old_session_id)?.close();
        wsClientsBySession.delete(old_session_id);
        const newClient = new WsClient(new_session_id);
        newClient.onMessage((e) => handleWsMessage(e, new_session_id));
        newClient.onOpen(() => {
          reconnectController.markConnected(new_session_id);
          if (isConfigValid(state.config)) {
            newClient.initRin(state.config);
          }
        });
        newClient.onClose(() => reconnectController.markDisconnected(new_session_id));
        newClient.connect();
        reconnectController.register(new_session_id, () => newClient.connect());
        wsClientsBySession.set(new_session_id, newClient);

        // Render immediately (empty). History will arrive via session WS.
        ensureChatSessionContainer(new_session_id);
        renderChatSession(new_session_id, { scrollOnEnter: true });

        renderSessionListView();
        showToast("对话已清空。", "success");
        saveStateToStorage();
        break;
      }
      case "read_state": {
        const { session_id, last_read_timestamp } = event.data;
        if (session_id && typeof last_read_timestamp === "number") {
          setReadTimestamp(session_id, last_read_timestamp);
          ensureChatSessionContainer(session_id);
          renderChatSession(session_id, { scrollOnEnter: false });
          if (session_id !== state.activeSessionId || isChatViewHidden()) {
            renderSessionListView();
          }
          saveStateToStorage();
        }
        break;
      }
      case "error": {
        if (event.data?.message) {
          showToast(`错误：${event.data.message}`, "error");
        }
        break;
      }
      default:
        break;
    }
  }

  function connectGlobalWs() {
    globalWsClient.onMessage(handleGlobalMessage);
    globalWsClient.onOpen(() => {
      reconnectController.markConnected("global");
    });
    globalWsClient.onClose(() => reconnectController.markDisconnected("global"));
    globalWsClient.connect();
    reconnectController.register("global", () => globalWsClient.connect());
  }

  function handleGlobalMessage(event) {
    switch (event.type) {
      case "toast": {
        const payload = event.data || {};
        const level = payload.level || "info";
        const type = level === "warning" ? "info" : level;
        if (payload.message) showToast(payload.message, type);
        break;
      }
      case "debug_log": {
        appendDebugLog(event.data);
        break;
      }
      default:
        break;
    }
  }

  function setupGlobalListeners() {
    const backBtn = document.getElementById("backButton");
    backBtn?.addEventListener("click", () => {
      showSessionListView();
      renderSessionListView();
    });

    const menuBtn = document.getElementById("menuButton");
    const popover = document.getElementById("menuPopover");
    menuBtn?.addEventListener("click", () => {
      if (menuBtn.classList.contains("plus-mode")) {
        import("../ui/modal.js").then((m) =>
          m.showCreateCharacterModal().then((created) => {
            if (created) {
              ensureSessionConnections();
              renderSessionListView();
            }
          }),
        );
        return;
      }
      const expanded = menuBtn.getAttribute("aria-expanded") === "true";
      menuBtn.setAttribute("aria-expanded", String(!expanded));
      popover?.setAttribute("aria-hidden", String(expanded));
      popover?.classList.toggle("open", !expanded);
    });

    popover?.addEventListener("click", async (ev) => {
      const target = /** @type {HTMLElement} */ (ev.target);
      const item = target.closest("[data-action]");
      const action = item?.getAttribute("data-action");
      if (!action) return;
      if (action === "clear") {
        const ok = await showConfirmModal("清空当前对话？");
        if (ok) {
          activeWsClient?.clearSession();
          showToast("正在清空对话...", "info");
        }
      }
      if (action === "character") {
        showCharacterSettings();
      }
      popover.classList.remove("open");
      popover.setAttribute("aria-hidden", "true");
      menuBtn?.setAttribute("aria-expanded", "false");
    });

    document.addEventListener("click", (ev) => {
      if (!popover || !menuBtn) return;
      if (!popover.classList.contains("open")) return;
      const target = /** @type {HTMLElement} */ (ev.target);
      const wrapper = target.closest(".menu-wrapper");
      if (wrapper) return;
      popover.classList.remove("open");
      popover.setAttribute("aria-hidden", "true");
      menuBtn.setAttribute("aria-expanded", "false");
    });

    const floatingGithubBtn = document.getElementById("floatingGithubBtn");
    floatingGithubBtn?.addEventListener("click", () => {
      window.open("https://github.com/KARPED1EM/Yuzuriha-Rin", "_blank");
    });

    const floatingSettingsBtn = document.getElementById("floatingSettingsBtn");
    floatingSettingsBtn?.addEventListener("click", () => {
      showSettingsModal(false).then((saved) => {
        if (saved) {
          ensureSessionConnections();
          if (isConfigValid(state.config)) {
            for (const client of wsClientsBySession.values()) {
              client.initRin(state.config);
            }
          }
        }
      });
    });

    window.addEventListener("debug-mode-changed", (ev) => {
      const enabled = Boolean(ev.detail?.enabled);
      state.debugEnabled = enabled;
      updateDebugModeUI();
      globalWsClient.setDebug(enabled);
    });

    window.addEventListener("character-deleted", (ev) => {
      const sessionId = ev.detail?.sessionId;
      if (sessionId) {
        wsClientsBySession.get(sessionId)?.close();
        wsClientsBySession.delete(sessionId);
        dropChatSessionContainer(sessionId);
      }
      setActiveSessionId(null);
      showSessionListView();
      ensureSessionConnections();
      renderSessionListView();
      saveStateToStorage();
    });

    window.addEventListener("active-session-changed", () => {
      updateActiveClient();
      updateDebugModeUI();
    });

    window.addEventListener("user-avatar-changed", () => {
      refreshVisibleAvatars();
    });

    window.addEventListener("character-avatar-changed", (ev) => {
      const characterId = ev.detail?.characterId;
      if (characterId) {
        renderSessionListView();
        refreshVisibleAvatars();
      }
    });
  }

  function showMainShell() {
    document.getElementById("wechatShell")?.classList.remove("hidden");
    document.getElementById("floatingGithubBtn")?.classList.remove("hidden");
    document.getElementById("floatingSettingsBtn")?.classList.remove("hidden");
  }

  function startStatusClock() {
    const ampmEl = document.getElementById("statusAmPm");
    const clockEl = document.getElementById("statusClock");
    if (!ampmEl || !clockEl) return;

    const update = () => {
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes().toString().padStart(2, "0");
      const displayHour = (hours % 12) || 12;
      const ampm = hours < 12 ? "上午" : "下午";
      ampmEl.textContent = ampm;
      clockEl.textContent = `${displayHour}:${minutes}`;
    };

    update();
    setInterval(update, 30000);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) update();
    });
  }

  function renderCurrentView() {
    if (state.activeSessionId) {
      showChatView();
      ensureChatSessionContainer(state.activeSessionId);
      renderChatSession(state.activeSessionId, { scrollOnEnter: true });
      showChatSession(state.activeSessionId, true);
    } else {
      showSessionListView();
      renderSessionListView();
    }

    if (!isConfigValid(state.config)) {
      showSettingsModal(true).then((saved) => {
        if (saved) {
          ensureSessionConnections();
          if (isConfigValid(state.config)) {
            for (const client of wsClientsBySession.values()) {
              client.initRin(state.config);
            }
          }
        }
      });
    }

    // Debug mode is non-persistent; always start disabled.
    state.debugEnabled = false;
    updateDebugModeUI();
  }

  function isChatViewHidden() {
    const chatView = document.getElementById("chatView");
    return chatView?.classList.contains("hidden");
  }

  function showCharacterSettings() {
    const session = state.sessions.find((s) => s.id === state.activeSessionId);
    if (!session) return;
    const character = state.characters.find(
      (c) => c.id === session.character_id,
    );
    if (!character) return;
    import("../ui/modal.js").then((m) =>
      m.showCharacterSettingsModal(character),
    );
  }

  function isConfigValid(config) {
    const provider = config.llm_provider;
    const apiKey = config.llm_api_key;
    const model = config.llm_model;
    if (!provider || !apiKey || !model) return false;
    return true;
  }

  async function handleStartupError(message, retry) {
    const shouldRetry = await showErrorModal(message);
    if (shouldRetry) retry().catch(() => {});
  }

  return { init };
}
