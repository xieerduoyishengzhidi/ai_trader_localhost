# Binance交易记录下载工具使用示例

# 设置API密钥（请替换为您的实际密钥）
$env:BINANCE_API_KEY = "sXK6tEj3DnleB8y8h4t3csWvEsbmOIoJfNejkv7is6Zimanqh9v08gHsBNWljUFb"
$env:BINANCE_SECRET_KEY = "1S778ekgCs0gas82tLVq28mhwzvcFUwb5QoCoNuxOgO02Xl0eSSkLTamDk5EjApQ"

Write-Host "`n示例0: 下载所有两天内交易对的记录" -ForegroundColor Cyan
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -testnet `
    -start-time "2025-11-30" `
    -output "all_trades.csv"
# 示例1: 下载BTCUSDT的交易记录
Write-Host "示例1: 下载BTCUSDT的交易记录" -ForegroundColor Cyan
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -symbol "BTCUSDT" `
    -output "btc_trades.csv"

# 示例2: 下载指定时间范围的交易记录
Write-Host "`n示例2: 下载指定时间范围的交易记录" -ForegroundColor Cyan
$startTime = (Get-Date).AddMonths(-1).ToString("yyyy-MM-dd")
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -symbol "ETHUSDT" `
    -start-time $startTime `
    -output "eth_trades_last_month.csv"

# 示例3: 下载为JSON格式
Write-Host "`n示例3: 下载为JSON格式" -ForegroundColor Cyan
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -symbol "BNBUSDT" `
    -format json `
    -output "bnb_trades.json"

# 示例4: 下载所有常见交易对的记录
Write-Host "`n示例4: 下载所有常见交易对的记录" -ForegroundColor Cyan
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -output "all_trades.csv"

Write-Host "`n✅ 所有示例执行完成！" -ForegroundColor Green

