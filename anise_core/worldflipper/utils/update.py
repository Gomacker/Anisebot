import asyncio
import hashlib
import json
import os

import httpx
import requests
import tomli
from nonebot import logger

from anise_core import RES_PATH, DATA_PATH, MAIN_URL, CONFIG_PATH


async def update_worldflipper_objects():
    path = DATA_PATH / 'worldflipper' / 'object' / 'os'
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
    (RES_PATH / 'worldflipper' / 'roster' / 'roster_unit.json').write_text(json.dumps(roster.get('unit', {}), indent=2, ensure_ascii=False), 'utf-8')
    (RES_PATH / 'worldflipper' / 'roster' / 'roster_armament.json').write_text(json.dumps(roster.get('armament', {}), indent=2, ensure_ascii=False), 'utf-8')


async def update_worldflipper_query():
    logger.info(f'获取query/config.json ...')
    r = requests.post(f'{MAIN_URL}/api/v1/query/get/?path=config.json')
    data: dict = r.json()
    async with httpx.AsyncClient(timeout=30) as httpx_client:
        for k, v in data.items():
            for query_item in v:
                if query_item['type'] == 'image':
                    logger.info(f'检查更新{query_item["src"]} ...')
                    h = await httpx_client.get(f'{MAIN_URL}/api/v1/query/hash/?path={query_item["src"]}')
                    path_res = RES_PATH / 'worldflipper' / 'query' / query_item['src']
                    os.makedirs(path_res.parent, exist_ok=True)

                    h2 = None
                    need_update = not path_res.exists() or not h.text == (h2 := hashlib.md5(path_res.read_bytes()).hexdigest())
                    if need_update:
                        logger.info(f'正在更新{query_item["src"]} ...' + (f'{h.text} -> {h2}' if h2 else ''))
                        res = await httpx_client.get(f'{MAIN_URL}/api/v1/query/get/?path={query_item["src"]}&hash={h}')
                        path_res.write_bytes(res.content)

    (RES_PATH / 'worldflipper' / 'query' / 'config.json').write_bytes(r.content)


async def update():
    path = CONFIG_PATH / 'worldflipper' / 'config.toml'
    os.makedirs(path.parent, exist_ok=True)
    if not path.exists():
        await update_worldflipper_objects()
        await update_worldflipper_query()
        path.write_text('update = false', 'utf-8')
    config = tomli.loads(path.read_text('utf-8'))
    if config.get('update', False):
        await update_worldflipper_objects()
        await update_worldflipper_query()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(update())
    asyncio.set_event_loop(loop)
