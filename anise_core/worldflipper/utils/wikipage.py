import asyncio
import hashlib
import io

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import time
from pathlib import Path

from PIL import Image

from anise_core import RES_PATH, MAIN_URL
from anise_core.worldflipper import WorldflipperObject, Unit, wfm
from anise_core.worldflipper.playw import get_browser


class WikiPageGenerator:
    def __init__(self, obj: WorldflipperObject):
        self.obj: WorldflipperObject = obj

    @property
    def hash_data(self) -> dict:
        path = RES_PATH / 'wikipage' / self.obj.source_id / self.obj.obj_type / f'hash_data.json'
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            path.write_text(json.dumps({}))
        d: dict = json.loads(path.read_text('utf-8'))
        return d

    @property
    def data_hash(self) -> str:
        return hashlib.md5(json.dumps(self.obj.data()).encode()).hexdigest()

    def write_hash(self, id_: str, hash_: str):
        path = RES_PATH / 'wikipage' / self.obj.source_id / self.obj.obj_type / f'hash_data.json'
        path.write_text(json.dumps(self.hash_data.update({id_: hash_}), indent=2, ensure_ascii=False), 'utf-8')

    def is_need_new(self) -> bool:
        return self.hash_data.get(str(self.obj.id), '') != self.data_hash

    def get_pic_path(self) -> Path:
        return RES_PATH / 'wikipage' / self.obj.source_id / self.obj.obj_type / f'{self.obj.id}.png'

    async def get_pic(self, save=False) -> Image.Image:

        b = await get_browser()
        page = await b.new_page()
        await page.goto(f'{MAIN_URL}/card/{self.obj.obj_type}?wf_id={self.obj.id}', wait_until='networkidle')
        img = await page.locator('#main-card').screenshot(type='png', omit_background=True)
        await page.close()
        img = Image.open(io.BytesIO(img)).convert('RGBA')

        if save:
            img.save(RES_PATH / 'wikipage' / self.obj.source_id / self.obj.obj_type / f'{self.obj.id}.png')
            self.write_hash(str(self.obj.id), self.data_hash)
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
