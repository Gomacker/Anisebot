import hashlib
import json
import os
import typing
from pathlib import Path

import httpx
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from anise_core import MAIN_URL

if __name__ == '__main__':
    def write_hash(text: str, hash_: str):
        path = Path('hash_test.json')
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            path.write_text(json.dumps({}))
        d = json.loads(path.read_text('utf-8'))
        d[text] = hash_
        path.write_text(json.dumps(d, indent=2, ensure_ascii=True), 'utf-8')


    async def get_message(text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{MAIN_URL.removesuffix("/")}/api/v1/party/page/?search_text={text}&page_index={1}')
            # TODO
            if r.status_code == 200:
                d: dict = r.json()
                h = hashlib.md5(json.dumps(d.get('parties', {})).encode())
                write_hash(text, h.hexdigest())

        from anise_core.worldflipper import playw
        b = await playw.get_browser()
        page = await b.new_page()
        # await page.goto('')

        return msg
    def test():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(get_message('abs3'))
    test()