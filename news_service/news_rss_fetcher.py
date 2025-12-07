"""
RSS 新闻抓取与清洗模块
用于抓取 Foresight News 和 BlockBeats 的 RSS 源，并进行 Pentosh1 策略过滤
"""
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import os
import sys
import requests

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class CryptoNewsFetcher:
    def __init__(self):
        # 定义 RSS 源 - 使用分类源，避免噪音
        # 只订阅高价值分类，剔除 Opinion/Analysis/Price Prediction
        self.feeds = {
            # --- 监管与宏观 (S3 核心) ---
            "CD_Policy": [
                "https://www.coindesk.com/arc/outboundfeeds/rss/?path=/policy/"
            ],
            "CT_Regulation": [
                "https://cointelegraph.com/rss/category/policy-regulation"
            ],
            
            # --- 机构与资金 (S1 核心) ---
            "CD_Business": [
                "https://www.coindesk.com/arc/outboundfeeds/rss/?path=/business/"
            ],
            "CT_Business": [
                "https://cointelegraph.com/rss/category/business"
            ],
            
            # --- 技术与基本面 (S2 轮动) ---
            "CD_Tech": [
                "https://www.coindesk.com/arc/outboundfeeds/rss/?path=/tech/"
            ],
            "CT_Bitcoin": [
                "https://cointelegraph.com/rss/tag/bitcoin"
            ]
        }
        
        # Pentosh1 认可的标签 (白名单)
        self.valid_tags = [
            "Business", "Regulation", "Policy", "Institutions", 
            "Bitcoin", "Ethereum", "Legal", "Adoption", "Technology",
            "Tech", "Business", "Policy", "Regulation"
        ]
        
        # 必须剔除的标签 (黑名单)
        self.banned_tags = [
            "Market Analysis", "Price Analysis", "Opinion", 
            "Altcoin Watch", "NFT", "Metaverse", "Analysis",
            "Price Prediction", "Market Wrap", "Daily Digest"
        ]


    def clean_html(self, raw_html):
        """去除 RSS 里的 HTML 标签 (<p>, <a> 等)"""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text().strip()

    def filter_for_pentosh1_strict(self, title, content, entry_tags=None):
        """
        针对 CoinDesk/CoinTelegraph 的严格过滤器
        目标：只保留硬核事实，剔除分析师瞎猜
        返回: (是否保留, 标签)
        """
        text = (title + " " + content).lower()
        
        # 1. 垃圾关键词 (黑名单升级版)
        # CT/CD 经常发 "Price Analysis", "Top 5 coins", "Why Bitcoin price is down"
        noise_keywords = [
            "price analysis", "price prediction", "top 5", "top 3", "could hit", 
            "opinion", "market wrap", "daily digest", "podcast", "video",
            "why", "what to expect", "bull run coming?", "analyst says",
            "should you buy", "when will", "how high", "could reach",
            "here's what happened", "what happened in crypto today", "daily",
            "depends on", "heavily depends", "shift to", "shifting to",
            "cycle", "end-of-year run", "$100k", "$100,000", "run to",
            "is bitcoin shifting", "shifting to a", "reveals how", "implications",
            "chance of hitting", "depends on investors", "market's response"
        ]
        
        # 检查标题是否包含问号（通常是分析类文章）
        if "?" in title:
            # 但允许一些例外，比如 "Will SEC approve?" 这种硬新闻
            if not any(kw in text for kw in ["sec", "approve", "lawsuit", "ban", "jail"]):
                return False, "Analysis_Question"
        
        # 检查明显的分析类标题模式
        analysis_patterns = [
            "charts point", "point to", "direction of", "next move", "next big move",
            "risks return", "risks", "trader says", "makes sense", "price target"
        ]
        for pattern in analysis_patterns:
            if pattern in title.lower():
                # 但允许一些例外，比如监管相关的硬新闻
                if not any(kw in text for kw in ["sec", "approve", "lawsuit", "ban", "jail", "regulation"]):
                    return False, "Analysis_Pattern"
        
        for noise in noise_keywords:
            if noise in text:
                return False, "Opinion/Noise"
        
        # 2. 基于 RSS 标签的过滤（如果可用）
        if entry_tags:
            # 先检查是不是垃圾分类
            for tag in entry_tags:
                tag_lower = tag.lower()
                for banned in self.banned_tags:
                    if banned.lower() in tag_lower:
                        return False, "Banned_Tag"
        
        # 3. Pentosh1 核心关注 (白名单)
        # 只保留4大类核心关键词（使用正则表达式匹配，确保单词边界）
        
        # 1. 宏观/财政 (Macro/Fiscal) - 决定"水位"
        macro_keywords = [
            # 核心央行与人物
            "fed", "federal reserve", "fomc", "jerome powell", "powell", "chair powell",
            "yellen", "janet yellen", "lagarde", "ecb", "european central bank",
            "boj", "bank of japan", "ueda", "pboc", "bank of england", "boe",
            "federal open market committee", "voting member", "fed governor",
            
            # 利率与政策动作
            "rate cut", "rate hike", "interest rate", "fed funds rate", "benchmark rate",
            "basis points", "bps", "pivot", "pause", "skip", "hold rates",
            "tightening", "easing", "monetary policy", "hawkish", "dovish",
            "hike", "cut", "terminal rate", "dot plot", "neutral rate",
            "rate decision", "policy shift", "normalization", "cheap money",
            
            # 通胀与经济指标
            "cpi", "consumer price index", "core cpi", "pce", "personal consumption expenditures",
            "ppi", "producer price index", "inflation", "deflation", "disinflation",
            "stagflation", "hyperinflation", "transitory", "sticky inflation",
            "nfp", "non-farm payrolls", "unemployment", "jobless claims", "labor market",
            "gdp", "gross domestic product", "recession", "soft landing", "hard landing",
            "economic slowdown", "economic growth", "pmi", "purchasing managers index",
            "retail sales", "consumer sentiment", "wage growth",
            
            # 流动性与资产负债表
            "liquidity", "global liquidity", "m2", "money supply", "balance sheet",
            "qe", "quantitative easing", "qt", "quantitative tightening", "tapering",
            "balance sheet reduction", "liquidity injection", "repo", "reverse repo", "rrp",
            "tga", "treasury general account", "bank reserves", "lending facility", "btfp",
            
            # 债券与美元
            "treasury", "us treasury", "bond", "yield", "yield curve", "inverted yield curve",
            "10-year", "2-year", "10y", "2y", "treasury yield", "sovereign debt",
            "dxy", "dollar index", "usd strength", "usd weakness", "fiat", "currency devaluation",
            "debt ceiling", "fiscal deficit", "government spending", "national debt", "credit rating"
        ]
        
        # 2. 机构/资金 (Smart Money) - 决定"风向"
        institutional_keywords = [
            # ETF 与信托产品
            "etf", "spot etf", "bitcoin etf", "ethereum etf", "crypto etf", "etp", "etn",
            "gbtc", "ethe", "ibit", "fbtc", "arkb", "bitb", "trust", "nav discount",
            "premium", "conversion", "approval", "filing", "s-1", "19b-4",
            
            # 顶级资管与发行商
            "blackrock", "larry fink", "fidelity", "vanguard", "grayscale", "bitwise",
            "vaneck", "ark invest", "cathie wood", "franklin templeton", "wisdomtree",
            "invesco", "galaxy digital", "mike novogratz", "21shares", "valkyrie",
            "hashdex", "global x", "proshares", "direction",
            
            # 投行与托管
            "goldman", "goldman sachs", "jpmorgan", "jpm", "jamie dimon", "morgan stanley",
            "citi", "citigroup", "wells fargo", "bny mellon", "state street",
            "standard chartered", "nomura", "laser digital", "deutsche bank",
            "custody", "custodian", "prime broker", "institutional access",
            
            # 企业持仓与巨鲸
            "microstrategy", "mstr", "michael saylor", "tesla", "elon musk", "block", "square",
            "metaplanet", "semler scientific", "corporate treasury", "balance sheet bitcoin",
            "whale", "accumulation", "dumping", "wallet movement", "dormant wallet",
            
            # 交易商与做市商
            "citadel", "jane street", "jump trading", "cumberland", "drw", "wintermute",
            "falconx", "genesis", "blockfi", "otc", "over-the-counter", "otc desk",
            "market maker", "liquidity provider",
            
            # 资金流向与衍生品
            "inflow", "outflow", "netflow", "net inflow", "net outflow", "aum",
            "assets under management", "volume", "trading volume", "open interest", "oi",
            "cme", "chicago mercantile exchange", "futures", "options", "longs", "shorts",
            "commitment of traders", "cot report", "funding rate", "basis", "contango", "backwardation"
        ]
        
        # 3. 监管 (Regulation) - 最大的黑天鹅
        regulation_keywords = [
            # 美国监管机构
            "sec", "securities and exchange commission", "gary gensler", "gensler", "hester peirce",
            "cftc", "commodity futures trading commission", "rostin behnam",
            "doj", "department of justice", "treasury", "yellen", "ofac", "fincen",
            "occ", "fdic", "irs", "white house", "congress", "senate", "house committee",
            
            # 全球监管
            "mica", "markets in crypto-assets", "esma", "ecb", "eu parliament",
            "fca", "financial conduct authority", "uk treasury",
            "mas", "monetary authority of singapore", "sfc", "hong kong",
            "fsa", "japan", "vara", "dubai", "adgm", "abu dhabi",
            "fatf", "financial action task force", "g20", "imf", "bis",
            
            # 法律行动与术语
            "lawsuit", "sue", "sued", "suing", "legal action", "litigation", "court",
            "judge", "ruling", "verdict", "settlement", "settle", "fine", "penalty",
            "charges", "indictment", "subpoena", "wells notice", "enforcement action",
            "cease and desist", "injunction", "guilty", "appeal", "dismissal",
            
            # 监管状态与分类
            "approve", "approval", "reject", "rejection", "deny", "denial", "delay", "deadline",
            "ban", "banned", "prohibit", "crackdown", "restrict", "illegal",
            "security", "securities", "unregistered securities", "howey test", "investment contract",
            "commodity", "property", "currency", "legal tender", "asset class",
            
            # 合规与立法
            "kyc", "aml", "anti-money laundering", "travel rule", "sanctions", "tornado cash",
            "privacy mixer", "compliance", "regulatory framework", "legislation", "bill",
            "fit21", "stablecoin bill", "sab 121", "custody rule", "license", "charter",
            "elizabeth warren", "cynthia lummis", "patrick mchenry", "tom emmer"
        ]
        
        # 4. 风险事件 (Risk Events) - 用于风控
        risk_keywords = [
            # 黑客与攻击
            "hack", "hacked", "hacker", "exploit", "exploited", "vulnerability", "bug",
            "attack", "attacker", "breach", "security breach", "compromised",
            "private key", "phishing", "scam", "fraud", "theft", "stolen",
            "bridge hack", "cross-chain hack", "smart contract exploit", "flash loan",
            "51% attack", "reorg", "double spend", "malware", "ransomware",
            
            # 财务崩溃与破产
            "bankrupt", "bankruptcy", "chapter 11", "insolvent", "insolvency", "default",
            "collapse", "implode", "shutdown", "close down", "liquidate", "liquidation",
            "margin call", "underwater", "bad debt", "deficit", "hole in balance sheet",
            "restructuring", "receivership", "ftx", "alameda", "celsius", "voyager", "3ac",
            
            # 市场脱锚与暂停
            "depeg", "de-peg", "lose peg", "unpeg", "stablecoin depeg", "usdt depeg", "usdc depeg",
            "halt", "halted", "suspended", "pause", "paused", "freeze", "frozen",
            "withdrawal", "withdrawals halted", "deposits suspended", "network congestion",
            "outage", "downtime", "offline", "delist", "delisting",
            
            # 欺诈与犯罪
            "ponzi", "pyramid scheme", "rug pull", "soft rug", "exit scam",
            "money laundering", "terrorist financing", "dark web", "silk road",
            "seized", "confiscated", "arrest", "arrested", "jail", "prison",
            "do kwon", "sbf", "sam bankman-fried", "mashinsky", "fraudster",
            
            # 系统性风险
            "contagion", "spillover", "systemic risk", "domino effect", "cascade",
            "black swan", "crash", "plunge", "dump", "capitulation", "panic selling",
            "fud", "fear uncertainty doubt", "bank run", "run on the bank"
        ]
        
        # 按类别组织关键词
        high_value_keywords = {
            "Macro": macro_keywords,
            "Institutional": institutional_keywords,
            "Regulation": regulation_keywords,
            "Risk": risk_keywords
        }
        
        # 使用正则表达式匹配（带单词边界）
        for tag, keywords in high_value_keywords.items():
            for kw in keywords:
                # 构建正则表达式模式
                escaped_kw = re.escape(kw.lower())
                if ' ' in kw or '-' in kw:
                    # 多词关键词：允许空格、连字符和标点
                    pattern = escaped_kw.replace(r'\ ', r'[\s\-]+').replace(r'\-', r'[\s\-]+')
                else:
                    # 单词边界匹配
                    pattern = r'\b' + escaped_kw + r'\b'
                
                if re.search(pattern, text, re.IGNORECASE):
                    return True, tag
        
        # 4. 基于 RSS 标签的白名单检查（如果可用）
        # 注意：标签检查只是辅助，主要依赖关键词匹配
        # 如果标签匹配到关键词类别，返回对应分类
        if entry_tags:
            for tag in entry_tags:
                tag_lower = tag.lower()
                # 检查标签是否包含关键词
                if any(kw in tag_lower for kw in ["regulation", "policy", "legal", "sec", "lawsuit"]):
                    return True, "Regulation"
                elif any(kw in tag_lower for kw in ["business", "institution", "etf", "funding"]):
                    return True, "Institutional"
                elif any(kw in tag_lower for kw in ["macro", "fed", "inflation", "rate"]):
                    return True, "Macro"
                elif any(kw in tag_lower for kw in ["hack", "exploit", "bankrupt", "halt"]):
                    return True, "Risk"
        
        # 默认丢弃 (只保留匹配到4大类关键词的新闻)
        return False, "Low_Relevance"

    def fetch_all(self, limit=None):
        """
        抓取所有新闻源的最新新闻（使用严格过滤器，只保留硬新闻）
        :param limit: 限制返回的新闻数量，None 表示返回所有
        """
        all_news = []
        print(f"📡 开始抓取 RSS 源: {datetime.now()}")

        for source_name, urls in self.feeds.items():
            # 支持多个备用 URL
            if isinstance(urls, str):
                urls = [urls]
            
            feed = None
            last_error = None
            
            for url in urls:
                try:
                    print(f"   ... 正在连接 {source_name}: {url}")
                    # 使用 requests 获取内容，设置 User-Agent
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.encoding = response.apparent_encoding or 'utf-8'
                    
                    # 调试：检查响应内容
                    if response.status_code != 200:
                        print(f"   ⚠️ HTTP 状态码: {response.status_code}")
                        continue
                    
                    # 检查内容类型
                    content_type = response.headers.get('Content-Type', '')
                    if 'xml' not in content_type.lower() and 'rss' not in content_type.lower() and 'atom' not in content_type.lower():
                        print(f"   ⚠️ 内容类型可能不正确: {content_type}")
                    
                    # 使用 feedparser 解析内容
                    feed = feedparser.parse(response.content)

                    # 即使有警告，也尝试读取条目（有些 RSS 源格式不完美但仍可用）
                    if feed.bozo and len(feed.entries) == 0:
                        error_msg = ""
                        if hasattr(feed, 'bozo_exception'):
                            error_msg = f" ({feed.bozo_exception})"
                        print(f"   ⚠️ {source_name} RSS 解析失败{error_msg}，尝试下一个源...")
                        last_error = feed.bozo_exception if hasattr(feed, 'bozo_exception') else "解析错误"
                        continue
                    
                    # 如果成功获取到条目，即使有警告也使用
                    if len(feed.entries) > 0:
                        if feed.bozo:
                            print(f"   ⚠️ {source_name} RSS 有格式警告，但已获取到 {len(feed.entries)} 条新闻")
                        break
                    else:
                        print(f"   ⚠️ {source_name} 未获取到新闻条目，尝试下一个源...")
                        continue
                    
                except Exception as e:
                    print(f"   ⚠️ {source_name} 连接失败 ({url}): {e}")
                    last_error = str(e)
                    continue

            # 如果所有源都失败了
            if feed is None or len(feed.entries) == 0:
                print(f"   ❌ {source_name} 所有源均失败，跳过")
                continue

            # 成功获取 feed，开始处理条目
            print(f"   ✅ {source_name} 连接成功，获取到 {len(feed.entries)} 条新闻")
            try:
                for entry in feed.entries:
                    # 提取基础信息
                    title = entry.title
                    # 有些 RSS 的正文在 'summary'，有些在 'content'，有些在 'description'
                    raw_content = entry.get('summary', '') or entry.get('description', '')

                    # 处理 content 字段（可能是列表）
                    if isinstance(raw_content, list) and len(raw_content) > 0:
                        raw_content = raw_content[0].get('value', '') if isinstance(raw_content[0], dict) else str(raw_content[0])
                    elif not isinstance(raw_content, str):
                        raw_content = str(raw_content)

                    content = self.clean_html(raw_content)

                    # 提取链接
                    link = entry.link

                    # 提取 RSS 标签
                    entry_tags = []
                    if hasattr(entry, 'tags'):
                        entry_tags = [t.term for t in entry.tags]

                    # 处理时间 (标准化为 YYYY-MM-DD HH:MM:SS)
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                    else:
                        pub_time = datetime.now()

                    # 🔥 核心：Pentosh1 严格过滤器（只保留硬新闻）
                    keep, tag = self.filter_for_pentosh1_strict(title, content, entry_tags=entry_tags)

                    if keep:
                        all_news.append({
                            "source": source_name,
                            "time": pub_time,
                            "tag": tag,
                            "title": title,
                            "content_summary": content[:500],  # 截取前500字给LLM
                            "url": link,
                            "rss_tags": ", ".join(entry_tags) if entry_tags else ""
                        })
            except Exception as e:
                print(f"   ❌ {source_name} 处理新闻条目时出错: {e}")

        # 转为 DataFrame 并按时间倒序
        df = pd.DataFrame(all_news)
        if not df.empty:
            df = df.sort_values(by="time", ascending=False)
            
            # 🔥 去重：相同时间+标题只保留一条，合并所有tag
            print(f"📊 去重前: {len(df)} 条新闻")
            df = self._deduplicate_news(df)
            print(f"📊 去重后: {len(df)} 条新闻")
            
            # 如果指定了限制，只返回前 N 条
            if limit is not None and len(df) > limit:
                df = df.head(limit)
            print(f"✅ 抓取完成！共获得 {len(df)} 条高价值新闻。")
        else:
            print("⚠️ 未获取到符合条件的新闻。")

        return df
    
    def _deduplicate_news(self, df):
        """
        去重：相同时间+标题只保留一条，合并所有tag和source
        """
        if df.empty:
            return df
        
        # 创建唯一标识：时间 + 标题
        df['time_str'] = df['time'].astype(str)
        df['unique_key'] = df['time_str'] + '|||' + df['title']
        
        # 用于存储去重后的数据
        deduplicated_rows = []
        seen_keys = {}
        
        for idx, row in df.iterrows():
            key = row['unique_key']
            
            if key not in seen_keys:
                # 第一次遇到这条新闻，直接添加
                seen_keys[key] = len(deduplicated_rows)
                deduplicated_rows.append({
                    "source": row['source'],
                    "time": row['time'],
                    "tag": row['tag'],
                    "title": row['title'],
                    "content_summary": row['content_summary'],
                    "url": row['url'],
                    "rss_tags": row['rss_tags']
                })
            else:
                # 重复新闻，合并tag、source和rss_tags
                existing_idx = seen_keys[key]
                existing = deduplicated_rows[existing_idx]
                
                # 合并source（用逗号分隔，去重）
                existing_sources = set(existing['source'].split(", "))
                new_sources = set([row['source']])
                merged_sources = existing_sources | new_sources
                existing['source'] = ", ".join(sorted(merged_sources))
                
                # 合并tag（用逗号分隔，去重）
                existing_tags = set(existing['tag'].split(", "))
                new_tags = set([row['tag']])
                merged_tags = existing_tags | new_tags
                existing['tag'] = ", ".join(sorted(merged_tags))
                
                # 合并rss_tags（去重后合并）
                existing_rss_tags = set(existing['rss_tags'].split(", ") if existing['rss_tags'] else [])
                new_rss_tags = set(row['rss_tags'].split(", ") if row['rss_tags'] else [])
                merged_rss_tags = existing_rss_tags | new_rss_tags
                existing['rss_tags'] = ", ".join(sorted([t for t in merged_rss_tags if t]))  # 过滤空字符串
        
        # 转换回DataFrame并删除辅助列
        result_df = pd.DataFrame(deduplicated_rows)
        if not result_df.empty:
            result_df = result_df.sort_values(by="time", ascending=False)
        
        return result_df


if __name__ == "__main__":
    fetcher = CryptoNewsFetcher()
    # 抓取最近十条硬新闻（使用严格过滤器，剔除 Opinion/Analysis）
    df = fetcher.fetch_all(limit=10)

    if not df.empty:
        # 打印所有抓取的新闻
        print(f"\n--- 最近 {len(df)} 条高价值快讯 ---")
        for idx, (i, row) in enumerate(df.iterrows(), 1):
            print(f"\n[{idx}] [{row['tag']}] {row['source']} | {row['time']}")
            print(f"标题: {row['title']}")
            print(f"摘要: {row['content_summary'][:100]}...")
            print(f"链接: {row['url']}")

        # 保存，准备喂给 DeepSeek 做逻辑提取
        output_path = "pentosh1_news_feed.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 数据已保存到: {output_path}")
    else:
        print("⚠️ 没有符合条件的新闻，未生成 CSV 文件。")

