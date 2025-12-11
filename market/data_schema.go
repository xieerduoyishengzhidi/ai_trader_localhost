package market

import (
	"fmt"
	"strings"
)

// DataSchema 数据模式定义 - 用于描述哪些数据字段需要传递给AI
type DataSchema struct {
	// 数据分类
	Categories []DataCategory `json:"categories"`
	// 字段描述映射（字段名 -> 含义说明）
	FieldDescriptions map[string]string `json:"field_descriptions"`
}

// DataCategory 数据分类
type DataCategory struct {
	ID          string   `json:"id"`          // 分类ID（如 "basic_price", "technical_indicators"）
	Name        string   `json:"name"`        // 分类名称（中文）
	Description string   `json:"description"` // 分类说明
	Fields      []string `json:"fields"`      // 该分类包含的字段列表
	Required    bool     `json:"required"`    // 是否必需
	Timeframes  []string `json:"timeframes"`  // 适用的时间框架（如 ["15m", "1h", "4h", "1d"]）
}

// PromptDataConfig Prompt数据配置 - 定义某个prompt需要哪些数据
type PromptDataConfig struct {
	PromptName       string   `json:"prompt_name"`       // Prompt名称（如 "林凡_多空"）
	DataCategories   []string `json:"data_categories"`   // 需要的数据分类ID列表
	CustomFields     []string `json:"custom_fields"`     // 自定义字段列表（覆盖分类）
	Format           string   `json:"format"`            // 输出格式："full" | "compact" | "json" | "markdown"
	IncludeBTC       bool     `json:"include_btc"`       // 是否包含BTC数据
	IncludeAccount   bool     `json:"include_account"`   // 是否包含账户信息
	IncludePositions bool     `json:"include_positions"` // 是否包含持仓信息
	IncludeRAG       bool     `json:"include_rag"`       // 是否包含RAG历史观点
	// 展示控制（默认true，便于向后兼容）
	ShowFibLevels  bool `json:"show_fib_levels"`  // 是否展示斐波那契各水平数值
	ShowOTE        bool `json:"show_ote"`         // 是否展示OTE区间/位置提示
	ShowRecentMove bool `json:"show_recent_move"` // 是否展示15m最新价格变动
}

