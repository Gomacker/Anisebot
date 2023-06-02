import json
import math
import os
from typing import Tuple

from PIL import Image, ImageDraw

from anise_core import RES_PATH

LEVEL_CAP: dict = {
    1: [40, 12, 5, 0.4, 0.4],
    2: [50, 10, 5, 0.5, 0.5],
    3: [60, 8, 5, 0.8, 0.8],
    4: [70, 6, 5, 1.5, 1.5],
    5: [80, 4, 5, 3, 3]
}

EVOLUTION_STATUS: dict = {
    1: [30, 150, 0, 0],
    2: [40, 200, 0, 0],
    3: [50, 250, 0, 0],
    4: [54, 270, 0, 0],
    5: [60, 300, 0, 0]
}


class Element:
    """
    属性类
    """
    def __init__(self, id_: int, inner_id: str, en_name: str, name: str):
        self.id = id_
        self.inner_id = inner_id
        self.en_name = en_name
        self.name = name

    @property
    def icon(self):
        return Image.open(RES_PATH / 'worldflipper' / 'ui/icon/normal' / f'{self.en_name}.png')

    @property
    def desc_icon(self):
        return Image.open(RES_PATH / 'worldflipper' / 'ui/icon/desc' / f'{self.en_name}.png')


class Elements:
    NONE = Element(-1, '(None)', 'none', '无属性')
    FIRE = Element(0, 'Red', 'fire', '火属性')
    WATER = Element(1, 'Blue', 'water', '水属性')
    THUNDER = Element(2, 'Yellow', 'thunder', '雷属性')
    WIND = Element(3, 'Green', 'wind', '风属性')
    LIGHT = Element(4, 'White', 'light', '光属性')
    DARK = Element(5, 'Black', 'dark', '暗属性')

    @staticmethod
    def get(id_):
        # id_ = id_.lower()
        if isinstance(id_, int):
            if id_ in id2ele:
                return id2ele[id_]
            else:
                return Elements.NONE
        elif isinstance(id_, str):
            if id_ in str2ele:
                return str2ele[id_]
            else:
                return Elements.NONE
        else:
            return Elements.NONE


id2ele = dict()
str2ele = dict()
for _k, _v in vars(Elements).items():
    if not _k.startswith('__') and not _k == 'get':
        id2ele[_v.id] = _v
        str2ele[_v.en_name] = _v


class WorldflipperObject:
    def __init__(self, source_id: str, id_: int, extractor_id: str = ''):
        self.source_id: str = source_id
        self._id: int = id_
        self.extractor_id = extractor_id
        self._roster = []

    @property
    def id(self):
        return self._id

    def res(self, res_group) -> Image.Image:
        img = Image.new('RGBA', (82, 82))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), f'Invalid Resource\n{res_group}\n{self.__class__}:\n{self.id}')
        return img

    def res_exists(self, res_group) -> bool:
        return False

    @property
    def main_roster(self) -> list[str]:
        return []

    @property
    def roster(self) -> list[str]:
        """未完成&准备弃用"""
        return self.main_roster + self._roster

    @property
    def name(self):
        return self.roster[0]

    def __bool__(self):
        return bool(self.id)

    @property
    def rarity(self) -> int:
        return 0

    def icon(self, **kwargs) -> Image.Image:
        return self.res('')


