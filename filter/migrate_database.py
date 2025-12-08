#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移数据库：删除 original_index_id，添加 source_index_id 作为外键字段
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pentosh1.db"


def migrate_database():
    """迁移数据库结构"""
    if not DB_PATH.exists():
        print(f"❌ 数据库不存在: {DB_PATH}")
        return 1
    
    print(f"📂 开始迁移数据库: {DB_PATH}")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='pentosh1_news'
        ''')
        if not cursor.fetchone():
            print("❌ 表 pentosh1_news 不存在")
            conn.close()
            return 1
        
        # 检查是否已经有 source_index_id 字段
        cursor.execute('PRAGMA table_info(pentosh1_news)')
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'source_index_id' in columns and 'original_index_id' not in columns:
            print("✅ 数据库已经是最新结构，无需迁移")
            conn.close()
            return 0
        
        print("🔄 开始迁移...")
        
        # 1. 创建新表
        print("   1. 创建新表结构...")
        cursor.execute('''
            CREATE TABLE pentosh1_news_new (
                index_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_index_id INTEGER NOT NULL UNIQUE,
                id TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                summary TEXT,
                source TEXT,
                publish_time TEXT,
                crawled_at TEXT,
                filtered_at TEXT
            )
        ''')
        
        # 2. 迁移数据（如果有 original_index_id，则复制其值到 source_index_id）
        print("   2. 迁移数据...")
        if 'original_index_id' in columns:
            cursor.execute('''
                INSERT INTO pentosh1_news_new 
                (source_index_id, id, url, title, content, summary, source, publish_time, crawled_at, filtered_at)
                SELECT original_index_id, id, url, title, content, summary, source, publish_time, crawled_at, filtered_at
                FROM pentosh1_news
            ''')
        else:
            # 如果没有 original_index_id，尝试从其他字段推断
            print("   ⚠️  未找到 original_index_id 字段，跳过数据迁移")
        
        # 3. 删除旧表
        print("   3. 删除旧表...")
        cursor.execute('DROP TABLE pentosh1_news')
        
        # 4. 重命名新表
        print("   4. 重命名新表...")
        cursor.execute('ALTER TABLE pentosh1_news_new RENAME TO pentosh1_news')
        
        # 5. 创建索引
        print("   5. 创建索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_index_id ON pentosh1_news(source_index_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_id ON pentosh1_news(id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON pentosh1_news(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON pentosh1_news(publish_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON pentosh1_news(source)')
        
        # 提交更改
        conn.commit()
        print("✅ 迁移完成！")
        
        # 显示统计
        cursor.execute('SELECT COUNT(*) FROM pentosh1_news')
        count = cursor.fetchone()[0]
        print(f"📊 迁移后记录数: {count}")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        conn.close()
        return 1
    
    conn.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(migrate_database())



