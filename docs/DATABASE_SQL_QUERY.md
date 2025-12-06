# 数据库 SQL 查询指南

## 📊 数据库信息

### 数据库类型
- **SQLite3** - 轻量级文件数据库

### 数据库文件位置
- **默认路径**: `config.db` (项目根目录)
- **完整路径**: `E:\nofx-dev\config.db` (Windows)
- **相对路径**: `./config.db`

## 🔧 查询工具

### 方法1: 命令行工具 (推荐)

#### Windows PowerShell
```powershell
# 安装 SQLite (如果未安装)
# 下载: https://www.sqlite.org/download.html
# 或使用 Chocolatey: choco install sqlite

# 进入项目目录
cd E:\nofx-dev

# 打开数据库
sqlite3 config.db

# 在 SQLite 命令行中执行查询
```

#### Linux/Mac
```bash
# 安装 SQLite (如果未安装)
# Ubuntu/Debian: sudo apt-get install sqlite3
# Mac: brew install sqlite3

# 进入项目目录
cd /path/to/nofx-dev

# 打开数据库
sqlite3 config.db
```

### 方法2: 图形化工具 (推荐)

#### DB Browser for SQLite (免费)
- 下载: https://sqlitebrowser.org/
- 打开 `config.db` 文件即可可视化查询

#### DBeaver (免费，功能强大)
- 下载: https://dbeaver.io/
- 支持多种数据库，包括 SQLite

#### VS Code 扩展
- 安装扩展: "SQLite Viewer" 或 "SQLite"
- 直接在 VS Code 中查看和查询

### 方法3: 在线工具
- SQLite Online: https://sqliteonline.com/
- 上传 `config.db` 文件即可查询

## 📋 常用 SQL 查询示例

### 1. 查看所有表
```sql
.tables
```

### 2. 查看表结构
```sql
-- 查看决策日志表结构
.schema trader_decision_logs

-- 查看决策动作表结构
.schema trader_decision_actions

-- 查看成交详情表结构
.schema trader_trade_details
```

### 3. 查询决策日志

#### 查询所有决策日志
```sql
SELECT 
    id,
    trader_id,
    timestamp,
    cycle_number,
    success,
    error_message
FROM trader_decision_logs
ORDER BY timestamp DESC
LIMIT 10;
```

#### 查询特定交易员的决策日志
```sql
SELECT 
    id,
    timestamp,
    cycle_number,
    success,
    error_message
FROM trader_decision_logs
WHERE trader_id = 'your_trader_id'
ORDER BY timestamp DESC;
```

#### 查询失败的决策
```sql
SELECT 
    id,
    trader_id,
    timestamp,
    cycle_number,
    error_message
FROM trader_decision_logs
WHERE success = 0
ORDER BY timestamp DESC;
```

### 4. 查询决策动作（订单）

#### 查询所有决策动作
```sql
SELECT 
    id,
    decision_log_id,
    action,
    symbol,
    quantity,
    price,
    order_id,
    success,
    error,
    timestamp
FROM trader_decision_actions
ORDER BY timestamp DESC
LIMIT 20;
```

#### 查询特定决策日志的所有动作
```sql
SELECT 
    a.id,
    a.action,
    a.symbol,
    a.quantity,
    a.price,
    a.order_id,
    a.success,
    a.error,
    a.timestamp
FROM trader_decision_actions a
WHERE a.decision_log_id = 1
ORDER BY a.timestamp ASC;
```

#### 查询成功的订单
```sql
SELECT 
    a.id,
    a.symbol,
    a.action,
    a.quantity,
    a.price,
    a.order_id,
    a.timestamp
FROM trader_decision_actions a
WHERE a.success = 1
ORDER BY a.timestamp DESC;
```

#### 查询失败的订单
```sql
SELECT 
    a.id,
    a.symbol,
    a.action,
    a.error,
    a.timestamp
FROM trader_decision_actions a
WHERE a.success = 0
ORDER BY a.timestamp DESC;
```

### 5. 查询成交详情

#### 查询所有成交记录
```sql
SELECT 
    t.id,
    t.decision_action_id,
    t.trade_id,
    t.price,
    t.quantity,
    t.commission,
    datetime(t.time/1000, 'unixepoch') as trade_time,
    t.is_buyer,
    t.is_maker
FROM trader_trade_details t
ORDER BY t.time DESC
LIMIT 50;
```

#### 查询特定订单的成交详情
```sql
SELECT 
    t.trade_id,
    t.price,
    t.quantity,
    t.quote_quantity,
    t.commission,
    datetime(t.time/1000, 'unixepoch') as trade_time,
    t.is_buyer,
    t.is_maker
FROM trader_trade_details t
WHERE t.decision_action_id = 1
ORDER BY t.time ASC;
```

### 6. 关联查询（完整决策信息）

