import base64
import io
import time
import typing
from typing import Union

import httpx

from anise_core.worldflipper.utils.wikipage import WikiPageGenerator
from ..manager import get_source_id
from ..schedule import gen_schedule
from .....service import Service

try:
    import ujson as json
except ModuleNotFoundError:
    import json
import os
import re

from PIL import Image, ImageSequence
from nonebot.adapters.onebot.v11 import MessageSegment, Event, Message, GroupMessageEvent

from anise_core import RES_PATH, MAIN_URL
from anise_core.worldflipper import Unit, Armament, WorldflipperObject, wfm
from .....utils import pic2b64


def make_simple_bg(img: Image.Image) -> Image.Image:
    """
    目前qq的图片压缩逻辑，透明背景png会显示错误
    所以要自行添加背景
    """
    bg: Image.Image = Image.new('RGBA', img.size, (240, 240, 240))
    bg.paste(img, mask=img)
    return bg


def make_simple_gif_to_byte(img: Image.Image) -> io.BytesIO:
    frames = list()
    durations = list()
    bg: Image.Image = Image.new('RGBA', img.size, (240, 240, 240))
    for frame in ImageSequence.all_frames(img):
        f_canvas = Image.new('RGBA', bg.size)
        f_canvas.paste(bg)
        temp = Image.new('RGBA', img.size)
        temp.paste(frame)
        f_canvas.paste(temp, (0, 0), mask=temp)
        frames.append(f_canvas)
        durations.append(frame.info['duration'])
    buf = io.BytesIO()
    frames[0].save(
        buf, format='GIF', save_all=True, loop=0,
        duration=durations, disposal=2, append_images=frames[1:]
    )
    return buf


class QuerySet:
    def __init__(self, data: dict):
        self.data = data

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        return None


class QueryObjects(QuerySet):

    @staticmethod
    async def search_wfo(text: str, main_source: str = None, strict=False) -> tuple[Union[Message, MessageSegment, None], dict]:
        """角色武器通用 资源查找"""
        params = text.split()
        res_group = None
        kwargs = {}
        print(params)
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
            print(search_str, uid, score)
            if score == 100 if strict else score > 60:
                target: WorldflipperObject = wfm.get(uid, main_source)
        if target:
            if res_group:
                if res_group in ('pixelart/special', 'pixelart/walk_front'):
                    if target.res_exists(res_group, 'gif'):
                        img = target.res(res_group)
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

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        strict = self.data.get('strict', False)
        wfo_result, kwargs = await self.search_wfo(text, strict=strict)
        if wfo_result:
            if strict:
                result += Service.get_send_content('worldflipper.query.success')
            else:
                result += Service.get_send_content('worldflipper.query.guess').format(**kwargs)
            result += wfo_result
            return result
        else:
            return None


class QueryText(QuerySet):

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        result += Service.get_send_content('worldflipper.query.success')
        result += MessageSegment.text(self.data.get('content', ''))
        return result


class QuerySchedule(QuerySet):

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        result += MessageSegment.text('今日日程：\n')
        result += await gen_schedule()
        return result


class QueryImage(QuerySet):

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        path = RES_PATH / 'worldflipper' / 'query' / self.data.get('src', '')
        if path.exists():
            result += Service.get_send_content('worldflipper.query.success')
            result += MessageSegment.image(path)
        return result


class QueryServerImage(QuerySet):

    def __init__(self, data: dict, main_url=MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        url = self.data.get('url', '')
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f'{MAIN_URL.removesuffix("/")}{url}', timeout=30.0)
                img = Image.open(io.BytesIO(r.content))
                result += Service.get_send_content('worldflipper.query.success')
                result += MessageSegment.image(pic2b64(img))
        except:
            return None
        return result

