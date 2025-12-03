package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"time"
)

// TradeRecord 交易记录结构
type TradeRecord struct {
	Symbol          string  `json:"symbol"`
	ID              int64   `json:"id"`
	OrderID         int64   `json:"orderId"`
	Price           float64 `json:"price"`
	Quantity        float64 `json:"quantity"`
	QuoteQuantity   float64 `json:"quoteQuantity"`
	Commission      float64 `json:"commission"`
	CommissionAsset string  `json:"commissionAsset"`
	Time            int64   `json:"time"`
	IsBuyer         bool    `json:"isBuyer"`
	IsMaker         bool    `json:"isMaker"`
	IsIsolated      bool    `json:"isIsolated"`
	PositionSide    string  `json:"positionSide"`
}

func main() {
	// 命令行参数
	var (
		apiKey     = flag.String("api-key", "", "Binance API Key (必需)")
		secretKey  = flag.String("secret-key", "", "Binance Secret Key (必需)")
		symbol     = flag.String("symbol", "", "交易对符号，例如 BTCUSDT (可选，不指定则下载所有交易对)")
		startTime  = flag.String("start-time", "", "开始时间 (格式: 2024-01-01 或 2024-01-01T00:00:00)")
		endTime    = flag.String("end-time", "", "结束时间 (格式: 2024-12-31 或 2024-12-31T23:59:59)，不指定则使用当前时间")
		output     = flag.String("output", "trades.csv", "输出文件名 (支持 .csv 或 .json)")
		format     = flag.String("format", "csv", "输出格式: csv 或 json")
		useTestnet = flag.Bool("testnet", false, "使用测试网")
		limit      = flag.Int("limit", 1000, "每次请求的最大记录数 (最大1000)")
	)
	flag.Parse()

	// 验证必需参数
	if *apiKey == "" || *secretKey == "" {
		log.Fatal("❌ 错误: 必须提供 API Key 和 Secret Key")
	}

	// 确定API基础URL
	baseURL := "https://fapi.binance.com"
	if *useTestnet {
		baseURL = "https://testnet.binancefuture.com"
		log.Println("📡 使用测试网")
	}

	ctx := context.Background()

	// 解析时间范围
	var startTimestamp, endTimestamp int64
	if *startTime != "" {
		t, err := parseTime(*startTime)
		if err != nil {
			log.Fatalf("❌ 解析开始时间失败: %v", err)
		}
		startTimestamp = t.UnixMilli()
	} else {
		// 默认从6个月前开始（Binance API限制：最多查询6个月）
		// 按时间顺序从旧到新获取
		startTimestamp = time.Now().AddDate(0, -6, 0).UnixMilli()
		log.Printf("ℹ️  未指定开始时间，默认从6个月前开始，按时间顺序从旧到新获取: %s", time.UnixMilli(startTimestamp).Format("2006-01-02 15:04:05"))
	}

	if *endTime != "" {
		t, err := parseTime(*endTime)
		if err != nil {
			log.Fatalf("❌ 解析结束时间失败: %v", err)
		}
		endTimestamp = t.UnixMilli()
	} else {
		endTimestamp = time.Now().UnixMilli()
		log.Printf("ℹ️  未指定结束时间，使用当前时间: %s", time.UnixMilli(endTimestamp).Format("2006-01-02 15:04:05"))
	}

	// 验证时间范围
	if startTimestamp >= endTimestamp {
		log.Fatal("❌ 错误: 开始时间必须早于结束时间")
	}

	// 检查时间范围是否超过6个月
	sixMonthsAgo := time.Now().AddDate(0, -6, 0).UnixMilli()
	if startTimestamp < sixMonthsAgo {
		log.Printf("⚠️  警告: Binance API 仅支持查询最近6个月的数据。开始时间将被调整为: %s", time.UnixMilli(sixMonthsAgo).Format("2006-01-02 15:04:05"))
		startTimestamp = sixMonthsAgo
	}

	// 确定输出格式
	if *format == "" {
		// 根据文件扩展名自动判断
		if len(*output) > 4 && (*output)[len(*output)-4:] == ".json" {
			*format = "json"
		} else {
			*format = "csv"
		}
	}

	// 获取交易记录
	var allTrades []TradeRecord
	if *symbol != "" {
		// 下载指定交易对的记录
		log.Printf("📥 开始下载 %s 的交易记录...", *symbol)
		trades, err := downloadTrades(ctx, baseURL, *apiKey, *secretKey, *symbol, startTimestamp, endTimestamp, *limit)
		if err != nil {
			log.Fatalf("❌ 下载失败: %v", err)
		}
		allTrades = trades
		log.Printf("✓ 成功下载 %d 条交易记录", len(allTrades))
	} else {
		// 下载所有交易对的记录
		log.Println("📥 开始下载所有交易对的交易记录...")
		log.Println("⚠️  注意: 这将下载所有交易对的数据，可能需要较长时间")

		// 从config.json读取的交易对列表（所有default_coins）
		commonSymbols := []string{
			"BTCUSDT",
			"ETHUSDT",
			"SOLUSDT",
			"BNBUSDT",
			"XRPUSDT",
			"DOGEUSDT",
			"ADAUSDT",
			"HYPEUSDT",
			"TRXUSDT",
			"XLMUSDT",
			"BCHUSDT",
			"LINKUSDT",
			"ZECUSDT",
			"HBARUSDT",
			"LTCUSDT",
			"UNIUSDT",
			"AVAXUSDT",
			"SUIUSDT",
			"1000SHIBUSDT",
			"WLFIUSDT",
			"TONUSDT",
			"DOTUSDT",
			"TAOUSDT",
			"AAVEUSDT",
			"BANKUSDT",
			"METUSDT",
			"ALLOUSDT",
			"OMUSDT",
			"BICOUSDT",
		}

		log.Printf("📋 将下载 %d 个常见交易对的数据...", len(commonSymbols))

		// 下载每个交易对的记录
		for _, sym := range commonSymbols {
			log.Printf("📥 正在下载 %s 的交易记录...", sym)
			trades, err := downloadTrades(ctx, baseURL, *apiKey, *secretKey, sym, startTimestamp, endTimestamp, *limit)
			if err != nil {
				log.Printf("⚠️  下载 %s 失败: %v，跳过", sym, err)
				continue
			}
			allTrades = append(allTrades, trades...)
			log.Printf("✓ %s: %d 条记录", sym, len(trades))
			// 避免请求过快
			time.Sleep(200 * time.Millisecond)
		}

		log.Printf("✓ 总共下载 %d 条交易记录", len(allTrades))
	}

	// 保存到文件
	if len(allTrades) == 0 {
		log.Println("⚠️  没有找到交易记录")
		return
	}

	if *format == "json" {
		if err := saveAsJSON(allTrades, *output); err != nil {
			log.Fatalf("❌ 保存JSON文件失败: %v", err)
		}
	} else {
		if err := saveAsCSV(allTrades, *output); err != nil {
			log.Fatalf("❌ 保存CSV文件失败: %v", err)
		}
	}

	log.Printf("✅ 交易记录已保存到: %s", *output)
}

