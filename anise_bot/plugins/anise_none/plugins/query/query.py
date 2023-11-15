import abc
import asyncio
import dataclasses
import enum
import io
import json
import os
import re
import time
import urllib.parse
from typing import Any, Optional, Type, Union

import httpx
from PIL import Image
from nonebot import logger
from pydantic import BaseModel

from ... import update
from ...utils import (
    MessageCard, ImageHandlerLocalFile, ImageHandlerNetwork, ImageHandlerPageScreenshot,
    ImageHandlerPostProcessor, PlaywrightContext
)
from ...anise.config import METEORHOUSE_URL, RES_PATH, CALENDAR_URL, config
from ...anise.query.alias import alias_manager
from ...models.worldflipper import Equipment, Character


class QueryHandler(BaseModel, abc.ABC):
    """用来代替 QuerySet"""
    type: str

    def __init__(self, **data: Any):
        super().__init__(**data)

    async def check(self, text: str) -> Any:
        return None

    @abc.abstractmethod
    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        return None


class QueryHandlerRegex(QueryHandler, abc.ABC):
    regex: str = ''

    async def check(self, text: str) -> bool:
        return not self.regex or bool(re.search(self.regex, text))


class QueryHandlerText(QueryHandlerRegex):
    content: str = ''

    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        mc = MessageCard()
        mc.text = self.content
        return mc


class QueryHandlerImage(QueryHandlerRegex):
    src: str = ''

    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        if self.src:
            return MessageCard(image_handler=ImageHandlerLocalFile(RES_PATH / 'query' / 'local' / self.src))
        return None


class QueryHandlerServerImage(QueryHandlerRegex):
    url: str = ''

    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        mc = MessageCard()
        mc.image_handler = ImageHandlerNetwork(self.url)
        return mc


class QueryHandlerServerTable(QueryHandlerRegex):
    table_id: str = ''

    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        ih = ImageHandlerPageScreenshot(
            urllib.parse.urljoin(
                METEORHOUSE_URL,
                f'/card/table/?table_id={urllib.parse.quote(self.table_id)}&show_replacements=true'
            ),
            selector='.table',
            cache_path_getter=lambda x: RES_PATH / 'query' / 'cache' / 'table' / f'{self.table_id}.png'
        )
        return MessageCard(
            text=urllib.parse.urljoin(METEORHOUSE_URL, f'/table/{urllib.parse.quote(self.table_id)}'),
            image_handler=ih
        )


class EnumObjectResType(enum.Enum):
    WIKICARD = 0
    FULL_SHOT_0 = 1
    FULL_SHOT_1 = 2
    PIXEL_ART_SPECIAL = 3
    PIXEL_ART_WALK_FRONT = 4
    PIXEL_ART_KACHI = 5


