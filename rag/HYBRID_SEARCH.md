# BM25 + 向量混合搜索说明

## 问题分析

### 1. 效率问题（The "Scan" Problem）

**之前的问题**：
```python
# ❌ 低效：获取所有数据然后在 Python 中过滤
all_results = collection.get(limit=5000)
for doc in all_results:
    if trader_name in doc.metadata['screen_name']:
        # 过滤...
```

**现在的解决方案**：
```python
# ✅ 高效：使用 ChromaDB 的 where 过滤（数据库层面）
results = collection.get(where={"screen_name": trader_name})
```

**优势**：
- 数据库层面过滤，速度快
- 只返回匹配的数据，内存占用小
- 支持索引加速

### 2. 关键字匹配问题（The "Ticker" Problem）

**问题场景**：
- 搜索 "SOL" → 向量搜索可能返回 "ETH"（语义相近，都是公链）
- 但用户想要的是 Solana，不是 Ethereum

**解决方案：BM25 + 向量混合搜索**

- **BM25**：擅长精确关键字匹配
  - 搜索 "SOL" → 精确匹配包含 "SOL" 的文档
  - 搜索 "CPI" → 精确匹配包含 "CPI" 的文档

- **向量搜索**：擅长语义理解
  - 搜索 "通胀数据" → 语义匹配到 "CPI"
  - 搜索 "市场崩盘" → 语义匹配到 "暴跌"

- **混合搜索（RRF）**：结合两者优势
  - 同时运行 BM25 和向量搜索
  - 使用 RRF (Reciprocal Rank Fusion) 算法合并结果
  - 既保证精确匹配，又保证语义理解

## 实现细节

### BM25 搜索

```python
from rank_bm25 import BM25Okapi

# 1. 构建索引（带缓存）
tokenized_docs = [tokenize(doc) for doc in documents]
bm25 = BM25Okapi(tokenized_docs)

# 2. 搜索
query_tokens = tokenize(query_text)
scores = bm25.get_scores(query_tokens)
```

### 向量搜索

```python
from sentence_transformers import SentenceTransformer

# 1. 加载模型（moka-ai/m3e-base，与导入时一致）
model = SentenceTransformer("moka-ai/m3e-base")

# 2. 计算查询向量
query_embedding = model.encode(query_text)

# 3. ChromaDB 向量搜索
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=limit,
    where={"screen_name": trader_name}  # 数据库层面过滤
)
```

### RRF 合并

```python
def rrf_merge(vector_results, bm25_results, k=60):
    """Reciprocal Rank Fusion"""
    rrf_scores = {}
    
    # 向量搜索结果
    for rank, (doc_id, score) in enumerate(vector_results):
        rrf_scores[doc_id] = 1.0 / (k + rank + 1)
    
    # BM25 搜索结果
    for rank, (doc_id, score) in enumerate(bm25_results):
        rrf_scores[doc_id] += 1.0 / (k + rank + 1)
    
    # 按 RRF 分数排序
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
```

## 使用示例

### 1. 精确关键字搜索

```http
POST /query
{
    "trader_name": "Pentosh1",
    "query_text": "SOL",
    "limit": 5
}
```

**结果**：
- BM25 匹配：包含 "SOL" 的文档（精确匹配）
- 向量匹配：语义相关的文档（如 "Solana", "solana"）
- RRF 合并：优先返回精确匹配，同时包含语义相关

### 2. 语义搜索

```http
POST /query
{
    "trader_name": "Pentosh1",
    "query_text": "通胀数据",
    "limit": 5
}
```

**结果**：
- BM25 匹配：包含 "通胀" 或 "数据" 的文档
- 向量匹配：语义相关的文档（如 "CPI", "通胀率"）
- RRF 合并：结合关键字和语义匹配

### 3. 交易员名称查询（自动混合搜索）

```http
POST /query_by_name
{
    "trader_name": "Pentosh1",
    "limit": 5
}
```

**内部处理**：
- 使用交易员名称作为查询文本
- 同时进行 BM25 和向量搜索
- 既匹配精确的交易员名称，也匹配相关的推文内容

## 性能优化

### 1. 数据库层面过滤

```python
# ✅ 使用 where 过滤（高效）
results = collection.get(where={"screen_name": trader_name})

# ❌ 避免在 Python 中过滤（低效）
all_results = collection.get(limit=5000)
filtered = [r for r in all_results if r.metadata['screen_name'] == trader_name]
```

### 2. BM25 索引缓存

```python
# 索引只构建一次，后续查询复用
_bm25_index = None
_documents_cache = None

def build_bm25_index(collection, trader_name):
    global _bm25_index, _documents_cache
    if _bm25_index is not None:
        return _bm25_index, _documents_cache
    # 构建索引...
```

### 3. Embedding 模型懒加载

```python
# 模型只在首次使用时加载
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model
```

## 配置

### 环境变量

```bash
# Embedding 模型（必须与导入时使用的模型一致）
EMBEDDING_MODEL=moka-ai/m3e-base

# API 服务配置
RAG_API_HOST=127.0.0.1
RAG_API_PORT=8765
```

### RRF 参数

```python
# k 值控制 RRF 的平滑度
# 较小的 k：更偏向排名靠前的结果
# 较大的 k：更平滑的合并
k = 60  # 默认值，可根据效果调整
```

## 优势总结

1. ✅ **高效查询**：使用数据库层面过滤，避免全表扫描
2. ✅ **精确匹配**：BM25 保证关键字精确匹配（如 "SOL"）
3. ✅ **语义理解**：向量搜索理解语义（如 "通胀" → "CPI"）
4. ✅ **最佳平衡**：RRF 合并两者，兼顾精确性和相关性
5. ✅ **性能优化**：索引缓存、模型懒加载、数据库过滤

## 对比

| 特性 | 之前（纯向量/全扫描） | 现在（BM25+向量混合） |
|------|---------------------|---------------------|
| 关键字匹配 | ❌ 弱 | ✅ 强（BM25） |
| 语义理解 | ✅ 强 | ✅ 强（向量） |
| 查询效率 | ❌ 低（全扫描） | ✅ 高（数据库过滤） |
| 内存占用 | ❌ 高（加载全部） | ✅ 低（只加载匹配） |
| 精确匹配 | ❌ 弱（"SOL"可能返回"ETH"） | ✅ 强（"SOL"精确匹配） |