// GetDefaultDataSchema 获取默认数据模式定义
func GetDefaultDataSchema() *DataSchema {
	return &DataSchema{
		Categories: []DataCategory{
			// 1. 基础价格数据
			{
				ID:          "basic_price",
				Name:        "基础价格",
				Description: "当前价格和价格变化百分比",
				Fields:      []string{"CurrentPrice", "PriceChange1h", "PriceChange4h", "PriceChange1d"},
				Required:    true,
				Timeframes:  []string{"15m", "1h", "4h", "1d"},
			},
			// 2. 技术指标（主时间框架）
			{
				ID:          "technical_indicators",
				Name:        "技术指标",
				Description: "EMA、MACD、RSI等主要技术指标",
				Fields:      []string{"CurrentEMA20", "CurrentMACD", "CurrentRSI7"},
				Required:    true,
				Timeframes:  []string{"15m"},
			},
			// 3. 多时间框架数据
			{
				ID:          "multi_timeframe",
				Name:        "多时间框架",
				Description: "15m、1h、4h、1d各时间框架的趋势、信号强度、技术指标",
				Fields:      []string{"MultiTimeframe"},
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h", "1d"},
			},
			// 4. 持仓量数据
			{
				ID:          "open_interest",
				Name:        "持仓量",
				Description: "当前持仓量、平均值、各时间框架变化率",
				Fields:      []string{"OpenInterest"},
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h", "1d"},
			},
			// 5. 资金费率数据
			{
				ID:          "funding_rate",
				Name:        "资金费率",
				Description: "当前资金费率、各时间框架变化率",
				Fields:      []string{"FundingRate"},
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h", "1d"},
			},
			// 6. 长期数据
			{
				ID:          "longer_term",
				Name:        "长期数据",
				Description: "4小时框架的EMA、ATR、成交量、MACD序列、RSI序列",
				Fields:      []string{"LongerTermContext"},
				Required:    false,
				Timeframes:  []string{"4h"},
			},
			// 7. 市场结构
			{
				ID:          "market_structure",
				Name:        "市场结构",
				Description: "波段高点/低点、当前偏向（bullish/bearish/neutral）。每个时间框架（15m/1h/4h/1d）都有独立的市场结构，Data.MarketStructure为日线结构（向后兼容）",
				Fields:      []string{"MarketStructure"},
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h", "1d"}, // 每个时间框架都有独立的市场结构
			},
			// 8. 斐波那契水平
			{
				ID:          "fibonacci",
				Name:        "斐波那契",
				Description: "0.236、0.382、0.5、0.618、0.705、0.786等回撤水平，OTE区间",
				Fields:      []string{"FibLevels"},
				Required:    false,
				Timeframes:  []string{"1d"},
			},
			// 9. 形态识别
			{
				ID:          "candlestick_patterns",
				Name:        "蜡烛图形态",
				Description: "TA-Lib识别的K线形态（吞噬、十字星、锤子等）",
				Fields:      []string{"PatternRecognition"},
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h", "1d"},
			},
			// 10. 成交量分析
			{
				ID:          "volume_analysis",
				Name:        "成交量分析",
				Description: "相对成交量（RVol）、成交量趋势",
				Fields:      []string{"RVol"},
				Required:    false,
				Timeframes:  []string{"15m"},
			},
			// 11. 价格偏离度
			{
				ID:          "price_deviation",
				Name:        "价格偏离度",
				Description: "EMA偏离度、价格相对EMA的位置",
				Fields:      []string{"EMADeviation"},
				Required:    false,
				Timeframes:  []string{"15m"},
			},
			// 12. 关键流动性
			{
				ID:          "liquidity_levels",
				Name:        "关键流动性",
				Description: "前日高点（PDH）、前日低点（PDL）",
				Fields:      []string{"PDH", "PDL"},
				Required:    false,
				Timeframes:  []string{"1d"},
			},
			// 13. 市场状态
			{
				ID:          "market_condition",
				Name:        "市场状态",
				Description: "趋势市/震荡市/波动市判断及置信度",
				Fields:      []string{"MarketCondition"}, // 这是计算得出的，不是Data字段
				Required:    false,
				Timeframes:  []string{"15m", "1h", "4h"},
			},
		},
		FieldDescriptions: map[string]string{
			// 基础价格
			"CurrentPrice":  "当前价格（最新成交价）",
			"PriceChange1h": "1小时价格变化百分比（%）",
			"PriceChange4h": "4小时价格变化百分比（%）",
			"PriceChange1d": "日线价格变化百分比（%）",

			// 技术指标
			"CurrentEMA20": "20周期指数移动平均线（主时间框架）",
			"CurrentMACD":  "MACD指标值（12-26周期）",
			"CurrentRSI7":  "7周期相对强弱指标（0-100）",

			// 多时间框架
			"MultiTimeframe": "多时间框架数据对象，包含15m/1h/4h/1d各框架的：价格、EMA20/EMA50、MACD、RSI7/RSI14、ATR14、成交量、趋势方向、信号强度、形态识别、市场结构（波段高低点）",

			// 持仓量
			"OpenInterest": "持仓量数据对象，包含：当前值、平均值、15m/1h/4h/1d变化率（%）",

			// 资金费率
			"FundingRate": "资金费率数据对象，包含：当前费率、15m/1h/4h/1d变化率（基点）",

			// 长期数据
			"LongerTermContext": "长期数据对象（基于4h），包含：EMA20/EMA50、ATR3/ATR14、成交量、MACD序列、RSI14序列",

			// 市场结构
			"MarketStructure": "市场结构对象，包含：波段高点数组、波段低点数组、当前偏向（bullish/bearish/neutral）、斐波那契水平。每个时间框架（15m/1h/4h/1d）都有独立的市场结构，Data.MarketStructure为日线结构（向后兼容）",

			// 斐波那契
			"FibLevels": "斐波那契水平对象，包含：0.236/0.382/0.5/0.618/0.705/0.786水平、波段高点/低点、趋势方向",

			// 形态识别
			"PatternRecognition": "形态识别对象，包含：币种、形态数组（名称、信号方向、时间框架、置信度）、时间戳",

			// 成交量分析
			"RVol": "相对成交量：当前K线成交量 / 过去20根K线平均成交量（>1.5表示放量，<0.5表示缩量）",

			// 价格偏离度
			"EMADeviation": "EMA偏离度：(当前价格 - EMA20) / EMA20 * 100（%），正数表示价格在EMA上方",

			// 关键流动性
			"PDH": "前日高点（Previous Day High）",
			"PDL": "前日低点（Previous Day Low）",

			// 市场状态（计算得出）
			"MarketCondition": "市场状态：trending（趋势市）/ranging（震荡市）/volatile（波动市），包含置信度（0-100）",
		},
	}
}

