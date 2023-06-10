#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from nonebot.adapters.onebot.v12 import Adapter as ONEBOT_V12Adapter
from nonebot.adapters.console import Adapter as CONSOLE_Adapter

# Custom your logger
# 
from nonebot.log import logger, default_format
logger.add(
    "logs/error.log",
    rotation="00:00",
    diagnose=False,
    level="ERROR",
    format=default_format,
    encoding='utf-8'
)

# You can pass some keyword args config to init function
nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)
# driver.register_adapter(CONSOLE_Adapter)
# driver.register_adapter(ONEBOT_V12Adapter)

sys.path.append(str(Path(__file__).resolve().parents[1]))

# nonebot.load_builtin_plugins("echo")

# Please DO NOT modify this file unless you know what you are doing!
# As an alternative, you should use command `nb` or modify `pyproject.toml` to load plugins
nonebot.load_from_toml("pyproject.toml")

# Modify some config / config depends on loaded configs
# 
# config = driver.config
# do something...


if __name__ == "__main__":
    nonebot.logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
