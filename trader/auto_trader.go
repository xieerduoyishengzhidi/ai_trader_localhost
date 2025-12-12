package trader

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	decisionpkg "nofx/decision" // 使用别名避免与变量名冲突
	"nofx/logger"
	"nofx/market"
	"nofx/mcp"
	"nofx/pool"
	"strconv"
	"strings"
	"time"
)

// AutoTraderConfig 自动交易配置（简化版 - AI全权决策）
type AutoTraderConfig struct {
	// Trader标识
	ID      string // Trader唯一标识（用于日志目录等）
	Name    string // Trader显示名称
	AIModel string // AI模型: "qwen" 或 "deepseek"

	// 交易平台选择
	Exchange string // "binance", "hyperliquid" 或 "aster"

	// 币安API配置
	BinanceAPIKey    string
	BinanceSecretKey string
	BinanceTestnet   bool

	// Hyperliquid配置
	HyperliquidPrivateKey string
	HyperliquidWalletAddr string
	HyperliquidTestnet    bool

	// Aster配置
	AsterUser       string // Aster主钱包地址
	AsterSigner     string // Aster API钱包地址
	AsterPrivateKey string // Aster API钱包私钥

	CoinPoolAPIURL string

	// AI配置
	UseQwen        bool
	DeepSeekKey    string
	QwenKey        string
	SiliconFlowKey string

	// 自定义AI API配置
	CustomAPIURL    string
	CustomAPIKey    string
	CustomModelName string

	// 扫描配置
	ScanInterval time.Duration // 扫描间隔（建议3分钟）

	// 账户配置
	InitialBalance float64 // 初始金额（用于计算盈亏，需手动设置）

	// 杠杆配置
	BTCETHLeverage  int // BTC和ETH的杠杆倍数
	AltcoinLeverage int // 山寨币的杠杆倍数

	// 风险控制（仅作为提示，AI可自主决定）
	MaxDailyLoss    float64       // 最大日亏损百分比（提示）
	MaxDrawdown     float64       // 最大回撤百分比（提示）
	StopTradingTime time.Duration // 触发风控后暂停时长

	// 仓位模式
	IsCrossMargin bool // true=全仓模式, false=逐仓模式

	// 币种配置
	DefaultCoins []string // 默认币种列表（从数据库获取）
	TradingCoins []string // 实际交易币种列表

	// 系统提示词模板
	SystemPromptTemplate string // 系统提示词模板名称（如 "default", "aggressive"）

	// Prompt 数据字段配置
	PromptDataFields []string
	RAGEnabled       bool
}

// AutoTrader 自动交易器
type AutoTrader struct {
	id                    string // Trader唯一标识
	name                  string // Trader显示名称
	aiModel               string // AI模型名称
	exchange              string // 交易平台名称
	config                AutoTraderConfig
	trader                Trader // 使用Trader接口（支持多平台）
	mcpClient             *mcp.Client
	decisionLogger        *logger.DecisionLogger // 决策日志记录器
	initialBalance        float64
	dailyPnL              float64
	customPrompt          string // 自定义交易策略prompt
	openPositions         map[string]*logger.DecisionAction
	overrideBasePrompt    bool     // 是否覆盖基础prompt
	systemPromptTemplate  string   // 系统提示词模板名称
	defaultCoins          []string // 默认币种列表（从数据库获取）
	tradingCoins          []string // 实际交易币种列表
	lastResetTime         time.Time
	stopUntil             time.Time
	isRunning             bool
	startTime             time.Time        // 系统启动时间
	callCount             int              // AI调用次数
	positionFirstSeenTime map[string]int64 // 持仓首次出现时间 (symbol_side -> timestamp毫秒)
}

// NewAutoTrader 创建自动交易器
func NewAutoTrader(config AutoTraderConfig) (*AutoTrader, error) {
	// 设置默认值
	if config.ID == "" {
		config.ID = "default_trader"
	}
	if config.Name == "" {
		config.Name = "Default Trader"
	}
	if config.AIModel == "" {
		if config.UseQwen {
			config.AIModel = "qwen"
		} else {
			config.AIModel = "deepseek"
		}
	}

	mcpClient := mcp.New()

	// 初始化AI
	if config.AIModel == "custom" {
		// 使用自定义API
		mcpClient.SetCustomAPI(config.CustomAPIURL, config.CustomAPIKey, config.CustomModelName)
		log.Printf("🤖 [%s] 使用自定义AI API: %s (模型: %s)", config.Name, config.CustomAPIURL, config.CustomModelName)
	} else if config.AIModel == "siliconflow" {
		// 使用SiliconFlow (支持自定义URL和Model)
		mcpClient.SetSiliconFlowAPIKey(config.SiliconFlowKey, config.CustomAPIURL, config.CustomModelName)
		if config.CustomAPIURL != "" || config.CustomModelName != "" {
			log.Printf("🤖 [%s] 使用SiliconFlow AI (自定义URL: %s, 模型: %s)", config.Name, config.CustomAPIURL, config.CustomModelName)
		} else {
			log.Printf("🤖 [%s] 使用SiliconFlow AI (模型: Pro/deepseek-ai/DeepSeek-V3.2)", config.Name)
		}
	} else if config.UseQwen || config.AIModel == "qwen" {
		// 使用Qwen (支持自定义URL和Model)
		mcpClient.SetQwenAPIKey(config.QwenKey, config.CustomAPIURL, config.CustomModelName)
		if config.CustomAPIURL != "" || config.CustomModelName != "" {
			log.Printf("🤖 [%s] 使用阿里云Qwen AI (自定义URL: %s, 模型: %s)", config.Name, config.CustomAPIURL, config.CustomModelName)
		} else {
			log.Printf("🤖 [%s] 使用阿里云Qwen AI", config.Name)
		}
	} else {
		// 默认使用DeepSeek (支持自定义URL和Model)
		mcpClient.SetDeepSeekAPIKey(config.DeepSeekKey, config.CustomAPIURL, config.CustomModelName)
		if config.CustomAPIURL != "" || config.CustomModelName != "" {
			log.Printf("🤖 [%s] 使用DeepSeek AI (自定义URL: %s, 模型: %s)", config.Name, config.CustomAPIURL, config.CustomModelName)
		} else {
			log.Printf("🤖 [%s] 使用DeepSeek AI", config.Name)
		}
	}

	// 初始化币种池API
	if config.CoinPoolAPIURL != "" {
		pool.SetCoinPoolAPI(config.CoinPoolAPIURL)
	}

	// 设置默认交易平台
	if config.Exchange == "" {
		config.Exchange = "binance"
	}

	// 根据配置创建对应的交易器
	var trader Trader
	var err error

	// 记录仓位模式（通用）
	marginModeStr := "全仓"
	if !config.IsCrossMargin {
		marginModeStr = "逐仓"
	}
	log.Printf("📊 [%s] 仓位模式: %s", config.Name, marginModeStr)

	switch config.Exchange {
	case "binance":
		log.Printf("🏦 [%s] 使用币安合约交易 (testnet=%v)", config.Name, config.BinanceTestnet)
		trader = NewFuturesTrader(config.BinanceAPIKey, config.BinanceSecretKey, config.BinanceTestnet)
	case "hyperliquid":
		log.Printf("🏦 [%s] 使用Hyperliquid交易", config.Name)
		trader, err = NewHyperliquidTrader(config.HyperliquidPrivateKey, config.HyperliquidWalletAddr, config.HyperliquidTestnet)
		if err != nil {
			return nil, fmt.Errorf("初始化Hyperliquid交易器失败: %w", err)
		}
	case "aster":
		log.Printf("🏦 [%s] 使用Aster交易", config.Name)
		trader, err = NewAsterTrader(config.AsterUser, config.AsterSigner, config.AsterPrivateKey)
		if err != nil {
			return nil, fmt.Errorf("初始化Aster交易器失败: %w", err)
		}
	default:
		return nil, fmt.Errorf("不支持的交易平台: %s", config.Exchange)
	}

	// 验证初始金额配置
	if config.InitialBalance <= 0 {
		return nil, fmt.Errorf("初始金额必须大于0，请在配置中设置InitialBalance")
	}

	// 初始化决策日志记录器（使用trader ID创建独立目录）
	logDir := fmt.Sprintf("decision_logs/%s", config.ID)
	decisionLogger := logger.NewDecisionLogger(logDir)

	// 设置默认系统提示词模板
	systemPromptTemplate := config.SystemPromptTemplate
	if systemPromptTemplate == "" {
		systemPromptTemplate = "default" // 默认使用 default 模板
	}

	return &AutoTrader{
		id:                    config.ID,
		name:                  config.Name,
		aiModel:               config.AIModel,
		exchange:              config.Exchange,
		config:                config,
		trader:                trader,
		mcpClient:             mcpClient,
		decisionLogger:        decisionLogger,
		initialBalance:        config.InitialBalance,
		openPositions:         make(map[string]*logger.DecisionAction),
		systemPromptTemplate:  systemPromptTemplate,
		defaultCoins:          config.DefaultCoins,
		tradingCoins:          config.TradingCoins,
		lastResetTime:         time.Now(),
		startTime:             time.Now(),
		callCount:             0,
		isRunning:             false,
		positionFirstSeenTime: make(map[string]int64),
	}, nil
}

