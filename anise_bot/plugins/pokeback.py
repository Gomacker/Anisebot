from nonebot import Bot
from nonebot.adapters.onebot.v11 import MessageSegment, Event

from ..service import Service
from ..utils import FreqLimiter

sv = Service('pokeback')

limiter = FreqLimiter(10)


@sv.on_poke()
async def _(bot: Bot, e: Event):
    uid = e.dict()['user_id']
    if limiter.check(uid):
        poke = MessageSegment('poke', {'qq': str(uid)})
        limiter.start_cd(uid)
        await bot.send(e, poke)
