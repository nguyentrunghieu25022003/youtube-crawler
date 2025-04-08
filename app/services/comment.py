import httpx
from typing import List, Dict
from ..utils import get_youtube_api_key, get_context


def extract_comment_continuation_token(data: dict) -> str:
    try:
        endpoints = data.get("onResponseReceivedEndpoints", [])
        for ep in endpoints:
            actions = ep.get("reloadContinuationItemsCommand", {}).get("continuationItems", [])
            for item in actions:
                continuation = item.get("continuationItemRenderer", {}) \
                    .get("continuationEndpoint", {}) \
                    .get("continuationCommand", {}) \
                    .get("token")
                if continuation:
                    print(continuation)
                    return continuation
    except Exception as e:
        print("Failed in onResponseReceivedEndpoints", e)

    try:
        results = data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"]
        for item in results:
            item_section = item.get("itemSectionRenderer", {})
            for content in item_section.get("contents", []):
                continuation = content.get("continuationItemRenderer", {}) \
                    .get("continuationEndpoint", {}) \
                    .get("continuationCommand", {}) \
                    .get("token")
                if continuation:
                    print(continuation)
                    return continuation
    except Exception as e:
        print("Fallback failed:", e)

    return None

def parse_comment_entities(data: dict) -> Dict[str, Dict]:
    """Parse entityBatchUpdate"""
    result = {}
    mutations = data.get("frameworkUpdates", {}).get("entityBatchUpdate", {}).get("mutations", [])
    for m in mutations:
        payload = m.get("payload", {})
        comment = payload.get("commentEntityPayload", {})
        props = comment.get("properties", {})
        comment_id = props.get("commentId")
        if comment_id:
            result[comment_id] = {
                "content": props.get("content", {}).get("content", ""),
                "author": comment.get("author", {}).get("displayName", ""),
                "avatar": comment.get("author", {}).get("avatarThumbnailUrl", ""),
                "published": props.get("publishedTime", {}),
                "likes": int(comment.get("toolbar", {}).get("likeCountLiked") or 0),
                "replies": int(comment.get("toolbar", {}).get("replyCount") or 0)
            }
            
    return result

async def get_video_comments(video_id: str, proxy: str = None, max_comments: int = 100) -> List[Dict]:
    API_KEY = await get_youtube_api_key()
    URL_NEXT = f"https://www.youtube.com/youtubei/v1/next?key={API_KEY}"
    URL_COMMENT = URL_NEXT
    context = get_context()

    comments = []

    async with httpx.AsyncClient(proxies=proxy, timeout=15) as client:
        payload = {
            "context": context,
            "videoId": video_id
        }
        resp = await client.post(URL_NEXT, json=payload)
        resp.raise_for_status()
        data = resp.json()

        continuation_token = extract_comment_continuation_token(data)
        if not continuation_token:
            print("[!] No comment continuation token found in response:")
            raise Exception("No comment continuation token found")

        # Step 2: Fetch comments
        while continuation_token and len(comments) < max_comments:
            payload = {
                "context": context,
                "continuation": continuation_token
            }
            resp = await client.post(URL_COMMENT, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            entity_map = parse_comment_entities(data)

            continuation_token = None
            actions = data.get("onResponseReceivedEndpoints", [])
            for action in actions:
                items = action.get("reloadContinuationItemsCommand", {}).get("continuationItems", []) or \
                action.get("appendContinuationItemsAction", {}).get("continuationItems", [])
                for item in items:
                    if "commentThreadRenderer" in item:
                        thread = item["commentThreadRenderer"]

                        comment_vm = thread.get("commentViewModel", {}).get("commentViewModel", {})
                        comment_id = comment_vm.get("commentId")
                        entity = entity_map.get(comment_id, {})

                        author = entity.get("author", "")
                        avatar = entity.get("avatar")
                        content = entity.get("content", "")
                        published = entity.get("published", "")
                        likes = entity.get("likes", 0)
                        reply_count = entity.get("replies", 0)
                        
                        comment_data = {
                            "commentId": comment_id,
                            "author": author,
                            "avatar": avatar,
                            "content": content,
                            "published": published,
                            "likes": likes,
                            "replies": reply_count
                        }

                        comments.append(comment_data)
                        if len(comments) >= max_comments:
                            break

                    elif "continuationItemRenderer" in item:
                        continuation_token = item["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]
                if len(comments) >= max_comments:
                    break

    return comments[:max_comments]