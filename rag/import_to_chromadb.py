#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 pentosh_all.csv 导入 ChromaDB
使用预计算的向量（embedding_context列），不需要配置 Embedding Function
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
except ImportError:
    print("❌ 请先安装 chromadb: pip install chromadb")
    print("   运行命令: pip install -r rag/requirements.txt")
    sys.exit(1)

# 配置
CSV_FILE = Path(__file__).parent.parent / "pentosh_all.csv"
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "pentosh_tweets"

# 用于构建文档文本的字段
TEXT_FIELDS = [
    "text",
    "info_overall_assessment",
    "gpt_explanation",
    "gpt_reason",
]

# 用于元数据的字段
METADATA_FIELDS = [
    "id",
    "tweet_id",
    "tweet_url",
    "screen_name",
    "display_name",
    "created_at",
    "gpt_sentiment",
    "gpt_assets",
    "info_final_score",
    "is_market_related",
]


def parse_embedding(embedding_str: str) -> Optional[List[float]]:
    """解析 embedding_context 列的向量数据"""
    if not embedding_str or embedding_str.strip() == "":
        return None
    
    try:
        # 尝试解析 JSON 数组
        embedding = json.loads(embedding_str)
        if isinstance(embedding, list):
            return [float(x) for x in embedding]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    return None


def build_document_text(row: Dict[str, Any]) -> str:
    """构建文档文本"""
    parts = []
    for field in TEXT_FIELDS:
        value = row.get(field, "")
        if value and str(value).strip():
            parts.append(str(value).strip())
    
    return " | ".join(parts) if parts else row.get("text", "")


def build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    """构建元数据"""
    metadata = {}
    for field in METADATA_FIELDS:
        value = row.get(field)
        if value is not None:
            # ChromaDB 元数据值必须是字符串、数字或布尔值
            if isinstance(value, (str, int, float, bool)):
                metadata[field] = value
            elif isinstance(value, list):
                # 列表转换为 JSON 字符串
                metadata[field] = json.dumps(value)
            elif isinstance(value, dict):
                # 字典转换为 JSON 字符串
                metadata[field] = json.dumps(value)
            else:
                metadata[field] = str(value)
    
    return metadata


def import_csv_to_chromadb(csv_path: Path, db_path: Path, collection_name: str):
    """将 CSV 文件导入 ChromaDB"""
    
    if not csv_path.exists():
        print(f"❌ CSV 文件不存在: {csv_path}")
        return False
    
    print(f"📂 读取 CSV 文件: {csv_path}")
    
    # 初始化 ChromaDB 客户端（持久化模式）
    print(f"🔧 初始化 ChromaDB，数据库路径: {db_path}")
    client = chromadb.PersistentClient(path=str(db_path))
    
    # 获取或创建集合
    # 注意：不设置 embedding_function，因为我们使用预计算的向量
    print(f"📦 获取/创建集合: {collection_name}")
    
    # 如果集合已存在，询问是否删除重建
    try:
        existing_collection = client.get_collection(name=collection_name)
        existing_count = existing_collection.count()
        print(f"⚠️  集合已存在，包含 {existing_count} 条数据")
        print(f"   将删除旧数据并重新导入...")
        client.delete_collection(name=collection_name)
    except Exception:
        pass  # 集合不存在，继续创建
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Pentoshi tweets with pre-computed embeddings"}
    )
    
    # 读取 CSV 文件
    documents = []
    embeddings = []
    metadatas = []
    ids = []
    
    total_rows = 0
    valid_rows = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_rows += 1
            
            # 解析向量
            embedding = parse_embedding(row.get("embedding_context", ""))
            if embedding is None:
                print(f"⚠️  第 {total_rows} 行缺少有效的向量数据，跳过")
                continue
            
            # 构建文档文本
            doc_text = build_document_text(row)
            if not doc_text:
                print(f"⚠️  第 {total_rows} 行没有文本内容，跳过")
                continue
            
            # 构建元数据
            metadata = build_metadata(row)
            
            # 使用 id 作为文档 ID
            doc_id = str(row.get("id", f"row_{total_rows}"))
            
            documents.append(doc_text)
            embeddings.append(embedding)
            metadatas.append(metadata)
            ids.append(doc_id)
            
            valid_rows += 1
            
            # 每处理 100 条显示进度
            if valid_rows % 100 == 0:
                print(f"✅ 已处理 {valid_rows} 条有效数据...")
    
    print(f"\n📊 统计信息:")
    print(f"   - 总行数: {total_rows}")
    print(f"   - 有效数据: {valid_rows}")
    print(f"   - 跳过数据: {total_rows - valid_rows}")
    
    if valid_rows == 0:
        print("❌ 没有有效数据可导入")
        return False
    
    # 批量添加到 ChromaDB
    print(f"\n🚀 开始导入到 ChromaDB...")
    batch_size = 100
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_documents = documents[i:i+batch_size]
        batch_embeddings = embeddings[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        
        try:
            collection.add(
                ids=batch_ids,
                documents=batch_documents,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas
            )
            print(f"✅ 已导入批次 {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1} ({len(batch_ids)} 条)")
        except Exception as e:
            print(f"❌ 导入批次 {i//batch_size + 1} 失败: {e}")
            return False
    
    # 验证导入结果
    count = collection.count()
    print(f"\n✅ 导入完成！ChromaDB 集合中共有 {count} 条数据")
    
    # 测试查询
    print(f"\n🔍 测试查询...")
    try:
        results = collection.query(
            query_embeddings=[embeddings[0]],
            n_results=3
        )
        print(f"✅ 查询测试成功，返回 {len(results['ids'][0])} 条结果")
    except Exception as e:
        print(f"⚠️  查询测试失败: {e}")
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("📥 将 pentosh_all.csv 导入 ChromaDB")
    print("=" * 60)
    print()
    
    # 检查 CSV 文件
    if not CSV_FILE.exists():
        print(f"❌ CSV 文件不存在: {CSV_FILE}")
        print(f"   请确保文件位于项目根目录")
        return 1
    
    # 创建数据库目录
    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    # 导入数据
    success = import_csv_to_chromadb(
        csv_path=CSV_FILE,
        db_path=CHROMA_DB_PATH,
        collection_name=COLLECTION_NAME
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 导入成功！")
        print(f"📂 数据库路径: {CHROMA_DB_PATH}")
        print(f"📦 集合名称: {COLLECTION_NAME}")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ 导入失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

