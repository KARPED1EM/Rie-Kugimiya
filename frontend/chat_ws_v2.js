class ChatApp {
    constructor() {
        this.config = null;
        this.sessionId = this.loadOrCreateSessionId();
        this.ws = null;
        this.isProcessing = false;
        this.messageRefs = new Map();
        this.localMessages = this.loadLocalMessages();
        this.lastSyncTimestamp = this.getLastSyncTimestamp();

        this.initElements();
        this.attachEventListeners();
        this.loadSavedConfig();
    }

    loadOrCreateSessionId() {
        const existing = localStorage.getItem('conversationId');
        if (existing) return existing;

        const uuid = this.createSessionId();
        localStorage.setItem('conversationId', uuid);
        return uuid;
    }

    createSessionId() {
        const fallback = `conv-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
        return (window.crypto && window.crypto.randomUUID)
            ? window.crypto.randomUUID()
            : fallback;
    }

    loadLocalMessages() {
        const key = `messages_${this.sessionId}`;
        const stored = localStorage.getItem(key);
        if (!stored) return new Map();

        try {
            const messages = JSON.parse(stored);
            return new Map(messages.map(msg => [msg.id, msg]));
        } catch (e) {
            console.error('Failed to load local messages:', e);
            return new Map();
        }
    }

    saveLocalMessages() {
        const key = `messages_${this.sessionId}`;
        const messages = Array.from(this.localMessages.values());
        localStorage.setItem(key, JSON.stringify(messages));
    }

    getLastSyncTimestamp() {
        if (this.localMessages.size === 0) return 0;

        let maxTimestamp = 0;
        for (const msg of this.localMessages.values()) {
            if (msg.timestamp > maxTimestamp) {
                maxTimestamp = msg.timestamp;
            }
        }
        return maxTimestamp;
    }

    initElements() {
        this.configPanel = document.getElementById('configPanel');
        this.providerSelect = document.getElementById('provider');
        this.apiKeyInput = document.getElementById('apiKey');
        this.baseUrlInput = document.getElementById('baseUrl');
        this.baseUrlGroup = document.getElementById('baseUrlGroup');
        this.modelInput = document.getElementById('model');
        this.personaInput = document.getElementById('personaInput');
        this.characterNameInput = document.getElementById('characterName');
        this.emotionThemeToggle = document.getElementById('emotionThemeToggle');
        this.saveConfigBtn = document.getElementById('saveConfig');

        this.chatContainer = document.getElementById('chatContainer');
        this.wechatShell = document.querySelector('.wechat-shell');
        this.chatTitle = document.getElementById('chatTitle');
        this.messagesDiv = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.toggleBtn = document.getElementById('toggleBtn');
        this.showConfigBtn = document.getElementById('showConfig');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusTime = document.getElementById('statusTime');
        this.plusBtn = document.querySelector('.plus-btn');

        this.defaultTitle = this.chatTitle.textContent || 'Rin';

        if (this.statusTime) {
            this.statusTime.textContent = this.getCurrentTime();
        }
    }

    attachEventListeners() {
        this.providerSelect.addEventListener('change', () => {
            const isCustom = this.providerSelect.value === 'custom';
            this.baseUrlGroup.style.display = isCustom ? 'block' : 'none';

            const defaults = {
                'deepseek': 'deepseek-chat',
                'openai': 'gpt-3.5-turbo',
                'anthropic': 'claude-3-5-sonnet-20241022',
                'custom': 'gpt-3.5-turbo'
            };
            this.modelInput.value = defaults[this.providerSelect.value];
        });

        this.saveConfigBtn.addEventListener('click', () => this.saveConfig());
        this.showConfigBtn.addEventListener('click', () => this.toggleView());

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                if (confirm('Clear all messages? This cannot be undone.')) {
                    this.clearConversation();
                }
            });
        }

        this.toggleBtn.addEventListener('click', () => {
            if (!this.toggleBtn.disabled) {
                this.sendMessage();
            }
        });

        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !this.isProcessing) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.userInput.addEventListener('input', () => this.updateComposerState());

        if (this.emotionThemeToggle) {
            this.emotionThemeToggle.addEventListener('change', () => {
                if (!this.emotionThemeToggle.checked) {
                    this.clearEmotionTheme();
                }
            });
        }

        window.addEventListener('beforeunload', () => {
            this.saveLocalMessages();
        });

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.saveLocalMessages();
            } else {
                this.syncMessages();
            }
        });
    }

    loadSavedConfig() {
        const saved = localStorage.getItem('chatConfig');
        if (saved) {
            try {
                const config = JSON.parse(saved);
                this.providerSelect.value = config.provider || 'openai';
                this.apiKeyInput.value = config.api_key || '';
                this.baseUrlInput.value = config.base_url || '';
                this.modelInput.value = config.model || 'gpt-3.5-turbo';
                this.personaInput.value = config.persona || '';
                this.characterNameInput.value = config.character_name || 'Rin';
                if (this.emotionThemeToggle) {
                    this.emotionThemeToggle.checked = config.enable_emotion_theme !== false;
                }

                this.providerSelect.dispatchEvent(new Event('change'));
            } catch (e) {
                console.error('Failed to load config:', e);
            }
        }
    }

    saveConfig() {
        const apiKey = this.apiKeyInput.value.trim();
        if (!apiKey) {
            alert('Please enter API key');
            return;
        }

        this.config = {
            provider: this.providerSelect.value,
            api_key: apiKey,
            base_url: this.baseUrlInput.value.trim() || null,
            model: this.modelInput.value.trim(),
            persona: this.personaInput.value.trim(),
            character_name: this.characterNameInput.value.trim() || 'Rin',
            enable_emotion_theme: this.emotionThemeToggle ? this.emotionThemeToggle.checked : false
        };

        localStorage.setItem('chatConfig', JSON.stringify(this.config));
        this.toggleView();
        this.enableChat();
        this.connectWebSocket();
    }

    toggleView() {
        const showChat = this.configPanel.style.display !== 'none';
        this.configPanel.style.display = showChat ? 'none' : 'block';
        this.chatContainer.style.display = showChat ? 'flex' : 'none';

        if (showChat && this.config) {
            this.defaultTitle = this.config.character_name || 'Rin';
            this.chatTitle.textContent = this.defaultTitle;
            this.renderLocalMessages();
        }
    }

    enableChat() {
        this.userInput.disabled = false;
        this.toggleBtn.disabled = true;
        this.userInput.focus();
        this.updateComposerState();
    }

    renderLocalMessages() {
        this.messagesDiv.innerHTML = '';
        this.messageRefs.clear();

        const messages = Array.from(this.localMessages.values())
            .sort((a, b) => a.timestamp - b.timestamp);

        for (const msg of messages) {
            if (msg.type === 'text') {
                const role = msg.sender_id === 'user' ? 'user' : 'assistant';
                const messageDiv = this.addMessage(role, msg.content, {
                    messageId: msg.id,
                    emotion: msg.metadata?.emotion,
                    skipSave: true
                });
                this.messageRefs.set(msg.id, messageDiv);
            } else if (msg.type === 'recall_event') {
                // 撤回事件在历史消息中，直接删除被撤回的消息
                const targetId = msg.metadata?.target_message_id;
                if (targetId && this.localMessages.has(targetId)) {
                    this.localMessages.delete(targetId);
                }
                // 显示撤回提示（可选，取决于是否想在历史加载时显示）
                // this.showRecallNotice(true);
            }
        }
    }

    connectWebSocket() {
        if (this.ws) {
            this.ws.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/${this.sessionId}?user_id=user`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.syncMessages();
            this.sendInitRin();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addMessage('system', 'Connection error. Reconnecting...', { skipSave: true });
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed');
            setTimeout(() => {
                if (this.config && this.chatContainer.style.display !== 'none') {
                    this.connectWebSocket();
                }
            }, 3000);
        };
    }

    syncMessages() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        this.ws.send(JSON.stringify({
            type: 'sync',
            after_timestamp: this.lastSyncTimestamp
        }));
    }

    sendInitRin() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        this.ws.send(JSON.stringify({
            type: 'init_rin',
            llm_config: this.config
        }));
    }

    handleWebSocketMessage(data) {
        const type = data.type;

        if (type === 'history') {
            this.handleHistory(data.data);
        } else if (type === 'message') {
            this.handleMessage(data.data);
        } else if (type === 'typing') {
            this.handleTyping(data.data);
        } else if (type === 'clear') {
            this.handleClear(data.data);
        }
        // 注意：不再单独处理'recall'类型，撤回事件现在作为type='recall_event'的消息
    }

    handleHistory(data) {
        const messages = data.messages || [];
        let hasNewMessages = false;

        for (const msg of messages) {
            if (!this.localMessages.has(msg.id)) {
                this.localMessages.set(msg.id, msg);
                hasNewMessages = true;

                if (msg.timestamp > this.lastSyncTimestamp) {
                    this.lastSyncTimestamp = msg.timestamp;
                }
            }
        }

        if (hasNewMessages) {
            this.saveLocalMessages();
            this.renderLocalMessages();
        }
    }

    handleMessage(data) {
        if (this.localMessages.has(data.id)) {
            return;
        }

        this.localMessages.set(data.id, data);
        this.saveLocalMessages();

        if (data.timestamp > this.lastSyncTimestamp) {
            this.lastSyncTimestamp = data.timestamp;
        }

        // 处理撤回事件消息
        if (data.type === 'recall_event') {
            this.handleRecallEvent(data);
            return;
        }

        // 处理普通文本消息
        const role = data.sender_id === 'user' ? 'user' : 'assistant';
        const messageDiv = this.addMessage(role, data.content, {
            messageId: data.id,
            emotion: data.metadata?.emotion,
            skipSave: true
        });

        if (data.id) {
            this.messageRefs.set(data.id, messageDiv);
        }

        if (role === 'assistant' && this.emotionThemeToggle?.checked) {
            this.applyEmotionFromMetadata(data.metadata);
        }
    }

    handleTyping(data) {
        if (data.user_id === 'rin') {
            this.setTypingStatus(data.is_typing);
        }
    }

    handleRecallEvent(recallEventMsg) {
        /**
         * 处理撤回事件消息
         * recallEventMsg格式：
         * {
         *   id: "recall-xxx",
         *   type: "recall_event",
         *   metadata: {
         *     target_message_id: "msg-123",
         *     recalled_by: "rin",
         *     original_sender: "rin"
         *   }
         * }
         */
        const targetMessageId = recallEventMsg.metadata?.target_message_id;
        if (!targetMessageId) {
            console.warn('Recall event missing target_message_id');
            return;
        }

        // 从localMessages中删除原消息（或标记为已撤回）
        if (this.localMessages.has(targetMessageId)) {
            this.localMessages.delete(targetMessageId);
            this.saveLocalMessages();
        }

        // 从UI中移除原消息
        if (this.messageRefs.has(targetMessageId)) {
            const messageDiv = this.messageRefs.get(targetMessageId);
            if (messageDiv) {
                messageDiv.remove();
            }
            this.messageRefs.delete(targetMessageId);
        }

        // 显示撤回提示
        this.showRecallNotice();
    }

    handleClear(data) {
        this.localMessages.clear();
        this.messageRefs.clear();
        this.messagesDiv.innerHTML = '';
        this.lastSyncTimestamp = 0;
        this.saveLocalMessages();
    }

    addMessage(role, content, options = {}) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;

        if (role === 'system') {
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = content;
            row.appendChild(bubble);
        } else {
            const avatar = document.createElement('img');
            avatar.className = 'avatar';
            avatar.src = role === 'user'
                ? '/static/assets/avatar_user.png'
                : '/static/assets/avatar_rin.png';
            avatar.alt = role === 'user' ? 'Me' : 'Rin';

            const bubble = document.createElement('div');
            bubble.className = `bubble ${role}`;
            bubble.textContent = content;

            if (options.emotion) {
                bubble.dataset.emotion = options.emotion;
            }

            row.appendChild(avatar);
            row.appendChild(bubble);
        }

        if (options.messageId) {
            row.dataset.messageId = options.messageId;
        }

        this.messagesDiv.appendChild(row);
        this.scrollToBottom();
        return row;
    }

    scrollToBottom() {
        this.messagesDiv.scrollTop = this.messagesDiv.scrollHeight;
    }

    sendMessage() {
        const text = this.userInput.value.trim();
        if (!text || this.isProcessing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        this.isProcessing = true;
        this.userInput.value = '';
        this.updateComposerState();

        const messageId = `msg-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
        const timestamp = Date.now() / 1000;

        const localMsg = {
            id: messageId,
            conversation_id: this.sessionId,
            sender_id: 'user',
            type: 'text',
            content: text,
            timestamp: timestamp,
            metadata: {}
        };

        this.localMessages.set(messageId, localMsg);
        this.saveLocalMessages();

        if (timestamp > this.lastSyncTimestamp) {
            this.lastSyncTimestamp = timestamp;
        }

        const messageDiv = this.addMessage('user', text, {
            messageId: messageId,
            skipSave: true
        });
        this.messageRefs.set(messageId, messageDiv);

        this.ws.send(JSON.stringify({
            type: 'message',
            id: messageId,
            content: text,
            metadata: {}
        }));

        this.isProcessing = false;
        this.userInput.focus();
    }

    clearConversation() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        this.ws.send(JSON.stringify({
            type: 'clear'
        }));
    }

    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    }

    updateComposerState() {
        const hasText = this.userInput.value.trim().length > 0;
        if (hasText) {
            this.plusBtn.classList.add('hidden');
            this.toggleBtn.classList.remove('hidden');
            this.toggleBtn.disabled = false;
        } else {
            this.plusBtn.classList.remove('hidden');
            this.toggleBtn.classList.add('hidden');
            this.toggleBtn.disabled = true;
        }
    }

    setTypingStatus(active) {
        if (!this.chatTitle) return;
        this.chatTitle.textContent = active ? "对方正在输入中..." : (this.defaultTitle || 'Rin');
    }

    showRecallNotice(skipSave = false) {
        const name = this.config?.character_name || 'Rin';
        const text = `"${name}" 撤回了一条消息`;
        this.addMessage('system', text, { skipSave });
    }

    applyEmotionFromMetadata(metadata) {
        if (!metadata || !this.emotionThemeToggle?.checked) {
            this.clearEmotionTheme();
            return;
        }

        const emotionMap = metadata.emotion_map || metadata.emotionMap;
        if (!emotionMap) {
            this.clearEmotionTheme();
            return;
        }

        this.wechatShell.classList.add('glow-enabled');
    }

    clearEmotionTheme() {
        if (!this.wechatShell) return;
        this.wechatShell.classList.remove('glow-enabled');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
