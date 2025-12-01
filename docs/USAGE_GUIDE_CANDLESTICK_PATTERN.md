# TA-Lib 形态识别功能使用指南

## 📖 目录

1. [快速开始](#快速开始)
2. [功能说明](#功能说明)
3. [API 使用](#api-使用)
4. [AI Prompt 集成](#ai-prompt-集成)
5. [配置选项](#配置选项)
6. [故障排查](#故障排查)
7. [最佳实践](#最佳实践)

## 🚀 快速开始

### 1. 环境准备

#### 本地开发（Windows）

```powershell
# 1. 安装 TA-Lib C 库（使用预编译版本或 vcpkg）
# 下载地址：https://ta-lib.org/install/

# 2. 设置环境变量
$env:CGO_ENABLED = "1"

# 3. 验证安装
go env CGO_ENABLED  # 应返回 "1"
```

#### Docker 环境

```bash
# Dockerfile 已配置好 TA-Lib，直接构建即可
docker build -f docker/Dockerfile.backend -t nofx-backend .
```

### 2. 编译运行

```bash
# 确保 CGO 已启用
export CGO_ENABLED=1  # Linux/macOS
# 或
$env:CGO_ENABLED = "1"  # Windows PowerShell

# 编译
go build -o nofx .

# 运行
./nofx
```

## 📋 功能说明

### 支持的形态类型

#### 单根 K 线形态（至少需要 1 根 K 线）
- **CDLHAMMER**：锤子线（看涨反转）
- **CDLSHOOTINGSTAR**：流星（看跌反转）
- **CDLDOJI**：十字星（反转信号）
- **CDLHANGINGMAN**：上吊线（看跌反转）
- **CDLINVERTEDHAMMER**：倒锤子（看涨反转）
- **CDLSPINNINGTOP**：纺锤线（犹豫信号）
- **CDLMARUBOZU**：光头光脚（趋势延续）

#### 双根 K 线形态（至少需要 2 根 K 线）
- **CDLENGULFING**：吞噬形态（强烈反转信号）
- **CDLHARAMI**：孕线（反转信号）
- **CDLPIERCING**：刺透形态（看涨反转）
- **CDLDARKCLOUDCOVER**：乌云盖顶（看跌反转）

#### 三根 K 线形态（至少需要 3 根 K 线）
- **CDLMORNINGSTAR**：晨星（看涨反转）
- **CDLEVENINGSTAR**：暮星（看跌反转）
- **CDL3BLACKCROWS**：三只乌鸦（看跌反转）
- **CDL3WHITESOLDIERS**：三白兵（看涨反转）
- **CDL3INSIDE**：三内升/降（反转信号）
- **CDL3LINESTRIKE**：三线打击（反转信号）

### 置信度计算

置信度范围：0.0 - 1.0

**影响因素**：
1. **信号强度**（基础 0.5-0.7）
   - TA-Lib 返回 ±100：基础置信度 0.7
   - 其他值：基础置信度 0.5

2. **实体大小**（±0.1）
   - 实体占 K 线 60% 以上：+0.1
   - 实体较小：按比例调整

3. **成交量分析**（±0.3，最重要）
   - 双倍放量（>2.0 倍）：+0.3
   - 明显放量（>1.5 倍）：+0.15
   - 温和放量（>1.2 倍）：+0.05
   - 缩量（<0.8 倍）：-0.2
   - 严重缩量（<0.5 倍）：-0.3

**置信度等级**：
- **高置信度**（>0.7）：强烈信号，建议重点关注
- **中置信度**（0.5-0.7）：一般信号，需结合其他指标
- **低置信度**（<0.5）：弱信号，可能是假突破

## 🔌 API 使用

### 获取市场数据（包含形态识别）

```go
import "nofx/market"

// 获取单个币种的市场数据
data, err := market.Get("BTCUSDT")
if err != nil {
    log.Fatal(err)
}

// 检查是否有形态识别结果
if data.PatternRecognition != nil {
    fmt.Printf("识别到 %d 个形态\n", len(data.PatternRecognition.Patterns))
    
    // 遍历所有形态
    for _, pattern := range data.PatternRecognition.Patterns {
        fmt.Printf("形态: %s (%s)\n", pattern.DisplayName, pattern.Name)
        fmt.Printf("  时间框架: %s\n", pattern.Timeframe)
        fmt.Printf("  信号: %s\n", pattern.Side)
        fmt.Printf("  置信度: %.2f\n", pattern.Confidence)
        if pattern.Note != "" {
            fmt.Printf("  备注: %s\n", pattern.Note)
        }
    }
}
```

### 获取特定时间框架的形态

```go
// 获取 15 分钟时间框架的形态
if data.MultiTimeframe != nil && data.MultiTimeframe.Timeframe15m != nil {
    patterns := data.MultiTimeframe.Timeframe15m.Patterns
    for _, pattern := range patterns {
        fmt.Printf("15m 形态: %s (置信度: %.2f)\n", 
            pattern.DisplayName, pattern.Confidence)
    }
}
```

### 筛选高置信度形态

```go
// 只获取高置信度的看涨形态
for _, pattern := range data.PatternRecognition.Patterns {
    if pattern.Side == "bullish" && pattern.Confidence > 0.7 {
        fmt.Printf("强烈看涨信号: %s (置信度: %.2f)\n",
            pattern.DisplayName, pattern.Confidence)
    }
}
```

## 🤖 AI Prompt 集成

### User Prompt 中的形态数据

形态识别结果会自动添加到 AI 的 user prompt 中，格式如下：

```
## 🕯️ 蜡烛图形态识别（机器可读）

以下数据包含所有币种在各时间框架识别的K线形态，用于辅助交易决策。
注意：置信度已包含量能分析，低量能的形态可能是假突破。

```json
{
  "BTCUSDT": {
    "symbol": "BTCUSDT",
    "patterns": [
      {
        "name": "CDLENGULFING",
        "display_name": "吞噬形态",
        "side": "bullish",
        "timeframe": "15m",
        "index": 99,
        "confidence": 0.85,
        "note": "Double Volume"
      }
    ],
    "timestamp": 1703123456789
  }
}
```
```

### AI 如何使用形态数据

AI 在决策时会考虑以下因素：

1. **形态类型**：
   - 反转形态（如吞噬、晨星）：可能预示趋势反转
   - 延续形态（如光头光脚）：可能预示趋势延续

2. **时间框架**：
   - 大时间框架（4h、1d）的形态更重要
   - 小时间框架（15m、1h）的形态用于精确入场

3. **置信度**：
   - 优先关注高置信度（>0.7）的形态
   - 低置信度形态需结合其他指标确认

4. **量能备注**：
   - "Double Volume"：放量确认，信号更可靠
   - "Low Volume"：缩量，可能是假突破

### 示例：AI 决策逻辑

```python
# 伪代码示例
def analyze_patterns(pattern_data):
    bullish_signals = []
    bearish_signals = []
    
    for symbol, recognition in pattern_data.items():
        for pattern in recognition.patterns:
            # 只关注高置信度形态
            if pattern.confidence < 0.7:
                continue
            
            # 大时间框架权重更高
            timeframe_weight = {
                "1d": 1.0,
                "4h": 0.8,
                "1h": 0.6,
                "15m": 0.4
            }.get(pattern.timeframe, 0.5)
            
            weighted_confidence = pattern.confidence * timeframe_weight
            
            if pattern.side == "bullish":
                bullish_signals.append({
                    "symbol": symbol,
                    "pattern": pattern.display_name,
                    "confidence": weighted_confidence,
                    "timeframe": pattern.timeframe
                })
            elif pattern.side == "bearish":
                bearish_signals.append(...)
    
    return bullish_signals, bearish_signals
```

## ⚙️ 配置选项

### 修改检测的形态列表

编辑 `market/pattern.go` 中的 `patternConfigs`：

```go
patternConfigs := []struct {
    name    string
    fnID    int
    minBars int
}{
    // 添加或删除形态
    {"CDLHAMMER", 21, 1},
    {"CDLENGULFING", 28, 2},
    // ... 更多形态
}
```

### 调整置信度计算权重

编辑 `market/pattern.go` 中的 `calculateConfidence()` 函数：

```go
// 修改量能分析的权重
if volRatio > 2.0 {
    confidence += 0.3  // 可以调整为 0.4 或 0.5
} else if volRatio > 1.5 {
    confidence += 0.15  // 可以调整为 0.2
}
```

### 修改平均成交量计算周期

编辑 `market/pattern.go` 中的 `calculateAverageVolume()`：

```go
// 使用最近 N 根 K 线的平均成交量
lookback := 20  // 可以调整为 10、30 等
```

## 🔍 故障排查

### 问题 1：编译错误 "cannot find -lta_lib"

**原因**：TA-Lib 库文件未找到

**解决方案**：
```bash
# Linux
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# 检查库文件是否存在
ls -la /usr/local/lib/libta_lib.so*

# 如果不存在，重新安装 TA-Lib
```

### 问题 2：运行时错误 "Library not found"

**原因**：运行时找不到 TA-Lib 动态库

**解决方案**：
```bash
# Docker 环境：确保 Dockerfile 中设置了 LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# 本地环境：设置环境变量
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
```

### 问题 3：形态识别结果为空

**可能原因**：
1. K 线数据不足（某些形态需要多根 K 线）
2. 当前市场没有符合条件的形态
3. TA-Lib 初始化失败

**排查步骤**：
```go
// 检查 K 线数据数量
klines, _ := market.GetKlines("BTCUSDT", "15m", 100)
fmt.Printf("K线数量: %d\n", len(klines))

// 检查 TA-Lib 初始化
// 在 market/pattern.go 中，确保 C.TA_Initialize() 被调用
```

### 问题 4：置信度始终很低

**可能原因**：
1. 成交量数据异常
2. 平均成交量计算有误

**排查步骤**：
```go
// 检查成交量数据
for _, k := range klines {
    fmt.Printf("成交量: %.2f\n", k.Volume)
}

// 检查平均成交量
avgVol := calculateAverageVolume(klines)
fmt.Printf("平均成交量: %.2f\n", avgVol)
```

## 💡 最佳实践

### 1. 形态组合分析

不要单独依赖一个形态，应该：
- 多个时间框架的形态相互确认
- 形态 + 技术指标（MACD、RSI）双重确认
- 形态 + 市场结构（支撑/压力位）结合分析

### 2. 置信度阈值

建议设置置信度阈值：
- **开仓信号**：置信度 > 0.7，且至少 2 个时间框架确认
- **平仓信号**：置信度 > 0.6，且与持仓方向相反
- **观望**：所有形态置信度 < 0.6

### 3. 量能确认

优先关注：
- ✅ 放量形态（"Double Volume"、"Volume Spike"）
- ⚠️ 缩量形态（"Low Volume"）需谨慎，可能是假突破

### 4. 时间框架优先级

建议优先级：
1. **1d（日线）**：大趋势方向
2. **4h（4小时）**：中期趋势
3. **1h（1小时）**：短期趋势
4. **15m（15分钟）**：入场时机

### 5. 形态失效处理

形态识别有时效性：
- 形态出现后，如果价格未按预期运行，应及时调整
- 建议设置形态有效期（如 2-4 根 K 线）

## 📊 监控指标

建议监控以下指标：

1. **形态识别率**：识别到形态的币种占比
2. **高置信度形态占比**：置信度 > 0.7 的形态占比
3. **形态准确率**：形态出现后价格按预期运行的比例
4. **量能确认率**：放量形态占比

## 🔗 相关资源

- [TA-Lib 官方文档](https://ta-lib.org/functions/)
- [形态识别集成方案](./CANDLESTICK_PATTERN_INTEGRATION.md)
- [更新日志](./CHANGELOG_CANDLESTICK_PATTERN.md)

---

**提示**：形态识别是辅助工具，不应作为唯一决策依据。建议结合技术指标、市场结构、资金管理等多方面因素进行综合判断。

