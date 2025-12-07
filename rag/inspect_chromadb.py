#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 ChromaDB 集合结构和数据
"""

import sys
import io
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import chromadb
except ImportError:
    print("❌ 请先安装 chromadb: pip install chromadb")
    sys.exit(1)

# 配置
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "pentosh_tweets"


def inspect_collection():
    """检查集合结构"""
    print("=" * 60)
    print("🔍 ChromaDB 集合结构检查")
    print("=" * 60)
    print()
    
    # 检查数据库目录是否存在
    if not CHROMA_DB_PATH.exists():
        print(f"❌ ChromaDB 数据库目录不存在: {CHROMA_DB_PATH}")
        print("   请先运行: python rag/import_to_chromadb.py")
        return 1
    
    # 初始化客户端
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    except Exception as e:
        print(f"❌ 初始化 ChromaDB 客户端失败: {e}")
        return 1
    
    # 列出所有集合
    print("📦 所有集合:")
    try:
        collections = client.list_collections()
        if collections:
            for col in collections:
                print(f"   - {col.name} (ID: {col.id})")
                if col.metadata:
                    print(f"     元数据: {col.metadata}")
        else:
            print("   (无)")
    except Exception as e:
        print(f"   ⚠️  列出集合失败: {e}")
    
    print()
    
    # 检查目标集合
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"❌ 获取集合 '{COLLECTION_NAME}' 失败: {e}")
        print("   请先运行: python rag/import_to_chromadb.py")
        return 1
    
    # 集合基本信息
    print(f"📊 集合信息: {COLLECTION_NAME}")
    print(f"   - ID: {collection.id}")
    print(f"   - 数据量: {collection.count()}")
    
    if collection.metadata:
        print(f"   - 元数据: {collection.metadata}")
    
    print()
    
    # 获取样本数据
    print("📝 样本数据（前3条）:")
    try:
        sample = collection.get(limit=3)
        
        if sample['ids']:
            for i, (doc_id, doc, metadata) in enumerate(zip(
                sample['ids'],
                sample['documents'],
                sample['metadatas']
            ), 1):
                print(f"\n{i}. ID: {doc_id}")
                print(f"   文档长度: {len(doc)} 字符")
                print(f"   文档预览: {doc[:100]}...")
                print(f"   元数据字段: {list(metadata.keys())}")
                print(f"   元数据示例:")
                for key, value in list(metadata.items())[:5]:
                    print(f"      - {key}: {value}")
        else:
            print("   (无数据)")
    except Exception as e:
        print(f"   ❌ 获取样本数据失败: {e}")
    
    print()
    
    # 检查向量维度
    print("🔢 向量信息:")
    try:
        sample_with_embeddings = collection.get(
            limit=1,
            include=['embeddings']
        )
        if sample_with_embeddings['embeddings'] and len(sample_with_embeddings['embeddings']) > 0:
            embedding = sample_with_embeddings['embeddings'][0]
            if isinstance(embedding, list) and len(embedding) > 0:
                print(f"   - 向量维度: {len(embedding)}")
                print(f"   - 向量类型: {type(embedding[0])}")
                print(f"   - 向量示例（前5个值）: {embedding[:5]}")
            else:
                print(f"   - 向量格式: {type(embedding)}")
        else:
            print("   ⚠️  无法获取向量信息")
    except Exception as e:
        print(f"   ❌ 获取向量信息失败: {e}")
    
    print()
    
    # 测试查询
    print("🔍 测试查询:")
    try:
        sample_with_embeddings = collection.get(
            limit=1,
            include=['embeddings']
        )
        if sample_with_embeddings['embeddings'] and len(sample_with_embeddings['embeddings']) > 0:
            query_embedding = sample_with_embeddings['embeddings'][0]
            if isinstance(query_embedding, list):
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3
                )
                print(f"   ✅ 查询成功，返回 {len(results['ids'][0])} 条结果")
                print(f"   - 查询向量维度: {len(query_embedding)}")
                print(f"   - 结果ID: {results['ids'][0]}")
            else:
                print(f"   ⚠️  向量格式不正确: {type(query_embedding)}")
        else:
            print("   ⚠️  无法测试查询（没有向量数据）")
    except Exception as e:
        print(f"   ❌ 测试查询失败: {e}")
    
    print()
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(inspect_collection())

