# Macro Service - 宏观经济数据服务

独立的宏观经济数据服务，集成 FRED API、yfinance 和 DeFi Llama，提供宏观经济指标、金融市场数据和 DeFi 数据。

## 功能

- **FRED API**: 获取美国联邦储备经济数据（GDP、失业率、CPI、利率等）
- **yfinance**: 获取股票、ETF、指数等金融市场数据
- **DeFi Llama**: 获取 DeFi 协议总锁仓价值（TVL）、协议数据、链数据、代币价格等
- **Crypto Fetcher**: 获取币圈原生数据（资金费率、持仓量、多空比、ETF流量、市场结构等）

## 快速开始

### 安装依赖

```powershell
cd macro_service
pip install -r requirements.txt
```

### 环境变量

```powershell
$env:FRED_API_KEY="bd89c0475f61d7555dee50daed12185f"
$env:PORT="8001"
```

### 运行服务

```powershell
python app.py
```

服务将在 `http://localhost:8001` 启动

## API 端点

### 健康检查
```
GET /health
```

### FRED API

#### 获取数据系列
```
POST /api/fred/series
Content-Type: application/json

{
  "series_id": "GDP",
  "start_date": "2020-01-01",
  "end_date": "2024-01-01",
  "limit": 100
}
```

#### 获取常用指标列表
```
GET /api/fred/common
```

### YFinance API

#### 获取单个股票/ETF数据
```
POST /api/yfinance/quote
Content-Type: application/json

{
  "symbol": "SPY",
  "period": "1mo",
  "interval": "1d"
}
```

#### 批量获取多个股票数据
```
POST /api/yfinance/multi
Content-Type: application/json

{
  "symbols": ["SPY", "QQQ", "^GSPC"],
  "period": "1mo",
  "interval": "1d"
}
```

### DeFi Llama API

#### 获取总TVL
```
GET /api/defillama/tvl
GET /api/defillama/tvl?chain=ethereum
```

#### 获取所有协议列表
```
GET /api/defillama/protocols
```

#### 获取特定协议数据
```
GET /api/defillama/protocol/uniswap
POST /api/defillama/protocol
Content-Type: application/json

{
  "protocol": "uniswap"
}
```

#### 获取所有链数据
```
GET /api/defillama/chains
```

#### 获取代币价格
```
GET /api/defillama/tokens
GET /api/defillama/tokens?tokens=ethereum:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
```

#### 获取历史TVL数据
```
POST /api/defillama/historical
Content-Type: application/json

{
  "protocol": "uniswap",
  "start": 1609459200,
  "end": 1640995200
}
```

## 使用示例

### 获取美国GDP数据
```powershell
$body = @{
    series_id = "GDP"
    start_date = "2020-01-01"
    end_date = "2024-01-01"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/fred/series" -Method POST -Body $body -ContentType "application/json"
```

### 获取标普500指数数据
```powershell
$body = @{
    symbol = "^GSPC"
    period = "1mo"
    interval = "1d"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/yfinance/quote" -Method POST -Body $body -ContentType "application/json"
```

### 获取DeFi协议数据
```powershell
# 获取Uniswap协议数据
Invoke-RestMethod -Uri "http://localhost:8001/api/defillama/protocol/uniswap" -Method GET

# 获取所有协议列表
Invoke-RestMethod -Uri "http://localhost:8001/api/defillama/protocols" -Method GET

# 获取以太坊链TVL
Invoke-RestMethod -Uri "http://localhost:8001/api/defillama/tvl?chain=ethereum" -Method GET
```

### Crypto Data API (币圈原生数据)

#### 获取期货数据（资金费率、OI、多空比）
```
POST /api/crypto/futures
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

#### 获取BTC ETF资金流向
```
GET /api/crypto/etf
```

#### 获取市场结构与流动性数据
```
GET /api/crypto/market-structure
```

#### 获取完整币圈数据面板
```
POST /api/crypto/all
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

### 使用示例

#### 获取BTC期货数据
```powershell
$body = @{
    symbol = "BTC/USDT"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/futures" -Method POST -Body $body -ContentType "application/json"
```

#### 获取完整Pentosh1数据面板
```powershell
$body = @{
    symbol = "BTC/USDT"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/crypto/all" -Method POST -Body $body -ContentType "application/json"
```

## 常用FRED系列ID

- `GDP`: 国内生产总值
- `UNRATE`: 失业率
- `CPIAUCSL`: 消费者物价指数
- `FEDFUNDS`: 联邦基金利率
- `DGS10`: 10年期国债收益率
- `DGS2`: 2年期国债收益率
- `DEXCHUS`: 人民币/美元汇率
- `DEXUSEU`: 欧元/美元汇率
- `DEXJPUS`: 日元/美元汇率
- `GOLDAMGBD228NLBM`: 黄金价格
- `DCOILWTICO`: 原油价格（WTI）

## Docker 部署

```powershell
docker build -t macro-service .
docker run -p 8001:8001 -e FRED_API_KEY="bd89c0475f61d7555dee50daed12185f" macro-service
```

