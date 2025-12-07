# Trading Brain - Pentosh1 数据合成主控制器

作为"大脑"调用 `macro_service` (localhost:8001) 的API，将零散数据拼装成 Pentosh1 需要的四层逻辑数据包。

## 功能

- **第一层级（L1）**: 全球宏观"水源"数据
  - Fed Net Liquidity (WALCL - TGA - RRP)
  - DXY (美元指数)
  - US10Y/US02Y (美债收益率)
  - Yield Curve (10Y-2Y利差)
  - SPX/NDX Correlation
  - CNY Liquidity

- **第二层级（L2）**: Crypto 原生"燃料"
  - Stablecoin Market Cap
  - BTC ETF Net Inflow

- **第三层级（L3）**: 市场结构与轮动
  - BTC Dominance
  - ETH/BTC Ratio
  - TOTAL3

- **第四层级（L4）**: 情绪与博弈
  - Funding Rate
  - Open Interest
  - Long/Short Ratio
  - Fear & Greed Index

## 快速开始

### 前置条件

1. 确保 `macro_service` 正在运行：
```powershell
cd macro_service
python app.py
```

2. 安装依赖：
```powershell
cd trading_brain
pip install -r requirements.txt
```

### 运行

```powershell
python main.py
```

## 输出

程序会生成 `output/Daily_Context_YYYY-MM-DD.json` 文件，包含完整的 Pentosh1 数据包。

### 输出文件结构

```json
{
  "timestamp": "2025-01-06T12:00:00",
  "date": "2025-01-06",
  "symbol": "BTC/USDT",
  "layer1_global_liquidity": {
    "indicators": {
      "fed_net_liquidity": {...},
      "dxy": {...},
      "us10y": {...},
      ...
    },
    "macro_score": {
      "score": 65,
      "level": "bullish",
      "signals": [...]
    }
  },
  "layer2_crypto_flows": {...},
  "layer3_market_structure": {...},
  "layer4_sentiment": {...},
  "pentosh1_signals": {
    "macro_trend": "bullish",
    "crypto_momentum": "strong_bullish",
    "overall_bias": "long",
    "risk_level": "medium"
  }
}
```

## 环境变量

- `MACRO_SERVICE_URL`: Macro Service 的URL（默认: http://localhost:8001）

```powershell
$env:MACRO_SERVICE_URL="http://localhost:8001"
```

## Pentosh1 信号说明

### overall_bias (总体偏向)
- `long`: 做多信号
- `short`: 做空信号
- `wait`: 观望

### risk_level (风险等级)
- `low`: 低风险
- `medium`: 中等风险
- `high`: 高风险

### macro_trend (宏观趋势)
- `bullish`: 看涨
- `bearish`: 看跌
- `neutral`: 中性

### crypto_momentum (币圈动能)
- `strong_bullish`: 强烈看涨（ETF流入 > $200M）
- `bullish`: 看涨
- `neutral`: 中性
- `bearish`: 看跌

## 集成示例

### Python 调用

```python
from main import Pentosh1DataAggregator

aggregator = Pentosh1DataAggregator()
data = aggregator.aggregate_all_data("BTC/USDT")
print(data["pentosh1_signals"])
```

### 定时任务

可以设置定时任务（如 cron 或 Windows Task Scheduler）每日运行：

```powershell
# Windows Task Scheduler 或 cron
python E:\nofx-dev\trading_brain\main.py
```

## 注意事项

1. 确保 `macro_service` 正常运行
2. 网络连接正常（需要访问外网API）
3. 某些数据源可能有API限制，失败时会使用默认值
4. 输出目录会自动创建