class Unit(WorldflipperObject):
    def __init__(self, source_id: str, id_: int, data: dict):
        super().__init__(source_id, int(id_), data['extraction_id'])
        self._data = data

    @property
    def wf_id(self) -> str:
        return self._data['wf_id']

    def data(self) -> dict:
        return self._data.copy()

    @property
    def zh_name(self) -> str:
        return self._data['name'][0]

    @property
    def sub_name(self) -> str:
        return self._data['name'][1]

    @property
    def jp_name(self) -> str:
        return self._data['name'][2]

    @property
    def legacy_id(self) -> str:
        return self._data['legacy_id']

    @property
    def element(self) -> Element:
        ele = self._data['element']
        return Elements.get(ele)

    @property
    def rarity(self):
        return self._data['rarity']

    @property
    def type(self):
        return self._data['type']

    @property
    def pf_type(self):
        return self._data['pf_type']

    @property
    def race(self):
        return self._data['race']

    @property
    def gender(self):
        return self._data['gender']

    @property
    def stance(self):
        return self._data['stance']

    @property
    def cv(self):
        return self._data['cv']

    @property
    def skill_name(self) -> str:
        return self._data[f'skill_name']

    @property
    def skill_description(self) -> str:
        return self._data[f'skill_description']

    @property
    def skill_weight(self) -> str:
        return self._data[f'skill_weight']

    def _ability(self, index) -> str:
        return self._data[f'ability{index}']

    @property
    def leader_ability_name(self) -> str:
        return self._data['leader_ability_name']

    @property
    def leader_ability(self) -> str:
        return self._data['leader_ability']

    @property
    def ability1(self) -> str:
        return self._ability(1)

    @property
    def ability2(self) -> str:
        return self._ability(2)

    @property
    def ability3(self) -> str:
        return self._ability(3)

    @property
    def ability4(self) -> str:
        return self._ability(4)

    @property
    def ability5(self) -> str:
        return self._ability(5)

    @property
    def ability6(self) -> str:
        return self._ability(6)

    def res(self, res_group, suffix=None) -> Image.Image:
        """
        尝试返回对应的图像资源，当有GIF格式时优先返回GIF，否则尝试返回PNG，其次JPEG
        :param res_group: 资源组
        :param suffix: 文件后缀
        :return: 对应的资源
        """
        path = RES_PATH / 'worldflipper' / 'unit' / res_group / f'{self.extractor_id}'
        if suffix:
            if os.path.exists(f'{path}.{suffix}'):
                return Image.open(f'{path}.{suffix}')
            else:
                return super().res(res_group)
        if os.path.exists(f'{path}.gif'):
            return Image.open(f'{path}.gif')
        elif os.path.exists(f'{path}.png'):
            return Image.open(f'{path}.png')
        elif os.path.exists(f'{path}.jpg'):
            return Image.open(f'{path}.jpg').convert('RGBA')
        else:
            return super().res(res_group)

    def res_exists(self, res_group, suffix=None) -> bool:
        path = RES_PATH / 'worldflipper' / 'unit' / res_group / f'{self.extractor_id}'
        if suffix:
            return os.path.exists(f'{path}.{suffix}')
        else:
            return \
                os.path.exists(f'{path}.gif') or \
                os.path.exists(f'{path}.png') or \
                os.path.exists(f'{path}.jpg')

    def icon(self, awakened=False, size=88, with_frame=True) -> Image.Image:
        res_group = f'square212x/{"awakened" if awakened else "base"}'
        pic = self.res(res_group)
        pic = pic.resize((212, 212), Image.NONE)
        if self.res_exists(res_group):
            if with_frame:
                bg = Image.open(RES_PATH / 'worldflipper' / 'ui' / 'unit_background.png')
                frame = Image.open(RES_PATH / 'worldflipper' / 'ui' / 'unit_frame.png')
                star_in_frame = Image.open(
                    RES_PATH / 'worldflipper' / 'ui' / 'star_in_frame' / f'star{self.rarity}inf.png')
                ele: Image.Image = self.element.icon
                canvas = Image.new('RGBA', (240, 240))
                canvas.paste(bg, (14, 14), bg)
                temp = Image.new('RGBA', pic.size)
                temp.paste(pic)
                canvas.paste(pic, (14, 14), temp)
                canvas.paste(frame, (0, 0), frame)
                canvas.paste(star_in_frame, (0, 0), star_in_frame)
                canvas.paste(ele, (182, 13), ele)
                pic = canvas
            if size > 0:
                pic = pic.resize((size, size), Image.LANCZOS)

        return pic

    @property
    def main_roster(self) -> list[str]:
        """
        返回主要名称(简中名, 称号名, 日服名)
        :return:
        """
        return [
            self.zh_name,
            self.sub_name,
            self.jp_name
        ]

    def status_data(self) -> dict:
        return json.loads(self._data['status_data'])

    @property
    def nature_max_level(self) -> int:
        return LEVEL_CAP.get(self.rarity, [0])[0]

    def get_cap_count(self, level) -> int:
        nml = self.nature_max_level
        return 0 if level <= nml else math.ceil((level - nml) / LEVEL_CAP.get(self.rarity)[2])

    @property
    def cap_rate(self) -> float:
        return LEVEL_CAP[self.rarity][3] / 100

    def _calculate_status(self, start, end, level_start, level_end, level, evolution):
        value = math.ceil(start + (((end - start) / (level_end - level_start)) * (level - level_start)))
        value = math.ceil(value * (1 + (self.get_cap_count(level) * self.cap_rate)))
        value = value + int(evolution)
        return value

    def get_status(self, level: int) -> Tuple[int, int]:
        status_data = self.status_data()
        mhp: int = 0
        atk: int = 0
        level = max(0, min(100, level))
        if level in range(80, 100 + 1):
            sd1 = [int(x) for x in status_data['80']]
            sd2 = [int(x) for x in status_data['100']]
            mhp = self._calculate_status(sd1[0], sd2[0], 80, 100, level, EVOLUTION_STATUS[self.rarity][1])
            atk = self._calculate_status(sd1[1], sd2[1], 80, 100, level, EVOLUTION_STATUS[self.rarity][0])

        elif level in range(10, 80):
            sd1 = [int(x) for x in status_data['10']]
            sd2 = [int(x) for x in status_data['80']]
            mhp = self._calculate_status(sd1[0], sd2[0], 10, 80, level, EVOLUTION_STATUS[self.rarity][1] if level >= self.nature_max_level else 0)
            atk = self._calculate_status(sd1[1], sd2[1], 10, 80, level, EVOLUTION_STATUS[self.rarity][0] if level >= self.nature_max_level else 0)
        elif level in range(1, 10):

            sd1 = [int(x) for x in status_data['1']]
            sd2 = [int(x) for x in status_data['10']]
            mhp = self._calculate_status(sd1[0], sd2[0], 1, 10, level, 0)
            atk = self._calculate_status(sd1[1], sd2[1], 1, 10, level, 0)
        return mhp, atk


