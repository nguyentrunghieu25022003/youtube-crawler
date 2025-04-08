import httpx
from typing import List, Dict
from ..utils import get_context, get_youtube_api_key

async def get_trending_videos(proxy: str = None, max_results: int = 50) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSE_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/"
    }

    collected = []

    async with httpx.AsyncClient(proxies=proxy, headers=headers, timeout=15) as client:
        payload = {
            "context": get_context(),
            "browseId": "FEtrending"
        }

        resp = await client.post(BROWSE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        for tab in tabs:
            contents = tab.get("tabRenderer", {}).get("content", {}) \
                          .get("sectionListRenderer", {}) \
                          .get("contents", [])

            for section in contents:
                items = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in items:
                    shelf = item.get("shelfRenderer", {})
                    horizontal_list = shelf.get("content", {}).get("horizontalListRenderer", {}).get("items", [])
                    for vid in horizontal_list:
                        video = vid.get("gridVideoRenderer", {})
                        if not video:
                            continue
                        collected.append({
                            "videoId": video.get("videoId"),
                            "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
                            "channel": video.get("shortBylineText", {}).get("runs", [{}])[0].get("text", ""),
                            "viewCount": video.get("shortViewCountText", {}).get("simpleText", ""),
                            "published": video.get("publishedTimeText", {}).get("simpleText", ""),
                            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}"
                        })

                        if len(collected) >= max_results:
                            return collected

    return collected