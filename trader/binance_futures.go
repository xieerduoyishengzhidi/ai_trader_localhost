package trader

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"sync"
	"time"

	"github.com/adshao/go-binance/v2/futures"
)

// FuturesTrader 币安合约交易器
type FuturesTrader struct {
	client *futures.Client

	// 余额缓存
	cachedBalance     map[string]interface{}
	balanceCacheTime  time.Time
	balanceCacheMutex sync.RWMutex

	// 持仓缓存
	cachedPositions     []map[string]interface{}
	positionsCacheTime  time.Time
	positionsCacheMutex sync.RWMutex

	// 缓存有效期（15秒）
	cacheDuration time.Duration
}

// NewFuturesTrader 创建合约交易器
func NewFuturesTrader(apiKey, secretKey string, useTestnet bool) *FuturesTrader {
	client := futures.NewClient(apiKey, secretKey)
	if useTestnet {
		client.BaseURL = "https://testnet.binancefuture.com"
	}
	return &FuturesTrader{
		client:        client,
		cacheDuration: 15 * time.Second, // 15秒缓存
	}
}

// GetBalance 获取账户余额（带缓存）
func (t *FuturesTrader) GetBalance() (map[string]interface{}, error) {
	// 先检查缓存是否有效
	t.balanceCacheMutex.RLock()
	if t.cachedBalance != nil && time.Since(t.balanceCacheTime) < t.cacheDuration {
		cacheAge := time.Since(t.balanceCacheTime)
		t.balanceCacheMutex.RUnlock()
		log.Printf("✓ 使用缓存的账户余额（缓存时间: %.1f秒前）", cacheAge.Seconds())
		return t.cachedBalance, nil
	}
	t.balanceCacheMutex.RUnlock()

	// 缓存过期或不存在，调用API
	log.Printf("🔄 缓存过期，正在调用币安API获取账户余额...")
	account, err := t.client.NewGetAccountService().Do(context.Background())
	if err != nil {
		log.Printf("❌ 币安API调用失败: %v", err)
		return nil, fmt.Errorf("获取账户信息失败: %w", err)
	}

	result := make(map[string]interface{})
	result["totalWalletBalance"], _ = strconv.ParseFloat(account.TotalWalletBalance, 64)
	result["availableBalance"], _ = strconv.ParseFloat(account.AvailableBalance, 64)
	result["totalUnrealizedProfit"], _ = strconv.ParseFloat(account.TotalUnrealizedProfit, 64)

	log.Printf("✓ 币安API返回: 总余额=%s, 可用=%s, 未实现盈亏=%s",
		account.TotalWalletBalance,
		account.AvailableBalance,
		account.TotalUnrealizedProfit)

	// 更新缓存
	t.balanceCacheMutex.Lock()
	t.cachedBalance = result
	t.balanceCacheTime = time.Now()
	t.balanceCacheMutex.Unlock()

	return result, nil
}

// ClearBalanceCache 清除余额缓存，强制下次调用 GetBalance 时刷新
func (t *FuturesTrader) ClearBalanceCache() {
	t.balanceCacheMutex.Lock()
	t.cachedBalance = nil
	t.balanceCacheTime = time.Time{} // 设置为零值，强制过期
	t.balanceCacheMutex.Unlock()
	log.Printf("  ✓ 已清除余额缓存，下次将强制刷新")
}

