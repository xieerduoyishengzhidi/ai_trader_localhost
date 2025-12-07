# 依赖安装指南

## Windows 安装问题解决

如果遇到编译错误（缺少 C 编译器），请使用以下方法：

### 方法 1: 使用预编译包（推荐）

运行 PowerShell 脚本：

```powershell
cd macro_service
.\install_dependencies.ps1
```

或者手动安装：

```powershell
# 升级 pip
python -m pip install --upgrade pip

# 先安装 numpy（使用预编译包）
pip install numpy --only-binary :all:

# 再安装 pandas（使用预编译包）
pip install pandas --only-binary :all:

# 安装其他依赖
pip install flask==3.0.0
pip install pydantic==2.5.0
pip install fredapi==0.5.1
pip install yfinance==0.2.40
pip install requests==2.31.0
pip install ccxt==4.2.25
pip install lxml
```

### 方法 2: 使用 conda（如果使用 conda 环境）

```powershell
conda install pandas numpy
pip install flask==3.0.0 pydantic==2.5.0 fredapi==0.5.1 yfinance==0.2.40 requests==2.31.0 ccxt==4.2.25 lxml
```

### 方法 3: 安装 Visual Studio Build Tools（如果需要编译）

1. 下载并安装 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. 安装时选择 "C++ build tools" 工作负载
3. 然后重新运行 `pip install -r requirements.txt`

## 验证安装

```powershell
python -c "import flask; import fredapi; import yfinance; import ccxt; import pandas; import numpy; print('✅ 所有依赖安装成功')"
```

## 常见问题

### Q: 为什么需要先安装 numpy？
A: pandas 依赖 numpy，先安装预编译的 numpy 可以避免编译问题。

### Q: `--only-binary :all:` 是什么意思？
A: 强制使用预编译的 wheel 包，不尝试从源码编译。

### Q: 如果还是失败怎么办？
A: 尝试使用 conda 环境，或者安装 Visual Studio Build Tools。

