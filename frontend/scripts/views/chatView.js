// @ts-check

import { state, setReadTimestamp, saveStateToStorage } from "../core/state.js";
import { applyEmotionTheme, clearEmotionTheme } from "../ui/emotionTheme.js";
import { formatChatTimestamp } from "../utils/time.js";
import { attachZoomToContainer } from "../ui/imageZoom.js";

/** @type {import("../core/ws.js").WsClient | null} */
let wsClient = null;
/** @type {Map<string, boolean>} */
const typingStateBySession = new Map();
/** @type {Map<string, HTMLElement>} */
const messageContainersBySession = new Map();
let activeMessageContainer = /** @type {HTMLElement | null} */ (null);

const DEFAULT_CHARACTER_AVATAR = "/static/images/avatar/default.webp";
const DEFAULT_USER_AVATAR = "/static/images/avatar/user.webp";

/**
 * @param {HTMLImageElement} img
 * @param {string} src
 */
function applyAvatar(img, src, fallback) {
  const safe = src ? String(src) : "";
  img.src = safe || fallback;
  img.onerror = () => {
    img.onerror = null;
    img.src = fallback;
  };
}

export function setWsClient(client) {
  wsClient = client;
  setupInputHandlers();
}

export function refreshVisibleAvatars() {
  if (!activeMessageContainer) return;
  const sessionId = activeMessageContainer.dataset.sessionId || "";
  if (!sessionId) return;

  const nodes = activeMessageContainer.querySelectorAll(".message");
  nodes.forEach((node) => {
    const senderId = node.getAttribute("data-sender-id") || node.dataset.senderId || "";
    const img = /** @type {HTMLImageElement | null} */ (
      node.querySelector("img.message-avatar")
    );
    if (!img) return;
    const src =
      senderId === "user"
        ? state.userAvatar || DEFAULT_USER_AVATAR
        : getCharacterAvatar(sessionId);
    applyAvatar(img, src, senderId === "user" ? DEFAULT_USER_AVATAR : DEFAULT_CHARACTER_AVATAR);
  });
}

/**
 * Remove a session's chat container and related in-memory UI state.
 * @param {string} sessionId
 */
export function dropChatSessionContainer(sessionId) {
  const el = messageContainersBySession.get(sessionId);
  if (el) el.remove();
  messageContainersBySession.delete(sessionId);
  typingStateBySession.delete(sessionId);
  if (activeMessageContainer?.dataset.sessionId === sessionId) {
    activeMessageContainer = null;
  }
}

export function showChatView() {
  document.getElementById("sessionListView")?.classList.add("hidden");
  document.getElementById("chatView")?.classList.remove("hidden");
  document.getElementById("wechatInput")?.classList.remove("hidden");
  const backBtn = document.getElementById("backButton");
  backBtn?.classList.remove("hidden");
  backBtn?.classList.remove("invisible");

  const menuBtn = document.getElementById("menuButton");
  menuBtn?.classList.remove("plus-mode");
  menuBtn?.setAttribute("aria-label", "more actions");
  menuBtn?.setAttribute("title", "More");
}

/**
 * Ensure a per-session messages container exists and returns it.
 * @param {string} sessionId
 */
export function ensureChatSessionContainer(sessionId) {
  const host = document.getElementById("chatView");
  if (!host) return null;

  let container = messageContainersBySession.get(sessionId);
  if (!container) {
    const wrap = document.createElement("div");
    wrap.className = "messages";
    wrap.id = `messages-${sessionId}`;
    wrap.dataset.sessionId = sessionId;
    wrap.setAttribute("role", "log");
    wrap.setAttribute("aria-live", "polite");
    wrap.classList.add("hidden");
    host.insertBefore(wrap, host.firstChild);
    container = wrap;
    messageContainersBySession.set(sessionId, container);
  }
  return container;
}

