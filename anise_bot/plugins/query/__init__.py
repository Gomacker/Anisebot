from anise_core import MAIN_URL
from anise_core.worldflipper import wfm, reload_wfm
from anise_core.worldflipper.utils.update import update
from ...utils import get_send_content

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import time

from nonebot import logger
from nonebot.adapters.qqguild import Bot, Event, Message, MessageEvent

from anise_bot.service import Service
from .query import query_manager

sv = Service('worldflipper.query')


@sv.on_prefix(('qr', '/qr', '查询', '搜索', '/'))
async def _(bot: Bot, e: MessageEvent):
    await wfm.statistic.add('query.count')
    text = e.get_message().extract_plain_text().strip()
    if text:
        try:
            t = time.time()
            query_result = await query_manager.query(text)
            query_result = Message(f'(耗时{"%.2f" % (time.time() - t)}s)\n') + query_result
        except Exception as ex:
            logger.exception(ex)
            await bot.send(e, get_send_content('worldflipper.query.failed') + '[发生错误]', reply_message=True)
            return
        logger.debug(f'查询完毕: {"%2f" % (time.time() - t)}s')
        await bot.send(e, query_result, reply_message=True)
        logger.debug(f'发送完毕: {"%2f" % (time.time() - t)}s')


@sv.on_prefix(('pqr', '/pqr', '茶盘', '查盘', '#'))
async def _(bot: Bot, e: MessageEvent):
    await wfm.statistic.add('query.count')
    text = e.get_message().extract_plain_text().strip()
    if text:
        try:
            t = time.time()
            query_result = await query_manager.query(text, query_map=[{"type": "pps"}])
            query_result = Message(f'(耗时{"%.2f" % (time.time() - t)}s)\n') + query_result
        except Exception as ex:
            logger.exception(ex)
            await bot.send(e, get_send_content('worldflipper.query.failed') + '[发生错误]', reply_message=True)
            return
        await bot.send(e, query_result, reply_message=True)


@sv.on_fullmatch(('同步库',))
async def _(bot: Bot, e: MessageEvent):
    if Service.SUPERUSER(bot, e):
        await bot.send(e, f'正在从{MAIN_URL}同步库，请稍后...', reply_message=True)
        await update()
        reload_wfm()
        await bot.send(
            e,
            f'同步完毕，{len(wfm.units())} Units and {len(wfm.armaments())} Armament loaded',
            reply_message=True
        )


def reload_query():
    count = query_manager.init()
    logger.success(f'已加载 {count} 个query索引')
    return count


@sv.on_fullmatch('重载索引')
async def _(bot: Bot, e: Event):
    if Service.SUPERUSER(bot, e):
        await bot.send(e, f'{reload_query()} 个索引重载完毕!')


reload_query()
