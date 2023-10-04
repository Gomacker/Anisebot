import httpx

from ....anise import config


class UpdateManager:
    def __init__(self, url: str = config.METEORHOUSE_URL, query_config_url: str = config.config.query.config_url):
        self.url = url
        self.query_config_url = query_config_url

    async def update(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(self.query_config_url)

