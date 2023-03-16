import time

from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent
from nonebot.plugin.on import on_command

from ..service import Service

sv = Service('_broadcast')


@on_command(('广播', 'bc')).handle()
async def _(bot: Bot, e: PrivateMessageEvent):
    if await Service.SUPERUSER(e.user_id):
        if content := e.get_plaintext()[2:]:
            await bot.send(e, f'开始广播: {content}')
            t = time.time()
            await sv.broadcast(content)
            await bot.send(e, f'广播完毕！(耗时: {"%.2f" % (time.time() - t)}s)')
