# 迁移数据库脚本

Write-Host "迁移 Pentosh1 数据库结构..." -ForegroundColor Green

# 检查数据库
$dbPath = "filter\pentosh1.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "数据库不存在: $dbPath" -ForegroundColor Yellow
    Write-Host "将创建新数据库" -ForegroundColor Cyan
}

# 运行迁移脚本
python filter/migrate_database.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "迁移完成！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "迁移失败" -ForegroundColor Red
    exit 1
}

