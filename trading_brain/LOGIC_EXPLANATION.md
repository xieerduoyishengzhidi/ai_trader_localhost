# Trading Brain 逻辑说明文档

## 📅 日期设置逻辑

### 1. 主数据包的日期

```python
# 在 aggregate_all_data() 方法中 (第324行)
"date": datetime.now().strftime("%Y-%m-%d")
```

**说明**:
- **date**: 使用**当前系统日期**（运行脚本时的日期）
- **格式**: `YYYY-MM-DD` (例如: `2025-12-06`)
- **用途**: 作为数据包的日期标识，用于文件名和记录

**示例**:
- 如果今天是 2025-12-06，则 `date = "2025-12-06"`
- 文件名会生成: `Daily_Context_2025-12-06.json`

---

## 📊 第一层级：全球宏观"水源" - 时间设置

### 时间范围配置

#### FRED API 数据（周频/日频数据）

**Fed Net Liquidity (WALCL - TGA - RRP)**:
```python
start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")
```
- **查询范围**: 最近30天
- **数据频率**: 周频（FRED数据）
- **获取方式**: 取数组最后一个值（最新值）

**US02Y (2年美债) & Yield Curve (10Y-2Y)**:
```python
start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")
```
- **查询范围**: 最近60天
- **数据频率**: 日频（FRED数据）
- **获取方式**: 取数组最后一个值（最新值）

#### yfinance 数据（日频数据）

**DXY, US10Y, SPX/NDX, CNY**:
```python
period = "3mo"  # 3个月
interval = "1d"  # 日线
```
- **查询范围**: 最近3个月
- **数据频率**: 日频
- **获取方式**: 取数组最后一个值（最新值）

---

## 📊 第二层级：Crypto 原生"燃料" - 时间设置

### 数据来源和频率

**Stablecoin Market Cap**:
- **来源**: DeFi Llama API
- **频率**: 实时（当前值）
- **时间范围**: 无历史查询，只获取当前总市值

**BTC ETF Net Inflow**:
- **来源**: Farside.co.uk (网页爬取)
- **频率**: 每日更新（T+1，即昨天的数据）
- **时间范围**: 获取最新一行数据（通常是昨天收盘数据）

**注意**: 
- ETF数据是T+1的，今天运行脚本获取的是昨天的数据
- 如果今天是周末，可能获取到的是周五的数据

---

## 📊 第三层级：市场结构与轮动 - 时间设置

**BTC Dominance, ETH/BTC Ratio, TOTAL3**:
- **来源**: CoinGecko API
- **频率**: 实时（当前值）
- **时间范围**: 无历史查询，只获取当前值

---

## 📊 第四层级：情绪与博弈 - 时间设置

**Funding Rate, Open Interest, Long/Short Ratio**:
- **来源**: Binance API (通过 ccxt)
- **频率**: 实时（当前值）
- **时间范围**: 无历史查询，只获取当前值

**Fear & Greed Index**:
- **来源**: Alternative.me API
- **频率**: 每日更新
- **时间范围**: 获取最新值

---

## 🔍 数据填充策略

### ✅ 当前实现：无填充，使用最新值

**第一层级（宏观数据）**:
- 如果数据获取失败 → `indicators` 字典为空
- 如果部分指标失败 → 只保存成功的指标
- **不填充**: 失败的数据不会用默认值填充

**第二、三、四层级（币圈数据）**:
- 如果 API 调用失败 → 返回空字典 `{}`
- 如果部分字段缺失 → 使用 `None` 值
- **不填充**: 缺失的字段保持为 `None`

### 📝 数据获取逻辑

```python
# 示例：获取最新值
if data and data.get("data") and len(data["data"]) > 0:
    latest = data["data"][-1]  # 取最后一个（最新）
    value = latest.get("value")
    if value is not None:
        # 保存数据
```

**关键点**:
1. **只取最新值**: 所有指标都只保存最新一个数据点
2. **不保存历史**: 不保存时间序列，只保存当前快照
3. **无插值**: 如果某个日期没有数据，不会填充

---

## 🕐 时间戳说明

### 数据包中的时间戳

```python
{
    "timestamp": "2025-12-06T16:06:15.385551",  # ISO格式，精确到微秒
    "date": "2025-12-06",                        # 日期字符串
    "layer1_global_liquidity": {
        "timestamp": "2025-12-06T16:05:25.614405"  # Layer1获取时的时间戳
    }
}
```

