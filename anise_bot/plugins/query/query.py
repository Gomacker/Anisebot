import io
import typing
from typing import Union

from anise_bot.service import Service
from .sets import QueryText, QuerySchedule, QueryImage, QueryObjects, QueryServerImage, QueryServerTable, QuerySet

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import re

from nonebot.adapters.onebot.v11 import MessageSegment, Message

from anise_core import RES_PATH


class QueryManager:
    def __init__(self):
        self.query_map: dict[str, dict] = dict()
        self.query_types: dict[str, type[QuerySet]] = dict()

    def init(self) -> int:
        self.query_map.clear()
        path = RES_PATH / 'query' / 'config.json'
        os.makedirs(path.parent, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({}), 'utf-8')
        self.query_map.update(json.loads(path.read_text('utf-8')))

        self.query_types.clear()
        self.register('text', QueryText)
        self.register('schedule', QuerySchedule)
        self.register('image', QueryImage)
        self.register('wfo', QueryObjects)
        self.register('server_image', QueryServerImage)
        self.register('server_table', QueryServerTable)

        return len(self.query_map)

    def register(self, type_id: str, query_type: type[QuerySet]):
        self.query_types[type_id] = query_type

    async def query(self, text: str) -> Union[Message, None]:
        for i, qs in self.query_map.items():
            for q in qs:
                if ('regex' in q and re.findall(q['regex'], text)) or 'regex' not in q:
                    rst = await self.read_query_set(q, text)
                    if rst:
                        return rst
        return Service.get_send_content('worldflipper.query.failed')

    async def read_query_set(self, query_set: dict, text: str) -> typing.Union[Message, MessageSegment, None]:
        if 'type' in query_set and query_set['type'] in self.query_types:
            QT: type[QuerySet] = self.query_types[query_set['type']]
            return await QT(query_set).get_message(text)
        return None


query_manager: QueryManager = QueryManager()
