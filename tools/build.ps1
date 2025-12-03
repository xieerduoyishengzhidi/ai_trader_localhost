# Binance交易记录下载工具编译脚本

Write-Host "🔨 正在编译 Binance 交易记录下载工具..." -ForegroundColor Cyan

# 检查Go是否安装
$goVersion = go version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 错误: 未找到 Go 编译器，请先安装 Go" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Go 版本: $goVersion" -ForegroundColor Green

# 编译
$outputPath = "binance_trades_downloader.exe"
go build -o $outputPath download_binance_trades.go

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 编译成功！可执行文件: $outputPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "使用方法:" -ForegroundColor Yellow
    Write-Host "  .\$outputPath -api-key YOUR_API_KEY -secret-key YOUR_SECRET_KEY -symbol BTCUSDT" -ForegroundColor White
} else {
    Write-Host "❌ 编译失败" -ForegroundColor Red
    exit 1
}

