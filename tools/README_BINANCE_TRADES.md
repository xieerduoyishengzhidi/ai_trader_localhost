# Binance U本位合约历史交易记录下载工具

这个工具可以自动下载Binance U本位合约的历史交易记录。

## 功能特点

- ✅ 支持下载指定交易对或所有交易对的历史记录
- ✅ 支持指定时间范围（注意：Binance API仅支持最近6个月的数据）
- ✅ 自动分页获取所有数据
- ✅ 支持导出为CSV或JSON格式
- ✅ 支持测试网和主网

## 使用方法

### 1. 编译工具（可选，已预编译）

工具已经预编译为 `binance_trades_downloader.exe`，可以直接使用。

如果需要重新编译：

```powershell
# 在tools目录下执行
cd tools
go build -o binance_trades_downloader.exe download_binance_trades.go
```

### 2. 基本用法

#### 下载指定交易对的历史记录

```powershell
.\tools\binance_trades_downloader.exe -api-key "YOUR_API_KEY" -secret-key "YOUR_SECRET_KEY" -symbol "BTCUSDT" -output "btc_trades.csv"
```

#### 指定时间范围

```powershell
.\tools\binance_trades_downloader.exe -api-key "YOUR_API_KEY" -secret-key "YOUR_SECRET_KEY" -symbol "BTCUSDT" -start-time "2024-01-01" -end-time "2024-12-31" -output "btc_trades_2024.csv"
```

#### 下载所有交易对的记录

```powershell
.\tools\binance_trades_downloader.exe -api-key "YOUR_API_KEY" -secret-key "YOUR_SECRET_KEY" -output "all_trades.csv"
```

#### 导出为JSON格式

```powershell
.\tools\binance_trades_downloader.exe -api-key "YOUR_API_KEY" -secret-key "YOUR_SECRET_KEY" -symbol "BTCUSDT" -format json -output "btc_trades.json"
```

#### 使用测试网

```powershell
.\tools\binance_trades_downloader.exe -api-key "YOUR_API_KEY" -secret-key "YOUR_SECRET_KEY" -symbol "BTCUSDT" -testnet
```

## 命令行参数

| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `-api-key` | Binance API Key | ✅ 是 | - |
| `-secret-key` | Binance Secret Key | ✅ 是 | - |
| `-symbol` | 交易对符号（如 BTCUSDT） | ❌ 否 | 空（下载所有交易对） |
| `-start-time` | 开始时间 | ❌ 否 | 6个月前 |
| `-end-time` | 结束时间 | ❌ 否 | 当前时间 |
| `-output` | 输出文件名 | ❌ 否 | trades.csv |
| `-format` | 输出格式（csv/json） | ❌ 否 | 根据文件扩展名自动判断 |
| `-testnet` | 使用测试网 | ❌ 否 | false |
| `-limit` | 每次请求的最大记录数 | ❌ 否 | 1000 |

## 时间格式

支持以下时间格式：
- `2024-01-01`
- `2024-01-01 15:04:05`
- `2024-01-01T15:04:05`
- `2024/01/01`
- `2024/01/01 15:04:05`

## 输出格式

### CSV格式

CSV文件包含以下列：
- 交易对
- 交易ID
- 订单ID
- 价格
- 数量
- 成交额
- 手续费
- 手续费币种
- 时间
- 是否买方
- 是否做市商
- 是否逐仓
- 持仓方向

### JSON格式

JSON文件包含交易记录数组，每个记录包含所有字段。

## 注意事项

1. **API限制**：Binance API仅支持查询最近6个月的数据。如果需要更早的数据，需要使用Binance的异步下载接口。

2. **API权限**：确保你的API Key具有"读取"权限。

3. **请求频率**：工具已内置请求延迟（100ms），避免触发API限流。

4. **数据量**：下载所有交易对的数据可能需要较长时间，建议先测试单个交易对。

5. **安全性**：不要将API Key和Secret Key提交到代码仓库。建议使用环境变量或配置文件。

## 示例

### 下载最近一个月的BTC交易记录

```powershell
$startTime = (Get-Date).AddMonths(-1).ToString("yyyy-MM-dd")
.\tools\binance_trades_downloader.exe -api-key $env:BINANCE_API_KEY -secret-key $env:BINANCE_SECRET_KEY -symbol "BTCUSDT" -start-time $startTime -output "btc_trades_last_month.csv"
```

### 下载所有交易对并保存为JSON

```powershell
.\tools\binance_trades_downloader.exe -api-key $env:BINANCE_API_KEY -secret-key $env:BINANCE_SECRET_KEY -format json -output "all_trades.json"
```

## API参考

本工具使用Binance Futures API的以下接口：
- `GET /fapi/v1/userTrades` - 获取账户交易历史

更多信息请参考：[Binance API文档](https://binance-docs.github.io/apidocs/futures/cn/#user_data-2)

## 故障排除

### 错误：必须提供 API Key 和 Secret Key
- 确保提供了 `-api-key` 和 `-secret-key` 参数

### 错误：获取交易记录失败
- 检查API Key和Secret Key是否正确
- 检查API Key是否有读取权限
- 检查网络连接

### 警告：Binance API 仅支持查询最近6个月的数据
- 这是Binance API的限制，无法获取更早的数据
- 如需更早的数据，请使用Binance的异步下载接口

