// @ts-check

import { showToast } from "./toast.js";

const USER_FALLBACK = "/static/images/avatar/user.webp";
const CHARACTER_FALLBACK = "/static/images/avatar/default.webp";
const BUILTIN_AVATARS = [
  { label: "默认", value: "" },
  { label: "Rin", value: "/static/images/avatar/rin.webp" },
  { label: "阿白", value: "/static/images/avatar/abai.webp" },
];

/**
 * @param {string} value
 * @returns {boolean}
 */
function isDataImage(value) {
  return /^data:image\//i.test(String(value || ""));
}

/**
 * @param {string} value
 * @returns {boolean}
 */
function isHttpUrl(value) {
  const s = String(value || "").trim();
  return /^https?:\/\//i.test(s);
}

/**
 * @param {string} value
 * @returns {boolean}
 */
function isAllowedLocalAvatar(value) {
  return BUILTIN_AVATARS.some((a) => a.value && a.value === value);
}

/**
 * @param {string} value
 * @returns {string}
 */
function normalizeValue(value) {
  return String(value || "").trim();
}

/**
 * @param {string} src
 * @returns {Promise<void>}
 */
function probeImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("Image load failed"));
    img.src = src;
  });
}

/**
 * @param {string} value
 * @param {"user"|"character"} kind
 * @returns {"default"|"url"|"upload"}
 */
function inferActiveTab(value, kind) {
  const v = normalizeValue(value);
  if (!v) return "default";
  if (isDataImage(v)) return "upload";
  if (isHttpUrl(v)) return "url";
  if (kind === "character" && isAllowedLocalAvatar(v)) return "default";
  return "default";
}

/**
 * @param {HTMLElement} host
 * @param {"default"|"url"|"upload"} tab
 */
function setActiveTab(host, tab) {
  host.dataset.activeTab = tab;
  host.querySelectorAll("[data-avatar-tab]").forEach((el) => {
    el.classList.toggle("is-active", el.getAttribute("data-avatar-tab") === tab);
  });
  host.querySelectorAll("[data-avatar-panel]").forEach((el) => {
    el.classList.toggle("is-active", el.getAttribute("data-avatar-panel") === tab);
  });
}

/**
 * @param {HTMLElement} host
 * @returns {string}
 */
export function getAvatarEditorValue(host) {
  return normalizeValue(host.dataset.value || "");
}

/**
 * @param {HTMLElement} host
 * @param {{kind:"user"|"character", initial?: string|null, readonly?: boolean}} opts
 */
