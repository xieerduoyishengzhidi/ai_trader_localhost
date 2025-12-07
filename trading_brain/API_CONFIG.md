# API 配置说明

## 必需的 API Key

### 1. FRED API Key ✅ (已内置默认值)

**用途**: 获取美国联邦储备经济数据（GDP、失业率、CPI、利率等）

**状态**: ✅ 已内置默认值，无需配置即可使用

**默认值**: `bd89c0475f61d7555dee50daed12185f`

**如需更换**:
```powershell
$env:FRED_API_KEY="your_fred_api_key"
```

**获取方式**: 
- 访问 https://fred.stlouisfed.org/docs/api/api_key.html
- 免费注册账号即可获取

---

## 可选的 API Key

### 2. Binance API Key (可选)

**用途**: 提高 Binance API 调用频率限制

**状态**: ⚠️ 可选，不设置也能正常工作（但频率限制更严格）

**设置方式**:
```powershell
$env:BINANCE_API_KEY="your_binance_api_key"
$env:BINANCE_SECRET="your_binance_secret"
```

**获取方式**:
1. 登录 Binance 账号
2. 进入 API 管理页面
3. 创建新的 API Key（只需要读取权限，不需要交易权限）

**注意**: 
- 即使不设置 API Key，也能获取行情数据
- 设置后可以提高调用频率限制
- 建议只给读取权限，不要给交易权限

---

## 不需要 API Key 的服务

以下服务使用公开API，无需配置：

### ✅ yfinance
- **用途**: 获取股票、ETF、指数数据
- **API Key**: 不需要
- **限制**: 无特殊限制

### ✅ DeFi Llama
- **用途**: 获取 DeFi 协议数据
- **API Key**: 不需要
- **限制**: 公开API，无特殊限制

### ✅ CoinGecko
- **用途**: 获取市场结构数据（BTC.D、TOTAL3）
- **API Key**: 不需要（免费版）
- **限制**: 10-30次/分钟

### ✅ Alternative.me
- **用途**: 获取恐惧贪婪指数
- **API Key**: 不需要
- **限制**: 公开API

### ✅ Farside.co.uk
- **用途**: 爬取BTC ETF资金流向
- **API Key**: 不需要
- **限制**: 网页爬取，注意频率

---

## 环境变量配置

### Windows PowerShell

```powershell
# 必需（但已有默认值）
$env:FRED_API_KEY="bd89c0475f61d7555dee50daed12185f"

# 可选 - Binance API（提高频率限制）
$env:BINANCE_API_KEY="your_binance_api_key"
$env:BINANCE_SECRET="your_binance_secret"

# 可选 - Macro Service URL
$env:MACRO_SERVICE_URL="http://localhost:8001"
```

### Linux/Mac

```bash
# 必需（但已有默认值）
export FRED_API_KEY="bd89c0475f61d7555dee50daed12185f"

# 可选 - Binance API
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_SECRET="your_binance_secret"

# 可选 - Macro Service URL
export MACRO_SERVICE_URL="http://localhost:8001"
```

### 永久配置（Windows）

创建 `.env` 文件或在系统环境变量中设置。

---

## 端口配置

### Macro Service
- **默认端口**: 8001
- **配置文件**: `macro_service/app.py`
- **修改方式**: 
  ```python
  port = int(os.getenv("PORT", 8001))
  ```
  或设置环境变量：
  ```powershell
  $env:PORT="8001"
  ```

### Trading Brain
- **连接地址**: `http://localhost:8001`
- **配置文件**: `trading_brain/main.py`
- **修改方式**: 
  ```python
  MACRO_SERVICE_URL = os.getenv("MACRO_SERVICE_URL", "http://localhost:8001")
  ```

---

## 快速检查配置

运行测试脚本：

```powershell
cd trading_brain
python test_setup.py
```

这会检查：
- ✅ 端口占用情况
- ✅ Python依赖安装
- ✅ API Key配置
- ✅ Macro Service连接
- ✅ 目录结构

---

## 常见问题

### Q: FRED API Key 是必需的吗？
A: 技术上已内置默认值，但建议使用自己的Key以避免频率限制。

### Q: Binance API Key 是必需的吗？
A: 不是必需的。不设置也能正常工作，但频率限制更严格。

### Q: 如何检查端口是否被占用？
A: 运行 `python test_setup.py` 或使用：
```powershell
netstat -ano | findstr :8001
```

### Q: 如何修改端口？
A: 修改 `macro_service/app.py` 中的端口配置，或设置 `PORT` 环境变量。

---

## 配置优先级

1. **环境变量** (最高优先级)
2. **代码中的默认值**
3. **配置文件** (如果有)

