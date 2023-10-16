from pathlib import Path

import nonebot
from nonebot import get_driver

from .config import Config

global_config = get_driver().config
config: Config = Config.parse_obj(global_config)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)
