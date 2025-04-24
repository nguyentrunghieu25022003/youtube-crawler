import httpx
from typing import List, Dict
from ..utils import get_context, get_youtube_api_key

SEARCH_URL = "https://www.youtube.com/youtubei/v1/search"

def extract_live_videos(items: List[Dict]) -> List[Dict]:
    videos = []
    for item in items:
        video = item.get("videoRenderer")
        if not video:
            continue
        view_count = ""
        if "shortViewCountText" in video:
            view_count = video["shortViewCountText"].get("simpleText") or \
                video["shortViewCountText"].get("runs", [{}])[0].get("text", "")
                 
        videos.append({
            "video_id": video.get("videoId"),
            "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
            "thumbnail": video.get("thumbnail", {}).get("thumbnails", []),
            "channel_name": video.get("ownerText", {}).get("runs", [{}])[0].get("text", ""),
            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}",
            "views": view_count,
            "is_live": True
        })
    return videos

async def get_all_live_videos(q: str, proxy: str = None, max_results: int = 100) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/"
    }

    collected = []
    continuation = None

    async with httpx.AsyncClient(proxies=proxy, headers=headers, timeout=15) as client:
        payload = {
            "context": get_context(),
            "query": q,
            "params": "EgJAAQ%3D%3D"
        }
        resp = await client.post(f"{SEARCH_URL}?key={API_KEY}", json=payload)
        resp.raise_for_status()
        data = resp.json()

        contents = data.get("contents", {}) \
                       .get("twoColumnSearchResultsRenderer", {}) \
                       .get("primaryContents", {}) \
                       .get("sectionListRenderer", {}) \
                       .get("contents", [])

        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            collected += extract_live_videos(items)

        continuation = next((
            section.get("continuationItemRenderer", {})
                   .get("continuationEndpoint", {})
                   .get("continuationCommand", {})
                   .get("token")
            for section in contents
            if "continuationItemRenderer" in section
        ), None)

        while continuation and len(collected) < max_results:
            payload = {
                "context": get_context(),
                "continuation": continuation
            }
            resp = await client.post(f"{SEARCH_URL}?key={API_KEY}", json=payload)
            resp.raise_for_status()
            data = resp.json()

            continuation_items = data.get("onResponseReceivedCommands", [])[0] \
                                     .get("appendContinuationItemsAction", {}) \
                                     .get("continuationItems", [])

            collected += extract_live_videos(continuation_items)

            continuation = next((
                item.get("continuationItemRenderer", {})
                    .get("continuationEndpoint", {})
                    .get("continuationCommand", {})
                    .get("token")
                for item in continuation_items
                if "continuationItemRenderer" in item
            ), None)

    return collected[:max_results]
