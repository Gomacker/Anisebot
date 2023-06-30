from anise_core.worldflipper import wfm

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import time

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageEvent

from anise_bot.service import Service
from .query import query_manager

sv = Service('worldflipper.query')
sv_whois = Service('worldflipper.whois')
sv_party = Service('worldflipper.party_searcher_beta')

query_manager.init()
logger.success(f'已加载query索引')


@sv.on_prefix(('qr', '查询', '搜索', '/'))
async def _(bot: Bot, e: MessageEvent):
    await wfm.statistic.add('query.count')
    text = e.get_message().extract_plain_text().strip()
    if text:
        t = time.time()
        logger.debug(f'查询事件: {text}')
        logger.debug(f'查询来源: q{e.user_id}')
        logger.debug(f'查询接收: q{bot.self_id}, m{e.message_id}')
        try:
            query_result = await query_manager.query(text)
            query_result = Message(f'(耗时{"%.2f" % (time.time() - t)}s)\n') + query_result
        except Exception as ex:
            logger.exception(ex)
            await bot.send(e, Service.get_send_content('worldflipper.query.failed') + '[发生错误]', at_sender=True)
            return
        logger.debug(f'查询完毕: {"%2f" % (time.time() - t)}s')
        await bot.send(e, query_result, at_sender=True)
        logger.debug(f'发送完毕: {"%2f" % (time.time() - t)}s')
    else:
        pass


@sv.on_fullmatch('重载索引')
async def _(bot: Bot, e: Event):
    if Service.SUPERUSER(bot, e):
        query_manager.init()
        await bot.send(e, f'索引重载完毕!')
