from nonebot import on_fullmatch
from nonebot.internal.rule import Rule

from nonebot.adapters.onebot.v11 import (
    Bot as Onebot11Bot,
    MessageEvent as Onebot11MessageEvent,
    GroupMessageEvent as Onebot11GroupMessageEvent
)

on_gacha = on_fullmatch(('单抽', '十连', '抽干'))


# @on_gacha.handle()
async def _(bot: Onebot11Bot, event: Onebot11MessageEvent):
    await bot.send(
        event,
        f'''由于针对大量消息的资源优化，抽卡已于2023/9/30正式从公用版移除，
您依然可以通过https://github.com/Gomacker/Anisebot部署包含了该子插件开源的版本，
感谢您的理解与支持（''',
        reply_message=True
    )
