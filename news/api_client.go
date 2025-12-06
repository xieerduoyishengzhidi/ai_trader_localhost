package news

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

const (
	baseURL = "https://cryptopanic.com/api/v1"
)

// APIClient CryptoPanic API 客户端
type APIClient struct {
	client  *http.Client
	apiKey  string
	baseURL string
}

// NewAPIClient 创建新的 API 客户端
func NewAPIClient(apiKey string) *APIClient {
	return &APIClient{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		apiKey:  apiKey,
		baseURL: baseURL,
	}
}

// GetBTCNews 获取 BTC 相关新闻
func (c *APIClient) GetBTCNews(limit int) (*CryptoPanicResponse, error) {
	return c.GetNews("BTC", limit)
}

// GetNews 获取指定货币的新闻
func (c *APIClient) GetNews(currency string, limit int) (*CryptoPanicResponse, error) {
	if limit <= 0 {
		limit = 20 // 默认20条
	}
	if limit > 100 {
		limit = 100 // 最大100条
	}

	url := fmt.Sprintf("%s/posts/?auth_token=%s&currencies=%s&limit=%d",
		c.baseURL, c.apiKey, currency, limit)

	log.Printf("🔄 正在请求 CryptoPanic API: %s", currency)

	resp, err := c.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("请求 CryptoPanic API 失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API 返回错误 (status %d): %s", resp.StatusCode, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %w", err)
	}

	// 解析原始 API 响应
	var apiResp CryptoPanicAPIResponse
	if err := json.Unmarshal(body, &apiResp); err != nil {
		return nil, fmt.Errorf("JSON 解析失败: %w", err)
	}

	// 转换为标准格式
	result := &CryptoPanicResponse{
		Count:    apiResp.Count,
		Next:     apiResp.Next,
		Previous: apiResp.Previous,
		Results:  make([]NewsItem, 0, len(apiResp.Results)),
	}

	for _, item := range apiResp.Results {
		// 解析时间
		publishedAt, _ := time.Parse(time.RFC3339, item.PublishedAt)
		createdAt, _ := time.Parse(time.RFC3339, item.CreatedAt)

		// 转换货币信息
		currencies := make([]Currency, 0, len(item.Currencies))
		for _, curr := range item.Currencies {
			currencies = append(currencies, Currency{
				Code:  curr.Code,
				Title: curr.Title,
				Slug:  curr.Slug,
				URL:   curr.URL,
			})
		}

		result.Results = append(result.Results, NewsItem{
			ID:          item.ID,
			Title:       item.Title,
			URL:         item.URL,
			Source:      item.Source.Title,
			PublishedAt: publishedAt,
			CreatedAt:   createdAt,
			Votes: Votes{
				Positive:  item.Votes.Positive,
				Negative:  item.Votes.Negative,
				Important: item.Votes.Important,
				Liked:     item.Votes.Liked,
				Disliked:  item.Votes.Disliked,
				Lol:       item.Votes.Lol,
				Disgust:   item.Votes.Disgust,
				Sad:       item.Votes.Sad,
			},
			Currencies: currencies,
		})
	}

	log.Printf("✓ 成功获取 %d 条 %s 新闻", len(result.Results), currency)
	return result, nil
}




