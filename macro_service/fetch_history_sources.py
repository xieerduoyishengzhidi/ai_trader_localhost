#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速拉取过去一年的关键历史数据并写入 history.sqlite3（daily_context）：
- 稳定币总市值：DeFi Llama (stablecoincharts/all)
- 币安合约资金费率：fapi/v1/fundingRate（支持分页）
- FRED 宏观序列：WALCL / WTREGEN / RRPONTSYD
- 恐慌贪婪指数：alternative.me/fng

输出：layer1/2/3/4 payload，用于 backfill_macro 回填。
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Tuple, Callable, Optional

import requests

BASE_FRED = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = None  # 可选：填入 FRED API KEY，提高稳定性
HISTORY_DB = Path(__file__).resolve().parent / "history" / "history.sqlite3"


def fetch_stablecoins_history() -> List[Dict[str, Any]]:
    """拉取 DeFi Llama 稳定币历史全量，再截取近一年。"""
    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    one_year_ago = datetime.utcnow().date() - timedelta(days=365)
    filtered = []
    for point in data:
        ts = point.get("date")
        if ts is None:
            continue
        dt = datetime.utcfromtimestamp(int(ts)).date()
        if dt < one_year_ago:
            continue
        usd = point.get("totalCirculatingUSD", {}).get("peggedUSD")
        if usd is None:
            continue
        filtered.append({"date": dt.isoformat(), "stablecoin_usd": float(usd)})
    return filtered


def fetch_binance_funding(symbol: str = "BTCUSDT", days: int = 365) -> List[Dict[str, Any]]:
    """分页拉取币安合约资金费率历史，取每天最后一条记录。"""
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    start_ts = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
    end_ts = int(datetime.utcnow().timestamp() * 1000)
    results = []
    cursor = start_ts
    while cursor < end_ts:
        params = {"symbol": symbol, "startTime": cursor, "endTime": end_ts, "limit": 1000}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        arr = resp.json()
        if not arr:
            break
        for item in arr:
            ts = int(item["fundingTime"])
            dt = datetime.utcfromtimestamp(ts / 1000)
            results.append(
                {
                    "datetime": dt.isoformat(),
                    "date": dt.date().isoformat(),
                    "funding_rate": float(item["fundingRate"]),
                }
            )
        cursor = int(arr[-1]["fundingTime"]) + 1
        time.sleep(0.35)  # 简单限速
    # 取每日最后一条
    daily = {}
    for r in results:
        daily[r["date"]] = r
    return list(daily.values())


