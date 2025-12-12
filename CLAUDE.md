# CLAUDE.md

NOFX - AI 驱动的加密货币期货自动交易系统

## 🛠 Project Commands (常用指令)

### 后端 (Go)
- **Run Dev**: `go run main.go` (后端 API 服务，默认端口 8080)
- **Build**: `go build -o nofx main.go`

### 前端 (React)
- **Run Dev**: `cd web && npm run dev` (开发服务器)
- **Build**: `cd web && npm run build` (生产构建)
- **Lint**: `cd web && npm run lint` (代码检查)
- **Format**: `cd web && npm run format` (代码格式化)

### Docker 部署
- **Start**: `docker compose up -d --build` (构建并启动)
- **Stop**: `docker compose down` (停止服务)
- **Logs**: `docker compose logs -f nofx` (查看后端日志)
- **Status**: `docker compose ps` (查看服务状态)

## 🏗 Tech Stack (技术栈)

### 后端
- **Language**: Go 1.25+
- **Framework**: Gin (HTTP 框架)
- **DB**: SQLite (config.db)
- **WebSocket**: gorilla/websocket
- **交易所**: Binance, Hyperliquid, Aster DEX

### 前端
- **Language**: TypeScript 5.0+, Node.js 18+
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Charts**: Recharts
- **Animation**: Framer Motion

### AI/服务
- **Instructor Service**: Python FastAPI (结构化 LLM 输出)
- **支持模型**: DeepSeek, Qwen, OpenAI

## 📂 Code Structure (代码结构)

```
nofx-dev/
├── main.go                 # 程序入口
├── api/server.go           # HTTP API 路由和处理
├── config/                 # 配置管理
│   ├── config.go           # 全局配置
│   └── database.go         # 数据库操作
├── trader/                 # 交易执行器
│   ├── interface.go        # Trader 接口定义
│   ├── binance_futures.go  # 币安期货交易
│   ├── hyperliquid_trader.go
│   └── aster_trader.go
├── decision/               # AI 决策引擎
│   ├── engine.go           # 决策引擎核心
│   ├── prompt_manager.go   # Prompt 管理
│   └── rag.go              # RAG 检索增强
├── market/                 # 市场数据
│   ├── data.go             # 数据获取
│   ├── monitor.go          # 市场监控
│   ├── pattern.go          # K线形态识别
│   └── websocket_client.go # WebSocket 数据流
├── manager/                # 交易员管理器
├── news/                   # 新闻模块
├── prompts/                # AI Prompt 模板
├── web/                    # 前端 (React)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/     # UI 组件
│   │   ├── contexts/       # React Context
│   │   ├── hooks/          # 自定义 Hooks
│   │   └── lib/            # 工具函数和 API
│   └── package.json
├── instructor_service/     # Python 结构化输出服务
├── docker/                 # Docker 配置
├── docker-compose.yml
└── config.json             # 运行时配置
```

## 📝 Coding Guidelines (编码规范)

### Go 后端
1. **错误处理**: 所有错误必须处理，使用 `if err != nil` 模式
2. **接口优先**: 交易所适配使用 `Trader` 接口 (`trader/interface.go`)
3. **并发安全**: 使用 `sync.Mutex` 保护共享状态
4. **日志**: 使用标准 `log` 包，关键操作必须记录日志

### React 前端
1. **Components**: 使用函数式组件，命名导出
2. **Typing**: 禁止 `any`，所有 props 使用严格接口
3. **Styling**: 只用 Tailwind 工具类，禁止 `style={{}}`
4. **State**: 全局状态用 Zustand，组件状态用 useState
5. **API**: 使用 SWR 进行数据获取和缓存

### 通用
1. **注释**: 只注释复杂逻辑，代码应自解释
2. **Git**: 每完成一个功能模块后进行 commit，描述清晰
3. **测试**: 关键业务逻辑需要单元测试

## 🔧 Configuration (配置)

主配置文件: `config.json`
```json
{
  "admin_mode": true,
  "leverage": {
    "btc_eth_leverage": 5,
    "altcoin_leverage": 5
  },
  "api_server_port": 8080,
  "jwt_secret": "your-secret-key"
}
```

敏感配置(API keys)存储在: `config.db` (SQLite)

## 🚀 Quick Start (快速开始)

```powershell
# 1. 复制配置文件
Copy-Item config.json.example config.json

# 2. 启动 Docker 服务
docker compose up -d --build

# 3. 访问 Web 界面
# http://localhost:4001
```

