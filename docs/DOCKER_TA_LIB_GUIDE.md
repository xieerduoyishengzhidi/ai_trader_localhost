# Docker 中使用 TA-Lib 完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [构建镜像](#构建镜像)
3. [运行容器](#运行容器)
4. [验证 TA-Lib](#验证-talib)
5. [故障排查](#故障排查)
6. [常见问题](#常见问题)

## 🚀 快速开始

### 前提条件

- Docker Desktop 已安装并运行
- 项目代码已克隆到本地

### 一键启动

```powershell
# Windows PowerShell
docker-compose up -d
```

```bash
# Linux/macOS
docker-compose up -d
```

## 🔨 构建镜像

### 方法 1: 使用 Dockerfile 直接构建

```powershell
# Windows PowerShell
docker build -f docker/Dockerfile.backend -t nofx-backend .
```

```bash
# Linux/macOS
docker build -f docker/Dockerfile.backend -t nofx-backend .
```

### 方法 2: 使用 Docker Compose 构建

```powershell
# Windows PowerShell
docker-compose build nofx
```

```bash
# Linux/macOS
docker-compose build nofx
```

### 构建过程说明

Dockerfile 使用**多阶段构建**：

1. **ta-lib-builder 阶段**：
   - 从源码编译 TA-Lib 0.4.0
   - 安装到 `/usr/local`
   - 包含头文件和库文件

2. **backend-builder 阶段**：
   - 复制 TA-Lib 到构建环境
   - 设置 CGO 编译选项
   - 编译 Go 应用程序

3. **运行时阶段**：
   - 最小化 Alpine 镜像
   - 复制 TA-Lib 库文件
   - 设置 `LD_LIBRARY_PATH`

## 🐳 运行容器

### 方法 1: 直接运行 Docker 容器

```powershell
# Windows PowerShell
docker run -d `
  --name nofx-backend `
  -p 8080:8080 `
  -v ${PWD}/config.json:/app/config.json:ro `
  -v ${PWD}/config.db:/app/config.db `
  -v ${PWD}/decision_logs:/app/decision_logs `
  -v ${PWD}/prompts:/app/prompts `
  -e TZ=Asia/Shanghai `
  nofx-backend
```

```bash
# Linux/macOS
docker run -d \
  --name nofx-backend \
  -p 8080:8080 \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/config.db:/app/config.db \
  -v $(pwd)/decision_logs:/app/decision_logs \
  -v $(pwd)/prompts:/app/prompts \
  -e TZ=Asia/Shanghai \
  nofx-backend
```

### 方法 2: 使用 Docker Compose（推荐）

```powershell
# Windows PowerShell
docker-compose up -d
```

```bash
# Linux/macOS
docker-compose up -d
```

### 查看日志

```powershell
# Windows PowerShell
docker logs -f nofx-trading
```

```bash
# Linux/macOS
docker logs -f nofx-trading
```

## ✅ 验证 TA-Lib

### 方法 1: 使用测试脚本（推荐）

```powershell
# Windows PowerShell
.\scripts\test-talib-docker.ps1
```

```bash
# Linux/macOS
chmod +x scripts/test-talib-docker.sh
./scripts/test-talib-docker.sh
```

### 方法 2: 手动验证

#### 检查 TA-Lib 库文件

```powershell
docker run --rm nofx-backend sh -c "ls -la /usr/local/lib/libta_lib*"
```

应该看到：
```
-rwxr-xr-x    1 root     root       2305232 Nov 26 12:24 /usr/local/lib/libta_lib.so.0.0.0
```

#### 检查头文件

```powershell
docker run --rm nofx-backend sh -c "ls -la /usr/local/include/ta-lib/ta_libc.h"
```

应该看到：
```
-rw-r--r--    1 root     root         ... /usr/local/include/ta-lib/ta_libc.h
```

#### 检查环境变量

```powershell
docker run --rm nofx-backend sh -c "echo \$LD_LIBRARY_PATH"
```

应该输出：
```
/usr/local/lib
```

#### 检查动态库链接

```powershell
docker run --rm nofx-backend sh -c "ldd /app/nofx | grep ta_lib"
```

应该看到 TA-Lib 库的链接信息。

### 方法 3: 功能测试

启动容器后，访问 API 端点检查形态识别功能：

```powershell
# 检查健康状态
curl http://localhost:8080/api/health

# 获取市场数据（包含形态识别）
curl http://localhost:8080/api/market/data?symbol=BTCUSDT
```

检查返回的 JSON 中是否包含 `pattern_recognition` 字段。

## 🔧 故障排查

### 问题 1: 构建失败 - 找不到 ta_libc.h

**错误信息**：
```
fatal error: ta_libc.h: No such file or directory
```

**解决方案**：
- ✅ 已修复：Dockerfile 已包含正确的头文件路径
- 确保使用最新的 Dockerfile.backend

### 问题 2: 运行时错误 - 找不到 libta_lib.so

**错误信息**：
```
error while loading shared libraries: libta_lib.so.0: cannot open shared object file
```

**解决方案**：
- ✅ 已修复：运行时阶段已复制库文件并设置 LD_LIBRARY_PATH
- 检查容器中的环境变量：`docker exec nofx-trading env | grep LD_LIBRARY_PATH`

### 问题 3: 编译错误 - 类型不匹配

**错误信息**：
```
cannot use cOutReal (variable of type *_Ctype_double) as *_Ctype_int value
```

**解决方案**：
- ✅ 已修复：代码已更新为使用正确的类型（C.int）
- 确保使用最新的 market/pattern.go

### 问题 4: 函数参数错误

**错误信息**：
```
not enough arguments in call to (_Cfunc_TA_CDLDARKCLOUDCOVER)
```

**解决方案**：
- ✅ 已修复：已为需要 penetration 参数的函数添加参数
- 确保使用最新的 market/pattern.go

## ❓ 常见问题

### Q1: 为什么需要多阶段构建？

**A**: 多阶段构建可以：
- 减小最终镜像大小（只包含运行时需要的文件）
- 分离编译环境和运行环境
- 共享 TA-Lib 编译结果

### Q2: TA-Lib 版本是什么？

**A**: 当前使用 TA-Lib 0.4.0，在 Dockerfile 中通过 `ARG TA_LIB_VERSION=0.4.0` 定义。

### Q3: 如何更新 TA-Lib 版本？

**A**: 修改 Dockerfile.backend 中的 `ARG TA_LIB_VERSION` 值，然后重新构建镜像。

### Q4: 可以在本地开发时使用 Docker 中的 TA-Lib 吗？

**A**: 可以，但建议在本地也安装 TA-Lib，这样开发更方便。Docker 主要用于生产环境。

### Q5: 容器启动后如何验证形态识别功能？

**A**: 
1. 查看日志：`docker logs -f nofx-trading`
2. 调用 API：`curl http://localhost:8080/api/market/data?symbol=BTCUSDT`
3. 检查返回的 JSON 中是否有 `pattern_recognition` 字段

## 📚 相关文档

- [TA-Lib 形态识别使用指南](USAGE_GUIDE_CANDLESTICK_PATTERN.md)
- [TA-Lib 输入指标分析](TA_LIB_PATTERN_INPUT_ANALYSIS.md)
- [变更日志](CHANGELOG_CANDLESTICK_PATTERN.md)

## 🎯 快速参考

### 常用命令

```powershell
# 构建镜像
docker build -f docker/Dockerfile.backend -t nofx-backend .

# 运行容器
docker run -p 8080:8080 nofx-backend

# 使用 docker-compose
docker-compose up -d

# 查看日志
docker logs -f nofx-trading

# 进入容器
docker exec -it nofx-trading sh

# 测试 TA-Lib
.\scripts\test-talib-docker.ps1
```

---

**最后更新**: 2025-01-XX  
**Docker 镜像**: nofx-backend:latest  
**TA-Lib 版本**: 0.4.0