**说明**:
- `timestamp`: 数据包生成时的完整时间戳（ISO 8601格式）
- `date`: 日期部分（用于文件名）
- `layer1.timestamp`: Layer1数据获取时的时间戳（可能比主时间戳早几秒）

---

## 📋 数据获取时间线示例

假设在 **2025-12-06 16:06:15** 运行脚本：

```
16:05:25 → 开始获取 Layer1 数据
  ├─ 16:05:26 → 调用 FRED API (WALCL)
  ├─ 16:05:27 → 调用 FRED API (TGA)
  ├─ 16:05:28 → 调用 FRED API (RRP)
  ├─ 16:05:30 → 调用 yfinance (DXY)
  ├─ 16:05:32 → 调用 yfinance (US10Y)
  └─ 16:05:35 → Layer1 完成

16:05:36 → 开始获取 Layer2-4 数据
  ├─ 16:05:37 → 调用 /api/crypto/all
  │   ├─ 16:05:38 → Binance API (资金费率、OI)
  │   ├─ 16:05:40 → Farside (ETF数据)
  │   ├─ 16:05:42 → DeFi Llama (稳定币)
  │   └─ 16:05:44 → CoinGecko (BTC.D)
  └─ 16:05:45 → Layer2-4 完成

16:06:15 → 生成最终数据包并保存
```

---

## ⚠️ 数据时效性说明

### 实时数据 vs 延迟数据

| 数据类型 | 时效性 | 说明 |
|---------|--------|------|
| **FRED数据** | T+1 到 T+7 | 周频数据可能延迟几天 |
| **yfinance数据** | T+0 (实时) | 市场开盘时实时更新 |
| **Binance期货数据** | T+0 (实时) | 实时更新 |
| **ETF资金流向** | T+1 | 昨天的数据 |
| **BTC Dominance** | T+0 (实时) | 实时计算 |
| **Fear & Greed** | T+0 (每日) | 每日更新 |

### 注意事项

1. **FRED数据延迟**: 
   - 周频数据（如WALCL）可能延迟几天
   - 如果查询今天的数据，可能返回空数组
   - 因此使用60天范围，确保能获取到数据

2. **ETF数据延迟**:
   - Farside 显示的是T+1数据
   - 周末可能没有新数据

3. **市场休市**:
   - 如果市场休市，yfinance可能返回空数据
   - 使用 `3mo` 周期可以避免这个问题

---

## 🔧 如何修改时间范围

### 修改第一层级时间范围

```python
# 在 get_layer1_global_liquidity() 方法中

# 修改为90天
start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

# 修改yfinance周期为6个月
period = "6mo"
```

### 修改数据获取日期

如果需要获取特定日期的数据（而不是今天）：

```python
# 在 aggregate_all_data() 中
target_date = datetime(2025, 1, 6)  # 指定日期
"date": target_date.strftime("%Y-%m-%d")
```

---

## 📊 数据完整性检查

### 当前实现

```python
# 检查数据是否存在
if data and data.get("data") and len(data["data"]) > 0:
    # 有数据，处理
else:
    # 无数据，跳过（不填充）
```

### 建议改进（未来可添加）

1. **数据填充**: 如果今天没有数据，使用最近有数据的日期
2. **历史回填**: 保存历史数据，用于趋势分析
3. **数据验证**: 检查数据是否过期（如超过7天）

---

## 🎯 总结

### 日期设置总结

| 层级 | 日期设置 | 时间范围 | 数据频率 |
|-----|---------|---------|---------|
| **主数据包** | `datetime.now()` | 当前日期 | 一次性快照 |
| **Layer1 - FRED** | 30-60天前 → 今天 | 30-60天 | 周频/日频 |
| **Layer1 - yfinance** | 3个月前 → 今天 | 3个月 | 日频 |
| **Layer2 - ETF** | T+1（昨天） | 单点数据 | 每日 |
| **Layer2-4 - Crypto** | 实时 | 当前值 | 实时 |

### 数据填充策略

- ✅ **当前**: 无填充，失败的数据保持为空或None
- ⚠️ **建议**: 可以添加默认值填充或使用最近可用数据

