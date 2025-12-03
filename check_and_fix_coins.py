#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查默认币池中的币种是否存在，对于不存在的币种尝试添加1000前缀
保留所有可得的币种并更新config.json
"""

import json
import requests
import time
import sys
import io
from typing import List, Dict, Tuple

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 币安合约API基础URL
BINANCE_FUTURES_API = "https://fapi.binance.com"

def get_all_binance_symbols() -> Dict[str, bool]:
    """
    获取币安合约所有可用的交易对
    返回: {symbol: True} 字典
    """
    print("正在获取币安合约所有交易对...")
    url = f"{BINANCE_FUTURES_API}/fapi/v1/exchangeInfo"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        symbols = {}
        for symbol_info in data.get("symbols", []):
            symbol = symbol_info.get("symbol", "")
            status = symbol_info.get("status", "")
            contract_type = symbol_info.get("contractType", "")
            
            # 只保留永续合约且状态为TRADING的交易对
            if status == "TRADING" and contract_type == "PERPETUAL":
                symbols[symbol] = True
        
        print(f"[OK] 成功获取 {len(symbols)} 个可用交易对")
        return symbols
    except Exception as e:
        print(f"[ERROR] 获取交易对失败: {e}")
        return {}

def check_symbol_exists(symbol: str, available_symbols: Dict[str, bool]) -> bool:
    """
    检查币种是否存在
    """
    return symbol in available_symbols

def try_with_1000_prefix(symbol: str, available_symbols: Dict[str, bool]) -> Tuple[bool, str]:
    """
    尝试在币种前面加1000前缀
    例如: HYPEUSDT -> 1000HYPEUSDT
    
    返回: (是否找到, 找到的symbol)
    """
    # 移除USDT后缀
    base = symbol.replace("USDT", "")
    # 添加1000前缀
    new_symbol = f"1000{base}USDT"
    
    if check_symbol_exists(new_symbol, available_symbols):
        return True, new_symbol
    return False, symbol

def process_coins(default_coins: List[str]) -> Tuple[List[str], List[Dict]]:
    """
    处理币种列表，检查存在性并尝试1000前缀
    
    返回: (有效的币种列表, 处理结果详情)
    """
    print("\n开始检查币种存在性...")
    
    # 获取所有可用交易对
    available_symbols = get_all_binance_symbols()
    if not available_symbols:
        print("[ERROR] 无法获取交易对列表，无法继续")
        return [], []
    
    valid_coins = []
    results = []
    
    for coin in default_coins:
        coin_upper = coin.upper()
        
        # 确保以USDT结尾
        if not coin_upper.endswith("USDT"):
            coin_upper = f"{coin_upper}USDT"
        
        # 检查原始币种是否存在
        if check_symbol_exists(coin_upper, available_symbols):
            valid_coins.append(coin_upper)
            results.append({
                "original": coin,
                "final": coin_upper,
                "status": "存在",
                "method": "原始"
            })
            print(f"[OK] {coin} -> {coin_upper} (存在)")
        else:
            # 尝试1000前缀
            found, new_symbol = try_with_1000_prefix(coin_upper, available_symbols)
            if found:
                valid_coins.append(new_symbol)
                results.append({
                    "original": coin,
                    "final": new_symbol,
                    "status": "存在",
                    "method": "1000前缀"
                })
                print(f"[OK] {coin} -> {new_symbol} (通过1000前缀找到)")
            else:
                results.append({
                    "original": coin,
                    "final": coin_upper,
                    "status": "不存在",
                    "method": "无"
                })
                print(f"[ERROR] {coin} -> {coin_upper} (不存在，1000前缀也无效)")
    
    return valid_coins, results

def update_config_json(valid_coins: List[str], config_path: str = "config.json"):
    """
    更新config.json文件
    """
    print(f"\n正在更新 {config_path}...")
    
    try:
        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 更新default_coins
        config["default_coins"] = valid_coins
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] 成功更新 {config_path}")
        print(f"  保留币种数量: {len(valid_coins)}")
    except Exception as e:
        print(f"[ERROR] 更新配置文件失败: {e}")

def print_summary(results: List[Dict], valid_coins: List[str]):
    """
    打印处理结果摘要
    """
    print("\n" + "="*60)
    print("处理结果摘要")
    print("="*60)
    
    total = len(results)
    exists_original = sum(1 for r in results if r["status"] == "存在" and r["method"] == "原始")
    exists_1000 = sum(1 for r in results if r["status"] == "存在" and r["method"] == "1000前缀")
    not_exists = sum(1 for r in results if r["status"] == "不存在")
    
    print(f"总币种数: {total}")
    print(f"[OK] 原始存在: {exists_original}")
    print(f"[OK] 1000前缀存在: {exists_1000}")
    print(f"[ERROR] 不存在: {not_exists}")
    print(f"[OK] 最终保留: {len(valid_coins)}")
    
    if not_exists > 0:
        print("\n不存在的币种:")
        for r in results:
            if r["status"] == "不存在":
                print(f"  - {r['original']}")
    
    if exists_1000 > 0:
        print("\n通过1000前缀找到的币种:")
        for r in results:
            if r["method"] == "1000前缀":
                print(f"  - {r['original']} -> {r['final']}")

def main():
    """
    主函数
    """
    print("="*60)
    print("币种存在性检查和修复工具")
    print("="*60)
    
    # 读取config.json
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] 读取config.json失败: {e}")
        return
    
    # 获取默认币池
    default_coins = config.get("default_coins", [])
    if not default_coins:
        print("[ERROR] config.json中没有找到default_coins配置")
        return
    
    print(f"\n默认币池包含 {len(default_coins)} 个币种:")
    for i, coin in enumerate(default_coins, 1):
        print(f"  {i}. {coin}")
    
    # 处理币种
    valid_coins, results = process_coins(default_coins)
    
    # 打印摘要
    print_summary(results, valid_coins)
    
    # 更新配置文件
    if valid_coins:
        update_config_json(valid_coins)
        print("\n[OK] 处理完成！")
    else:
        print("\n[WARNING] 没有找到任何有效的币种，配置文件未更新")

if __name__ == "__main__":
    main()

