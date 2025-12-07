# Supabase → ChromaDB 迁移总结

## 迁移完成 ✅

已成功从 Supabase RAG 迁移到 ChromaDB RAG。

## 变更内容

### 1. 代码变更

#### `decision/rag.go`
- ❌ 删除：`SupabaseRAGClient` 结构体
- ❌ 删除：`NewSupabaseRAGClient()` 函数
- ❌ 删除：`CleanDataRow` 结构体（不再需要）
- ❌ 删除：`extractViewpoint()` 函数（逻辑移至 API）
- ❌ 删除：`coerceToText()` 函数（不再需要）
- ✅ 新增：`ChromaDBRAGClient` 结构体
- ✅ 新增：`NewChromaDBRAGClient()` 函数
- ✅ 保留：`RAGResult` 结构体（接口不变）
- ✅ 保留：`ExtractTraderNameFromPrompt()` 函数
- ✅ 保留：`FormatRAGContext()` 函数

#### `decision/engine.go`
- ✅ 更新：`buildUserPromptWithRAG()` 中使用 `NewChromaDBRAGClient()` 替代 `NewSupabaseRAGClient()`

### 2. 新增文件

- ✅ `rag/chromadb_api.py` - ChromaDB RAG HTTP API 服务
- ✅ `rag/start_api.ps1` - API 服务启动脚本
- ✅ `rag/MIGRATION_SUMMARY.md` - 本文件

### 3. 更新文件

- ✅ `rag/requirements.txt` - 添加 Flask 依赖
- ✅ `rag/README.md` - 更新使用说明
- ✅ `docs/RAG_USAGE.md` - 更新文档
- ✅ `env.example` - 删除 Supabase 配置，添加 ChromaDB RAG API 配置

### 4. 删除/废弃

- ❌ Supabase 相关环境变量：`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CLEAN_DATA_TABLE_NAME`
- ⚠️ `3_retrieve_clean_data_embeddings.py` - 保留但不再用于 RAG（仅用于数据迁移）

## 使用方式变化

### 之前（Supabase）

1. 配置环境变量：
   ```powershell
   $env:SUPABASE_URL="https://xxx.supabase.co"
   $env:SUPABASE_SERVICE_KEY="xxx"
   ```

2. Go 代码直接调用 Supabase REST API

### 现在（ChromaDB）

1. 启动 ChromaDB RAG API 服务：
   ```powershell
   python rag/chromadb_api.py
   # 或
   .\rag\start_api.ps1
   ```

2. （可选）配置 API 地址：
   ```powershell
   $env:CHROMADB_RAG_API_URL="http://127.0.0.1:8765"
   ```

3. Go 代码调用本地 API 服务

## 优势

1. ✅ **本地存储**：无需外部 Supabase 服务
2. ✅ **更快速度**：本地查询，无网络延迟
3. ✅ **向量支持**：已导入预计算向量，未来可扩展语义搜索
4. ✅ **接口兼容**：Go 代码接口保持不变，无需修改调用代码
5. ✅ **易于调试**：本地服务，便于排查问题

## 注意事项

1. ⚠️ **服务依赖**：需要先启动 `chromadb_api.py` 服务
2. ⚠️ **数据导入**：首次使用需要运行 `python rag/import_to_chromadb.py`
3. ⚠️ **服务管理**：建议使用进程管理器（如 PM2）管理 API 服务

## 回滚方案

如果需要回滚到 Supabase：

1. 恢复 `decision/rag.go` 中的 `SupabaseRAGClient` 代码
2. 恢复 `decision/engine.go` 中的调用
3. 配置 Supabase 环境变量
4. 删除或停止 ChromaDB RAG API 服务

## 测试验证

迁移后请验证：

1. ✅ API 服务健康检查：`curl http://127.0.0.1:8765/health`
2. ✅ Go 代码调用：检查日志中是否有 "✅ RAG检索成功"
3. ✅ 数据查询：确认能正确返回历史观点

## 相关文档

- [RAG 使用指南](../docs/RAG_USAGE.md)
- [ChromaDB 导入说明](./README.md)
- [RAG 查询方式总结](./RAG_QUERY_SUMMARY.md)

