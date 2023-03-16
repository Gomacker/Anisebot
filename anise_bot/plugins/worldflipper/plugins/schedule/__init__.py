from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment

from .schedule import gen_schedule
from .....service import Service

sv = Service('schedule')

# TODO 注：未整理


@sv.on_fullmatch(('sc', '日程'))
async def schedule_reply(bot: Bot, e: GroupMessageEvent):
    await bot.send(
        e,
        MessageSegment.at(e.user_id) +
        MessageSegment.text(f'今日日程：') +
        gen_schedule(False)
    )


# @sv.scheduled_job('cron', hour='8', minute='30')
# async def daily_send():
#     await sv.broadcast(f'早上好~\n\n今日日程：{gen_schedule(False)}', interval_time=10)


@sv.on_fullmatch(('千里眼',))
async def kly_reply(bot, e: GroupMessageEvent):
    await bot.send(
        e,
        MessageSegment.at(e.user_id) +
        MessageSegment.text(f'目前的千里眼：\n千里眼基于过往活动数据预测，最终活动请以官宣内容为准\n') +
        gen_schedule(True))
