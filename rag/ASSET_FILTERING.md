# 资产过滤功能说明

## 功能概述

支持通过 `asset` 或 `assets` 参数过滤包含指定资产的文档。

## API 参数

### 1. 单个资产过滤（asset）

```json
{
    "asset": "SOL"
}
```

**说明**：
- 返回 `gpt_assets` 字段中包含 "SOL" 的文档
- 大小写不敏感（"SOL" = "sol" = "Sol"）

### 2. 多个资产过滤（assets）

```json
{
    "assets": ["SOL", "BTC"]
}
```

**说明**：
- 返回 `gpt_assets` 字段中包含任意一个资产的文档（OR 逻辑）
- 例如：`gpt_assets = ["SOL", "ETH"]` 会被 `assets: ["SOL", "BTC"]` 匹配（因为包含 "SOL"）

### 3. 不进行资产过滤（blur）

```json
{
    "asset": "blur"
}
```

或

```json
{
    "assets": ["blur"]
}
```

**说明**：
- 特殊值 `"blur"` 表示跳过资产过滤
- 即使提供了 `asset` 或 `assets` 参数，如果值为 `"blur"`，也不会进行资产过滤
- 适用于：只想用其他条件（如交易员、情感）过滤，不关心资产的情况

### 4. 参数优先级

- 如果同时提供 `asset` 和 `assets`，优先使用 `assets`
- 如果只提供 `asset`，使用单个资产过滤
- 如果都不提供，不过滤资产
- 如果 `asset="blur"` 或 `assets` 包含 `"blur"`，跳过资产过滤

## 使用示例

### 示例 1：查询某个交易员关于 SOL 的观点

```http
POST /query
{
    "trader_name": "Pentosh1",
    "asset": "SOL",
    "query_text": "价格预测",
    "limit": 5
}
```

### 示例 2：查询关于 SOL 或 BTC 的观点

```http
POST /query
{
    "assets": ["SOL", "BTC"],
    "query_text": "市场分析",
    "limit": 10
}
```

### 示例 3：查询某个交易员关于多个资产的观点

```http
POST /query
{
    "trader_name": "Pentosh1",
    "assets": ["SOL", "BTC", "ETH"],
    "sentiment": "positive",
    "query_text": "看涨信号",
    "limit": 5
}
```

### 示例 4：使用 query_by_name 接口

```http
POST /query_by_name
{
    "trader_name": "Pentosh1",
    "asset": "SOL",
    "limit": 5
}
```

### 示例 5：跳过资产过滤（blur）

```http
POST /query
{
    "trader_name": "Pentosh1",
    "asset": "blur",  // 不进行资产过滤
    "sentiment": "positive",
    "query_text": "市场分析",
    "limit": 10
}
```

**说明**：
- 即使提供了 `asset: "blur"`，也不会进行资产过滤
- 只使用其他条件（交易员、情感等）进行过滤
- 适用于：想查看某个交易员的所有观点，不限制资产类型

## 实现细节

### 数据格式

`gpt_assets` 字段存储为 JSON 字符串：
```json
["SOL", "BTC"]
```

### 过滤逻辑

1. 解析 `gpt_assets` JSON 字符串
2. 转换为大写进行比较（大小写不敏感）
3. 检查文档的资产列表是否包含目标资产（OR 逻辑）

### 性能说明

⚠️ **结果层面过滤**：
- 资产过滤在结果层面进行（不在数据库层面）
- 原因：`gpt_assets` 是 JSON 数组，ChromaDB 不支持直接查询
- 建议：先用其他条件（如 `trader_name`）缩小范围，再过滤资产

### 优化建议

1. **组合使用其他过滤条件**：
   ```json
   {
       "trader_name": "Pentosh1",  // 先过滤交易员（数据库层面）
       "asset": "SOL"              // 再过滤资产（结果层面）
   }
   ```

2. **限制结果数量**：
   ```json
   {
       "assets": ["SOL", "BTC"],
       "limit": 20  // 限制返回数量，减少过滤开销
   }
   ```

## 字段映射

| API 参数 | ChromaDB 字段 | 存储格式 | 过滤方式 |
|---------|--------------|---------|---------|
| `asset` | `gpt_assets` | JSON 字符串数组 | ⚠️ 结果层面 |
| `assets` | `gpt_assets` | JSON 字符串数组 | ⚠️ 结果层面 |

## 注意事项

1. **大小写不敏感**：`"SOL"`、`"sol"`、`"Sol"` 都会被匹配
2. **部分匹配**：如果 `gpt_assets = ["SOL", "BTC"]`，查询 `asset: "SOL"` 会匹配
3. **空值处理**：如果 `gpt_assets` 为空或不存在，不会匹配任何资产过滤条件
4. **性能考虑**：资产过滤在结果层面进行，如果数据量大，建议先用其他条件缩小范围
5. **blur 选项**：
   - `asset: "blur"` 或 `assets: ["blur"]` 会跳过资产过滤
   - 适用于只想用其他条件过滤的场景
   - 大小写不敏感（"blur" = "BLUR" = "Blur"）

