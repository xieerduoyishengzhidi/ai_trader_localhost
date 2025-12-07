"""
Macro Service - 宏观经济数据服务
集成 FRED API、yfinance 和 DeFi Llama 提供宏观经济数据
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field
from fredapi import Fred
import yfinance as yf
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入币圈数据抓取模块（在logger定义之后）
CRYPTO_FETCHER_AVAILABLE = False
try:
    from crypto_fetcher import CryptoDataLoader
    CRYPTO_FETCHER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️  crypto_fetcher 模块未导入，币圈数据功能不可用: {e}")

app = Flask(__name__)

# FRED API 配置
FRED_API_KEY = os.getenv("FRED_API_KEY", "bd89c0475f61d7555dee50daed12185f")
fred = None
if FRED_API_KEY:
    try:
        fred = Fred(api_key=FRED_API_KEY)
        logger.info("✅ FRED API 客户端初始化成功")
    except Exception as e:
        logger.error(f"❌ 初始化 FRED API 客户端失败: {e}")
else:
    logger.warning("⚠️  FRED_API_KEY 未设置，FRED 功能可能无法正常工作")

# DeFi Llama API 配置
DEFILLAMA_API_BASE = "https://api.llama.fi"

# 初始化币圈数据加载器
crypto_loader = None
if CRYPTO_FETCHER_AVAILABLE:
    try:
        # 从环境变量读取 Binance API Key（可选）
        binance_api_key = os.getenv("BINANCE_API_KEY")
        binance_secret = os.getenv("BINANCE_SECRET")
        crypto_loader = CryptoDataLoader(api_key=binance_api_key, secret=binance_secret)
        logger.info("✅ CryptoDataLoader 初始化成功")
    except Exception as e:
        logger.error(f"❌ CryptoDataLoader 初始化失败: {e}")
        crypto_loader = None

# 常用FRED数据系列ID
COMMON_SERIES = {
    "GDP": "GDP",  # 国内生产总值
    "UNRATE": "UNRATE",  # 失业率
    "CPIAUCSL": "CPIAUCSL",  # 消费者物价指数
    "FEDFUNDS": "FEDFUNDS",  # 联邦基金利率
    "DGS10": "DGS10",  # 10年期国债收益率
    "DGS2": "DGS2",  # 2年期国债收益率
    "DEXCHUS": "DEXCHUS",  # 人民币/美元汇率
    "DEXUSEU": "DEXUSEU",  # 欧元/美元汇率
    "DEXJPUS": "DEXJPUS",  # 日元/美元汇率
    "GOLDAMGBD228NLBM": "GOLDAMGBD228NLBM",  # 黄金价格
    "DCOILWTICO": "DCOILWTICO",  # 原油价格（WTI）
}


class FredDataRequest(BaseModel):
    """FRED数据请求"""
    series_id: str = Field(..., description="FRED数据系列ID")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    limit: Optional[int] = Field(None, description="返回数据点数量限制")


class YFinanceDataRequest(BaseModel):
    """YFinance数据请求"""
    symbol: str = Field(..., description="股票/ETF代码，如 SPY, QQQ, ^GSPC")
    period: Optional[str] = Field("1mo", description="数据周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max")
    interval: Optional[str] = Field("1d", description="数据间隔: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo")


class DeFiLlamaProtocolRequest(BaseModel):
    """DeFi Llama协议数据请求"""
    protocol: str = Field(..., description="协议名称，如 uniswap, aave, compound")


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "service": "macro-service",
        "fred_available": fred is not None,
        "yfinance_available": True,
        "defillama_available": True,
        "crypto_fetcher_available": CRYPTO_FETCHER_AVAILABLE and crypto_loader is not None
    })


@app.route("/api/fred/series", methods=["POST"])
def get_fred_series():
    """
    获取FRED数据系列
    
    请求体:
    {
        "series_id": "GDP",
        "start_date": "2020-01-01",  # 可选
        "end_date": "2024-01-01",    # 可选
        "limit": 100                  # 可选
    }
    """
    try:
        if not fred:
            return jsonify({"error": "FRED API 未初始化，请检查 FRED_API_KEY"}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        series_id = data.get("series_id", "")
        if not series_id:
            return jsonify({"error": "series_id 是必需的"}), 400
        
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        limit = data.get("limit")
        
        logger.info(f"📡 获取FRED数据: {series_id}")
        
        # 获取数据
        try:
            df = fred.get_series(
                series_id=series_id,
                start=start_date,
                end=end_date,
                limit=limit
            )
            
            if df is None or df.empty:
                return jsonify({
                    "series_id": series_id,
                    "data": [],
                    "message": "未找到数据"
                }), 404
            
            # 转换为JSON格式
            data_points = []
            for date, value in df.items():
                data_points.append({
                    "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "value": float(value) if value is not None else None
                })
            
            # 获取系列信息
            try:
                info = fred.get_series_info(series_id)
                series_info = {
                    "title": info.get("title", ""),
                    "units": info.get("units", ""),
                    "frequency": info.get("frequency", ""),
                    "seasonal_adjustment": info.get("seasonal_adjustment", ""),
                    "last_updated": info.get("last_updated", ""),
                }
            except Exception as e:
                logger.warning(f"无法获取系列信息: {e}")
                series_info = {}
            
            return jsonify({
                "series_id": series_id,
                "series_info": series_info,
                "data": data_points,
                "count": len(data_points)
            })
            
        except Exception as e:
            logger.error(f"❌ 获取FRED数据失败: {e}", exc_info=True)
            return jsonify({"error": f"获取数据失败: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/fred/common", methods=["GET"])
def get_common_series():
    """
    获取常用宏观经济指标列表
    """
    return jsonify({
        "common_series": COMMON_SERIES,
        "description": {
            "GDP": "国内生产总值",
            "UNRATE": "失业率",
            "CPIAUCSL": "消费者物价指数",
            "FEDFUNDS": "联邦基金利率",
            "DGS10": "10年期国债收益率",
            "DGS2": "2年期国债收益率",
            "DEXCHUS": "人民币/美元汇率",
            "DEXUSEU": "欧元/美元汇率",
            "DEXJPUS": "日元/美元汇率",
            "GOLDAMGBD228NLBM": "黄金价格",
            "DCOILWTICO": "原油价格（WTI）"
        }
    })


@app.route("/api/yfinance/quote", methods=["POST"])
def get_yfinance_quote():
    """
    获取YFinance股票/ETF报价数据
    
    请求体:
    {
        "symbol": "SPY",
        "period": "1mo",  # 可选
        "interval": "1d"  # 可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        symbol = data.get("symbol", "")
        if not symbol:
            return jsonify({"error": "symbol 是必需的"}), 400
        
        period = data.get("period", "1mo")
        interval = data.get("interval", "1d")
        
        logger.info(f"📡 获取YFinance数据: {symbol}, period={period}, interval={interval}")
        
        try:
            ticker = yf.Ticker(symbol)
            
            # 获取历史数据
            hist = ticker.history(period=period, interval=interval)
            
            if hist is None or hist.empty:
                return jsonify({
                    "symbol": symbol,
                    "data": [],
                    "message": "未找到数据"
                }), 404
            
            # 转换为JSON格式
            data_points = []
            for date, row in hist.iterrows():
                data_points.append({
                    "date": date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(date, 'strftime') else str(date),
                    "open": float(row["Open"]) if row["Open"] is not None else None,
                    "high": float(row["High"]) if row["High"] is not None else None,
                    "low": float(row["Low"]) if row["Low"] is not None else None,
                    "close": float(row["Close"]) if row["Close"] is not None else None,
                    "volume": int(row["Volume"]) if row["Volume"] is not None else None,
                })
            
            # 获取基本信息
            try:
                info = ticker.info
                symbol_info = {
                    "symbol": info.get("symbol", symbol),
                    "longName": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "marketCap": info.get("marketCap"),
                    "currentPrice": info.get("currentPrice"),
                    "currency": info.get("currency", ""),
                }
            except Exception as e:
                logger.warning(f"无法获取股票信息: {e}")
                symbol_info = {}
            
            return jsonify({
                "symbol": symbol,
                "symbol_info": symbol_info,
                "data": data_points,
                "count": len(data_points)
            })
            
        except Exception as e:
            logger.error(f"❌ 获取YFinance数据失败: {e}", exc_info=True)
            return jsonify({"error": f"获取数据失败: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/yfinance/multi", methods=["POST"])
def get_yfinance_multi():
    """
    批量获取多个股票/ETF数据
    
    请求体:
    {
        "symbols": ["SPY", "QQQ", "^GSPC"],
        "period": "1mo",
        "interval": "1d"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        symbols = data.get("symbols", [])
        if not symbols or not isinstance(symbols, list):
            return jsonify({"error": "symbols 必须是包含至少一个符号的数组"}), 400
        
        period = data.get("period", "1mo")
        interval = data.get("interval", "1d")
        
        logger.info(f"📡 批量获取YFinance数据: {symbols}")
        
        try:
            # 使用yfinance的download函数批量获取
            df = yf.download(symbols, period=period, interval=interval, group_by='ticker')
            
            if df is None or df.empty:
                return jsonify({
                    "symbols": symbols,
                    "data": {},
                    "message": "未找到数据"
                }), 404
            
            result = {}
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_df = df
                    else:
                        symbol_df = df[symbol]
                    
                    data_points = []
                    for date, row in symbol_df.iterrows():
                        data_points.append({
                            "date": date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(date, 'strftime') else str(date),
                            "open": float(row["Open"]) if row["Open"] is not None else None,
                            "high": float(row["High"]) if row["High"] is not None else None,
                            "low": float(row["Low"]) if row["Low"] is not None else None,
                            "close": float(row["Close"]) if row["Close"] is not None else None,
                            "volume": int(row["Volume"]) if row["Volume"] is not None else None,
                        })
                    
                    result[symbol] = {
                        "data": data_points,
                        "count": len(data_points)
                    }
                except Exception as e:
                    logger.warning(f"处理 {symbol} 时出错: {e}")
                    result[symbol] = {"error": str(e)}
            
            return jsonify({
                "symbols": symbols,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"❌ 批量获取YFinance数据失败: {e}", exc_info=True)
            return jsonify({"error": f"获取数据失败: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


# ==================== DeFi Llama API ====================

@app.route("/api/defillama/tvl", methods=["GET"])
def get_defillama_tvl():
    """
    获取DeFi总锁仓价值（TVL）
    
    查询参数:
    - chain: 可选，指定链名称（如 ethereum, bsc, polygon）
    """
    try:
        chain = request.args.get("chain")
        url = f"{DEFILLAMA_API_BASE}/tvl"
        if chain:
            url = f"{DEFILLAMA_API_BASE}/tvl/{chain}"
        
        logger.info(f"📡 获取DeFi Llama TVL数据: {chain or '全部'}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return jsonify({
            "chain": chain or "all",
            "tvl": data,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取DeFi Llama TVL失败: {e}", exc_info=True)
        return jsonify({"error": f"获取TVL数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/protocols", methods=["GET"])
def get_defillama_protocols():
    """
    获取所有DeFi协议列表
    """
    try:
        logger.info("📡 获取DeFi Llama协议列表")
        
        url = f"{DEFILLAMA_API_BASE}/protocols"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        protocols = response.json()
        
        return jsonify({
            "protocols": protocols,
            "count": len(protocols),
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取协议列表失败: {e}", exc_info=True)
        return jsonify({"error": f"获取协议列表失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/protocol/<protocol>", methods=["GET"])
def get_defillama_protocol(protocol):
    """
    获取特定协议的详细信息
    
    路径参数:
    - protocol: 协议名称（如 uniswap, aave, compound）
    """
    try:
        logger.info(f"📡 获取DeFi Llama协议数据: {protocol}")
        
        url = f"{DEFILLAMA_API_BASE}/protocol/{protocol}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return jsonify({
                "error": f"协议 '{protocol}' 未找到",
                "protocol": protocol
            }), 404
        
        response.raise_for_status()
        data = response.json()
        
        return jsonify({
            "protocol": protocol,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取协议数据失败: {e}", exc_info=True)
        return jsonify({"error": f"获取协议数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/protocol", methods=["POST"])
def get_defillama_protocol_post():
    """
    通过POST请求获取协议数据
    
    请求体:
    {
        "protocol": "uniswap"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        protocol = data.get("protocol", "")
        if not protocol:
            return jsonify({"error": "protocol 是必需的"}), 400
        
        logger.info(f"📡 获取DeFi Llama协议数据: {protocol}")
        
        url = f"{DEFILLAMA_API_BASE}/protocol/{protocol}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return jsonify({
                "error": f"协议 '{protocol}' 未找到",
                "protocol": protocol
            }), 404
        
        response.raise_for_status()
        protocol_data = response.json()
        
        return jsonify({
            "protocol": protocol,
            "data": protocol_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取协议数据失败: {e}", exc_info=True)
        return jsonify({"error": f"获取协议数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/chains", methods=["GET"])
def get_defillama_chains():
    """
    获取所有链的TVL数据
    """
    try:
        logger.info("📡 获取DeFi Llama链数据")
        
        url = f"{DEFILLAMA_API_BASE}/chains"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        chains = response.json()
        
        return jsonify({
            "chains": chains,
            "count": len(chains),
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取链数据失败: {e}", exc_info=True)
        return jsonify({"error": f"获取链数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/tokens", methods=["GET"])
def get_defillama_tokens():
    """
    获取代币价格数据
    
    查询参数:
    - tokens: 可选，代币地址列表（逗号分隔），格式: chain:address
    """
    try:
        tokens = request.args.get("tokens")
        
        if tokens:
            url = f"{DEFILLAMA_API_BASE}/prices/current/{tokens}"
            logger.info(f"📡 获取DeFi Llama代币价格: {tokens}")
        else:
            url = f"{DEFILLAMA_API_BASE}/tokens"
            logger.info("📡 获取DeFi Llama代币列表")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return jsonify({
            "tokens": tokens if tokens else "all",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取代币数据失败: {e}", exc_info=True)
        return jsonify({"error": f"获取代币数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/defillama/historical", methods=["POST"])
def get_defillama_historical():
    """
    获取历史TVL数据
    
    请求体:
    {
        "protocol": "uniswap",  # 或 "chain": "ethereum"
        "start": 1609459200,    # Unix时间戳（可选）
        "end": 1640995200       # Unix时间戳（可选）
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        protocol = data.get("protocol")
        chain = data.get("chain")
        start = data.get("start")
        end = data.get("end")
        
        if not protocol and not chain:
            return jsonify({"error": "protocol 或 chain 至少需要一个"}), 400
        
        if protocol:
            url = f"{DEFILLAMA_API_BASE}/protocol/{protocol}"
            logger.info(f"📡 获取协议历史数据: {protocol}")
        else:
            url = f"{DEFILLAMA_API_BASE}/v2/historicalChainTvl/{chain}"
            logger.info(f"📡 获取链历史数据: {chain}")
        
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return jsonify({
                "error": f"{'协议' if protocol else '链'} '{protocol or chain}' 未找到"
            }), 404
        
        response.raise_for_status()
        historical_data = response.json()
        
        return jsonify({
            "protocol": protocol,
            "chain": chain,
            "data": historical_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 获取历史数据失败: {e}", exc_info=True)
        return jsonify({"error": f"获取历史数据失败: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


# ==================== Crypto Data API (币圈原生数据) ====================

@app.route("/api/crypto/futures", methods=["POST"])
def get_crypto_futures():
    """
    获取币圈期货数据（第四层级：情绪与博弈）
    
    请求体:
    {
        "symbol": "BTC/USDT"  # 可选，默认 BTC/USDT
    }
    """
    try:
        if not crypto_loader:
            return jsonify({"error": "CryptoDataLoader 未初始化"}), 500
        
        data = request.get_json() or {}
        symbol = data.get("symbol", "BTC/USDT")
        
        logger.info(f"📡 获取币圈期货数据: {symbol}")
        
        result = crypto_loader.get_binance_futures_data(symbol)
        
        if result is None:
            return jsonify({"error": "获取数据失败"}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/crypto/etf", methods=["GET"])
def get_crypto_etf():
    """
    获取BTC ETF资金流向数据（第二层级：机构资金）
    """
    try:
        if not crypto_loader:
            return jsonify({"error": "CryptoDataLoader 未初始化"}), 500
        
        logger.info("📡 获取BTC ETF资金流向数据")
        
        result = crypto_loader.get_etf_flows()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/crypto/market-structure", methods=["GET"])
def get_crypto_market_structure():
    """
    获取市场结构与流动性数据
    包含：稳定币市值、BTC Dominance、TOTAL3、ETH/BTC Ratio、恐惧贪婪指数
    """
    try:
        if not crypto_loader:
            return jsonify({"error": "CryptoDataLoader 未初始化"}), 500
        
        logger.info("📡 获取市场结构与流动性数据")
        
        result = crypto_loader.get_market_structure_and_liquidity()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


@app.route("/api/crypto/all", methods=["POST"])
def get_all_crypto_data():
    """
    获取所有币圈原生数据（完整 Pentosh1 数据面板）
    
    请求体:
    {
        "symbol": "BTC/USDT"  # 可选，默认 BTC/USDT
    }
    """
    try:
        if not crypto_loader:
            return jsonify({"error": "CryptoDataLoader 未初始化"}), 500
        
        data = request.get_json() or {}
        symbol = data.get("symbol", "BTC/USDT")
        
        logger.info(f"📡 获取完整币圈数据: {symbol}")
        
        result = crypto_loader.get_all_crypto_data(symbol)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    logger.info(f"🚀 Macro Service 启动在端口 {port}")
    logger.info(f"   FRED API Key: {'已设置' if FRED_API_KEY else '未设置'}")
    logger.info(f"   DeFi Llama API: {DEFILLAMA_API_BASE}")
    logger.info(f"   Crypto Fetcher: {'已启用' if CRYPTO_FETCHER_AVAILABLE and crypto_loader else '未启用'}")
    app.run(host="0.0.0.0", port=port, debug=False)

