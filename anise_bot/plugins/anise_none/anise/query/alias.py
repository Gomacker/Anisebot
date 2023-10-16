from pathlib import Path
from typing import Optional, Callable

import toml
from pygtrie import CharTrie, Trie
from pypinyin import lazy_pinyin
from fuzzywuzzy import process

from ..manager import manager
from ...models.worldflipper import Character, Equipment
from ..config import RES_PATH
from ..object import GameObject


class AliasManager:
    def __init__(self):
        self.alias2obj: CharTrie[str, GameObject] = CharTrie()
        # self.pyalias2obj: Trie[str, GameObject] = Trie(separator='-')

    def init_from_toml(self, path: Path, obj_getter: Callable[[str], GameObject]):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(toml.dumps({}))
        d: dict = toml.loads(path.read_text('utf-8'))
        for id_, names in d.items():
            for n in names:
                if n in self.alias2obj:
                    continue
                if not isinstance(n, str):
                    continue
                if not n:
                    continue
                self.add(n, obj_getter(id_))

    def init(self):
        self.init_from_toml(RES_PATH / 'alias' / 'character.toml', lambda x: manager.get(Character, x))
        self.init_from_toml(RES_PATH / 'alias' / 'equipment.toml', lambda x: manager.get(Equipment, x))
        for t in [Character, Equipment]:
            for id_, obj in manager.dict_of(t).items():
                for name in obj.names:
                    if name in self.alias2obj:
                        continue
                    if not name:
                        continue
                    self.add(name, obj)

    def get_obj(self, s: str) -> Optional[GameObject]:
        return self.alias2obj.get(s)

    def add(self, alias: str, obj: GameObject):
        self.alias2obj[alias] = obj
        # self.pyalias2obj['-'.join(lazy_pinyin(alias))] = obj

    def clear(self):
        self.alias2obj.clear()
        # self.pyalias2obj.clear()

    def guess(self, s: str) -> Optional[GameObject]:
        name, score = process.extractOne(s, self.alias2obj.keys())
        print(name, score)
        if score >= 60:
            return self.alias2obj[name]
        return None
        # if s in self.alias2obj:
        #     return self.get_obj(s)
        # else:
        #     for i in reversed(range(len(s))):
        #         self.alias2obj.items(prefix='')


alias_manager = AliasManager()

alias_manager.init()

if __name__ == '__main__':
    print('aa')
