from typing import Optional

import playwright
from playwright.async_api import Browser, BrowserContext

from ....anise.config import DATA_PATH

_browser: Optional[Browser] = None


async def init(proxy=None, **kwargs) -> Browser:
    if proxy:
        kwargs['proxy'] = {'server': proxy}
    global _browser
    p = await playwright.async_api.async_playwright().start()
    _browser = await p.chromium.launch(**kwargs)
    return _browser


async def get_browser(**kwargs) -> Browser:
    return _browser or await init(**kwargs)


class PlaywrightContext:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.store_path = DATA_PATH / 'state.json'
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        b = await get_browser(**self.kwargs)

        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text('{}', encoding='utf-8')
        print(self.store_path)

        try:
            self.context = await b.new_context(storage_state=self.store_path)
        except Exception:
            b = await init(**self.kwargs)
            self.context = await b.new_context(storage_state=self.store_path)
        return self.context

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.context.storage_state(path=self.store_path)
        await self.context.close()


async def del_browser():
    del _browser