// Run 运行自动交易主循环
func (at *AutoTrader) Run() error {
	at.isRunning = true
	log.Println("🚀 AI驱动自动交易系统启动")
	log.Printf("💰 初始余额: %.2f USDT", at.initialBalance)
	log.Printf("⚙️  扫描间隔: %v", at.config.ScanInterval)
	log.Println("🤖 AI将全权决定杠杆、仓位大小、止损止盈等参数")

	ticker := time.NewTicker(at.config.ScanInterval)
	defer ticker.Stop()

	// 首次立即执行
	if err := at.runCycle(); err != nil {
		log.Printf("❌ 执行失败: %v", err)
	}

	for at.isRunning {
		select {
		case <-ticker.C:
			if err := at.runCycle(); err != nil {
				log.Printf("❌ 执行失败: %v", err)
			}
		}
	}

	return nil
}

// Stop 停止自动交易
func (at *AutoTrader) Stop() {
	at.isRunning = false
	log.Println("⏹ 自动交易系统停止")
}

// runCycle 运行一个交易周期（使用AI全权决策）
func (at *AutoTrader) runCycle() error {
	at.callCount++

	log.Print("\n" + strings.Repeat("=", 70) + "\n")
	log.Printf("⏰ %s - AI决策周期 #%d", time.Now().Format("2006-01-02 15:04:05"), at.callCount)
	log.Println(strings.Repeat("=", 70))

	// 创建决策记录
	record := &logger.DecisionRecord{
		ExecutionLog: []string{},
		Success:      true,
	}

	// 1. 检查是否需要停止交易
	if time.Now().Before(at.stopUntil) {
		remaining := at.stopUntil.Sub(time.Now())
		log.Printf("⏸ 风险控制：暂停交易中，剩余 %.0f 分钟", remaining.Minutes())
		record.Success = false
		record.ErrorMessage = fmt.Sprintf("风险控制暂停中，剩余 %.0f 分钟", remaining.Minutes())
		at.decisionLogger.LogDecision(record)
		return nil
	}

	// 2. 重置日盈亏（每天重置）
	if time.Since(at.lastResetTime) > 24*time.Hour {
		at.dailyPnL = 0
		at.lastResetTime = time.Now()
		log.Println("📅 日盈亏已重置")
	}

	// 3. 收集交易上下文
	ctx, err := at.buildTradingContext()
	if err != nil {
		record.Success = false
		record.ErrorMessage = fmt.Sprintf("构建交易上下文失败: %v", err)
		at.decisionLogger.LogDecision(record)
		return fmt.Errorf("构建交易上下文失败: %w", err)
	}

	// 保存账户状态快照
	record.AccountState = logger.AccountSnapshot{
		TotalBalance:          ctx.Account.TotalEquity,
		AvailableBalance:      ctx.Account.AvailableBalance,
		TotalUnrealizedProfit: ctx.Account.TotalPnL,
		PositionCount:         ctx.Account.PositionCount,
		MarginUsedPct:         ctx.Account.MarginUsedPct,
	}

	// 保存持仓快照
	for _, pos := range ctx.Positions {
		record.Positions = append(record.Positions, logger.PositionSnapshot{
			Symbol:           pos.Symbol,
			Side:             pos.Side,
			PositionAmt:      pos.Quantity,
			EntryPrice:       pos.EntryPrice,
			MarkPrice:        pos.MarkPrice,
			UnrealizedProfit: pos.UnrealizedPnL,
			Leverage:         float64(pos.Leverage),
			LiquidationPrice: pos.LiquidationPrice,
		})
	}

	// 保存候选币种列表
	for _, coin := range ctx.CandidateCoins {
		record.CandidateCoins = append(record.CandidateCoins, coin.Symbol)
	}

	log.Printf("📊 账户净值: %.2f USDT | 可用: %.2f USDT | 持仓: %d",
		ctx.Account.TotalEquity, ctx.Account.AvailableBalance, ctx.Account.PositionCount)

	// 4. 调用AI获取完整决策
	log.Printf("🤖 正在请求AI分析并决策... [模板: %s]", at.systemPromptTemplate)
	decision, err := decisionpkg.GetFullDecisionWithCustomPrompt(ctx, at.mcpClient, at.customPrompt, at.overrideBasePrompt, at.systemPromptTemplate)

	// 即使有错误，也保存思维链、决策和输入prompt（用于debug）
	if decision != nil {
		record.SystemPrompt = decision.SystemPrompt // 保存系统提示词
		record.InputPrompt = decision.UserPrompt
		record.CoTTrace = decision.CoTTrace
		record.AIRawResponse = decision.RawResponse
		if len(decision.Decisions) > 0 {
			decisionJSON, _ := json.MarshalIndent(decision.Decisions, "", "  ")
			record.DecisionJSON = string(decisionJSON)
		}
	}

	if err != nil {
		record.Success = false
		record.ErrorMessage = fmt.Sprintf("获取AI决策失败: %v", err)

		// 打印系统提示词和AI思维链（即使有错误，也要输出以便调试）
		if decision != nil {
			if decision.SystemPrompt != "" {
				log.Print("\n" + strings.Repeat("=", 70) + "\n")
				log.Printf("📋 系统提示词 [模板: %s] (错误情况)", at.systemPromptTemplate)
				log.Println(strings.Repeat("=", 70))
				log.Println(decision.SystemPrompt)
				log.Println(strings.Repeat("=", 70))
			}

			if decision.CoTTrace != "" {
				log.Print("\n" + strings.Repeat("-", 70) + "\n")
				log.Println("💭 AI思维链分析（错误情况）:")
				log.Println(strings.Repeat("-", 70))
				log.Println(decision.CoTTrace)
				log.Println(strings.Repeat("-", 70))
			}
		}

		at.decisionLogger.LogDecision(record)
		return fmt.Errorf("获取AI决策失败: %w", err)
	}

	// // 5. 打印系统提示词
	// log.Printf("\n" + strings.Repeat("=", 70))
	// log.Printf("📋 系统提示词 [模板: %s]", at.systemPromptTemplate)
	// log.Println(strings.Repeat("=", 70))
	// log.Println(decision.SystemPrompt)
	// log.Printf(strings.Repeat("=", 70) + "\n")

	// 6. 打印AI思维链
	// log.Printf("\n" + strings.Repeat("-", 70))
	// log.Println("💭 AI思维链分析:")
	// log.Println(strings.Repeat("-", 70))
	// log.Println(decision.CoTTrace)
	// log.Printf(strings.Repeat("-", 70) + "\n")

	// 7. 打印AI决策
	// log.Printf("📋 AI决策列表 (%d 个):\n", len(decision.Decisions))
	// for i, d := range decision.Decisions {
	// 	log.Printf("  [%d] %s: %s - %s", i+1, d.Symbol, d.Action, d.Reasoning)
	// 	if d.Action == "open_long" || d.Action == "open_short" {
	// 		log.Printf("      杠杆: %dx | 仓位: %.2f USDT | 止损: %.4f | 止盈: %.4f",
	// 			d.Leverage, d.PositionSizeUSD, d.StopLoss, d.TakeProfit)
	// 	}
	// }
	log.Println()

	// 8. 分离 close 和 open 操作，确保先执行所有 close，再执行所有 open
	// 注意：decision 是变量名（*decisionpkg.FullDecision），使用 decision.Decisions 访问决策列表
	var closeDecisions []decisionpkg.Decision
	var openDecisions []decisionpkg.Decision
	var otherDecisions []decisionpkg.Decision

	// 为了避免变量名和包名冲突，先获取决策列表
	decisionsList := decision.Decisions
	for _, d := range decisionsList {
		switch d.Action {
		case "close_long", "close_short":
			closeDecisions = append(closeDecisions, d)
		case "open_long", "open_short":
			openDecisions = append(openDecisions, d)
		default:
			otherDecisions = append(otherDecisions, d)
		}
	}

	log.Println("🔄 执行顺序（已优化）: 先执行所有平仓→刷新余额→再执行所有开仓")
	log.Printf("  📉 平仓操作: %d 个", len(closeDecisions))
	for i, d := range closeDecisions {
		log.Printf("    [%d] %s %s", i+1, d.Symbol, d.Action)
	}
	log.Printf("  📈 开仓操作: %d 个", len(openDecisions))
	for i, d := range openDecisions {
		log.Printf("    [%d] %s %s", i+1, d.Symbol, d.Action)
	}
	log.Println()

	// 第一步：执行所有 close 操作
	for _, d := range closeDecisions {
		actionRecord := logger.DecisionAction{
			Action:    d.Action,
			Symbol:    d.Symbol,
			Quantity:  0,
			Leverage:  d.Leverage,
			Price:     0,
			Timestamp: time.Now(),
			Success:   false,
		}

		if err := at.executeDecisionWithRecord(&d, &actionRecord); err != nil {
			log.Printf("❌ 执行决策失败 (%s %s): %v", d.Symbol, d.Action, err)
			actionRecord.Error = err.Error()
			record.ExecutionLog = append(record.ExecutionLog, fmt.Sprintf("❌ %s %s 失败: %v", d.Symbol, d.Action, err))
		} else {
			actionRecord.Success = true
			record.ExecutionLog = append(record.ExecutionLog, fmt.Sprintf("✓ %s %s 成功", d.Symbol, d.Action))
			// 成功执行后短暂延迟
			time.Sleep(1 * time.Second)
		}

		record.Decisions = append(record.Decisions, actionRecord)
	}

	// 第二步：所有 close 操作完成后，清除缓存并刷新余额
	if len(closeDecisions) > 0 && len(openDecisions) > 0 {
		log.Println("  🔄 平仓操作完成，正在清除缓存并刷新数据...")

		// 清除余额和仓位缓存（如果支持）
		if binanceTrader, ok := at.trader.(*FuturesTrader); ok {
			binanceTrader.ClearBalanceCache()
			binanceTrader.ClearPositionsCache() // 清除仓位缓存，确保开仓前获取最新数据
		}

		// ⚠️ 关键：等待API更新（2秒），避免平仓后立即开仓时API还未更新
		log.Println("  ⏱ 等待API更新（2秒）...")
		time.Sleep(2 * time.Second)

		// 强制刷新余额
		balance, err := at.trader.GetBalance()
		if err != nil {
			log.Printf("  ⚠ 刷新余额失败: %v", err)
		} else {
			if availableBalance, ok := balance["availableBalance"].(float64); ok {
				log.Printf("  ✓ 余额已刷新: 可用余额 = %.2f USDT", availableBalance)
			}
		}

		log.Println()
	}

	// 第三步：执行所有 open 操作
	for _, d := range openDecisions {
		actionRecord := logger.DecisionAction{
			Action:    d.Action,
			Symbol:    d.Symbol,
			Quantity:  0,
			Leverage:  d.Leverage,
			Price:     0,
			Timestamp: time.Now(),
			Success:   false,
		}

		if err := at.executeDecisionWithRecord(&d, &actionRecord); err != nil {
			log.Printf("❌ 执行决策失败 (%s %s): %v", d.Symbol, d.Action, err)
			actionRecord.Error = err.Error()
			record.ExecutionLog = append(record.ExecutionLog, fmt.Sprintf("❌ %s %s 失败: %v", d.Symbol, d.Action, err))
		} else {
			actionRecord.Success = true
			record.ExecutionLog = append(record.ExecutionLog, fmt.Sprintf("✓ %s %s 成功", d.Symbol, d.Action))
			// 成功执行后短暂延迟
			time.Sleep(1 * time.Second)
		}

		record.Decisions = append(record.Decisions, actionRecord)
	}

	// 第四步：执行其他操作（hold/wait等）
	for _, d := range otherDecisions {
		actionRecord := logger.DecisionAction{
			Action:    d.Action,
			Symbol:    d.Symbol,
			Quantity:  0,
			Leverage:  d.Leverage,
			Price:     0,
			Timestamp: time.Now(),
			Success:   true, // hold/wait 总是成功
		}
		record.Decisions = append(record.Decisions, actionRecord)
	}

	// 9. 保存决策记录（初始保存，不含成交数据）
	if err := at.decisionLogger.LogDecision(record); err != nil {
		log.Printf("⚠ 保存决策记录失败: %v", err)
	}

	// 10. 异步检测成交并更新记录（仅对成功的open/close操作）
	go at.checkAndUpdateTrades(record)

	return nil
}

