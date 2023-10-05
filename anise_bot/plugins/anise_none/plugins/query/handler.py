import dataclasses
import json
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Awaitable, Callable, Any, Coroutine, Optional

from nonebot import on_message, on_fullmatch, logger
from nonebot.adapters.onebot.v11 import (
    Bot as Onebot11Bot,
    MessageEvent as Onebot11MessageEvent,
    GroupMessageEvent as Onebot11GroupMessageEvent,
    MessageSegment as Onebot11MessageSegment
)
from nonebot.internal.rule import Rule
from websockets.legacy.client import WebSocketClientProtocol

from .query import get_query, QueryManager, QueryHandlerWorldflipperPurePartySearcher
from .utils import MessageCard
from ... import config
from ...anise import config as anise_config


async def soft_to_me_checker(event: Onebot11MessageEvent):
    def is_at_or_reply_other(segment: Onebot11MessageSegment):
        return (event.reply and event.reply.sender.user_id != event.self_id) or (
                segment.type == 'at' and segment.data['qq'] != event.self_id)

    return not any(filter(is_at_or_reply_other, [m for m in event.message]))


class _PrefixChecker:
    def __init__(self, prefix):
        if isinstance(prefix, str):
            prefix = (prefix,)
        self.prefix: list[str] = [x.lower() for x in sorted(list(set(prefix)), key=lambda x: len(x), reverse=True)]

    async def __call__(self, event: Onebot11MessageEvent) -> bool:
        msg = event.get_message()
        tmsg = None
        for m in msg:
            if m.type == 'text':
                tmsg = m
                break
        if tmsg:
            start_msg: str = tmsg.data['text']
            start_msg = start_msg.lower().strip()
            for p in self.prefix:
                if start_msg.startswith(p):
                    tmsg.data['text'] = tmsg.data['text'][len(p):]
                    return True
        return False


async def whitelist_checker(event: Onebot11MessageEvent) -> bool:
    if config.whitelist and isinstance(event, Onebot11GroupMessageEvent):
        return event.group_id in config.whitelist
    return True


class MessageSync:
    """
    同步分布式Bot的消息，去掉不必要的重复回复
    ** 这是一个“Post Check but before generate”
    """

    def __init__(self):
        self.bot_id: str = 'debug-xxxxxx'
        self.sync_server: str = ''
        self.ws: Optional[WebSocketClientProtocol] = None
        self.uri = 'ws://meteorhouse.wiki/bot/sync/ws'

        self.failed_count = 0
        self.failed_max = 3
        self.retry_cooldown = 60 * 30
        self.retry_time = 0

    async def connect(self):
        import websockets
        self.ws = await websockets.connect(self.uri)

    async def check(self, event: Onebot11MessageEvent, card: MessageCard) -> bool:
        if self.failed_count >= self.failed_max:
            if time.time() < self.retry_time:
                self.failed_count = 0
            return True

        try:
            if not self.ws or self.ws.closed:
                await self.connect()
            print(type(self.ws))
            data = {'message_id': event.message_id, 'user_id': event.user_id}
            if isinstance(event, Onebot11GroupMessageEvent):
                data['group_id'] = event.group_id
            data['card_hash'] = card.hash()
            await self.ws.send(json.dumps(data))
            msg: dict = json.loads(await self.ws.recv())
            print(f'Received {msg}')
            return msg.get('accept', False)
        except:
            self.failed_count += 1
            self.retry_time = time.time() + self.retry_cooldown
            logger.error('连接至同步服务器失败，已自动通过消息处理过滤')
            return True


msync = MessageSync()