class QueryHandlerWorldflipperObject(QueryHandler):
    strict: bool = True

    @dataclasses.dataclass
    class CheckResult:
        type: EnumObjectResType
        obj: Union[Character, Equipment]

    async def check(self, text: str) -> Optional[CheckResult]:
        res_type = EnumObjectResType.WIKICARD
        if text.endswith('觉醒立绘'):
            res_type = EnumObjectResType.FULL_SHOT_1
            text = text.removesuffix('觉醒立绘')
        elif text.endswith('立绘'):
            res_type = EnumObjectResType.FULL_SHOT_0
            text = text.removesuffix('立绘')
        elif text.endswith('pasp'):
            res_type = EnumObjectResType.PIXEL_ART_SPECIAL
            text = text.removesuffix('pasp')
        elif text.endswith('pawf'):
            res_type = EnumObjectResType.PIXEL_ART_WALK_FRONT
            text = text.removesuffix('pawf')
        elif text.endswith('pakc'):
            res_type = EnumObjectResType.PIXEL_ART_KACHI
            text = text.removesuffix('pakc')

        if self.strict:
            obj = alias_manager.get_obj(text)
        else:
            obj = alias_manager.guess(text)
        if obj:
            return QueryHandlerWorldflipperObject.CheckResult(
                res_type,
                obj
            )
        return None

    async def get_message(self, check_result: CheckResult) -> Optional[MessageCard]:
        id_ = check_result.obj.id
        res_id = check_result.obj.resource_id
        ih = None
        if isinstance(check_result.obj, Character):
            def full_shot_post_process(image: Image.Image):
                bg = Image.new('RGB', size=image.size, color=(240, 240, 240))
                bg.paste(image, mask=image)
                return bg.convert('RGBA')

            if check_result.type == EnumObjectResType.FULL_SHOT_0:
                ih = ImageHandlerPostProcessor(
                    ImageHandlerNetwork(
                        urllib.parse.urljoin(
                            METEORHOUSE_URL,
                            f'/static/worldflipper/unit/full_resized/base/{check_result.obj.resource_id}.png'
                        ),
                        cache_path_getter=lambda
                            x: RES_PATH / check_result.obj.type_id() / 'full_shot_0' / f'{res_id}.png'
                    ),
                    post_process=full_shot_post_process
                )
            elif check_result.type == EnumObjectResType.FULL_SHOT_1:
                ih = ImageHandlerPostProcessor(
                    ImageHandlerNetwork(
                        urllib.parse.urljoin(
                            METEORHOUSE_URL,
                            f'/static/worldflipper/unit/full_resized/awakened/{check_result.obj.resource_id}.png'
                        ),
                        cache_path_getter=lambda
                            x: RES_PATH / check_result.obj.type_id() / 'full_shot_1' / f'{res_id}.png'
                    ),
                    post_process=full_shot_post_process
                )
            elif check_result.type == EnumObjectResType.PIXEL_ART_SPECIAL:
                ih = ImageHandlerNetwork(
                    urllib.parse.urljoin(
                        METEORHOUSE_URL,
                        f'/static/worldflipper/unit/pixelart/special/{check_result.obj.resource_id}.gif'
                    ),
                    cache_path_getter=lambda
                        x: RES_PATH / check_result.obj.type_id() / 'pixelart/special' / f'{res_id}.gif'
                )
            elif check_result.type == EnumObjectResType.PIXEL_ART_WALK_FRONT:
                ih = ImageHandlerNetwork(
                    urllib.parse.urljoin(
                        METEORHOUSE_URL,
                        f'/static/worldflipper/unit/pixelart/walk_front/{check_result.obj.resource_id}.gif'
                    ),
                    cache_path_getter=lambda
                        x: RES_PATH / check_result.obj.type_id() / 'pixelart/walk_front' / f'{res_id}.gif'
                )
            elif check_result.type == EnumObjectResType.PIXEL_ART_KACHI:
                ih = ImageHandlerNetwork(
                    urllib.parse.urljoin(
                        METEORHOUSE_URL,
                        f'/static/worldflipper/unit/pixelart/kachidoki/{check_result.obj.resource_id}.gif'
                    ),
                    cache_path_getter=lambda
                        x: RES_PATH / check_result.obj.type_id() / 'pixelart/kachidoki' / f'{res_id}.gif'
                )
            else:
                ih = ImageHandlerPageScreenshot(
                    urllib.parse.urljoin(METEORHOUSE_URL, f'/card/character/?wf_id={id_}'),
                    selector='#main-card',
                    cache_path_getter=lambda x: RES_PATH / 'query' / 'cache' / 'wikicard' / check_result.obj.type_id() / f'{res_id}.png'
                )
        elif isinstance(check_result.obj, Equipment):
            ih = ImageHandlerPageScreenshot(
                    urllib.parse.urljoin(METEORHOUSE_URL, f'/card/equipment/?wf_id={id_}'),
                    selector='#main-card',
                    cache_path_getter=lambda x: RES_PATH / 'query' / 'cache' / 'wikicard' / check_result.obj.type_id() / f'{res_id}.png'
                )
        mc = MessageCard(
            image_handler=ih
        )
        # self.obj = None
        return mc


