"""
测试新的数据库结构（带自增主键）
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

print("🧪 测试新的数据库结构（带自增主键）\n")

# 1. 初始化数据库
print("1️⃣ 初始化数据库...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表是否存在
cursor.execute('''
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='history_news'
''')
table_exists = cursor.fetchone() is not None

if not table_exists:
    cursor.execute('''
        CREATE TABLE history_news (
            index_id INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            content TEXT,
            summary TEXT,
            source TEXT,
            publish_time TEXT,
            crawled_at TEXT
        )
    ''')
    cursor.execute('CREATE INDEX idx_id ON history_news(id)')
    cursor.execute('CREATE INDEX idx_url ON history_news(url)')
    cursor.execute('CREATE INDEX idx_publish_time ON history_news(publish_time)')
    cursor.execute('CREATE INDEX idx_source ON history_news(source)')
    conn.commit()
    print(f"   ✅ 创建新表: history_news")
else:
    print(f"   ✅ 表已存在")

# 2. 插入测试数据（不指定 index_id，让它自动递增）
print("\n2️⃣ 插入测试数据（index_id 自动递增）...")
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
    },
    {
        "id": "ghi789",
        "url": "https://test.com/3",
        "title": "Test Article 3",
        "content": "Third test article content...",
        "summary": "Third test article summary.",
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

# 3. 查询数据，验证 index_id 自增
print("\n3️⃣ 查询数据，验证 index_id 自增...")
cursor.execute('SELECT index_id, id, url, title FROM history_news ORDER BY index_id')
rows = cursor.fetchall()
print(f"   📋 数据列表（包含自增的 index_id）:")
for row in rows:
    print(f"      index_id={row[0]}, id={row[1]}, url={row[2]}, title={row[3]}")

# 4. 再次插入数据，验证 index_id 继续递增
print("\n4️⃣ 再次插入数据，验证 index_id 继续递增...")
cursor.execute('''
    INSERT OR REPLACE INTO history_news 
    (id, url, title, content, summary, source, publish_time, crawled_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    "jkl012",
    "https://test.com/4",
    "Test Article 4",
    "Fourth test article content...",
    "Fourth test article summary.",
    "CoinTelegraph",
    str(datetime.now()),
    str(datetime.now())
))
conn.commit()

cursor.execute('SELECT index_id, id, url FROM history_news ORDER BY index_id')
rows = cursor.fetchall()
print(f"   📋 更新后的数据列表:")
for row in rows:
    print(f"      index_id={row[0]}, id={row[1]}, url={row[2]}")

# 5. 使用pandas读取
print("\n5️⃣ 使用pandas读取数据...")
df = pd.read_sql_query('SELECT * FROM history_news ORDER BY index_id', conn)
print(f"   ✅ 读取成功，共 {len(df)} 条记录")
print(f"\n   DataFrame结构:")
print(df[['index_id', 'id', 'url', 'title']].head())

# 6. 验证表结构
print("\n6️⃣ 验证表结构...")
cursor.execute('PRAGMA table_info(history_news)')
columns = cursor.fetchall()
print(f"   📋 表结构:")
for col in columns:
    print(f"      {col[1]} ({col[2]}) - {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else ''}")

conn.close()

# 7. 清理
print("\n7️⃣ 清理测试数据库...")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"   ✅ 已删除 {db_path}")

print("\n✅ 测试完成！")

