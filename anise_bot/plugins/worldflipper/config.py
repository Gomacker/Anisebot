import os.path
from pathlib import Path

from pydantic import BaseSettings


class Config(BaseSettings):

    class Config:
        extra = "ignore"
        RES_DIR = Path(r'../res/')
