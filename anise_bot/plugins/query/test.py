import hashlib
import io
import json
import os
import re
import typing
from pathlib import Path
from urllib import parse

import httpx
from PIL import Image
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from anise_bot.utils import pic2b64
from anise_core import MAIN_URL, RES_PATH

if __name__ == '__main__':

    def read_hash(text: str) -> typing.Union[str, None]:
        path = Path('hash_test.json')
        if not path.exists():
            return None
        else:
            d = json.loads(path.read_text('utf-8'))
            s = d.get(text, None)
            return s

    def write_hash(text: str, hash_: str):
        path = Path('hash_test.json')
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            path.write_text(json.dumps({}))
        d = json.loads(path.read_text('utf-8'))
        d[text] = hash_
        path.write_text(json.dumps(d, indent=2, ensure_ascii=True), 'utf-8')

    def get_text_and_page(text: str) -> tuple[str, int]:
        if not re.search(r'(06|02)$', text) and (page_index := re.search(r'\d+$', text)):
            page_index = page_index.group(0)
            text = text.removesuffix(page_index)
            page_index = int(page_index)
        else:
            page_index = 1
        text = text.strip()
        return text, page_index


    async def get_image(text: str, page_index: int) -> Image.Image:
        from anise_core.worldflipper import playw
        b = await playw.get_browser()
        page = await b.new_page(viewport={'width': 1036, 'height': 120})
        url = f'{MAIN_URL.removesuffix("/")}/pure/partySearcher/?q={parse.quote(text)}&page={page_index}'
        await page.goto(url, wait_until='networkidle')
        img = await page.screenshot(full_page=True)
        await page.close()
        img = Image.open(io.BytesIO(img))
        return img

    async def get_message(text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        text, page_index = get_text_and_page(text)
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{MAIN_URL.removesuffix("/")}/api/v1/party/page/?search_text={text}&page_index={page_index}')
            if r.status_code == 200:
                d: dict = r.json()
                pts = d.get('parties', {})
                hash_key = f'{text}_page{page_index}'
                if pts:
                    h1 = hashlib.md5(json.dumps(pts).encode())
                    h2 = read_hash(hash_key)
                    cache_path = RES_PATH / 'query' / 'party' / f'{hash_key}.png'
                    if h1 == h2 and cache_path.exists():
                        msg += MessageSegment.image(cache_path)
                    else:
                        write_hash(hash_key, h1.hexdigest())
                        img = await get_image(text, page_index)
                        msg += MessageSegment.image(pic2b64(img))
                    print(f'{hash_key} length: {len(pts)}')

                    return msg
                else:
                    print(f'it\'s empty in {hash_key}')
                    return None
            else:
                return None


    def test():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(get_message('abs'))
    test()