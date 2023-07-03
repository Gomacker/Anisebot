import asyncio

import toml

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os

import requests
from nonebot import logger

from anise_core import RES_PATH, DATA_PATH, MAIN_URL


async def update_worldflipper_objects():
    path = DATA_PATH / 'object' / 'os'
    os.makedirs(path, exist_ok=True)
    logger.info(f'获取open source unit data ...')
    r = requests.post(f'{MAIN_URL}/api/v1/data/unit/')
    (path / 'unit.json').write_bytes(r.content)
    logger.info(f'获取open source armament data ...')
    r = requests.post(f'{MAIN_URL}/api/v1/data/armament/')
    (path / 'armament.json').write_bytes(r.content)
    logger.info(f'获取open source roster data ...')
    r = requests.post(f'{MAIN_URL}/api/v1/data/roster/')
    roster: dict = r.json()
    (RES_PATH / 'roster' / 'unit.toml').write_text(toml.dumps(roster.get('unit', {})), 'utf-8')
    (RES_PATH / 'roster' / 'armament.toml').write_text(toml.dumps(roster.get('armament', {})), 'utf-8')


async def update():
    await update_worldflipper_objects()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(update())
    asyncio.set_event_loop(loop)
