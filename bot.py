import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

from nonebot.adapters.red import Adapter as REDPROTOCOLAdapter

from nonebot.log import logger, default_format
logger.add(
    "logs/error.log",
    rotation="00:00",
    diagnose=False,
    level="ERROR",
    format=default_format,
    encoding='utf-8'
)


nonebot.init()

# app = nonebot.get_asgi()
driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

driver.register_adapter(REDPROTOCOLAdapter)

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()

nonebot.load_from_toml("pyproject.toml")

# if __name__ == "__main__":
#     sys.path.append(str(Path(__file__).resolve().parents[1]))
#     nonebot.run(app="__mp_main__:app")