// GetPromptDataConfig 获取指定prompt的数据配置
func GetPromptDataConfig(promptName string) *PromptDataConfig {
	configs := map[string]*PromptDataConfig{
		// 林凡多空策略配置
		"1bxxx": {
			PromptName: "1bxxx",
			DataCategories: []string{
				"basic_price",          // 基礎價格 (PriceChange)
				"technical_indicators", // 主圖指標 (EMA20, MACD)
				"multi_timeframe",      // 多週期數據 (包含 ATR14, 4H/1H 趨勢)
				"market_structure",     // 市場結構 (高低點)
				"candlestick_patterns", // K線形態 (識別光頭光腳/吞噬)
				"volume_analysis",      // 成交量分析 (RVol 必需)
				"open_interest",        // 持倉量分析 (OI 必需 - 修正了這裡)
				"funding_rate",         // 資金費率 (修正了這裡，原為 FundingRate)
				"market_condition",     // 市場狀態 (趨勢/震盪)
			},
			Format:           "markdown",
			IncludeBTC:       true, // 必需：用於判斷【崩盤/拉升模式】
			IncludeAccount:   true, // 必需：用於計算保證金和開倉數量
			IncludePositions: true, // 必需：用於判斷持倉上限和先平後開
			IncludeRAG:       false,
		},
		// 林凡只做多策略配置
		"林凡_只做多": {
			PromptName: "林凡_只做多",
			DataCategories: []string{
				"basic_price",
				"technical_indicators",
				"multi_timeframe",
				"fibonacci",            // OTE回调入场
				"candlestick_patterns", // S2突破信号
				"volume_analysis",      // 放量确认
				"market_condition",     // 避免震荡市
			},
			Format:           "markdown",
			IncludeBTC:       true,
			IncludeAccount:   true,
			IncludePositions: true,
			IncludeRAG:       true,
		},

		// 默认配置（完整数据）
		"default": {
			PromptName: "default",
			DataCategories: []string{
				"basic_price",
				"technical_indicators",
				"multi_timeframe",
				"open_interest",
				"funding_rate",
				"longer_term",
				"market_structure",
				"fibonacci",
				"candlestick_patterns",
				"volume_analysis",
				"price_deviation",
				"liquidity_levels",
				"market_condition",
			},
			Format:           "markdown",
			IncludeBTC:       true,
			IncludeAccount:   true,
			IncludePositions: true,
			IncludeRAG:       false,
		},
	}

	if config, ok := configs[promptName]; ok {
		return config
	}
	return configs["default"]
}

