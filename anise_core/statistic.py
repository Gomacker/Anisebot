try:
    import ujson as json
except ModuleNotFoundError:
    import json

from anise_core import DATA_PATH

STATISTIC_PATH = DATA_PATH / 'statistic.json'


class StatisticManager:
    def __init__(self, group):
        self.group = group

    async def add(self, item: str, count=1) -> int:
        if not STATISTIC_PATH.exists():
            with open(STATISTIC_PATH, 'w', encoding='utf-8') as f:
                f.write(json.dumps({}))
        with open(STATISTIC_PATH, 'r', encoding='utf-8') as f:
            item = f'{self.group}.{item}'
            d = json.loads(f.read())
            if item in d:
                d[item] += count
            else:
                d[item] = count
        with open(STATISTIC_PATH, 'w', encoding='utf-8') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2))
        return d[item]

    async def get(self, item: str) -> int:
        if not STATISTIC_PATH.exists():
            with open(STATISTIC_PATH, 'w', encoding='utf-8') as f:
                f.write(json.dumps({}))
                return 0
        with open(STATISTIC_PATH, 'r', encoding='utf-8') as f:
            item = f'{self.group}.{item}'
            d = json.loads(f.read())
            if item in d:
                return d[item]
            else:
                return 0
