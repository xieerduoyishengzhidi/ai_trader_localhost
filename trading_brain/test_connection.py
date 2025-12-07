"""
测试 Macro Service 连接
"""
import requests
import sys

MACRO_SERVICE_URL = "http://localhost:8001"

def test_connection():
    """测试 Macro Service 连接"""
    print("🔍 测试 Macro Service 连接...")
    
    try:
        response = requests.get(f"{MACRO_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Macro Service 连接成功")
            print(f"   状态: {data.get('status')}")
            print(f"   FRED: {'可用' if data.get('fred_available') else '不可用'}")
            print(f"   yfinance: {'可用' if data.get('yfinance_available') else '不可用'}")
            print(f"   DeFi Llama: {'可用' if data.get('defillama_available') else '不可用'}")
            print(f"   Crypto Fetcher: {'可用' if data.get('crypto_fetcher_available') else '不可用'}")
            return True
        else:
            print(f"❌ Macro Service 返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 Macro Service ({MACRO_SERVICE_URL})")
        print("   请确保 macro_service 正在运行:")
        print("   cd macro_service")
        print("   python app.py")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

