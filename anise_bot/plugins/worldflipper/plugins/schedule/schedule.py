try:
    import ujson as json
except ModuleNotFoundError:
    import json
import time

import requests
from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageSegment

from anise_core import RES_PATH
from ..schedule import html_util
from .....utils import FreqLimiter, pic2b64

download_schedule_cooldown = FreqLimiter(600)


def download_schedule(url='https://wf-calendar.miaowm5.com/data/info.json'):
    path = RES_PATH / 'worldflipper' / 'schedule.json'
    logger.info(f'trying to download {url}')
    d = dict()
    try:
        rsp = requests.get(url, stream=True, timeout=10)
        d = json.loads(rsp.content.decode('UTF-8'))
        f = open(path, 'w+')
        f.write(json.dumps(d, sort_keys=True, indent=4, separators=(',', ': ')))
    except Exception as e:
        logger.error(f'download failed {url}')
        logger.exception(e)
    return d


def gen_schedule(qly):
    path = RES_PATH / 'worldflipper' / 'schedule.json'
    d: dict
    if (not path.exists()) or download_schedule_cooldown.check('schedule'):
        d = download_schedule()
        download_schedule_cooldown.start_cd('schedule')
    else:
        d = json.loads(open(path, 'r').read())
    msg = html_util.gen_pic(qly, d)
    msg = MessageSegment.image(pic2b64(msg, format_='JPEG'))
    return msg
