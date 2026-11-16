import httpx

from .config import settings


class KeitaroError(RuntimeError):
    """An error returned by the Keitaro Admin API."""


class KeitaroClient:
    def __init__(self):
        self.base_url = settings.keitaro_base_url.rstrip("/")
        self.api_key = settings.keitaro_api_key

    async def request(self, method: str, path: str, **kwargs):
        if not self.base_url or not self.api_key or self.api_key == "replace_me":
            raise KeitaroError("Настройте KEITARO_BASE_URL и KEITARO_API_KEY в .env")

        url = f"{self.base_url}/admin_api/v1/{path.lstrip('/')}"
        headers = {"Api-Key": self.api_key}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, url, headers=headers, **kwargs)

        if response.is_error:
            message = response.text[:400]
            raise KeitaroError(f"Keitaro API вернул {response.status_code}: {message}")
        return response.json() if response.content else {}

    async def list(self, path: str, **params):
        return await self.request("GET", path, params=params)

    async def create_campaign(self, payload: dict):
        return await self.request("POST", "campaigns", json=payload)

    async def get_campaign(self, campaign_id: int):
        return await self.request("GET", f"campaigns/{campaign_id}")

    async def create_stream(self, campaign_id: int, payload: dict):
        body = {"campaign_id": campaign_id, **payload}
        return await self.request("POST", "streams", json=body)

    async def streams(self, campaign_id: int):
        return await self.request("GET", f"campaigns/{campaign_id}/streams")

    async def update_stream(self, stream_id: int, payload: dict):
        return await self.request("PUT", f"streams/{stream_id}", json=payload)
