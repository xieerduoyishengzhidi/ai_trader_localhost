"""
API 诊断脚本 - 检查各个 API 端点是否正常工作
"""
import requests
import json
from datetime import datetime, timedelta

MACRO_SERVICE_URL = "http://localhost:8001"

def test_endpoint(name, method, endpoint, data=None):
    """测试单个 API 端点"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    url = f"{MACRO_SERVICE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            if isinstance(result, dict):
                # 显示关键字段
                if "data" in result:
                    data_count = len(result["data"]) if isinstance(result["data"], list) else "N/A"
                    print(f"   数据点数量: {data_count}")
                if "error" in result:
                    print(f"   ⚠️  错误: {result['error']}")
            return True
        else:
            print(f"❌ 失败")
            try:
                error = response.json()
                print(f"   错误信息: {error.get('error', 'Unknown error')}")
            except:
                print(f"   响应: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    print("="*60)
    print("API 诊断工具")
    print("="*60)
    
    # 1. 健康检查
    test_endpoint("健康检查", "GET", "/health")
    
    # 2. FRED API 测试
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    test_endpoint("FRED - DGS2 (2年美债)", "POST", "/api/fred/series", {
        "series_id": "DGS2",
        "start_date": start_date,
        "end_date": end_date
    })
    
    test_endpoint("FRED - T10Y2Y (收益率曲线)", "POST", "/api/fred/series", {
        "series_id": "T10Y2Y",
        "start_date": start_date,
        "end_date": end_date
    })
    
    # 3. yfinance API 测试
    test_endpoint("yfinance - ^TNX (10年美债)", "POST", "/api/yfinance/quote", {
        "symbol": "^TNX",
        "period": "3mo",
        "interval": "1d"
    })
    
    test_endpoint("yfinance - DX-Y.NYB (美元指数)", "POST", "/api/yfinance/quote", {
        "symbol": "DX-Y.NYB",
        "period": "3mo",
        "interval": "1d"
    })
    
    # 4. Crypto API 测试
    test_endpoint("Crypto - 完整数据", "POST", "/api/crypto/all", {
        "symbol": "BTC/USDT"
    })
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)

if __name__ == "__main__":
    main()

