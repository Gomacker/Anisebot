import os
import traceback
from pathlib import Path

from anise_core.worldflipper import wfm
from ..manager import get_source_id

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import time
from collections import defaultdict

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, GroupMessageEvent, Event, Message

from .....service import Service
from .....utils import FreqLimiter
from .query import query_manager, query, get_target

sv = Service('worldflipper.query')
sv_whois = Service('worldflipper.whois')
sv_party = Service('worldflipper.party_searcher_beta')

query_group_cooldown = FreqLimiter(6)
query_private_cooldown = FreqLimiter(12)
on_query_stack = defaultdict(tuple[str, int])

logger.success(f'已加载{query_manager.init()}个query索引')


@sv.on_prefix(('qr', '查询', '搜索', '/'))
async def _(bot: Bot, e: GroupMessageEvent):
    await wfm.statistic.add('query.count')
    text = e.get_message().extract_plain_text().strip()
    if text:
        t = time.time()
        print(f'查询事件: {text}')
        print(f'查询来源: g{e.group_id}, q{e.user_id}')
        print(f'查询接收: q{e.self_id}, m{e.message_id}')
        try:
            query_result = await query(text, e)
            query_result = Message(f'(耗时{"%.2f" % (time.time() - t)}s)\n') + query_result
        except Exception as ex:
            logger.exception(ex)
            await bot.send(
                e,
                MessageSegment.at(e.user_id) +
                Service.get_send_content('worldflipper.query.failed') + '[发生错误]')
            return
        print(f'查询完毕: {"%2f" % (time.time() - t)}s')
        try:
            await bot.call_api(
                'send_group_msg', group_id=e.group_id,
                message=MessageSegment.reply(e.message_id) + query_result
            )
        except:
            os.makedirs('!exception', exist_ok=True)
            (Path('!exception') / f'{time.strftime("%Y%m%d%H%M%S")}.txt').write_text(
                f'{bot.self_id}\ne: {e.dict()}\nmsg: {query_result}\n{traceback.format_exc()}'
            )
        print(f'send query result: self: {e.self_id}, msg: {e.message_id}, time: {time.strftime("%Y%m%d %H:%M:%S")}')
        print(f'发送完毕: {"%2f" % (time.time() - t)}s')
    else:
        pass


@sv.on_fullmatch('重载索引')
async def _(bot: Bot, e: Event):
    if Service.SUPERUSER(bot, e):
        logger.success(f'已加载{query_manager.init()}个query索引')
        await bot.send(e, f'{query_manager.init()}个索引重载完毕!')
