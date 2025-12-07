# 历史新闻挖掘指南 - Pentosh1 逻辑库构建

## 概述

`history_miner.py` 使用 **Sitemap 挖掘法**从 CoinTelegraph 等新闻网站获取历史数据，用于构建 Pentosh1 历史逻辑库（Logic DB）。

## 工作原理

1. **解析 Sitemap**: 从 `https://cointelegraph.com/sitemap.xml` 获取月度 sitemap 列表
2. **过滤链接**: 只保留包含 Pentosh1 关键词的 `/news/` 类型链接
3. **提取内容**: 使用 `trafilatura` 爬取文章正文
4. **保存数据**: 导出为 CSV 格式，便于后续处理

## 安装依赖

```powershell
pip install -r requirements.txt
```

主要依赖：
- `trafilatura`: 文章内容提取
- `requests`: HTTP 请求
- `beautifulsoup4`: HTML 解析
- `pandas`: 数据处理

## 使用方法

### 1. 快速模式（推荐用于每日更新）

挖掘最近 30 天的新闻：

```powershell
python history_miner.py --mode recent --max 50
```

参数说明：
- `--mode recent`: 快速模式，只处理最近2个月的 sitemap
- `--max 50`: 最多爬取 50 篇文章

### 2. 完整模式（用于冷启动）

挖掘过去 12 个月的历史数据：

```powershell
python history_miner.py --mode full --months 12 --max 1000
```

参数说明：
- `--mode full`: 完整模式，处理所有指定的月度 sitemap
- `--months 12`: 回溯 12 个月
- `--max 1000`: 最多爬取 1000 篇文章

## 关键词过滤

脚本会自动过滤包含以下关键词的新闻：

**监管/宏观**:
- SEC, ETF, Fed, 美联储, 加息, 降息, CPI, 通胀
- regulation, policy, lawsuit, approve, ban

**机构/资金**:
- 融资, 领投, a16z, Paradigm, Binance Labs
- blackrock, fidelity, jpmorgan, goldman

**技术/基本面**:
- 主网, 升级, 分叉, 提案, 回购
- mainnet, upgrade, launch, deploy

**风险事件**:
- 黑客, 攻击, 被盗, 清算, 停机
- hack, exploit, stolen, bankrupt

## 输出格式

CSV 文件包含以下字段：

| 字段 | 说明 |
|------|------|
| url | 文章链接 |
| title | 文章标题 |
| content | 文章正文（前2000字符） |
| source | 新闻来源（CoinTelegraph） |
| crawled_at | 爬取时间 |

## 使用场景

### 冷启动（Cold Start）

首次构建逻辑库：

```powershell
# 挖掘过去1年的高价值新闻（约2000-3000篇）
python history_miner.py --mode full --months 12 --max 2000
```

这将：
1. 解析所有月度 sitemap
2. 过滤出包含关键词的新闻链接
3. 爬取文章正文
4. 保存到 `history_news_YYYYMMDD.csv`

### 每日更新（Daily Update）

每天运行 RSS 抓取器即可：

```powershell
python news_rss_fetcher.py
```

RSS 源提供实时更新，无需每天运行历史挖掘。

## 注意事项

1. **请求频率**: 脚本内置了延迟（0.3-0.5秒），避免请求过快
2. **内容提取**: 使用 `trafilatura` 提取正文，如果失败会回退到 BeautifulSoup
3. **数据量**: 完整模式可能需要较长时间，建议分批处理
4. **存储**: CSV 文件会按日期命名，避免覆盖

## 示例输出

```
🚀 快速模式：挖掘最近30天数据
🔍 快速挖掘 CoinTelegraph 最近 30 天的新闻
📡 解析主站点地图: https://cointelegraph.com/sitemap.xml
   ✅ 找到 98 个月度站点地图
📊 找到 357 条相关新闻链接
   [1/50] 爬取: https://cointelegraph.com/news/sec-approves...
   [2/50] 爬取: https://cointelegraph.com/news/eu-crypto-regulations...
✅ 成功爬取 50 篇文章
💾 数据已保存到: history_news_20251206.csv
📊 共 50 条历史新闻
```

## 后续处理

获取的历史数据可以：

1. **导入数据库**: 存入 Logic DB
2. **LLM 分析**: 使用 DeepSeek 提取逻辑链
3. **结合宏观数据**: 与 Daily_Context.json 结合分析
4. **构建知识图谱**: 建立事件-影响-结果的关系网络

## 故障排除

### 问题：无法提取内容

**解决方案**:
- 检查网络连接
- 确认 trafilatura 已正确安装
- 脚本会自动回退到 BeautifulSoup 备用方案

### 问题：Sitemap 解析失败

**解决方案**:
- 检查 sitemap URL 是否可访问
- 脚本支持多种 XML 格式，会自动适配

### 问题：提取内容为空

**解决方案**:
- 可能是网站结构变化
- 检查 URL 是否有效
- 尝试手动访问 URL 确认

