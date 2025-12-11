package decision

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

// logicNewsItem 表示 logic_analysis.db 中的一条新闻逻辑记录
type logicNewsItem struct {
	ID          int64
	Title       string
	Summary     string
	Direction   string
	Timeframe   string
	Strength    int
	Trigger     string
	Impact      string
	Macro       string
	Commentary  string
	URL         string
	PublishTime string
}

// fetchLatestLogicNews 读取 logic_analysis.db 中最新的新闻逻辑，默认取最近20条
func fetchLatestLogicNews(limit int) ([]logicNewsItem, error) {
	if limit <= 0 {
		limit = 20
	}

	dbPath := os.Getenv("LOGIC_DB_PATH")
	if dbPath == "" {
		dbPath = filepath.Join("rag", "logic_analysis.db")
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("打开logic_analysis.db失败: %w", err)
	}
	defer db.Close()

	rows, err := db.Query(`
		SELECT id, news_title, news_summary, signal_direction, signal_timeframe, signal_strength,
		       trigger_event, expected_market_impact, macro_confluence, pentosh_commentary,
		       news_url, news_publish_time
		  FROM logic_analysis
		 ORDER BY id DESC
		 LIMIT ?`, limit)
	if err != nil {
		return nil, fmt.Errorf("查询logic_analysis失败: %w", err)
	}
	defer rows.Close()

	var result []logicNewsItem
	for rows.Next() {
		var item logicNewsItem
		var title, summary, direction, timeframe, trigger, impact, macro, commentary, url, publishTime sql.NullString
		var strength sql.NullInt64

		if err := rows.Scan(
			&item.ID,
			&title, &summary, &direction, &timeframe, &strength,
			&trigger, &impact, &macro, &commentary,
			&url, &publishTime,
		); err != nil {
			return nil, fmt.Errorf("解析logic_analysis行失败: %w", err)
		}

		item.Title = nullString(title)
		item.Summary = nullString(summary)
		item.Direction = nullString(direction)
		item.Timeframe = nullString(timeframe)
		item.Strength = int(strength.Int64)
		item.Trigger = nullString(trigger)
		item.Impact = nullString(impact)
		item.Macro = nullString(macro)
		item.Commentary = nullString(commentary)
		item.URL = nullString(url)
		item.PublishTime = nullString(publishTime)

		result = append(result, item)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("遍历logic_analysis失败: %w", err)
	}

	return result, nil
}

// formatLogicNewsForPrompt 将新闻逻辑格式化为 prompt 片段
func formatLogicNewsForPrompt(items []logicNewsItem) string {
	if len(items) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("## 📰 宏观RAG（logic_analysis，最近20条）\n\n")

	for i, item := range items {
		head := fmt.Sprintf("%d) %s | %s %s 强度%d", i+1, item.Title, item.Direction, item.Timeframe, item.Strength)
		sb.WriteString(head + "\n")

		if item.Trigger != "" {
			sb.WriteString(fmt.Sprintf("   触发: %s\n", item.Trigger))
		}
		if item.Impact != "" {
			sb.WriteString(fmt.Sprintf("   预期影响: %s\n", item.Impact))
		}
		if item.Macro != "" {
			sb.WriteString(fmt.Sprintf("   宏观: %s\n", item.Macro))
		}
		if item.Commentary != "" {
			sb.WriteString(fmt.Sprintf("   评论: %s\n", item.Commentary))
		}
		if item.Summary != "" {
			sb.WriteString(fmt.Sprintf("   摘要: %s\n", item.Summary))
		}
		if item.URL != "" {
			sb.WriteString(fmt.Sprintf("   链接: %s\n", item.URL))
		}
		if item.PublishTime != "" {
			sb.WriteString(fmt.Sprintf("   发布时间: %s\n", item.PublishTime))
		}
		sb.WriteString("\n")
	}

	return sb.String()
}

func nullString(ns sql.NullString) string {
	if ns.Valid {
		return strings.TrimSpace(ns.String)
	}
	return ""
}
