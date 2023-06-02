import playwright
from playwright.async_api import Browser

_browser: Browser | None = None


async def init(proxy=None, **kwargs) -> Browser:
    if proxy:
        kwargs['proxy'] = {'server': proxy}
    global _browser
    p = await playwright.async_api.async_playwright().start()
    _browser = await p.chromium.launch(**kwargs)
    return _browser


async def get_browser(**kwargs) -> Browser:
    return _browser or await init(**kwargs)


async def del_browser():
    del _browser