// downloadTrades 下载指定交易对的交易记录
// 按时间顺序从旧到新获取（从最早交易开始，向后获取所有历史数据）
func downloadTrades(ctx context.Context, baseURL, apiKey, secretKey, symbol string, startTime, endTime int64, limit int) ([]TradeRecord, error) {
	var allTrades []TradeRecord

	// Binance API限制：每次查询最多7天
	const maxInterval = 7 * 24 * time.Hour
	maxIntervalMs := int64(maxInterval / time.Millisecond)

	// 计算总天数
	totalDays := (endTime - startTime) / (24 * 60 * 60 * 1000)

	// 如果时间范围超过7天，需要分割成多个7天的块
	if totalDays > 7 {
		log.Printf("ℹ️  时间范围 %d 天超过7天限制，将从最早开始，分块向后获取...", totalDays)
	}

	// 从最早时间开始，向后获取
	currentStart := startTime
	blockNum := 1

	for currentStart < endTime {
		// 计算当前块的结束时间（向后7天，但不晚于endTime）
		currentEnd := currentStart + maxIntervalMs
		if currentEnd > endTime {
			currentEnd = endTime
		}

		if totalDays > 7 {
			log.Printf("📦 下载第 %d 个时间块（从旧到新）: %s 至 %s",
				blockNum,
				time.UnixMilli(currentStart).Format("2006-01-02"),
				time.UnixMilli(currentEnd).Format("2006-01-02"))
		}

		// 下载当前时间块的数据（API返回的就是从旧到新的顺序）
		blockTrades, err := downloadTradesInRange(ctx, baseURL, apiKey, secretKey, symbol, currentStart, currentEnd, limit)
		if err != nil {
			return nil, fmt.Errorf("下载时间块失败 (%s 至 %s): %w",
				time.UnixMilli(currentStart).Format("2006-01-02"),
				time.UnixMilli(currentEnd).Format("2006-01-02"), err)
		}

		// 直接追加（保持从旧到新的顺序）
		allTrades = append(allTrades, blockTrades...)
		log.Printf("✓ 时间块 %d: 获取 %d 条记录（累计: %d 条）", blockNum, len(blockTrades), len(allTrades))

		// 移动到下一个时间块（向后移动）
		currentStart = currentEnd + 1
		blockNum++

		// 避免请求过快
		time.Sleep(200 * time.Millisecond)
	}

	return allTrades, nil
}

