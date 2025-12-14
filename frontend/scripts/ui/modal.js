// @ts-check

import { state, saveStateToStorage, setActiveSessionId } from "../core/state.js";
import * as api from "../core/api.js";
import { showToast } from "./toast.js";
import { mountAvatarEditor, getAvatarEditorValue } from "./avatarEditor.js";

/** @type {Array<{key:string,type:string,default:any,group:string}> | null} */
let behaviorSchemaCache = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeBaseUrl(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (!["http:", "https:"].includes(url.protocol)) return "";
    const path = (url.pathname || "").replace(/\/+$/, "");
    return `${url.origin}${path}`;
  } catch {
    return "";
  }
}

async function getBehaviorSchema() {
  if (behaviorSchemaCache) return behaviorSchemaCache;
  try {
    behaviorSchemaCache = await api.fetchCharacterBehaviorSchema();
    return behaviorSchemaCache;
  } catch {
    return null;
  }
}

/**
 * Pre-fetch behavior schema during app initialization to avoid delay on first modal open
 */
export async function prefetchBehaviorSchema() {
  await getBehaviorSchema();
}

function createOverlay() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  return overlay;
}

/**
 * Ensures overlay dismissal only happens when both pointer down/up occurred outside the modal.
 * @param {HTMLDivElement} overlay
 * @param {{onDismiss: () => void, canDismiss?: () => boolean}} options
 */
function attachOverlayDismiss(overlay, { onDismiss, canDismiss = () => true }) {
  let startedOutside = false;

  overlay.addEventListener("mousedown", (ev) => {
    startedOutside = canDismiss() && ev.target === overlay;
  });

  overlay.addEventListener("mouseup", (ev) => {
    if (startedOutside && ev.target === overlay && canDismiss()) {
      onDismiss();
    }
    startedOutside = false;
  });
}

function createModalShell(title) {
  const modal = document.createElement("div");
  modal.className = "modal";

  const header = document.createElement("div");
  header.className = "modal-header";
  header.innerHTML = `
    <h2>${title}</h2>
    <button class="modal-close" data-modal-close>&times;</button>
  `;

  const body = document.createElement("div");
  body.className = "modal-body";

  modal.appendChild(header);
  modal.appendChild(body);
  return { modal, body };
}

/**
 * @param {boolean} forceOpen
 * @returns {Promise<boolean>}
 */
export function showSettingsModal(forceOpen) {
  return new Promise((resolve) => {
    const overlay = createOverlay();
    const { modal, body } = createModalShell("设置");

    body.innerHTML = getSettingsContent();
    overlay.appendChild(modal);

    const avatarHost = /** @type {HTMLElement | null} */ (
      modal.querySelector("#settingsAvatarEditor")
    );
    if (avatarHost) {
      mountAvatarEditor(avatarHost, {
        kind: "user",
        initial: state.userAvatar,
        readonly: false,
      });
    }

    const closeBtns = modal.querySelectorAll("[data-modal-close]");
    if (forceOpen) closeBtns.forEach((b) => b.classList.add("hidden"));

    attachOverlayDismiss(overlay, {
      canDismiss: () => !forceOpen,
      onDismiss: () => {
        overlay.remove();
        resolve(false);
      },
    });

    closeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!forceOpen) {
          overlay.remove();
          resolve(false);
        }
      });
    });

    modal.querySelector("#settingsSaveBtn")?.addEventListener("click", async () => {
      const ok = await saveSettings(modal);
      if (ok) {
        overlay.remove();
        resolve(true);
      }
    });

    document.body.appendChild(overlay);
  });
}

