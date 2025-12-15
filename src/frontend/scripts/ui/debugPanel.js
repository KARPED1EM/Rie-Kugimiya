// @ts-check

/**
 * @param {any} logEntry
 */
export function appendDebugLog(logEntry) {
  const panel = document.getElementById("debugLogContent");
  if (!panel) return;
  const scrollContainer = document.getElementById("debugLogPanel");
  const shouldAutoScroll = (() => {
    if (!scrollContainer) return false;
    const thresholdPx = 16;
    const distanceFromBottom =
      scrollContainer.scrollHeight -
      scrollContainer.scrollTop -
      scrollContainer.clientHeight;
    return distanceFromBottom <= thresholdPx;
  })();
  const div = document.createElement("div");
  const level = (logEntry.level || "info").toLowerCase();
  div.className = `debug-log-entry level-${level}`;

  const time = new Date(
    (logEntry.timestamp || Date.now() / 1000) * 1000,
  ).toLocaleTimeString();

  const timeSpan = document.createElement("span");
  timeSpan.className = "log-time";
  timeSpan.textContent = `[${time}]`;

  const categorySpan = document.createElement("span");
  categorySpan.className = "log-category";
  categorySpan.textContent = logEntry.category || "system";

  const msgSpan = document.createElement("span");
  msgSpan.className = "log-message";
  msgSpan.textContent = logEntry.message || "";

  const header = document.createElement("div");
  header.className = "log-header";
  header.appendChild(timeSpan);
  header.appendChild(categorySpan);
  header.appendChild(msgSpan);
  div.appendChild(header);

  const meta = logEntry.metadata;
  const metaKeys =
    meta && typeof meta === "object" ? Object.keys(meta) : [];
  if (meta && (typeof meta !== "object" || metaKeys.length > 0)) {
    const details = document.createElement("details");
    details.className = "log-details";

    const summary = document.createElement("summary");
    summary.className = "log-details-summary";
    summary.textContent =
      meta && typeof meta === "object"
        ? `details (${metaKeys.length})`
        : "details";

    const pre = document.createElement("pre");
    pre.className = "log-details-pre";
    try {
      pre.textContent = JSON.stringify(meta, null, 2);
    } catch {
      pre.textContent = String(meta);
    }

    details.appendChild(summary);
    details.appendChild(pre);
    div.appendChild(details);
  }

  panel.appendChild(div);
  if (scrollContainer && shouldAutoScroll) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

export function setDebugPanelVisible(visible) {
  const appContainer = document.querySelector(".app-container");
  const panel = document.getElementById("debugLogPanel");
  appContainer?.classList.toggle("debug-mode", visible);
  panel?.classList.toggle("hidden", !visible);
  if (panel) panel.style.display = visible ? "flex" : "none";
  if (visible && panel) panel.scrollTop = panel.scrollHeight;
}