// downloadTradesInRange 下载指定时间范围内的交易记录（不超过7天）
func downloadTradesInRange(ctx context.Context, baseURL, apiKey, secretKey, symbol string, startTime, endTime int64, limit int) ([]TradeRecord, error) {
	var allTrades []TradeRecord
	fromID := int64(0)
	httpClient := &http.Client{Timeout: 30 * time.Second}

	for {
		// 构建查询参数
		params := url.Values{}
		params.Set("symbol", symbol)
		params.Set("limit", strconv.Itoa(limit))

		if fromID > 0 {
			params.Set("fromId", strconv.FormatInt(fromID, 10))
		}

		if startTime > 0 {
			params.Set("startTime", strconv.FormatInt(startTime, 10))
		}

		if endTime > 0 {
			params.Set("endTime", strconv.FormatInt(endTime, 10))
		}

		// 添加时间戳和签名
		timestamp := time.Now().UnixMilli()
		params.Set("timestamp", strconv.FormatInt(timestamp, 10))

		// 生成签名
		queryString := params.Encode()
		signature := generateSignature(queryString, secretKey)

		// 构建完整URL
		requestURL := fmt.Sprintf("%s/fapi/v1/userTrades?%s&signature=%s", baseURL, queryString, signature)

		// 创建HTTP请求
		req, err := http.NewRequestWithContext(ctx, "GET", requestURL, nil)
		if err != nil {
			return nil, fmt.Errorf("创建请求失败: %w", err)
		}

		// 添加API Key到请求头
		req.Header.Set("X-MBX-APIKEY", apiKey)

		// 执行请求
		resp, err := httpClient.Do(req)
		if err != nil {
			return nil, fmt.Errorf("请求失败: %w", err)
		}
		defer resp.Body.Close()

		// 读取响应
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("读取响应失败: %w", err)
		}

		// 检查HTTP状态码
		if resp.StatusCode != http.StatusOK {
			// 解析错误响应以提供更详细的错误信息
			var errorResp map[string]interface{}
			if err := json.Unmarshal(body, &errorResp); err == nil {
				if code, ok := errorResp["code"].(float64); ok {
					if code == -4165 {
						return nil, fmt.Errorf("时间间隔超过7天限制 (错误代码: %.0f): %v\n"+
							"提示: 代码应该自动处理此问题，如果仍然出现，请检查时间范围设置",
							code, errorResp["msg"])
					}
					return nil, fmt.Errorf("API返回错误 (代码: %.0f): %v", code, errorResp["msg"])
				}
			}
			return nil, fmt.Errorf("API返回错误: %s, 响应: %s", resp.Status, string(body))
		}

		// 解析JSON响应
		var trades []map[string]interface{}
		if err := json.Unmarshal(body, &trades); err != nil {
			return nil, fmt.Errorf("解析JSON失败: %w", err)
		}

		if len(trades) == 0 {
			break
		}

		// 转换为我们的结构
		for _, trade := range trades {
			record := parseTradeRecord(trade)
			allTrades = append(allTrades, record)
		}

		// 如果返回的记录数少于limit，说明已经获取完所有数据
		if len(trades) < limit {
			break
		}

		// 使用最后一条记录的ID作为下一次请求的起始ID
		if lastID, ok := trades[len(trades)-1]["id"].(float64); ok {
			fromID = int64(lastID) + 1
		} else {
			break
		}

		// 避免请求过快
		time.Sleep(200 * time.Millisecond)
	}

	return allTrades, nil
}

