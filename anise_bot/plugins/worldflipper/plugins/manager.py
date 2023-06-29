try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot

from ....service import Service
from anise_core import CONFIG_PATH
from anise_core.worldflipper import wfm

sv = Service('worldflipper._manager')


GROUP_CONFIG = CONFIG_PATH / 'worldflipper' / 'source' / 'group.json'
PRIVATE_CONFIG = CONFIG_PATH / 'worldflipper' / 'source' / 'private.json'
os.makedirs(CONFIG_PATH / 'worldflipper' / 'source', exist_ok=True)
if not GROUP_CONFIG.exists():
    GROUP_CONFIG.write_text(json.dumps({}), 'utf-8')
    PRIVATE_CONFIG.write_text(json.dumps({}), 'utf-8')


@sv.on_prefix(('切换群源',))
async def _(bot: Bot, e: GroupMessageEvent):
    print(f'''
    切换群源：
    SUPERUSER：{await Service.SUPERUSER(bot, e)}
    OWNER：{await Service.OWNER(bot, e)}
    ADMIN：{await Service.ADMIN(bot, e)}
    {e.get_plaintext().strip()}
    {e.get_plaintext().strip() in wfm.loaded_source_ids()}
    ''')
    print(await (Service.SUPERUSER | Service.ADMIN | Service.OWNER)(bot, e))
    if await Service.SUPERUSER(bot, e) | await Service.OWNER(bot, e) | await Service.ADMIN(bot, e):
        s = e.get_plaintext().strip()
        if s in wfm.loaded_source_ids():
            d = json.loads(GROUP_CONFIG.read_text('utf-8'))
            d[str(e.group_id)] = s
            GROUP_CONFIG.write_text(json.dumps(d, ensure_ascii=False, indent=2))
            await bot.send(e, f'已将群库源切换为 {d[str(e.group_id)]}')


DEFAULT_SOURCE = wfm.loaded_source_ids()[0]


def get_source_id(group_id, user_id) -> str:
    gd: dict = json.loads(GROUP_CONFIG.read_text('utf-8'))
    pd: dict = json.loads(PRIVATE_CONFIG.read_text('utf-8'))
    if str(user_id) in pd:
        return pd[str(user_id)]
    elif group_id and str(group_id) in gd:
        return gd[str(group_id)]
    else:
        return DEFAULT_SOURCE

