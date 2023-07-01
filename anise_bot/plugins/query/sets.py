import base64
import hashlib
import io
try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import re
import time
import typing
from pathlib import Path
from urllib import parse

import httpx
from PIL import Image
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from anise_core import MAIN_URL, RES_PATH
from anise_core.worldflipper import wfm, WorldflipperObject, Armament, Unit
from anise_core.worldflipper.utils.schedule import get_schedule
from anise_core.worldflipper.utils.wikipage import WikiPageGenerator
from ...utils import pic2b64, make_simple_gif_to_byte, make_simple_bg, get_send_content


class QuerySet:
    def __init__(self, data: dict):
        self.data = data

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        return None


class QueryObjects(QuerySet):

    @staticmethod
    async def search_wfo(text: str, main_source: str = None, strict=False) -> tuple[typing.Union[Message, MessageSegment, None], dict]:
        """角色武器通用 资源查找"""
        params = text.split()
        res_group = None
        kwargs = {}
        if params[-1] == 'img':
            extra_param = params[1:]
            awakened = 'a' in extra_param
            if 's212' in extra_param:
                res_group = f'square212x/{"awakened" if awakened else "base"}'
            elif 'fr' in extra_param:
                res_group = f'full_resized/{"awakened" if awakened else "base"}'
            elif 'ps' in extra_param:
                res_group = f'pixelart/special'
            elif 'pf' in extra_param:
                res_group = f'pixelart/walk_front'
        elif re.search('觉醒立绘', text):
            text = text.replace('觉醒立绘', '')
            res_group = f'full_resized/awakened'
        elif re.search('立绘', text):
            text = text.replace('立绘', '')
            res_group = f'full_resized/base'

        search_str: str = params[0]
        target: None = None
        if search_str.startswith('uid') and search_str[3:].isdigit():
            target: Unit = wfm.get(f'u{int(search_str[3:])}', main_source)
        if search_str.startswith('aid') and search_str[3:].isdigit():
            target: Armament = wfm.get(f'a{int(search_str[3:])}', main_source)
        uid, score, guess_content = wfm.roster.guess_id(search_str)
        if score == 100:
            target: WorldflipperObject = wfm.get(uid, main_source)
        if not target:
            search_str = text
            uid, score, guess_content = wfm.roster.guess_id(search_str)
            kwargs['guess_content'] = guess_content
            if score == 100 if strict else score > 60:
                target: WorldflipperObject = wfm.get(uid, main_source)
        if target:
            if res_group:
                if res_group in ('pixelart/special', 'pixelart/walk_front'):
                    if target.res_exists(res_group, 'gif'):
                        img = target.res(res_group, 'gif')
                        buf = make_simple_gif_to_byte(img)
                        base64_str = base64.b64encode(buf.getvalue()).decode()
                        img = MessageSegment.image('base64://' + base64_str)
                        return img, kwargs
                elif target.res_exists(res_group):
                    img = make_simple_bg(target.res(res_group))
                    img = MessageSegment.image(pic2b64(img))
                    return img, kwargs
            elif isinstance(target, Unit) or isinstance(target, Armament):
                wpg = WikiPageGenerator(target)
                return MessageSegment.image(pic2b64(await wpg.get())), kwargs
        return None, {}

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        strict = self.data.get('strict', False)
        wfo_result, kwargs = await self.search_wfo(text, strict=strict)
        if wfo_result:
            if strict:
                msg += get_send_content('worldflipper.query.success')
            else:
                msg += get_send_content('worldflipper.query.guess').format(**kwargs)
            msg += wfo_result
            return msg
        else:
            return None


class QueryText(QuerySet):

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        msg += get_send_content('worldflipper.query.success')
        msg += MessageSegment.text(self.data.get('content', ''))
        return msg


class QuerySchedule(QuerySet):

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        msg += MessageSegment.text('今日日程：\n')
        msg += MessageSegment.image(pic2b64(await get_schedule()))
        return msg


class QueryImage(QuerySet):

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        path = RES_PATH / 'query' / self.data.get('src', '')
        if path.exists():
            msg += get_send_content('worldflipper.query.success')
            msg += MessageSegment.image(path)
        return msg


