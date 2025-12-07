# 故障排除指南

## 常见错误和解决方案

### 1. TypeError: '>' not supported between instances of 'NoneType' and 'int'

**原因**: 数据获取失败，返回了 None 值，但代码没有检查就直接比较。

**解决方案**: ✅ 已修复 - 添加了 None 值检查

### 2. FRED API 返回 500 错误

**可能原因**:
- FRED API Key 无效或过期
- 网络连接问题
- 数据系列ID不存在

**解决方案**:
1. 检查 FRED API Key:
   ```powershell
   $env:FRED_API_KEY="bd89c0475f61d7555dee50daed12185f"
   ```

2. 检查 Macro Service 日志，查看具体错误信息

3. 验证数据系列ID是否正确（如 WALCL, WTREGEN, RRPONTSYD）

### 3. yfinance API 返回 404 错误

**可能原因**:
- Symbol 格式错误
- 数据为空（周末或节假日）
- yfinance 库版本问题

**解决方案**:
1. 检查 Symbol 格式:
   - ✅ `DX-Y.NYB` (美元指数)
   - ✅ `^TNX` (10年美债)
   - ✅ `^GSPC` (标普500)
   - ✅ `CNH=X` (人民币汇率)

2. 增加数据周期（已修复）:
   - 从 `1mo` 改为 `3mo`，确保有足够数据

3. 检查 yfinance 版本:
   ```powershell
   pip install yfinance==0.2.40
   ```

### 4. Macro Service 无法连接

**解决方案**:
1. 确认 Macro Service 正在运行:
   ```powershell
   cd macro_service
   python app.py
   ```

2. 检查端口是否被占用:
   ```powershell
   netstat -ano | findstr :8001
   ```

3. 检查防火墙设置

### 5. 部分数据缺失

**正常情况**: 某些数据源可能暂时不可用，程序会继续运行并使用可用数据。

**检查方法**:
- 查看日志中的警告信息
- 检查生成的 JSON 文件，查看哪些字段为 null

## 调试技巧

### 1. 启用详细日志

在 `main.py` 中修改日志级别:
```python
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. 单独测试 API 端点

```powershell
# 测试 FRED API
$body = @{
    series_id = "DGS2"
    start_date = "2024-12-01"
    end_date = "2025-01-06"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/fred/series" -Method POST -Body $body -ContentType "application/json"

# 测试 yfinance API
$body = @{
    symbol = "^TNX"
    period = "3mo"
    interval = "1d"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/yfinance/quote" -Method POST -Body $body -ContentType "application/json"
```

### 3. 检查 Macro Service 健康状态

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

应该返回:
```json
{
  "status": "ok",
  "fred_available": true,
  "yfinance_available": true,
  ...
}
```

## 数据验证

### 检查生成的 JSON 文件

```powershell
# 查看输出文件
Get-Content output/Daily_Context_2025-01-06.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### 验证数据完整性

检查以下关键字段是否存在:
- `layer1_global_liquidity.indicators` - 应该包含多个指标
- `layer2_crypto_flows.etf_net_inflow_m` - ETF数据
- `layer3_market_structure.btc_dominance` - BTC Dominance
- `layer4_sentiment.funding_rate_annualized_pct` - 资金费率
- `pentosh1_signals.overall_bias` - 交易信号

## 性能优化

如果 API 调用太慢，可以考虑:
1. 增加超时时间（已设置为30秒）
2. 使用缓存机制（未来可添加）
3. 并行调用独立的数据源（未来可优化）

