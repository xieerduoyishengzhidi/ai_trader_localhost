# 数据模式设计文档

## 📋 概述

本文档描述交易系统中传递给AI的数据结构分类和使用方式。不同策略（prompt）可以根据需要选择不同的数据子集，以提高效率和针对性。

## 🗂️ 数据分类

### 1. 基础价格数据 (`basic_price`)
**用途**: 所有策略必需的基础数据
- `CurrentPrice`: 当前价格
- `PriceChange1h`: 1小时价格变化（%）
- `PriceChange4h`: 4小时价格变化（%）
- `PriceChange1d`: 日线价格变化（%）

**适用场景**: 所有交易策略

---

### 2. 技术指标 (`technical_indicators`)
**用途**: 主要技术分析指标
- `CurrentEMA20`: 20周期EMA
- `CurrentMACD`: MACD指标值
- `CurrentRSI7`: 7周期RSI

**适用场景**: 趋势判断、超买超卖分析

---

### 3. 多时间框架数据 (`multi_timeframe`)
**用途**: 多时间框架趋势确认
- 15m/1h/4h/1d各框架的：
  - 价格、EMA20/EMA50、MACD、RSI7/RSI14
  - 趋势方向（bullish/bearish/neutral）
  - 信号强度（0-100）
  - 形态识别结果

**适用场景**: 需要多时间框架确认的策略（如林凡策略）

---

### 4. 持仓量数据 (`open_interest`)
**用途**: 市场参与度和资金流向
- `Latest`: 当前持仓量
- `Average`: 平均持仓量
- `Change15m/1h/4h/1d`: 各时间框架变化率（%）

**适用场景**: 强弱判断、资金流向分析

---

### 5. 资金费率数据 (`funding_rate`)
**用途**: 市场情绪和套利机会
- `Latest`: 当前资金费率
- `Change15m/1h/4h/1d`: 各时间框架变化率（基点）

**适用场景**: 套利策略、市场情绪判断

---

### 6. 长期数据 (`longer_term`)
**用途**: 长期趋势和波动率
- EMA20/EMA50（4h框架）
- ATR3/ATR14（波动率）
- 成交量数据
- MACD/RSI序列

**适用场景**: 长期趋势分析、止损止盈计算

---

### 7. 市场结构 (`market_structure`)
**用途**: 波段分析和趋势判断
- `SwingHighs`: 波段高点数组
- `SwingLows`: 波段低点数组
- `CurrentBias`: 当前偏向（bullish/bearish/neutral）

**✅ 更新说明**：
- **每个时间框架都有独立的 MarketStructure**
- `TimeframeData.MarketStructure` - 每个时间框架（15m/1h/4h/1d）都有独立的波段高低点
- `Data.MarketStructure` - 日线的市场结构（用于大周期分析，保持向后兼容）
- 每个时间框架基于自己的价格序列计算波段高低点

**适用场景**: 趋势确认、结构交易（多时间框架分析）

---

### 8. 斐波那契水平 (`fibonacci`)
**用途**: OTE入场区间识别
- 0.236/0.382/0.5/0.618/0.705/0.786水平
- OTE区间（0.618-0.705）
- 波段高点/低点

**适用场景**: OTE回调/反弹入场策略

---

### 9. 蜡烛图形态 (`candlestick_patterns`)
**用途**: K线形态识别和入场信号
- 形态名称（吞噬、十字星、锤子等）
- 信号方向（bullish/bearish）
- 时间框架、置信度

**适用场景**: 入场信号确认、反转识别

---

### 10. 成交量分析 (`volume_analysis`)
**用途**: 量能确认
- `RVol`: 相对成交量（当前/20均量）
  - >1.5: 放量（突破确认）
  - <0.5: 缩量（反转确认）

**适用场景**: S2突破确认、形态过滤

---

### 11. 价格偏离度 (`price_deviation`)
**用途**: 价格相对位置
- `EMADeviation`: (价格-EMA20)/EMA20 * 100（%）

**适用场景**: 超买超卖判断

---

### 12. 关键流动性 (`liquidity_levels`)
**用途**: 关键支撑阻力
- `PDH`: 前日高点
- `PDL`: 前日低点

**适用场景**: 止损止盈设置、流动性分析

---

### 13. 市场状态 (`market_condition`)
**用途**: 市场环境判断
- `Condition`: trending/ranging/volatile
- `Confidence`: 置信度（0-100）

**适用场景**: 震荡市过滤、策略选择

---

## 🎯 Prompt配置示例

### 林凡多空策略
```go
{
    PromptName: "林凡_多空",
    DataCategories: [
        "basic_price",           // 必需
        "technical_indicators",  // 必需
        "multi_timeframe",       // 多时间框架确认
        "market_structure",      // 趋势判断
        "fibonacci",             // OTE入场
        "candlestick_patterns",  // 入场信号
        "volume_analysis",       // S2突破确认
        "open_interest",         // 强弱判断
        "market_condition",      // 震荡市过滤
    ],
    IncludeBTC: true,
    IncludeAccount: true,
    IncludePositions: true,
    IncludeRAG: true,
}
```

### 林凡只做多策略
```go
{
    PromptName: "林凡_只做多",
    DataCategories: [
        "basic_price",
        "technical_indicators",
        "multi_timeframe",
        "fibonacci",             // OTE回调
        "candlestick_patterns",  // S2突破
        "volume_analysis",
        "market_condition",
    ],
    IncludeBTC: true,
    IncludeAccount: true,
    IncludePositions: true,
    IncludeRAG: true,
}
```

---

## 📊 数据字段含义速查

| 字段名 | 含义 | 单位/范围 |
|--------|------|-----------|
| `CurrentPrice` | 当前价格 | 价格单位 |
| `PriceChange1h` | 1小时涨跌幅 | % |
| `CurrentEMA20` | 20周期EMA | 价格单位 |
| `CurrentMACD` | MACD值 | 差值 |
| `CurrentRSI7` | 7周期RSI | 0-100 |
| `RVol` | 相对成交量 | 倍数（>1.5放量，<0.5缩量）|
| `EMADeviation` | EMA偏离度 | % |
| `PDH/PDL` | 前日高低点 | 价格单位 |
| `FibLevels.Level618` | 0.618回撤位 | 价格单位 |
| `FibLevels.Level705` | 0.705回撤位 | 价格单位 |
| `MarketStructure.CurrentBias` | 当前偏向 | bullish/bearish/neutral |
| `PatternRecognition.Patterns[].Side` | 形态方向 | bullish/bearish |

---

## 🔧 使用方式

### 1. 获取数据模式
```go
schema := market.GetDefaultDataSchema()
```

### 2. 获取Prompt配置
```go
config := market.GetPromptDataConfig("林凡_多空")
```

### 3. 过滤数据
```go
filteredData := market.FilterDataBySchema(marketData, config, schema)
```

### 4. 构建User Prompt
根据配置选择性地包含：
- BTC市场数据（如果`IncludeBTC=true`）
- 账户信息（如果`IncludeAccount=true`）
- 持仓信息（如果`IncludePositions=true`）
- RAG历史观点（如果`IncludeRAG=true`）
- 过滤后的市场数据（根据`DataCategories`）

---

## 💡 最佳实践

1. **必需数据**: `basic_price`和`technical_indicators`应该始终包含
2. **策略特定**: 根据策略特点选择数据（如OTE策略需要`fibonacci`）
3. **性能优化**: 不需要的数据不要包含，减少Token消耗
4. **格式选择**: 
   - `markdown`: 人类可读，适合思维链分析
   - `json`: 机器可读，适合结构化处理
   - `compact`: 精简版，节省Token