/**
 * Show a given session's chat without rebuilding on click.
 * @param {string} sessionId
 * @param {boolean} scrollToBottomOnEnter
 */
export function showChatSession(sessionId, scrollToBottomOnEnter) {
  for (const [sid, el] of messageContainersBySession.entries()) {
    el.classList.toggle("hidden", sid !== sessionId);
  }
  activeMessageContainer = messageContainersBySession.get(sessionId) || null;
  setupInputHandlers();
  if (activeMessageContainer) {
    setupScrollReadTracking(activeMessageContainer);
    if (activeMessageContainer.childElementCount === 0) {
      renderChatSession(sessionId, { scrollOnEnter: scrollToBottomOnEnter });
    }
    if (scrollToBottomOnEnter) {
      scrollToBottom(activeMessageContainer);
      markAllRead(sessionId);
      updateNewMessageIndicator(sessionId, activeMessageContainer);
    }
  }
  applyHeaderTitle(sessionId);
  applyEmotionForSession(sessionId);
}

/**
 * Render (or re-render) a specific session's messages container.
 * @param {string} sessionId
 * @param {{scrollOnEnter?: boolean}} opts
 */
export function renderChatSession(sessionId, opts = {}) {
  const container = ensureChatSessionContainer(sessionId);
  if (!container) return;

  const messages = state.messageCache.get(sessionId) || [];
  typingStateBySession.set(sessionId, false);

  const prevScrollHeight = container.scrollHeight;
  const prevScrollTop = container.scrollTop;
  const wasAtBottom = isAtBottom(container);

  container.innerHTML = "";
  const effective = messages.filter((m) => !m.is_recalled);

  let latestEmotionMap = null;
  let isBlocked = false;
  let blockTimestamp = null;

  // First pass: find if there's any blocked message
  for (const msg of effective) {
    if (msg.type === "system-blocked") {
      isBlocked = true;
      blockTimestamp = msg.timestamp;
      break;
    }
  }

  for (const msg of effective) {
    if (msg.type === "system-emotion") {
      latestEmotionMap = msg.metadata;
      continue;
    }
    if (msg.type === "system-typing") {
      updateTypingIndicator(sessionId, msg.metadata);
      continue;
    }

    if (msg.type === "system-time") {
      container.appendChild(buildSystemTimeHint(msg));
      continue;
    }
    if (msg.type === "system-hint") {
      container.appendChild(buildHintMessage(msg));
      continue;
    }
    if (msg.type === "system-recall") {
      container.appendChild(buildRecallNotice(msg));
      continue;
    }
    if (msg.type === "system-blocked") {
      // Don't render blocked messages, just track the state
      continue;
    }
    if (msg.type === "system-tool") {
      // Don't render tool messages, only used in LLM history
      continue;
    }

    // Check if this message is after block
    const isAfterBlock = isBlocked && blockTimestamp !== null && msg.timestamp > blockTimestamp;

    if (msg.type === "text") {
      const element = buildTextMessage(msg);
      if (isAfterBlock) {
        addBlockedIndicator(element);
      }
      container.appendChild(element);
      continue;
    }
    if (msg.type === "image") {
      const element = buildImageMessage(msg);
      if (isAfterBlock) {
        addBlockedIndicator(element);
      }
      container.appendChild(element);
      continue;
    }
    container.appendChild(buildUnsupportedMessage(msg));
  }

  if (sessionId === state.activeSessionId) {
    activeMessageContainer = container;
    applyHeaderTitle(sessionId);
    setupInputHandlers();
    setupScrollReadTracking(container);
    applyEmotionForSession(sessionId, latestEmotionMap);

    if (opts.scrollOnEnter) {
      scrollToBottom(container);
      markAllRead(sessionId);
    } else if (wasAtBottom) {
      scrollToBottom(container);
      markAllRead(sessionId);
    } else {
      const newHeight = container.scrollHeight;
      const delta = newHeight - prevScrollHeight;
      container.scrollTop = prevScrollTop + Math.max(0, delta);
    }

    updateNewMessageIndicator(sessionId, container);
  }

  // Attach zoom to image messages only
  attachZoomToContainer(container);
}

