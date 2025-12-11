import json
import sqlite3
from pathlib import Path

JSONL_PATH = Path("rag/manual_logic.jsonl")
DB_PATH = Path("rag/logic_analysis.db")

def main():
    if not JSONL_PATH.exists():
        print(f"JSONL not found: {JSONL_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    sql = "INSERT INTO logic_analysis (news_index_id, analysis_json) VALUES (?, ?)"
    added = 0
    with JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            idx = obj.get("_news", {}).get("index_id")
            cur.execute(sql, (idx, json.dumps(obj, ensure_ascii=False)))
            added += 1
    conn.commit()
    conn.close()
    print(f"inserted {added}")

if __name__ == "__main__":
    main()

