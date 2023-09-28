from enum import Enum

from .set import QuerySet


class CardBuilder:
    class ResultType(Enum):
        FAILED = 0
        SUCCESS = 1
        GUESS = 2

    def __init__(self):
        self.kwargs = dict()


class QueryManager:
    def __init__(self):
        self.query_map: list[dict] = list()
        self.query_types: dict[str, type[QuerySet]] = dict()

    def init(self) -> int:
        """
        :return: query map 的长度
        """
        self.query_map.clear()
        return len(self.query_map)

    def register(self, type_id: str, query_type: type[QuerySet]):
        self.query_types[type_id] = query_type

    async def query(self, text: str, query_map: list[dict] = None):
        pass

    async def read_query_set(self, query_set: dict):
        pass
