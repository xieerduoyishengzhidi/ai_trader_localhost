#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ChromaDB 查询示例
演示如何使用预计算的向量进行相似度搜索
"""

import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    print("❌ 请先安装 chromadb: pip install chromadb")
    sys.exit(1)

# 配置
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "pentosh_tweets"


def query_by_text(query_text: str, n_results: int = 5):
    """通过文本查询（需要先计算查询文本的向量）"""
    print(f"⚠️  注意：此方法需要先计算查询文本的向量")
    print(f"   由于我们使用预计算的向量，建议使用 query_by_embedding 方法")
    return None


def query_by_embedding(query_embedding: list, n_results: int = 5):
    """通过预计算的向量查询"""
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = client.get_collection(name=COLLECTION_NAME)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    return results


def get_collection_info():
    """获取集合信息"""
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = client.get_collection(name=COLLECTION_NAME)
    
    count = collection.count()
    print(f"📊 集合信息:")
    print(f"   - 名称: {COLLECTION_NAME}")
    print(f"   - 数据量: {count}")
    
    return collection


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 ChromaDB 查询示例")
    print("=" * 60)
    print()
    
    # 获取集合信息
    collection = get_collection_info()
    
    # 示例：获取第一条数据的向量用于测试查询
    print("\n📝 示例查询（使用第一条数据的向量）...")
    try:
        # 获取所有数据（限制1条）
        sample = collection.get(limit=1)
        if sample['ids']:
            # 获取第一条数据的向量
            sample_embedding = collection.get(
                ids=[sample['ids'][0]],
                include=['embeddings']
            )['embeddings'][0]
            
            # 使用该向量进行查询
            results = query_by_embedding(sample_embedding, n_results=3)
            
            print(f"\n✅ 查询成功，返回 {len(results['ids'][0])} 条结果:")
            for i, (doc_id, doc, metadata) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0]
            ), 1):
                print(f"\n{i}. ID: {doc_id}")
                print(f"   文本: {doc[:100]}...")
                print(f"   元数据: {metadata.get('screen_name', 'N/A')} | {metadata.get('created_at', 'N/A')}")
        else:
            print("⚠️  集合中没有数据")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("💡 使用提示:")
    print("   1. 使用 query_by_embedding(query_embedding, n_results) 进行向量查询")
    print("   2. query_embedding 应该是与导入时相同维度的向量列表")
    print("   3. 如果需要通过文本查询，需要先使用相同的 embedding 模型计算文本向量")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

