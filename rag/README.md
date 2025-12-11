# RAG 模块 - ChromaDB 集成

将 Pentoshi 的历史推文数据导入 ChromaDB，用于 RAG（检索增强生成）功能。

## 功能特点

- ✅ 使用预计算的向量（`embedding_context` 列），无需配置 Embedding Function
- ✅ 支持批量导入，自动处理大量数据
- ✅ 持久化存储，数据保存在本地
- ✅ HTTP API 服务，Go 代码可直接调用
- ✅ 包含完整的元数据（推文ID、时间、情感分析等）

## 安装依赖

```powershell
pip install -r rag/requirements.txt
```

## 使用方法

### 1. 导入 CSV 数据到 ChromaDB

```powershell
python rag/import_to_chromadb.py
```

脚本会：
- 读取 `pentosh_all.csv` 文件
- 解析 `embedding_context` 列的向量数据
- 将所有有效数据导入 ChromaDB
- 数据库保存在 `rag/chroma_db/` 目录

### 2. 启动 ChromaDB RAG API 服务

```powershell
python rag/chromadb_api.py
```

服务默认运行在 `http://127.0.0.1:8765`

可以通过环境变量配置：
```powershell
$env:RAG_API_HOST="127.0.0.1"
$env:RAG_API_PORT="8765"
python rag/chromadb_api.py
```

### 3. 在 Go 代码中使用

Go 代码会自动调用 ChromaDB RAG API，无需额外配置。

如果需要自定义 API 地址，设置环境变量：
```powershell
$env:CHROMADB_RAG_API_URL="http://127.0.0.1:8765"
```

### 4. Level 2 因果逻辑引擎（新闻 → JSON）

```powershell
$env:DEEPSEEK_API_KEY="your_key"
# 可选：设置 pentosh1.db 路径（默认 ../filter/pentosh1.db）
# $env:PENTOSHI_DB_PATH="E:\nofx-dev\filter\pentosh1.db"
python rag/logic_level2.py
```

- 输入：新闻（title/summary 或通过 URL 抓正文）+ 市场上下文（可选，默认取 pentosh1.db 的 macro 字段）+ RAG 记忆（自动调用 `/query`，使用抓取后的正文）。
- 输出：新版因果 JSON（signal + causal_logic + invalidation + is_actionable），可直接写入决策/数据库。

## API 接口

### 健康检查
```http
GET /health
```

### 根据交易员名称查询
```http
POST /query_by_name
Content-Type: application/json

{
    "trader_name": "Pentosh1",
    "limit": 5
}
```

### 向量查询（高级）
```http
POST /query
Content-Type: application/json

{
    "trader_name": "Pentosh1",
    "query_embedding": [0.1, 0.2, ...],
    "limit": 5
}
```

## 数据结构

### 文档文本
由以下字段组合而成：
- `text` - 原始推文文本
- `info_overall_assessment` - 综合评估
- `gpt_explanation` - GPT 解释
- `gpt_reason` - GPT 原因

### 元数据
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

## 配置

- **数据库路径**: `rag/chroma_db/`
- **集合名称**: `pentosh_tweets`
- **CSV 文件**: `pentosh_all.csv`（项目根目录）
- **API 地址**: `http://127.0.0.1:8765`（默认）

## 注意事项

1. **向量维度**：确保查询时使用的向量维度与导入时一致（768维）
2. **API 服务**：需要先启动 `chromadb_api.py` 服务，Go 代码才能调用
3. **数据量**：3000+ 条数据对 ChromaDB 来说非常小，性能不会有问题
4. **服务管理**：建议使用进程管理器（如 PM2）管理 API 服务

## 迁移说明

已从 Supabase 迁移到 ChromaDB：
- ✅ 删除了 Supabase 相关代码
- ✅ 使用本地 ChromaDB 存储
- ✅ 通过 HTTP API 提供服务
- ✅ 保持相同的 Go 接口，无需修改调用代码
