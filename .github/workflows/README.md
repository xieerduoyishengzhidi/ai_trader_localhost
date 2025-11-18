# GitHub Actions 工作流配置说明

## 每日 Telegram 群组摘要工作流

此工作流每天自动运行 `fetch_tg_ai.py` 脚本，抓取 Telegram 群组消息并生成 AI 摘要。

### 配置步骤

#### 1. 设置 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加以下 secrets：

**必需配置：**
- `TELEGRAM_API_ID`: Telegram API ID（从 https://my.telegram.org/apps 获取）
- `TELEGRAM_API_HASH`: Telegram API Hash
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥
- `TELEGRAM_SESSION`: Telegram session 文件的 base64 编码内容
  - 在本地运行一次脚本生成 session 文件后，使用以下命令编码：
    ```bash
    base64 telegram插件/telegram_session.session
    ```
  - 将输出的 base64 字符串保存为 secret
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token（用于发送通知）
  - 向 [@BotFather](https://t.me/botfather) 创建 bot 并获取 token
- `TELEGRAM_CHAT_ID`: 接收通知的 Telegram Chat ID（你的用户 ID 或群组 ID）
  - 向 [@userinfobot](https://t.me/userinfobot) 发送消息获取你的 Chat ID

**可选配置：**
- `TELEGRAM_CHAT`: 要抓取的群组名称（默认：`nofx_dev_community`）
- `TELEGRAM_LIMIT`: 抓取消息数量限制（默认：`2000`）

#### 2. 调整运行时间

默认设置为每天 UTC 23:00（中国时间早上 7:00）。如需修改，编辑 `.github/workflows/daily-telegram-summary.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 23 * * *'  # 分钟 小时 日 月 星期
```

**时区说明：**
- GitHub Actions 使用 UTC 时间
- 中国时间（UTC+8）早上 7:00 = UTC 23:00（前一天）
- 例如：要在中国时间早上 7:00 运行，使用 `'0 23 * * *'`

#### 3. 手动触发

工作流支持手动触发，在 GitHub Actions 页面点击 "Run workflow" 即可。

### 输出文件

工作流运行后会：
1. 生成摘要文件并上传为 Artifact
2. 发送 Telegram 通知（包含摘要预览）

### 故障排查

- **Session 文件问题**：确保 `TELEGRAM_SESSION` secret 包含完整的 base64 编码 session 文件
- **权限问题**：确保 Telegram 账号有权限访问目标群组
- **API 限制**：如果遇到 FloodWait 错误，工作流会自动重试
