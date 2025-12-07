"""
测试数据库功能
"""
import sys
import sqlite3
import pandas as pd
from datetime import datetime
import os

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

db_path = "test_history_news.db"

print("🧪 测试数据库功能\n")

# 1. 初始化数据库
print("1️⃣ 初始化数据库...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS history_news (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE NOT NULL,
        title TEXT,
        content TEXT,
        summary TEXT,
        source TEXT,
        publish_time TEXT,
        crawled_at TEXT
    )
''')

cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON history_news(url)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON history_news(publish_time)')

conn.commit()
print(f"   ✅ 数据库表已创建")

# 2. 插入测试数据
print("\n2️⃣ 插入测试数据...")
test_articles = [
    {
        "id": "abc123",
        "url": "https://test.com/1",
        "title": "Test Article 1",
        "content": "This is a test article content...",
        "summary": "This is a test article summary.",
        "source": "CoinTelegraph",
        "publish_time": str(datetime.now()),
        "crawled_at": str(datetime.now())
    },
    {
        "id": "def456",
        "url": "https://test.com/2",
        "title": "Test Article 2",
        "content": "Another test article content...",
        "summary": "Another test article summary.",
        "source": "CoinTelegraph",
        "publish_time": str(datetime.now()),
        "crawled_at": str(datetime.now())
    }
]

for article in test_articles:
    cursor.execute('''
        INSERT OR REPLACE INTO history_news 
        (id, url, title, content, summary, source, publish_time, crawled_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        article['id'],
        article['url'],
        article['title'],
        article['content'],
        article['summary'],
        article['source'],
        article['publish_time'],
        article['crawled_at']
    ))

conn.commit()
print(f"   ✅ 已插入 {len(test_articles)} 条测试数据")

# 3. 查询数据
print("\n3️⃣ 查询数据...")
cursor.execute('SELECT COUNT(*) FROM history_news')
count = cursor.fetchone()[0]
print(f"   ✅ 数据库中共有 {count} 条记录")

cursor.execute('SELECT url FROM history_news')
urls = cursor.fetchall()
print(f"   📋 URL列表:")
for url in urls:
    print(f"      - {url[0]}")

# 4. 使用pandas读取
print("\n4️⃣ 使用pandas读取数据...")
df = pd.read_sql_query('SELECT * FROM history_news', conn)
print(f"   ✅ 读取成功，共 {len(df)} 条记录")
print(f"\n   DataFrame结构:")
print(df.head())

# 5. 清理
print("\n5️⃣ 清理测试数据库...")
conn.close()
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"   ✅ 已删除 {db_path}")

print("\n✅ 测试完成！")

