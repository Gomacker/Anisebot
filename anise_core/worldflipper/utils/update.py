import hashlib
import json

import requests
from nonebot import logger

from anise_core import RES_PATH, DATA_PATH


def update_worldflipper_objects():
    path = DATA_PATH / 'worldflipper' / 'object' / 'os'
    logger.info(f'获取open source unit data ...')
    r = requests.post('http://meteorhouse.wiki/api/v1/data/unit/')
    (path / 'unit.json').write_bytes(r.content)
    logger.info(f'获取open source armament data ...')
    r = requests.post('http://meteorhouse.wiki/api/v1/data/armament/')
    (path / 'armament.json').write_bytes(r.content)
    logger.info(f'获取open source roster data ...')
    r = requests.post('http://meteorhouse.wiki/api/v1/data/roster/')
    roster: dict = r.json()
    (RES_PATH / 'worldflipper' / 'roster' / 'roster_unit.json').write_text(json.dumps(roster.get('unit', {}), indent=2, ensure_ascii=False), 'utf-8')
    (RES_PATH / 'worldflipper' / 'roster' / 'roster_armament.json').write_text(json.dumps(roster.get('armament', {}), indent=2, ensure_ascii=False), 'utf-8')

def main():
    # logger.info(f'获取query/config.json ...')
    # r = requests.post('http://meteorhouse.wiki/api/v1/query/get/?path=config.json')
    # logger.info(f'获取query/config.json ...')
    # r = requests.post('http://meteorhouse.wiki/api/v1/query/get/?path=config.json')
    logger.info(f'获取query/config.json ...')
    r = requests.post('http://meteorhouse.wiki/api/v1/query/get/?path=config.json')
    data: dict = r.json()
    for k, v in data.items():
        for query_item in v:
            if query_item['type'] == 'image':
                logger.info(f'检查更新{query_item["src"]} ...')
                h = requests.post(f'http://meteorhouse.wiki/api/v1/query/hash/?path={query_item["src"]}')
                path_res = RES_PATH / 'worldflipper' / 'query' / query_item['src']
                h2 = hashlib.md5(path_res.read_bytes()).hexdigest()
                if not path_res.exists() or not h.text == h2:
                    logger.info(f'正在更新{query_item["src"]} ...{h.text} != {h2}')
                    res = requests.get(f'http://meteorhouse.wiki/api/v1/query/get/?path={query_item["src"]}&hash={h}')
                    path_res.write_bytes(res.content)

    (RES_PATH / 'worldflipper' / 'query' / 'config.json').write_bytes(r.content)


if __name__ == '__main__':
    update_worldflipper_objects()
    # main()
