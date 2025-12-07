package decision

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
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

// ChromaDBRAGClient ChromaDB RAG客户端
type ChromaDBRAGClient struct {
	apiURL     string
	httpClient *http.Client
}

// NewChromaDBRAGClient 创建ChromaDB RAG客户端
func NewChromaDBRAGClient() (*ChromaDBRAGClient, error) {
	apiURL := os.Getenv("CHROMADB_RAG_API_URL")
	if apiURL == "" {
		apiURL = "http://127.0.0.1:8765" // 默认地址
	}

	return &ChromaDBRAGClient{
		apiURL: apiURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}, nil
}

// RetrieveTraderViewpoints 根据交易员名称检索历史观点
func (c *ChromaDBRAGClient) RetrieveTraderViewpoints(traderName string, limit int) (*RAGResult, error) {
	if traderName == "" {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: "交易员名称为空",
		}, nil
	}

	// 标准化交易员名称（去除空格）
	normalizedName := strings.TrimSpace(traderName)

	// 构建请求体
	requestBody := map[string]interface{}{
		"trader_name": normalizedName,
		"limit":       limit,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("构建请求失败: %v", err),
		}, nil
	}

	// 创建HTTP请求
	apiURL := fmt.Sprintf("%s/query_by_name", c.apiURL)
	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("创建请求失败: %v", err),
		}, nil
	}

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
		log.Printf("⚠️  ChromaDB RAG API返回错误状态码: %d, 响应: %s", resp.StatusCode, string(body))
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("API返回错误: %d", resp.StatusCode),
		}, nil
	}

	// 解析JSON响应
	var result RAGResult
	if err := json.Unmarshal(body, &result); err != nil {
		return &RAGResult{
			TraderName:  traderName,
			Viewpoints:  []string{},
			ErrorReason: fmt.Sprintf("JSON解析失败: %v", err),
		}, nil
	}

	if result.ErrorReason != "" {
		log.Printf("⚠️  RAG检索返回错误: %s", result.ErrorReason)
	}

	if len(result.Viewpoints) > 0 {
		log.Printf("✅ RAG检索成功: 交易员'%s'找到%d条历史观点", traderName, len(result.Viewpoints))
	}

	return &result, nil
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
