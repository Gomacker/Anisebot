import asyncio
import dataclasses
import json
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from queue import Queue
from typing import Awaitable, Callable, Optional, Union

from nonebot import on_message, on_fullmatch, logger, Bot
from nonebot.adapters.onebot.v11 import (
    MessageEvent as Onebot11MessageEvent,
    GroupMessageEvent as Onebot11GroupMessageEvent,
    MessageSegment as Onebot11MessageSegment
)
from nonebot.adapters.red import (
    MessageEvent as RedMessageEvent,
    GroupMessageEvent as RedGroupMessageEvent,
    MessageSegment as RedMessageSegment
)
from nonebot.internal.rule import Rule
from websockets.exceptions import ConnectionClosed
from websockets.legacy.client import WebSocketClientProtocol

from .query import get_query, QueryManager, QueryHandlerWorldflipperPurePartySearcher
from ... import config
from ...anise import config as anise_config
from ...utils import MessageCard

MessageEvent = Union[Onebot11MessageEvent, RedMessageEvent]
GroupMessageEvent = Union[Onebot11GroupMessageEvent, RedGroupMessageEvent]
MessageSegment = Union[Onebot11MessageSegment, RedMessageSegment]


async def soft_to_me_checker(event: MessageEvent):
    def is_at_or_reply_other(segment: MessageSegment):
        if isinstance(segment, Onebot11MessageSegment):
            return (event.reply and event.reply.sender.user_id != event.self_id) or (
                    segment.type == 'at' and segment.data['qq'] != event.self_id)
        elif isinstance(segment, RedMessageSegment):
            return event.to_me

    return not any(filter(is_at_or_reply_other, [msg for msg in event.message]))


class _PrefixChecker:
    def __init__(self, prefix):
        if isinstance(prefix, str):
            prefix = (prefix,)
        self.prefix: list[str] = [x.lower() for x in sorted(list(set(prefix)), key=lambda x: len(x), reverse=True)]

    async def __call__(self, event: MessageEvent) -> bool:
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


async def whitelist_checker(event: MessageEvent) -> bool:
    if config.whitelist:
        if isinstance(event, Onebot11GroupMessageEvent):
            return event.group_id in config.whitelist
        elif isinstance(event, RedGroupMessageEvent):
            return int(event.peerUid) in config.whitelist
    return True


@dataclasses.dataclass
class CheckPackage:
    bot: Bot
    event: MessageEvent
    card: MessageCard

class MessageSync:
    """
    同步分布式Bot的消息，去掉不必要的重复回复
    ** 这是一个“Post Check but before generate”
    """

    def __init__(self):
        self.bot_id: str = 'debug-xxxxxx'
        self.sync_server: str = ''
        self.ws: Optional[WebSocketClientProtocol] = None
        self.uri = anise_config.config.sync_uri

        self.failed_count = 0
        self.failed_max = 3
        self.retry_cooldown = 60 * 30
        self.retry_time = 0

    async def connect(self):
        import websockets
        self.ws = await websockets.connect(self.uri) if self.uri else None

    async def check(self, bot: Bot, event: MessageEvent, card: MessageCard, retry: bool = False) -> bool:
        if self.failed_count >= self.failed_max:
            if time.time() < self.retry_time:
                self.failed_count = 0
            return True

        try:
            if anise_config.config.sync_uri and not self.ws or self.ws.closed:
                await self.connect()

            logger.info(event)
            message_id = str(event.message_id) if isinstance(event, Onebot11MessageEvent) else event.msgRandom
            user_id = event.get_user_id()
            bot_id = bot.self_id


            data = {'user_id': user_id, 'bot_id': bot_id, 'message_id': message_id}
            print(message_id)
            if isinstance(event, RedGroupMessageEvent):
                data['group_id'] = int(event.peerUid)
            elif isinstance(event, Onebot11GroupMessageEvent):
                data['group_id'] = event.group_id
            data['card_hash'] = card.hash()
            print(data)
            print(self.ws)
            await self.ws.send(json.dumps(data))
            # try to receive correct msg
            for _ in range(10):
                msg: dict = json.loads(await self.ws.recv())
                if msg['package'].get('message_id') == message_id and msg['package'].get('bot_id') == bot_id:
                    logger.debug(f'Received {msg}')
                    return msg.get('send', False)
        except ConnectionClosed as e:
            if not retry:
                return await self.check(bot, event, card, retry=True)
        except Exception as e:
            self.failed_count += 1
            self.retry_time = time.time() + self.retry_cooldown
            traceback.print_exception(e)
            logger.error('连接至同步服务器失败，已自动通过消息处理过滤')
            return True


class CheckerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.sync = MessageSync()
        self.check_queue: Queue[CheckPackage] = Queue()
        self.output_queue: Queue[bool] = Queue()
        self.start()

    def run(self):
        while True:
            time.sleep(1)
            if not self.check_queue.empty():
                package: CheckPackage = self.check_queue.get()
                is_ok: bool = asyncio.run(self.sync.check(package.bot, package.event, package.card))
                self.output_queue.put(is_ok)

    async def check(self, bot: Bot, event: MessageEvent, card: MessageCard) -> bool:
        self.check_queue.put(CheckPackage(bot, event, card))
        # async wait for check queue is not empty
        while self.output_queue.empty():
            print(f'{bot} is waiting {event.msgRandom}')
            await asyncio.sleep(1)
        return self.output_queue.get()



