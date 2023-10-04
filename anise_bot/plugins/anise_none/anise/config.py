import json
import os
from pathlib import Path


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

message_contents_path = CONFIG_PATH / 'message_contents.json'
message_contents_path.parent.mkdir(parents=True, exist_ok=True)
if not message_contents_path.exists():
    message_contents_path.write_text('{}')
message_contents: dict = json.loads(message_contents_path.read_text(encoding='utf-8'))
