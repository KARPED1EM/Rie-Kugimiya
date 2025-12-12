<div align="center">

# 🌸 Yuzuriha Rin (楪鈴)

**A Natural Virtual Character Dialogue System**

[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124+-00C7B7.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

*Transform AI conversations into lifelike messaging experiences with intelligent behavior simulation*

[Features](#-features) • [Quick Start](#-quick-start) • [Usage Guide](#-usage-guide) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## ✨ Features

### 🎭 **Natural Behavior Engine**
- **Smart Segmentation** - Messages split naturally like real conversations
- **Typing Indicators** - Real-time "typing..." status with hesitation simulation
- **Typo Injection** - Emotion-driven typos with intelligent auto-correction
- **Message Recall** - AI can recall and retype messages with errors
- **Emotion Detection** - LLM-driven emotion analysis affects typing patterns

### 🚀 **Modern Architecture**
- **Real-time WebSocket** - Bidirectional communication for instant updates
- **Message Persistence** - SQLite storage, conversations survive page refreshes
- **Multi-LLM Support** - DeepSeek, OpenAI, Anthropic, or custom endpoints
- **Centralized Config** - All settings managed in one place
- **Clean Separation** - Backend handles logic, frontend handles UI

### 💬 **Rich Messaging Experience**
- **WeChat-style UI** - Familiar mobile messaging interface
- **Timeline Playback** - Precise timestamp-based message delivery
- **Session Management** - Multiple character conversations
- **Debug Mode** - Real-time behavior logging for development

---

## 📸 Screenshots

<div align="center">
<img src="docs/screenshot-chat.png" alt="Chat Interface" width="350"/>
<img src="docs/screenshot-config.png" alt="Configuration Panel" width="350"/>
</div>

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (3.11 not supported due to PyTorch compatibility)
- **uv** package manager (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/KARPED1EM/Yuzuriha-Rin.git
cd Yuzuriha-Rin

# Install dependencies with uv (recommended)
uv pip install -e .

# Or use pip
pip install -e .
```

### Start the Server

```bash
# Quick start
python run.py

# Or use uvicorn directly
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

> ⚠️ **Important**: Always use `localhost`, NOT `0.0.0.0` for WebSocket connections

---

## 🎯 Usage Guide

### 1️⃣ Configure Your AI Character

Click the **Character Settings** button in the app header to configure:

#### **LLM Provider**
Choose your AI provider:
- **DeepSeek** (Recommended for Chinese users - fast & affordable)
- **OpenAI** (GPT-3.5, GPT-4)
- **Anthropic** (Claude models)
- **Custom** (Any OpenAI-compatible API)

#### **API Configuration**
```yaml
Provider: deepseek
API Key: sk-xxxxxxxxxxxxxxxx
Model: deepseek-chat
```

#### **Character Persona**
Define your character's personality:
```
You are Rin, an 18-year-old cheerful girl who loves chatting with users...
```

#### **Behavior Settings**
Fine-tune natural behaviors:
- **Segmentation**: Break long messages into natural chunks
- **Typo Rate**: How often the character makes typos (0-20%)
- **Recall Rate**: Chance to fix typos (0-100%)
- **Emotion Detection**: Enable emotion-aware responses

### 2️⃣ Start Chatting

1. Type your message in the input box
2. Press **Enter** or click **Send**
3. Watch Rin respond naturally with:
   - Typing indicators
   - Message segmentation
   - Occasional typos and corrections
   - Emotion-appropriate pauses

### 3️⃣ Advanced Features

#### **Clear Conversation**
Click the menu (⋯) → **Clear Conversation** to start fresh

#### **Debug Mode**
Access via global WebSocket endpoint to view:
- Behavior timeline execution
- Emotion detection results
- System logs in real-time

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│            Message Server (Backend)             │
│  ┌──────────────┐      ┌──────────────────┐   │
│  │   SQLite DB  │◄─────┤ MessageService   │   │
│  └──────────────┘      └────────┬─────────┘   │
│                                  │              │
│  ┌───────────────────────────────▼──────────┐  │
│  │       WebSocket Manager                  │  │
│  └─────┬─────────────────────────┬──────────┘  │
└────────┼─────────────────────────┼─────────────┘
         │                         │
    ┌────▼────┐              ┌─────▼──────┐
    │  User   │              │ Rin Client │
    │(Browser)│              │  + LLM +   │
    └─────────┘              │  Behavior  │
                             └────────────┘
```

### Key Components

- **Message Server**: WebSocket hub + SQLite persistence
- **Rin Client**: Independent AI agent with behavior engine
- **Behavior Engine**: Simulates natural messaging patterns
- **Frontend**: Pure HTML/CSS/JS, event-driven UI

For detailed architecture, see [IMPLEMENTS.md](IMPLEMENTS.md)

---

## 📁 Project Structure

```
Yuzuriha-Rin/
├── src/
│   ├── core/              # Domain models & config
│   ├── infrastructure/    # Database, WebSocket, utils
│   ├── services/          # Business logic layer
│   ├── behavior/          # Natural behavior engine
│   └── api/               # FastAPI routes & schemas
├── frontend/              # Web UI (HTML/CSS/JS)
├── data/                  # SQLite database storage
├── tests/                 # Unit & integration tests
└── pyproject.toml         # Project dependencies
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file to override defaults:

```bash
# LLM Configuration
LLM_PROVIDER=deepseek
LLM_MODEL_DEEPSEEK=deepseek-chat

# Behavior Tuning
BEHAVIOR_BASE_TYPO_RATE=0.05
BEHAVIOR_ENABLE_SEGMENTATION=true

# Server Settings
WS_HOST=0.0.0.0
WS_PORT=8000
```

### Character Presets

Built-in characters are automatically initialized:
- **Rin** (小红) - Default cheerful assistant
- **Abai** (阿白) - Alternative personality

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test module
python -m pytest tests/test_behavior_system.py

# Check server health
curl http://localhost:8000/api/health
```

---

## 📚 Documentation

- **[IMPLEMENTS.md](IMPLEMENTS.md)** - Complete developer documentation
  - Detailed architecture diagrams
  - API specifications
  - Database schema
  - Behavior engine algorithms
  - Extension guides

---

## 🛠️ Troubleshooting

### WebSocket Connection Failed

✅ **Solution**: Use `http://localhost:8000` instead of `http://0.0.0.0:8000`

### LLM Response Timeout

```bash
# Check API key validity
# Verify network connectivity
# Increase timeout in LLM client settings
```

### Database Lock Errors

SQLite uses single-writer locks. Ensure:
- No long-running transactions
- Proper connection cleanup with context managers

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process or change port in config
```

---

## 🤝 Contributing

This is an educational project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Inspired by WeChat's messaging UX
- Behavior patterns based on real messaging app research

---

<div align="center">

**Made with ❤️ for Natural AI Conversations**

[⬆ Back to Top](#-yuzuriha-rin-楪鈴)

</div>
