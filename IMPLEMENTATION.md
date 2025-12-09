# Implementation Guide

This document explains the implementation of the Yuzuriha Rin virtual character system, focusing on the behavior simulation architecture.

## Architecture Overview

The system is divided into three main layers:

```
┌─────────────────┐
│   Frontend UI   │  - Web interface with WeChat-style playback
│   (HTML/CSS/JS) │  - Sequential send/pause/recall timeline
└────────┬────────┘  - Emotion indicators and recall removal
         │
┌────────▼────────┐
│   FastAPI API   │  - REST endpoints
│                 │  - Request/response handling
└────────┬────────┘  - Configuration management
         │
┌────────▼────────┐
│  LLM Client     │  - Multi-provider support (OpenAI/Anthropic/Custom)
│                 │  - Async HTTP communication
└────────┬────────┘
         │
┌────────▼────────┐
│ Behavior System │  - Message segmentation (rule-based)
│                 │  - Emotion interpretation
│                 │  - Typo injection
│                 │  - Recall simulation
└─────────────────┘
```

## Behavior System Components

### 1. Message Segmentation (`src/behavior/segmenter.py`)

The segmentation module now relies purely on rule-based logic (no mini model dependency):

**BaseSegmenter (Abstract Class)**
- Defines the interface for all segmenters
- Method: `segment(text: str) -> List[str]`

**RuleBasedSegmenter**
- Splits on punctuation/dash characters
- Preserves punctuation (later trimmed by postfix)
- Enforces a soft max segment length when no punctuation is present

**SmartSegmenter (Recommended)**
- Currently uses `RuleBasedSegmenter` internally
- Provides consistent API for segmentation

### 2. Emotion Interpretation (`src/behavior/emotion.py`)

**EmotionDetector**
- Interprets LLM-returned emotion maps (`{emotion: intensity}`)
- Supports 7 emotion states: neutral, happy, excited, sad, angry, anxious, confused
- Intensity order: low < medium < high < extreme
- Falls back to neutral when the map is missing/invalid

**Supported Emotions:**
- `NEUTRAL`: Default state
- `HAPPY`: Joy, happiness
- `EXCITED`: High energy, enthusiasm
- `SAD`: Sadness, disappointment
- `ANGRY`: Frustration, anger
- `ANXIOUS`: Nervousness, worry
- `CONFUSED`: Uncertainty, confusion

### 3. Typo Injection (`src/behavior/typo.py`)

**TypoInjector**
- Simulates realistic typos
- Supports both Chinese and English
- Chinese: Similar character substitution
- English: Keyboard neighbor substitution
- Configurable typo rate (probability)
- Emotion-aware typo frequency

**Typo Strategy:**
- Position: Prefers middle-to-end of text (more realistic)
- Character selection: Only replaceable characters (has similar char or keyboard neighbor)
- Preserves case for English

### 4. Pause Prediction (`src/behavior/pause.py`)

**PausePredictor**
- Predicts natural pause durations between segments
- Emotion-aware pause timing
- Typing speed prediction based on emotion
- First/last segment handling

**Pause Factors:**
- Emotion state (excited = faster, sad/anxious = slower)
- Segment length (longer text = slightly longer pause)
- Position (first/last segment handling with variation)

### 5. Behavior Coordinator (`src/behavior/coordinator.py`)

**BehaviorCoordinator**
- Main orchestrator for all behavior components
- Processes messages through the full pipeline
- Configurable via `BehaviorConfig`

**Processing Pipeline:**
1. Detect emotion from text
2. Segment message into chunks and apply the postfix (trim trailing commas/periods)
3. For each segment:
   - Optionally inject typo (and decide whether it should be recalled)
   - Emit a `send` action (typo text first if needed)
   - Insert recall/pause actions when a typo is fixed
   - Append a random interval (`pause` action) before moving to the next segment
4. Return an ordered list of playback actions (`send`/`pause`/`recall`)

## API Integration

### Request Schema (`src/api/schemas.py`)

**ChatRequest:**
```python
{
    "llm_config": {
        "provider": "openai",
        "api_key": "sk-...",
        "model": "gpt-3.5-turbo",
        "system_prompt": "..."
    },
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "character_name": "Rie",
    "conversation_id": "conv-123",
    "behavior_settings": {  # Optional
        "enable_segmentation": true,
        "enable_typo": true,
        "enable_recall": true,
        "enable_emotion_detection": true,
        "min_pause_duration": 0.4,
        "max_pause_duration": 2.5,
        "base_typo_rate": 0.08,
        "typo_recall_rate": 0.4
    },
}
```

