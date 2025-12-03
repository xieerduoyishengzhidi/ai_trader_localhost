# 错误处理测试文档

## 概述

本文档描述了资金费率和持仓量获取功能的错误处理机制。

## 错误处理策略

### 1. 资金费率 (Funding Rate) 错误处理

**API**: `GET https://fapi.binance.com/fapi/v1/premiumIndex`

**错误场景及处理**:

1. **网络错误**
   - 行为: 如果缓存中有旧数据，返回旧数据
   - 如果缓存为空，返回错误，Get函数会记录警告并使用默认值 0.0

2. **API返回错误状态码**
   - 行为: 返回错误，Get函数会记录警告并使用默认值 0.0

3. **JSON解析错误**
   - 行为: 返回错误，Get函数会记录警告并使用默认值 0.0

4. **币种不存在**
   - 行为: 返回错误"未找到币种 XXX 的资金费率"，Get函数会记录警告并使用默认值 0.0

5. **缓存机制**
   - 缓存TTL: 5分钟
   - 缓存失效时自动更新
   - 更新失败时使用旧缓存（如果存在）

### 2. 持仓量 (Open Interest) 错误处理

**API**: 
- 主API: `GET https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT`
- 历史API: `GET https://fapi.binance.com/fapi/v1/openInterestHist?symbol=BTCUSDT&period=5m&limit=30`

**错误场景及处理**:

1. **主API网络错误**
   - 行为: 返回错误，Get函数会记录警告并使用默认值 `OIData{Latest: 0, Average: 0}`

2. **主API返回错误状态码**
   - 行为: 返回错误，Get函数会记录警告并使用默认值

3. **主API JSON解析错误**
   - 行为: 返回错误，Get函数会记录警告并使用默认值

4. **历史API失败（主API成功）**
   - 行为: **不影响主流程**
   - Latest值: 从主API获取
   - Average值: 使用Latest值（因为历史API失败）
   - 不返回错误

5. **历史API JSON解析错误**
   - 行为: 不影响主流程，Average使用Latest值

## Get函数中的错误处理

在 `market.Get()` 函数中：

```go
// 获取OI数据
oiData, err := getOpenInterestData(symbol)
if err != nil {
    log.Printf("⚠️  获取 %s 持仓量数据失败: %v，使用默认值", symbol, err)
    oiData = &OIData{Latest: 0, Average: 0}
}

// 获取Funding Rate
fundingRate, err := getFundingRate(symbol)
if err != nil {
    log.Printf("⚠️  获取 %s 资金费率失败: %v，使用默认值 0.0", symbol, err)
    fundingRate = 0.0
}
```

**关键点**:
- OI和资金费率获取失败**不会**导致整个Get函数失败
- 失败时会记录警告日志
- 使用合理的默认值继续执行

## 测试场景

### 测试1: OI获取失败
```go
// 使用不存在的币种
oiData, err := getOpenInterestData("INVALIDCOIN123USDT")
// 预期: err != nil
// Get函数中: 使用默认值 OIData{Latest: 0, Average: 0}
```

### 测试2: 资金费率获取失败（缓存为空）
```go
// 重置缓存为空
fundingRateCache = make(map[string]float64)
rate, err := getFundingRate("NONEXISTENTCOINUSDT")
// 预期: err != nil
// Get函数中: 使用默认值 0.0
```

### 测试3: 历史数据API失败
```go
// 主API成功，历史API失败
oiData, err := getOpenInterestData("BTCUSDT")
// 预期: err == nil
// Latest: 从主API获取
// Average: 等于Latest（因为历史API失败）
```

### 测试4: Get函数整体错误处理
```go
data, err := Get("BTCUSDT")
// 即使OI或资金费率失败，Get函数也应该成功返回
// 失败的字段会使用默认值
```

## 运行测试

```bash
# 运行所有错误处理测试
go test -v ./market -run TestErrorHandling

# 运行特定测试
go test -v ./market -run TestErrorHandling_OpenInterestFailure
go test -v ./market -run TestErrorHandling_FundingRateFailure
go test -v ./market -run TestErrorHandling_HistoryAPIFailure
go test -v ./market -run TestErrorHandling_GetFunction
```

## 总结

1. **容错性**: OI和资金费率获取失败不会导致整个Get函数失败
2. **可观测性**: 所有错误都会记录警告日志
3. **默认值**: 使用合理的默认值（0.0 和 OIData{0, 0}）
4. **缓存机制**: 资金费率使用缓存，减少API调用，提高容错性
5. **历史数据**: 历史数据获取失败不影响主流程

