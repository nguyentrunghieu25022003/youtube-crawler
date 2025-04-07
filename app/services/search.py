import httpx
from typing import List, Dict
from ..utils import get_youtube_api_key, get_context

SORT_OPTIONS = {
    "relevance": None,
    "upload_date": "CAISAhAB",
    "view_count": "CAMSAhAB",
    "rating": "CAESAhAB",
}

def extract_video_items(items: List[Dict]) -> List[Dict]:
    videos = []

    for item in items:
        content = None

        if "richItemRenderer" in item:
            content = item["richItemRenderer"].get("content", {})
        elif "videoRenderer" in item:
            content = item

        if not content or ("videoRenderer" not in content and "videoId" not in content):
            continue

        video = content.get("videoRenderer") or content

        videos.append({
            "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
            "video_id": video.get("videoId"),
            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}",
            "duration": video.get("lengthText", {}).get("simpleText", ""),
            "views": video.get("viewCountText", {}).get("simpleText", ""),
            "channel": video.get("ownerText", {}).get("runs", [{}])[0].get("text", ""),
            "channel_id": video.get("ownerText", {}).get("runs", [{}])[0]
                .get("navigationEndpoint", {})
                .get("browseEndpoint", {})
                .get("browseId", ""),
            "published_time": video.get("publishedTimeText", {}).get("simpleText", ""),
            "description_snippet": video.get("detailedMetadataSnippets", [{}])[0]
                .get("snippetText", {}).get("runs", [{}])[0].get("text", ""),
            "thumbnails": video.get("thumbnail", {}).get("thumbnails", [])
        })

    return videos


async def search_youtube(query: str, max_results: int = 50, proxy: str = None, sort: str = "relevance") -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    SEARCH_URL = f"https://www.youtube.com/youtubei/v1/search?key={API_KEY}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/"
    }

    collected = []
    continuation = None
    sort_param = SORT_OPTIONS.get(sort)

    async with httpx.AsyncClient(proxies=proxy, headers=headers, timeout=15) as client:
        # First request
        payload = {
            "context": get_context(),
            "query": query
        }
        
        if sort_param:
            payload["params"] = sort_param

        resp = await client.post(SEARCH_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        # Extract initial items
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
        for section in sections:
            if "itemSectionRenderer" in section:
                items = section["itemSectionRenderer"].get("contents", [])
                collected += extract_video_items(items)
            if "continuationItemRenderer" in section:
                continuation = section["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]

        # Continue fetching
        while continuation and len(collected) < max_results:
            payload = {
                "context": get_context(),
                "continuation": continuation
            }

            resp = await client.post(SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            continuation_items = data.get("onResponseReceivedCommands", [])[0] \
                .get("appendContinuationItemsAction", {}) \
                .get("continuationItems", [])

            for section in continuation_items:
                if "itemSectionRenderer" in section:
                    items = section["itemSectionRenderer"].get("contents", [])
                    collected += extract_video_items(items)
                if "continuationItemRenderer" in section:
                    continuation = section["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]

    return collected[:max_results]
