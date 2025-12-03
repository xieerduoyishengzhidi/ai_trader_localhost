# 数据结构设计总结

## 🎯 设计目标

1. **数据分类**: 将市场数据按功能分类，便于不同策略按需选择
2. **配置化**: 通过配置文件定义不同prompt需要的数据
3. **可扩展**: 易于添加新的数据分类和字段
4. **文档化**: 每个字段都有明确的含义说明

## 📁 文件结构

```
market/
├── data.go              # 原有数据获取和计算逻辑
├── types.go             # 数据结构定义
├── data_schema.go       # 数据模式定义（新增）
└── data_schema_example.go # 使用示例（新增）

docs/
├── DATA_SCHEMA.md              # 数据模式详细文档
├── USER_PROMPT_DATA_SUMMARY.md # 当前数据上传总结
└── DATA_STRUCTURE_DESIGN.md    # 本文档
```

## 🗂️ 数据分类体系

### 13个数据分类

1. **basic_price** - 基础价格（必需）
2. **technical_indicators** - 技术指标（必需）
3. **multi_timeframe** - 多时间框架
4. **open_interest** - 持仓量
5. **funding_rate** - 资金费率
6. **longer_term** - 长期数据
7. **market_structure** - 市场结构
8. **fibonacci** - 斐波那契
9. **candlestick_patterns** - 蜡烛图形态
10. **volume_analysis** - 成交量分析
11. **price_deviation** - 价格偏离度
12. **liquidity_levels** - 关键流动性
13. **market_condition** - 市场状态

## 🔧 核心结构

### DataSchema
定义所有可用的数据分类和字段描述

### PromptDataConfig
定义某个prompt需要哪些数据分类

### FilterDataBySchema
根据配置过滤数据，只返回需要的字段

## 📊 当前User Prompt数据清单

### 系统级数据
- 时间、周期、运行时长
- BTC市场数据
- 账户信息
- 持仓信息
- 候选币种列表
- RAG历史观点（可选）
- 夏普比率
- 市场状态摘要
- 形态识别JSON
- 决策字段提示JSON

### 每个币种的市场数据（通过market.Format()）
包含Data结构体的所有字段，格式化输出

## 🎯 使用流程

### 1. 定义数据模式
```go
schema := market.GetDefaultDataSchema()
```

### 2. 配置Prompt数据需求
```go
config := market.GetPromptDataConfig("林凡_多空")
```

### 3. 获取市场数据
```go
data, _ := market.Get("BTCUSDT")
```

### 4. 过滤数据
```go
filteredData := market.FilterDataBySchema(data, config, schema)
```

### 5. 构建User Prompt
根据配置和过滤后的数据构建prompt

## 💡 优势

1. **灵活性**: 不同策略可以选择不同的数据子集
2. **效率**: 减少不必要的Token消耗
3. **可维护**: 数据结构集中管理，易于修改
4. **可扩展**: 添加新分类和字段很简单
5. **文档化**: 每个字段都有含义说明

## 🔄 迁移建议

### 阶段1: 保持兼容
- 保留现有的`buildUserPrompt`函数
- 新增`buildUserPromptByConfig`函数
- 逐步迁移策略到新函数

### 阶段2: 优化配置
- 为每个prompt创建配置文件
- 根据策略特点选择数据分类
- 优化Token使用

### 阶段3: 完全迁移
- 所有策略使用新结构
- 移除旧函数或标记为废弃

## 📝 配置示例

### 林凡多空策略
需要：价格、技术指标、多时间框架、市场结构、斐波那契、形态、成交量、持仓量、市场状态

### 林凡只做多策略
需要：价格、技术指标、多时间框架、斐波那契、形态、成交量、市场状态

### 简单趋势跟踪
需要：价格、技术指标、多时间框架、市场状态

## 🚀 下一步

1. 在`decision/engine.go`中集成新的数据结构
2. 为每个prompt创建配置文件
3. 实现`buildUserPromptByConfig`函数
4. 测试不同配置的Token消耗
5. 优化数据格式（markdown/json/compact）

