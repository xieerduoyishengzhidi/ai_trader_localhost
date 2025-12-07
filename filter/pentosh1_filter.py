#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pentosh1 新闻筛选模块
使用 DeepSeek API 对新闻进行大规模筛选，筛选出符合 Pentosh1 策略的新闻
"""

import json
import sqlite3
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI


# 配置
SOURCE_DB_PATH = Path(__file__).parent.parent / "news_service" / "history_news.db"
TARGET_DB_PATH = Path(__file__).parent.parent / "filter" / "pentosh1.db"
BATCH_SIZE =  50  # 每批处理的新闻数量
MAX_RETRIES = 3  # API 调用最大重试次数
RETRY_DELAY = 2  # 重试延迟（秒）

# DeepSeek API 配置（从环境变量读取）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# System Prompt
SYSTEM_PROMPT = """### Role

You are the "Pentosh1 News Filter", a specialized crypto macro trading assistant. Your objective is to filter a batch of news items and identify ONLY those that align with Pentosh1's "Quantamental" trading strategy (S1 Trend Following & S3 Event Driven). 

**Your mindset: You are looking for structural shifts, institutional liquidity, and regulatory clarity. You ignore noise, retail speculation, and short-term price action.**

### 🛑 SIGNIFICANCE THRESHOLDS (CRITICAL PRE-FILTER)

**Before applying the specific criteria below, apply these GLOBAL THRESHOLDS. If a news item does not meet these, DISCARD IT immediately:**

1. **Geographic Relevance:** Focus ONLY on Tier 1 jurisdictions: **USA, China, EU, Japan**. (Ignore news from minor countries like Poland, El Salvador, etc., unless they adopt BTC as legal tender).
2. **Monetary Threshold:** Flows, raises, or acquisitions must be **>$100M**. (e.g., "MicroStrategy buys $1B BTC" is KEEP. "Startup raises $17M" is IGNORE).
3. **Entity Status:** Focus on Market Movers (BlackRock, Vanguard, Tesla, Coinbase, Binance, US Gov). Ignore minor hiring news (e.g., "Company X hires new CIO") or small partnerships.
4. **Impact:** Ask yourself: "Does this have the potential to move BTC/ETH price by 1-2% or shift the global narrative?" If No, Discard.

---

### Pentosh1's Selection Criteria (The "Keep" List)

Select a news item IF it meets the thresholds above AND falls into these categories:

1. **Institutional Flows & "Sticky Money":**
   - **ETF Activity:** Significant inflows/outflows (BlackRock IBIT, Fidelity FBTC, ETH ETFs), new filings from majors, or options approval.
   - **Corporate Treasuries:** MicroStrategy (MSTR), Metaplanet, Semler Scientific buying BTC/ETH (Must be substantial).
   - **TradFi Integration:** Major banks/fintechs (PayPal, Stripe, Visa, Mastercard, Robinhood) launching crypto products or stablecoins.

2. **Regulation, Legal & Political Shifts (CRITICAL):**
   - **Legislative Wins:** Passage of major bills like FIT21, SAB 121 repeal, or "Genius Act".
   - **Executive Action:** US Presidential stance (Trump/Admin), Strategic Bitcoin Reserve (SBR) announcements.
   - **SEC/CFTC/DOJ:** Lawsuit dismissals/Settlements with MAJOR players (e.g., Ripple, Coinbase, Binance), or ending investigations (e.g., ETH 2.0 probe dropped). **Discard routine license approvals in minor jurisdictions.**
   - **Global Adoption:** Major Nation-state adoption or legalization (e.g., Russia mining, UK crypto hub).

3. **Global Macro & Liquidity (The "Tide"):**
   - **Fed Policy:** Rate cuts/hikes, QE (Quantitative Easing), ending QT, Balance Sheet expansion.
   - **Global Liquidity:** China stimulus, ECB/BOJ rate changes, M2 Money Supply expansion.
   - **Treasury/Bond Yields:** Significant moves in US10Y or DXY that impact risk assets.

4. **Supply & Demand Mechanics:**
   - **Supply Shock:** Halving events, massive token burns (e.g., $PUMP, $BEAM), or aggressive buyback programs.
   - **Supply Overhang:** Mt. Gox distributions, Government seizures selling (e.g., Silk Road BTC > 10k BTC), or massive VC unlocks.
   - **Exchange Data:** Exchange balances hitting multi-year lows (Supply Crunch).

5. **High-Conviction Narratives:**
   - **RWA/Tokenization:** BlackRock BUIDL, Franklin Templeton, or Treasury tokenization news.
   - **Stablecoin Expansion:** Market cap hitting ATHs, new yield-bearing stablecoins from major issuers.
   - **Infrastructure:** Major mainnet launches or upgrades that solve scalability (e.g., Firedancer, ETH Pectra) - *Only if major*.

### Exclusion Criteria (The "Ignore" List - AGGRESSIVE FILTERING)

**Discard the news IMMEDIATELY if it matches any of the following:**

1. **Generic Price Analysis:** "Analyst predicts BTC to 100k", "RSI signals oversold", "Golden Cross forming". (We trade flows, not lines).

