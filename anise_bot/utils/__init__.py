import base64
import io
import json
import os
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import Literal

import pytz as pytz
import unicodedata
import zhconv
from PIL import Image, ImageSequence

from anise_core import CONFIG_PATH
from . import dao


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


def get_send_content(message_key):
    path = CONFIG_PATH / 'message_contents.json'
    os.makedirs(path.parent, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({}), 'utf-8')
    data = json.loads(path.read_text('utf-8'))
    result = None
    if message_key in data:
        result = data[message_key]

    if isinstance(result, list):
        return random.choice(result)
    elif isinstance(result, str):
        return result
    else:
        return message_key


def normalize_str(s) -> str:
    s = unicodedata.normalize('NFKC', s)
    # s = s.lower()
    s = zhconv.convert(s, 'zh-hans')
    return s


def pic2b64(pic: Image.Image, format_: Literal['PNG', 'JPEG'] = 'PNG') -> str:
    buf = BytesIO()
    pic.convert('RGB' if format_ == 'JPEG' else 'RGBA').save(buf, format=format_)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return 'base64://' + base64_str


def concat_pic(pics, border=5):
    num = len(pics)
    w, h = pics[0].size
    des = Image.new('RGBA', (w, num * h + (num - 1) * border), (255, 255, 255, 255))
    for i, pic in enumerate(pics):
        des.paste(pic, (0, i * (h + border)), pic)
    return des


class FreqLimiter:
    def __init__(self, default_cd_seconds):
        self.next_time: dict[float] = defaultdict(float)
        self.default_cd = default_cd_seconds

    def check(self, key) -> bool:
        return bool(time.time() >= self.next_time[key])

    def start_cd(self, key, cd_time=0):
        self.next_time[key] = time.time() + (cd_time if cd_time > 0 else self.default_cd)

    def left_time(self, key) -> float:
        return self.next_time[key] - time.time()


class DailyCountLimiter:
    tz = pytz.timezone('Asia/Shanghai')

    def __init__(self, name, max_num):
        self.today = (datetime.now(self.tz) - timedelta(hours=5)).day
        self._count = defaultdict(int)
        self.max = max_num
        self._dao = dao.CountLimiterDao(name)
        self.init_from_db()

    def check(self, key) -> bool:
        now = datetime.now(self.tz)
        day = (now - timedelta(hours=5)).day
        if day != self.today:
            self.today = day
            self._count.clear()
        return bool(self._count[key] < self.max)

    def get(self, key) -> int:
        return self._count[key]

    def decrease(self, key, count):
        self._count[key] -= count
        self.write(key)

    def increase(self, key, count):
        self._count[key] += count
        self.write(key)

    def reset(self, key):
        self._count[key] = 0
        self.write(key)

    def init_from_db(self):
        for uid, today, count in self._dao.read_gacha_all():
            now = datetime.now(self.tz)
            day = (now - timedelta(hours=5)).day
            if day != today:
                self.reset(uid)
            else:
                self._count[uid] = count

    def read(self, user_id):
        uid, today, count = self._dao.read_gacha_record(user_id)
        self._count[uid] = count
        if today != self.today:
            self.reset(uid)

    def write(self, user_id):
        self._dao.write_gacha_record(user_id, self.today, self._count[user_id])