export function mountAvatarEditor(host, opts) {
  const kind = opts.kind;
  const readonly = Boolean(opts.readonly);
  const fallback = kind === "user" ? USER_FALLBACK : CHARACTER_FALLBACK;
  const initial = normalizeValue(opts.initial || "");

  host.classList.add("avatar-editor");
  host.dataset.kind = kind;
  host.dataset.value = initial;
  host.dataset.activeTab = inferActiveTab(initial, kind);

  host.innerHTML = `
    <div class="avatar-card ${readonly ? "is-readonly" : ""}">
      <div class="avatar-card-head">
        <div class="avatar-preview-wrap">
          <img class="avatar-preview" alt="avatar preview" />
        </div>
        <div class="avatar-tabs" role="tablist" aria-label="avatar editor">
          <button type="button" class="avatar-tab" data-avatar-tab="default" ${
            readonly ? "disabled" : ""
          }>默认</button>
          <button type="button" class="avatar-tab" data-avatar-tab="url" ${
            readonly ? "disabled" : ""
          }>URL</button>
          <button type="button" class="avatar-tab" data-avatar-tab="upload" ${
            readonly ? "disabled" : ""
          }>上传</button>
        </div>
      </div>

      <div class="avatar-panels">
        <div class="avatar-panel" data-avatar-panel="default">
          ${
            kind === "character"
              ? `
                <div class="avatar-row">
                  <select class="avatar-select" ${readonly ? "disabled" : ""}>
                    ${BUILTIN_AVATARS.map(
                      (a) =>
                        `<option value="${a.value.replaceAll('"', "&quot;")}">${a.label}</option>`,
                    ).join("")}
                  </select>
                </div>
              `
              : `
                <div class="avatar-row">
                  <div class="avatar-hint">使用默认头像</div>
                </div>
              `
          }
        </div>

        <div class="avatar-panel" data-avatar-panel="url">
          <div class="avatar-row">
            <input class="avatar-input" type="text" placeholder="https://..." ${
              readonly ? "disabled" : ""
            } />
            <button type="button" class="avatar-btn avatar-btn-primary" data-action="apply-url" ${
              readonly ? "disabled" : ""
            }>使用</button>
          </div>
          <div class="avatar-hint">支持 http/https 链接</div>
        </div>

        <div class="avatar-panel" data-avatar-panel="upload">
          <div class="avatar-row">
            <label class="avatar-btn avatar-btn-primary ${readonly ? "is-disabled" : ""}">
              <input class="avatar-file" type="file" accept="image/*" ${
                readonly ? "disabled" : ""
              } />
              选择图片
            </label>
          </div>
          <div class="avatar-hint">建议 ≤ 2.5MB</div>
        </div>
      </div>
    </div>
  `;

  const preview = /** @type {HTMLImageElement | null} */ (host.querySelector(".avatar-preview"));
  const fileInput = /** @type {HTMLInputElement | null} */ (host.querySelector(".avatar-file"));
  const urlInput = /** @type {HTMLInputElement | null} */ (host.querySelector(".avatar-input"));
  const builtinSelect = /** @type {HTMLSelectElement | null} */ (
    host.querySelector(".avatar-select")
  );

  /**
   * @param {string} value
   */
  function setValue(value) {
    host.dataset.value = normalizeValue(value);
    const current = getAvatarEditorValue(host);
    if (preview) {
      preview.src = current || fallback;
      preview.onerror = () => {
        preview.onerror = null;
        preview.src = fallback;
      };
    }

    if (builtinSelect && kind === "character") {
      const v = current && isAllowedLocalAvatar(current) ? current : "";
      builtinSelect.value = v;
    }
    if (urlInput) {
      urlInput.value = current && isHttpUrl(current) ? current : "";
    }
  }

  async function applyUrl() {
    if (readonly) return;
    const raw = normalizeValue(urlInput?.value || "");
    if (!raw) {
      showToast("请输入图片 URL。", "error");
      return;
    }
    if (!isHttpUrl(raw)) {
      showToast("仅支持 http/https 图片 URL。", "error");
      return;
    }
    const normalized = new URL(raw).toString();
    setValue(normalized);
    setActiveTab(host, "url");
    try {
      await probeImage(normalized);
      showToast("头像已更新。", "success");
    } catch {
      showToast("链接已保存，但图片可能无法在应用内显示（可改用上传）。", "info");
    }
  }

  if (builtinSelect && kind === "character") {
    builtinSelect.addEventListener("change", () => {
      if (readonly) return;
      const v = normalizeValue(builtinSelect.value);
      setValue(v);
      setActiveTab(host, "default");
    });
  }

  host.querySelectorAll("[data-avatar-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (readonly) return;
      const tab = /** @type {"default"|"url"|"upload"} */ (btn.getAttribute("data-avatar-tab"));
      if (tab === "default") {
        const v =
          kind === "character" && builtinSelect ? normalizeValue(builtinSelect.value) : "";
        setValue(v);
      }
      setActiveTab(host, tab);
    });
  });

  host.querySelector('[data-action="apply-url"]')?.addEventListener("click", applyUrl);
  urlInput?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") applyUrl();
  });

  fileInput?.addEventListener("change", async () => {
    if (readonly) return;
    const file = fileInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showToast("请选择图片文件。", "error");
      fileInput.value = "";
      return;
    }
    if (file.size > 2.5 * 1024 * 1024) {
      showToast("图片过大（>2.5MB），请压缩后再上传。", "error");
      fileInput.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => {
      showToast("读取图片失败。", "error");
      fileInput.value = "";
    };
    reader.onload = async () => {
      const result = String(reader.result || "");
      if (!result || !isDataImage(result)) {
        showToast("图片编码失败。", "error");
        fileInput.value = "";
        return;
      }
      try {
        await probeImage(result);
        setValue(result);
        setActiveTab(host, "upload");
        showToast("头像已更新。", "success");
      } catch {
        showToast("图片无效或无法预览。", "error");
      }
    };
    reader.readAsDataURL(file);
  });

  setValue(initial);
  setActiveTab(host, inferActiveTab(initial, kind));
}
