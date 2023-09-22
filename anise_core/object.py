import abc
from collections import defaultdict

from PI import Image
L

class GameObject:

    def __init__(self):
        self.resource_id: str = ''

    def res_img(self, res_group: str, suffix: str = None) -> Image.Image:
        """
        返回图像资源
        """

class ManagerBase:
    def __init__(self):
        self.data_dict: dict[type[GameObject], dict[str, GameObject]] = defaultdict(lambda: defaultdict(None))

    def register_type(self, t: type[GameObject]):
        pass

    def register(self, id_: str, obj: GameObject):
        pass
