#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration module for embedding and Supabase settings."""

import os
from typing import List

# ============================================================================
# Embedding 配置
# ============================================================================

# Embedding 模型选择
# 推荐模型（按性能排序）:
# 1. moka-ai/m3e-base (默认) - 中文优化，768维，速度快，适合中文文本
# 2. moka-ai/m3e-large - 中文优化，1024维，精度更高但速度较慢
# 3. sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 - 多语言，384维，速度快
# 4. sentence-transformers/paraphrase-multilingual-mpnet-base-v2 - 多语言，768维，精度高
# 5. BAAI/bge-large-zh-v1.5 - 中文优化，1024维，精度最高但速度最慢
# 6. BAAI/bge-base-zh-v1.5 - 中文优化，768维，平衡性能和精度
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "moka-ai/m3e-base")

# Embedding 批处理大小（一次处理多少条文本）
# 较大的批次可以提高吞吐量，但需要更多内存
# 建议值：100-500，根据可用内存调整
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "200"))

# Embedding 速率限制退避时间（秒）
# 当遇到速率限制时，等待多长时间后重试
EMBEDDING_RATE_LIMIT_BACKOFF = float(os.getenv("EMBEDDING_RATE_LIMIT_BACKOFF", "2.0"))

# Embedding 上下文长度限制（字符数）
# 超过此长度的文本会被截断
EMBEDDING_CONTEXT_LIMIT = int(os.getenv("EMBEDDING_CONTEXT_LIMIT", "6000"))

# Embedding 列名（数据库中的列名）
EMBEDDING_COLUMN = os.getenv("EMBEDDING_COLUMN", "embedding_context")

# ============================================================================
# Supabase 配置
# ============================================================================

# Supabase 项目 URL
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# Supabase 服务密钥（Service Role Key）
# 注意：这是敏感信息，不要提交到版本控制
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ============================================================================
# 数据库表配置
# ============================================================================

# 清理数据表名
CLEAN_DATA_TABLE_NAME = os.getenv("CLEAN_DATA_TABLE_NAME", "clean_data")

# 行标识符列名列表（用于唯一标识每一行）
# 按优先级顺序排列，第一个存在的列将被用作主键
ROW_IDENTIFIER_COLUMNS: List[str] = [
    "id",
    "message_id",
    "row_id",
]


