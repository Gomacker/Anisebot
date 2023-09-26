import abc
import base64
import hashlib
import io
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

import httpx
from PIL import Image, UnidentifiedImageError

from . import playw
from .playw import PlaywrightContext

try:
    from nonebot.adapters.onebot.v11 import Message as Onebot11Message
except ModuleNotFoundError:
    pass


class ImageHandler(abc.ABC):
    @abc.abstractmethod
    async def get(self) -> Optional[Image.Image]:
        pass

    @abc.abstractmethod
    def key(self) -> str:
        pass

    def __str__(self):
        return f'''{self.__class__.__name__}({", ".join([f"""{k}={f'"{v}"' if isinstance(v, str) else v}""" for k, v in self.__dict__.items()])})'''


class ImageHandlerLocalFile(ImageHandler):

    def __init__(self, path: Path):
        self.path: Path = path

    def key(self) -> str:
        pass

    async def get(self) -> Optional[Image.Image]:
        if not self.path.exists():
            return None
        try:
            return Image.open(self.path)
        except Union[FileNotFoundError, UnidentifiedImageError]:
            return None


class Cacheable(abc.ABC):
    @abc.abstractmethod
    def cache(self):
        pass
    @abc.abstractmethod
    def is_cached(self) -> bool:
        pass

    @abc.abstractmethod
    def need_recache(self):
        pass


class ImageHandlerNetwork(ImageHandler, Cacheable):

    def __init__(self, url: str, timeout: float = 30.0):
        self.url: str = url
        self.timeout: float = timeout

    def key(self) -> str:
        return f'Network({self.url})'

    def cache(self):
        pass

    def is_cached(self) -> bool:
        pass

    def need_recache(self):
        pass

    async def get(self) -> Optional[Image.Image]:
        if not self.url:
            return None
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self.url, timeout=self.timeout)
                return Image.open(io.BytesIO(r.content))
        except TimeoutError:
            return None


class ImageHandlerPageScreenshot(ImageHandler, Cacheable):

    def __init__(self, url: str, timeout: float = 30.0, selector: str = '#main-card', **kwargs):
        self.url: str = url
        self.timeout: float = timeout
        self.selector: str = selector
        self.kwargs: dict = kwargs

    def key(self) -> str:
        return f'PageScreenshot({self.url}, {self.selector})'

    def cache(self):
        pass

    def is_cached(self) -> bool:
        pass

    def need_recache(self):
        pass

    async def get(self) -> Optional[Image.Image]:
        try:
            async with PlaywrightContext(**self.kwargs) as context:
                page = await context.new_page()
                await page.goto(self.url, wait_until='networkidle')
                loc = page.locator(self.selector)
                img = await loc.screenshot(type='png', omit_background=True)
            img = Image.open(io.BytesIO(img)).convert('RGBA')
            return img
        except:
            return None


def pic2b64(pic: Image.Image) -> str:
    buf = BytesIO()
    pic.convert('RGBA').save(buf)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return 'base64://' + base64_str


class MessageCard:
    def __init__(self, text='', image_handler=None):
        self.text: str = text
        self.image_handler: Optional[ImageHandler] = image_handler

    async def to_message_onebot11(self, start_time = None) -> "Onebot11Message":
        from nonebot.adapters.onebot.v11 import Message, MessageSegment
        msg = Message()
        if img := await self.image_handler.get():
            img = pic2b64(img)
            msg += MessageSegment.image(img)
        msg = MessageSegment.text(f'''{self.text}\n{f'(耗时{"%.2f" % (time.time() - start_time)}s)' if start_time else ''}''') + msg
        return msg

    def hash(self) -> object:
        return hashlib.md5(f'{self.text}{self.image_handler.hash() if self.image_handler else None}').hexdigest()

    def __str__(self):
        return f'''MessageCard
{'-' * 30}
{self.text}
{self.image_handler}
{'-' * 30}'''
