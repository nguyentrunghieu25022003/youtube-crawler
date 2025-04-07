import re
import httpx

async def get_youtube_api_key() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://www.youtube.com")
        html = resp.text
        match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
        if not match:
            raise Exception("INNERTUBE_API_KEY not found")
        return match.group(1)
    
def get_context():
    return {
        "client": {
            "hl": "en",
            "gl": "US",
            "clientName": "WEB",
            "clientVersion": "2.20240115.00.00"
        }
    }

async def resolve_channel_id_from_handle(handle: str) -> str:
    async with httpx.AsyncClient() as client:
        url = f"https://www.youtube.com/@{handle}"
        resp = await client.get(url)
        html = resp.text
        match = re.search(r'channel_id=([a-zA-Z0-9_-]{24})', html)
        if match:
            return match.group(1)

        match = re.search(r'"browseId":"(UC[^\"]+)"', html)
        if match:
            return match.group(1)

        raise Exception("Channel_id not found")