class QueryHandlerWorldflipperScheduler(QueryHandlerRegex):
    class ImageHandlerScheduler(ImageHandlerPageScreenshot):
        """这是一个临时用的日程抓取器，在正式版本中在Meteorhouse重写"""
        def key(self) -> str:
            return f'Scheduler({self.url}, {self.selector})'

        async def get(self) -> Optional[Image.Image]:
            try:
                if await self.need_recache() or not self.is_cached():
                    async with PlaywrightContext(**self.kwargs) as context:
                        page = await context.new_page()
                        await page.goto(self.url, wait_until='load')
                        await page.click('body', position={'x': 440, 'y': 195})
                        await page.wait_for_load_state(state='networkidle', timeout=600000)
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

    async def get_message(self, check_result: Any) -> Optional[MessageCard]:
        return MessageCard(
            image_handler=QueryHandlerWorldflipperScheduler.ImageHandlerScheduler(
                CALENDAR_URL,
                cache_path_getter=lambda x: RES_PATH / 'query' / 'cache' / 'calendar.png'
            )
        )


class QueryHandlerWorldflipperPurePartySearcher(QueryHandler):
    @dataclasses.dataclass
    class CheckResult:
        text: str
        page_index: int

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

    async def check(self, text: str) -> Optional[CheckResult]:
        if not text:
            return None
        text, page_index = self.get_text_and_page(text)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                urllib.parse.urljoin(
                    METEORHOUSE_URL,
                    f'/api/v1/party/page/?search_text={text}&page_index={page_index}'
                ),
                timeout=20.0
            )
            if response.status_code == 200:
                d: dict = response.json()
                pts = d.get('parties', {})
                if pts:
                    return QueryHandlerWorldflipperPurePartySearcher.CheckResult(
                        text,
                        page_index
                    )
        return None

    async def get_message(self, check_result: CheckResult) -> Optional[MessageCard]:
        hash_key = f'{check_result.text}_page{check_result.page_index}'
        return MessageCard(
            image_handler=ImageHandlerPageScreenshot(
                urllib.parse.urljoin(
                    METEORHOUSE_URL,
                    f'/pure/partySearcher/?q={urllib.parse.quote(check_result.text)}&page={check_result.page_index}',
                ),
                cache_path_getter=lambda x: RES_PATH / 'query' / 'cache' / 'party_page' / f'{hash_key}.png'
            )
        )


class QueryHandlerWorldflipperPartyRefer(QueryHandler):
    @dataclasses.dataclass
    class CheckResult:
        pic: Image.Image
        party_code: str

    async def check(self, text: str) -> Optional[CheckResult]:
        text = text.strip()
        if re.match(r'[a-zA-Z0-9]{6}$', text) and not text.isdigit():
            pic = await self.get_image(text)
            if pic:
                return QueryHandlerWorldflipperPartyRefer.CheckResult(pic, text)
        return None

    async def get_image(self, party_code: str) -> Optional[Image.Image]:

        cache_path = RES_PATH / 'query' / 'cache' / 'party_refer' / f'{party_code}.png'
        try:
            if not cache_path.exists():
                async with PlaywrightContext() as context:
                    page = await context.new_page()
                    url = urllib.parse.urljoin(METEORHOUSE_URL, f'/card/party_refer/?id={party_code}')
                    await page.goto(url)
                    await page.wait_for_selector('#card-complete')
                    if await page.query_selector('#main-card'):
                        print('wait networkidle')
                        await page.wait_for_load_state('networkidle')
                        locator = page.locator('#main-card')
                        img = await locator.screenshot()
                        img = Image.open(io.BytesIO(img))
                    else:
                        img = None
                    return img
            return Image.open(cache_path)
        except:
            return None

    async def get_message(self, check_result: CheckResult) -> Optional[MessageCard]:
        cache_path = RES_PATH / 'query' / 'cache' / 'party_refer' / f'{check_result.party_code}.png'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        check_result.pic.save(cache_path)
        return MessageCard(image_handler=ImageHandlerLocalFile(cache_path))


