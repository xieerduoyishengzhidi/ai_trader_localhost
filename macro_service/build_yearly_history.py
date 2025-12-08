"""
Build a local SQLite store containing the past year's macro + sentiment frames.

数据来源：
- Macro Service 的 /api/fred/series 和 /api/yfinance/quote 端点（统一走 localhost:8001）
- 单次调用覆盖整个时间段，避免频繁请求导致被封

输出：
- macro_service/history/history.sqlite3 里的 daily_context 表
- 每条记录包含一整天的 layer1 + layer4 映射

用法：`python build_yearly_history.py`
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd

BASE_URL = "http://localhost:8001"
DB_PATH = Path(__file__).resolve().parent / "history" / "history.sqlite3"
START_DAYS_DELTA = 400  # 先多取一些，方便计算趋势线
SNAPSHOT_SYMBOL = "BTC/USDT"

def _ensure_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

def _fetch_fred_series(session: requests.Session, series_id: str, start: str, end: str) -> List[Tuple[date, Optional[float]]]:
    payload = {"series_id": series_id, "start_date": start, "end_date": end}
    resp = session.post(f"{BASE_URL}/api/fred/series", json=payload, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    points = body.get("data", [])
    data_list = []
    for point in points:
        try:
            dt = datetime.strptime(point["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        data_list.append((dt, point.get("value")))
    data_list.sort(key=lambda x: x[0])
    time.sleep(0.6)
    return data_list

def _fetch_yfinance(session: requests.Session, symbol: str, period: str = "1y", interval: str = "1d") -> List[Tuple[date, Optional[float]]]:
    payload = {"symbol": symbol, "period": period, "interval": interval}
    resp = session.post(f"{BASE_URL}/api/yfinance/quote", json=payload, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    points = body.get("data", [])
    data_list = []
    for point in points:
        date_txt = point.get("date")
        if not date_txt:
            continue
        try:
            dt = datetime.strptime(date_txt.split(" ")[0], "%Y-%m-%d").date()
        except Exception:
            continue
        data_list.append((dt, point.get("close")))
    data_list.sort(key=lambda x: x[0])
    time.sleep(0.6)
    return data_list


def _fetch_crypto_snapshot(session: requests.Session, symbol: str) -> Dict:
    """
    获取一次完整的币圈快照，用于前向填充历史记录，避免大量调用。
    """
    try:
        resp = session.post(f"{BASE_URL}/api/crypto/all", json={"symbol": symbol}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        data["_snapshot_asof"] = datetime.utcnow().isoformat()
        time.sleep(0.6)
        return data
    except Exception as exc:
        print(f"⚠️ 获取 crypto 快照失败: {exc}")
        return {"layer2_flows": {}, "layer3_structure": {}, "layer4_sentiment": {}, "_snapshot_asof": None}


def _ffill(value, fallback):
    return value if value is not None else fallback


def _fetch_farside_etf_history() -> Dict[date, Dict[str, float]]:
    """
    读取 Farside ETF 历史表格（单次请求），返回按日期的净流入。
    """
    url = "https://farside.co.uk/btc/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(resp.text)
        if not tables:
            return {}
        df = tables[0]
        history = {}
        for _, row in df.iterrows():
            dt_raw = row.get("Date")
            if pd.isna(dt_raw):
                continue
            try:
                dt = pd.to_datetime(dt_raw).date()
            except Exception:
                continue
            total = row.get("Total")
            ibit = row.get("IBIT")
            def _parse(x):
                if pd.isna(x):
                    return None
                if isinstance(x, (int, float)):
                    return float(x)
                txt = str(x).replace(",", "").strip()
                mul = 1.0
                if txt.endswith("M"):
                    txt = txt[:-1]
                elif txt.endswith("B"):
                    txt = txt[:-1]
                    mul = 1000.0
                try:
                    return float(txt) * mul
                except Exception:
                    return None
            history[dt] = {
                "etf_net_inflow_m": _parse(total),
                "etf_ibit_flow_m": _parse(ibit)
            }
        return history
    except Exception as exc:
        print(f"⚠️ 获取 ETF 历史失败: {exc}")
        return {}


def _fetch_stablecoin_history() -> Dict[date, float]:
    """
    DeFi Llama 稳定币总市值历史（接口可能调整，失败则返回空）
    """
    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        history = {}
        for point in data:
            ts = point.get("date")
            if ts is None:
                continue
            dt = datetime.utcfromtimestamp(ts).date()
            val = point.get("totalCirculatingUSD")
            if val is not None:
                history[dt] = float(val) / 1e9  # 转为 Billions
        return history
    except Exception as exc:
        print(f"⚠️ 获取稳定币历史失败: {exc}")
        return {}


def _fetch_cg_market_caps(coin_id: str, days: int = 400) -> Dict[date, float]:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        body = resp.json()
        history = {}
        for ts, cap in body.get("market_caps", []):
            dt = datetime.utcfromtimestamp(ts / 1000).date()
            history[dt] = float(cap)
        return history
    except Exception as exc:
        print(f"⚠️ 获取 {coin_id} 市值历史失败: {exc}")
        return {}


def _fetch_binance_funding_history(symbol: str = "BTCUSDT", days: int = 400) -> Dict[date, float]:
    """
    拉取 fundingRate 历史，取每天最后一条，计算年化百分比。
    """
    start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol, "startTime": start_time, "limit": 1000}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        arr = resp.json()
        history = {}
        for item in arr:
            ts = int(item["fundingTime"]) / 1000
            dt = datetime.utcfromtimestamp(ts).date()
            rate = float(item["fundingRate"])
            history[dt] = rate * 3 * 365 * 100  # 年化 %
        return history
    except Exception as exc:
        print(f"⚠️ 获取 funding 历史失败: {exc}")
        return {}


def _fetch_fg_history(limit: int = 500) -> Dict[date, int]:
    url = f"https://api.alternative.me/fng/?limit={limit}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        history = {}
        for item in data:
            dt = datetime.utcfromtimestamp(int(item["timestamp"])).date()
            try:
                history[dt] = int(item["value"])
            except Exception:
                continue
        return history
    except Exception as exc:
        print(f"⚠️ 获取恐惧贪婪历史失败: {exc}")
        return {}

def _value_on_or_before(series: List[Tuple[date, Optional[float]]], target: date) -> Optional[float]:
    value = None
    for dt, val in series:
        if dt <= target and val is not None:
            value = val
        elif dt > target:
            break
    return value


def _value_from_map_on_or_before(series_map: Dict[date, float], target: date) -> Optional[float]:
    value = None
    for dt in sorted(series_map.keys()):
        if dt <= target:
            value = series_map[dt]
        else:
            break
    return value

def _pct_change(series: List[Tuple[date, Optional[float]]], target: date, days: int) -> Optional[float]:
    current = _value_on_or_before(series, target)
    past_date = target - timedelta(days=days)
    past = _value_on_or_before(series, past_date)
    if current is None or past is None or past == 0:
        return None
    return round((current - past) / past * 100, 2)

def _moving_average(series: List[Tuple[date, Optional[float]]], target: date, length: int) -> Optional[float]:
    filtered = [val for dt, val in series if dt <= target and val is not None]
    if len(filtered) < length:
        return None
    window = filtered[-length:]
    return round(sum(window) / len(window), 2)

def _build_payload(
    date_cursor: date,
    dxy_series,
    walcl,
    tga,
    rrp,
    btc,
    etf_hist: Dict[date, Dict[str, float]],
    stable_hist: Dict[date, float],
    btc_mcap_hist: Dict[date, float],
    eth_mcap_hist: Dict[date, float],
    total_mcap_hist: Dict[date, float],
    funding_hist: Dict[date, float],
    fg_hist: Dict[date, int],
):
    dxy_today = _value_on_or_before(dxy_series, date_cursor)
    dxy_trend = _pct_change(dxy_series, date_cursor, 30)
    liquidity_today = None
    walcl_val = _value_on_or_before(walcl, date_cursor)
    tga_val = _value_on_or_before(tga, date_cursor)
    rrp_val = _value_on_or_before(rrp, date_cursor)
    if walcl_val is not None and tga_val is not None and rrp_val is not None:
        rrp_m = rrp_val * 1000
        liquidity_today = walcl_val - tga_val - rrp_m
    liquidity_prev = None
    if liquidity_today is not None:
        prev_date = date_cursor - timedelta(days=30)
        walcl_prev = _value_on_or_before(walcl, prev_date)
        tga_prev = _value_on_or_before(tga, prev_date)
        rrp_prev = _value_on_or_before(rrp, prev_date)
        if walcl_prev is not None and tga_prev is not None and rrp_prev is not None:
            liquidity_prev = walcl_prev - tga_prev - (rrp_prev * 1000)

    btc_price = _value_on_or_before(btc, date_cursor)
    price_change_24h = _pct_change(btc, date_cursor, 1)
    price_change_7d = _pct_change(btc, date_cursor, 7)
    ma50 = _moving_average(btc, date_cursor, 50)
    price_vs_ma = None
    if btc_price is not None and ma50 and ma50 != 0:
        price_vs_ma = round((btc_price - ma50) / ma50 * 100, 2)

    # Layer2: ETF 历史（逐日），稳定币历史（逐日前向填充）
    etf_today = etf_hist.get(date_cursor, {})
    # 7 日均值
    last7 = []
    for i in range(7):
        dt = date_cursor - timedelta(days=i)
        v = etf_hist.get(dt, {}).get("etf_net_inflow_m")
        if v is not None:
            last7.append(v)
    etf_weekly_avg = round(sum(last7) / len(last7), 2) if last7 else None

    stable_today = _value_from_map_on_or_before(stable_hist, date_cursor)
    stable_30d_ago = _value_from_map_on_or_before(stable_hist, date_cursor - timedelta(days=30))
    stable_growth_30d = None
    if stable_today is not None and stable_30d_ago not in (None, 0):
        stable_growth_30d = round((stable_today - stable_30d_ago) / stable_30d_ago * 100, 2)

    # Layer3: 用 CoinGecko 市值历史推 dominance / total3 / MA50
    btc_mcap = _value_from_map_on_or_before(btc_mcap_hist, date_cursor)
    eth_mcap = _value_from_map_on_or_before(eth_mcap_hist, date_cursor)
    total_mcap = _value_from_map_on_or_before(total_mcap_hist, date_cursor)
    btc_dominance = None
    eth_dominance = None
    total3_cap_b = None
    total3_ma50_b = None
    total3_status = None
    btc_dom_trend_90d = None
    if btc_mcap and total_mcap:
        btc_dominance = round(btc_mcap / total_mcap * 100, 2)
    if eth_mcap and total_mcap:
        eth_dominance = round(eth_mcap / total_mcap * 100, 2)
    if total_mcap and btc_mcap and eth_mcap:
        total3_cap_b = round((total_mcap - btc_mcap - eth_mcap) / 1e9, 2)
    # 计算 total3 MA50
    if total3_cap_b is not None:
        # 回溯 total3 series
        total3_series = []
        for dt in sorted(total_mcap_hist.keys()):
            if dt > date_cursor:
                break
            tm = total_mcap_hist.get(dt)
            bm = btc_mcap_hist.get(dt)
            em = eth_mcap_hist.get(dt)
            if tm and bm and em:
                total3_series.append(tm - bm - em)
        if len(total3_series) >= 50:
            ma50_val = sum(total3_series[-50:]) / 50 / 1e9
            total3_ma50_b = round(ma50_val, 2)
            total3_status = "Above MA50" if total3_cap_b >= total3_ma50_b else "Below MA50"
    # BTC.D 90d 趋势
    if btc_dominance is not None:
        # 构建 dominance 历史
        dom_hist = []
        for dt in sorted(total_mcap_hist.keys()):
            tm = total_mcap_hist.get(dt)
            bm = btc_mcap_hist.get(dt)
            if tm and bm:
                dom_hist.append((dt, bm / tm * 100))
        btc_dom_trend_90d = _pct_change(dom_hist, date_cursor, 90)

    # Layer4: 价格历史已用 yfinance；资金费率历史用 binance fundingRate
    funding_annual = _value_from_map_on_or_before(funding_hist, date_cursor)
    fg_idx = fg_hist.get(date_cursor) or _value_from_map_on_or_before(fg_hist, date_cursor)

    payload = {
        "date": date_cursor.isoformat(),
        "layer1": {
            "dxy": dxy_today,
            "dxy_trend_30d": "Downtrend" if dxy_trend is not None and dxy_trend < 0 else "Uptrend" if dxy_trend is not None and dxy_trend > 0 else "flat",
            "liquidity_change_30d_b": round((liquidity_today - liquidity_prev) / 1000, 2) if liquidity_today is not None and liquidity_prev is not None else None,
            "liquidity_billions": round(liquidity_today / 1000, 2) if liquidity_today is not None else None
        },
        "layer2": {
            "stablecoin_mcap_b": stable_today,
            "stablecoin_growth_30d_pct": stable_growth_30d,
            "etf_net_inflow_m": etf_today.get("etf_net_inflow_m"),
            "etf_ibit_flow_m": etf_today.get("etf_ibit_flow_m"),
            "etf_weekly_avg_flow_m": etf_weekly_avg,
            "etf_date": date_cursor.isoformat(),
            "_fill": "historical"
        },
        "layer3": {
            "btc_dominance": btc_dominance,
            "eth_dominance": eth_dominance,
            "total3_cap_b": total3_cap_b,
            "btc_dom_trend_90d": btc_dom_trend_90d,
            "total3_structure_status": total3_status,
            "total3_ma50_b": total3_ma50_b,
            "_fill": "historical"
        },
        "layer4": {
            "price_btc": btc_price,
            "price_change_24h_pct": price_change_24h,
            "price_change_7d_pct": price_change_7d,
            "price_vs_50d_ma_pct": price_vs_ma,
            "funding_rate_annualized_pct": funding_annual,
            "fear_greed_index": fg_idx,
            "_fill": "historical"
        }
    }

    # 清理没有真实值的字段（按需删除）
    for layer in ("layer2", "layer3", "layer4"):
        payload[layer] = {k: v for k, v in payload[layer].items() if v is not None}

    return payload

def main():
    end = datetime.utcnow().date()
    start = end - timedelta(days=START_DAYS_DELTA)
    session = _make_session()
    walcl = _fetch_fred_series(session, "WALCL", start.isoformat(), end.isoformat())
    tga = _fetch_fred_series(session, "WTREGEN", start.isoformat(), end.isoformat())
    rrp = _fetch_fred_series(session, "RRPONTSYD", start.isoformat(), end.isoformat())
    dxy = _fetch_yfinance(session, "DX-Y.NYB")
    btc = _fetch_yfinance(session, "BTC-USD")
    etf_hist = _fetch_farside_etf_history()
    stable_hist = _fetch_stablecoin_history()
    btc_mcap_hist = _fetch_cg_market_caps("bitcoin")
    eth_mcap_hist = _fetch_cg_market_caps("ethereum")
    total_mcap_hist = _fetch_cg_market_caps("global")  # 可能失败，失败则相关字段缺失
    funding_hist = _fetch_binance_funding_history("BTCUSDT")
    fg_hist = _fetch_fg_history()

    all_dates = sorted({dt for dt, _ in dxy} | {dt for dt, _ in walcl} | {dt for dt, _ in btc})
    conn = _ensure_db()
    conn.execute("DELETE FROM daily_context WHERE date BETWEEN ? AND ?", ((end - timedelta(days=365)).isoformat(), end.isoformat()))

    target_start = end - timedelta(days=365)
    for current in all_dates:
        if current < target_start:
            continue
        payload = _build_payload(
            current,
            dxy,
            walcl,
            tga,
            rrp,
            btc,
            etf_hist,
            stable_hist,
            btc_mcap_hist,
            eth_mcap_hist,
            total_mcap_hist,
            funding_hist,
            fg_hist,
        )
        conn.execute(
            "INSERT OR REPLACE INTO daily_context (date, payload, created_at) VALUES (?, ?, ?)",
            (current.isoformat(), json.dumps(payload, ensure_ascii=False), datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()
    print(f"✅ 已保存 {len([d for d in all_dates if d >= target_start])} 条历史记录到 {DB_PATH}")

if __name__ == "__main__":
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    main()

