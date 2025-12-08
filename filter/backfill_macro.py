#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
给 pentosh1.db 的 pentosh1_news 增加 macro 字段，并用宏观历史库填充。

数据来源：
- filter/pentosh1.db    : 目标库（新闻）
- macro_service/history/history.sqlite3 : 提供 daily_context.payload（含 layer1/2/3/4 历史）

填充规则：
- 以新闻 publish_time 的日期（UTC，取 YYYY-MM-DD 部分）匹配 daily_context.date。
- 若当日无记录，向前寻找最近日期。
- 仅在当前记录 macro 为空时更新。

使用：
    python backfill_macro.py
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET_DB = ROOT / "pentosh1.db"
HISTORY_DB = ROOT.parent / "macro_service" / "history" / "history.sqlite3"


def ensure_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(pentosh1_news)")
    cols = [c[1] for c in cur.fetchall()]
    if "macro" not in cols:
        cur.execute("ALTER TABLE pentosh1_news ADD COLUMN macro TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_macro ON pentosh1_news(macro)")
        conn.commit()


def load_history():
    if not HISTORY_DB.exists():
        raise FileNotFoundError(f"历史库不存在: {HISTORY_DB}")
    hconn = sqlite3.connect(str(HISTORY_DB))
    hcur = hconn.cursor()
    hcur.execute("SELECT date, payload FROM daily_context ORDER BY date ASC")
    rows = hcur.fetchall()
    hconn.close()
    history = [(datetime.strptime(d, "%Y-%m-%d").date(), p) for d, p in rows]
    return history


def find_payload(history, target_date):
    # 返回 <= target_date 的最近一条 payload
    payload = None
    for d, p in history:
        if d <= target_date:
            payload = p
        else:
            break
    return payload


def backfill():
    if not TARGET_DB.exists():
        raise FileNotFoundError(f"目标库不存在: {TARGET_DB}")

    history = load_history()
    if not history:
        raise RuntimeError("历史库无数据")

    conn = sqlite3.connect(str(TARGET_DB))
    ensure_column(conn)
    cur = conn.cursor()

    cur.execute("SELECT index_id, publish_time, macro FROM pentosh1_news")
    rows = cur.fetchall()

    updated = 0
    for idx, pub_time, macro in rows:
        if macro:
            continue
        if not pub_time:
            continue
        try:
            dt = datetime.fromisoformat(pub_time)
        except Exception:
            # 如果格式异常，跳过
            continue
        payload = find_payload(history, dt.date())
        if payload:
            cur.execute(
                "UPDATE pentosh1_news SET macro = ? WHERE index_id = ?",
                (payload, idx),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"done, updated {updated} rows")


if __name__ == "__main__":
    backfill()

