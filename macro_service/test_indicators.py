"""
测试脚本：检查所有Pentosh1宏观指标的数据可用性
测试日期：2025-01-06
"""
import os
import sys
from datetime import datetime, timedelta

# 尝试导入库
# 设置编码
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    print("[WARNING] fredapi not installed, skipping FRED tests")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARNING] yfinance not installed, skipping yfinance tests")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WARNING] requests not installed, skipping DeFi Llama tests")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[WARNING] pandas not installed, may affect data processing")

# 配置
FRED_API_KEY = os.getenv("FRED_API_KEY", "bd89c0475f61d7555dee50daed12185f")
DEFILLAMA_API_BASE = "https://api.llama.fi"
TEST_DATE = "2025-01-06"

# 初始化FRED
fred = None
if FRED_AVAILABLE and FRED_API_KEY:
    try:
        fred = Fred(api_key=FRED_API_KEY)
        print("[OK] FRED API client initialized successfully")
    except Exception as e:
        print(f"[ERROR] FRED API initialization failed: {e}")
elif not FRED_AVAILABLE:
    print("[WARNING] FRED API unavailable (library not installed)")

print(f"\n{'='*80}")
print(f"Pentosh1 Macro Indicators Data Availability Test")
print(f"Test Date: {TEST_DATE}")
print(f"{'='*80}\n")

results = {
    "found": [],
    "not_found": [],
    "partial": []
}

def test_fred(series_id, name, description=""):
    """测试FRED数据"""
    if not FRED_AVAILABLE or not fred:
        results["not_found"].append({
            "指标": name,
            "代码": series_id,
            "原因": "FRED API未初始化"
        })
        return None
    
    try:
        # 获取最近的数据
        end_date = TEST_DATE
        start_date = (datetime.strptime(TEST_DATE, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        
        df = fred.get_series(series_id, start=start_date, end=end_date)
        
        if df is None or df.empty:
            results["not_found"].append({
                "指标": name,
                "代码": series_id,
                "原因": "数据为空"
            })
            return None
        
        # 查找最接近测试日期的数据
        test_dt = datetime.strptime(TEST_DATE, "%Y-%m-%d")
        closest_date = None
        closest_value = None
        min_diff = float('inf')
        
        for date, value in df.items():
            if PANDAS_AVAILABLE and isinstance(date, pd.Timestamp):
                date_dt = date.to_pydatetime()
            elif hasattr(date, 'to_pydatetime'):
                date_dt = date.to_pydatetime()
            else:
                date_dt = date
            diff = abs((date_dt - test_dt).days)
            if diff < min_diff:
                min_diff = diff
                closest_date = date_dt
                closest_value = value
        
        if closest_date:
            results["found"].append({
                "指标": name,
                "代码": series_id,
                "日期": closest_date.strftime("%Y-%m-%d"),
                "值": closest_value,
                "距离测试日期": f"{min_diff}天"
            })
            return closest_value
        else:
            results["not_found"].append({
                "指标": name,
                "代码": series_id,
                "原因": "未找到接近日期的数据"
            })
            return None
            
    except Exception as e:
        results["not_found"].append({
            "指标": name,
            "代码": series_id,
            "原因": f"错误: {str(e)}"
        })
        return None

def test_yfinance(symbol, name, description=""):
    """测试yfinance数据"""
    if not YFINANCE_AVAILABLE:
        results["not_found"].append({
            "指标": name,
            "代码": symbol,
            "原因": "yfinance库未安装"
        })
        return None
    try:
        ticker = yf.Ticker(symbol)
        
        # 获取历史数据
        hist = ticker.history(start="2025-01-01", end="2025-01-10", interval="1d")
        
        if hist is None or hist.empty:
            results["not_found"].append({
                "指标": name,
                "代码": symbol,
                "原因": "数据为空"
            })
            return None
        
        # 查找测试日期的数据
        if PANDAS_AVAILABLE:
            test_date = pd.Timestamp(TEST_DATE)
        else:
            test_date = datetime.strptime(TEST_DATE, "%Y-%m-%d")
            
        if PANDAS_AVAILABLE and test_date in hist.index:
            value = hist.loc[test_date, "Close"]
            results["found"].append({
                "指标": name,
                "代码": symbol,
                "日期": TEST_DATE,
                "值": float(value),
                "距离测试日期": "0天"
            })
            return float(value)
        else:
            # 查找最接近的日期
            if PANDAS_AVAILABLE:
                closest_idx = hist.index.get_indexer([test_date], method='nearest')[0]
                closest_date = hist.index[closest_idx]
                closest_value = hist.loc[closest_date, "Close"]
                diff = abs((closest_date - test_date).days)
            else:
                # 简单查找
                closest_date = hist.index[0]
                closest_value = hist.iloc[0]["Close"]
                diff = abs((closest_date - test_date).days) if hasattr(closest_date, '__sub__') else 0
            
            results["found"].append({
                "指标": name,
                "代码": symbol,
                "日期": closest_date.strftime("%Y-%m-%d"),
                "值": float(closest_value),
                "距离测试日期": f"{diff}天"
            })
            return float(closest_value)
            
    except Exception as e:
        results["not_found"].append({
            "指标": name,
            "代码": symbol,
            "原因": f"错误: {str(e)}"
        })
        return None

def test_defillama(endpoint, name, params=None):
    """测试DeFi Llama数据"""
    if not REQUESTS_AVAILABLE:
        results["not_found"].append({
            "指标": name,
            "端点": endpoint,
            "原因": "requests库未安装"
        })
        return None
    try:
        url = f"{DEFILLAMA_API_BASE}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results["found"].append({
                "指标": name,
                "端点": endpoint,
                "状态": "成功",
                "数据": "已获取"
            })
            return data
        else:
            results["not_found"].append({
                "指标": name,
                "端点": endpoint,
                "原因": f"HTTP {response.status_code}"
            })
            return None
            
    except Exception as e:
        results["not_found"].append({
            "指标": name,
            "端点": endpoint,
            "原因": f"错误: {str(e)}"
        })
        return None

