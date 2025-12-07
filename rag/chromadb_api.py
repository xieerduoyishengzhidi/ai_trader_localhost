#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ChromaDB RAG HTTP API 服务
为 Go 代码提供 ChromaDB 查询接口
支持 BM25 + 向量混合搜索（Hybrid Search）

BM25 搜索字段：
- documents 字段（包含 text, info_overall_assessment, gpt_explanation, gpt_reason）

元数据过滤：
- 数据库层面：screen_name (trader_name), gpt_sentiment (sentiment), is_market_related
- 结果层面：gpt_assets (asset) - JSON 数组，需要解析后过滤
"""

import json
import os
import sys
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("❌ 请先安装 flask: pip install flask")
    sys.exit(1)

try:
    import chromadb
except ImportError:
    print("❌ 请先安装 chromadb: pip install chromadb")
    sys.exit(1)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("❌ 请先安装 rank-bm25: pip install rank-bm25")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("❌ 请先安装 sentence-transformers: pip install sentence-transformers")
    sys.exit(1)

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "pentosh_tweets"
DEFAULT_PORT = 8765

# Embedding 模型配置（与导入时使用的模型一致）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "moka-ai/m3e-base")

app = Flask(__name__)

# 全局变量
_client = None
_collection = None
_embedding_model = None
_bm25_index = None  # BM25 索引缓存
_documents_cache = None  # 文档缓存（用于 BM25）


def get_collection():
    """获取 ChromaDB 集合（懒加载）"""
    global _client, _collection
    
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        try:
            _collection = _client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            raise RuntimeError(f"无法获取集合 '{COLLECTION_NAME}': {e}")
    
    return _collection


def get_embedding_model():
    """获取 Embedding 模型（懒加载）"""
    global _embedding_model
    
    if _embedding_model is None:
        print(f"📦 加载 Embedding 模型: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✅ 模型加载完成")
    
    return _embedding_model


def build_bm25_index(collection, trader_name: Optional[str] = None, where_clause: Optional[Dict] = None):
    """构建 BM25 索引（带缓存）
    
    Args:
        collection: ChromaDB 集合
        trader_name: 交易员名称（用于缓存键，已废弃，保留兼容性）
        where_clause: where 过滤条件（数据库层面过滤，高效）
    
    Note:
        BM25 索引在 documents 字段上构建，该字段包含：
        - text (原始推文文本)
        - info_overall_assessment (综合评估)
        - gpt_explanation (GPT 解释)
        - gpt_reason (GPT 原因)
    """
    global _bm25_index, _documents_cache
    
    # 构建缓存键（基于 where_clause）
    cache_key = str(where_clause) if where_clause else "all"
    
    # 如果已有缓存且条件匹配，直接返回
    if _bm25_index is not None and _documents_cache is not None:
        if where_clause is None or cache_key == "all":
            return _bm25_index, _documents_cache
    
    # 使用 ChromaDB 的 where 过滤（数据库层面，高效）
    # 如果没有提供 where_clause，尝试使用 trader_name（向后兼容）
    if where_clause is None and trader_name:
        where_clause = {"screen_name": trader_name}
    
    try:
        # 使用 where 过滤获取数据（数据库层面过滤，高效）
        if where_clause:
            results = collection.get(where=where_clause)
        else:
            results = collection.get()
    except Exception:
        # 如果 where 查询失败（比如字段不存在），fallback 到获取所有数据
        results = collection.get()
    
    if not results['ids']:
        # 如果没有精确匹配，尝试模糊匹配（但只在内存中过滤少量数据）
        if trader_name:
            # 先获取少量数据尝试匹配
            all_results = collection.get(limit=100)
            filtered_ids = []
            filtered_docs = []
            filtered_metadatas = []
            
            for doc_id, doc, metadata in zip(
                all_results['ids'],
                all_results['documents'],
                all_results['metadatas']
            ):
                screen_name = metadata.get('screen_name', '')
                display_name = metadata.get('display_name', '')
                if (trader_name.lower() in screen_name.lower() or 
                    trader_name.lower() in display_name.lower()):
                    filtered_ids.append(doc_id)
                    filtered_docs.append(doc)
                    filtered_metadatas.append(metadata)
            
            if filtered_ids:
                results = {
                    'ids': filtered_ids,
                    'documents': filtered_docs,
                    'metadatas': filtered_metadatas
                }
            else:
                # 如果还是找不到，返回空索引
                return None, None
    
    # 准备 BM25 数据
    documents = results['documents']
    if not documents:
        return None, None
    
    # 分词（简单的中英文分词）
    tokenized_docs = []
    for doc in documents:
        # 简单分词：按空格和标点分割，保留字母数字和中文
        import re
        tokens = re.findall(r'\b\w+\b|[\u4e00-\u9fff]+', doc.lower())
        tokenized_docs.append(tokens)
    
    # 构建 BM25 索引
    bm25 = BM25Okapi(tokenized_docs)
    
    # 缓存
    _bm25_index = bm25
    _documents_cache = {
        'ids': results['ids'],
        'documents': results['documents'],
        'metadatas': results.get('metadatas', [])
    }
    
    return bm25, _documents_cache


def rrf_merge(vector_results: List[Tuple[str, float]], 
              bm25_results: List[Tuple[str, float]], 
              k: int = 60) -> List[str]:
    """Reciprocal Rank Fusion (RRF) 合并搜索结果
    
    Args:
        vector_results: [(doc_id, score), ...] 向量搜索结果
        bm25_results: [(doc_id, score), ...] BM25 搜索结果
        k: RRF 常数（默认 60）
    
    Returns:
        合并后的文档 ID 列表（按 RRF 分数排序）
    """
    # 构建文档 ID 到排名的映射
    vector_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(vector_results)}
    bm25_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(bm25_results)}
    
    # 计算 RRF 分数
    rrf_scores = defaultdict(float)
    all_doc_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
    
    for doc_id in all_doc_ids:
        if doc_id in vector_ranks:
            rrf_scores[doc_id] += 1.0 / (k + vector_ranks[doc_id])
        if doc_id in bm25_ranks:
            rrf_scores[doc_id] += 1.0 / (k + bm25_ranks[doc_id])
    
    # 按 RRF 分数排序
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [doc_id for doc_id, _ in sorted_docs]


def build_where_clause(trader_name: Optional[str] = None, 
                       asset: Optional[str] = None,
                       sentiment: Optional[str] = None,
                       is_market_related: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    """构建 ChromaDB where 过滤条件
    
    Args:
        trader_name: 交易员名称（匹配 screen_name）
        asset: 标的资产（匹配 gpt_assets JSON 数组）
        sentiment: 情感（positive/negative，匹配 gpt_sentiment）
        is_market_related: 是否市场相关（匹配 is_market_related）
    
    Returns:
        where 条件字典，或 None
    """
    where_parts = []
    
    if trader_name:
        where_parts.append({"screen_name": trader_name})
    
    if sentiment:
        where_parts.append({"gpt_sentiment": sentiment})
    
    if is_market_related is not None:
        where_parts.append({"is_market_related": is_market_related})
    
    # asset 需要特殊处理，因为 gpt_assets 是 JSON 字符串
    # ChromaDB 不支持 JSON 数组查询，需要在结果中过滤
    # 这里先不加入 where，后续在结果中过滤
    
    if len(where_parts) == 0:
        return None
    elif len(where_parts) == 1:
        return where_parts[0]
    else:
        # ChromaDB 支持 $and 操作符
        return {"$and": where_parts}


def filter_by_asset(results: List[Dict[str, Any]], asset: Optional[str] = None, 
                    assets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """在结果中过滤包含指定资产的文档
    
    Args:
        results: 搜索结果列表
        asset: 单个资产名称（如 "SOL", "BTC"），与 assets 二选一
               - 特殊值 "blur" 表示不进行资产过滤
        assets: 多个资产名称列表（如 ["SOL", "BTC"]），与 asset 二选一
                - 如果包含 "blur"，则不进行资产过滤
    
    Returns:
        过滤后的结果列表
    
    Note:
        - 如果同时提供 asset 和 assets，优先使用 assets
        - 如果 assets 包含多个资产，返回包含任意一个资产的文档（OR 逻辑）
        - 如果 asset="blur" 或 assets 包含 "blur"，跳过资产过滤
    """
    # 检查 blur 选项
    if asset and asset.lower() == "blur":
        return results
    
    if assets:
        # 检查 assets 列表中是否包含 "blur"
        if any(str(a).lower() == "blur" for a in assets):
            return results
        target_assets = [a.upper() for a in assets if a and str(a).lower() != "blur"]
    elif asset:
        target_assets = [asset.upper()]
    else:
        return results
    
    if not target_assets:
        return results
    
    filtered = []
    
    for result in results:
        metadata = result.get('metadata', {})
        gpt_assets_str = metadata.get('gpt_assets', '[]')
        
        try:
            # 解析 JSON 字符串
            gpt_assets = json.loads(gpt_assets_str) if isinstance(gpt_assets_str, str) else gpt_assets_str
            if isinstance(gpt_assets, list):
                # 检查资产列表中是否包含任意一个目标资产
                assets_upper = [a.upper() if isinstance(a, str) else str(a).upper() for a in gpt_assets]
                # OR 逻辑：包含任意一个目标资产即可
                if any(target_asset in assets_upper for target_asset in target_assets):
                    filtered.append(result)
        except (json.JSONDecodeError, TypeError):
            # 如果解析失败，尝试字符串匹配
            gpt_assets_upper = str(gpt_assets_str).upper()
            if any(target_asset in gpt_assets_upper for target_asset in target_assets):
                filtered.append(result)
    
    return filtered


def hybrid_search(collection, query_text: str, trader_name: Optional[str] = None,
                  asset: Optional[str] = None,
                  assets: Optional[List[str]] = None,
                  sentiment: Optional[str] = None,
                  is_market_related: Optional[bool] = None,
                  limit: int = 20) -> List[Dict[str, Any]]:
    """BM25 + 向量混合搜索
    
    Args:
        collection: ChromaDB 集合
        query_text: 查询文本（BM25 和向量搜索都使用此文本）
        trader_name: 交易员名称（可选，用于元数据过滤 screen_name）
        asset: 单个标的资产（可选，用于过滤 gpt_assets，如 "SOL"）
               - 特殊值 "blur" 表示不进行资产过滤
        assets: 多个标的资产列表（可选，用于过滤 gpt_assets，如 ["SOL", "BTC"]）
               - 与 asset 二选一，如果同时提供，优先使用 assets
               - 返回包含任意一个资产的文档（OR 逻辑）
               - 如果包含 "blur"，则不进行资产过滤
        sentiment: 情感（可选，positive/negative，用于过滤 gpt_sentiment）
        is_market_related: 是否市场相关（可选，用于过滤 is_market_related）
        limit: 返回结果数量
    
    Returns:
        搜索结果列表，每个元素包含 id, document, metadata, score
    
    Note:
        - BM25 搜索在 documents 字段上进行（包含 text, info_overall_assessment, gpt_explanation, gpt_reason）
        - 元数据过滤在数据库层面进行（where 条件）
        - asset/assets 过滤在结果层面进行（因为 gpt_assets 是 JSON 数组）
    """
    # 构建 where 过滤条件（数据库层面，高效）
    where_clause = build_where_clause(trader_name, asset=None, sentiment=sentiment, is_market_related=is_market_related)
    # 注意：asset 不在 where 中，因为 gpt_assets 是 JSON 数组，ChromaDB 不支持直接查询
    
    # 1. BM25 搜索（关键字匹配）
    # BM25 在 documents 字段上搜索，该字段包含：
    # - text (原始推文文本)
    # - info_overall_assessment (综合评估)
    # - gpt_explanation (GPT 解释)
    # - gpt_reason (GPT 原因)
    bm25_index, bm25_cache = build_bm25_index(collection, trader_name, where_clause)
    
    if bm25_index is None or bm25_cache is None:
        return []
    
    # 分词查询文本
    import re
    query_tokens = re.findall(r'\b\w+\b|[\u4e00-\u9fff]+', query_text.lower())
    
    # BM25 搜索
    bm25_scores = bm25_index.get_scores(query_tokens)
    bm25_results = []
    for i, score in enumerate(bm25_scores):
        if score > 0:  # 只保留有匹配的
            bm25_results.append((bm25_cache['ids'][i], score))
    
    # 按分数排序
    bm25_results.sort(key=lambda x: x[1], reverse=True)
    bm25_results = bm25_results[:limit * 2]  # 多取一些用于合并
    
    # 2. 向量搜索（语义匹配）
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.encode(query_text, convert_to_numpy=True).tolist()
    
    # 使用 where 过滤（数据库层面）
    try:
        vector_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # 多取一些用于合并
            where=where_clause
        )
    except Exception:
        # 如果 where 查询失败，不使用过滤
        vector_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2
        )
    
    # 构建向量搜索结果（ChromaDB 返回的是距离，需要转换为分数）
    vector_scores = []
    if vector_results['ids'] and len(vector_results['ids'][0]) > 0:
        # ChromaDB 返回 distances，越小越相似，转换为分数（1 / (1 + distance)）
        for i, doc_id in enumerate(vector_results['ids'][0]):
            distance = vector_results['distances'][0][i] if 'distances' in vector_results else 0
            score = 1.0 / (1.0 + distance)  # 转换为相似度分数
            vector_scores.append((doc_id, score))
    
    # 3. RRF 合并
    merged_doc_ids = rrf_merge(vector_scores, bm25_results, k=60)
    
    # 4. 构建结果
    # 创建文档 ID 到文档的映射（合并 BM25 和向量搜索结果）
    doc_map = {}
    
    # 从 BM25 缓存添加
    for i, doc_id in enumerate(bm25_cache['ids']):
        doc_map[doc_id] = {
            'id': doc_id,
            'document': bm25_cache['documents'][i],
            'metadata': bm25_cache['metadatas'][i] if bm25_cache['metadatas'] and i < len(bm25_cache['metadatas']) else {}
        }
    
    # 从向量搜索结果添加（可能包含 BM25 缓存中没有的）
    if vector_results['ids'] and len(vector_results['ids'][0]) > 0:
        for i, doc_id in enumerate(vector_results['ids'][0]):
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    'id': doc_id,
                    'document': vector_results['documents'][0][i] if vector_results['documents'] and i < len(vector_results['documents'][0]) else "",
                    'metadata': vector_results['metadatas'][0][i] if vector_results.get('metadatas') and i < len(vector_results['metadatas'][0]) else {}
                }
    
    # 按合并后的顺序返回
    results = []
    for doc_id in merged_doc_ids[:limit]:
        if doc_id in doc_map:
            results.append(doc_map[doc_id])
    
    # 5. 资产过滤（在结果层面，因为 gpt_assets 是 JSON 数组）
    # 如果 asset="blur" 或 assets 包含 "blur"，跳过资产过滤
    should_filter_asset = True
    if asset and asset.lower() == "blur":
        should_filter_asset = False
    elif assets and any(str(a).lower() == "blur" for a in assets):
        should_filter_asset = False
    
    if should_filter_asset and (asset or assets):
        results = filter_by_asset(results, asset=asset, assets=assets)
    
    return results[:limit]  # 确保不超过 limit


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    try:
        collection = get_collection()
        count = collection.count()
        return jsonify({
            "status": "ok",
            "collection": COLLECTION_NAME,
            "count": count,
            "embedding_model": EMBEDDING_MODEL
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/query', methods=['POST'])
def query():
    """混合搜索查询（BM25 + 向量）
    
    请求体:
    {
        "trader_name": "Pentosh1",  # 交易员名称（可选，元数据过滤 screen_name）
        "asset": "SOL",  # 单个标的资产（可选，元数据过滤 gpt_assets，如 "SOL"）
                       # 特殊值 "blur" 表示不进行资产过滤
        "assets": ["SOL", "BTC"],  # 多个标的资产（可选，与 asset 二选一，返回包含任意一个资产的文档）
                                  # 如果包含 "blur"，则不进行资产过滤
        "sentiment": "positive",  # 情感（可选，positive/negative，元数据过滤 gpt_sentiment）
        "is_market_related": true,  # 是否市场相关（可选，元数据过滤 is_market_related）
        "query_text": "SOL 价格预测",  # 查询文本（必需，用于 BM25 和向量搜索）
        "limit": 5  # 返回结果数量，默认5
    }
    
    返回:
    {
        "trader_name": "Pentosh1",
        "viewpoints": ["观点1", "观点2", ...],
        "error_reason": ""  # 如果有错误
    }
    
    Note:
        - BM25 搜索在 documents 字段上进行（包含 text, info_overall_assessment, gpt_explanation, gpt_reason）
        - 元数据过滤在数据库层面进行（where 条件），高效
        - asset 过滤在结果层面进行（因为 gpt_assets 是 JSON 数组）
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "trader_name": "",
                "viewpoints": [],
                "error_reason": "请求体为空"
            }), 400
        
        trader_name = data.get("trader_name", "").strip() or None
        asset = data.get("asset", "").strip() or None
        assets = data.get("assets")  # 可以是列表或 None
        if assets and isinstance(assets, list):
            assets = [a.strip() for a in assets if a and str(a).strip()]
            assets = assets if assets else None
        else:
            assets = None
        sentiment = data.get("sentiment", "").strip() or None
        is_market_related = data.get("is_market_related")
        query_text = data.get("query_text", "").strip()
        limit = int(data.get("limit", 5))
        
        if not query_text:
            return jsonify({
                "trader_name": trader_name or "",
                "viewpoints": [],
                "error_reason": "查询文本为空"
            }), 400
        
        collection = get_collection()
        
        # 执行混合搜索
        results = hybrid_search(
            collection, 
            query_text, 
            trader_name=trader_name,
            asset=asset,
            assets=assets,
            sentiment=sentiment,
            is_market_related=is_market_related,
            limit=limit
        )
        
        # 提取观点
        viewpoints = []
        for result in results:
            doc = result['document']
            if doc:
                # 限制每条观点最多500字符
                viewpoint = doc[:500] if len(doc) <= 500 else doc[:497] + "..."
                viewpoints.append(viewpoint)
        
        return jsonify({
            "trader_name": trader_name or "",
            "viewpoints": viewpoints,
            "error_reason": ""
        })
        
    except Exception as e:
        return jsonify({
            "trader_name": data.get("trader_name", "") if 'data' in locals() else "",
            "viewpoints": [],
            "error_reason": f"服务器错误: {str(e)}"
        }), 500


