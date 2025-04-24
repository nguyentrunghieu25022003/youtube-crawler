import httpx
from typing import List, Dict
from ..utils import get_youtube_api_key

async def build_web_context() -> Dict:
    return {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20230401.01.00"
            }
        }
    }
    
def extract_playlists_tab_info(data):
    tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])

    browse_id = None
    params = None

    for tab in tabs:
        tab_renderer = tab.get("tabRenderer", {})
        title = tab_renderer.get("title", "").lower()
        if title == "videos":
            endpoint = tab_renderer.get("endpoint", {}).get("browseEndpoint", {})
            browse_id = endpoint.get("browseId")
            params = endpoint.get("params")
            break

    if not browse_id or not params:
        raise Exception("Cannot find browseId or params for the Playlists tab.")

    return browse_id, params


async def get_playlist_videos(channel_id: str, proxy: str = None) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSER_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

    async with httpx.AsyncClient(proxies=proxy, timeout=15) as client:
        payload = await build_web_context()
        payload["browseId"] = channel_id
        resp = await client.post(BROWSER_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        playlists = []

        browse_id, params = extract_playlists_tab_info(data)

        if not browse_id or not params:
            raise Exception("browseId and params not found")

        payload = await build_web_context()
        payload["browseId"] = browse_id
        payload["params"] = params

        resp = await client.post(BROWSER_URL, json=payload)
        resp.raise_for_status()
        playlist_data = resp.json()

        contents = playlist_data.get("contents", {}) \
                                .get("twoColumnBrowseResultsRenderer", {}) \
                                .get("tabs", [])
                                
        target_tab = None
        for tab in contents:
            tab_renderer = tab.get("tabRenderer", {})
            title = tab_renderer.get("title", "").lower()
            if title == "playlists":
                target_tab = tab_renderer
                break

        if not target_tab or "content" not in target_tab:
            endpoint = target_tab.get("endpoint", {}).get("browseEndpoint", {})
            browse_id = endpoint.get("browseId")
            params = endpoint.get("params")
            if not browse_id or not params:
                raise Exception("browseId and params not found")

            payload = await build_web_context()
            payload["browseId"] = browse_id
            payload["params"] = params

            resp = await client.post(BROWSER_URL, json=payload)
            resp.raise_for_status()
            playlist_data = resp.json()

            contents = playlist_data.get("contents", {}) \
                                    .get("twoColumnBrowseResultsRenderer", {}) \
                                    .get("tabs", [])
            target_tab = next(
                (tab.get("tabRenderer", {}) for tab in contents
                 if tab.get("tabRenderer", {}).get("title", "").lower() == "playlists"),
                None
            )
            if not target_tab:
                raise Exception("Playlists not load from browseEndpoint")

        contents = target_tab.get("content", {}) \
                             .get("sectionListRenderer", {})

        for section in contents.get("contents", []):
            item_section = section.get("itemSectionRenderer", {})
            for item in item_section.get("contents", []):
                for grid_item in item.get("gridRenderer", {}).get("items", []):
                    lockup = grid_item.get("lockupViewModel", {})
                    thumbnail_url = (
                        lockup.get("contentImage", {})
                              .get("collectionThumbnailViewModel", {})
                              .get("primaryThumbnail", {})
                              .get("thumbnailViewModel", {})
                              .get("image", {})
                              .get("sources", [{}])[-1]
                              .get("url", "")
                    )
                    
                    import json
                    with open("playlist_error_dump.json", "w", encoding="utf-8") as f:
                        json.dump(lockup, f, ensure_ascii=False, indent=2)
                    videoCount = ""
                    
                    overlays = (
                        lockup.get("contentImage", {})
                              .get("collectionThumbnailViewModel", {})
                              .get("primaryThumbnail", {})
                              .get("thumbnailViewModel", {})
                              .get("overlays", [])
                    )

                    for overlay in overlays:
                        badge = overlay.get("thumbnailOverlayBadgeViewModel", {}).get("thumbnailBadges", [])
                        if badge:
                            videoCount = badge[0].get("thumbnailBadgeViewModel", {}).get("text", "")
                            if videoCount:
                                break
                    
                    title = (
                        lockup.get("metadata", {})
                            .get("lockupMetadataViewModel", {})
                            .get("title", {})
                            .get("content", "")
                    )
                        
                    playlist_id = (
                        lockup.get("rendererContext", {})
                            .get("commandContext", {})
                            .get("onTap", {})
                            .get("innertubeCommand", {})
                            .get("watchEndpoint", {})
                            .get("playlistId", "")
                    )

                    playlists.append({
                        "playlistId": playlist_id,
                        "title": title,
                        "thumbnail": thumbnail_url,
                        "videoCount": videoCount
                    })

        return playlists

def extract_title(title_obj):
    if "simpleText" in title_obj:
        return title_obj["simpleText"]
    elif "runs" in title_obj and title_obj["runs"]:
        return "".join([run.get("text", "") for run in title_obj["runs"]])
    return ""

async def get_videos_from_playlist(playlist_id: str, proxy: str = None) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSER_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

    payload = await build_web_context()
    payload["browseId"] = f"VL{playlist_id}"

    videos = []

    async with httpx.AsyncClient(proxies=proxy, timeout=15) as client:
        while True:
            resp = await client.post(BROWSER_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            if "contents" not in data:
                raise Exception("Invalid response structure")

            try:
                contents = (
                    data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]
                    ["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]
                    ["itemSectionRenderer"]["contents"][0]["playlistVideoListRenderer"]["contents"]
                )
            except Exception as e:
                print("[!] Error parsing playlist content:", e)
                break

            continuation_token = None

            for item in contents:
                if "playlistVideoRenderer" in item:
                    renderer = item["playlistVideoRenderer"]
                    videos.append({
                        "video_id": renderer.get("videoId"),
                        "title": extract_title(renderer.get("title", {})),
                        "published_time": renderer.get("publishedTimeText", {}).get("simpleText", ""),
                        "duration": renderer.get("lengthText", {}).get("simpleText", ""),
                        "thumbnail": renderer.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "")
                    })
                elif "continuationItemRenderer" in item:
                    continuation_token = (
                        item["continuationItemRenderer"]
                        ["continuationEndpoint"]["continuationCommand"]["token"]
                    )

            if continuation_token:
                payload = await build_web_context()
                payload["continuation"] = continuation_token
            else:
                break

    return videos
