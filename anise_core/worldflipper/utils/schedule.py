import asyncio
import io

from PIL import Image

from anise_core.worldflipper.playw import get_browser


async def get_schedule() -> Image.Image:
    b = await get_browser()
    page = await b.new_page(viewport={'width': 1036, 'height': 120})
    url = f'https://wf-calendar.miaowm5.com/'
    await page.goto(url, wait_until='load')
    await page.click('body', position={'x': 315, 'y': 200})
    await page.wait_for_load_state(state='networkidle', timeout=1000000)
    img = await page.screenshot(full_page=True)
    await page.close()
    return Image.open(io.BytesIO(img))


async def main():
    (await get_schedule()).show()


if __name__ == '__main__':
    asyncio.run(main())
