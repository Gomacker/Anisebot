from PIL import Image

from anise_core import RES_PATH
from anise_core.worldflipper.utils.schedule import get_schedule

try:
    import ujson as json
except ModuleNotFoundError:
    import json

from nonebot.adapters.onebot.v11 import MessageSegment

from .....utils import FreqLimiter, pic2b64

gen_schedule_cooldown = FreqLimiter(600)
save_path = RES_PATH / 'worldflipper' / 'schedule.png'


async def gen_schedule() -> MessageSegment:
    if gen_schedule_cooldown.check('') and save_path.exists():
        img = await get_schedule()
        gen_schedule_cooldown.start_cd('')
        img.save(save_path)
    else:
        img = Image.open(save_path)
    return MessageSegment.image(pic2b64(img, format_='JPEG'))