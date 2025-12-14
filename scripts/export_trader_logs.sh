#!/bin/bash
# Export Trader Logs Script (Linux/macOS)
# Usage: ./export_trader_logs.sh [trader_id]
# Example: ./export_trader_logs.sh binance_admin_deepseek_1762252655

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Config
DB_PATH="${DB_PATH:-config.db}"
OUTPUT_DIR="${OUTPUT_DIR:-exports}"
TRADER_ID="$1"

# Check sqlite3
if ! command -v sqlite3 &> /dev/null; then
    echo -e "${RED}[ERROR] sqlite3 not found. Install: apt install sqlite3${NC}"
    exit 1
fi

# Check database file
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}[ERROR] Database not found: $DB_PATH${NC}"
    exit 1
fi

# List all traders if no TraderId specified
if [ -z "$TRADER_ID" ]; then
    echo ""
    echo -e "${CYAN}=== Available Traders ===${NC}"
    echo ""
    echo "ID | Name | Exchange | Running | Created"
    echo "--------------------------------------------------------------------------------"
    sqlite3 "$DB_PATH" "SELECT id, name, exchange_id, is_running, created_at FROM traders ORDER BY created_at DESC;"
    echo ""
    echo -e "${GREEN}Usage: ./export_trader_logs.sh 'trader_id'${NC}"
    exit 0
fi

# Create output directory
EXPORT_DIR="$OUTPUT_DIR/$TRADER_ID"
mkdir -p "$EXPORT_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo ""
echo -e "${CYAN}=== Exporting Trader: $TRADER_ID ===${NC}"
echo ""

# 1. Export decision logs
echo -e "${YELLOW}[1/6] Exporting decision logs...${NC}"
LOGS_FILE="$EXPORT_DIR/decision_logs_$TIMESTAMP.csv"

sqlite3 -header -csv "$DB_PATH" "
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
WHERE trader_id = '$TRADER_ID'
ORDER BY timestamp DESC;
" > "$LOGS_FILE"

LOGS_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trader_decision_logs WHERE trader_id = '$TRADER_ID';")
echo -e "      ${GREEN}Exported $LOGS_COUNT decision logs -> $LOGS_FILE${NC}"

# 2. Export decision actions (orders)
echo -e "${YELLOW}[2/6] Exporting orders...${NC}"
ACTIONS_FILE="$EXPORT_DIR/orders_$TIMESTAMP.csv"

sqlite3 -header -csv "$DB_PATH" "
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
WHERE l.trader_id = '$TRADER_ID'
ORDER BY a.timestamp DESC;
" > "$ACTIONS_FILE"

ACTIONS_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trader_decision_actions a JOIN trader_decision_logs l ON a.decision_log_id = l.id WHERE l.trader_id = '$TRADER_ID';")
echo -e "      ${GREEN}Exported $ACTIONS_COUNT orders -> $ACTIONS_FILE${NC}"

# 3. Export trade details
echo -e "${YELLOW}[3/6] Exporting trade details...${NC}"
TRADES_FILE="$EXPORT_DIR/trades_$TIMESTAMP.csv"

sqlite3 -header -csv "$DB_PATH" "
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
WHERE l.trader_id = '$TRADER_ID'
ORDER BY t.time DESC;
" > "$TRADES_FILE"

TRADES_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trader_trade_details t JOIN trader_decision_actions a ON t.decision_action_id = a.id JOIN trader_decision_logs l ON a.decision_log_id = l.id WHERE l.trader_id = '$TRADER_ID';")
echo -e "      ${GREEN}Exported $TRADES_COUNT trade details -> $TRADES_FILE${NC}"

# 4. Export full decision logs (JSON)
echo -e "${YELLOW}[4/6] Exporting full logs (JSON)...${NC}"
FULL_LOGS_FILE="$EXPORT_DIR/full_logs_$TIMESTAMP.json"

sqlite3 -json "$DB_PATH" "
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
WHERE trader_id = '$TRADER_ID'
ORDER BY timestamp DESC
LIMIT 100;
" > "$FULL_LOGS_FILE"

