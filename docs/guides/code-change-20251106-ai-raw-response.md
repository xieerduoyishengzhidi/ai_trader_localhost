# 代码变更记录：AI 原始响应持久化

## 背景
在分析交易 AI 决策失败时，需要完整了解模型的原始输出。但原实现仅在成功解析并通过校验时记录 JSON，导致失败场景中缺少排查依据。本次变更为所有决策周期持久化 AI 原始响应，并在日志与前端展示层面提供访问入口。

## 主要改动

- **新增字段** `ai_raw_response`
  - `decision.FullDecision` 增加 `RawResponse` 字段，并在 `parseFullDecisionResponse` 初始即写入 `CallWithMessages` 的原始文本。
  - `logger.DecisionRecord` 与前端 `DecisionRecord` 类型同步增加可选字段 `ai_raw_response`，确保持久化与 UI 层兼容。

- **调整解析流程**
  - `GetFullDecision` 与 `GetFullDecisionWithCustomPrompt` 在解析失败时仍返回 `FullDecision` 实例，以便后续日志逻辑写入 `RawResponse`、`SystemPrompt`、`CoTTrace` 等调试信息。
  - `parseFullDecisionResponse` 始终返回 `FullDecision`，即便 JSON 提取或校验失败，也会保留已解析成功的部分（思维链、原始响应、已提取的决策）。

- **日志记录增强**
  - `trader.AutoTrader` 在记录决策日志时写入 `record.AIRawResponse`，保证 `decision_logs/*.json` 始终包含原始模型输出。

## 影响文件

- `decision/engine.go`
  - 定义 `FullDecision.RawResponse`
  - 更新 `GetFullDecision*`、`parseFullDecisionResponse`

- `trader/auto_trader.go`
  - 日志记录新增 `record.AIRawResponse`

- `logger/decision_logger.go`
  - `DecisionRecord` 结构体新增 `AIRawResponse`

- `web/src/types.ts`
- `web/src/types/index.ts`
  - 前端类型定义新增可选字段 `ai_raw_response`

## 注意事项

- 当前开发环境未安装 `go`/`gofmt`，后续请在具备 Go 工具链的环境运行：
  - `gofmt -w decision/engine.go trader/auto_trader.go logger/decision_logger.go`

- 新的日志字段默认存在于所有决策 JSON 中，前端视图若需展示原始响应，可直接读取 `ai_raw_response`。

- 若需进一步审计历史记录，可在导出脚本中增加对该字段的处理，避免过长文本影响下游分析。


