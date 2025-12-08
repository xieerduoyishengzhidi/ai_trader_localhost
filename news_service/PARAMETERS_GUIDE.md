# history_miner.py 参数详解

## 概述

`history_miner.py` 是一个历史新闻挖掘工具，支持两种模式：完整历史挖掘和快速模式。所有参数都是可选的，有合理的默认值。

## 命令行参数

### 1. `--mode` (挖掘模式)

**类型**: 字符串，可选值  
**默认值**: `recent`  
**可选值**: 
- `full`: 完整历史挖掘模式
- `recent`: 快速模式（最近30天）

**说明**:
- **`full` 模式**: 挖掘指定月数的完整历史数据，适合冷启动或批量数据收集
- **`recent` 模式**: 快速挖掘最近30天的数据，适合日常更新

**示例**:
```bash
# 使用完整模式
python history_miner.py --mode full

# 使用快速模式（默认）
python history_miner.py --mode recent
# 或者直接不指定（默认就是 recent）
python history_miner.py
```

---

### 2. `--months` (回溯月数)

**类型**: 整数  
**默认值**: `12`  
**适用范围**: 仅用于 `full` 模式  
**说明**: 指定要回溯多少个月的历史数据

**示例**:
```bash
# 挖掘过去12个月的数据（默认）
python history_miner.py --mode full --months 12

# 挖掘过去6个月的数据
python history_miner.py --mode full --months 6

# 挖掘过去24个月的数据
python history_miner.py --mode full --months 24
```

**注意事项**:
- 只在 `--mode full` 时有效
- `recent` 模式固定为最近30天，此参数无效
- 月数越大，需要处理的数据越多，耗时越长

---

### 3. `--max` (最大文章数量)

**类型**: 整数  
**默认值**: `None`（不限制）  
**适用范围**: 仅用于 `full` 模式  
**说明**: 限制最多爬取多少篇文章。如果设置为 `None` 或不指定，将爬取所有匹配的新闻。

**示例**:
```bash
# 不限制数量（默认，爬取所有匹配的新闻）
python history_miner.py --mode full --months 12

# 限制最多爬取1000篇文章
python history_miner.py --mode full --months 12 --max 1000

# 限制最多爬取500篇文章
python history_miner.py --mode full --months 12 --max 500
```

**注意事项**:
- 只在 `--mode full` 时有效
- `recent` 模式固定为最多50篇，此参数无效
- 设置为 `None` 时，会爬取所有匹配关键词的新闻（可能数量很大）

---

## 完整使用示例

### 示例 1: 快速模式（默认）

```bash
python history_miner.py
```

**等价于**:
```bash
python history_miner.py --mode recent
```

**行为**:
- 挖掘最近30天的数据
- 最多爬取50篇文章
- 适合日常快速更新

---

### 示例 2: 完整模式 - 挖掘过去12个月（默认）

```bash
python history_miner.py --mode full
```

**等价于**:
```bash
python history_miner.py --mode full --months 12
```

**行为**:
- 挖掘过去12个月的数据
- 不限制文章数量（爬取所有匹配的新闻）
- 适合冷启动或完整数据收集

---

### 示例 3: 完整模式 - 挖掘过去6个月，限制1000篇

```bash
python history_miner.py --mode full --months 6 --max 1000
```

**行为**:
- 挖掘过去6个月的数据
- 最多爬取1000篇文章
- 适合测试或小规模数据收集

---

### 示例 4: 完整模式 - 挖掘过去24个月，不限制数量

```bash
python history_miner.py --mode full --months 24
```

**行为**:
- 挖掘过去24个月的数据
- 不限制文章数量
- 适合大规模历史数据收集（可能需要很长时间）

---

## 参数组合说明

| 模式 | --months | --max | 说明 |
|------|----------|-------|------|
| `recent` | 忽略 | 忽略 | 固定：最近30天，最多50篇 |
| `full` | 12（默认） | None（默认） | 过去12个月，不限制数量 |
| `full` | 自定义 | None | 过去N个月，不限制数量 |
| `full` | 自定义 | 自定义 | 过去N个月，最多M篇 |

---

## 实际运行示例

### 场景 1: 首次运行（冷启动）

```bash
# 挖掘过去12个月的所有数据
python history_miner.py --mode full --months 12
```

**预期结果**:
- 创建 `history_news.db` 数据库
- 爬取过去12个月所有匹配关键词的新闻
- 可能需要数小时甚至更长时间
- 每5条自动保存一次，支持中断恢复

---

### 场景 2: 日常更新

```bash
# 快速模式，获取最近30天的数据
python history_miner.py --mode recent
```

**预期结果**:
- 使用现有的 `history_news.db` 数据库
- 快速爬取最近30天的数据（最多50篇）
- 通常几分钟内完成

---

### 场景 3: 测试运行

```bash
# 只爬取少量数据用于测试
python history_miner.py --mode full --months 1 --max 10
```

**预期结果**:
- 只爬取过去1个月的数据
- 最多10篇文章
- 快速完成，适合测试脚本功能

---

## 参数验证

脚本会自动验证参数的有效性：

- ✅ `--mode` 必须是 `full` 或 `recent`
- ✅ `--months` 必须是正整数
- ✅ `--max` 必须是正整数（如果指定）

如果参数无效，脚本会显示错误信息并退出。

---

## 查看帮助信息

使用 `--help` 参数查看所有可用参数：

```bash
python history_miner.py --help
```

**输出示例**:
```
usage: history_miner.py [-h] [--mode {full,recent}] [--months MONTHS] [--max MAX]

历史新闻挖掘工具

optional arguments:
  -h, --help            show this help message and exit
  --mode {full,recent}  挖掘模式: full=完整历史, recent=最近30天
  --months MONTHS       回溯月数（仅用于 full 模式）
  --max MAX             最大文章数量（默认不限制）
```

---

## 注意事项

1. **数据库文件**: 所有数据都保存在 `history_news.db` 中，统一管理
2. **中断恢复**: 支持中断后继续，每5条自动保存一次
3. **去重机制**: 基于 URL 自动去重，不会重复爬取
4. **请求频率**: 内置延迟机制，避免请求过快被封
5. **数据量**: `full` 模式不限制数量时，可能爬取数千篇文章，需要较长时间

---

## 推荐配置

### 首次运行（冷启动）
```bash
python history_miner.py --mode full --months 12
```

### 日常更新
```bash
python history_miner.py --mode recent
```

### 测试/调试
```bash
python history_miner.py --mode full --months 1 --max 10
```