// GetPositions 获取所有持仓（带缓存）
func (t *FuturesTrader) GetPositions() ([]map[string]interface{}, error) {
	// 先检查缓存是否有效
	t.positionsCacheMutex.RLock()
	if t.cachedPositions != nil && time.Since(t.positionsCacheTime) < t.cacheDuration {
		cacheAge := time.Since(t.positionsCacheTime)
		t.positionsCacheMutex.RUnlock()
		log.Printf("✓ 使用缓存的持仓信息（缓存时间: %.1f秒前）", cacheAge.Seconds())
		return t.cachedPositions, nil
	}
	t.positionsCacheMutex.RUnlock()

	// 缓存过期或不存在，调用API
	log.Printf("🔄 缓存过期，正在调用币安API获取持仓信息...")
	positions, err := t.client.NewGetPositionRiskService().Do(context.Background())
	if err != nil {
		return nil, fmt.Errorf("获取持仓失败: %w", err)
	}

	var result []map[string]interface{}
	for _, pos := range positions {
		posAmt, _ := strconv.ParseFloat(pos.PositionAmt, 64)
		if posAmt == 0 {
			continue // 跳过无持仓的
		}

		posMap := make(map[string]interface{})
		posMap["symbol"] = pos.Symbol
		posMap["positionAmt"], _ = strconv.ParseFloat(pos.PositionAmt, 64)
		posMap["entryPrice"], _ = strconv.ParseFloat(pos.EntryPrice, 64)
		posMap["markPrice"], _ = strconv.ParseFloat(pos.MarkPrice, 64)
		posMap["unRealizedProfit"], _ = strconv.ParseFloat(pos.UnRealizedProfit, 64)
		posMap["leverage"], _ = strconv.ParseFloat(pos.Leverage, 64)
		posMap["liquidationPrice"], _ = strconv.ParseFloat(pos.LiquidationPrice, 64)

		// 判断方向
		if posAmt > 0 {
			posMap["side"] = "long"
		} else {
			posMap["side"] = "short"
		}

		result = append(result, posMap)
	}

	// 更新缓存
	t.positionsCacheMutex.Lock()
	t.cachedPositions = result
	t.positionsCacheTime = time.Now()
	t.positionsCacheMutex.Unlock()

	return result, nil
}

// SetMarginMode 设置仓位模式
func (t *FuturesTrader) SetMarginMode(symbol string, isCrossMargin bool) error {
	var marginType futures.MarginType
	if isCrossMargin {
		marginType = futures.MarginTypeCrossed
	} else {
		marginType = futures.MarginTypeIsolated
	}

	// 尝试设置仓位模式
	err := t.client.NewChangeMarginTypeService().
		Symbol(symbol).
		MarginType(marginType).
		Do(context.Background())

	marginModeStr := "全仓"
	if !isCrossMargin {
		marginModeStr = "逐仓"
	}

	if err != nil {
		// 如果错误信息包含"No need to change"，说明仓位模式已经是目标值
		if contains(err.Error(), "No need to change margin type") {
			log.Printf("  ✓ %s 仓位模式已是 %s", symbol, marginModeStr)
			return nil
		}
		// 如果有持仓，无法更改仓位模式，但不影响交易
		if contains(err.Error(), "Margin type cannot be changed if there exists position") {
			log.Printf("  ⚠️ %s 有持仓，无法更改仓位模式，继续使用当前模式", symbol)
			return nil
		}
		log.Printf("  ⚠️ 设置仓位模式失败: %v", err)
		// 不返回错误，让交易继续
		return nil
	}

	log.Printf("  ✓ %s 仓位模式已设置为 %s", symbol, marginModeStr)
	return nil
}

// SetLeverage 设置杠杆（智能判断+冷却期）
func (t *FuturesTrader) SetLeverage(symbol string, leverage int) error {
	// 先尝试获取当前杠杆（从持仓信息）
	currentLeverage := 0
	positions, err := t.GetPositions()
	if err == nil {
		for _, pos := range positions {
			if pos["symbol"] == symbol {
				if lev, ok := pos["leverage"].(float64); ok {
					currentLeverage = int(lev)
					break
				}
			}
		}
	}

	// 如果当前杠杆已经是目标杠杆，跳过
	if currentLeverage == leverage && currentLeverage > 0 {
		log.Printf("  ✓ %s 杠杆已是 %dx，无需切换", symbol, leverage)
		return nil
	}

	// 切换杠杆
	_, err = t.client.NewChangeLeverageService().
		Symbol(symbol).
		Leverage(leverage).
		Do(context.Background())

	if err != nil {
		// 如果错误信息包含"No need to change"，说明杠杆已经是目标值
		if contains(err.Error(), "No need to change") {
			log.Printf("  ✓ %s 杠杆已是 %dx", symbol, leverage)
			return nil
		}
		// 如果错误是 "Symbol is closed" (错误代码 -4141)，说明交易对已关闭
		if contains(err.Error(), "Symbol is closed") || contains(err.Error(), "-4141") {
			log.Printf("  ❌ %s 交易对已关闭，无法设置杠杆", symbol)
			return fmt.Errorf("交易对 %s 已关闭或不可交易，请检查币安交易所状态", symbol)
		}
		return fmt.Errorf("设置杠杆失败: %w", err)
	}

	log.Printf("  ✓ %s 杠杆已切换为 %dx", symbol, leverage)

	// 切换杠杆后等待5秒（避免冷却期错误）
	log.Printf("  ⏱ 等待5秒冷却期...")
	time.Sleep(5 * time.Second)

	return nil
}

