#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看 Pentosh1 筛选结果统计
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pentosh1.db"


def main():
    """主函数"""
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        return 1
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 Pentosh1 筛选结果统计")
    print("=" * 80)
    print()
    
    # 总记录数
    cursor.execute('SELECT COUNT(*) FROM pentosh1_news')
    total_count = cursor.fetchone()[0]
    print(f"📈 总筛选新闻数: {total_count:,} 条")
    print()
    
    # 按来源统计
    cursor.execute('''
        SELECT source, COUNT(*) as count 
        FROM pentosh1_news 
        GROUP BY source 
        ORDER BY count DESC
    ''')
    source_stats = cursor.fetchall()
    
    if source_stats:
        print("📰 按来源统计:")
        for source, count in source_stats:
            print(f"   {source:<30} {count:>8,} 条")
        print()
    
    # 时间范围统计
    cursor.execute('''
        SELECT 
            MIN(publish_time) as min_time,
            MAX(publish_time) as max_time,
            COUNT(DISTINCT DATE(publish_time)) as distinct_days
        FROM pentosh1_news
        WHERE publish_time IS NOT NULL AND publish_time != ''
    ''')
    time_stats = cursor.fetchone()
    
    if time_stats and time_stats[0]:
        min_time, max_time, distinct_days = time_stats
        print("📅 时间范围:")
        print(f"   最早: {min_time}")
        print(f"   最新: {max_time}")
        print(f"   覆盖天数: {distinct_days} 天")
        print()
    
    # 最近筛选时间
    cursor.execute('''
        SELECT MAX(filtered_at) as last_filter
        FROM pentosh1_news
        WHERE filtered_at IS NOT NULL AND filtered_at != ''
    ''')
    last_filter = cursor.fetchone()[0]
    
    if last_filter:
        print(f"🕐 最近筛选时间: {last_filter}")
        print()
    
    # 示例数据（最近5条）
    print("=" * 80)
    print("📋 最近筛选的 5 条新闻:")
    print("=" * 80)
    print()
    
    cursor.execute('''
        SELECT index_id, title, source, publish_time
        FROM pentosh1_news
        ORDER BY index_id DESC
        LIMIT 5
    ''')
    sample_rows = cursor.fetchall()
    
    if sample_rows:
        for i, row in enumerate(sample_rows, 1):
            index_id, title, source, publish_time = row
            print(f"{i}. [{index_id}] {title[:60]}...")
            print(f"   来源: {source} | 时间: {publish_time}")
            print()
    else:
        print("   暂无数据")
    
    conn.close()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

