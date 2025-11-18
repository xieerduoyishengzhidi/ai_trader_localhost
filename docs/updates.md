#### 决策引擎提示词与输出约束（decision/engine.go）
- System Prompt：补充并强化“结构化输出约束”
  - 最终响应为“思维链 + JSON 决策数组”；禁止 Markdown 代码块包裹数组
  - 仅允许的 action：open_long | open_short | close_long | close_short | hold | wait
  - 禁止聚合符号（ALL/ANY/*），必须为真实交易对
  - open_* 必填字段与校验要求：leverage、position_size_usd、stop_loss、take_profit；止损止盈方向正确；R:R ≥ 3
- User Prompt：新增“决策字段数值提示（机器可读）”JSON，仅用于信息再次确认
  - risk_usd_max = 账户净值 × 2%
  - leverage_max = { btc_eth: 配置上限, alt: 配置上限 }
  - position_size_usd_max = { btc_eth: 账户净值 × 10, alt: 账户净值 × 1.5 }
  - stop_loss/take_profit 必须为正数
- 解析逻辑不变：先提取思维链，再从首个“[”开始提取 JSON 数组并校验

### 修复
- 通过提示词约束规避 AI 产出非法 action/symbol（如 monitor_only、ALL）导致的“决策验证失败”

### 影响
- 输出要求更严格，减少解析失败与无效决策；对 API 与存储无破坏性影响
- 代码位置：`decision/engine.go`（System Prompt 输出约束、User Prompt 数值提示）

---2025.11.7