class Armament(WorldflipperObject):
    def __init__(self, source_id: str, id_: int, data: dict):
        super().__init__(source_id, int(id_), data['extraction_id'])
        self._data = data

    def data(self) -> dict:
        return self._data.copy()

    @property
    def zh_name(self) -> str:
        return self._data['name'][0]

    @property
    def jp_name(self) -> str:
        return self._data['name'][1]

    def res(self, res_group, suffix=None) -> Image.Image:
        """
        尝试返回对应的图像资源，当有GIF格式时优先返回GIF，否则尝试返回PNG，其次JPEG
        :param res_group: 资源组
        :param suffix: 文件后缀
        :return: 对应的资源
        """
        path = RES_PATH / 'worldflipper' / 'armament' / res_group / f'{self.extractor_id}'
        if suffix:
            if os.path.exists(f'{path}.{suffix}'):
                return Image.open(f'{path}.{suffix}')
            else:
                return super().res(res_group)
        if os.path.exists(f'{path}.gif'):
            return Image.open(f'{path}.gif')
        elif os.path.exists(f'{path}.png'):
            return Image.open(f'{path}.png')
        elif os.path.exists(f'{path}.jpg'):
            return Image.open(f'{path}.jpg')
        else:
            return super().res(res_group)

    def res_exists(self, res_group, suffix=None) -> bool:
        path = RES_PATH / 'worldflipper' / 'armament' / res_group / f'{self.extractor_id}'
        if suffix:
            return os.path.exists(f'{path}.{suffix}')
        else:
            return \
                os.path.exists(f'{path}.gif') or \
                os.path.exists(f'{path}.png') or \
                os.path.exists(f'{path}.jpg')

    def icon(self, awakened=False, size=88, with_frame=True) -> Image.Image:
        res_group = f'generated/{"core" if awakened else "normal"}'
        pic = self.res(res_group)
        pic = pic.resize((212, 212), Image.NONE)
        if self.res_exists(res_group):
            if with_frame:
                bg = Image.open(RES_PATH / 'worldflipper' / 'ui' / 'unit_background.png')
                frame = Image.open(RES_PATH / 'worldflipper' / 'ui' / 'unit_frame.png')
                star_in_frame = Image.open(
                    RES_PATH / 'worldflipper' / 'ui' / 'star_in_frame' / f'star{self.rarity}inf.png')
                ele: Image.Image = self.element.icon
                canvas = Image.new('RGBA', (240, 240))
                canvas.paste(bg, (14, 14), bg)
                canvas.paste(pic, (14, 14), pic)
                canvas.paste(frame, (0, 0), frame)
                canvas.paste(star_in_frame, (0, 0), star_in_frame)
                canvas.paste(ele, (182, 13), ele)
                pic = canvas
            if size > 0:
                pic = pic.resize((size, size), Image.LANCZOS)

        return pic

    @property
    def anise_id(self):
        return self._data['anise_id']

    @property
    def element(self):
        ele = self._data['element']
        return Elements.get(ele)

    @property
    def rarity(self):
        return self._data['rarity']

    @property
    def main_roster(self) -> list[str]:
        """
        返回主要名称(简中名, 称号名, 日服名)
        :return:
        """
        return [
            self.zh_name,
            self.jp_name
        ]
