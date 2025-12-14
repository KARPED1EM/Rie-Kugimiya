// @ts-check

export class WsClient {
  /**
   * @param {string} sessionId
   */
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.ws = /** @type {WebSocket | null} */ (null);
    this.messageHandlers = [];
    this.openHandlers = [];
    this.closeHandlers = [];
  }

  connect() {
    const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.addEventListener("open", () => {
      for (const h of this.openHandlers) h();
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
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ type, ...data }));
  }

  /**
   * @param {Record<string, any>} config
   */
  initCharacter(config) {
    this.send("init_character", {
      llm_config: {
        protocol: config.llm_protocol,
        api_key: config.llm_api_key,
        model: config.llm_model,
        base_url: config.llm_base_url,
        temperature: config.llm_temperature || null,
        max_tokens: parseInt(config.llm_max_tokens, 10) || 1000,
        user_nickname: config.user_nickname,
      },
    });
  }

  /**
   * @param {string} content
   */
  sendText(content) {
    this.send("send_message", { content, metadata: {} });
  }

  /**
   * @param {number} afterTimestamp
   */
  syncMessages(afterTimestamp) {
    this.send("sync_messages", { after_timestamp: afterTimestamp });
  }

  clearSession() {
    this.send("clear_session", {});
  }

  /**
   * @param {number} untilTimestamp
   */
  markRead(untilTimestamp) {
    this.send("mark_read", { until_timestamp: untilTimestamp });
  }
}

// Temporary history WS removed; incremental sync uses HTTP.
