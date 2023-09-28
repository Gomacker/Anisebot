import abc
from typing import Any, Optional

from PIL import Image
from pydantic import BaseModel


class GameObject(BaseModel):
    resource_id: str = ''

    def __init__(self, resource_id: str = None, **data: Any):
        if resource_id:
            data['resource_id'] = resource_id
        super().__init__(**data)

    @classmethod
    @abc.abstractmethod
    def type_id(cls) -> str:
        return ''

    async def res(self, res_group: "ResourceGroup") -> Optional[Image.Image]:
        """
        返回资源
        """
        return await res_group.get(self)