# ==================== 第一层级：全球宏观"水源" ====================
print("第一层级：全球宏观水源 (Global Liquidity)\n")

# 1. Fed Net Liquidity = WALCL - TGA - RRP
print("1. Fed Net Liquidity (WALCL - TGA - RRP)...")
walcl = test_fred("WALCL", "WALCL (美联储总资产)", "美联储总资产")
tga = test_fred("WTREGEN", "TGA (财政部一般账户)", "财政部一般账户")  # 注意：可能是WTREGEN
rrp = test_fred("RRPONTSYD", "RRP (逆回购)", "逆回购")
if walcl and tga and rrp:
    net_liquidity = walcl - tga - rrp
    results["found"].append({
        "指标": "Fed Net Liquidity",
        "代码": "WALCL - TGA - RRP",
        "日期": TEST_DATE,
        "值": net_liquidity,
        "距离测试日期": "计算值"
    })
else:
    results["partial"].append({
        "指标": "Fed Net Liquidity",
        "代码": "WALCL - TGA - RRP",
        "原因": "部分数据缺失"
    })

# 2. DXY
print("2. DXY (美元指数)...")
test_yfinance("DX-Y.NYB", "DXY (美元指数)")

# 3. US10Y
print("3. US10Y (10年美债)...")
test_yfinance("^TNX", "US10Y (10年美债收益率)")

# 4. US02Y
print("4. US02Y (2年美债)...")
# 尝试yfinance
test_yfinance("^IRX", "US02Y (2年美债收益率 - yfinance)")
# 也尝试FRED
test_fred("DGS2", "US02Y (2年美债收益率 - FRED)")

# 5. Yield Curve (10Y-2Y)
print("5. Yield Curve (10Y-2Y)...")
test_fred("T10Y2Y", "Yield Curve (10Y-2Y利差)")

# 6. SPX/NDX
print("6. SPX/NDX Correlation...")
spx = test_yfinance("^GSPC", "SPX (标普500)")
ndx = test_yfinance("^NDX", "NDX (纳斯达克100)")

# 7. CNY Liquidity
print("7. CNY Liquidity (人民币流动性)...")
test_yfinance("CNH=X", "CNY/CNH (人民币汇率)")

# ==================== 第二层级：Crypto 原生"燃料" ====================
print("\n第二层级：Crypto 原生燃料 (On-Chain/Flow Liquidity)\n")

# 1. Stablecoin Market Cap
print("1. Stablecoin Market Cap...")
test_defillama("stablecoins", "Stablecoin Market Cap")

# 2-5. 其他指标不在我们的库中
print("2. Stablecoin Exchange Reserve - ❌ 需要 CryptoQuant API")
results["not_found"].append({
    "指标": "Stablecoin Exchange Reserve",
    "代码": "CryptoQuant",
    "原因": "需要 CryptoQuant API"
})

print("3. BTC ETF Net Inflow - ❌ 需要 Farside API")
results["not_found"].append({
    "指标": "BTC ETF Net Inflow",
    "代码": "Farside",
    "原因": "需要 Farside API"
})

print("4. Coinbase Premium Gap - ❌ 需要 CryptoQuant API")
results["not_found"].append({
    "指标": "Coinbase Premium Gap",
    "代码": "CryptoQuant",
    "原因": "需要 CryptoQuant API"
})

