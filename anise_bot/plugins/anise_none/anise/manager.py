from collections import defaultdict
from typing import TypeVar, Optional

from .object import GameObject


class AniseStar:
    pass


T: TypeVar = TypeVar('T')


class ManagerBase:
    def __init__(self):
        self.objects: dict[str, dict[str, T]] = dict()

    def register_type(self, t: type[GameObject]):
        self.objects[t.type_id()] = defaultdict(None)

    def register(self, id_: str, obj: GameObject):
        try:
            self.objects[obj.type_id()][id_] = obj
        except:
            raise Exception('type not registered')

    def get(self, type_: T, id_: str) -> Optional[T]:
        try:
            assert issubclass(type_, GameObject)
            return self.objects[type_.type_id()].get(id_)
        except:
            return None

    def dict_of(self, type_: T) -> Optional[dict[str, T]]:
        assert issubclass(type_, GameObject)
        return self.objects.get(type_.type_id())


manager = ManagerBase()
