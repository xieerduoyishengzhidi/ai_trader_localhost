package decision

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// RAGResult RAG检索结果
type RAGResult struct {
	TraderName  string   `json:"trader_name"`
	Viewpoints  []string `json:"viewpoints"`
	ErrorReason string   `json:"error_reason,omitempty"`
}

// SupabaseRAGClient Supabase RAG客户端
type SupabaseRAGClient struct {
	baseURL    string
	apiKey     string
	tableName  string
	httpClient *http.Client
}

// CleanDataRow clean_data表的行结构（参考3_retrieve_clean_data_embeddings.py）
type CleanDataRow struct {
	ID                         interface{} `json:"id"`
	MessageID                  interface{} `json:"message_id"`
	RowID                      interface{} `json:"row_id"`
	Text                       string      `json:"text"`
	OriginalPayload            interface{} `json:"original_payload"`
	GPTAssets                  interface{} `json:"gpt_assets"`
	IsMarketRelatedReason      interface{} `json:"is_market_related_reason"`
	IsMarketRelatedResultJSON  interface{} `json:"is_market_related_result_json"`
	InfoOverallAssessment      string      `json:"info_overall_assessment"`
	InfoFinalScoreJSON         interface{} `json:"info_final_score_json"`
	InfoFinalScore             interface{} `json:"info_final_score"`
	InfoScores                 interface{} `json:"info_scores"`
	EmbeddingContext           interface{} `json:"embedding_context"`
}

// NewSupabaseRAGClient 创建Supabase RAG客户端
func NewSupabaseRAGClient() (*SupabaseRAGClient, error) {
	supabaseURL := os.Getenv("SUPABASE_URL")
	supabaseKey := os.Getenv("SUPABASE_SERVICE_KEY")
	tableName := os.Getenv("CLEAN_DATA_TABLE_NAME")

	if tableName == "" {
		tableName = "clean_data" // 默认表名
	}

	if supabaseURL == "" || supabaseKey == "" {
		return nil, fmt.Errorf("SUPABASE_URL 或 SUPABASE_SERVICE_KEY 未设置")
	}

	return &SupabaseRAGClient{
		baseURL:   supabaseURL,
		apiKey:    supabaseKey,
		tableName: tableName,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}, nil
}

// RetrieveTraderViewpoints 根据交易员名称检索历史观点
func (c *SupabaseRAGClient) RetrieveTraderViewpoints(traderName string, limit int) (*RAGResult, error) {
	if traderName == "" {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: "交易员名称为空",
		}, nil
	}

	// 标准化交易员名称（去除空格）
	normalizedName := strings.TrimSpace(traderName)

	// 构建Supabase REST API URL
	// 使用PostgREST的查询语法：or参数用于多字段搜索
	apiURL := fmt.Sprintf("%s/rest/v1/%s", c.baseURL, c.tableName)
	
	// 构建查询参数
	params := url.Values{}
	params.Add("select", "id,message_id,text,original_payload,gpt_assets,is_market_related_reason,info_overall_assessment,info_final_score_json,info_final_score")
	// 使用or查询在多个字段中搜索交易员名称（ilike是不区分大小写的LIKE）
	params.Add("or", fmt.Sprintf("(text.ilike.%%%s%%,info_overall_assessment.ilike.%%%s%%)", normalizedName, normalizedName))
	params.Add("order", "id.desc")
	params.Add("limit", fmt.Sprintf("%d", limit))

	fullURL := fmt.Sprintf("%s?%s", apiURL, params.Encode())

	// 创建HTTP请求
	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("创建请求失败: %v", err),
		}, nil
	}

	// 设置Supabase认证头
	req.Header.Set("apikey", c.apiKey)
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	req.Header.Set("Content-Type", "application/json")

	// 执行请求
	resp, err := c.httpClient.Do(req)
	if err != nil {
		log.Printf("⚠️  RAG检索失败: %v", err)
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("HTTP请求失败: %v", err),
		}, nil
	}
	defer resp.Body.Close()

	// 读取响应
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("读取响应失败: %v", err),
		}, nil
	}

	// 检查HTTP状态码
	if resp.StatusCode != http.StatusOK {
		log.Printf("⚠️  Supabase返回错误状态码: %d, 响应: %s", resp.StatusCode, string(body))
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("Supabase返回错误: %d", resp.StatusCode),
		}, nil
	}

	// 解析JSON响应
	var rows []CleanDataRow
	if err := json.Unmarshal(body, &rows); err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("JSON解析失败: %v", err),
		}, nil
	}

	// 提取观点
	viewpoints := make([]string, 0)
	for _, row := range rows {
		viewpoint := extractViewpoint(&row)
		if viewpoint != "" {
			viewpoints = append(viewpoints, viewpoint)
		}
	}

	log.Printf("✅ RAG检索成功: 交易员'%s'找到%d条历史观点", traderName, len(viewpoints))

	return &RAGResult{
		TraderName: traderName,
		Viewpoints: viewpoints,
	}, nil
}

