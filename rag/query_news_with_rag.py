#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从新闻数据库读取新闻摘要，使用 RAG 混合搜索查询相关推文
参数使用 blur（不进行资产过滤）
"""

import sqlite3
import requests
import json
import os
from pathlib import Path
from datetime import datetime

# 配置
NEWS_DB_PATH = Path(__file__).parent.parent / "news_service" / "history_news.db"
RAG_API_URL = os.getenv("RAG_API_URL", "http://127.0.0.1:8765/query")
OUTPUT_FILE = Path(__file__).parent / "news_rag_query_results.txt"
NUM_NEWS = 10


def get_news_summaries(db_path: Path, limit: int = 10):
    """从数据库读取新闻摘要"""
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return []
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 查询新闻摘要（按 index_id 降序，获取最新的）
        cursor.execute('''
            SELECT index_id, title, summary, source, publish_time
            FROM history_news
            WHERE summary IS NOT NULL AND summary != ''
            ORDER BY index_id DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        news_list = []
        for row in rows:
            news_list.append({
                "index_id": row[0],
                "title": row[1],
                "summary": row[2],
                "source": row[3],
                "publish_time": row[4]
            })
        
        return news_list
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        return []


def query_rag(query_text: str, asset: str = "blur", limit: int = 5):
    """调用 RAG API 进行混合搜索"""
    try:
        payload = {
            "query_text": query_text,
            "asset": asset,
            "limit": limit
        }
        
        response = requests.post(RAG_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        return {
            "trader_name": "",
            "viewpoints": [],
            "error_reason": f"API 请求失败: {str(e)}"
        }
    except Exception as e:
        return {
            "trader_name": "",
            "viewpoints": [],
            "error_reason": f"处理响应失败: {str(e)}"
        }


def main():
    """主函数"""
    print("=" * 80)
    print("📰 新闻 RAG 混合搜索查询")
    print("=" * 80)
    print()
    
    # 1. 读取新闻摘要
    print(f"1️⃣ 从数据库读取 {NUM_NEWS} 条新闻摘要...")
    print(f"   数据库路径: {NEWS_DB_PATH}")
    news_list = get_news_summaries(NEWS_DB_PATH, NUM_NEWS)
    
    if not news_list:
        print("❌ 未找到新闻数据")
        return 1
    
    print(f"✅ 成功读取 {len(news_list)} 条新闻")
    print()
    
    # 2. 检查 RAG API 是否可用
    print(f"2️⃣ 检查 RAG API 服务...")
    print(f"   API 地址: {RAG_API_URL}")
    try:
        health_url = RAG_API_URL.replace("/query", "/health")
        test_response = requests.get(health_url, timeout=5)
        print("✅ RAG API 服务可用")
    except:
        print("⚠️  无法连接到 RAG API，但将继续尝试查询...")
    print()
    
    # 3. 对每条新闻进行 RAG 查询
    print(f"3️⃣ 开始查询 RAG（参数: asset=blur）...")
    print()
    
    results = []
    
    for i, news in enumerate(news_list, 1):
        print(f"   [{i}/{len(news_list)}] 查询新闻: {news['title'][:50]}...")
        
        # 使用 summary 作为查询文本
        query_text = news['summary']
        
        # 调用 RAG API
        rag_result = query_rag(query_text, asset="blur", limit=5)
        
        # 保存结果
        result_item = {
            "news": news,
            "rag_result": rag_result
        }
        results.append(result_item)
        
        # 显示简要结果
        if rag_result.get("error_reason"):
            print(f"      ❌ 错误: {rag_result['error_reason']}")
        else:
            viewpoints_count = len(rag_result.get("viewpoints", []))
            print(f"      ✅ 找到 {viewpoints_count} 条相关推文")
        print()
    
    # 4. 保存结果到文件
    print(f"4️⃣ 保存结果到文件...")
    print(f"   输出文件: {OUTPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("新闻 RAG 混合搜索查询结果\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"查询参数: asset=blur (不进行资产过滤)\n")
        f.write(f"RAG API: {RAG_API_URL}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result_item in enumerate(results, 1):
            news = result_item["news"]
            rag_result = result_item["rag_result"]
            
            f.write(f"\n{'=' * 80}\n")
            f.write(f"新闻 #{i}\n")
            f.write(f"{'=' * 80}\n\n")
            
            # 新闻信息
            f.write("📰 新闻信息:\n")
            f.write(f"   ID: {news['index_id']}\n")
            f.write(f"   标题: {news['title']}\n")
            f.write(f"   来源: {news['source']}\n")
            f.write(f"   发布时间: {news['publish_time']}\n")
            f.write(f"\n   摘要:\n")
            f.write(f"   {news['summary']}\n")
            f.write("\n")
            
            # RAG 查询结果
            f.write("🔍 RAG 查询结果:\n")
            if rag_result.get("error_reason"):
                f.write(f"   ❌ 错误: {rag_result['error_reason']}\n")
            else:
                viewpoints = rag_result.get("viewpoints", [])
                f.write(f"   ✅ 找到 {len(viewpoints)} 条相关推文\n\n")
                
                for j, viewpoint in enumerate(viewpoints, 1):
                    f.write(f"   [{j}] {viewpoint}\n\n")
            
            f.write("\n")
    
    print(f"✅ 结果已保存到: {OUTPUT_FILE}")
    print()
    
    # 5. 统计信息
    print("5️⃣ 查询统计:")
    success_count = sum(1 for r in results if not r["rag_result"].get("error_reason"))
    error_count = len(results) - success_count
    total_viewpoints = sum(len(r["rag_result"].get("viewpoints", [])) for r in results)
    
    print(f"   成功查询: {success_count}/{len(results)}")
    print(f"   失败查询: {error_count}/{len(results)}")
    print(f"   总相关推文数: {total_viewpoints}")
    print()
    
    print("=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

