# News Service 依赖安装脚本
# PowerShell 脚本，用于安装 Python 依赖

Write-Host "📦 开始安装 News Service 依赖..." -ForegroundColor Cyan

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ 检测到 Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未检测到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "`n正在安装依赖包..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 依赖安装完成！" -ForegroundColor Green
    Write-Host "`n现在可以运行: python news_rss_fetcher.py" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ 依赖安装失败，请检查错误信息" -ForegroundColor Red
    exit 1
}