// extractViewpoint 从CleanDataRow中提取观点（参考3_retrieve_clean_data_embeddings.py的summarize_row函数）
func extractViewpoint(row *CleanDataRow) string {
	var parts []string

	// 提取原始文本
	if row.Text != "" {
		parts = append(parts, fmt.Sprintf("原始内容: %s", row.Text))
	}

	// 提取资产分析
	if row.GPTAssets != nil {
		assetsStr := coerceToText(row.GPTAssets)
		if assetsStr != "" {
			parts = append(parts, fmt.Sprintf("资产分析: %s", assetsStr))
		}
	}

	// 提取市场相关原因
	if row.IsMarketRelatedReason != nil {
		reasonStr := coerceToText(row.IsMarketRelatedReason)
		if reasonStr != "" {
			parts = append(parts, fmt.Sprintf("市场相关性: %s", reasonStr))
		}
	}

	// 提取信息评估
	if row.InfoOverallAssessment != "" {
		parts = append(parts, fmt.Sprintf("综合评估: %s", row.InfoOverallAssessment))
	} else if row.InfoFinalScoreJSON != nil {
		assessmentStr := coerceToText(row.InfoFinalScoreJSON)
		if assessmentStr != "" {
			parts = append(parts, fmt.Sprintf("评分分析: %s", assessmentStr))
		}
	}

	if len(parts) == 0 {
		return ""
	}

	// 合并成一条观点
	viewpoint := strings.Join(parts, " | ")

	// 限制长度（参考EMBEDDING_CONTEXT_LIMIT=6000）
	maxLength := 500 // 每条观点最多500字符
	if len(viewpoint) > maxLength {
		viewpoint = viewpoint[:maxLength-3] + "..."
	}

	return viewpoint
}

// coerceToText 将任意类型转换为文本（参考3_retrieve_clean_data_embeddings.py的_coerce_to_text函数）
func coerceToText(value interface{}) string {
	if value == nil {
		return ""
	}

	switch v := value.(type) {
	case string:
		return strings.TrimSpace(v)
	case int, int64, float64, bool:
		return fmt.Sprintf("%v", v)
	case map[string]interface{}:
		// 提取常见的文本字段
		for _, key := range []string{"text", "reason", "overall_assessment", "content", "summary"} {
			if fieldValue, ok := v[key]; ok {
				if str, ok := fieldValue.(string); ok && strings.TrimSpace(str) != "" {
					return strings.TrimSpace(str)
				}
			}
		}
		// 如果没有找到文本字段，序列化整个对象
		if jsonBytes, err := json.Marshal(v); err == nil {
			return string(jsonBytes)
		}
	case []interface{}:
		var items []string
		for _, item := range v {
			itemStr := coerceToText(item)
			if itemStr != "" {
				items = append(items, itemStr)
			}
		}
		return strings.Join(items, ", ")
	}

	// 默认：序列化为JSON
	if jsonBytes, err := json.Marshal(value); err == nil {
		return string(jsonBytes)
	}

	return ""
}

// ExtractTraderNameFromPrompt 从prompt名称中提取交易员名字（第一个名字）
func ExtractTraderNameFromPrompt(promptName string) string {
	if promptName == "" {
		return ""
	}

	// 按下划线分割
	parts := strings.Split(promptName, "_")
	if len(parts) > 0 {
		// 返回第一个部分
		return strings.TrimSpace(parts[0])
	}

	return promptName
}

// FormatRAGContext 格式化RAG上下文用于插入prompt
func FormatRAGContext(result *RAGResult) string {
	if result == nil || len(result.Viewpoints) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("\n## 📚 历史观点参考\n\n")
	sb.WriteString(fmt.Sprintf("**这是历史上该交易员'%s'的观点，用该观点辅助你的现有判断**\n\n", result.TraderName))

	for i, viewpoint := range result.Viewpoints {
		if i >= 5 { // 最多显示5条观点
			break
		}
		sb.WriteString(fmt.Sprintf("%d. %s\n\n", i+1, viewpoint))
	}

	return sb.String()
}

