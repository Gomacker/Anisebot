import asyncio
import hashlib
import io
import json
import os
import time
from pathlib import Path

from PIL import Image

from anise_core import RES_PATH
from anise_core.worldflipper import WorldflipperObject, Unit, wfm
from anise_core.worldflipper.playw import get_browser

ICON_REPLACES: dict = {
    '火属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'fire.png',
    '水属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'water.png',
    '雷属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'thunder.png',
    '风属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'wind.png',
    '光属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'light.png',
    '暗属性': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'dark.png',
    '作为主要角色编成：': RES_PATH / 'worldflipper' / 'ui/icon/desc' / 'main.png'
}


class WikiPageGenerator:
    def __init__(self, obj: WorldflipperObject):
        self.obj: WorldflipperObject = obj

    def is_need_new(self) -> bool:
        hash_path = \
            RES_PATH / 'worldflipper' / 'generated' / 'wikipage' / self.obj.source_id / \
            ('unit' if isinstance(self.obj, Unit) else 'armament') / f'hash_data.json'
        os.makedirs(hash_path.parent, exist_ok=True)
        if not hash_path.exists():
            hash_path.write_text(json.dumps({}, ensure_ascii=False, indent=2))
        hash_data: dict = json.loads(hash_path.read_text('utf-8'))
        data_hash = hashlib.md5(str(self.obj.data()).encode()).hexdigest()
        return hash_data.get(str(self.obj.id)) != data_hash

    def get_pic_path(self) -> Path:
        return (
            RES_PATH / 'worldflipper' / 'generated' / 'wikipage' / self.obj.source_id /
            ('unit' if isinstance(self.obj, Unit) else 'armament') / f'{self.obj.id}.png'
        )

    async def get_pic(self, save=False) -> Image.Image:

        b = await get_browser()
        page = await b.new_page()
        await page.goto(
            # f'http://localhost/card/{"unit" if isinstance(self.obj, Unit) else "armament"}?source={self.obj.source_id}&wf_id={self.obj.id}',
            f'http://meteorhouse.wiki/card/{"unit" if isinstance(self.obj, Unit) else "armament"}?wf_id={self.obj.id}',
            wait_until='networkidle'
        )
        img = await page.locator('#main-card').screenshot(type='png', omit_background=True)
        await page.close()
        img = Image.open(io.BytesIO(img)).convert('RGBA')

        if save:
            img.save(
                RES_PATH / 'worldflipper' / 'generated' / 'wikipage' / self.obj.source_id /
                ('unit' if isinstance(self.obj, Unit) else 'armament') / f'{self.obj.id}.png'
            )
            hash_path = (
                RES_PATH / 'worldflipper' / 'generated' / 'wikipage' / self.obj.source_id /
                ('unit' if isinstance(self.obj, Unit) else 'armament') / f'hash_data.json'
            )
            if not hash_path.exists():
                hash_path.write_text(json.dumps({}, ensure_ascii=False, indent=2))
            hash_data: dict = json.loads(hash_path.read_text('utf-8'))
            data_hash = hashlib.md5(str(self.obj.data()).encode()).hexdigest()
            hash_data[str(self.obj.id)] = data_hash
            hash_path.write_text(json.dumps(hash_data, ensure_ascii=False, indent=2))
        return img

    async def get(self) -> Image.Image:
        if self.is_need_new():
            return await self.get_pic(save=True)
        else:
            return Image.open(self.get_pic_path())

if __name__ == '__main__':
    async def test():
        for u in wfm.units():
            t = time.time()
            wpg = WikiPageGenerator(u)
            img = await wpg.get()
            print(f'get img unit {u.id} {"%.2f" % (time.time() - t)}s')
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test())
    asyncio.set_event_loop(loop)