/**
 * Apply latest emotion glow for a session (chat view only).
 * @param {string} sessionId
 * @param {any=} latestFromRender
 */
function applyEmotionForSession(sessionId, latestFromRender) {
  const chatView = document.getElementById("chatView");
  if (!chatView || chatView.classList.contains("hidden")) {
    clearEmotionTheme();
    return;
  }

  const enabled =
    String(state.config.enable_emotion_theme ?? "true").toLowerCase() !== "false";
  if (!enabled) {
    clearEmotionTheme();
    return;
  }

  const map =
    latestFromRender ||
    findLatestEmotionMap(state.messageCache.get(sessionId) || []);
  if (!map || typeof map !== "object") {
    clearEmotionTheme();
    return;
  }
  const keys = Object.keys(map).map((k) => String(k).toLowerCase());
  const hasNonNeutral = keys.some((k) => k && k !== "neutral");
  if (!hasNonNeutral) {
    clearEmotionTheme();
    return;
  }
  applyEmotionTheme(map);
}

/**
 * Add blocked indicator (red exclamation mark) to a message element.
 * @param {HTMLElement} messageElement
 */
function addBlockedIndicator(messageElement) {
  const indicator = document.createElement("span");
  indicator.className = "blocked-indicator";
  indicator.textContent = "!";
  indicator.title = "此消息在被拉黑后发送";
  
  // Find the message bubble within the message element
  const bubble = messageElement.querySelector(".message-bubble");
  if (bubble) {
    // Insert the indicator inside the bubble (at the beginning)
    bubble.insertBefore(indicator, bubble.firstChild);
  }
  
  messageElement.classList.add("message-blocked");
}

/**
 * @param {import("../core/types.js").Message[]} messages
 */
function findLatestEmotionMap(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m && !m.is_recalled && m.type === "system-emotion") return m.metadata;
  }
  return null;
}

function applyHeaderTitle(sessionId) {
  const session = state.sessions.find((s) => s.id === sessionId);
  const character = session
    ? state.characters.find((c) => c.id === session.character_id)
    : null;
  const title = document.getElementById("chatTitle");
  if (!title) return;
  if (typingStateBySession.get(sessionId)) {
    title.textContent = "对方正在输入...";
  } else {
    title.textContent = character?.name || "Chat";
  }
}

function buildSystemTimeHint(msg) {
  const div = document.createElement("div");
  div.className = "system-hint";
  div.textContent = formatChatTimestamp(msg.timestamp);
  return div;
}

function buildHintMessage(msg) {
  const div = document.createElement("div");
  div.className = "system-hint";
  div.textContent = msg.content;
  return div;
}

function buildRecallNotice() {
  const div = document.createElement("div");
  div.className = "system-hint";
  div.textContent = "Message recalled";
  return div;
}

function buildTextMessage(msg) {
  const div = document.createElement("div");
  div.className = `message ${msg.sender_id === "user" ? "message-user" : "message-assistant"}`;
  div.dataset.messageId = msg.id;
  div.dataset.timestamp = String(msg.timestamp);
  div.dataset.senderId = msg.sender_id;

  const avatar = document.createElement("img");
  avatar.className = "message-avatar";
  applyAvatar(
    avatar,
    msg.sender_id === "user"
      ? state.userAvatar || DEFAULT_USER_AVATAR
      : getCharacterAvatar(msg.session_id),
    msg.sender_id === "user" ? DEFAULT_USER_AVATAR : DEFAULT_CHARACTER_AVATAR,
  );

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = msg.content;

  if (msg.sender_id === "user") {
    div.appendChild(bubble);
    div.appendChild(avatar);
  } else {
    div.appendChild(avatar);
    div.appendChild(bubble);
  }
  return div;
}

