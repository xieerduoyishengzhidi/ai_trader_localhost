# SiliconFlow AI 模型使用指南

## 功能说明

NOFX 现已支持使用 SiliconFlow 平台的 AI 模型，包括：
- **Pro/deepseek-ai/DeepSeek-V3.2**（默认模型）
- 其他 SiliconFlow 平台上的可选模型

## 配置方式

### 1. 通过 Web 界面配置（推荐）

1. 登录 Web 管理界面
2. 进入「AI 模型配置」页面
3. 找到「SiliconFlow」模型
4. 填写以下信息：
   - **启用状态**：勾选以启用
   - **API Key**：您的 SiliconFlow API 密钥
   - **自定义 API URL**（可选）：默认为 `https://api.siliconflow.cn/v1`
   - **自定义模型名称**（可选）：默认为 `Pro/deepseek-ai/DeepSeek-V3.2`

### 2. 创建使用 SiliconFlow 的交易员

1. 进入「交易员管理」页面
2. 创建新交易员或编辑现有交易员
3. 在「AI 模型」下拉菜单中选择「SiliconFlow」
4. 配置其他交易参数（交易所、初始余额等）
5. 保存并启动交易员

## 支持的模型

SiliconFlow 平台支持多种模型，您可以通过「自定义模型名称」字段使用其他模型，例如：

- `Pro/deepseek-ai/DeepSeek-V3.2`（默认，高性能文本生成）
- `deepseek-ai/DeepSeek-V3`（DeepSeek V3）
- `Qwen/Qwen2.5-72B-Instruct`（Qwen2.5 72B）
- `Qwen/Qwen2.5-Coder-32B-Instruct`（代码生成专用）
- 其他 SiliconFlow 平台上的模型

## 配置示例

### 使用默认模型（DeepSeek-V3.2）

```json
{
  "provider": "siliconflow",
  "api_key": "your-siliconflow-api-key",
  "custom_api_url": "",
  "custom_model_name": ""
}
```

### 使用自定义模型

```json
{
  "provider": "siliconflow",
  "api_key": "your-siliconflow-api-key",
  "custom_api_url": "https://api.siliconflow.cn/v1",
  "custom_model_name": "Qwen/Qwen2.5-72B-Instruct"
}
```

## 获取 API 密钥

1. 访问 [SiliconFlow 官网](https://siliconflow.cn/)
2. 注册并完成企业认证
3. 在控制台创建 API 应用
4. 获取 API 密钥并妥善保存

## 注意事项

1. **API 格式**：SiliconFlow 使用 OpenAI 兼容的 API 格式
2. **认证方式**：使用 Bearer Token 认证（`Authorization: Bearer <API_KEY>`）
3. **模型名称格式**：模型名称格式为 `Provider/Model-Name`，例如 `Pro/deepseek-ai/DeepSeek-V3.2`
4. **自定义 URL**：如果 SiliconFlow 的 API 地址发生变化，可以通过自定义 URL 字段更新

## 故障排查

如果遇到问题，请检查：

1. API 密钥是否正确
2. 服务器出站 IP 是否已加入 SiliconFlow 白名单
3. 模型名称是否正确（区分大小写）
4. API URL 是否正确（默认为 `https://api.siliconflow.cn/v1`）

## 相关链接

- [SiliconFlow 官网](https://siliconflow.cn/)
- [SiliconFlow API 文档](https://docs.siliconflow.cn/)

