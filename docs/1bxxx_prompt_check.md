# 1bxxx Prompt UserPrompt 构建检查报告

## 📋 Prompt 需求分析

根据 `prompts/1bxxx.txt`，该策略需要以下数据：

### 必需数据
1. **强弱判断**：需要 BTC 对比数据 ✅
2. **价格数据**：当前价、1h/4h/1d 变化 ✅
3. **技术指标**：EMA20, MACD, RSI7 ✅
4. **多时间框架**：15m/1h/4h/1d 趋势、信号强度 ✅
5. **持仓量 (OI)**：当前值、变化率（1h/4h）✅
6. **相对成交量 (RVol)**：用于 S2 信号确认 ✅
7. **形态识别**：光头光脚、吞噬形态 ✅
8. **市场结构**：波段高低点、偏向 ✅
9. **市场状态**：趋势市/震荡市 ✅
10. **ATR14**：用于止损止盈计算 ❌ **缺失**

### 可选数据
- **资金费率**：配置中有但 prompt 未明确使用

---

## ⚠️ 发现的问题

### 1. **ATR14 数据缺失** 🔴 严重

**问题描述**：
- `1bxxx.txt` prompt 第125-130行需要 ATR14 来计算止损止盈：
  ```
  做空: SL = 当前价格 + (2.0 * ATR14)
  做多: SL = 当前价格 - (1.5 * ATR14)
  ```

**当前状态**：
- ❌ `1bxxx` 配置中没有 `longer_term`（那里有 ATR14）
- ❌ `FormatDataByConfig` 没有输出多时间框架中的 `ATR14`
- ❌ `market.Format()` 只在 `LongerTermContext` 中输出 ATR14（第1443-1444行）
- ✅ ATR14 存在于 `TimeframeData.ATR14`（每个时间框架都有）

**影响**：
- AI 无法获取 ATR14 值来计算止损止盈
- 可能导致计算错误或使用默认值

**解决方案**：
1. 在 `FormatDataByConfig` 中添加 ATR14 输出（从多时间框架中提取）
2. 或者在 `1bxxx` 配置中添加 `longer_term`（但会包含不需要的数据）

### 2. **数据格式化未使用配置** 🟡 中等

**问题描述**：
- `buildUserPromptWithRAG` 函数（第1295、1322行）使用的是 `market.Format(marketData)`
- 这会输出**完整**的市场数据，而不是根据 `1bxxx` 配置过滤的数据

**当前状态**：
```go
// decision/engine.go:1295
sb.WriteString(market.Format(marketData))  // 输出完整数据
```

**影响**：
- 会包含不需要的数据（如 `longer_term`, `fibonacci`, `price_deviation` 等）
- Token 消耗增加
- 不符合按需加载的设计理念

**解决方案**：
- 修改 `buildUserPromptWithRAG` 使用 `FormatDataByConfig` 替代 `market.Format`
- 需要传入配置和 schema

### 3. **资金费率配置不一致** 🟢 轻微

**问题描述**：
- `1bxxx` 配置中没有 `funding_rate`
- 但注释第223行提到"修正了這裡，原為 FundingRate"

**当前状态**：
- 配置中没有 `funding_rate`
- Prompt 中也没有明确使用资金费率

**影响**：
- 无影响（prompt 不需要）

---

## ✅ 当前可用的数据

使用 `1bxxx` prompt 时，`buildUserPromptWithRAG` 会输出以下数据：

### 1. 系统状态
- 时间、周期、运行时长 ✅

### 2. BTC 市场数据
- 当前价格、1h/4h 变化 ✅
- MACD、RSI7 ✅
- 市场状态 ✅

### 3. 账户信息
- 净值、余额、盈亏 ✅
- 保证金使用率 ✅
- 持仓数量 ✅

### 4. 持仓数据（每个持仓）
- 持仓信息（价格、盈亏、杠杆等）✅
- **完整市场数据**（通过 `market.Format()` 输出）✅

