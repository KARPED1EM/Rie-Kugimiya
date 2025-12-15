// @ts-check

const JSON_HEADERS = { "Content-Type": "application/json" };

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = "";
    try {
      const text = await res.text();
      if (text) {
        try {
          const parsed = JSON.parse(text);
          detail =
            typeof parsed?.detail === "string" ? parsed.detail : JSON.stringify(parsed);
        } catch {
          detail = text;
        }
      }
    } catch {
      // ignore
    }
    throw new Error(`HTTP ${res.status}${detail ? `: ${detail}` : ""}`);
  }
  return res.json();
}

export async function fetchServerHash() {
  const data = await fetchJson("/api/hash");
  return data.hash || "";
}

export async function fetchCharacters() {
  const data = await fetchJson("/api/characters");
  return data.characters || [];
}

export async function fetchSessions() {
  const data = await fetchJson("/api/sessions");
  return data.sessions || [];
}

/**
 * Incremental message sync over HTTP.
 * @param {string} sessionId
 * @param {number} afterTimestamp
 */
export async function fetchMessages(sessionId, afterTimestamp) {
  const data = await fetchJson(
    `/api/sessions/${sessionId}/messages?after=${encodeURIComponent(afterTimestamp || 0)}`,
  );
  return data.messages || [];
}

export async function fetchConfig() {
  const data = await fetchJson("/api/config");
  return data.config || {};
}

export async function updateConfig(config) {
  await fetchJson("/api/config", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ config }),
  });
}

export async function fetchUserAvatar() {
  try {
    const data = await fetchJson("/api/avatar");
    return data.avatar || null;
  } catch {
    return null;
  }
}

/**
 * @param {string|null} avatar
 */
export async function updateUserAvatar(avatar) {
  await fetchJson("/api/avatar", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ avatar: avatar || "" }),
  });
}

export async function createCharacter(payload) {
  const data = await fetchJson("/api/characters", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return data.character;
}

export async function updateCharacter(id, payload) {
  const data = await fetchJson(`/api/characters/${id}`, {
    method: "PUT",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return data.character;
}

export async function deleteCharacter(id) {
  await fetchJson(`/api/characters/${id}`, { method: "DELETE" });
}

export async function fetchCharacterBehaviorSchema() {
  const data = await fetchJson("/api/characters/behavior-schema");
  return data.fields || [];
}
