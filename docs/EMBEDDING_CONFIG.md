# Embedding 配置说明

本文档说明如何配置 Embedding 相关参数。

## 快速开始

### 1. 创建环境变量文件

复制示例文件并重命名为 `.env`：

```bash
# Linux/macOS
cp env.example .env

# Windows PowerShell
Copy-Item env.example .env
```

### 2. 编辑环境变量

编辑 `.env` 文件，设置你的配置：

```bash
# 使用你喜欢的编辑器
nano .env
# 或
notepad .env
```

### 3. 加载环境变量

在运行 Python 脚本之前，加载环境变量：

#### Linux/macOS:
```bash
export $(cat .env | grep -v '^#' | xargs)
python 3_retrieve_clean_data_embeddings.py
```

#### Windows PowerShell:
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
python 3_retrieve_clean_data_embeddings.py
```

#### 使用 python-dotenv（推荐）:
安装 `python-dotenv`:
```bash
pip install python-dotenv
```

然后在 Python 代码中加载：
```python
from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件
```

## 配置参数说明

### EMBEDDING_MODEL

Embedding 模型名称。详细模型选择指南请参考 [EMBEDDING_MODEL_GUIDE.md](./EMBEDDING_MODEL_GUIDE.md)。

**默认值**: `moka-ai/m3e-base`

**示例**:
```bash
EMBEDDING_MODEL=moka-ai/m3e-base
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

### EMBEDDING_BATCH_SIZE

批处理大小，控制一次处理多少条文本。

**默认值**: `200`

**建议值**:
- 内存受限: `100`
- 默认: `200`
- 内存充足: `500`

**示例**:
```bash
EMBEDDING_BATCH_SIZE=200
```

### EMBEDDING_RATE_LIMIT_BACKOFF

速率限制退避时间（秒）。当遇到速率限制时，等待多长时间后重试。

**默认值**: `2.0`

**示例**:
```bash
EMBEDDING_RATE_LIMIT_BACKOFF=2.0
```

### EMBEDDING_CONTEXT_LIMIT

上下文长度限制（字符数）。超过此长度的文本会被截断。

**默认值**: `6000`

**建议值**:
- 短文本: `4000`
- 默认: `6000`
- 长文本: `10000`

**示例**:
```bash
EMBEDDING_CONTEXT_LIMIT=6000
```

### EMBEDDING_COLUMN

数据库中的 embedding 列名。

**默认值**: `embedding_context`

**示例**:
```bash
EMBEDDING_COLUMN=embedding_context
```

### EMBEDDING_DEVICE（可选）

指定运行设备。如果不设置，系统会自动检测可用设备。

**可选值**:
- `cpu`: CPU 运行
- `cuda`: NVIDIA GPU 运行（需要 CUDA）
- `mps`: Apple Silicon GPU 运行（macOS M1/M2）

**示例**:
```bash
# 自动检测（推荐）
# EMBEDDING_DEVICE=

# 使用 GPU
EMBEDDING_DEVICE=cuda
```

## Supabase 配置

### SUPABASE_URL

Supabase 项目 URL。

**格式**: `https://your-project-id.supabase.co`

**获取方式**: Supabase 项目设置 -> API -> Project URL

**示例**:
```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
```

### SUPABASE_SERVICE_KEY

Supabase 服务密钥（Service Role Key）。

⚠️ **注意**: 这是敏感信息，不要提交到版本控制！

**获取方式**: Supabase 项目设置 -> API -> service_role key

**示例**:
```bash
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 数据库配置

### CLEAN_DATA_TABLE_NAME

清理数据表名。

**默认值**: `clean_data`

**示例**:
```bash
CLEAN_DATA_TABLE_NAME=clean_data
```

## 完整配置示例

```bash
# Embedding 配置
EMBEDDING_MODEL=moka-ai/m3e-base
EMBEDDING_BATCH_SIZE=200
EMBEDDING_RATE_LIMIT_BACKOFF=2.0
EMBEDDING_CONTEXT_LIMIT=6000
EMBEDDING_COLUMN=embedding_context
EMBEDDING_DEVICE=cuda

# Supabase 配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# 数据库配置
CLEAN_DATA_TABLE_NAME=clean_data
```

## 验证配置

运行以下命令验证配置是否正确：

```bash
python -c "from config import *; print(f'Model: {EMBEDDING_MODEL}'); print(f'Batch Size: {EMBEDDING_BATCH_SIZE}'); print(f'Context Limit: {EMBEDDING_CONTEXT_LIMIT}')"
```

## 常见问题

### Q: 环境变量没有生效？
A: 确保在运行脚本之前已经加载了环境变量，或者使用 `python-dotenv` 自动加载。

### Q: 如何在不同环境使用不同配置？
A: 创建多个环境变量文件，如 `.env.dev`、`.env.prod`，然后在使用时指定：
```bash
export $(cat .env.prod | grep -v '^#' | xargs)
```

### Q: 配置文件的优先级是什么？
A: 环境变量 > 代码中的默认值。如果设置了环境变量，将优先使用环境变量的值。

## 相关文档

- [Embedding 模型选择指南](./EMBEDDING_MODEL_GUIDE.md) - 详细的模型选择说明
- [config.py](../config.py) - 配置模块源代码