### 5. 候选币种数据（每个币种）
- **完整市场数据**（通过 `market.Format()` 输出），包括：
  - ✅ 基础价格（当前价、1h/4h/1d 变化）
  - ✅ 技术指标（EMA20, MACD, RSI7）
  - ✅ 多时间框架（15m/1h/4h/1d：趋势、强度、EMA、MACD、RSI、市场结构）
  - ✅ 持仓量（当前值、平均值、变化率）
  - ✅ 资金费率（当前值、变化率）
  - ✅ 相对成交量 (RVol)
  - ✅ EMA 偏离度
  - ✅ 关键流动性（PDH/PDL）
  - ✅ 长期数据（EMA、ATR3/ATR14、成交量序列）
  - ✅ 市场结构（日线：波段高低点、偏向）
  - ✅ 斐波那契水平（OTE 区间）
  - ✅ 市场状态
  - ❌ **ATR14（仅在 longer_term 中，但配置中没有）**

### 6. RAG 历史观点
- 交易员历史观点（最多5条）✅

### 7. 夏普比率
- 账户夏普比率 ✅

### 8. 市场状态摘要
- 趋势市/震荡市/波动市统计 ✅

### 9. 形态识别（JSON）
- TA-Lib 识别的 K 线形态 ✅

### 10. 决策字段提示（JSON）
- 风险限制、杠杆限制、仓位限制 ✅

---

## 🔧 修复建议

### 优先级 1：修复 ATR14 缺失

**方案 A（推荐）**：在 `FormatDataByConfig` 中添加 ATR14 输出

```go
// 在多时间框架数据输出中添加 ATR14
if mtf.Timeframe15m != nil && mtf.Timeframe15m.ATR14 > 0 {
    sb.WriteString(fmt.Sprintf(" | ATR14:%.4f", mtf.Timeframe15m.ATR14))
}
```

**方案 B**：在 `1bxxx` 配置中添加 `longer_term`
- 优点：简单
- 缺点：会包含不需要的数据（MACD序列、RSI序列等）

### 优先级 2：使用配置化数据格式化

修改 `buildUserPromptWithRAG` 使用 `FormatDataByConfig`：

```go
// 获取数据配置
config := market.GetDataConfigByTraderName(traderName, systemPromptTemplate)
schema := market.GetDefaultDataSchema()

// 使用配置格式化数据
formattedData := market.FormatDataByConfig(marketData, config, schema)
sb.WriteString(formattedData)
```

---

## 📊 数据完整性检查

| 数据项 | Prompt 需要 | 配置包含 | 实际输出 | 状态 |
|--------|------------|---------|---------|------|
| BTC 对比 | ✅ | ✅ | ✅ | ✅ |
| 基础价格 | ✅ | ✅ | ✅ | ✅ |
| 技术指标 | ✅ | ✅ | ✅ | ✅ |
| 多时间框架 | ✅ | ✅ | ✅ | ✅ |
| OI 持仓量 | ✅ | ✅ | ✅ | ✅ |
| RVol | ✅ | ✅ | ✅ | ✅ |
| 形态识别 | ✅ | ✅ | ✅ | ✅ |
| 市场结构 | ✅ | ✅ | ✅ | ✅ |
| 市场状态 | ✅ | ✅ | ✅ | ✅ |
| **ATR14** | ✅ | ❌ | ❌ | ❌ **缺失** |
| 资金费率 | ❓ | ❌ | ✅ | ⚠️ |

---

## 🎯 总结

### 会报错吗？
- ❌ **不会报错**，但会有功能缺失
- ATR14 缺失会导致 AI 无法正确计算止损止盈

### 数据都正确吗？
- ✅ 大部分数据正确
- ❌ ATR14 缺失
- ⚠️ 数据未按配置过滤（输出完整数据）

### 都有什么数据？
- ✅ 包含所有必需数据（除 ATR14）
- ⚠️ 还包含一些不需要的数据（因为使用 `market.Format()` 而非配置化格式化）

### 建议
1. **立即修复**：添加 ATR14 输出
2. **优化**：使用配置化数据格式化，减少 Token 消耗

