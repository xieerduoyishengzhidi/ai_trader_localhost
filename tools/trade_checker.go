package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// TradeDetail 成交详情
type TradeDetail struct {
	TradeID         int64   `json:"trade_id"`
	Price           float64 `json:"price"`
	Quantity        float64 `json:"quantity"`
	QuoteQuantity   float64 `json:"quote_quantity"`
	Commission      float64 `json:"commission"`
	CommissionAsset string  `json:"commission_asset"`
	Time            int64   `json:"time"`
	IsBuyer         bool    `json:"is_buyer"`
	IsMaker         bool    `json:"is_maker"`
}

// GetOrderTrades 获取指定订单的成交记录
func GetOrderTrades(baseURL, apiKey, secretKey, symbol string, orderID int64) ([]TradeDetail, error) {
	ctx := context.Background()
	var allTrades []TradeDetail
	httpClient := &http.Client{Timeout: 30 * time.Second}

	// 查询最近1小时的交易记录（订单通常会在几分钟内成交）
	startTime := time.Now().Add(-1 * time.Hour).UnixMilli()
	endTime := time.Now().UnixMilli()
	fromID := int64(0)
	limit := 1000

	for {
		params := url.Values{}
		params.Set("symbol", symbol)
		params.Set("limit", strconv.Itoa(limit))
		params.Set("startTime", strconv.FormatInt(startTime, 10))
		params.Set("endTime", strconv.FormatInt(endTime, 10))

		if fromID > 0 {
			params.Set("fromId", strconv.FormatInt(fromID, 10))
		}

		timestamp := time.Now().UnixMilli()
		params.Set("timestamp", strconv.FormatInt(timestamp, 10))

		queryString := params.Encode()
		signature := generateSignature(queryString, secretKey)

		requestURL := fmt.Sprintf("%s/fapi/v1/userTrades?%s&signature=%s", baseURL, queryString, signature)

		req, err := http.NewRequestWithContext(ctx, "GET", requestURL, nil)
		if err != nil {
			return nil, fmt.Errorf("创建请求失败: %w", err)
		}

		req.Header.Set("X-MBX-APIKEY", apiKey)

		resp, err := httpClient.Do(req)
		if err != nil {
			return nil, fmt.Errorf("请求失败: %w", err)
		}
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("读取响应失败: %w", err)
		}

		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("API返回错误: %s, 响应: %s", resp.Status, string(body))
		}

		var trades []map[string]interface{}
		if err := json.Unmarshal(body, &trades); err != nil {
			return nil, fmt.Errorf("解析JSON失败: %w", err)
		}

		if len(trades) == 0 {
			break
		}

		// 筛选出匹配订单ID的成交记录
		for _, trade := range trades {
			if tradeOrderID, ok := trade["orderId"].(float64); ok && int64(tradeOrderID) == orderID {
				detail := parseTradeDetail(trade)
				allTrades = append(allTrades, detail)
			}
		}

		// 如果已经找到匹配的记录，且当前批次中没有更多匹配，可以提前退出
		if len(allTrades) > 0 && len(trades) < limit {
			break
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

// parseTradeDetail 解析成交记录
func parseTradeDetail(trade map[string]interface{}) TradeDetail {
	detail := TradeDetail{}

	if v, ok := trade["id"].(float64); ok {
		detail.TradeID = int64(v)
	}
	if v, ok := trade["price"].(string); ok {
		detail.Price, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["qty"].(string); ok {
		detail.Quantity, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["quoteQty"].(string); ok {
		detail.QuoteQuantity, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["commission"].(string); ok {
		detail.Commission, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := trade["commissionAsset"].(string); ok {
		detail.CommissionAsset = v
	}
	if v, ok := trade["time"].(float64); ok {
		detail.Time = int64(v)
	}
	if v, ok := trade["buyer"].(bool); ok {
		detail.IsBuyer = v
	}
	if v, ok := trade["maker"].(bool); ok {
		detail.IsMaker = v
	}

	return detail
}