function getSettingsContent() {
  const provider = state.config.llm_provider || "deepseek";
  const apiKey = state.config.llm_api_key || "";
  const model = state.config.llm_model || "";
  const baseUrl = normalizeBaseUrl(state.config.llm_base_url) || "";
  const nickname = state.config.user_nickname || "";
  const emotionTheme = state.config.enable_emotion_theme !== "false";
  const debugMode = state.debugEnabled === true;

  return `
    <div class="modal-section">
      <div class="form-group">
        <label>服务商</label>
        <select id="settingsProvider">
          <option value="deepseek" ${
            provider === "deepseek" ? "selected" : ""
          }>DeepSeek</option>
          <option value="openai" ${
            provider === "openai" ? "selected" : ""
          }>OpenAI</option>
          <option value="anthropic" ${
            provider === "anthropic" ? "selected" : ""
          }>Anthropic</option>
        </select>
      </div>
      <div class="form-group">
        <label>API Key</label>
        <input id="settingsApiKey" type="password" value="${apiKey}" placeholder="必填" />
      </div>
      <div class="form-group">
        <label>模型</label>
        <input id="settingsModel" type="text" value="${model}" placeholder="必填" />
      </div>
      <div class="form-group">
        <label>Base URL（可选覆盖服务商域名）</label>
        <input
          id="settingsBaseUrl"
          type="text"
          value="${baseUrl}"
          placeholder="https://example.com/proxy"
        />
        <div class="help-text">
          留空或填写格式非法不会改变默认 URL，填写合法 http/https 地址则强制替换服务商的域名部分。
        </div>
      </div>
      <div class="form-group">
        <label>用户昵称</label>
        <input id="settingsNickname" type="text" value="${nickname}" />
      </div>
      <div class="form-group">
        <label>用户头像</label>
        <div id="settingsAvatarEditor"></div>
      </div>
      <div class="form-group inline">
        <label>情绪主题</label>
        <label class="switch">
          <input id="settingsEmotionTheme" type="checkbox" ${
            emotionTheme ? "checked" : ""
          } />
          <span class="slider"></span>
        </label>
      </div>
      <div class="form-group inline">
        <label>调试模式</label>
        <label class="switch">
          <input id="settingsDebugMode" type="checkbox" ${
            debugMode ? "checked" : ""
          } />
          <span class="slider"></span>
        </label>
      </div>
      <div class="modal-actions">
        <button class="btn-primary" id="settingsSaveBtn">保存</button>
      </div>
    </div>
  `;
}

async function saveSettings(modal) {
  const provider = modal.querySelector("#settingsProvider")?.value;
  const apiKey = modal.querySelector("#settingsApiKey")?.value?.trim();
  const model = modal.querySelector("#settingsModel")?.value?.trim();
  const rawBaseUrl = modal.querySelector("#settingsBaseUrl")?.value?.trim();
  const nickname = modal.querySelector("#settingsNickname")?.value?.trim();
  const emotionTheme = modal.querySelector("#settingsEmotionTheme")?.checked;
  const debugMode = modal.querySelector("#settingsDebugMode")?.checked;
  const avatarEditor = /** @type {HTMLElement | null} */ (
    modal.querySelector("#settingsAvatarEditor")
  );
  const newAvatar = avatarEditor ? getAvatarEditorValue(avatarEditor) : "";

  if (!provider || !apiKey || !model) {
    showToast("服务商、API Key 和模型为必填项。", "error");
    return false;
  }
  const baseUrl = normalizeBaseUrl(rawBaseUrl);
  if (rawBaseUrl && !baseUrl) {
    showToast("Base URL 格式非法，将回退为默认服务商域名。", "warning");
  }

  state.config.llm_provider = provider;
  state.config.llm_api_key = apiKey;
  state.config.llm_model = model;
  state.config.llm_base_url = baseUrl || "";
  state.config.user_nickname = nickname || "";
  state.config.enable_emotion_theme = String(Boolean(emotionTheme));
  state.debugEnabled = Boolean(debugMode);

  try {
    await api.updateUserAvatar(newAvatar || "");
    await api.updateConfig({
      llm_provider: provider,
      llm_api_key: apiKey,
      llm_model: model,
      llm_base_url: baseUrl || "",
      user_nickname: nickname || "",
      enable_emotion_theme: String(Boolean(emotionTheme)).toLowerCase(),
    });
    state.userAvatar = newAvatar || null;
    window.dispatchEvent(
      new CustomEvent("user-avatar-changed", { detail: { avatar: newAvatar || null } }),
    );
    saveStateToStorage();
    window.dispatchEvent(
      new CustomEvent("debug-mode-changed", { detail: { enabled: debugMode } }),
    );
    showToast("设置已保存。", "success");
    return true;
  } catch (err) {
    const msg = err instanceof Error ? err.message : "保存设置失败。";
    showToast(msg || "保存设置失败。", "error");
    return false;
  }
}

