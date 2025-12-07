#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 pentosh1.db 导出为 CSV 文件
"""

import sqlite3
import csv
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "pentosh1.db"
OUTPUT_CSV = Path(__file__).parent / f"pentosh1_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def export_to_csv():
    """导出数据库到 CSV"""
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        return 1
    
    print(f"📂 读取数据库: {DB_PATH}")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 查询所有数据
    cursor.execute('''
        SELECT 
            index_id,
            source_index_id,
            id,
            url,
            title,
            content,
            summary,
            source,
            publish_time,
            crawled_at,
            filtered_at
        FROM pentosh1_news
        ORDER BY index_id ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("⚠️  数据库中没有数据")
        return 1
    
    print(f"📊 找到 {len(rows)} 条记录")
    print(f"💾 导出到: {OUTPUT_CSV}")
    
    # 写入 CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # 写入表头
        writer.writerow([
            'index_id',
            'source_index_id',
            'id',
            'url',
            'title',
            'content',
            'summary',
            'source',
            'publish_time',
            'crawled_at',
            'filtered_at'
        ])
        
        # 写入数据
        for row in rows:
            writer.writerow(row)
    
    print(f"✅ 导出完成！")
    print(f"   文件: {OUTPUT_CSV}")
    print(f"   记录数: {len(rows)}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(export_to_csv())