// checkAndUpdateTrades 检测订单成交并更新决策记录
func (at *AutoTrader) checkAndUpdateTrades(record *logger.DecisionRecord) {
	// 只检测币安交易所的订单
	if at.exchange != "binance" {
		return
	}

	// 获取API配置
	apiKey := at.config.BinanceAPIKey
	secretKey := at.config.BinanceSecretKey
	baseURL := "https://fapi.binance.com"
	if at.config.BinanceTestnet {
		baseURL = "https://testnet.binancefuture.com"
	}

	// 检测每个决策动作的成交情况
	hasUpdates := false
	for i := range record.Decisions {
		action := &record.Decisions[i]

		// 只检测成功的open/close操作，且订单ID有效
		if !action.Success || action.OrderID == 0 {
			continue
		}

		isOpenOrClose := action.Action == "open_long" || action.Action == "open_short" ||
			action.Action == "close_long" || action.Action == "close_short"
		if !isOpenOrClose {
			continue
		}

		// 如果已经检测过，跳过
		if action.TradeChecked {
			continue
		}

		// 定期检测成交（最多检测30秒，每3秒检测一次）
		maxAttempts := 10
		checkInterval := 3 * time.Second

		for attempt := 0; attempt < maxAttempts; attempt++ {
			// 调用工具函数获取成交记录
			trades, err := at.getOrderTradesFromAPI(baseURL, apiKey, secretKey, action.Symbol, action.OrderID)
			if err != nil {
				log.Printf("⚠️  检测订单 %d 成交失败: %v", action.OrderID, err)
				time.Sleep(checkInterval)
				continue
			}

			if len(trades) > 0 {
				// 找到成交记录，更新到决策动作中
				action.TradeDetails = trades
				action.TradeChecked = true
				hasUpdates = true
				log.Printf("✓ 订单 %d (%s %s) 已成交，找到 %d 条成交记录",
					action.OrderID, action.Symbol, action.Action, len(trades))
				break
			}

			// 未找到成交记录，等待后重试
			if attempt < maxAttempts-1 {
				time.Sleep(checkInterval)
			}
		}

		// 如果检测超时仍未找到成交记录，标记为已检测（可能订单还未成交或已取消）
		if !action.TradeChecked {
			action.TradeChecked = true
			hasUpdates = true
			log.Printf("⚠️  订单 %d (%s %s) 检测超时，未找到成交记录",
				action.OrderID, action.Symbol, action.Action)
		}
	}

	// 如果有更新，保存到文件
	if pairUpdated := at.pairPositionsAndPnL(record); pairUpdated {
		hasUpdates = true
	}
	if hasUpdates {
		if err := at.decisionLogger.UpdateDecisionWithTrades(record); err != nil {
			log.Printf("⚠️  更新决策记录失败: %v", err)
		} else {
			log.Printf("📝 决策记录已更新成交数据")
		}
	}
}

