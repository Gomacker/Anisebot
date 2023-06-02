import os
from pathlib import Path

ROOT_PATH = Path(__file__).parent
RES_PATH = ROOT_PATH.parent / 'res'
os.makedirs(RES_PATH, exist_ok=True)
DATA_PATH = ROOT_PATH.parent / 'data'
os.makedirs(DATA_PATH, exist_ok=True)
CONFIG_PATH = ROOT_PATH.parent / 'config'
os.makedirs(CONFIG_PATH, exist_ok=True)

MAIN_URL = 'http://meteorhouse.wiki'
