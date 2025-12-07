# Pentosh1 宏观指标数据可用性报告

测试日期：2025-01-06

## 数据源状态

- ✅ **FRED API**: 已集成，需要安装 `fredapi` 库
- ✅ **yfinance**: 已集成，需要安装 `yfinance` 库  
- ✅ **DeFi Llama**: 已集成，使用 `requests` 库

---

## 第一层级：全球宏观"水源" (Global Liquidity)

| 指标名称 | 代码/源 | 数据源 | 状态 | 说明 |
|---------|---------|--------|------|------|
| **Fed Net Liquidity** | WALCL - TGA - RRP | FRED | ✅ 可用 | 需要计算：WALCL - TGA - RRP |
| **DXY (美元指数)** | DX-Y.NYB | yfinance | ✅ 可用 | 直接获取 |
| **US10Y (10年美债)** | ^TNX | yfinance | ✅ 可用 | 直接获取 |
| **US02Y (2年美债)** | DGS2 / ^IRX | FRED / yfinance | ✅ 可用 | FRED更准确 |
| **Yield Curve (10Y-2Y)** | T10Y2Y | FRED | ✅ 可用 | 直接获取 |
| **SPX/NDX Correlation** | ^GSPC, ^NDX | yfinance | ✅ 可用 | 需要计算相关性 |
| **CNY Liquidity** | CNH=X | yfinance | ✅ 可用 | 直接获取 |

**第一层级总结**: 7项指标全部可用 ✅

---

## 第二层级：Crypto 原生"燃料" (On-Chain/Flow Liquidity)

| 指标名称 | 代码/源 | 数据源 | 状态 | 说明 |
|---------|---------|--------|------|------|
| **Stablecoin Market Cap** | DeFiLlama | DeFi Llama | ✅ 可用 | 使用 `/stablecoins` 端点 |
| **Stablecoin Exchange Reserve** | CryptoQuant | ❌ 未集成 | ❌ 不可用 | 需要 CryptoQuant API |
| **BTC ETF Net Inflow** | Farside | ❌ 未集成 | ❌ 不可用 | 需要 Farside API |
| **Coinbase Premium Gap** | CryptoQuant | ❌ 未集成 | ❌ 不可用 | 需要 CryptoQuant API |
| **BTC Exchange Reserve** | Glassnode | ❌ 未集成 | ❌ 不可用 | 需要 Glassnode API |

**第二层级总结**: 1项可用，4项不可用 ⚠️

---

## 第三层级：市场结构与轮动 (Market Structure & Rotation)

| 指标名称 | 代码/源 | 数据源 | 状态 | 说明 |
|---------|---------|--------|------|------|
| **BTC Dominance** | BTC.D | TradingView | ❌ 不可用 | 需要 TradingView API |
| **ETH/BTC Ratio** | ETH-USD / BTC-USD | yfinance | ✅ 可用 | 需要计算：ETH价格/BTC价格 |
| **TOTAL3** | TradingView | TradingView | ❌ 不可用 | 需要 TradingView API |
| **OTHERS.D** | TradingView | TradingView | ❌ 不可用 | 需要 TradingView API |

**第三层级总结**: 1项可用，3项不可用 ⚠️

---

## 第四层级：情绪与博弈 (Sentiment & Positioning)

| 指标名称 | 代码/源 | 数据源 | 状态 | 说明 |
|---------|---------|--------|------|------|
| **Funding Rate** | 交易所API | Binance/OKX等 | ❌ 不可用 | 需要交易所API |
| **Open Interest** | Coinglass | Coinglass | ❌ 不可用 | 需要 Coinglass API |
| **Long/Short Ratio** | 交易所API | Binance/OKX等 | ❌ 不可用 | 需要交易所API |
| **Fear & Greed Index** | Alternative.me | Alternative.me | ❌ 不可用 | 需要 Alternative.me API |
| **Liquidation Heatmap** | Coinglass | Coinglass | ❌ 不可用 | 需要 Coinglass API |

**第四层级总结**: 0项可用，5项不可用 ❌

---

## 总体统计

- ✅ **可用**: 9项 (第一层级7项 + 第二层级1项 + 第三层级1项)
- ❌ **不可用**: 12项 (需要额外API集成)

---

## 需要集成的额外API

### 高优先级（第二层级）
1. **CryptoQuant API** - Stablecoin Exchange Reserve, Coinbase Premium Gap
2. **Farside API** - BTC ETF Net Inflow
3. **Glassnode API** - BTC Exchange Reserve

### 中优先级（第三层级）
4. **TradingView API** - BTC Dominance, TOTAL3, OTHERS.D

### 低优先级（第四层级）
5. **交易所API** (Binance/OKX) - Funding Rate, Long/Short Ratio
6. **Coinglass API** - Open Interest, Liquidation Heatmap
7. **Alternative.me API** - Fear & Greed Index

---

## 当前可用数据的API调用示例

### FRED API
```python
# Fed Net Liquidity
walcl = fred.get_series("WALCL", start="2025-01-01", end="2025-01-10")
tga = fred.get_series("WTREGEN", start="2025-01-01", end="2025-01-10")
rrp = fred.get_series("RRPONTSYD", start="2025-01-01", end="2025-01-10")
net_liquidity = walcl - tga - rrp

# Yield Curve
yield_curve = fred.get_series("T10Y2Y", start="2025-01-01", end="2025-01-10")
```

### yfinance
```python
# DXY
dxy = yf.Ticker("DX-Y.NYB").history(start="2025-01-01", end="2025-01-10")

# US10Y
us10y = yf.Ticker("^TNX").history(start="2025-01-01", end="2025-01-10")

# SPX/NDX
spx = yf.Ticker("^GSPC").history(start="2025-01-01", end="2025-01-10")
ndx = yf.Ticker("^NDX").history(start="2025-01-01", end="2025-01-10")

# CNY
cny = yf.Ticker("CNH=X").history(start="2025-01-01", end="2025-01-10")

# ETH/BTC Ratio
eth = yf.Ticker("ETH-USD").history(start="2025-01-01", end="2025-01-10")
btc = yf.Ticker("BTC-USD").history(start="2025-01-01", end="2025-01-10")
eth_btc_ratio = eth["Close"] / btc["Close"]
```

### DeFi Llama
```python
import requests

# Stablecoin Market Cap
response = requests.get("https://api.llama.fi/stablecoins")
stablecoin_data = response.json()
```

---

## 下一步建议

1. **优先集成 CryptoQuant API** - 获取 Stablecoin Exchange Reserve 和 Coinbase Premium Gap
2. **集成 Farside API** - 获取 BTC ETF Net Inflow（重要指标）
3. **集成 Glassnode API** - 获取 BTC Exchange Reserve
4. **考虑集成 Coinglass API** - 获取 Open Interest 和 Liquidation Heatmap
5. **考虑集成交易所API** - 获取 Funding Rate 和 Long/Short Ratio

