import abc
import re
from typing import Any

from PIL import Image
from pydantic import BaseModel

from ..config import RES_PATH


class QuerySet(BaseModel, metaclass=abc.ABCMeta):
    def __init__(self, **data: Any):
        super().__init__(**data)

    @abc.abstractmethod
    async def get(self, text: str) -> Any:
        return None


class QuerySetBase(QuerySet, metaclass=abc.ABCMeta):
    regex: str = ''

    def __init__(self, **data: Any):
        super().__init__(**data)

    async def get(self, text: str) -> Any:
        if not self.regex or re.findall(self.regex, text):
            return self._get(text)

    @abc.abstractmethod
    async def _get(self, text: str) -> Any:
        return None


class QueryObjects(QuerySetBase):
    async def _get(self, text: str) -> Any:
        pass


class QueryText(QuerySetBase):
    content = ''

    async def _get(self, text: str) -> str | None:
        return self.content


class QueryImage(QuerySetBase):
    src = ''

    async def _get(self, text: str) -> Image.Image | None:
        path = RES_PATH / self.src
        try:
            img = Image.open(path)
            return img
        except:
            return None
