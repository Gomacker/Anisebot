import json
from collections import defaultdict
from pathlib import Path

path = Path('ss.txt')
all_text = path.read_text('utf-8').split('\n')
count_set = defaultdict(int)
for t in all_text:
    count_set[t] += 1
count_set = {k: v for k, v in sorted(count_set.items(), key=lambda x: x[1], reverse=True)}
Path('ss.json').write_text(json.dumps(count_set, indent=2, ensure_ascii=False), 'utf-8')