// OpenLong 开多仓
func (t *FuturesTrader) OpenLong(symbol string, quantity float64, leverage int) (map[string]interface{}, error) {
	// 先取消该币种的所有委托单（清理旧的止损止盈单）
	if err := t.CancelAllOrders(symbol); err != nil {
		log.Printf("  ⚠ 取消旧委托单失败（可能没有委托单）: %v", err)
	}

	// 设置杠杆
	if err := t.SetLeverage(symbol, leverage); err != nil {
		return nil, err
	}

	// 注意：仓位模式应该由调用方（AutoTrader）在开仓前通过 SetMarginMode 设置

	// 格式化数量到正确精度
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return nil, err
	}

	// 创建市价买入订单
	order, err := t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(futures.SideTypeBuy).
		PositionSide(futures.PositionSideTypeLong).
		Type(futures.OrderTypeMarket).
		Quantity(quantityStr).
		Do(context.Background())

	if err != nil {
		// 如果错误是 "Symbol is closed" (错误代码 -4141)，说明交易对已关闭
		if contains(err.Error(), "Symbol is closed") || contains(err.Error(), "-4141") {
			return nil, fmt.Errorf("交易对 %s 已关闭或不可交易，无法开多仓。请检查币安交易所状态或从候选列表中移除该交易对", symbol)
		}
		return nil, fmt.Errorf("开多仓失败: %w", err)
	}

	log.Printf("✓ 开多仓成功: %s 数量: %s", symbol, quantityStr)
	log.Printf("  订单ID: %d", order.OrderID)

	result := make(map[string]interface{})
	result["orderId"] = order.OrderID
	result["symbol"] = order.Symbol
	result["status"] = order.Status
	return result, nil
}

// OpenShort 开空仓
func (t *FuturesTrader) OpenShort(symbol string, quantity float64, leverage int) (map[string]interface{}, error) {
	// 先取消该币种的所有委托单（清理旧的止损止盈单）
	if err := t.CancelAllOrders(symbol); err != nil {
		log.Printf("  ⚠ 取消旧委托单失败（可能没有委托单）: %v", err)
	}

	// 设置杠杆
	if err := t.SetLeverage(symbol, leverage); err != nil {
		return nil, err
	}

	// 注意：仓位模式应该由调用方（AutoTrader）在开仓前通过 SetMarginMode 设置

	// 格式化数量到正确精度
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return nil, err
	}

	// 创建市价卖出订单
	order, err := t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(futures.SideTypeSell).
		PositionSide(futures.PositionSideTypeShort).
		Type(futures.OrderTypeMarket).
		Quantity(quantityStr).
		Do(context.Background())

	if err != nil {
		// 如果错误是 "Symbol is closed" (错误代码 -4141)，说明交易对已关闭
		if contains(err.Error(), "Symbol is closed") || contains(err.Error(), "-4141") {
			return nil, fmt.Errorf("交易对 %s 已关闭或不可交易，无法开空仓。请检查币安交易所状态或从候选列表中移除该交易对", symbol)
		}
		return nil, fmt.Errorf("开空仓失败: %w", err)
	}

	log.Printf("✓ 开空仓成功: %s 数量: %s", symbol, quantityStr)
	log.Printf("  订单ID: %d", order.OrderID)

	result := make(map[string]interface{})
	result["orderId"] = order.OrderID
	result["symbol"] = order.Symbol
	result["status"] = order.Status
	return result, nil
}

