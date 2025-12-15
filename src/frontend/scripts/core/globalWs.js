// @ts-check

export class GlobalWsClient {
  constructor() {
    this.ws = /** @type {WebSocket | null} */ (null);
    this.messageHandlers = [];
    this.openHandlers = [];
    this.closeHandlers = [];
    /** @type {any[]} */
    this.pendingQueue = [];
    this.desiredDebugEnabled = false;
  }

  connect() {
    const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws-global`;
    this.ws = new WebSocket(url);

    this.ws.addEventListener("open", () => {
      // Flush queued messages (e.g., set_debug sent before open).
      for (const msg of this.pendingQueue) {
        try {
          this.ws?.send(msg);
        } catch {
          // ignore
        }
      }
      this.pendingQueue = [];
      for (const h of this.openHandlers) h();
      // Ensure debug state is applied on every (re)connect.
      if (this.desiredDebugEnabled) {
        this.setDebug(this.desiredDebugEnabled);
      }
    });

    this.ws.addEventListener("close", () => {
      for (const h of this.closeHandlers) h();
    });
    this.ws.addEventListener("error", () => {
      for (const h of this.closeHandlers) h();
    });

    this.ws.addEventListener("message", (ev) => {
      try {
        const data = JSON.parse(ev.data);
        for (const h of this.messageHandlers) h(data);
      } catch {
        // ignore
      }
    });
  }

  close() {
    this.ws?.close();
    this.ws = null;
  }

  /**
   * @param {(event:any)=>void} handler
   */
  onMessage(handler) {
    this.messageHandlers.push(handler);
  }

  /**
   * @param {()=>void} handler
   */
  onOpen(handler) {
    this.openHandlers.push(handler);
  }

  /**
   * @param {()=>void} handler
   */
  onClose(handler) {
    this.closeHandlers.push(handler);
  }

  /**
   * @param {string} type
   * @param {any} data
   */
  send(type, data) {
    const payload = JSON.stringify({ type, ...data });
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.pendingQueue.push(payload);
      return;
    }
    this.ws.send(payload);
  }

  /**
   * @param {boolean} enabled
   */
  setDebug(enabled) {
    this.desiredDebugEnabled = Boolean(enabled);
    this.send("set_debug", { enabled: Boolean(enabled) });
  }
}
