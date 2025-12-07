"""
Trading Brain - Pentosh1 数据合成主控制器
作为"大脑"调用 macro_service (localhost:8001) 的API
将零散数据拼装成 Pentosh1 需要的四层逻辑数据包
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Macro Service API 配置
MACRO_SERVICE_URL = os.getenv("MACRO_SERVICE_URL", "http://localhost:8001")


class Pentosh1DataAggregator:
    """Pentosh1 数据聚合器"""
    
    def __init__(self, macro_service_url: str = MACRO_SERVICE_URL):
        self.macro_service_url = macro_service_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def _call_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """调用 Macro Service API"""
        url = f"{self.macro_service_url}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API调用失败 {endpoint}: {e}")
            return None
    
    # ==================== 第一层级：全球宏观"水源" ====================
    
    def get_layer1_global_liquidity(self) -> Dict[str, Any]:
        """
        获取第一层级：全球宏观"水源"数据
        修正了单位换算和缩放问题
        """
        logger.info("📡 获取第一层级：全球宏观水源数据...")
        
        layer1 = {
            "timestamp": datetime.now().isoformat(),
            "indicators": {}
        }
        
        # 1. Fed Net Liquidity (WALCL - TGA - RRP)
        try:
            # 定义查询参数
            params = {
                "start_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"), # 稍微拉长周期确保拿到周更数据
                "end_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            walcl_data = self._call_api("/api/fred/series", "POST", {**params, "series_id": "WALCL"})
            tga_data = self._call_api("/api/fred/series", "POST", {**params, "series_id": "WTREGEN"})
            rrp_data = self._call_api("/api/fred/series", "POST", {**params, "series_id": "RRPONTSYD"})
            
            if walcl_data and tga_data and rrp_data:
                # 获取最新值 (注意：WALCL/TGA是Millions, RRP是Billions)
                walcl_latest = walcl_data.get("data", [])[-1].get("value") if walcl_data.get("data") else None
                tga_latest = tga_data.get("data", [])[-1].get("value") if tga_data.get("data") else None
                rrp_latest = rrp_data.get("data", [])[-1].get("value") if rrp_data.get("data") else None
                
                if all(v is not None for v in [walcl_latest, tga_latest, rrp_latest]):
                    # 修正：RRP (Billions) -> Millions，统一单位计算
                    rrp_in_millions = rrp_latest * 1000 
                    net_liquidity = walcl_latest - tga_latest - rrp_in_millions
                    
                    # 转换为 Billions 以便阅读
                    net_liquidity_b = net_liquidity / 1000
                    
                    layer1["indicators"]["fed_net_liquidity"] = {
                        "value_billions": net_liquidity_b,
                        "raw_components": {
                            "walcl_m": walcl_latest,
                            "tga_m": tga_latest,
                            "rrp_b": rrp_latest
                        },
                        # 简单的趋势判断：如果净流动性 > 6000B (6T) 视为相对充裕，或者对比30天前（此处简化为绝对值判断）
                        # 更严谨的逻辑是对比30天前的数据计算 delta
                        "signal": "bullish" if net_liquidity_b > 6000 else "neutral", 
                        "description": "美联储净流动性(Assets-TGA-RRP)，单位修正后"
                    }
        except Exception as e:
            logger.warning(f"获取Fed Net Liquidity失败: {e}")
        
        # 2. DXY (美元指数) - 逻辑无误
        try:
            dxy_data = self._call_api("/api/yfinance/quote", "POST", {
                "symbol": "DX-Y.NYB",
                "period": "3mo",
                "interval": "1d"
            })
            if dxy_data and dxy_data.get("data"):
                latest = dxy_data["data"][-1]
                close_value = latest.get("close")
                if close_value is not None:
                    layer1["indicators"]["dxy"] = {
                        "value": close_value,
                        "signal": "bearish" if close_value < 103 else "neutral", # 103以下利好风险资产
                        "description": "美元指数，下跌利好风险资产"
                    }
        except Exception as e:
            logger.warning(f"获取DXY失败: {e}")
        
        # 3. US10Y (10年美债) - 修正缩放问题
        try:
            us10y_data = self._call_api("/api/yfinance/quote", "POST", {
                "symbol": "^TNX",
                "period": "3mo",
                "interval": "1d"
            })
            if us10y_data and us10y_data.get("data"):
                latest = us10y_data["data"][-1]
                raw_value = latest.get("close")
                if raw_value is not None:
                    # 修正：Yahoo ^TNX 返回的是 42.5 代表 4.25%，需要除以 10
                    real_yield = raw_value / 10 if raw_value > 10 else raw_value
                    
                    layer1["indicators"]["us10y"] = {
                        "value": real_yield,
                        "signal": "bullish" if real_yield < 4.0 else "neutral", # 调整阈值适应当前市场
                        "description": "10年美债收益率，修正缩放后"
                    }
        except Exception as e:
            logger.warning(f"获取US10Y失败: {e}")
        
        # 4. US02Y (2年美债)
        try:
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            us2y_data = self._call_api("/api/fred/series", "POST", {
                "series_id": "DGS2",
                "start_date": start_date,
                "end_date": end_date
            })
            if us2y_data and us2y_data.get("data") and len(us2y_data["data"]) > 0:
                latest = us2y_data["data"][-1]
                value = latest.get("value")
                if value is not None:
                    layer1["indicators"]["us02y"] = {
                        "value": value,
                        "signal": "bullish" if value < 4.0 else "neutral",
                        "description": "2年美债收益率，暴跌预示降息预期"
                    }
        except Exception as e:
            logger.warning(f"获取US02Y失败: {e}")
        
        # 5. Yield Curve (10Y-2Y) - 建议微调阈值
        try:
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            yield_curve_data = self._call_api("/api/fred/series", "POST", {
                "series_id": "T10Y2Y",
                "start_date": start_date,
                "end_date": end_date
            })
            if yield_curve_data and yield_curve_data.get("data"):
                latest = yield_curve_data["data"][-1]
                curve_value = latest.get("value")
                if curve_value is not None:
                    # 修正逻辑：解除倒挂(接近0或正值)才是衰退信号
                    layer1["indicators"]["yield_curve"] = {
                        "value": curve_value,
                        "signal": "danger" if curve_value > -0.1 else "neutral",
                        "description": "10Y-2Y利差，解除倒挂(回到0以上)通常预示衰退"
                    }
        except Exception as e:
            logger.warning(f"获取Yield Curve失败: {e}")
        
        # 6. SPX/NDX Correlation
        try:
            spx_data = self._call_api("/api/yfinance/quote", "POST", {
                "symbol": "^GSPC",
                "period": "3mo",
                "interval": "1d"
            })
            ndx_data = self._call_api("/api/yfinance/quote", "POST", {
                "symbol": "^NDX",
                "period": "3mo",
                "interval": "1d"
            })
            if spx_data and spx_data.get("data") and len(spx_data["data"]) > 0:
                spx_latest = spx_data["data"][-1].get("close")
            else:
                spx_latest = None
            if ndx_data and ndx_data.get("data") and len(ndx_data["data"]) > 0:
                ndx_latest = ndx_data["data"][-1].get("close")
            else:
                ndx_latest = None
            if spx_latest is not None and ndx_latest is not None:
                layer1["indicators"]["spx_ndx"] = {
                    "spx": spx_latest,
                    "ndx": ndx_latest,
                    "signal": "follow_stocks",
                    "description": "币圈通常跟随纳指，纳指新高而BTC不动是背离信号"
                }
        except Exception as e:
            logger.warning(f"获取SPX/NDX失败: {e}")
        
        # 7. CNY Liquidity
        try:
            cny_data = self._call_api("/api/yfinance/quote", "POST", {
                "symbol": "CNH=X",
                "period": "3mo",
                "interval": "1d"
            })
            if cny_data and cny_data.get("data") and len(cny_data["data"]) > 0:
                latest = cny_data["data"][-1]
                close_value = latest.get("close")
                if close_value is not None:
                    layer1["indicators"]["cny_liquidity"] = {
                        "value": close_value,
                        "signal": "bullish" if close_value > 7.2 else "neutral",
                        "description": "人民币汇率，贬值/注入流动性常对应BTC上涨"
                    }
        except Exception as e:
            logger.warning(f"获取CNY Liquidity失败: {e}")
        
        # 计算第一层级综合评分
        layer1["macro_score"] = self._calculate_macro_score(layer1["indicators"])
        
        return layer1
    
    def _calculate_macro_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """计算宏观综合评分"""
        score = 50  # 中性起点
        signals = []
        
        # Fed Net Liquidity
        if "fed_net_liquidity" in indicators:
            if indicators["fed_net_liquidity"]["signal"] == "bullish":
                score += 15
                signals.append("净流动性上升")
            else:
                score -= 10
                signals.append("净流动性下降")
        
        # DXY
        if "dxy" in indicators:
            if indicators["dxy"]["signal"] == "bearish":
                score += 10
                signals.append("美元指数下跌")
            else:
                score -= 5
        
        # US10Y
        if "us10y" in indicators:
            if indicators["us10y"]["signal"] == "bullish":
                score += 10
                signals.append("10年美债收益率下降")
        
        # Yield Curve
        if "yield_curve" in indicators:
            if indicators["yield_curve"]["signal"] == "danger":
                score -= 20
                signals.append("⚠️ 收益率曲线回正，极度危险")
        
        # CNY
        if "cny_liquidity" in indicators:
            if indicators["cny_liquidity"]["signal"] == "bullish":
                score += 5
                signals.append("人民币流动性注入")
        
        # 限制在 0-100
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "level": "bullish" if score > 60 else "bearish" if score < 40 else "neutral",
            "signals": signals
        }
    
    # ==================== 第二、三、四层级：币圈数据 ====================
    
    def get_layer2_4_crypto_data(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        获取第二、三、四层级币圈数据
        通过调用 /api/crypto/all 一次性获取
        """
        logger.info(f"📡 获取第二、三、四层级币圈数据 ({symbol})...")
        
        crypto_data = self._call_api("/api/crypto/all", "POST", {"symbol": symbol})
        
        if not crypto_data:
            logger.warning("⚠️ 无法获取币圈数据，返回空结构")
            return {
                "layer2_flows": {},
                "layer3_structure": {},
                "layer4_sentiment": {}
            }
        
        return {
            "layer2_flows": crypto_data.get("layer2_flows", {}),
            "layer3_structure": crypto_data.get("layer3_structure", {}),
            "layer4_sentiment": crypto_data.get("layer4_sentiment", {})
        }
    
    # ==================== 数据合成 ====================
    
    def aggregate_all_data(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        聚合所有数据，生成完整的 Pentosh1 数据包
        """
        logger.info("🚀 开始聚合 Pentosh1 数据包...")
        
        # 获取各层级数据
        layer1 = self.get_layer1_global_liquidity()
        layer2_4 = self.get_layer2_4_crypto_data(symbol)
        
        # 合成完整数据包
        full_package = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": symbol,
            "layer1_global_liquidity": layer1,
            "layer2_crypto_flows": {
                "stablecoin_mcap_b": layer2_4["layer2_flows"].get("stablecoin_mcap_b"),
                "etf_net_inflow_m": layer2_4["layer2_flows"].get("etf_net_inflow_m"),
                "etf_ibit_flow_m": layer2_4["layer2_flows"].get("etf_ibit_flow_m"),
                "etf_date": layer2_4["layer2_flows"].get("etf_date")
            },
            "layer3_market_structure": {
                "btc_dominance": layer2_4["layer3_structure"].get("btc_dominance"),
                "eth_btc_ratio": layer2_4["layer3_structure"].get("eth_btc_ratio"),
                "total3_cap_b": layer2_4["layer3_structure"].get("total3_cap_b")
            },
            "layer4_sentiment": {
                "price_btc": layer2_4["layer4_sentiment"].get("price_btc"),
                "funding_rate_annualized_pct": layer2_4["layer4_sentiment"].get("funding_rate_annualized_pct"),
                "open_interest_usd_b": layer2_4["layer4_sentiment"].get("open_interest_usd_b"),
                "long_short_ratio": layer2_4["layer4_sentiment"].get("long_short_ratio"),
                "fear_greed_index": layer2_4["layer4_sentiment"].get("fear_greed_index")
            },
            "pentosh1_signals": self._generate_pentosh1_signals(layer1, layer2_4)
        }
        
        return full_package
    
    def _generate_pentosh1_signals(self, layer1: Dict, layer2_4: Dict) -> Dict[str, Any]:
        """生成 Pentosh1 交易信号"""
        signals = {
            "macro_trend": "neutral",
            "crypto_momentum": "neutral",
            "market_structure": "neutral",
            "sentiment": "neutral",
            "overall_bias": "wait",
            "risk_level": "medium"
        }
        
        # 宏观趋势判断
        macro_score = layer1.get("macro_score", {}).get("score", 50)
        if macro_score > 60:
            signals["macro_trend"] = "bullish"
        elif macro_score < 40:
            signals["macro_trend"] = "bearish"
        
        # 币圈动能判断（第二层级）
        etf_inflow = layer2_4.get("layer2_flows", {}).get("etf_net_inflow_m")
        if etf_inflow is not None:
            if etf_inflow > 200:
                signals["crypto_momentum"] = "strong_bullish"
            elif etf_inflow > 0:
                signals["crypto_momentum"] = "bullish"
            elif etf_inflow < -100:
                signals["crypto_momentum"] = "bearish"
        
        # 市场结构判断（第三层级）
        btc_d = layer2_4.get("layer3_structure", {}).get("btc_dominance")
        if btc_d is not None:
            if btc_d > 55:
                signals["market_structure"] = "btc_dominant"
            elif btc_d < 50:
                signals["market_structure"] = "alt_season"
        
        # 情绪判断（第四层级）
        funding_rate = layer2_4.get("layer4_sentiment", {}).get("funding_rate_annualized_pct")
        fear_greed = layer2_4.get("layer4_sentiment", {}).get("fear_greed_index")
        
        # 处理 None 值
        if funding_rate is not None:
            if funding_rate > 10:
                signals["sentiment"] = "overheated"
                signals["risk_level"] = "high"
            elif funding_rate < -5:
                signals["sentiment"] = "oversold"
        
        if fear_greed is not None:
            if fear_greed > 85:
                signals["sentiment"] = "extreme_greed"
                signals["risk_level"] = "high"
            elif fear_greed < 20:
                signals["sentiment"] = "extreme_fear"
        
        # 综合判断
        bullish_count = sum([
            signals["macro_trend"] == "bullish",
            signals["crypto_momentum"] in ["bullish", "strong_bullish"],
            signals["sentiment"] not in ["overheated", "extreme_greed"]
        ])
        
        bearish_count = sum([
            signals["macro_trend"] == "bearish",
            signals["crypto_momentum"] == "bearish",
            signals["sentiment"] in ["overheated", "extreme_greed"]
        ])
        
        if bullish_count >= 2:
            signals["overall_bias"] = "long"
        elif bearish_count >= 2:
            signals["overall_bias"] = "short"
        else:
            signals["overall_bias"] = "wait"
        
        return signals
    
    # ==================== 输出 ====================
    
    def save_daily_context(self, data: Dict[str, Any], output_dir: str = "output") -> str:
        """保存每日上下文数据到JSON文件"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"Daily_Context_{date_str}.json"
        filepath = output_path / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ 数据已保存到: {filepath}")
        return str(filepath)


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("🚀 Pentosh1 Trading Brain 启动")
    logger.info("=" * 80)
    
    # 检查 Macro Service 是否可用
    try:
        response = requests.get(f"{MACRO_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error(f"❌ Macro Service 不可用 (状态码: {response.status_code})")
            return
        logger.info("✅ Macro Service 连接正常")
    except Exception as e:
        logger.error(f"❌ 无法连接到 Macro Service: {e}")
        logger.error(f"   请确保 macro_service 正在运行在 {MACRO_SERVICE_URL}")
        return
    
    # 创建聚合器
    aggregator = Pentosh1DataAggregator()
    
    # 聚合所有数据
    full_data = aggregator.aggregate_all_data("BTC/USDT")
    
    # 保存数据
    output_file = aggregator.save_daily_context(full_data)
    
    # 打印摘要
    logger.info("\n" + "=" * 80)
    logger.info("📊 Pentosh1 数据包摘要")
    logger.info("=" * 80)
    logger.info(f"日期: {full_data['date']}")
    logger.info(f"宏观评分: {full_data['layer1_global_liquidity']['macro_score']['score']}/100 ({full_data['layer1_global_liquidity']['macro_score']['level']})")
    logger.info(f"交易信号: {full_data['pentosh1_signals']['overall_bias']}")
    logger.info(f"风险等级: {full_data['pentosh1_signals']['risk_level']}")
    logger.info(f"BTC价格: ${full_data['layer4_sentiment'].get('price_btc', 'N/A')}")
    logger.info(f"资金费率: {full_data['layer4_sentiment'].get('funding_rate_annualized_pct', 'N/A')}%")
    logger.info(f"恐惧贪婪指数: {full_data['layer4_sentiment'].get('fear_greed_index', 'N/A')}")
    logger.info(f"BTC Dominance: {full_data['layer3_market_structure'].get('btc_dominance', 'N/A')}%")
    logger.info(f"ETF净流入: ${full_data['layer2_crypto_flows'].get('etf_net_inflow_m', 'N/A')}M")
    logger.info("=" * 80)
    logger.info(f"📁 完整数据已保存到: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