// GetDataConfigByTraderName 根据prompt模板名称获取数据配置
// 简化逻辑：直接使用prompt模板名称映射到配置，不做复杂提取
// 例如: "1bxxx" -> 直接查找 "1bxxx" 配置
func GetDataConfigByTraderName(traderName string, promptTemplateName string) *PromptDataConfig {
	// 优先使用prompt模板名称（如果提供）
	if promptTemplateName != "" && promptTemplateName != "default" {
		// 直接使用模板名称查找配置
		if config := GetPromptDataConfig(promptTemplateName); config != nil && config.PromptName != "default" {
			return config
		}
	}

	// 如果提供了交易员名称，尝试匹配
	if traderName != "" {
		// 直接匹配交易员名称
		if config := GetPromptDataConfig(traderName); config != nil && config.PromptName != "default" {
			return config
		}
	}

	// 默认返回完整数据配置
	return GetPromptDataConfig("default")
}

// FilterDataBySchema 根据数据模式过滤数据，只返回需要的字段
func FilterDataBySchema(data *Data, config *PromptDataConfig, schema *DataSchema) map[string]interface{} {
	if data == nil || config == nil || schema == nil {
		return nil
	}

	result := make(map[string]interface{})
	fieldSet := make(map[string]bool)

	// 收集需要的字段
	for _, categoryID := range config.DataCategories {
		for _, category := range schema.Categories {
			if category.ID == categoryID {
				for _, field := range category.Fields {
					fieldSet[field] = true
				}
			}
		}
	}

	// 添加自定义字段
	for _, field := range config.CustomFields {
		fieldSet[field] = true
	}

	// 根据字段集合提取数据
	if fieldSet["CurrentPrice"] {
		result["current_price"] = data.CurrentPrice
	}
	if fieldSet["PriceChange1h"] {
		result["price_change_1h"] = data.PriceChange1h
	}
	if fieldSet["PriceChange4h"] {
		result["price_change_4h"] = data.PriceChange4h
	}
	if fieldSet["PriceChange1d"] {
		result["price_change_1d"] = data.PriceChange1d
	}
	if fieldSet["CurrentEMA20"] {
		result["ema20"] = data.CurrentEMA20
	}
	if fieldSet["CurrentMACD"] {
		result["macd"] = data.CurrentMACD
	}
	if fieldSet["CurrentRSI7"] {
		result["rsi7"] = data.CurrentRSI7
	}
	if fieldSet["MultiTimeframe"] {
		result["multi_timeframe"] = data.MultiTimeframe
	}
	if fieldSet["OpenInterest"] {
		result["open_interest"] = data.OpenInterest
	}
	if fieldSet["FundingRate"] {
		result["funding_rate"] = data.FundingRate
	}
	if fieldSet["LongerTermContext"] {
		result["longer_term"] = data.LongerTermContext
	}
	if fieldSet["MarketStructure"] {
		result["market_structure"] = data.MarketStructure
	}
	if fieldSet["FibLevels"] {
		result["fibonacci"] = data.FibLevels
	}
	if fieldSet["PatternRecognition"] {
		result["patterns"] = data.PatternRecognition
	}
	if fieldSet["RVol"] {
		result["rvol"] = data.RVol
	}
	if fieldSet["EMADeviation"] {
		result["ema_deviation"] = data.EMADeviation
	}
	if fieldSet["PDH"] {
		result["pdh"] = data.PDH
	}
	if fieldSet["PDL"] {
		result["pdl"] = data.PDL
	}

	// 市场状态是计算得出的
	if fieldSet["MarketCondition"] {
		result["market_condition"] = DetectMarketCondition(data)
	}

	return result
}

