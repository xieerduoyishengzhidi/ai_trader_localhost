' python fetch_tg_ai.py --chat nofx_dev_community --limit 2000'


import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests
from requests.exceptions import RequestException
from telethon import TelegramClient, errors
from telethon.tl.custom.message import Message

# === Static configuration (fill with your own credentials) ===
# 支持从环境变量读取，如果环境变量不存在则使用默认值
API_ID = int(os.getenv("TELEGRAM_API_ID", "38035966"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bb0b96c728301a2fb46655af27cd2fe4")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-7d9909d67ac74e60aa3f8a3283f95715")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # e.g. deepseek-chat / deepseek-coder / deepseek-r1
DEEPSEEK_REQUEST_TIMEOUT = (30, 600)  # seconds (connect timeout, read timeout)

# === Defaults ===
DEFAULT_PROMPT = (
    "你是一位资深技术分析助手。请从以下 Telegram 群组聊天内容中提取对项目优化最有价值的重要信息，"
    "避免无关闲聊。请按以下格式输出：\n"
    "- 总览：概述今天的关键变化、主要模块或分支、潜在收益与风险、优先处理事项。新版prompt，新方法增加收益率，新思路（比如说增加新的技术指标，或者新的交易策略）\n"
    "- 事件清单：逐条列出过去24小时的重要事件（含Bug、功能、配置、部署、策略、性能问题等），"
    "每条说明事件标题、类型、时间、参与者、影响组件、环境、复现步骤、错误或日志要点、配置变更、"
    "代码或链接参考、指标与证据、当前结论、状态与下一步行动。\n"
    "- 行动计划：列出8个最优先执行的任务，说明目标、负责人、环境、验收标准与预期时间。\n"
    "事件清单（按影响力由高到低排序；每个事件都要尽可能完整）】 对每个事件，使用如下模板分段输出： 1) 标题（一句话，含模块/版本/分支） 2) 类型：bug / feature / config / ops / strategy / decision / notice 3) 发生时间：具体时间或“约在HH:MM”（若不明写“未知”） 4) 参与者：@用户名 或 sender_id（若多名，列出关键干系人） 5) 受影响组件：文件/接口/模块/路由（尽量具体，如 server.go:/equity-history） 6) 环境：dev / main / binance / paper / prod（可多选） 7) 复现步骤：用step1/step2…给出可操作步骤（本地/测试网/生产分别说明） 8) 错误/日志要点：贴出原文关键句（20–140字），不要意译 9) 配置变化：.env或参数/开关的 before→after（如 admin_mode、API Key 范围、风控阈值） 10) 代码/链接参考：PR/commit/issue/文档路径或URL（若无写“无”） 11) 指标与证据：盈利/回撤/胜率/延迟/吞吐等；给出数值或“未知” 12) 风险评估：影响半径、是否可复现、是否牵涉资金或合规 13) 当前结论：群里形成的共识或主流判断（若分歧，写出分歧点） 14) 状态：open / fixed / workaround / investigating 15) 下一步：列出明确动作清单（含责任人与期望完成时间/里程碑） 16) 关键引用：至少2条消息的简短原文摘录，格式为 - #message_id @author YYYY-MM-DD HH:MM | 关键原句 - 可附链接（若有）"
    "- 风险与阻断：指出当前最大风险、限制与可能的替代方案。\n"
    "- 开放问题：列出待验证或需追问的关键问题及验证方式。\n"
    "- 变更与回归检查：说明今日涉及的配置、依赖或分支变动，并给出需要执行的回归测试与对照检查。"
)

DEFAULT_LIMIT = 500
SESSION_NAME = "telegram_session"
OUTPUT_DIR = "output"
RAW_FILENAME_TEMPLATE = "telegram_raw_{date}.jsonl"
SUMMARY_FILENAME_TEMPLATE = "summary_{date}.txt"
PAST_HOURS = 24
MAX_RETRIES = 3


class GroupAccessError(Exception):
    """Raised when the target chat cannot be accessed."""


class TelegramFetchError(Exception):
    """Raised when fetching messages fails after retries."""


class SummaryError(Exception):
    """Raised when summarisation via DeepSeek fails."""


@dataclass
class ChatMetadata:
    identifier: str
    display_name: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch past 24h Telegram messages from a single chat and summarise with DeepSeek."
    )
    parser.add_argument("--chat", required=True, help="目标群组的用户名或聊天 ID（例如 @group_name）")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"最多抓取的消息条数（默认 {DEFAULT_LIMIT}）",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="自定义 AI 总结 prompt，若未提供则使用内置模板",
    )
    return parser.parse_args()


