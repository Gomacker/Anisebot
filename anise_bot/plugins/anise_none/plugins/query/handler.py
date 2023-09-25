import time

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot as Onebot11Bot, MessageEvent as Onebot11MessageEvent
from nonebot.internal.rule import Rule

from .query import get_query, QueryManager
from .utils import MessageCard


class _PrefixChecker:
    def __init__(self, prefix):
        if isinstance(prefix, str):
            prefix = (prefix,)
        self.prefix: list[str] = [x.lower() for x in sorted(list(prefix), key=lambda x: len(x), reverse=True)]

    async def __call__(self, event: Onebot11MessageEvent) -> bool:
        msg = event.get_message()
        tmsg = None
        for m in msg:
            if m.type == 'text':
                tmsg = m
                break
        if tmsg:
            start_msg: str = tmsg.data['text']
            start_msg = start_msg.lower()
            for p in self.prefix:
                if start_msg.startswith(p):
                    tmsg.data['text'] = tmsg.data['text'][len(p):]
                    return True
        return False


on_query = on_message(rule=Rule(_PrefixChecker(('qr', '/qr', '查询', '/'))))
on_query_ = on_message(rule=Rule(_PrefixChecker(('pqr', '/pqr', '查盘', '茶盘', '#'))))

@on_query.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    t = time.time()
    qm: QueryManager = get_query()
    mc = await qm.query(event.get_plaintext())
    try:
        msg = await mc.to_message_onebot11(start_time=t)
    except Exception as e:
        mc = MessageCard(text=f'发生了错误: {e.__class__}')
        msg = await mc.to_message_onebot11(start_time=t)
    await bot.send(event, msg)

