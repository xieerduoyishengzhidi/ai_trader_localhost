"""
系统测试和配置检查脚本
检查端口冲突、API配置、依赖安装等
"""
import os
import sys
import socket
import subprocess
import requests
from pathlib import Path

# 设置Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_port(port: int) -> bool:
    """检查端口是否被占用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def check_dependencies():
    """检查Python依赖"""
    print("\n📦 检查Python依赖...")
    required_packages = {
        'requests': 'requests',
        'flask': 'flask',
        'fredapi': 'fredapi',
        'yfinance': 'yfinance',
        'ccxt': 'ccxt',
        'pandas': 'pandas',
        'pydantic': 'pydantic'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (缺失)")
            missing.append(package)
    
    return missing

def check_api_keys():
    """检查API Key配置"""
    print("\n🔑 检查API Key配置...")
    
    api_config = {
        "FRED_API_KEY": {
            "required": True,
            "default": "bd89c0475f61d7555dee50daed12185f",
            "description": "FRED API密钥（已内置默认值）",
            "env_var": "FRED_API_KEY"
        },
        "BINANCE_API_KEY": {
            "required": False,
            "description": "Binance API密钥（可选，提高频率限制）",
            "env_var": "BINANCE_API_KEY"
        },
        "BINANCE_SECRET": {
            "required": False,
            "description": "Binance API密钥（可选，提高频率限制）",
            "env_var": "BINANCE_SECRET"
        },
        "MACRO_SERVICE_URL": {
            "required": False,
            "default": "http://localhost:8001",
            "description": "Macro Service URL",
            "env_var": "MACRO_SERVICE_URL"
        }
    }
    
    for key, config in api_config.items():
        env_value = os.getenv(config["env_var"])
        if env_value:
            print(f"  ✅ {key}: 已设置 (环境变量)")
        elif "default" in config:
            print(f"  ⚠️  {key}: 使用默认值 ({config['default']})")
        elif config["required"]:
            print(f"  ❌ {key}: 未设置 (必需)")
        else:
            print(f"  ⚠️  {key}: 未设置 (可选)")
    
    return api_config

def check_macro_service():
    """检查Macro Service是否运行"""
    print("\n🌐 检查Macro Service连接...")
    
    url = os.getenv("MACRO_SERVICE_URL", "http://localhost:8001")
    
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Macro Service 运行正常 ({url})")
            print(f"     FRED: {'可用' if data.get('fred_available') else '不可用'}")
            print(f"     yfinance: {'可用' if data.get('yfinance_available') else '不可用'}")
            print(f"     DeFi Llama: {'可用' if data.get('defillama_available') else '不可用'}")
            print(f"     Crypto Fetcher: {'可用' if data.get('crypto_fetcher_available') else '不可用'}")
            return True
        else:
            print(f"  ❌ Macro Service 返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 无法连接到 Macro Service ({url})")
        print(f"     请确保 macro_service 正在运行")
        return False
    except Exception as e:
        print(f"  ❌ 连接测试失败: {e}")
        return False

def check_ports():
    """检查端口占用情况"""
    print("\n🔌 检查端口占用...")
    
    ports_to_check = {
        8001: "Macro Service (macro_service/app.py)",
        8000: "Instructor Service (instructor_service/app.py)"
    }
    
    for port, service in ports_to_check.items():
        if check_port(port):
            print(f"  ⚠️  端口 {port} 已被占用 ({service})")
            print(f"     如果这是其他服务，请修改配置或停止该服务")
        else:
            print(f"  ✅ 端口 {port} 可用 ({service})")

def check_directories():
    """检查目录结构"""
    print("\n📁 检查目录结构...")
    
    base_dir = Path(__file__).parent.parent
    
    required_dirs = {
        "macro_service": "Macro Service目录",
        "trading_brain": "Trading Brain目录",
        "trading_brain/output": "输出目录（会自动创建）"
    }
    
    for dir_path, description in required_dirs.items():
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"  ✅ {description}: {full_path}")
        else:
            print(f"  ❌ {description}: 不存在 ({full_path})")
            if dir_path == "trading_brain/output":
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    print(f"     → 已自动创建")
                except:
                    pass

def print_setup_instructions():
    """打印设置说明"""
    print("\n" + "=" * 80)
    print("📋 设置说明")
    print("=" * 80)
    print("\n1. 安装依赖:")
    print("   cd macro_service")
    print("   pip install -r requirements.txt")
    print("   cd ../trading_brain")
    print("   pip install -r requirements.txt")
    
    print("\n2. 设置环境变量（可选，已有默认值）:")
    print("   $env:FRED_API_KEY='bd89c0475f61d7555dee50daed12185f'")
    print("   $env:BINANCE_API_KEY='your_binance_key'  # 可选")
    print("   $env:BINANCE_SECRET='your_binance_secret'  # 可选")
    print("   $env:MACRO_SERVICE_URL='http://localhost:8001'  # 可选")
    
    print("\n3. 启动Macro Service:")
    print("   cd macro_service")
    print("   python app.py")
    
    print("\n4. 运行Trading Brain（新终端）:")
    print("   cd trading_brain")
    print("   python main.py")
    
    print("\n5. 测试连接:")
    print("   python test_connection.py")
    print("=" * 80)

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 Trading Brain 系统测试和配置检查")
    print("=" * 80)
    
    # 检查目录结构
    check_directories()
    
    # 检查端口
    check_ports()
    
    # 检查依赖
    missing = check_dependencies()
    
    # 检查API配置
    api_config = check_api_keys()
    
    # 检查Macro Service
    macro_service_ok = check_macro_service()
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 检查总结")
    print("=" * 80)
    
    issues = []
    
    if missing:
        issues.append(f"❌ 缺失 {len(missing)} 个Python包: {', '.join(missing)}")
    
    if not macro_service_ok:
        issues.append("❌ Macro Service 未运行或无法连接")
    
    if issues:
        print("\n⚠️  发现以下问题:")
        for issue in issues:
            print(f"  {issue}")
        print_setup_instructions()
        return False
    else:
        print("\n✅ 所有检查通过！系统已就绪。")
        print("\n可以运行以下命令开始使用:")
        print("  cd trading_brain")
        print("  python main.py")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