class QueryServerTable(QuerySet):
    def __init__(self, data: dict, main_url: str = MAIN_URL):
        super().__init__(data)
        self.main_url: str = main_url

    async def get_message(self, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        result = Message()
        cache_timeout = self.data.get('cache_timeout', True)
        table_id = self.data.get('table_id', '')
        cache_path = RES_PATH / 'worldflipper' / 'query' / 'table' / f'{table_id}.png'
        os.makedirs(cache_path, exist_ok=True)
        need_cache = cache_path.stat().st_mtime + cache_timeout < time.time()
        if cache_path.exists() and not need_cache:
            result += Service.get_send_content('worldflipper.query.success')
            result += MessageSegment.image(cache_path)
        from anise_core.worldflipper import playw
        b = await playw.get_browser()
        page = await b.new_page()
        await page.goto(
            f'{MAIN_URL.removesuffix("/")}/card/table/?table_id={table_id}&show_replacements=true',
            wait_until='networkidle'
        )
        img = await page.locator('.table').screenshot(type='png', omit_background=True)
        await page.close()
        img = Image.open(io.BytesIO(img)).convert('RGBA')
        if need_cache:
            img.save(cache_path)
        result += Service.get_send_content('worldflipper.query.success')
        result += f'{MAIN_URL.removesuffix("/")}/table/{table_id}\n'
        result += MessageSegment.image(pic2b64(img))
        return result


class QueryManager:
    def __init__(self):
        self.query_map: dict[str, dict] = dict()
        self.query_types: dict[str, type[QuerySet]] = dict()

    def init(self) -> int:
        self.query_map.clear()
        path = RES_PATH / 'worldflipper' / 'query' / 'config.json'
        os.makedirs(path.parent, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({}), 'utf-8')
        self.query_map.update(json.loads(path.read_text('utf-8')))

        self.query_types.clear()
        self.register('text', QueryText)
        self.register('schedule', QuerySchedule)
        self.register('image', QueryImage)
        self.register('wfo', QueryObjects)
        self.register('server_image', QueryServerImage)
        self.register('server_table', QueryServerTable)

        return len(self.query_map)

    def register(self, type_id: str, query_type: type[QuerySet]):
        self.query_types[type_id] = query_type

    async def query(self, text: str, e: Event) -> Union[Message, None]:
        for i, qs in self.query_map.items():
            for q in qs:
                if ('regex' in q and re.findall(q['regex'], text)) or 'regex' not in q:
                    rst = await read_query_set(q, text, e)
                    if rst:
                        return rst
        return Service.get_send_content('worldflipper.query.failed')

    async def read_query_set(self, query_set: dict, text: str, e: Event) -> typing.Union[Message, MessageSegment, None]:
        if 'type' in query_set and query_set['type'] in self.query_types:
            QT: type[QuerySet] = self.query_types[query_set['type']]
            return await QT(query_set).get_message(text, e)
        return None


query_manager = QueryManager()


async def read_query_set(query_set: dict, text: str, e: Event) -> Message:
    result = Message()

    if 'type' not in query_set:
        pass

    elif query_set['type'] == 'wfo':
        if isinstance(e, GroupMessageEvent):
            main_source = get_source_id(e.group_id, e.user_id)
        else:
            main_source = get_source_id(None, e.get_user_id())
        wfo_result, kwargs = await search_wfo(text, main_source=main_source, strict=query_set['strict'])
        if wfo_result:
            if query_set['strict']:
                result += Service.get_send_content('worldflipper.query.success')
            else:

                result += Service.get_send_content('worldflipper.query.guess').format(**kwargs)
            result += wfo_result

    elif query_set['type'] == 'text':
        result += Service.get_send_content('worldflipper.query.success')
        result += MessageSegment.text(query_set.get('content', ''))

    elif query_set['type'] == 'image':
        path = RES_PATH / 'worldflipper' / 'query' / query_set.get('src', '')
        if path.exists():
            result += Service.get_send_content('worldflipper.query.success')
            result += MessageSegment.image(path)

    elif query_set['type'] == 'bundle':
        for c in query_set['contents']:
            if c['type'] == 'package':
                continue
            result += await read_query_set(c, text, e)
        if result:
            result = Message(Service.get_send_content('worldflipper.query.success')) + result

    elif query_set['type'] == 'schedule':
        result += MessageSegment.text('今日日程：\n')
        result += await gen_schedule()

    elif query_set['type'] == 'schedule_qly':
        result += MessageSegment.text('千里眼：\n')
        result += await gen_schedule()

    else:
        result += Service.get_send_content('worldflipper.query.failed') + '[未知的返回类型]'

    return result


async def query(text: str, e: Event) -> Union[Message, None]:
    for i, qs in query_manager.query_map.items():
        for q in qs:
            if ('regex' in q and re.findall(q['regex'], text)) or 'regex' not in q:
                rst = await read_query_set(q, text, e)
                if rst:
                    return rst
    return Service.get_send_content('worldflipper.query.failed')


def get_target(
        text: str,
        main_source: str = None,
        strict: bool = False
) -> tuple[Union[Unit, Armament, WorldflipperObject, None], int, str]:
    target: None = None
    guess_content = ''
    score = 100
    if text.startswith('uid') and text[3:].isdigit():
        target: Unit = wfm.get_unit(int(text[3:]), main_source)
    if text.startswith('aid') and text[3:].isdigit():
        target: Unit = wfm.get_unit(int(text[3:]), main_source)
    if not target:
        uid, score, guess_content = wfm.roster.guess_id(text)
        print(uid, score, guess_content)
        if score == 100 if strict else score > 60:
            target: WorldflipperObject = wfm.get(f'{uid}', main_source)
    return target, score, guess_content