print("5. BTC Exchange Reserve - ❌ 需要 Glassnode API")
results["not_found"].append({
    "指标": "BTC Exchange Reserve",
    "代码": "Glassnode",
    "原因": "需要 Glassnode API"
})

# ==================== 第三层级：市场结构与轮动 ====================
print("\n第三层级：市场结构与轮动 (Market Structure & Rotation)\n")

print("1. BTC Dominance - ❌ 需要 TradingView API")
results["not_found"].append({
    "指标": "BTC Dominance",
    "代码": "BTC.D",
    "原因": "需要 TradingView API"
})

# 2. ETH/BTC Ratio
print("2. ETH/BTC Ratio...")
eth = test_yfinance("ETH-USD", "ETH (以太坊)")
btc = test_yfinance("BTC-USD", "BTC (比特币)")
if eth and btc:
    eth_btc_ratio = eth / btc
    results["found"].append({
        "指标": "ETH/BTC Ratio",
        "代码": "ETH-USD / BTC-USD",
        "日期": TEST_DATE,
        "值": eth_btc_ratio,
        "距离测试日期": "计算值"
    })

print("3. TOTAL3 - ❌ 需要 TradingView API")
results["not_found"].append({
    "指标": "TOTAL3",
    "代码": "TradingView",
    "原因": "需要 TradingView API"
})

print("4. OTHERS.D - ❌ 需要 TradingView API")
results["not_found"].append({
    "指标": "OTHERS.D",
    "代码": "TradingView",
    "原因": "需要 TradingView API"
})

# ==================== 第四层级：情绪与博弈 ====================
print("\n第四层级：情绪与博弈 (Sentiment & Positioning)\n")

print("1. Funding Rate - ❌ 需要交易所API")
results["not_found"].append({
    "指标": "Funding Rate",
    "代码": "交易所API",
    "原因": "需要交易所API (Binance/OKX等)"
})

print("2. Open Interest - ❌ 需要 Coinglass API")
results["not_found"].append({
    "指标": "Open Interest",
    "代码": "Coinglass",
    "原因": "需要 Coinglass API"
})

print("3. Long/Short Ratio - ❌ 需要交易所API")
results["not_found"].append({
    "指标": "Long/Short Ratio",
    "代码": "交易所API",
    "原因": "需要交易所API"
})

print("4. Fear & Greed Index - ❌ 需要 Alternative.me API")
results["not_found"].append({
    "指标": "Fear & Greed Index",
    "代码": "Alternative.me",
    "原因": "需要 Alternative.me API"
})

print("5. Liquidation Heatmap - ❌ 需要 Coinglass API")
results["not_found"].append({
    "指标": "Liquidation Heatmap",
    "代码": "Coinglass",
    "原因": "需要 Coinglass API"
})

# ==================== 输出结果 ====================
print(f"\n{'='*80}")
print("📊 测试结果汇总")
print(f"{'='*80}\n")

print(f"[FOUND] Data found ({len(results['found'])} items):")
print("-" * 80)
for item in results["found"]:
    if "值" in item or "value" in item:
        val = item.get('值') or item.get('value', 'N/A')
        if isinstance(val, (int, float)):
            print(f"  [OK] {item['指标']:30s} | {item.get('代码', item.get('code', '')):20s} | Value: {val:.4f} | {item.get('距离测试日期', item.get('days_away', ''))}")
        else:
            print(f"  [OK] {item['指标']:30s} | {item.get('代码', item.get('code', '')):20s} | Value: {val} | {item.get('距离测试日期', item.get('days_away', ''))}")
    else:
        print(f"  [OK] {item['指标']:30s} | {item.get('端点', item.get('endpoint', '')):20s} | {item.get('状态', item.get('status', ''))}")

if results["partial"]:
    print(f"\n[PARTIAL] Partial data ({len(results['partial'])} items):")
    print("-" * 80)
    for item in results["partial"]:
        print(f"  [PARTIAL] {item['指标']:30s} | {item.get('代码', item.get('code', '')):20s} | {item.get('原因', item.get('reason', ''))}")

print(f"\n[NOT FOUND] Data not found ({len(results['not_found'])} items):")
print("-" * 80)
for item in results["not_found"]:
    code = item.get('代码') or item.get('code') or item.get('端点') or item.get('endpoint') or ''
    reason = item.get('原因') or item.get('reason') or ''
    print(f"  [MISSING] {item['指标']:30s} | {code:20s} | {reason}")

print(f"\n{'='*80}")
print(f"Total: {len(results['found'])} available | {len(results['partial'])} partial | {len(results['not_found'])} unavailable")
print(f"{'='*80}\n")