// FormatDataByConfig 根据配置格式化市场数据为字符串
func FormatDataByConfig(data *Data, config *PromptDataConfig, schema *DataSchema) string {
	if data == nil || config == nil || schema == nil {
		return ""
	}

	// 展示开关（默认开启，保持向后兼容）
	showFib := true
	showOTE := true
	showRecentMove := true
	if !config.ShowFibLevels {
		showFib = false
	}
	if !config.ShowOTE {
		showOTE = false
	}
	if !config.ShowRecentMove {
		showRecentMove = false
	}

	var sb strings.Builder
	filteredData := FilterDataBySchema(data, config, schema)

	// 基础价格数据（必需）
	if price, ok := filteredData["current_price"].(float64); ok {
		sb.WriteString(fmt.Sprintf("💰 当前价格: %.4f", price))
		if change1h, ok := filteredData["price_change_1h"].(float64); ok {
			sb.WriteString(fmt.Sprintf(" | 1h: %+.2f%%", change1h))
		}
		if change4h, ok := filteredData["price_change_4h"].(float64); ok {
			sb.WriteString(fmt.Sprintf(" | 4h: %+.2f%%", change4h))
		}
		if change1d, ok := filteredData["price_change_1d"].(float64); ok {
			sb.WriteString(fmt.Sprintf(" | 1d: %+.2f%%", change1d))
		}
		sb.WriteString("\n")
	}

	// 技术指标（必需）
	if ema20, ok := filteredData["ema20"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 EMA20: %.4f", ema20))
		if macd, ok := filteredData["macd"].(float64); ok {
			sb.WriteString(fmt.Sprintf(" | MACD: %.4f", macd))
		}
		if rsi7, ok := filteredData["rsi7"].(float64); ok {
			sb.WriteString(fmt.Sprintf(" | RSI7: %.1f", rsi7))
		}
		sb.WriteString("\n")
	}

	// 多时间框架数据
	if mtf, ok := filteredData["multi_timeframe"].(*MultiTimeframeData); ok && mtf != nil {
		sb.WriteString("⏰ 多时间框架: (趋势方向=bullish看涨/bearish看跌/neutral中性, 强度=0-100信号强度, ATR14=波动率用于止损止盈计算)\n")
		sb.WriteString("   ⚠️ 波段高低点数组顺序: 从前向后(最早→最新), 最后一个元素=最新波段, 第一个元素=最早波段\n")
		sb.WriteString("   ⚠️ 结构说明: 高点抬高+低点抬高=上升趋势, 高点降低+低点降低=下降趋势, 高点=阻力位, 低点=支撑位\n")
		if mtf.Timeframe15m != nil {
			sb.WriteString(fmt.Sprintf("   • 15m: %s(强度%d) | EMA20:%.4f | MACD:%.4f | RSI:%.1f",
				mtf.Timeframe15m.TrendDirection, mtf.Timeframe15m.SignalStrength,
				mtf.Timeframe15m.EMA20, mtf.Timeframe15m.MACD, mtf.Timeframe15m.RSI7))
			if mtf.Timeframe15m.ATR14 > 0 {
				sb.WriteString(fmt.Sprintf(" | ATR14:%.4f", mtf.Timeframe15m.ATR14))
			}
			if mtf.Timeframe15m.MarketStructure != nil {
				highCount := len(mtf.Timeframe15m.MarketStructure.SwingHighs)
				lowCount := len(mtf.Timeframe15m.MarketStructure.SwingLows)
				sb.WriteString(fmt.Sprintf(" | 结构:%s(高点%d个/低点%d个, 最新高点=第%d个, 最新低点=第%d个)",
					mtf.Timeframe15m.MarketStructure.CurrentBias,
					highCount, lowCount, highCount, lowCount))
			}
			sb.WriteString("\n")
		}
		if mtf.Timeframe1h != nil {
			sb.WriteString(fmt.Sprintf("   • 1h:  %s(强度%d) | EMA20:%.4f | MACD:%.4f | RSI:%.1f",
				mtf.Timeframe1h.TrendDirection, mtf.Timeframe1h.SignalStrength,
				mtf.Timeframe1h.EMA20, mtf.Timeframe1h.MACD, mtf.Timeframe1h.RSI7))
			if mtf.Timeframe1h.ATR14 > 0 {
				sb.WriteString(fmt.Sprintf(" | ATR14:%.4f", mtf.Timeframe1h.ATR14))
			}
			if mtf.Timeframe1h.MarketStructure != nil {
				highCount := len(mtf.Timeframe1h.MarketStructure.SwingHighs)
				lowCount := len(mtf.Timeframe1h.MarketStructure.SwingLows)
				sb.WriteString(fmt.Sprintf(" | 结构:%s(高点%d个/低点%d个, 最新高点=第%d个, 最新低点=第%d个)",
					mtf.Timeframe1h.MarketStructure.CurrentBias,
					highCount, lowCount, highCount, lowCount))
			}
			sb.WriteString("\n")
		}
		if mtf.Timeframe4h != nil {
			sb.WriteString(fmt.Sprintf("   • 4h:  %s(强度%d) | EMA20:%.4f | MACD:%.4f | RSI:%.1f",
				mtf.Timeframe4h.TrendDirection, mtf.Timeframe4h.SignalStrength,
				mtf.Timeframe4h.EMA20, mtf.Timeframe4h.MACD, mtf.Timeframe4h.RSI7))
			if mtf.Timeframe4h.ATR14 > 0 {
				sb.WriteString(fmt.Sprintf(" | ATR14:%.4f", mtf.Timeframe4h.ATR14))
			}
			if mtf.Timeframe4h.MarketStructure != nil {
				highCount := len(mtf.Timeframe4h.MarketStructure.SwingHighs)
				lowCount := len(mtf.Timeframe4h.MarketStructure.SwingLows)
				sb.WriteString(fmt.Sprintf(" | 结构:%s(高点%d个/低点%d个, 最新高点=第%d个, 最新低点=第%d个)",
					mtf.Timeframe4h.MarketStructure.CurrentBias,
					highCount, lowCount, highCount, lowCount))
			}
			sb.WriteString("\n")
		}
		if mtf.Timeframe1d != nil {
			sb.WriteString(fmt.Sprintf("   • 1d:  %s(强度%d) | EMA20:%.4f | MACD:%.4f | RSI:%.1f",
				mtf.Timeframe1d.TrendDirection, mtf.Timeframe1d.SignalStrength,
				mtf.Timeframe1d.EMA20, mtf.Timeframe1d.MACD, mtf.Timeframe1d.RSI7))
			if mtf.Timeframe1d.ATR14 > 0 {
				sb.WriteString(fmt.Sprintf(" | ATR14:%.4f", mtf.Timeframe1d.ATR14))
			}
			if mtf.Timeframe1d.MarketStructure != nil {
				highCount := len(mtf.Timeframe1d.MarketStructure.SwingHighs)
				lowCount := len(mtf.Timeframe1d.MarketStructure.SwingLows)
				sb.WriteString(fmt.Sprintf(" | 结构:%s(高点%d个/低点%d个, 最新高点=第%d个, 最新低点=第%d个)",
					mtf.Timeframe1d.MarketStructure.CurrentBias,
					highCount, lowCount, highCount, lowCount))
			}
			sb.WriteString("\n")
		}
	}

	// 斐波那契水平
	if fib, ok := filteredData["fibonacci"].(*FibLevels); ok && fib != nil {
		if showFib {
			sb.WriteString("📐 斐波那契水平: (回撤位用于判断支撑阻力, OTE区间=0.618-0.705是回调入场最佳区域)\n")
			sb.WriteString(fmt.Sprintf("   • 0.5中线: %.4f | 0.618: %.4f | 0.705: %.4f\n",
				fib.Level500, fib.Level618, fib.Level705))
		}
		if showOTE {
			sb.WriteString(fmt.Sprintf("   • OTE区间: %.4f - %.4f\n",
				fib.Level618, fib.Level705))
		}
	}

	// 市场结构（日线，用于大周期分析）
	if ms, ok := filteredData["market_structure"].(*MarketStructure); ok && ms != nil {
		sb.WriteString("🏗️ 市场结构（日线）: (偏向=bullish看涨/bearish看跌/neutral中性)\n")
		highCount := len(ms.SwingHighs)
		lowCount := len(ms.SwingLows)
		sb.WriteString(fmt.Sprintf("   • 偏向: %s | 波段高点: %d个 | 波段低点: %d个\n",
			ms.CurrentBias, highCount, lowCount))
		if highCount > 0 && lowCount > 0 {
			latestHighIdx := highCount
			latestLowIdx := lowCount
			sb.WriteString(fmt.Sprintf("   • 最近波段: 高点%.4f(第%d个) → 低点%.4f(第%d个)\n",
				ms.SwingHighs[highCount-1], latestHighIdx,
				ms.SwingLows[lowCount-1], latestLowIdx))
			// 显示更多波段信息（如果有）
			if highCount > 1 {
				prevHighIdx := highCount - 1
				sb.WriteString(fmt.Sprintf("   • 前一个波段高点: %.4f(第%d个)", ms.SwingHighs[highCount-2], prevHighIdx))
				if lowCount > 1 {
					prevLowIdx := lowCount - 1
					sb.WriteString(fmt.Sprintf(" | 前一个波段低点: %.4f(第%d个)", ms.SwingLows[lowCount-2], prevLowIdx))
				}
				sb.WriteString("\n")
			}
		}
	}

	// 成交量分析
	if rvol, ok := filteredData["rvol"].(float64); ok {
		sb.WriteString(fmt.Sprintf("📊 相对成交量(RVol): %.2fx (当前/20均量, >1.5表示放量, <0.5表示缩量)\n", rvol))
	}

	// 形态识别
	if patterns, ok := filteredData["patterns"].(*PatternRecognition); ok && patterns != nil && len(patterns.Patterns) > 0 {
		sb.WriteString("🕯️ 形态识别: (K线形态用于入场信号, bullish=看涨, bearish=看跌, 置信度越高信号越强)\n")
		for _, p := range patterns.Patterns {
			sb.WriteString(fmt.Sprintf("   • %s (%s) - %s - 置信度%.0f%%\n",
				p.DisplayName, p.Timeframe, p.Side, p.Confidence*100))
		}
	}

	// 市场状态
	if condition, ok := filteredData["market_condition"].(*MarketCondition); ok && condition != nil {
		sb.WriteString(fmt.Sprintf("🌊 市场状态: %s (置信度: %d%%, trending=趋势市可交易, ranging=震荡市避免开仓, volatile=波动市谨慎)\n",
			condition.Condition, condition.Confidence))
	}

	// 持仓量数据
	if oi, ok := filteredData["open_interest"].(*OIData); ok && oi != nil {
		sb.WriteString(fmt.Sprintf("📈 持仓量: %.0f | 平均: %.0f", oi.Latest, oi.Average))
		if oi.Change1h != 0 {
			sb.WriteString(fmt.Sprintf(" | 1h变化: %+.2f%%", oi.Change1h))
		}
		if oi.Change4h != 0 {
			sb.WriteString(fmt.Sprintf(" | 4h变化: %+.2f%%", oi.Change4h))
		}
		sb.WriteString(" (价格跌+OI涨=主动做空信号强, 价格跌+OI跌=多头止损动能弱)\n")
	}

	// 资金费率数据
	if fr, ok := filteredData["funding_rate"].(*FundingRateData); ok && fr != nil {
		sb.WriteString(fmt.Sprintf("💵 资金费率: %.4f", fr.Latest))
		if fr.Change1h != 0 {
			sb.WriteString(fmt.Sprintf(" | 1h变化: %+.2f基点", fr.Change1h))
		}
		if fr.Change4h != 0 {
			sb.WriteString(fmt.Sprintf(" | 4h变化: %+.2f基点", fr.Change4h))
		}
		sb.WriteString(" (正费率=做多付费, 负费率=做空付费, 费率上升=做多情绪增强)\n")
	}

	// 价格序列近期变动（15m）
	if showRecentMove && data.MultiTimeframe != nil && data.MultiTimeframe.Timeframe15m != nil {
		priceSeries := data.MultiTimeframe.Timeframe15m.PriceSeries
		if len(priceSeries) >= 2 {
			recentChange := ((priceSeries[len(priceSeries)-1] - priceSeries[len(priceSeries)-2]) / priceSeries[len(priceSeries)-2]) * 100
			sb.WriteString(fmt.Sprintf("📈 最新变动(15m): %+.2f%%\n", recentChange))
		}
	}

	return sb.String()
}
