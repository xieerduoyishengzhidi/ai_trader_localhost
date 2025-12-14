# 🤖 NOFX - AI 驱动的加密货币期货自动交易系统

[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?style=flat&logo=go)](https://golang.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)

> ⚠️ **风险警告**: 本系统为实验性项目，AI 自动交易存在重大风险。强烈建议仅用于学习研究或小额测试！

---

## ✨ 核心特色

### 🧠 AI 决策引擎
- **多模型支持**: DeepSeek、Qwen、OpenAI 兼容 API
- **思维链推理**: 完整的 Chain of Thought (CoT) 决策过程
- **自适应学习**: 基于历史表现自动调整策略
- **RAG 增强**: 支持检索增强生成，提升决策质量

### 📊 多交易所支持
| 交易所 | 状态 | 特点 |
|--------|------|------|
| **Binance Futures** | ✅ 已实现 | 主流 CEX，流动性最佳 |
| **Hyperliquid** | ✅ 已实现 | 去中心化永续合约 |
| **Aster DEX** | ✅ 已实现 | Binance 兼容 API |

### 🎯 智能风控系统
- 仓位限制（山寨币 ≤1.5x 净值，BTC/ETH ≤10x 净值）
- 动态杠杆配置（1x-50x）
- 强制风险回报比（≥1:2）
- 防重复开仓保护

### 🖥️ 专业 Web 界面
- 实时账户监控
- 净值曲线图表
- AI 决策日志（可展开查看完整思维链）
- 多交易员竞赛模式

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web 前端 (React + Vite)                 │
│                    localhost:3000                            │
└─────────────────────────────────────────────────────────────┘
                              ↓ API
┌─────────────────────────────────────────────────────────────┐
│                   后端服务 (Go + Gin)                        │
│                    localhost:8080                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 交易管理器   │  │  AI 决策引擎  │  │    市场数据模块     │  │
│  │  manager/   │  │  decision/  │  │      market/        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  交易执行器  │  │   数据库     │  │    日志记录器       │  │
│  │   trader/   │  │   config/   │  │      logger/        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              交易所 API (Binance / Hyperliquid / Aster)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### Docker 一键部署（推荐）

```bash
# 1. 复制配置文件
cp config.json.example config.json

# 2. 启动服务
docker compose up -d --build

# 3. 访问 http://localhost:3000
```

### 手动安装

```bash
# 安装依赖
go mod download
cd web && npm install && cd ..

# 启动后端
go run main.go

# 启动前端（新终端）
cd web && npm run dev
```

**环境要求**: Go 1.21+, Node.js 18+, TA-Lib

---

## 📂 项目结构

```
nofx-dev/
├── main.go                 # 程序入口
├── api/server.go           # HTTP API 路由
├── config/                 # 配置管理
│   ├── config.go           # 全局配置
│   └── database.go         # 数据库操作 (SQLite)
├── trader/                 # 交易执行器
│   ├── interface.go        # Trader 接口定义
│   ├── binance_futures.go  # 币安期货
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
├── logger/                 # 决策日志记录
├── prompts/                # AI Prompt 模板
├── web/                    # 前端 (React)
└── docker-compose.yml      # Docker 配置
```

---

## 📋 开发进度

### ✅ 已完成功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **交易执行** | Binance Futures API | ✅ |
| | Hyperliquid DEX | ✅ |
| | Aster DEX | ✅ |
| | 自动精度处理 | ✅ |
| **AI 决策** | DeepSeek 集成 | ✅ |
| | Qwen 集成 | ✅ |
| | 思维链 (CoT) | ✅ |
| | 历史反馈学习 | ✅ |
| | RAG 增强 | ✅ |
| **市场数据** | 多时间框架分析 | ✅ |
| | 技术指标 (EMA/MACD/RSI/ATR) | ✅ |
| | K线形态识别 | ✅ |
| | WebSocket 实时数据 | ✅ |
| **风控系统** | 仓位限制 | ✅ |
| | 杠杆控制 | ✅ |
| | 止盈止损 | ✅ |
| **Web 界面** | 账户监控 | ✅ |
| | 净值曲线 | ✅ |
| | 决策日志 | ✅ |
| | 交易员管理 | ✅ |
| **数据管理** | SQLite 数据库 | ✅ |
| | 决策日志导出 | ✅ |
| | 盈亏统计 | ✅ |

### 🚧 进行中

| 功能 | 进度 | 说明 |
|------|------|------|
| Prompt 模板优化 | 80% | 改进决策质量 |
| 新闻情绪分析 | 60% | Telegram/Twitter 数据 |
| 多策略竞赛 | 70% | AI 模型对战 |

### 📅 计划中

- [ ] OKX / Bybit 交易所集成
- [ ] GPT-4 / Claude 支持
- [ ] 移动端适配
- [ ] TradingView 图表集成
- [ ] 回测系统
- [ ] API 密钥加密存储

---

## 🛠️ 常用命令

```bash
# 后端
go run main.go              # 运行开发服务器
go build -o nofx main.go    # 编译

# 前端
cd web && npm run dev       # 开发服务器
cd web && npm run build     # 生产构建
cd web && npm run lint      # 代码检查

# Docker
docker compose up -d --build  # 启动
docker compose down           # 停止
docker compose logs -f nofx   # 查看日志

# 工具脚本
.\scripts\export_trader_logs.ps1                    # 列出交易员
.\scripts\export_trader_logs.ps1 -TraderId "xxx"    # 导出日志
```

---

## 📊 数据导出

使用内置脚本导出交易员数据：

```powershell
# Windows
.\scripts\export_trader_logs.ps1 -TraderId "binance_admin_deepseek_xxx"

# Linux/macOS
./scripts/export_trader_logs.sh binance_admin_deepseek_xxx
```

导出内容：
- `decision_logs_*.csv` - 决策日志
- `orders_*.csv` - 订单记录
- `trades_*.csv` - 成交详情
- `pnl_summary_*.txt` - 盈亏汇总

---

## ⚙️ 配置说明

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

敏感配置（API keys）存储在: `config.db` (SQLite)

---

## 📈 AI 决策流程

```
1. 获取账户状态 → 2. 分析持仓 → 3. 获取市场数据
                           ↓
4. AI 综合决策 ← 5. 技术指标计算 ← 6. 历史表现回顾
      ↓
7. 执行交易 → 8. 记录日志 → 9. 更新统计
      ↓
   🔄 每 3-5 分钟循环
```

---

## ⚠️ 风险提示

1. **加密货币市场波动剧烈**，AI 决策不保证盈利
2. **期货交易使用杠杆**，亏损可能超过本金
3. **极端行情**可能导致爆仓风险
4. 建议使用**小额资金测试**（100-500 USDT）
5. 请**定期监控**系统运行状态

---

## 📬 联系方式

- **GitHub Issues**: 提交 Bug 或功能建议
- **Telegram**: 开发者社区讨论

---

**⚡ 探索 AI 量化交易的无限可能！**