function buildImageMessage(msg) {
  const div = document.createElement("div");
  div.className = `message ${msg.sender_id === "user" ? "message-user" : "message-assistant"}`;
  div.dataset.messageId = msg.id;
  div.dataset.timestamp = String(msg.timestamp);
  div.dataset.senderId = msg.sender_id;

  const avatar = document.createElement("img");
  avatar.className = "message-avatar";
  applyAvatar(
    avatar,
    msg.sender_id === "user"
      ? state.userAvatar || DEFAULT_USER_AVATAR
      : getCharacterAvatar(msg.session_id),
    msg.sender_id === "user" ? DEFAULT_USER_AVATAR : DEFAULT_CHARACTER_AVATAR,
  );

  const bubble = document.createElement("div");
  bubble.className = "message-bubble message-image";

  const img = document.createElement("img");
  img.src = msg.content;
  img.alt = "Image";
  bubble.appendChild(img);

  if (msg.sender_id === "user") {
    div.appendChild(bubble);
    div.appendChild(avatar);
  } else {
    div.appendChild(avatar);
    div.appendChild(bubble);
  }
  return div;
}

function buildUnsupportedMessage(msg) {
  const div = document.createElement("div");
  div.className = `message ${msg.sender_id === "user" ? "message-user" : "message-assistant"}`;
  div.dataset.messageId = msg.id;
  div.dataset.timestamp = String(msg.timestamp);
  div.dataset.senderId = msg.sender_id;

  const avatar = document.createElement("img");
  avatar.className = "message-avatar";
  applyAvatar(
    avatar,
    msg.sender_id === "user"
      ? state.userAvatar || DEFAULT_USER_AVATAR
      : getCharacterAvatar(msg.session_id),
    msg.sender_id === "user" ? DEFAULT_USER_AVATAR : DEFAULT_CHARACTER_AVATAR,
  );

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = `${msg.type} message is not supported yet`;

  if (msg.sender_id === "user") {
    div.appendChild(bubble);
    div.appendChild(avatar);
  } else {
    div.appendChild(avatar);
    div.appendChild(bubble);
  }
  return div;
}

function getCharacterAvatar(sessionId) {
  const session = state.sessions.find((s) => s.id === sessionId);
  const character = session
    ? state.characters.find((c) => c.id === session.character_id)
    : null;
  const avatar = character?.avatar ? String(character.avatar) : "";
  return avatar || DEFAULT_CHARACTER_AVATAR;
}

function setupInputHandlers() {
  const input = /** @type {HTMLTextAreaElement | null} */ (
    document.getElementById("userInput")
  );
  const sendBtn = document.getElementById("toggleBtn");
  if (!input || !sendBtn || !wsClient) return;

  input.disabled = false;

  input.oninput = () => {
    adjustTextareaHeight(input);
    if (input.value.trim()) {
      sendBtn.classList.remove("hidden");
      sendBtn.disabled = false;
    } else {
      sendBtn.classList.add("hidden");
      sendBtn.disabled = true;
    }
  };

  input.onkeydown = (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      sendCurrentText();
    }
  };

  sendBtn.onclick = () => sendCurrentText();
}

function sendCurrentText() {
  const input = /** @type {HTMLTextAreaElement | null} */ (
    document.getElementById("userInput")
  );
  if (!input || !wsClient) return;
  const content = input.value.trim();
  if (!content) return;
  wsClient.sendText(content);
  input.value = "";
  adjustTextareaHeight(input);
  const sendBtn = document.getElementById("toggleBtn");
  if (sendBtn) {
    sendBtn.classList.add("hidden");
    sendBtn.disabled = true;
  }
}

