
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

API_ID = 38035966
API_HASH = "bb0b96c728301a2fb46655af27cd2fe4"
SESSION = "tg_session"

async def main():
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        print("序号 | 名称(title) | username | id | 类型")
        async for i, d in aenumerate(client.iter_dialogs()):
            ent = d.entity
            title = getattr(ent, "title", None) or getattr(d, "name", "")
            username = getattr(ent, "username", None)
            kind = ("supergroup" if isinstance(ent, Channel) and ent.megagroup else
                    "channel"   if isinstance(ent, Channel) and not ent.megagroup else
                    "group"     if isinstance(ent, Chat) else
                    "user")
            print(f"{i:>3} | {title} | {username} | {ent.id} | {kind}")

# 小工具：异步枚举
async def aenumerate(aiter, start=0):
    idx = start
    async for item in aiter:
        yield idx, item
        idx += 1

import asyncio
asyncio.run(main())
