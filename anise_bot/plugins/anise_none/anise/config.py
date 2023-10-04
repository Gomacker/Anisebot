import json
import os
import urllib.parse
from pathlib import Path

import toml
from pydantic import BaseModel

ROOT_PATH = Path('.').parent
RES_PATH = ROOT_PATH.parent / 'res'
os.makedirs(RES_PATH, exist_ok=True)
DATA_PATH = ROOT_PATH.parent / 'data'
os.makedirs(DATA_PATH, exist_ok=True)
CONFIG_PATH = ROOT_PATH.parent / 'config'
os.makedirs(CONFIG_PATH, exist_ok=True)
METEORHOUSE_URL = 'https://meteorhouse.wiki'
CALENDAR_URL = 'https://wf-calendar.miaowm5.com'

MAIN_URL = METEORHOUSE_URL

_message_contents_path = CONFIG_PATH / 'message_contents.json'
_message_contents_path.parent.mkdir(parents=True, exist_ok=True)
if not _message_contents_path.exists():
    _message_contents_path.write_text('{}')
message_contents: dict = json.loads(_message_contents_path.read_text(encoding='utf-8'))


class QueryConfig(BaseModel):
    config_url: str = urllib.parse.urljoin(METEORHOUSE_URL, '/static/worldflipper/query/config.json')
    update_on_startup = False
    query_prefixes: list = ['qr', '/qr', '查询', '/']
    worldflipper_party_query_prefixes: list = ['pqr', '/pqr', '查盘', '茶盘', '#']


class Config(BaseModel):
    query: QueryConfig = QueryConfig.parse_obj({})


_config_path = CONFIG_PATH / 'config.toml'
_config_path.parent.mkdir(parents=True, exist_ok=True)
if not _config_path.exists():
    _config_path.write_text(toml.dumps(Config(**{}).dict()), encoding='utf-8')

config: Config = Config.parse_obj(toml.loads(_config_path.read_text('utf-8')))


print(config)
