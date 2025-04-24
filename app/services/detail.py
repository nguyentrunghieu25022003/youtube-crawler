import httpx
from ..utils import get_youtube_api_key, get_context

async def get_video_detail(video_id: str, proxy: str = None):
    API_KEY = await get_youtube_api_key()
    VIDEO_DETAIL_URL = f"https://www.youtube.com/youtubei/v1/player?key={API_KEY}"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com"
    }

    payload = {
        "context": get_context(),
        "videoId": video_id
    }

    async with httpx.AsyncClient(proxies=proxy, headers=headers, timeout=10) as client:
        resp = await client.post(VIDEO_DETAIL_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("playabilityStatus", {})
        if status.get("status") != "OK":
            return {
                "error": True,
                "reason": status.get("reason", "Unavailable"),
                "status": status.get("status")
            }

        video_details = data.get("videoDetails", {})
        streaming_data = data.get("streamingData", {})
        
        return {
            "video_id": video_details.get("videoId"),
            "title": video_details.get("title"),
            "author": video_details.get("author"),
            "length_seconds": video_details.get("lengthSeconds"),
            "views": video_details.get("viewCount"),
            "is_live_content": video_details.get("isLiveContent"),
            "formats": streaming_data.get("formats", []),
            "adaptive_formats": streaming_data.get("adaptiveFormats", [])
        }
