"""
Crypto Data Fetcher - 币圈原生数据抓取模块
集成 ccxt、Farside、DeFi Llama、CoinGecko 等数据源
用于补全 Pentosh1 策略所需的非宏观数据
"""
import ccxt
import pandas as pd
import requests
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
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
        
        self.cache_path = Path(__file__).resolve().parent / "data_cache.json"
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 读取缓存失败 ({self.cache_path}): {e}")
        return {"futures": {}, "etf": {}, "structure": {}}

    def _write_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ 写入缓存失败 ({self.cache_path}): {e}")

    def _update_cache_section(self, section: str, payload: Dict[str, Any]) -> None:
        section_data = self.cache.setdefault(section, {})
        section_data.update(payload)
        self._write_cache()

    def _get_cache_section(self, section: str) -> Dict[str, Any]:
        return self.cache.get(section, {})

    def _append_history(self, section: str, key: str, value: float, limit: int = 180) -> None:
        if value is None:
            return
        today = datetime.utcnow().strftime("%Y-%m-%d")
        history_key = f"{key}_history"
        history = self.cache.setdefault(section, {}).setdefault(history_key, [])
        if history and history[-1].get("date") == today:
            history[-1]["value"] = value
        else:
            history.append({"date": today, "value": value})
        self.cache[section][history_key] = history[-limit:]
        self._write_cache()

    def _get_history(self, section: str, key: str) -> list:
        return self.cache.get(section, {}).get(f"{key}_history", [])

    def _get_value_days_ago(self, section: str, key: str, days: int) -> Optional[float]:
        history = self._get_history(section, key)
        if not history:
            return None
        target_date = (datetime.utcnow() - timedelta(days=days)).date()
        for entry in reversed(history):
            try:
                entry_date = datetime.fromisoformat(entry["date"]).date()
            except Exception:
                continue
            if entry_date <= target_date:
                return entry["value"]
        # fallback to earliest available
        try:
            return history[0]["value"]
        except (IndexError, KeyError):
            return None

    def _compute_ma(self, section: str, key: str, length: int) -> Optional[float]:
        history = [entry["value"] for entry in self._get_history(section, key) if entry.get("value") is not None]
        if not history:
            return None
        window = history[-length:]
        return sum(window) / len(window)

    def _fill_with_cache(self, section: str, data: Dict[str, Any], zeros_missing: Optional[set] = None) -> Dict[str, Any]:
        zeros_missing = zeros_missing or set()
        cache_section = self._get_cache_section(section)
        for key, value in data.items():
            needs_fill = value is None or (key in zeros_missing and value == 0)
            if needs_fill:
                cached_value = cache_section.get(key)
                if cached_value is not None:
                    data[key] = cached_value
        return data

    def _compute_pct_change(self, section: str, key: str, days: int, current: Optional[float]) -> Optional[float]:
        if current is None:
            return None
        past = self._get_value_days_ago(section, key, days)
        if past is None or past == 0:
            return None
        return round((current - past) / past * 100, 2)

    def _parse_flow_value(self, raw: Any) -> Optional[float]:
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        text = str(raw).replace(',', '').strip()
        multiplier = 1.0
        if text.endswith('M'):
            multiplier = 1.0
            text = text[:-1]
        elif text.endswith('B'):
            multiplier = 1000.0
            text = text[:-1]
        try:
            return float(text) * multiplier
        except ValueError:
            return None

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
            
            result = {
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
            if result.get("price") is not None:
                self._append_history("futures", "price", result["price"])
            result = self._fill_with_cache("futures", result, zeros_missing={"price"})
            self._update_cache_section("futures", {
                "price": result.get("price"),
                "price_change_24h_pct": result.get("price_change_24h_pct"),
                "funding_rate": result.get("funding_rate"),
                "open_interest_usd": result.get("open_interest_usd"),
                "long_short_ratio": result.get("long_short_ratio")
            })
            return result
        except Exception as e:
            logger.error(f"❌ 获取 Binance 期货数据失败 ({symbol}): {e}", exc_info=True)
            cached = self._get_cache_section("futures")
            if cached:
                logger.warning("⚠️ Binance 期货数据回退到缓存值")
                cached_copy = dict(cached)
                cached_copy["symbol"] = symbol
                cached_copy["from_cache"] = True
                return cached_copy
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
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            tables = pd.read_html(response.text)
            if not tables:
                return {"etf_net_inflow_total": 0, "status": "No table found", "timestamp": datetime.now().isoformat()}

            df = tables[0]
            latest = df.iloc[-1]
            if pd.isna(latest.get('Total', None)) and len(df) > 1:
                latest = df.iloc[-2]

            total_value = self._parse_flow_value(latest.get('Total', 0))
            ibit_value = self._parse_flow_value(latest.get('IBIT', 0))
            date_str = str(latest.get('Date', 'Unknown')).strip()
            date_ts = pd.to_datetime(date_str, errors='coerce')
            is_weekend = False
            if not pd.isna(date_ts):
                is_weekend = date_ts.weekday() >= 5
                date_str = date_ts.strftime("%Y-%m-%d")

            status = "ok"
            if is_weekend and (total_value is None or total_value == 0):
                total_value = None
                status = "weekend_forward_fill"

            week_values = []
            for _, row in df.tail(7).iterrows():
                value = self._parse_flow_value(row.get('Total'))
                if value is not None:
                    week_values.append(value)
            week_avg = round(sum(week_values) / len(week_values), 2) if week_values else None

            result = {
                "etf_date": date_str or "Unknown",
                "etf_net_inflow_total": total_value,
                "etf_ibit_flow": ibit_value,
                "etf_weekly_avg_flow_m": week_avg,
                "etf_weekly_data_points": len(week_values),
                "status": status,
                "timestamp": datetime.now().isoformat()
            }

            cache_section = self._get_cache_section("etf")
            filled = False
            for key in ("etf_net_inflow_total", "etf_ibit_flow"):
                if result.get(key) is None:
                    cached_value = cache_section.get(key)
                    if cached_value is not None:
                        result[key] = cached_value
                        filled = True
            if filled and status == "ok":
                result["status"] = "forward_fill_from_cache"

            self._update_cache_section("etf", {
                "etf_net_inflow_total": result.get("etf_net_inflow_total"),
                "etf_ibit_flow": result.get("etf_ibit_flow"),
                "etf_date": result.get("etf_date"),
                "status": result.get("status")
            })

            return result
        except Exception as e:
            logger.error(f"❌ 获取 ETF 数据失败: {e}", exc_info=True)
            cached = self._get_cache_section("etf")
            if cached:
                cached_copy = dict(cached)
                cached_copy["from_cache"] = True
                cached_copy.setdefault("status", "cache_replay")
                cached_copy["timestamp"] = datetime.now().isoformat()
                return cached_copy

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
        self._append_history("structure", "stablecoin_cap", metrics['stablecoin_total_cap_billions'])
        
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
        self._append_history("structure", "btc_dom", metrics['btc_dominance'])
        self._append_history("structure", "total3", metrics['total3_cap_billions'])
        
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
        
        # 填补 Eth/BTC 等无法为 0 的字段
        metrics = self._fill_with_cache("structure", metrics, zeros_missing={"eth_btc_ratio"})

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
        metrics['btc_dom_trend_90d'] = self._compute_pct_change("structure", "btc_dom", 90, metrics.get('btc_dominance'))
        metrics['stablecoin_growth_30d_pct'] = self._compute_pct_change("structure", "stablecoin_cap", 30, metrics.get('stablecoin_total_cap_billions'))
        ma50 = self._compute_ma("structure", "total3", 50)
        if ma50 is not None and metrics.get('total3_cap_billions') is not None:
            metrics['total3_structure_status'] = "Above MA50" if metrics['total3_cap_billions'] >= ma50 else "Below MA50"
            metrics['total3_ma50_b'] = round(ma50, 2)
        else:
            metrics['total3_structure_status'] = "MA50 unavailable"

        self._update_cache_section("structure", {
            "stablecoin_total_cap_billions": metrics.get('stablecoin_total_cap_billions'),
            "btc_dominance": metrics.get('btc_dominance'),
            "total3_cap_billions": metrics.get('total3_cap_billions'),
            "eth_btc_ratio": metrics.get('eth_btc_ratio'),
            "total_market_cap_billions": metrics.get('total_market_cap_billions')
        })

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
        price_change_7d = self._compute_pct_change(
            "futures",
            "price",
            7,
            binance_data.get('price') if binance_data else None
        )

        ma50 = self._compute_ma("futures", "price", 50)
        price_vs_ma = None
        if ma50 and binance_data and binance_data.get('price') is not None and ma50 != 0:
            price_vs_ma = round((binance_data['price'] - ma50) / ma50 * 100, 2)

        full_crypto_context = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "layer2_flows": {
                "stablecoin_mcap_b": structure_data.get('stablecoin_total_cap_billions'),
                "etf_net_inflow_m": etf_data.get('etf_net_inflow_total'),
                "etf_ibit_flow_m": etf_data.get('etf_ibit_flow'),
                "etf_weekly_avg_flow_m": etf_data.get('etf_weekly_avg_flow_m'),
                "etf_weekly_data_points": etf_data.get('etf_weekly_data_points'),
                "etf_date": etf_data.get('etf_date'),
                "etf_status": etf_data.get('status')
            },
            "layer3_structure": {
                "btc_dominance": structure_data.get('btc_dominance'),
                "eth_dominance": structure_data.get('eth_dominance'),
                "eth_btc_ratio": structure_data.get('eth_btc_ratio'),
                "total3_cap_b": structure_data.get('total3_cap_billions'),
                "total_market_cap_b": structure_data.get('total_market_cap_billions'),
                "btc_dom_trend_90d": structure_data.get('btc_dom_trend_90d'),
                "total3_structure_status": structure_data.get('total3_structure_status'),
                "total3_ma50_b": structure_data.get('total3_ma50_b'),
                "stablecoin_growth_30d_pct": structure_data.get('stablecoin_growth_30d_pct')
            },
            "layer4_sentiment": {
                "price_btc": binance_data.get('price') if binance_data else None,
                "price_change_24h_pct": binance_data.get('price_change_24h_pct') if binance_data else None,
                "price_change_7d_pct": price_change_7d,
                "price_vs_50d_ma_pct": price_vs_ma,
                "funding_rate": binance_data.get('funding_rate') if binance_data else None,
                "funding_rate_annualized_pct": round(binance_data.get('funding_yearly_pct', 0), 2) if binance_data else None,
                "open_interest_usd_b": round(binance_data.get('open_interest_usd', 0) / 1e9, 2) if binance_data else None,
                "open_interest_btc": binance_data.get('open_interest_btc') if binance_data else None,
                "long_short_ratio": binance_data.get('long_short_ratio') if binance_data else None,
                "price_source": "cache" if binance_data and binance_data.get('from_cache') else "live",
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

