import dataclasses
import json
import urllib.parse
from pathlib import Path

import httpx
from nonebot import logger

from ....anise import config
from ....anise.config import RES_PATH, DATA_PATH


class UpdateManager:
    def __init__(self, url: str = config.METEORHOUSE_URL, query_config_url: str = config.config.query.config_url):
        self.url = url
        self.query_config_url = query_config_url

    @staticmethod
    async def update_single_file(client: httpx.AsyncClient, url: str, path: Path) -> bool:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.content
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                return True
        except:
            return False
        return False

    @dataclasses.dataclass
    class UpdateEntry:
        url: str
        path: Path
        log_name: str

    async def update(self):
        async with httpx.AsyncClient() as client:
            if config.config.query.update_on_startup:
                UpdateEntry = UpdateManager.UpdateEntry
                updates: list[UpdateEntry] = [
                    UpdateEntry(self.query_config_url, RES_PATH / 'query' / 'config.json', 'Query Config'),
                    UpdateEntry(urllib.parse.urljoin(self.url, '/api/v2/'), DATA_PATH / 'object' / 'os' / 'character.json', 'Character Data'),
                    UpdateEntry(self.url, DATA_PATH / 'object' / 'os' / 'equipment.json', 'Equipment Data'),

                ]
                for update_ in updates:
                    logger.info(f'从{self.query_config_url}获取{update_.log_name}...')
                    success = await self.update_single_file(client, update_.url, update_.path)
                    if not success:
                        logger.warning(f'更新{update_.log_name}失败')
                    else:
                        logger.info(f'已更新{update_.log_name}!')


manager = UpdateManager()
