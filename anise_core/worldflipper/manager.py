from typing import Tuple, Union

from anise_core import DATA_PATH, RES_PATH
from anise_core.worldflipper import Unit, Armament, UNKNOWN, WorldflipperObject

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os.path
from pathlib import Path

from anise_core.statistic import StatisticManager
from anise_core.worldflipper.roster import Roster, NicknameMaster, NicknameMasterOrigin


WF_RES_PATH = RES_PATH / 'worldflipper'
WF_EXTRACTIONS_PATH = WF_RES_PATH / 'assets'
WF_DATA_PATH = DATA_PATH / 'worldflipper'
WF_ORDEREDMAP_PATH = WF_DATA_PATH / 'orderedmap'


class ServerSource:
    """
    服务器源，
    包括一个服务器的所有源数据，
    用于解决有服务器差异的角色与武器
    include: Units Armaments
    """
    def __init__(self, source_id, spare_data_path):
        self.source_id = source_id
        self.spare_data_path: Path = spare_data_path
        # 用旧方法加载的备用data TODO 最后舍弃掉
        self.loaded_unit: dict[str, Unit] = dict()
        self.loaded_armament: dict[str, Armament] = dict()
        self._init()

    def units(self) -> set[Unit]:
        return set(self.loaded_unit.values())

    def armaments(self) -> set[Armament]:
        return set(self.loaded_armament.values())

    def get_unit(self, id_) -> Union[Unit, None]:
        if id_ and id_ != UNKNOWN:
            return self.loaded_unit.get(str(id_), None)
        return None

    def get_armament(self, id_) -> Union[Armament, None]:
        if id_ and id_ != UNKNOWN:
            return self.loaded_armament.get(str(id_), None)
        return None

    def get(self, id_: str) -> Union[Unit, Armament, WorldflipperObject, None]:
        if id_ and id_ != UNKNOWN:
            if id_.startswith('u'):
                return self.loaded_unit.get(id_[1:], None)
            elif id_.startswith('a'):
                return self.loaded_armament.get(id_[1:], None)
            else:
                return None
        else:
            return None

    def _init(self):
        print(f'ServerService {self.source_id} load objects')
        os.makedirs(self.spare_data_path, exist_ok=True)
        if not (self.spare_data_path / 'unit.json').exists():
            (self.spare_data_path / 'unit.json').write_text(json.dumps({}))
        if not (self.spare_data_path / 'armament.json').exists():
            (self.spare_data_path / 'armament.json').write_text(json.dumps({}))
        unit_data: dict = json.loads((self.spare_data_path / 'unit.json').read_text('utf-8'))
        armament_data: dict = json.loads((self.spare_data_path / 'armament.json').read_text('utf-8'))
        for id_, u in unit_data.items():
            self.loaded_unit[id_] = Unit(self.source_id, id_, u)
        for id_, a in armament_data.items():
            self.loaded_armament[id_] = Armament(self.source_id, id_, a)


class Manager:
    """
    弹射资源管理器
    """
    def __init__(self):
        self._loaded_sources: dict[str, ServerSource] = dict()
        self._statistic: StatisticManager = StatisticManager('worldflipper')
        self.roster = Roster()
        self.roster.update(NicknameMaster())

    def loaded_source_ids(self) -> list[str]:
        return list(self._loaded_sources.keys())

    def load_source(self, source: str, server: ServerSource):
        self._loaded_sources[source] = server
        self.roster.update(
            NicknameMasterOrigin(server.spare_data_path / 'unit.json', server.spare_data_path / 'armament.json')
        )

    def clear(self):
        self._loaded_sources.clear()
        self.roster.clear()

    @property
    def statistic(self) -> StatisticManager:
        return self._statistic

    def has_unit(self, id_):
        sources = []
        for ss in self._loaded_sources:
            if str(id_) in self._loaded_sources[ss].loaded_unit:
                sources.append(ss)
        return sources

    def has_armament(self, id_):
        sources = []
        for ss in self._loaded_sources:
            if str(id_) in self._loaded_sources[ss].loaded_armament:
                sources.append(ss)
        return sources

    def units(self) -> set[Unit]:
        units: dict[str, Unit] = dict()
        for ss in self._loaded_sources:
            for uid, u in self._loaded_sources[ss].loaded_unit.items():
                if uid not in units:
                    units[uid] = u
        return set(units.values())

    def armaments(self) -> set[Armament]:
        armaments: dict[str, Armament] = dict()
        for ss in self._loaded_sources:
            for aid, a in self._loaded_sources[ss].loaded_armament.items():
                if aid not in armaments:
                    armaments[aid] = a
        return set(armaments.values())

    def get_unit(self, id_, main_source: str = None) -> Union[Unit, None]:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get_unit(id_)
        if not result:
            for ssid, ss in self._loaded_sources.items():
                result = ss.get_unit(id_)
                if result:
                    break
        return result

    def get_armament(self, id_, main_source: str = None) -> Union[Armament, None]:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get_armament(id_)
        if not result:
            for ssid, ss in self._loaded_sources.items():
                result = ss.get_armament(id_)
                if result:
                    break
        return result

    def get(self, id_, main_source: str = None) -> Union[Unit, Armament, WorldflipperObject, None]:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get(id_)
        if not result:
            for ssid, ss in self._loaded_sources.items():
                result = ss.get(id_)
                if result:
                    break
        return result

    def get_id(self, s: str) -> str:
        return self.roster.get_id(s)

    def guess_id(self, s: str) -> Tuple[str, int, str]:
        """
        :return: (id, guess_score, name)
        """
        return self.roster.guess_id(s)

    def get_source(self, source_id: str) -> Union[ServerSource, None]:
        return self._loaded_sources.get(source_id)


wfm: Manager = Manager()
"""
Worldflipper Manager 弹射资源管理器
"""


def reload_wfm():
    wfm.clear()
    wfm.load_source(
        'sc',
        ServerSource(
            'sc',
            DATA_PATH / 'worldflipper' / 'object' / 'sc'
        )
    )
    wfm.load_source(
        'jp',
        ServerSource(
            'jp',
            DATA_PATH / 'worldflipper' / 'object' / 'jp'
        )
    )


reload_wfm()
