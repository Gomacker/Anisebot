from collections import defaultdict
from pathlib import Path

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os

import pygtrie
import unicodedata
import zhconv as zhconv
from fuzzywuzzy import process
from nonebot import logger

from anise_core import RES_PATH
from anise_core.worldflipper.manager import UNKNOWN


class NicknameMaster:
    def __init__(self):
        self.names: dict[str, list] = defaultdict(list)
        self.data_path_unit = RES_PATH / 'worldflipper' / 'roster' / 'roster_unit.json'
        self.data_path_armament = RES_PATH / 'worldflipper' / 'roster' / 'roster_armament.json'
        self.__load_data()
        self.__self_check()
        # print(self.names)

    def __self_check(self):
        for id_ in self.names:
            if '' in self.names[id_]:
                self.names[id_].remove('')
        # self.__save_data()

    def __load_data(self):
        if not self.data_path_unit.exists():
            os.makedirs(self.data_path_unit.parent, exist_ok=True)
            self.data_path_unit.write_text(json.dumps({}))
        with open(self.data_path_unit, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        for id_ in data:
            self.names[f'u{id_}'] += data[id_]

        if not self.data_path_armament.exists():
            os.makedirs(self.data_path_armament.parent, exist_ok=True)
            self.data_path_armament.write_text(json.dumps({}))
        with open(self.data_path_armament, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        for id_ in data:
            self.names[f'a{id_}'] += data[id_]

    def __save_data(self):
        with open(self.data_path_unit, 'w+', encoding='utf-8') as f:
            json.dump({k[1:]: v for k, v in filter(lambda x: x[0].startswith('u'), self.names.items())}, f, ensure_ascii=False, indent=2)
        with open(self.data_path_armament, 'w+', encoding='utf-8') as f:
            json.dump({k[1:]: v for k, v in filter(lambda x: x[0].startswith('a'), self.names.items())}, f, ensure_ascii=False, indent=2)


class NicknameMasterOrigin(NicknameMaster):
    def __init__(self, unit_path: Path, armament_path: Path):
        super().__init__()
        self.data_path_unit: Path = unit_path
        self.data_path_armament: Path = armament_path
        self.__self_check()
        # print(self.names)

    def __self_check(self):
        for id_ in self.names:
            if '' in self.names[id_]:
                self.names[id_].remove('')

    def __load_data(self):
        if self.data_path_unit.exists():
            data: dict = json.loads(self.data_path_unit.read_text('utf-8'))
            for id_, value in data.items():
                print(self.names)
                print(value)
                self.names[f'u{id_}'] += value['name']

    def __save_data(self):
        pass


class Roster:
    def __init__(self):
        self._roster: pygtrie.CharTrie = pygtrie.CharTrie()
        self._id2names = defaultdict(list)
        self._all_name_list = set()

    def clear(self):
        self._roster.clear()

    def update(self, nickname_master: NicknameMaster):
        name_data = nickname_master.names
        for idx, names in name_data.items():
            for n in names:
                # print(n)
                n = normalize_str(n)
                if n:
                    if n not in self._roster:
                        self._id2names[idx].append(n)
                        self._roster[n] = idx
                    else:
                        logger.warning(f'Roster: 出现重名{n}于id{idx}与id{self._roster[n]}')
                        pass
        self._all_name_list = self._roster.keys()

    @property
    def size(self):
        return len(self._all_name_list)

    def get_nicknames(self, id_):
        return self._id2names[id_]

    def get_id(self, name):
        return self._roster[name] if name in self._roster else UNKNOWN

    def guess_id(self, name):
        name, score = process.extractOne(name, self._all_name_list)
        return self._roster[name], score, name


def normalize_str(s) -> str:
    s = unicodedata.normalize('NFKC', s)
    s = s.lower()
    s = zhconv.convert(s, 'zh-hans')
    return s