echo -e "      ${GREEN}Exported last 100 full logs -> $FULL_LOGS_FILE${NC}"

# 5. Generate PnL summary
echo -e "${YELLOW}[5/6] Generating PnL summary...${NC}"
SUMMARY_FILE="$EXPORT_DIR/pnl_summary_$TIMESTAMP.txt"

cat > "$SUMMARY_FILE" << EOF
================================================================================
TRADER PnL SUMMARY REPORT
================================================================================
Trader ID: $TRADER_ID
Export Time: $(date "+%Y-%m-%d %H:%M:%S")
================================================================================

[ORDER STATISTICS]
EOF

sqlite3 "$DB_PATH" "
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
WHERE l.trader_id = '$TRADER_ID';
" >> "$SUMMARY_FILE"

cat >> "$SUMMARY_FILE" << EOF

[PnL STATISTICS]
EOF

sqlite3 "$DB_PATH" "
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
WHERE l.trader_id = '$TRADER_ID' AND a.closed = 1;
" >> "$SUMMARY_FILE"

cat >> "$SUMMARY_FILE" << EOF

[PnL BY SYMBOL]
EOF

sqlite3 "$DB_PATH" "
SELECT 
    symbol || ': ' || 
    ROUND(COALESCE(SUM(pnl), 0), 4) || ' USDT (' || 
    COUNT(*) || ' trades, WinRate ' || 
    ROUND(100.0 * SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) || '%)'
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TRADER_ID' AND a.closed = 1
GROUP BY symbol
ORDER BY SUM(pnl) DESC;
" >> "$SUMMARY_FILE"

cat >> "$SUMMARY_FILE" << EOF

[TOTAL FEES]
EOF

sqlite3 "$DB_PATH" "
SELECT 
    'Total Fees (USDT): ' || ROUND(COALESCE(SUM(fee), 0), 4)
FROM trader_decision_actions a
JOIN trader_decision_logs l ON a.decision_log_id = l.id
WHERE l.trader_id = '$TRADER_ID';
" >> "$SUMMARY_FILE"

echo -e "      ${GREEN}Generated PnL summary -> $SUMMARY_FILE${NC}"

# 6. Check and export from decision_logs folder
FILE_LOGS_DIR="decision_logs/$TRADER_ID"
echo -e "${YELLOW}[6/6] Exporting from file logs...${NC}"

if [ -d "$FILE_LOGS_DIR" ]; then
    FILE_LOGS_COUNT=$(find "$FILE_LOGS_DIR" -name "*.json" 2>/dev/null | wc -l)
    
    if [ "$FILE_LOGS_COUNT" -gt 0 ]; then
        FILE_LOGS_EXPORT_DIR="$EXPORT_DIR/file_logs"
        mkdir -p "$FILE_LOGS_EXPORT_DIR"
        cp "$FILE_LOGS_DIR"/*.json "$FILE_LOGS_EXPORT_DIR/" 2>/dev/null || true
        echo -e "      ${GREEN}Copied $FILE_LOGS_COUNT file logs -> $FILE_LOGS_EXPORT_DIR${NC}"
    else
        echo -e "      ${YELLOW}No file logs found${NC}"
    fi
else
    echo -e "      ${YELLOW}No file logs directory found for this trader${NC}"
fi

# Done
echo ""
echo "============================================================"
echo -e "${GREEN}Export Complete!${NC}"
echo -e "${CYAN}Output directory: $EXPORT_DIR${NC}"
echo ""
echo "Exported files:"
for f in "$EXPORT_DIR"/*"$TIMESTAMP"*; do
    if [ -f "$f" ]; then
        SIZE=$(du -h "$f" | cut -f1)
        echo "   - $(basename "$f") ($SIZE)"
    fi
done

# Show file logs if any
if [ -d "$EXPORT_DIR/file_logs" ]; then
    FILE_LOGS_COUNT=$(find "$EXPORT_DIR/file_logs" -name "*.json" | wc -l)
    echo "   - file_logs/ ($FILE_LOGS_COUNT JSON files)"
fi

