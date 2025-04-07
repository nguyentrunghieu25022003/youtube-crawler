import httpx
from typing import List, Dict
from ..utils import get_youtube_api_key, get_context

def extract_video_items(items: List[Dict]) -> List[Dict]:
    videos = []
    for item in items:
        content = item.get("richItemRenderer", {}).get("content", {}) or item
        video = content.get("videoRenderer") or content.get("gridVideoRenderer")
        if not video:
            continue
        videos.append({
            "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
            "videoId": video.get("videoId"),
            "url": f"https://www.youtube.com/watch?v={video.get('videoId')}",
            "duration": video.get("lengthText", {}).get("simpleText", ""),
            "views": video.get("viewCountText", {}).get("simpleText", ""),
            "channel": video.get("ownerText", {}).get("runs", [{}])[0].get("text", ""),
        })
    return videos

async def get_channel_videos(channel_id: str, proxy: str = None, max_results: int = 100) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSE_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

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
            "browseId": channel_id
        }

        resp = await client.post(BROWSE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        if not tabs:
            raise Exception("'Tabs' not found")

        videos_browse_id = None
        videos_params = None
        for tab in tabs:
            tab_renderer = tab.get("tabRenderer", {})
            if tab_renderer.get("title", "").lower() == "videos":
                endpoint = tab_renderer.get("endpoint", {}).get("browseEndpoint", {})
                videos_browse_id = endpoint.get("browseId")
                videos_params = endpoint.get("params")
                break

        if not videos_browse_id:
            raise Exception("'Videos' not found")

        payload = {
            "context": get_context(),
            "browseId": videos_browse_id,
            "params": videos_params
        }

        resp = await client.post(BROWSE_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        if not tabs:
            raise Exception("Tabs not found on tab Videos.")

        section = []
        for tab in tabs:
            tab_renderer = tab.get("tabRenderer", {})
            if tab_renderer.get("title", "").lower() == "videos":
                section = tab_renderer.get("content", {}) \
                    .get("richGridRenderer", {}) \
                    .get("contents", [])
                break

        if not section:
            raise Exception("Video list not found on tab Videos.")

        collected += extract_video_items(section)
        continuation = next((
            c.get("continuationItemRenderer", {}).get("continuationEndpoint", {}).get("continuationCommand", {}).get("token")
            for c in section if "continuationItemRenderer" in c
        ), None)

        print(f"[Init] Fetched: {len(collected)} | Continuation: {bool(continuation)}")

        while continuation and len(collected) < max_results:
            payload = {
                "context": get_context(),
                "continuation": continuation
            }

            resp = await client.post(BROWSE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            commands = data.get("onResponseReceivedCommands", [])
            if not commands:
                break

            continuation_items = commands[0].get("appendContinuationItemsAction", {}).get("continuationItems", [])
            new_videos = extract_video_items(continuation_items)
            collected += new_videos

            continuation = next((
                i.get("continuationItemRenderer", {}).get("continuationEndpoint", {}).get("continuationCommand", {}).get("token")
                for i in continuation_items if "continuationItemRenderer" in i
            ), None)

            print(f"[+] Fetched: {len(collected)} | Next: {bool(continuation)}")

    return collected[:max_results]