/**
 * @param {import("../core/types.js").Character} character
 * @returns {Promise<void>}
 */
export async function showCharacterSettingsModal(character) {
  const overlay = createOverlay();
  const readonly = character.is_builtin;
  const { modal, body } = createModalShell(
    `${character.name} 设置${readonly ? "（预览）" : ""}`,
  );

  const behaviorFields = await getBehaviorSchema();
  body.innerHTML = `
    <div class="modal-section">
      ${
        readonly
          ? '<div class="modal-notice modal-notice-readonly modal-notice-strong">系统自带角色，仅可预览，不可编辑。</div>'
          : ""
      }
      <div class="form-group">
        <label>名称</label>
        <input id="charName" type="text" value="${escapeHtml(character.name)}" ${
          readonly ? "readonly" : ""
        } />
      </div>
      <div class="form-group">
        <label>头像</label>
        <div id="charAvatarEditor"></div>
      </div>
      <div class="form-group">
        <label>人设</label>
        <textarea id="charPersona" rows="6" ${
          readonly ? "readonly" : ""
        }>${escapeHtml(character.persona)}</textarea>
      </div>
      ${
        Array.isArray(behaviorFields) && behaviorFields.length
          ? renderCharacterBehaviorFields(character, behaviorFields, readonly)
          : '<div class="modal-notice modal-notice-readonly">行为系统配置加载失败（可尝试刷新页面）。</div>'
      }
      <div class="modal-actions">
        ${
          readonly
            ? ""
            : '<button class="modal-btn modal-btn-danger" id="charDeleteBtn">删除角色</button>'
        }
        <button class="modal-btn modal-btn-primary" id="charSaveBtn" ${
          readonly ? "disabled" : ""
        }>保存</button>
      </div>
    </div>
  `;

  modal
    .querySelectorAll("[data-modal-close]")
    .forEach((btn) => btn.addEventListener("click", () => overlay.remove()));
  attachOverlayDismiss(overlay, {
    onDismiss: () => overlay.remove(),
  });

  modal.querySelector("#charSaveBtn")?.addEventListener("click", async () => {
    if (readonly) return;
    const name = modal.querySelector("#charName")?.value?.trim();
    const avatarEditor = /** @type {HTMLElement | null} */ (
      modal.querySelector("#charAvatarEditor")
    );
    const avatar = avatarEditor ? getAvatarEditorValue(avatarEditor) : "";
    const persona = modal.querySelector("#charPersona")?.value?.trim() || "";
    if (!name) {
      showToast("名称为必填项。", "error");
      return;
    }

    const behaviorParams = collectCharacterBehaviorParams(modal, behaviorFields);
    if (behaviorParams === null) return;

    try {
      const updated = await api.updateCharacter(character.id, {
        name,
        avatar,
        persona,
        behavior_params: behaviorParams,
      });
      Object.assign(character, updated);
      window.dispatchEvent(
        new CustomEvent("character-avatar-changed", {
          detail: { characterId: character.id, avatar: updated.avatar || "" },
        }),
      );
      saveStateToStorage();
      showToast("角色已更新。", "success");
      overlay.remove();
    } catch {
      showToast("更新角色失败。", "error");
    }
  });

  modal.querySelector("#charDeleteBtn")?.addEventListener("click", async () => {
    if (readonly) return;
    const ok = await showConfirmModal("删除该角色？此操作不可恢复。");
    if (!ok) return;

    try {
      await api.deleteCharacter(character.id);

      const sess = state.sessions.find((s) => s.character_id === character.id);
      const sessionId = sess?.id || null;

      state.characters = state.characters.filter((c) => c.id !== character.id);
      state.sessions = state.sessions.filter((s) => s.character_id !== character.id);

      if (sessionId) {
        state.messageCache.delete(sessionId);
        state.readTimestampBySession.delete(sessionId);
      }

      setActiveSessionId(null);
      saveStateToStorage();
      showToast("角色已删除。", "success");
      overlay.remove();

      window.dispatchEvent(
        new CustomEvent("character-deleted", {
          detail: { characterId: character.id, sessionId },
        }),
      );
    } catch {
      showToast("删除失败。", "error");
    }
  });

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  const charAvatarEditor = /** @type {HTMLElement | null} */ (
    modal.querySelector("#charAvatarEditor")
  );
  if (charAvatarEditor) {
    mountAvatarEditor(charAvatarEditor, {
      kind: "character",
      initial: character.avatar || "",
      readonly,
    });
  }

  if (Array.isArray(behaviorFields) && behaviorFields.length) {
    initTagInputs(modal, character, behaviorFields, readonly);
  }
}

