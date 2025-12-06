# Embedding 模型选择指南

本文档介绍如何选择合适的 Embedding 模型以及相关配置。

## 模型选择

### 推荐模型（按性能排序）

#### 1. moka-ai/m3e-base（默认推荐）⭐
- **维度**: 768
- **特点**: 专为中文优化，速度快，精度好
- **适用场景**: 中文文本处理，平衡性能和精度
- **内存需求**: 中等（约 300MB）
- **速度**: 快
- **精度**: 高

#### 2. moka-ai/m3e-large
- **维度**: 1024
- **特点**: 专为中文优化，精度更高
- **适用场景**: 需要更高精度的中文文本处理
- **内存需求**: 较高（约 600MB）
- **速度**: 中等
- **精度**: 很高

#### 3. sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **维度**: 384
- **特点**: 多语言支持，速度快
- **适用场景**: 多语言文本，对速度要求高
- **内存需求**: 低（约 100MB）
- **速度**: 很快
- **精度**: 中等

#### 4. sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- **维度**: 768
- **特点**: 多语言支持，精度高
- **适用场景**: 多语言文本，需要较高精度
- **内存需求**: 中等（约 400MB）
- **速度**: 中等
- **精度**: 高

#### 5. BAAI/bge-large-zh-v1.5
- **维度**: 1024
- **特点**: 中文优化，精度最高
- **适用场景**: 对精度要求极高的中文文本处理
- **内存需求**: 高（约 1GB）
- **速度**: 慢
- **精度**: 最高

#### 6. BAAI/bge-base-zh-v1.5
- **维度**: 768
- **特点**: 中文优化，平衡性能和精度
- **适用场景**: 中文文本，需要平衡性能和精度
- **内存需求**: 中等（约 400MB）
- **速度**: 中等
- **精度**: 高

## 如何选择模型

### 根据语言选择
- **纯中文文本**: 推荐 `moka-ai/m3e-base` 或 `BAAI/bge-base-zh-v1.5`
- **多语言文本**: 推荐 `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`

### 根据性能需求选择
- **速度优先**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **平衡性能**: `moka-ai/m3e-base`（默认）
- **精度优先**: `BAAI/bge-large-zh-v1.5` 或 `moka-ai/m3e-large`

### 根据硬件资源选择
- **内存受限（< 2GB）**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **内存充足（2-4GB）**: `moka-ai/m3e-base`
- **内存充足（> 4GB）**: `moka-ai/m3e-large` 或 `BAAI/bge-large-zh-v1.5`

## 配置参数说明

### EMBEDDING_MODEL
设置要使用的 Embedding 模型名称。

```bash
# 使用默认模型（moka-ai/m3e-base）
EMBEDDING_MODEL=moka-ai/m3e-base

# 使用高精度模型
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5

# 使用多语言模型
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

### EMBEDDING_BATCH_SIZE
批处理大小，控制一次处理多少条文本。

- **较小值（50-100）**: 内存占用低，但处理速度慢
- **中等值（200-300）**: 平衡内存和速度（推荐）
- **较大值（500+）**: 速度快，但需要更多内存

```bash
# 内存受限时使用较小值
EMBEDDING_BATCH_SIZE=100

# 默认值（推荐）
EMBEDDING_BATCH_SIZE=200

# 内存充足时使用较大值
EMBEDDING_BATCH_SIZE=500
```

### EMBEDDING_CONTEXT_LIMIT
上下文长度限制（字符数），超过此长度的文本会被截断。

- **较小值（3000-4000）**: 适合短文本，节省内存
- **中等值（6000-8000）**: 适合大多数场景（推荐）
- **较大值（10000+）**: 适合长文本，但需要更多内存

```bash
# 短文本场景
EMBEDDING_CONTEXT_LIMIT=4000

# 默认值（推荐）
EMBEDDING_CONTEXT_LIMIT=6000

# 长文本场景
EMBEDDING_CONTEXT_LIMIT=10000
```

### EMBEDDING_RATE_LIMIT_BACKOFF
速率限制退避时间（秒），当遇到速率限制时等待的时间。

```bash
# 默认值
EMBEDDING_RATE_LIMIT_BACKOFF=2.0

# 更保守的重试策略
EMBEDDING_RATE_LIMIT_BACKOFF=5.0
```

### EMBEDDING_DEVICE
指定运行设备（可选）。

- **cpu**: CPU 运行（最慢但兼容性最好）
- **cuda**: NVIDIA GPU 运行（最快，需要 CUDA）
- **mps**: Apple Silicon GPU 运行（macOS M1/M2）

如果不设置，系统会自动检测可用设备。

```bash
# 自动检测（推荐）
# EMBEDDING_DEVICE=

# 强制使用 CPU
EMBEDDING_DEVICE=cpu

# 使用 NVIDIA GPU
EMBEDDING_DEVICE=cuda

# 使用 Apple Silicon GPU
EMBEDDING_DEVICE=mps
```

## 使用示例

### 1. 复制环境变量示例文件
```bash
cp .env.example .env
```

### 2. 编辑 .env 文件
根据你的需求修改配置：

```bash
# 使用高精度中文模型
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5

# 使用 GPU 加速
EMBEDDING_DEVICE=cuda

# 增加批处理大小以提高速度
EMBEDDING_BATCH_SIZE=500
```

### 3. 加载环境变量
```bash
# Linux/macOS
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }
```

## 性能优化建议

1. **使用 GPU**: 如果有 NVIDIA GPU，设置 `EMBEDDING_DEVICE=cuda` 可以显著提升速度
2. **调整批处理大小**: 根据可用内存调整 `EMBEDDING_BATCH_SIZE`
3. **选择合适的模型**: 根据实际需求在速度和精度之间平衡
4. **限制上下文长度**: 如果文本通常较短，可以减小 `EMBEDDING_CONTEXT_LIMIT` 以节省内存

## 常见问题

### Q: 如何知道哪个模型最适合我的场景？
A: 建议先使用默认的 `moka-ai/m3e-base`，如果精度不够再尝试 `moka-ai/m3e-large` 或 `BAAI/bge-large-zh-v1.5`。

### Q: 模型下载很慢怎么办？
A: 可以配置 Hugging Face 镜像或使用代理。模型首次使用时会自动下载。

### Q: 内存不足怎么办？
A: 尝试使用较小的模型（如 `paraphrase-multilingual-MiniLM-L12-v2`）或减小 `EMBEDDING_BATCH_SIZE`。

### Q: 如何测试不同模型的效果？
A: 修改 `.env` 文件中的 `EMBEDDING_MODEL`，然后运行你的脚本，比较结果质量。












