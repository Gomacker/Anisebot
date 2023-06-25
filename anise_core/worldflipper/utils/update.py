import hashlib

import requests
from nonebot import logger

from anise_core import RES_PATH


def main():
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
    main()
