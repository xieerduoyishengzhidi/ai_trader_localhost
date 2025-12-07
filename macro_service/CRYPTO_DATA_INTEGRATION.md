# 币圈原生数据集成说明

## 概述

已成功集成 `crypto_fetcher.py` 模块，用于获取 Pentosh1 策略所需的币圈原生数据。该模块使用 ccxt、Farside、DeFi Llama、CoinGecko 等数据源，补全了之前缺失的非宏观数据。

## 新增功能

### 1. Binance 期货数据（第四层级：情绪与博弈）

**数据包括：**
- 价格和24小时变化率
- 资金费率（Funding Rate）- Pentosh1 关键指标
- 未平仓合约（Open Interest）- OI 暴涨但价格滞涨 = 变盘信号
- 多空比（Long/Short Ratio）- 散户情绪指标

**API端点：**
```
POST /api/crypto/futures
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

### 2. BTC ETF 资金流向（第二层级：机构资金）

**数据包括：**
- ETF 净流入总额
- IBIT（贝莱德）资金流向
- 数据日期

**Pentosh1 逻辑：** 净流入 > $200M = 强趋势信号

**API端点：**
```
GET /api/crypto/etf
```

### 3. 市场结构与流动性（第二、三、四层级）

**数据包括：**
- 稳定币总市值（USDT + USDC + DAI + FDUSD + USDe）
- BTC Dominance（BTC.D）
- ETH Dominance
- ETH/BTC Ratio
- TOTAL3（剔除BTC和ETH的总市值）
- 恐惧贪婪指数（Fear & Greed Index）

**API端点：**
```
GET /api/crypto/market-structure
```

### 4. 完整数据面板

**API端点：**
```
POST /api/crypto/all
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

返回完整的 Pentosh1 数据面板，包含所有层级的数据。

## 数据源说明

### ccxt (Binance)
- **用途：** 获取期货市场数据（资金费率、OI、价格）
- **优势：** 统一的交易所接口，支持多个交易所
- **限制：** 无API Key时频次限制较严格

### Farside.co.uk
- **用途：** 爬取BTC ETF资金流向数据
- **方法：** 使用 pandas.read_html() 解析网页表格
- **更新频率：** 每日更新

### DeFi Llama
- **用途：** 获取稳定币总市值
- **端点：** `https://stablecoins.llama.fi/stablecoins`

### CoinGecko
- **用途：** 获取市场结构数据（BTC.D、TOTAL3）
- **优势：** 免费API，无需Key
- **限制：** 10-30次/分钟

### Alternative.me
- **用途：** 获取恐惧贪婪指数
- **端点：** `https://api.alternative.me/fng/`

## 安装依赖

```powershell
cd macro_service
pip install -r requirements.txt
```

新增依赖：
- `ccxt==4.2.25` - 交易所接口库
- `lxml==5.1.0` - HTML解析（pandas需要）

## 环境变量（可选）

如果需要更高的API调用频率限制，可以设置 Binance API Key：

```powershell
$env:BINANCE_API_KEY="your_api_key"
$env:BINANCE_SECRET="your_secret"
```

**注意：** 即使不设置API Key，也能正常获取行情数据，只是频次限制更严格。

## 使用示例

### PowerShell 示例

```powershell
# 获取BTC期货数据
$body = @{
    symbol = "BTC/USDT"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/futures" -Method POST -Body $body -ContentType "application/json"

# 获取ETF资金流向
Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/etf" -Method GET

# 获取市场结构数据
Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/market-structure" -Method GET

# 获取完整数据面板
$body = @{
    symbol = "BTC/USDT"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/all" -Method POST -Body $body -ContentType "application/json"
```

### Python 示例

```python
from crypto_fetcher import CryptoDataLoader

# 初始化（可选：传入API Key）
loader = CryptoDataLoader(api_key="your_key", secret="your_secret")

# 获取完整数据
data = loader.get_all_crypto_data("BTC/USDT")
print(data)
```

## 数据覆盖情况

### ✅ 已补全的数据

**第二层级：Crypto 原生"燃料"**
- ✅ Stablecoin Market Cap（稳定币总市值）
- ✅ BTC ETF Net Inflow（ETF资金流向）

**第三层级：市场结构与轮动**
- ✅ BTC Dominance（BTC.D）
- ✅ ETH/BTC Ratio
- ✅ TOTAL3（近似值）

**第四层级：情绪与博弈**
- ✅ Funding Rate（资金费率）
- ✅ Open Interest（持仓量）
- ✅ Long/Short Ratio（多空比）
- ✅ Fear & Greed Index（恐惧贪婪指数）

### ⚠️ 仍需集成的数据

**第二层级：**
- ❌ Stablecoin Exchange Reserve（需要 CryptoQuant API）
- ❌ Coinbase Premium Gap（需要 CryptoQuant API）
- ❌ BTC Exchange Reserve（需要 Glassnode API）

**第三层级：**
- ⚠️ TOTAL3（当前为近似值，如需精确值需要 TradingView API）
- ⚠️ OTHERS.D（需要 TradingView API）

**第四层级：**
- ❌ Liquidation Heatmap（需要 Coinglass API）

## 与现有 data.go 的集成

`crypto_fetcher.py` 模块独立运行，不直接调用 Go 代码。但可以通过以下方式集成：

1. **通过API调用：** Go 代码可以通过 HTTP 请求调用 macro_service 的 API
2. **数据格式统一：** 返回的JSON格式可以直接被 Go 代码解析
3. **独立运行：** Python模块可以独立运行，不依赖Go服务

## 注意事项

1. **API限制：** 注意各数据源的API调用频率限制
2. **错误处理：** 所有方法都包含错误处理，失败时返回默认值或None
3. **数据更新频率：** ETF数据每日更新，期货数据实时更新
4. **网络依赖：** 需要访问外网才能获取数据

## 测试

运行测试脚本：

```powershell
cd macro_service
python crypto_fetcher.py
```

这将输出完整的 Pentosh1 数据面板。

