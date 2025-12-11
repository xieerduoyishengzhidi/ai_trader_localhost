#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出 rag/logic_analysis.db 的 logic_analysis 表到 CSV。
默认输出到 rag/logic_analysis_export.csv，编码 utf-8-sig。
"""

import sqlite3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "logic_analysis.db"
OUT_PATH = ROOT / "logic_analysis_export.csv"


def export():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"数据库不存在: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(logic_analysis)")
    cols = [row[1] for row in cur.fetchall()]

    cur.execute("SELECT * FROM logic_analysis ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    with OUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"written {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    export()

