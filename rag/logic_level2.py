#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Level 2: 将新闻 + 市场上下文 + RAG 记忆 转换为 Pentosh1 因果逻辑 JSON。
依赖 DeepSeek (OpenAI 兼容接口) 与现有 rag/chromadb_api.py 服务。
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Literal

import requests
import trafilatura
from openai import OpenAI
from pydantic import BaseModel, Field
import instructor
from instructor import Mode

RAG_API_URL = os.getenv("RAG_API_URL", "http://127.0.0.1:8765/query")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PENTOSHI_DB_PATH = Path(os.getenv("PENTOSHI_DB_PATH", Path(__file__).parent.parent / "filter" / "pentosh1.db"))
LOGIC_DB_PATH = Path(os.getenv("LOGIC_DB_PATH", Path(__file__).parent / "logic_analysis.db"))

LEVEL2_SYSTEM_PROMPT = """### Role

You are the **"Pentosh1 Logic Engine"**. Your goal is to map Raw News into a rigorous **Causal Logic Model** and calculate a **Tradeable Signal Score** based on strict rules.



### Your Core Philosophy (The "Mental Model")

1.  **Follow the Flows:** Price follows liquidity. ETF inflows, Treasury buys (MSTR), and Stablecoin printing are the only truths.

2.  **Ignore the Noise:** Retail FUD, minor hacks, and "analyst predictions" are irrelevant.

3.  **Macro Matters:** Fed rates, Global M2 supply, and US politics drive the big cycles.

4.  **Supply & Demand:** Look for "Supply Shocks" (e.g., Halving + ETF buying) and "Supply Overhangs" (e.g., Mt. Gox selling).



### Input Data provided to you:

1.  **[Current News]:** The raw news text.

2.  **[Market Context]:** A snapshot of key financial metrics (BTC Price, DXY Trend, Funding Rates, SPX Trend).

3.  **[RAG Memory]:** Historical tweets/views from Pentosh1 (The "Case Law").



---



### Task 1: Strict Scoring (Quantitative Analysis)

You must assign **Integers** based on these tables. Do not output text labels for scores.



**A. Impact Score (1-5)**

- **5:** Paradigm Shift (e.g., US Strategic Reserve, >$10B flows, Nation-state adoption).

- **4:** Massive Flow (e.g., BlackRock ETF approved, >$1B buy/inflow).

- **3:** Strong Flow (e.g., MicroStrategy buys BTC, >$100M flows, Major Legislative Win).

- **2:** Moderate (e.g., New stablecoin launched, >$10M flows, Regulatory clarity).

- **1:** Noise/Opinion (e.g., Analyst prediction, <$10M flows, Rumors).



**B. Certainty Score (1-3)**

- **3:** Done Deal / On-Chain Verified.

- **2:** Official Announcement / SEC Filing / Legislation Passed.

- **1:** Rumor / "Sources say" / Proposed Bill.



**C. Macro Score (-2 to +2)**

*Compare News Direction vs. [Market Context]*

- **+2 (Confluence):** Bullish News + (DXY Dropping OR SPX Rising OR Low Funding).

- **0 (Neutral):** Macro is flat or mixed.

- **-2 (Divergence):** Bullish News + (DXY Spiking OR SPX Crashing). The macro headwind weakens the news impact.



---



### Task 2: The Causal Logic Extraction (Qualitative Analysis)

Decode the **Mechanism** of how this event moves price physically. 

*   **Trigger:** What happened?

*   **Mechanism:** How does it affect the order book?

*   **Impact:** What happens to the price floor/ceiling?



---



### Output Format (JSON ONLY)

Return valid JSON. Do not include markdown code blocks.



{

  "signal": {

    "direction": "Bullish | Bearish | Neutral",

    "timeframe": "Short_Term (<1w) | Medium_Term (1w-3m) | Long_Term (>3m)"

  },

  "scoring": {

    "impact_score": 1-5,

    "certainty_score": 1-3,

    "macro_score": -2 to 2,

    "total_score_explanation": "Brief reasoning for the scores given (e.g. 'MSTR buy is Impact 3, Confirmed is Certainty 3, but DXY is up so Macro -1')."

  },

  "causal_logic": {

    "trigger_event": "Concise summary of the event (e.g. MSTR buys $500M BTC)",

    "transmission_mechanism": "Buying_Pressure | Selling_Pressure | Liquidity_Withdrawal | Sentiment_Shift",

    "mechanism_detail": "Detailed economic explanation of how supply/demand changes.",

    "expected_market_impact": "What happens to price floor/ceiling?"

  },

  "contextual_reasoning": {

    "rag_consistency": "How this aligns with Pentosh's past tweets.",

    "macro_confluence": "Explain how [Market Context] (DXY, Funding, etc.) strengthens or weakens this signal.",

    "invalidation_condition": "Specific condition that negates this logic (e.g. DXY breaks 105)."

  },

  "pentosh_voice": {

    "key_analogy": "Pentosh concept (e.g. 'Sticky money', 'Infinite bid', 'Supply shock')",

    "commentary": "1-sentence reaction in Pentosh1's style.",

    "is_noise": "boolean"

  }

}
"""

