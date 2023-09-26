import time
from typing import Awaitable, Callable, Any, Coroutine

from nonebot import on_message
from nonebot.adapters.onebot.v11 import (
    Bot as Onebot11Bot,
    MessageEvent as Onebot11MessageEvent,
    GroupMessageEvent as Onebot11GroupMessageEvent
)
from nonebot.internal.rule import Rule

from .query import get_query, QueryManager, QueryHandlerWorldflipperPurePartySearcher
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


class MessageSync:
    """
    同步分布式Bot的消息，去掉不必要的重复回复
    ** 这是一个“Post Check but before generate”
    """

    def __init__(self):
        self.bot_id: str = 'debug-xxxxxx'
        self.sync_server: str = ''

    async def check(self, event: Onebot11MessageEvent, card: MessageCard) -> bool:
        data = {'message_id': event.message_id, 'user_id': event.user_id}
        if isinstance(event, Onebot11GroupMessageEvent):
            data['group_id'] = event.group_id
        data['card_hash'] = card.hash()



msync = MessageSync()


on_query = on_message(rule=Rule(_PrefixChecker(('qr', '/qr', '查询', '/'))))
on_party_query = on_message(rule=Rule(_PrefixChecker(('pqr', '/pqr', '查盘', '茶盘', '#'))))


async def do_query(bot: Onebot11Bot, event: Onebot11MessageEvent, query_manager: QueryManager):
    t = time.time()
    mc = await query_manager.query(event.get_plaintext())
    if await msync.check(event, mc):
        try:
            msg = await mc.to_message_onebot11(start_time=t)
        except Exception as e:
            exc = MessageCard(text=f'发生了错误: {e.__class__}')
            msg = await exc.to_message_onebot11(start_time=t)
        await bot.send(event, msg)


@on_query.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    await do_query(bot, event, get_query())


PQR_QM = QueryManager()
PQR_QM.load_worldflipper_type()
PQR_QM.query_handlers = [QueryHandlerWorldflipperPurePartySearcher()]


@on_party_query.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    await do_query(bot, event, PQR_QM)
