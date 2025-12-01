# 测试 Docker 容器中的 TA-Lib 是否正常工作

Write-Host "🔍 测试 Docker 容器中的 TA-Lib..." -ForegroundColor Cyan

# 检查镜像是否存在
$imageExists = docker images | Select-String "nofx-backend"
if (-not $imageExists) {
    Write-Host "❌ 错误：nofx-backend 镜像不存在" -ForegroundColor Red
    Write-Host "请先运行: docker build -f docker/Dockerfile.backend -t nofx-backend ." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 镜像存在" -ForegroundColor Green

# 测试 1: 检查 TA-Lib 库文件是否存在
Write-Host ""
Write-Host "📦 测试 1: 检查 TA-Lib 库文件..." -ForegroundColor Cyan
$libTest = docker run --rm nofx-backend sh -c "ls -la /usr/local/lib/libta_lib*" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ TA-Lib 库文件不存在" -ForegroundColor Red
    exit 1
}
Write-Host "✅ TA-Lib 库文件存在" -ForegroundColor Green

# 测试 2: 检查头文件是否存在
Write-Host ""
Write-Host "📦 测试 2: 检查 TA-Lib 头文件..." -ForegroundColor Cyan
$headerTest = docker run --rm nofx-backend sh -c "ls -la /usr/local/include/ta-lib/ta_libc.h" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ TA-Lib 头文件不存在" -ForegroundColor Red
    exit 1
}
Write-Host "✅ TA-Lib 头文件存在" -ForegroundColor Green

# 测试 3: 检查 LD_LIBRARY_PATH 环境变量
Write-Host ""
Write-Host "📦 测试 3: 检查 LD_LIBRARY_PATH..." -ForegroundColor Cyan
$envTest = docker run --rm nofx-backend sh -c "echo `$LD_LIBRARY_PATH"
if ($envTest -notmatch "/usr/local/lib") {
    Write-Host "❌ LD_LIBRARY_PATH 未正确设置" -ForegroundColor Red
    exit 1
}
Write-Host "✅ LD_LIBRARY_PATH 正确设置: $envTest" -ForegroundColor Green

# 测试 4: 检查可执行文件
Write-Host ""
Write-Host "📦 测试 4: 检查可执行文件..." -ForegroundColor Cyan
$exeTest = docker run --rm nofx-backend sh -c "file /app/nofx" 2>&1
if ($exeTest -notmatch "ELF") {
    Write-Host "❌ 可执行文件不存在或格式错误" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 可执行文件存在且格式正确" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 所有测试通过！TA-Lib 在 Docker 中配置正确！" -ForegroundColor Green
Write-Host ""
Write-Host "💡 下一步：" -ForegroundColor Yellow
Write-Host "   1. 运行容器: docker run -p 8080:8080 nofx-backend" -ForegroundColor White
Write-Host "   2. 或使用 docker-compose: docker-compose up" -ForegroundColor White