function adjustTextareaHeight(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 100)}px`;
}

let scrollThrottleTimer = 0;

function setupScrollReadTracking(container) {
  if (container.dataset.scrollBound === "true") return;
  container.dataset.scrollBound = "true";

  container.addEventListener("scroll", () => {
    if (scrollThrottleTimer) return;
    scrollThrottleTimer = window.setTimeout(() => {
      scrollThrottleTimer = 0;
      handleScroll(container);
    }, 180);
  });

  const newMsgBtn = document.getElementById("newMessageBtn");
  newMsgBtn?.addEventListener("click", () => {
    scrollToBottom(container);
    markAllRead(state.activeSessionId);
    updateNewMessageIndicator(state.activeSessionId, container);
  });
}

function handleScroll(container) {
  const sessionId = state.activeSessionId;
  if (!sessionId) return;

  const visibleBottom = container.scrollTop + container.clientHeight;
  const messageNodes = Array.from(
    container.querySelectorAll(".message[data-timestamp]"),
  );
  let maxSeenTs = 0;
  for (const node of messageNodes) {
    const el = /** @type {HTMLElement} */ (node);
    const senderId = el.dataset.senderId;
    if (senderId && senderId !== "assistant") {
      continue;
    }
    const bottom = el.offsetTop + el.offsetHeight;
    if (bottom <= visibleBottom + 4) {
      const ts = Number(el.dataset.timestamp || 0);
      if (ts > maxSeenTs) maxSeenTs = ts;
    }
  }

  if (maxSeenTs > 0) {
    markReadUpTo(sessionId, maxSeenTs);
  }

  if (isAtBottom(container)) {
    markAllRead(sessionId);
  }

  updateNewMessageIndicator(sessionId, container);
}

function markAllRead(sessionId) {
  if (!sessionId) return;
  const msgs = state.messageCache.get(sessionId) || [];
  const lastAssistant = msgs
    .filter(
      (m) =>
        m.sender_id === "assistant" &&
        !m.is_recalled &&
        m.type !== "system-emotion" &&
        m.type !== "system-typing",
    )
    .slice(-1)[0];
  if (!lastAssistant) return;
  markReadUpTo(sessionId, lastAssistant.timestamp);
}

function markReadUpTo(sessionId, timestamp) {
  const current = state.readTimestampBySession.get(sessionId) || 0;
  if (timestamp <= current) return;
  setReadTimestamp(sessionId, timestamp);
  saveStateToStorage();
  wsClient?.markRead(timestamp);
}

function updateNewMessageIndicator(sessionId, container) {
  const unread = getUnreadCount(sessionId);
  const btn = document.getElementById("newMessageBtn");
  const text = document.getElementById("newMessageText");
  if (!btn || !text) return;

  if (unread > 0 && !isAtBottom(container)) {
    btn.classList.remove("hidden");
    text.textContent = `${unread} 条新消息`;
  } else {
    btn.classList.add("hidden");
  }
}

function getUnreadCount(sessionId) {
  const msgs = state.messageCache.get(sessionId) || [];
  const lastRead = state.readTimestampBySession.get(sessionId) || 0;
  let count = 0;
  for (const msg of msgs) {
    if (msg.is_recalled) continue;
    if (msg.sender_id !== "assistant") continue;
    if (msg.type === "system-emotion" || msg.type === "system-typing") continue;
    if (msg.timestamp > lastRead) count += 1;
  }
  return count;
}

function isAtBottom(container) {
  return (
    container.scrollHeight - container.scrollTop - container.clientHeight < 6
  );
}

function scrollToBottom(container) {
  container.scrollTop = container.scrollHeight;
}

function updateTypingIndicator(sessionId, metadata) {
  const userId = metadata?.user_id;
  if (userId === "user") return;
  typingStateBySession.set(sessionId, Boolean(metadata?.is_typing));
  if (sessionId && sessionId === state.activeSessionId) {
    applyHeaderTitle(sessionId);
  }

  const hint = document.getElementById("typingHint");
  if (hint) hint.style.display = "none";
}

// Timestamp formatting handled by utils/time.js