class QueryManager:

    def __init__(self):
        self.registered_handler_type: dict[str, Type[QueryHandler]] = {}
        self.query_handlers: list[QueryHandler] = []

    def register(self, handler_type: Type[QueryHandler], name: str):
        self.registered_handler_type[name] = handler_type

    def read_query_handler(self, data: dict) -> Optional[QueryHandler]:
        type_ = data.get('type', '')
        if not type_:
            return None
        TQH: Type[QueryHandler] = self.registered_handler_type.get(type_)
        if not TQH:
            logger.error(f"QueryManager can't read type: {type_}")
            return None
        return TQH(**data)

    async def init(self, path=RES_PATH):
        if config.query.update_on_startup:
            await update.manager.update()
        self.query_handlers.clear()
        config_path = path / 'query' / 'config.json'
        if not path.exists():
            os.makedirs(path.parent, exist_ok=True)
            config_path.write_text(json.dumps({'query_map': []}))
        query_config: list = json.loads(config_path.read_text('utf-8')).get('query_map', '')
        self.query_handlers: list = list(filter(None, [self.read_query_handler(x) for x in query_config]))
        return len(self.query_handlers)

    def load_default_type(self):
        self.register(QueryHandlerText, 'text')
        self.register(QueryHandlerText, 'Text')

        self.register(QueryHandlerImage, 'image')
        self.register(QueryHandlerImage, 'Image')
        self.register(QueryHandlerImage, 'local_image')
        self.register(QueryHandlerImage, 'LocalImage')
        self.register(QueryHandlerImage, 'image_local')
        self.register(QueryHandlerImage, 'ImageLocal')

        self.register(QueryHandlerServerImage, 'server_image')
        self.register(QueryHandlerServerImage, 'ServerImage')
        self.register(QueryHandlerServerImage, 'image_server')
        self.register(QueryHandlerServerImage, 'ImageServer')

        self.register(QueryHandlerServerTable, 'server_table')
        self.register(QueryHandlerServerTable, 'ServerTable')

    def load_worldflipper_type(self):

        self.register(QueryHandlerWorldflipperScheduler, 'schedule')
        self.register(QueryHandlerWorldflipperScheduler, 'Schedule')

        self.register(QueryHandlerWorldflipperObject, 'wfo')
        self.register(QueryHandlerWorldflipperObject, 'WorldflipperObject')
        self.register(QueryHandlerWorldflipperObject, 'worldflipper_object')

        self.register(QueryHandlerWorldflipperPartyRefer, 'party_refer')
        self.register(QueryHandlerWorldflipperPartyRefer, 'PartyRefer')

        self.register(QueryHandlerWorldflipperPurePartySearcher, 'pps')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'PurePartySearcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'pure_party_searcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'PartySearcher')
        self.register(QueryHandlerWorldflipperPurePartySearcher, 'party_searcher')

    async def query(self, text: str) -> Optional[MessageCard]:
        try:
            text = text.strip()
            for handler in self.query_handlers:
                if check_result := await handler.check(text):
                    mc = await handler.get_message(check_result)
                    if mc:
                        return mc
            else:
                return None
        except Exception as e:
            raise e


_QM = None


async def get_query() -> QueryManager:
    global _QM
    if _QM is None:
        _QM = QueryManager()
        _QM.load_default_type()
        _QM.load_worldflipper_type()
        await _QM.init()
    return _QM

asyncio.get_event_loop().run_until_complete(get_query())


if __name__ == '__main__':
    async def main():
        t = time.time()
        # print(f'(耗时{"%.2f" % (time.time() - t)}s)')
        qm = await get_query()
        mc = await qm.query('雷废')
        print(mc)
        # for query_handler in qm.query_handlers:
        #     print(query_handler)


    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    asyncio.set_event_loop(loop)
