import hashlib
import io
from json import JSONDecodeError

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
from ...utils import pic2b64, get_send_content


class QuerySet:
    def __init__(self, data: dict):
        self.data = data

    def hash(self) -> str:
        return hashlib.md5(json.dumps(self.data).encode()).hexdigest()

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        return None

class QueryObjects(QuerySet):

    async def search_wfo(self, text: str, main_source: str = None, strict=False) -> tuple[
        typing.Union[Message, MessageSegment, None], dict]:
        """角色武器通用 资源查找"""
        params = text.split()
        kwargs = {}
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
            if isinstance(target, Unit) or isinstance(target, Armament):
                wpg = WikiPageGenerator(target, self.data.get('cache_timeout', 60 * 60 * 24))
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
        path = RES_PATH / 'query' / 'local' / self.data.get('src', '')
        os.makedirs(path.parent, exist_ok=True)
        if path.exists():
            msg += get_send_content('worldflipper.query.success')
            msg += MessageSegment.image(path)
        return msg


class QueryServerImage(QuerySet):

    def __init__(self, data: dict, main_url=MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url
        self.cache_timeout: float = 60 * 60 * 24

    def get_pic_path(self):
        path = RES_PATH / 'query' / 'cache' / f'{Path(self.data.get("url", "")).name}'
        return path

    def is_need_new(self) -> bool:
        cache_path = self.get_pic_path()
        return not cache_path.exists() or cache_path.stat().st_mtime + self.cache_timeout < time.time()

    async def get_image(self) -> Image.Image:
        if self.is_need_new():
            async with httpx.AsyncClient() as client:
                url = self.data.get('url', '')
                r = await client.get(f'{self.main_url.removesuffix("/")}{url}', timeout=30.0)
                img = Image.open(io.BytesIO(r.content))
                cache_path = self.get_pic_path()
                os.makedirs(cache_path.parent, exist_ok=True)
                img.save(cache_path)
        else:
            img = Image.open(self.get_pic_path())
        return img

    async def get_message(self, text: str) -> typing.Union[Message, MessageSegment, None]:
        msg = Message()
        try:
            img = await self.get_image()
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
        cache_timeout = self.data.get('cache_timeout', 60 * 60 * 24)
        table_id = self.data.get('table_id', '')
        cache_path = RES_PATH / 'query' / 'table' / f'{table_id}.png'
        os.makedirs(cache_path.parent, exist_ok=True)
        need_cache = not cache_path.exists() or cache_path.stat().st_mtime + cache_timeout < time.time()
        if cache_path.exists() and not need_cache:
            msg += get_send_content('worldflipper.query.success')
            msg += f'{self.main_url.removesuffix("/")}/table/{table_id}\n'
            msg += MessageSegment.image(cache_path)
        else:
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
    def hash_path():
        return RES_PATH / 'query' / 'party_hash.json'

    @staticmethod
    def read_hash(text: str) -> typing.Union[str, None]:
        path = QueryPartyPage.hash_path()
        if not path.exists():
            return None
        else:
            try:
                d = json.loads(path.read_text('utf-8'))
            except JSONDecodeError:
                path.write_text(json.dumps({}))
                d = {}
            s = d.get(text, None)
            return s

    @staticmethod
    def write_hash(text: str, hash_: str):
        path = QueryPartyPage.hash_path()
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
                f'{MAIN_URL.removesuffix("/")}/api/v1/party/page/?search_text={text}&page_index={page_index}',
                timeout=30.0
            )
            if r.status_code == 200:
                d: dict = r.json()
                pts = d.get('parties', {})
                hash_key = f'{text}_page{page_index}'
                if pts:
                    logger.debug(pts)
                    h1 = hashlib.md5(json.dumps(pts).encode()).hexdigest()
                    h2 = self.read_hash(hash_key)
                    logger.debug(h1, h2)
                    cache_path = RES_PATH / 'query' / 'party' / f'{hash_key}.png'
                    logger.debug(f'exists: {cache_path.exists()}')
                    if h1 == h2 and cache_path.exists():
                        msg += MessageSegment.image(cache_path)
                    else:
                        self.write_hash(hash_key, h1)
                        img = await self.get_image(text, page_index)
                        os.makedirs(cache_path.parent, exist_ok=True)
                        img.save(cache_path)
                        msg += MessageSegment.image(pic2b64(img))
                    logger.debug(f'{hash_key} length: {len(pts)}')

                    return msg
                else:
                    logger.debug(f'it\'s empty in {hash_key}')
                    return None
            else:
                return None
