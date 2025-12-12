# 目录功能速览（精简版）

> 运行示例（PowerShell）：启动后端 API  
> `go run .`

## 目录说明（含清理记录）
- `api/`：Go 后端路由，提供交易员管理、状态查询等 HTTP 接口。
- `decision/`：决策引擎与 Prompt 处理，含 RAG 客户端与上下文格式化。
- `manager/`：交易员生命周期与调度管理。
- `trader/`：交易员实体定义、配置与运行控制。
- `market/`：行情数据获取与格式化。清理：移除历史占位测试 `data_test.go`、`error_handling_test.go`（依赖真实网络、无断言，未在流水线使用）。
- `rag/`：Python RAG 服务（ChromaDB 混合搜索），含导入、查询、API 启动脚本。
- `filter/`：新闻/观点数据清洗与导出脚本（Pentoshi 数据管道）。
- `news_service/`：新闻数据库管理与查询工具。
- `macro_service/`：宏观数据采集与处理脚本/服务。
- `instructor_service/`：指令生成微服务（Python）。
- `prompts/`：系统/交易员 Prompt 模板集合。
- `docs/`：项目文档与指南。
- `web/`：前端（React/TS），交易员配置与控制台。
- `docker/` & `docker-compose.yml`：容器化与本地编排配置。
- `tools/`、`scripts/`：运维/发布/校验辅助脚本。
- `telegram_fetch/`：Telegram 数据抓取与落库工具。
- `trading_brain/`：研究/实验脚本与说明。清理：移除历史说明文档与测试记录（ARCHITECTURE.md、API_CONFIG.md、CODE_FLOW.md、LOGIC_EXPLANATION.md、逻辑说明.md、TROUBLESHOOTING.md、TEST_RESULTS.md），保留 README 作为唯一入口。
- `decision_logs/`、`output/`：运行产物与导出结果。
- `tools/`：二进制/脚本示例。清理：删除冗余示例脚本 `example_usage.ps1`、`download_2days_example.ps1`（示例密钥和重复功能）。

## 备注
- 如需继续清理其他历史方案或未引用文档，可先标记来源与影响，再删除并在此处追加记录。

