# Export Trader Logs Script
# Usage: .\export_trader_logs.ps1 -TraderId "your_trader_id"
# Example: .\export_trader_logs.ps1 -TraderId "binance_admin_deepseek_1762252655"

param(
    [Parameter(Mandatory=$false)]
    [string]$TraderId,
    
    [Parameter(Mandatory=$false)]
    [string]$DbPath = "config.db",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "exports"
)

# Check sqlite3
$sqlite3 = Get-Command sqlite3 -ErrorAction SilentlyContinue
if (-not $sqlite3) {
    Write-Host "[ERROR] sqlite3 not found. Install: winget install SQLite.SQLite" -ForegroundColor Red
    exit 1
}

# Check database file
if (-not (Test-Path $DbPath)) {
    Write-Host "[ERROR] Database not found: $DbPath" -ForegroundColor Red
    exit 1
}

# List all traders if no TraderId specified
if (-not $TraderId) {
    Write-Host ""
    Write-Host "=== Available Traders ===" -ForegroundColor Cyan
    Write-Host ""
    
    $traders = sqlite3 $DbPath "SELECT id, name, exchange_id, is_running, created_at FROM traders ORDER BY created_at DESC;"
    if ($traders) {
        Write-Host "ID | Name | Exchange | Running | Created"
        Write-Host ("-" * 80)
        $traders | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host "No traders found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Usage: .\export_trader_logs.ps1 -TraderId 'trader_id'" -ForegroundColor Green
    exit 0
}

# Create output directory
$exportDir = Join-Path $OutputDir $TraderId
if (-not (Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host ""
Write-Host "=== Exporting Trader: $TraderId ===" -ForegroundColor Cyan
Write-Host ""

# 1. Export decision logs
Write-Host "[1/5] Exporting decision logs..." -ForegroundColor Yellow
$logsFile = Join-Path $exportDir "decision_logs_$timestamp.csv"

$logsQuery = @"
SELECT 
    id,
    trader_id,
    datetime(timestamp) as timestamp,
    cycle_number,
    substr(cot_trace, 1, 200) as cot_trace_preview,
    substr(decision_json, 1, 500) as decision_json,
    success,
    error_message,
    datetime(created_at) as created_at
FROM trader_decision_logs
WHERE trader_id = '$TraderId'
ORDER BY timestamp DESC;
"@

sqlite3 -header -csv $DbPath $logsQuery | Out-File -FilePath $logsFile -Encoding UTF8

$logsCount = sqlite3 $DbPath "SELECT COUNT(*) FROM trader_decision_logs WHERE trader_id = '$TraderId';"
Write-Host "      Exported $logsCount decision logs -> $logsFile" -ForegroundColor Green

# 2. Export decision actions (orders)
Write-Host "[2/5] Exporting orders..." -ForegroundColor Yellow
$actionsFile = Join-Path $exportDir "orders_$timestamp.csv"

$actionsQuery = @"
SELECT 
    a.id,
    l.trader_id,
    a.decision_log_id,
    a.action,
    a.symbol,
    a.quantity,
    a.leverage,
    a.price,
    a.order_id,
    a.position_id,
    a.open_action_id,
    a.closed,
    datetime(a.close_time) as close_time,
    a.pnl,
    a.pnl_ratio,
    a.fee,
    datetime(a.timestamp) as timestamp,
    a.success,
    a.error,
    a.trade_checked
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId'
ORDER BY a.timestamp DESC;
"@

sqlite3 -header -csv $DbPath $actionsQuery | Out-File -FilePath $actionsFile -Encoding UTF8

$actionsCount = sqlite3 $DbPath "SELECT COUNT(*) FROM trader_decision_actions a JOIN trader_decision_logs l ON a.decision_log_id = l.id WHERE l.trader_id = '$TraderId';"
Write-Host "      Exported $actionsCount orders -> $actionsFile" -ForegroundColor Green

# 3. Export trade details
Write-Host "[3/5] Exporting trade details..." -ForegroundColor Yellow
$tradesFile = Join-Path $exportDir "trades_$timestamp.csv"

$tradesQuery = @"
SELECT 
    t.id,
    l.trader_id,
    a.symbol,
    a.action,
    t.decision_action_id,
    t.trade_id,
    t.price,
    t.quantity,
    t.quote_quantity,
    t.commission,
    t.commission_asset,
    datetime(t.time/1000, 'unixepoch', 'localtime') as trade_time,
    t.is_buyer,
    t.is_maker
FROM trader_trade_details t
JOIN trader_decision_actions a ON t.decision_action_id = a.id
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId'
ORDER BY t.time DESC;
"@

sqlite3 -header -csv $DbPath $tradesQuery | Out-File -FilePath $tradesFile -Encoding UTF8

$tradesCount = sqlite3 $DbPath "SELECT COUNT(*) FROM trader_trade_details t JOIN trader_decision_actions a ON t.decision_action_id = a.id JOIN trader_decision_logs l ON a.decision_log_id = l.id WHERE l.trader_id = '$TraderId';"
Write-Host "      Exported $tradesCount trade details -> $tradesFile" -ForegroundColor Green

# 4. Export full decision logs (JSON)
Write-Host "[4/5] Exporting full logs (JSON)..." -ForegroundColor Yellow
$fullLogsFile = Join-Path $exportDir "full_logs_$timestamp.json"

$fullLogsQuery = @"
SELECT 
    id,
    trader_id,
    datetime(timestamp) as timestamp,
    cycle_number,
    system_prompt,
    user_prompt,
    cot_trace,
    decision_json,
    ai_raw_response,
    account_state_json,
    positions_json,
    candidate_coins_json,
    execution_log_json,
    success,
    error_message,
    datetime(created_at) as created_at
FROM trader_decision_logs
WHERE trader_id = '$TraderId'
ORDER BY timestamp DESC
LIMIT 100;
"@

sqlite3 -json $DbPath $fullLogsQuery | Out-File -FilePath $fullLogsFile -Encoding UTF8
Write-Host "      Exported last 100 full logs -> $fullLogsFile" -ForegroundColor Green

# 5. Generate PnL summary
Write-Host "[5/5] Generating PnL summary..." -ForegroundColor Yellow
$summaryFile = Join-Path $exportDir "pnl_summary_$timestamp.txt"

$summaryContent = @"
================================================================================
TRADER PnL SUMMARY REPORT
================================================================================
Trader ID: $TraderId
Export Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
================================================================================

[ORDER STATISTICS]
"@

$orderStatsQuery = @"
SELECT 
    'Total Orders: ' || COUNT(*) || char(10) ||
    'Successful: ' || SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) || char(10) ||
    'Failed: ' || SUM(CASE WHEN a.success = 0 THEN 1 ELSE 0 END) || char(10) ||
    'Open Long: ' || SUM(CASE WHEN a.action = 'open_long' THEN 1 ELSE 0 END) || char(10) ||
    'Close Long: ' || SUM(CASE WHEN a.action = 'close_long' THEN 1 ELSE 0 END) || char(10) ||
    'Open Short: ' || SUM(CASE WHEN a.action = 'open_short' THEN 1 ELSE 0 END) || char(10) ||
    'Close Short: ' || SUM(CASE WHEN a.action = 'close_short' THEN 1 ELSE 0 END)
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId';
"@

$orderStats = sqlite3 $DbPath $orderStatsQuery
$summaryContent += "`n$orderStats"

$summaryContent += @"

[PnL STATISTICS]
"@

$pnlStatsQuery = @"
SELECT 
    'Closed Trades: ' || COUNT(*) || char(10) ||
    'Total PnL (USDT): ' || ROUND(COALESCE(SUM(pnl), 0), 4) || char(10) ||
    'Winning Trades: ' || SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) || char(10) ||
    'Losing Trades: ' || SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) || char(10) ||
    'Total Profit (USDT): ' || ROUND(COALESCE(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 0), 4) || char(10) ||
    'Total Loss (USDT): ' || ROUND(COALESCE(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END), 0), 4) || char(10) ||
    'Average PnL (USDT): ' || ROUND(COALESCE(AVG(pnl), 0), 4) || char(10) ||
    'Win Rate: ' || ROUND(100.0 * SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) || '%'
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId' AND a.closed = 1;
"@

