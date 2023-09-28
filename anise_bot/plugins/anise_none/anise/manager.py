from collections import defaultdict

from .object import GameObject


class AniseStar:
    pass


class ManagerBase:
    def __init__(self):
        self.data_dict: dict[type[GameObject], dict[str, GameObject]] = defaultdict(lambda: defaultdict(None))
        # self.res: ResourceManager = ResourceManager()

    def register_type(self, t: type[GameObject]):
        pass

    def register(self, id_: str, obj: GameObject):
        pass


manager = ManagerBase()
