# 下载两天内所有交易对的交易记录示例
# 数据按时间顺序从旧到新排列

# 设置API密钥（请替换为您的实际密钥）
$env:BINANCE_API_KEY = "YOUR_API_KEY"
$env:BINANCE_SECRET_KEY = "YOUR_SECRET_KEY"

# 检查API密钥是否设置
if ($env:BINANCE_API_KEY -eq "YOUR_API_KEY" -or $env:BINANCE_SECRET_KEY -eq "YOUR_SECRET_KEY") {
    Write-Host "❌ 错误: 请先设置API密钥！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请修改脚本中的以下行：" -ForegroundColor Yellow
    Write-Host '  $env:BINANCE_API_KEY = "YOUR_API_KEY"' -ForegroundColor White
    Write-Host '  $env:BINANCE_SECRET_KEY = "YOUR_SECRET_KEY"' -ForegroundColor White
    exit 1
}

# 计算两天前的时间
$endTime = Get-Date
$startTime = $endTime.AddDays(-2)

# 格式化时间（格式: 2024-01-01）
$startTimeStr = $startTime.ToString("yyyy-MM-dd")
$endTimeStr = $endTime.ToString("yyyy-MM-dd")

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📥 下载最近2天的所有交易对交易记录" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "时间范围: $startTimeStr 至 $endTimeStr" -ForegroundColor Yellow
Write-Host "数据顺序: 从旧到新（按时间顺序）" -ForegroundColor Yellow
Write-Host "输出文件: trades_2days.csv" -ForegroundColor Yellow
Write-Host ""
Write-Host "将下载以下交易对（来自config.json的default_coins，共29个）：" -ForegroundColor Cyan
$symbols = @(
	"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "HYPEUSDT",
	"TRXUSDT", "XLMUSDT", "BCHUSDT", "LINKUSDT", "ZECUSDT", "HBARUSDT", "LTCUSDT", "UNIUSDT",
	"AVAXUSDT", "SUIUSDT", "1000SHIBUSDT", "WLFIUSDT", "TONUSDT", "DOTUSDT", "TAOUSDT",
	"AAVEUSDT", "BANKUSDT", "METUSDT", "ALLOUSDT", "OMUSDT", "BICOUSDT"
)
foreach ($symbol in $symbols) {
	Write-Host "  - $symbol" -ForegroundColor White
}
Write-Host ""
Write-Host "开始下载..." -ForegroundColor Green
Write-Host ""

# 下载所有交易对的记录（不指定symbol参数）
# 工具会自动下载config.json中配置的交易对
.\binance_trades_downloader.exe `
    -api-key $env:BINANCE_API_KEY `
    -secret-key $env:BINANCE_SECRET_KEY `
    -start-time $startTimeStr `
    -end-time $endTimeStr `
    -output "trades_2days.csv"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "✅ 下载完成！" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "文件已保存到: trades_2days.csv" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "提示: 可以使用Excel或其他工具打开CSV文件查看数据" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ 下载失败，请检查错误信息" -ForegroundColor Red
}

