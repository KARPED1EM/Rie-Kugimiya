// Chat application logic
class ChatApp {
    constructor() {
        this.config = null;
        this.conversationHistory = [];
        this.sessionId = this.loadOrCreateSessionId();
        this.isProcessing = false;
        this.avatarPaths = {
            user: "/static/assets/avatar_user.png",
            assistant: "/static/assets/avatar_rin.png"
        };
        this.emotionPalette = {
            neutral: { h: 155, s: 18, l: 60 },
            happy: { h: 48, s: 86, l: 62 },
            excited: { h: 14, s: 82, l: 58 },
            sad: { h: 208, s: 60, l: 56 },
            angry: { h: 2, s: 78, l: 52 },
            anxious: { h: 266, s: 46, l: 56 },
            confused: { h: 190, s: 48, l: 54 },
            caring: { h: 120, s: 50, l: 58 },
            playful: { h: 320, s: 62, l: 60 },
            surprised: { h: 30, s: 80, l: 60 },
        };
        this.intensityWeights = { low: 0.45, medium: 0.85, high: 1.1, extreme: 1.3 };
        this.baseAccent = this.hexToHsl("#07c160");
        this.lastEmotionMap = null;
        
        this.initElements();
        this.attachEventListeners();
        this.loadSavedConfig();
    }

    loadOrCreateSessionId() {
        const existing = localStorage.getItem('conversationId');
        if (existing) {
            return existing;
        }
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
    
    initElements() {
        // Config elements
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
        
        // Chat elements
        this.chatContainer = document.getElementById('chatContainer');
        this.wechatShell = document.querySelector('.wechat-shell');
        this.wechatInput = document.querySelector('.wechat-input');
        this.chatTitle = document.getElementById('chatTitle');
        this.messagesDiv = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.voiceBtn = document.querySelector('.voice-btn');
        this.emojiBtn = document.querySelector('.emoji-btn');
        this.plusBtn = document.querySelector('.plus-btn');
        this.toggleBtn = document.getElementById('toggleBtn');
        this.showConfigBtn = document.getElementById('showConfig');
        this.statusTime = document.getElementById('statusTime');
        this.typingHint = document.getElementById('typingHint');
        this.messageRefs = new Map();
        this.defaultTitle = this.chatTitle.textContent || 'Rin';
        this.typingActive = false;
        this.typingStartTimestamp = null;
        this.baseComposerHeight = 34;
        this.composerMetricsInitialized = false;

        if (this.statusTime) {
            this.statusTime.textContent = this.getCurrentTime();
        }
    }
    
    attachEventListeners() {
        this.providerSelect.addEventListener('change', () => {
            const isCustom = this.providerSelect.value === 'custom';
            this.baseUrlGroup.style.display = isCustom ? 'block' : 'none';
            
            // Update default models
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
                if (this.emotionThemeToggle.checked) {
                    this.applyEmotionTheme(this.lastEmotionMap);
                } else {
                    this.clearEmotionTheme();
                }
            });
        }
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
                
                // Trigger change event
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

        // Reset session and history on new config
        this.sessionId = this.createSessionId();
        localStorage.setItem('conversationId', this.sessionId);
        this.conversationHistory = [];
        this.lastEmotionMap = null;
        this.clearEmotionTheme();
        
        localStorage.setItem('chatConfig', JSON.stringify(this.config));
        this.toggleView();
        this.enableChat();
    }
    
    toggleView() {
        const showChat = this.configPanel.style.display !== 'none';
        this.configPanel.style.display = showChat ? 'none' : 'block';
        this.chatContainer.style.display = showChat ? 'flex' : 'none';
        
        if (showChat && this.config) {
            this.defaultTitle = this.config.character_name || 'Rin';
            this.chatTitle.textContent = this.defaultTitle;
        }
    }
    
    enableChat() {
        this.userInput.disabled = false;
        this.toggleBtn.disabled = true;
        this.initComposerMetrics();
        this.resetComposerHeight();
        this.autoResizeInput();
        this.userInput.focus();
        this.updateComposerState();
    }

