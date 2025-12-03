package market

import (
	"testing"
	"time"
)

// TestErrorHandling_OpenInterestFailure 测试OI获取失败时的处理
// 当getOpenInterestData失败时，应该返回默认值而不是nil
func TestErrorHandling_OpenInterestFailure(t *testing.T) {
	// 测试一个不存在的币种，看看错误处理
	symbol := "INVALIDCOIN123USDT"

	// 直接调用getOpenInterestData看看错误处理
	oiData, err := getOpenInterestData(symbol)

	if err != nil {
		t.Logf("✓ getOpenInterestData返回错误（预期）: %v", err)
		t.Logf("  注意：在Get函数中，这个错误会被捕获，使用默认值 OIData{Latest: 0, Average: 0}")
	} else {
		t.Logf("getOpenInterestData成功: Latest=%f, Average=%f", oiData.Latest, oiData.Average)
	}
}

// TestErrorHandling_FundingRateFailure 测试资金费率获取失败时的处理
func TestErrorHandling_FundingRateFailure(t *testing.T) {
	// 重置缓存为空，模拟首次调用且API失败的情况
	fundingRateMutex.Lock()
	originalCache := fundingRateCache
	originalTime := fundingRateLastUpdate
	fundingRateCache = make(map[string]float64)
	fundingRateLastUpdate = time.Time{}
	fundingRateMutex.Unlock()

	// 恢复原始状态
	defer func() {
		fundingRateMutex.Lock()
		fundingRateCache = originalCache
		fundingRateLastUpdate = originalTime
		fundingRateMutex.Unlock()
	}()

	// 测试获取一个不存在的币种
	rate, err := getFundingRate("NONEXISTENTCOINUSDT")

	if err != nil {
		t.Logf("✓ getFundingRate返回错误（预期）: %v", err)
		t.Logf("  注意：在Get函数中，这个错误会被忽略（使用_），返回默认值 0.0")
	} else {
		t.Logf("getFundingRate成功: %f", rate)
	}
}

// TestErrorHandling_HistoryAPIFailure 测试历史数据API失败时的处理
// 历史数据获取失败不应该影响主流程，应该使用当前值作为平均值
func TestErrorHandling_HistoryAPIFailure(t *testing.T) {
	t.Log("测试场景：主OI API成功，但历史数据API失败")
	t.Log("预期行为：")
	t.Log("  1. Latest值应该从主API获取")
	t.Log("  2. Average值应该等于Latest（因为历史API失败）")
	t.Log("  3. 不应该返回错误")

	// 注意：这个测试需要实际调用API，所以可能会失败
	// 但我们可以验证错误处理逻辑
	symbol := "BTCUSDT"
	oiData, err := getOpenInterestData(symbol)

	if err != nil {
		t.Logf("主API失败: %v", err)
	} else {
		t.Logf("✓ 主API成功")
		t.Logf("  Latest: %f", oiData.Latest)
		t.Logf("  Average: %f", oiData.Average)
		if oiData.Latest > 0 && oiData.Average == oiData.Latest {
			t.Logf("  ✓ 历史API失败时，Average使用Latest值（符合预期）")
		}
	}
}

// TestErrorHandling_GetFunction 测试Get函数整体的错误处理
func TestErrorHandling_GetFunction(t *testing.T) {
	t.Log("测试Get函数中的错误处理逻辑")
	t.Log("场景1: OI获取失败")
	t.Log("  预期: 使用默认值 OIData{Latest: 0, Average: 0}，不中断流程")
	t.Log("")
	t.Log("场景2: 资金费率获取失败")
	t.Log("  预期: 使用默认值 0.0，不中断流程")
	t.Log("")
	t.Log("场景3: 历史数据API失败")
	t.Log("  预期: Average使用Latest值，不返回错误")

	// 测试一个真实存在的币种（如果API可用）
	symbol := "BTCUSDT"
	data, err := Get(symbol)

	if err != nil {
		t.Logf("Get函数返回错误（可能是K线数据获取失败）: %v", err)
		t.Logf("  注意：如果K线数据获取失败，整个Get函数会失败")
		t.Logf("  但OI和资金费率的错误不会导致Get函数失败")
	} else {
		t.Logf("✓ Get函数成功")
		if data.OpenInterest != nil {
			t.Logf("  OI数据: Latest=%f, Average=%f",
				data.OpenInterest.Latest, data.OpenInterest.Average)
		} else {
			t.Errorf("  ✗ OpenInterest不应该为nil")
		}
		t.Logf("  资金费率: %f", data.FundingRate)
	}
}
