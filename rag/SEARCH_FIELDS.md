# 搜索字段和元数据过滤说明

## BM25 搜索字段

BM25 搜索在 **documents** 字段上进行，该字段由以下 CSV 列组合而成：

```
documents = text | info_overall_assessment | gpt_explanation | gpt_reason
```

### 字段说明

| CSV 列名 | 说明 | 示例 |
|---------|------|------|
| `text` | 原始推文文本 | "@FrankRemoulada vs its circulating float, its insignificant" |
| `info_overall_assessment` | 综合评估 | "观点简洁但信息增量低..." |
| `gpt_explanation` | GPT 解释 | "He argues that LINK's weekly buybacks..." |
| `gpt_reason` | GPT 原因 | "The trader dismisses the impact..." |

### BM25 搜索示例

当查询 "SOL" 时，BM25 会在以下文本中搜索：
- `text` 字段中包含 "SOL" 的推文
- `info_overall_assessment` 中包含 "SOL" 的评估
- `gpt_explanation` 中包含 "SOL" 的解释
- `gpt_reason` 中包含 "SOL" 的原因

**优势**：精确关键字匹配，如搜索 "SOL" 会精确匹配包含 "SOL" 的文档。

## 元数据过滤

### 支持的元数据字段

| 字段名 | 类型 | 过滤方式 | 说明 |
|--------|------|---------|------|
| `screen_name` | string | ✅ 数据库层面 | 用户名（如 "Pentosh1"） |
| `gpt_sentiment` | string | ✅ 数据库层面 | 情感（"positive"/"negative"） |
| `is_market_related` | bool | ✅ 数据库层面 | 是否与市场相关 |
| `gpt_assets` | JSON string | ⚠️ 结果层面 | 涉及的资产（如 `["SOL", "BTC"]`） |

### 过滤效率

#### ✅ 数据库层面过滤（高效）

```python
# 使用 where 条件，ChromaDB 在数据库层面过滤
where_clause = {
    "screen_name": "Pentosh1",
    "gpt_sentiment": "positive"
}
results = collection.get(where=where_clause)
```

**支持的字段**：
- `screen_name` (trader_name)
- `gpt_sentiment` (sentiment)
- `is_market_related`

**优势**：
- 只返回匹配的数据
- 利用数据库索引加速
- 内存占用小
- 速度快

#### ⚠️ 结果层面过滤（低效，但必要）

```python
# gpt_assets 是 JSON 数组，需要在结果中过滤
filtered = filter_by_asset(results, "SOL")
```

**支持的字段**：
- `gpt_assets` (asset)

**原因**：
- `gpt_assets` 存储为 JSON 字符串（如 `["SOL", "BTC"]`）
- ChromaDB 的 where 条件不支持 JSON 数组查询
- 需要在结果中解析 JSON 后过滤

## API 使用示例

### 1. 查询某个交易员的某个标的

```http
POST /query
Content-Type: application/json

{
    "trader_name": "Pentosh1",  // 数据库层面过滤 screen_name
    "asset": "SOL",              // 结果层面过滤 gpt_assets
    "query_text": "价格预测",    // BM25 + 向量搜索
    "limit": 5
}
```

**执行流程**：
1. ✅ 数据库层面：`where={"screen_name": "Pentosh1"}` 过滤交易员
2. ✅ BM25 搜索：在过滤后的 documents 上搜索 "价格预测"
3. ✅ 向量搜索：在过滤后的数据上搜索 "价格预测"
4. ✅ RRF 合并：合并 BM25 和向量搜索结果
5. ⚠️ 结果层面：过滤 `gpt_assets` 包含 "SOL" 的文档

### 2. 查询某个交易员的看涨观点

```http
POST /query
{
    "trader_name": "Pentosh1",
    "sentiment": "positive",     // 数据库层面过滤 gpt_sentiment
    "query_text": "市场分析",
    "limit": 5
}
```

### 3. 查询某个标的的所有市场相关观点

```http
POST /query
{
    "asset": "BTC",
    "is_market_related": true,   // 数据库层面过滤
    "query_text": "价格走势",
    "limit": 10
}
```

### 4. 组合查询：交易员 + 标的 + 情感

```http
POST /query
{
    "trader_name": "Pentosh1",   // 数据库层面
    "asset": "SOL",               // 结果层面
    "sentiment": "positive",     // 数据库层面
    "is_market_related": true,   // 数据库层面
    "query_text": "价格预测",
    "limit": 5
}
```

## 字段映射表

| API 参数 | ChromaDB 元数据字段 | 过滤方式 | 说明 |
|---------|-------------------|---------|------|
| `trader_name` | `screen_name` | ✅ 数据库层面 | 交易员用户名 |
| `asset` | `gpt_assets` | ⚠️ 结果层面 | 标的资产（JSON 数组） |
| `sentiment` | `gpt_sentiment` | ✅ 数据库层面 | 情感（positive/negative） |
| `is_market_related` | `is_market_related` | ✅ 数据库层面 | 是否市场相关 |

## 性能建议

1. **优先使用数据库层面过滤**：
   - ✅ `trader_name` → `screen_name`
   - ✅ `sentiment` → `gpt_sentiment`
   - ✅ `is_market_related`

2. **合理使用结果层面过滤**：
   - ⚠️ `asset` → `gpt_assets`（如果数据量大，建议先用其他条件缩小范围）

3. **组合策略**：
   ```
   先用数据库层面过滤缩小范围
   ↓
   然后进行 BM25 + 向量搜索
   ↓
   最后用结果层面过滤精确匹配
   ```

## BM25 vs 向量搜索

| 特性 | BM25 | 向量搜索 |
|------|------|---------|
| **搜索字段** | documents（text + info + explanation + reason） | documents（同上） |
| **匹配方式** | 关键字精确匹配 | 语义相似度匹配 |
| **优势** | "SOL" → 精确匹配 "SOL" | "通胀数据" → 匹配 "CPI" |
| **劣势** | 不擅长语义理解 | "SOL" 可能匹配到 "ETH" |

**混合搜索（RRF）**：结合两者优势，既保证精确匹配，又保证语义理解。

