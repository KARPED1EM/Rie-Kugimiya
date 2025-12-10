# 故障排除指南 | Troubleshooting Guide

## WebSocket 连接失败

如果前端显示 WebSocket 连接错误，请按以下步骤排查：

### 1. 检查服务器是否运行

```bash
python test_server.py
```

如果显示 `✅ Server is running correctly!`，说明服务器正常运行。

### 2. 确认使用正确的 URL

**✅ 正确：**
```
http://localhost:8000
```

**❌ 错误：**
```
http://0.0.0.0:8000  # WebSocket 无法连接到 0.0.0.0
http://127.0.0.1:8000  # 虽然可以工作，但建议用 localhost
```

**重要提示：** `0.0.0.0` 是服务器监听地址，浏览器无法连接到这个地址。前端代码已经自动处理了这个问题，但最好直接使用 `localhost`。

### 3. 检查浏览器控制台

打开浏览器开发者工具（F12），查看 Console 标签页：

**正常情况应该看到：**
```
WebSocket connected
```

**如果看到错误：**
```
WebSocket connection to 'ws://...' failed
```

可能的原因：
- 服务器未启动
- 防火墙阻止了端口 8000
- 浏览器扩展干扰（尝试无痕模式）

### 4. 验证端口可用性

```bash
# 检查端口 8000 是否被占用
lsof -i :8000

# 或使用
netstat -an | grep 8000
```

如果端口被占用，可以修改 `run.py` 中的端口号。

### 5. 查看服务器日志

启动服务器时会显示详细日志：

```bash
python run.py
```

正常的 WebSocket 连接日志：
```
INFO:     127.0.0.1:xxxxx - "WebSocket /api/ws/..." [accepted]
```

错误日志会显示具体问题。

### 6. 测试基本连接

```bash
# 测试 HTTP 端点
curl http://localhost:8000/api/health

# 应该返回：
# {"status":"ok","service":"Yuzuriha Rin Virtual Character System",...}
```

### 7. 清除浏览器缓存

有时候旧的 JavaScript 文件会被缓存：

1. 按 Ctrl+Shift+Delete 打开清除数据对话框
2. 选择"缓存的图片和文件"
3. 清除后刷新页面（Ctrl+F5）

### 8. 检查 CORS 配置

如果从不同域名访问（不太可能在本地开发中），检查 `src/config.py` 中的 CORS 设置。

## 常见问题

### Q: WebSocket 连接后立即断开

**A:** 检查是否有 LLM API 密钥配置错误。虽然 WebSocket 能连接，但如果后续处理出错会导致连接关闭。

### Q: 前端显示"Connection error. Reconnecting..."

**A:** 这是正常的重连机制。如果服务器重启，前端会自动尝试重连。

### Q: 消息发送后没有响应

**A:** 检查以下内容：
1. LLM API 密钥是否正确配置
2. 网络是否能访问 LLM API
3. 查看服务器日志中的错误信息

### Q: TypeError 或其他 JavaScript 错误

**A:**
1. 确保使用最新代码（git pull）
2. 清除浏览器缓存
3. 检查是否修改了前端文件

## 获取帮助

如果以上步骤都无法解决问题，请提供：

1. 运行 `python test_server.py` 的输出
2. 浏览器控制台的完整错误信息
3. 服务器日志（`python run.py` 的输出）
4. 操作系统和浏览器版本

在 GitHub Issues 中创建问题单，附上以上信息。
