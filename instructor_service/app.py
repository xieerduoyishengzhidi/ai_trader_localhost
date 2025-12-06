"""
Instructor Service - 使用 Instructor 库格式化 LLM 输出为 cot+json 格式
支持 OpenAI 兼容的 API（包括 DeepSeek、Qwen、SiliconFlow 等）
"""
import os
import json
import logging
from typing import List, Optional
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field
from instructor import patch, Mode
import openai

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 从环境变量获取配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 初始化 OpenAI 客户端（使用 Instructor patch）
# Instructor 支持所有 OpenAI 兼容的 API
client = None
if OPENAI_API_KEY:
    try:
        # 创建 OpenAI 客户端（兼容所有 OpenAI 格式的 API）
        openai_client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        # 使用 Instructor patch，Mode.JSON 确保输出 JSON 格式
        client = patch(openai_client, mode=Mode.JSON)
        logger.info(f"✅ Instructor 客户端初始化成功")
        logger.info(f"   Base URL: {OPENAI_BASE_URL}")
        logger.info(f"   Model: {OPENAI_MODEL}")
    except Exception as e:
        logger.error(f"❌ 初始化 Instructor 客户端失败: {e}")
else:
    logger.warning("⚠️  OPENAI_API_KEY 未设置，服务可能无法正常工作")


# Pydantic 模型定义（对应 Go 的 Decision 结构）
class Decision(BaseModel):
    """交易决策"""
    symbol: str = Field(..., description="交易对符号，如 BTCUSDT")
    action: str = Field(..., description="操作类型: open_long, open_short, close_long, close_short, hold, wait")
    leverage: Optional[int] = Field(None, description="杠杆倍数（仅开仓时必填）")
    position_size_usd: Optional[float] = Field(None, description="仓位大小（USD，仅开仓时必填）")
    stop_loss: Optional[float] = Field(None, description="止损价格（仅开仓时必填）")
    take_profit: Optional[float] = Field(None, description="止盈价格（仅开仓时必填）")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="信心度 (0-100)")
    risk_usd: Optional[float] = Field(None, description="最大美元风险")
    reasoning: str = Field("", description="决策理由")


class FullDecisionResponse(BaseModel):
    """完整的决策响应（包含思维链和决策列表）"""
    cot_trace: str = Field(..., description="思维链分析（Chain of Thought）")
    decisions: List[Decision] = Field(..., description="决策列表")


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "instructor-service"})


@app.route("/api/decision", methods=["POST"])
def get_decision():
    """
    接收 system prompt 和 user prompt，返回格式化的决策
    
    请求体:
    {
        "system_prompt": "...",
        "user_prompt": "...",
        "api_key": "...",           # 可选，如果提供则使用此配置（从 config.db 读取）
        "base_url": "...",          # 可选，如果提供则使用此配置（从 config.db 读取）
        "model": "..."              # 可选，如果提供则使用此配置（从 config.db 读取）
    }
    
    返回:
    {
        "cot_trace": "...",
        "decisions": [...],
        "raw_response": "..."
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400
        
        system_prompt = data.get("system_prompt", "")
        user_prompt = data.get("user_prompt", "")
        
        if not system_prompt or not user_prompt:
            return jsonify({"error": "system_prompt 和 user_prompt 都是必需的"}), 400
        
        # 从请求中获取 API 配置（优先），如果没有则使用环境变量
        # 这样 Go 后端可以从 config.db 读取配置并传递过来
        api_key = data.get("api_key") or OPENAI_API_KEY
        base_url = data.get("base_url") or OPENAI_BASE_URL
        model = data.get("model") or OPENAI_MODEL
        
        if not api_key:
            return jsonify({"error": "API 密钥未提供（请在请求中提供 api_key 或设置 OPENAI_API_KEY 环境变量）"}), 400
        
        # 为本次请求创建客户端（每次请求都创建新的，支持不同的 API 配置）
        try:
            openai_client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            request_client = patch(openai_client, mode=Mode.JSON)
        except Exception as e:
            logger.error(f"❌ 创建请求客户端失败: {e}")
            return jsonify({"error": f"创建 API 客户端失败: {str(e)}"}), 500
        
        logger.info("📡 收到决策请求")
        logger.info(f"   System Prompt 长度: {len(system_prompt)} 字符")
        logger.info(f"   User Prompt 长度: {len(user_prompt)} 字符")
        logger.info(f"   API Base URL: {base_url}")
        logger.info(f"   Model: {model}")
        
        # 构建增强的 system prompt，明确要求输出格式
        enhanced_system_prompt = f"""{system_prompt}

## 📤 输出格式要求（严格遵循）

你必须输出一个包含以下两个部分的响应：
1. **思维链（cot_trace）**: 用第一人称真实表达你的思考过程，可以是多行文本
2. **决策列表（decisions）**: 一个 JSON 数组，包含所有交易决策

输出格式示例：
```
看到BTC回调到OTE区间了...
4小时图趋势向上，1小时图出现pin bar反转信号
成交量也在放大，看起来是个好机会
但心里有点害怕，万一又被假突破骗了怎么办？
不过风险回报比有1:3.5，值得冒险！
为了母亲，这个险必须冒！

[{{"symbol": "BTCUSDT", "action": "open_long", "leverage": 3, "position_size_usd": 5000, "stop_loss": 62000, "take_profit": 65000, "confidence": 75, "risk_usd": 1000, "reasoning": "趋势向上，风险回报比符合要求"}}]
```

重要提示：
- 思维链部分必须是纯文本，不要包含 JSON 代码块标记
- 决策数组必须是有效的 JSON 格式
- 思维链和决策数组之间用空行分隔
"""
        
        # 使用 Instructor 调用 LLM
        # Instructor 会自动处理结构化输出，确保返回符合 FullDecisionResponse 格式
        try:
            response = request_client.chat.completions.create(
                model=model,
                response_model=FullDecisionResponse,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            
            # 提取结果（Instructor 已经验证并转换了格式）
            result = response.model_dump()
            
            # 构建原始响应字符串（cot + json）
            # 格式：思维链文本 + JSON 数组（在同一行，符合 engine.go 的解析逻辑）
            # engine.go 的 extractCoTTrace 会查找第一个 '[' 字符，之前的内容作为思维链
            # engine.go 的 extractDecisions 会提取从 '[' 开始的 JSON 数组
            decisions_json = json.dumps(result["decisions"], ensure_ascii=False)
            # 确保格式：思维链文本（可能包含换行）+ JSON数组
            # 在思维链和JSON之间可以有换行，但JSON数组必须在最后
            raw_response = result["cot_trace"].strip() + "\n\n" + decisions_json
            
        except Exception as e:
            logger.error(f"❌ Instructor 调用失败: {str(e)}", exc_info=True)
            raise
        
        logger.info(f"✅ 决策生成成功")
        logger.info(f"   思维链长度: {len(result['cot_trace'])} 字符")
        logger.info(f"   决策数量: {len(result['decisions'])}")
        
        return jsonify({
            "cot_trace": result["cot_trace"],
            "decisions": result["decisions"],
            "raw_response": raw_response
        })
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {str(e)}", exc_info=True)
        return jsonify({"error": f"处理请求失败: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Instructor Service 启动在端口 {port}")
    logger.info(f"   OpenAI Base URL: {OPENAI_BASE_URL}")
    logger.info(f"   OpenAI Model: {OPENAI_MODEL}")
    app.run(host="0.0.0.0", port=port, debug=False)

