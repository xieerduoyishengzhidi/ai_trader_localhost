# PowerShell 脚本：安装依赖（Windows优化版）
# 使用预编译的wheel包，避免编译问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "安装 Macro Service 依赖" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 升级 pip
Write-Host "升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host ""
Write-Host "安装基础依赖（使用预编译包）..." -ForegroundColor Yellow

# 先安装 numpy（使用预编译包）
Write-Host "安装 numpy..." -ForegroundColor Green
pip install numpy --only-binary :all:

# 再安装 pandas（使用预编译包）
Write-Host "安装 pandas..." -ForegroundColor Green
pip install pandas --only-binary :all:

# 安装其他依赖
Write-Host "安装其他依赖..." -ForegroundColor Green
pip install flask==3.0.0
pip install pydantic==2.5.0
pip install fredapi==0.5.1
pip install yfinance==0.2.40
pip install requests==2.31.0
pip install ccxt==4.2.25
pip install lxml

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# 验证安装
Write-Host ""
Write-Host "验证安装..." -ForegroundColor Yellow
python -c "import flask; import fredapi; import yfinance; import ccxt; import pandas; import numpy; print('✅ 所有依赖安装成功')"

