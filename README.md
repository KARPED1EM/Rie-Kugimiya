# Yuzuriha Rin（楪鈴） - 虚拟角色对话系统

一个基于大语言模型的虚拟角色对话系统，通过智能规则引擎模拟真人发消息的行为模式，包括分段、停顿、错别字、撤回重发等自然对话行为，让AI对话更加生动真实。

## ✨ 功能特点

- 🤖 **多LLM支持** - 支持DeepSeek、OpenAI、Anthropic及自定义OpenAI兼容API
- 🔌 **WebSocket实时通信** - 真正的实时双向通信架构
- 💬 **消息持久化** - SQLite本地数据库存储，刷新页面不丢失消息
- ⚙️ **配置集中化** - 统一配置管理，所有默认值集中定义
- 🎭 **前后端职责分离** - 所有行为逻辑在后端计算，前端仅负责UI渲染
- 🤖 **Rin独立客户端** - Rin作为独立客户端，与用户平等通信
- 🧠 **消息行为建模** - 智能分段、输入状态、迟疑系统完整模拟
- ✏️ **错别字注入** - 基于情绪的自然错别字模拟和智能撤回
- ↩️ **撤回重发** - 模拟真人发现错误后的撤回行为
- 📊 **情感分析** - LLM驱动的实时情绪检测
- ⏱️ **时间戳行为序列** - 所有行为带时间戳，精确模拟真实时间线

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│               Message Server                    │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │   SQLite DB  │◄────────┤ MessageService  │  │
│  └──────────────┘         └────────┬────────┘  │
│                                    │            │
│  ┌──────────────────────────────────▼─────────┐ │
│  │        WebSocket Manager                   │ │
│  └──────┬───────────────────────────┬─────────┘ │
└─────────┼───────────────────────────┼───────────┘
          │                           │
    ┌─────▼──────┐            ┌──────▼──────┐
    │   User     │            │ Rin Client  │
    │  (Browser) │            │             │
    └────────────┘            └──────┬──────┘
                                     │
                              ┌──────▼──────────┐
                              │  LLM + Behavior │
                              │  ├─ Segmenter   │
                              │  ├─ Emotion     │
                              │  ├─ Typo        │
                              │  ├─ Timeline    │
                              │  └─ Coordinator │
                              └─────────────────┘
```

**架构特点**:

- 用户和Rin都是平等的客户端，通过消息服务器通信
- 所有消息持久化到SQLite数据库
- Rin客户端独立运行，根据时间戳执行行为序列
- 前端只负责接收WebSocket事件并更新UI
- 输入状态、迟疑、所有行为逻辑都在后端完成

## 🛠️ 技术栈

**前端**

- 原生HTML + CSS + JavaScript
- WebSocket客户端实时通信
- 事件驱动的UI更新机制

**后端**

- FastAPI - 现代化异步Web框架，支持WebSocket
- Pydantic - 数据验证和配置管理
- SQLite - 轻量级本地数据库
- HTTPX - 异步HTTP客户端

**消息服务器**

- WebSocket实时双向通信
- SQLite消息持久化
- 输入状态管理（不持久化）
- 事件广播机制

**行为引擎**

- 时间轴构建器（Timeline Builder）
- 智能分段算法
- 迟疑系统模拟
- 输入状态管理
- 情绪感知的停顿和错别字系统
- 概率模型模拟真实聊天行为

## 📦 安装

### 环境要求

- Python 3.10+
- uv 包管理器（推荐）或 pip

## 🚀 快速开始

### 1. 启动后端服务

```bash
# 方式1: 直接运行
python -m src.api.main

# 方式2: 使用uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 访问Web界面

打开浏览器访问 `http://localhost:8000`

### 3. 配置LLM

在配置面板中填入：

- **Provider**: 选择 DeepSeek/OpenAI/Anthropic/Custom
  - 🌟 **推荐国内用户**: DeepSeek (快速、便宜、中文好)
- **API Key**: 你的API密钥
- **Model**: 模型名称
  - DeepSeek: `deepseek-chat`
  - OpenAI: `gpt-3.5-turbo`
  - Anthropic: `claude-3-5-sonnet-20241022`
- **角色人设**: 自定义角色性格和说话风格
- **Character Name**: 角色显示名称

