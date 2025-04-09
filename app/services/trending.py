import json
import httpx
from typing import List, Dict
from ..utils import get_youtube_api_key, get_context

def extract_videos(items: List[Dict]) -> List[Dict]:
    results = []
    for item in items:
        video = item.get("videoRenderer") or item.get("gridVideoRenderer")
        if not video:
            continue
        results.append({
            "videoId": video.get("videoId"),
            "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
            "channel": video.get("shortBylineText", {}).get("runs", [{}])[0].get("text", ""),
            "viewCount": video.get("shortViewCountText", {}).get("simpleText", ""),
            "published": video.get("publishedTimeText", {}).get("simpleText", ""),
            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}"
        })
    return results

def extract_videos_from_item(item: Dict) -> List[Dict]:
    if "carouselRenderer" in item:
        carousel = item["carouselRenderer"]
        return extract_videos(carousel.get("contents", []))
    
    elif "shelfRenderer" in item:
        shelf = item["shelfRenderer"]
        items = shelf.get("content", {}) \
                     .get("expandedShelfContentsRenderer", {}) \
                     .get("items", [])
        return extract_videos(items)
    return []

async def get_trending_videos(proxy: str = None, max_results: int = 100) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSE_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com"
    }

    collected = []
    continuation = None

    async with httpx.AsyncClient(proxies=proxy, headers=headers, timeout=15) as client:
        payload = {"context": get_context(), "browseId": "FEtrending"}
        resp = await client.post(BROWSE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        with open("debug_trending_first.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        renderers = data.get("contents", {}) \
                        .get("twoColumnBrowseResultsRenderer", {}) \
                        .get("tabs", [])[0] \
                        .get("tabRenderer", {}) \
                        .get("content", {}) \
                        .get("sectionListRenderer", {}) \
                        .get("contents", [])

        for section in renderers:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                videos = extract_videos_from_item(item)
                if videos:
                    collected += videos
                    if "carouselRenderer" in item:
                        continuation = item["carouselRenderer"].get("continuations", [{}])[0] \
                                          .get("nextContinuationData", {}) \
                                          .get("continuation")
                                          
        while continuation and len(collected) < max_results:
            payload = {"context": get_context(), "continuation": continuation}
            resp = await client.post(BROWSE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("onResponseReceivedActions", [{}])[0] \
                        .get("appendContinuationItemsAction", {}) \
                        .get("continuationItems", [])
            collected += extract_videos(items)
        
            continuation = next(
                (item.get("continuationItemRenderer", {}) \
                    .get("continuationEndpoint", {}) \
                    .get("continuationCommand", {}) \
                    .get("token")
                 for item in items if "continuationItemRenderer" in item),
                None
            )

    return collected[:max_results]