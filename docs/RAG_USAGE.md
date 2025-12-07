# RAG 功能使用指南

## 功能概述

RAG（Retrieval-Augmented Generation）功能允许系统从 ChromaDB 数据库中检索历史交易观点，并将其添加到AI决策的用户提示词中，帮助AI基于历史经验做出更好的决策。

## 工作原理

1. **交易员名称提取**：从prompt文件名中提取第一个名字作为交易员标识
   - 例如：`林凡.txt` → 交易员名称: `林凡`
   - 例如：`1bxxx_林凡_只做多.txt` → 交易员名称: `1bxxx`

2. **历史观点检索**：使用交易员名称在 ChromaDB 中搜索相关记录
   - 搜索字段：`screen_name`、`display_name`
   - 使用元数据过滤和文本匹配

3. **观点格式化**：提取的观点包含以下信息：
   - 原始推文文本
   - 综合评估
   - GPT 解释和原因

4. **插入提示词**：在用户提示词的技术指标部分之后，插入格式化的历史观点

## 配置要求

### 1. 启动 ChromaDB RAG API 服务

```powershell
# 方式1：直接运行
python rag/chromadb_api.py

# 方式2：使用启动脚本
.\rag\start_api.ps1
```

服务默认运行在 `http://127.0.0.1:8765`

### 2. 环境变量配置（可选）

```powershell
# API 服务地址（可选，默认 http://127.0.0.1:8765）
$env:CHROMADB_RAG_API_URL="http://127.0.0.1:8765"

# API 服务端口（可选，默认 8765）
$env:RAG_API_PORT="8765"
```

## 数据准备

### 1. 导入数据到 ChromaDB

首次使用需要导入数据：

```powershell
python rag/import_to_chromadb.py
```

这会读取 `pentosh_all.csv` 文件并导入到 ChromaDB。

### 2. 检查数据

```powershell
python rag/inspect_chromadb.py
```

## 使用示例

### 1. 创建交易员提示词文件

在`prompts/`目录下创建以交易员名称命名的提示词文件：

```
prompts/
  ├── Pentosh1.txt
  ├── 1bxxx_林凡_只做多.txt
  └── ...
```

### 2. 系统自动调用

当使用自定义 prompt 模板时，系统会：
1. 从 prompt 文件名提取交易员名称
2. 调用 ChromaDB RAG API 检索历史观点
3. 将观点插入到 User Prompt 中
4. AI 基于历史观点做出决策

## API 接口

### 健康检查
```http
GET http://127.0.0.1:8765/health
```

### 查询历史观点
```http
POST http://127.0.0.1:8765/query_by_name
Content-Type: application/json

{
    "trader_name": "Pentosh1",
    "limit": 5
}
```

响应：
```json
{
    "trader_name": "Pentosh1",
    "viewpoints": [
        "观点1...",
        "观点2...",
        ...
    ],
    "error_reason": ""
}
```

## 故障排查

### 1. RAG 服务未启动

**症状**：Go 代码报错 "HTTP请求失败"

**解决**：
```powershell
# 检查服务是否运行
curl http://127.0.0.1:8765/health

# 启动服务
python rag/chromadb_api.py
```

### 2. 数据未导入

**症状**：查询返回空结果

**解决**：
```powershell
# 导入数据
python rag/import_to_chromadb.py

# 检查数据
python rag/inspect_chromadb.py
```

### 3. 依赖缺失

**症状**：Python 报错 "No module named 'chromadb'"

**解决**：
```powershell
pip install -r rag/requirements.txt
```

## 技术细节

### ChromaDB 集合结构

- **集合名称**: `pentosh_tweets`
- **数据量**: 3141+ 条
- **向量维度**: 768 维（moka-ai/m3e-base）
- **存储位置**: `rag/chroma_db/`

### 查询方式

1. **元数据过滤**：根据 `screen_name` 或 `display_name` 匹配交易员
2. **文本匹配**：如果精确匹配失败，使用模糊匹配
3. **向量查询**（高级）：支持使用预计算的向量进行语义搜索

### 性能优化

- 数据量小（3000+条），查询速度很快
- 本地存储，无网络延迟
- 批量查询，一次返回多条结果

## 迁移说明

已从 Supabase 迁移到 ChromaDB：
- ✅ 使用本地 ChromaDB 存储，无需外部服务
- ✅ 通过 HTTP API 提供服务，Go 代码接口保持不变
- ✅ 支持向量相似度搜索（未来可扩展）
- ✅ 更快的查询速度，更低的延迟

## 相关文档

- [RAG 查询方式总结](../rag/RAG_QUERY_SUMMARY.md)
- [ChromaDB 导入脚本](../rag/README.md)
