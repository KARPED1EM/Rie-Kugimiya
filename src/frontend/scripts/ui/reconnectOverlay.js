// @ts-check

let overlayEl = /** @type {HTMLElement | null} */ (null);

export function showReconnectOverlay() {
  if (overlayEl) return;
  const el = document.createElement("div");
  el.id = "reconnectOverlay";
  el.className = "reconnect-overlay";
  el.innerHTML = `
    <div class="reconnect-card">
      <div class="reconnect-title">正在重连...</div>
      <div class="reconnect-list" id="reconnectList"></div>
      <div class="reconnect-footer" id="reconnectFooter"></div>
    </div>
  `;
  document.body.appendChild(el);
  overlayEl = el;
}

/**
 * @param {{id:string, connected:boolean, retries:number, failed:boolean}[]} items
 * @param {boolean} failed
 */
export function updateReconnectOverlay(items, failed) {
  if (!overlayEl) return;
  const list = overlayEl.querySelector("#reconnectList");
  const footer = overlayEl.querySelector("#reconnectFooter");
  if (list) {
    list.innerHTML = "";
    for (const item of items) {
      const row = document.createElement("div");
      row.className = "reconnect-row";
      row.innerHTML = `
        <span class="reconnect-name">${item.id}</span>
        <span class="reconnect-status ${item.connected ? "ok" : "bad"}">
          ${item.connected ? "已连接" : item.failed ? "失败" : "重连中"}
        </span>
        <span class="reconnect-retries">${item.connected ? "" : `#${item.retries}`}</span>
      `;
      list.appendChild(row);
    }
  }
  if (footer) {
    footer.textContent = failed
      ? "重连次数已达上限，请检查服务器并刷新页面。"
      : "请稍候，重连期间界面已禁用。";
  }
}

export function hideReconnectOverlay() {
  overlayEl?.remove();
  overlayEl = null;
}

