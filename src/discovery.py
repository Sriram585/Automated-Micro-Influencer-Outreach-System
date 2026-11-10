import statistics
from googleapiclient.discovery import build
from src.config import YOUTUBE_API_KEY, SEARCH_QUERIES

def discover_youtube_influencers(target_count: int = 65) -> list[dict]:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    discovered_channel_ids = set()

    print(f"[Discovery] Searching YouTube across {len(SEARCH_QUERIES)} niche queries...")
    for query in SEARCH_QUERIES:
        if len(discovered_channel_ids) >= target_count:
            break
        req = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=25,
            relevanceLanguage="en"
        )
        res = req.execute()
        for item in res.get("items", []):
            cid = item["snippet"]["channelId"]
            discovered_channel_ids.add(cid)

    channel_id_list = list(discovered_channel_ids)[:target_count]
    print(f"[Discovery] Found {len(channel_id_list)} unique channels. Fetching metrics...")

    profiles = []
    # Batch in chunks of 50 (YouTube API limit per request)
    for i in range(0, len(channel_id_list), 50):
        batch_ids = channel_id_list[i:i+50]
        ch_req = youtube.channels().list(
            id=",".join(batch_ids),
            part="snippet,statistics,contentDetails"
        )
        ch_res = ch_req.execute()

        for ch in ch_res.get("items", []):
            cid = ch["id"]
            snippet = ch["snippet"]
            stats = ch["statistics"]
            
            if stats.get("hiddenSubscriberCount", False):
                continue
                
            subs = int(stats.get("subscriberCount", 0))
            uploads_playlist = ch["contentDetails"]["relatedPlaylists"].get("uploads")
            
            recent_titles, median_er = _fetch_recent_video_engagement(youtube, uploads_playlist, subs)
            if not recent_titles:
                continue

            custom_url = snippet.get("customUrl", f"channel/{cid}")
            profile_url = f"https://www.youtube.com/{custom_url}" if custom_url.startswith("@") else f"https://www.youtube.com/channel/{cid}"

            profiles.append({
                "channel_id": cid,
                "name": snippet.get("title", "Unknown"),
                "platform": "YouTube",
                "profile_url": profile_url,
                "followers": subs,
                "engagement_rate": round(median_er, 2),
                "raw_description": snippet.get("description", ""),
                "country": snippet.get("country", "Global / Unspecified"),
                "recent_videos": " | ".join(recent_titles[:4])
            })

    print(f"[Discovery] Successfully extracted {len(profiles)} complete influencer profiles.")
    return profiles

def _fetch_recent_video_engagement(youtube, playlist_id: str, followers: int) -> tuple[list[str], float]:
    if not playlist_id or followers == 0:
        return [], 0.0
    try:
        pl_req = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="contentDetails",
            maxResults=5
        )
        pl_res = pl_req.execute()
        video_ids = [item["contentDetails"]["videoId"] for item in pl_res.get("items", [])]
        if not video_ids:
            return [], 0.0

        v_req = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics"
        )
        v_res = v_req.execute()

        titles = []
        er_list = []
        for v in v_res.get("items", []):
            titles.append(v["snippet"]["title"])
            v_stats = v.get("statistics", {})
            views = int(v_stats.get("viewCount", 0))
            likes = int(v_stats.get("likeCount", 0))
            comments = int(v_stats.get("commentCount", 0))
            
            # Engagement Rate Formula: ((Likes + Comments) / Views) * 100
            # Fallback to Followers denominator if views are abnormally low
            denom = max(views, 1)
            er = ((likes + comments) / denom) * 100.0
            er_list.append(er)

        median_er = statistics.median(er_list) if er_list else 0.0
        return titles, median_er
    except Exception:
        return [], 0.0