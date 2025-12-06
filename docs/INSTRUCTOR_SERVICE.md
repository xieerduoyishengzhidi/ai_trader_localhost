# Instructor Service 使用指南

## 概述

Instructor Service 是一个 Python 微服务，使用 [Instructor](https://github.com/jxnl/instructor) 库来确保 LLM 输出符合 `engine.go` 要求的数据格式（cot+json）。

## 功能

- ✅ 接收 `system_prompt` 和 `user_prompt`
- ✅ 使用 Instructor 库确保 LLM 输出结构化格式
- ✅ 返回符合 `FullDecision` 格式的响应（思维链 + JSON 决策数组）
- ✅ 支持所有 OpenAI 兼容的 API（DeepSeek、Qwen、SiliconFlow 等）

## 数据格式

输出格式完全符合 `decision/engine.go` 中的 `FullDecision` 结构：

```go
type FullDecision struct {
    CoTTrace     string     `json:"cot_trace"`       // 思维链分析
    Decisions    []Decision `json:"decisions"`       // 决策列表
    RawResponse  string     `json:"ai_raw_response"` // 原始响应
}
```

`raw_response` 格式：`思维链文本\n\n[决策JSON数组]`

## API 端点

### POST /api/decision

生成交易决策

**请求示例（从 config.db 读取配置）:**
```bash
curl -X POST http://localhost:8000/api/decision \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "你是一个交易专家...",
    "user_prompt": "当前市场情况...",
    "api_key": "sk-xxx...",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  }'
```

**请求参数说明:**
- `system_prompt` (必需): 系统提示词
- `user_prompt` (必需): 用户提示词
- `api_key` (可选): API 密钥，如果不提供则使用环境变量 `OPENAI_API_KEY`
- `base_url` (可选): API 基础 URL，如果不提供则使用环境变量 `OPENAI_BASE_URL`
- `model` (可选): 模型名称，如果不提供则使用环境变量 `OPENAI_MODEL`

**注意**: API 配置应该从 `config.db` 的 `ai_models` 表中读取，并通过请求参数传递。这样每个交易员可以使用不同的 LLM 配置。

**响应示例:**
```json
{
  "cot_trace": "看到BTC回调到OTE区间了...\n4小时图趋势向上...",
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
      "reasoning": "趋势向上，风险回报比符合要求"
    }
  ],
  "raw_response": "看到BTC回调到OTE区间了...\n\n[{\"symbol\":\"BTCUSDT\",...}]"
}
```

### GET /health

健康检查

## Docker 部署

### 使用 docker-compose

服务已集成到 `docker-compose.yml`：

```yaml
instructor-service:
  build:
    context: ./instructor_service
    dockerfile: Dockerfile
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - OPENAI_BASE_URL=${OPENAI_BASE_URL}
    - OPENAI_MODEL=${OPENAI_MODEL}
```

启动服务：
```bash
docker-compose up -d instructor-service
```

### 单独构建和运行

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

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | API 密钥（必需） | - |
| `OPENAI_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `PORT` | 服务端口 | `8000` |

## 支持的 LLM 提供商

Instructor 支持所有 OpenAI 兼容的 API：

- ✅ OpenAI
- ✅ DeepSeek (`https://api.deepseek.com/v1`)
- ✅ Qwen/阿里云 (`https://dashscope.aliyuncs.com/compatible-mode/v1`)
- ✅ SiliconFlow (`https://api.siliconflow.cn/v1`)
- ✅ 其他兼容 OpenAI 格式的 API

## 集成到 Go 后端

在 `mcp/client.go` 中可以添加调用此服务的选项：

```go
// CallWithInstructorService 使用 Instructor 服务调用 LLM（从 config.db 读取配置）
func (client *Client) CallWithInstructorService(systemPrompt, userPrompt string) (string, error) {
    // 构建请求体，包含 API 配置（从 client 中获取，这些值来自 config.db）
    requestBody := map[string]interface{}{
        "system_prompt": systemPrompt,
        "user_prompt":   userPrompt,
        "api_key":       client.APIKey,    // 从 config.db 的 ai_models 表读取
        "base_url":      client.BaseURL,   // 从 config.db 的 ai_models 表读取
        "model":         client.Model,     // 从 config.db 的 ai_models 表读取
    }
    
    jsonData, err := json.Marshal(requestBody)
    if err != nil {
        return "", fmt.Errorf("序列化请求失败: %w", err)
    }
    
    // 调用 Instructor 服务
    resp, err := http.Post(
        "http://instructor-service:8000/api/decision",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    if err != nil {
        return "", fmt.Errorf("调用 Instructor 服务失败: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return "", fmt.Errorf("Instructor 服务返回错误 (status %d): %s", resp.StatusCode, string(body))
    }
    
    var result struct {
        RawResponse string `json:"raw_response"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return "", fmt.Errorf("解析响应失败: %w", err)
    }
    
    return result.RawResponse, nil
}
```

**配置流程:**
1. Go 后端从 `config.db` 的 `ai_models` 表读取 API 配置（通过 `GetTraderConfig` 方法）
2. 配置传递给 `mcp.Client`（通过 `SetDeepSeekAPIKey`、`SetQwenAPIKey` 等方法）
3. 调用 `CallWithInstructorService` 时，配置自动传递给 Python 服务
4. Python 服务使用这些配置调用 LLM API

## 工作原理

1. **接收请求**: Flask 接收 `system_prompt` 和 `user_prompt`
2. **增强 Prompt**: 在 system prompt 中添加输出格式要求
3. **Instructor 调用**: 使用 Instructor 的 `response_model` 确保输出符合 `FullDecisionResponse` 结构
4. **格式化输出**: 将结构化结果转换为 `engine.go` 期望的文本格式（cot + json）
5. **返回响应**: 返回包含 `cot_trace`、`decisions` 和 `raw_response` 的 JSON

## 优势

- ✅ **结构化输出**: Instructor 确保输出始终符合 Pydantic 模型定义
- ✅ **类型安全**: 使用 Pydantic 进行数据验证
- ✅ **格式一致**: 自动处理 JSON 格式，避免解析错误
- ✅ **兼容性好**: 支持所有 OpenAI 兼容的 API

## 故障排查

### 服务无法启动

检查环境变量：
```bash
docker logs instructor-service
```

### API 调用失败

检查 API 密钥和 URL：
```bash
curl http://localhost:8000/health
```

### 输出格式错误

Instructor 会自动验证输出格式，如果失败会抛出异常。检查日志：
```bash
docker logs -f instructor-service
```

