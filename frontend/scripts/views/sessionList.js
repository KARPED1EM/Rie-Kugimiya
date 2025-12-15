// @ts-check

import { state, saveStateToStorage, setActiveSessionId } from "../core/state.js";
import { renderChatSession, showChatSession, showChatView, ensureChatSessionContainer } from "./chatView.js";
import { formatSessionTimestamp } from "../utils/time.js";
import { clearEmotionTheme } from "../ui/emotionTheme.js";

const DEFAULT_AVATAR = "/static/images/avatar/default.webp";

export function showSessionListView() {
  clearEmotionTheme();
  // No active session when in session list view.
  setActiveSessionId(null);
  document.getElementById("sessionListView")?.classList.remove("hidden");
  document.getElementById("chatView")?.classList.add("hidden");
  document.getElementById("wechatInput")?.classList.add("hidden");
  const backBtn = document.getElementById("backButton");
  backBtn?.classList.remove("hidden");
  backBtn?.classList.add("invisible");
  const title = document.getElementById("chatTitle");
  if (title) title.textContent = "微信";

  const menuBtn = document.getElementById("menuButton");
  const popover = document.getElementById("menuPopover");
  menuBtn?.classList.add("plus-mode");
  menuBtn?.setAttribute("aria-label", "add character");
  menuBtn?.setAttribute("title", "Add");
  popover?.classList.remove("open");
  popover?.setAttribute("aria-hidden", "true");
  
  // Hide new message indicator when in session list view
  const newMsgBtn = document.getElementById("newMessageBtn");
  if (newMsgBtn) {
    newMsgBtn.classList.remove("show");
    newMsgBtn.classList.add("hidden");
  }
}

export function renderSessionListView() {
  const list = document.getElementById("sessionList");
  if (!list) return;
  list.innerHTML = "";

  const sessions = state.sessions.slice();
  sessions.sort((a, b) => getLastEffectiveTimestamp(b.id) - getLastEffectiveTimestamp(a.id));
  if (sessions.length === 0) {
    const empty = document.createElement("div");
    empty.className = "session-empty-state";
    empty.innerHTML = "<p>暂无会话</p><p>点击右上角「＋」创建角色后开始聊天</p>";
    list.appendChild(empty);
    return;
  }

  for (const session of sessions) {
    const character = state.characters.find((c) => c.id === session.character_id);
    if (!character) continue;
    const item = buildSessionItem(session, character);
    list.appendChild(item);
  }

  // Plus button handled globally in appCore.
}

function getLastEffectiveTimestamp(sessionId) {
  const msgs = state.messageCache.get(sessionId) || [];
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const msg = msgs[i];
    if (msg.is_recalled) continue;
    if (msg.type === "system-emotion" || msg.type === "system-typing") continue;
    return msg.timestamp || 0;
  }
  return 0;
}

function buildSessionItem(session, character) {
  const div = document.createElement("div");
  div.className = "session-item";
  // No persistent active styling for session items.

  const avatarWrap = document.createElement("div");
  avatarWrap.className = "session-avatar-wrap";

  const avatar = document.createElement("img");
  avatar.className = "avatar";
  avatar.src = character.avatar ? String(character.avatar) : DEFAULT_AVATAR;
  avatar.onerror = () => {
    avatar.onerror = null;
    avatar.src = DEFAULT_AVATAR;
  };
  avatarWrap.appendChild(avatar);

  div.appendChild(avatarWrap);

  const info = document.createElement("div");
  info.className = "session-item-content";

  const header = document.createElement("div");
  header.className = "session-item-header";

  const name = document.createElement("div");
  name.className = "session-item-name";
  name.textContent = character.name;

  const time = document.createElement("div");
  time.className = "session-item-time";
  time.textContent = getLastPreviewTime(session.id);

  header.appendChild(name);
  header.appendChild(time);

  const preview = document.createElement("div");
  preview.className = "session-item-preview";
  preview.textContent = getLastPreviewText(session.id);

  info.appendChild(header);
  info.appendChild(preview);
  div.appendChild(info);

  const unread = getUnreadCount(session.id);
  if (unread > 0) {
    const badge = document.createElement("div");
    badge.className = "session-unread-badge";
    badge.textContent = unread > 99 ? "99+" : String(unread);
    avatarWrap.appendChild(badge);
  }

  div.addEventListener("click", async () => {
    const switching = state.activeSessionId !== session.id;
    if (switching) {
      setActiveSessionId(session.id);
    }
    window.dispatchEvent(new CustomEvent("active-session-changed"));
    showChatView();
    ensureChatSessionContainer(session.id);
    showChatSession(session.id, true);
    saveStateToStorage();
  });

  return div;
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

function getLastPreviewText(sessionId) {
  const msgs = state.messageCache.get(sessionId) || [];
  for (let i = msgs.length - 1; i >= 0; i -= 1) {
    const msg = msgs[i];
    if (msg.is_recalled) continue;
    if (msg.type === "system-emotion" || msg.type === "system-typing") continue;
    if (msg.type === "text") return msg.content.slice(0, 30);
    if (msg.type === "image") return "[Image]";
    if (msg.type === "system-recall") return "Message recalled";
  }
  return "No messages yet";
}

function getLastPreviewTime(sessionId) {
  const msgs = state.messageCache.get(sessionId) || [];
  const last = msgs.filter((m) => !m.is_recalled).slice(-1)[0];
  if (!last) return "";
  return formatSessionTimestamp(last.timestamp);
}