/**
 * @param {import("../core/types.js").Character} character
 * @param {Array<{key:string,type:string,default:any,group:string}>} fields
 * @param {boolean} readonly
 */
function renderCharacterBehaviorFields(character, fields, readonly) {
  /** @type {Record<string, Array<{key:string,type:string,default:any,group:string}>>} */
  const grouped = {};
  fields.forEach((f) => {
    (grouped[f.group] ||= []).push(f);
  });

  // Define module display names
  const moduleNames = {
    timeline: "时间轴模块",
    segmenter: "分段模块",
    typo: "错字模块",
    recall: "撤回模块",
    pause: "停顿模块",
    sticker: "表情包模块",
  };

  // Get all modules that have fields, sorted alphabetically
  const modules = Object.keys(grouped).sort();

  const sections = modules
    .map((group) => {
      // Get display name or use capitalized group name as fallback
      const title = moduleNames[group] || group.charAt(0).toUpperCase() + group.slice(1);
      
      // Sort fields within each group by type: bool -> list -> number -> text
      const typeOrder = { bool: 0, "list[str]": 1, int: 2, float: 3, str: 4 };
      const sortedFields = grouped[group].sort((a, b) => {
        const orderA = typeOrder[a.type] ?? 99;
        const orderB = typeOrder[b.type] ?? 99;
        return orderA - orderB;
      });

      const inner = sortedFields
        .map((f) => renderBehaviorField(character, f, readonly))
        .join("");

      return `
        <details class="modal-details">
          <summary>${title}</summary>
          <div class="modal-details-body">${inner}</div>
        </details>
      `;
    })
    .join("");

  return `
    <div class="modal-divider"></div>
    ${sections}
  `;
}

/**
 * @param {import("../core/types.js").Character} character
 * @param {{key:string,type:string,default:any,group:string}} field
 * @param {boolean} readonly
 */
function renderBehaviorField(character, field, readonly) {
  const key = field.key;
  const type = String(field.type || "str");
  const currentValue = character?.[key];
  const value = currentValue ?? field.default ?? "";
  const label = escapeHtml(key);
  const help =
    field.default !== undefined && field.default !== null
      ? `<div class="help-text">default: ${escapeHtml(field.default)}</div>`
      : "";

  if (type === "bool") {
    return `
      <div class="form-group inline">
        <label>${label}</label>
        <label class="switch">
          <input type="checkbox" data-bfield="${escapeHtml(key)}" ${
            value ? "checked" : ""
          } ${readonly ? "disabled" : ""} />
          <span class="slider"></span>
        </label>
      </div>
    `;
  }

  if (type === "int" || type === "float") {
    const step = type === "int" ? "1" : "0.01";
    return `
      <div class="form-group">
        <label>${label}</label>
        <input type="number" step="${step}" data-bfield="${escapeHtml(key)}" value="${escapeHtml(
          value,
        )}" ${readonly ? "disabled" : ""} />
        ${help}
      </div>
    `;
  }

  if (type.startsWith("list[")) {
    return `
      <div class="form-group">
        <label>${label}</label>
        <div class="tag-input" data-bfield="${escapeHtml(key)}" ${
          readonly ? 'data-readonly="true"' : ""
        }></div>
        <div class="help-text">回车/逗号添加，点击标签删除</div>
      </div>
    `;
  }

  return `
    <div class="form-group">
      <label>${label}</label>
      <input type="text" data-bfield="${escapeHtml(key)}" value="${escapeHtml(
        value,
      )}" ${readonly ? "disabled" : ""} />
      ${help}
    </div>
  `;
}

