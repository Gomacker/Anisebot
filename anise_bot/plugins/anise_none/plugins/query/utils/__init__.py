import abc
import base64
import hashlib
import io
import time
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, Callable, Any

import httpx
from PIL import Image, UnidentifiedImageError, ImageSequence

from anise_bot.plugins.anise_none.anise.config import METEORHOUSE_URL
from . import playw
from .playw import PlaywrightContext

try:
    from nonebot.adapters.onebot.v11 import Message as Onebot11Message
except ModuleNotFoundError:
    pass


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


def pic2b64(pic: Image.Image, format_: str = 'PNG') -> str:
    buf = BytesIO()
    pic.convert('RGBA').save(buf, format=format_)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return 'base64://' + base64_str


class ImageHandler(abc.ABC):
    @abc.abstractmethod
    async def get(self) -> Optional[Image.Image]:
        pass

    @abc.abstractmethod
    def key(self) -> str:
        pass

    def __str__(self):
        return f'''{self.__class__.__name__}({", ".join([f"""{k}={f'"{v}"' if isinstance(v, str) else v}""" for k, v in self.__dict__.items()])})'''

    async def to_io(self, image: Image.Image) -> Optional[io.BytesIO]:
        buf = BytesIO()
        image.convert('RGBA').save(buf, format='PNG')
        return buf

    async def get_io(self) -> Optional[io.BytesIO]:
        pic = await self.get()
        if not pic:
            return None
        return await self.to_io(pic)


class ImageHandlerLocalFile(ImageHandler):

    def __init__(self, path: Path):
        self.path: Path = path

    def key(self) -> str:
        pass

    async def get(self) -> Optional[Image.Image]:
        return Image.open(self.path)


class Cacheable(abc.ABC):
    @abc.abstractmethod
    def cache(self, obj: Any):
        pass

    @abc.abstractmethod
    def is_cached(self) -> bool:
        pass

    @abc.abstractmethod
    async def need_recache(self):
        pass


class BasicTimerCache(Cacheable):

    def __init__(self, cache_path_getter: Optional[Callable[["BasicTimerCache"], Path]]):
        self.cache_path_getter = cache_path_getter

    def cache(self, obj: io.BytesIO):
        if self.cache_path_getter:
            cache_path = self.cache_path_getter(self)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(obj.getvalue())

    def is_cached(self) -> bool:
        if self.cache_path_getter:
            return Path(self.cache_path_getter(self)).exists()
        return False

    async def need_recache(self):
        if self.cache_path_getter:
            cache_path = Path(self.cache_path_getter(self))
            cache_timeout = 60 * 60 * 24
            return not cache_path.exists() or cache_path.stat().st_mtime + cache_timeout < time.time()
        return False


class ImageHandlerNetwork(ImageHandler, BasicTimerCache):

    def __init__(
            self, url: str, timeout: float = 30.0,
            cache_path_getter: Optional[Callable[["ImageHandlerNetwork"], Path]] = None):
        super().__init__(cache_path_getter)
        self.url: str = url
        self.timeout: float = timeout
        self.content_type: str = 'image/png'

    def key(self) -> str:
        return f'Network({self.url})'

    async def get(self) -> Optional[Image.Image]:
        if not self.url:
            return None
        try:
            if await self.need_recache() or not self.is_cached():
                async with httpx.AsyncClient() as client:
                    r = await client.get(urllib.parse.urljoin(METEORHOUSE_URL, self.url), timeout=self.timeout)
                    self.content_type = r.headers['content-type']
                    if r.status_code // 100 == 2:
                        img = Image.open(io.BytesIO(r.content))
                        self.cache(await self.to_io(img))
                        return img
                    else:
                        return None
            else:
                path = self.cache_path_getter(self)
                img: Image.Image = Image.open(path)
                if path.suffix == '.gif':
                    self.content_type = 'image/gif'
                return img
        except TimeoutError:
            return None

    async def to_io(self, image: Image.Image) -> Optional[io.BytesIO]:
        if self.content_type == 'image/gif':
            buf = io.BytesIO()
            image.save(buf, format='GIF', save_all=True, loop=0, disposal=2)
            return buf
        else:
            return await super().to_io(image)


class ImageHandlerPageScreenshot(ImageHandler, BasicTimerCache):

    def __init__(
            self,
            url: str,
            timeout: float = 30.0,
            selector: str = 'body',
            cache_path_getter: Optional[Callable[["ImageHandlerPageScreenshot"], Path]] = None,
            **kwargs
    ):
        super().__init__(cache_path_getter)
        self.url: str = url
        self.timeout: float = timeout
        self.selector: str = selector
        self.kwargs: dict = kwargs

    def key(self) -> str:
        return f'PageScreenshot({self.url}, {self.selector})'

    async def get(self) -> Optional[Image.Image]:
        try:
            if await self.need_recache() or not self.is_cached():
                async with PlaywrightContext(**self.kwargs) as context:
                    page = await context.new_page()
                    await page.goto(self.url, wait_until='networkidle')
                    loc = page.locator(self.selector)
                    img = await loc.screenshot(type='png', omit_background=True)
                img = Image.open(io.BytesIO(img)).convert('RGBA')
                self.cache(await self.to_io(img))
                return img
            else:
                img = Image.open(self.cache_path_getter(self))
                return img
        except Exception as e:
            raise e


class ImageHandlerPostProcessor(ImageHandler):

    def __init__(self, ih: ImageHandler, post_process: Callable[[Image.Image], Image.Image]):
        self.ih: ImageHandler = ih
        self.post_process: Callable[[Image.Image], Image.Image] = post_process

    async def get(self) -> Optional[Image.Image]:
        img = await self.ih.get()
        # return self.post_process(img, self.ih)
        return self.post_process(img)

    def key(self) -> str:
        return self.ih.key()


class MessageCard:
    def __init__(self, text='', image_handler=None):
        self.text: str = text
        self.image_handler: Optional[ImageHandler] = image_handler

    async def to_message_onebot11(self, start_time=None) -> "Onebot11Message":
        from nonebot.adapters.onebot.v11 import Message, MessageSegment
        msg = Message()
        # if self.image_handler and (img := await self.image_handler.get()):
        if self.image_handler and (img := await self.image_handler.get_io()):
            # img = pic2b64(img)
            msg += MessageSegment.image(img)
        msg = MessageSegment.text(f'''{self.text} ''' + (
            '\n' if self.text else '') + f'''{f'(耗时{"%.2f" % (time.time() - start_time)}s)' if start_time else ''}''') + msg
        return msg

    def hash(self) -> object:
        return hashlib.md5(
            f'{self.text}{self.image_handler.key() if self.image_handler else None}'.encode()).hexdigest()

    def __str__(self):
        return f'''MessageCard
{'-' * 30}
{self.text}
{self.image_handler}
{'-' * 30}'''
