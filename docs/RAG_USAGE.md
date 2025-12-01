# RAG 功能使用指南

## 功能概述

RAG（Retrieval-Augmented Generation）功能允许系统从Supabase数据库中检索历史交易观点，并将其添加到AI决策的用户提示词中，帮助AI基于历史经验做出更好的决策。

## 工作原理

1. **交易员名称提取**：从prompt文件名中提取第一个名字作为交易员标识
   - 例如：`林凡.txt` → 交易员名称: `林凡`
   - 例如：`1bxxx_林凡_只做多.txt` → 交易员名称: `1bxxx`

2. **历史观点检索**：使用交易员名称在Supabase的`clean_data`表中搜索相关记录
   - 搜索字段：`text`、`info_overall_assessment`
   - 使用不区分大小写的模糊匹配（ILIKE）

3. **观点格式化**：提取的观点包含以下信息：
   - 原始内容
   - 资产分析
   - 市场相关性
   - 综合评估

4. **插入提示词**：在用户提示词的技术指标部分之后，插入格式化的历史观点

## 配置要求

在`.env`文件中需要配置以下参数：

```env
# Supabase配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# 数据库表配置
CLEAN_DATA_TABLE_NAME=clean_data
```

## 数据库表结构

`clean_data`表应包含以下字段（参考`3_retrieve_clean_data_embeddings.py`）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | int/string | 主键 |
| `message_id` | string | 消息ID |
| `text` | text | 原始文本内容 |
| `original_payload` | jsonb | 原始数据 |
| `gpt_assets` | jsonb | GPT资产分析 |
| `is_market_related_reason` | jsonb | 市场相关性原因 |
| `info_overall_assessment` | text | 综合评估 |
| `info_final_score_json` | jsonb | 最终评分 |
| `info_final_score` | float | 评分数值 |
| `embedding_context` | vector | 向量嵌入 |

## 使用示例

### 1. 创建交易员提示词文件

在`prompts/`目录下创建以交易员名称命名的提示词文件：

```
prompts/
  ├── 林凡.txt
  ├── 1bxxx_林凡_只做多.txt
  └── taro_long_prompts.txt
```

### 2. 在Supabase中准备历史数据

确保`clean_data`表中有相关交易员的历史记录，例如：

```json
{
  "id": 1,
  "text": "林凡：BTC突破65000，建议做多",
  "info_overall_assessment": "看涨信号强烈，技术面支持",
  "gpt_assets": "BTC, ETH",
  ...
}
```

### 3. 系统自动调用

当使用指定的prompt模板名称时，系统会自动：
1. 提取交易员名称（例如从`林凡.txt`提取`林凡`）
2. 在Supabase中检索相关历史观点（最多5条）
3. 将观点格式化后插入用户提示词

### 4. 输出格式

在用户提示词中，历史观点会以如下格式呈现：

```
## 📚 历史观点参考

**这是历史上该交易员'林凡'的观点，用该观点辅助你的现有判断**

1. 原始内容: BTC突破65000，建议做多 | 综合评估: 看涨信号强烈，技术面支持

2. 原始内容: ETH回调到支撑位，考虑加仓 | 综合评估: 支撑位有效，风险可控

...
```

## 代码结构

### 核心文件

- `decision/rag.go`：RAG检索实现
  - `SupabaseRAGClient`：Supabase客户端
  - `RetrieveTraderViewpoints()`：检索交易员观点
  - `ExtractTraderNameFromPrompt()`：提取交易员名称
  - `FormatRAGContext()`：格式化RAG上下文

- `decision/engine.go`：决策引擎集成
  - `buildUserPromptWithRAG()`：构建带RAG的用户提示词

### 数据流

```
prompt文件名 → 提取交易员名称 → Supabase查询 → 提取观点 → 格式化 → 插入提示词 → AI决策
```

## 错误处理

系统采用优雅降级策略：

1. **Supabase配置缺失**：跳过RAG，使用原始提示词
2. **数据库查询失败**：记录警告日志，继续执行
3. **未找到历史观点**：记录信息日志，不影响决策流程

日志输出示例：

```
✅ RAG检索成功: 交易员'林凡'找到3条历史观点
⚠️  RAG检索失败: database connection timeout
ℹ️  交易员'新手'未找到历史观点
```

## 性能优化

1. **查询限制**：默认最多检索5条历史观点
2. **内容截断**：每条观点最多500字符
3. **HTTP超时**：10秒超时设置，避免长时间等待
4. **缓存建议**：可以在未来版本中添加内存缓存

## 安全注意事项

1. **敏感信息**：`SUPABASE_SERVICE_KEY`是敏感信息，不要提交到版本控制
2. **权限控制**：使用Service Role Key时注意权限范围
3. **SQL注入**：使用参数化查询，避免SQL注入风险

## 调试技巧

### 1. 检查Supabase连接

```bash
# 测试Supabase URL是否可访问
curl -X GET "$SUPABASE_URL/rest/v1/clean_data?limit=1" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY"
```

### 2. 查看RAG日志

运行系统时，注意观察以下日志：

```
✅ RAG检索成功: 交易员'林凡'找到3条历史观点
```

### 3. 手动测试查询

使用Supabase控制台的SQL Editor测试查询：

```sql
SELECT id, text, info_overall_assessment 
FROM clean_data 
WHERE text ILIKE '%林凡%' 
   OR info_overall_assessment ILIKE '%林凡%'
ORDER BY id DESC 
LIMIT 5;
```

## 未来改进方向

1. **向量搜索**：使用`embedding_context`字段进行语义相似度搜索
2. **相关性排序**：基于时间、相关性等维度排序
3. **观点聚合**：对相似观点进行聚合和去重
4. **缓存机制**：添加内存缓存提高性能
5. **多语言支持**：支持更多语言的观点检索

## 参考资料

- Python参考实现：`3_retrieve_clean_data_embeddings.py`
- 表结构配置：`config.py`
- 环境变量示例：`env.example`
- Supabase文档：https://supabase.com/docs