#### 查询完整的决策记录（包含动作和成交）
```sql
SELECT 
    l.id as log_id,
    l.trader_id,
    l.timestamp as decision_time,
    l.cycle_number,
    l.success as decision_success,
    a.id as action_id,
    a.action,
    a.symbol,
    a.quantity,
    a.price,
    a.order_id,
    a.success as action_success,
    COUNT(t.id) as trade_count
FROM trader_decision_logs l
LEFT JOIN trader_decision_actions a ON l.id = a.decision_log_id
LEFT JOIN trader_trade_details t ON a.id = t.decision_action_id
WHERE l.trader_id = 'your_trader_id'
GROUP BY l.id, a.id
ORDER BY l.timestamp DESC, a.timestamp ASC
LIMIT 20;
```

#### 查询决策日志及其所有动作
```sql
SELECT 
    l.id as log_id,
    l.timestamp,
    l.cycle_number,
    a.action,
    a.symbol,
    a.quantity,
    a.price,
    a.order_id,
    a.success
FROM trader_decision_logs l
LEFT JOIN trader_decision_actions a ON l.id = a.decision_log_id
WHERE l.trader_id = 'your_trader_id'
ORDER BY l.timestamp DESC, a.timestamp ASC;
```

#### 查询订单及其成交详情
```sql
SELECT 
    a.id as action_id,
    a.symbol,
    a.action,
    a.order_id,
    t.trade_id,
    t.price,
    t.quantity,
    t.commission,
    datetime(t.time/1000, 'unixepoch') as trade_time
FROM trader_decision_actions a
LEFT JOIN trader_trade_details t ON a.id = t.decision_action_id
WHERE a.order_id IS NOT NULL
ORDER BY a.timestamp DESC, t.time ASC;
```

### 7. 统计查询

#### 统计每个交易员的决策数量
```sql
SELECT 
    trader_id,
    COUNT(*) as total_decisions,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_decisions,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_decisions
FROM trader_decision_logs
GROUP BY trader_id;
```

#### 统计每个币种的交易次数
```sql
SELECT 
    symbol,
    COUNT(*) as trade_count,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_trades,
    SUM(CASE WHEN action = 'open_long' OR action = 'open_short' THEN 1 ELSE 0 END) as open_trades,
    SUM(CASE WHEN action = 'close_long' OR action = 'close_short' THEN 1 ELSE 0 END) as close_trades
FROM trader_decision_actions
GROUP BY symbol
ORDER BY trade_count DESC;
```

#### 统计每日决策数量
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as decision_count,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_count
FROM trader_decision_logs
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

#### 统计订单成交情况
```sql
SELECT 
    a.symbol,
    COUNT(DISTINCT a.id) as total_orders,
    COUNT(DISTINCT t.id) as total_trades,
    SUM(t.quantity) as total_quantity,
    SUM(t.commission) as total_commission
FROM trader_decision_actions a
LEFT JOIN trader_trade_details t ON a.id = t.decision_action_id
WHERE a.success = 1
GROUP BY a.symbol
ORDER BY total_orders DESC;
```

### 8. 导出数据

#### 导出为 CSV
```sql
.headers on
.mode csv
.output decisions.csv
SELECT * FROM trader_decision_logs;
.output stdout
```

#### 导出为 JSON (需要额外工具)
使用 SQLite 命令行工具或 Python 脚本

## 💡 实用技巧

### 1. 格式化输出
```sql
-- 设置列模式
.mode column
.headers on

-- 设置宽度
.width 10 20 15

-- 执行查询
SELECT * FROM trader_decision_logs LIMIT 5;
```

### 2. 查看数据库信息
```sql
-- 查看数据库文件信息
.dbinfo

-- 检查数据库完整性
PRAGMA integrity_check;

-- 查看表大小
SELECT 
    name,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as row_count
FROM sqlite_master m
WHERE type='table';
```

### 3. 备份数据库
```bash
# Windows PowerShell
sqlite3 config.db ".backup backup_$(Get-Date -Format 'yyyyMMdd').db"

# Linux/Mac
sqlite3 config.db ".backup backup_$(date +%Y%m%d).db"
```

### 4. 性能优化查询
```sql
-- 分析查询计划
EXPLAIN QUERY PLAN 
SELECT * FROM trader_decision_logs 
WHERE trader_id = 'your_trader_id' 
ORDER BY timestamp DESC;

-- 更新统计信息
ANALYZE;
```

## ⚠️ 注意事项

1. **备份数据**: 修改数据前请先备份
2. **只读查询**: 建议使用只读模式打开数据库
3. **事务处理**: 大量更新操作时使用事务
4. **索引使用**: 查询时尽量使用已创建的索引字段

## 🔗 相关资源

- SQLite 官方文档: https://www.sqlite.org/docs.html
- SQLite 教程: https://www.sqlitetutorial.net/
- DB Browser for SQLite: https://sqlitebrowser.org/

