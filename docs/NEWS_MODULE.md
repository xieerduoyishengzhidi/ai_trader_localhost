# 新闻模块使用指南

## 概述

新闻模块集成了 CryptoPanic API，用于获取加密货币相关新闻。当前 MVP 版本支持获取 BTC 相关新闻。

## 配置

### 1. 获取 CryptoPanic API Key

1. 访问 [CryptoPanic](https://cryptopanic.com/) 并注册账户
2. 登录后进入开发者选项获取 API Key

### 2. 设置 API Key

有三种方式设置 API Key，按优先级排序（优先级高的会覆盖优先级低的）：

**方式一：环境变量（最高优先级）**
```powershell
$env:CRYPTOPANIC_API_KEY="your_api_key_here"
```

**方式二：config.json 配置文件（推荐）**
在项目根目录的 `config.json` 文件中添加：
```json
{
  "cryptopanic_api_key": "your_api_key_here"
}
```
配置会在启动时自动同步到数据库。

**方式三：数据库系统配置**
通过 API 或数据库直接设置系统配置项 `cryptopanic_api_key`

> **注意**：如果同时设置了环境变量和 config.json，环境变量会优先使用。

## API 端点

### 获取 BTC 新闻

```
GET /api/news/btc?limit=20
```

**参数：**
- `limit` (可选): 返回的新闻数量，默认 20，最大 100

**示例：**
```powershell
# 获取 10 条 BTC 新闻
Invoke-WebRequest -Uri "http://localhost:8080/api/news/btc?limit=10" | Select-Object -ExpandProperty Content
```

### 获取指定货币新闻

```
GET /api/news/:currency?limit=20
```

**参数：**
- `currency`: 货币代码（如 BTC, ETH, SOL）
- `limit` (可选): 返回的新闻数量，默认 20，最大 100

**示例：**
```powershell
# 获取 ETH 新闻
Invoke-WebRequest -Uri "http://localhost:8080/api/news/ETH?limit=10" | Select-Object -ExpandProperty Content
```

## 数据结构

### 响应格式

```json
{
  "count": 100,
  "next": "https://cryptopanic.com/api/v1/posts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 123456,
      "title": "新闻标题",
      "url": "https://example.com/news",
      "source": "新闻来源",
      "published_at": "2025-01-20T10:30:00Z",
      "created_at": "2025-01-20T10:35:00Z",
      "votes": {
        "positive": 10,
        "negative": 2,
        "important": 5,
        "liked": 8,
        "disliked": 1,
        "lol": 3,
        "disgust": 0,
        "sad": 1
      },
      "currencies": [
        {
          "code": "BTC",
          "title": "Bitcoin",
          "slug": "bitcoin",
          "url": "https://cryptopanic.com/news/bitcoin/"
        }
      ]
    }
  ]
}
```

### 字段说明

- `id`: 新闻 ID
- `title`: 新闻标题
- `url`: 新闻链接
- `source`: 新闻来源
- `published_at`: 发布时间（ISO 8601 格式）
- `created_at`: 创建时间（ISO 8601 格式）
- `votes`: 投票信息
  - `positive`: 正面投票数
  - `negative`: 负面投票数
  - `important`: 重要标记数
  - `liked`: 喜欢数
  - `disliked`: 不喜欢数
  - `lol`: 有趣数
  - `disgust`: 厌恶数
  - `sad`: 悲伤数
- `currencies`: 相关货币列表

## 测试脚本

使用测试脚本查看数据表结构：

```powershell
# 设置 API Key
$env:CRYPTOPANIC_API_KEY="your_api_key_here"

# 运行测试脚本
cd tools
go run test_news.go
```

测试脚本会显示：
- 数据表结构预览（表格格式）
- 完整 JSON 数据结构示例
- 投票信息
- 相关货币信息

## 代码示例

### Go 代码示例

```go
package main

import (
    "fmt"
    "nofx/news"
)

func main() {
    // 创建 API 客户端
    client := news.NewAPIClient("your_api_key")
    
    // 获取 BTC 新闻
    result, err := client.GetBTCNews(10)
    if err != nil {
        fmt.Printf("错误: %v\n", err)
        return
    }
    
    // 打印新闻
    for _, item := range result.Results {
        fmt.Printf("标题: %s\n", item.Title)
        fmt.Printf("来源: %s\n", item.Source)
        fmt.Printf("链接: %s\n", item.URL)
        fmt.Printf("发布时间: %s\n", item.PublishedAt.Format("2006-01-02 15:04:05"))
        fmt.Println("---")
    }
}
```

## 注意事项

1. API Key 需要妥善保管，不要提交到代码仓库
2. CryptoPanic API 可能有请求频率限制，请合理使用
3. 新闻数据实时更新，建议缓存结果以提高性能

