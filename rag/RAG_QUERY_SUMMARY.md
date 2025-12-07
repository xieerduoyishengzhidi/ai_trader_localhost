# RAG 查询方式总结

## ChromaDB 集合结构

### 基本信息
- **集合名称**: `pentosh_tweets`
- **数据量**: 3141 条
- **存储位置**: `rag/chroma_db/`
- **向量维度**: 768 维（moka-ai/m3e-base 模型）

### 数据结构

#### 文档（Documents）
由以下字段组合而成：
- `text` - 原始推文文本
- `info_overall_assessment` - 综合评估
- `gpt_explanation` - GPT 解释
- `gpt_reason` - GPT 原因

格式：`字段1 | 字段2 | 字段3`

#### 向量（Embeddings）
- **来源**: CSV 的 `embedding_context` 列（预计算）
- **模型**: moka-ai/m3e-base（768维）
- **格式**: JSON 数组，例如 `[0.814, 0.841, ...]`

#### 元数据（Metadata）
包含以下字段：
- `id` - 记录ID
- `tweet_id` - 推文ID
- `tweet_url` - 推文URL
- `screen_name` - 用户名（如 "Pentosh1"）
- `display_name` - 显示名称（如 "🐧 Pentoshi"）
- `created_at` - 创建时间
- `gpt_sentiment` - GPT情感分析（positive/negative）
- `gpt_assets` - 涉及的资产（JSON数组）
- `info_final_score` - 最终评分（-2 到 5）
- `is_market_related` - 是否与市场相关（true/false）

---

## 当前 RAG 查询方式（Supabase）

### 实现位置
- **文件**: `decision/rag.go`
- **客户端**: `SupabaseRAGClient`
- **调用位置**: `decision/engine.go` → `buildUserPromptWithRAG()`

### 查询流程

1. **提取交易员名称**
   ```go
   traderName := ExtractTraderNameFromPrompt(systemPromptTemplate)
   // 例如: "1bxxx_林凡_只做多" → "1bxxx"
   ```

2. **创建 RAG 客户端**
   ```go
   ragClient, err := NewSupabaseRAGClient()
   // 需要环境变量: SUPABASE_URL, SUPABASE_SERVICE_KEY
   ```

3. **检索历史观点**
   ```go
   ragResult, err := ragClient.RetrieveTraderViewpoints(traderName, 5)
   ```

4. **查询方式（Supabase REST API）**
   - **方法**: HTTP GET 请求到 Supabase REST API
   - **查询字段**: `text`, `info_overall_assessment`
   - **匹配方式**: ILIKE 模糊匹配（不区分大小写）
   - **查询语法**: `text.ilike.%交易员名称% OR info_overall_assessment.ilike.%交易员名称%`
   - **排序**: 按 `id` 降序
   - **限制**: 返回最多 5 条

5. **格式化结果**
   ```go
   ragContext := FormatRAGContext(ragResult)
   // 格式化为 Markdown，插入到 User Prompt 中
   ```

### 查询示例（Supabase）

```http
GET /rest/v1/clean_data?select=id,message_id,text,...&or=(text.ilike.%Pentosh1%,info_overall_assessment.ilike.%Pentosh1%)&order=id.desc&limit=5
```

### 结果格式

```go
type RAGResult struct {
    TraderName  string   // 交易员名称
    Viewpoints  []string // 历史观点列表（最多5条）
    ErrorReason string   // 错误原因（如果有）
}
```

### 观点提取逻辑

每条观点包含：
- 原始内容: `text`
- 资产分析: `gpt_assets`
- 市场相关性: `is_market_related_reason`
- 综合评估: `info_overall_assessment` 或 `info_final_score_json`

每条观点最多 500 字符。

---

## ChromaDB 查询方式（新）

### 优势
1. **向量相似度搜索**：基于语义相似度，而非关键词匹配
2. **本地存储**：无需 Supabase 服务，降低延迟
3. **预计算向量**：直接使用 CSV 中的向量，无需重新计算

### 查询方式

```python
# 1. 初始化客户端
client = chromadb.PersistentClient(path="rag/chroma_db")
collection = client.get_collection(name="pentosh_tweets")

# 2. 向量查询（需要先计算查询文本的向量）
results = collection.query(
    query_embeddings=[query_embedding],  # 768维向量
    n_results=5,
    where={"screen_name": "Pentosh1"}  # 可选：元数据过滤
)
```

### 与 Supabase 方式对比

| 特性 | Supabase（当前） | ChromaDB（新） |
|------|-----------------|----------------|
| 查询方式 | 关键词模糊匹配（ILIKE） | 向量相似度搜索 |
| 匹配精度 | 文本包含匹配 | 语义相似度匹配 |
| 数据源 | Supabase 数据库 | 本地 ChromaDB |
| 依赖 | 需要 Supabase 服务 | 仅需本地文件 |
| 性能 | 网络请求延迟 | 本地查询，速度快 |
| 向量使用 | 未使用向量 | 使用预计算向量 |

---

## 集成建议

### 方案1：替换 Supabase（推荐）
- 将 `SupabaseRAGClient` 替换为 `ChromaDBRAGClient`
- 通过 Python API 服务或直接调用 Python 脚本
- 优势：语义搜索更准确，本地查询更快

### 方案2：双模式支持
- 保留 Supabase 作为备选
- 优先使用 ChromaDB，失败时回退到 Supabase
- 优势：兼容性好，平滑迁移

### 方案3：混合查询
- 使用 ChromaDB 进行向量相似度搜索
- 使用元数据过滤（如 `screen_name`）精确匹配交易员
- 优势：结合语义搜索和精确匹配的优势

---

## 使用示例

### 当前方式（Supabase）
```go
// 在 buildUserPromptWithRAG() 中
ragClient, _ := NewSupabaseRAGClient()
ragResult, _ := ragClient.RetrieveTraderViewpoints("Pentosh1", 5)
ragContext := FormatRAGContext(ragResult)
```

### 新方式（ChromaDB）
```python
# Python 脚本
client = chromadb.PersistentClient(path="rag/chroma_db")
collection = client.get_collection(name="pentosh_tweets")

# 需要先计算查询文本的向量（使用相同的 embedding 模型）
query_embedding = compute_embedding("查询文本")

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"screen_name": "Pentosh1"}
)
```