// pairPositionsAndPnL 为平仓动作关联开仓，并计算盈亏
func (at *AutoTrader) pairPositionsAndPnL(record *logger.DecisionRecord) bool {
	updated := false

	for i := range record.Decisions {
		action := &record.Decisions[i]
		side := at.actionSide(action.Action)
		if side == "" {
			continue
		}

		key := at.positionKey(action.Symbol, side)

		// 开仓：补齐PositionID并登记
		if strings.HasPrefix(action.Action, "open_") {
			action.PositionID = at.ensurePositionID(action, action.Symbol, side)
			action.Closed = false
			at.openPositions[key] = action
			continue
		}

		// 平仓：寻找对应开仓
		if !strings.HasPrefix(action.Action, "close_") {
			continue
		}

		openAction, ok := at.openPositions[key]
		if !ok || openAction == nil || openAction.Closed {
			continue
		}

		action.PositionID = openAction.PositionID

		// 计算盈亏
		pnl, ratio, closeFee := at.calculatePNL(openAction, action, side)
		now := time.Now()

		action.PNL = pnl
		action.PNLRatio = ratio
		action.Fee = closeFee
		action.CloseTime = &now
		action.Closed = true

		openAction.PNL = pnl
		openAction.PNLRatio = ratio
		openAction.Fee += closeFee
		openAction.CloseTime = &now
		openAction.Closed = true

		delete(at.openPositions, key)
		updated = true
	}

	return updated
}

func (at *AutoTrader) ensurePositionID(action *logger.DecisionAction, symbol, side string) string {
	if action.PositionID == "" {
		action.PositionID = at.generatePositionID(symbol, side)
	}
	return action.PositionID
}

func (at *AutoTrader) generatePositionID(symbol, side string) string {
	return fmt.Sprintf("%s-%s-%d", strings.ToUpper(symbol), side, time.Now().UnixNano())
}

func (at *AutoTrader) positionKey(symbol, side string) string {
	return strings.ToUpper(symbol) + "_" + side
}

func (at *AutoTrader) actionSide(action string) string {
	switch action {
	case "open_long", "close_long":
		return "long"
	case "open_short", "close_short":
		return "short"
	default:
		return ""
	}
}

// attachOpenPosition 将平仓动作关联到开仓，并返回开仓动作指针
func (at *AutoTrader) attachOpenPosition(action *logger.DecisionAction, symbol, side string) *logger.DecisionAction {
	key := at.positionKey(symbol, side)
	openAction, ok := at.openPositions[key]
	if !ok || openAction == nil || openAction.Closed {
		return nil
	}

	action.PositionID = openAction.PositionID
	// 如果未来有持久化ID，可写入 openActionID；当前保留默认值
	return openAction
}

func (at *AutoTrader) aggregateTradeStats(trades []logger.TradeDetail, fallbackPrice float64, fallbackQty float64) (qty float64, quote float64, fee float64) {
	for _, t := range trades {
		q := t.QuoteQuantity
		if q == 0 {
			q = t.Price * t.Quantity
		}
		qty += t.Quantity
		quote += q
		fee += t.Commission
	}

	// 如果无成交明细，使用回退价格和数量估算
	if qty == 0 && fallbackQty > 0 {
		qty = fallbackQty
		quote = fallbackPrice * fallbackQty
	}

	return qty, quote, fee
}

