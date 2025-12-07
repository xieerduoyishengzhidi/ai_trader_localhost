# Pentosh1 新闻筛选启动脚本（PowerShell）

Write-Host "启动 Pentosh1 新闻筛选系统..." -ForegroundColor Green

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    Write-Host "未找到 Python，请先安装 Python" -ForegroundColor Red
    exit 1
}

# 检查 API Key
$apiKeyEnv = $env:DEEPSEEK_API_KEY
if ([string]::IsNullOrEmpty($apiKeyEnv)) {
    Write-Host "未设置 DEEPSEEK_API_KEY 环境变量" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请设置 API Key:" -ForegroundColor Cyan
    Write-Host '   $env:DEEPSEEK_API_KEY="your_api_key_here"' -ForegroundColor White
    Write-Host ""
    $apiKey = Read-Host "请输入 DeepSeek API Key"
    if (-not [string]::IsNullOrEmpty($apiKey)) {
        $env:DEEPSEEK_API_KEY = $apiKey
        Write-Host "API Key 已设置（仅本次会话有效）" -ForegroundColor Green
    } else {
        Write-Host "未提供 API Key，退出" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# 检查依赖
Write-Host "检查依赖..." -ForegroundColor Yellow
python -c "import openai" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "缺少依赖，正在安装..." -ForegroundColor Yellow
    pip install -r filter/requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 检查源数据库
$sourceDb = "news_service\history_news.db"
if (-not (Test-Path $sourceDb)) {
    Write-Host "源数据库不存在: $sourceDb" -ForegroundColor Red
    exit 1
}

Write-Host "环境检查通过" -ForegroundColor Green
Write-Host ""
$separator = "=".PadRight(80, "=")
Write-Host $separator -ForegroundColor Cyan
Write-Host ""

# 运行筛选脚本
python filter/pentosh1_filter.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "筛选完成！结果已保存到 filter/pentosh1.db" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "筛选失败，请检查错误信息" -ForegroundColor Red
    exit 1
}

