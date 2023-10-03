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
