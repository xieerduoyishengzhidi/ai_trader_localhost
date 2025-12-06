package main

import (
	"encoding/json"
	"fmt"
	"log"
	"nofx/news"
	"os"
	"strings"
)

func main() {
	// 从环境变量获取 API Key
	apiKey := os.Getenv("CRYPTOPANIC_API_KEY")
	if apiKey == "" {
		log.Fatal("❌ 请设置环境变量 CRYPTOPANIC_API_KEY")
	}

	fmt.Println("🚀 开始测试 CryptoPanic 新闻模块...")
	fmt.Println()

	// 创建 API 客户端
	client := news.NewAPIClient(apiKey)

	// 获取 BTC 新闻
	fmt.Println("📰 正在获取 BTC 相关新闻...")
	result, err := client.GetBTCNews(10)
	if err != nil {
		log.Fatalf("❌ 获取新闻失败: %v", err)
	}

	// 显示数据表结构
	fmt.Println()
	fmt.Println("=" + strings.Repeat("=", 100) + "=")
	fmt.Println("📊 数据表结构预览")
	fmt.Println("=" + strings.Repeat("=", 100) + "=")
	fmt.Println()

	// 显示统计信息
	fmt.Printf("总数量: %d\n", result.Count)
	fmt.Printf("返回数量: %d\n", len(result.Results))
	if result.Next != "" {
		fmt.Printf("下一页: %s\n", result.Next)
	}
	fmt.Println()

	// 显示表头
	fmt.Println("┌" + strings.Repeat("─", 10) + "┬" + strings.Repeat("─", 60) + "┬" + strings.Repeat("─", 30) + "┬" + strings.Repeat("─", 20) + "┐")
	fmt.Printf("│ %-8s │ %-58s │ %-28s │ %-18s │\n", "ID", "标题", "来源", "发布时间")
	fmt.Println("├" + strings.Repeat("─", 10) + "┼" + strings.Repeat("─", 60) + "┼" + strings.Repeat("─", 30) + "┼" + strings.Repeat("─", 20) + "┤")

	// 显示前5条数据
	maxShow := 5
	if len(result.Results) < maxShow {
		maxShow = len(result.Results)
	}

	for i := 0; i < maxShow; i++ {
		item := result.Results[i]
		title := item.Title
		if len(title) > 55 {
			title = title[:52] + "..."
		}
		source := item.Source
		if len(source) > 25 {
			source = source[:22] + "..."
		}
		publishedAt := item.PublishedAt.Format("2006-01-02 15:04")
		fmt.Printf("│ %-8d │ %-58s │ %-28s │ %-18s │\n", item.ID, title, source, publishedAt)
	}

	fmt.Println("└" + strings.Repeat("─", 10) + "┴" + strings.Repeat("─", 60) + "┴" + strings.Repeat("─", 30) + "┴" + strings.Repeat("─", 20) + "┘")
	fmt.Println()

	// 显示完整 JSON 结构（第一条新闻）
	if len(result.Results) > 0 {
		fmt.Println("=" + strings.Repeat("=", 100) + "=")
		fmt.Println("📋 完整数据结构示例（第一条新闻）")
		fmt.Println("=" + strings.Repeat("=", 100) + "=")
		fmt.Println()

		firstItem := result.Results[0]
		jsonData, err := json.MarshalIndent(firstItem, "", "  ")
		if err != nil {
			log.Printf("❌ JSON 序列化失败: %v", err)
		} else {
			fmt.Println(string(jsonData))
		}
		fmt.Println()

		// 显示投票信息
		fmt.Println("=" + strings.Repeat("=", 100) + "=")
		fmt.Println("👍 投票信息")
		fmt.Println("=" + strings.Repeat("=", 100) + "=")
		fmt.Printf("正面: %d | 负面: %d | 重要: %d | 喜欢: %d | 不喜欢: %d | 有趣: %d | 厌恶: %d | 悲伤: %d\n",
			firstItem.Votes.Positive,
			firstItem.Votes.Negative,
			firstItem.Votes.Important,
			firstItem.Votes.Liked,
			firstItem.Votes.Disliked,
			firstItem.Votes.Lol,
			firstItem.Votes.Disgust,
			firstItem.Votes.Sad,
		)
		fmt.Println()

		// 显示货币信息
		if len(firstItem.Currencies) > 0 {
			fmt.Println("=" + strings.Repeat("=", 100) + "=")
			fmt.Println("💰 相关货币")
			fmt.Println("=" + strings.Repeat("=", 100) + "=")
			for _, curr := range firstItem.Currencies {
				fmt.Printf("  • %s (%s) - %s\n", curr.Code, curr.Title, curr.URL)
			}
			fmt.Println()
		}
	}

	fmt.Println("✅ 测试完成！")
}