def ensure_credentials() -> None:
    unresolved = []
    if API_ID == 123456:
        unresolved.append("API_ID")
    if API_HASH == "your_telegram_api_hash":
        unresolved.append("API_HASH")
    if DEEPSEEK_API_KEY == "your_deepseek_api_key":
        unresolved.append("DEEPSEEK_API_KEY")
    if unresolved:
        joined = ", ".join(unresolved)
        raise SystemExit(
            f"请先在 fetch_tg_ai.py 中设置有效的凭据: {joined}"
        )


async def resolve_chat_metadata(client: TelegramClient, chat: str) -> ChatMetadata:
    try:
        entity = await client.get_entity(chat)
    except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError, errors.ChannelInvalidError):
        raise GroupAccessError("无法找到指定的群组或用户名无效。")
    except errors.ChatAdminRequiredError:
        raise GroupAccessError("缺少访问该群组的权限（需要管理员或加入群组）。")
    except (errors.PeerIdInvalidError, ValueError):
        raise GroupAccessError("无法识别该聊天标识，请检查 --chat 参数。")

    title = getattr(entity, "title", None)
    username = getattr(entity, "username", None)
    if title:
        display_name = title
    elif username:
        display_name = f"@{username}"
    else:
        first_name = getattr(entity, "first_name", "")
        last_name = getattr(entity, "last_name", "")
        name_parts = [part for part in (first_name, last_name) if part]
        display_name = " ".join(name_parts) if name_parts else str(chat)

    identifier = f"@{username}" if username else str(chat)
    return ChatMetadata(identifier=identifier, display_name=display_name)


async def fetch_recent_messages(
    client: TelegramClient,
    chat: str,
    limit: int,
) -> List[Message]:
    since = datetime.now(timezone.utc) - timedelta(hours=PAST_HOURS)
    until = datetime.now(timezone.utc)

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            messages = await client.get_messages(chat, limit=limit)
            filtered = [
                msg for msg in messages
                if msg.date and since <= msg.date <= until
            ]
            filtered.sort(key=lambda msg: msg.date)
            return filtered
        except errors.FloodWaitError as exc:
            wait_time = exc.seconds + 1
            logging.warning("触发 FloodWait，需要等待 %s 秒后重试（第 %s 次）", wait_time, attempt)
            await asyncio.sleep(wait_time)
            last_error = exc
        except (ConnectionError, asyncio.TimeoutError) as exc:
            backoff = 2 ** attempt
            logging.warning("网络异常，%s 秒后重试（第 %s 次）: %s", backoff, attempt, exc)
            await asyncio.sleep(backoff)
            last_error = exc
        except errors.ChatAdminRequiredError as exc:
            raise GroupAccessError("缺少访问该群组的权限（需要管理员或加入群组）。") from exc
        except errors.RPCError as exc:
            if attempt >= MAX_RETRIES:
                raise TelegramFetchError(f"调用 Telegram API 失败: {exc}") from exc
            backoff = 2 ** attempt
            logging.warning("Telegram API 异常，%s 秒后重试（第 %s 次）: %s", backoff, attempt, exc)
            await asyncio.sleep(backoff)
            last_error = exc

    raise TelegramFetchError(f"重复重试后仍无法抓取消息: {last_error}")


