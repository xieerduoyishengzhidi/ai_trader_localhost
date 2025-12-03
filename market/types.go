package market

import "time"

// Data 市场数据结构
type Data struct {
	Symbol            string
	CurrentPrice      float64
	PriceChange1h     float64 // 1小时价格变化百分比
	PriceChange4h     float64 // 4小时价格变化百分比
	PriceChange1d     float64 // 日线价格变化百分比
	CurrentEMA20      float64
	CurrentMACD       float64
	CurrentRSI7       float64
	OpenInterest      *OIData
	FundingRate       *FundingRateData
	MultiTimeframe    *MultiTimeframeData
	LongerTermContext *LongerTermData
	MarketStructure   *MarketStructure   // 新增：市场结构分析
	FibLevels         *FibLevels         // 新增：斐波那契水平
	PatternRecognition *PatternRecognition `json:"pattern_recognition,omitempty"` // 新增：形态识别汇总
	RVol              float64 // 相对成交量：当前K线成交量 / 过去20根K线平均成交量
	EMADeviation      float64 // EMA偏离度：(当前价格 - EMA20) / EMA20 * 100
	PDH               float64 // 前日高点 (Previous Day High)
	PDL               float64 // 前日低点 (Previous Day Low)
}

// OIData Open Interest数据
type OIData struct {
	Latest      float64 // 当前持仓量
	Average     float64 // 平均持仓量
	Change15m   float64 // 15分钟变化率（%）
	Change1h    float64 // 1小时变化率（%）
	Change4h    float64 // 4小时变化率（%）
	Change1d    float64 // 1天变化率（%）
}

// FundingRateData 资金费率数据
type FundingRateData struct {
	Latest    float64 // 当前资金费率
	Change15m float64 // 15分钟变化率（%）
	Change1h  float64 // 1小时变化率（%）
	Change4h  float64 // 4小时变化率（%）
	Change1d  float64 // 1天变化率（%）
}

// IntradayData 日内数据(3分钟间隔)
type IntradayData struct {
	MidPrices   []float64
	EMA20Values []float64
	MACDValues  []float64
	RSI7Values  []float64
	RSI14Values []float64
}

// LongerTermData 长期数据(4小时时间框架)
type LongerTermData struct {
	EMA20         float64
	EMA50         float64
	ATR3          float64
	ATR14         float64
	CurrentVolume float64
	AverageVolume float64
	MACDValues    []float64
	RSI14Values   []float64
}

// FibLevels 斐波那契水平
type FibLevels struct {
	Level236 float64 // 0.236
	Level382 float64 // 0.382
	Level500 float64 // 0.5
	Level618 float64 // 0.618
	Level705 float64 // 0.705
	Level786 float64 // 0.786
	High     float64 // 波段高点
	Low      float64 // 波段低点
	Trend    string  // "bullish" or "bearish"
}

// MarketStructure 市场结构
type MarketStructure struct {
	SwingHighs []float64 // 波段高点序列
	SwingLows  []float64 // 波段低点序列
	CurrentBias string   // "bullish", "bearish", "neutral"
	FibLevels  *FibLevels
}

// MultiTimeframeData 多时间框架数据
type MultiTimeframeData struct {
	Timeframe15m *TimeframeData
	Timeframe1h  *TimeframeData
	Timeframe4h  *TimeframeData
	Timeframe1d  *TimeframeData // 新增：日线数据
}

// TimeframeData 单个时间框架数据
type TimeframeData struct {
	Timeframe      string
	CurrentPrice   float64
	EMA20          float64
	EMA50          float64
	MACD           float64
	RSI7           float64
	RSI14          float64
	ATR14          float64
	Volume         float64
	PriceSeries    []float64
	TrendDirection string              // "bullish", "bearish", "neutral"
	SignalStrength int                 // 0-100
	Patterns       []CandlestickPattern `json:"patterns,omitempty"` // 新增：形态识别结果
	MarketStructure *MarketStructure   `json:"market_structure,omitempty"` // 新增：该时间框架的市场结构
}

// CandlestickPattern 单个形态识别结果
type CandlestickPattern struct {
	Name        string  `json:"name"`         // 形态名称（如 "CDLENGULFING"）
	DisplayName string  `json:"display_name"` // 显示名称（如 "吞噬形态"）
	Signal      int     `json:"signal"`       // 信号：100=看涨, -100=看跌, 0=无信号（保留用于兼容）
	Side        string  `json:"side"`        // 语义化信号："bullish" 或 "bearish"（推荐使用）
	Timeframe   string  `json:"timeframe"`    // 时间框架（15m, 1h, 4h, 1d）
	Index       int     `json:"index"`        // K线索引（-1表示最新一根）
	Confidence  float64 `json:"confidence"`   // 置信度（0-1，已包含量能分析）
	Note        string  `json:"note,omitempty"` // 可选备注（如 "Double Volume"）
}

