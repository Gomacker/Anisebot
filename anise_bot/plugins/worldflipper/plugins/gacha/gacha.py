try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import random

from anise_core import CONFIG_PATH
from anise_core.worldflipper import wfm, WorldflipperObject

GACHA_POOL_CONFIG = CONFIG_PATH / 'worldflipper' / 'gacha' / 'config.json'
GACHA_POOL_CONFIG_PATH = CONFIG_PATH / 'worldflipper' / 'gacha' / 'pool'


class Gacha:
    def __init__(self, pool_name: str):
        self.type = 'unit'
        self.up5_prob_single = 0
        self.up4_prob_single = 0
        self.up3_prob_single = 0
        self.star5_prob = 0
        self.star4_prob = 0
        self.star5_up = []
        self.star4_up = []
        self.star3_up = []
        self.star5 = []
        self.star4 = []
        self.star3 = []

        self.init_pool(pool_name)

    def init_pool(self, pool_name: str):
        path = GACHA_POOL_CONFIG_PATH / f'{pool_name}.json'
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            path = path.parent / 'default.json'
            if not path.exists():
                units = wfm.units()
                path.write_text(json.dumps({
                    'type': 'unit',
                    'up5_prob_single': 0.015,
                    'up4_prob_single': 0.025,
                    'up3_prob_single': 0.035,
                    'star5_prob': 0.05,
                    'star4_prob': 0.25,
                    'star5_up': [],
                    'star4_up': [],
                    'star3_up': [],
                    'star5': [u.id for u in filter(lambda x: x.rarity == 5, units)],
                    'star4': [u.id for u in filter(lambda x: x.rarity == 4, units)],
                    'star3': [u.id for u in filter(lambda x: x.rarity == 3, units)],
                }, ensure_ascii=False, indent=2))
        pool_data = json.loads(path.read_text('utf-8'))
        self.type = 'armament' if pool_data['type'] == 'armament' else 'unit'
        self.up5_prob_single = pool_data['up5_prob_single']
        self.up4_prob_single = pool_data['up4_prob_single']
        self.up3_prob_single = pool_data['up3_prob_single']
        self.star5_prob = pool_data['star5_prob']
        self.star4_prob = pool_data['star4_prob']
        self.star5_up = pool_data['star5_up']
        self.star4_up = pool_data['star4_up']
        self.star3_up = pool_data['star3_up']
        self.star5 = pool_data['star5']
        self.star4 = pool_data['star4']
        self.star3 = pool_data['star3']

    def random_region(self):
        r = random.random()
        if r <= self.up5_prob_single * len(self.star5_up):
            return 5  # 五星up
        elif r <= self.star5_prob:
            return 4  # 五星非up
        elif r <= self.star5_prob + (self.up4_prob_single * len(self.star4_up)):
            return 3  # 四星up
        elif r <= self.star5_prob + self.star4_prob:
            return 2  # 四星非up
        elif r <= self.star5_prob + self.star4_prob + (self.up3_prob_single * len(self.star3_up)):
            return 1  # 三星up
        else:
            return 0  # 三星非up

    def random_object(self, region) -> WorldflipperObject:

        if region == 5:
            c = random.choice(self.star5_up)
        elif region == 4:
            c = random.choice(self.star5)
        elif region == 3:
            c = random.choice(self.star4_up)
        elif region == 2:
            c = random.choice(self.star4)
        elif region == 1:
            c = random.choice(self.star3_up)
        else:
            c = random.choice(self.star3)
        if self.type == 'armament':
            return wfm.get_armament(c)
        else:
            return wfm.get_unit(c)

    def gacha_select(self, count: int) -> list[WorldflipperObject]:
        """
        :return: list[WorldflipperObject]
        """
        if count < 1:
            return []
        result = list()
        for i in range(count//10):
            sub_ten = []
            for j in range(9):
                sub_ten.append(self.random_object(self.random_region()))
            sub_ten.append(self.random_object(max(self.random_region(), 2)))
            random.shuffle(sub_ten)
            result += sub_ten
        for i in range(count % 10):
            result.append(self.random_object(self.random_region()))
        return result

