# News Service - RSS 新闻抓取与清洗模块

## 概述

News Service 用于抓取加密货币新闻 RSS 源，并通过 Pentosh1 策略过滤器筛选高价值新闻。

## 功能特性

- 📡 支持多个 RSS 源（Foresight News、BlockBeats）
- 🧹 自动清洗 HTML 标签
- 🎯 Pentosh1 策略过滤器（白名单/黑名单）
- 📊 输出 CSV 格式，便于后续处理

## 安装依赖

```powershell
cd news_service
pip install -r requirements.txt
```

或使用 PowerShell 脚本：

```powershell
.\install_dependencies.ps1
```

## 使用方法

### 基本使用

```powershell
cd news_service
python news_rss_fetcher.py
```

脚本会自动：
1. 抓取所有配置的 RSS 源
2. 清洗 HTML 内容
3. 应用 Pentosh1 过滤器
4. 保存结果到 `pentosh1_news_feed.csv`

### 在代码中使用

```python
from news_rss_fetcher import CryptoNewsFetcher

fetcher = CryptoNewsFetcher()
df = fetcher.fetch_all()

# 查看结果
print(df.head())
```

## RSS 源配置

当前支持的 RSS 源：

- **Foresight News**: https://foresightnews.pro/feed
- **BlockBeats**: https://www.theblockbeats.info/rss.xml

如果 BlockBeats 官方 RSS 不稳定，可以使用 RSSHub 镜像：
```python
"BlockBeats": "https://rsshub.app/blockbeats/newsflash"
```

## Pentosh1 过滤器

### 白名单关键词（高优先级）

- **宏观/监管**: SEC, ETF, 美联储, 加息, 降息, CPI, 通胀
- **聪明钱**: 融资, 领投, a16z, Paradigm, Binance Labs
- **基本面**: 主网, 升级, 分叉, 提案, 回购
- **风险事件**: 黑客, 攻击, 被盗, 清算, 停机

### 黑名单关键词（过滤噪音）

NFT, 空投, 领取, Meme, 土狗, GameFi, 元宇宙, 活动, 圆桌, Space, AMA, 晚报, 早报

### 标签分类

- `Regulation`: 监管相关（SEC, ETF, 监管）
- `Funding`: 融资相关（融资, 领投）
- `Macro`: 宏观相关（美联储, CPI）
- `General_Catalyst`: 其他催化剂事件

## 输出格式

CSV 文件包含以下字段：

| 字段 | 说明 |
|------|------|
| source | 新闻来源（Foresight/BlockBeats） |
| time | 发布时间 |
| tag | 标签分类 |
| title | 新闻标题 |
| content_summary | 内容摘要（前500字） |
| url | 新闻链接 |

## 数据对接流程

1. **RSS 抓取**: 运行 `news_rss_fetcher.py` 生成 `pentosh1_news_feed.csv`
2. **逻辑提取**: 使用 DeepSeek 分析每条新闻的逻辑链
3. **宏观结合**: 结合 Daily_Context.json（L1 宏观数据）
4. **存入数据库**: 最终格式包含 news_event, tag, logic, macro_context_at_time, pentosh1_verdict

## 示例输出

```
📡 开始抓取 RSS 源: 2025-01-20 10:30:00
   ... 正在连接 Foresight
   ... 正在连接 BlockBeats
✅ 抓取完成！共获得 15 条高价值新闻。

--- 最新高价值快讯 ---
[Funding] 2025-01-20 09:00:00 | Paradigm 领投 Monad 2亿美元融资
摘要: 顶级VC大额押注高性能EVM...

💾 数据已保存到: pentosh1_news_feed.csv
```

## 注意事项

1. RSS 源可能不稳定，脚本内置容错机制
2. 过滤器可根据策略需求调整关键词列表
3. 建议定期运行（每小时或每天）以获取最新新闻
4. CSV 文件会覆盖之前的输出，建议添加时间戳命名