def fetch_fred_series(series_id: str, start: str, end: str) -> List[Dict[str, Any]]:
    """获取 FRED 序列；返回 date-value 列表。"""
    params = {
        "series_id": series_id,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
    }
    if FRED_API_KEY:
        params["api_key"] = FRED_API_KEY
    resp = requests.get(BASE_FRED, params=params, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    out = []
    for obs in body.get("observations", []):
        date_txt = obs.get("date")
        val_txt = obs.get("value")
        if val_txt in (None, ".", ""):
            continue
        try:
            out.append({"date": date_txt, "value": float(val_txt)})
        except Exception:
            continue
    return out


def fetch_fg_history(limit: int = 500) -> List[Dict[str, Any]]:
    """恐慌贪婪指数历史（alternative.me）。"""
    url = f"https://api.alternative.me/fng/?limit={limit}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        rows = []
        for item in data:
            ts = item.get("timestamp")
            val = item.get("value")
            if ts is None or val is None:
                continue
            try:
                dt = datetime.utcfromtimestamp(int(ts)).date()
                rows.append({"date": dt.isoformat(), "fg_index": int(val)})
            except Exception:
                continue
        return rows
    except Exception:
        return []


def _list_to_map(
    rows: List[Dict[str, Any]],
    value_key: str,
    transform: Optional[Callable[[Any], Optional[float]]] = None,
) -> Dict[date, float]:
    """将 [{date, value_key}] 转为 {date_obj: value}，可选转换。"""
    out: Dict[date, float] = {}
    for row in rows:
        d_txt = row.get("date")
        val = row.get(value_key)
        if d_txt is None or val is None:
            continue
        try:
            dt = datetime.fromisoformat(str(d_txt)).date()
        except Exception:
            continue
        try:
            parsed_val = transform(val) if transform else float(val)
        except Exception:
            continue
        out[dt] = parsed_val
    return out


def _value_on_or_before(series_map: Dict[date, float], target: date) -> Optional[float]:
    """按日期回溯取最近值。"""
    value = None
    for dt in sorted(series_map.keys()):
        if dt <= target:
            value = series_map[dt]
        else:
            break
    return value


def _pct_change(series_map: Dict[date, float], target: date, days: int) -> Optional[float]:
    current = _value_on_or_before(series_map, target)
    past = _value_on_or_before(series_map, target - timedelta(days=days))
    if current is None or past in (None, 0):
        return None
    return round((current - past) / past * 100, 2)


def _ensure_db() -> sqlite3.Connection:
    HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(HISTORY_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_context (
            date TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def _build_payload(
    date_cursor: date,
    walcl_map: Dict[date, float],
    tga_map: Dict[date, float],
    rrp_map: Dict[date, float],
    stable_map: Dict[date, float],
    funding_map: Dict[date, float],
    fg_map: Dict[date, float],
) -> Dict[str, Any]:
    walcl_val = _value_on_or_before(walcl_map, date_cursor)
    tga_val = _value_on_or_before(tga_map, date_cursor)
    rrp_val = _value_on_or_before(rrp_map, date_cursor)

    liquidity_today = None
    liquidity_prev = None
    if walcl_val is not None and tga_val is not None and rrp_val is not None:
        liquidity_today = walcl_val - tga_val - (rrp_val * 1000)
        prev_date = date_cursor - timedelta(days=30)
        walcl_prev = _value_on_or_before(walcl_map, prev_date)
        tga_prev = _value_on_or_before(tga_map, prev_date)
        rrp_prev = _value_on_or_before(rrp_map, prev_date)
        if walcl_prev is not None and tga_prev is not None and rrp_prev is not None:
            liquidity_prev = walcl_prev - tga_prev - (rrp_prev * 1000)

    stable_today = _value_on_or_before(stable_map, date_cursor)
    stable_growth_30d = _pct_change(stable_map, date_cursor, 30)

    funding_annualized = _value_on_or_before(funding_map, date_cursor)
    fg_index = _value_on_or_before(fg_map, date_cursor)

    payload = {
        "date": date_cursor.isoformat(),
        "layer1": {
            "walcl": walcl_val,
            "tga": tga_val,
            "rrp": rrp_val,
            "liquidity_billions": round(liquidity_today / 1000, 2) if liquidity_today is not None else None,
            "liquidity_change_30d_b": round((liquidity_today - liquidity_prev) / 1000, 2)
            if liquidity_today is not None and liquidity_prev is not None
            else None,
        },
        "layer2": {
            "stablecoin_mcap_b": stable_today,
            "stablecoin_growth_30d_pct": stable_growth_30d,
            "_fill": "fetch_history_sources",
        },
        "layer3": {
            "_fill": "fetch_history_sources",
        },
        "layer4": {
            "funding_rate_annualized_pct": funding_annualized,
            "fear_greed_index": fg_index,
            "_fill": "fetch_history_sources",
        },
    }

    # 清理空字段
    payload["layer1"] = {k: v for k, v in payload["layer1"].items() if v is not None}
    for layer in ("layer2", "layer3", "layer4"):
        payload[layer] = {k: v for k, v in payload[layer].items() if v is not None}

    return payload


def _summary(name: str, rows: List[Dict[str, Any]]):
    if not rows:
        print(f"[{name}] 空数据")
        return
    rows_sorted = sorted(rows, key=lambda x: x["date"])
    print(f"[{name}] 共 {len(rows_sorted)} 条 | 起止: {rows_sorted[0]['date']} -> {rows_sorted[-1]['date']}")
    print("  示例前2:", rows_sorted[:2])
    print("  示例后2:", rows_sorted[-2:])


def main():
    start_date = datetime.utcnow().date() - timedelta(days=365)
    end_date = datetime.utcnow().date()
    start = start_date.isoformat()
    end = end_date.isoformat()

    # 1) 稳定币历史
    stable = fetch_stablecoins_history()
    _summary("stablecoins_llama", stable)

    # 2) 币安资金费率
    funding = fetch_binance_funding(symbol="BTCUSDT", days=365)
    _summary("binance_funding_BTCUSDT", funding)
    fg_rows = fetch_fg_history(limit=500)
    _summary("fear_greed", fg_rows)

    # 3) FRED 序列
    walcl_rows = fetch_fred_series("WALCL", start, end)
    tga_rows = fetch_fred_series("WTREGEN", start, end)
    rrp_rows = fetch_fred_series("RRPONTSYD", start, end)
    _summary("fred_WALCL", walcl_rows)
    _summary("fred_WTREGEN", tga_rows)
    _summary("fred_RRPONTSYD", rrp_rows)

    # --- 将数据写入 history.sqlite3 ---
    walcl_map = _list_to_map(walcl_rows, "value")
    tga_map = _list_to_map(tga_rows, "value")
    rrp_map = _list_to_map(rrp_rows, "value")
    stable_map = _list_to_map(stable, "stablecoin_usd", lambda v: float(v) / 1e9)  # 转为 Billions
    funding_map = _list_to_map(
        funding, "funding_rate", lambda v: float(v) * 3 * 365 * 100  # 8 小时一次，年化百分比
    )
    fg_map = _list_to_map(fg_rows, "fg_index")

    all_dates = sorted(
        {
            *walcl_map.keys(),
            *tga_map.keys(),
            *rrp_map.keys(),
            *stable_map.keys(),
            *funding_map.keys(),
            *fg_map.keys(),
        }
    )
    conn = _ensure_db()
    conn.execute("DELETE FROM daily_context WHERE date BETWEEN ? AND ?", (start_date.isoformat(), end_date.isoformat()))

    inserted = 0
    for current in all_dates:
        if current < start_date or current > end_date:
            continue
        payload = _build_payload(current, walcl_map, tga_map, rrp_map, stable_map, funding_map, fg_map)
        conn.execute(
            "INSERT OR REPLACE INTO daily_context (date, payload, created_at) VALUES (?, ?, ?)",
            (current.isoformat(), json.dumps(payload, ensure_ascii=False), datetime.utcnow().isoformat()),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"[history.sqlite3] 已写入 {inserted} 条记录 -> {HISTORY_DB}")


if __name__ == "__main__":
    main()

