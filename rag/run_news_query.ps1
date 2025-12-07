# 新闻 RAG 查询脚本（PowerShell）

Write-Host "🚀 开始新闻 RAG 混合搜索查询..." -ForegroundColor Green

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "❌ 未找到 Python，请先安装 Python" -ForegroundColor Red
    exit 1
}

# 检查依赖
Write-Host "📦 检查依赖..." -ForegroundColor Yellow
python -c "import requests, sqlite3" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  缺少依赖，正在安装..." -ForegroundColor Yellow
    pip install requests
}

# 检查 RAG API 服务是否运行
Write-Host "🔍 检查 RAG API 服务..." -ForegroundColor Yellow
$apiUrl = "http://127.0.0.1:8765/health"
try {
    $response = Invoke-WebRequest -Uri $apiUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ RAG API 服务正在运行" -ForegroundColor Green
} catch {
    Write-Host "⚠️  RAG API 服务未运行，请先启动服务:" -ForegroundColor Yellow
    Write-Host "   .\rag\start_api.ps1" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "是否继续？(y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}

Write-Host ""
Write-Host "✅ 开始执行查询..." -ForegroundColor Green
Write-Host ""

# 运行 Python 脚本
python rag/query_news_with_rag.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ 查询完成！结果已保存到 rag/news_rag_query_results.txt" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ 查询失败，请检查错误信息" -ForegroundColor Red
    exit 1
}

