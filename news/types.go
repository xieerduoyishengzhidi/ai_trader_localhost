package news

import "time"

// NewsItem 新闻条目
type NewsItem struct {
	ID          int64      `json:"id"`
	Title       string     `json:"title"`
	URL         string     `json:"url"`
	Source      string     `json:"source"`
	PublishedAt time.Time  `json:"published_at"`
	CreatedAt   time.Time  `json:"created_at"`
	Votes       Votes      `json:"votes"`
	Currencies  []Currency `json:"currencies"`
}

// Votes 投票信息
type Votes struct {
	Positive  int `json:"positive"`
	Negative  int `json:"negative"`
	Important int `json:"important"`
	Liked     int `json:"liked"`
	Disliked  int `json:"disliked"`
	Lol       int `json:"lol"`
	Disgust   int `json:"disgust"`
	Sad       int `json:"sad"`
}

// Currency 货币信息
type Currency struct {
	Code  string `json:"code"`
	Title string `json:"title"`
	Slug  string `json:"slug"`
	URL   string `json:"url"`
}

// CryptoPanicResponse CryptoPanic API 响应结构
type CryptoPanicResponse struct {
	Results  []NewsItem `json:"results"`
	Count    int        `json:"count"`
	Next     string     `json:"next"`
	Previous string     `json:"previous"`
}

// CryptoPanicAPIResponse 原始 API 响应（用于解析）
type CryptoPanicAPIResponse struct {
	Results []struct {
		ID     int64  `json:"id"`
		Title  string `json:"title"`
		URL    string `json:"url"`
		Source struct {
			Title  string `json:"title"`
			Region string `json:"region"`
		} `json:"source"`
		PublishedAt string `json:"published_at"`
		CreatedAt   string `json:"created_at"`
		Votes       struct {
			Positive  int `json:"positive"`
			Negative  int `json:"negative"`
			Important int `json:"important"`
			Liked     int `json:"liked"`
			Disliked  int `json:"disliked"`
			Lol       int `json:"lol"`
			Disgust   int `json:"disgust"`
			Sad       int `json:"sad"`
		} `json:"votes"`
		Currencies []struct {
			Code  string `json:"code"`
			Title string `json:"title"`
			Slug  string `json:"slug"`
			URL   string `json:"url"`
		} `json:"currencies"`
	} `json:"results"`
	Count    int    `json:"count"`
	Next     string `json:"next"`
	Previous string `json:"previous"`
}