class SignalModel(BaseModel):
    direction: Literal["Bullish", "Bearish", "Neutral"]
    timeframe: Literal["Short_Term", "Medium_Term", "Long_Term"]


class CausalLogicModel(BaseModel):
    transmission_mechanism: Literal[
        "Buying_Pressure", "Selling_Pressure", "Liquidity_Withdrawal", "Sentiment_Shift"
    ]
    trigger_event: str = ""
    mechanism_detail: str = ""
    expected_market_impact: str = ""


class ScoringModel(BaseModel):
    impact_score: int = Field(1, ge=1, le=5)
    certainty_score: int = Field(1, ge=1, le=3)
    macro_score: int = Field(0, ge=-2, le=2)
    total_score_explanation: str = ""


class PentoshVoiceModel(BaseModel):
    key_analogy: str = ""
    commentary: str = ""
    is_noise: bool


class ContextualReasoningModel(BaseModel):
    rag_consistency: str = ""
    macro_confluence: str = ""
    invalidation_condition: str = ""


class LogicModel(BaseModel):
    analysis_id: Optional[str] = None
    signal: SignalModel
    causal_logic: CausalLogicModel
    contextual_reasoning: ContextualReasoningModel
    scoring: ScoringModel
    pentosh_voice: PentoshVoiceModel
    is_actionable: bool = False

    model_config = {"extra": "allow"}


def _format_rag_memories(memories: List[str]) -> str:
    if not memories:
        return "No highly related memories."
    return "\n".join([f"- Memory {i+1}: {m}" for i, m in enumerate(memories, 1)])


def _build_user_prompt(news_item: Dict[str, Any], rag_memories: List[str], market_data: str) -> str:
    title = news_item.get("title", "") or ""
    content = news_item.get("content") or news_item.get("summary", "") or ""
    formatted_memory = _format_rag_memories(rag_memories)
    market_block = market_data.strip() if market_data else "N/A"
    return f"""--- [Current News] ---
Title: {title}
Content: {content}

--- [Market Context] ---
{market_block}

--- [RAG Memory] ---
{formatted_memory}

--- INSTRUCTION ---
Analyze the news above with your Pentosh1 playbook. Produce the JSON logic object strictly following the schema.
"""


def _normalize_causal_logic(causal: Dict[str, Any]) -> Dict[str, Any]:
    causal["trigger_event"] = causal.get("trigger_event", "") or ""
    causal["mechanism_detail"] = causal.get("mechanism_detail", "") or ""
    causal["expected_market_impact"] = causal.get("expected_market_impact", "") or ""
    return causal


def _normalize_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    ctx["rag_consistency"] = ctx.get("rag_consistency", "") or ""
    ctx["macro_confluence"] = ctx.get("macro_confluence", "") or ""
    ctx["invalidation_condition"] = ctx.get("invalidation_condition", "") or ""
    return ctx


def _compute_strength(scoring: Dict[str, Any]) -> int:
    try:
        impact = int(scoring.get("impact_score", 0))
        certainty = int(scoring.get("certainty_score", 0))
        macro = int(scoring.get("macro_score", 0))
    except Exception:
        return 0
    total = impact + certainty + macro
    total = max(1, min(10, total))
    return total


