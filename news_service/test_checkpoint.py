"""
测试检查点功能
"""
import sys
import pandas as pd
import os

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 测试检查点文件
checkpoint_file = "test_checkpoint.csv"

# 创建测试数据
test_data = [
    {"id": "abc123", "url": "https://test.com/1", "title": "Test 1"},
    {"id": "def456", "url": "https://test.com/2", "title": "Test 2"},
    {"id": "ghi789", "url": "https://test.com/3", "title": "Test 3"},
    {"id": "jkl012", "url": "https://test.com/4", "title": "Test 4"},
    {"id": "mno345", "url": "https://test.com/5", "title": "Test 5"},
]

print("🧪 测试检查点功能\n")

# 1. 保存检查点
print("1️⃣ 保存检查点文件...")
df = pd.DataFrame(test_data)
df.to_csv(checkpoint_file, index=False, encoding='utf-8-sig')
print(f"   ✅ 已保存 {len(test_data)} 条数据到 {checkpoint_file}")

# 2. 读取检查点
print("\n2️⃣ 读取检查点文件...")
if os.path.exists(checkpoint_file):
    df_loaded = pd.read_csv(checkpoint_file, encoding='utf-8-sig')
    processed_urls = set(df_loaded['url'].tolist())
    print(f"   ✅ 读取成功: {len(processed_urls)} 条URL")
    print(f"   📋 已处理的URL:")
    for url in processed_urls:
        print(f"      - {url}")

# 3. 模拟继续处理
print("\n3️⃣ 模拟继续处理...")
all_urls = [
    "https://test.com/1",
    "https://test.com/2",
    "https://test.com/3",
    "https://test.com/4",
    "https://test.com/5",
    "https://test.com/6",  # 新的
    "https://test.com/7",  # 新的
]

remaining_urls = [url for url in all_urls if url not in processed_urls]
print(f"   📊 总URL数: {len(all_urls)}")
print(f"   ✅ 已处理: {len(processed_urls)}")
print(f"   ⏳ 待处理: {len(remaining_urls)}")
print(f"   📋 待处理的URL:")
for url in remaining_urls:
    print(f"      - {url}")

# 4. 清理测试文件
print("\n4️⃣ 清理测试文件...")
if os.path.exists(checkpoint_file):
    os.remove(checkpoint_file)
    print(f"   ✅ 已删除 {checkpoint_file}")

print("\n✅ 测试完成！")