**ChatResponse:**
```python
{
    "actions": [
        {
            "type": "send",
            "duration": 0.0,
            "text": "你好！",
            "message_id": "a1b2c3",
            "metadata": {"segment_index": 0, "emotion": "happy"}
        },
        {
            "type": "pause",
            "duration": 0.8,
            "metadata": {"reason": "segment_interval"}
        },
        {
            "type": "send",
            "duration": 0.0,
            "text": "今天天气不错呢",
            "message_id": "d4e5f6",
            "metadata": {"segment_index": 1, "emotion": "happy"}
        }
    ],
    "raw_response": "你好！今天天气不错呢",
    "metadata": {
        "emotion": "happy",
        "emotion_map": {"happy": "high"},
        "segment_count": 2
    }
}
```

### Message Action Types

1. **send**: Display a chat bubble immediately (optionally track `message_id`)
2. **pause**: Wait silently for `duration`
3. **recall**: Remove/mark the message referenced by `target_id`

## Frontend Implementation

### Playback Timeline (`frontend/chat.js`)

The frontend plays the action list sequentially:

1. Wait for `duration` before rendering each action.
2. For `send` actions: append the assistant bubble and store `message_id` → DOM element mapping.
3. For `pause` actions: do nothing—the awaited delay already created the rhythm.
4. For `recall` actions: locate the DOM node by `target_id`, mark it as recalled, then remove it so the final history matches the post-recall state.

### Visual Features

- **Segment pacing**: Random pauses create natural rhythm without fake typing indicators
- **Recall effect**: Brief strikethrough before the bubble disappears
- **Emotion indicators**: Dynamic theme colors based on detected emotion map
- **Smooth scrolling**: Auto-scroll to latest message
- **Typing status**: Realistic "typing..." indicator with hesitation simulation

## LLM JSON Contract

The LLM is instructed via a fixed system prompt to respond **only** with JSON:

```json
{
  "emotion": {"happy": "medium", "excited": "high"},
  "reply": "好的，马上发给你～"
}
```

- `emotion`: dictionary of emotion → intensity (`low|medium|high|extreme`)
- `reply`: short, WeChat-style message without narration or inner thoughts
- The frontend prompt is treated as persona text; the backend injects history + system prompt automatically.

## Configuration

### Behavior Settings

All behavior can be controlled via `BehaviorConfig`:

```python
config = BehaviorConfig(
    enable_segmentation=True,      # Enable message segmentation
    enable_typo=True,               # Enable typo injection
    enable_recall=True,             # Enable recall behavior
    enable_emotion_detection=True,  # Enable emotion detection

    max_segment_length=50,          # Max chars per segment
    min_pause_duration=0.3,         # Min pause (seconds)
    max_pause_duration=2.5,         # Max pause (seconds)

    base_typo_rate=0.08,           # 8% base typo chance
    typo_recall_rate=0.4,          # 40% chance to recall typo
    recall_delay=1.5,              # Delay before recall
    retype_delay=0.8,              # Delay before correction
)
```

## Testing

Run tests with pytest:

```bash
pytest tests/ -v
```

Tests cover:
- Segmentation (rule-based)
- Emotion detection
- Typo injection
- Recall probability
- End-to-end behavior coordination

## Development Workflow

1. **Start backend**:
   ```bash
   python -m src.api.main
   ```

2. **Access frontend**: `http://localhost:8000`

3. **Test behavior**:
   - Configure LLM settings
   - Send messages
   - Observe segmentation, pauses, typos, recalls

4. **Adjust behavior**:
   - Modify `BehaviorConfig` in `routes.py`
   - Or send custom settings in API requests

## Future Enhancements

- [ ] Multi-character conversation support
- [ ] Conversation history persistence
- [ ] Character preset library
- [ ] Extended emotion types (shy, embarrassed, surprised, playful, etc.)
- [ ] User-adjustable behavior intensity settings
- [ ] Performance optimization for high-concurrency scenarios
- [ ] Mobile responsive design
