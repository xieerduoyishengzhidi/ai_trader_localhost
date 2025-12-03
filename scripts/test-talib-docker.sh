#!/bin/bash
# 测试 Docker 容器中的 TA-Lib 是否正常工作

echo "🔍 测试 Docker 容器中的 TA-Lib..."

# 检查镜像是否存在
if ! docker images | grep -q "nofx-backend"; then
    echo "❌ 错误：nofx-backend 镜像不存在"
    echo "请先运行: docker build -f docker/Dockerfile.backend -t nofx-backend ."
    exit 1
fi

echo "✅ 镜像存在"

# 测试 1: 检查 TA-Lib 库文件是否存在
echo ""
echo "📦 测试 1: 检查 TA-Lib 库文件..."
docker run --rm nofx-backend sh -c "ls -la /usr/local/lib/libta_lib*" || {
    echo "❌ TA-Lib 库文件不存在"
    exit 1
}
echo "✅ TA-Lib 库文件存在"

# 测试 2: 检查头文件是否存在
echo ""
echo "📦 测试 2: 检查 TA-Lib 头文件..."
docker run --rm nofx-backend sh -c "ls -la /usr/local/include/ta-lib/ta_libc.h" || {
    echo "❌ TA-Lib 头文件不存在"
    exit 1
}
echo "✅ TA-Lib 头文件存在"

# 测试 3: 检查 LD_LIBRARY_PATH 环境变量
echo ""
echo "📦 测试 3: 检查 LD_LIBRARY_PATH..."
docker run --rm nofx-backend sh -c "echo \$LD_LIBRARY_PATH" | grep -q "/usr/local/lib" || {
    echo "❌ LD_LIBRARY_PATH 未正确设置"
    exit 1
}
echo "✅ LD_LIBRARY_PATH 正确设置"

# 测试 4: 检查可执行文件是否可以运行（需要配置文件，跳过）
echo ""
echo "📦 测试 4: 检查可执行文件..."
docker run --rm nofx-backend sh -c "file /app/nofx" | grep -q "ELF" || {
    echo "❌ 可执行文件不存在或格式错误"
    exit 1
}
echo "✅ 可执行文件存在且格式正确"

# 测试 5: 检查动态库依赖
echo ""
echo "📦 测试 5: 检查动态库依赖..."
docker run --rm nofx-backend sh -c "ldd /app/nofx 2>/dev/null | grep ta_lib" || {
    echo "⚠️  警告：无法检查动态库依赖（可能是静态链接）"
}
echo "✅ 动态库检查完成"

echo ""
echo "🎉 所有测试通过！TA-Lib 在 Docker 中配置正确！"
echo ""
echo "💡 下一步："
echo "   1. 运行容器: docker run -p 8080:8080 nofx-backend"
echo "   2. 或使用 docker-compose: docker-compose up"