def message_to_record(message: Message) -> dict:
    sender = getattr(message, "sender", None)
    username = getattr(sender, "username", None) if sender else None
    first_name = getattr(sender, "first_name", None) if sender else None
    last_name = getattr(sender, "last_name", None) if sender else None

    name_parts = [part for part in (first_name, last_name) if part]
    display_name: Optional[str]
    if name_parts:
        display_name = " ".join(name_parts)
    elif username:
        display_name = f"@{username}"
    elif message.sender_id:
        display_name = str(message.sender_id)
    else:
        display_name = "Unknown"

    text_content = message.message or ""

    return {
        "id": message.id,
        "date": message.date.astimezone(timezone.utc).isoformat(),
        "sender_id": message.sender_id,
        "sender": display_name,
        "username": f"@{username}" if username else None,
        "text": text_content,
    }


def build_summary_prompt(base_prompt: str, records: List[dict]) -> str:
    lines = []
    for record in records:
        timestamp = record["date"]
        sender = record["sender"]
        text = record["text"].replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"[{timestamp}] {sender}: {text}")

    message_log = "\n".join(lines) if lines else "（过去24小时无文本消息）"
    return f"{base_prompt.strip()}\n\n以下是群聊内容：\n{message_log}"


def summarise_with_deepseek(prompt_text: str) -> str:
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=DEEPSEEK_REQUEST_TIMEOUT,
        )
    except RequestException as exc:
        raise SummaryError(f"DeepSeek API 请求失败: {exc}") from exc

    if response.status_code != 200:
        raise SummaryError(
            f"DeepSeek API 返回错误（{response.status_code}）: {response.text}"
        )

    data = response.json()
    choices = data.get("choices")
    if not choices:
        raise SummaryError("DeepSeek API 未返回任何内容。")

    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise SummaryError("DeepSeek API 返回的内容为空。")
    return content.strip()


async def generate_summary(prompt_text: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, summarise_with_deepseek, prompt_text)


def ensure_output_dir(output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)


def write_jsonl(path: str, records: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def write_summary_file(path: str, chat: ChatMetadata, summary: str, date_label: str) -> None:
    header = (
        "=== Telegram 群组每日摘要 ===\n"
        f"群组: {chat.identifier}\n"
        f"时间: {date_label} (过去24小时)\n\n"
        "【AI 总结】\n"
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(header)
        handle.write(summary.strip())
        handle.write("\n")


async def async_main() -> None:
    args = parse_args()
    ensure_credentials()

    if args.limit <= 0:
        raise SystemExit("--limit 必须为正整数。")

    ensure_output_dir(OUTPUT_DIR)

    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        chat_meta = await resolve_chat_metadata(client, args.chat)
        logging.info("成功连接到 Telegram，开始抓取 %s 的消息。", chat_meta.display_name)
        messages = await fetch_recent_messages(client, args.chat, args.limit)

    records = [message_to_record(message) for message in messages]
    utc_now = datetime.now(timezone.utc)
    date_stamp = utc_now.strftime("%Y%m%d")
    date_label = utc_now.astimezone().strftime("%Y-%m-%d")

    raw_path = os.path.join(OUTPUT_DIR, RAW_FILENAME_TEMPLATE.format(date=date_stamp))
    write_jsonl(raw_path, records)

    prompt_text = args.prompt if args.prompt else DEFAULT_PROMPT
    full_prompt = build_summary_prompt(prompt_text, records)

    if records:
        summary_text = await generate_summary(full_prompt)
    else:
        summary_text = "过去24小时未检测到可总结的文本消息。"

    summary_path = os.path.join(OUTPUT_DIR, SUMMARY_FILENAME_TEMPLATE.format(date=date_stamp))
    write_summary_file(summary_path, chat_meta, summary_text, date_label)

    print(f"抓取消息：{len(records)} 条")
    print(f"原始数据已保存：{raw_path}")
    print(f"AI 汇总已生成：{summary_path}")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    configure_logging()
    try:
        asyncio.run(async_main())
    except GroupAccessError as exc:
        logging.error("群组访问失败：%s", exc)
    except TelegramFetchError as exc:
        logging.error("消息抓取失败：%s", exc)
    except SummaryError as exc:
        logging.error("AI 总结失败：%s", exc)


if __name__ == "__main__":
    main()
