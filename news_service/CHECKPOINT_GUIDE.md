# 检查点（Checkpoint）功能使用指南

## 功能说明

历史新闻挖掘脚本现在支持**中断恢复**功能，可以：
- ✅ 中断后从上次停止的地方继续
- ✅ 每5条自动保存一次，避免数据丢失
- ✅ 自动跳过已处理的URL，避免重复爬取

## 使用方法

### 1. 正常启动

```bash
python history_miner.py --mode full --months 12
```

脚本会自动创建检查点文件：`history_news_cointelegraph_YYYYMMDD.csv`

### 2. 中断后恢复

如果脚本被中断（Ctrl+C 或程序崩溃），只需**重新运行相同的命令**：

```bash
python history_miner.py --mode full --months 12
```

脚本会：
1. 自动检测检查点文件
2. 读取已处理的URL列表
3. 跳过已处理的URL
4. 从上次中断的地方继续

### 3. 检查点文件

- **文件名格式**: `history_news_cointelegraph_YYYYMMDD.csv`
- **保存频率**: 每5条自动保存一次
- **文件位置**: 与脚本同目录

### 4. 手动指定检查点文件

如果需要使用自定义的检查点文件：

```python
from news_service.history_miner import HistoryNewsMiner

miner = HistoryNewsMiner()
df = miner.mine_history(
    site_name="CoinTelegraph",
    months_back=12,
    checkpoint_file="my_custom_checkpoint.csv"
)
```

## 工作流程

```
1. 启动脚本
   ↓
2. 检查是否存在检查点文件
   ├─ 存在 → 加载已处理的URL列表
   └─ 不存在 → 从头开始
   ↓
3. 收集所有待处理的URL
   ↓
4. 过滤掉已处理的URL
   ↓
5. 开始爬取剩余URL
   ├─ 每5条 → 自动保存检查点
   ├─ 每10条 → 休息2秒
   └─ 每5条 → 休息1秒
   ↓
6. 完成所有URL后，最终保存
```

## 注意事项

1. **不要手动删除检查点文件**，除非你想从头开始
2. **检查点文件就是最终的CSV文件**，包含所有已爬取的数据
3. **中断时按 Ctrl+C**，脚本会自动保存当前进度
4. **如果检查点文件损坏**，可以删除后重新开始

## 示例输出

```
🔍 开始挖掘 CoinTelegraph 的历史数据（过去 12 个月）
💾 检查点文件: history_news_cointelegraph_20251206.csv
   📂 发现检查点文件: 150 条已处理
   ✅ 从检查点恢复: 已处理 150 条，将继续处理剩余URL

📊 共找到 500 条相关新闻链接
📊 已处理 150 条，剩余 350 条待处理

   [151/500] 爬取: https://cointelegraph.com/news/...
      ✅ 成功提取: ...
      💾 已保存检查点（共 155 条）
```

## 故障排除

### 问题：检查点文件无法读取

**解决方案**: 检查文件编码，确保是 UTF-8 格式

### 问题：重复处理某些URL

**解决方案**: 检查URL是否完全匹配（包括协议、域名、路径）

### 问题：检查点文件太大

**解决方案**: 这是正常的，文件包含完整的文章内容。可以定期备份并清理旧文件。

