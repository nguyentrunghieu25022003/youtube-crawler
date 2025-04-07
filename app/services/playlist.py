import httpx
import json
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

async def get_playlist_videos(channel_id: str, proxy: str = None) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    BROWSER_URL = f"https://www.youtube.com/youtubei/v1/browse?key={API_KEY}"

    async with httpx.AsyncClient(proxies=proxy, timeout=15) as client:
        payload = await build_web_context()
        payload["browseId"] = channel_id
        resp = await client.post(BROWSER_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        playlists = []

        browse_id = None
        params = None
        for tab in tabs:
            tab_renderer = tab.get("tabRenderer", {})
            if tab_renderer.get("title", "").lower() == "playlists":
                endpoint = tab_renderer.get("endpoint", {}).get("browseEndpoint", {})
                browse_id = endpoint.get("browseId")
                params = endpoint.get("params")
                break

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
                                .get("tabs", [])[3] \
                                .get("tabRenderer", {}) \
                                .get("content", {}) \
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
                    
                    title = (
                        lockup.get("metadata", {})
                            .get("lockupMetadataViewModel", {})
                            .get("title", {})
                            .get("content", "")
                    )

                    video_count = ""
                    overlays = grid_item.get("overlays", [])
                    for overlay in overlays:
                        badges = overlay.get("thumbnailOverlayBadgeViewModel", {}).get("thumbnailBadges", []).get("thumbnailBadgeViewModel", {})
                        for badge in badges:
                            text = badge.get("text", "")
                            if text:
                                video_count = text
                                break
                        if video_count:
                            break
                        
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
                        "videoCount": video_count,
                    })

        return playlists