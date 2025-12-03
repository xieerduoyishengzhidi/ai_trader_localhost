package market

/*
#cgo LDFLAGS: -lta_lib
#include <ta_libc.h>
#include <stdlib.h>
*/
import "C"
import (
	"fmt"
	"math"
	"time"
	"unsafe"
)

// detectCandlestickPatterns 检测K线形态
// ⚠️ 注意：某些形态需要多个指标确认，函数会检查K线数量和数据完整性
func detectCandlestickPatterns(klines []Kline, timeframe string) []CandlestickPattern {
	if len(klines) == 0 {
		return nil
	}

	// 提取OHLC数据
	open := make([]float64, len(klines))
	high := make([]float64, len(klines))
	low := make([]float64, len(klines))
	close := make([]float64, len(klines))

	for i, k := range klines {
		open[i] = k.Open
		high[i] = k.High
		low[i] = k.Low
		close[i] = k.Close
	}

	patterns := []CandlestickPattern{}

	// 定义要检测的形态列表（常用形态）及其对应的TA-Lib函数和最小K线数
	// ⚠️ 注意：某些形态需要多个指标确认，这里只列出基础形态
	patternConfigs := []struct {
		name    string
		fnID    int // TA-Lib函数ID（使用整数常量）
		minBars int
	}{
		// 单根K线形态（至少1根）
		{"CDLHAMMER", 21, 1},         // TA_CDLHAMMER
		{"CDLSHOOTINGSTAR", 22, 1},   // TA_CDLSHOOTINGSTAR
		{"CDLDOJI", 23, 1},           // TA_CDLDOJI
		{"CDLHANGINGMAN", 24, 1},     // TA_CDLHANGINGMAN
		{"CDLINVERTEDHAMMER", 25, 1}, // TA_CDLINVERTEDHAMMER
		{"CDLSPINNINGTOP", 26, 1},    // TA_CDLSPINNINGTOP
		{"CDLMARUBOZU", 27, 1},       // TA_CDLMARUBOZU

		// 双根K线形态（至少2根）
		{"CDLENGULFING", 28, 2},      // TA_CDLENGULFING
		{"CDLHARAMI", 29, 2},         // TA_CDLHARAMI
		{"CDLPIERCING", 30, 2},       // TA_CDLPIERCING
		{"CDLDARKCLOUDCOVER", 31, 2}, // TA_CDLDARKCLOUDCOVER

		// 三根K线形态（至少3根）
		{"CDLMORNINGSTAR", 32, 3},    // TA_CDLMORNINGSTAR
		{"CDLEVENINGSTAR", 33, 3},    // TA_CDLEVENINGSTAR
		{"CDL3BLACKCROWS", 34, 3},    // TA_CDL3BLACKCROWS
		{"CDL3WHITESOLDIERS", 35, 3}, // TA_CDL3WHITESOLDIERS
		{"CDL3INSIDE", 36, 3},        // TA_CDL3INSIDE
		{"CDL3LINESTRIKE", 37, 3},    // TA_CDL3LINESTRIKE
	}

	// 计算平均成交量（用于置信度计算）
	avgVol := calculateAverageVolume(klines)

	// 初始化TA-Lib（如果还没有初始化）
	C.TA_Initialize()

	// 检测每个形态
	for _, config := range patternConfigs {
		// 检查是否有足够的K线数据
		if len(klines) < config.minBars {
			continue // 跳过需要更多K线的形态
		}

		// 调用TA-Lib C库函数
		result := callTALibCdlFunction(config.fnID, open, high, low, close)
		if len(result) == 0 {
			continue
		}

		// 检查最新一根K线是否有形态信号
		latestIndex := len(result) - 1
		if latestIndex < 0 {
			continue
		}

		latestSignal := result[latestIndex]

		// 只记录有信号的形态（非零值）
		// TA-Lib返回值：100=看涨, -100=看跌, 0=无信号
		if latestSignal != 0 {
			// 计算对应的K线索引
			klineIndex := len(klines) - 1

			// 计算置信度（包含量能分析）
			confidence := calculateConfidence(latestSignal, klines, klineIndex, avgVol)

			// 转换为语义化信号（需要在生成note之前定义）
			side := "neutral"
			if latestSignal > 0 {
				side = "bullish"
			} else if latestSignal < 0 {
				side = "bearish"
			}

			// 生成备注：包含量能信息和形态含义
			note := ""
			if klineIndex >= 0 && klineIndex < len(klines) {
				currentVol := klines[klineIndex].Volume
				volInfo := ""
				if avgVol > 0 {
					volRatio := currentVol / avgVol
					if volRatio > 2.0 {
						volInfo = fmt.Sprintf("量能: %.1fx (双倍放量，主力进场)", volRatio)
					} else if volRatio > 1.5 {
						volInfo = fmt.Sprintf("量能: %.1fx (明显放量)", volRatio)
					} else if volRatio > 1.2 {
						volInfo = fmt.Sprintf("量能: %.1fx (温和放量)", volRatio)
					} else if volRatio < 0.5 {
						volInfo = fmt.Sprintf("量能: %.1fx (严重缩量，警惕假突破)", volRatio)
					} else if volRatio < 0.8 {
						volInfo = fmt.Sprintf("量能: %.1fx (缩量，可能假突破)", volRatio)
					} else {
						volInfo = fmt.Sprintf("量能: %.1fx (正常)", volRatio)
					}
				}

				// 获取形态含义
				patternMeaning := getPatternMeaning(config.name, side)

				// 组合量能和形态含义
				if volInfo != "" && patternMeaning != "" {
					note = fmt.Sprintf("%s | 形态含义: %s", volInfo, patternMeaning)
				} else if volInfo != "" {
					note = volInfo
				} else if patternMeaning != "" {
					note = fmt.Sprintf("形态含义: %s", patternMeaning)
				}
			}

			pattern := CandlestickPattern{
				Name:        config.name,
				DisplayName: getPatternDisplayName(config.name),
				Signal:      int(latestSignal), // 保留用于兼容
				Side:        side,              // 语义化信号（推荐使用）
				Timeframe:   timeframe,
				Index:       klineIndex,
				Confidence:  confidence,
				Note:        note, // 可选备注
			}
			patterns = append(patterns, pattern)
		}
	}

	return patterns
}

