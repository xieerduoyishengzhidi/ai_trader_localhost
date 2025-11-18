# Telegram 单群近一日消息爬取与 AI 汇总——需求说明（v2.0）

> 目标：使用 **Telethon** 从 **一个指定 Telegram 群组** 中抓取 **过去 24 小时** 的消息，并通过 **DeepSeek API** 自动生成一份“有用信息汇总”。
> 本工具为 **本地运行脚本**，不包含复杂的配置或多进程逻辑。

---

## 1. 功能范围（Scope）
- **核心功能**：
  1. 从指定群抓取过去 24 小时内的消息（带时间、用户、文本）。
  2. 限制抓取条数（`--limit`）。
  3. 将结果保存为 JSONL 文件。
  4. 调用 DeepSeek API，对抓取内容进行总结（“提取有用信息”）。
  5. 支持自定义总结 prompt。

- **不包含**：
  - 媒体下载、图像分析。
  - 多群批量任务。
  - 数据库或前端展示。
  - 云端或服务器部署。

---

## 2. 环境配置
所有配置直接写入代码顶部常量，无需 .env 文件：
```python
API_ID = 123456
API_HASH = 'your_telegram_api_hash'
DEEPSEEK_API_KEY = 'your_deepseek_api_key'
DEEPSEEK_MODEL = 'deepseek-chat'  # 或 deepseek-coder / deepseek-r1 等
```

---

## 3. 命令行参数
```bash
python fetch_tg_ai.py --chat @group_name [--limit 500] [--prompt "请帮我提取今日要闻"]
```

参数说明：
- `--chat`（必填）：目标群组用户名或 ID。
- `--limit`（可选）：最大抓取条数，默认 500。
- `--prompt`（可选）：自定义 AI 总结提示语，默认内置模板。

---

## 4. 输出结果
执行后生成：
1. **群消息原始数据**：`output/telegram_raw_YYYYMMDD.jsonl`
2. **AI 汇总结果**：`output/summary_YYYYMMDD.txt`

汇总文件格式：
```
=== Telegram 群组每日摘要 ===
群组: @group_name
时间: 2025-11-06 (过去24小时)

【AI 总结】
- 今日主要讨论了...
- 有人提到了...
- 链接/资源：...
```

---

## 5. 实现思路

### Step 1️⃣：抓取消息
使用 Telethon 从目标群中拉取过去 24 小时的消息：
```python
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient

since = datetime.now(timezone.utc) - timedelta(hours=24)
until = datetime.now(timezone.utc)
messages = await client.get_messages(chat, limit=limit)
filtered = [m for m in messages if since <= m.date <= until]
```

### Step 2️⃣：调用 DeepSeek 总结
将消息拼接成一个长文本后发送给 DeepSeek API：
```python
from openai import OpenAI
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

prompt_text = f"{user_prompt}\n以下是群聊内容：\n{all_messages}"

resp = client.chat.completions.create(
    model=DEEPSEEK_MODEL,
    messages=[{"role": "user", "content": prompt_text}]
)
summary = resp.choices[0].message.content
```

### Step 3️⃣：保存结果
- 写入 JSONL（原始消息）
- 写入 TXT（AI 汇总）

---

## 6. 文件结构
```
fetch_tg_ai.py
output/
  ├── telegram_raw_20251106.jsonl
  └── summary_20251106.txt
requirements.txt
```

---

## 7. 默认 AI Prompt
```text
你是一位信息提炼助手。请从以下 Telegram 群组聊天内容中提取对我有帮助的重要信息，避免无关闲聊。请按以下格式输出：
- 主要话题：
- 关键事件：
- 提及的资源或链接：
- 建议或行动项：
```

用户可通过命令行传入自定义 prompt。

---

## 8. 依赖与安装
```bash
pip install telethon openai
mkdir -p output
```

---

## 9. 错误处理
- 网络超时：自动重试 3 次。
- 群不存在或无权限：输出友好错误信息。
- DeepSeek API 错误：提示响应码与内容。

---

## 10. 示例运行
```bash
python fetch_tg_ai.py --chat @mygroup --limit 300 --prompt "请生成简短摘要"
```
输出：
```
✅ 抓取消息：276 条
✅ 生成摘要：summary_20251106.txt
```

---

## 11. 验收标准
- 抓取功能稳定，限定时间与条数生效。
- AI 汇总内容可读、准确、与 prompt 相符。
- 文件成功输出并带时间戳。

---

**作者**：JJS  
**版本**：v2.0（单群爬取 + DeepSeek 本地摘要版）

