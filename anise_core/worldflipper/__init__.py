import asyncio

import httpx
import toml
from nonebot import logger

from anise_core import DATA_PATH, CONFIG_PATH
from anise_core.worldflipper.utils.update import update

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os.path
from pathlib import Path

from anise_core.statistic import StatisticManager
from anise_core.worldflipper.object import *
from anise_core.worldflipper.roster import Roster, NicknameMaster, NicknameMasterOrigin


class ServerSource:
    def __init__(self, source_id: str, api: str):
        self.source_id = source_id
        self.api = api
        self.spare_data_path: Path = DATA_PATH / 'object' / source_id
        self.loaded_unit: dict[str, Unit] = dict()
        self.loaded_armament: dict[str, Armament] = dict()
        self._init()

    def units(self) -> set[Unit]:
        return set(self.loaded_unit.values())

    def armaments(self) -> set[Armament]:
        return set(self.loaded_armament.values())

    def get_unit(self, id_) -> Unit | None:
        return self.loaded_unit.get(str(id_), None)

    def get_armament(self, id_) -> Armament | None:
        return self.loaded_armament.get(str(id_), None)

    def get(self, id_: str) -> Unit | Armament | WorldflipperObject | None:
        if id_.startswith('u'):
            return self.loaded_unit.get(id_[1:], None)
        elif id_.startswith('a'):
            return self.loaded_armament.get(id_[1:], None)
        else:
            return None

    def _init(self):
        logger.info(f'ServerService {self.source_id} load objects')
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
    def __init__(self):
        self._server_sources_arranged: list[str] = []
        self._loaded_sources: dict[str, ServerSource] = dict()
        self._statistic: StatisticManager = StatisticManager('worldflipper')
        self.roster = Roster()
        self.roster.update(NicknameMaster())

    def loaded_source_ids(self) -> list[str]:
        return list(self._loaded_sources.keys())

    def load_source(self, server: ServerSource):
        self._server_sources_arranged.append(server.source_id)
        self._loaded_sources[server.source_id] = server
        self.roster.update(
            NicknameMasterOrigin(
                server.spare_data_path / 'unit.json',
                server.spare_data_path / 'armament.json'
            )
        )

    def clear(self):
        self._server_sources_arranged.clear()
        self._loaded_sources.clear()
        self.roster.clear()

    @property
    def statistic(self) -> StatisticManager:
        return self._statistic

    def has_object(self, id_: str):
        if id_.startswith('u'):
            return self.has_unit(id_[1:])
        elif id_.startswith('a'):
            return self.has_armament(id_[1:])
        else:
            return False

    def has_unit(self, id_):
        for ss in self._server_sources_arranged:
            if ss in self._loaded_sources and str(id_) in self._loaded_sources[ss].loaded_unit:
                return True
        return False

    def has_armament(self, id_):
        for ss in self._server_sources_arranged:
            if ss in self._loaded_sources and str(id_) in self._loaded_sources[ss].loaded_armament:
                return True
        return False

    def units(self) -> set[Unit]:
        units: dict[str, Unit] = dict()
        for ss in self._server_sources_arranged:
            # print(ss)
            for uid, u in self._loaded_sources[ss].loaded_unit.items():
                # print(ss, uid)
                if uid not in units:
                    units[uid] = u
        return set(units.values())

    def armaments(self) -> set[Armament]:
        armaments: dict[str, Armament] = dict()
        for ss in self._server_sources_arranged:
            for aid, a in self._loaded_sources[ss].loaded_armament.items():
                if aid not in armaments:
                    armaments[aid] = a
        return set(armaments.values())

    def get_unit(self, id_, main_source: str = None) -> Unit | None:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get_unit(id_)
        if not result:
            for ss in self._server_sources_arranged:
                result = self._loaded_sources[ss].get_unit(id_)
                if result:
                    break
        return result

    def get_armament(self, id_, main_source: str = None) -> Armament | None:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get_armament(id_)
        if not result:
            for ss in self._server_sources_arranged:
                result = self._loaded_sources[ss].get_armament(id_)
                if result:
                    break
        return result

    def get(self, id_, main_source: str = None) -> Unit | Armament | WorldflipperObject | None:
        result = None
        if main_source and main_source in self._loaded_sources:
            result = self._loaded_sources[main_source].get(id_)
        if not result:
            for ss in self._server_sources_arranged:
                result = self._loaded_sources[ss].get(id_)
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

    def get_source(self, source_id: str) -> ServerSource | None:
        return self._loaded_sources.get(source_id)


wfm: Manager = Manager()


def reload_wfm():
    wfm.clear()
    wfm.load_source(ServerSource('os', ''))

async def init_wfm():
    path = CONFIG_PATH / 'config.toml'
    os.makedirs(path.parent, exist_ok=True)
    if not path.exists():
        config = toml.loads((Path(__file__).parent / 'config_default.toml').read_text('utf-8'))
        await update()
        async with httpx.AsyncClient() as client:
            r = await client.get(config['query']['config_url'], timeout=30.0)
            qc_path = RES_PATH / 'query' / 'config.json'
            os.makedirs(qc_path.parent, exist_ok=True)
            qc_path.write_bytes(r.content)
        path.write_text(toml.dumps(config), 'utf-8')
    config = toml.loads(path.read_text('utf-8'))
    if config.get('update', False):
        await update()
    reload_wfm()

loop = asyncio.get_event_loop()
loop.run_until_complete(init_wfm())

if __name__ == '__main__':
    def test():
        print('\n'.join([str(x.data()) for x in wfm.units()]))
    test()