msync_list: dict[str, CheckerThread] = dict()

def package_checkers(
        *checkers: Callable[[MessageEvent], Awaitable[bool]],
        enable_cache: bool = True
) -> Callable:
    # 狂暴写成了一个lru_cache，回来再优化这个的结构吧
    @dataclasses.dataclass
    class CheckerCache:
        message_id: int
        result: bool
    caches: deque[CheckerCache] = deque(maxlen=10)

    async def deco(event: MessageEvent):
        for checker in checkers:
            result = await checker(event)
            if not result:
                return False
        return True

    async def checker_(event: MessageEvent):
        if enable_cache:
            message_id = event.msgId if isinstance(event, RedMessageEvent) else event.message_id
            f: list[CheckerCache] = list(filter(lambda x: x.message_id == message_id, caches))
            if f:
                return f[0].result
            else:
                result = await deco(event)
                caches.append(CheckerCache(message_id, result))
                return result
        else:
            return await deco(event)

    return checker_


silent_list = set()
_temp_silent_list_path = Path('temp_silent_list.json')
if not _temp_silent_list_path.exists():
    _temp_silent_list_path.write_text(json.dumps([]), encoding='utf-8')
silent_list = set(json.loads(_temp_silent_list_path.read_text('utf-8')))


async def temp_silent(event: MessageEvent):
    if isinstance(event, Onebot11GroupMessageEvent):
        return event.group_id not in silent_list
    elif isinstance(event, RedGroupMessageEvent):
        return event.peerUid not in silent_list
    return True


basic_checkers = package_checkers(whitelist_checker, temp_silent, soft_to_me_checker)

on_query = on_message(rule=Rule(_PrefixChecker(anise_config.config.query.query_prefixes), basic_checkers))
on_party_query = on_message(
    rule=Rule(_PrefixChecker(anise_config.config.query.worldflipper_party_query_prefixes), basic_checkers))
on_query_refresh = on_fullmatch(('刷新索引', '重载索引'), rule=Rule(basic_checkers))


async def do_query(bot: Bot, event: MessageEvent, query_manager: QueryManager):
    t = time.time()
    mc = await query_manager.query(event.get_plaintext())


    if not mc:
        mc = MessageCard()  # 空Card返回Failed的Message
        if isinstance(event, RedMessageEvent):
            await bot.send(event, await mc.to_message_red(event, start_time=t), reply_message=True)
        else:
            await bot.send(event, await mc.to_message_onebot11(start_time=t), reply_message=True)
        return

    # if bot.self_id not in msync_list:
    #     check_thread = CheckerThread()
    #     msync_list[bot.self_id] = check_thread
    # else:
    #     check_thread = msync_list[bot.self_id]

    # if await check_thread.check(bot, event, mc):
    if True:
        try:
            if isinstance(event, RedMessageEvent):
                msg = await mc.to_message_red(event, start_time=t)
            else:
                msg = await mc.to_message_onebot11(start_time=t)
        except Exception as e:
            exc = MessageCard(exception=f'发生了错误: {e.__class__}')
            traceback.print_exception(e)
            if isinstance(event, RedMessageEvent):
                msg = await exc.to_message_red(event, start_time=t)
            else:
                msg = await exc.to_message_onebot11(start_time=t)
        await bot.send(event, msg, reply_message=True)


@on_query.handle()
async def _(bot: Bot, event: MessageEvent):
    await do_query(bot, event, await get_query())



PQR_QM = QueryManager()
PQR_QM.load_worldflipper_type()
PQR_QM.query_handlers = [QueryHandlerWorldflipperPurePartySearcher(**{'type': 'pps'})]


@on_party_query.handle()
async def _(bot: Bot, event: MessageEvent):
    await do_query(bot, event, PQR_QM)


@on_query_refresh.handle()
async def _(bot: Bot, event: MessageEvent):
    qm = await get_query()
    ql = await qm.init()
    await bot.send(event, f'已加载 {ql} 个Query索引！')


from nonebot.adapters.onebot.v11 import permission as onebot_permission

onebot_group_admin = onebot_permission.GROUP_ADMIN | onebot_permission.GROUP_OWNER
on_silent_open = on_message(rule=_PrefixChecker(('静音',)))
on_silent_close = on_message(rule=_PrefixChecker(('解除静音',)))


@on_silent_open.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    if event.to_me:
        silent_list.add(int(event.peerUid) if isinstance(event, RedGroupMessageEvent) else event.group_id)
        Path('temp_silent_list.json').write_text(json.dumps(list(silent_list)), encoding='utf-8')

        await bot.send(event, '已静音')


@on_silent_close.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    if event.to_me:
        silent_list.remove(int(event.peerUid) if isinstance(event, RedGroupMessageEvent) else event.group_id)
        Path('temp_silent_list.json').write_text(json.dumps(list(silent_list)), encoding='utf-8')

        await bot.send(event, f'已解除静音')
