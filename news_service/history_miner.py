"""
历史新闻挖掘模块 - 使用 Sitemap 挖掘法
用于构建 Pentosh1 历史逻辑库（Logic DB）
"""
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import os
import sys
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import trafilatura
import hashlib
import sqlite3

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class HistoryNewsMiner:
    def __init__(self):
        # Pentosh1 关注的关键词（用于过滤历史文章）
        # 只保留核心关键词，分为4大类
        
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
        # 合并所有关键词
        self.target_keywords = macro_keywords + institutional_keywords + regulation_keywords + risk_keywords
        
        # 新闻站点配置
        self.sites = {
            "CoinTelegraph": {
                "sitemap": "https://cointelegraph.com/sitemap.xml",
                "base_url": "https://cointelegraph.com",
                "news_pattern": r"/news/"
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_sitemap(self, sitemap_url):
        """获取并解析 sitemap.xml"""
        try:
            print(f"   📍 获取站点地图: {sitemap_url}")
            response = requests.get(sitemap_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析 XML（处理命名空间）
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                # 如果解析失败，尝试用 BeautifulSoup
                soup = BeautifulSoup(response.content, 'xml')
                urls = []
                for loc in soup.find_all('loc'):
                    urls.append(loc.text)
                return urls
            
            # 定义命名空间
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            urls = []
            
            # 方法1: 使用命名空间查找
            for namespace in ['{http://www.sitemaps.org/schemas/sitemap/0.9}', '']:
                for loc in root.findall(f'.//{namespace}loc'):
                    if loc.text:
                        urls.append(loc.text)
                if urls:
                    break
            
            # 方法2: 如果没有找到，尝试直接查找所有 loc 标签
            if not urls:
                for elem in root.iter():
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag.lower() == 'loc' and elem.text:
                        urls.append(elem.text)
            
            return urls
        except Exception as e:
            print(f"   ❌ 获取站点地图失败: {e}")
            return []

    def extract_monthly_sitemaps(self, main_sitemap_url):
        """从主 sitemap 提取月度 sitemap 链接"""
        print(f"📡 解析主站点地图: {main_sitemap_url}")
        sitemaps = self.fetch_sitemap(main_sitemap_url)
        
        # 过滤出月度 sitemap（通常包含 post-YYYY-MM 格式）
        monthly_sitemaps = []
        for sitemap_url in sitemaps:
            if 'post-' in sitemap_url.lower() or 'sitemap' in sitemap_url.lower():
                monthly_sitemaps.append(sitemap_url)
        
        print(f"   ✅ 找到 {len(monthly_sitemaps)} 个月度站点地图")
        return monthly_sitemaps

    def filter_news_urls(self, urls, keywords=None, months_back=12):
        """过滤新闻 URL，只保留包含关键词的链接（使用正则表达式匹配）"""
        if keywords is None:
            keywords = self.target_keywords
        
        filtered_urls = []
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        
        # 构建正则表达式模式（使用单词边界）
        # 将关键词转换为正则表达式，使用 \b 确保单词边界匹配
        patterns = []
        for kw in keywords:
            # 转义特殊字符
            escaped_kw = re.escape(kw.lower())
            # 使用单词边界，但允许空格和连字符
            if ' ' in kw or '-' in kw:
                # 多词关键词：允许空格和连字符
                pattern = escaped_kw.replace(r'\ ', r'[\s-]+').replace(r'\-', r'[\s-]+')
            else:
                # 单词边界匹配
                pattern = r'\b' + escaped_kw + r'\b'
            patterns.append(pattern)
        
        # 组合所有模式
        combined_pattern = '|'.join(patterns)
        regex = re.compile(combined_pattern, re.IGNORECASE)
        
        for url in urls:
            # 只保留 /news/ 类型的链接
            if '/news/' not in url.lower():
                continue
            
            # 使用正则表达式匹配
            if regex.search(url.lower()):
                filtered_urls.append(url)
        
        return filtered_urls

    def extract_article_content(self, url):
        """使用 trafilatura 提取文章正文（完整内容，不截断）"""
        try:
            # 方法1: 使用 trafilatura 直接从 URL 提取
            article = trafilatura.extract(trafilatura.fetch_url(url))
            if article and len(article.strip()) > 100:
                return article.strip()  # 返回完整内容
        except Exception as e:
            pass
        
        # 方法2: 备用方案 - requests + BeautifulSoup
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = response.apparent_encoding or 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 尝试多种选择器提取正文
            content_selectors = [
                'article',
                '[class*="article"]',
                '[class*="post-content"]',
                '[class*="content"]',
                'main'
            ]
            
            text_parts = []
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for elem in elements[:2]:  # 只取前2个
                        text = elem.get_text(separator=' ', strip=True)
                        if len(text) > 200:  # 确保有足够内容
                            text_parts.append(text)
                    if text_parts:
                        break
            
            if text_parts:
                full_text = ' '.join(text_parts)
                if len(full_text) > 100:
                    return full_text  # 返回完整内容
            
            return None
        except Exception as e:
            return None
    
    def extract_article_metadata(self, url, content):
        """从文章内容或 URL 提取元数据（标题、发布时间等）"""
        title = ""
        publish_time = None
        
        # 尝试从 URL 提取标题
        url_parts = url.split('/')
        if url_parts:
            title = url_parts[-1].replace('-', ' ').replace('_', ' ').title()
        
        # 尝试从内容中提取标题和发布时间
        if content:
            # 使用 trafilatura 提取元数据
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    metadata = trafilatura.extract_metadata(downloaded)
                    if metadata:
                        if metadata.title:
                            title = metadata.title
                        if metadata.date:
                            try:
                                publish_time = datetime.fromisoformat(str(metadata.date).replace('Z', '+00:00'))
                            except:
                                pass
            except:
                pass
            
            # 如果 trafilatura 失败，尝试从 HTML 中提取
            if not publish_time:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 提取标题
                    if not title or title == url_parts[-1]:
                        title_tag = soup.find('title')
                        if title_tag:
                            title = title_tag.get_text(strip=True)
                    
                    # 提取发布时间
                    time_selectors = [
                        'time[datetime]',
                        '[class*="date"]',
                        '[class*="time"]',
                        'meta[property="article:published_time"]',
                        'meta[name="publish-date"]'
                    ]
                    for selector in time_selectors:
                        elem = soup.select_one(selector)
                        if elem:
                            time_str = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                            if time_str:
                                try:
                                    # 尝试解析各种时间格式
                                    publish_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                    break
                                except:
                                    try:
                                        publish_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                                        break
                                    except:
                                        pass
                except:
                    pass
        
        # 如果仍然没有时间，使用当前时间
        if not publish_time:
            publish_time = datetime.now()
        
        return title, publish_time
    
    def smart_truncate_summary(self, text, target_length=300):
        """
        智能截断摘要：在300字左右找到句号截断
        """
        if not text:
            return ""
        
        # 清理文本
        text = text.strip()
        
        # 如果文本长度小于目标长度，直接返回
        if len(text) <= target_length:
            return text
        
        # 在目标长度附近查找句号
        search_start = max(0, target_length - 100)  # 向前搜索100字
        search_end = min(len(text), target_length + 100)  # 向后搜索100字
        
        # 查找句号、问号、感叹号
        sentence_endings = ['.', '!', '?', '。', '！', '？']
        best_pos = target_length
        
        for pos in range(search_start, search_end):
            if text[pos] in sentence_endings:
                # 检查后面是否有空格或换行
                if pos + 1 < len(text) and text[pos + 1] in [' ', '\n', '\r', '\t']:
                    best_pos = pos + 1
                    break
        
        # 如果没找到句号，在目标长度处截断
        summary = text[:best_pos].strip()
        
        # 确保摘要不为空
        if not summary:
            summary = text[:target_length].strip()
        
        return summary

    def init_database(self, db_path):
        """初始化数据库，创建表结构（只在表不存在时创建）"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='history_news'
        ''')
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # 创建表结构（与CSV结构一致，但增加自增主键）
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
            
            # 创建索引以提高查询速度
            cursor.execute('CREATE INDEX idx_id ON history_news(id)')
            cursor.execute('CREATE INDEX idx_url ON history_news(url)')
            cursor.execute('CREATE INDEX idx_publish_time ON history_news(publish_time)')
            cursor.execute('CREATE INDEX idx_source ON history_news(source)')
            
            conn.commit()
            print(f"   ✅ 创建新表: history_news")
        else:
            # 检查是否需要添加 index_id 列（兼容旧表结构）
            cursor.execute('PRAGMA table_info(history_news)')
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'index_id' not in columns:
                # 添加自增主键列
                print(f"   🔄 升级表结构：添加 index_id 列...")
                cursor.execute('''
                    CREATE TABLE history_news_new (
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
                
                # 迁移数据
                cursor.execute('''
                    INSERT INTO history_news_new 
                    (id, url, title, content, summary, source, publish_time, crawled_at)
                    SELECT id, url, title, content, summary, source, publish_time, crawled_at
                    FROM history_news
                ''')
                
                # 删除旧表，重命名新表
                cursor.execute('DROP TABLE history_news')
                cursor.execute('ALTER TABLE history_news_new RENAME TO history_news')
                
                # 重新创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_id ON history_news(id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON history_news(url)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON history_news(publish_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON history_news(source)')
                
                conn.commit()
                print(f"   ✅ 表结构升级完成")
            else:
                # 确保索引存在
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_id ON history_news(id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON history_news(url)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON history_news(publish_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON history_news(source)')
                conn.commit()
        
        conn.close()
    
    def load_checkpoint(self, db_path):
        """从数据库加载检查点：返回已处理的URL集合和已保存的文章列表"""
        processed_urls = set()
        existing_articles = []
        
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 查询所有已处理的URL
                cursor.execute('SELECT url FROM history_news')
                urls = cursor.fetchall()
                processed_urls = set([url[0] for url in urls])
                
                # 查询所有文章（包含 index_id）
                cursor.execute('SELECT index_id, id, url, title, content, summary, source, publish_time, crawled_at FROM history_news')
                rows = cursor.fetchall()
                
                for row in rows:
                    existing_articles.append({
                        "index_id": row[0],
                        "id": row[1],
                        "url": row[2],
                        "title": row[3],
                        "content": row[4],
                        "summary": row[5],
                        "source": row[6],
                        "publish_time": row[7],
                        "crawled_at": row[8]
                    })
                
                conn.close()
                print(f"   📂 发现数据库文件: {len(processed_urls)} 条已处理")
            except Exception as e:
                print(f"   ⚠️ 读取数据库失败: {e}")
        else:
            # 如果数据库不存在，初始化它
            self.init_database(db_path)
            print(f"   📂 创建新数据库: {db_path}")
        
        return processed_urls, existing_articles
    
    def save_checkpoint(self, articles, db_path):
        """保存检查点：将文章保存到数据库（index_id 自动递增）"""
        if not articles:
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 确保表存在
            self.init_database(db_path)
            
            # 批量插入或更新文章（使用 INSERT OR REPLACE 避免重复）
            # index_id 会自动递增，不需要手动指定
            for article in articles:
                cursor.execute('''
                    INSERT OR REPLACE INTO history_news 
                    (id, url, title, content, summary, source, publish_time, crawled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.get('id', ''),
                    article.get('url', ''),
                    article.get('title', ''),
                    article.get('content', ''),
                    article.get('summary', ''),
                    article.get('source', ''),
                    str(article.get('publish_time', '')),
                    str(article.get('crawled_at', ''))
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"   ⚠️ 保存数据库失败: {e}")
            return False

    def mine_history(self, site_name="CoinTelegraph", months_back=12, max_articles=None, db_path=None):
        """
        挖掘历史新闻（支持中断恢复，使用SQLite数据库）
        :param site_name: 站点名称
        :param months_back: 回溯多少个月
        :param max_articles: 最大文章数量（None 表示不限制）
        :param db_path: 数据库文件路径（用于中断恢复）
        """
        if site_name not in self.sites:
            print(f"❌ 未知站点: {site_name}")
            return pd.DataFrame()
        
        site_config = self.sites[site_name]
        main_sitemap = site_config["sitemap"]
        
        # 设置数据库文件路径（统一使用同一个数据库文件）
        if db_path is None:
            db_path = "history_news.db"  # 统一文件名，所有数据存在一个表里
        
        print(f"\n🔍 开始挖掘 {site_name} 的历史数据（过去 {months_back} 个月）")
        print(f"📅 目标关键词: {', '.join(self.target_keywords[:5])}...")
        if max_articles:
            print(f"📊 最大文章数量限制: {max_articles}")
        else:
            print(f"📊 无数量限制，将爬取所有匹配的新闻")
        print(f"💾 数据库文件: {db_path}")
        
        # 初始化数据库
        self.init_database(db_path)
        
        # 加载检查点（如果存在）
        processed_urls, existing_articles = self.load_checkpoint(db_path)
        articles = existing_articles.copy()
        
        if processed_urls:
            print(f"   ✅ 从检查点恢复: 已处理 {len(processed_urls)} 条，将继续处理剩余URL")
        
        # 1. 获取月度 sitemap 列表
        monthly_sitemaps = self.extract_monthly_sitemaps(main_sitemap)
        
        # 限制只处理最近 N 个月的
        if len(monthly_sitemaps) > months_back:
            monthly_sitemaps = monthly_sitemaps[:months_back]
        
        # 2. 从每个月度 sitemap 提取文章链接
        all_news_urls = []
        for sitemap_url in monthly_sitemaps:
            print(f"\n   📂 处理: {sitemap_url}")
            urls = self.fetch_sitemap(sitemap_url)
            filtered = self.filter_news_urls(urls)
            all_news_urls.extend(filtered)
            print(f"   ✅ 提取到 {len(filtered)} 条相关新闻链接")
            
            # 如果设置了限制，检查是否达到
            if max_articles and len(all_news_urls) >= max_articles:
                all_news_urls = all_news_urls[:max_articles]
                print(f"   ⚠️ 达到最大数量限制，停止收集链接")
                break
        
        # 过滤掉已处理的URL
        remaining_urls = [url for url in all_news_urls if url not in processed_urls]
        print(f"\n📊 共找到 {len(all_news_urls)} 条相关新闻链接")
        print(f"📊 已处理 {len(processed_urls)} 条，剩余 {len(remaining_urls)} 条待处理")
        
        if not remaining_urls:
            print("✅ 所有URL已处理完成！")
            return pd.DataFrame(articles)
        
        # 3. 爬取文章内容
        start_idx = len(processed_urls) + 1
        new_articles_count = 0  # 记录新增文章数量
        
        for idx, url in enumerate(remaining_urls, start=start_idx):
            print(f"   [{idx}/{len(all_news_urls)}] 爬取: {url[:80]}...")
            
            try:
                content = self.extract_article_content(url)
                if content:
                    # 提取元数据（标题、发布时间）
                    title, publish_time = self.extract_article_metadata(url, content)
                    
                    # 生成唯一 ID（基于 URL 的 hash）
                    article_id = hashlib.md5(url.encode()).hexdigest()[:16]
                    
                    # 智能截断摘要（300字左右，在句号处截断）
                    summary = self.smart_truncate_summary(content, target_length=300)
                    
                    new_article = {
                        "id": article_id,
                        "url": url,
                        "title": title,
                        "content": content,  # 完整内容
                        "summary": summary,  # 智能截断的摘要
                        "source": site_name,
                        "publish_time": str(publish_time) if publish_time else "",  # 转换为字符串
                        "crawled_at": str(datetime.now())  # 转换为字符串
                    }
                    
                    articles.append(new_article)
                    processed_urls.add(url)
                    new_articles_count += 1
                    
                    print(f"      ✅ 成功提取: {title[:50]}...")
                    
                    # 每5条保存一次检查点（只保存新增的文章）
                    if new_articles_count % 5 == 0:
                        # 只保存新增的文章，避免重复保存
                        new_articles = articles[len(existing_articles):]
                        if self.save_checkpoint(new_articles, db_path):
                            print(f"      💾 已保存检查点（共 {len(articles)} 条，新增 {new_articles_count} 条）")
                else:
                    print(f"      ⚠️ 无法提取内容")
            except KeyboardInterrupt:
                print(f"\n⚠️ 用户中断，保存当前进度...")
                new_articles = articles[len(existing_articles):]
                if self.save_checkpoint(new_articles, db_path):
                    print(f"💾 已保存 {len(articles)} 条数据到 {db_path}")
                    print(f"🔄 下次运行将从第 {len(articles) + 1} 条继续")
                raise
            except Exception as e:
                print(f"      ❌ 提取失败: {e}")
            
            # 避免请求过快（根据索引调整延迟，避免被封）
            # 每10条请求后增加延迟
            if idx % 10 == 0:
                time.sleep(2)  # 每10条休息2秒
            elif idx % 5 == 0:
                time.sleep(1)  # 每5条休息1秒
            else:
                time.sleep(0.8)  # 基础延迟0.8秒
        
        # 最终保存（只保存新增的文章）
        new_articles = articles[len(existing_articles):]
        if new_articles and self.save_checkpoint(new_articles, db_path):
            print(f"\n💾 最终保存: {len(articles)} 条数据（新增 {len(new_articles)} 条）")
        
        print(f"\n✅ 成功爬取 {len(articles)} 篇文章")
        
        # 从数据库读取所有数据返回DataFrame（包含 index_id）
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query('SELECT * FROM history_news ORDER BY publish_time DESC', conn)
        conn.close()
        
        return df

    def mine_recent_sitemap(self, site_name="CoinTelegraph", days_back=30):
        """
        快速挖掘最近 N 天的新闻（用于每日更新）
        """
        if site_name not in self.sites:
            print(f"❌ 未知站点: {site_name}")
            return pd.DataFrame()
        
        site_config = self.sites[site_name]
        main_sitemap = site_config["sitemap"]
        
        print(f"\n🔍 快速挖掘 {site_name} 最近 {days_back} 天的新闻")
        
        # 获取最近的月度 sitemap
        monthly_sitemaps = self.extract_monthly_sitemaps(main_sitemap)
        recent_sitemaps = monthly_sitemaps[:2]  # 最近2个月
        
        all_news_urls = []
        for sitemap_url in recent_sitemaps:
            urls = self.fetch_sitemap(sitemap_url)
            filtered = self.filter_news_urls(urls)
            all_news_urls.extend(filtered)
        
        print(f"📊 找到 {len(all_news_urls)} 条相关新闻链接")
        
        # 只爬取前50条（快速模式）
        articles = []
        
        for idx, url in enumerate(all_news_urls[:50], 1):
            print(f"   [{idx}/50] 爬取: {url[:60]}...")
            try:
                content = self.extract_article_content(url)
                if content:
                    title, publish_time = self.extract_article_metadata(url, content)
                    article_id = hashlib.md5(url.encode()).hexdigest()[:16]
                    summary = self.smart_truncate_summary(content, target_length=300)
                    
                    articles.append({
                        "id": article_id,
                        "url": url,
                        "title": title,
                        "content": content,
                        "summary": summary,
                        "source": site_name,
                        "publish_time": publish_time,
                        "crawled_at": datetime.now()
                    })
            except Exception as e:
                print(f"      ⚠️ 提取失败: {e}")
            
            time.sleep(0.8)  # 基础延迟
        
        return pd.DataFrame(articles)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='历史新闻挖掘工具')
    parser.add_argument('--mode', choices=['full', 'recent'], default='recent',
                       help='挖掘模式: full=完整历史, recent=最近30天')
    parser.add_argument('--months', type=int, default=12,
                       help='回溯月数（仅用于 full 模式）')
    parser.add_argument('--max', type=int, default=None,
                       help='最大文章数量（默认不限制）')
    
    args = parser.parse_args()
    
    miner = HistoryNewsMiner()
    
    if args.mode == 'full':
        print("🚀 冷启动模式：挖掘完整历史数据")
        # 统一使用同一个数据库文件，所有数据存在一个表里
        db_path = "history_news.db"
        df = miner.mine_history(
            site_name="CoinTelegraph",
            months_back=args.months,
            max_articles=args.max,  # None 表示不限制
            db_path=db_path
        )
    else:
        print("🚀 快速模式：挖掘最近30天数据")
        df = miner.mine_recent_sitemap(
            site_name="CoinTelegraph",
            days_back=30
        )
    
    if not df.empty:
        # 数据已经在数据库中保存了，这里只是确认
        print(f"\n✅ 数据挖掘完成！")
        print(f"📊 共 {len(df)} 条历史新闻")
        print(f"💾 数据已保存在数据库中")
        
        # 可选：导出为CSV备份
        csv_backup = f"history_news_backup_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(csv_backup, index=False, encoding='utf-8-sig')
        print(f"📄 CSV备份已保存到: {csv_backup}")
    else:
        print("⚠️ 未获取到数据")