// PatternRecognition 形态识别结果集合
type PatternRecognition struct {
	Symbol    string                `json:"symbol"`
	Patterns  []CandlestickPattern `json:"patterns"`
	Timestamp int64                `json:"timestamp"`
}

// Binance API 响应结构
type ExchangeInfo struct {
	Symbols []SymbolInfo `json:"symbols"`
}

type SymbolInfo struct {
	Symbol            string `json:"symbol"`
	Status            string `json:"status"`
	BaseAsset         string `json:"baseAsset"`
	QuoteAsset        string `json:"quoteAsset"`
	ContractType      string `json:"contractType"`
	PricePrecision    int    `json:"pricePrecision"`
	QuantityPrecision int    `json:"quantityPrecision"`
}

type Kline struct {
	OpenTime            int64   `json:"openTime"`
	Open                float64 `json:"open"`
	High                float64 `json:"high"`
	Low                 float64 `json:"low"`
	Close               float64 `json:"close"`
	Volume              float64 `json:"volume"`
	CloseTime           int64   `json:"closeTime"`
	QuoteVolume         float64 `json:"quoteVolume"`
	Trades              int     `json:"trades"`
	TakerBuyBaseVolume  float64 `json:"takerBuyBaseVolume"`
	TakerBuyQuoteVolume float64 `json:"takerBuyQuoteVolume"`
}

type KlineResponse []interface{}

type PriceTicker struct {
	Symbol string `json:"symbol"`
	Price  string `json:"price"`
}

type Ticker24hr struct {
	Symbol             string `json:"symbol"`
	PriceChange        string `json:"priceChange"`
	PriceChangePercent string `json:"priceChangePercent"`
	Volume             string `json:"volume"`
	QuoteVolume        string `json:"quoteVolume"`
}

// 特征数据结构
type SymbolFeatures struct {
	Symbol           string    `json:"symbol"`
	Timestamp        time.Time `json:"timestamp"`
	Price            float64   `json:"price"`
	PriceChange15Min float64   `json:"price_change_15min"`
	PriceChange1H    float64   `json:"price_change_1h"`
	PriceChange4H    float64   `json:"price_change_4h"`
	Volume           float64   `json:"volume"`
	VolumeRatio5     float64   `json:"volume_ratio_5"`
	VolumeRatio20    float64   `json:"volume_ratio_20"`
	VolumeTrend      float64   `json:"volume_trend"`
	RSI14            float64   `json:"rsi_14"`
	SMA5             float64   `json:"sma_5"`
	SMA10            float64   `json:"sma_10"`
	SMA20            float64   `json:"sma_20"`
	HighLowRatio     float64   `json:"high_low_ratio"`
	Volatility20     float64   `json:"volatility_20"`
	PositionInRange  float64   `json:"position_in_range"`
}

// 警报数据结构
type Alert struct {
	Type      string    `json:"type"`
	Symbol    string    `json:"symbol"`
	Value     float64   `json:"value"`
	Threshold float64   `json:"threshold"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
}

type Config struct {
	AlertThresholds AlertThresholds `json:"alert_thresholds"`
	UpdateInterval  int             `json:"update_interval"` // seconds
	CleanupConfig   CleanupConfig   `json:"cleanup_config"`
}

type AlertThresholds struct {
	VolumeSpike      float64 `json:"volume_spike"`
	PriceChange15Min float64 `json:"price_change_15min"`
	VolumeTrend      float64 `json:"volume_trend"`
	RSIOverbought    float64 `json:"rsi_overbought"`
	RSIOversold      float64 `json:"rsi_oversold"`
}
type CleanupConfig struct {
	InactiveTimeout   time.Duration `json:"inactive_timeout"`    // 不活跃超时时间
	MinScoreThreshold float64       `json:"min_score_threshold"` // 最低评分阈值
	NoAlertTimeout    time.Duration `json:"no_alert_timeout"`    // 无警报超时时间
	CheckInterval     time.Duration `json:"check_interval"`      // 检查间隔
}

var config = Config{
	AlertThresholds: AlertThresholds{
		VolumeSpike:      3.0,
		PriceChange15Min: 0.05,
		VolumeTrend:      2.0,
		RSIOverbought:    70,
		RSIOversold:      30,
	},
	CleanupConfig: CleanupConfig{
		InactiveTimeout:   30 * time.Minute,
		MinScoreThreshold: 15.0,
		NoAlertTimeout:    20 * time.Minute,
		CheckInterval:     5 * time.Minute,
	},
	UpdateInterval: 60, // 1 minute
}
