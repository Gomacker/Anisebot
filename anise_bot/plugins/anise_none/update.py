import abc
import dataclasses
import urllib.parse
from pathlib import Path

import httpx
from nonebot import logger, on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from pydantic import BaseModel

from .anise import config
from .anise.config import RES_PATH, DATA_PATH


class UpdateEntry(BaseModel, abc.ABC):
    url: str
    path: Path
    name: str = ''

    @abc.abstractmethod
    async def update(self):
        raise NotImplementedError


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
                updates: list[UpdateManager.UpdateEntry] = [
                    UpdateManager.UpdateEntry(self.query_config_url, RES_PATH / 'query' / 'config.json', 'Query Config'),
                    UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/api/v2/worldflipper/character'), DATA_PATH / 'object' / 'os' / 'character.json', 'Character Data'),
                    UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/api/v2/worldflipper/equipment'), DATA_PATH / 'object' / 'os' / 'equipment.json', 'Equipment Data'),
                    UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/alias/worldflipper/character'), RES_PATH / 'alias/worldflipper' / 'equipment.json', 'Equipment Data'),
                    UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/alias/worldflipper/equipment'), RES_PATH / 'alias' / 'equipment.json', 'Equipment Data'),
                ]
                for update_ in updates:
                    logger.info(f'从{self.query_config_url}获取{update_.log_name}...')
                    success = await self.update_single_file(client, update_.url, update_.path)
                    if not success:
                        logger.warning(f'更新{update_.log_name}失败')
                    else:
                        logger.info(f'已更新{update_.log_name}!')


on_receive_update = on_fullmatch('更新')


@on_receive_update.handle()
async def _(bot: Bot, event: MessageEvent):
    await manager.update()
    await bot.send(event, '更新完毕')


manager = UpdateManager()