/**
 * @param {HTMLElement} modal
 * @param {import("../core/types.js").Character} character
 * @param {Array<{key:string,type:string,default:any,group:string}>} fields
 * @param {boolean} readonly
 */
function initTagInputs(modal, character, fields, readonly) {
  fields
    .filter((f) => String(f.type || "").startsWith("list["))
    .forEach((f) => {
      const container = /** @type {HTMLElement | null} */ (
        modal.querySelector(`[data-bfield="${f.key}"].tag-input`)
      );
      if (!container) return;
      const initial = Array.isArray(character?.[f.key]) ? character[f.key] : [];
      setupTagInput(container, initial, readonly);
    });
}

/**
 * @param {HTMLElement} container
 * @param {string[]} initialTags
 * @param {boolean} readonly
 */
function setupTagInput(container, initialTags, readonly) {
  /** @type {string[]} */
  let tags = Array.isArray(initialTags) ? initialTags.slice() : [];
  tags = normalizeTags(tags);

  container.innerHTML = "";
  container.classList.add("tag-input");

  const input = document.createElement("input");
  input.type = "text";
  input.className = "tag-input-field";
  input.placeholder = readonly ? "" : "输入后回车…";
  input.disabled = Boolean(readonly);

  function sync() {
    container.dataset.value = JSON.stringify(tags);
    container.querySelectorAll(".tag-chip").forEach((n) => n.remove());
    tags.forEach((t) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      const text = document.createElement("span");
      text.className = "tag-chip-text";
      text.textContent = t;
      chip.appendChild(text);

      if (!readonly) {
        const rm = document.createElement("button");
        rm.type = "button";
        rm.className = "tag-chip-remove";
        rm.textContent = "×";
        rm.addEventListener("click", () => {
          tags = tags.filter((x) => x !== t);
          sync();
        });
        chip.appendChild(rm);
      }

      container.insertBefore(chip, input);
    });
  }

  /**
   * @param {string} raw
   */
  function addFromRaw(raw) {
    if (readonly) return;
    const parts = raw.split(/[,\n]+/g);
    let changed = false;
    for (const part of parts) {
      const next = normalizeTags([part])[0];
      if (!next) continue;
      if (tags.includes(next)) continue;
      tags.push(next);
      changed = true;
    }
    if (changed) {
      tags = normalizeTags(tags);
      input.value = "";
      sync();
    }
  }

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === "," || ev.key === "Tab") {
      ev.preventDefault();
      addFromRaw(input.value);
      return;
    }

    if (ev.key === "Backspace" && !input.value) {
      if (readonly) return;
      if (!tags.length) return;
      tags.pop();
      sync();
    }
  });
  input.addEventListener("blur", () => addFromRaw(input.value));
  input.addEventListener("paste", (ev) => {
    if (readonly) return;
    const text = ev.clipboardData?.getData("text/plain");
    if (!text) return;
    if (!/[,\n]/.test(text)) return;
    ev.preventDefault();
    addFromRaw(text);
  });

  container.addEventListener("click", () => {
    if (!readonly) input.focus();
  });

  container.appendChild(input);
  sync();
}

/**
 * @param {string[]} raw
 * @returns {string[]}
 */
function normalizeTags(raw) {
  const out = [];
  for (const item of raw || []) {
    const s = String(item ?? "").trim();
    if (!s) continue;
    if (!out.includes(s)) out.push(s);
  }
  return out;
}

/**
 * @param {HTMLElement} modal
 * @param {Array<{key:string,type:string,default:any,group:string}> | null} fields
 * @returns {Record<string, any> | null}
 */
