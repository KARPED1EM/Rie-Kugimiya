class ChatApp {
    constructor() {
        this.config = null;
        this.sessionId = this.loadOrCreateSessionId();
        this.ws = null;
        this.isProcessing = false;
        this.messageRefs = new Map();
        this.localMessages = this.loadLocalMessages();
        this.lastSyncTimestamp = this.getLastSyncTimestamp();
        this.defaults = null;
        this.emotionState = this.loadEmotionState();
        this.newMessageCount = 0;
        this.isUserNearBottom = true;
        this.isMenuOpen = false;
        this.isShuttingDown = false;

        this.initElements();
        this.attachEventListeners();
        this.initializeConfig();
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

    getEmotionStateKey() {
        return `emotion_state_${this.sessionId}`;
    }

    loadEmotionState() {
        const stored = localStorage.getItem(this.getEmotionStateKey());
        if (!stored) return null;

        try {
            const parsed = JSON.parse(stored);
            if (!parsed || !parsed.emotionMap) return null;
            return parsed;
        } catch (e) {
            console.error('Failed to load emotion state:', e);
            return null;
        }
    }

    saveEmotionState(state) {
        if (!state) return;
        this.emotionState = state;
        localStorage.setItem(this.getEmotionStateKey(), JSON.stringify(state));
    }

    clearEmotionState() {
        this.emotionState = null;
        localStorage.removeItem(this.getEmotionStateKey());
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
        this.appContainer = document.querySelector('.app-container');
        this.configPanel = document.getElementById('configPanel');
        this.providerSelect = document.getElementById('provider');
        this.apiKeyInput = document.getElementById('apiKey');
        this.baseUrlInput = document.getElementById('baseUrl');
        this.baseUrlGroup = document.getElementById('baseUrlGroup');
        this.modelInput = document.getElementById('model');
        this.personaInput = document.getElementById('personaInput');
        this.characterNameInput = document.getElementById('characterName');
        this.userNicknameInput = document.getElementById('userNickname');
        this.emotionThemeToggle = document.getElementById('emotionThemeToggle');
        this.debugModeToggle = document.getElementById('debugModeToggle');
        this.saveConfigBtn = document.getElementById('saveConfig');
        this.avatarPreview = document.getElementById('avatarPreview');
        this.avatarInput = document.getElementById('avatarInput');
        this.uploadAvatarBtn = document.getElementById('uploadAvatarBtn');
        this.deleteAvatarBtn = document.getElementById('deleteAvatarBtn');

        this.phoneContainer = document.querySelector('.phone-container');
        this.wechatShell = document.getElementById('wechatShell');
        this.chatTitle = document.getElementById('chatTitle');
        this.messagesDiv = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.toggleBtn = document.getElementById('toggleBtn');
        this.showConfigBtn = document.getElementById('showConfig');
        this.menuButton = document.getElementById('menuButton');
        this.menuPopover = document.getElementById('menuPopover');
        this.menuWrapper = document.querySelector('.menu-wrapper');
        this.statusTime = document.getElementById('statusTime');
        this.statusClock = document.getElementById('statusClock');
        this.statusAmPm = document.getElementById('statusAmPm');
        this.plusBtn = document.querySelector('.plus-btn');
        this.debugLogPanel = document.getElementById('debugLogPanel');
        this.debugLogContent = document.getElementById('debugLogContent');
        this.newMessageBtn = document.getElementById('newMessageBtn');
        this.newMessageText = document.getElementById('newMessageText');

        this.defaultTitle = this.chatTitle.textContent || 'Rin';
        this.debugMode = false;

        if (this.statusTime) {
            this.startStatusClock();
        }
    }

    attachEventListeners() {
        this.providerSelect.addEventListener('change', () => {
            const isCustom = this.providerSelect.value === 'custom';
            this.baseUrlGroup.style.display = isCustom ? 'block' : 'none';

            // Use backend defaults if available
            if (this.defaults && this.defaults.llm) {
                const provider = this.providerSelect.value;
                if (provider === 'deepseek') {
                    this.modelInput.value = this.defaults.llm.model_deepseek;
                } else if (provider === 'openai') {
                    this.modelInput.value = this.defaults.llm.model_openai;
                } else if (provider === 'anthropic') {
                    this.modelInput.value = this.defaults.llm.model_anthropic;
                } else if (provider === 'custom') {
                    this.modelInput.value = this.defaults.llm.model_custom;
                }
            }
        });

        this.saveConfigBtn.addEventListener('click', () => this.saveConfig());
        this.showConfigBtn.addEventListener('click', () => this.toggleView());

        if (this.menuButton) {
            this.menuButton.addEventListener('click', (event) => {
                event.stopPropagation();
                this.toggleMenu();
            });
        }

        if (this.menuPopover) {
            this.menuPopover.addEventListener('click', (event) => {
                const actionButton = event.target.closest('[data-action]');
                if (!actionButton) return;
                event.stopPropagation();
                this.handleMenuAction(actionButton.dataset.action);
            });
        }

        document.addEventListener('click', (event) => {
            if (!this.isMenuOpen) return;
            if (this.menuWrapper && !this.menuWrapper.contains(event.target)) {
                this.closeMenu();
            }
        });

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

        this.userInput.addEventListener('input', () => {
            this.updateComposerState();

            // Delay height calculation slightly to let browser finish layout after button width changes
            // Button widths now change instantly (no transition), but we need to wait for DOM layout
            requestAnimationFrame(() => {
                this.adjustTextareaHeight();
            });
        });

        if (this.emotionThemeToggle) {
            this.emotionThemeToggle.addEventListener('change', () => {
                if (this.emotionThemeToggle.checked) {
                    this.restoreEmotionTheme();
                } else {
                    this.clearEmotionTheme();
                }
            });
        }

        if (this.debugModeToggle) {
            this.debugModeToggle.addEventListener('change', () => {
                this.toggleDebugMode(this.debugModeToggle.checked);
            });
        }

        if (this.uploadAvatarBtn && this.avatarInput) {
            this.uploadAvatarBtn.addEventListener('click', () => {
                this.avatarInput.click();
            });

            this.avatarInput.addEventListener('change', (e) => {
                this.handleAvatarUpload(e);
            });
        }

        if (this.deleteAvatarBtn) {
            this.deleteAvatarBtn.addEventListener('click', () => {
                this.handleAvatarDelete();
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

        this.messagesDiv.addEventListener('scroll', () => this.handleMessagesScroll());

        if (this.newMessageBtn) {
            this.newMessageBtn.addEventListener('click', () => {
                this.scrollToBottom({ smooth: true });
                this.resetNewMessageIndicator();
            });
        }
    }

    toggleMenu() {
        if (this.isMenuOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }

    openMenu() {
        if (!this.menuPopover) return;
        this.menuPopover.classList.add('open');
        this.menuPopover.setAttribute('aria-hidden', 'false');
        if (this.menuButton) {
            this.menuButton.setAttribute('aria-expanded', 'true');
        }
        this.isMenuOpen = true;
    }

    closeMenu() {
        if (!this.menuPopover) return;
        this.menuPopover.classList.remove('open');
        this.menuPopover.setAttribute('aria-hidden', 'true');
        if (this.menuButton) {
            this.menuButton.setAttribute('aria-expanded', 'false');
        }
        this.isMenuOpen = false;
    }

    handleMenuAction(action) {
        if (action === 'clear') {
            this.closeMenu();
            this.triggerClearConversation();
        } else if (action === 'terminate') {
            this.closeMenu();
            this.triggerShutdown();
        }
    }

    triggerClearConversation() {
        const canNotifyServer = this.ws && this.ws.readyState === WebSocket.OPEN;
        if (canNotifyServer) {
            this.clearConversation();
        } else {
            this.addMessage('system', '未连接服务器，暂时无法清空对话。', { skipIndicator: true });
        }
    }

    async triggerShutdown() {
        if (this.isShuttingDown) return;

        this.isShuttingDown = true;
        this.addMessage('system', '终止指令已发送，服务即将关闭...', { skipIndicator: true });

        try {
            const response = await fetch('/api/shutdown', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Shutdown request failed:', error);
            this.isShuttingDown = false;
            this.addMessage('system', '终止失败，请检查服务状态。', { skipIndicator: true });
            return;
        }

        if (this.userInput) {
            this.userInput.disabled = true;
        }
        if (this.toggleBtn) {
            this.toggleBtn.disabled = true;
        }
        if (this.ws) {
            try {
                this.ws.close();
            } catch (e) {
                // No-op if close fails
            }
        }
    }

    async initializeConfig() {
        try {
            // Fetch defaults from backend
            const response = await fetch('/api/config/defaults');
            if (response.ok) {
                this.defaults = await response.json();
            } else {
                console.error('Failed to fetch defaults:', response.statusText);
                // Fallback defaults if API fails
                this.defaults = {
                    llm: {
                        provider: 'deepseek',
                        model_deepseek: 'deepseek-chat',
                        model_openai: 'gpt-3.5-turbo',
                        model_anthropic: 'claude-3-5-sonnet-20241022',
                        model_custom: 'gpt-3.5-turbo'
                    },
                    character: {
                        name: 'Rin',
                        persona: ''
                    },
                    ui: {
                        enable_emotion_theme: true
                    }
                };
            }
        } catch (e) {
            console.error('Error fetching defaults:', e);
            this.defaults = {
                llm: { provider: 'deepseek', model_deepseek: 'deepseek-chat' },
                character: { name: 'Rin', persona: '' },
                ui: { enable_emotion_theme: true }
            };
        }

        // Load saved config or apply defaults
        this.loadSavedConfig();

        // Load user avatar
        this.loadUserAvatar();
    }

    async loadSavedConfig() {
        try {
            // Load config from backend database (single source of truth)
            const response = await fetch('/api/config');
            if (response.ok) {
                const config = await response.json();
                this.applyConfig(config);
            } else {
                console.error('Failed to load config from backend');
                this.applyDefaults();
            }
        } catch (e) {
            console.error('Failed to load config:', e);
            this.applyDefaults();
        }
    }

    applyDefaults() {
        if (!this.defaults) return;

        this.providerSelect.value = this.defaults.llm.provider;
        this.apiKeyInput.value = '';
        this.baseUrlInput.value = '';

        // Set model based on provider
        const provider = this.defaults.llm.provider;
        if (provider === 'deepseek') {
            this.modelInput.value = this.defaults.llm.model_deepseek;
        } else if (provider === 'openai') {
            this.modelInput.value = this.defaults.llm.model_openai;
        } else if (provider === 'anthropic') {
            this.modelInput.value = this.defaults.llm.model_anthropic;
        } else if (provider === 'custom') {
            this.modelInput.value = this.defaults.llm.model_custom;
        }

        this.personaInput.value = this.defaults.character.persona;
        this.characterNameInput.value = this.defaults.character.name;
        this.userNicknameInput.value = '鲨鲨';

        if (this.emotionThemeToggle) {
            this.emotionThemeToggle.checked = this.defaults.ui.enable_emotion_theme;
        }

        this.providerSelect.dispatchEvent(new Event('change'));
    }

    applyConfig(config) {
        this.providerSelect.value = config.provider || (this.defaults?.llm.provider || 'deepseek');
        this.apiKeyInput.value = config.api_key || '';
        this.baseUrlInput.value = config.base_url || '';
        this.modelInput.value = config.model || (this.defaults?.llm.model_deepseek || 'deepseek-chat');
        this.personaInput.value = config.persona || (this.defaults?.character.persona || '');
        this.characterNameInput.value = config.character_name || (this.defaults?.character.name || 'Rin');
        this.userNicknameInput.value = config.user_nickname || '鲨鲨';

        if (this.emotionThemeToggle) {
            this.emotionThemeToggle.checked = config.enable_emotion_theme !== false;
        }

        if (this.debugModeToggle) {
            this.debugModeToggle.checked = config.debug_mode || false;
            // Apply debug mode UI immediately if enabled
            if (config.debug_mode) {
                this.toggleDebugMode(true);
            }
        }

        this.providerSelect.dispatchEvent(new Event('change'));
    }

    async saveConfig() {
        const apiKey = this.apiKeyInput.value.trim();
        if (!apiKey) {
            alert('Please enter API key');
            return;
        }

        const config = {
            provider: this.providerSelect.value,
            api_key: apiKey,
            base_url: this.baseUrlInput.value.trim() || null,
            model: this.modelInput.value.trim(),
            persona: this.personaInput.value.trim(),
            character_name: this.characterNameInput.value.trim() || 'Rin',
            user_nickname: this.userNicknameInput.value.trim() || '鲨鲨',
            enable_emotion_theme: this.emotionThemeToggle ? this.emotionThemeToggle.checked : false,
            debug_mode: this.debugModeToggle ? this.debugModeToggle.checked : false
        };

        try {
            // Save to backend database (single source of truth)
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error('Failed to save config');
            }

            // Keep in memory for this session
            this.config = config;

            this.toggleView();
            this.enableChat();
            this.connectWebSocket();
        } catch (error) {
            console.error('Error saving config:', error);
            alert('Failed to save configuration. Please try again.');
        }
    }

    toggleView() {
        const showChat = this.configPanel.style.display !== 'none';
        // Keep the config panel as a flex container so its content stays centered
        this.configPanel.style.display = showChat ? 'none' : 'flex';
        this.wechatShell.style.display = showChat ? 'block' : 'none';

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

        let lastTimestamp = null;

        for (const msg of messages) {
            if (msg.type === 'text') {
                // Check if we need to insert a time hint
                // First message always shows time hint, others check time difference
                if (lastTimestamp === null) {
                    // First message - always show time hint
                    const timeStr = this.formatTimestamp(msg.timestamp);
                    this.addMessage('system', timeStr, {
                        skipSave: true,
                        skipIndicator: true
                    });
                } else {
                    // Subsequent messages - check time difference
                    const timeDiff = msg.timestamp - lastTimestamp;
                    if (timeDiff > 5 * 60) { // 5 minutes in seconds
                        const timeStr = this.formatTimestamp(msg.timestamp);
                        this.addMessage('system', timeStr, {
                            skipSave: true,
                            skipIndicator: true
                        });
                    }
                }

                // Determine role based on sender_id
                let role;
                if (msg.sender_id === 'user') {
                    role = 'user';
                } else if (msg.sender_id === 'system') {
                    role = 'system';
                } else {
                    role = 'assistant';
                }

                const messageDiv = this.addMessage(role, msg.content, {
                    messageId: msg.id,
                    emotion: msg.metadata?.emotion,
                    skipSave: true,
                    skipIndicator: true
                });
                this.messageRefs.set(msg.id, messageDiv);
                lastTimestamp = msg.timestamp;
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

        this.restoreEmotionTheme();
        this.resetNewMessageIndicator();
        this.scrollToBottom();
    }

    connectWebSocket() {
        if (this.ws) {
            this.ws.close();
        }

        // For local development, always use localhost instead of 0.0.0.0
        let host = window.location.host;
        if (host.startsWith('0.0.0.0:')) {
            host = host.replace('0.0.0.0:', 'localhost:');
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${host}/api/ws/${this.sessionId}?user_id=user`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.syncMessages();
            this.sendInitRin();

            // Send debug mode state if enabled
            if (this.config && this.config.debug_mode) {
                console.log('Sending initial debug_mode=true to backend');
                this.ws.send(JSON.stringify({
                    type: 'debug_mode',
                    enabled: true
                }));
            } else {
                console.log('Debug mode not enabled in config');
            }
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
            if (this.isShuttingDown) {
                return;
            }
            setTimeout(() => {
                if (this.config && this.wechatShell.style.display !== 'none') {
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
        } else if (type === 'debug_log') {
            this.handleDebugLog(data.data);
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

        // 处理撤回事件消息
        if (data.type === 'recall_event') {
            this.localMessages.set(data.id, data);
            this.saveLocalMessages();
            if (data.timestamp > this.lastSyncTimestamp) {
                this.lastSyncTimestamp = data.timestamp;
            }
            this.handleRecallEvent(data);
            return;
        }

        // Check if we need to insert a time hint BEFORE saving the message
        const lastMessageTimestamp = this.getLastVisibleMessageTimestamp();
        if (lastMessageTimestamp === null) {
            // First message - always show time hint
            const timeStr = this.formatTimestamp(data.timestamp);
            this.addMessage('system', timeStr, {
                skipSave: true,
                skipIndicator: true
            });
        } else if (lastMessageTimestamp !== data.timestamp) {
            // Subsequent messages - check time difference
            const timeDiff = data.timestamp - lastMessageTimestamp;
            if (timeDiff > 5 * 60) { // 5 minutes in seconds
                const timeStr = this.formatTimestamp(data.timestamp);
                this.addMessage('system', timeStr, {
                    skipSave: true,
                    skipIndicator: true
                });
            }
        }

        // Now save the message after checking time hints
        this.localMessages.set(data.id, data);
        this.saveLocalMessages();

        if (data.timestamp > this.lastSyncTimestamp) {
            this.lastSyncTimestamp = data.timestamp;
        }

        // 处理普通文本消息
        // Determine role based on sender_id
        let role;
        if (data.sender_id === 'user') {
            role = 'user';
        } else if (data.sender_id === 'system') {
            role = 'system';
        } else {
            role = 'assistant';
        }

        const messageDiv = this.addMessage(role, data.content, {
            messageId: data.id,
            emotion: data.metadata?.emotion,
            skipSave: true
        });

        if (data.id) {
            this.messageRefs.set(data.id, messageDiv);
        }

        if (role === 'assistant') {
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
        this.clearEmotionTheme({ resetState: true });
        this.resetNewMessageIndicator();
    }

    addMessage(role, content, options = {}) {
        const shouldStickToBottom = this.isNearBottom();
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
            // Use custom avatar if available, otherwise use default
            if (role === 'user') {
                avatar.src = this.userAvatarData || '/static/assets/avatar_user.png';
            } else {
                avatar.src = '/static/assets/avatar_rin.png';
            }
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
        this.handleAfterMessageAdded({
            role,
            shouldStickToBottom,
            skipIndicator: options.skipIndicator
        });
        return row;
    }

    handleAfterMessageAdded({ role, shouldStickToBottom, skipIndicator }) {
        if (shouldStickToBottom) {
            this.scrollToBottom();
            return;
        }

        this.isUserNearBottom = false;

        if (!skipIndicator && role !== 'user') {
            this.bumpNewMessageIndicator();
        }
    }

    scrollToBottom(options = {}) {
        if (!this.messagesDiv) return;

        const behavior = options.smooth ? 'smooth' : 'auto';
        this.messagesDiv.scrollTo({
            top: this.messagesDiv.scrollHeight,
            behavior
        });
        this.isUserNearBottom = true;
        this.resetNewMessageIndicator();
    }

    isNearBottom(threshold = 36) {
        if (!this.messagesDiv) return true;

        const distance = this.messagesDiv.scrollHeight - (this.messagesDiv.scrollTop + this.messagesDiv.clientHeight);
        return distance <= threshold;
    }

    handleMessagesScroll() {
        if (this.isMenuOpen) {
            this.closeMenu();
        }

        const nearBottom = this.isNearBottom();
        this.isUserNearBottom = nearBottom;

        if (nearBottom) {
            this.resetNewMessageIndicator();
        }
    }

    bumpNewMessageIndicator() {
        if (!this.newMessageBtn || !this.newMessageText) return;

        this.newMessageCount += 1;
        this.newMessageText.textContent = `${this.newMessageCount} 条新消息`;
        this.newMessageBtn.classList.add('show');
    }

    resetNewMessageIndicator() {
        this.newMessageCount = 0;
        if (this.newMessageBtn) {
            this.newMessageBtn.classList.remove('show');
        }
    }

    sendMessage() {
        const text = this.userInput.value.trim();
        if (!text || this.isProcessing || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        this.isProcessing = true;
        this.userInput.value = '';
        this.adjustTextareaHeight(); // Reset height after clearing
        this.updateComposerState();

        const messageId = `msg-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
        const timestamp = Date.now() / 1000;

        // Check if we need to insert a time hint before the user's message
        const lastMessageTimestamp = this.getLastVisibleMessageTimestamp();
        if (lastMessageTimestamp === null) {
            // First message - always show time hint
            const timeStr = this.formatTimestamp(timestamp);
            this.addMessage('system', timeStr, {
                skipSave: true,
                skipIndicator: true
            });
        } else {
            // Subsequent messages - check time difference
            const timeDiff = timestamp - lastMessageTimestamp;
            if (timeDiff > 5 * 60) { // 5 minutes in seconds
                const timeStr = this.formatTimestamp(timestamp);
                this.addMessage('system', timeStr, {
                    skipSave: true,
                    skipIndicator: true
                });
            }
        }

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

    adjustTextareaHeight() {
        // Reset height to auto to get the correct scrollHeight
        this.userInput.style.height = 'auto';
        
        // Calculate the new height based on content
        const scrollHeight = this.userInput.scrollHeight;
        const maxHeight = 120; // Maximum height in pixels (about 6 lines)
        
        // Set the height to fit content, but cap at maxHeight
        if (scrollHeight > maxHeight) {
            this.userInput.style.height = maxHeight + 'px';
            this.userInput.style.overflowY = 'auto';
        } else {
            this.userInput.style.height = scrollHeight + 'px';
            this.userInput.style.overflowY = 'hidden';
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
        if (!metadata) {
            this.clearEmotionTheme({ resetState: true });
            return;
        }

        const emotionMap = metadata.emotion_map || metadata.emotionMap;
        if (!emotionMap || Object.keys(emotionMap).length === 0) {
            this.clearEmotionTheme({ resetState: true });
            return;
        }

        // Calculate mixed color based on all emotions and their intensities
        const mixedColor = this.mixEmotionColors(emotionMap);

        // Persist the last known emotion so it survives refreshes
        this.saveEmotionState({
            emotionMap,
            colors: mixedColor,
            updatedAt: Date.now()
        });

        // Only apply glow when the toggle is enabled
        if (!this.emotionThemeToggle?.checked) {
            return;
        }

        this.applyGlowColors(mixedColor);
    }

    applyGlowColors(colorSet) {
        if (!this.wechatShell || !colorSet) return;

        this.wechatShell.style.setProperty('--glow-base', colorSet.base);
        this.wechatShell.style.setProperty('--glow-shadow', colorSet.shadow);
        this.wechatShell.style.setProperty('--glow-shadow-soft', colorSet.shadowSoft);
        this.wechatShell.classList.add('glow-enabled');
    }

    mixEmotionColors(emotionMap) {
        // Define color mapping for emotions
        const emotionColors = {
            'neutral': { r: 26, g: 173, b: 25 },      // Green (default)
            'happy': { r: 255, g: 215, b: 0 },        // Gold
            'excited': { r: 255, g: 140, b: 0 },      // Orange
            'sad': { r: 100, g: 149, b: 237 },        // Cornflower blue
            'angry': { r: 220, g: 20, b: 60 },        // Crimson
            'anxious': { r: 186, g: 85, b: 211 },     // Medium orchid
            'confused': { r: 169, g: 169, b: 169 },   // Dark gray
            'mad': { r: 220, g: 20, b: 60 },          // Crimson (same as angry)
            'playful': { r: 255, g: 105, b: 180 },    // Hot pink
            'affectionate': { r: 255, g: 182, b: 193 }, // Light pink
            'nervous': { r: 186, g: 85, b: 211 },     // Medium orchid (same as anxious)
            'shy': { r: 255, g: 192, b: 203 },        // Pink
            'embarrassed': { r: 255, g: 160, b: 122 }, // Light salmon
            'surprised': { r: 255, g: 215, b: 0 },    // Gold (same as happy)
            'tired': { r: 119, g: 136, b: 153 },      // Light slate gray
            'bored': { r: 128, g: 128, b: 128 },      // Gray
            'serious': { r: 70, g: 130, b: 180 },     // Steel blue
            'caring': { r: 255, g: 218, b: 185 }      // Peach puff
        };

        // Intensity weights
        const intensityWeights = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.9,
            'extreme': 1.2
        };

        let totalR = 0, totalG = 0, totalB = 0, totalWeight = 0;

        // Mix colors based on emotion intensities
        for (const [emotion, intensity] of Object.entries(emotionMap)) {
            const emotionKey = emotion.toLowerCase().trim();
            const intensityKey = intensity.toLowerCase().trim();
            
            const color = emotionColors[emotionKey];
            const weight = intensityWeights[intensityKey] || 0.5;

            if (color) {
                totalR += color.r * weight;
                totalG += color.g * weight;
                totalB += color.b * weight;
                totalWeight += weight;
            }
        }

        // Calculate average color
        if (totalWeight === 0) {
            // Fallback to default green
            return {
                base: 'rgb(26, 173, 25)',
                shadow: 'rgba(26, 173, 25, 0.35)',
                shadowSoft: 'rgba(26, 173, 25, 0.22)'
            };
        }

        const r = Math.round(totalR / totalWeight);
        const g = Math.round(totalG / totalWeight);
        const b = Math.round(totalB / totalWeight);

        return {
            base: `rgb(${r}, ${g}, ${b})`,
            shadow: `rgba(${r}, ${g}, ${b}, 0.35)`,
            shadowSoft: `rgba(${r}, ${g}, ${b}, 0.22)`
        };
    }

    getLastEmotionFromMessages() {
        const messages = Array.from(this.localMessages.values())
            .sort((a, b) => b.timestamp - a.timestamp);

        for (const msg of messages) {
            const emotionMap = msg.metadata?.emotion_map || msg.metadata?.emotionMap;
            if (emotionMap && Object.keys(emotionMap).length > 0) {
                return {
                    emotionMap,
                    updatedAt: msg.timestamp ? msg.timestamp * 1000 : Date.now()
                };
            }
        }

        return null;
    }

    restoreEmotionTheme() {
        if (!this.emotionThemeToggle?.checked) return;

        if (!this.emotionState) {
            this.emotionState = this.loadEmotionState();
        }

        let state = this.emotionState;

        if (!state || !state.emotionMap) {
            const fromMessages = this.getLastEmotionFromMessages();
            if (fromMessages) {
                const colors = this.mixEmotionColors(fromMessages.emotionMap);
                state = {
                    emotionMap: fromMessages.emotionMap,
                    colors,
                    updatedAt: fromMessages.updatedAt || Date.now()
                };
                this.saveEmotionState(state);
            }
        }

        if (!state || !state.colors) return;

        this.applyGlowColors(state.colors);
    }

    clearEmotionTheme(options = {}) {
        if (!this.wechatShell) return;
        this.wechatShell.classList.remove('glow-enabled');
        this.wechatShell.style.removeProperty('--glow-base');
        this.wechatShell.style.removeProperty('--glow-shadow');
        this.wechatShell.style.removeProperty('--glow-shadow-soft');

        if (options.resetState) {
            this.clearEmotionState();
        }
    }

    startStatusClock() {
        this.updateStatusTime();

        if (this.timeInterval) {
            clearInterval(this.timeInterval);
        }

        const now = new Date();
        const msToNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds();

        setTimeout(() => {
            this.updateStatusTime();
            this.timeInterval = setInterval(() => this.updateStatusTime(), 60000);
        }, Math.max(msToNextMinute, 500));
    }

    updateStatusTime() {
        const { ampm, clock } = this.getCurrentTimeParts();

        if (this.statusClock && this.statusAmPm) {
            this.statusAmPm.textContent = ampm;
            this.statusClock.textContent = clock;
        } else if (this.statusTime) {
            this.statusTime.textContent = `${ampm} ${clock}`;
        }
    }

    getCurrentTimeParts() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? '下午' : '上午';
        hours = hours % 12 || 12;
        return { ampm, clock: `${hours}:${minutes}` };
    }

    toggleDebugMode(enabled) {
        this.debugMode = enabled;

        if (enabled) {
            this.appContainer.classList.add('debug-mode');
            console.log('Debug mode enabled on frontend');
        } else {
            this.appContainer.classList.remove('debug-mode');
            console.log('Debug mode disabled on frontend');
        }

        // Notify backend if WebSocket is connected
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('Sending debug_mode message to backend:', enabled);
            this.ws.send(JSON.stringify({
                type: 'debug_mode',
                enabled: enabled
            }));
        } else {
            console.log('WebSocket not ready, debug mode will be sent when connected');
        }
    }

    handleDebugLog(logEntry) {
        console.log('Received debug log:', logEntry);

        if (!this.debugMode) {
            console.log('Debug mode is off, ignoring log');
            return;
        }

        const logDiv = document.createElement('div');
        logDiv.className = `debug-log-entry level-${logEntry.level}`;

        const timestamp = new Date(logEntry.timestamp * 1000);
        const timeStr = timestamp.toLocaleTimeString('zh-CN', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });

        const timeSpan = document.createElement('span');
        timeSpan.className = 'log-time';
        timeSpan.textContent = timeStr;

        const categorySpan = document.createElement('span');
        categorySpan.className = 'log-category';
        categorySpan.textContent = `[${logEntry.category}]`;

        const messageSpan = document.createElement('span');
        messageSpan.className = 'log-message';
        messageSpan.textContent = logEntry.message;

        logDiv.appendChild(timeSpan);
        logDiv.appendChild(categorySpan);
        logDiv.appendChild(messageSpan);

        // Add metadata if present and useful
        if (logEntry.metadata && Object.keys(logEntry.metadata).length > 0) {
            // Show compact metadata for specific categories
            if (logEntry.category === 'llm') {
                // Show full response
                if (logEntry.metadata.response) {
                    const metaDiv = document.createElement('div');
                    metaDiv.className = 'log-message';
                    metaDiv.style.marginLeft = '12px';
                    metaDiv.style.opacity = '0.7';
                    metaDiv.textContent = `→ Response: ${logEntry.metadata.response}`;
                    logDiv.appendChild(metaDiv);
                }
                // Show emotion map if present
                if (logEntry.metadata.emotion_map) {
                    const emotionDiv = document.createElement('div');
                    emotionDiv.className = 'log-message';
                    emotionDiv.style.marginLeft = '12px';
                    emotionDiv.style.opacity = '0.7';
                    emotionDiv.textContent = `→ Emotions: ${JSON.stringify(logEntry.metadata.emotion_map)}`;
                    logDiv.appendChild(emotionDiv);
                }
                // Show messages preview
                if (logEntry.metadata.preview) {
                    const previewDiv = document.createElement('div');
                    previewDiv.className = 'log-message';
                    previewDiv.style.marginLeft = '12px';
                    previewDiv.style.opacity = '0.6';
                    previewDiv.style.fontSize = '10px';
                    previewDiv.textContent = logEntry.metadata.preview.slice(0, 3).join('\n');
                    logDiv.appendChild(previewDiv);
                }
            }

            if (logEntry.category === 'emotion') {
                // Show emotion map
                if (logEntry.metadata.emotion_map) {
                    const emotionDiv = document.createElement('div');
                    emotionDiv.className = 'log-message';
                    emotionDiv.style.marginLeft = '12px';
                    emotionDiv.style.opacity = '0.7';
                    emotionDiv.textContent = `→ ${JSON.stringify(logEntry.metadata.emotion_map)}`;
                    logDiv.appendChild(emotionDiv);
                }
                // Show context
                if (logEntry.metadata.context) {
                    const contextDiv = document.createElement('div');
                    contextDiv.className = 'log-message';
                    contextDiv.style.marginLeft = '12px';
                    contextDiv.style.opacity = '0.6';
                    contextDiv.textContent = `→ Context: ${logEntry.metadata.context}`;
                    logDiv.appendChild(contextDiv);
                }
            }

            if (logEntry.category === 'behavior') {
                // Show action details
                if (logEntry.metadata.details) {
                    const details = logEntry.metadata.details;

                    // Show reply text
                    if (details.reply) {
                        const replyDiv = document.createElement('div');
                        replyDiv.className = 'log-message';
                        replyDiv.style.marginLeft = '12px';
                        replyDiv.style.opacity = '0.7';
                        replyDiv.textContent = `→ Reply: ${details.reply}`;
                        logDiv.appendChild(replyDiv);
                    }

                    // Show action sequence
                    if (details.actions && Array.isArray(details.actions)) {
                        const actionsDiv = document.createElement('div');
                        actionsDiv.className = 'log-message';
                        actionsDiv.style.marginLeft = '12px';
                        actionsDiv.style.opacity = '0.6';
                        actionsDiv.style.fontSize = '10px';
                        actionsDiv.textContent = `→ Timeline:\n  ${details.actions.join('\n  ')}`;
                        logDiv.appendChild(actionsDiv);
                    }

                    // Show total count
                    if (details.total_actions !== undefined) {
                        const countDiv = document.createElement('div');
                        countDiv.className = 'log-message';
                        countDiv.style.marginLeft = '12px';
                        countDiv.style.opacity = '0.5';
                        countDiv.style.fontSize = '10px';
                        countDiv.textContent = `→ Total actions: ${details.total_actions}`;
                        logDiv.appendChild(countDiv);
                    }
                }
            }

            if (logEntry.category === 'websocket') {
                // Show WebSocket message details
                if (logEntry.metadata) {
                    const meta = logEntry.metadata;

                    // Show message content if available
                    if (meta.content) {
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'log-message';
                        contentDiv.style.marginLeft = '12px';
                        contentDiv.style.opacity = '0.7';
                        contentDiv.textContent = `→ ${meta.content}`;
                        logDiv.appendChild(contentDiv);
                    }

                    // Show emotion data if available
                    if (meta.emotion_map) {
                        const emotionDiv = document.createElement('div');
                        emotionDiv.className = 'log-message';
                        emotionDiv.style.marginLeft = '12px';
                        emotionDiv.style.opacity = '0.6';
                        emotionDiv.style.fontSize = '10px';
                        emotionDiv.textContent = `→ Emotions: ${JSON.stringify(meta.emotion_map)}`;
                        logDiv.appendChild(emotionDiv);
                    }

                    // Show message ID
                    if (meta.message_id) {
                        const idDiv = document.createElement('div');
                        idDiv.className = 'log-message';
                        idDiv.style.marginLeft = '12px';
                        idDiv.style.opacity = '0.4';
                        idDiv.style.fontSize = '9px';
                        idDiv.textContent = `→ ID: ${meta.message_id}`;
                        logDiv.appendChild(idDiv);
                    }
                }
            }
        }

        this.debugLogContent.appendChild(logDiv);

        // Keep only last 200 logs to prevent memory issues
        while (this.debugLogContent.children.length > 200) {
            this.debugLogContent.removeChild(this.debugLogContent.firstChild);
        }

        // Auto-scroll to bottom (since we're using column-reverse, scroll stays at bottom)
    }

    async loadUserAvatar() {
        try {
            const response = await fetch('/api/avatar/user');
            if (response.ok) {
                const data = await response.json();
                if (data.avatar_data) {
                    this.updateAvatarPreview(data.avatar_data);
                    // Store in memory for message rendering
                    this.userAvatarData = data.avatar_data;
                } else {
                    this.userAvatarData = null;
                }
            }
        } catch (error) {
            console.error('Failed to load user avatar:', error);
        }
    }

    updateAvatarPreview(avatarData) {
        if (this.avatarPreview) {
            if (avatarData) {
                this.avatarPreview.src = avatarData;
            } else {
                this.avatarPreview.src = '/static/assets/avatar_user.png';
            }
        }
    }

    async handleAvatarUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('请选择有效的图片格式（PNG、JPG、WEBP）');
            return;
        }

        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            alert('图片大小不能超过 5MB');
            return;
        }

        // Read file and convert to base64
        const reader = new FileReader();
        reader.onload = async (e) => {
            const avatarData = e.target.result;

            try {
                // Upload to server
                const response = await fetch('/api/avatar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_id: 'user',
                        avatar_data: avatarData
                    })
                });

                if (response.ok) {
                    this.updateAvatarPreview(avatarData);
                    this.userAvatarData = avatarData;
                    // Refresh message avatars if in chat view
                    if (this.wechatShell.style.display !== 'none') {
                        this.renderLocalMessages();
                    }
                } else {
                    const error = await response.json();
                    alert(`上传失败：${error.detail || '未知错误'}`);
                }
            } catch (error) {
                console.error('Failed to upload avatar:', error);
                alert('上传失败，请重试');
            }
        };

        reader.onerror = () => {
            alert('读取图片失败，请重试');
        };

        reader.readAsDataURL(file);

        // Clear input so the same file can be selected again
        event.target.value = '';
    }

    async handleAvatarDelete() {
        if (!confirm('确定要恢复为默认头像吗？')) {
            return;
        }

        try {
            const response = await fetch('/api/avatar/user', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.updateAvatarPreview(null);
                this.userAvatarData = null;
                // Refresh message avatars if in chat view
                if (this.wechatShell.style.display !== 'none') {
                    this.renderLocalMessages();
                }
            } else {
                const error = await response.json();
                alert(`删除失败：${error.detail || '未知错误'}`);
            }
        } catch (error) {
            console.error('Failed to delete avatar:', error);
            alert('删除失败，请重试');
        }
    }

    formatTimestamp(timestamp) {
        const msgDate = new Date(timestamp * 1000);
        const now = new Date();

        // Get date strings without time for comparison
        const msgDateStr = msgDate.toDateString();
        const nowDateStr = now.toDateString();
        const yesterdayDateStr = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString();

        // Format time as HH:MM (24-hour)
        const hours = msgDate.getHours().toString().padStart(2, '0');
        const minutes = msgDate.getMinutes().toString().padStart(2, '0');
        const timeStr = `${hours}:${minutes}`;

        // Check if today
        if (msgDateStr === nowDateStr) {
            return timeStr;
        }

        // Check if yesterday
        if (msgDateStr === yesterdayDateStr) {
            return `昨天 ${timeStr}`;
        }

        // Check if within 7 days (beyond yesterday)
        const daysDiff = Math.floor((now.getTime() - msgDate.getTime()) / (24 * 60 * 60 * 1000));
        if (daysDiff < 7) {
            const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
            const weekDay = weekDays[msgDate.getDay()];
            return `${weekDay} ${timeStr}`;
        }

        // Check if this year
        const msgYear = msgDate.getFullYear();
        const nowYear = now.getFullYear();
        const month = (msgDate.getMonth() + 1).toString().padStart(2, '0');
        const day = msgDate.getDate().toString().padStart(2, '0');

        if (msgYear === nowYear) {
            return `${month}-${day} ${timeStr}`;
        }

        // Different year
        return `${msgYear}-${month}-${day} ${timeStr}`;
    }

    getLastVisibleMessageTimestamp() {
        const messages = Array.from(this.localMessages.values())
            .filter(msg => msg.type === 'text')
            .sort((a, b) => a.timestamp - b.timestamp);

        if (messages.length === 0) return null;
        return messages[messages.length - 1].timestamp;
    }

}

document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
