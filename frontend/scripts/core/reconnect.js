// @ts-check
import { showReconnectOverlay, updateReconnectOverlay, hideReconnectOverlay } from "../ui/reconnectOverlay.js";

const MAX_RETRIES = 8;
const BASE_DELAY_MS = 1200;

class ReconnectController {
  constructor() {
    /** @type {Map<string, {connect: ()=>void, connected: boolean, retries: number, timer: any}>} */
    this.items = new Map();
    this.overlayVisible = false;
  }

  /**
   * @param {string} id
   * @param {()=>void} connectFn
   */
  register(id, connectFn) {
    if (this.items.has(id)) return;
    this.items.set(id, {
      connect: connectFn,
      connected: false,
      retries: 0,
      timer: null,
    });
    this._render();
  }

  markConnected(id) {
    const item = this.items.get(id);
    if (!item) return;
    item.connected = true;
    item.retries = 0;
    if (item.timer) {
      clearTimeout(item.timer);
      item.timer = null;
    }
    this._render();
    this._maybeHide();
  }

  markDisconnected(id) {
    const item = this.items.get(id);
    if (!item) return;
    if (!item.connected && item.timer) return;
    item.connected = false;
    this._render();
    this._show();
    this._scheduleRetry(id);
  }

  /**
   * Unregister a connection (e.g. when character/session is deleted)
   * @param {string} id
   */
  unregister(id) {
    const item = this.items.get(id);
    if (!item) return;
    if (item.timer) {
      clearTimeout(item.timer);
      item.timer = null;
    }
    this.items.delete(id);
    this._render();
    this._maybeHide();
  }

  _scheduleRetry(id) {
    const item = this.items.get(id);
    if (!item) return;
    if (item.retries >= MAX_RETRIES) {
      this._render(true);
      return;
    }
    const delay = BASE_DELAY_MS * Math.pow(1.4, item.retries);
    item.timer = setTimeout(() => {
      item.timer = null;
      item.retries += 1;
      this._render();
      try {
        item.connect();
      } catch {
        // ignore
      }
      this._scheduleRetry(id);
    }, delay);
  }

  _show() {
    if (this.overlayVisible) return;
    this.overlayVisible = true;
    showReconnectOverlay();
    this._render();
  }

  _maybeHide() {
    const anyDisconnected = Array.from(this.items.values()).some((i) => !i.connected);
    const anyFailed = Array.from(this.items.values()).some((i) => i.retries >= MAX_RETRIES && !i.connected);
    if (!anyDisconnected && !anyFailed && this.overlayVisible) {
      this.overlayVisible = false;
      hideReconnectOverlay();
    }
  }

  _render(failed = false) {
    const list = Array.from(this.items.entries()).map(([id, item]) => ({
      id,
      connected: item.connected,
      retries: item.retries,
      failed: failed && !item.connected && item.retries >= MAX_RETRIES,
    }));
    updateReconnectOverlay(list, failed);
  }
}

export const reconnectController = new ReconnectController();

