// @ts-check

import { sha256Json } from "../utils/hash.js";

const STORAGE_KEYS = {
  config: "rin_config",
  characters: "rin_characters",
  sessions: "rin_sessions",
  messages: "rin_messages",
  lastServerHash: "rin_last_server_hash",
  readTimestamps: "rin_read_timestamps",
  userAvatar: "rin_user_avatar",
};

/** @type {import("./types.js").Character[]} */
let characters = [];
/** @type {import("./types.js").Session[]} */
let sessions = [];
/** @type {Record<string, any>} */
let config = {};
/** @type {Map<string, import("./types.js").Message[]>} */
let messageCache = new Map();
/** @type {string | null} */
let activeSessionId = null;
/** @type {string | null} */
let lastServerHash = null;
/** @type {Map<string, number>} */
let readTimestampBySession = new Map();
/** @type {string | null} */
let userAvatar = null;
/** @type {boolean} */
let debugEnabled = false;

export const state = {
  get characters() {
    return characters;
  },
  set characters(v) {
    characters = v;
  },
  get sessions() {
    return sessions;
  },
  set sessions(v) {
    sessions = v;
  },
  get config() {
    return config;
  },
  set config(v) {
    config = v;
  },
  get messageCache() {
    return messageCache;
  },
  get activeSessionId() {
    return activeSessionId;
  },
  get lastServerHash() {
    return lastServerHash;
  },
  get readTimestampBySession() {
    return readTimestampBySession;
  },
  get userAvatar() {
    return userAvatar;
  },
  set userAvatar(v) {
    userAvatar = v;
  },
  get debugEnabled() {
    return debugEnabled;
  },
  set debugEnabled(v) {
    debugEnabled = Boolean(v);
  },
};

export function loadStateFromStorage() {
  try {
    const rawConfig = localStorage.getItem(STORAGE_KEYS.config);
    const rawChars = localStorage.getItem(STORAGE_KEYS.characters);
    const rawSessions = localStorage.getItem(STORAGE_KEYS.sessions);
    const rawMessages = localStorage.getItem(STORAGE_KEYS.messages);
    const rawHash = localStorage.getItem(STORAGE_KEYS.lastServerHash);
    const rawRead = localStorage.getItem(STORAGE_KEYS.readTimestamps);
    const rawAvatar = localStorage.getItem(STORAGE_KEYS.userAvatar);

    config = rawConfig ? JSON.parse(rawConfig) : {};
    // Debug mode is non-persistent.
    if (config && typeof config === "object") {
      delete config.enable_debug_mode;
    }
    characters = rawChars ? JSON.parse(rawChars) : [];
    sessions = rawSessions ? JSON.parse(rawSessions) : [];
    activeSessionId = null;
    lastServerHash = rawHash || null;
    userAvatar = rawAvatar || null;

    messageCache = new Map();
    if (rawMessages) {
      const obj = JSON.parse(rawMessages);
      for (const [sid, msgs] of Object.entries(obj)) {
        messageCache.set(sid, /** @type {any} */ (msgs));
      }
    }

    readTimestampBySession = new Map();
    if (rawRead) {
      const obj = JSON.parse(rawRead);
      for (const [sid, ts] of Object.entries(obj)) {
        if (typeof ts === "number") readTimestampBySession.set(sid, ts);
      }
    }
  } catch {
    characters = [];
    sessions = [];
    config = {};
    messageCache = new Map();
    activeSessionId = null;
    lastServerHash = null;
    readTimestampBySession = new Map();
  }
}

export function saveStateToStorage() {
  try {
    const persistConfig = { ...config };
    delete persistConfig.enable_debug_mode;
    localStorage.setItem(STORAGE_KEYS.config, JSON.stringify(persistConfig));
    localStorage.setItem(STORAGE_KEYS.characters, JSON.stringify(characters));
    localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(sessions));
    localStorage.setItem(
      STORAGE_KEYS.lastServerHash,
      lastServerHash || "",
    );
    localStorage.setItem(STORAGE_KEYS.userAvatar, userAvatar || "");

    const messagesObj = {};
    for (const [sid, msgs] of messageCache.entries()) {
      messagesObj[sid] = msgs;
    }
    localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(messagesObj));

    const readObj = {};
    for (const [sid, ts] of readTimestampBySession.entries()) {
      readObj[sid] = ts;
    }
    localStorage.setItem(
      STORAGE_KEYS.readTimestamps,
      JSON.stringify(readObj),
    );
  } catch {
    // ignore
  }
}

export function setActiveSessionId(sessionId) {
  activeSessionId = sessionId;
}

export function setLastServerHash(hash) {
  lastServerHash = hash;
}

/**
 * @param {string} sessionId
 * @param {import("./types.js").Message[]} messages
 */
export function upsertMessages(sessionId, messages) {
  if (!sessionId) return;
  const existing = messageCache.get(sessionId) || [];
  const map = new Map(existing.map((m) => [m.id, m]));
  
  // First, add all messages to the map
  for (const msg of messages) {
    if (!msg || !msg.id) continue;
    map.set(msg.id, msg);
  }
  
  // Then, handle SYSTEM_RECALL messages to mark target messages as recalled
  for (const msg of messages) {
    if (msg && msg.type === "system-recall" && msg.metadata?.target_message_id) {
      const targetId = msg.metadata.target_message_id;
      const targetMsg = map.get(targetId);
      if (targetMsg) {
        targetMsg.is_recalled = true;
      }
    }
  }
  
  const merged = Array.from(map.values()).sort(
    (a, b) => a.timestamp - b.timestamp,
  );
  messageCache.set(sessionId, merged);
}

/**
 * @param {string} sessionId
 * @param {number} timestamp
 */
export function setReadTimestamp(sessionId, timestamp) {
  if (!sessionId) return;
  const prev = readTimestampBySession.get(sessionId) || 0;
  if (timestamp > prev) {
    readTimestampBySession.set(sessionId, timestamp);
  }
}

export async function computeLocalHash() {
  const payload = { config, characters, sessions };
  return sha256Json(payload);
}