function collectCharacterBehaviorParams(modal, fields) {
  if (!Array.isArray(fields) || !fields.length) return {};

  /** @type {Record<string, any>} */
  const out = {};

  for (const f of fields) {
    const key = f.key;
    const type = String(f.type || "str");
    const el = modal.querySelector(`[data-bfield="${key}"]`);
    if (!el) continue;

    if (type === "bool") {
      out[key] = Boolean(/** @type {HTMLInputElement} */ (el).checked);
      continue;
    }

    if (type === "int" || type === "float") {
      const raw = /** @type {HTMLInputElement} */ (el).value;
      if (raw === "" || raw == null) {
        showToast(`${key} 不能为空`, "error");
        return null;
      }
      const num = type === "int" ? Number.parseInt(raw, 10) : Number.parseFloat(raw);
      if (Number.isNaN(num)) {
        showToast(`${key} 不是有效数字`, "error");
        return null;
      }
      out[key] = num;
      continue;
    }

    if (type.startsWith("list[")) {
      out[key] = readTagInputValue(/** @type {HTMLElement} */ (el));
      continue;
    }

    out[key] = String(/** @type {HTMLInputElement} */ (el).value ?? "");
  }

  return out;
}

/**
 * @param {HTMLElement | null} container
 * @returns {string[]}
 */
function readTagInputValue(container) {
  if (!container) return [];
  try {
    const tags = JSON.parse(container.dataset.value || "[]");
    return Array.isArray(tags) ? tags : [];
  } catch {
    return [];
  }
}

/**
 * @returns {Promise<boolean>}
 */
export function showCreateCharacterModal() {
  return new Promise((resolve) => {
    const overlay = createOverlay();
    const { modal, body } = createModalShell("创建角色");

    body.innerHTML = `
      <div class="modal-section">
        <div class="form-group">
          <label>名称</label>
          <input id="newCharName" type="text" placeholder="必填" />
        </div>
        <div class="modal-actions">
          <button class="modal-btn modal-btn-secondary" data-modal-close>取消</button>
          <button class="modal-btn modal-btn-primary" id="newCharCreateBtn">创建</button>
        </div>
      </div>
    `;

    modal.querySelectorAll("[data-modal-close]").forEach((btn) =>
      btn.addEventListener("click", () => {
        overlay.remove();
        resolve(false);
      }),
    );
    attachOverlayDismiss(overlay, {
      onDismiss: () => {
        overlay.remove();
        resolve(false);
      },
    });

    modal.querySelector("#newCharCreateBtn")?.addEventListener("click", async () => {
      const name = modal.querySelector("#newCharName")?.value?.trim();
      if (!name) {
        showToast("名称为必填项。", "error");
        return;
      }
      try {
        const created = await api.createCharacter({ name });
        state.characters.push(created);
        state.sessions = await api.fetchSessions();
        saveStateToStorage();
        showToast("角色已创建。", "success");
        overlay.remove();
        resolve(true);
      } catch {
        showToast("创建角色失败。", "error");
      }
    });

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  });
}

/**
 * @param {string} message
 * @returns {Promise<boolean>}
 */
export function showErrorModal(message) {
  return new Promise((resolve) => {
    const overlay = createOverlay();
    const { modal, body } = createModalShell("错误");
    body.innerHTML = `
      <p>${message}</p>
      <div class="modal-actions">
        <button class="btn-secondary" data-modal-close>取消</button>
        <button class="btn-primary" id="retryBtn">重试</button>
      </div>
    `;

    modal.querySelectorAll("[data-modal-close]").forEach((btn) =>
      btn.addEventListener("click", () => {
        overlay.remove();
        resolve(false);
      }),
    );
    modal.querySelector("#retryBtn")?.addEventListener("click", () => {
      overlay.remove();
      resolve(true);
    });

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  });
}

/**
 * @param {string} message
 * @returns {Promise<boolean>}
 */
export function showConfirmModal(message) {
  return new Promise((resolve) => {
    const overlay = createOverlay();
    const { modal, body } = createModalShell("警告");
    body.innerHTML = `
      <div class="confirm-message">${message}</div>
      <div class="modal-actions">
        <button class="btn-secondary" data-modal-close>取消</button>
        <button class="modal-btn modal-btn-danger" id="confirmBtn">确认删除</button>
      </div>
    `;

    modal.querySelectorAll("[data-modal-close]").forEach((btn) =>
      btn.addEventListener("click", () => {
        overlay.remove();
        resolve(false);
      }),
    );
    modal.querySelector("#confirmBtn")?.addEventListener("click", () => {
      overlay.remove();
      resolve(true);
    });

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  });
}