    pickLLMConfig(source) {
        if (!source) {
            return null;
        }
        const { provider, api_key, base_url, model, persona } = source;
        return {
            provider,
            api_key,
            base_url: base_url || null,
            model,
            persona
        };
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
            avatar.src = role === 'user' ? this.avatarPaths.user : this.avatarPaths.assistant;
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

        if (options.recalled) {
            row.classList.add('recalled');
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
    
    async sendMessage() {
        const text = this.userInput.value.trim();
        if (!text || this.isProcessing) return;
        
        this.isProcessing = true;
        this.userInput.value = '';
        this.updateComposerState();
        
        // Add user message
        this.addMessage('user', text);
        this.conversationHistory.push({ role: 'user', content: text });
        
        try {
            this.setTypingStatus(false);

            // Call API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    llm_config: this.pickLLMConfig(this.config),
                    messages: this.conversationHistory,
                    character_name: this.config.character_name,
                    conversation_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            this.applyEmotionTheme(data?.metadata?.emotion_map || data?.metadata?.emotionMap || null);
            this.setTypingStatus(false);
            await this.waitBeforePlayback();
            // Play message actions
            await this.playMessageActions(data.actions);
            
            // Update conversation history
            this.conversationHistory.push({
                role: 'assistant',
                content: data.raw_response
            });
            
        } catch (error) {
            // Try to get more detailed error info
            let errorMsg = error.message;
            if (error.message.includes('API error: 500')) {
                errorMsg = 'Server error. Please check:\n' +
                          '1. API key is valid\n' +
                          '2. Model name is correct\n' +
                          '3. Network connection\n' +
                          'Check browser console for details.';
            } else if (error.message.includes('API error: 401')) {
                errorMsg = 'Authentication failed. Please check your API key.';
            } else if (error.message.includes('API error: 404')) {
                errorMsg = 'Model not found. Please check the model name.';
            }

            this.addMessage('system', `Error: ${errorMsg}`);
            console.error('Chat error:', error);
        } finally {
            this.setTypingStatus(false);
            this.isProcessing = false;
            this.userInput.focus();
        }
    }
    
    async playMessageActions(actions) {
        await this.playHesitationSequence();
        let typingPlan = this.createTypingPlan(this.findNextSendText(actions, 0));

        for (let idx = 0; idx < actions.length; idx++) {
            const action = actions[idx];

            switch (action.type) {
                case 'pause': {
                    await this.playPauseWithPlan(action.duration || 0, typingPlan);
                    break;
                }

                case 'send': {
                    await this.ensureTypingLead(typingPlan);
                    const messageDiv = this.addMessage('assistant', action.text, {
                        emotion: action.metadata?.emotion,
                        messageId: action.message_id
                    });

                    if (action.message_id) {
                        this.messageRefs.set(action.message_id, messageDiv);
                    }

                    const nextText = this.findNextSendText(actions, idx + 1);
                    const keepTyping = typingPlan && typingPlan.keepAfterSend && !!nextText;
                    if (!keepTyping) {
                        this.setTypingStatus(false);
                    }
                    typingPlan = this.createTypingPlan(nextText);
                    break;
                }

                case 'recall': {
                    if (action.target_id && this.messageRefs.has(action.target_id)) {
                        const messageDiv = this.messageRefs.get(action.target_id);
                        if (messageDiv) {
                            messageDiv.remove();
                        }
                        this.messageRefs.delete(action.target_id);
                        this.showRecallNotice();
                    }
                    break;
                }
                default: {
                    break;
                }
            }
        }

        this.finishTypingState();
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
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
        this.autoResizeInput();
    }

    initComposerMetrics() {
        if (!this.wechatInput || !this.userInput || this.composerMetricsInitialized) return;
        const measured = this.measureBaseComposerHeight();
        if (!Number.isNaN(measured) && measured > 0) {
            this.baseComposerHeight = measured;
        }
        this.composerMetricsInitialized = true;
    }

    resetComposerHeight() {
        if (!this.wechatInput || !this.userInput) return;
        this.userInput.style.height = `${this.baseComposerHeight}px`;
    }

    measureBaseComposerHeight() {
        if (!this.userInput) return this.baseComposerHeight;
        const prevValue = this.userInput.value;
        const prevHeight = this.userInput.style.height;
        this.userInput.style.height = 'auto';
        this.userInput.value = '';
        const measured = this.userInput.scrollHeight || this.baseComposerHeight;
        this.userInput.value = prevValue;
        this.userInput.style.height = prevHeight;
        return measured;
    }

    autoResizeInput() {
        if (!this.userInput || !this.wechatInput) return;
        const minHeight = this.baseComposerHeight || 34;
        this.userInput.style.height = 'auto';
        const nextHeight = Math.max(minHeight, this.userInput.scrollHeight);
        this.userInput.style.height = `${nextHeight}px`;
    }

    setTypingStatus(active, forceReset = false) {
        if (!this.chatTitle) {
            return;
        }
        if (this.typingActive === active && !forceReset) {
            return;
        }
        this.typingActive = active;
        this.chatTitle.textContent = active
            ? "对方正在输入中..."
            : (this.defaultTitle || 'Rin');
        this.typingStartTimestamp = active ? Date.now() : null;
    }

    finishTypingState() {
        this.setTypingStatus(false);
    }

    findNextSendText(actions, startIndex) {
        for (let i = startIndex; i < actions.length; i++) {
            if (actions[i] && actions[i].type === 'send') {
                return actions[i].text || '';
            }
        }
        return null;
    }

    getAssistantDisplayName() {
        if (this.config && this.config.character_name) {
            const name = this.config.character_name.trim();
            if (name) {
                return name;
            }
        }
        if (this.defaultTitle && this.defaultTitle.trim()) {
            return this.defaultTitle.trim();
        }
        return 'Rin';
    }

    showRecallNotice() {
        const name = this.getAssistantDisplayName();
        const text = `“${name}” 撤回了一条消息`;
        this.addMessage('system', text);
    }

    createTypingPlan(text) {
        if (!text) {
            return null;
        }

        const length = text.trim().length;
        if (length > 140) {
            return {
                leadTime: 2500,
                keepAfterSend: true,
                entryDelayRange: { min: 200, max: 600 }
            };
        }
        if (length > 100) {
            return {
                leadTime: 2200,
                keepAfterSend: true,
                entryDelayRange: { min: 200, max: 800 }
            };
        }
        if (length > 60) {
            return {
                leadTime: 1600,
                keepAfterSend: false,
                entryDelayRange: { min: 300, max: 1000 }
            };
        }
        if (length > 30) {
            return {
                leadTime: 1100,
                keepAfterSend: false,
                entryDelayRange: { min: 400, max: 1200 }
            };
        }
        if (length > 15) {
            return {
                leadTime: 800,
                keepAfterSend: false,
                entryDelayRange: { min: 550, max: 1500 }
            };
        }
        return {
            leadTime: 600,
            keepAfterSend: false,
            entryDelayRange: { min: 750, max: 2000 }
        };
    }

    async playPauseWithPlan(duration, plan) {
        const pauseMs = Math.max(0, (duration || 0) * 1000);

        if (!plan) {
            if (pauseMs > 0) {
                await this.sleep(pauseMs);
            }
            return;
        }

        if (!this.typingActive) {
            const entryDelay = this.sampleTypingEntryDelay(plan);
            if (entryDelay > 0) {
                await this.sleep(entryDelay);
            }
        }

        const targetMs = pauseMs > 0 ? pauseMs : (plan.leadTime || 0);
        const forceRestart = this.typingActive;
        await this.ensureTypingLead(plan, targetMs, forceRestart);
    }

    async ensureTypingLead(plan, overrideLeadMs = null, forceRestart = false) {
        if (!plan) {
            this.setTypingStatus(false);
            return;
        }

        const targetMs = overrideLeadMs != null ? overrideLeadMs : plan.leadTime;
        if (!this.typingActive) {
            this.setTypingStatus(true);
        } else if (forceRestart) {
            this.setTypingStatus(true, true);
        }

        if (!targetMs || targetMs <= 0) {
            return;
        }

        const elapsed = this.typingActive && this.typingStartTimestamp
            ? Date.now() - this.typingStartTimestamp
            : 0;
        const remaining = Math.max(0, targetMs - elapsed);
        if (remaining > 0) {
            await this.sleep(remaining);
        }
    }

    async playHesitationSequence() {
        if (Math.random() > 0.15) {
            return;
        }

        const cycles = Math.random() < 0.4 ? 2 : 1;
        for (let i = 0; i < cycles; i++) {
            this.setTypingStatus(true);
            await this.sleep(this.randomRange(400, 1200));
            this.setTypingStatus(false);
            if (i < cycles - 1 && Math.random() < 0.3) {
                await this.sleep(this.randomRange(300, 900));
            }
        }
    }

    sampleTypingEntryDelay(plan) {
        const defaultMin = 200;
        const defaultMax = 2000;

        const range = plan?.entryDelayRange || {};
        const rawMin = typeof range.min === 'number' ? range.min : defaultMin;
        const rawMax = typeof range.max === 'number' ? range.max : defaultMax;

        const clampedMin = Math.max(0, Math.min(rawMin, 2500));
        const clampedMax = Math.max(clampedMin, Math.min(rawMax, 2500));
        return this.randomRange(clampedMin, clampedMax);
    }

    randomRange(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    applyEmotionTheme(emotionMap) {
        if (!this.wechatShell) {
            return;
        }
        if (!this.emotionThemeToggle || !this.emotionThemeToggle.checked) {
            this.clearEmotionTheme();
            return;
        }

        this.lastEmotionMap = emotionMap || null;
        const theme = this.computeThemeColor(emotionMap);
        if (!theme) {
            this.clearEmotionTheme();
            return;
        }

        const glowBase = this.hslToString(theme, 1);
        const glowCore = this.hslToString(
            { h: theme.h, s: Math.min(theme.s + 6, 92), l: Math.min(theme.l + 4, 74) },
            0.72
        );
        const glowSoft = this.hslToString(
            { h: theme.h, s: Math.max(theme.s - 8, 30), l: Math.min(theme.l + 12, 82) },
            0.38
        );

        this.wechatShell.style.setProperty('--glow-base', glowBase);
        this.wechatShell.style.setProperty('--glow-shadow', glowCore);
        this.wechatShell.style.setProperty('--glow-shadow-soft', glowSoft);
        this.wechatShell.classList.add('glow-enabled');
    }

    clearEmotionTheme() {
        if (!this.wechatShell) return;
        this.wechatShell.classList.remove('glow-enabled');
        this.wechatShell.style.removeProperty('--glow-base');
        this.wechatShell.style.removeProperty('--glow-shadow');
        this.wechatShell.style.removeProperty('--glow-shadow-soft');
    }

    computeThemeColor(emotionMap) {
        const normalized = this.normalizeEmotionMap(emotionMap);
        const base = this.baseAccent || { h: 141, s: 80, l: 46 };
        const anchorWeight = 1.2;

        let vx = Math.cos(this.degToRad(base.h)) * anchorWeight;
        let vy = Math.sin(this.degToRad(base.h)) * anchorWeight;
        let sAcc = base.s * anchorWeight;
        let lAcc = base.l * anchorWeight;
        let total = anchorWeight;

        Object.entries(normalized).forEach(([emotion, intensity]) => {
            const color = this.emotionPalette[emotion] || this.emotionPalette.neutral || base;
            const weight = this.intensityWeights[intensity] ?? 0.6;
            const emotionBias = emotion === 'neutral' ? 0.45 : 1;
            const w = weight * emotionBias;

            vx += Math.cos(this.degToRad(color.h)) * w;
            vy += Math.sin(this.degToRad(color.h)) * w;
            sAcc += color.s * w;
            lAcc += color.l * w;
            total += w;
        });

        if (total <= 0) {
            return base;
        }

        const hue = (Math.atan2(vy, vx) * 180 / Math.PI + 360) % 360;
        const saturation = this.clamp(sAcc / total, 32, 86);
        const lightness = this.clamp(lAcc / total, 38, 70);

        return {
            h: Math.round(hue),
            s: Math.round(saturation),
            l: Math.round(lightness),
        };
    }

    normalizeEmotionMap(emotionMap) {
        if (!emotionMap || typeof emotionMap !== 'object') {
            return {};
        }
        const normalized = {};
        Object.entries(emotionMap).forEach(([key, value]) => {
            const emotion = String(key).trim().toLowerCase();
            const intensity = String(value).trim().toLowerCase();
            if (!emotion) return;
            if (!this.intensityWeights[intensity]) return;
            normalized[emotion] = intensity;
        });
        return normalized;
    }

    hslToString(hsl, alpha = 1) {
        const a = this.clamp(alpha, 0, 1);
        return `hsla(${Math.round(hsl.h)}, ${Math.round(hsl.s)}%, ${Math.round(hsl.l)}%, ${a})`;
    }

    degToRad(deg) {
        return (deg * Math.PI) / 180;
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    hexToHsl(hex) {
        const rgb = this.hexToRgb(hex);
        if (!rgb) return { h: 141, s: 80, l: 46 };
        return this.rgbToHsl(rgb.r, rgb.g, rgb.b);
    }

    hexToRgb(hex) {
        if (!hex || typeof hex !== 'string') return null;
        const normalized = hex.replace('#', '');
        if (normalized.length !== 3 && normalized.length !== 6) return null;
        const value = normalized.length === 3
            ? normalized.split('').map((c) => c + c).join('')
            : normalized;
        const intVal = parseInt(value, 16);
        if (Number.isNaN(intVal)) return null;
        return {
            r: (intVal >> 16) & 255,
            g: (intVal >> 8) & 255,
            b: intVal & 255,
        };
    }

    rgbToHsl(r, g, b) {
        const rn = r / 255;
        const gn = g / 255;
        const bn = b / 255;

        const max = Math.max(rn, gn, bn);
        const min = Math.min(rn, gn, bn);
        let h = 0;
        let s = 0;
        const l = (max + min) / 2;

        if (max !== min) {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case rn:
                    h = (gn - bn) / d + (gn < bn ? 6 : 0);
                    break;
                case gn:
                    h = (bn - rn) / d + 2;
                    break;
                default:
                    h = (rn - gn) / d + 4;
                    break;
            }
            h /= 6;
        }

        return {
            h: Math.round(h * 360),
            s: Math.round(s * 100),
            l: Math.round(l * 100),
        };
    }

    async waitBeforePlayback() {
        const delay = this.sampleInitialDelay();
        if (delay > 0) {
            await this.sleep(delay * 1000);
        }
    }

    sampleInitialDelay() {
        const roll = Math.random();
        if (roll < 0.45) {
            return this.randomRange(3, 4);
        }
        if (roll < 0.75) {
            return this.randomRange(4, 6);
        }
        if (roll < 0.93) {
            return this.randomRange(6, 8);
        }
        return this.randomRange(8, 10);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