func (at *AutoTrader) calculatePNL(openAction *logger.DecisionAction, closeAction *logger.DecisionAction, side string) (pnl float64, ratio float64, closeFee float64) {
	openQty, openQuote, openFee := at.aggregateTradeStats(openAction.TradeDetails, openAction.Price, openAction.Quantity)
	closeQty, closeQuote, closeFee := at.aggregateTradeStats(closeAction.TradeDetails, closeAction.Price, closeAction.Quantity)

	if openQty == 0 || closeQty == 0 {
		return 0, 0, closeFee
	}

	openNotional := openQuote
	closeNotional := closeQuote
	totalFee := openFee + closeFee

	if side == "long" {
		pnl = closeNotional - openNotional - totalFee
	} else {
		pnl = openNotional - closeNotional - totalFee
	}

	if openNotional != 0 {
		ratio = pnl / openNotional
	}

	// 回写开仓手续费，便于后续统计
	openAction.Fee = openFee
	return pnl, ratio, closeFee
}

// getOrderTradesFromAPI 从币安API获取订单成交记录
func (at *AutoTrader) getOrderTradesFromAPI(baseURL, apiKey, secretKey, symbol string, orderID int64) ([]logger.TradeDetail, error) {
	// 这里需要调用tools中的函数，但由于包结构限制，我们直接实现
	// 或者可以通过HTTP调用独立的工具程序

	// 简化实现：直接使用HTTP请求
	ctx := context.Background()
	var allTrades []logger.TradeDetail
	httpClient := &http.Client{Timeout: 10 * time.Second}

	// 查询最近1小时的交易记录
	startTime := time.Now().Add(-1 * time.Hour).UnixMilli()
	endTime := time.Now().UnixMilli()
	fromID := int64(0)
	limit := 100

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
		signature := at.generateSignature(queryString, secretKey)

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
			return nil, fmt.Errorf("API返回错误: %s", resp.Status)
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
				detail := at.parseTradeDetail(trade)
				allTrades = append(allTrades, detail)
			}
		}

		if len(trades) < limit {
			break
		}

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
func (at *AutoTrader) generateSignature(queryString, secretKey string) string {
	mac := hmac.New(sha256.New, []byte(secretKey))
	mac.Write([]byte(queryString))
	return hex.EncodeToString(mac.Sum(nil))
}

