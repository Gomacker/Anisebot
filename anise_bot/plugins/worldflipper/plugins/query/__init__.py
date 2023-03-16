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

from anise_core import DATA_PATH
from .....service import Service
from .....utils import FreqLimiter, pic2b64
from .query import query_manager, query, get_target

sv = Service('worldflipper.query')
sv_whois = Service('worldflipper.whois')
sv_party = Service('worldflipper.party_searcher_beta')

query_group_cooldown = FreqLimiter(6)
query_private_cooldown = FreqLimiter(12)
on_query_stack = defaultdict(tuple[str, int])

logger.success(f'已加载{query_manager.init()}个query索引')


async def write_query_statistic(text):
    query_log_path = DATA_PATH / 'logs' / 'query.json'
    os.makedirs(query_log_path.parent, exist_ok=True)
    if not query_log_path.exists():
        query_log_path.write_text(json.dumps({}), 'utf-8')
    query_log: dict = defaultdict(int, json.loads(query_log_path.read_text('utf-8')))
    query_log[text] += 1
    query_log = {k: v for k, v in sorted(query_log.items(), key=lambda x: x[1], reverse=True)}
    query_log_path.write_text(json.dumps(query_log, ensure_ascii=False, indent=2), 'utf-8')


@sv.on_prefix(('tqr', 't查询', 't搜索'))
async def _(bot: Bot, e: GroupMessageEvent):
    await wfm.statistic.add('query.count')
    text = e.get_message().extract_plain_text().strip()
    if text:
        t = time.time()
        print(f'查询事件: {text}')
        print(f'查询来源: g{e.group_id}, q{e.user_id}')
        print(f'查询接收: q{e.self_id}, m{e.message_id}')
        await write_query_statistic(text)
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


@sv_whois.on_prefix(('谁是',))
@sv_whois.on_suffix(('是谁', '是哪个', '是啥', '是啥me', '是什么'))
async def _(bot: Bot, e: GroupMessageEvent):
    text = e.get_plaintext()
    target, source, guess_content = get_target(text, get_source_id(e.group_id, e.user_id))
    print(text, target)
    print(wfm.roster.size)
    if target:
        if source < 60:
            if len(text) <= 2:
                return
            await bot.send(
                e,
                MessageSegment.at(e.user_id) +
                Service.get_send_content('worldflipper.query.guess')
                .format(guess_content=guess_content) +
                MessageSegment.image(pic2b64(target.icon(size=88))) +
                f'{list(filter(lambda x: x, target.main_roster))[0]}'
            )
        else:
            await bot.send(
                e,
                MessageSegment.at(e.user_id) +
                MessageSegment.image(pic2b64(target.icon(size=88))) +
                f'{list(filter(lambda x: x, target.main_roster))[0]}'
            )
    else:
        pass


@sv.on_fullmatch('重载索引')
async def _(bot: Bot, e: Event):
    if Service.SUPERUSER(bot, e):
        logger.success(f'已加载{query_manager.init()}个query索引')
        await bot.send(e, f'{query_manager.init()}个索引重载完毕!')