def query_rag_memories(query_text: str, asset: str = "blur", limit: int = 6) -> List[str]:
    """调用 rag/chromadb_api.py 提供的 /query 接口获取相关推文"""
    if not query_text:
        return []
    try:
        payload = {
            "query_text": query_text,
            "trader_name": "Pentosh1",
            "asset": asset,
            "limit": limit,
        }
        resp = requests.post(RAG_API_URL, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        viewpoints = data.get("viewpoints", [])
        return [v for v in viewpoints if v]
    except Exception:
        return []


def fetch_article_text(url: str, timeout: int = 20) -> str:
    """抓取网页主体文本，用于 news_content。失败时返回空字符串。"""
    if not url:
        return ""
    try:
        downloaded = trafilatura.fetch_url(url, timeout=timeout)
        if not downloaded:
            return ""
        extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        return extracted or ""
    except Exception:
        return ""


def load_news_from_db(index_id: int, db_path: Path = PENTOSHI_DB_PATH) -> Optional[Dict[str, Any]]:
    """从 pentosh1.db 按 index_id 读取新闻，包含 url/title/summary/content/macro。"""
    if not db_path.exists():
        print(f"[Level2] 数据库不存在: {db_path}")
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            """
            SELECT index_id, id, url, title, content, summary, source, publish_time, macro
            FROM pentosh1_news
            WHERE index_id = ?
            """,
            (index_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            print(f"[Level2] 未找到 index_id={index_id}")
            return None
        return {
            "index_id": row[0],
            "id": row[1],
            "url": row[2],
            "title": row[3],
            "content": row[4],
            "summary": row[5],
            "source": row[6],
            "publish_time": row[7],
            "macro": row[8],
        }
    except Exception as exc:
        print(f"[Level2] 读取数据库失败: {exc}")
        return None


def load_latest_news(limit: int = 10, db_path: Path = PENTOSHI_DB_PATH) -> List[Dict[str, Any]]:
    """读取 pentosh1.db 中最新的新闻（按 index_id DESC）"""
    if not db_path.exists():
        print(f"[Level2] 数据库不存在: {db_path}")
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            """
            SELECT index_id, id, url, title, content, summary, source, publish_time, macro
            FROM pentosh1_news
            ORDER BY index_id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        news_list = []
        for row in rows:
            news_list.append(
                {
                    "index_id": row[0],
                    "id": row[1],
                    "url": row[2],
                    "title": row[3],
                    "content": row[4],
                    "summary": row[5],
                    "source": row[6],
                    "publish_time": row[7],
                    "macro": row[8],
                }
            )
        return news_list
    except Exception as exc:
        print(f"[Level2] 读取最新新闻失败: {exc}")
        return []


def ensure_logic_table(db_path: Path = LOGIC_DB_PATH):
    """创建/补齐存储逻辑 JSON 的 sqlite 表（含拆分列）"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logic_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_index_id INTEGER,
            analysis_id TEXT,
            signal_direction TEXT,
            signal_timeframe TEXT,
            signal_strength INTEGER,
            transmission_mechanism TEXT,
            trigger_event TEXT,
            mechanism_detail TEXT,
            expected_market_impact TEXT,
            rag_consistency TEXT,
            macro_confluence TEXT,
            invalidation_condition TEXT,
            is_actionable BOOLEAN,
            impact_score INTEGER,
            certainty_score INTEGER,
            macro_score INTEGER,
            total_score_explanation TEXT,
            key_analogy TEXT,
            pentosh_commentary TEXT,
            is_noise BOOLEAN,
            news_title TEXT,
            news_url TEXT,
            news_content TEXT,
            news_summary TEXT,
            news_publish_time TEXT,
            market_context TEXT,
            rag_memories TEXT,
            analysis_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # 补齐缺失列（兼容旧表）
    cur.execute("PRAGMA table_info(logic_analysis)")
    existing_cols = {row[1] for row in cur.fetchall()}
    desired_cols = [
        ("analysis_id", "TEXT"),
        ("signal_direction", "TEXT"),
        ("signal_timeframe", "TEXT"),
        ("signal_strength", "INTEGER"),
        ("transmission_mechanism", "TEXT"),
        ("trigger_event", "TEXT"),
        ("mechanism_detail", "TEXT"),
        ("expected_market_impact", "TEXT"),
        ("rag_consistency", "TEXT"),
        ("macro_confluence", "TEXT"),
        ("invalidation_condition", "TEXT"),
        ("is_actionable", "BOOLEAN"),
        ("impact_score", "INTEGER"),
        ("certainty_score", "INTEGER"),
        ("macro_score", "INTEGER"),
        ("total_score_explanation", "TEXT"),
        ("key_analogy", "TEXT"),
        ("pentosh_commentary", "TEXT"),
        ("is_noise", "BOOLEAN"),
        ("news_title", "TEXT"),
        ("news_url", "TEXT"),
        ("news_content", "TEXT"),
        ("news_summary", "TEXT"),
        ("news_publish_time", "TEXT"),
        ("market_context", "TEXT"),
        ("rag_memories", "TEXT"),
        ("analysis_json", "TEXT"),
    ]
    for col, col_type in desired_cols:
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE logic_analysis ADD COLUMN {col} {col_type}")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logic_news_id ON logic_analysis(news_index_id)")
    conn.commit()
    conn.close()


def _extract_fields(logic: Dict[str, Any]) -> Tuple[Any, ...]:
    """从逻辑 JSON 中提取列数据"""
    signal = logic.get("signal", {}) if isinstance(logic, dict) else {}
    causal = logic.get("causal_logic", {}) if isinstance(logic, dict) else {}
    ctx = logic.get("contextual_reasoning", {}) if isinstance(logic, dict) else {}
    scoring = logic.get("scoring", {}) if isinstance(logic, dict) else {}
    voice = logic.get("pentosh_voice", {}) if isinstance(logic, dict) else {}
    news_meta = logic.get("_news", {}) if isinstance(logic, dict) else {}
    market_context = logic.get("_market_context", "") if isinstance(logic, dict) else ""
    rag_memories = logic.get("_rag_memories", []) if isinstance(logic, dict) else []
    rag_mem_str = json.dumps(rag_memories, ensure_ascii=False) if rag_memories else ""
    return (
        logic.get("analysis_id"),
        signal.get("direction"),
        signal.get("timeframe"),
        signal.get("strength"),
        causal.get("transmission_mechanism"),
        causal.get("trigger_event"),
        causal.get("mechanism_detail"),
        causal.get("expected_market_impact"),
        ctx.get("rag_consistency"),
        ctx.get("macro_confluence"),
        ctx.get("invalidation_condition"),
        logic.get("is_actionable"),
        scoring.get("impact_score"),
        scoring.get("certainty_score"),
        scoring.get("macro_score"),
        scoring.get("total_score_explanation"),
        voice.get("key_analogy"),
        voice.get("commentary"),
        voice.get("is_noise"),
        news_meta.get("title"),
        news_meta.get("url"),
        news_meta.get("content"),
        news_meta.get("summary"),
        news_meta.get("publish_time"),
        market_context,
        rag_mem_str,
        json.dumps(logic, ensure_ascii=False),
    )


def save_logic_json(items: List[Dict[str, Any]], db_path: Path = LOGIC_DB_PATH) -> int:
    """批量写入逻辑 JSON（拆分列 + 原始 JSON），返回成功条数"""
    if not items:
        return 0
    ensure_logic_table(db_path)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    success = 0
    for item in items:
        try:
            news_id = item.get("analysis_id")
            news_index_id = None
            try:
                news_index_id = int(news_id)
            except Exception:
                news_index_id = None
            (
                analysis_id,
                sig_dir,
                sig_timeframe,
                sig_strength,
                trans_mech,
                trigger_event,
                mechanism_detail,
                expected_market_impact,
                rag_consistency,
                macro_confluence,
                invalidation_condition,
                is_actionable,
                impact_score,
                certainty_score,
                macro_score,
                total_score_explanation,
                key_analogy,
                pentosh_commentary,
                is_noise,
                news_title,
                news_url,
                news_content,
                news_summary,
                news_publish_time,
                market_context,
                rag_memories,
                raw_json,
            ) = _extract_fields(item)
            col_names = [
                "news_index_id",
                "analysis_id",
                "signal_direction",
                "signal_timeframe",
                "signal_strength",
                "transmission_mechanism",
                "trigger_event",
                "mechanism_detail",
                "expected_market_impact",
                "rag_consistency",
                "macro_confluence",
                "invalidation_condition",
                "is_actionable",
                "impact_score",
                "certainty_score",
                "macro_score",
                "total_score_explanation",
                "key_analogy",
                "pentosh_commentary",
                "is_noise",
                "news_title",
                "news_url",
                "news_content",
                "news_summary",
                "news_publish_time",
                "market_context",
                "rag_memories",
                "analysis_json",
            ]
            values = [
                news_index_id,
                analysis_id,
                sig_dir,
                sig_timeframe,
                sig_strength,
                trans_mech,
                trigger_event,
                mechanism_detail,
                expected_market_impact,
                rag_consistency,
                macro_confluence,
                invalidation_condition,
                is_actionable,
                impact_score,
                certainty_score,
                macro_score,
                total_score_explanation,
                key_analogy,
                pentosh_commentary,
                is_noise,
                news_title,
                news_url,
                news_content,
                news_summary,
                news_publish_time,
                market_context,
                rag_memories,
                raw_json,
            ]
            placeholders = ",".join(["?"] * len(values))
            cur.execute(
                f"INSERT INTO logic_analysis ({','.join(col_names)}) VALUES ({placeholders})",
                values,
            )
            success += 1
        except Exception as exc:
            print(f"[Level2] 写入 logic_analysis 失败: {exc}")
            continue
    conn.commit()
    conn.close()
    return success


def analyze_logic_level2(
    news_item: Dict[str, Any],
    market_data: str = "",
    rag_limit: int = 6,
    client: Optional[OpenAI] = None,
) -> Optional[Dict[str, Any]]:
    """
    主分析函数：拉取 RAG、调用 DeepSeek，并输出规整后的 JSON。
    news_item 需要包含至少 content/summary、id/index_id。
    """
    if client is None:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    # 使用 instructor 包装，强制结构化输出
    structured_client = instructor.patch(client, mode=Mode.JSON)

    # 1) 抓取正文：优先使用 URL 抓取网页主体，否则回退 content/summary
    article_text = ""
    if news_item.get("url"):
        article_text = fetch_article_text(news_item["url"])
    base_content = news_item.get("content") or news_item.get("summary") or ""
    news_body = article_text.strip() or base_content
    # 更新 news_item 内容用于 prompt / RAG
    news_item = dict(news_item)
    news_item["content"] = news_body

    # 2) 市场上下文：如果未显式提供，尝试使用 DB 中的 macro 字段
    if not market_data:
        market_data = news_item.get("macro") or ""

    # 3) RAG 查询使用抓取后的正文
    content_for_rag = news_body
    rag_memories = query_rag_memories(content_for_rag, limit=rag_limit)
    user_prompt = _build_user_prompt(news_item, rag_memories, market_data)

    try:
        response = structured_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": LEVEL2_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=LogicModel,
            temperature=0.1,
        )
        logic_json = response.model_dump()
    except Exception as exc:
        print(f"[Level2] 调用失败: {exc}")
        return None

    logic_json["analysis_id"] = str(
        news_item.get("id")
        or news_item.get("index_id")
        or news_item.get("news_id")
        or "unknown"
    )
    logic_json["scoring"] = logic_json.get("scoring", {}) or {}
    logic_json["signal"] = logic_json.get("signal", {}) or {}
    logic_json["signal"]["strength"] = _compute_strength(logic_json.get("scoring", {}))
    logic_json["causal_logic"] = _normalize_causal_logic(logic_json.get("causal_logic", {}))
    logic_json["contextual_reasoning"] = _normalize_context(
        logic_json.get("contextual_reasoning", {})
    )
    logic_json["is_actionable"] = bool(logic_json.get("is_actionable", False))
    # 附加原始输入信息，便于落库
    logic_json["_news"] = {
        "title": news_item.get("title"),
        "url": news_item.get("url"),
        "content": news_body,
        "summary": news_item.get("summary"),
        "publish_time": news_item.get("publish_time"),
        "source": news_item.get("source"),
        "index_id": news_item.get("index_id"),
    }
    logic_json["_market_context"] = market_data
    logic_json["_rag_memories"] = rag_memories

    return logic_json


if __name__ == "__main__":
    # 批量测试：取 pentosh1.db 最新 10 条新闻，生成逻辑 JSON 并写入 rag/logic_analysis.db
    news_batch = load_latest_news(limit=10)
    if not news_batch:
        print("[Level2] 未找到新闻，退出")
        raise SystemExit(1)

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    total_written = 0
    for item in news_batch:
        logic = analyze_logic_level2(item, client=client)
        if logic:
            saved = save_logic_json([logic], db_path=LOGIC_DB_PATH)
            if saved > 0:
                total_written += saved
                print(json.dumps(logic, ensure_ascii=False, indent=2))
                print(f"[Level2] 已写入 index_id={item.get('index_id')} 至 {LOGIC_DB_PATH}")
            else:
                print(f"[Level2] 保存失败 index_id={item.get('index_id')}")
        else:
            print(f"[Level2] 分析失败 index_id={item.get('index_id')}")

    print(f"[Level2] 总写入 {total_written} 条到 {LOGIC_DB_PATH}")