// generateSignature 生成HMAC SHA256签名
func generateSignature(queryString, secretKey string) string {
	mac := hmac.New(sha256.New, []byte(secretKey))
	mac.Write([]byte(queryString))
	return hex.EncodeToString(mac.Sum(nil))
}

// parseTradeRecord 解析交易记录
func parseTradeRecord(trade map[string]interface{}) TradeRecord {
	record := TradeRecord{}

	if v, ok := trade["symbol"].(string); ok {
		record.Symbol = v
	}
	if v, ok := trade["id"].(float64); ok {
		record.ID = int64(v)
	}
	if v, ok := trade["orderId"].(float64); ok {
		record.OrderID = int64(v)
	}
	if v, ok := trade["price"].(string); ok {
		record.Price, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["qty"].(string); ok {
		record.Quantity, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["quoteQty"].(string); ok {
		record.QuoteQuantity, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["commission"].(string); ok {
		record.Commission, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["commissionAsset"].(string); ok {
		record.CommissionAsset = v
	}
	if v, ok := trade["time"].(float64); ok {
		record.Time = int64(v)
	}
	if v, ok := trade["buyer"].(bool); ok {
		record.IsBuyer = v
	}
	if v, ok := trade["maker"].(bool); ok {
		record.IsMaker = v
	}
	if v, ok := trade["isolated"].(bool); ok {
		record.IsIsolated = v
	}
	if v, ok := trade["positionSide"].(string); ok {
		record.PositionSide = v
	}

	return record
}

// parseTime 解析时间字符串
func parseTime(timeStr string) (time.Time, error) {
	// 尝试多种时间格式
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"2006/01/02 15:04:05",
		"2006/01/02",
	}

	for _, format := range formats {
		if t, err := time.Parse(format, timeStr); err == nil {
			return t, nil
		}
	}

	return time.Time{}, fmt.Errorf("无法解析时间格式: %s", timeStr)
}

// saveAsCSV 保存为CSV格式
func saveAsCSV(trades []TradeRecord, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// 写入表头
	header := []string{
		"交易对", "交易ID", "订单ID", "价格", "数量", "成交额", "手续费", "手续费币种",
		"时间", "是否买方", "是否做市商", "是否逐仓", "持仓方向",
	}
	if err := writer.Write(header); err != nil {
		return err
	}

	// 写入数据
	for _, trade := range trades {
		record := []string{
			trade.Symbol,
			strconv.FormatInt(trade.ID, 10),
			strconv.FormatInt(trade.OrderID, 10),
			strconv.FormatFloat(trade.Price, 'f', -1, 64),
			strconv.FormatFloat(trade.Quantity, 'f', -1, 64),
			strconv.FormatFloat(trade.QuoteQuantity, 'f', -1, 64),
			strconv.FormatFloat(trade.Commission, 'f', -1, 64),
			trade.CommissionAsset,
			time.UnixMilli(trade.Time).Format("2006-01-02 15:04:05"),
			strconv.FormatBool(trade.IsBuyer),
			strconv.FormatBool(trade.IsMaker),
			strconv.FormatBool(trade.IsIsolated),
			trade.PositionSide,
		}
		if err := writer.Write(record); err != nil {
			return err
		}
	}

	return nil
}

// saveAsJSON 保存为JSON格式
func saveAsJSON(trades []TradeRecord, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(trades)
}
