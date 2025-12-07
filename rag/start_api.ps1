# ChromaDB RAG API 服务启动脚本（PowerShell）

Write-Host "🚀 启动 ChromaDB RAG API 服务..." -ForegroundColor Green

# 检查 Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "❌ 未找到 Python，请先安装 Python" -ForegroundColor Red
    exit 1
}

# 检查依赖
Write-Host "📦 检查依赖..." -ForegroundColor Yellow
python -c "import chromadb, flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  缺少依赖，正在安装..." -ForegroundColor Yellow
    pip install -r rag/requirements.txt
}

# 设置环境变量（可选）
if (-not $env:RAG_API_PORT) {
    $env:RAG_API_PORT = "8765"
}
if (-not $env:RAG_API_HOST) {
    $env:RAG_API_HOST = "127.0.0.1"
}

Write-Host "✅ 启动服务..." -ForegroundColor Green
Write-Host "   - 地址: http://$env:RAG_API_HOST`:$env:RAG_API_PORT" -ForegroundColor Cyan
Write-Host "   - 按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动服务
python rag/chromadb_api.py