def package_checkers(
        *checkers: Callable[[Onebot11MessageEvent], Awaitable[bool]],
        enable_cache: bool = True
) -> Callable:
    # 狂暴写成了一个lru_cache，回来再优化这个的结构吧
    @dataclasses.dataclass
    class CheckerCache:
        message_id: int
        result: bool
    caches: deque[CheckerCache] = deque(maxlen=10)

    async def deco(event: Onebot11MessageEvent):

        for checker in checkers:
            result = await checker(event)
            if not result:
                return False
        return True

    async def checker_(event: Onebot11MessageEvent):
        if enable_cache:
            f: list[CheckerCache] = list(filter(lambda x: x.message_id == event.message_id, caches))
            if f:
                return f[0].result
            else:
                result = await deco(event)
                caches.append(CheckerCache(event.message_id, result))
                return result
        else:
            return await deco(event)

    return checker_


silent_list = set()
_temp_silent_list_path = Path('temp_silent_list.json')
if not _temp_silent_list_path.exists():
    _temp_silent_list_path.write_text(json.dumps([]), encoding='utf-8')
silent_list = set(json.loads(_temp_silent_list_path.read_text('utf-8')))


async def temp_silent(event: Onebot11MessageEvent):
    if isinstance(event, Onebot11GroupMessageEvent):
        return event.group_id not in silent_list
    return True


def temp_reducer(interval: int):
    async def checker(event: Onebot11MessageEvent):
        pass


basic_checkers = package_checkers(whitelist_checker, temp_silent, soft_to_me_checker)

on_query = on_message(rule=Rule(_PrefixChecker(anise_config.config.query.query_prefixes), basic_checkers))
on_party_query = on_message(
    rule=Rule(_PrefixChecker(anise_config.config.query.worldflipper_party_query_prefixes), basic_checkers))
on_query_refresh = on_fullmatch(('刷新索引', '重载索引'), rule=Rule(basic_checkers))


async def do_query(bot: Onebot11Bot, event: Onebot11MessageEvent, query_manager: QueryManager):
    t = time.time()
    mc = await query_manager.query(event.get_plaintext())
    if not mc:
        mc = MessageCard()
        await bot.send(event, await mc.to_message_onebot11(start_time=t), reply_message=True)
        return
    if await msync.check(event, mc):
        try:
            msg = await mc.to_message_onebot11(start_time=t)
        except Exception as e:
            exc = MessageCard(exception=f'发生了错误: {e.__class__}')
            traceback.print_exception(e)
            msg = await exc.to_message_onebot11(start_time=t)
        await bot.send(event, msg, reply_message=True)


@on_query.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    print(f'on handle {event}')
    await do_query(bot, event, get_query())


PQR_QM = QueryManager()
PQR_QM.load_worldflipper_type()
PQR_QM.query_handlers = [QueryHandlerWorldflipperPurePartySearcher(**{'type': 'pps'})]


@on_party_query.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    await do_query(bot, event, PQR_QM)


@on_query_refresh.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    qm = get_query()
    ql = qm.init()
    await bot.send(event, f'已加载 {ql} 个Query索引！')


from nonebot.adapters.onebot.v11 import permission as onebot_permission

on_silent_open = on_message(
    rule=_PrefixChecker(('静音',)),
    permission=onebot_permission.GROUP_ADMIN | onebot_permission.GROUP_OWNER
)
on_silent_close = on_message(
    rule=_PrefixChecker(('解除静音',)),
    permission=onebot_permission.GROUP_ADMIN | onebot_permission.GROUP_OWNER
)


@on_silent_open.handle()
async def _(bot: Onebot11Bot, event: Onebot11GroupMessageEvent):
    if event.to_me:
        silent_list.add(event.group_id)
        Path('temp_silent_list.json').write_text(json.dumps(list(silent_list)), encoding='utf-8')

        await bot.send(event, '已静音')


@on_silent_close.handle()
async def _(bot: Onebot11Bot, event: Onebot11GroupMessageEvent):
    if event.to_me:
        silent_list.remove(event.group_id)
        Path('temp_silent_list.json').write_text(json.dumps(list(silent_list)), encoding='utf-8')

        await bot.send(event, f'已解除静音')