// CloseLong 平多仓
func (t *FuturesTrader) CloseLong(symbol string, quantity float64) (map[string]interface{}, error) {
	// 如果数量为0，获取当前持仓数量
	if quantity == 0 {
		positions, err := t.GetPositions()
		if err != nil {
			// 即使获取失败，也清除缓存，避免缓存导致的问题
			t.clearPositionsCache()
			return nil, fmt.Errorf("获取持仓失败: %w", err)
		}

		hasPosition := false
		for _, pos := range positions {
			if pos["symbol"] == symbol && pos["side"] == "long" {
				hasPosition = true
				quantity = pos["positionAmt"].(float64)
				break
			}
		}

		// 如果没有持仓，清除缓存并返回成功（可能已经被平掉，比如止损触发）
		if !hasPosition || quantity == 0 {
			t.clearPositionsCache()
			log.Printf("  ℹ️ %s 没有多仓，可能已经被平掉", symbol)
			return map[string]interface{}{
				"orderId": int64(0),
				"symbol":  symbol,
				"status":  "ALREADY_CLOSED",
			}, nil
		}
	}

	// 格式化数量
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return nil, err
	}

	// 创建市价卖出订单（平多）
	order, err := t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(futures.SideTypeSell).
		PositionSide(futures.PositionSideTypeLong).
		Type(futures.OrderTypeMarket).
		Quantity(quantityStr).
		Do(context.Background())

	// ⚠️ 关键：无论平仓成功或失败，都清除缓存，避免缓存导致的问题
	// 如果平仓失败，可能是持仓已不存在，清除缓存后下次会重新获取
	defer t.clearPositionsCache()

	if err != nil {
		return nil, fmt.Errorf("平多仓失败: %w", err)
	}

	log.Printf("✓ 平多仓成功: %s 数量: %s", symbol, quantityStr)

	// 平仓后取消该币种的所有挂单（止损止盈单）
	if err := t.CancelAllOrders(symbol); err != nil {
		log.Printf("  ⚠ 取消挂单失败: %v", err)
	}

	result := make(map[string]interface{})
	result["orderId"] = order.OrderID
	result["symbol"] = order.Symbol
	result["status"] = order.Status
	return result, nil
}

// CloseShort 平空仓
func (t *FuturesTrader) CloseShort(symbol string, quantity float64) (map[string]interface{}, error) {
	// 如果数量为0，获取当前持仓数量
	if quantity == 0 {
		positions, err := t.GetPositions()
		if err != nil {
			// 即使获取失败，也清除缓存，避免缓存导致的问题
			t.clearPositionsCache()
			return nil, fmt.Errorf("获取持仓失败: %w", err)
		}

		hasPosition := false
		for _, pos := range positions {
			if pos["symbol"] == symbol && pos["side"] == "short" {
				hasPosition = true
				quantity = -pos["positionAmt"].(float64) // 空仓数量是负的，取绝对值
				break
			}
		}

		// 如果没有持仓，清除缓存并返回成功（可能已经被平掉，比如止损触发）
		if !hasPosition || quantity == 0 {
			t.clearPositionsCache()
			log.Printf("  ℹ️ %s 没有空仓，可能已经被平掉", symbol)
			return map[string]interface{}{
				"orderId": int64(0),
				"symbol":  symbol,
				"status":  "ALREADY_CLOSED",
			}, nil
		}
	}

	// 格式化数量
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return nil, err
	}

	// 创建市价买入订单（平空）
	order, err := t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(futures.SideTypeBuy).
		PositionSide(futures.PositionSideTypeShort).
		Type(futures.OrderTypeMarket).
		Quantity(quantityStr).
		Do(context.Background())

	// ⚠️ 关键：无论平仓成功或失败，都清除缓存，避免缓存导致的问题
	// 如果平仓失败，可能是持仓已不存在，清除缓存后下次会重新获取
	defer t.clearPositionsCache()

	if err != nil {
		return nil, fmt.Errorf("平空仓失败: %w", err)
	}

	log.Printf("✓ 平空仓成功: %s 数量: %s", symbol, quantityStr)

	// 平仓后取消该币种的所有挂单（止损止盈单）
	if err := t.CancelAllOrders(symbol); err != nil {
		log.Printf("  ⚠ 取消挂单失败: %v", err)
	}

	result := make(map[string]interface{})
	result["orderId"] = order.OrderID
	result["symbol"] = order.Symbol
	result["status"] = order.Status
	return result, nil
}

// clearPositionsCache 清除仓位缓存（平仓后调用，确保下次获取最新数据）
func (t *FuturesTrader) clearPositionsCache() {
	t.positionsCacheMutex.Lock()
	t.cachedPositions = nil
	t.positionsCacheTime = time.Time{} // 设置为零值，强制下次重新获取
	t.positionsCacheMutex.Unlock()
	log.Printf("  🔄 已清除仓位缓存，下次将获取最新数据")
}

// ClearPositionsCache 公开方法：清除仓位缓存（供外部调用）
func (t *FuturesTrader) ClearPositionsCache() {
	t.clearPositionsCache()
}

