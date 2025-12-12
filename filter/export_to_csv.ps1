# 导出 pentosh1.db 到 CSV

Write-Host "导出 Pentosh1 数据库到 CSV..." -ForegroundColor Green

# 检查数据库
$dbPath = "filter\pentosh1.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "数据库不存在: $dbPath" -ForegroundColor Red
    exit 1
}

# 运行导出脚本
python filter/export_to_csv.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "导出完成！" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "导出失败" -ForegroundColor Red
    exit 1
}