2. **Low-Impact Partnerships:** "Coin X partners with unknown Company Y", "Project Z integrates with Wallet A". (Unless it involves a Fortune 500 company).

3. **Retail Noise & Shills:** "Top 5 coins to buy now", "Why Doge might flip SHIB", "Influencer X is bullish on Y".

4. **Minor Security Incidents:** Small DeFi hacks (<$50M), phishing attacks on individuals, or discord hacks.

5. **NFT/Metaverse Fluff:** New collection mints, floor price updates, or "gaming partnerships" without tokenomic implications.

6. **Tutorials & Guides:** "How to stake SOL", "What is a wallet", "Guide to airdrops".

7. **Vague Rumors:** "Insiders say...", "Rumors circulate..." (Unless the source is Tier 1 like Bloomberg/Reuters/WSJ).

8. **Ecosystem Updates:** Minor protocol upgrades, governance proposals (unless it changes tokenomics/fee switch), or testnet launches.

9. **Opinion Pieces:** Editorials, "Why crypto is dead", "Why crypto is the future" (Pure opinion without news).

10. **Old News:** Recycled headlines about events that happened days/weeks ago.

11. **Regional/Minor Compliance:** "Exchange X gets license in Singapore/Dubai/Poland". (This is routine business, not a macro driver).

12. **Corporate Fluff:** Hiring news (CIO/CEO changes), small acquisitions, or minor VC raises (<$50M).

### Input Format

A list of items: `ID | Date | Content`

### Output Format

Return ONLY a JSON object containing a list of the selected IDs. Do not output any explanation.

