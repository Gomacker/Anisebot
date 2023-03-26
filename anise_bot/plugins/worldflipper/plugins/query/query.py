import base64
import hashlib
import io
from typing import Literal, Union

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

from PIL import Image, ImageSequence, ImageDraw, ImageFont
from nonebot.adapters.onebot.v11 import MessageSegment, Event, Message, GroupMessageEvent

from anise_core import RES_PATH
from anise_core.worldflipper import Unit, Armament, WorldflipperObject, wfm
from .....utils import pic2b64


class QueryManager:
    def __init__(self, source):
        self.source: str = source
        self.query_map: dict = dict()

    def init(self) -> int:
        self.query_map.clear()
        path = RES_PATH / 'worldflipper' / 'query' / 'config.json'
        os.makedirs(path.parent, exist_ok=True)
        if not path.exists():
            path.write_text(json.dumps({}), 'utf-8')
        self.query_map.update(json.loads(path.read_text('utf-8')))
        return len(self.query_map)


query_manager = QueryManager('sc')


def make_simple_bg(img: Image.Image) -> Image.Image:
    bg: Image.Image = Image.new('RGBA', img.size, (240, 240, 240))
    bg.paste(img, mask=img)
    return bg


def make_simple_gif_to_byte(img: Image.Image, text: str = 'Copyright Cygames, Inc.') -> io.BytesIO:
    frames = list()
    durations = list()
    bg: Image.Image = Image.new('RGBA', img.size, (240, 240, 240))
    for frame in ImageSequence.all_frames(img):
        f_canvas = Image.new('RGBA', bg.size)
        f_canvas.paste(bg)
        draw = ImageDraw.Draw(f_canvas)
        temp = Image.new('RGBA', img.size)
        temp.paste(frame)
        f_canvas.paste(temp, (0, 0), mask=temp)
        font = ImageFont.load_default()
        font_w, font_h = font.getsize(text)
        draw.text((bg.width - font_w - 2, bg.height - font_h - 2), text, fill='black')
        frames.append(f_canvas)
        durations.append(frame.info['duration'])
    buf = io.BytesIO()
    frames[0].save(
        buf, format='GIF', save_all=True, loop=0,
        duration=durations, disposal=2, append_images=frames[1:]
    )
    return buf


async def search_wfo(text: str, e, main_source: str = None, strict=False) -> tuple[Union[Message, MessageSegment, None], dict]:
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
            if res_group == 'pixelart/special':
                if target.res_exists(res_group, 'gif'):
                    img = target.res(res_group)
                    buf = make_simple_gif_to_byte(img, text='')
                    base64_str = base64.b64encode(buf.getvalue()).decode()
                    img = MessageSegment.image('base64://' + base64_str)
                    return img, kwargs

            elif res_group == 'pixelart/walk_front':
                if target.res_exists(res_group, 'gif'):
                    img = target.res(res_group)
                    buf = make_simple_gif_to_byte(img, text='')
                    base64_str = base64.b64encode(buf.getvalue()).decode()
                    img = MessageSegment.image('base64://' + base64_str)
                    return img, kwargs
            elif target.res_exists(res_group):
                img = make_simple_bg(target.res(res_group))
                img = MessageSegment.image(pic2b64(img))
                return img, kwargs
        elif isinstance(target, Unit) or isinstance(target, Armament):
            print(target, isinstance(target, Armament))
            wpg = WikiPageGenerator(target)
            print('get wikipage from file')
            return MessageSegment.image(wpg.get_pic_path()), kwargs
    return None, {}


async def read_query_set(query_set: dict, text: str, e: Event) -> Message:
    result = Message()

    if 'type' not in query_set:
        pass

    elif query_set['type'] == 'wfo':
        if isinstance(e, GroupMessageEvent):
            main_source = get_source_id(e.group_id, e.user_id)
        else:
            main_source = get_source_id(None, e.get_user_id())
        wfo_result, kwargs = await search_wfo(text, e, main_source=main_source, strict=query_set['strict'])
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
        result += gen_schedule(False)

    elif query_set['type'] == 'schedule_qly':
        result += MessageSegment.text('千里眼：\n')
        result += gen_schedule(True)

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