@app.route('/query_by_name', methods=['POST'])
def query_by_name():
    """根据交易员名称查询（使用混合搜索，查询文本为交易员名称）
    
    请求体:
    {
        "trader_name": "Pentosh1",  # 交易员名称（必需）
        "asset": "SOL",  # 单个标的资产（可选，如 "SOL"）
                       # 特殊值 "blur" 表示不进行资产过滤
        "assets": ["SOL", "BTC"],  # 多个标的资产（可选，与 asset 二选一）
                                  # 如果包含 "blur"，则不进行资产过滤
        "sentiment": "positive",  # 情感（可选）
        "is_market_related": true,  # 是否市场相关（可选）
        "limit": 5  # 返回结果数量，默认5
    }
    
    Note:
        - 使用交易员名称作为查询文本，进行混合搜索
        - 这样可以同时利用 BM25（精确匹配）和向量（语义匹配）
        - BM25 在 documents 字段上搜索（包含 text, info_overall_assessment, gpt_explanation, gpt_reason）
    """
    try:
        data = request.get_json()
        trader_name = data.get("trader_name", "").strip()
        asset = data.get("asset", "").strip() or None
        assets = data.get("assets")  # 可以是列表或 None
        if assets and isinstance(assets, list):
            assets = [a.strip() for a in assets if a and str(a).strip()]
            assets = assets if assets else None
        else:
            assets = None
        sentiment = data.get("sentiment", "").strip() or None
        is_market_related = data.get("is_market_related")
        limit = int(data.get("limit", 5))
        
        if not trader_name:
            return jsonify({
                "trader_name": "",
                "viewpoints": [],
                "error_reason": "交易员名称为空"
            })
        
        collection = get_collection()
        
        # 使用交易员名称作为查询文本，进行混合搜索
        # 这样可以同时利用 BM25（精确匹配）和向量（语义匹配）
        results = hybrid_search(
            collection, 
            trader_name,  # 查询文本
            trader_name=trader_name,  # 元数据过滤
            asset=asset,
            assets=assets,
            sentiment=sentiment,
            is_market_related=is_market_related,
            limit=limit
        )
        
        # 提取观点
        viewpoints = []
        for result in results:
            doc = result['document']
            if doc:
                viewpoint = doc[:500] if len(doc) <= 500 else doc[:497] + "..."
                viewpoints.append(viewpoint)
        
        return jsonify({
            "trader_name": trader_name,
            "viewpoints": viewpoints,
            "error_reason": ""
        })
        
    except Exception as e:
        return jsonify({
            "trader_name": data.get("trader_name", "") if 'data' in locals() else "",
            "viewpoints": [],
            "error_reason": f"查询失败: {str(e)}"
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('RAG_API_PORT', DEFAULT_PORT))
    host = os.getenv('RAG_API_HOST', '127.0.0.1')
    
    print(f"🚀 启动 ChromaDB RAG API 服务（混合搜索模式）...")
    print(f"   - 地址: http://{host}:{port}")
    print(f"   - 数据库: {CHROMA_DB_PATH}")
    print(f"   - 集合: {COLLECTION_NAME}")
    print(f"   - Embedding 模型: {EMBEDDING_MODEL}")
    print(f"   - 搜索模式: BM25 + 向量混合搜索 (RRF)")
    
    app.run(host=host, port=port, debug=False)
