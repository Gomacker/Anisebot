import abc
import asyncio
import json
import os
import re
import time
import urllib.parse
from typing import Any, Optional, Type

from nonebot import logger
from pydantic import BaseModel

from anise_core import DATA_PATH, RES_PATH

if __name__ == '__main__':
    from utils import MessageCard, ImageHandlerLocalFile, ImageHandlerNetwork, ImageHandlerPageScreenshot
else:
    from .utils import MessageCard, ImageHandlerLocalFile, ImageHandlerNetwork, ImageHandlerPageScreenshot


class QueryHandler(BaseModel, abc.ABC):
    """用来代替 QuerySet"""
    type: str

    def __init__(self, **data: Any):
        super().__init__(**data)

    def check(self, text: str) -> bool:
        return False

    @abc.abstractmethod
    async def get_message(self) -> Optional[MessageCard]:
        return None


class QueryHandlerRegex(QueryHandler, abc.ABC):
    regex: str = ''

    def check(self, text: str) -> bool:
        return not self.regex or bool(re.search(self.regex, text))


class QueryHandlerText(QueryHandlerRegex):
    content: str = ''

    async def get_message(self) -> Optional[MessageCard]:
        mc = MessageCard()
        mc.text = self.content
        return mc


class QueryHandlerImage(QueryHandlerRegex):
    src: str = ''

    async def get_message(self) -> Optional[MessageCard]:
        return MessageCard(image_handler=ImageHandlerLocalFile(RES_PATH / 'query' / 'local' / self.src))


class QueryHandlerServerImage(QueryHandlerRegex):
    url: str = ''

    async def get_message(self) -> Optional[MessageCard]:
        mc = MessageCard()
        mc.image_handler = ImageHandlerNetwork(self.url)
        return mc


class QueryHandlerServerTable(QueryHandlerRegex):
    table_id: str = ''

    async def get_message(self) -> Optional[MessageCard]:
        ih = ImageHandlerPageScreenshot(
            f'{"https://meteorhouse.wiki".removesuffix("/")}/card/table/?table_id={self.table_id}&show_replacements=true',
            selector='.table'
        )
        mc = MessageCard(image_handler=ih)
        return mc


class QueryHandlerWorldflipperObject(QueryHandler):
    strict: bool = True

    def check(self, text: str) -> bool:
        return False

    async def get_message(self) -> Optional[MessageCard]:
        pass


class QueryHandlerWorldflipperScheduler(QueryHandlerRegex):
    async def get_message(self) -> Optional[MessageCard]:
        pass


class QueryHandlerWorldflipperPurePartySearcher(QueryHandlerRegex):
    async def get_message(self) -> Optional[MessageCard]:
        pass


class QueryManager:

    def __init__(self):
        self.registered_handler_type: dict[str, Type[QueryHandler]] = {}
        self.query_handlers: list[QueryHandler] = []

    def register(self, handler_type: Type[QueryHandler], name: str):
        self.registered_handler_type[name] = handler_type

    def read_query_handler(self, data: dict) -> Optional[QueryHandler]:
        type_ = data.get('type', '')
        if not type_:
            return None
        TQH: Type[QueryHandler] = self.registered_handler_type.get(type_)
        if not TQH:
            logger.error(f"QueryManager can't read type: {type_}")
            return None
        return TQH(**data)

    def init(self, path=RES_PATH):
        config_path = path / 'query' / 'config.json'
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            config_path.write_text(json.dumps({'query_map': []}))
        query_config: list = json.loads(config_path.read_text('utf-8')).get('query_map', '')
        self.query_handlers: list = list(filter(None, [self.read_query_handler(x) for x in query_config]))
        # print('\n'.join([y.json(ensure_ascii=False) for y in filter(None, [self.read_query_handler(x) for x in query_config])]))

    def load_default_type(self):
        self.register(QueryHandlerText, 'text')
        self.register(QueryHandlerText, 'Text')

        self.register(QueryHandlerImage, 'image')
        self.register(QueryHandlerImage, 'Image')
        self.register(QueryHandlerImage, 'local_image')
        self.register(QueryHandlerImage, 'LocalImage')
        self.register(QueryHandlerImage, 'image_local')
        self.register(QueryHandlerImage, 'ImageLocal')

        self.register(QueryHandlerServerImage, 'server_image')
        self.register(QueryHandlerServerImage, 'ServerImage')
        self.register(QueryHandlerServerImage, 'image_server')
        self.register(QueryHandlerServerImage, 'ImageServer')

        self.register(QueryHandlerServerTable, 'server_table')
        self.register(QueryHandlerServerTable, 'ServerTable')

    def load_worldflipper_type(self):

        self.register(QueryHandlerWorldflipperScheduler, 'schedule')
        self.register(QueryHandlerWorldflipperScheduler, 'Schedule')

        self.register(QueryHandlerWorldflipperObject, 'wfo')
        self.register(QueryHandlerWorldflipperObject, 'WorldflipperObject')
        self.register(QueryHandlerWorldflipperObject, 'worldflipper_object')

        # self.register(QueryHandler, 'party_refer')
        # self.register(QueryHandler, 'PartyRefer')

        self.register(QueryHandlerWorldflipperPurePartySearcher, 'pps')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'PurePartySearcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'pure_party_searcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'PartySearcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'party_searcher')

    async def query(self, text: str) -> Optional[MessageCard]:
        t = time.time()
        try:
            for handler in self.query_handlers:
                if handler.check(text):
                    mc = await handler.get_message()
                    if mc:
                        return mc
            else:
                return None
        except Exception as e:
            raise e


_QM = None


def get_query() -> QueryManager:
    global _QM
    if _QM is None:
        _QM = QueryManager()
        _QM.load_default_type()
        _QM.load_worldflipper_type()
        _QM.init()
    return _QM


if __name__ == '__main__':
    async def main():
        t = time.time()
        # print(f'(耗时{"%.2f" % (time.time() - t)}s)')
        qm = get_query()
        mc = await qm.query('雷废')
        print(mc)
        # for query_handler in qm.query_handlers:
        #     print(query_handler)


    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    asyncio.set_event_loop(loop)