Example:
{"selected_ids": [101, 104, 108]}"""


def init_pentosh1_database(db_path: Path):
    """初始化 Pentosh1 数据库表结构"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 创建表结构（与 history_news 类似，但添加筛选时间戳）
    # source_index_id 作为外键，引用源数据库 history_news 表的 index_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pentosh1_news (
            index_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_index_id INTEGER NOT NULL UNIQUE,
            id TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            content TEXT,
            summary TEXT,
            source TEXT,
            publish_time TEXT,
            crawled_at TEXT,
            filtered_at TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_index_id ON pentosh1_news(source_index_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_id ON pentosh1_news(id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON pentosh1_news(url)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_publish_time ON pentosh1_news(publish_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON pentosh1_news(source)')
    
    conn.commit()
    conn.close()


def load_news_batch(db_path: Path, offset: int, limit: int) -> List[Dict[str, Any]]:
    """从源数据库加载一批新闻"""
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT index_id, id, url, title, content, summary, source, publish_time, crawled_at
        FROM history_news
        WHERE content IS NOT NULL AND content != ''
        ORDER BY index_id ASC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    news_list = []
    for row in rows:
        news_list.append({
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
    
    return news_list


def check_already_filtered(db_path: Path, index_id: int) -> bool:
    """检查新闻是否已经被筛选过"""
    if not db_path.exists():
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM pentosh1_news WHERE source_index_id = ?', (index_id,))
    exists = cursor.fetchone() is not None
    
    conn.close()
    return exists


def filter_news_with_deepseek(news_batch: List[Dict[str, Any]], client: OpenAI) -> List[int]:
    """使用 DeepSeek API 筛选新闻批次
    
    Args:
        news_batch: 新闻列表，每个元素包含 id, content 等字段
        client: DeepSeek OpenAI 客户端
    
    Returns:
        被选中的新闻 index_id 列表
    """
    if not news_batch:
        return []
    
    # 构造 User Prompt
    news_text_block = "\n".join([
        f"ID: {item['index_id']} | Date: {item.get('publish_time', 'N/A')} | Content: {item.get('content', item.get('summary', ''))[:500]}"
        for item in news_batch
    ])
    
    user_prompt = f"""
Here is the batch of news to filter. 
Select only the ones that match the Pentosh1 Macro/Flow strategy.

--- NEWS BATCH START ---
{news_text_block}
--- NEWS BATCH END ---
"""
    
    # 发送请求（带重试）
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            # 解析结果
            result = json.loads(response.choices[0].message.content)
            selected_ids = result.get('selected_ids', [])
            
            # 验证返回的 ID 是否在批次中
            batch_index_ids = {item['index_id'] for item in news_batch}
            valid_selected_ids = [idx for idx in selected_ids if idx in batch_index_ids]
            
            return valid_selected_ids
            
        except json.JSONDecodeError as e:
            print(f"      ⚠️  JSON 解析失败: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return []
        except Exception as e:
            print(f"      ⚠️  API 调用失败: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return []
    
    return []


def save_filtered_news(target_db_path: Path, news_items: List[Dict[str, Any]]):
    """保存筛选后的新闻到目标数据库"""
    if not news_items:
        return
    
    conn = sqlite3.connect(str(target_db_path))
    cursor = conn.cursor()
    
    filtered_at = datetime.now().isoformat()
    
    for item in news_items:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO pentosh1_news 
                (source_index_id, id, url, title, content, summary, source, publish_time, crawled_at, filtered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['index_id'],
                item['id'],
                item['url'],
                item['title'],
                item['content'],
                item['summary'],
                item['source'],
                item['publish_time'],
                item['crawled_at'],
                filtered_at
            ))
        except sqlite3.IntegrityError:
            # 忽略重复记录
            pass
    
    conn.commit()
    conn.close()


def get_total_news_count(db_path: Path) -> int:
    """获取源数据库中的新闻总数"""
    if not db_path.exists():
        return 0
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM history_news
        WHERE content IS NOT NULL AND content != ''
    ''')
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def get_already_filtered_count(target_db_path: Path) -> int:
    """获取已经筛选过的新闻数量"""
    if not target_db_path.exists():
        return 0
    
    conn = sqlite3.connect(str(target_db_path))
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM pentosh1_news')
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def main():
    """主函数"""
    print("=" * 80)
    print("🔍 Pentosh1 新闻筛选系统")
    print("=" * 80)
    print()
    
    # 1. 检查 API Key
    if not DEEPSEEK_API_KEY:
        print("❌ 未设置 DEEPSEEK_API_KEY 环境变量")
        print("   请设置: $env:DEEPSEEK_API_KEY='your_api_key'")
        return 1
    
    # 2. 检查源数据库
    if not SOURCE_DB_PATH.exists():
        print(f"❌ 源数据库不存在: {SOURCE_DB_PATH}")
        return 1
    
    print(f"✅ 源数据库: {SOURCE_DB_PATH}")
    
    # 3. 初始化目标数据库
    print(f"📂 目标数据库: {TARGET_DB_PATH}")
    init_pentosh1_database(TARGET_DB_PATH)
    print("✅ 目标数据库已初始化")
    print()
    
    # 4. 初始化 DeepSeek 客户端
    print("🤖 初始化 DeepSeek API 客户端...")
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )
    print(f"   模型: {DEEPSEEK_MODEL}")
    print(f"   批次大小: {BATCH_SIZE}")
    print()
    
    # 5. 统计信息
    total_count = get_total_news_count(SOURCE_DB_PATH)
    already_filtered = get_already_filtered_count(TARGET_DB_PATH)
    
    print("📊 统计信息:")
    print(f"   源数据库总新闻数: {total_count:,}")
    print(f"   已筛选新闻数: {already_filtered:,}")
    print(f"   待筛选新闻数: {total_count - already_filtered:,}")
    print()
    
    if total_count == 0:
        print("❌ 源数据库中没有新闻")
        return 1
    
    # 6. 开始批量筛选
    print("=" * 80)
    print("🚀 开始批量筛选...")
    print("=" * 80)
    print()
    
    offset = 0
    batch_num = 0
    total_selected = 0
    total_processed = 0
    
    start_time = time.time()
    
    while True:
        # 加载一批新闻
        news_batch = load_news_batch(SOURCE_DB_PATH, offset, BATCH_SIZE)
        
        if not news_batch:
            break
        
        # 过滤掉已经筛选过的新闻
        news_to_filter = [
            item for item in news_batch
            if not check_already_filtered(TARGET_DB_PATH, item['index_id'])
        ]
        
        if not news_to_filter:
            offset += BATCH_SIZE
            continue
        
        batch_num += 1
        print(f"📦 批次 #{batch_num}: 处理 {len(news_to_filter)} 条新闻 (索引 {offset} - {offset + len(news_batch) - 1})")
        
        # 调用 DeepSeek API 筛选
        selected_ids = filter_news_with_deepseek(news_to_filter, client)
        
        # 保存筛选结果
        selected_news = [item for item in news_to_filter if item['index_id'] in selected_ids]
        if selected_news:
            save_filtered_news(TARGET_DB_PATH, selected_news)
            total_selected += len(selected_news)
            print(f"   ✅ 选中 {len(selected_news)} 条新闻")
        else:
            print(f"   ⏭️  未选中任何新闻")
        
        total_processed += len(news_to_filter)
        offset += BATCH_SIZE
        
        # 显示进度
        progress = (total_processed / total_count) * 100 if total_count > 0 else 0
        print(f"   进度: {total_processed:,}/{total_count:,} ({progress:.1f}%) | 已选中: {total_selected:,}")
        print()
        
        # 避免 API 限流，添加延迟
        time.sleep(1)
    
    elapsed_time = time.time() - start_time
    
    # 7. 最终统计
    print("=" * 80)
    print("✅ 筛选完成！")
    print("=" * 80)
    print()
    print("📊 最终统计:")
    print(f"   处理批次: {batch_num}")
    print(f"   处理新闻数: {total_processed:,}")
    print(f"   选中新闻数: {total_selected:,}")
    print(f"   筛选率: {(total_selected/total_processed*100):.2f}%" if total_processed > 0 else "0%")
    print(f"   耗时: {elapsed_time:.1f} 秒")
    print(f"   平均速度: {total_processed/elapsed_time:.1f} 条/秒" if elapsed_time > 0 else "N/A")
    print()
    print(f"📂 结果已保存到: {TARGET_DB_PATH}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