$pnlStats = sqlite3 $DbPath $pnlStatsQuery
$summaryContent += "`n$pnlStats"

$summaryContent += @"

[PnL BY SYMBOL]
"@

$symbolPnlQuery = @"
SELECT 
    symbol || ': ' || 
    ROUND(COALESCE(SUM(pnl), 0), 4) || ' USDT (' || 
    COUNT(*) || ' trades, WinRate ' || 
    ROUND(100.0 * SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) || '%)'
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId' AND a.closed = 1
GROUP BY symbol
ORDER BY SUM(pnl) DESC;
"@

$symbolPnl = sqlite3 $DbPath $symbolPnlQuery
$summaryContent += "`n$symbolPnl"

$summaryContent += @"

[TOTAL FEES]
"@

$feeQuery = @"
SELECT 
    'Total Fees (USDT): ' || ROUND(COALESCE(SUM(fee), 0), 4)
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TraderId';
"@

$feeStats = sqlite3 $DbPath $feeQuery
$summaryContent += "`n$feeStats"

$summaryContent | Out-File -FilePath $summaryFile -Encoding UTF8
Write-Host "      Generated PnL summary -> $summaryFile" -ForegroundColor Green

# 6. Check and export from decision_logs folder
$fileLogsDir = Join-Path "decision_logs" $TraderId
if (Test-Path $fileLogsDir) {
    Write-Host "[6/6] Exporting from file logs..." -ForegroundColor Yellow
    $fileLogsCount = (Get-ChildItem $fileLogsDir -Filter "*.json" | Measure-Object).Count
    
    if ($fileLogsCount -gt 0) {
        $fileLogsExportDir = Join-Path $exportDir "file_logs"
        if (-not (Test-Path $fileLogsExportDir)) {
            New-Item -ItemType Directory -Path $fileLogsExportDir -Force | Out-Null
        }
        
        # Copy all JSON files
        Copy-Item "$fileLogsDir\*.json" $fileLogsExportDir -Force
        Write-Host "      Copied $fileLogsCount file logs -> $fileLogsExportDir" -ForegroundColor Green
    } else {
        Write-Host "      No file logs found" -ForegroundColor Yellow
    }
} else {
    Write-Host "[6/6] No file logs directory found for this trader" -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host ("=" * 60)
Write-Host "Export Complete!" -ForegroundColor Green
Write-Host "Output directory: $exportDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Exported files:"
Get-ChildItem $exportDir -Filter "*$timestamp*" | ForEach-Object {
    $sizeKB = [math]::Round($_.Length / 1KB, 2)
    Write-Host "   - $($_.Name) ($sizeKB KB)"
}

# Show file logs if any
$fileLogsExportDir = Join-Path $exportDir "file_logs"
if (Test-Path $fileLogsExportDir) {
    $fileLogsCount = (Get-ChildItem $fileLogsExportDir -Filter "*.json" | Measure-Object).Count
    Write-Host "   - file_logs/ ($fileLogsCount JSON files)"
}
