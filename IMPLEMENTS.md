# Rie-Kugimiya 技术实现文档

> 面向开发者的完整技术文档

## 📑 目录

- [系统架构](#系统架构)
- [核心模块](#核心模块)
- [数据流设计](#数据流设计)
- [配置系统](#配置系统)
- [消息服务器](#消息服务器)
- [行为引擎](#行为引擎)
- [Rin客户端](#rin客户端)
- [WebSocket通信](#websocket通信)
- [数据库设计](#数据库设计)
- [前端实现](#前端实现)
- [测试架构](#测试架构)
- [部署指南](#部署指南)

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Message Server                           │
│  ┌──────────────┐                  ┌──────────────────┐     │
│  │   SQLite DB  │◄─────────────────┤ MessageService   │     │
│  │              │                  │                  │     │
│  │  messages    │                  │  - CRUD操作      │     │
│  │  indexes     │                  │  - 事件创建      │     │
│  └──────────────┘                  │  - 输入状态管理  │     │
│                                    └────────┬─────────┘     │
│                                             │                │
│  ┌──────────────────────────────────────────▼──────────┐    │
│  │           WebSocketManager                          │    │
│  │                                                      │    │
│  │  - 连接管理: Dict[conv_id, Set[WebSocket]]         │    │
│  │  - 用户映射: Dict[WebSocket, user_id]              │    │
│  │  - 消息广播                                         │    │
│  │  - 连接隔离                                         │    │
│  └──────┬──────────────────────────────┬───────────────┘    │
└─────────┼──────────────────────────────┼────────────────────┘
          │                              │
          │ WebSocket                    │ WebSocket
          │ 双向通信                      │ 双向通信
          │                              │
    ┌─────▼──────┐                ┌─────▼────────────┐
    │   User     │                │   Rin Client     │
    │  (Browser) │                │                  │
    │            │                │  ┌─────────────┐ │
    │  - UI渲染  │                │  │ LLM Client  │ │
    │  - 事件接收│                │  └──────┬──────┘ │
    │  - 用户输入│                │         │        │
    └────────────┘                │  ┌──────▼──────┐ │
                                  │  │  Behavior   │ │
                                  │  │ Coordinator │ │
                                  │  └──────┬──────┘ │
                                  │         │        │
                                  │  ┌──────▼──────┐ │
                                  │  │  Timeline   │ │
                                  │  │  Builder    │ │
                                  │  └─────────────┘ │
                                  └──────────────────┘
```

### 设计理念

1. **完全前后端分离**
   - 前端：纯UI渲染，事件驱动
   - 后端：所有业务逻辑，包括行为模拟

2. **客户端平等原则**
   - User和Rin都是平等的客户端
   - 都通过WebSocket连接到消息服务器
   - 都遵循相同的通信协议

3. **事件驱动架构**
   - 所有状态变化通过事件通知
   - WebSocket消息即事件
   - 前端只负责响应事件更新UI

4. **时间戳行为序列**
   - 所有行为带绝对时间戳
   - 精确控制行为执行时间
   - 支持暂停/恢复/回放

5. **配置集中化**
   - 所有默认值集中管理
   - 支持环境变量覆盖
   - Pydantic类型安全

---

## 核心模块

### 模块结构

```
src/
├── config.py                      # 配置中心
├── api/                           # FastAPI后端
│   ├── main.py                   # 应用入口
│   ├── ws_routes.py              # WebSocket路由
│   ├── schemas.py                # Pydantic模型
│   └── llm_client.py             # LLM客户端
├── message_server/                # 消息服务器
│   ├── __init__.py
│   ├── models.py                 # 数据模型
│   ├── database.py               # SQLite数据库层
│   ├── service.py                # 业务逻辑层
│   └── websocket.py              # WebSocket管理器
├── behavior/                      # 行为引擎
│   ├── __init__.py
│   ├── models.py                 # 行为模型
│   ├── coordinator.py            # 行为协调器
│   ├── timeline.py               # 时间轴构建器
│   ├── segmenter.py              # 智能分段
│   ├── emotion.py                # 情绪检测
│   ├── typo.py                   # 错别字注入
│   └── pause.py                  # 停顿预测
└── rin_client/                    # Rin客户端
    ├── __init__.py
    └── client.py                 # Rin客户端逻辑
```

### 依赖关系

```python
# 核心依赖
FastAPI         # Web框架
Pydantic        # 数据验证和配置管理
SQLite3         # 数据库
HTTPX           # 异步HTTP客户端
Uvicorn         # ASGI服务器

# 行为引擎依赖
无外部依赖，纯Python实现
```

---

## 数据流设计

### 用户发送消息流程

```
1. 用户在前端输入消息
   └─> Frontend: ws.send({type: "message", content: "..."})

2. WebSocket服务器接收
   └─> ws_routes.py: handle_user_message()
       └─> 创建Message对象
       └─> MessageService.save_message()
           └─> MessageDatabase.save_message()
               └─> SQLite INSERT

3. 广播给所有客户端
   └─> WebSocketManager.send_to_conversation()
       └─> 遍历conversation的所有WebSocket
       └─> websocket.send_json(message_event)

4. Rin客户端接收并处理
   └─> RinClient.process_user_message()
       └─> 获取对话历史
       └─> 调用LLM
       └─> 生成行为时间轴
       └─> 执行时间轴
```

### Rin回复流程

```
1. Rin客户端处理
   └─> RinClient.process_user_message()
       └─> MessageService.get_messages() - 获取历史
       └─> LLMClient.chat() - 调用LLM
       └─> BehaviorCoordinator.process_message() - 生成行为
           └─> Segmenter.segment() - 分段
           └─> EmotionDetector.detect() - 情绪检测
           └─> TypoInjector.inject_typo() - 错别字
           └─> TimelineBuilder.build_timeline() - 构建时间轴
               └─> _generate_hesitation_sequence() - 迟疑
               └─> _sample_initial_delay() - 初始延迟
               └─> _calculate_typing_lead_time() - 输入前导时间

2. 执行时间轴
   └─> RinClient._execute_timeline()
       └─> 遍历timeline中的每个action
       └─> 根据timestamp计算等待时间
       └─> asyncio.sleep(wait_time)
       └─> 执行对应action:
           ├─> typing_start: 发送输入状态事件
           ├─> typing_end: 结束输入状态
           ├─> send: 保存消息并广播
           ├─> recall: 撤回消息并广播
           └─> wait: 纯等待

3. 每个行为都通过WebSocket广播
   └─> WebSocketManager.send_to_conversation()
       └─> 所有连接的客户端（包括User）收到事件
       └─> 前端更新UI
```

### 增量同步流程

```
1. 前端发送sync请求
   └─> ws.send({type: "sync", after_timestamp: last_timestamp})

2. 服务器处理
   └─> handle_sync()
       └─> MessageService.get_messages(after_timestamp=...)
       └─> 只返回新消息

3. 前端接收并合并
   └─> 去重（基于message_id）
   └─> 更新本地存储
   └─> 更新UI
```

---

## 配置系统

### 配置文件: `src/config.py`

所有配置集中在一个文件中，使用Pydantic Settings管理。

#### AppConfig - 应用配置

```python
class AppConfig(BaseSettings):
    app_name: str = "Yuzuriha Rin Virtual Chat"
    debug: bool = True
    cors_origins: list = ["*"]

    class Config:
        env_file = ".env"
```

#### CharacterConfig - 角色配置

```python
class CharacterConfig(BaseSettings):
    default_name: str = "Rin"
    default_persona: str = "You are a helpful assistant."

    class Config:
        env_prefix = "CHARACTER_"
```

#### LLMDefaults - LLM默认配置

```python
class LLMDefaults(BaseSettings):
    provider: str = "openai"
    model_openai: str = "gpt-3.5-turbo"
    model_anthropic: str = "claude-3-5-sonnet-20241022"
    model_deepseek: str = "deepseek-chat"
    model_custom: str = "gpt-3.5-turbo"
```

#### BehaviorDefaults - 行为系统配置

```python
class BehaviorDefaults(BaseSettings):
    # 开关
    enable_segmentation: bool = True
    enable_typo: bool = True
    enable_recall: bool = True
    enable_emotion_detection: bool = True

    # 分段
    max_segment_length: int = 50

    # 停顿
    min_pause_duration: float = 0.4
    max_pause_duration: float = 2.5

    # 错别字
    base_typo_rate: float = 0.08
    typo_recall_rate: float = 0.4
    recall_delay: float = 1.2
    retype_delay: float = 0.6

    # 情绪影响
    emotion_typo_multiplier: Dict[str, float] = {
        "neutral": 1.0,
        "happy": 0.8,
        "excited": 1.5,
        "sad": 1.2,
        "angry": 1.8,
        "anxious": 2.0,
        "confused": 1.3,
    }
```

#### TypingStateDefaults - 输入状态配置

```python
class TypingStateDefaults(BaseSettings):
    # 迟疑系统
    hesitation_probability: float = 0.15
    hesitation_cycles_min: int = 1
    hesitation_cycles_max: int = 2
    hesitation_duration_min: int = 400   # ms
    hesitation_duration_max: int = 1200  # ms
    hesitation_gap_min: int = 300        # ms
    hesitation_gap_max: int = 900        # ms

    # 输入前导时间（根据文本长度）
    typing_lead_time_threshold_1: int = 15   # 字符
    typing_lead_time_1: int = 600            # ms
    typing_lead_time_threshold_2: int = 30
    typing_lead_time_2: int = 800
    typing_lead_time_threshold_3: int = 60
    typing_lead_time_3: int = 1100
    typing_lead_time_threshold_4: int = 100
    typing_lead_time_4: int = 1600
    typing_lead_time_threshold_5: int = 140
    typing_lead_time_5: int = 2200
    typing_lead_time_default: int = 2500

    # 初始延迟概率分布
    initial_delay_weight_1: float = 0.45
    initial_delay_range_1_min: int = 3   # 秒
    initial_delay_range_1_max: int = 4
    initial_delay_weight_2: float = 0.75
    initial_delay_range_2_min: int = 4
    initial_delay_range_2_max: int = 6
    initial_delay_weight_3: float = 0.93
    initial_delay_range_3_min: int = 6
    initial_delay_range_3_max: int = 8
    initial_delay_range_4_min: int = 8
    initial_delay_range_4_max: int = 10
```

#### 使用方式

```python
from src.config import behavior_defaults, typing_state_defaults

# 直接使用
typo_rate = behavior_defaults.base_typo_rate

# 环境变量覆盖
# export BEHAVIOR_BASE_TYPO_RATE=0.1
# export TYPING_HESITATION_PROBABILITY=0.2
```

---

## 消息服务器

### 数据模型: `src/message_server/models.py`

#### Message - 消息模型

```python
class MessageType(str, Enum):
    TEXT = "text"
    RECALLED = "recalled"
    SYSTEM = "system"

class Message(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    type: MessageType = MessageType.TEXT
    content: str
    timestamp: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True  # 自动转换枚举为字符串值
```

#### TypingState - 输入状态

```python
class TypingState(BaseModel):
    user_id: str
    conversation_id: str
    is_typing: bool
    timestamp: float
```

#### WSMessage - WebSocket消息封装

```python
class WSMessage(BaseModel):
    type: str  # message/typing/recall/clear/history
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None

    def model_dump(self, **kwargs):
        result = super().model_dump(**kwargs)
        if result.get('timestamp') is None:
            result['timestamp'] = datetime.now().timestamp()
        return result
```

### 数据库层: `src/message_server/database.py`

#### 数据库架构

```sql
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversation_timestamp
ON messages(conversation_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_sender
ON messages(sender_id);
```

#### 核心方法

```python
class MessageDatabase:
    def save_message(self, message: Message) -> bool:
        """保存消息到数据库"""
        # 使用INSERT INTO插入消息
        # metadata序列化为JSON字符串

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        after_timestamp: Optional[float] = None
    ) -> List[Message]:
        """查询消息，支持增量查询"""
        # WHERE conversation_id = ? AND timestamp > ?
        # ORDER BY timestamp ASC
        # LIMIT ?

    def recall_message(self, message_id: str, conversation_id: str) -> bool:
        """撤回消息"""
        # UPDATE messages SET type = 'recalled', content = ''
        # WHERE id = ? AND conversation_id = ?

    def clear_conversation(self, conversation_id: str) -> bool:
        """清空会话"""
        # DELETE FROM messages WHERE conversation_id = ?

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """根据ID查询单条消息"""
```

### 服务层: `src/message_server/service.py`

#### 核心职责

1. 封装数据库操作为async接口
2. 管理输入状态（内存，不持久化）
3. 创建标准化的WebSocket事件

```python
class MessageService:
    def __init__(self, db_path: str = None):
        self.db = MessageDatabase(db_path)
        self.typing_states: Dict[str, TypingState] = {}  # 内存存储

    async def save_message(self, message: Message) -> Message:
        """异步保存消息"""

    async def get_messages(...) -> List[Message]:
        """异步查询消息"""

    async def set_typing_state(self, typing_state: TypingState):
        """设置输入状态"""
        key = f"{typing_state.conversation_id}:{typing_state.user_id}"
        if typing_state.is_typing:
            self.typing_states[key] = typing_state
        else:
            self.typing_states.pop(key, None)

    def create_message_event(self, message: Message) -> WSMessage:
        """创建消息事件"""
        return WSMessage(type="message", data={...})

    def create_typing_event(self, typing_state: TypingState) -> WSMessage:
        """创建输入状态事件"""

    def create_recall_event(...) -> WSMessage:
        """创建撤回事件"""

    def create_history_event(self, messages: List[Message]) -> WSMessage:
        """创建历史消息事件"""
```

### WebSocket管理器: `src/message_server/websocket.py`

```python
class WebSocketManager:
    def __init__(self):
        # conversation_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user_id
        self.user_websockets: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        # 添加到对应会话的连接集合

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        """断开连接并清理"""
        # 从集合中移除
        # 清理user_websockets映射

    async def send_to_conversation(
        self,
        conversation_id: str,
        message: dict,
        exclude_ws: WebSocket = None
    ):
        """发送消息给会话中的所有客户端"""
        # 遍历conversation的所有WebSocket
        # 跳过exclude_ws（如果指定）
        # 发送失败的自动移除

    async def send_to_websocket(self, websocket: WebSocket, message: dict):
        """发送消息给单个WebSocket"""

    def get_user_id(self, websocket: WebSocket) -> str:
        """获取WebSocket对应的用户ID"""

    def get_conversation_connections(self, conversation_id: str) -> Set[WebSocket]:
        """获取会话的所有连接"""
```

---

## 行为引擎

### 行为模型: `src/behavior/models.py`

```python
class EmotionState(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CONFUSED = "confused"

class PlaybackAction(BaseModel):
    type: Literal["send", "pause", "recall", "typing_start", "typing_end", "wait"]
    timestamp: float = Field(default=0.0, ge=0.0)  # 绝对时间戳（秒）
    duration: float = Field(default=0.0, ge=0.0)   # 持续时间（秒）
    text: Optional[str] = None                      # send类型的文本
    message_id: Optional[str] = None                # send的消息ID
    target_id: Optional[str] = None                 # recall的目标消息ID
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BehaviorConfig(BaseModel):
    """行为配置"""
    enable_segmentation: bool = True
    enable_typo: bool = True
    enable_recall: bool = True
    enable_emotion_detection: bool = True
    max_segment_length: int = 50
    min_pause_duration: float = 0.4
    max_pause_duration: float = 2.5
    base_typo_rate: float = 0.08
    typo_recall_rate: float = 0.4
    recall_delay: float = 1.2
    retype_delay: float = 0.6
    emotion_typo_multiplier: Dict[str, float] = {
        "neutral": 1.0,
        "happy": 0.8,
        "excited": 1.5,
        # ...
    }
```

### 行为协调器: `src/behavior/coordinator.py`

```python
class BehaviorCoordinator:
    """
    整合所有行为模块，生成完整的行为时间轴
    """

    def __init__(self, config: BehaviorConfig = None):
        self.segmenter = SmartSegmenter()
        self.emotion_detector = EmotionDetector()
        self.typo_injector = TypoInjector()
        self.pause_predictor = PausePredictor()
        self.timeline_builder = TimelineBuilder()

    def process_message(self, text: str, emotion_map: dict = None) -> List[PlaybackAction]:
        """
        处理消息并生成时间轴

        流程:
        1. 检测情绪
        2. 分段
        3. 对每个分段:
           - 错别字注入
           - 生成send action
           - 如果有错别字且需要撤回，生成撤回序列
           - 生成分段间隔pause
        4. 通过TimelineBuilder转换为带时间戳的时间轴
        """

        # 情绪检测
        emotion = self._detect_emotion(text, emotion_map)

        # 分段
        segments = self._segment_and_clean(text)

        # 为每个分段生成actions
        actions = []
        for index, segment in enumerate(segments):
            actions.extend(
                self._build_actions_for_segment(
                    segment, index, len(segments), emotion
                )
            )

        # 转换为时间轴
        timeline = self.timeline_builder.build_timeline(actions)
        return timeline
```

### 时间轴构建器: `src/behavior/timeline.py`

```python
class TimelineBuilder:
    """
    将相对duration的actions转换为绝对timestamp的timeline
    """

    def build_timeline(self, actions: List[PlaybackAction]) -> List[PlaybackAction]:
        """
        构建时间轴

        流程:
        1. 生成迟疑序列（15%概率，1-2轮）
        2. 添加初始延迟（3-10秒，概率分布）
        3. 遍历actions:
           - 对send action:
             * 添加typing_start
             * 添加typing_lead_time等待
             * 添加send
             * 决定是否typing_end
           - 对pause action:
             * 转换为wait
           - 对recall action:
             * 确保先typing_end
             * 添加recall
        4. 所有action都带上绝对timestamp

        返回: 按时间戳排序的完整行为序列
        """

    def _generate_hesitation_sequence(self) -> List[PlaybackAction]:
        """
        生成迟疑序列

        概率: 15%
        循环次数: 1-2
        每轮:
          - typing_start
          - wait (400-1200ms)
          - typing_end
          - 可能的间隔gap (300-900ms, 30%概率)
        """

    def _sample_initial_delay(self) -> float:
        """
        采样初始延迟

        概率分布:
        - 45%: 3-4秒
        - 30%: 4-6秒
        - 18%: 6-8秒
        - 7%: 8-10秒
        """

    def _calculate_typing_lead_time(self, text_length: int) -> float:
        """
        根据文本长度计算输入前导时间

        分段:
        - <=15字符: 600ms
        - 15-30: 800ms
        - 30-60: 1100ms
        - 60-100: 1600ms
        - 100-140: 2200ms
        - >140: 2500ms
        """
```

### 智能分段器: `src/behavior/segmenter.py`

```python
class SmartSegmenter:
    """
    基于标点符号的智能分段
    """

    def segment(self, text: str) -> List[str]:
        """
        分段逻辑:
        1. 按句号、问号、感叹号强制分割
        2. 对过长的句子，按逗号分割
        3. 仍过长的，按max_length硬切
        """
```

### 情绪检测器: `src/behavior/emotion.py`

```python
class EmotionDetector:
    """
    情绪检测（基于LLM返回的emotion_map）
    """

    def detect(self, emotion_map: dict = None, fallback_text: str = "") -> EmotionState:
        """
        检测情绪

        优先级:
        1. emotion_map中强度最高的情绪
        2. fallback_text的简单规则匹配
        3. 默认neutral
        """
```

### 错别字注入器: `src/behavior/typo.py`

```python
class TypoInjector:
    """
    错别字注入和撤回决策
    """

    def inject_typo(self, text: str, typo_rate: float) -> Tuple[bool, str, int, str]:
        """
        注入错别字

        方法:
        - 随机选择一个字符
        - 替换为相似字符（同音字、形似字等）

        返回: (有错别字, 错别字文本, 位置, 原字符)
        """

    def should_recall_typo(self, recall_rate: float) -> bool:
        """是否撤回错别字"""
```

### 停顿预测器: `src/behavior/pause.py`

```python
class PausePredictor:
    """
    分段间隔停顿预测
    """

    def segment_interval(
        self,
        emotion: EmotionState,
        min_duration: float,
        max_duration: float
    ) -> float:
        """
        预测分段间隔

        策略:
        - 基础: min_duration到max_duration的随机值
        - 情绪调整: excited可能更短，sad可能更长
        """
```

---

## Rin客户端

### 客户端架构: `src/rin_client/client.py`

```python
class RinClient:
    """
    Rin作为独立客户端，连接到消息服务器
    """

    def __init__(
        self,
        message_service: MessageService,
        ws_manager: WebSocketManager,
        llm_config: dict,
        behavior_config: Optional[BehaviorConfig] = None
    ):
        self.message_service = message_service
        self.ws_manager = ws_manager
        self.llm_client = LLMClient(llm_config)
        self.coordinator = BehaviorCoordinator(behavior_config)
        self.user_id = "rin"
        self._running = False
        self._tasks = []

    async def start(self, conversation_id: str):
        """启动Rin客户端"""
        self._running = True

    async def stop(self):
        """停止Rin客户端"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await self.llm_client.close()

    async def process_user_message(self, user_message: Message):
        """
        处理用户消息并生成回复

        流程:
        1. 从数据库获取对话历史
        2. 调用LLM生成回复
        3. 行为系统生成时间轴
        4. 异步执行时间轴
        """

        # 获取历史
        history = await self.message_service.get_messages(
            user_message.conversation_id
        )

        # 构建对话历史
        conversation_history = []
        for msg in history:
            if msg.type == MessageType.TEXT:
                role = "assistant" if msg.sender_id == self.user_id else "user"
                conversation_history.append({
                    "role": role,
                    "content": msg.content
                })

        # 调用LLM
        llm_response = await self.llm_client.chat(
            conversation_history,
            character_name=self.character_name
        )

        # 生成时间轴
        timeline = self.coordinator.process_message(
            llm_response.reply,
            emotion_map=llm_response.emotion_map
        )

        # 异步执行
        task = asyncio.create_task(
            self._execute_timeline(timeline, user_message.conversation_id)
        )
        self._tasks.append(task)

    async def _execute_timeline(self, timeline: List[PlaybackAction], conversation_id: str):
        """
        执行时间轴

        核心逻辑:
        1. 记录开始时间
        2. 遍历timeline中的每个action
        3. 计算scheduled_time = start_time + action.timestamp
        4. wait_time = scheduled_time - current_time
        5. await asyncio.sleep(wait_time)
        6. 执行action对应的操作
        """

        start_time = datetime.now().timestamp()

        for action in timeline:
            if not self._running:
                break

            # 计算等待时间
            scheduled_time = start_time + action.timestamp
            current_time = datetime.now().timestamp()
            wait_time = max(0, scheduled_time - current_time)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # 执行action
            if action.type == "typing_start":
                await self._send_typing_state(conversation_id, True)

            elif action.type == "typing_end":
                await self._send_typing_state(conversation_id, False)

            elif action.type == "send":
                await self._send_typing_state(conversation_id, False)
                await self._send_message(
                    conversation_id,
                    action.text,
                    action.message_id,
                    action.metadata
                )

            elif action.type == "recall":
                await self._send_typing_state(conversation_id, False)
                await self._recall_message(conversation_id, action.target_id)

            elif action.type == "wait":
                pass  # 纯等待，不做任何操作

    async def _send_typing_state(self, conversation_id: str, is_typing: bool):
        """发送输入状态"""
        typing_state = TypingState(...)
        await self.message_service.set_typing_state(typing_state)

        event = self.message_service.create_typing_event(typing_state)
        await self.ws_manager.send_to_conversation(
            conversation_id,
            event.model_dump()
        )

    async def _send_message(self, conversation_id: str, content: str, ...):
        """发送消息"""
        message = Message(...)
        await self.message_service.save_message(message)

        event = self.message_service.create_message_event(message)
        await self.ws_manager.send_to_conversation(
            conversation_id,
            event.model_dump()
        )

    async def _recall_message(self, conversation_id: str, message_id: str):
        """撤回消息"""
        await self.message_service.recall_message(message_id, conversation_id)

        event = self.message_service.create_recall_event(...)
        await self.ws_manager.send_to_conversation(...)
```

---

## WebSocket通信

### 路由定义: `src/api/ws_routes.py`

```python
@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str = Query(default="user")
):
    """
    WebSocket连接端点

    1. 接受连接
    2. 发送历史消息
    3. 循环接收并处理客户端消息
    4. 捕获断开连接并清理
    """

    await ws_manager.connect(websocket, conversation_id, user_id)

    try:
        # 发送历史消息
        history = await message_service.get_messages(conversation_id)
        history_event = message_service.create_history_event(history)
        await ws_manager.send_to_websocket(websocket, history_event.model_dump())

        # 消息循环
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, conversation_id, user_id, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, conversation_id)
        await message_service.clear_user_typing_state(user_id, conversation_id)

    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, conversation_id)
```

### 消息处理器

```python
async def handle_client_message(websocket, conversation_id, user_id, data):
    """
    路由客户端消息到对应的处理器
    """
    msg_type = data.get("type")

    if msg_type == "sync":
        await handle_sync(...)           # 增量同步
    elif msg_type == "message":
        await handle_user_message(...)   # 用户消息
    elif msg_type == "typing":
        await handle_typing_state(...)   # 输入状态
    elif msg_type == "recall":
        await handle_recall(...)         # 撤回消息
    elif msg_type == "clear":
        await handle_clear(...)          # 清空对话
    elif msg_type == "init_rin":
        await handle_init_rin(...)       # 初始化Rin
```

### 消息协议

#### 客户端 -> 服务器

```javascript
// 1. 用户消息
{
    type: "message",
    id: "msg-uuid",
    content: "Hello",
    metadata: {}
}

// 2. 输入状态
{
    type: "typing",
    is_typing: true
}

// 3. 撤回消息
{
    type: "recall",
    message_id: "msg-uuid"
}

// 4. 清空对话
{
    type: "clear"
}

// 5. 增量同步
{
    type: "sync",
    after_timestamp: 1234567890.123
}

// 6. 初始化Rin
{
    type: "init_rin",
    llm_config: {
        provider: "openai",
        api_key: "...",
        model: "gpt-3.5-turbo",
        persona: "..."
    }
}
```

#### 服务器 -> 客户端

```javascript
// 1. 消息事件
{
    type: "message",
    data: {
        id: "msg-uuid",
        conversation_id: "conv-1",
        sender_id: "rin",
        type: "text",
        content: "Hello!",
        timestamp: 1234567890.123,
        metadata: {}
    },
    timestamp: 1234567890.123
}

// 2. 输入状态事件
{
    type: "typing",
    data: {
        user_id: "rin",
        conversation_id: "conv-1",
        is_typing: true
    },
    timestamp: 1234567890.123
}

// 3. 撤回事件
{
    type: "recall",
    data: {
        message_id: "msg-uuid",
        conversation_id: "conv-1"
    },
    timestamp: 1234567890.123
}

// 4. 清空事件
{
    type: "clear",
    data: {
        conversation_id: "conv-1"
    },
    timestamp: 1234567890.123
}

// 5. 历史消息事件
{
    type: "history",
    data: {
        messages: [
            {...},
            {...}
        ]
    },
    timestamp: 1234567890.123
}
```

---

## 数据库设计

### 表结构

```sql
messages
--------
id              TEXT PRIMARY KEY
conversation_id TEXT NOT NULL
sender_id       TEXT NOT NULL
type            TEXT NOT NULL
content         TEXT NOT NULL
timestamp       REAL NOT NULL
metadata        TEXT
created_at      DATETIME DEFAULT CURRENT_TIMESTAMP

索引:
- idx_conversation_timestamp (conversation_id, timestamp)
- idx_sender (sender_id)
```

### 设计决策

1. **使用SQLite**
   - 轻量级，无需独立服务器
   - 单文件存储，易于备份
   - 支持并发读，单写锁

2. **timestamp使用REAL类型**
   - 存储Unix时间戳（秒，浮点数）
   - 支持毫秒精度
   - 便于范围查询和排序

3. **metadata存储为JSON字符串**
   - 灵活扩展
   - 无需更改表结构即可添加新字段

4. **索引设计**
   - (conversation_id, timestamp): 支持快速查询会话消息
   - sender_id: 支持查询特定用户的所有消息

5. **消息撤回设计**
   - 不删除记录
   - 更改type为"recalled"
   - 清空content
   - 保留metadata和timestamp

---

## 前端实现

### WebSocket客户端: `frontend/chat_ws.js`

```javascript
class ChatApp {
    constructor() {
        this.ws = null;
        this.sessionId = 'default';
        this.messageMap = new Map();  // message_id -> message
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/${this.sessionId}?user_id=user`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed');
            // 重连逻辑
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleServerMessage(data) {
        const handlers = {
            'history': this.handleHistory.bind(this),
            'message': this.handleMessage.bind(this),
            'typing': this.handleTyping.bind(this),
            'recall': this.handleRecall.bind(this),
            'clear': this.handleClear.bind(this)
        };

        const handler = handlers[data.type];
        if (handler) {
            handler(data);
        }
    }

    handleHistory(data) {
        // 加载历史消息
        data.data.messages.forEach(msg => {
            this.messageMap.set(msg.id, msg);
            this.addMessageToUI(msg);
        });
    }

    handleMessage(data) {
        // 去重
        if (this.messageMap.has(data.data.id)) {
            return;
        }

        this.messageMap.set(data.data.id, data.data);
        this.addMessageToUI(data.data);
    }

    handleTyping(data) {
        // 更新输入状态UI
        const isTyping = data.data.is_typing;
        const userId = data.data.user_id;

        if (userId !== 'user') {
            this.updateTypingIndicator(isTyping);
        }
    }

    handleRecall(data) {
        // 撤回消息
        const messageId = data.data.message_id;
        const msgElement = document.getElementById(`msg-${messageId}`);

        if (msgElement) {
            msgElement.classList.add('recalled');
            msgElement.querySelector('.message-content').textContent = '[消息已撤回]';
        }
    }

    handleClear(data) {
        // 清空对话
        this.messageMap.clear();
        this.clearUI();
    }

    sendMessage(content) {
        const message = {
            type: 'message',
            id: `msg-${Date.now()}`,
            content: content,
            metadata: {}
        };

        this.ws.send(JSON.stringify(message));
    }

    initRin(llmConfig) {
        const message = {
            type: 'init_rin',
            llm_config: llmConfig
        };

        this.ws.send(JSON.stringify(message));
    }
}
```

### UI更新策略

1. **事件驱动**
   - 所有UI更新响应WebSocket事件
   - 不直接修改状态，只响应事件

2. **消息去重**
   - 使用Map存储消息（message_id -> message）
   - 收到消息前检查是否已存在

3. **输入状态指示器**
   - 监听typing事件
   - 显示/隐藏"正在输入..."提示

4. **撤回动画**
   - 添加CSS类
   - 淡出效果
   - 替换为"消息已撤回"

---

## 测试架构

### 测试结构

```
tests/
├── __init__.py
├── run_all_tests.py           # 测试运行器
├── test_config.py              # 配置测试
├── test_database.py            # 数据库测试
├── test_message_service.py     # 消息服务测试
├── test_behavior_system.py     # 行为系统测试
├── test_websocket_manager.py   # WebSocket管理器测试
└── test_integration.py         # 集成测试
```

### 测试覆盖

#### 配置测试 (8个测试)
- 所有配置类的字段验证
- 范围检查（min < max）
- 概率值在[0,1]
- 阈值递增性

#### 数据库测试 (8个测试)
- 数据库初始化
- CRUD操作
- 增量查询（after_timestamp）
- 消息撤回
- 会话清空
- 多会话隔离

#### 消息服务测试 (5个测试)
- 异步消息保存和查询
- 输入状态管理
- 事件创建
- 增量同步

#### 行为系统测试 (9个测试)
- 行为协调器
- 智能分段
- 情绪检测
- 错别字注入
- 撤回决策
- 停顿预测
- 时间轴构建
- 时间戳验证

#### WebSocket管理器测试 (8个测试)
- 连接和断开
- 多连接管理
- 消息广播
- 排除特定客户端
- 连接查询
- 异常处理

#### 集成测试 (7个测试)
- 完整消息流
- 行为到消息流
- 输入状态流
- 撤回流
- 增量同步流
- 多会话隔离
- 时间轴执行模拟

### 测试统计

```
总测试数: 45
通过: 45
失败: 0
覆盖率: 100%
```

### 运行测试

```bash
# 运行所有测试
python tests/run_all_tests.py

# 运行单个模块
python tests/test_config.py
python tests/test_database.py
```

---

## 部署指南

### 环境要求

```
Python >= 3.10
uv (推荐) 或 pip
SQLite3 (Python内置)
```

### 安装依赖

```bash
# 使用uv (推荐)
uv pip install -e .

# 使用pip
pip install -e .
```

### 配置环境变量

创建`.env`文件:

```bash
# 应用配置
APP_NAME="Yuzuriha Rin Virtual Chat"
DEBUG=true

# 角色配置
CHARACTER_DEFAULT_NAME="Rin"
CHARACTER_DEFAULT_PERSONA="You are a helpful assistant."

# LLM配置
LLM_PROVIDER="openai"
LLM_MODEL_OPENAI="gpt-3.5-turbo"
LLM_MODEL_DEEPSEEK="deepseek-chat"

# 行为配置
BEHAVIOR_BASE_TYPO_RATE=0.08
BEHAVIOR_ENABLE_SEGMENTATION=true

# WebSocket配置
WS_HOST="0.0.0.0"
WS_PORT=8000

# 数据库配置
DB_PATH="data/messages.db"
```

### 启动服务

```bash
# 开发模式
python -m src.api.main

# 或使用uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 访问应用

```
http://localhost:8000
```

### Docker部署 (可选)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv pip install -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t rie-kugimiya .
docker run -p 8000:8000 -v $(pwd)/data:/app/data rie-kugimiya
```

### 数据备份

```bash
# 备份数据库
cp data/messages.db data/messages.db.backup

# 恢复
cp data/messages.db.backup data/messages.db
```

---

## 性能优化

### 数据库优化

1. **索引优化**
   - (conversation_id, timestamp) 复合索引
   - sender_id 单列索引

2. **查询优化**
   - 使用LIMIT限制返回数量
   - 使用after_timestamp进行增量查询
   - 避免SELECT *，只查询需要的字段

3. **连接池**
   - 使用contextmanager管理连接
   - 及时关闭连接

### WebSocket优化

1. **连接管理**
   - 使用Set存储连接，O(1)查找
   - 断开时自动清理

2. **消息广播**
   - 异步并发发送
   - 失败的连接自动移除

3. **心跳检测**
   - 配置ping_interval和ping_timeout
   - 自动清理僵尸连接

### 行为引擎优化

1. **缓存机制**
   - 情绪检测结果缓存
   - 分段结果缓存

2. **异步执行**
   - timeline执行使用asyncio
   - 不阻塞主线程

---

## 故障排查

### 常见问题

#### 1. WebSocket连接失败

```python
# 检查端口占用
lsof -i :8000

# 检查CORS配置
# 确保cors_origins包含前端域名
```

#### 2. 数据库锁定

```python
# SQLite只支持单写
# 确保没有长时间持有连接
# 使用contextmanager及时释放连接
```

#### 3. LLM调用超时

```python
# 增加超时时间
# 检查API密钥是否有效
# 检查网络连接
```

#### 4. 消息丢失

```python
# 检查WebSocket是否正常连接
# 检查数据库是否正常写入
# 检查日志输出
```

### 日志调试

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看WebSocket消息
# 在ws_routes.py中添加print语句

# 查看数据库操作
# 在database.py中添加print语句
```

---

## 未来扩展

### 短期计划

1. **性能监控**
   - 添加Prometheus指标
   - 监控WebSocket连接数
   - 监控消息延迟

2. **日志系统**
   - 结构化日志（JSON格式）
   - 日志轮转
   - 错误告警

3. **数据库迁移**
   - 使用Alembic管理schema变更
   - 版本化迁移脚本

### 中期计划

1. **多角色支持**
   - 多个Rin实例
   - 角色切换
   - 角色配置持久化

2. **对话管理**
   - 对话列表
   - 对话搜索
   - 对话导出

3. **前端优化**
   - 虚拟滚动（大量消息）
   - 图片支持
   - 代码高亮

### 长期计划

1. **分布式部署**
   - Redis作为消息中间件
   - 多实例负载均衡
   - Session sticky

2. **语音支持**
   - TTS（文本转语音）
   - STT（语音转文本）

3. **移动端**
   - React Native应用
   - 推送通知
   - 离线支持

---

## 贡献指南

### 代码规范

1. **Python风格**
   - 遵循PEP 8
   - 使用类型注解
   - 文档字符串

2. **提交规范**
   - feat: 新功能
   - fix: 修复bug
   - refactor: 重构
   - docs: 文档
   - test: 测试

3. **测试要求**
   - 新功能必须有测试
   - 测试覆盖率 >= 80%
   - 集成测试通过

### 开发流程

1. Fork仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交PR
5. 代码审查
6. 合并到主分支

---

## 许可证

MIT License

---

**文档版本**: 1.0.0
**最后更新**: 2025-12-09
**维护者**: Leever
