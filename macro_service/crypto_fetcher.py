"""
Crypto Data Fetcher - 币圈原生数据抓取模块
集成 ccxt、Farside、DeFi Llama、CoinGecko 等数据源
用于补全 Pentosh1 策略所需的非宏观数据
"""
import ccxt
import pandas as pd
import requests
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CryptoDataLoader:
    def __init__(self, api_key=None, secret=None):
        """
        初始化币安合约接口
        即使不填 Key 也能获取行情数据，填了 Key 频次限制更宽松
        """
        try:
            self.exchange = ccxt.binanceusdm({
                'apiKey': api_key or '',
                'secret': secret or '',
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'  # 使用期货市场
                }
            })
            logger.info("✅ Binance 期货接口初始化成功")
        except Exception as e:
            logger.error(f"❌ 初始化 Binance 接口失败: {e}")
            self.exchange = None

    def get_binance_futures_data(self, symbol="BTC/USDT") -> Optional[Dict[str, Any]]:
        """
        获取第四层级：情绪与博弈数据
        包含：价格, 资金费率, 持仓量(OI), 多空比
        
        Pentosh1 逻辑：
        - 资金费率 > 0.01% (年化10%) 偏多头拥挤，> 0.03% 极度危险
        - OI 暴涨但价格滞涨 = 庄家正在派发或吸筹，即将变盘
        """
        if not self.exchange:
            logger.error("Binance 交易所未初始化")
            return None
            
        try:
            # 标准化 symbol 格式
            if "/" not in symbol:
                symbol = f"{symbol}/USDT"
            
            # 1. 获取基础行情 (价格 & 24h变化)
            ticker = self.exchange.fetch_ticker(symbol)
            
            # 2. 获取资金费率 (Funding Rate)
            funding = self.exchange.fetch_funding_rate(symbol)
            
            # 3. 获取未平仓合约 (Open Interest)
            oi = self.exchange.fetch_open_interest(symbol)
            
            # 4. 获取多空比 (Long/Short Ratio)
            # CCXT 标准方法有时拿不到这个特定的 Global Ratio，直接调 API 更稳
            # 这是一个公共端点，不需要签名
            symbol_clean = symbol.replace("/", "")  # 转为 BTCUSDT
            ls_url = "https://fapi.binance.com/fapi/data/globalLongShortAccountRatio"
            ls_params = {
                "symbol": symbol_clean,
                "period": "1d",  # 关注日线级别的多空倾向
                "limit": 1
            }
            
            ls_resp = requests.get(ls_url, params=ls_params, timeout=10)
            ls_data = ls_resp.json() if ls_resp.status_code == 200 else []
            ls_ratio = float(ls_data[0]['longShortRatio']) if ls_data else None
            
            return {
                "symbol": symbol,
                "price": ticker['last'],
                "price_change_24h_pct": ticker['percentage'],
                "funding_rate": funding['fundingRate'],
                "funding_yearly_pct": funding['fundingRate'] * 3 * 365 * 100,  # 换算成年化百分比
                "open_interest_btc": oi['openInterestAmount'],  # 持仓多少个BTC
                "open_interest_usd": oi['openInterestValue'],   # 持仓价值多少U
                "long_short_ratio": ls_ratio,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 获取 Binance 期货数据失败 ({symbol}): {e}", exc_info=True)
            return None

    def get_etf_flows(self) -> Dict[str, Any]:
        """
        获取第二层级：机构资金 (BTC ETF Net Inflow)
        来源：直接爬取 Farside 网页表格
        
        Pentosh1 逻辑：净流入 > $200M = 强趋势信号
        """
        url = "https://farside.co.uk/btc/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        try:
            # Pandas 自动识别网页里的表格
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            tables = pd.read_html(response.text)
            if not tables:
                return {"etf_net_inflow_total": 0, "status": "No table found"}
            
            df = tables[0]
            
            # 这是一个大表格，最后几行通常是最新的
            # 我们只需要最后一行的数据（昨天的收盘数据）
            # Farside 的列名经常变，但 'Total' 列通常比较稳定
            latest = df.iloc[-1]
            
            # 有时候最后一行是空数据（今天还没出），取倒数第二行
            if pd.isna(latest.get('Total', None)) and len(df) > 1:
                latest = df.iloc[-2]
            
            # 尝试解析数值（可能是字符串格式，如 "123.45M"）
            total_value = latest.get('Total', 0)
            ibit_value = latest.get('IBIT', 0)
            
            # 如果是字符串，尝试提取数字
            if isinstance(total_value, str):
                try:
                    # 移除 M, B 等后缀并转换
                    total_value = float(total_value.replace('M', '').replace('B', '').replace(',', '').strip())
                    if 'B' in str(latest.get('Total', '')):
                        total_value *= 1000  # B 转 M
                except:
                    total_value = 0
            
            if isinstance(ibit_value, str):
                try:
                    ibit_value = float(ibit_value.replace('M', '').replace('B', '').replace(',', '').strip())
                    if 'B' in str(latest.get('IBIT', '')):
                        ibit_value *= 1000
                except:
                    ibit_value = 0
            
            return {
                "etf_date": str(latest.get('Date', 'Unknown')),
                "etf_net_inflow_total": total_value,  # 单位通常是 Million USD
                "etf_ibit_flow": ibit_value,  # 贝莱德的数据，作为风向标
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 获取 ETF 数据失败: {e}", exc_info=True)
            return {
                "etf_net_inflow_total": 0,
                "etf_ibit_flow": 0,
                "status": f"Fetch Failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_market_structure_and_liquidity(self) -> Dict[str, Any]:
        """
        获取第二层级(稳定币) & 第三层级(BTC.D, TOTAL3) & 第四层级(恐慌指数)
        """
        metrics = {}
        
        # 1. 稳定币总市值 (DeFi Llama)
        try:
            stable_url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
            resp = requests.get(stable_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            total_stable_cap = 0
            for coin in data.get('peggedAssets', []):
                # 统计主流稳定币
                if coin.get('symbol') in ['USDT', 'USDC', 'DAI', 'FDUSD', 'USDe']:
                    circulating = coin.get('circulating', {})
                    if isinstance(circulating, dict):
                        total_stable_cap += (circulating.get('peggedUSD') or 0)
                    elif isinstance(circulating, (int, float)):
                        total_stable_cap += circulating
            
            metrics['stablecoin_total_cap_billions'] = round(total_stable_cap / 1e9, 2)
        except Exception as e:
            logger.warning(f"获取稳定币数据失败: {e}")
            metrics['stablecoin_total_cap_billions'] = 0
        
        # 2. 市场结构: BTC.D 和 TOTAL3 (CoinGecko)
        try:
            # CoinGecko 免费版无需 Key，限制约 10-30次/分钟
            cg_url = "https://api.coingecko.com/api/v3/global"
            cg_resp = requests.get(cg_url, timeout=10)
            cg_resp.raise_for_status()
            cg_data = cg_resp.json()['data']
            
            btc_d = cg_data['market_cap_percentage']['btc']
            eth_d = cg_data['market_cap_percentage']['eth']
            total_cap = cg_data['total_market_cap']['usd']
            
            # 计算 TOTAL3 (Crypto Total Market Cap Excluding BTC & ETH)
            # 这是一个近似值，非常接近 TradingView 的 TOTAL3
            total3_val = total_cap * (1 - (btc_d/100) - (eth_d/100))
            
            metrics['btc_dominance'] = round(btc_d, 2)
            metrics['eth_dominance'] = round(eth_d, 2)
            metrics['total3_cap_billions'] = round(total3_val / 1e9, 2)
            metrics['total_market_cap_billions'] = round(total_cap / 1e9, 2)
        except Exception as e:
            logger.warning(f"获取 CoinGecko 数据失败: {e}")
            metrics['btc_dominance'] = 55.0  # Fallback
            metrics['total3_cap_billions'] = 0
        
        # 3. ETH/BTC Ratio (使用 Binance 价格计算)
        try:
            if self.exchange:
                eth_ticker = self.exchange.fetch_ticker("ETH/USDT")
                btc_ticker = self.exchange.fetch_ticker("BTC/USDT")
                eth_btc_ratio = eth_ticker['last'] / btc_ticker['last'] if btc_ticker['last'] > 0 else 0
                metrics['eth_btc_ratio'] = round(eth_btc_ratio, 6)
            else:
                # 备用方案：使用 CoinGecko
                eth_url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd"
                eth_resp = requests.get(eth_url, timeout=10)
                if eth_resp.status_code == 200:
                    prices = eth_resp.json()
                    eth_price = prices.get('ethereum', {}).get('usd', 0)
                    btc_price = prices.get('bitcoin', {}).get('usd', 0)
                    if btc_price > 0:
                        metrics['eth_btc_ratio'] = round(eth_price / btc_price, 6)
                    else:
                        metrics['eth_btc_ratio'] = 0
                else:
                    metrics['eth_btc_ratio'] = 0
        except Exception as e:
            logger.warning(f"计算 ETH/BTC 比率失败: {e}")
            metrics['eth_btc_ratio'] = 0
        
        # 4. 恐惧贪婪指数 (Alternative.me)
        try:
            fg_url = "https://api.alternative.me/fng/?limit=1"
            fg_resp = requests.get(fg_url, timeout=10)
            fg_resp.raise_for_status()
            fg_data = fg_resp.json()
            metrics['fear_greed_index'] = int(fg_data['data'][0]['value'])
            metrics['fear_greed_classification'] = fg_data['data'][0].get('value_classification', 'Neutral')
        except Exception as e:
            logger.warning(f"获取恐惧贪婪指数失败: {e}")
            metrics['fear_greed_index'] = 50
            metrics['fear_greed_classification'] = 'Neutral'
        
        metrics['timestamp'] = datetime.now().isoformat()
        return metrics

    def get_all_crypto_data(self, symbol="BTC/USDT") -> Dict[str, Any]:
        """
        获取所有币圈原生数据（整合方法）
        返回完整的 Pentosh1 数据面板
        """
        logger.info(f"📡 开始获取 {symbol} 的完整币圈数据...")
        
        # 获取各层级数据
        binance_data = self.get_binance_futures_data(symbol)
        etf_data = self.get_etf_flows()
        structure_data = self.get_market_structure_and_liquidity()
        
        # 整合数据
        full_crypto_context = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "layer2_flows": {
                "stablecoin_mcap_b": structure_data.get('stablecoin_total_cap_billions'),
                "etf_net_inflow_m": etf_data.get('etf_net_inflow_total'),
                "etf_ibit_flow_m": etf_data.get('etf_ibit_flow'),
                "etf_date": etf_data.get('etf_date')
            },
            "layer3_structure": {
                "btc_dominance": structure_data.get('btc_dominance'),
                "eth_dominance": structure_data.get('eth_dominance'),
                "eth_btc_ratio": structure_data.get('eth_btc_ratio'),
                "total3_cap_b": structure_data.get('total3_cap_billions'),
                "total_market_cap_b": structure_data.get('total_market_cap_billions')
            },
            "layer4_sentiment": {
                "price_btc": binance_data.get('price') if binance_data else None,
                "price_change_24h_pct": binance_data.get('price_change_24h_pct') if binance_data else None,
                "funding_rate": binance_data.get('funding_rate') if binance_data else None,
                "funding_rate_annualized_pct": round(binance_data.get('funding_yearly_pct', 0), 2) if binance_data else None,
                "open_interest_usd_b": round(binance_data.get('open_interest_usd', 0) / 1e9, 2) if binance_data else None,
                "open_interest_btc": binance_data.get('open_interest_btc') if binance_data else None,
                "long_short_ratio": binance_data.get('long_short_ratio') if binance_data else None,
                "fear_greed_index": structure_data.get('fear_greed_index'),
                "fear_greed_classification": structure_data.get('fear_greed_classification')
            }
        }
        
        return full_crypto_context


# 运行测试
if __name__ == "__main__":
    # 如果你有 Key，填在这里，没有就留 None
    # api_key = "YOUR_BINANCE_API_KEY"
    # secret = "YOUR_BINANCE_SECRET"
    
    loader = CryptoDataLoader()
    
    print("正在抓取 Binance 期货数据...")
    binance_data = loader.get_binance_futures_data("BTC/USDT")
    print(f"Binance 数据: {binance_data}")
    
    print("\n正在抓取 ETF 资金流向...")
    etf_data = loader.get_etf_flows()
    print(f"ETF 数据: {etf_data}")
    
    print("\n正在抓取链上流动性与市场结构...")
    structure_data = loader.get_market_structure_and_liquidity()
    print(f"市场结构数据: {structure_data}")
    
    print("\n========= 完整的 Pentosh1 数据面板 =========")
    full_data = loader.get_all_crypto_data("BTC/USDT")
    import json
    print(json.dumps(full_data, indent=2, ensure_ascii=False))

