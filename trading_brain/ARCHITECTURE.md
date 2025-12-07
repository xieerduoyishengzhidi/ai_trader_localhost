# Trading Brain 架构说明

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              Trading Brain (main.py)                    │
│                  "大脑" - 主控制器                        │
│                                                          │
│  • 数据聚合                                              │
│  • 逻辑合成                                              │
│  • 信号生成                                              │
│  • 输出管理                                              │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP API 调用
                   │
┌──────────────────▼──────────────────────────────────────┐
│         Macro Service (localhost:8001)                  │
│              "手脚" - 数据服务层                          │
│                                                          │
│  • FRED API (宏观数据)                                  │
│  • yfinance (股票/指数数据)                              │
│  • DeFi Llama (DeFi数据)                                │
│  • Crypto Fetcher (币圈原生数据)                         │
└──────────────────────────────────────────────────────────┘
```

## 数据流

### 第一层级：全球宏观"水源"
```
Trading Brain → Macro Service → FRED API
              → Macro Service → yfinance
              
获取指标：
- Fed Net Liquidity (WALCL - TGA - RRP)
- DXY (美元指数)
- US10Y/US02Y (美债收益率)
- Yield Curve (10Y-2Y)
- SPX/NDX Correlation
- CNY Liquidity
```

### 第二、三、四层级：币圈数据
```
Trading Brain → Macro Service → /api/crypto/all
              → Crypto Fetcher → ccxt/Binance
                              → Farside (ETF)
                              → DeFi Llama
                              → CoinGecko
                              → Alternative.me
```

## 核心类：Pentosh1DataAggregator

### 主要方法

1. **get_layer1_global_liquidity()**
   - 获取第一层级宏观数据
   - 计算宏观综合评分
   - 返回指标和信号

2. **get_layer2_4_crypto_data(symbol)**
   - 获取第二、三、四层级币圈数据
   - 调用 `/api/crypto/all` 接口
   - 返回结构化数据

3. **aggregate_all_data(symbol)**
   - 聚合所有层级数据
   - 生成完整 Pentosh1 数据包
   - 包含所有指标和信号

4. **_generate_pentosh1_signals(layer1, layer2_4)**
   - 生成 Pentosh1 交易信号
   - 综合判断多层级数据
   - 输出交易建议

5. **save_daily_context(data, output_dir)**
   - 保存每日上下文数据
   - 生成 `Daily_Context_YYYY-MM-DD.json`
   - 自动创建输出目录

## 信号生成逻辑

### 宏观趋势 (macro_trend)
- **bullish**: 宏观评分 > 60
- **bearish**: 宏观评分 < 40
- **neutral**: 40-60

### 币圈动能 (crypto_momentum)
- **strong_bullish**: ETF流入 > $200M
- **bullish**: ETF流入 > 0
- **neutral**: 0
- **bearish**: ETF流出 > $100M

### 市场结构 (market_structure)
- **btc_dominant**: BTC.D > 55%
- **alt_season**: BTC.D < 50%
- **neutral**: 50-55%

### 情绪 (sentiment)
- **overheated**: 资金费率 > 10% (年化)
- **extreme_greed**: 恐惧贪婪指数 > 85
- **extreme_fear**: 恐惧贪婪指数 < 20
- **oversold**: 资金费率 < -5%

### 总体偏向 (overall_bias)
- **long**: 至少2个看涨信号
- **short**: 至少2个看跌信号
- **wait**: 信号不明确

## 输出格式

### Daily_Context_YYYY-MM-DD.json 结构

```json
{
  "timestamp": "2025-01-06T12:00:00",
  "date": "2025-01-06",
  "symbol": "BTC/USDT",
  "layer1_global_liquidity": {
    "indicators": {
      "fed_net_liquidity": {...},
      "dxy": {...},
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

## 使用流程

1. **启动 Macro Service**
   ```powershell
   cd macro_service
   python app.py
   ```

2. **运行 Trading Brain**
   ```powershell
   cd trading_brain
   python main.py
   ```

3. **查看输出**
   - 控制台输出摘要信息
   - JSON文件保存在 `output/Daily_Context_YYYY-MM-DD.json`

## 定时任务设置

### Windows Task Scheduler
1. 打开任务计划程序
2. 创建基本任务
3. 触发器：每日运行
4. 操作：启动程序
   - 程序：`python`
   - 参数：`E:\nofx-dev\trading_brain\main.py`
   - 起始于：`E:\nofx-dev\trading_brain`

### Linux/Mac Cron
```bash
# 每天上午9点运行
0 9 * * * cd /path/to/trading_brain && python main.py
```

## 错误处理

- API调用失败时会记录警告，使用默认值
- Macro Service 不可用时会提前退出
- 数据缺失时会使用空结构，不影响整体流程

## 扩展性

### 添加新指标
1. 在 `get_layer1_global_liquidity()` 中添加数据获取逻辑
2. 在 `_calculate_macro_score()` 中添加评分计算
3. 在 `_generate_pentosh1_signals()` 中添加信号判断

### 添加新数据源
1. 在 Macro Service 中添加新的 API 端点
2. 在 Trading Brain 中调用新端点
3. 集成到数据包中

## 性能优化

- 使用 Session 复用连接
- 并行调用独立的数据源（未来可优化）
- 缓存机制（未来可添加）