// callTALibCdlFunction 调用TA-Lib C库的形态识别函数
// 使用通用的TA_CDL函数接口
func callTALibCdlFunction(fnID int, open, high, low, close []float64) []float64 {
	if len(open) == 0 || len(high) == 0 || len(low) == 0 || len(close) == 0 {
		return nil
	}

	// 准备C数组
	cOpen := make([]C.double, len(open))
	cHigh := make([]C.double, len(high))
	cLow := make([]C.double, len(low))
	cClose := make([]C.double, len(close))

	for i := range open {
		cOpen[i] = C.double(open[i])
		cHigh[i] = C.double(high[i])
		cLow[i] = C.double(low[i])
		cClose[i] = C.double(close[i])
	}

	startIdx := C.int(0)
	endIdx := C.int(len(open) - 1)
	outBegIdx := C.int(0)
	outNBElement := C.int(0)

	// 分配输出数组（TA-Lib CDL函数返回int类型，不是double）
	outReal := make([]C.int, len(open))
	cOutReal := (*C.int)(unsafe.Pointer(&outReal[0]))

	// 根据函数ID调用对应的TA-Lib函数
	// 这里使用函数指针表，简化调用
	var retCode C.TA_RetCode

	switch fnID {
	case 21: // CDLHAMMER
		retCode = C.TA_CDLHAMMER(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 22: // CDLSHOOTINGSTAR
		retCode = C.TA_CDLSHOOTINGSTAR(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 23: // CDLDOJI
		retCode = C.TA_CDLDOJI(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 24: // CDLHANGINGMAN
		retCode = C.TA_CDLHANGINGMAN(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 25: // CDLINVERTEDHAMMER
		retCode = C.TA_CDLINVERTEDHAMMER(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 26: // CDLSPINNINGTOP
		retCode = C.TA_CDLSPINNINGTOP(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 27: // CDLMARUBOZU
		retCode = C.TA_CDLMARUBOZU(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 28: // CDLENGULFING
		retCode = C.TA_CDLENGULFING(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 29: // CDLHARAMI
		retCode = C.TA_CDLHARAMI(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 30: // CDLPIERCING
		retCode = C.TA_CDLPIERCING(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 31: // CDLDARKCLOUDCOVER (需要penetration参数，默认0.5即50%)
		penetration := C.double(0.5)
		retCode = C.TA_CDLDARKCLOUDCOVER(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], penetration, &outBegIdx, &outNBElement, cOutReal)
	case 32: // CDLMORNINGSTAR (需要penetration参数，默认0.3即30%)
		penetration := C.double(0.3)
		retCode = C.TA_CDLMORNINGSTAR(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], penetration, &outBegIdx, &outNBElement, cOutReal)
	case 33: // CDLEVENINGSTAR (需要penetration参数，默认0.3即30%)
		penetration := C.double(0.3)
		retCode = C.TA_CDLEVENINGSTAR(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], penetration, &outBegIdx, &outNBElement, cOutReal)
	case 34: // CDL3BLACKCROWS
		retCode = C.TA_CDL3BLACKCROWS(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 35: // CDL3WHITESOLDIERS
		retCode = C.TA_CDL3WHITESOLDIERS(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 36: // CDL3INSIDE
		retCode = C.TA_CDL3INSIDE(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	case 37: // CDL3LINESTRIKE
		retCode = C.TA_CDL3LINESTRIKE(startIdx, endIdx, &cOpen[0], &cHigh[0], &cLow[0], &cClose[0], &outBegIdx, &outNBElement, cOutReal)
	default:
		return nil
	}

	if retCode != C.TA_SUCCESS {
		return nil
	}

	// 转换结果
	if int(outNBElement) == 0 {
		return nil
	}

	// TA-Lib返回的结果从outBegIdx开始，需要正确映射到原始数组
	// 创建一个与输入长度相同的数组，前面填充0
	result := make([]float64, len(open))
	// 前面的数据填充0（表示没有形态）
	for i := 0; i < int(outBegIdx); i++ {
		result[i] = 0.0
	}
	// 填充实际结果（从outBegIdx位置开始）
	// TA-Lib CDL函数返回int类型：100=看涨, -100=看跌, 0=无信号
	for i := 0; i < int(outNBElement); i++ {
		if int(outBegIdx)+i < len(result) {
			result[int(outBegIdx)+i] = float64(outReal[i])
		}
	}

	return result
}

// calculateConfidence 计算形态置信度（包含量能分析）
// ⚠️ 关键：必须传入平均成交量，量能是判断形态真实性的核心指标
func calculateConfidence(signal float64, klines []Kline, index int, avgVol float64) float64 {
	if len(klines) == 0 || index < 0 || index >= len(klines) {
		return 0.0
	}

	// 1. 基础置信度：根据信号强度
	confidence := 0.5

	// 如果信号很强（绝对值=100），增加置信度
	if math.Abs(signal) == 100 {
		confidence = 0.7
	}

	// 2. 实体大小加分
	k := klines[index]
	totalRange := k.High - k.Low
	if totalRange > 0 {
		bodySize := math.Abs(k.Close - k.Open)
		bodyRatio := bodySize / totalRange
		// 实体占60%以上，加分
		if bodyRatio > 0.6 {
			confidence += 0.1
		} else {
			// 实体较小，略微减分
			confidence += bodyRatio * 0.1
		}
	}

	// 3. 🔴 【关键改进】量能确认（最重要的一步）
	// 在加密货币市场，缩量的反转形态通常是假突破（Fakeout）
	currentVol := k.Volume
	if avgVol > 0 {
		volRatio := currentVol / avgVol

		if volRatio > 2.0 {
			// 双倍放量，极大加分（主力进场信号）
			confidence += 0.3
		} else if volRatio > 1.5 {
			// 明显放量，加分
			confidence += 0.15
		} else if volRatio > 1.2 {
			// 温和放量，小幅加分
			confidence += 0.05
		} else if volRatio < 0.8 {
			// 缩量，减分（可能是假突破）
			confidence -= 0.2
		} else if volRatio < 0.5 {
			// 严重缩量，大幅减分
			confidence -= 0.3
		}
	} else {
		// 如果没有平均成交量数据，保守处理
		// 对于反转形态，如果没有量能确认，降低置信度
		if math.Abs(signal) == 100 {
			confidence -= 0.1 // 反转形态需要量能确认
		}
	}

	// 4. 归一化限制（确保在合理范围内）
	if confidence > 1.0 {
		confidence = 1.0
	}
	if confidence < 0.1 {
		confidence = 0.1 // 最低保留10%置信度
	}

	// 保留两位小数
	return math.Round(confidence*100) / 100
}

// calculateAverageVolume 计算平均成交量
func calculateAverageVolume(klines []Kline) float64 {
	if len(klines) == 0 {
		return 0.0
	}

	// 使用最近20根K线的平均成交量（如果不足20根，使用全部）
	lookback := 20
	if len(klines) < lookback {
		lookback = len(klines)
	}

	start := len(klines) - lookback
	sum := 0.0
	for i := start; i < len(klines); i++ {
		sum += klines[i].Volume
	}

	return sum / float64(lookback)
}

// getPatternDisplayName 获取形态的中文显示名称
func getPatternDisplayName(name string) string {
	displayNames := map[string]string{
		"CDLHAMMER":         "锤子线",
		"CDLSHOOTINGSTAR":   "流星",
		"CDLDOJI":           "十字星",
		"CDLHANGINGMAN":     "上吊线",
		"CDLINVERTEDHAMMER": "倒锤子",
		"CDLSPINNINGTOP":    "纺锤线",
		"CDLMARUBOZU":       "光头光脚",
		"CDLENGULFING":      "吞噬形态",
		"CDLHARAMI":         "孕线",
		"CDLPIERCING":       "刺透形态",
		"CDLDARKCLOUDCOVER": "乌云盖顶",
		"CDLMORNINGSTAR":    "晨星",
		"CDLEVENINGSTAR":    "暮星",
		"CDL3BLACKCROWS":    "三只乌鸦",
		"CDL3WHITESOLDIERS": "三白兵",
		"CDL3INSIDE":        "三内升/降",
		"CDL3LINESTRIKE":    "三线打击",
	}

	if displayName, ok := displayNames[name]; ok {
		return displayName
	}
	return name // 如果没有找到，返回原名
}

// getPatternMeaning 获取形态的含义说明
func getPatternMeaning(patternName, side string) string {
	meanings := map[string]map[string]string{
		"CDLHAMMER": {
			"bullish": "看涨反转形态，出现在下跌趋势底部，下影线长表示买盘强劲",
			"bearish": "看跌反转形态，出现在上涨趋势顶部，下影线长但收盘价低",
		},
		"CDLSHOOTINGSTAR": {
			"bullish": "看涨反转形态，出现在下跌趋势中，上影线长表示卖压被消化",
			"bearish": "看跌反转形态，出现在上涨趋势顶部，上影线长表示卖压强劲",
		},
		"CDLDOJI": {
			"bullish": "多空平衡，出现在关键位置可能预示反转",
			"bearish": "多空平衡，出现在关键位置可能预示反转",
		},
		"CDLHANGINGMAN": {
			"bullish": "看涨反转形态，出现在下跌趋势中",
			"bearish": "看跌反转形态，出现在上涨趋势顶部，需确认",
		},
		"CDLINVERTEDHAMMER": {
			"bullish": "看涨反转形态，出现在下跌趋势底部，上影线长表示买盘尝试",
			"bearish": "看跌反转形态，出现在上涨趋势顶部",
		},
		"CDLSPINNINGTOP": {
			"bullish": "多空争夺激烈，出现在关键位置需关注",
			"bearish": "多空争夺激烈，出现在关键位置需关注",
		},
		"CDLMARUBOZU": {
			"bullish": "强势看涨，实体大无影线，表示单边上涨动能强",
			"bearish": "强势看跌，实体大无影线，表示单边下跌动能强",
		},
		"CDLENGULFING": {
			"bullish": "看涨吞噬，第二根K线完全吞没第一根，反转信号强",
			"bearish": "看跌吞噬，第二根K线完全吞没第一根，反转信号强",
		},
		"CDLHARAMI": {
			"bullish": "看涨孕线，小实体被大实体包含，可能预示反转",
			"bearish": "看跌孕线，小实体被大实体包含，可能预示反转",
		},
		"CDLPIERCING": {
			"bullish": "刺透形态，第二根阳线刺入第一根阴线实体，看涨反转",
			"bearish": "看跌形态",
		},
		"CDLDARKCLOUDCOVER": {
			"bullish": "看涨形态",
			"bearish": "乌云盖顶，第二根阴线覆盖第一根阳线，看跌反转信号",
		},
		"CDLMORNINGSTAR": {
			"bullish": "晨星形态，三根K线组合，出现在底部预示看涨反转",
			"bearish": "看跌形态",
		},
		"CDLEVENINGSTAR": {
			"bullish": "看涨形态",
			"bearish": "暮星形态，三根K线组合，出现在顶部预示看跌反转",
		},
		"CDL3BLACKCROWS": {
			"bullish": "看涨形态",
			"bearish": "三只乌鸦，连续三根阴线，看跌信号强烈",
		},
		"CDL3WHITESOLDIERS": {
			"bullish": "三白兵，连续三根阳线，看涨信号强烈",
			"bearish": "看跌形态",
		},
		"CDL3INSIDE": {
			"bullish": "三内升，看涨反转形态",
			"bearish": "三内降，看跌反转形态",
		},
		"CDL3LINESTRIKE": {
			"bullish": "三线打击，看涨反转形态",
			"bearish": "三线打击，看跌反转形态",
		},
	}

	if patternMeanings, ok := meanings[patternName]; ok {
		if meaning, ok := patternMeanings[side]; ok {
			return meaning
		}
		// 如果没有找到对应side的含义，返回第一个可用的
		for _, m := range patternMeanings {
			return m
		}
	}
	return "" // 如果没有找到，返回空字符串
}

// aggregatePatterns 汇总所有时间框架的形态识别结果
func aggregatePatterns(multiTimeframe *MultiTimeframeData) *PatternRecognition {
	if multiTimeframe == nil {
		return nil
	}

	allPatterns := []CandlestickPattern{}

	// 收集所有时间框架的形态
	timeframes := []struct {
		name string
		tf   *TimeframeData
	}{
		{"15m", multiTimeframe.Timeframe15m},
		{"1h", multiTimeframe.Timeframe1h},
		{"4h", multiTimeframe.Timeframe4h},
		{"1d", multiTimeframe.Timeframe1d},
	}

	for _, tf := range timeframes {
		if tf.tf != nil && len(tf.tf.Patterns) > 0 {
			allPatterns = append(allPatterns, tf.tf.Patterns...)
		}
	}

	// 如果没有识别到任何形态，返回nil（稀疏输出）
	if len(allPatterns) == 0 {
		return nil
	}

	return &PatternRecognition{
		Patterns:  allPatterns,
		Timestamp: time.Now().UnixMilli(),
	}
}
