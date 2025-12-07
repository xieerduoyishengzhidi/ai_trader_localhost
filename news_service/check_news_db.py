"""
检查新闻数据库表结构和数据量
"""
import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 数据库文件路径
db_path = "history_news.db"

print("=" * 60)
print("📊 新闻数据库检查工具")
print("=" * 60)

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"\n❌ 数据库文件不存在: {db_path}")
    print("   请先运行 history_miner.py 创建数据库")
    exit(1)

print(f"\n✅ 数据库文件存在: {db_path}")
print(f"   文件大小: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")

# 连接数据库
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 检查表是否存在
    print("\n" + "=" * 60)
    print("1️⃣ 检查表是否存在")
    print("=" * 60)
    
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='history_news'
    ''')
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("❌ 表 'history_news' 不存在")
        conn.close()
        exit(1)
    
    print("✅ 表 'history_news' 存在")
    
    # 2. 查看表结构
    print("\n" + "=" * 60)
    print("2️⃣ 表结构")
    print("=" * 60)
    
    cursor.execute('PRAGMA table_info(history_news)')
    columns = cursor.fetchall()
    
    print(f"\n   共 {len(columns)} 个字段:\n")
    print(f"   {'字段名':<20} {'类型':<20} {'非空':<10} {'默认值':<15} {'主键':<10}")
    print("   " + "-" * 75)
    
    for col in columns:
        cid, name, col_type, notnull, default_val, pk = col
        notnull_str = "是" if notnull else "否"
        pk_str = "是" if pk else "否"
        default_str = str(default_val) if default_val else ""
        print(f"   {name:<20} {col_type:<20} {notnull_str:<10} {default_str:<15} {pk_str:<10}")
    
    # 3. 查看索引
    print("\n" + "=" * 60)
    print("3️⃣ 索引信息")
    print("=" * 60)
    
    cursor.execute('''
        SELECT name, sql FROM sqlite_master 
        WHERE type='index' AND tbl_name='history_news'
    ''')
    indexes = cursor.fetchall()
    
    if indexes:
        print(f"\n   共 {len(indexes)} 个索引:\n")
        for idx_name, idx_sql in indexes:
            print(f"   - {idx_name}")
            if idx_sql:
                print(f"     {idx_sql}")
    else:
        print("\n   ⚠️ 未找到索引")
    
    # 4. 统计数据量
    print("\n" + "=" * 60)
    print("4️⃣ 数据统计")
    print("=" * 60)
    
    # 总记录数
    cursor.execute('SELECT COUNT(*) FROM history_news')
    total_count = cursor.fetchone()[0]
    print(f"\n   📊 总记录数: {total_count:,} 条")
    
    # 按来源统计
    cursor.execute('''
        SELECT source, COUNT(*) as count 
        FROM history_news 
        GROUP BY source 
        ORDER BY count DESC
    ''')
    source_stats = cursor.fetchall()
    
    if source_stats:
        print(f"\n   📊 按来源统计:")
        for source, count in source_stats:
            print(f"      {source:<20} {count:>8,} 条")
    
    # 时间范围统计
    cursor.execute('''
        SELECT 
            MIN(publish_time) as min_time,
            MAX(publish_time) as max_time,
            COUNT(DISTINCT DATE(publish_time)) as distinct_days
        FROM history_news
        WHERE publish_time IS NOT NULL AND publish_time != ''
    ''')
    time_stats = cursor.fetchone()
    
    if time_stats and time_stats[0]:
        min_time, max_time, distinct_days = time_stats
        print(f"\n   📅 时间范围:")
        print(f"      最早: {min_time}")
        print(f"      最新: {max_time}")
        print(f"      覆盖天数: {distinct_days} 天")
    
    # 最近爬取时间
    cursor.execute('''
        SELECT MAX(crawled_at) as last_crawl
        FROM history_news
        WHERE crawled_at IS NOT NULL AND crawled_at != ''
    ''')
    last_crawl = cursor.fetchone()[0]
    
    if last_crawl:
        print(f"\n   🕐 最近爬取时间: {last_crawl}")
    
    # 5. 查看示例数据
    print("\n" + "=" * 60)
    print("5️⃣ 示例数据（最近5条）")
    print("=" * 60)
    
    cursor.execute('''
        SELECT index_id, id, url, title, source, publish_time, crawled_at
        FROM history_news
        ORDER BY index_id DESC
        LIMIT 5
    ''')
    sample_rows = cursor.fetchall()
    
    if sample_rows:
        print(f"\n   {'ID':<8} {'标题':<50} {'来源':<15} {'发布时间':<20}")
        print("   " + "-" * 95)
        for row in sample_rows:
            index_id, article_id, url, title, source, pub_time, crawl_time = row
            title_short = (title[:47] + "...") if title and len(title) > 50 else (title or "")
            pub_time_short = (pub_time[:17] + "...") if pub_time and len(pub_time) > 20 else (pub_time or "")
            print(f"   {index_id:<8} {title_short:<50} {source:<15} {pub_time_short:<20}")
    else:
        print("\n   ⚠️ 暂无数据")
    
    # 6. 数据完整性检查
    print("\n" + "=" * 60)
    print("6️⃣ 数据完整性检查")
    print("=" * 60)
    
    # 检查空值
    cursor.execute('SELECT COUNT(*) FROM history_news WHERE title IS NULL OR title = ""')
    empty_title = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM history_news WHERE content IS NULL OR content = ""')
    empty_content = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM history_news WHERE url IS NULL OR url = ""')
    empty_url = cursor.fetchone()[0]
    
    print(f"\n   📋 空值统计:")
    print(f"      标题为空: {empty_title} 条")
    print(f"      内容为空: {empty_content} 条")
    print(f"      URL为空: {empty_url} 条")
    
    # 检查重复URL
    cursor.execute('''
        SELECT url, COUNT(*) as count
        FROM history_news
        GROUP BY url
        HAVING count > 1
    ''')
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"\n   ⚠️ 发现 {len(duplicates)} 个重复URL（应该被UNIQUE约束阻止）")
    else:
        print(f"\n   ✅ 无重复URL")
    
    # 7. 使用pandas读取统计
    print("\n" + "=" * 60)
    print("7️⃣ Pandas DataFrame 统计")
    print("=" * 60)
    
    df = pd.read_sql_query('SELECT * FROM history_news', conn)
    
    print(f"\n   📊 DataFrame 信息:")
    print(f"      行数: {len(df):,}")
    print(f"      列数: {len(df.columns)}")
    print(f"\n   列名列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"      {i}. {col}")
    
    print(f"\n   数据类型:")
    print(df.dtypes.to_string())
    
    print(f"\n   内存使用: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 检查完成！")
    print("=" * 60)
    
except sqlite3.Error as e:
    print(f"\n❌ 数据库错误: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