// CancelAllOrders 取消该币种的所有挂单
func (t *FuturesTrader) CancelAllOrders(symbol string) error {
	err := t.client.NewCancelAllOpenOrdersService().
		Symbol(symbol).
		Do(context.Background())

	if err != nil {
		return fmt.Errorf("取消挂单失败: %w", err)
	}

	log.Printf("  ✓ 已取消 %s 的所有挂单", symbol)
	return nil
}

// CancelOrdersByType 取消指定币种和类型的订单
func (t *FuturesTrader) CancelOrdersByType(symbol string, orderType futures.OrderType) error {
	// 查询该币种的所有挂单
	orders, err := t.client.NewListOpenOrdersService().
		Symbol(symbol).
		Do(context.Background())

	if err != nil {
		return fmt.Errorf("查询挂单失败: %w", err)
	}

	// 筛选并取消指定类型的订单
	canceledCount := 0
	for _, order := range orders {
		if order.Type == orderType {
			_, err := t.client.NewCancelOrderService().
				Symbol(symbol).
				OrderID(order.OrderID).
				Do(context.Background())
			if err != nil {
				log.Printf("  ⚠ 取消订单失败 (orderID=%d, type=%s): %v", order.OrderID, order.Type, err)
			} else {
				canceledCount++
			}
		}
	}

	if canceledCount > 0 {
		log.Printf("  ✓ 已取消 %s 的 %d 个 %s 订单", symbol, canceledCount, orderType)
	}

	return nil
}

// GetMarketPrice 获取市场价格
func (t *FuturesTrader) GetMarketPrice(symbol string) (float64, error) {
	prices, err := t.client.NewListPricesService().Symbol(symbol).Do(context.Background())
	if err != nil {
		return 0, fmt.Errorf("获取价格失败: %w", err)
	}

	if len(prices) == 0 {
		return 0, fmt.Errorf("未找到价格")
	}

	price, err := strconv.ParseFloat(prices[0].Price, 64)
	if err != nil {
		return 0, err
	}

	return price, nil
}

// CalculatePositionSize 计算仓位大小
func (t *FuturesTrader) CalculatePositionSize(balance, riskPercent, price float64, leverage int) float64 {
	riskAmount := balance * (riskPercent / 100.0)
	positionValue := riskAmount * float64(leverage)
	quantity := positionValue / price
	return quantity
}

// SetStopLoss 设置止损单
func (t *FuturesTrader) SetStopLoss(symbol string, positionSide string, quantity, stopPrice float64) error {
	// ⚠️ 关键：先检查并取消旧的止损单，避免多个止损单同时存在
	if err := t.CancelOrdersByType(symbol, futures.OrderTypeStopMarket); err != nil {
		log.Printf("  ⚠ 取消旧止损单失败（继续设置新止损）: %v", err)
		// 继续执行，不因取消失败而阻止设置新止损
	}

	var side futures.SideType
	var posSide futures.PositionSideType

	if positionSide == "LONG" {
		side = futures.SideTypeSell
		posSide = futures.PositionSideTypeLong
	} else {
		side = futures.SideTypeBuy
		posSide = futures.PositionSideTypeShort
	}

	// 格式化数量
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return err
	}

	_, err = t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(side).
		PositionSide(posSide).
		Type(futures.OrderTypeStopMarket).
		StopPrice(fmt.Sprintf("%.8f", stopPrice)).
		Quantity(quantityStr).
		WorkingType(futures.WorkingTypeContractPrice).
		ClosePosition(true).
		Do(context.Background())

	if err != nil {
		return fmt.Errorf("设置止损失败: %w", err)
	}

	log.Printf("  止损价设置: %.4f", stopPrice)
	return nil
}

