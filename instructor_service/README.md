# Instructor Service

使用 Instructor Python 库格式化 LLM 输出为符合 `engine.go` 要求的数据格式（cot+json）。

## 功能

- 接收 `system_prompt` 和 `user_prompt`
- 使用 Instructor 库确保 LLM 输出符合结构化格式
- 返回包含思维链（CoT）和决策列表（JSON）的响应

## 数据格式

输出格式符合 `decision/engine.go` 中的 `FullDecision` 结构：

```json
{
  "cot_trace": "思维链分析文本...",
  "decisions": [
    {
      "symbol": "BTCUSDT",
      "action": "open_long",
      "leverage": 3,
      "position_size_usd": 5000,
      "stop_loss": 62000,
      "take_profit": 65000,
      "confidence": 75,
      "risk_usd": 1000,
      "reasoning": "决策理由"
    }
  ],
  "raw_response": "思维链文本\n\n[决策JSON数组]"
}
```

## API 端点

### POST /api/decision

生成交易决策

**请求体:**
```json
{
  "system_prompt": "系统提示词...",
  "user_prompt": "用户提示词..."
}
```

**响应:**
```json
{
  "cot_trace": "...",
  "decisions": [...],
  "raw_response": "..."
}
```

### GET /health

健康检查

## 环境变量

- `OPENAI_API_KEY`: OpenAI API 密钥（或兼容 API 的密钥）
- `OPENAI_BASE_URL`: API 基础 URL（默认: https://api.openai.com/v1）
- `OPENAI_MODEL`: 模型名称（默认: gpt-4o-mini）
- `PORT`: 服务端口（默认: 8000）

## Docker 使用

```bash
# 构建镜像
docker build -t instructor-service ./instructor_service

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_api_key \
  -e OPENAI_BASE_URL=https://api.openai.com/v1 \
  -e OPENAI_MODEL=gpt-4o-mini \
  instructor-service
```

## 集成到 Go 后端

在 `mcp/client.go` 中可以添加调用此服务的选项：

```go
// 调用 Instructor 服务
resp, err := http.Post("http://instructor-service:8000/api/decision", 
    "application/json", 
    bytes.NewBuffer(requestBody))
```

## 支持的 LLM 提供商

Instructor 支持所有 OpenAI 兼容的 API，包括：
- OpenAI
- DeepSeek
- Qwen（阿里云）
- SiliconFlow
- 其他兼容 OpenAI 格式的 API

