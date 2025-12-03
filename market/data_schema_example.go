package market

import (
	"fmt"
	"strings"
)

// BuildUserPromptByConfig 根据配置构建User Prompt（示例实现）
// 这个函数展示了如何使用DataSchema和PromptDataConfig来构建不同策略的prompt
func BuildUserPromptByConfig(
	symbol string,
	data *Data,
	config *PromptDataConfig,
	schema *DataSchema,
	includeBTC bool,
	includeAccount bool,
) string {
	if data == nil || config == nil || schema == nil {
		return ""
	}

	var sb strings.Builder

	// 1. 基础信息（始终包含）
	sb.WriteString(fmt.Sprintf("**币种**: %s\n\n", symbol))

	// 2. 根据配置过滤数据
	filteredData := FilterDataBySchema(data, config, schema)

	// 3. 基础价格数据（必需）
	if price, ok := filteredData["current_price"].(float64); ok {
		sb.WriteString(fmt.Sprintf("💰 **当前价格**: %.4f\n", price))
	}
	if change1h, ok := filteredData["price_change_1h"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📈 **1小时变化**: %+.2f%%\n", change1h))
	}
	if change4h, ok := filteredData["price_change_4h"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📈 **4小时变化**: %+.2f%%\n", change4h))
	}
	if change1d, ok := filteredData["price_change_1d"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📈 **日线变化**: %+.2f%%\n\n", change1d))
	}

	// 4. 技术指标（必需）
	if ema20, ok := filteredData["ema20"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 **EMA20**: %.4f\n", ema20))
	}
	if macd, ok := filteredData["macd"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 **MACD**: %.4f\n", macd))
	}
	if rsi7, ok := filteredData["rsi7"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 **RSI7**: %.1f\n\n", rsi7))
	}

	// 5. 多时间框架数据（如果配置需要）
	if mtf, ok := filteredData["multi_timeframe"].(*MultiTimeframeData); ok && mtf != nil {
		sb.WriteString("⏰ **多时间框架**:\n")
		if mtf.Timeframe15m != nil {
			sb.WriteString(fmt.Sprintf("   • 15m: %s (强度%d)\n",
				mtf.Timeframe15m.TrendDirection, mtf.Timeframe15m.SignalStrength))
		}
		if mtf.Timeframe1h != nil {
			sb.WriteString(fmt.Sprintf("   • 1h:  %s (强度%d)\n",
				mtf.Timeframe1h.TrendDirection, mtf.Timeframe1h.SignalStrength))
		}
		if mtf.Timeframe4h != nil {
			sb.WriteString(fmt.Sprintf("   • 4h:  %s (强度%d)\n",
				mtf.Timeframe4h.TrendDirection, mtf.Timeframe4h.SignalStrength))
		}
		if mtf.Timeframe1d != nil {
			sb.WriteString(fmt.Sprintf("   • 1d:  %s (强度%d)\n\n",
				mtf.Timeframe1d.TrendDirection, mtf.Timeframe1d.SignalStrength))
		}
	}

	// 6. 斐波那契水平（如果配置需要）
	if fib, ok := filteredData["fibonacci"].(*FibLevels); ok && fib != nil {
		sb.WriteString("📐 **斐波那契水平**:\n")
		sb.WriteString(fmt.Sprintf("   • OTE区间: %.4f - %.4f\n", fib.Level618, fib.Level705))
		sb.WriteString(fmt.Sprintf("   • 0.5中线: %.4f\n\n", fib.Level500))
	}

	// 7. 市场结构（如果配置需要）
	if ms, ok := filteredData["market_structure"].(*MarketStructure); ok && ms != nil {
		sb.WriteString("🏗️ **市场结构**:\n")
		sb.WriteString(fmt.Sprintf("   • 偏向: %s\n", ms.CurrentBias))
		if len(ms.SwingHighs) > 0 && len(ms.SwingLows) > 0 {
			sb.WriteString(fmt.Sprintf("   • 最近波段: %.4f → %.4f\n\n",
				ms.SwingHighs[len(ms.SwingHighs)-1],
				ms.SwingLows[len(ms.SwingLows)-1]))
		}
	}

	// 8. 成交量分析（如果配置需要）
	if rvol, ok := filteredData["rvol"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 **相对成交量(RVol)**: %.2fx\n\n", rvol))
	}

	// 9. 形态识别（如果配置需要）
	if patterns, ok := filteredData["patterns"].(*PatternRecognition); ok && patterns != nil && len(patterns.Patterns) > 0 {
		sb.WriteString("🕯️ **形态识别**:\n")
		for _, p := range patterns.Patterns {
			sb.WriteString(fmt.Sprintf("   • %s (%s) - %s - 置信度%.0f%%\n",
				p.DisplayName, p.Timeframe, p.Side, p.Confidence*100))
		}
		sb.WriteString("\n")
	}

	// 10. 市场状态（如果配置需要）
	if condition, ok := filteredData["market_condition"].(*MarketCondition); ok && condition != nil {
		sb.WriteString(fmt.Sprintf("🌊 **市场状态**: %s (置信度%d%%)\n\n",
			condition.Condition, condition.Confidence))
	}

	// 11. 持仓量数据（如果配置需要）
	if oi, ok := filteredData["open_interest"].(*OIData); ok && oi != nil {
		sb.WriteString(fmt.Sprintf("📈 **持仓量**: %.0f (平均%.0f)\n", oi.Latest, oi.Average))
		if oi.Change1h != 0 {
			sb.WriteString(fmt.Sprintf("   • 1h变化: %+.2f%%\n", oi.Change1h))
		}
		if oi.Change4h != 0 {
			sb.WriteString(fmt.Sprintf("   • 4h变化: %+.2f%%\n\n", oi.Change4h))
		}
	}

	return sb.String()
}

// ExampleUsage 使用示例
func ExampleUsage() {
	// 1. 获取数据模式
	schema := GetDefaultDataSchema()

	// 2. 获取林凡多空策略的配置
	config := GetPromptDataConfig("林凡_多空")

	// 3. 获取市场数据
	data, _ := Get("BTCUSDT")

	// 4. 根据配置构建User Prompt
	userPrompt := BuildUserPromptByConfig("BTCUSDT", data, config, schema, true, true)

	fmt.Println(userPrompt)
}

