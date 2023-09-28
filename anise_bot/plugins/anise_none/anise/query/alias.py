from typing import Optional
from pygtrie import CharTrie, Trie
from pypinyin import lazy_pinyin

from ..object import GameObject


class AliasManager:
    def __init__(self):
        self.alias2obj: CharTrie[str, GameObject] = CharTrie()
        self.pyalias2obj: Trie[str, GameObject] = Trie(separator='-')

    def get_obj(self, s: str) -> Optional[GameObject]:
        return self.alias2obj.get(s)

    def add(self, alias: str, obj: GameObject):
        self.alias2obj[alias] = obj
        self.pyalias2obj['-'.join(lazy_pinyin(alias))] = obj

    def clear(self):
        self.alias2obj.clear()
        self.pyalias2obj.clear()

    def guess(self, s: str) -> Optional[GameObject]:
        if s in self.alias2obj:
            return self.get_obj(s)
        else:
            self.alias2obj.items('')
