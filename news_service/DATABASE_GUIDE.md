# 数据库存储指南

## 概述

历史新闻挖掘脚本现在使用 **SQLite 数据库**存储数据，替代了之前的 CSV 文件。数据库提供了更好的性能、查询能力和数据完整性。

## 数据库结构

### 表名：`history_news`

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| index_id | INTEGER | 自增主键（自动递增） | PRIMARY KEY AUTOINCREMENT |
| id | TEXT | 文章ID（基于URL的MD5 hash） | NOT NULL |
| url | TEXT | 文章链接 | UNIQUE NOT NULL |
| title | TEXT | 文章标题 | |
| content | TEXT | 完整文章内容 | |
| summary | TEXT | 智能截断的摘要（约300字） | |
| source | TEXT | 新闻来源（如 CoinTelegraph） | |
| publish_time | TEXT | 文章发布时间 | |
| crawled_at | TEXT | 爬取时间 | |

### 索引

- `idx_id`: 基于 id 字段的索引（提高查询速度）
- `idx_url`: 基于 url 字段的索引（提高查询速度）
- `idx_publish_time`: 基于 publish_time 字段的索引（便于按时间排序）
- `idx_source`: 基于 source 字段的索引（便于按来源筛选）

### 主键说明

- **index_id**: 自增主键，每次插入新记录时自动递增
- **id**: 基于URL的MD5 hash，用于唯一标识文章
- **url**: 唯一约束，防止重复URL

## 数据库文件

- **默认文件名**: `history_news.db`（统一文件名，所有数据存在一个表里）
- **位置**: 与脚本同目录
- **格式**: SQLite 3 数据库文件
- **表名**: `history_news`（所有数据都保存在同一个表中）

## 使用方法

### 1. 正常使用

```bash
python history_miner.py --mode full --months 12
```

脚本会自动创建数据库文件 `history_news.db`（如果不存在）。所有数据都保存在同一个 `history_news` 表中。

### 2. 中断恢复

数据库支持中断恢复功能：

```bash
# 第一次运行
python history_miner.py --mode full --months 12

# 如果中断了，重新运行相同命令即可自动恢复
python history_miner.py --mode full --months 12
```

### 3. 查询数据库

#### 使用 Python

```python
import sqlite3
import pandas as pd

# 连接数据库
conn = sqlite3.connect('history_news.db')

# 查询所有数据（包含自增主键 index_id）
df = pd.read_sql_query('SELECT * FROM history_news ORDER BY publish_time DESC', conn)

# 查询特定来源
df = pd.read_sql_query('SELECT * FROM history_news WHERE source = "CoinTelegraph"', conn)

# 查询最近的数据
df = pd.read_sql_query('SELECT * FROM history_news ORDER BY publish_time DESC LIMIT 10', conn)

# 按自增主键查询
df = pd.read_sql_query('SELECT * FROM history_news ORDER BY index_id DESC LIMIT 10', conn)

conn.close()
```

#### 使用 SQLite 命令行工具

```bash
# 打开数据库
sqlite3 history_news.db

# 查看表结构
.schema history_news

# 查询数据
SELECT COUNT(*) FROM history_news;
SELECT * FROM history_news ORDER BY publish_time DESC LIMIT 10;

# 查询自增主键
SELECT index_id, id, url, title FROM history_news ORDER BY index_id DESC LIMIT 10;

# 退出
.quit
```

## 优势

### 相比 CSV 的优势

1. **性能更好**: 数据库查询比读取整个 CSV 文件快得多
2. **支持索引**: 可以快速按时间、来源等字段查询
3. **数据完整性**: UNIQUE 约束防止重复数据
4. **增量更新**: 只保存新增数据，避免重复写入
5. **事务支持**: 保证数据一致性
6. **查询灵活**: 支持复杂的 SQL 查询

### 检查点功能

- ✅ 每5条自动保存一次
- ✅ 中断后自动恢复
- ✅ 只保存新增数据，避免重复写入
- ✅ 自动去重（基于 URL）

## 数据导出

如果需要导出为 CSV：

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('history_news.db')
df = pd.read_sql_query('SELECT * FROM history_news', conn)
df.to_csv('export.csv', index=False, encoding='utf-8-sig')
conn.close()
```

或者使用脚本自带的备份功能（会自动生成 CSV 备份）。

## 维护建议

1. **定期备份**: 定期复制 `.db` 文件作为备份
2. **清理旧数据**: 可以删除超过一定时间的旧数据
3. **优化数据库**: 定期运行 `VACUUM` 命令优化数据库

```sql
VACUUM;
```

## 故障排除

### 问题：数据库文件损坏

**解决方案**: 
1. 从备份恢复
2. 或者删除数据库文件，重新运行脚本

### 问题：数据库文件太大

**解决方案**: 
1. 这是正常的，数据库包含完整的文章内容
2. 可以定期导出为 CSV 并清理旧数据
3. 使用 `VACUUM` 命令优化数据库

### 问题：无法写入数据库

**解决方案**: 
1. 检查文件权限
2. 确保磁盘空间充足
3. 检查是否有其他进程正在使用数据库

## 示例查询

```sql
-- 统计各来源的文章数量
SELECT source, COUNT(*) as count 
FROM history_news 
GROUP BY source;

-- 查询包含特定关键词的文章
SELECT * FROM history_news 
WHERE title LIKE '%SEC%' OR content LIKE '%SEC%';

-- 查询最近一周的文章
SELECT * FROM history_news 
WHERE publish_time >= datetime('now', '-7 days')
ORDER BY publish_time DESC;

-- 查询摘要长度
SELECT index_id, url, title, LENGTH(summary) as summary_length 
FROM history_news 
ORDER BY summary_length DESC;

-- 查询最新的记录（按自增主键）
SELECT index_id, id, url, title, publish_time 
FROM history_news 
ORDER BY index_id DESC 
LIMIT 10;
```