// parseTradeDetail 解析成交记录
func (at *AutoTrader) parseTradeDetail(trade map[string]interface{}) logger.TradeDetail {
	detail := logger.TradeDetail{}

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

// buildTradingContext 构建交易上下文
func (at *AutoTrader) buildTradingContext() (*decisionpkg.Context, error) {
	// 1. 获取账户信息
	balance, err := at.trader.GetBalance()
	if err != nil {
		return nil, fmt.Errorf("获取账户余额失败: %w", err)
	}

	// 获取账户字段
	totalWalletBalance := 0.0
	totalUnrealizedProfit := 0.0
	availableBalance := 0.0

	if wallet, ok := balance["totalWalletBalance"].(float64); ok {
		totalWalletBalance = wallet
	}
	if unrealized, ok := balance["totalUnrealizedProfit"].(float64); ok {
		totalUnrealizedProfit = unrealized
	}
	if avail, ok := balance["availableBalance"].(float64); ok {
		availableBalance = avail
	}

	// Total Equity = 钱包余额 + 未实现盈亏
	totalEquity := totalWalletBalance + totalUnrealizedProfit

	// 2. 获取持仓信息
	positions, err := at.trader.GetPositions()
	if err != nil {
		return nil, fmt.Errorf("获取持仓失败: %w", err)
	}

	var positionInfos []decisionpkg.PositionInfo
	totalMarginUsed := 0.0

	// 当前持仓的key集合（用于清理已平仓的记录）
	currentPositionKeys := make(map[string]bool)

	for _, pos := range positions {
		symbol := pos["symbol"].(string)
		side := pos["side"].(string)
		entryPrice := pos["entryPrice"].(float64)
		markPrice := pos["markPrice"].(float64)
		quantity := pos["positionAmt"].(float64)
		if quantity < 0 {
			quantity = -quantity // 空仓数量为负，转为正数
		}
		unrealizedPnl := pos["unRealizedProfit"].(float64)
		liquidationPrice := pos["liquidationPrice"].(float64)

		// 计算盈亏百分比
		pnlPct := 0.0
		if side == "long" {
			pnlPct = ((markPrice - entryPrice) / entryPrice) * 100
		} else {
			pnlPct = ((entryPrice - markPrice) / entryPrice) * 100
		}

		// 计算占用保证金（估算）
		leverage := 10 // 默认值，实际应该从持仓信息获取
		if lev, ok := pos["leverage"].(float64); ok {
			leverage = int(lev)
		}
		marginUsed := (quantity * markPrice) / float64(leverage)
		totalMarginUsed += marginUsed

		// 跟踪持仓首次出现时间
		posKey := symbol + "_" + side
		currentPositionKeys[posKey] = true
		if _, exists := at.positionFirstSeenTime[posKey]; !exists {
			// 新持仓，记录当前时间
			at.positionFirstSeenTime[posKey] = time.Now().UnixMilli()
		}
		updateTime := at.positionFirstSeenTime[posKey]

		positionInfos = append(positionInfos, decisionpkg.PositionInfo{
			Symbol:           symbol,
			Side:             side,
			EntryPrice:       entryPrice,
			MarkPrice:        markPrice,
			Quantity:         quantity,
			Leverage:         leverage,
			UnrealizedPnL:    unrealizedPnl,
			UnrealizedPnLPct: pnlPct,
			LiquidationPrice: liquidationPrice,
			MarginUsed:       marginUsed,
			UpdateTime:       updateTime,
		})
	}

	// 清理已平仓的持仓记录
	for key := range at.positionFirstSeenTime {
		if !currentPositionKeys[key] {
			delete(at.positionFirstSeenTime, key)
		}
	}

	// 3. 获取交易员的候选币种池
	candidateCoins, err := at.getCandidateCoins()
	if err != nil {
		return nil, fmt.Errorf("获取候选币种失败: %w", err)
	}

	// 4. 计算总盈亏
	totalPnL := totalEquity - at.initialBalance
	totalPnLPct := 0.0
	if at.initialBalance > 0 {
		totalPnLPct = (totalPnL / at.initialBalance) * 100
	}

	marginUsedPct := 0.0
	if totalEquity > 0 {
		marginUsedPct = (totalMarginUsed / totalEquity) * 100
	}

	// 计算剩余可用保证金
	availableMargin := totalEquity - totalMarginUsed
	if availableMargin < 0 {
		availableMargin = 0 // 确保不为负数
	}

	// 5. 分析历史表现（最近100个周期，避免长期持仓的交易记录丢失）
	// 假设每3分钟一个周期，100个周期 = 5小时，足够覆盖大部分交易
	performance, err := at.decisionLogger.AnalyzePerformance(100)
	if err != nil {
		log.Printf("⚠️  分析历史表现失败: %v", err)
		// 不影响主流程，继续执行（但设置performance为nil以避免传递错误数据）
		performance = nil
	}

	// 6. 构建上下文
	ctx := &decisionpkg.Context{
		CurrentTime:     time.Now().Format("2006-01-02 15:04:05"),
		RuntimeMinutes:  int(time.Since(at.startTime).Minutes()),
		CallCount:       at.callCount,
		BTCETHLeverage:  at.config.BTCETHLeverage,  // 使用配置的杠杆倍数
		AltcoinLeverage: at.config.AltcoinLeverage, // 使用配置的杠杆倍数
		Account: decisionpkg.AccountInfo{
			TotalEquity:      totalEquity,
			AvailableBalance: availableBalance,
			TotalPnL:         totalPnL,
			TotalPnLPct:      totalPnLPct,
			MarginUsed:       totalMarginUsed,
			MarginUsedPct:    marginUsedPct,
			AvailableMargin:  availableMargin,
			PositionCount:    len(positionInfos),
		},
		Positions:      positionInfos,
		CandidateCoins: candidateCoins,
		Performance:    performance, // 添加历史表现分析
		PromptFields:   at.config.PromptDataFields,
		RAGEnabled:     at.config.RAGEnabled,
	}

	return ctx, nil
}

// executeDecisionWithRecord 执行AI决策并记录详细信息
func (at *AutoTrader) executeDecisionWithRecord(decision *decisionpkg.Decision, actionRecord *logger.DecisionAction) error {
	switch decision.Action {
	case "open_long":
		return at.executeOpenLongWithRecord(decision, actionRecord)
	case "open_short":
		return at.executeOpenShortWithRecord(decision, actionRecord)
	case "close_long":
		return at.executeCloseLongWithRecord(decision, actionRecord)
	case "close_short":
		return at.executeCloseShortWithRecord(decision, actionRecord)
	case "hold", "wait":
		// 无需执行，仅记录
		return nil
	default:
		return fmt.Errorf("未知的action: %s", decision.Action)
	}
}

// executeOpenLongWithRecord 执行开多仓并记录详细信息
func (at *AutoTrader) executeOpenLongWithRecord(decision *decisionpkg.Decision, actionRecord *logger.DecisionAction) error {
	log.Printf("  📈 开多仓: %s", decision.Symbol)

	// ⚠️ 关键：检查是否已有同币种同方向持仓，如果有则拒绝开仓（防止仓位叠加超限）
	positions, err := at.trader.GetPositions()
	if err == nil {
		for _, pos := range positions {
			if pos["symbol"] == decision.Symbol && pos["side"] == "long" {
				return fmt.Errorf("❌ %s 已有多仓，拒绝开仓以防止仓位叠加超限。如需换仓，请先给出 close_long 决策", decision.Symbol)
			}
		}
	}

	// 获取当前价格
	marketData, err := market.Get(decision.Symbol)
	if err != nil {
		return err
	}

	// 计算数量
	quantity := decision.PositionSizeUSD / marketData.CurrentPrice
	actionRecord.Quantity = quantity
	actionRecord.Price = marketData.CurrentPrice

	// 设置仓位模式
	if err := at.trader.SetMarginMode(decision.Symbol, at.config.IsCrossMargin); err != nil {
		log.Printf("  ⚠️ 设置仓位模式失败: %v", err)
		// 继续执行，不影响交易
	}

	// 开仓
	order, err := at.trader.OpenLong(decision.Symbol, quantity, decision.Leverage)
	if err != nil {
		return err
	}

	// 记录订单ID
	if orderID, ok := order["orderId"].(int64); ok {
		actionRecord.OrderID = orderID
	}

	// 生成并记录仓位ID，标记为未平仓
	actionRecord.PositionID = at.ensurePositionID(actionRecord, decision.Symbol, "long")
	actionRecord.Closed = false
	at.openPositions[at.positionKey(decision.Symbol, "long")] = actionRecord

	log.Printf("  ✓ 开仓成功，订单ID: %v, 数量: %.4f", order["orderId"], quantity)

	// 记录开仓时间
	posKey := decision.Symbol + "_long"
	at.positionFirstSeenTime[posKey] = time.Now().UnixMilli()

	// 设置止损止盈
	if err := at.trader.SetStopLoss(decision.Symbol, "LONG", quantity, decision.StopLoss); err != nil {
		log.Printf("  ⚠ 设置止损失败: %v", err)
	}
	if err := at.trader.SetTakeProfit(decision.Symbol, "LONG", quantity, decision.TakeProfit); err != nil {
		log.Printf("  ⚠ 设置止盈失败: %v", err)
	}

	return nil
}

// executeOpenShortWithRecord 执行开空仓并记录详细信息
func (at *AutoTrader) executeOpenShortWithRecord(decision *decisionpkg.Decision, actionRecord *logger.DecisionAction) error {
	log.Printf("  📉 开空仓: %s", decision.Symbol)

	// ⚠️ 关键：检查是否已有同币种同方向持仓，如果有则拒绝开仓（防止仓位叠加超限）
	positions, err := at.trader.GetPositions()
	if err == nil {
		for _, pos := range positions {
			if pos["symbol"] == decision.Symbol && pos["side"] == "short" {
				return fmt.Errorf("❌ %s 已有空仓，拒绝开仓以防止仓位叠加超限。如需换仓，请先给出 close_short 决策", decision.Symbol)
			}
		}
	}

	// 获取当前价格
	marketData, err := market.Get(decision.Symbol)
	if err != nil {
		return err
	}

	// 计算数量
	quantity := decision.PositionSizeUSD / marketData.CurrentPrice
	actionRecord.Quantity = quantity
	actionRecord.Price = marketData.CurrentPrice

	// 设置仓位模式
	if err := at.trader.SetMarginMode(decision.Symbol, at.config.IsCrossMargin); err != nil {
		log.Printf("  ⚠️ 设置仓位模式失败: %v", err)
		// 继续执行，不影响交易
	}

	// 开仓
	order, err := at.trader.OpenShort(decision.Symbol, quantity, decision.Leverage)
	if err != nil {
		return err
	}

	// 记录订单ID
	if orderID, ok := order["orderId"].(int64); ok {
		actionRecord.OrderID = orderID
	}

	// 生成并记录仓位ID，标记为未平仓
	actionRecord.PositionID = at.ensurePositionID(actionRecord, decision.Symbol, "short")
	actionRecord.Closed = false
	at.openPositions[at.positionKey(decision.Symbol, "short")] = actionRecord

	log.Printf("  ✓ 开仓成功，订单ID: %v, 数量: %.4f", order["orderId"], quantity)

	// 记录开仓时间
	posKey := decision.Symbol + "_short"
	at.positionFirstSeenTime[posKey] = time.Now().UnixMilli()

	// 设置止损止盈
	if err := at.trader.SetStopLoss(decision.Symbol, "SHORT", quantity, decision.StopLoss); err != nil {
		log.Printf("  ⚠ 设置止损失败: %v", err)
	}
	if err := at.trader.SetTakeProfit(decision.Symbol, "SHORT", quantity, decision.TakeProfit); err != nil {
		log.Printf("  ⚠ 设置止盈失败: %v", err)
	}

	return nil
}

// executeCloseLongWithRecord 执行平多仓并记录详细信息
func (at *AutoTrader) executeCloseLongWithRecord(decision *decisionpkg.Decision, actionRecord *logger.DecisionAction) error {
	log.Printf("  🔄 平多仓: %s", decision.Symbol)

	// 关联到已开仓位
	openAction := at.attachOpenPosition(actionRecord, decision.Symbol, "long")
	if openAction == nil {
		log.Printf("  ⚠ 未找到待平多仓的开仓记录，symbol=%s", decision.Symbol)
	}

	// 获取当前价格
	marketData, err := market.Get(decision.Symbol)
	if err != nil {
		return err
	}
	actionRecord.Price = marketData.CurrentPrice

	// 平仓
	order, err := at.trader.CloseLong(decision.Symbol, 0) // 0 = 全部平仓
	if err != nil {
		return err
	}

	// 记录订单ID
	if orderID, ok := order["orderId"].(int64); ok {
		actionRecord.OrderID = orderID
	}

	log.Printf("  ✓ 平仓成功")

	// 标记开仓已提交平仓请求，避免重复匹配
	if openAction != nil {
		openAction.Closed = true
	}
	return nil
}

// executeCloseShortWithRecord 执行平空仓并记录详细信息
func (at *AutoTrader) executeCloseShortWithRecord(decision *decisionpkg.Decision, actionRecord *logger.DecisionAction) error {
	log.Printf("  🔄 平空仓: %s", decision.Symbol)

	// 关联到已开仓位
	openAction := at.attachOpenPosition(actionRecord, decision.Symbol, "short")
	if openAction == nil {
		log.Printf("  ⚠ 未找到待平空仓的开仓记录，symbol=%s", decision.Symbol)
	}

	// 获取当前价格
	marketData, err := market.Get(decision.Symbol)
	if err != nil {
		return err
	}
	actionRecord.Price = marketData.CurrentPrice

	// 平仓
	order, err := at.trader.CloseShort(decision.Symbol, 0) // 0 = 全部平仓
	if err != nil {
		return err
	}

	// 记录订单ID
	if orderID, ok := order["orderId"].(int64); ok {
		actionRecord.OrderID = orderID
	}

	log.Printf("  ✓ 平仓成功")

	// 标记开仓已提交平仓请求，避免重复匹配
	if openAction != nil {
		openAction.Closed = true
	}
	return nil
}

// GetID 获取trader ID
func (at *AutoTrader) GetID() string {
	return at.id
}

// GetName 获取trader名称
func (at *AutoTrader) GetName() string {
	return at.name
}

// GetAIModel 获取AI模型
func (at *AutoTrader) GetAIModel() string {
	return at.aiModel
}

// GetExchange 获取交易所
func (at *AutoTrader) GetExchange() string {
	return at.exchange
}

// SetCustomPrompt 设置自定义交易策略prompt
func (at *AutoTrader) SetCustomPrompt(prompt string) {
	at.customPrompt = prompt
}

// SetOverrideBasePrompt 设置是否覆盖基础prompt
func (at *AutoTrader) SetOverrideBasePrompt(override bool) {
	at.overrideBasePrompt = override
}

// SetSystemPromptTemplate 设置系统提示词模板
func (at *AutoTrader) SetSystemPromptTemplate(templateName string) {
	at.systemPromptTemplate = templateName
}

// GetSystemPromptTemplate 获取当前系统提示词模板名称
func (at *AutoTrader) GetSystemPromptTemplate() string {
	return at.systemPromptTemplate
}

// GetDecisionLogger 获取决策日志记录器
func (at *AutoTrader) GetDecisionLogger() *logger.DecisionLogger {
	return at.decisionLogger
}

// GetStatus 获取系统状态（用于API）
func (at *AutoTrader) GetStatus() map[string]interface{} {
	aiProvider := "DeepSeek"
	if at.config.UseQwen {
		aiProvider = "Qwen"
	}

	return map[string]interface{}{
		"trader_id":       at.id,
		"trader_name":     at.name,
		"ai_model":        at.aiModel,
		"exchange":        at.exchange,
		"is_running":      at.isRunning,
		"start_time":      at.startTime.Format(time.RFC3339),
		"runtime_minutes": int(time.Since(at.startTime).Minutes()),
		"call_count":      at.callCount,
		"initial_balance": at.initialBalance,
		"scan_interval":   at.config.ScanInterval.String(),
		"stop_until":      at.stopUntil.Format(time.RFC3339),
		"last_reset_time": at.lastResetTime.Format(time.RFC3339),
		"ai_provider":     aiProvider,
	}
}

// GetAccountInfo 获取账户信息（用于API）
func (at *AutoTrader) GetAccountInfo() (map[string]interface{}, error) {
	balance, err := at.trader.GetBalance()
	if err != nil {
		return nil, fmt.Errorf("获取余额失败: %w", err)
	}

	// 获取账户字段
	totalWalletBalance := 0.0
	totalUnrealizedProfit := 0.0
	availableBalance := 0.0

	if wallet, ok := balance["totalWalletBalance"].(float64); ok {
		totalWalletBalance = wallet
	}
	if unrealized, ok := balance["totalUnrealizedProfit"].(float64); ok {
		totalUnrealizedProfit = unrealized
	}
	if avail, ok := balance["availableBalance"].(float64); ok {
		availableBalance = avail
	}

	// Total Equity = 钱包余额 + 未实现盈亏
	totalEquity := totalWalletBalance + totalUnrealizedProfit

	// 获取持仓计算总保证金
	positions, err := at.trader.GetPositions()
	if err != nil {
		return nil, fmt.Errorf("获取持仓失败: %w", err)
	}

	totalMarginUsed := 0.0
	totalUnrealizedPnL := 0.0
	for _, pos := range positions {
		markPrice := pos["markPrice"].(float64)
		quantity := pos["positionAmt"].(float64)
		if quantity < 0 {
			quantity = -quantity
		}
		unrealizedPnl := pos["unRealizedProfit"].(float64)
		totalUnrealizedPnL += unrealizedPnl

		leverage := 10
		if lev, ok := pos["leverage"].(float64); ok {
			leverage = int(lev)
		}
		marginUsed := (quantity * markPrice) / float64(leverage)
		totalMarginUsed += marginUsed
	}

	totalPnL := totalEquity - at.initialBalance
	totalPnLPct := 0.0
	if at.initialBalance > 0 {
		totalPnLPct = (totalPnL / at.initialBalance) * 100
	}

	marginUsedPct := 0.0
	if totalEquity > 0 {
		marginUsedPct = (totalMarginUsed / totalEquity) * 100
	}

	// 计算剩余可用保证金
	availableMargin := totalEquity - totalMarginUsed
	if availableMargin < 0 {
		availableMargin = 0 // 确保不为负数
	}

	return map[string]interface{}{
		// 核心字段
		"total_equity":      totalEquity,           // 账户净值 = wallet + unrealized
		"wallet_balance":    totalWalletBalance,    // 钱包余额（不含未实现盈亏）
		"unrealized_profit": totalUnrealizedProfit, // 未实现盈亏（从API）
		"available_balance": availableBalance,      // 可用余额

		// 盈亏统计
		"total_pnl":            totalPnL,           // 总盈亏 = equity - initial
		"total_pnl_pct":        totalPnLPct,        // 总盈亏百分比
		"total_unrealized_pnl": totalUnrealizedPnL, // 未实现盈亏（从持仓计算）
		"initial_balance":      at.initialBalance,  // 初始余额
		"daily_pnl":            at.dailyPnL,        // 日盈亏

		// 持仓信息
		"position_count":   len(positions),  // 持仓数量
		"margin_used":      totalMarginUsed, // 保证金占用
		"margin_used_pct":  marginUsedPct,   // 保证金使用率
		"available_margin": availableMargin, // 剩余可用保证金
	}, nil
}

// GetPositions 获取持仓列表（用于API）
func (at *AutoTrader) GetPositions() ([]map[string]interface{}, error) {
	positions, err := at.trader.GetPositions()
	if err != nil {
		return nil, fmt.Errorf("获取持仓失败: %w", err)
	}

	var result []map[string]interface{}
	for _, pos := range positions {
		symbol := pos["symbol"].(string)
		side := pos["side"].(string)
		entryPrice := pos["entryPrice"].(float64)
		markPrice := pos["markPrice"].(float64)
		quantity := pos["positionAmt"].(float64)
		if quantity < 0 {
			quantity = -quantity
		}
		unrealizedPnl := pos["unRealizedProfit"].(float64)
		liquidationPrice := pos["liquidationPrice"].(float64)

		leverage := 10
		if lev, ok := pos["leverage"].(float64); ok {
			leverage = int(lev)
		}

		// 计算占用保证金
		marginUsed := (quantity * markPrice) / float64(leverage)

		// 计算盈亏百分比（基于保证金）
		// 收益率 = 未实现盈亏 / 保证金 × 100%
		pnlPct := 0.0
		if marginUsed > 0 {
			pnlPct = (unrealizedPnl / marginUsed) * 100
		}

		result = append(result, map[string]interface{}{
			"symbol":             symbol,
			"side":               side,
			"entry_price":        entryPrice,
			"mark_price":         markPrice,
			"quantity":           quantity,
			"leverage":           leverage,
			"unrealized_pnl":     unrealizedPnl,
			"unrealized_pnl_pct": pnlPct,
			"liquidation_price":  liquidationPrice,
			"margin_used":        marginUsed,
		})
	}

	return result, nil
}

// sortDecisionsByPriority 对决策排序：先平仓，再开仓，最后hold/wait
// 这样可以避免换仓时仓位叠加超限
func sortDecisionsByPriority(decisions []decisionpkg.Decision) []decisionpkg.Decision {
	if len(decisions) <= 1 {
		return decisions
	}

	// 定义优先级
	getActionPriority := func(action string) int {
		switch action {
		case "close_long", "close_short":
			return 1 // 最高优先级：先平仓
		case "open_long", "open_short":
			return 2 // 次优先级：后开仓
		case "hold", "wait":
			return 3 // 最低优先级：观望
		default:
			return 999 // 未知动作放最后
		}
	}

	// 复制决策列表
	sorted := make([]decisionpkg.Decision, len(decisions))
	copy(sorted, decisions)

	// 按优先级排序
	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if getActionPriority(sorted[i].Action) > getActionPriority(sorted[j].Action) {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	return sorted
}

// getCandidateCoins 获取交易员的候选币种列表
func (at *AutoTrader) getCandidateCoins() ([]decisionpkg.CandidateCoin, error) {
	if len(at.tradingCoins) == 0 {
		// 使用数据库配置的默认币种列表
		var candidateCoins []decisionpkg.CandidateCoin

		if len(at.defaultCoins) > 0 {
			// 使用数据库中配置的默认币种
			for _, coin := range at.defaultCoins {
				symbol := normalizeSymbol(coin)
				candidateCoins = append(candidateCoins, decisionpkg.CandidateCoin{
					Symbol:  symbol,
					Sources: []string{"default"}, // 标记为数据库默认币种
				})
			}
			log.Printf("📋 [%s] 使用数据库默认币种: %d个币种 %v",
				at.name, len(candidateCoins), at.defaultCoins)
			return candidateCoins, nil
		} else {
			// 如果数据库中没有配置默认币种，则使用AI500+OI Top作为fallback
			const ai500Limit = 20 // AI500取前20个评分最高的币种

			mergedPool, err := pool.GetMergedCoinPool(ai500Limit)
			if err != nil {
				return nil, fmt.Errorf("获取合并币种池失败: %w", err)
			}

			// 构建候选币种列表（包含来源信息）
			for _, symbol := range mergedPool.AllSymbols {
				sources := mergedPool.SymbolSources[symbol]
				candidateCoins = append(candidateCoins, decisionpkg.CandidateCoin{
					Symbol:  symbol,
					Sources: sources, // "ai500" 和/或 "oi_top"
				})
			}

			log.Printf("📋 [%s] 数据库无默认币种配置，使用AI500+OI Top: AI500前%d + OI_Top20 = 总计%d个候选币种",
				at.name, ai500Limit, len(candidateCoins))
			return candidateCoins, nil
		}
	} else {
		// 使用自定义币种列表
		var candidateCoins []decisionpkg.CandidateCoin
		for _, coin := range at.tradingCoins {
			// 确保币种格式正确（转为大写USDT交易对）
			symbol := normalizeSymbol(coin)
			candidateCoins = append(candidateCoins, decisionpkg.CandidateCoin{
				Symbol:  symbol,
				Sources: []string{"custom"}, // 标记为自定义来源
			})
		}

		log.Printf("📋 [%s] 使用自定义币种: %d个币种 %v",
			at.name, len(candidateCoins), at.tradingCoins)
		return candidateCoins, nil
	}
}

// normalizeSymbol 标准化币种符号（确保以USDT结尾）
func normalizeSymbol(symbol string) string {
	// 转为大写
	symbol = strings.ToUpper(strings.TrimSpace(symbol))

	// 确保以USDT结尾
	if !strings.HasSuffix(symbol, "USDT") {
		symbol = symbol + "USDT"
	}

	return symbol
}
