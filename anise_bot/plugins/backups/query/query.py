import typing
from typing import Union

from .sets import QueryText, QuerySchedule, QueryImage, QueryObjects, QueryServerImage, QueryServerTable, QuerySet, \
    QueryPartyPage, QueryPartyRefer
from ...utils import get_send_content

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
        self.query_map: list[dict] = list()
        self.query_types: dict[str, type[QuerySet]] = dict()

    def init(self) -> int:
        self.query_map.clear()
        path = RES_PATH / 'query' / 'config.json'
        os.makedirs(path.parent, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({'query_map': []}), 'utf-8')
        self.query_map += json.loads(path.read_text('utf-8')).get('query_map', [])

        self.query_types.clear()
        self.register('text', QueryText)
        self.register('schedule', QuerySchedule)
        self.register('image', QueryImage)
        self.register('wfo', QueryObjects)
        self.register('pps', QueryPartyPage)
        self.register('server_image', QueryServerImage)
        self.register('server_table', QueryServerTable)
        self.register('party_refer', QueryPartyRefer)

        return len(self.query_map)

    def register(self, type_id: str, query_type: type[QuerySet]):
        self.query_types[type_id] = query_type

    async def query(self, text: str, query_map: list[dict] = None) -> Union[Message, None]:
        if query_map is None:
            query_map = self.query_map
        for q in query_map:
            if ('regex' in q and re.findall(q['regex'], text)) or 'regex' not in q:
                rst = await self.read_query_set(q, text)
                if rst:
                    return rst
        return get_send_content('worldflipper.query.failed')

    async def read_query_set(self, query_set: dict, text: str) -> typing.Union[Message, MessageSegment, None]:
        if 'type' in query_set and query_set['type'] in self.query_types:
            QT: type[QuerySet] = self.query_types[query_set['type']]
            return await QT(query_set).get_message(text)
        return None


query_manager: QueryManager = QueryManager()