class QueryServerImage(QuerySet):

    def __init__(self, data: dict, main_url=MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        url = self.data.get('url', '')
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f'{self.main_url.removesuffix("/")}{url}', timeout=30.0)
                img = Image.open(io.BytesIO(r.content))
                msg += get_send_content('worldflipper.query.success')
                msg += MessageSegment.image(pic2b64(img))
        except Exception as ex:
            logger.exception(ex)
            return None
        return msg


class QueryServerTable(QuerySet):
    def __init__(self, data: dict, main_url: str = MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        cache_timeout = self.data.get('cache_timeout', True)
        table_id = self.data.get('table_id', '')
        cache_path = RES_PATH / 'query' / 'table' / f'{table_id}.png'
        os.makedirs(cache_path, exist_ok=True)
        need_cache = cache_path.stat().st_mtime + cache_timeout < time.time()
        if cache_path.exists() and not need_cache:
            msg += get_send_content('worldflipper.query.success')
            msg += MessageSegment.image(cache_path)
        from anise_core.worldflipper import playw
        b = await playw.get_browser()
        page = await b.new_page()
        await page.goto(
            f'{self.main_url.removesuffix("/")}/card/table/?table_id={table_id}&show_replacements=true',
            wait_until='networkidle'
        )
        img = await page.locator('.table').screenshot(type='png', omit_background=True)
        await page.close()
        img = Image.open(io.BytesIO(img)).convert('RGBA')
        if need_cache:
            img.save(cache_path)
        msg += get_send_content('worldflipper.query.success')
        msg += f'{self.main_url.removesuffix("/")}/table/{table_id}\n'
        msg += MessageSegment.image(pic2b64(img))
        return msg

class QueryPartyPage(QuerySet):
    def __init__(self, data: dict, main_url: str = MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url

    @staticmethod
    def read_hash(text: str) -> typing.Union[str, None]:
        path = Path('hash_test.json')
        if not path.exists():
            return None
        else:
            d = json.loads(path.read_text('utf-8'))
            s = d.get(text, None)
            return s

    @staticmethod
    def write_hash(text: str, hash_: str):
        path = Path('hash_test.json')
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            path.write_text(json.dumps({}))
        d = json.loads(path.read_text('utf-8'))
        d[text] = hash_
        path.write_text(json.dumps(d, indent=2, ensure_ascii=False), 'utf-8')

    @staticmethod
    def get_text_and_page(text: str) -> tuple[str, int]:
        if not re.search(r'(06|02)$', text) and (page_index := re.search(r'\d+$', text)):
            page_index = page_index.group(0)
            text = text.removesuffix(page_index)
            page_index = int(page_index)
        else:
            page_index = 1
        text = text.strip()
        return text, page_index

    async def get_image(self, text: str, page_index: int) -> Image.Image:
        from anise_core.worldflipper import playw
        b = await playw.get_browser()
        page = await b.new_page(viewport={'width': 1036, 'height': 120})
        url = f'{self.main_url.removesuffix("/")}/pure/partySearcher/?q={parse.quote(text)}&page={page_index}'
        await page.goto(url, wait_until='networkidle')
        img = await page.screenshot(full_page=True)
        await page.close()
        img = Image.open(io.BytesIO(img))
        return img

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        text, page_index = self.get_text_and_page(text)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f'{MAIN_URL.removesuffix("/")}/api/v1/party/page/?search_text={text}&page_index={page_index}')
            if r.status_code == 200:
                d: dict = r.json()
                pts = d.get('parties', {})
                hash_key = f'{text}_page{page_index}'
                if pts:
                    print(pts)
                    h1 = hashlib.md5(json.dumps(pts).encode()).hexdigest()
                    h2 = self.read_hash(hash_key)
                    print(h1, h2)
                    cache_path = RES_PATH / 'query' / 'party' / f'{hash_key}.png'
                    print(f'exists: {cache_path.exists()}')
                    if h1 == h2 and cache_path.exists():
                        msg += MessageSegment.image(cache_path)
                    else:
                        self.write_hash(hash_key, h1)
                        img = await self.get_image(text, page_index)
                        os.makedirs(cache_path.parent, exist_ok=True)
                        img.save(cache_path)
                        msg += MessageSegment.image(pic2b64(img))
                    print(f'{hash_key} length: {len(pts)}')

                    return msg
                else:
                    print(f'it\'s empty in {hash_key}')
                    return None
            else:
                return None