// SetTakeProfit 设置止盈单
func (t *FuturesTrader) SetTakeProfit(symbol string, positionSide string, quantity, takeProfitPrice float64) error {
	// ⚠️ 关键：先检查并取消旧的止盈单，避免多个止盈单同时存在
	if err := t.CancelOrdersByType(symbol, futures.OrderTypeTakeProfitMarket); err != nil {
		log.Printf("  ⚠ 取消旧止盈单失败（继续设置新止盈）: %v", err)
		// 继续执行，不因取消失败而阻止设置新止盈
	}

	var side futures.SideType
	var posSide futures.PositionSideType

	if positionSide == "LONG" {
		side = futures.SideTypeSell
		posSide = futures.PositionSideTypeLong
	} else {
		side = futures.SideTypeBuy
		posSide = futures.PositionSideTypeShort
	}

	// 格式化数量
	quantityStr, err := t.FormatQuantity(symbol, quantity)
	if err != nil {
		return err
	}

	_, err = t.client.NewCreateOrderService().
		Symbol(symbol).
		Side(side).
		PositionSide(posSide).
		Type(futures.OrderTypeTakeProfitMarket).
		StopPrice(fmt.Sprintf("%.8f", takeProfitPrice)).
		Quantity(quantityStr).
		WorkingType(futures.WorkingTypeContractPrice).
		ClosePosition(true).
		Do(context.Background())

	if err != nil {
		return fmt.Errorf("设置止盈失败: %w", err)
	}

	log.Printf("  止盈价设置: %.4f", takeProfitPrice)
	return nil
}

// GetSymbolPrecision 获取交易对的数量精度
func (t *FuturesTrader) GetSymbolPrecision(symbol string) (int, error) {
	exchangeInfo, err := t.client.NewExchangeInfoService().Do(context.Background())
	if err != nil {
		return 0, fmt.Errorf("获取交易规则失败: %w", err)
	}

	for _, s := range exchangeInfo.Symbols {
		if s.Symbol == symbol {
			// 从LOT_SIZE filter获取精度
			for _, filter := range s.Filters {
				if filter["filterType"] == "LOT_SIZE" {
					stepSize := filter["stepSize"].(string)
					precision := calculatePrecision(stepSize)
					log.Printf("  %s 数量精度: %d (stepSize: %s)", symbol, precision, stepSize)
					return precision, nil
				}
			}
		}
	}

	log.Printf("  ⚠ %s 未找到精度信息，使用默认精度3", symbol)
	return 3, nil // 默认精度为3
}

// calculatePrecision 从stepSize计算精度
func calculatePrecision(stepSize string) int {
	// 去除尾部的0
	stepSize = trimTrailingZeros(stepSize)

	// 查找小数点
	dotIndex := -1
	for i := 0; i < len(stepSize); i++ {
		if stepSize[i] == '.' {
			dotIndex = i
			break
		}
	}

	// 如果没有小数点或小数点在最后，精度为0
	if dotIndex == -1 || dotIndex == len(stepSize)-1 {
		return 0
	}

	// 返回小数点后的位数
	return len(stepSize) - dotIndex - 1
}

// trimTrailingZeros 去除尾部的0
func trimTrailingZeros(s string) string {
	// 如果没有小数点，直接返回
	if !stringContains(s, ".") {
		return s
	}

	// 从后向前遍历，去除尾部的0
	for len(s) > 0 && s[len(s)-1] == '0' {
		s = s[:len(s)-1]
	}

	// 如果最后一位是小数点，也去掉
	if len(s) > 0 && s[len(s)-1] == '.' {
		s = s[:len(s)-1]
	}

	return s
}

// FormatQuantity 格式化数量到正确的精度
func (t *FuturesTrader) FormatQuantity(symbol string, quantity float64) (string, error) {
	precision, err := t.GetSymbolPrecision(symbol)
	if err != nil {
		// 如果获取失败，使用默认格式
		return fmt.Sprintf("%.3f", quantity), nil
	}

	format := fmt.Sprintf("%%.%df", precision)
	return fmt.Sprintf(format, quantity), nil
}

// GetOrderTrades 获取订单的成交记录
func (t *FuturesTrader) GetOrderTrades(symbol string, orderID int64) ([]map[string]interface{}, error) {
	// 注意：Binance Futures API的userTrades接口不支持直接通过orderId查询
	// 我们需要查询最近的交易记录，然后筛选出匹配的订单ID

	// 由于go-binance库的限制，这里提供一个基本实现框架
	// 实际查询逻辑建议使用tools中的实现，或直接调用HTTP API
	// 查询时间窗口建议：最近24小时（扩大时间窗口，确保能找到订单）

	// 返回错误提示，建议使用tools中的方法或HTTP API直接查询
	return nil, fmt.Errorf("GetOrderTrades需要完整实现，建议使用tools/trade_checker.go中的GetOrderTrades方法，或通过HTTP API查询/fapi/v1/userTrades接口并筛选orderId=%d", orderID)
}

// 辅助函数
func contains(s, substr string) bool {
	return len(s) >= len(substr) && stringContains(s, substr)
}

func stringContains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
