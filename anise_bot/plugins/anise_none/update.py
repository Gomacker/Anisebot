import abc
import dataclasses
import traceback
import urllib.parse
from pathlib import Path
from typing import Union

import httpx
from nonebot import logger, on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import (
Bot as Onebot11Bot,
MessageEvent as Onebot11MessageEvent
)
from nonebot.adapters.red import (
Bot as RedBot,
MessageEvent as RedMessageEvent
)
from nonebot.internal.rule import Rule
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
    async def get_single_file(client: httpx.AsyncClient, url: str, path: Path) -> bool:
        try:
            response = await client.post(url)
            print(response)
            if response.status_code == 200:
                content = response.content
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                return True
        except:
            traceback.print_exc()
            return False
        return False

    @dataclasses.dataclass
    class UpdateEntry:
        url: str
        path: Path
        log_name: str

    async def update(self):
        updated_list = {}
        async with httpx.AsyncClient() as client:
            updates: list[UpdateManager.UpdateEntry] = [
                UpdateManager.UpdateEntry(self.query_config_url, RES_PATH / 'query' / 'config.json', 'Query Config'),
                UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/update/worldflipper/data/character'), DATA_PATH / 'worldflipper/object' / 'character.json', 'Character Data'),
                UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/update/worldflipper/data/equipment'), DATA_PATH / 'worldflipper/object' / 'equipment.json', 'Equipment Data'),
                UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/update/worldflipper/alias/character'), RES_PATH / 'worldflipper/alias' / 'character.json', 'Character Alias'),
                UpdateManager.UpdateEntry(urllib.parse.urljoin(self.url, '/bot/update/worldflipper/alias/equipment'), RES_PATH / 'worldflipper/alias' / 'equipment.json', 'Equipment Alias'),
            ]
            for update_ in updates:
                logger.info(f'从{update_.url}获取{update_.log_name}...')
                success = await self.get_single_file(client, update_.url, update_.path)
                if not success:
                    updated_list[update_.log_name] = False
                    logger.warning(f'更新{update_.log_name}失败')
                else:
                    updated_list[update_.log_name] = True
                    logger.info(f'已更新{update_.log_name}!')
        return updated_list

async def to_me(event: Union[Onebot11MessageEvent, RedMessageEvent]):
    return event.to_me

on_receive_update = on_fullmatch('更新', rule=Rule(to_me))


@on_receive_update.handle()
async def _(bot: Bot, event: Union[Onebot11MessageEvent, RedMessageEvent]):
    ulist = await manager.update()
    await bot.send(
        event,
        f'更新完毕\n成功: \n' +
        '\n'.join([str(k) for k, v in filter(lambda x: x[1], ulist.items())]) +
        '\n失败: \n' +
        '\n'.join([str(k) for k, v in filter(lambda x: not x[1], ulist.items())])
    )


manager = UpdateManager()
