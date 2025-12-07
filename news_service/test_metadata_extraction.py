"""
测试 HTML 元数据提取功能
"""
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import trafilatura

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def test_extract_metadata(url):
    """测试从 URL 提取元数据"""
    print(f"\n🔍 测试 URL: {url}")
    print("=" * 80)
    
    title = ""
    publish_time = None
    
    # 方法1: 使用 trafilatura 提取元数据
    print("\n1️⃣ 使用 trafilatura 提取元数据:")
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            metadata = trafilatura.extract_metadata(downloaded)
            if metadata:
                print(f"   ✅ 标题: {metadata.title}")
                print(f"   ✅ 日期: {metadata.date}")
                print(f"   ✅ 作者: {metadata.author}")
                print(f"   ✅ 描述: {metadata.description[:100] if metadata.description else 'N/A'}...")
                
                if metadata.title:
                    title = metadata.title
                if metadata.date:
                    try:
                        publish_time = datetime.fromisoformat(str(metadata.date).replace('Z', '+00:00'))
                        print(f"   ✅ 解析后的时间: {publish_time}")
                    except Exception as e:
                        print(f"   ⚠️ 时间解析失败: {e}")
            else:
                print("   ❌ trafilatura 未提取到元数据")
    except Exception as e:
        print(f"   ❌ trafilatura 提取失败: {e}")
    
    # 方法2: 从 HTML 中提取
    print("\n2️⃣ 从 HTML 中提取元数据:")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        print("\n   📝 提取标题:")
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                print(f"   ✅ <title> 标签: {title}")
            else:
                print("   ❌ 未找到 <title> 标签")
        
        # 提取发布时间
        print("\n   📅 提取发布时间:")
        time_selectors = [
            ('time[datetime]', 'time 标签的 datetime 属性'),
            ('meta[property="article:published_time"]', 'Open Graph 发布时间'),
            ('meta[name="publish-date"]', 'publish-date meta'),
            ('meta[name="date"]', 'date meta'),
            ('meta[property="article:published"]', 'article:published'),
            ('[class*="date"]', '包含 date 的 class'),
            ('[class*="time"]', '包含 time 的 class'),
        ]
        
        found_time = False
        for selector, desc in time_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    time_str = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                    if time_str:
                        print(f"   ✅ {desc}: {time_str}")
                        if not found_time:
                            try:
                                publish_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                print(f"      ✅ 解析成功: {publish_time}")
                                found_time = True
                            except:
                                try:
                                    publish_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                                    print(f"      ✅ 解析成功: {publish_time}")
                                    found_time = True
                                except Exception as e:
                                    print(f"      ⚠️ 解析失败: {e}")
            except:
                pass
        
        if not found_time:
            print("   ❌ 未找到发布时间")
        
        # 显示所有可能的 meta 标签
        print("\n   🔍 所有相关的 meta 标签:")
        meta_tags = soup.find_all('meta')
        relevant_metas = []
        for meta in meta_tags:
            prop = meta.get('property', '') or meta.get('name', '')
            content = meta.get('content', '')
            if any(kw in prop.lower() for kw in ['date', 'time', 'publish', 'article']):
                relevant_metas.append((prop, content))
        
        if relevant_metas:
            for prop, content in relevant_metas[:10]:  # 只显示前10个
                print(f"      - {prop}: {content[:80]}")
        else:
            print("      ❌ 未找到相关 meta 标签")
            
    except Exception as e:
        print(f"   ❌ HTML 提取失败: {e}")
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 提取结果总结:")
    print(f"   标题: {title[:80] if title else '未提取到'}")
    print(f"   发布时间: {publish_time if publish_time else '未提取到'}")
    print("=" * 80)
    
    return title, publish_time

if __name__ == "__main__":
    # 测试几个真实的 CoinTelegraph URL（从实际抓取的数据中获取）
    test_urls = [
        "https://cointelegraph.com/news/eu-crypto-regulations-imf-stablecoin-risk-global-express",
        "https://cointelegraph.com/news/bitcoin-treasury-firms-enter-darwinian-phase-as-premiums-collapse",
        "https://cointelegraph.com/news/clear-street-prepares-10b-ipo-as-crypto-treasury-boom-falters"
    ]
    
    print("🧪 开始测试 HTML 元数据提取功能\n")
    
    for idx, url in enumerate(test_urls, 1):
        print(f"\n{'='*80}")
        print(f"测试 {idx}/{len(test_urls)}")
        print(f"{'='*80}")
        test_extract_metadata(url)
        if idx < len(test_urls):
            print("\n⏸️  等待2秒后继续下一个测试...")
            import time
            time.sleep(2)

