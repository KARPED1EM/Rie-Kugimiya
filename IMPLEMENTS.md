# Yuzuriha Rin - Technical Implementation Documentation

> **Complete Developer Guide**  
> Version: 2.0 | Last Updated: 2024-12-12  
> For: Backend Developers, Full-Stack Engineers, System Architects

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [Behavior Engine](#behavior-engine)
6. [WebSocket Communication](#websocket-communication)
7. [Database Design](#database-design)
8. [API Specification](#api-specification)
9. [Frontend Implementation](#frontend-implementation)
10. [Configuration System](#configuration-system)
11. [Deployment Guide](#deployment-guide)
12. [Testing Strategy](#testing-strategy)
13. [Performance Optimization](#performance-optimization)
14. [Troubleshooting](#troubleshooting)
15. [Extension Guide](#extension-guide)

---

## System Overview

### Project Vision

Yuzuriha Rin is a **virtual character dialogue system** that simulates natural human messaging behavior using rule-based behavior engines and large language models. Unlike traditional chatbots that respond instantly, Rin exhibits realistic patterns:

- **Typing indicators** with hesitation
- **Message segmentation** like real conversations  
- **Typos and corrections** based on emotional state
- **Variable response timing** with probability distributions

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI 0.124+ | Async web framework with WebSocket support |
| **Database** | SQLite 3 | Embedded relational database for message persistence |
| **Validation** | Pydantic 2.12+ | Runtime type checking and settings management |
| **HTTP Client** | HTTPX 0.28+ | Async HTTP client for LLM API calls |
| **Frontend** | HTML5 + Vanilla JS | Lightweight, no framework overhead |
| **Real-time** | WebSocket (ASGI) | Bidirectional persistent connections |
| **NLP** | jieba, pypinyin | Chinese text processing for typo generation |

### Key Metrics

```
Code Base:        ~49 Python files
Lines of Code:    ~8,000 Python + ~1,700 CSS + Modular JS
Test Coverage:    ~80% (45+ test cases)
Response Time:    < 100ms (database queries)
Concurrency:      100+ concurrent WebSocket connections
Database Size:    < 10MB for 10k messages
```

---

## Architecture Design

### Layered Architecture

Yuzuriha Rin follows **Clean Architecture** and **Domain-Driven Design** principles with strict dependency rules:

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│  (FastAPI Routes, WebSocket Endpoints, REST APIs)       │
└────────────────────┬────────────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────────────┐
│                   Service Layer                         │
│  (Business Logic, Orchestration, Use Cases)             │
└────────────────────┬────────────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────────────┐
│               Infrastructure Layer                      │
│  (Database Repos, WebSocket Manager, Network Utils)     │
└────────────────────┬────────────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────────────┐
│                    Core Layer                           │
│  (Domain Models, Configuration, Business Rules)         │
└─────────────────────────────────────────────────────────┘

                ┌──────────────────────┐
                │  Behavior Engine     │
                │  (Independent Module)│
                └──────────────────────┘
```

### Directory Structure

```
src/
├── core/                          # 🔵 Core Domain Layer
│   ├── models/                    # Domain entities
│   │   ├── message.py             # Message, MessageType, WSMessage
│   │   ├── character.py           # Character entity
│   │   ├── session.py             # Session entity
│   │   └── constants.py           # System constants
│   └── config/                    # Configuration management
│       └── settings.py            # Pydantic Settings classes
│
├── infrastructure/                # 🟢 Infrastructure Layer  
│   ├── database/                  # Data persistence
│   │   ├── connection.py          # Database connection pool
│   │   └── repositories/          # Repository pattern
│   │       ├── base.py            # BaseRepository[T]
│   │       ├── message_repo.py    # Message CRUD
│   │       ├── character_repo.py  # Character management
│   │       ├── session_repo.py    # Session management
│   │       └── config_repo.py     # Config persistence
│   ├── network/                   # Network layer
│   │   ├── websocket_manager.py   # WebSocket connection pool
│   │   └── port_manager.py        # Port allocation
│   └── utils/                     # Infrastructure utilities
│       └── logger.py              # Unified logging system
│
├── services/                      # 🟡 Service Layer
│   ├── messaging/                 # Message business logic
│   │   └── message_service.py     # Send, recall, query messages
│   ├── character/                 # Character management
│   │   └── character_service.py   # Character CRUD, initialization
│   ├── config/                    # Configuration service
│   │   └── config_service.py      # Config read/write
│   └── ai/                        # AI services
│       ├── llm_client.py          # LLM API client
│       └── rin_client.py          # Rin AI agent
│
├── behavior/                      # 🔴 Behavior Engine (Independent)
│   ├── models.py                  # Behavior data models
│   ├── coordinator.py             # Behavior orchestration
│   ├── timeline.py                # Timeline builder
│   ├── segmenter.py               # Smart text segmentation
│   ├── emotion.py                 # Emotion detection
│   ├── typo.py                    # Typo injection & pinyin lookup
│   └── pause.py                   # Pause duration prediction
│
└── api/                           # 🟣 API/Presentation Layer
    ├── main.py                    # FastAPI application entry
    ├── routes.py                  # REST API endpoints
    ├── ws_routes.py               # WebSocket routes (per-session)
    ├── ws_global_routes.py        # Global WebSocket (debug)
    ├── schemas.py                 # API request/response DTOs
    └── dependencies.py            # Dependency injection
```

### Dependency Rules

1. **Core** → No dependencies (pure business logic)
2. **Infrastructure** → Depends on Core only
3. **Services** → Depends on Infrastructure + Core
4. **API** → Depends on Services + Infrastructure + Core
5. **Behavior** → Independent, can be used by Services

---

## Core Components

### 1. Message Server

**Location**: `src/services/messaging/message_service.py`

The message server is the **central hub** for all message operations:

**Key Features**:
- Automatic time divider insertion (every 5 minutes)
- Typing state management (in-memory, not persisted)
- Message recall with event-sourcing pattern
- System message validation (only system sender can send system types)

### 2. WebSocket Manager

**Location**: `src/infrastructure/network/websocket_manager.py`

Manages all WebSocket connections with **session-based isolation**:

- Connection pool: `Dict[session_id, Set[WebSocket]]`
- User mapping: `Dict[WebSocket, user_id]`
- Automatic cleanup on disconnect
- Broadcast to all clients in a session
- Debug mode for development

### 3. Rin Client (AI Agent)

**Location**: `src/services/ai/rin_client.py`

Rin operates as an **independent client** that:
1. Listens to user messages via MessageService
2. Calls LLM to generate responses
3. Processes text through BehaviorCoordinator
4. Executes timeline actions via WebSocket

### 4. Behavior Coordinator

**Location**: `src/behavior/coordinator.py`

The **behavior engine** transforms LLM responses into natural message sequences:

**Pipeline**:
1. Emotion Detection → Extract dominant emotion from LLM response
2. Segmentation → Split text by punctuation and length
3. Per-Segment Processing → Typo injection, send action, recall decision, pause
4. Timeline Building → Add hesitation, typing states, absolute timestamps

**Behavior Types**:

| Action Type | Description | Example |
|------------|-------------|---------|
| `typing_start` | Show typing indicator | User sees "正在输入..." |
| `typing_end` | Hide typing indicator | Indicator disappears |
| `send` | Send a message segment | "你好" appears in chat |
| `recall` | Recall a message | Message deleted |
| `wait` | Pause execution | 1.5s delay |

---

## Data Models

### Message Model

**Location**: `src/core/models/message.py`

```python
class MessageType(str, Enum):
    TEXT = "text"                    # Regular user/assistant message
    SYSTEM_TIME = "system-time"      # Time divider (e.g., "下午 2:30")
    SYSTEM_CLEAR = "system-clear"    # Clear conversation marker
    SYSTEM_RECALL = "system-recall"  # Recall event
    SYSTEM_EDIT = "system-edit"      # Edit event (future)

class Message(BaseModel):
    id: str                          # "msg-{uuid12}"
    session_id: str                  # Session identifier
    sender_id: str                   # "user" | "assistant" | "system"
    type: MessageType                # Message type enum
    content: str                     # Message text
    metadata: Dict[str, Any]         # Flexible JSON metadata
    is_recalled: bool                # Recall status
    is_read: bool                    # Read status
    timestamp: float                 # Unix timestamp (UTC)
```

### Character Model

**Location**: `src/core/models/character.py`

Characters define the AI's personality and behavior parameters with 20+ configurable fields including:
- Basic info (name, avatar, persona)
- Behavior toggles (segmentation, typo, recall, emotion)
- Rate parameters (typo rate, recall rate, delays)
- Timing configurations (hesitation, typing lead time)

### Session Model

**Location**: `src/core/models/session.py`

One-to-one relationship: Each session belongs to exactly one character.

### Playback Action Model

**Location**: `src/behavior/models.py`

Represents a single step in the behavior timeline with absolute timestamps for precise execution.

---

## Behavior Engine

### Timeline Building Algorithm

**Location**: `src/behavior/timeline.py`

The timeline builder converts relative durations into absolute timestamps:

**Steps**:
1. Generate hesitation sequence (15% probability) → 1-2 cycles of typing_start/wait/typing_end
2. Sample initial delay (probability-weighted) → 45%: 3-4s | 30%: 4-6s | 18%: 6-7s | 7%: 8-9s
3. Process each action with typing states and lead times
4. Accumulate timestamps and return sorted timeline

**Typing Lead Time Calculation**:

| Text Length | Lead Time |
|------------|-----------|
| ≤ 6 chars | 1200 ms |
| 6-15 chars | 2000 ms |
| 15-28 chars | 3800 ms |
| 28-34 chars | 6000 ms |
| 34-50 chars | 8800 ms |
| > 50 chars | 2500 ms (default) |

### Typo Injection

**Location**: `src/behavior/typo.py`

Typos are generated using **same-pinyin character substitution** with emotion-based probability multipliers:

```python
{
    "neutral": 1.0,
    "happy": 1.2,
    "excited": 2.0,    # 2x more typos when excited
    "sad": 0.5,        # 50% fewer typos when sad
    "angry": 2.3,      # Most typos when angry
    "anxious": 1.3,
    "confused": 0.3,   # Fewest typos when confused
}
```

### Segmentation Algorithm

**Location**: `src/behavior/segmenter.py`

Smart segmentation based on **punctuation and length**:

1. Split on sentence-ending punctuation (。！？)
2. Split long sentences on commas (，)
3. Hard-split if still exceeds max_length
4. Clean trailing punctuation from segments

**Example**:
```
Input:  "你好！今天天气真好，我们出去玩吧。"
Output: ["你好", "今天天气真好", "我们出去玩吧"]
```

---

## WebSocket Communication

### Protocol Specification

All WebSocket messages use this envelope:

```typescript
interface WSMessage {
    type: string;                    // Event type
    data: Record<string, any>;       // Payload
    timestamp: number;               // Unix timestamp
}
```

### Client → Server Events

1. **User Message**: Send a text message
2. **Typing State**: Update typing indicator
3. **Recall Message**: Recall a previously sent message
4. **Clear Conversation**: Clear all messages
5. **Sync Request**: Get messages after timestamp (incremental sync)

### Server → Client Events

1. **Message Event**: New message delivered
2. **Typing Event**: Typing status update
3. **Recall Event**: Message recall notification
4. **History Event**: Initial or incremental message history
5. **Clear Event**: Conversation cleared

### Event-Sourced Recall Pattern

**Problem**: Traditional UPDATE-based recall breaks incremental sync

**Solution**: Recall as a **new event** with new timestamp:
- ✅ Incremental sync works (new timestamp > client's last_sync)
- ✅ Audit trail preserved (original message still in DB)
- ✅ Offline clients sync recalls when reconnecting
- ✅ Supports undo/redo in future

---

## Database Design

### Schema

```sql
-- Messages table (unified storage for all message types)
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    metadata TEXT,
    is_recalled BOOLEAN DEFAULT 0,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_timestamp ON messages(session_id, timestamp);
CREATE INDEX idx_sender ON messages(sender_id);

-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Characters table (20+ config columns)
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    avatar TEXT NOT NULL,
    persona TEXT NOT NULL,
    is_builtin BOOLEAN DEFAULT 0,
    -- Behavior config columns
    enable_segmentation BOOLEAN DEFAULT 1,
    enable_typo BOOLEAN DEFAULT 1,
    -- ... more config fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Config table (key-value store)
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Repository Pattern

All repositories extend `BaseRepository[T]` with common CRUD operations. Custom methods are added per repository for specific queries (e.g., `get_by_session`, `get_active_session`).

---

## API Specification

### REST Endpoints

**Location**: `src/api/routes.py`

- `GET /api/health` - Health check
- `GET /api/characters` - List all characters
- `GET /api/characters/{id}` - Get character by ID
- `PUT /api/characters/{id}` - Update character
- `GET /api/sessions` - List sessions
- `POST /api/sessions` - Create new session
- `PUT /api/config` - Update configuration

### WebSocket Endpoints

- `WS /api/ws/{session_id}?user_id=user` - Per-session WebSocket
- `WS /api/ws/global?debug=true` - Global debug WebSocket

---

## Frontend Implementation

### Architecture

Pure vanilla JavaScript with **modular structure**:

```
frontend/
├── index.html
├── scripts/
│   ├── app.js                  # Entry point
│   ├── core/                   # Core modules
│   ├── views/                  # UI views
│   ├── ui/                     # UI components
│   └── utils/                  # Utilities
└── styles/
    └── styles.css              # All styles (~1700 lines)
```

WeChat-style mobile interface with:
- Message bubbles (sent/received)
- Typing indicators
- Time dividers
- Smooth animations
- Responsive design

---

## Configuration System

### Centralized Settings

**Location**: `src/core/config/settings.py`

All configuration uses **Pydantic Settings** with environment variable support:

- `AppConfig` - Application settings
- `LLMDefaults` - LLM provider defaults
- `BehaviorDefaults` - Behavior engine settings
- `TypingStateDefaults` - Typing/hesitation config
- `DatabaseConfig` - Database configuration
- `WebSocketConfig` - WebSocket settings

### Built-in Characters

Two characters are initialized on first run:

- **Rin (小红)** - Default cheerful assistant
- **Abai (阿白)** - Alternative personality

---

## Deployment Guide

### Development

```bash
python run.py
# Or with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --ws-ping-interval 20 \
    --ws-ping-timeout 10
```

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv pip install -e .
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Testing Strategy

### Test Structure

```
tests/
├── test_config.py              # Config validation
├── test_database.py            # DB operations
├── test_message_service.py     # Service layer
├── test_behavior_system.py     # Behavior engine
└── run_all_tests.py            # Test runner
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## Performance Optimization

### Database Optimization

- Compound indexes for session + timestamp queries
- Use LIMIT to prevent full table scans
- Select only needed columns (avoid SELECT *)
- Context managers for auto-cleanup

### WebSocket Optimization

- Efficient set-based lookups O(1)
- Parallel broadcast with asyncio.gather
- Auto-remove failed connections
- Connection pooling

### Behavior Engine Optimization

- Caching emotion detection results
- Async execution for timeline playback
- Pre-computed probability distributions

---

## Troubleshooting

### Common Issues

#### WebSocket Connection Failed
- ✅ Use `localhost` instead of `0.0.0.0`
- ✅ Check CORS configuration
- ✅ Verify proxy WebSocket upgrade headers

#### Database Locked
- ✅ Use context managers for auto-cleanup
- ❌ Avoid long-lived connections

#### LLM API Timeout
- ✅ Verify API key validity
- ✅ Check network connectivity
- ✅ Increase timeout configuration

#### Messages Not Persisting
- ✅ Ensure `data/` directory exists
- ✅ Check disk space
- ✅ Verify service layer calls

---

## Extension Guide

### Adding a New LLM Provider

Implement in `LLMClient._call_custom_provider()` following the existing pattern.

### Adding a New Behavior Type

1. Add to `PlaybackAction` type literal
2. Generate in `BehaviorCoordinator`
3. Handle in `RinClient._execute_timeline()`

### Adding a New Repository

1. Create repository class extending `BaseRepository[T]`
2. Implement abstract methods
3. Add custom query methods
4. Register in service layer

### Extending WebSocket Protocol

1. Add handler in `ws_routes.py`
2. Update frontend to send/receive
3. Document new message type

---

## Maintainer

**Project**: Yuzuriha Rin  
**Author**: Leever  
**Documentation Version**: 2.0  
**Last Updated**: 2024-12-12

---

For user documentation, see [README.md](README.md)