### 4. 开始对话

保存配置后即可开始与虚拟角色聊天！

## 🧪 测试与故障排除

### 服务器连接测试

运行测试脚本验证服务器是否正常工作：

```bash
python test_server.py
```

如果显示 `✅ Server is running correctly!`，说明服务器正常运行。

### WebSocket 连接问题

如果前端无法连接 WebSocket，请检查：

1. **使用正确的 URL**
   - ✅ 正确：`http://localhost:8000`
   - ❌ 错误：`http://0.0.0.0:8000`（WebSocket 无法连接）

2. **查看浏览器控制台**（F12）
   - 应该看到 "WebSocket connected"
   - 如有错误信息，查看 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

3. **验证健康检查端点**

   ```bash
   curl http://localhost:8000/api/health
   ```

更多诊断步骤请参考 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

## 📁 项目结构

```bash
Rie-Kugimiya/
├── src/
│   ├── config.py         # 集中化配置管理
│   ├── api/              # FastAPI后端
│   │   ├── main.py       # 应用入口
│   │   ├── ws_routes.py  # WebSocket路由
│   │   ├── schemas.py    # Pydantic模型
│   │   └── llm_client.py # LLM客户端
│   ├── message_server/   # 消息服务器
│   │   ├── service.py    # 消息服务核心
│   │   ├── websocket.py  # WebSocket管理器
│   │   ├── database.py   # SQLite数据库层
│   │   └── models.py     # 消息数据模型
│   ├── rin_client/       # Rin独立客户端
│   │   └── client.py     # Rin客户端逻辑
│   ├── behavior/         # 消息行为引擎
│   │   ├── coordinator.py # 行为协调器
│   │   ├── timeline.py   # 时间轴构建器
│   │   ├── segmenter.py  # 分段模块
│   │   ├── emotion.py    # 情绪检测
│   │   ├── typo.py       # 错别字注入
│   │   └── pause.py      # 停顿计算
│   └── utils/            # 工具函数
├── frontend/             # Web前端
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── data/                 # 数据目录
│   └── rin_app.db       # SQLite数据库
├── tests/                # 单元测试
└── pyproject.toml        # 项目配置
```

## 🎯 开发路线图

### Phase 1: 基础对话系统 ✅

- [x] FastAPI后端框架
- [x] 多LLM API支持
- [x] Web聊天界面
- [x] 配置管理

### Phase 2: 行为引擎 ✅

- [x] 智能分段模块
- [x] LLM驱动的情绪检测
- [x] 错别字注入逻辑
- [x] 撤回重发系统
- [x] 微信式播放时间线
- [x] 动态停顿计算

### Phase 3: 功能增强（规划中）

- [ ] 多角色对话支持
- [ ] 对话历史管理
- [ ] 角色预设库
- [ ] 更多情绪类型支持
- [ ] 性能优化和调优
- [ ] 移动端适配

## 🔬 核心特色

1. **WebSocket实时架构** - 真正的实时双向通信，支持多客户端同步
2. **消息持久化** - 所有消息存储在SQLite，刷新页面不丢失历史记录
3. **配置集中化** - 所有默认配置统一管理，修改一处生效全局
4. **前后端职责分离** - 所有行为逻辑在后端，前端只负责UI渲染
5. **Rin独立客户端** - Rin作为独立客户端运行，与用户平等通信
6. **时间戳行为序列** - 所有行为带时间戳，精确模拟真实对话时间线
7. **智能分段** - 基于标点和语义的智能分段算法
8. **迟疑系统** - 模拟真人打字前的犹豫和反复
9. **输入状态管理** - 实时"正在输入"状态，不持久化
10. **情绪感知** - LLM生成情绪标注，驱动停顿时长和错别字概率
11. **概率行为** - 错别字和撤回基于概率分布，每次对话略有不同

## 🤝 贡献

这是一个课程项目，暂不接受外部贡献。

## 📄 许可证

MIT License

## 👨‍💻 作者

Leever - AI课程作业项目

---

**Note**: 本项目是一个完整可用的虚拟角色对话系统，采用规则驱动的行为引擎实现自然的对话体验。适合作为学习项目或二次开发的基础。
